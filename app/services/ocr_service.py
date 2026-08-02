from __future__ import annotations

import base64
import io
import json
import re
import uuid

from PIL import Image

from app.core.config import settings
from app.models.schemas import PageResult

OCR_SYSTEM_PROMPT = """You are a careful handwriting OCR engine for general letters and notes.
Transcribe visible printed and handwritten text exactly.
Do not guess. Do not invent missing words, names, dates, emails, or phone numbers.
If text is unclear, write [illegible] in the transcription and list the unclear segment.
Preserve line breaks and paragraph structure.
Return JSON only (no markdown, no code fences) with keys: full_text, confidence_score, legibility_issues_detected, unclear_segments.
confidence_score must be a number from 0.0 to 1.0 reflecting readability, blur, skew, shadows, cropping, and handwriting ambiguity.
unclear_segments must be a list of strings."""

# provider -> (emergentintegrations provider name, model name)
PROVIDER_MODELS: dict[str, tuple[str, str]] = {
    "openai": ("openai", settings.OPENAI_MODEL),
    "anthropic": ("anthropic", settings.ANTHROPIC_MODEL),
}

PROVIDER_ALIASES = {
    "openai": "openai",
    "gpt": "openai",
    "chatgpt": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
}


class OCRServiceError(Exception):
    pass


class OCRService:
    def __init__(self) -> None:
        self.api_key = settings.EMERGENT_LLM_KEY.strip()

    @property
    def available_providers(self) -> list[str]:
        return list(PROVIDER_MODELS.keys()) if self.api_key else []

    @property
    def default_provider(self) -> str:
        return self.resolve_provider(settings.OCR_PROVIDER)

    @staticmethod
    def resolve_provider(provider: str | None) -> str:
        candidate = (provider or settings.OCR_PROVIDER or "openai").strip().lower()
        resolved = PROVIDER_ALIASES.get(candidate, candidate)
        if resolved not in PROVIDER_MODELS:
            resolved = "openai"
        return resolved

    @staticmethod
    def model_for(provider: str) -> str:
        return PROVIDER_MODELS[provider][1]

    @staticmethod
    def _clamp_confidence(value: object) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.5
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _encode_image(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        # Fall back to treating the whole response as transcribed text.
        return {
            "full_text": text,
            "confidence_score": 0.5,
            "legibility_issues_detected": True,
            "unclear_segments": [],
        }

    async def process_image_page(
        self, image: Image.Image, page_number: int, provider: str | None = None
    ) -> PageResult:
        if not self.api_key:
            raise OCRServiceError(
                "EMERGENT_LLM_KEY is not configured. Set it in /app/.env to enable OCR."
            )

        resolved = self.resolve_provider(provider)
        emergent_provider, model = PROVIDER_MODELS[resolved]

        try:
            from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage
        except Exception as exc:  # pragma: no cover - import guard
            raise OCRServiceError(f"OCR engine library is unavailable: {exc}") from exc

        chat = LlmChat(
            api_key=self.api_key,
            session_id=str(uuid.uuid4()),
            system_message=OCR_SYSTEM_PROMPT,
        ).with_model(emergent_provider, model)

        message = UserMessage(
            text="Transcribe every visible printed and handwritten word on this page. Return JSON only.",
            file_contents=[ImageContent(image_base64=self._encode_image(image))],
        )

        try:
            raw = await chat.send_message(message)
        except Exception as exc:
            raise OCRServiceError(f"{resolved} OCR service is unavailable: {exc}") from exc

        parsed = self._parse_json(raw)
        unclear = parsed.get("unclear_segments", [])
        if not isinstance(unclear, list):
            unclear = [str(unclear)]

        return PageResult(
            page_number=page_number,
            full_text=str(parsed.get("full_text", "")),
            confidence_score=self._clamp_confidence(parsed.get("confidence_score", 0.5)),
            legibility_issues_detected=bool(parsed.get("legibility_issues_detected", False)),
            unclear_segments=[str(item) for item in unclear if str(item).strip()],
        )


ocr_service = OCRService()
