const $ = (id) => document.getElementById(id);
const sessionKey = "orbit-session-id";
let sessionId = localStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionKey, sessionId);
}
const conversation = $("conversation");
const messages = $("messages");
const input = $("message-input");
const send = $("send-button");
const fileInput = $("resume-file");
let busy = false;
let hydrated = false;
const txt = (tag, value, className) => {
  const element = document.createElement(tag);
  element.textContent = value ?? "";
  if (className) element.className = className;
  return element;
};
const scrollBottom = () => { conversation.scrollTop = conversation.scrollHeight; };

function addMessage(role, content, error = false) {
  const row = txt("div", "", `message-row ${role}`);
  if (role === "assistant") row.append(txt("div", "✳", "avatar"));
  const box = txt("div", "", "message-content");
  if (role === "assistant") {
    const speaker = txt("div", "Orbit", "speaker");
    speaker.append(txt("span", "AI assistant"));
    box.append(speaker);
  }
  box.append(txt("div", content, `bubble${error ? " error-bubble" : ""}`));
  row.append(box);
  messages.append(row);
  scrollBottom();
  return box;
}

function renderJobs(container, jobs) {
  if (!jobs?.length) return;
  const list = txt("div", "", "job-list");
  jobs.forEach((job, index) => {
    const card = txt("article", "", "job-card");
    const top = txt("div", "", "job-card-top");
    top.append(txt("span", `MATCH ${String(index + 1).padStart(2, "0")}`, "job-number"));
    const source = txt("a", job.source || "Original source", "job-source");
    source.href = job.source_link;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    top.append(source);
    card.append(top);
    card.append(txt("h3", job.title));
    const meta = txt("div", "", "job-meta");
    meta.append(txt("strong", job.company));
    meta.append(txt("span", "·"));
    meta.append(txt("span", job.location));
    meta.append(txt("span", "·"));
    meta.append(txt("span", job.experience_required || "Experience not specified"));
    card.append(meta);
    const reason = txt("div", "", "job-reason");
    reason.append(txt("b", "Why it fits · "));
    reason.append(document.createTextNode(job.match_reason || "Relevant to your search"));
    card.append(reason);
    const actions = txt("div", "", "job-actions");
    const apply = txt("button", "Start application ↗");
    apply.addEventListener("click", () => submitMessage(`apply to job ${index + 1}`, job.id));
    actions.append(apply);
    const link = txt("a", "View original listing ↗");
    link.href = job.source_link;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    actions.append(link);
    card.append(actions);
    list.append(card);
  });
  container.append(list);
  scrollBottom();
}

function renderProfile(container, profile) {
  if (!profile) return;
  const panel = txt("div", "", "profile-inline");
  panel.append(txt("h3", "Resume snapshot"));
  const dl = document.createElement("dl");
  const fields = [
    ["Name", profile.name], ["Contact", [profile.email, profile.phone].filter(x => x && x !== "Not found").join(" · ") || "Not found"],
    ["Designation", profile.designation], ["Skills", profile.skills?.join(", ") || "Not found"],
    ["Experience", profile.experience?.slice(0, 2).join(" · ") || "Not found"],
    ["Education", profile.education?.slice(0, 2).join(" · ") || "Not found"],
    ["Projects", profile.projects?.slice(0, 2).join(" · ") || "Not found"]
  ];
  for (const [name, value] of fields) { dl.append(txt("dt", name)); dl.append(txt("dd", value)); }
  panel.append(dl);
  container.append(panel);
  renderRail(profile);
}

function renderRail(profile) {
  const rail = $("profile-box");
  rail.replaceChildren();
  if (!profile) {
    const empty = txt("div", "", "profile-empty");
    empty.append(txt("div", "↥", "profile-empty-icon"));
    empty.append(txt("strong", "Your profile starts here"));
    empty.append(txt("p", "Upload a resume and I’ll turn it into a useful snapshot for your search."));
    const button = txt("button", "Upload resume ↗");
    button.addEventListener("click", () => fileInput.click());
    empty.append(button);
    rail.append(empty);
    return;
  }
  const card = txt("div", "", "profile-card");
  const top = txt("div", "", "profile-top");
  top.append(txt("div", (profile.name || "?")[0].toUpperCase(), "profile-initial"));
  const person = txt("div", "");
  person.append(txt("strong", profile.name));
  person.append(txt("small", profile.designation));
  top.append(person);
  card.append(top);
  const skills = txt("div", "", "profile-detail");
  skills.append(txt("b", "SKILLS FOUND"));
  const tags = txt("div", "", "tag-list");
  (profile.skills || []).slice(0, 10).forEach(skill => tags.append(txt("span", skill, "tag")));
  if (!tags.children.length) tags.append(txt("span", "No skills detected yet", "empty-note"));
  skills.append(tags);
  card.append(skills);
  rail.append(card);
}

function renderApplications(container, applications) {
  if (!applications?.length) return;
  const list = txt("div", "", "applications-list");
  applications.forEach(app => {
    const row = txt("div", "", "app-row");
    row.append(txt("strong", `${app.job?.title || app.job_id} · ${app.job?.company || ""}`));
    const date = new Date(app.applied_at);
    row.append(txt("small", `${app.status === "submitted" ? "Submitted (confirmed by you)" : "Awaiting external submission"} · ${Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString()}`));
    const actions = txt("div", "", "app-actions");
    if (app.job?.application_link) {
      const link = txt("a", "Open application ↗");
      link.href = app.job.application_link;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actions.append(link);
    }
    if (app.status === "awaiting_submission") {
      const confirm = txt("button", "I submitted this");
      confirm.addEventListener("click", () => submitMessage("I submitted this job", app.job_id));
      actions.append(confirm);
    }
    row.append(actions);
    list.append(row);
  });
  container.append(list);
  scrollBottom();
}

function renderResponse(data) {
  const box = addMessage("assistant", data.reply || "I’m ready to help.");
  renderProfile(box, data.profile);
  renderJobs(box, data.jobs);
  renderApplications(box, data.applications);
  if (data.application?.job?.application_link) {
    const actions = txt("div", "", "suggestions");
    const link = txt("a", "Open application page ↗", "chip");
    link.href = data.application.job.application_link;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    actions.append(link);
    if (data.application.status === "awaiting_submission") {
      const confirm = txt("button", "I submitted this", "chip");
      confirm.addEventListener("click", () => submitMessage("I submitted this job", data.application.job_id));
      actions.append(confirm);
    }
    box.append(actions);
  }
  if (data.action === "resume") renderRail(data.profile);
  if (data.applications) $("application-count").textContent = data.applications.length;
}

async function submitMessage(value, jobId = null) {
  const message = (value ?? input.value).trim();
  if (!message || busy) return;
  input.value = "";
  input.style.height = "auto";
  addMessage("user", message);
  busy = true; send.disabled = true;
  try {
    const response = await fetch("/api/chat", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({session_id: sessionId, message, job_id: jobId})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Chat failed. Please try again.");
    renderResponse(data);
    if (data.action === "apply") refreshCount();
  } catch (error) { addMessage("assistant", error.message || "Something went wrong.", true); }
  finally { busy = false; send.disabled = false; input.focus(); }
}

async function uploadResume(file) {
  if (!file) return;
  if (!/\.(pdf|docx)$/i.test(file.name)) { addMessage("assistant", "Please choose a PDF or DOCX file.", true); return; }
  addMessage("user", `Uploaded resume: ${file.name}`);
  busy = true; send.disabled = true;
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);
  try {
    const response = await fetch("/api/resume", {method:"POST", body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not read that resume.");
    renderResponse(data);
  } catch (error) { addMessage("assistant", error.message || "Could not upload the resume.", true); }
  finally { busy = false; send.disabled = false; fileInput.value = ""; }
}

async function refreshCount() {
  try {
    const response = await fetch(`/api/bootstrap?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    $("application-count").textContent = data.applications?.length || 0;
    $("dataset-count").textContent = `${(data.job_count || 0).toLocaleString()} real jobs`;
    if (data.profile) renderRail(data.profile);
    if (!hydrated) {
      hydrated = true;
      const history = data.history || [];
      let lastAssistant = null;
      history.forEach(entry => { lastAssistant = addMessage(entry.role, entry.content); });
      if (lastAssistant && data.last_jobs?.length && /I found|I parsed/.test(history.at(-1)?.content || "")) renderJobs(lastAssistant, data.last_jobs);
    }
  } catch { $("dataset-count").textContent = "Job catalogue unavailable"; }
}

$("attach-button").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => uploadResume(fileInput.files?.[0]));
$("rail-upload").addEventListener("click", () => fileInput.click());
$("send-button").addEventListener("click", () => submitMessage());
input.addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submitMessage(); } });
input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 120)}px`; });
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => submitMessage(button.dataset.prompt)));
$("nav-applications").addEventListener("click", () => {
  $("nav-applications").classList.add("active");
  $("nav-chat").classList.remove("active");
  submitMessage("show my applied jobs");
});
$("nav-chat").addEventListener("click", () => {
  $("nav-chat").classList.add("active");
  $("nav-applications").classList.remove("active");
  input.focus();
});
refreshCount();
