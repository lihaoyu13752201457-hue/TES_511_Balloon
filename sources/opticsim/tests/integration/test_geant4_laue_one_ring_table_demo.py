from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_run_contract


def _table_demo_path() -> Path:
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/laue_one_ring_table_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/laue_one_ring_table_demo")


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


class Geant4LaueOneRingTableDemoTest(unittest.TestCase):
    @unittest.skipUnless(_table_demo_path().exists(), "laue_one_ring_table_demo is not built")
    def test_regression_table_reproduces_full_diffraction_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            demo = _table_demo_path()
            out = Path(tmp) / "laue_table"
            completed = subprocess.run(
                [
                    str(demo),
                    "--n",
                    "16",
                    "--seed",
                    "23",
                    "--efficiency-table",
                    "data/laue/Ge111_511keV_regression_table.csv",
                    "--out",
                    str(out),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_demo_env(demo),
            )
            self.assertIn("LAUE_ONE_RING_TABLE_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["n_diffracted"], 16)
            self.assertEqual(summary["n_absorbed"], 0)
            self.assertEqual(summary["n_leaked"], 0)
            self.assertTrue((out / "laue_table_scene.wrl").exists())
            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
