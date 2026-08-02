"""End-to-end backend API tests for Handwriting OCR Digitizer.

Hits the PREVIEW URL, no mocks. OCR calls hit real LLMs — allow generous timeouts.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("PREVIEW_URL", "https://ocr-benchmark-1.preview.emergentagent.com").rstrip("/")
TEST_IMG = "/app/test_data/01_legible_handwritten_letter.png"
TEST_IMG2 = "/app/test_data/06_contact_details_letter.png"


@pytest.fixture
def api():
    s = requests.Session()
    return s


# Health check
def test_health_endpoint(api):
    r = api.get(f"{BASE_URL}/health", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["ocr_configured"] is True
    assert set(data["available_providers"]) == {"openai", "anthropic"}
    assert data["models"]["openai"] == "gpt-5.4"
    assert data["models"]["anthropic"] == "claude-sonnet-4-6"


def test_index_page_renders(api):
    r = api.get(f"{BASE_URL}/", timeout=20)
    assert r.status_code == 200
    assert "Handwriting OCR Digitizer" in r.text
    assert 'data-testid="provider-openai-btn"' in r.text
    assert 'data-testid="provider-anthropic-btn"' in r.text
    assert 'data-testid="digitize-btn"' in r.text


# OCR digitize with OpenAI
def test_digitize_openai(api):
    with open(TEST_IMG, "rb") as f:
        files = {"file": ("01_legible_handwritten_letter.png", f, "image/png")}
        data = {"provider": "openai"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "openai"
    assert body["ocr_model"] == "gpt-5.4"
    assert isinstance(body["full_text"], str) and len(body["full_text"]) > 20
    assert 0.0 <= body["confidence_score"] <= 1.0


# OCR digitize with Anthropic Claude
def test_digitize_anthropic(api):
    with open(TEST_IMG2, "rb") as f:
        files = {"file": ("06_contact_details_letter.png", f, "image/png")}
        data = {"provider": "anthropic"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "anthropic"
    assert body["ocr_model"] == "claude-sonnet-4-6"
    assert isinstance(body["full_text"], str) and len(body["full_text"]) > 20


# Error handling: unsupported .txt file
def test_digitize_unsupported_extension(api, tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello world")
    with open(p, "rb") as f:
        files = {"file": ("note.txt", f, "text/plain")}
        data = {"provider": "openai"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=30)
    assert r.status_code == 400
    body = r.json()
    assert "Unsupported" in body.get("message", "") or "Unsupported" in str(body)


# PDF export sanity
def test_export_pdf(api):
    r = api.post(
        f"{BASE_URL}/api/export/pdf",
        json={"title": "Test", "text": "Hello world", "file_name": "test.pdf"},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
