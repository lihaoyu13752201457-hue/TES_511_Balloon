#!/usr/bin/env python3
"""Reweight the retained SG3B mature timeline with the expanded gamma catalog.

This is the recovery path used when the external activation-manifest mount is
offline.  The delayed 81-node curves and five common-time anchors are retained;
only the statistically improved prompt-gamma category is replaced.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
BASE_PACKAGE = ROOT / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818"
BASE_OUT = BASE_PACKAGE / "outputs/02_mature_timeline"
BASE_CATALOG = BASE_PACKAGE / "outputs/01_event_catalog"
EXPANDED = PACKAGE / "outputs/03_expanded_catalog"
OUT = PACKAGE / "outputs/04_candidate_timeline"
SCALES = ROOT / "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv"
SECONDS_PER_DAY = 86_400.0
TAU_S = 1.0e-6


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def asimov_flux(background: float, kernel: float, sigma: float) -> float:
    def significance(flux: float) -> float:
        signal = flux * kernel
        return math.sqrt(2.0 * ((signal + background) * math.log1p(signal / background) - signal))

    low = 0.0
    high = sigma * math.sqrt(background) / kernel * 2.0
    while significance(high) < sigma:
        high *= 2.0
    for _ in range(100):
        mid = 0.5 * (low + high)
        if significance(mid) < sigma:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def main(candidate_aeff: float | None = None) -> int:
    if candidate_aeff is None:
        signal = load_json(PACKAGE / "outputs/01_signal/summary.json")
        candidate_aeff = float(
            signal["effective_area"]["w2_510p58_511p42"]["compton_trajectory_veto"]["Aeff_cm2"]
        )
    expanded = load_json(EXPANDED / "summary.json")
    if not expanded.get("publication_precision_rule_met"):
        raise RuntimeError("expanded gamma catalog does not meet publication precision rule")

    categories = load_json(BASE_CATALOG / "category_registry.json")["categories"]
    gamma_rows = [row for row in categories if row["stream"] == "prompt" and row["family"] == "gamma"]
    if len(gamma_rows) != 1:
        raise RuntimeError(f"expected one retained prompt-gamma category, found {len(gamma_rows)}")
    gamma = gamma_rows[0]
    start = int(gamma["event_start"])
    stop = start + int(gamma["event_count"])
    with np.load(BASE_CATALOG / "combined_event_catalog.npz", allow_pickle=False) as data:
        old_gamma_raw = int(np.count_nonzero(data["w2_flags"][start:stop] & (1 << 4)))
    if old_gamma_raw <= 0:
        raise RuntimeError("retained prompt-gamma category has no W2 final survivor")

    old_gamma_weight = float(gamma["base_event_weight_cps"])
    old_gamma_final = old_gamma_raw * old_gamma_weight
    old_gamma_occupancy = float(gamma["base_detector_positive_rate_cps"])
    new_gamma_raw = int(expanded["combined_gamma_W2_final_raw_survivors"])
    new_gamma_weight = float(expanded["combined_gamma_event_weight_cps"])
    new_gamma_final = float(expanded["combined_gamma_W2_final_rate_cps"])
    new_gamma_occupancy = (
        int(expanded["combined_gamma_detector_positive_templates"]) * new_gamma_weight
    )

    mission_base = read_csv(BASE_OUT / "mission_mature_flux_threshold.csv")
    anchors_base = read_csv(BASE_OUT / "anchor_timeline_rates.csv")
    scales = read_csv(SCALES)
    if len(mission_base) != 81 or len(scales) != 81:
        raise RuntimeError("retained mission/scaling axis is not 81 nodes")
    scales_by_node = {int(row["time_bin_id"]): float(row["scale_gamma_to_parma_reference"]) for row in scales}

    mission: list[dict[str, Any]] = []
    cumulative_background = 0.0
    cumulative_kernel = 0.0
    previous_day = None
    previous_background = None
    previous_kernel = None
    old_per_survivor_rates = []
    new_per_survivor_rates = []
    for base in mission_base:
        node = int(base["time_bin_id"])
        day = float(base["day_mid"])
        gamma_scale = scales_by_node[node]
        direct_delta = (new_gamma_final - old_gamma_final) * gamma_scale
        occupancy_delta = (new_gamma_occupancy - old_gamma_occupancy) * gamma_scale
        coincidence_adjustment = math.exp(-2.0 * occupancy_delta * TAU_S)
        direct = float(base["direct_W2_final_no_coincidence_cps"]) + direct_delta
        ratio = float(base["interpolated_background_timeline_ratio"]) * coincidence_adjustment
        background_rate = direct * ratio
        survival = float(base["conditional_signal_accidental_survival"]) * coincidence_adjustment
        transmission = float(base["T_atm_511_slant45"])
        kernel_rate = candidate_aeff * transmission * survival
        old_per_survivor_rates.append(old_gamma_weight * gamma_scale * float(base["interpolated_background_timeline_ratio"]))
        new_per_survivor_rates.append(new_gamma_weight * gamma_scale * ratio)
        if previous_day is not None:
            dt_s = (day - previous_day) * SECONDS_PER_DAY
            cumulative_background += 0.5 * (previous_background + background_rate) * dt_s
            cumulative_kernel += 0.5 * (previous_kernel + kernel_rate) * dt_s
        gaussian3 = 3.0 * math.sqrt(cumulative_background) / cumulative_kernel if cumulative_kernel else math.nan
        gaussian5 = 5.0 * math.sqrt(cumulative_background) / cumulative_kernel if cumulative_kernel else math.nan
        row = {
            "time_bin_id": node,
            "day_mid": day,
            "direct_W2_final_no_coincidence_cps": direct,
            "interpolated_background_timeline_ratio": ratio,
            "mature_background_W2_final_cps": background_rate,
            "conditional_signal_accidental_survival": survival,
            "T_atm_511_slant45": transmission,
            "conditional_signal_proxy_Aeff_cm2": candidate_aeff,
            "conditional_signal_kernel_cm2": kernel_rate,
            "cumulative_background_counts": cumulative_background,
            "cumulative_signal_counts_per_unit_flux": cumulative_kernel,
            "Fmin_3sigma_gaussian_ph_cm2_s": gaussian3 if cumulative_kernel else "",
            "Fmin_5sigma_gaussian_ph_cm2_s": gaussian5 if cumulative_kernel else "",
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": asimov_flux(cumulative_background, cumulative_kernel, 3.0) if cumulative_kernel else "",
            "Fmin_5sigma_poisson_asimov_ph_cm2_s": asimov_flux(cumulative_background, cumulative_kernel, 5.0) if cumulative_kernel else "",
        }
        mission.append(row)
        previous_day = day
        previous_background = background_rate
        previous_kernel = kernel_rate

    anchor_fields = list(anchors_base[0])
    anchors: list[dict[str, Any]] = []
    for base in anchors_base:
        row: dict[str, Any] = dict(base)
        if base["window_id"] == "w2_510p58_511p42" and base["stage"] == "compton_trajectory_veto":
            node = int(base["time_bin_id"])
            gamma_scale = scales_by_node[node]
            direct_delta = (new_gamma_final - old_gamma_final) * gamma_scale
            occupancy_delta = (new_gamma_occupancy - old_gamma_occupancy) * gamma_scale
            adjustment = math.exp(-2.0 * occupancy_delta * TAU_S)
            old_direct = float(base["direct_no_coincidence_rate_cps"])
            new_direct = old_direct + direct_delta
            old_ratio = float(base["timeline_to_direct_ratio"])
            new_ratio = old_ratio * adjustment
            old_transport_sigma = float(base["direct_transport_MC_sigma_cps"])
            old_gamma_sigma = math.sqrt(old_gamma_raw) * old_gamma_weight * gamma_scale
            new_gamma_sigma = math.sqrt(new_gamma_raw) * new_gamma_weight * gamma_scale
            new_transport_sigma = math.sqrt(max(0.0, old_transport_sigma**2 - old_gamma_sigma**2) + new_gamma_sigma**2)
            row["direct_no_coincidence_rate_cps"] = new_direct
            row["timeline_rate_cps"] = new_direct * new_ratio
            row["timeline_rate_standard_error_cps"] = float(base["timeline_rate_standard_error_cps"]) * math.sqrt(new_direct / old_direct)
            row["timeline_to_direct_ratio"] = new_ratio
            row["direct_selected_transport_templates"] = int(base["direct_selected_transport_templates"]) - old_gamma_raw + new_gamma_raw
            row["direct_transport_MC_sigma_cps"] = new_transport_sigma
            row["direct_transport_MC_relative_sigma"] = new_transport_sigma / new_direct
            row["direct_transport_MC_effective_survivors"] = (new_direct / new_transport_sigma) ** 2
            row["signal_accidental_survival"] = float(base["signal_accidental_survival"]) * adjustment
            row["signal_survival_standard_error"] = float(base["signal_survival_standard_error"]) * adjustment
        anchors.append(row)

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "mission_mature_flux_threshold.csv", mission, list(mission[0]))
    write_csv(OUT / "anchor_timeline_rates.csv", anchors, anchor_fields)

    trapz = getattr(np, "trapezoid", None) or np.trapz
    days = np.asarray([float(row["day_mid"]) for row in mission], dtype=float)
    old_per_counts = float(trapz(np.asarray(old_per_survivor_rates), days) * SECONDS_PER_DAY)
    new_per_counts = float(trapz(np.asarray(new_per_survivor_rates), days) * SECONDS_PER_DAY)
    base_summary = load_json(BASE_OUT / "summary.json")
    base_transport = base_summary["transport_MC_uncertainty_final_20day"]
    transport_variance = (
        float(base_transport["background_counts_sigma"]) ** 2
        - old_gamma_raw * old_per_counts**2
        + new_gamma_raw * new_per_counts**2
    )
    transport_sigma = math.sqrt(max(0.0, transport_variance))
    final = mission[-1]
    final_background = float(final["cumulative_background_counts"])
    final_kernel = float(final["cumulative_signal_counts_per_unit_flux"])
    summary = dict(base_summary)
    summary["status"] = "PASS__SG3B_MATURE_TIMELINE__RETAINED_ANCHOR_GAMMA_REWEIGHT"
    summary["mission_final_20day"] = dict(final)
    summary["transport_MC_uncertainty_final_20day"] = {
        "background_counts_sigma": transport_sigma,
        "background_counts_relative_sigma": transport_sigma / final_background,
        "approximate_relative_sigma_on_Fmin_from_background_only": 0.5 * transport_sigma / final_background,
        "weighted_background_counts": final_background,
        "weighted_effective_survivors": (final_background / transport_sigma) ** 2,
        "selected_transport_templates": int(base_transport["selected_transport_templates"]) - old_gamma_raw + new_gamma_raw,
        "model": "retained non-gamma mission-correlated variance with exact old/new prompt-gamma survivor replacement",
    }
    summary["gamma_reweight"] = {
        "old_raw_survivors": old_gamma_raw,
        "new_raw_survivors": new_gamma_raw,
        "old_day15_rate_cps": old_gamma_final,
        "new_day15_rate_cps": new_gamma_final,
        "old_detector_positive_rate_cps": old_gamma_occupancy,
        "new_detector_positive_rate_cps": new_gamma_occupancy,
        "source": str(EXPANDED / "summary.json"),
        "boundary": "retained 81-node delayed curves and five common-time anchors; prompt-gamma category reweighted without fresh replay",
    }
    summary.setdefault("authority_boundary", {})["external_activation_manifest"] = "offline after host reboot; retained mature timeline used"
    summary["authority_boundary"]["gamma_update"] = "expanded corrected-keV compact catalog reweight"
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "background_counts_20d": final_background,
        "signal_kernel_20d": final_kernel,
        "Fmin_3sigma_gaussian": final["Fmin_3sigma_gaussian_ph_cm2_s"],
        "transport_sigma_counts": transport_sigma,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
