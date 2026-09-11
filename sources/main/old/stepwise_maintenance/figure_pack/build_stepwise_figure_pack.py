#!/usr/bin/env python3
"""Build compact figure-pack plots for the current stepwise breakdown.

The plots here are presentation/index artifacts.  They only read the current
Step06/08/09 authority tables and do not rerun transport or redefine any
science metric.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "stepwise_maintenance" / "outputs" / "figures"

STEP06_TRAJECTORY = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "trajectory_profile.csv"
STEP06_BACKGROUND = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"
STEP06_SUMMARY = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "step06_mission_time_variation_summary.json"

STEP08_T3 = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "t3_t5_summary.csv"
LINE_WINDOW = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "line_window_sensitivity.csv"
SPATIAL_LINE = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "spatial_line_proxy.csv"

FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
SPECTRUM = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "non_xray_background_spectrum_480_550.csv"

REFERENCE_FLUX = 1.0e-4
MISSION_DAYS = 20.0


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str, default: float = math.nan) -> float:
    value = row.get(key, "")
    if value in ("", None):
        return default
    return float(value)


def first_float(row: dict[str, str], *keys: str, default: float = math.nan) -> float:
    for key in keys:
        value = as_float(row, key, math.nan)
        if math.isfinite(value):
            return value
    return default


def fmt(value: float, digits: int = 4) -> str:
    if not math.isfinite(value):
        return "n/a"
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e4:
        return f"{value:.{digits}e}"
    return f"{value:.{digits}g}"


def figure_path(name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / name


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def plot_trajectory_time_variation() -> dict[str, Any]:
    trajectory = read_csv(STEP06_TRAJECTORY)
    background = read_csv(STEP06_BACKGROUND)
    summary = load_json(STEP06_SUMMARY)

    days = np.asarray([as_float(row, "day_mid") for row in trajectory])
    altitude = np.asarray([as_float(row, "altitude_km") for row in trajectory])
    depth = np.asarray([as_float(row, "depth_g_cm2") for row in trajectory])
    latitude_offset = np.asarray([as_float(row, "latitude_offset_deg") for row in trajectory])
    longitude_offset = np.asarray([as_float(row, "longitude_offset_deg") for row in trajectory])
    rc_gv = np.asarray([as_float(row, "Rc_GV") for row in trajectory])

    t_atm = np.asarray([as_float(row, "T_atm_511") for row in background])
    prompt_scale = np.asarray([as_float(row, "prompt_scale_to_day15") for row in background])
    delayed_scale = np.asarray([as_float(row, "delayed_activity_scale_to_day15") for row in background])
    science_scale = np.asarray([as_float(row, "science_atm_scale_to_day15") for row in background])
    prompt = np.asarray([as_float(row, "prompt_final_cps") for row in background])
    delayed = np.asarray([as_float(row, "delayed_final_cps") for row in background])
    total = np.asarray([as_float(row, "background_final_cps") for row in background])

    fig, axes = plt.subplots(4, 1, figsize=(9.0, 10.2), sharex=True)

    ax = axes[0]
    ax.plot(days, altitude, color="#4C78A8", lw=2.0, label="altitude")
    ax.set_ylabel("Altitude (km)")
    ax.grid(True, alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(days, depth, color="#F58518", lw=1.8, ls="--", label="residual depth")
    ax2.set_ylabel("Depth (g cm$^{-2}$)")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)
    ax.set_title("Step06 mission trajectory and time-dependent response")

    ax = axes[1]
    ax.plot(days, latitude_offset, color="#54A24B", lw=1.8, label="latitude offset")
    ax.plot(days, longitude_offset, color="#B279A2", lw=1.8, label="longitude offset")
    ax.set_ylabel("Offset (deg)")
    ax.grid(True, alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(days, rc_gv, color="#E45756", lw=1.5, ls=":", label="cutoff proxy")
    ax2.set_ylabel("Rc proxy (GV)")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)

    ax = axes[2]
    ax.plot(days, prompt, color="#4C78A8", lw=1.5, label="prompt final")
    ax.plot(days, delayed, color="#F58518", lw=1.5, label="delayed final")
    ax.plot(days, total, color="#2F4B7C", lw=2.0, label="background final")
    ax.set_ylabel("Background (cps)")
    ax.grid(True, alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(days, t_atm, color="#54A24B", lw=1.8, ls="--", label="T_atm 511")
    ax2.set_ylabel("511 keV transmission")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8, ncols=2)

    ax = axes[3]
    ax.plot(days, prompt_scale, color="#4C78A8", lw=1.8, label="prompt production scale")
    ax.plot(days, delayed_scale, color="#F58518", lw=1.8, label="delayed activity scale")
    ax.plot(days, science_scale, color="#54A24B", lw=1.8, label="science/T_atm scale")
    ax.axhline(1.0, color="black", ls="--", lw=1.0)
    ax.set_ylabel("Scale to day 15")
    ax.set_xlabel("Mission day")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncols=3)

    for axis in axes:
        axis.axvline(15.0, color="black", ls=":", lw=1.0)

    fig.tight_layout()
    out = figure_path("stepwise_trajectory_time_variation.png")
    fig.savefig(out, dpi=220)
    plt.close(fig)

    return {
        "figure": rel(out),
        "inputs": [rel(STEP06_TRAJECTORY), rel(STEP06_BACKGROUND), rel(STEP06_SUMMARY)],
        "n_bins": len(trajectory),
        "day_start": summary["trajectory"]["day_start"],
        "day_stop": summary["trajectory"]["day_stop"],
        "altitude_range_km": [float(np.nanmin(altitude)), float(np.nanmax(altitude))],
        "T_atm_range": [float(np.nanmin(t_atm)), float(np.nanmax(t_atm))],
        "background_final_cps_range": [float(np.nanmin(total)), float(np.nanmax(total))],
    }


def w1_mission_axis_metric() -> dict[str, float]:
    rows = read_csv(STEP08_T3)
    row = next(
        item
        for item in rows
        if item["analysis_case_id"] == "A_mono_511_F0.0001_R0arcmin"
        and item["source_case_id"] == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"
    )
    z20 = as_float(row, "final_counting_Z")
    t3 = as_float(row, "T3_day_counting")
    if not math.isfinite(t3):
        t3 = as_float(row, "T3_day_extrapolated_constant_profile")
    return {
        "Z20d": z20,
        "T3_day": t3,
        "flux_3sigma_20d": REFERENCE_FLUX * 3.0 / z20 if z20 > 0.0 else math.nan,
    }


def plot_background_component_breakout() -> dict[str, Any]:
    rows = read_csv(STEP06_BACKGROUND)
    days = np.asarray([as_float(row, "day_mid") for row in rows])

    prompt_raw = np.asarray([as_float(row, "prompt_raw_cps") for row in rows])
    prompt_bgo = np.asarray([as_float(row, "prompt_bgo_cps") for row in rows])
    prompt_final = np.asarray([as_float(row, "prompt_final_cps") for row in rows])
    delayed_raw = np.asarray([as_float(row, "delayed_raw_cps") for row in rows])
    delayed_bgo = np.asarray([as_float(row, "delayed_bgo_cps") for row in rows])
    delayed_final = np.asarray([as_float(row, "delayed_final_cps") for row in rows])
    background_raw = np.asarray([as_float(row, "background_raw_cps") for row in rows])
    background_bgo = np.asarray([as_float(row, "background_bgo_cps") for row in rows])
    background_final = np.asarray([as_float(row, "background_final_cps") for row in rows])

    prompt_fraction = np.divide(prompt_final, background_final, out=np.zeros_like(prompt_final), where=background_final > 0.0)
    delayed_fraction = np.divide(delayed_final, background_final, out=np.zeros_like(delayed_final), where=background_final > 0.0)

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.2), sharex=True)
    axes = axes.ravel()

    stage_styles = [
        (prompt_raw, "raw", "#9E9E9E", "-"),
        (prompt_bgo, "active-shield pass", "#4C78A8", "--"),
        (prompt_final, "final", "#2F4B7C", "-"),
    ]
    ax = axes[0]
    for values, label, color, style in stage_styles:
        ax.plot(days, values, color=color, ls=style, lw=1.8, label=label)
    ax.set_title("Prompt background")
    ax.set_ylabel("Rate (cps)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    for values, label, color, style in [
        (delayed_raw, "raw", "#9E9E9E", "-"),
        (delayed_bgo, "active-shield pass", "#F58518", "--"),
        (delayed_final, "final", "#C44E00", "-"),
    ]:
        ax.plot(days, values, color=color, ls=style, lw=1.8, label=label)
    ax.set_title("Delayed activation background")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2]
    for values, label, color, style in [
        (background_raw, "raw", "#9E9E9E", "-"),
        (background_bgo, "active-shield pass", "#6B6ECF", "--"),
        (background_final, "final", "#2F4B7C", "-"),
    ]:
        ax.plot(days, values, color=color, ls=style, lw=1.8, label=label)
    ax.set_title("Prompt + delayed background")
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Rate (cps)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[3]
    ax.stackplot(days, prompt_fraction, delayed_fraction, colors=["#4C78A8", "#F58518"], labels=["prompt final fraction", "delayed final fraction"], alpha=0.75)
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Final background composition")
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Fraction")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="center right")

    for ax in axes:
        ax.axvline(15.0, color="black", ls=":", lw=1.0)

    fig.suptitle("Step06 time-dependent background component breakout", y=1.02, fontsize=13)
    fig.tight_layout()
    out = figure_path("stepwise_background_component_breakout.png")
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)

    return {
        "figure": rel(out),
        "inputs": [rel(STEP06_BACKGROUND)],
        "prompt_final_cps_range": [float(np.nanmin(prompt_final)), float(np.nanmax(prompt_final))],
        "delayed_final_cps_range": [float(np.nanmin(delayed_final)), float(np.nanmax(delayed_final))],
        "background_final_cps_range": [float(np.nanmin(background_final)), float(np.nanmax(background_final))],
        "day15_final_cps": {
            "prompt": float(prompt_final[np.argmin(np.abs(days - 15.0))]),
            "delayed": float(delayed_final[np.argmin(np.abs(days - 15.0))]),
            "background": float(background_final[np.argmin(np.abs(days - 15.0))]),
        },
    }


def csv_row(path: Path, key: str, value: str) -> dict[str, str]:
    return next(row for row in read_csv(path) if row[key] == value)


def plot_3sigma_results() -> dict[str, Any]:
    w1 = w1_mission_axis_metric()
    w2_row = csv_row(LINE_WINDOW, "window_id", "line_pm_3sigma")
    spot_row = csv_row(SPATIAL_LINE, "cut_id", "spot_r90")

    metrics = [
        {
            "label": "W1 mission axis",
            "selection": "500.994-521.006 keV, time-dependent",
            "Z20d": w1["Z20d"],
            "T3_day": w1["T3_day"],
            "flux_3sigma_20d": w1["flux_3sigma_20d"],
            "color": "#4C78A8",
        },
        {
            "label": "W2 line window",
            "selection": "510.58-511.42 keV, time-dependent",
            "Z20d": first_float(w2_row, "Z20d_time_dependent_at_reference_flux", "Z20d_at_reference_flux"),
            "T3_day": first_float(w2_row, "T3_day_time_dependent", "T3_day_constant_rate"),
            "flux_3sigma_20d": first_float(w2_row, "flux_3sigma_20d_time_dependent_ph_cm2_s", "flux_3sigma_20d_ph_cm2_s"),
            "color": "#F58518",
        },
        {
            "label": "W2 spot_r90",
            "selection": "W2 + detector-coupled r90 spot, time-dependent",
            "Z20d": first_float(spot_row, "Z20d_time_dependent_at_reference_flux", "Z20d_at_reference_flux"),
            "T3_day": first_float(spot_row, "T3_day_time_dependent", "T3_day_constant_rate"),
            "flux_3sigma_20d": first_float(spot_row, "flux_3sigma_20d_time_dependent_ph_cm2_s", "flux_3sigma_20d_ph_cm2_s"),
            "color": "#54A24B",
        },
    ]

    labels = [item["label"] for item in metrics]
    x = np.arange(len(metrics))
    colors = [item["color"] for item in metrics]

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.6))

    z = np.asarray([item["Z20d"] for item in metrics])
    axes[0].bar(x, z, color=colors, alpha=0.82)
    axes[0].axhline(3.0, color="#D62728", ls="--", lw=1.2, label="3 sigma")
    axes[0].set_ylabel("Z after 20 days")
    axes[0].set_xticks(x, labels, rotation=22, ha="right")
    axes[0].set_title("Counting significance at 1e-4 flux")
    axes[0].grid(True, axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)

    t3 = np.asarray([item["T3_day"] for item in metrics])
    axes[1].bar(x, t3, color=colors, alpha=0.82)
    axes[1].axhline(MISSION_DAYS, color="#D62728", ls="--", lw=1.2, label="20-day mission")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("T3 (days)")
    axes[1].set_xticks(x, labels, rotation=22, ha="right")
    axes[1].set_title("3-sigma time")
    axes[1].grid(True, axis="y", which="both", alpha=0.25)
    axes[1].legend(fontsize=8)

    flux = np.asarray([item["flux_3sigma_20d"] for item in metrics])
    axes[2].bar(x, flux, color=colors, alpha=0.82)
    axes[2].set_yscale("log")
    axes[2].set_ylabel("20-day 3-sigma flux (ph cm$^{-2}$ s$^{-1}$)")
    axes[2].set_xticks(x, labels, rotation=22, ha="right")
    axes[2].set_title("Flux threshold")
    axes[2].grid(True, axis="y", which="both", alpha=0.25)

    for ax, values in zip(axes, (z, t3, flux)):
        for xi, value in zip(x, values):
            ax.annotate(fmt(float(value), 3), (xi, float(value)), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)

    fig.suptitle("Step08 headline 3-sigma calculation results", y=1.02, fontsize=13)
    fig.tight_layout()
    out = figure_path("stepwise_3sigma_headline_results.png")
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)

    return {
        "figure": rel(out),
        "inputs": [rel(STEP08_T3), rel(LINE_WINDOW), rel(SPATIAL_LINE)],
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "metrics": [
            {
                "label": item["label"],
                "selection": item["selection"],
                "Z20d": item["Z20d"],
                "T3_day": item["T3_day"],
                "flux_3sigma_20d_ph_cm2_s": item["flux_3sigma_20d"],
            }
            for item in metrics
        ],
    }


def plot_spectrum_windows() -> dict[str, Any]:
    focus = load_json(FOCUS_RESPONSE)
    rows = read_csv(SPECTRUM)
    energy = np.asarray([as_float(row, "energy_center_keV") for row in rows])

    raw = np.asarray([as_float(row, "raw_cps_per_keV") for row in rows])
    final = np.asarray([as_float(row, "both_cps_per_keV") for row in rows])
    final_prompt = np.asarray([as_float(row, "both_prompt_cps_per_keV") for row in rows])
    final_delayed = np.asarray([as_float(row, "both_delayed_cps_per_keV") for row in rows])

    w1 = focus["windows"]["W1_design_passband"]
    w2 = focus["windows"]["W2_511_pm_420eV"]
    w1_checks = focus["window_checks"]["W1_design_passband"]
    w2_checks = focus["window_checks"]["W2_511_pm_420eV"]

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.step(energy, raw, where="mid", color="#9E9E9E", lw=1.0, alpha=0.8, label="raw")
    ax.step(energy, final_delayed, where="mid", color="#F58518", lw=1.3, label="final delayed")
    ax.step(energy, final_prompt, where="mid", color="#54A24B", lw=1.3, label="final prompt")
    ax.step(energy, final, where="mid", color="#4C78A8", lw=2.0, label="final prompt+delayed")
    ax.axvspan(float(w1["lo_keV"]), float(w1["hi_keV"]), color="#4C78A8", alpha=0.10, label="Laue W1 passband")
    ax.axvspan(float(w2["lo_keV"]), float(w2["hi_keV"]), color="#D62728", alpha=0.18, label="W2 line window")
    ax.axvline(511.0, color="black", ls=":", lw=1.0)
    ax.set_yscale("log")
    ax.set_xlim(480.0, 550.0)
    ax.set_xlabel("TES event energy (keV)")
    ax.set_ylabel("Non-X-ray background rate (cps/keV)")
    ax.set_title("Step09 day-15 background spectrum with Laue W1 and W2 windows")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, ncols=2, loc="upper right")

    text = (
        f"W1 {float(w1['lo_keV']):.3f}-{float(w1['hi_keV']):.3f} keV: "
        f"{float(w1_checks['background_both_cps']):.3g} cps\n"
        f"W2 {float(w2['lo_keV']):.2f}-{float(w2['hi_keV']):.2f} keV: "
        f"{float(w2_checks['background_both_cps']):.3g} cps"
    )
    ax.text(0.02, 0.04, text, transform=ax.transAxes, fontsize=8, va="bottom", bbox={"facecolor": "white", "alpha": 0.76, "edgecolor": "#CCCCCC"})

    fig.tight_layout()
    out = figure_path("stepwise_spectrum_laue_w2_windows.png")
    fig.savefig(out, dpi=220)
    plt.close(fig)

    return {
        "figure": rel(out),
        "inputs": [rel(SPECTRUM), rel(FOCUS_RESPONSE)],
        "W1_design_passband_keV": [float(w1["lo_keV"]), float(w1["hi_keV"])],
        "W2_line_window_keV": [float(w2["lo_keV"]), float(w2["hi_keV"])],
        "W1_background_cps": float(w1_checks["background_both_cps"]),
        "W2_background_cps": float(w2_checks["background_both_cps"]),
    }


def write_readme(summary: dict[str, Any]) -> None:
    lines = [
        "# Stepwise Figure Pack",
        "",
        "These figures are compact index products built from the current Step06/08/09 authority tables. They do not rerun transport.",
        "",
        "| Requirement | Figure | Primary inputs |",
        "| --- | --- | --- |",
        f"| Trajectory time variation curve | `{summary['trajectory_time_variation']['figure']}` | Step06 trajectory/background CSV |",
        f"| Background component breakout | `{summary['background_component_breakout']['figure']}` | Step06 background time-variation CSV |",
        f"| 3-sigma significance result plot | `{summary['headline_3sigma_results']['figure']}` | Step08 W1 mission axis plus W2/spot time-fold sidecars |",
        f"| Spectrum with Laue and W2 windows | `{summary['spectrum_laue_w2_windows']['figure']}` | Step09 non-X-ray background spectrum and detector-coupled focus response |",
        "",
        "Historical Records references consulted for organization and plotting style:",
        "",
        "- `COSMOSRAY_BALLOON_SIM/Records/03_mission_time_variation/mission_time_variation.md`",
        "- `COSMOSRAY_BALLOON_SIM/Records/05_laue_current_mainline/source_significance_time_dependent_20260522/README.md`",
        "- `COSMOSRAY_BALLOON_SIM/Records/08_nai_shield_substitution_20260522/README.md`",
        "",
        "Headline 3-sigma values:",
        "",
        "| selection | Z20d at 1e-4 | T3 day | 20-day 3-sigma flux |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in summary["headline_3sigma_results"]["metrics"]:
        lines.append(
            f"| {item['label']} | {fmt(float(item['Z20d']), 5)} | {fmt(float(item['T3_day']), 5)} | {fmt(float(item['flux_3sigma_20d_ph_cm2_s']), 5)} |"
        )
    lines.extend(
        [
            "",
            "Claim boundaries: W1 is the Step08 mission-axis counting fold; W2 and spot_r90 are detector-coupled direct-expectation sidecars folded over the Step06 time axis. The current chain includes the focused optics EventList handoff, but not a separate upstream optics self-background transport.",
            "",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summary = {
        "status": "PASS",
        "scope": "Compact figure pack for CURRENT_PROGRESS_STEP_BREAKDOWN.md",
        "trajectory_time_variation": plot_trajectory_time_variation(),
        "background_component_breakout": plot_background_component_breakout(),
        "headline_3sigma_results": plot_3sigma_results(),
        "spectrum_laue_w2_windows": plot_spectrum_windows(),
        "source_policy": {
            "project_memory": "Use the Step09 detector-coupled focused EventList chain as the current science authority.",
            "old_records_reference": "COSMOSRAY_BALLOON_SIM/Records uses the same pattern of durable figure records for trajectory and significance scans; it is historical reference material, not the current numeric authority.",
        },
    }
    write_json(OUT / "stepwise_figure_pack_summary.json", summary)
    write_readme(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
