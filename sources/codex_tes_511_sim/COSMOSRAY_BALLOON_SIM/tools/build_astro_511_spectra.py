#!/usr/bin/env python3
"""Build A/B/C 511-keV source spectra for the source-case layer."""

from __future__ import annotations

import json

from make_511_source_case_report import build_spectra, ensure_dirs, rel, write_source_configs


def main() -> int:
    ensure_dirs()
    write_source_configs()
    rows = build_spectra()
    print(json.dumps({"status": "PASS", "spectra": len(rows), "out": "reports2.0/09_SOURCE_CASES_ABC/source_spectrum_summary.csv"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
