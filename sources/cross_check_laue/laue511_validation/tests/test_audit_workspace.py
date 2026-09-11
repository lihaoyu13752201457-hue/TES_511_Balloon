from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceAuditTest(unittest.TestCase):
    def test_current_workspace_is_clean(self) -> None:
        completed = subprocess.run(
            ["python3", str(ROOT / "tools/audit_workspace.py")],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        report = json.loads(completed.stdout)
        self.assertTrue(report["ok"], report)
        self.assertLess(report["total_bytes"], 7_000_000)


if __name__ == "__main__":
    unittest.main()
