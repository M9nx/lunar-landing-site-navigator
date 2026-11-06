# Jupyter practice pass (research workspace)

**Status:** operational guidance — **not** part of the static synthetic demo or the gated API.

This separates three lanes:

| Lane | Role |
|------|------|
| **JupyterHub** | Run notebooks and scripts against data mounted read-only (e.g. `~/data` / team mount). Write notebooks, notes, and **ignored** outputs under `research-results/` or Hub home — **do not commit rasters or large artifacts.** |
| **Static prototype** | [`prototype/`](prototype/) — **synthetic** UI only; illustrates flow and **clear / blocked / unknown** (see **[DEMO_DESIGN_SKETCH.md](DEMO_DESIGN_SKETCH.md)**). |
| **API** | [`backend/routers/calc.py`](../backend/routers/calc.py): **`GET /v1/benchmark/status`** = DB/infrastructure ping; **`POST /v1/compare`** stays gated while **`SCIENCE_CALCULATIONS_READY`** is false. Do not route practice science through `/v1/compare`. |

## Practice session checklist (one labeled run)

1. **Inspect existing notebooks** under `research/notebooks/` (e.g. Site04 registration, point selection, geometry) and reuse cells where possible.
2. **Data:** use current practice files only inside the Hub mount; treat Product 78/90/69 as **practice inputs** for ingestion, masks, and transforms — **not** validated challenge outputs until benchmarks pass.
3. **Record in a run note** (ignored folder): CRS, masks, source hashes, environment (Python/GDAL/PROJ versions), and **git commit** of the notebook/script — not the raster bytes.
4. **Keep outputs out of git:** `data/` and `research-results/` remain ignored; copy conclusions into markdown in-repo only as **documentation**, not binary results.

## Competition caution

NASA Space Apps prep guidance may restrict developing the **submission** solution before the event. Confirm with your **local organizer** what existing simulation or practice code may be reused: [Space Apps local events](https://www.spaceappschallenge.org/2026/local-events/santiago-dominican-republic/?utm_source=chatgpt.com) (example local page; verify your event’s rules).

## Cross-links

- Method stages: **[METHOD_DECISION.md](METHOD_DECISION.md)**
- Frame and horizon language: **[FRAME_GEOMETRY_VALIDATION.md](FRAME_GEOMETRY_VALIDATION.md)**
- Far-field / Product context: **[FAR_FIELD_B5_B6_PLAN.md](FAR_FIELD_B5_B6_PLAN.md)**
- Engine pipeline (concept): **[ENGINE_CALCULATION_PIPELINE.md](ENGINE_CALCULATION_PIPELINE.md)**
