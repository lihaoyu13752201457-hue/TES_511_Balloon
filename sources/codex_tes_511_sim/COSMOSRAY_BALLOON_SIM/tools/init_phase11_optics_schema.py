#!/usr/bin/env python3
"""Initialize the Phase 11 production optics response schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_phase11_metric_crosswalk import CONFIG_DIR, OUT_DEFAULT, init_optics_schema


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=CONFIG_DIR / "optics_response_511_production_schema.yaml")
    ap.add_argument("--copy-out", type=Path, default=OUT_DEFAULT / "optics_response_511_production_schema.yaml")
    args = ap.parse_args()
    schema = init_optics_schema(args.out, args.copy_out)
    print(json.dumps({"status": "PASS_PHASE11_OPTICS_SCHEMA_INITIALIZED", "optics_status": schema["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
