from __future__ import annotations

import math
import unittest
from pathlib import Path

from laue511.bragg import bragg_angle_rad, focal_length_mm_from_radius, ring_radius_mm
from laue511.rings import load_ring_config


ROOT = Path(__file__).resolve().parents[1]


class BraggGeometryTest(unittest.TestCase):
    def test_511kev_ge111_angle_and_radius(self) -> None:
        theta = bragg_angle_rad(511.0, 3.266590088)
        inferred_focal = focal_length_mm_from_radius(61.661820, theta)
        self.assertAlmostEqual(math.degrees(theta), 0.213, delta=0.001)
        self.assertAlmostEqual(inferred_focal, 8301.4997, delta=0.01)
        self.assertAlmostEqual(ring_radius_mm(inferred_focal, theta), 61.661820, delta=1.0e-9)

    def test_ring_config_internal_focal_length_consistency(self) -> None:
        focals = []
        for ring in load_ring_config(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"):
            theta = bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)
            focals.append(focal_length_mm_from_radius(ring.radius_mm, theta))
        mean_focal = sum(focals) / len(focals)
        for focal in focals:
            self.assertLess(abs(focal - mean_focal) / mean_focal, 1.0e-8)


if __name__ == "__main__":
    unittest.main()
