from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class BaselineFreezeTest(unittest.TestCase):
    def test_freeze_and_self_compare_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "baseline"
            subprocess.run(
                ["python3", "analysis/freeze_baseline.py", "--out", str(out)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            metrics = json.loads((out / "baseline_metrics.json").read_text())
            self.assertGreater(metrics["channel_python"]["transmissivity"], 0.79)
            self.assertLess(metrics["channel_python"]["transmissivity"], 0.81)
            self.assertEqual(metrics["wsi_crosscheck"]["status"], "PASS")
            completed = subprocess.run(
                [
                    "python3",
                    "analysis/compare_to_baseline.py",
                    "--baseline",
                    str(out / "baseline_metrics.json"),
                    "--current",
                    str(out / "baseline_metrics.json"),
                    "--out",
                    str(out / "baseline_compare_report.md"),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn('"ok": true', completed.stdout)


if __name__ == "__main__":
    unittest.main()
