# Handwriting OCR Digitizer — PRD

## Original Request
"Implement the best OCR models and delete gemini and easyocr; let me test it."

## Architecture
- FastAPI + Jinja2 monolith in `/app/app` (UI + API in one app).
- Runs under this pod's supervisor via two shims:
  - `/app/backend/server.py` → serves API on port 8001 (preview `/api/*`).
  - `/app/frontend/package.json` `start` → runs same uvicorn app on port 3000 (preview `/`).
- Config loaded from `/app/.env` (absolute) via pydantic-settings.
- Persistence: SQLite at `/app/ocr_uploads.sqlite3` (SHA-256 duplicate detection).

## OCR Engines (2026-08-02)
- Powered by Emergent Universal LLM key (`EMERGENT_LLM_KEY`) via `emergentintegrations`.
- **OpenAI** vision — default model `gpt-5.4`.
- **Anthropic Claude** vision — `claude-sonnet-4-6`.
- Per-upload provider toggle in the UI; `provider` form field on `POST /api/digitize`.
- REMOVED: Gemini, EasyOCR, and mock OCR mode (also deleted `requirements-free-ocr.txt`, `.env.free.example`).
- Strict no-guess prompt; `[illegible]` for unclear text; JSON output parsed with fallback.

## Implemented
- OCR service rewrite (`app/services/ocr_service.py`) with OpenAI + Claude + provider resolver.
- Config, schemas (`ocr_provider`/`ocr_model` in response), main.py (`provider` Form param, `/health` reports providers/models), UI toggle (index.html + app.js).
- Fixed Starlette `TemplateResponse(request, name, ctx)` signature.
- Updated README, `.env.example`, `render.yaml`; updated `tests/test_api.py` (mocks OCR, tests provider echo + duplicates).

## Verified
- 9/9 pytest pass.
- Live OpenAI OCR: exact transcription, conf 0.99.
- Live Claude OCR: correct transcription + `[illegible]` on unclear digit, conf 0.82.
- UI loads with working OpenAI/Claude toggle.

## Preview Fix (2026-08-02)
- Root cause of "preview does not work": frontend (3000) + backend (8001) were both FATAL/unconfigured before this session.
- Fix: `/app/backend/server.py` (API on 8001) + `/app/frontend/package.json` start=uvicorn on 3000 serving same monolith; fixed Starlette `TemplateResponse(request, name, ctx)` signature.
- Testing agent: 100% backend + 100% frontend E2E via preview URL. retest_needed=false.

## Backlog / Next
- P1: Show active engine + timing badge on the result panel.
- P2: Side-by-side OpenAI vs Claude comparison view.
- P2: Allow model dropdown (e.g. gpt-5.6, claude-opus) in the UI.
