#!/usr/bin/env python3
"""720-ray (0.5°) valid-pixel coverage and radial-continuity diagnostics on a Product 90 DEM.

Diagnostic only: matches notebook 05 map-plane ray assignment logic (observer basis
from notebook 03 / 05) but uses each raster's CRS and pixel centres. Per-bin metrics
include sample counts and largest radial gaps (including inner annulus gap before the
first sample and outer gap after the last). Does not verify MOON_ME frame tie, vertical
datum, or terrain horizons. Does not unblock B5 — no pass/fail threshold is applied.

Example::

  python research/scripts/product90_ray_coverage_diagnostic.py \\
    --site04 /path/to/Site04_final_adj_5mpp_surf.tif \\
    --dem /path/to/LDEM_80S_80MPP_ADJ.TIF \\
    --min-range-m 5000 --max-range-m 100000 \\
    --output /tmp/cov_80.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer

# Same fixed point as audit / notebook 05
POINT_ID = "S04-P02"
OBSERVER_XY_SITE04_M = (-2652.5, -6082.5)
REFERENCE_RADIUS_M = 1_737_400.0
AZIMUTH_STEP_DEG = 0.5
DEFAULT_RAY_STEP_M = 2.5  # notebook 05; scaled by pixel for cross-track below
MAP_TANGENT_STEP_M = 1.0


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


def lonlat_xyz_km(lon_deg: float, lat_deg: float, z_m: float) -> np.ndarray:
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    r = (REFERENCE_RADIUS_M + z_m) / 1000.0
    return np.array(
        [r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)],
        dtype=np.float64,
    )


def xyz_km_to_lonlat_deg(xyz_km: np.ndarray) -> tuple[float, float]:
    xyz = np.asarray(xyz_km, dtype=float)
    r = float(np.linalg.norm(xyz))
    lat = math.degrees(math.asin(xyz[2] / r))
    lon = math.degrees(math.atan2(xyz[1], xyz[0]))
    return lon, lat


def map_offset_from_tangent_km(
    obs_km: np.ndarray,
    tangent_unit_km: np.ndarray,
    fwd: Transformer,
    ox: float,
    oy: float,
    step_m: float = MAP_TANGENT_STEP_M,
) -> tuple[float, float]:
    lon, lat = xyz_km_to_lonlat_deg(obs_km + tangent_unit_km * (step_m / 1000.0))
    x, y = fwd.transform(lon, lat)
    return float(x - ox), float(y - oy)


def assign_ray_bins(
    map_az: np.ndarray,
    vx: np.ndarray,
    vy: np.ndarray,
    *,
    n_bins: int,
    az_centres: np.ndarray,
    ray_dx: np.ndarray,
    ray_dy: np.ndarray,
    min_range_m: float,
    max_range_m: float,
    cross_track_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (chosen_bin, ok, along_m_at_pick) for each row."""
    az_half = AZIMUTH_STEP_DEG / 2.0
    center = np.rint(map_az / AZIMUTH_STEP_DEG).astype(np.int64) % n_bins
    offsets = np.array([-1, 0, 1], dtype=np.int64)
    candidates = (center[:, None] + offsets[None, :]) % n_bins
    rdx = ray_dx[candidates]
    rdy = ray_dy[candidates]
    along = vx[:, None] * rdx + vy[:, None] * rdy
    cross = np.abs(vx[:, None] * (-rdy) + vy[:, None] * rdx)
    az_c = az_centres[candidates]
    az_diff = np.abs((map_az[:, None] - az_c + 180.0) % 360.0 - 180.0)
    valid = (
        (along >= min_range_m)
        & (along <= max_range_m)
        & (cross <= cross_track_m)
        & (az_diff <= az_half)
    )
    cross_score = np.where(valid, cross, np.inf)
    pick = np.argmin(cross_score, axis=1)
    row_idx = np.arange(vx.shape[0], dtype=np.int64)
    chosen = candidates[row_idx, pick]
    ok = np.isfinite(cross_score[row_idx, pick])
    along_pick = along[row_idx, pick]
    return chosen, ok, along_pick


def radial_continuity_stats(
    radii_sorted: np.ndarray,
    *,
    min_ring_m: float,
    max_ring_m: float,
) -> dict[str, Any]:
    """Largest gap includes inner (min_ring to first sample) and outer (last to max_ring)."""
    if radii_sorted.size == 0:
        return {
            "sample_count": 0,
            "first_valid_radius_m": None,
            "last_valid_radius_m": None,
            "radial_span_m": None,
            "max_gap_between_samples_m": None,
            "gap_from_inner_ring_to_first_sample_m": None,
            "gap_from_last_sample_to_outer_ring_m": None,
            "largest_radial_gap_m": None,
        }
    first = float(radii_sorted[0])
    last = float(radii_sorted[-1])
    gap_inner = max(0.0, first - min_ring_m)
    gap_outer = max(0.0, max_ring_m - last)
    if radii_sorted.size >= 2:
        internal = np.diff(radii_sorted)
        max_internal = float(np.max(internal))
    else:
        max_internal = 0.0
    largest = max(gap_inner, gap_outer, max_internal)
    return {
        "sample_count": int(radii_sorted.size),
        "first_valid_radius_m": first,
        "last_valid_radius_m": last,
        "radial_span_m": last - first,
        "max_gap_between_samples_m": max_internal,
        "gap_from_inner_ring_to_first_sample_m": gap_inner,
        "gap_from_last_sample_to_outer_ring_m": gap_outer,
        "largest_radial_gap_m": largest,
    }


def run_coverage(
    site04_path: Path,
    dem_path: Path,
    min_range_m: float,
    max_range_m: float,
) -> dict[str, Any]:
    with rasterio.open(site04_path) as s04, rasterio.open(dem_path) as dem:
        if s04.crs is None or dem.crs is None:
            raise ValueError("Site04 or DEM missing CRS")
        site04_crs = CRS.from_wkt(s04.crs.to_wkt())
        dem_crs = CRS.from_wkt(dem.crs.to_wkt())
        geo = dem_crs.geodetic_crs
        if geo is None:
            raise ValueError("DEM has no geodetic CRS")
        inv_s04 = Transformer.from_crs(site04_crs, geo, always_xy=True)
        fwd_dem = Transformer.from_crs(geo, dem_crs, always_xy=True)

        x_m, y_m = OBSERVER_XY_SITE04_M
        lon0, lat0 = inv_s04.transform(x_m, y_m)
        srow, scol = s04.index(x_m, y_m)
        zblock = s04.read(1, masked=True)
        z0 = float(zblock[srow, scol])
        if not np.isfinite(z0) or np.ma.is_masked(zblock[srow, scol]):
            raise ValueError("Observer elevation invalid on Site04")

        ox, oy = fwd_dem.transform(lon0, lat0)

        bounds = dem.bounds
        corners = (
            (bounds.left, bounds.bottom),
            (bounds.left, bounds.top),
            (bounds.right, bounds.bottom),
            (bounds.right, bounds.top),
        )
        max_extent_m = max(math.hypot(cx - ox, cy - oy) for cx, cy in corners)
        max_range_eff = min(float(max_range_m), max_extent_m)
        min_range_eff = min(float(min_range_m), max_range_eff)

        obs = lonlat_xyz_km(lon0, lat0, z0)
        lonr, latr = math.radians(lon0), math.radians(lat0)
        east = np.array([-math.sin(lonr), math.cos(lonr), 0.0])
        north = np.array(
            [-math.sin(latr) * math.cos(lonr), -math.sin(latr) * math.sin(lonr), math.cos(latr)]
        )

        ex_m, ey_m = map_offset_from_tangent_km(obs, east, fwd_dem, ox, oy)
        nx_m, ny_m = map_offset_from_tangent_km(obs, north, fwd_dem, ox, oy)
        ex_m, ey_m = ex_m / math.hypot(ex_m, ey_m), ey_m / math.hypot(ex_m, ey_m)
        nx_m, ny_m = nx_m / math.hypot(nx_m, ny_m), ny_m / math.hypot(nx_m, ny_m)

        n_bins = int(round(360.0 / AZIMUTH_STEP_DEG))
        az_centres = np.arange(n_bins, dtype=np.float64) * AZIMUTH_STEP_DEG
        az_rad_centres = np.deg2rad(az_centres)
        ray_dx = np.sin(az_rad_centres) * ex_m + np.cos(az_rad_centres) * nx_m
        ray_dy = np.sin(az_rad_centres) * ey_m + np.cos(az_rad_centres) * ny_m
        ray_len = np.hypot(ray_dx, ray_dy)
        ray_dx, ray_dy = ray_dx / ray_len, ray_dy / ray_len

        transform = dem.transform
        width, height = dem.width, dem.height
        pixel_size_x = abs(float(transform.a))
        pixel_size_y = abs(float(transform.e))
        cross_track_m = max(DEFAULT_RAY_STEP_M, 0.5 * max(pixel_size_x, pixel_size_y))

        dem_data = dem.read(1, masked=True)
        mask_ok = ~np.ma.getmaskarray(dem_data) & np.isfinite(np.asarray(dem_data, dtype=np.float64))

        # Lists of (bin_id, along_ray_m) for radial continuity; same gates as before
        bin_ids: list[int] = []
        along_ms: list[float] = []
        count_per_bin = np.zeros(n_bins, dtype=np.int64)
        block = 256
        for row_start in range(0, height, block):
            row_stop = min(row_start + block, height)
            rg, cg = np.indices((row_stop - row_start, width))
            rg = rg + row_start
            xb = transform.c + transform.a * (cg + 0.5) + transform.b * (rg + 0.5)
            yb = transform.f + transform.d * (cg + 0.5) + transform.e * (rg + 0.5)
            zb = mask_ok[row_start:row_stop]
            dist = np.hypot(xb - ox, yb - oy)
            within = (dist >= min_range_eff) & (dist <= max_range_eff) & zb
            rb, cb = np.where(within)
            if not len(rb):
                continue
            rb = rb + row_start
            x = xb[rb - row_start, cb]
            y = yb[rb - row_start, cb]
            vx = x - ox
            vy = y - oy
            map_az = (np.degrees(np.arctan2(vx * ex_m + vy * ey_m, vx * nx_m + vy * ny_m)) % 360.0)
            bins, ok, along_pick = assign_ray_bins(
                map_az,
                vx,
                vy,
                n_bins=n_bins,
                az_centres=az_centres,
                ray_dx=ray_dx,
                ray_dy=ray_dy,
                min_range_m=min_range_eff,
                max_range_m=max_range_eff,
                cross_track_m=cross_track_m,
            )
            if not np.any(ok):
                continue
            bins = bins[ok]
            along_ok = along_pick[ok]
            for b, a in zip(bins.tolist(), along_ok.tolist()):
                bi = int(b)
                bin_ids.append(bi)
                along_ms.append(float(a))
                count_per_bin[bi] += 1

        gap_bins = [int(i) for i in np.where(count_per_bin == 0)[0]]
        gap_azimuths_deg = [float(i) * AZIMUTH_STEP_DEG for i in gap_bins]
        covered = int(np.sum(count_per_bin > 0))

        # Per-bin radial continuity (sorted radii along assigned ray direction)
        per_bin_continuity: list[dict[str, Any]] = []
        largest_gap_global = 0.0
        worst_bin_largest_gap: int | None = None
        if bin_ids:
            all_bins = np.array(bin_ids, dtype=np.int64)
            all_along = np.array(along_ms, dtype=np.float64)
            for b in range(n_bins):
                sel = all_along[all_bins == b]
                sel.sort()
                stats = radial_continuity_stats(sel, min_ring_m=min_range_eff, max_ring_m=max_range_eff)
                stats["bin_index"] = b
                stats["azimuth_centre_deg"] = float(b * AZIMUTH_STEP_DEG)
                per_bin_continuity.append(stats)
                lg = stats["largest_radial_gap_m"]
                if lg is not None and lg > largest_gap_global:
                    largest_gap_global = lg
                    worst_bin_largest_gap = b
        else:
            for b in range(n_bins):
                per_bin_continuity.append(
                    {
                        "bin_index": b,
                        "azimuth_centre_deg": float(b * AZIMUTH_STEP_DEG),
                        **radial_continuity_stats(
                            np.array([], dtype=np.float64),
                            min_ring_m=min_range_eff,
                            max_ring_m=max_range_eff,
                        ),
                    }
                )

        # Proximity to DEM bounds in map plane (pixel centres on outermost row/col)
        on_edge = np.zeros((height, width), dtype=bool)
        on_edge[0, :] = on_edge[-1, :] = on_edge[:, 0] = on_edge[:, -1] = True
        edge_valid_in_band = False
        for row_start in range(0, height, block):
            row_stop = min(row_start + block, height)
            rg, cg = np.indices((row_stop - row_start, width))
            rg = rg + row_start
            xb = transform.c + transform.a * (cg + 0.5) + transform.b * (rg + 0.5)
            yb = transform.f + transform.d * (cg + 0.5) + transform.e * (rg + 0.5)
            zb = mask_ok[row_start:row_stop]
            dist = np.hypot(xb - ox, yb - oy)
            within = (dist >= min_range_eff) & (dist <= max_range_eff) & zb
            ed = on_edge[row_start:row_stop]
            if np.any(within & ed):
                edge_valid_in_band = True
                break

        return {
            "diagnostic_type": "product90_native_grid_720_ray_pixel_coverage",
            "b5_verdict": "blocked",
            "no_threshold_applied": True,
            "interpretation": (
                "Counts valid pixel centres per 0.5° map-plane azimuth bin in the annulus and "
                "cross-track corridor (notebook 05 style). Per-bin radial gaps measure distance "
                "along the assigned ray between samples (inner/outer gaps are from ring edges "
                "to first/last sample). Full bins do not imply continuous valid terrain along "
                "each ray at native posting. Missing bins mean no qualifying samples. "
                "Not a frame tie, datum proof, horizon, or seam acceptance. Does not unblock B5."
            ),
            "point_id": POINT_ID,
            "observer_xy_site04_m": [OBSERVER_XY_SITE04_M[0], OBSERVER_XY_SITE04_M[1]],
            "observer_xy_dem_m": [ox, oy],
            "observer_lon_lat_z": {"lon_deg": float(lon0), "lat_deg": float(lat0), "z_m_site04": z0},
            "site04_path": str(site04_path),
            "dem_path": str(dem_path),
            "dem_bounds_m": {
                "left": bounds.left,
                "bottom": bounds.bottom,
                "right": bounds.right,
                "top": bounds.top,
            },
            "dem_shape_hw": [height, width],
            "pixel_size_m_xy": [pixel_size_x, pixel_size_y],
            "cross_track_m": cross_track_m,
            "min_range_m_requested": min_range_m,
            "max_range_m_requested": max_range_m,
            "min_range_m_effective": min_range_eff,
            "max_range_m_effective": max_range_eff,
            "max_extent_from_observer_m": max_extent_m,
            "azimuth_step_deg": AZIMUTH_STEP_DEG,
            "n_bins": n_bins,
            "bins_with_any_valid_sample": covered,
            "bins_without_valid_sample": len(gap_bins),
            "gap_bin_indices": gap_bins,
            "gap_azimuth_centres_deg": gap_azimuths_deg,
            "edge_touch_in_band": edge_valid_in_band,
            "edge_touch_note": (
                "True if any in-band valid pixel centre lies on the outermost row/column "
                "(possible raster edge / seam vicinity)."
            ),
            "sample_count_per_bin_max": int(np.max(count_per_bin)) if n_bins else 0,
            "sample_count_per_bin_min_nonzero": (
                int(np.min(count_per_bin[count_per_bin > 0])) if covered else None
            ),
            "radial_continuity_per_bin": per_bin_continuity,
            "worst_bin_index_by_largest_radial_gap": worst_bin_largest_gap,
            "worst_azimuth_centre_deg_by_largest_radial_gap": (
                float(worst_bin_largest_gap * AZIMUTH_STEP_DEG) if worst_bin_largest_gap is not None else None
            ),
            "global_max_largest_radial_gap_m": largest_gap_global if bin_ids else None,
        }


def _git_head() -> str | None:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            timeout=5,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--site04",
        type=Path,
        required=True,
        help="Path to Site04_final_adj_5mpp_surf.tif (for observer lon/lat/z).",
    )
    p.add_argument("--dem", type=Path, required=True, help="Product 90 GeoTIFF path.")
    p.add_argument("--min-range-m", type=float, required=True)
    p.add_argument("--max-range-m", type=float, required=True)
    p.add_argument(
        "--repo-commit",
        type=str,
        default=None,
        help="Optional git HEAD (host can pass `git rev-parse HEAD`; container may lack git).",
    )
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    head = _git_head() or args.repo_commit
    payload = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "run_environment": {
            "host_hint": "docker_singleuser_image",
            "git_commit": head,
        },
        "platform": platform.platform(),
        "python": sys.version,
        "rasterio": rasterio.__version__,
        **run_coverage(args.site04.expanduser(), args.dem.expanduser(), args.min_range_m, args.max_range_m),
    }
    args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
    out = args.output.expanduser()
    out.write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    print("Wrote:", out)
    cov = payload["bins_with_any_valid_sample"]
    gaps = payload["bins_without_valid_sample"]
    print(
        f"covered_bins={cov}/720 gap_bins={gaps} edge_touch_in_band={payload['edge_touch_in_band']} "
        f"global_max_largest_radial_gap_m={payload.get('global_max_largest_radial_gap_m')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
