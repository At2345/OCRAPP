# Coding Instructions: Handwriting OCR Web App

You are an expert senior Python engineer. Build the complete project in this repository from scratch. The application must satisfy the job-task requirements exactly and be ready for GitHub + online deployment.

## Goal

Create a small public web application that accepts handwritten letters and notes in `PDF`, `JPG`, `JPEG`, or `PNG` format and digitizes them into editable full text.

The app focuses only on general handwriting OCR. Do **not** include prescriptions, medical orders, or industry-specific workflows. Use only fictional test data.

## Required Capabilities

Implement all of these:

- Upload `PDF`, `JPG`, `JPEG`, and `PNG` files.
- Process multi-page PDFs as one document.
- Recognize handwritten text and printed text together.
- Output editable full text.
- Extract dates, email addresses, and phone numbers when present.
- Provide confidence scores for:
  - overall text
  - each page
  - extracted fields
- Clearly indicate when human review is required because of poor legibility, OCR service errors, unclear words, skew/shadows, or low confidence.
- Never guess or fabricate unreadable information. Use `[illegible]` for unclear content.
- Detect duplicate uploads using SHA-256 file hashes.
- Gracefully handle corrupt PDFs, unreadable images, unsupported files, empty files, oversized files, and unreachable OCR services.
- No login required.
- API keys and configuration must come from environment variables only.
- Include Docker Compose local startup.
- Include tests and fictional test documents with ground truth.
- Include a strong `README.md` with setup, architecture, model choice, limitations, deployment, and demo script.

## Technology Requirements

Use Python.

Recommended stack:

- Backend: `FastAPI`
- Templates/UI: `Jinja2`, plain JavaScript, Tailwind CDN
- OCR/Vision model: OpenAI `gpt-4o-mini` by default, configurable to `gpt-4o`
- PDF rendering: `PyMuPDF`
- Image handling/test data: `Pillow`
- Persistence: `SQLite` for upload/hash records
- Validation/settings: `Pydantic v2`, `pydantic-settings`
- Tests: `pytest`, `httpx`, `fastapi.testclient`
- Deployment: Dockerfile + Render/Railway-compatible start command

## Important Quality Rules

- Write production-quality, typed, readable code.
- Use clear service separation.
- Do not hardcode secrets.
- Do not crash on bad input.
- Return structured JSON errors from API endpoints.
- Keep OCR prompts strict: no guessing, no hallucination.
- Make the UI polished, modern, responsive, and demo-friendly.
- Include mock OCR mode when no API key exists, so tests/local demo can run without paid credentials.
- Keep test data fully fictional.
- Avoid medical/prescription examples entirely.

## Project Structure To Create

Create this structure:

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── sqlite_store.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── entity_extractor.py
│   │   ├── hash_service.py
│   │   ├── image_service.py
│   │   ├── ocr_service.py
│   │   └── pdf_service.py
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       └── index.html
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_entities.py
│   └── test_hash_duplicates.py
├── test_data/
│   └── .gitkeep
├── generate_test_docs.py
├── ground_truth.json
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── render.yaml
```

## File-by-File Implementation Requirements

### `requirements.txt`

Include compatible packages:

```text
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9
jinja2>=3.1.4
pydantic>=2.7.0
pydantic-settings>=2.3.0
openai>=1.35.0
PyMuPDF>=1.24.0
Pillow>=10.3.0
numpy>=1.26.0
pytest>=8.2.0
httpx>=0.27.0
```

### `.env.example`

Include:

```text
APP_NAME="Handwriting OCR Digitizer"
DEBUG=false
OPENAI_API_KEY=""
OPENAI_MODEL="gpt-4o-mini"
CONFIDENCE_THRESHOLD=0.80
MAX_FILE_SIZE_MB=15
DATABASE_PATH="./ocr_uploads.sqlite3"
OCR_TIMEOUT_SECONDS=60
```

### `.gitignore`

Include Python, venv, env, cache, SQLite, generated local files:

```text
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
.env
*.sqlite3
.DS_Store
.coverage
htmlcov/
```

### `app/core/config.py`

Implement `Settings` using `pydantic-settings`.

Fields:

- `APP_NAME: str`
- `DEBUG: bool`
- `OPENAI_API_KEY: str`
- `OPENAI_MODEL: str`
- `CONFIDENCE_THRESHOLD: float`
- `MAX_FILE_SIZE_MB: int`
- `DATABASE_PATH: str`
- `OCR_TIMEOUT_SECONDS: int`
- `ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png")`

Export `settings = Settings()`.

### `app/models/schemas.py`

Define Pydantic models:

- `FieldConfidence`
  - `value: str`
  - `confidence_score: float`
  - `requires_human_review: bool`
- `ExtractedEntities`
  - `dates: list[FieldConfidence]`
  - `emails: list[FieldConfidence]`
  - `phone_numbers: list[FieldConfidence]`
- `PageResult`
  - `page_number: int`
  - `full_text: str`
  - `confidence_score: float`
  - `legibility_issues_detected: bool`
  - `unclear_segments: list[str]`
- `OCRAnalysisResponse`
  - `upload_id: str`
  - `file_name: str`
  - `file_hash: str`
  - `is_duplicate: bool`
  - `duplicate_of_upload_id: str | None`
  - `duplicate_of_filename: str | None`
  - `total_pages: int`
  - `full_text: str`
  - `confidence_score: float`
  - `requires_human_review: bool`
  - `review_reasons: list[str]`
  - `entities: ExtractedEntities`
  - `pages: list[PageResult]`
- `ErrorResponse`
  - `error: str`
  - `message: str`
  - `details: str | None`

Use `Field(..., ge=0, le=1)` for confidence fields.

### `app/db/sqlite_store.py`

Implement a lightweight SQLite store.

Requirements:

- Create DB/table automatically on startup.
- Table `uploads` columns:
  - `upload_id TEXT PRIMARY KEY`
  - `file_hash TEXT NOT NULL`
  - `filename TEXT NOT NULL`
  - `created_at TEXT NOT NULL`
- Index on `file_hash`.
- Functions/methods:
  - `init_db()`
  - `find_by_hash(file_hash: str) -> dict | None`
  - `register_upload(file_hash: str, filename: str) -> dict`
- Use UUID4 for `upload_id`.

### `app/services/hash_service.py`

Implement:

- `calculate_sha256(file_bytes: bytes) -> str`

### `app/services/pdf_service.py`

Use `fitz` / PyMuPDF.

Implement:

- `PDFProcessingError(Exception)`
- `pdf_bytes_to_images(file_bytes: bytes) -> list[PIL.Image.Image]`

Requirements:

- Open PDF from bytes.
- Reject encrypted PDFs.
- Reject zero-page PDFs.
- Render every page at 200 DPI.
- Convert each page to RGB PIL Image.
- Convert corrupt PDFs into `PDFProcessingError` with a clear message.
- Always close the PyMuPDF document.

### `app/services/image_service.py`

Implement:

- `ImageProcessingError(Exception)`
- `image_bytes_to_image(file_bytes: bytes) -> PIL.Image.Image`

Requirements:

- Verify image integrity.
- Reopen after verify.
- Convert to RGB.
- Raise clear `ImageProcessingError` on unreadable/corrupt images.

### `app/services/entity_extractor.py`

Implement regex extraction for:

- emails
- phone numbers
- dates

Requirements:

- Return `ExtractedEntities`.
- Deduplicate while preserving order.
- Each extracted field should have confidence score `0.95` unless it contains `[illegible]`, in which case `0.30` and `requires_human_review=True`.
- Date patterns should support:
  - `MM/DD/YYYY`
  - `DD-MM-YYYY`
  - `YYYY-MM-DD`
  - `January 5, 2026`
  - abbreviated months
- Phone pattern should support fictional/demo numbers such as `555-0198`, `(555) 013-4455`, and `+1-555-019-2834`.

### `app/services/ocr_service.py`

Implement OCR service with strict model prompt and mock fallback.

Requirements:

- `OCRServiceError(Exception)`
- `OCRService`
  - Constructor reads `OPENAI_API_KEY`, `OPENAI_MODEL`, timeout from settings.
  - If API key is missing, run mock mode.
  - `process_image_page(image: PIL.Image.Image, page_number: int) -> PageResult`
- Convert image to base64 PNG.
- Use OpenAI Chat Completions vision API.
- Set low temperature.
- Request JSON output only.
- Parse safely.
- Clamp confidence to `0.0`-`1.0`.
- If API is unreachable, raise `OCRServiceError` and let API return graceful HTTP error.

Prompt must include:

```text
You are a careful handwriting OCR engine for general letters and notes.
Transcribe visible printed and handwritten text exactly.
Do not guess. Do not invent missing words, names, dates, emails, or phone numbers.
If text is unclear, write [illegible] in the transcription and list the unclear segment.
Preserve line breaks and paragraph structure.
Return JSON only with keys: full_text, confidence_score, legibility_issues_detected, unclear_segments.
Confidence must reflect readability, blur, skew, shadows, cropping, and handwriting ambiguity.
```

Mock mode:

- Return deterministic demo text based on page number:
  - `"[MOCK OCR OUTPUT] Configure OPENAI_API_KEY for real handwriting recognition."`
  - confidence `0.88`
  - no legibility issues
- This allows tests and local startup without secrets.

### `app/main.py`

Implement the full FastAPI app.

Endpoints:

- `GET /`
  - Render `index.html`.
- `GET /health`
  - Return service health JSON.
- `POST /api/digitize`
  - Accept file upload.
  - Validate extension.
  - Validate file is non-empty.
  - Validate file size <= `MAX_FILE_SIZE_MB`.
  - Calculate SHA-256.
  - Check duplicate in SQLite before registering.
  - Register upload.
  - Convert PDF or image to list of PIL images.
  - OCR each page sequentially.
  - Combine multi-page text as:
    - `--- Page 1 ---\n...\n\n--- Page 2 ---\n...`
  - Extract entities from combined text.
  - Average page confidence.
  - Human review required if:
    - duplicate upload
    - average confidence below threshold
    - any page has `legibility_issues_detected=True`
    - any page has unclear segments
    - OCR service failed
  - Return `OCRAnalysisResponse`.

Error handling:

- Unsupported file: HTTP 400.
- Empty file: HTTP 400.
- Oversized file: HTTP 413.
- Corrupt PDF/image: HTTP 400.
- OCR service failure: HTTP 503.
- Unexpected failure: HTTP 500 with generic safe message.

Add global exception handlers for `HTTPException` and generic `Exception` that return structured JSON matching `ErrorResponse`.

Mount static files and templates.

### `app/templates/index.html`

Build a polished web UI with Tailwind CDN and plain JS.

UI requirements:

- Dark modern dashboard.
- Large upload dropzone.
- Supports click upload and drag/drop.
- Shows selected filename.
- Shows loading spinner/progress state.
- Shows graceful error alert.
- Shows duplicate warning when duplicate detected.
- Shows large `HUMAN REVIEW REQUIRED` banner when required.
- Shows confidence percentage with green/yellow/red styling.
- Shows total pages.
- Shows extracted dates, emails, and phones as chips with confidence percentages.
- Shows editable `textarea` containing full OCR output.
- Copy-to-clipboard button.
- Shows per-page confidence/unclear segments.
- Include demo guidance panel listing the required scenarios.

Use external scripts only from CDN; no build step.

### `app/static/js/app.js`

Put UI JavaScript here instead of inline if possible.

Requirements:

- Handle drag/drop.
- Submit `FormData` to `/api/digitize`.
- Render results.
- Render errors.
- Copy text.
- Reset file input after upload.

### `app/static/css/styles.css`

Add small custom CSS for:

- dropzone hover state
- confidence bar
- textarea resizing
- subtle animations

### `generate_test_docs.py`

Generate all eight mandatory fictional test documents and `ground_truth.json`.

Important: Use only fictional names and safe general letters/notes. No real personal data. No medical/prescription data.

Use `Pillow` and `PyMuPDF`.

Create these exact files in `test_data/`:

1. `01_legible_handwritten_letter.png`
   - Clearly legible handwritten-style letter.
   - Text:
     ```text
     Dear Morgan,
     Thank you for the garden club notes.
     I will bring the seed catalog on Saturday.
     Warmly,
     Riley
     ```
   - Human review: false.

2. `02_multipage_letter.pdf`
   - Two-page PDF.
   - Page 1:
     ```text
     Dear Taylor,
     This is page one of a fictional multi-page letter.
     The community art plan looks ready for review.
     ```
   - Page 2:
     ```text
     Page two continues the same letter.
     Please send final comments by 2026-08-15.
     Sincerely,
     Jordan
     ```
   - Human review: false.
   - Extract date `2026-08-15`.

3. `03_skewed_shadow_photo.jpg`
   - Smartphone-style photo with skew and shadow.
   - Text:
     ```text
     Workshop Notes
     Bring blue markers and blank cards.
     Meet near the library entrance.
     ```
   - Human review: true because skew/shadows.

4. `04_hard_to_read_handwriting.png`
   - Blurred/low contrast hard-to-read handwriting.
   - Text should contain a few intentionally unclear words represented in ground truth as `[illegible]`.
   - Human review: true.

5. `05_printed_with_handwritten_additions.png`
   - Printed letter with blue handwritten-style additions.
   - Printed text:
     ```text
     COMMUNITY ROOM BOOKING
     Status: Pending
     ```
   - Handwritten addition:
     ```text
     Approved by Casey on 12/05/2026
     ```
   - Human review: false.
   - Extract date `12/05/2026`.

6. `06_contact_details_letter.png`
   - Letter containing fictional phone and email.
   - Text:
     ```text
     Hello Avery,
     Please contact notes@example.test or call +1-555-019-2834.
     Backup desk number: (555) 013-4455.
     Date: August 1, 2026
     ```
   - Human review: false.
   - Extract email `notes@example.test`, phones `+1-555-019-2834`, `(555) 013-4455`, date `August 1, 2026`.

7. `07_corrupt_unreadable.pdf`
   - Write invalid PDF bytes.
   - Expected outcome: graceful error, human review true.

8. `08_duplicate_of_legible.png`
   - Binary duplicate copy of `01_legible_handwritten_letter.png`.
   - Expected outcome when uploaded after file 1: duplicate true, human review true due to duplicate.

Ground truth JSON must include for each file:

- `description`
- `expected_text`
- `expected_entities`
- `requires_human_review`
- `notes`

Make generated image text visually realistic enough for demo:

- Use available system fonts where possible.
- Fall back to PIL default if needed.
- Add mild rotation/noise for handwritten-style examples.
- Add strong blur/low contrast only for hard-to-read case.
- Add shadow gradient for skewed photo.

### `tests/test_api.py`

Include tests for:

- `GET /health` returns 200.
- Unsupported `.txt` upload returns 400.
- Empty file returns 400.
- Oversized file returns 413.
- Corrupt PDF returns 400 and does not crash.
- Valid generated PNG returns 200 in mock mode.
- Duplicate upload: upload same bytes twice, second response has `is_duplicate=True` and `requires_human_review=True`.

Use temporary DB path if possible so tests are isolated.

### `tests/test_entities.py`

Test extraction of:

- email `notes@example.test`
- phone `+1-555-019-2834`
- phone `(555) 013-4455`
- date `2026-08-15`
- date `12/05/2026`
- date `August 1, 2026`

### `tests/test_hash_duplicates.py`

Test SHA-256 deterministic behavior and SQLite duplicate lookup/register behavior.

### `Dockerfile`

Use `python:3.11-slim`.

Requirements:

- Install OS libs needed by Pillow/PyMuPDF if necessary.
- Install requirements.
- Copy project.
- Run `python generate_test_docs.py` at build time.
- Expose `8000`.
- Start with:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### `docker-compose.yml`

Expose local app on `8000:8000`.

Read `.env`.

Mount project directory for local development.

### `render.yaml`

Create a Render Blueprint service:

- Type: web
- Runtime: docker
- Health check path: `/health`
- Environment variable placeholders for `OPENAI_API_KEY`, `OPENAI_MODEL`, `CONFIDENCE_THRESHOLD`, `MAX_FILE_SIZE_MB`.

### `README.md`

Write a complete README with these sections:

1. Project overview.
2. Live demo URL placeholder.
3. Git repository URL placeholder.
4. Features checklist mapped to requirements.
5. Architecture.
6. Model choice:
   - Explain OpenAI `gpt-4o-mini` / `gpt-4o` Vision.
   - Explain why it is better than basic OCR for handwriting, skew, mixed printed/handwritten text.
   - Explain mock mode if no API key is configured.
7. Setup locally with Python.
8. Setup locally with Docker Compose.
9. Environment variables.
10. Running tests.
11. Generating test documents.
12. Test data + ground truth summary table for all 8 cases.
13. Deployment to Render/Railway.
14. API documentation endpoints.
15. Security notes:
    - no secrets in code
    - file size validation
    - no login required by task
    - fictional data only
16. Known limitations:
    - vision API required for real handwriting quality
    - confidence scores are model-estimated
    - SQLite is suitable for demo, use managed DB for production
17. Five-minute live demo script covering:
    - standard letter
    - uncertain case
    - multi-page document
    - error scenario
    - duplicate upload

## API Response Behavior Details

For a successful upload, response shape must look like:

```json
{
  "upload_id": "uuid",
  "file_name": "example.png",
  "file_hash": "sha256",
  "is_duplicate": false,
  "duplicate_of_upload_id": null,
  "duplicate_of_filename": null,
  "total_pages": 1,
  "full_text": "--- Page 1 ---\n...",
  "confidence_score": 0.92,
  "requires_human_review": false,
  "review_reasons": [],
  "entities": {
    "dates": [],
    "emails": [],
    "phone_numbers": []
  },
  "pages": []
}
```

For errors, response shape must look like:

```json
{
  "error": "Bad Request",
  "message": "PDF Error: Corrupt or invalid PDF file.",
  "details": null
}
```

## Human Review Logic

Implement exact human review reasons:

- `Duplicate upload detected.`
- `Overall confidence is below configured threshold.`
- `Legibility issues detected on page X.`
- `Unclear text detected on page X: ...`
- `OCR service is unavailable.`

## Final Verification Checklist

Before finishing, run or ensure:

```bash
python generate_test_docs.py
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then confirm:

- App loads at `/`.
- `/health` returns healthy.
- `/docs` shows FastAPI docs.
- Upload of generated PNG works in mock mode without API key.
- Duplicate detection works.
- Corrupt PDF returns graceful UI/API error.
- README is complete.
- No API keys are committed.

## Extra Scoring Improvements

If time permits, add these polish items:

- Per-page result accordion in UI.
- Confidence color coding:
  - `>= 0.85` green
  - `0.70-0.84` amber
  - `< 0.70` red
- Download transcript as `.txt` button.
- Download JSON result button.
- Include a `Makefile` with `install`, `test`, `run`, and `generate-test-data` commands.

Build the complete application now. Do not only provide snippets. Create all files, tests, docs, and configuration in the repository.
