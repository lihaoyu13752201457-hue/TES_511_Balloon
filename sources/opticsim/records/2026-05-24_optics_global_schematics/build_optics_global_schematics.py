#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent

LAUE_RING_CONFIG = ROOT / "data" / "laue" / "ge111_480_550keV_multiring_darwin_config.csv"
LAUE_SUMMARY = ROOT / "runs" / "geant4_laue_multiring_darwin" / "summary.json"
LAUE_GUAN_SUMMARY = ROOT / "runs" / "geant4_laue_darwin_guan_process" / "summary.json"

CHANNEL_RING_CONFIG = ROOT / "data" / "channel" / "cam511_channel_rings.csv"
CHANNEL_SUMMARY = ROOT / "runs" / "channel" / "geant4_4ring_multibounce_calibrated" / "summary.json"
CHANNEL_WALL_SUMMARY = ROOT / "runs" / "channel_wallbywall_rebuild" / "summary.json"


PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_figure(fig: plt.Figure, stem: str) -> None:
    for suffix in ("png", "svg"):
        fig.savefig(OUT_DIR / f"{stem}.{suffix}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def draw_arrow(
    ax: plt.Axes,
    xy0: tuple[float, float],
    xy1: tuple[float, float],
    color: str,
    lw: float = 1.8,
    alpha: float = 1.0,
    mutation_scale: float = 10.0,
    ls: str = "-",
) -> None:
    ax.annotate(
        "",
        xy=xy1,
        xytext=xy0,
        arrowprops={
            "arrowstyle": "-|>",
            "color": color,
            "lw": lw,
            "alpha": alpha,
            "linestyle": ls,
            "mutation_scale": mutation_scale,
            "shrinkA": 0,
            "shrinkB": 0,
        },
    )


def cm(value_mm: float) -> float:
    return value_mm / 10.0


def add_front_tiles(
    ax: plt.Axes,
    radii_cm: Iterable[float],
    n_tiles: Iterable[int],
    colors: Iterable[str],
    marker: str = "s",
    size: float = 15.0,
) -> None:
    for radius_cm, n_tile, color in zip(radii_cm, n_tiles, colors):
        phi = [2.0 * math.pi * i / n_tile for i in range(n_tile)]
        xs = [radius_cm * math.cos(p) for p in phi]
        ys = [radius_cm * math.sin(p) for p in phi]
        ax.add_patch(Circle((0, 0), radius_cm, fill=False, color=color, lw=1.25, alpha=0.75))
        ax.scatter(xs, ys, s=size, marker=marker, color=color, alpha=0.85, edgecolor="white", linewidth=0.25)


def plot_laue() -> None:
    rings = read_csv(LAUE_RING_CONFIG)
    summary = read_json(LAUE_SUMMARY)
    guan = read_json(LAUE_GUAN_SUMMARY)
    focal_m = float(summary["focal_length_mm"]) / 1000.0
    spot_d90_cm = float(summary["spot_d90_cm"])
    radii_cm = [cm(float(row["radius_mm"])) for row in rings]
    energies = [float(row["design_energy_keV"]) for row in rings]
    n_tiles = [int(row["n_tiles"]) for row in rings]
    thickness_mm = [float(row["thickness_mm"]) for row in rings]
    colors = PALETTE[: len(rings)]

    fig = plt.figure(figsize=(15.5, 8.6), facecolor="white")
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 1.55],
        height_ratios=[1.0, 0.72],
        wspace=0.24,
        hspace=0.28,
    )
    ax_front = fig.add_subplot(grid[0, 0])
    ax_process = fig.add_subplot(grid[1, 0])
    ax_side = fig.add_subplot(grid[:, 1])

    # Front aperture: the same five-ring geometry used by the table-driven and Guan-style lines.
    add_front_tiles(ax_front, radii_cm, n_tiles, colors, marker="s", size=13)
    max_radius = max(radii_cm)
    ax_front.scatter([0], [0], s=28, color="#111827", zorder=4)
    ax_front.text(0.18, 0.18, "optical axis", fontsize=8.5, color="#111827")
    ax_front.set_aspect("equal", adjustable="box")
    ax_front.set_xlim(-max_radius - 1.0, max_radius + 1.0)
    ax_front.set_ylim(-max_radius - 1.0, max_radius + 1.0)
    ax_front.set_xlabel("x at lens plane (cm)")
    ax_front.set_ylabel("y at lens plane (cm)")
    ax_front.set_title("Laue entrance plane: Ge(111) five-ring lens")
    ax_front.grid(True, alpha=0.22)
    laue_handles = [
        Line2D([0], [0], color=color, marker="s", lw=1.4, ms=5, label=f"{energy:.0f} keV, r={radius:.2f} cm")
        for energy, radius, color in zip(energies, radii_cm, colors)
    ]
    ax_front.legend(handles=laue_handles, loc="lower left", fontsize=7.2, frameon=True, borderpad=0.45)

    # Local process inset: keep it simple and readable.
    ax_process.set_title("Boundary process schematic")
    ax_process.add_patch(Rectangle((0.0, -0.36), 0.42, 0.72, facecolor="#d1fae5", edgecolor="#047857", lw=1.2))
    ax_process.text(0.21, 0.42, "Ge tile\nz=0", ha="center", va="bottom", fontsize=9, color="#065f46")
    draw_arrow(ax_process, (-0.56, 0.0), (0.0, 0.0), "#1f2937", lw=2.0)
    ax_process.text(-0.55, 0.12, "parallel source\nu=(0,0,+1)", fontsize=8.5, color="#1f2937")
    draw_arrow(ax_process, (0.42, 0.0), (0.92, 0.0), "#6b7280", lw=1.7, alpha=0.8, ls="--")
    ax_process.text(0.61, 0.08, "TRANSMIT", fontsize=8.5, color="#4b5563")
    draw_arrow(ax_process, (0.42, 0.0), (0.92, -0.36), "#b91c1c", lw=2.0)
    ax_process.text(0.58, -0.47, "DIFFRACT\ntoward focus", fontsize=8.5, color="#991b1b")
    ax_process.scatter([0.30], [0.02], s=34, color="#f59e0b", zorder=4)
    ax_process.text(0.08, -0.55, "ABSORB branch is sampled from p_abs", fontsize=8.2, color="#92400e")
    ax_process.set_xlim(-0.68, 1.02)
    ax_process.set_ylim(-0.68, 0.68)
    ax_process.axis("off")

    # Global side view, with the radial axis deliberately expanded.
    ax_side.axvline(0.0, color="#111827", lw=1.2)
    ax_side.axvline(focal_m, color="#b91c1c", lw=1.1, ls="--")
    ax_side.text(0.02, max_radius + 0.55, "lens plane z=0", fontsize=9.5, color="#111827")
    ax_side.text(focal_m - 0.28, max_radius + 0.55, f"focal plane z={focal_m:.1f} m", fontsize=9.5, color="#991b1b")
    source_z = -0.38
    for idx, (row, radius_cm, energy, color) in enumerate(zip(rings, radii_cm, energies, colors)):
        draw_arrow(ax_side, (source_z, radius_cm), (0.0, radius_cm), "#374151", lw=1.2, alpha=0.8, mutation_scale=8)
        ax_side.plot([0.0, focal_m], [radius_cm, 0.0], color=color, lw=2.0, alpha=0.82)
        draw_arrow(
            ax_side,
            (focal_m * 0.58, radius_cm * 0.42),
            (focal_m * 0.70, radius_cm * 0.30),
            color,
            lw=2.0,
            alpha=0.82,
            mutation_scale=8,
        )
        ax_side.scatter([0.0], [radius_cm], s=48, color=color, edgecolor="white", linewidth=0.6, zorder=4)
        label_y = max_radius + 0.33 - 0.30 * idx
        ax_side.plot([0.02, 0.40], [radius_cm, label_y], color=color, lw=0.75, alpha=0.55)
        ax_side.text(0.44, label_y, f"{energy:.0f} keV  r={radius_cm:.2f} cm", fontsize=8.5, color=color, va="center")
    ax_side.scatter([focal_m], [0.0], marker="*", s=160, color="#b91c1c", zorder=5)
    ax_side.vlines(focal_m, -spot_d90_cm / 2.0, spot_d90_cm / 2.0, color="#b91c1c", lw=4, alpha=0.38)
    ax_side.text(
        focal_m * 0.72,
        -0.43,
        f"mainline spot D90={spot_d90_cm:.3f} cm\nGuan-style D90={float(guan['spot_d90_cm']):.3f} cm",
        fontsize=9,
        color="#7f1d1d",
    )
    ax_side.text(
        focal_m * 0.22,
        max_radius + 0.56,
        "Global side view: z is compressed; radial coordinate is expanded",
        fontsize=9,
        color="#4b5563",
    )
    ax_side.text(
        focal_m * 0.43,
        max_radius * 0.58,
        "R = F tan(2 theta_B)\nBragg-selected rings focus to the optical axis",
        fontsize=10,
        color="#111827",
        bbox={"facecolor": "white", "edgecolor": "#e5e7eb", "boxstyle": "round,pad=0.35"},
    )
    ax_side.set_xlim(source_z - 0.06, focal_m + 0.34)
    ax_side.set_ylim(-0.65, max_radius + 1.02)
    ax_side.set_xlabel("z along optical axis (m)")
    ax_side.set_ylabel("radius from optical axis (cm)")
    ax_side.set_title("Laue global 2D focusing schematic")
    ax_side.grid(True, alpha=0.22)

    fig.suptitle(
        "Laue optics overview: source incidence, five-ring geometry, and 8.3 m focus",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.012,
        0.012,
        "Sources: data/laue/ge111_480_550keV_multiring_darwin_config.csv, runs/geant4_laue_multiring_darwin/summary.json",
        fontsize=8,
        color="#4b5563",
    )
    save_figure(fig, "laue_optics_global_2d")


def plot_channel() -> None:
    rings = read_csv(CHANNEL_RING_CONFIG)
    summary = read_json(CHANNEL_SUMMARY)
    wall = read_json(CHANNEL_WALL_SUMMARY)
    focal_m = float(summary["focal_length_mm"]) / 1000.0
    spot_d90_cm = float(summary["spot_d90_cm"])
    radii_cm = [float(row["radius_cm"]) for row in rings]
    bend_deg = [float(row["bending_angle_deg"]) for row in rings]
    length_cm = [float(row["length_cm"]) for row in rings]
    n_tiles = [int(row["n_tiles"]) for row in rings]
    n_bounce = [int(row["n_bounce_calibrated"]) for row in rings]
    colors = PALETTE[: len(rings)]

    fig = plt.figure(figsize=(15.5, 8.6), facecolor="white")
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 1.55],
        height_ratios=[1.0, 0.72],
        wspace=0.24,
        hspace=0.28,
    )
    ax_front = fig.add_subplot(grid[0, 0])
    ax_local = fig.add_subplot(grid[1, 0])
    ax_side = fig.add_subplot(grid[:, 1])

    # Front aperture: four rings with public CAM511-style tile counts.
    add_front_tiles(ax_front, radii_cm, n_tiles, colors, marker="o", size=24)
    max_radius = max(radii_cm)
    ax_front.add_patch(Circle((0, 0), max_radius, fill=False, color="#111827", lw=1.1, ls="--", alpha=0.45))
    ax_front.scatter([0], [0], s=26, color="#111827", zorder=4)
    ax_front.text(0.14, 0.15, "optical axis", fontsize=8.5, color="#111827")
    ax_front.set_aspect("equal", adjustable="box")
    ax_front.set_xlim(-max_radius - 0.8, max_radius + 0.8)
    ax_front.set_ylim(-max_radius - 0.8, max_radius + 0.8)
    ax_front.set_xlabel("x at channel entrance (cm)")
    ax_front.set_ylabel("y at channel entrance (cm)")
    ax_front.set_title("Channel entrance plane: four-ring 511-CAM layout")
    ax_front.grid(True, alpha=0.22)
    channel_handles = [
        Line2D(
            [0],
            [0],
            color=color,
            marker="o",
            lw=1.4,
            ms=5,
            label=f"ring {row['ring_id']}: r={radius:.2f} cm, N={row['n_tiles']}",
        )
        for row, radius, color in zip(rings, radii_cm, colors)
    ]
    ax_front.legend(handles=channel_handles, loc="lower left", fontsize=7.6, frameon=True, borderpad=0.45)

    # Local channel inset: one representative curved spacer with magnified gap.
    ax_local.set_title("Local wall-by-wall path concept, gap magnified")
    s = [i / 120.0 for i in range(121)]
    rep = rings[-1]
    rep_len_cm = float(rep["length_cm"])
    rep_bend = math.radians(float(rep["bending_angle_deg"]))
    center_y = [0.23 * (1.0 - math.cos(rep_bend * t)) / max(1.0e-12, 1.0 - math.cos(rep_bend)) for t in s]
    x = [rep_len_cm * t for t in s]
    upper = [y + 0.11 for y in center_y]
    lower = [y - 0.11 for y in center_y]
    ax_local.fill_between(x, lower, upper, color="#dbeafe", alpha=0.65, edgecolor="#2563eb", linewidth=1.1)
    bounce_x = [rep_len_cm * i / 10.0 for i in range(11)]
    bounce_y = [center_y[min(120, int(120 * i / 10.0))] + (0.085 if i % 2 == 0 else -0.085) for i in range(11)]
    ax_local.plot(bounce_x, bounce_y, color="#0f766e", lw=1.8, marker=".", ms=5)
    draw_arrow(ax_local, (-0.42, center_y[0]), (0.0, center_y[0]), "#374151", lw=1.8, mutation_scale=9)
    draw_arrow(
        ax_local,
        (rep_len_cm, center_y[-1]),
        (rep_len_cm + 0.62, center_y[-1] - 0.12),
        "#0f766e",
        lw=1.8,
        mutation_scale=9,
    )
    ax_local.text(0.08, 0.34, "150 nm Si spacer open path", fontsize=8.3, color="#1d4ed8")
    ax_local.text(1.75, -0.25, "W/Si wall hits sample R/A/T", fontsize=8.3, color="#065f46")
    ax_local.text(rep_len_cm - 0.55, 0.17, f"bend={float(rep['bending_angle_deg']):.2f} deg", fontsize=8.3, color="#111827")
    ax_local.set_xlim(-0.48, rep_len_cm + 0.72)
    ax_local.set_ylim(-0.36, 0.48)
    ax_local.set_xlabel("channel length coordinate (cm)")
    ax_local.set_yticks([])
    ax_local.grid(True, axis="x", alpha=0.18)

    # Global side view.
    ax_side.axvline(0.0, color="#111827", lw=1.2)
    ax_side.axvline(focal_m, color="#b91c1c", lw=1.1, ls="--")
    ax_side.text(0.02, max_radius + 0.55, "channel entrance z=0", fontsize=9.5, color="#111827")
    ax_side.text(focal_m - 0.45, max_radius + 0.55, f"focal plane z={focal_m:.1f} m", fontsize=9.5, color="#991b1b")
    source_z = -0.22
    for idx, (row, radius_cm, bend, length, bounce, color) in enumerate(
        zip(rings, radii_cm, bend_deg, length_cm, n_bounce, colors)
    ):
        draw_arrow(ax_side, (source_z, radius_cm), (0.0, radius_cm), "#374151", lw=1.2, alpha=0.82, mutation_scale=8)

        # Curved channel segment from the wall-by-wall coordinate convention, scaled in true z/r units.
        bend_rad = math.radians(bend)
        length_mm = length * 10.0
        curvature = bend_rad / length_mm
        zs_m: list[float] = []
        rs_cm: list[float] = []
        for j in range(40):
            s_mm = length_mm * j / 39.0
            theta = curvature * s_mm
            if abs(curvature) < 1.0e-18:
                z_mm = s_mm
                r_mm = radius_cm * 10.0
            else:
                z_mm = math.sin(theta) / curvature
                r_mm = radius_cm * 10.0 + (math.cos(theta) - 1.0) / curvature
            zs_m.append(z_mm / 1000.0)
            rs_cm.append(r_mm / 10.0)
        ax_side.plot(zs_m, rs_cm, color=color, lw=4.0, alpha=0.95, solid_capstyle="round")
        ax_side.plot([zs_m[-1], focal_m], [rs_cm[-1], 0.0], color=color, lw=2.0, alpha=0.82)
        draw_arrow(
            ax_side,
            (focal_m * 0.58, rs_cm[-1] * 0.42),
            (focal_m * 0.70, rs_cm[-1] * 0.30),
            color,
            lw=2.0,
            alpha=0.82,
            mutation_scale=8,
        )
        ax_side.scatter([0.0], [radius_cm], s=54, color=color, edgecolor="white", linewidth=0.6, zorder=4)
        label_y = radius_cm + (0.14 if idx % 2 == 0 else -0.24)
        ax_side.text(
            0.08,
            label_y,
            f"r={radius_cm:.2f} cm  L={length:.1f} cm  bend={bend:.2f} deg  N={bounce}",
            fontsize=8.5,
            color=color,
        )

    ax_side.scatter([focal_m], [0.0], marker="*", s=170, color="#b91c1c", zorder=5)
    ax_side.vlines(focal_m, -spot_d90_cm / 2.0, spot_d90_cm / 2.0, color="#b91c1c", lw=5, alpha=0.34)
    ax_side.text(
        focal_m * 0.68,
        -1.95,
        f"calibrated focal envelope D90={spot_d90_cm:.2f} cm\nwall-by-wall public-geometry D90={float(wall['spot_d90_cm']):.2f} cm",
        fontsize=9,
        color="#7f1d1d",
    )
    ax_side.text(source_z + 0.02, max_radius + 0.16, "source generator\nu=(0,0,+1)", fontsize=9, color="#374151")
    ax_side.text(
        focal_m * 0.21,
        max_radius + 0.17,
        "Global side view: z is compressed; radial coordinate is expanded",
        fontsize=9,
        color="#4b5563",
    )
    ax_side.text(
        focal_m * 0.38,
        max_radius * 0.62,
        "Bent W/Si channels progressively deflect photons inward\nthen project surviving EXIT photons to the 12 m focal plane",
        fontsize=10,
        color="#111827",
        bbox={"facecolor": "white", "edgecolor": "#e5e7eb", "boxstyle": "round,pad=0.35"},
    )
    ax_side.set_xlim(source_z - 0.06, focal_m + 0.48)
    ax_side.set_ylim(-2.25, max_radius + 0.82)
    ax_side.set_xlabel("z along optical axis (m)")
    ax_side.set_ylabel("radius from optical axis (cm)")
    ax_side.set_title("Channel global 2D focusing schematic")
    ax_side.grid(True, alpha=0.22)

    fig.suptitle(
        "Channel optics overview: source incidence, four-ring W/Si geometry, and 12 m focus",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.012,
        0.012,
        "Sources: data/channel/cam511_channel_rings.csv, runs/channel/geant4_4ring_multibounce_calibrated/summary.json, runs/channel_wallbywall_rebuild/summary.json",
        fontsize=8,
        color="#4b5563",
    )
    save_figure(fig, "channel_optics_global_2d")


def write_readme() -> None:
    laue = read_json(LAUE_SUMMARY)
    guan = read_json(LAUE_GUAN_SUMMARY)
    channel = read_json(CHANNEL_SUMMARY)
    wall = read_json(CHANNEL_WALL_SUMMARY)
    readme = f"""# Optics global 2D schematics

Generated on 2026-05-24 from local opticsim configuration and run summaries.

## Outputs

- `laue_optics_global_2d.png` / `laue_optics_global_2d.svg`
- `channel_optics_global_2d.png` / `channel_optics_global_2d.svg`

## What the figures show

- The left aperture panel shows the entrance/lens plane ring geometry.
- The right panel is a global side schematic of source incidence and focusing.
- The longitudinal axis is compressed and the radial axis is expanded so the
  global geometry is readable despite meter-scale focal lengths and centimeter-
  scale apertures.
- These are review schematics, not CAD/WRL replacements.

## Source facts used

Laue:

- Ring config: `data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- Focal length: {float(laue["focal_length_mm"]) / 1000.0:.1f} m
- Mainline spot D90: {float(laue["spot_d90_cm"]):.4f} cm
- Guan-style spot D90: {float(guan["spot_d90_cm"]):.4f} cm
- Source convention: primary gamma rays are generated upstream and travel
  approximately along `u=(0,0,+1)` into the lens plane.

Channel:

- Ring config: `data/channel/cam511_channel_rings.csv`
- Focal length: {float(channel["focal_length_mm"]) / 1000.0:.1f} m
- Calibrated Geant4 spot D90: {float(channel["spot_d90_cm"]):.4f} cm
- Public wall-by-wall reconstruction spot D90: {float(wall["spot_d90_cm"]):.4f} cm
- Source convention: primary gamma rays are generated upstream of each selected
  channel tile and travel along `u=(0,0,+1)`.

## Rebuild

```bash
python3 records/2026-05-24_optics_global_schematics/build_optics_global_schematics.py
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    plot_laue()
    plot_channel()
    write_readme()


if __name__ == "__main__":
    main()
