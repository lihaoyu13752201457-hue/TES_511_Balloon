#!/usr/bin/env python3
"""Approximate SH3+W-grid Fmin by replacing only the PARMA mono-511 template.

This deliberately freezes the SH3 non-line background, coincidence timeline,
signal effective area, atmospheric transmission, and signal-survival kernel.
It is therefore a conditional engineering estimate, not a full W-grid closure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import uuid

import numpy as np


SECONDS_PER_DAY = 86400.0
ANCHORS = np.asarray([0, 20, 40, 60, 80], dtype=float)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def asimov_required_signal(background: float, target_z: float) -> float:
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)

    def significance(signal: float) -> float:
        return math.sqrt(
            2.0 * ((signal + background) * math.log1p(signal / background) - signal)
        )

    while significance(high) < target_z:
        high *= 2.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if significance(middle) < target_z:
            low = middle
        else:
            high = middle
    return high


def fmin_values(background: float, kernel: float) -> dict[str, float]:
    return {
        "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(background) / kernel,
        "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(background) / kernel,
        "Fmin_3sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 3.0) / kernel,
        "Fmin_5sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 5.0) / kernel,
    }


def selected_by_bin(path: Path) -> np.ndarray:
    rows = read_csv(path)
    if len(rows) != 80 or [int(row["source_bin80"]) for row in rows] != list(range(80)):
        raise RuntimeError(f"source-bin table is not exactly bins 0..79: {path}")
    return np.asarray([int(row["selected_events"]) for row in rows], dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package67", type=Path, required=True)
    parser.add_argument("--package68-analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p67 = args.package67.resolve()
    p68 = args.package68_analysis.resolve()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.staging-{os.getpid()}-{uuid.uuid4().hex}"
    staging.mkdir(mode=0o755)

    source_dir = p67 / "outputs/00_source_closure"
    old_line_dir = p67 / "outputs/01_line_response_b60"
    old_timeline_dir = p67 / "outputs/03_fluxclosed_timeline_b"
    new_line_dir = p68 / "response"

    paths = {
        "mono511_target": source_dir / "mono511_target_81x80.csv",
        "old_line_bins": old_line_dir / "mono_line_final_by_source_bin80.csv",
        "old_line_summary": old_line_dir / "summary.json",
        "old_timeline": old_timeline_dir / "mission_timeline_81nodes.csv",
        "old_timeline_summary": old_timeline_dir / "summary.json",
        "new_line_bins": new_line_dir / "mono_line_final_by_source_bin80.csv",
        "new_line_summary": new_line_dir / "summary.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    old_line_summary = read_json(paths["old_line_summary"])
    new_line_summary = read_json(paths["new_line_summary"])
    old_timeline_summary = read_json(paths["old_timeline_summary"])
    old_n = selected_by_bin(paths["old_line_bins"])
    new_n = selected_by_bin(paths["new_line_bins"])
    old_weight = 1.0 / float(old_line_summary["physical_exposure_s"])
    new_weight = 1.0 / float(new_line_summary["physical_exposure_s"])

    if int(old_n.sum()) != int(old_line_summary["w2_final_selected_events"]):
        raise RuntimeError("old SH3 bin counts do not close to final selection")
    if int(new_n.sum()) != int(new_line_summary["w2_final_selected_events"]):
        raise RuntimeError("W-grid bin counts do not close to final selection")
    if int(old_line_summary["incident_photons"]) != int(new_line_summary["incident_photons"]):
        raise RuntimeError("old SH3 and W-grid incident statistics are not matched")
    if not math.isclose(float(old_n.sum()) * old_weight, float(old_line_summary["w2_final_rate_cps"]), rel_tol=2e-14):
        raise RuntimeError("old SH3 day-15 line rate does not close")
    if not math.isclose(float(new_n.sum()) * new_weight, float(new_line_summary["w2_final_rate_cps"]), rel_tol=2e-14):
        raise RuntimeError("W-grid day-15 line rate does not close")

    target_rows = read_csv(paths["mono511_target"])
    if len(target_rows) != 81 * 80:
        raise RuntimeError("mono511 target table is not 81x80")
    importance = np.zeros((81, 80), dtype=float)
    days = np.full(81, np.nan, dtype=float)
    seen = set()
    for row in target_rows:
        node = int(row["time_bin_id"])
        source_bin = int(row["source_bin80"])
        key = (node, source_bin)
        if key in seen:
            raise RuntimeError(f"duplicate mono511 target row: {key}")
        seen.add(key)
        importance[node, source_bin] = float(row["importance_ratio"])
        day = float(row["day_mid"])
        if math.isnan(days[node]):
            days[node] = day
        elif days[node] != day:
            raise RuntimeError(f"inconsistent day at node {node}")
    if seen != {(node, source_bin) for node in range(81) for source_bin in range(80)}:
        raise RuntimeError("mono511 target node/bin coverage is incomplete")

    timeline_rows = read_csv(paths["old_timeline"])
    if len(timeline_rows) != 81 or [int(row["time_bin_id"]) for row in timeline_rows] != list(range(81)):
        raise RuntimeError("old SH3 mission timeline is not exactly nodes 0..80")
    timeline_days = np.asarray([float(row["day_mid"]) for row in timeline_rows])
    if not np.array_equal(days, timeline_days):
        raise RuntimeError("source and mission day axes differ")
    timeline_ratio = np.asarray([float(row["interpolated_background_timeline_ratio"]) for row in timeline_rows])
    direct_other = np.asarray([float(row["direct_other_cps"]) for row in timeline_rows])
    direct_gamma = np.asarray([float(row["direct_gamma_continuum_cps"]) for row in timeline_rows])
    signal_kernel = np.asarray([float(row["conditional_signal_kernel_cm2"]) for row in timeline_rows])

    direct_old_line = importance @ (old_n * old_weight)
    direct_new_line = importance @ (new_n * new_weight)
    direct_new_total = direct_other + direct_gamma + direct_new_line
    mature_new_total = direct_new_total * timeline_ratio

    trapz = getattr(np, "trapezoid", None) or np.trapz
    bin_coefficients = np.asarray([
        float(trapz(importance[:, source_bin] * timeline_ratio, days)) * SECONDS_PER_DAY
        for source_bin in range(80)
    ])
    old_line_counts = float(np.sum(old_n * old_weight * bin_coefficients))
    new_line_counts = float(np.sum(new_n * new_weight * bin_coefficients))
    old_line_variance = float(np.sum(old_n * (old_weight * bin_coefficients) ** 2))
    new_line_variance = float(np.sum(new_n * (new_weight * bin_coefficients) ** 2))

    old_line_authority = old_timeline_summary["mission_transport_components"]["atm511"]
    if not math.isclose(old_line_counts, float(old_line_authority["integrated_background_counts"]), rel_tol=3e-12):
        raise RuntimeError("independent old-line mission count reproduction failed")
    if not math.isclose(old_line_variance, float(old_line_authority["sum_W_i2_counts2"]), rel_tol=3e-12):
        raise RuntimeError("independent old-line mission variance reproduction failed")

    old_components = old_timeline_summary["mission_transport_components"]
    frozen_other_counts = float(old_components["other"]["integrated_background_counts"])
    frozen_gamma_counts = float(old_components["gamma_continuum"]["integrated_background_counts"])
    frozen_other_variance = float(old_components["other"]["sum_W_i2_counts2"])
    frozen_gamma_variance = float(old_components["gamma_continuum"]["sum_W_i2_counts2"])
    new_background = frozen_other_counts + frozen_gamma_counts + new_line_counts
    new_transport_variance = frozen_other_variance + frozen_gamma_variance + new_line_variance
    new_transport_sigma = math.sqrt(new_transport_variance)

    anchor_errors = np.asarray([
        float(old_timeline_summary["anchors"][str(int(node))]["timeline_to_direct_ratio_standard_error"])
        for node in ANCHORS
    ])
    node_axis = np.arange(81, dtype=float)
    ratio_coefficients = []
    for index in range(len(ANCHORS)):
        basis = np.zeros(len(ANCHORS), dtype=float)
        basis[index] = 1.0
        interpolated = np.interp(node_axis, ANCHORS, basis)
        ratio_coefficients.append(float(trapz(direct_new_total * interpolated, days)) * SECONDS_PER_DAY)
    new_timeline_sigma = float(np.sqrt(np.sum((np.asarray(ratio_coefficients) * anchor_errors) ** 2)))
    new_background_sigma = math.hypot(new_transport_sigma, new_timeline_sigma)
    new_background_relative_sigma = new_background_sigma / new_background

    old_final = old_timeline_summary["mission_final_20day"]
    old_background = float(old_final["cumulative_background_counts"])
    signal_counts_per_unit_flux = float(old_final["cumulative_signal_counts_per_unit_flux"])
    independently_integrated_signal_kernel = float(trapz(signal_kernel, days)) * SECONDS_PER_DAY
    if not math.isclose(independently_integrated_signal_kernel, signal_counts_per_unit_flux, rel_tol=3e-12):
        raise RuntimeError("frozen SH3 signal kernel integration failed")
    old_fmins_recomputed = fmin_values(old_background, signal_counts_per_unit_flux)
    for key, value in old_fmins_recomputed.items():
        if not math.isclose(value, float(old_final[key]), rel_tol=3e-12):
            raise RuntimeError(f"old SH3 Fmin reproduction failed: {key}")

    new_fmins = fmin_values(new_background, signal_counts_per_unit_flux)
    signal_relative_sigma = float(old_timeline_summary["statistical_uncertainty"]["signal_combined_relative_sigma"])
    fmin_uncertainty = {}
    for z in (3.0, 5.0):
        gaussian_key = f"Fmin_{int(z)}sigma_gaussian_ph_cm2_s"
        gaussian_value = new_fmins[gaussian_key]
        gaussian_relative = math.hypot(0.5 * new_background_relative_sigma, signal_relative_sigma)
        fmin_uncertainty[gaussian_key] = {
            "value": gaussian_value,
            "standard_error": gaussian_value * gaussian_relative,
            "relative_standard_error": gaussian_relative,
        }
        asimov_key = f"Fmin_{int(z)}sigma_poisson_asimov_ph_cm2_s"
        asimov_value = new_fmins[asimov_key]
        required_signal = asimov_required_signal(new_background, z)
        logarithm = math.log1p(required_signal / new_background)
        derivative = (required_signal / new_background - logarithm) / logarithm
        asimov_sigma = math.hypot(
            derivative * new_background_sigma / signal_counts_per_unit_flux,
            asimov_value * signal_relative_sigma,
        )
        fmin_uncertainty[asimov_key] = {
            "value": asimov_value,
            "standard_error": asimov_sigma,
            "relative_standard_error": asimov_sigma / asimov_value,
        }

    old_day15 = old_timeline_summary["day15_W2_final_component_rates"]
    new_day15_total = (
        float(old_day15["other"]["rate_cps"])
        + float(old_day15["gamma_continuum"]["rate_cps"])
        + float(new_line_summary["w2_final_rate_cps"])
    )

    cumulative_background = 0.0
    cumulative_kernel = 0.0
    cumulative_new_line = 0.0
    output_timeline = []
    for node in range(81):
        if node > 0:
            dt = (days[node] - days[node - 1]) * SECONDS_PER_DAY
            cumulative_background += 0.5 * (mature_new_total[node - 1] + mature_new_total[node]) * dt
            cumulative_kernel += 0.5 * (signal_kernel[node - 1] + signal_kernel[node]) * dt
            new_line_rate_previous = direct_new_line[node - 1] * timeline_ratio[node - 1]
            new_line_rate_current = direct_new_line[node] * timeline_ratio[node]
            cumulative_new_line += 0.5 * (new_line_rate_previous + new_line_rate_current) * dt
        row = {
            "time_bin_id": node,
            "day_mid": float(days[node]),
            "direct_other_cps_frozen_sh3": float(direct_other[node]),
            "direct_gamma_continuum_cps_frozen_sh3": float(direct_gamma[node]),
            "direct_atm511_cps_wgrid": float(direct_new_line[node]),
            "direct_total_cps_approx": float(direct_new_total[node]),
            "interpolated_background_timeline_ratio_frozen_sh3": float(timeline_ratio[node]),
            "mature_background_cps_approx": float(mature_new_total[node]),
            "cumulative_atm511_counts_wgrid": cumulative_new_line,
            "cumulative_background_counts_approx": cumulative_background,
            "cumulative_signal_counts_per_unit_flux_frozen_sh3": cumulative_kernel,
        }
        if cumulative_kernel > 0.0:
            row.update(fmin_values(cumulative_background, cumulative_kernel))
        else:
            row.update({key: "" for key in new_fmins})
        output_timeline.append(row)

    if not math.isclose(cumulative_background, new_background, rel_tol=3e-12):
        raise RuntimeError("new total background component/trapezoid closure failed")
    if not math.isclose(cumulative_new_line, new_line_counts, rel_tol=3e-12):
        raise RuntimeError("new line component/trapezoid closure failed")
    if not math.isclose(cumulative_kernel, signal_counts_per_unit_flux, rel_tol=3e-12):
        raise RuntimeError("new timeline signal-kernel closure failed")

    summary = {
        "status": "PASS__APPROX_WGRID_FMIN_UNDER_FROZEN_SH3_NONLINE_ASSUMPTION",
        "schema_version": 1,
        "result_scope": "conditional approximation requested by user; not a full W-grid broadband/signal/activation closure",
        "assumptions": {
            "other_background": "frozen from SH3 model B 81-node authority",
            "gamma_continuum": "flux-conserving SH3 continuum frozen from SH3 model B 81-node authority",
            "atm511": "replaced by matched W-grid 510.99895-keV response and folded with the same 81x80 PARMA target",
            "wgrid_activation_near_511": "assumed absent by user; no added W-grid activation component",
            "timeline_coincidence_ratio": "frozen SH3 five-anchor interpolation",
            "signal_response": "frozen SH3 effective area, atmospheric transmission, and accidental-survival kernel",
        },
        "parma": {
            "line_energy_keV": 510.99895,
            "day15_full_space_flux_ph_cm2_s": 0.16651547160226118,
            "angular_components_equal_mu": 80,
        },
        "matched_line_statistics": {
            "incident_photons_each": int(old_line_summary["incident_photons"]),
            "open_sh3_selected_events": int(old_n.sum()),
            "wgrid_selected_events": int(new_n.sum()),
            "open_sh3_day15_line_rate_cps": float(old_line_summary["w2_final_rate_cps"]),
            "wgrid_day15_line_rate_cps": float(new_line_summary["w2_final_rate_cps"]),
        },
        "day15_reference": {
            "old_sh3_total_rate_cps": float(old_day15["total"]["rate_cps"]),
            "approx_wgrid_total_rate_cps": new_day15_total,
            "ratio": new_day15_total / float(old_day15["total"]["rate_cps"]),
        },
        "mission_20day": {
            "old_sh3_atm511_counts": old_line_counts,
            "approx_wgrid_atm511_counts": new_line_counts,
            "atm511_ratio": new_line_counts / old_line_counts,
            "frozen_other_counts": frozen_other_counts,
            "frozen_gamma_continuum_counts": frozen_gamma_counts,
            "old_sh3_total_background_counts": old_background,
            "approx_wgrid_total_background_counts": new_background,
            "total_background_ratio": new_background / old_background,
            "signal_counts_per_unit_flux_frozen_sh3": signal_counts_per_unit_flux,
            "old_sh3_Fmin": {key: float(old_final[key]) for key in new_fmins},
            "approx_wgrid_Fmin": fmin_uncertainty,
            "gaussian_3sigma_threshold_ratio_new_over_old": new_fmins["Fmin_3sigma_gaussian_ph_cm2_s"] / float(old_final["Fmin_3sigma_gaussian_ph_cm2_s"]),
            "gaussian_3sigma_threshold_reduction_fraction": 1.0 - new_fmins["Fmin_3sigma_gaussian_ph_cm2_s"] / float(old_final["Fmin_3sigma_gaussian_ph_cm2_s"]),
            "gaussian_3sigma_sensitivity_improvement_factor": float(old_final["Fmin_3sigma_gaussian_ph_cm2_s"]) / new_fmins["Fmin_3sigma_gaussian_ph_cm2_s"],
        },
        "uncertainty": {
            "new_atm511_transport_sigma_counts": math.sqrt(new_line_variance),
            "new_total_transport_sigma_counts": new_transport_sigma,
            "new_timeline_replay_sigma_counts": new_timeline_sigma,
            "new_background_combined_sigma_counts": new_background_sigma,
            "new_background_combined_relative_sigma": new_background_relative_sigma,
            "frozen_signal_combined_relative_sigma": signal_relative_sigma,
            "note": "MC/statistical uncertainty only; approximation/systematic error from freezing non-line and signal response is not quantified",
        },
        "validation": {
            "old_line_mission_counts_reproduced": True,
            "old_line_mission_variance_reproduced": True,
            "old_sh3_Fmin_reproduced": True,
            "new_line_81node_count_and_variance_folded_from_bin80": True,
            "component_sum_matches_trapezoid_total": True,
            "signal_kernel_reproduced": True,
        },
        "inputs": {name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()},
        "outputs": ["approx_fmin_summary.json", "mission_timeline_81nodes_approx.csv", "README.md"],
    }

    write_json(staging / "approx_fmin_summary.json", summary)
    write_csv(staging / "mission_timeline_81nodes_approx.csv", output_timeline)
    g3 = fmin_uncertainty["Fmin_3sigma_gaussian_ph_cm2_s"]
    a3 = fmin_uncertainty["Fmin_3sigma_poisson_asimov_ph_cm2_s"]
    readme = f"""# SH3 + W-grid conditional Fmin approximation\n\n+This is a **conditional approximation**, not a full W-grid background/signal closure.\n+It freezes the SH3 non-line background, five-anchor timeline correction, signal\n+effective area, atmospheric transmission, and accidental-survival response; only\n+the matched PARMA monoenergetic 510.99895-keV template is replaced by the W-grid\n+result. Per the requested assumption, no W-grid activation component near 511 keV\n+is added.\n\n+## 20-day result\n\n+- Gaussian 3 sigma: `{g3['value']:.12g} +/- {g3['standard_error']:.12g} ph cm^-2 s^-1`\n+- Poisson Asimov 3 sigma: `{a3['value']:.12g} +/- {a3['standard_error']:.12g} ph cm^-2 s^-1`\n+- Old SH3 Gaussian 3 sigma: `{float(old_final['Fmin_3sigma_gaussian_ph_cm2_s']):.12g} ph cm^-2 s^-1`\n+- Threshold reduction: `{100.0 * summary['mission_20day']['gaussian_3sigma_threshold_reduction_fraction']:.6g}%`\n+- Sensitivity improvement factor: `{summary['mission_20day']['gaussian_3sigma_sensitivity_improvement_factor']:.9g}`\n+- Approximate cumulative background: `{new_background:.12g}` counts\n\n+The quoted uncertainty is statistical only and does not quantify the approximation\n+error caused by freezing the W-grid broadband and signal responses.\n+"""
    (staging / "README.md").write_text(readme, encoding="utf-8")
    os.rename(staging, output)
    print(json.dumps({"status": summary["status"], "output": str(output), "gaussian_3sigma": g3, "asimov_3sigma": a3}, indent=2))


if __name__ == "__main__":
    main()
