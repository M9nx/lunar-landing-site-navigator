/**
 * Stream simulation lab UI — SIMULATION / PRACTICE only.
 * Consumes SSE from GET /v1/simulation/stream/session/{id}/events
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const defaultApi =
  (typeof window !== "undefined" && window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "")) || "http://127.0.0.1:8000";

const els = {
  apiBase: document.querySelector("#stream-api-base"),
  connect: document.querySelector("#stream-connect"),
  play: document.querySelector("#stream-play"),
  pause: document.querySelector("#stream-pause"),
  step: document.querySelector("#stream-step"),
  stop: document.querySelector("#stream-stop"),
  speed: document.querySelector("#stream-speed"),
  speedLabel: document.querySelector("#stream-speed-label"),
  scrub: document.querySelector("#stream-scrub"),
  indexLabel: document.querySelector("#stream-index-label"),
  connState: document.querySelector("#stream-conn-state"),
  apiStatus: document.querySelector("#api-stream-status"),
  liveRegion: document.querySelector("#stream-live-region"),
  invalidCount: document.querySelector("#stream-invalid-count"),
  lastUtc: document.querySelector("#stream-last-utc"),
  sampleAge: document.querySelector("#stream-sample-age"),
  nameA: document.querySelector("#card-name-a"),
  nameB: document.querySelector("#card-name-b"),
  metaA: document.querySelector("#card-meta-a"),
  metaB: document.querySelector("#card-meta-b"),
  skyA: document.querySelector("#stream-sky-a"),
  skyB: document.querySelector("#stream-sky-b"),
  tbody: document.querySelector("#stream-summary-body"),
  tlSvg: document.querySelector("#stream-timeline-svg"),
  miniGlobe: document.querySelector("#stream-mini-globe"),
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const POLAR = { cx: 110, cy: 115, r0: 78, elScale: 3.2, rMin: 32, rMax: 100 };

/** Practice site pins (same order of magnitude as training prototype). */
const SITE_GEO = {
  s04p02: { lat: -89.78, lon: -156.44 },
  malapert: { lat: -86.0, lon: 2.7 },
};

let sessionId = null;
let eventSource = null;
let totalSamples = 0;
let invalidTotal = 0;
let latestBySite = {};
let timelinePoints = [];
let globe = { ready: false };

function apiUrl(path) {
  const base = (els.apiBase?.value || defaultApi).replace(/\/$/, "");
  return `${base}${path}`;
}

function announce(msg) {
  if (els.liveRegion) els.liveRegion.textContent = msg;
}

function polarRadius(elDeg) {
  const r = POLAR.r0 - elDeg * POLAR.elScale;
  return Math.min(POLAR.rMax, Math.max(POLAR.rMin, r));
}

function polarXY(azDeg, elDeg) {
  const r = polarRadius(elDeg);
  const rad = (azDeg * Math.PI) / 180;
  return { x: POLAR.cx + r * Math.sin(rad), y: POLAR.cy - r * Math.cos(rad) };
}

function miniSkySvg(siteKey, id) {
  return `
<svg class="stream-mini-svg" viewBox="0 0 220 240" width="100%" height="auto" aria-hidden="true">
  <defs>
    <radialGradient id="${id}-sky" cx="50%" cy="48%" r="62%">
      <stop offset="0%" stop-color="#1c2438"/>
      <stop offset="100%" stop-color="#07080c"/>
    </radialGradient>
  </defs>
  <circle cx="${POLAR.cx}" cy="${POLAR.cy}" r="${POLAR.rMax}" fill="url(#${id}-sky)"/>
  <circle cx="${POLAR.cx}" cy="${POLAR.cy}" r="${polarRadius(0)}" fill="none" stroke="#8d8d92" stroke-dasharray="5 5"/>
  <path id="${id}-terrain" class="stream-mini-terrain" />
  <circle cx="${POLAR.cx}" cy="${POLAR.cy}" r="3" fill="#cfd3da" />
  <text x="${POLAR.cx}" y="${POLAR.cy - 8}" text-anchor="middle" class="stream-mini-zenith">zenith</text>
  <line id="${id}-ray-sun" class="stream-mini-ray stream-mini-ray-sun" />
  <line id="${id}-ray-earth" class="stream-mini-ray stream-mini-ray-earth" />
  <circle id="${id}-sun" r="7" class="stream-mini-sun" />
  <circle id="${id}-earth" r="6" class="stream-mini-earth" />
</svg>`;
}

function terrainPath(siteKey) {
  const inner = [];
  const outer = [];
  for (let az = 0; az <= 360; az += 6) {
    let el = 0;
    let known = true;
    const a = az % 360;
    if (siteKey === "malapert") {
      if (a >= 20 && a <= 40) {
        known = false;
        el = 0;
      } else if (a >= 70 && a <= 110) {
        const t = (a - 70) / 40;
        el = 12 * Math.sin(Math.PI * t);
      }
    }
    inner.push(polarXY(az, known ? el : 0));
    outer.push(polarXY(az, -12));
  }
  let d = `M ${inner[0].x} ${inner[0].y}`;
  for (let i = 1; i < inner.length; i++) d += ` L ${inner[i].x} ${inner[i].y}`;
  for (let i = outer.length - 1; i >= 0; i--) d += ` L ${outer[i].x} ${outer[i].y}`;
  return `${d} Z`;
}

function paintMiniSky(prefix, siteKey, sample) {
  const host = prefix === "a" ? els.skyA : els.skyB;
  if (!host.querySelector("svg")) {
    host.innerHTML = miniSkySvg(siteKey, `ms${prefix}`);
  }
  const terr = host.querySelector(`#ms${prefix}-terrain`);
  if (terr) terr.setAttribute("d", terrainPath(siteKey));
  if (!sample) return;
  const sun = host.querySelector(`#ms${prefix}-sun`);
  const earth = host.querySelector(`#ms${prefix}-earth`);
  const rs = host.querySelector(`#ms${prefix}-ray-sun`);
  const re = host.querySelector(`#ms${prefix}-ray-earth`);
  const ps = polarXY(sample.sun_az_deg, sample.sun_el_deg);
  const pe = polarXY(sample.earth_az_deg, sample.earth_el_deg);
  sun.setAttribute("cx", ps.x);
  sun.setAttribute("cy", ps.y);
  earth.setAttribute("cx", pe.x);
  earth.setAttribute("cy", pe.y);
  rs.setAttribute("x1", POLAR.cx);
  rs.setAttribute("y1", POLAR.cy);
  rs.setAttribute("x2", ps.x);
  rs.setAttribute("y2", ps.y);
  re.setAttribute("x1", POLAR.cx);
  re.setAttribute("y1", POLAR.cy);
  re.setAttribute("x2", pe.x);
  re.setAttribute("y2", pe.y);
}

function stateGlyph(code) {
  if (code === "clear") return "✓ clear";
  if (code === "blocked") return "✕ blocked";
  return "? unknown";
}

function renderTable() {
  const rows = Object.values(latestBySite);
  if (!rows.length) {
    els.tbody.innerHTML = '<tr><td colspan="7" class="stream-empty">No samples yet.</td></tr>';
    return;
  }
  els.tbody.innerHTML = rows
    .map((r) => {
      const sm = r.sun_margin_deg != null ? r.sun_margin_deg.toFixed(1) : "n/a";
      const em = r.earth_margin_deg != null ? r.earth_margin_deg.toFixed(1) : "n/a";
      return `<tr>
        <td>${escapeHtml(r.site_label || r.site_id)}</td>
        <td><span class="stream-state">${stateGlyph(r.sun_state)}</span></td>
        <td><span class="stream-state">${stateGlyph(r.earth_state)}</span></td>
        <td class="stream-mono">${escapeHtml(sm)}</td>
        <td class="stream-mono">${escapeHtml(em)}</td>
        <td class="stream-mono">${escapeHtml(r.utc || "")}</td>
        <td>${escapeHtml(r.data_validity || "accepted")}</td>
      </tr>`;
    })
    .join("");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function updateTimeline(seqIndex) {
  const svg = els.tlSvg;
  if (!svg || totalSamples < 1) return;
  const frac = Math.min(1, Math.max(0, seqIndex / Math.max(1, totalSamples - 1)));
  const x = 40 + frac * 720;
  const ph = svg.querySelector("#stream-tl-playhead");
  if (ph) {
    ph.setAttribute("x1", x);
    ph.setAttribute("x2", x);
  }
}

async function apiPost(path, body) {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

async function createSession() {
  const data = await apiPost("/v1/simulation/stream/session", { scenario_id: "s04_malapert_hourly_practice_v1" });
  sessionId = data.session_id;
  totalSamples = data.scenario?.sample_count || 0;
  els.scrub.max = String(Math.max(0, totalSamples - 1));
  els.scrub.value = "0";
  els.indexLabel.textContent = `0 / ${totalSamples}`;
  els.nameA.textContent = data.scenario.site_labels[data.scenario.site_a] || data.scenario.site_a;
  els.nameB.textContent = data.scenario.site_labels[data.scenario.site_b] || data.scenario.site_b;
  els.metaA.textContent = `Terrain: synthetic toy · ${data.scenario.terrain_source}`;
  els.metaB.textContent = `Terrain: synthetic toy · ${data.scenario.terrain_source}`;
  paintMiniSky("a", data.scenario.site_a, null);
  paintMiniSky("b", data.scenario.site_b, null);
  initMiniGlobe(data.scenario.site_a, data.scenario.site_b);
  els.play.disabled = false;
  els.pause.disabled = false;
  els.step.disabled = false;
  els.stop.disabled = false;
  els.speed.disabled = false;
  els.scrub.disabled = false;
  announce("Session created — open SSE and press Play");
  connectEvents();
}

function connectEvents() {
  if (!sessionId) return;
  if (eventSource) eventSource.close();
  const url = `${apiUrl(`/v1/simulation/stream/session/${sessionId}/events`)}`;
  eventSource = new EventSource(url, { withCredentials: false });
  els.connState.textContent = "connecting";
  els.connState.dataset.state = "connecting";
  eventSource.onopen = () => {
    els.connState.textContent = "connected";
    els.connState.dataset.state = "connected";
    els.apiStatus.textContent = "SSE open";
  };
  eventSource.onerror = () => {
    els.connState.textContent = "error";
    els.connState.dataset.state = "error";
    els.apiStatus.textContent = "SSE error — check API base and CORS";
  };
  eventSource.onmessage = (ev) => {
    let payload;
    try {
      payload = JSON.parse(ev.data);
    } catch {
      return;
    }
    handleEvent(payload);
  };
}

function handleEvent(payload) {
  if (payload.kind === "stream_health") {
    if (payload.invalid_observation_count != null) {
      invalidTotal = payload.invalid_observation_count;
    }
    els.invalidCount.textContent = String(invalidTotal);
    if (payload.session) {
      const idx = payload.session.index ?? 0;
      els.scrub.value = String(idx);
      els.indexLabel.textContent = `${idx} / ${totalSamples}`;
      updateTimeline(idx);
    }
  }
  if (payload.kind === "invalid_observation") {
    invalidTotal += 1;
    els.invalidCount.textContent = String(invalidTotal);
  }
  if (payload.kind === "visibility_sample") {
    const label =
      payload.site_id === "s04p02" ? els.nameA?.textContent : payload.site_id === "malapert" ? els.nameB?.textContent : payload.site_id;
    latestBySite[payload.site_id] = { ...payload, site_label: label };
    els.lastUtc.textContent = payload.utc;
    els.sampleAge.textContent = "live stream";
    renderTable();
    paintMiniSky(payload.site_id === "s04p02" ? "a" : "b", payload.site_id, payload);
    timelinePoints.push({ seq: payload.sequence_id, sun: payload.sun_state });
    const idx = payload.sequence_id + 1;
    els.scrub.value = String(Math.min(totalSamples, idx));
    els.indexLabel.textContent = `${Math.min(totalSamples, idx)} / ${totalSamples}`;
    updateTimeline(idx);
    announce(`Sample ${payload.sequence_id} ${payload.site_id} Sun ${payload.sun_state}`);
  }
  if (payload.invalid_observation_count != null) {
    invalidTotal = payload.invalid_observation_count;
    els.invalidCount.textContent = String(invalidTotal);
  }
}

async function control(action, extra = {}) {
  if (!sessionId) return;
  await apiPost(`/v1/simulation/stream/session/${sessionId}/control`, { action, ...extra });
}

function initMiniGlobe(siteA, siteB) {
  const host = els.miniGlobe;
  if (!host || globe.ready) return;
  try {
    const w = host.clientWidth || 220;
    const h = 140;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, w / h, 0.1, 20);
    camera.position.set(0, -2.2, 1.6);
    camera.lookAt(0, -0.2, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    host.appendChild(renderer.domElement);
    const moon = new THREE.Mesh(
      new THREE.SphereGeometry(1, 48, 48),
      new THREE.MeshStandardMaterial({ color: 0xb7aea3, roughness: 0.95 })
    );
    scene.add(moon);
    const amb = new THREE.AmbientLight(0x8899aa, 0.5);
    const sun = new THREE.DirectionalLight(0xffe6b0, 1.1);
    sun.position.set(2, 0.5, 2);
    scene.add(amb, sun);
    const pin = (color) =>
      new THREE.Mesh(new THREE.SphereGeometry(0.04, 10, 10), new THREE.MeshBasicMaterial({ color }));
    const pA = pin(0xe3b34a);
    const pB = pin(0x5ba8d8);
    const v = (lat, lon, rad) => {
      const phi = ((90 - lat) * Math.PI) / 180;
      const th = ((lon + 180) * Math.PI) / 180;
      return new THREE.Vector3(-rad * Math.sin(phi) * Math.cos(th), rad * Math.cos(phi), rad * Math.sin(phi) * Math.sin(th));
    };
    const ga = SITE_GEO[siteA] || { lat: -89, lon: 0 };
    const gb = SITE_GEO[siteB] || { lat: -89, lon: 30 };
    pA.position.copy(v(ga.lat, ga.lon, 1.02));
    pB.position.copy(v(gb.lat, gb.lon, 1.02));
    moon.add(pA, pB);
    const ctrl = new OrbitControls(camera, renderer.domElement);
    ctrl.enableDamping = true;
    ctrl.target.set(0, -0.15, 0);
    globe.ready = true;
    function tick() {
      ctrl.update();
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    }
    tick();
  } catch {
    host.textContent = "";
  }
}

els.apiBase.value = defaultApi;

els.connect?.addEventListener("click", () => {
  createSession().catch((e) => {
    els.apiStatus.textContent = `API error: ${e.message}`;
    announce(`Error ${e.message}`);
  });
});

els.play?.addEventListener("click", () => control("play"));
els.pause?.addEventListener("click", () => control("pause"));
els.step?.addEventListener("click", () => control("step"));
els.stop?.addEventListener("click", () => {
  control("stop");
  latestBySite = {};
  renderTable();
});

els.speed?.addEventListener("input", () => {
  const v = Number(els.speed.value);
  if (els.speedLabel) els.speedLabel.textContent = `${v}×`;
  if (sessionId) control("set_speed", { speed: v });
});

els.scrub?.addEventListener("change", () => {
  const idx = Number(els.scrub.value);
  control("seek", { index: idx }).catch(() => {});
  updateTimeline(idx);
});

if (!reducedMotion && typeof gsap !== "undefined") {
  gsap.from(".stream-lab-hero", { opacity: 0, y: 12, duration: 0.45, ease: "power2.out" });
}
