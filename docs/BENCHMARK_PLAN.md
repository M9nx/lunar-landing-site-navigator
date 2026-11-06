# Benchmark Plan and Partial Results

This document defines evaluation methods and records Site04 runs. B1–B4 and the B5 near-field subcheck have reported results; far-field B5, B6, and B7 remain open. These Hub results are owner-reported; raw run files remain in the owner's persistent Jupyter home and are not committed here.

## Evaluation principles

1. Freeze the test cases, reference source, and metric definitions before comparing implementations.
2. Use an independent reference for date-specific geometry where possible.
3. Keep long-term-average products such as LOLA GDRVIS separate from date-specific predictions.
4. Report data resolution, coordinate frame, time standard, terrain model, and sampling interval with every result.
5. Mark synthetic demo values as excluded from scientific accuracy evaluation.

## Candidate metrics

| Metric | Definition | Test procedure | Interpretation |
|---|---|---|---|
| Direction-vector angular error | For normalized predicted/reference vectors **u** and **v**, error = arccos(clamp(**u**·**v**, −1, 1)), converted to degrees. | Evaluate Sun and Earth direction at fixed site/time cases against an independent ephemeris/reference. | Smaller error means closer directional agreement. Record reference frame and aberration/time settings. |
| Elevation-angle error | Absolute difference between predicted and reference local elevation angles, in degrees. | Compare at a predetermined set of site/time cases. | Measures error in the quantity shown to the user. |
| Visibility-window boundary error | For every reference start/end boundary, take absolute time difference; report mean and maximum in seconds or minutes. | Compare transition times using a defined visibility threshold and terrain model. | Indicates how well the tool identifies when a window opens or closes. |
| Long-term illumination/visibility fraction difference | Absolute difference in percentage points between a prototype’s long-term aggregate and a compatible reference product. | Run a sufficiently long, documented simulation and compare only to a product with matching assumptions and coverage. | Useful for broad aggregate validation; not validation of an individual date. |
| Task completion time | Elapsed time for a participant to compare two site/date options and answer a fixed question. | Give each participant the same task and record completion time. | Lower time may indicate an easier comparison flow; interpret alongside correctness. |
| Interpretation accuracy | Share of participants who correctly identify which option has the better displayed sunlight or visibility result, as defined by the demo data. | Ask a fixed comprehension question after the task. | Checks whether labels and visualizations communicate the result. |
| Calculation runtime | Wall-clock time to compute a comparison for fixed inputs. | Run the same input cases on the same device; report median and range. | Measures responsiveness; record hardware and software version. |

## Important compatibility caveats

- GDRVIS is modeled over approximately one lunar precession cycle (~18.6 years). It can support comparisons of long-term average illumination/Earth visibility, but cannot serve as an exact oracle for selected-date window boundaries.
- Comparisons are meaningful only when the site coordinates, time range, reference frame, terrain representation, elevation above surface, and visibility definition are compatible.
- Product resolutions differ. A 5 m/pixel local DEM and a coarser polar grid may produce different terrain horizons.
- Earth visibility is not equivalent to a complete radio link budget or guaranteed communications service.
- Sun visibility is not equivalent to generated power; panel orientation and other engineering factors may matter.

## Initial test matrix to populate

| Case ID | Site / coordinates | UTC input time(s) | Reference product/tool | Terrain model | Expected output | Status |
|---|---|---|---|---|---|---|
| S04-01 | Site04 S04-P02, X=−2652.5 m, Y=−6082.5 m; row/col 1416/1269 | 2025-01-01T00:00Z through 23:00Z, hourly | DE421 SPICE geometric baseline; B4 cross-check via NAIF `azlcpo` | Reference sphere for notebook 03; PCK ellipsoid for B4 | Sun/Earth centre azimuth/elevation; no terrain clearance | B1–B3 execution reported; B4 pass reported; review pending |
| S23-01 | Malapert Massif; exact point pending ROI review | Pending | Pending | Pending | Sun/Earth azimuth and elevation | Not run |
| S04-AVG | Shackleton rim | Aggregate period compatible with reference | LOLA GDRVIS, if grid coverage and assumptions match | Product-defined | Average illumination/Earth visibility comparison | Not run |
| S23-AVG | Malapert Massif | Aggregate period compatible with reference | LOLA GDRVIS, if grid coverage and assumptions match | Product-defined | Average illumination/Earth visibility comparison | Not run |

## First recorded run: Site04 S04-P02

**Provenance:** Results below were reported from a JupyterHub run on 2026-11-06. The notebook CSV and JSON manifests remain in the owner's persistent Hub home; they were not attached to this repository update. Values marked approximate should be replaced with exact manifest values if the artifacts are later archived.

| Gate | Reported result | Status / interpretation |
|---|---|---|
| B1: Raster registration | S04-P02 sampled at row 1416, column 1269; projected coordinate matches the audited pixel centre (X=−2652.5 m, Y=−6082.5 m); Z=1736.902 m, LDEC=2 | Executed; benchmark owner sign-off pending |
| B2: Projection | Inverse/forward projection round-trip residual approximately 7.5×10⁻⁹ m | Within proposed 1×10⁻³ m criterion for this point; extent-wide cases still pending |
| B3: Frame and kernels | Five kernels loaded; `MOON_ME` resolved as frame ID 31001; cached kernel SHA-256 values matched notebook 03 manifest | Executed; manifest review pending |
| B4: Local angle conversion | Hand-built ellipsoid-normal basis vs NAIF `azlcpo` for Sun/Earth at 00:00, 12:00, 23:00 UTC (six comparisons); maximum absolute azimuth and elevation errors each approximately 1×10⁻¹⁴°; manifest reports `B4_pass: true` | Pass against proposed 1×10⁻⁶° criterion for this point, these epochs, and these kernel inputs |
| B5: Terrain horizon | Near-field-only comparison: 720/720 rays complete; per-bin Method A/B sample counts match; maximum absolute profile difference ≈3.6×10⁻¹⁵°; median difference 0°; manifest reports `near_field_pass: true` | Near-field subcheck passed as reported; far-field/Product 90 compatibility and full B5 remain open |
| B6: Published illumination context | No result yet | Open |
| B7: Runtime/API | `GET /v1/benchmark/status` returns DB ping ms and `calculation_version` with `science_calculations_ready: false`; prototype calls it for smoke checks — **not** lunar geometry | Partial (infrastructure only); compare remains 503 |

**B5 data coverage:** The Site04 5 m raster is 16 × 16 km, which supports a near-field horizon check but does not cover a full far-field skyline. Barker et al. used nested terrain products: 5 m below 5 km, 80 m from 5–100 km, and 240 m at larger distances. Product 90's 80 m and 240 m COGs are now mounted on the Hub host and have a user-reported source preflight; until frame alignment, elevation convention, and far-field coverage are verified, any completed Site04 horizon remains near-field-only. Reference: https://ntrs.nasa.gov/citations/20205009660

**B5 near-field run (owner-reported, 2026-11-06):** The Hub run reports 720 of 720 azimuth coverage probes complete, matching A/B sample counts per 0.5° bin (for example, 943/943 at 0°), maximum absolute horizon difference approximately 3.6×10⁻¹⁵°, median 0°, and `near_field_pass: true`. The hourly visibility CSV has 48 rows marked complete and reports centre-ray clearance over the 0–5 km near-field only. Method A streams pixel-centre samples into ray bins; Method B rescans those same pixel-centre samples per fixed ray. Their agreement checks the two code paths against one another, but does not independently validate the DEM horizon, shared frame mapping, or far-field visibility. The executed CSV/JSON artifacts are not committed.

**Product 90 source preflight (owner-reported, 2026-11-06):** Both Product 90 COGs are mounted in the Hub data path. The audit reports valid S04-P02 samples for both products and valid elevations at all 25 shared-area comparison samples. Strict pyproj CRS equality and equality ignoring axis order are both false, while the normalized projection-math check reports `projection-parameters-match: true` for method, numeric projection parameters, and ellipsoid axes (1,737,400 m sphere). The shared-area elevation deltas remain diagnostic only because the rasters have different resolutions; they do not establish the vertical datum. This preflight does not prove the MOON_ME body-fixed frame tie, elevation convention, far-field valid-data coverage along all 720 rays, or seam behavior. Keep `compatibility_verdict: blocked` and `full_B5_pass: false`; raw audit JSON and rasters remain outside git.

Notebook 03 reports geometric centre angles at 2025-01-01T00:00Z of approximately Sun azimuth 318.6° / elevation +1.68° and Earth azimuth 152° / elevation −6.5°. They are not terrain-cleared. The B4 run reports the Site04 PCK ellipsoid radii [1737.4, 1737.4, 1737.4] km and approximately 0° between radial-sphere up and ellipsoid up at S04-P02.

Artifacts in the owner's persistent Hub home:

- `~/research-results/site04-spice-baseline/S04-P02_2025-01-01_hourly_geometric_angles.csv`
- `~/research-results/site04-spice-baseline/kernel_and_run_manifest.json`
- `~/research-results/site04-spice-baseline/S04-P02_azlcpo_crosscheck.csv`
- `~/research-results/site04-spice-baseline/B4_validation_manifest.json`
- `~/research-results/site04-spice-baseline/B5_terrain_sources.json`
- `~/research-results/site04-spice-baseline/S04-P02_horizon_profile.csv`
- `~/research-results/site04-spice-baseline/S04-P02_hourly_terrain_visibility.csv`
- `~/research-results/site04-spice-baseline/B5_validation_manifest.json`

B4 validates the local angle conversion against NAIF's routine using the same DE421 ephemeris and kernels. It is not an independent ephemeris validation. The reported B5 near-field pass is limited to the 0–5 km sample domain and method consistency; it does not close far-field B5. Keep `SCIENCE_CALCULATIONS_READY=false` while far-field B5, B6–B7, and benchmark-owner review remain open.

## Far-field B5 diagnostics and B7 API probe (2026-11-06, workspace)

**Host:** Linux workstation with Docker and repo `data/` COGs mounted read-only into `lunar-navigator-singleuser`.

**Software (inside container):** Python 3.12.x, rasterio 1.5.x, GDAL 3.12.x, PROJ 9.8.x (see `research-results/sprint-b5-b7-2026-11-06/B5_terrain_sources.json` → `software`).

**Commands (artifacts under ignored `research-results/sprint-b5-b7-2026-11-06/`):**

```sh
docker compose --profile hub build singleuser-image

docker run --rm \
  -v "$PWD:/repo:ro" -v "$PWD/research-results:/out" lunar-navigator-singleuser:latest \
  python3 /repo/research/scripts/audit_product90_sources.py \
    --data-root /repo/data --output /out/sprint-b5-b7-2026-11-06/B5_terrain_sources.json

docker run --rm \
  -v "$PWD:/repo:ro" -v "$PWD/research-results:/out" lunar-navigator-singleuser:latest \
  python3 /repo/research/scripts/product90_ray_coverage_diagnostic.py \
    --site04 /repo/data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif \
    --dem /repo/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF \
    --min-range-m 5000 --max-range-m 100000 \
    --output /out/sprint-b5-b7-2026-11-06/product90_ray_cov_80m_5k_100k.json

docker run --rm \
  -v "$PWD:/repo:ro" -v "$PWD/research-results:/out" lunar-navigator-singleuser:latest \
  python3 /repo/research/scripts/product90_ray_coverage_diagnostic.py \
    --site04 /repo/data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif \
    --dem /repo/data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF \
    --min-range-m 100000 --max-range-m 450000 \
    --output /out/sprint-b5-b7-2026-11-06/product90_ray_cov_240m_100k_450k.json

docker run --rm \
  -v "$PWD:/repo:ro" -v "$PWD/research-results:/out" lunar-navigator-singleuser:latest \
  python3 /repo/research/scripts/site04_multiband_horizon_farfield.py \
    --data-root /repo/data --outer-cap-m 450000 \
    --output-dir /out/sprint-b5-b7-2026-11-06/multiband_horizon \
    --repo-commit "$(git rev-parse HEAD)"
```

**Measured highlights (diagnostic only):**

- Product 90 native-grid coverage (720 bins, annulus per script): 80 m band 5000–100000 m — 720/720 bins with samples; global max of per-bin `largest_radial_gap_m` ≈ **3362 m** (largest inner gap before first sample on bin 313). 240 m band 100000–450000 m — 720/720 bins; global max largest gap ≈ **339 m** (native posting-limited).
- Multiband horizon script runtime ~ **1 min** on this host; manifest `b5_verdict: blocked`, `science_calculations_ready: false`. The reported **seam_*** summaries are **adjacent annulus horizon contrasts** (max horizon in one non-overlapping range vs max in the next) — **boundary** contrast, not co-located overlap seam validation. Example degree stats where both finite: 5 km **boundary** median ≈ **0.39°**, p95 ≈ **1.39°**, max |diff| ≈ **1.98°**; 100 km **boundary** median ≈ **0.049°**, p95 ≈ **1.13°**, max |diff| ≈ **1.61°** — **no acceptance threshold** applied; B5 remains blocked.
- `GET /v1/benchmark/status` — SQLite round-trip latency only; **not** a science result (see `backend/routers/calc.py`).

**B6:** Product 69 raster not on local `data/` — see `research/B6_PRODUCT69_BLOCKER.md`.

## Sprint evidence — 2026-11-06 (bin 313 corridor, overlap dZ, B7)

**Branch:** `sprint/b5-b7-evidence` (not merged). **Artifacts:** ignored `research-results/sprint-b5-b7-evidence-2026-11-06/`.

| Script / file | Purpose |
|----------------|---------|
| `research/scripts/product90_ray_corridor_diagnostic.py` | Fixed-step probe along **bin-centre** ray; per pixel-centre applies **`assign_ray_bins`** (same gates as coverage diagnostic). CSV + JSON list assigned bin, mask, raw float. |
| `research/scripts/b5_overlap_elevation_diagnostic.py` | Co-located **(B − A)** elevation on native grid of B after **average** resample A→B; CRS op strings recorded (**Ballpark** on Site04→80 m pair in this run — diagnostic only). |
| `research/scripts/collect_b7_api_benchmark.sh` | `curl` timing for `/health` and `/v1/benchmark/status` (client round-trip; see JSON `interpretation`). |

**Bin 313 / 80 m:** Corridor JSON reports `first_valid_assigned_along_m` ≈ **8362.5 m** and inner gap ≈ **3362.5 m** (matches `product90_ray_cov_80m_5k_100k.json` radial continuity). Along the centre line, nearest pixel centres often **assign to bin 312** (`status: assigned_to_bin_312_not_313`) until distance grows — consistent with **discrete 0.5° bins and 80 m posting**, not a transform bug.

**Co-located overlap (this workspace):** Site04→80 m window: **40000** common valid cells; median **(80 m − aggregated Site04) ≈ 0.18 m**; transform description includes **Ballpark**. 80 m→240 m: **6416089** cells; median residual **0 m**; max |residual| in top list **≈ 18 m** — still **not** seam acceptance; no threshold applied.

**B7:** Example `b7_api_benchmark.json`: 25× `curl` to loopback — if `/v1/benchmark/status` returns **404**, deploy API at commit that includes that route (squash merge #20 on `main`); `sqlite_ping_ms` is authoritative when the route exists.

**Owner checklist:** `research/B5_OWNER_REVIEW_CHECKLIST.md`.

## Reporting template

For each metric, report:

- Metric and formula
- Number of cases and case selection
- Reference source/version
- Input coordinates, time system, and frame
- Terrain and sampling assumptions
- Result with units
- Limitations and interpretation
- Whether the result is measured, inferred, or synthetic