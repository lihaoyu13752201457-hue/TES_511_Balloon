from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ChannelConfidenceReportTest(unittest.TestCase):
    def test_report_builds_and_separates_conservative_from_headline_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "channel_report.html"
            summary_path = Path(tmp) / "summary.json"
            subprocess.run(
                [
                    "python3",
                    "analysis/build_channel_confidence_report.py",
                    "--out",
                    str(report),
                    "--summary",
                    str(summary_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary["status"], "CHANNEL_CONFIDENCE_REPORT_BUILT")
            self.assertEqual(summary["conservative_channel_confidence"], "HIGH_CURRENT_RESEARCH_PROTOTYPE")
            self.assertEqual(summary["headline_80pct_confidence"], "MEDIUM_CALIBRATED_NOT_FIRST_PRINCIPLES")
            self.assertLess(summary["strict_vs_wallbywall_relative_delta"], 0.03)
            text = report.read_text(encoding="utf-8")
            self.assertIn("保守物理闭合 Channel 模型", text)
            self.assertIn("80% headline", text)
            self.assertIn("https://www.osti.gov/biblio/1716823", text)


if __name__ == "__main__":
    unittest.main()
