from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_run_contract


class Geant4DetectorOnlyDemoTest(unittest.TestCase):
    @unittest.skipUnless(Path("/tmp/opticsim-build/detector_only_demo").exists(), "detector_only_demo is not built")
    def test_detector_only_demo_writes_contract_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "phase_space.csv"
            out = tmp_path / "geant4_detector"
            with source.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["event_id", "E_keV", "x_mm", "y_mm", "z_mm", "ux", "uy", "uz", "weight", "source_tag"])
                writer.writerow([0, 511.0, 0.0, 0.0, 12000.0, 0.0, 0.0, 1.0, 1.0, "test"])
                writer.writerow([1, 511.0, 5.0, 0.0, 12000.0, 0.0, 0.0, 1.0, 1.0, "test"])
                writer.writerow([2, 511.0, 20.0, 0.0, 12000.0, 0.0, 0.0, 1.0, 1.0, "test"])

            completed = subprocess.run(
                ["/tmp/opticsim-build/detector_only_demo", str(source), str(out), "3", "17"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("DETECTOR_ONLY_SUMMARY", completed.stdout)

            report = validate_run_contract(
                phase_space=source,
                hits=out / "hits.csv",
                event_summary=out / "event_summary.csv",
            )
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
