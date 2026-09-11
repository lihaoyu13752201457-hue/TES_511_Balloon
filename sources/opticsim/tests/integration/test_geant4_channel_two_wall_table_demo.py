from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


EXE = Path("/tmp/opticsim-build/channel_two_wall_table_demo")


class Geant4ChannelTwoWallTableDemoTest(unittest.TestCase):
    @unittest.skipUnless(EXE.exists(), "channel_two_wall_table_demo is not built")
    def test_constant_modes_have_expected_boundary_counts(self) -> None:
        cases = [
            (["--R", "1", "--A", "0", "--T", "0"], 6, 6, 0, 0),
            (["--R", "0", "--A", "1", "--T", "0"], 3, 0, 3, 0),
            (["--R", "0", "--A", "0", "--T", "1"], 3, 0, 0, 3),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for i, (rat_args, n_boundary, n_reflect, n_absorb, n_leak) in enumerate(cases):
                out = Path(tmp) / f"case_{i}"
                completed = subprocess.run(
                    [str(EXE), "--n", "3", "--out", str(out), *rat_args],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self.assertIn("CHANNEL_TWO_WALL_TABLE_SUMMARY", completed.stdout)
                summary = json.loads((out / "summary.json").read_text())
                self.assertEqual(summary["n_boundary"], n_boundary)
                self.assertEqual(summary["n_reflect"], n_reflect)
                self.assertEqual(summary["n_absorb"], n_absorb)
                self.assertEqual(summary["n_leak"], n_leak)

    @unittest.skipUnless(EXE.exists(), "channel_two_wall_table_demo is not built")
    def test_table_mode_writes_boundary_history_and_matches_expected_survival(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "table"
            subprocess.run(
                [
                    str(EXE),
                    "--n",
                    "1000",
                    "--energy-keV",
                    "511",
                    "--theta-rad",
                    "1.5e-4",
                    "--reflectivity-table",
                    "data/reflectivity/WSi_511keV_parratt_grid.csv",
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
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["model"], "table_driven_RAT")
            self.assertGreater(summary["n_boundary"], 1500)
            with (out / "optics_history.csv").open() as f:
                n_history_rows = sum(1 for _ in f) - 1
            self.assertEqual(n_history_rows, summary["n_boundary"])
            expected_survival = summary["expected_R"] ** 2
            self.assertLess(abs(summary["survival_fraction"] - expected_survival), 0.08)


if __name__ == "__main__":
    unittest.main()
