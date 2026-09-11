#!/usr/bin/env python3
"""Couple validated first-principles channeling optics into the Phase 12 package."""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
PHASE12 = R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
FP_OUT = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast"
REPORT = PHASE12 / "first_principles_channeling_optics"
CURRENT_CAM511_AEFF_CM2 = 50.89
TARGET_FLUX = 1.0e-4


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


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normal_survival(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def hard_checks_pass(path: Path) -> bool:
    rows = read_csv(path)
    return bool(rows) and not any(row["status"] == "FAIL" for row in rows)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def guard_copied_workflow_claims(path: Path) -> None:
    if not path.exists():
        return
    replacements = {
        "CAM511 production optics reproduced": "Forbidden, not claimed: CAM511 production optics reproduced",
        "independent validation by matching CAM511 after tuning": "Forbidden, not claimed: independent validation by matching CAM511 after tuning",
        "final production optics detectability": "Forbidden, not claimed: final production optics detectability",
        "final Galactic-center compact-source detection claim": "Forbidden, not claimed: final Galactic-center compact-source detection claim",
    }
    guarded_lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        prefix = line[: len(line) - len(line.lstrip())]
        guarded_lines.append(prefix + replacements.get(stripped, stripped))
    path.write_text("\n".join(guarded_lines) + "\n", encoding="utf-8")


def build_coupling_rows(aeff_cm2: float) -> list[dict[str, Any]]:
    scale = aeff_cm2 / CURRENT_CAM511_AEFF_CM2
    rows = []
    metric_rows = read_csv(PHASE12 / "metric_closure_final.csv")
    for metric_id in ["phase12_baseline_measured_ERL", "phase12_selection_best_measured_ERL"]:
        row = next(item for item in metric_rows if item["metric_id"] == metric_id)
        old_response = float(row["response_cps_per_flux"])
        old_f3 = float(row["F3_1Ms"])
        new_response = old_response * scale
        new_f3 = old_f3 / scale if scale > 0 else float("nan")
        sigma_at_target = 3.0 * TARGET_FLUX / new_f3 if new_f3 > 0 else 0.0
        rows.append(
            {
                "metric_id": metric_id,
                "selection_id": row["selection_id"],
                "baseline_response_cps_per_flux": old_response,
                "firstprinciples_aeff_cm2": aeff_cm2,
                "cam511_reference_aeff_cm2": CURRENT_CAM511_AEFF_CM2,
                "response_scale_vs_current": scale,
                "firstprinciples_response_cps_per_flux": new_response,
                "baseline_F3_1Ms": old_f3,
                "firstprinciples_scaled_F3_1Ms": new_f3,
                "P_ge_3sigma_at_1e-4_1Ms_approx": normal_survival(3.0 - sigma_at_target),
                "claim_level": "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT",
                "approximation": "scalar_Aeff_rescale_existing_detector_templates_no_new_Cosima_transport",
            }
        )
    return rows


def main() -> int:
    sanity = FP_OUT / "first_principles_sanity_checks.csv"
    l1_summary = FP_OUT / "L1_surface_onaxis" / "summary.json"
    l2_summary = FP_OUT / "L2_parratt_onaxis" / "summary.json"
    comparison = FP_OUT / "first_principles_vs_cam511_after_freeze.csv"
    if not sanity.exists() or not l2_summary.exists() or not comparison.exists():
        raise FileNotFoundError("first-principles optics outputs are incomplete; run L1/L2 validation first")
    pass_hard = hard_checks_pass(sanity)
    l1 = json.loads(l1_summary.read_text(encoding="utf-8"))
    l2 = json.loads(l2_summary.read_text(encoding="utf-8"))
    matrix_summary_path = FP_OUT / "optics_response_matrix_coarse_summary.json"
    matrix_summary = json.loads(matrix_summary_path.read_text(encoding="utf-8")) if matrix_summary_path.exists() else {}
    l2_metrics = l2["summary"]
    aeff = float(l2_metrics["estimated_effective_area_cm2"])
    response_scale = aeff / CURRENT_CAM511_AEFF_CM2

    canonical_summary = {
        "primary_model": "L2_parratt",
        "model_id": "FIRST_PRINCIPLES_CHANNELING_L2_PARRATT_V1",
        "claim_level": "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT",
        "cam511_calibration_used": False,
        "production_optics_response": False,
        "L1_surface": l1["summary"],
        "L2_parratt": l2_metrics,
    }
    write_json(FP_OUT / "first_principles_onaxis_summary.json", canonical_summary)
    copy_if_exists(FP_OUT / "L2_parratt_onaxis/bent_channel_samples.csv", FP_OUT / "first_principles_onaxis_samples.csv")

    claim_boundary_text = """# First-Principles Channeling Optics Claim Boundary

Allowed:

- uncalibrated first-principles optics prototype
- W/Si Parratt-multilayer per-bounce transport weights
- physics-driven optics requirement input
- post-freeze comparison with CAM511 reference values
- scalar coupling to existing Phase 12 detector/background templates

Forbidden:

- Forbidden, not claimed: CAM511 production optics reproduced
- Forbidden, not claimed: independent validation by matching CAM511 after tuning
- Forbidden, not claimed: final production optics detectability
- Forbidden, not claimed: final Galactic-center compact-source detection claim

This layer can be used as a paper-level first-principles prototype or
requirements input. It does not replace the validated Be-window detector
transport authority and does not perform a new Cosima detector transport.
"""
    (FP_OUT / "first_principles_claim_boundary.md").write_text(claim_boundary_text, encoding="utf-8")
    write_json(
        FP_OUT / "first_principles_model_freeze.json",
        {
            "model_id": "FIRST_PRINCIPLES_CHANNELING_L2_PARRATT_V1",
            "status": "FROZEN_FOR_REQUIREMENTS_INPUT" if pass_hard else "VALIDATION_FAILED",
            "claim_level": "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT",
            "cam511_calibration_used": False,
            "effective_lookup_used": False,
            "exit_angle_supplement_used": False,
            "production_optics_response": False,
            "inputs": {
                "workflow": "first_principles_channeling_optics_fast_workflow.md",
                "L1_config": "optics/channeling_fp/configs/cam511_channeling_fp_firstprinciples_L1_surface.json",
                "L2_config": "optics/channeling_fp/configs/cam511_channeling_fp_firstprinciples_L2_parratt.json",
                "reflectivity_table": "optics/channeling_fp/out/first_principles_fast/reflectivity_wsi_parratt.csv",
            },
            "primary_outputs": {
                "onaxis_summary": "optics/channeling_fp/out/first_principles_fast/first_principles_onaxis_summary.json",
                "onaxis_samples": "optics/channeling_fp/out/first_principles_fast/first_principles_onaxis_samples.csv",
                "sanity_checks": "optics/channeling_fp/out/first_principles_fast/first_principles_sanity_checks.csv",
                "comparison": "optics/channeling_fp/out/first_principles_fast/first_principles_vs_cam511_after_freeze.csv",
                "matrix_summary": "optics/channeling_fp/out/first_principles_fast/first_principles_matrix_summary.csv",
            },
            "L1_surface_summary": l1["summary"],
            "L2_parratt_summary": l2_metrics,
            "matrix_summary": matrix_summary,
            "claim_boundary": "requirements input only; not production 511-CAM optics and not final compact-source detection",
        },
    )

    REPORT.mkdir(parents=True, exist_ok=True)
    for src, name in [
        (ROOT.parent / "first_principles_channeling_optics_fast_workflow.md", "first_principles_channeling_optics_fast_workflow.md"),
        (ROOT / "optics/channeling_fp/configs/cam511_channeling_fp_firstprinciples_L1_surface.json", "configs/cam511_channeling_fp_firstprinciples_L1_surface.json"),
        (ROOT / "optics/channeling_fp/configs/cam511_channeling_fp_firstprinciples_L2_parratt.json", "configs/cam511_channeling_fp_firstprinciples_L2_parratt.json"),
        (FP_OUT / "first_principles_model_freeze.json", "first_principles_model_freeze.json"),
        (FP_OUT / "first_principles_onaxis_summary.json", "first_principles_onaxis_summary.json"),
        (FP_OUT / "first_principles_onaxis_samples.csv", "first_principles_onaxis_samples.csv"),
        (FP_OUT / "first_principles_claim_boundary.md", "first_principles_claim_boundary.md"),
        (FP_OUT / "reflectivity_wsi_parratt.csv", "reflectivity_wsi_parratt.csv"),
        (FP_OUT / "reflectivity_wsi_parratt.summary.json", "reflectivity_wsi_parratt.summary.json"),
        (sanity, "first_principles_sanity_checks.csv"),
        (FP_OUT / "first_principles_sanity_checks.json", "first_principles_sanity_checks.json"),
        (comparison, "first_principles_vs_cam511_after_freeze.csv"),
        (l1_summary, "first_principles_onaxis_summary_L1_surface.json"),
        (l2_summary, "first_principles_onaxis_summary_L2_parratt.json"),
        (FP_OUT / "L1_surface_onaxis/bent_channel_samples.csv", "first_principles_onaxis_samples_L1_surface.csv"),
        (FP_OUT / "L2_parratt_onaxis/bent_channel_samples.csv", "first_principles_onaxis_samples_L2_parratt.csv"),
        (FP_OUT / "L1_surface_onaxis/bent_channel_overview.png", "figures/first_principles_L1_focal_spot.png"),
        (FP_OUT / "L1_surface_onaxis/bounce_hist.png", "figures/first_principles_L1_bounce_alpha.png"),
        (FP_OUT / "L2_parratt_onaxis/bent_channel_overview.png", "figures/first_principles_L2_focal_spot.png"),
        (FP_OUT / "L2_parratt_onaxis/bounce_hist.png", "figures/first_principles_L2_bounce_alpha.png"),
        (FP_OUT / "reflectivity_wsi_parratt.png", "figures/reflectivity_wsi_parratt.png"),
        (FP_OUT / "first_principles_matrix_summary.csv", "first_principles_matrix_summary.csv"),
        (FP_OUT / "optics_response_matrix_coarse.npz", "optics_response_matrix_coarse.npz"),
        (FP_OUT / "optics_response_matrix_coarse_summary.json", "optics_response_matrix_coarse_summary.json"),
    ]:
        copy_if_exists(src, REPORT / name)
    guard_copied_workflow_claims(REPORT / "first_principles_channeling_optics_fast_workflow.md")

    coupling_rows = build_coupling_rows(aeff)
    write_csv(REPORT / "phase12_firstprinciples_optics_coupling.csv", coupling_rows)
    status = {
        "status": "PASS_FIRST_PRINCIPLES_OPTICS_COUPLED" if pass_hard else "FAIL_FIRST_PRINCIPLES_OPTICS_VALIDATION",
        "optics_id": "FIRST_PRINCIPLES_CHANNELING_L2_PARRATT_V1",
        "claim_level": "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT",
        "cam511_calibration_used": False,
        "production_optics_response": False,
        "firstprinciples_aeff_cm2": aeff,
        "response_scale_vs_current_cam511_normalization": response_scale,
        "weighted_r95_mm": float(l2_metrics["weighted_r95_mm"]),
        "weighted_hpd_diameter_mm": float(l2_metrics["weighted_hpd_diameter_mm"]),
        "hard_checks_pass": pass_hard,
        "coupling": "scalar Aeff rescale of existing Phase 12 measured detector/background templates; no new Cosima detector transport",
    }
    write_json(REPORT / "first_principles_optics_coupling_summary.json", status)
    yaml.safe_dump(
        {
            "optics_id": "FIRST_PRINCIPLES_CHANNELING_L2_PARRATT_V1",
            "status": "first_principles_prototype_validated_for_requirements_input" if pass_hard else "validation_failed",
            "source": "optics/channeling_fp/out/first_principles_fast",
            "cam511_calibration_used": False,
            "production_optics_response": False,
            "aeff_cm2_at_511": aeff,
            "response_scale_vs_current_cam511_normalization": response_scale,
            "psf_proxy": {
                "weighted_r50_mm": float(l2_metrics["weighted_r50_mm"]),
                "weighted_r90_mm": float(l2_metrics["weighted_r90_mm"]),
                "weighted_r95_mm": float(l2_metrics["weighted_r95_mm"]),
                "weighted_hpd_diameter_mm": float(l2_metrics["weighted_hpd_diameter_mm"]),
            },
            "claim_control": {
                "allowed": "physics-driven first-principles optics requirement input",
                "forbidden": "Forbidden, not claimed: production 511-CAM optics response or final compact-source detection",
            },
        },
        (REPORT / "optics_response_firstprinciples_channeling_v1.yaml").open("w", encoding="utf-8"),
        sort_keys=False,
        allow_unicode=False,
    )
    claim = claim_boundary_text
    (REPORT / "first_principles_claim_boundary.md").write_text(claim, encoding="utf-8")
    readme = f"""# First-Principles Channeling Optics Coupling

This directory couples the uncalibrated first-principles channeling optics
prototype into the existing Phase 12 compact-source analysis.

- optics id: `FIRST_PRINCIPLES_CHANNELING_L2_PARRATT_V1`
- CAM511 calibration used: `false`
- production optics response: `false`
- L2 Parratt Aeff at 511 keV: `{aeff:.6g} cm2`
- response scale versus current 50.89 cm2 normalization: `{response_scale:.6g}`
- hard checks pass: `{pass_hard}`

The coupling is intentionally conservative: existing measured detector and
background templates are rescaled by the first-principles Aeff. This is a
requirements input. Forbidden, not claimed: final production optics
detectability.
"""
    (REPORT / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0 if pass_hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
