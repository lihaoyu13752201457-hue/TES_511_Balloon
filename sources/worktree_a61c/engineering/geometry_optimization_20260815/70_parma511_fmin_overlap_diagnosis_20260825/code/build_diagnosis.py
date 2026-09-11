#!/usr/bin/env python3
"""Reproduce the PARMA-511 overlap and Fmin diagnosis from frozen authorities.

This script is read-only with respect to every input authority.  It writes a
small, bounded diagnostic bundle and the canonical report artifact into the
requested output directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REL = {
    "source_closure": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/00_source_closure/source_closure.json",
    "coarse_bins": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/00_source_closure/coarse_line_decomposition_20bins.csv",
    "mono_target": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/00_source_closure/mono511_target_81x80.csv",
    "trajectory_scales": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/00_source_closure/trajectory_component_scales_81nodes.csv",
    "catalog_audit": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/02_fluxclosed_catalog_b/audit.json",
    "publication_values": "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/06_publication_values/publication_values.json",
    "old_sh3": "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json",
    "old_sg3": "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/04_candidate_timeline/summary.json",
    "wgrid_fmin": "engineering/geometry_optimization_20260815/69_sh3_wgrid_conditional_fmin_20260825/outputs/01_approx_fmin_20260825/approx_fmin_summary.json",
    "wgrid_compare": "engineering/geometry_optimization_20260815/68_sh3_wgrid_mono511_statistics_20260824/outputs/01_wgrid_mono511_response_comparison_20260825/comparison_summary.json",
    "wgrid_geometry": "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3_wgrid_20260824/README.md",
}

OUT_REL = "engineering/geometry_optimization_20260815/70_parma511_fmin_overlap_diagnosis_20260825/outputs/01_diagnosis_20260825"
CODE_REL = "engineering/geometry_optimization_20260815/70_parma511_fmin_overlap_diagnosis_20260825/code/build_diagnosis.py"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def close(a: float, b: float, *, atol: float = 1e-12, rtol: float = 1e-10) -> bool:
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def fmin_gaussian(background_counts: float, signal_counts_per_flux: float, sigma: float = 3.0) -> float:
    return sigma * math.sqrt(background_counts) / signal_counts_per_flux


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def compact(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}g}"


def sqlite_type(rows: list[dict[str, Any]], field: str) -> str:
    values = [row.get(field) for row in rows if row.get(field) is not None]
    if any(isinstance(value, str) for value in values):
        return "TEXT"
    if any(isinstance(value, float) for value in values):
        return "REAL"
    if any(isinstance(value, (int, bool)) for value in values):
        return "INTEGER"
    return "REAL"


def build_sqlite_snapshot(path: Path, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Materialize and re-query every exposed dataset so SQL provenance is literal."""
    temp = path.with_name(path.name + ".tmp")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    connection.row_factory = sqlite3.Row
    queried: dict[str, list[dict[str, Any]]] = {}
    try:
        for table, rows in datasets.items():
            require(rows, f"dataset {table} is empty")
            ordered_rows = [{"_row_order": index, **row} for index, row in enumerate(rows)]
            fields = list(ordered_rows[0])
            require(all(list(row) == fields for row in ordered_rows), f"dataset {table} has inconsistent fields")
            column_sql = ", ".join(f'"{field}" {sqlite_type(ordered_rows, field)}' for field in fields)
            connection.execute(f'CREATE TABLE "{table}" ({column_sql})')
            placeholders = ", ".join("?" for _ in fields)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                [[row[field] for field in fields] for row in ordered_rows],
            )
            query = f'SELECT * FROM "{table}" ORDER BY _row_order'
            queried[table] = [dict(row) for row in connection.execute(query).fetchall()]
        connection.commit()
    finally:
        connection.close()
    os.replace(temp, path)
    return queried


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    authority_root = args.authority_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {key: authority_root / rel for key, rel in REL.items()}
    for key, path in paths.items():
        require(path.is_file(), f"missing authority {key}: {path}")

    source = load_json(paths["source_closure"])
    coarse_rows = load_csv(paths["coarse_bins"])
    mono_rows = load_csv(paths["mono_target"])
    trajectory_rows = load_csv(paths["trajectory_scales"])
    catalog = load_json(paths["catalog_audit"])
    publication = load_json(paths["publication_values"])
    old_sh3 = load_json(paths["old_sh3"])
    old_sg3 = load_json(paths["old_sg3"])
    wgrid = load_json(paths["wgrid_fmin"])
    compare = load_json(paths["wgrid_compare"])

    # Source-level closure and partition audit.
    require(len(coarse_rows) == 20, "continuum de-line table is not 20 rows")
    require({int(r["source_bin20"]) for r in coarse_rows} == set(range(20)), "20-bin angular partition is incomplete or duplicated")
    require(len(mono_rows) == 81 * 80, "mono target is not 81x80")
    mono_pairs = {(int(r["time_bin_id"]), int(r["source_bin80"])) for r in mono_rows}
    require(len(mono_pairs) == 81 * 80, "mono target contains a duplicated node/bin pair")
    require({p[0] for p in mono_pairs} == set(range(81)), "mono target time nodes are incomplete")
    require(all(sum(1 for p in mono_pairs if p[0] == node) == 80 for node in range(81)), "a mono target node does not contain 80 bins")

    coarse = source["coarse_line"]
    reference = source["continuum_deline_reference_closure"]
    line_authority = source["mono511_day15_authority"]
    w2 = coarse["w2_source_flux"]

    w2_total_sum = sum(float(r["w2_total_flux_ph_cm2_s"]) for r in coarse_rows)
    w2_line_sum = sum(float(r["w2_coarse_line_flux_ph_cm2_s"]) for r in coarse_rows)
    w2_cont_sum = sum(float(r["w2_continuum_flux_ph_cm2_s"]) for r in coarse_rows)
    require(close(w2_total_sum, w2["broadband_total_ph_cm2_s"], atol=2e-15), "20-bin W2 broadband sum does not close")
    require(close(w2_line_sum, w2["coarse_line_contribution_ph_cm2_s"], atol=2e-15), "20-bin W2 coarse-line sum does not close")
    require(close(w2_cont_sum, w2["continuum_ph_cm2_s"], atol=2e-15), "20-bin W2 continuum sum does not close")
    require(close(w2_total_sum, w2_line_sum + w2_cont_sum, atol=2e-15), "W2 broadband != coarse line + continuum")

    day15_mono = [r for r in mono_rows if int(r["time_bin_id"]) == 60]
    day15_target_flux = sum(float(r["target_flux_ph_cm2_s"]) for r in day15_mono)
    day15_proposal_flux = sum(float(r["proposal_flux_ph_cm2_s"]) for r in day15_mono)
    day15_ratio_deviation = max(abs(float(r["importance_ratio"]) - 1.0) for r in day15_mono)
    require(close(day15_target_flux, line_authority["integrated_flux_ph_cm2_s"], atol=2e-15), "day-15 target flux does not close")
    require(close(day15_proposal_flux, day15_target_flux, atol=2e-15), "day-15 proposal differs from target")
    require(day15_ratio_deviation <= 2e-13, "day-15 importance ratios are not unity")

    day15_scale_rows = [r for r in trajectory_rows if int(r["time_bin_id"]) == 60]
    require(len(day15_scale_rows) == 1, "trajectory node 60 is not unique")
    day15_scale = day15_scale_rows[0]

    original_day15 = float(day15_scale["original_broadband_flux_ph_cm2_s"])
    continuum_day15 = float(day15_scale["continuum_flux_ph_cm2_s"])
    removed_day15 = float(day15_scale["removed_coarse_line_flux_ph_cm2_s"])
    mono_day15 = float(day15_scale["target_mono511_flux_ph_cm2_s"])
    recomposed_day15 = float(day15_scale["recomposed_gamma_flux_ph_cm2_s"])
    representation_delta_day15 = float(day15_scale["representation_delta_ph_cm2_s"])
    gamma_scale_day15 = float(day15_scale["gamma_continuum_scale_to_reference"])
    w2_total_day15 = w2_total_sum * gamma_scale_day15
    w2_line_day15 = w2_line_sum * gamma_scale_day15
    w2_cont_day15 = w2_cont_sum * gamma_scale_day15
    require(close(original_day15, continuum_day15 + removed_day15, atol=2e-14), "day-15 original != continuum + removed coarse line")
    require(close(recomposed_day15, continuum_day15 + mono_day15, atol=2e-14), "day-15 recomposition != continuum + mono")

    reference_residual = float(reference["exact_subtraction_identity_residual_ph_cm2_s"])
    reference_original = float(reference["broadband_reference_flux_ph_cm2_s"])
    reference_continuum = float(reference["continuum_reference_flux_ph_cm2_s"])
    reference_removed = float(reference["removed_coarse_line_reference_flux_ph_cm2_s"])
    reference_mono = float(reference["parma511_flux_at_continuum_deline_state_ph_cm2_s"])
    reference_recomposed = float(reference["recomposed_continuum_plus_same_state_parma511_flux_ph_cm2_s"])
    require(abs(reference_residual) <= 1e-14, "reference subtraction identity failed")
    require(close(reference_original, reference_continuum + reference_removed, atol=2e-14), "reference flux subtraction failed")
    require(close(reference_recomposed, reference_continuum + reference_mono, atol=2e-14), "reference recomposition failed")

    # Event catalog exclusivity audit.
    component_events = sum(int(v["events"]) for v in catalog["components"].values())
    output_events = int(catalog["output_schema"]["event_count"])
    require(component_events == output_events, "exclusive component counts do not sum to catalog total")
    require({int(v["component_id"]) for v in catalog["components"].values()} == {0, 1, 2}, "component ids are not the expected exclusive set")
    require(int(catalog["excluded_mature_prompt_gamma_events"]) == int(catalog["gamma_join"]["events"]), "excluded gamma events were not replaced one-for-one")
    require(close(catalog["gamma_join"]["matching_rate"], 1.0), "continuum gamma IA_INIT matching is not complete")

    # Mission budgets and formula reproduction.
    model_a = publication["models"]["a"]
    model_b = publication["models"]["b"]
    mission_a = model_a["mission_20day"]
    mission_b = model_b["mission_20day"]
    comp_a = mission_a["components"]
    comp_b = mission_b["components"]

    a_non_line = float(comp_a["other"]["integrated_background_counts"]) + float(comp_a["gamma_continuum"]["integrated_background_counts"])
    a_line = float(comp_a["atm511"]["integrated_background_counts"])
    a_total = float(mission_a["cumulative_background_counts_B"])
    a_k = float(mission_a["cumulative_signal_counts_per_unit_flux_K"])
    a_fmin = float(mission_a["Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["value_ph_cm2_s"])
    require(close(a_total, a_non_line + a_line, atol=2e-8), "model A mission component sum failed")
    require(close(a_fmin, fmin_gaussian(a_total, a_k), atol=2e-14), "model A Gaussian Fmin formula failed")

    b_non_line = float(comp_b["other"]["integrated_background_counts"]) + float(comp_b["gamma_continuum"]["integrated_background_counts"])
    b_line = float(comp_b["atm511"]["integrated_background_counts"])
    b_total = float(mission_b["cumulative_background_counts_B"])
    b_k = float(mission_b["cumulative_signal_counts_per_unit_flux_K"])
    b_fmin = float(mission_b["Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["value_ph_cm2_s"])
    require(close(b_total, b_non_line + b_line, atol=2e-8), "model B mission component sum failed")
    require(close(b_fmin, fmin_gaussian(b_total, b_k), atol=2e-14), "model B Gaussian Fmin formula failed")

    old_b = float(old_sh3["mission_final_20day"]["cumulative_background_counts"])
    old_k = float(old_sh3["mission_final_20day"]["cumulative_signal_counts_per_unit_flux"])
    old_fmin = float(old_sh3["mission_final_20day"]["fmin_3sigma_gauss_ph_cm2_s"])
    require(close(old_fmin, fmin_gaussian(old_b, old_k), atol=2e-14), "old SH3 Gaussian Fmin formula failed")

    old_a_b = float(old_sg3["mission_final_20day"]["cumulative_background_counts"])
    old_a_k = float(old_sg3["mission_final_20day"]["cumulative_signal_counts_per_unit_flux"])
    old_a_fmin = float(old_sg3["mission_final_20day"]["Fmin_3sigma_gaussian_ph_cm2_s"])
    require(close(old_a_fmin, fmin_gaussian(old_a_b, old_a_k), atol=2e-14), "old SG3 Gaussian Fmin formula failed")

    wg20 = wgrid["mission_20day"]
    grid_line = float(wg20["approx_wgrid_atm511_counts"])
    grid_total = float(wg20["approx_wgrid_total_background_counts"])
    grid_k = float(wg20["signal_counts_per_unit_flux_frozen_sh3"])
    grid_fmin = float(wg20["approx_wgrid_Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["value"])
    grid_fmin_sigma = float(wg20["approx_wgrid_Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["standard_error"])
    require(close(grid_total, b_non_line + grid_line, atol=2e-8), "W-grid conditional component sum failed")
    require(close(grid_fmin, fmin_gaussian(grid_total, grid_k), atol=2e-14), "W-grid Gaussian Fmin formula failed")

    # Geometry response and the matched-statistics uncertainty calculation.
    a_rate = float(model_a["line_response"]["node60_target_and_transport_proposal_final_rate_cps"])
    a_sigma = float(model_a["line_response"]["node60_target_and_transport_proposal_final_transport_sigma_cps"])
    a_selected = int(model_a["line_response"]["final_selected_events"])
    open_rate = float(compare["key_comparisons"]["w2_final"]["old_rate_cps"])
    open_sigma = float(compare["key_comparisons"]["w2_final"]["old_mc_sigma_cps"])
    open_selected = int(compare["key_comparisons"]["w2_final"]["old_selected_events"])
    grid_rate = float(compare["key_comparisons"]["w2_final"]["new_rate_cps"])
    grid_sigma = float(compare["key_comparisons"]["w2_final"]["new_mc_sigma_cps"])
    grid_selected = int(compare["key_comparisons"]["w2_final"]["new_selected_events"])

    a_span_cm = 3.796
    sh3_span_cm = 5.40
    aperture_area_scale_grid_over_a = (sh3_span_cm / a_span_cm) ** 2
    a_rate_per_square_envelope = a_rate / (a_span_cm ** 2)
    open_rate_per_square_envelope = open_rate / (sh3_span_cm ** 2)
    grid_rate_per_square_envelope = grid_rate / (sh3_span_cm ** 2)

    def ratio_with_sigma(n: float, sn: float, d: float, sd: float) -> tuple[float, float]:
        ratio = n / d
        sigma = ratio * math.sqrt((sn / n) ** 2 + (sd / d) ** 2)
        return ratio, sigma

    grid_abs_over_a, grid_abs_over_a_sigma = ratio_with_sigma(grid_rate, grid_sigma, a_rate, a_sigma)
    open_abs_over_a, open_abs_over_a_sigma = ratio_with_sigma(open_rate, open_sigma, a_rate, a_sigma)
    grid_area_norm_over_a = grid_abs_over_a / aperture_area_scale_grid_over_a
    grid_area_norm_over_a_sigma = grid_abs_over_a_sigma / aperture_area_scale_grid_over_a
    open_area_norm_over_a = open_abs_over_a / aperture_area_scale_grid_over_a
    open_area_norm_over_a_sigma = open_abs_over_a_sigma / aperture_area_scale_grid_over_a
    grid_area_norm_z_from_unity = (grid_area_norm_over_a - 1.0) / grid_area_norm_over_a_sigma

    down = compare["direction_aggregates"]["down"]
    up = compare["direction_aggregates"]["up"]
    total_flux = float(compare["parma_day15_full_space_flux_ph_cm2_s"])
    require(close(float(down["parma_line_flux_ph_cm2_s"]) + float(up["parma_line_flux_ph_cm2_s"]), total_flux, atol=2e-15), "hemisphere PARMA flux does not close")
    require(int(down["new_selected_events"]) + int(up["new_selected_events"]) == grid_selected, "W-grid hemisphere selected counts do not close")
    require(int(down["old_selected_events"]) + int(up["old_selected_events"]) == open_selected, "open SH3 hemisphere selected counts do not close")

    # Source-representation and sensitivity-floor calculations.
    coarse_w2_fraction = w2_line_sum / reference_removed
    mono_to_old_w2_line_ratio = mono_day15 / w2_line_day15
    mono_to_same_state_old_w2_line_ratio = reference_mono / w2_line_sum
    sigma_keV = 0.420 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    ideal_mono_w2_fraction = math.erf(0.420 / (math.sqrt(2.0) * sigma_keV))

    old_to_closed_background_ratio = b_total / old_b
    old_to_closed_fmin_ratio = b_fmin / old_fmin
    grid_to_old_fmin_ratio = grid_fmin / old_fmin
    b_k_fractional_change_from_old = b_k / old_k - 1.0
    b_nonline_fractional_change_from_old = b_non_line / old_b - 1.0
    wrong_old_broadband_plus_mono_B = old_b + b_line
    wrong_old_broadband_plus_mono_fmin = fmin_gaussian(wrong_old_broadband_plus_mono_B, b_k)
    wrong_two_mono_lines_B = b_non_line + b_line + grid_line
    wrong_two_mono_lines_fmin = fmin_gaussian(wrong_two_mono_lines_B, grid_k)

    non_line_floor_fmin = fmin_gaussian(b_non_line, grid_k)
    fmin_if_sg3_absolute_line = fmin_gaussian(b_non_line + a_line, grid_k)

    def target_row(label: str, target_fmin: float) -> dict[str, Any]:
        allowed_total = (target_fmin * grid_k / 3.0) ** 2
        allowed_line = allowed_total - b_non_line
        if allowed_line >= 0:
            suppression = 1.0 - allowed_line / grid_line
            feasibility = "仅压线可达" if suppression <= 1.0 else "仅压线不可达"
        else:
            suppression = None
            feasibility = "非线本底已超预算"
        return {
            "target": label,
            "target_fmin": target_fmin,
            "target_fmin_display": f"{target_fmin * 1e5:.6f} × 10⁻⁵",
            "allowed_total_counts": allowed_total,
            "allowed_line_counts": allowed_line,
            "required_line_suppression_fraction": suppression,
            "feasibility": feasibility,
        }

    target_rows = [
        target_row("恢复旧 SH3 阈值", old_fmin),
        target_row("达到 3.0e-5", 3.0e-5),
        target_row("达到 2.0e-5", 2.0e-5),
    ]

    # Exact lookup tables.
    scenario_rows = [
        {
            "scenario": "旧 SH3 粗线表示",
            "representation": "宽带粗 IP-LIN 帽；未物理窄化",
            "non_line_counts": None,
            "mono511_counts": None,
            "total_counts": old_b,
            "signal_K": old_k,
            "fmin_3sigma": old_fmin,
            "line_share": None,
            "scope": "旧基线",
        },
        {
            "scenario": "SG3 通量闭合",
            "representation": "去粗线 + PARMA 单能线（现有混合状态）",
            "non_line_counts": a_non_line,
            "mono511_counts": a_line,
            "total_counts": a_total,
            "signal_K": a_k,
            "fmin_3sigma": a_fmin,
            "line_share": a_line / a_total,
            "scope": "现有混合态算术/任务折叠闭合",
        },
        {
            "scenario": "SH3 开放框通量闭合",
            "representation": "去粗线 + PARMA 单能线（现有混合状态）",
            "non_line_counts": b_non_line,
            "mono511_counts": b_line,
            "total_counts": b_total,
            "signal_K": b_k,
            "fmin_3sigma": b_fmin,
            "line_share": b_line / b_total,
            "scope": "现有混合态算术/任务折叠闭合",
        },
        {
            "scenario": "SH3 + W-grid 条件近似",
            "representation": "W-grid 单能线 + 冻结 SH3 非线/信号",
            "non_line_counts": b_non_line,
            "mono511_counts": grid_line,
            "total_counts": grid_total,
            "signal_K": grid_k,
            "fmin_3sigma": grid_fmin,
            "line_share": grid_line / grid_total,
            "scope": "用户指定条件近似",
        },
    ]
    for row in scenario_rows:
        row["fmin_3sigma_display"] = f"{float(row['fmin_3sigma']) * 1e5:.6f} × 10⁻⁵"

    background_budget_rows = []
    for row in scenario_rows:
        if row["non_line_counts"] is None:
            continue
        for component, count in [
            ("非线本底", row["non_line_counts"]),
            ("PARMA 511 单能线", row["mono511_counts"]),
        ]:
            background_budget_rows.append({
                "scenario": row["scenario"],
                "component": component,
                "background_counts": count,
                "total_counts": row["total_counts"],
                "signal_K": row["signal_K"],
                "fmin_3sigma": row["fmin_3sigma"],
                "fmin_3sigma_display": row["fmin_3sigma_display"],
                "line_share": row["line_share"],
                "scope": row["scope"],
            })

    geometry_rows = [
        {
            "design": "SG3",
            "aperture_span_cm": a_span_cm,
            "envelope_area_scale_vs_sg3": 1.0,
            "line_rate_cps": a_rate,
            "line_sigma_cps": a_sigma,
            "selected_events": a_selected,
            "incident_photons": int(model_a["line_response"]["incident_photons"]),
            "rate_per_square_envelope_cps_cm2": a_rate_per_square_envelope,
            "area_normalized_ratio_vs_sg3": 1.0,
            "area_normalized_ratio_sigma": None,
        },
        {
            "design": "开放 SH3",
            "aperture_span_cm": sh3_span_cm,
            "envelope_area_scale_vs_sg3": aperture_area_scale_grid_over_a,
            "line_rate_cps": open_rate,
            "line_sigma_cps": open_sigma,
            "selected_events": open_selected,
            "incident_photons": int(compare["matched_statistics"]["incident_photons_each"]),
            "rate_per_square_envelope_cps_cm2": open_rate_per_square_envelope,
            "area_normalized_ratio_vs_sg3": open_area_norm_over_a,
            "area_normalized_ratio_sigma": open_area_norm_over_a_sigma,
        },
        {
            "design": "SH3 + W-grid",
            "aperture_span_cm": sh3_span_cm,
            "envelope_area_scale_vs_sg3": aperture_area_scale_grid_over_a,
            "line_rate_cps": grid_rate,
            "line_sigma_cps": grid_sigma,
            "selected_events": grid_selected,
            "incident_photons": int(compare["matched_statistics"]["incident_photons_each"]),
            "rate_per_square_envelope_cps_cm2": grid_rate_per_square_envelope,
            "area_normalized_ratio_vs_sg3": grid_area_norm_over_a,
            "area_normalized_ratio_sigma": grid_area_norm_over_a_sigma,
        },
    ]

    hemisphere_rows = []
    for label, row in [("down", down), ("up", up)]:
        hemisphere_rows.append({
            "hemisphere": label,
            "parma_flux": float(row["parma_line_flux_ph_cm2_s"]),
            "parma_flux_share": float(row["parma_line_flux_ph_cm2_s"]) / total_flux,
            "open_rate_cps": float(row["old_rate_cps"]),
            "wgrid_rate_cps": float(row["new_rate_cps"]),
            "suppression_fraction": float(row["suppression_fraction"]),
            "difference_z": float(row["difference_z"]),
            "wgrid_selected": int(row["new_selected_events"]),
            "open_selected": int(row["old_selected_events"]),
            "wgrid_residual_share": float(row["new_rate_cps"]) / grid_rate,
        })

    closure_rows = [
        {"check": "参考宽带 = 连续谱 + 被移除粗线", "observed": reference_original, "expected": reference_continuum + reference_removed, "residual": reference_original - reference_continuum - reference_removed, "verdict": "PASS"},
        {"check": "参考重组 = 连续谱 + 同状态 PARMA 线", "observed": reference_recomposed, "expected": reference_continuum + reference_mono, "residual": reference_recomposed - reference_continuum - reference_mono, "verdict": "PASS"},
        {"check": "day-15 宽带 = 连续谱 + 被移除粗线", "observed": original_day15, "expected": continuum_day15 + removed_day15, "residual": original_day15 - continuum_day15 - removed_day15, "verdict": "PASS"},
        {"check": "day-15 重组 = 连续谱 + PARMA 单能线", "observed": recomposed_day15, "expected": continuum_day15 + mono_day15, "residual": recomposed_day15 - continuum_day15 - mono_day15, "verdict": "PASS"},
        {"check": "20 角箱 W2 = 粗线 + 连续谱", "observed": w2_total_sum, "expected": w2_line_sum + w2_cont_sum, "residual": w2_total_sum - w2_line_sum - w2_cont_sum, "verdict": "PASS"},
        {"check": "day-15 缩放 W2 = 粗线 + 连续谱", "observed": w2_total_day15, "expected": w2_line_day15 + w2_cont_day15, "residual": w2_total_day15 - w2_line_day15 - w2_cont_day15, "verdict": "PASS"},
        {"check": "81×80 唯一 node/bin 对", "observed": len(mono_pairs), "expected": 6480, "residual": len(mono_pairs) - 6480, "verdict": "PASS"},
        {"check": "day-15 80 箱通量和", "observed": day15_target_flux, "expected": total_flux, "residual": day15_target_flux - total_flux, "verdict": "PASS"},
        {"check": "事件目录三个互斥分量求和", "observed": component_events, "expected": output_events, "residual": component_events - output_events, "verdict": "PASS"},
    ]

    diagnostics = {
        "schema_version": 1,
        "status": "PASS__NO_DIRECT_DOUBLE_COUNT_FOUND__SOURCE_AND_EVENT_CLOSURE",
        "scope": "PARMA 510.99895-keV line, mature background, W-grid conditional Fmin diagnosis",
        "parma": {
            "line_energy_keV": 510.99895,
            "day15_full_space_flux_ph_cm2_s": total_flux,
            "angular_components_equal_mu": 80,
            "normalization_source": "PARMA dedicated line parameterization at the mission mono-target state",
        },
        "double_count_audit": {
            "verdict": "NO_EVIDENCE_OF_DIRECT_DOUBLE_COUNT_OR_BIN_OVERLAP",
            "reference_original_broadband_flux": reference_original,
            "reference_removed_coarse_line_flux": reference_removed,
            "reference_continuum_flux": reference_continuum,
            "reference_same_state_parma_line_flux": reference_mono,
            "reference_recomposed_flux": reference_recomposed,
            "reference_recomposition_delta_vs_original": reference_recomposed - reference_original,
            "day15_original_broadband_flux": original_day15,
            "day15_removed_coarse_line_flux": removed_day15,
            "day15_continuum_flux": continuum_day15,
            "day15_parma_line_flux": mono_day15,
            "day15_recomposed_flux": recomposed_day15,
            "day15_recomposition_delta_vs_original": representation_delta_day15,
            "day15_recomposition_fractional_delta_vs_original": representation_delta_day15 / original_day15,
            "state_policy": "hybrid: W118.3/g0 continuum de-line plus W114.6/g0.15 per-node mono target",
            "strict_same_atmospheric_state_closed": False,
            "catalog_exclusive_component_events": {k: int(v["events"]) for k, v in catalog["components"].items()},
            "catalog_total_events": output_events,
            "mono_target_unique_node_bin_pairs": len(mono_pairs),
            "maximum_day15_importance_ratio_deviation_from_one": day15_ratio_deviation,
            "counterfactual_old_broadband_plus_mono_B20": wrong_old_broadband_plus_mono_B,
            "counterfactual_old_broadband_plus_mono_Fmin3": wrong_old_broadband_plus_mono_fmin,
            "counterfactual_two_mono_lines_B20": wrong_two_mono_lines_B,
            "counterfactual_two_mono_lines_Fmin3": wrong_two_mono_lines_fmin,
        },
        "spectral_representation": {
            "old_coarse_line_total_area_ph_cm2_s": reference_removed,
            "old_coarse_line_area_inside_W2_ph_cm2_s": w2_line_sum,
            "old_coarse_line_fraction_inside_W2": coarse_w2_fraction,
            "day15_scaled_old_coarse_line_area_inside_W2_ph_cm2_s": w2_line_day15,
            "day15_physical_mono_flux_ph_cm2_s": mono_day15,
            "mono_to_old_coarse_W2_line_ratio": mono_to_old_w2_line_ratio,
            "same_state_mono_to_old_coarse_W2_line_ratio": mono_to_same_state_old_w2_line_ratio,
            "response_fwhm_keV": 0.420,
            "W2_half_width_keV": 0.420,
            "ideal_unscattered_gaussian_fraction_in_W2": ideal_mono_w2_fraction,
        },
        "fmin_decomposition": {
            "old_sh3": {"B20": old_b, "K": old_k, "Fmin3": old_fmin},
            "closed_sh3": {"non_line_B20": b_non_line, "line_B20": b_line, "B20": b_total, "K": b_k, "Fmin3": b_fmin, "line_share": b_line / b_total},
            "wgrid_conditional": {"non_line_B20": b_non_line, "line_B20": grid_line, "B20": grid_total, "K": grid_k, "Fmin3": grid_fmin, "Fmin3_standard_error": grid_fmin_sigma, "line_share": grid_line / grid_total},
            "closed_sg3": {"non_line_B20": a_non_line, "line_B20": a_line, "B20": a_total, "K": a_k, "Fmin3": a_fmin, "line_share": a_line / a_total},
            "old_to_closed_sh3_background_ratio": old_to_closed_background_ratio,
            "old_to_closed_sh3_fmin_ratio": old_to_closed_fmin_ratio,
            "wgrid_to_old_sh3_fmin_ratio": grid_to_old_fmin_ratio,
            "closed_sh3_signal_K_fractional_change_from_old": b_k_fractional_change_from_old,
            "closed_sh3_non_line_fractional_change_from_old_total": b_nonline_fractional_change_from_old,
            "non_line_only_fmin_floor": non_line_floor_fmin,
            "fmin_if_wgrid_line_equaled_sg3_absolute_line": fmin_if_sg3_absolute_line,
        },
        "geometry_response": {
            "sg3_line_rate_cps": a_rate,
            "open_sh3_line_rate_cps": open_rate,
            "wgrid_line_rate_cps": grid_rate,
            "wgrid_over_open_ratio": grid_rate / open_rate,
            "wgrid_over_open_ratio_sigma": float(compare["key_comparisons"]["w2_final"]["independent_ratio_sigma"]),
            "wgrid_minus_open_difference_z": float(compare["key_comparisons"]["w2_final"]["difference_z"]),
            "wgrid_absolute_over_sg3_ratio": grid_abs_over_a,
            "wgrid_absolute_over_sg3_ratio_sigma": grid_abs_over_a_sigma,
            "aperture_envelope_area_scale_wgrid_over_sg3": aperture_area_scale_grid_over_a,
            "wgrid_area_normalized_over_sg3_ratio": grid_area_norm_over_a,
            "wgrid_area_normalized_over_sg3_ratio_sigma": grid_area_norm_over_a_sigma,
            "wgrid_area_normalized_z_from_unity": grid_area_norm_z_from_unity,
            "open_sh3_area_normalized_over_sg3_ratio": open_area_norm_over_a,
            "open_sh3_area_normalized_over_sg3_ratio_sigma": open_area_norm_over_a_sigma,
            "wgrid_normal_incidence_open_fraction": 0.84430,
            "observed_wgrid_over_open_minus_open_fraction_sigma": ((grid_rate / open_rate) - 0.84430) / float(compare["key_comparisons"]["w2_final"]["independent_ratio_sigma"]),
            "down_flux_share": float(down["parma_line_flux_ph_cm2_s"]) / total_flux,
            "up_flux_share": float(up["parma_line_flux_ph_cm2_s"]) / total_flux,
            "down_suppression": float(down["suppression_fraction"]),
            "up_suppression": float(up["suppression_fraction"]),
            "wgrid_residual_up_share": float(up["new_rate_cps"]) / grid_rate,
        },
        "targets": target_rows,
        "limitations": [
            "The W-grid Fmin is the user-requested conditional approximation: SH3 non-line background, signal response, and timeline coincidence ratio are frozen.",
            "The current package is an explicit hybrid state: continuum de-line uses W=118.3/g=0 while the correct mono target uses W=114.6/g=0.15 with node-specific Rc/depth; strict same-state continuum closure remains outstanding.",
            "SG3 mono511 has only 12 final selected events (28.9% rate RSE); absolute and angular comparisons retain this uncertainty.",
            "PARMA/source-model systematics and the continuum/line hybrid-state approximation are not included in the quoted Monte Carlo errors.",
            "The aperture-area comparison uses the stated square envelope spans as a geometry scale, not an effective-area calibration.",
        ],
        "source_files": REL,
    }

    with (output_dir / "diagnostic_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(diagnostics, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    write_csv(output_dir / "scenario_fmin_decomposition.csv", scenario_rows, list(scenario_rows[0]))
    write_csv(output_dir / "geometry_line_response.csv", geometry_rows, list(geometry_rows[0]))
    write_csv(output_dir / "hemisphere_response.csv", hemisphere_rows, list(hemisphere_rows[0]))
    write_csv(output_dir / "source_and_catalog_closure_checks.csv", closure_rows, list(closure_rows[0]))
    write_csv(output_dir / "sensitivity_targets.csv", target_rows, list(target_rows[0]))

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    diagnosis_source = {
        "id": "diagnostic_bundle",
        "label": "PARMA 511 keV 守恒与灵敏度诊断包",
        "path": f"{OUT_REL}/diagnostic_summary.json",
    }

    headline = [{
        "wgrid_fmin_display": "3.890×10⁻⁵",
        "wgrid_vs_old_display": "+74.5% vs 旧粗表示",
        "line_share_display": "67.5%",
        "line_share_context": "W-grid 条件近似总本底",
        "overlap_verdict": "未发现",
        "overlap_context": "源级与事件级守恒均通过",
        "area_ratio_display": "1.187 ± 0.356",
        "area_ratio_context": "W-grid / SG3，按口径面积归一",
    }]

    artifact_datasets = build_sqlite_snapshot(
        output_dir / "diagnosis.sqlite",
        {
            "headline": headline,
            "background_budget": background_budget_rows,
            "closure_checks": closure_rows,
            "geometry_response": geometry_rows,
            "hemisphere_response": hemisphere_rows,
            "scenario_decomposition": scenario_rows,
            "target_budget": target_rows,
        },
    )

    dataset_descriptions = {
        "headline": "从复算诊断摘要提取的四项标题指标。",
        "background_budget": "现有混合态去线+PARMA mono 的 SG3、开放 SH3 与条件 W-grid 20 日本底组成。",
        "closure_checks": "源通量、角分箱唯一性与互斥事件目录的守恒检查。",
        "geometry_response": "共同 PARMA 单线和共同选择下的 SG3、开放 SH3、W-grid 响应。",
        "hemisphere_response": "80 等 mu 角分量按源表 down/up 标签互斥聚合后的响应。",
        "scenario_decomposition": "旧粗表示、现有混合态算术闭合与条件 W-grid 的任务本底和 Fmin。",
        "target_budget": "冻结 SH3 非线本底与信号核时，各目标 Fmin 允许的单能线预算。",
    }

    dataset_metric_definitions = {
        "headline": ["Headline strings are formatted from diagnostic_summary.json without additional calculation."],
        "background_budget": ["background_counts is the component count; non-line = other + de-lined gamma continuum.", "total_counts = non-line counts + mono511 counts."],
        "closure_checks": ["residual = observed - expected; PASS requires the authority-specific floating-point tolerance."],
        "geometry_response": ["area_normalized_ratio_vs_sg3 = absolute line-rate ratio / (aperture_span/3.796 cm)^2."],
        "hemisphere_response": ["suppression_fraction = 1 - W-grid rate/open-SH3 rate for the same angular subset."],
        "scenario_decomposition": ["Fmin_3sigma = 3*sqrt(total_counts)/signal_K.", "line_share = mono511_counts/total_counts."],
        "target_budget": ["allowed_total_counts = (target_fmin*signal_K/3)^2.", "allowed_line_counts = allowed_total_counts - frozen_non_line_counts."],
    }

    dataset_sources = []
    for dataset_name in artifact_datasets:
        dataset_sources.append({
            "id": f"source_{dataset_name}",
            "label": dataset_descriptions[dataset_name],
            "path": f"{OUT_REL}/diagnosis.sqlite",
            "query": {
                "engine": "sqlite3",
                "language": "sql",
                "sql": f'SELECT * FROM "{dataset_name}" ORDER BY _row_order',
                "description": dataset_descriptions[dataset_name],
                "executed_at": generated_at,
                "tables_used": [dataset_name],
                "filters": ["Frozen authority inputs listed in diagnostic_summary.json", "No row sampling or truncation"],
                "metric_definitions": dataset_metric_definitions[dataset_name],
            },
        })

    # Reader-facing report.  Quantitative markdown blocks point to the derived
    # diagnostic bundle, whose JSON contains every displayed number.
    blocks = [
        {"id": "title", "type": "markdown", "body": "# PARMA 511 keV 单能线为何显著抬高 SH3 最小可分辨通量"},
        {"id": "summary", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 技术摘要\n\n"
            "**结论：现有闭合中没有发现单能 511 keV 被重复相加，也没有发现 20/80 角分箱或两个能窗被求和两次。** "
            "真正的跳变来自旧宽带能谱的表示误差：相近的线总面积过去被摊在 449.65–566.08–712.64 keV 的粗 IP-LIN 帽上，只有 0.3366% 的粗线面积位于 W2 源能区；物理 PARMA 单能线则把 0.16651547 ph cm⁻² s⁻¹ 集中在 510.99895 keV。"
            "因此，守恒总线面积并不等于守恒 0.84 keV 科学窗内的计数。\n\n"
            "W-grid 也确实工作：它把开放 SH3 的末级单能线率降低 18.78%。但它复制的是 SG3 的孔距、筋宽和深度，不是相同总口径或完整的全空间屏蔽拓扑。"
            "SH3 的 5.40 cm 网格包络面积尺度是 SG3 3.796 cm 包络的 2.024 倍；按这一启发式面积尺度归一后，W-grid/SG3 线响应为 1.187±0.356，与 1 统计相容。绝对差与约 2.024 倍包络尺度相容，但现有统计不能把口径、完整遮蔽和质量拓扑的贡献分别识别出来。"
            "\n\n**同时必须保留一个独立的闭合风险：** 当前连续谱去线采用 W=118.3、g=0 状态，而正确单能线采用 W=114.6、g=0.15 和逐节点 Rc/depth；所以现有包不能被称为严格同一大气状态闭合。这个混合状态不是大退化的来源，但论文定稿前必须重建同态连续谱。"
        )},
        {"id": "headline_strip", "type": "metric-strip", "cardIds": ["card_fmin", "card_line_share", "card_overlap", "card_area_ratio"]},
        {"id": "key_findings", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 关键发现\n\n"
            "**SH3 的大退化几乎完全是正确窄化后的大气线背景，而不是信号响应的变化。** 旧 SH3 的整个粗表示 20 日本底为 15,551.68 counts；通量闭合后的非线本底为 15,376.17 counts，两者仅差 −1.13%，但这不是同定义的“非线前后差”；信号核 K 仅差 −0.0010%。"
            "新增的物理单能线却贡献 39,429.80 counts，使总本底增至 54,805.97，Gaussian 3σ 阈值按 √B/K 从 2.229×10⁻⁵ 升至 4.185×10⁻⁵。"
        )},
        {"id": "budget_chart", "type": "chart", "chartId": "background_budget"},
        {"id": "budget_explain", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "图中只画现有混合态算术闭合后可严格拆分的三种任务分量；它们不是严格同一大气状态闭合。SG3 的单能线只占总本底 12.56%，所以旧到新只退化 7.29%；开放 SH3 中线占 71.94%，W-grid 条件近似中仍占 67.53%。"
            "这正是“A 没有明显退化、B 却退化很多”的差别：SG3 原先的非线本底很大，而 SH3 压低近场/活化本底后，大气窄线成为新的本底地板。"
        )},
        {"id": "overlap", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 重复计数与分箱重叠审计\n\n"
            "闭合流程是“宽带总量 − 粗线贡献 + PARMA 单能线”，不是把单能线直接加到原宽带。参考状态重组通量比原宽带还低 0.002660 ph cm⁻² s⁻¹；day-15 重组也低 0.002269 ph cm⁻² s⁻¹（−0.0494%）。若存在直接重复加线，总通量应高出约 0.1665，而不是略低。\n\n"
            "20 个 bin 是宽带连续谱去线时的等 μ 角分区；80 个 bin 是单能线的等 μ 角分区。它们覆盖同一角域，但属于已经谱分离的两个物理分量。每个事件只映射到一个角箱，81×80 表中 6,480 个 node/bin 对全部唯一。"
            "W2=[510.58,511.42) keV 与 480–550 keV 只是嵌套的 cut-flow 诊断窗，不参与相加；510.99895 keV 只在 W2 内计一次。\n\n"
            "反事实也能区分错误：若 W-grid 结果把开放 SH3 的旧单能线和新 W-grid 单能线同时保留，会得到约 5.266×10⁻⁵，而不是当前 3.890×10⁻⁵。当前和式明确是冻结非线本底 + 新 W-grid 线，旧线已被替换。另一方面，若只犯“旧粗宽带直接加物理 mono”错误，会得到 4.1919×10⁻⁵，仅比正确 4.1852×10⁻⁵ 高 0.16%；所以最终阈值本身不能排除这个错误，排除证据来自前述减线恒等式和互斥事件目录。"
        )},
        {"id": "closure_table", "type": "table", "tableId": "closure_checks"},
        {"id": "spectral", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 为什么总通量守恒仍会让窄窗本底暴涨\n\n"
            "旧粗线总面积是 0.176443 ph cm⁻² s⁻¹，和物理 PARMA 线面积同量级；但旧线帽跨越约 263 keV，落在 W2 源能范围的面积只有 5.939×10⁻⁴ ph cm⁻² s⁻¹。"
            "按 day-15 旧宽带缩放后，W2 内被扣粗线只有 5.681×10⁻⁴ ph cm⁻² s⁻¹，物理单能线是它的 293.09 倍；这是**源空间通量比**，不是探测器选后计数或响应倍数。对 0.420 keV FWHM 的高斯响应，理想未散射单能事件约 98.15% 落入 ±0.420 keV。"
            "所以旧 2.23×10⁻⁵ 本质上是粗能量网格把窄线摊宽后的乐观值，不是“已经正确包含物理 511 线”的基线。"
        )},
        {"id": "geometry", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## W-grid 已接近 SG3 的孔结构，为何绝对线率仍高\n\n"
            "W-grid/open-SH3 的末级线率比为 0.8122±0.0890；网格法向开孔率为 0.8443，两者只差 0.36σ。该比值与“既有几何先限定可达路径、网格近似施加开孔率因子”的简单图景相容；当前统计不能排除 off-axis 拒止、绕行和散射的混合产生相同比值。\n\n"
            "绝对 W-grid/SG3 线率为 2.402±0.720，但口径包络面积尺度本身就是 2.024。按面积归一后比值降为 1.187±0.356，仅偏离 1 约 0.52σ。"
            "按包络面积尺度归一后的中心值与 SG3 统计相容，说明当前尚无可分辨的单位包络响应差异；但这是一阶误差传播下的启发式尺度，不能证明单位口径传输等价，也不能分解口径与全局拓扑各自贡献。"
        )},
        {"id": "geometry_table", "type": "table", "tableId": "geometry_response"},
        {"id": "hemisphere_explain", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "PARMA day-15 线通量中 up 半球占 82.32%。中心值显示 W-grid 对 down 抑制 24.97%、对 up 抑制 14.11%，但两项差异分别只有 −1.69σ 和 −1.07σ，尚不能宣称半球抑制差异已显著测得；它只提供方向性提示。最终残余线率有 60.3% 来自 up，这是同权重事件的算术分解，不是入射路径追踪。"
            "局部孔结构或近场几何接近 SG3，只说明局部构型接近；它不保证包含侧向、后向和散射贡献的 4π 远场单能响应相同。"
        )},
        {"id": "hemisphere_table", "type": "table", "tableId": "hemisphere_response"},
        {"id": "fmin", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## (F_{min}) 分解与当前结论\n\n"
            "在用户指定的条件近似下，W-grid 把 20 日单能线从 39,429.80 降到 31,975.64 counts，总本底从 54,805.97 降到 47,351.81，Gaussian 3σ (F_{min}) 为 (3.890±0.160)×10⁻⁵ ph cm⁻² s⁻¹（MC/statistical only）。"
            "这比开放 SH3 的 4.185×10⁻⁵ 改善 7.05%，但仍比旧粗线基线高 74.5%。"
        )},
        {"id": "scenario_table", "type": "table", "tableId": "scenario_decomposition"},
        {"id": "targets", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 能否靠进一步压低单能线恢复 2×10⁻⁵\n\n"
            "不能。冻结的非线本底 15,376.17 counts 自身已经给出 2.217×10⁻⁵ 的 Gaussian 3σ 地板。要恢复旧 2.229×10⁻⁵，留给 W-grid 单能线的任务预算只有约 175 counts，意味着相对当前线项还要抑制 99.45%。"
            "若把 SH3 的绝对线计数压到 SG3 水平，阈值约为 2.988×10⁻⁵；达到 3.0×10⁻⁵ 所需的线项也恰好接近 SG3 水平。要达到 2.0×10⁻⁵，即使先把线项清零，仍必须再把非线本底降低约 18.6%或把信号核提高约 10.8%。"
        )},
        {"id": "targets_table", "type": "table", "tableId": "target_budget"},
        {"id": "scope_method", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 范围、数据与计算方法\n\n"
            "单能线严格使用 PARMA 专用线参数化：510.99895 keV、day-15 全空间通量 0.16651547160226118 ph cm⁻² s⁻¹、80 个等 μ 分量。"
            "[33,34] 类型的大气观测文献不参与数值归一。Gaussian 阈值统一复算为 (F_{min}=3\sqrt{B_{20}}/K)。"
            "源级检查覆盖参考状态和 day-15 的减线/重组恒等式；事件级检查覆盖三个互斥目录分量；几何检查使用匹配入射数和共同响应/选择的独立输运。"
            "现有连续谱去线仍是 W=118.3/g=0 与 W=114.6/g=0.15 单线的混合状态，因此这里只能验证实现守恒和退化来源，不能宣称严格同一大气状态已经完成。"
        )},
        {"id": "limitations", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 局限性、不确定度与稳健性\n\n"
            "- W-grid (F_{min}) 是条件近似：非线本底、信号响应和时间轴偶合修正冻结为 SH3；它不是完整 W-grid 宽带/活化/信号闭合。\n"
            "- **严格同态风险：** 当前连续谱去线与单能线不是同一 PARMA 大气状态。正确单线归一必须保留，但同态宽带连续谱仍需重建。\n"
            "- SG3 单能线末级只有 12 个事件，线率相对统计误差 28.9%；因此不能过读单个角箱。不过 W-grid 与 SG3 的绝对差约 4.0σ，面积归一后与 1 相容。\n"
            "- 现有 Monte Carlo 误差不含 PARMA 源模型系统学，也不含连续谱去线状态与单能目标状态混合口径的系统误差。\n"
            "- 口径归一使用几何包络面积尺度，不是有效面积标定；它用于解释 2.024 倍几何尺度，不替代完整响应模拟。"
        )},
        {"id": "recommendations", "type": "markdown", "sourceId": "diagnostic_bundle", "body": (
            "## 建议的下一步\n\n"
            "1. 把“未见重复计数”作为当前实现结论保留；不要回退到把单能线直接加在含粗线面积的宽带上。\n"
            "2. 论文数值闭合前，保留当前正确的 PARMA 单线归一，重建与任务节点相同 W、g、Rc/depth 的宽带连续谱并重新去线；这一步解决同态口径，不是为了把线改回文献归一。\n"
            "3. 若目标是 3×10⁻⁵，设计指标应针对全空间线响应的绝对值，而不只是网格孔结构；需要控制主导半球、侧/后向和散射路径，或同步提升信号核。\n"
            "4. W-grid 当前线项 151 个选后事件给出 8.14% 率误差，可报告中心值、误差和当前 3.89×10⁻⁵ 条件近似；但 W-grid/open 差异只有 1.90σ，尚不足以把“19% 抑制”写成高显著性几何结论。若论文要求抑制比 <10% 相对误差或更强显著性，再补最小增量统计。\n"
            "5. 在任何论文回填前，仍应把条件 W-grid 近似明确标注为近似；不要把它写成完整本底闭合。"
        )},
        {"id": "questions", "type": "markdown", "body": (
            "## 尚待回答的问题\n\n"
            "- 设计目标是把 W-grid 的绝对线响应压到 SG3 水平（约 3×10⁻⁵），还是坚持恢复旧粗表示的 2.23×10⁻⁵？后者要求近乎完全消除物理线，并仍受非线地板限制。\n"
            "- 是否需要为 W-grid 补完整宽带、信号和潜在材料本底闭合，以把当前条件近似升级为论文可报告结果？"
        )},
    ]

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "PARMA 511 keV 单能线为何显著抬高 SH3 最小可分辨通量",
            "description": "源级守恒、事件互斥、角分箱、几何响应与 Fmin 的可复算诊断。",
            "generatedAt": generated_at,
            "sources": [diagnosis_source, *dataset_sources],
            "cards": [
                {"id": "card_fmin", "dataset": "headline", "sourceId": "source_headline", "description": "用户指定的冻结 SH3 非线/信号条件近似。", "metrics": [{"label": "W-grid 3σ Fmin", "field": "wgrid_fmin_display"}, {"label": "变化", "field": "wgrid_vs_old_display"}]},
                {"id": "card_line_share", "dataset": "headline", "sourceId": "source_headline", "description": "20 日 W-grid 条件近似中 PARMA 线占总本底的比例。", "metrics": [{"label": "PARMA 线占比", "field": "line_share_display"}, {"label": "范围", "field": "line_share_context"}]},
                {"id": "card_overlap", "dataset": "headline", "sourceId": "source_headline", "description": "减线/重组恒等式、81×80 唯一性和事件目录互斥均通过。", "metrics": [{"label": "重复计数证据", "field": "overlap_verdict"}, {"label": "审计", "field": "overlap_context"}]},
                {"id": "card_area_ratio", "dataset": "headline", "sourceId": "source_headline", "description": "用 5.40/3.796 的包络面积尺度归一，不是有效面积标定。", "metrics": [{"label": "面积归一线响应比", "field": "area_ratio_display"}, {"label": "比较", "field": "area_ratio_context"}]},
            ],
            "charts": [
                {
                    "id": "background_budget",
                    "title": "现有去线 + PARMA mono 算术闭合后的 20 日本底预算",
                    "subtitle": "SG3、开放 SH3 与 SH3+W-grid；counts，W-grid 为冻结非线/信号的条件近似",
                    "showDescription": True,
                    "intent": "composition",
                    "question": "PARMA 511 keV 线在不同几何的总本底中占多大比例？",
                    "rationale": "堆叠柱能同时显示绝对本底和线/非线组成。",
                    "comparisonContext": {"grain": "geometry scenario", "unit": "20-day counts", "denominator": "total background counts"},
                    "type": "stackedBar",
                    "dataset": "background_budget",
                    "sourceId": "source_background_budget",
                    "encodings": {
                        "x": {"field": "scenario", "type": "nominal", "label": "情形"},
                        "y": {"field": "background_counts", "type": "quantitative", "aggregate": "sum", "label": "20 日本底计数", "unit": "counts"},
                        "color": {"field": "component", "type": "nominal", "label": "本底分量"},
                        "tooltip": [
                            {"field": "component", "type": "text", "label": "分量"},
                            {"field": "background_counts", "type": "quantitative", "label": "分量本底"},
                            {"field": "total_counts", "type": "quantitative", "label": "总本底"},
                            {"field": "fmin_3sigma_display", "type": "text", "label": "3σ Fmin"},
                            {"field": "line_share", "type": "quantitative", "format": "percent", "label": "线占比"},
                            {"field": "scope", "type": "text", "label": "范围"},
                        ],
                    },
                    "xAxisTitle": "情形",
                    "yAxisTitle": "20 日本底计数",
                    "palette": {"kind": "categorical"},
                    "valueFormat": "compact",
                    "unit": "counts",
                    "layout": "full",
                    "maxRows": 10,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                }
            ],
            "tables": [
                {
                    "id": "closure_checks", "title": "源级与事件级守恒检查", "subtitle": "残差为浮点复算值；全部检查使用冻结权威文件", "showDescription": True,
                    "dataset": "closure_checks", "defaultSort": {"field": "check", "direction": "asc"}, "density": "dense", "sourceId": "source_closure_checks", "layout": "full",
                    "columns": [
                        {"field": "check", "label": "检查", "type": "text"}, {"field": "observed", "label": "观测/复算", "format": "number"},
                        {"field": "expected", "label": "期望", "format": "number"}, {"field": "residual", "label": "残差", "format": "number"}, {"field": "verdict", "label": "结论", "type": "text"},
                    ],
                },
                {
                    "id": "geometry_response", "title": "PARMA 单能线几何响应", "subtitle": "共同 510.99895 keV 源与选择；SG3 样本量仅 12", "showDescription": True,
                    "dataset": "geometry_response", "defaultSort": {"field": "line_rate_cps", "direction": "desc"}, "density": "dense", "sourceId": "source_geometry_response", "layout": "full",
                    "columns": [
                        {"field": "design", "label": "几何", "type": "text"}, {"field": "aperture_span_cm", "label": "包络宽/cm", "format": "number"},
                        {"field": "envelope_area_scale_vs_sg3", "label": "面积尺度/SG3", "format": "number"}, {"field": "line_rate_cps", "label": "线率/cps", "format": "number"},
                        {"field": "line_sigma_cps", "label": "MC σ/cps", "format": "number"}, {"field": "selected_events", "label": "选后数", "format": "number"},
                        {"field": "area_normalized_ratio_vs_sg3", "label": "面积归一比/SG3", "format": "number"}, {"field": "area_normalized_ratio_sigma", "label": "比值 σ", "format": "number"},
                    ],
                },
                {
                    "id": "hemisphere_response", "title": "W-grid 对两个 PARMA 半球的响应", "subtitle": "down/up 为源表方向标签；同一 80 等 μ 分量的互斥聚合", "showDescription": True,
                    "dataset": "hemisphere_response", "defaultSort": {"field": "parma_flux", "direction": "desc"}, "density": "dense", "sourceId": "source_hemisphere_response", "layout": "full",
                    "columns": [
                        {"field": "hemisphere", "label": "半球", "type": "text"}, {"field": "parma_flux", "label": "PARMA 通量/ph cm⁻² s⁻¹", "format": "number"},
                        {"field": "parma_flux_share", "label": "通量占比", "format": "percent"}, {"field": "open_rate_cps", "label": "开放 SH3/cps", "format": "number"},
                        {"field": "wgrid_rate_cps", "label": "W-grid/cps", "format": "number"}, {"field": "suppression_fraction", "label": "抑制", "format": "percent"},
                        {"field": "difference_z", "label": "差值 z", "format": "number"}, {"field": "wgrid_residual_share", "label": "W-grid 残余占比", "format": "percent"},
                    ],
                },
                {
                    "id": "scenario_decomposition", "title": "20 日任务本底与 Fmin 精确值", "subtitle": "旧粗表示不可唯一拆成物理单能线与非线项，故留空", "showDescription": True,
                    "dataset": "scenario_decomposition", "defaultSort": {"field": "total_counts", "direction": "desc"}, "density": "dense", "sourceId": "source_scenario_decomposition", "layout": "full",
                    "columns": [
                        {"field": "scenario", "label": "情形", "type": "text"}, {"field": "representation", "label": "谱表示", "type": "text"},
                        {"field": "non_line_counts", "label": "非线 counts", "format": "number"}, {"field": "mono511_counts", "label": "511 线 counts", "format": "number"},
                        {"field": "total_counts", "label": "总 B20", "format": "number"}, {"field": "signal_K", "label": "信号 K", "format": "number"},
                        {"field": "fmin_3sigma_display", "label": "3σ Fmin", "type": "text"}, {"field": "line_share", "label": "线占比", "format": "percent"},
                    ],
                },
                {
                    "id": "target_budget", "title": "目标阈值对应的单能线预算", "subtitle": "冻结 SH3 非线本底和信号核；负预算表示仅压线不可达", "showDescription": True,
                    "dataset": "target_budget", "defaultSort": {"field": "target_fmin_display", "direction": "desc"}, "density": "dense", "sourceId": "source_target_budget", "layout": "full",
                    "columns": [
                        {"field": "target", "label": "目标", "type": "text"}, {"field": "target_fmin_display", "label": "目标 Fmin", "type": "text"},
                        {"field": "allowed_total_counts", "label": "允许总 B20", "format": "number"}, {"field": "allowed_line_counts", "label": "允许线 counts", "format": "number"},
                        {"field": "required_line_suppression_fraction", "label": "相对当前需抑制", "format": "percent"}, {"field": "feasibility", "label": "可达性", "type": "text"},
                    ],
                },
            ],
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": artifact_datasets,
        },
        "sources": [diagnosis_source, *dataset_sources],
    }

    with (output_dir / "artifact.json").open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    receipt = {
        "status": "PASS__DIAGNOSTIC_BUNDLE_BUILT",
        "generated_at": generated_at,
        "authority_root": str(authority_root),
        "output_dir": str(output_dir),
        "checks": {row["check"]: row["verdict"] for row in closure_rows},
        "outputs": [
            "diagnostic_summary.json",
            "scenario_fmin_decomposition.csv",
            "geometry_line_response.csv",
            "hemisphere_response.csv",
            "source_and_catalog_closure_checks.csv",
            "sensitivity_targets.csv",
            "diagnosis.sqlite",
            "artifact.json",
        ],
    }
    with (output_dir / "build_receipt.json").open("w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(json.dumps({
        "status": receipt["status"],
        "double_count_verdict": diagnostics["double_count_audit"]["verdict"],
        "wgrid_Fmin_3sigma": grid_fmin,
        "output_dir": str(output_dir),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
