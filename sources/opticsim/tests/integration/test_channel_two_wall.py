from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable
from external_baseline.channel_raytrace_py.two_wall import trace_two_wall_channel


class TwoWallChannelTest(unittest.TestCase):
    def test_perfect_reflector_exits(self) -> None:
        table = ReflectivityTable.constant(stack_id="toy", E_keV=511.0, R=1.0, A=0.0, T=0.0)
        result = trace_two_wall_channel(
            position_mm=(0.0, 0.0, 0.0),
            direction=(0.0, 0.2, 1.0),
            half_gap_mm=1.0,
            length_mm=20.0,
            E_keV=511.0,
            table=table,
            seed=1,
        )
        self.assertEqual(result.outcome, "EXIT")
        self.assertEqual(len(result.bounces), 2)

    def test_absorber_kills_first_hit(self) -> None:
        table = ReflectivityTable.constant(stack_id="toy", E_keV=511.0, R=0.0, A=1.0, T=0.0)
        result = trace_two_wall_channel(
            position_mm=(0.0, 0.0, 0.0),
            direction=(0.0, 0.2, 1.0),
            half_gap_mm=1.0,
            length_mm=20.0,
            E_keV=511.0,
            table=table,
            seed=1,
        )
        self.assertEqual(result.outcome, "ABSORB")
        self.assertEqual(len(result.bounces), 1)


if __name__ == "__main__":
    unittest.main()
