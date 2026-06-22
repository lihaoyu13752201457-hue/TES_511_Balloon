#!/usr/bin/env python3
"""Build manuscript figures for veto selection and time-axis folding.

The script reads the current fix5 M=50000 exact-position Step05/06/08 authority
products and does not rerun transport or event selection.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "core_md" / "balloon511_nima_latex_drafts" / "paper_source_figure_table"

STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / "outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1"
    / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json"
)
STEP06_BG = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / "outputs_fix5_fullstat_v2_exactpos_m50000_s260613"
    / "background_time_variation.csv"
)
STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_fix5_fullstat_v2_exactpos_m50000_s260613"
    / "step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json"
)
STEP08_CUM = STEP08_SUMMARY.parent / "cumulative_significance_by_case.csv"

FIG_SELECTION = OUT / "fig_selection_veto_time_axis.png"
FIG_GEOMETRY = OUT / "fig_compton_fov_geometry.png"
SUMMARY_JSON = OUT / "fig_selection_veto_time_axis_summary.json"
CAPTION_MD = OUT / "fig_selection_veto_time_axis_caption.md"

W2 = "w2_510p58_511p42"
CASE_ID = "A_point_w2_510p58_511p42_F0.0001"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def physical_rates(step05: dict[str, Any]) -> dict[str, dict[str, float]]:
    w2 = step05["windows"][W2]
    inj = float(step05["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"])
    result: dict[str, dict[str, float]] = {}
    for stream, row in w2["by_stream"].items():
        scale = inj if stream == "science" else 1.0
        result[stream] = {
            "raw": float(row["raw_rate_s-1"]) * scale,
            "active": float(row["active_veto_pass_rate_s-1"]) * scale,
            "final": float(row["side_compton_fov_pass_rate_s-1"]) * scale,
            "raw_events": int(row["raw_events"]),
            "active_events": int(row["active_veto_pass_events"]),
            "final_events": int(row["side_compton_fov_pass_events"]),
        }
    return result


def selection_survival(step05: dict[str, Any]) -> dict[str, dict[str, float]]:
    w2 = step05["windows"][W2]
    result: dict[str, dict[str, float]] = {}
    for stream, row in w2["by_stream"].items():
        raw = float(row["raw_rate_s-1"])
        active = float(row["active_veto_pass_rate_s-1"])
        final = float(row["side_compton_fov_pass_rate_s-1"])
        result[stream] = {
            "raw": 1.0,
            "active": active / raw if raw > 0 else 0.0,
            "final": final / raw if raw > 0 else 0.0,
        }
    return result


def class_counts(step05: dict[str, Any]) -> dict[str, dict[str, int]]:
    w2 = step05["windows"][W2]
    return {
        stream: {str(k): int(v) for k, v in row["side_compton_class_counts"].items()}
        for stream, row in w2["by_stream"].items()
    }


def build_selection_figure(step05: dict[str, Any], bg_rows: list[dict[str, str]], cum_rows: list[dict[str, str]]) -> None:
    rates = physical_rates(step05)
    survival = selection_survival(step05)
    classes = class_counts(step05)
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.2))

    stages = ["raw", "active", "final"]
    stage_labels = ["raw", "active veto", "Compton/FoV"]
    colors = {"prompt": "#4C78A8", "delayed": "#F58518", "science": "#54A24B"}
    x = np.arange(len(stages))
    width = 0.24
    for offset, stream in zip([-width, 0.0, width], ["prompt", "delayed", "science"]):
        vals = [rates[stream][stage] for stage in stages]
        axes[0, 0].bar(x + offset, vals, width=width, color=colors[stream], label=stream)
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(stage_labels)
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_ylabel("W2 rate (s$^{-1}$)")
    axes[0, 0].set_title("A. Step05 W2 rate through veto stages")
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 0].grid(axis="y", alpha=0.25)

    for stream in ["prompt", "delayed", "science"]:
        vals = [survival[stream][stage] for stage in stages]
        axes[0, 1].plot(stage_labels, vals, marker="o", lw=2.0, color=colors[stream], label=stream)
    axes[0, 1].set_ylim(0.0, 1.05)
    axes[0, 1].set_ylabel("rate / raw rate")
    axes[0, 1].set_title("B. W2 survival fraction")
    axes[0, 1].grid(alpha=0.25)
    axes[0, 1].legend(frameon=False, fontsize=8)

    class_order = ["single", "keep", "veto", "reject_kept"]
    bottom = np.zeros(3)
    streams = ["prompt", "delayed", "science"]
    class_colors = {
        "single": "#72B7B2",
        "keep": "#B279A2",
        "veto": "#E45756",
        "reject_kept": "#9D755D",
    }
    for cls in class_order:
        vals = np.asarray([classes.get(stream, {}).get(cls, 0) for stream in streams], dtype=float)
        axes[1, 0].bar(streams, vals, bottom=bottom, color=class_colors[cls], label=cls)
        bottom += vals
    axes[1, 0].set_ylabel("active-pass W2 events")
    axes[1, 0].set_title("C. Compton/FoV outcomes")
    axes[1, 0].legend(frameon=False, fontsize=8)
    axes[1, 0].grid(axis="y", alpha=0.25)

    w2_bg = [row for row in bg_rows if row["selection_id"] == W2]
    days = np.asarray([float(row["day_mid"]) for row in w2_bg])
    background = np.asarray([float(row["background_final_cps"]) for row in w2_bg])
    science = np.asarray([float(row["science_final_cps_at_ref_flux"]) for row in w2_bg])
    live = np.asarray([
        math.exp(-(float(row["prompt_event_rate_hz"]) + float(row["delayed_event_rate_hz"])) * float(step05["normalization"]["coincidence_window_s"]))
        for row in w2_bg
    ])
    case_rows = [row for row in cum_rows if row["analysis_case_id"] == CASE_ID]
    z_days = np.asarray([float(row["elapsed_stop_day"]) for row in case_rows])
    z_vals = np.asarray([float(row["counting_Z"]) for row in case_rows])
    ax = axes[1, 1]
    ax.plot(days, background, color="#4C78A8", label="background")
    ax.plot(days, science, color="#54A24B", label="signal @ $10^{-4}$")
    ax.set_xlabel("mission day")
    ax.set_ylabel("W2 rate (s$^{-1}$)")
    ax.set_title("D. Mission-time fold")
    ax.grid(alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(z_days, z_vals, color="#E45756", lw=2.0, label="$Z(t)$")
    ax2.plot(days, live, color="#9D755D", ls="--", label="live factor")
    ax2.set_ylabel("Z or live factor")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, frameon=False, fontsize=8, loc="center right")

    fig.tight_layout()
    fig.savefig(FIG_SELECTION, dpi=220)
    plt.close(fig)


def build_geometry_figure(step05: dict[str, Any]) -> None:
    disk = step05["normalization"]["side_entry_disk"]
    center = np.asarray(disk["center_cm"], dtype=float)
    normal = np.asarray(disk["normal"], dtype=float)
    radius = float(disk["radius_cm"])
    v = np.asarray([-normal[2], 0.0, normal[0]], dtype=float)
    v /= np.linalg.norm(v)
    p_a = center - radius * v
    p_b = center + radius * v

    theta = math.radians(60.0)
    total_e = 511.0
    scattered_e = total_e / (2.0 - math.cos(theta))
    recoil_e = total_e - scattered_e
    hit1 = np.asarray([-5.0, 0.0, -1.0])
    target_dir = center - hit1
    target_dir /= np.linalg.norm(target_dir)
    perp = np.asarray([-target_dir[2], 0.0, target_dir[0]], dtype=float)
    perp /= np.linalg.norm(perp)
    axis = math.cos(theta) * target_dir + math.sin(theta) * perp
    axis /= np.linalg.norm(axis)
    cone_basis = (target_dir - math.cos(theta) * axis) / math.sin(theta)
    cone_basis /= np.linalg.norm(cone_basis)
    hit2 = hit1 - 1.7 * axis
    cone_dir_1 = target_dir
    cone_dir_2 = math.cos(theta) * axis - math.sin(theta) * cone_basis
    ray_len = 13.0

    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    ax.plot([p_a[0], p_b[0]], [p_a[2], p_b[2]], color="#222222", lw=4, solid_capstyle="round", label="Be window disk projection")
    ax.quiver(center[0], center[2], normal[0], normal[2], angles="xy", scale_units="xy", scale=0.35, color="#555555", width=0.006)
    ax.scatter([hit1[0], hit2[0]], [hit1[2], hit2[2]], s=[80, 70], color=["#4C78A8", "#F58518"], zorder=5)
    ax.text(hit1[0] + 0.2, hit1[2] + 0.2, "hit 1", fontsize=9)
    ax.text(hit2[0] + 0.2, hit2[2] - 0.35, "hit 2", fontsize=9)
    ax.plot([hit1[0], hit2[0]], [hit1[2], hit2[2]], color="#888888", lw=1.5)
    for d, color in [(cone_dir_1, "#B279A2"), (cone_dir_2, "#B279A2")]:
        p = hit1 + ray_len * d
        ax.plot([hit1[0], p[0]], [hit1[2], p[2]], color=color, lw=1.4, ls="--")
    ax.text(
        -15.4,
        -4.7,
        "$\\cos\\theta_C = 1-m_ec^2(1/E_\\mathrm{sc}-1/E_0)$\n"
        f"example: $E_1={recoil_e:.1f}$ keV, $E_\\mathrm{{sc}}={scattered_e:.1f}$ keV, $\\theta_C=60^\\circ$",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#CCCCCC", "alpha": 0.9},
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("instrument x (cm)")
    ax.set_ylabel("instrument z (cm)")
    ax.set_title("Compton/FoV side-window consistency geometry")
    ax.set_xlim(-16.5, 2.0)
    ax.set_ylim(-7.0, 8.5)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_GEOMETRY, dpi=220)
    plt.close(fig)


def write_summary(step05: dict[str, Any], bg_rows: list[dict[str, str]], cum_rows: list[dict[str, str]]) -> None:
    rates = physical_rates(step05)
    survival = selection_survival(step05)
    w2_bg = [row for row in bg_rows if row["selection_id"] == W2]
    case_rows = [row for row in cum_rows if row["analysis_case_id"] == CASE_ID]
    live_values = [
        math.exp(-(float(row["prompt_event_rate_hz"]) + float(row["delayed_event_rate_hz"])) * float(step05["normalization"]["coincidence_window_s"]))
        for row in w2_bg
    ]
    payload = {
        "status": "PASS_SELECTION_VETO_TIME_AXIS_FIGURE",
        "inputs": {
            "step05_summary": str(STEP05.relative_to(ROOT)),
            "step06_background_time_variation": str(STEP06_BG.relative_to(ROOT)),
            "step08_summary": str(STEP08_SUMMARY.relative_to(ROOT)),
            "step08_cumulative": str(STEP08_CUM.relative_to(ROOT)),
        },
        "figures": {
            "selection_veto_time_axis": str(FIG_SELECTION.relative_to(ROOT)),
            "compton_fov_geometry": str(FIG_GEOMETRY.relative_to(ROOT)),
        },
        "w2_physical_rates_cps": rates,
        "w2_survival_fraction": survival,
        "w2_compton_class_counts": class_counts(step05),
        "poisson_timeline": {
            "coincidence_window_s": step05["normalization"]["coincidence_window_s"],
            "timeline_draw_summary": step05["timeline_draw_summary"],
            "timeline_candidate_summary": {
                "obs_time_s": step05["timeline"]["obs_time_s"],
                "n_event_instances": step05["timeline"]["n_event_instances"],
                "n_candidates_total": step05["timeline"]["n_candidates_total"],
                "n_candidates_with_tes": step05["timeline"]["n_candidates_with_tes"],
                "n_mixed_candidates": step05["timeline"]["n_mixed_candidates"],
            },
            "accidental_live_factor_range": [min(live_values), max(live_values)],
        },
        "time_fold_reference_case": {
            "analysis_case_id": CASE_ID,
            "final_day": float(case_rows[-1]["elapsed_stop_day"]),
            "final_Z": float(case_rows[-1]["counting_Z"]),
            "total_source_counts": float(case_rows[-1]["cumulative_source_counts"]),
            "total_background_counts": float(case_rows[-1]["cumulative_background_counts"]),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    CAPTION_MD.write_text(
        "\n".join(
            [
                "# Selection and time-axis figure caption",
                "",
                "The figure is generated from the current fix5 Step05/Step06/Step08 exact-position M=50000 authority products.",
                "Panel A shows the W2 raw, active-veto-pass, and Compton/FoV-pass rates.",
                "Panel B shows stream-wise survival fractions.",
                "Panel C shows Compton/FoV classification outcomes after the active-veto gate.",
                "Panel D shows the Step06/08 mission-time fold for the reference W2 point-source case, including the analytic accidental live factor.",
                "The separate Compton/FoV geometry panel uses the actual side-entry Be-window disk center, normal, radius, and the Compton kinematic equation used by the selection code.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    step05 = load_json(STEP05)
    bg_rows = read_csv(STEP06_BG)
    cum_rows = read_csv(STEP08_CUM)
    build_selection_figure(step05, bg_rows, cum_rows)
    build_geometry_figure(step05)
    write_summary(step05, bg_rows, cum_rows)
    print(json.dumps({"status": "PASS", "figures": [str(FIG_SELECTION), str(FIG_GEOMETRY)], "summary": str(SUMMARY_JSON)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
