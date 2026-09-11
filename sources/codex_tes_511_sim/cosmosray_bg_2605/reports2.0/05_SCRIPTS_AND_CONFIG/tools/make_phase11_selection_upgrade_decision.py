#!/usr/bin/env python3
"""Write Phase 11 selection-only upgrade decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_phase11_metric_crosswalk import OUT_DEFAULT, PHASE10_DEFAULT, build_selection_upgrade_decision


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric-crosswalk", type=Path, default=OUT_DEFAULT / "metric_crosswalk_phase11.csv")
    ap.add_argument("--phase10-selection", type=Path, default=PHASE10_DEFAULT / "selection_best_measured_energy_audit.csv")
    ap.add_argument("--out-md", type=Path, default=OUT_DEFAULT / "selection_best_upgrade_decision.md")
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT / "selection_best_upgrade_decision.json")
    args = ap.parse_args()
    result = build_selection_upgrade_decision(args.metric_crosswalk, args.phase10_selection, args.out_md, args.out_json)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
