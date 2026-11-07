"""Centre-ray visibility contract (synthetic). See docs/ENGINE_CALCULATION_PIPELINE.md."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal

BodyState = Literal["clear", "blocked", "unknown"]


class ObservationValidity(str, Enum):
    accepted = "accepted"
    rejected_duplicate = "rejected_duplicate"
    rejected_out_of_order = "rejected_out_of_order"
    rejected_malformed = "rejected_malformed"
    rejected_unit_mismatch = "rejected_unit_mismatch"
    rejected_frame_mismatch = "rejected_frame_mismatch"


def classify_centre_ray(
    target_elevation_deg: float,
    terrain_horizon_elevation_deg: float | None,
    *,
    ray_terrain_known: bool,
) -> BodyState:
    if not ray_terrain_known or terrain_horizon_elevation_deg is None:
        return "unknown"
    if math.isnan(target_elevation_deg) or math.isnan(terrain_horizon_elevation_deg):
        return "unknown"
    if target_elevation_deg > terrain_horizon_elevation_deg:
        return "clear"
    return "blocked"


@dataclass(frozen=True)
class SiteHorizonCache:
    """Precomputed synthetic horizon samples (3° steps) for fast lookup."""

    site_id: str
    # azimuth_bucket 0..119 -> centre azimuth bucket*3
    elevations: list[float | None]
    known: list[bool]

    @classmethod
    def build(cls, site_id: str) -> SiteHorizonCache:
        from .terrain import horizon_for_site

        elevations: list[float | None] = []
        known: list[bool] = []
        for b in range(120):
            az = b * 3.0
            s = horizon_for_site(site_id, az)
            elevations.append(s.elevation_deg)
            known.append(s.terrain_known)
        return cls(site_id=site_id, elevations=elevations, known=known)

    def at_azimuth(self, az_deg: float) -> tuple[float | None, bool]:
        """Nearest 3° bucket (same resolution as prototype terrain ring)."""
        a = az_deg % 360.0
        b = int(round(a / 3.0)) % 120
        return self.elevations[b], self.known[b]
