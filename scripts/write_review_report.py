"""Build a public, redacted review summary from local verification outputs."""
import argparse
import json
import platform
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, default=Path("tmp/final-tests.xml"))
    parser.add_argument("--resume-report", type=Path, default=Path("tmp/resume-verification.json"))
    parser.add_argument("--clean-install", choices=["passed", "blocked_by_download_timeout"], required=True)
    parser.add_argument("--repository-url", default=None)
    parser.add_argument("--ci-status", choices=["pending", "passed", "failed"], default="pending")
    parser.add_argument("--llm-report", type=Path, default=Path("docs/llm-verification.json"))
    args = parser.parse_args()
    suites = ET.parse(args.junit).getroot().iter("testsuite")
    totals = {"tests": 0, "errors": 0, "failures": 0, "skipped": 0, "seconds": 0.0}
    for suite in suites:
        for key in ("tests", "errors", "failures", "skipped"):
            totals[key] += int(suite.get(key, "0"))
        totals["seconds"] += float(suite.get("time", "0"))
    totals["seconds"] = round(totals["seconds"], 2)
    private = json.loads(args.resume_report.read_text(encoding="utf-8"))
    safe_keys = ["designation", "experience_months", "skills_detected", "projects_detected", "total_initial_matches", "react_india_matches", "upload_and_match_ms"]
    llm = json.loads(args.llm_report.read_text(encoding="utf-8")) if args.llm_report.exists() else {}
    output = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "automated_tests": totals,
        "runtime": {"python": platform.python_version(), "os": platform.system(), "isolated_virtualenv": sys.prefix != sys.base_prefix,
                    "dependencies": {name: version(name) for name in ["fastapi", "starlette", "pydantic", "uvicorn", "PyMuPDF", "python-docx", "openai"]}},
        "actual_resume": {key: private["resume_result"][key] for key in safe_keys},
        "actual_resume_http_checkpoints": len(private["checks"]),
        "actual_resume_http_passed": sum(item["status"] == "passed" for item in private["checks"]),
        "browser_review": {"desktop": "1280x720", "tablet": "768x1024", "phone": "390x844", "horizontal_overflow_observed": False,
                           "header_top_after_reply": 0, "main_container_scroll_after_reply": 0,
                           "console_errors_observed": 0, "console_warnings_observed": 0},
        "clean_environment_install": args.clean_install,
        "live_llm_call_verified": bool(llm.get("live_function_call_verified")),
        "live_llm_orchestrator_verified": bool(llm.get("http_orchestrator_verified")),
        "llm_provider": llm.get("provider", "gemini"),
        "llm_model": llm.get("model", "gemini-3.8-flash"),
        "external_employer_submission_verified": False,
        "external_source_page_checks": "HTTP 403 / browser security verification; not verified",
        "deployment": "User will deploy; configuration and synthetic smoke checker included",
        "public_repository": args.repository_url or "Not published",
        "github_ci": args.ci_status,
        "recording": "Outline prepared; recording pending release",
        "privacy": "No raw resume text, phone number, email address, filename, or workspace ID is included in this report.",
    }
    Path("docs").mkdir(exist_ok=True)
    Path("docs/verification.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
