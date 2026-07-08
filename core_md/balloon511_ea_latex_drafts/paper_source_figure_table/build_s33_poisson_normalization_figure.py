#!/usr/bin/env python3
"""Schematic for paper section 3.3.1: Poisson superposition / rate normalization.

Panel (a): three independent homogeneous-Poisson streams (prompt, delayed,
focused signal) are drawn at their full-band detector rates and merged, time
ordered, onto one common coincidence time axis. Panel (b): events within the
tau = 1 us coincidence window form one candidate group; the accidental-
coincidence bookkeeping over the reference exposure is annotated.

Numbers are the fix5 baseline coincidence-axis values from
core_md/balloon511_nima_latex_drafts/paper_source_figure_table/
fig_selection_veto_time_axis_summary.json (poisson_timeline block); the event
tick positions in panel (a) are an illustrative Poisson realization, not data.
"""
from __future__ import annotations
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fig_s33_poisson_normalization.png"

INK, BLUE, RED, GREEN, ORANGE, GRAY = "#1b1b1b", "#1f6f8b", "#c0392b", "#27803a", "#e08a1e", "#7a7a7a"

# fix5 coincidence-axis (full-band) rates and accidental bookkeeping
R = {"prompt": 676.0, "delayed": 71.0, "signal": 0.99}   # Hz
N_INSTANCES = 8.7e6
N_MIXED = 1134
LIVE = 0.9992
TAU_US = 1.0

rng = np.random.default_rng(20260708)


def poisson_ticks(rate_hz, t_span_s):
    """Illustrative homogeneous-Poisson event times in [0, t_span_s]."""
    n = rng.poisson(rate_hz * t_span_s)
    return np.sort(rng.uniform(0, t_span_s, size=n))


def panel_streams(ax):
    span = 0.018  # 18 ms window
    rows = [("prompt", 3, BLUE, R["prompt"]),
            ("delayed", 2, GREEN, R["delayed"]),
            ("signal", 1, RED, R["signal"])]
    all_t = []
    for name, y, c, rate in rows:
        t = poisson_ticks(rate, span)
        all_t.append(t)
        ax.vlines(t * 1e3, y - 0.32, y + 0.32, color=c, lw=1.6)
        ax.text(-0.6, y, f"{name}\n{rate:g} Hz", ha="right", va="center",
                fontsize=8.2, color=c, fontweight="bold")
        if len(t) == 0:
            ax.text(span * 1e3 * 0.5, y, r"($\lesssim1$ in 18 ms window)",
                    ha="center", va="center", fontsize=7.2, color=GRAY, style="italic")
    merged = np.sort(np.concatenate(all_t))
    ax.vlines(merged * 1e3, 0 - 0.32, 0 + 0.32, color=INK, lw=1.4)
    ax.text(-0.6, 0, "combined\naxis", ha="right", va="center",
            fontsize=8.2, color=INK, fontweight="bold")
    ax.annotate("", xy=(span * 1e3 + 0.3, 0), xytext=(-0.1, 0),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1))
    ax.text(span * 1e3 + 0.35, 0, "t", fontsize=9, va="center")
    for y in (3, 2, 1):
        ax.annotate("", xy=(-0.1, 0.55), xytext=(-0.1, y - 0.55),
                    arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=0.8))
    ax.text(span * 1e3 * 0.5, 3.95,
            r"$N_k\sim\mathrm{Pois}(R_k T)$, times $\sim\mathcal{U}[0,T]$, then merge & sort",
            ha="center", fontsize=8.6, color=INK)
    ax.set_xlim(-3.6, span * 1e3 + 1.0)
    ax.set_ylim(-0.7, 4.3)
    ax.set_xlabel("time [ms]", fontsize=8.5)
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_title("(a) independent Poisson streams superposed", fontsize=9.5)


def panel_coincidence(ax):
    # zoom window ~8 us with a couple of singletons and one within-tau pair
    ev = np.array([0.7, 2.9, 4.35, 4.95, 7.1])  # us
    grp_colors = [BLUE, BLUE, BLUE, GREEN, BLUE]
    ax.vlines(ev, 0.55, 1.15, color=grp_colors, lw=2.0)
    ax.annotate("", xy=(8.0, 0.85), xytext=(0.0, 0.85),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1))
    ax.text(8.05, 0.85, r"t [$\mu$s]", fontsize=8.5, va="center")
    # tau bracket around the close pair (4.35, 4.95)
    ax.plot([4.35, 4.95], [1.32, 1.32], color=RED, lw=1.6)
    ax.plot([4.35, 4.35], [1.24, 1.4], color=RED, lw=1.6)
    ax.plot([4.95, 4.95], [1.24, 1.4], color=RED, lw=1.6)
    ax.text(4.65, 1.5, r"$\tau=1\,\mu$s" + "\ncandidate group $c$",
            ha="center", va="bottom", fontsize=8.0, color=RED, fontweight="bold")
    for x in (0.7, 2.9, 7.1):
        ax.text(x, 0.4, "singleton", ha="center", va="top", fontsize=6.8, color=GRAY)
    ax.text(0.2, 0.06,
            ("over $T$: $\\simeq8.7\\times10^{6}$ instances $\\to$ candidate groups\n"
             f"74354 carry TES energy;  {N_MIXED} mixed-stream coincidences\n"
             f"accidental live factor $L\\simeq{LIVE}$"),
            fontsize=7.8, va="bottom",
            bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.set_xlim(-0.4, 9.2)
    ax.set_ylim(-0.05, 1.95)
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_title(r"(b) $\tau$-coincidence grouping on the merged axis", fontsize=9.5)


def main():
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.5))
    panel_streams(axes[0])
    panel_coincidence(axes[1])
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
