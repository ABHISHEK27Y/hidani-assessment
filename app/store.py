"""Anonymous session and application persistence with SQLite."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "data/app.db"))


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            profile_json TEXT,
            filters_json TEXT NOT NULL DEFAULT '{}',
            last_jobs_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS applications (
            session_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('awaiting_submission','submitted')),
            applied_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(session_id, job_id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        """)


def _now():
    return datetime.now(timezone.utc).isoformat()


def session(session_id: str):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO sessions(id, updated_at) VALUES (?, ?)", (session_id, _now()))
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    return {
        "profile": json.loads(row["profile_json"]) if row["profile_json"] else None,
        "filters": json.loads(row["filters_json"]),
        "last_jobs": json.loads(row["last_jobs_json"]),
    }


def update_session(session_id: str, **fields):
    allowed = {"profile": "profile_json", "filters": "filters_json", "last_jobs": "last_jobs_json"}
    unknown = set(fields) - set(allowed)
    if unknown:
        raise ValueError(f"Unknown session fields: {unknown}")
    if not fields:
        return
    values = {allowed[key]: json.dumps(value) if value is not None else None for key, value in fields.items()}
    clauses = ", ".join(f"{key}=?" for key in values)
    with connect() as db:
        db.execute(f"UPDATE sessions SET {clauses}, updated_at=? WHERE id=?", (*values.values(), _now(), session_id))


def add_message(session_id: str, role: str, content: str):
    with connect() as db:
        db.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)", (session_id, role, content[:4000], _now()))


def history(session_id: str):
    with connect() as db:
        rows = db.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 10", (session_id,)).fetchall()
    return [dict(row) for row in reversed(rows)]


def create_application(session_id: str, job_id: str):
    now = _now()
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO applications(session_id,job_id,status,applied_at,updated_at) VALUES (?,?,?,?,?)", (session_id, job_id, "awaiting_submission", now, now))
        row = db.execute("SELECT * FROM applications WHERE session_id=? AND job_id=?", (session_id, job_id)).fetchone()
    return dict(row)


def confirm_application(session_id: str, job_id: str):
    with connect() as db:
        db.execute("UPDATE applications SET status='submitted', updated_at=? WHERE session_id=? AND job_id=? AND status='awaiting_submission'", (_now(), session_id, job_id))
        row = db.execute("SELECT * FROM applications WHERE session_id=? AND job_id=?", (session_id, job_id)).fetchone()
    return dict(row) if row else None


def applications(session_id: str):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM applications WHERE session_id=? ORDER BY applied_at DESC", (session_id,))]
