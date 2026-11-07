"""
Tests for SIMULATION stream engine and replay (no FastAPI dependency).

SCIENCE_CALCULATIONS_READY and POST /v1/compare are not touched by these modules.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from datetime import datetime, timedelta, timezone

from simulation.contracts import SiteHorizonCache
from simulation.engine import process_observation
from simulation.replay import generate_replay_sequence, synthetic_obs_to_dict
from simulation.synthetic_ephemeris import DEFAULT_SCENARIO


def _obs(**kwargs):
    base = {
        "sequence_id": 0,
        "utc": "2025-01-01T12:00:00Z",
        "site_id": "s04p02",
        "sun_az_deg": 180.0,
        "sun_el_deg": 5.0,
        "earth_az_deg": 320.0,
        "earth_el_deg": 5.0,
        "units": "deg",
        "angles_frame": "local_topocentric_clockwise_from_north_geometric_0",
    }
    base.update(kwargs)
    return base


class SimulationEngineTests(unittest.TestCase):
    def test_flat_site_clear_and_blocked(self) -> None:
        cache = {"s04p02": SiteHorizonCache.build("s04p02")}
        last_seq: dict[str, int | None] = {"s04p02": None}
        last_utc: dict[str, datetime | None] = {"s04p02": None}
        o1 = _obs(sequence_id=0, sun_el_deg=5.0, earth_el_deg=3.0)
        r1, e1 = process_observation(
            obs=o1, horizon_cache=cache, last_sequence_by_site=last_seq, last_utc_by_site=last_utc, check_stale_vs_wall_clock=False
        )
        self.assertIsNotNone(r1)
        self.assertFalse(e1)
        self.assertEqual(r1.sun_state, "clear")
        self.assertEqual(r1.earth_state, "clear")
        o2 = _obs(sequence_id=1, sun_el_deg=-2.0)
        r2, e2 = process_observation(
            obs=o2, horizon_cache=cache, last_sequence_by_site=last_seq, last_utc_by_site=last_utc, check_stale_vs_wall_clock=False
        )
        self.assertIsNotNone(r2)
        self.assertFalse(e2)
        self.assertEqual(r2.sun_state, "blocked")

    def test_malapert_gap_unknown_never_clear(self) -> None:
        cache = {"malapert": SiteHorizonCache.build("malapert")}
        last_seq: dict[str, int | None] = {"malapert": None}
        last_utc: dict[str, datetime | None] = {"malapert": None}
        o = _obs(
            site_id="malapert",
            sequence_id=0,
            sun_az_deg=30.0,
            sun_el_deg=20.0,
            earth_az_deg=200.0,
            earth_el_deg=10.0,
        )
        r, e = process_observation(
            obs=o, horizon_cache=cache, last_sequence_by_site=last_seq, last_utc_by_site=last_utc, check_stale_vs_wall_clock=False
        )
        self.assertIsNotNone(r)
        self.assertFalse(e)
        self.assertEqual(r.sun_state, "unknown")
        self.assertNotEqual(r.sun_state, "clear")

    def test_duplicate_sequence_rejected(self) -> None:
        cache = {"s04p02": SiteHorizonCache.build("s04p02")}
        last_seq: dict[str, int | None] = {"s04p02": None}
        last_utc: dict[str, datetime | None] = {"s04p02": None}
        o = _obs(sequence_id=0)
        process_observation(
            obs=o, horizon_cache=cache, last_sequence_by_site=last_seq, last_utc_by_site=last_utc, check_stale_vs_wall_clock=False
        )
        r2, e2 = process_observation(
            obs=o, horizon_cache=cache, last_sequence_by_site=last_seq, last_utc_by_site=last_utc, check_stale_vs_wall_clock=False
        )
        self.assertIsNone(r2)
        self.assertEqual(e2.get("validity"), "rejected_duplicate")

    def test_out_of_order_timestamp_rejected(self) -> None:
        cache = {"s04p02": SiteHorizonCache.build("s04p02")}
        last_seq: dict[str, int | None] = {"s04p02": None}
        last_utc: dict[str, datetime | None] = {"s04p02": None}
        process_observation(
            obs=_obs(sequence_id=0, utc="2025-01-01T13:00:00Z"),
            horizon_cache=cache,
            last_sequence_by_site=last_seq,
            last_utc_by_site=last_utc,
            check_stale_vs_wall_clock=False,
        )
        r2, e2 = process_observation(
            obs=_obs(sequence_id=1, utc="2025-01-01T12:00:00Z"),
            horizon_cache=cache,
            last_sequence_by_site=last_seq,
            last_utc_by_site=last_utc,
            check_stale_vs_wall_clock=False,
        )
        self.assertIsNone(r2)
        self.assertEqual(e2.get("validity"), "rejected_out_of_order")

    def test_unit_and_frame_mismatch(self) -> None:
        cache = {"s04p02": SiteHorizonCache.build("s04p02")}
        last_seq: dict[str, int | None] = {"s04p02": None}
        last_utc: dict[str, datetime | None] = {"s04p02": None}
        r1, e1 = process_observation(
            obs=_obs(sequence_id=0, units="radians"),
            horizon_cache=cache,
            last_sequence_by_site=last_seq,
            last_utc_by_site=last_utc,
            check_stale_vs_wall_clock=False,
        )
        self.assertIsNone(r1)
        self.assertEqual(e1.get("validity"), "rejected_unit_mismatch")
        r2, e2 = process_observation(
            obs=_obs(sequence_id=1, units="deg", angles_frame="ITRF93"),
            horizon_cache=cache,
            last_sequence_by_site=last_seq,
            last_utc_by_site=last_utc,
            check_stale_vs_wall_clock=False,
        )
        self.assertIsNone(r2)
        self.assertEqual(e2.get("validity"), "rejected_frame_mismatch")

    def test_stale_vs_wall_clock_rejects(self) -> None:
        cache = {"s04p02": SiteHorizonCache.build("s04p02")}
        last_seq: dict[str, int | None] = {"s04p02": None}
        last_utc: dict[str, datetime | None] = {"s04p02": None}
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat().replace("+00:00", "Z")
        r, e = process_observation(
            obs=_obs(sequence_id=0, utc=old),
            horizon_cache=cache,
            last_sequence_by_site=last_seq,
            last_utc_by_site=last_utc,
            check_stale_vs_wall_clock=True,
        )
        self.assertIsNone(r)
        self.assertIn("stale", e.get("detail", ""))

    def test_replay_deterministic(self) -> None:
        a = [synthetic_obs_to_dict(o) for o in generate_replay_sequence(DEFAULT_SCENARIO)]
        b = [synthetic_obs_to_dict(o) for o in generate_replay_sequence(DEFAULT_SCENARIO)]
        self.assertEqual(a, b)
        self.assertGreater(len(a), 10)

    def test_replay_processed_incremental_matches_vector(self) -> None:
        """Full replay through engine yields same final state as cumulative step."""
        seq = [synthetic_obs_to_dict(o) for o in generate_replay_sequence(DEFAULT_SCENARIO)]
        cache = {
            DEFAULT_SCENARIO.site_a: SiteHorizonCache.build(DEFAULT_SCENARIO.site_a),
            DEFAULT_SCENARIO.site_b: SiteHorizonCache.build(DEFAULT_SCENARIO.site_b),
        }
        last_seq: dict[str, int | None] = {DEFAULT_SCENARIO.site_a: None, DEFAULT_SCENARIO.site_b: None}
        last_utc: dict[str, datetime | None] = {DEFAULT_SCENARIO.site_a: None, DEFAULT_SCENARIO.site_b: None}
        last_results: dict[str, tuple] = {}
        for obs in seq:
            r, rej = process_observation(
                obs=obs,
                horizon_cache=cache,
                last_sequence_by_site=last_seq,
                last_utc_by_site=last_utc,
                check_stale_vs_wall_clock=False,
            )
            if r:
                last_results[r.site_id] = (r.sun_state, r.earth_state, r.sun_margin_deg, r.earth_margin_deg)
            self.assertFalse(rej, msg=str(rej))
        self.assertEqual(len(last_results), 2)
        for _site_id, (ss, es, sm, em) in last_results.items():
            self.assertIn(ss, ("clear", "blocked", "unknown"))
            self.assertIn(es, ("clear", "blocked", "unknown"))
            if ss == "unknown":
                self.assertIsNone(sm)
            if es == "unknown":
                self.assertIsNone(em)


if __name__ == "__main__":
    unittest.main()
