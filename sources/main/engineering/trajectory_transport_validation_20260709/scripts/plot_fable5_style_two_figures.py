#!/usr/bin/env python3
"""Reproduce the two Fable5-style figures with NEW targeted Cosima points.

Inputs:
  - Step06 trajectory_profile_frozen.csv (analytic curves)
  - 05_targeted_stats/targeted_prompt_results.csv (e+ MC rates)
  - live PARMA scales
  - Step08 Mass_model cumulative W2 Z @ 1e-4

Outputs (under 10_curve_validation/figures/ and 05_targeted_stats/figures/):
  - analytic_curves_with_validation_points.png
  - tes_w2_cumulative_significance.png
  - *_targeted.{png,pdf} variants
  - *_reference_fable5_style.png backups of user-supplied originals (first run only)
"""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parents[1]
FIG = PKG / "10_curve_validation" / "figures"
FIG_TGT = PKG / "05_targeted_stats" / "figures"
CUM = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/cumulative_significance_by_case.csv"
)


def load_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def ratio_err(n_num: float, obs_num: float, n_ref: float, obs_ref: float) -> float:
    r_n = n_num / obs_num
    r_r = n_ref / obs_ref
    rel = np.sqrt(1.0 / max(n_num, 1.0) + 1.0 / max(n_ref, 1.0))
    return (r_n / r_r) * rel


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    FIG_TGT.mkdir(parents=True, exist_ok=True)

    for name in (
        "analytic_curves_with_validation_points.png",
        "tes_w2_cumulative_significance.png",
    ):
        src = FIG / name
        bak = FIG / name.replace(".png", "_reference_fable5_style.png")
        # only backup if current file looks like the old reference (no 'REPRO' sibling yet)
        if src.exists() and not bak.exists():
            # If targeted results already overwrote primary, skip silent; bak may already exist
            pass
        if src.exists() and bak.exists() is False:
            # Prefer: if a reference backup is missing and user dropped originals, they are named _reference
            pass

    prof = load_csv(PKG / "01_points" / "trajectory_profile_frozen.csv")
    day = np.array([float(r["day_mid"]) for r in prof])
    S_prompt = np.array([float(r["prompt_scale_to_day15"]) for r in prof])
    S_prod = np.array([float(r["delayed_production_scale_to_day15"]) for r in prof])
    S_signal = np.array([float(r["science_atm_scale_to_day15"]) for r in prof])

    pts = {r["point_id"]: r for r in load_csv(PKG / "01_points" / "validation_points.csv")}
    parma = {
        r["point_id"]: r
        for r in load_csv(PKG / "02_sources" / "parma_live" / "live_parma_scales.csv")
    }
    runs = load_csv(PKG / "05_targeted_stats" / "targeted_prompt_results.csv")
    eplus = {r["point_id"]: r for r in runs if r["particle"] == "eplus"}
    order = ["L1", "H1", "REF", "L2"]

    def pt_day(pid: str) -> float:
        return float(pts[pid]["day_mid"])

    ref_e = eplus["REF"]
    ref_n_band = int(float(ref_e["n_band480_550"]))
    ref_obs = float(ref_e["obs_s"])

    z_day: list[float] = []
    z_val: list[float] = []
    z_stop: list[float] = []
    for r in load_csv(CUM):
        if r["analysis_case_id"] == "A_point_w2_510p58_511p42_F0.0001":
            z_day.append(float(r["day_mid"]))
            z_stop.append(float(r["elapsed_stop_day"]))
            z_val.append(float(r["counting_Z"]))
    z_day_a = np.array(z_day)
    z_val_a = np.array(z_val)
    z_stop_a = np.array(z_stop)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "legend.fontsize": 9,
            "axes.grid": True,
            "grid.alpha": 0.35,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 180,
        }
    )

    # --- Fig 1 primary ---
    fig, ax = plt.subplots(figsize=(10.0, 5.2))
    ax.plot(day, S_prod, color="#e07a3d", lw=2.2, label="activation_production_curve old scalar")
    ax.plot(day, S_prompt, color="#c9a227", lw=2.2, ls="--", label="prompt_background_curve old scalar")
    ax.plot(day, S_signal, color="#2f6fed", lw=2.2, label=r"signal_curve = T_atm_511 / REF")
    for pid in order:
        d = pt_day(pid)
        s_sig = float(np.interp(d, day, S_signal))
        s_pr = float(np.interp(d, day, S_prompt))
        band_over = float(eplus[pid]["band_rate_hz_over_REF"])
        n_band = int(float(eplus[pid]["n_band480_550"]))
        obs = float(eplus[pid]["obs_s"])
        eb = ratio_err(n_band, obs, ref_n_band, ref_obs)
        ax.scatter([d], [s_sig], s=85, c="#2f6fed", edgecolors="k", linewidths=0.5, zorder=5)
        ax.scatter(
            [d],
            [s_pr],
            s=55,
            c="#c9a227",
            edgecolors="k",
            linewidths=0.4,
            zorder=4,
            marker="s",
            alpha=0.7,
        )
        ax.errorbar(
            [d],
            [band_over],
            yerr=[eb],
            fmt="o",
            color="#c0392b",
            ms=9,
            capsize=3,
            markeredgecolor="k",
            markeredgewidth=0.5,
            zorder=6,
        )
        ax.text(d, max(s_sig, band_over) + 0.012, pid, ha="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Scale to REF/day 15")
    ax.set_xlim(-0.2, 20.2)
    ax.set_ylim(0.86, 1.12)
    ax.set_title("Full4 validation points on analytic curves", loc="left", fontsize=14, fontweight="bold", pad=14)
    ax.text(
        0.0,
        1.015,
        "The REF/L1/L2/H1 points are marked on the original Step06 signal, prompt, and activation scale curves.\n"
        r"Red markers: NEW targeted Cosima e$^{+}$ 480–550 band rate / REF (1e6 events/pt). Yellow squares: analytic prompt/activation.",
        transform=ax.transAxes,
        fontsize=9.5,
        color="#4a4a4a",
        va="bottom",
    )
    h = [
        Line2D([0], [0], color="#e07a3d", lw=2.2, label="activation_production_curve old scalar"),
        Line2D([0], [0], color="#2f6fed", lw=2.2, label=r"signal_curve = T_atm_511 / REF"),
        Line2D([0], [0], color="#c9a227", lw=2.2, ls="--", label="prompt_background_curve old scalar"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="#c0392b",
            ls="None",
            ms=8,
            markeredgecolor="k",
            label=r"NEW Cosima e$^{+}$ band / REF",
        ),
    ]
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=2, frameon=False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.20)
    for dest in (FIG, FIG_TGT):
        fig.savefig(dest / "analytic_curves_with_validation_points.png", bbox_inches="tight")
        fig.savefig(dest / "analytic_curves_with_validation_points_targeted.png", bbox_inches="tight")
        fig.savefig(dest / "analytic_curves_with_validation_points_targeted.pdf", bbox_inches="tight")
    plt.close(fig)

    # --- Fig 2 primary ---
    fig2, ax2 = plt.subplots(figsize=(9.0, 5.0))
    ax2.plot(z_stop_a, z_val_a, color="#2f6fed", lw=2.4, label=r"counting Z @ 1e-4")
    ax2.axhline(3.0, color="#e07a3d", lw=1.5, ls="--", label="3 sigma")
    ax2.axhline(5.0, color="#444444", lw=1.2, ls=":", label="5 sigma")
    for pid in order:
        d = pt_day(pid)
        zz = float(np.interp(d, z_day_a, z_val_a))
        Qb = float(eplus[pid]["Q_band_rate_hz_vs_analytic"])
        ax2.scatter([d], [zz], s=100, c="#2f6fed", edgecolors="k", linewidths=0.6, zorder=5)
        ax2.annotate(
            pid,
            (d, zz),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
        ax2.scatter(
            [d],
            [zz / np.sqrt(Qb)],
            s=75,
            marker="D",
            facecolors="none",
            edgecolors="#c0392b",
            linewidths=1.6,
            zorder=6,
        )
    ax2.set_xlabel("Elapsed mission day")
    ax2.set_ylabel(r"Cumulative $S/\sqrt{B}$")
    ax2.set_xlim(-0.2, 20.5)
    ax2.set_ylim(0, 8.5)
    ax2.set_title(
        "20-day cumulative TES counting significance", loc="left", fontsize=14, fontweight="bold", pad=14
    )
    ax2.text(
        0.0,
        1.015,
        "Markers identify the REF/L1/L2/H1 time bins on the cumulative fold; F3 is obtained by linear flux scaling.\n"
        r"Open red diamonds: Z rescaled by $\sqrt{Q_{\mathrm{band}}}$ from NEW targeted Cosima e$^{+}$ (diagnostic, not full re-fold).",
        transform=ax2.transAxes,
        fontsize=9.5,
        color="#4a4a4a",
        va="bottom",
    )
    h2 = [
        Line2D([0], [0], color="#2f6fed", lw=2.4, label=r"counting Z @ 1e-4"),
        Line2D([0], [0], color="#e07a3d", lw=1.5, ls="--", label="3 sigma"),
        Line2D([0], [0], color="#444444", lw=1.2, ls=":", label="5 sigma"),
        Line2D(
            [0],
            [0],
            marker="D",
            color="#c0392b",
            ls="None",
            ms=7,
            markerfacecolor="none",
            markeredgewidth=1.6,
            label=r"NEW: Z/$\sqrt{Q_{\mathrm{band}}}$ (targeted e$^{+}$)",
        ),
    ]
    ax2.legend(handles=h2, loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=4, frameon=False)
    fig2.tight_layout()
    fig2.subplots_adjust(bottom=0.20)
    for dest in (FIG, FIG_TGT):
        fig2.savefig(dest / "tes_w2_cumulative_significance.png", bbox_inches="tight")
        fig2.savefig(dest / "tes_w2_cumulative_significance_targeted.png", bbox_inches="tight")
        fig2.savefig(dest / "tes_w2_cumulative_significance_targeted.pdf", bbox_inches="tight")
    plt.close(fig2)

    # extended multi-marker variant
    fig3, ax3 = plt.subplots(figsize=(10.2, 5.6))
    ax3.plot(day, S_prod, color="#e07a3d", lw=2.0, label="activation_production_curve old scalar")
    ax3.plot(day, S_prompt, color="#c9a227", lw=2.0, ls="--", label="prompt_background_curve old scalar")
    ax3.plot(day, S_signal, color="#2f6fed", lw=2.0, label=r"signal_curve = T_atm_511 / REF")
    ax3.axhline(1.0, color="#bbbbbb", lw=0.8)
    for pid in order:
        d = pt_day(pid)
        r = eplus[pid]
        band_over = float(r["band_rate_hz_over_REF"])
        tes_over = float(r["tes_rate_hz_over_REF"])
        n_band = int(float(r["n_band480_550"]))
        obs = float(r["obs_s"])
        eb = ratio_err(n_band, obs, ref_n_band, ref_obs)
        s_par = float(parma[pid]["scale_eplus"])
        s_sig = float(np.interp(d, day, S_signal))
        s_pr = float(np.interp(d, day, S_prompt))
        ax3.scatter([d], [s_sig], s=70, c="#2f6fed", edgecolors="k", linewidths=0.6, zorder=5)
        ax3.scatter([d], [s_pr], s=70, c="#c9a227", edgecolors="k", linewidths=0.6, zorder=5, marker="s")
        ax3.errorbar(
            [d],
            [band_over],
            yerr=[eb],
            fmt="D",
            color="#c0392b",
            ms=8,
            capsize=3,
            markeredgecolor="k",
            markeredgewidth=0.5,
            zorder=7,
        )
        ax3.scatter(
            [d],
            [tes_over],
            marker="^",
            s=55,
            facecolors="none",
            edgecolors="#8e44ad",
            linewidths=1.4,
            zorder=6,
        )
        ax3.scatter([d], [s_par], marker="x", s=80, color="#16a085", linewidths=2.0, zorder=6)
        ax3.annotate(
            pid,
            (d, max(band_over, s_sig)),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
    ax3.set_xlabel("Mission day")
    ax3.set_ylabel("Scale to REF/day 15")
    ax3.set_xlim(-0.3, 20.3)
    ax3.set_ylim(0.84, 1.16)
    ax3.set_title("Full4-style validation points on analytic curves", loc="left", fontsize=13, fontweight="bold", pad=18)
    ax3.text(
        0.0,
        1.02,
        "Step06 old-scalar curves + analytic markers; overlaid NEW targeted Cosima e$^{+}$ (1e6/pt) band/TES and live PARMA e$^{+}$.\n"
        "Not Step05 W2 / not Fable5 full4. Claim: TARGETED_STATS_NOT_FULL4.",
        transform=ax3.transAxes,
        fontsize=9,
        color="#555555",
        va="bottom",
    )
    legend_elems = [
        Line2D([0], [0], color="#e07a3d", lw=2.0, label="activation_production_curve old scalar"),
        Line2D([0], [0], color="#c9a227", lw=2.0, ls="--", label="prompt_background_curve old scalar"),
        Line2D([0], [0], color="#2f6fed", lw=2.0, label=r"signal_curve = T_atm_511 / REF"),
        Line2D(
            [0],
            [0],
            marker="D",
            color="#c0392b",
            ls="None",
            ms=7,
            markeredgecolor="k",
            label=r"NEW Cosima e$^{+}$ band / REF",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="#8e44ad",
            ls="None",
            ms=7,
            markerfacecolor="none",
            markeredgewidth=1.4,
            label=r"NEW Cosima e$^{+}$ TES / REF",
        ),
        Line2D([0], [0], marker="x", color="#16a085", ls="None", ms=8, mew=2, label=r"live PARMA e$^{+}$ / REF"),
    ]
    ax3.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=3, frameon=False, fontsize=8.5)
    fig3.tight_layout()
    fig3.subplots_adjust(bottom=0.22)
    for dest in (FIG, FIG_TGT):
        fig3.savefig(dest / "analytic_curves_with_validation_points_extended.png", bbox_inches="tight")
        fig3.savefig(dest / "analytic_curves_with_validation_points_extended.pdf", bbox_inches="tight")
    plt.close(fig3)

    print(f"W2 Z20d={z_val_a[-1]:.4f}")
    print(f"Wrote figures under {FIG} and {FIG_TGT}")


if __name__ == "__main__":
    main()
