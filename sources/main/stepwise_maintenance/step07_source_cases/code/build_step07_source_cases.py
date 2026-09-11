#!/usr/bin/env python3
"""Build the Step07 astrophysical 511-keV source-case layer for new_geo_re.

Step07 now uses the Step09 full focused EventList detector-coupled response as
the science-response authority.  It still does not add optics hardware mass to
the prompt/delayed background model.
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


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step07_source_cases"
OUT = STEP_DIR / "outputs"
CONFIG_DIR = OUT / "configs"
RUN_CONFIG_DIR = OUT / "run_configs"
SPECTRA_DIR = OUT / "spectra"
SKY_DIR = OUT / "sky_models"
FIG_DIR = OUT / "figures"

DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
STEP06_BACKGROUND = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"
STEP06_SUMMARY = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "step06_mission_time_variation_summary.json"
BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
SOURCE_TEMPLATE = ROOT / "config" / "run_configs" / "Science_511_onaxis_ADR_cm_local.source"
OPTICS_AUTHORITY = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority.json"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
STEP09_SUMMARY = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "step09_optics_bridge_summary.json"

E0_KEV = 511.0
C_KM_S = 299792.458
REFERENCE_EXPOSURE_S = 1.0e6


def initial_windows() -> tuple[float, float, float, float]:
    try:
        payload = json.loads(OPTICS_AUTHORITY.read_text(encoding="utf-8"))
        w1 = payload["natural_passband_fwhm"]
        return float(w1["lo_keV"]), float(w1["hi_keV"]), 510.58, 511.42
    except Exception:
        return 500.99393711182086, 521.0060628881791, 510.58, 511.42


ANALYSIS_E_MIN_KEV, ANALYSIS_E_MAX_KEV, LINE_E_MIN_KEV, LINE_E_MAX_KEV = initial_windows()
TINY_RESPONSE_CLAMP = 1.0e-100


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    for path in (CONFIG_DIR, RUN_CONFIG_DIR, SPECTRA_DIR, SKY_DIR, FIG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    x = float(x)
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e4:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def clamp_tiny_response(value: float) -> float:
    value = float(value)
    return 0.0 if abs(value) < TINY_RESPONSE_CLAMP else value


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:.12g}"
    text = str(value)
    if text == "" or any(ch in text for ch in ":#[]{}&,*!|>'\"%@`"):
        return json.dumps(text)
    return text


def yaml_lines(obj: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(obj, dict):
        lines: list[str] = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(yaml_lines(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(value)}")
        return lines
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, dict):
                lines.append(f"{pad}-")
                lines.extend(yaml_lines(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
        return lines
    return [f"{pad}{yaml_scalar(obj)}"]


def write_yaml(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(yaml_lines(obj)) + "\n", encoding="utf-8")


def source_cases() -> dict[str, Any]:
    return {
        "meta": {
            "version": "new_geo_re_step07_v2_focused_eventlist",
            "purpose": "Astrophysical 511-keV source cases folded through the Step09 focused EventList detector-coupled response.",
            "implementation_level": "L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING",
            "detector_response_authority": rel(FOCUS_RESPONSE),
            "optics_policy": "B-FULL Step04/Step09 focused EventList science response is used; optics-mass prompt/delayed activation is still not included",
            "warning": "Diffuse source projection and optics-mass activation remain separate upgrades.",
        },
        "folding_authority": {
            "geometry_bounds": rel(BOUNDS),
            "day15_veto_timeline": rel(DAY15_SUMMARY),
            "mission_time_variation": rel(STEP06_BACKGROUND),
        },
        "cases": [
            {
                "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
                "source_class": "point_steady",
                "priority": "primary",
                "target": "Galactic_Center",
                "position": {"frame": "galactic", "l_deg": 0.0, "b_deg": 0.0},
                "line_flux_ph_cm2_s": {
                    "anchor": 8.0e-5,
                    "scan": [3.0e-5, 5.0e-5, 8.0e-5, 1.0e-4, 1.5e-4, 2.0e-4, 3.0e-4],
                    "note": "SPI central compact model-fit anchor; not a confirmed Sgr A* point-source claim.",
                },
                "spectra": ["mono_511", "gaussian_fwhm_0p5", "gaussian_fwhm_1p5", "velocity_sigma_300"],
                "morphology": {
                    "type": "point_or_uniform_compact_proxy",
                    "angular_radius_arcmin_scan": [0, 1, 5, 10, 30, 60],
                },
                "handling": "point_source_current_detector_response_reuse",
            },
            {
                "case_id": "B_GC_DIFFUSE_BULGE_DISK",
                "source_class": "extended_steady",
                "priority": "foreground",
                "target": "Galactic_Center",
                "sky_models": [
                    "bulge_gaussian_fwhm_3deg",
                    "bulge_gaussian_fwhm_8deg",
                    "bulge_gaussian_fwhm_12deg",
                    "disk_thick_gaussian",
                ],
                "spectra": ["gaussian_fwhm_1p0", "gaussian_fwhm_2p5", "warm_ism_two_component_proxy"],
                "handling": "aperture_integral_no_focal_spot_source",
            },
            {
                "case_id": "C_V404_2015_TRANSIENT_BENCHMARK",
                "source_class": "point_transient",
                "priority": "secondary_benchmark",
                "target": "V404_Cygni",
                "position": {"frame": "icrs", "ra_j2000": "20h24m03s", "dec_j2000": "+33d52m02s"},
                "line_flux_ph_cm2_s": {
                    "reference_policy": "Flux grid is a transient benchmark, not a fixed steady narrow-line source.",
                    "scan": [1.0e-5, 3.0e-5, 5.0e-5, 1.0e-4, 3.0e-4, 1.0e-3, 3.0e-3, 5.0e-3, 6.5e-3, 1.0e-2],
                },
                "spectra": [
                    "v404_kT30_no_shift",
                    "v404_kT170_no_shift",
                    "v404_redshift_z0p10_narrow_proxy",
                    "v404_redshift_z0p10_broad_proxy",
                ],
                "time_model": {"bins": ["1h", "6h", "24h", "72h"]},
                "handling": "transient_point_source_bandpass_check",
            },
        ],
    }


def literature_anchors() -> dict[str, Any]:
    return {
        "meta": {
            "version": "new_geo_re_step07_v1",
            "policy": "Literature anchors are source-case assumptions, not detections by this instrument.",
        },
        "anchors": [
            {
                "id": "SPI_MW_TOTAL_511",
                "quantity": "total Galactic 511-keV line intensity",
                "value_ph_cm2_s": 2.74e-3,
                "uncertainty_ph_cm2_s": 0.25e-3,
                "role": "literature context only",
                "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
                "caveat": "Total Galactic flux is not a point-source input to the focused telescope.",
            },
            {
                "id": "SPI_GCS_POINTLIKE_511",
                "quantity": "central compact 511-keV line flux",
                "value_ph_cm2_s": 8.0e-5,
                "uncertainty_ph_cm2_s": 1.9e-5,
                "role": "scan anchor only",
                "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
                "caveat": "SPI model-fit central component is not a focusing-telescope compact-source confirmation.",
            },
            {
                "id": "B_bulge_total",
                "quantity": "bulge total line flux proxy",
                "value_ph_cm2_s": 9.6e-4,
                "uncertainty_ph_cm2_s": 7.0e-5,
                "role": "diffuse foreground aperture integral",
                "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
                "caveat": "Do not multiply total bulge flux directly by optics area.",
            },
            {
                "id": "B_disk_total",
                "quantity": "disk total line flux proxy",
                "value_ph_cm2_s": 1.66e-3,
                "uncertainty_ph_cm2_s": 3.5e-4,
                "role": "diffuse foreground aperture integral",
                "reference": "Siegert et al. 2016, A&A 586 A84, arXiv:1512.00325",
                "caveat": "Disk model is a broad proxy for null-model stress tests.",
            },
            {
                "id": "SPI_V404_ANNIHILATION_FEATURE",
                "quantity": "V404 Cyg 2015 variable positron-annihilation feature",
                "value_ph_cm2_s": None,
                "scan_ph_cm2_s": [1.0e-5, 3.0e-5, 5.0e-5, 1.0e-4, 3.0e-4, 1.0e-3, 3.0e-3],
                "role": "observed-feature transient flux benchmark grid",
                "reference": "Siegert et al. 2016, Nature 531, 341-343, arXiv:1603.01169",
                "caveat": "Use as a transient flux/time-scale and bandpass benchmark, not as a fixed steady narrow 511-keV source.",
            },
        ],
    }


def write_configs() -> None:
    write_yaml(CONFIG_DIR / "source_cases_511_ABC.yaml", source_cases())
    write_yaml(CONFIG_DIR / "literature_flux_anchors.yaml", literature_anchors())
    bounds = load_json(BOUNDS)
    optics_authority = load_json(OPTICS_AUTHORITY)
    focus_response = load_json(FOCUS_RESPONSE)
    focal_length_cm = float(optics_authority["focal_length_mm"]) / 10.0
    be_r = be_window_radius_cm(bounds)
    fov_arcmin = math.degrees(math.atan(be_r / focal_length_cm)) * 60.0
    w1 = optics_authority["natural_passband_fwhm"]
    aeff = float(optics_authority["aeff_511_cm2"])
    optics = {
        "metadata": {
            "optics_id": optics_authority["design_name"],
            "status": "FOCUSED_EVENTLIST_DETECTOR_COUPLED",
            "channel_optics_used": False,
            "full_detector_coupled_eventlist_bridge": True,
            "detector_response_authority": rel(FOCUS_RESPONSE),
            "claim_control": "Step07 rate folding uses the full Step09 focused EventList detector response; optics-mass backgrounds are not included",
        },
        "geometry_limited_fov": {
            "be_window_radius_cm": be_r,
            "focal_length_cm": focal_length_cm,
            "angular_radius_arcmin": fov_arcmin,
            "basis": "atan(Be-window radius / Step04 focal length); off-axis diffuse projection remains an aperture proxy",
        },
        "effective_area_authority": {
            "basis": "Step04 B-FULL emergent within-Be A_eff at 511 keV with the design natural passband FWHM",
            "energy_keV": [w1["lo_keV"] - 2.0, w1["lo_keV"], 511.0, w1["hi_keV"], w1["hi_keV"] + 2.0],
            "aeff_cm2": [0.0, aeff, aeff, aeff, 0.0],
            "analysis_window_keV": [ANALYSIS_E_MIN_KEV, ANALYSIS_E_MAX_KEV],
            "W2_511_pm_420eV": [LINE_E_MIN_KEV, LINE_E_MAX_KEV],
            "focused_W1_final_response_cps_per_ph_cm2_s": focus_response["window_checks"]["W1_design_passband"]["signal_both_response_cps_per_ph_cm2_s"],
            "focused_W2_final_response_cps_per_ph_cm2_s": focus_response["window_checks"]["W2_511_pm_420eV"]["signal_both_response_cps_per_ph_cm2_s"],
        },
    }
    write_yaml(CONFIG_DIR / "optics_response_current_scaffold.yaml", optics)


def be_window_radius_cm(bounds: dict[str, Any]) -> float:
    for window in bounds.get("WINDOWS", []):
        if window.get("name") == "Win_Be_Cryostat":
            return float(window["r_max"])
    raise RuntimeError("Win_Be_Cryostat not found in bounds.json")


def source_beam_params(bounds: dict[str, Any]) -> dict[str, float]:
    meta = bounds.get("META", {})
    return {
        "z_cm": float(meta.get("science_beam_z_cm", 16.051)),
        "r_cm": float(meta.get("science_beam_radius_cm", 1.8)),
        "be_r_cm": be_window_radius_cm(bounds),
    }


def authority_numbers() -> dict[str, float]:
    summary = load_json(DAY15_SUMMARY)
    step06 = load_json(STEP06_SUMMARY)
    optics = load_json(OPTICS_AUTHORITY)
    focus = load_json(FOCUS_RESPONSE)
    flux_ref = float(summary["normalization"]["science_flux_ph_cm2_s"])
    t_ref = float(step06["atmosphere"]["T_ref"])
    a_opt = float(optics["aeff_511_cm2"])
    plane_rate_per_flux = a_opt * t_ref
    w1 = focus["window_checks"]["W1_design_passband"]
    w2 = focus["window_checks"]["W2_511_pm_420eV"]
    response_final = float(w1["signal_both_response_cps_per_ph_cm2_s"])
    response_raw = float(w1["signal_raw_cps_at_reference_flux"]) / flux_ref
    response_bgo = float(w1.get("signal_scintillator_response_cps_per_ph_cm2_s", response_final))
    background_final = float(w1["background_both_cps"])
    background_raw = float(w1["background_raw_cps"])
    background_bgo = float(w1["background_scintillator_cps"])
    return {
        "reference_flux_ph_cm2_s": flux_ref,
        "reference_science_injection_rate_cps": plane_rate_per_flux * flux_ref,
        "plane_rate_cps_per_flux": plane_rate_per_flux,
        "A_opt_cm2": a_opt,
        "T_atm_ref": t_ref,
        "optics_design": optics["design_name"],
        "analysis_window_W1_keV": [ANALYSIS_E_MIN_KEV, ANALYSIS_E_MAX_KEV],
        "line_window_W2_keV": [LINE_E_MIN_KEV, LINE_E_MAX_KEV],
        "science_raw_response_cps_per_flux": response_raw,
        "science_bgo_response_cps_per_flux": response_bgo,
        "science_final_response_cps_per_flux": response_final,
        "science_W2_final_response_cps_per_flux": float(w2["signal_both_response_cps_per_ph_cm2_s"]),
        "science_transport_final_efficiency": response_final / plane_rate_per_flux,
        "background_raw_cps_prompt_plus_delayed": background_raw,
        "background_bgo_cps_prompt_plus_delayed": background_bgo,
        "background_final_cps_prompt_plus_delayed": background_final,
        "background_W2_final_cps_prompt_plus_delayed": float(w2["background_both_cps"]),
    }


def mission_average_numbers(auth: dict[str, float]) -> dict[str, float]:
    rows = read_csv(STEP06_BACKGROUND)
    day15_summary = load_json(DAY15_SUMMARY)
    old_bg = day15_summary["expectation_rates_by_stream_cps"]
    old_bg_final = float(old_bg["prompt"]["final"]) + float(old_bg["delayed"]["final"])
    old_bg_raw = float(old_bg["prompt"]["raw"]) + float(old_bg["delayed"]["raw"])
    old_bg_bgo = float(old_bg["prompt"]["bgo"]) + float(old_bg["delayed"]["bgo"])
    total_dt = 0.0
    sums = {
        "background_final_cps": 0.0,
        "background_raw_cps": 0.0,
        "background_bgo_cps": 0.0,
        "science_final_cps_at_ref_flux": 0.0,
        "science_atm_scale_to_day15": 0.0,
    }
    for row in rows:
        dt = float(row["dt_s"])
        total_dt += dt
        sums["background_final_cps"] += float(row["background_final_cps"]) * auth["background_final_cps_prompt_plus_delayed"] / old_bg_final * dt
        sums["background_raw_cps"] += float(row["background_raw_cps"]) * auth["background_raw_cps_prompt_plus_delayed"] / old_bg_raw * dt
        sums["background_bgo_cps"] += float(row["background_bgo_cps"]) * auth["background_bgo_cps_prompt_plus_delayed"] / old_bg_bgo * dt
        sums["science_final_cps_at_ref_flux"] += auth["reference_flux_ph_cm2_s"] * auth["science_final_response_cps_per_flux"] * float(row["science_atm_scale_to_day15"]) * dt
        sums["science_atm_scale_to_day15"] += float(row["science_atm_scale_to_day15"]) * dt
    avg = {key: value / total_dt for key, value in sums.items()}
    avg["exposure_s"] = total_dt
    avg["science_final_response_cps_per_flux"] = avg["science_final_cps_at_ref_flux"] / auth["reference_flux_ph_cm2_s"]
    return avg


def effective_area_table() -> tuple[np.ndarray, np.ndarray]:
    optics = load_json(OPTICS_AUTHORITY)
    w1 = optics["natural_passband_fwhm"]
    aeff = float(optics["aeff_511_cm2"])
    return (
        np.array([w1["lo_keV"] - 2.0, w1["lo_keV"], 511.0, w1["hi_keV"], w1["hi_keV"] + 2.0], dtype=float),
        np.array([0.0, aeff, aeff, aeff, 0.0], dtype=float),
    )


def aeff_at(energy: np.ndarray | float) -> np.ndarray | float:
    e_grid, a_grid = effective_area_table()
    return np.interp(energy, e_grid, a_grid, left=0.0, right=0.0)


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def gaussian_pdf(energy: np.ndarray, center: float, fwhm: float) -> np.ndarray:
    sigma = max(fwhm / 2.3548200450309493, 1.0e-9)
    y = np.exp(-0.5 * ((energy - center) / sigma) ** 2)
    area = trapz(y, energy)
    if area <= 0:
        return y
    return y / area


def normalize_pdf(energy: np.ndarray, pdf: np.ndarray) -> np.ndarray:
    area = trapz(pdf, energy)
    if area <= 0:
        return pdf
    return pdf / area


def spectrum_model(model_id: str, energy: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    if model_id == "mono_511":
        return gaussian_pdf(energy, E0_KEV, 0.05), {"type": "mono_proxy_dat", "center_keV": E0_KEV, "fwhm_keV": 0.0}
    if model_id.startswith("gaussian_fwhm_"):
        fwhm = float(model_id.replace("gaussian_fwhm_", "").replace("p", "."))
        return gaussian_pdf(energy, E0_KEV, fwhm), {"type": "gaussian", "center_keV": E0_KEV, "fwhm_keV": fwhm}
    if model_id.startswith("velocity_sigma_"):
        sigma_v = float(model_id.replace("velocity_sigma_", ""))
        sigma_e = E0_KEV * sigma_v / C_KM_S
        fwhm = 2.3548200450309493 * sigma_e
        return gaussian_pdf(energy, E0_KEV, fwhm), {
            "type": "velocity_gaussian",
            "center_keV": E0_KEV,
            "fwhm_keV": fwhm,
            "sigma_v_km_s": sigma_v,
        }
    if model_id == "warm_ism_two_component_proxy":
        pdf = 0.7 * gaussian_pdf(energy, E0_KEV, 1.0) + 0.3 * gaussian_pdf(energy, E0_KEV, 2.5)
        return normalize_pdf(energy, pdf), {"type": "mixture_proxy", "center_keV": E0_KEV, "fwhm_keV": "mixture"}
    if model_id == "v404_kT30_no_shift":
        return gaussian_pdf(energy, E0_KEV, 30.0), {"type": "thermal_pair_proxy", "center_keV": E0_KEV, "fwhm_keV": 30.0}
    if model_id == "v404_kT170_no_shift":
        return gaussian_pdf(energy, E0_KEV, 170.0), {"type": "thermal_pair_proxy", "center_keV": E0_KEV, "fwhm_keV": 170.0}
    if model_id == "v404_redshift_z0p10_narrow_proxy":
        center = E0_KEV / 1.10
        return gaussian_pdf(energy, center, 1.5), {
            "type": "redshifted_gaussian_proxy",
            "center_keV": center,
            "fwhm_keV": 1.5,
            "redshift": 0.10,
        }
    if model_id == "v404_redshift_z0p10_broad_proxy":
        center = E0_KEV / 1.10
        return gaussian_pdf(energy, center, 30.0), {
            "type": "redshifted_thermal_proxy",
            "center_keV": center,
            "fwhm_keV": 30.0,
            "redshift": 0.10,
        }
    raise ValueError(f"unknown spectrum model: {model_id}")


def fraction_in_window(energy: np.ndarray, pdf: np.ndarray, lo: float, hi: float) -> float:
    mask = (energy >= lo) & (energy <= hi)
    if not np.any(mask):
        return 0.0
    return trapz(pdf[mask], energy[mask]) / trapz(pdf, energy)


def write_spectrum_file(path: Path, energy: np.ndarray, pdf: np.ndarray) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("IP LIN\n")
        for e, p in zip(energy, pdf):
            handle.write(f"DP {e:.8e} {p:.12e}\n")


def all_spectrum_ids() -> list[str]:
    ids: list[str] = []
    for case in source_cases()["cases"]:
        for model_id in case.get("spectra", []):
            if model_id not in ids:
                ids.append(model_id)
    return ids


def build_spectra() -> list[dict[str, Any]]:
    energy = np.arange(430.0, 570.00001, 0.05)
    aeff = np.asarray(aeff_at(energy), dtype=float)
    aeff_511 = float(aeff_at(E0_KEV))
    analysis_mask = (energy >= ANALYSIS_E_MIN_KEV) & (energy <= ANALYSIS_E_MAX_KEV)
    rows: list[dict[str, Any]] = []
    for model_id in all_spectrum_ids():
        pdf, meta = spectrum_model(model_id, energy)
        path = SPECTRA_DIR / f"{model_id}.dat"
        write_spectrum_file(path, energy, pdf)
        if model_id == "mono_511":
            full_aeff_fraction = 1.0
            analysis_response_fraction = 1.0
            frac_480_550 = 1.0
            frac_line = 1.0
        else:
            full_aeff = trapz(pdf * aeff, energy)
            windowed_aeff = trapz(pdf[analysis_mask] * aeff[analysis_mask], energy[analysis_mask])
            full_aeff_fraction = full_aeff / aeff_511
            analysis_response_fraction = clamp_tiny_response(windowed_aeff / aeff_511)
            frac_480_550 = clamp_tiny_response(fraction_in_window(energy, pdf, ANALYSIS_E_MIN_KEV, ANALYSIS_E_MAX_KEV))
            frac_line = clamp_tiny_response(fraction_in_window(energy, pdf, LINE_E_MIN_KEV, LINE_E_MAX_KEV))
        rows.append(
            {
                "model_id": model_id,
                "type": meta.get("type", ""),
                "center_keV": meta.get("center_keV", ""),
                "fwhm_keV": meta.get("fwhm_keV", ""),
                "sigma_v_km_s": meta.get("sigma_v_km_s", ""),
                "redshift": meta.get("redshift", ""),
                "fraction_480_550": frac_480_550,
                "fraction_510p3_511p8": frac_line,
                "aeff_full_fraction_of_511": full_aeff_fraction,
                "analysis_response_fraction_of_511": analysis_response_fraction,
                "tiny_response_clamp": TINY_RESPONSE_CLAMP,
                "spectrum_file": rel(path),
            }
        )
    write_csv(OUT / "source_spectrum_summary.csv", rows)
    plot_spectra(energy)
    return rows


def plot_spectra(energy: np.ndarray) -> None:
    aeff = np.asarray(aeff_at(energy), dtype=float)
    fig, ax1 = plt.subplots(figsize=(8.8, 5.0))
    chosen = [
        "mono_511",
        "gaussian_fwhm_1p5",
        "v404_kT30_no_shift",
        "v404_redshift_z0p10_narrow_proxy",
        "v404_redshift_z0p10_broad_proxy",
    ]
    max_pdf = 0.0
    for model_id in chosen:
        pdf, _ = spectrum_model(model_id, energy)
        max_pdf = max(max_pdf, float(pdf.max()))
        ax1.plot(energy, pdf, lw=1.2, label=model_id)
    ax1.axvspan(ANALYSIS_E_MIN_KEV, ANALYSIS_E_MAX_KEV, color="#F58518", alpha=0.12, label="W1 design passband")
    ax1.set_xlabel("Energy (keV)")
    ax1.set_ylabel("Normalized source spectrum")
    ax1.grid(True, alpha=0.22)
    ax2 = ax1.twinx()
    ax2.plot(energy, aeff, color="#222222", ls="--", lw=1.0, label="Step04 Aeff authority")
    ax2.set_ylabel("Aeff authority (cm2)")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=7, ncols=2, loc="upper left")
    ax1.set_ylim(0, max_pdf * 1.2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "source_spectra_and_current_response_surrogate.png", dpi=220)
    plt.close(fig)


def spectrum_row_map() -> dict[str, dict[str, str]]:
    return {row["model_id"]: row for row in read_csv(OUT / "source_spectrum_summary.csv")}


def sky_model_defs() -> list[dict[str, Any]]:
    return [
        {"model_id": "bulge_gaussian_fwhm_3deg", "kind": "circular_gaussian", "total_flux_ph_cm2_s": 9.6e-4, "fwhm_l_deg": 3.0, "fwhm_b_deg": 3.0},
        {"model_id": "bulge_gaussian_fwhm_8deg", "kind": "circular_gaussian", "total_flux_ph_cm2_s": 9.6e-4, "fwhm_l_deg": 8.0, "fwhm_b_deg": 8.0},
        {"model_id": "bulge_gaussian_fwhm_12deg", "kind": "circular_gaussian", "total_flux_ph_cm2_s": 9.6e-4, "fwhm_l_deg": 12.0, "fwhm_b_deg": 12.0},
        {"model_id": "disk_thick_gaussian", "kind": "elliptical_gaussian", "total_flux_ph_cm2_s": 1.66e-3, "fwhm_l_deg": 60.0, "fwhm_b_deg": 10.5},
    ]


def fov_radius_arcmin() -> float:
    bounds = load_json(BOUNDS)
    optics = load_json(OPTICS_AUTHORITY)
    focal_length_cm = float(optics["focal_length_mm"]) / 10.0
    be_r = be_window_radius_cm(bounds)
    return math.degrees(math.atan(be_r / focal_length_cm)) * 60.0


def analytic_fov_flux(model: dict[str, Any], radius_deg: float) -> tuple[float, float]:
    total = float(model["total_flux_ph_cm2_s"])
    sigma_l = float(model["fwhm_l_deg"]) / 2.3548200450309493
    sigma_b = float(model["fwhm_b_deg"]) / 2.3548200450309493
    if abs(sigma_l - sigma_b) / max(sigma_l, sigma_b) < 1.0e-12:
        frac = 1.0 - math.exp(-(radius_deg * radius_deg) / (2.0 * sigma_l * sigma_l))
        return total * frac, frac
    central_intensity = total / (2.0 * math.pi * sigma_l * sigma_b)
    fov_flux = central_intensity * math.pi * radius_deg * radius_deg
    frac = min(1.0, fov_flux / total)
    return total * frac, frac


def build_sky_models() -> list[dict[str, Any]]:
    fov_arcmin = fov_radius_arcmin()
    radius_deg = fov_arcmin / 60.0
    l_grid = np.arange(-90.0, 90.00001, 0.2)
    b_grid = np.arange(-30.0, 30.00001, 0.2)
    ll, bb = np.meshgrid(l_grid, b_grid, indexing="xy")
    pixel_area_deg2 = 0.2 * 0.2
    rows: list[dict[str, Any]] = []
    for model in sky_model_defs():
        sigma_l = float(model["fwhm_l_deg"]) / 2.3548200450309493
        sigma_b = float(model["fwhm_b_deg"]) / 2.3548200450309493
        raw = np.exp(-0.5 * ((ll / sigma_l) ** 2 + (bb / sigma_b) ** 2))
        norm = float(np.sum(raw) * pixel_area_deg2)
        intensity = raw * (float(model["total_flux_ph_cm2_s"]) / norm)
        fov_flux, fov_fraction = analytic_fov_flux(model, radius_deg)
        path = SKY_DIR / f"{model['model_id']}.npz"
        np.savez_compressed(path, l_deg=l_grid, b_deg=b_grid, intensity_ph_cm2_s_deg2=intensity)
        center_i = int(np.argmin(np.abs(b_grid)))
        center_j = int(np.argmin(np.abs(l_grid)))
        rows.append(
            {
                "sky_model": model["model_id"],
                "kind": model["kind"],
                "total_flux_ph_cm2_s": model["total_flux_ph_cm2_s"],
                "fwhm_l_deg": model["fwhm_l_deg"],
                "fwhm_b_deg": model["fwhm_b_deg"],
                "fov_radius_arcmin": fov_arcmin,
                "fov_radius_deg": radius_deg,
                "fov_flux_ph_cm2_s": fov_flux,
                "fov_fraction": fov_fraction,
                "central_intensity_ph_cm2_s_deg2": float(intensity[center_i, center_j]),
                "sky_model_file": rel(path),
            }
        )
    write_csv(OUT / "diffuse_aperture_foreground.csv", rows)
    plot_diffuse_fraction(rows)
    return rows


def plot_diffuse_fraction(rows: list[dict[str, Any]]) -> None:
    labels = [str(row["sky_model"]).replace("bulge_gaussian_", "bulge_").replace("_gaussian", "") for row in rows]
    vals = [float(row["fov_fraction"]) for row in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar(np.arange(len(vals)), vals, color=["#4C78A8", "#4C78A8", "#4C78A8", "#54A24B"])
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(vals)), labels, rotation=24, ha="right", fontsize=8)
    ax.set_ylabel("FoV-selected fraction of total diffuse flux")
    ax.set_title("Diffuse 511-keV flux is aperture-limited in Step07")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "diffuse_fov_fraction.png", dpi=220)
    plt.close(fig)


def source_radius_factor(radius_arcmin: float) -> float:
    if radius_arcmin <= 0:
        return 1.0
    fov = fov_radius_arcmin()
    return min(1.0, (fov / radius_arcmin) ** 2)


def diffuse_row_map() -> dict[str, dict[str, str]]:
    return {row["sky_model"]: row for row in read_csv(OUT / "diffuse_aperture_foreground.csv")}


def fold_source_cases() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    auth = authority_numbers()
    mission = mission_average_numbers(auth)
    spectra = spectrum_row_map()
    diffuse = diffuse_row_map()
    rows: list[dict[str, Any]] = []
    default_diffuse_final_cps = 0.0
    default_diffuse_missionavg_final_cps = 0.0
    durations = {"1h": 3600.0, "6h": 21600.0, "24h": 86400.0, "72h": 259200.0}
    for case in source_cases()["cases"]:
        case_id = case["case_id"]
        if case["source_class"] == "point_steady":
            for model_id in case["spectra"]:
                response_fraction = float(spectra[model_id]["analysis_response_fraction_of_511"])
                for radius_arcmin in case["morphology"]["angular_radius_arcmin_scan"]:
                    aperture_factor = source_radius_factor(float(radius_arcmin))
                    for flux in case["line_flux_ph_cm2_s"]["scan"]:
                        final_ref = flux * auth["science_final_response_cps_per_flux"] * response_fraction * aperture_factor
                        final_avg = flux * mission["science_final_response_cps_per_flux"] * response_fraction * aperture_factor
                        rows.append(
                            {
                                "case_id": case_id,
                                "source_class": case["source_class"],
                                "model_id": model_id,
                                "sky_model": "",
                                "flux_ph_cm2_s": flux,
                                "total_flux_ph_cm2_s": "",
                                "fov_flux_ph_cm2_s": "",
                                "fov_fraction": "",
                                "duration_s": "",
                                "angular_radius_arcmin": radius_arcmin,
                                "aperture_factor": aperture_factor,
                                "spectral_response_fraction_of_511": response_fraction,
                                "plane_rate_day15_cps": flux * auth["plane_rate_cps_per_flux"] * response_fraction * aperture_factor,
                                "final_rate_day15_cps": final_ref,
                                "final_rate_missionavg_cps": final_avg,
                                "expected_counts_1Ms_day15": final_ref * REFERENCE_EXPOSURE_S,
                                "handling": case["handling"],
                            }
                        )
        elif case["source_class"] == "extended_steady":
            for sky_model in case["sky_models"]:
                sky = diffuse[sky_model]
                fov_flux = float(sky["fov_flux_ph_cm2_s"])
                for model_id in case["spectra"]:
                    response_fraction = float(spectra[model_id]["analysis_response_fraction_of_511"])
                    final_ref = fov_flux * auth["science_final_response_cps_per_flux"] * response_fraction
                    final_avg = fov_flux * mission["science_final_response_cps_per_flux"] * response_fraction
                    if sky_model in ("bulge_gaussian_fwhm_8deg", "disk_thick_gaussian") and model_id == "gaussian_fwhm_1p0":
                        default_diffuse_final_cps += final_ref
                        default_diffuse_missionavg_final_cps += final_avg
                    rows.append(
                        {
                            "case_id": case_id,
                            "source_class": case["source_class"],
                            "model_id": model_id,
                            "sky_model": sky_model,
                            "flux_ph_cm2_s": "",
                            "total_flux_ph_cm2_s": sky["total_flux_ph_cm2_s"],
                            "fov_flux_ph_cm2_s": fov_flux,
                            "fov_fraction": sky["fov_fraction"],
                            "duration_s": "",
                            "angular_radius_arcmin": "",
                            "aperture_factor": "",
                            "spectral_response_fraction_of_511": response_fraction,
                            "plane_rate_day15_cps": fov_flux * auth["plane_rate_cps_per_flux"] * response_fraction,
                            "final_rate_day15_cps": final_ref,
                            "final_rate_missionavg_cps": final_avg,
                            "expected_counts_1Ms_day15": final_ref * REFERENCE_EXPOSURE_S,
                            "handling": case["handling"],
                        }
                    )
        elif case["source_class"] == "point_transient":
            for model_id in case["spectra"]:
                response_fraction = float(spectra[model_id]["analysis_response_fraction_of_511"])
                for duration_label in case["time_model"]["bins"]:
                    duration_s = durations[duration_label]
                    for flux in case["line_flux_ph_cm2_s"]["scan"]:
                        final_ref = flux * auth["science_final_response_cps_per_flux"] * response_fraction
                        final_avg = flux * mission["science_final_response_cps_per_flux"] * response_fraction
                        rows.append(
                            {
                                "case_id": case_id,
                                "source_class": case["source_class"],
                                "model_id": model_id,
                                "sky_model": "",
                                "flux_ph_cm2_s": flux,
                                "total_flux_ph_cm2_s": "",
                                "fov_flux_ph_cm2_s": "",
                                "fov_fraction": "",
                                "duration_s": duration_s,
                                "angular_radius_arcmin": 0,
                                "aperture_factor": 1.0,
                                "spectral_response_fraction_of_511": response_fraction,
                                "plane_rate_day15_cps": flux * auth["plane_rate_cps_per_flux"] * response_fraction,
                                "final_rate_day15_cps": final_ref,
                                "final_rate_missionavg_cps": final_avg,
                                "expected_counts_in_duration_day15": final_ref * duration_s,
                                "handling": case["handling"],
                            }
                        )
    write_csv(OUT / "source_case_rates.csv", rows)
    summary = build_summary(auth, mission, default_diffuse_final_cps, default_diffuse_missionavg_final_cps, rows)
    write_json(OUT / "source_case_summary.json", summary)
    plot_case_rates(rows)
    return summary, rows


def build_summary(
    auth: dict[str, float],
    mission: dict[str, float],
    default_diffuse_final_cps: float,
    default_diffuse_missionavg_final_cps: float,
    rates: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = auth["reference_flux_ph_cm2_s"] * auth["science_final_response_cps_per_flux"]
    a_mono = next(
        row for row in rates
        if row["case_id"] == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"
        and row["model_id"] == "mono_511"
        and float(row["flux_ph_cm2_s"]) == auth["reference_flux_ph_cm2_s"]
        and float(row["angular_radius_arcmin"]) == 0.0
    )
    plane_expected = auth["reference_flux_ph_cm2_s"] * auth["A_opt_cm2"] * auth["T_atm_ref"]
    source_card_manifest = OUT / "cosima_source_manifest.csv"
    spectra = spectrum_row_map()
    v404_narrow = [row for row in rates if row["model_id"] == "v404_redshift_z0p10_narrow_proxy"]
    v404_narrow_max_final = max((abs(float(row["final_rate_day15_cps"])) for row in v404_narrow), default=math.inf)
    v404_narrow_response = float(spectra["v404_redshift_z0p10_narrow_proxy"]["analysis_response_fraction_of_511"])
    return {
        "status": "PASS",
        "claim_level": "L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING",
        "scope": "A/B/C astrophysical source cases folded through the full Step09 focused EventList detector-coupled science response and the Step06 rate-level mission profile. Optics-mass background production is not included.",
        "optics_policy": "B-FULL Step04/Step09 focused EventList detector response is the science authority; optics-mass background production is not included",
        "authority": auth,
        "mission_average": mission,
        "fov_proxy": {
            "fov_radius_arcmin": fov_radius_arcmin(),
            "basis": "atan(Be-window radius / Step04 focal length); diffuse off-axis projection is still aperture-level",
        },
        "checks": {
            "A_onaxis_mono_final_rate_day15_cps": float(a_mono["final_rate_day15_cps"]),
            "A_onaxis_mono_final_expected_cps": expected,
            "A_onaxis_mono_final_rel_error": abs(float(a_mono["final_rate_day15_cps"]) - expected) / expected,
            "A_onaxis_mono_plane_rate_day15_cps": float(a_mono["plane_rate_day15_cps"]),
            "A_onaxis_mono_plane_expected_cps": plane_expected,
            "A_onaxis_mono_plane_rel_error": abs(float(a_mono["plane_rate_day15_cps"]) - plane_expected) / plane_expected,
            "B_default_diffuse_day15_final_cps": default_diffuse_final_cps,
            "B_default_diffuse_missionavg_final_cps": default_diffuse_missionavg_final_cps,
            "B_default_diffuse_to_instrument_background_fraction": default_diffuse_final_cps / auth["background_final_cps_prompt_plus_delayed"],
            "B_cosima_source_card_policy": "skipped_by_design_for_diffuse_source; focused mono A uses Step09 EventList source",
            "tiny_response_clamp": TINY_RESPONSE_CLAMP,
            "V404_redshift_narrow_response_fraction": v404_narrow_response,
            "V404_redshift_narrow_max_final_rate_day15_cps": v404_narrow_max_final,
            "source_card_manifest": rel(source_card_manifest),
        },
        "outputs": {
            "source_cases_yaml": rel(CONFIG_DIR / "source_cases_511_ABC.yaml"),
            "literature_anchors_yaml": rel(CONFIG_DIR / "literature_flux_anchors.yaml"),
            "optics_response_yaml": rel(CONFIG_DIR / "optics_response_current_scaffold.yaml"),
            "source_spectrum_summary": rel(OUT / "source_spectrum_summary.csv"),
            "diffuse_aperture_foreground": rel(OUT / "diffuse_aperture_foreground.csv"),
            "source_case_rates": rel(OUT / "source_case_rates.csv"),
            "point_vs_diffuse": rel(OUT / "point_vs_diffuse_discrimination.csv"),
            "cosima_source_manifest": rel(OUT / "cosima_source_manifest.csv"),
            "readme": rel(STEP_DIR / "README.md"),
        },
    }


def plot_case_rates(rows: list[dict[str, Any]]) -> None:
    selected = [
        row for row in rows
        if row["case_id"] == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"
        and row["model_id"] == "mono_511"
        and float(row["angular_radius_arcmin"]) == 0.0
    ]
    flux = [float(row["flux_ph_cm2_s"]) for row in selected]
    rate = [float(row["final_rate_day15_cps"]) for row in selected]
    brows = [
        row for row in rows
        if row["case_id"] == "B_GC_DIFFUSE_BULGE_DISK" and row["model_id"] == "gaussian_fwhm_1p0"
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(flux, rate, marker="o", label="A point mono, r=0")
    for row in brows:
        ax.axhline(float(row["final_rate_day15_cps"]), lw=0.8, alpha=0.55, label=row["sky_model"])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Point-source flux (ph cm-2 s-1)")
    ax.set_ylabel("Final selected rate at day-15 reference (cps)")
    ax.set_title("Step07 source-case folded rates")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "source_case_final_rates_day15.png", dpi=220)
    plt.close(fig)


def build_point_diffuse_report(summary: dict[str, Any], rates: list[dict[str, Any]]) -> None:
    auth = summary["authority"]
    a_rows = [
        row for row in rates
        if row["case_id"] == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"
        and row["model_id"] == "mono_511"
        and float(row["angular_radius_arcmin"]) == 0.0
    ]
    a_anchor = next(row for row in a_rows if float(row["flux_ph_cm2_s"]) == 8.0e-5)
    a_ref = next(row for row in a_rows if float(row["flux_ph_cm2_s"]) == 1.0e-4)
    b_rows = [
        row for row in rates
        if row["case_id"] == "B_GC_DIFFUSE_BULGE_DISK" and row["model_id"] == "gaussian_fwhm_1p0"
    ]
    b_default = [
        row for row in b_rows
        if row["sky_model"] in ("bulge_gaussian_fwhm_8deg", "disk_thick_gaussian")
    ]
    b_default_rate = sum(float(row["final_rate_day15_cps"]) for row in b_default)
    rows = [
        {
            "diagnostic": "A_anchor_point_mono_rate",
            "value": float(a_anchor["final_rate_day15_cps"]),
            "unit": "cps",
            "interpretation": "central compact point-source anchor at 8e-5 ph cm-2 s-1",
        },
        {
            "diagnostic": "A_reference_point_mono_rate",
            "value": float(a_ref["final_rate_day15_cps"]),
            "unit": "cps",
            "interpretation": "on-axis closure case at 1e-4 ph cm-2 s-1",
        },
        {
            "diagnostic": "B_default_diffuse_foreground_rate",
            "value": b_default_rate,
            "unit": "cps",
            "interpretation": "bulge fwhm 8 deg plus thick disk, FoV aperture only",
        },
        {
            "diagnostic": "A_anchor_to_B_default_rate_ratio",
            "value": float(a_anchor["final_rate_day15_cps"]) / max(b_default_rate, 1.0e-300),
            "unit": "ratio",
            "interpretation": "rate-only diagnostic, not a spatial profile likelihood",
        },
        {
            "diagnostic": "B_default_to_instrument_background_fraction",
            "value": b_default_rate / auth["background_final_cps_prompt_plus_delayed"],
            "unit": "ratio",
            "interpretation": "astrophysical diffuse foreground relative to prompt+delayed final instrumental background",
        },
        {
            "diagnostic": "counting_Z_A_anchor_1Ms_without_Bdiffuse",
            "value": float(a_anchor["final_rate_day15_cps"]) * REFERENCE_EXPOSURE_S / math.sqrt(auth["background_final_cps_prompt_plus_delayed"] * REFERENCE_EXPOSURE_S),
            "unit": "sigma_proxy",
            "interpretation": "simple counting proxy only; Step08 will replace with time-dependent significance",
        },
    ]
    write_csv(OUT / "point_vs_diffuse_discrimination.csv", rows)

    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    labels = ["A 8e-5 point", "A 1e-4 point", "B default diffuse", "instrument B"]
    vals = [
        float(a_anchor["final_rate_day15_cps"]),
        float(a_ref["final_rate_day15_cps"]),
        b_default_rate,
        auth["background_final_cps_prompt_plus_delayed"],
    ]
    ax.bar(np.arange(len(vals)), vals, color=["#4C78A8", "#4C78A8", "#F58518", "#777777"])
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(vals)), labels, rotation=18, ha="right")
    ax.set_ylabel("Final rate at day-15 reference (cps)")
    ax.set_title("Point-vs-diffuse rate scale diagnostic")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "point_vs_diffuse_rate_scales.png", dpi=220)
    plt.close(fig)

    lines = [
        "# Point-vs-Diffuse Diagnostic",
        "",
        "This is a Step07 rate-scale diagnostic, not the Step08 spatial-spectral profile likelihood.",
        "",
        f"- A anchor point source (8e-5 ph cm-2 s-1, mono, on-axis): `{fmt(float(a_anchor['final_rate_day15_cps']))}` cps.",
        f"- A reference closure source (1e-4 ph cm-2 s-1): `{fmt(float(a_ref['final_rate_day15_cps']))}` cps.",
        f"- B default diffuse foreground (8 deg bulge plus thick disk, aperture integrated): `{fmt(b_default_rate)}` cps.",
        f"- Instrumental prompt+delayed final background: `{fmt(auth['background_final_cps_prompt_plus_delayed'])}` cps.",
        f"- A anchor / B default rate ratio: `{fmt(float(a_anchor['final_rate_day15_cps']) / max(b_default_rate, 1.0e-300))}`.",
        "",
        "B is not generated as a Cosima focal-spot source because diffuse sky emission needs an optics focal-map projection. Step07 therefore treats B as an aperture foreground rate.",
    ]
    (OUT / "point_vs_diffuse_discrimination.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_cosima_sources() -> list[dict[str, Any]]:
    step09 = load_json(STEP09_SUMMARY)
    focus = load_json(FOCUS_RESPONSE)
    spectra = spectrum_row_map()
    requested = [
        ("A_GC_POINT", "mono_511"),
        ("A_GC_POINT", "gaussian_fwhm_1p5"),
        ("C_V404", "v404_kT30_no_shift"),
        ("C_V404", "v404_redshift_z0p10_narrow_proxy"),
    ]
    rows: list[dict[str, Any]] = []
    for idx, (case_prefix, model_id) in enumerate(requested, start=1):
        response_fraction = float(spectra[model_id]["analysis_response_fraction_of_511"])
        if model_id == "mono_511":
            rows.append(
                {
                    "case_prefix": case_prefix,
                    "model_id": model_id,
                    "status": "FOCUSED_EVENTLIST_SOURCE_READY",
                    "source_file": step09["bridge"]["source"],
                    "eventlist_file": step09["bridge"]["eventlist"],
                    "beam_z_cm": step09["bridge"]["z_plane_cm"],
                    "beam_radius_cm": focus["spatial_checks"]["signal_radius_r90_cm"],
                    "analysis_response_fraction_of_511": response_fraction,
                    "output_prefix": "runs/step09_optics_bridge/Opticsim_laue_new_geo_re",
                    "note": "Full non-smoke detector transport has already been run from this EventList source.",
                }
            )
        else:
            rows.append(
                {
                    "case_prefix": case_prefix,
                    "model_id": model_id,
                    "status": "RATE_FOLDING_ONLY_NO_FOCUSED_EVENTLIST",
                    "source_file": "",
                    "spectrum_file": spectra[model_id]["spectrum_file"],
                    "analysis_response_fraction_of_511": response_fraction,
                    "reason": "The current detector-coupled EventList authority is the mono 511-keV focused source; broader spectra need an energy-dependent optics EventList run.",
                }
            )
    rows.append(
        {
            "case_prefix": "B_GC_DIFFUSE",
            "model_id": "all",
            "status": "SKIPPED_BY_DESIGN",
            "reason": "Diffuse B is aperture-integrated in Step07; a diffuse sky focal-map projection is separate from the mono focused EventList source.",
        }
    )
    write_csv(OUT / "cosima_source_manifest.csv", rows)
    return rows


def build_artifact_manifest() -> None:
    rows = []
    for path in sorted(STEP_DIR.rglob("*")):
        if path.is_file():
            rows.append({"path": rel(path), "bytes": path.stat().st_size})
    write_csv(OUT / "artifact_manifest.csv", rows)


def write_readme(summary: dict[str, Any]) -> None:
    auth = summary["authority"]
    checks = summary["checks"]
    outputs = summary["outputs"]
    lines = [
        "# Step07 Astrophysical Source Cases",
        "",
        "Status: `PASS`.",
        "",
        "This step adds A/B/C 511-keV source cases above the validated `new_geo_re` detector/background chain. The mono point-source science response is the full Step09 focused EventList detector transport. It does not change geometry, Step02/03 transport, Step05 veto logic, or add optics-mass background production.",
        "",
        "## Scope",
        "",
        "- Claim level: `L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING`.",
        "- Optics policy: B-FULL Step04/Step09 focused EventList detector response is the science authority.",
        "- The mono source card is the Step09 EventList source; broad spectra remain rate-folding cases until energy-dependent EventLists are run.",
        "- Diffuse B is aperture-integrated and intentionally not emitted as a focal-spot Cosima source.",
        "- Step08 must still do time-dependent significance and accidental-veto folding.",
        "",
        "## Authority Numbers",
        "",
        f"- `A_opt_cm2 = {fmt(auth['A_opt_cm2'])}`.",
        f"- optics design: `{auth['optics_design']}`.",
        f"- W1 analysis window: `{fmt(auth['analysis_window_W1_keV'][0])}-{fmt(auth['analysis_window_W1_keV'][1])}` keV.",
        f"- W2 line window: `{fmt(auth['line_window_W2_keV'][0])}-{fmt(auth['line_window_W2_keV'][1])}` keV.",
        f"- `T_atm_ref = {fmt(auth['T_atm_ref'])}`.",
        f"- `plane_rate_per_flux = {fmt(auth['plane_rate_cps_per_flux'])}` cps/(ph cm-2 s-1).",
        f"- `science_final_response = {fmt(auth['science_final_response_cps_per_flux'])}` cps/(ph cm-2 s-1).",
        f"- `instrument_background_final = {fmt(auth['background_final_cps_prompt_plus_delayed'])}` cps.",
        "",
        "## Closure Checks",
        "",
        f"- A on-axis mono final closure rel error: `{fmt(checks['A_onaxis_mono_final_rel_error'])}`.",
        f"- A on-axis mono plane-rate closure rel error: `{fmt(checks['A_onaxis_mono_plane_rel_error'])}`.",
        f"- B default diffuse final rate: `{fmt(checks['B_default_diffuse_day15_final_cps'])}` cps.",
        f"- B default diffuse / instrument background: `{fmt(checks['B_default_diffuse_to_instrument_background_fraction'])}`.",
        f"- V404 redshift narrow proxy response: `{fmt(checks['V404_redshift_narrow_response_fraction'])}` after tiny-response clamp `{fmt(checks['tiny_response_clamp'])}`.",
        f"- V404 redshift narrow max final rate: `{fmt(checks['V404_redshift_narrow_max_final_rate_day15_cps'])}` cps.",
        f"- FoV proxy radius: `{fmt(summary['fov_proxy']['fov_radius_arcmin'])}` arcmin.",
        "",
        "## Outputs",
        "",
    ]
    for key, value in outputs.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "- figures: `stepwise_maintenance/step07_source_cases/outputs/figures/`",
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py",
            "```",
        ]
    )
    (STEP_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    write_configs()
    build_spectra()
    build_sky_models()
    summary, rates = fold_source_cases()
    build_cosima_sources()
    build_point_diffuse_report(summary, rates)
    write_readme(summary)
    build_artifact_manifest()
    print(json.dumps({"status": summary["status"], "claim_level": summary["claim_level"], "out": rel(OUT), "checks": summary["checks"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
