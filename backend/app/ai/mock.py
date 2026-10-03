import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.ai.base import HairTransferModel


class MockHairTransfer(HairTransferModel):
    """CPU-only stand-in. NOT a real hair transfer.

    Finds the face with OpenCV, then feathers the top of the reference image over the
    area above the face so the UI flow can be demoed. A visible 'ÖNİZLEME' badge is added.
    """

    name = "mock"
    is_mock = True

    def __init__(self) -> None:
        self._cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def _face_box(self, rgb: np.ndarray) -> tuple[int, int, int, int]:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        faces = self._cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        h, w = gray.shape
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            return int(x), int(y), int(fw), int(fh)
        return int(w * 0.3), int(h * 0.25), int(w * 0.4), int(h * 0.4)  # fallback: centered box

    def transfer(self, face: Image.Image, hair_reference: Image.Image) -> Image.Image:
        face = face.convert("RGB")
        w, h = face.size
        rgb = np.asarray(face)
        x, y, fw, fh = self._face_box(rgb)

        # Hair region: wider than the face, from above the forehead down to the eyebrows.
        top = max(y - int(fh * 0.55), 0)
        bottom = y + int(fh * 0.30)
        left = max(x - int(fw * 0.25), 0)
        right = min(x + fw + int(fw * 0.25), w)
        region_w, region_h = right - left, max(bottom - top, 1)

        ref = hair_reference.convert("RGB")
        rw, rh = ref.size
        ref_top = ref.crop((int(rw * 0.1), 0, int(rw * 0.9), int(rh * 0.5))).resize((region_w, region_h))

        # Keep only "hair-like" pixels: drop the reference background (color of its corner),
        # then fade the bottom edge so there is no hard seam on the forehead.
        arr = np.asarray(ref_top).astype(np.int16)
        bg = arr[:4, :4].reshape(-1, 3).mean(axis=0)
        fg = (np.abs(arr - bg).sum(axis=2) > 60).astype(np.float32)
        fade = np.clip((1.0 - np.linspace(0, 1, region_h)) / 0.45, 0, 1)[:, None]
        alpha = fg * fade
        k = max(region_w // 12, 3) | 1
        alpha = cv2.GaussianBlur(alpha, (k, k), 0)
        mask = Image.fromarray((alpha * 255).astype(np.uint8))

        out = face.copy()
        out.paste(ref_top, (left, top), mask)

        draw = ImageDraw.Draw(out)
        font = ImageFont.load_default()
        draw.rectangle((8, 8, 150, 28), fill=(38, 20, 47))
        draw.text((14, 13), "ONIZLEME (MOCK)", fill=(255, 255, 255), font=font)
        return out
