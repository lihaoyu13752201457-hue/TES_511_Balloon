#!/usr/bin/env python3
"""Validate Phase 11 selection upgrade guard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from make_phase11_metric_crosswalk import OUT_DEFAULT


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def validate(results: list[dict[str, str]]) -> None:
    path = OUT_DEFAULT / "selection_best_upgrade_decision.json"
    md = OUT_DEFAULT / "selection_best_upgrade_decision.md"
    if not path.exists() or not md.exists():
        add(results, "phase11_selection_upgrade_guard", "FAIL", "missing selection upgrade decision md/json")
        return
    data = read_json(path)
    states_ok = (
        data.get("state_audit") in {"AUDIT_EXECUTED", "AUDIT_NOT_EXECUTED"}
        and data.get("state_performance") in {"PERFORMANCE_REPRODUCED", "PERFORMANCE_NOT_REPRODUCED_PENDING_TEMPLATE_CROSSWALK"}
        and data.get("state_upgrade") in {"UPGRADED_TO_MAIN_ANALYSIS", "NOT_UPGRADED_TO_MAIN_ANALYSIS"}
    )
    current_expected = (
        data.get("audit_executed") is True
        and data.get("performance_reproduced") is False
        and data.get("upgraded_to_main_analysis") is False
        and data.get("criteria", {}).get("performance_threshold_reproduced") is False
        and "BGO remains event-total proxy" in data.get("primary_reason", "")
    )
    text = md.read_text(encoding="utf-8")
    wording_ok = "Not upgraded" in text and "Forbidden, not claimed: selection best replaces baseline" in text
    add(
        results,
        "phase11_selection_upgrade_guard",
        "PASS" if states_ok and current_expected and wording_ok else "FAIL",
        f"states_ok={states_ok} audit={data.get('audit_executed')} reproduced={data.get('performance_reproduced')} upgraded={data.get('upgraded_to_main_analysis')}",
    )


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
