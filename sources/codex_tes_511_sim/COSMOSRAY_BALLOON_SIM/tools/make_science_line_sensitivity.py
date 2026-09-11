#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build sensitivity rows for configured 511-keV intrinsic line models.

The line-model source builder creates Cosima source files and records the
intrinsic source fraction inside the broad and narrow analysis windows.  This
script propagates those fractions through the current corrected mono-source
response.  It is intentionally a lightweight normalization step, not a new
transport run.
"""

from __future__ import annotations

import argparse
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
DEFAULT_FRACTIONS = ROOT / "reports" / "nextphase_511" / "science_line_models" / "source_fraction_in_windows.csv"
DEFAULT_LIKELIHOOD = ROOT / "reports" / "nextphase_511" / "likelihood_511" / "likelihood_sensitivity_by_model.csv"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "science_line_models"
DET_FWHM_KEV = 0.14


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def likelihood_lookup(path: Path) -> dict[tuple[str, str, float], dict[str, str]]:
    rows = read_csv(path)
    out: dict[tuple[str, str, float], dict[str, str]] = {}
    for row in rows:
        out[(row["energy_window"], row["model"], float(row["exposure_s"]))] = row
    return out


def flux_threshold(background_cps: float, response_cps_per_flux: float, exposure_s: float, nsigma: float) -> float:
    if background_cps <= 0.0 or response_cps_per_flux <= 0.0 or exposure_s <= 0.0:
        return float("nan")
    return nsigma * math.sqrt(background_cps * exposure_s) / (response_cps_per_flux * exposure_s)


def gaussian_pdf(e: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    y = np.exp(-0.5 * ((e - mu) / sigma) ** 2)
    area = np.trapezoid(y, e)
    return y / area if area > 0 else y


def write_spectrum_plot(rows: list[dict[str, str]], outdir: Path) -> None:
    e = np.linspace(506.0, 516.0, 2500)
    sigma_det = DET_FWHM_KEV / 2.3548200450309493
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    for row in rows:
        fwhm = float(row["fwhm_src_keV"])
        sigma_src = fwhm / 2.3548200450309493
        sigma_obs = math.sqrt(sigma_src * sigma_src + sigma_det * sigma_det)
        label = row["model_id"].replace("gaussian_", "g_").replace("velocity_", "v_")
        ax.plot(e, gaussian_pdf(e, 511.0, max(sigma_obs, sigma_det)), lw=1.4, label=label)
    ax.axvspan(510.3, 511.8, color="#F58518", alpha=0.16, label="510.3-511.8 keV")
    ax.set_xlabel("Measured energy proxy (keV)")
    ax.set_ylabel("Normalized line density")
    ax.set_title("Intrinsic 511-keV line models convolved with 0.14 keV FWHM detector response")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(outdir / "spectrum_true_vs_measured_by_model.png", dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fractions", type=Path, default=DEFAULT_FRACTIONS)
    ap.add_argument("--likelihood", type=Path, default=DEFAULT_LIKELIHOOD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    fractions = read_csv(args.fractions)
    lk = likelihood_lookup(args.likelihood)
    base_broad = lk[("broad_480_550", "window_counting_same_events", 1.0e6)]
    base_line = lk[("line_510p3_511p8", "window_counting_same_events", 1.0e6)]

    window_base = {
        "broad_480_550": {
            "fraction_column": "fraction_480_550",
            "background_cps": float(base_broad["background_cps"]),
            "mono_response_cps_per_flux": float(base_broad["response_cps_per_flux"]),
            "survival": float(base_broad["science_survival"]),
        },
        "line_510p3_511p8": {
            "fraction_column": "fraction_510p3_511p8",
            "background_cps": float(base_line["background_cps"]),
            "mono_response_cps_per_flux": float(base_line["response_cps_per_flux"]),
            "survival": float(base_line["science_survival"]),
        },
    }

    out_rows: list[dict[str, Any]] = []
    for frac_row in fractions:
        for window, base in window_base.items():
            frac = float(frac_row[base["fraction_column"]])
            response = base["mono_response_cps_per_flux"] * frac
            response_after_timing = response * base["survival"]
            for exposure_s in (1.0e5, 1.0e6, 1.0e7):
                out_rows.append({
                    "model_id": frac_row["model_id"],
                    "type": frac_row["type"],
                    "fwhm_src_keV": frac_row["fwhm_src_keV"],
                    "energy_window": window,
                    "source_fraction_in_window": frac,
                    "background_cps": base["background_cps"],
                    "response_cps_per_flux_before_accidental": response,
                    "science_survival": base["survival"],
                    "response_cps_per_flux_after_accidental": response_after_timing,
                    "exposure_s": exposure_s,
                    "flux_3sigma_ph_cm2_s": flux_threshold(base["background_cps"], response_after_timing, exposure_s, 3.0),
                    "flux_5sigma_ph_cm2_s": flux_threshold(base["background_cps"], response_after_timing, exposure_s, 5.0),
                })

    out_csv = args.out / "sensitivity_by_line_model.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    write_spectrum_plot(fractions, args.out)

    one_ms = [r for r in out_rows if abs(float(r["exposure_s"]) - 1.0e6) < 1.0]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    labels = []
    vals = []
    colors = []
    for r in one_ms:
        labels.append(f"{r['model_id']}\n{r['energy_window'].replace('_', ' ')}")
        vals.append(float(r["flux_3sigma_ph_cm2_s"]))
        colors.append("#4C78A8" if r["energy_window"] == "broad_480_550" else "#F58518")
    ax.bar(np.arange(len(vals)), vals, color=colors)
    ax.set_xticks(np.arange(len(vals)), labels, rotation=55, ha="right", fontsize=7)
    ax.set_ylabel("3 sigma flux threshold, 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Line-width effect on window-counting sensitivity")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.out / "sensitivity_by_line_model.png", dpi=220)
    plt.close(fig)

    audit = {
        "status": "PASS",
        "method": "Window source fractions propagated through current corrected mono-source response and timing-survival corrections.",
        "detector_response_fwhm_keV_for_plot": DET_FWHM_KEV,
        "rows_written": len(out_rows),
        "outputs": [
            "sensitivity_by_line_model.csv",
            "sensitivity_by_line_model.png",
            "spectrum_true_vs_measured_by_model.png",
        ],
    }
    (args.out / "science_line_sensitivity_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
