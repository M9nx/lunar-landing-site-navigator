# Dataset intake checklist (human handoff)

**Status:** template for recording **official** or new datasets before wiring loaders or benchmarks. Mark fields **unverified** until evidence exists — do not invent metadata.

Use with **[ENGINE_CALCULATION_PIPELINE.md](ENGINE_CALCULATION_PIPELINE.md)** (stages) and **[METHOD_DECISION.md](METHOD_DECISION.md)** (approach). Research-only diagnostics (Product 78/90/69) remain separate from challenge validation unless explicitly benchmarked.

## Identification and provenance

| Field | Record | Loader / pipeline hook |
|--------|--------|-------------------------|
| Source agency / archive | | |
| Product / collection ID | | |
| Version or revision | | Version checks in audit scripts |
| Citation / DOI / PDS volume | | Documentation links in manifests |
| Checksum(s) per file | | Run manifest, integrity gates |
| Access date / retrieval URL | | |
| Files on disk (tree, naming) | | `data/` layout; **never commit rasters** |

## Space reference and CRS

| Field | Record | May need to adapt |
|--------|--------|---------------------|
| CRS WKT / EPSG | | pyproj / rasterio open; reprojection tests |
| Body-fixed frame name (e.g. MOON_ME) | | SPICE frame chain; benchmark B3/B4 |
| Ellipsoid / reference radius (m) | | Observer height, horizon math |
| Axis order (e.g. easting/northing, `always_xy`) | | All transforms |
| Pixel registration (`AREA_OR_POINT`) | | Sample at pixel centre vs corner |
| Vertical convention (surface height, datum) | | B5 overlap / vertical zero checks |

## Raster geometry and values

| Field | Record | May need to adapt |
|--------|--------|---------------------|
| Bounds / extent | | Coverage vs required rays |
| Resolution / posting | | Horizon sampling, nested bands |
| Units | | |
| Dtype | | Cast, overflow |
| Scale / offset (if any) | | Apply before physics |
| NoData value(s) | | Mask propagation |
| Internal / bitmask layers | | Parser for valid mask |
| Compression / COG | | GDAL options |

## Terrain vs time-dependent products

| Question | Terrain (DEM) | Illumination / visibility product |
|----------|----------------|-------------------------------------|
| Time varying? | No (static surface) | Often yes — record epoch span |
| Timestep / averaging period | N/A | Loader metadata; B6 compatibility |
| Target definition (disc / centre) | N/A | Must match comparison metric |
| Observer height / model | Implicit in DEM | Label-dependent |

For time-dependent files: record **epoch**, **timestep**, **averaging period**, and **observer / target definition**. Comparison is valid only when definitions align (see **[BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)** / **[FAR_FIELD_B5_B6_PLAN.md](FAR_FIELD_B5_B6_PLAN.md)**).

## Review

- Unknown fields stay **unverified** until filled from labels or independent checks.
- Practice datasets (78/90/69) are for **learning ingestion and diagnostics** — not automatic challenge validation.
