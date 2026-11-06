#!/usr/bin/env python3
"""Along-ray corridor probe on a native Product 90 grid: valid vs masked pixel centres.

For one azimuth bin (default 313 ≈ 156.5° centre), steps from ``--radius-start-m`` to
``--radius-end-m`` along the same map-plane unit ray used in ``product90_ray_coverage_diagnostic.py``.
At each step, samples the DEM at the **containing pixel** (``index`` + pixel-centre coordinates)
and records raw value, mask state, and distance from observer.

Use this to distinguish a **raster NoData wedge** (many consecutive masked steps) from a
transform/sampling bug. Does not unblock B5.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer

POINT_ID = "S04-P02"
OBSERVER_XY_SITE04_M = (-2652.5, -6082.5)
REFERENCE_RADIUS_M = 1_737_400.0
AZIMUTH_STEP_DEG = 0.5
DEFAULT_RAY_STEP_M = 2.5
MAP_TANGENT_STEP_M = 1.0


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
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
    """Same as product90_ray_coverage_diagnostic.assign_ray_bins."""
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


def run_probe(
    site04_path: Path,
    dem_path: Path,
    *,
    bin_index: int,
    radius_start_m: float,
    radius_end_m: float,
    step_m: float,
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
        annulus_requested = (radius_start_m, radius_end_m)
        min_range_eff = float(radius_start_m)
        max_range_eff = min(float(radius_end_m), max_extent_m)

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
        if not 0 <= bin_index < n_bins:
            raise ValueError(f"bin_index must be in [0, {n_bins - 1}]")
        az_centre_deg = float(bin_index) * AZIMUTH_STEP_DEG
        az_centres = np.arange(n_bins, dtype=np.float64) * AZIMUTH_STEP_DEG
        az_rad_centres = np.deg2rad(az_centres)
        ray_dx = np.sin(az_rad_centres) * ex_m + np.cos(az_rad_centres) * nx_m
        ray_dy = np.sin(az_rad_centres) * ey_m + np.cos(az_rad_centres) * ny_m
        ray_len = np.hypot(ray_dx, ray_dy)
        ray_dx, ray_dy = ray_dx / ray_len, ray_dy / ray_len
        rdx_centre = float(ray_dx[bin_index])
        rdy_centre = float(ray_dy[bin_index])

        transform = dem.transform
        pixel_size_x = abs(float(transform.a))
        pixel_size_y = abs(float(transform.e))
        cross_track_m = max(DEFAULT_RAY_STEP_M, 0.5 * max(pixel_size_x, pixel_size_y))

        data = dem.read(1, masked=True)
        nodata = dem.nodata
        profile = dem.profile

        samples: list[dict[str, Any]] = []
        r = float(radius_start_m)
        while r <= radius_end_m + 1e-6:
            px = ox + rdx_centre * r
            py = oy + rdy_centre * r
            try:
                row, col = dem.index(px, py)
            except Exception:
                samples.append(
                    {
                        "along_ray_m_query": r,
                        "along_ray_m_pixel_centre": None,
                        "map_x_query_m": px,
                        "map_y_query_m": py,
                        "status": "outside_raster_index",
                        "row": None,
                        "col": None,
                        "is_masked": None,
                        "raw_value_if_unmasked": None,
                        "dataset_nodata": float(nodata) if nodata is not None else None,
                    }
                )
                r += step_m
                continue
            if row < 0 or col < 0 or row >= dem.height or col >= dem.width:
                samples.append(
                    {
                        "along_ray_m_query": r,
                        "along_ray_m_pixel_centre": None,
                        "map_x_query_m": px,
                        "map_y_query_m": py,
                        "status": "outside_bounds",
                        "row": int(row),
                        "col": int(col),
                        "is_masked": None,
                        "raw_value_if_unmasked": None,
                        "dataset_nodata": float(nodata) if nodata is not None else None,
                    }
                )
                r += step_m
                continue
            cx = transform.c + transform.a * (col + 0.5) + transform.b * (row + 0.5)
            cy = transform.f + transform.d * (col + 0.5) + transform.e * (row + 0.5)
            dist_centre = math.hypot(cx - ox, cy - oy)
            val = data[row, col]
            is_masked = bool(np.ma.is_masked(val))
            raw_f = float(val) if not is_masked and np.isfinite(val) else None

            vx, vy = cx - ox, cy - oy
            map_az = (math.degrees(math.atan2(vx * ex_m + vy * ey_m, vx * nx_m + vy * ny_m)) % 360.0)

            bins, ok_b, along_m = assign_ray_bins(
                np.array([map_az], dtype=np.float64),
                np.array([vx], dtype=np.float64),
                np.array([vy], dtype=np.float64),
                n_bins=n_bins,
                az_centres=az_centres,
                ray_dx=ray_dx,
                ray_dy=ray_dy,
                min_range_m=min_range_eff,
                max_range_m=max_range_eff,
                cross_track_m=cross_track_m,
            )
            assigned_bin = int(bins[0]) if ok_b[0] else None
            along_assigned_m = float(along_m[0]) if ok_b[0] else None
            matches_target_bin = ok_b[0] and assigned_bin == bin_index

            abs_az_err = abs((map_az - az_centre_deg + 180.0) % 360.0 - 180.0)

            if is_masked:
                row_status = "masked"
            elif raw_f is None:
                row_status = "invalid_nonmasked"
            elif not ok_b[0]:
                row_status = "not_in_annulus_or_failed_ray_gate"
            elif not matches_target_bin:
                row_status = f"assigned_to_bin_{assigned_bin}_not_{bin_index}"
            else:
                row_status = "valid_assigned_to_target_bin"

            samples.append(
                {
                    "along_ray_m_query": r,
                    "along_ray_m_pixel_centre": dist_centre,
                    "along_m_for_assigned_bin": along_assigned_m,
                    "assigned_bin_index": assigned_bin,
                    "matches_target_bin": matches_target_bin,
                    "map_x_query_m": px,
                    "map_y_query_m": py,
                    "pixel_centre_x_m": cx,
                    "pixel_centre_y_m": cy,
                    "row": int(row),
                    "col": int(col),
                    "pixel_map_azimuth_deg": map_az,
                    "azimuth_err_vs_bin_centre_deg": float(abs_az_err),
                    "cross_track_m": float(abs(vx * (-rdy_centre) + vy * rdx_centre)),
                    "is_masked": is_masked,
                    "raw_value_if_unmasked": raw_f,
                    "dataset_nodata": float(nodata) if nodata is not None else None,
                    "status": row_status,
                }
            )
            r += step_m

        first_valid_along: float | None = None
        for s in samples:
            if s.get("status") == "valid_assigned_to_target_bin" and s.get("raw_value_if_unmasked") is not None:
                first_valid_along = float(s["along_m_for_assigned_bin"])
                break

        inner_ring = min_range_eff
        gap_inner = (
            (first_valid_along - inner_ring)
            if first_valid_along is not None
            else None
        )

        return {
            "diagnostic_type": "native_grid_ray_corridor_pixel_sample",
            "b5_verdict": "blocked",
            "interpretation": (
                "Fixed-step query points along the bin-centre direction; each sample uses the "
                "containing pixel centre, then the same assign_ray_bins gating as "
                "product90_ray_coverage_diagnostic (annulus, cross-track, azimuth to bin). "
                "First 'valid_assigned_to_target_bin' matches radial continuity first-sample "
                "semantics for that bin."
            ),
            "point_id": POINT_ID,
            "bin_index": bin_index,
            "azimuth_centre_deg": az_centre_deg,
            "dem_path": str(dem_path),
            "observer_xy_dem_m": [ox, oy],
            "cross_track_m": cross_track_m,
            "annulus_effective_m": {"min": min_range_eff, "max": max_range_eff},
            "annulus_requested_m": {"start": annulus_requested[0], "end": annulus_requested[1]},
            "max_extent_from_observer_m": max_extent_m,
            "step_m": step_m,
            "radius_range_m": {"start": radius_start_m, "end": radius_end_m},
            "bin_centre_ray_unit_map_xy": [rdx_centre, rdy_centre],
            "raster_nodata_value": nodata,
            "raster_dtype": str(profile.get("dtype", "")),
            "first_valid_assigned_along_m": first_valid_along,
            "gap_from_inner_ring_to_first_assigned_valid_m": gap_inner,
            "samples": samples,
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site04", type=Path, required=True)
    p.add_argument("--dem", type=Path, required=True)
    p.add_argument("--bin-index", type=int, default=313)
    p.add_argument("--radius-start-m", type=float, default=5000.0)
    p.add_argument("--radius-end-m", type=float, default=9000.0)
    p.add_argument("--step-m", type=float, default=20.0)
    p.add_argument("--output-json", type=Path, required=True)
    p.add_argument("--output-csv", type=Path, default=None)
    args = p.parse_args()

    payload = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "rasterio": rasterio.__version__,
        **run_probe(
            args.site04.expanduser(),
            args.dem.expanduser(),
            bin_index=args.bin_index,
            radius_start_m=args.radius_start_m,
            radius_end_m=args.radius_end_m,
            step_m=args.step_m,
        ),
    }

    outj = args.output_json.expanduser()
    outj.parent.mkdir(parents=True, exist_ok=True)
    outj.write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    print("Wrote:", outj)

    if args.output_csv:
        csv_path = args.output_csv.expanduser()
        with csv_path.open("w", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(
                [
                    "along_ray_m_query",
                    "along_ray_m_pixel_centre",
                    "assigned_bin_index",
                    "along_m_for_assigned_bin",
                    "row",
                    "col",
                    "is_masked",
                    "raw_value",
                    "dataset_nodata",
                    "status",
                ]
            )
            for s in payload["samples"]:
                w.writerow(
                    [
                        s.get("along_ray_m_query", ""),
                        s.get("along_ray_m_pixel_centre", ""),
                        s.get("assigned_bin_index", ""),
                        s.get("along_m_for_assigned_bin", ""),
                        s.get("row", ""),
                        s.get("col", ""),
                        s.get("is_masked", ""),
                        s.get("raw_value_if_unmasked", ""),
                        s.get("dataset_nodata", ""),
                        s.get("status", ""),
                    ]
                )
        print("Wrote:", csv_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
