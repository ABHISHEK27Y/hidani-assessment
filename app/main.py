"""Single-service API and UI with bounded uploads and observable failures."""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

from app import agent, jobs, store  # noqa: E402
from app.resume import MAX_BYTES, extract_profile, read_resume  # noqa: E402

logger = logging.getLogger(__name__)


class BodyLimitMiddleware:
    """Bound multipart data before it reaches the multipart parser, including chunked bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        limit = MAX_BYTES + 128 * 1024 if scope["path"] == "/api/resume" else 32 * 1024
        chunks, size = [], 0
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            chunk = event.get("body", b"")
            size += len(chunk)
            if size > limit:
                return await JSONResponse({"detail": "Request is too large. Resume uploads are limited to 8 MB."}, status_code=413)(scope, receive, send)
            chunks.append(chunk)
            if not event.get("more_body", False):
                break
        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


class RateLimiter:
    def __init__(self):
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, session_id, action="chat"):
        limit = 10 if action == "resume" else 40
        now = time.monotonic()
        with self.lock:
            queue = self.events[(str(session_id), action)]
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= limit:
                raise HTTPException(429, "Too many requests. Please wait a minute and try again.", headers={"Retry-After": "60"})
            queue.append(now)
            if len(self.events) > 10000:
                for key in list(self.events):
                    if not self.events[key] or self.events[key][-1] < now - 60:
                        self.events.pop(key, None)


limiter = RateLimiter()


@asynccontextmanager
async def lifespan(_app):
    store.init_db()
    jobs.catalogue()
    agent.application_mode()
    agent.llm_status()
    yield


app = FastAPI(title="Orbit | Job Search Workspace", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None)
app.add_middleware(BodyLimitMiddleware)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.middleware("http")
async def response_headers(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Request failed id=%s path=%s", request_id, request.url.path)
        response = JSONResponse({"detail": "Something went wrong. Please retry.", "request_id": request_id}, status_code=500)
    response.headers.update({
        "X-Request-ID": request_id, "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store" if request.url.path.startswith("/api/") else "no-cache",
    })
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
    return response


@app.get("/docs", include_in_schema=False)
def api_docs():
    """Allow Swagger's CDN assets only on the documentation page, with a nonced initializer."""
    nonce = secrets.token_urlsafe(24)
    page = get_swagger_ui_html(openapi_url="/openapi.json", title="Orbit API",
                               swagger_favicon_url="/static/favicon.svg")
    content = page.body.decode().replace("<script>", f'<script nonce="{nonce}">')
    policy = (f"default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; "
              "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data:; "
              "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
    return HTMLResponse(content, headers={"Content-Security-Policy": policy})


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    job_id: str | None = Field(default=None, max_length=300)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class ApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: UUID
    job_id: str = Field(min_length=1, max_length=300)
    action: Literal["start", "confirm"] = "start"


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


@app.get("/health")
def health():
    with store.connect() as db:
        db.execute("SELECT 1").fetchone()
    records = jobs.catalogue()
    return {"ok": True, "jobs": len(records), "active_jobs": sum(jobs.is_active(job) for job in records),
            **agent.llm_status(), "application_mode": agent.application_mode()}


@app.get("/api/bootstrap")
def bootstrap(session_id: UUID):
    sid = str(session_id)
    state = store.session(sid)
    active = [job for job in jobs.catalogue() if jobs.is_active(job)]
    return {"profile": state["profile"], "filters": state["filters"],
            "applications": agent.enriched_applications(sid), "job_count": len(active),
            "dataset_count": len(jobs.catalogue()), "history": store.history(sid),
            "application_mode": agent.application_mode(), **agent.llm_status()}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    job = jobs.find_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {**job, "active": jobs.is_active(job)}


@app.post("/api/resume")
async def resume(session_id: UUID = Form(...), file: UploadFile = File(...)):
    sid = str(session_id)
    limiter.check(sid, "resume")
    try:
        data = await file.read(MAX_BYTES + 1)
        text = await run_in_threadpool(read_resume, file.filename or "", data)
        profile = await run_in_threadpool(extract_profile, text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()
    store.session(sid)
    store.update_session(sid, profile=profile, filters={})
    found = await run_in_threadpool(jobs.search_jobs, profile, {})
    store.update_session(sid, last_jobs=[job["id"] for job in found["jobs"]])
    reply = (f"Your resume is ready. I extracted your profile and found {found['total']} potential matches. "
             "Review the details below, then tell me what matters to you.")
    if not found["jobs"]:
        reply = "I parsed your resume, but no current roles meet its experience and skill constraints. Review your profile or try a broader search."
    result = {"reply": reply, "profile": profile, "jobs": [agent.compact_job(job) for job in found["jobs"]],
              "total": found["total"], "has_more": found["has_more"], "filters": {}, "action": "resume",
              "tools": ["parse_resume", "match_jobs"], "application_count": len(store.applications(sid))}
    store.add_message(sid, "user", "Uploaded resume: " + Path(file.filename or "resume").name[:120])
    store.add_message(sid, "assistant", reply, result)
    return result


@app.post("/api/chat")
def chat(body: ChatRequest):
    limiter.check(body.session_id)
    return agent.respond(str(body.session_id), body.message, body.job_id)


@app.get("/api/applications")
def applications(session_id: UUID):
    return {"applications": agent.enriched_applications(str(session_id))}


@app.post("/api/applications")
def application_action(body: ApplicationRequest):
    limiter.check(body.session_id)
    message = "apply to this job" if body.action == "start" else "I submitted this job"
    return agent.respond(str(body.session_id), message, body.job_id)


@app.delete("/api/session/{session_id}")
def delete_session(session_id: UUID):
    store.delete_session(str(session_id))
    return {"ok": True}
