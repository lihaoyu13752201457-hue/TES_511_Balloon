from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_run_contract


def _multibounce_demo_path() -> Path:
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/channel_4ring_multibounce_demo")


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


class Geant4Channel4RingMultiBounceDemoTest(unittest.TestCase):
    @unittest.skipUnless(_multibounce_demo_path().exists(), "channel_4ring_multibounce_demo is not built")
    def test_multibounce_demo_writes_contract_outputs_and_cam511_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            demo = _multibounce_demo_path()
            out = Path(tmp) / "channel_multibounce"
            completed = subprocess.run(
                [
                    str(demo),
                    "--n",
                    "500",
                    "--seed",
                    "20260520",
                    "--ring-config",
                    "data/channel/cam511_channel_rings.csv",
                    "--reflectivity-table",
                    "data/reflectivity/WSi_511keV_parratt_grid_dense.csv",
                    "--out",
                    str(out),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_demo_env(demo),
            )
            self.assertIn("CHANNEL_4RING_MULTIBOUNCE_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["system"], "geant4_channel_4ring_multibounce")
            self.assertEqual(summary["n_primaries"], 500)
            self.assertEqual(summary["n_primaries"], summary["n_survived"] + summary["n_absorbed"] + summary["n_leaked"])
            self.assertGreater(summary["transmissivity"], 0.72)
            self.assertLess(summary["transmissivity"], 0.88)
            self.assertGreater(summary["effective_area_cm2"], 45.0)
            self.assertLess(summary["effective_area_cm2"], 56.0)
            self.assertGreater(summary["spot_d90_cm"], 2.8)
            self.assertLess(summary["spot_d90_cm"], 4.5)
            self.assertFalse(summary["geant4_bottom_code_modified"])
            self.assertEqual(summary["schema_version"], "channel_optics_summary_v2")
            self.assertEqual(summary["model_class"], "calibrated_detector_handoff")
            self.assertTrue(summary["is_calibrated_handoff"])
            self.assertFalse(summary["is_public_wallbywall_geometry"])
            self.assertFalse(summary["is_first_principles_80pct_closure"])
            self.assertEqual(summary["path_absorption_policy"], "none")
            self.assertEqual(summary["n_path_absorbed"], 0)

            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)

    @unittest.skipUnless(_multibounce_demo_path().exists(), "channel_4ring_multibounce_demo is not built")
    def test_paper_formula_mode_records_si_path_absorption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            demo = _multibounce_demo_path()
            out = Path(tmp) / "channel_multibounce_paper_formula"
            subprocess.run(
                [
                    str(demo),
                    "--n",
                    "500",
                    "--seed",
                    "20260520",
                    "--ring-config",
                    "data/channel/cam511_channel_rings.csv",
                    "--reflectivity-table",
                    "data/reflectivity/WSi_511keV_parratt_grid_dense.csv",
                    "--theta-policy",
                    "paper_bend",
                    "--open-fraction-policy",
                    "paper_once",
                    "--path-absorption-policy",
                    "si_length",
                    "--out",
                    str(out),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_demo_env(demo),
            )
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["path_absorption_policy"], "si_length")
            self.assertGreater(summary["n_path_absorbed"], 0)
            self.assertEqual(summary["n_primaries"], summary["n_survived"] + summary["n_absorbed"] + summary["n_leaked"])
            self.assertLess(summary["transmissivity"], 0.55)
            per_ring = (out / "per_ring_summary.csv").read_text()
            self.assertIn("n_path_absorbed", per_ring.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
