# Engine calculation pipeline (concept)

**Status:** training reference for the intended full pipeline — not an implemented production path in this repository.

This note summarizes **stages and contracts** for a terrain-aware visibility navigator. For staged method detail see **[METHOD_DECISION.md](METHOD_DECISION.md)**. For benchmark metrics and gate language see **[BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)**. For frame, notebook, and horizon terminology see **[FRAME_GEOMETRY_VALIDATION.md](FRAME_GEOMETRY_VALIDATION.md)**. For far-field terrain and Product 69/90 *research* context see **[FAR_FIELD_B5_B6_PLAN.md](FAR_FIELD_B5_B6_PLAN.md)**.

## Tool stack (what does what)

No single package covers validated science, GIS rasters, and browser visuals. Keep responsibilities separate:

| Need | Good fit | Use it for |
|------|----------|------------|
| Sun/Earth positions over time | [NAIF SPICE](https://naif.jpl.nasa.gov/) via [SpiceyPy](https://github.com/AndrewAnnex/spiceypy) | Ephemerides and reference-frame transforms (`spkezr`, `pxform`, `azlcpo`, etc.); derived observation geometry *relative to documented frames and kernels*. |
| Raster and lunar coordinates | **rasterio** + **pyproj** (existing research stack) | DEM reads, CRS, masks, site coordinates, terrain horizon sampling. Ballpark or unvalidated frame mapping stays a **blocker** for science claims — see [DATASET_INTAKE_CHECKLIST.md](DATASET_INTAKE_CHECKLIST.md) and [FRAME_GEOMETRY_VALIDATION.md](FRAME_GEOMETRY_VALIDATION.md). |
| Dynamic 3D visuals (static site) | **Three.js** (+ **OrbitControls** in the prototype) | Spheres, textures, camera/light — [prototype](prototype/index.html) loads `three.module.js` and keeps synthetic sky math in [`ephemeris.js`](prototype/ephemeris.js). **Illustration only** — not SPICE. |
| Optional full globe / map UI | **CesiumJS** | Global globe with terrain/imagery layers; extra setup vs custom lunar polar rasters; still not a substitute for SPICE + validated rasters. |
| Visual assets | [NASA 3D Resources](https://nasa3d.arc.nasa.gov/) and related Moon imagery | Appearance (textures, models). Treat as **display**; they do not define geometry. |

**Hub / notebooks:** SpiceyPy and rasterio are already on the Hub image (see `backend/Dockerfile`). The API remains gated for validated compare until benchmarks pass; storing run metadata in SQLite is unrelated to ephemeris math.

## Stages

1. **Terrain input** — DEM / multiband stack (and metadata) covering the observer and required azimuths.
2. **Metadata and coverage checks** — CRS, nodata, masks, dtype, scale/offset, footprint; reject or flag incomplete rays.
3. **Terrain horizon by azimuth** — along each azimuth, derive the maximum blocking elevation (or equivalent) from valid samples; missing required samples → no classified clearance on that ray.
4. **Time-tagged Sun and Earth directions** — ephemeris (e.g. SPICE) or another documented source; observer position, frame, and time scale must match the benchmark plan.
5. **Visibility classification** — compare **target elevation** to **terrain horizon** on the relevant azimuth when terrain is known (see contract below).
6. **Time windows** — merge contiguous intervals per body and label transitions.
7. **Display** — geometric vs terrain horizons, body markers, and **clear / blocked / unknown** (not color-only).

## Definitions

- **Geometric horizon** — horizon for a smooth reference surface (e.g. sphere/ellipsoid at the observer), **without** local terrain relief. A target can be above this and still hidden behind terrain.
- **Terrain horizon** — horizon angle from terrain/occlusion along the azimuth of interest, derived from validated elevation data and sampling rules.
- **Centre-ray visibility** — comparison of the **centre** of the apparent disk to the terrain horizon in that direction. It is **not** finite-disc visibility (partial disk), **not** solar power, **not** a communications link budget, and **not** landing safety.

## State contract (centre-ray vs terrain)

| State | Meaning |
|--------|--------|
| **clear** | Required terrain data for that ray is **known**, and target elevation is **strictly above** the terrain horizon. |
| **blocked** | Required terrain data is **known**, and target elevation is **at or below** the terrain horizon. |
| **unknown** | Required terrain coverage is **missing** or **masked** on that ray (or otherwise not computable). **Unknown must never be treated as clear.** |

## Synthetic / demo scope

The static prototype ([`prototype/index.html`](prototype/index.html)) and unit tests under `tests/test_horizon_visibility_semantics.py` use **invented** terrain profiles and angles in a **simplified local plane** — not validated lunar geodesy, frames, or ephemeris. They exist to rehearse **labels and state logic** only.

For JupyterHub vs API vs prototype boundaries see **[JUPYTER_PRACTICE_PASS.md](JUPYTER_PRACTICE_PASS.md)**.

For the **SIMULATION incremental stream** (SSE + replay controls, separate from `POST /v1/compare`) see **[SIMULATION_STREAM.md](SIMULATION_STREAM.md)**.

## Flow diagram

```mermaid
flowchart LR
  subgraph in [Inputs]
    T[Terrain rasters]
    M[Metadata masks]
  end
  subgraph hor [Horizon]
    H[Terrain horizon by azimuth]
  end
  subgraph sky [Ephemeris]
    E[Sun Earth directions over time]
  end
  subgraph cls [Classification]
    C[Compare target elevation to terrain horizon]
  end
  subgraph out [Outputs]
    W[Time windows]
    D[Display]
  end
  T --> M
  M --> H
  M -->|missing ray| D
  E --> C
  H --> C
  C --> W --> D
```
