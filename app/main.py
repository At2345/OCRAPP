from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.db.sqlite_store import find_by_hash, init_db, register_upload
from app.models.schemas import ErrorResponse, OCRAnalysisResponse, PDFExportRequest
from app.services.entity_extractor import extract_entities
from app.services.hash_service import calculate_sha256
from app.services.image_service import ImageProcessingError, image_bytes_to_image
from app.services.ocr_service import OCRServiceError, ocr_service
from app.services.pdf_export_service import PDFExportError, text_to_pdf_bytes
from app.services.pdf_service import PDFProcessingError, pdf_bytes_to_images


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _error_name(status_code: int) -> str:
    return {
        400: "Bad Request",
        413: "Payload Too Large",
        422: "Validation Error",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }.get(status_code, "Error")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    payload = ErrorResponse(error=_error_name(exc.status_code), message=str(exc.detail), details=None)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    payload = ErrorResponse(error="Validation Error", message="Invalid request payload.", details=str(exc))
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    details = str(exc) if settings.DEBUG else None
    payload = ErrorResponse(error="Internal Server Error", message="Unexpected server error.", details=details)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())


@app.get("/")
def render_index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.APP_NAME,
            "model_catalog": ocr_service.model_catalog(),
            "default_models": ocr_service.default_models(),
            "default_provider": ocr_service.default_provider,
        },
    )


@app.get("/health")
def health_check() -> dict[str, object]:
    default_provider = ocr_service.default_provider
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "ocr_configured": bool(ocr_service.available_providers),
        "available_providers": ocr_service.available_providers,
        "default_provider": default_provider,
        "models": {
            "openai": settings.OPENAI_MODEL,
            "anthropic": settings.ANTHROPIC_MODEL,
        },
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/export/pdf")
def export_pdf(payload: PDFExportRequest) -> StreamingResponse:
    try:
        pdf_bytes = text_to_pdf_bytes(payload.title, payload.text)
    except PDFExportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    filename = Path(payload.file_name or "digitized-document.pdf").stem + ".pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)


@app.post(
    "/api/digitize",
    response_model=OCRAnalysisResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def digitize_document(
    file: UploadFile = File(...),
    provider: str = Form("openai"),
    model: str = Form(""),
) -> OCRAnalysisResponse:
    resolved_provider = ocr_service.resolve_provider(provider)
    resolved_model = ocr_service.resolve_model(resolved_provider, model)
    filename = Path(file.filename or "uploaded_document").name
    extension = Path(filename).suffix.lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{extension}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds {settings.MAX_FILE_SIZE_MB} MB limit.",
        )

    file_hash = calculate_sha256(file_bytes)
    previous_upload = find_by_hash(file_hash)
    current_upload = register_upload(file_hash, filename)
    is_duplicate = previous_upload is not None

    try:
        images = pdf_bytes_to_images(file_bytes) if extension == ".pdf" else [image_bytes_to_image(file_bytes)]
    except PDFProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"PDF Error: {exc}") from exc
    except ImageProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    pages = []
    review_reasons: list[str] = []
    if is_duplicate:
        review_reasons.append("Duplicate upload detected.")

    try:
        for page_number, image in enumerate(images, start=1):
            page = await ocr_service.process_image_page(image, page_number, resolved_provider, resolved_model)
            pages.append(page)
            if page.legibility_issues_detected:
                review_reasons.append(f"Legibility issues detected on page {page_number}.")
            if page.unclear_segments:
                review_reasons.append(f"Unclear text detected on page {page_number}: {', '.join(page.unclear_segments)}")
    except OCRServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OCR service is unavailable.") from exc

    full_text = "\n\n".join(f"--- Page {page.page_number} ---\n{page.full_text}" for page in pages)
    confidence = round(sum(page.confidence_score for page in pages) / len(pages), 2) if pages else 0.0
    if confidence < settings.CONFIDENCE_THRESHOLD:
        review_reasons.append("Overall confidence is below configured threshold.")

    entities = extract_entities(full_text)
    entity_review_required = any(
        item.requires_human_review
        for group in (entities.dates, entities.emails, entities.phone_numbers)
        for item in group
    )
    requires_human_review = bool(review_reasons) or entity_review_required

    return OCRAnalysisResponse(
        upload_id=current_upload["upload_id"],
        file_name=filename,
        file_hash=file_hash,
        ocr_provider=resolved_provider,
        ocr_model=resolved_model,
        is_duplicate=is_duplicate,
        duplicate_of_upload_id=previous_upload["upload_id"] if previous_upload else None,
        duplicate_of_filename=previous_upload["filename"] if previous_upload else None,
        total_pages=len(images),
        full_text=full_text,
        confidence_score=confidence,
        requires_human_review=requires_human_review,
        review_reasons=list(dict.fromkeys(review_reasons)),
        entities=entities,
        pages=pages,
    )
