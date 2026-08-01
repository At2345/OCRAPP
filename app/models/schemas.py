from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FieldConfidence(BaseModel):
    value: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_human_review: bool = False


class ExtractedEntities(BaseModel):
    dates: list[FieldConfidence] = []
    emails: list[FieldConfidence] = []
    phone_numbers: list[FieldConfidence] = []


class PageResult(BaseModel):
    page_number: int
    full_text: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    legibility_issues_detected: bool = False
    unclear_segments: list[str] = []


class OCRAnalysisResponse(BaseModel):
    upload_id: str
    file_name: str
    file_hash: str
    is_duplicate: bool = False
    duplicate_of_upload_id: Optional[str] = None
    duplicate_of_filename: Optional[str] = None
    total_pages: int
    full_text: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_human_review: bool
    review_reasons: list[str] = []
    entities: ExtractedEntities
    pages: list[PageResult]


class PDFExportRequest(BaseModel):
    file_name: str = "digitized-document.pdf"
    title: str = "Digitized Document"
    text: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[str] = None
