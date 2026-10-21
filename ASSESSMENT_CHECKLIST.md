# Assessment acceptance checklist

Reviewed against all three pages of the supplied Hidani Tech assessment. A checked box means the local implementation was exercised. External or release-dependent requirements are identified separately; they are not counted as completed functionality.

## Dataset

- [x] **D01 — Done:** Collect 1,500–2,000 real online listings. The snapshot contains **1,800 unique jobs** from the Himalayas public API.
- [x] **D02 — Done:** Store the dataset in a JSON database file: `data/jobs.json`.
- [x] **D03 — Done:** Every record includes job ID, title, company, location, experience required, skills, description and source link. All 1,800 have non-empty extracted skill arrays. Numeric experience is labeled unknown where the source does not state it.
- [x] **D04 — Done:** Include the collection script. It handles pagination, duplicate IDs, transient failures, rate limits, source attribution and atomic output.
- [x] **D05 — Done:** Preserve full country and timezone restrictions, seniority, expiry, collection time and the source-provided application link. Expired rows are excluded from recommendations.
- [ ] **D06 — External check incomplete:** Sampled source pages returned HTTP 403 to the checker; a normal browser showed a security-verification screen. The public JSON API worked. External source pages cannot be marked verified from this environment.

Evidence: `scripts/scrape_jobs.py`, `scripts/audit_dataset.py`, `docs/data-audit.json` and the dataset contract test.

## Expected user flow

- [x] **F01 — Done:** Upload a **PDF** resume inside the conversation. Verified with the user's newer resume and synthetic test fixtures.
- [x] **F02 — Done:** Upload a **DOCX** resume inside the conversation, including paragraph/table content in document order.
- [x] **F03 — Done:** Automatically extract and display the candidate's **name**.
- [x] **F04 — Done:** Automatically extract and display **contact details**. Contact values are excluded from committed verification reports.
- [x] **F05 — Done:** Extract **designation**, including “Software Engineering Intern” from work history.
- [x] **F06 — Done:** Extract **skills**, including symbol/alias forms such as C++, React.js, TailwindCSS and Express.js.
- [x] **F07 — Done:** Extract **experience** and estimate work duration from dated work entries. The user's June–August internship is three inclusive calendar months; college/project dates do not inflate it.
- [x] **F08 — Done:** Extract **education**.
- [x] **F09 — Done:** Extract **projects** and retain all three project titles and their text in the user's resume.
- [x] **F10 — Done:** Recommend jobs using **designation, skills and experience**, with a grounded reason for each card. Senior/staff/architect roles are excluded for the tested junior profile.
- [x] **F11 — Done:** Refine naturally with “show only remote roles” and “jobs needing React”. Also tested multiple skills, India, entry-level roles, internships, filter removal and more results.
- [x] **F12 — Done for local workflow:** “Apply to job 3” invokes the application tool, creates a dated record once and returns the original application link. Explicit simulation mode records a labeled demo submission and receipt.
- [ ] **F13 — Partial:** **Real employer automatic submission** is not implemented. Assisted mode requires the candidate to complete the external form; simulation does not contact an employer. This requirement remains a real assessment gap if the evaluator expects actual third-party submission.
- [x] **F14 — Done:** “Show my applied jobs” lists records with job IDs, dates, statuses and original links. A confirmation updates submitted status and date.

Evidence: parser, matching, agent and HTTP tests; `scripts/verify_local.py`; browser upload/filter/details/application checks.

## Functional requirements

- [x] **R01 — Done:** A conversational assistant, with resume upload in the conversation and subsequent requests handled as messages.
- [x] **R02 — Done:** An orchestrator with specialized parsing, matching, profile, application and status tools.
- [x] **R03 — Done:** Gemini is the default function-calling provider. Arguments are validated with the server's schema before dispatch. An explicit OpenAI option retains its strict schema. Invalid arguments, provider failure and Gemini quota exhaustion fall back to local rules without switching providers.
- [x] **R04 — Done:** Gemini 3.8 Flash passed both a live synthetic function call and the complete HTTP chat/orchestrator/matching flow. Keys are stored only in ignored local configuration. Redacted evidence is in `docs/llm-verification.json`.
- [x] **R05 — Done:** Conversation memory and rich results survive reload through SQLite-backed history.
- [x] **R06 — Done:** Applications store job ID, initiation/submission dates and status. Duplicate protection is enforced by a unique database key, including simultaneous requests.
- [x] **R07 — Done:** Unreadable, empty, scanned, password-protected, unsupported and oversized resume errors are handled clearly.
- [x] **R08 — Done:** No-match results and invalid references return recovery instructions.
- [x] **R09 — Done:** Authentication is not required; anonymous workspaces are isolated by UUID.
- [x] **R10 — Done:** REST input validation, structured errors, request IDs, bounded uploads, provider timeout handling and request rate limits are present.

## UI and local quality review

- [x] **Q01 — Done:** Black glass panels, muted purple accents and an original Orbit visual identity replace the earlier light interface.
- [x] **Q02 — Done:** Desktop (1280×720), tablet (768×1024) and phone (390×844) layouts inspected. No horizontal overflow at the tested widths.
- [x] **Q03 — Done:** Input remains available while results scroll; header scrolling bug corrected.
- [x] **Q04 — Done:** Full job details, complete resume sections, source links, loading states, retries and removable filter chips work.
- [x] **Q05 — Done:** Keyboard labels, dialog close behavior, visible focus, reduced-motion support and icon-only navigation labels checked. This is not a formal WCAG certification.
- [x] **Q06 — Done:** Reload restores cards and filters; application counts stay in sync; actions on old cards use stable job IDs.
- [x] **Q07 — Done:** API isolation and workspace reset tested. Resume files, contact values, `.env`, local databases and private test output are excluded from Git.
- [x] **Q08 — Done:** JavaScript syntax and Python compilation checked. Automated test results and environment details are recorded in `docs/verification.json`.
- [x] **Q09 — Done:** Interactive API documentation renders with a separate nonce-based policy; the main workspace retains its stricter policy.
- [x] **Q10 — Done:** The isolated installation completed after earlier network timeouts. `pip check` and all 45 tests passed inside `.venv`, including Gemini routing and provider-isolation regressions. A separate synthetic running-server check passed 13/13 checkpoints. The exact GitHub Actions run and source commit are in `docs/ci-verification.json`.

## Submission deliverables and timing

- [x] **S01 — Done:** Full source code exists in the local Git repository.
- [x] **S02 — Done:** JSON job database and scraper are included.
- [x] **S03 — Done:** README covers setup, agent architecture, dataflow, APIs, configuration, limitations and verification commands.
- [x] **S04 — Done:** A 3–5 minute recording outline is prepared in `DEMO.md`.
- [x] **S05 — Done:** Public source repository: https://github.com/ABHISHEK27Y/hidani-assessment. Its JSON catalogue, scraper, documentation and tests are included.
- [ ] **S06 — User deployment:** Docker, Compose, Railway configuration, deployment instructions and a synthetic smoke checker are supplied. The user will create the live link and run the public-domain check.
- [ ] **S07 — Pending release:** The actual 3–5 minute screen recording.
- [ ] **S08 — Pending release:** Final submission of URLs, code/data and recording.
- [x] **S09 — Deadline recorded:** Assessment received **19 October 2026**; five days later is **24 October 2026**. Submit earlier if possible because no exact cutoff time was provided.

The user has taken over deployment. Before calling the full assessment complete, resolve the external application expectation, configure the Gemini key on the host, deploy, and record the live flow. See `DEPLOYMENT.md` for the handoff.
