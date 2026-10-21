"""SQLite persistence with per-session isolation and atomic duplicate protection."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "data/app.db")))


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            yield db
    finally:
        db.close()


def init_db():
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, profile_json TEXT,
            filters_json TEXT NOT NULL DEFAULT '{}',
            last_jobs_json TEXT NOT NULL DEFAULT '[]', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS applications (
            session_id TEXT NOT NULL, job_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('awaiting_submission','submitted')),
            applied_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            created_at TEXT, submitted_at TEXT,
            delivery TEXT NOT NULL DEFAULT 'assisted', receipt TEXT,
            PRIMARY KEY(session_id, job_id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL, created_at TEXT NOT NULL, payload_json TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id);
        """)
        # Non-destructive migration from the first local build.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(applications)")}
        for name, definition in {"created_at": "TEXT", "submitted_at": "TEXT", "delivery": "TEXT NOT NULL DEFAULT 'assisted'", "receipt": "TEXT"}.items():
            if name not in columns:
                db.execute(f"ALTER TABLE applications ADD COLUMN {name} {definition}")
        if "payload_json" not in {row["name"] for row in db.execute("PRAGMA table_info(messages)")}:
            db.execute("ALTER TABLE messages ADD COLUMN payload_json TEXT")
        db.execute("UPDATE applications SET created_at=applied_at WHERE created_at IS NULL")
        db.execute("UPDATE applications SET submitted_at=updated_at, applied_at=updated_at WHERE status='submitted' AND submitted_at IS NULL")


def _now():
    return datetime.now(timezone.utc).isoformat()


def session(session_id: str):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO sessions(id, updated_at) VALUES (?, ?)", (session_id, _now()))
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    return {"profile": json.loads(row["profile_json"]) if row["profile_json"] else None,
            "filters": json.loads(row["filters_json"]), "last_jobs": json.loads(row["last_jobs_json"])}


def update_session(session_id: str, **fields):
    allowed = {"profile": "profile_json", "filters": "filters_json", "last_jobs": "last_jobs_json"}
    if set(fields) - set(allowed):
        raise ValueError("Unknown session field")
    if not fields:
        return
    values = {allowed[key]: json.dumps(value) if value is not None else None for key, value in fields.items()}
    clauses = ", ".join(f"{key}=?" for key in values)
    with connect() as db:
        db.execute(f"UPDATE sessions SET {clauses}, updated_at=? WHERE id=?", (*values.values(), _now(), session_id))


def add_message(session_id: str, role: str, content: str, payload: dict | None = None):
    with connect() as db:
        db.execute("INSERT INTO messages(session_id,role,content,created_at,payload_json) VALUES (?,?,?,?,?)",
                   (session_id, role, content[:4000], _now(), json.dumps(payload) if payload else None))
        db.execute("DELETE FROM messages WHERE session_id=? AND id NOT IN (SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 200)", (session_id, session_id))


def history(session_id: str, limit=40):
    with connect() as db:
        rows = db.execute("SELECT id, role, content, created_at, payload_json FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
    return [{"id": row["id"], "role": row["role"], "content": row["content"], "created_at": row["created_at"],
             "payload": json.loads(row["payload_json"]) if row["payload_json"] else None} for row in reversed(rows)]


def create_application(session_id: str, job_id: str, mode="assisted"):
    now = _now()
    simulated = mode == "simulation"
    receipt = "SIM-" + uuid.uuid4().hex[:12].upper() if simulated else None
    with connect() as db:
        cursor = db.execute("""INSERT OR IGNORE INTO applications
            (session_id,job_id,status,applied_at,updated_at,created_at,submitted_at,delivery,receipt)
            VALUES (?,?,?,?,?,?,?,?,?)""", (session_id, job_id, "submitted" if simulated else "awaiting_submission",
                now, now, now, now if simulated else None, mode, receipt))
        created = cursor.rowcount == 1
        row = db.execute("SELECT * FROM applications WHERE session_id=? AND job_id=?", (session_id, job_id)).fetchone()
    return {**dict(row), "duplicate": not created}


def confirm_application(session_id: str, job_id: str):
    now = _now()
    with connect() as db:
        db.execute("UPDATE applications SET status='submitted', applied_at=?, submitted_at=?, updated_at=? WHERE session_id=? AND job_id=? AND status='awaiting_submission'", (now, now, now, session_id, job_id))
        row = db.execute("SELECT * FROM applications WHERE session_id=? AND job_id=?", (session_id, job_id)).fetchone()
    return dict(row) if row else None


def applications(session_id: str):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM applications WHERE session_id=? ORDER BY created_at DESC", (session_id,))]


def delete_session(session_id: str):
    with connect() as db:
        for table in ("messages", "applications", "sessions"):
            column = "id" if table == "sessions" else "session_id"
            db.execute(f"DELETE FROM {table} WHERE {column}=?", (session_id,))
