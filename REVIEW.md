# Complete local project review — 21 October 2026

The local project supports resume upload, extraction, experience-aware recommendations, conversational refinement, job details, application tracking and restored history through a redesigned black/purple glass interface. The local API and browser flows were exercised. The release handoff includes public source publication and deployment files; the user will perform deployment.

The acceptance status for every point in the brief is in **[ASSESSMENT_CHECKLIST.md](ASSESSMENT_CHECKLIST.md)**. The local flow is verified; actual employer auto-submission, live provider access and release deliverables are not represented as complete.

## Resume test

The newer resume in the user's job-apply folder was read locally and uploaded to the localhost API and UI. No copy of the PDF, raw text, phone number or email is included in this repository.

| Extraction | Result |
|---|---|
| Name and contact | Detected and displayed in the local profile |
| Designation | Software Engineering Intern |
| Work duration | 3 inclusive calendar months from the dated internship |
| Skills | 30 recognized skills |
| Education | Institute, degree and academic details retained |
| Projects | All 3 project titles and descriptions retained |

The final match counts and response timing are recorded in the redacted `docs/verification.json`. The parser estimates calendar duration, not verified professional tenure. Profile corrections can be supplied in chat.

## Problems found and corrected

1. **Internship title was missed.** The first parser only searched a small header window and did not recognize “Software Engineering Intern”. Work-section titles now take precedence.
2. **Experience was unknown.** Date ranges now produce a work-month estimate, with overlapping ranges unioned. College and project dates are excluded.
3. **Overly senior recommendations appeared.** Seniority markers, stated experience requirements and candidate duration now constrain matching. Architect, staff, senior/Sr. and management titles are handled explicitly.
4. **Skills were missed or falsely detected.** The shared vocabulary now supports C++, C#, React.js, TailwindCSS, Express.js, RAG and other aliases, with word boundaries. Generic “Spring” and English “go” matches were removed.
5. **Geography was truncated.** The snapshot retains full country and timezone arrays. Country filtering checks the full array and known standard country offsets; short card labels indicate additional locations.
6. **Many collected rows had empty skills.** The final collector excludes these rows and fills the required snapshot with real records containing extractable skills.
7. **History lost cards on reload.** Messages now persist typed result payloads, so resume cards, job results and application state can be reconstructed.
8. **Old card actions could refer to newer results.** Button actions carry a stable job ID; typed job numbers refer to the latest result page.
9. **Application dates lacked clear meaning.** Started and confirmed-submission timestamps are now separate; repeat requests preserve the original record. The earlier database schema migrates without deleting records.
10. **Empty/invalid requests were weakly checked.** UUIDs, whitespace, length, unknown fields, file types, file contents, page counts, upload expansion and overall request size are validated.
11. **The upload path could block the async server.** CPU parsing/matching work runs in worker threads. SQLite connections are now explicitly closed.
12. **Long replies could scroll the header away.** Scrolling now targets the conversation region rather than all ancestors.
13. **Loading and failures were hard to distinguish.** The UI now has request-specific loading messages, disabled upload/send controls, timeout messages and retry actions.
14. **Icon-only tablet controls lost their names.** Navigation controls now retain explicit accessible labels when text labels are hidden.
15. **Configuration was awkward.** `.env` loading and pinned tested top-level dependencies are now part of setup. Private files and local databases are ignored by Git.
16. **API documentation did not render under the app's strict content policy.** The Swagger documentation now has its own nonce for the initializer and permits its official CDN assets; the main workspace retains the strict same-origin policy. Browser rendering and policy separation were verified.

## Verification performed

- Automated HTTP tests cover readiness, static assets, profile upload, filtering, details, applications, validation errors, limits, isolation, history and reset.
- Parser tests cover PDF, DOCX, table order, work dates, projects, aliases, corrupted files, scanned/locked files and size limits.
- Matching tests cover junior/senior separation, multiple skills, geography, timezone restrictions, expiry and pagination.
- State tests cover simultaneous duplicate requests, status transitions, timestamp stability and migration from the first database schema.
- Optional provider tests cover valid function arguments, invalid JSON, unsupported intents, invalid references, unexpected fields and provider failure.
- A localhost-only script exercised the full tool flow using the actual resume and deleted its disposable test session afterwards.
- Browser checks covered real-resume upload, details, application initiation, skill/location filtering, restored history, reset, fixed header/composer behavior, responsive layouts, and console warnings/errors.

The machine-readable test summary, redacted actual-resume result and browser dimensions are in `docs/verification.json`. Dataset schema and source-check evidence are in `docs/data-audit.json`.

Final results: **39 automated tests passed, with no failures or skips**, inside the isolated virtual environment, and **15 of 15 actual-resume HTTP checkpoints passed**. The synthetic deployment checker also passed **13/13 checkpoints** against localhost. `pip check`, JavaScript syntax, Python compilation and Git whitespace checks passed. The actual resume produced 38 initial matches and four matches after React/India refinement; its release-check upload-and-match request took 174 ms on this machine. This is a single local observation, not a load-test result. The clean environment reports a dependency-level Starlette/AnyIO deprecation warning; it does not cause a test failure.

## API review

All eight application endpoints are documented in the README and OpenAPI schema. Success, 404, 413, 422 and 429 paths are exercised where applicable. Responses include request IDs, no-store controls for private API data, a same-origin content policy and MIME-sniffing protection. The app renders external text with DOM text nodes and checks outbound link protocols.

The no-auth brief is implemented with anonymous UUID workspaces. This provides separation but no account recovery or identity verification. A production version would need a deliberate retention policy, stronger abuse controls and account recovery choices. These are outside the assessment's stated authentication requirement.

## Remaining limits and release work

1. **Real employer submission is incomplete.** Assisted mode returns the original form and records candidate confirmation. Simulation mode creates a visibly simulated local receipt. Neither proves that an employer received an application.
2. **The live LLM path is unverified.** No provider key is configured. Actual function-calling code and fallback behavior are present; mocked checks do not establish account/model availability.
3. **External source pages could not be verified.** Sample HTTP requests returned 403 and the browser displayed a security-verification screen. The source API worked; the blocker was not bypassed.
4. **Deployment belongs to the user's handoff.** No public live link or final recording has been produced here. Docker, Compose, Railway configuration, a synthetic public-domain checker and step-by-step instructions are included. GitHub CI builds and exercises the Docker image; its recorded status is in `docs/verification.json`.
5. **The dataset is a remote-job snapshot.** On-site filtering is implemented/tested, but this source contains remote roles. Expiry metadata and a valid source URL do not guarantee current employer availability. Missing numeric experience remains explicitly unknown.
6. **Parsing is conservative text extraction.** Scanned resumes need OCR or a text-based export. More layouts should be added as regression fixtures when encountered; there is no claim of perfect parsing of every resume.
7. **The installation blocker was resolved.** After earlier PyPI timeouts, the full installation completed inside an isolated Python 3.13.2 virtual environment. `pip check` and all 39 tests passed there. `constraints.txt` records versions without local wheel paths; Linux/container compatibility is checked in CI.

## Release handoff

- Public source target: https://github.com/ABHISHEK27Y/hidani-assignmnet
- Full instructions: `DEPLOYMENT.md`.
- Windows launcher: `scripts/run.ps1`.
- Deployment configuration: `Dockerfile`, `compose.yaml`, `railway.json`, `requirements.txt`, `constraints.txt` and `.env.example`.
- Post-deployment check: `scripts/smoke_test.py`, using synthetic data only.
- Optional paid provider check: `scripts/check_llm.py`; a configured key is still required.
- GitHub Actions passed Linux installation, automated tests, the Docker build and the running-container HTTP smoke check. Exact tested commit and run URL are in `docs/ci-verification.json`.

![Desktop workspace](docs/screenshots/desktop.jpg)

![Phone workspace](docs/screenshots/mobile.jpg)
