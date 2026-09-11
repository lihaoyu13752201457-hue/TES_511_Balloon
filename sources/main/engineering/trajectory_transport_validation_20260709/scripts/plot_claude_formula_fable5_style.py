#!/usr/bin/env python3
"""Draw Fable5-style trajectory figures for the Claude corrected formula audit.

The style intentionally follows the two 2026-07-02 reference figures kept under
10_curve_validation/figures/*_reference_fable5_style.png.  The plotted evidence
uses the current targeted prompt extraction plus the recovered Claude formula
mapping in 11_analytic_agreement_20260709.
"""
from __future__ import annotations

import csv
import math
import os
import subprocess
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parents[1]
OUT11 = PKG / "11_analytic_agreement_20260709" / "figures"
OUT10 = PKG / "10_curve_validation" / "figures"
TARGETED = PKG / "05_targeted_stats" / "targeted_prompt_results.csv"
CURVE_CACHE = PKG / "11_analytic_agreement_20260709" / "claude_source_response_curve_by_time.csv"
CUM = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_Mass_model_511_fullstat_v1"
    / "cumulative_significance_by_case.csv"
)
PARMA_EXE = Path(
    "/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/external/expacs_parma/phase2_parma_grid_driver"
)
PARMA_CWD = PARMA_EXE.parent / "parma_cpp"
MU_W = 0.1
PARTICLES = ["eplus", "n", "gamma"]
CURVE_METHOD = "parma_discrete_particle_totals_audit_v1"

os.environ.setdefault("MPLCONFIGDIR", str(OUT11 / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


POINT_ORDER = ["L1", "H1", "REF", "L2"]
POINT_COLOR = "#5678c4"
OLD_PROMPT = "#b8a12a"
OLD_ACT = "#d27a51"
SIGNAL = "#5276c6"
CORRECTED = "#20865a"
MC = "#c43c35"
GRID = "#d8dde8"
INK = "#202432"
MUTED = "#70778c"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_parma(lat: float, lon: float, alt: float) -> tuple[dict[str, float], list[dict[str, str]]]:
    cmd = [str(PARMA_EXE), "2025", "8", "31", str(lat), str(lon), str(alt), "10.0"]
    proc = subprocess.run(
        cmd,
        cwd=str(PARMA_CWD),
        text=True,
        capture_output=True,
        check=True,
    )
    lines = [line for line in proc.stdout.splitlines() if line]
    start = next(i for i, line in enumerate(lines) if line.startswith("particle,"))
    meta_line = next(line for line in lines if line.startswith("META,"))
    _, w, rc, depth = meta_line.split(",")
    rows = list(csv.DictReader(lines[start:]))
    return {"W": float(w), "Rc": float(rc), "depth": float(depth)}, rows


def particle_totals_for_audit(rows: list[dict[str, str]]) -> dict[str, float]:
    """Match 02_sources/parma_live/live_parma_scales.csv provenance.

    The current agreement audit was built from run_escalation_pipeline.py
    particle_totals(), which sums the PARMA differential table on the fixed
    grid and applies the angle-bin solid angle.  Use the same discrete proxy
    here so the continuous curve and the validation-point expected_ratio values
    are the same analytic object.
    """
    d_omega = 2 * math.pi * MU_W
    totals = {particle: 0.0 for particle in PARTICLES}
    for row in rows:
        particle = row["particle"]
        if particle not in totals:
            continue
        totals[particle] += max(float(row["differential_flux_cm2_s_sr_MeV"]), 0.0) * d_omega
    return totals


def load_ref_band_response_weights() -> dict[str, float]:
    weights = {
        row["particle"]: float(row["band_rate_hz"])
        for row in load_csv(TARGETED)
        if row["point_id"] == "REF" and row["particle"] in PARTICLES
    }
    missing = [particle for particle in PARTICLES if particle not in weights]
    if missing:
        raise RuntimeError(f"Missing REF band response weights for {missing}")
    return weights


def build_source_response_curve() -> list[dict[str, str]]:
    if CURVE_CACHE.exists():
        rows = load_csv(CURVE_CACHE)
        required = {"curve_method", "corrected_band_family_response", "scale_eplus", "scale_n", "scale_gamma"}
        if rows and required <= set(rows[0]) and rows[0]["curve_method"] == CURVE_METHOD:
            return rows

    profile = load_csv(PKG / "01_points" / "trajectory_profile_frozen.csv")
    points = {r["point_id"]: r for r in load_csv(PKG / "01_points" / "validation_points.csv")}
    ref_time_bin = int(points["REF"]["time_bin_id"])
    weights = load_ref_band_response_weights()
    weight_sum = sum(weights.values())

    flux_by_bin: dict[int, dict[str, float]] = {}
    meta_by_bin: dict[int, dict[str, float]] = {}
    for idx, row in enumerate(profile, start=1):
        time_bin = int(row["time_bin_id"])
        if idx == 1 or idx % 10 == 0 or idx == len(profile):
            print(f"PARMA source-response curve {idx}/{len(profile)} day={float(row['day_mid']):.2f}", flush=True)
        meta, parma_rows = run_parma(
            float(row["latitude_deg"]),
            float(row["longitude_deg"]),
            float(row["altitude_km"]),
        )
        meta_by_bin[time_bin] = meta
        flux_by_bin[time_bin] = particle_totals_for_audit(parma_rows)

    ref_flux = flux_by_bin[ref_time_bin]
    out_rows: list[dict[str, object]] = []
    for row in profile:
        time_bin = int(row["time_bin_id"])
        scales = {
            particle: flux_by_bin[time_bin][particle] / ref_flux[particle]
            for particle in PARTICLES
        }
        corrected = sum(weights[p] * scales[p] for p in PARTICLES) / weight_sum
        out_rows.append(
            {
                "time_bin_id": row["time_bin_id"],
                "curve_method": CURVE_METHOD,
                "day_mid": row["day_mid"],
                "altitude_km": row["altitude_km"],
                "latitude_deg": row["latitude_deg"],
                "longitude_deg": row["longitude_deg"],
                "Rc_GV_profile": row["Rc_GV"],
                "depth_g_cm2_profile": row["depth_g_cm2"],
                "Rc_GV_parma": f"{meta_by_bin[time_bin]['Rc']:.12g}",
                "depth_g_cm2_parma": f"{meta_by_bin[time_bin]['depth']:.12g}",
                "flux_eplus": f"{flux_by_bin[time_bin]['eplus']:.12e}",
                "flux_n": f"{flux_by_bin[time_bin]['n']:.12e}",
                "flux_gamma": f"{flux_by_bin[time_bin]['gamma']:.12e}",
                "scale_eplus": f"{scales['eplus']:.12g}",
                "scale_n": f"{scales['n']:.12g}",
                "scale_gamma": f"{scales['gamma']:.12g}",
                "weight_ref_band_eplus_hz": f"{weights['eplus']:.12g}",
                "weight_ref_band_n_hz": f"{weights['n']:.12g}",
                "weight_ref_band_gamma_hz": f"{weights['gamma']:.12g}",
                "corrected_band_family_response": f"{corrected:.12g}",
                "old_prompt_scale": row["prompt_scale_to_day15"],
                "signal_scale": row["science_atm_scale_to_day15"],
            }
        )

    write_csv(
        CURVE_CACHE,
        out_rows,
        [
            "time_bin_id",
            "curve_method",
            "day_mid",
            "altitude_km",
            "latitude_deg",
            "longitude_deg",
            "Rc_GV_profile",
            "depth_g_cm2_profile",
            "Rc_GV_parma",
            "depth_g_cm2_parma",
            "flux_eplus",
            "flux_n",
            "flux_gamma",
            "scale_eplus",
            "scale_n",
            "scale_gamma",
            "weight_ref_band_eplus_hz",
            "weight_ref_band_n_hz",
            "weight_ref_band_gamma_hz",
            "corrected_band_family_response",
            "old_prompt_scale",
            "signal_scale",
        ],
    )
    return load_csv(CURVE_CACHE)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "#fbfcff",
            "axes.facecolor": "white",
            "axes.edgecolor": "#ccd3e2",
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.alpha": 0.85,
            "grid.linewidth": 1.0,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.labelsize": 15,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "legend.fontsize": 12,
            "savefig.dpi": 180,
        }
    )


def setup_title(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.075, 0.945, title, fontsize=22, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.075, 0.905, subtitle, fontsize=14.5, color=MUTED, ha="left", va="top")


def despine(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_all(fig: plt.Figure, stem: str) -> None:
    for out in (OUT11, OUT10):
        out.mkdir(parents=True, exist_ok=True)
        fig.savefig(out / f"{stem}.png", bbox_inches="tight")
        fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")


def point_days(points: dict[str, dict[str, str]]) -> dict[str, float]:
    return {pid: float(points[pid]["day_mid"]) for pid in POINT_ORDER}


def load_agreement_rows() -> dict[tuple[str, str], dict[str, str]]:
    rows = load_csv(PKG / "11_analytic_agreement_20260709" / "analytic_agreement_rows.csv")
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if (
            row["scope"] == "combined_species"
            and row["metric"] == "band480_550"
            and row["model"] in {"step06_prompt_scalar", "live_parma_species_weighted"}
        ):
            out[(row["point_id"], row["model"])] = row
    return out


def plot_curves() -> None:
    profile = load_csv(PKG / "01_points" / "trajectory_profile_frozen.csv")
    source_curve = build_source_response_curve()
    points = {r["point_id"]: r for r in load_csv(PKG / "01_points" / "validation_points.csv")}
    agreement = load_agreement_rows()

    day = np.array([float(r["day_mid"]) for r in profile])
    source_day = np.array([float(r["day_mid"]) for r in source_curve])
    corrected_curve = np.array([float(r["corrected_band_family_response"]) for r in source_curve])
    signal_curve = np.array([float(r["science_atm_scale_to_day15"]) for r in profile])
    prompt_old = np.array([float(r["prompt_scale_to_day15"]) for r in profile])
    act_old = np.array([float(r["delayed_production_scale_to_day15"]) for r in profile])
    pday = point_days(points)

    corr_x = []
    corr_y = []
    mc_y = []
    mc_err = []
    old_y = []
    q_labels = {}
    for pid in POINT_ORDER:
        corr_x.append(pday[pid])
        if pid == "REF":
            corr_y.append(1.0)
            mc_y.append(1.0)
            mc_err.append(0.0)
            old_y.append(1.0)
            q_labels[pid] = "1.00"
            continue
        live = agreement[(pid, "live_parma_species_weighted")]
        old = agreement[(pid, "step06_prompt_scalar")]
        corr_y.append(float(live["expected_ratio"]))
        mc_y.append(float(live["mc_ratio_to_REF"]))
        mc_err.append(float(live["sigma_ratio"]))
        old_y.append(float(old["expected_ratio"]))
        q_labels[pid] = f"{float(live['Q']):.3f}"

    fig, ax = plt.subplots(figsize=(15.5, 8.8))
    setup_title(
        fig,
        "Validation points on analytic curves",
        "Same layout as the 2026-07-02 figure; red MC points overlap the Claude/PARMA source-response prediction.",
    )
    fig.subplots_adjust(top=0.80, bottom=0.19, left=0.08, right=0.98)

    ax.plot(day, act_old, color=OLD_ACT, lw=2.6, label="activation_production_curve old scalar")
    ax.plot(day, prompt_old, color=OLD_PROMPT, lw=2.6, ls="--", label="prompt_background_curve old scalar")
    ax.plot(day, signal_curve, color=SIGNAL, lw=3.0, label="signal_curve = T_atm_511 / REF")
    ax.plot(
        source_day,
        corrected_curve,
        color=CORRECTED,
        lw=3.0,
        ls="-",
        label="Claude/PARMA prompt source-response",
    )

    for pid in POINT_ORDER:
        x = pday[pid]
        ax.axvline(x, color="#e3e7f0", lw=1.3, ls=":", zorder=0)
        ax.text(x, 1.099, pid, ha="center", va="bottom", fontsize=13, color=INK)

    ax.scatter(corr_x, [float(np.interp(x, day, signal_curve)) for x in corr_x], s=120, color=SIGNAL, edgecolor=INK, linewidth=1.4, zorder=6)
    ax.scatter(corr_x, old_y, s=115, marker="s", color=OLD_PROMPT, edgecolor=INK, linewidth=1.4, zorder=7)
    ax.scatter(corr_x, corr_y, s=150, marker="o", color=CORRECTED, edgecolor=INK, linewidth=1.4, zorder=8)
    ax.errorbar(
        corr_x,
        mc_y,
        yerr=mc_err,
        fmt="D",
        ms=8.5,
        mfc="white",
        mec=MC,
        mew=2.0,
        ecolor=MC,
        elinewidth=1.8,
        capsize=4,
        zorder=9,
        label="targeted MC 480-550 band / REF",
    )

    for x, y, pid in zip(corr_x, mc_y, POINT_ORDER):
        if y > 1.04:
            ax.text(x, y - 0.020, f"Q={q_labels[pid]}", color=CORRECTED, fontsize=10.5, ha="center", va="top")
        else:
            ax.text(x, y + 0.018, f"Q={q_labels[pid]}", color=CORRECTED, fontsize=10.5, ha="center", va="bottom")

    ax.set_xlim(-1.0, 21.0)
    ax.set_ylim(0.845, 1.165)
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Scale to REF/day 15")
    ax.set_yticks([0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15])
    despine(ax)

    legend = [
        Line2D([0], [0], color=OLD_ACT, lw=2.6, label="activation_production_curve old scalar"),
        Line2D([0], [0], color=OLD_PROMPT, lw=2.6, ls="--", label="prompt_background_curve old scalar"),
        Line2D([0], [0], color=SIGNAL, lw=3.0, label="signal_curve = T_atm_511 / REF"),
        Line2D([0], [0], color=CORRECTED, lw=3.0, marker="o", ms=7, label="Claude/PARMA prompt source-response"),
        Line2D([0], [0], color=MC, marker="D", lw=0, ms=8, markerfacecolor="white", markeredgewidth=2.0, label="targeted MC band / REF"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.26), ncol=3, frameon=False)
    save_all(fig, "analytic_curves_with_claude_source_response")
    plt.close(fig)


def load_z_curve() -> tuple[np.ndarray, np.ndarray]:
    rows = [
        r
        for r in load_csv(CUM)
        if r["analysis_case_id"] == "A_point_w2_510p58_511p42_F0.0001"
    ]
    if not rows:
        raise RuntimeError("Missing W2 F0.0001 cumulative significance rows")
    return (
        np.array([float(r["elapsed_stop_day"]) for r in rows]),
        np.array([float(r["counting_Z"]) for r in rows]),
    )


def plot_cumulative() -> None:
    points = {r["point_id"]: r for r in load_csv(PKG / "01_points" / "validation_points.csv")}
    agreement = load_agreement_rows()
    xz, z = load_z_curve()
    pday = point_days(points)

    fig, ax = plt.subplots(figsize=(14.0, 8.1))
    setup_title(
        fig,
        "20-day cumulative TES counting significance",
        "Markers identify the REF/L1/L2/H1 time bins; source-response agreement at these bins has max |z| = 0.51.",
    )
    fig.subplots_adjust(top=0.80, bottom=0.18, left=0.08, right=0.98)

    ax.plot(xz, z, color=SIGNAL, lw=3.2, label="counting Z @ 1e-4")
    ax.axhline(3.0, color=OLD_ACT, lw=1.7, ls="--", label="3 sigma")
    ax.axhline(5.0, color="#4e5565", lw=1.7, ls=":", label="5 sigma")

    q_text = {"REF": "Q=1.00"}
    for pid in ("L1", "H1", "L2"):
        q_text[pid] = f"Q={float(agreement[(pid, 'live_parma_species_weighted')]['Q']):.3f}"

    for pid in POINT_ORDER:
        x = pday[pid]
        zz = float(np.interp(x, xz, z))
        ax.scatter([x], [zz], s=145, color=POINT_COLOR, edgecolor=INK, linewidth=1.5, zorder=5)
        ax.text(x, zz + 0.18, pid, ha="center", va="bottom", fontsize=12, color=MUTED)
        ax.text(x, zz - 0.33, q_text[pid], ha="center", va="top", fontsize=9.8, color=CORRECTED)

    ax.set_xlim(-0.9, 21.0)
    ax.set_ylim(0.25, 8.15)
    ax.set_xlabel("Elapsed mission day")
    ax.set_ylabel("Cumulative S / sqrt(B)")
    ax.set_yticks(range(1, 9))
    despine(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False)

    save_all(fig, "tes_w2_cumulative_significance_claude_source_response")
    plt.close(fig)


def main() -> None:
    OUT11.mkdir(parents=True, exist_ok=True)
    OUT10.mkdir(parents=True, exist_ok=True)
    apply_style()
    plot_curves()
    plot_cumulative()
    print(f"Wrote Claude/Fable5-style figures under {OUT11} and {OUT10}")


if __name__ == "__main__":
    main()
