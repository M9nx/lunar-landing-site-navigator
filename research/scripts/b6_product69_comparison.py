#!/usr/bin/env python3
"""Product 69 — optional raster manifest for B6; comparison only after PDS label review.

Without ``--product69-raster``, prints the blocker and exits 2.

With ``--product69-raster`` and ``--output-json``, writes a **manifest only** (checksum,
CRS, dtype, shape, tags). This does **not** assert compatibility with S04-P02 or with
notebook 03’s 2025 hourly outputs. Long-term (~18.6 y) averages remain separate from
date-specific predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio


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
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def raster_manifest(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as ds:
        tags = ds.tags()
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "count": ds.count,
            "dtypes": [ds.dtypes[i] for i in range(ds.count)],
            "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
            "transform": [ds.transform.a, ds.transform.b, ds.transform.c, ds.transform.d, ds.transform.e, ds.transform.f],
            "bounds": {
                "left": ds.bounds.left,
                "bottom": ds.bounds.bottom,
                "right": ds.bounds.right,
                "top": ds.bounds.top,
            },
            "nodata": ds.nodata,
            "tags": tags,
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--product69-raster",
        type=Path,
        default=None,
        help="Path to a Product 69 GeoTIFF on the ignored data mount.",
    )
    p.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Write manifest JSON (metadata only; not a validation result).",
    )
    args = p.parse_args()

    if args.product69_raster is None or not args.product69_raster.is_file():
        print(
            "B6 blocked: pass --product69-raster to a mounted Product 69 file; optionally "
            "--output-json for a manifest. Read PDS labels before any S04-P02 comparison. "
            "See research/B6_PRODUCT69_BLOCKER.md.",
            file=sys.stderr,
        )
        return 2

    manifest = {
        "b6_status": "manifest_only_labels_review_required",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "source_product": "PGDA Product 69 — see https://pgda.gsfc.nasa.gov/products/69",
        "caveat": (
            "~18.6-year lunar nutation cycle averages in Product 69 are not an oracle for "
            "2025 hourly notebook 03 outputs."
        ),
        "raster": raster_manifest(args.product69_raster.expanduser()),
    }

    if args.output_json:
        out = args.output_json.expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(json_safe(manifest), indent=2) + "\n")
        print("Wrote:", out)
    else:
        print(
            "Product 69 raster readable; pass --output-json to save manifest. "
            "Pixel comparison at S04-P02 not implemented until PDS label definitions are reviewed.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
