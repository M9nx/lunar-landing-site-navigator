# Demo design sketch (synthetic prototype)

**Status:** UX intent for the **static** browser demo — all values are **synthetic** and **not** validated lunar science.

Related: **[ENGINE_CALCULATION_PIPELINE.md](ENGINE_CALCULATION_PIPELINE.md)** (stages and state contract), **[DATASET_INTAKE_CHECKLIST.md](DATASET_INTAKE_CHECKLIST.md)** (real data handoff), **[METHOD_DECISION.md](METHOD_DECISION.md)** (method stages), **[BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)** (metrics and gates).

## User flow (implemented in this pass)

1. Open [`docs/prototype/index.html`](prototype/index.html) (served locally or from static hosting).
2. Choose **Site A** and **Site B** from synthetic presets (two-site comparison at one selected UTC hour).
3. Adjust **date** and **hour** (date is for labeling only in this synthetic pass).
4. Read **per-site cards**: Sun and Earth **illustrative** elevations, **geometric horizon** (0°), **synthetic terrain horizon**, and **centre-ray** states: **Clear**, **Blocked**, or **Unknown (terrain gap)** — each with explicit text (not color alone).
5. Read **comparison strip**: Site A vs Site B at the same hour for Sun and Earth states.
6. Inspect **chart**: Sun/Earth curves, **geometric horizon line**, **terrain horizon lines** (Site A and Site B), legend.

**Synthetic hotspots (Malapert preset):** at **02:00 UTC**, the invented Sun azimuth (~30°) falls in a **masked sector** → **Unknown (terrain gap)**. Near **06:00–07:00 UTC**, a **ridge** raises the synthetic terrain horizon → **Blocked** for typical illustrative Sun elevations unless above the ridge.

**API:** [`backend/routers/calc.py`](../backend/routers/calc.py) keeps **`SCIENCE_CALCULATIONS_READY=false`** and gates **`POST /v1/compare`**. The prototype does not submit science to the API; health/benchmark calls are **infrastructure probes** only.

## Future extension (not required for this pass)

- **Same site, two dates:** duplicate time-axis comparison or side-by-side cards; not implemented in the current static pass.

## Limitations and labels

- Every numeric curve and terrain rule is **labeled SYNTHETIC** in the UI.
- **Product 90 / Product 69** (and similar) are **practice references** for research workflows only — not ground truth for the challenge until a compatible benchmark says otherwise (**[FAR_FIELD_B5_B6_PLAN.md](FAR_FIELD_B5_B6_PLAN.md)**).

## Accessibility

- Status uses **words** (Clear / Blocked / Unknown) plus optional color; meaning does not rely on color alone.
- Controls are keyboard-focusable; skip link remains at top of page.

## Navigating these docs from the site

- From the doc viewer: `documents.html?doc=DEMO_DESIGN_SKETCH.md` (after the doc is listed in `assets/js/markdown.js`).
- From the prototype: footer links to the pipeline and this sketch.
