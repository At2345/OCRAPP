from __future__ import annotations

import io

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.paragraph import cleanBlockQuotedText


class PDFExportError(Exception):
    pass


def text_to_pdf_bytes(title: str, text: str) -> bytes:
    if not text.strip():
        raise PDFExportError("No text provided for PDF export.")
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    story = [Paragraph(cleanBlockQuotedText(title), styles["Title"]), Spacer(1, 18)]
    for block in text.split("\n"):
        line = block if block.strip() else "&nbsp;"
        story.append(Paragraph(cleanBlockQuotedText(line), styles["BodyText"]))
        story.append(Spacer(1, 4))
    try:
        document.build(story)
    except Exception as exc:
        raise PDFExportError(f"PDF export failed: {exc}") from exc
    return buffer.getvalue()
