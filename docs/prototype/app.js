/**
 * Synthetic training demo — no validated lunar geometry or terrain.
 * State contract: see docs/ENGINE_CALCULATION_PIPELINE.md and tests/test_horizon_visibility_semantics.py
 */

const SIMULATION = {
  label:
    "SYNTHETIC local-plane model: invented elevations, azimuths, and terrain rules. Not Product 78/90/69.",
  geometricHorizonDeg: 0,
  /** Sun azimuth (deg): advances 15° per hour for illustration. */
  sunAzimuthDeg(hour) {
    return (hour * 15) % 360;
  },
  /** Earth azimuth (deg): offset from sun for illustration. */
  earthAzimuthDeg(hour) {
    return (hour * 15 + 140) % 360;
  },
  /** Per-site terrain horizon along azimuth; unknown sector → not clear. */
  terrainHorizon(siteKey, azDeg) {
    const a = ((azDeg % 360) + 360) % 360;
    if (siteKey === "malapert") {
      if (a >= 20 && a <= 40) return { elevationDeg: null, terrainKnown: false };
      if (a >= 80 && a <= 100) return { elevationDeg: 12, terrainKnown: true };
      return { elevationDeg: 0, terrainKnown: true };
    }
    return { elevationDeg: 0, terrainKnown: true };
  },
};

function classifyCentreRay(targetElDeg, horizonDeg, terrainKnown) {
  if (!terrainKnown || horizonDeg === null || Number.isNaN(horizonDeg)) {
    return { code: "unknown", label: "Unknown (terrain gap)", detail: "Terrain not known on this ray; not treated as clear." };
  }
  if (Number.isNaN(targetElDeg)) {
    return { code: "unknown", label: "Unknown", detail: "Invalid target angle." };
  }
  if (targetElDeg > horizonDeg) {
    return { code: "clear", label: "Clear", detail: "Centre ray above synthetic terrain horizon (known terrain)." };
  }
  return { code: "blocked", label: "Blocked", detail: "Centre ray at or below synthetic terrain horizon (known terrain)." };
}

const sites = {
  s04p02: {
    name: "Site04 S04-P02 (documented anchor)",
    id: "LOLA Site04 · X/Y −2652.5 / −6082.5 m (not terrain-cleared)",
    phase: 0.15,
    earthPhase: 1.05,
  },
  shackleton: {
    name: "Shackleton rim",
    id: "PROVISIONAL REGION · LOLA SITE04",
    phase: 0.15,
    earthPhase: 1.05,
  },
  malapert: {
    name: "Malapert Massif",
    id: "PROVISIONAL REGION · LOLA SITE23",
    phase: 1.1,
    earthPhase: 0.35,
  },
};

const siteA = document.querySelector("#site-a");
const siteB = document.querySelector("#site-b");
const dateInput = document.querySelector("#date");
const timeInput = document.querySelector("#time");
const timeLabel = document.querySelector("#time-label");
const results = document.querySelector("#results");
const compareStrip = document.querySelector("#compare-strip");
const sunLine = document.querySelector("#sun-line");
const earthLine = document.querySelector("#earth-line");
const geoHorizonLine = document.querySelector("#geo-horizon-line");
const terrainHorizonLineA = document.querySelector("#terrain-horizon-line-a");
const terrainHorizonLineB = document.querySelector("#terrain-horizon-line-b");
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
const gatePanel = document.querySelector("#gate-panel");

const API_TIMEOUT_MS = 10000;

let csrfToken = null;

function apiBase() {
  return window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "") || "";
}

function hubBase() {
  return window.NAVIGATOR_CONFIG?.hubBaseUrl?.replace(/\/$/, "") || "";
}

function bindAuthLinks() {
  const baseUrl = apiBase();
  const hub = hubBase();
  if (hubLink && hub) {
    hubLink.href = `${hub}/`;
    hubLink.removeAttribute("hidden");
  }
  if (apiSignIn && baseUrl) {
    apiSignIn.href = `${baseUrl}/auth/github/login?redirect=${encodeURIComponent(window.location.href)}`;
  }
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

function makePath(phase, amplitude, offset) {
  const points = [];
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const y = toY(angle(phase, hour, amplitude, offset));
    points.push((hour === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  return points.join(" ");
}

/** Horizontal line at fixed elevation (degrees). */
function makeHorizonPath(elevationDeg) {
  const y = toY(elevationDeg);
  return `M 55 ${y.toFixed(1)} H 780`;
}

/** Terrain horizon vs time: sample at Sun azimuth each hour (synthetic rule). */
function makeTerrainHorizonPath(siteKey, getPhaseAmpOff) {
  const [, amplitude, offset] = getPhaseAmpOff;
  const phase = getPhaseAmpOff[0];
  const points = [];
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const az = SIMULATION.sunAzimuthDeg(hour);
    const { elevationDeg, terrainKnown } = SIMULATION.terrainHorizon(siteKey, az);
    const yDeg =
      terrainKnown && elevationDeg !== null ? elevationDeg : SIMULATION.geometricHorizonDeg;
    const y = toY(yDeg);
    points.push((hour === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  return points.join(" ");
}

function bodyRow(label, elevationDeg, azDeg, horizonInfo, geometricHorizonDeg) {
  const geoState = classifyCentreRay(elevationDeg, geometricHorizonDeg, true);
  const terrState = classifyCentreRay(elevationDeg, horizonInfo.elevationDeg, horizonInfo.terrainKnown);
  return `
    <div class="visibility-block" role="group" aria-label="${label} centre-ray vs horizons">
      <h3 class="visibility-heading">${label}</h3>
      <p class="visibility-meta">Synthetic azimuth ${azDeg.toFixed(0)}° · elevation ${elevationDeg.toFixed(1)}° (illustrative)</p>
      <div class="visibility-grid">
        <div class="metric metric-visibility">
          <small>vs geometric horizon (${geometricHorizonDeg}°)</small>
          <strong class="status-text">${geoState.label}</strong>
          <div class="state">${geoState.detail}</div>
        </div>
        <div class="metric metric-visibility">
          <small>vs synthetic terrain horizon</small>
          <strong class="status-text">${terrState.label}</strong>
          <div class="state">${terrState.detail}</div>
        </div>
      </div>
    </div>`;
}

function card(siteKey, slot, hour, date) {
  const site = sites[siteKey];
  const sun = angle(site.phase, hour, 8.2, -0.7);
  const earth = angle(site.earthPhase, hour, 6.5, -0.3);
  const sunAz = SIMULATION.sunAzimuthDeg(hour);
  const earthAz = SIMULATION.earthAzimuthDeg(hour);
  const sunH = SIMULATION.terrainHorizon(siteKey, sunAz);
  const earthH = SIMULATION.terrainHorizon(siteKey, earthAz);
  const s04 =
    siteKey === "s04p02"
      ? `<div class="metric"><small>Research note</small><strong>Practice data</strong><div class="state">Product 90/69 diagnostics in Hub only — not validated challenge output.</div></div>`
      : "";

  return `<article class="site-card" data-site="${siteKey}">
    <div class="site-heading">
      <div><div class="site-id">${site.id}</div><h2>${site.name}</h2><p class="slot-label">Compare slot ${slot} · same UTC hour</p></div>
      <span class="demo-chip">SYNTHETIC</span>
    </div>
    <p class="sim-contract">${SIMULATION.label}</p>
    <div class="metrics metrics-visibility">
      ${bodyRow("Sun", sun, sunAz, sunH, SIMULATION.geometricHorizonDeg)}
      ${bodyRow("Earth", earth, earthAz, earthH, SIMULATION.geometricHorizonDeg)}
      <div class="metric">
        <small>Selected sample time (UTC)</small>
        <strong>${String(hour).padStart(2, "0")}:00</strong>
        <div class="state">${date}</div>
      </div>
      <div class="metric">
        <small>Not modeled here</small>
        <strong>Finite disc · power · RF</strong>
        <div class="state">Centre-ray only; not solar power or comms link (see ENGINE_CALCULATION_PIPELINE.md).</div>
      </div>
      ${s04}
    </div>
  </article>`;
}

function compareCell(siteKey, hour) {
  const site = sites[siteKey];
  const sun = angle(site.phase, hour, 8.2, -0.7);
  const earth = angle(site.earthPhase, hour, 6.5, -0.3);
  const sAz = SIMULATION.sunAzimuthDeg(hour);
  const eAz = SIMULATION.earthAzimuthDeg(hour);
  const sunH = SIMULATION.terrainHorizon(siteKey, sAz);
  const earthH = SIMULATION.terrainHorizon(siteKey, eAz);
  const sunSt = classifyCentreRay(sun, sunH.elevationDeg, sunH.terrainKnown);
  const earthSt = classifyCentreRay(earth, earthH.elevationDeg, earthH.terrainKnown);
  return `<div class="compare-cell">
    <h3 class="compare-cell-title">${site.name}</h3>
    <p><strong>Sun vs terrain:</strong> ${sunSt.label}</p>
    <p><strong>Earth vs terrain:</strong> ${earthSt.label}</p>
  </div>`;
}

function render() {
  const keyA = siteA.value;
  const keyB = siteB.value;
  const a = sites[keyA];
  const b = sites[keyB];
  const hour = Number(timeInput.value);
  const date = dateInput.value || "No date selected";
  timeLabel.textContent = `${String(hour).padStart(2, "0")}:00`;
  if (timeInput) {
    timeInput.setAttribute("aria-valuenow", String(hour));
  }

  results.innerHTML = card(keyA, "A", hour, date) + card(keyB, "B", hour, date);
  if (compareStrip) {
    compareStrip.innerHTML = `<h2 class="compare-strip-title">Same-time comparison (synthetic)</h2><div class="compare-row">${compareCell(keyA, hour)}${compareCell(keyB, hour)}</div>`;
  }

  sunLine?.setAttribute("d", makePath(a.phase, 8.2, -0.7));
  earthLine?.setAttribute("d", makePath(a.earthPhase, 6.5, -0.3));
  geoHorizonLine?.setAttribute("d", makeHorizonPath(SIMULATION.geometricHorizonDeg));
  terrainHorizonLineA?.setAttribute("d", makeTerrainHorizonPath(keyA, [a.phase, 8.2, -0.7]));
  terrainHorizonLineB?.setAttribute("d", makeTerrainHorizonPath(keyB, [b.phase, 8.2, -0.7]));

  const x = 55 + (hour / 23) * 725;
  cursorLine?.setAttribute("d", `M ${x.toFixed(1)} 25 V 220`);
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
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
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

async function updateGatePanel() {
  if (!gatePanel) return;
  const baseUrl = apiBase();
  if (!baseUrl) {
    gatePanel.textContent =
      "API URL not configured — cannot probe /health or /v1/benchmark/status. Compare remains synthetic only.";
    return;
  }
  try {
    const [hRes, bRes] = await Promise.all([apiFetch("/health"), apiFetch("/v1/benchmark/status")]);
    const health = hRes.ok ? await hRes.json() : null;
    const bench = bRes.ok ? await bRes.json() : null;
    const ready = health?.science_calculations_ready === true;
    const lines = [];
    lines.push(
      "Diagnostics (API health / DB ping) are not validated lunar geometry — charts below stay SYNTHETIC until the science gate is explicitly enabled."
    );
    lines.push(`Science gate (SCIENCE_CALCULATIONS_READY): ${ready ? "true" : "false"} — validated compare still disabled.`);
    if (bench && bench.benchmark_kind) {
      lines.push(
        `[Diagnostic] GET /v1/benchmark/status: sqlite_ping_ms=${bench.sqlite_ping_ms ?? "?"} — ` +
          (bench.interpretation || "infrastructure probe only (not ephemeris or terrain).")
      );
    } else {
      lines.push("GET /v1/benchmark/status: unavailable on this deployment (deploy API ≥ branch with benchmark route).");
    }
    lines.push(
      "[Not validated] POST /v1/compare returns 503 while the gate is false — by design; use Hub research scripts for terrain diagnostics."
    );
    gatePanel.textContent = lines.join(" ");
  } catch {
    gatePanel.textContent = "Could not reach API for gate panel — demo values remain synthetic.";
  }
}

async function refreshAuthState() {
  bindAuthLinks();
  const baseUrl = apiBase();
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
    bindAuthLinks();
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

async function apiLogout() {
  if (!csrfToken) return;
  await apiFetch("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
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
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify({
      inputs: {
        site_a: siteA.value,
        site_b: siteB.value,
        date: dateInput.value,
        sample_hour: hour,
        note: "stub from prototype UI",
      },
    }),
  });
  if (response.ok) await loadRuns();
}

bindAuthLinks();
apiSignOut?.addEventListener("click", apiLogout);
recordStubRun?.addEventListener("click", createStubRun);

[siteA, siteB, dateInput, timeInput].forEach((control) => control?.addEventListener("input", render));

render();
updateBackendStatus();
updateGatePanel();
refreshAuthState();
