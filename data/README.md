# Local data directory

Place downloaded mission products here for local processing. Keep the original archive names and record source URL, product identifier/version, coordinate reference frame, scale, and checksum in your research notes.

Large mission datasets are intentionally excluded from Git. The API receives `data/` read-only at `/app/data`; the legacy `research` Compose profile mounts it read-only at `/workspace/data`. Hub singleuser servers receive the host `HOST_DATA_PATH` read-only at `~/data` (`/home/jovyan/data`).

No challenge dataset has been validated or bundled yet.

## Suggested layout (optional)

Paths under `data/` are gitignored except this file and `data/.gitkeep`. Example:

| Product | Suggested path | Notes |
|---------|----------------|--------|
| Site04 (Product 78) | `LOLA_5mpp/Site04/` | e.g. `Site04_final_adj_5mpp_surf.tif` |
| Product 90 | `LOLA_20mpp/` | e.g. `LDEM_80S_80MPP_ADJ.TIF`, `LDEM_60S_240MPP_ADJ.TIF` |
| **Product 69** (B6) | `LOLA_product69/` (or PGDA naming you prefer) | Place **GeoTIFF(s)** and matching **PDS `.lbl`** (or equivalent label bundle) side by side; never commit. Run `research/scripts/b6_product69_comparison.py --product69-raster … --output-json …` to `research-results/` only. |

For Hub, set `HOST_DATA_PATH` in `.env` to the host directory that bind-mounts as `/home/jovyan/data` (see deployment docs).
