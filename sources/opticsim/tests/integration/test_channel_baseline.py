from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.channel_raytrace import simulate_channel, summarize_events
from external_baseline.channel_raytrace_py.geometry import load_channel_config


class ChannelBaselineTest(unittest.TestCase):
    def test_cam511_baseline_metrics(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        events = simulate_channel(cfg, n=20000, seed=20260517)
        summary = summarize_events(cfg, events, seed=20260517)
        self.assertGreater(summary["transmissivity"], 0.79)
        self.assertLess(summary["transmissivity"], 0.81)
        self.assertGreater(summary["spot_d90_cm"], 3.3)
        self.assertLess(summary["spot_d90_cm"], 3.9)
        self.assertGreater(summary["effective_area_cm2"], 50.0)
        self.assertLess(summary["effective_area_cm2"], 51.8)


if __name__ == "__main__":
    unittest.main()

