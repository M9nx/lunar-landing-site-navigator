# B5 — owner review checklist (blocked until evidence is supplied)

**Repository state:** `full_B5_pass` and any “pass” flags for far-field terrain must remain **false**. `SCIENCE_CALCULATIONS_READY` stays **false**. This document does **not** apply numeric pass/fail thresholds; it lists **independent evidence** the benchmark owner must supply, file, or sign off on.

**Diagnostic reminder (bin 313):** Large **inner-ring gap** metrics in `product90_ray_coverage_diagnostic.py` mean **no sample assigned to that bin** in that radial interval under the script’s gates — combined with **bin 312** assignments on the bin-centre trace in `product90_ray_corridor_diagnostic.py`, this is an **assignment / posting** diagnostic, **not** by itself proof of a NoData wedge, **not** a coverage pass, and **not** a transform proof until frame tie is independently established.

---

## How to record evidence (for the owner)

Fill the tables below in a **separate, non-committed** run note under `research-results/` (ignored) or your team’s doc system. Link paths and checksums here only as plain text after the fact; **do not commit** large JSON or rasters.

| Field | Value |
|--------|--------|
| Review date (UTC) | _YYYY-MM-DD_ |
| Reviewer(s) | _names / roles_ |
| Git commit of scripts used | `git rev-parse HEAD` |
| Host / container | _e.g. Hub singleuser + `data/` mount_ |

---

## 1. Frame / body-fixed tie (MOON_ME / DE421)

| Item | Done | Evidence location / notes |
|------|------|---------------------------|
| Independent **control-point** or survey-grade tie between Product 78 / 90 rasters and reviewed DE421 `MOON_ME` (not only pyproj “Ballpark” or projection-parameter match) | [ ] | _paths to control coordinates, residuals, PROJ pipeline or authority codes_ |
| Documented **forward/inverse** operations with stated accuracy for stacking | [ ] | _PROJ JSON / WKT / ticket reference_ |
| Extent-wide spot checks (corners, edges) if claiming beyond S04-P02 | [ ] | _list of points, residuals_ |

**Supporting commands (Hub/local, read-only data):**

```text
python research/scripts/audit_product90_sources.py --data-root ./data --output ./research-results/.../B5_terrain_sources.json
python research/scripts/b5_overlap_elevation_diagnostic.py --site04 ... --dem-80 ... --dem-240 ... --output ./research-results/.../b5_overlap_elevation_co_located.json
```

Review JSON field `crs_transform_metadata.forward_operation_description`; if it contains **Ballpark**, treat residuals as **diagnostic only** until non-ballpark ops are documented.

---

## 2. Vertical convention / zero (adjusted LOLA heights)

| Item | Done | Evidence location / notes |
|------|------|---------------------------|
| PDS labels or PGDA metadata for **vertical zero** and scale/offset per COG | [ ] | _label file paths on data mount_ |
| Agreed rule: no **ad-hoc** vertical shift in tooling without written evidence | [ ] | _owner note_ |
| Whether co-located median dZ from overlap diagnostic is allowed for a **named purpose** or remains “diagnostic only” | [ ] | _decision + scope_ |

---

## 3. Coverage and continuity (native grid, 720×0.5°)

| Item | Done | Evidence location / notes |
|------|------|---------------------------|
| For each band (Site04 / 80 m / 240 m), owner policy on **inner-ring gaps** and **incomplete rays** (null vs partial vs composite) | [ ] | _policy text_ |
| Cited runs: `product90_ray_coverage_diagnostic.py` + optional `product90_ray_corridor_diagnostic.py` | [ ] | _paths under `research-results/`_ |

Scripts do **not** impose radial-gap thresholds; owner sets criteria after review.

---

## 4. Seam / overlap (distinct from adjacent-annulus horizon contrast)

| Item | Done | Evidence location / notes |
|------|------|---------------------------|
| Owner **tolerance** (if any) for **co-located** overlap elevation residuals — **separate** from adjacent-annulus horizon contrast in `site04_multiband_horizon_farfield.py` | [ ] | _numeric band if defined; “none yet” is valid_ |
| Ballpark transforms acknowledged as **non-verified tie** for overlap metrics | [ ] | _initial / yes_ |

---

## 5. Science readiness gate

| Item | Done | Evidence location / notes |
|------|------|---------------------------|
| Explicit sign-off before `SCIENCE_CALCULATIONS_READY=true` or user-facing “validated” far-field terrain | [ ] | _date, reviewer, conditions_ |

---

## Sign-off (owner only — do not pre-fill without authority)

- [ ] Frame tie evidence reviewed and accepted or rejected with reason  
- [ ] Vertical convention reviewed  
- [ ] Coverage / seam criteria documented  
- [ ] Decision on `SCIENCE_CALCULATIONS_READY` recorded elsewhere (`BENCHMARK_PLAN.md` or team record)

**Reviewer name / date:** __________________ / __________  

Until the items above are satisfied and recorded, **B5 far-field remains blocked** (`b5_verdict: blocked`).
