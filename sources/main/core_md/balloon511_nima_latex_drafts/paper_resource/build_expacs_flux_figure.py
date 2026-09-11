#!/usr/bin/env python3
"""Build the manuscript EXPACS/PARMA full-sphere flux figure.

The figure is derived from the actual COSIMA source-card manifest rather than
from a hand-entered table.  It visualizes the particle-family fluxes and the
20 equal-mu angular bins used by the prompt and activation-production streams.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "expacs_fullsphere_20bin_sources" / "manifest.csv"
OUTDIR = ROOT / "core_md" / "balloon511_nima_latex_drafts" / "paper_source_figure_table"
FIG_PATH = OUTDIR / "fig_expacs_fullsphere_flux.png"
SUMMARY_CSV = OUTDIR / "fig_expacs_fullsphere_flux_summary.csv"
ANGULAR_CSV = OUTDIR / "fig_expacs_fullsphere_flux_angular_bins.csv"
SUMMARY_JSON = OUTDIR / "fig_expacs_fullsphere_flux_summary.json"

PARTICLE_ORDER = ["gamma", "n", "eminus", "eplus", "p", "alpha", "muminus", "muplus"]
PARTICLE_LABEL = {
    "gamma": r"$\gamma$",
    "n": "n",
    "eminus": r"$e^-$",
    "eplus": r"$e^+$",
    "p": "p",
    "alpha": r"$\alpha$",
    "muminus": r"$\mu^-$",
    "muplus": r"$\mu^+$",
}

COLORS = {
    "gamma": "#4C78A8",
    "n": "#F58518",
    "eminus": "#54A24B",
    "eplus": "#E45756",
    "p": "#72B7B2",
    "alpha": "#B279A2",
    "muminus": "#9D755D",
    "muplus": "#FF9DA6",
}


def read_rows() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    rows = read_rows()
    if not rows:
        raise SystemExit(f"No rows in {MANIFEST}")

    by_particle_dir: dict[tuple[str, str], float] = defaultdict(float)
    by_particle_bin: dict[tuple[str, int], float] = defaultdict(float)
    theta_mid: dict[int, float] = {}
    environment = {
        "latitude_deg": rows[0]["expacs_lat_deg"],
        "longitude_deg": rows[0]["expacs_lon_deg"],
        "altitude_km": rows[0]["expacs_altitude_km"],
        "Rc_GV": rows[0]["expacs_Rc_GV"],
        "W_or_date": rows[0]["W_or_date"],
        "delta_omega_sr": rows[0]["delta_omega_sr"],
    }

    for row in rows:
        particle = row["particle"]
        bin_id = int(row["bin_id"])
        direction = "down" if float(row["theta_max_deg"]) <= 90.0 else "up"
        flux = float(row["flux_cm2_s"])
        by_particle_dir[(particle, direction)] += flux
        by_particle_bin[(particle, bin_id)] += flux
        theta_mid[bin_id] = float(row["theta_mid_deg"])

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["particle", "down_flux_cm2_s", "up_flux_cm2_s", "total_flux_cm2_s"],
        )
        writer.writeheader()
        for particle in PARTICLE_ORDER:
            down = by_particle_dir[(particle, "down")]
            up = by_particle_dir[(particle, "up")]
            writer.writerow(
                {
                    "particle": particle,
                    "down_flux_cm2_s": f"{down:.12e}",
                    "up_flux_cm2_s": f"{up:.12e}",
                    "total_flux_cm2_s": f"{down + up:.12e}",
                }
            )

    with ANGULAR_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["particle", "bin_id", "theta_mid_deg", "flux_cm2_s"],
        )
        writer.writeheader()
        for particle in PARTICLE_ORDER:
            for bin_id in sorted(theta_mid):
                writer.writerow(
                    {
                        "particle": particle,
                        "bin_id": bin_id,
                        "theta_mid_deg": f"{theta_mid[bin_id]:.6f}",
                        "flux_cm2_s": f"{by_particle_bin[(particle, bin_id)]:.12e}",
                    }
                )

    totals = {
        particle: {
            "down_flux_cm2_s": by_particle_dir[(particle, "down")],
            "up_flux_cm2_s": by_particle_dir[(particle, "up")],
            "total_flux_cm2_s": by_particle_dir[(particle, "down")]
            + by_particle_dir[(particle, "up")],
        }
        for particle in PARTICLE_ORDER
    }
    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "manifest": str(MANIFEST.relative_to(ROOT)),
                "figure": str(FIG_PATH.relative_to(ROOT)),
                "environment": environment,
                "particle_totals": totals,
                "n_particles": len(PARTICLE_ORDER),
                "n_angular_bins": len(theta_mid),
                "angular_bin_note": "20 equal-mu bins over theta=0--180 deg; first 10 down-going, last 10 up-going.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "savefig.dpi": 300,
        }
    )

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11.8, 4.4))

    x = np.arange(len(PARTICLE_ORDER))
    width = 0.36
    down = np.array([by_particle_dir[(p, "down")] for p in PARTICLE_ORDER])
    up = np.array([by_particle_dir[(p, "up")] for p in PARTICLE_ORDER])
    ax0.bar(x - width / 2.0, down, width, label=r"$0^\circ$--$90^\circ$", color="#4C78A8")
    ax0.bar(x + width / 2.0, up, width, label=r"$90^\circ$--$180^\circ$", color="#F58518")
    ax0.set_yscale("log")
    ax0.set_xticks(x)
    ax0.set_xticklabels([PARTICLE_LABEL[p] for p in PARTICLE_ORDER])
    ax0.set_ylabel(r"Integrated flux per source plane area (cm$^{-2}$ s$^{-1}$)")
    ax0.set_title("Full-sphere particle-family flux")
    ax0.grid(True, axis="y", which="both", alpha=0.25)
    ax0.legend(frameon=False, loc="upper right")
    ax0.text(
        0.02,
        0.04,
        "lat=34 deg, lon=100 deg\naltitude=38 km, Rc=11.6 GV\n2025-08-31, W=118.3",
        transform=ax0.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 2},
    )

    bins = sorted(theta_mid)
    theta = np.array([theta_mid[b] for b in bins])
    for particle in PARTICLE_ORDER:
        y = np.array([by_particle_bin[(particle, b)] for b in bins])
        ax1.plot(
            theta,
            y,
            marker="o",
            linewidth=1.35,
            markersize=3.2,
            label=PARTICLE_LABEL[particle],
            color=COLORS[particle],
        )
    ax1.axvline(90.0, color="0.25", linestyle="--", linewidth=0.9)
    ax1.set_yscale("log")
    ax1.text(
        88.0,
        0.03,
        "down",
        transform=ax1.get_xaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=8,
    )
    ax1.text(
        92.0,
        0.03,
        "up",
        transform=ax1.get_xaxis_transform(),
        ha="left",
        va="bottom",
        fontsize=8,
    )
    ax1.set_xlabel(r"Zenith angle bin center $\theta$ (deg)")
    ax1.set_ylabel(r"Bin-integrated flux (cm$^{-2}$ s$^{-1}$)")
    ax1.set_title(r"20 equal-$\mu$ angular bins")
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(frameon=False, ncol=2, loc="upper right")
    ax1.set_xlim(0, 180)

    fig.tight_layout()
    fig.savefig(FIG_PATH, bbox_inches="tight")
    print(FIG_PATH.relative_to(ROOT))
    print(SUMMARY_CSV.relative_to(ROOT))
    print(ANGULAR_CSV.relative_to(ROOT))
    print(SUMMARY_JSON.relative_to(ROOT))


if __name__ == "__main__":
    main()
