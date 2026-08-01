from app.db import sqlite_store
from app.services.hash_service import calculate_sha256


def test_sha256_is_deterministic():
    payload = b"fictional document bytes"
    assert calculate_sha256(payload) == calculate_sha256(payload)
    assert calculate_sha256(payload) != calculate_sha256(b"different")


def test_sqlite_register_and_find_duplicate(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(sqlite_store.settings, "DATABASE_PATH", str(db_path))
    sqlite_store.init_db()
    first = sqlite_store.register_upload("abc123", "one.png")
    found = sqlite_store.find_by_hash("abc123")
    assert found is not None
    assert found["upload_id"] == first["upload_id"]
    assert found["filename"] == "one.png"
