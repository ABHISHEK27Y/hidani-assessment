"""Exercise the HTTP flow with a user-selected local resume; report no contact data.

python scripts/verify_local.py --resume /absolute/path/to/cv.pdf --base-url http://127.0.0.1:8870
Only the specified local server receives the file. Test sessions are deleted afterwards.
"""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


def verify(base_url: str, resume: Path):
    host = urlparse(base_url).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("This private-resume verification command only accepts localhost URLs")
    sid, isolated = str(uuid.uuid4()), str(uuid.uuid4())
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"checkpoint": name, "status": "passed"})
    with httpx.Client(base_url=base_url, timeout=30) as client:
        def chat(message, **extra):
            response = client.post("/api/chat", json={"session_id": sid, "message": message, **extra})
            response.raise_for_status()
            return response.json()
        try:
            health = client.get("/health").json()
            check("Readiness and dataset size", health["ok"] and 1500 <= health["jobs"] <= 2000)
            started = time.perf_counter()
            response = client.post("/api/resume", data={"session_id": sid}, files={"file": (resume.name, resume.read_bytes())})
            response.raise_for_status(); parsed = response.json()
            parse_ms = round((time.perf_counter() - started) * 1000)
            profile = parsed["profile"]
            check("Resume identity and contact fields detected", all(profile.get(key) and profile[key] != "Not found" for key in ("name", "email", "phone", "designation")))
            check("Resume skills, experience, education and projects detected", all(profile.get(key) for key in ("skills", "experience", "education", "projects")))
            check("Dated work duration detected", profile.get("experience_months") is not None)
            check("Recommendations with match reasons", bool(parsed["jobs"]) and all(job["match_reason"] for job in parsed["jobs"]))
            remote = chat("show only remote roles")
            check("Remote conversation refinement", bool(remote["jobs"]) and all(job["remote"] for job in remote["jobs"]))
            react = chat("jobs needing React in India")
            check("Technology and geography refinement", bool(react["jobs"]) and all("React" in job["skills"] for job in react["jobs"]))
            job_id = react["jobs"][0]["id"]
            detail = client.get(f"/api/jobs/{job_id}")
            check("Full job detail endpoint", detail.status_code == 200 and len(detail.json()["description"]) > 100)
            application = chat("apply to job 1")["application"]
            duplicate = chat("apply to job 1")["application"]
            check("Atomic duplicate protection", duplicate["duplicate"] and duplicate["applied_at"] == application["applied_at"])
            # This is a disposable test session: confirmation exercises local state,
            # and is not evidence of a real employer submission.
            confirmed = chat("I submitted job 1")
            check("Application date and status transition", confirmed["applications"][0]["status"] == "submitted" and bool(confirmed["applications"][0]["submitted_at"]))
            check("Conversational application status", len(chat("show my applied jobs")["applications"]) == 1)
            restored = client.get("/api/bootstrap", params={"session_id": sid}).json()
            check("Profile, applications and rich history restore", bool(restored["profile"]) and len(restored["applications"]) == 1 and any(item.get("payload", {}).get("jobs") for item in restored["history"] if item.get("payload")))
            check("Anonymous session isolation", not client.get("/api/bootstrap", params={"session_id": isolated}).json()["applications"])
            invalid = chat("apply to job 999")
            check("Invalid job reference recovery", "could not identify" in invalid["reply"])
            missing = chat("find zzzimpossiblezzz jobs")
            check("No-match recovery", missing["total"] == 0 and not missing["jobs"])
            return {"verified_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
                    "resume_result": {"designation": profile["designation"], "experience_months": profile["experience_months"],
                                      "skills_detected": len(profile["skills"]), "projects_detected": len(profile["project_titles"]),
                                      "total_initial_matches": parsed["total"], "react_india_matches": react["total"], "upload_and_match_ms": parse_ms},
                    "live_llm_verified": False, "external_employer_submission_verified": False,
                    "note": "Local tool workflow only; raw resume and contact values are omitted."}
        finally:
            client.delete(f"/api/session/{sid}")
            client.delete(f"/api/session/{isolated}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8870")
    parser.add_argument("--resume", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("tmp/resume-verification.json"))
    args = parser.parse_args()
    report = verify(args.base_url, args.resume)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
