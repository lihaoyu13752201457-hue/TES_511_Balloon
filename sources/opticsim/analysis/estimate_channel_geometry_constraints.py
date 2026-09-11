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


def estimate_half_gap_mm(length_mm: float, theta_rad: float, n_bounce: float) -> float:
    if n_bounce <= 0.0:
        return 0.0
    return theta_rad * length_mm / (2.0 * n_bounce)


def build_rows(config_path: Path, calibration_path: Path) -> list[dict[str, Any]]:
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    calibration = {int(row["ring_id"]): row for row in load_json(calibration_path)}

    focal_length_mm = float(cfg["focal_length_m"]) * 1000.0
    rows: list[dict[str, Any]] = []
    for ring in cfg["rings"]:
        ring_id = int(ring["id"])
        radius_mm = float(ring["radius_cm"]) * 10.0
        length_mm = float(ring["length_cm"]) * 10.0
        configured_bend_rad = math.radians(float(ring["bending_angle_deg"]))
        paraxial_focus_rad = math.atan2(radius_mm, focal_length_mm)
        theta_rad = float(calibration[ring_id]["theta_rad"])
        calibrated_bounces = float(calibration[ring_id]["n_bounce"])
        required_bounces_config = configured_bend_rad / (2.0 * theta_rad)
        required_bounces_focus = paraxial_focus_rad / (2.0 * theta_rad)
        rows.append(
            {
                "ring_id": ring_id,
                "radius_cm": float(ring["radius_cm"]),
                "length_cm": float(ring["length_cm"]),
                "configured_bend_deg": float(ring["bending_angle_deg"]),
                "configured_bend_rad": configured_bend_rad,
                "paraxial_focus_rad": paraxial_focus_rad,
                "calibrated_theta_rad": theta_rad,
                "effective_model_bounces": calibrated_bounces,
                "required_bounces_from_config_bend": required_bounces_config,
                "required_bounces_from_focus_angle": required_bounces_focus,
                "bounce_ratio_config_to_effective": required_bounces_config / calibrated_bounces,
                "half_gap_for_config_bend_mm": estimate_half_gap_mm(length_mm, theta_rad, required_bounces_config),
                "half_gap_for_focus_angle_mm": estimate_half_gap_mm(length_mm, theta_rad, required_bounces_focus),
                "max_deflection_with_effective_bounces_rad": 2.0 * calibrated_bounces * theta_rad,
                "deflection_shortfall_config_rad": configured_bend_rad - 2.0 * calibrated_bounces * theta_rad,
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
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=140)

    ax = axes[0]
    effective = [row["effective_model_bounces"] for row in rows]
    required = [row["required_bounces_from_config_bend"] for row in rows]
    x = range(len(rows))
    ax.bar([i - 0.18 for i in x], effective, width=0.36, label="effective model", color="#2563eb")
    ax.bar([i + 0.18 for i in x], required, width=0.36, label="needed for 2theta deflection", color="#dc2626")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("bounce count")
    ax.set_title("bounce-count consistency check")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(labels, [row["configured_bend_rad"] for row in rows], marker="o", label="configured bend", color="#dc2626")
    ax.plot(
        labels,
        [row["max_deflection_with_effective_bounces_rad"] for row in rows],
        marker="o",
        label="2Ntheta from effective bounces",
        color="#2563eb",
    )
    ax.set_ylabel("angle [rad]")
    ax.set_title("available small-angle deflection")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out_dir / "channel_geometry_constraints.png")
    plt.close(fig)


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    worst = max(rows, key=lambda row: row["bounce_ratio_config_to_effective"])
    return {
        "system": "channel_geometry_constraints",
        "warning": "Analytic paraxial/specular estimate only; it is a consistency diagnostic for the current effective bounce assumptions.",
        "target_theta_source": "runs/channel_4ring_calibrated_v2/ring_theta_calibration.json",
        "n_rings": len(rows),
        "max_required_bounces_from_config_bend": max(row["required_bounces_from_config_bend"] for row in rows),
        "max_bounce_ratio_config_to_effective": worst["bounce_ratio_config_to_effective"],
        "worst_ring_id": worst["ring_id"],
        "worst_ring_configured_bend_rad": worst["configured_bend_rad"],
        "worst_ring_effective_model_bounces": worst["effective_model_bounces"],
        "worst_ring_required_bounces_from_config_bend": worst["required_bounces_from_config_bend"],
        "conclusion": (
            "The configured focusing deflections require roughly 6-13 small-angle reflections at theta~1.5e-4 rad, "
            "while the current calibrated effective model uses 1-3 bounce bookkeeping. This explains why direct "
            "wall-by-wall Geant4 geometry cannot be forced to match the effective throughput without revisiting the "
            "channel geometry/reflection-count model."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate channel geometry/bounce-count constraints from 511-CAM parameters.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--calibration", default="runs/channel_4ring_calibrated_v2/ring_theta_calibration.json")
    parser.add_argument("--out", default="runs/channel_geometry_constraints")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = build_rows(ROOT / args.config, ROOT / args.calibration)
    write_csv(rows, out / "channel_geometry_constraints.csv")
    summary = build_summary(rows)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    plot(rows, out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
