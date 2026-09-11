#!/usr/bin/env python3
"""Build picture3 from the same full-sphere binning motif as picture2."""

from __future__ import annotations

import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "01_source_injection_smoke" / "图片3.png"

os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
(HERE / ".mplconfig").mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


def bin_color(i: int) -> tuple[float, float, float, float]:
    if i < 10:
        return plt.cm.YlOrRd(0.25 + 0.055 * i)
    return plt.cm.PuBuGn(0.28 + 0.055 * (i - 10))


def draw_fullsphere(ax) -> None:
    mu_edges = np.linspace(1.0, -1.0, 21)
    theta_edges = np.arccos(mu_edges)
    phi = np.linspace(0.0, 2.0 * math.pi, 181)

    for i in range(20):
        theta = np.linspace(theta_edges[i], theta_edges[i + 1], 8)
        pp, tt = np.meshgrid(phi, theta)
        x = np.sin(tt) * np.cos(pp)
        y = np.sin(tt) * np.sin(pp)
        z = np.cos(tt)
        ax.plot_surface(
            x,
            y,
            z,
            color=bin_color(i),
            alpha=0.60,
            linewidth=0,
            antialiased=True,
            shade=True,
        )

    for j, mu in enumerate(mu_edges):
        r = math.sqrt(max(0.0, 1.0 - float(mu) ** 2))
        x = r * np.cos(phi)
        y = r * np.sin(phi)
        z = np.full_like(phi, mu)
        is_equator = j == 10
        ax.plot(
            x,
            y,
            z,
            color="#111111" if is_equator else "#5c5c5c",
            lw=1.6 if is_equator else 0.65,
            alpha=0.82 if is_equator else 0.50,
        )

    mer_theta = np.linspace(0.0, math.pi, 200)
    ax.plot(np.sin(mer_theta), np.zeros_like(mer_theta), np.cos(mer_theta), color="#333333", lw=1.0, alpha=0.60)
    ax.quiver(0, 0, -1.08, 0, 0, 2.16, color="#1f1f1f", arrow_length_ratio=0.055, lw=1.1)

    ax.set_box_aspect((1, 1, 1))
    ax.set_xlim(-1.16, 1.16)
    ax.set_ylim(-1.16, 1.16)
    ax.set_zlim(-1.12, 1.18)
    ax.view_init(elev=23, azim=-48)
    ax.set_axis_off()


def fig_arrow(fig, start, end, *, color, lw=3.0, ls="-", rad=0.0, label=None, label_xy=None, fontsize=24):
    arrow = FancyArrowPatch(
        start,
        end,
        transform=fig.transFigure,
        arrowstyle="-|>",
        mutation_scale=24,
        linewidth=lw,
        linestyle=ls,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=4,
        shrinkB=4,
    )
    fig.patches.append(arrow)
    if label:
        x, y = label_xy if label_xy else ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        fig.text(x, y, label, ha="center", va="center", fontsize=fontsize, weight="bold", color=color)


def add_box(fig, xy, w, h, text, fc, *, fontsize=24):
    box = FancyBboxPatch(
        xy,
        w,
        h,
        transform=fig.transFigure,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        facecolor=fc,
        edgecolor="#222222",
        linewidth=2.0,
    )
    fig.patches.append(box)
    fig.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fontsize, weight="bold")


def main() -> None:
    fig = plt.figure(figsize=(13.333, 7.5), dpi=144)
    fig.patch.set_facecolor("white")
    fig.suptitle("Full-sphere source accounting", fontsize=24, y=0.975, weight="bold")
    fig.text(0.5, 0.905, "picture2 binning + optics / detector background ledger", ha="center", fontsize=18, color="#333333")

    ax_sphere = fig.add_axes([0.06, 0.18, 0.42, 0.64], projection="3d")
    draw_fullsphere(ax_sphere)
    fig.text(0.16, 0.74, "prompt source\n20 bins", ha="center", va="center", fontsize=24, weight="bold")
    fig.text(0.14, 0.34, "direct full-sphere\nprompt", ha="center", va="center", fontsize=24, weight="bold", color="#d84315")

    # FoV wedge and two coupled systems.
    wedge = Polygon(
        [(0.36, 0.56), (0.50, 0.62), (0.50, 0.45), (0.36, 0.50)],
        closed=True,
        transform=fig.transFigure,
        facecolor="#fff0b3",
        edgecolor="#b58b00",
        linewidth=1.8,
        alpha=0.55,
    )
    fig.patches.append(wedge)
    fig.text(0.45, 0.665, "FoV / bandpass", ha="center", fontsize=22, color="#8a6a00", weight="bold")

    add_box(fig, (0.51, 0.43), 0.13, 0.21, "front\noptics", "#d9e8ff", fontsize=24)
    add_box(fig, (0.76, 0.41), 0.17, 0.25, "Detector\nTES + BGO", "#f3e0c4", fontsize=22)

    fig_arrow(fig, (0.34, 0.57), (0.51, 0.57), color="#1976d2", lw=3.2, label="511 signal", label_xy=(0.44, 0.602), fontsize=22)
    fig_arrow(
        fig,
        (0.34, 0.50),
        (0.51, 0.50),
        color="#7b1fa2",
        lw=3.0,
        ls="--",
        label="focused gamma",
        label_xy=(0.44, 0.445),
        fontsize=22,
    )
    fig_arrow(fig, (0.64, 0.57), (0.76, 0.57), color="#1976d2", lw=3.2)
    fig_arrow(fig, (0.64, 0.50), (0.76, 0.50), color="#7b1fa2", lw=3.0, ls="--")
    fig_arrow(fig, (0.25, 0.30), (0.76, 0.43), color="#d84315", lw=3.6, rad=-0.15)

    # Delayed component inside detector.
    act = Rectangle(
        (0.80, 0.43),
        0.09,
        0.055,
        transform=fig.transFigure,
        facecolor="#f9c7c7",
        edgecolor="#b71c1c",
        linewidth=1.6,
        alpha=0.90,
    )
    fig.patches.append(act)
    fig.text(0.845, 0.457, "activation", ha="center", va="center", fontsize=18, weight="bold", color="#8b0000")
    fig_arrow(fig, (0.845, 0.43), (0.845, 0.34), color="#8b0000", lw=3.0)
    fig.text(0.845, 0.27, "delayed\nactivation", ha="center", va="center", fontsize=24, weight="bold", color="#8b0000")

    add_box(fig, (0.22, 0.07), 0.62, 0.09, "B = prompt_direct + delayed_activation + gamma_focused", "#f7f7f7", fontsize=22)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=144, facecolor="white")
    plt.close(fig)
    OUT.chmod(0o644)
    print(OUT)


if __name__ == "__main__":
    main()
