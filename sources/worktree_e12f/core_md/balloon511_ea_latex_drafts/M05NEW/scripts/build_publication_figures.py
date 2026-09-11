#!/usr/bin/env python3
"""Build the compact publication figures for the new M05 manuscript.

The script reads only retained CSV and JSON products.  It does not open SIM
payloads, run detector response, start transport, or compute file hashes.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05new_publication_figures_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


HERE = Path(__file__).resolve()
M05NEW = HERE.parents[1]
ROOT = next(parent for parent in HERE.parents if (parent / "AGENTS.md").exists())
FIGURES = M05NEW / "figures"

GEOMETRY_CONTRACT = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "66_m05new_mxc_bpe_veto_review_20260821/data/"
    "cross_section_geometry_contract.csv"
)
ORIGIN_SHARES = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "66_m05new_mxc_bpe_veto_review_20260821/data/"
    "cold_stage_origin_share.csv"
)
GEOMETRY_ASSESSMENT = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "66_m05new_mxc_bpe_veto_review_20260821/outputs/assessment.json"
)
REFERENCE_ORIGINS = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/"
    "selected_event_lineage.csv"
)
CHIMNEY_ORIGINS = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/"
    "optv3_delayed_selected_events.csv"
)

REFERENCE_CUTFLOW = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/03_expanded_catalog/"
    "expanded_direct_cutflow.csv"
)
CHIMNEY_CUTFLOW = ROOT / (
    "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/"
    "direct_cutflow_totals.csv"
)
MATCHED_COMPARISON = M05NEW / "SG3B_OPTV3_COMPARISON.json"

REFERENCE_TIMELINE = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/04_candidate_timeline/"
    "mission_mature_flux_threshold.csv"
)
CHIMNEY_TIMELINE = ROOT / (
    "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/"
    "mission_timeline_81nodes.csv"
)
M05NEW_VALIDATION = M05NEW / "M05NEW_VALIDATION.json"


# Okabe--Ito colors, with line styles and marker shapes providing redundant cues.
BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#D89000"
VERMILION = "#D55E00"
PURPLE = "#8E5AA9"
GRAY = "#69757F"
LIGHT_GRAY = "#E9EDF0"
INK = "#18222C"
TES = "#A92535"
COPPER = "#C77C45"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["TeX Gyre Termes", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
            "axes.linewidth": 0.8,
            "axes.edgecolor": "#77838D",
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for suffix in ("pdf", "svg", "png"):
        path = FIGURES / f"{stem}.{suffix}"
        kwargs: dict[str, Any] = {
            "bbox_inches": "tight",
            "pad_inches": 0.035,
            "facecolor": "white",
        }
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs


def physical_region(volume: str) -> str:
    if volume.startswith("ColdPlate_") or volume == "DR_MixingChamber_Cu":
        return "cold stages"
    nearby_tokens = (
        "TES_",
        "SubstrateSupport",
        "SH3_Layer",
        "W_Frame",
        "BottomColdPlate",
        "ColdFinger",
        "50mK",
        "Bi_MXC_TES",
    )
    if any(token in volume for token in nearby_tokens):
        return "focal-plane vicinity"
    return "other"


def load_origin_points() -> dict[str, list[dict[str, float | str]]]:
    reference: list[dict[str, float | str]] = []
    for row in read_csv(REFERENCE_ORIGINS):
        if row["stream"] != "delayed":
            continue
        reference.append(
            {
                "region": physical_region(row["source_volume"]),
                "x": float(row["source_xprime_cm"]),
                "z": float(row["source_zprime_cm"]),
                "weight": float(row["day15_noacc_cps"]),
            }
        )

    chimney: list[dict[str, float | str]] = []
    angle = math.radians(45.0)
    cosine, sine = math.cos(angle), math.sin(angle)
    for row in read_csv(CHIMNEY_ORIGINS):
        x_world = float(row["x_cm"])
        z_world = float(row["z_cm"])
        chimney.append(
            {
                "region": physical_region(row["source_volume"]),
                "x": cosine * x_world - sine * z_world,
                "z": sine * x_world + cosine * z_world,
                "weight": float(row["day15_event_weight_cps"]),
            }
        )
    return {"reference": reference, "optimized": chimney}


def draw_cold_stages(ax: plt.Axes, plate_rows: Iterable[dict[str, str]]) -> None:
    ax.add_patch(
        Rectangle(
            (-17.5, -15.5),
            35.0,
            47.0,
            facecolor=ORANGE,
            edgecolor="none",
            alpha=0.055,
            zorder=0,
        )
    )
    for row in plate_rows:
        x_min = float(row["x_min_cm"])
        x_max = float(row["x_max_cm"])
        z_min = float(row["z_min_cm"])
        z_max = float(row["z_max_cm"])
        ax.add_patch(
            Rectangle(
                (x_min, z_min),
                x_max - x_min,
                z_max - z_min,
                facecolor="#F4DDA5",
                edgecolor=ORANGE,
                linewidth=0.8,
                hatch="///",
                zorder=3,
            )
        )
    ax.add_patch(
        Rectangle(
            (-2.2, 0.35),
            4.4,
            1.8,
            facecolor=COPPER,
            edgecolor="#744226",
            linewidth=0.8,
            hatch="..",
            zorder=4,
        )
    )


def draw_tes(ax: plt.Axes, rows: list[dict[str, str]]) -> None:
    x_min = min(float(row["x_min_cm"]) for row in rows)
    x_max = max(float(row["x_max_cm"]) for row in rows)
    z_min = min(float(row["z_min_cm"]) for row in rows)
    z_max = max(float(row["z_max_cm"]) for row in rows)
    for row in rows:
        left = float(row["x_min_cm"])
        bottom = float(row["z_min_cm"])
        width = float(row["x_max_cm"]) - left
        height = float(row["z_max_cm"]) - bottom
        ax.add_patch(
            Rectangle(
                (left, bottom),
                width,
                height,
                facecolor=TES,
                edgecolor="#681520",
                linewidth=0.65,
                zorder=8,
            )
        )
    ax.add_patch(
        Rectangle(
            (x_min - 0.25, z_min - 0.2),
            x_max - x_min + 0.5,
            z_max - z_min + 0.4,
            fill=False,
            edgecolor="#681520",
            linewidth=1.0,
            linestyle=(0, (4, 2)),
            zorder=9,
        )
    )


def draw_reference_bgo(ax: plt.Axes) -> None:
    for x0 in (-25.2, 21.2):
        ax.add_patch(
            Rectangle(
                (x0, -17.0),
                4.0,
                49.0,
                facecolor="#CFE5F3",
                edgecolor=BLUE,
                linewidth=0.9,
                alpha=0.72,
                zorder=1,
            )
        )
    # The side-entry opening is shown only to make the preserved focused path explicit.
    ax.add_patch(Rectangle((-25.35, -7.10), 4.3, 3.80, facecolor="white", edgecolor="none", zorder=2))


def draw_chimney_bgo(ax: plt.Axes) -> None:
    ax.add_patch(
        Rectangle(
            (-45.75, -13.85),
            30.75,
            22.10,
            facecolor="#EFF2F4",
            edgecolor="#9AA5AE",
            linewidth=0.9,
            zorder=0,
        )
    )
    ax.add_patch(
        Rectangle(
            (-45.45, -13.55),
            30.45,
            21.50,
            facecolor="white",
            edgecolor="none",
            zorder=0,
        )
    )
    for z0 in (-13.5, 3.9):
        ax.add_patch(
            Rectangle(
                (-41.7, z0),
                13.0,
                4.0,
                facecolor="#CFE5F3",
                edgecolor=BLUE,
                linewidth=0.9,
                alpha=0.78,
                zorder=2,
            )
        )
    for x0 in (-45.7, -28.7):
        ax.add_patch(
            Rectangle(
                (x0, -13.5),
                4.0,
                21.4,
                facecolor="#CFE5F3",
                edgecolor=BLUE,
                linewidth=0.9,
                alpha=0.78,
                zorder=2,
            )
        )
    ax.add_patch(Rectangle((-45.85, -4.70), 4.3, 3.80, facecolor="white", edgecolor="none", zorder=3))


def draw_focused_path(ax: plt.Axes, start_x: float, stop_x: float, z: float) -> None:
    ax.annotate(
        "",
        xy=(stop_x, z),
        xytext=(start_x, z),
        arrowprops={"arrowstyle": "-|>", "color": PURPLE, "lw": 1.15},
        zorder=12,
    )


def scatter_origins(ax: plt.Axes, rows: list[dict[str, float | str]]) -> None:
    styles = {
        "cold stages": (ORANGE, "o", INK),
        "focal-plane vicinity": (BLUE, "^", "white"),
        "other": (GRAY, "x", GRAY),
    }
    max_weight = max(float(row["weight"]) for row in rows)
    for region, (color, marker, edge) in styles.items():
        selected = [row for row in rows if row["region"] == region]
        if not selected:
            continue
        sizes = [7.0 + 34.0 * math.sqrt(float(row["weight"]) / max_weight) for row in selected]
        kwargs: dict[str, Any] = {
            "s": sizes,
            "c": color,
            "marker": marker,
            "alpha": 0.62,
            "linewidths": 0.45,
            "zorder": 10,
            "clip_on": True,
        }
        if marker != "x":
            kwargs["edgecolors"] = edge
        ax.scatter(
            [float(row["x"]) for row in selected],
            [float(row["z"]) for row in selected],
            **kwargs,
        )


def build_geometry_figure() -> list[Path]:
    contract_rows = read_csv(GEOMETRY_CONTRACT)
    share_rows = read_csv(ORIGIN_SHARES)
    assessment = read_json(GEOMETRY_ASSESSMENT)
    points = load_origin_points()

    shares = {
        row["geometry"]: float(row["fraction_of_delayed_W2_final"])
        for row in share_rows
        if row["region"] == "DR/MXC + staged cold plates"
    }
    # Use the retained numeric geometry contract; ancillary historical layers are intentionally not drawn.
    if assessment["selected_delayed_origins"]["SG3B_rows"] != len(points["reference"]):
        raise RuntimeError("reference selected-origin row count changed")
    if assessment["selected_delayed_origins"]["SH3_OptV3_rows"] != len(points["optimized"]):
        raise RuntimeError("optimized selected-origin row count changed")

    plates = [
        row
        for row in contract_rows
        if row["geometry"] == "SG3B" and row["kind"] == "cold_plate"
    ]
    tes_rows = {
        "reference": [
            row
            for row in contract_rows
            if row["geometry"] == "SG3B" and row["kind"] == "TES_active_layer"
        ],
        "optimized": [
            row
            for row in contract_rows
            if row["geometry"] == "SH3_OptV3" and row["kind"] == "TES_active_layer"
        ],
    }

    fig, axes = plt.subplots(1, 2, figsize=(7.05, 3.55), sharex=True, sharey=True)
    for index, (ax, key, title) in enumerate(
        zip(
            axes,
            ("reference", "optimized"),
            ("Reference geometry", "Optimized chimney geometry"),
            strict=True,
        )
    ):
        ax.set_xlim(-52.0, 32.0)
        ax.set_ylim(-16.0, 32.0)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color="#DDE3E7", linewidth=0.45, zorder=-10)
        ax.set_title(f"({chr(97 + index)})  {title}", loc="left", fontweight="bold", pad=4)
        ax.set_xlabel("Local transverse coordinate $x'$ (cm)")
        if index == 0:
            ax.set_ylabel("Local axial coordinate $z'$ (cm)")
        draw_cold_stages(ax, plates)
        if key == "reference":
            draw_reference_bgo(ax)
            draw_focused_path(ax, -48.0, -3.5, -5.2)
            share = shares["SG3B"]
        else:
            draw_chimney_bgo(ax)
            draw_focused_path(ax, -50.5, -38.9, -2.8)
            share = shares["SH3_OptV3"]
        draw_tes(ax, tes_rows[key])
        scatter_origins(ax, points[key])
        ax.text(
            0.025,
            0.965,
            "Cold-stage share of selected\n"
            f"delayed background: {100.0 * share:.2f}%",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.2,
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#B6C0C7", "alpha": 0.94},
            zorder=20,
        )

    legend = [
        Patch(facecolor="#F4DDA5", edgecolor=ORANGE, hatch="///", label="cold stages and mixing chamber"),
        Patch(facecolor=TES, edgecolor="#681520", label="TES active layers"),
        Patch(facecolor="#CFE5F3", edgecolor=BLUE, label="active BGO shield"),
        Patch(facecolor="#EFF2F4", edgecolor="#9AA5AE", label="chimney wall"),
        Line2D([0], [0], color=PURPLE, lw=1.2, marker=">", markevery=[1], label="focused photon path"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor=INK, markersize=5, label="selected decay site: cold stages"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=5, label="selected decay site: focal-plane vicinity"),
        Line2D([0], [0], marker="x", color=GRAY, markersize=5, label="selected decay site: other"),
    ]
    fig.suptitle("Spatial separation of the TES from the cryogenic stages", y=0.995, fontsize=10.2, fontweight="bold")
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        ncol=4,
        frameon=False,
        columnspacing=1.0,
        handlelength=1.8,
        fontsize=6.7,
    )
    fig.subplots_adjust(left=0.065, right=0.99, top=0.91, bottom=0.22, wspace=0.08)
    return save_figure(fig, "fig_geometry_causal_section")


def load_cutflow_rates() -> dict[str, list[float]]:
    # Show the BGO stage itself so the causal comparison does not fold an
    # ancillary veto layer into the optimization narrative.
    stages = ("pre_veto", "bgo_active_scintillator_veto", "compton_trajectory_veto")
    reference_grouped: dict[str, float] = defaultdict(float)
    for row in read_csv(REFERENCE_CUTFLOW):
        if row["window_id"] == "w2_510p58_511p42" and row["stage"] in stages:
            reference_grouped[row["stage"]] += float(row["weighted_rate_cps"])

    optimized_grouped: dict[str, float] = {}
    for row in read_csv(CHIMNEY_CUTFLOW):
        if row["window_id"] == "w2_510p58_511p42" and row["stage"] in stages:
            optimized_grouped[row["stage"]] = float(row["total_rate_cps"])

    return {
        "reference": [reference_grouped[stage] for stage in stages],
        "optimized": [optimized_grouped[stage] for stage in stages],
    }


def build_cutflow_performance_figure() -> list[Path]:
    rates = load_cutflow_rates()
    comparison = read_json(MATCHED_COMPARISON)
    ratios = comparison["ratios_OptV3_over_SG3B"]

    fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.95), gridspec_kw={"width_ratios": [1.15, 0.85]})
    ax = axes[0]
    x = np.arange(3)
    stage_labels = ("Science window", "After active BGO veto", "Final topology")
    for key, color, marker, linestyle, label in (
        ("reference", ORANGE, "s", (0, (4, 2)), "Reference geometry"),
        ("optimized", BLUE, "o", "-", "Optimized chimney geometry"),
    ):
        values = np.asarray(rates[key])
        ax.plot(
            x,
            values,
            color=color,
            marker=marker,
            markersize=4.8,
            linewidth=1.5,
            linestyle=linestyle,
            label=label,
            zorder=4,
        )
        for xi, value in zip(x, values, strict=True):
            ax.annotate(
                f"{value:.3g}",
                (xi, value),
                xytext=(0, 7 if key == "reference" else -10),
                textcoords="offset points",
                ha="center",
                va="bottom" if key == "reference" else "top",
                fontsize=6.7,
                color=color,
            )
    ax.set_yscale("log")
    ax.set_ylim(4.0e-3, 10.0)
    ax.set_xticks(x, stage_labels)
    ax.set_ylabel("Prompt + delayed background rate (s$^{-1}$)")
    ax.set_title("(a)  Matched science-window cut-flow", loc="left", fontweight="bold")
    ax.grid(True, which="both", axis="y", color="#DDE3E7", linewidth=0.5)
    ax.legend(frameon=False, loc="upper right", handlelength=2.3)

    ax = axes[1]
    labels = ("Effective area", "Day-15 background", r"3$\sigma$ flux threshold")
    values = np.asarray([ratios["Aeff"], ratios["day15_background"], ratios["Fmin"]]) * 100.0
    colors = (BLUE, ORANGE, PURPLE)
    y = np.arange(3)
    bars = ax.barh(y, values, color=colors, edgecolor=INK, linewidth=0.55, height=0.55)
    ax.axvline(100.0, color=GRAY, linewidth=0.9, linestyle=(0, (3, 2)))
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            min(value + 2.2, 102.0),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            ha="left" if value < 96 else "right",
            fontsize=7.2,
            fontweight="bold",
            color=INK,
        )
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 108.0)
    ax.set_xlabel("Optimized / reference (%)")
    ax.set_title("(b)  Matched performance ratios", loc="left", fontweight="bold")
    ax.grid(True, axis="x", color="#DDE3E7", linewidth=0.5)

    fig.suptitle("Background rejection and retained focused response", y=0.995, fontsize=10.2, fontweight="bold")
    fig.subplots_adjust(left=0.085, right=0.99, top=0.86, bottom=0.22, wspace=0.42)
    return save_figure(fig, "fig_matched_cutflow_performance")


def numeric_column(rows: list[dict[str, str]], name: str) -> np.ndarray:
    values: list[float] = []
    for row in rows:
        raw = row[name].strip()
        values.append(float(raw) if raw else math.nan)
    return np.asarray(values, dtype=float)


def timeline_arrays(path: Path, *, optimized: bool) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    days = numeric_column(rows, "day_mid")
    background = numeric_column(rows, "cumulative_background_counts")
    kernel = numeric_column(rows, "cumulative_signal_counts_per_unit_flux")
    signal = kernel * 1.0e-4
    gaussian_z = np.divide(signal, np.sqrt(background), out=np.full_like(signal, np.nan), where=background > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        asimov_z = np.sqrt(2.0 * ((signal + background) * np.log1p(signal / background) - signal))
    if optimized:
        gaussian_fmin = numeric_column(rows, "fmin_3sigma_gauss_ph_cm2_s")
        asimov_fmin = numeric_column(rows, "fmin_3sigma_asimov_ph_cm2_s")
    else:
        gaussian_fmin = numeric_column(rows, "Fmin_3sigma_gaussian_ph_cm2_s")
        asimov_fmin = numeric_column(rows, "Fmin_3sigma_poisson_asimov_ph_cm2_s")
    return {
        "day": days,
        "gaussian_z": gaussian_z,
        "asimov_z": asimov_z,
        "gaussian_fmin": gaussian_fmin,
        "asimov_fmin": asimov_fmin,
    }


def build_mission_figure() -> list[Path]:
    reference = timeline_arrays(REFERENCE_TIMELINE, optimized=False)
    optimized = timeline_arrays(CHIMNEY_TIMELINE, optimized=True)
    validation = read_json(M05NEW_VALIDATION)

    fig, axes = plt.subplots(1, 2, figsize=(7.05, 3.15))
    ax = axes[0]
    for data, color, linestyle, label in (
        (reference, ORANGE, (0, (4, 2)), "Reference geometry"),
        (optimized, BLUE, "-", "Optimized chimney geometry"),
    ):
        ax.plot(data["day"], data["gaussian_z"], color=color, linewidth=1.55, linestyle=linestyle, label=label)
    ax.axhline(3.0, color=GRAY, linewidth=0.8, linestyle=(0, (2, 2)))
    ax.axhline(5.0, color=GRAY, linewidth=0.8, linestyle=(0, (2, 2)))
    ax.text(0.35, 3.16, r"3$\sigma$", color=GRAY, fontsize=7.0)
    ax.text(0.35, 5.16, r"5$\sigma$", color=GRAY, fontsize=7.0)
    ax.scatter([5.52487, 15.9322], [3.0, 5.0], color=ORANGE, marker="s", s=20, zorder=5)
    ax.scatter([0.72369, 1.93507], [3.0, 5.0], color=BLUE, marker="o", s=20, zorder=5)
    ax.annotate("13.46", (20.0, optimized["gaussian_z"][-1]), xytext=(-5, -2), textcoords="offset points", ha="right", va="top", color=BLUE, fontweight="bold")
    ax.annotate("5.55", (20.0, reference["gaussian_z"][-1]), xytext=(-5, 3), textcoords="offset points", ha="right", va="bottom", color=ORANGE, fontweight="bold")
    ax.set_xlim(0.0, 20.2)
    ax.set_ylim(0.0, 14.5)
    ax.set_xlabel("Elapsed observing time (d)")
    ax.set_ylabel("Gaussian counting significance")
    ax.set_title("(a)  Significance for $10^{-4}$ ph cm$^{-2}$ s$^{-1}$", loc="left", fontweight="bold")
    ax.grid(True, color="#DDE3E7", linewidth=0.5)
    ax.legend(frameon=False, loc="upper left", handlelength=2.4)

    ax = axes[1]
    for data, color, linestyle, label in (
        (reference, ORANGE, (0, (4, 2)), "Reference geometry"),
        (optimized, BLUE, "-", "Optimized chimney geometry"),
    ):
        ax.plot(data["day"], data["gaussian_fmin"] * 1.0e5, color=color, linewidth=1.55, linestyle=linestyle, label=label)
        ax.plot(data["day"], data["asimov_fmin"] * 1.0e5, color=color, linewidth=0.95, linestyle=(0, (1, 1.5)), alpha=0.9)
    ax.axhline(24.0, color=GRAY, linewidth=0.85, linestyle=(0, (2, 2)))
    ax.text(0.45, 25.4, r"IBIS Gaussian-rescaled 3$\sigma$ scale", color=GRAY, fontsize=6.7)

    endpoint_values = {
        "reference": float(validation["SG3B_Fmin_3sigma_gaussian"]) * 1.0e5,
        "reference_error": float(validation["SG3B_Fmin_standard_error"]) * 1.0e5,
        "optimized": float(validation["OptV3_Fmin_3sigma_gaussian"]) * 1.0e5,
        "optimized_error": float(validation["OptV3_Fmin_standard_error"]) * 1.0e5,
    }
    ax.errorbar(20.0, endpoint_values["reference"], yerr=endpoint_values["reference_error"], fmt="s", color=ORANGE, capsize=2.5, markersize=4.5, zorder=6)
    ax.errorbar(20.0, endpoint_values["optimized"], yerr=endpoint_values["optimized_error"], fmt="o", color=BLUE, capsize=2.5, markersize=4.5, zorder=6)
    ax.annotate(
        f'{endpoint_values["reference"]:.3f} $\\pm$ {endpoint_values["reference_error"]:.3f}',
        (20.0, endpoint_values["reference"]),
        xytext=(-6, 8),
        textcoords="offset points",
        ha="right",
        va="bottom",
        color=ORANGE,
        fontsize=7.0,
        fontweight="bold",
    )
    ax.annotate(
        f'{endpoint_values["optimized"]:.3f} $\\pm$ {endpoint_values["optimized_error"]:.3f}',
        (20.0, endpoint_values["optimized"]),
        xytext=(-6, -8),
        textcoords="offset points",
        ha="right",
        va="top",
        color=BLUE,
        fontsize=7.0,
        fontweight="bold",
    )
    ax.set_yscale("log")
    ax.set_xlim(0.0, 20.2)
    ax.set_ylim(1.65, 42.0)
    ax.set_xlabel("Elapsed observing time (d)")
    ax.set_ylabel(r"3$\sigma$ flux threshold ($10^{-5}$ ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title(r"(b)  3$\sigma$ line-flux threshold", loc="left", fontweight="bold")
    ax.grid(True, which="both", color="#DDE3E7", linewidth=0.5)
    style_handles = [
        Line2D([0], [0], color=INK, lw=1.4, label="Gaussian"),
        Line2D([0], [0], color=INK, lw=1.0, linestyle=(0, (1, 1.5)), label="Asimov"),
        Line2D([0], [0], color=INK, marker="|", markersize=8, linestyle="none", label=r"20 d Gaussian $1\sigma$ MC error"),
    ]
    ax.legend(handles=style_handles, frameon=False, loc="upper right", handlelength=2.4, fontsize=6.8)

    fig.suptitle("Mission-integrated 511 keV narrow-line performance", y=0.995, fontsize=10.2, fontweight="bold")
    fig.subplots_adjust(left=0.085, right=0.99, top=0.86, bottom=0.20, wspace=0.35)
    return save_figure(fig, "fig_mission_significance_sensitivity")


def main() -> int:
    configure_matplotlib()
    outputs = []
    outputs.extend(build_geometry_figure())
    outputs.extend(build_cutflow_performance_figure())
    outputs.extend(build_mission_figure())
    for path in outputs:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
