#!/usr/bin/env python3
"""Make the LOOP-1 prompt ray/denominator figure without smoothing."""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3d_o8_loop_mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy.stats import beta


EVENT_COLORS = {3883: "#0072B2", 19932: "#D55E00", 8081: "#CC79A7"}
MATERIAL_COLORS = {
    "PlasticScintillator": "#56B4E9",
    "BoratedPolyethylene5wtB": "#999999",
    "BGO": "#009E73",
    "Copper": "#E69F00",
    "Nb": "#0072B2",
    "MuMetal": "#CC79A7",
    "W": "#333333",
}
ACTIVE_VOLUMES = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def cp_upper(k: int, n: int) -> float:
    return 1.0 if k == n else float(beta.ppf(0.95, k + 1, n - k))


def add_rect_band(ax, horizontal: str, r0: float, r1: float, z0: float, z1: float, color: str, alpha: float):
    # Orthographic projection of a cylindrical annulus as two side bands.
    for sgn in (-1, 1):
        lo = -r1 if sgn < 0 else r0
        ax.add_patch(mpatches.Rectangle((lo, z0), r1 - r0, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.7, zorder=0))


def add_disk(ax, radius: float, z0: float, z1: float, color: str, alpha: float, inner: float = 0.0):
    if inner <= 0:
        ax.add_patch(mpatches.Rectangle((-radius, z0), 2 * radius, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.7, zorder=0))
    else:
        add_rect_band(ax, "", inner, radius, z0, z1, color, alpha)


def add_longitudinal_geometry(ax, projected_radius_axis: str):
    add_rect_band(ax, "", 29.0, 30.0, -26.5, 48.0, MATERIAL_COLORS["PlasticScintillator"], 0.16)
    add_disk(ax, 30.0, -27.5, -26.5, MATERIAL_COLORS["PlasticScintillator"], 0.16)
    add_disk(ax, 30.0, 48.0, 49.0, MATERIAL_COLORS["PlasticScintillator"], 0.16)
    add_rect_band(ax, "", 27.0, 29.0, -24.5, 46.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 0.13)
    add_disk(ax, 29.0, -26.5, -24.5, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 0.13)
    add_disk(ax, 29.0, 46.0, 48.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 0.13)
    add_rect_band(ax, "", 21.2, 25.2, -19.4, 40.9, MATERIAL_COLORS["BGO"], 0.20)
    add_disk(ax, 25.2, -22.4, -19.4, MATERIAL_COLORS["BGO"], 0.20)
    add_disk(ax, 25.2, 40.9, 41.9, MATERIAL_COLORS["BGO"], 0.20, inner=20.9)
    if projected_radius_axis == "x":
        # Exact BGO-only negative-x optical opening: 37.96 x 37.96 mm,
        # centered at IF (x,z)=(-12.6,-5.2) cm and extending to the cavity.
        ax.add_patch(mpatches.Rectangle((-25.25, -7.098), 25.3, 3.796, facecolor="white", edgecolor="#A33A2B", alpha=0.96, lw=0.9, ls="--", zorder=1))
        ax.text(-24.5, -2.6, "BGO optical opening", fontsize=7.2, color="#A33A2B", ha="left", va="bottom")
    # Central passive structures in their exact proxy extents.
    ax.add_patch(mpatches.Rectangle((-15.0, -0.3), 30.0, 0.6, facecolor=MATERIAL_COLORS["Copper"], edgecolor=MATERIAL_COLORS["Copper"], alpha=0.25, lw=0.8))
    ax.add_patch(mpatches.Rectangle((-2.2, 0.31), 4.4, 1.8, facecolor=MATERIAL_COLORS["Copper"], edgecolor=MATERIAL_COLORS["Copper"], alpha=0.35, lw=0.8))
    # x-axis magnetic sleeves appear as their projected bounding box.
    ax.add_patch(mpatches.Rectangle((-4.35, -9.65), 8.65, 8.9, fill=False, edgecolor=MATERIAL_COLORS["MuMetal"], lw=1.0, ls="--"))
    ax.add_patch(mpatches.Rectangle((-3.85, -9.4), 7.95, 8.4, fill=False, edgecolor=MATERIAL_COLORS["Nb"], lw=1.0, ls=":"))
    ax.axhline(-5.2, color="#555555", lw=0.5, alpha=0.5)
    ax.set_xlim(-52, 52)
    ax.set_ylim(-53, 55)
    ax.set_aspect("equal", adjustable="box")


def add_cross_section_geometry(ax):
    for radius, color, lw, ls in [
        (30.0, MATERIAL_COLORS["PlasticScintillator"], 2.2, "-"),
        (29.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 2.0, "--"),
        (27.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 1.0, "--"),
        (25.2, MATERIAL_COLORS["BGO"], 3.0, "-"),
        (21.2, MATERIAL_COLORS["BGO"], 1.2, "-"),
    ]:
        ax.add_patch(mpatches.Circle((0, 0), radius, fill=False, edgecolor=color, lw=lw, ls=ls, alpha=0.65, zorder=0))
    # Mask only the BGO arcs in the exact negative-x optical opening, then
    # redraw the full BPE/plastic shells which have no corresponding opening.
    ax.add_patch(mpatches.Rectangle((-25.25, -1.898), 25.3, 3.796, facecolor="white", edgecolor="#A33A2B", alpha=0.96, lw=0.9, ls="--", zorder=1))
    for radius, color, lw, ls in [
        (30.0, MATERIAL_COLORS["PlasticScintillator"], 2.2, "-"),
        (29.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 2.0, "--"),
        (27.0, MATERIAL_COLORS["BoratedPolyethylene5wtB"], 1.0, "--"),
    ]:
        ax.add_patch(mpatches.Circle((0, 0), radius, fill=False, edgecolor=color, lw=lw, ls=ls, alpha=0.65, zorder=2))
    # Magnetic x-axis sleeves at z_IF=-5.2 are two y-bands.
    ax.add_patch(mpatches.Rectangle((-4.35, -4.45), 8.65, 8.9, fill=False, edgecolor=MATERIAL_COLORS["MuMetal"], lw=1.1, ls="--"))
    ax.add_patch(mpatches.Rectangle((-3.85, -4.2), 7.95, 8.4, fill=False, edgecolor=MATERIAL_COLORS["Nb"], lw=1.1, ls=":"))
    # Six TES layer envelopes projected in x-y.
    for xc in (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0):
        ax.add_patch(mpatches.Rectangle((xc - 0.15, -1.8), 0.3, 3.6, facecolor="#F0E442", edgecolor="#8C7A00", alpha=0.28, lw=0.4))
    ax.set_xlim(-52, 52)
    ax.set_ylim(-52, 52)
    ax.set_aspect("equal", adjustable="box")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", type=Path, required=True)
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--event-summary", type=Path, required=True)
    parser.add_argument("--grammage", type=Path, required=True)
    parser.add_argument("--energy", type=Path, required=True)
    parser.add_argument("--direction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    segments = read_csv(args.segments)
    points = read_csv(args.points)
    summaries = {int(row["event_id"]): row for row in read_csv(args.event_summary)}
    grammage = read_csv(args.grammage)
    energy = read_csv(args.energy)
    direction = read_csv(args.direction)

    active_passive = defaultdict(dict)
    for row in grammage:
        if row["role"] == "total":
            active_passive[int(row["event_id"])][row["material"]] = float(row["grammage_to_first_pair_g_cm2"])

    point_map = defaultdict(list)
    for row in points:
        xyz_if = to_if(float(row["x_world_cm"]), float(row["y_world_cm"]), float(row["z_world_cm"]))
        point_map[int(row["event_id"])].append((row, xyz_if))

    fig = plt.figure(figsize=(18.5, 12.2), constrained_layout=True)
    gs = fig.add_gridspec(3, 6, height_ratios=(1.05, 0.12, 0.95))
    ray_axes = [fig.add_subplot(gs[0, 0:2]), fig.add_subplot(gs[0, 2:4]), fig.add_subplot(gs[0, 4:6])]
    path_ax = fig.add_subplot(gs[1, :])
    energy_ax = fig.add_subplot(gs[2, 0:2])
    dir_ax = fig.add_subplot(gs[2, 2:6])
    projections = [(0, 2, "$x_{IF}$", "$z_{IF}$"), (1, 2, "$y_{IF}$", "$z_{IF}$"), (0, 1, "$x_{IF}$", "$y_{IF}$")]

    add_longitudinal_geometry(ray_axes[0], "x")
    add_longitudinal_geometry(ray_axes[1], "y")
    add_cross_section_geometry(ray_axes[2])

    # Draw exact MEGAlib membership segments from INIT to first pair.
    for ax, (ia, ib, xlabel, ylabel) in zip(ray_axes, projections):
        for row in segments:
            event = int(row["ray_id"])
            p0 = to_if(float(row["x0_cm"]), float(row["y0_cm"]), float(row["z0_cm"]))
            p1 = to_if(float(row["x1_cm"]), float(row["y1_cm"]), float(row["z1_cm"]))
            is_active = row["volume"] in ACTIVE_VOLUMES
            if is_active:
                ax.plot([p0[ia], p1[ia]], [p0[ib], p1[ib]], color=MATERIAL_COLORS["BGO"] if row["material"] == "BGO" else MATERIAL_COLORS["PlasticScintillator"], lw=6.0, alpha=0.34, solid_capstyle="round", zorder=3)
            ax.plot([p0[ia], p1[ia]], [p0[ib], p1[ib]], color=EVENT_COLORS[event], lw=1.65, alpha=0.96, zorder=4)

        for event, event_points in point_map.items():
            by_type = defaultdict(list)
            for row, xyz in event_points:
                by_type[row["point_type"]].append((row, xyz))
            marker_spec = {"INIT": ("o", 30), "PAIR": ("X", 72), "ANNI": ("D", 45), "TES_HTsim": ("*", 88)}
            for kind, (marker, size) in marker_spec.items():
                for row, xyz in by_type.get(kind, []):
                    ax.scatter(xyz[ia], xyz[ib], marker=marker, s=size, facecolor=EVENT_COLORS[event] if kind != "TES_HTsim" else "#F0E442", edgecolor="#111111", linewidth=0.65, zorder=7)
            if by_type.get("ANNI") and by_type.get("TES_HTsim"):
                ann = by_type["ANNI"][0][1]
                for _, tes in by_type["TES_HTsim"]:
                    ax.plot([ann[ia], tes[ia]], [ann[ib], tes[ib]], color=EVENT_COLORS[event], lw=1.0, ls="--", alpha=0.7, zorder=5)
        ax.set_xlabel(f"{xlabel} (cm)")
        ax.set_ylabel(f"{ylabel} (cm)")
        ax.grid(True, color="#AAAAAA", lw=0.35, alpha=0.28)

    ray_axes[0].set_title("Orthographic x-z projection")
    ray_axes[1].set_title("Orthographic y-z projection")
    ray_axes[2].set_title("x-y projection; true z=-5.2 cm core slice")

    event_handles = [Line2D([0], [0], color=EVENT_COLORS[e], lw=2.2, label=f"event {e}: {float(summaries[e]['init_energy_keV'])/1000:.3f} MeV") for e in (3883, 19932, 8081)]
    marker_handles = [
        Line2D([0], [0], marker="X", color="none", markerfacecolor="#FFFFFF", markeredgecolor="#111111", markersize=8, label="first PAIR"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#FFFFFF", markeredgecolor="#111111", markersize=6, label="annihilation"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor="#F0E442", markeredgecolor="#111111", markersize=10, label="TES hit"),
    ]
    ray_axes[0].legend(handles=event_handles + marker_handles, loc="upper left", fontsize=8, framealpha=0.88)

    path_text = []
    for event in (3883, 19932, 8081):
        s = summaries[event]
        ap = active_passive[event]
        path_text.append(
            f"{event}: active {ap['ACTIVE_TOTAL']:.2f}, passive {ap['PASSIVE_TOTAL']:.2f} g cm$^{{-2}}$; "
            f"PAIR {s['pair_volume'].replace('_',' ')}; ANNI {s['annihilation_volume'].replace('_',' ')}; "
            f"active edep = 0 keV"
        )
    path_ax.axis("off")
    path_ax.text(0.5, 0.5, "\n".join(path_text), ha="center", va="center", fontsize=8.7, family="DejaVu Sans Mono")

    # Energy denominators.  Bars are incident histories; labels are the discrete numerators.
    labels = [row["energy_range_MeV"].replace("inf", "∞") for row in energy]
    nvals = np.array([int(row["incident_histories_N"]) for row in energy])
    kv = np.array([int(row["veto_survivors_k"]) for row in energy])
    ks = np.array([int(row["step05_survivors_k"]) for row in energy])
    x = np.arange(len(labels))
    bar_colors = ["#BDBDBD" if not (3 <= j <= 5) else "#80CDC1" for j in range(len(labels))]
    energy_ax.bar(x, nvals, color=bar_colors, edgecolor="#444444", lw=0.6)
    energy_ax.set_yscale("log")
    energy_ax.set_ylabel("Incident primary histories N (log scale)")
    energy_ax.set_xlabel("Primary gamma energy (MeV)")
    energy_ax.set_xticks(x, labels, rotation=42, ha="right", fontsize=8)
    energy_ax.set_title("Full incident-energy denominators (132 shards; no conditioning on W2)")
    for j, (n, v, s) in enumerate(zip(nvals, kv, ks)):
        if v:
            energy_ax.text(j, n * 1.12, f"veto {v}; final {s}\n{s}/{n:,}", ha="center", va="bottom", fontsize=8, color="#8B1A1A" if s else "#7A4A00")
    energy_ax.grid(True, axis="y", which="both", color="#AAAAAA", lw=0.35, alpha=0.35)

    # Equal-solid-angle direction denominator, aggregated only over 4-8 MeV.
    cells = defaultdict(lambda: {"n": 0, "v": 0, "s": 0})
    for row in direction:
        if int(row["energy_bin"]) not in (3, 4, 5):
            continue
        key = (int(row["mu_bin"]), int(row["azimuth_bin"]))
        cells[key]["n"] += int(row["incident_histories_N"])
        cells[key]["v"] += int(row["veto_survivors_k"])
        cells[key]["s"] += int(row["step05_survivors_k"])
    grid = np.zeros((4, 8))
    for mu in range(4):
        for az in range(8):
            item = cells[(mu, az)]
            grid[mu, az] = item["s"] / item["n"] if item["n"] else 0.0
    # Binary, discrete fill: no interpolation or smoothing.
    shown = np.where(grid > 0, 1.0, 0.0)
    dir_ax.imshow(shown, cmap=matplotlib.colors.ListedColormap(["#F2F2F2", "#F4A582"]), vmin=0, vmax=1, interpolation="nearest", aspect="auto", extent=(-0.5, 7.5, -0.5, 3.5))
    id_for_cell = {(2, 1): "3883", (0, 6): "19932", (0, 0): "8081 veto-only"}
    for mu in range(4):
        plot_y = 3 - mu
        for az in range(8):
            item = cells[(mu, az)]
            text = f"{item['s']}/{item['n']:,}"
            if (mu, az) in id_for_cell:
                text += f"\n{id_for_cell[(mu, az)]}"
            if item["s"]:
                text += f"\nU95={100*cp_upper(item['s'], item['n']):.3f}%"
            dir_ax.text(az, plot_y, text, ha="center", va="center", fontsize=7.1, color="#111111")
            if item["v"] > item["s"]:
                dir_ax.add_patch(mpatches.Rectangle((az - 0.47, plot_y - 0.47), 0.94, 0.94, fill=False, edgecolor="#E69F00", lw=2.0, ls="--"))
    dir_ax.set_xticks(range(8), [f"{45*a}–{45*(a+1)}°" for a in range(8)], rotation=30, ha="right", fontsize=8)
    dir_ax.set_yticks(range(4), ["μ=0.5..1\nθ=0..60°", "μ=0..0.5\nθ=60..90°", "μ=-0.5..0\nθ=90..120°", "μ=-1..-0.5\nθ=120..180°"], fontsize=8)
    dir_ax.set_xlabel("Azimuth about IF +x, atan2(z,y); each cell = π/8 sr")
    dir_ax.set_ylabel("Equal-solid-angle μ=cos θ bins")
    dir_ax.set_title("4–8 MeV Step05 leak k/N by direction (discrete cells; no smoothing)")
    dir_ax.set_xlim(-0.5, 7.5)
    dir_ax.set_ylim(-0.5, 3.5)
    dir_ax.set_xticks(np.arange(-0.5, 8, 1), minor=True)
    dir_ax.set_yticks(np.arange(-0.5, 4, 1), minor=True)
    dir_ax.grid(which="minor", color="#555555", lw=0.65)
    dir_ax.tick_params(which="minor", bottom=False, left=False)
    dir_ax.text(7.46, -0.42, "orange dashed = veto survivor rejected by Step05", ha="right", va="bottom", fontsize=8, color="#7A4A00")

    fig.suptitle(
        "S3d-O8 prompt leakage: exact geometry rays and full incident denominators\n"
        "3,207,738 primary γ; 3 veto survivors; 2 Step05 W2 events",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=220, bbox_inches="tight")
    fig.savefig(args.output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
