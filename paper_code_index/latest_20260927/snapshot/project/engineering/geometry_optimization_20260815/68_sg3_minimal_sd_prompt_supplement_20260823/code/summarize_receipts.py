#!/usr/bin/env python3
"""Summarize small PASS receipts across the retained three data strata."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


TARGET = 16_415_399
ROOTS = {
    "sg3_old_full_sd": Path(
        "/mnt/data/TES_Balloon_511_data/SG3/m05new_zero_prompt_supplement_20260823_v1"
    ),
    "sg3_new_minimal": Path(
        "/mnt/data/TES_Balloon_511_data/SG3/m05new_zero_prompt_minimal_supplement_20260823_v1"
    ),
    "sh3": Path(
        "/mnt/data/TES_Balloon_511_data/SH3/m05new_zero_prompt_supplement_20260823_v1"
    ),
}


def main() -> int:
    layers = {}
    families = defaultdict(int)
    total_events = 0
    total_receipts = 0
    for label, root in ROOTS.items():
        rows = []
        for path in root.glob("*/run/receipts/*.json"):
            row = json.loads(path.read_text())
            if row.get("status") == "PASS":
                rows.append(row)
        events = sum(int(row["events"]) for row in rows)
        layers[label] = {"events": events, "receipts": len(rows)}
        total_events += events
        total_receipts += len(rows)
        for row in rows:
            families[f"{label}:{row['family']}"] += int(row["events"])
    payload = {
        "target_events": TARGET,
        "pass_events": total_events,
        "remaining_events": TARGET - total_events,
        "fraction": total_events / TARGET,
        "pass_receipts": total_receipts,
        "layers": layers,
        "families": dict(sorted(families.items())),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
