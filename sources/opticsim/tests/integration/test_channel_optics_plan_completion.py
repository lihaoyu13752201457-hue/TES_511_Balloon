from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ChannelOpticsPlanCompletionTest(unittest.TestCase):
    def test_plan_completion_report_records_current_channel_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "summary.json"
            record = Path(tmp) / "record.md"
            subprocess.run(
                [
                    "python3",
                    "analysis/complete_channel_optics_plan.py",
                    "--out",
                    str(out),
                    "--record",
                    str(record),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            summary = json.loads(out.read_text())
            self.assertEqual(summary["status"], "CHANNEL_PLAN_COMPLETE_CURRENT_STAGE")
            self.assertTrue(summary["contract"]["wallbywall_optics_only"]["ok"])
            self.assertTrue(summary["contract"]["wallbywall_detector_1k"]["ok"])
            statuses = {row["item"]: row["status"] for row in summary["plan_rows"]}
            self.assertEqual(
                statuses["A. Public-geometry wall-by-wall channel optics"],
                "DONE_CURRENT_STAGE",
            )
            self.assertEqual(statuses["D. IDL/IMD provenance recovery"], "OPEN_EXTERNAL_PROVENANCE")
            self.assertEqual(statuses["E. Optics-to-detector handoff"], "DONE_END_TO_END_SMOKE")
            text = record.read_text()
            self.assertIn("Geant4 calibrated multibounce remains parameterized", text)


if __name__ == "__main__":
    unittest.main()
