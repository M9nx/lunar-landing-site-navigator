# Lunar Geometry: Frame Mapping and Validation Plan

**Research date:** 2026-11-06  
**Status:** Source-level frame mapping established; Site04 geometric baseline and B4 pass reported; B1–B3 sign-off and B5–B7 remain pending.  
**Scope:** Site04 (Shackleton) LOLA DEM, lunar frame handling, and a reproducible first benchmark for Sun/Earth direction and local visibility.

## Executive decision

NASA PGDA identifies the Site04/Site23 south-polar stereographic GeoTIFF X/Y coordinates as metres in the **MOON_ME reference frame of DE421**. The archive therefore gives us an authoritative frame label for the raster coordinates. The earlier uncertainty about whether the published map was associated with MOON_ME is resolved at the product-description level.

The Site04 notebook run reports a sub-micrometre projection round trip and B4 agreement with NAIF `azlcpo` for six fixed cases. These are point- and epoch-specific checks, not validation of extent-wide coordinate behavior, ephemeris truth, local terrain normals, horizon masking, or final visibility windows. See `docs/BENCHMARK_PLAN.md` for the reported results. Keep `SCIENCE_CALCULATIONS_READY=false` while B5–B7 and benchmark-owner review remain open.

## Evidence and interpretation

1. PGDA Product 78 describes the raster products as 5 m/pixel GeoTIFFs with south-polar stereographic X/Y coordinates in metres, in MOON_ME for ephemeris DE421. It names Site04 as Shackleton rim and Site23 as Malapert massif.  
   Source: https://pgda.gsfc.nasa.gov/products/78

2. The local Site04 audit found a 3200 × 3200 grid, 5 m pixels, sphere radius 1,737,400 m, and projected bounds X=[−9000, 7000], Y=[−15000, 1000] m. The source GMT history uses pixel registration (`-r`, `node_offset=1`); GDAL reports `AREA_OR_POINT=Area`. The audit found no evidence supporting an additional half-pixel shift. Retain native pixel-centre sampling and record the exact affine transform used.  
   Local evidence: `research/notebooks/01_site04_data_audit.ipynb` and `research/notebooks/02_site04_registration_and_point_selection.ipynb`.

3. NAIF documents that the lunar FK defines the MOON_ME frame tied to a particular JPL ephemeris; for the DE421 frame set, the relevant binary lunar orientation PCK is `moon_pa_de421_1900-2050.bpc` and the lunar FK is `moon_080317.tf`. NAIF says the generic names `MOON_ME` and `MOON_PA` alias the ephemeris-specific frames. Use the frame name explicitly in the calculation and save the loaded kernel manifest with every run.  
   Sources:  
   - https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/pdf/individual_docs/23_lunar-earth_pck-fk.pdf  
   - https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/  
   - https://naif.jpl.nasa.gov/pub/naif/pds/wgc/kernels/fk/

4. The SPICE `azlcpo_c` routine supports azimuth/elevation from a constant observer position and an ellipsoid-derived surface normal. That is a useful independent implementation cross-check for ellipsoidal geometry, but it does **not** model the raster’s local terrain normal or terrain horizon. The notebook must not label its result as terrain-visible until the DEM-based occlusion stage has been added and checked.  
   Source: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html

5. PGDA notes that about 90% of the polar 5 m pixels are interpolated, and defines the total Z uncertainty product as RMS error. Do not describe DEM height RMS as a landing probability or a confidence interval. The audit’s selected LDEC>0 example is FID 2 at projected X=−2652.5 m, Y=−6082.5 m; Z=1736.902 m, total Z RMS=0.169 m, slope=3.29°, LDEC=2. It is a reproducible sample point, not a named or endorsed landing site.  
   Source: https://pgda.gsfc.nasa.gov/products/78  
   Local evidence: `research/notebooks/02_site04_registration_and_point_selection.ipynb`.

## Coordinate and frame pipeline to implement

Use one explicit chain and preserve units and frame names at each boundary:

1. **Select a DEM pixel centre.** Read its centre X/Y from the raster affine transform. Sample elevation Z and uncertainty at the same row/column. Reject NoData and record LDEC; distinguish measured returns (`LDEC>0`) from interpolated cells (`LDEC=0`).
2. **Invert the documented south-polar stereographic projection.** Use the exact raster CRS parameters and a tested geospatial library. Do not infer latitude/longitude from the axis labels alone. Save the CRS WKT, PROJ version, input X/Y, output coordinates, and a forward-projection round-trip residual.
3. **Establish the body-fixed point.** Convert the inverse projection’s lunar longitude/latitude and sampled height to a Cartesian point only after confirming the projection’s longitude convention, latitude type, sphere/ellipsoid assumptions, and that the resulting Cartesian axes are aligned with the product’s MOON_ME/DE421 frame. Do not add a PA↔ME rotation if the coordinates are already MOON_ME.
4. **Convert requested UTC to SPICE ET.** Load a NAIF leap-seconds kernel, parse UTC with SPICE, and store both input UTC and resulting ET/TDB. Reject times outside the coverage of all loaded kernels.
5. **Compute target vectors.** Use a documented SPICE call for Sun and Earth relative to the lunar observer at that epoch, with the selected aberration correction recorded (start with geometric `NONE` for a transparent baseline). Transform vectors into the same lunar body-fixed frame used by the point.
6. **Calculate geometric local angles.** Build a local frame from the DEM-derived surface normal and a documented north/east convention. Calculate azimuth/elevation from the observer-to-target vector. Separately compare the ellipsoid-normal case against NAIF `azlcpo_c`.
7. **Calculate terrain visibility as a separate layer.** Trace DEM elevations along the target azimuth to find the terrain horizon. For extended Sun/Earth disks, compute partial visibility only if the disk model and sampling method are implemented and benchmarked. Clearly distinguish “centre above local geometric horizon,” “terrain horizon clear,” and “fraction of apparent disk visible.”

### Kernel manifest for a reproducible DE421 baseline

Use NAIF-hosted kernels and record exact filenames, source URLs, download date, and SHA-256. The baseline set is expected to include:

- Planetary ephemeris SPK covering the requested epoch and Moon/Sun/Earth states (DE421 is the product’s stated ephemeris; verify the selected file’s coverage).
- A current NAIF LSK for UTC-to-ET conversion.
- `moon_pa_de421_1900-2050.bpc` and `moon_080317.tf` for high-accuracy DE421 lunar orientation and the ME frame.
- A text PCK supplying lunar radii and other body constants (record the exact file/version).

Use `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/` and the NAIF directory indexes above. Do not silently substitute a different DE ephemeris or lunar frame. If a newer ephemeris is evaluated, treat it as a separate configuration and quantify its effect against the DE421 product frame.

## Benchmark plan and pass/fail gates

These remain **proposed acceptance criteria**. Initial user-reported Site04 results are recorded in `docs/BENCHMARK_PLAN.md`; add exact outputs, software versions, inputs, and failure cases there as artifacts are reviewed.

| Gate | Test | Proposed acceptance criterion | What it proves |
|---|---|---|---|
| B1: Raster registration | Pixel-centre X/Y → pixel index → same centre, for corners and selected interior points | Maximum round-trip residual < 1e-6 m; no half-pixel offset | Affine and pixel-centre handling |
| B2: Projection | X/Y → lon/lat → X/Y for points across the Site04 extent | Maximum residual < 1e-3 m; document axis/longitude conventions | Projection implementation, not frame correctness by itself |
| B3: Frame identity | Load DE421 kernels; inspect frame IDs and transform a fixed vector between J2000 and MOON_ME at several epochs | No missing-frame errors; output changes smoothly; exact frame/kernel manifest saved | Correct kernel and frame wiring |
| B4: Ephemeris geometry | Compute geometric Sun/Earth az/el using both a vector-to-local-basis implementation and NAIF `azlcpo_c` with the same observer and ellipsoid normal | Absolute angular difference < 1e-6 degrees for the same target, epoch, observer, and correction | Independent angle conversion and API wiring; not independent ephemeris truth |
| B5: DEM horizon | Compare two separately implemented near-field horizon calculations on fixed clear, blocked, and grazing rays | Horizon elevation difference ≤ 0.1 degrees for the in-domain near-field rays; handle NoData and edge cases | Near-field masking only; a complete visibility horizon needs compatible far-field terrain |
| B6: Published illumination context | Compare only a matching Site04 ROI, height, date interval, and definition against the PGDA product’s published illumination result or supplied clones | Report absolute area/fraction difference and uncertainty; threshold set only after exact definitions/data are confirmed | End-to-end illumination sanity check, not a substitute for B1–B5 |
| B7: Runtime and API | Run a fixed 24-hour hourly series for the same two regions and capture p50/p95 latency, memory, and error responses | Target p95 < 2 seconds for cached, single-site series on the documented host; no silent synthetic fallback | Demo responsiveness and truthful failure behavior |

**B4 limitation:** B4 compares two angle conversions that share the same SPICE ephemeris and kernels. It can catch coordinate-frame, sign, azimuth, and local-basis mistakes, but it does not independently establish ephemeris accuracy.

**B5 coverage limitation:** The Site04 5 m raster is 16 × 16 km, so it can support a near-field horizon check but not the full far-field skyline. Barker et al. use a nested terrain grid for illumination: 5 m below 5 km, 80 m from 5–100 km, and 240 m at larger distances. Until compatible far-field terrain is acquired and aligned, label any horizon result as near-field-only. Reference: https://ntrs.nasa.gov/citations/20205009660

## Fixed benchmark cases

Use these deterministic cases before adding an API endpoint:

- **Point S04-P02:** Site04 valid ROI FID 2, selected LDEC>0 pixel centre (X=−2652.5 m, Y=−6082.5 m); store raster row/column from notebook 02 rather than reselecting dynamically.
- **Time series:** UTC every hour for 2025-01-01 00:00 through 2025-01-01 23:00, plus one fixed time near each geometric visibility transition discovered by the series. Record the transition-finding method.
- **Cross-region:** one valid, explicitly documented Site23 pixel centre using the same selection and provenance fields. Do not make the UI’s named “Malapert Massif” point appear authoritative until its precise coordinates and product source are recorded.
- **Edge cases:** NoData near raster boundary; `LDEC=0` interpolated pixel; low-elevation grazing target; target below terrain horizon; UTC conversion around a leap-second boundary (conversion test only, not a lunar visibility case).

The previously selected Site04 point can anchor testing, but it is not a validation truth value. Store outputs as benchmark results only after the gates are implemented.

## Work batch for the team

1. **Coordinate reviewer:** document the raster CRS WKT and independently confirm the inverse-projection axis and longitude conventions; add projection round-trip outputs.
2. **SPICE implementer:** create a notebook that loads the recorded DE421 kernels, converts UTC→ET, and computes Sun/Earth vectors and ellipsoid az/el at S04-P02. Save exact outputs and kernel checksums.
3. **Terrain implementer:** implement DEM local normal and azimuthal horizon profile as separate steps; test grazing and NoData cases.
4. **Benchmark owner:** fill B1–B7 with actual outputs, versions, and a short pass/fail interpretation. Do not invent a threshold after seeing results; if a proposed tolerance is impractical, justify and revise it before collecting final results.
5. **Integration owner:** only after review, replace the stub calculation endpoint and UI values with calculation outputs. Until then, keep the health flag false and the prototype’s synthetic label visible.

## Explicitly out of scope for this stage

- Ranking or recommending a landing site.
- Treating any Site04 ROI as an Artemis landing ellipse or a named landing zone.
- Calling a point “safe” from slope or height RMS alone.
- Claiming Earth communication availability from Earth-centre elevation alone; link geometry, antenna constraints, terrain, and mission communications assumptions need their own model.
- Enabling `SCIENCE_CALCULATIONS_READY` before all required benchmark results are reviewed.

## References

1. NASA GSFC PGDA, *High-Resolution LOLA Topography for Lunar South Pole Sites*, Product 78: https://pgda.gsfc.nasa.gov/products/78
2. NAIF, *High Accuracy Orientation and Body-fixed Frames for the Moon and Earth*: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/pdf/individual_docs/23_lunar-earth_pck-fk.pdf
3. NAIF CSPICE, `azlcpo_c` reference: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html
4. NAIF generic kernels: https://naif.jpl.nasa.gov/pub/naif/generic_kernels/
5. Barker et al., LOLA polar DEM and illumination uncertainty description, linked from PGDA Product 78.
6. Project audit notebooks: `research/notebooks/01_site04_data_audit.ipynb` and `research/notebooks/02_site04_registration_and_point_selection.ipynb`.
