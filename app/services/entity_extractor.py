from __future__ import annotations

import re

from app.models.schemas import ExtractedEntities, FieldConfidence


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]\d{4}|\b\d{3}[-.]\d{4}\b"
)
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            output.append(normalized)
    return output


def _field(value: str) -> FieldConfidence:
    low_confidence = "[illegible]" in value.lower()
    return FieldConfidence(
        value=value,
        confidence_score=0.30 if low_confidence else 0.95,
        requires_human_review=low_confidence,
    )


def extract_entities(text: str) -> ExtractedEntities:
    return ExtractedEntities(
        dates=[_field(value) for value in _dedupe(DATE_PATTERN.findall(text))],
        emails=[_field(value) for value in _dedupe(EMAIL_PATTERN.findall(text))],
        phone_numbers=[_field(value) for value in _dedupe(PHONE_PATTERN.findall(text))],
    )
