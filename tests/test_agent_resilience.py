import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app import agent, jobs, store


def test_concurrent_application_requests_create_one_record(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "concurrent.db")
    store.init_db(); sid = str(uuid.uuid4()); store.session(sid)
    with ThreadPoolExecutor(max_workers=5) as executor:
        records = list(executor.map(lambda _: store.create_application(sid, "same-job"), range(10)))
    assert len(store.applications(sid)) == 1
    assert sum(not record["duplicate"] for record in records) == 1
    assert len({record["applied_at"] for record in records}) == 1


@pytest.mark.parametrize("arguments", ['not JSON', '{"intent":"delete_everything"}', '{"intent":"apply","reference":-3}', '{"intent":"apply","extra":"bad"}'])
def test_invalid_llm_arguments_are_rejected(monkeypatch, arguments):
    import openai
    call = SimpleNamespace(function=SimpleNamespace(name="route_job_request", arguments=arguments))
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: response)))
    monkeypatch.setattr(openai, "OpenAI", lambda **_: fake)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    assert agent._llm_intent("some request", []) is None


def test_provider_failure_keeps_local_router_working(tmp_path, monkeypatch):
    import openai
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "fallback.db")
    store.init_db()
    def unavailable(**_):
        raise TimeoutError("test provider outage")
    monkeypatch.setattr(openai, "OpenAI", unavailable)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    result = agent.respond(str(uuid.uuid4()), "something ambiguous")
    assert result["router"] == "rules" and result["reply"]


def test_expired_job_cannot_start_application(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "expired.db")
    store.init_db(); sid = str(uuid.uuid4()); store.session(sid)
    store.update_session(sid, profile={"name": "Sample"}, last_jobs=[jobs.catalogue()[0]["id"]])
    monkeypatch.setattr(jobs, "is_active", lambda _: False)
    result = agent.respond(sid, "apply to job 1")
    assert "expired" in result["reply"] and not store.applications(sid)


def test_filter_removal_and_false_remote_are_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "filters.db")
    store.init_db(); sid = str(uuid.uuid4())
    agent.respond(sid, "remote React jobs in India")
    agent.respond(sid, "clear skill filter")
    state = store.session(sid)
    assert "skills" not in state["filters"] and state["filters"]["location"] == "India"
    agent.respond(sid, "show onsite roles")
    assert store.session(sid)["filters"]["remote"] is False
    agent.respond(sid, "clear remote filter")
    assert "remote" not in store.session(sid)["filters"]


def test_existing_database_migrates_without_losing_application(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE sessions(id TEXT PRIMARY KEY,profile_json TEXT,filters_json TEXT DEFAULT '{}',last_jobs_json TEXT DEFAULT '[]',updated_at TEXT);
        CREATE TABLE applications(session_id TEXT,job_id TEXT,status TEXT,applied_at TEXT,updated_at TEXT,PRIMARY KEY(session_id,job_id));
        CREATE TABLE messages(id INTEGER PRIMARY KEY,session_id TEXT,role TEXT,content TEXT,created_at TEXT);
        INSERT INTO sessions VALUES('sample',NULL,'{}','[]','2026-10-21T00:00:00+00:00');
        INSERT INTO applications VALUES('sample','job-1','submitted','2026-10-20T00:00:00+00:00','2026-10-21T00:00:00+00:00');
    """)
    db.commit(); db.close()
    monkeypatch.setattr(store, "DB_PATH", path)
    store.init_db()
    record = store.applications("sample")[0]
    assert record["job_id"] == "job-1"
    assert record["created_at"] == "2026-10-20T00:00:00+00:00"
    assert record["submitted_at"] == record["applied_at"] == "2026-10-21T00:00:00+00:00"
