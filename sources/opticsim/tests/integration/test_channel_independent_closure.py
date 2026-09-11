from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ChannelIndependentClosureTest(unittest.TestCase):
    def test_independent_closure_records_no_fudge_gap_to_cam511(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            html_path = Path(tmp) / "closure.html"
            subprocess.run(
                [
                    "python3",
                    "analysis/build_channel_independent_closure.py",
                    "--n",
                    "80",
                    "--roughness-nm",
                    "5",
                    "--summary",
                    str(summary_path),
                    "--html",
                    str(html_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary["status"], "INDEPENDENT_CLOSURE_COMPLETE")
            self.assertFalse(summary["no_fudge_reaches_cam511"])
            self.assertEqual(summary["optical_constant_checks"]["status"], "PASS")
            self.assertTrue(
                all(row["status"] == "PASS" for row in summary["reflectivity_algorithm_checks"])
            )
            self.assertIn("80% headline", summary["closure_statement"])
            text = html_path.read_text(encoding="utf-8")
            self.assertIn("CAM511 80% headline", text)
            self.assertIn("IMD/DarpanX-equivalent", text)


if __name__ == "__main__":
    unittest.main()
