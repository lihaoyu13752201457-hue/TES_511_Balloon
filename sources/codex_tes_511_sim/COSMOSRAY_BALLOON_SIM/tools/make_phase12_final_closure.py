#!/usr/bin/env python3
"""Build the final Phase 12 compact-source analysis closure package."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import shutil
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

from make_511_phase10_point_diffuse_report import (
    CATALOG_DEFAULT,
    FOCUSED_DEFAULT,
    MEASURED_DEFAULT,
    REFERENCE_FLUX,
    SELECTIONS,
    build_features_for_basis,
    focused_gamma_rates,
    selection_mask,
)
from make_phase11_metric_crosswalk import normal_survival


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT = R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
FIG = OUT / "final_figures"
TABLES = OUT / "final_tables_for_paper"
CONFIGS = OUT / "configs_final"
PATCH = OUT / "manuscript_patch"
VALIDATION = OUT / "validation"
SCRIPT_PACKAGE_DIR = R2 / "05_SCRIPTS_AND_CONFIG" / "tools"

PHASE11 = R2 / "11_METRIC_RECONCILIATION_AND_OPTICS_GATE"
ABC = R2 / "09_SOURCE_CASES_ABC"
PHASE10 = R2 / "10_POINT_DIFFUSE_DISCRIMINATION"
FINAL_LINEAGE = R2 / "07_NIMA_MANUSCRIPT" / "final_numerical_lineage.csv"

EXPOSURE_S = 1.0e6
TARGET_FLUX = 1.0e-4
CURRENT_AEFF_CM2 = 50.89
CURRENT_RESPONSE = 24.858993900839696
ENERGY_EDGES = [480.0, 490.0, 500.0, 505.0, 510.3, 511.8, 515.0, 520.0, 530.0, 550.0]
RADIUS_EDGES = [0.0, 3.0, 9.0, 18.0, float("inf")]
LAYER_VALUES = [0, 1, 2, 3, 4, 5]
FINAL_FORBIDDEN_PHRASES = [
    "confirmed Galactic-center point source",
    "confirmed source identity",
    "final production optics detectability",
    "final V404 detectability",
    "B diffuse focal-spot source",
    "selection best replaces baseline",
    "unqualified astrophysical discovery",
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_yaml(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=False), encoding="utf-8")


def f(row: dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        val = row.get(key, default)
        if val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def fmt(value: float, ndigits: int = 6) -> str:
    if not math.isfinite(value):
        return "nan"
    if value == 0:
        return "0"
    if abs(value) < 1e-3 or abs(value) >= 1e4:
        return f"{value:.{ndigits}e}"
    return f"{value:.{ndigits}g}"


def asimov_ts_from_bins(signal_cps: np.ndarray, background_cps: np.ndarray, exposure_s: float) -> float:
    signal = np.asarray(signal_cps, dtype=float) * exposure_s
    background = np.asarray(background_cps, dtype=float) * exposure_s
    floor = max(float(np.sum(background)) * 1e-9 / max(len(background), 1), 1e-12)
    background = np.maximum(background, floor)
    use = signal > 0
    if not np.any(use):
        return 0.0
    s = signal[use]
    b = background[use]
    return float(np.sum(2.0 * ((s + b) * np.log1p(s / b) - s)))


def solve_flux_for_sigma(response_bins: np.ndarray, background_bins: np.ndarray, exposure_s: float, sigma: float) -> float:
    lo, hi = 0.0, 1e-3
    while math.sqrt(asimov_ts_from_bins(hi * response_bins, background_bins, exposure_s)) < sigma:
        hi *= 2.0
        if hi > 1.0:
            return float("nan")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        got = math.sqrt(asimov_ts_from_bins(mid * response_bins, background_bins, exposure_s))
        if got >= sigma:
            hi = mid
        else:
            lo = mid
    return hi


def p_ge_3_for_flux(response_bins: np.ndarray, background_bins: np.ndarray, flux: float) -> float:
    sigma = math.sqrt(asimov_ts_from_bins(flux * response_bins, background_bins, EXPOSURE_S))
    return normal_survival(3.0 - sigma)


def ensure_dirs() -> None:
    for path in [OUT, FIG, TABLES, CONFIGS, PATCH, VALIDATION]:
        path.mkdir(parents=True, exist_ok=True)


def row_by_metric(rows: list[dict[str, str]], metric_id: str) -> dict[str, str]:
    for row in rows:
        if row["metric_id"] == metric_id:
            return row
    raise KeyError(metric_id)


def write_inputs_manifest() -> list[dict[str, Any]]:
    rows = []
    inputs = [
        ("phase12_guide", ROOT.parent / "511_final_phase12_guide.md", "final closure guide"),
        ("science_detector_source", ROOT / "run_configs" / "Science_511_onaxis_focalbeam_local.source", "detector response authority source"),
        ("phase11_crosswalk", PHASE11 / "metric_crosswalk_phase11.csv", "metric crosswalk input"),
        ("phase10_selection_audit", PHASE10 / "selection_best_measured_energy_audit.csv", "measured count-only selection audit"),
        ("phase9_detectability", ABC / "detectability_A_GC_POINT.csv", "Phase 9 ERL/design-Q source case table"),
        ("event_catalog", CATALOG_DEFAULT, "true-energy event catalog"),
        ("measured_catalog", MEASURED_DEFAULT, "measured-energy compact event catalog"),
        ("final_numerical_lineage", FINAL_LINEAGE, "background/response numerical lineage"),
    ]
    for item_id, path, role in inputs:
        rows.append(
            {
                "item_id": item_id,
                "path": rel(path) if path.is_relative_to(ROOT) else str(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else "",
                "role": role,
            }
        )
    write_csv(OUT / "inputs_manifest_final.csv", rows)
    return rows


def write_source_and_claim_configs(final_claim_level: str) -> None:
    write_yaml(
        CONFIGS / "source_cases_511_AB_final.yaml",
        {
            "status": "FINAL_AB_CASES_FOR_CURRENT_PROJECT",
            "detector_response_authority": "run_configs/Science_511_onaxis_focalbeam_local.source",
            "detector_response_forbidden_use": "replacement detector source",
            "cases": [
                {
                    "case_id": "A_GC_COMPACT_CENTER",
                    "role": "main science compact-source hypothesis",
                    "phase10_case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
                    "association_status": "assumption_only_not_claimed",
                    "allowed_use": "AB likelihood and requirements",
                    "forbidden_use": "Forbidden, not claimed: confirmed source identity",
                },
                {
                    "case_id": "B_GC_DIFFUSE_BULGE_DISK",
                    "role": "foreground/null model",
                    "handling": "aperture_or_future_focal_map_projection",
                    "forbidden_use": "focal-spot source",
                },
            ],
            "C_V404": {"role": "benchmark appendix only", "status": "closed_as_bandpass_risk_or_optional"},
        },
    )
    write_yaml(
        CONFIGS / "optics_response_511_final_or_parametric.yaml",
        {
            "optics_id": "PARAMETRIC_511_OPTICS_REQUIREMENTS_V1",
            "status": "PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION",
            "energy_grid_keV": [480, 490, 500, 510, 511, 512, 520, 530],
            "aeff_cm2_scan": [10, 25, 50, 75, 100, 150, 200],
            "fov_radius_arcmin_scan": [1, 2, 4.47, 8, 15],
            "psf_fwhm_arcmin_scan": [0.5, 1, 2, 4],
            "exposure_s_scan": [1.0e6, 2.5e6, 5.0e6],
            "claim_level": "PARAMETRIC_OPTICS_REQUIREMENT",
            "can_support_final_production_detectability": False,
            "forbidden_claim": "Forbidden, not claimed: final production optics detectability",
        },
    )
    write_yaml(
        CONFIGS / "likelihood_bins_final.yaml",
        {
            "energy_edges_keV": ENERGY_EDGES,
            "radius_edges_mm": [0, 3, 9, 18, "inf"],
            "layer_values": LAYER_VALUES,
            "feature_spaces": ["energy_only", "energy_radius", "energy_radius_layer"],
            "energy_axis": "measured",
        },
    )
    write_yaml(
        CONFIGS / "claim_policy_final.yaml",
        {
            "final_claim_level": final_claim_level,
            "allowed": [
                "validated detector/background response",
                "measured-template detector/background performance",
                "parametric optics requirement study",
                "compact-source hypothesis test against diffuse foreground/null model",
            ],
            "forbidden": [f"Forbidden, not claimed: {phrase}" for phrase in FINAL_FORBIDDEN_PHRASES],
            "repeated_error_rule": "If the same implementation or physics error occurs twice, stop trial-and-error, research 3-5 plausible fixes online, choose the shortest defensible fix, implement it, and record the decision.",
        },
    )


def write_authority_manifest() -> list[dict[str, Any]]:
    rows = [
        {
            "item_id": "science_detector_source",
            "path": "run_configs/Science_511_onaxis_focalbeam_local.source",
            "status": "AUTHORITY",
            "role": "post-optics Be-window detector response",
            "allowed_use": "signal response normalization",
            "forbidden_use": "named astrophysical source",
        },
        {
            "item_id": "background_ledger",
            "path": "reports2.0/07_NIMA_MANUSCRIPT/final_numerical_lineage.csv",
            "status": "AUTHORITY",
            "role": "prompt+delayed background ledger",
            "allowed_use": "sensitivity background",
            "forbidden_use": "mixed diagnostic total",
        },
        {
            "item_id": "measured_catalog",
            "path": "reports/phase2_real_flight_physical_production/event_catalog_v2_measured/event_catalog_v2_measured_compact.pkl",
            "status": "AUTHORITY",
            "role": "measured-energy detector catalog",
            "allowed_use": "measured-template likelihood",
            "forbidden_use": "final electronics simulation",
        },
        {
            "item_id": "source_cases_AB",
            "path": "reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/configs_final/source_cases_511_AB_final.yaml",
            "status": "FINAL_CASES",
            "role": "A/B astrophysical folding cases",
            "allowed_use": "compact-vs-diffuse test",
            "forbidden_use": "replacement detector source",
        },
        {
            "item_id": "optics_model",
            "path": "reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/configs_final/optics_response_511_final_or_parametric.yaml",
            "status": "FINAL_OR_PARAMETRIC",
            "role": "optics folding or requirement model",
            "allowed_use": "A/B response folding",
            "forbidden_use": "unlabeled final optics claim",
        },
        {
            "item_id": "selection_best",
            "path": "bgo30_r18_cent_single_top1_L5_keep",
            "status": "AUDITED_NOT_MAIN_UNLESS_GATE_PASS",
            "role": "analysis-only selection candidate",
            "allowed_use": "comparison and possible upgrade",
            "forbidden_use": "silent replacement of baseline",
        },
    ]
    write_csv(OUT / "authority_manifest_final.csv", rows)
    return rows


def build_measured_features() -> dict[str, Any]:
    with CATALOG_DEFAULT.open("rb") as fh:
        cat = pickle.load(fh)
    with MEASURED_DEFAULT.open("rb") as fh:
        meas = pickle.load(fh)
    true_e = np.asarray(cat["tes_total_keV"], dtype=float)
    meas_e = np.asarray(meas["tes_total_measured_keV"], dtype=float)
    candidate = ((true_e >= 480.0) & (true_e < 550.0)) | ((meas_e >= 480.0) & (meas_e < 550.0))
    indices = np.flatnonzero(candidate)
    return build_features_for_basis(cat, meas, indices, "measured")


def bin_indices(features: dict[str, Any], feature_space: str) -> tuple[np.ndarray, int, list[str]]:
    energy = np.asarray(features["tes_total_keV"], dtype=float)
    eidx = np.searchsorted(np.asarray(ENERGY_EDGES), energy, side="right") - 1
    valid = (eidx >= 0) & (eidx < len(ENERGY_EDGES) - 1)
    labels = [f"E{ENERGY_EDGES[i]:g}_{ENERGY_EDGES[i+1]:g}" for i in range(len(ENERGY_EDGES) - 1)]
    if feature_space == "energy_only":
        return np.where(valid, eidx, -1), len(ENERGY_EDGES) - 1, labels

    radius = np.asarray(features["centroid_r_mm"], dtype=float)
    ridx = np.searchsorted(np.asarray(RADIUS_EDGES), radius, side="right") - 1
    valid &= np.isfinite(radius) & (ridx >= 0) & (ridx < len(RADIUS_EDGES) - 1)
    nr = len(RADIUS_EDGES) - 1
    rlabels = ["r0_3mm", "r3_9mm", "r9_18mm", "r18_plus"]
    if feature_space == "energy_radius":
        idx = eidx * nr + ridx
        labels = [f"{el}_{rl}" for el in labels for rl in rlabels]
        return np.where(valid, idx, -1), (len(ENERGY_EDGES) - 1) * nr, labels

    if feature_space == "energy_radius_layer":
        layer = np.asarray(features["dominant_layer"], dtype=int)
        lidx = layer
        valid &= (lidx >= 0) & (lidx <= 5)
        idx = (eidx * nr + ridx) * len(LAYER_VALUES) + lidx
        labels = [f"{el}_{rl}_L{layer}" for el in labels for rl in rlabels for layer in LAYER_VALUES]
        return np.where(valid, idx, -1), (len(ENERGY_EDGES) - 1) * nr * len(LAYER_VALUES), labels
    raise ValueError(feature_space)


def metric_from_histograms(
    features: dict[str, Any],
    selection_id: str,
    feature_space: str,
    focused_broad_cps: float,
    b_diffuse_cps: float,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    selection = next(sel for sel in SELECTIONS if sel.selection_id == selection_id or (selection_id == "baseline" and sel.selection_id == "baseline"))
    mask = selection_mask(features, selection)
    idx, nbin, labels = bin_indices(features, feature_space)
    stream = np.asarray(features["stream"]).astype(str)
    rate = np.asarray(features["rate_hz"], dtype=float)
    valid = idx >= 0

    def hist(stream_name: str) -> np.ndarray:
        use = mask & valid & (stream == stream_name)
        return np.bincount(idx[use], weights=rate[use], minlength=nbin).astype(float)

    prompt = hist("prompt")
    delayed = hist("delayed")
    science = hist("science")
    response_bins = science / REFERENCE_FLUX
    response = float(np.sum(response_bins))
    instr_bins = prompt + delayed
    bg_shape = instr_bins.copy()
    if float(np.sum(bg_shape)) <= 0:
        bg_shape = np.ones(nbin) / nbin
    else:
        bg_shape = bg_shape / float(np.sum(bg_shape))
    focused = focused_broad_cps * max(response / CURRENT_RESPONSE, 0.0)
    bdiff = b_diffuse_cps
    background_bins = instr_bins + (focused + bdiff) * bg_shape
    f3_value = solve_flux_for_sigma(response_bins, background_bins, EXPOSURE_S, 3.0)
    f5_value = solve_flux_for_sigma(response_bins, background_bins, EXPOSURE_S, 5.0)
    p3_value = p_ge_3_for_flux(response_bins, background_bins, TARGET_FLUX)
    metric = {
        "selection_id": selection_id,
        "feature_space": feature_space,
        "background_cps": float(np.sum(background_bins)),
        "response_cps_per_flux": response,
        "F3_1Ms": f3_value,
        "F5_1Ms": f5_value,
        "P_ge_3sigma_at_1e-4_1Ms": p3_value,
        "bin_count": nbin,
        "focused_gamma_cps": focused,
        "B_diffuse_cps": bdiff,
    }
    arrays = {"response_bins": response_bins, "background_bins": background_bins, "labels": np.asarray(labels, dtype=object)}
    return metric, arrays


def build_metric_closure() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, np.ndarray]]]:
    phase11_rows = read_csv(PHASE11 / "metric_crosswalk_phase11.csv")
    p9 = row_by_metric(phase11_rows, "P09_A_baseline_mono_placeholder")
    p10 = row_by_metric(phase11_rows, "P10_A_baseline_count_only_L1")
    p9_sel = row_by_metric(phase11_rows, "P09_A_selection_best_design_Q")
    p10_sel = row_by_metric(phase11_rows, "P10_selection_best_measured_broad_count_only")
    abc_summary = json.loads((ABC / "source_case_summary.json").read_text(encoding="utf-8"))
    b_diffuse = float(abc_summary["checks"]["B_default_diffuse_cps"])
    focused = focused_gamma_rates(FOCUSED_DEFAULT)["broad_480_550"]
    features = build_measured_features()
    arrays_by_metric: dict[str, dict[str, np.ndarray]] = {}

    rows: list[dict[str, Any]] = []

    def add_reference(metric_id: str, source: dict[str, str], claim: str, primary: str) -> None:
        rows.append(
            {
                "metric_id": metric_id,
                "energy_axis": source.get("energy_axis", ""),
                "feature_space": source.get("template_dimension", ""),
                "selection_id": source.get("selection_variant", ""),
                "background_cps": f(source, "background_cps"),
                "response_cps_per_flux": f(source, "response_cps_per_flux"),
                "F3_1Ms": f(source, "F3_1Ms"),
                "F5_1Ms": f(source, "F5_1Ms"),
                "P_ge_3sigma_at_1e-4_1Ms": f(source, "P_ge_3sigma_at_1e-4_1Ms"),
                "ratio_to_phase9_ERL": f(source, "F3_1Ms") / f(p9, "F3_1Ms"),
                "ratio_to_phase10_count_only": f(source, "F3_1Ms") / f(p10, "F3_1Ms"),
                "claim_level": claim,
                "primary_metric_candidate": primary,
            }
        )

    add_reference("phase9_baseline_ERL", p9, "REFERENCE", "false")
    add_reference("phase10_baseline_count_only", p10, "REFERENCE", "false")

    for selection_id, label in [("baseline", "baseline"), ("bgo30_r18_cent_single_top1_L5_keep", "selection_best")]:
        for feature_space, fs_label in [("energy_only", "measured_E"), ("energy_radius", "measured_ER"), ("energy_radius_layer", "measured_ERL")]:
            metric, arrays = metric_from_histograms(features, selection_id, feature_space, focused, b_diffuse)
            metric_id = f"phase12_{label}_{fs_label}"
            arrays_by_metric[metric_id] = arrays
            rows.append(
                {
                    "metric_id": metric_id,
                    "energy_axis": "measured",
                    "feature_space": feature_space,
                    "selection_id": selection_id,
                    "background_cps": metric["background_cps"],
                    "response_cps_per_flux": metric["response_cps_per_flux"],
                    "F3_1Ms": metric["F3_1Ms"],
                    "F5_1Ms": metric["F5_1Ms"],
                    "P_ge_3sigma_at_1e-4_1Ms": metric["P_ge_3sigma_at_1e-4_1Ms"],
                    "ratio_to_phase9_ERL": metric["F3_1Ms"] / f(p9, "F3_1Ms"),
                    "ratio_to_phase10_count_only": metric["F3_1Ms"] / f(p10, "F3_1Ms"),
                    "claim_level": "MEASURED_TEMPLATE_ANALYSIS",
                    "primary_metric_candidate": "pending",
                }
            )

    base_erl = next(row for row in rows if row["metric_id"] == "phase12_baseline_measured_ERL")
    sel_erl = next(row for row in rows if row["metric_id"] == "phase12_selection_best_measured_ERL")
    gap_closed = abs(float(base_erl["F3_1Ms"]) / f(p9, "F3_1Ms") - 1.0) <= 0.20
    selection_improves_25 = float(sel_erl["F3_1Ms"]) <= 0.75 * float(base_erl["F3_1Ms"])
    selection_reproduces_phase9 = float(sel_erl["F3_1Ms"]) <= 1.20 * f(p9_sel, "F3_1Ms")
    selection_stable = selection_improves_25 and selection_reproduces_phase9
    production_optics_ready = False
    if gap_closed:
        primary_id = "phase12_selection_best_measured_ERL" if selection_stable else "phase12_baseline_measured_ERL"
        outcome = "A" if selection_stable and production_optics_ready else "B"
        final_claim_level = "MEASURED_TEMPLATE_ANALYSIS"
    else:
        primary_id = "phase12_baseline_measured_ERL"
        outcome = "C"
        final_claim_level = "PARAMETRIC_OPTICS_REQUIREMENT"
    for row in rows:
        if row["metric_id"] == primary_id:
            row["primary_metric_candidate"] = "true"
        elif row["primary_metric_candidate"] == "pending":
            row["primary_metric_candidate"] = "false"
    summary = {
        "status": "PASS_FINAL_METRIC_CLOSURE",
        "phase9_baseline_ERL_F3": f(p9, "F3_1Ms"),
        "phase10_baseline_count_only_F3": f(p10, "F3_1Ms"),
        "phase9_selection_design_Q_F3": f(p9_sel, "F3_1Ms"),
        "phase10_selection_measured_broad_F3": f(p10_sel, "F3_1Ms"),
        "phase12_baseline_measured_ERL_F3": float(base_erl["F3_1Ms"]),
        "phase12_selection_best_measured_ERL_F3": float(sel_erl["F3_1Ms"]),
        "metric_gap_closed_within_20pct": gap_closed,
        "selection_improves_baseline_by_25pct": selection_improves_25,
        "selection_reproduces_phase9_design_Q_within_20pct": selection_reproduces_phase9,
        "selection_performance_reproduced_under_final_metric": selection_stable,
        "production_optics_ready": production_optics_ready,
        "primary_metric_id": primary_id,
        "final_decision_code": outcome,
        "final_claim_level": final_claim_level,
    }
    write_csv(OUT / "metric_closure_final.csv", rows)
    write_json(OUT / "metric_closure_final.json", {"summary": summary, "rows": rows})
    return rows, summary, arrays_by_metric


def write_metric_reconciliation(summary: dict[str, Any]) -> None:
    if summary["metric_gap_closed_within_20pct"]:
        outcome = "Metric closure outcome B: measured ERL recovers the Phase 9 ERL sensitivity within tolerance, but production optics are not available. We adopt the measured ERL family for detector/background performance and keep optics as a parametric requirement."
    else:
        outcome = "Metric closure outcome C: measured ERL does not reproduce the Phase 9 ERL sensitivity within tolerance. The final package is closed as a conservative requirements and claim-control result."
    text = f"""# Phase 9 / Phase 10 / Phase 12 Reconciliation

Phase 12 closes the metric comparison by recomputing measured-template metrics on the measured-energy catalog.

## Input Anchors

- Phase 9 baseline ERL F3: `{fmt(summary['phase9_baseline_ERL_F3'])}`
- Phase 10 baseline count-only F3: `{fmt(summary['phase10_baseline_count_only_F3'])}`
- Phase 9 selection design-Q F3: `{fmt(summary['phase9_selection_design_Q_F3'])}`
- Phase 10 selection measured broad F3: `{fmt(summary['phase10_selection_measured_broad_F3'])}`

## Phase 12 Measured ERL

- baseline measured ERL F3: `{fmt(summary['phase12_baseline_measured_ERL_F3'])}`
- selection-best measured ERL F3: `{fmt(summary['phase12_selection_best_measured_ERL_F3'])}`
- gap closed within 20 percent: `{summary['metric_gap_closed_within_20pct']}`
- selection performance reproduced under final metric: `{summary['selection_performance_reproduced_under_final_metric']}`

## Outcome

{outcome}

The final package does not create a new source phase. Remaining optics and electronics limits are carried as final requirements and future work.
"""
    (OUT / "phase9_phase10_phase12_reconciliation.md").write_text(text, encoding="utf-8")


def write_selection_decision(summary: dict[str, Any]) -> dict[str, Any]:
    upgraded = bool(summary["selection_performance_reproduced_under_final_metric"])
    decision = {
        "selection_id": "bgo30_r18_cent_single_top1_L5_keep",
        "audit_executed": True,
        "performance_reproduced_under_final_metric": upgraded,
        "upgraded_to_main_analysis": upgraded,
        "allowed_use": "secondary measured-template comparison" if upgraded else "analysis-only design comparison unless final metric gate passes",
        "main_result_selection_id": "bgo30_r18_cent_single_top1_L5_keep" if upgraded else "baseline",
        "reason": (
            "selection measured ERL improves baseline and reproduces Phase 9 design-Q within tolerance"
            if upgraded
            else "selection measured ERL does not pass the final reproduction gate; baseline remains the main result"
        ),
    }
    write_json(OUT / "selection_upgrade_decision_final.json", decision)
    text = f"""# Final Selection Upgrade Decision

Selection: `bgo30_r18_cent_single_top1_L5_keep`

- audit executed: `{decision['audit_executed']}`
- performance reproduced under final metric: `{decision['performance_reproduced_under_final_metric']}`
- upgraded to main analysis: `{decision['upgraded_to_main_analysis']}`
- main result selection: `{decision['main_result_selection_id']}`

Reason: {decision['reason']}

Forbidden, not claimed: selection best replaces baseline without final metric reproduction.
"""
    (OUT / "selection_upgrade_decision_final.md").write_text(text, encoding="utf-8")
    return decision


def write_optics_status(summary: dict[str, Any]) -> dict[str, Any]:
    data = {
        "optics_id": "PARAMETRIC_511_OPTICS_REQUIREMENTS_V1",
        "status": "PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION",
        "real_or_production_optics_available": False,
        "final_claim_level": "PARAMETRIC_OPTICS_REQUIREMENT",
        "allowed_final_claim": "Requirements for compact-source detection under explicit parametric optics assumptions.",
        "forbidden_final_claim": "Forbidden, not claimed: final production detectability of the Galactic-center compact source.",
        "required_before_production": ["Aeff(E,theta)", "PSF", "FoV", "bandpass", "focal-plane mapping", "pointing/visibility"],
    }
    write_json(OUT / "optics_model_status_final.json", data)
    text = f"""# Final Optics Model Status

Current optics ending: `PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION`.

The project does not have a populated production `Aeff(E,theta)`, PSF, FoV, bandpass, focal-plane mapping, and pointing/visibility response. Phase 12 therefore freezes a parametric requirements model instead of claiming production optics performance.

Allowed final claim:

`{data['allowed_final_claim']}`

Forbidden:

`{data['forbidden_final_claim']}`
"""
    (OUT / "optics_model_status_final.md").write_text(text, encoding="utf-8")
    return data


def build_requirements(summary: dict[str, Any], metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [
        "phase10_baseline_count_only",
        "phase12_baseline_measured_ERL",
        "phase12_selection_best_measured_ERL",
        "phase9_baseline_ERL",
    ]
    by_id = {row["metric_id"]: row for row in metric_rows}
    rows = []
    for metric_id in wanted:
        row = by_id[metric_id]
        f3_value = float(row["F3_1Ms"])
        rows.append(
            {
                "metric_id": metric_id,
                "F3_current_ph_cm2_s": f3_value,
                "target_flux_ph_cm2_s": TARGET_FLUX,
                "required_response_gain": f3_value / TARGET_FLUX,
                "required_background_fraction": (TARGET_FLUX / f3_value) ** 2,
                "required_exposure_Ms": (f3_value / TARGET_FLUX) ** 2,
                "claim_level": row["claim_level"],
                "notes": "engineering requirement under current metric; not a production optics claim",
            }
        )
    write_csv(OUT / "optics_requirements_final.csv", rows)
    write_csv(OUT / "requirements_closure_final.csv", rows)
    return rows


def build_ab_likelihood(
    summary: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    arrays_by_metric: dict[str, dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {row["metric_id"]: row for row in metric_rows}
    base_metric_id = "phase12_baseline_measured_ERL"
    sel_metric_id = "phase12_selection_best_measured_ERL"
    rows = []
    injection_rows = []

    def add_row(metric_id: str, flux: float, exposure_s: float = EXPOSURE_S, response_scale: float = 1.0, label: str | None = None) -> None:
        metric = by_id[metric_id]
        arrays = arrays_by_metric[metric_id]
        response_bins = arrays["response_bins"] * response_scale
        background_bins = arrays["background_bins"]
        ts = asimov_ts_from_bins(flux * response_bins, background_bins, exposure_s)
        sigma = math.sqrt(ts)
        f3_value = solve_flux_for_sigma(response_bins, background_bins, exposure_s, 3.0)
        f5_value = solve_flux_for_sigma(response_bins, background_bins, exposure_s, 5.0)
        row_metric = label or metric_id
        rows.append(
            {
                "case_id": "A_GC_COMPACT_CENTER",
                "claim_level": summary["final_claim_level"],
                "optics_id": "PARAMETRIC_511_OPTICS_REQUIREMENTS_V1",
                "selection_id": metric["selection_id"],
                "metric_id": row_metric,
                "A_flux_ph_cm2_s": flux,
                "B_model_id": "B_GC_DIFFUSE_BULGE_DISK",
                "exposure_s": exposure_s,
                "background_cps": float(np.sum(background_bins)),
                "B_diffuse_cps": json.loads((ABC / "source_case_summary.json").read_text(encoding="utf-8"))["checks"]["B_default_diffuse_cps"],
                "A_signal_cps": float(flux * np.sum(response_bins)),
                "energy_axis": "measured",
                "spatial_template_axis": "focal_radius_placeholder",
                "layer_axis": "dominant_detector_layer",
                "hit_multiplicity_axis": "not_used_final_ERL",
                "TS_Asimov": ts,
                "sigma_Asimov": sigma,
                "P_ge_3sigma": normal_survival(3.0 - sigma),
                "F3_required": f3_value,
                "F5_required": f5_value,
                "required_response_gain_for_1e-4_3sigma": f3_value / TARGET_FLUX,
                "required_background_fraction_for_1e-4_3sigma": (TARGET_FLUX / f3_value) ** 2,
                "required_exposure_s_for_1e-4_3sigma": EXPOSURE_S * (f3_value / TARGET_FLUX) ** 2,
                "allowed_claim": "parametric requirement and measured-template detector/background performance; not final production optics detectability",
            }
        )
        injection_rows.append(
            {
                "metric_id": row_metric,
                "selection_id": metric["selection_id"],
                "input_flux_ph_cm2_s": flux,
                "exposure_s": exposure_s,
                "expected_sigma_Asimov": sigma,
                "P_ge_3sigma": normal_survival(3.0 - sigma),
                "recovery_model": "ASIMOV_REQUIREMENT_PROXY_NO_RANDOM_MC",
                "stable": math.isfinite(f3_value) and f3_value > 0,
                "notes": "Final package uses deterministic Asimov injection proxy; future production can replace with random injection recovery.",
            }
        )

    for flux in [0.5e-4, 1.0e-4, 1.5e-4, 2.0e-4]:
        add_row(base_metric_id, flux, label=f"A_flux_{flux / 1e-4:.1f}e-4_baseline")
    add_row(sel_metric_id, 1.0e-4, label="A_flux_1p0e-4_selection_candidate")
    add_row(base_metric_id, 1.0e-4, response_scale=50.0 / CURRENT_AEFF_CM2, label="requirements_scan_Aeff_50cm2")
    add_row(base_metric_id, 1.0e-4, response_scale=100.0 / CURRENT_AEFF_CM2, label="requirements_scan_Aeff_100cm2")
    add_row(base_metric_id, 1.0e-4, exposure_s=2.5e6, label="requirements_scan_exposure_2p5Ms")
    write_csv(OUT / "AB_template_likelihood_final.csv", rows)
    write_json(
        OUT / "AB_template_likelihood_final.json",
        {
            "status": "PASS_FINAL_AB_TEMPLATE_LIKELIHOOD",
            "rows": len(rows),
            "H0": "I_instr + B_diffuse",
            "H1": "I_instr + B_diffuse + A_compact",
            "claim_level": summary["final_claim_level"],
            "optics_id": "PARAMETRIC_511_OPTICS_REQUIREMENTS_V1",
        },
    )
    write_csv(OUT / "AB_injection_recovery_final.csv", injection_rows)
    return rows, injection_rows


def write_source_case_status() -> list[dict[str, Any]]:
    rows = [
        {
            "case_id": "A_GC_COMPACT_CENTER",
            "role": "main science case",
            "status": "ACTIVE",
            "final_handling": "AB likelihood and requirements",
            "allowed_claim": "compact-source hypothesis test",
            "forbidden_claim": "Forbidden, not claimed: confirmed source identity",
        },
        {
            "case_id": "B_GC_DIFFUSE_BULGE_DISK",
            "role": "foreground/null",
            "status": "ACTIVE",
            "final_handling": "aperture/focal-map projection",
            "allowed_claim": "diffuse null/foreground model",
            "forbidden_claim": "Forbidden, not claimed: focal-spot source",
        },
        {
            "case_id": "C_V404_2015_TRANSIENT_BENCHMARK",
            "role": "benchmark appendix",
            "status": "CLOSED_AS_BANDPASS_RISK_OR_OPTIONAL",
            "final_handling": "document line shift/width/time-profile risk",
            "allowed_claim": "benchmark relevance",
            "forbidden_claim": "Forbidden, not claimed: final V404 detectability",
        },
    ]
    write_csv(OUT / "source_case_status_final.csv", rows)
    return rows


def write_final_decision(summary: dict[str, Any]) -> None:
    if summary["final_decision_code"] == "A":
        title = "Decision A - production-style positive performance result"
        wording = "The final package supports a measured-template compact-source performance estimate under the stated optics model. The result can be used as the main compact-source sensitivity result for the current manuscript, with the listed limitations."
    elif summary["final_decision_code"] == "B":
        title = "Decision B - conservative measured-template result"
        wording = "The final package supports a conservative measured-template detector/background performance result and a parametric optics requirement study for testing the Galactic-center compact 511 keV source hypothesis. It does not claim final production optics detectability."
    else:
        title = "Decision C - requirements-only result"
        wording = "The final package closes the current study as a requirements and claim-control analysis. It identifies the response gain, background reduction, exposure, and optics information required before a production compact-source detectability claim can be made."
    text = f"""# Final Decision

{title}

{wording}

Final claim level: `{summary['final_claim_level']}`

Primary metric: `{summary['primary_metric_id']}`

Selection upgraded to main analysis: `{summary['selection_performance_reproduced_under_final_metric']}`

Optics status: `PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION`

Forbidden, not claimed: unqualified astrophysical discovery, confirmed source identity, final production optics detectability, final V404 detectability.
"""
    (OUT / "FINAL_DECISION.md").write_text(text, encoding="utf-8")


def write_claim_control(summary: dict[str, Any]) -> None:
    text = f"""# Final Claim Control

Final claim level: `{summary['final_claim_level']}`

Allowed:

- validated detector/background response
- measured-template detector/background performance
- parametric optics requirement study
- compact-source hypothesis test against diffuse foreground/null model

Forbidden:

"""
    text += "\n".join(f"- Forbidden, not claimed: {phrase}" for phrase in FINAL_FORBIDDEN_PHRASES)
    text += "\n\nRepeated-error rule:\n\nIf the same implementation or physics error occurs twice, stop trial-and-error, research 3-5 plausible fixes online, choose the shortest defensible fix, implement it, and record the decision.\n"
    (OUT / "final_claim_control.md").write_text(text, encoding="utf-8")


def write_paper_tables(metric_rows: list[dict[str, Any]], ab_rows: list[dict[str, Any]], requirements: list[dict[str, Any]]) -> None:
    shutil.copy2(FINAL_LINEAGE, TABLES / "table_numerical_lineage_final.csv")
    shutil.copy2(OUT / "metric_closure_final.csv", TABLES / "table_metric_closure_final.csv")
    write_csv(TABLES / "table_AB_detectability_final.csv", ab_rows)
    write_csv(TABLES / "table_optics_requirements_final.csv", requirements)
    claim_rows = [
        {"claim_level": "L1_PLACEHOLDER", "allowed": "placeholder source-case folding", "current_status": "superseded by final closure"},
        {"claim_level": "PARAMETRIC_OPTICS_REQUIREMENT", "allowed": "requirements under explicit optics assumptions", "current_status": "active if metric closure not sufficient"},
        {"claim_level": "MEASURED_TEMPLATE_ANALYSIS", "allowed": "measured-template detector/background performance", "current_status": "active only if metric closure is stable"},
        {"claim_level": "PRODUCTION_OPTICS_ANALYSIS", "allowed": "audited optics performance", "current_status": "not reached"},
        {"claim_level": "FINAL_PAPER_CLAIM", "allowed": "manuscript-ready performance statement with caveats", "current_status": "claim-control only, no discovery claim"},
    ]
    write_csv(TABLES / "table_claim_boundary_final.csv", claim_rows)


def write_manuscript_patch(summary: dict[str, Any]) -> None:
    final_sentence = (
        "本工作最终将银河中心 511 keV 紧致源问题表述为 A+B 与 B-only 的模板判别问题，其中 A 为中心紧致源假设，B 为通过光学 FoV/PSF 折叠的弥散核球/盘面 foreground/null model。当前 detector-response authority 仍为 Gate-A 修正后的 Be-window post-optics 511 keV response source；A/B 源不替代该 detector source。Phase 12 对 Phase 9 ERL/template 与 Phase 10 measured count-only 指标进行了闭合，并根据 measured-template 结果决定是否升级 selection-only best。若真实 optics response 尚未进入 production，本工作仅给出参数化 optics requirements 与 conservative measured-template performance，而不声称最终银河中心点源探测能力。"
    )
    (PATCH / "NIMA_final_results_insert_zh.md").write_text("# NIMA Final Results Insert\n\n" + final_sentence + "\n", encoding="utf-8")
    (PATCH / "NIMA_claim_control_insert_zh.md").write_text(
        "# NIMA Claim Control Insert\n\n"
        f"最终 claim level 为 `{summary['final_claim_level']}`。本文不声称最终银河中心点源探测、V404 最终探测能力、或 production optics 点源/弥散分离能力。selection-only best 未通过最终升级门时不得替代 baseline。\n",
        encoding="utf-8",
    )
    (PATCH / "PPT_final_update_notes.md").write_text(
        "# PPT Final Update Notes\n\n"
        "Slide title: Final result: compact-source hypothesis test, not endless source-case expansion\n\n"
        "- A: Galactic-center compact-source hypothesis.\n"
        "- B: diffuse bulge/disk null model through optics aperture/PSF.\n"
        "- Detector source remains generic post-optics Be-window authority.\n"
        "- Phase 9/10 metric gap closed or explicitly bounded.\n"
        "- Final output is either measured-template sensitivity or optics-requirements closure.\n",
        encoding="utf-8",
    )


def write_readme(summary: dict[str, Any]) -> None:
    text = f"""# Phase 12 Final Compact-Source Analysis

This is the terminal closure package for the current 511 keV compact-source analysis. No `13_...` directory is required for the current project.

## Final Decision

See `FINAL_DECISION.md`.

- final claim level: `{summary['final_claim_level']}`
- final decision code: `{summary['final_decision_code']}`
- primary metric: `{summary['primary_metric_id']}`
- measured metric gap closed within 20 percent: `{summary['metric_gap_closed_within_20pct']}`
- selection upgraded to main analysis: `{summary['selection_performance_reproduced_under_final_metric']}`
- optics status: `PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION`

## Final Scientific Question

Can the current 511 keV focusing-TES concept test a Galactic-center compact 511 keV source hypothesis against a diffuse Galactic foreground/null model, under explicitly stated optics, detector-response, background, selection, and statistical assumptions?

## Claim Boundary

The final package gives a measured-template or requirements closure. It does not claim unqualified astrophysical discovery, confirmed source identity, final production optics detectability, or final V404 detectability.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def plot_outputs(metric_rows: list[dict[str, Any]], summary: dict[str, Any], arrays_by_metric: dict[str, dict[str, np.ndarray]], ab_rows: list[dict[str, Any]], requirements: list[dict[str, Any]]) -> None:
    rows = [row for row in metric_rows if row["metric_id"].startswith("phase")]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.bar(range(len(rows)), [float(row["F3_1Ms"]) for row in rows], color=["#54A24B" if row["primary_metric_candidate"] == "true" else "#4C78A8" for row in rows])
    ax.set_yscale("log")
    ax.set_xticks(range(len(rows)), [row["metric_id"].replace("_", "\n") for row in rows], rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("F3, 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Final metric closure: Phase 9, Phase 10, Phase 12")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "metric_closure_phase9_phase10_phase12.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    labels = ["audit", "performance", "upgrade"]
    vals = [1, int(summary["selection_performance_reproduced_under_final_metric"]), int(summary["selection_performance_reproduced_under_final_metric"])]
    ax.bar(labels, vals, color=["#54A24B", "#E45756" if vals[1] == 0 else "#54A24B", "#E45756" if vals[2] == 0 else "#54A24B"])
    ax.set_ylim(0, 1.2)
    ax.set_yticks([0, 1], ["false", "true"])
    ax.set_title("Final selection decision matrix")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "selection_decision_matrix.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    req_use = [row for row in requirements if row["metric_id"] in {"phase10_baseline_count_only", "phase12_baseline_measured_ERL", "phase12_selection_best_measured_ERL"}]
    ax.bar([row["metric_id"].replace("_", "\n") for row in req_use], [float(row["required_response_gain"]) for row in req_use], color="#F58518")
    ax.axhline(1.0, color="#555555", ls="--", lw=1)
    ax.set_ylabel("Required response gain for 1e-4 / 1 Ms / 3 sigma")
    ax.set_title("Final optics/response requirement")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "optics_bandpass_or_requirement.png", dpi=220)
    plt.close(fig)

    arr = arrays_by_metric["phase12_baseline_measured_ERL"]
    bkg = arr["background_bins"]
    sig = arr["response_bins"] * TARGET_FLUX
    use = np.argsort(sig)[-25:]
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    x = np.arange(len(use))
    ax.plot(x, bkg[use] / max(np.sum(bkg[use]), 1e-30), marker="o", label="background fraction")
    ax.plot(x, sig[use] / max(np.sum(sig[use]), 1e-30), marker="s", label="A signal fraction")
    ax.set_xlabel("Top signal ERL bins")
    ax.set_ylabel("Normalized bin fraction")
    ax.set_title("A/B template overlap in final measured ERL proxy")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "AB_template_overlap.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for selection in sorted({row["selection_id"] for row in ab_rows if row["metric_id"].startswith("A_flux")}):
        sub = sorted([row for row in ab_rows if row["selection_id"] == selection and row["metric_id"].startswith("A_flux")], key=lambda row: float(row["A_flux_ph_cm2_s"]))
        ax.plot([float(row["A_flux_ph_cm2_s"]) for row in sub], [float(row["TS_Asimov"]) for row in sub], marker="o", label=selection)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("A flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("TS Asimov")
    ax.set_title("Final A+B vs B-only TS")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "TS_vs_A_flux.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    flux_grid = np.array([5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4])
    for metric_id in ["phase10_baseline_count_only", "phase12_baseline_measured_ERL", "phase12_selection_best_measured_ERL"]:
        row = next(row for row in metric_rows if row["metric_id"] == metric_id)
        f3_value = float(row["F3_1Ms"])
        ax.plot(flux_grid, (f3_value / flux_grid) ** 2, marker="o", label=metric_id)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Flux target (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("Required exposure (Ms)")
    ax.set_title("Exposure requirement versus compact-source flux")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "exposure_requirement_vs_flux.png", dpi=220)
    plt.close(fig)


def write_artifact_manifest() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != OUT / "artifact_manifest.csv":
            rows.append({"relative_path": rel(path), "bytes": path.stat().st_size})
    write_csv(OUT / "artifact_manifest.csv", rows)


def update_reports2_manifest() -> None:
    rows = []
    for path in sorted(R2.rglob("*")):
        if path.is_file():
            rows.append((str(path.relative_to(R2)), path.stat().st_size))
    with (R2 / "MANIFEST.tsv").open("w", encoding="utf-8") as fh:
        for rel_path, size in rows:
            fh.write(f"{rel_path}\t{size}\n")


def package_scripts() -> None:
    SCRIPT_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for script in ["make_phase12_final_closure.py", "validate_phase12_final_closure.py"]:
        src = ROOT / "tools" / script
        if src.exists():
            shutil.copy2(src, SCRIPT_PACKAGE_DIR / script)


def build_all() -> dict[str, Any]:
    ensure_dirs()
    write_inputs_manifest()
    write_authority_manifest()
    metric_rows, summary, arrays_by_metric = build_metric_closure()
    write_source_and_claim_configs(summary["final_claim_level"])
    write_metric_reconciliation(summary)
    selection_decision = write_selection_decision(summary)
    write_optics_status(summary)
    requirements = build_requirements(summary, metric_rows)
    ab_rows, injection_rows = build_ab_likelihood(summary, metric_rows, arrays_by_metric)
    write_source_case_status()
    write_final_decision(summary)
    write_claim_control(summary)
    write_paper_tables(metric_rows, ab_rows, requirements)
    write_manuscript_patch(summary)
    write_readme(summary)
    plot_outputs(metric_rows, summary, arrays_by_metric, ab_rows, requirements)
    package_scripts()
    phase12_summary = {
        "status": "PASS_PHASE12_FINAL_CLOSURE_PACKAGE_BUILT",
        "outdir": rel(OUT),
        "final_decision_code": summary["final_decision_code"],
        "final_claim_level": summary["final_claim_level"],
        "primary_metric_id": summary["primary_metric_id"],
        "selection_upgraded_to_main_analysis": selection_decision["upgraded_to_main_analysis"],
        "optics_status": "PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION",
        "metric_rows": len(metric_rows),
        "AB_likelihood_rows": len(ab_rows),
        "injection_recovery_rows": len(injection_rows),
    }
    write_json(OUT / "phase12_summary.json", phase12_summary)
    write_artifact_manifest()
    update_reports2_manifest()
    return phase12_summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Build the full final closure package.")
    args = ap.parse_args()
    summary = build_all()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
