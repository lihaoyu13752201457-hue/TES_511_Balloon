#!/usr/bin/env python3
"""Build source-level balloon/LEO/lunar prompt-spectrum comparisons.

The lunar input is the public REDMoon Figure-5 table.  This script deliberately
stops before detector transport, activation, delayed decay, or reconstruction.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_lunar_mplconfig"))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
BASE_ROOT = REPO_ROOT / "engineering" / "satellite_leo530_source_comparison_20260813"
BASE_TABLES = BASE_ROOT / "outputs" / "tables"
REDMOON_PATH = PACKAGE_ROOT / "inputs" / "redmoon_zenodo_5561427" / "fig5.txt"
OUTPUT_ROOT = PACKAGE_ROOT / "outputs"
FIGURE_ROOT = OUTPUT_ROOT / "figures"
TABLE_ROOT = OUTPUT_ROOT / "tables"

EXPECTED_INPUT_SHA256 = {
    REDMOON_PATH: "82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5",
    BASE_ROOT / "data" / "validation.json": "0c507ea29cf05d14e7af13d3d6c374e99cc28013986a6166cd6dfcd3ae5b51a7",
    BASE_TABLES / "balloon_aggregated_spectra.csv": "b4a26f8f4b528c22f99d6396971331a10d88b3f23b00da07e998c1b8ac975611",
    BASE_TABLES / "satellite_component_spectra.csv": "49aa2e4777fea53d7138081f9e8c2c34e11097567319cee9574b32141f59cd25",
    BASE_TABLES / "satellite_profile_spectra.csv": "89f0d55e0d9706c4a963720a379e60108f70d9400a84a867ec37bca7f04f185f",
    BASE_TABLES / "satellite_line_components.csv": "758c074f66ec34c7bba2243a64d4376680ee6b8b0ece9b9146d9d3413d4d24a1",
    BASE_TABLES / "band_integrals.csv": "55376aadfed70ada5b9def0866443d195d8e202d9b593b35fe2b662d27824074",
    BASE_TABLES / "environment_contrasts.csv": "d6ed13b188b66886d8c09ee64410cbe566980f2fc348ca5a7a1b4d597e722f03",
}

BALLOON = "#2369BD"
LEO = "#E07A1F"
MOON = "#7651A8"
TEXT = "#1F2933"
MUTED = "#606B75"
GRID = "#D8DDE2"

FAMILY_COLORS = {
    "gamma": "#2369BD",
    "p": "#2A9D45",
    "alpha": "#7C8B24",
    "eminus": "#E07A1F",
    "eplus": "#CC5C91",
    "n": "#7651A8",
    "mu": "#7A7F85",
    "epm": "#A56047",
}

BANDS = (
    ("100_300_keV", "100–300 keV", 100.0, 300.0),
    ("300_450_keV", "300–450 keV", 300.0, 450.0),
    ("450_600_keV_annihilation_region_proxy", "450–600 keV†", 450.0, 600.0),
    ("600_1000_keV", "600–1000 keV", 600.0, 1000.0),
    ("1_10_MeV", "1–10 MeV", 1000.0, 10000.0),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def require_pinned_inputs() -> None:
    for path, expected in EXPECTED_INPUT_SHA256.items():
        if not path.is_file():
            raise RuntimeError(f"Missing required input: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Input hash mismatch for {path}: {actual} != {expected}")
    base_validation = json.loads((BASE_ROOT / "data" / "validation.json").read_text(encoding="utf-8"))
    if base_validation.get("status") != "PASS":
        raise RuntimeError("The balloon/LEO source-input package is not PASS")


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.family": "sans-serif",
            # Matplotlib exposes the installed Noto CJK TTC under its internal
            # family name "Noto Sans CJK JP"; the file includes the Chinese
            # glyph coverage needed by this figure.
            "font.sans-serif": ["Noto Sans CJK JP", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "legend.fontsize": 8.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.alpha": 0.72,
            "grid.linestyle": ":",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_ROOT / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURE_ROOT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def unique_curve(
    rows: list[dict[str, str]], energy_field: str, value_field: str
) -> tuple[np.ndarray, np.ndarray]:
    grouped: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(value_field, "") == "":
            continue
        energy = float(row[energy_field])
        value = float(row[value_field])
        if math.isfinite(energy) and math.isfinite(value) and energy > 0 and value >= 0:
            grouped[energy].append(value)
    energy = np.asarray(sorted(grouped), dtype=float)
    values = np.asarray([float(np.mean(grouped[item])) for item in energy], dtype=float)
    if len(energy) < 2 or np.any(np.diff(energy) <= 0):
        raise RuntimeError("Curve does not have a valid strictly increasing energy axis")
    return energy, values


def parse_redmoon() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    lines = REDMOON_PATH.read_text(encoding="utf-8").splitlines()
    if "upper hemisphere" not in lines[0] or "Smin 2019" not in lines[2]:
        raise RuntimeError("Unexpected REDMoon fig5 header")
    pairs = {
        "gcr_proton_reference": (3, 4),
        "secondary_proton": (5, 6),
        "secondary_neutron": (7, 8),
        "secondary_gamma": (9, 10),
        "secondary_electron_positron": (11, 12),
    }
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name, (energy_line, value_line) in pairs.items():
        energy = np.asarray([float(item) for item in lines[energy_line].split(",")], dtype=float)
        values = np.asarray([float(item) for item in lines[value_line].split(",")], dtype=float)
        if len(energy) != len(values) or len(energy) < 2:
            raise RuntimeError(f"REDMoon pair length mismatch: {name}")
        if np.any(np.diff(energy) <= 0) or np.any(~np.isfinite(values)) or np.any(values < 0):
            raise RuntimeError(f"Invalid REDMoon data: {name}")
        result[name] = (energy, values)
    gamma_energy, gamma_values = result["secondary_gamma"]
    peak_index = int(np.argmax(gamma_values))
    if not math.isclose(gamma_energy[peak_index], 0.51286, rel_tol=0, abs_tol=1e-8):
        raise RuntimeError("REDMoon gamma peak energy is not the pinned 0.51286 MeV node")
    if not math.isclose(gamma_values[peak_index], 325.06, rel_tol=0, abs_tol=1e-6):
        raise RuntimeError("REDMoon gamma peak value changed")
    return result


def interp_loglog(x: np.ndarray, y: np.ndarray, target: np.ndarray) -> np.ndarray:
    output = np.zeros_like(target, dtype=float)
    valid = (x > 0) & (y > 0)
    xv = x[valid]
    yv = y[valid]
    inside = (target >= xv[0]) & (target <= xv[-1])
    output[inside] = np.exp(
        np.interp(np.log(target[inside]), np.log(xv), np.log(yv))
    )
    return output


def centered_log_bin_integral(
    energy_mev: np.ndarray, values_per_mev: np.ndarray, low_mev: float, high_mev: float
) -> float:
    """Integrate a tabulated centered log-energy histogram without smoothing lines."""
    edges = np.empty(len(energy_mev) + 1, dtype=float)
    edges[1:-1] = np.sqrt(energy_mev[:-1] * energy_mev[1:])
    edges[0] = energy_mev[0] * math.sqrt(energy_mev[0] / energy_mev[1])
    edges[-1] = energy_mev[-1] * math.sqrt(energy_mev[-1] / energy_mev[-2])
    widths = np.maximum(0.0, np.minimum(edges[1:], high_mev) - np.maximum(edges[:-1], low_mev))
    return float(np.sum(widths * values_per_mev))


def load_inputs() -> dict[str, object]:
    balloon_rows = read_csv(BASE_TABLES / "balloon_aggregated_spectra.csv")
    satellite_component_rows = read_csv(BASE_TABLES / "satellite_component_spectra.csv")
    satellite_profile_rows = read_csv(BASE_TABLES / "satellite_profile_spectra.csv")
    line_rows = read_csv(BASE_TABLES / "satellite_line_components.csv")
    band_rows = read_csv(BASE_TABLES / "band_integrals.csv")
    contrast_rows = read_csv(BASE_TABLES / "environment_contrasts.csv")
    redmoon = parse_redmoon()

    line_matches = [row for row in line_rows if row["component_id"] == "atmospheric_511_line"]
    if len(line_matches) != 1:
        raise RuntimeError("Expected exactly one LEO mono-511 line component")

    cosmic_rows = [
        row
        for row in satellite_component_rows
        if row["component_id"] == "cosmic_photons"
        and row["within_cited_model_validity"].lower() == "true"
    ]
    cosmic_energy_kev, cosmic_intensity_per_kev_sr = unique_curve(
        cosmic_rows, "energy_keV_total", "support_avg_intensity_cm2_s_sr_keV"
    )
    cosmic_omega_values = {float(row["solid_angle_sr"]) for row in cosmic_rows}
    if len(cosmic_omega_values) != 1:
        raise RuntimeError("Cosmic-photon angular support is not unique")

    return {
        "balloon_rows": balloon_rows,
        "satellite_component_rows": satellite_component_rows,
        "satellite_profile_rows": satellite_profile_rows,
        "line_row": line_matches[0],
        "band_rows": band_rows,
        "contrast_rows": contrast_rows,
        "redmoon": redmoon,
        "cosmic_energy_kev": cosmic_energy_kev,
        "cosmic_intensity_per_kev_sr": cosmic_intensity_per_kev_sr,
        "cosmic_original_omega_sr": cosmic_omega_values.pop(),
    }


def build_lunar_tables(data: dict[str, object]) -> dict[str, object]:
    redmoon: dict[str, tuple[np.ndarray, np.ndarray]] = data["redmoon"]  # type: ignore[assignment]
    component_meta = {
        "gcr_proton_reference": ("p", "sky/GCR reference", "REDMoon GCR p reference"),
        "secondary_proton": ("p", "regolith-up", "REDMoon secondary proton"),
        "secondary_neutron": ("n", "regolith-up", "REDMoon secondary neutron"),
        "secondary_gamma": ("gamma", "regolith-up", "REDMoon secondary gamma; includes 511-keV spike"),
        "secondary_electron_positron": ("e-+e+", "regolith-up", "REDMoon secondary electron+positron"),
    }
    lunar_component_rows: list[dict[str, object]] = []
    for component, (energy_mev, values_per_mev) in redmoon.items():
        family, direction, note = component_meta[component]
        for energy, value in zip(energy_mev, values_per_mev):
            lunar_component_rows.append(
                {
                    "environment": "exposed_lunar_surface_proxy",
                    "profile": "REDMoon_2019_solar_min_Apollo17_FTFP_BERT_HP",
                    "component": component,
                    "family": family,
                    "direction_domain": direction,
                    "energy_MeV_total": energy,
                    "differential_flux_cm2_s_MeV": value,
                    "energy_weighted_flux_cm2_s": energy * value,
                    "note": note,
                }
            )
    write_csv(
        TABLE_ROOT / "lunar_prompt_components.csv",
        lunar_component_rows,
        (
            "environment",
            "profile",
            "component",
            "family",
            "direction_domain",
            "energy_MeV_total",
            "differential_flux_cm2_s_MeV",
            "energy_weighted_flux_cm2_s",
            "note",
        ),
    )

    balloon_rows: list[dict[str, str]] = data["balloon_rows"]  # type: ignore[assignment]
    balloon_gamma = [
        row for row in balloon_rows if row["family"] == "gamma" and row["domain"] == "full"
    ]
    balloon_energy_kev, balloon_flux_per_kev = unique_curve(
        balloon_gamma, "energy_keV_total", "differential_flux_cm2_s_keV"
    )

    satellite_profile_rows: list[dict[str, str]] = data["satellite_profile_rows"]  # type: ignore[assignment]
    leo_gamma = [
        row
        for row in satellite_profile_rows
        if row["family"] == "gamma" and row["profile"] == "satellite_nominal_continuum"
    ]
    leo_energy_kev, leo_flux_per_kev = unique_curve(
        leo_gamma, "energy_keV_total", "validity_filtered_differential_flux_cm2_s_keV"
    )

    moon_energy_mev, moon_flux_per_mev = redmoon["secondary_gamma"]
    moon_energy_kev = moon_energy_mev * 1000.0
    moon_flux_per_kev = moon_flux_per_mev / 1000.0
    cosmic_energy_kev: np.ndarray = data["cosmic_energy_kev"]  # type: ignore[assignment]
    cosmic_intensity_per_kev_sr: np.ndarray = data["cosmic_intensity_per_kev_sr"]  # type: ignore[assignment]
    lunar_sky_flux_per_kev_native = interp_loglog(
        cosmic_energy_kev,
        cosmic_intensity_per_kev_sr * (2.0 * math.pi),
        moon_energy_kev,
    )
    lunar_total_flux_per_kev = moon_flux_per_kev + lunar_sky_flux_per_kev_native

    gamma_rows: list[dict[str, object]] = []

    def append_curve(
        environment: str,
        component: str,
        angular_scope: str,
        energy_kev: np.ndarray,
        flux_per_kev: np.ndarray,
        provenance: str,
    ) -> None:
        for energy, value in zip(energy_kev, flux_per_kev):
            gamma_rows.append(
                {
                    "environment": environment,
                    "component": component,
                    "angular_scope": angular_scope,
                    "energy_keV_total": energy,
                    "differential_flux_cm2_s_keV": value,
                    "energy_weighted_flux_cm2_s": energy * value,
                    "provenance": provenance,
                }
            )

    append_curve(
        "balloon_38km",
        "broadband_total_gamma",
        "full sphere",
        balloon_energy_kev,
        balloon_flux_per_kev,
        "validated corrected-keV EXPACS/PARMA package",
    )
    append_curve(
        "leo530_proxy",
        "nominal_gamma_continuum",
        "mixed unocculted-sky and Earth-visible supports",
        leo_energy_kev,
        leo_flux_per_kev,
        "validated COSI DC4 proxy; delta-511 stored separately",
    )
    append_curve(
        "lunar_surface_proxy",
        "regolith_up_gamma",
        "upper hemisphere",
        moon_energy_kev,
        moon_flux_per_kev,
        "REDMoon 2019 solar minimum, Apollo-17 soil, FTFP_BERT_HP",
    )
    append_curve(
        "lunar_surface_proxy",
        "sky_down_cosmic_gamma_proxy",
        "visible sky hemisphere (2pi)",
        cosmic_energy_kev,
        cosmic_intensity_per_kev_sr * (2.0 * math.pi),
        "COSI cosmic-photon spectral intensity rescaled to 2pi; model splice",
    )
    append_curve(
        "lunar_surface_proxy",
        "total_prompt_gamma_proxy",
        "regolith-up plus sky-down",
        moon_energy_kev,
        lunar_total_flux_per_kev,
        "REDMoon regolith plus COSI cosmic-sky spectral proxy",
    )
    write_csv(
        TABLE_ROOT / "three_environment_gamma_spectra.csv",
        gamma_rows,
        (
            "environment",
            "component",
            "angular_scope",
            "energy_keV_total",
            "differential_flux_cm2_s_keV",
            "energy_weighted_flux_cm2_s",
            "provenance",
        ),
    )

    contrast_rows: list[dict[str, str]] = data["contrast_rows"]  # type: ignore[assignment]
    contrast_lookup = {
        row["band"]: row for row in contrast_rows if row["family"] == "gamma"
    }
    band_rows: list[dict[str, str]] = data["band_rows"]  # type: ignore[assignment]
    cosmic_band_lookup = {
        row["band"]: row
        for row in band_rows
        if row["environment"] == "satellite_leo530_proxy"
        and row["component_or_family"] == "cosmic_photons"
        and row["profile"] == "component_physical_restored"
    }
    cosmic_original_omega_sr = float(data["cosmic_original_omega_sr"])
    lunar_sky_scale = 2.0 * math.pi / cosmic_original_omega_sr

    output_band_rows: list[dict[str, object]] = []
    band_values: dict[str, dict[str, float]] = {}
    for band_id, label, low_kev, high_kev in BANDS:
        if band_id not in contrast_lookup or band_id not in cosmic_band_lookup:
            raise RuntimeError(f"Missing validated base band: {band_id}")
        base = contrast_lookup[band_id]
        balloon_value = float(base["balloon_full_flux_cm2_s"])
        leo_value = float(base["satellite_flux_cm2_s"])
        lunar_regolith = centered_log_bin_integral(
            moon_energy_mev, moon_flux_per_mev, low_kev / 1000.0, high_kev / 1000.0
        )
        lunar_sky = float(cosmic_band_lookup[band_id]["band_flux_cm2_s"]) * lunar_sky_scale
        lunar_total = lunar_regolith + lunar_sky
        band_values[band_id] = {
            "balloon": balloon_value,
            "leo": leo_value,
            "lunar_regolith": lunar_regolith,
            "lunar_sky": lunar_sky,
            "lunar_total": lunar_total,
        }
        for environment, component, value, note in (
            ("balloon_38km", "broadband_total_gamma", balloon_value, "full-sphere corrected balloon field"),
            ("leo530_proxy", "nominal_gamma_including_delta_when_in_band", leo_value, "LEO continuum; mono-511 included only in 450–600 keV"),
            ("lunar_surface_proxy", "regolith_up_gamma", lunar_regolith, "REDMoon native centered log-energy bins"),
            ("lunar_surface_proxy", "sky_down_cosmic_gamma_proxy", lunar_sky, "COSI cosmic intensity scaled to lunar visible 2pi"),
            ("lunar_surface_proxy", "total_prompt_gamma_proxy", lunar_total, "regolith-up plus sky-down proxy"),
        ):
            output_band_rows.append(
                {
                    "environment": environment,
                    "component": component,
                    "band": band_id,
                    "band_label": label,
                    "low_keV": low_kev,
                    "high_keV": high_kev,
                    "band_flux_cm2_s": value,
                    "comparison_grade": "C" if environment == "lunar_surface_proxy" or "450_600" in band_id else "B",
                    "note": note,
                }
            )

    totals = {
        key: sum(values[key] for values in band_values.values())
        for key in ("balloon", "leo", "lunar_regolith", "lunar_sky", "lunar_total")
    }
    for environment, component, key, note in (
        ("balloon_38km", "broadband_total_gamma", "balloon", "sum of five contiguous bands"),
        ("leo530_proxy", "nominal_gamma_including_mono_511", "leo", "sum of five contiguous bands"),
        ("lunar_surface_proxy", "regolith_up_gamma", "lunar_regolith", "sum of five contiguous bands"),
        ("lunar_surface_proxy", "sky_down_cosmic_gamma_proxy", "lunar_sky", "sum of five contiguous bands"),
        ("lunar_surface_proxy", "total_prompt_gamma_proxy", "lunar_total", "sum of five contiguous bands"),
    ):
        output_band_rows.append(
            {
                "environment": environment,
                "component": component,
                "band": "100_keV_10_MeV_total",
                "band_label": "0.1–10 MeV",
                "low_keV": 100.0,
                "high_keV": 10000.0,
                "band_flux_cm2_s": totals[key],
                "comparison_grade": "C" if environment == "lunar_surface_proxy" else "B",
                "note": note,
            }
        )

    write_csv(
        TABLE_ROOT / "gamma_band_integrals.csv",
        output_band_rows,
        (
            "environment",
            "component",
            "band",
            "band_label",
            "low_keV",
            "high_keV",
            "band_flux_cm2_s",
            "comparison_grade",
            "note",
        ),
    )

    line_row: dict[str, str] = data["line_row"]  # type: ignore[assignment]
    line_output = [
        {
            "environment": "leo530_proxy",
            "component": "atmospheric_mono_511",
            "line_energy_keV": float(line_row["line_energy_keV_total"]),
            "integrated_line_flux_cm2_s": float(line_row["physical_line_flux_cm2_s"]),
            "plot_treatment": "position marker only; no arbitrary differential height",
        }
    ]
    write_csv(
        TABLE_ROOT / "line_components.csv",
        line_output,
        (
            "environment",
            "component",
            "line_energy_keV",
            "integrated_line_flux_cm2_s",
            "plot_treatment",
        ),
    )

    return {
        "balloon_energy_kev": balloon_energy_kev,
        "balloon_flux_per_kev": balloon_flux_per_kev,
        "leo_energy_kev": leo_energy_kev,
        "leo_flux_per_kev": leo_flux_per_kev,
        "moon_energy_kev": moon_energy_kev,
        "moon_regolith_flux_per_kev": moon_flux_per_kev,
        "moon_total_flux_per_kev": lunar_total_flux_per_kev,
        "band_values": band_values,
        "totals": totals,
        "line_flux_cm2_s": float(line_row["physical_line_flux_cm2_s"]),
        "lunar_component_rows": lunar_component_rows,
    }


def plot_three_environment_components(data: dict[str, object], derived: dict[str, object]) -> None:
    balloon_rows: list[dict[str, str]] = data["balloon_rows"]  # type: ignore[assignment]
    satellite_rows: list[dict[str, str]] = data["satellite_component_rows"]  # type: ignore[assignment]
    redmoon: dict[str, tuple[np.ndarray, np.ndarray]] = data["redmoon"]  # type: ignore[assignment]

    fig, axes = plt.subplots(1, 3, figsize=(16.4, 6.2), sharex=True, sharey=True)

    balloon_styles = {
        "gamma": ("γ 宽带总谱", FAMILY_COLORS["gamma"], "-"),
        "p": ("质子", FAMILY_COLORS["p"], "-"),
        "alpha": ("α", FAMILY_COLORS["alpha"], ":"),
        "eminus": ("电子", FAMILY_COLORS["eminus"], "-"),
        "eplus": ("正电子", FAMILY_COLORS["eplus"], "--"),
        "n": ("中子", FAMILY_COLORS["n"], "-."),
        "muminus": ("μ−", FAMILY_COLORS["mu"], "-."),
        "muplus": ("μ+", FAMILY_COLORS["mu"], ":"),
    }
    for family, (label, color, style) in balloon_styles.items():
        rows = [row for row in balloon_rows if row["family"] == family and row["domain"] == "full"]
        energy_kev, flux_per_kev = unique_curve(
            rows, "energy_keV_total", "differential_flux_cm2_s_keV"
        )
        energy_mev = energy_kev / 1000.0
        flux_per_mev = flux_per_kev * 1000.0
        mask = (energy_mev >= 0.1) & (energy_mev <= 1.0e5) & (flux_per_mev > 0)
        axes[0].loglog(energy_mev[mask], flux_per_mev[mask], color=color, ls=style, lw=1.55, label=label)

    leo_specs = (
        ("cosmic_photons", "天空 γ", "gamma", "-"),
        ("albedo_photons_continuum", "地球反照 γ", "gamma", "--"),
        ("primary_proton", "初级质子", "p", "-"),
        ("secondary_proton", "次级质子", "p", "--"),
        ("primary_alpha", "初级 α", "alpha", ":"),
        ("primary_electron", "初级电子", "eminus", "-"),
        ("secondary_electron", "次级电子", "eminus", "--"),
        ("primary_positron", "初级正电子", "eplus", "-"),
        ("secondary_positron", "次级正电子", "eplus", "--"),
    )
    for component, label, family, style in leo_specs:
        rows = [
            row
            for row in satellite_rows
            if row["component_id"] == component
            and row["within_cited_model_validity"].lower() == "true"
        ]
        energy_kev, flux_per_kev = unique_curve(
            rows, "energy_keV_total", "differential_flux_cm2_s_keV"
        )
        energy_mev = energy_kev / 1000.0
        flux_per_mev = flux_per_kev * 1000.0
        mask = (energy_mev >= 0.1) & (energy_mev <= 1.0e5) & (flux_per_mev > 0)
        axes[1].loglog(
            energy_mev[mask], flux_per_mev[mask], color=FAMILY_COLORS[family], ls=style, lw=1.5, label=label
        )
    axes[1].axvline(0.511, color="#333333", lw=1.1, ls=":", label="LEO mono-511（仅位置）")

    moon_specs = (
        ("gcr_proton_reference", "GCR 质子参考", "p", "-"),
        ("secondary_proton", "月壤次级质子", "p", "--"),
        ("secondary_neutron", "月壤上行中子", "n", "-."),
        ("secondary_gamma", "月壤上行 γ（含511）", "gamma", "-"),
        ("secondary_electron_positron", "月壤上行 e−+e+", "epm", "--"),
    )
    for component, label, family, style in moon_specs:
        energy_mev, flux_per_mev = redmoon[component]
        mask = (energy_mev >= 0.1) & (energy_mev <= 1.0e5) & (flux_per_mev > 0)
        axes[2].loglog(
            energy_mev[mask], flux_per_mev[mask], color=FAMILY_COLORS[family], ls=style, lw=1.55, label=label
        )
    cosmic_energy_kev: np.ndarray = data["cosmic_energy_kev"]  # type: ignore[assignment]
    cosmic_intensity: np.ndarray = data["cosmic_intensity_per_kev_sr"]  # type: ignore[assignment]
    sky_energy_mev = cosmic_energy_kev / 1000.0
    sky_flux_per_mev = cosmic_intensity * (2.0 * math.pi) * 1000.0
    sky_mask = (sky_energy_mev >= 0.1) & (sky_energy_mev <= 1.0e5) & (sky_flux_per_mev > 0)
    axes[2].loglog(
        sky_energy_mev[sky_mask],
        sky_flux_per_mev[sky_mask],
        color=FAMILY_COLORS["gamma"],
        ls=":",
        lw=1.35,
        label="天空 γ 代理",
    )
    moon_energy, moon_gamma = redmoon["secondary_gamma"]
    peak = int(np.argmax(moon_gamma))
    axes[2].scatter(
        [moon_energy[peak]], [moon_gamma[peak]], marker="*", s=88, color=FAMILY_COLORS["gamma"], edgecolor="white", linewidth=0.7, zorder=5
    )

    titles = (
        "38 km 大气气球场",
        "530 km 近赤道 LEO 代理",
        "裸露月面代理",
    )
    scope_notes = (
        "全空间角积分",
        "各组件原生角域积分；SAA略去",
        "REDMoon月壤上行 + 天空γ代理",
    )
    for ax, title, scope in zip(axes, titles, scope_notes):
        ax.set_title(title, pad=9, weight="bold")
        ax.set_xlim(1.0e-1, 1.0e5)
        ax.set_ylim(1.0e-14, 1.0e3)
        ax.set_xlabel("总动能 [MeV]")
        ax.text(0.03, 0.025, scope, transform=ax.transAxes, fontsize=8.2, color=MUTED, ha="left", va="bottom")
        ax.legend(loc="upper right", frameon=True, framealpha=0.94, ncol=1, borderpad=0.45, labelspacing=0.32)
    axes[0].set_ylabel(r"角域积分 $dF/dE$ [cm$^{-2}$ s$^{-1}$ MeV$^{-1}$]")

    fig.suptitle("瞬时入射粒子源谱：大气、LEO 与月面", fontsize=18, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.942,
        "源级比较 · 不含探测器响应、活化与延迟源 · 不跨粒子族绘制 Total",
        ha="center",
        va="top",
        fontsize=10.5,
        color=MUTED,
    )
    fig.text(
        0.5,
        0.012,
        "月面为 REDMoon 2019太阳极小 / Apollo-17月壤 / FTFP_BERT_HP；并非月球南极基地最终模型。LEO中子诊断代理未绘。",
        ha="center",
        va="bottom",
        fontsize=8.7,
        color=MUTED,
    )
    fig.subplots_adjust(left=0.07, right=0.99, top=0.86, bottom=0.13, wspace=0.08)
    save_figure(fig, "three_environment_prompt_components")


def plot_gamma_comparison(derived: dict[str, object]) -> None:
    balloon_energy: np.ndarray = derived["balloon_energy_kev"]  # type: ignore[assignment]
    balloon_flux: np.ndarray = derived["balloon_flux_per_kev"]  # type: ignore[assignment]
    leo_energy: np.ndarray = derived["leo_energy_kev"]  # type: ignore[assignment]
    leo_flux: np.ndarray = derived["leo_flux_per_kev"]  # type: ignore[assignment]
    moon_energy: np.ndarray = derived["moon_energy_kev"]  # type: ignore[assignment]
    moon_regolith: np.ndarray = derived["moon_regolith_flux_per_kev"]  # type: ignore[assignment]
    moon_total: np.ndarray = derived["moon_total_flux_per_kev"]  # type: ignore[assignment]
    band_values: dict[str, dict[str, float]] = derived["band_values"]  # type: ignore[assignment]
    totals: dict[str, float] = derived["totals"]  # type: ignore[assignment]
    line_flux = float(derived["line_flux_cm2_s"])

    fig = plt.figure(figsize=(12.8, 8.2))
    grid = fig.add_gridspec(2, 1, height_ratios=[2.45, 1.0], hspace=0.28)
    ax = fig.add_subplot(grid[0])
    band_ax = fig.add_subplot(grid[1])

    bm = (balloon_energy >= 100.0) & (balloon_energy <= 10000.0) & (balloon_flux > 0)
    lm = (leo_energy >= 100.0) & (leo_energy <= 10000.0) & (leo_flux > 0)
    mm = (moon_energy >= 100.0) & (moon_energy <= 10000.0) & (moon_total > 0)
    ax.loglog(
        balloon_energy[bm], balloon_energy[bm] * balloon_flux[bm], color=BALLOON, lw=2.15, ls="-", label="38 km 气球（全空间宽带 γ）"
    )
    ax.loglog(
        leo_energy[lm], leo_energy[lm] * leo_flux[lm], color=LEO, lw=2.05, ls="--", label="530 km LEO 连续谱代理"
    )
    ax.loglog(
        moon_energy[mm], moon_energy[mm] * moon_total[mm], color=MOON, lw=2.25, ls="-", label="裸露月面总 γ 代理"
    )
    ax.loglog(
        moon_energy[mm], moon_energy[mm] * moon_regolith[mm], color=MOON, lw=1.1, ls=":", alpha=0.82, label="其中：月壤上行 γ"
    )
    ax.axvspan(450.0, 600.0, color=MOON, alpha=0.075, zorder=0)
    ax.axvline(511.0, color="#3B4045", lw=1.0, ls=":", zorder=1)

    peak_index = int(np.argmax(moon_regolith[(moon_energy >= 100.0) & (moon_energy <= 10000.0)]))
    in_band_indices = np.where((moon_energy >= 100.0) & (moon_energy <= 10000.0))[0]
    peak_global = int(in_band_indices[peak_index])
    peak_x = moon_energy[peak_global]
    peak_y = moon_energy[peak_global] * moon_total[peak_global]
    ax.scatter([peak_x], [peak_y], marker="*", s=112, color=MOON, edgecolor="white", linewidth=0.8, zorder=5)
    ax.annotate(
        "REDMoon 原生 512.86 keV 节点\n有限能格峰，不代表仪器线宽",
        xy=(peak_x, peak_y),
        xytext=(790.0, 115.0),
        arrowprops={"arrowstyle": "->", "color": MOON, "lw": 1.0},
        fontsize=8.6,
        color=MOON,
        ha="left",
        va="top",
    )
    ax.text(
        0.985,
        0.96,
        f"LEO mono-511：积分通量 {line_flux:.6f} cm$^{{-2}}$ s$^{{-1}}$\n仅计入下方 450–600 keV 能带；上图不赋人为峰高",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.4,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": "#D5DADD", "alpha": 0.94, "pad": 4},
    )
    ax.set_xlim(100.0, 10000.0)
    ax.set_ylim(0.02, 350.0)
    ax.set_xlabel("入射 γ 能量 [keV]")
    ax.set_ylabel(r"$E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
    ax.legend(loc="lower left", frameon=True, framealpha=0.94, ncol=2)

    y_positions = np.arange(len(BANDS), dtype=float)
    offsets = {"balloon": -0.18, "leo": 0.0, "lunar_total": 0.18}
    plot_specs = (
        ("balloon", "气球", BALLOON, "o"),
        ("leo", "LEO", LEO, "^"),
        ("lunar_total", "月面", MOON, "s"),
    )
    for key, label, color, marker in plot_specs:
        values = np.asarray([band_values[band_id][key] for band_id, *_ in BANDS])
        band_ax.semilogx(
            values,
            y_positions + offsets[key],
            marker=marker,
            ms=7.0,
            lw=0,
            color=color,
            markeredgecolor="white",
            markeredgewidth=0.7,
            label=label,
        )
    for y in y_positions:
        band_ax.axhline(y, color=GRID, lw=0.8, ls=":", zorder=0)
    band_ax.axhspan(1.62, 2.38, color=MOON, alpha=0.055, zorder=0)
    band_ax.set_yticks(y_positions, [label for _, label, _, _ in BANDS])
    band_ax.invert_yaxis()
    band_ax.set_xlim(0.05, 40.0)
    band_ax.set_xlabel(r"能带积分 γ 通量 [cm$^{-2}$ s$^{-1}$]（对数轴）")
    band_ax.set_title("同一宽能带下的源级比较", loc="left", fontsize=11.2, weight="bold")
    band_ax.legend(loc="lower right", ncol=3, frameon=True, framealpha=0.94)
    proxy = band_values["450_600_keV_annihilation_region_proxy"]
    band_ax.text(
        0.985,
        0.94,
        f"450–600 keV：月面/气球 ≈ {proxy['lunar_total']/proxy['balloon']:.1f}×；月面/LEO ≈ {proxy['lunar_total']/proxy['leo']:.1f}×",
        transform=band_ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.7,
        color=TEXT,
    )

    fig.suptitle("γ 入射源谱：大气、LEO 与裸露月面", fontsize=17.5, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.948,
        "角域积分源通量 · 100 keV–10 MeV · 不含探测器响应、活化与延迟源",
        ha="center",
        va="top",
        color=MUTED,
        fontsize=10.3,
    )
    fig.text(
        0.5,
        0.008,
        f"0.1–10 MeV 积分：气球 {totals['balloon']:.3f}，LEO {totals['leo']:.3f}，月面 {totals['lunar_total']:.2f} cm$^{{-2}}$ s$^{{-1}}$。"
        " †450–600 keV 仅为湮灭区域代理。月面采用 REDMoon 2019太阳极小/Apollo-17月壤，并拼接2π天空γ代理。",
        ha="center",
        va="bottom",
        fontsize=8.4,
        color=MUTED,
    )
    fig.subplots_adjust(left=0.11, right=0.975, top=0.88, bottom=0.11)
    save_figure(fig, "gamma_balloon_leo_lunar_comparison")


def write_summary(derived: dict[str, object]) -> None:
    totals: dict[str, float] = derived["totals"]  # type: ignore[assignment]
    bands: dict[str, dict[str, float]] = derived["band_values"]  # type: ignore[assignment]
    proxy = bands["450_600_keV_annihilation_region_proxy"]
    summary = {
        "schema_version": 1,
        "status": "BUILT__SOURCE_INPUT_PROXY__VALIDATION_RECORDED_SEPARATELY",
        "authority_boundary": "prompt incident source comparison only; not detector background, activation, delayed response, sensitivity, or geometry authority",
        "lunar_model": {
            "model": "REDMoon",
            "epoch": "2019 solar minimum",
            "soil": "Apollo-17 profile",
            "geant4": "4.10.06.p01",
            "physics_list": "FTFP_BERT_HP",
            "public_dataset_doi": "10.5281/zenodo.5561427",
            "paper_doi": "10.1029/2021JE006930",
            "scope": "exposed lunar surface proxy; not final south-pole/base-site model",
        },
        "integrated_gamma_flux_cm2_s_100keV_10MeV": totals,
        "ratios_100keV_10MeV": {
            "lunar_total_to_balloon": totals["lunar_total"] / totals["balloon"],
            "lunar_total_to_leo": totals["lunar_total"] / totals["leo"],
        },
        "annihilation_region_proxy_450_600keV": {
            **proxy,
            "lunar_total_to_balloon": proxy["lunar_total"] / proxy["balloon"],
            "lunar_total_to_leo": proxy["lunar_total"] / proxy["leo"],
            "warning": "broad-band proxy, not a narrow 511-keV line-flux ratio",
        },
        "leo_mono_511_integrated_flux_cm2_s": float(derived["line_flux_cm2_s"]),
        "redmoon_peak_native_node": {
            "energy_keV": 512.86,
            "differential_flux_cm2_s_MeV": 325.06,
            "warning": "finite tabulated node; not an intrinsic or detector line width",
        },
        "omissions": [
            "activation and delayed radiation",
            "SEP events",
            "LEO SAA",
            "local lunar base, lander, RTG, reactor, and structural materials",
            "final south-pole soil, ice, terrain, and horizon model",
        ],
        "input_sha256": {
            str(path.relative_to(REPO_ROOT)): digest for path, digest in EXPECTED_INPUT_SHA256.items()
        },
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    require_pinned_inputs()
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    data = load_inputs()
    derived = build_lunar_tables(data)
    plot_three_environment_components(data, derived)
    plot_gamma_comparison(derived)
    write_summary(derived)
    print(f"Built lunar source comparison in {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
