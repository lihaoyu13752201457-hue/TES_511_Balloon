#!/usr/bin/env python3
"""Draw the current and recommended diffuse-source injection logic."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
OUT = RECORDS / "02_point_diffuse_source_model" / "science_diffuse_source_schematic.png"


def box(ax, xy, text, width=2.7, height=0.9, fc="#f7f7f2", ec="#2f3a45"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.03,rounding_size=0.04",
        linewidth=1.2,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=9.5,
        color="#1e2933",
        linespacing=1.25,
    )
    return patch


def arrow(ax, start, end, color="#44515e", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def main():
    fig, ax = plt.subplots(figsize=(13, 7.2), dpi=180)
    ax.set_xlim(0, 12.9)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        0.5,
        6.72,
        "Diffuse 511-keV source: sky map first, detector injection only after optics folding",
        fontsize=15,
        fontweight="bold",
        color="#111827",
    )
    ax.text(
        0.5,
        6.35,
        "Current project status: B_GC_DIFFUSE is rate-folded only; no Cosima focal-spot source is generated without a real optics focal map.",
        fontsize=9.5,
        color="#4b5563",
    )

    b1 = box(ax, (0.5, 4.95), "Diffuse sky model\nI(l,b,E)\nbulge + disk map", fc="#eef6ff")
    b2 = box(ax, (3.45, 4.95), "Pointing / visibility\nFoV aperture\natmosphere T(E,t)", fc="#f5f0ff")
    b3 = box(ax, (6.4, 4.95), "Optics response\nAeff(E,theta)\nPSF K(x,y | l,b,E)", fc="#ecfdf3")
    b4 = box(ax, (9.35, 4.95), "Focal-plane photons\nat Be window\nP(x,y,E,t)", fc="#fff7ed")

    arrow(ax, (3.2, 5.4), (3.45, 5.4))
    arrow(ax, (6.15, 5.4), (6.4, 5.4))
    arrow(ax, (9.1, 5.4), (9.35, 5.4))

    c1 = box(ax, (0.75, 2.75), "Current L1 path\naperture / FoV integral\nrate only", fc="#f3f4f6")
    c2 = box(ax, (3.95, 2.75), "Allowed output\nB diffuse foreground\nno focal morphology claim", fc="#f3f4f6")
    arrow(ax, (2.0, 4.95), (1.95, 3.65), color="#6b7280", rad=0.1)
    arrow(ax, (2.7, 3.2), (3.95, 3.2), color="#6b7280")

    d1 = box(ax, (6.7, 2.75), "Production path\nsample sky pixels/rays\nweighted by I*Aeff*T", fc="#e8faf0")
    d2 = box(ax, (9.75, 2.75), "Cosima transport\nnear-field ray table\nor many small beams", fc="#e8faf0")
    arrow(ax, (10.7, 4.95), (8.05, 3.65), color="#059669", rad=-0.08)
    arrow(ax, (9.4, 3.2), (9.75, 3.2), color="#059669")

    ax.plot([0.5, 12.45], [2.2, 2.2], color="#d1d5db", linewidth=1.0)
    ax.text(0.65, 1.74, "Do not do:", fontsize=11, fontweight="bold", color="#991b1b")
    ax.text(
        1.75,
        1.74,
        "do not replace diffuse bulge/disk emission with one on-axis HomogeneousBeam or a uniform disk spot.",
        fontsize=9.5,
        color="#7f1d1d",
    )
    ax.text(0.65, 1.32, "Do:", fontsize=11, fontweight="bold", color="#065f46")
    ax.text(
        1.15,
        1.32,
        "fold sky brightness through pointing, atmosphere, Aeff and PSF; only then inject post-optics rays at the Be window.",
        fontsize=9.5,
        color="#064e3b",
    )

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
