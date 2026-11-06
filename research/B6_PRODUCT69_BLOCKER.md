# B6 (Product 69) — current blocker

**Status:** Not executed in this repository run.

## Choose one layer before downloading

[Product 69](https://pgda.gsfc.nasa.gov/products/69) is a **collection** (e.g. average solar illumination, Earth visibility, permanent shadow, sky visibility). **Layers are not interchangeable** — pick the quantity that matches the benchmark question (e.g. long-term Earth-disc visibility vs long-term solar illumination fraction), then download **that** GeoTIFF and its **matching** PDS label.

## Earth-visibility candidate (65°S–90°S, 240 m) — documentation only

If B6 targets **average Earth visibility** at south polar **240 m** posting, the PGDA GeoTIFF and a corresponding PDS label are:

| Role | URL |
|------|-----|
| GeoTIFF | `https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_65S_240M_201608_EARTH.TIF` |
| PDS label (describes matching IMG product) | `https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/img/avgvisib_65s_240m_201608_earth.lbl` |

Suggested local paths (gitignored): `data/LOLA_product69/AVGVISIB_65S_240M_201608_EARTH.TIF` and `data/LOLA_product69/avgvisib_65s_240m_201608_earth.lbl` (see `data/README.md`).

**Label vs TIFF:** The label documents the **PDS IMG** (e.g. scale/offset for stored values, **1737.4 km** sphere, polar stereographic, ME/DE421 frame). The **converted GeoTIFF** may carry different embedded tags, NoData, and masks — **always** read both the label and **rasterio/GDAL** metadata after download. PGDA states that TIF scale/offsets are applied during conversion.

**Averaging interval:** The label may list `START_TIME` / `STOP_TIME` that do **not** alone define the published long-term averaging period; the [Product 69](https://pgda.gsfc.nasa.gov/products/69) page describes average maps over a **~18.6 year** lunar nutation cycle. Do not use Product 69 as an oracle for **2025 hourly** notebook outputs.

```bash
mkdir -p data/LOLA_product69

curl -fL --retry 3 \
  -o data/LOLA_product69/AVGVISIB_65S_240M_201608_EARTH.TIF \
  'https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_65S_240M_201608_EARTH.TIF'

curl -fL --retry 3 \
  -o data/LOLA_product69/avgvisib_65s_240m_201608_earth.lbl \
  'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/img/avgvisib_65s_240m_201608_earth.lbl'
```

**Why B6 can stay blocked:** Even with files present, **B6 remains blocked** until the label and TIFF are **reviewed** and a comparison definition at S04-P02 is shown compatible. Keep rasters and generated JSON under **`data/`** and **`research-results/`** (ignored); never commit them.

**Raster manifest (metadata only):** After download, run (from repo root, with deps e.g. Docker `lunar-navigator-singleuser`):

```bash
python research/scripts/b6_product69_comparison.py \
  --product69-raster data/LOLA_product69/AVGVISIB_65S_240M_201608_EARTH.TIF \
  --output-json research-results/B6_product69_manifest.json
```

This writes checksum, CRS, dtype, tags — **not** a validated comparison.

**What the owner must still supply**

1. Written choice of **which Product 69 layer** matches B6 (if not Earth visibility, cite the correct PGDA files and labels).
2. Label + TIFF review notes (quantity, units, NoData, mask, frame) and confirmation that S04-P02 lies in valid coverage at the chosen resolution.
3. Explicit statement that long-term averages are **not** used as oracle for date-specific hourly results.

**Repository rule:** `SCIENCE_CALCULATIONS_READY=false`; `/v1/compare` gated; demo stays **SYNTHETIC** until separate benchmark sign-off.
