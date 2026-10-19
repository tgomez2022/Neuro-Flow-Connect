"use strict";

const stateLabels = {
  RECEIVED: "Received",
  NEEDS_INFORMATION: "Needs information",
  READY_TO_SCHEDULE: "Ready to schedule",
  SCHEDULED: "Scheduled",
  READY_FOR_STUDY: "Ready for study",
  STUDY_COMPLETE: "Study complete",
  AWAITING_INTERPRETATION: "Awaiting interpretation",
  REPORT_SIGNED: "Report signed",
  RESULTS_COMMUNICATED: "Results communicated",
  FOLLOW_UP_CONFIRMED: "Follow-up confirmed"
};

const roleActors = {
  referral_staff: "Avery — Referral Staff",
  pcp: "Dr. Smith — PCP",
  referral_clinician: "Dr. Smith — PCP",
  scheduler: "Sam — Scheduling Coordinator",
  patient: "Alex — Patient (demo action)",
  eeg_technologist: "Terry — EEG Technologist",
  neurologist: "Dr. Jones — Neurologist",
  authorized_clinician: "Dr. Jones — Authorized Clinician",
  care_coordinator: "Casey — Care Coordinator"
};

const app = {
  cases: [],
  current: null,
  dashboard: null,
  health: null,
  states: Object.keys(stateLabels),
  knowledge: null,
  busy: false
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pretty(value) {
  return String(value ?? "—").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  if (!value) return "No deadline";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit"
  }).format(date);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Server returned ${response.status}`);
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

function showToast(message, error = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3800);
}

async function loadApp(preferredId = null) {
  try {
    const [dashboardPayload, casesPayload, health] = await Promise.all([
      api("/api/dashboard"), api("/api/cases"), api("/api/health")
    ]);
    app.dashboard = dashboardPayload.dashboard;
    app.cases = casesPayload.cases;
    app.states = casesPayload.states;
    app.health = health;
    const selectedId = preferredId || app.current?.id || app.cases[0]?.id;
    if (selectedId) {
      const detail = await api(`/api/cases/${encodeURIComponent(selectedId)}`);
      app.current = detail.case;
    }
    renderAll();
  } catch (error) {
    $("#loading").textContent = `Unable to load NeuroFlow: ${error.message}`;
    showToast(error.message, true);
  }
}

function renderAll() {
  $("#loading").hidden = true;
  $("#case-workspace").hidden = !app.current;
  renderModelStatus();
  renderMetrics();
  renderCases();
  if (!app.current) return;
  renderHero();
  renderJourney();
  renderActionCenter();
  renderFacts();
  renderTasks();
  renderKnowledge();
  renderAudit();
}

function renderModelStatus() {
  if (!app.health) return;
  const status = $("#model-status");
  const granite = app.health.watsonx;
  status.textContent = granite.mode === "granite" ? "IBM Granite connected" : "IBM-ready • local fallback";
  status.className = `badge ${granite.mode === "granite" ? "badge-success" : "badge-neutral"}`;
}

function renderMetrics() {
  const d = app.dashboard;
  if (!d) return;
  const items = [
    [d.active_cases, "Active cases"],
    [d.pending_human_reviews, "Human reviews"],
    [`${d.visible_ownership_pct}%`, "Visible ownership"],
    [d.closed_loops, "Closed loops"]
  ];
  $("#metrics").innerHTML = items.map(([value, label]) => `
    <div class="metric-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>
  `).join("");
}

function renderCases() {
  $("#case-count").textContent = app.cases.length;
  $("#case-list").innerHTML = app.cases.map((caseItem) => `
    <button class="case-card ${caseItem.id === app.current?.id ? "active" : ""}"
      type="button" role="listitem" data-case-id="${escapeHtml(caseItem.id)}"
      aria-current="${caseItem.id === app.current?.id ? "true" : "false"}">
      <div class="case-card-top">
        <span class="case-card-id">${escapeHtml(caseItem.id)}</span>
        <span class="badge ${caseItem.workflow_status === "COMPLETE" ? "badge-success" : "badge-neutral"}">${escapeHtml(caseItem.workflow_status)}</span>
      </div>
      <div class="case-card-name">${escapeHtml(caseItem.patient_alias)}</div>
      <div class="case-card-state">${escapeHtml(stateLabels[caseItem.state] || pretty(caseItem.state))}</div>
      <div class="mini-progress" aria-hidden="true"><span style="width:${caseItem.progress_pct}%"></span></div>
    </button>
  `).join("");
  $$(".case-card").forEach((button) => button.addEventListener("click", () => selectCase(button.dataset.caseId)));
}

async function selectCase(caseId) {
  try {
    const payload = await api(`/api/cases/${encodeURIComponent(caseId)}`);
    app.current = payload.case;
    app.knowledge = null;
    renderAll();
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderHero() {
  const c = app.current;
  $("#case-id").textContent = c.id;
  $("#case-priority").textContent = c.priority;
  $("#case-status").textContent = stateLabels[c.state] || pretty(c.state);
  $("#patient-alias").textContent = c.patient_alias;
  $("#case-summary").textContent = c.fields.referral_reason || "Synthetic routine EEG coordination case.";
  $("#progress-value").textContent = `${c.progress_pct}%`;
  $(".completion-ring").style.setProperty("--progress", `${c.progress_pct * 3.6}deg`);
  $("#current-owner").textContent = c.owner;
  $("#next-action").textContent = c.next_action;
  $("#active-agent").textContent = c.active_agent;
  $("#due-at").textContent = formatDate(c.due_at);
}

function renderJourney() {
  const currentIndex = app.current.state_index;
  $("#journey-state").textContent = app.current.state;
  $("#journey-track").innerHTML = app.states.map((state, index) => {
    const phase = index < currentIndex ? "done" : index === currentIndex ? "current" : "future";
    const marker = index < currentIndex ? "✓" : String(index + 1);
    return `
      <div class="journey-step ${phase}" title="${escapeHtml(stateLabels[state] || state)}">
        <div class="journey-dot">${marker}</div>
        <div class="journey-name">${escapeHtml(stateLabels[state] || pretty(state))}</div>
      </div>`;
  }).join("");
}

function renderActionCenter() {
  const actions = app.current.available_actions || [];
  const gate = $("#gate-chip");
  if (!actions.length) {
    gate.textContent = app.current.workflow_status === "COMPLETE" ? "Loop closed" : "Human review required";
    gate.className = `badge ${app.current.workflow_status === "COMPLETE" ? "badge-success" : "badge-warning"}`;
    $("#action-content").innerHTML = app.current.workflow_status === "COMPLETE"
      ? `<div class="empty-box"><strong>Verified closure</strong><br>Delivery, acknowledgment, follow-up owner, and timing are recorded.</div>`
      : `<div class="empty-box"><strong>Automation paused safely</strong><br>${escapeHtml(app.current.next_action)}</div>`;
    return;
  }

  const action = actions[0];
  const role = action.roles[0];
  const actor = roleActors[role] || pretty(role);
  gate.textContent = action.human_gate ? "Human gate" : "Bounded automation";
  gate.className = `badge ${action.human_gate ? "badge-human" : "badge-neutral"}`;
  const fallbackButton = action.id === "schedule_case" ? `
    <button class="button button-danger" id="failure-button" type="button">Inject tool failure</button>` : "";
  $("#action-content").innerHTML = `
    <div class="action-card">
      <h3>${escapeHtml(action.label)}</h3>
      <p>${escapeHtml(app.current.next_action)}</p>
      <div class="action-meta">
        <div class="meta-box"><span>Acting role</span><strong>${escapeHtml(pretty(role))}</strong></div>
        <div class="meta-box"><span>Recorded actor</span><strong>${escapeHtml(actor)}</strong></div>
      </div>
      <div class="action-buttons">
        <button class="button button-primary" id="primary-action" type="button" ${app.busy ? "disabled" : ""}>
          ${action.human_gate ? "Review and approve" : "Run next safe step"}
        </button>
        ${fallbackButton}
      </div>
    </div>`;
  $("#primary-action").addEventListener("click", () => performAction(action, role, actor, {}));
  const failureButton = $("#failure-button");
  if (failureButton) failureButton.addEventListener("click", () => performAction(action, role, actor, { failure_mode: "scheduling_api" }));
}

async function performAction(action, role, actor, payload) {
  if (app.busy) return;
  app.busy = true;
  renderActionCenter();
  try {
    const result = await api(`/api/cases/${encodeURIComponent(app.current.id)}/action`, {
      method: "POST",
      body: JSON.stringify({ action: action.id, role, actor, payload })
    });
    app.current = result.case;
    showToast(result.message);
    await loadApp(app.current.id);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    app.busy = false;
    renderActionCenter();
  }
}

function renderFacts() {
  const f = app.current.fields;
  const facts = [
    ["Order", f.order_type],
    ["Ordering clinician", f.ordering_clinician],
    ["Neurologist", f.neurologist],
    ["Facility", f.facility],
    ["Contact", f.preferred_contact],
    ["Appointment", f.appointment_slot || "Not scheduled"],
    ["Preparation", f.preparation_acknowledged ? "Acknowledged" : "Pending"],
    ["Report", f.report_status || "Not signed"],
    ["Delivery", f.delivery_status || "Not released"],
    ["Follow-up owner", f.followup_owner || "Not assigned"]
  ];
  $("#case-facts-list").innerHTML = facts.map(([label, value]) => `
    <div class="fact"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? "—")}</dd></div>
  `).join("");
}

function renderTasks() {
  const tasks = app.current.tasks || [];
  const open = tasks.filter((task) => task.status === "OPEN");
  $("#open-task-count").textContent = open.length;
  if (!tasks.length) {
    $("#task-list").innerHTML = `<div class="empty-box">No work items yet. The supervisor creates owned tasks when a gate or exception appears.</div>`;
    return;
  }
  $("#task-list").innerHTML = tasks.map((task) => `
    <article class="task-item ${task.status === "RESOLVED" ? "resolved" : ""}">
      <div class="task-icon" aria-hidden="true">${task.status === "RESOLVED" ? "✓" : "!"}</div>
      <div>
        <h3>${escapeHtml(task.title)}</h3>
        <p>${escapeHtml(pretty(task.owner_role))} • ${escapeHtml(task.details)}</p>
      </div>
      <span class="badge ${task.status === "RESOLVED" ? "badge-success" : task.approval_type ? "badge-human" : "badge-warning"}">
        ${escapeHtml(task.status)}
      </span>
    </article>
  `).join("");
}

function renderKnowledge() {
  const container = $("#knowledge-result");
  if (!app.knowledge) {
    container.className = "knowledge-result empty-result";
    container.textContent = "Ask a question to see citations, evidence status, and safe abstention.";
    return;
  }
  const r = app.knowledge;
  const badgeClass = r.status === "ANSWERED" ? "badge-success" : r.status === "REFUSED" ? "badge-danger" : "badge-warning";
  const citations = (r.citations || []).map((citation) => `
    <li><strong>${escapeHtml(citation.source_id)} v${escapeHtml(citation.version)}</strong> — ${escapeHtml(citation.title)}<br>${escapeHtml(citation.excerpt)}</li>
  `).join("");
  container.className = "knowledge-result";
  container.innerHTML = `
    <div class="result-status">
      <span class="badge ${badgeClass}">${escapeHtml(r.status)}</span>
      <span class="badge badge-neutral">${escapeHtml(r.model_mode)}</span>
    </div>
    <p><strong>${escapeHtml(r.evidence_status)}</strong></p>
    <p>${escapeHtml(r.answer)}</p>
    ${r.notice ? `<p class="muted">${escapeHtml(r.notice)}</p>` : ""}
    ${citations ? `<ul class="citation-list">${citations}</ul>` : ""}
  `;
}

async function askKnowledge(question) {
  try {
    const payload = await api(`/api/cases/${encodeURIComponent(app.current.id)}/ask`, {
      method: "POST",
      body: JSON.stringify({ question, actor: "Demo operator", role: "scheduler" })
    });
    app.knowledge = payload.result;
    app.current = payload.case;
    renderAll();
    showToast(payload.result.status === "ANSWERED" ? "Grounded answer returned with evidence." : "Safe boundary triggered; human review created.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderAudit() {
  const events = app.current.audit || [];
  $("#audit-count").textContent = events.length;
  if (!events.length) {
    $("#audit-list").innerHTML = `<div class="empty-box">No audit evidence yet.</div>`;
    return;
  }
  $("#audit-list").innerHTML = events.map((event) => {
    const badgeClass = ["SUCCESS"].includes(event.outcome) ? "badge-success"
      : ["BLOCKED", "FALLBACK", "ABSTAIN", "ABSTAINED"].includes(event.outcome) ? "badge-warning"
      : ["REFUSED", "ESCALATED"].includes(event.outcome) ? "badge-danger" : "badge-neutral";
    return `
      <article class="audit-item">
        <time class="audit-time">${escapeHtml(formatDate(event.timestamp))}</time>
        <div class="audit-marker" aria-hidden="true"></div>
        <div class="audit-detail">
          <strong>${escapeHtml(pretty(event.action))}</strong>
          <p>${escapeHtml(event.agent)} • ${escapeHtml(event.actor)} (${escapeHtml(pretty(event.role))})</p>
          <p>${escapeHtml(event.reason || "No reason supplied")}</p>
          <span class="state-change">${escapeHtml(event.state_before)} → ${escapeHtml(event.state_after)}</span>
        </div>
        <span class="badge ${badgeClass} audit-outcome">${escapeHtml(event.outcome)}</span>
      </article>`;
  }).join("");
}

$("#knowledge-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("#knowledge-question").value.trim();
  if (question) askKnowledge(question);
});

$$(".example-question").forEach((button) => button.addEventListener("click", () => {
  $("#knowledge-question").value = button.dataset.question;
  askKnowledge(button.dataset.question);
}));

$("#reset-button").addEventListener("click", async () => {
  if (!window.confirm("Reset all synthetic cases, tasks, and audit events to the original demo state?")) return;
  try {
    await api("/api/reset", { method: "POST", body: "{}" });
    app.current = null;
    app.knowledge = null;
    showToast("Synthetic demo reset.");
    await loadApp("NF-001");
  } catch (error) {
    showToast(error.message, true);
  }
});

loadApp();

