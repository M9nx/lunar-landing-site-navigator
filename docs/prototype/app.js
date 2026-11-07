/**
 * Synthetic training demo — no validated lunar geometry or terrain.
 * State contract: docs/ENGINE_CALCULATION_PIPELINE.md
 * Polar sky is an invented local-plane drawing, not a DEM.
 * Three.js / OrbitControls: visuals only; ephemeris lives in ephemeris.js (synthetic).
 * Polar terrain fill uses a moon albedo image as display-only texture (not geometry).
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { SIMULATION, sites, syntheticBodyAngles } from "./ephemeris.js";

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

const POLAR = { cx: 220, cy: 228, r0: 148, elScale: 5.4, rMin: 58, rMax: 210 };

/** Display-only moon surface image (aligned with Three.js globe texture). Not validated DEM geometry. */
const LUNAR_ALBEDO_URL = "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/textures/planets/moon_1024.jpg";

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

function toY(deg) {
  const top = 30;
  const bottom = 220;
  const min = -12;
  const max = 15;
  return bottom - ((deg - min) / (max - min)) * (bottom - top);
}

function makeSunPath(siteKey) {
  const points = [];
  const dateStr = dateInput?.value || "";
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const { sunEl } = syntheticBodyAngles(siteKey, hour, dateStr);
    points.push((hour === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${toY(sunEl).toFixed(1)}`);
  }
  return points.join(" ");
}

function makeEarthPath(siteKey) {
  const points = [];
  const dateStr = dateInput?.value || "";
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const { earthEl } = syntheticBodyAngles(siteKey, hour, dateStr);
    points.push((hour === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${toY(earthEl).toFixed(1)}`);
  }
  return points.join(" ");
}

function makeSunArea(siteKey) {
  const line = makeSunPath(siteKey);
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

/** Inverse of polarXY for SVG coords (synthetic polar map). Not validated lunar geometry. */
function polarFromXY(x, y) {
  const dx = x - POLAR.cx;
  const dy = y - POLAR.cy;
  const dist = Math.hypot(dx, dy);
  if (dist < 0.5) {
    return { azDeg: 0, elDeg: 15 };
  }
  const r = Math.min(POLAR.rMax, Math.max(POLAR.rMin, dist));
  let elDeg = (POLAR.r0 - r) / POLAR.elScale;
  elDeg = Math.min(15, Math.max(-12, elDeg));
  let azDeg = (Math.atan2(dx, -dy) * 180) / Math.PI;
  if (azDeg < 0) azDeg += 360;
  return { azDeg, elDeg };
}

/**
 * Optional drag offsets per polar plot (SYNTHETIC exploration). Cleared when site/date/hour changes.
 * lander: { x, y } SVG coords for ray origin (default = zenith at POLAR.cx / POLAR.cy).
 */
const plotDrag = {
  sessionKey: "",
  pa: { sun: null, earth: null, lander: null },
  pb: { sun: null, earth: null, lander: null },
};

function plotDragSessionKey() {
  return `pa:${siteA.value}|pb:${siteB.value}|${dateInput?.value || ""}|${timeInput?.value ?? ""}`;
}

function syncPlotDragSession() {
  const k = plotDragSessionKey();
  if (plotDrag.sessionKey !== k) {
    plotDrag.sessionKey = k;
    plotDrag.pa = { sun: null, earth: null, lander: null };
    plotDrag.pb = { sun: null, earth: null, lander: null };
  }
}

function rayOrigin(prefix) {
  const L = plotDrag[prefix]?.lander;
  if (L && Number.isFinite(L.x) && Number.isFinite(L.y)) {
    return { x: L.x, y: L.y };
  }
  return { x: POLAR.cx, y: POLAR.cy };
}

let polarDragActive = null;

function clientToSvgPoint(svg, clientX, clientY) {
  if (!svg?.createSVGPoint) return null;
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  return pt.matrixTransform(ctm.inverse());
}

function bindPolarInteractions() {
  document.querySelectorAll(".sky-svg").forEach((svg) => {
    const prefix = svg.closest("#plot-a, #plot-b")?.id === "plot-a" ? "pa" : "pb";
    if (!svg.dataset.dragBound) {
      svg.dataset.dragBound = "1";
      svg.addEventListener("pointerdown", (e) => {
        const t = e.target;
        const sunG = t.closest?.(".sky-sun");
        const earthG = t.closest?.(".sky-earth");
        const landerG = t.closest?.(".sky-observer");
        const kind = sunG ? "sun" : earthG ? "earth" : landerG ? "lander" : null;
        if (!kind) return;
        e.preventDefault();
        e.stopPropagation();
        const pt = clientToSvgPoint(svg, e.clientX, e.clientY);
        if (!pt) return;
        polarDragActive = { svg, prefix, kind, pointerId: e.pointerId };
        svg.setPointerCapture(e.pointerId);
        if (kind === "lander") {
          plotDrag[prefix].lander = { x: pt.x, y: pt.y };
        } else {
          const { azDeg, elDeg } = polarFromXY(pt.x, pt.y);
          plotDrag[prefix][kind] = { az: azDeg, el: elDeg };
        }
        render();
      });
      svg.addEventListener("pointermove", (e) => {
        if (!polarDragActive || polarDragActive.svg !== svg || polarDragActive.pointerId !== e.pointerId) return;
        const pt = clientToSvgPoint(svg, e.clientX, e.clientY);
        if (!pt) return;
        const { prefix, kind } = polarDragActive;
        if (kind === "lander") {
          plotDrag[prefix].lander = { x: pt.x, y: pt.y };
        } else {
          const { azDeg, elDeg } = polarFromXY(pt.x, pt.y);
          plotDrag[prefix][kind] = { az: azDeg, el: elDeg };
        }
        render();
      });
      const endDrag = (e) => {
        if (!polarDragActive || polarDragActive.svg !== svg || polarDragActive.pointerId !== e.pointerId) return;
        try {
          svg.releasePointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
        polarDragActive = null;
      };
      svg.addEventListener("pointerup", (e) => {
        endDrag(e);
        render();
      });
      svg.addEventListener("pointercancel", endDrag);
      svg.addEventListener("dblclick", (e) => {
        if (e.target.closest(".sky-sun, .sky-earth, .sky-observer")) return;
        plotDrag[prefix] = { sun: null, earth: null, lander: null };
        render();
      });
    }
  });
}

function sunGlyph() {
  const rays = [0, 45, 90, 135, 180, 225, 270, 315]
    .map((a) => `<rect class="sky-sun-ray" x="-1.15" y="-17" width="2.3" height="6.5" rx="1" transform="rotate(${a})"/>`)
    .join("");
  return `
    <circle r="18" class="sky-pulse"/>
    <circle r="14" class="sky-sun-halo"/>
    <g class="sky-sun-rays">${rays}</g>
    <circle r="7.4" class="sky-sun-core"/>`;
}

function earthGlyph() {
  return `
    <circle r="16" class="sky-pulse earth-pulse"/>
    <circle r="12" class="sky-earth-halo"/>
    <circle r="8" class="sky-earth-core"/>
    <ellipse class="sky-earth-eq" rx="8" ry="3.1"/>
    <path class="sky-earth-mer" d="M0,-8 A3.1,8 0 0 0 0,8 A3.1,8 0 0 0 0,-8"/>
    <path class="sky-earth-land" d="M-5,-1 C-3,-4 1,-5 4,-2 C5,1 1,4 -2,3 C-5,2 -6,1 -5,-1Z"/>`;
}

function landerGlyph() {
  return `
    <g class="sky-lander" aria-hidden="true">
      <rect x="-5.5" y="-3.5" width="11" height="6.5" rx="1.4"/>
      <circle cx="0" cy="-6.6" r="2.1"/>
      <path d="M-4.5 3 L-9.5 12 M4.5 3 L9.5 12 M0 3 L0 11"/>
      <circle cx="-9.5" cy="12" r="1.15"/>
      <circle cx="9.5" cy="12" r="1.15"/>
      <circle cx="0" cy="11" r="1.15"/>
    </g>`;
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
    const rose =
      lab === "N"
        ? `<path class="sky-compass" d="M ${p.x.toFixed(1)} ${(p.y - 16).toFixed(1)} l 4.2 11 -4.2 -2.6 -4.2 2.6 z"/>`
        : "";
    return `${rose}<text class="sky-dir" x="${p.x.toFixed(1)}" y="${p.y.toFixed(1)}" text-anchor="middle" dominant-baseline="middle">${lab}</text>`;
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
        <pattern id="${prefix}-lunar-regolith" width="200" height="200" patternUnits="userSpaceOnUse" patternContentUnits="userSpaceOnUse" patternTransform="rotate(-8 ${POLAR.cx} ${POLAR.cy})">
          <image href="${LUNAR_ALBEDO_URL}" xlink:href="${LUNAR_ALBEDO_URL}" width="200" height="200" preserveAspectRatio="xMidYMid slice" opacity="0.92"/>
        </pattern>
        <linearGradient id="${prefix}-terrain-shade" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f0e8dc" stop-opacity="0.12"/>
          <stop offset="45%" stop-color="#1a1814" stop-opacity="0.38"/>
          <stop offset="100%" stop-color="#0a0908" stop-opacity="0.22"/>
        </linearGradient>
        <filter id="${prefix}-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="3.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <circle class="sky-disc" cx="${POLAR.cx}" cy="${POLAR.cy}" r="${POLAR.rMax}" fill="url(#${prefix}-sky)"/>
      ${rings}
      <path id="${prefix}-terrain" class="sky-terrain" fill="url(#${prefix}-lunar-regolith)" stroke="url(#${prefix}-terrain-shade)"/>
      <g id="${prefix}-gaps"></g>
      <circle class="sky-geo-dash" cx="${POLAR.cx}" cy="${POLAR.cy}" r="${polarRadius(0).toFixed(1)}"/>
      <text class="sky-annote" x="${POLAR.cx + polarRadius(0) + 4}" y="${POLAR.cy - 4}">0° geometric</text>
      <text class="sky-annote sky-annote-dim" x="${POLAR.cx + 8}" y="${POLAR.cy - polarRadius(15) + 4}">+15°</text>
      ${dirs}
      <g id="${prefix}-ray-sun" class="sky-ray"></g>
      <g id="${prefix}-ray-earth" class="sky-ray earth-ray"></g>
      <g class="sky-observer" role="button" tabindex="0" aria-label="Observer (lander) — drag to move ray origins. Double-click plot to reset.">
        <text class="sky-zenith" x="0" y="-18" text-anchor="middle">zenith</text>
        ${landerGlyph()}
      </g>
      <g id="${prefix}-sun" class="sky-marker sky-sun" filter="url(#${prefix}-glow)">
        ${sunGlyph()}
        <text class="marker-name" y="-24" text-anchor="middle">Sun</text>
        <text class="marker-el" id="${prefix}-sun-el" y="30" text-anchor="middle"></text>
      </g>
      <g id="${prefix}-earth" class="sky-marker sky-earth" filter="url(#${prefix}-glow)">
        ${earthGlyph()}
        <text class="marker-name earth-name" y="-22" text-anchor="middle">Earth</text>
        <text class="marker-el" id="${prefix}-earth-el" y="28" text-anchor="middle"></text>
      </g>
      <text class="sky-caption" x="${POLAR.cx}" y="454" text-anchor="middle">Inward = higher elevation · terrain = invented silhouette (moon texture, not real DEM) · drag Sun/Earth/lander · hatch = no data</text>
    </svg>`;
}

function mountPlots() {
  const a = document.querySelector("#plot-a");
  const b = document.querySelector("#plot-b");
  if (a && !a.querySelector("svg")) a.innerHTML = skySvgMarkup("pa");
  if (b && !b.querySelector("svg")) b.innerHTML = skySvgMarkup("pb");
  bindPolarInteractions();
}

function readoutDragSuffix(prefix) {
  const d = plotDrag[prefix];
  const parts = [];
  if (d?.sun) parts.push("Sun hand-drag");
  if (d?.earth) parts.push("Earth hand-drag");
  if (d?.lander) parts.push("observer moved");
  if (!parts.length) return "";
  return ` · OVERRIDE: ${parts.join(", ")}`;
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
  if (polarDragActive) {
    el.setAttribute("transform", `translate(${x} ${y})`);
    return;
  }
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
  const origin = rayOrigin(prefix);
  const tip = polarXY(az, el);
  g.innerHTML = `<line x1="${origin.x}" y1="${origin.y}" x2="${tip.x.toFixed(1)}" y2="${tip.y.toFixed(1)}"/>`;
}

function snapshot(siteKey, hour, prefix) {
  const site = sites[siteKey];
  const dateStr = dateInput?.value || "";
  const base = syntheticBodyAngles(siteKey, hour, dateStr);
  let { sunEl, earthEl, sunAz, earthAz } = base;
  const ov = plotDrag[prefix];
  if (ov?.sun) {
    sunAz = ov.sun.az;
    sunEl = ov.sun.el;
  }
  if (ov?.earth) {
    earthAz = ov.earth.az;
    earthEl = ov.earth.el;
  }
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

function ico(name) {
  return `<iconify-icon icon="${name}" aria-hidden="true"></iconify-icon>`;
}

function pillsHtml(snap) {
  return `
    <span class="status-pill status-${snap.sunSt.code}" title="${snap.sunSt.detail}">${ico("lucide:sun")} Sun ${snap.sunSt.short}</span>
    <span class="status-pill status-${snap.earthSt.code}" title="${snap.earthSt.detail}">${ico("lucide:earth")} Earth ${snap.earthSt.short}</span>`;
}

function marginDeg(el, horizon, known) {
  if (!known || horizon === null || Number.isNaN(horizon)) return null;
  return el - horizon;
}

function whyBody(name, el, az, h, st) {
  if (st.code === "unknown") {
    return `<strong>${name}: Unknown.</strong> Azimuth ${az.toFixed(0)}° has no valid terrain on this toy map (red hatch). Missing coverage is never treated as clear.`;
  }
  const m = marginDeg(el, h.elevationDeg, h.terrainKnown);
  const terr = h.elevationDeg;
  if (st.code === "clear") {
    return `<strong>${name}: Clear.</strong> Elevation ${el.toFixed(1)}° is ${m.toFixed(1)}° above the terrain horizon (${terr.toFixed(1)}°) on azimuth ${az.toFixed(0)}°. That is centre-ray only — not a full disc, power, or radio link.`;
  }
  const vsGeo = el > 0 ? "even though it is above geometric 0°" : "and it is also at or below geometric 0°";
  return `<strong>${name}: Blocked.</strong> Elevation ${el.toFixed(1)}° sits ${Math.abs(m).toFixed(1)}° below the terrain silhouette (${terr.toFixed(1)}°) ${vsGeo}.`;
}

function meterHtml(label, el, h, st) {
  const min = -12;
  const max = 15;
  const pct = (v) => `${(((v - min) / (max - min)) * 100).toFixed(1)}%`;
  const known = h.terrainKnown && h.elevationDeg !== null;
  const terrPct = known ? pct(h.elevationDeg) : null;
  const elPct = pct(el);
  const m = marginDeg(el, h.elevationDeg, h.terrainKnown);
  const marginTxt = m === null ? "margin n/a (unknown ray)" : `margin ${m >= 0 ? "+" : ""}${m.toFixed(1)}° vs terrain`;
  return `
    <div class="meter" data-state="${st.code}">
      <div class="meter-head"><span>${ico(label === "Sun" ? "lucide:sun" : "lucide:earth")} ${label}</span><span>${el.toFixed(1)}° · ${st.short}</span></div>
      <div class="meter-track" aria-hidden="true">
        <span class="meter-geo" style="left:${pct(0)}"></span>
        ${terrPct !== null ? `<span class="meter-terr" style="left:${terrPct}"></span>` : ""}
        <span class="meter-body meter-${label.toLowerCase()}" style="left:${elPct}"></span>
      </div>
      <p class="meter-note">${marginTxt}. Tick = geometric 0°; gold tick = terrain.</p>
    </div>`;
}

function setPipeline(snapA, snapB) {
  const unknown = [snapA.sunSt, snapA.earthSt, snapB.sunSt, snapB.earthSt].some((s) => s.code === "unknown");
  const blocked = [snapA.sunSt, snapA.earthSt, snapB.sunSt, snapB.earthSt].some((s) => s.code === "blocked");
  const live = unknown ? "coverage" : blocked ? "horizon" : "classify";
  document.querySelectorAll("#pipe [data-stage]").forEach((el) => {
    el.classList.toggle("is-live", el.dataset.stage === live || el.dataset.stage === "ephemeris" || el.dataset.stage === "classify");
    el.classList.toggle("is-focus", el.dataset.stage === live);
  });
}

function lessonCopy(hour, snapA, snapB) {
  const hh = `${String(hour).padStart(2, "0")}:00`;
  const bits = [];
  if (snapA.sunSt.code === "unknown" || snapB.sunSt.code === "unknown") {
    bits.push("A hatched wedge means the engine lacks terrain on that azimuth, so the Sun is Unknown — it does not default to clear sky.");
  } else if (snapA.sunSt.code === "blocked" || snapB.sunSt.code === "blocked") {
    bits.push("The shaded moon-textured fill is the synthetic terrain skyline (appearance only, not a DEM). If the Sun sits in or behind that fill, the centre ray is Blocked even if elevation looks small and positive.");
  } else {
    bits.push("Both Suns are Clear: each centre ray is above the known terrain horizon at this hour.");
  }
  const aSunM = marginDeg(snapA.sunEl, snapA.sunH.elevationDeg, snapA.sunH.terrainKnown);
  const bSunM = marginDeg(snapB.sunEl, snapB.sunH.elevationDeg, snapB.sunH.terrainKnown);
  const aTxt = aSunM === null ? "n/a" : `${aSunM >= 0 ? "+" : ""}${aSunM.toFixed(1)}°`;
  const bTxt = bSunM === null ? "n/a" : `${bSunM >= 0 ? "+" : ""}${bSunM.toFixed(1)}°`;
  return {
    headline: `${hh} UTC · Sun margin A ${aTxt} vs B ${bTxt} (synthetic).`,
    body: `${bits[0]} Earth uses the same contract on a different azimuth. Geometric 0° (dashed ring) is a smooth sphere — not the crater rim.`,
  };
}

let lastStatusKey = "";
function pulseStatus(key) {
  if (key === lastStatusKey) return;
  lastStatusKey = key;
  if (!hasGsap || reducedMotion) return;
  window.gsap.fromTo(
    ".status-pill, .lesson-board",
    { scale: 0.97, opacity: 0.7 },
    { scale: 1, opacity: 1, duration: 0.35, ease: "power2.out", stagger: 0.04, overwrite: "auto" }
  );
}

function updatePlot(prefix, siteKey, hour) {
  syncPlotDragSession();
  const snap = snapshot(siteKey, hour, prefix);
  const terrain = document.querySelector(`#${prefix}-terrain`);
  if (terrain) terrain.setAttribute("d", terrainFillPath(siteKey));
  gapWedges(siteKey, prefix);
  const sunPt = polarXY(snap.sunAz, snap.sunEl);
  const earthPt = polarXY(snap.earthAz, snap.earthEl);
  moveMarker(document.querySelector(`#${prefix}-sun`), sunPt.x, sunPt.y);
  moveMarker(document.querySelector(`#${prefix}-earth`), earthPt.x, earthPt.y);
  const plotEl = document.querySelector(prefix === "pa" ? "#plot-a" : "#plot-b");
  const observerG = plotEl?.querySelector(".sky-observer");
  const L = plotDrag[prefix]?.lander;
  const ox = L?.x ?? POLAR.cx;
  const oy = L?.y ?? POLAR.cy;
  moveMarker(observerG, ox, oy);
  const sunElLab = document.querySelector(`#${prefix}-sun-el`);
  const earthElLab = document.querySelector(`#${prefix}-earth-el`);
  if (sunElLab) sunElLab.textContent = `${snap.sunEl.toFixed(1)}°`;
  if (earthElLab) earthElLab.textContent = `${snap.earthEl.toFixed(1)}°`;
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
  document.querySelector("#meters-a").innerHTML =
    meterHtml("Sun", snapA.sunEl, snapA.sunH, snapA.sunSt) +
    meterHtml("Earth", snapA.earthEl, snapA.earthH, snapA.earthSt);
  document.querySelector("#meters-b").innerHTML =
    meterHtml("Sun", snapB.sunEl, snapB.sunH, snapB.sunSt) +
    meterHtml("Earth", snapB.earthEl, snapB.earthH, snapB.earthSt);
  document.querySelector("#why-a").innerHTML =
    whyBody("Sun", snapA.sunEl, snapA.sunAz, snapA.sunH, snapA.sunSt) +
    " " +
    whyBody("Earth", snapA.earthEl, snapA.earthAz, snapA.earthH, snapA.earthSt);
  document.querySelector("#why-b").innerHTML =
    whyBody("Sun", snapB.sunEl, snapB.sunAz, snapB.sunH, snapB.sunSt) +
    " " +
    whyBody("Earth", snapB.earthEl, snapB.earthAz, snapB.earthH, snapB.earthSt);
  document.querySelector("#readout-a").textContent =
    `${snapA.site.id} · Sun az ${snapA.sunAz.toFixed(0)}° el ${snapA.sunEl.toFixed(1)}° · Earth az ${snapA.earthAz.toFixed(0)}° el ${snapA.earthEl.toFixed(1)}° · ${date} ${String(hour).padStart(2, "0")}:00 UTC · SYNTHETIC${readoutDragSuffix("pa")}`;
  document.querySelector("#readout-b").textContent =
    `${snapB.site.id} · Sun az ${snapB.sunAz.toFixed(0)}° el ${snapB.sunEl.toFixed(1)}° · Earth az ${snapB.earthAz.toFixed(0)}° el ${snapB.earthEl.toFixed(1)}° · centre-ray only${readoutDragSuffix("pb")}`;

  const lesson = lessonCopy(hour, snapA, snapB);
  const headline = document.querySelector("#lesson-headline");
  const body = document.querySelector("#lesson-body");
  if (headline) headline.textContent = lesson.headline;
  if (body) body.textContent = lesson.body;
  setPipeline(snapA, snapB);
  pulseStatus(`${snapA.sunSt.code}${snapA.earthSt.code}${snapB.sunSt.code}${snapB.earthSt.code}|${keyA}|${keyB}`);

  if (compareStrip) {
    compareStrip.innerHTML = `
      <div class="hud-grid">
        <div class="hud-cell">
          <p class="hud-kicker">Site A · ${snapA.site.name}</p>
          <p><span class="status-pill status-${snapA.sunSt.code}">${ico("lucide:sun")} Sun ${snapA.sunSt.short}</span>
             <span class="status-pill status-${snapA.earthSt.code}">${ico("lucide:earth")} Earth ${snapA.earthSt.short}</span></p>
          <p class="hud-detail">${snapA.sunSt.detail}</p>
        </div>
        <div class="hud-cell">
          <p class="hud-kicker">Site B · ${snapB.site.name}</p>
          <p><span class="status-pill status-${snapB.sunSt.code}">${ico("lucide:sun")} Sun ${snapB.sunSt.short}</span>
             <span class="status-pill status-${snapB.earthSt.code}">${ico("lucide:earth")} Earth ${snapB.earthSt.short}</span></p>
          <p class="hud-detail">${snapB.earthSt.detail}</p>
        </div>
      </div>`;
  }

  sunLine?.setAttribute("d", makeSunPath(keyA));
  earthLine?.setAttribute("d", makeEarthPath(keyA));
  sunArea?.setAttribute("d", makeSunArea(keyA));
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
  updateGlobe(keyA, keyB, hour);
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

function latLonToVec(lat, lon, radius) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function craterTexture() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#b7aea3";
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 220; i += 1) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const r = 2 + Math.random() * 18;
    ctx.fillStyle = `rgba(70,64,58,${0.12 + Math.random() * 0.25})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = "rgba(40,40,48,0.35)";
  ctx.fillRect(0, 470, 512, 42);
  return new THREE.CanvasTexture(c);
}

function earthTexture() {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 64;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#1b4f8c";
  ctx.fillRect(0, 0, 128, 64);
  ctx.fillStyle = "#2f8f56";
  [
    [18, 22, 28, 16],
    [52, 18, 22, 14],
    [88, 28, 26, 12],
    [30, 40, 18, 10],
  ].forEach(([x, y, w, h]) => {
    ctx.beginPath();
    ctx.ellipse(x, y, w / 2, h / 2, 0.2, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.fillStyle = "#e8eef4";
  ctx.fillRect(0, 0, 128, 6);
  ctx.fillRect(0, 58, 128, 6);
  return new THREE.CanvasTexture(c);
}

function makeBeacon(color) {
  const T = THREE;
  const g = new T.Group();
  const cone = new T.Mesh(new T.ConeGeometry(0.028, 0.1, 10), new T.MeshBasicMaterial({ color }));
  cone.position.y = 0.06;
  const ring = new T.Mesh(new T.TorusGeometry(0.038, 0.007, 8, 18), new T.MeshBasicMaterial({ color }));
  ring.rotation.x = Math.PI / 2;
  g.add(cone, ring);
  return g;
}

function placeBeacon(group, lat, lon) {
  const p = latLonToVec(lat, lon, 1.02);
  group.position.copy(p);
  group.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p.clone().normalize());
}

const globe = { ready: false };

function loadMoonAlbedo(material) {
  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin("anonymous");
  loader.load(
    "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/textures/planets/moon_1024.jpg",
    (tex) => {
      if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
      material.map = tex;
      material.needsUpdate = true;
    },
    undefined,
    () => {}
  );
}

function initGlobe() {
  const host = document.querySelector("#moon-globe");
  if (!host) return;
  try {
    const w = host.clientWidth || 260;
    const h = host.clientHeight || 260;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, w / h, 0.1, 40);
    camera.position.set(0, -3.4, 2.6);
    camera.lookAt(0, -0.2, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h);
    host.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, -0.15, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 1.85;
    controls.maxDistance = 6;
    controls.enablePan = false;

    const moonMat = new THREE.MeshStandardMaterial({
      map: craterTexture(),
      roughness: 0.95,
      metalness: 0.02,
    });
    const moon = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), moonMat);
    loadMoonAlbedo(moonMat);
    scene.add(moon);

    const polePts = [];
    for (let i = 0; i <= 64; i += 1) {
      const t = (i / 64) * Math.PI * 2;
      polePts.push(new THREE.Vector3(Math.cos(t) * 0.14, -0.99, Math.sin(t) * 0.14));
    }
    const polarRing = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(polePts),
      new THREE.LineBasicMaterial({ color: 0xe3b34a, transparent: true, opacity: 0.7 })
    );
    moon.add(polarRing);

    const amb = new THREE.AmbientLight(0x8899aa, 0.32);
    const sun = new THREE.DirectionalLight(0xffe6b0, 1.45);
    sun.castShadow = false;
    const sunBall = new THREE.Mesh(new THREE.SphereGeometry(0.11, 16, 16), new THREE.MeshBasicMaterial({ color: 0xffe08a }));
    scene.add(amb, sun, sunBall);
    const earth = new THREE.Mesh(
      new THREE.SphereGeometry(0.09, 20, 20),
      new THREE.MeshBasicMaterial({ map: earthTexture() })
    );
    scene.add(earth);
    const pinA = makeBeacon(0xe3b34a);
    const pinB = makeBeacon(0x5ba8d8);
    moon.add(pinA, pinB);

    globe.ready = true;
    globe.sun = sun;
    globe.sunBall = sunBall;
    globe.earth = earth;
    globe.pinA = pinA;
    globe.pinB = pinB;
    globe.renderer = renderer;
    globe.scene = scene;
    globe.camera = camera;
    globe.moon = moon;
    globe.controls = controls;

    window.addEventListener("resize", () => {
      if (!globe.ready) return;
      const nw = host.clientWidth || 260;
      const nh = host.clientHeight || 260;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    });

    function tick() {
      controls.update();
      renderer.render(scene, camera);
      globe.raf = requestAnimationFrame(tick);
    }
    tick();
  } catch (err) {
    host.textContent = "Globe unavailable (Three.js). Polar plots still work.";
    globe.ready = false;
  }
}

function updateGlobe(keyA, keyB, hour) {
  if (!globe.ready) return;
  const a = sites[keyA];
  const b = sites[keyB];
  placeBeacon(globe.pinA, a.lat, a.lon);
  placeBeacon(globe.pinB, b.lat, b.lon);
  const az = (SIMULATION.sunAzimuthDeg(hour) * Math.PI) / 180;
  const sunDir = new THREE.Vector3(Math.sin(az), 0.35, Math.cos(az)).normalize();
  globe.sun.position.copy(sunDir.clone().multiplyScalar(5));
  globe.sunBall.position.copy(sunDir.clone().multiplyScalar(5));
  const eaz = (SIMULATION.earthAzimuthDeg(hour) * Math.PI) / 180;
  globe.earth.position.set(Math.sin(eaz) * 1.7, -0.15, Math.cos(eaz) * 1.7);
  const cap = document.querySelector("#globe-caption");
  if (cap) {
    cap.textContent = `Illustrative south pole · A ${a.name} · B ${b.name} · Sun az ${SIMULATION.sunAzimuthDeg(hour).toFixed(0)}° · Three.js OrbitControls · SYNTHETIC`;
  }
}

function initStarfield() {
  const canvas = document.querySelector("#starfield");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const stars = [];
  let starRaf = null;
  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    stars.length = 0;
    const n = Math.floor((canvas.width * canvas.height) / 9000);
    for (let i = 0; i < n; i += 1) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.2,
        a: 0.25 + Math.random() * 0.6,
        tw: Math.random() * Math.PI * 2,
        sp: 0.004 + Math.random() * 0.01,
      });
    }
  }
  function drawFrame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of stars) {
      if (!reducedMotion) s.tw += s.sp;
      const a = reducedMotion ? s.a : s.a * (0.55 + 0.45 * Math.sin(s.tw));
      ctx.fillStyle = `rgba(230,230,240,${a})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    starRaf = requestAnimationFrame(drawFrame);
  }
  resize();
  starRaf = requestAnimationFrame(drawFrame);
  window.addEventListener("resize", resize);
}

const GLOSS = {
  geometric:
    "Geometric 0° is the local horizon of a smooth sphere. A target can sit above it and still hide behind real (or synthetic) terrain.",
  terrain:
    "The moon-textured fill is the terrain horizon silhouette — the highest blocking elevation along each azimuth (texture is display-only). Compare the Sun/Earth discs to this silhouette, not only to 0°.",
  centre:
    "Centre-ray means one line of sight through the disc centre. It is not finite-disc visibility, solar power, or a communications link.",
  unknown:
    "Unknown means required terrain is missing or masked on that azimuth. The contract forbids treating a gap as clear sky.",
};

function bindGlossary() {
  const def = document.querySelector("#gloss-def");
  document.querySelectorAll(".gloss-term").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".gloss-term").forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");
      const term = btn.dataset.term;
      if (def) def.textContent = GLOSS[term] || "";
      document.body.dataset.highlight = term || "";
      if (hasGsap && !reducedMotion) {
        window.gsap.fromTo(def, { opacity: 0.4, y: 4 }, { opacity: 1, y: 0, duration: 0.25, ease: "power2.out" });
      }
    });
  });
}

mountPlots();
initStarfield();
initGlobe();
bindGlossary();
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
  const intro = window.gsap.timeline({ defaults: { ease: "power2.out" } });
  intro
    .from(".sky-panel", { opacity: 0, y: 18, duration: 0.5, stagger: 0.1 })
    .from(".lesson-board", { opacity: 0, y: 10, duration: 0.4 }, "<0.15")
    .from(".pipe li", { opacity: 0, y: 6, duration: 0.28, stagger: 0.04 }, "<")
    .from(".moon-globe-wrap", { opacity: 0, scale: 0.92, duration: 0.5 }, 0)
    .from(".shape-key li", { opacity: 0, y: 6, duration: 0.3, stagger: 0.05 }, "<0.2");
  window.gsap.to(".sky-sun-rays", {
    rotation: 360,
    svgOrigin: "0 0",
    duration: 22,
    repeat: -1,
    ease: "none",
  });
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
