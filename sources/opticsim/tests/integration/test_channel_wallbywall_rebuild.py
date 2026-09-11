from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from external_baseline.channel_raytrace_py.geometry import load_channel_config
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable
from external_baseline.channel_raytrace_py.wallbywall_channel import (
    WallByWallOptions,
    simulate_wallbywall_channel,
    summarize_wallbywall,
    write_wallbywall_outputs,
)
from external_baseline.io_contract_py.io_contract import validate_run_contract


class ChannelWallByWallRebuildTest(unittest.TestCase):
    def test_constant_reflectivity_produces_natural_many_bounce_history(self) -> None:
        cfg = load_channel_config("config/cam511_channel_baseline.yaml")
        table = ReflectivityTable.constant(
            stack_id="WSi_30_150",
            E_keV=511.0,
            R=1.0,
            A=0.0,
            T=0.0,
            source="constant_toy",
        )
        options = WallByWallOptions(seed=20260521, include_si_path_absorption=False)
        events, history = simulate_wallbywall_channel(cfg, 200, table, options)
        survivors = [row for row in events if row.outcome == "EXIT"]

        self.assertGreater(len(survivors), 120)
        self.assertGreater(max(row.n_bounce for row in survivors), 10)
        self.assertGreater(sum(row.n_bounce for row in survivors) / len(survivors), 8.0)
        self.assertTrue(any(row.stage == "BOUNCE" for row in history))

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "wallbywall"
            summary = summarize_wallbywall(cfg, events, history, options, "constant_toy")
            self.assertEqual(summary["schema_version"], "channel_optics_summary_v2")
            self.assertEqual(summary["model_class"], "public_geometry_wallbywall_reconstruction")
            self.assertFalse(summary["is_calibrated_handoff"])
            self.assertTrue(summary["is_public_wallbywall_geometry"])
            self.assertFalse(summary["is_first_principles_80pct_closure"])
            write_wallbywall_outputs(out, cfg, events, history, summary)
            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
