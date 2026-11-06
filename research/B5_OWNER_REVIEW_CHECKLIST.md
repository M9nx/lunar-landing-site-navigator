# B5 — owner review checklist (blocked until evidence is supplied)

**Repository state:** `full_B5_pass` and any “pass” flags for far-field terrain must remain **false**. `SCIENCE_CALCULATIONS_READY` stays **false**. This note does not apply acceptance thresholds; it lists **independent evidence** the benchmark owner must provide or sign off on.

## 1. Frame / body-fixed tie (MOON_ME / DE421)

- [ ] Independent **control-point** or survey-grade tie between Product 78 / 90 rasters and a reviewed DE421 `MOON_ME` definition (pyproj “Ballpark” or projection-parameter equality alone is **not** sufficient).
- [ ] Documented transformation operations (PROJ pipeline or authoritative EPSG/authority codes) with **non-ballpark** accuracy where claimed.
- [ ] Extent-wide spot checks (corners, edges) if “global” tie is asserted beyond S04-P02.

## 2. Vertical convention / zero (adjusted LOLA heights)

- [ ] PDS labels or PGDA metadata proving **vertical zero** and scaling for each COG used in production.
- [ ] Agreed interpretation of “adjusted” vs Site04 surface height **without** applying an ad-hoc elevation shift in tooling.
- [ ] Owner decision if co-located median dZ (diagnostic) is acceptable for a stated purpose, or remains “diagnostic only.”

## 3. Coverage and continuity (native grid, 720×0.5°)

- [ ] For each band, accept or reject **inner-ring gaps** (e.g. masked/NoData wedges) using `product90_ray_coverage_diagnostic.py` and optional `product90_ray_corridor_diagnostic.py` corridor traces.
- [ ] Policy for **incomplete rays** (null vs partial vs composite) in any delivered product — **no threshold** imposed by scripts; owner sets policy after review.

## 4. Seam / overlap (distinct from adjacent-annulus horizon contrast)

- [ ] Owner-defined **tolerance** (if any) for **co-located** overlap elevation residuals (`b5_overlap_elevation_diagnostic.py` or equivalent), separate from **adjacent-annulus** horizon contrast in `site04_multiband_horizon_farfield.py`.
- [ ] Acknowledgement that overlap residuals under **Ballpark** transforms are **diagnostic only**.

## 5. Science readiness gate

- [ ] Explicit benchmark-owner sign-off before `SCIENCE_CALCULATIONS_READY=true` or merge of any claim of “validated” far-field terrain to user-facing outputs.

Until the items above are satisfied and recorded, **B5 far-field remains blocked** (`b5_verdict: blocked`).
