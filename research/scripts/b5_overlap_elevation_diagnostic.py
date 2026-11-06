#!/usr/bin/env python3
"""Co-located native-grid elevation comparison on geographic overlap (diagnostic only).

**Site04 vs 80 m:** reproject Site04 to the 80 m Product 90 grid (average aggregate).
**80 m vs 240 m:** reproject 80 m to the 240 m grid (average aggregate).

Only pixels where **both** rasters have finite, unmasked values after resampling are used.
Reports residual stats (B minus A) and optional GeoJSON Point features for the largest |dZ|
samples (capped).

This is **not** a verified frame tie or seam acceptance: CRS transforms may use **Ballpark**
unless PROJ provides verified operations — see ``crs_pair`` in the output. Do not apply an
elevation shift. full_B5_pass remains false.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window, from_bounds, transform as window_transform


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def crs_pair_metadata(a: CRS, b: CRS) -> dict[str, Any]:
    fwd = Transformer.from_crs(a, b, always_xy=True)
    inv = Transformer.from_crs(b, a, always_xy=True)
    return {
        "site04_or_source_crs_projjson": a.to_json_dict() if a else None,
        "target_crs_projjson": b.to_json_dict() if b else None,
        "forward_operation_description": getattr(fwd, "description", str(fwd)),
        "inverse_operation_description": getattr(inv, "description", str(inv)),
        "forward_accuracy_m": getattr(fwd, "accuracy", None),
        "inverse_accuracy_m": getattr(inv, "accuracy", None),
        "ballpark_warning": (
            "If description mentions Ballpark, transform is not a verified raster tie "
            "(diagnostic residuals only)."
        ),
    }


def reproject_a_to_b_grid(
    path_a: Path,
    path_b: Path,
) -> tuple[np.ndarray, Any, Window, np.ndarray, Any]:
    """Return (values_a_on_b_grid, b_masked_array, window_on_b, diff_valid_mask, dst_transform)."""
    with rasterio.open(path_a) as ds_a, rasterio.open(path_b) as ds_b:
        if ds_a.crs is None or ds_b.crs is None:
            raise ValueError("Missing CRS")
        crs_a = CRS.from_wkt(ds_a.crs.to_wkt())
        crs_b = CRS.from_wkt(ds_b.crs.to_wkt())

        left_a, bottom_a, right_a, top_a = ds_a.bounds
        transformer = Transformer.from_crs(crs_a, crs_b, always_xy=True)
        corners = [
            (left_a, bottom_a),
            (left_a, top_a),
            (right_a, bottom_a),
            (right_a, top_a),
        ]
        mapped = [transformer.transform(x, y) for x, y in corners]
        left = min(x for x, _ in mapped)
        right = max(x for x, _ in mapped)
        bottom = min(y for _, y in mapped)
        top = max(y for _, y in mapped)

        window = from_bounds(left, bottom, right, top, transform=ds_b.transform)
        window = window.round_offsets().round_lengths().intersection(
            Window(0, 0, ds_b.width, ds_b.height)
        )
        h, w = int(window.height), int(window.width)
        if h <= 0 or w <= 0:
            raise ValueError("No overlap window on B grid")

        dst_transform = window_transform(window, ds_b.transform)
        src = ds_a.read(1, masked=True).astype("float32").filled(np.nan)

        dest_a = np.full((h, w), np.nan, dtype=np.float32)
        reproject(
            source=src,
            destination=dest_a,
            src_transform=ds_a.transform,
            src_crs=ds_a.crs,
            src_nodata=np.nan,
            dst_transform=dst_transform,
            dst_crs=ds_b.crs,
            dst_nodata=np.nan,
            resampling=Resampling.average,
            init_dest_nodata=True,
        )

        b_data = ds_b.read(1, window=window, masked=True).astype("float32")
        b_vals = np.asarray(b_data.filled(np.nan), dtype=np.float64)
        b_mask = np.ma.getmaskarray(b_data)

        valid_b = np.isfinite(b_vals) & ~b_mask
        valid_a = np.isfinite(dest_a) & (dest_a == dest_a)
        both = valid_a & valid_b

        return dest_a.astype(np.float64), b_data, window, both.astype(bool), dst_transform


def summarize_residuals(
    z_a: np.ndarray,
    z_b: np.ndarray,
    valid: np.ndarray,
    dst_transform: Any,
    window: Window,
    top_n: int,
) -> dict[str, Any]:
    diff = np.where(valid, z_b - z_a, np.nan)
    finite = diff[np.isfinite(diff)]
    if finite.size == 0:
        return {
            "common_valid_cell_count": 0,
            "residual_B_minus_A_m": None,
            "top_abs_residual_locations": [],
        }
    abs_d = np.abs(diff)
    flat_idx = np.argsort(-abs_d.ravel())[: min(top_n, int(np.sum(valid)))]
    rows, cols = np.unravel_index(flat_idx, diff.shape)
    top_list: list[dict[str, Any]] = []
    for ri, ci in zip(rows.tolist(), cols.tolist()):
        r_win, c_win = int(ri), int(ci)
        r_global = int(window.row_off + r_win)
        c_global = int(window.col_off + c_win)
        px = (
            dst_transform.c
            + dst_transform.a * (c_win + 0.5)
            + dst_transform.b * (r_win + 0.5)
        )
        py = (
            dst_transform.f
            + dst_transform.d * (c_win + 0.5)
            + dst_transform.e * (r_win + 0.5)
        )
        top_list.append(
            {
                "row_in_window": r_win,
                "col_in_window": c_win,
                "map_x_m": float(px),
                "map_y_m": float(py),
                "z_a_m": float(z_a[r_win, c_win]),
                "z_b_m": float(z_b[r_win, c_win]),
                "residual_B_minus_A_m": float(z_b[r_win, c_win] - z_a[r_win, c_win]),
            }
        )
    return {
        "common_valid_cell_count": int(np.sum(valid)),
        "residual_B_minus_A_m": {
            "min": float(np.min(finite)),
            "median": float(np.median(finite)),
            "max": float(np.max(finite)),
            "mean": float(np.mean(finite)),
        },
        "top_abs_residual_locations": top_list,
    }


def run_pair(
    path_a: Path,
    path_b: Path,
    *,
    name: str,
    top_n: int,
) -> dict[str, Any]:
    with rasterio.open(path_a) as ds_a, rasterio.open(path_b) as ds_b:
        crs_a = CRS.from_wkt(ds_a.crs.to_wkt())
        crs_b = CRS.from_wkt(ds_b.crs.to_wkt())
    pair_meta = crs_pair_metadata(crs_a, crs_b)
    z_a_on_b, b_masked, window, valid, dst_t = reproject_a_to_b_grid(path_a, path_b)
    z_b = np.asarray(b_masked.filled(np.nan), dtype=np.float64)

    stats = summarize_residuals(z_a_on_b, z_b, valid, dst_t, window, top_n)
    return {
        "pair_name": name,
        "path_a": str(path_a),
        "path_b": str(path_b),
        "resampling_a_to_b": "average",
        "grid": "native_pixels_of_B",
        "crs_transform_metadata": pair_meta,
        "interpretation": (
            "Elevations on B's pixel grid where both layers are valid after average resample "
            "of A onto B. Separate from adjacent-annulus horizon contrast. Not a verified tie."
        ),
        **stats,
    }


def git_head() -> str | None:
    try:
        root = Path(__file__).resolve().parents[2]
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=5
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site04", type=Path, required=True)
    p.add_argument("--dem-80", type=Path, required=True)
    p.add_argument("--dem-240", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--top-locations", type=int, default=15)
    p.add_argument("--repo-commit", type=str, default=None)
    args = p.parse_args()

    payload = {
        "diagnostic_type": "b5_overlap_elevation_native_grid_co_located",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "b5_verdict": "blocked",
        "full_B5_pass": False,
        "science_calculations_ready": False,
        "no_threshold_applied": True,
        "platform": platform.platform(),
        "python": sys.version,
        "rasterio": rasterio.__version__,
        "git_commit": args.repo_commit or git_head(),
        "pairs": [
            run_pair(
                args.site04.expanduser(),
                args.dem_80.expanduser(),
                name="site04_average_to_80m_grid_vs_80m_native",
                top_n=args.top_locations,
            ),
            run_pair(
                args.dem_80.expanduser(),
                args.dem_240.expanduser(),
                name="80m_average_to_240m_grid_vs_240m_native",
                top_n=args.top_locations,
            ),
        ],
    }

    args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
    args.output.expanduser().write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    print("Wrote:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
