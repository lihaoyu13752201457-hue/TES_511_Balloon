#!/usr/bin/env python3
"""Build the 260516 source-model and time-variation update package.

This update deliberately does not launch new Cosima transport.  It folds
literature-anchored 511-keV sky cases through the current detector/parametric
optics response and makes the already-built Phase2 time-dependent activation
and prompt ledgers explicit as plots and tables.
"""

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
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports_260516" / "source_time_update"
FIG = OUT / "figures"

R2 = ROOT / "reports2.0"
PHASE2 = ROOT / "reports" / "phase2_real_flight_physical_production"

METRIC_CLOSURE = R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "metric_closure_final.json"
FP_COUPLING = (
    R2
    / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
    / "first_principles_channeling_optics"
    / "phase12_firstprinciples_optics_coupling.csv"
)
DIFFUSE_APERTURE = R2 / "09_SOURCE_CASES_ABC" / "diffuse_aperture_foreground.csv"
V404_BANDPASS = R2 / "09_SOURCE_CASES_ABC" / "v404_bandpass_loss.csv"
ENV_GRID = PHASE2 / "environment_grid_real" / "environment_grid_real.csv"
PROMPT_RATE = PHASE2 / "prompt_reweight_real" / "prompt_final_rate_by_time_window.csv"
SCI_TRANS = PHASE2 / "environment_grid_real" / "science_atmospheric_transmission.csv"
ACTIVITY_SERIES = R2 / "04_FIGURES" / "phase2" / "phase2_total_delayed_activity_time_series.csv"
MEASURED_RATES = PHASE2 / "event_catalog_v2_measured" / "true_vs_measured_rates.csv"

REFERENCE_EXPOSURE_S = 1.0e6
SECONDS_PER_DAY = 86400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
V404_FLUX_SCAN = [1e-5, 3e-5, 5e-5, 1e-4, 3e-4, 1e-3, 3e-3]
TIME_DEP_POINT_FLUX_SCAN = [1e-5, 3e-5, 5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4, 1e-3, 3e-3]
SCIENCE_T_REF = 0.7390423888027


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def normal_survival(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def p3_from_f3(flux: float, f3: float) -> float:
    if flux <= 0.0 or f3 <= 0.0:
        return float("nan")
    mean_sigma = 3.0 * flux / f3
    return normal_survival(3.0 - mean_sigma)


def crossing_time(days: list[float], z: list[float], threshold: float = 3.0) -> float | None:
    for i, value in enumerate(z):
        if value < threshold:
            continue
        if i == 0:
            return days[0]
        x0, x1 = days[i - 1], days[i]
        y0, y1 = z[i - 1], z[i]
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def exposure_for_3sigma(flux: float, f3_1ms: float) -> float:
    if flux <= 0.0:
        return float("inf")
    return REFERENCE_EXPOSURE_S * (f3_1ms / flux) ** 2


def exposure_for_rate(signal_cps: float, background_cps: float, sigma: float = 3.0) -> float:
    if signal_cps <= 0.0:
        return float("inf")
    return (sigma * math.sqrt(background_cps) / signal_cps) ** 2


def fmt(x: float, nd: int = 4) -> str:
    if not np.isfinite(x):
        return "inf"
    if x == 0.0:
        return "0"
    if abs(x) < 1e-3 or abs(x) >= 1e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def load_metric_authorities() -> dict[str, float]:
    metric = json.loads(METRIC_CLOSURE.read_text(encoding="utf-8"))
    primary = None
    for row in metric["rows"]:
        if row.get("metric_id") == "phase12_baseline_measured_ERL":
            primary = row
            break
    if primary is None:
        raise RuntimeError("phase12_baseline_measured_ERL not found")

    fp_rows = read_csv(FP_COUPLING)
    fp = [r for r in fp_rows if r["metric_id"] == "phase12_baseline_measured_ERL"][0]

    return {
        "background_cps": float(primary["background_cps"]),
        "response_cps_per_flux": float(primary["response_cps_per_flux"]),
        "f3_1ms": float(primary["F3_1Ms"]),
        "f5_1ms": float(primary["F5_1Ms"]),
        "p3_at_1e4_1ms": float(primary["P_ge_3sigma_at_1e-4_1Ms"]),
        "fp_response_cps_per_flux": float(fp["firstprinciples_response_cps_per_flux"]),
        "fp_f3_1ms": float(fp["firstprinciples_scaled_F3_1Ms"]),
        "fp_response_scale": float(fp["response_scale_vs_current"]),
        "fp_aeff_cm2": float(fp["firstprinciples_aeff_cm2"]),
        "cam511_reference_aeff_cm2": float(fp["cam511_reference_aeff_cm2"]),
    }


def literature_anchors() -> list[dict[str, Any]]:
    return [
        {
            "anchor_id": "SPI_MW_TOTAL_511",
            "source_class": "diffuse_milky_way",
            "quantity": "total Galactic 511-keV line intensity",
            "value_ph_cm2_s": 2.74e-3,
            "uncertainty_ph_cm2_s": 0.25e-3,
            "use_in_update": "context_only",
            "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
            "url": "https://arxiv.org/abs/1512.00325",
            "claim_note": "SPI diffuse all-sky model intensity, not a focused point-source flux.",
        },
        {
            "anchor_id": "SPI_BULGE_511",
            "source_class": "diffuse_bulge",
            "quantity": "bulge 511-keV line intensity",
            "value_ph_cm2_s": 0.96e-3,
            "uncertainty_ph_cm2_s": 0.07e-3,
            "use_in_update": "B_diffuse_total_flux",
            "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
            "url": "https://arxiv.org/abs/1512.00325",
            "claim_note": "Fold only the FoV-contained fraction into a pointed optics model.",
        },
        {
            "anchor_id": "SPI_DISK_511",
            "source_class": "diffuse_disk",
            "quantity": "disk 511-keV line intensity",
            "value_ph_cm2_s": 1.66e-3,
            "uncertainty_ph_cm2_s": 0.35e-3,
            "use_in_update": "B_diffuse_total_flux",
            "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
            "url": "https://arxiv.org/abs/1512.00325",
            "claim_note": "Broad disk foreground; not collapsible into a point source.",
        },
        {
            "anchor_id": "SPI_GCS_POINTLIKE_511",
            "source_class": "central_compact_hypothesis",
            "quantity": "point-like Galactic-centre source component",
            "value_ph_cm2_s": 0.80e-4,
            "uncertainty_ph_cm2_s": 0.19e-4,
            "use_in_update": "point_flux_anchor_scan",
            "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
            "url": "https://arxiv.org/abs/1512.00325",
            "claim_note": "Model component near Sgr A*; association is not confirmed.",
        },
        {
            "anchor_id": "SPI_V404_ANNIHILATION_FEATURE",
            "source_class": "microquasar_transient",
            "quantity": "variable positron-annihilation feature during V404 Cyg 2015 outburst",
            "value_ph_cm2_s": "",
            "uncertainty_ph_cm2_s": "",
            "use_in_update": "transient_flux_scan_not_fixed_flux",
            "reference": "Siegert et al. 2016, Nature 531, 341-343, arXiv:1603.01169",
            "url": "https://arxiv.org/abs/1603.01169",
            "claim_note": "Observed transient annihilation signature; this update uses a 1e-5..3e-3 flux grid as a literature-motivated benchmark, not as a fixed steady narrow-line source.",
        },
        {
            "anchor_id": "GAMMA_LINE_REVIEW_2026",
            "source_class": "review",
            "quantity": "recent gamma-ray-line review",
            "value_ph_cm2_s": "",
            "uncertainty_ph_cm2_s": "",
            "use_in_update": "literature_context",
            "reference": "Siegert et al. 2026, Space Sci. Rev. 222, 34",
            "url": "https://link.springer.com/article/10.1007/s11214-026-01281-y",
            "claim_note": "Recent open-access review for NIMA manuscript context.",
        },
    ]


def build_source_tables(authority: dict[str, float]) -> dict[str, Any]:
    anchors = literature_anchors()
    write_csv(
        OUT / "literature_anchor_summary.csv",
        anchors,
        [
            "anchor_id",
            "source_class",
            "quantity",
            "value_ph_cm2_s",
            "uncertainty_ph_cm2_s",
            "use_in_update",
            "reference",
            "url",
            "claim_note",
        ],
    )

    diffuse_rows: list[dict[str, Any]] = []
    background = authority["background_cps"]
    for row in read_csv(DIFFUSE_APERTURE):
        fov_flux = f(row, "fov_flux_ph_cm2_s")
        for response_id, response, f3 in [
            ("parametric_CAM511_normalized", authority["response_cps_per_flux"], authority["f3_1ms"]),
            ("firstprinciples_L2_scalar_rescale", authority["fp_response_cps_per_flux"], authority["fp_f3_1ms"]),
        ]:
            signal = fov_flux * response
            t3 = exposure_for_rate(signal, background)
            diffuse_rows.append(
                {
                    "case_id": row["sky_model"],
                    "response_id": response_id,
                    "total_flux_ph_cm2_s": row["total_flux_ph_cm2_s"],
                    "fov_radius_deg": row["fov_radius_deg"],
                    "fov_flux_ph_cm2_s": fov_flux,
                    "fov_fraction": row["fov_fraction"],
                    "signal_cps": signal,
                    "background_cps": background,
                    "T3_s": t3,
                    "T3_days": t3 / SECONDS_PER_DAY,
                    "T3_years": t3 / SECONDS_PER_YEAR,
                    "claim_level": "diffuse_aperture_foreground_not_focal_spot_source",
                }
            )

    default_bulge = [r for r in diffuse_rows if r["case_id"] == "bulge_gaussian_fwhm_8deg"]
    default_disk = [r for r in diffuse_rows if r["case_id"] == "disk_thick_gaussian"]
    for response_id in ["parametric_CAM511_normalized", "firstprinciples_L2_scalar_rescale"]:
        b = [r for r in default_bulge if r["response_id"] == response_id][0]
        d = [r for r in default_disk if r["response_id"] == response_id][0]
        fov_flux = float(b["fov_flux_ph_cm2_s"]) + float(d["fov_flux_ph_cm2_s"])
        response = authority["response_cps_per_flux"] if response_id.startswith("parametric") else authority["fp_response_cps_per_flux"]
        signal = fov_flux * response
        t3 = exposure_for_rate(signal, background)
        diffuse_rows.append(
            {
                "case_id": "B_default_bulge8deg_plus_disk",
                "response_id": response_id,
                "total_flux_ph_cm2_s": 0.96e-3 + 1.66e-3,
                "fov_radius_deg": b["fov_radius_deg"],
                "fov_flux_ph_cm2_s": fov_flux,
                "fov_fraction": fov_flux / (0.96e-3 + 1.66e-3),
                "signal_cps": signal,
                "background_cps": background,
                "T3_s": t3,
                "T3_days": t3 / SECONDS_PER_DAY,
                "T3_years": t3 / SECONDS_PER_YEAR,
                "claim_level": "default_SPI_diffuse_aperture_foreground",
            }
        )

    write_csv(OUT / "spi_diffuse_detectability.csv", diffuse_rows)

    scan_fluxes = [
        1e-9,
        3e-9,
        1e-8,
        3e-8,
        1e-7,
        3e-7,
        1e-6,
        3e-6,
        1e-5,
        3e-5,
        5e-5,
        8e-5,
        1e-4,
        1.5e-4,
        2e-4,
        3e-4,
        1e-3,
        3e-3,
    ]
    point_rows: list[dict[str, Any]] = []
    for flux in scan_fluxes:
        for response_id, f3, response, claim in [
            (
                "parametric_CAM511_normalized_phase12_primary",
                authority["f3_1ms"],
                authority["response_cps_per_flux"],
                "PARAMETRIC_OPTICS_REQUIREMENT",
            ),
            (
                "firstprinciples_L2_scalar_rescale_requirement_input",
                authority["fp_f3_1ms"],
                authority["fp_response_cps_per_flux"],
                "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT",
            ),
        ]:
            t3 = exposure_for_3sigma(flux, f3)
            point_rows.append(
                {
                    "source_family": "generic_point_source_flux_scan",
                    "response_id": response_id,
                    "flux_ph_cm2_s": flux,
                    "signal_cps": flux * response,
                    "F3_1Ms_ph_cm2_s": f3,
                    "P_ge_3sigma_at_1Ms": p3_from_f3(flux, f3),
                    "T3_s_Asimov": t3,
                    "T3_days_Asimov": t3 / SECONDS_PER_DAY,
                    "T3_years_Asimov": t3 / SECONDS_PER_YEAR,
                    "claim_level": claim,
                }
            )

    # Explicit literature benchmark rows.
    for case_id, flux, note in [
        ("SPI_GCS_POINTLIKE_ANCHOR", 0.80e-4, "SPI model-fit central point-like component; association not confirmed"),
    ]:
        for response_id, f3, response in [
            ("parametric_CAM511_normalized_phase12_primary", authority["f3_1ms"], authority["response_cps_per_flux"]),
            ("firstprinciples_L2_scalar_rescale_requirement_input", authority["fp_f3_1ms"], authority["fp_response_cps_per_flux"]),
        ]:
            t3 = exposure_for_3sigma(flux, f3)
            point_rows.append(
                {
                    "source_family": case_id,
                    "response_id": response_id,
                    "flux_ph_cm2_s": flux,
                    "signal_cps": flux * response,
                    "F3_1Ms_ph_cm2_s": f3,
                    "P_ge_3sigma_at_1Ms": p3_from_f3(flux, f3),
                    "T3_s_Asimov": t3,
                    "T3_days_Asimov": t3 / SECONDS_PER_DAY,
                    "T3_years_Asimov": t3 / SECONDS_PER_YEAR,
                    "claim_level": "literature_benchmark_scan",
                    "note": note,
                }
            )

    write_csv(OUT / "point_source_flux_scan.csv", point_rows)

    v404_rows: list[dict[str, Any]] = []
    bandpass_rows = read_csv(V404_BANDPASS)
    transient_fluxes = V404_FLUX_SCAN
    exposures = [3600.0, 6 * 3600.0, 24 * 3600.0, 72 * 3600.0]
    for bp in bandpass_rows:
        if not bp["spectrum"].startswith("v404"):
            continue
        aeff_fraction = f(bp, "Aeff_weighted_fraction")
        for flux in transient_fluxes:
            effective_flux = flux * max(aeff_fraction, 0.0)
            t3 = exposure_for_3sigma(effective_flux, authority["f3_1ms"])
            for exposure in exposures:
                sigma = 3.0 * effective_flux / authority["f3_1ms"] * math.sqrt(exposure / REFERENCE_EXPOSURE_S)
                v404_rows.append(
                    {
                        "case_id": "C_V404_2015_TRANSIENT_BENCHMARK",
                        "spectrum": bp["spectrum"],
                        "status": bp["bandpass_status"],
                        "input_flux_ph_cm2_s": flux,
                        "aeff_weighted_fraction": aeff_fraction,
                        "effective_flux_ph_cm2_s": effective_flux,
                        "exposure_s": exposure,
                        "expected_sigma_parametric": sigma,
                        "T3_days_parametric": t3 / SECONDS_PER_DAY,
                        "T3_s_parametric": t3,
                        "claim_level": "transient_observed_feature_flux_benchmark_not_final_detectability",
                    }
                )
    write_csv(OUT / "transient_point_benchmarks.csv", v404_rows)

    make_source_figures(diffuse_rows, point_rows)

    return {
        "anchors": anchors,
        "diffuse_rows": diffuse_rows,
        "point_rows": point_rows,
        "v404_rows": v404_rows,
    }


def unique_trajectory_rows() -> list[dict[str, Any]]:
    if not ENV_GRID.exists():
        fallback = OUT / "trajectory_profile.csv"
        if fallback.exists() and fallback.stat().st_size > 0:
            rows = []
            for row in read_csv(fallback):
                rows.append(
                    {
                        "time_bin_id": int(float(row["time_bin_id"])),
                        "time_mid_s": f(row, "time_mid_s"),
                        "day_mid": f(row, "day_mid"),
                        "altitude_km": f(row, "altitude_km"),
                        "latitude_deg": f(row, "latitude_deg"),
                        "longitude_deg": f(row, "longitude_deg"),
                        "Rc_GV": f(row, "Rc_GV"),
                        "depth_g_cm2": f(row, "depth_g_cm2"),
                    }
                )
            rows.sort(key=lambda r: r["time_bin_id"])
            return rows
        raise FileNotFoundError(
            f"missing {ENV_GRID.relative_to(ROOT)} and no bootstrap {fallback.relative_to(ROOT)}"
        )
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for row in read_csv(ENV_GRID):
        tid = int(float(row["time_bin_id"]))
        if tid in seen:
            continue
        seen.add(tid)
        rows.append(
            {
                "time_bin_id": tid,
                "time_mid_s": f(row, "time_mid_s"),
                "day_mid": f(row, "day_mid"),
                "altitude_km": f(row, "altitude_km"),
                "latitude_deg": f(row, "latitude_deg"),
                "longitude_deg": f(row, "longitude_deg"),
                "Rc_GV": f(row, "Rc_GV"),
                "depth_g_cm2": f(row, "depth_g_cm2"),
            }
        )
    rows.sort(key=lambda r: r["time_bin_id"])
    return rows


def build_time_variation_tables() -> dict[str, Any]:
    trajectory = unique_trajectory_rows()
    write_csv(OUT / "trajectory_profile.csv", trajectory)

    prompt = read_csv(PROMPT_RATE)
    prompt_index: dict[tuple[float, str], float] = {}
    for row in prompt:
        if row["particle"] == "TOTAL":
            prompt_index[(round(f(row, "day_mid"), 6), row["window"])] = f(row, "final_cps")

    activity_rows = read_csv(ACTIVITY_SERIES)
    activity_index = {round(f(r, "day"), 6): r for r in activity_rows}

    rate_rows = read_csv(MEASURED_RATES)
    total_measured = {
        row["window"]: f(row, "final_cps")
        for row in rate_rows
        if row["energy_type"] == "measured"
    }
    day15 = 15.0
    day15_activity = f(activity_index[round(day15, 6)], "total_delayed_activity_Bq")
    delayed_day15: dict[str, float] = {}
    for window in ("broad_480_550", "line_510p3_511p8"):
        prompt_day15 = prompt_index[(day15, window)]
        delayed_day15[window] = total_measured[window] - prompt_day15

    background_rows: list[dict[str, Any]] = []
    for tr in trajectory:
        day = round(float(tr["day_mid"]), 6)
        if day not in activity_index:
            continue
        activity = f(activity_index[day], "total_delayed_activity_Bq")
        driver = f(activity_index[day], "activation_driver")
        for window in ("broad_480_550", "line_510p3_511p8"):
            prompt_final = prompt_index.get((day, window), float("nan"))
            delayed_final = delayed_day15[window] * activity / day15_activity if day15_activity > 0 else float("nan")
            total_final = prompt_final + delayed_final
            background_rows.append(
                {
                    "time_bin_id": tr["time_bin_id"],
                    "day_mid": day,
                    "window": window,
                    "altitude_km": tr["altitude_km"],
                    "latitude_deg": tr["latitude_deg"],
                    "longitude_deg": tr["longitude_deg"],
                    "Rc_GV": tr["Rc_GV"],
                    "depth_g_cm2": tr["depth_g_cm2"],
                    "activation_driver": driver,
                    "total_delayed_activity_Bq": activity,
                    "prompt_final_cps": prompt_final,
                    "delayed_final_cps_level1": delayed_final,
                    "total_background_final_cps_level1": total_final,
                    "delayed_scaling_reference": "measured_total_minus_prompt_day15_scaled_by_total_activity",
                    "spatial_profile_mode": "fixed_day15_scaled",
                }
            )
    write_csv(OUT / "background_time_variation.csv", background_rows)
    make_time_figures(trajectory, background_rows)

    return {
        "trajectory": trajectory,
        "background_rows": background_rows,
        "day15_activity_Bq": day15_activity,
        "delayed_day15_cps": delayed_day15,
    }


def make_source_figures(diffuse_rows: list[dict[str, Any]], point_rows: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    default_diffuse = [
        r
        for r in diffuse_rows
        if r["case_id"] == "B_default_bulge8deg_plus_disk"
        and r["response_id"] == "parametric_CAM511_normalized"
    ][0]
    labels = []
    years = []
    for r in diffuse_rows:
        if r["response_id"] != "parametric_CAM511_normalized":
            continue
        labels.append(str(r["case_id"]).replace("bulge_gaussian_", "bulge_").replace("_", "\n"))
        years.append(float(r["T3_years"]))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(labels, years, color="#4C78A8")
    ax.set_yscale("log")
    ax.set_ylabel("3-sigma exposure (years)")
    ax.set_title("SPI diffuse 511-keV emission through the pointed FoV aperture")
    ax.axhline(default_diffuse["T3_years"], color="#E45756", linestyle="--", linewidth=1.2, label="default bulge8+disk")
    ax.legend()
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "diffuse_exposure_requirement.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.6))
    for response_id, color in [
        ("parametric_CAM511_normalized_phase12_primary", "#4C78A8"),
        ("firstprinciples_L2_scalar_rescale_requirement_input", "#F58518"),
    ]:
        rows = [
            r
            for r in point_rows
            if r["source_family"] == "generic_point_source_flux_scan"
            and r["response_id"] == response_id
        ]
        x = [float(r["flux_ph_cm2_s"]) for r in rows]
        y = [float(r["T3_days_Asimov"]) for r in rows]
    ax.plot(x, y, marker="o", markersize=3.5, label=response_id, color=color)
    ax.axvline(0.8e-4, color="#54A24B", linestyle="--", linewidth=1.1, label="SPI central component anchor")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("point-source line flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("Asimov 3-sigma exposure (days)")
    ax.set_title("Point-source flux scan")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "point_source_flux_scan.png", dpi=180)
    plt.close(fig)


def make_time_figures(trajectory: list[dict[str, Any]], background_rows: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    days = np.array([float(r["day_mid"]) for r in trajectory])
    lat = np.array([float(r["latitude_deg"]) for r in trajectory])
    lon = np.array([float(r["longitude_deg"]) for r in trajectory])
    alt = np.array([float(r["altitude_km"]) for r in trajectory])
    depth = np.array([float(r["depth_g_cm2"]) for r in trajectory])

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    sc = ax.scatter(lon, lat, c=days, s=25 + 3.0 * (alt - np.nanmin(alt)), cmap="viridis", edgecolor="black", linewidth=0.25)
    ax.plot(lon, lat, color="#555555", linewidth=0.8, alpha=0.7)
    ax.set_xlabel("longitude (deg)")
    ax.set_ylabel("latitude (deg)")
    ax.set_title("Reference balloon trajectory used for Phase2 reweighting")
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("mission day")
    fig.tight_layout()
    fig.savefig(FIG / "trajectory_lat_lon_altitude.png", dpi=180)
    plt.close(fig)

    fig, ax1 = plt.subplots(figsize=(8.2, 4.5))
    ax1.plot(days, alt, color="#4C78A8", label="altitude")
    ax1.set_xlabel("mission day")
    ax1.set_ylabel("altitude (km)", color="#4C78A8")
    ax1.tick_params(axis="y", labelcolor="#4C78A8")
    ax2 = ax1.twinx()
    ax2.plot(days, depth, color="#E45756", label="atmospheric depth")
    ax2.set_ylabel("depth (g cm$^{-2}$)", color="#E45756")
    ax2.tick_params(axis="y", labelcolor="#E45756")
    ax1.set_title("Altitude and atmospheric depth profile")
    fig.tight_layout()
    fig.savefig(FIG / "altitude_depth_vs_time.png", dpi=180)
    plt.close(fig)

    for window, title in [
        ("broad_480_550", "480-550 keV final background"),
        ("line_510p3_511p8", "510.3-511.8 keV final background"),
    ]:
        rows = [r for r in background_rows if r["window"] == window]
        x = np.array([float(r["day_mid"]) for r in rows])
        prompt = np.array([float(r["prompt_final_cps"]) for r in rows])
        delayed = np.array([float(r["delayed_final_cps_level1"]) for r in rows])
        total = np.array([float(r["total_background_final_cps_level1"]) for r in rows])

        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        ax.plot(x, prompt, label="prompt particle-scale reweight", color="#4C78A8")
        ax.plot(x, delayed, label="delayed Level-1 activation", color="#F58518")
        ax.plot(x, total, label="total", color="#54A24B", linewidth=2.0)
        ax.set_xlabel("mission day")
        ax.set_ylabel("final selected rate (cps)")
        ax.set_title(title)
        ax.legend()
        fig.tight_layout()
        suffix = "broad" if window == "broad_480_550" else "line"
        fig.savefig(FIG / f"background_time_variation_{suffix}.png", dpi=180)
        plt.close(fig)

    act_rows = [r for r in background_rows if r["window"] == "broad_480_550"]
    x = np.array([float(r["day_mid"]) for r in act_rows])
    activity = np.array([float(r["total_delayed_activity_Bq"]) for r in act_rows])
    driver = np.array([float(r["activation_driver"]) for r in act_rows])
    fig, ax1 = plt.subplots(figsize=(8.3, 4.6))
    ax1.plot(x, activity, color="#F58518", label="total delayed activity")
    ax1.set_xlabel("mission day")
    ax1.set_ylabel("activity (Bq)", color="#F58518")
    ax1.tick_params(axis="y", labelcolor="#F58518")
    ax2 = ax1.twinx()
    ax2.plot(x, driver, color="#4C78A8", alpha=0.85, label="activation driver")
    ax2.set_ylabel("relative activation driver", color="#4C78A8")
    ax2.tick_params(axis="y", labelcolor="#4C78A8")
    ax1.set_title("Time-dependent activation driven by the reference trajectory")
    fig.tight_layout()
    fig.savefig(FIG / "delayed_activity_driver_time_variation.png", dpi=180)
    plt.close(fig)


def time_grid_rows(time_data: dict[str, Any]) -> list[dict[str, Any]]:
    bg_rows = [
        r for r in time_data["background_rows"]
        if r["window"] == "broad_480_550"
    ]
    bg_rows.sort(key=lambda r: int(float(r["time_bin_id"])))
    trans_by_bin = {int(float(r["time_bin_id"])): r for r in read_csv(SCI_TRANS)}
    grid: list[dict[str, Any]] = []
    prev_time_s: float | None = None
    for row in bg_rows:
        tid = int(float(row["time_bin_id"]))
        tr = trans_by_bin.get(tid)
        time_s = f(tr, "time_mid_s") if tr is not None else float(row["day_mid"]) * SECONDS_PER_DAY
        dt_s = 0.0 if prev_time_s is None else max(time_s - prev_time_s, 0.0)
        prev_time_s = time_s
        t_atm = (f(tr, "T_atm_511", 1.0) * f(tr, "earth_occultation_factor", 1.0)) if tr is not None else 1.0
        grid.append(
            {
                "time_bin_id": tid,
                "time_mid_s": time_s,
                "day_mid": float(row["day_mid"]),
                "dt_s": dt_s,
                "T_atm_511": t_atm,
                "source_zenith_deg": f(tr, "source_zenith_deg") if tr is not None else "",
                "atm_scale_vs_reference": t_atm / SCIENCE_T_REF if SCIENCE_T_REF > 0 else 1.0,
                "prompt_final_cps": float(row["prompt_final_cps"]),
                "delayed_final_cps_level1": float(row["delayed_final_cps_level1"]),
                "background_cps": float(row["total_background_final_cps_level1"]),
                "activation_driver": float(row["activation_driver"]),
                "total_delayed_activity_Bq": float(row["total_delayed_activity_Bq"]),
            }
        )
    return grid


def integrate_time_dependent_case(
    grid: list[dict[str, Any]],
    *,
    flux: float,
    source_factor: float,
    response_cps_per_flux: float,
    f3_1ms: float,
    background_ref_cps: float,
    scenario_id: str,
    source_family: str,
    spectrum: str = "",
    keep_profile: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    info_ref_per_s = (3.0 / f3_1ms) ** 2 / REFERENCE_EXPOSURE_S
    cum_signal = 0.0
    cum_background = 0.0
    cum_metric_info = 0.0
    days: list[float] = []
    z_counting: list[float] = []
    z_metric: list[float] = []
    profile: list[dict[str, Any]] = []
    for row in grid:
        atm_scale = float(row["atm_scale_vs_reference"])
        background = max(float(row["background_cps"]), 1.0e-300)
        dt_s = float(row["dt_s"])
        signal_rate = flux * source_factor * response_cps_per_flux * atm_scale
        cum_signal += signal_rate * dt_s
        cum_background += background * dt_s
        cum_metric_info += info_ref_per_s * (source_factor * atm_scale) ** 2 * background_ref_cps / background * dt_s
        z_c = cum_signal / math.sqrt(cum_background) if cum_background > 0 else 0.0
        z_m = flux * math.sqrt(cum_metric_info) if cum_metric_info > 0 else 0.0
        day = float(row["day_mid"])
        days.append(day)
        z_counting.append(z_c)
        z_metric.append(z_m)
        if keep_profile:
            profile.append(
                {
                    "scenario_id": scenario_id,
                    "source_family": source_family,
                    "spectrum": spectrum,
                    "input_flux_ph_cm2_s": flux,
                    "source_factor": source_factor,
                    "time_bin_id": row["time_bin_id"],
                    "day_mid": day,
                    "dt_s": dt_s,
                    "T_atm_511": row["T_atm_511"],
                    "atm_scale_vs_reference": atm_scale,
                    "source_zenith_deg": row["source_zenith_deg"],
                    "prompt_final_cps": row["prompt_final_cps"],
                    "delayed_final_cps_level1": row["delayed_final_cps_level1"],
                    "background_cps": background,
                    "activation_driver": row["activation_driver"],
                    "total_delayed_activity_Bq": row["total_delayed_activity_Bq"],
                    "signal_cps": signal_rate,
                    "cumulative_signal_counts": cum_signal,
                    "cumulative_background_counts": cum_background,
                    "cumulative_Z_counting": z_c,
                    "cumulative_Z_metric_scaled": z_m,
                }
            )

    final_day = days[-1] if days else 0.0
    final_z_c = z_counting[-1] if z_counting else 0.0
    final_z_m = z_metric[-1] if z_metric else 0.0
    cross_c = crossing_time(days, z_counting)
    cross_m = crossing_time(days, z_metric)
    summary = {
        "scenario_id": scenario_id,
        "source_family": source_family,
        "spectrum": spectrum,
        "input_flux_ph_cm2_s": flux,
        "source_factor": source_factor,
        "response_cps_per_flux_reference": response_cps_per_flux,
        "F3_1Ms_reference_ph_cm2_s": f3_1ms,
        "background_ref_cps": background_ref_cps,
        "reference_T_atm_511": SCIENCE_T_REF,
        "elapsed_days": final_day,
        "cumulative_signal_counts": cum_signal,
        "cumulative_background_counts": cum_background,
        "final_Z_counting": final_z_c,
        "final_Z_metric_scaled": final_z_m,
        "T3_days_counting_crossing": "" if cross_c is None else cross_c,
        "T3_days_metric_crossing": "" if cross_m is None else cross_m,
        "T3_days_counting_avg_extrapolated": "" if final_z_c <= 0 else final_day * (3.0 / final_z_c) ** 2,
        "T3_days_metric_avg_extrapolated": "" if final_z_m <= 0 else final_day * (3.0 / final_z_m) ** 2,
        "claim_level": "time_dependent_background_and_atmosphere_L1_not_full_profile_likelihood",
    }
    return summary, profile


def build_time_dependent_detectability(
    source: dict[str, Any],
    time_data: dict[str, Any],
    authority: dict[str, float],
) -> dict[str, Any]:
    grid = time_grid_rows(time_data)
    write_csv(OUT / "time_dependent_driver_grid.csv", grid)

    point_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    selected_profile_keys = {
        ("generic_point_source", 8e-5, ""),
        ("generic_point_source", 1e-4, ""),
        ("generic_point_source", 3e-4, ""),
    }
    for response_id, response, f3 in [
        ("parametric_CAM511_normalized_phase12_primary", authority["response_cps_per_flux"], authority["f3_1ms"]),
        ("firstprinciples_L2_scalar_rescale_requirement_input", authority["fp_response_cps_per_flux"], authority["fp_f3_1ms"]),
    ]:
        for flux in TIME_DEP_POINT_FLUX_SCAN:
            keep = response_id.startswith("parametric") and ("generic_point_source", flux, "") in selected_profile_keys
            scenario = f"generic_{response_id}_{flux:.3g}"
            summary, profile = integrate_time_dependent_case(
                grid,
                flux=flux,
                source_factor=1.0,
                response_cps_per_flux=response,
                f3_1ms=f3,
                background_ref_cps=authority["background_cps"],
                scenario_id=scenario,
                source_family="generic_point_source",
                keep_profile=keep,
            )
            summary["response_id"] = response_id
            point_rows.append(summary)
            profile_rows.extend(profile)

    v404_rows: list[dict[str, Any]] = []
    bandpass_rows = [r for r in read_csv(V404_BANDPASS) if r["spectrum"].startswith("v404")]
    selected_v404_profiles = {
        ("v404_kT30_no_shift", 1e-4),
        ("v404_kT30_no_shift", 1e-3),
        ("v404_kT30_no_shift", 3e-3),
        ("v404_redshift_z0p10_narrow_proxy", 3e-3),
    }
    for bp in bandpass_rows:
        spectrum = bp["spectrum"]
        aeff_fraction = max(f(bp, "Aeff_weighted_fraction"), 0.0)
        for flux in V404_FLUX_SCAN:
            keep = (spectrum, flux) in selected_v404_profiles
            scenario = f"v404_{spectrum}_{flux:.3g}"
            summary, profile = integrate_time_dependent_case(
                grid,
                flux=flux,
                source_factor=aeff_fraction,
                response_cps_per_flux=authority["response_cps_per_flux"],
                f3_1ms=authority["f3_1ms"],
                background_ref_cps=authority["background_cps"],
                scenario_id=scenario,
                source_family="C_V404_2015_TRANSIENT_BENCHMARK",
                spectrum=spectrum,
                keep_profile=keep,
            )
            summary["bandpass_status"] = bp["bandpass_status"]
            v404_rows.append(summary)
            profile_rows.extend(profile)

    write_csv(OUT / "time_dependent_point_source_scan.csv", point_rows)
    write_csv(OUT / "time_dependent_v404_benchmarks.csv", v404_rows)
    write_csv(OUT / "time_dependent_cumulative_profiles.csv", profile_rows)
    make_time_dependent_figures(grid, point_rows, v404_rows, profile_rows, source)
    return {
        "driver_grid": grid,
        "point_time_rows": point_rows,
        "v404_time_rows": v404_rows,
        "profile_rows": profile_rows,
    }


def make_time_dependent_figures(
    grid: list[dict[str, Any]],
    point_rows: list[dict[str, Any]],
    v404_rows: list[dict[str, Any]],
    profile_rows: list[dict[str, Any]],
    source: dict[str, Any],
) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    days = np.array([float(r["day_mid"]) for r in grid])
    bg = np.array([float(r["background_cps"]) for r in grid])
    prompt = np.array([float(r["prompt_final_cps"]) for r in grid])
    delayed = np.array([float(r["delayed_final_cps_level1"]) for r in grid])
    tatm = np.array([float(r["T_atm_511"]) for r in grid])

    fig, ax1 = plt.subplots(figsize=(8.6, 4.8))
    ax1.plot(days, bg, color="#4C78A8", lw=2.0, label="total final background")
    ax1.plot(days, prompt, color="#72B7B2", lw=1.4, label="prompt final")
    ax1.plot(days, delayed, color="#F58518", lw=1.4, label="delayed final")
    ax1.set_xlabel("mission day")
    ax1.set_ylabel("background rate (cps)")
    ax2 = ax1.twinx()
    ax2.plot(days, tatm, color="#E45756", lw=1.6, alpha=0.85, label="T_atm(511)")
    ax2.set_ylabel("511 keV atmospheric transmission")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax1.set_title("Time-dependent final background and science-source transmission")
    fig.tight_layout()
    fig.savefig(FIG / "time_dependent_background_transmission_drivers.png", dpi=180)
    plt.close(fig)

    static_by_flux = {
        float(r["flux_ph_cm2_s"]): float(r["T3_days_Asimov"])
        for r in source["point_rows"]
        if r["source_family"] == "generic_point_source_flux_scan"
        and r["response_id"] == "parametric_CAM511_normalized_phase12_primary"
    }
    rows = [
        r for r in point_rows
        if r["source_family"] == "generic_point_source"
        and r.get("response_id") == "parametric_CAM511_normalized_phase12_primary"
    ]
    x = np.array([float(r["input_flux_ph_cm2_s"]) for r in rows])
    y_td = np.array([
        float(r["T3_days_metric_crossing"]) if r["T3_days_metric_crossing"] != "" else float(r["T3_days_metric_avg_extrapolated"])
        for r in rows
    ])
    y_static = np.array([static_by_flux.get(float(r["input_flux_ph_cm2_s"]), np.nan) for r in rows])
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(x, y_static, marker="o", color="#9D755D", label="static Asimov benchmark")
    ax.plot(x, y_td, marker="s", color="#4C78A8", label="time-dependent L1 metric-scaled")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("point-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("3-sigma exposure (days)")
    ax.set_title("Static versus time-dependent point-source benchmark")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "time_dependent_point_source_scan.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for scenario in sorted({r["scenario_id"] for r in profile_rows}):
        rows_s = [r for r in profile_rows if r["scenario_id"] == scenario]
        rows_s.sort(key=lambda r: int(float(r["time_bin_id"])))
        if "generic" in scenario:
            label = scenario.replace("generic_parametric_CAM511_normalized_phase12_primary_", "generic F=")
            color = None
            ls = "-"
        elif "redshift" in scenario:
            label = "V404 z=0.10 F=" + scenario.split("_")[-1]
            color = "#E45756"
            ls = "--"
        else:
            label = "V404 kT30 F=" + scenario.split("_")[-1]
            color = None
            ls = "-"
        ax.plot(
            [float(r["day_mid"]) for r in rows_s],
            [float(r["cumulative_Z_metric_scaled"]) for r in rows_s],
            lw=1.8,
            linestyle=ls,
            label=label,
            color=color,
        )
    ax.axhline(3.0, color="#333333", ls=":", lw=1.3)
    ax.set_xlabel("mission day")
    ax.set_ylabel("cumulative Z, metric-scaled")
    ax.set_title("Time-dependent cumulative significance examples")
    ax.grid(True, alpha=0.24)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "time_dependent_cumulative_significance.png", dpi=180)
    plt.close(fig)

def write_markdown(
    source: dict[str, Any],
    time_data: dict[str, Any],
    time_dep: dict[str, Any],
    authority: dict[str, float],
) -> None:
    diffuse_default = [
        r
        for r in source["diffuse_rows"]
        if r["case_id"] == "B_default_bulge8deg_plus_disk"
        and r["response_id"] == "parametric_CAM511_normalized"
    ][0]
    gcs_rows = [
        r
        for r in source["point_rows"]
        if r["source_family"] == "SPI_GCS_POINTLIKE_ANCHOR"
        and r["response_id"] == "parametric_CAM511_normalized_phase12_primary"
    ]
    v404_kT30_rows = [
        r
        for r in source["v404_rows"]
        if r["spectrum"] == "v404_kT30_no_shift" and float(r["exposure_s"]) == 86400.0
    ]
    v404_z_rows = [
        r
        for r in source["v404_rows"]
        if r["spectrum"] == "v404_redshift_z0p10_narrow_proxy" and float(r["exposure_s"]) == 86400.0
    ]
    v404_kT30_by_flux = {float(r["input_flux_ph_cm2_s"]): r for r in v404_kT30_rows}
    v404_z_by_flux = {float(r["input_flux_ph_cm2_s"]): r for r in v404_z_rows}
    broad = [r for r in time_data["background_rows"] if r["window"] == "broad_480_550"]
    line = [r for r in time_data["background_rows"] if r["window"] == "line_510p3_511p8"]
    broad_total = [float(r["total_background_final_cps_level1"]) for r in broad]
    line_total = [float(r["total_background_final_cps_level1"]) for r in line]
    broad_prompt = [float(r["prompt_final_cps"]) for r in broad]
    broad_delayed = [float(r["delayed_final_cps_level1"]) for r in broad]
    point_td = [
        r for r in time_dep["point_time_rows"]
        if r.get("response_id") == "parametric_CAM511_normalized_phase12_primary"
    ]
    point_td_by_flux = {float(r["input_flux_ph_cm2_s"]): r for r in point_td}
    v404_td_by_key = {
        (r["spectrum"], float(r["input_flux_ph_cm2_s"])): r
        for r in time_dep["v404_time_rows"]
    }

    lines = [
        "# COSMOSRAY_BG_260516 Source and Time-Variation Update",
        "",
        "## Scope",
        "",
        "This package updates the 2605 source/time-variable interpretation without launching new large Cosima transport.",
        "It folds SPI/INTEGRAL 511-keV literature anchors through the current Phase12 parametric detector response and makes the Phase2 time-dependent prompt/activation ledgers explicit.",
        "",
        "## Source-Model Conclusions",
        "",
        f"- Current Phase12 primary response: `{authority['response_cps_per_flux']:.12g} cps/(ph cm^-2 s^-1)`.",
        f"- Current Phase12 primary F3 at 1 Ms: `{authority['f3_1ms']:.6e} ph cm^-2 s^-1`.",
        f"- First-principles L2 scalar optics response is only `{authority['fp_response_scale']:.6g}` of the CAM511-normalized response; its F3 is `{authority['fp_f3_1ms']:.6e}`.",
        f"- SPI diffuse default B model through the pointed FoV gives signal `{float(diffuse_default['signal_cps']):.6e} cps`; Asimov 3-sigma exposure is `{float(diffuse_default['T3_years']):.3e}` years. This is effectively not a suitable diffuse-source measurement mode.",
        f"- SPI central point-like component anchor `8.0e-5 ph cm^-2 s^-1` reaches Asimov 3-sigma after `{float(gcs_rows[0]['T3_days_Asimov']):.3f}` days under the inherited parametric response, but this remains a requirements/proxy result, not production optics detectability.",
        "- White-dwarf/classical-nova source cases are intentionally excluded from the current benchmark set; the active source set is SPI diffuse/compact plus V404 flux-scan benchmarks.",
        f"- V404 Cyg is now carried as an observed-feature flux benchmark grid, not a single steady source. For the kT30/no-shift proxy, `1e-4`, `1e-3`, and `3e-3 ph cm^-2 s^-1` give Asimov 3-sigma times of `{float(v404_kT30_by_flux[1e-4]['T3_days_parametric']):.3f}`, `{float(v404_kT30_by_flux[1e-3]['T3_days_parametric']):.3f}`, and `{float(v404_kT30_by_flux[3e-3]['T3_days_parametric']):.3f}` days after bandpass folding.",
        f"- The redshifted narrow V404 proxy is a cautionary counterexample: at `3e-3 ph cm^-2 s^-1`, only `{float(v404_z_by_flux[3e-3]['aeff_weighted_fraction']):.3f}` of the assumed spectrum remains Aeff-weighted in band, giving `{float(v404_z_by_flux[3e-3]['T3_days_parametric']):.3f}` days.",
        f"- Time-dependent L1 integration is now available. Including prompt variation, Level-1 activation buildup/decay, and `T_atm(t)`, the SPI compact-anchor flux `8e-5 ph cm^-2 s^-1` gives final 20-day metric-scaled Z=`{float(point_td_by_flux[8e-5]['final_Z_metric_scaled']):.3f}` and average-extrapolated T3=`{float(point_td_by_flux[8e-5]['T3_days_metric_avg_extrapolated']):.3f}` days.",
        f"- Under the same time-dependent integration, `1e-4` and `3e-4 ph cm^-2 s^-1` point-source fluxes give average-extrapolated metric T3 values of `{float(point_td_by_flux[1e-4]['T3_days_metric_avg_extrapolated']):.3f}` and `{float(point_td_by_flux[3e-4]['T3_days_metric_avg_extrapolated']):.3f}` days. Crossing days are reported in `time_dependent_point_source_scan.csv` when they occur inside the 20-day profile.",
        f"- V404 kT30/no-shift with `1e-3 ph cm^-2 s^-1` reaches metric-scaled 3 sigma at day `{float(v404_td_by_key[('v404_kT30_no_shift', 1e-3)]['T3_days_metric_crossing']):.3f}` in the time-dependent profile; the redshifted narrow `3e-3` proxy has final 20-day metric Z=`{float(v404_td_by_key[('v404_redshift_z0p10_narrow_proxy', 3e-3)]['final_Z_metric_scaled']):.3f}`.",
        "",
        "## Time-Variation Conclusions",
        "",
        f"- The reference trajectory spans altitude `{min(float(r['altitude_km']) for r in time_data['trajectory']):.2f}-{max(float(r['altitude_km']) for r in time_data['trajectory']):.2f} km`, latitude `{min(float(r['latitude_deg']) for r in time_data['trajectory']):.2f}-{max(float(r['latitude_deg']) for r in time_data['trajectory']):.2f} deg`, and longitude `{min(float(r['longitude_deg']) for r in time_data['trajectory']):.2f}-{max(float(r['longitude_deg']) for r in time_data['trajectory']):.2f} deg`.",
        f"- Broad-window prompt final rate varies from `{min(broad_prompt):.4f}` to `{max(broad_prompt):.4f} cps`.",
        f"- Broad-window delayed Level-1 rate varies from `{min(broad_delayed):.4f}` to `{max(broad_delayed):.4f} cps` because the activation inventory is driven by the time-dependent irradiation profile.",
        f"- Broad-window total final background varies from `{min(broad_total):.4f}` to `{max(broad_total):.4f} cps`.",
        f"- Line-window total final background varies from `{min(line_total):.4f}` to `{max(line_total):.4f} cps`.",
        "",
        "## Claim Control",
        "",
        "- Diffuse SPI bulge/disk flux is aperture-integrated foreground only; it is not emitted as a Cosima focal-spot source.",
        "- The central compact/Sgr A* case is a hypothesis anchored to a SPI model component, not a confirmed source identity.",
        "- V404 is an observed transient annihilation-feature benchmark used for flux/time-scale scanning; no final V404 detectability or steady narrow-line source identity is claimed.",
        "- White-dwarf/classical-nova rows are not carried in the active benchmark outputs.",
        "- The delayed time series uses Level-1 fixed day-15 spatial profiles scaled by total activity; it does not contain new day-by-day RPIP spatial transport.",
        "- Parent-fed decay-chain numerical changes remain inactive without audited branch-ratio tables.",
        "",
        "## Files",
        "",
        "- `literature_anchor_summary.csv`",
        "- `spi_diffuse_detectability.csv`",
        "- `point_source_flux_scan.csv`",
        "- `transient_point_benchmarks.csv`",
        "- `trajectory_profile.csv`",
        "- `background_time_variation.csv`",
        "- `time_dependent_driver_grid.csv`",
        "- `time_dependent_point_source_scan.csv`",
        "- `time_dependent_v404_benchmarks.csv`",
        "- `time_dependent_cumulative_profiles.csv`",
        "- `figures/trajectory_lat_lon_altitude.png`",
        "- `figures/background_time_variation_broad.png`",
        "- `figures/background_time_variation_line.png`",
        "- `figures/point_source_flux_scan.png`",
        "- `figures/time_dependent_background_transmission_drivers.png`",
        "- `figures/time_dependent_point_source_scan.png`",
        "- `figures/time_dependent_cumulative_significance.png`",
        "- `figures/diffuse_exposure_requirement.png`",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_outputs() -> dict[str, Any]:
    required = [
        OUT / "README.md",
        OUT / "literature_anchor_summary.csv",
        OUT / "spi_diffuse_detectability.csv",
        OUT / "point_source_flux_scan.csv",
        OUT / "transient_point_benchmarks.csv",
        OUT / "trajectory_profile.csv",
        OUT / "background_time_variation.csv",
        OUT / "time_dependent_driver_grid.csv",
        OUT / "time_dependent_point_source_scan.csv",
        OUT / "time_dependent_v404_benchmarks.csv",
        OUT / "time_dependent_cumulative_profiles.csv",
        FIG / "trajectory_lat_lon_altitude.png",
        FIG / "background_time_variation_broad.png",
        FIG / "background_time_variation_line.png",
        FIG / "point_source_flux_scan.png",
        FIG / "time_dependent_background_transmission_drivers.png",
        FIG / "time_dependent_point_source_scan.png",
        FIG / "time_dependent_cumulative_significance.png",
        FIG / "diffuse_exposure_requirement.png",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists() or p.stat().st_size == 0]
    diffuse = read_csv(OUT / "spi_diffuse_detectability.csv")
    point = read_csv(OUT / "point_source_flux_scan.csv")
    bg = read_csv(OUT / "background_time_variation.csv")
    transient = read_csv(OUT / "transient_point_benchmarks.csv")
    time_point = read_csv(OUT / "time_dependent_point_source_scan.csv")
    default = [
        r
        for r in diffuse
        if r["case_id"] == "B_default_bulge8deg_plus_disk"
        and r["response_id"] == "parametric_CAM511_normalized"
    ][0]
    v404_has_low_flux = any(
        r.get("spectrum") == "v404_kT30_no_shift"
        and abs(float(r.get("input_flux_ph_cm2_s", "nan")) - 1.0e-5) < 1e-14
        for r in transient
    )
    td_anchor = [
        r for r in time_point
        if r.get("response_id") == "parametric_CAM511_normalized_phase12_primary"
        and abs(float(r.get("input_flux_ph_cm2_s", "nan")) - 8.0e-5) < 1e-14
    ]
    ok = (
        not missing
        and float(default["T3_years"]) > 1.0e4
        and v404_has_low_flux
        and td_anchor
        and float(td_anchor[0]["final_Z_metric_scaled"]) > 0.0
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "missing": missing,
        "default_diffuse_T3_years": float(default["T3_years"]),
        "wd_nova_source_case_status": "excluded_from_active_benchmarks",
        "v404_flux_grid_min_ph_cm2_s": min(float(r["input_flux_ph_cm2_s"]) for r in transient if r.get("case_id") == "C_V404_2015_TRANSIENT_BENCHMARK"),
        "v404_flux_grid_max_ph_cm2_s": max(float(r["input_flux_ph_cm2_s"]) for r in transient if r.get("case_id") == "C_V404_2015_TRANSIENT_BENCHMARK"),
        "time_dependent_anchor_8e5_Z20_metric": float(td_anchor[0]["final_Z_metric_scaled"]) if td_anchor else float("nan"),
        "time_dependent_anchor_8e5_T3_days_avg": float(td_anchor[0]["T3_days_metric_avg_extrapolated"]) if td_anchor else float("nan"),
        "background_rows": len(bg),
        "claim_level": "260516_SOURCE_TIME_UPDATE_WITH_EXPLICIT_LIMITATIONS",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    authority = load_metric_authorities()
    source = build_source_tables(authority)
    time_data = build_time_variation_tables()
    time_dep = build_time_dependent_detectability(source, time_data, authority)
    write_markdown(source, time_data, time_dep, authority)
    summary = {
        "status": "PASS_WITH_EXPLICIT_LIMITATIONS",
        "authority": authority,
        "n_literature_anchors": len(source["anchors"]),
        "n_diffuse_rows": len(source["diffuse_rows"]),
        "n_point_rows": len(source["point_rows"]),
        "n_transient_rows": len(source["v404_rows"]),
        "n_time_dependent_point_rows": len(time_dep["point_time_rows"]),
        "n_time_dependent_v404_rows": len(time_dep["v404_time_rows"]),
        "n_time_dependent_profile_rows": len(time_dep["profile_rows"]),
        "n_trajectory_bins": len(time_data["trajectory"]),
        "n_background_rows": len(time_data["background_rows"]),
        "day15_activity_Bq": time_data["day15_activity_Bq"],
        "delayed_day15_cps": time_data["delayed_day15_cps"],
        "validation": validate_outputs(),
    }
    write_json(OUT / "source_time_update_summary.json", summary)
    print(json.dumps(summary["validation"], indent=2))
    return 0 if summary["validation"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
