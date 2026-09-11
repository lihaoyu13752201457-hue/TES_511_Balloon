from __future__ import annotations

import unittest

from laue511.sampling import sample_branch_counts


class SamplingTest(unittest.TestCase):
    def test_fixed_seed_reproducible(self) -> None:
        probs = {"p_abs": 0.2, "p_diff": 0.3, "p_trans": 0.5}
        self.assertEqual(sample_branch_counts(probs, 1000, 7), sample_branch_counts(probs, 1000, 7))

    def test_branch_fractions_converge(self) -> None:
        probs = {"p_abs": 0.2, "p_diff": 0.3, "p_trans": 0.5}
        counts = sample_branch_counts(probs, 20000, 11)
        self.assertAlmostEqual(counts["ABSORB"] / 20000, probs["p_abs"], delta=0.01)
        self.assertAlmostEqual(counts["DIFFRACT"] / 20000, probs["p_diff"], delta=0.01)
        self.assertAlmostEqual(counts["TRANSMIT"] / 20000, probs["p_trans"], delta=0.01)


if __name__ == "__main__":
    unittest.main()
