import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AnyRole, Principal, StaffUp
from app.core.db import get_db
from app.models import HairModel
from app.rag import service as rag
from app.schemas import HairModelOut
from app.services import storage

router = APIRouter(prefix="/hair-models", tags=["hair-models"])


def _index(db: Session, m: HairModel) -> None:
    attrs = ", ".join(
        f"{label}: {v}" for label, v in
        [("kategori", m.category), ("uzunluk", m.hair_length), ("saç tipi", m.hair_type), ("renk", m.hair_color)] if v
    )
    text = f"{m.name} saç modeli. {attrs}. {m.description or ''}".strip()
    rag.reindex_source(db, salon_id=m.salon_id, source_type="hair_model", source_id=m.id,
                       title=f"Saç modeli: {m.name}", content=text, hair_model_id=m.id)


def get_owned(db: Session, salon_id: uuid.UUID, model_id: uuid.UUID) -> HairModel:
    m = db.scalar(select(HairModel).where(HairModel.id == model_id, HairModel.salon_id == salon_id))
    if m is None:
        raise HTTPException(status_code=404, detail="Saç modeli bulunamadı")
    return m


@router.get("", response_model=list[HairModelOut])
def list_hair_models(category: str | None = None, p: Principal = AnyRole, db: Session = Depends(get_db)):
    q = select(HairModel).where(HairModel.salon_id == p.salon_id).order_by(HairModel.created_at)
    if category:
        q = q.where(HairModel.category == category)
    return db.scalars(q).all()


@router.post("", response_model=HairModelOut, status_code=201)
async def create_hair_model(
    name: str = Form(min_length=2, max_length=200),
    description: str | None = Form(default=None, max_length=2000),
    category: str | None = Form(default=None, max_length=100),
    hair_length: str | None = Form(default=None, max_length=50),
    hair_type: str | None = Form(default=None, max_length=50),
    hair_color: str | None = Form(default=None, max_length=50),
    image: UploadFile = File(...),
    p: Principal = StaffUp,
    db: Session = Depends(get_db),
):
    img = storage.process_image_bytes(await storage.read_limited(image))
    rel = storage.save_jpeg(img, "hair_models", p.salon_id)
    m = HairModel(salon_id=p.salon_id, name=name, description=description, category=category,
                  hair_length=hair_length, hair_type=hair_type, hair_color=hair_color, image_path=rel)
    db.add(m)
    db.flush()
    m.image_url = f"/api/v1/hair-models/{m.id}/image"
    _index(db, m)
    db.commit()
    return m


@router.get("/{model_id}/image")
def hair_model_image(model_id: uuid.UUID, p: Principal = AnyRole, db: Session = Depends(get_db)):
    m = get_owned(db, p.salon_id, model_id)
    if not m.image_path:
        raise HTTPException(status_code=404, detail="Görsel yok")
    return FileResponse(storage.safe_path(m.image_path), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=300"})


@router.delete("/{model_id}", status_code=204)
def delete_hair_model(model_id: uuid.UUID, p: Principal = StaffUp, db: Session = Depends(get_db)) -> None:
    m = get_owned(db, p.salon_id, model_id)
    rag.remove_source(db, p.salon_id, "hair_model", m.id)
    storage.delete_file(m.image_path)
    db.delete(m)
    db.commit()
