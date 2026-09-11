#!/usr/bin/env python3
"""Run only the Phase 10 measured-energy audit for the selection-only best row."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_511_phase10_point_diffuse_report import (
    CATALOG_DEFAULT,
    FOCUSED_DEFAULT,
    MEASURED_DEFAULT,
    OUT_DEFAULT,
    audit_selection_measured_energy,
    focused_gamma_rates,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    ap.add_argument("--measured-catalog", type=Path, default=MEASURED_DEFAULT)
    ap.add_argument("--focused-gamma", type=Path, default=FOCUSED_DEFAULT)
    args = ap.parse_args()
    (args.outdir / "figures").mkdir(parents=True, exist_ok=True)
    _, summary = audit_selection_measured_energy(args.outdir, args.catalog, args.measured_catalog, focused_gamma_rates(args.focused_gamma))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
