#!/usr/bin/env python3
"""Draw point vs diffuse sources when both are represented on a start sphere."""

from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Rectangle, Wedge


HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "02_point_diffuse_source_model" / "spherical_field_point_vs_diffuse.png"


def arrow(ax, start, end, color, lw=1.3, alpha=1.0, ms=10):
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


def draw_instrument(ax, cx, cy, scale=1.0):
    lens_y = cy + 0.55 * scale
    det_y = cy - 0.55 * scale

    ax.add_patch(Rectangle((cx - 0.75 * scale, lens_y - 0.06 * scale), 1.5 * scale, 0.12 * scale,
                           facecolor="#64748b", edgecolor="#334155", linewidth=0.8))
    for x in [-0.55, -0.25, 0.05, 0.35]:
        ax.add_patch(Rectangle((cx + x * scale, lens_y - 0.22 * scale), 0.13 * scale, 0.44 * scale,
                               facecolor="#dbeafe", edgecolor="#2563eb", linewidth=0.7))
    ax.text(cx, lens_y + 0.35 * scale, "physical focusing optic", ha="center", va="center",
            fontsize=8.5, color="#334155")

    ax.add_patch(Rectangle((cx - 0.42 * scale, det_y - 0.06 * scale), 0.84 * scale, 0.12 * scale,
                           facecolor="#fb923c", edgecolor="#9a3412", linewidth=0.8))
    ax.add_patch(Rectangle((cx - 0.18 * scale, det_y - 0.35 * scale), 0.36 * scale, 0.24 * scale,
                           facecolor="#fed7aa", edgecolor="#9a3412", linewidth=0.7))
    ax.text(cx, det_y - 0.62 * scale, "detector", ha="center", va="center", fontsize=8.5, color="#334155")


def panel(ax, x0, title, mode):
    cx, cy, r = x0 + 2.85, 2.65, 2.25
    ax.text(x0 + 0.2, 5.35, title, fontsize=14, fontweight="bold", color="#111827")
    ax.text(x0 + 0.2, 5.05, "same surrounding/start sphere, different angular distribution",
            fontsize=8.7, color="#64748b")

    ax.add_patch(Circle((cx, cy), r, fill=False, linestyle=(0, (4, 3)), linewidth=1.2, edgecolor="#94a3b8"))
    ax.text(cx, cy - r - 0.25, "surrounding / start sphere", ha="center", fontsize=8.5, color="#64748b")
    draw_instrument(ax, cx, cy, scale=0.9)

    if mode == "point":
        col = "#2563eb"
        ax.add_patch(Wedge((cx, cy), r + 0.03, 100, 116, width=0.22, facecolor=col, alpha=0.25, edgecolor=col))
        ax.text(cx - 0.8, cy + r + 0.28, "one sky direction", fontsize=9, color=col, ha="center")

        starts = [(cx - 0.72, cy + r - 0.25), (cx - 0.36, cy + r - 0.18), (cx, cy + r - 0.13),
                  (cx + 0.36, cy + r - 0.18), (cx + 0.72, cy + r - 0.25)]
        lens = [(cx - 0.55, cy + 0.56), (cx - 0.28, cy + 0.56), (cx, cy + 0.56),
                (cx + 0.28, cy + 0.56), (cx + 0.55, cy + 0.56)]
        for s, e in zip(starts, lens):
            arrow(ax, s, e, col, lw=1.35)
        for e in lens:
            arrow(ax, e, (cx, cy - 0.47), col, lw=1.1)
        ax.add_patch(Circle((cx, cy - 0.47), 0.10, facecolor=col, edgecolor="white", linewidth=0.8))
        ax.text(cx + 1.05, cy - 0.28, "one compact\nfocal spot", fontsize=9, color=col, va="center")
        ax.text(x0 + 0.32, 0.35, "Sphere source setting:\nfixed theta/phi, finite start area\nparallel rays from one direction",
                fontsize=8.4, color="#1e3a8a")
    else:
        colors = ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#d97706"]
        angles = [122, 106, 90, 74, 58]
        focus_offsets = [-0.52, -0.25, 0.0, 0.25, 0.52]
        for col, ang, off in zip(colors, angles, focus_offsets):
            ax.add_patch(Wedge((cx, cy), r + 0.03, ang - 5, ang + 5, width=0.20,
                               facecolor=col, alpha=0.22, edgecolor=col, linewidth=0.8))
            rad = math.radians(ang)
            sx = cx + r * 0.96 * math.cos(rad)
            sy = cy + r * 0.96 * math.sin(rad)
            for dx in [-0.18, 0.0, 0.18]:
                start = (sx + dx, sy)
                hit = (cx + 0.55 * off, cy + 0.56)
                arrow(ax, start, hit, col, lw=1.05, alpha=0.95)
            spot = (cx + off, cy - 0.47)
            arrow(ax, (cx + 0.55 * off, cy + 0.56), spot, col, lw=1.0)
            ax.add_patch(Circle(spot, 0.085, facecolor=col, edgecolor="white", linewidth=0.7))

        ax.add_patch(Rectangle((cx - 0.65, cy - 0.67), 1.3, 0.38, fill=False,
                               linestyle=":", edgecolor="#334155", linewidth=1.0))
        ax.text(cx, cy + r + 0.28, "many weighted sky directions", fontsize=9, color="#374151", ha="center")
        ax.text(cx + 1.1, cy - 0.47, "extended / multi-spot\nfocal pattern", fontsize=9,
                color="#374151", va="center")
        ax.text(x0 + 0.32, 0.35, "Sphere source setting:\nI(theta,phi,E) over a sky patch\nmany direction bins, weighted rays",
                fontsize=8.4, color="#374151")


def main():
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=180)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.8)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(0.55, 5.68, "Spherical far-field source: point vs diffuse with optics above detector",
            fontsize=15, fontweight="bold", color="#111827")
    ax.text(0.55, 5.45,
            "The sphere is only the sampling/start surface. The physics difference is one angular direction versus a weighted angular map.",
            fontsize=9.3, color="#4b5563")

    panel(ax, 0.35, "Point source", "point")
    panel(ax, 6.15, "Diffuse source", "diffuse")

    ax.plot([6.0, 6.0], [0.25, 5.18], color="#e5e7eb", linewidth=1.0)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
