"""Conversation orchestrator. It delegates to parsing, matching and application tools.

The optional LLM only interprets intent. Job facts and application state always come
from the catalogue and database, never from generated text.
"""
from __future__ import annotations

import json
import os
import re

from app import jobs, store
from app.resume import SKILLS


def _llm_intent(message: str, conversation: list[dict]) -> dict | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(timeout=12, max_retries=1)
        tool = {"type": "function", "function": {
            "name": "route_job_request",
            "description": "Choose a job assistant action and extract safe filters. This function only routes intent; the server executes and validates every action.",
            "parameters": {"type": "object", "properties": {
                "intent": {"type": "string", "enum": ["recommend", "apply", "confirm", "status", "profile", "help"]},
                "reference": {"type": ["integer", "null"], "description": "One-based job number from recent recommendations, or null."},
                "skill": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "remote": {"type": ["boolean", "null"]},
                "query": {"type": ["string", "null"]},
                "reset": {"type": "boolean"},
            }, "required": ["intent", "reference", "skill", "location", "remote", "query", "reset"],
                "additionalProperties": False},
            "strict": True,
        }}
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": "route_job_request"}},
            messages=[
                {"role": "system", "content": (
                    "Route the user's request to the provided function. Extract a one-based job reference, "
                    "one skill, location, remote preference, and short job-title search query when present. "
                    "Do not invent job IDs or claim an application was submitted. "
                    "Use recent context only to resolve the user's intent."
                )},
                *conversation[-6:],
                {"role": "user", "content": message[:2000]},
            ],
        )
        calls = response.choices[0].message.tool_calls or []
        if not calls or calls[0].function.name != "route_job_request":
            return None
        payload = json.loads(calls[0].function.arguments)
        return payload if payload.get("intent") in {"recommend", "apply", "confirm", "status", "profile", "help"} else None
    except Exception:
        return None


def _rule_intent(message: str) -> dict:
    low = message.lower().strip()
    reference = re.search(r"(?:job\s*#?\s*|#)(\d{1,2})\b", low)
    if not reference:
        reference = re.search(r"\b(?:apply to|submitted|applied to|open|view)\s+(?:the\s+)?(?:job\s+)?(\d{1,2})\b", low)
    number = int(reference.group(1)) if reference else None
    if number is None:
        for word, value in {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8}.items():
            if re.search(r"\b" + word + r"\b", low):
                number = value
                break
    if re.search(r"\b(i (?:have |already )?(?:submitted|applied)|mark .* submitted|finished applying)\b", low):
        intent = "confirm"
    elif re.search(r"\b(apply|application link|start application)\b", low) and not re.search(r"\b(applied jobs|applications|application status)\b", low):
        intent = "apply"
    elif re.search(r"\b(applied jobs|applications|application status|track|status)\b", low):
        intent = "status"
    elif re.search(r"\b(my profile|my resume|extracted details|what did you find)\b", low):
        intent = "profile"
    elif re.search(r"\b(help|what can you do)\b", low):
        intent = "help"
    else:
        intent = "recommend"
    skill = None
    for known in sorted(SKILLS, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(known.lower()) + r"(?!\w)", low):
            skill = known
            break
    remote = True if re.search(r"\bremote|work from home|wfh\b", low) else None
    loc = re.search(r"\b(?:in|near|from)\s+([a-zA-Z][a-zA-Z ]{2,25})(?:\?|$)", message, re.I)
    location = loc.group(1).strip() if loc and not re.search(r"\b(?:apply|submitted|job)\b", loc.group(1), re.I) else None
    reset = bool(re.search(r"\b(reset|clear filters|start over|all jobs)\b", low))
    query = None
    title_query = re.search(r"\b(?:looking for|search for|find|show me|show|recommend)\s+(?:only )?(.+?)(?:\s+jobs?|\s+roles?|$)", low)
    if title_query:
        candidate = title_query.group(1).strip()
        candidate = re.sub(r"^(?:me\s+)?(?:only\s+)?remote\s+", "", candidate)
        if candidate and candidate not in {"my applied", "applied", "remote", "only remote", "me"} and len(candidate.split()) <= 5:
            query = candidate
    return {"intent": intent, "reference": number, "skill": skill, "remote": remote,
            "location": location, "query": query, "reset": reset}


def _resolve_job(state: dict, number) -> dict | None:
    if number is None:
        return None
    try:
        index = int(number) - 1
    except (TypeError, ValueError):
        return None
    ids = state["last_jobs"]
    if index < 0 or index >= len(ids):
        return None
    return jobs.find_job(ids[index])


def respond(session_id: str, message: str, job_id: str | None = None) -> dict:
    state = store.session(session_id)
    intent = _rule_intent(message)
    if (intent["intent"] == "recommend" and not any((intent["skill"], intent["remote"], intent["query"], intent["reset"]))) or (intent["intent"] in {"apply", "confirm"} and intent["reference"] is None and not job_id):
        intent = _llm_intent(message, store.history(session_id)) or intent
    result: dict = {"reply": "", "jobs": [], "applications": [], "profile": None, "action": intent["intent"]}
    kind = intent["intent"]
    if kind == "apply":
        job = jobs.find_job(job_id) if job_id else _resolve_job(state, intent.get("reference"))
        if not job:
            result["reply"] = "I could not identify that job. Ask for recommendations, then say ‘apply to job 3’ using one of the numbered results."
        else:
            app = store.create_application(session_id, job["id"])
            result["application"] = {**app, "job": job}
            result["reply"] = (f"I saved {job['title']} at {job['company']} to your application tracker. "
                               "Open the employer's application page and submit there. When finished, tell me ‘I submitted job "
                               f"{intent['reference']}’ so I can mark it submitted. Current status: "
                               + ("submitted" if app["status"] == "submitted" else "awaiting external submission") + ".")
    elif kind == "confirm":
        job = jobs.find_job(job_id) if job_id else _resolve_job(state, intent.get("reference"))
        if not job:
            result["reply"] = "Tell me which numbered job you submitted, for example ‘I submitted job 3’."
        else:
            app = store.confirm_application(session_id, job["id"])
            result["reply"] = (f"Marked {job['title']} at {job['company']} as submitted."
                               if app else "That job is not in your tracker yet. Ask me to apply first.")
            result["applications"] = _enriched_applications(session_id)
    elif kind == "status":
        result["applications"] = _enriched_applications(session_id)
        result["reply"] = (f"You have {len(result['applications'])} tracked application(s). Submitted means you confirmed the external application was completed."
                           if result["applications"] else "No applications yet. Ask me to apply to a numbered job to start tracking it.")
    elif kind == "profile":
        result["profile"] = state["profile"]
        result["reply"] = "Here is what I extracted from your resume. Tell me if I should refine the search."
        if not state["profile"]:
            result["reply"] = "Upload a PDF or DOCX resume first, and I’ll extract your details."
    elif kind == "help":
        result["reply"] = "Upload a resume, ask for matches, refine with ‘remote React roles’, say ‘apply to job 3’, then ‘show my applied jobs’. Applications open at the original job site; tell me when you have submitted one."
    else:
        filters = {} if intent.get("reset") else dict(state["filters"])
        for key in ("skill", "remote", "location", "query"):
            value = intent.get(key)
            if value:
                filters[key] = value
        if intent.get("reset"):
            filters = {}
        if not state["profile"] and not filters and not intent.get("reset"):
            result["reply"] = "Upload your resume to get tailored matches, or ask for something specific like ‘remote Python jobs’."
        else:
            found = jobs.rank_jobs(state["profile"], filters)
            store.update_session(session_id, filters=filters, last_jobs=[job["id"] for job in found])
            result["jobs"] = found
            result["filters"] = filters
            result["reply"] = (f"I found {len(found)} roles ranked for you. You can refine by skill or location, or say ‘apply to job 3’."
                               if found else "No roles match those filters in the current dataset. Try clearing a filter or asking for another skill.")
    store.add_message(session_id, "user", message)
    store.add_message(session_id, "assistant", result["reply"])
    return result


def _enriched_applications(session_id: str):
    return [{**app, "job": jobs.find_job(app["job_id"])} for app in store.applications(session_id)]
