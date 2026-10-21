"""Collect real listings from the Himalayas public jobs API.

Run: python scripts/scrape_jobs.py --target 1800
The API permits job-search apps with source attribution. Respect 429/Retry-After.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.resume import SKILLS  # noqa: E402


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(html: str) -> str:
    parser = TextOnly()
    parser.feed(html or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def normalize(raw: dict, collected_at: str) -> dict | None:
    title = (raw.get("title") or "").strip()
    company = (raw.get("companyName") or "").strip()
    link = raw.get("applicationLink") or ""
    if not (title and company and link.startswith("https://")):
        return None
    description = plain(raw.get("description") or raw.get("excerpt") or "")[:8000]
    skill_text = f"{title} {description}"
    skills = [name for name, patterns in SKILLS.items() if any(re.search(p, skill_text, re.I) for p in patterns)]
    years = re.search(r"(?:minimum of |at least )?(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\+?\s+years?\s+(?:of )?(?:relevant |professional |work )?experience", description, re.I)
    restrictions = raw.get("locationRestrictions") or []
    location = "Remote - " + (", ".join(restrictions[:3]) if restrictions else "Worldwide")
    published = raw.get("pubDate")
    expires = raw.get("expiryDate")
    if expires:
        try:
            if datetime.fromtimestamp(int(expires), timezone.utc) <= datetime.now(timezone.utc):
                return None
        except (ValueError, TypeError, OSError):
            return None
    def iso(value):
        try:
            return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
        except (ValueError, TypeError, OSError):
            return None
    return {
        "id": "himalayas:" + hashlib.sha256(str(raw.get("guid") or link).encode("utf-8")).hexdigest()[:16],
        "title": title, "company": company, "location": location,
        "remote": True, "employment_type": raw.get("employmentType") or "Not specified",
        "experience_required": f"{years.group(1)}+ years" if years else "Not specified",
        "min_years_experience": int(years.group(1)) if years else None,
        "skills": skills, "description": description,
        "source": "Himalayas", "source_link": str(raw.get("guid") or link),
        "application_link": link, "published_at": iso(published),
        "expires_at": iso(expires), "collected_at": collected_at,
    }


def request_page(cursor: str | None) -> dict:
    params = {"limit": "20"}
    if cursor:
        params["cursor"] = cursor
    url = "https://himalayas.app/jobs/api?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HidaniAssessmentJobAssistant/1.0 (educational demo)", "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            wait = int(exc.headers.get("Retry-After", "0") or 0) or min(60, 2 ** attempt)
            print(f"HTTP {exc.code}; waiting {wait}s", flush=True)
            time.sleep(wait)
        except (TimeoutError, urllib.error.URLError):
            if attempt == 5:
                raise
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError("Could not fetch jobs")


def scrape(target: int, output: Path, delay: float) -> None:
    if not 1500 <= target <= 2000:
        raise ValueError("Target must be between 1500 and 2000")
    collected_at = datetime.now(timezone.utc).isoformat()
    jobs = {}
    cursor = None
    pages = 0
    while len(jobs) < target:
        payload = request_page(cursor)
        pages += 1
        for raw in payload.get("jobs", []):
            job = normalize(raw, collected_at)
            if job:
                jobs.setdefault(job["id"], job)
        print(f"page={pages} unique_jobs={len(jobs)}", flush=True)
        next_cursor = payload.get("nextCursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(delay)
    if len(jobs) < 1500:
        raise RuntimeError(f"Only {len(jobs)} valid listings were available; refusing to write an undersized dataset")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = list(jobs.values())[:target]
    tmp = output.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    tmp.replace(output)
    print(f"Wrote {len(result)} real listings to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=1800)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "jobs.json")
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()
    scrape(args.target, args.output, args.delay)
