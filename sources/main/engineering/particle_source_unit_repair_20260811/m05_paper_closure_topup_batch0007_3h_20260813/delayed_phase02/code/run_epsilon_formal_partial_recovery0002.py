#!/usr/bin/env python3
"""Recovery0002 entry point for corrected epsilon delayed partial screening.

Recovery0001 is preserved as an interrupted, non-authoritative initialization
attempt whose 10,000 retained blocks were not flux-rescaled.  This entry point
uses a wholly new append-only namespace, multiplies each retained equal block
flux by five with per-cell sum-flux closure, and assigns new matched seeds.
All implementation and validation gates are inherited from the reviewed
formal partial controller; only the write namespace and fresh seeds differ.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
BASE_FILE = THIS_FILE.with_name("run_epsilon_formal_partial_recovery0001.py")


def load_base():
    spec = importlib.util.spec_from_file_location("epsilon_formal_partial_recovery0002_impl", BASE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load implementation: {BASE_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IMPL = load_base()
IMPL.THIS_FILE = THIS_FILE
IMPL.RECOVERY_ROOT = IMPL.PACKAGE_ROOT / "spectrum_epsilon_formal_partial_recovery0002"
IMPL.RECOVERY_PLAN = IMPL.RECOVERY_ROOT / "formal_partial_jobs.json"
IMPL.RECOVERY_SUMMARY = IMPL.RECOVERY_ROOT / "formal_partial_validation.json"
IMPL.FRESH_MATCHED_SEEDS = {
    "p": 2_068_810_001,
    "n": 2_068_910_001,
    "alpha": 2_069_010_001,
}


if __name__ == "__main__":
    raise SystemExit(IMPL.main())
