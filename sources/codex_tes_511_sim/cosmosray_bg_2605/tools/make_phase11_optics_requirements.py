#!/usr/bin/env python3
"""Write Phase 11 optics requirements matrix v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_phase11_metric_crosswalk import EXPOSURE_S, OUT_DEFAULT, TARGET_FLUX, build_optics_requirements


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric-crosswalk", type=Path, default=OUT_DEFAULT / "metric_crosswalk_phase11.csv")
    ap.add_argument("--target-flux", type=float, default=TARGET_FLUX)
    ap.add_argument("--exposure-s", type=float, default=EXPOSURE_S)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT / "optics_requirements_matrix_v2.csv")
    args = ap.parse_args()
    rows = build_optics_requirements(args.metric_crosswalk, args.target_flux, args.exposure_s, args.out)
    print(json.dumps({"status": "PASS_PHASE11_OPTICS_REQUIREMENTS_WRITTEN", "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
