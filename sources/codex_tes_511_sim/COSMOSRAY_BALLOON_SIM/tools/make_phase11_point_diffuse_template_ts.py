#!/usr/bin/env python3
"""Write Phase 11 A+B vs B-only template-TS scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_phase11_metric_crosswalk import CONFIG_DIR, OUT_DEFAULT, PHASE10_DEFAULT, build_point_diffuse_template_ts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric-crosswalk", type=Path, default=OUT_DEFAULT / "metric_crosswalk_phase11.csv")
    ap.add_argument("--phase10", type=Path, default=PHASE10_DEFAULT)
    ap.add_argument("--optics", type=Path, default=CONFIG_DIR / "optics_response_511_production_schema.yaml")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT / "point_diffuse_template_TS_phase11.csv")
    args = ap.parse_args()
    rows, summary = build_point_diffuse_template_ts(args.metric_crosswalk, args.phase10, args.optics, args.out)
    summary = dict(summary)
    summary["rows"] = len(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
