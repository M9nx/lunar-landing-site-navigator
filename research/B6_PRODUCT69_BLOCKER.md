# B6 (Product 69) — current blocker

**Status:** Not executed in this repository run.

**Why:** NASA PGDA [Product 69](https://pgda.gsfc.nasa.gov/products/69) LOLA polar illumination / Earth-visibility reference rasters are **not** present under the local `data/` tree (only Product 78 Site04 and Product 90 COGs are mounted here). Download the product page’s **PDS-calibrated data** links (GeoTIFF and `.lbl` / PDS label) onto the **ignored** Hub `data/` mount when running Hub-side — never commit rasters. B6 requires reading the **PDS labels** for the chosen file (value type, scale/offset, NoData, grid definition, epoch averaging interval, and visibility rules) before any pixel comparison at S04-P02.

**Partial manifest (raster present, labels not reviewed):** Run `python research/scripts/b6_product69_comparison.py --product69-raster /path/to/file.tif --output-json /path/to/B6_product69_manifest.json` to record path, bytes, SHA-256, CRS WKT, dtype, shape, and embedded tags — still **not** a B6 comparison until label definitions are documented.

**What the owner must supply**

1. At least one Product 69 GeoTIFF (or the authoritative path on the Hub data mount) plus its PDS label or embedded metadata sufficient to document the stored quantity and units.
2. Confirmation of which band matches the benchmark intent (e.g. long-term average solar illumination fraction vs Earth-disc visibility fraction) and which resolution strip includes S04-P02.

**Script stub:** `research/scripts/b6_product69_comparison.py` exits with a reminder unless `--product69-raster` points at a file; it does not claim validation.

**Caveat (from plan):** Product 69 aggregates are over ~**18.6 years**; they must **not** be used as an oracle for **2025 hourly** notebook outputs.
