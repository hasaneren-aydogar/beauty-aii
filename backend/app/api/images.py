import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.factory import get_hair_model
from app.api.deps import AnyRole, Principal
from app.api.hair_models import get_owned
from app.core.config import get_settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.models import GeneratedImage, UploadedImage
from app.schemas import TryIn, TryOut, UploadOut
from app.services import storage

log = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


def _owned_upload(db: Session, p: Principal, upload_id: uuid.UUID) -> UploadedImage:
    up = db.scalar(select(UploadedImage).where(UploadedImage.id == upload_id, UploadedImage.salon_id == p.salon_id))
    if up is None or up.expires_at < storage.now():
        raise HTTPException(status_code=404, detail="Fotoğraf bulunamadı veya süresi doldu")
    if p.role == "customer" and up.customer_id != p.customer_id:
        raise HTTPException(status_code=404, detail="Fotoğraf bulunamadı veya süresi doldu")
    return up


@router.post("/image/upload", response_model=UploadOut, status_code=201)
@limiter.limit("20/minute")
async def upload_image(
    request: Request, file: UploadFile = File(...), p: Principal = AnyRole, db: Session = Depends(get_db)
) -> UploadOut:
    img = storage.process_image_bytes(await storage.read_limited(file))
    rel = storage.save_jpeg(img, "uploads", p.salon_id)
    up = UploadedImage(salon_id=p.salon_id, customer_id=p.customer_id, path=rel, expires_at=storage.expiry())
    db.add(up)
    db.commit()
    return UploadOut(upload_id=up.id, expires_at=up.expires_at)


@router.get("/image/{upload_id}")
def get_upload(upload_id: uuid.UUID, p: Principal = AnyRole, db: Session = Depends(get_db)):
    up = _owned_upload(db, p, upload_id)
    return FileResponse(storage.safe_path(up.path), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


@router.delete("/image/{upload_id}", status_code=204)
def delete_upload(upload_id: uuid.UUID, p: Principal = AnyRole, db: Session = Depends(get_db)) -> None:
    """Customer finished: remove the photo and all results generated for this session right away."""
    up = _owned_upload(db, p, upload_id)
    storage.delete_file(up.path)
    db.delete(up)
    if p.customer_id:
        for gi in db.scalars(select(GeneratedImage).where(
            GeneratedImage.salon_id == p.salon_id, GeneratedImage.customer_id == p.customer_id,
            GeneratedImage.result_path.is_not(None),
        )):
            storage.delete_file(gi.result_path)
            gi.result_path, gi.status = None, "expired"
    db.commit()


@router.post("/hair/try", response_model=TryOut)
@limiter.limit(get_settings().rate_limit_try)
def try_hair(request: Request, body: TryIn, p: Principal = AnyRole, db: Session = Depends(get_db)) -> TryOut:
    up = _owned_upload(db, p, body.upload_id)
    hm = get_owned(db, p.salon_id, body.hair_model_id)
    if not hm.image_path:
        raise HTTPException(status_code=422, detail="Bu saç modelinin görseli yok")

    engine = get_hair_model()
    try:
        with Image.open(storage.safe_path(up.path)) as f, Image.open(storage.safe_path(hm.image_path)) as r:
            result = engine.transfer(f.convert("RGB"), r.convert("RGB"))
    except HTTPException:
        raise
    except Exception:
        log.exception("Hair transfer failed (engine=%s)", engine.name)
        db.add(GeneratedImage(salon_id=p.salon_id, customer_id=p.customer_id, hair_model_id=hm.id,
                              status="failed", engine=engine.name, expires_at=storage.expiry()))
        db.commit()
        raise HTTPException(status_code=502, detail="Saç modeli uygulanamadı. Lütfen başka bir fotoğrafla deneyin.")

    rel = storage.save_jpeg(result, "results", p.salon_id)
    gi = GeneratedImage(salon_id=p.salon_id, customer_id=p.customer_id, hair_model_id=hm.id,
                        result_path=rel, engine=engine.name, expires_at=storage.expiry())
    db.add(gi)
    db.commit()
    return TryOut(generated_image_id=gi.id, engine=engine.name, expires_at=gi.expires_at, is_mock=engine.is_mock)


@router.get("/hair/result/{generated_id}")
def get_result(generated_id: uuid.UUID, p: Principal = AnyRole, db: Session = Depends(get_db)):
    gi = db.scalar(select(GeneratedImage).where(GeneratedImage.id == generated_id, GeneratedImage.salon_id == p.salon_id))
    if gi is None or not gi.result_path or gi.expires_at < storage.now():
        raise HTTPException(status_code=404, detail="Sonuç bulunamadı veya süresi doldu")
    if p.role == "customer" and gi.customer_id != p.customer_id:
        raise HTTPException(status_code=404, detail="Sonuç bulunamadı veya süresi doldu")
    return FileResponse(storage.safe_path(gi.result_path), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})
