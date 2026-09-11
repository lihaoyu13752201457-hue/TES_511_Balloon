from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _guan_demo_path() -> Path:
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/laue_multiring_darwin_guan_demo")


class Geant4DarwinGuanSensitivityTest(unittest.TestCase):
    @unittest.skipUnless(_guan_demo_path().exists(), "laue_multiring_darwin_guan_demo is not built")
    def test_sensitivity_runner_uses_online_backend_and_changes_with_mosaic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sensitivity"
            subprocess.run(
                [
                    "python3",
                    "analysis/scan_geant4_darwin_guan_sensitivity.py",
                    "--n",
                    "2000",
                    "--seed",
                    "20260522",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["ok"])
            self.assertTrue(summary["all_cases_online_backend"])
            by_case = {row["case"]: row for row in summary["rows"]}
            self.assertGreater(
                by_case["mosaic_narrow"]["diffraction_fraction"],
                by_case["mosaic_wide"]["diffraction_fraction"],
            )
            self.assertLess(
                by_case["mosaic_narrow"]["spot_d90_cm"],
                by_case["mosaic_wide"]["spot_d90_cm"],
            )
            self.assertTrue((out / "GEANT4_DARWIN_GUAN_SENSITIVITY_CHECK.md").exists())


if __name__ == "__main__":
    unittest.main()
