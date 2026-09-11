from __future__ import annotations

import math
import unittest

from external_baseline.laue_raytrace_py.bragg import bragg_angle_rad, focal_length_m_from_radius_cm, ring_radius_cm_from_focal_length_m, wavelength_A


class BraggGeometryTest(unittest.TestCase):
    def test_511kev_ge111_ring_radius(self) -> None:
        theta = bragg_angle_rad(511.0, 3.266)
        self.assertAlmostEqual(wavelength_A(511.0), 0.0242630525, places=9)
        radius_cm = ring_radius_cm_from_focal_length_m(8.3, theta)
        self.assertAlmostEqual(radius_cm, 6.17, delta=0.03)
        focal_m = focal_length_m_from_radius_cm(radius_cm, theta)
        self.assertAlmostEqual(focal_m, 8.3, places=10)


if __name__ == "__main__":
    unittest.main()
