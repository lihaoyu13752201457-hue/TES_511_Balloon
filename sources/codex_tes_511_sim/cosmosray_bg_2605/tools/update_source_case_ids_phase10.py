#!/usr/bin/env python3
"""Write Phase 10 A/B/C source-case identifiers and optics placeholder schema."""

from __future__ import annotations

import json
from pathlib import Path

from make_511_phase10_point_diffuse_report import CFG_DIR, update_source_case_ids, write_optics_schema


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    source_cases = CFG_DIR / "source_cases_511_ABC.yaml"
    source_cases_v2 = CFG_DIR / "source_cases_511_ABC_v2.yaml"
    schema = CFG_DIR / "optics_response_511_schema.yaml"
    placeholder = CFG_DIR / "optics_response_511_placeholder.yaml"
    cfg = update_source_case_ids(source_cases, source_cases_v2)
    write_optics_schema(schema, status="SCHEMA_REQUIRED_FIELDS")
    write_optics_schema(placeholder, status="PLACEHOLDER")
    print(
        json.dumps(
            {
                "status": "PASS_PHASE10_SOURCE_CASE_IDS_UPDATED",
                "source_cases_v2": str(source_cases_v2.relative_to(ROOT)),
                "optics_schema": str(schema.relative_to(ROOT)),
                "optics_placeholder": str(placeholder.relative_to(ROOT)),
                "case_ids": [case.get("case_id") for case in cfg.get("cases", [])],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
