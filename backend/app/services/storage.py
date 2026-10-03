import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

log = logging.getLogger(__name__)
Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def expiry() -> datetime:
    return now() + timedelta(minutes=get_settings().image_ttl_minutes)


def safe_path(rel: str) -> Path:
    """Resolve a stored relative path and make sure it stays inside the storage root."""
    root = get_settings().storage_path
    p = (root / rel).resolve()
    if root not in p.parents:
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
    return p


def process_image_bytes(data: bytes) -> Image.Image:
    """Validate by actually decoding; drop EXIF/metadata; bound the size."""
    s = get_settings()
    try:
        probe = Image.open(io.BytesIO(data))
        if probe.format not in ALLOWED_FORMATS:
            raise HTTPException(status_code=415, detail="Yalnızca JPEG, PNG veya WEBP yüklenebilir")
        probe.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")  # re-created pixels => no metadata
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise HTTPException(status_code=400, detail="Geçerli bir görsel dosyası değil")
    if img.width < 128 or img.height < 128:
        raise HTTPException(status_code=400, detail="Görsel çok küçük (en az 128x128)")
    img.thumbnail((s.max_image_side, s.max_image_side))
    return img


async def read_limited(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_mb * 1024 * 1024
    buf = bytearray()
    while chunk := await file.read(64 * 1024):
        buf.extend(chunk)
        if len(buf) > limit:
            raise HTTPException(status_code=413, detail=f"Dosya {get_settings().max_upload_mb} MB sınırını aşıyor")
    return bytes(buf)


def save_jpeg(img: Image.Image, folder: str, salon_id: uuid.UUID) -> str:
    rel = f"{folder}/{salon_id}/{uuid.uuid4().hex}.jpg"
    path = safe_path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=90)
    return rel


def delete_file(rel: str | None) -> None:
    if not rel:
        return
    try:
        safe_path(rel).unlink(missing_ok=True)
    except Exception:
        log.exception("Could not delete %s", rel)
