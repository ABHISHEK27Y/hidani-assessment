# Run and deploy Orbit

## Windows: start locally

Install Python 3.11 or newer. Extract the source ZIP, open PowerShell in the extracted project folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

The script creates `.venv`, installs runtime dependencies with the tested constraints, creates `.env` from the example if it is missing, and starts the app at **http://127.0.0.1:8000**. It does not overwrite an existing `.env`.

After the first installation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 -SkipInstall
# If 8000 is in use:
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 -SkipInstall -Port 8001
```

The policy option applies only to this script process. It does not change the machine's saved execution policy. To stop the app, press Ctrl+C in its terminal.

## macOS/Linux: start locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Copy the example only when `.env` does not already contain your configuration.

## Optional OpenAI configuration

Local parsing, recommendations, supported chat commands and tracking work without a provider key. Ambiguous phrasing can use OpenAI function calling when a key is configured.

1. Open [OpenAI API keys](https://platform.openai.com/api-keys), sign in, select your project and create a secret key.
2. Check your account's API billing/available test credits. Ongoing API usage is priced separately from ChatGPT subscription usage; do not assume a subscription supplies API credit.
3. Edit the ignored `.env` locally:

```dotenv
OPENAI_API_KEY=replace_with_your_actual_key
OPENAI_MODEL=gpt-4o-mini
DATABASE_PATH=data/app.db
JOBS_PATH=data/jobs.json
APPLICATION_MODE=assisted
```

4. Verify one synthetic function call:

```powershell
.\.venv\Scripts\python.exe scripts/check_llm.py
```

This command may incur provider usage charges. It sends a synthetic search request, not your resume. Restart the server after changing `.env`. Keep secrets out of screenshots, chat messages, Git and browser-side JavaScript.

References: [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart), [API pricing](https://developers.openai.com/api/docs/pricing), [ChatGPT subscription pricing](https://learn.chatgpt.com/docs/pricing).

## Docker Compose

With Docker Desktop/Engine running:

```bash
docker compose up --build -d
docker compose logs -f
```

Open **http://127.0.0.1:8000**. The named `orbit-data` volume preserves SQLite data when the container is replaced. `docker compose down` stops the service; do not add `-v` unless you intend to remove that persistent volume.

## Railway: deploy your GitHub repository

1. In Railway, create a project and deploy **ABHISHEK27Y/hidani-assignmnet** from GitHub. Select the branch containing the latest release commit (`main` after publication).
2. Railway reads `railway.json` and builds the included Dockerfile. You do not need Node.js or a frontend build command.
3. Attach a **persistent volume mounted at `/data`** to this service.
4. Set the service variables below. The first one is required for persistent application history:

| Variable | Value |
|---|---|
| `DATABASE_PATH` | `/data/app.db` |
| `APPLICATION_MODE` | `assisted` |
| `OPENAI_API_KEY` | Your key, if you want live model interpretation |
| `OPENAI_MODEL` | `gpt-4o-mini`, or an available compatible model |

The catalogue is bundled in the image. Leave `JOBS_PATH` unset. Railway injects `PORT`, which the container start command reads automatically. Keep **one replica** for this SQLite deployment.

5. Generate a public domain. The configured readiness path is **`/health`**. Confirm that it reports `ok: true` and 1,800 catalogue rows.
6. From your local project folder, install the development requirements and run a synthetic deployment check:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c constraints.txt
.\.venv\Scripts\python.exe scripts/smoke_test.py --base-url https://YOUR-DOMAIN.up.railway.app
```

The checker uploads a fictional resume, filters jobs, initiates a tracked application, checks duplicate prevention, restores history, and deletes its own workspace. It does not submit anything to a real employer.

7. In the browser, upload a consented resume, refine results and initiate an application. Reload to confirm the cards return. Redeploy once and confirm the same workspace persists; this verifies that the volume and `DATABASE_PATH` are configured correctly.
8. Record the 3–5 minute walkthrough described in `DEMO.md` on the public URL.

Railway plan limits and infrastructure charges depend on your account. Check the dashboard before enabling paid resources. See [Railway config reference](https://docs.railway.com/config-as-code/reference), [volumes](https://docs.railway.com/volumes) and [healthchecks](https://docs.railway.com/deployments/healthchecks).

## Application submission limitation

Assisted mode saves an application and opens the original employer form. The candidate completes that form, then confirms submission in Orbit. Simulation mode is an explicitly labeled local demo with no employer delivery. Neither is automatic employer submission.

Greenhouse/Lever submission integrations require the employer's authorized credentials and job-specific required answers. See the [Greenhouse Job Board API](https://docs.greenhouse.io/job-board) and [Lever Postings API](https://github.com/lever/postings-api). No employer credentials are bundled or assumed. Explain this gap in the assessment demo rather than claiming that a local receipt proves delivery.

## Troubleshooting

| Symptom | Action |
|---|---|
| `python` not recognized | Install Python 3.11+ and enable its PATH option; reopen the terminal. |
| Installation times out | Retry on a stable connection. Preserve `requirements.txt` and `constraints.txt`; do not replace versions randomly. |
| Server says address is in use | Choose another `-Port` locally, or stop the previous app process. |
| Railway history disappears | Verify the `/data` volume and `DATABASE_PATH=/data/app.db`, then redeploy. |
| Model calls fall back to rules | Run `scripts/check_llm.py`; check key, billing, model access and connectivity. |
| Upload says scanned/unreadable | Export a text-based PDF or DOCX; OCR is not included. |
| External application page shows verification/login | Complete the source site's normal flow. Orbit does not bypass it. |

The source bundle intentionally excludes `.env`, private resumes, local SQLite databases and `.venv`. Recreate dependencies and configuration using the commands above.
