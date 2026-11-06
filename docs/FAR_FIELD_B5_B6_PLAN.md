# Far-field B5 and B6 Data Plan

**Status:** Product 90 80 m and 240 m COGs are mounted on the Hub host. A user-reported source preflight found the normalized projection method, numeric parameters, and ellipsoid axes match Site04, while full pyproj CRS equality remains false. Frame tie, elevation convention, 720-ray far-field coverage, and seams remain unverified. B5 near-field is reported passed; full B5, B6, B7, and the science readiness gate remain open.

**Purpose:** Give the benchmark owner a repeatable sequence to finish verifying the mounted Product 90 rasters against Site04, extend the terrain horizon without filling data gaps with assumed clear sky, and prepare a definition-compatible B6 comparison.

## 1. Candidate terrain files

NASA PGDA Product 90 lists both files as cloud-optimized GeoTIFFs (COGs) in south-polar stereographic X/Y metres and the MOON_ME frame of DE421. The associated Barker et al. paper reports the polar DEM products use the same projection/frame family and gives the map ranges below. These source-level descriptions make Product 90 a strong candidate; they do not replace local metadata and tie-point checks.

| Terrain band | Product 90 asset | Published pixel scale | Published coverage description | Approx. file size |
|---|---|---:|---|---:|
| Intermediate | `LDEM_80S_80MPP_ADJ.TIF` | 80 m/pixel | 80°S–90°S; stereographic range ±304 km | 181 MB |
| Far field | `LDEM_60S_240MPP_ADJ.TIF` | 240 m/pixel | 60°S–90°S; stereographic range ±931.2 km | 210 MB |

Sources:

- Product 90: https://pgda.gsfc.nasa.gov/products/90
- Barker et al. (2023), *A New View of the Lunar South Pole from LOLA*: https://ntrs.nasa.gov/citations/20230014419
- Product 78, Site04 5 m DEM: https://pgda.gsfc.nasa.gov/products/78

The proposed exclusive range bands follow the existing nested-scale plan: Product 78 Site04 5 m terrain from the observer to 5 km; Product 90 80 m terrain from 5 km to 100 km; Product 90 240 m terrain beyond 100 km to the actual validated edge of the raster. The 80 m raster is published to a wider radial extent than the 100 km band, and the 240 m raster overlaps the intermediate range. Use the overlap to evaluate seams; do not count both surfaces in the final horizon at once.

## 2. Put the files on the Hub data mount

Keep the files under the host's ignored data directory. With the default Compose paths:

```sh
mkdir -p data/LOLA_20mpp
curl --fail --location --retry 3 \
  https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF \
  -o data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF
curl --fail --location --retry 3 \
  https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF \
  -o data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF
sha256sum data/LOLA_20mpp/*.TIF
```

If production `HOST_DATA_PATH` points elsewhere, use that host path instead. Hub user servers mount this data directory read-only. Do not add the rasters to git. Record access date, byte size, SHA-256, and source URL in the run manifest.

## 3. Product compatibility audit — required before any raster stack

For Site04 and each Product 90 raster, record:

1. Driver, dimensions, dtype, pixel size, affine transform, bounds, NoData, compression/COG layout, `AREA_OR_POINT`, all metadata tags, and full CRS WKT.
2. Whether each CRS resolves to the same sphere radius (1,737,400 m), south-polar stereographic parameters, central meridian/axis convention, and geodetic coordinate interpretation as Product 78.
3. Forward/inverse round trips at S04-P02 and several shared coordinates, including the tile corners and both Product 90 coverage edges. Compare transformed coordinates and round-trip residuals; record the exact transformations and library versions.
4. Elevation convention and offsets. Product 78 and Product 90 describe LDEM values as surface height in metres. The PDS LOLA RDR label defines raw HEIGHT relative to a 1,737,400 m reference radius (scale 0.5, offset 1,737,400 m). Product 90's paper says the adjusted maps were built from LOLA RDR surface-height measurements, but that raw-data convention alone does not prove the exported adjusted COGs retained the identical zero. Verify the COG tags/labels and shared-area values; do not apply a vertical shift without evidence.
5. Actual valid-data coverage, including NoData holes, along all 720 test azimuths. The published latitude limits and nominal stereographic ranges are not proof that every required pixel is valid.

The Product 90 bin-count/radial-gap diagnostic records whether each 0.5° bin has pixel-centre samples and the largest sampled radial gaps. It is diagnostic only: it does not prove continuous valid terrain along every ray, compute a terrain horizon, or establish seam acceptance. No pass threshold is applied.

### Evidence checked and current interpretation

- NASA PGDA Product 78 identifies the Site04 GeoTIFFs as south-polar stereographic X/Y metres in MOON_ME/DE421; Product 90 gives the same frame/projection description for its COGs. Barker et al. (2023) likewise state that the LOLA polar products use a pole-centred stereographic projection in MOON_ME/DE421, and note a few-metre overall uncertainty of that frame relative to the principal-axis frame. These sources support the same product-level frame convention; they do not replace raster control-point checks or establish sub-metre absolute alignment.
- The owner-reported Hub preflight finds the projection method, numeric parameters, and ellipsoid axes match, while pyproj full CRS equality remains false. Treat that as a match in projection math, not as a completed body-fixed tie.
- The LOLA PDS RDR label documents the 1,737,400 m reference-radius convention for raw heights. Since the adjusted Product 90 GeoTIFFs are derived outputs, confirm their vertical zero from available product metadata and shared-area diagnostics before setting `vertical_convention_verified`. The 25 shared valid samples are useful diagnostics, not a datum proof.

Use these source-level findings to guide the remaining Hub checks: compare fixed map control points through both CRS definitions, document transformation/round-trip residuals and any coordinate displacement, then assess co-located elevations at a common effective resolution. Keep the frame-tie and vertical-datum flags false until the benchmark owner reviews the raster evidence.

Sources: [PGDA Product 78](https://pgda.gsfc.nasa.gov/products/78), [PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90), [Barker et al. (2023)](https://ntrs.nasa.gov/citations/20230014419), and [LOLA RDR SIS](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/rdrsis.htm).

**Compatibility verdict:** `compatible`, `compatible_with_documented_transform`, or `blocked`. Record evidence for the verdict in `B5_terrain_sources.json`; matching product descriptions alone are insufficient.

## 4. Far-field horizon design

For each terrain pixel centre used in a range band:

- Invert that raster's CRS to lunar longitude/latitude; use its own affine transform and pixel registration.
- Convert its spherical coordinates and DEM height to a MOON_ME Cartesian point using the verified 1,737,400 m reference sphere and the same DE421 body-fixed convention as the observer.
- Compute ground distance from S04-P02 on the reference sphere, local azimuth, and line-of-sight elevation in the documented observer basis.
- Assign the sample to exactly one primary range band: `[0, 5 km]`, `(5, 100 km]`, or `(100 km, validated outer limit]`. Preserve each band's coverage and sample counts by azimuth.
- For each azimuth bin, take the maximum terrain elevation over all valid points in that bin. Interpolate the resulting horizon only when its adjacent bins have complete coverage. Any missing required source samples make that ray incomplete.

Run seam diagnostics in common valid areas before selecting the final source by distance:

- 5 m vs 80 m around the 5 km boundary, using only directions with actual common valid coverage.
- 80 m vs 240 m around the 100 km boundary.
- Report per-ray maximum horizon differences and the elevation differences of common terrain samples. Report median, 95th percentile, and maximum; do not declare a seam acceptable until the benchmark owner sets and records a tolerance before reviewing the outcome.

Keep the 720 × 0.5° near-field ray IDs for continuity with notebook 05. Also perform a finer angular-sampling sensitivity run (for example 0.25°) to estimate whether narrow far-field terrain features are missed by the baseline bins. This is a convergence diagnostic, not a substitute for actual source coverage.

A full far-field B5 result requires: verified source compatibility; complete valid coverage to the chosen outer range for every reported ray; explicit NoData/edge flags; documented seam behavior; and a reviewed horizon/profile and hourly visibility table. For each hourly Sun/Earth centre direction, calculate `centre_ray_clear = (geometric_elevation_deg > terrain_horizon_deg_at_azimuth)`. Label the output centre-ray visibility. It is not finite-disc visibility, solar power, a radio link budget, or a landing safety score.

## 5. B6 published illumination comparison

NASA PGDA Product 69 provides LOLA polar illumination references. The south-polar products include average solar illumination and average Earth visibility at 240 m/pixel for 65°S–90°S and at 60 m/pixel for 85°S–90°S. The described averages span hourly samples over an approximately 18.6-year lunar nutation cycle. For Earth visibility, the product counts Earth as visible when any part of its disc is unobscured; this can be optimistic for a DSN-specific communications link.

Before comparing:

1. Read the PDS labels and document the stored value type, scale/offset, NoData, coordinate reference, observer height, time span, timestep, and target-disk/illumination definition.
2. Choose one comparison target supported by the labels: solar illumination fraction, Earth-disc visibility fraction, or both.
3. Compare the same georeferenced S04-P02 surface location against the corresponding Product 69 pixel. Record the pixel index and inspect a small neighborhood for sensitivity to spatial resolution and local placement.
4. Use a matching long-term epoch/timestep and the same geometric/terrain/height definition if available. If the published map's assumptions cannot be matched, report an informative comparison with the mismatch; do not call it a validation pass.
5. Report absolute difference in percentage points and the resolution/assumption limits.

Product 69 is a long-term average reference. It is **not** an oracle for notebook 03's 2025-01-01 hourly visibility windows. A selected-date B6 claim needs a date-matched independent reference or a second validated implementation.

- Product 69: https://pgda.gsfc.nasa.gov/products/69
- Mazarico et al. (2011): https://doi.org/10.1016/j.icarus.2010.10.030

## 6. Required outputs and gate state

Keep the raw files and generated run outputs in the ignored Hub data/results locations. Add no large raster or private run artifact to git.

Expected benchmark artifacts:

- `B5_terrain_sources.json`: source URLs, local paths, byte counts, SHA-256, metadata, overlap/coverage results, compatibility verdict.
- `S04-P02_horizon_profile_farfield.csv`: azimuth, horizon elevation, contributing range band, coverage flag, sample counts.
- `S04-P02_hourly_terrain_visibility_farfield.csv`: geometric angles, horizon at target azimuth, completeness, centre-ray clear/blocked/null.
- `B5_farfield_validation_manifest.json`: methods, frame, range boundaries, angular resolution, seam metrics, coverage counts, pass flag, explicit limitations.
- `B6_product69_comparison.json` and a small CSV: reference pixel, definitions, source metadata, modeled/reference fractions, percentage-point differences, compatibility notes.

The near-field B5 result remains reported as passed. Full B5, B6, and B7 remain open pending actual data audit, execution, and benchmark-owner review. Keep `SCIENCE_CALCULATIONS_READY=false`.

## Sprint record — 2026-11-06 (local workspace, not merged to `main`)

Repeatable commands and version stamps are in `docs/BENCHMARK_PLAN.md` § “Far-field B5 diagnostics and B7 API probe”.

**Artifacts (ignored `research-results/sprint-b5-b7-2026-11-06/`):**

| File | Role |
|------|------|
| `B5_terrain_sources.json` | Product 90 audit output (`compatibility_verdict: blocked`) |
| `product90_ray_cov_80m_5k_100k.json` | 80 m native-grid radial continuity / coverage |
| `product90_ray_cov_240m_100k_450k.json` | 240 m native-grid radial continuity / coverage |
| `multiband_horizon/S04-P02_horizon_profile_farfield.csv` | 720×0.5° per-band + composite (nanmax) horizons |
| `multiband_horizon/B5_farfield_validation_manifest.json` | Bands, seams, `full_B5_pass: false`, blockers |

**Blockers (unchanged):** independent MOON_ME/DE421 control-point proof for stacked rasters; Product 90 vertical zero vs Site04 not established from metadata alone; B6 needs Product 69 files + PDS label review (`research/B6_PRODUCT69_BLOCKER.md`).

**Interpretation note (80 m bin 313):** The radial-coverage JSON reports the first sample assigned to bin 313 at ≈ **8362 m** (an inner-boundary gap of ≈ **3362 m**) and 1146 assigned samples across the annulus. The corridor probe steps along the bin-centre ray and shows many queries mapping to valid pixel centres assigned to **bin 312** before bin 313 receives hits. With 0.5° bins, 80 m posting, and pixel-centre snapping, this gap is **not proof of a masked NoData stripe**; it is the first accepted sample for bin 313 under the current assignment rules. Treat it as a diagnostic, not a coverage pass or a confirmed raster hole; the owner must review the coverage criterion and frame tie.

**Composite horizons:** `research/scripts/site04_multiband_horizon_farfield.py` writes both `horizon_composite_nanmax_deg` (can hide missing-band wedges) and `horizon_composite_fail_closed_deg` (nan unless all three bands have ≥1 sample in the bin). The manifest `scope_limit` reminds that **per-bin counts still do not prove** continuous 80 m radial coverage — use the coverage diagnostic’s inner-gap fields for that.

**Boundary horizon contrast vs overlap seam:** Manifest `seam_annulus_summaries_deg` compares **horizon maxima** from **adjacent, non-overlapping** along-ray annuli (e.g. just inside vs just outside a nominal distance). That is **diagnostic boundary contrast** between distance bands; it does **not** measure elevation or horizon agreement at **co-located** map points in the geographic overlap between rasters. Treating it as an accepted stack seam requires separate overlap evidence (e.g. common valid pixels and owner-set tolerances). Full B5 remains blocked.

**Co-located overlap elevations (separate script):** `research/scripts/b5_overlap_elevation_diagnostic.py` writes `b5_overlap_elevation_co_located.json` — residual **B − A** on **B's** native grid where both layers are valid (**average** resample A→B). Record **PROJ operation descriptions** in JSON; **Ballpark** wording means diagnostic only, not verified tie. Example sprint path: `research-results/sprint-b5-b7-evidence-2026-11-06/b5_overlap_elevation_co_located.json`.

**Corridor trace (bin 313):** `research/scripts/product90_ray_corridor_diagnostic.py` steps along the **bin-centre** direction and applies the same **`assign_ray_bins`** gates as `product90_ray_coverage_diagnostic.py`. Example: `research-results/sprint-b5-b7-evidence-2026-11-06/bin313_corridor_80m_5k_9k.json` (+ `.csv`). Explains how discrete bins and pixel snapping relate to inner-ring gap.

**B5 owner review:** `research/B5_OWNER_REVIEW_CHECKLIST.md` (frame tie, vertical zero, coverage policy, overlap tolerances — **owner** must set any tolerance).
