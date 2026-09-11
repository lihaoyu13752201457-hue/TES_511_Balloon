#!/usr/bin/env python3
"""Symbolic schematic for the M05NEW three-catalogue coincidence test.

The layout follows the earlier M05 Poisson-normalization figure, but all legacy
rates and coincidence counts are deliberately removed.  The atmospheric
mono-511 catalogue is kept outside the reference three-catalogue draw; the
callout distinguishes that reference test from the final four-component time
axis.
"""
from __future__ import annotations

import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fig04a_poisson_time_axis_schematic.png"

INK = "#1a1a1a"
BLUE = "#0072B2"
GREEN = "#009E73"
RED = "#D55E00"
PURPLE = "#CC79A7"
ORANGE = "#d35400"
GRAY = "#666666"
LIGHT = "#f4f6f8"
BOX_EC = "#b0b0b0"

TAU_US = 1.0
# Panel (b) is in ms; true tau is invisible there, so use a schematic footprint.
EVENT_DT_MS = 0.35

STREAMS = [
    ("prompt", BLUE),
    ("delayed", GREEN),
    ("signal", RED),
]


def _spine_off(ax, which=("top", "right", "left")):
    for s in which:
        ax.spines[s].set_visible(False)


def _event_hatch(ax, t, y0, height, width, color, zorder=0):
    ax.add_patch(
        Rectangle(
            (t, y0),
            width,
            height,
            facecolor=color,
            edgecolor=color,
            lw=0.4,
            alpha=0.18,
            hatch="////",
            zorder=zorder,
        )
    )


def panel_rate_scale(ax):
    y_positions = [2.45, 1.45, 0.45]
    for (name, color), y in zip(STREAMS, y_positions):
        ax.add_patch(
            Rectangle(
                (0.05, y - 0.32),
                0.90,
                0.64,
                facecolor=color,
                edgecolor=color,
                lw=0.8,
                alpha=0.09,
            )
        )
        ax.plot([0.11, 0.25], [y, y], color=color, lw=3.0, solid_capstyle="round")
        ax.text(0.30, y + 0.15, name, color=color, fontsize=9.5,
                fontweight="bold", va="center")
        ax.text(0.30, y - 0.15,
                rf"$r_{{k m}}\qquad R_k=\sum_m r_{{k m}}$",
                color=INK, fontsize=7.2, va="center")

    ax.text(
        0.50,
        -0.30,
        "three independently\nnormalized catalogues",
        ha="center",
        va="center",
        fontsize=7.2,
        color=GRAY,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.60, 3.05)
    ax.set_xticks([])
    ax.set_yticks([])
    _spine_off(ax, ("top", "right", "left", "bottom"))
    ax.set_title("(a) rate weights", fontsize=11.0,
                 fontweight="bold", pad=10)


def panel_merge(ax):
    times = {
        "prompt": np.array([1.2, 3.8, 6.1, 8.4, 11.0, 13.7, 15.2]),
        "delayed": np.array([2.4, 7.0, 12.5]),
        "signal": np.array([9.6]),
    }
    colors = dict(STREAMS)
    y_map = {"prompt": 3.0, "delayed": 2.0, "signal": 1.0}
    dt = EVENT_DT_MS

    for name, y in y_map.items():
        ax.axhspan(y - 0.36, y + 0.36, color=colors[name], alpha=0.06, zorder=0)
        ax.plot([0, 16.2], [y, y], color=colors[name], lw=0.55, alpha=0.3, zorder=1)

    # stream rows: hatch = event time footprint + tick
    for name, y in y_map.items():
        for t in times[name]:
            _event_hatch(ax, t, y - 0.28, 0.56, dt, colors[name], zorder=1)
            ax.plot(
                [t, t],
                [y - 0.26, y + 0.26],
                color=colors[name],
                lw=2.0,
                solid_capstyle="round",
                zorder=3,
            )
        ax.text(
            -0.55,
            y,
            name,
            ha="right",
            va="center",
            fontsize=9.2,
            fontweight="bold",
            color=colors[name],
        )

    guide_x = -0.15
    ax.plot([guide_x, guide_x], [0.35, 3.0], color=GRAY, lw=0.8, ls="--", zorder=1)
    ax.annotate(
        "",
        xy=(guide_x, 0.32),
        xytext=(guide_x, 0.55),
        arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=0.9),
    )

    merged = sorted(
        ((t, name) for name, arr in times.items() for t in arr),
        key=lambda x: x[0],
    )
    ax.plot([0.0, 16.2], [0.0, 0.0], color=INK, lw=1.25, zorder=2)
    ax.annotate(
        "",
        xy=(16.7, 0.0),
        xytext=(16.2, 0.0),
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.25),
    )
    ax.text(16.9, 0.0, "t", fontsize=9, va="center", color=INK)

    for t, name in merged:
        _event_hatch(ax, t, -0.28, 0.56, dt, colors[name], zorder=1)
        ax.plot(
            [t, t],
            [-0.26, 0.26],
            color=colors[name],
            lw=2.0,
            solid_capstyle="round",
            zorder=3,
        )

    ax.text(
        -0.55,
        0.0,
        "common\ntime axis",
        ha="right",
        va="center",
        fontsize=8.8,
        fontweight="bold",
        color=INK,
    )

    ax.text(
        8.1,
        3.72,
        r"$N_k\sim\mathrm{Pois}(R_k T)$,  $t\sim\mathcal{U}[0,T]$  $\rightarrow$  merge & sort",
        ha="center",
        va="center",
        fontsize=8.2,
        color=INK,
        bbox=dict(boxstyle="round,pad=0.28", fc=LIGHT, ec=BOX_EC, lw=0.6),
    )

    ax.set_xlim(-3.2, 17.4)
    ax.set_ylim(-0.65, 4.1)
    ax.set_xticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
    ax.set_xlabel("time [ms]", fontsize=8.2)
    ax.set_yticks([])
    _spine_off(ax)
    ax.set_title(
        "(b) Poisson merge",
        fontsize=11.0,
        fontweight="bold",
        pad=10,
    )


def panel_group(ax):
    tau = TAU_US
    events = [
        (0.9, "prompt", "singleton"),
        (2.7, "prompt", "singleton"),
        (4.40, "prompt", "mixed"),
        (4.85, "delayed", "mixed"),
        (6.9, "signal", "singleton"),
        (8.7, "prompt", "singleton"),
    ]
    colors = dict(STREAMS)
    t_lo, t_hi = 4.40, 4.85

    # compact color key
    for (name, col), xleg in zip(STREAMS, [0.1, 4.0, 7.9]):
        ax.plot([xleg, xleg + 0.35], [2.55, 2.55], color=col, lw=2.4, solid_capstyle="round")
        ax.text(xleg + 0.38, 2.55, name, fontsize=7.8, color=col, va="center", fontweight="bold")

    ax.plot([0.0, 10.2], [1.0, 1.0], color=INK, lw=1.25, zorder=1)
    ax.annotate(
        "",
        xy=(10.6, 1.0),
        xytext=(10.2, 1.0),
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.25),
    )
    ax.text(10.75, 1.0, r"$t$ [$\mu$s]", fontsize=8.8, va="center")

    # event-time hatch for every arrival
    for t, name, _kind in events:
        _event_hatch(ax, t, 0.68, 0.64, tau, colors[name], zorder=0)

    # mixed group emphasis
    ax.add_patch(
        Rectangle(
            (t_lo - 0.05, 0.55),
            (t_hi - t_lo) + tau * 0.55,
            1.0,
            facecolor=ORANGE,
            edgecolor="none",
            alpha=0.10,
            zorder=0,
        )
    )
    ax.plot([t_lo, t_hi], [1.72, 1.72], color=ORANGE, lw=1.7)
    ax.plot([t_lo, t_lo], [1.62, 1.82], color=ORANGE, lw=1.7)
    ax.plot([t_hi, t_hi], [1.62, 1.82], color=ORANGE, lw=1.7)
    ax.text(
        0.5 * (t_lo + t_hi),
        1.95,
        r"candidate group $c$",
        ha="center",
        va="bottom",
        fontsize=8.8,
        color=ORANGE,
        fontweight="bold",
    )

    for t, name, kind in events:
        ax.plot(
            [t, t],
            [0.72, 1.28],
            color=colors[name],
            lw=2.4,
            solid_capstyle="round",
            zorder=3,
        )
        ax.plot(t, 1.0, "o", color=colors[name], ms=3.8, zorder=4)

    ax.annotate(
        "",
        xy=(t_hi + 0.05, 0.38),
        xytext=(t_lo - 0.05, 0.38),
        arrowprops=dict(arrowstyle="|-|", color=ORANGE, lw=1.0, mutation_scale=5),
    )
    ax.text(
        0.5 * (t_lo + t_hi),
        0.12,
        r"$\Delta t \leq \tau$",
        ha="center",
        va="top",
        fontsize=8.0,
        color=ORANGE,
        fontweight="bold",
    )

    box = (
        "final four-component calculation:" "\n"
        "atmospheric 511 joins the background time axis;" "\n"
        "focused signal is inserted as a conditional probe"
    )
    ax.text(
        5.2,
        -0.55,
        box,
        ha="center",
        va="top",
        fontsize=7.5,
        color=INK,
        linespacing=1.4,
        bbox=dict(boxstyle="round,pad=0.4", fc=LIGHT, ec=BOX_EC, lw=0.7),
    )

    ax.set_xlim(-0.15, 11.4)
    ax.set_ylim(-1.7, 2.9)
    ax.set_yticks([])
    ax.set_xticks([])
    _spine_off(ax, ("top", "right", "left", "bottom"))
    ax.set_title(
        r"(c) $\tau$-grouping",
        fontsize=11.0,
        fontweight="bold",
        pad=10,
    )


def main():
    fig = plt.figure(figsize=(8.4, 3.25))
    gs = fig.add_gridspec(
        1,
        3,
        width_ratios=[1.0, 2.2, 1.9],
        wspace=0.28,
        left=0.055,
        right=0.99,
        top=0.88,
        bottom=0.12,
    )
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])

    panel_rate_scale(ax0)
    panel_merge(ax1)
    panel_group(ax2)

    fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")
    print(f"wrote {OUT.with_suffix('.svg')}")
    print(f"wrote {OUT.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
