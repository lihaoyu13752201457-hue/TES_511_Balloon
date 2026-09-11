#!/usr/bin/env python3
"""Draw point-source vs diffuse-source behavior with a mass-model optic."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle


HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "02_point_diffuse_source_model" / "point_vs_diffuse_optics_schematic.png"


def arrow(ax, start, end, color, lw=1.4, alpha=1.0, ms=12):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=ms,
            linewidth=lw,
            color=color,
            alpha=alpha,
        )
    )


def draw_optic(ax, x, y, h=2.2):
    ax.add_patch(Rectangle((x - 0.05, y - h / 2), 0.1, h, facecolor="#64748b", edgecolor="none"))
    ax.add_patch(Rectangle((x - 0.22, y - h / 2), 0.12, h, facecolor="#dbeafe", edgecolor="#334155", linewidth=1.0))
    ax.add_patch(Rectangle((x + 0.10, y - h / 2), 0.12, h, facecolor="#dbeafe", edgecolor="#334155", linewidth=1.0))
    for k in range(6):
        yy = y - h / 2 + 0.25 + k * (h - 0.5) / 5
        ax.plot([x - 0.22, x + 0.22], [yy, yy + 0.12], color="#2563eb", linewidth=0.9, alpha=0.75)
        ax.plot([x - 0.22, x + 0.22], [yy + 0.12, yy], color="#2563eb", linewidth=0.9, alpha=0.75)


def draw_detector(ax, x, y):
    ax.add_patch(Rectangle((x - 0.07, y - 0.9), 0.14, 1.8, facecolor="#f97316", edgecolor="#7c2d12", linewidth=1.0))
    ax.add_patch(Rectangle((x + 0.18, y - 0.55), 0.22, 1.1, facecolor="#fed7aa", edgecolor="#9a3412", linewidth=0.9))


def draw_panel(ax, y0, title, mode):
    ax.text(0.45, y0 + 2.75, title, fontsize=14, fontweight="bold", color="#111827")
    ax.plot([0.45, 11.55], [y0 - 0.05, y0 - 0.05], color="#e5e7eb", linewidth=1.0)

    ax.text(0.65, y0 + 2.25, "far-field sky", fontsize=10, color="#475569")
    ax.text(4.8, y0 + 2.25, "mass-model optics", fontsize=10, color="#475569", ha="center")
    ax.text(8.7, y0 + 2.25, "focal plane / detector", fontsize=10, color="#475569", ha="center")

    draw_optic(ax, 5.0, y0 + 1.05)
    draw_detector(ax, 8.35, y0 + 1.05)

    ax.add_patch(Rectangle((0.7, y0 + 0.0), 1.25, 2.05, fill=False, edgecolor="#94a3b8", linewidth=1.0, linestyle="--"))
    ax.text(1.32, y0 - 0.27, "start surface", fontsize=8.5, color="#64748b", ha="center")

    if mode == "point":
        color = "#2563eb"
        for yy in [0.35, 0.75, 1.05, 1.35, 1.75]:
            arrow(ax, (0.8, y0 + yy), (4.72, y0 + yy), color, lw=1.5)
        for yy in [0.35, 0.75, 1.05, 1.35, 1.75]:
            arrow(ax, (5.25, y0 + yy), (8.15, y0 + 1.05 + 0.14 * (yy - 1.05)), color, lw=1.25)
        ax.add_patch(Circle((8.35, y0 + 1.05), 0.17, facecolor="#2563eb", edgecolor="white", linewidth=1.0, alpha=0.9))
        ax.text(2.7, y0 + 1.98, "one sky direction", fontsize=9.5, color=color, ha="center")
        ax.text(8.9, y0 + 1.05, "compact spot", fontsize=9.5, color=color, va="center")
        ax.text(
            0.75,
            y0 + 0.05,
            "Source input: fixed direction\nparallel rays over aperture",
            fontsize=9,
            color="#1e3a8a",
        )
    else:
        colors = ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#ca8a04"]
        slopes = [-0.32, -0.16, 0.0, 0.16, 0.32]
        starts = [1.85, 1.55, 1.05, 0.55, 0.25]
        spots = [1.65, 1.35, 1.05, 0.78, 0.48]
        for col, slope, yy, spot_y in zip(colors, slopes, starts, spots):
            for dx in [0.0, 0.22, 0.44]:
                arrow(ax, (0.75, y0 + yy - dx * 0.25), (4.72, y0 + yy + slope - dx * 0.25), col, lw=1.15, alpha=0.9)
            arrow(ax, (5.25, y0 + yy + slope), (8.15, y0 + spot_y), col, lw=1.05, alpha=0.9)
            ax.add_patch(Circle((8.35, y0 + spot_y), 0.11, facecolor=col, edgecolor="white", linewidth=0.8, alpha=0.88))

        ax.add_patch(
            Polygon(
                [(8.18, y0 + 0.25), (8.62, y0 + 0.35), (8.58, y0 + 1.82), (8.16, y0 + 1.68)],
                closed=True,
                fill=False,
                edgecolor="#334155",
                linewidth=1.0,
                linestyle=":",
            )
        )
        ax.text(2.7, y0 + 1.98, "many sky directions", fontsize=9.5, color="#374151", ha="center")
        ax.text(8.95, y0 + 1.05, "extended / shifted\nfocal pattern", fontsize=9.5, color="#374151", va="center")
        ax.text(
            0.75,
            y0 + 0.05,
            "Source input: angular map I(l,b,E)\nsampled as many far-field beams",
            fontsize=9,
            color="#374151",
        )


def main():
    fig, ax = plt.subplots(figsize=(12.5, 7.6), dpi=180)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.4)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        0.45,
        7.05,
        "Point source vs diffuse source with a physical optics mass model",
        fontsize=16,
        fontweight="bold",
        color="#111827",
    )
    ax.text(
        0.45,
        6.68,
        "Both can be far-field inputs. The difference is angular extent: one direction versus an intensity map over many directions.",
        fontsize=10,
        color="#4b5563",
    )

    draw_panel(ax, 3.55, "Point source", "point")
    draw_panel(ax, 0.25, "Diffuse source", "diffuse")

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
