#!/usr/bin/env python3
"""Plot analytic Step06 prompt curve with Cosima multi-point validation overlays.

Outputs under 10_curve_validation/figures/:
  - analytic_curve_vs_mc_points.{png,pdf}     main 2-panel overlay + Q residual
  - analytic_curve_mc_diagnostics.{png,pdf}   4-panel diagnostics
  - analytic_curve_overlay_paperstyle.{png,pdf} clean single-panel insert
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / "10_curve_validation" / "figures"
OUT_TGT = PKG / "05_targeted_stats" / "figures"


def load_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def ratio_err(n_num: float, obs_num: float, n_ref: float, obs_ref: float) -> float:
    if n_ref <= 0 or obs_num <= 0 or obs_ref <= 0:
        return float("nan")
    r_n = n_num / obs_num
    r_r = n_ref / obs_ref
    rel = np.sqrt(1.0 / max(n_num, 1.0) + 1.0 / max(n_ref, 1.0))
    return (r_n / r_r) * rel


def resolve_results_csv() -> tuple[Path, str]:
    """Prefer targeted results when complete; else smoke escalation CSV."""
    tgt = PKG / "05_targeted_stats" / "targeted_prompt_results.csv"
    smoke = PKG / "04_prompt_smoke" / "escalation_prompt_results.csv"
    if tgt.exists():
        rows = load_csv(tgt)
        eplus = [r for r in rows if r["particle"] == "eplus"]
        ok = all(
            r.get("rc") in ("0", 0) or (r.get("obs_s") and r.get("gen"))
            for r in eplus
        ) and len(eplus) >= 4
        if ok:
            return tgt, "targeted"
    return smoke, "smoke"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_TGT.mkdir(parents=True, exist_ok=True)

    prof = load_csv(PKG / "01_points" / "trajectory_profile_frozen.csv")
    day = np.array([float(r["day_mid"]) for r in prof])
    S_prompt = np.array([float(r["prompt_scale_to_day15"]) for r in prof])
    alt = np.array([float(r["altitude_km"]) for r in prof])

    pts = {r["point_id"]: r for r in load_csv(PKG / "01_points" / "validation_points.csv")}
    parma = {
        r["point_id"]: r
        for r in load_csv(PKG / "02_sources" / "parma_live" / "live_parma_scales.csv")
    }
    results_path, results_tag = resolve_results_csv()
    runs = load_csv(results_path)
    eplus = {r["point_id"]: r for r in runs if r["particle"] == "eplus"}
    claim_note = (
        "Claim: TARGETED_STATS_NOT_FULL4  ·  e$^{+}$ 1e6/pt  ·  TES proxy det 1–6  ·  not Step05 W2"
        if results_tag == "targeted"
        else "Claim: MEDIUM_SMOKE_NOT_FULL4  ·  e$^{+}$ 50k/pt  ·  TES proxy det 1–6  ·  not Step05 W2"
    )
    title_tag = "targeted e$^{+}$ 1e6" if results_tag == "targeted" else "smoke e$^{+}$ 50k"
    print(f"Using results: {results_path} ({results_tag})")

    order = ["L1", "H1", "REF", "L2"]
    colors = {"L1": "#d62728", "H1": "#1f77b4", "REF": "#2ca02c", "L2": "#ff7f0e"}
    markers = {"L1": "o", "H1": "s", "REF": "D", "L2": "^"}

    def pt_day(pid: str) -> float:
        return float(pts[pid]["day_mid"])

    def pt_S(pid: str) -> float:
        return float(pts[pid]["analytic_prompt_scale_to_day15"])

    ref_e = eplus["REF"]
    ref_n_band = int(float(ref_e["n_band480_550"]))
    ref_n_tes = int(float(ref_e["n_tes"]))
    ref_obs = float(ref_e["obs_s"])

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 11,
            "legend.fontsize": 8.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.9,
            "figure.dpi": 140,
            "savefig.dpi": 200,
            "axes.grid": True,
            "grid.alpha": 0.28,
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
        }
    )

    # ----- Figure 1: main overlay -----
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(9.2, 7.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.12},
    )

    ax = axes[0]
    ax_alt = ax.twinx()
    ax_alt.fill_between(day, alt, alpha=0.10, color="#7f7f7f", zorder=0)
    ax_alt.plot(day, alt, color="#9a9a9a", lw=0.8, alpha=0.55, zorder=1)
    ax_alt.set_ylabel("Altitude [km]", color="#666666", fontsize=9)
    ax_alt.tick_params(axis="y", labelcolor="#666666", labelsize=8)
    ax_alt.set_ylim(35.0, 43.5)
    ax_alt.grid(False)

    ax.plot(
        day,
        S_prompt,
        color="#111111",
        lw=2.0,
        label=r"Analytic $S_{\mathrm{prompt}}(t)$ (Step06 fold)",
        zorder=3,
    )
    ax.axhline(1.0, color="#444444", lw=0.7, ls=":", zorder=2)

    for pid in order:
        d = pt_day(pid)
        s_par = float(parma[pid]["scale_eplus"])
        ax.scatter(
            [d],
            [s_par],
            marker="x",
            s=90,
            linewidths=2.0,
            color=colors[pid],
            zorder=5,
        )
        ax.axvline(d, color=colors[pid], lw=0.5, alpha=0.25, zorder=1)

        r = eplus[pid]
        band_over = float(r["band_rate_hz_over_REF"])
        tes_over = float(r["tes_rate_hz_over_REF"])
        gen_over = float(r["gen_rate_hz_over_REF"])
        n_band = int(float(r["n_band480_550"]))
        obs = float(r["obs_s"])
        eb = ratio_err(n_band, obs, ref_n_band, ref_obs)

        ax.errorbar(
            [d],
            [band_over],
            yerr=[eb],
            fmt=markers[pid],
            color=colors[pid],
            ms=9,
            capsize=3,
            elinewidth=1.1,
            markeredgecolor="k",
            markeredgewidth=0.5,
            zorder=6,
        )
        ax.scatter(
            [d],
            [tes_over],
            marker=markers[pid],
            s=36,
            facecolors="none",
            edgecolors=colors[pid],
            linewidths=1.3,
            zorder=6,
        )
        ax.scatter(
            [d],
            [gen_over],
            marker="_",
            s=120,
            color=colors[pid],
            linewidths=1.6,
            zorder=6,
        )
        ax.text(
            d,
            band_over + 0.022,
            pid,
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color=colors[pid],
            zorder=7,
        )

    ax.set_ylabel(r"Rate scale relative to day-15 REF")
    ax.set_ylim(0.82, 1.22)
    ax.set_title(
        rf"Prompt trajectory: analytic curve vs Cosima multi-point ({title_tag})",
        loc="left",
        pad=8,
    )
    legend_elems = [
        Line2D([0], [0], color="#111111", lw=2.0, label=r"Analytic $S_{\mathrm{prompt}}(t)$"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="k",
            ls="None",
            ms=8,
            markeredgecolor="k",
            label=r"MC e$^{+}$ band 480–550 / REF",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="k",
            ls="None",
            ms=7,
            markerfacecolor="none",
            markeredgewidth=1.3,
            label=r"MC e$^{+}$ TES-hit / REF",
        ),
        Line2D(
            [0],
            [0],
            marker="_",
            color="k",
            ls="None",
            ms=12,
            mew=2,
            label=r"MC e$^{+}$ gen-rate / REF",
        ),
        Line2D(
            [0],
            [0],
            marker="x",
            color="k",
            ls="None",
            ms=8,
            mew=2,
            label=r"Live PARMA e$^{+}$ flux scale",
        ),
    ]
    ax.legend(handles=legend_elems, loc="upper right", framealpha=0.92, borderpad=0.5)
    ax.text(
        0.01,
        0.02,
        claim_note,
        transform=ax.transAxes,
        fontsize=7.5,
        color="#444444",
        va="bottom",
    )

    ax2 = axes[1]
    ax2.axhline(1.0, color="#111111", lw=1.2, zorder=2)
    ax2.fill_between([0, 20], 0.85, 1.15, color="#2ca02c", alpha=0.08, zorder=0)
    ax2.axhline(0.85, color="#2ca02c", lw=0.6, ls="--", alpha=0.5)
    ax2.axhline(1.15, color="#2ca02c", lw=0.6, ls="--", alpha=0.5)

    for pid in order:
        d = pt_day(pid)
        r = eplus[pid]
        Qb_a = float(r["Q_band_rate_hz_vs_analytic"])
        Qb_p = float(r["Q_band_rate_hz_vs_live_parma"])
        n_band = int(float(r["n_band480_550"]))
        obs = float(r["obs_s"])
        eb = ratio_err(n_band, obs, ref_n_band, ref_obs) / pt_S(pid)
        ax2.errorbar(
            [d - 0.18],
            [Qb_a],
            yerr=[eb],
            fmt=markers[pid],
            color=colors[pid],
            ms=8,
            capsize=2.5,
            markeredgecolor="k",
            markeredgewidth=0.4,
            zorder=5,
        )
        ax2.scatter(
            [d + 0.18],
            [Qb_p],
            marker=markers[pid],
            s=70,
            facecolors="none",
            edgecolors=colors[pid],
            linewidths=1.5,
            zorder=5,
        )
        ax2.text(
            d,
            max(Qb_a, Qb_p) + 0.025,
            pid,
            ha="center",
            fontsize=8,
            color=colors[pid],
            fontweight="bold",
        )

    ax2.set_xlabel("Mission day")
    ax2.set_ylabel(r"$Q = (R^{\mathrm{MC}}/R^{\mathrm{REF}})\,/\,S$")
    ax2.set_xlim(-0.3, 20.3)
    ax2.set_ylim(0.78, 1.22)
    ax2.set_xticks([0, 5, 10, 15, 20])
    leg2 = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="k",
            ls="None",
            ms=7,
            markeredgecolor="k",
            label=r"$Q_{\mathrm{band}}$ vs analytic $S$",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="k",
            ls="None",
            ms=7,
            markerfacecolor="none",
            markeredgewidth=1.4,
            label=r"$Q_{\mathrm{band}}$ vs live PARMA e$^{+}$",
        ),
        Line2D([0], [0], color="#2ca02c", lw=6, alpha=0.25, label="±15% guide"),
    ]
    ax2.legend(handles=leg2, loc="lower left", framealpha=0.92, ncol=3)
    ax2.set_title(
        r"e$^{+}$ band residual $Q$ (filled = vs analytic; open = vs live PARMA)",
        loc="left",
        pad=6,
    )

    fig.suptitle(
        f"Trajectory transport validation — analytic curve + Cosima points ({results_tag}, 2026-07-09)",
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )
    fig.subplots_adjust(left=0.09, right=0.93, top=0.93, bottom=0.08, hspace=0.18)
    for dest in (OUT, OUT_TGT):
        for ext in ("png", "pdf"):
            fig.savefig(dest / f"analytic_curve_vs_mc_points.{ext}", bbox_inches="tight")
    plt.close(fig)

    # ----- Figure 2: diagnostics -----
    fig2, axes2 = plt.subplots(
        2, 2, figsize=(10.5, 7.8), gridspec_kw={"hspace": 0.35, "wspace": 0.30}
    )
    species_color = {"eplus": "#e41a1c", "n": "#377eb8", "gamma": "#4daf4a"}

    ax = axes2[0, 0]
    ax.plot(day, S_prompt, "k-", lw=1.8, label=r"Analytic $S_{\mathrm{prompt}}$")
    ax.axhline(1.0, color="0.5", lw=0.6, ls=":")
    for part, mk in [("eplus", "o"), ("n", "s"), ("gamma", "^")]:
        for pid in order:
            r = next(x for x in runs if x["point_id"] == pid and x["particle"] == part)
            ax.scatter(
                [pt_day(pid)],
                [float(r["gen_rate_hz_over_REF"])],
                marker=mk,
                color=species_color[part],
                s=55,
                edgecolors="k",
                linewidths=0.4,
                zorder=5,
            )
    for pid in order:
        ax.scatter(
            [pt_day(pid)],
            [float(parma[pid]["scale_eplus"])],
            marker="x",
            color="#984ea3",
            s=70,
            linewidths=1.8,
            zorder=6,
        )
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Scale / REF")
    ax.set_title("(a) Gen-rate scales vs analytic curve", loc="left")
    ax.set_ylim(0.78, 1.28)
    ax.legend(
        handles=[
            Line2D([0], [0], color="k", lw=1.8, label=r"Analytic $S$"),
            Line2D(
                [0],
                [0],
                marker="o",
                color=species_color["eplus"],
                ls="None",
                ms=7,
                markeredgecolor="k",
                label=r"e$^{+}$ gen",
            ),
            Line2D(
                [0],
                [0],
                marker="s",
                color=species_color["n"],
                ls="None",
                ms=7,
                markeredgecolor="k",
                label="n gen",
            ),
            Line2D(
                [0],
                [0],
                marker="^",
                color=species_color["gamma"],
                ls="None",
                ms=7,
                markeredgecolor="k",
                label=r"$\gamma$ gen",
            ),
            Line2D(
                [0],
                [0],
                marker="x",
                color="#984ea3",
                ls="None",
                ms=7,
                mew=2,
                label=r"PARMA e$^{+}$",
            ),
        ],
        fontsize=7.5,
        loc="upper right",
    )

    ax = axes2[0, 1]
    ax.plot(day, S_prompt, "k-", lw=1.8)
    for part, col, mk, lab in [
        ("eplus", "#e41a1c", "o", r"PARMA e$^{+}$"),
        ("n", "#377eb8", "s", "PARMA n"),
        ("gamma", "#4daf4a", "^", r"PARMA $\gamma$"),
    ]:
        xs = [pt_day(pid) for pid in order]
        ys = [float(parma[pid][f"scale_{part}"]) for pid in order]
        ax.plot(xs, ys, color=col, lw=1.0, alpha=0.35, zorder=2)
        ax.scatter(
            xs,
            ys,
            marker=mk,
            color=col,
            s=70,
            edgecolors="k",
            linewidths=0.4,
            label=lab,
            zorder=5,
        )
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Flux scale / REF")
    ax.set_title("(b) Live PARMA env scales (species diverge)", loc="left")
    ax.set_ylim(0.78, 1.28)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.axhline(1.0, color="0.5", lw=0.6, ls=":")

    ax = axes2[1, 0]
    ax.plot(day, S_prompt, "k-", lw=1.8)
    ax.axhline(1.0, color="0.5", lw=0.6, ls=":")
    for pid in order:
        d = pt_day(pid)
        r = eplus[pid]
        band_over = float(r["band_rate_hz_over_REF"])
        tes_over = float(r["tes_rate_hz_over_REF"])
        n_band = int(float(r["n_band480_550"]))
        n_tes = int(float(r["n_tes"]))
        obs = float(r["obs_s"])
        eb = ratio_err(n_band, obs, ref_n_band, ref_obs)
        et = ratio_err(n_tes, obs, ref_n_tes, ref_obs)
        ax.errorbar(
            [d],
            [band_over],
            yerr=[eb],
            fmt="o",
            color=colors[pid],
            ms=8,
            capsize=3,
            markeredgecolor="k",
            markeredgewidth=0.4,
            zorder=5,
        )
        ax.errorbar(
            [d],
            [tes_over],
            yerr=[et],
            fmt="s",
            color=colors[pid],
            ms=6,
            capsize=2,
            markerfacecolor="none",
            markeredgewidth=1.2,
            zorder=5,
        )
        ax.text(
            d,
            band_over + 0.02,
            pid,
            ha="center",
            fontsize=8,
            color=colors[pid],
            fontweight="bold",
        )
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Rate / REF")
    ax.set_title(r"(c) Cosima e$^{+}$ TES & 480–550 band vs analytic", loc="left")
    ax.set_ylim(0.82, 1.20)
    ax.legend(
        handles=[
            Line2D([0], [0], color="k", lw=1.8, label=r"Analytic $S$"),
            Line2D(
                [0],
                [0],
                marker="o",
                color="0.3",
                ls="None",
                ms=7,
                markeredgecolor="k",
                label="band / REF",
            ),
            Line2D(
                [0],
                [0],
                marker="s",
                color="0.3",
                ls="None",
                ms=6,
                markerfacecolor="none",
                markeredgewidth=1.2,
                label="TES / REF",
            ),
        ],
        fontsize=7.5,
        loc="upper right",
    )

    ax = axes2[1, 1]
    x = np.arange(len(order))
    w = 0.22
    Qb_ana = [float(eplus[pid]["Q_band_rate_hz_vs_analytic"]) for pid in order]
    Qb_par = [float(eplus[pid]["Q_band_rate_hz_vs_live_parma"]) for pid in order]
    Qt_ana = [float(eplus[pid]["Q_tes_rate_hz_vs_analytic"]) for pid in order]
    Qt_par = [float(eplus[pid]["Q_tes_rate_hz_vs_live_parma"]) for pid in order]
    ax.bar(
        x - 1.5 * w,
        Qb_ana,
        w,
        label=r"$Q_{\mathrm{band}}$ vs analytic",
        color="#e41a1c",
        edgecolor="k",
        lw=0.4,
    )
    ax.bar(
        x - 0.5 * w,
        Qb_par,
        w,
        label=r"$Q_{\mathrm{band}}$ vs PARMA",
        color="#e41a1c",
        alpha=0.45,
        edgecolor="k",
        lw=0.4,
        hatch="///",
    )
    ax.bar(
        x + 0.5 * w,
        Qt_ana,
        w,
        label=r"$Q_{\mathrm{TES}}$ vs analytic",
        color="#377eb8",
        edgecolor="k",
        lw=0.4,
    )
    ax.bar(
        x + 1.5 * w,
        Qt_par,
        w,
        label=r"$Q_{\mathrm{TES}}$ vs PARMA",
        color="#377eb8",
        alpha=0.45,
        edgecolor="k",
        lw=0.4,
        hatch="///",
    )
    ax.axhline(1.0, color="k", lw=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(order)
    ax.set_ylabel(r"$Q$")
    ax.set_ylim(0.85, 1.15)
    ax.set_title(r"(d) e$^{+}$ residual $Q$ at validation points", loc="left")
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    ax.set_xlabel("Validation point")

    fig2.suptitle(
        f"Trajectory validation diagnostics — {results_tag} Cosima (NOT full4 / NOT W2)",
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )
    fig2.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.08, hspace=0.35, wspace=0.28)
    for dest in (OUT, OUT_TGT):
        for ext in ("png", "pdf"):
            fig2.savefig(dest / f"analytic_curve_mc_diagnostics.{ext}", bbox_inches="tight")
    plt.close(fig2)

    # ----- Figure 3: paper-style -----
    fig3, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(
        day,
        S_prompt,
        color="k",
        lw=2.2,
        label=r"Analytic prompt scale $S_{\mathrm{prompt}}(t)$",
        zorder=3,
    )
    ax.axhline(1.0, color="0.4", lw=0.7, ls=":", zorder=1)
    ord_by_day = sorted(order, key=pt_day)
    ax.errorbar(
        [pt_day(pid) for pid in ord_by_day],
        [float(eplus[pid]["band_rate_hz_over_REF"]) for pid in ord_by_day],
        yerr=[
            ratio_err(
                int(float(eplus[pid]["n_band480_550"])),
                float(eplus[pid]["obs_s"]),
                ref_n_band,
                ref_obs,
            )
            for pid in ord_by_day
        ],
        fmt="o",
        color="#c0392b",
        ms=9,
        capsize=3.5,
        elinewidth=1.2,
        markeredgecolor="k",
        markeredgewidth=0.5,
        zorder=6,
        label=r"Cosima e$^{+}$ 480–550 keV rate / REF",
    )
    ax.scatter(
        [pt_day(pid) for pid in ord_by_day],
        [float(parma[pid]["scale_eplus"]) for pid in ord_by_day],
        marker="D",
        s=55,
        color="#2980b9",
        edgecolors="k",
        linewidths=0.5,
        zorder=5,
        label=r"Live PARMA e$^{+}$ flux / REF",
    )
    for pid in order:
        d = pt_day(pid)
        y = float(eplus[pid]["band_rate_hz_over_REF"])
        ax.annotate(
            pid,
            (d, y),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#c0392b",
        )
    ax.set_xlabel("Mission day")
    ax.set_ylabel(r"Scale relative to day-15 reference")
    ax.set_xlim(-0.5, 20.5)
    ax.set_ylim(0.84, 1.18)
    ax.set_title(
        rf"Analytic trajectory curve with multi-point Cosima validation ({title_tag})",
        loc="left",
        fontsize=10.5,
    )
    ax.legend(loc="upper right", framealpha=0.95)
    ax.text(
        0.02,
        0.03,
        claim_note
        + "\n"
        + r"MC tracks live PARMA; residual vs analytic $S$ is env-layer scalar mismatch. "
        r"Not full4 / not Step05 W2 / not activation.",
        transform=ax.transAxes,
        fontsize=7.2,
        color="#333333",
        va="bottom",
    )
    fig3.tight_layout()
    for dest in (OUT, OUT_TGT):
        for ext in ("png", "pdf"):
            fig3.savefig(dest / f"analytic_curve_overlay_paperstyle.{ext}", bbox_inches="tight")
    plt.close(fig3)

    print(f"Wrote figures under {OUT} and {OUT_TGT} (source={results_tag})")
    for dest in (OUT, OUT_TGT):
        print(dest)
        for f in sorted(dest.iterdir()):
            print(f"  {f.name} {f.stat().st_size}")


if __name__ == "__main__":
    main()
