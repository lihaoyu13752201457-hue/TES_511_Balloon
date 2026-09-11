#!/usr/bin/env python3
"""Build the manuscript schematic for the atmospheric 511 keV line supplement.

Panel (a) shows that the tabulated EXPACS/PARMA gamma spectrum has no 511 keV
line feature (the 511 keV ordinate is only a continuum interpolation) and that a
separate monoenergetic line source is added on top. Panel (b) shows the 4pi
angular model of the added line (downward residual-atmosphere slab kernel and
upward Earth-albedo limb darkening).

The script reads the archived EXPACS 511 gap excerpt and reuses the current
atmospheric-511 sidecar source parameters; it does not rerun transport.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = (
    ROOT
    / "core_md"
    / "balloon511_ea_latex_drafts"
    / "paper_source_figure_table"
    / "fig_atm511_line_supplement.png"
)
EXCERPT = (
    ROOT
    / "engineering"
    / "geometry_optimization_20260704"
    / "11_expacs_atm511_line_gap_20260707"
    / "gamma_bin00_theta18p19_excerpt_around_511.csv"
)

# Signal window (W2) around the 511 keV line.
W2_LO, W2_HI = 510.58, 511.42

# Atmospheric-511 sidecar reference parameters (2026-07-08 4pi sidecar replay).
PHI_4PI = 5.15558541132e-2   # ph cm^-2 s^-1
PHI_UP = 4.31027869674e-2    # upward Earth-albedo
PHI_DOWN = 8.45306714584e-3  # downward residual atmosphere
R_DOWN = 0.196114
X_DEPTH = 3.46147            # g cm^-2 residual depth at the reference condition
LAMBDA_511 = 11.5            # g cm^-2 air attenuation scale at 511 keV
ALBEDO_A = 1.7              # HEAO-3/SMM limb-darkening index


def read_excerpt() -> list[dict[str, str]]:
    with open(EXCERPT) as fh:
        return list(csv.DictReader(fh))


def slab_kernel(mu: np.ndarray) -> np.ndarray:
    """Downward slab production/escape kernel K(mu, X) for mu = cos(theta) > 0."""
    mu = np.clip(mu, 1e-6, 1.0)
    return 1.0 - np.exp(-X_DEPTH / (LAMBDA_511 * mu))


def panel_spectrum(ax: plt.Axes, rows: list[dict[str, str]]) -> None:
    energy = np.array([float(r["energy_keV"]) for r in rows])
    pdf = np.array([float(r["pdf_per_keV"]) for r in rows])
    is_interp = np.array(["interpolation" in r["status"] for r in rows])

    table_e, table_p = energy[~is_interp], pdf[~is_interp]
    interp_e, interp_p = energy[is_interp], pdf[is_interp]

    # Continuum through the EXPACS table points.
    order = np.argsort(table_e)
    ax.plot(
        table_e[order],
        table_p[order],
        "-",
        color="0.45",
        lw=1.6,
        zorder=2,
        label="EXPACS gamma continuum",
    )
    ax.plot(
        table_e[order],
        table_p[order],
        "o",
        color="0.15",
        ms=6,
        zorder=3,
        label="EXPACS table points",
    )
    # The 511 keV ordinate: interpolation only, not a line.
    ax.plot(
        interp_e,
        interp_p,
        "o",
        mfc="white",
        mec="#c0392b",
        mew=1.8,
        ms=8,
        zorder=4,
        label="511 keV: interpolation only",
    )

    # Signal window band.
    ax.axvspan(W2_LO, W2_HI, color="#f4d03f", alpha=0.35, zorder=1, label="signal window")

    # The supplemented monoenergetic 511 keV line, drawn as a stem/arrow on top.
    line_top = table_p.max() * 4.0
    ax.annotate(
        "",
        xy=(511.0, line_top),
        xytext=(511.0, interp_p[0]),
        arrowprops=dict(arrowstyle="-|>", color="#1f6f8b", lw=2.4),
        zorder=5,
    )
    ax.text(
        511.0,
        line_top * 1.06,
        "supplemented\natmospheric 511 keV line",
        color="#1f6f8b",
        ha="center",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
    )

    ax.set_xlim(430, 590)
    ax.set_ylim(table_p.min() * 0.6, line_top * 2.2)
    ax.set_yscale("log")
    ax.set_xlabel("photon energy [keV]")
    ax.set_ylabel(r"gamma PDF [keV$^{-1}$]")
    ax.set_title("(a) spectral insertion at 511 keV", fontsize=10)
    ax.legend(fontsize=7.3, loc="lower left", framealpha=0.9)


def panel_angular(ax: plt.Axes) -> None:
    # Downward residual-atmosphere hemisphere, 0..90 deg.
    th_d = np.linspace(0.5, 90.0, 200)
    mu_d = np.cos(np.radians(th_d))
    k_d = slab_kernel(mu_d)
    mu_grid = np.linspace(1e-3, 1.0, 2000)
    trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
    a_norm = trapz(slab_kernel(mu_grid), mu_grid)
    i_down = PHI_DOWN / (2.0 * np.pi * a_norm) * k_d

    # Upward Earth-albedo hemisphere, 90..180 deg, limb darkening 1 + a*mu_u.
    th_u = np.linspace(90.0, 179.5, 200)
    mu_u = -np.cos(np.radians(th_u))
    i_up = PHI_UP / (2.0 * np.pi * (1.0 + ALBEDO_A / 2.0)) * (1.0 + ALBEDO_A * mu_u)

    ax.axvspan(0, 90, color="#aed6f1", alpha=0.30, zorder=0)
    ax.axvspan(90, 180, color="#f5b7b1", alpha=0.30, zorder=0)

    ax.plot(th_d, i_down, color="#2471a3", lw=2.2,
            label=r"downward residual atmosphere, slab kernel (0--90$^\circ$)")
    ax.plot(th_u, i_up, color="#a93226", lw=2.2,
            label=r"upward Earth albedo, limb darkening (90--180$^\circ$)")
    ax.axvline(90, color="0.5", ls=":", lw=1.0)

    ax.set_xlim(0, 180)
    ax.set_ylim(bottom=0, top=i_up.max() * 1.28)
    ax.set_xticks([0, 45, 90, 135, 180])
    ax.set_xlabel(r"zenith angle $\theta$ [deg]")
    ax.set_ylabel(r"line intensity $I(\theta)$ [ph cm$^{-2}$ s$^{-1}$ sr$^{-1}$]")
    ax.set_title("(b) 4$\\pi$ angular model of the added line", fontsize=10)
    ax.legend(fontsize=7.0, loc="upper left", framealpha=0.9)
    ax.annotate(
        r"$\Phi_{511}^{4\pi}=5.2\times10^{-2}$ ph cm$^{-2}$ s$^{-1}$"
        "\n" r"$r_{\rm down}=\Phi_{\rm down}/\Phi_{\rm up}\approx0.20$",
        xy=(0.05, 0.30), xycoords="axes fraction", fontsize=7.6,
        bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.9),
    )


def main() -> None:
    rows = read_excerpt()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    panel_spectrum(axes[0], rows)
    panel_angular(axes[1])
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200)
    fig.savefig(OUT.with_suffix(".svg"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
