from __future__ import annotations

import math
import unittest

from external_baseline.channel_raytrace_py.vector import grazing_angle_rad, specular_reflect, unit


class SpecularReflectionTest(unittest.TestCase):
    def test_flat_surface_reflection(self) -> None:
        k = unit((1.0, 0.0, -1.0))
        n = (0.0, 0.0, 1.0)
        reflected = specular_reflect(k, n)
        expected = unit((1.0, 0.0, 1.0))
        for a, b in zip(reflected, expected):
            self.assertAlmostEqual(a, b, places=12)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in reflected)), 1.0, places=12)
        self.assertAlmostEqual(grazing_angle_rad(k, n), grazing_angle_rad(reflected, n), places=12)


if __name__ == "__main__":
    unittest.main()

