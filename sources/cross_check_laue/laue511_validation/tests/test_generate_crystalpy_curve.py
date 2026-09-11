from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GenerateCrystalPyCurveTest(unittest.TestCase):
    def test_generator_smoke_writes_valid_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "crystalpy"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/generate_crystalpy_curve.py"),
                    "--out-dir",
                    str(out_dir),
                    "--n-angle",
                    "5",
                    "--scan-min-urad",
                    "-2",
                    "--scan-max-urad",
                    "2",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["n_rows"], 5)
            self.assertTrue((out_dir / "ge111_511keV_crystalpy_laue_curve.csv").exists())


if __name__ == "__main__":
    unittest.main()
