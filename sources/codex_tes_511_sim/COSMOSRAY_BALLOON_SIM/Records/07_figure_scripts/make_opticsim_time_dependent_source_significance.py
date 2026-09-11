#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build current-optics time-dependent 3-sigma source-significance records."""

from __future__ import annotations

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


ROOT = Path(__file__).resolve().parents[2]
SECONDS_PER_DAY = 86400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
REFERENCE_T_ATM_511 = 0.7390423888027
SPI_BULGE_FLUX = 0.96e-3
SPI_DISK_FLUX = 1.66e-3
WINDOWS = ["broad_480_550", "line_510p3_511p8"]
WINDOW_LABELS = {
    "broad_480_550": "480-550 keV",
    "line_510p3_511p8": "510.3-511.8 keV",
}
WINDOW_COLORS = {
    "broad_480_550": "#4C78A8",
    "line_510p3_511p8": "#F58518",
}
POINT_FLUX_SCAN = [
    1e-5,
    2e-5,
    3e-5,
    5e-5,
    8e-5,
    1e-4,
    1.5e-4,
    2e-4,
    3e-4,
    5e-4,
    8e-4,
    1e-3,
    2e-3,
    3e-3,
]
V404_REFERENCE_ANCHOR = {
    "anchor_id": "Siegert2016_V404_orbit1555_thermal_pair_annihilation",
    "flux_ph_cm2_s": 6.5e-3,
    "uncertainty_ph_cm2_s": 1.6e-3,
    "spectrum": "v404_kT170_no_shift",
    "reference": "Siegert et al. 2016 Nature 531, 341-343; arXiv:1603.01169, Extended Data Table 1",
}
V404_REFERENCE_SCALE_FACTORS = [0.2, 0.5, 1.0, 2.0, 5.0]
V404_REFERENCE_SCALED_FLUXES = [V404_REFERENCE_ANCHOR["flux_ph_cm2_s"] * x for x in V404_REFERENCE_SCALE_FACTORS]
V404_FLUX_SCAN = sorted(set(POINT_FLUX_SCAN + [5e-3, 6.5e-3, 1e-2] + V404_REFERENCE_SCALED_FLUXES))

BACKGROUND = ROOT / "reports_260516/source_time_update/background_time_variation.csv"
TRANSMISSION = ROOT / "reports/phase2_real_flight_physical_production/environment_grid_real/science_atmospheric_transmission.csv"
DIFFUSE = ROOT / "reports2.0/09_SOURCE_CASES_ABC/diffuse_aperture_foreground.csv"
V404_BANDPASS = ROOT / "reports2.0/09_SOURCE_CASES_ABC/v404_bandpass_loss.csv"

ROUTES = [
    {
        "route_id": "laue_f17p5",
        "route_label": "current f17.5 m Ge(111/220/311) Laue scaffold",
        "replay_summary": ROOT / "reports_260516/opticsim_laue_511_mono_ge_hkl_f17p5_replay_20260521/summary.json",
        "outdir": ROOT / "Records/05_laue_current_mainline/source_significance_time_dependent_20260522",
    },
    {
        "route_id": "channel_wallbywall",
        "route_label": "current wall-by-wall public-geometry channel-optics route",
        "replay_summary": ROOT / "reports_260516/opticsim_channel_wallbywall_511_replay_20260521/summary.json",
        "outdir": ROOT / "Records/06_channel_current_mainline/source_significance_time_dependent_20260522",
    },
]


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row: dict[str, str] | dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(value: Any, digits: int = 4) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(val):
        return "nan"
    return f"{val:.{digits}g}"


def same_float(a: float, b: float) -> bool:
    return abs(a - b) < max(1.0e-15, abs(b) * 1.0e-9)


def v404_reference_scale_factor(flux: float) -> float | str:
    for factor, scaled_flux in zip(V404_REFERENCE_SCALE_FACTORS, V404_REFERENCE_SCALED_FLUXES):
        if same_float(flux, scaled_flux):
            return factor
    return ""


def t3_seconds(signal_cps: float, background_cps: float, sigma: float = 3.0) -> float:
    if signal_cps <= 0.0 or background_cps <= 0.0:
        return float("inf")
    return (sigma * math.sqrt(background_cps) / signal_cps) ** 2


def crossing_time(days: list[float], z_values: list[float], threshold: float = 3.0) -> float | None:
    for idx, z_val in enumerate(z_values):
        if z_val < threshold:
            continue
        if idx == 0:
            return days[0]
        x0, x1 = days[idx - 1], days[idx]
        y0, y1 = z_values[idx - 1], z_val
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def background_by_window(path: Path) -> dict[str, list[dict[str, float]]]:
    rows_by_window: dict[str, list[dict[str, float]]] = {window: [] for window in WINDOWS}
    for row in read_csv(path):
        window = row.get("window", "")
        if window not in rows_by_window:
            continue
        rows_by_window[window].append(
            {
                "time_bin_id": int(f(row, "time_bin_id")),
                "day_mid": f(row, "day_mid"),
                "altitude_km": f(row, "altitude_km"),
                "prompt_final_cps": f(row, "prompt_final_cps"),
                "delayed_final_cps_level1": f(row, "delayed_final_cps_level1"),
                "background_cps": f(row, "total_background_final_cps_level1"),
                "activation_driver": f(row, "activation_driver"),
                "total_delayed_activity_Bq": f(row, "total_delayed_activity_Bq"),
            }
        )
    for rows in rows_by_window.values():
        rows.sort(key=lambda item: item["time_bin_id"])
    return rows_by_window


def transmission_by_bin(path: Path) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    for row in read_csv(path):
        tid = int(f(row, "time_bin_id"))
        out[tid] = {
            "time_mid_s": f(row, "time_mid_s"),
            "day_mid": f(row, "day_mid"),
            "altitude_km": f(row, "altitude_km"),
            "source_zenith_deg": f(row, "source_zenith_deg"),
            "vertical_depth_g_cm2": f(row, "vertical_depth_g_cm2"),
            "path_depth_g_cm2": f(row, "path_depth_g_cm2"),
            "T_atm_511": f(row, "T_atm_511") * f(row, "earth_occultation_factor", 1.0),
            "earth_occultation_factor": f(row, "earth_occultation_factor", 1.0),
        }
    return out


def day15_background(rows: list[dict[str, float]]) -> float:
    if not rows:
        return float("nan")
    return min(rows, key=lambda row: abs(row["day_mid"] - 15.0))["background_cps"]


def response_table(replay: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for window in WINDOWS:
        win = replay["windows"][window]
        out[window] = {
            "response_no_atm_cps_per_ph_cm2_s": float(win["geometric_area_response_cm2"]),
            "detector_final_survival": float(win["detector_final_survival_per_diffracted"]),
            "end_to_end_final_survival": float(win["end_to_end_final_survival_per_laue_primary"]),
        }
    return out


def fov_solid_angle(fov_radius_deg: float) -> tuple[float, float]:
    theta = math.radians(fov_radius_deg)
    omega = 2.0 * math.pi * (1.0 - math.cos(theta))
    area_deg2 = math.pi * fov_radius_deg * fov_radius_deg
    return omega, area_deg2


def integrate_time_dependent(
    *,
    flux_top_atm: float,
    source_factor: float,
    response_no_atm: float,
    background_rows: list[dict[str, float]],
    trans: dict[int, dict[str, float]],
    scenario_id: str,
    source_family: str,
    window: str,
    spectrum: str = "",
    keep_profile: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    previous_time_s: float | None = None
    cum_signal = 0.0
    cum_background = 0.0
    weighted_t_sum = 0.0
    live_s = 0.0
    days: list[float] = []
    z_values: list[float] = []
    profile: list[dict[str, Any]] = []

    for row in background_rows:
        tid = int(row["time_bin_id"])
        tr = trans.get(tid, {})
        time_s = float(tr.get("time_mid_s", row["day_mid"] * SECONDS_PER_DAY))
        dt_s = 0.0 if previous_time_s is None else max(time_s - previous_time_s, 0.0)
        previous_time_s = time_s
        t_atm = float(tr.get("T_atm_511", 1.0))
        signal_cps = flux_top_atm * source_factor * response_no_atm * t_atm
        background_cps = max(float(row["background_cps"]), 1.0e-300)
        cum_signal += signal_cps * dt_s
        cum_background += background_cps * dt_s
        if dt_s > 0.0:
            weighted_t_sum += t_atm * dt_s
            live_s += dt_s
        z_val = cum_signal / math.sqrt(cum_background) if cum_background > 0.0 else 0.0
        days.append(float(row["day_mid"]))
        z_values.append(z_val)
        if keep_profile:
            profile.append(
                {
                    "scenario_id": scenario_id,
                    "source_family": source_family,
                    "spectrum": spectrum,
                    "window": window,
                    "input_flux_top_atm_ph_cm2_s": flux_top_atm,
                    "source_factor": source_factor,
                    "time_bin_id": tid,
                    "day_mid": row["day_mid"],
                    "dt_s": dt_s,
                    "altitude_km": tr.get("altitude_km", row.get("altitude_km", "")),
                    "source_zenith_deg": tr.get("source_zenith_deg", ""),
                    "path_depth_g_cm2": tr.get("path_depth_g_cm2", ""),
                    "T_atm_511": t_atm,
                    "prompt_final_cps": row["prompt_final_cps"],
                    "delayed_final_cps_level1": row["delayed_final_cps_level1"],
                    "background_cps": background_cps,
                    "activation_driver": row["activation_driver"],
                    "total_delayed_activity_Bq": row["total_delayed_activity_Bq"],
                    "signal_cps": signal_cps,
                    "cumulative_signal_counts": cum_signal,
                    "cumulative_background_counts": cum_background,
                    "cumulative_Z_counting": z_val,
                }
            )

    elapsed_days = days[-1] if days else 0.0
    final_z = z_values[-1] if z_values else 0.0
    crossing = crossing_time(days, z_values)
    extrapolated = "" if final_z <= 0.0 else elapsed_days * (3.0 / final_z) ** 2
    if crossing is None:
        reported = extrapolated
        method = "average_extrapolated_from_20day_profile"
    else:
        reported = crossing
        method = "interpolated_crossing_inside_20day_profile"

    summary = {
        "source_family": source_family,
        "scenario_id": scenario_id,
        "spectrum": spectrum,
        "window": window,
        "window_label": WINDOW_LABELS[window],
        "input_flux_top_atm_ph_cm2_s": flux_top_atm,
        "source_factor": source_factor,
        "effective_flux_factor_applied": flux_top_atm * source_factor,
        "response_no_atm_cps_per_ph_cm2_s": response_no_atm,
        "elapsed_days": elapsed_days,
        "live_s": live_s,
        "time_weighted_T_atm_511": weighted_t_sum / live_s if live_s > 0.0 else "",
        "cumulative_signal_counts": cum_signal,
        "cumulative_background_counts": cum_background,
        "final_Z_counting": final_z,
        "T3_days_counting_crossing": "" if crossing is None else crossing,
        "T3_days_counting_avg_extrapolated": extrapolated,
        "T3_days_reported": reported,
        "T3_report_method": method,
        "claim_level": "current_opticsim_response_linear_flux_rescale_with_time_dependent_atmosphere_and_L1_background",
    }
    return summary, profile


def add_day15_reference_metrics(
    row: dict[str, Any],
    *,
    background_day15: float,
    response_no_atm: float,
) -> None:
    flux_eff = float(row["input_flux_top_atm_ph_cm2_s"]) * float(row["source_factor"])
    signal_no_atm = flux_eff * response_no_atm
    signal_ref_atm = signal_no_atm * REFERENCE_T_ATM_511
    t3_no = t3_seconds(signal_no_atm, background_day15)
    t3_ref = t3_seconds(signal_ref_atm, background_day15)
    row.update(
        {
            "background_day15_cps": background_day15,
            "signal_cps_no_atm_day15": signal_no_atm,
            "signal_cps_reference_T_atm_day15": signal_ref_atm,
            "T3_days_no_atm_day15": t3_no / SECONDS_PER_DAY,
            "T3_days_reference_T_atm_day15": t3_ref / SECONDS_PER_DAY,
        }
    )


def diffuse_model_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [dict(row) for row in read_csv(path)]
    bulge8 = next(row for row in rows if row["sky_model"] == "bulge_gaussian_fwhm_8deg")
    disk = next(row for row in rows if row["sky_model"] == "disk_thick_gaussian")
    default_fov_flux = f(bulge8, "fov_flux_ph_cm2_s") + f(disk, "fov_flux_ph_cm2_s")
    default_total_flux = SPI_BULGE_FLUX + SPI_DISK_FLUX
    rows.append(
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
    return rows


def v404_source_factor(row: dict[str, str], window: str) -> tuple[float, str]:
    if window == "broad_480_550":
        return max(f(row, "Aeff_weighted_fraction"), 0.0), "Aeff_weighted_fraction_over_480_550_optics_band"
    return max(f(row, "fraction_510p3_511p8"), 0.0), "spectral_fraction_inside_510p3_511p8_detector_window"


def build_route(route: dict[str, Any]) -> dict[str, Any]:
    outdir = Path(route["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    replay = load_json(route["replay_summary"])
    responses = response_table(replay)
    bg = background_by_window(BACKGROUND)
    trans = transmission_by_bin(TRANSMISSION)

    point_rows: list[dict[str, Any]] = []
    v404_rows: list[dict[str, Any]] = []
    diffuse_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []

    selected_profiles = {
        ("generic_point_source", "", "broad_480_550", 8e-5),
        ("generic_point_source", "", "broad_480_550", 1e-4),
        ("generic_point_source", "", "broad_480_550", 3e-4),
        ("generic_point_source", "", "line_510p3_511p8", 1e-4),
        ("C_V404_2015_TRANSIENT_BENCHMARK", "v404_kT30_no_shift", "broad_480_550", 1e-3),
        ("C_V404_2015_TRANSIENT_BENCHMARK", "v404_kT30_no_shift", "line_510p3_511p8", 1e-3),
        ("diffuse_511_aperture", "B_default_bulge8deg_plus_disk", "broad_480_550", 0.0),
    }

    for window in WINDOWS:
        response_no_atm = responses[window]["response_no_atm_cps_per_ph_cm2_s"]
        background_day15 = day15_background(bg[window])
        for flux in POINT_FLUX_SCAN:
            keep_profile = ("generic_point_source", "", window, flux) in selected_profiles
            scenario_id = f"{route['route_id']}_point_{window}_{flux:.3g}"
            row, profile = integrate_time_dependent(
                flux_top_atm=flux,
                source_factor=1.0,
                response_no_atm=response_no_atm,
                background_rows=bg[window],
                trans=trans,
                scenario_id=scenario_id,
                source_family="generic_point_source",
                window=window,
                keep_profile=keep_profile,
            )
            row["literature_anchor"] = "SPI compact/point-like 511-keV flux anchor when flux=8e-5; otherwise scan value"
            add_day15_reference_metrics(row, background_day15=background_day15, response_no_atm=response_no_atm)
            point_rows.append(row)
            profile_rows.extend(profile)

        for v404 in read_csv(V404_BANDPASS):
            spectrum = v404["spectrum"]
            source_factor, factor_definition = v404_source_factor(v404, window)
            for flux in V404_FLUX_SCAN:
                keep_profile = ("C_V404_2015_TRANSIENT_BENCHMARK", spectrum, window, flux) in selected_profiles
                scenario_id = f"{route['route_id']}_v404_{spectrum}_{window}_{flux:.3g}"
                row, profile = integrate_time_dependent(
                    flux_top_atm=flux,
                    source_factor=source_factor,
                    response_no_atm=response_no_atm,
                    background_rows=bg[window],
                    trans=trans,
                    scenario_id=scenario_id,
                    source_family="C_V404_2015_TRANSIENT_BENCHMARK",
                    spectrum=spectrum,
                    window=window,
                    keep_profile=keep_profile,
                )
                row.update(
                    {
                        "case_id": v404["case_id"],
                        "center_keV": f(v404, "center_keV"),
                        "redshift": v404.get("redshift", ""),
                        "Aeff_weighted_fraction": f(v404, "Aeff_weighted_fraction"),
                        "fraction_480_550": f(v404, "fraction_480_550"),
                        "fraction_510p3_511p8": f(v404, "fraction_510p3_511p8"),
                        "source_factor_definition": factor_definition,
                        "bandpass_status": v404["bandpass_status"],
                        "v404_reference_anchor_id": V404_REFERENCE_ANCHOR["anchor_id"],
                        "v404_reference_flux_ph_cm2_s": V404_REFERENCE_ANCHOR["flux_ph_cm2_s"],
                        "v404_reference_flux_uncertainty_ph_cm2_s": V404_REFERENCE_ANCHOR["uncertainty_ph_cm2_s"],
                        "v404_reference_spectrum": V404_REFERENCE_ANCHOR["spectrum"],
                        "v404_reference_scale_factor": v404_reference_scale_factor(flux),
                        "v404_reference": V404_REFERENCE_ANCHOR["reference"],
                    }
                )
                add_day15_reference_metrics(row, background_day15=background_day15, response_no_atm=response_no_atm)
                v404_rows.append(row)
                profile_rows.extend(profile)

        for source in diffuse_model_rows(DIFFUSE):
            sky_model = source["sky_model"]
            fov_flux = f(source, "fov_flux_ph_cm2_s")
            fov_radius = f(source, "fov_radius_deg")
            omega_sr, area_deg2 = fov_solid_angle(fov_radius)
            keep_profile = ("diffuse_511_aperture", sky_model, window, 0.0) in selected_profiles
            scenario_id = f"{route['route_id']}_diffuse_{sky_model}_{window}"
            row, profile = integrate_time_dependent(
                flux_top_atm=fov_flux,
                source_factor=1.0,
                response_no_atm=response_no_atm,
                background_rows=bg[window],
                trans=trans,
                scenario_id=scenario_id,
                source_family="diffuse_511_aperture",
                spectrum=sky_model,
                window=window,
                keep_profile=keep_profile,
            )
            row.update(
                {
                    "sky_model": sky_model,
                    "kind": source["kind"],
                    "total_flux_top_atm_ph_cm2_s": f(source, "total_flux_ph_cm2_s"),
                    "fov_radius_deg": fov_radius,
                    "fov_radius_arcmin": fov_radius * 60.0,
                    "fov_solid_angle_sr": omega_sr,
                    "fov_area_deg2_small_angle": area_deg2,
                    "fov_flux_top_atm_ph_cm2_s": fov_flux,
                    "fov_fraction": f(source, "fov_fraction"),
                    "T3_years_reported": float(row["T3_days_reported"]) / 365.25 if row["T3_days_reported"] != "" else "",
                    "claim_level": "diffuse_FoV_aperture_upper_bound_using_current_onaxis_optics_response_not_full_offaxis_focal_map",
                }
            )
            add_day15_reference_metrics(row, background_day15=background_day15, response_no_atm=response_no_atm)
            diffuse_rows.append(row)
            profile_rows.extend(profile)

    write_csv(outdir / "point_source_flux_scan_time_dependent.csv", point_rows)
    write_csv(outdir / "v404_flux_scan_time_dependent.csv", v404_rows)
    write_csv(
        outdir / "v404_literature_anchor_scaled_flux_points.csv",
        [row for row in v404_rows if row.get("v404_reference_scale_factor") != ""],
    )
    write_csv(outdir / "diffuse_source_time_dependent.csv", diffuse_rows)
    write_csv(outdir / "cumulative_profiles_time_dependent.csv", profile_rows)
    make_figures(outdir, route, point_rows, v404_rows, diffuse_rows, profile_rows)

    summary = build_summary(route, replay, responses, trans, point_rows, v404_rows, diffuse_rows)
    write_json(outdir / "summary.json", summary)
    write_readme(outdir, route, summary, point_rows, v404_rows, diffuse_rows)
    return summary


def y_reported(row: dict[str, Any]) -> float:
    value = row.get("T3_days_reported", "")
    if value == "":
        return float("nan")
    return float(value)


def scaled_anchor_rows(v404_rows: list[dict[str, Any]], window: str, spectrum: str) -> list[dict[str, Any]]:
    rows = [
        row
        for row in v404_rows
        if row["window"] == window and row["spectrum"] == spectrum and row.get("v404_reference_scale_factor") != ""
    ]
    return sorted(rows, key=lambda row: float(row["v404_reference_scale_factor"]))


def make_figures(
    outdir: Path,
    route: dict[str, Any],
    point_rows: list[dict[str, Any]],
    v404_rows: list[dict[str, Any]],
    diffuse_rows: list[dict[str, Any]],
    profile_rows: list[dict[str, Any]],
) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.9))
    for window in WINDOWS:
        use = [row for row in point_rows if row["window"] == window]
        ax.plot(
            [float(row["input_flux_top_atm_ph_cm2_s"]) for row in use],
            [y_reported(row) for row in use],
            marker="o",
            ms=3.6,
            lw=1.5,
            color=WINDOW_COLORS[window],
            label=f"{WINDOW_LABELS[window]} time-dependent",
        )
    ax.axvline(8.0e-5, color="#54A24B", ls="--", lw=1.1, label="SPI compact anchor 8e-5")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("top-of-atmosphere point-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("3-sigma exposure (days)")
    ax.set_title(f"Point-source scan: {route['route_id']}")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "point_source_flux_scan_time_dependent.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.7), sharey=True)
    for ax, window in zip(axes, WINDOWS):
        use = [row for row in v404_rows if row["window"] == window]
        for spectrum, color in [
            ("v404_kT30_no_shift", "#4C78A8"),
            ("v404_kT170_no_shift", "#F58518"),
            ("v404_redshift_z0p10_narrow_proxy", "#54A24B"),
            ("v404_redshift_z0p10_broad_proxy", "#B279A2"),
        ]:
            sub = [row for row in use if row["spectrum"] == spectrum]
            if not sub:
                continue
            ax.plot(
                [float(row["input_flux_top_atm_ph_cm2_s"]) for row in sub],
                [y_reported(row) for row in sub],
                marker="o",
                ms=3.0,
                lw=1.2,
                color=color,
                label=spectrum.replace("v404_", ""),
            )
            scaled_sub = [row for row in sub if row.get("v404_reference_scale_factor") != ""]
            if scaled_sub:
                ax.scatter(
                    [float(row["input_flux_top_atm_ph_cm2_s"]) for row in scaled_sub],
                    [y_reported(row) for row in scaled_sub],
                    s=46,
                    facecolors="none",
                    edgecolors="black",
                    linewidths=0.9,
                    zorder=4,
                )
        ref_flux = float(V404_REFERENCE_ANCHOR["flux_ph_cm2_s"])
        ref_unc = float(V404_REFERENCE_ANCHOR["uncertainty_ph_cm2_s"])
        ax.axvspan(ref_flux - ref_unc, ref_flux + ref_unc, color="#222222", alpha=0.08)
        ax.axvline(ref_flux, color="#222222", ls="--", lw=1.0)
        ax.annotate(
            "Siegert+2016\norbit 1555\n6.5e-3",
            xy=(ref_flux, 0.78),
            xycoords=("data", "axes fraction"),
            xytext=(1.12 * ref_flux, 0.86),
            textcoords=("data", "axes fraction"),
            fontsize=7,
            arrowprops={"arrowstyle": "-", "lw": 0.7, "color": "#222222"},
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("input V404 feature flux (ph cm$^{-2}$ s$^{-1}$)")
        ax.set_title(WINDOW_LABELS[window])
        ax.grid(True, which="both", alpha=0.25)
    axes[0].set_ylabel("3-sigma exposure (days)")
    axes[1].legend(fontsize=7, loc="best")
    fig.suptitle(f"V404 benchmark flux scan with atmosphere: {route['route_id']}", y=1.02, fontsize=12)
    fig.tight_layout()
    fig.savefig(outdir / "v404_flux_scan_time_dependent.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 4.9))
    for window in WINDOWS:
        sub = scaled_anchor_rows(v404_rows, window, str(V404_REFERENCE_ANCHOR["spectrum"]))
        ax.plot(
            [float(row["v404_reference_scale_factor"]) for row in sub],
            [y_reported(row) for row in sub],
            marker="o",
            lw=1.6,
            color=WINDOW_COLORS[window],
            label=WINDOW_LABELS[window],
        )
        for row in sub:
            factor = float(row["v404_reference_scale_factor"])
            if same_float(factor, 1.0):
                ax.annotate(
                    f"paper flux\nF={float(row['input_flux_top_atm_ph_cm2_s']):.2e}",
                    xy=(factor, y_reported(row)),
                    xytext=(1.15, y_reported(row) * 1.6),
                    textcoords="data",
                    fontsize=8,
                    arrowprops={"arrowstyle": "->", "lw": 0.8},
                )
    ax.axvline(1.0, color="#222222", ls="--", lw=1.0)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("scale factor relative to V404 orbit-1555 paper flux")
    ax.set_ylabel("3-sigma exposure (days)")
    ax.set_title(f"V404 paper-flux scaled points: {route['route_id']}")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "v404_literature_anchor_scaled_flux_points.png", dpi=220)
    plt.close(fig)

    use = [row for row in diffuse_rows if row["window"] == "broad_480_550"]
    labels = [str(row["sky_model"]).replace("bulge_gaussian_", "bulge_").replace("_", "\n") for row in use]
    years = [float(row["T3_years_reported"]) for row in use]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    ax.bar(labels, years, color="#4C78A8")
    ax.set_yscale("log")
    ax.set_ylabel("3-sigma exposure (years)")
    ax.set_title(f"Diffuse aperture detectability: {route['route_id']}")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "diffuse_source_time_dependent.png", dpi=220)
    plt.close(fig)

    if profile_rows:
        fig, ax = plt.subplots(figsize=(8.2, 4.9))
        for scenario_id in sorted({row["scenario_id"] for row in profile_rows}):
            sub = [row for row in profile_rows if row["scenario_id"] == scenario_id]
            if not sub:
                continue
            label = scenario_id.replace(f"{route['route_id']}_", "")
            ax.plot(
                [float(row["day_mid"]) for row in sub],
                [float(row["cumulative_Z_counting"]) for row in sub],
                lw=1.2,
                label=label[:48],
            )
        ax.axhline(3.0, color="#D62728", ls="--", lw=1.0, label="3 sigma")
        ax.set_xlabel("mission day")
        ax.set_ylabel("cumulative counting Z")
        ax.set_title(f"Selected cumulative significance profiles: {route['route_id']}")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=6.5, ncol=2)
        fig.tight_layout()
        fig.savefig(outdir / "cumulative_significance_examples.png", dpi=220)
        plt.close(fig)


def row_by_flux(rows: list[dict[str, Any]], window: str, flux: float) -> dict[str, Any]:
    return next(
        row
        for row in rows
        if row["window"] == window and abs(float(row["input_flux_top_atm_ph_cm2_s"]) - flux) < max(1e-15, flux * 1e-9)
    )


def v404_key(rows: list[dict[str, Any]], window: str, spectrum: str, flux: float) -> dict[str, Any]:
    return next(
        row
        for row in rows
        if row["window"] == window
        and row["spectrum"] == spectrum
        and abs(float(row["input_flux_top_atm_ph_cm2_s"]) - flux) < max(1e-15, flux * 1e-9)
    )


def diffuse_key(rows: list[dict[str, Any]], window: str, sky_model: str) -> dict[str, Any]:
    return next(row for row in rows if row["window"] == window and row["sky_model"] == sky_model)


def build_summary(
    route: dict[str, Any],
    replay: dict[str, Any],
    responses: dict[str, dict[str, float]],
    trans: dict[int, dict[str, float]],
    point_rows: list[dict[str, Any]],
    v404_rows: list[dict[str, Any]],
    diffuse_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    t_values = [row["T_atm_511"] for row in trans.values()]
    p8 = row_by_flux(point_rows, "line_510p3_511p8", 8e-5)
    p1 = row_by_flux(point_rows, "line_510p3_511p8", 1e-4)
    vb = v404_key(v404_rows, "broad_480_550", "v404_kT30_no_shift", 1e-3)
    vl = v404_key(v404_rows, "line_510p3_511p8", "v404_kT30_no_shift", 1e-3)
    vref_b = v404_key(
        v404_rows,
        "broad_480_550",
        str(V404_REFERENCE_ANCHOR["spectrum"]),
        float(V404_REFERENCE_ANCHOR["flux_ph_cm2_s"]),
    )
    vref_l = v404_key(
        v404_rows,
        "line_510p3_511p8",
        str(V404_REFERENCE_ANCHOR["spectrum"]),
        float(V404_REFERENCE_ANCHOR["flux_ph_cm2_s"]),
    )
    diff = diffuse_key(diffuse_rows, "broad_480_550", "B_default_bulge8deg_plus_disk")
    return {
        "status": "PASS",
        "route_id": route["route_id"],
        "route_label": route["route_label"],
        "claim_level": "CURRENT_OPTICSIM_LINEAR_SOURCE_FLUX_RESCAN_WITH_TIME_DEPENDENT_ATMOSPHERE_AND_L1_BACKGROUND",
        "inputs": {
            "replay_summary": str(route["replay_summary"].relative_to(ROOT)),
            "background_time_variation": str(BACKGROUND.relative_to(ROOT)),
            "atmospheric_transmission": str(TRANSMISSION.relative_to(ROOT)),
            "diffuse_aperture": str(DIFFUSE.relative_to(ROOT)),
            "v404_bandpass": str(V404_BANDPASS.relative_to(ROOT)),
        },
        "responses": responses,
        "replay_claim_level": replay.get("claim_level"),
        "v404_reference_anchor": V404_REFERENCE_ANCHOR,
        "v404_reference_scale_factors": V404_REFERENCE_SCALE_FACTORS,
        "v404_reference_scaled_fluxes_ph_cm2_s": V404_REFERENCE_SCALED_FLUXES,
        "T_atm_511_min": min(t_values),
        "T_atm_511_max": max(t_values),
        "T_atm_511_time_weighted": p1["time_weighted_T_atm_511"],
        "key_results": {
            "point_line_8e_minus_5_T3_days_reported": p8["T3_days_reported"],
            "point_line_1e_minus_4_T3_days_reported": p1["T3_days_reported"],
            "v404_kT30_broad_1e_minus_3_T3_days_reported": vb["T3_days_reported"],
            "v404_kT30_line_1e_minus_3_T3_days_reported": vl["T3_days_reported"],
            "v404_reference_kT170_broad_orbit1555_T3_days_reported": vref_b["T3_days_reported"],
            "v404_reference_kT170_line_orbit1555_T3_days_reported": vref_l["T3_days_reported"],
            "diffuse_default_broad_T3_years_reported": diff["T3_years_reported"],
        },
        "caveats": [
            "Flux scan is a linear rescale of the current mono-511 opticsim replay response; it does not rerun Geant4 for each flux value because the transport is linear at this level.",
            "Diffuse source remains a FoV aperture upper-bound using the current on-axis response, not a full off-axis diffuse focal-map production.",
            "The significance is counting S/sqrt(B) with the current Level-1 time-dependent background ledger, not a profile likelihood.",
            "V404 is carried only as a benchmark feature-flux scan; no steady V404 source claim is made.",
        ],
    }


def write_readme(
    outdir: Path,
    route: dict[str, Any],
    summary: dict[str, Any],
    point_rows: list[dict[str, Any]],
    v404_rows: list[dict[str, Any]],
    diffuse_rows: list[dict[str, Any]],
) -> None:
    p8b = row_by_flux(point_rows, "broad_480_550", 8e-5)
    p8l = row_by_flux(point_rows, "line_510p3_511p8", 8e-5)
    p1b = row_by_flux(point_rows, "broad_480_550", 1e-4)
    p1l = row_by_flux(point_rows, "line_510p3_511p8", 1e-4)
    v404_b = v404_key(v404_rows, "broad_480_550", "v404_kT30_no_shift", 1e-3)
    v404_l = v404_key(v404_rows, "line_510p3_511p8", "v404_kT30_no_shift", 1e-3)
    vref_b = v404_key(v404_rows, "broad_480_550", str(V404_REFERENCE_ANCHOR["spectrum"]), float(V404_REFERENCE_ANCHOR["flux_ph_cm2_s"]))
    vref_l = v404_key(v404_rows, "line_510p3_511p8", str(V404_REFERENCE_ANCHOR["spectrum"]), float(V404_REFERENCE_ANCHOR["flux_ph_cm2_s"]))
    diffuse_b = diffuse_key(diffuse_rows, "broad_480_550", "B_default_bulge8deg_plus_disk")
    diffuse_l = diffuse_key(diffuse_rows, "line_510p3_511p8", "B_default_bulge8deg_plus_disk")

    lines = [
        f"# Time-dependent source significance: {route['route_id']}",
        "",
        "Status: `PASS`",
        "",
        f"Route: `{route['route_label']}`.",
        "",
        "## What Changed",
        "",
        "This directory applies the front-optics signal-source flux correction requested for the current workflow. Literature or scan fluxes are treated as top-of-atmosphere photon fluxes and are multiplied in each trajectory bin by `T_atm_511 * earth_occultation_factor` before applying the current opticsim detector response.",
        "",
        "The flux scan is a linear rescale of the already replayed current optics response. Re-running Geant4 for each flux point is unnecessary here because the optics and detector response are linear in source normalization; the stochastic transport has already supplied the response per incident flux.",
        "",
        "## Inputs",
        "",
        f"- Replay summary: `{summary['inputs']['replay_summary']}`",
        f"- Time-dependent background: `{summary['inputs']['background_time_variation']}`",
        f"- Atmospheric transmission: `{summary['inputs']['atmospheric_transmission']}`",
        f"- V404 bandpass table: `{summary['inputs']['v404_bandpass']}`",
        f"- Diffuse aperture table: `{summary['inputs']['diffuse_aperture']}`",
        "",
        "## V404 Paper Flux Anchor",
        "",
        f"- Paper anchor: `{V404_REFERENCE_ANCHOR['anchor_id']}`.",
        f"- Flux: `{fmt(V404_REFERENCE_ANCHOR['flux_ph_cm2_s'])} +/- {fmt(V404_REFERENCE_ANCHOR['uncertainty_ph_cm2_s'])} ph cm^-2 s^-1`.",
        f"- Reference: `{V404_REFERENCE_ANCHOR['reference']}`.",
        f"- Five scale points: `{', '.join(fmt(x) + 'x' for x in V404_REFERENCE_SCALE_FACTORS)}`.",
        "",
        "| scale | flux ph cm^-2 s^-1 | 480-550 T3 d | 510.3-511.8 T3 d |",
        "|---:|---:|---:|---:|",
        *[
            (
                f"| {fmt(factor)} | {fmt(V404_REFERENCE_ANCHOR['flux_ph_cm2_s'] * factor)} | "
                f"{fmt(v404_key(v404_rows, 'broad_480_550', str(V404_REFERENCE_ANCHOR['spectrum']), float(V404_REFERENCE_ANCHOR['flux_ph_cm2_s']) * factor)['T3_days_reported'])} | "
                f"{fmt(v404_key(v404_rows, 'line_510p3_511p8', str(V404_REFERENCE_ANCHOR['spectrum']), float(V404_REFERENCE_ANCHOR['flux_ph_cm2_s']) * factor)['T3_days_reported'])} |"
            )
            for factor in V404_REFERENCE_SCALE_FACTORS
        ],
        "",
        "## Atmospheric Driver",
        "",
        f"- `T_atm_511` range on the trajectory: `{fmt(summary['T_atm_511_min'])}` to `{fmt(summary['T_atm_511_max'])}`.",
        f"- Live-time weighted `T_atm_511` used by the 20-day profile: `{fmt(summary['T_atm_511_time_weighted'])}`.",
        "",
        "## Key 3sigma Results",
        "",
        "| source | window | input flux | reported T3 | method |",
        "|---|---|---:|---:|---|",
        f"| SPI compact anchor | 480-550 | 8e-5 | {fmt(p8b['T3_days_reported'])} d | {p8b['T3_report_method']} |",
        f"| SPI compact anchor | 510.3-511.8 | 8e-5 | {fmt(p8l['T3_days_reported'])} d | {p8l['T3_report_method']} |",
        f"| generic point | 480-550 | 1e-4 | {fmt(p1b['T3_days_reported'])} d | {p1b['T3_report_method']} |",
        f"| generic point | 510.3-511.8 | 1e-4 | {fmt(p1l['T3_days_reported'])} d | {p1l['T3_report_method']} |",
        f"| V404 kT30/no-shift benchmark | 480-550 | 1e-3 | {fmt(v404_b['T3_days_reported'])} d | {v404_b['T3_report_method']} |",
        f"| V404 kT30/no-shift benchmark | 510.3-511.8 | 1e-3 | {fmt(v404_l['T3_days_reported'])} d | {v404_l['T3_report_method']} |",
        f"| V404 paper anchor kT170 | 480-550 | 6.5e-3 | {fmt(vref_b['T3_days_reported'])} d | {vref_b['T3_report_method']} |",
        f"| V404 paper anchor kT170 | 510.3-511.8 | 6.5e-3 | {fmt(vref_l['T3_days_reported'])} d | {vref_l['T3_report_method']} |",
        f"| diffuse default bulge8+disk FoV aperture | 480-550 | {fmt(diffuse_b['fov_flux_top_atm_ph_cm2_s'])} | {fmt(diffuse_b['T3_years_reported'])} yr | {diffuse_b['T3_report_method']} |",
        f"| diffuse default bulge8+disk FoV aperture | 510.3-511.8 | {fmt(diffuse_l['fov_flux_top_atm_ph_cm2_s'])} | {fmt(float(diffuse_l['T3_days_reported']) / 365.25)} yr | {diffuse_l['T3_report_method']} |",
        "",
        "## V404 Factor Convention",
        "",
        "For the 480-550 keV window, the V404 benchmark uses the local `Aeff_weighted_fraction`, which already folds the broad spectral proxy through the placeholder 480-550 keV optics bandpass. For the 510.3-511.8 keV line window, it uses the direct spectral fraction inside that detector window, because off-window continuum photons should not contribute to a narrow-line count.",
        "",
        "## Files",
        "",
        "- `point_source_flux_scan_time_dependent.csv` and `.png`",
        "- `v404_flux_scan_time_dependent.csv` and `.png`",
        "- `v404_literature_anchor_scaled_flux_points.csv` and `.png`",
        "- `diffuse_source_time_dependent.csv` and `.png`",
        "- `cumulative_profiles_time_dependent.csv`",
        "- `cumulative_significance_examples.png`",
        "- `summary.json`",
        "",
        "## Remaining Limits",
        "",
        "- Diffuse source is still a FoV aperture upper-bound using the current on-axis response; it is not a full off-axis diffuse focal-map production.",
        "- 3sigma is counting `S/sqrt(B)` with the Level-1 prompt+activation background time series, not a final profile-likelihood sensitivity.",
        "- V404 remains a benchmark feature-flux scan, not a steady-source claim.",
    ]
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    summaries = [build_route(route) for route in ROUTES]
    write_json(
        ROOT / "Records/07_figure_scripts/opticsim_time_dependent_source_significance_summary.json",
        {"status": "PASS", "routes": summaries},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
