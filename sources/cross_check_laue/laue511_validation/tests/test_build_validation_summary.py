from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildValidationSummaryTest(unittest.TestCase):
    def test_status_exit_code_accepts_all_crosscheck_pass_states(self) -> None:
        module = _load_tool_module()
        self.assertEqual(module._status_exit_code("crosscheck_pass_external_lens_curve_pending"), 0)
        self.assertEqual(module._status_exit_code("crosscheck_pass_external_lens_observables_imported"), 0)
        self.assertEqual(module._status_exit_code("needs_attention"), 1)


def _load_tool_module() -> object:
    path = ROOT / "tools/build_validation_summary.py"
    spec = importlib.util.spec_from_file_location("build_validation_summary_tool", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_validation_summary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
