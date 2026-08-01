from __future__ import annotations

import io

import fitz
from PIL import Image


class PDFProcessingError(Exception):
    pass


def pdf_bytes_to_images(file_bytes: bytes) -> list[Image.Image]:
    doc = None
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.is_encrypted:
            raise PDFProcessingError("PDF is encrypted and cannot be processed.")
        if doc.page_count == 0:
            raise PDFProcessingError("PDF contains no pages.")
        images: list[Image.Image] = []
        for page in doc:
            pixmap = page.get_pixmap(dpi=200)
            image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
            images.append(image)
        return images
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError(f"Corrupt or invalid PDF file: {exc}") from exc
    finally:
        if doc is not None:
            doc.close()
