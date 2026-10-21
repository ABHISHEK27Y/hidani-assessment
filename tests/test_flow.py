"""Core flow tests without network or an LLM key."""
import uuid
import io
from types import SimpleNamespace

import fitz
from docx import Document

from app import agent, jobs, store
from app.resume import extract_profile, read_resume


def sample_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Asha Mehta\nSoftware Engineer\nasha@example.com\n+91 9876543210\nSkills\nPython React SQL Docker\nExperience\nSoftware Engineer at Acme - built APIs with Python and React for 2 years\nEducation\nB.Tech Computer Science, Example University\nProjects\nJob recommendation engine using Python and React")
    content = doc.tobytes()
    doc.close()
    return content


def test_full_chat_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "app.db")
    store.init_db()
    session_id = str(uuid.uuid4())
    profile = extract_profile(read_resume("resume.pdf", sample_pdf()))
    assert profile["email"] == "asha@example.com"
    assert "Python" in profile["skills"]
    assert len(jobs.catalogue()) == 1800
    store.session(session_id)
    store.update_session(session_id, profile=profile)

    result = agent.respond(session_id, "show only remote roles")
    assert result["jobs"]
    assert all(job["remote"] for job in result["jobs"])
    first_id = result["jobs"][0]["id"]

    apply = agent.respond(session_id, "apply to job 1")
    assert apply["application"]["job_id"] == first_id
    assert apply["application"]["status"] == "awaiting_submission"
    agent.respond(session_id, "apply to job 1")
    assert len(store.applications(session_id)) == 1

    confirmed = agent.respond(session_id, "I submitted job 1")
    assert confirmed["applications"][0]["status"] == "submitted"
    status = agent.respond(session_id, "show my applied jobs")
    assert len(status["applications"]) == 1


def test_bad_resume_and_bad_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "app.db")
    store.init_db()
    session_id = str(uuid.uuid4())
    try:
        read_resume("resume.pdf", b"garbage")
        assert False, "Unreadable PDF should be rejected"
    except ValueError:
        pass
    result = agent.respond(session_id, "apply to job 99")
    assert "could not identify" in result["reply"].lower()


def test_docx_resume_extraction():
    doc = Document()
    for line in ["Nina Rao", "Frontend Developer", "nina@example.com", "Skills", "React TypeScript JavaScript", "Experience", "Frontend Developer at Sample Co for 3 years", "Education", "B.Tech", "Projects", "Built an accessible dashboard with React"]:
        doc.add_paragraph(line)
    stream = io.BytesIO()
    doc.save(stream)
    profile = extract_profile(read_resume("resume.docx", stream.getvalue()))
    assert profile["name"] == "Nina Rao"
    assert profile["designation"] == "Frontend Developer"
    assert "React" in profile["skills"]
    assert profile["projects"]


def test_llm_tool_call_is_only_an_intent_router(monkeypatch):
    import openai
    from app.agent import _llm_intent

    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        call = SimpleNamespace(function=SimpleNamespace(name="route_job_request", arguments='{"intent":"recommend","reference":null,"skill":"React","location":null,"remote":true,"query":null,"reset":false}'))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai, "OpenAI", lambda **_: fake)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    intent = _llm_intent("remote React roles", [])
    assert intent["skill"] == "React"
    assert captured["tools"][0]["function"]["name"] == "route_job_request"
    assert captured["tool_choice"]["function"]["name"] == "route_job_request"
