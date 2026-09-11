#!/usr/bin/env python3
"""Fold A/B/C astrophysical source cases through placeholder optics and current response."""

from __future__ import annotations

import json

from make_511_source_case_report import build_sky_models, build_spectra, ensure_dirs, fold_source_cases, write_source_configs


def main() -> int:
    ensure_dirs()
    write_source_configs()
    build_spectra()
    build_sky_models()
    summary = fold_source_cases()
    print(json.dumps({"status": summary["status"], "out": "reports2.0/09_SOURCE_CASES_ABC/source_case_rates.csv"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
