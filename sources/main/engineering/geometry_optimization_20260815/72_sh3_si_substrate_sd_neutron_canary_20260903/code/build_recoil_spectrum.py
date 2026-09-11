#!/usr/bin/env python3
"""Build the strict Si elastic-recoil spectrum from the completed 10M catalog."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PRODUCTION = PACKAGE / "production_10m"
INPUT = PRODUCTION / "analysis_10m/si_event_catalog_10m.csv"
AUDIT = PRODUCTION / "quick_parallel_recoil_audit.json"
OUTPUTS = PRODUCTION / "recoil_spectrum"
EVENTS = OUTPUTS / "strict_si_elastic_recoil_events_10m.csv"
HISTOGRAM = OUTPUTS / "strict_si_elastic_recoil_spectrum_10m.csv"
SUMMARY = OUTPUTS / "strict_si_elastic_recoil_spectrum_10m.json"
PNG = OUTPUTS / "strict_si_elastic_recoil_spectrum_10m.png"
PDF = OUTPUTS / "strict_si_elastic_recoil_spectrum_10m.pdf"

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-sh3-si-recoil-spectrum")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main() -> int:
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)
    if not AUDIT.is_file():
        raise FileNotFoundError(AUDIT)
    if OUTPUTS.exists():
        raise FileExistsError(f"non-overwrite output gate: {OUTPUTS}")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS__READ_ONLY_PARALLEL_RECOIL_AUDIT":
        raise RuntimeError("parallel audit is not PASS authority")
    equivalent_time_s = float(audit["TT"]["combined_s"])

    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if float(row["si_elastic_recoil_keV"]) > 0.0
        ]
    if len(rows) != int(audit["strict_si_elastic_recoil_events"]):
        raise RuntimeError(
            f"independent recoil-count mismatch: catalog={len(rows)}, "
            f"parallel={audit['strict_si_elastic_recoil_events']}"
        )

    energies = np.asarray([float(row["si_elastic_recoil_keV"]) for row in rows])
    bgo = np.asarray([float(row["bgo_total_keV"]) for row in rows])
    veto_pass = bgo < 50.0
    log_edges = np.geomspace(0.5, 2000.0, 46)
    all_counts, _ = np.histogram(energies, bins=log_edges)
    pass_counts, _ = np.histogram(energies[veto_pass], bins=log_edges)
    widths = np.diff(log_edges)
    all_density = all_counts / (equivalent_time_s * widths)
    pass_density = pass_counts / (equivalent_time_s * widths)

    OUTPUTS.mkdir(parents=False, exist_ok=False)
    with EVENTS.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with HISTOGRAM.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            (
                "energy_low_keV", "energy_high_keV", "energy_center_keV",
                "all_count", "all_differential_rate_s-1_keV-1",
                "bgo_lt_50keV_count", "bgo_lt_50keV_differential_rate_s-1_keV-1",
            )
        )
        for low, high, n_all, r_all, n_pass, r_pass in zip(
            log_edges[:-1], log_edges[1:], all_counts, all_density,
            pass_counts, pass_density, strict=True,
        ):
            writer.writerow(
                (low, high, math.sqrt(low * high), n_all, r_all, n_pass, r_pass)
            )

    in_laue = (energies >= 480.0) & (energies <= 550.0)
    in_roi = (energies >= 510.58) & (energies < 511.42)
    high = energies >= 511.0
    payload = {
        "schema_version": 1,
        "status": "PASS__STRICT_SI_ELASTIC_RECOIL_SPECTRUM_BUILT",
        "histories": 10_000_000,
        "equivalent_time_s": equivalent_time_s,
        "definition": (
            "Si-substrate CC HIT with secondary Si*, parent neutron, cproc hadElastic"
        ),
        "counts": {
            "all": int(energies.size),
            "bgo_lt_50keV": int(np.count_nonzero(veto_pass)),
            "480_550keV": int(np.count_nonzero(in_laue)),
            "480_550keV_bgo_lt_50keV": int(np.count_nonzero(in_laue & veto_pass)),
            "510p58_511p42keV": int(np.count_nonzero(in_roi)),
            "510p58_511p42keV_bgo_lt_50keV": int(np.count_nonzero(in_roi & veto_pass)),
            "ge_511keV": int(np.count_nonzero(high)),
            "ge_511keV_bgo_lt_50keV": int(np.count_nonzero(high & veto_pass)),
        },
        "energy_keV": {
            "min": float(np.min(energies)),
            "median": float(np.median(energies)),
            "q90": float(np.quantile(energies, 0.90)),
            "q99": float(np.quantile(energies, 0.99)),
            "max": float(np.max(energies)),
        },
        "high_energy_candidates": [
            {
                "sample_id": row["sample_id"],
                "job_id": row["job_id"],
                "event_id": int(row["event_id"]),
                "recoil_keV": float(row["si_elastic_recoil_keV"]),
                "si_total_keV": float(row["si_total_keV"]),
                "tes_total_keV": float(row["tes_total_keV"]),
                "bgo_total_keV": float(row["bgo_total_keV"]),
                "bgo_lt_50keV": float(row["bgo_total_keV"]) < 50.0,
                "eta_for_511_from_recoil": 511.0 / float(row["si_elastic_recoil_keV"]),
            }
            for row in rows if float(row["si_elastic_recoil_keV"]) >= 511.0
        ],
        "spectrum": {
            "binning": "45 logarithmic bins from 0.5 to 2000 keV",
            "ordinate": "differential rate per equivalent second per keV",
            "histogram_csv": str(HISTOGRAM),
            "event_catalog_csv": str(EVENTS),
            "png": str(PNG),
            "pdf": str(PDF),
        },
        "interpretation_boundary": (
            "Raw Geant4 recoil deposition spectrum; no Si-to-TES phonon collection "
            "or TES response convolution."
        ),
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.fontsize": 9,
            "figure.dpi": 160,
        }
    )
    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(8.0, 7.2), gridspec_kw={"height_ratios": [1.25, 1.0]}
    )
    centers = np.sqrt(log_edges[:-1] * log_edges[1:])
    ax0.step(centers, np.where(all_density > 0, all_density, np.nan), where="mid",
             color="#d55e00", linewidth=1.7, label=f"All strict recoils (N={len(rows)})")
    ax0.step(centers, np.where(pass_density > 0, pass_density, np.nan), where="mid",
             color="#0072b2", linewidth=1.7,
             label=f"BGO < 50 keV (N={np.count_nonzero(veto_pass)})")
    ax0.axvspan(480, 550, color="#f0c419", alpha=0.18, label="480–550 keV band")
    ax0.axvspan(510.58, 511.42, color="#8e44ad", alpha=0.65,
                label="511-keV ROI")
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlim(0.5, 2000)
    ax0.set_ylabel(r"$dR/dE$ (s$^{-1}$ keV$^{-1}$)")
    ax0.set_title("SH3 Si-substrate neutron elastic-recoil spectrum")
    ax0.grid(True, which="both", alpha=0.18)
    ax0.legend(ncol=2, loc="upper right")

    zoom_edges = np.arange(450.0, 601.0, 5.0)
    zoom_all, _ = np.histogram(energies, bins=zoom_edges)
    zoom_pass, _ = np.histogram(energies[veto_pass], bins=zoom_edges)
    zoom_centers = (zoom_edges[:-1] + zoom_edges[1:]) / 2.0
    ax1.step(zoom_centers, zoom_all, where="mid", color="#d55e00", linewidth=1.7,
             label="All strict recoils")
    ax1.step(zoom_centers, zoom_pass, where="mid", color="#0072b2", linewidth=1.7,
             label="BGO < 50 keV")
    ax1.axvspan(480, 550, color="#f0c419", alpha=0.18)
    ax1.axvspan(510.58, 511.42, color="#8e44ad", alpha=0.65)
    ax1.scatter(energies[in_laue], np.full(np.count_nonzero(in_laue), -0.18),
                marker="|", s=80, color="#d55e00", clip_on=False)
    ax1.scatter(energies[in_laue & veto_pass],
                np.full(np.count_nonzero(in_laue & veto_pass), -0.38),
                marker="|", s=80, color="#0072b2", clip_on=False)
    ax1.set_xlim(450, 600)
    ax1.set_ylim(bottom=-0.6)
    ax1.set_xlabel("Raw Si elastic-recoil deposition (keV)")
    ax1.set_ylabel("Counts per 5-keV bin")
    ax1.set_title("Line-region zoom (rug marks show individual 480–550 keV recoils)")
    ax1.grid(True, alpha=0.18)
    ax1.legend(loc="upper right")
    fig.text(
        0.5, 0.01,
        "10⁷ atmospheric-neutron histories; equivalent time 1911.8824 s. "
        "Raw Geant4 deposition—no Si→TES phonon collection.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(PNG, bbox_inches="tight")
    fig.savefig(PDF, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
