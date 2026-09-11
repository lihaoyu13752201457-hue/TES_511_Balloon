#!/usr/bin/env python3
"""Make the LOOP-1 delayed source-bubble and production-to-W2 figure."""

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
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


FAMILY_COLORS = {
    "n": "#0072B2",
    "p": "#D55E00",
    "alpha": "#009E73",
    "eplus": "#CC79A7",
    "other": "#777777",
}
MATERIAL_COLORS = {
    "Copper": "#E69F00",
    "Nb": "#0072B2",
    "Mu-metal": "#CC79A7",
    "Ag-proxy": "#777777",
    "Other": "#999999",
}
FAMILY_MARKERS = {"n": "o", "p": "^", "alpha": "s", "eplus": "D", "other": "X"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def family_group(value: str) -> str:
    return value if value in ("n", "p", "alpha", "eplus") else "other"


def short_component(value: str) -> str:
    mapping = {
        "MXC_50mK_plate": "MXC plate",
        "Nb_inner_cylinder": "Nb sleeve",
        "MuMetal_outer_cylinder": "Mu sleeve",
        "can_50mK_bottom": "50 mK can",
        "L0_Cu_disk": "L0 Cu",
        "L2_Cu_support": "L2 Cu",
        "L5_Cu_support": "L5 Cu",
        "Ag_sinter_proxy": "Ag proxy",
        "Other": "other volumes",
    }
    return mapping.get(value, value.replace("_", " "))


def aggregate_paths(rows: list[dict[str, str]]) -> list[dict]:
    raw = []
    isotope_rates = defaultdict(float)
    component_rates = defaultdict(float)
    for row in rows:
        rate = float(row["selected_rate_cps_observed_mix"])
        if rate <= 0:
            continue
        isotope_rates[row["isotope"]] += rate
        component_rates[row["component_group"]] += rate
        raw.append(row)
    keep_isotopes = {name for name, _ in sorted(isotope_rates.items(), key=lambda item: -item[1])[:7]}
    keep_components = {name for name, _ in sorted(component_rates.items(), key=lambda item: -item[1])[:8]}
    grouped = defaultdict(float)
    for row in raw:
        path = (
            family_group(row["family"]),
            row["material"] if row["material"] in MATERIAL_COLORS else "Other",
            row["isotope"] if row["isotope"] in keep_isotopes else "other isotopes",
            short_component(row["component_group"]) if row["component_group"] in keep_components else "other volumes",
            "selected W2",
        )
        grouped[path] += float(row["selected_rate_cps_observed_mix"])
    return [{"path": key, "rate": value} for key, value in grouped.items()]


def alluvial(ax, paths: list[dict]) -> None:
    total = math.fsum(path["rate"] for path in paths)
    stages = list(zip(*(path["path"] for path in paths)))
    node_totals = []
    for stage_idx in range(5):
        values = defaultdict(float)
        for item in paths:
            values[item["path"][stage_idx]] += item["rate"]
        node_totals.append(values)

    xs = np.linspace(0.02, 0.98, 5)
    node_bounds: list[dict[str, tuple[float, float]]] = []
    alloc: list[dict[tuple[str, tuple[str, ...]], tuple[float, float]]] = []
    for stage_idx, values in enumerate(node_totals):
        names = sorted(values, key=lambda name: (-values[name], name))
        gap = 0.018 if len(names) > 1 else 0.0
        scale = (1.0 - gap * (len(names) - 1)) / total
        y = 0.0
        bounds = {}
        stage_alloc = {}
        for name in names:
            height = values[name] * scale
            bounds[name] = (y, y + height)
            relevant = [item for item in paths if item["path"][stage_idx] == name]
            relevant.sort(key=lambda item: item["path"])
            cursor = y
            for item in relevant:
                dh = item["rate"] * scale
                stage_alloc[(name, item["path"])] = (cursor, cursor + dh)
                cursor += dh
            y += height + gap
        node_bounds.append(bounds)
        alloc.append(stage_alloc)

    Path = mpath.Path
    for stage_idx in range(4):
        x0, x1 = xs[stage_idx] + 0.012, xs[stage_idx + 1] - 0.012
        dx = (x1 - x0) * 0.45
        for item in paths:
            p = item["path"]
            y00, y01 = alloc[stage_idx][(p[stage_idx], p)]
            y10, y11 = alloc[stage_idx + 1][(p[stage_idx + 1], p)]
            verts = [
                (x0, y00), (x0 + dx, y00), (x1 - dx, y10), (x1, y10),
                (x1, y11), (x1 - dx, y11), (x0 + dx, y01), (x0, y01), (x0, y00),
            ]
            codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
            color = FAMILY_COLORS[p[0]]
            ax.add_patch(mpatches.PathPatch(Path(verts, codes), facecolor=color, edgecolor="none", alpha=0.33, zorder=1))

    stage_titles = ["incident\nfamily", "material", "parent\nisotope", "source\nvolume", "W2"]
    for stage_idx, bounds in enumerate(node_bounds):
        x = xs[stage_idx]
        for name, (y0, y1) in bounds.items():
            height = y1 - y0
            face = "#E8E8E8" if stage_idx else FAMILY_COLORS.get(name, "#999999")
            ax.add_patch(mpatches.Rectangle((x - 0.012, y0), 0.024, height, facecolor=face, edgecolor="#333333", lw=0.5, alpha=0.95, zorder=3))
            pct = 100.0 * node_totals[stage_idx][name] / total
            label = f"{name}\n{pct:.1f}%" if stage_idx not in (1, 3) else f"{name}\n{pct:.1f}%"
            align = "right" if stage_idx in (0, 2, 4) else "left"
            tx = x - 0.017 if align == "right" else x + 0.017
            ax.text(tx, (y0 + y1) / 2, label, ha=align, va="center", fontsize=6.8, color="#111111", zorder=4)
        ax.text(x, 1.035, stage_titles[stage_idx], ha="center", va="bottom", fontsize=8.5, weight="bold")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.02, 1.10)
    ax.axis("off")
    ax.set_title("Observed selected-rate flow (band width = W2 cps)", fontsize=11)


def component_material(name: str) -> str:
    if name == "Nb_inner_cylinder":
        return "Nb"
    if name == "MuMetal_outer_cylinder":
        return "Mu-metal"
    if name == "Ag_sinter_proxy":
        return "Ag-proxy"
    if "Cu" in name or name in ("MXC_50mK_plate", "can_50mK_bottom"):
        return "Copper"
    return "Other"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bubbles", type=Path, required=True)
    parser.add_argument("--key-flow", type=Path, required=True)
    parser.add_argument("--components", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    bubbles = read_csv(args.bubbles)
    key_flow = read_csv(args.key_flow)
    components = read_csv(args.components)
    total_rate = math.fsum(float(row["selected_rate_cps_at_position"]) for row in bubbles)

    fig = plt.figure(figsize=(18.5, 11.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=(0.90, 1.10), height_ratios=(1.08, 0.92))
    bubble_ax = fig.add_subplot(gs[:, 0])
    flow_ax = fig.add_subplot(gs[0, 1])
    coupling_ax = fig.add_subplot(gs[1, 1])

    # Exact magnetic-shell spans in this common IF-x/r projection.
    bubble_ax.add_patch(mpatches.Rectangle((-4.35, 4.25), 8.65, 0.20, facecolor=MATERIAL_COLORS["Mu-metal"], edgecolor=MATERIAL_COLORS["Mu-metal"], alpha=0.14, lw=1.0, label="Mu shell proxy"))
    bubble_ax.add_patch(mpatches.Rectangle((-3.85, 4.00), 7.95, 0.20, facecolor=MATERIAL_COLORS["Nb"], edgecolor=MATERIAL_COLORS["Nb"], alpha=0.14, lw=1.0, label="Nb shell proxy"))
    bubble_ax.add_patch(mpatches.Rectangle((-3.15, 0.0), 6.30, 1.9, facecolor="#F0E442", edgecolor="#8C7A00", alpha=0.12, lw=0.8, label="TES envelope"))

    for row in bubbles:
        family = family_group(row["family"])
        material = row["material"] if row["material"] in MATERIAL_COLORS else "Other"
        rate = float(row["selected_rate_cps_at_position"])
        x = float(row["generic_axis_x_cm"])
        r = float(row["generic_radius_about_IF_x_axis_at_z_minus5p2_cm"])
        high_single = int(row["single_event_high_weight_flag"]) == 1
        bubble_ax.scatter(
            x,
            r,
            s=24.0 + 4200.0 * rate / total_rate,
            marker=FAMILY_MARKERS[family],
            facecolor=MATERIAL_COLORS[material],
            edgecolor="#B2182B" if high_single else "#202020",
            linewidth=1.8 if high_single else 0.55,
            alpha=0.79,
            zorder=4,
        )
    top = sorted(bubbles, key=lambda row: -float(row["selected_rate_cps_at_position"]))[:10]
    offsets = [(7, 7), (7, -13), (-7, 8), (-7, -14), (9, 9), (9, -15), (-9, 10), (-9, -16), (10, 10), (-10, 11)]
    for row, offset in zip(top, offsets):
        label = f"{row['event_ids']}  {short_component(row['component_group'])}\n{row['family']}→{row['isotope']}  {100*float(row['rate_fraction_of_full_delayed']):.2f}%"
        bubble_ax.annotate(
            label,
            (float(row["generic_axis_x_cm"]), float(row["generic_radius_about_IF_x_axis_at_z_minus5p2_cm"])),
            xytext=offset,
            textcoords="offset points",
            fontsize=7.1,
            ha="left" if offset[0] > 0 else "right",
            va="bottom" if offset[1] > 0 else "top",
            arrowprops={"arrowstyle": "-", "color": "#777777", "lw": 0.45},
            zorder=6,
        )
    bubble_ax.set_xlabel("InstrumentFrame x (cm)")
    bubble_ax.set_ylabel("r about TES/magnetic x-axis at IF z = −5.2 cm (cm)")
    bubble_ax.set_title("66 independent delayed source positions; no smoothing\nsize = selected W2 rate, red edge = single-event high weight")
    bubble_ax.set_xlim(-17.5, 16.5)
    bubble_ax.set_ylim(0, 19)
    bubble_ax.grid(True, color="#AAAAAA", lw=0.4, alpha=0.35)

    material_handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor="#222222", markersize=7, label=name) for name, color in MATERIAL_COLORS.items() if name != "Other"]
    family_handles = [Line2D([0], [0], marker=FAMILY_MARKERS[name], color="#222222", linestyle="none", markersize=7, label=name) for name in ("n", "p", "alpha", "eplus", "other")]
    high_handle = Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="#B2182B", markeredgewidth=1.8, markersize=8, label="single-event high weight")
    bubble_ax.legend(handles=material_handles + family_handles + [high_handle], loc="upper right", fontsize=7.5, ncol=2, framealpha=0.90)

    paths = aggregate_paths(key_flow)
    alluvial(flow_ax, paths)

    # Component-level production and coupling remain separate axes/quantities.
    for row in components:
        bq = float(row["day15_activity_Bq"])
        coupling = float(row["W2_per_Bq_on_supported_inventory"])
        rate = float(row["selected_rate_cps_observed_mix"])
        neff = float(row["selected_event_Neff"])
        dominant = float(row["dominant_event_fraction_of_group_rate"])
        material = component_material(row["component_group"])
        low_support = neff < 2.0 or dominant >= 0.5
        marker = "X" if low_support else "o"
        coupling_ax.scatter(
            bq,
            coupling,
            s=35.0 + 1800.0 * rate / total_rate,
            marker=marker,
            facecolor=MATERIAL_COLORS[material],
            edgecolor="#B2182B" if low_support else "#202020",
            linewidth=1.5 if low_support else 0.6,
            alpha=0.82,
            zorder=4,
        )
        coupling_ax.annotate(
            short_component(row["component_group"]),
            (bq, coupling),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=7.4,
            ha="left",
            va="bottom",
        )
    coupling_ax.set_xscale("log")
    coupling_ax.set_yscale("log")
    coupling_ax.set_xlabel("Day-15 production inventory (Bq), component total")
    coupling_ax.set_ylabel("Selected W2 / decay on supported inventory")
    coupling_ax.set_title("Production and detector coupling are distinct\nmarker area = observed W2 cps; X/red = Neff<2 or one event ≥50%")
    coupling_ax.grid(True, which="both", color="#AAAAAA", lw=0.4, alpha=0.35)
    coupling_ax.text(
        0.01,
        0.01,
        "Total transported activity = 1404.131 Bq; selected = 0.05447975 cps; event Neff = 28.75; position Neff = 24.93",
        transform=coupling_ax.transAxes,
        fontsize=8,
        ha="left",
        va="bottom",
    )

    fig.suptitle(
        "S3d-O8 delayed background: discrete source positions and production→W2 coupling",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=220, bbox_inches="tight")
    fig.savefig(args.output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
