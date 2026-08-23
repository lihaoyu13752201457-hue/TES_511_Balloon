#!/usr/bin/env python3
"""Schematic for paper section 3.3.1: Poisson superposition / rate normalization.

(a) relative full-band detector rates
(b) independent Poisson draws merged onto one axis (color = stream)
(c) tau-grouping on the merged microsecond axis

Hatched bands mark the temporal footprint of each event. On panel (b) the
footprint is schematic (ms scale); on panel (c) it is tau = 1 us. Event
positions are didactic, not catalogue data.
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

OUT = Path(__file__).resolve().parent / "fig_s33_poisson_normalization.png"

INK = "#1a1a1a"
BLUE = "#1f6f8b"
GREEN = "#2e7d32"
RED = "#c0392b"
ORANGE = "#d35400"
GRAY = "#666666"
LIGHT = "#f4f6f8"
BOX_EC = "#b0b0b0"

R = {"prompt": 927.909, "delayed": 97.1211, "signal": 0.98661}  # s^-1
TAU_US = 1.0
# Panel (b) is in ms; true tau is invisible there, so use a schematic footprint.
EVENT_DT_MS = 0.35

STREAMS = [
    ("prompt", BLUE, R["prompt"]),
    ("delayed", GREEN, R["delayed"]),
    ("signal", RED, R["signal"]),
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
    names = [s[0] for s in STREAMS]
    colors = [s[1] for s in STREAMS]
    rates = np.array([s[2] for s in STREAMS], dtype=float)
    y = np.arange(len(rates))[::-1]

    ax.barh(y, rates, color=colors, height=0.58, edgecolor="none", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [rf"{n}" + "\n" + rf"{r:g} s$^{{-1}}$" for n, r in zip(names, rates)],
        fontsize=8.2,
        fontweight="bold",
    )
    for lab, c in zip(ax.get_yticklabels(), colors):
        lab.set_color(c)

    ax.set_xscale("log")
    ax.set_xlim(0.5, 1400)
    ax.set_xlabel(r"detector event rate [s$^{-1}$]", fontsize=8.2)
    ax.set_xticks([1, 10, 100, 1000])
    ax.set_xticklabels(["1", "10", "100", "10$^3$"], fontsize=7.6)
    ax.tick_params(axis="x", length=3, pad=2)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", which="major", ls=":", lw=0.6, color="#cccccc", zorder=0)
    _spine_off(ax, ("top", "right"))
    ax.spines["left"].set_visible(False)

    for yi, rate, c in zip(y, rates, colors):
        x_lab = rate * 1.15 if rate >= 1 else 1.35
        ax.text(x_lab, yi, f"{rate:g}", va="center", ha="left", fontsize=7.4, color=c)

    ax.set_title("(a) relative rates", fontsize=10.0, fontweight="bold", pad=10)


def panel_merge(ax):
    times = {
        "prompt": np.array([1.2, 3.8, 6.1, 8.4, 11.0, 13.7, 15.2]),
        "delayed": np.array([2.4, 7.0, 12.5]),
        "signal": np.array([9.6]),
    }
    colors = {s[0]: s[1] for s in STREAMS}
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
            fontsize=8.6,
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
        fontsize=8.2,
        fontweight="bold",
        color=INK,
    )

    ax.text(
        8.1,
        3.72,
        r"$N_k\sim\mathrm{Pois}(R_k T)$,  $t\sim\mathcal{U}[0,T]$  $\rightarrow$  merge & sort",
        ha="center",
        va="center",
        fontsize=7.6,
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
        "(b) independent draws  →  common time axis",
        fontsize=10.0,
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
    colors = {s[0]: s[1] for s in STREAMS}
    t_lo, t_hi = 4.40, 4.85

    # compact color key
    xleg = 0.2
    for name, col, _ in STREAMS:
        ax.plot([xleg, xleg + 0.35], [2.55, 2.55], color=col, lw=2.4, solid_capstyle="round")
        ax.text(xleg + 0.45, 2.55, name, fontsize=7.2, color=col, va="center", fontweight="bold")
        xleg += 2.4

    ax.plot([0.0, 10.2], [1.0, 1.0], color=INK, lw=1.25, zorder=1)
    ax.annotate(
        "",
        xy=(10.6, 1.0),
        xytext=(10.2, 1.0),
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.25),
    )
    ax.text(10.75, 1.0, r"$t$ [$\mu$s]", fontsize=8.2, va="center")

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
        fontsize=8.0,
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
        if kind == "singleton":
            ax.text(t, 0.48, "singleton", ha="center", va="top", fontsize=6.2, color=GRAY)

    ax.annotate(
        "",
        xy=(t_hi + 0.05, 0.38),
        xytext=(t_lo - 0.05, 0.38),
        arrowprops=dict(arrowstyle="|-|", color=ORANGE, lw=1.0, mutation_scale=5),
    )
    ax.text(
        0.5 * (t_lo + t_hi),
        0.12,
        r"$\Delta t < \tau$",
        ha="center",
        va="top",
        fontsize=7.2,
        color=ORANGE,
        fontweight="bold",
    )

    box = (
        r"$7{,}215{,}233$ instances" "\n"
        r"1275 mixed coincidences" "\n"
        r"$L=\mathrm{e}^{-R\tau}\simeq 0.9990$"
    )
    ax.text(
        5.2,
        -0.55,
        box,
        ha="center",
        va="top",
        fontsize=7.3,
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
        r"(c) $\tau$-grouping on the merged axis",
        fontsize=10.0,
        fontweight="bold",
        pad=10,
    )


def main():
    fig = plt.figure(figsize=(12.4, 4.5))
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

    fig.suptitle(
        "Rate normalization on a common coincidence time axis",
        fontsize=11.0,
        fontweight="bold",
        y=0.98,
        color=INK,
    )

    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")
    print(f"wrote {OUT.with_suffix('.svg')}")


if __name__ == "__main__":
    main()
