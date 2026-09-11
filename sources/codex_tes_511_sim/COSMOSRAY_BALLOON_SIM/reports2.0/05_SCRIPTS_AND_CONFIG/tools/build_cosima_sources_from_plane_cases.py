#!/usr/bin/env python3
"""Build point-source Cosima source candidates for A/C source cases."""

from __future__ import annotations

import json

from make_511_source_case_report import build_cosima_sources, build_spectra, ensure_dirs, write_source_configs


def main() -> int:
    ensure_dirs()
    write_source_configs()
    build_spectra()
    rows = build_cosima_sources()
    print(json.dumps({"status": "PASS", "rows": len(rows), "out": "reports2.0/09_SOURCE_CASES_ABC/cosima_source_manifest.csv"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
