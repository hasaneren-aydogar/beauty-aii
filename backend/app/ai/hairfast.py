"""HairFastGAN adapter (real inference, needs an NVIDIA GPU).

Setup: scripts/setup_hairfast.sh. Not verified on GPU hardware in this repo's CI —
check the upstream README if the import/API below drifted.
"""
import logging
import sys
import threading
from pathlib import Path

from PIL import Image

from app.ai.base import HairTransferModel

log = logging.getLogger(__name__)


class HairFastGANModel(HairTransferModel):
    name = "hairfastgan"
    is_mock = False

    def __init__(self, repo_path: str) -> None:
        import torch  # noqa: F401  (fail early if torch is missing)

        repo = Path(repo_path).resolve()
        if not (repo / "hair_swap.py").exists():
            raise FileNotFoundError(f"HairFastGAN repo not found at {repo}. Run scripts/setup_hairfast.sh")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU not available; HairFastGAN is impractically slow on CPU.")
        sys.path.insert(0, str(repo))
        from hair_swap import HairFast, get_parser  # type: ignore[import-not-found]

        log.info("Loading HairFastGAN from %s", repo)
        self._model = HairFast(get_parser().parse_args([]))
        self._lock = threading.Lock()  # one inference at a time per GPU

    def transfer(self, face: Image.Image, hair_reference: Image.Image) -> Image.Image:
        from torchvision.transforms.functional import to_pil_image

        face = face.convert("RGB")
        ref = hair_reference.convert("RGB")
        with self._lock:
            # shape and color both come from the selected hair model
            result = self._model.swap(face, ref, ref, align=True)
        if isinstance(result, tuple):
            result = result[0]
        return to_pil_image(result.clamp(0, 1).cpu()) if hasattr(result, "clamp") else result
