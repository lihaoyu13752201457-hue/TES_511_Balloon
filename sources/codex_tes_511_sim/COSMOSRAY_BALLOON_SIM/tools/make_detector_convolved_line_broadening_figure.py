#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build detector-convolved 511-keV line-model diagnostic figure."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
LINE_DIR = R2 / "03_NEXT_PHASE_SUPPORT" / "science_line_models"
OUT_DIR = R2 / "04_FIGURES" / "nima_update"
FRACTIONS_CSV = LINE_DIR / "source_fraction_in_windows.csv"
SENS_CSV = LINE_DIR / "sensitivity_by_line_model.csv"
GATE_B_JSON = R2 / "03_NEXT_PHASE_SUPPORT" / "gate_B_detector_response" / "detector_response_summary.json"

E0_KEV = 511.0
DET_FWHM_KEV = 0.14
FWHM_TO_SIGMA = 1.0 / 2.3548200450309493
LINE_LO_KEV = 510.3
LINE_HI_KEV = 511.8
EXPOSURE_S = 1.0e6


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def gaussian_pdf(e: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    y = np.exp(-0.5 * ((e - mu) / sigma) ** 2)
    area = np.trapezoid(y, e)
    return y / area if area > 0 else y


def gaussian_fraction(lo: float, hi: float, mu: float, sigma: float) -> float:
    def cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))

    return cdf(hi) - cdf(lo)


def flux_threshold(background_cps: float, response_cps_per_flux_after_timing: float) -> float:
    return 3.0 * math.sqrt(background_cps * EXPOSURE_S) / (response_cps_per_flux_after_timing * EXPOSURE_S)


def clean_label(model_id: str) -> str:
    return model_id.replace("gaussian_", "g_").replace("velocity_", "v_")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fractions = read_csv(FRACTIONS_CSV)
    sensitivity = read_csv(SENS_CSV)
    gate_b = json.loads(GATE_B_JSON.read_text(encoding="utf-8"))

    line_measured = gate_b["windows"]["510.3-511.8_measured"]
    background_cps = float(line_measured["background_final_cps"])
    response_mono = float(line_measured["science_final_cps"]) / 1.0e-4

    base_line = next(
        r for r in sensitivity
        if r["model_id"] == "mono"
        and r["energy_window"] == "line_510p3_511p8"
        and abs(float(r["exposure_s"]) - EXPOSURE_S) < 1.0
    )
    survival = float(base_line["science_survival"])

    sigma_det = DET_FWHM_KEV * FWHM_TO_SIGMA
    rows: list[dict[str, Any]] = []
    for row in fractions:
        sigma_src = float(row["sigma_src_keV"])
        fwhm_src = float(row["fwhm_src_keV"])
        frac_intrinsic = float(row["fraction_510p3_511p8"])
        sigma_obs = math.sqrt(sigma_src * sigma_src + sigma_det * sigma_det)
        fwhm_obs = sigma_obs / FWHM_TO_SIGMA
        frac_conv = gaussian_fraction(LINE_LO_KEV, LINE_HI_KEV, E0_KEV, sigma_obs)
        response_intrinsic = response_mono * frac_intrinsic * survival
        response_conv = response_mono * frac_conv * survival
        threshold_intrinsic = flux_threshold(background_cps, response_intrinsic)
        threshold_conv = flux_threshold(background_cps, response_conv)
        rows.append({
            "model_id": row["model_id"],
            "type": row["type"],
            "fwhm_src_keV": fwhm_src,
            "fwhm_detector_keV": DET_FWHM_KEV,
            "fwhm_observed_keV": fwhm_obs,
            "fraction_intrinsic_510p3_511p8": frac_intrinsic,
            "fraction_detector_convolved_510p3_511p8": frac_conv,
            "background_measured_cps": background_cps,
            "mono_response_cps_per_flux": response_mono,
            "science_survival": survival,
            "flux_3sigma_1Ms_intrinsic_fraction": threshold_intrinsic,
            "flux_3sigma_1Ms_detector_convolved": threshold_conv,
            "threshold_rel_change_percent": 100.0 * (threshold_conv / threshold_intrinsic - 1.0),
        })

    write_csv(LINE_DIR / "detector_convolved_line_sensitivity.csv", rows)

    colors = {
        "mono": "#333333",
        "gaussian_fwhm_0p5": "#4C78A8",
        "gaussian_fwhm_1p5": "#F58518",
        "gaussian_fwhm_2p5": "#E45756",
        "velocity_sigma_100": "#72B7B2",
        "velocity_sigma_300": "#59A14F",
        "velocity_sigma_600": "#54A24B",
        "velocity_sigma_1000": "#B279A2",
    }
    plot_ids = ["mono", "gaussian_fwhm_0p5", "gaussian_fwhm_1p5", "gaussian_fwhm_2p5", "velocity_sigma_600", "velocity_sigma_1000"]
    row_by_id = {r["model_id"]: r for r in rows}

    e = np.linspace(506.0, 516.0, 3000)
    fig = plt.figure(figsize=(13.2, 7.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0])
    ax_profile = fig.add_subplot(gs[0, :])
    ax_fwhm = fig.add_subplot(gs[1, 0])
    ax_sens = fig.add_subplot(gs[1, 1])

    for model_id in plot_ids:
        r = row_by_id[model_id]
        color = colors[model_id]
        fwhm_src = float(r["fwhm_src_keV"])
        sigma_src = fwhm_src * FWHM_TO_SIGMA
        sigma_obs = float(r["fwhm_observed_keV"]) * FWHM_TO_SIGMA
        label = clean_label(model_id)
        if sigma_src > 0:
            ax_profile.plot(e, gaussian_pdf(e, E0_KEV, sigma_src), color=color, lw=1.0, ls="--", alpha=0.45)
        ax_profile.plot(e, gaussian_pdf(e, E0_KEV, sigma_obs), color=color, lw=1.7, label=label)

    ax_profile.axvspan(LINE_LO_KEV, LINE_HI_KEV, color="#F58518", alpha=0.14, label="510.3-511.8 keV")
    ax_profile.set_title("Intrinsic 511-keV line models convolved with TES response")
    ax_profile.set_xlabel("Measured energy proxy (keV)")
    ax_profile.set_ylabel("Normalized density")
    ax_profile.grid(True, alpha=0.25)
    ax_profile.legend(fontsize=8, ncols=4)
    ax_profile.text(
        0.01,
        0.97,
        "solid: intrinsic line x TES FWHM 0.14 keV; dashed: intrinsic only",
        transform=ax_profile.transAxes,
        va="top",
        fontsize=9,
        color="#333333",
    )

    labels = [clean_label(r["model_id"]) for r in rows]
    x = np.arange(len(rows))
    width = 0.38
    fwhm_src_vals = [float(r["fwhm_src_keV"]) for r in rows]
    fwhm_obs_vals = [float(r["fwhm_observed_keV"]) for r in rows]
    ax_fwhm.bar(x - width / 2, fwhm_src_vals, width=width, color="#9E9E9E", label="source FWHM")
    ax_fwhm.bar(x + width / 2, fwhm_obs_vals, width=width, color="#4C78A8", label="after TES convolution")
    ax_fwhm.set_xticks(x, labels, rotation=35, ha="right", fontsize=8)
    ax_fwhm.set_ylabel("FWHM (keV)")
    ax_fwhm.set_title("Observed width is quadrature-summed")
    ax_fwhm.grid(True, axis="y", alpha=0.25)
    ax_fwhm.legend(fontsize=8)

    old_thr = [float(r["flux_3sigma_1Ms_intrinsic_fraction"]) * 1.0e4 for r in rows]
    new_thr = [float(r["flux_3sigma_1Ms_detector_convolved"]) * 1.0e4 for r in rows]
    ax_sens.bar(x - width / 2, old_thr, width=width, color="#9E9E9E", label="intrinsic fraction")
    ax_sens.bar(x + width / 2, new_thr, width=width, color="#E45756", label="detector-convolved")
    ax_sens.set_xticks(x, labels, rotation=35, ha="right", fontsize=8)
    ax_sens.set_ylabel("1 Ms 3 sigma threshold (1e-4 ph cm$^{-2}$ s$^{-1}$)")
    ax_sens.set_title("Narrow-window sensitivity after convolution")
    ax_sens.grid(True, axis="y", alpha=0.25)
    ax_sens.legend(fontsize=8)

    fig.savefig(OUT_DIR / "science_line_broadening_detector_convolved.png", dpi=220)
    plt.close(fig)
    print(OUT_DIR / "science_line_broadening_detector_convolved.png")
    print(LINE_DIR / "detector_convolved_line_sensitivity.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
