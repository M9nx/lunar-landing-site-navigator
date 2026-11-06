#!/usr/bin/env python3
"""B6 diagnostic: sample S04-P02 on Product 69 Earth-visibility GeoTIFF (+ neighborhood).

Transforms fixed Site04 map X/Y (S04-P02 pixel centre) into the Product 69 raster CRS,
samples ``row, col``, reports **raw DN**, **fraction = DN × 0.00004** after masking
``nodata`` (typically -32768), and a small neighborhood summary (placement sensitivity).

**Does not** assert validation pass, B6 closure, or compatibility with notebook 03’s
2025 hourly geometry. Any model comparison must be definition-compatible long-term;
otherwise record mismatch only (diagnostic).

Outputs JSON (+ optional markdown run note) under ``--output-dir`` (use ignored
``research-results/``).

Example::

  python research/scripts/b6_sample_s04_p02_product69.py \\
    --site04 ./data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif \\
    --product69 ./data/LOLA_product69/AVGVISIB_65S_240M_201608_EARTH.TIF \\
    --output-dir ./research-results/b6-s04p02-product69-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window


POINT_ID = "S04-P02"
OBSERVER_XY_SITE04_M = (-2652.5, -6082.5)
B6_QUANTITY = "average_earth_disc_visibility_fraction_long_term"
DN_TO_FRACTION = 0.00004
DEFAULT_NODATA = -32768.0


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str | None:
    for key in ("SCRIPT_GIT_COMMIT", "GIT_COMMIT", "SOURCE_GIT_COMMIT"):
        env = os.environ.get(key)
        if env and env.strip():
            return env.strip()[:64]
    try:
        root = Path(__file__).resolve().parents[2]
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=5
        ).strip()
    except (OSError, subprocess.CalledProcessError, FileNotFoundError):
        return None


def site04_map_xy_to_lon_lat(
    row: int,
    col: int,
    *,
    transform: rasterio.transform.Affine,
    crs: CRS,
) -> tuple[float, float]:
    mx, my = rasterio.transform.xy(transform, row, col, offset="center")
    if crs.is_geographic:
        return float(mx), float(my)
    geo = crs.geodetic_crs
    lon, lat = Transformer.from_crs(crs, geo, always_xy=True).transform(mx, my)
    return float(lon), float(lat)


def crs_transform_metadata(crs_a: CRS, crs_b: CRS) -> dict[str, Any]:
    fwd = Transformer.from_crs(crs_a, crs_b, always_xy=True)
    inv = Transformer.from_crs(crs_b, crs_a, always_xy=True)
    return {
        "forward_axis_order": "always_xy (eastings/northings map metres)",
        "forward_site04_xy_to_product69_xy": getattr(fwd, "description", str(fwd)),
        "inverse_product69_xy_to_site04_xy": getattr(inv, "description", str(inv)),
        "forward_accuracy_m": getattr(fwd, "accuracy", None),
        "inverse_accuracy_m": getattr(inv, "accuracy", None),
        "note": (
            "If description mentions Ballpark, map coordinate tie is diagnostic only "
            "until owner-reviewed non-ballpark ops exist."
        ),
    }


def dn_to_fraction(dn: float | int, nodata: float | None) -> dict[str, Any]:
    d_try = float(dn)
    if math.isnan(d_try):
        return {
            "raw_dn": None,
            "valid": False,
            "earth_disc_visibility_fraction": None,
            "reason": "masked_or_nan",
        }
    if nodata is not None and d_try == float(nodata):
        return {
            "raw_dn": int(dn) if float(dn).is_integer() else float(dn),
            "valid": False,
            "earth_disc_visibility_fraction": None,
            "reason": "nodata",
        }
    d = d_try
    return {
        "raw_dn": int(d) if d.is_integer() else d,
        "valid": True,
        "earth_disc_visibility_fraction": d * DN_TO_FRACTION,
    }


def neighborhood_stats(arr: np.ndarray, nodata: float | None) -> dict[str, Any]:
    flat = arr.astype(np.float64).ravel()
    finite = np.isfinite(flat)
    if nodata is not None:
        m = finite & (flat != float(nodata))
    else:
        m = finite
    v = flat[m]
    if v.size == 0:
        return {"valid_cell_count": 0, "raw_dn": None, "fraction": None}
    fr = v * DN_TO_FRACTION
    return {
        "valid_cell_count": int(v.size),
        "raw_dn_min": float(np.min(v)),
        "raw_dn_max": float(np.max(v)),
        "raw_dn_median": float(np.median(v)),
        "fraction_min": float(np.min(fr)),
        "fraction_max": float(np.max(fr)),
        "fraction_median": float(np.median(fr)),
    }


def run_sample(
    site04_path: Path,
    product69_path: Path,
    *,
    neighborhood_radius: int,
) -> dict[str, Any]:
    with rasterio.open(site04_path) as s04, rasterio.open(product69_path) as p69:
        if s04.crs is None or p69.crs is None:
            raise ValueError("Site04 or Product 69 missing CRS")
        crs_s = CRS.from_wkt(s04.crs.to_wkt())
        crs_p = CRS.from_wkt(p69.crs.to_wkt())
        meta_tie = crs_transform_metadata(crs_s, crs_p)
        crs_payload = {
            "site04_crs_wkt": s04.crs.to_wkt(),
            "product69_crs_wkt": p69.crs.to_wkt(),
        }

        x0, y0 = OBSERVER_XY_SITE04_M
        # Document both fixed plan coordinates and pixel-centre georeferencing
        row_s, col_s = s04.index(x0, y0)
        lon0, lat0 = site04_map_xy_to_lon_lat(
            int(row_s), int(col_s), transform=s04.transform, crs=crs_s
        )
        px_p, py_p = Transformer.from_crs(crs_s, crs_p, always_xy=True).transform(
            x0, y0
        )
        row_p, col_p = p69.index(px_p, py_p)

        nd = p69.nodata if p69.nodata is not None else DEFAULT_NODATA

        h, w = p69.height, p69.width
        r0 = max(0, int(row_p) - neighborhood_radius)
        r1 = min(h, int(row_p) + neighborhood_radius + 1)
        c0 = max(0, int(col_p) - neighborhood_radius)
        c1 = min(w, int(col_p) + neighborhood_radius + 1)
        window = Window(c0, r0, c1 - c0, r1 - r0)
        block = p69.read(1, window=window, masked=True)
        # int16 masks cannot use np.nan as fill until promoted to float
        arr = np.ma.filled(block.astype(np.float64), np.nan)
        if nd is not None:
            arr_ma = np.where(arr == float(nd), np.nan, arr)
            # nodata may not be flagged on the raster mask; treat both as invalid
            arr_ma = np.where(~np.isfinite(arr_ma), np.nan, arr_ma)
        else:
            arr_ma = arr

        # Centre pixel relative to window
        cr = int(row_p) - r0
        cc = int(col_p) - c0
        centre_dn = float(arr[cr, cc])

        centre = dn_to_fraction(centre_dn, float(nd) if nd is not None else None)
        nh = neighborhood_stats(
            np.where(np.isnan(arr_ma), nd if nd is not None else np.nan, arr),
            float(nd) if nd is not None else None,
        )

        # Distances from centre to neighbors (map plane, Product 69)
        trans = p69.transform
        neigh: list[dict[str, Any]] = []
        for dr in range(-neighborhood_radius, neighborhood_radius + 1):
            for dc in range(-neighborhood_radius, neighborhood_radius + 1):
                ri, ci = int(row_p) + dr, int(col_p) + dc
                if ri < 0 or ci < 0 or ri >= h or ci >= w:
                    continue
                cx = trans.c + trans.a * (ci + 0.5) + trans.b * (ri + 0.5)
                cy = trans.f + trans.d * (ci + 0.5) + trans.e * (ri + 0.5)
                cell = p69.read(1, window=Window(ci, ri, 1, 1), masked=True)
                cell_arr = cell.astype(np.float64)
                if np.ma.is_masked(cell_arr) or bool(np.ma.getmaskarray(cell_arr)[0, 0]):
                    info = dn_to_fraction(float("nan"), float(nd) if nd is not None else None)
                else:
                    dnp = float(np.asarray(cell_arr)[0, 0])
                    info = dn_to_fraction(dnp, float(nd) if nd is not None else None)
                neigh.append(
                    {
                        "drow": dr,
                        "dcol": dc,
                        "row": ri,
                        "col": ci,
                        "map_x_m": cx,
                        "map_y_m": cy,
                        **info,
                    }
                )

        transform = p69.transform
        pcx = transform.c + transform.a * (col_p + 0.5) + transform.b * (row_p + 0.5)
        pcy = transform.f + transform.d * (col_p + 0.5) + transform.e * (row_p + 0.5)

        return {
            "diagnostic_type": "b6_s04_p02_product69_earth_visibility_sample",
            "b6_verdict": "blocked",
            "b6_interpretation": (
                "S04-P02 location sampled on Product 69 Earth-visibility GeoTIFF. "
                "Not a validation pass; no definition-compatible model long-term "
                "comparison is performed here. Notebook 03 2025 hourly results are out of scope."
            ),
            "b6_metric_intent": B6_QUANTITY,
            "scaling": {
                "dn_to_fraction": DN_TO_FRACTION,
                "nodata_value_used": float(nd) if nd is not None else None,
                "formula": "earth_disc_visibility_fraction = DN * 0.00004 (after nodata mask)",
            },
            "point_id": POINT_ID,
            "observer_site04_map_xy_m": [x0, y0],
            "site04_row_col_centre": [int(row_s), int(col_s)],
            "site04_lon_lat_deg_at_centre": [float(lon0), float(lat0)],
            **crs_payload,
            "site04_map_xy_to_product69_map_xy_pyproj": {
                "source_crs_role": "Site04 GeoTIFF projected CRS (S04-P02 map X/Y metres)",
                "target_crs_role": "Product 69 GeoTIFF projected CRS (map X/Y metres)",
                **meta_tie,
            },
            "product69_map_xy_m_observer": [float(px_p), float(py_p)],
            "product69_pixel_centre_map_xy_m": [float(pcx), float(pcy)],
            "product69_row_col": [int(row_p), int(col_p)],
            "centre_pixel": {**dn_to_fraction(centre_dn, float(nd) if nd is not None else None), "row": int(row_p), "col": int(col_p)},
            "neighborhood_radius_px": neighborhood_radius,
            "neighborhood_fraction_stats": nh,
            "neighborhood_cells": neigh,
            "product69_path": str(product69_path),
            "product69_sha256": sha256_file(product69_path),
            "site04_path": str(site04_path),
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site04", type=Path, required=True)
    p.add_argument("--product69", type=Path, required=True)
    p.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Ignored folder, e.g. research-results/b6-run",
    )
    p.add_argument("--neighborhood-radius", type=int, default=2)
    p.add_argument(
        "--reviewer",
        type=str,
        default="PENDING_OWNER_REVIEW",
        help="Owner reviewer id (for run note).",
    )
    p.add_argument(
        "--review-date-utc",
        type=str,
        default=None,
        help=(
            "ISO date YYYY-MM-DD when owner reviewed the run. "
            "Omit until review; default is pending (not run date — use run_utc)."
        ),
    )
    args = p.parse_args()

    script_path = Path(__file__).resolve()
    script_sha = sha256_file(script_path)

    site04 = args.site04.expanduser().resolve()
    product69 = args.product69.expanduser().resolve()
    if not site04.is_file() or not product69.is_file():
        print("Missing --site04 or --product69 file.", file=sys.stderr)
        return 2

    payload = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "script_git_commit": git_head(),
        "script_file_sha256": script_sha,
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "rasterio": rasterio.__version__,
        },
        "owner_review_fields": {
            "reviewer": args.reviewer,
            "review_date_utc": args.review_date_utc
            if args.review_date_utc is not None
            else "PENDING_OWNER_REVIEW",
            "b6_metric_confirmed": (
                "Set to true in a signed run note only after owner confirms "
                "average Earth-disc visibility is the intended B6 quantity."
            ),
        },
        **run_sample(site04, product69, neighborhood_radius=args.neighborhood_radius),
    }

    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "B6_S04-P02_product69_earth_visibility_sample.json"
    json_path.write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    print("Wrote:", json_path)

    md_path = out_dir / "B6_S04-P02_run_note.md"
    o = payload
    centre = o["centre_pixel"]
    md = f"""# B6 run note — S04-P02 × Product 69 (Earth visibility)

**Status:** diagnostic sample only — **not** a benchmark pass. `b6_verdict: blocked`.

| Field | Value |
|--------|--------|
| Run UTC | {o["run_utc"]} |
| Reviewer (fill) | {o["owner_review_fields"]["reviewer"]} |
| Review date (UTC) | {o["owner_review_fields"]["review_date_utc"]} |
| Script commit | `{o["script_git_commit"]}` |
| Script file SHA-256 | `{o["script_file_sha256"]}` |
| Host | `{o["host"]["platform"]}` |

## B6 metric

**Target:** {o["b6_metric_intent"]} (owner must confirm)

## Sources

| File | SHA-256 |
|------|---------|
| Product 69 | `{o["product69_sha256"]}` |

Paths: see JSON `product69_path`, `site04_path`.

## CRS / transform

See JSON `site04_crs_wkt`, `product69_crs_wkt`, and `site04_map_xy_to_product69_map_xy_pyproj` (check for Ballpark). Re-run with host `SCRIPT_GIT_COMMIT=$(git rev-parse HEAD)` if `script_git_commit` is null (e.g. minimal Docker image has no `git`). Set `--review-date-utc` only after owner review (otherwise `review_date_utc` stays pending).

## S04-P02 sample

| Item | Value |
|------|--------|
| Site04 map X/Y (m) | {o["observer_site04_map_xy_m"]} |
| Product 69 row, col | {o["product69_row_col"]} |
| Map XY centre (m) | {o["product69_pixel_centre_map_xy_m"]} |
| Raw DN (centre) | {centre.get("raw_dn")} |
| Valid | {centre.get("valid")} |
| Earth-disc visibility fraction | {centre.get("earth_disc_visibility_fraction")} |

Neighborhood (radius {o["neighborhood_radius_px"]} px): see JSON `neighborhood_fraction_stats` and `neighborhood_cells`.

## Comparison

No definition-compatible long-term model result was compared in this script. If a future comparison uses different epoch, terrain, or visibility definition, report **diagnostic only** and describe the mismatch (per `docs/FAR_FIELD_B5_B6_PLAN.md`, section B6).

## Gates

`SCIENCE_CALCULATIONS_READY=false`; `/v1/compare` gated; demo SYNTHETIC.
"""
    md_path.write_text(md)
    print("Wrote:", md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
