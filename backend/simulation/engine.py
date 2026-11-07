"""Validate observations and compute incremental centre-ray visibility (SIMULATION)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from .contracts import (
    BodyState,
    ObservationValidity,
    SiteHorizonCache,
    classify_centre_ray,
)

EXPECTED_UNITS = "deg"
EXPECTED_FRAME = "local_topocentric_clockwise_from_north_geometric_0"
GEOMETRIC_HORIZON_DEG = 0.0


@dataclass(frozen=True)
class ValidationResult:
    validity: ObservationValidity
    detail: str


@dataclass(frozen=True)
class ComputationResultOut:
    sequence_id: int
    utc: str
    site_id: str
    geometric_horizon_deg: float
    sun_az_deg: float
    sun_el_deg: float
    earth_az_deg: float
    earth_el_deg: float
    sun_state: BodyState
    earth_state: BodyState
    sun_margin_deg: float | None
    earth_margin_deg: float | None
    centre_ray_only: bool
    data_validity: Literal["accepted"]


def validate_observation_fields(obs: dict[str, Any]) -> ValidationResult | None:
    """Return ValidationResult if invalid, else None."""
    if obs.get("units") not in (None, EXPECTED_UNITS):
        return ValidationResult(ObservationValidity.rejected_unit_mismatch, f"units must be {EXPECTED_UNITS!r}")
    if obs.get("angles_frame") not in (None, EXPECTED_FRAME):
        return ValidationResult(ObservationValidity.rejected_frame_mismatch, f"angles_frame must be {EXPECTED_FRAME!r}")
    for key in ("sun_az_deg", "sun_el_deg", "earth_az_deg", "earth_el_deg"):
        v = obs.get(key)
        if v is None or not isinstance(v, (int, float)) or math.isnan(float(v)):
            return ValidationResult(ObservationValidity.rejected_malformed, f"missing or invalid {key}")
    if "sequence_id" not in obs:
        return ValidationResult(ObservationValidity.rejected_malformed, "missing sequence_id")
    if "utc" not in obs:
        return ValidationResult(ObservationValidity.rejected_malformed, "missing utc")
    if "site_id" not in obs:
        return ValidationResult(ObservationValidity.rejected_malformed, "missing site_id")
    return None


def process_observation(
    *,
    obs: dict[str, Any],
    horizon_cache: dict[str, SiteHorizonCache],
    last_sequence_by_site: dict[str, int | None],
    last_utc_by_site: dict[str, datetime | None],
    stale_seconds: float = 86400.0 * 14,
    wall_clock_now: datetime | None = None,
    check_stale_vs_wall_clock: bool = True,
) -> tuple[ComputationResultOut | None, dict[str, Any]]:
    """
    Returns (result, rejection_event). Exactly one is truthy.
    rejection_event empty dict means no rejection.
    """
    inv = validate_observation_fields(obs)
    if inv:
        return None, _rejection_payload(inv, obs)

    site_id = str(obs["site_id"])
    seq = int(obs["sequence_id"])
    utc_raw = obs["utc"]
    if isinstance(utc_raw, datetime):
        utc = utc_raw if utc_raw.tzinfo else utc_raw.replace(tzinfo=timezone.utc)
    else:
        try:
            s = str(utc_raw).replace("Z", "+00:00")
            utc = datetime.fromisoformat(s)
            if utc.tzinfo is None:
                utc = utc.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None, _rejection_payload(ValidationResult(ObservationValidity.rejected_malformed, "invalid utc"), obs)

    prev_seq = last_sequence_by_site.get(site_id)
    if prev_seq is not None:
        if seq < prev_seq:
            return None, _rejection_payload(
                ValidationResult(ObservationValidity.rejected_out_of_order, "sequence_id decreased"), obs
            )
        if seq == prev_seq:
            return None, _rejection_payload(
                ValidationResult(ObservationValidity.rejected_duplicate, "duplicate sequence_id"), obs
            )

    prev_utc = last_utc_by_site.get(site_id)
    if prev_utc is not None and utc < prev_utc:
        return None, _rejection_payload(
            ValidationResult(ObservationValidity.rejected_out_of_order, "timestamp before previous sample"), obs
        )

    if check_stale_vs_wall_clock:
        now = wall_clock_now or datetime.now(timezone.utc)
        if (now - utc).total_seconds() > stale_seconds:
            return None, _rejection_payload(
                ValidationResult(ObservationValidity.rejected_malformed, "stale sample vs wall clock"), obs
            )

    cache = horizon_cache.get(site_id)
    if cache is None:
        return None, _rejection_payload(
            ValidationResult(ObservationValidity.rejected_malformed, "unknown site_id"), obs
        )

    sun_az = float(obs["sun_az_deg"])
    sun_el = float(obs["sun_el_deg"])
    earth_az = float(obs["earth_az_deg"])
    earth_el = float(obs["earth_el_deg"])

    sh_el, sh_known = cache.at_azimuth(sun_az)
    eh_el, eh_known = cache.at_azimuth(earth_az)

    sun_st = classify_centre_ray(sun_el, sh_el, ray_terrain_known=sh_known)
    earth_st = classify_centre_ray(earth_el, eh_el, ray_terrain_known=eh_known)

    sun_margin = (sun_el - sh_el) if sh_known and sh_el is not None else None
    earth_margin = (earth_el - eh_el) if eh_known and eh_el is not None else None

    last_sequence_by_site[site_id] = seq
    last_utc_by_site[site_id] = utc

    return (
        ComputationResultOut(
            sequence_id=seq,
            utc=utc.isoformat().replace("+00:00", "Z"),
            site_id=site_id,
            geometric_horizon_deg=GEOMETRIC_HORIZON_DEG,
            sun_az_deg=sun_az,
            sun_el_deg=sun_el,
            earth_az_deg=earth_az,
            earth_el_deg=earth_el,
            sun_state=sun_st,
            earth_state=earth_st,
            sun_margin_deg=sun_margin,
            earth_margin_deg=earth_margin,
            centre_ray_only=True,
            data_validity="accepted",
        ),
        {},
    )


def _rejection_payload(v: ValidationResult, obs: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "invalid_observation",
        "practice_data": True,
        "simulation_mode": True,
        "validity": v.validity.value,
        "detail": v.detail,
        "sequence_id": obs.get("sequence_id"),
        "site_id": obs.get("site_id"),
    }
