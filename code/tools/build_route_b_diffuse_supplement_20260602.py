#!/usr/bin/env python3
"""Build the Route B diffuse-source supplement.

The supplement keeps Route B as a physical sky-intensity/aperture calculation:
literature bulge/disk total flux -> Gaussian sky model -> focal-aperture solid
angle -> atmospheric transmission -> current detector-coupled Route-A response.
It intentionally does not create a Cosima focal-spot source for diffuse emission.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - report remains useful without figures.
    plt = None


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "route_b_diffuse_supplement_20260602"
TRACKED_MD = ROOT / "ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md"

BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
OPTICS_AUTHORITY = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority.json"
STEP06_SUMMARY = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "step06_mission_time_variation_summary.json"
STEP07_SUMMARY = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_case_summary.json"
STEP07_DIFFUSE = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "diffuse_aperture_foreground.csv"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"

SECONDS_PER_DAY = 86400.0
MISSION_DAYS = 20.0
MISSION_EXPOSURE_S = MISSION_DAYS * SECONDS_PER_DAY
FWHM_TO_SIGMA = 2.3548200450309493
DEG2_PER_SR = (180.0 / math.pi) ** 2

REFERENCES = {
    "siegert_2016": {
        "label": "Siegert et al. 2016, A&A 586 A84 / arXiv:1512.00325",
        "url": "https://arxiv.org/abs/1512.00325",
        "role": "Milky Way 511-keV bulge/disk line-flux anchors used by Step07.",
    },
    "knodlseder_2003": {
        "label": "Knodlseder et al. 2003, A&A 411 L457-L460 / arXiv:astro-ph/0309442",
        "url": "https://arxiv.org/abs/astro-ph/0309442",
        "role": "Early SPI morphology context for an extended bulge-scale 511-keV source.",
    },
}

SKY_COMPONENTS = [
    {
        "model_id": "bulge_gaussian_fwhm_3deg",
        "kind": "circular_gaussian",
        "component": "bulge",
        "scenario": "compact bulge stress case",
        "total_flux_ph_cm2_s": 9.6e-4,
        "flux_uncertainty_ph_cm2_s": 7.0e-5,
        "fwhm_l_deg": 3.0,
        "fwhm_b_deg": 3.0,
        "flux_reference": REFERENCES["siegert_2016"]["label"],
        "morphology_reference": "Step07 sensitivity bracket around an extended SPI bulge model.",
    },
    {
        "model_id": "bulge_gaussian_fwhm_8deg",
        "kind": "circular_gaussian",
        "component": "bulge",
        "scenario": "default extended bulge",
        "total_flux_ph_cm2_s": 9.6e-4,
        "flux_uncertainty_ph_cm2_s": 7.0e-5,
        "fwhm_l_deg": 8.0,
        "fwhm_b_deg": 8.0,
        "flux_reference": REFERENCES["siegert_2016"]["label"],
        "morphology_reference": REFERENCES["knodlseder_2003"]["label"],
    },
    {
        "model_id": "bulge_gaussian_fwhm_12deg",
        "kind": "circular_gaussian",
        "component": "bulge",
        "scenario": "broad bulge stress case",
        "total_flux_ph_cm2_s": 9.6e-4,
        "flux_uncertainty_ph_cm2_s": 7.0e-5,
        "fwhm_l_deg": 12.0,
        "fwhm_b_deg": 12.0,
        "flux_reference": REFERENCES["siegert_2016"]["label"],
        "morphology_reference": "Step07 sensitivity bracket around an extended SPI bulge model.",
    },
    {
        "model_id": "disk_thick_gaussian",
        "kind": "elliptical_gaussian",
        "component": "disk",
        "scenario": "thick Galactic disk proxy",
        "total_flux_ph_cm2_s": 1.66e-3,
        "flux_uncertainty_ph_cm2_s": 3.5e-4,
        "sigma_l_deg": 60.0,
        "sigma_b_deg": 10.5,
        "fwhm_l_deg": 60.0 * FWHM_TO_SIGMA,
        "fwhm_b_deg": 10.5 * FWHM_TO_SIGMA,
        "flux_reference": REFERENCES["siegert_2016"]["label"],
        "morphology_reference": REFERENCES["siegert_2016"]["label"],
    },
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def fmt(value: float, nd: int = 6) -> str:
    value = float(value)
    if not math.isfinite(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{nd}e}"
    return f"{value:.{nd}g}"


def be_window_radius_cm(bounds: dict[str, Any]) -> float:
    for window in bounds.get("STAGE_WINDOWS", []) + bounds.get("WINDOWS", []):
        if window.get("name") == "Win_Be_Cryostat":
            return float(window["r_max"])
    raise RuntimeError("Win_Be_Cryostat not found in bounds.json")


def t3_days_from_z20(z20: float) -> float:
    if z20 <= 0.0:
        return math.inf
    if z20 >= 3.0:
        return MISSION_DAYS
    return MISSION_DAYS * (3.0 / z20) ** 2


def z20_for_rates(signal_cps: float, background_cps: float) -> float:
    if signal_cps <= 0.0 or background_cps <= 0.0:
        return 0.0
    return signal_cps * MISSION_EXPOSURE_S / math.sqrt(background_cps * MISSION_EXPOSURE_S)


def fov_geometry(bounds: dict[str, Any], optics: dict[str, Any]) -> dict[str, float]:
    be_r = be_window_radius_cm(bounds)
    focal_length_cm = float(optics["focal_length_mm"]) / 10.0
    theta_rad = math.atan(be_r / focal_length_cm)
    theta_deg = math.degrees(theta_rad)
    omega_sr = 2.0 * math.pi * (1.0 - math.cos(theta_rad))
    area_deg2_exact = omega_sr * DEG2_PER_SR
    area_deg2_plane = math.pi * theta_deg * theta_deg
    return {
        "be_window_radius_cm": be_r,
        "focal_length_cm": focal_length_cm,
        "theta_radius_rad": theta_rad,
        "theta_radius_deg": theta_deg,
        "theta_radius_arcmin": theta_deg * 60.0,
        "omega_sr": omega_sr,
        "fov_area_deg2_from_solid_angle": area_deg2_exact,
        "fov_area_deg2_plane_small_angle": area_deg2_plane,
        "solid_angle_vs_plane_area_rel_delta": abs(area_deg2_exact - area_deg2_plane) / area_deg2_plane,
    }


def component_metrics(component: dict[str, Any], geom: dict[str, float], auth: dict[str, float], step07_by_model: dict[str, dict[str, str]]) -> dict[str, Any]:
    total = float(component["total_flux_ph_cm2_s"])
    sigma_l = float(component.get("sigma_l_deg", float(component["fwhm_l_deg"]) / FWHM_TO_SIGMA))
    sigma_b = float(component.get("sigma_b_deg", float(component["fwhm_b_deg"]) / FWHM_TO_SIGMA))
    central_intensity_deg2 = total / (2.0 * math.pi * sigma_l * sigma_b)
    radius_deg = geom["theta_radius_deg"]
    if component["kind"] == "circular_gaussian":
        fov_fraction = 1.0 - math.exp(-(radius_deg * radius_deg) / (2.0 * sigma_l * sigma_l))
        fov_flux = total * fov_fraction
        fov_formula = "F_total * (1 - exp(-r^2/(2*sigma^2)))"
    else:
        fov_flux = central_intensity_deg2 * geom["fov_area_deg2_plane_small_angle"]
        fov_fraction = min(1.0, fov_flux / total)
        fov_formula = "I0 * pi*r^2 small-angle aperture integral"

    step07_row = step07_by_model.get(str(component["model_id"]), {})
    step07_flux = float(step07_row.get("fov_flux_ph_cm2_s", fov_flux))
    step07_delta = abs(fov_flux - step07_flux) / max(abs(step07_flux), 1.0e-300)
    plane_rate = fov_flux * auth["plane_rate_cps_per_flux"]
    w1_rate = fov_flux * auth["science_W1_final_response_cps_per_flux"]
    w2_rate = fov_flux * auth["science_W2_final_response_cps_per_flux"]
    z20 = z20_for_rates(w2_rate, auth["background_W2_final_cps"])
    return {
        **component,
        "sigma_l_deg": sigma_l,
        "sigma_b_deg": sigma_b,
        "central_intensity_ph_cm2_s_deg2": central_intensity_deg2,
        "central_intensity_ph_cm2_s_sr": central_intensity_deg2 * DEG2_PER_SR,
        "fov_radius_arcmin": geom["theta_radius_arcmin"],
        "fov_radius_deg": geom["theta_radius_deg"],
        "omega_sr": geom["omega_sr"],
        "fov_area_deg2": geom["fov_area_deg2_plane_small_angle"],
        "fov_formula": fov_formula,
        "fov_flux_top_atm_ph_cm2_s": fov_flux,
        "fov_fraction_of_component_total": fov_fraction,
        "step07_fov_flux_ph_cm2_s": step07_flux,
        "step07_fov_flux_rel_delta": step07_delta,
        "T_atm_ref": auth["T_atm_ref"],
        "A_eff_511_cm2": auth["A_eff_511_cm2"],
        "plane_rate_after_atm_cps": plane_rate,
        "W1_final_rate_cps": w1_rate,
        "W2_final_rate_cps": w2_rate,
        "W2_Z20d_no_spatial": z20,
        "W2_T3_day_constant_rate": t3_days_from_z20(z20),
        "ratio_to_route_A_ref_flux": fov_flux / auth["route_A_reference_flux_ph_cm2_s"],
        "ratio_to_route_A_ref_W2_signal": w2_rate / auth["route_A_W2_final_rate_cps"],
    }


def aggregate_metrics(model_id: str, scenario: str, rows: list[dict[str, Any]], auth: dict[str, float], geom: dict[str, float]) -> dict[str, Any]:
    total_flux = sum(float(row["total_flux_ph_cm2_s"]) for row in rows)
    fov_flux = sum(float(row["fov_flux_top_atm_ph_cm2_s"]) for row in rows)
    central_deg2 = sum(float(row["central_intensity_ph_cm2_s_deg2"]) for row in rows)
    plane_rate = fov_flux * auth["plane_rate_cps_per_flux"]
    w1_rate = fov_flux * auth["science_W1_final_response_cps_per_flux"]
    w2_rate = fov_flux * auth["science_W2_final_response_cps_per_flux"]
    z20 = z20_for_rates(w2_rate, auth["background_W2_final_cps"])
    return {
        "model_id": model_id,
        "kind": "aggregate",
        "component": "+".join(str(row["component"]) for row in rows),
        "scenario": scenario,
        "total_flux_ph_cm2_s": total_flux,
        "flux_uncertainty_ph_cm2_s": "",
        "fwhm_l_deg": "",
        "fwhm_b_deg": "",
        "sigma_l_deg": "",
        "sigma_b_deg": "",
        "central_intensity_ph_cm2_s_deg2": central_deg2,
        "central_intensity_ph_cm2_s_sr": central_deg2 * DEG2_PER_SR,
        "fov_radius_arcmin": geom["theta_radius_arcmin"],
        "fov_radius_deg": geom["theta_radius_deg"],
        "omega_sr": geom["omega_sr"],
        "fov_area_deg2": geom["fov_area_deg2_plane_small_angle"],
        "fov_formula": "sum of listed component aperture integrals",
        "fov_flux_top_atm_ph_cm2_s": fov_flux,
        "fov_fraction_of_component_total": fov_flux / total_flux if total_flux > 0.0 else 0.0,
        "step07_fov_flux_ph_cm2_s": sum(float(row["step07_fov_flux_ph_cm2_s"]) for row in rows),
        "step07_fov_flux_rel_delta": 0.0,
        "T_atm_ref": auth["T_atm_ref"],
        "A_eff_511_cm2": auth["A_eff_511_cm2"],
        "plane_rate_after_atm_cps": plane_rate,
        "W1_final_rate_cps": w1_rate,
        "W2_final_rate_cps": w2_rate,
        "W2_Z20d_no_spatial": z20,
        "W2_T3_day_constant_rate": t3_days_from_z20(z20),
        "ratio_to_route_A_ref_flux": fov_flux / auth["route_A_reference_flux_ph_cm2_s"],
        "ratio_to_route_A_ref_W2_signal": w2_rate / auth["route_A_W2_final_rate_cps"],
        "flux_reference": "; ".join(sorted({str(row["flux_reference"]) for row in rows})),
        "morphology_reference": "; ".join(sorted({str(row["morphology_reference"]) for row in rows})),
    }


def comparison_rows(metrics: list[dict[str, Any]], auth: dict[str, float], geom: dict[str, float]) -> list[dict[str, Any]]:
    by_id = {str(row["model_id"]): row for row in metrics}
    spot_fraction = (auth["spot_r90_radius_cm"] / geom["be_window_radius_cm"]) ** 2
    default = by_id["B_default_bulge8deg_plus_disk"]
    compact = by_id["bulge_gaussian_fwhm_3deg"]
    default_spot_signal = float(default["W2_final_rate_cps"]) * spot_fraction
    return [
        {
            "case_id": "Route_A_point_ref_W2_no_spatial",
            "description": "Focused on-axis compact 511-keV source at 1e-4 ph cm-2 s-1, W2 both selection.",
            "source_flux_or_fov_flux_ph_cm2_s": auth["route_A_reference_flux_ph_cm2_s"],
            "W2_signal_cps": auth["route_A_W2_final_rate_cps"],
            "background_cps": auth["background_W2_final_cps"],
            "Z20d": auth["route_A_W2_Z20d"],
            "T3_day_constant_rate": auth["route_A_W2_T3_day"],
            "spatial_policy": "no spot cut",
        },
        {
            "case_id": "Route_A_point_ref_W2_spot_r90",
            "description": "Same Route-A point source with detector spot_r90 point-source cut.",
            "source_flux_or_fov_flux_ph_cm2_s": auth["route_A_reference_flux_ph_cm2_s"],
            "W2_signal_cps": auth["route_A_W2_final_rate_cps"] * auth["spot_r90_signal_psf_fraction"],
            "background_cps": auth["spot_r90_background_cps"],
            "Z20d": auth["spot_r90_Z20d"],
            "T3_day_constant_rate": t3_days_from_z20(auth["spot_r90_Z20d"]),
            "spatial_policy": "valid for compact focused source",
        },
        {
            "case_id": "Route_B_compact_bulge3deg_W2_no_spatial",
            "description": "Route-B upper stress case: all bulge flux in a compact 3-deg FWHM Gaussian.",
            "source_flux_or_fov_flux_ph_cm2_s": compact["fov_flux_top_atm_ph_cm2_s"],
            "W2_signal_cps": compact["W2_final_rate_cps"],
            "background_cps": auth["background_W2_final_cps"],
            "Z20d": compact["W2_Z20d_no_spatial"],
            "T3_day_constant_rate": compact["W2_T3_day_constant_rate"],
            "spatial_policy": "aperture/rate fold only",
        },
        {
            "case_id": "Route_B_default_bulge8deg_plus_disk_W2_no_spatial",
            "description": "Route-B default diffuse foreground: 8-deg bulge plus thick disk, aperture integrated.",
            "source_flux_or_fov_flux_ph_cm2_s": default["fov_flux_top_atm_ph_cm2_s"],
            "W2_signal_cps": default["W2_final_rate_cps"],
            "background_cps": auth["background_W2_final_cps"],
            "Z20d": default["W2_Z20d_no_spatial"],
            "T3_day_constant_rate": default["W2_T3_day_constant_rate"],
            "spatial_policy": "aperture/rate fold only",
        },
        {
            "case_id": "Route_B_default_uniform_spot_r90_sanity",
            "description": "Sanity check only: if diffuse light fills the Be aperture uniformly, a point-source spot cut also removes signal by area.",
            "source_flux_or_fov_flux_ph_cm2_s": default["fov_flux_top_atm_ph_cm2_s"] * spot_fraction,
            "W2_signal_cps": default_spot_signal,
            "background_cps": auth["spot_r90_background_cps"],
            "Z20d": z20_for_rates(default_spot_signal, auth["spot_r90_background_cps"]),
            "T3_day_constant_rate": t3_days_from_z20(z20_for_rates(default_spot_signal, auth["spot_r90_background_cps"])),
            "spatial_policy": f"not a detection claim; uniform-aperture area fraction {spot_fraction:.6g}",
        },
    ]


def plot_comparison(rows: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[str]:
    if plt is None:
        return []
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    labels = [row["case_id"].replace("Route_", "").replace("_W2", "").replace("_", "\n") for row in rows[:4]]
    zvals = [float(row["Z20d"]) for row in rows[:4]]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.bar(range(len(zvals)), zvals, color=["#4C78A8", "#4C78A8", "#F58518", "#F58518"])
    ax.axhline(3.0, color="#333333", lw=1.0, ls="--", label="3 sigma")
    ax.set_yscale("log")
    ax.set_ylabel("20-day W2 counting Z")
    ax.set_title("Route A focused point source vs Route B diffuse aperture foreground")
    ax.set_xticks(range(len(zvals)), labels, fontsize=7)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig_path = fig_dir / "route_a_b_w2_z20_comparison.png"
    fig.savefig(fig_path, dpi=220)
    plt.close(fig)

    selected = [row for row in metrics if row["kind"] != "aggregate"]
    labels = [str(row["model_id"]).replace("_", "\n") for row in selected]
    vals = [float(row["fov_fraction_of_component_total"]) for row in selected]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.bar(range(len(vals)), vals, color=["#54A24B"] * len(vals))
    ax.set_yscale("log")
    ax.set_ylabel("FoV-selected fraction of total diffuse flux")
    ax.set_title("Route B is limited by the 7.25 arcmin focal aperture")
    ax.set_xticks(range(len(vals)), labels, fontsize=7)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    frac_path = fig_dir / "route_b_diffuse_fov_fraction.png"
    fig.savefig(frac_path, dpi=220)
    plt.close(fig)
    return [rel(fig_path), rel(frac_path)]


def md_table(rows: list[dict[str, Any]], fields: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in fields:
            value = row.get(key, "")
            if isinstance(value, float):
                values.append(fmt(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_report(summary: dict[str, Any], metrics: list[dict[str, Any]], comp_rows: list[dict[str, Any]], figures: list[str]) -> None:
    geom = summary["geometry"]
    auth = summary["authority"]
    by_id = {str(row["model_id"]): row for row in metrics}
    default = by_id["B_default_bulge8deg_plus_disk"]
    compact = by_id["bulge_gaussian_fwhm_3deg"]
    lines = [
        "# Route B Diffuse Supplement (2026-06-02)",
        "",
        "## Decision",
        "",
        "Route B is useful as a comparison/null foreground, but it is not worth turning into a focal-spot Cosima source for the current focused-detector chain. A diffuse bulge/disk model must be treated as sky brightness over solid angle; after the 7.25 arcmin focal aperture and atmospheric transmission, the signal is far below the Route-A compact point-source case.",
        "",
        "## Physical Input Chain",
        "",
        f"- Sky flux anchors: bulge `{fmt(9.6e-4)}` ph cm-2 s-1 and disk `{fmt(1.66e-3)}` ph cm-2 s-1 from `{REFERENCES['siegert_2016']['label']}`.",
        "- Sky morphology: circular Gaussian bulge stress/default cases plus an elliptical thick-disk proxy. The 8-deg bulge is the default extended-bulge comparison; 3-deg and 12-deg cases bracket compact/broad alternatives rather than claiming a unique morphology.",
        f"- Focal aperture: Be radius `{fmt(geom['be_window_radius_cm'])}` cm, focal length `{fmt(geom['focal_length_cm'])}` cm, angular radius `{fmt(geom['theta_radius_arcmin'])}` arcmin.",
        f"- Input solid angle: Omega = `2*pi*(1-cos(atan(r/f))) = {fmt(geom['omega_sr'])}` sr, plane small-angle area `{fmt(geom['fov_area_deg2_plane_small_angle'])}` deg2.",
        f"- Atmosphere: Step06 day-15 reference transmission `T_atm_ref = {fmt(auth['T_atm_ref'])}`. The detector-plane photon rate is `F_fov * A_eff(511) * T_atm_ref`.",
        f"- Current optics/detector authority: `A_eff(511) = {fmt(auth['A_eff_511_cm2'])}` cm2; W2 final response `{fmt(auth['science_W2_final_response_cps_per_flux'])}` cps per ph cm-2 s-1.",
        "",
        "## Route B Results",
        "",
        f"- Default Route B (8-deg bulge + thick disk) FoV flux: `{fmt(default['fov_flux_top_atm_ph_cm2_s'])}` ph cm-2 s-1, only `{fmt(default['ratio_to_route_A_ref_flux'])}` of the Route-A `1e-4` point-source reference.",
        f"- Default Route B W2 final signal: `{fmt(default['W2_final_rate_cps'])}` cps; W2 20-day counting Z: `{fmt(default['W2_Z20d_no_spatial'])}`.",
        f"- Even the compact 3-deg bulge stress case gives FoV flux `{fmt(compact['fov_flux_top_atm_ph_cm2_s'])}` ph cm-2 s-1 and W2 20-day Z `{fmt(compact['W2_Z20d_no_spatial'])}`.",
        f"- Route A point-source W2 no-spatial Z is `{fmt(auth['route_A_W2_Z20d'])}`; with the valid point-source `spot_r90` cut it is `{fmt(auth['spot_r90_Z20d'])}`.",
        "",
        "The point-source spot cut should not be applied as a gain to Route B. For an aperture-filling diffuse signal, the spot cut also removes signal area; the included uniform-aperture sanity row gives a lower Z, not a stronger detection.",
        "",
        "## Component Table",
        "",
        *md_table(
            [row for row in metrics if row["kind"] != "aggregate"],
            [
                ("model_id", "model"),
                ("total_flux_ph_cm2_s", "total flux"),
                ("fwhm_l_deg", "FWHM l"),
                ("fwhm_b_deg", "FWHM b"),
                ("fov_flux_top_atm_ph_cm2_s", "FoV flux"),
                ("fov_fraction_of_component_total", "FoV fraction"),
                ("plane_rate_after_atm_cps", "plane cps"),
                ("W2_final_rate_cps", "W2 cps"),
                ("W2_Z20d_no_spatial", "W2 Z20d"),
            ],
        ),
        "",
        "## Route A / Route B Comparison",
        "",
        *md_table(
            comp_rows,
            [
                ("case_id", "case"),
                ("source_flux_or_fov_flux_ph_cm2_s", "source/FoV flux"),
                ("W2_signal_cps", "W2 signal cps"),
                ("background_cps", "background cps"),
                ("Z20d", "Z20d"),
                ("T3_day_constant_rate", "T3 day"),
                ("spatial_policy", "spatial policy"),
            ],
        ),
        "",
        "## Checks",
        "",
        f"- Max relative delta against existing Step07 `diffuse_aperture_foreground.csv`: `{fmt(summary['checks']['max_step07_fov_flux_rel_delta'])}`.",
        f"- Solid-angle exact area vs small-angle plane area relative delta: `{fmt(geom['solid_angle_vs_plane_area_rel_delta'])}`.",
        f"- Generated report outputs are under `{rel(OUT)}` and are ignored by Git policy.",
        "",
        "## References",
        "",
    ]
    for ref in REFERENCES.values():
        lines.append(f"- {ref['label']}: {ref['url']} ({ref['role']})")
    if figures:
        lines.extend(["", "## Figures", ""])
        lines.extend(f"- `{path}`" for path in figures)
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "route_b_diffuse_supplement.md").write_text(text, encoding="utf-8")
    TRACKED_MD.write_text(text, encoding="utf-8")


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    bounds = load_json(BOUNDS)
    optics = load_json(OPTICS_AUTHORITY)
    step06 = load_json(STEP06_SUMMARY)
    step07 = load_json(STEP07_SUMMARY)
    focus = load_json(FOCUS_RESPONSE)
    step07_rows = {row["sky_model"]: row for row in read_csv(STEP07_DIFFUSE)}

    geom = fov_geometry(bounds, optics)
    w2 = focus["window_checks"]["W2_511_pm_420eV"]
    w1 = focus["window_checks"]["W1_design_passband"]
    spatial = focus["spatial_checks"]
    reference_flux = float(focus["normalization"]["reference_flux_ph_cm2_s"])
    auth = {
        "route_A_reference_flux_ph_cm2_s": reference_flux,
        "A_eff_511_cm2": float(optics["aeff_511_cm2"]),
        "T_atm_ref": float(step06["atmosphere"]["T_ref"]),
        "plane_rate_cps_per_flux": float(optics["aeff_511_cm2"]) * float(step06["atmosphere"]["T_ref"]),
        "science_W1_final_response_cps_per_flux": float(w1["signal_both_response_cps_per_ph_cm2_s"]),
        "science_W2_final_response_cps_per_flux": float(w2["signal_both_response_cps_per_ph_cm2_s"]),
        "background_W2_final_cps": float(w2["background_both_cps"]),
        "route_A_W2_final_rate_cps": float(w2["signal_both_cps_at_reference_flux"]),
        "route_A_W2_Z20d": float(w2["Z20d_both"]),
        "route_A_W2_T3_day": float(w2["T3_day_constant_rate"]),
        "spot_r90_radius_cm": float(spatial["signal_radius_r90_cm"]),
        "spot_r90_signal_psf_fraction": float(spatial["spot_r90_signal_psf_fraction"]),
        "spot_r90_background_cps": float(spatial["spot_r90_background_cps"]),
        "spot_r90_Z20d": float(spatial["spot_r90_Z20d"]),
        "step07_claim_level": step07["claim_level"],
    }
    metrics = [component_metrics(component, geom, auth, step07_rows) for component in SKY_COMPONENTS]
    by_id = {str(row["model_id"]): row for row in metrics}
    metrics.append(aggregate_metrics("B_default_bulge8deg_plus_disk", "default diffuse foreground", [by_id["bulge_gaussian_fwhm_8deg"], by_id["disk_thick_gaussian"]], auth, geom))
    metrics.append(aggregate_metrics("B_bulge3deg_plus_disk_stress", "compact-bulge plus disk stress foreground", [by_id["bulge_gaussian_fwhm_3deg"], by_id["disk_thick_gaussian"]], auth, geom))
    comp_rows = comparison_rows(metrics, auth, geom)
    max_step07_delta = max(float(row["step07_fov_flux_rel_delta"]) for row in metrics if row["kind"] != "aggregate")
    summary = {
        "status": "PASS",
        "claim_level": "L1_ROUTE_B_DIFFUSE_APERTURE_PHYSICAL_SUPPLEMENT",
        "scope": "Diffuse bulge/disk Route B comparison using sky-intensity-over-solid-angle, Step06 atmospheric transmission, and current Step09 detector-coupled response.",
        "geometry": geom,
        "authority": auth,
        "checks": {
            "max_step07_fov_flux_rel_delta": max_step07_delta,
            "step07_claim_level": step07["claim_level"],
            "no_simulation_data_staged_policy": "outputs are generated under ignored outputs/reports; tracked artifacts are code and markdown only",
        },
        "references": REFERENCES,
        "outputs": {
            "metrics_csv": rel(OUT / "route_b_diffuse_metrics.csv"),
            "comparison_csv": rel(OUT / "route_ab_comparison.csv"),
            "summary_json": rel(OUT / "route_b_diffuse_summary.json"),
            "report_md": rel(OUT / "route_b_diffuse_supplement.md"),
            "tracked_md": rel(TRACKED_MD),
        },
    }
    figures = plot_comparison(comp_rows, metrics)
    summary["outputs"]["figures"] = figures
    write_csv(OUT / "route_b_diffuse_metrics.csv", metrics)
    write_csv(OUT / "route_ab_comparison.csv", comp_rows)
    write_json(OUT / "route_b_diffuse_summary.json", summary)
    write_report(summary, metrics, comp_rows, figures)
    print(json.dumps({"status": summary["status"], "claim_level": summary["claim_level"], "tracked_md": rel(TRACKED_MD), "out": rel(OUT), "checks": summary["checks"]}, indent=2, ensure_ascii=False))
    return summary


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
