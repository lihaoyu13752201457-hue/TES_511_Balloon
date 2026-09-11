from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


EXE = Path("/tmp/opticsim-build/channel_single_curved_demo")


class Geant4ChannelSingleCurvedDemoTest(unittest.TestCase):
    @unittest.skipUnless(EXE.exists(), "channel_single_curved_demo is not built")
    def test_single_curved_constant_reflector_writes_optics_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "curved"
            completed = subprocess.run(
                [
                    str(EXE),
                    "--n",
                    "5",
                    "--R",
                    "1",
                    "--A",
                    "0",
                    "--T",
                    "0",
                    "--segments",
                    "64",
                    "--bend-angle-rad",
                    "0.003833333333",
                    "--out",
                    str(out),
                    "--seed",
                    "20260517",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("CHANNEL_SINGLE_CURVED_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["model"], "segmented_curved_constant_RAT")
            self.assertEqual(summary["n_survived"], 5)
            self.assertGreater(summary["n_reflect"], 0)
            self.assertGreater(summary["mean_grazing_angle_rad"], 0.0)
            with (out / "optics_history.csv").open() as f:
                n_history_rows = sum(1 for _ in f) - 1
            self.assertEqual(n_history_rows, summary["n_boundary"])
            with (out / "phase_space.csv").open() as f:
                n_phase_rows = sum(1 for _ in f) - 1
            self.assertEqual(n_phase_rows, summary["n_survived"])


if __name__ == "__main__":
    unittest.main()
