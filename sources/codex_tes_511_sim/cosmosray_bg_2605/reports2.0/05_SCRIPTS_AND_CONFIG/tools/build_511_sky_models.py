#!/usr/bin/env python3
"""Build diffuse 511-keV sky-model proxies for B source aperture folding."""

from __future__ import annotations

import json

from make_511_source_case_report import build_sky_models, ensure_dirs, write_source_configs


def main() -> int:
    ensure_dirs()
    write_source_configs()
    rows = build_sky_models()
    print(json.dumps({"status": "PASS", "sky_models": len(rows), "out": "reports2.0/09_SOURCE_CASES_ABC/diffuse_aperture_foreground.csv"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
