#!/usr/bin/env python3
"""Integrate a constant-profile activation inventory from the fixed day-15 table.

The current production chain gives a corrected day-15 activity table after the
W183/W180 ground-state fix.  For the Phase-2 constant-limit gate we invert the
closed-form activation equation at day 15, recover a constant production rate,
and re-integrate the inventory to selected days.  Day 15 must reproduce the
reference table to numerical precision.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "reports" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
DEFAULT_ENV_GRID = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "env_grid.csv"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "inventory"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_days(text: str) -> list[float]:
    days = []
    for item in text.split(","):
        item = item.strip()
        if item:
            days.append(float(item))
    return sorted(set(days))


def activity_col(rows: list[dict[str, str]]) -> str:
    if not rows:
        raise SystemExit("empty inventory")
    names = rows[0].keys()
    if "Activity_Bq_after_fix" in names:
        return "Activity_Bq_after_fix"
    if "Activity_Bq" in names:
        return "Activity_Bq"
    raise SystemExit("inventory has no Activity_Bq_after_fix or Activity_Bq column")


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def production_rate_from_reference(activity_bq: float, half_life_s: float, reference_day: float) -> float:
    if activity_bq <= 0.0 or half_life_s <= 0.0 or not math.isfinite(half_life_s):
        return 0.0
    lam = math.log(2.0) / half_life_s
    denom = -math.expm1(-lam * reference_day * 86400.0)
    if denom <= 0.0:
        return 0.0
    return activity_bq / denom


def activity_at_day(production_rate_atoms_s: float, half_life_s: float, day: float) -> tuple[float, float]:
    if production_rate_atoms_s <= 0.0 or half_life_s <= 0.0 or not math.isfinite(half_life_s):
        return 0.0, 0.0
    lam = math.log(2.0) / half_life_s
    activity = production_rate_atoms_s * (-math.expm1(-lam * day * 86400.0))
    inventory_atoms = activity / lam if lam > 0.0 else 0.0
    return inventory_atoms, activity


def plot_total_activity(path: Path, total_rows: list[dict[str, object]]) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return False
    days = [float(r["day"]) for r in total_rows]
    totals = [float(r["total_activity_Bq"]) for r in total_rows]
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.plot(days, totals, marker="o")
    ax.set_xlabel("Day")
    ax.set_ylabel("Total activity (Bq)")
    ax.set_title("Constant-profile activation inventory")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return True


def integrate_inventory(inventory: Path, env_grid: Path, outdir: Path, days: list[float], reference_day: float) -> dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(inventory)
    col = activity_col(rows)

    if env_grid.exists():
        env_rows = read_csv(env_grid)
        scale_values = [safe_float(r.get("scale_to_ref", "1"), 1.0) for r in env_rows]
        scale_min = min(scale_values) if scale_values else 1.0
        scale_max = max(scale_values) if scale_values else 1.0
    else:
        env_rows = []
        scale_min = scale_max = 1.0

    activity_rows: list[dict[str, object]] = []
    inventory_rows: list[dict[str, object]] = []
    top_rows: list[dict[str, object]] = []
    total_by_day: dict[float, float] = defaultdict(float)
    max_day15_abs_diff = 0.0
    max_day15_rel_diff = 0.0
    n_used = 0
    n_skipped = 0

    for row in rows:
        ref_activity = safe_float(row.get(col, "0"))
        half_life_s = safe_float(row.get("hl_s", "0"))
        if ref_activity <= 0.0 or half_life_s <= 0.0 or not math.isfinite(half_life_s):
            n_skipped += 1
            continue
        prod = production_rate_from_reference(ref_activity, half_life_s, reference_day)
        if prod <= 0.0:
            n_skipped += 1
            continue
        n_used += 1
        base = {
            "VN": row.get("VN", ""),
            "ZA": row.get("ZA", ""),
            "nuclide": row.get("nuclide", ""),
            "exc_keV": row.get("exc_keV", ""),
            "hl_s": half_life_s,
            "reference_activity_Bq_day15": ref_activity,
            "constant_production_atoms_s": prod,
            "RP_yield": row.get("RP_yield", ""),
            "Points": row.get("Points", ""),
        }
        for day in days:
            inv_atoms, activity = activity_at_day(prod, half_life_s, day)
            ratio = activity / ref_activity if ref_activity > 0.0 else 0.0
            activity_rec = {
                **base,
                "day": day,
                "time_s": day * 86400.0,
                "activity_Bq": activity,
                "activity_ratio_to_day15": ratio,
            }
            inventory_rec = {
                **base,
                "day": day,
                "time_s": day * 86400.0,
                "inventory_atoms": inv_atoms,
                "activity_Bq": activity,
                "activity_ratio_to_day15": ratio,
            }
            activity_rows.append(activity_rec)
            inventory_rows.append(inventory_rec)
            total_by_day[day] += activity
            if abs(day - reference_day) < 1.0e-9:
                abs_diff = abs(activity - ref_activity)
                rel_diff = abs_diff / ref_activity if ref_activity else 0.0
                max_day15_abs_diff = max(max_day15_abs_diff, abs_diff)
                max_day15_rel_diff = max(max_day15_rel_diff, rel_diff)

    total_rows = [
        {"day": day, "time_s": day * 86400.0, "total_activity_Bq": total_by_day.get(day, 0.0)}
        for day in days
    ]
    for day in days:
        day_rows = [r for r in activity_rows if abs(float(r["day"]) - day) < 1.0e-9]
        for rank, rec in enumerate(sorted(day_rows, key=lambda r: float(r["activity_Bq"]), reverse=True)[:20], 1):
            top_rows.append({
                "day": day,
                "rank": rank,
                "VN": rec["VN"],
                "ZA": rec["ZA"],
                "nuclide": rec["nuclide"],
                "activity_Bq": rec["activity_Bq"],
                "note": "activity-ranked proxy; gamma-line branching not applied",
            })

    activity_fields = [
        "day", "time_s", "VN", "ZA", "nuclide", "exc_keV", "hl_s",
        "reference_activity_Bq_day15", "constant_production_atoms_s",
        "activity_Bq", "activity_ratio_to_day15", "RP_yield", "Points",
    ]
    inventory_fields = [
        "day", "time_s", "VN", "ZA", "nuclide", "exc_keV", "hl_s",
        "reference_activity_Bq_day15", "constant_production_atoms_s",
        "inventory_atoms", "activity_Bq", "activity_ratio_to_day15", "RP_yield", "Points",
    ]
    write_csv(outdir / "activity_by_time_nuclide_volume.csv", activity_rows, activity_fields)
    write_csv(outdir / "inventory_by_time_nuclide_volume.csv", inventory_rows, inventory_fields)
    write_csv(outdir / "total_activity_by_time.csv", total_rows, ["day", "time_s", "total_activity_Bq"])
    write_csv(outdir / "top_511_related_nuclides_by_day.csv", top_rows, [
        "day", "rank", "VN", "ZA", "nuclide", "activity_Bq", "note",
    ])
    plotted = plot_total_activity(outdir / "total_activity_by_time.png", total_rows)

    reference_total = sum(safe_float(r.get(col, "0")) for r in rows)
    generated_ref_total = total_by_day.get(reference_day, 0.0)
    total_abs_diff = abs(generated_ref_total - reference_total)
    total_rel_diff = total_abs_diff / reference_total if reference_total > 0.0 else 0.0
    passed = (
        n_used > 0
        and scale_min == 1.0
        and scale_max == 1.0
        and total_rel_diff < 1.0e-12
        and max_day15_rel_diff < 1.0e-10
    )
    summary = {
        "status": "PASS" if passed else "FAIL",
        "mode": "constant_profile_inventory",
        "inventory_input": str(inventory.relative_to(ROOT) if inventory.is_relative_to(ROOT) else inventory),
        "environment_grid": str(env_grid.relative_to(ROOT) if env_grid.is_relative_to(ROOT) else env_grid),
        "activity_column": col,
        "reference_day": reference_day,
        "days": days,
        "n_input_rows": len(rows),
        "n_used_rows": n_used,
        "n_skipped_rows": n_skipped,
        "environment_scale_min": scale_min,
        "environment_scale_max": scale_max,
        "reference_total_activity_Bq": reference_total,
        "generated_reference_day_total_activity_Bq": generated_ref_total,
        "reference_total_abs_diff_Bq": total_abs_diff,
        "reference_total_rel_diff": total_rel_diff,
        "max_day15_row_abs_diff_Bq": max_day15_abs_diff,
        "max_day15_row_rel_diff": max_day15_rel_diff,
        "plot_written": plotted,
        "caveat": "Constant-profile ODE validation only; parent feeding and real flight environment scaling are not yet modeled.",
    }
    (outdir / "constant_limit_validation.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md = f"""# Constant-profile activation inventory validation

Status: `{summary['status']}`

- Input inventory: `{summary['inventory_input']}`
- Reference day: `{reference_day}`
- Used rows: `{n_used}` / `{len(rows)}`
- Environment scale range: `{scale_min}` to `{scale_max}`
- Reference total activity: `{reference_total:.12g}` Bq
- Reconstructed day-{reference_day:g} total activity: `{generated_ref_total:.12g}` Bq
- Total relative difference: `{total_rel_diff:.3e}`
- Maximum row relative difference at day {reference_day:g}: `{max_day15_rel_diff:.3e}`

This validates the constant-production ODE normalization against the corrected
day-15 fixed inventory. It is not yet a real day1-day20 flight profile model.
"""
    (outdir / "constant_profile_inventory_summary.md").write_text(md, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--environment-grid", type=Path, default=DEFAULT_ENV_GRID)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--days", default="1,5,10,15,20")
    parser.add_argument("--reference-day", type=float, default=15.0)
    args = parser.parse_args()

    summary = integrate_inventory(args.inventory, args.environment_grid, args.out, parse_days(args.days), args.reference_day)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
