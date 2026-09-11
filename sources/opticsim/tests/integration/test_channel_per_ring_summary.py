from __future__ import annotations

import unittest

from external_baseline.channel_raytrace_py.channel_raytrace import simulate_channel, summarize_events_by_ring
from external_baseline.channel_raytrace_py.geometry import load_channel_config


class ChannelPerRingSummaryTest(unittest.TestCase):
    def test_per_ring_summary_covers_all_four_rings(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        events = simulate_channel(cfg, n=5000, seed=11)
        summary = summarize_events_by_ring(cfg, events)
        self.assertEqual([row["ring_id"] for row in summary], [0, 1, 2, 3])
        self.assertEqual(sum(row["n_primaries"] for row in summary), 5000)
        self.assertGreater(sum(row["effective_area_contribution_cm2"] for row in summary), 0.0)


if __name__ == "__main__":
    unittest.main()
