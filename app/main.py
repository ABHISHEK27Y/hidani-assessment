"""FastAPI app: a single deployable service for UI, resume parsing and chat."""
from __future__ import annotations

import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import agent, jobs, store
from app.resume import extract_profile, read_resume

ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    jobs.catalogue()
    yield


app = FastAPI(title="Orbit | AI Job Assistant", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=36, max_length=36)
    message: str = Field(min_length=1, max_length=2000)
    job_id: str | None = Field(default=None, max_length=300)


def checked_session(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise HTTPException(422, "Invalid session ID")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "jobs": len(jobs.catalogue())}


@app.get("/api/bootstrap")
def bootstrap(session_id: str):
    session_id = checked_session(session_id)
    state = store.session(session_id)
    return {"profile": state["profile"], "filters": state["filters"],
            "applications": agent._enriched_applications(session_id), "job_count": len(jobs.catalogue()),
            "history": store.history(session_id),
            "last_jobs": [job for job_id in state["last_jobs"] if (job := jobs.find_job(job_id))]}


@app.post("/api/resume")
async def resume(session_id: str = Form(...), file: UploadFile = File(...)):
    session_id = checked_session(session_id)
    data = await file.read(8 * 1024 * 1024 + 1)
    try:
        text = read_resume(file.filename or "", data)
        profile = extract_profile(text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    store.session(session_id)
    store.update_session(session_id, profile=profile, filters={})
    found = jobs.rank_jobs(profile, {})
    store.update_session(session_id, last_jobs=[job["id"] for job in found])
    reply = (f"I parsed your resume and found {len(found)} initial matches. "
             "Check the extracted details below, then tell me how to refine your search.")
    store.add_message(session_id, "assistant", reply)
    return {"reply": reply, "profile": profile, "jobs": found, "action": "resume"}


@app.post("/api/chat")
def chat(body: ChatRequest):
    return agent.respond(checked_session(body.session_id), body.message.strip(), body.job_id)
