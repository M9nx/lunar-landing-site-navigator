#!/usr/bin/env python3
"""Fail-closed Product 90 metadata and Site04 overlap audit.

Run from JupyterHub, where the data mount is read-only and the home directory
is writable. Team scripts are mounted at ``~/shared-scripts`` (see ``HOST_SHARED_SCRIPTS`` in
``jupyterhub_config.py``; not under ``~/shared-readonly`` — nested binds fail)::

  python ~/shared-scripts/audit_product90_sources.py

This is a source-compatibility preflight. It does NOT validate all 720 far-field
rays, the body-fixed frame tie, the DEM vertical datum, COG conformance, or a
terrain horizon. It therefore never returns a passing compatibility verdict.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer


EXPECTED = {
    "LDEM_80S_80MPP_ADJ.TIF": {
        "url": "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF",
        "sha256": "82030dcbdd7c4bb0c7d858e9b4b293b9f2cda5a543ba31ec0f42784bd6beee5a",
    },
    "LDEM_60S_240MPP_ADJ.TIF": {
        "url": "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF",
        "sha256": "3f9663257b63022f2b0d5a623482ff3cadddceb91594a4e4ca14a94d8cec8b34",
    },
}
POINT_ID = "S04-P02"
POINT_X_M, POINT_Y_M = -2652.5, -6082.5
REFERENCE_RADIUS_M = 1_737_400.0
SITE04_GLOB = "Site04_final_adj_5mpp_surf.tif"

# Diagnostic comparison only: ignores CRS names/authority IDs; does not clear compatibility.
ELLIPSOID_AXIS_ATOL_M = 1e-3
PROJECTION_PARAM_RTOL = 1e-9
PROJECTION_PARAM_ATOL_DEG = 1e-12
PROJECTION_PARAM_ATOL_M = 1e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def raster_metadata(path: Path, expected: dict[str, str] | None = None) -> dict[str, Any]:
    size = path.stat().st_size
    digest = sha256_file(path)
    with rasterio.open(path) as ds:
        crs = CRS.from_user_input(ds.crs) if ds.crs else None
        ellipsoid = None
        if crs and crs.geodetic_crs and crs.geodetic_crs.ellipsoid:
            e = crs.geodetic_crs.ellipsoid
            ellipsoid = {
                "name": e.name,
                "semi_major_m": e.semi_major_metre,
                "semi_minor_m": e.semi_minor_metre,
                "inverse_flattening": e.inverse_flattening,
            }
        return {
            "path": str(path),
            "bytes": size,
            "sha256": digest,
            "expected_sha256": expected.get("sha256") if expected else None,
            "sha256_matches_reported_download": (
                digest == expected["sha256"] if expected else None
            ),
            "source_url": expected.get("url") if expected else None,
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "count": ds.count,
            "dtypes": list(ds.dtypes),
            "pixel_size_x_y": list(ds.res),
            "transform": list(ds.transform),
            "bounds": {
                "left": ds.bounds.left,
                "bottom": ds.bounds.bottom,
                "right": ds.bounds.right,
                "top": ds.bounds.top,
            },
            "nodata": ds.nodata,
            "nodatavals": list(ds.nodatavals),
            "mask_flags": [[flag.name for flag in band] for band in ds.mask_flag_enums],
            "block_shapes": [list(v) for v in ds.block_shapes],
            "overviews_band_1": ds.overviews(1) if ds.count else [],
            "area_or_point": ds.tags().get("AREA_OR_POINT"),
            "dataset_tags": ds.tags(),
            "band_1_tags": ds.tags(1) if ds.count else {},
            "image_structure_tags": ds.tags(ns="IMAGE_STRUCTURE"),
            "crs_wkt": crs.to_wkt() if crs else None,
            "crs_projjson": crs.to_json_dict() if crs else None,
            "geodetic_ellipsoid": ellipsoid,
        }


def _ellipsoid_summary(crs: CRS) -> dict[str, Any] | None:
    g = crs.geodetic_crs
    if g is None or g.ellipsoid is None:
        return None
    e = g.ellipsoid
    return {
        "name": e.name,
        "semi_major_m": e.semi_major_metre,
        "semi_minor_m": e.semi_minor_metre,
        "inverse_flattening": e.inverse_flattening,
    }


def _coordinate_operation_str(crs: CRS) -> str | None:
    op = crs.coordinate_operation
    if op is None:
        return None
    return str(op)


def crs_site04_vs_product90_detail(site: CRS | None, product: CRS | None) -> dict[str, Any]:
    """Strict vs axis-order-ignored equality and parameter summaries for JSON output."""
    if not site or not product:
        return {
            "strict_equal": False,
            "equal_ignore_axis_order": None,
            "axis_directions": {
                "site04": None,
                "product90": None,
            },
            "ellipsoids": {"site04": None, "product90": None},
            "coordinate_operation": {"site04": None, "product90": None},
        }
    strict = bool(site.equals(product))
    equal_ignore: bool | None
    try:
        equal_ignore = bool(site.equals(product, ignore_axis_order=True))
    except TypeError:
        # pyproj too old for ignore_axis_order
        equal_ignore = None
    return {
        "strict_equal": strict,
        "equal_ignore_axis_order": equal_ignore,
        "axis_directions": {
            "site04": [a.direction for a in site.axis_info],
            "product90": [a.direction for a in product.axis_info],
        },
        "ellipsoids": {
            "site04": _ellipsoid_summary(site),
            "product90": _ellipsoid_summary(product),
        },
        "coordinate_operation": {
            "site04": _coordinate_operation_str(site),
            "product90": _coordinate_operation_str(product),
        },
    }


def _ellipsoid_axes_from_crs(crs: CRS | None) -> dict[str, float] | None:
    if crs is None:
        return None
    g = crs.geodetic_crs
    if g is None or g.ellipsoid is None:
        return None
    e = g.ellipsoid
    return {
        "semi_major_m": float(e.semi_major_metre),
        "semi_minor_m": float(e.semi_minor_metre),
    }


def _conversion_from_projjson(projjson: dict[str, Any] | None) -> dict[str, Any] | None:
    if not projjson or projjson.get("type") != "ProjectedCRS":
        return None
    conv = projjson.get("conversion")
    return conv if isinstance(conv, dict) else None


def _conversion_method_name(conv: dict[str, Any] | None) -> str | None:
    if not conv:
        return None
    method = conv.get("method")
    if not isinstance(method, dict):
        return None
    name = method.get("name")
    return str(name) if name is not None else None


def _normalized_conversion_parameters(
    conv: dict[str, Any] | None,
) -> list[tuple[str, float, str]]:
    """Stable-ordered (param name, value, unit string) tuples."""
    if not conv:
        return []
    params = conv.get("parameters")
    if not isinstance(params, list):
        return []
    out: list[tuple[str, float, str]] = []
    for p in params:
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        if name is None:
            continue
        val = p.get("value")
        if val is None:
            continue
        try:
            fv = float(val)
        except (TypeError, ValueError):
            continue
        unit = p.get("unit")
        out.append((str(name), fv, str(unit) if unit is not None else ""))
    return sorted(out, key=lambda x: (x[0], x[2]))


def _param_abs_tol(unit_str: str) -> float:
    u = unit_str.lower()
    if "degree" in u or u in {"°", "deg"}:
        return PROJECTION_PARAM_ATOL_DEG
    if "metre" in u or u == "m":
        return PROJECTION_PARAM_ATOL_M
    return PROJECTION_PARAM_ATOL_M


def projection_parameters_match_detail(
    site04_meta: dict[str, Any],
    product_meta: dict[str, Any],
    site04_crs: CRS | None,
    product_crs: CRS | None,
) -> dict[str, Any]:
    """Compare ellipsoid axes + PROJJSON conversion method/parameters (names/IDs ignored elsewhere)."""
    tolerances = {
        "ellipsoid_semi_axis_m": ELLIPSOID_AXIS_ATOL_M,
        "projection_numeric_relative": PROJECTION_PARAM_RTOL,
        "projection_angle_absolute_deg": PROJECTION_PARAM_ATOL_DEG,
        "projection_linear_absolute_m": PROJECTION_PARAM_ATOL_M,
    }
    site_axes = _ellipsoid_axes_from_crs(site04_crs)
    prod_axes = _ellipsoid_axes_from_crs(product_crs)
    ellipsoid_axes_match: bool | None
    if site_axes is None or prod_axes is None:
        ellipsoid_axes_match = None
    else:
        ellipsoid_axes_match = (
            math.isclose(
                site_axes["semi_major_m"],
                prod_axes["semi_major_m"],
                rel_tol=0.0,
                abs_tol=ELLIPSOID_AXIS_ATOL_M,
            )
            and math.isclose(
                site_axes["semi_minor_m"],
                prod_axes["semi_minor_m"],
                rel_tol=0.0,
                abs_tol=ELLIPSOID_AXIS_ATOL_M,
            )
        )

    site_pj = site04_meta.get("crs_projjson")
    prod_pj = product_meta.get("crs_projjson")
    site_conv = _conversion_from_projjson(site_pj) if isinstance(site_pj, dict) else None
    prod_conv = _conversion_from_projjson(prod_pj) if isinstance(prod_pj, dict) else None

    site_method = _conversion_method_name(site_conv)
    prod_method = _conversion_method_name(prod_conv)
    if site_method is None and prod_method is None and site_conv is None and prod_conv is None:
        conversion_method_match: bool | None = None
    elif site_method is None or prod_method is None:
        conversion_method_match = False
    else:
        conversion_method_match = site_method == prod_method

    site_norm = _normalized_conversion_parameters(site_conv)
    prod_norm = _normalized_conversion_parameters(prod_conv)
    conversion_parameters_match: bool | None
    param_mismatch_reason: str | None = None
    if site_conv is None or prod_conv is None:
        conversion_parameters_match = None
    elif len(site_norm) != len(prod_norm):
        conversion_parameters_match = False
        param_mismatch_reason = "parameter_count_mismatch"
    else:
        conversion_parameters_match = True
        for (na, va, ua), (nb, vb, ub) in zip(site_norm, prod_norm):
            if na != nb:
                conversion_parameters_match = False
                param_mismatch_reason = f"parameter_name_mismatch:{na}!={nb}"
                break
            atol = max(_param_abs_tol(ua), _param_abs_tol(ub))
            if not math.isclose(va, vb, rel_tol=PROJECTION_PARAM_RTOL, abs_tol=atol):
                conversion_parameters_match = False
                param_mismatch_reason = f"value_mismatch:{na}"
                break

    match_components = [
        ellipsoid_axes_match,
        conversion_method_match,
        conversion_parameters_match,
    ]
    if any(m is False for m in match_components):
        overall_match = False
    elif any(m is None for m in match_components):
        overall_match = None
    else:
        overall_match = True

    return {
        "match": overall_match,
        "tolerances": tolerances,
        "notes": (
            "Compares geodetic ellipsoid semi-axes from pyproj and ProjectedCRS conversion "
            "method/parameters from crs_projjson. CRS names, datum IDs, and WKT wording are ignored. "
            "Diagnostic only; does not clear compatibility_verdict or science_calculations_ready."
        ),
        "components": {
            "ellipsoid_axes_match": ellipsoid_axes_match,
            "ellipsoid_axes_m": {"site04": site_axes, "product90": prod_axes},
            "conversion_method_match": conversion_method_match,
            "conversion_methods": {"site04": site_method, "product90": prod_method},
            "conversion_parameters_match": conversion_parameters_match,
            "conversion_parameters_normalized": {
                "site04": [{"name": n, "value": v, "unit": u} for n, v, u in site_norm],
                "product90": [{"name": n, "value": v, "unit": u} for n, v, u in prod_norm],
            },
            "conversion_parameters_mismatch_reason": param_mismatch_reason,
        },
    }


def sample_value(path: Path, x: float, y: float) -> dict[str, Any]:
    with rasterio.open(path) as ds:
        inside = ds.bounds.left <= x <= ds.bounds.right and ds.bounds.bottom <= y <= ds.bounds.top
        if not inside:
            return {"inside_bounds": False, "x": x, "y": y, "value": None}
        arr = next(ds.sample([(x, y)], indexes=1, masked=True))
        value = None if np.ma.is_masked(arr[0]) else float(arr[0])
        row, col = ds.index(x, y)
        return {
            "inside_bounds": True,
            "row": int(row),
            "col": int(col),
            "x": float(x),
            "y": float(y),
            "value": value,
            "is_valid": value is not None and np.isfinite(value),
        }


def find_first(paths: list[Path], pattern: str) -> Path | None:
    for root in paths:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Hub data root; defaults to the mounted /home/jovyan/data or /workspace/data.",
    )
    parser.add_argument(
        "--site04",
        type=Path,
        default=None,
        help="Optional explicit path to Site04_final_adj_5mpp_surf.tif.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "research-results/site04-spice-baseline/B5_terrain_sources.json",
    )
    args = parser.parse_args()

    roots = [args.data_root.expanduser()] if args.data_root else [
        Path("/home/jovyan/data"),
        Path("/workspace/data"),
    ]
    product_root = find_first(roots, "LOLA_20mpp")
    if product_root is None:
        raise FileNotFoundError(
            "Could not find LOLA_20mpp below the data roots: "
            + ", ".join(map(str, roots))
        )
    site04_path = args.site04.expanduser() if args.site04 else find_first(
        roots, f"LOLA_5mpp/Site04/{SITE04_GLOB}"
    )
    if site04_path is None or not site04_path.is_file():
        raise FileNotFoundError(
            f"Could not find {SITE04_GLOB}. Pass --site04 /path/to/file."
        )

    assets: dict[str, Any] = {}
    missing: list[str] = []
    for filename, expected in EXPECTED.items():
        path = product_root / filename
        if not path.is_file():
            missing.append(str(path))
            continue
        assets[filename] = raster_metadata(path, expected)

    if missing:
        raise FileNotFoundError("Missing Product 90 assets: " + ", ".join(missing))

    site04 = raster_metadata(site04_path)
    site04_crs = CRS.from_wkt(site04["crs_wkt"]) if site04["crs_wkt"] else None
    candidate_results: dict[str, Any] = {}
    for filename in EXPECTED:
        product = assets[filename]
        product_crs = CRS.from_wkt(product["crs_wkt"]) if product["crs_wkt"] else None
        crs_equal = bool(site04_crs and product_crs and site04_crs.equals(product_crs))
        crs_axis_info = {
            "site04": [a.direction for a in site04_crs.axis_info] if site04_crs else None,
            "product90": [a.direction for a in product_crs.axis_info] if product_crs else None,
        }
        crs_site04_vs_product90 = crs_site04_vs_product90_detail(site04_crs, product_crs)
        projection_parameters_match = projection_parameters_match_detail(
            site04, product, site04_crs, product_crs,
        )
        shared_samples: list[dict[str, Any]] = []
        if not site04_crs or not product_crs:
            point = {"error": "CRS missing; cannot transform fixed point."}
            roundtrip = None
        else:
            forward = Transformer.from_crs(site04_crs, product_crs, always_xy=True)
            inverse = Transformer.from_crs(product_crs, site04_crs, always_xy=True)
            px, py = forward.transform(POINT_X_M, POINT_Y_M)
            rx, ry = inverse.transform(px, py)
            point = sample_value(product_root / filename, px, py)
            point.update({
                "site04_xy_m": [POINT_X_M, POINT_Y_M],
                "product90_xy_m": [float(px), float(py)],
                "transform_name": forward.description,
            })
            roundtrip = {
                "site04_xy_roundtrip_m": [float(rx), float(ry)],
                "residual_m": float(np.hypot(rx - POINT_X_M, ry - POINT_Y_M)),
            }

            # Sample a deterministic 5x5 set over the Site04 footprint, then
            # compare co-located elevations where both rasters have valid data.
            # Differences are diagnostic only: the surfaces have different
            # resolutions and this cannot establish a vertical datum by itself.
            with rasterio.open(site04_path) as sds:
                xs = np.linspace(sds.bounds.left + sds.res[0] / 2,
                                 sds.bounds.right - sds.res[0] / 2, 5)
                ys = np.linspace(sds.bounds.bottom + abs(sds.res[1]) / 2,
                                 sds.bounds.top - abs(sds.res[1]) / 2, 5)
                coords = [(float(x), float(y)) for y in ys for x in xs]
                svals = list(sds.sample(coords, indexes=1, masked=True))
            mapped = [forward.transform(x, y) for x, y in coords]
            with rasterio.open(product_root / filename) as pds:
                pvals = list(pds.sample(mapped, indexes=1, masked=True))
            for i, ((sx, sy), sv, pv) in enumerate(zip(coords, svals, pvals)):
                svalue = None if np.ma.is_masked(sv[0]) else float(sv[0])
                pvalue = None if np.ma.is_masked(pv[0]) else float(pv[0])
                shared_samples.append({
                    "sample_id": i,
                    "site04_xy_m": [sx, sy],
                    "product90_xy_m": [float(mapped[i][0]), float(mapped[i][1])],
                    "site04_z_m": svalue,
                    "product90_z_m": pvalue,
                    "product90_minus_site04_m": (
                        pvalue - svalue if svalue is not None and pvalue is not None else None
                    ),
                    "both_valid": svalue is not None and pvalue is not None,
                })

        valid_diffs = [
            row["product90_minus_site04_m"] for row in shared_samples
            if row["product90_minus_site04_m"] is not None
        ]
        with rasterio.open(product_root / filename) as pds:
            inside_site04_bounds = (
                pds.bounds.left <= POINT_X_M <= pds.bounds.right
                and pds.bounds.bottom <= POINT_Y_M <= pds.bounds.top
            ) if crs_equal else None
        candidate_results[filename] = {
            "crs_equals_site04": crs_equal,
            "crs_site04_vs_product90": crs_site04_vs_product90,
            "projection_parameters_match": projection_parameters_match,
            "axis_directions": crs_axis_info,
            "observer_point_sample": point,
            "observer_point_roundtrip": roundtrip,
            "observer_xy_in_bounds_without_transform": inside_site04_bounds,
            "shared_area_samples": shared_samples,
            "shared_area_valid_sample_count": len(valid_diffs),
            "shared_area_vertical_difference_m": (
                {
                    "min": float(np.min(valid_diffs)),
                    "median": float(np.median(valid_diffs)),
                    "max": float(np.max(valid_diffs)),
                } if valid_diffs else None
            ),
            "vertical_convention_verified": False,
            "frame_tie_verified": False,
            "720_ray_valid_coverage_checked": False,
        }

    payload = {
        "audit_type": "Product 90 metadata and Site04 overlap preflight",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "access_date_utc": datetime.now(timezone.utc).date().isoformat(),
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "rasterio": rasterio.__version__,
            "gdal": rasterio.__gdal_version__,
            "proj": rasterio.__proj_version__,
        },
        "site04": site04,
        "reference_radius_expected_m": REFERENCE_RADIUS_M,
        "fixed_point": {
            "id": POINT_ID,
            "x_m": POINT_X_M,
            "y_m": POINT_Y_M,
            "source": "docs/FRAME_GEOMETRY_VALIDATION.md",
        },
        "product90_assets": assets,
        "candidate_checks": candidate_results,
        "compatibility_verdict": "blocked",
        "verdict_reason": (
            "This preflight records raster metadata, checksum, observer-point sampling, "
            "round-trip, and shared-area elevation diagnostics. It does not verify the "
            "MOON_ME frame tie, elevation datum, all 720-ray NoData coverage, or COG "
            "conformance. Owner review and those follow-up checks are required before stacking."
        ),
        "full_B5_pass": False,
        "science_calculations_ready": False,
    }

    args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
    output_path = args.output.expanduser()
    output_path.write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    print("Wrote:", output_path)
    for filename, result in candidate_results.items():
        crs_detail = result["crs_site04_vs_product90"]
        proj_match = result["projection_parameters_match"]
        print(
            filename,
            "CRS-equal=", result["crs_equals_site04"],
            "CRS-equal-ignore-axis=",
            crs_detail["equal_ignore_axis_order"],
            "proj-params-match=", proj_match["match"],
            "observer-valid=", result["observer_point_sample"].get("is_valid"),
            "shared-valid=", result["shared_area_valid_sample_count"], "/ 25",
            "meanings: diagnostic only; compatibility verdict remains blocked",
        )
    print("compatibility_verdict=blocked; full_B5_pass=false; SCIENCE_CALCULATIONS_READY=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
