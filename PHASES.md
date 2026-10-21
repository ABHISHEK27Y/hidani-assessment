# Delivery phases

The assessment was received on **19 October 2026**. Five days from receipt is **24 October 2026**; aim to submit before that date's end and avoid relying on an unspecified cutoff time.

| Phase | Outcome | State |
|---|---|---|
| 1. Requirement and source review | Convert brief to acceptance criteria, choose a permitted job source and honest application behavior | Complete |
| 2. Dataset and core agents | Collect 1,500–2,000 real jobs; parse resumes; rank and explain matches; route conversation; persist tracker | Complete |
| 3. Product polish and verification | Responsive chat UI, tests, malformed-file handling, zero-match handling, duplicate protection, accessibility review | In progress |
| 4. Public release | Public GitHub repository, persistent Docker deployment, live smoke test, source-link validation | Pending account access |
| 5. Submission package | 3–5 minute full-flow recording, final README review, submit live URL and repo | Pending release |

## Review gates

1. Run `python -m pytest -q --basetemp=.pytest_run` and check `/health` reports 1,800 jobs.
2. Use a sample PDF and DOCX resume; verify name, contact, designation, skills, experience, education, and projects. Edit parser heuristics if a real format exposes a gap.
3. Ask “show only remote roles”, “jobs needing React”, and a location query. Verify result reasons and that senior roles do not rank for a junior profile when experience is known.
4. Start the same application twice and confirm the tracker still has one record. Open its original link. Mark it submitted only after completing the external application.
5. Deploy with a persistent volume and repeat the flow on the live URL. Redeploy once to verify data survives.
6. Record a continuous 3–5 minute walkthrough and include a clear explanation of external submission limits in the narration.

## Interview talking points

- Why the agent separates intent interpretation from authoritative tools and data.
- Why deterministic matching is explainable and less prone to invented claims.
- How cursor pagination, deduplication, retries, and source attribution work.
- How anonymous session state and a unique database key prevent duplicate applications.
- Why the app distinguishes starting an application from third-party submission.
- How a production version would add OAuth/ATS-specific integrations, encryption, retention controls, and richer semantic ranking.
