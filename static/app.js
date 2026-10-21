"use strict";

const $ = (id) => document.getElementById(id);
const iconPaths = {
  plus: ["M12 5v14", "M5 12h14"], close: ["m6 6 12 12", "M18 6 6 18"],
  chat: ["M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l-3 3V11.5A7.5 7.5 0 0 1 9.5 4h3A7.5 7.5 0 0 1 20 11.5Z", "M7 10h8", "M7 14h5"],
  briefcase: ["M4 7h16v13H4z", "M9 7V4h6v3", "M4 12c5 3 11 3 16 0", "M10 13h4v3h-4z"],
  user: ["M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z", "M4 21v-2a8 8 0 0 1 16 0v2"],
  shield: ["m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z", "m8 12 3 3 5-6"],
  file: ["M6 3h8l4 4v14H6z", "M14 3v5h4", "M9 12h6", "M9 16h4"],
  "arrow-up-right": ["M6 18 18 6", "M6 6h12v12"], "arrow-up": ["M12 19V5", "m6 11 6-6 6 6"],
  globe: ["M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z", "M3 12h18", "M12 3c5 5 5 13 0 18", "M12 3c-5 5-5 13 0 18"],
  layers: ["m3 8 9-5 9 5-9 5Z", "m3 12 9 5 9-5", "m3 16 9 5 9-5"],
  compass: ["M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z", "m16 8-3 5-5 3 3-5Z"],
  paperclip: ["m8 13 7-7a3 3 0 0 1 4 4L9 20a5 5 0 0 1-7-7L12 3", "m6 14 7-7"],
  external: ["M14 3h7v7", "m10 14 11-11", "M10 3H3v18h18v-7"],
  fingerprint: ["M5 16v-5a7 7 0 0 1 14 0v5", "M8 18v-7a4 4 0 0 1 8 0v8", "M12 10v10", "M3 11v2", "M21 11v2"],
  pin: ["M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z", "M14 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z"],
  clock: ["M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z", "M12 7v5l3 2"],
  orbit: ["M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z", "M4 19 20 5", "M17 4h4v4"],
};

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  for (const d of iconPaths[name] || iconPaths.orbit) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}
document.querySelectorAll("[data-icon]").forEach((el) => el.append(icon(el.dataset.icon)));

function el(tag, text = "", className = "") {
  const node = document.createElement(tag);
  node.textContent = text ?? "";
  if (className) node.className = className;
  return node;
}

function button(text, callback, className = "button button-quiet") {
  const node = el("button", text, className);
  node.type = "button";
  node.addEventListener("click", callback);
  return node;
}

function externalLink(text, href, className = "button button-quiet") {
  const node = el("a", text, className);
  try {
    const url = new URL(href);
    if (url.protocol !== "https:" || url.username || url.password) throw new Error("Invalid link");
    node.href = url.href;
  } catch { node.removeAttribute("href"); node.setAttribute("aria-disabled", "true"); }
  node.target = "_blank";
  node.rel = "noopener noreferrer";
  return node;
}

let sessionId;
try { sessionId = localStorage.getItem("orbit-session-id"); } catch { /* Session works in memory when storage is unavailable. */ }
if (!/^[0-9a-f-]{36}$/i.test(sessionId || "")) sessionId = crypto.randomUUID();
function saveSession() { try { localStorage.setItem("orbit-session-id", sessionId); } catch { /* Memory-only session. */ } }
saveSession();

const messages = $("messages");
const input = $("message-input");
const fileInput = $("resume-file");
let currentProfile = null;
let busy = false;
let applicationMode = "assisted";
let toastTimer;

function toast(text) {
  clearTimeout(toastTimer);
  $("toast").textContent = text;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4500);
}

function setBusy(value) {
  busy = value;
  for (const id of ["send-button", "attach-button", "welcome-upload", "rail-upload", "confirm-reset"]) $(id).disabled = value;
  $("conversation").setAttribute("aria-busy", String(value));
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join("; ") : data.detail;
      throw new Error(detail || `Request failed (${response.status}). Please retry.`);
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("This request took too long. Check your connection and try again.");
    if (error instanceof TypeError) throw new Error("I couldn’t reach the server. Check your connection and retry.");
    throw error;
  } finally { clearTimeout(timeout); }
}

function addMessage(role, content, { error = false, timestamp = null } = {}) {
  $("welcome").hidden = true;
  const row = el("div", "", `message-row ${role}`);
  if (role === "assistant") {
    const avatar = el("div", "", "avatar"); avatar.append(icon("orbit")); row.append(avatar);
  }
  const box = el("div", "", "message-content");
  if (role === "assistant") {
    const speaker = el("div", "Orbit", "speaker");
    const time = new Date(timestamp || Date.now());
    const clock = el("time", time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    clock.dateTime = time.toISOString(); speaker.append(clock); box.append(speaker);
  }
  const bubble = el("div", content, `bubble${error ? " error-bubble" : ""}`);
  box.append(bubble); row.append(box); messages.append(row);
  return { row, box, bubble };
}

function scrollToRow(row) {
  const region = $("conversation");
  const top = row.getBoundingClientRect().top - region.getBoundingClientRect().top + region.scrollTop - 20;
  region.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

function pending(text) {
  const message = addMessage("assistant", "");
  message.row.classList.add("pending");
  message.bubble.append(el("span", text));
  const dots = el("span", "", "loading-dots");
  for (let i = 0; i < 3; i++) dots.append(el("i"));
  message.bubble.append(dots);
  $("typing-status").textContent = text;
  scrollToRow(message.row);
  return () => { message.row.remove(); $("typing-status").textContent = ""; };
}

function renderProfile(container, profile) {
  if (!profile) return;
  const panel = el("section", "", "profile-inline");
  panel.append(el("h3", profile.name));
  const duration = profile.experience_months == null ? "Duration not found" : `${profile.experience_months} months of work experience`;
  panel.append(el("p", `${profile.designation} · ${duration}`, "profile-designation"));
  const contact = el("div", "", "profile-contact");
  contact.append(el("span", profile.email), el("span", profile.phone)); panel.append(contact);
  const tags = el("div", "", "tag-list");
  (profile.skills || []).forEach(skill => tags.append(el("span", skill, "tag matched")));
  panel.append(tags);
  for (const [label, values] of [["Work experience", profile.experience], ["Education", profile.education], ["Projects", profile.projects]]) {
    const detail = document.createElement("details");
    detail.append(el("summary", label));
    detail.append(el("div", values?.length ? values.join("\n") : "Not found in this resume", "profile-lines"));
    if (label === "Projects" && profile.project_titles?.length) {
      const titles = el("p", profile.project_titles.join(" · "), "profile-lines");
      panel.append(titles);
    }
    panel.append(detail);
  }
  for (const warning of profile.warnings || []) panel.append(el("p", warning, "profile-warning"));
  container.append(panel);
}

function updateRail(profile) {
  currentProfile = profile;
  const rail = $("profile-box"); rail.replaceChildren();
  $("rail-upload").textContent = profile ? "View ↗" : "Upload +";
  if (!profile) {
    const placeholder = el("div", "", "profile-placeholder");
    placeholder.append(icon("fingerprint"), el("p", "Your experience is the starting point."), el("span", "Upload a resume to see your skills and work history here."));
    rail.append(placeholder); return;
  }
  const header = el("div", "", "rail-profile-name");
  header.append(el("div", profile.name?.[0] || "?", "profile-initial"));
  const person = el("div"); person.append(el("strong", profile.name), el("small", profile.designation)); header.append(person); rail.append(header);
  rail.append(el("p", profile.experience_months == null ? "Experience duration not detected" : `${profile.experience_months} months · ${profile.experience_source}`, "rail-experience"));
  rail.append(el("p", `${profile.skills?.length || 0} SKILLS FOUND`, "rail-skills-label"));
  const tags = el("div", "", "tag-list");
  (profile.skills || []).slice(0, 10).forEach(skill => tags.append(el("span", skill, "tag")));
  if (profile.skills?.length > 10) tags.append(el("span", `+${profile.skills.length - 10}`, "tag"));
  rail.append(tags);
}

function renderJobs(container, jobs, total) {
  if (!jobs?.length) return;
  const heading = el("div", "", "results-heading");
  heading.append(el("span", "Selected opportunities"), el("span", `${jobs.length} shown${total ? ` · ${total} matches` : ""}`));
  container.append(heading);
  const list = el("div", "", "job-list");
  jobs.forEach((job, index) => {
    const card = el("article", "", "job-card");
    const top = el("div", "", "job-card-top");
    top.append(el("span", `JOB ${String(index + 1).padStart(2, "0")}`, "job-number"), externalLink(`${job.source} ↗`, job.source_link, "job-source"));
    card.append(top, el("h3", job.title), el("div", job.company, "job-company"));
    const meta = el("div", "", "job-meta");
    for (const [name, value] of [["pin", job.location], ["clock", job.experience_required]]) {
      const line = el("span"); line.append(icon(name), document.createTextNode(value)); meta.append(line);
    }
    card.append(meta);
    const tags = el("div", "", "tag-list");
    const matched = job.matched_skills || [];
    const allSkills = [...new Set([...matched, ...(job.skills || [])])].slice(0, 4);
    allSkills.forEach(skill => tags.append(el("span", skill, `tag${matched.includes(skill) ? " matched" : ""}`)));
    card.append(tags);
    const reason = el("div", "", "job-reason");
    reason.append(el("b", "THE FIT"), document.createTextNode(job.match_reason || "Matches your search preferences")); card.append(reason);
    const actions = el("div", "", "job-actions");
    actions.append(button("Start application", () => submitMessage(`apply to job ${index + 1}`, job.id), "button button-primary"), button("Details ↗", () => showJob(job.id)));
    card.append(actions); list.append(card);
  });
  container.append(list);
}

function applicationLabel(application) {
  if (application.delivery === "simulation") return ["Demo submission", "simulated"];
  return application.status === "submitted" ? ["Submitted · confirmed by you", "submitted"] : ["Awaiting submission", ""];
}

function renderApplications(container, applications) {
  const list = el("div", "", "applications-list");
  for (const application of applications) {
    const row = el("article", "", "app-row");
    const top = el("div", "", "app-row-top");
    const title = el("div");
    title.append(el("strong", application.job?.title || "Listing unavailable"), el("small", application.job?.company || application.job_id));
    const [label, type] = applicationLabel(application);
    top.append(title, el("span", label, `status-pill ${type}`)); row.append(top);
    const date = new Date(application.submitted_at || application.created_at || application.applied_at);
    row.append(el("small", `${application.submitted_at ? "Recorded" : "Started"} ${date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}${application.receipt ? ` · ${application.receipt}` : ""}`));
    const actions = el("div", "", "app-actions");
    if (application.job?.application_link) actions.append(externalLink("Original application ↗", application.job.application_link));
    if (application.status === "awaiting_submission") actions.append(button("I submitted this", () => submitMessage("I submitted this job", application.job_id), "button button-primary"));
    row.append(actions); list.append(row);
  }
  container.append(list);
}

function renderFilters(filters = {}) {
  const strip = $("filter-strip"); strip.replaceChildren();
  const definitions = [];
  if (filters.remote != null) definitions.push([filters.remote ? "Remote" : "On-site", "clear remote filter"]);
  if (filters.skills?.length) definitions.push([filters.skills.join(" + "), "clear skill filter"]);
  if (filters.location) definitions.push([filters.location, "clear location filter"]);
  if (filters.query) definitions.push([filters.query, "clear role filter"]);
  if (filters.level) definitions.push([filters.level === "intern" ? "Internships" : "Entry level", "clear experience filter"]);
  for (const [label, command] of definitions) {
    const chip = button(label, () => submitMessage(command), "filter-chip");
    chip.append(icon("close")); chip.setAttribute("aria-label", `Remove ${label} filter`); strip.append(chip);
  }
  strip.hidden = !definitions.length;
}

function renderResponse(data, { restore = false, timestamp = null } = {}) {
  const message = addMessage("assistant", data.reply, { timestamp });
  if (data.profile) { renderProfile(message.box, data.profile); if (!restore) updateRail(data.profile); }
  renderJobs(message.box, data.jobs, data.total);
  if (data.application) renderApplications(message.box, [data.application]);
  else if (Array.isArray(data.applications)) {
    if (data.applications.length) renderApplications(message.box, data.applications);
    else {
      const empty = el("div", "", "empty-state"); empty.append(icon("briefcase"), document.createTextNode("Your application tracker is ready for its first role.")); message.box.append(empty);
    }
  }
  if (data.has_more) {
    const actions = el("div", "", "inline-actions"); actions.append(button("Show more matches ↓", () => submitMessage("show more"))); message.box.append(actions);
  }
  if (data.total === 0) {
    const actions = el("div", "", "inline-actions"); actions.append(button("Clear filters", () => submitMessage("clear filters"))); message.box.append(actions);
  }
  if (!restore && data.filters) renderFilters(data.filters);
  if (!restore && data.application_count != null) $("application-count").textContent = data.application_count;
  if (data.job_detail && !restore) openJobDialog(data.job_detail);
  if (!restore) scrollToRow(message.row);
  return message;
}

function showError(error, retry) {
  const message = addMessage("assistant", error.message || "Something went wrong. Please retry.", { error: true });
  if (retry) { const actions = el("div", "", "inline-actions"); actions.append(button("Try again", retry)); message.box.append(actions); }
  scrollToRow(message.row);
}

async function submitMessage(value, jobId = null) {
  await ready;
  const text = (value ?? input.value).trim();
  if (!text || busy) return;
  if (text.length > 2000) { toast("Please keep your message under 2,000 characters."); return; }
  input.value = ""; input.rows = 1;
  addMessage("user", text);
  setBusy(true);
  const finish = pending(/apply|submitted/i.test(text) ? "Updating your application…" : "Looking into that…");
  try {
    const data = await request("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, message: text, job_id: jobId }) });
    finish(); renderResponse(data);
  } catch (error) { finish(); showError(error, () => submitMessage(text, jobId)); }
  finally { setBusy(false); input.focus({ preventScroll: true }); }
}

async function uploadResume(file) {
  await ready;
  if (!file || busy) return;
  if (!/\.(pdf|docx)$/i.test(file.name)) { toast("Please choose a PDF or DOCX resume."); return; }
  if (!file.size || file.size > 8 * 1024 * 1024) { toast("Choose a non-empty resume smaller than 8 MB."); return; }
  addMessage("user", `Uploaded resume: ${file.name}`);
  setBusy(true); const finish = pending("Reading your resume and finding matches…");
  const form = new FormData(); form.append("session_id", sessionId); form.append("file", file);
  try {
    const data = await request("/api/resume", { method: "POST", body: form });
    finish(); renderResponse(data);
  } catch (error) { finish(); showError(error, () => uploadResume(file)); }
  finally { setBusy(false); fileInput.value = ""; }
}

function openJobDialog(job) {
  const content = $("detail-content"); content.replaceChildren();
  const heading = el("h2", job.title); heading.id = "detail-title"; content.append(heading);
  const fullLocation = job.location_restrictions?.length ? `Remote — ${job.location_restrictions.join(", ")}` : job.location;
  content.append(el("p", `${job.company} · ${fullLocation}`, "dialog-meta"), el("p", `${job.experience_required} · ${job.employment_type || "Employment type not specified"}`, "dialog-meta"));
  const tags = el("div", "", "tag-list"); (job.skills || []).forEach(skill => tags.append(el("span", skill, "tag"))); content.append(tags);
  content.append(el("div", job.description, "dialog-description"));
  const actions = el("div", "", "dialog-actions");
  const start = button(job.active === false ? "Listing expired" : "Start application", () => { $("detail-dialog").close(); submitMessage("apply to this job", job.id); }, "button button-primary");
  start.disabled = job.active === false;
  actions.append(start, externalLink(`View on ${job.source} ↗`, job.source_link));
  content.append(actions);
  if (!$("detail-dialog").open) $("detail-dialog").showModal();
}

async function showJob(id) {
  try { openJobDialog(await request(`/api/jobs/${encodeURIComponent(id)}`)); }
  catch (error) { toast(error.message); }
}

function showProfile() {
  const content = $("profile-content"); content.replaceChildren();
  if (currentProfile) renderProfile(content, currentProfile);
  else { content.append(el("p", "Upload a PDF or DOCX resume to see your profile here.", "dialog-copy"), button("Choose resume", () => { $("profile-dialog").close(); fileInput.click(); }, "button button-primary")); }
  $("profile-dialog").showModal();
}

async function bootstrap() {
  setBusy(true);
  try {
    const data = await request(`/api/bootstrap?session_id=${encodeURIComponent(sessionId)}`);
    applicationMode = data.application_mode;
    $("dataset-count").textContent = data.job_count.toLocaleString();
    $("application-count").textContent = data.applications.length;
    $("connection-label").textContent = "Workspace ready";
    $("connection").classList.remove("offline");
    if (applicationMode === "simulation") {
      $("composer-note").textContent = "Application demo · submissions are simulated.";
      $("application-note").lastElementChild.textContent = "Demo mode records simulated submissions with receipts. No application is sent to an employer.";
    }
    for (const item of data.history || []) {
      if (item.role === "assistant" && item.payload) renderResponse(item.payload, { restore: true, timestamp: item.created_at });
      else addMessage(item.role, item.content, { timestamp: item.created_at });
    }
    updateRail(data.profile); renderFilters(data.filters);
    if (messages.lastElementChild) scrollToRow(messages.lastElementChild);
  } catch (error) {
    $("connection-label").textContent = "Connection unavailable";
    $("connection").classList.add("offline");
    toast(error.message);
  } finally { setBusy(false); }
}

const ready = bootstrap();
$("attach-button").addEventListener("click", () => fileInput.click());
$("welcome-upload").addEventListener("click", () => fileInput.click());
$("rail-upload").addEventListener("click", () => currentProfile ? showProfile() : fileInput.click());
fileInput.addEventListener("change", () => uploadResume(fileInput.files?.[0]));
$("send-button").addEventListener("click", () => submitMessage());
input.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); submitMessage(); } });
input.addEventListener("input", () => { input.rows = Math.min(4, Math.max(1, input.value.split("\n").length)); });
document.querySelectorAll("[data-prompt]").forEach(node => node.addEventListener("click", () => submitMessage(node.dataset.prompt)));
function navigate(view) {
  $("nav-chat").classList.toggle("active", view === "chat");
  $("nav-applications").classList.toggle("active", view === "applications");
  $("nav-chat").setAttribute("aria-current", view === "chat" ? "page" : "false");
  $("nav-applications").setAttribute("aria-current", view === "applications" ? "page" : "false");
  $("view-label").textContent = view === "chat" ? "Conversation" : "Applications";
  if (view === "applications") submitMessage("show my applied jobs");
  else input.focus();
}
$("nav-chat").addEventListener("click", () => navigate("chat"));
$("nav-applications").addEventListener("click", () => navigate("applications"));
$("mobile-applications").addEventListener("click", () => navigate("applications"));
for (const id of ["profile-button", "nav-profile"]) $(id).addEventListener("click", showProfile);
document.querySelectorAll(".dialog-close").forEach(node => node.addEventListener("click", () => node.closest("dialog").close()));
document.querySelectorAll("dialog").forEach(dialog => dialog.addEventListener("click", event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } }));
$("new-search").addEventListener("click", () => $("reset-dialog").showModal());
$("cancel-reset").addEventListener("click", () => $("reset-dialog").close());
$("confirm-reset").addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  try {
    await request(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    sessionId = crypto.randomUUID(); saveSession();
    messages.replaceChildren(); $("welcome").hidden = false;
    updateRail(null); renderFilters({}); $("application-count").textContent = "0";
    $("reset-dialog").close(); navigate("chat"); toast("A fresh workspace is ready.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
});
const dropzone = $("upload-dropzone");
dropzone.addEventListener("dragover", event => { event.preventDefault(); dropzone.classList.add("drag-over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", event => { event.preventDefault(); dropzone.classList.remove("drag-over"); if (event.dataTransfer.files.length !== 1) toast("Please upload one resume at a time."); else uploadResume(event.dataTransfer.files[0]); });
