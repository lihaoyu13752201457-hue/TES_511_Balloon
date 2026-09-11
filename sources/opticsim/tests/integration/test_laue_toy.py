from __future__ import annotations

import unittest

from external_baseline.laue_raytrace_py.laue_raytrace import load_laue_config, simulate_laue, summarize_laue


class LaueToyTest(unittest.TestCase):
    def test_parameterized_focus(self) -> None:
        cfg = load_laue_config("config/laue_toy_baseline.yaml")
        events = simulate_laue(cfg, n=10000, seed=20260517)
        summary = summarize_laue(cfg, events, seed=20260517)
        self.assertEqual(summary["n_absorbed"], 0)
        self.assertEqual(summary["n_transmitted"], 0)
        self.assertEqual(summary["n_diffracted"], 10000)
        self.assertGreater(summary["spot_d90_cm"], 0.8)
        self.assertLess(summary["spot_d90_cm"], 1.3)
        self.assertAlmostEqual(summary["configured_focal_length_m"], summary["focal_length_from_first_ring_m"], delta=0.05)


if __name__ == "__main__":
    unittest.main()
