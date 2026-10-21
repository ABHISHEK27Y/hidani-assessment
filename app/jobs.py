"""Grounded, explainable matching against the validated JSON catalogue."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from app.skills import canonical_skill

ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = Path(os.getenv("JOBS_PATH", str(ROOT / "data/jobs.json")))
STOP = {"and", "the", "for", "with", "job", "jobs", "role", "roles", "remote", "only", "me", "a", "an", "engineering", "intern"}
TECH_ROLE = re.compile(r"software|develop|front.?end|back.?end|full.?stack|web|platform engineer|AI engineer|machine learning|data engineer|devops|site.reliability|\bSRE\b|\bQA\b|test engineer|automation engineer", re.I)
COUNTRY_OFFSETS = {"india": {5.5}, "united states": {-10, -9, -8, -7, -6, -5},
                   "united kingdom": {0}, "canada": {-8, -7, -6, -5, -4, -3.5},
                   "germany": {1}, "france": {1}, "australia": {8, 9.5, 10}, "nepal": {5.75}}


def catalogue() -> list[dict]:
    stat = JOBS_PATH.stat()
    return _load_catalogue(str(JOBS_PATH.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=2)
def _load_catalogue(path: str, _mtime: int, _size: int) -> list[dict]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("The job catalogue must be a non-empty JSON array")
    seen = set()
    for job in records:
        required = ["id", "title", "company", "location", "experience_required", "description", "source_link", "application_link"]
        if not isinstance(job, dict) or not all(isinstance(job.get(key), str) and job[key].strip() for key in required):
            raise ValueError("A job is missing a required text field")
        if job["id"] in seen or not isinstance(job.get("skills"), list) or not job["skills"] or not all(isinstance(skill, str) and skill.strip() for skill in job["skills"]):
            raise ValueError("Job IDs must be unique and skills must be non-empty string arrays")
        seen.add(job["id"])
        for key in ("source_link", "application_link"):
            parsed = urlparse(job[key])
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("Job links must be valid HTTPS URLs")
    return records


def find_job(job_id: str | None):
    return next((job for job in catalogue() if job["id"] == job_id), None)


def is_active(job: dict) -> bool:
    if not job.get("expires_at"):
        return True
    try:
        value = datetime.fromisoformat(job["expires_at"].replace("Z", "+00:00"))
        return value.tzinfo is not None and value > datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def _tokens(value: str):
    value = value.lower().replace("engineering", "engineer").replace("front-end", "frontend").replace("front end", "frontend").replace("back-end", "backend").replace("back end", "backend").replace("full-stack", "fullstack").replace("full stack", "fullstack")
    return {token for token in re.findall(r"[a-z][a-z0-9+#.]*", value) if len(token) > 1 and token not in STOP}


def _required_years(job):
    explicit = job.get("min_years_experience")
    title = job["title"]
    seniority = " ".join(job.get("seniority") or [])
    inferred = 0
    if re.search(r"\b(staff|principal|director|head of|executive|architect)\b", title + " " + seniority, re.I):
        inferred = 7
    elif re.search(r"\b(senior|sr|lead|manager)\b", title + " " + seniority, re.I):
        inferred = 5
    elif re.search(r"\bmid(?:dle)?[ -]level\b", title + " " + seniority, re.I):
        inferred = 2
    return max(explicit if explicit is not None else 0, inferred), explicit is not None


def search_jobs(profile: dict | None, filters: dict, offset=0, limit=6) -> dict:
    profile = profile or {}
    designation = profile.get("designation") or ""
    desired = {canonical_skill(value) for value in profile.get("skills", [])}
    years = profile.get("years_experience")
    title_tokens = _tokens(designation) if designation != "Not found" else set()
    requested = filters.get("skills") or ([filters["skill"]] if filters.get("skill") else [])
    requested = {canonical_skill(value) for value in requested}
    query_tokens = _tokens(filters.get("query") or "")
    location = (filters.get("location") or "").lower()
    location = {"us": "united states", "usa": "united states", "uk": "united kingdom", "in": "india", "bangalore": "india", "bengaluru": "india", "delhi": "india", "mumbai": "india"}.get(location, location)
    candidate_technical = bool(TECH_ROLE.search(designation))
    ranked = []
    for job in catalogue():
        if not is_active(job):
            continue
        if filters.get("remote") is not None and bool(job.get("remote")) != filters["remote"]:
            continue
        restrictions = job.get("location_restrictions")
        location_text = " ".join(restrictions).lower() if restrictions is not None else job["location"].lower()
        worldwide = not restrictions if restrictions is not None else "worldwide" in location_text
        if location and not worldwide and location not in location_text:
            continue
        timezone_restrictions = job.get("timezone_restrictions") or []
        if location in COUNTRY_OFFSETS and timezone_restrictions and not COUNTRY_OFFSETS[location].intersection(timezone_restrictions):
            continue
        title = job["title"]
        job_skills = {canonical_skill(value) for value in job.get("skills", [])}
        if requested and not requested <= job_skills:
            continue
        if query_tokens and not query_tokens <= _tokens(title):
            continue
        if candidate_technical and not TECH_ROLE.search(title):
            continue
        required_years, stated_years = _required_years(job)
        cap = filters.get("max_years")
        if cap is not None and required_years > cap:
            continue
        if years is not None and required_years > years + 0.5:
            continue
        if filters.get("level") == "intern" and not re.search(r"\bintern(?:ship)?\b", title + " " + job.get("employment_type", ""), re.I):
            continue
        if filters.get("level") == "entry" and required_years > 1:
            continue
        matched = sorted(desired & job_skills)
        title_overlap = title_tokens & _tokens(title)
        if desired and not matched and not title_overlap and not requested and not query_tokens:
            continue
        score = len(title_overlap) * 5 + len(matched) * 2.5
        if designation != "Not found" and designation and designation.lower().replace(" engineering", " engineer").removesuffix(" intern") in title.lower():
            score += 6
        score += len(requested) * 4 + len(query_tokens) * 3
        # A junior candidate should see junior and internship roles ahead of unspecified seniority.
        if years is not None and years < 2 and re.search(r"\b(junior|intern|graduate|entry)\b", title, re.I):
            score += 6
        reasons = []
        if title_overlap or (candidate_technical and TECH_ROLE.search(title)):
            reasons.append("Aligned with your software experience" if candidate_technical else "Aligned with your role")
        if matched:
            reasons.append("Shared skills: " + ", ".join(matched[:5]))
        if stated_years and years is not None:
            reasons.append(f"Requires {job['experience_required']}; your profile has {profile.get('experience_months', round(years * 12))} months")
        elif years is not None:
            reasons.append("Years not specified — check the listing")
        if requested:
            reasons.append("Includes " + ", ".join(sorted(requested)))
        if location:
            reasons.append("Worldwide listing" if worldwide else f"Location includes {filters['location']}")
        if not reasons:
            reasons.append("Matches your search" if query_tokens else "Recent listing")
        ranked.append((score, job.get("published_at") or "", {**job,
            "match_score": round(score, 1), "matched_skills": matched,
            "missing_skills": sorted(job_skills - desired)[:8] if desired else [],
            "match_reason": "; ".join(reasons),
        }))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {"jobs": [item[2] for item in ranked[offset:offset + limit]],
            "total": len(ranked), "offset": offset, "has_more": offset + limit < len(ranked)}


def rank_jobs(profile: dict | None, filters: dict, limit=8) -> list[dict]:
    return search_jobs(profile, filters, limit=limit)["jobs"]
