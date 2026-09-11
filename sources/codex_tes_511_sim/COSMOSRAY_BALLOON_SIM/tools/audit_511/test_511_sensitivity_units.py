#!/usr/bin/env python3
"""Focused unit checks for the 511 keV sensitivity bookkeeping."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / "reports2.0" / "99_O15_BGO_ROOT_CAUSE_AUDIT" / "test_511_sensitivity_units.log"
LIKELIHOOD = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "likelihood_511" / "likelihood_sensitivity_by_model.csv"
SELECTION = ROOT / "reports2.0" / "10_POINT_DIFFUSE_DISCRIMINATION" / "selection_best_measured_energy_audit.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def approx(a: float, b: float, tol: float = 1e-12) -> None:
    if not math.isclose(a, b, rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"{a!r} != {b!r}")


def run_checks() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    # Analytic window-counting sanity.
    b_cps = 2.0
    exposure_s = 1.0e6
    aeff = 50.0
    eps = 0.65
    response = aeff * eps
    expected = 3.0 * math.sqrt(b_cps * exposure_s) / (response * exposure_s)
    approx(expected, 1.3054279037290106e-4, 1e-12)
    results.append({"check": "analytic_window_counting", "status": "PASS", "F3": expected})

    # Scaling checks.
    approx(3.0 * math.sqrt((4 * b_cps) * exposure_s) / (response * exposure_s), expected * 2.0)
    approx(3.0 * math.sqrt(b_cps * (4 * exposure_s)) / (response * (4 * exposure_s)), expected / 2.0)
    approx(3.0 * math.sqrt(b_cps * exposure_s) / ((2 * response) * exposure_s), expected / 2.0)
    results.append({"check": "scaling_background_exposure_response", "status": "PASS"})

    # FWHM / sigma conversion.
    sigma = 0.390 / 2.35482
    approx(sigma, 0.16561775422325273, 1e-12)
    results.append({"check": "fwhm_to_sigma", "status": "PASS", "sigma_keV": sigma})

    # Fisher/information-per-second formula and window-counting survival.
    for row in read_csv(LIKELIHOOD):
        exposure = float(row["exposure_s"])
        listed = float(row["flux_3sigma_ph_cm2_s"])
        info = float(row["information_per_s"])
        expected_info = 3.0 / math.sqrt(info * exposure)
        approx(listed, expected_info, 1e-12)
        if row["model"] == "window_counting_same_events":
            bkg = float(row["background_cps"])
            response_raw = float(row["response_cps_per_flux"])
            survival = float(row["science_survival"])
            response_surviving = response_raw * survival
            expected_window = 3.0 * math.sqrt(bkg * exposure) / (response_surviving * exposure)
            approx(listed, expected_window, 1e-12)
    results.append({"check": "fisher_information_and_window_survival", "status": "PASS"})

    # Component closure.
    for row in read_csv(SELECTION):
        if row.get("selection_id") == "baseline" and row.get("energy_basis") == "true":
            total = float(row["background_cps"])
            summed = float(row["prompt_cps"]) + float(row["delayed_cps"]) + float(row["focused_gamma_cps"])
            approx(summed, total, 1e-12)
    results.append({"check": "component_closure", "status": "PASS"})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=OUT_DEFAULT, help="Path to write the test log")
    args = parser.parse_args()

    results = run_checks()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"status": "PASS", "results": results}, indent=2, ensure_ascii=False)
    args.log.write_text(text + "\n", encoding="utf-8")
    print(f"Input likelihood: {LIKELIHOOD}")
    print(f"Input selection: {SELECTION}")
    print(f"Output log: {args.log}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
