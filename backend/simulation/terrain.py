"""
Synthetic terrain horizon lookup by azimuth (practice / SIMULATION).

Mirrors the teaching model in docs/prototype/ephemeris.js and tests — not a DEM.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin


@dataclass(frozen=True)
class HorizonSample:
    """Terrain horizon elevation (deg) on a ray, or unknown."""

    elevation_deg: float | None
    terrain_known: bool


def terrain_horizon_malapert(az_deg: float) -> HorizonSample:
    """Malapert toy map: gap (unknown), ridge bump, else 0°."""
    a = az_deg % 360.0
    if 20.0 <= a <= 40.0:
        return HorizonSample(elevation_deg=None, terrain_known=False)
    if 70.0 <= a <= 110.0:
        t = (a - 70.0) / 40.0
        bump = sin(pi * t)
        return HorizonSample(elevation_deg=12.0 * bump, terrain_known=True)
    return HorizonSample(elevation_deg=0.0, terrain_known=True)


def terrain_horizon_s04p02(_az_deg: float) -> HorizonSample:
    """Flat synthetic silhouette at 0° everywhere."""
    return HorizonSample(elevation_deg=0.0, terrain_known=True)


TERRAIN_BY_SITE: dict[str, callable[[float], HorizonSample]] = {
    "s04p02": terrain_horizon_s04p02,
    "malapert": terrain_horizon_malapert,
}


def horizon_for_site(site_id: str, azimuth_deg: float) -> HorizonSample:
    fn = TERRAIN_BY_SITE.get(site_id)
    if fn is None:
        return HorizonSample(elevation_deg=None, terrain_known=False)
    return fn(azimuth_deg)
