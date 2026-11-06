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
const sunLine = document.querySelector("#sun-line");
const earthLine = document.querySelector("#earth-line");
const cursorLine = document.querySelector("#cursor-line");
const backendStatus = document.querySelector("#backend-status");
const authStatus = document.querySelector("#auth-status");
const apiSignIn = document.querySelector("#api-sign-in");
const apiSignOut = document.querySelector("#api-sign-out");
const hubLink = document.querySelector("#hub-link");
const runsPanel = document.querySelector("#runs-panel");
const runsList = document.querySelector("#runs-list");
const runsEmpty = document.querySelector("#runs-empty");
const recordStubRun = document.querySelector("#record-stub-run");

let csrfToken = null;

function apiBase() {
  return window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "") || "";
}

function hubBase() {
  return window.NAVIGATOR_CONFIG?.hubBaseUrl?.replace(/\/$/, "") || "";
}

function angle(phase, hour, amplitude, offset = 0) {
  return offset + amplitude * Math.sin((2 * Math.PI * hour / 24) + phase);
}
function toY(deg) {
  const top = 30, bottom = 220, min = -12, max = 15;
  return bottom - ((deg - min) / (max - min)) * (bottom - top);
}
function makePath(phase, amplitude, offset) {
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
function card(site, slot, hour, date) {
  const sun = angle(site.phase, hour, 8.2, -0.7);
  const earth = angle(site.earthPhase, hour, 6.5, -0.3);
  const [sunState, sunClass] = visibilityText(sun);
  const [earthState, earthClass] = visibilityText(earth);
  return `<article class="site-card">
    <div class="site-heading"><div><div class="site-id">${site.id}</div><h2>${site.name}</h2></div><span class="demo-chip">SYNTHETIC</span></div>
    <div class="metrics">
      <div class="metric"><small>Sun elevation · illustrative</small><strong>${sun.toFixed(1)}°</strong><div class="state ${sunClass}">${sunState}</div></div>
      <div class="metric"><small>Earth elevation · illustrative</small><strong>${earth.toFixed(1)}°</strong><div class="state ${earthClass}">${earthState}</div></div>
      <div class="metric"><small>Selected sample time</small><strong>${String(hour).padStart(2,"0")}:00</strong><div class="state">${date}</div></div>
      <div class="metric"><small>Terrain / link model</small><strong>Not included</strong><div class="state">UI demonstration only</div></div>
    </div>
  </article>`;
}
function render() {
  const a = sites[siteA.value], b = sites[siteB.value];
  const hour = Number(timeInput.value);
  const date = dateInput.value || "No date selected";
  timeLabel.textContent = String(hour).padStart(2, "0") + ":00";
  results.innerHTML = card(a, "A", hour, date) + card(b, "B", hour, date);
  sunLine.setAttribute("d", makePath(a.phase, 8.2, -0.7));
  earthLine.setAttribute("d", makePath(a.earthPhase, 6.5, -0.3));
  const x = 55 + (hour / 23) * 725;
  cursorLine.setAttribute("d", `M ${x.toFixed(1)} 25 V 220`);
}

async function apiFetch(path, options = {}) {
  const baseUrl = apiBase();
  if (!baseUrl) throw new Error("API not configured");
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  return fetch(`${baseUrl}${path}`, { ...options, headers, credentials: "include" });
}

async function updateBackendStatus() {
  const baseUrl = apiBase();
  if (!baseUrl) {
    backendStatus.className = "status-chip offline";
    backendStatus.textContent = "Backend not connected · showing synthetic demo values only.";
    return;
  }
  try {
    const response = await apiFetch("/health");
    if (!response.ok) throw new Error("Health endpoint returned an error");
    const health = await response.json();
    backendStatus.className = "status-chip online";
    backendStatus.textContent = health.science_calculations_ready
      ? "API reachable · science flag set; results still require validation."
      : "API reachable · science calculations are not ready. Values below remain synthetic.";
  } catch {
    backendStatus.className = "status-chip offline";
    backendStatus.textContent = "Backend unavailable · showing synthetic demo values only.";
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
    authStatus.textContent = "API sign-in unavailable (no apiBaseUrl).";
    runsPanel.hidden = true;
    return;
  }
  try {
    const response = await apiFetch("/auth/me");
    if (!response.ok) throw new Error("not authed");
    const me = await response.json();
    authStatus.className = "status-chip online";
    authStatus.textContent = `API signed in as ${me.user_login} · Hub login is separate.`;
    apiSignIn.hidden = true;
    apiSignOut.hidden = false;
    runsPanel.hidden = false;
    const csrfResp = await apiFetch("/auth/csrf");
    const csrfData = await csrfResp.json();
    csrfToken = csrfData.csrf_token;
    await loadRuns();
  } catch {
    csrfToken = null;
    authStatus.className = "status-chip offline";
    authStatus.textContent = "Not signed in to API · synthetic demo only.";
    apiSignIn.hidden = false;
    apiSignOut.hidden = true;
    runsPanel.hidden = true;
  }
}

async function loadRuns() {
  runsList.innerHTML = "";
  const response = await apiFetch("/runs");
  if (!response.ok) return;
  const data = await response.json();
  const runs = data.runs || [];
  runsEmpty.hidden = runs.length > 0;
  runs.forEach((run) => {
    const li = document.createElement("li");
    li.textContent = `${run.created_at} · ${run.status} · ${run.id.slice(0, 8)}…`;
    runsList.appendChild(li);
  });
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
  if (response.ok) await loadRuns();
}

apiSignIn?.addEventListener("click", startApiLogin);
apiSignOut?.addEventListener("click", apiLogout);
recordStubRun?.addEventListener("click", createStubRun);

[siteA, siteB, dateInput, timeInput].forEach(control => control.addEventListener("input", render));
render();
updateBackendStatus();
refreshAuthState();
