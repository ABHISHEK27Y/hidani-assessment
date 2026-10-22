"""Validate the full snapshot and optionally check a small sample of source URLs."""
import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.jobs import catalogue, is_active


def audit(link_count=0):
    records = catalogue()  # Performs the complete schema, duplicate and URL validation.
    checked = []
    for job in records[:link_count]:
        try:
            request = urllib.request.Request(job["source_link"], headers={"User-Agent": "OrbitAssessmentAudit/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                checked.append({"job_id": job["id"], "status": response.status})
        except urllib.error.HTTPError as exc:
            checked.append({"job_id": job["id"], "status": exc.code})
        except Exception as exc:
            checked.append({"job_id": job["id"], "status": "unreachable", "error_type": type(exc).__name__})
    return {"verified_at": datetime.now(timezone.utc).isoformat(), "count": len(records),
            "unique_ids": len({job["id"] for job in records}), "active": sum(is_active(job) for job in records),
            "with_full_geographic_restrictions": sum("location_restrictions" in job for job in records),
            "with_extracted_skills": sum(bool(job["skills"]) for job in records),
            "explicit_experience_years": sum(job.get("min_years_experience") is not None for job in records),
            "sources": dict(Counter(job["source"] for job in records)), "source_link_sample": checked,
            "note": "Unknown skills or numeric experience are not fabricated. A link sample is not a guarantee that every listing remains open."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-links", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/data-audit.json")
    args = parser.parse_args()
    report = audit(max(0, min(args.check_links, 20)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
