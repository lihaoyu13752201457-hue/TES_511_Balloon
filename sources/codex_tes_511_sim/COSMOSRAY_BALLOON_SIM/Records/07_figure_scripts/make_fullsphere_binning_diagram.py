#!/usr/bin/env python3
"""Draw the full-sphere 20-bin equal-solid-angle source diagram."""

from __future__ import annotations

import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "01_source_injection_smoke" / "图片2.png"

os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
(HERE / ".mplconfig").mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt


def bin_color(i: int) -> tuple[float, float, float, float]:
    if i < 10:
        return plt.cm.YlOrRd(0.25 + 0.055 * i)
    return plt.cm.PuBuGn(0.28 + 0.055 * (i - 10))


def draw_sphere(ax) -> None:
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
            alpha=0.58,
            linewidth=0,
            antialiased=True,
            shade=True,
        )

    # Equal-mu bin boundaries. The equator separates down-going and up-going bins.
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
            alpha=0.85 if is_equator else 0.55,
        )

    # A faint meridian helps show that the bins are full-azimuth bands.
    mer_theta = np.linspace(0.0, math.pi, 200)
    ax.plot(
        np.sin(mer_theta),
        np.zeros_like(mer_theta),
        np.cos(mer_theta),
        color="#333333",
        lw=0.9,
        alpha=0.55,
    )

    # Axis only; text labels live in figure coordinates to avoid overlap.
    ax.quiver(0, 0, -1.08, 0, 0, 2.16, color="#1f1f1f", arrow_length_ratio=0.055, lw=1.15)

    ax.set_box_aspect((1, 1, 1))
    ax.set_xlim(-1.16, 1.16)
    ax.set_ylim(-1.16, 1.16)
    ax.set_zlim(-1.12, 1.18)
    ax.view_init(elev=23, azim=-48)
    ax.set_axis_off()


def main() -> None:
    fig = plt.figure(figsize=(13.333, 7.5), dpi=144)
    fig.patch.set_facecolor("white")
    fig.suptitle("Full-sphere source binning", fontsize=24, y=0.965, weight="bold")
    fig.text(
        0.5,
        0.895,
        "20 equal-solid-angle bins in mu = cos(theta)",
        ha="center",
        fontsize=22,
        color="#333333",
    )
    fig.text(0.18, 0.60, "down-going\nbin00-09", ha="center", va="center", fontsize=24, weight="bold")
    fig.text(0.82, 0.40, "up / albedo-like\nbin10-19", ha="center", va="center", fontsize=24, weight="bold")
    fig.text(0.50, 0.765, "theta=0", ha="center", va="center", fontsize=24)
    fig.text(0.72, 0.505, "theta=90\nmu=0", ha="center", va="center", fontsize=24)
    fig.text(
        0.5,
        0.07,
        "theta: 0-180 deg        phi: 0-360 deg",
        ha="center",
        fontsize=22,
        color="#333333",
    )

    ax3d = fig.add_axes([0.22, 0.11, 0.56, 0.74], projection="3d")
    draw_sphere(ax3d)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=144, facecolor="white")
    plt.close(fig)
    OUT.chmod(0o644)
    print(OUT)


if __name__ == "__main__":
    main()
