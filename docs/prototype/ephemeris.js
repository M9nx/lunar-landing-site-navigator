/**
 * Synthetic ephemeris + terrain model for the static prototype only.
 * SPICE / validated kernels live in Hub notebooks — not in this file.
 * @see docs/ENGINE_CALCULATION_PIPELINE.md
 */

export const SIMULATION = {
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

/** Site registry (labels + phases for synthetic elevation curves). */
export const sites = {
  s04p02: {
    name: "Site04 S04-P02",
    id: "LOLA Site04 · X/Y −2652.5 / −6082.5 m",
    phase: 0.15,
    earthPhase: 1.05,
    lat: -89.78,
    lon: -156.44,
  },
  shackleton: {
    name: "Shackleton rim",
    id: "PROVISIONAL · LOLA SITE04",
    phase: 0.15,
    earthPhase: 1.05,
    lat: -89.54,
    lon: 129.2,
  },
  malapert: {
    name: "Malapert Massif",
    id: "PROVISIONAL · LOLA SITE23",
    phase: 1.1,
    earthPhase: 0.35,
    lat: -86.0,
    lon: 2.7,
  },
};

export function angle(phase, hour, amplitude, offset = 0) {
  return offset + amplitude * Math.sin((2 * Math.PI * hour) / 24 + phase);
}

/**
 * @param {string} isoDate - YYYY-MM-DD from &lt;input type="date"&gt;
 * @returns {number} deterministic seed [0, 1) for layering tiny variation on synthetic angles
 */
export function dateVariationSeed(isoDate) {
  if (!isoDate || typeof isoDate !== "string") return 0;
  let h = 0;
  for (let i = 0; i < isoDate.length; i += 1) h = (Math.imul(31, h) + isoDate.charCodeAt(i)) | 0;
  const u = Math.abs(Math.sin(h * 0.0001));
  return u - Math.floor(u);
}

/**
 * @param {string} siteKey
 * @param {number} hour - 0..23
 * @param {string} [dateStr] - optional YYYY-MM-DD
 */
export function syntheticBodyAngles(siteKey, hour, dateStr) {
  const site = sites[siteKey];
  const d = dateVariationSeed(dateStr) * 0.35;
  return {
    sunEl: angle(site.phase, hour, 8.2, -0.7 + d * 0.1),
    earthEl: angle(site.earthPhase, hour, 6.5, -0.3 + d * 0.08),
    sunAz: SIMULATION.sunAzimuthDeg(hour),
    earthAz: SIMULATION.earthAzimuthDeg(hour),
  };
}
