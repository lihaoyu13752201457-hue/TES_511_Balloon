from __future__ import annotations

import unittest
from pathlib import Path

from laue511.constants import DEFAULT_FOCAL_LENGTH_MM
from laue511.focal import audit_focal_convention
from laue511.rings import load_ring_config


ROOT = Path(__file__).resolve().parents[1]


class FocalConventionTest(unittest.TestCase):
    def test_default_focal_offset_is_small_and_quantified(self) -> None:
        metrics = audit_focal_convention(
            load_ring_config(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"),
            DEFAULT_FOCAL_LENGTH_MM,
        )
        self.assertAlmostEqual(metrics["center_plane_focal_mm_mean"], 8301.499662, delta=1.0e-3)
        self.assertLess(metrics["max_abs_center_plane_radius_delta_mm"], 0.02)
        self.assertLess(metrics["max_abs_delta_theta_entry_arcsec"], 1.0)
        self.assertLess(metrics["max_abs_p_diff_delta"], 0.002)


if __name__ == "__main__":
    unittest.main()
