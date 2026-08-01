import base64
import io
import json

import numpy as np
from PIL import Image

from app.core.config import settings
from app.models.schemas import PageResult


class OCRServiceError(Exception):
    pass


class OCRService:
    def __init__(self) -> None:
        self.engine = settings.OCR_ENGINE.strip().lower()
        self.api_key = settings.OPENAI_API_KEY.strip()
        self.gemini_api_key = settings.GEMINI_API_KEY.strip()
        self.model = settings.OPENAI_MODEL
        self.gemini_model_name = settings.GEMINI_MODEL
        self.client = None
        self.gemini_model = None
        self.easyocr_reader = None
        if self.engine not in {"openai", "gemini", "easyocr", "mock"}:
            self.engine = "mock"

    def _init_openai(self) -> None:
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key, timeout=settings.OCR_TIMEOUT_SECONDS)
        except Exception as exc:
            raise OCRServiceError(f"OpenAI client could not be initialized: {exc}") from exc

    def _init_gemini(self) -> None:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
        except Exception as exc:
            raise OCRServiceError(f"Gemini client could not be initialized: {exc}") from exc

    def _init_easyocr(self) -> None:
        try:
            import easyocr

            self.easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception as exc:
            raise OCRServiceError(
                "EasyOCR is not available. Install it with `pip install easyocr` or set OCR_ENGINE=mock/openai. "
                f"Original error: {exc}"
            ) from exc

    @property
    def active_mode(self) -> str:
        if self.engine == "easyocr":
            return "easyocr"
        if self.engine == "openai" and self.api_key:
            return "openai"
        if self.engine == "gemini" and self.gemini_api_key:
            return "gemini"
        return "mock"

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
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def process_image_page(self, image: Image.Image, page_number: int) -> PageResult:
        if self.active_mode == "easyocr":
            if self.easyocr_reader is None:
                self._init_easyocr()
            return self._process_with_easyocr(image, page_number)
        if self.active_mode == "openai":
            if self.client is None:
                self._init_openai()
            return self._process_with_openai(image, page_number)
        if self.active_mode == "gemini":
            if self.gemini_model is None:
                self._init_gemini()
            return self._process_with_gemini(image, page_number)
        return PageResult(
            page_number=page_number,
            full_text="[MOCK OCR OUTPUT] Configure OPENAI_API_KEY for OpenAI OCR, GEMINI_API_KEY with OCR_ENGINE=gemini, or set OCR_ENGINE=easyocr for free local OCR.",
            confidence_score=0.88,
            legibility_issues_detected=False,
            unclear_segments=[],
        )

    def _process_with_easyocr(self, image: Image.Image, page_number: int) -> PageResult:
        if self.easyocr_reader is None:
            raise OCRServiceError("EasyOCR reader is not initialized.")
        try:
            image_array = np.array(image.convert("RGB"))
            results = self.easyocr_reader.readtext(image_array, detail=1, paragraph=False)
            lines = []
            confidences = []
            unclear_segments = []
            for result in results:
                text = str(result[1]).strip()
                confidence = self._clamp_confidence(result[2])
                if not text:
                    continue
                if confidence < 0.45:
                    unclear_segments.append(text)
                    text = "[illegible]"
                lines.append(text)
                confidences.append(confidence)
            full_text = "\n".join(lines).strip()
            if not full_text:
                full_text = "[illegible]"
                unclear_segments.append("No readable text detected by EasyOCR.")
                confidences.append(0.2)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.2
            return PageResult(
                page_number=page_number,
                full_text=full_text,
                confidence_score=round(self._clamp_confidence(avg_confidence), 2),
                legibility_issues_detected=bool(unclear_segments) or avg_confidence < settings.CONFIDENCE_THRESHOLD,
                unclear_segments=unclear_segments,
            )
        except Exception as exc:
            raise OCRServiceError(f"EasyOCR processing failed on page {page_number}: {exc}") from exc

    def _process_with_gemini(self, image: Image.Image, page_number: int) -> PageResult:
        if self.gemini_model is None:
            raise OCRServiceError("Gemini model is not initialized.")
        prompt = """You are a careful handwriting OCR engine for general letters and notes.
Transcribe visible printed and handwritten text exactly.
Do not guess. Do not invent missing words, names, dates, emails, or phone numbers.
If text is unclear, write [illegible] in the transcription and list the unclear segment.
Preserve line breaks and paragraph structure.
Return JSON only with keys: full_text, confidence_score, legibility_issues_detected, unclear_segments.
Confidence must be a number from 0.0 to 1.0."""
        try:
            response = self.gemini_model.generate_content(
                [prompt, image.convert("RGB")],
                generation_config={"response_mime_type": "application/json", "temperature": 0.0},
            )
            parsed = json.loads(response.text or "{}")
            unclear = parsed.get("unclear_segments", [])
            if not isinstance(unclear, list):
                unclear = [str(unclear)]
            return PageResult(
                page_number=page_number,
                full_text=str(parsed.get("full_text", "")),
                confidence_score=self._clamp_confidence(parsed.get("confidence_score", 0.5)),
                legibility_issues_detected=bool(parsed.get("legibility_issues_detected", False)),
                unclear_segments=[str(item) for item in unclear],
            )
        except Exception as exc:
            raise OCRServiceError(f"Gemini OCR service is unavailable: {exc}") from exc

    def _process_with_openai(self, image: Image.Image, page_number: int) -> PageResult:
        prompt = """You are a careful handwriting OCR engine for general letters and notes.
Transcribe visible printed and handwritten text exactly.
Do not guess. Do not invent missing words, names, dates, emails, or phone numbers.
If text is unclear, write [illegible] in the transcription and list the unclear segment.
Preserve line breaks and paragraph structure.
Return JSON only with keys: full_text, confidence_score, legibility_issues_detected, unclear_segments.
Confidence must reflect readability, blur, skew, shadows, cropping, and handwriting ambiguity."""
        base64_image = self._encode_image(image)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            unclear = parsed.get("unclear_segments", [])
            if not isinstance(unclear, list):
                unclear = [str(unclear)]
            return PageResult(
                page_number=page_number,
                full_text=str(parsed.get("full_text", "")),
                confidence_score=self._clamp_confidence(parsed.get("confidence_score", 0.5)),
                legibility_issues_detected=bool(parsed.get("legibility_issues_detected", False)),
                unclear_segments=[str(item) for item in unclear],
            )
        except Exception as exc:
            raise OCRServiceError(f"OCR service is unavailable: {exc}") from exc


ocr_service = OCRService()
