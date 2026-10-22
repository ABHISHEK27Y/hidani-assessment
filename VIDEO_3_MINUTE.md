# Three-minute assessment walkthrough

Read the **Say** text aloud while following the **Show** instructions. Aim for about three minutes. Use the public app, a fictional or redacted resume, and a warmed-up Render tab. The [numbered screenshot guide](docs/video-guide/README.md) marks the target for your mouse pointer; the pictures are a rehearsal guide, not slides to replace the live demo.

## 0:00–0:18 — Introduce Orbit

**Show:** Open `https://orbit-assessment-r2j9.onrender.com` in a browser. Keep the address bar and 1,800-job count visible. Point at **Choose file**.

**Say:** “Hi, I’m Abhishek. This is Orbit, my job-search assistant for the Hidani Tech assessment. It reads a resume, finds suitable roles from a real job dataset, refines results through chat, and tracks application progress. I’ll show the live flow.”

## 0:18–0:48 — Resume upload and extraction

**Show:** Click **Choose file**, upload the prepared PDF. Point at the extracted profile, then open the full profile to show work experience, education, projects and skills.

**Say:** “The upload accepts PDF and DOCX. Python extracts the candidate’s name, contact, designation, skills, dated work experience, education and projects. Work duration comes from work entries, not college or project dates. The structured profile appears beside the conversation.”

## 0:48–1:18 — Recommendations and chat refinement

**Show:** Point at a job card’s **The fit** explanation. In the chat type `remote React jobs in India`. Point at the active filter chips and refreshed results. If the demo resume gives no matches, use `remote React jobs` instead.

**Say:** “The matcher ranks relevant jobs by role, skills, experience and location. Each card explains why it fits. I can refine the same search in normal language; here I’m asking for remote React roles available in India. The filters and conversation stay in this workspace.”

## 1:18–1:43 — Details and application

**Show:** Click **Details** on a result, point at the full description and source link, close it, then click **Start application** on a result.

**Say:** “The details view keeps the original description and source link. Starting an application creates one dated tracker record and opens the employer’s original form. This is assisted application tracking: the user completes the external form. Orbit does not submit it to an employer automatically.”

## 1:43–2:05 — Tracker and persistence

**Show:** Click **Applications** in the left sidebar. Point at the status and date, then refresh the browser and show that the record returns. Do not click **I submitted this** unless the employer form was truly submitted.

**Say:** “The tracker shows the job, start date and current status. Repeating the same application does not duplicate it. On Render, PostgreSQL preserves the profile, conversation and application records after refresh. The assessment requires no login.”

## 2:05–2:40 — How it works

**Show:** Switch to the GitHub repository. Point in turn at `data/jobs.json`, `scripts/scrape_jobs.py`, the README architecture diagram, and `app/agent.py`. Keep this brisk; open those tabs before recording.

**Say:** “The assignment asked for 1,500 to 2,000 real listings, a JSON database and collection script. My collector fetched 1,800 unique Himalayas listings, validated required fields and removed duplicates. FastAPI handles uploads and chat. The agent routes requests to parsing, matching and application tools. Gemini interprets ambiguous requests, and the server validates its function arguments. Recommendations come from the saved dataset, not invented model results.”

## 2:40–3:00 — Verification and finish

**Show:** Open `ASSESSMENT_CHECKLIST.md`, point at the checked features and the clearly marked external-submission limitation. Finish on the live app tab.

**Say:** “The app handles invalid job numbers, unsupported resumes and searches with no matches. Thirteen public checks and forty-five automated tests passed. The repository contains the source, dataset, scraper and setup guide. The remaining functional gap is automatic submission to third-party employer forms. Thank you for reviewing Orbit.”

## Recording setup

1. In OBS’s first-run wizard, choose **Optimize just for recording**. Add **Window Capture** for the browser; use **Display Capture** if Window Capture is blank.
2. Check the **Mic/Aux** meter while speaking. Record ten seconds and play it back before the full take.
3. Use one browser window with the live app and the pre-opened GitHub tabs. Keep browser zoom at 90–100%, notifications off, and keys or private contact details out of view.
4. Keep the pointer still on the feature you are discussing. Move it only when switching to the next feature; avoid circling or shaking it.
5. Export the recording as an MP4, watch the whole file once, and confirm the final sharing link opens without requesting access.
