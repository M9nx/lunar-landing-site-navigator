const sites = {
  shackleton: { name: "Shackleton rim", id: "PROVISIONAL REGION · LOLA SITE04", phase: 0.15, earthPhase: 1.05 },
  malapert: { name: "Malapert Massif", id: "PROVISIONAL REGION · LOLA SITE23", phase: 1.1, earthPhase: 0.35 }
};

const siteA = document.querySelector("#site-a");
const siteB = document.querySelector("#site-b");
const dateInput = document.querySelector("#date");
const timeInput = document.querySelector("#time");
const timeLabel = document.querySelector("#time-label");
const results = document.querySelector("#results");
const sunLineA = document.querySelector("#sun-line-a");
const earthLineA = document.querySelector("#earth-line-a");
const sunLineB = document.querySelector("#sun-line-b");
const earthLineB = document.querySelector("#earth-line-b");
const cursorLine = document.querySelector("#cursor-line");
const comparisonSummary = document.querySelector("#comparison-summary");
const sidebarSummary = document.querySelector("#sidebar-summary");
const chartSubtitle = document.querySelector("#chart-subtitle");
const chartSiteCaption = document.querySelector("#chart-site-caption");
const backendStatus = document.querySelector("#backend-status");
const authStatus = document.querySelector("#auth-status");
const apiSignIn = document.querySelector("#api-sign-in");
const apiSignOut = document.querySelector("#api-sign-out");
const hubLink = document.querySelector("#hub-link");
const runsList = document.querySelector("#runs-list");
const runsEmpty = document.querySelector("#runs-empty");
const runsSigninWall = document.querySelector("#runs-signin-wall");
const runsAuthed = document.querySelector("#runs-authed");
const recordStubRun = document.querySelector("#record-stub-run");
const runsSignIn = document.querySelector("#runs-sign-in");
const runToast = document.querySelector("#run-toast");

const API_TIMEOUT_MS = 10000;

let csrfToken = null;
let toastTimer = null;
let scienceReady = false;

const RUN_STATUS = {
  queued: { label: "Queued", hint: "Waiting for worker (not used in stub mode)." },
  rejected_not_ready: {
    label: "Stub saved",
    hint: "Inputs stored; science calculations are disabled on the API."
  },
  completed: { label: "Completed", hint: "Validated result attached." },
  failed: { label: "Failed", hint: "See error detail on the run." },
  running: { label: "Running", hint: "Calculation in progress." }
};

function apiBase() {
  return window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "") || "";
}

function hubBase() {
  return window.NAVIGATOR_CONFIG?.hubBaseUrl?.replace(/\/$/, "") || "";
}

function angle(phase, hour, amplitude, offset = 0) {
  return offset + amplitude * Math.sin((2 * Math.PI * hour) / 24 + phase);
}

function toY(deg) {
  const top = 30;
  const bottom = 220;
  const min = -12;
  const max = 15;
  return bottom - ((deg - min) / (max - min)) * (bottom - top);
}

function makePath(site, amplitude, offset, earth = false) {
  const phase = earth ? site.earthPhase : site.phase;
  const points = [];
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const y = toY(angle(phase, hour, amplitude, offset));
    points.push((hour === 0 ? "M" : "L") + " " + x.toFixed(1) + " " + y.toFixed(1));
  }
  return points.join(" ");
}

function visibilityText(value) {
  return value > 0 ? ["Above geometric horizon", "positive"] : ["Below geometric horizon", "negative"];
}

function formatLocalDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(d);
}

function formatRelative(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 45) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} h ago`;
  return formatLocalDateTime(iso);
}

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function statusMeta(status) {
  return RUN_STATUS[status] || { label: status || "Unknown", hint: "" };
}

function describeInputs(inputs) {
  if (!inputs || typeof inputs !== "object") return "No inputs recorded";
  const a = sites[inputs.site_a]?.name || inputs.site_a || "Site A";
  const b = sites[inputs.site_b]?.name || inputs.site_b || "Site B";
  const date = inputs.date || "—";
  const hour =
    inputs.sample_hour != null
      ? String(inputs.sample_hour).padStart(2, "0") + ":00"
      : "—";
  return `${a} vs ${b} · ${date} · ${hour}`;
}

function card(site, slot, hour, date) {
  const sun = angle(site.phase, hour, 8.2, -0.7);
  const earth = angle(site.earthPhase, hour, 6.5, -0.3);
  const [sunState, sunClass] = visibilityText(sun);
  const [earthState, earthClass] = visibilityText(earth);
  return `<article class="site-card">
    <div class="site-heading"><div><div class="site-id">${site.id}</div><h2>${site.name}</h2><span class="site-slot">Site ${slot}</span></div><span class="demo-chip">SYNTHETIC</span></div>
    <div class="metrics">
      <div class="metric"><small>Sun elevation · illustrative</small><strong>${sun.toFixed(1)}°</strong><div class="state ${sunClass}">${sunState}</div></div>
      <div class="metric"><small>Earth elevation · illustrative</small><strong>${earth.toFixed(1)}°</strong><div class="state ${earthClass}">${earthState}</div></div>
      <div class="metric"><small>Sample hour</small><strong>${String(hour).padStart(2, "0")}:00</strong><div class="state">Illustrative UTC label</div></div>
      <div class="metric"><small>Sample date</small><strong>${date}</strong><div class="state">From date picker</div></div>
    </div>
  </article>`;
}

function render() {
  const a = sites[siteA.value];
  const b = sites[siteB.value];
  const hour = Number(timeInput.value);
  const date = dateInput.value || "No date selected";
  timeLabel.textContent = String(hour).padStart(2, "0") + ":00";

  const summaryLine = `${a.name} vs ${b.name} · ${date} · ${timeLabel.textContent}`;
  comparisonSummary.textContent = summaryLine;
  if (sidebarSummary) sidebarSummary.textContent = summaryLine;
  chartSubtitle.textContent = `Solid lines: ${a.name}. Dashed: ${b.name}. Vertical marker: hour ${timeLabel.textContent}.`;
  chartSiteCaption.textContent = `Marker at ${timeLabel.textContent}`;

  results.innerHTML = card(a, "A", hour, date) + card(b, "B", hour, date);

  sunLineA.setAttribute("d", makePath(a, 8.2, -0.7, false));
  earthLineA.setAttribute("d", makePath(a, 6.5, -0.3, true));
  sunLineB.setAttribute("d", makePath(b, 8.2, -0.7, false));
  earthLineB.setAttribute("d", makePath(b, 6.5, -0.3, true));

  const x = 55 + (hour / 23) * 725;
  cursorLine.setAttribute("d", `M ${x.toFixed(1)} 25 V 220`);
}

function applyRunInputs(inputs) {
  if (!inputs) return;
  if (inputs.site_a && siteA.querySelector(`option[value="${inputs.site_a}"]`)) {
    siteA.value = inputs.site_a;
  }
  if (inputs.site_b && siteB.querySelector(`option[value="${inputs.site_b}"]`)) {
    siteB.value = inputs.site_b;
  }
  if (inputs.date) dateInput.value = inputs.date;
  if (inputs.sample_hour != null) timeInput.value = String(inputs.sample_hour);
  render();
  showToast("Loaded saved inputs into the comparison controls.");
}

function showToast(message) {
  if (!runToast) return;
  runToast.textContent = message;
  runToast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    runToast.hidden = true;
  }, 5000);
}

function renderRunItem(run) {
  const li = document.createElement("li");
  li.className = "run-card";
  const meta = statusMeta(run.status);
  const inputsLine = describeInputs(run.inputs);
  const calcVer = run.calculation_version ? `calc ${run.calculation_version}` : "";
  const prov =
    run.provenance?.note && typeof run.provenance.note === "string"
      ? run.provenance.note
      : meta.hint;

  li.innerHTML = `
    <div class="run-card-top">
      <span class="status-badge status-${run.status || "unknown"}">${meta.label}</span>
      <time class="run-time" datetime="${run.created_at}">${formatLocalDateTime(run.created_at)}</time>
    </div>
    <p class="run-inputs">${inputsLine}</p>
    <dl class="run-meta">
      <div><dt>Recorded</dt><dd>${formatRelative(run.created_at)}</dd></div>
      <div><dt>API handling</dt><dd>${formatDuration(run.duration_ms)}</dd></div>
      <div><dt>Run ID</dt><dd><code>${run.id}</code></dd></div>
      ${calcVer ? `<div><dt>Version</dt><dd>${calcVer}</dd></div>` : ""}
    </dl>
    <p class="run-hint">${prov}</p>
    <div class="run-actions">
      <button type="button" class="btn btn-ghost btn-sm run-apply">Apply to comparison</button>
    </div>
  `;

  li.querySelector(".run-apply")?.addEventListener("click", () => applyRunInputs(run.inputs));
  return li;
}

async function apiFetch(path, options = {}) {
  const baseUrl = apiBase();
  if (!baseUrl) throw new Error("API not configured");
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
      credentials: "include",
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

function setRunsAuthed(authed) {
  if (runsSigninWall) runsSigninWall.hidden = authed;
  if (runsAuthed) runsAuthed.hidden = !authed;
}

async function updateBackendStatus() {
  const baseUrl = apiBase();
  if (!baseUrl) {
    backendStatus.className = "status-chip offline";
    backendStatus.textContent = "Backend not configured · live preview still works in the browser.";
    scienceReady = false;
    return;
  }
  try {
    const response = await apiFetch("/health");
    if (!response.ok) throw new Error("Health endpoint returned an error");
    const health = await response.json();
    scienceReady = Boolean(health.science_calculations_ready);
    backendStatus.className = "status-chip online";
    backendStatus.textContent = scienceReady
      ? "API reachable · science flag on (results still need validation)."
      : "API reachable · saving stubs only; preview values are browser-generated.";
  } catch (err) {
    scienceReady = false;
    backendStatus.className = "status-chip offline";
    const timedOut = err?.name === "AbortError";
    backendStatus.textContent = timedOut
      ? "API timeout · preview still works; check api.m9nx.me or CORS."
      : "API unavailable · preview still works in the browser.";
  }
}

async function refreshAuthState() {
  const baseUrl = apiBase();
  const hub = hubBase();
  if (hub && hubLink) {
    hubLink.href = hub + "/";
    hubLink.hidden = false;
  }
  if (!baseUrl) {
    authStatus.className = "status-chip offline";
    authStatus.textContent = "API URL not configured.";
    setRunsAuthed(false);
    return;
  }
  try {
    const response = await apiFetch("/auth/me");
    if (!response.ok) throw new Error("not authed");
    const me = await response.json();
    authStatus.className = "status-chip online";
    authStatus.textContent = `Signed in as ${me.user_login}`;
    apiSignIn.hidden = true;
    apiSignOut.hidden = false;
    setRunsAuthed(true);
    const csrfResp = await apiFetch("/auth/csrf");
    const csrfData = await csrfResp.json();
    csrfToken = csrfData.csrf_token;
    await loadRuns();
  } catch (err) {
    csrfToken = null;
    authStatus.className = "status-chip offline";
    authStatus.textContent =
      err?.name === "AbortError" ? "Sign-in check timed out" : "Not signed in";
    apiSignIn.hidden = false;
    apiSignOut.hidden = true;
    setRunsAuthed(false);
  }
}

async function loadRuns() {
  runsList.innerHTML = "";
  const response = await apiFetch("/runs");
  if (!response.ok) return;
  const data = await response.json();
  const runs = data.runs || [];
  runsEmpty.hidden = runs.length > 0;
  runs.forEach((run) => runsList.appendChild(renderRunItem(run)));
}

function startApiLogin() {
  const baseUrl = apiBase();
  if (!baseUrl) return;
  const redirect = encodeURIComponent(window.location.href);
  window.location.href = `${baseUrl}/auth/github/login?redirect=${redirect}`;
}

async function apiLogout() {
  if (!csrfToken) return;
  await apiFetch("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken }
  });
  csrfToken = null;
  await refreshAuthState();
}

async function createStubRun() {
  if (!csrfToken) return;
  const hour = Number(timeInput.value);
  recordStubRun.disabled = true;
  try {
    const response = await apiFetch("/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken
      },
      body: JSON.stringify({
        inputs: {
          site_a: siteA.value,
          site_b: siteB.value,
          date: dateInput.value,
          sample_hour: hour,
          note: "stub from prototype UI"
        }
      })
    });
    if (!response.ok) {
      showToast("Could not save run — check API sign-in and try again.");
      return;
    }
    const run = await response.json();
    await loadRuns();
    const meta = statusMeta(run.status);
    showToast(
      `${meta.label} · ${describeInputs(run.inputs)} · API ${formatDuration(run.duration_ms)} · ${formatLocalDateTime(run.created_at)}`
    );
  } finally {
    recordStubRun.disabled = false;
  }
}

apiSignIn?.addEventListener("click", startApiLogin);
runsSignIn?.addEventListener("click", startApiLogin);
apiSignOut?.addEventListener("click", apiLogout);
recordStubRun?.addEventListener("click", createStubRun);

[siteA, siteB, dateInput, timeInput].forEach((control) =>
  control.addEventListener("input", render)
);
render();
updateBackendStatus();
refreshAuthState();
