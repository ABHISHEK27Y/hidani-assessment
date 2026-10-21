from copy import deepcopy
from datetime import datetime, timedelta, timezone

from app import jobs


def listing(job_id="junior", **changes):
    base = {"id": job_id, "title": "Junior Software Engineer", "company": "Example", "remote": True,
            "location": "Remote - Worldwide", "location_restrictions": [], "seniority": ["Entry-level"],
            "skills": ["React", "Python"], "min_years_experience": None, "experience_required": "Not specified",
            "description": "Build React and Python applications.", "source_link": "https://example.test/job", "application_link": "https://example.test/apply"}
    return {**base, **changes}


def test_junior_matching_filters_seniority_and_unrelated_roles(monkeypatch):
    records = [listing(), listing("senior", title="Senior Software Engineer", min_years_experience=5),
               listing("architect", title="Software Solution Architect", seniority=["Senior"]),
               listing("nurse", title="Clinical Care Manager", skills=["Python"])]
    monkeypatch.setattr(jobs, "catalogue", lambda: records)
    profile = {"designation": "Software Engineering Intern", "skills": ["Python", "React"], "years_experience": .25, "experience_months": 3}
    assert [job["id"] for job in jobs.rank_jobs(profile, {})] == ["junior"]


def test_full_geography_and_multiple_skills(monkeypatch):
    records = [listing("restricted", location_restrictions=["Canada", "France", "Germany", "India"]),
               listing("us", location_restrictions=["United States"]), listing("world")]
    monkeypatch.setattr(jobs, "catalogue", lambda: records)
    assert {job["id"] for job in jobs.rank_jobs(None, {"location": "India", "skills": ["React", "Python"]})} == {"restricted", "world"}
    assert not jobs.rank_jobs(None, {"skills": ["React", "Rust"]})
    assert not jobs.rank_jobs(None, {"remote": False})


def test_expiry_and_pagination(monkeypatch):
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    records = [listing(str(number)) for number in range(9)] + [listing("expired", expires_at=expired)]
    monkeypatch.setattr(jobs, "catalogue", lambda: records)
    first = jobs.search_jobs(None, {}, limit=6)
    second = jobs.search_jobs(None, {}, offset=6, limit=6)
    assert first["total"] == 9 and first["has_more"]
    assert len(second["jobs"]) == 3 and not second["has_more"]
    assert not {j["id"] for j in first["jobs"]} & {j["id"] for j in second["jobs"]}


def test_country_filter_respects_timezone_restrictions(monkeypatch):
    monkeypatch.setattr(jobs, "catalogue", lambda: [listing("us-hours", timezone_restrictions=[-8, -7, -6, -5]), listing("india-hours", timezone_restrictions=[5.5])])
    assert [job["id"] for job in jobs.rank_jobs(None, {"location": "India"})] == ["india-hours"]


def test_dataset_contract():
    records = jobs.catalogue()
    assert 1500 <= len(records) <= 2000
    assert len({job["id"] for job in records}) == len(records)
    assert all(isinstance(job["skills"], list) and job["skills"] and len(job["description"]) >= 100 and job["source_link"].startswith("https://") for job in records)
    assert all("location_restrictions" in job and "timezone_restrictions" in job for job in records)
