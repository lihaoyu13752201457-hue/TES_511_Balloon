from __future__ import annotations

import unittest
from pathlib import Path

from laue511.probabilities import darwin_hamilton_mosaic_probabilities
from laue511.rings import find_ring, load_ring_config


ROOT = Path(__file__).resolve().parents[1]


class ProbabilitiesTest(unittest.TestCase):
    def test_probabilities_are_conserved_without_silent_normalization(self) -> None:
        ring = find_ring(load_ring_config(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"), 2)
        result = darwin_hamilton_mosaic_probabilities(
            E_keV=ring.design_energy_keV,
            d_spacing_A=ring.d_spacing_A,
            thickness_mm=ring.thickness_mm,
        )
        self.assertFalse(result.renormalized_flag)
        self.assertGreaterEqual(result.p_diff, 0.0)
        self.assertGreaterEqual(result.p_abs, 0.0)
        self.assertGreaterEqual(result.p_trans, 0.0)
        self.assertAlmostEqual(result.prob_sum_raw, 1.0, delta=1.0e-12)
        self.assertAlmostEqual(result.p_diff, 0.2464, delta=0.002)
        self.assertAlmostEqual(result.p_abs, 0.3570, delta=0.002)

    def test_strict_mode_accepts_current_kernel_residual(self) -> None:
        ring = find_ring(load_ring_config(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"), 0)
        darwin_hamilton_mosaic_probabilities(
            E_keV=ring.design_energy_keV,
            d_spacing_A=ring.d_spacing_A,
            thickness_mm=ring.thickness_mm,
            strict=True,
        )


if __name__ == "__main__":
    unittest.main()
