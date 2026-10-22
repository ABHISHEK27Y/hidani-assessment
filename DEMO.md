# Five-minute assessment video script

For a faster walkthrough, use the [three-minute script](VIDEO_3_MINUTE.md) and its [annotated screenshot guide](docs/video-guide/README.md).

Record after the public deployment passes its checks. Speak slowly and pause while results load. Aim for 4:40–5:00. Read the quoted paragraphs; the other lines tell you what to show. Do not describe localhost as a deployed app.

Before recording, open the app and GitHub in two tabs, prepare a readable PDF or DOCX resume, and hide private contact details if needed. Keep API keys and hosting settings off screen. Use assisted mode. This walkthrough does not send a real employer application.

## 0:00–0:30 — Introduce the project

Show the app and its address bar.

“Hi, I am Abhishek Yadav. This is Orbit, my AI job chat assistant for the Hidani Tech assessment. It helps a user upload a resume, find suitable jobs, refine the results through chat, and track applications. I built the backend with Python and FastAPI, and the interface with JavaScript. I will show the complete flow and explain one limitation in the application step.”

## 0:30–1:15 — Upload and read a resume

Click **Choose file**, select the resume, and show the profile. Expand work experience, education and projects.

“I am uploading a resume directly inside the conversation. The app supports PDF and DOCX. It extracts the name, contact details, designation, skills, work experience, education and projects. Here are the extracted details. Work duration comes from the dates in the experience section. College dates and project dates are not counted as work experience. If something needs correction, I can update the role or experience through chat.”

## 1:15–2:00 — Explain and refine matches

Show a job card and its reason. Send **show only remote roles**, then **jobs needing React**, then **jobs in India**. Wait for each reply.

“The app compares the profile with a dataset of 1,800 real job listings. Matching uses the candidate's role, skills and experience. Each result explains why it was selected. The cards also show the company, location, required skills and source link. I can narrow the results with normal messages. I am asking for remote roles, then React jobs, and then jobs available in India. The app remembers these filters across the conversation.”

## 2:00–2:50 — Apply and show duplicate protection

Confirm at least three results exist. Send **apply to job 3**. Show the application card, then send the same command again.

“Now I am asking the assistant to apply to job three. In this version, applying is an assisted workflow. The app creates an application record and gives me the original application link. I must complete the employer's form myself. The app does not automatically submit that external form, so this is a limitation of my implementation. The status stays awaiting submission until I confirm that I have completed it. When I ask again, the app keeps the same record instead of creating a duplicate.”

## 2:50–3:20 — Track and restore

Send **show my applied jobs**. Show the job, date and status. Reload. Do not click **I submitted this** unless you actually submitted the external form.

“Here I can see my tracked application, its date and its current status. The hosted app saves profile, messages and application records in PostgreSQL. When I refresh the browser, the conversation and results return. Each anonymous workspace has its own records, and the app does not require a login.”

## 3:20–3:50 — Show error handling

Send **apply to job 999**, then **find zzzimpossiblezzz jobs**.

“The app also handles errors. An invalid job number gives a clear message instead of starting an application. A search with no matches explains how to broaden the search. Unreadable resumes, unsupported files and oversized uploads also have clear error messages. The automated tests cover these cases.”

## 3:50–4:35 — Explain the architecture and source

Switch to GitHub. Show the README diagram, `data/jobs.json`, `scripts/scrape_jobs.py`, and `app/agent.py`.

“The main agent coordinates tools for resume parsing, matching, applying and checking status. Gemini interprets requests that need language understanding. Its function arguments are validated before a tool runs. Simple requests can use local rules, which also keep the basic flow working if the provider is unavailable. The model does not invent job listings. The scraper collects listings from the Himalayas public API, removes duplicates, and saves the JSON dataset. Missing experience requirements are shown as not specified.”

## 4:35–5:00 — Finish

Show the checklist and test evidence. Only mention a live link after deployment succeeds.

“The repository includes the full source, dataset, scraper, setup instructions, API documentation and deployment configuration. Forty-five automated tests passed, along with the resume and running-server checks. My main remaining functional limitation is automatic submission to external employers. Thank you for reviewing my assessment.”

## Submission reminder

- Submit the verified live URL, public GitHub URL and actual screen recording.
- This script is not a recording. Record your own walkthrough and voice.
- Keep the application limitation visible in the checklist and narration.
- If fewer than three jobs match, use an available number and say that number consistently.
