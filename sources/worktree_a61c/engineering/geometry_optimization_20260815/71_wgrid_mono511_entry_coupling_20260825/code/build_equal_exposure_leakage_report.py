#!/usr/bin/env python3
"""Compare SG3 and SH3+W-grid atmospheric-511 leakage at equal exposure.

This is a read-only transformation of the completed package-67/package-68
catalogs.  It distinguishes any recorded TES energy deposition from final
science-window leakage and never starts transport.
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
from typing import Any

import numpy as np
from scipy.stats import beta, binomtest


SG3_BASE_REL = "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/01_line_response_a"
WGRID_BASE_REL = "engineering/geometry_optimization_20260815/68_sh3_wgrid_mono511_statistics_20260824/outputs/01_wgrid_mono511_response_comparison_20260825"
PUB_REL = "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/06_publication_values/publication_values.json"
WGRID_MISSION_REL = "engineering/geometry_optimization_20260815/69_sh3_wgrid_conditional_fmin_20260825/outputs/01_approx_fmin_20260825/approx_fmin_summary.json"
OUT_REL = "engineering/geometry_optimization_20260815/71_wgrid_mono511_entry_coupling_20260825/outputs/02_equal_exposure_leakage_20260825"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sqlite_type(rows: list[dict[str, Any]], field: str) -> str:
    values = [row[field] for row in rows if row.get(field) is not None]
    if any(isinstance(value, str) for value in values):
        return "TEXT"
    if any(isinstance(value, float) for value in values):
        return "REAL"
    return "INTEGER"


def build_sqlite(path: Path, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    connection.row_factory = sqlite3.Row
    queried: dict[str, list[dict[str, Any]]] = {}
    try:
        for table, rows in datasets.items():
            require(bool(rows), f"dataset {table} is empty")
            ordered = [{"_row_order": index, **row} for index, row in enumerate(rows)]
            fields = list(ordered[0])
            require(all(list(row) == fields for row in ordered), f"inconsistent fields in {table}")
            columns = ", ".join(f'"{field}" {sqlite_type(ordered, field)}' for field in fields)
            connection.execute(f'CREATE TABLE "{table}" ({columns})')
            placeholders = ", ".join("?" for _ in fields)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                [[row[field] for field in fields] for row in ordered],
            )
            queried[table] = [
                dict(row)
                for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY _row_order').fetchall()
            ]
        connection.commit()
    finally:
        connection.close()
    os.replace(temp, path)
    return queried


def ratio_and_sigma(a: float, sa: float, b: float, sb: float) -> tuple[float, float]:
    ratio = a / b
    return ratio, ratio * math.sqrt((sa / a) ** 2 + (sb / b) ** 2)


def exact_poisson_rate_ratio_interval(
    count_a: int,
    exposure_a: float,
    count_b: int,
    exposure_b: float,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Conditional exact interval for (count_a/exposure_a)/(count_b/exposure_b)."""
    require(count_a > 0 and count_b > 0, "exact finite rate-ratio interval requires positive counts")
    alpha = 1.0 - confidence
    p_low = float(beta.ppf(alpha / 2.0, count_a, count_b + 1))
    p_high = float(beta.ppf(1.0 - alpha / 2.0, count_a + 1, count_b))
    scale = exposure_b / exposure_a
    return p_low / (1.0 - p_low) * scale, p_high / (1.0 - p_high) * scale


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.transport_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    sg3_summary = read_json(root / SG3_BASE_REL / "summary.json")
    wgrid_summary = read_json(root / WGRID_BASE_REL / "response/summary.json")
    comparison = read_json(root / WGRID_BASE_REL / "comparison_summary.json")
    publication = read_json(root / PUB_REL)
    wgrid_mission = read_json(root / WGRID_MISSION_REL)
    sg3_cutflow = read_csv(root / SG3_BASE_REL / "mono_line_cutflow.csv")
    wgrid_cutflow = read_csv(root / WGRID_BASE_REL / "response/mono_line_cutflow.csv")

    require(float(comparison["line_energy_keV"]) == 510.99895, "line energy mismatch")
    require(int(comparison["metadata"]["angular_components_equal_mu"]) == 80 if "metadata" in comparison else True,
            "angular component mismatch")
    require(math.isclose(float(comparison["parma_day15_full_space_flux_ph_cm2_s"]), 0.16651547160226118, rel_tol=0, abs_tol=1e-15),
            "PARMA day-15 flux mismatch")

    records: dict[str, dict[str, Any]] = {}
    for key, label, summary, catalog_path, cutflow in (
        ("sg3", "SG3", sg3_summary, root / SG3_BASE_REL / "mono_line_event_catalog.npz", sg3_cutflow),
        ("wgrid", "SH3 + W-grid", wgrid_summary, root / WGRID_BASE_REL / "response/mono_line_event_catalog.npz", wgrid_cutflow),
    ):
        with np.load(catalog_path, allow_pickle=False) as data:
            hit_count = np.asarray(data["hit_count"])
            measured = np.asarray(data["measured_total_keV"])
            source_bin80 = np.asarray(data["source_bin80"])
            w2_flags = np.asarray(data["w2_flags"])
            any_tes_mask = hit_count > 0
            raw_tes_sum_keV = np.zeros(len(hit_count), dtype=np.float64)
            nonzero_hit_rows = np.flatnonzero(any_tes_mask)
            hit_start = np.asarray(data["hit_start"])
            hit_energy_keV = np.asarray(data["hit_energy_keV"])
            for event_row in nonzero_hit_rows:
                start = int(hit_start[event_row])
                count = int(hit_count[event_row])
                raw_tes_sum_keV[event_row] = float(hit_energy_keV[start:start + count].sum(dtype=np.float64))
            raw_full_energy_mask = np.abs(raw_tes_sum_keV - 510.99895) < 0.01
            w2_pre_mask = (w2_flags & 1) != 0
            w2_final_mask = (w2_flags & 16) != 0
            any_tes = int(np.count_nonzero(any_tes_mask))
            positive_measured = int(np.count_nonzero(measured > 0))
            pixel_hits = int(hit_count.sum())
            w2_final = int(np.count_nonzero(w2_final_mask))
            catalog_rows = len(data["event_id"])
            hemisphere_counts = {}
            for stage_name, mask in (
                ("any_tes", any_tes_mask),
                ("raw_full", raw_full_energy_mask),
                ("w2_pre", w2_pre_mask),
                ("w2_final", w2_final_mask),
            ):
                hemisphere_counts[stage_name] = {
                    "down": int(np.count_nonzero(mask & (source_bin80 < 40))),
                    "up": int(np.count_nonzero(mask & (source_bin80 >= 40))),
                }
        require(any_tes == positive_measured, f"{key}: hit_count/measured-positive disagreement")
        require(w2_final == int(summary["w2_final_selected_events"]), f"{key}: final count mismatch")
        w2_pre_rows = [row for row in cutflow if row["window_id"] == "w2_510p58_511p42" and row["stage"] == "pre_veto"]
        require(len(w2_pre_rows) == 1, f"{key}: W2 pre-veto row not unique")
        broad_pre_rows = [row for row in cutflow if row["window_id"] == "broad_480_550" and row["stage"] == "pre_veto"]
        require(len(broad_pre_rows) == 1, f"{key}: broad pre-veto row not unique")
        exposure = float(summary["physical_exposure_s"])
        records[key] = {
            "geometry": label,
            "incident_photons": int(summary["incident_photons"]),
            "physical_exposure_s": exposure,
            "catalog_rows_detector_positive_any_subsystem": catalog_rows,
            "any_tes_events": any_tes,
            "any_tes_rate_cps": any_tes / exposure,
            "any_tes_sigma_cps": math.sqrt(any_tes) / exposure,
            "pixel_hit_records": pixel_hits,
            "raw_full_events": int(np.count_nonzero(raw_full_energy_mask)),
            "raw_full_rate_cps": int(np.count_nonzero(raw_full_energy_mask)) / exposure,
            "raw_full_sigma_cps": math.sqrt(int(np.count_nonzero(raw_full_energy_mask))) / exposure,
            "w2_pre_events": int(w2_pre_rows[0]["selected_events"]),
            "w2_pre_rate_cps": float(w2_pre_rows[0]["weighted_rate_cps"]),
            "w2_pre_sigma_cps": float(w2_pre_rows[0]["weighted_mc_sigma_cps"]),
            "broad_pre_events": int(broad_pre_rows[0]["selected_events"]),
            "broad_pre_rate_cps": float(broad_pre_rows[0]["weighted_rate_cps"]),
            "broad_pre_sigma_cps": float(broad_pre_rows[0]["weighted_mc_sigma_cps"]),
            "w2_final_events": w2_final,
            "w2_final_rate_cps": float(summary["w2_final_rate_cps"]),
            "w2_final_sigma_cps": float(summary["w2_final_mc_sigma_cps"]),
            "hemisphere_counts": hemisphere_counts,
        }

    sg3 = records["sg3"]
    wgrid = records["wgrid"]
    common_time = float(wgrid["physical_exposure_s"])
    require(math.isclose(common_time, 8339.8231, rel_tol=0, abs_tol=1e-7), "unexpected W-grid exposure")

    stage_contracts = [
        ("TES 任意可记录沉积", "any_tes", "至少一个原始正能 TES 像素沉积；不是边界穿越"),
        ("原始 TES 全能峰", "raw_full", "响应前 TES 总沉积满足 |E−510.99895|<0.01 keV"),
        ("511 窄窗、主动 veto 前", "w2_pre", "510.58–511.42 keV，尚未施加最终轨迹选择"),
        ("511 窄窗末级泄漏", "w2_final", "共同响应、能窗、主动 veto 与轨迹选择后的线本底"),
    ]
    equal_rows: list[dict[str, Any]] = []
    for stage, prefix, definition in stage_contracts:
        for record in (sg3, wgrid):
            rate = float(record[f"{prefix}_rate_cps"])
            sigma_rate = float(record[f"{prefix}_sigma_cps"])
            equal_rows.append({
                "stage": stage,
                "geometry": record["geometry"],
                "definition": definition,
                "raw_selected_events": int(record[f"{prefix}_events"]),
                "raw_physical_exposure_s": float(record["physical_exposure_s"]),
                "rate_cps": rate,
                "rate_mc_sigma_cps": sigma_rate,
                "equal_exposure_s": common_time,
                "equal_exposure_expected_events": rate * common_time,
                "equal_exposure_current_mc_sigma_events": sigma_rate * common_time,
            })

    any_ratio, any_ratio_sigma = ratio_and_sigma(
        float(wgrid["any_tes_rate_cps"]), float(wgrid["any_tes_sigma_cps"]),
        float(sg3["any_tes_rate_cps"]), float(sg3["any_tes_sigma_cps"]),
    )
    final_ratio, final_ratio_sigma = ratio_and_sigma(
        float(wgrid["w2_final_rate_cps"]), float(wgrid["w2_final_sigma_cps"]),
        float(sg3["w2_final_rate_cps"]), float(sg3["w2_final_sigma_cps"]),
    )
    any_diff_z = (
        float(wgrid["any_tes_rate_cps"]) - float(sg3["any_tes_rate_cps"])
    ) / math.hypot(float(wgrid["any_tes_sigma_cps"]), float(sg3["any_tes_sigma_cps"]))
    final_diff_z = (
        float(wgrid["w2_final_rate_cps"]) - float(sg3["w2_final_rate_cps"])
    ) / math.hypot(float(wgrid["w2_final_sigma_cps"]), float(sg3["w2_final_sigma_cps"]))
    final_ratio_exact95 = exact_poisson_rate_ratio_interval(
        int(wgrid["w2_final_events"]), float(wgrid["physical_exposure_s"]),
        int(sg3["w2_final_events"]), float(sg3["physical_exposure_s"]),
    )
    equal_rate_null_p = float(binomtest(
        int(wgrid["w2_final_events"]),
        int(wgrid["w2_final_events"]) + int(sg3["w2_final_events"]),
        float(wgrid["physical_exposure_s"]) /
        (float(wgrid["physical_exposure_s"]) + float(sg3["physical_exposure_s"])),
    ).pvalue)

    hemisphere_rows: list[dict[str, Any]] = []
    for stage_label, stage_key in (
        ("TES 任意可记录沉积", "any_tes"),
        ("511 窄窗末级泄漏", "w2_final"),
    ):
        for record in (sg3, wgrid):
            for hemisphere in ("down", "up"):
                raw_count = int(record["hemisphere_counts"][stage_key][hemisphere])
                rate = raw_count / float(record["physical_exposure_s"])
                hemisphere_rows.append({
                    "sample": f"{record['geometry']} · {stage_label}",
                    "stage": stage_label,
                    "geometry": record["geometry"],
                    "hemisphere": hemisphere,
                    "raw_events": raw_count,
                    "raw_exposure_s": float(record["physical_exposure_s"]),
                    "equal_exposure_expected_events": rate * common_time,
                    "equal_exposure_current_mc_sigma_events": (
                        math.sqrt(raw_count) / float(record["physical_exposure_s"]) * common_time
                        if raw_count > 0 else 0.0
                    ),
                })
    require(
        math.isclose(
            sum(row["equal_exposure_expected_events"] for row in hemisphere_rows
                if row["geometry"] == "SH3 + W-grid" and row["stage"] == "511 窄窗末级泄漏"),
            float(wgrid["w2_final_events"]), rel_tol=0, abs_tol=1e-12,
        ),
        "W-grid hemisphere final-count closure failed",
    )

    efficiency_rows: list[dict[str, Any]] = []
    for record in (sg3, wgrid):
        fraction = int(record["w2_final_events"]) / int(record["any_tes_events"])
        sigma = math.sqrt(fraction * (1.0 - fraction) / int(record["any_tes_events"]))
        efficiency_rows.append({
            "geometry": record["geometry"],
            "any_tes_events": int(record["any_tes_events"]),
            "w2_final_events": int(record["w2_final_events"]),
            "final_given_any_tes_fraction": fraction,
            "binomial_sigma": sigma,
        })
    retention_ratio = efficiency_rows[1]["final_given_any_tes_fraction"] / efficiency_rows[0]["final_given_any_tes_fraction"]

    stage_factor_rows: list[dict[str, Any]] = []
    stage_factor_contract = (
        ("单位时间任意 TES 沉积", "any_tes_rate_cps", None),
        ("原始全能峰 / 任意 TES 沉积", "raw_full_events", "any_tes_events"),
        ("响应后窄窗 / 原始全能峰", "w2_pre_events", "raw_full_events"),
        ("末级 / 窄窗前级", "w2_final_events", "w2_pre_events"),
    )
    factor_product = 1.0
    for factor_index, (stage_name, numerator_key, denominator_key) in enumerate(stage_factor_contract, start=1):
        if denominator_key is None:
            sg3_value = float(sg3[numerator_key])
            wgrid_value = float(wgrid[numerator_key])
        else:
            sg3_value = float(sg3[numerator_key]) / float(sg3[denominator_key])
            wgrid_value = float(wgrid[numerator_key]) / float(wgrid[denominator_key])
        factor = wgrid_value / sg3_value
        factor_product *= factor
        stage_factor_rows.append({
            "sequence": factor_index,
            "factor_stage": stage_name,
            "sg3_value": sg3_value,
            "wgrid_value": wgrid_value,
            "wgrid_over_sg3_factor": factor,
            "cumulative_product": factor_product,
        })
    require(math.isclose(factor_product, final_ratio, rel_tol=0, abs_tol=2e-12),
            "stage-factor multiplicative closure failed")

    sg3_mission = publication["models"]["a"]["mission_20day"]["components"]["atm511"]
    wgrid_mission_line = wgrid_mission["mission_20day"]
    mission_rows = [
        {
            "geometry": "SG3",
            "mission_days": 20,
            "mission_final_line_counts": float(sg3_mission["integrated_background_counts"]),
            "transport_mc_sigma_counts": float(sg3_mission["transport_sigma_counts"]),
            "transport_ess": float(sg3_mission["transport_ESS"]),
            "scope": "完整 81 节点任务折叠",
        },
        {
            "geometry": "SH3 + W-grid",
            "mission_days": 20,
            "mission_final_line_counts": float(wgrid_mission_line["approx_wgrid_atm511_counts"]),
            "transport_mc_sigma_counts": float(wgrid_mission["uncertainty"]["new_atm511_transport_sigma_counts"]),
            "transport_ess": (
                float(wgrid_mission_line["approx_wgrid_atm511_counts"])
                / float(wgrid_mission["uncertainty"]["new_atm511_transport_sigma_counts"])
            ) ** 2,
            "scope": "实际 W-grid 单线响应 × 同一 81 节点任务；非线/信号冻结不影响本行线计数",
        },
    ]
    mission_ratio, mission_ratio_sigma = ratio_and_sigma(
        mission_rows[1]["mission_final_line_counts"], mission_rows[1]["transport_mc_sigma_counts"],
        mission_rows[0]["mission_final_line_counts"], mission_rows[0]["transport_mc_sigma_counts"],
    )

    sg3_mission_full = publication["models"]["a"]["mission_20day"]
    sg3_total_background = float(sg3_mission_full["cumulative_background_counts_B"])
    sg3_line_background = float(sg3_mission["integrated_background_counts"])
    sg3_nonline_background = sg3_total_background - sg3_line_background
    sg3_signal_kernel = float(sg3_mission_full["cumulative_signal_counts_per_unit_flux_K"])
    wgrid_total_background = float(wgrid_mission_line["approx_wgrid_total_background_counts"])
    wgrid_line_background = float(wgrid_mission_line["approx_wgrid_atm511_counts"])
    wgrid_nonline_background = (
        float(wgrid_mission_line["frozen_gamma_continuum_counts"])
        + float(wgrid_mission_line["frozen_other_counts"])
    )
    wgrid_signal_kernel = float(wgrid_mission_line["signal_counts_per_unit_flux_frozen_sh3"])
    require(math.isclose(wgrid_line_background + wgrid_nonline_background, wgrid_total_background, rel_tol=0, abs_tol=1e-8),
            "W-grid line/non-line background closure failed")
    fmin_rows = []
    for geometry, line_background, nonline_background, total_background, signal_kernel, gaussian, asimov, scope in (
        (
            "SG3", sg3_line_background, sg3_nonline_background, sg3_total_background, sg3_signal_kernel,
            float(sg3_mission_full["Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["value_ph_cm2_s"]),
            float(sg3_mission_full["Fmin"]["Fmin_3sigma_poisson_asimov_ph_cm2_s"]["value_ph_cm2_s"]),
            "完整 SG3 81 节点闭合",
        ),
        (
            "SH3 + W-grid", wgrid_line_background, wgrid_nonline_background, wgrid_total_background, wgrid_signal_kernel,
            float(wgrid_mission_line["approx_wgrid_Fmin"]["Fmin_3sigma_gaussian_ph_cm2_s"]["value"]),
            float(wgrid_mission_line["approx_wgrid_Fmin"]["Fmin_3sigma_poisson_asimov_ph_cm2_s"]["value"]),
            "条件近似：冻结 SH3 非线、信号与时间修正，只替换 W-grid 单线",
        ),
    ):
        no_line_fmin = 3.0 * math.sqrt(nonline_background) / signal_kernel
        fmin_rows.append({
            "geometry": geometry,
            "mission_days": 20,
            "observation_contract": "0–20 d 连续有效观测；81 节点；无额外显式 duty 参数",
            "line_background_counts": line_background,
            "nonline_background_counts": nonline_background,
            "total_background_counts": total_background,
            "line_fraction_of_total": line_background / total_background,
            "signal_kernel_counts_per_unit_flux": signal_kernel,
            "gaussian_3sigma_fmin": gaussian,
            "asimov_3sigma_fmin": asimov,
            "gaussian_3sigma_fmin_without_mono_line": no_line_fmin,
            "fmin_increase_from_mono_line_fraction": gaussian / no_line_fmin - 1.0,
            "scope": scope,
        })

    open_sh3_line = publication["models"]["b"]["line_response"]
    line_rate_rows = []
    for geometry, raw_count, exposure, rate, sigma, scope in (
        ("SG3", int(sg3["w2_final_events"]), float(sg3["physical_exposure_s"]),
         float(sg3["w2_final_rate_cps"]), float(sg3["w2_final_sigma_cps"]), "参考几何，3M 单能输运"),
        ("开放 SH3", int(open_sh3_line["final_selected_events"]), float(open_sh3_line["physical_exposure_s"]),
         float(open_sh3_line["node60_target_and_transport_proposal_final_rate_cps"]),
         float(open_sh3_line["node60_target_and_transport_proposal_final_transport_sigma_cps"]),
         "与 W-grid 匹配的 15,709,417 初级光子"),
        ("SH3 + W-grid", int(wgrid["w2_final_events"]), float(wgrid["physical_exposure_s"]),
         float(wgrid["w2_final_rate_cps"]), float(wgrid["w2_final_sigma_cps"]),
         "与开放 SH3 匹配的 15,709,417 初级光子"),
    ):
        line_rate_rows.append({
            "geometry": geometry,
            "raw_final_events": raw_count,
            "transport_exposure_s": exposure,
            "final_line_rate_cps": rate,
            "rate_mc_sigma_cps": sigma,
            "rate_over_sg3": rate / float(sg3["w2_final_rate_cps"]),
            "scope": scope,
        })
    open_to_grid_ratio = line_rate_rows[2]["final_line_rate_cps"] / line_rate_rows[1]["final_line_rate_cps"]
    require(math.isclose(open_to_grid_ratio, float(comparison["key_comparisons"]["w2_final"]["new_over_old_ratio"]), rel_tol=0, abs_tol=1e-15),
            "open-SH3/W-grid comparison closure failed")

    aperture_rows = [
        {
            "geometry": "SG3",
            "front_envelope_width_cm": 3.796,
            "front_envelope_area_cm2": 3.796 ** 2,
            "net_normal_open_area_cm2": 12.158848,
            "normal_open_fraction": 0.843801,
            "grid_to_first_tes_layer_cm": 22.9,
            "scope": "逐条投影冻结几何中的W条带；只描述前平面法向净开孔",
        },
        {
            "geometry": "SH3 + W-grid",
            "front_envelope_width_cm": 5.4,
            "front_envelope_area_cm2": 5.4 ** 2,
            "net_normal_open_area_cm2": 24.619776,
            "normal_open_fraction": 0.844300,
            "grid_to_first_tes_layer_cm": 6.15,
            "scope": "逐条投影冻结几何中的W条带；只描述前平面法向净开孔",
        },
    ]
    aperture_ratio = aperture_rows[1]["net_normal_open_area_cm2"] / aperture_rows[0]["net_normal_open_area_cm2"]

    source_audit_rows = []
    for record in (sg3, wgrid):
        source_audit_rows.append({
            "geometry": record["geometry"],
            "incident_photons": record["incident_photons"],
            "physical_exposure_s": record["physical_exposure_s"],
            "source_primary_rate_s1": record["incident_photons"] / record["physical_exposure_s"],
            "catalog_rows_detector_positive_any_subsystem": record["catalog_rows_detector_positive_any_subsystem"],
            "any_tes_events": record["any_tes_events"],
            "pixel_hit_records": record["pixel_hit_records"],
            "w2_final_events": record["w2_final_events"],
        })
    source_rate_delta = source_audit_rows[1]["source_primary_rate_s1"] / source_audit_rows[0]["source_primary_rate_s1"] - 1.0
    require(abs(source_rate_delta) < 0.001, "source primary rates differ by >=0.1%")

    summary = {
        "status": "PASS__SG3_WGRID_EQUAL_EXPOSURE_LEAKAGE_CLOSED",
        "line_source": {
            "provider": "PARMA dedicated atmospheric line parameterization",
            "energy_keV": 510.99895,
            "day15_full_space_flux_ph_cm2_s": 0.16651547160226118,
            "equal_mu_components": 80,
        },
        "common_physical_exposure_s": common_time,
        "equal_exposure": {
            "any_recorded_tes_deposition": {
                "sg3_expected_events": float(sg3["any_tes_rate_cps"]) * common_time,
                "sg3_current_mc_sigma_events": float(sg3["any_tes_sigma_cps"]) * common_time,
                "wgrid_events": int(wgrid["any_tes_events"]),
                "wgrid_current_mc_sigma_events": math.sqrt(int(wgrid["any_tes_events"])),
                "wgrid_over_sg3_ratio": any_ratio,
                "ratio_sigma": any_ratio_sigma,
                "difference_z": any_diff_z,
            },
            "final_w2_line_leakage": {
                "sg3_expected_events": float(sg3["w2_final_rate_cps"]) * common_time,
                "sg3_current_mc_sigma_events": float(sg3["w2_final_sigma_cps"]) * common_time,
                "wgrid_events": int(wgrid["w2_final_events"]),
                "wgrid_current_mc_sigma_events": math.sqrt(int(wgrid["w2_final_events"])),
                "wgrid_over_sg3_ratio": final_ratio,
                "ratio_sigma": final_ratio_sigma,
                "difference_z": final_diff_z,
                "exact_conditional_poisson_rate_ratio_95": list(final_ratio_exact95),
                "equal_rate_null_two_sided_p": equal_rate_null_p,
            },
            "final_window_retention_given_any_tes": {
                "sg3_fraction": efficiency_rows[0]["final_given_any_tes_fraction"],
                "wgrid_fraction": efficiency_rows[1]["final_given_any_tes_fraction"],
                "wgrid_over_sg3_ratio": retention_ratio,
                "multiplicative_closure": any_ratio * retention_ratio,
            },
        },
        "mission_20day_final_line": {
            "sg3_counts": mission_rows[0]["mission_final_line_counts"],
            "sg3_mc_sigma_counts": mission_rows[0]["transport_mc_sigma_counts"],
            "wgrid_counts": mission_rows[1]["mission_final_line_counts"],
            "wgrid_mc_sigma_counts": mission_rows[1]["transport_mc_sigma_counts"],
            "wgrid_over_sg3_ratio": mission_ratio,
            "ratio_sigma": mission_ratio_sigma,
        },
        "hemisphere_equal_exposure": {
            "sg3_any_tes_down": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SG3" and row["stage"] == "TES 任意可记录沉积" and row["hemisphere"] == "down"),
            "sg3_any_tes_up": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SG3" and row["stage"] == "TES 任意可记录沉积" and row["hemisphere"] == "up"),
            "wgrid_any_tes_down": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SH3 + W-grid" and row["stage"] == "TES 任意可记录沉积" and row["hemisphere"] == "down"),
            "wgrid_any_tes_up": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SH3 + W-grid" and row["stage"] == "TES 任意可记录沉积" and row["hemisphere"] == "up"),
            "sg3_final_down": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SG3" and row["stage"] == "511 窄窗末级泄漏" and row["hemisphere"] == "down"),
            "sg3_final_up": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SG3" and row["stage"] == "511 窄窗末级泄漏" and row["hemisphere"] == "up"),
            "wgrid_final_down": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SH3 + W-grid" and row["stage"] == "511 窄窗末级泄漏" and row["hemisphere"] == "down"),
            "wgrid_final_up": next(row["equal_exposure_expected_events"] for row in hemisphere_rows if row["geometry"] == "SH3 + W-grid" and row["stage"] == "511 窄窗末级泄漏" and row["hemisphere"] == "up"),
        },
        "fmin_common_time_audit": {
            "explicit_observation_duty_cycle_parameter_present": False,
            "contract": "0–20 d continuous effective observation, 81 nodes at 0.25 d spacing, trapezoidal integration",
            "rows": fmin_rows,
        },
        "matched_open_sh3_wgrid_check": {
            "incident_photons_each": int(comparison["matched_statistics"]["incident_photons_each"]),
            "wgrid_over_open_sh3_final_rate_ratio": open_to_grid_ratio,
            "wgrid_over_open_sh3_ratio_sigma": float(comparison["key_comparisons"]["w2_final"]["independent_ratio_sigma"]),
            "wgrid_suppression_fraction": float(comparison["key_comparisons"]["w2_final"]["suppression_fraction"]),
        },
        "front_aperture_audit": {
            "sg3_net_normal_open_area_cm2": aperture_rows[0]["net_normal_open_area_cm2"],
            "wgrid_net_normal_open_area_cm2": aperture_rows[1]["net_normal_open_area_cm2"],
            "wgrid_over_sg3_net_open_area_ratio": aperture_ratio,
            "scope": "front-plane normal projection only; not a 4pi effective acceptance",
        },
        "definition_boundary": "Any TES entry means at least one recorded positive-energy TES pixel deposit. Zero-interaction boundary crossings are unobservable in the frozen catalogs/SIM contract.",
        "source_primary_rate_fractional_difference": source_rate_delta,
        "sources": {
            "sg3_summary": f"{SG3_BASE_REL}/summary.json",
            "sg3_catalog": f"{SG3_BASE_REL}/mono_line_event_catalog.npz",
            "wgrid_summary": f"{WGRID_BASE_REL}/response/summary.json",
            "wgrid_catalog": f"{WGRID_BASE_REL}/response/mono_line_event_catalog.npz",
            "publication": PUB_REL,
            "wgrid_mission": WGRID_MISSION_REL,
        },
    }
    with (output / "equal_exposure_leakage_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    write_csv(output / "equal_exposure_leakage.csv", equal_rows)
    write_csv(output / "final_window_retention.csv", efficiency_rows)
    write_csv(output / "mission_20day_line_leakage.csv", mission_rows)
    write_csv(output / "source_exposure_audit.csv", source_audit_rows)
    write_csv(output / "hemisphere_equal_exposure.csv", hemisphere_rows)
    write_csv(output / "line_rate_three_geometry_audit.csv", line_rate_rows)
    write_csv(output / "fmin_common_time_audit.csv", fmin_rows)
    write_csv(output / "stage_factor_decomposition.csv", stage_factor_rows)
    write_csv(output / "front_aperture_audit.csv", aperture_rows)

    headline = [{
        "any_tes_sg3": f"{float(sg3['any_tes_rate_cps'])*common_time:.1f} ± {float(sg3['any_tes_sigma_cps'])*common_time:.1f}",
        "any_tes_wgrid": f"{int(wgrid['any_tes_events'])} ± {math.sqrt(int(wgrid['any_tes_events'])):.1f}",
        "any_ratio": f"{any_ratio:.3f} ± {any_ratio_sigma:.3f}",
        "final_sg3": f"{float(sg3['w2_final_rate_cps'])*common_time:.1f} ± {float(sg3['w2_final_sigma_cps'])*common_time:.1f}",
        "final_wgrid": f"{int(wgrid['w2_final_events'])} ± {math.sqrt(int(wgrid['w2_final_events'])):.1f}",
        "final_ratio": f"{final_ratio:.3f} ± {final_ratio_sigma:.3f}",
        "final_ratio_exact95": f"{final_ratio_exact95[0]:.3f}–{final_ratio_exact95[1]:.3f}",
        "equal_rate_p": f"{equal_rate_null_p:.4g}",
    }]
    datasets = build_sqlite(output / "equal_exposure_leakage.sqlite", {
        "headline": headline,
        "equal_exposure": equal_rows,
        "retention": efficiency_rows,
        "mission_20day": mission_rows,
        "source_audit": source_audit_rows,
        "hemisphere": hemisphere_rows,
        "line_rate_audit": line_rate_rows,
        "fmin_audit": fmin_rows,
        "stage_factors": stage_factor_rows,
        "front_aperture": aperture_rows,
    })
    descriptions = {
        "headline": "相同 8339.8231 s 物理曝光下的主要绝对泄漏结果。",
        "equal_exposure": "由各自冻结输运率换算到 W-grid 8339.8231 s 的 TES 沉积和科学线窗事件数。",
        "retention": "最终线窗事件占所有可记录 TES 沉积事件的条件比例。",
        "mission_20day": "共同 81 节点、连续 20 日有效观测和任务时间折叠后的大气 511 线计数。",
        "source_audit": "SG3 与 W-grid 原始模拟入射数、曝光、目录与 TES 命中闭合。",
        "hemisphere": "同一8339.8231 s下按PARMA down/up半球分解的TES沉积与最终线泄漏。",
        "line_rate_audit": "SG3、开放SH3与SH3+W-grid的最终单线率、原始统计量和输运曝光。",
        "fmin_audit": "SG3与SH3+W-grid条件近似的共同20日观测时间、线/非线本底、信号核和Fmin。",
        "stage_factors": "最终2.40168倍线率比的四阶段乘法分解。",
        "front_aperture": "SG3与SH3+W-grid冻结几何的前平面法向包络、净开孔与TES距离。",
    }
    definitions = {
        "headline": ["Values are formatted from equal_exposure_leakage_summary.json."],
        "equal_exposure": ["N_equal = rate_cps * 8339.8231 s.", "The quoted sigma is the current finite-MC rate uncertainty multiplied by the common exposure."],
        "retention": ["retention = W2-final events / events with at least one positive-energy TES pixel hit."],
        "mission_20day": ["Counts use the 81-node mission fold, not a constant day-15 rate times 20 days."],
        "source_audit": ["detector-positive catalog rows may come from TES, plastic, or BGO; any_tes_events is hit_count>0 and is the relevant TES metric."],
        "hemisphere": ["source_bin80 0–39 is down and 40–79 is up.", "SG3 values are scaled from its own 1591.7573 s transport exposure."],
        "line_rate_audit": ["Each geometry is normalized by its own Cosima exposure before comparison.", "Open SH3 and W-grid each use 15,709,417 incident photons."],
        "fmin_audit": ["Both rows use 0–20 d, 81 nodes, 0.25 d spacing and trapezoidal integration.", "No separate sub-unity observation duty-cycle parameter is present."],
        "stage_factors": ["The product of the four W-grid/SG3 factors equals the final line-rate ratio."],
        "front_aperture": ["Net open area is the front-plane normal projection after summing the frozen W bars.", "It is not a full-sphere effective acceptance."],
    }
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    dataset_sources = []
    for name in datasets:
        dataset_sources.append({
            "id": f"source_{name}",
            "label": descriptions[name],
            "path": f"{OUT_REL}/equal_exposure_leakage.sqlite",
            "query": {
                "engine": "sqlite3", "language": "sql",
                "sql": f'SELECT * FROM "{name}" ORDER BY _row_order',
                "description": descriptions[name], "executed_at": generated_at,
                "tables_used": [name],
                "filters": ["PARMA 510.99895 keV only", "No row sampling"],
                "metric_definitions": definitions[name],
            },
        })
    main_source = {
        "id": "equal_exposure_bundle",
        "label": "SG3 与 SH3+W-grid 同曝光大气 511 keV 泄漏闭合",
        "path": f"{OUT_REL}/equal_exposure_leakage_summary.json",
    }
    entry_path_source = {
        "id": "entry_path_bundle",
        "label": "W-grid末级事件的逐事件入射路径与前网格包络求交",
        "path": "engineering/geometry_optimization_20260815/71_wgrid_mono511_entry_coupling_20260825/outputs/01_entry_path_diagnosis_20260825/entry_coupling_summary.json",
    }

    blocks = [
        {"id": "title", "type": "markdown", "body": "# SG3 与 SH3+W-grid：同时间口径、2.4倍泄漏与统计审计"},
        {"id": "summary", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 技术结论\n\n"
            "**Fmin 的任务时间口径相同，但2.40倍不是一个已经精确测定的几何常数。** SG3 与SH3+W-grid都按0–20 d、81节点、0.25 d间隔做梯形积分；代码没有额外的亚单位观测占空率参数，等价于连续20日有效观测。8339.8231 s和1591.7573 s只是两套蒙卡模板曝光，均先除以各自曝光变成cps。\n\n"
            "同8339.8231 s展示时，末级线泄漏为151±12.3对62.9±18.1，中心比值2.402±0.720；但SG3分母底层只有12个原始事件，精确95%区间为1.335–4.752。因此现有结果支持W-grid高于SG3，却不能区分1.5、2.0和2.4。前平面法向净开孔面积比本身为2.025，与2.402只差约0.52σ。"
        )},
        {"id": "metrics", "type": "metric-strip", "cardIds": ["card_any", "card_any_ratio", "card_final", "card_final_ratio"]},
        {"id": "absolute_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 151与62.9的确是同曝光显示，但62.9不是新模拟整数\n\n"
            "W-grid的151来自8339.8231 s实际输运；SG3的62.87是12×8339.8231/1591.7573的率外推。下图同时给出任意TES沉积、响应前原始全能峰、响应后窄窗和末级泄漏，避免把不同阶段混为同一‘入口’。"
        )},
        {"id": "equal_chart", "type": "chart", "chartId": "equal_exposure_counts"},
        {"id": "factor_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 2.402倍在响应和能窗之前已经基本形成\n\n"
            "最终倍率可精确分解为1.24390（任意TES沉积率）×1.80839（原始全能沉积概率）×1.03124（Gaussian响应后的窄窗接受）×1.03534（末级选择）=2.40168。共同响应、能窗和末级选择合计只再放大约6.8%；没有发现pixel-hit重复、宽/窄窗相加或80方向分箱重叠。"
        )},
        {"id": "factor_table", "type": "table", "tableId": "stage_factor_detail"},
        {"id": "line_audit_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 网络板正常工作；剩余差异继承自开放SH3\n\n"
            "开放SH3相对SG3的末级线率原本就是2.957倍；加入网络板后，W-grid/open-SH3=0.812±0.089，即降低18.8%。因此2.957×0.812=2.402。网络板没有制造异常，问题在于一块前置网络并不会把SH3整体的4π路径结构变成SG3。"
        )},
        {"id": "line_audit_table", "type": "table", "tableId": "line_rate_detail"},
        {"id": "aperture_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 前平面净开孔其实约为SG3的2.025倍，但两者仍不是等效准直器\n\n"
            "W-grid前包络为5.40×5.40 cm²，SG3为3.796×3.796 cm²；逐条扣除W网筋后净开孔为24.6198与12.1588 cm²，法向开孔率都约84.4%。更重要的是，W-grid距第一层TES约6.15 cm，SG3约22.9 cm；几何接受度不能只由开孔面积决定。"
        )},
        {"id": "aperture_table", "type": "table", "tableId": "aperture_detail"},
        {"id": "hemisphere_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 差异集中在down方向，不是全空间归一漂移\n\n"
            "任意TES沉积的up分量几乎完全相同：W-grid 369、SG3等效372；down则为198对83.8。末级中W-grid为down/up=60/91，SG3原始12个末级事件全部来自up。SG3的down末级中心值为0并不等于严格零接受度，因为该方向样本尤其稀薄。"
        )},
        {"id": "hemisphere_chart", "type": "chart", "chartId": "hemisphere_counts"},
        {"id": "path_heading", "type": "markdown", "sourceId": "entry_path_bundle", "body": (
            "## 约70.9%的W-grid末级事件没有完整穿过前网络包络\n\n"
            "逐事件路径重建显示：151个末级事件中42个完整穿过网络包络、2个掠过；42个从前侧包络外绕入，65个从后方或侧方绕入。即107/151完全绕开这块前网络。它填补了一个前开口，但不是4π包围准直。"
        )},
        {"id": "fmin_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## Fmin同为连续20日，但W-grid仍是条件近似\n\n"
            "SG3完整闭合得到B=99,923.14、K=16,350,529.19和3σ Gaussian Fmin=5.79993×10⁻⁵。W-grid条件包得到B=47,351.81、冻结SH3信号核K=16,781,213.42和3.89015×10⁻⁵；它只替换W-grid单线，冻结了SH3非线本底、五锚点时间修正和信号响应，并假设网络不增加511 keV邻近活化。"
        )},
        {"id": "fmin_table", "type": "table", "tableId": "fmin_detail"},
        {"id": "fmin_driver_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 为什么线项对SH3+W-grid的Fmin影响大、对SG3看起来小\n\n"
            "SG3的单线只占总本底12.56%，从去线的5.423×10⁻⁵升到5.800×10⁻⁵，仅恶化6.9%。W-grid条件包的单线占总本底67.53%，从冻结非线基线2.217×10⁻⁵升到3.890×10⁻⁵，恶化75.5%。这是同一20日下的分量占比效应，不是观测时间不同。"
        )},
        {"id": "mission_heading", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 20日任务折叠后的大气单线计数\n\n"
            "逐节点折叠得到SH3+W-grid 31,975.6±2,602.8、SG3 12,552.2±3,623.5。该表只比较单线分量；Fmin还取决于各自非线本底和信号核。"
        )},
        {"id": "mission_table", "type": "table", "tableId": "mission_detail"},
        {"id": "definitions", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 范围、数据与指标定义\n\n"
            "源严格采用PARMA专用大气线参数化：510.99895 keV、day-15全空间通量0.16651547160226118 ph cm⁻² s⁻¹、80个等μ分量。‘任意TES沉积’是至少一个正能TES像素命中；‘原始全能峰’是响应前|ΣE−510.99895|<0.01 keV；‘末级线泄漏’是共同响应后落入[510.58,511.42) keV并通过主动veto和轨迹选择。"
        )},
        {"id": "method", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 归一与统计检验\n\n"
            "每套模板按r=N/T归一，再按所需展示时间或0–20 d任务积分换算。两源初级率为1884.709与1883.663 s⁻¹，仅差0.0555%。最终率比的small-count条件Poisson精确95%区间为1.335–4.752；等率原假设双侧p=0.00178。后者排斥‘完全相同率’，但宽区间意味着无法把2.40与约2.0精确区分。"
        )},
        {"id": "limitations", "type": "markdown", "sourceId": "equal_exposure_bundle", "body": (
            "## 局限性与稳健性\n\n"
            "- 现有SIM没有被动体边界crossing日志；可计数的是TES正能沉积，不是零相互作用穿越。\n"
            "- SG3最终线样本只有12个，特别是down方向为0个末级事件；2.402不能当作高精度定值。\n"
            "- 原有NO_TOPUP门只保证总Fmin误差目标：SG3线只占总本底12.56%，不代表几何线率比已精确。\n"
            "- W-grid Fmin是用户指定的条件近似，而非W-grid宽带、信号和活化的完整自洽闭合。"
        )},
        {"id": "next", "type": "markdown", "body": (
            "## 建议的最小下一步\n\n"
            "当前最稳妥结论是：**SH3+W-grid泄漏与约2倍前开孔接受度相容；2.4是有限SG3统计下的中心值。** 若只需判断1.5与2.0，先把SG3补到约72个末级事件（约再补1500万初级光子）即可达到约2σ；若要10%倍率精度，SG3约需297个末级事件，代价约再补7125万初级光子。未获得新授权前不启动输运。"
        )},
        {"id": "questions", "type": "markdown", "body": (
            "## 尚需由精度目标决定的问题\n\n"
            "真正需要决定的不是是否存在一个已发现的归一错误，而是论文要报告‘约2倍、方向相关’还是精确报告2.40倍。前者现有证据足够；后者需要匹配的SG3增量统计，并且若要区分2.0与2.4，所需统计显著高于简单匹配15.7M初级光子。"
        )},
    ]

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1, "surface": "report",
            "title": "SG3 与 SH3+W-grid：同时间口径、泄漏倍率与统计审计",
            "description": "核对蒙卡曝光与 20 日 Fmin 时间口径，分解 511 keV 泄漏倍率，并检验其与开孔和有限统计的相容性。",
            "generatedAt": generated_at,
            "sources": [main_source, entry_path_source, *dataset_sources],
            "cards": [
                {"id": "card_any", "dataset": "headline", "sourceId": "source_headline", "description": "8339.8231 s，至少一个正能 TES 像素沉积。", "metrics": [{"label": "SG3 任意TES沉积", "field": "any_tes_sg3"}, {"label": "SH3+W-grid", "field": "any_tes_wgrid"}]},
                {"id": "card_any_ratio", "dataset": "headline", "sourceId": "source_headline", "description": "SH3+W-grid / SG3；独立 MC 一阶误差。", "metrics": [{"label": "绝对TES沉积率比", "field": "any_ratio"}]},
                {"id": "card_final", "dataset": "headline", "sourceId": "source_headline", "description": "8339.8231 s，最终511窄窗共同选择。", "metrics": [{"label": "SG3 末级泄漏", "field": "final_sg3"}, {"label": "SH3+W-grid", "field": "final_wgrid"}]},
                {"id": "card_final_ratio", "dataset": "headline", "sourceId": "source_headline", "description": "SH3+W-grid / SG3；独立 MC 一阶误差。", "metrics": [{"label": "末级线泄漏率比", "field": "final_ratio"}]},
            ],
            "charts": [
                {
                    "id": "equal_exposure_counts", "title": "相同 8339.8231 s 下的单能 TES 事件数", "subtitle": "SG3 为冻结率换算期望；SH3+W-grid 为该曝光的实际选后数", "showDescription": True,
                    "intent": "comparison", "question": "两个几何在同一时间内分别有多少绝对TES沉积与最终线泄漏？", "rationale": "分组柱同时保留物理阶段和几何两个维度。",
                    "comparisonContext": {"grain": "selection stage by geometry", "unit": "expected events", "denominator": "8339.8231 s common physical exposure"},
                    "type": "bar", "dataset": "equal_exposure", "sourceId": "source_equal_exposure",
                    "encodings": {
                        "x": {"field": "stage", "type": "nominal", "label": "物理/选择阶段"},
                        "y": {"field": "equal_exposure_expected_events", "type": "quantitative", "label": "同曝光事件数", "unit": "events"},
                        "color": {"field": "geometry", "type": "nominal", "label": "几何"},
                        "tooltip": [{"field": "geometry", "type": "text", "label": "几何"}, {"field": "equal_exposure_expected_events", "type": "quantitative", "label": "同曝光事件数"}, {"field": "equal_exposure_current_mc_sigma_events", "type": "quantitative", "label": "当前MC σ"}, {"field": "rate_cps", "type": "quantitative", "label": "率/cps"}, {"field": "raw_selected_events", "type": "quantitative", "label": "原始选后数"}],
                    },
                    "xAxisTitle": "阶段", "yAxisTitle": "8339.8231 s 内事件数", "palette": {"kind": "categorical"}, "unit": "events", "layout": "full", "maxRows": 20,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                },
                {
                    "id": "hemisphere_counts", "title": "相同曝光下的 down/up 半球分解", "subtitle": "SG3按1591.7573 s原始样本换算；W-grid为8339.8231 s实际事件", "showDescription": True,
                    "intent": "comparison", "question": "额外泄漏主要来自哪个PARMA半球？", "rationale": "按物理阶段分面比较down/up贡献，定位倍率的方向来源。",
                    "comparisonContext": {"grain": "geometry and selection stage by hemisphere", "unit": "expected events", "denominator": "8339.8231 s common physical exposure"},
                    "type": "bar", "dataset": "hemisphere", "sourceId": "source_hemisphere",
                    "encodings": {
                        "x": {"field": "sample", "type": "nominal", "label": "几何与阶段"},
                        "y": {"field": "equal_exposure_expected_events", "type": "quantitative", "label": "同曝光事件数", "unit": "events"},
                        "color": {"field": "hemisphere", "type": "nominal", "label": "PARMA半球"},
                        "tooltip": [{"field": "geometry", "type": "text", "label": "几何"}, {"field": "stage", "type": "text", "label": "阶段"}, {"field": "hemisphere", "type": "text", "label": "半球"}, {"field": "raw_events", "type": "quantitative", "label": "原始事件"}, {"field": "equal_exposure_expected_events", "type": "quantitative", "label": "同曝光事件数"}],
                    },
                    "xAxisTitle": "几何与阶段", "yAxisTitle": "8339.8231 s 内事件数", "palette": {"kind": "categorical"}, "unit": "events", "layout": "full", "maxRows": 20,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                },
            ],
            "tables": [
                {"id": "retention_detail", "title": "从任意 TES 沉积到最终窄窗的条件保留率", "subtitle": "分母为各自目录中的 hit_count>0 事件", "showDescription": True, "dataset": "retention", "defaultSort": {"field": "geometry", "direction": "asc"}, "density": "spacious", "sourceId": "source_retention", "layout": "full", "columns": [{"field": "geometry", "label": "几何", "type": "text"}, {"field": "any_tes_events", "label": "任意TES沉积", "format": "number"}, {"field": "w2_final_events", "label": "末级线窗", "format": "number"}, {"field": "final_given_any_tes_fraction", "label": "条件保留率", "format": "percent"}, {"field": "binomial_sigma", "label": "二项 σ", "format": "percent"}]},
                {"id": "stage_factor_detail", "title": "最终2.40168倍的阶段分解", "subtitle": "四个W-grid/SG3因子的乘积等于末级线率比", "showDescription": True, "dataset": "stage_factors", "defaultSort": {"field": "sequence", "direction": "asc"}, "density": "spacious", "sourceId": "source_stage_factors", "layout": "full", "columns": [{"field": "sequence", "label": "序", "format": "number"}, {"field": "factor_stage", "label": "阶段因子", "type": "text"}, {"field": "sg3_value", "label": "SG3", "format": "number"}, {"field": "wgrid_value", "label": "SH3+W-grid", "format": "number"}, {"field": "wgrid_over_sg3_factor", "label": "倍率", "format": "number"}, {"field": "cumulative_product", "label": "累计乘积", "format": "number"}]},
                {"id": "line_rate_detail", "title": "SG3、开放SH3与W-grid的单线率", "subtitle": "每套样本先除以各自Cosima曝光；开放SH3与W-grid初级数匹配", "showDescription": True, "dataset": "line_rate_audit", "defaultSort": {"field": "rate_over_sg3", "direction": "asc"}, "density": "spacious", "sourceId": "source_line_rate_audit", "layout": "full", "columns": [{"field": "geometry", "label": "几何", "type": "text"}, {"field": "raw_final_events", "label": "原始末级事件", "format": "number"}, {"field": "transport_exposure_s", "label": "蒙卡曝光/s", "format": "number"}, {"field": "final_line_rate_cps", "label": "末级线率/cps", "format": "number"}, {"field": "rate_mc_sigma_cps", "label": "MC σ/cps", "format": "number"}, {"field": "rate_over_sg3", "label": "相对SG3", "format": "number"}, {"field": "scope", "label": "范围", "type": "text"}]},
                {"id": "aperture_detail", "title": "前平面法向净开孔审计", "subtitle": "仅比较投影开孔；不等同于4π有效接受度", "showDescription": True, "dataset": "front_aperture", "defaultSort": {"field": "geometry", "direction": "asc"}, "density": "spacious", "sourceId": "source_front_aperture", "layout": "full", "columns": [{"field": "geometry", "label": "几何", "type": "text"}, {"field": "front_envelope_width_cm", "label": "前包络宽/cm", "format": "number"}, {"field": "front_envelope_area_cm2", "label": "包络面积/cm²", "format": "number"}, {"field": "net_normal_open_area_cm2", "label": "净开孔/cm²", "format": "number"}, {"field": "normal_open_fraction", "label": "开孔率", "format": "percent"}, {"field": "grid_to_first_tes_layer_cm", "label": "至首层TES/cm", "format": "number"}, {"field": "scope", "label": "范围", "type": "text"}]},
                {"id": "fmin_detail", "title": "共同20日口径的背景组成与Fmin", "subtitle": "0–20 d、81节点、0.25 d梯形积分；无额外显式亚单位duty参数", "showDescription": True, "dataset": "fmin_audit", "defaultSort": {"field": "geometry", "direction": "asc"}, "density": "spacious", "sourceId": "source_fmin_audit", "layout": "full", "columns": [{"field": "geometry", "label": "几何", "type": "text"}, {"field": "line_background_counts", "label": "单线B", "format": "number"}, {"field": "nonline_background_counts", "label": "非线B", "format": "number"}, {"field": "total_background_counts", "label": "总B", "format": "number"}, {"field": "line_fraction_of_total", "label": "线占比", "format": "percent"}, {"field": "signal_kernel_counts_per_unit_flux", "label": "信号核K", "format": "number"}, {"field": "gaussian_3sigma_fmin", "label": "Gaussian 3σ Fmin", "format": "number"}, {"field": "asimov_3sigma_fmin", "label": "Asimov 3σ Fmin", "format": "number"}, {"field": "scope", "label": "范围", "type": "text"}]},
                {"id": "mission_detail", "title": "20日任务折叠的大气511线本底", "subtitle": "81节点、共同PARMA目标、连续20日有效观测；无额外显式亚单位duty参数", "showDescription": True, "dataset": "mission_20day", "defaultSort": {"field": "mission_final_line_counts", "direction": "desc"}, "density": "spacious", "sourceId": "source_mission_20day", "layout": "full", "columns": [{"field": "geometry", "label": "几何", "type": "text"}, {"field": "mission_final_line_counts", "label": "20日线计数", "format": "number"}, {"field": "transport_mc_sigma_counts", "label": "MC σ", "format": "number"}, {"field": "transport_ess", "label": "输运 ESS", "format": "number"}, {"field": "scope", "label": "范围", "type": "text"}]},
            ],
            "blocks": blocks,
        },
        "snapshot": {"version": 1, "generatedAt": generated_at, "status": "ready", "datasets": datasets},
        "sources": [main_source, entry_path_source, *dataset_sources],
    }
    with (output / "artifact.json").open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    receipt = {
        "status": "PASS__EQUAL_EXPOSURE_REPORT_BUNDLE_BUILT",
        "generated_at": generated_at,
        "transport_root": str(root),
        "output_dir": str(output),
        "checks": {
            "sg3_any_tes": sg3["any_tes_events"], "wgrid_any_tes": wgrid["any_tes_events"],
            "sg3_w2_final": sg3["w2_final_events"], "wgrid_w2_final": wgrid["w2_final_events"],
            "source_primary_rate_fractional_difference": source_rate_delta,
            "final_ratio_multiplicative_closure_residual": final_ratio - any_ratio * retention_ratio,
        },
        "outputs": ["equal_exposure_leakage_summary.json", "equal_exposure_leakage.csv", "final_window_retention.csv", "mission_20day_line_leakage.csv", "source_exposure_audit.csv", "hemisphere_equal_exposure.csv", "line_rate_three_geometry_audit.csv", "fmin_common_time_audit.csv", "stage_factor_decomposition.csv", "front_aperture_audit.csv", "equal_exposure_leakage.sqlite", "artifact.json"],
    }
    with (output / "build_receipt.json").open("w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": receipt["status"], "any_tes_equal": summary["equal_exposure"]["any_recorded_tes_deposition"], "final_equal": summary["equal_exposure"]["final_w2_line_leakage"], "mission_20day": summary["mission_20day_final_line"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
