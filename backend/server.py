"""Supervisor entrypoint: exposes the FastAPI OCR app on the backend port (8001).

The application code lives in /app/app. This shim makes it importable and loads
environment variables from /app/.env regardless of the working directory.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app")
load_dotenv("/app/.env")

from app.main import app  # noqa: E402,F401
