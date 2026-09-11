from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_run_contract


class Geant4Channel4RingEffectiveDemoTest(unittest.TestCase):
    @unittest.skipUnless(
        Path("/tmp/opticsim-build/channel_4ring_effective_demo").exists(),
        "channel_4ring_effective_demo is not built",
    )
    def test_channel_4ring_effective_demo_writes_focused_contract_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "channel"
            completed = subprocess.run(
                ["/tmp/opticsim-build/channel_4ring_effective_demo", "500", str(out), "29"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("CHANNEL_4RING_EFFECTIVE_SUMMARY", completed.stdout)
            summary = json.loads((out / "summary.json").read_text())
            self.assertGreater(summary["transmissivity"], 0.74)
            self.assertLess(summary["transmissivity"], 0.85)
            self.assertGreater(summary["spot_d90_cm"], 2.8)
            self.assertLess(summary["spot_d90_cm"], 4.4)
            report = validate_run_contract(
                phase_space=out / "phase_space.csv",
                optics_history=out / "optics_history.csv",
            )
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
