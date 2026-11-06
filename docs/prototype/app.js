/**
 * Synthetic training demo — no validated lunar geometry or terrain.
 * State contract: docs/ENGINE_CALCULATION_PIPELINE.md
 * Polar sky is an invented local-plane drawing, not a DEM.
 */

const SIMULATION = {
  label:
    "SYNTHETIC local-plane model: invented elevations, azimuths, and terrain rules. Not Product 78/90/69.",
  geometricHorizonDeg: 0,
  sunAzimuthDeg(hour) {
    return (hour * 15) % 360;
  },
  earthAzimuthDeg(hour) {
    return (hour * 15 + 140) % 360;
  },
  terrainHorizon(siteKey, azDeg) {
    const a = ((azDeg % 360) + 360) % 360;
    if (siteKey === "malapert") {
      if (a >= 20 && a <= 40) return { elevationDeg: null, terrainKnown: false };
      if (a >= 70 && a <= 110) {
        const t = (a - 70) / 40;
        const bump = Math.sin(Math.PI * t);
        return { elevationDeg: 12 * bump, terrainKnown: true };
      }
      return { elevationDeg: 0, terrainKnown: true };
    }
    return { elevationDeg: 0, terrainKnown: true };
  },
};

function classifyCentreRay(targetElDeg, horizonDeg, terrainKnown) {
  if (!terrainKnown || horizonDeg === null || Number.isNaN(horizonDeg)) {
    return {
      code: "unknown",
      label: "Unknown (terrain gap)",
      short: "Unknown",
      detail: "Terrain not known on this ray; not treated as clear.",
    };
  }
  if (Number.isNaN(targetElDeg)) {
    return { code: "unknown", label: "Unknown", short: "Unknown", detail: "Invalid target angle." };
  }
  if (targetElDeg > horizonDeg) {
    return {
      code: "clear",
      label: "Clear",
      short: "Clear",
      detail: "Centre ray above synthetic terrain horizon (known terrain).",
    };
  }
  return {
    code: "blocked",
    label: "Blocked",
    short: "Blocked",
    detail: "Centre ray at or below synthetic terrain horizon (known terrain).",
  };
}

const sites = {
  s04p02: {
    name: "Site04 S04-P02",
    id: "LOLA Site04 · X/Y −2652.5 / −6082.5 m",
    phase: 0.15,
    earthPhase: 1.05,
  },
  shackleton: {
    name: "Shackleton rim",
    id: "PROVISIONAL · LOLA SITE04",
    phase: 0.15,
    earthPhase: 1.05,
  },
  malapert: {
    name: "Malapert Massif",
    id: "PROVISIONAL · LOLA SITE23",
    phase: 1.1,
    earthPhase: 0.35,
  },
};

const POLAR = { cx: 220, cy: 228, r0: 148, elScale: 5.4, rMin: 58, rMax: 210 };

const siteA = document.querySelector("#site-a");
const siteB = document.querySelector("#site-b");
const dateInput = document.querySelector("#date");
const timeInput = document.querySelector("#time");
const timeLabel = document.querySelector("#time-label");
const compareStrip = document.querySelector("#compare-strip");
const sunLine = document.querySelector("#sun-line");
const earthLine = document.querySelector("#earth-line");
const sunArea = document.querySelector("#sun-area");
const geoHorizonLine = document.querySelector("#geo-horizon-line");
const terrainHorizonLineA = document.querySelector("#terrain-horizon-line-a");
const cursorLine = document.querySelector("#cursor-line");
const sunNow = document.querySelector("#sun-now");
const earthNow = document.querySelector("#earth-now");
const playBtn = document.querySelector("#play-hours");
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
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const hasGsap = typeof window.gsap === "function";

let csrfToken = null;
let playTween = null;
let playing = false;
let markersReady = false;

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

function makeArea(phase, amplitude, offset) {
  const line = makePath(phase, amplitude, offset);
  const y0 = toY(0);
  return `${line} L 780 ${y0.toFixed(1)} L 55 ${y0.toFixed(1)} Z`;
}

function makeHorizonPath(elevationDeg) {
  const y = toY(elevationDeg);
  return `M 55 ${y.toFixed(1)} H 780`;
}

function makeTerrainHorizonPath(siteKey) {
  const points = [];
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const az = SIMULATION.sunAzimuthDeg(hour);
    const { elevationDeg, terrainKnown } = SIMULATION.terrainHorizon(siteKey, az);
    const yDeg = terrainKnown && elevationDeg !== null ? elevationDeg : SIMULATION.geometricHorizonDeg;
    points.push((hour === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${toY(yDeg).toFixed(1)}`);
  }
  return points.join(" ");
}

function polarRadius(elDeg) {
  const r = POLAR.r0 - elDeg * POLAR.elScale;
  return Math.min(POLAR.rMax, Math.max(POLAR.rMin, r));
}

function polarXY(azDeg, elDeg) {
  const r = polarRadius(elDeg);
  const rad = (azDeg * Math.PI) / 180;
  return {
    x: POLAR.cx + r * Math.sin(rad),
    y: POLAR.cy - r * Math.cos(rad),
  };
}

function skySvgMarkup(prefix) {
  const rings = [0, 8, 15].map((el) => {
    const r = polarRadius(el);
    return `<circle cx="${POLAR.cx}" cy="${POLAR.cy}" r="${r.toFixed(1)}" class="sky-ring${el === 0 ? " sky-ring-geo" : ""}"/>`;
  }).join("");
  const dirs = [
    [0, "N"],
    [90, "E"],
    [180, "S"],
    [270, "W"],
  ].map(([az, lab]) => {
    const p = polarXY(az, -11);
    return `<text class="sky-dir" x="${p.x.toFixed(1)}" y="${p.y.toFixed(1)}" text-anchor="middle" dominant-baseline="middle">${lab}</text>`;
  }).join("");
  return `
    <svg class="sky-svg" viewBox="0 0 440 470" role="img" aria-labelledby="${prefix}-title">
      <title id="${prefix}-title">Synthetic polar sky</title>
      <defs>
        <radialGradient id="${prefix}-sky" cx="50%" cy="48%" r="62%">
          <stop offset="0%" stop-color="#1c2438"/>
          <stop offset="70%" stop-color="#0c1018"/>
          <stop offset="100%" stop-color="#07080c"/>
        </radialGradient>
        <pattern id="${prefix}-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="#c45c5c" stroke-width="2" opacity="0.7"/>
        </pattern>
        <filter id="${prefix}-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="3.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <circle class="sky-disc" cx="${POLAR.cx}" cy="${POLAR.cy}" r="${POLAR.rMax}" fill="url(#${prefix}-sky)"/>
      ${rings}
      <path id="${prefix}-terrain" class="sky-terrain"/>
      <g id="${prefix}-gaps"></g>
      <circle class="sky-geo-dash" cx="${POLAR.cx}" cy="${POLAR.cy}" r="${polarRadius(0).toFixed(1)}"/>
      ${dirs}
      <g id="${prefix}-ray-sun" class="sky-ray"></g>
      <g id="${prefix}-ray-earth" class="sky-ray earth-ray"></g>
      <g id="${prefix}-sun" class="sky-marker sky-sun" filter="url(#${prefix}-glow)">
        <circle r="14" class="sky-sun-halo"/>
        <circle r="7" class="sky-sun-core"/>
      </g>
      <g id="${prefix}-earth" class="sky-marker sky-earth" filter="url(#${prefix}-glow)">
        <circle r="12" class="sky-earth-halo"/>
        <circle r="6" class="sky-earth-core"/>
      </g>
      <text class="sky-zenith" x="${POLAR.cx}" y="${POLAR.cy - 8}" text-anchor="middle">zenith</text>
      <text class="sky-caption" x="${POLAR.cx}" y="454" text-anchor="middle">Azimuth from north · elevation from geometric 0°</text>
    </svg>`;
}

function mountPlots() {
  const a = document.querySelector("#plot-a");
  const b = document.querySelector("#plot-b");
  if (a && !a.querySelector("svg")) a.innerHTML = skySvgMarkup("pa");
  if (b && !b.querySelector("svg")) b.innerHTML = skySvgMarkup("pb");
}

function terrainFillPath(siteKey) {
  const inner = [];
  const outer = [];
  for (let az = 0; az <= 360; az += 3) {
    const h = SIMULATION.terrainHorizon(siteKey, az);
    const el = h.terrainKnown && h.elevationDeg !== null ? h.elevationDeg : 0;
    inner.push(polarXY(az, el));
    outer.push(polarXY(az, -12));
  }
  let d = `M ${inner[0].x.toFixed(1)} ${inner[0].y.toFixed(1)}`;
  for (let i = 1; i < inner.length; i += 1) d += ` L ${inner[i].x.toFixed(1)} ${inner[i].y.toFixed(1)}`;
  for (let i = outer.length - 1; i >= 0; i -= 1) d += ` L ${outer[i].x.toFixed(1)} ${outer[i].y.toFixed(1)}`;
  return `${d} Z`;
}

function gapWedges(siteKey, prefix) {
  const host = document.querySelector(`#${prefix}-gaps`);
  if (!host) return;
  host.innerHTML = "";
  if (siteKey !== "malapert") return;
  const start = polarXY(20, 15);
  const mid1 = polarXY(20, -12);
  const mid2 = polarXY(40, -12);
  const end = polarXY(40, 15);
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  const rOut = polarRadius(-12);
  const rIn = polarRadius(15);
  p.setAttribute(
    "d",
    `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} L ${mid1.x.toFixed(1)} ${mid1.y.toFixed(1)} A ${rOut} ${rOut} 0 0 1 ${mid2.x.toFixed(1)} ${mid2.y.toFixed(1)} L ${end.x.toFixed(1)} ${end.y.toFixed(1)} A ${rIn} ${rIn} 0 0 0 ${start.x.toFixed(1)} ${start.y.toFixed(1)} Z`
  );
  p.setAttribute("class", "sky-gap");
  p.setAttribute("fill", `url(#${prefix}-hatch)`);
  host.appendChild(p);
}

function moveMarker(el, x, y) {
  if (!el) return;
  if (hasGsap && !reducedMotion) {
    if (!markersReady) {
      window.gsap.set(el, { x, y });
      return;
    }
    window.gsap.to(el, { x, y, duration: 0.4, ease: "power2.out", overwrite: "auto" });
  } else {
    el.setAttribute("transform", `translate(${x} ${y})`);
  }
}

function setRay(prefix, kind, az, el) {
  const g = document.querySelector(`#${prefix}-ray-${kind}`);
  if (!g) return;
  const origin = { x: POLAR.cx, y: POLAR.cy };
  const tip = polarXY(az, el);
  g.innerHTML = `<line x1="${origin.x}" y1="${origin.y}" x2="${tip.x.toFixed(1)}" y2="${tip.y.toFixed(1)}"/>`;
}

function snapshot(siteKey, hour) {
  const site = sites[siteKey];
  const sunEl = angle(site.phase, hour, 8.2, -0.7);
  const earthEl = angle(site.earthPhase, hour, 6.5, -0.3);
  const sunAz = SIMULATION.sunAzimuthDeg(hour);
  const earthAz = SIMULATION.earthAzimuthDeg(hour);
  const sunH = SIMULATION.terrainHorizon(siteKey, sunAz);
  const earthH = SIMULATION.terrainHorizon(siteKey, earthAz);
  return {
    site,
    sunEl,
    earthEl,
    sunAz,
    earthAz,
    sunH,
    earthH,
    sunSt: classifyCentreRay(sunEl, sunH.elevationDeg, sunH.terrainKnown),
    earthSt: classifyCentreRay(earthEl, earthH.elevationDeg, earthH.terrainKnown),
  };
}

function pillsHtml(snap) {
  return `
    <span class="status-pill status-${snap.sunSt.code}" title="${snap.sunSt.detail}">Sun ${snap.sunSt.short}</span>
    <span class="status-pill status-${snap.earthSt.code}" title="${snap.earthSt.detail}">Earth ${snap.earthSt.short}</span>`;
}

function updatePlot(prefix, siteKey, hour) {
  const snap = snapshot(siteKey, hour);
  const terrain = document.querySelector(`#${prefix}-terrain`);
  if (terrain) terrain.setAttribute("d", terrainFillPath(siteKey));
  gapWedges(siteKey, prefix);
  const sunPt = polarXY(snap.sunAz, snap.sunEl);
  const earthPt = polarXY(snap.earthAz, snap.earthEl);
  moveMarker(document.querySelector(`#${prefix}-sun`), sunPt.x, sunPt.y);
  moveMarker(document.querySelector(`#${prefix}-earth`), earthPt.x, earthPt.y);
  setRay(prefix, "sun", snap.sunAz, snap.sunEl);
  setRay(prefix, "earth", snap.earthAz, snap.earthEl);
  return snap;
}

function render() {
  const keyA = siteA.value;
  const keyB = siteB.value;
  const hour = Number(timeInput.value);
  const date = dateInput.value || "No date selected";
  timeLabel.textContent = `${String(hour).padStart(2, "0")}:00`;
  timeInput?.setAttribute("aria-valuenow", String(hour));

  const snapA = updatePlot("pa", keyA, hour);
  const snapB = updatePlot("pb", keyB, hour);

  document.querySelector("#name-a").textContent = snapA.site.name;
  document.querySelector("#name-b").textContent = snapB.site.name;
  document.querySelector("#pills-a").innerHTML = pillsHtml(snapA);
  document.querySelector("#pills-b").innerHTML = pillsHtml(snapB);
  document.querySelector("#readout-a").textContent =
    `${snapA.site.id} · Sun az ${snapA.sunAz.toFixed(0)}° el ${snapA.sunEl.toFixed(1)}° · Earth az ${snapA.earthAz.toFixed(0)}° el ${snapA.earthEl.toFixed(1)}° · ${date} ${String(hour).padStart(2, "0")}:00 UTC · SYNTHETIC`;
  document.querySelector("#readout-b").textContent =
    `${snapB.site.id} · Sun az ${snapB.sunAz.toFixed(0)}° el ${snapB.sunEl.toFixed(1)}° · Earth az ${snapB.earthAz.toFixed(0)}° el ${snapB.earthEl.toFixed(1)}° · centre-ray only`;

  if (compareStrip) {
    compareStrip.innerHTML = `
      <div class="hud-grid">
        <div class="hud-cell">
          <p class="hud-kicker">Site A · ${snapA.site.name}</p>
          <p><span class="status-pill status-${snapA.sunSt.code}">Sun ${snapA.sunSt.short}</span>
             <span class="status-pill status-${snapA.earthSt.code}">Earth ${snapA.earthSt.short}</span></p>
          <p class="hud-detail">${snapA.sunSt.detail}</p>
        </div>
        <div class="hud-cell">
          <p class="hud-kicker">Site B · ${snapB.site.name}</p>
          <p><span class="status-pill status-${snapB.sunSt.code}">Sun ${snapB.sunSt.short}</span>
             <span class="status-pill status-${snapB.earthSt.code}">Earth ${snapB.earthSt.short}</span></p>
          <p class="hud-detail">${snapB.earthSt.detail}</p>
        </div>
      </div>`;
  }

  const a = sites[keyA];
  sunLine?.setAttribute("d", makePath(a.phase, 8.2, -0.7));
  earthLine?.setAttribute("d", makePath(a.earthPhase, 6.5, -0.3));
  sunArea?.setAttribute("d", makeArea(a.phase, 8.2, -0.7));
  geoHorizonLine?.setAttribute("d", makeHorizonPath(SIMULATION.geometricHorizonDeg));
  terrainHorizonLineA?.setAttribute("d", makeTerrainHorizonPath(keyA));
  const x = 55 + (hour / 23) * 725;
  cursorLine?.setAttribute("d", `M ${x.toFixed(1)} 25 V 220`);
  const sunY = toY(snapA.sunEl);
  const earthY = toY(snapA.earthEl);
  if (sunNow) {
    sunNow.setAttribute("cx", x.toFixed(1));
    sunNow.setAttribute("cy", sunY.toFixed(1));
  }
  if (earthNow) {
    earthNow.setAttribute("cx", x.toFixed(1));
    earthNow.setAttribute("cy", earthY.toFixed(1));
  }
  markersReady = true;
}

function setHour(hour, { fromPlay } = {}) {
  const h = Math.max(0, Math.min(23, Math.round(hour)));
  timeInput.value = String(h);
  if (!fromPlay && playing) stopPlay();
  render();
}

function stopPlay() {
  playing = false;
  playTween?.kill?.();
  playTween = null;
  if (playBtn) {
    playBtn.setAttribute("aria-pressed", "false");
    playBtn.textContent = "Play 24 h";
  }
}

function startPlay() {
  if (reducedMotion || !hasGsap) {
    let h = Number(timeInput.value);
    playing = true;
    playBtn?.setAttribute("aria-pressed", "true");
    if (playBtn) playBtn.textContent = "Pause";
    playTween = { kill() { window.clearInterval(playTween.id); } };
    playTween.id = window.setInterval(() => {
      h = (h + 1) % 24;
      timeInput.value = String(h);
      render();
    }, 420);
    return;
  }
  playing = true;
  playBtn?.setAttribute("aria-pressed", "true");
  if (playBtn) playBtn.textContent = "Pause";
  const state = { h: Number(timeInput.value) };
  playTween = window.gsap.to(state, {
    h: 24,
    duration: Math.max(0.4, (24 - state.h) * 0.38),
    ease: "none",
    onUpdate() {
      const wrapped = state.h >= 24 ? 0 : state.h;
      timeInput.value = String(Math.floor(wrapped) % 24);
      render();
    },
    onComplete() {
      state.h = 0;
      playTween = window.gsap.to(state, {
        h: 24,
        duration: 9.2,
        ease: "none",
        repeat: -1,
        onUpdate() {
          timeInput.value = String(Math.floor(state.h) % 24);
          render();
        },
      });
    },
  });
}

function togglePlay() {
  if (playing) stopPlay();
  else startPlay();
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
      "Diagnostics (API health / DB ping) are not validated lunar geometry — the demo stays SYNTHETIC until the science gate is explicitly enabled."
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

mountPlots();
bindAuthLinks();
apiSignOut?.addEventListener("click", apiLogout);
recordStubRun?.addEventListener("click", createStubRun);
playBtn?.addEventListener("click", togglePlay);
document.querySelector("#cue-unknown")?.addEventListener("click", () => setHour(2));
document.querySelector("#cue-ridge")?.addEventListener("click", () => setHour(6));

[siteA, siteB, dateInput].forEach((control) =>
  control?.addEventListener("input", () => {
    if (playing) stopPlay();
    render();
  })
);
timeInput?.addEventListener("input", () => {
  if (playing) stopPlay();
  render();
});

document.addEventListener("keydown", (event) => {
  if (event.code !== "Space") return;
  const tag = event.target?.tagName;
  if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || event.target?.isContentEditable) return;
  event.preventDefault();
  togglePlay();
});

if (hasGsap && !reducedMotion) {
  window.gsap.from(".sky-panel", { opacity: 0, y: 18, duration: 0.55, stagger: 0.08, ease: "power2.out" });
}

render();
updateBackendStatus();
updateGatePanel();
refreshAuthState();

function scrollToHashTarget() {
  const id = (location.hash || "").replace(/^#/, "");
  if (id === "compare-demo") {
    document.getElementById("compare-demo")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  }
}
scrollToHashTarget();
window.addEventListener("hashchange", scrollToHashTarget);
