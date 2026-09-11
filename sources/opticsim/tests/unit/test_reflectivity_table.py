from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityParams, ReflectivityTable


class ReflectivityTableTest(unittest.TestCase):
    def test_constant_table_lookup(self) -> None:
        table = ReflectivityTable.constant(stack_id="toy", E_keV=511.0, R=0.8, A=0.15, T=0.05, open_fraction=0.833)
        params = table.lookup(511.0, 1.0e-6, "toy")
        self.assertAlmostEqual(params.R + params.A + params.T, 1.0)
        self.assertAlmostEqual(params.open_fraction, 0.833)

    def test_reject_bad_sum(self) -> None:
        with self.assertRaises(ValueError):
            ReflectivityTable.constant(stack_id="bad", E_keV=511.0, R=0.8, A=0.3, T=0.0)

    def test_physical_table_rejects_silent_extrapolation(self) -> None:
        table = ReflectivityTable(
            [
                ReflectivityParams("phys", 500.0, 1.0e-6, 0.7, 0.2, 0.1, 0.8, 0.0, 5.0, "imd"),
                ReflectivityParams("phys", 520.0, 2.0e-6, 0.6, 0.25, 0.15, 0.8, 0.0, 5.0, "imd"),
            ]
        )
        with self.assertRaises(ValueError):
            table.lookup(530.0, 1.5e-6, "phys")
        with self.assertRaises(ValueError):
            table.lookup(511.0, 3.0e-6, "phys")

    def test_physical_table_interpolates_theta(self) -> None:
        table = ReflectivityTable(
            [
                ReflectivityParams("phys", 511.0, 1.0e-6, 0.8, 0.1, 0.1, 0.8, 0.0, 5.0, "imd"),
                ReflectivityParams("phys", 511.0, 3.0e-6, 0.4, 0.4, 0.2, 0.8, 0.0, 5.0, "imd"),
            ]
        )
        params = table.lookup(511.0, 2.0e-6, "phys")
        self.assertAlmostEqual(params.R, 0.6)
        self.assertAlmostEqual(params.A, 0.25)
        self.assertAlmostEqual(params.T, 0.15)
        self.assertAlmostEqual(params.R + params.A + params.T, 1.0)


if __name__ == "__main__":
    unittest.main()
