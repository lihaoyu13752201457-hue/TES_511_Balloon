from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.channel_raytrace import simulate_channel_with_reflectivity, summarize_events
from external_baseline.channel_raytrace_py.geometry import load_channel_config
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable


class ChannelReflectivityModeTest(unittest.TestCase):
    def test_constant_perfect_reflector_survives(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        table = ReflectivityTable.constant(stack_id="WSi_30_150", E_keV=511.0, R=1.0, A=0.0, T=0.0)
        events = simulate_channel_with_reflectivity(cfg, 1000, table, seed=7, fixed_theta_rad=1.0e-5)
        summary = summarize_events(cfg, events, seed=7)
        self.assertEqual(summary["n_survived"], 1000)

    def test_constant_absorber_kills(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        table = ReflectivityTable.constant(stack_id="WSi_30_150", E_keV=511.0, R=0.0, A=1.0, T=0.0)
        events = simulate_channel_with_reflectivity(cfg, 1000, table, seed=7, fixed_theta_rad=1.0e-5)
        summary = summarize_events(cfg, events, seed=7)
        self.assertEqual(summary["n_survived"], 0)
        self.assertEqual(summary["n_absorbed"], 1000)


if __name__ == "__main__":
    unittest.main()

