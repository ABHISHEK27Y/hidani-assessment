"""HTTP contract and state transitions, using isolated local databases."""
import io
import uuid

import fitz
import pytest
from fastapi.testclient import TestClient

from app import agent, jobs, store
from app.main import app, limiter


def resume_pdf():
    document = fitz.open(); page = document.new_page()
    page.insert_text((30, 30), "Sample Candidate\ncandidate@example.test\nWORK EXPERIENCE\nSoftware Engineering Intern June 2026 - August 2026\nBuilt Python APIs and React interfaces.\nEDUCATION\nB.Tech Computer Science\nPROJECTS\nCloudCanvas March 2026 - August 2026\nTECHNICAL SKILLS\nPython React TypeScript AWS Docker")
    result = document.tobytes(); document.close(); return result


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "api.db")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("APPLICATION_MODE", "assisted")
    limiter.events.clear()
    with TestClient(app) as test_client:
        yield test_client


def upload(client, sid):
    response = client.post("/api/resume", data={"session_id": sid}, files={"file": ("sample.pdf", resume_pdf(), "application/pdf")})
    assert response.status_code == 200, response.text
    return response.json()


def chat(client, sid, message, **extra):
    response = client.post("/api/chat", json={"session_id": sid, "message": message, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_page_assets_and_readiness(client):
    for path in ["/", "/static/styles.css", "/static/theme.css", "/static/app.js", "/static/favicon.svg", "/openapi.json"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-request-id"]
    health = client.get("/health").json()
    assert health["ok"] and health["jobs"] == 1800
    assert not health["llm_configured"]


def test_health_reports_selected_provider_without_exposing_key(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-health-key')
    response = client.get('/health')
    assert response.json()['llm_provider'] == 'gemini'
    assert response.json()['llm_model'] == 'gemini-3.8-flash'
    assert response.json()['llm_configured']
    assert 'synthetic-health-key' not in response.text


def test_api_docs_policy_allows_initializer_without_weakening_workspace(client):
    response = client.get("/docs")
    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    nonce = policy.split("'nonce-", 1)[1].split("'", 1)[0]
    assert f'<script nonce="{nonce}">' in response.text
    assert "https://cdn.jsdelivr.net" in policy
    assert "'unsafe-inline'" not in policy.split("script-src", 1)[1].split(";", 1)[0]
    assert "cdn.jsdelivr.net" not in client.get("/").headers["content-security-policy"]
    assert "/api/chat" in client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
def test_chat_validation(client, message):
    assert client.post("/api/chat", json={"session_id": str(uuid.uuid4()), "message": message}).status_code == 422


def test_invalid_sessions_fields_and_jobs(client):
    assert client.get("/api/bootstrap?session_id=broken").status_code == 422
    assert client.post("/api/chat", json={"session_id": "broken", "message": "hi"}).status_code == 422
    assert client.post("/api/chat", json={"session_id": str(uuid.uuid4()), "message": "hi", "unknown": True}).status_code == 422
    assert client.get("/api/jobs/not-a-job").status_code == 404


def test_upload_errors_and_request_limit(client):
    sid = str(uuid.uuid4())
    for filename, content in [("broken.pdf", b"not a pdf"), ("bad.exe", b"x"), ("empty.docx", b"")]:
        assert client.post("/api/resume", data={"session_id": sid}, files={"file": (filename, content)}).status_code == 422
    assert client.post("/api/resume", content=b"x" * (9 * 1024 * 1024)).status_code == 413


def test_resume_refine_apply_duplicate_status_history_and_isolation(client):
    sid = str(uuid.uuid4()); other = str(uuid.uuid4())
    parsed = upload(client, sid)
    assert parsed["profile"]["experience_months"] == 3
    assert parsed["profile"]["designation"] == "Software Engineering Intern"
    assert parsed["jobs"]
    remote = chat(client, sid, "show only remote roles")
    assert remote["jobs"] and all(job["remote"] for job in remote["jobs"])
    refined = chat(client, sid, "jobs needing React")
    assert all("React" in job["skills"] for job in refined["jobs"])
    chat(client, sid, "clear skill filter")
    # A button on an older card keeps its original ID even after refinements.
    job_id = parsed["jobs"][0]["id"]
    application = client.post("/api/applications", json={"session_id": sid, "job_id": job_id}).json()["application"]
    duplicate = client.post("/api/applications", json={"session_id": sid, "job_id": job_id}).json()["application"]
    assert application["status"] == "awaiting_submission"
    assert duplicate["duplicate"] and duplicate["applied_at"] == application["applied_at"]
    confirmed = client.post("/api/applications", json={"session_id": sid, "job_id": job_id, "action": "confirm"}).json()
    assert confirmed["applications"][0]["submitted_at"]
    assert confirmed["applications"][0]["status"] == "submitted"
    restored = client.get("/api/bootstrap", params={"session_id": sid}).json()
    assert restored["profile"]["name"] == "Sample Candidate"
    assert any(item["payload"] and item["payload"].get("jobs") for item in restored["history"])
    assert client.get("/api/applications", params={"session_id": other}).json()["applications"] == []
    assert client.get(f"/api/jobs/{job_id}").json()["description"]
    assert client.delete(f"/api/session/{sid}").json()["ok"]
    cleared = client.get("/api/bootstrap", params={"session_id": sid}).json()
    assert not cleared["history"] and not cleared["profile"] and not cleared["applications"]


def test_profile_corrections_no_match_invalid_refs_and_negated_action(client):
    sid = str(uuid.uuid4()); parsed = upload(client, sid)
    changed = chat(client, sid, "I have 6 months of experience")
    assert changed["profile"]["experience_months"] == 6
    changed = chat(client, sid, "my role is frontend developer")
    assert changed["profile"]["designation"] == "frontend developer"
    none = chat(client, sid, "find zzzimpossiblezzz jobs")
    assert none["total"] == 0 and not none["jobs"]
    invalid = chat(client, sid, "apply to job 999")
    assert "could not identify" in invalid["reply"]
    chat(client, sid, "clear filters")
    chat(client, sid, "do not apply to job 1")
    assert not client.get("/api/applications", params={"session_id": sid}).json()["applications"]


def test_simulated_application_has_explicit_receipt(client, monkeypatch):
    sid = str(uuid.uuid4()); parsed = upload(client, sid)
    monkeypatch.setenv("APPLICATION_MODE", "simulation")
    result = chat(client, sid, "apply to job 1")
    assert result["application"]["delivery"] == "simulation"
    assert result["application"]["receipt"].startswith("SIM-")
    assert "not been sent" in result["reply"]


def test_rate_limit_has_retry_after(client):
    sid = str(uuid.uuid4())
    for _ in range(40):
        assert client.post("/api/chat", json={"session_id": sid, "message": "hi"}).status_code == 200
    response = client.post("/api/chat", json={"session_id": sid, "message": "hi"})
    assert response.status_code == 429 and response.headers["retry-after"] == "60"


def test_unexpected_failure_returns_request_id_not_internal_error(client, monkeypatch):
    def unavailable():
        raise RuntimeError("internal-test-detail")
    monkeypatch.setattr(store, "connect", unavailable)
    response = client.get("/health")
    assert response.status_code == 500
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "internal-test-detail" not in response.text
