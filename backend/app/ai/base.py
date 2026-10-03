from abc import ABC, abstractmethod

from PIL import Image


class HairTransferModel(ABC):
    """Contract every hair-transfer engine must implement."""

    name: str = "base"
    is_mock: bool = False

    @abstractmethod
    def transfer(self, face: Image.Image, hair_reference: Image.Image) -> Image.Image:
        """Return `face` wearing the hairstyle (shape + color) of `hair_reference`."""
