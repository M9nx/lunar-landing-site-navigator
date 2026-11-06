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

**Label vs TIFF (scaling — do not double-apply):**

- The **PDS label** defines the **IMG** product: `SCALING_FACTOR = 0.00004`, `OFFSET = 0`, i.e. **physical value ≈ DN × 0.00004** for valid DN (see `AVERAGE_VISIBILITY = (DN * SCALING_FACTOR) + OFFSET` in the label). It also describes a **continuous** fraction in **[0, 1]** (“percentage of timesteps … Earth disc”), while the `IMAGE` object uses the word **“binary”** in one sentence — read together with the next lines: DN **0** → shadow (0), DN up to **25000** → scales to **1** (so it is **not** a literal single-bit mask; it is **INT16 digital numbers** encoding a fraction).
- **Empirical check on the PGDA GeoTIFF** (`rasterio` read): for `AVGVISIB_65S_240M_201608_EARTH.TIF`, valid pixels span **DN 0–25000** with `nodata = -32768` — i.e. the **TIF still holds the same DN range as the PDS description**, not pre-scaled floats. Before any analysis, **confirm on your copy** (histogram or min/max). If values are still DN, convert to physical fraction with **one** application of **× 0.00004**. If a future PGDA build ever ships **already scaled** floats, the owner must detect that and **not** multiply by `0.00004` again.
- **CRS / grid:** Compare label map projection block (sphere 1737.4 km, polar stereographic, scale m/pix) to GeoTIFF CRS/transform (see manifest in `research-results/…_manifest.json`). **Coverage:** label lists latitude limits (e.g. maximum latitude −55.2° in the file we used) — confirm **S04-P02** lies in valid grid and unmasked area.

**Averaging interval:** The label may list `START_TIME` / `STOP_TIME` that do **not** alone define the published long-term averaging period; the [Product 69](https://pgda.gsfc.nasa.gov/products/69) page describes average maps over a **~18.6 year** lunar nutation cycle. Do not use Product 69 as an oracle for **2025 hourly** notebook outputs.

## Owner review checklist (before any B6 comparison)

Record answers in team notes or `research-results/` (ignored); do not commit large outputs.

| Step | Owner action |
|------|----------------|
| 1. Metric | Confirm **average Earth-disc visibility** (this layer) is the intended B6 quantity vs solar / PSS / sky. |
| 2. PDS wording | Resolve apparent conflict: read **DESCRIPTION** + **IMAGE.DESCRIPTION** + scaling lines — quantity is **fraction of timesteps with any Earth disc** (0–1), encoded as INT16 DN with **× 0.00004**. |
| 3. TIFF values | Run min/max/histogram on the downloaded TIF. If DN ∈ [0, 25000] and nodata −32768, physical **visibility_fraction ≈ DN × 4×10⁻⁵** (one application only). |
| 4. NoData / mask | Treat −32768 (and any additional mask band) per GDAL; document in the run note. |
| 5. Frame | Confirm CRS matches expected Moon polar stereographic / ME frame for comparison with Site04/Product 90 tooling. |
| 6. S04-P02 | Map point to row/col; verify valid pixel and record DN + converted fraction. |
| 7. Comparison definition | Write down what is being compared (e.g. reference long-term fraction vs model long-term aggregate only — **not** 2025 hourly). |

After the checklist is complete, implement sampling/compare in a script or notebook and write results to **`research-results/`** only. **`b6_status`** stays **`manifest_only…`** or a new blocked state until owner signs off.

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
