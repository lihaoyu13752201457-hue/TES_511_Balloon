#!/usr/bin/env python3
"""Validate Phase 11 claim-control wording."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from make_phase11_metric_crosswalk import ALLOWING_GUARDS, FORBIDDEN_PHRASES, OUT_DEFAULT


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def line_allowed(line: str) -> bool:
    low = line.lower()
    return any(guard in low for guard in ALLOWING_GUARDS)


def validate(results: list[dict[str, str]]) -> None:
    md = OUT_DEFAULT / "claim_control_phase11.md"
    js = OUT_DEFAULT / "claim_control_phase11.json"
    if not md.exists() or not js.exists():
        add(results, "phase11_claim_control_guard", "FAIL", "missing claim-control md/json")
        return
    data = read_json(js)
    bad: list[str] = []
    checked_files = [
        OUT_DEFAULT / "README.md",
        OUT_DEFAULT / "phase10_vs_phase9_number_reconciliation.md",
        OUT_DEFAULT / "selection_best_upgrade_decision.md",
        OUT_DEFAULT / "claim_control_phase11.md",
    ]
    for path in checked_files:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for phrase in FORBIDDEN_PHRASES:
                if phrase.lower() in line.lower() and not line_allowed(line):
                    bad.append(f"{path.name}:{lineno}:{phrase}")
    data_ok = data.get("status") == "PASS_PHASE11_CLAIM_CONTROL" and set(FORBIDDEN_PHRASES).issubset(set(data.get("guard_phrases", [])))
    add(
        results,
        "phase11_claim_control_guard",
        "PASS" if data_ok and not bad else "FAIL",
        f"data_ok={data_ok} dangerous_hits={bad[:5]}",
    )


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
