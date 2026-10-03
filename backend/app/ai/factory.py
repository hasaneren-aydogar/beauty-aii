import logging
from functools import lru_cache

from app.ai.base import HairTransferModel
from app.ai.mock import MockHairTransfer
from app.core.config import get_settings

log = logging.getLogger(__name__)


@lru_cache
def get_hair_model() -> HairTransferModel:
    s = get_settings()
    if s.ai_backend == "hairfast":
        try:
            from app.ai.hairfast import HairFastGANModel

            return HairFastGANModel(s.hairfast_repo_path)
        except Exception:
            if not s.ai_fallback_to_mock:
                raise
            log.exception("HairFastGAN unavailable -> falling back to MOCK engine")
    return MockHairTransfer()
