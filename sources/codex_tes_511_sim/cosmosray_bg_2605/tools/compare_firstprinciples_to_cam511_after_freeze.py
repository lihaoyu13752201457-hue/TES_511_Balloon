#!/usr/bin/env python3
"""Compare frozen first-principles optics outputs with CAM511 reference values."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast"


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))["summary"]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["metric", "CAM511_reference", "L1_surface", "L2_Parratt", "used_for_tuning", "notes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    cam = json.loads((ROOT / "docs" / "summary.json").read_text(encoding="utf-8"))
    cam_cfg = cam["config"]
    cam_metrics = cam["metrics"]
    l1 = load_summary(OUT / "L1_surface_onaxis" / "summary.json")
    l2 = load_summary(OUT / "L2_parratt_onaxis" / "summary.json")

    rows = [
        {
            "metric": "focal_length_m",
            "CAM511_reference": cam_cfg["focus_length_m"],
            "L1_surface": l1["focus_length_m"],
            "L2_Parratt": l2["focus_length_m"],
            "used_for_tuning": "false",
            "notes": "geometry input retained from 511-CAM-inspired design",
        },
        {
            "metric": "ring_radii_mm",
            "CAM511_reference": "22.5/30/37.5/45",
            "L1_surface": "22.5/30/37.5/45",
            "L2_Parratt": "22.5/30/37.5/45",
            "used_for_tuning": "false",
            "notes": "geometry input, not output calibration",
        },
        {
            "metric": "W_Si_thickness_nm",
            "CAM511_reference": "30/150",
            "L1_surface": "30/150",
            "L2_Parratt": "30/150",
            "used_for_tuning": "false",
            "notes": "material stack input",
        },
        {
            "metric": "FoV_radius_arcmin",
            "CAM511_reference": cam_cfg["field_of_view_radius_arcmin"],
            "L1_surface": "same input",
            "L2_Parratt": "same input",
            "used_for_tuning": "false",
            "notes": "used as pointing/FoV reference only",
        },
        {
            "metric": "effective_area_cm2",
            "CAM511_reference": cam_cfg["effective_area_cm2_at_511"],
            "L1_surface": l1["estimated_effective_area_cm2"],
            "L2_Parratt": l2["estimated_effective_area_cm2"],
            "used_for_tuning": "false",
            "notes": "post-freeze comparison only",
        },
        {
            "metric": "r95_diameter_mm",
            "CAM511_reference": cam_metrics["measured_r95_diameter_mm"],
            "L1_surface": 2.0 * float(l1["weighted_r95_mm"]),
            "L2_Parratt": 2.0 * float(l2["weighted_r95_mm"]),
            "used_for_tuning": "false",
            "notes": "post-freeze comparison only",
        },
        {
            "metric": "HPD_diameter_mm",
            "CAM511_reference": cam_metrics["measured_hpd_diameter_mm"],
            "L1_surface": l1["weighted_hpd_diameter_mm"],
            "L2_Parratt": l2["weighted_hpd_diameter_mm"],
            "used_for_tuning": "false",
            "notes": "post-freeze comparison only",
        },
        {
            "metric": "weight_model",
            "CAM511_reference": "not used",
            "L1_surface": l1["weight_model"],
            "L2_Parratt": l2["weight_model"],
            "used_for_tuning": "false",
            "notes": "effective_lookup forbidden in first-principles mode",
        },
    ]
    write_csv(OUT / "first_principles_vs_cam511_after_freeze.csv", rows)
    print(json.dumps({"status": "PASS_COMPARISON_WRITTEN", "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
