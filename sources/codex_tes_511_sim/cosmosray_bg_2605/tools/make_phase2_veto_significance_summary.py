#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build cumulative 3-sigma time curves for a configured 511-keV source case."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "reports" / "phase2_real_flight_physical_production"
R2 = ROOT / "reports2.0"

PROMPT = PHASE2 / "prompt_reweight_real" / "prompt_final_rate_by_time_window.csv"
SCI_TRANS = PHASE2 / "environment_grid_real" / "science_atmospheric_transmission.csv"
DAY15_RATES = PHASE2 / "tables" / "image8_style_component_rates.csv"
DELAYED_ACTIVITY = R2 / "04_FIGURES" / "phase2" / "phase2_total_delayed_activity_time_series.csv"
SOURCE_CASE_RATES = R2 / "09_SOURCE_CASES_ABC" / "source_case_rates.csv"
SOURCE_CASE_DETECTABILITY = R2 / "09_SOURCE_CASES_ABC" / "detectability_A_GC_POINT.csv"

OUT_FIG = R2 / "04_FIGURES" / "phase2" / "phase2_A_GC_gaussian_fwhm1p5_veto_significance_vs_time.png"
OUT_CSV = R2 / "04_FIGURES" / "phase2" / "phase2_A_GC_gaussian_fwhm1p5_veto_significance_vs_time.csv"

WINDOW = "broad_480_550"
SOURCE_CASE_ID = "A_GC_POINT_SgrA_anchor"
SOURCE_MODEL = "gaussian_fwhm_1p5"
SOURCE_DESIGN = "baseline Ta6"
SOURCE_ANGULAR_RADIUS_ARCMIN = 0.0
SOURCE_LABEL = "A GC compact source case, Gaussian FWHM 1.5 keV"
SOURCE_FLUX = 8.0e-5
SCIENCE_T_REF = 0.7390423888027
DAY15 = 15.0
SECONDS_PER_DAY = 86400.0
STAGES = [
    ("raw", "No veto", "#4C78A8"),
    ("bgo", "BGO veto", "#F58518"),
    ("final", "BGO+Compton/FoV", "#54A24B"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fnum(x: float, nd: int = 3) -> str:
    if not math.isfinite(x):
        return "not reached"
    return f"{x:.{nd}f}"


def crossing_time(days: np.ndarray, z: np.ndarray, threshold: float = 3.0) -> float | None:
    above = np.flatnonzero(z >= threshold)
    if len(above) == 0:
        return None
    i = int(above[0])
    if i == 0:
        return float(days[0])
    x0, x1 = float(days[i - 1]), float(days[i])
    y0, y1 = float(z[i - 1]), float(z[i])
    if y1 == y0:
        return x1
    return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)


def source_case_row(rows: list[dict[str, str]]) -> dict[str, str]:
    for r in rows:
        if (
            r["case_id"] == SOURCE_CASE_ID
            and r["model_id"] == SOURCE_MODEL
            and abs(float(r["flux_ph_cm2_s"]) - SOURCE_FLUX) < 1e-12
            and abs(float(r.get("angular_radius_arcmin") or 0.0) - SOURCE_ANGULAR_RADIUS_ARCMIN) < 1e-12
        ):
            return r
    raise RuntimeError(
        f"Missing source row: {SOURCE_CASE_ID}, {SOURCE_MODEL}, "
        f"F={SOURCE_FLUX}, radius={SOURCE_ANGULAR_RADIUS_ARCMIN} arcmin"
    )


def detectability_row(rows: list[dict[str, str]]) -> dict[str, str]:
    for r in rows:
        if (
            r["case_id"] == SOURCE_CASE_ID
            and r["line_model"] == SOURCE_MODEL
            and r["design_case"] == SOURCE_DESIGN
            and abs(float(r["flux_ph_cm2_s"]) - SOURCE_FLUX) < 1e-12
        ):
            return r
    raise RuntimeError(
        f"Missing detectability row: {SOURCE_CASE_ID}, {SOURCE_MODEL}, "
        f"{SOURCE_DESIGN}, F={SOURCE_FLUX}"
    )


def main() -> int:
    prompt_rows = [
        r for r in read_csv(PROMPT)
        if r["window"] == WINDOW and r["particle"] == "TOTAL"
    ]
    trans_rows = read_csv(SCI_TRANS)
    delayed_rows = read_csv(DELAYED_ACTIVITY)
    day15_rows = [r for r in read_csv(DAY15_RATES) if r["window"] == WINDOW]

    day15_by_component = {r["component"]: r for r in day15_rows}
    delayed_day15 = day15_by_component["delayed"]
    science_day15 = day15_by_component["science"]
    source_case = source_case_row(read_csv(SOURCE_CASE_RATES))
    detectability = detectability_row(read_csv(SOURCE_CASE_DETECTABILITY))
    mono_science_final_cps = float(science_day15["final_cps"])
    source_case_final_cps = float(source_case["final_rate_cps"])
    source_stage_scale = source_case_final_cps / mono_science_final_cps
    diffuse_foreground_cps = float(detectability["B_diffuse_cps"])

    delayed_activity_by_day = {round(float(r["day"]), 6): float(r["total_delayed_activity_Bq"]) for r in delayed_rows}
    day15_activity = delayed_activity_by_day.get(DAY15)
    if not day15_activity or day15_activity <= 0:
        day15_activity = min(
            delayed_activity_by_day.values(),
            key=lambda v: abs(v - float(delayed_rows[-1]["total_delayed_activity_Bq"])),
        )

    trans_by_bin = {int(r["time_bin_id"]): r for r in trans_rows}

    cum_signal = {stage: 0.0 for stage, _, _ in STAGES}
    cum_background = {stage: 0.0 for stage, _, _ in STAGES}
    rows: list[dict[str, Any]] = []
    prev_t = 0.0
    for r in prompt_rows:
        ibin = int(r["time_bin_id"])
        day = float(r["day_mid"])
        tr = trans_by_bin[ibin]
        t = float(tr["time_mid_s"])
        dt = max(t - prev_t, 0.0)
        prev_t = t

        delayed_activity = delayed_activity_by_day.get(round(day, 6), 0.0)
        delayed_scale = delayed_activity / day15_activity if day15_activity > 0 else 0.0
        t_atm = float(tr["T_atm_511"]) * float(tr["earth_occultation_factor"])
        source_scale = t_atm / SCIENCE_T_REF if SCIENCE_T_REF > 0 else 0.0

        out: dict[str, Any] = {
            "time_bin_id": ibin,
            "day": day,
            "dt_s": dt,
            "T_atm_511": t_atm,
            "delayed_activity_Bq": delayed_activity,
            "delayed_scale_vs_day15": delayed_scale,
            "source_scale_vs_reference": source_scale,
            "source_case_id": SOURCE_CASE_ID,
            "source_model": SOURCE_MODEL,
            "source_flux_ph_cm2_s": SOURCE_FLUX,
            "source_stage_scale_vs_mono_1e_minus_4": source_stage_scale,
            "diffuse_foreground_cps": diffuse_foreground_cps,
        }
        for stage, _, _ in STAGES:
            prompt_rate = float(r[f"{stage}_cps"])
            delayed_rate = float(delayed_day15[f"{stage}_cps"]) * delayed_scale
            source_rate = float(science_day15[f"{stage}_cps"]) * source_stage_scale * source_scale
            background_rate = prompt_rate + delayed_rate + diffuse_foreground_cps
            cum_signal[stage] += source_rate * dt
            cum_background[stage] += background_rate * dt
            z = cum_signal[stage] / math.sqrt(cum_background[stage]) if cum_background[stage] > 0 else 0.0
            out[f"{stage}_prompt_cps"] = prompt_rate
            out[f"{stage}_delayed_cps"] = delayed_rate
            out[f"{stage}_background_cps"] = background_rate
            out[f"{stage}_source_cps"] = source_rate
            out[f"{stage}_cum_source_counts"] = cum_signal[stage]
            out[f"{stage}_cum_background_counts"] = cum_background[stage]
            out[f"{stage}_cumulative_Z"] = z
        rows.append(out)

    write_csv(OUT_CSV, rows)

    days = np.asarray([float(r["day"]) for r in rows])
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    zoom_ax = ax.inset_axes([0.08, 0.16, 0.40, 0.36])
    summary_lines = []
    for stage, label, color in STAGES:
        z = np.asarray([float(r[f"{stage}_cumulative_Z"]) for r in rows])
        ax.plot(days, z, lw=2.2, color=color, label=label)
        zoom_ax.plot(days, z, lw=2.0, color=color)
        cross = crossing_time(days, z)
        final_z = float(z[-1])
        if cross is None:
            extrap_days = float(days[-1]) * (3.0 / final_z) ** 2 if final_z > 0 else float("nan")
            summary_lines.append(f"{label}: Z20={final_z:.2f}, 3 sigma not reached; repeat-profile extrap. {extrap_days:.1f} d")
        else:
            ax.axvline(cross, color=color, ls=":", lw=1.2, alpha=0.8)
            summary_lines.append(f"{label}: reaches 3 sigma at day {cross:.2f}; Z20={final_z:.2f}")

    ax.axhline(3.0, color="#D62728", ls="--", lw=1.5, label="3 sigma")
    ax.set_xlabel("Elapsed flight time (day)")
    ax.set_ylabel("Cumulative significance Z = S / sqrt(B)")
    ax.set_title("Phase2 time-variable 480-550 keV detectability for the A GC source case")
    ax.set_xlim(0, float(days[-1]))
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=9)

    zoom_ax.set_xlim(0, float(days[-1]))
    zoom_ax.set_ylim(0, 0.50)
    zoom_ax.grid(True, alpha=0.25)
    zoom_ax.set_title("zoom: actual accumulated Z", fontsize=9)
    zoom_ax.tick_params(labelsize=8)

    text = (
        f"{SOURCE_LABEL}\n"
        f"{SOURCE_CASE_ID}; F={SOURCE_FLUX:.1e} ph cm$^{{-2}}$ s$^{{-1}}$; radius={SOURCE_ANGULAR_RADIUS_ARCMIN:.0f} arcmin\n"
        "Signal: source-case response x Phase2 atmospheric transmission. Background: prompt + delayed activity + diffuse foreground.\n"
        + "\n".join(summary_lines)
    )
    ax.text(
        0.98,
        0.92,
        text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.4,
        bbox=dict(facecolor="white", alpha=0.88, edgecolor="none"),
    )

    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)
    print(OUT_FIG)
    print(OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
