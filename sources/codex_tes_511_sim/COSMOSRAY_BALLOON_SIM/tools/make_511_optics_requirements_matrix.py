#!/usr/bin/env python3
"""Write Phase 10 optics requirements matrix and placeholder/schema YAML files."""

from __future__ import annotations

import json

from make_511_phase10_point_diffuse_report import CFG_DIR, OUT_DEFAULT, write_optics_requirements, write_optics_schema


def main() -> int:
    OUT_DEFAULT.mkdir(parents=True, exist_ok=True)
    rows = write_optics_requirements(OUT_DEFAULT)
    schema = write_optics_schema(CFG_DIR / "optics_response_511_schema.yaml", status="SCHEMA_REQUIRED_FIELDS")
    placeholder = write_optics_schema(CFG_DIR / "optics_response_511_placeholder.yaml", status="PLACEHOLDER")
    print(
        json.dumps(
            {
                "status": "PASS_PHASE10_OPTICS_REQUIREMENTS_WRITTEN",
                "requirements": len(rows),
                "schema_status": schema["metadata"]["status"],
                "placeholder_status": placeholder["metadata"]["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
