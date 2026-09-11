from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExternalLensHandoffTest(unittest.TestCase):
    def test_audit_removes_temporary_import_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "report"
            work_dir = Path(tmp) / "work"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/audit_external_lens_handoff.py"),
                    "--out-dir",
                    str(out_dir),
                    "--work-dir",
                    str(work_dir),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["ok"], metrics)
            self.assertTrue(metrics["work_dir_removed"])
            self.assertFalse(work_dir.exists())


if __name__ == "__main__":
    unittest.main()
