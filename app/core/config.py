from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Handwriting OCR Digitizer"
    DEBUG: bool = False

    # Emergent Universal LLM key powers both OpenAI and Anthropic vision OCR.
    EMERGENT_LLM_KEY: str = ""
    OCR_PROVIDER: str = "openai"  # default engine: "openai" or "anthropic"
    OPENAI_MODEL: str = "gpt-5.4"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    CONFIDENCE_THRESHOLD: float = 0.80
    MAX_FILE_SIZE_MB: int = 15
    DATABASE_PATH: str = "/app/ocr_uploads.sqlite3"
    OCR_TIMEOUT_SECONDS: int = 60
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png")

    model_config = SettingsConfigDict(env_file="/app/.env", extra="ignore")


settings = Settings()
