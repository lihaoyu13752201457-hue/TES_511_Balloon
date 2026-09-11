from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_run_contract


class Geant4LaueOneRingDemoTest(unittest.TestCase):
    @unittest.skipUnless(Path("/tmp/opticsim-build/laue_one_ring_demo").exists(), "laue_one_ring_demo is not built")
    def test_laue_one_ring_demo_writes_optics_contract_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "laue"
            completed = subprocess.run(
                ["/tmp/opticsim-build/laue_one_ring_demo", "8", str(out), "23"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("LAUE_ONE_RING_SUMMARY", completed.stdout)
            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
