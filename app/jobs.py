"""Validated job catalogue and explainable, deterministic ranking."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

JOBS_PATH = Path(os.getenv("JOBS_PATH", "data/jobs.json"))
STOP = {"and", "the", "for", "with", "job", "jobs", "role", "roles", "remote", "only", "me"}


@lru_cache(maxsize=1)
def catalogue() -> list[dict]:
    if not JOBS_PATH.exists():
        return []
    jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    if not isinstance(jobs, list):
        raise ValueError("The job catalogue must be a JSON array")
    return jobs


@lru_cache(maxsize=1)
def by_id() -> dict[str, dict]:
    return {job["id"]: job for job in catalogue()}


def find_job(job_id: str):
    return by_id().get(job_id)


def is_active(job: dict) -> bool:
    expiry = job.get("expires_at")
    if not expiry:
        return True
    try:
        return datetime.fromisoformat(expiry) > datetime.now(timezone.utc)
    except ValueError:
        return False


def _tokens(value: str):
    return {x.lower() for x in re.findall(r"[a-zA-Z][\w+#.]*", value or "") if len(x) > 2 and x.lower() not in STOP}


def rank_jobs(profile: dict | None, filters: dict, limit=8) -> list[dict]:
    profile = profile or {}
    designation = profile.get("designation", "")
    desired = {x.lower() for x in profile.get("skills", [])}
    years = profile.get("years_experience")
    required_skill = (filters.get("skill") or "").lower()
    query = filters.get("query") or ""
    location = (filters.get("location") or "").lower()
    title_tokens = _tokens(designation)
    query_tokens = {"engineer" if token == "engineering" else token for token in _tokens(query)}
    ranked = []
    for job in catalogue():
        if not is_active(job):
            continue
        if filters.get("remote") and not job.get("remote"):
            continue
        job_location = job.get("location", "").lower()
        if location and location not in job_location and "worldwide" not in job_location:
            continue
        job_skills = {x.lower() for x in job.get("skills", [])}
        title = job.get("title", "")
        text = f"{title} {job.get('description', '')[:2500]}".lower()
        if required_skill and required_skill not in job_skills and required_skill not in text:
            continue
        if query_tokens and not (all(token in title.lower() for token in query_tokens) or (required_skill and required_skill in text)):
            continue
        matched = sorted(desired & job_skills)
        title_overlap = title_tokens & _tokens(title)
        required_years = job.get("min_years_experience")
        seniority_years = 7 if re.search(r"\b(staff|principal|director)\b", title, re.I) else (5 if re.search(r"\bsenior\b", title, re.I) else None)
        required_years = required_years or seniority_years
        experience_fit = years is None or required_years is None or required_years <= years + 1
        if not experience_fit:
            continue
        score = (5 * len(title_overlap)) + (2.5 * len(matched))
        if designation and designation != "Not found" and designation.lower() in title.lower():
            score += 7
        if desired and not matched and not title_overlap:
            score -= 3
        if query_tokens:
            score += 3 * sum(token in title.lower() for token in query_tokens)
        if required_skill:
            score += 4
        if job.get("published_at"):
            score += 0.01
        reasons = []
        if title_overlap:
            reasons.append("Role aligns with your designation")
        if matched:
            reasons.append("Shared skills: " + ", ".join(x.title() for x in matched[:4]))
        if years is not None and required_years is not None and experience_fit:
            reasons.append("Experience requirement is within your range")
        if required_skill:
            reasons.append(f"Includes {filters['skill']}")
        if not reasons:
            reasons.append("Relevant to your search" if query_tokens else "Recent open role")
        ranked.append((score, job.get("published_at") or "", job, "; ".join(reasons)))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if profile and (desired or title_tokens) and not filters.get("query") and not required_skill:
        ranked = [item for item in ranked if item[0] > 0]
    return [{**job, "match_score": round(score, 1), "match_reason": reason} for score, _, job, reason in ranked[:limit]]
