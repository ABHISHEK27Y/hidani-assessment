# Run and deploy Orbit

## Run locally

Use Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000`. On Windows, `powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1` performs the first-time setup and starts the same app. The runner creates `.env` from `.env.example` only if the file does not already exist. The app loads `.env` automatically; Git excludes it.

The dataset is already included at `data/jobs.json`. SQLite is used locally by default, so no separate database server is required. Local matching, supported chat commands and application tracking work without an LLM key. For ambiguous requests, set `GEMINI_API_KEY` in `.env` and restart the app. `LLM_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.5-flash-lite` are the defaults. Keep keys out of Git and recordings.

## Deploy on Render

The assessment deployment is [live on Render](https://orbit-assessment-r2j9.onrender.com). The repository's `render.yaml` defines a Docker web service and PostgreSQL database. The database connection is injected as `DATABASE_URL`; the web service stores no application history on its container filesystem.

1. Connect this repository's `main` branch in Render and deploy the root `render.yaml` as a Blueprint.
2. Review both services and their plan before deploying. Enter `GEMINI_API_KEY` in Render's secret field; never add the value to the repository.
3. Wait for `/health` to return `ok: true` and `jobs: 1800`. Render's free web service can take time to wake after inactivity.
4. Keep Auto-Deploy enabled for the web service. Pushing `main` then deploys code updates. Blueprint Auto Sync controls changes to `render.yaml` separately.

The app handles provider failure by using local rules. It does not switch to another provider automatically. The Google project's own tier and quota control Gemini billing and availability. Raw resume files and extracted profile payloads are not sent to Gemini; ambiguous chat text can be sent. Use fictional data in public demos.

## Verify the release

```bash
python -m pytest -q --basetemp=.pytest_run
python scripts/audit_dataset.py
node --check static/app.js
python scripts/smoke_test.py --base-url https://orbit-assessment-r2j9.onrender.com
```

The smoke test uses fictional data and removes its disposable workspace. It checks upload, matching, application tracking, duplicate prevention and history. GitHub Actions runs the tests, builds the Docker image and exercises the HTTP flow against both SQLite and PostgreSQL.

For the required 3–5 minute screen recording, use the single [phone-friendly guide](output/pdf/Orbit_3_Minute_Video_Guide.pdf). It contains the spoken script, all screenshot cues and OBS setup. Demonstrate the deployed app, then briefly show the JSON dataset and scraper in GitHub.

## Application limitation

In assisted mode, “apply to job 3” saves one dated record and opens the original employer form. The candidate completes that external form and can then confirm submission in Orbit. Simulation mode creates a clearly labeled local demo receipt. Neither mode automatically submits to an employer. Explain this assessment gap clearly in the recording.

## Troubleshooting

| Symptom | Check |
|---|---|
| App wakes slowly | The free Render web service may be idle; open it before recording. |
| Model uses local rules | Check the Gemini key, model access, quota and connection. Run `python scripts/check_llm.py` locally with a synthetic request. |
| Upload says scanned or unreadable | Export a text-based PDF or DOCX; OCR is not included. |
| No application history after redeploy | Confirm `DATABASE_URL` points to the Render PostgreSQL database. |
| Employer page asks for login or verification | Complete the employer's normal process. Orbit does not bypass it. |

Never commit `.env`, a private resume, local databases or a recording that exposes credentials or contact details.
