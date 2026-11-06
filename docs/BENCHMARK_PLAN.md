# Benchmark Plan and Partial Results

This document defines evaluation methods and records the first Site04 run. Only B1–B4 have partial or reported results; B5–B7 remain open. The B4 entry below is a Hub-run result reported by the project owner; raw run files remain in the owner's persistent Jupyter home and are not committed here.

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
| B5: Terrain horizon | No result yet | Open |
| B6: Published illumination context | No result yet | Open |
| B7: Runtime/API | No result yet | Open |

Notebook 03 reports geometric centre angles at 2025-01-01T00:00Z of approximately Sun azimuth 318.6° / elevation +1.68° and Earth azimuth 152° / elevation −6.5°. They are not terrain-cleared. The B4 run reports the Site04 PCK ellipsoid radii [1737.4, 1737.4, 1737.4] km and approximately 0° between radial-sphere up and ellipsoid up at S04-P02.

Artifacts in the owner's persistent Hub home:

- `~/research-results/site04-spice-baseline/S04-P02_2025-01-01_hourly_geometric_angles.csv`
- `~/research-results/site04-spice-baseline/kernel_and_run_manifest.json`
- `~/research-results/site04-spice-baseline/S04-P02_azlcpo_crosscheck.csv`
- `~/research-results/site04-spice-baseline/B4_validation_manifest.json`

B4 validates the local angle conversion against NAIF's routine using the same DE421 ephemeris and kernels. It is not an independent ephemeris validation and does not establish terrain visibility. Keep `SCIENCE_CALCULATIONS_READY=false` while B5–B7 and review remain open.

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