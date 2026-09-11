from __future__ import annotations

import unittest

from external_baseline.detector_response_py.detector_response import load_detector_config, pixel_index


class DetectorGeometryTest(unittest.TestCase):
    def test_pixel_index_for_center_and_edges(self) -> None:
        cfg = load_detector_config("config/detector_tes_bgo.yaml")
        absorber = cfg.absorber

        self.assertEqual(pixel_index(0.0, 0.0, absorber), (10, 10))
        self.assertEqual(pixel_index(-14.49, -14.49, absorber), (0, 0))
        self.assertEqual(pixel_index(14.49, 14.49, absorber), (19, 19))
        self.assertIsNone(pixel_index(14.5, 0.0, absorber))
        self.assertIsNone(pixel_index(0.0, -14.51, absorber))


if __name__ == "__main__":
    unittest.main()
