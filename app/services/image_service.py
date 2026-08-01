import io

from PIL import Image, UnidentifiedImageError


class ImageProcessingError(Exception):
    pass


def image_bytes_to_image(file_bytes: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image.verify()
        image = Image.open(io.BytesIO(file_bytes))
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageProcessingError(f"Corrupt or unreadable image file: {exc}") from exc
