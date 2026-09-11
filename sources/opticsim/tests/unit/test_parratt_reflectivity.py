from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.parratt_reflectivity import (
    MultilayerSpec,
    compute_reflectivity_rows,
    compute_manual_parratt_rows,
    geometric_theta_grid,
    summarize_rows,
)


class ParrattReflectivityTest(unittest.TestCase):
    def test_wsi_511kev_grid_is_normalized_and_angle_sensitive(self) -> None:
        theta = geometric_theta_grid(1.0e-8, 5.0e-3, 32)
        rows = compute_reflectivity_rows(MultilayerSpec(), E_keV=511.0, theta_rad=theta)
        self.assertEqual(len(rows), 32)
        for row in rows:
            self.assertGreaterEqual(row.R, 0.0)
            self.assertGreaterEqual(row.A, 0.0)
            self.assertGreaterEqual(row.T, 0.0)
            self.assertAlmostEqual(row.R + row.A + row.T, 1.0, places=9)
        summary = summarize_rows(rows)
        self.assertGreater(summary["R_at_min_theta"], 0.99)
        self.assertLess(summary["R_at_max_theta"], 1.0e-6)
        self.assertGreater(summary["theta_R_ge_0p5_max_rad"], 5.0e-5)
        self.assertLess(summary["theta_R_ge_0p5_max_rad"], 3.0e-4)

    def test_manual_parratt_matches_xraydb_solver_for_same_stack(self) -> None:
        theta = geometric_theta_grid(1.0e-7, 5.0e-4, 48)
        spec = MultilayerSpec()
        xraydb_rows = compute_reflectivity_rows(spec, E_keV=511.0, theta_rad=theta)
        manual_rows = compute_manual_parratt_rows(spec, E_keV=511.0, theta_rad=theta)
        max_delta = max(abs(a.R - b.R) for a, b in zip(xraydb_rows, manual_rows))
        self.assertLess(max_delta, 1.0e-10)


if __name__ == "__main__":
    unittest.main()
