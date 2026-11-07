"""
Deterministic replay observation generator (SIMULATION / PRACTICE DATA).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .synthetic_ephemeris import DEFAULT_SCENARIO, ScenarioDefinition, synthetic_body_angles


@dataclass(frozen=True)
class SyntheticObservation:
    """One timestamped practice observation."""

    sequence_id: int
    utc: datetime
    site_id: str
    sun_az_deg: float
    sun_el_deg: float
    earth_az_deg: float
    earth_el_deg: float
    units: str = "deg"
    angles_frame: str = "local_topocentric_clockwise_from_north_geometric_0"
    source: str = "replay_synthetic_v1"


def synthetic_obs_to_dict(o: SyntheticObservation) -> dict[str, Any]:
    return {
        "sequence_id": o.sequence_id,
        "utc": o.utc.isoformat().replace("+00:00", "Z"),
        "site_id": o.site_id,
        "sun_az_deg": o.sun_az_deg,
        "sun_el_deg": o.sun_el_deg,
        "earth_az_deg": o.earth_az_deg,
        "earth_el_deg": o.earth_el_deg,
        "units": o.units,
        "angles_frame": o.angles_frame,
        "source": o.source,
    }


def generate_replay_sequence(scenario: ScenarioDefinition) -> list[SyntheticObservation]:
    out: list[SyntheticObservation] = []
    base = datetime.fromisoformat(scenario.iso_date + "T00:00:00+00:00")
    seq = 0
    for i in range(scenario.hour_count):
        utc = base + timedelta(hours=i)
        hour_of_day = utc.hour
        for site in (scenario.site_a, scenario.site_b):
            sun_el, earth_el, sun_az, earth_az = synthetic_body_angles(
                site_key=site,
                hour=hour_of_day,
                iso_date=scenario.iso_date,
                phases=scenario.phases,
            )
            out.append(
                SyntheticObservation(
                    sequence_id=seq,
                    utc=utc,
                    site_id=site,
                    sun_az_deg=sun_az,
                    sun_el_deg=sun_el,
                    earth_az_deg=earth_az,
                    earth_el_deg=earth_el,
                )
            )
            seq += 1
    return out
