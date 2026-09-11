#!/usr/bin/env python3
"""Build the bilingual Compton-cone/aperture-veto method schematic."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, Ellipse, FancyArrowPatch, Polygon
from fontTools.ttLib import TTCollection


HERE = Path(__file__).resolve().parent

INK = "#263746"
BLUE = "#0072B2"
GREEN = "#009E73"
ORANGE = "#D55E00"
GRAY = "#6B7280"
LIGHT_GRAY = "#D6DCE1"
TES_FILL = "#F4D7D3"

FONT_COLLECTION = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_PATH = Path("/tmp/m05-NotoSansCJKSC-Regular.ttf")
if FONT_COLLECTION.exists() and not FONT_PATH.exists():
    collection = TTCollection(str(FONT_COLLECTION))
    collection.fonts[2].save(str(FONT_PATH))  # Noto Sans CJK SC
    collection.close()
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))

mpl.rcParams.update(
    {
        "font.family": "Noto Sans CJK SC",
        "font.size": 8.0,
        "axes.titlesize": 9.5,
        "text.color": INK,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


TEXT = {
    "en": {
        "title_a": "(a) Reconstructed cone",
        "title_b": "(b) Nine-point proxy",
        "title_c": "(c) Aperture decision",
        "aperture": "analysis aperture",
        "scatter": "scattered photon",
        "possible": "incident photon",
        "hit1": "hit 1",
        "hit2": "hit 2",
        "nine": "analysis representative box\n8 corners + centre",
        "pairs": r"$9\times9=81$ position pairs",
        "trace": "24 samples and connecting segments",
        "retain": "RETAIN",
        "veto": "VETO",
        "intersects": "intersects\naperture disk",
        "misses": "misses\naperture disk",
        "unreconstructed": r"No valid cone: kept as unreconstructed",
    },
    "zh": {
        "title_a": "(a) 康普顿重建锥",
        "title_b": "(b) 九点位置表示",
        "title_c": "(c) 孔径相容性判据",
        "aperture": "分析孔径",
        "scatter": "散射光子",
        "possible": "入射光子",
        "hit1": "命中 1",
        "hit2": "命中 2",
        "nine": "分析代表盒\n八个角点 + 中心",
        "pairs": r"$9\times9=81$ 组位置假设",
        "trace": "24 个方位采样点及相邻连线",
        "retain": "保留",
        "veto": "否决",
        "intersects": "与孔径圆盘\n相交",
        "misses": "未与孔径圆盘\n相交",
        "unreconstructed": r"无有效锥：记为未重建类并保留",
    },
}


def setup_axis(ax) -> None:
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")


def pixel_marker(ax, xy, label: str, color: str) -> None:
    x, y = xy
    ax.add_patch(
        Polygon(
            [[x - 0.035, y - 0.028], [x + 0.035, y - 0.028],
             [x + 0.035, y + 0.028], [x - 0.035, y + 0.028]],
            closed=True,
            facecolor=TES_FILL,
            edgecolor=color,
            lw=1.1,
            zorder=5,
        )
    )
    ax.plot(x, y, "o", ms=3.1, color=color, zorder=6)
    ax.text(x, y - 0.063, label, ha="center", va="top", fontsize=7.2)


def panel_cone(ax, txt) -> None:
    setup_axis(ax)
    ax.set_title(txt["title_a"], fontweight="bold", pad=5)

    aperture_x = 0.13
    aperture_y = 0.50
    r1 = np.array([0.69, 0.50])
    r2 = np.array([0.88, 0.50])
    upper = np.array([aperture_x, 0.68])
    lower = np.array([aperture_x, 0.32])

    ax.plot([aperture_x, aperture_x], [0.14, 0.86], color=GRAY, lw=1.0)
    ax.add_patch(
        Ellipse(
            (aperture_x, aperture_y),
            0.075,
            0.48,
            facecolor=GREEN,
            edgecolor=GREEN,
            alpha=0.13,
            lw=1.4,
            zorder=3,
        )
    )
    ax.text(aperture_x - 0.005, 0.12, txt["aperture"], ha="center", va="top", fontsize=7.0)
    ax.text(aperture_x + 0.045, 0.75, r"$r_{\rm ap}$", color=GREEN, fontsize=7.2)

    ax.add_patch(
        Polygon(
            [r1, upper, lower],
            closed=True,
            facecolor=BLUE,
            edgecolor="none",
            alpha=0.08,
            zorder=1,
        )
    )
    ax.plot([r1[0], upper[0]], [r1[1], upper[1]], color=BLUE, lw=1.25)
    ax.plot([r1[0], lower[0]], [r1[1], lower[1]], color=BLUE, lw=1.25)
    ax.plot([r1[0], aperture_x], [r1[1], aperture_y], color=BLUE, lw=0.9, ls="--")
    ax.add_patch(
        FancyArrowPatch(
            posA=(0.21, 0.50),
            posB=(0.58, 0.50),
            arrowstyle="-|>",
            mutation_scale=8,
            lw=1.1,
            color=GREEN,
        )
    )
    ax.text(0.31, 0.68, txt["possible"], color=GREEN, ha="center", va="bottom", fontsize=6.7)

    pixel_marker(ax, r1, r"$\mathbf{r}_1,\ E_1$", ORANGE)
    pixel_marker(ax, r2, r"$\mathbf{r}_2,\ E_{\rm sc}$", ORANGE)
    ax.add_patch(
        FancyArrowPatch(
            posA=(r1[0] + 0.03, r1[1]),
            posB=(r2[0] - 0.03, r2[1]),
            arrowstyle="-|>",
            mutation_scale=8,
            lw=1.2,
            color=ORANGE,
        )
    )
    ax.text(0.80, 0.67, txt["scatter"], color=ORANGE, ha="center", fontsize=6.8)
    ax.text(0.48, 0.455, r"$-\hat{\mathbf{u}}_{12}$", color=BLUE, ha="center", fontsize=7.4)

    theta_deg = np.degrees(np.arctan2(0.18, r1[0] - aperture_x))
    ax.add_patch(
        Arc(
            r1,
            0.22,
            0.22,
            angle=0.0,
            theta1=180.0 - theta_deg,
            theta2=180.0,
            color=INK,
            lw=0.9,
        )
    )
    ax.text(r1[0] - 0.125, r1[1] + 0.035, r"$\theta_C$", fontsize=7.5)


def cube_vertices(x: float, y: float, size: float = 0.25):
    dx = 0.085
    dy = 0.070
    front = np.array(
        [[x, y], [x + size, y], [x + size, y + size], [x, y + size]],
        dtype=float,
    )
    back = front + np.array([dx, dy])
    return front, back


def draw_cube(ax, x: float, y: float, label: str, color: str) -> None:
    front, back = cube_vertices(x, y)
    for poly in (front, back):
        closed = np.vstack([poly, poly[0]])
        ax.plot(closed[:, 0], closed[:, 1], color=INK, lw=0.9)
    for i in range(4):
        ax.plot([front[i, 0], back[i, 0]], [front[i, 1], back[i, 1]], color=INK, lw=0.9)
    points = np.vstack([front, back])
    ax.scatter(points[:, 0], points[:, 1], s=15, color=color, edgecolors="white", linewidths=0.35, zorder=4)
    centroid = points.mean(axis=0)
    ax.scatter([centroid[0]], [centroid[1]], s=32, marker="*", color=ORANGE, edgecolors=INK, linewidths=0.35, zorder=5)
    ax.text(centroid[0], y - 0.075, label, ha="center", va="top", fontsize=7.3)


def panel_subpixel(ax, txt) -> None:
    setup_axis(ax)
    ax.set_title(txt["title_b"], fontweight="bold", pad=5)
    draw_cube(ax, 0.10, 0.39, txt["hit1"], BLUE)
    draw_cube(ax, 0.57, 0.39, txt["hit2"], BLUE)
    ax.add_patch(
        FancyArrowPatch(
            posA=(0.42, 0.55),
            posB=(0.56, 0.55),
            arrowstyle="<->",
            mutation_scale=7,
            lw=0.9,
            color=GRAY,
        )
    )
    ax.text(0.50, 0.84, txt["nine"], ha="center", va="center", fontsize=7.0, linespacing=1.15)
    ax.text(0.50, 0.18, txt["pairs"], ha="center", va="center", fontsize=9.0, color=BLUE, fontweight="bold")


def sampled_ellipse(ax, center, width, height, color=BLUE) -> None:
    phi = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
    x = center[0] + 0.5 * width * np.cos(phi)
    y = center[1] + 0.5 * height * np.sin(phi)
    ax.plot(np.r_[x, x[0]], np.r_[y, y[0]], color=color, lw=1.0, zorder=2)
    ax.scatter(x, y, s=7.0, color=color, edgecolors="white", linewidths=0.25, zorder=3)


def panel_decision(ax, txt) -> None:
    setup_axis(ax)
    ax.set_title(txt["title_c"], fontweight="bold", pad=5)

    disk_y = 0.57
    disk_r = 0.125
    left_disk = (0.25, disk_y)
    right_disk = (0.68, disk_y)

    for center in (left_disk, right_disk):
        ax.add_patch(Circle(center, disk_r, facecolor=GREEN, edgecolor=GREEN, alpha=0.13, lw=1.2, zorder=1))

    sampled_ellipse(ax, (0.34, disk_y), 0.30, 0.40)
    sampled_ellipse(ax, (0.91, disk_y), 0.16, 0.34)

    ax.text(0.50, 0.82, txt["trace"], color=BLUE, ha="center", va="bottom", fontsize=6.4)
    ax.text(0.25, 0.28, txt["retain"], color=GREEN, ha="center", va="top", fontsize=9.0, fontweight="bold")
    ax.text(0.25, 0.22, txt["intersects"], ha="center", va="top", fontsize=6.3, linespacing=1.1)
    ax.text(0.68, 0.28, txt["veto"], color=ORANGE, ha="center", va="top", fontsize=9.0, fontweight="bold")
    ax.text(0.68, 0.22, txt["misses"], ha="center", va="top", fontsize=6.3, linespacing=1.1)

    ax.plot([0.49, 0.49], [0.34, 0.84], color=LIGHT_GRAY, lw=0.8)
    ax.text(0.50, 0.055, txt["unreconstructed"], color=GRAY, ha="center", va="center", fontsize=6.4)


def build(language: str) -> None:
    txt = TEXT[language]
    fig = plt.figure(figsize=(7.28, 2.65))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.14, 0.94, 1.25], wspace=0.10)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    panel_cone(axes[0], txt)
    panel_subpixel(axes[1], txt)
    panel_decision(axes[2], txt)

    for left_ax, right_ax in zip(axes[:-1], axes[1:]):
        left_box = left_ax.get_position()
        right_box = right_ax.get_position()
        x = 0.5 * (left_box.x1 + right_box.x0)
        fig.add_artist(
            mpl.lines.Line2D([x, x], [0.08, 0.92], transform=fig.transFigure, color=LIGHT_GRAY, lw=0.8)
        )

    out = HERE / f"fig_compton_aperture_consistency_{language}.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.025, metadata={"Creator": "Matplotlib"})
    plt.close(fig)


def main() -> None:
    build("zh")
    build("en")


if __name__ == "__main__":
    main()
