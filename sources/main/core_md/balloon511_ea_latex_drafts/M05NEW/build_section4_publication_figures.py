#!/usr/bin/env python3
"""Build the publication-facing Section 4 geometry and spectrum figures.

The script reads only the current formal compact CSV/JSON products and the two
retained geometry text files.  It does not open SIM/NPZ payloads or job
catalogues, run transport, or alter any simulation product.

Two figures are produced:

* a dimensionally aligned model-A/model-B cold-stage section with selected
  delayed-source positions and current-normalization response diagnostics;
* the day-15 measured TES differential count-rate spectrum before the active
  veto, after the active veto, and after the final Compton selection.

The model-B source-position catalogue predates the final Package-70 family
normalization.  Its event centres and second moments are therefore reweighted
family by family and are required to close exactly to the current formal
``sumw`` and ``sumw2`` values before any manuscript-facing output is written.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_section4_publication_mpl")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

import build_section4_current_results as current


HERE = Path(__file__).resolve().parent
REPO = Path("/home/ubuntu/TES_511_Balloon")
OUT = HERE / "figures" / "section4_current"
REPORT = HERE / "M05_SECTION4_PUBLICATION_FIGURES_20260829.json"

A_ORIGINS = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "59_sg3b_prompt_activation_coupling_20260818"
    / "outputs/02_coupling_analysis/selected_event_lineage.csv"
)
B_ORIGINS = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820"
    / "outputs/05_optv3_delayed_origins/optv3_delayed_selected_events.csv"
)
GEOMETRY_CONTRACT = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "66_m05new_mxc_bpe_veto_review_20260821"
    / "data/cross_section_geometry_contract.csv"
)
A_GEOMETRY = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "68_sg3_minimal_sd_prompt_supplement_20260823"
    / "geometry/DEMO2_DR_v3p5_SG3B.geo"
)
B_GEOMETRY = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.geo"
)

FINAL = "compton_trajectory_veto"
STAGES = ("pre_veto", "combined_active_veto", FINAL)
PHYSICAL_ROWS = (
    ("prompt", "other"),
    ("prompt", "gamma_continuum"),
    ("delayed", "other"),
)
W2_LOW = 510.58
W2_HIGH = 511.42
FORBIDDEN_TASK = "01a02314-a50b-78d2-bb8c-b43ffa350704"

COLORS = {
    "ink": "#222222",
    "muted": "#6B7280",
    "grid": "#D7DEE8",
    "A": "#0072B2",
    "B": "#D55E00",
    "pre": "#333333",
    "active": "#0072B2",
    "final": "#D55E00",
    "copper": "#E69F00",
    "aluminium": "#56B4E9",
    "heavy": "#CC79A7",
    "other": "#7A7A7A",
    "tes": "#B2182B",
    "bgo": "#009E73",
    "bgo_fill": "#CDEBDD",
    "cold": "#A65E2E",
    "cold_fill": "#F1D5B5",
    "w": "#4B5563",
    "al": "#9CA3AF",
    "plastic": "#8C6BB1",
    "bpe": "#6B8E23",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if FORBIDDEN_TASK in str(path):
        raise RuntimeError("refusing to read the excluded task product")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def close(
    actual: float,
    expected: float,
    message: str,
    *,
    rtol: float = 2.0e-10,
    atol: float = 1.0e-14,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise RuntimeError(f"{message}: {actual!r} != {expected!r}")


def configure() -> None:
    current.configure()
    mpl.rcParams.update(
        {
            "font.size": 8.2,
            "axes.titlesize": 9.1,
            "axes.labelsize": 8.2,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "legend.fontsize": 7.2,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.35,
        }
    )


def save(fig: mpl.figure.Figure, basename: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    metadata = {"Title": basename, "Creator": Path(__file__).name}
    for suffix in ("pdf", "svg", "png"):
        path = OUT / f"{basename}.{suffix}"
        kwargs: dict[str, Any] = {"bbox_inches": "tight", "pad_inches": 0.04}
        if suffix == "png":
            kwargs.update({"dpi": 600, "metadata": {"Software": Path(__file__).name}})
        else:
            kwargs["metadata"] = metadata
        fig.savefig(path, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


def panel(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(
        -0.14,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=10.0,
        fontweight="bold",
        va="bottom",
    )


def tidy(ax: mpl.axes.Axes, *, grid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(True, color=COLORS["grid"], lw=0.55, alpha=0.8)
        ax.set_axisbelow(True)


def formal_delayed_by_family(data: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    rows = [
        row
        for row in data["cutflow"]
        if row["stream"] == "delayed"
        and row["component"] == "other"
        and row["window_id"] == current.W2
        and row["stage"] == FINAL
    ]
    result: dict[str, dict[str, float | int]] = {}
    for row in rows:
        family = row["family"]
        require(family not in result, f"duplicate delayed family {family}")
        result[family] = {
            "raw": int(row["selected_raw"]),
            "rate": float(row["sumw_cps"]),
            "variance": float(row["sumw2_cps2"]),
        }
    return result


def classify_region(volume: str) -> str:
    if volume.startswith("ColdPlate_") or volume == "DR_MixingChamber_Cu":
        return "DR/MXC and cold plates"
    near_tokens = (
        "TES_",
        "SubstrateSupport",
        "SH3_Layer",
        "SH3_OptV2_W_Frame",
        "BottomColdPlate",
        "ColdFinger",
        "50mK",
        "Bi_MXC_TES",
    )
    if any(token in volume for token in near_tokens):
        return "TES-near structures"
    return "Other structures"


def material_group(material: str) -> str:
    value = material.lower()
    if "copper" in value:
        return "Copper"
    if "alum" in value:
        return "Aluminium"
    if value in {"bi", "bismuth", "ta", "tantalum", "w", "tungsten"}:
        return "Bi/Ta/W"
    return "Other"


def load_a_origins(data: dict[str, Any]) -> list[dict[str, Any]]:
    formal = formal_delayed_by_family(data)
    rows: list[dict[str, Any]] = []
    for row in read_csv(A_ORIGINS):
        if row["stream"] != "delayed":
            continue
        rows.append(
            {
                "family": row["family"],
                "volume": row["source_volume"],
                "material": row["source_material"],
                "material_group": material_group(row["source_material"]),
                "region": classify_region(row["source_volume"]),
                "x": float(row["source_xprime_cm"]),
                "z": float(row["source_zprime_cm"]),
                "rate": float(row["day15_noacc_cps"]),
                "variance": float(row["day15_noacc_cps"]) ** 2,
            }
        )
    require(len(rows) == 394, f"model A origin row count changed: {len(rows)}")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    for family, values in by_family.items():
        target = formal[family]
        require(len(values) == target["raw"], f"model A {family} origin/raw mismatch")
        close(math.fsum(row["rate"] for row in values), float(target["rate"]), f"model A {family} rate closure")
        close(math.fsum(row["variance"] for row in values), float(target["variance"]), f"model A {family} variance closure")
    return rows


def load_b_origins(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    formal = formal_delayed_by_family(data)
    raw_rows = read_csv(B_ORIGINS)
    require(len(raw_rows) == 111, f"model B origin row count changed: {len(raw_rows)}")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        grouped[row["family"]].append(row)

    scales: dict[str, dict[str, float | int]] = {}
    for family, target in formal.items():
        values = grouped.get(family, [])
        require(len(values) == target["raw"], f"model B {family} origin/raw mismatch")
        if not values:
            require(float(target["rate"]) == 0.0 and float(target["variance"]) == 0.0, f"model B {family} empty-family mismatch")
            continue
        old_rate = math.fsum(float(row["day15_event_weight_cps"]) for row in values)
        old_variance = math.fsum(float(row["day15_event_weight_cps"]) ** 2 for row in values)
        require(old_rate > 0.0 and old_variance > 0.0, f"model B {family} invalid old moments")
        scales[family] = {
            "raw": len(values),
            "old_rate": old_rate,
            "formal_rate": float(target["rate"]),
            "rate_scale": float(target["rate"]) / old_rate,
            "old_variance": old_variance,
            "formal_variance": float(target["variance"]),
            "variance_scale": float(target["variance"]) / old_variance,
        }

    angle = math.radians(45.0)
    cosine, sine = math.cos(angle), math.sin(angle)
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        family = row["family"]
        scale = scales[family]
        old_weight = float(row["day15_event_weight_cps"])
        x_world = float(row["x_cm"])
        z_world = float(row["z_cm"])
        rows.append(
            {
                "family": family,
                "volume": row["source_volume"],
                "material": row["source_material"],
                "material_group": material_group(row["source_material"]),
                "region": classify_region(row["source_volume"]),
                "x": cosine * x_world - sine * z_world,
                "z": sine * x_world + cosine * z_world,
                "rate": old_weight * float(scale["rate_scale"]),
                "variance": old_weight * old_weight * float(scale["variance_scale"]),
            }
        )

    for family, values in grouped.items():
        normalized = [row for row in rows if row["family"] == family]
        target = formal[family]
        close(math.fsum(row["rate"] for row in normalized), float(target["rate"]), f"model B {family} rate closure")
        close(math.fsum(row["variance"] for row in normalized), float(target["variance"]), f"model B {family} variance closure")
    close(
        math.fsum(row["rate"] for row in rows),
        math.fsum(float(item["rate"]) for item in formal.values()),
        "model B total reweighted origin rate",
    )
    close(
        math.fsum(row["variance"] for row in rows),
        math.fsum(float(item["variance"]) for item in formal.values()),
        "model B total reweighted origin variance",
    )
    return rows, scales


def region_summary(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"raw": 0, "rate": 0.0, "variance": 0.0}
    )
    for row in rows:
        item = grouped[row["region"]]
        item["raw"] = int(item["raw"]) + 1
        item["rate"] = float(item["rate"]) + float(row["rate"])
        item["variance"] = float(item["variance"]) + float(row["variance"])
    for item in grouped.values():
        item["sigma"] = math.sqrt(float(item["variance"]))
    return dict(grouped)


def material_summary(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"raw": 0, "rate": 0.0, "variance": 0.0}
    )
    for row in rows:
        item = grouped[row["material_group"]]
        item["raw"] = int(item["raw"]) + 1
        item["rate"] = float(item["rate"]) + float(row["rate"])
        item["variance"] = float(item["variance"]) + float(row["variance"])
    for item in grouped.values():
        item["sigma"] = math.sqrt(float(item["variance"]))
    return dict(grouped)


def draw_plate(
    ax: mpl.axes.Axes,
    z: float,
    radius: float,
    label: str,
    *,
    show_label: bool,
) -> None:
    ax.add_patch(
        Rectangle(
            (-radius, z - 0.20),
            2 * radius,
            0.40,
            facecolor=COLORS["cold_fill"],
            edgecolor=COLORS["cold"],
            lw=0.75,
            hatch="///",
            zorder=2,
        )
    )
    if show_label:
        ax.text(
            radius + 0.55,
            z,
            label,
            va="center",
            fontsize=6.2,
            color=COLORS["cold"],
            clip_on=True,
        )


def draw_common_cold_stages(ax: mpl.axes.Axes, *, show_labels: bool) -> None:
    for z, radius, label in (
        (0.0, 15.0, "MXC 50 mK Cu plate"),
        (5.0, 15.0, "0.1 K"),
        (11.0, 15.0, "0.7 K"),
        (20.0, 17.5, "4 K"),
        (29.0, 17.5, "60 K"),
    ):
        draw_plate(ax, z, radius, label, show_label=show_labels)
    ax.add_patch(
        Rectangle(
            (-2.2, 0.30),
            4.4,
            1.8,
            facecolor="#D9A57D",
            edgecolor=COLORS["cold"],
            lw=0.8,
            hatch="..",
            zorder=3,
        )
    )


def draw_tes_stack(
    ax: mpl.axes.Axes,
    x_positions: list[float],
    z_center: float,
) -> tuple[float, float]:
    for index, x in enumerate(x_positions):
        ax.add_patch(
            Rectangle(
                (x - 0.15, z_center - 1.8),
                0.30,
                3.60,
                facecolor=COLORS["tes"],
                edgecolor="white",
                lw=0.38,
                zorder=8,
            )
        )
        if index in (0, 5):
            ax.text(x, z_center - 2.1, f"L{index}", ha="center", va="top", fontsize=5.6, color=COLORS["tes"])
    x0, x1 = min(x_positions) - 0.35, max(x_positions) + 0.35
    ax.add_patch(
        Rectangle(
            (x0, z_center - 2.05),
            x1 - x0,
            4.10,
            fill=False,
            edgecolor=COLORS["tes"],
            lw=0.9,
            zorder=8,
        )
    )
    return x0, x1


def draw_model_a(
    ax: mpl.axes.Axes,
    *,
    annotations: bool,
    cold_labels: bool,
) -> None:
    draw_common_cold_stages(ax, show_labels=cold_labels)
    # Current full-wrap BGO, including the retained detector-side window.
    for x0 in (-25.2, 21.2):
        if x0 < 0:
            spans = ((-19.4, -7.1), (-3.3, 34.0))
        else:
            spans = ((-19.4, 34.0),)
        for z0, z1 in spans:
            ax.add_patch(
                Rectangle(
                    (x0, z0),
                    4.0,
                    z1 - z0,
                    facecolor=COLORS["bgo_fill"],
                    edgecolor=COLORS["bgo"],
                    lw=0.9,
                    zorder=1,
                )
            )
    ax.add_patch(Rectangle((-25.2, -22.4), 50.4, 3.0, facecolor=COLORS["bgo_fill"], edgecolor=COLORS["bgo"], lw=0.9, zorder=1))
    # Retained BPE and plastic channels are outlines so that they do not mask origins.
    for x0 in (-29.0, 27.0):
        ax.add_patch(Rectangle((x0, -20.0), 2.0, 54.0, fill=False, edgecolor=COLORS["bpe"], lw=0.75, ls=(0, (4, 2)), zorder=1))
    for x0 in (-30.0, 29.0):
        ax.add_patch(Rectangle((x0, -20.0), 1.0, 54.0, fill=False, edgecolor=COLORS["plastic"], lw=0.75, ls=(0, (1.5, 1.5)), zorder=1))
    # W multihole collimator in the BGO side-window aperture.
    ax.add_patch(Rectangle((-26.30, -7.10), 0.80, 3.80, facecolor=COLORS["w"], edgecolor=COLORS["ink"], lw=0.65, zorder=6))
    for z in np.linspace(-6.85, -3.55, 10):
        ax.plot([-26.28, -25.52], [z, z], color="white", lw=0.35, zorder=7)
    # Six active layers and representative Cu support rings.
    x_positions = [-3.0, -1.8, -0.6, 0.6, 1.8, 3.0]
    draw_tes_stack(ax, x_positions, -5.2)
    for x in x_positions:
        ax.add_patch(Rectangle((x + 0.24, -8.0), 0.20, 1.95, facecolor=COLORS["copper"], edgecolor="#8A5800", lw=0.35, zorder=7))
        ax.add_patch(Rectangle((x + 0.24, -4.35), 0.20, 1.95, facecolor=COLORS["copper"], edgecolor="#8A5800", lw=0.35, zorder=7))
    ax.plot([-25.4, -3.4], [-5.2, -5.2], color=COLORS["muted"], lw=0.8, ls=(0, (5, 3)), zorder=5)
    if annotations:
        ax.annotate("W multihole aperture", xy=(-25.9, -5.2), xytext=(-21.0, -12.0), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["w"]}, color=COLORS["w"])
        ax.annotate("six TES layers", xy=(0.0, -5.2), xytext=(2.5, -11.1), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["tes"]}, color=COLORS["tes"])
        ax.annotate("BGO side-window", xy=(-23.2, -7.4), xytext=(-15.0, -13.4), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["bgo"]}, color=COLORS["bgo"])
        ax.annotate("L2 Cu support ring", xy=(-1.35, -3.06), xytext=(-12.5, -9.2), fontsize=5.9, arrowprops={"arrowstyle": "->", "lw": 0.58, "color": "#8A5800"}, color="#8A5800")
        ax.annotate("L0 Cu heat-sink ring", xy=(3.31, -2.90), xytext=(5.2, 1.8), fontsize=5.9, arrowprops={"arrowstyle": "->", "lw": 0.58, "color": "#8A5800"}, color="#8A5800")


def draw_model_b(
    ax: mpl.axes.Axes,
    *,
    annotations: bool,
    cold_labels: bool,
) -> None:
    draw_common_cold_stages(ax, show_labels=cold_labels)
    # Five nested Al chimney shells, shown as their x'-z' envelope intersections.
    shells = (
        (-35.35, 3.95, 4.00, 4.20),
        (-35.30, 4.35, 4.45, 4.75),
        (-35.30, 4.90, 5.00, 5.30),
        (-35.25, 5.45, 5.55, 5.85),
        (-35.20, 5.90, 6.10, 6.60),
    )
    for center, half_length, inner, outer in shells:
        x0, x1 = center - half_length, center + half_length
        for z0 in (-2.8 - outer, -2.8 + inner):
            height = outer - inner
            ax.add_patch(Rectangle((x0, z0), x1 - x0, height, facecolor="#ECEFF2", edgecolor=COLORS["al"], lw=0.5, zorder=2))
    # BGO side shell, front optical annulus and rear cold-port annulus.
    for z0 in (-13.5, 3.9):
        ax.add_patch(Rectangle((-41.7, z0), 13.0, 4.0, facecolor=COLORS["bgo_fill"], edgecolor=COLORS["bgo"], lw=0.9, zorder=1))
    for z0, height in ((-13.5, 7.7), (0.2, 7.7)):
        ax.add_patch(Rectangle((-45.7, z0), 4.0, height, facecolor=COLORS["bgo_fill"], edgecolor=COLORS["bgo"], lw=0.9, zorder=1))
    for z0, height in ((-13.5, 9.95), (-2.05, 9.95)):
        ax.add_patch(Rectangle((-28.7, z0), 4.0, height, facecolor=COLORS["bgo_fill"], edgecolor=COLORS["bgo"], lw=0.9, zorder=1))
    # W square-frame top and bottom bars at the optical entrance.
    ax.add_patch(Rectangle((-45.7, -5.80), 2.0, 0.30, facecolor=COLORS["w"], edgecolor=COLORS["ink"], lw=0.55, zorder=6))
    ax.add_patch(Rectangle((-45.7, -0.10), 2.0, 0.30, facecolor=COLORS["w"], edgecolor=COLORS["ink"], lw=0.55, zorder=6))
    x_positions = [-38.55, -37.35, -36.15, -34.95, -33.75, -32.55]
    draw_tes_stack(ax, x_positions, -2.8)
    for x in x_positions:
        ax.add_patch(Rectangle((x + 0.24, -5.6), 0.20, 1.95, facecolor=COLORS["copper"], edgecolor="#8A5800", lw=0.35, zorder=7))
        ax.add_patch(Rectangle((x + 0.24, -1.95), 0.20, 1.95, facecolor=COLORS["copper"], edgecolor="#8A5800", lw=0.35, zorder=7))
    # The retained cold finger connects the local TES plate to the MXC plate.
    ax.plot([-32.15, 6.05], [-2.8, -2.8], color=COLORS["copper"], lw=1.1, zorder=5)
    ax.plot([6.05, 6.05], [-2.8, -0.2], color=COLORS["copper"], lw=1.1, zorder=5)
    if annotations:
        ax.annotate("nested Al chimney", xy=(-35.2, 3.8), xytext=(-25.0, 6.7), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["al"]}, color=COLORS["muted"])
        ax.annotate("local BGO", xy=(-40.0, 5.8), xytext=(-27.5, 4.7), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["bgo"]}, color=COLORS["bgo"])
        ax.annotate("W frame", xy=(-44.7, -0.05), xytext=(-42.5, -11.6), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["w"]}, color=COLORS["w"])
        ax.annotate("six TES layers", xy=(-35.55, -2.8), xytext=(-28.3, -9.0), fontsize=6.2, arrowprops={"arrowstyle": "->", "lw": 0.65, "color": COLORS["tes"]}, color=COLORS["tes"])
        ax.annotate("Cu cold finger", xy=(-15.0, -2.8), xytext=(-12.5, -7.1), fontsize=6.1, arrowprops={"arrowstyle": "->", "lw": 0.6, "color": COLORS["copper"]}, color="#8A5800")
    ax.plot([-49.0, -30.0], [-2.8, -2.8], color=COLORS["muted"], lw=0.8, ls=(0, (5, 3)), zorder=5)


def plot_origins(
    ax: mpl.axes.Axes,
    rows: list[dict[str, Any]],
    global_max_weight: float,
) -> None:
    styles = {
        "Copper": (COLORS["copper"], "o"),
        "Aluminium": (COLORS["aluminium"], "s"),
        "Bi/Ta/W": (COLORS["heavy"], "^"),
        "Other": (COLORS["other"], "D"),
    }
    for material, (color, marker) in styles.items():
        selected = [row for row in rows if row["material_group"] == material]
        if not selected:
            continue
        sizes = [max(3.5, 70.0 * float(row["rate"]) / global_max_weight) for row in selected]
        ax.scatter(
            [row["x"] for row in selected],
            [row["z"] for row in selected],
            s=sizes,
            c=color,
            marker=marker,
            alpha=0.64,
            edgecolors="white",
            linewidths=0.28,
            zorder=10,
            rasterized=False,
        )


def ratio_with_sigma(
    a: float,
    sa: float,
    b: float,
    sb: float,
) -> tuple[float, float]:
    require(a > 0.0 and b > 0.0, "ratio inputs must be positive")
    ratio = b / a
    sigma = ratio * math.sqrt((sa / a) ** 2 + (sb / b) ** 2)
    return ratio, sigma


def build_geometry_response(
    data: dict[str, dict[str, Any]],
) -> tuple[list[Path], dict[str, Any]]:
    contract_rows = read_csv(GEOMETRY_CONTRACT)
    tes_contract = {
        model: sorted(
            [row for row in contract_rows if row["geometry"] == geometry and row["kind"] == "TES_active_layer"],
            key=lambda row: row["component"],
        )
        for model, geometry in (("A", "SG3B"), ("B", "SH3_OptV3"))
    }
    require(len(tes_contract["A"]) == 6 and len(tes_contract["B"]) == 6, "TES geometry contract changed")
    a_origins = load_a_origins(data["A"])
    b_origins, b_scales = load_b_origins(data["B"])
    a_regions, b_regions = region_summary(a_origins), region_summary(b_origins)
    a_materials, b_materials = material_summary(a_origins), material_summary(b_origins)

    fig = plt.figure(figsize=(7.20, 6.15), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=(1.0, 1.0), hspace=0.12, wspace=0.10)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1], sharex=ax_a, sharey=ax_a)
    ax_a_zoom = fig.add_subplot(grid[1, 0])
    ax_b_zoom = fig.add_subplot(grid[1, 1], sharey=ax_a_zoom)

    draw_model_a(ax_a, annotations=False, cold_labels=False)
    draw_model_b(ax_b, annotations=False, cold_labels=False)
    draw_model_a(ax_a_zoom, annotations=True, cold_labels=True)
    draw_model_b(ax_b_zoom, annotations=True, cold_labels=False)
    global_max_weight = max(float(row["rate"]) for row in a_origins + b_origins)
    plot_origins(ax_a, a_origins, global_max_weight)
    plot_origins(ax_b, b_origins, global_max_weight)
    plot_origins(ax_a_zoom, a_origins, global_max_weight)
    plot_origins(ax_b_zoom, b_origins, global_max_weight)
    for ax, title in ((ax_a, "Mass model A"), (ax_b, "Mass model B")):
        ax.set_xlim(-53.0, 33.0)
        ax.set_ylim(-21.0, 34.0)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(r"Instrument $x'$ (cm)")
        ax.set_title(title, pad=4)
        ax.grid(True, color=COLORS["grid"], lw=0.45, alpha=0.75)
        ax.set_axisbelow(True)
        ax.tick_params(length=2.8)
    ax_a.set_ylabel(r"Instrument $z'$ (cm)")
    ax_b.tick_params(labelleft=False)
    panel(ax_a, "(a)")
    panel(ax_b, "(b)")

    for ax, xlim, title in (
        (ax_a_zoom, (-28.5, 15.5), "Model A detector neighborhood"),
        (ax_b_zoom, (-48.5, -4.5), "Model B detector neighborhood"),
    ):
        ax.set_xlim(*xlim)
        ax.set_ylim(-15.0, 8.0)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(r"Instrument $x'$ (cm)")
        ax.set_title(title, pad=4)
        ax.grid(True, color=COLORS["grid"], lw=0.45, alpha=0.75)
        ax.set_axisbelow(True)
        ax.tick_params(length=2.8)
    ax_a_zoom.set_ylabel(r"Instrument $z'$ (cm)")
    ax_b_zoom.tick_params(labelleft=False)
    panel(ax_a_zoom, "(c)")
    panel(ax_b_zoom, "(d)")

    material_handles = [
        Line2D([0], [0], marker=marker, color="none", markerfacecolor=color, markeredgecolor="white", markersize=5.2, label=label)
        for label, color, marker in (
            ("Cu origin", COLORS["copper"], "o"),
            ("Al origin", COLORS["aluminium"], "s"),
            ("Bi/Ta/W origin", COLORS["heavy"], "^"),
            ("other origin", COLORS["other"], "D"),
        )
    ]
    structure_handles = [
        Patch(facecolor=COLORS["tes"], edgecolor="white", label="TES"),
        Patch(facecolor=COLORS["cold_fill"], edgecolor=COLORS["cold"], hatch="///", label="Cu cold plate"),
        Patch(facecolor=COLORS["bgo_fill"], edgecolor=COLORS["bgo"], label="active BGO"),
        Patch(facecolor=COLORS["w"], edgecolor=COLORS["ink"], label="W aperture/frame"),
    ]
    fig.legend(
        handles=material_handles + structure_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.045),
        ncol=4,
        frameon=False,
        handlelength=1.2,
        columnspacing=1.15,
    )

    geometry_paths = save(fig, "fig09_geometry_response_detailed")

    categories = ("DR/MXC and cold plates", "TES-near structures", "Other structures")
    fig_response, (ax_regions, ax_ratios) = plt.subplots(
        1,
        2,
        figsize=(7.20, 2.85),
        constrained_layout=True,
        gridspec_kw={"width_ratios": (1.0, 1.12)},
    )
    fig_response.set_constrained_layout_pads(w_pad=0.05, h_pad=0.04, wspace=0.08, hspace=0.04)
    y = np.arange(len(categories), dtype=float)
    offsets = {"A": -0.13, "B": 0.13}
    for model, summaries, color, marker in (
        ("A", a_regions, COLORS["A"], "o"),
        ("B", b_regions, COLORS["B"], "s"),
    ):
        values = np.array([float(summaries[category]["rate"]) for category in categories])
        errors = np.array([float(summaries[category]["sigma"]) for category in categories])
        ax_regions.errorbar(
            values,
            y + offsets[model],
            xerr=errors,
            fmt=marker,
            color=color,
            mfc="white",
            mew=0.9,
            ms=4.4,
            capsize=2,
            elinewidth=1.0,
            label=f"Model {model}",
        )
    ax_regions.set_xscale("log")
    ax_regions.set_xlim(2.0e-5, 4.5e-2)
    ax_regions.set_yticks(y, ["Cold stages", "TES-near", "Other"])
    ax_regions.invert_yaxis()
    ax_regions.set_xlabel(r"Day-15 final delayed rate (s$^{-1}$)")
    ax_regions.set_title("Selected delayed-source regions")
    ax_regions.legend(frameon=False, loc="lower right")
    tidy(ax_regions)
    panel(ax_regions, "(a)")

    a_final = current.aggregate(data["A"]["cutflow"], window_id=current.W2, stage=FINAL)
    b_final = current.aggregate(data["B"]["cutflow"], window_id=current.W2, stage=FINAL)
    a_delayed = current.physical_stream_aggregate(data["A"]["cutflow"], "delayed", window_id=current.W2, stage=FINAL)
    b_delayed = current.physical_stream_aggregate(data["B"]["cutflow"], "delayed", window_id=current.W2, stage=FINAL)
    a_cold, b_cold = a_regions[categories[0]], b_regions[categories[0]]
    a_cu, b_cu = a_materials["Copper"], b_materials["Copper"]
    a_aeff = float(data["A"]["summary"]["signal_proxy"]["aeff_cm2"])
    b_aeff = float(data["B"]["summary"]["signal_proxy"]["aeff_cm2"])
    a_aeff_sigma = float(data["A"]["summary"]["signal_proxy"]["aeff_sigma_cm2"])
    b_aeff_sigma = float(data["B"]["summary"]["signal_proxy"]["aeff_sigma_cm2"])

    ratio_items = [
        ("Cold-stage delayed", ratio_with_sigma(float(a_cold["rate"]), float(a_cold["sigma"]), float(b_cold["rate"]), float(b_cold["sigma"]))),
        ("Cu-derived delayed", ratio_with_sigma(float(a_cu["rate"]), float(a_cu["sigma"]), float(b_cu["rate"]), float(b_cu["sigma"]))),
        ("All delayed", ratio_with_sigma(float(a_delayed["rate_cps"]), float(a_delayed["sigma_cps"]), float(b_delayed["rate_cps"]), float(b_delayed["sigma_cps"]))),
        ("Total 511-keV-window background", ratio_with_sigma(float(a_final["rate_cps"]), float(a_final["sigma_cps"]), float(b_final["rate_cps"]), float(b_final["sigma_cps"]))),
        (r"Signal $A_{\rm eff}$", ratio_with_sigma(a_aeff, a_aeff_sigma, b_aeff, b_aeff_sigma)),
    ]
    ratio_y = np.arange(len(ratio_items), dtype=float)
    ratio_values = np.array([item[1][0] for item in ratio_items])
    ratio_errors = np.array([item[1][1] for item in ratio_items])
    ax_ratios.errorbar(
        ratio_values,
        ratio_y,
        xerr=ratio_errors,
        fmt="o",
        color=COLORS["B"],
        mfc="white",
        mew=1.0,
        ms=4.5,
        capsize=2,
        elinewidth=1.0,
    )
    ax_ratios.axvline(1.0, color=COLORS["muted"], lw=0.9, ls="--")
    ax_ratios.set_xscale("log")
    ax_ratios.set_xlim(2.0e-3, 1.5)
    ax_ratios.set_yticks(ratio_y, [item[0] for item in ratio_items])
    ax_ratios.invert_yaxis()
    ax_ratios.set_xlabel("Model B / model A")
    ax_ratios.set_title("Design-response ratios")
    tidy(ax_ratios)
    panel(ax_ratios, "(b)")

    response_paths = save(fig_response, "fig09b_geometry_response_rates")
    paths = geometry_paths + response_paths
    report = {
        "model_B_family_reweight": b_scales,
        "model_A_regions": a_regions,
        "model_B_regions_current_reweighted": b_regions,
        "model_A_materials": a_materials,
        "model_B_materials_current_reweighted": b_materials,
        "B_over_A": {
            label: {"value": value, "sigma": sigma}
            for label, (value, sigma) in ratio_items
        },
        "geometry_contract_tes_x_ranges_cm": {
            model: [
                min(float(row["x_min_cm"]) for row in rows),
                max(float(row["x_max_cm"]) for row in rows),
            ]
            for model, rows in tes_contract.items()
        },
    }
    return paths, report


def selected_spectrum_rows(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    result = [
        row
        for row in rows
        if row["stage"] in STAGES
        and (row["stream"], row["component"]) in PHYSICAL_ROWS
    ]
    require(len(result) == 3 * 3 * 280, f"unexpected selected spectrum row count: {len(result)}")
    # Explicit physical-branch aggregation must close to the file's all/all rows.
    all_rows = {
        (row["stage"], float(row["energy_low_keV"])): row
        for row in rows
        if row["stage"] in STAGES and row["stream"] == "all" and row["component"] == "all"
    }
    grouped: dict[tuple[str, float], list[dict[str, str]]] = defaultdict(list)
    for row in result:
        grouped[(row["stage"], float(row["energy_low_keV"]))].append(row)
    require(set(grouped) == set(all_rows), "physical/all spectrum key coverage mismatch")
    for key, values in grouped.items():
        close(math.fsum(float(row["sumw_cps"]) for row in values), float(all_rows[key]["sumw_cps"]), f"spectrum rate closure {key}")
        close(math.fsum(float(row["sumw2_cps2"]) for row in values), float(all_rows[key]["sumw2_cps2"]), f"spectrum variance closure {key}")
    return result


def spectrum_arrays(
    rows: list[dict[str, str]],
    stage: str,
    factor: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    selected = [row for row in rows if row["stage"] == stage]
    by_bin: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in selected:
        by_bin[float(row["energy_low_keV"])].append(row)
    lows = sorted(by_bin)
    require(len(lows) == 280, f"{stage}: expected 280 native bins")
    native_width = 0.25
    require(len(lows) % factor == 0, f"{stage}: invalid rebin factor")
    edges: list[float] = []
    rates: list[float] = []
    errors: list[float] = []
    raw: list[int] = []
    for start in range(0, len(lows), factor):
        chunk = lows[start : start + factor]
        if not edges:
            edges.append(chunk[0])
        edges.append(chunk[-1] + native_width)
        values = [row for low in chunk for row in by_bin[low]]
        width = native_width * factor
        rates.append(math.fsum(float(row["sumw_cps"]) for row in values) / width)
        errors.append(math.sqrt(math.fsum(float(row["sumw2_cps2"]) for row in values)) / width)
        raw.append(sum(int(row["selected_raw"]) for row in values))
    return np.asarray(edges), np.asarray(rates), np.asarray(errors), np.asarray(raw)


def positive(values: np.ndarray) -> np.ndarray:
    return np.where(values > 0.0, values, np.nan)


def build_day15_spectra(
    data: dict[str, dict[str, Any]],
) -> tuple[list[Path], dict[str, Any]]:
    spectra = {
        model: selected_spectrum_rows(Path(data[model]["input_paths"]["measured_energy_diagnostic"]))
        for model in ("A", "B")
    }
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.20, 5.35),
        constrained_layout=True,
        sharey="row",
        gridspec_kw={"height_ratios": (1.0, 1.0)},
    )
    fig.set_constrained_layout_pads(w_pad=0.04, h_pad=0.04, wspace=0.06, hspace=0.08)
    stage_style = {
        "pre_veto": (COLORS["pre"], "-", "Pre-veto"),
        "combined_active_veto": (COLORS["active"], "--", "After active veto"),
        FINAL: (COLORS["final"], "-.", "After Compton selection"),
    }
    report: dict[str, Any] = {}

    for column, model in enumerate(("A", "B")):
        broad_ax = axes[0, column]
        zoom_ax = axes[1, column]
        report[model] = {"integrated_480_550_cps": {}}
        for stage in STAGES:
            color, linestyle, label = stage_style[stage]
            edges, values, errors, _ = spectrum_arrays(spectra[model], stage, factor=4)
            broad_ax.stairs(positive(values), edges, color=color, ls=linestyle, lw=1.25, label=label)
            centers = 0.5 * (edges[:-1] + edges[1:])
            sparse = np.arange(2, len(centers), 7)
            valid = sparse[values[sparse] > 0.0]
            if stage != FINAL:
                broad_ax.errorbar(
                    centers[valid],
                    values[valid],
                    yerr=errors[valid],
                    fmt="none",
                    ecolor=color,
                    elinewidth=0.55,
                    alpha=0.65,
                    capsize=0,
                )
            else:
                lower = np.where(values > 0.0, np.maximum(values - errors, values * 0.08), np.nan)
                upper = np.where(values > 0.0, values + errors, np.nan)
                broad_ax.fill_between(centers, lower, upper, step="mid", color=color, alpha=0.18, lw=0)
            integrated = math.fsum(float(row["sumw_cps"]) for row in spectra[model] if row["stage"] == stage)
            variance = math.fsum(float(row["sumw2_cps2"]) for row in spectra[model] if row["stage"] == stage)
            report[model]["integrated_480_550_cps"][stage] = {
                "rate": integrated,
                "sigma": math.sqrt(variance),
            }

            native_edges, native_values, native_errors, _ = spectrum_arrays(spectra[model], stage, factor=1)
            native_centers = 0.5 * (native_edges[:-1] + native_edges[1:])
            mask = (native_centers >= 508.0) & (native_centers <= 514.0)
            zoom_values = positive(native_values[mask])
            zoom_errors = np.where(native_values[mask] > 0.0, native_errors[mask], np.nan)
            marker = {"pre_veto": "o", "combined_active_veto": "s", FINAL: "^"}[stage]
            zoom_ax.errorbar(
                native_centers[mask],
                zoom_values,
                yerr=zoom_errors,
                color=color,
                ls=linestyle,
                marker=marker,
                ms=2.4,
                mew=0.4,
                mfc="white",
                lw=1.0,
                elinewidth=0.55,
                capsize=1.2,
                label=label,
            )

        broad_values = report[model]["integrated_480_550_cps"]
        broad_ax.text(
            0.02,
            0.045,
            rf"$R_{{480-550}}$: {broad_values['pre_veto']['rate']:.3g} $\rightarrow$ "
            rf"{broad_values['combined_active_veto']['rate']:.3g} $\rightarrow$ "
            rf"{broad_values[FINAL]['rate']:.3g} s$^{{-1}}$",
            transform=broad_ax.transAxes,
            fontsize=6.8,
            color=COLORS["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.2},
        )
        broad_ax.set_title(f"Mass model {model}")
        broad_ax.set_xlim(480.0, 550.0)
        broad_ax.set_ylim(2.0e-5, 2.0e1)
        broad_ax.set_yscale("log")
        broad_ax.set_xlabel("Measured TES energy (keV)")
        tidy(broad_ax)

        zoom_ax.axvspan(W2_LOW, W2_HIGH, color="#BFC5CC", alpha=0.32, zorder=-2)
        zoom_ax.axvline(W2_LOW, color=COLORS["muted"], lw=0.65, ls=":")
        zoom_ax.axvline(W2_HIGH, color=COLORS["muted"], lw=0.65, ls=":")
        zoom_ax.text(
            511.0,
            1.15e1,
            "511-keV\nscience window",
            ha="center",
            va="top",
            fontsize=5.8,
            color=COLORS["muted"],
        )
        zoom_ax.set_xlim(508.0, 514.0)
        zoom_ax.set_ylim(2.0e-5, 2.0e1)
        zoom_ax.set_yscale("log")
        zoom_ax.set_xlabel("Measured TES energy (keV)")
        tidy(zoom_ax)

    axes[0, 0].set_ylabel(r"$\mathrm{d}R/\mathrm{d}E$ (s$^{-1}$ keV$^{-1}$)")
    axes[1, 0].set_ylabel(r"$\mathrm{d}R/\mathrm{d}E$ (s$^{-1}$ keV$^{-1}$)")
    axes[0, 1].tick_params(labelleft=False)
    axes[1, 1].tick_params(labelleft=False)
    for label, ax in zip(("(a)", "(b)", "(c)", "(d)"), axes.flat):
        panel(ax, label)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.035),
        ncol=3,
        frameon=False,
        handlelength=2.8,
        columnspacing=1.4,
    )
    paths = save(fig, "fig05_day15_selection_spectra_current")
    return paths, report


def main() -> int:
    configure()
    for path in (A_ORIGINS, B_ORIGINS, GEOMETRY_CONTRACT, A_GEOMETRY, B_GEOMETRY):
        require(path.is_file(), f"missing required compact input: {path}")
        require(FORBIDDEN_TASK not in str(path), "excluded task path entered the input set")
    data = {model: current.model_data(model) for model in ("A", "B")}
    geometry_paths, geometry_report = build_geometry_response(data)
    spectrum_paths, spectrum_report = build_day15_spectra(data)
    payload = {
        "schema_version": 1,
        "status": "PASS__M05_SECTION4_PUBLICATION_FIGURES_CURRENT_FORMAL_SCOPE",
        "authority_boundary": {
            "new_transport": False,
            "simulation_started": False,
            "SIM_or_NPZ_opened": False,
            "large_job_catalog_scanned": False,
            "model_B_origin_reweight": "family-wise first and second moments independently closed to Package-70 formal delayed cutflow",
            "spectrum_scope": "explicit sum of prompt/other, prompt/gamma_continuum, and delayed/other; all/all used only as a closure check",
        },
        "figures": [str(path) for path in geometry_paths + spectrum_paths],
        "geometry_response": geometry_report,
        "day15_spectra": spectrum_report,
        "input_sha256": {
            str(path): sha256(path)
            for path in (
                A_ORIGINS,
                B_ORIGINS,
                GEOMETRY_CONTRACT,
                A_GEOMETRY,
                B_GEOMETRY,
                Path(data["A"]["input_paths"]["measured_energy_diagnostic"]),
                Path(data["B"]["input_paths"]["measured_energy_diagnostic"]),
                Path(data["A"]["input_paths"]["cutflow"]),
                Path(data["B"]["input_paths"]["cutflow"]),
            )
        },
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    require("mono511" not in serialized and "atm511" not in serialized, "manuscript-facing report contains an excluded component label")
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "figures": payload["figures"], "report": str(REPORT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
