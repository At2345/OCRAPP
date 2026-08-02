# Handwriting OCR Digitizer

A FastAPI web application for digitizing handwritten letters, notes, mixed printed/handwritten documents, and multi-page PDFs. The app returns editable full text, extracted dates/emails/phone numbers, confidence scores, duplicate detection, and human review flags.



## Git Repository URL

Add your GitHub repository URL here:

```text
https://github.com/your-username/handwriting-ocr-digitizer
```

## Features Checklist

- Upload support for `PDF`, `JPG`, `JPEG`, and `PNG`.
- Multi-page PDFs processed as one document.
- Handwriting and printed text processed together.
- Editable full-text output.
- Extraction of dates, email addresses, and phone numbers.
- Overall, per-page, and extracted-field confidence scores.
- Human review banner for low confidence, unclear text, duplicates, and poor legibility.
- Strict no-guess OCR prompt using `[illegible]` for uncertain content.
- SHA-256 duplicate detection using SQLite.
- Graceful handling of corrupt PDFs/images, unsupported formats, empty files, oversized files, and OCR service outages.
- Docker Compose local startup.
- Fictional test data with ground truth.

## Architecture

```text
Browser UI
  -> FastAPI /api/digitize
    -> file validation
    -> SHA-256 hash + SQLite duplicate lookup
    -> PDF rendering with PyMuPDF or image validation with Pillow
    -> OpenAI or Claude vision OCR (Emergent Universal LLM key)
    -> regex entity extraction
    -> confidence + human-review rules
    -> structured JSON response
```

## Model Choice

The app uses vision-language models for OCR and lets you switch engines per upload:

- **OpenAI** (`OPENAI_MODEL`, default `gpt-5.4`)
- **Anthropic Claude** (`ANTHROPIC_MODEL`, default `claude-sonnet-4-6`)

Pick the engine from the toggle in the UI, or send `provider=openai` / `provider=anthropic`
as a form field to `POST /api/digitize`. The default engine is set by `OCR_PROVIDER`.

Vision-language models are selected because general OCR engines often struggle with cursive
handwriting, skewed smartphone photos, shadows, and mixed printed/handwritten notes. The OCR
prompt requires exact transcription, layout preservation, no hallucination, and `[illegible]`
markers for unclear words.

Both providers are powered by the **Emergent Universal LLM key** (`EMERGENT_LLM_KEY`), so no
separate OpenAI/Anthropic keys are required. Set `EMERGENT_LLM_KEY` in your `.env`.

## Local Setup With Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python generate_test_docs.py
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

## Local Setup With Docker Compose

```bash
copy .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8000
```

## Environment Variables

| Variable | Purpose |
|---|---|
| `APP_NAME` | Display/API app name |
| `DEBUG` | Enables exception details when true |
| `EMERGENT_LLM_KEY` | Emergent Universal LLM key powering OpenAI + Claude OCR |
| `OCR_PROVIDER` | Default engine: `openai` or `anthropic` |
| `OPENAI_MODEL` | OpenAI vision model, default `gpt-5.4` |
| `ANTHROPIC_MODEL` | Claude vision model, default `claude-sonnet-4-6` |
| `CONFIDENCE_THRESHOLD` | Below this requires human review |
| `MAX_FILE_SIZE_MB` | Upload size limit |
| `DATABASE_PATH` | SQLite database path |
| `OCR_TIMEOUT_SECONDS` | OCR request timeout |

## PDF Export

After digitizing a document, use the frontend `Download PDF` button to export the editable text area as a PDF. The API endpoint is:

```text
POST /api/export/pdf
```

## Running Tests

```bash
pytest
```

## Generating Test Documents

```bash
python generate_test_docs.py
```

This creates files in `test_data/` and writes `ground_truth.json`.

## Test Data Summary

| File | Scenario | Human Review |
|---|---|---|
| `01_legible_handwritten_letter.png` | Clearly legible handwritten-style letter | No |
| `02_multipage_letter.pdf` | Two-page fictional letter with date | No |
| `03_skewed_shadow_photo.jpg` | Smartphone-style skew/shadow photo | Yes |
| `04_hard_to_read_handwriting.png` | Blurred low-contrast handwriting | Yes |
| `05_printed_with_handwritten_additions.png` | Printed booking note plus handwritten approval | No |
| `06_contact_details_letter.png` | Fictional email, phone numbers, and date | No |
| `07_corrupt_unreadable.pdf` | Invalid PDF bytes | Yes/error |
| `08_duplicate_of_legible.png` | Binary duplicate of case 1 | Yes when uploaded after case 1 |

## Deployment

### Render

1. Push this repository to GitHub.
2. Create a new Render Blueprint or Docker web service.
3. Use `render.yaml` or configure:
   - Runtime: Docker
   - Health check path: `/health`
4. Add environment variables:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL=gpt-4o-mini`
   - `CONFIDENCE_THRESHOLD=0.80`
   - `MAX_FILE_SIZE_MB=15`

### Railway

1. Connect the GitHub repository.
2. Use the Dockerfile.
3. Add the same environment variables.
4. Deploy and open the public URL.

## API Documentation

- Web app: `/`
- Health check: `/health`
- Swagger docs: `/docs`
- OCR endpoint: `POST /api/digitize`

## Security Notes

- No API keys are stored in code.
- `.env` is ignored by Git.
- Upload file types and file sizes are validated.
- No login is required because the task explicitly requests public access.
- Test data is completely fictional.
- SQLite is used for demo duplicate tracking; use a managed database for production scale.

## Known Limitations

- Real handwriting accuracy requires a configured vision API key.
- Confidence scores are model-estimated and should be treated as decision support.
- SQLite duplicate storage is suitable for demos, not high-traffic production.
- OCR quality can degrade with extreme blur, cropped pages, very low contrast, or severe shadows.


## Development Shortcuts

```bash
make install
make generate-test-data
make test
make run