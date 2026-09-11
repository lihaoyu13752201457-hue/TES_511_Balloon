#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Annotate the day-15 480-550 keV veto-chain spectrum with the reference 511 source."""

from __future__ import annotations

import csv
import json
import pickle
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from make_complete_day15_report import (  # noqa: E402
    BGO_THR_KEV,
    ZOOM_BINW,
    ZOOM_EMAX,
    ZOOM_EMIN,
    add_hist,
    axis,
    classify_final,
    event_hits,
)


REPORT = ROOT / "reports" / "day15_complete_report"
R2 = ROOT / "reports2.0"
CATALOG = REPORT / "work" / "event_catalog.pkl"
TIMELINE_CSV = REPORT / "timeline_spectrum_480_550_rates.csv"
SUMMARY_JSON = REPORT / "complete_day15_summary.json"
OUT = R2 / "04_FIGURES" / "day15" / "timeline_spectrum_480_550_veto_chain_with_science_marker.png"
OUT_CSV = R2 / "04_FIGURES" / "day15" / "timeline_spectrum_480_550_with_science_marker.csv"


def read_timeline(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols: dict[str, list[float]] = {k: [] for k in rows[0].keys()}
    for row in rows:
        for k, v in row.items():
            cols[k].append(float(v))
    return {k: np.asarray(v, dtype=float) for k, v in cols.items()}


def science_stage_spectra(cat: dict, reject_policy: str) -> dict[str, np.ndarray]:
    n_zoom = int((ZOOM_EMAX - ZOOM_EMIN) / ZOOM_BINW)
    raw = np.zeros(n_zoom, dtype=float)
    bgo = np.zeros(n_zoom, dtype=float)
    final = np.zeros(n_zoom, dtype=float)
    streams = cat["stream"].astype(str)
    for i in np.flatnonzero(streams == "science"):
        e = float(cat["tes_total_keV"][i])
        if not (ZOOM_EMIN <= e < ZOOM_EMAX):
            continue
        rate = float(cat["rate_hz"][i])
        add_hist(raw, e, rate, ZOOM_EMIN, ZOOM_BINW)
        if float(cat["bgo_total_keV"][i]) >= BGO_THR_KEV:
            continue
        add_hist(bgo, e, rate, ZOOM_EMIN, ZOOM_BINW)
        keep, _ = classify_final(event_hits(cat, int(i)), reject_policy)
        if keep:
            add_hist(final, e, rate, ZOOM_EMIN, ZOOM_BINW)
    return {"raw": raw, "bgo": bgo, "final": final}


def write_csv(path: Path, cols: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(cols)
    n = len(next(iter(cols.values())))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(names)
        for i in range(n):
            w.writerow([f"{cols[k][i]:.12g}" for k in names])


def main() -> int:
    data = read_timeline(TIMELINE_CSV)
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    with CATALOG.open("rb") as fh:
        cat = pickle.load(fh)

    _, centers = axis(ZOOM_EMIN, ZOOM_EMAX, ZOOM_BINW)
    science = science_stage_spectra(cat, summary["normalization"]["reject_policy"])
    science_raw_rate = float(np.sum(science["raw"]))
    science_bgo_rate = float(np.sum(science["bgo"]))
    science_final_rate = float(np.sum(science["final"]))
    bgo_survival = science_bgo_rate / science_raw_rate if science_raw_rate > 0 else 0.0
    final_survival = science_final_rate / science_raw_rate if science_raw_rate > 0 else 0.0
    final_given_bgo = science_final_rate / science_bgo_rate if science_bgo_rate > 0 else 0.0
    background_final = float(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"])
    science_flux = float(summary["normalization"]["science_flux_ph_cm2_s"])
    ratio = science_final_rate / background_final if background_final > 0 else 0.0

    plot_floor = 1.0e-6
    fig, ax = plt.subplots(figsize=(11.0, 6.2))
    ax.step(centers, data["timeline_raw_cps_per_bin"], where="mid", label="Timeline no veto", lw=1.5)
    ax.step(centers, data["timeline_bgo_cps_per_bin"], where="mid", label="Timeline BGO veto", lw=1.5)
    ax.step(centers, data["timeline_final_cps_per_bin"], where="mid", label="Timeline BGO+Compton/FoV", lw=1.8)
    ax.step(
        centers,
        np.where(science["final"] > 0, science["final"], np.nan),
        where="mid",
        color="#E45756",
        lw=2.2,
        label=f"Reference 511 source final, F={science_flux:.0e}",
        zorder=5,
    )
    ax.axvline(511.0, color="#E45756", lw=1.2, ls=":", alpha=0.9)
    ax.text(
        511.25,
        max(np.nanmax(science["final"]) * 1.6, plot_floor),
        "511 keV source",
        color="#E45756",
        fontsize=10,
        va="bottom",
    )
    txt_left = (
        f"timeline no veto: {summary['timeline_rates_cps']['raw']:.4g} cps\n"
        f"BGO: {summary['timeline_rates_cps']['bgo']:.4g} cps\n"
        f"BGO+Compton/FoV: {summary['timeline_rates_cps']['final']:.4g} cps"
    )
    ax.text(
        0.02,
        0.98,
        txt_left,
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox=dict(facecolor="white", alpha=0.88, edgecolor="none"),
    )
    txt_right = (
        "Reference 511 source veto chain, direct expectation:\n"
        f"raw {science_raw_rate:.4g} cps -> BGO {science_bgo_rate:.4g} cps "
        f"({100.0 * bgo_survival:.3f}% surv.)\n"
        f"final {science_final_rate:.4g} cps "
        f"({100.0 * final_survival:.3f}% raw-to-final; "
        f"{100.0 * (1.0 - final_survival):.3f}% loss)\n"
        f"not counted as background; final/background = {100.0 * ratio:.4g}%."
    )
    ax.text(
        0.98,
        0.04,
        txt_right,
        transform=ax.transAxes,
        va="bottom",
        ha="right",
        bbox=dict(facecolor="white", alpha=0.88, edgecolor="none"),
        fontsize=9.5,
    )
    ax.set_yscale("log")
    ax.set_ylim(bottom=plot_floor)
    ax.set_xlim(ZOOM_EMIN, ZOOM_EMAX)
    ax.set_xlabel("TES event/candidate summed energy (keV)")
    ax.set_ylabel("Rate (counts s$^{-1}$ bin$^{-1}$)")
    ax.set_title("511 keV window: time-axis veto chain with reference source marked")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8.5, loc="upper right")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220)
    plt.close(fig)

    write_csv(
        OUT_CSV,
        {
            "E_keV": centers,
            "timeline_raw_cps_per_bin": data["timeline_raw_cps_per_bin"],
            "timeline_bgo_cps_per_bin": data["timeline_bgo_cps_per_bin"],
            "timeline_final_cps_per_bin": data["timeline_final_cps_per_bin"],
            "reference_511_source_raw_expectation_cps_per_bin": science["raw"],
            "reference_511_source_bgo_expectation_cps_per_bin": science["bgo"],
            "reference_511_source_final_expectation_cps_per_bin": science["final"],
        },
    )
    print(OUT)
    print(OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
