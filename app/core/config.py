from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Handwriting OCR Digitizer"
    DEBUG: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OCR_ENGINE: str = "openai"
    CONFIDENCE_THRESHOLD: float = 0.80
    MAX_FILE_SIZE_MB: int = 15
    DATABASE_PATH: str = "./ocr_uploads.sqlite3"
    OCR_TIMEOUT_SECONDS: int = 60
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
