#!/usr/bin/env python3
"""Validate Phase 11 metric crosswalk and number reconciliation."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from make_phase11_metric_crosswalk import CROSSWALK_FIELDS, OUT_DEFAULT, REQUIRED_METRICS


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def validate(results: list[dict[str, str]]) -> None:
    path = OUT_DEFAULT / "metric_crosswalk_phase11.csv"
    json_path = OUT_DEFAULT / "metric_crosswalk_phase11.json"
    if not path.exists() or not json_path.exists():
        add(results, "phase11_metric_crosswalk_complete", "FAIL", "missing metric_crosswalk_phase11 csv/json")
        return
    rows = read_csv(path)
    fields_ok = set(CROSSWALK_FIELDS).issubset(rows[0].keys()) if rows else False
    ids = {row["metric_id"] for row in rows}
    missing = sorted(REQUIRED_METRICS - ids)
    claim_ok = all(row["claim_level"] for row in rows) and all(row["statistic_type"] for row in rows)
    no_missing_authority = not any("MISSING_AUTHORITY" in row.values() for row in rows)
    add(
        results,
        "phase11_metric_crosswalk_complete",
        "PASS" if rows and fields_ok and not missing and claim_ok and no_missing_authority else "FAIL",
        f"rows={len(rows)} missing={missing} fields_ok={fields_ok} no_missing_authority={no_missing_authority}",
    )

    recon_md = OUT_DEFAULT / "phase10_vs_phase9_number_reconciliation.md"
    recon_json = OUT_DEFAULT / "phase10_vs_phase9_number_reconciliation.json"
    if not recon_md.exists() or not recon_json.exists():
        add(results, "phase11_number_reconciliation_complete", "FAIL", "missing reconciliation md/json")
        return
    recon = read_json(recon_json)
    by_id = {row["metric_id"]: row for row in rows}
    rb = f(by_id["P10_A_baseline_count_only_L1"], "F3_1Ms") / f(by_id["P09_A_baseline_mono_placeholder"], "F3_1Ms")
    rs = f(by_id["P10_selection_best_measured_broad_count_only"], "F3_1Ms") / f(by_id["P09_A_selection_best_design_Q"], "F3_1Ms")
    ratio_ok = (
        math.isclose(float(recon["ratio_baseline_phase10_over_phase9"]), rb, rel_tol=1e-10)
        and math.isclose(float(recon["ratio_selection_phase10_over_phase9"]), rs, rel_tol=1e-10)
        and bool(recon["common_factor_consistency"]) == (abs(rb - rs) / rb < 0.05)
        and "metric-definition change" in recon["suspected_cause"]
    )
    text = recon_md.read_text(encoding="utf-8")
    wording_ok = "Phase 10 does not contradict Phase 9" in text and "Do not write that Phase 10 overturned Phase 9" in text
    add(
        results,
        "phase11_number_reconciliation_complete",
        "PASS" if ratio_ok and wording_ok else "FAIL",
        f"baseline_ratio={rb:.6f} selection_ratio={rs:.6f} common={recon.get('common_factor_consistency')} wording_ok={wording_ok}",
    )


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
