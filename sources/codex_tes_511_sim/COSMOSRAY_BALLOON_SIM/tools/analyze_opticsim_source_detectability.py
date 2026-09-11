#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build source detectability tables for the current opticsim Laue mainline."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAY = ROOT / "reports_260516/opticsim_laue_cam511_f12m_nonoverlap_replay_20260521/summary.json"
DEFAULT_CONFIG_SUMMARY = ROOT / "configs/opticsim/laue_ge111_480_550keV_cam511_f12m_nonoverlap_5ring_summary.json"
DEFAULT_DIFFUSE = ROOT / "reports2.0/09_SOURCE_CASES_ABC/diffuse_aperture_foreground.csv"
DEFAULT_TRANS = ROOT / "reports/phase2_real_flight_physical_production/environment_grid_real/science_atmospheric_transmission.csv"
DEFAULT_BACKGROUND = ROOT / "reports_260516/source_time_update/background_time_variation.csv"
DEFAULT_OUT = ROOT / "reports_260516/opticsim_cam511_f12m_source_detectability_20260521"

SECONDS_PER_DAY = 86400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
REFERENCE_EXPOSURE_S = 1.0e6
REFERENCE_T_ATM_511 = 0.7390423888027
SPI_BULGE_FLUX = 0.96e-3
SPI_DISK_FLUX = 1.66e-3
POINT_FLUX_SCAN = [1e-5, 3e-5, 5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4, 5e-4, 1e-3, 3e-3]
WINDOWS = ["broad_480_550", "line_510p3_511p8"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--config-summary", type=Path, default=DEFAULT_CONFIG_SUMMARY)
    parser.add_argument("--diffuse", type=Path, default=DEFAULT_DIFFUSE)
    parser.add_argument("--transmission", type=Path, default=DEFAULT_TRANS)
    parser.add_argument("--background", type=Path, default=DEFAULT_BACKGROUND)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--label",
        default="current CAM511-inspired 12 m non-overlapping Ge(111) Laue detector replay",
        help="Human-readable optics label for README and summary caveats.",
    )
    return parser.parse_args()


def f(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def t3_seconds(signal_cps: float, background_cps: float, sigma: float = 3.0) -> float:
    if signal_cps <= 0.0 or background_cps <= 0.0:
        return float("inf")
    return (sigma * math.sqrt(background_cps) / signal_cps) ** 2


def f3_1ms(response_cps_per_flux: float, background_cps: float) -> float:
    if response_cps_per_flux <= 0.0 or background_cps <= 0.0:
        return float("inf")
    return 3.0 * math.sqrt(background_cps) / (response_cps_per_flux * math.sqrt(REFERENCE_EXPOSURE_S))


def normal_survival(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def p_ge_3sigma(flux: float, f3: float) -> float:
    if flux <= 0.0 or f3 <= 0.0 or not math.isfinite(f3):
        return float("nan")
    mean_sigma = 3.0 * flux / f3
    return normal_survival(3.0 - mean_sigma)


def crossing_time(days: list[float], z_values: list[float], threshold: float = 3.0) -> float | None:
    for i, z in enumerate(z_values):
        if z < threshold:
            continue
        if i == 0:
            return days[0]
        x0, x1 = days[i - 1], days[i]
        y0, y1 = z_values[i - 1], z
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def background_by_window(path: Path) -> dict[str, list[dict[str, float]]]:
    rows_by_window: dict[str, list[dict[str, float]]] = {w: [] for w in WINDOWS}
    for row in read_csv(path):
        window = row["window"]
        if window not in rows_by_window:
            continue
        rows_by_window[window].append(
            {
                "time_bin_id": int(float(row["time_bin_id"])),
                "day_mid": f(row, "day_mid"),
                "background_cps": f(row, "total_background_final_cps_level1"),
            }
        )
    for rows in rows_by_window.values():
        rows.sort(key=lambda r: r["time_bin_id"])
    return rows_by_window


def transmission_by_bin(path: Path) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    for row in read_csv(path):
        tid = int(float(row["time_bin_id"]))
        out[tid] = {
            "time_mid_s": f(row, "time_mid_s"),
            "day_mid": f(row, "day_mid"),
            "T_atm_511": f(row, "T_atm_511") * f(row, "earth_occultation_factor", 1.0),
            "source_zenith_deg": f(row, "source_zenith_deg"),
            "altitude_km": f(row, "altitude_km"),
        }
    return out


def integrate_time_dependent(
    *,
    top_flux_ph_cm2_s: float,
    response_no_atm: float,
    background_rows: list[dict[str, float]],
    trans: dict[int, dict[str, float]],
) -> dict[str, float | str]:
    previous_time: float | None = None
    cum_signal = 0.0
    cum_background = 0.0
    days: list[float] = []
    z_values: list[float] = []
    weighted_t_sum = 0.0
    live_s = 0.0
    for row in background_rows:
        tid = int(row["time_bin_id"])
        tr = trans.get(tid, {})
        time_s = float(tr.get("time_mid_s", row["day_mid"] * SECONDS_PER_DAY))
        dt_s = 0.0 if previous_time is None else max(time_s - previous_time, 0.0)
        previous_time = time_s
        t_atm = float(tr.get("T_atm_511", 1.0))
        signal_cps = top_flux_ph_cm2_s * response_no_atm * t_atm
        background_cps = max(float(row["background_cps"]), 1.0e-300)
        cum_signal += signal_cps * dt_s
        cum_background += background_cps * dt_s
        if dt_s > 0:
            weighted_t_sum += t_atm * dt_s
            live_s += dt_s
        day = float(row["day_mid"])
        days.append(day)
        z_values.append(cum_signal / math.sqrt(cum_background) if cum_background > 0.0 else 0.0)

    final_day = days[-1] if days else 0.0
    final_z = z_values[-1] if z_values else 0.0
    cross = crossing_time(days, z_values)
    return {
        "td_elapsed_days": final_day,
        "td_live_s": live_s,
        "td_time_weighted_T_atm": weighted_t_sum / live_s if live_s > 0 else float("nan"),
        "td_cumulative_signal_counts": cum_signal,
        "td_cumulative_background_counts": cum_background,
        "td_final_Z_counting": final_z,
        "td_T3_days_crossing": "" if cross is None else cross,
        "td_T3_days_avg_extrapolated": "" if final_z <= 0.0 else final_day * (3.0 / final_z) ** 2,
    }


def response_table(replay: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for window in WINDOWS:
        win = replay["windows"][window]
        out[window] = {
            "response_no_atm_cps_per_ph_cm2_s": float(win["geometric_area_response_cm2"]),
            "detector_final_survival_per_diffracted": float(win["detector_final_survival_per_diffracted"]),
            "end_to_end_final_survival_per_laue_primary": float(win["end_to_end_final_survival_per_laue_primary"]),
        }
    return out


def build_point_rows(
    responses: dict[str, dict[str, float]],
    bg: dict[str, list[dict[str, float]]],
    trans: dict[int, dict[str, float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        response_no_atm = responses[window]["response_no_atm_cps_per_ph_cm2_s"]
        background_day15 = bg[window][60]["background_cps"] if len(bg[window]) > 60 else bg[window][-1]["background_cps"]
        response_ref_atm = response_no_atm * REFERENCE_T_ATM_511
        f3_no_atm = f3_1ms(response_no_atm, background_day15)
        f3_ref_atm = f3_1ms(response_ref_atm, background_day15)
        for flux in POINT_FLUX_SCAN:
            signal_no_atm = flux * response_no_atm
            signal_ref_atm = flux * response_ref_atm
            t3_no = t3_seconds(signal_no_atm, background_day15)
            t3_ref = t3_seconds(signal_ref_atm, background_day15)
            td = integrate_time_dependent(
                top_flux_ph_cm2_s=flux,
                response_no_atm=response_no_atm,
                background_rows=bg[window],
                trans=trans,
            )
            row = {
                "source_case": "generic_point_source_flux_scan",
                "window": window,
                "literature_anchor": "SPI_GCS_POINTLIKE_511 when flux=8e-5; otherwise scan value",
                "flux_top_of_atmosphere_ph_cm2_s": flux,
                "response_no_atm_cps_per_ph_cm2_s": response_no_atm,
                "reference_T_atm_511": REFERENCE_T_ATM_511,
                "response_ref_atm_cps_per_ph_cm2_s": response_ref_atm,
                "background_day15_cps": background_day15,
                "signal_cps_no_atm": signal_no_atm,
                "signal_cps_ref_atm": signal_ref_atm,
                "F3_1Ms_no_atm_ph_cm2_s": f3_no_atm,
                "F3_1Ms_ref_atm_ph_cm2_s": f3_ref_atm,
                "P_ge_3sigma_1Ms_no_atm": p_ge_3sigma(flux, f3_no_atm),
                "P_ge_3sigma_1Ms_ref_atm": p_ge_3sigma(flux, f3_ref_atm),
                "T3_days_no_atm": t3_no / SECONDS_PER_DAY,
                "T3_days_ref_atm": t3_ref / SECONDS_PER_DAY,
                "claim_level": "current_Laue_detector_replay_counting_scan_not_profile_likelihood",
            }
            row.update(td)
            rows.append(row)
    return rows


def fov_solid_angle(fov_radius_deg: float) -> tuple[float, float]:
    theta = math.radians(fov_radius_deg)
    omega = 2.0 * math.pi * (1.0 - math.cos(theta))
    area_deg2 = math.pi * fov_radius_deg * fov_radius_deg
    return omega, area_deg2


def build_diffuse_rows(
    diffuse_path: Path,
    responses: dict[str, dict[str, float]],
    bg: dict[str, list[dict[str, float]]],
    trans: dict[int, dict[str, float]],
) -> list[dict[str, Any]]:
    base_rows = read_csv(diffuse_path)
    model_rows = list(base_rows)
    bulge8 = [r for r in base_rows if r["sky_model"] == "bulge_gaussian_fwhm_8deg"][0]
    disk = [r for r in base_rows if r["sky_model"] == "disk_thick_gaussian"][0]
    default_fov_flux = f(bulge8, "fov_flux_ph_cm2_s") + f(disk, "fov_flux_ph_cm2_s")
    default_total_flux = SPI_BULGE_FLUX + SPI_DISK_FLUX
    model_rows.append(
        {
            "sky_model": "B_default_bulge8deg_plus_disk",
            "kind": "composite_aperture_sum",
            "total_flux_ph_cm2_s": str(default_total_flux),
            "fwhm_l_deg": "",
            "fwhm_b_deg": "",
            "central_intensity_ph_cm2_s_deg2": "",
            "fov_radius_deg": bulge8["fov_radius_deg"],
            "fov_flux_ph_cm2_s": str(default_fov_flux),
            "fov_fraction": str(default_fov_flux / default_total_flux),
            "sky_model_file": f"{bulge8['sky_model_file']} + {disk['sky_model_file']}",
        }
    )

    out: list[dict[str, Any]] = []
    for source in model_rows:
        fov_flux = f(source, "fov_flux_ph_cm2_s")
        total_flux = f(source, "total_flux_ph_cm2_s")
        fov_radius = f(source, "fov_radius_deg")
        omega_sr, omega_deg2 = fov_solid_angle(fov_radius)
        for window in WINDOWS:
            response_no_atm = responses[window]["response_no_atm_cps_per_ph_cm2_s"]
            background_day15 = bg[window][60]["background_cps"] if len(bg[window]) > 60 else bg[window][-1]["background_cps"]
            response_ref_atm = response_no_atm * REFERENCE_T_ATM_511
            signal_no_atm = fov_flux * response_no_atm
            signal_ref_atm = fov_flux * response_ref_atm
            t3_no = t3_seconds(signal_no_atm, background_day15)
            t3_ref = t3_seconds(signal_ref_atm, background_day15)
            td = integrate_time_dependent(
                top_flux_ph_cm2_s=fov_flux,
                response_no_atm=response_no_atm,
                background_rows=bg[window],
                trans=trans,
            )
            row = {
                "source_case": source["sky_model"],
                "window": window,
                "total_flux_top_of_atmosphere_ph_cm2_s": total_flux,
                "fov_radius_deg": fov_radius,
                "fov_radius_arcmin": fov_radius * 60.0,
                "fov_solid_angle_sr": omega_sr,
                "fov_area_deg2_small_angle": omega_deg2,
                "fov_flux_top_of_atmosphere_ph_cm2_s": fov_flux,
                "fov_fraction": f(source, "fov_fraction"),
                "reference_T_atm_511": REFERENCE_T_ATM_511,
                "fov_flux_ref_atm_ph_cm2_s": fov_flux * REFERENCE_T_ATM_511,
                "response_no_atm_cps_per_ph_cm2_s": response_no_atm,
                "background_day15_cps": background_day15,
                "signal_cps_no_atm": signal_no_atm,
                "signal_cps_ref_atm": signal_ref_atm,
                "T3_days_no_atm": t3_no / SECONDS_PER_DAY,
                "T3_years_no_atm": t3_no / SECONDS_PER_YEAR,
                "T3_days_ref_atm": t3_ref / SECONDS_PER_DAY,
                "T3_years_ref_atm": t3_ref / SECONDS_PER_YEAR,
                "claim_level": "diffuse_FoV_aperture_upper_bound_using_onaxis_Laue_response_not_full_offaxis_map",
            }
            row.update(td)
            out.append(row)

    # Explicit invalid comparison to make the point-source/diffuse distinction auditable.
    for window in WINDOWS:
        response_no_atm = responses[window]["response_no_atm_cps_per_ph_cm2_s"]
        background_day15 = bg[window][60]["background_cps"] if len(bg[window]) > 60 else bg[window][-1]["background_cps"]
        signal_wrong = default_total_flux * response_no_atm * REFERENCE_T_ATM_511
        t3_wrong = t3_seconds(signal_wrong, background_day15)
        out.append(
            {
                "source_case": "INVALID_total_bulge8deg_plus_disk_treated_as_point_source",
                "window": window,
                "total_flux_top_of_atmosphere_ph_cm2_s": default_total_flux,
                "fov_radius_deg": "",
                "fov_radius_arcmin": "",
                "fov_solid_angle_sr": "",
                "fov_area_deg2_small_angle": "",
                "fov_flux_top_of_atmosphere_ph_cm2_s": default_total_flux,
                "fov_fraction": 1.0,
                "reference_T_atm_511": REFERENCE_T_ATM_511,
                "fov_flux_ref_atm_ph_cm2_s": default_total_flux * REFERENCE_T_ATM_511,
                "response_no_atm_cps_per_ph_cm2_s": response_no_atm,
                "background_day15_cps": background_day15,
                "signal_cps_ref_atm": signal_wrong,
                "T3_days_ref_atm": t3_wrong / SECONDS_PER_DAY,
                "T3_years_ref_atm": t3_wrong / SECONDS_PER_YEAR,
                "claim_level": "INVALID_COMPARISON_FORBIDDEN_total_diffuse_flux_collapsed_to_onaxis_point",
            }
        )
    return out


def config_area_summary(config_summary: dict[str, Any]) -> tuple[float, float]:
    if "estimated_optics_effective_area_cm2" in config_summary:
        return (
            float(config_summary["estimated_optics_effective_area_cm2"]),
            float(config_summary["geometric_crystal_area_cm2"]),
        )
    selected = config_summary.get("selected", {})
    if "estimated_optics_effective_area_cm2" in selected:
        return (
            float(selected["estimated_optics_effective_area_cm2"]),
            float(selected["geometric_crystal_area_cm2"]),
        )
    raise KeyError("config summary missing estimated/geometric Laue area fields")


def literature_audit_rows(config_summary: dict[str, Any]) -> list[dict[str, Any]]:
    fov_radius_deg = 0.0745
    omega_sr, area_deg2 = fov_solid_angle(fov_radius_deg)
    optics_aeff, geometric_area = config_area_summary(config_summary)
    return [
        {
            "item": "SPI total Galactic 511-keV line flux",
            "value": "2.74e-3 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "context only; not a point-source input",
            "status": "OK",
        },
        {
            "item": "SPI central point-like model component",
            "value": "8.0e-5 +/- 1.9e-5 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "point-source flux-scan anchor; identity not confirmed",
            "status": "OK_WITH_CAVEAT",
        },
        {
            "item": "SPI bulge and disk diffuse flux",
            "value": "bulge 0.96e-3; disk 1.66e-3 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "diffuse FoV aperture integral, not on-axis point source",
            "status": "OK",
        },
        {
            "item": "FoV solid angle",
            "value": f"radius 0.0745 deg = 4.47 arcmin; Omega {omega_sr:.6e} sr; area {area_deg2:.6e} deg2",
            "reference": "CAM511 FoV radius carried in local CAM511-derived source model",
            "usage": "diffuse aperture fraction",
            "status": "OK_SMALL_FOV",
        },
        {
            "item": "Atmospheric transmission",
            "value": f"reference T_atm={REFERENCE_T_ATM_511}; time grid min/max are reported in summary",
            "reference": "reports/phase2_real_flight_physical_production/environment_grid_real/science_atmospheric_transmission.csv",
            "usage": "multiply top-of-atmosphere literature flux before detector response",
            "status": "OK",
        },
        {
            "item": "Current Laue effective area",
            "value": f"{optics_aeff:.6g} cm2 estimated optics Aeff; geometric crystal area {geometric_area:.6g} cm2",
            "reference": "user-selected opticsim Laue config summary",
            "usage": "current scaffold normalization; not CAM511 50.89 cm2 channel optics",
            "status": "LIMITED_SCAFFOLD",
        },
    ]


def plot_point(rows: list[dict[str, Any]], outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.3, 4.8))
    for window, color in [("broad_480_550", "#4C78A8"), ("line_510p3_511p8", "#F58518")]:
        use = [r for r in rows if r["window"] == window]
        x = [float(r["flux_top_of_atmosphere_ph_cm2_s"]) for r in use]
        y = [float(r["T3_days_ref_atm"]) for r in use]
        ax.plot(x, y, marker="o", ms=3.5, lw=1.4, color=color, label=f"{window}, T_atm ref")
    ax.axvline(8.0e-5, color="#54A24B", ls="--", lw=1.2, label="SPI central compact anchor")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("top-of-atmosphere point-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("3-sigma exposure (days)")
    ax.set_title("Current Laue point-source flux scan")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "point_source_flux_scan_current_laue.png", dpi=200)
    plt.close(fig)


def plot_diffuse(rows: list[dict[str, Any]], outdir: Path) -> None:
    use = [
        r for r in rows
        if r["window"] == "broad_480_550" and not str(r["source_case"]).startswith("INVALID")
    ]
    labels = [str(r["source_case"]).replace("bulge_gaussian_", "bulge_").replace("_", "\n") for r in use]
    years = [float(r["T3_years_ref_atm"]) for r in use]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.bar(labels, years, color="#4C78A8")
    ax.set_yscale("log")
    ax.set_ylabel("3-sigma exposure with reference atmosphere (years)")
    ax.set_title("Diffuse 511-keV flux intercepted by the 4.47 arcmin FoV")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "diffuse_fov_detectability_current_laue.png", dpi=200)
    plt.close(fig)


def write_readme(
    outdir: Path,
    point_rows: list[dict[str, Any]],
    diffuse_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    responses: dict[str, dict[str, float]],
    trans: dict[int, dict[str, float]],
    label: str,
    config_summary: dict[str, Any],
) -> None:
    def find_point(window: str, flux: float) -> dict[str, Any]:
        for row in point_rows:
            if row["window"] == window and abs(float(row["flux_top_of_atmosphere_ph_cm2_s"]) - flux) < flux * 1.0e-9:
                return row
        raise KeyError((window, flux))

    def find_diff(case: str, window: str = "broad_480_550") -> dict[str, Any]:
        for row in diffuse_rows:
            if row["source_case"] == case and row["window"] == window:
                return row
        raise KeyError((case, window))

    t_values = [float(v["T_atm_511"]) for v in trans.values()]
    anchor = find_point("broad_480_550", 8.0e-5)
    p1e4 = find_point("broad_480_550", 1.0e-4)
    p1e3 = find_point("broad_480_550", 1.0e-3)
    line_anchor = find_point("line_510p3_511p8", 8.0e-5)
    line_p1e4 = find_point("line_510p3_511p8", 1.0e-4)
    default_diff = find_diff("B_default_bulge8deg_plus_disk")
    wrong = find_diff("INVALID_total_bulge8deg_plus_disk_treated_as_point_source")
    optics_aeff, _geometric_area = config_area_summary(config_summary)
    lines = [
        "# Current Opticsim Laue Source Detectability",
        "",
        "Status: `PASS_WITH_EXPLICIT_CAVEATS`",
        "",
        f"This report recalculates point-source and diffuse-source detectability using `{label}`. Literature fluxes are treated as top-of-atmosphere astrophysical fluxes and are multiplied by atmospheric transmission before detector-response counting.",
        "",
        "## Source And Geometry Audit",
        "",
        "| item | value | usage | status |",
        "|---|---|---|---|",
    ]
    for row in audit_rows:
        lines.append(f"| {row['item']} | {row['value']} | {row['usage']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Atmospheric Transmission",
            "",
            f"- Reference `T_atm_511`: `{REFERENCE_T_ATM_511:.6g}`.",
            f"- Time grid `T_atm_511` range: `{min(t_values):.6g}` to `{max(t_values):.6g}`.",
            "- The time-dependent table uses the actual `T_atm_511 * earth_occultation_factor` in each trajectory bin.",
            "",
            "## Current Point-Source Scan",
            "",
            "| case | window | flux top-of-atm | T3 no atmosphere | T3 reference atmosphere | T3 time-dependent avg extrapolated |",
            "|---|---|---:|---:|---:|---:|",
            f"| SPI central compact anchor | 480-550 | 8e-5 | {float(anchor['T3_days_no_atm']):.4g} d | {float(anchor['T3_days_ref_atm']):.4g} d | {float(anchor['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| generic point | 480-550 | 1e-4 | {float(p1e4['T3_days_no_atm']):.4g} d | {float(p1e4['T3_days_ref_atm']):.4g} d | {float(p1e4['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| generic point | 480-550 | 1e-3 | {float(p1e3['T3_days_no_atm']):.4g} d | {float(p1e3['T3_days_ref_atm']):.4g} d | {float(p1e3['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| SPI central compact anchor | 510.3-511.8 | 8e-5 | {float(line_anchor['T3_days_no_atm']):.4g} d | {float(line_anchor['T3_days_ref_atm']):.4g} d | {float(line_anchor['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| generic point | 510.3-511.8 | 1e-4 | {float(line_p1e4['T3_days_no_atm']):.4g} d | {float(line_p1e4['T3_days_ref_atm']):.4g} d | {float(line_p1e4['td_T3_days_avg_extrapolated']):.4g} d |",
            "",
            "These are conservative full-window counting numbers. They still do not include a profiled PSF/energy/radius/layer likelihood for the new Laue focal distribution.",
            "",
            "## Diffuse Source",
            "",
            "| case | window | total flux | FoV flux | FoV fraction | T3 reference atmosphere |",
            "|---|---|---:|---:|---:|---:|",
            f"| default SPI bulge8+disk | 480-550 | {float(default_diff['total_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(default_diff['fov_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(default_diff['fov_fraction']):.4g} | {float(default_diff['T3_years_ref_atm']):.4g} yr |",
            f"| invalid total-flux-as-point comparison | 480-550 | {float(wrong['total_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(wrong['fov_flux_top_of_atmosphere_ph_cm2_s']):.4g} | 1 | {float(wrong['T3_days_ref_atm']):.4g} d |",
            "",
            "The invalid row is intentionally included only as a warning: it collapses a many-degree diffuse sky distribution into an on-axis point source and must not be used as the diffuse detectability claim.",
            "",
            "## Why SPI Can See It But This Pointed Balloon Mode May Not",
            "",
            f"SPI observes the Galactic 511-keV emission with a wide coded-mask field and long space exposure, fitting extended sky templates. A narrow pointed focusing telescope only receives the small part of the diffuse brightness inside its FoV at any instant. For point sources, the selected Laue scaffold has about `{optics_aeff:.4g} cm2` estimated optics effective area and the calculation above is still full-window counting against balloon prompt+activation background.",
            "",
            "## Files",
            "",
            "- `point_source_flux_scan_current_laue.csv`",
            "- `diffuse_source_detectability_current_laue.csv`",
            "- `source_geometry_atmosphere_audit.csv`",
            "- `point_source_flux_scan_current_laue.png`",
            "- `diffuse_fov_detectability_current_laue.png`",
        ]
    )
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    replay = load_json(args.replay)
    config_summary = load_json(args.config_summary)
    responses = response_table(replay)
    bg = background_by_window(args.background)
    trans = transmission_by_bin(args.transmission)
    point_rows = build_point_rows(responses, bg, trans)
    diffuse_rows = build_diffuse_rows(args.diffuse, responses, bg, trans)
    audit_rows = literature_audit_rows(config_summary)

    write_csv(outdir / "point_source_flux_scan_current_laue.csv", point_rows)
    write_csv(outdir / "diffuse_source_detectability_current_laue.csv", diffuse_rows)
    write_csv(outdir / "source_geometry_atmosphere_audit.csv", audit_rows)
    plot_point(point_rows, outdir)
    plot_diffuse(diffuse_rows, outdir)

    t_values = [float(v["T_atm_511"]) for v in trans.values()]
    summary = {
        "status": "PASS_WITH_EXPLICIT_CAVEATS",
        "claim_level": "CURRENT_OPTICSIM_LAUE_SOURCE_DETECTABILITY_COUNTING_NOT_PROFILED_FINAL",
        "optics_label": args.label,
        "inputs": {
            "replay_summary": str(args.replay),
            "config_summary": str(args.config_summary),
            "diffuse_aperture": str(args.diffuse),
            "atmospheric_transmission": str(args.transmission),
            "background_time_variation": str(args.background),
        },
        "responses": responses,
        "reference_T_atm_511": REFERENCE_T_ATM_511,
        "time_grid_T_atm_min": min(t_values),
        "time_grid_T_atm_max": max(t_values),
        "point_rows": len(point_rows),
        "diffuse_rows": len(diffuse_rows),
        "key_results": {
            "point_broad_8e_minus_5_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "broad_480_550" and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 8.0e-5) < 1e-12
            ),
            "point_broad_1e_minus_4_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "broad_480_550" and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 1.0e-4) < 1e-12
            ),
            "point_line_8e_minus_5_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "line_510p3_511p8" and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 8.0e-5) < 1e-12
            ),
            "point_line_1e_minus_4_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "line_510p3_511p8" and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 1.0e-4) < 1e-12
            ),
            "diffuse_default_broad_ref_atm_T3_years": next(
                float(r["T3_years_ref_atm"])
                for r in diffuse_rows
                if r["source_case"] == "B_default_bulge8deg_plus_disk" and r["window"] == "broad_480_550"
            ),
            "diffuse_default_line_ref_atm_T3_years": next(
                float(r["T3_years_ref_atm"])
                for r in diffuse_rows
                if r["source_case"] == "B_default_bulge8deg_plus_disk" and r["window"] == "line_510p3_511p8"
            ),
        },
        "caveats": [
            "Literature fluxes are top-of-atmosphere/source fluxes; reference and time-dependent atmospheric attenuation are applied explicitly.",
            "Diffuse rows use the existing 4.47 arcmin FoV aperture integral and on-axis Laue response as an upper-bound scaffold, not a full off-axis diffuse focal map.",
            "Point rows are full-window counting numbers for the new Laue replay, not optimized profile-likelihood sensitivity.",
            "The invalid total-diffuse-as-point row is included only to demonstrate why total SPI diffuse flux cannot be compared to a focused point-source flux.",
        ],
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(outdir, point_rows, diffuse_rows, audit_rows, responses, trans, args.label, config_summary)
    print(json.dumps({"status": summary["status"], "summary": str(outdir / "summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
