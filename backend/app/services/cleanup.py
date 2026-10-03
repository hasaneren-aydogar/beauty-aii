import logging
import threading
import time

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import GeneratedImage, UploadedImage
from app.services.storage import delete_file, now

log = logging.getLogger(__name__)


def purge_expired() -> int:
    """Delete expired customer photos/results from disk and DB. Returns number of files removed."""
    removed = 0
    with SessionLocal() as db:
        for up in db.scalars(select(UploadedImage).where(UploadedImage.expires_at < now())):
            delete_file(up.path)
            db.execute(delete(UploadedImage).where(UploadedImage.id == up.id))
            removed += 1
        for gi in db.scalars(
            select(GeneratedImage).where(GeneratedImage.expires_at < now(), GeneratedImage.result_path.is_not(None))
        ):
            delete_file(gi.result_path)
            gi.result_path, gi.status = None, "expired"
            removed += 1
        db.commit()
    if removed:
        log.info("Auto-deleted %d expired image(s)", removed)
    return removed


def start_cleanup_loop(stop: threading.Event) -> threading.Thread:
    interval = get_settings().cleanup_interval_seconds

    def loop() -> None:
        while not stop.wait(interval):
            try:
                purge_expired()
            except Exception:
                log.exception("cleanup failed")

    t = threading.Thread(target=loop, name="image-cleanup", daemon=True)
    t.start()
    return t
