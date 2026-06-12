#!/usr/bin/env python3
"""Build revised new_figure a/b/c panels from current W1/W2 authority tables."""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "stepwise_maintenance" / "new_figure"

STEP07_SPECTRA = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_spectrum_summary.csv"
STEP08_T3 = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "t3_t5_summary.csv"
STEP08_CUMULATIVE = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "cumulative_significance_by_case.csv"
LINE_SUMMARY = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "line_window_sensitivity.csv"
LINE_CURVE = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "line_window_time_dependent_significance.csv"
SPATIAL_SUMMARY = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "spatial_line_proxy.csv"
SPATIAL_CURVE = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "spatial_line_time_dependent_significance.csv"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
SPATIAL_CURRENT = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_spatial_line_cuts.csv"

REFERENCE_FLUX = 1.0e-4
V404_F0 = 6.5e-3
V404_F0_UNC = 1.6e-3
REFERENCE_SPECTRUM = "v404_kT170_no_shift"
REFERENCE_SCALES = [0.2, 0.5, 1.0, 2.0, 5.0]
ONE_MS = 1.0e6
CAM511_FIG11_APPROX_F3_1MS = 3.0e-6
CAM511_FIG11_SOURCE_RATE_PH_S = 0.1
CAM511_FIG11_AEFF_CM2 = 50.89
CAM511_FIG11_DETECTION_EFFICIENCY = 0.65
SPI_511_NARROW_LINE_F3_1MS = 4.8e-5
COSI_511_LINE_SENS_2YR_PH_CM2_S = 1.2e-5
COSI_SURVEY_DURATION_S = 2.0 * 365.25 * 86400.0
COSI_511_LINE_F3_1MS_SQRT_SCALED = COSI_511_LINE_SENS_2YR_PH_CM2_S * math.sqrt(
    COSI_SURVEY_DURATION_S / ONE_MS
)

FLUX_GRID = [
    1.0e-5,
    2.0e-5,
    3.0e-5,
    5.0e-5,
    8.0e-5,
    1.0e-4,
    1.5e-4,
    2.0e-4,
    3.0e-4,
    5.0e-4,
    8.0e-4,
    1.0e-3,
    1.3e-3,
    2.0e-3,
    3.0e-3,
    3.25e-3,
    5.0e-3,
    6.5e-3,
    1.0e-2,
    1.3e-2,
    3.25e-2,
]

WINDOWS = [
    {
        "id": "W1",
        "title": "W1 500.994-521.006 keV",
        "fraction_key": "analysis_response_fraction_of_511",
        "curve_source": "Step08 W1 mission-axis counting fold",
        "color": "#5477C4",
    },
    {
        "id": "W2",
        "title": "W2 510.58-511.42 keV",
        "fraction_key": "fraction_510p3_511p8",
        "curve_source": "Step08 line_pm_3sigma time-dependent sidecar",
        "color": "#CC6F47",
    },
]

MODELS = [
    ("v404_kT30_no_shift", "kT30_no_shift", "#5477C4", "-"),
    ("v404_kT170_no_shift", "kT170_no_shift", "#CC6F47", "-"),
    ("v404_redshift_z0p10_narrow_proxy", "redshift_z0p10_narrow_proxy", "#71B436", "--"),
    ("v404_redshift_z0p10_broad_proxy", "redshift_z0p10_broad_proxy", "#BD569B", "-"),
]

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

PNG_TAG = "_BGO" if ROOT.name == "new_geo_re_2" else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: Any, default: float = math.nan) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if text == "":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def fmt_days(days: float) -> str:
    if not math.isfinite(days):
        return "inf"
    if days >= 1000.0:
        return f"{days:.0f} d"
    if days >= 10.0:
        return f"{days:.1f} d"
    if days >= 1.0:
        return f"{days:.2f} d"
    return f"{days:.3f} d"


def fmt_flux(value: float) -> str:
    return f"{value:.3g}"


def setup_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(TOKENS["panel"])
    ax.grid(True, which="both", color=TOKENS["grid"], lw=0.8, alpha=0.65)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TOKENS["axis"])
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=TOKENS["ink"], labelsize=9)


def curve_from_rows(rows: list[dict[str, str]]) -> list[dict[str, float]]:
    curve = []
    elapsed_s = 0.0
    for row in sorted(rows, key=lambda r: int(float(r["time_bin_id"]))):
        dt_s = fnum(row.get("dt_s", row.get("dt_active_s")))
        elapsed_s += dt_s
        elapsed_stop_day = fnum(row.get("elapsed_stop_day"))
        if not math.isfinite(elapsed_stop_day):
            elapsed_stop_day = elapsed_s / 86400.0
        curve.append(
            {
                "time_bin_id": fnum(row["time_bin_id"]),
                "elapsed_stop_day": elapsed_stop_day,
                "dt_s": dt_s,
                "source_counts_ref": fnum(row["cumulative_source_counts"]),
                "background_counts": fnum(row["cumulative_background_counts"]),
            }
        )
    return curve


def load_w1_curve() -> list[dict[str, float]]:
    rows = [
        row
        for row in read_csv(STEP08_CUMULATIVE)
        if row["analysis_case_id"] == "A_mono_511_F0.0001_R0arcmin"
    ]
    return curve_from_rows(rows)


def load_w2_curve() -> list[dict[str, float]] | None:
    if not LINE_CURVE.exists():
        return None
    rows = [row for row in read_csv(LINE_CURVE) if row["selection_id"] == "line_pm_3sigma"]
    return curve_from_rows(rows)


def load_spot_curve(cut_id: str = "spot_r90") -> list[dict[str, float]] | None:
    if not SPATIAL_CURVE.exists():
        return None
    rows = [row for row in read_csv(SPATIAL_CURVE) if row["cut_id"] == cut_id]
    return curve_from_rows(rows)


def result_for_factor(curve: list[dict[str, float]], factor: float) -> dict[str, Any]:
    if factor <= 0.0 or not math.isfinite(factor):
        return {
            "Z20d": 0.0,
            "T3_days": math.inf,
            "T3_status": "no_response",
            "flux_3sigma_20d_ph_cm2_s": math.inf,
        }
    days: list[float] = []
    zvals: list[float] = []
    for row in curve:
        source = row["source_counts_ref"] * factor
        background = row["background_counts"]
        z = source / math.sqrt(background) if background > 0.0 else 0.0
        days.append(row["elapsed_stop_day"])
        zvals.append(z)
    t3 = math.inf
    status = "extrapolated_beyond_20d"
    prev_day = 0.0
    prev_z = 0.0
    for day, z in zip(days, zvals):
        if z >= 3.0:
            if z <= prev_z:
                t3 = day
            else:
                t3 = prev_day + (3.0 - prev_z) * (day - prev_day) / (z - prev_z)
            status = "mission_internal_crossing"
            break
        prev_day = day
        prev_z = z
    final_day = days[-1]
    final_z = zvals[-1]
    if not math.isfinite(t3):
        if final_z > 0.0:
            t3 = final_day * (3.0 / final_z) ** 2
        else:
            t3 = math.inf
            status = "no_response"
    flux3 = REFERENCE_FLUX * 3.0 / final_z if final_z > 0.0 else math.inf
    return {
        "Z20d": final_z,
        "T3_days": t3,
        "T3_status": status,
        "flux_3sigma_20d_ph_cm2_s": flux3,
    }


def constant_rate_result(z20_ref: float, factor: float) -> dict[str, Any]:
    final_z = z20_ref * factor if factor > 0.0 and math.isfinite(factor) else 0.0
    if final_z <= 0.0:
        return {
            "Z20d": 0.0,
            "T3_days": math.inf,
            "T3_status": "no_response",
            "flux_3sigma_20d_ph_cm2_s": math.inf,
        }
    t3 = 20.0 * (3.0 / final_z) ** 2
    return {
        "Z20d": final_z,
        "T3_days": t3,
        "T3_status": "mission_internal_crossing" if t3 <= 20.0 else "extrapolated_beyond_20d",
        "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / final_z,
    }


def current_line_summary_row() -> dict[str, str] | None:
    if not FOCUS_RESPONSE.exists():
        return None
    check = read_json(FOCUS_RESPONSE).get("window_checks", {}).get("W2_511_pm_420eV")
    if not check:
        return None
    return {
        "window_id": "line_pm_3sigma",
        "source_window_id": "W2_511_pm_420eV",
        "label": "511 +/- 3 sigma_TES / W2 511 +/- 420 eV",
        "background_cps": str(check["background_both_cps"]),
        "science_cps_at_reference_flux": str(check["signal_both_cps_at_reference_flux"]),
        "science_response_cps_per_ph_cm2_s": str(check["signal_both_response_cps_per_ph_cm2_s"]),
        "Z20d_at_reference_flux": str(check["Z20d_both"]),
        "T3_day_constant_rate": str(check["T3_day_constant_rate"]),
        "T3_status": str(check["T3_status"]),
        "flux_3sigma_20d_ph_cm2_s": str(check["flux_3sigma_20d_ph_cm2_s"]),
        "_authority_source": "Step09 detector_coupled_focus_response current W2 constant-rate sidecar",
    }


def has_time_dependent_metrics(row: dict[str, str]) -> bool:
    keys = (
        "Z20d_time_dependent_at_reference_flux",
        "total_source_counts_time_dependent",
        "total_background_counts_time_dependent",
    )
    return all(math.isfinite(fnum(row.get(key))) for key in keys)


def line_summary_row() -> dict[str, str]:
    if LINE_SUMMARY.exists():
        row = next(row for row in read_csv(LINE_SUMMARY) if row["window_id"] == "line_pm_3sigma")
        row["_authority_source"] = "Step08 line_pm_3sigma time-dependent sidecar"
        return row
    current = current_line_summary_row()
    if current:
        return current
    raise FileNotFoundError(f"missing line summary: {LINE_SUMMARY}")


def spatial_summary_row(cut_id: str) -> dict[str, str]:
    if SPATIAL_SUMMARY.exists():
        row = next(row for row in read_csv(SPATIAL_SUMMARY) if row["cut_id"] == cut_id)
        row["_authority_source"] = f"Step08 spatial_line_proxy {cut_id} time-dependent sidecar"
        return row
    if SPATIAL_CURRENT.exists():
        for row in read_csv(SPATIAL_CURRENT):
            if row["cut_id"] == cut_id:
                row["_authority_source"] = f"Step09 detector_coupled_spatial_line_cuts {cut_id} current sidecar"
                return row
    raise FileNotFoundError(f"missing spatial summary: {SPATIAL_SUMMARY}")


def window_result(window_id: str, curves: dict[str, list[dict[str, float]] | None], factor: float) -> dict[str, Any]:
    curve = curves.get(window_id)
    if curve:
        return result_for_factor(curve, factor)
    if window_id == "W2":
        line = line_summary_row()
        return constant_rate_result(fnum(line["Z20d_at_reference_flux"]), factor)
    raise ValueError(f"No curve or fallback result for {window_id}")


def response_source_label(window: dict[str, Any], curves: dict[str, list[dict[str, float]] | None]) -> str:
    if curves.get(window["id"]):
        return window["curve_source"]
    if window["id"] == "W2":
        return line_summary_row().get("_authority_source", "Step08 line_pm_3sigma constant-rate sidecar")
    return window["curve_source"]


def total_duration_s(curve: list[dict[str, float]]) -> float:
    return sum(row["dt_s"] for row in curve if math.isfinite(row["dt_s"]))


def one_ms_equivalent(row: dict[str, str], curve: list[dict[str, float]]) -> dict[str, float]:
    duration_s = total_duration_s(curve)
    if duration_s <= 0.0:
        raise ValueError("non-positive curve duration")
    z20 = fnum(row["Z20d_time_dependent_at_reference_flux"])
    z1ms = z20 * math.sqrt(ONE_MS / duration_s)
    flux3_1ms = REFERENCE_FLUX * 3.0 / z1ms
    source_1ms = fnum(row["total_source_counts_time_dependent"]) * ONE_MS / duration_s
    background_1ms = fnum(row["total_background_counts_time_dependent"]) * ONE_MS / duration_s
    return {
        "duration_s": duration_s,
        "Z_1Ms_at_reference_flux": z1ms,
        "F3_1Ms_ph_cm2_s": flux3_1ms,
        "source_counts_1Ms_at_reference_flux": source_1ms,
        "background_counts_1Ms": background_1ms,
    }


def one_ms_from_rate_summary(row: dict[str, str]) -> dict[str, float]:
    source_1ms = fnum(row.get("science_cps_at_reference_flux", row.get("signal_cps_at_reference_flux"))) * ONE_MS
    background_1ms = fnum(row["background_cps"]) * ONE_MS
    z1ms = source_1ms / math.sqrt(background_1ms) if background_1ms > 0.0 else 0.0
    return {
        "duration_s": ONE_MS,
        "Z_1Ms_at_reference_flux": z1ms,
        "F3_1Ms_ph_cm2_s": REFERENCE_FLUX * 3.0 / z1ms if z1ms > 0.0 else math.inf,
        "source_counts_1Ms_at_reference_flux": source_1ms,
        "background_counts_1Ms": background_1ms,
    }


def one_ms_for_row(row: dict[str, str], curve: list[dict[str, float]] | None) -> dict[str, float]:
    if curve and has_time_dependent_metrics(row):
        return one_ms_equivalent(row, curve)
    return one_ms_from_rate_summary(row)


def load_model_fractions() -> dict[str, dict[str, float]]:
    rows = read_csv(STEP07_SPECTRA)
    by_model: dict[str, dict[str, float]] = {}
    for row in rows:
        model_id = row["model_id"]
        if not model_id.startswith("v404_"):
            continue
        by_model[model_id] = {
            "W1": fnum(row["analysis_response_fraction_of_511"], 0.0),
            "W2": fnum(row["fraction_510p3_511p8"], 0.0),
            "fraction_480_550": fnum(row["fraction_480_550"], 0.0),
        }
    return by_model


def build_scan_rows(curves: dict[str, list[dict[str, float]] | None], fractions: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        window_id = window["id"]
        for model_id, label, _color, _ls in MODELS:
            response_fraction = fractions[model_id][window_id]
            for flux in FLUX_GRID:
                factor = (flux / REFERENCE_FLUX) * response_fraction
                result = window_result(window_id, curves, factor)
                rows.append(
                    {
                        "figure_panel": "a",
                        "route_id": "laue_current",
                        "window": window_id,
                        "window_label": window["title"],
                        "response_curve_source": response_source_label(window, curves),
                        "spectrum": model_id,
                        "spectrum_label": label,
                        "input_flux_top_atm_ph_cm2_s": f"{flux:.12e}",
                        "response_fraction_of_511": f"{response_fraction:.12e}",
                        "effective_reference_factor": f"{factor:.12e}",
                        "Z20d": f"{result['Z20d']:.12e}",
                        "T3_days_reported": f"{result['T3_days']:.12e}" if math.isfinite(result["T3_days"]) else "inf",
                        "T3_report_method": result["T3_status"],
                        "flux_3sigma_20d_ph_cm2_s": f"{result['flux_3sigma_20d_ph_cm2_s']:.12e}"
                        if math.isfinite(result["flux_3sigma_20d_ph_cm2_s"])
                        else "inf",
                    }
                )
    return rows


def build_scaled_rows(curves: dict[str, list[dict[str, float]] | None], fractions: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        window_id = window["id"]
        response_fraction = fractions[REFERENCE_SPECTRUM][window_id]
        for scale in REFERENCE_SCALES:
            flux = V404_F0 * scale
            factor = (flux / REFERENCE_FLUX) * response_fraction
            result = window_result(window_id, curves, factor)
            rows.append(
                {
                    "figure_panel": "b",
                    "route_id": "laue_current",
                    "window": window_id,
                    "window_label": window["title"],
                    "response_curve_source": response_source_label(window, curves),
                    "spectrum": REFERENCE_SPECTRUM,
                    "scale_factor_vs_orbit1555_flux": scale,
                    "input_flux_top_atm_ph_cm2_s": f"{flux:.12e}",
                    "response_fraction_of_511": f"{response_fraction:.12e}",
                    "effective_reference_factor": f"{factor:.12e}",
                    "Z20d": f"{result['Z20d']:.12e}",
                    "T3_days_reported": f"{result['T3_days']:.12e}" if math.isfinite(result["T3_days"]) else "inf",
                    "T3_report_method": result["T3_status"],
                    "paper_flux_ph_cm2_s": V404_F0,
                    "paper_flux_unc_ph_cm2_s": V404_F0_UNC,
                }
            )
    return rows


def plot_a(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.2), sharey=True)
    fig.patch.set_facecolor(TOKENS["surface"])
    all_y = [fnum(row["T3_days_reported"]) for row in rows if math.isfinite(fnum(row["T3_days_reported"]))]
    ymin = max(min(all_y) * 0.45, 0.01)
    ymax = max(max(all_y) * 4.0, 1.0e3)

    for ax, window in zip(axes, WINDOWS):
        setup_axes(ax)
        window_rows = [row for row in rows if row["window"] == window["id"]]
        for model_id, label, color, linestyle in MODELS:
            model_rows = [row for row in window_rows if row["spectrum"] == model_id]
            xs = np.asarray([fnum(row["input_flux_top_atm_ph_cm2_s"]) for row in model_rows], dtype=float)
            ys = np.asarray([fnum(row["T3_days_reported"]) for row in model_rows], dtype=float)
            finite = np.isfinite(ys)
            if np.any(finite):
                ax.plot(xs[finite], ys[finite], marker="o", ms=4.0, lw=1.6, color=color, ls=linestyle, label=label)
                scaled_fluxes = np.asarray([V404_F0 * s for s in REFERENCE_SCALES])
                mask = np.isin(np.round(xs, 12), np.round(scaled_fluxes, 12)) & finite
                ax.scatter(xs[mask], ys[mask], s=48, facecolors="none", edgecolors=TOKENS["ink"], lw=1.1, zorder=4)
            else:
                ax.plot([], [], marker="o", ms=4.0, lw=1.4, color=color, ls=linestyle, label=f"{label} (0 response)")
        ax.axvspan(V404_F0 - V404_F0_UNC, V404_F0 + V404_F0_UNC, color="#C5CAD3", alpha=0.24, lw=0)
        ax.axvline(V404_F0, color=TOKENS["ink"], ls="--", lw=1.0)
        ax.annotate(
            "Siegert+2016\norbit 1555\n6.5e-3",
            xy=(V404_F0, min(ymax / 50.0, 2.0e8)),
            xytext=(8, 22),
            textcoords="offset points",
            fontsize=8,
            color=TOKENS["ink"],
            arrowprops={"arrowstyle": "-", "lw": 0.7, "color": TOKENS["ink"]},
        )
        if window["id"] == "W2":
            ax.legend(loc="lower left", fontsize=8, frameon=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(6.5e-6, 5.0e-2)
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel(r"input V404 feature flux (ph cm$^{-2}$ s$^{-1}$)")
        ax.set_title(window["title"], fontsize=13, color=TOKENS["ink"], pad=8)
    axes[0].set_ylabel("3-sigma exposure (days)")
    fig.suptitle("V404 benchmark flux scan with current time-dependent W1/W2 Laue response", fontsize=12, color=TOKENS["ink"])
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = OUT / "a_w1_w2.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_b(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.2))
    fig.patch.set_facecolor(TOKENS["surface"])
    for ax, window in zip(axes, WINDOWS):
        setup_axes(ax)
        sub = [row for row in rows if row["window"] == window["id"]]
        xs = np.asarray([fnum(row["scale_factor_vs_orbit1555_flux"]) for row in sub], dtype=float)
        ys = np.asarray([fnum(row["T3_days_reported"]) for row in sub], dtype=float)
        fluxes = np.asarray([fnum(row["input_flux_top_atm_ph_cm2_s"]) for row in sub], dtype=float)
        ax.plot(xs, ys, marker="o", ms=6, lw=2.0, color=window["color"])
        ax.axvline(1.0, color=TOKENS["ink"], ls="--", lw=1.0)
        ax.set_xlim(0.0, 5.35)
        ymax = max(ys) * 1.22
        ax.set_ylim(0.0, ymax)
        ax.set_xlabel(r"scale factor $F/F_0$ (linear)")
        ax.set_ylabel("3-sigma exposure (days)")
        ax.set_title(window["title"], fontsize=13, color=TOKENS["ink"], pad=8)
        for x, y, flux in zip(xs, ys, fluxes):
            va = "bottom"
            xytext = (0, 10)
            ha = "center"
            if y > 0.72 * ymax:
                va = "top"
                xytext = (9, -34) if x < 0.35 else (0, -34)
                ha = "left" if x < 0.35 else "center"
            elif x < 0.35:
                ha = "left"
                xytext = (8, 8)
            ax.annotate(
                f"{fmt_days(float(y))}\nF={fmt_flux(float(flux))}",
                xy=(x, y),
                xytext=xytext,
                textcoords="offset points",
                ha=ha,
                va=va,
                fontsize=8,
                color=TOKENS["ink"],
                arrowprops={"arrowstyle": "-", "lw": 0.6, "color": TOKENS["muted"]},
            )
    fig.suptitle(
        "V404 five scaled flux points, v404_kT170_no_shift, current Laue\n"
        r"$F_0=6.5\times10^{-3}\ \mathrm{ph\,cm^{-2}\,s^{-1}}$"
        " (Siegert+2016 orbit 1555)",
        fontsize=12,
        color=TOKENS["ink"],
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = OUT / f"b_w1_w2{PNG_TAG}.png"
    fig.savefig(out, dpi=220)
    if PNG_TAG:
        fig.savefig(OUT / "b_w1_w2.png", dpi=220)
    plt.close(fig)
    return out


def build_c_rows() -> list[dict[str, Any]]:
    line = line_summary_row()
    spot = spatial_summary_row("spot_r90")
    line_curve = load_w2_curve()
    spot_curve = load_spot_curve("spot_r90")
    line_equiv = one_ms_for_row(line, line_curve)
    spot_equiv = one_ms_for_row(spot, spot_curve)
    focus = read_json(FOCUS_RESPONSE)
    norm = focus["normalization"]
    reference_flux = fnum(norm["reference_flux_ph_cm2_s"])
    focused_plane_rate = fnum(norm["focused_plane_rate_cps_at_reference_flux"])
    v404_w2_fraction = load_model_fractions()[REFERENCE_SPECTRUM]["W2"]
    v404_w2_factor = (V404_F0 / REFERENCE_FLUX) * v404_w2_fraction
    cam511_input_counts = CAM511_FIG11_SOURCE_RATE_PH_S * ONE_MS
    cam511_detected_counts = cam511_input_counts * CAM511_FIG11_DETECTION_EFFICIENCY
    cam511_sky_equiv_flux = CAM511_FIG11_SOURCE_RATE_PH_S / CAM511_FIG11_AEFF_CM2
    line_source = (
        "Step08 line_pm_3sigma time-dependent fold; 1Ms equivalent uses the 20-day average rates"
        if line_curve and has_time_dependent_metrics(line)
        else f"{line.get('_authority_source', 'Step08 line_pm_3sigma constant-rate sidecar')}; 1Ms equivalent uses the current day-15 rates"
    )
    spot_source = (
        "Step08 spatial_line_proxy spot_r90 time-dependent fold; 1Ms equivalent uses the 20-day average rates"
        if spot_curve and has_time_dependent_metrics(spot)
        else f"{spot.get('_authority_source', 'Step08 spatial_line_proxy spot_r90 constant-rate sidecar')}; 1Ms equivalent uses the current day-15 rates"
    )
    rows: list[dict[str, Any]] = [
        {
            "label": "511-CAM Fig.11 approx",
            "scheme": "literature",
            "comparison_role": "sensitivity_and_signal_context",
            "F3_1Ms_ph_cm2_s": CAM511_FIG11_APPROX_F3_1MS,
            "F3_20d_time_dependent_ph_cm2_s": "",
            "Z_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_flux": cam511_detected_counts,
            "source_counts_1Ms_at_reference_signal": cam511_detected_counts,
            "input_signal_rate_ph_s": CAM511_FIG11_SOURCE_RATE_PH_S,
            "input_flux_top_atm_ph_cm2_s": "",
            "sky_equivalent_flux_ph_cm2_s": cam511_sky_equiv_flux,
            "background_counts_1Ms": "",
            "source": "511-CAM paper Fig. 11/Table 2: 0.1 ph/s source, 50.89 cm2 optics, 65% TES stack efficiency",
            "normalization_note": "CAM511 sensitivity point uses a much stronger simulation source than the current Laue 1e-4 ph cm-2 s-1 reference.",
        },
        {
            "label": "SPI manual",
            "scheme": "literature",
            "comparison_role": "sensitivity_context",
            "F3_1Ms_ph_cm2_s": SPI_511_NARROW_LINE_F3_1MS,
            "F3_20d_time_dependent_ph_cm2_s": "",
            "Z_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_signal": "",
            "input_signal_rate_ph_s": "",
            "input_flux_top_atm_ph_cm2_s": "",
            "sky_equivalent_flux_ph_cm2_s": "",
            "background_counts_1Ms": "",
            "source": "INTEGRAL/SPI Observer's Manual narrow-line marker",
            "normalization_note": "Literature sensitivity marker only; no common signal-count normalization is used here.",
        },
        {
            "label": "COSI 511 line",
            "scheme": "literature",
            "comparison_role": "sensitivity_context",
            "F3_1Ms_ph_cm2_s": COSI_511_LINE_F3_1MS_SQRT_SCALED,
            "F3_20d_time_dependent_ph_cm2_s": "",
            "Z_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_signal": "",
            "input_signal_rate_ph_s": "",
            "input_flux_top_atm_ph_cm2_s": "",
            "sky_equivalent_flux_ph_cm2_s": "",
            "background_counts_1Ms": "",
            "source": "COSI ICRC2023 Table 1: 3-sigma narrow-line point-source sensitivity at 0.511 MeV is 1.2e-5 ph cm-2 s-1 in 2 years of survey observations",
            "normalization_note": "Shown after sqrt(time) scaling from 2-year survey sensitivity to a 1Ms-equivalent marker; this is context only, not a direct pointed 1Ms COSI performance quote.",
        },
        {
            "label": "Laue W2 spot_r90",
            "scheme": "current_laue",
            "comparison_role": "sensitivity_and_signal_context",
            "F3_1Ms_ph_cm2_s": line_safe(spot_equiv["F3_1Ms_ph_cm2_s"]),
            "F3_20d_time_dependent_ph_cm2_s": fnum(
                spot.get("flux_3sigma_20d_time_dependent_ph_cm2_s", spot.get("flux_3sigma_20d_ph_cm2_s"))
            ),
            "Z_1Ms_at_reference_flux": line_safe(spot_equiv["Z_1Ms_at_reference_flux"]),
            "source_counts_1Ms_at_reference_flux": line_safe(spot_equiv["source_counts_1Ms_at_reference_flux"]),
            "source_counts_1Ms_at_reference_signal": line_safe(spot_equiv["source_counts_1Ms_at_reference_flux"]),
            "input_signal_rate_ph_s": focused_plane_rate,
            "input_flux_top_atm_ph_cm2_s": reference_flux,
            "sky_equivalent_flux_ph_cm2_s": reference_flux,
            "background_counts_1Ms": line_safe(spot_equiv["background_counts_1Ms"]),
            "source": spot_source,
            "normalization_note": "Current Laue mono-511 reference: 1e-4 ph cm-2 s-1 top-atmosphere flux, folded through A_eff and atmosphere.",
        },
        {
            "label": "Laue W2 diffuse",
            "scheme": "current_laue",
            "comparison_role": "sensitivity_and_signal_context",
            "F3_1Ms_ph_cm2_s": line_safe(line_equiv["F3_1Ms_ph_cm2_s"]),
            "F3_20d_time_dependent_ph_cm2_s": fnum(
                line.get("flux_3sigma_20d_time_dependent_ph_cm2_s", line.get("flux_3sigma_20d_ph_cm2_s"))
            ),
            "Z_1Ms_at_reference_flux": line_safe(line_equiv["Z_1Ms_at_reference_flux"]),
            "source_counts_1Ms_at_reference_flux": line_safe(line_equiv["source_counts_1Ms_at_reference_flux"]),
            "source_counts_1Ms_at_reference_signal": line_safe(line_equiv["source_counts_1Ms_at_reference_flux"]),
            "input_signal_rate_ph_s": focused_plane_rate,
            "input_flux_top_atm_ph_cm2_s": reference_flux,
            "sky_equivalent_flux_ph_cm2_s": reference_flux,
            "background_counts_1Ms": line_safe(line_equiv["background_counts_1Ms"]),
            "source": line_source,
            "normalization_note": "Current Laue mono-511 reference without the spot cut.",
        },
        {
            "label": "V404 kT170 W2",
            "scheme": "current_laue",
            "comparison_role": "signal_context_only",
            "F3_1Ms_ph_cm2_s": "",
            "F3_20d_time_dependent_ph_cm2_s": "",
            "Z_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_flux": "",
            "source_counts_1Ms_at_reference_signal": line_safe(line_equiv["source_counts_1Ms_at_reference_flux"]) * v404_w2_factor,
            "input_signal_rate_ph_s": focused_plane_rate * (V404_F0 / REFERENCE_FLUX) * v404_w2_fraction,
            "input_flux_top_atm_ph_cm2_s": V404_F0,
            "sky_equivalent_flux_ph_cm2_s": V404_F0 * v404_w2_fraction,
            "background_counts_1Ms": "",
            "source": f"{REFERENCE_SPECTRUM} W2 spectral fraction folded through current Laue W2 time-dependent response",
            "normalization_note": "V404 benchmark is a broad/transient feature; only the W2 in-band fraction is shown here and it is not a CAM511 Fig.11-like narrow-line source.",
        },
    ]
    return rows


def line_safe(value: float) -> float:
    return value if math.isfinite(value) else math.inf


def plot_c(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 6.0))
    fig.patch.set_facecolor(TOKENS["surface"])
    signal_rows = [row for row in rows if math.isfinite(fnum(row.get("source_counts_1Ms_at_reference_signal")))]
    sensitivity_rows = [row for row in rows if math.isfinite(fnum(row.get("F3_1Ms_ph_cm2_s")))]
    color_by_label = {
        "511-CAM Fig.11 approx": "#1F2430",
        "SPI manual": "#7A828F",
        "COSI 511 line": "#8A5FBF",
        "Laue W2 spot_r90": "#71B436",
        "Laue W2 diffuse": "#5477C4",
        "V404 kT170 W2": "#CC6F47",
    }

    ax = axes[0]
    setup_axes(ax)
    labels = [row["label"] for row in signal_rows]
    values = np.asarray([fnum(row["source_counts_1Ms_at_reference_signal"]) for row in signal_rows], dtype=float)
    ypos = np.arange(len(signal_rows))
    colors = [color_by_label.get(row["label"], "#7A828F") for row in signal_rows]
    ax.barh(ypos, values, color=colors, alpha=0.92)
    ax.set_xscale("log")
    ax.set_yticks(ypos, labels)
    ax.invert_yaxis()
    ax.set_xlabel("source counts in 1 Ms at each reference signal")
    ax.set_title("Signal normalization is not common", fontsize=12, color=TOKENS["ink"], pad=8)
    ax.set_xlim(max(min(values) / 3.0, 1.0), max(values) * 4.0)
    for y, value in zip(ypos, values):
        ax.annotate(f"{value:.3g}", (value, y), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8, color=TOKENS["ink"])

    ax = axes[1]
    setup_axes(ax)
    labels = [row["label"] for row in sensitivity_rows]
    values = np.asarray([fnum(row["F3_1Ms_ph_cm2_s"]) for row in sensitivity_rows], dtype=float)
    ypos = np.arange(len(sensitivity_rows))
    colors = [color_by_label.get(row["label"], "#7A828F") for row in sensitivity_rows]
    ax.barh(ypos, values, color=colors, alpha=0.92)
    ax.set_xscale("log")
    ax.set_yticks(ypos, labels)
    ax.invert_yaxis()
    ax.set_xlabel(r"3$\sigma$ line sensitivity in 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Literature sensitivity context only", fontsize=12, color=TOKENS["ink"], pad=8)
    ax.set_xlim(min(values) / 2.4, max(values) * 3.0)
    for y, value in zip(ypos, values):
        ax.annotate(f"{value:.2g}", (value, y), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8, color=TOKENS["ink"])

    fig.suptitle("CAM511 Fig.11 and current Laue use different signal normalizations", fontsize=12, color=TOKENS["ink"])
    fig.text(
        0.02,
        0.025,
        "CAM511 Fig.11 uses 0.1 ph/s (sky-equivalent 1.97e-3 ph cm-2 s-1 for 50.89 cm2 optics). "
        "Current Laue mono-511 uses 1e-4 ph cm-2 s-1.\n"
        "COSI is sqrt-time scaled from a 2-year survey 511-keV narrow-line requirement to a 1Ms-equivalent marker. "
        "The V404 point is a broad-feature W2 in-band count proxy. "
        "Do not read the right panel as a detector-only ranking.",
        ha="left",
        va="bottom",
        fontsize=8,
        color=TOKENS["muted"],
    )
    fig.tight_layout(rect=(0, 0.16, 1, 0.93))
    out = OUT / f"c_laue_only{PNG_TAG}.png"
    fig.savefig(out, dpi=220)
    if PNG_TAG:
        fig.savefig(OUT / "c_laue_only.png", dpi=220)
    plt.close(fig)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    curves = {"W1": load_w1_curve(), "W2": load_w2_curve()}
    fractions = load_model_fractions()

    scan_rows = build_scan_rows(curves, fractions)
    scaled_rows = build_scaled_rows(curves, fractions)
    c_rows = build_c_rows()

    write_csv(OUT / "b_w1_w2.csv", scaled_rows)
    write_csv(OUT / "c_laue_only.csv", c_rows)

    only_bc = "--only-bc" in sys.argv
    paths = []
    if not only_bc:
        write_csv(OUT / "a_w1_w2.csv", scan_rows)
        paths.append(plot_a(scan_rows))
    paths.extend([plot_b(scaled_rows), plot_c(c_rows)])
    for path in paths:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
