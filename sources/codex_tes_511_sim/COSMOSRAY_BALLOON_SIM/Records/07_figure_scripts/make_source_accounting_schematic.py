#!/usr/bin/env python3
"""Draw a 2D source-accounting schematic for the coupled optics/detector system."""

from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "01_source_injection_smoke" / "source_accounting_two_systems.png"

os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
(HERE / ".mplconfig").mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


def add_box(ax, xy, width, height, label, *, fc, ec="#222222", lw=2.0, fontsize=24, weight="bold"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, label, ha="center", va="center", fontsize=fontsize, weight=weight)
    return box


def add_arrow(ax, start, end, *, color, lw=3.0, ls="-", rad=0.0, label=None, label_xy=None, fontsize=24, weight="bold"):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=22,
        linewidth=lw,
        linestyle=ls,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arrow)
    if label:
        x, y = label_xy if label_xy else ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        ax.text(x, y, label, ha="center", va="center", fontsize=fontsize, weight=weight, color=color)
    return arrow


def main() -> None:
    fig, ax = plt.subplots(figsize=(13.333, 7.5), dpi=144)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.suptitle("Source accounting in the coupled system", fontsize=24, y=0.95, weight="bold")

    # Systems.
    add_box(ax, (0.38, 0.42), 0.13, 0.23, "front\noptics", fc="#d9e8ff", fontsize=24)
    add_box(ax, (0.70, 0.39), 0.18, 0.28, "Detector\nTES + BGO", fc="#f3e0c4", fontsize=22)

    # Sky / atmosphere sources.
    ax.text(0.10, 0.78, "sky /\natmosphere", fontsize=24, weight="bold", ha="center", va="center")
    ax.add_patch(Circle((0.10, 0.57), 0.055, facecolor="#f5f5f5", edgecolor="#555555", linewidth=1.8))
    ax.add_patch(Polygon([(0.085, 0.59), (0.115, 0.59), (0.103, 0.535)], closed=True, facecolor="#d0d0d0", edgecolor="none"))

    # Aperture cone.
    cone = Polygon([(0.17, 0.60), (0.38, 0.63), (0.38, 0.45), (0.17, 0.53)], closed=True, facecolor="#fff0b3", edgecolor="#b58b00", alpha=0.42, linewidth=1.8)
    ax.add_patch(cone)
    ax.text(0.32, 0.68, "FoV / bandpass", ha="center", fontsize=22, color="#8a6a00", weight="bold")

    # Main streams.
    add_arrow(
        ax,
        (0.15, 0.58),
        (0.38, 0.57),
        color="#1976d2",
        lw=3.2,
        label="511 signal",
        label_xy=(0.28, 0.60),
        fontsize=24,
    )
    add_arrow(
        ax,
        (0.18, 0.51),
        (0.38, 0.49),
        color="#7b1fa2",
        lw=3.0,
        ls="--",
        label="focused gamma",
        label_xy=(0.27, 0.45),
        fontsize=24,
    )
    add_arrow(ax, (0.51, 0.57), (0.70, 0.57), color="#1976d2", lw=3.2)
    add_arrow(ax, (0.51, 0.49), (0.70, 0.49), color="#7b1fa2", lw=3.0, ls="--")

    add_arrow(
        ax,
        (0.14, 0.26),
        (0.70, 0.42),
        color="#d84315",
        lw=3.5,
        rad=-0.12,
        label="direct prompt\nfull sphere",
        label_xy=(0.37, 0.28),
        fontsize=24,
    )

    # Delayed activation is born inside detector/shield materials.
    ax.add_patch(Rectangle((0.735, 0.425), 0.11, 0.055, facecolor="#f9c7c7", edgecolor="#b71c1c", linewidth=1.6, alpha=0.85))
    ax.text(0.79, 0.452, "activation", ha="center", va="center", fontsize=18, weight="bold", color="#8b0000")
    ax.text(0.79, 0.27, "delayed\nactivation", ha="center", va="center", fontsize=24, weight="bold", color="#8b0000")
    add_arrow(ax, (0.79, 0.425), (0.79, 0.36), color="#8b0000", lw=3.0)

    # Accounting ledger.
    ledger = FancyBboxPatch(
        (0.16, 0.07),
        0.76,
        0.10,
        boxstyle="round,pad=0.02,rounding_size=0.018",
        facecolor="#f7f7f7",
        edgecolor="#555555",
        linewidth=1.5,
    )
    ax.add_patch(ledger)
    ax.text(
        0.50,
        0.12,
        "B = prompt_direct + delayed_activation + gamma_focused",
        ha="center",
        va="center",
        fontsize=22,
        color="#222222",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=144, facecolor="white")
    plt.close(fig)
    OUT.chmod(0o644)
    print(OUT)


if __name__ == "__main__":
    main()
