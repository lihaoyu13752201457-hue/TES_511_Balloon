from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
import csv
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_phase_space, validate_run_contract


ROOT = Path(__file__).resolve().parents[2]


def _guan_demo_path() -> Path:
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/laue_multiring_darwin_guan_demo")


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


class Geant4LaueDarwinGuanDemoTest(unittest.TestCase):
    @unittest.skipUnless(_guan_demo_path().exists(), "laue_multiring_darwin_guan_demo is not built")
    def test_darwin_guan_process_writes_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            demo = _guan_demo_path()
            out = Path(tmp) / "laue_darwin_guan"
            completed = subprocess.run(
                [
                    str(demo),
                    "--n",
                    "80",
                    "--seed",
                    "20260521",
                    "--ring-config",
                    "data/laue/ge111_480_550keV_multiring_darwin_config.csv",
                    "--efficiency-table",
                    "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_demo_env(demo),
            )
            self.assertIn("LAUE_DARWIN_GUAN_PROCESS_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["system"], "geant4_laue_darwin_guan_process")
            self.assertEqual(summary["n_rings"], 5)
            self.assertEqual(summary["n_primaries"], 80)
            self.assertEqual(
                summary["n_primaries"],
                summary["n_diffracted"] + summary["n_absorbed"] + summary["n_transmitted"],
            )
            self.assertTrue(summary["model_process_split"])
            self.assertFalse(summary["registered_in_geant4_em_category"])
            self.assertFalse(summary["uses_external_efficiency_table_for_physics"])
            self.assertIn("Darwin-Hamilton mosaic", summary["online_physics_backend"])
            self.assertIn("GuanStyleLaueBraggProcess", summary["registered_process"])
            self.assertTrue(summary["vector_diagnostics_in_optics_history"])
            self.assertIn("guan_virtual_crystallite_plane_normal", summary["plane_normal_diagnostic_model"])
            with (out / "optics_history.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            diffracted = [row for row in rows if row["stage"] == "DIFFRACT"]
            self.assertTrue(diffracted)
            self.assertIn("plane_normal_x", rows[0])
            self.assertLess(
                max(float(row["angle_code_vs_recorded_reflect_rad"]) for row in diffracted),
                1.0e-7,
            )

            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)

            transmitted_report = validate_phase_space(out / "transmitted_space.csv")
            self.assertTrue(transmitted_report.ok, transmitted_report)


if __name__ == "__main__":
    unittest.main()
