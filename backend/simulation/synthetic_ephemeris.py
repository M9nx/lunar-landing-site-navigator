"""
Deterministic synthetic Sun/Earth azimuth and elevation (practice only).

Aligned with docs/prototype/ephemeris.js — not SPICE, not challenge truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


def _date_variation_seed(iso_date: str) -> float:
    h = 0
    for ch in iso_date:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    u = abs(math.sin(h * 0.0001))
    return u - int(u)


def _angle(phase: float, hour: int, amplitude: float, offset: float) -> float:
    return offset + amplitude * math.sin((2 * math.pi * hour) / 24.0 + phase)


def synthetic_body_angles(
    *,
    site_key: str,
    hour: int,
    iso_date: str,
    phases: dict[str, tuple[float, float]],
) -> tuple[float, float, float, float]:
    """
    Returns sun_el, earth_el, sun_az, earth_az (degrees).
    phases maps site_key -> (phase, earth_phase) for sin wave.
    """
    phase, earth_phase = phases.get(site_key, (0.15, 1.05))
    d = _date_variation_seed(iso_date) * 0.35
    sun_el = _angle(phase, hour, 8.2, -0.7 + d * 0.1)
    earth_el = _angle(earth_phase, hour, 6.5, -0.3 + d * 0.08)
    sun_az = (hour * 15) % 360
    earth_az = (hour * 15 + 140) % 360
    return sun_el, earth_el, float(sun_az), float(earth_az)


@dataclass(frozen=True)
class ScenarioDefinition:
    """Static scenario metadata (SIMULATION)."""

    id: str
    label: str
    iso_date: str
    site_a: str
    site_b: str
    site_labels: dict[str, str]
    terrain_source: str
    resolution_note: str
    phases: dict[str, tuple[float, float]]
    hour_start: int
    hour_count: int  # e.g. 72 = 3 days hourly


DEFAULT_SCENARIO = ScenarioDefinition(
    id="s04_malapert_hourly_practice_v1",
    label="Site04 vs Malapert · hourly synthetic · PRACTICE",
    iso_date="2025-01-01",
    site_a="s04p02",
    site_b="malapert",
    site_labels={
        "s04p02": "Site04 S04-P02",
        "malapert": "Malapert Massif",
    },
    terrain_source="Invented polar silhouette (not Site04 Product 90/69 DEM)",
    resolution_note="Azimuth step 3° cache; samples hourly UTC",
    phases={
        "s04p02": (0.15, 1.05),
        "malapert": (1.1, 0.35),
    },
    hour_start=0,
    hour_count=72,
)
