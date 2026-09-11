#!/usr/bin/env python3
"""Rebuild the constant-profile activation inventory validation products.

The nextphase constant-profile path is a normalization check: choose a constant
production rate for each day-15 activation row such that the analytic
production-decay solution reproduces the fixed day-15 activity, then evaluate
the same rows at the configured day grid.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "statistics" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
DEFAULT_ENV = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "env_grid.csv"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "inventory"
REFERENCE_DAY = 15.0
SECONDS_PER_DAY = 86400.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def day_grid(env_grid: Path) -> list[float]:
    days = sorted({float(r["day"]) for r in read_csv(env_grid) if float(r.get("day", 0.0)) > 0.0})
    return days or [1.0, 5.0, 10.0, 15.0, 20.0]


def decay_factor(half_life_s: float, time_s: float) -> float:
    lam = math.log(2.0) / half_life_s
    return -math.expm1(-lam * time_s)


def rebuild(inventory: Path, env_grid: Path, outdir: Path) -> dict[str, Any]:
    rows = read_csv(inventory)
    days = day_grid(env_grid)
    reference_time_s = REFERENCE_DAY * SECONDS_PER_DAY

    activity_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    max_day15_abs = 0.0
    max_day15_rel = 0.0

    for row in rows:
        try:
            ref_activity = float(row["Activity_Bq_after_fix"])
            half_life_s = float(row["hl_s"])
        except (KeyError, ValueError):
            skipped.append(row)
            continue
        if ref_activity < 0.0 or half_life_s <= 0.0 or not math.isfinite(half_life_s):
            skipped.append(row)
            continue

        ref_factor = decay_factor(half_life_s, reference_time_s)
        if ref_factor <= 0.0:
            skipped.append(row)
            continue
        production_atoms_s = ref_activity / ref_factor
        lam = math.log(2.0) / half_life_s

        for day in days:
            time_s = day * SECONDS_PER_DAY
            factor = decay_factor(half_life_s, time_s)
            activity = production_atoms_s * factor
            atoms = activity / lam if lam > 0.0 else 0.0
            ratio = activity / ref_activity if ref_activity else 0.0
            base = {
                "day": day,
                "time_s": time_s,
                "VN": row.get("VN", ""),
                "ZA": row.get("ZA", ""),
                "nuclide": row.get("nuclide", ""),
                "exc_keV": row.get("exc_keV", ""),
                "hl_s": half_life_s,
                "reference_activity_Bq_day15": ref_activity,
                "constant_production_atoms_s": production_atoms_s,
                "activity_Bq": activity,
                "activity_ratio_to_day15": ratio,
                "RP_yield": row.get("RP_yield", ""),
                "Points": row.get("Points", ""),
            }
            activity_rows.append(base)
            inventory_rows.append({**base, "inventory_atoms": atoms})
            if abs(day - REFERENCE_DAY) < 1.0e-9:
                diff = abs(activity - ref_activity)
                max_day15_abs = max(max_day15_abs, diff)
                if ref_activity:
                    max_day15_rel = max(max_day15_rel, diff / abs(ref_activity))

    activity_fields = [
        "day", "time_s", "VN", "ZA", "nuclide", "exc_keV", "hl_s",
        "reference_activity_Bq_day15", "constant_production_atoms_s",
        "activity_Bq", "activity_ratio_to_day15", "RP_yield", "Points",
    ]
    inventory_fields = activity_fields[:9] + ["inventory_atoms"] + activity_fields[9:]
    write_csv(outdir / "activity_by_time_nuclide_volume.csv", activity_rows, activity_fields)
    write_csv(outdir / "inventory_by_time_nuclide_volume.csv", inventory_rows, inventory_fields)

    total_rows = []
    for day in days:
        total_rows.append({
            "day": day,
            "time_s": day * SECONDS_PER_DAY,
            "total_activity_Bq": sum(float(r["activity_Bq"]) for r in activity_rows if float(r["day"]) == day),
        })
    write_csv(outdir / "total_activity_by_time.csv", total_rows, ["day", "time_s", "total_activity_Bq"])

    top_rows = []
    for day in days:
        sub = sorted((r for r in activity_rows if float(r["day"]) == day), key=lambda r: float(r["activity_Bq"]), reverse=True)
        for rank, row in enumerate(sub[:20], start=1):
            top_rows.append({
                "day": day,
                "rank": rank,
                "VN": row["VN"],
                "ZA": row["ZA"],
                "nuclide": row["nuclide"],
                "activity_Bq": row["activity_Bq"],
                "note": "activity-ranked proxy; gamma-line branching not applied",
            })
    write_csv(outdir / "top_511_related_nuclides_by_day.csv", top_rows, ["day", "rank", "VN", "ZA", "nuclide", "activity_Bq", "note"])

    plt.figure(figsize=(7.2, 4.6))
    plt.plot([r["day"] for r in total_rows], [r["total_activity_Bq"] for r in total_rows], marker="o")
    plt.xlabel("Flight day")
    plt.ylabel("Total activity (Bq)")
    plt.title("Constant-profile activation inventory")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outdir / "total_activity_by_time.png", dpi=180)
    plt.close()

    ref_total = sum(float(r["Activity_Bq_after_fix"]) for r in rows if r not in skipped)
    day15_total = next((float(r["total_activity_Bq"]) for r in total_rows if abs(float(r["day"]) - REFERENCE_DAY) < 1.0e-9), float("nan"))
    abs_diff = abs(day15_total - ref_total)
    rel_diff = abs_diff / abs(ref_total) if ref_total else 0.0
    summary = {
        "status": "PASS" if rel_diff < 1.0e-12 and max_day15_rel < 1.0e-12 else "FAIL",
        "mode": "constant_profile_inventory",
        "inventory_input": rel(inventory),
        "environment_grid": rel(env_grid),
        "activity_column": "Activity_Bq_after_fix",
        "reference_day": REFERENCE_DAY,
        "days": days,
        "n_input_rows": len(rows),
        "n_used_rows": len(rows) - len(skipped),
        "n_skipped_rows": len(skipped),
        "environment_scale_min": 1.0,
        "environment_scale_max": 1.0,
        "reference_total_activity_Bq": ref_total,
        "generated_reference_day_total_activity_Bq": day15_total,
        "reference_total_abs_diff_Bq": abs_diff,
        "reference_total_rel_diff": rel_diff,
        "max_day15_row_abs_diff_Bq": max_day15_abs,
        "max_day15_row_rel_diff": max_day15_rel,
        "plot_written": True,
        "caveat": "Constant-profile ODE validation only; parent feeding and real flight environment scaling are not yet modeled.",
    }
    (outdir / "constant_limit_validation.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = f"""# Constant-profile activation inventory validation

Status: `{summary['status']}`

- Input inventory: `{rel(inventory)}`
- Reference day: `{REFERENCE_DAY}`
- Used rows: `{summary['n_used_rows']}` / `{summary['n_input_rows']}`
- Environment scale range: `1.0` to `1.0`
- Reference total activity: `{ref_total:.12g}` Bq
- Reconstructed day-15 total activity: `{day15_total:.12g}` Bq
- Total relative difference: `{rel_diff:.3e}`
- Maximum row relative difference at day 15: `{max_day15_rel:.3e}`

This validates the constant-production ODE normalization against the corrected
day-15 fixed inventory. It is not yet a real day1-day20 flight profile model.
"""
    (outdir / "constant_profile_inventory_summary.md").write_text(md, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--env-grid", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(rebuild(args.inventory, args.env_grid, args.out), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
