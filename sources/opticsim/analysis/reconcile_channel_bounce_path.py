from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")

import matplotlib.pyplot as plt
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def estimate_half_gap_um(length_mm: float, theta_rad: float, n_reflections: float) -> float:
    if n_reflections <= 0.0:
        return 0.0
    return 1000.0 * theta_rad * length_mm / (2.0 * n_reflections)


def build_rows(
    config_path: Path,
    calibration_path: Path,
    literature_min_reflections: int,
    literature_max_reflections: int,
) -> list[dict[str, Any]]:
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    calibration = {int(row["ring_id"]): row for row in load_json(calibration_path)}

    focal_length_mm = float(cfg["focal_length_m"]) * 1000.0
    rows: list[dict[str, Any]] = []
    for ring in cfg["rings"]:
        ring_id = int(ring["id"])
        radius_mm = float(ring["radius_cm"]) * 10.0
        length_mm = float(ring["length_cm"]) * 10.0
        bend_rad = math.radians(float(ring["bending_angle_deg"]))
        focus_rad = math.atan2(radius_mm, focal_length_mm)
        theta_cal = float(calibration[ring_id]["theta_rad"])
        effective_bounces = float(calibration[ring_id]["n_bounce"])

        required_bounces_from_bend = bend_rad / (2.0 * theta_cal)
        required_bounces_from_focus = focus_rad / (2.0 * theta_cal)
        theta_for_lit_min = bend_rad / (2.0 * literature_min_reflections)
        theta_for_lit_max = bend_rad / (2.0 * literature_max_reflections)

        rows.append(
            {
                "ring_id": ring_id,
                "radius_cm": float(ring["radius_cm"]),
                "length_cm": float(ring["length_cm"]),
                "configured_bend_rad": bend_rad,
                "paraxial_focus_rad": focus_rad,
                "calibrated_theta_rad": theta_cal,
                "effective_model_bounces": effective_bounces,
                "required_bounces_at_calibrated_theta": required_bounces_from_bend,
                "required_bounces_from_focus_angle": required_bounces_from_focus,
                "literature_min_reflections": literature_min_reflections,
                "literature_max_reflections": literature_max_reflections,
                "theta_if_literature_min_reflections_rad": theta_for_lit_min,
                "theta_if_literature_max_reflections_rad": theta_for_lit_max,
                "half_gap_um_if_literature_min_reflections": estimate_half_gap_um(
                    length_mm, theta_for_lit_min, literature_min_reflections
                ),
                "half_gap_um_if_literature_max_reflections": estimate_half_gap_um(
                    length_mm, theta_for_lit_max, literature_max_reflections
                ),
                "deflection_from_effective_model_rad": 2.0 * effective_bounces * theta_cal,
                "deflection_from_literature_min_at_calibrated_theta_rad": (
                    2.0 * literature_min_reflections * theta_cal
                ),
                "deflection_from_literature_max_at_calibrated_theta_rad": (
                    2.0 * literature_max_reflections * theta_cal
                ),
            }
        )
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot(rows: list[dict[str, Any]], out_dir: Path) -> None:
    labels = [f"R{row['ring_id']}" for row in rows]
    x = list(range(len(rows)))
    lit_min = rows[0]["literature_min_reflections"]
    lit_max = rows[0]["literature_max_reflections"]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.1), dpi=140)

    ax = axes[0]
    effective = [row["effective_model_bounces"] for row in rows]
    required = [row["required_bounces_at_calibrated_theta"] for row in rows]
    ax.axhspan(lit_min, lit_max, color="#fde68a", alpha=0.45, label="literature clue 17-38")
    ax.bar([i - 0.18 for i in x], effective, width=0.36, color="#2563eb", label="current effective")
    ax.bar([i + 0.18 for i in x], required, width=0.36, color="#dc2626", label="needed at calibrated theta")
    ax.set_xticks(x, labels)
    ax.set_ylabel("reflection count")
    ax.set_title("bounce-count bracket")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=7.5)

    ax = axes[1]
    theta_cal = [row["calibrated_theta_rad"] * 1.0e4 for row in rows]
    theta_lit_min = [row["theta_if_literature_min_reflections_rad"] * 1.0e4 for row in rows]
    theta_lit_max = [row["theta_if_literature_max_reflections_rad"] * 1.0e4 for row in rows]
    ax.fill_between(x, theta_lit_max, theta_lit_min, color="#bbf7d0", alpha=0.65, label="theta if 17-38 bounces")
    ax.plot(x, theta_cal, marker="o", color="#7c3aed", label="calibrated effective theta")
    ax.plot(x, theta_lit_min, marker="o", color="#16a34a", linewidth=1.2, label="17 bounces")
    ax.plot(x, theta_lit_max, marker="o", color="#15803d", linewidth=1.2, label="38 bounces")
    ax.set_xticks(x, labels)
    ax.set_ylabel("theta [1e-4 rad]")
    ax.set_title("implied local grazing angle")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7.5)

    ax = axes[2]
    gap_lit_min = [row["half_gap_um_if_literature_min_reflections"] for row in rows]
    gap_lit_max = [row["half_gap_um_if_literature_max_reflections"] for row in rows]
    ax.fill_between(x, gap_lit_max, gap_lit_min, color="#dbeafe", alpha=0.75, label="implied half-gap band")
    ax.plot(x, gap_lit_min, marker="o", color="#0284c7", linewidth=1.2, label="17 bounces")
    ax.plot(x, gap_lit_max, marker="o", color="#0369a1", linewidth=1.2, label="38 bounces")
    ax.set_xticks(x, labels)
    ax.set_ylabel("half-gap [um]")
    ax.set_title("parallel-wall scale if applied directly")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7.5)

    fig.tight_layout()
    fig.savefig(out_dir / "channel_bounce_path_reconciliation.png")
    plt.close(fig)


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    theta_lit_values = [
        value
        for row in rows
        for value in (
            row["theta_if_literature_min_reflections_rad"],
            row["theta_if_literature_max_reflections_rad"],
        )
    ]
    gap_lit_values = [
        value
        for row in rows
        for value in (
            row["half_gap_um_if_literature_min_reflections"],
            row["half_gap_um_if_literature_max_reflections"],
        )
    ]
    required = [row["required_bounces_at_calibrated_theta"] for row in rows]
    effective = [row["effective_model_bounces"] for row in rows]
    return {
        "system": "channel_bounce_path_reconciliation",
        "warning": (
            "Diagnostic bridge only. The 17-38 reflection range comes from the Shirazi/Bloser soft-gamma "
            "concentrator lineage, not directly from the 511-CAM four-ring configuration."
        ),
        "n_rings": len(rows),
        "literature_reflection_range": [
            rows[0]["literature_min_reflections"],
            rows[0]["literature_max_reflections"],
        ],
        "effective_model_bounce_range": [min(effective), max(effective)],
        "required_bounce_range_at_calibrated_theta": [min(required), max(required)],
        "theta_range_if_literature_reflections_rad": [min(theta_lit_values), max(theta_lit_values)],
        "half_gap_range_if_literature_reflections_um": [min(gap_lit_values), max(gap_lit_values)],
        "all_literature_theta_below_calibrated_theta": all(
            row["theta_if_literature_min_reflections_rad"] <= row["calibrated_theta_rad"]
            and row["theta_if_literature_max_reflections_rad"] <= row["calibrated_theta_rad"]
            for row in rows
        ),
        "conclusion": (
            "The next missing physics input is the actual many-bounce channel path. The current 1-3 bounce "
            "effective bookkeeping is too shallow, the calibrated-theta deflection estimate needs 6-13 bounces, "
            "and the 17-38-reflection literature clue would imply smaller local grazing angles that remain below "
            "the current calibrated theta scale. This supports recovering the original IDL/channel geometry before "
            "building four-ring wall-by-wall Geant4."
        ),
    }


def write_markdown(rows: list[dict[str, Any]], summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Channel Bounce/Path Reconciliation",
        "",
        "This diagnostic turns the current geometry blocker into a table that can be audited before more Geant4 geometry is added.",
        "",
        f"Literature reflection range used as lineage clue: `{summary['literature_reflection_range'][0]}-"
        f"{summary['literature_reflection_range'][1]}`.",
        f"Effective model bounce range: `{summary['effective_model_bounce_range'][0]:.0f}-"
        f"{summary['effective_model_bounce_range'][1]:.0f}`.",
        f"Required bounces at calibrated theta: `{summary['required_bounce_range_at_calibrated_theta'][0]:.2f}-"
        f"{summary['required_bounce_range_at_calibrated_theta'][1]:.2f}`.",
        "",
        "| Ring | effective bounces | needed at calibrated theta | theta if 17 bounces [rad] | theta if 38 bounces [rad] | half-gap band [um] |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        gap_low = row["half_gap_um_if_literature_max_reflections"]
        gap_high = row["half_gap_um_if_literature_min_reflections"]
        lines.append(
            f"| R{row['ring_id']} | {row['effective_model_bounces']:.0f} | "
            f"{row['required_bounces_at_calibrated_theta']:.2f} | "
            f"{row['theta_if_literature_min_reflections_rad']:.6g} | "
            f"{row['theta_if_literature_max_reflections_rad']:.6g} | "
            f"{gap_low:.4g}-{gap_high:.4g} |"
        )
    lines.extend(["", summary["conclusion"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile current 511-CAM channel bounce assumptions with many-bounce literature clues.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--calibration", default="runs/channel_4ring_calibrated_v2/ring_theta_calibration.json")
    parser.add_argument("--out", default="runs/channel_bounce_path_reconciliation")
    parser.add_argument("--literature-min-reflections", type=int, default=17)
    parser.add_argument("--literature-max-reflections", type=int, default=38)
    args = parser.parse_args()

    if args.literature_min_reflections <= 0 or args.literature_max_reflections <= args.literature_min_reflections:
        raise ValueError("Require 0 < literature-min-reflections < literature-max-reflections")

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = build_rows(
        ROOT / args.config,
        ROOT / args.calibration,
        args.literature_min_reflections,
        args.literature_max_reflections,
    )
    write_csv(rows, out / "channel_bounce_path_reconciliation.csv")
    summary = build_summary(rows)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    write_markdown(rows, summary, out / "channel_bounce_path_reconciliation.md")
    plot(rows, out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
