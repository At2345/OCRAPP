from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.db import sqlite_store
from app.main import app


client = TestClient(app)


def _png_bytes(path: Path) -> bytes:
    image = Image.new("RGB", (200, 120), "white")
    image.save(path)
    return path.read_bytes()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unsupported_file_extension():
    response = client.post("/api/digitize", files={"file": ("doc.txt", b"hello", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["message"]


def test_empty_file():
    response = client.post("/api/digitize", files={"file": ("empty.png", b"", "image/png")})
    assert response.status_code == 400
    assert "empty" in response.json()["message"].lower()


def test_oversized_file(monkeypatch):
    monkeypatch.setattr(sqlite_store.settings, "MAX_FILE_SIZE_MB", 0)
    response = client.post("/api/digitize", files={"file": ("large.png", b"123", "image/png")})
    assert response.status_code == 413


def test_corrupt_pdf_handling():
    response = client.post("/api/digitize", files={"file": ("bad.pdf", b"%PDF broken", "application/pdf")})
    assert response.status_code == 400
    assert "PDF Error" in response.json()["message"]


def test_valid_png_and_duplicate(tmp_path, monkeypatch):
    import app.main as main_module
    from app.models.schemas import PageResult

    async def fake_ocr(image, page_number, provider=None, model=None):
        return PageResult(
            page_number=page_number,
            full_text="Dear Morgan, thank you for the notes.",
            confidence_score=0.95,
            legibility_issues_detected=False,
            unclear_segments=[],
        )

    monkeypatch.setattr(main_module.ocr_service, "process_image_page", fake_ocr)
    monkeypatch.setattr(sqlite_store.settings, "DATABASE_PATH", str(tmp_path / "api.sqlite3"))
    sqlite_store.init_db()
    file_bytes = _png_bytes(tmp_path / "sample.png")
    first = client.post("/api/digitize", files={"file": ("sample.png", file_bytes, "image/png")})
    assert first.status_code == 200
    assert first.json()["is_duplicate"] is False
    assert first.json()["ocr_provider"] == "openai"
    second = client.post(
        "/api/digitize",
        files={"file": ("sample-again.png", file_bytes, "image/png")},
        data={"provider": "anthropic"},
    )
    assert second.status_code == 200
    data = second.json()
    assert data["is_duplicate"] is True
    assert data["requires_human_review"] is True
    assert data["ocr_provider"] == "anthropic"
