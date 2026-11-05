# Benchmark Plan — Proposed, Not Yet Measured

This document defines how the prototype could be evaluated. It contains no benchmark results yet.

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
| S04-01 | Shackleton rim; exact point pending ROI review | Pending | Pending | Pending | Sun/Earth azimuth and elevation | Not run |
| S23-01 | Malapert Massif; exact point pending ROI review | Pending | Pending | Pending | Sun/Earth azimuth and elevation | Not run |
| S04-AVG | Shackleton rim | Aggregate period compatible with reference | LOLA GDRVIS, if grid coverage and assumptions match | Product-defined | Average illumination/Earth visibility comparison | Not run |
| S23-AVG | Malapert Massif | Aggregate period compatible with reference | LOLA GDRVIS, if grid coverage and assumptions match | Product-defined | Average illumination/Earth visibility comparison | Not run |

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