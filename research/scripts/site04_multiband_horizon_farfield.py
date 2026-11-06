#!/usr/bin/env python3
"""Multiband 720×0.5° terrain horizon (Site04 5 m + Product 90 80 m + 240 m) — diagnostic, fail-closed.

Observer S04-P02: lon/lat/Z from ``Site04_final_adj_5mpp_surf.tif``. Each DEM uses notebook 05
ray assignment in **that raster's** map plane; ``los_elevation_deg`` uses the shared observer
east/north/up (from lon/lat at the surface).

Bands (s = along-ray distance in map plane, m): site04 (5,5000]; 80 m (5000,1e5]; 240 m
(1e5, min(outer_cap, extent_to_corner)]. Composite = nanmax across bands — not validated.

Seam annuli (deg diffs where both finite): Site04 (4500,5000] vs 80 m (5000,5500]; 80 m
(95000,1e5] vs 240 m (1e5,110000].

Example::

  python research/scripts/site04_multiband_horizon_farfield.py \\
    --data-root ./data --outer-cap-m 450000 \\
    --output-dir ./research-results/site04-spice-baseline/sprint_run
"""
from __future__ import annotations

import argparse
import csv
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

POINT_ID = "S04-P02"
OBSERVER_XY_SITE04_M = (-2652.5, -6082.5)
REFERENCE_RADIUS_M = 1_737_400.0
AZIMUTH_STEP_DEG = 0.5
RAY_STEP_M = 2.5
MAP_TANGENT_STEP_M = 1.0

EXPECTED = {
    "site04_surf": Path("LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif"),
    "p90_80": Path("LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF"),
    "p90_240": Path("LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF"),
}


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


def lonlat_xyz_km_vec(lon: np.ndarray, lat: np.ndarray, z_m: np.ndarray) -> np.ndarray:
    lonr = np.deg2rad(lon)
    latr = np.deg2rad(lat)
    r = (REFERENCE_RADIUS_M + np.asarray(z_m)) / 1000.0
    return np.stack(
        [r * np.cos(latr) * np.cos(lonr), r * np.cos(latr) * np.sin(lonr), r * np.sin(latr)],
        axis=-1,
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
) -> tuple[float, float]:
    lon, lat = xyz_km_to_lonlat_deg(obs_km + tangent_unit_km * (MAP_TANGENT_STEP_M / 1000.0))
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
    min_along: float,
    max_along: float,
    cross_track_m: float,
    exclusive_min: bool,
) -> tuple[np.ndarray, np.ndarray]:
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
    lo = along > min_along if exclusive_min else along >= min_along
    valid = lo & (along <= max_along) & (cross <= cross_track_m) & (az_diff <= az_half)
    cross_score = np.where(valid, cross, np.inf)
    pick = np.argmin(cross_score, axis=1)
    row_idx = np.arange(vx.shape[0], dtype=np.int64)
    chosen = candidates[row_idx, pick]
    ok = np.isfinite(cross_score[row_idx, pick])
    return chosen, ok


def observer_lonlat_z(site04_path: Path) -> tuple[float, float, float]:
    with rasterio.open(site04_path) as ds:
        if ds.crs is None:
            raise ValueError("Site04 has no CRS")
        crs = CRS.from_wkt(ds.crs.to_wkt())
        geo = crs.geodetic_crs
        if geo is None:
            raise ValueError("Site04 has no geodetic CRS")
        inv = Transformer.from_crs(crs, geo, always_xy=True)
        lon0, lat0 = inv.transform(OBSERVER_XY_SITE04_M[0], OBSERVER_XY_SITE04_M[1])
        row, col = ds.index(OBSERVER_XY_SITE04_M[0], OBSERVER_XY_SITE04_M[1])
        zarr = ds.read(1, masked=True)
        z0 = float(zarr[row, col])
        if not np.isfinite(z0) or np.ma.is_masked(zarr[row, col]):
            raise ValueError("Observer Z invalid on Site04")
        return float(lon0), float(lat0), z0


def dem_ray_geometry(
    lon0: float,
    lat0: float,
    z0: float,
    dem_path: Path,
) -> tuple[
    Any,
    float,
    float,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    float,
    float,
    float,
    np.ndarray,
    np.ndarray,
]:
    """Return open dataset handle (caller must close), ox,oy, obs_km,east,north,up, ex,ey,nx,ny, ray_dx,ray_dy, az_centres, cross, extent."""
    dem = rasterio.open(dem_path)
    if dem.crs is None:
        dem.close()
        raise ValueError("DEM missing CRS")
    dem_crs = CRS.from_wkt(dem.crs.to_wkt())
    geo = dem_crs.geodetic_crs
    if geo is None:
        dem.close()
        raise ValueError("DEM has no geodetic CRS")
    fwd_dem = Transformer.from_crs(geo, dem_crs, always_xy=True)
    inv_dem = Transformer.from_crs(dem_crs, geo, always_xy=True)
    ox, oy = fwd_dem.transform(lon0, lat0)

    bounds = dem.bounds
    corners = (
        (bounds.left, bounds.bottom),
        (bounds.left, bounds.top),
        (bounds.right, bounds.bottom),
        (bounds.right, bounds.top),
    )
    max_extent_m = max(math.hypot(cx - ox, cy - oy) for cx, cy in corners)

    obs_km = lonlat_xyz_km(lon0, lat0, z0)
    lonr, latr = math.radians(lon0), math.radians(lat0)
    east = np.array([-math.sin(lonr), math.cos(lonr), 0.0])
    north = np.array(
        [-math.sin(latr) * math.cos(lonr), -math.sin(latr) * math.sin(lonr), math.cos(latr)]
    )
    up = obs_km / np.linalg.norm(obs_km)

    ex_m, ey_m = map_offset_from_tangent_km(obs_km, east, fwd_dem, ox, oy)
    nx_m, ny_m = map_offset_from_tangent_km(obs_km, north, fwd_dem, ox, oy)
    ex_m, ey_m = ex_m / math.hypot(ex_m, ey_m), ey_m / math.hypot(ex_m, ey_m)
    nx_m, ny_m = nx_m / math.hypot(nx_m, ny_m), ny_m / math.hypot(nx_m, ny_m)

    n_bins = int(round(360.0 / AZIMUTH_STEP_DEG))
    az_centres = np.arange(n_bins, dtype=np.float64) * AZIMUTH_STEP_DEG
    az_rad = np.deg2rad(az_centres)
    ray_dx = np.sin(az_rad) * ex_m + np.cos(az_rad) * nx_m
    ray_dy = np.sin(az_rad) * ey_m + np.cos(az_rad) * ny_m
    rl = np.hypot(ray_dx, ray_dy)
    ray_dx, ray_dy = ray_dx / rl, ray_dy / rl

    transform = dem.transform
    pixel_size_x = abs(float(transform.a))
    pixel_size_y = abs(float(transform.e))
    cross_track_m = max(RAY_STEP_M, 0.5 * max(pixel_size_x, pixel_size_y))

    return (
        dem,
        ox,
        oy,
        obs_km,
        east,
        north,
        up,
        ex_m,
        ey_m,
        nx_m,
        ny_m,
        ray_dx,
        ray_dy,
        az_centres,
        cross_track_m,
        max_extent_m,
        inv_dem,
    )


def max_horizon_annulus(
    lon0: float,
    lat0: float,
    z0: float,
    dem_path: Path,
    *,
    min_along: float,
    max_along: float,
    exclusive_min: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    (
        dem,
        ox,
        oy,
        obs_km,
        east,
        north,
        up,
        ex_m,
        ey_m,
        nx_m,
        ny_m,
        ray_dx,
        ray_dy,
        az_centres,
        cross_track_m,
        max_extent_m,
        inv_dem,
    ) = dem_ray_geometry(lon0, lat0, z0, dem_path)

    n_bins = ray_dx.shape[0]
    h_max = np.full(n_bins, np.nan, dtype=np.float64)
    counts = np.zeros(n_bins, dtype=np.int64)

    try:
        transform = dem.transform
        w, h = dem.width, dem.height
        arr = dem.read(1, masked=True)
        mask_ok = ~np.ma.getmaskarray(arr) & np.isfinite(np.asarray(arr, dtype=np.float64))

        block = 128
        for row0 in range(0, h, block):
            r1 = min(row0 + block, h)
            rg, cg = np.indices((r1 - row0, w))
            rg = rg + row0
            xb = transform.c + transform.a * (cg + 0.5) + transform.b * (rg + 0.5)
            yb = transform.f + transform.d * (cg + 0.5) + transform.e * (rg + 0.5)
            zb = mask_ok[row0:r1]
            rb, cb = np.where(zb)
            if not len(rb):
                continue
            rb = rb + row0
            x = xb[rb - row0, cb]
            y = yb[rb - row0, cb]
            zpix = np.asarray(arr)[rb, cb]
            vx = x - ox
            vy = y - oy
            map_az = (np.degrees(np.arctan2(vx * ex_m + vy * ey_m, vx * nx_m + vy * ny_m)) % 360.0)
            bins, ok = assign_ray_bins(
                map_az,
                vx,
                vy,
                n_bins=n_bins,
                az_centres=az_centres,
                ray_dx=ray_dx,
                ray_dy=ray_dy,
                min_along=min_along,
                max_along=max_along,
                cross_track_m=cross_track_m,
                exclusive_min=exclusive_min,
            )
            if not np.any(ok):
                continue
            x = x[ok]
            y = y[ok]
            zpix = zpix[ok]
            bins = bins[ok]
            lon_p, lat_p = inv_dem.transform(x, y)
            xyz = lonlat_xyz_km_vec(lon_p, lat_p, zpix)
            vec = xyz - obs_km
            e = vec @ east
            nn = vec @ north
            uu = vec @ up
            el = np.degrees(np.arctan2(uu, np.hypot(e, nn)))
            for b in range(n_bins):
                m = bins == b
                if not np.any(m):
                    continue
                counts[b] += int(np.sum(m))
                mx = float(np.nanmax(el[m]))
                if not np.isfinite(h_max[b]) or mx > h_max[b]:
                    h_max[b] = mx
    finally:
        dem.close()

    meta = {
        "dem_path": str(dem_path),
        "cross_track_m": cross_track_m,
        "min_along_m": min_along,
        "max_along_m": max_along,
        "exclusive_min": exclusive_min,
        "max_extent_from_observer_m": max_extent_m,
    }
    return h_max, counts, meta


def seam_stats(name: str, h_a: np.ndarray, h_b: np.ndarray) -> dict[str, Any]:
    both = np.isfinite(h_a) & np.isfinite(h_b)
    diff = np.where(both, h_b - h_a, np.nan)
    finite = diff[np.isfinite(diff)]
    top: list[dict[str, Any]] = []
    if finite.size:
        abs_d = np.abs(np.where(both, h_b - h_a, np.nan))
        order = np.argsort(-abs_d)[:20]
        for i in order:
            if not both[i]:
                continue
            d = float(diff[i])
            top.append(
                {
                    "bin_index": int(i),
                    "azimuth_centre_deg": float(i) * AZIMUTH_STEP_DEG,
                    "diff_deg_h_b_minus_h_a": d,
                }
            )
    return {
        "name": name,
        "bins_with_both_finite": int(np.sum(both)),
        "diff_deg_median": float(np.median(finite)) if finite.size else None,
        "diff_deg_p95": float(np.percentile(finite, 95)) if finite.size else None,
        "diff_deg_max_abs": float(np.max(np.abs(finite))) if finite.size else None,
        "largest_abs_diff_bins_top20": top,
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
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--outer-cap-m", type=float, default=450_000.0)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--repo-commit", type=str, default=None)
    args = p.parse_args()

    data_root = args.data_root.expanduser().resolve()
    site04 = data_root / EXPECTED["site04_surf"]
    p80 = data_root / EXPECTED["p90_80"]
    p240 = data_root / EXPECTED["p90_240"]
    for path in (site04, p80, p240):
        if not path.is_file():
            raise FileNotFoundError(path)

    lon0, lat0, z0 = observer_lonlat_z(site04)
    _geom240 = dem_ray_geometry(lon0, lat0, z0, p240)
    dem240 = _geom240[0]
    max_ext_240 = _geom240[15]
    try:
        outer = min(args.outer_cap_m, max_ext_240)
    finally:
        dem240.close()

    h5, c5, m5 = max_horizon_annulus(
        lon0, lat0, z0, site04, min_along=5.0, max_along=5000.0, exclusive_min=True
    )
    h5_seam_a, _, _ = max_horizon_annulus(
        lon0, lat0, z0, site04, min_along=4500.0, max_along=5000.0, exclusive_min=True
    )

    h80, c80, m80 = max_horizon_annulus(
        lon0, lat0, z0, p80, min_along=5000.0, max_along=100_000.0, exclusive_min=True
    )
    h80_seam_b, _, _ = max_horizon_annulus(
        lon0, lat0, z0, p80, min_along=5000.0, max_along=5500.0, exclusive_min=True
    )
    h80_seam_100, _, _ = max_horizon_annulus(
        lon0, lat0, z0, p80, min_along=95_000.0, max_along=100_000.0, exclusive_min=True
    )

    h240, c240, m240 = max_horizon_annulus(
        lon0, lat0, z0, p240, min_along=100_000.0, max_along=outer, exclusive_min=True
    )
    h240_seam_100, _, _ = max_horizon_annulus(
        lon0, lat0, z0, p240, min_along=100_000.0, max_along=110_000.0, exclusive_min=True
    )

    composite = np.nanmax(np.stack([h5, h80, h240], axis=0), axis=0)

    seams = [
        seam_stats("seam_5km_site04_4500_5000_vs_80m_5000_5500", h5_seam_a, h80_seam_b),
        seam_stats("seam_100km_80m_95k_100k_vs_240m_100k_110k", h80_seam_100, h240_seam_100),
    ]

    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    az_centres = np.arange(720, dtype=np.float64) * AZIMUTH_STEP_DEG
    csv_path = out_dir / "S04-P02_horizon_profile_farfield.csv"
    with csv_path.open("w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "azimuth_deg",
                "horizon_site04_5m_deg",
                "horizon_p90_80m_deg",
                "horizon_p90_240m_deg",
                "horizon_composite_nanmax_deg",
                "coverage_site04_samples",
                "coverage_80m_samples",
                "coverage_240m_samples",
            ]
        )
        for i in range(720):
            w.writerow(
                [
                    f"{float(az_centres[i]):.4f}",
                    "" if not np.isfinite(h5[i]) else f"{float(h5[i]):.8f}",
                    "" if not np.isfinite(h80[i]) else f"{float(h80[i]):.8f}",
                    "" if not np.isfinite(h240[i]) else f"{float(h240[i]):.8f}",
                    "" if not np.isfinite(composite[i]) else f"{float(composite[i]):.8f}",
                    int(c5[i]),
                    int(c80[i]),
                    int(c240[i]),
                ]
            )

    manifest = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "full_B5_pass": False,
        "b5_verdict": "blocked",
        "science_calculations_ready": False,
        "point_id": POINT_ID,
        "observer_lon_lat_z": {"lon_deg": lon0, "lat_deg": lat0, "z_m_site04": z0},
        "data_root": str(data_root),
        "outer_cap_m_requested": args.outer_cap_m,
        "outer_cap_m_effective_240m": outer,
        "bands": {
            "site04_5m_5_5000_exclusive": m5,
            "p90_80m_5000_100000": m80,
            "p90_240m_100000_to_cap": m240,
        },
        "seam_annulus_summaries_deg": seams,
        "blockers": {
            "frame_tie": (
                "Independent MOON_ME/DE421 raster tie not established; pyproj uses Ballpark "
                "transforms between CRS labels unless owner supplies verified ops."
            ),
            "vertical_datum": (
                "Product 90 adjusted GeoTIFF vertical zero vs Site04 not independently verified."
            ),
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "rasterio": rasterio.__version__,
        },
        "git_commit": args.repo_commit or git_head(),
        "csv_path": str(csv_path),
    }
    man_path = out_dir / "B5_farfield_validation_manifest.json"
    man_path.write_text(json.dumps(json_safe(manifest), indent=2) + "\n")

    print("Wrote:", csv_path)
    print("Wrote:", man_path)
    print(
        "finite_bins: site04=", int(np.sum(np.isfinite(h5))),
        "80m=", int(np.sum(np.isfinite(h80))),
        "240m=", int(np.sum(np.isfinite(h240))),
        "composite=", int(np.sum(np.isfinite(composite))),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
