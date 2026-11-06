"""
Structural semantics tests for centre-ray vs terrain horizon classification.

This is a toy local-plane model for teaching and regression tests only. It is
not production lunar geodesy, frame-accurate ephemeris, or a validated horizon.
"""

from __future__ import annotations

import math
import unittest


def classify_centre_ray(
    target_elevation_deg: float,
    terrain_horizon_elevation_deg: float | None,
    *,
    ray_terrain_known: bool,
) -> str:
    """
    State contract (see docs/ENGINE_CALCULATION_PIPELINE.md):

    - clear: ray terrain known and target strictly above terrain horizon
    - blocked: ray terrain known and target at or below terrain horizon
    - unknown: required terrain missing/masked — must not collapse to clear
    """
    if not ray_terrain_known or terrain_horizon_elevation_deg is None:
        return "unknown"
    if math.isnan(target_elevation_deg) or math.isnan(terrain_horizon_elevation_deg):
        return "unknown"
    if target_elevation_deg > terrain_horizon_elevation_deg:
        return "clear"
    return "blocked"


def terrain_horizon_local_plane_flat() -> tuple[float, bool]:
    """Flat plane: terrain silhouette at observer is 0° elevation; fully known."""
    return 0.0, True


def terrain_horizon_ridge_sector(
    observer_azimuth_deg: float,
    *,
    ridge_low_deg: float,
    ridge_high_deg: float,
    ridge_horizon_deg: float,
) -> tuple[float, bool]:
    """Raised horizon inside an azimuth sector; known everywhere."""
    a = observer_azimuth_deg % 360.0
    in_ridge = ridge_low_deg <= a <= ridge_high_deg
    return (ridge_horizon_deg if in_ridge else 0.0), True


def terrain_horizon_masked_sector(
    observer_azimuth_deg: float,
    *,
    gap_low_deg: float,
    gap_high_deg: float,
) -> tuple[float | None, bool]:
    """No valid terrain samples in gap sector → unknown on that ray."""
    a = observer_azimuth_deg % 360.0
    if gap_low_deg <= a <= gap_high_deg:
        return None, False
    return 0.0, True


class HorizonVisibilitySemanticsTests(unittest.TestCase):
    def test_flat_terrain_zero_horizon_clear_and_blocked(self) -> None:
        h_terr, known = terrain_horizon_local_plane_flat()
        self.assertTrue(known)
        self.assertEqual(h_terr, 0.0)
        self.assertEqual(
            classify_centre_ray(5.0, h_terr, ray_terrain_known=known), "clear"
        )
        self.assertEqual(
            classify_centre_ray(-2.0, h_terr, ray_terrain_known=known), "blocked"
        )
        self.assertEqual(
            classify_centre_ray(0.0, h_terr, ray_terrain_known=known), "blocked"
        )

    def test_ridge_blocks_target_below_silhouette(self) -> None:
        az = 90.0
        h_terr, known = terrain_horizon_ridge_sector(
            az, ridge_low_deg=80.0, ridge_high_deg=100.0, ridge_horizon_deg=10.0
        )
        self.assertTrue(known)
        self.assertEqual(h_terr, 10.0)
        self.assertEqual(
            classify_centre_ray(5.0, h_terr, ray_terrain_known=known), "blocked"
        )
        self.assertEqual(
            classify_centre_ray(10.0, h_terr, ray_terrain_known=known), "blocked"
        )
        self.assertEqual(
            classify_centre_ray(11.0, h_terr, ray_terrain_known=known), "clear"
        )

    def test_nodata_sector_unknown_never_clear(self) -> None:
        az = 210.0
        h_terr, known = terrain_horizon_masked_sector(
            az, gap_low_deg=200.0, gap_high_deg=220.0
        )
        self.assertFalse(known)
        self.assertIsNone(h_terr)
        self.assertEqual(
            classify_centre_ray(15.0, h_terr, ray_terrain_known=known), "unknown"
        )
        self.assertEqual(
            classify_centre_ray(-5.0, h_terr, ray_terrain_known=known), "unknown"
        )


if __name__ == "__main__":
    unittest.main()
