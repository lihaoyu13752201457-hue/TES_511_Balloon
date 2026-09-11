from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.channel_raytrace import simulate_channel_with_reflectivity, summarize_events_by_ring
from external_baseline.channel_raytrace_py.geometry import load_channel_config
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable


class ChannelRingCalibratedTest(unittest.TestCase):
    def test_ring_calibrated_policy_uses_ring_theta_map(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        table = ReflectivityTable.constant(stack_id="WSi_30_150", E_keV=511.0, R=1.0, A=0.0, T=0.0)
        theta_map = {ring.id: 1.0e-5 * (ring.id + 1) for ring in cfg.rings}
        events = simulate_channel_with_reflectivity(
            cfg,
            2000,
            table,
            seed=13,
            theta_policy="ring_calibrated",
            ring_theta_rad=theta_map,
        )
        per_ring = summarize_events_by_ring(cfg, events)
        self.assertEqual(sum(row["n_survived"] for row in per_ring), 2000)


if __name__ == "__main__":
    unittest.main()
