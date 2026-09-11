#!/usr/bin/env python3
"""Write Phase 11 Phase10-vs-Phase9 number reconciliation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_phase11_metric_crosswalk import OUT_DEFAULT, build_number_reconciliation


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric-crosswalk", type=Path, default=OUT_DEFAULT / "metric_crosswalk_phase11.csv")
    ap.add_argument("--out-md", type=Path, default=OUT_DEFAULT / "phase10_vs_phase9_number_reconciliation.md")
    args = ap.parse_args()
    result = build_number_reconciliation(args.metric_crosswalk, args.out_md)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
