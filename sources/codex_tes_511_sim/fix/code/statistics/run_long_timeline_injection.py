#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run binned Poisson source-injection studies for long 511-keV timelines.

This is the statistical long-timeline realization layer for the current
corrected catalog.  For each window/model it uses the same signal/background
templates as the Asimov likelihood study and draws Poisson binned counts for
specified input fluxes and exposures.  The recovered flux is the score/Fisher
linear estimator, which is unbiased for the template model in the small-signal
regime.
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


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIKELIHOOD = ROOT / "statistics" / "nextphase_511" / "likelihood_511"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "long_timeline_injection"
FLUXES = [0.0, 5.0e-5, 1.0e-4, 2.0e-4, 5.0e-4]
EXPOSURES = [1.0e5, 1.0e6, 1.0e7]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_likelihood_rows(path: Path) -> list[dict[str, str]]:
    return read_csv(path / "likelihood_sensitivity_by_model.csv")


def load_template(path: Path, survival: float) -> tuple[np.ndarray, np.ndarray, int]:
    rows = read_csv(path)
    b = []
    s = []
    ignored = 0
    for row in rows:
        br = float(row["background_cps"])
        sr = float(row["signal_cps_per_flux"]) * survival
        if br > 0.0:
            b.append(br)
            s.append(sr)
        elif sr > 0.0:
            ignored += 1
    return np.asarray(b, dtype=float), np.asarray(s, dtype=float), ignored


def model_arrays(row: dict[str, str], likelihood_dir: Path) -> tuple[np.ndarray, np.ndarray, int]:
    window = row["energy_window"]
    model = row["model"]
    survival = float(row["science_survival"])
    if model == "window_counting_same_events":
        return (
            np.asarray([float(row["background_cps"])], dtype=float),
            np.asarray([float(row["response_cps_per_flux"]) * survival], dtype=float),
            0,
        )
    if model == "energy_template":
        return load_template(likelihood_dir / f"template_{window}_energy.csv", survival)
    if model == "energy_radius_layer_template":
        return load_template(likelihood_dir / f"template_{window}_energy_spatial.csv", survival)
    raise ValueError(f"unsupported model {model}")


def score_recover(rng: np.random.Generator, b: np.ndarray, s: np.ndarray, flux: float, exposure_s: float, n_realizations: int) -> dict[str, float]:
    info_per_s = float(np.sum((s * s) / b))
    fisher = exposure_s * info_per_s
    if fisher <= 0.0:
        return {k: float("nan") for k in (
            "mean_recovered_flux", "std_recovered_flux", "median_recovered_flux",
            "q16_recovered_flux", "q84_recovered_flux", "bias_flux",
            "mean_z", "std_z", "detection_probability_3sigma", "detection_probability_5sigma",
        )}
    lam = (b + flux * s) * exposure_s
    counts = rng.poisson(lam=lam, size=(n_realizations, len(b)))
    expected_b = b * exposure_s
    score = np.sum((counts - expected_b) * (s / b), axis=1)
    recovered = score / fisher
    z = score / math.sqrt(fisher)
    return {
        "mean_recovered_flux": float(np.mean(recovered)),
        "std_recovered_flux": float(np.std(recovered, ddof=1)),
        "median_recovered_flux": float(np.median(recovered)),
        "q16_recovered_flux": float(np.quantile(recovered, 0.16)),
        "q84_recovered_flux": float(np.quantile(recovered, 0.84)),
        "bias_flux": float(np.mean(recovered) - flux),
        "mean_z": float(np.mean(z)),
        "std_z": float(np.std(z, ddof=1)),
        "detection_probability_3sigma": float(np.mean(z >= 3.0)),
        "detection_probability_5sigma": float(np.mean(z >= 5.0)),
    }


def make_plots(rows: list[dict[str, Any]], outdir: Path) -> None:
    one_ms = [r for r in rows if abs(float(r["exposure_s"]) - 1.0e6) < 1.0]
    models = sorted({(r["energy_window"], r["model"]) for r in one_ms})

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for window, model in models:
        sub = sorted(
            [r for r in one_ms if r["energy_window"] == window and r["model"] == model],
            key=lambda x: float(x["input_flux_ph_cm2_s"]),
        )
        x = np.asarray([float(r["input_flux_ph_cm2_s"]) for r in sub])
        y = np.asarray([float(r["detection_probability_3sigma"]) for r in sub])
        label = f"{window}/{model}".replace("window_counting_same_events", "window")
        ax.plot(x, y, marker="o", lw=1.4, label=label)
    ax.set_xlabel("Injected flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("P(detection >= 3 sigma), 1 Ms")
    ax.set_title("Long-timeline source-injection detection probability")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir / "detection_probability_vs_flux.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for window, model in models:
        if model not in {"window_counting_same_events", "energy_radius_layer_template"}:
            continue
        sub = sorted(
            [r for r in one_ms if r["energy_window"] == window and r["model"] == model],
            key=lambda x: float(x["input_flux_ph_cm2_s"]),
        )
        x = np.asarray([float(r["input_flux_ph_cm2_s"]) for r in sub])
        y = np.asarray([float(r["mean_recovered_flux"]) for r in sub])
        yerr = np.asarray([float(r["std_recovered_flux"]) for r in sub])
        label = f"{window}/{model}".replace("window_counting_same_events", "window")
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, lw=1.2, label=label)
    lim = max(FLUXES) * 1.08
    ax.plot([0, lim], [0, lim], color="black", lw=1.0, alpha=0.5)
    ax.set_xlabel("Injected flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("Recovered flux, 1 Ms")
    ax.set_title("Flux recovery in Poisson source-injection tests")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir / "recovered_flux_vs_true_flux.png", dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--likelihood-dir", type=Path, default=DEFAULT_LIKELIHOOD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--realizations", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=260551109)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    likelihood_rows = load_likelihood_rows(args.likelihood_dir)
    model_rows = [r for r in likelihood_rows if abs(float(r["exposure_s"]) - 1.0e6) < 1.0]

    output_rows: list[dict[str, Any]] = []
    for like_row in model_rows:
        b, s, ignored = model_arrays(like_row, args.likelihood_dir)
        info_per_s = float(np.sum((s * s) / b))
        for exposure_s in EXPOSURES:
            for flux in FLUXES:
                stats = score_recover(rng, b, s, flux, exposure_s, args.realizations)
                output_rows.append({
                    "energy_window": like_row["energy_window"],
                    "model": like_row["model"],
                    "exposure_s": exposure_s,
                    "input_flux_ph_cm2_s": flux,
                    "n_realizations": args.realizations,
                    "n_bins_used": int(len(b)),
                    "signal_only_bins_ignored": int(ignored),
                    "background_cps_sum_used": float(np.sum(b)),
                    "response_cps_per_flux_sum_used_after_accidental": float(np.sum(s)),
                    "information_per_s_used": info_per_s,
                    "nominal_flux_3sigma_ph_cm2_s": 3.0 / math.sqrt(exposure_s * info_per_s) if info_per_s > 0 else float("nan"),
                    "nominal_flux_5sigma_ph_cm2_s": 5.0 / math.sqrt(exposure_s * info_per_s) if info_per_s > 0 else float("nan"),
                    **stats,
                })

    out_csv = args.out / "injection_recovery_summary.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    false_rows = [r for r in output_rows if float(r["input_flux_ph_cm2_s"]) == 0.0]
    with (args.out / "false_positive_rate.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = [
            "energy_window",
            "model",
            "exposure_s",
            "n_realizations",
            "false_positive_rate_3sigma",
            "false_positive_rate_5sigma",
            "mean_z",
            "std_z",
        ]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in false_rows:
            writer.writerow({
                "energy_window": row["energy_window"],
                "model": row["model"],
                "exposure_s": row["exposure_s"],
                "n_realizations": row["n_realizations"],
                "false_positive_rate_3sigma": row["detection_probability_3sigma"],
                "false_positive_rate_5sigma": row["detection_probability_5sigma"],
                "mean_z": row["mean_z"],
                "std_z": row["std_z"],
            })

    make_plots(output_rows, args.out)

    one_ms_f1e4 = [
        r for r in output_rows
        if abs(float(r["exposure_s"]) - 1.0e6) < 1.0 and abs(float(r["input_flux_ph_cm2_s"]) - 1.0e-4) < 1.0e-12
    ]
    summary = {
        "status": "PASS",
        "method": "Binned Poisson source injection using current likelihood templates; recovered flux is score/Fisher estimator.",
        "realizations": args.realizations,
        "seed": args.seed,
        "flux_grid_ph_cm2_s": FLUXES,
        "exposure_grid_s": EXPOSURES,
        "one_ms_flux_1e_minus_4_detection": [
            {
                "energy_window": r["energy_window"],
                "model": r["model"],
                "detection_probability_3sigma": r["detection_probability_3sigma"],
                "mean_recovered_flux": r["mean_recovered_flux"],
                "std_recovered_flux": r["std_recovered_flux"],
            }
            for r in one_ms_f1e4
        ],
        "caveat": "This is a statistical long-timeline injection based on current static day-15 templates. It does not rerun a detector-response or real flight-profile event transport.",
    }
    (args.out / "long_timeline_injection_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Long Timeline Source-Injection", "", "Status: `PASS`", ""]
    md.append("Binned Poisson realizations were drawn from the current corrected 511-keV signal/background templates.")
    md.append("")
    md.append("## 1 Ms, injected flux 1e-4 ph cm^-2 s^-1")
    for r in one_ms_f1e4:
        md.append(
            f"- `{r['energy_window']}` / `{r['model']}`: "
            f"P(>=3 sigma) `{float(r['detection_probability_3sigma']):.4f}`, "
            f"mean recovered `{float(r['mean_recovered_flux']):.6g}`."
        )
    md.append("")
    md.append("Caveat: " + summary["caveat"])
    (args.out / "long_timeline_injection_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    audit = {"status": "PASS", "rows_written": len(output_rows), "summary": "long_timeline_injection_summary.json"}
    (args.out / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
