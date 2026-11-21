from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES users(id), title TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES users(id), project_id TEXT NOT NULL REFERENCES projects(id),
 filename TEXT NOT NULL, media_type TEXT NOT NULL, stored_path TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS text_segments (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES users(id), project_id TEXT NOT NULL REFERENCES projects(id),
 document_id TEXT NOT NULL REFERENCES documents(id), chapter INTEGER NOT NULL, ordinal INTEGER NOT NULL,
 original_text TEXT NOT NULL, normalized_text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', audio_path TEXT,
 created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS segment_order ON text_segments(document_id, ordinal);
CREATE TABLE IF NOT EXISTS generation_jobs (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES users(id), segment_id TEXT NOT NULL REFERENCES text_segments(id),
 status TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 10, error TEXT, created_at TEXT NOT NULL, finished_at TEXT,
 speaker TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS voice_profiles (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
 audio_path TEXT NOT NULL, reference_text TEXT NOT NULL, duration_seconds REAL NOT NULL,
 consented_at TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.executescript(SCHEMA)
            columns = {row["name"] for row in con.execute("PRAGMA table_info(generation_jobs)").fetchall()}
            if "speaker" not in columns:
                con.execute("ALTER TABLE generation_jobs ADD COLUMN speaker TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
