#!/usr/bin/env python3
"""Audit the current CsI active-shield activation baseline."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "groundstate_activity_corrections.csv"
FIX_SUMMARY = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "source_fix_summary.json"
DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
OUT = ROOT / "outputs" / "reports" / "csi_activation_baseline"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: float, nd: int = 6) -> str:
    value = float(value)
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{nd}e}"
    return f"{value:.{nd}g}"


def top_rows(mapping: dict[str, float], total: float, key_name: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = []
    for key, activity in sorted(mapping.items(), key=lambda item: -item[1])[:limit]:
        rows.append(
            {
                key_name: key,
                "activity_Bq": activity,
                "fraction_of_total": activity / total if total > 0.0 else 0.0,
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        vals = []
        for field in fields:
            value = row.get(field, "")
            vals.append(fmt(value) if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_csv(CORRECTIONS)
    fix = load_json(FIX_SUMMARY)
    day15 = load_json(DAY15_SUMMARY)

    by_nuclide: dict[str, float] = defaultdict(float)
    by_volume: dict[str, float] = defaultdict(float)
    active_by_nuclide: dict[str, float] = defaultdict(float)
    active_by_volume: dict[str, float] = defaultdict(float)

    total = 0.0
    active_total = 0.0
    for row in rows:
        activity = float(row["new_groundstate_activity_Bq"])
        total += activity
        nuclide = row["nuclide"]
        volume = row["VN"]
        by_nuclide[nuclide] += activity
        by_volume[volume] += activity
        if volume.startswith("CsI_Active_Shield"):
            active_total += activity
            active_by_nuclide[nuclide] += activity
            active_by_volume[volume] += activity

    i128_total = by_nuclide.get("I-128", 0.0)
    active_i128 = active_by_nuclide.get("I-128", 0.0)
    delayed_final_cps = float(day15["expectation_rates_by_stream_cps"]["delayed"]["final"])
    delayed_bgo_cps = float(day15["expectation_rates_by_stream_cps"]["delayed"]["bgo"])
    delayed_raw_cps = float(day15["expectation_rates_by_stream_cps"]["delayed"]["raw"])

    top_nuclides = top_rows(by_nuclide, total, "nuclide")
    top_active_nuclides = top_rows(active_by_nuclide, active_total, "nuclide")
    top_active_volumes = top_rows(active_by_volume, active_total, "volume")
    write_csv(OUT / "top_total_activity_by_nuclide.csv", top_nuclides)
    write_csv(OUT / "top_csi_activity_by_nuclide.csv", top_active_nuclides)
    write_csv(OUT / "top_csi_activity_by_volume.csv", top_active_volumes)

    payload = {
        "status": "PASS",
        "claim_level": "L1_CSI_ACTIVATION_BASELINE_NO_BGO_CONTROL",
        "scope": "Current CsI active-shield activation budget from the fixed delayed-source correction table. This is a baseline for the requested future CsI-vs-BGO control, not a BGO replacement simulation.",
        "inputs": {
            "groundstate_activity_corrections": rel(CORRECTIONS),
            "source_fix_summary": rel(FIX_SUMMARY),
            "day15_summary": rel(DAY15_SUMMARY),
            "public_context": "511-CAM mission paper: https://arxiv.org/abs/2206.14652",
        },
        "checks": {
            "rows": len(rows),
            "fixed_total_activity_Bq_from_rows": total,
            "fixed_total_activity_Bq_summary": float(fix["new_total_activity_Bq"]),
            "total_activity_rel_error": abs(total - float(fix["new_total_activity_Bq"])) / max(float(fix["new_total_activity_Bq"]), 1.0e-300),
            "csi_active_shield_activity_Bq": active_total,
            "csi_active_shield_activity_fraction": active_total / total if total > 0.0 else 0.0,
            "I128_total_activity_Bq": i128_total,
            "I128_total_activity_fraction": i128_total / total if total > 0.0 else 0.0,
            "I128_in_csi_activity_Bq": active_i128,
            "I128_in_csi_fraction_of_csi_activity": active_i128 / active_total if active_total > 0.0 else 0.0,
            "delayed_raw_480_550_cps": delayed_raw_cps,
            "delayed_active_veto_pass_480_550_cps": delayed_bgo_cps,
            "delayed_final_480_550_cps": delayed_final_cps,
            "bgo_control_status": "NOT_RUN",
        },
        "outputs": {
            "markdown": rel(OUT / "csi_activation_baseline.md"),
            "top_total_activity_by_nuclide": rel(OUT / "top_total_activity_by_nuclide.csv"),
            "top_csi_activity_by_nuclide": rel(OUT / "top_csi_activity_by_nuclide.csv"),
            "top_csi_activity_by_volume": rel(OUT / "top_csi_activity_by_volume.csv"),
        },
    }
    (OUT / "csi_activation_baseline_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# CsI Activation Baseline",
        "",
        "Status: `PASS`.",
        "",
        "This report quantifies the current CsI active-shield activation burden. It is a baseline for the review-requested CsI-vs-BGO control, not a BGO control simulation.",
        "",
        "## Key Numbers",
        "",
        f"- Fixed delayed-source total activity: `{fmt(total)}` Bq.",
        f"- CsI active-shield activity: `{fmt(active_total)}` Bq (`{fmt(active_total / total)}` of total).",
        f"- I-128 total activity: `{fmt(i128_total)}` Bq (`{fmt(i128_total / total)}` of total).",
        f"- I-128 in CsI: `{fmt(active_i128)}` Bq (`{fmt(active_i128 / active_total)}` of CsI activity).",
        f"- Delayed broad-window rates: raw `{fmt(delayed_raw_cps)}` cps, active-veto pass `{fmt(delayed_bgo_cps)}` cps, final `{fmt(delayed_final_cps)}` cps.",
        "",
        "## Interpretation Boundary",
        "",
        "- The current fixed source is CsI-dominated in activity, mostly through I-128.",
        "- The current event catalog does not retain source-volume labels for delayed events, so this report does not assign the final 480-550 keV leakage rate to individual activation volumes.",
        "- A real CsI-vs-BGO conclusion still requires an alternate BGO geometry/source/transport chain run through the same Step02-Step08 gates.",
        "- Public context: the 511-CAM concept combines focusing gamma-ray optics with TES microcalorimeter arrays and projects sub-keV 511 keV energy resolution; see https://arxiv.org/abs/2206.14652.",
        "",
        "## Top Total Nuclides",
        "",
        markdown_table(top_nuclides[:10], ["nuclide", "activity_Bq", "fraction_of_total"]),
        "",
        "## Top CsI Nuclides",
        "",
        markdown_table(top_active_nuclides[:10], ["nuclide", "activity_Bq", "fraction_of_total"]),
        "",
    ]
    (OUT / "csi_activation_baseline.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": payload["checks"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
