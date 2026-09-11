from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
import csv
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_phase_space, validate_run_contract


def _multiring_demo_path() -> Path:
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/laue_multiring_table_demo")


def _demo_env(demo: Path) -> dict[str, str]:
    env = dict(os.environ)
    if "opticsim-build-g4-11.4.0" in str(demo):
        for key in list(env):
            if key.startswith("G4") or key == "GEANT4_DATA_DIR":
                env.pop(key, None)
        lib = "/home/ubuntu/software/geant4-11.4.0-install/lib"
        env["LD_LIBRARY_PATH"] = lib + ":" + env.get("LD_LIBRARY_PATH", "")
        env["PATH"] = "/home/ubuntu/software/geant4-11.4.0-install/bin:" + env.get("PATH", "")
        env["GEANT4_DATA_DIR"] = "/home/ubuntu/software/geant4-11.4.0-install/share/Geant4/data"
    return env


class Geant4LaueMultiringTableDemoTest(unittest.TestCase):
    @unittest.skipUnless(_multiring_demo_path().exists(), "laue_multiring_table_demo is not built")
    def test_multiring_table_demo_writes_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            demo = _multiring_demo_path()
            out = Path(tmp) / "laue_multiring_table"
            completed = subprocess.run(
                [
                    str(demo),
                    "--n",
                    "60",
                    "--seed",
                    "20260520",
                    "--ring-config",
                    "data/laue/ge111_480_550keV_multiring_darwin_config.csv",
                    "--efficiency-table",
                    "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv",
                    "--out",
                    str(out),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_demo_env(demo),
            )
            self.assertIn("LAUE_MULTIRING_TABLE_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["n_rings"], 5)
            self.assertEqual(summary["n_primaries"], 60)
            self.assertEqual(
                summary["n_primaries"],
                summary["n_diffracted"] + summary["n_absorbed"] + summary["n_transmitted"],
            )
            self.assertFalse(summary["geant4_bottom_code_modified"])
            self.assertTrue(summary["vector_diagnostics_in_optics_history"])
            self.assertIn("table_design_focus_plane_normal", summary["plane_normal_diagnostic_model"])
            self.assertTrue((out / "laue_multiring_scene.wrl").exists())
            with (out / "optics_history.csv").open(newline="") as handle:
                fields = list(csv.DictReader(handle).fieldnames or [])
            self.assertIn("plane_normal_x", fields)
            self.assertIn("reciprocal_vector_x_invA", fields)

            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)

            transmitted_report = validate_phase_space(out / "transmitted_space.csv")
            self.assertTrue(transmitted_report.ok, transmitted_report)


if __name__ == "__main__":
    unittest.main()
