from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SingleRingBenchmarkCliTest(unittest.TestCase):
    def test_cli_writes_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "single_ring"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/single_ring_benchmark.py"),
                    "--ring-id",
                    "2",
                    "--n-photons",
                    "200",
                    "--seed",
                    "5",
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["n_photons"], 200)
            self.assertTrue((out_dir / "phase_space.csv").exists())
            self.assertTrue((out_dir / "transmitted_space.csv").exists())


if __name__ == "__main__":
    unittest.main()
