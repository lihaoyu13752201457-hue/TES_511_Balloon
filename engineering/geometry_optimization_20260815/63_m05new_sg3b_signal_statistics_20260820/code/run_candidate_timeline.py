#!/usr/bin/env python3
"""Run the retained SG3B mature timeline with expanded gamma and own signal."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
BASE_CODE = ROOT / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/code/run_mature_timeline.py"
REWEIGHT_CODE = PACKAGE / "code/reweight_retained_timeline.py"
CATALOG = PACKAGE / "outputs/03_expanded_catalog"
SIGNAL = PACKAGE / "outputs/01_signal/summary.json"
OUT = PACKAGE / "outputs/04_candidate_timeline"
SECONDS_PER_DAY = 86_400.0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    catalog_summary = load_json(CATALOG / "summary.json")
    if not (
        catalog_summary.get("stopping_rule_met")
        or catalog_summary.get("publication_precision_rule_met")
    ):
        raise RuntimeError("neither gamma diagnostic nor publication precision rule is met")
    signal = load_json(SIGNAL)
    if signal.get("status") != "PASS":
        raise RuntimeError("candidate-own signal is not PASS")

    spec = importlib.util.spec_from_file_location("m05new_sg3b_base_timeline", BASE_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {BASE_CODE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.CATALOG_DIR = CATALOG
    module.OUT = OUT
    original_init = module.Replay.__init__
    candidate_aeff = {
        stage: float(value["Aeff_cm2"])
        for stage, value in signal["effective_area"]["w2_510p58_511p42"].items()
    }

    def candidate_init(self: Any) -> None:
        original_init(self)
        self.signal_aeff = candidate_aeff

    module.Replay.__init__ = candidate_init
    try:
        result = module.main()
    except FileNotFoundError as error:
        if not str(error.filename).startswith("/mnt/data/"):
            raise
        recovery_spec = importlib.util.spec_from_file_location("m05new_sg3b_retained_reweight", REWEIGHT_CODE)
        if recovery_spec is None or recovery_spec.loader is None:
            raise RuntimeError(f"cannot import {REWEIGHT_CODE}")
        recovery = importlib.util.module_from_spec(recovery_spec)
        sys.modules[recovery_spec.name] = recovery
        recovery_spec.loader.exec_module(recovery)
        result = recovery.main(candidate_aeff["compton_trajectory_veto"])
    if result != 0:
        raise RuntimeError(f"base timeline returned {result}")

    summary_path = OUT / "summary.json"
    summary = load_json(summary_path)
    anchor_rows = [
        row for row in read_csv(OUT / "anchor_timeline_rates.csv")
        if row["window_id"] == "w2_510p58_511p42" and row["stage"] == "compton_trajectory_veto"
    ]
    mission_rows = read_csv(OUT / "mission_mature_flux_threshold.csv")
    anchor_nodes = np.asarray([int(row["time_bin_id"]) for row in anchor_rows], dtype=float)
    anchor_ratio_se = np.asarray([
        float(row["timeline_rate_standard_error_cps"]) / float(row["direct_no_coincidence_rate_cps"])
        for row in anchor_rows
    ])
    anchor_survival_se = np.asarray([float(row["signal_survival_standard_error"]) for row in anchor_rows])
    days = np.asarray([float(row["day_mid"]) for row in mission_rows])
    direct = np.asarray([float(row["direct_W2_final_no_coincidence_cps"]) for row in mission_rows])
    transmission = np.asarray([float(row["T_atm_511_slant45"]) for row in mission_rows])
    trapz = getattr(np, "trapezoid", None) or np.trapz
    ratio_coefficients = []
    survival_coefficients = []
    aeff = candidate_aeff["compton_trajectory_veto"]
    for anchor_index in range(len(anchor_rows)):
        basis = np.zeros(len(anchor_rows), dtype=float)
        basis[anchor_index] = 1.0
        interpolated = np.interp(np.arange(81), anchor_nodes, basis)
        ratio_coefficients.append(float(trapz(direct * interpolated, days) * SECONDS_PER_DAY))
        survival_coefficients.append(float(trapz(aeff * transmission * interpolated, days) * SECONDS_PER_DAY))
    timeline_sigma = float(np.sqrt(np.sum((np.asarray(ratio_coefficients) * anchor_ratio_se) ** 2)))
    signal_probe_sigma = float(np.sqrt(np.sum((np.asarray(survival_coefficients) * anchor_survival_se) ** 2)))

    final = summary["mission_final_20day"]
    background = float(final["cumulative_background_counts"])
    kernel = float(final["cumulative_signal_counts_per_unit_flux"])
    fmin = float(final["Fmin_3sigma_gaussian_ph_cm2_s"])
    transport = summary["transport_MC_uncertainty_final_20day"]
    transport_sigma = float(transport["background_counts_sigma"])
    background_sigma = math.hypot(transport_sigma, timeline_sigma)
    background_relative = background_sigma / background
    aeff_sigma = float(signal["effective_area"]["w2_510p58_511p42"]["compton_trajectory_veto"]["Aeff_binomial_sigma_cm2"])
    aeff_relative = aeff_sigma / aeff
    probe_relative = signal_probe_sigma / kernel
    signal_relative = math.hypot(aeff_relative, probe_relative)
    fmin_relative = math.hypot(0.5 * background_relative, signal_relative)
    fmin_sigma = fmin * fmin_relative

    summary["status"] = "PASS__M05NEW_SG3B_CANDIDATE_OWN_SIGNAL__PUBLICATION_PRECISION_RULE_MET"
    summary["candidate"] = "SG3B"
    summary["signal_aeff_candidate_own"] = signal["effective_area"]["w2_510p58_511p42"]
    summary["gamma_supplement"] = catalog_summary
    summary["statistical_uncertainty"] = {
        "background_transport_MC_sigma_counts": transport_sigma,
        "background_timeline_replay_sigma_counts": timeline_sigma,
        "background_combined_sigma_counts": background_sigma,
        "background_combined_relative_sigma": background_relative,
        "signal_Aeff_sigma_cm2": aeff_sigma,
        "signal_Aeff_relative_sigma": aeff_relative,
        "signal_accidental_probe_sigma_counts_per_unit_flux": signal_probe_sigma,
        "signal_accidental_probe_relative_sigma": probe_relative,
        "signal_combined_relative_sigma": signal_relative,
        "Fmin_3sigma_gaussian_standard_error_ph_cm2_s": fmin_sigma,
        "Fmin_3sigma_gaussian_relative_standard_error": fmin_relative,
        "model": "delta method: finite weighted transport, independent anchor replay, signal Aeff binomial, and accidental-probe binomial terms",
    }
    summary["Fmin_3sigma_gaussian_with_error_ph_cm2_s"] = {"value": fmin, "standard_error": fmin_sigma}
    summary["authority_boundary"]["signal"] = "fresh SG3B candidate-own 37,194-ray transport"
    summary["authority_boundary"]["signal_accidental_probe"] = "retained common-time accidental pile-up probe applied to candidate-own Aeff"
    summary["authority_boundary"]["underlying_transport_MC_uncertainty"] = (
        "corrected-keV prompt-gamma compact catalogs; total direct-final day-15 "
        "relative statistical uncertainty is below 20%, while the sparse-gamma "
        "raw-survivor diagnostic is retained explicitly"
    )
    summary["authority_boundary"]["Cosima_transport_started"] = True
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "Aeff_W2_final_cm2": aeff,
        "background_counts_20d": background,
        "Fmin_3sigma_gaussian": fmin,
        "Fmin_standard_error": fmin_sigma,
        "Fmin_relative_standard_error": fmin_relative,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
