#!/usr/bin/env python3
"""Build no-direct-scaling spot-definition diagnostics for channeling optics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHASE12 = ROOT / "reports2.0" / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
DEFAULT_OUT = PHASE12 / "no_direct_scaling_optics_alignment"
FP_OUT = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    ap.add_argument("--energy-keV", type=float, default=511.0)
    return ap.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))["summary"]


def quantile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.quantile(np.asarray(values, dtype=float), q))


def matrix_rows_for_energy(matrix: list[dict[str, str]], energy_keV: float) -> list[dict[str, str]]:
    return [row for row in matrix if abs(float(row["energy_keV"]) - energy_keV) < 1.0e-9]


def build_diagnostics(outdir: Path, energy_keV: float) -> dict[str, Any]:
    tables = outdir / "tables"
    figures = outdir / "figures"
    notes = outdir / "notes"
    for d in (tables, figures, notes):
        d.mkdir(parents=True, exist_ok=True)

    cam = json.loads((ROOT / "docs" / "summary.json").read_text(encoding="utf-8"))
    cam_cfg = cam["config"]
    cam_metrics = cam["metrics"]
    l1 = load_summary(FP_OUT / "L1_surface_onaxis" / "summary.json")
    l2 = load_summary(FP_OUT / "L2_parratt_onaxis" / "summary.json")
    matrix_path = FP_OUT / "first_principles_matrix_summary.csv"
    matrix = read_csv(matrix_path)
    matrix_511 = matrix_rows_for_energy(matrix, energy_keV)

    f_mm = float(l2["focus_length_m"]) * 1000.0
    fov_radius_arcmin = float(cam_cfg["field_of_view_radius_arcmin"])
    fov_radius_mm = f_mm * math.tan(math.radians(fov_radius_arcmin / 60.0))
    onaxis_l2_r95_mm = float(l2["weighted_r95_mm"])
    expected_full_fov_envelope_d95_mm = 2.0 * (fov_radius_mm + onaxis_l2_r95_mm)

    edge_theta = max(float(row["theta_arcmin"]) for row in matrix_511)
    edge_rows = [row for row in matrix_511 if abs(float(row["theta_arcmin"]) - edge_theta) < 1.0e-9]
    edge_d95 = [float(row["D95_mm"]) for row in edge_rows]
    edge_aeff = [float(row["Aeff_cm2"]) for row in edge_rows]
    onaxis_rows = [row for row in matrix_511 if abs(float(row["theta_arcmin"])) < 1.0e-9]
    onaxis_d95 = [float(row["D95_mm"]) for row in onaxis_rows]

    spot_defs = [
        {
            "metric_id": "intrinsic_onaxis_core_D50",
            "definition": "on-axis point-source weighted D50 from no-calibration specular ray tracing",
            "value_mm": float(l2["weighted_hpd_diameter_mm"]),
            "source": "current_L2_parratt_onaxis",
            "allowed_comparison": "not the CAM511 reported few-cm beam diameter directly",
            "claim_level": "physics_prototype_intrinsic_core",
        },
        {
            "metric_id": "intrinsic_onaxis_core_D95",
            "definition": "on-axis point-source weighted D95 from no-calibration specular ray tracing",
            "value_mm": 2.0 * onaxis_l2_r95_mm,
            "source": "current_L2_parratt_onaxis",
            "allowed_comparison": "diagnostic only; not a final CAM511 beam-footprint comparison",
            "claim_level": "physics_prototype_intrinsic_core",
        },
        {
            "metric_id": "fov_edge_expected_mapping_D95",
            "definition": "D95 at the FoV edge measured relative to ideal focal-plane off-axis mapping",
            "value_mm": quantile(edge_d95, 0.50),
            "source": "current_L2_coarse_matrix",
            "allowed_comparison": "cautious comparison with few-cm CAM511 beam scale after definition audit",
            "claim_level": "engineering_footprint_proxy",
        },
        {
            "metric_id": "expected_full_fov_envelope_D95",
            "definition": "2 * (focal-plane FoV radius + intrinsic on-axis r95), no scaling to CAM511",
            "value_mm": expected_full_fov_envelope_d95_mm,
            "source": "geometry_plus_current_intrinsic_core",
            "allowed_comparison": "cautious comparison with reported focused-beam footprint scale",
            "claim_level": "engineering_footprint_proxy",
        },
        {
            "metric_id": "reported_cam511_focused_beam_diameter",
            "definition": "CAM511 paper/local reference reported focused beam diameter",
            "value_mm": float(cam_cfg.get("target_spot_diameter_mm", cam_metrics["measured_r95_diameter_mm"])),
            "source": "CAM511_literature_reference_via_docs_summary",
            "allowed_comparison": "definition ambiguous; do not label as on-axis r95 unless independently proven",
            "claim_level": "literature_reference_not_calibration_target",
        },
    ]
    write_csv(tables / "spot_metric_definitions.csv", spot_defs)

    comparison_map = [
        {
            "cam511_metric": "reported_focused_beam_diameter",
            "cam511_value_mm": float(cam_cfg.get("target_spot_diameter_mm", 35.0)),
            "cam511_definition_status": "ambiguous_in_local_reference",
            "current_metric": "intrinsic_onaxis_core_D95",
            "current_value_mm": 2.0 * onaxis_l2_r95_mm,
            "comparison_role": "not_preferred",
            "reason": "intrinsic on-axis core is not necessarily the same as the reported engineering beam footprint",
            "used_for_tuning": False,
        },
        {
            "cam511_metric": "reported_focused_beam_diameter",
            "cam511_value_mm": float(cam_cfg.get("target_spot_diameter_mm", 35.0)),
            "cam511_definition_status": "ambiguous_in_local_reference",
            "current_metric": "expected_full_fov_envelope_D95",
            "current_value_mm": expected_full_fov_envelope_d95_mm,
            "comparison_role": "preferred_cautious_proxy",
            "reason": "uses design FoV and current intrinsic core without scaling to CAM511",
            "used_for_tuning": False,
        },
        {
            "cam511_metric": "reported_focused_beam_diameter",
            "cam511_value_mm": float(cam_cfg.get("target_spot_diameter_mm", 35.0)),
            "cam511_definition_status": "ambiguous_in_local_reference",
            "current_metric": "fov_edge_expected_mapping_D95_median",
            "current_value_mm": quantile(edge_d95, 0.50),
            "comparison_role": "supporting_proxy",
            "reason": "existing off-axis matrix shows few-cm residual footprint scale at FoV edge",
            "used_for_tuning": False,
        },
    ]
    write_csv(tables / "cam511_comparison_metric_map.csv", comparison_map)

    fov_rows = [
        {
            "metric_id": "fov_radius_focal_plane_mm",
            "value": fov_radius_mm,
            "unit": "mm",
            "definition": "f_mm * tan(fov_radius_arcmin)",
            "used_for_tuning": False,
        },
        {
            "metric_id": "fov_diameter_focal_plane_mm",
            "value": 2.0 * fov_radius_mm,
            "unit": "mm",
            "definition": "2 * fov_radius_focal_plane_mm",
            "used_for_tuning": False,
        },
        {
            "metric_id": "intrinsic_onaxis_core_D95_mm",
            "value": 2.0 * onaxis_l2_r95_mm,
            "unit": "mm",
            "definition": "L2 on-axis weighted D95",
            "used_for_tuning": False,
        },
        {
            "metric_id": "expected_geometric_full_fov_envelope_D95_mm",
            "value": expected_full_fov_envelope_d95_mm,
            "unit": "mm",
            "definition": "2 * (fov_radius_focal_plane_mm + onaxis_r95_mm)",
            "used_for_tuning": False,
        },
        {
            "metric_id": "matrix_onaxis_D95_median_mm",
            "value": quantile(onaxis_d95, 0.50),
            "unit": "mm",
            "definition": "median over phi in existing L2 matrix at theta=0",
            "used_for_tuning": False,
        },
        {
            "metric_id": "matrix_fov_edge_D95_min_mm",
            "value": min(edge_d95),
            "unit": "mm",
            "definition": f"minimum D95 at theta={edge_theta:g} arcmin over matrix phi bins",
            "used_for_tuning": False,
        },
        {
            "metric_id": "matrix_fov_edge_D95_median_mm",
            "value": quantile(edge_d95, 0.50),
            "unit": "mm",
            "definition": f"median D95 at theta={edge_theta:g} arcmin over matrix phi bins",
            "used_for_tuning": False,
        },
        {
            "metric_id": "matrix_fov_edge_D95_max_mm",
            "value": max(edge_d95),
            "unit": "mm",
            "definition": f"maximum D95 at theta={edge_theta:g} arcmin over matrix phi bins",
            "used_for_tuning": False,
        },
        {
            "metric_id": "matrix_fov_edge_Aeff_median_cm2",
            "value": quantile(edge_aeff, 0.50),
            "unit": "cm2",
            "definition": f"median Aeff at theta={edge_theta:g} arcmin over matrix phi bins",
            "used_for_tuning": False,
        },
    ]
    write_csv(tables / "fov_footprint_summary.csv", fov_rows)

    note = f"""# CAM511 Focused-Beam Definition Audit

The local CAM511 reference currently labels the few-cm focused beam as
`target_spot_diameter_metric = approx_r95_diameter_mm`. This package treats
that definition as ambiguous until externally confirmed.

No direct scaling was used here.

Key numbers:

- L2 intrinsic on-axis D95: `{2.0 * onaxis_l2_r95_mm:.6g} mm`
- focal-plane FoV radius for `{fov_radius_arcmin:g} arcmin` at `{f_mm:g} mm` focal length: `{fov_radius_mm:.6g} mm`
- expected full-FoV envelope D95 proxy: `{expected_full_fov_envelope_d95_mm:.6g} mm`
- existing matrix FoV-edge D95 median: `{quantile(edge_d95, 0.50):.6g} mm`

Interpretation: the intrinsic on-axis core and full-FoV / engineering footprint
are different quantities. The CAM511 few-cm number should not be compared to
the on-axis core as a final error ratio until its definition is confirmed.
"""
    (notes / "cam511_definition_audit.md").write_text(note, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    labels = ["L2 on-axis D95", "FoV diameter", "expected envelope", "matrix FoV-edge D95", "CAM511 reported"]
    values = [
        2.0 * onaxis_l2_r95_mm,
        2.0 * fov_radius_mm,
        expected_full_fov_envelope_d95_mm,
        quantile(edge_d95, 0.50),
        float(cam_cfg.get("target_spot_diameter_mm", 35.0)),
    ]
    colors = ["#2563eb", "#64748b", "#0f766e", "#f59e0b", "#7c3aed"]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("diameter / footprint metric [mm]")
    ax.set_title("No-direct-scaling spot metric separation")
    ax.tick_params(axis="x", rotation=20)
    fig.savefig(figures / "onaxis_core_vs_full_fov_footprint.png", dpi=180)
    plt.close(fig)

    return {
        "status": "PASS_SPOT_DEFINITION_DIAGNOSTICS",
        "outdir": str(outdir.relative_to(ROOT)),
        "intrinsic_onaxis_core_D95_mm": 2.0 * onaxis_l2_r95_mm,
        "expected_full_fov_envelope_D95_mm": expected_full_fov_envelope_d95_mm,
        "matrix_fov_edge_D95_median_mm": quantile(edge_d95, 0.50),
        "cam511_reported_focused_beam_diameter_mm": float(cam_cfg.get("target_spot_diameter_mm", 35.0)),
        "used_for_tuning": False,
    }


def main() -> int:
    args = parse_args()
    summary = build_diagnostics(ROOT / args.outdir if not Path(args.outdir).is_absolute() else Path(args.outdir), args.energy_keV)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
