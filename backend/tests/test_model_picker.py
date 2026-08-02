"""Backend tests for the Model Picker feature.

Verifies POST /api/digitize honors the 'model' form field per provider,
and that invalid models fall back to the provider's default.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("PREVIEW_URL", "https://ocr-benchmark-1.preview.emergentagent.com").rstrip("/")
TEST_IMG = "/app/test_data/01_legible_handwritten_letter.png"


@pytest.fixture
def api():
    return requests.Session()


def test_index_exposes_model_catalog_and_select(api):
    r = api.get(f"{BASE_URL}/", timeout=20)
    assert r.status_code == 200
    html = r.text
    assert 'data-testid="model-select"' in html
    assert 'id="modelCatalog"' in html
    assert 'id="defaultModels"' in html
    # OpenAI model options present
    for m in ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.1", "gpt-4.1", "gpt-4o"]:
        assert m in html, f"missing openai model {m} in index html"
    # Anthropic model options present
    for m in ["claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-5", "claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"]:
        assert m in html, f"missing anthropic model {m} in index html"


def test_digitize_openai_with_specific_model_gpt4o(api):
    with open(TEST_IMG, "rb") as f:
        files = {"file": ("01_legible_handwritten_letter.png", f, "image/png")}
        data = {"provider": "openai", "model": "gpt-4o"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "openai"
    assert body["ocr_model"] == "gpt-4o"
    assert len(body["full_text"]) > 20


def test_digitize_anthropic_with_specific_model_opus46(api):
    with open(TEST_IMG, "rb") as f:
        files = {"file": ("01_legible_handwritten_letter.png", f, "image/png")}
        data = {"provider": "anthropic", "model": "claude-opus-4-6"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "anthropic"
    assert body["ocr_model"] == "claude-opus-4-6"
    assert len(body["full_text"]) > 20


def test_invalid_model_falls_back_to_default(api):
    with open(TEST_IMG, "rb") as f:
        files = {"file": ("01_legible_handwritten_letter.png", f, "image/png")}
        data = {"provider": "openai", "model": "not-a-real-model-xyz"}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "openai"
    assert body["ocr_model"] == "gpt-5.4"  # default fallback


def test_empty_model_uses_default(api):
    with open(TEST_IMG, "rb") as f:
        files = {"file": ("01_legible_handwritten_letter.png", f, "image/png")}
        data = {"provider": "anthropic", "model": ""}
        r = api.post(f"{BASE_URL}/api/digitize", files=files, data=data, timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ocr_provider"] == "anthropic"
    assert body["ocr_model"] == "claude-sonnet-4-6"
