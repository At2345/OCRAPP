from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path("test_data")
GROUND_TRUTH_PATH = Path("ground_truth.json")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoepr.ttf",
        "C:/Windows/Fonts/comic.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_multiline(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], fill: str, font: ImageFont.ImageFont, spacing: int = 12) -> None:
    x, y = xy
    for line in text.splitlines():
        draw.text((x, y), line, fill=fill, font=font)
        bbox = draw.textbbox((x, y), line or "A", font=font)
        y += bbox[3] - bbox[1] + spacing


def _paper(width: int = 900, height: int = 650) -> Image.Image:
    image = Image.new("RGB", (width, height), "#fbfaf5")
    arr = np.array(image).astype(np.int16)
    noise = np.random.default_rng(42).integers(-4, 5, arr.shape, dtype=np.int16)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))


def _shadow_skew(image: Image.Image) -> Image.Image:
    rotated = image.rotate(4, expand=True, fillcolor="#f7f4ea")
    arr = np.array(rotated).astype(float)
    height, width, _ = arr.shape
    shadow = np.linspace(0.58, 1.0, width)
    shadow = np.tile(shadow, (height, 1))
    arr *= np.stack([shadow, shadow, shadow], axis=-1)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _save_image(filename: str, text: str, fill: str = "#1e3a8a", rotate: float = -1.0) -> None:
    image = _paper()
    draw = ImageDraw.Draw(image)
    _draw_multiline(draw, text, (70, 70), fill, _font(30), 16)
    image = image.rotate(rotate, expand=True, fillcolor="#fbfaf5")
    image.save(OUTPUT_DIR / filename)


def generate_all() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    ground_truth: dict[str, dict] = {}

    text1 = "Dear Morgan,\nThank you for the garden club notes.\nI will bring the seed catalog on Saturday.\nWarmly,\nRiley"
    _save_image("01_legible_handwritten_letter.png", text1)
    ground_truth["01_legible_handwritten_letter.png"] = {
        "description": "Clearly legible handwritten-style letter",
        "expected_text": text1,
        "expected_entities": {"dates": [], "emails": [], "phone_numbers": []},
        "requires_human_review": False,
        "notes": "Standard legible fictional letter.",
    }

    page1 = "Dear Taylor,\nThis is page one of a fictional multi-page letter.\nThe community art plan looks ready for review."
    page2 = "Page two continues the same letter.\nPlease send final comments by 2026-08-15.\nSincerely,\nJordan"
    doc = fitz.open()
    for text in (page1, page2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 90), text, fontsize=16, lineheight=1.4)
    doc.save(OUTPUT_DIR / "02_multipage_letter.pdf")
    doc.close()
    ground_truth["02_multipage_letter.pdf"] = {
        "description": "Two-page fictional letter PDF",
        "expected_text": f"--- Page 1 ---\n{page1}\n\n--- Page 2 ---\n{page2}",
        "expected_entities": {"dates": ["2026-08-15"], "emails": [], "phone_numbers": []},
        "requires_human_review": False,
        "notes": "Multi-page document processed as one document.",
    }

    text3 = "Workshop Notes\nBring blue markers and blank cards.\nMeet near the library entrance."
    image3 = _paper()
    _draw_multiline(ImageDraw.Draw(image3), text3, (80, 90), "#111827", _font(30), 18)
    _shadow_skew(image3).save(OUTPUT_DIR / "03_skewed_shadow_photo.jpg", quality=90)
    ground_truth["03_skewed_shadow_photo.jpg"] = {
        "description": "Smartphone-style photo with skew and shadow",
        "expected_text": text3,
        "expected_entities": {"dates": [], "emails": [], "phone_numbers": []},
        "requires_human_review": True,
        "notes": "Human review required due to skew/shadow conditions.",
    }

    text4_visible = "Market list\nBring [illegible] cards\nMeet at [illegible] gate"
    image4 = _paper(850, 460)
    _draw_multiline(ImageDraw.Draw(image4), "Market list\nBring smudged cards\nMeet at west gate", (60, 80), "#9ca3af", _font(28), 16)
    image4 = image4.filter(ImageFilter.GaussianBlur(radius=2.1))
    image4.save(OUTPUT_DIR / "04_hard_to_read_handwriting.png")
    ground_truth["04_hard_to_read_handwriting.png"] = {
        "description": "Blurred, low-contrast hard-to-read handwriting",
        "expected_text": text4_visible,
        "expected_entities": {"dates": [], "emails": [], "phone_numbers": []},
        "requires_human_review": True,
        "notes": "Ground truth uses [illegible] for intentionally unclear words.",
    }

    image5 = _paper()
    draw5 = ImageDraw.Draw(image5)
    _draw_multiline(draw5, "COMMUNITY ROOM BOOKING\nStatus: Pending", (70, 70), "#111827", _font(34), 18)
    _draw_multiline(draw5, "Approved by Casey on 12/05/2026", (90, 230), "#1d4ed8", _font(30), 12)
    image5.save(OUTPUT_DIR / "05_printed_with_handwritten_additions.png")
    ground_truth["05_printed_with_handwritten_additions.png"] = {
        "description": "Printed letter with handwritten-style additions",
        "expected_text": "COMMUNITY ROOM BOOKING\nStatus: Pending\nApproved by Casey on 12/05/2026",
        "expected_entities": {"dates": ["12/05/2026"], "emails": [], "phone_numbers": []},
        "requires_human_review": False,
        "notes": "Mixed printed and handwritten-style content.",
    }

    text6 = "Hello Avery,\nPlease contact notes@example.test or call +1-555-019-2834.\nBackup desk number: (555) 013-4455.\nDate: August 1, 2026"
    _save_image("06_contact_details_letter.png", text6, "#111827", 0)
    ground_truth["06_contact_details_letter.png"] = {
        "description": "Letter containing fictional phone numbers and email",
        "expected_text": text6,
        "expected_entities": {"dates": ["August 1, 2026"], "emails": ["notes@example.test"], "phone_numbers": ["+1-555-019-2834", "(555) 013-4455"]},
        "requires_human_review": False,
        "notes": "Uses reserved .test domain and fictional 555 numbers.",
    }

    (OUTPUT_DIR / "07_corrupt_unreadable.pdf").write_bytes(b"%PDF-1.4 corrupt fictional bytes not a valid PDF")
    ground_truth["07_corrupt_unreadable.pdf"] = {
        "description": "Corrupt or unreadable PDF",
        "expected_text": "Graceful PDF error response",
        "expected_entities": {"dates": [], "emails": [], "phone_numbers": []},
        "requires_human_review": True,
        "notes": "Application must return a controlled error and not crash.",
    }

    shutil.copyfile(OUTPUT_DIR / "01_legible_handwritten_letter.png", OUTPUT_DIR / "08_duplicate_of_legible.png")
    ground_truth["08_duplicate_of_legible.png"] = {
        "description": "Identical binary duplicate of the first legible letter",
        "expected_text": text1,
        "expected_entities": {"dates": [], "emails": [], "phone_numbers": []},
        "requires_human_review": True,
        "notes": "Duplicate detection should trigger when uploaded after case 1.",
    }

    GROUND_TRUTH_PATH.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate_all()
    print("Generated 8 fictional test documents and ground_truth.json")
