from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunLightweightCrosscheckTest(unittest.TestCase):
    def test_dry_run_lists_expected_steps(self) -> None:
        completed = subprocess.run(
            ["python3", str(ROOT / "tools/run_lightweight_crosscheck.py"), "--dry-run"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        payload = json.loads(completed.stdout)
        commands = [" ".join(command) for command in payload["commands"]]
        self.assertTrue(any("compare_geant4_vs_reference.py" in command for command in commands))
        self.assertTrue(any("audit_cosima_bridge.py" in command for command in commands))
        self.assertTrue(any("audit_full_lens_observables.py" in command for command in commands))
        self.assertTrue(any("build_python_full_lens_reference.py" in command for command in commands))
        self.assertTrue(any("export_external_lens_request.py" in command for command in commands))
        self.assertTrue(any("audit_external_lens_handoff.py" in command for command in commands))
        self.assertTrue(any("generate_crystalpy_curve.py" in command for command in commands))
        self.assertTrue(any("build_bfull_rocking_curve_map_status.py" in command for command in commands))
        self.assertTrue(commands[-1].startswith("python3 -m unittest"))


if __name__ == "__main__":
    unittest.main()
