from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.DATABASE_PATH)
    if db_path.parent and str(db_path.parent) != ".":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                upload_id TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_uploads_file_hash ON uploads(file_hash)")
        conn.commit()


def find_by_hash(file_hash: str) -> dict | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT upload_id, file_hash, filename, created_at FROM uploads WHERE file_hash = ? ORDER BY created_at ASC LIMIT 1",
            (file_hash,),
        ).fetchone()
    return dict(row) if row else None


def register_upload(file_hash: str, filename: str) -> dict:
    init_db()
    upload = {
        "upload_id": str(uuid.uuid4()),
        "file_hash": file_hash,
        "filename": filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO uploads (upload_id, file_hash, filename, created_at) VALUES (?, ?, ?, ?)",
            (upload["upload_id"], upload["file_hash"], upload["filename"], upload["created_at"]),
        )
        conn.commit()
    return upload
