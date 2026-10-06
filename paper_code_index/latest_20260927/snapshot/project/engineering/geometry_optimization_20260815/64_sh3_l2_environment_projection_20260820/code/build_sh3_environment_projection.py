#!/usr/bin/env python3
"""Reweight the retained SH3 background response to balloon/LEO/Moon/L2 spectra.

This is a source-spectrum response projection.  It reuses the exact SH3
prompt survivors and the exact activation parent-volume-state keys, but it is
not a replacement for environment-matched prompt -> activation -> delayed
transport.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_sh3_l2_mpl"))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
BASE = ROOT / "engineering/satellite_leo530_source_comparison_20260813"
LUNAR = ROOT / "engineering/lunar_surface_source_comparison_20260813"
CATALOG_SUMMARY = ROOT / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json"
CATEGORY_REGISTRY = ROOT / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/category_registry.json"
DIRECT_CUTFLOW = ROOT / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow.csv"
MISSION = ROOT / "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json"
MISSION_TIMELINE = ROOT / "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv"
DELAYED_SELECTED = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/"
    "optv3_delayed_selected_events.csv"
)
ACTIVATION = PACKAGE / "outputs/tables/sh3_activation_selected_key_primary_energy.csv.gz"
ACTIVATION_SUMMARY = PACKAGE / "data/activation_primary_energy_scan_summary.json"
TABLES = PACKAGE / "outputs/tables"
FIGURES = PACKAGE / "outputs/figures"
SUMMARY = PACKAGE / "outputs/summary.json"

ENVIRONMENTS = (
    "balloon_38km",
    "leo530_quiet_proxy",
    "lunar_surface_proxy",
    "sun_earth_l2_quiet_1au_proxy",
)
FAMILIES = ("gamma", "p", "n", "alpha", "eplus", "eminus", "muminus", "muplus")
PLOT_FAMILIES = ("gamma", "eminus", "eplus", "p", "alpha", "n")
RESPONSE_PANELS = ("gamma", "eplus", "p", "alpha", "n")
ENV_LABEL = {
    "balloon_38km": "38 km 大气",
    "leo530_quiet_proxy": "530 km LEO",
    "lunar_surface_proxy": "月面",
    "sun_earth_l2_quiet_1au_proxy": "日–地 L2",
}
ENV_SHORT = {
    "balloon_38km": "大气",
    "leo530_quiet_proxy": "LEO",
    "lunar_surface_proxy": "月面",
    "sun_earth_l2_quiet_1au_proxy": "L2",
}
ENV_COLOR = {
    "balloon_38km": "#2C4054",
    "leo530_quiet_proxy": "#D97706",
    "lunar_surface_proxy": "#168A93",
    "sun_earth_l2_quiet_1au_proxy": "#7A4CB3",
}
ENV_STYLE = {
    "balloon_38km": "-",
    "leo530_quiet_proxy": "--",
    "lunar_surface_proxy": ":",
    "sun_earth_l2_quiet_1au_proxy": "-.",
}
FAMILY_LABEL = {
    "gamma": "γ",
    "p": "p",
    "n": "n",
    "alpha": "α",
    "eplus": r"$e^+$",
    "eminus": r"$e^-$",
    "muminus": r"$\mu^-$",
    "muplus": r"$\mu^+$",
}
FAMILY_CN = {
    "gamma": "γ 光子",
    "eplus": "正电子",
    "p": "质子",
    "alpha": "α 粒子",
    "n": "中子",
}
FAMILY_COLOR = {
    "gamma": "#2468BD",
    "p": "#239344",
    "n": "#7450B2",
    "alpha": "#7D8B1B",
    "eplus": "#CC5B91",
    "eminus": "#E07A16",
    "muminus": "#6F747A",
    "muplus": "#A0A4A8",
}
T_SECONDS = 20.0 * 86400.0
FULL_SKY_SR = 4.0 * math.pi
LEO_RC_GV = 12.6
FINAL_BIT = 1 << 4


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fields: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"Refusing to write empty table: {path}")
    names = list(fields) if fields is not None else list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=names, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_excitation(value: float | str) -> float:
    rounded = round(float(value) + 0.0, 2)
    return 0.0 if rounded == 0.0 else rounded


@dataclass(frozen=True)
class Curve:
    energy_keV: np.ndarray
    value_per_keV: np.ndarray
    interpolation: str = "loglog"

    def __post_init__(self) -> None:
        if len(self.energy_keV) < 2 or np.any(np.diff(self.energy_keV) <= 0):
            raise ValueError("curve energy must be strictly increasing")
        if np.any(self.value_per_keV < 0) or np.any(~np.isfinite(self.value_per_keV)):
            raise ValueError("curve values must be finite and nonnegative")

    def at(self, energy_keV: float | np.ndarray) -> float | np.ndarray:
        target = np.asarray(energy_keV, dtype=float)
        out = np.zeros_like(target)
        inside = (target >= self.energy_keV[0]) & (target <= self.energy_keV[-1])
        if self.interpolation == "linear":
            out[inside] = np.interp(target[inside], self.energy_keV, self.value_per_keV)
        elif self.interpolation == "nearest_log_bin":
            edges = np.sqrt(self.energy_keV[:-1] * self.energy_keV[1:])
            idx = np.searchsorted(edges, target[inside], side="right")
            out[inside] = self.value_per_keV[idx]
        else:
            positive = self.value_per_keV > 0
            if np.count_nonzero(positive) >= 2:
                x = self.energy_keV[positive]
                y = self.value_per_keV[positive]
                valid = inside & (target >= x[0]) & (target <= x[-1])
                out[valid] = np.exp(np.interp(np.log(target[valid]), np.log(x), np.log(y)))
        if np.ndim(energy_keV) == 0:
            return float(out)
        return out


def curve_from_rows(
    rows: list[dict[str, str]],
    x_field: str,
    y_field: str,
    *,
    x_scale: float = 1.0,
    y_scale: float = 1.0,
    interpolation: str = "loglog",
) -> Curve:
    grouped: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(x_field, "") == "" or row.get(y_field, "") == "":
            continue
        x = float(row[x_field]) * x_scale
        y = float(row[y_field]) * y_scale
        if x > 0 and y >= 0 and math.isfinite(x) and math.isfinite(y):
            grouped[x].append(y)
    energy = np.asarray(sorted(grouped), dtype=float)
    values = np.asarray([float(np.mean(grouped[x])) for x in energy], dtype=float)
    return Curve(energy, values, interpolation)


def rigidity_gv(family: str, energy_keV_total: float | np.ndarray) -> np.ndarray:
    kinetic = np.asarray(energy_keV_total, dtype=float) * 1.0e-6
    if family == "p":
        mass, charge = 0.9382720813, 1.0
    elif family == "alpha":
        mass, charge = 4.0 * 0.9382720813, 2.0
    elif family in ("eminus", "eplus"):
        mass, charge = 0.00051099895, 1.0
    else:
        raise KeyError(family)
    return np.sqrt(kinetic * kinetic + 2.0 * kinetic * mass) / charge


def geomagnetic_transmission(family: str, energy_keV_total: float | np.ndarray) -> np.ndarray:
    rigidity = rigidity_gv(family, energy_keV_total)
    exponent = 12.0 if family in ("p", "alpha") else 6.0
    with np.errstate(over="ignore", divide="ignore"):
        return 1.0 / (1.0 + np.power(rigidity / LEO_RC_GV, -exponent))


class SourceModels:
    def __init__(self) -> None:
        balloon_rows = read_csv(BASE / "outputs/tables/balloon_aggregated_spectra.csv")
        leo_rows = read_csv(BASE / "outputs/tables/satellite_profile_spectra.csv")
        component_rows = read_csv(BASE / "outputs/tables/satellite_component_spectra.csv")
        lunar_rows = read_csv(LUNAR / "outputs/tables/lunar_prompt_components.csv")
        lunar_gamma = read_csv(LUNAR / "outputs/tables/three_environment_gamma_spectra.csv")
        self.balloon: dict[str, Curve] = {}
        self.leo: dict[str, Curve] = {}
        self.l2: dict[str, Curve] = {}
        self.l2_rows: list[dict[str, object]] = []
        self.lunar_components: dict[str, list[Curve]] = defaultdict(list)

        for family in FAMILIES:
            selected = [row for row in balloon_rows if row["family"] == family and row["domain"] == "full"]
            if selected:
                self.balloon[family] = curve_from_rows(
                    selected, "energy_keV_total", "differential_flux_cm2_s_keV", interpolation="linear"
                )
            selected = [row for row in leo_rows if row["family"] == family]
            if selected:
                self.leo[family] = curve_from_rows(
                    selected,
                    "energy_keV_total",
                    "validity_filtered_differential_flux_cm2_s_keV",
                    interpolation="loglog",
                )

        gamma_selected = [
            row
            for row in lunar_gamma
            if row["environment"] == "lunar_surface_proxy"
            and row["component"] == "total_prompt_gamma_proxy"
        ]
        self.lunar_components["gamma"].append(
            curve_from_rows(
                gamma_selected,
                "energy_keV_total",
                "differential_flux_cm2_s_keV",
                interpolation="nearest_log_bin",
            )
        )
        lunar_meta = {
            "gcr_proton_reference": "p",
            "secondary_proton": "p",
            "secondary_neutron": "n",
            "secondary_electron_positron": "epm",
        }
        for component, family in lunar_meta.items():
            selected = [row for row in lunar_rows if row["component"] == component]
            self.lunar_components[family].append(
                curve_from_rows(
                    selected,
                    "energy_MeV_total",
                    "differential_flux_cm2_s_MeV",
                    x_scale=1000.0,
                    y_scale=1.0 / 1000.0,
                    interpolation="nearest_log_bin",
                )
            )

        component_for_family = {
            "gamma": "cosmic_photons",
            "p": "primary_proton",
            "alpha": "primary_alpha",
            "eminus": "primary_electron",
            "eplus": "primary_positron",
        }
        for family, component in component_for_family.items():
            selected = [
                row
                for row in component_rows
                if row["component_id"] == component and row["within_cited_model_validity"].lower() == "true"
            ]
            rows = []
            for row in selected:
                energy = float(row["energy_keV_total"])
                leo_intensity = float(row["support_avg_intensity_cm2_s_sr_keV"])
                if family == "gamma":
                    transmission = 1.0
                else:
                    transmission = float(geomagnetic_transmission(family, energy))
                value = FULL_SKY_SR * leo_intensity / transmission if transmission > 0 else 0.0
                rows.append(
                    {
                        "environment": "sun_earth_l2_quiet_1au_proxy",
                        "component": component,
                        "family": family,
                        "angular_domain": "full_sphere_4pi",
                        "solid_angle_sr": FULL_SKY_SR,
                        "energy_keV_total": energy,
                        "leo_geomagnetic_transmission_at_12p6GV": transmission,
                        "differential_flux_cm2_s_keV": value,
                        "construction": (
                            "COSI cosmic-photon intensity x 4pi"
                            if family == "gamma"
                            else "COSI 1-AU primary spectrum recovered by removing LEO geomagnetic transmission x 4pi"
                        ),
                    }
                )
            self.l2_rows.extend(rows)
            self.l2[family] = curve_from_rows(
                [{k: str(v) for k, v in row.items()} for row in rows],
                "energy_keV_total",
                "differential_flux_cm2_s_keV",
                interpolation="loglog",
            )

    @staticmethod
    def zero_like(energy_keV: float | np.ndarray) -> float | np.ndarray:
        target = np.asarray(energy_keV, dtype=float)
        out = np.zeros_like(target)
        return float(out) if np.ndim(energy_keV) == 0 else out

    def target_flux(self, environment: str, family: str, energy_keV: float | np.ndarray) -> float | np.ndarray:
        if environment == "balloon_38km":
            curve = self.balloon.get(family)
            return curve.at(energy_keV) if curve is not None else self.zero_like(energy_keV)
        if environment == "leo530_quiet_proxy":
            curve = self.leo.get(family)
            return curve.at(energy_keV) if curve is not None else self.zero_like(energy_keV)
        if environment == "sun_earth_l2_quiet_1au_proxy":
            curve = self.l2.get(family)
            return curve.at(energy_keV) if curve is not None else self.zero_like(energy_keV)
        if environment != "lunar_surface_proxy":
            raise KeyError(environment)

        target = np.asarray(energy_keV, dtype=float)
        if family in self.lunar_components:
            out = np.zeros_like(target)
            for curve in self.lunar_components[family]:
                out += np.asarray(curve.at(target))
        elif family in ("eplus", "eminus"):
            out = np.zeros_like(target)
            for curve in self.lunar_components["epm"]:
                out += 0.5 * np.asarray(curve.at(target))
        elif family == "alpha":
            p_energy = target / 4.0
            lunar_p = np.zeros_like(target)
            for curve in self.lunar_components["p"]:
                lunar_p += np.asarray(curve.at(p_energy))
            balloon_p = np.asarray(self.balloon["p"].at(p_energy))
            ratio = np.divide(lunar_p, balloon_p, out=np.zeros_like(target), where=balloon_p > 0)
            out = np.asarray(self.balloon["alpha"].at(target)) * ratio
        elif family in ("muminus", "muplus"):
            out = np.asarray(self.balloon[family].at(target))
        else:
            out = np.zeros_like(target)
        return float(out) if np.ndim(energy_keV) == 0 else out

    def ratio(self, environment: str, family: str, energy_keV: float) -> tuple[float, str]:
        if environment == "balloon_38km":
            return 1.0, "DIRECT_SH3_BALLOON_REFERENCE"
        denominator_curve = self.balloon.get(family)
        denominator = float(denominator_curve.at(energy_keV)) if denominator_curve is not None else 0.0
        if denominator <= 0:
            return 0.0, "OUTSIDE_BALLOON_REFERENCE_SUPPORT"
        numerator = float(self.target_flux(environment, family, energy_keV))
        if environment == "sun_earth_l2_quiet_1au_proxy" and family in ("n", "muminus", "muplus"):
            return 0.0, "L2_NO_PLANETARY_ALBEDO_NEUTRON_OR_ATMOSPHERIC_MUON_COMPONENT"
        if environment == "sun_earth_l2_quiet_1au_proxy" and family in ("p", "alpha", "eminus", "eplus"):
            status = "L2_COSI_1AU_PRIMARY__LEO_GEOMAGNETIC_FILTER_REMOVED__4PI"
        elif environment == "sun_earth_l2_quiet_1au_proxy" and family == "gamma":
            status = "L2_COSI_COSMIC_PHOTON_INTENSITY__4PI"
        elif environment == "leo530_quiet_proxy" and family == "n":
            status = "LEO_10GV_NEUTRON_DIAGNOSTIC_PROXY"
        elif environment == "leo530_quiet_proxy" and family in ("muminus", "muplus"):
            status = "LEO_MUON_UNAVAILABLE_AS_ZERO"
        elif environment == "lunar_surface_proxy" and family == "alpha":
            status = "LUNAR_ALPHA_PROTON_TRANSFER_PROXY"
        elif environment == "lunar_surface_proxy" and family in ("eplus", "eminus"):
            status = "LUNAR_EPM_EQUAL_CHARGE_SPLIT_PROXY"
        elif environment == "lunar_surface_proxy" and family in ("muminus", "muplus"):
            status = "LUNAR_MUON_BALLOON_CARRY_FORWARD_PLACEHOLDER"
        else:
            status = "SOURCE_SPECTRUM_DIRECT__ANGULAR_DOMAIN_INTEGRATED"
        if numerator == 0.0 and status.startswith(("L2_COSI", "SOURCE_")):
            status = "TARGET_MODEL_OUTSIDE_CITED_SUPPORT_AS_ZERO"
        return numerator / denominator, status


def parse_prompt_init(line: str) -> tuple[float, float, float, float]:
    fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
    if len(fields) < 23:
        raise RuntimeError(f"Malformed prompt IA INIT: {line.rstrip()}")
    energy = float(fields[22])
    dx, dy, dz = float(fields[16]), float(fields[17]), float(fields[18])
    return energy, dx, dy, dz


def extract_prompt_rows(models: SourceModels) -> list[dict[str, object]]:
    registry = json.loads(CATEGORY_REGISTRY.read_text(encoding="utf-8"))["categories"]
    official_weight = {
        str(row["family"]): float(row["base_event_weight_cps"])
        for row in registry
        if row["stream"] == "prompt"
    }
    rows: list[dict[str, object]] = []
    # The retained merged catalog reuses four early-round compact catalogs from
    # outputs/01.  Its summary is therefore the complete authority for catalog
    # paths; walking only the current job_catalogs directory silently omits one
    # of the 12 official prompt W2 survivors.
    catalog_summary = json.loads(CATALOG_SUMMARY.read_text(encoding="utf-8"))
    prompt_metas = [
        meta
        for meta in sorted(catalog_summary["jobs"], key=lambda row: int(row["scan_index"]))
        if meta.get("stream") == "prompt"
    ]

    # A completed raw-SIM join is a reusable semantic checkpoint: validate its
    # event identity against the compact catalogs, then refresh every spectrum
    # ratio and official merged-catalog weight.  This avoids repeatedly
    # decompressing the same large SIM files during plot/PPT iterations.
    checkpoint = TABLES / "sh3_prompt_w2_primary_energy.csv"
    expected: dict[tuple[str, int], tuple[str, float, str]] = {}
    for meta in prompt_metas:
        with np.load(meta["catalog_path"], allow_pickle=False) as data:
            selected = np.flatnonzero((data["w2_flags"] & FINAL_BIT) != 0)
            for index in selected:
                key = (str(meta["job_id"]), int(data["event_id"][index]))
                expected[key] = (
                    str(meta["family"]),
                    float(data["measured_total_keV"][index]),
                    str(meta["sim_path"]),
                )
    if checkpoint.is_file():
        cached = read_csv(checkpoint)
        cached_keys = {(row["job_id"], int(row["event_id"])) for row in cached}
        if cached_keys == set(expected):
            for cached_row in cached:
                key = (cached_row["job_id"], int(cached_row["event_id"]))
                family, measured, source_file = expected[key]
                if not math.isclose(float(cached_row["measured_total_keV"]), measured, rel_tol=0.0, abs_tol=2.0e-5):
                    raise RuntimeError(f"Prompt checkpoint measured-energy mismatch: {key}")
                row: dict[str, object] = {
                    "job_id": key[0],
                    "family": family,
                    "event_id": key[1],
                    "primary_energy_keV_total": float(cached_row["primary_energy_keV_total"]),
                    "primary_energy_MeV_total": float(cached_row["primary_energy_MeV_total"]),
                    "primary_dir_x": float(cached_row["primary_dir_x"]),
                    "primary_dir_y": float(cached_row["primary_dir_y"]),
                    "primary_dir_z": float(cached_row["primary_dir_z"]),
                    "measured_total_keV": measured,
                    "event_weight_cps": official_weight[family],
                    "source_file": source_file,
                    "primary_energy_provenance": "REUSED_SEMANTIC_CHECKPOINT__EVENT_ID_AND_MEASURED_ENERGY_REVALIDATED",
                }
                for environment in ENVIRONMENTS:
                    ratio, status = models.ratio(environment, family, float(row["primary_energy_keV_total"]))
                    row[f"{environment}_source_ratio"] = ratio
                    row[f"{environment}_mapping_status"] = status
                rows.append(row)
            rows.sort(key=lambda row: (str(row["job_id"]), int(row["event_id"])))
            return rows

    for meta in prompt_metas:
        npz_path = Path(meta["catalog_path"])
        with np.load(npz_path, allow_pickle=False) as data:
            mask = (data["w2_flags"] & FINAL_BIT) != 0
            ids = data["event_id"][mask].astype(int)
            measured = data["measured_total_keV"][mask].astype(float)
        if not len(ids):
            continue
        wanted = {int(event_id): float(value) for event_id, value in zip(ids, measured)}
        found: dict[int, tuple[float, float, float, float]] = {}
        current_id: int | None = None
        with gzip.open(meta["sim_path"], "rt", encoding="utf-8", errors="strict") as stream:
            for raw in stream:
                if raw.startswith("ID "):
                    parts = raw.split()
                    current_id = int(parts[1]) if len(parts) >= 2 else None
                elif current_id in wanted and raw.startswith("IA INIT"):
                    if current_id in found:
                        raise RuntimeError(f"Multiple prompt INIT records: {meta['job_id']} event {current_id}")
                    found[current_id] = parse_prompt_init(raw)
        if set(found) != set(wanted):
            raise RuntimeError(f"Prompt INIT closure failed for {meta['job_id']}: {len(found)}/{len(wanted)}")
        for event_id in sorted(found):
            energy, dx, dy, dz = found[event_id]
            row: dict[str, object] = {
                "job_id": meta["job_id"],
                "family": meta["family"],
                "event_id": event_id,
                "primary_energy_keV_total": energy,
                "primary_energy_MeV_total": energy / 1000.0,
                "primary_dir_x": dx,
                "primary_dir_y": dy,
                "primary_dir_z": dz,
                "measured_total_keV": wanted[event_id],
                "event_weight_cps": official_weight[str(meta["family"])],
                "source_file": meta["sim_path"],
                "primary_energy_provenance": "EXACT_RAW_SIM_IA_INIT_JOIN",
            }
            for environment in ENVIRONMENTS:
                ratio, status = models.ratio(environment, str(meta["family"]), energy)
                row[f"{environment}_source_ratio"] = ratio
                row[f"{environment}_mapping_status"] = status
            rows.append(row)
    rows.sort(key=lambda row: (str(row["job_id"]), int(row["event_id"])))
    return rows


def load_activation() -> dict[tuple[str, str, int, float], list[float]]:
    grouped: dict[tuple[str, str, int, float], list[float]] = defaultdict(list)
    with gzip.open(ACTIVATION, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (
                row["incident_family"],
                row["source_volume"],
                int(row["source_parent_ZA"]),
                canonical_excitation(row["source_excitation_keV"]),
            )
            grouped[key].append(float(row["primary_energy_keV_total"]))
    return grouped


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    if len(values) == 0 or np.sum(weights) <= 0:
        return math.nan
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cdf = np.cumsum(sorted_weights) / np.sum(sorted_weights)
    return float(np.interp(q, cdf, sorted_values))


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 220,
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans CJK JP", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#D7DDE4",
            "grid.alpha": 0.8,
            "grid.linestyle": ":",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def positive_plot(ax: plt.Axes, x: np.ndarray, y: np.ndarray, **kwargs: object) -> None:
    mask = np.isfinite(y) & (y > 0)
    if np.count_nonzero(mask) >= 2:
        ax.plot(x[mask], y[mask], **kwargs)


def plot_full_spectra(models: SourceModels) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(16, 6.25), sharex=True, sharey=True)
    grid_keV = np.logspace(2, 8, 650)
    styles = {"gamma": "-", "eminus": "--", "eplus": "-.", "p": "-", "alpha": ":", "n": "--"}
    for ax, environment in zip(axes, ENVIRONMENTS):
        for family in PLOT_FAMILIES:
            flux = np.asarray(models.target_flux(environment, family, grid_keV), dtype=float)
            positive_plot(
                ax,
                grid_keV / 1000.0,
                grid_keV * flux,
                color=FAMILY_COLOR[family],
                linestyle=styles[family],
                linewidth=2.0,
            )
        ax.axvline(0.511, color="#73808C", linewidth=0.8, linestyle=":")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(1.0e-1, 1.0e5)
        ax.set_ylim(1.0e-9, 1.0e3)
        ax.set_title(ENV_LABEL[environment], fontweight="bold", fontsize=13)
        ax.set_xlabel("初级粒子总动能 [MeV]")
    axes[0].set_ylabel(r"角域积分 $E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")
    fig.suptitle("大气、LEO、月面与日–地 L2 主要连续入射粒子谱", x=0.045, ha="left", fontsize=20, fontweight="bold")
    fig.text(
        0.045,
        0.91,
        "统一使用总动能与角域积分通量；L2 为 1 AU 静态 GCR/宇宙 γ 基线，不含 SEP。",
        color="#596673",
        fontsize=11.5,
    )
    handles = [
        Line2D([0], [0], color=FAMILY_COLOR[family], linestyle=styles[family], linewidth=2.2, label=FAMILY_LABEL[family])
        for family in PLOT_FAMILIES
    ]
    handles.append(Line2D([0], [0], color="#73808C", linestyle=":", linewidth=1, label="511 keV 位置"))
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False, bbox_to_anchor=(0.53, 0.075))
    fig.text(
        0.045,
        0.015,
        "[1] EXPACS/PARMA  [2] COSI DC4 / Cumani+2019  [3] REDMoon / Dobynde & Guo 2021  "
        "[4] L2：COSI 1 AU primary 去 12.6 GV 地磁滤波并扩展至 4π；深空 GCR 语义参照 BON2020",
        fontsize=8.4,
        color="#596673",
    )
    fig.subplots_adjust(left=0.055, right=0.985, top=0.82, bottom=0.19, wspace=0.10)
    save_figure(fig, "02_full_spectrum_comparison_sh3_l2")


def format_energy_interval(low_mev: float, high_mev: float) -> str:
    if high_mev >= 1000.0:
        return f"{low_mev / 1000.0:.2g}–{high_mev / 1000.0:.2g} GeV"
    return f"{low_mev:.3g}–{high_mev:.3g} MeV"


def plot_response_bands(models: SourceModels, bands: list[dict[str, object]]) -> None:
    band_by_family = {str(row["family"]): row for row in bands}
    fig = plt.figure(figsize=(15, 8.3))
    grid = fig.add_gridspec(2, 3, left=0.055, right=0.985, top=0.83, bottom=0.09, wspace=0.28, hspace=0.48)
    positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
    xlimits = {
        "gamma": (1.0e-1, 1.0e4),
        "eplus": (1.0e0, 1.0e5),
        "p": (1.0e1, 1.0e6),
        "alpha": (1.0e2, 1.0e6),
        "n": (1.0e-2, 1.0e6),
    }
    for family, position in zip(RESPONSE_PANELS, positions):
        ax = fig.add_subplot(grid[position])
        xmin, xmax = xlimits[family]
        energy_mev = np.logspace(math.log10(xmin), math.log10(xmax), 600)
        energy_keV = energy_mev * 1000.0
        plotted_values = []
        for environment in ENVIRONMENTS:
            flux = np.asarray(models.target_flux(environment, family, energy_keV), dtype=float)
            y = energy_keV * flux
            positive_plot(
                ax,
                energy_mev,
                y,
                color=ENV_COLOR[environment],
                linestyle=ENV_STYLE[environment],
                linewidth=2.1,
            )
            plotted_values.extend(y[y > 0].tolist())
        band = band_by_family[family]
        low = float(band["response_weighted_primary_energy_p10_MeV"])
        high = float(band["response_weighted_primary_energy_p90_MeV"])
        ax.axvspan(low, high, color=FAMILY_COLOR[family], alpha=0.14)
        ax.axvline(low, color=FAMILY_COLOR[family], alpha=0.7, linewidth=0.9)
        ax.axvline(high, color=FAMILY_COLOR[family], alpha=0.7, linewidth=0.9)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(xmin, xmax)
        if plotted_values:
            positive = np.asarray(plotted_values)
            ax.set_ylim(max(float(np.nanmin(positive)) / 3.0, 1.0e-12), float(np.nanmax(positive)) * 3.0)
        ax.set_title(FAMILY_CN[family], loc="left", color=FAMILY_COLOR[family], fontweight="bold", fontsize=13)
        ax.set_xlabel("初级粒子总动能 [MeV]")
        ax.set_ylabel(r"角域积分 $E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
        fraction_percent = 100.0 * float(band["fraction_of_balloon_W2_final"])
        fraction_text = f"{fraction_percent:.2f}%" if fraction_percent < 0.1 else f"{fraction_percent:.1f}%"
        ax.text(
            0.03,
            0.91,
            f"{format_energy_interval(low, high)}  ·  SH3 本底贡献 {fraction_text}",
            transform=ax.transAxes,
            color=FAMILY_COLOR[family],
            fontsize=9.5,
            bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 1.5},
        )
    legend_ax = fig.add_subplot(grid[1, 2])
    legend_ax.axis("off")
    handles = [
        Line2D([0], [0], color=ENV_COLOR[env], linestyle=ENV_STYLE[env], linewidth=2.4, label=ENV_LABEL[env])
        for env in ENVIRONMENTS
    ]
    handles.append(Patch(facecolor="#C7CED6", alpha=0.45, label="SH3 响应加权 10–90% 能区"))
    legend_ax.legend(handles=handles, loc="center left", frameon=False, fontsize=11, handlelength=3.3)
    fig.suptitle("四种环境入射谱与 SH3 主要本底能区", x=0.035, ha="left", fontsize=20, fontweight="bold")
    fig.text(
        0.035,
        0.885,
        "曲线为环境源谱；阴影由 SH3 的 12 个 prompt 与 111 个 delayed 末级事件反推。",
        fontsize=11.5,
        color="#596673",
    )
    save_figure(fig, "01_background_energy_bands_sh3_l2")


def plot_performance(estimates: list[dict[str, object]]) -> None:
    by_env = {str(row["environment"]): row for row in estimates}
    labels = [ENV_SHORT[env] for env in ENVIRONMENTS]
    values = [float(by_env[env]["mission_relative_F3_to_SH3_balloon_including_signal_transmission"]) for env in ENVIRONMENTS]
    absolute = [float(by_env[env]["estimated_20d_F3_ph_cm2_s"]) for env in ENVIRONMENTS]
    errors = [
        float(by_env[env]["estimated_20d_F3_conditional_MC_sigma_ph_cm2_s"])
        / float(by_env[env]["SH3_balloon_official_F3_ph_cm2_s"])
        for env in ENVIRONMENTS
    ]
    colors = [ENV_COLOR[env] for env in ENVIRONMENTS]
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(values))
    bars = ax.bar(
        x,
        values,
        width=0.58,
        color=colors,
        yerr=errors,
        capsize=4,
        error_kw={"elinewidth": 1.0, "ecolor": "#4A535C", "capthick": 1.0},
    )
    ax.axhline(1.0, color="#7D8790", linewidth=1.0, linestyle="--")
    ax.set_xticks(x, labels, fontsize=12)
    ax.set_ylabel("相对 SH3 气球 20 天最小可分辨通量（越低越好）")
    ax.set_ylim(0, max(values) * 1.24)
    for bar, value, flux in zip(bars, values, absolute):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(values) * 0.025,
            f"{value:.2f}×\n{flux:.2e}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )
    ax.set_title("SH3 同质量模型四环境 511 keV 性能估算", fontsize=18, fontweight="bold", loc="left", pad=18)
    ax.text(
        0.0,
        1.01,
        "数值第二行为 20 天、3σ 估算 [ph cm^-2 s^-1]；误差棒为有限响应样本条件统计。",
        transform=ax.transAxes,
        fontsize=10.5,
        color="#596673",
    )
    ax.text(
        0.0,
        -0.16,
        "源谱重加权代理：同 Aeff/曝光；非气球环境无大气衰减；未重跑匹配输运，未含 L2 SEP/重离子、LEO SAA。",
        transform=ax.transAxes,
        fontsize=9.2,
        color="#596673",
    )
    fig.subplots_adjust(left=0.12, right=0.98, top=0.83, bottom=0.22)
    save_figure(fig, "03_normalized_minimum_detectable_flux_sh3_l2")


def main() -> int:
    required = [
        ACTIVATION,
        ACTIVATION_SUMMARY,
        DIRECT_CUTFLOW,
        MISSION,
        MISSION_TIMELINE,
        DELAYED_SELECTED,
        BASE / "data/validation.json",
        LUNAR / "data/validation.json",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing required input: {path}")
    scan_summary = json.loads(ACTIVATION_SUMMARY.read_text(encoding="utf-8"))
    if scan_summary.get("status") != "PASS__SH3_SELECTED_ACTIVATION_KEYS_EXACT_PRIMARY_ENERGY_JOIN":
        raise RuntimeError("SH3 activation primary-energy join is not PASS")
    mission = json.loads(MISSION.read_text(encoding="utf-8"))
    if mission.get("status") != "PASS__SH3_OPTV3_M05_FIXED_MATURE_TIMELINE_20D":
        raise RuntimeError("SH3 M05 fixed mature timeline is not PASS")

    models = SourceModels()
    write_csv(TABLES / "l2_source_spectra.csv", models.l2_rows)
    l2_source_integrals: dict[str, dict[str, float | int]] = {}
    for family in ("gamma", "p", "alpha", "eminus", "eplus"):
        rows = [row for row in models.l2_rows if row["family"] == family]
        energy = np.asarray([float(row["energy_keV_total"]) for row in rows], dtype=float)
        flux = np.asarray([float(row["differential_flux_cm2_s_keV"]) for row in rows], dtype=float)
        l2_source_integrals[family] = {
            "nodes": len(rows),
            "support_min_MeV_total": float(np.min(energy) / 1000.0),
            "support_max_MeV_total": float(np.max(energy) / 1000.0),
            "integrated_flux_over_model_support_cm2_s": float(np.trapezoid(flux, energy)),
        }

    prompt_rows = extract_prompt_rows(models)
    if len(prompt_rows) != 12:
        raise RuntimeError(f"Unexpected SH3 prompt W2-final event count: {len(prompt_rows)}")
    write_csv(TABLES / "sh3_prompt_w2_primary_energy.csv", prompt_rows)

    activation = load_activation()
    delayed_rows = read_csv(DELAYED_SELECTED)
    if len(delayed_rows) != 111:
        raise RuntimeError(f"Unexpected SH3 delayed W2-final event count: {len(delayed_rows)}")

    key_ratio: dict[tuple[str, tuple[str, str, int, float]], float] = {}
    activation_key_rows: list[dict[str, object]] = []
    for key, energies_list in sorted(activation.items()):
        family, volume, za, excitation = key
        energies = np.asarray(energies_list, dtype=float)
        for environment in ENVIRONMENTS:
            ratios_and_status = [models.ratio(environment, family, float(energy)) for energy in energies]
            ratios = np.asarray([item[0] for item in ratios_and_status], dtype=float)
            statuses = Counter(item[1] for item in ratios_and_status)
            mean_ratio = float(np.mean(ratios))
            key_ratio[(environment, key)] = mean_ratio
            activation_key_rows.append(
                {
                    "environment": environment,
                    "incident_family": family,
                    "source_volume": volume,
                    "source_parent_ZA": za,
                    "source_excitation_keV": excitation,
                    "rp_records": len(energies),
                    "primary_energy_p10_MeV": weighted_quantile(energies / 1000.0, np.ones(len(energies)), 0.10),
                    "primary_energy_p50_MeV": weighted_quantile(energies / 1000.0, np.ones(len(energies)), 0.50),
                    "primary_energy_p90_MeV": weighted_quantile(energies / 1000.0, np.ones(len(energies)), 0.90),
                    "production_ratio_to_balloon": mean_ratio,
                    "ratio_rms": float(np.sqrt(np.mean(ratios * ratios))),
                    "mapping_status_counts": json.dumps(dict(sorted(statuses.items())), sort_keys=True),
                }
            )
    write_csv(TABLES / "sh3_activation_key_energy_response.csv", activation_key_rows)
    l2_activation_mapping_status = Counter()
    for row in activation_key_rows:
        if row["environment"] == "sun_earth_l2_quiet_1au_proxy":
            l2_activation_mapping_status.update(json.loads(str(row["mapping_status_counts"])))

    component: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0}
    )
    delayed_event_contributions: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        for row in prompt_rows:
            family = str(row["family"])
            ratio = float(row[f"{environment}_source_ratio"])
            projected = float(row["event_weight_cps"]) * ratio
            target = component[(environment, "prompt", family)]
            target["events"] += 1
            target["rate"] += projected
            target["variance"] += projected * projected
        for row in delayed_rows:
            family = row["family"]
            key = (
                family,
                row["source_volume"],
                int(row["source_parent_ZA"]),
                canonical_excitation(row["excitation_keV"]),
            )
            if (environment, key) not in key_ratio:
                raise RuntimeError(f"Delayed SH3 event has no activation response key: {environment}, {key}")
            projected = float(row["day15_event_weight_cps"]) * key_ratio[(environment, key)]
            target = component[(environment, "delayed", family)]
            target["events"] += 1
            target["rate"] += projected
            target["variance"] += projected * projected
            delayed_event_contributions.append(
                {
                    "environment": environment,
                    "family": family,
                    "job_id": row["job_id"],
                    "event_id": int(row["event_id"]),
                    "source_volume": row["source_volume"],
                    "source_parent_ZA": int(row["source_parent_ZA"]),
                    "source_excitation_keV": canonical_excitation(row["excitation_keV"]),
                    "balloon_day15_event_weight_cps": float(row["day15_event_weight_cps"]),
                    "source_spectrum_ratio_to_balloon": key_ratio[(environment, key)],
                    "projected_day15_event_rate_cps": projected,
                }
            )

    component_rows: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        for stream in ("prompt", "delayed"):
            for family in FAMILIES:
                item = component[(environment, stream, family)]
                component_rows.append(
                    {
                        "environment": environment,
                        "stream": stream,
                        "family": family,
                        "selected_mc_events": int(item["events"]),
                        "projected_rate_cps": item["rate"],
                        "conditional_mc_sigma_cps": math.sqrt(item["variance"]),
                    }
                )
    write_csv(TABLES / "sh3_projected_background_components.csv", component_rows)
    delayed_event_contributions.sort(
        key=lambda row: (str(row["environment"]), -float(row["projected_day15_event_rate_cps"]))
    )
    write_csv(TABLES / "sh3_projected_delayed_event_contributions.csv", delayed_event_contributions)

    dominance: dict[str, dict[str, float]] = {}
    for environment in ENVIRONMENTS:
        selected = [row for row in delayed_event_contributions if row["environment"] == environment]
        values = sorted((float(row["projected_day15_event_rate_cps"]) for row in selected), reverse=True)
        delayed_total = math.fsum(values)
        by_key: dict[tuple[str, str, int, float], float] = defaultdict(float)
        family_total: dict[str, float] = defaultdict(float)
        for row in selected:
            value = float(row["projected_day15_event_rate_cps"])
            key = (
                str(row["family"]),
                str(row["source_volume"]),
                int(row["source_parent_ZA"]),
                float(row["source_excitation_keV"]),
            )
            by_key[key] += value
            family_total[str(row["family"])] += value
        key_values = sorted(by_key.values(), reverse=True)
        dominance[environment] = {
            "top_5_delayed_event_fraction": math.fsum(values[:5]) / delayed_total if delayed_total else 0.0,
            "top_2_activation_key_fraction": math.fsum(key_values[:2]) / delayed_total if delayed_total else 0.0,
            "proton_fraction_of_delayed": family_total["p"] / delayed_total if delayed_total else 0.0,
        }

    direct_rows = read_csv(DIRECT_CUTFLOW)
    final_direct = [
        row
        for row in direct_rows
        if row["window_id"] == "w2_510p58_511p42" and row["stage"] == "compton_trajectory_veto"
    ]
    expected_prompt = math.fsum(
        float(row["weighted_rate_cps"]) for row in final_direct if row["stream"] == "prompt"
    )
    expected_delayed = math.fsum(
        float(row["weighted_rate_cps"]) for row in final_direct if row["stream"] == "delayed"
    )
    observed_prompt = math.fsum(float(row["event_weight_cps"]) for row in prompt_rows)
    observed_delayed = math.fsum(float(row["day15_event_weight_cps"]) for row in delayed_rows)
    if not math.isclose(observed_prompt, expected_prompt, rel_tol=0.0, abs_tol=1.0e-15):
        raise RuntimeError(f"Prompt rate closure failed: {observed_prompt} vs {expected_prompt}")
    if not math.isclose(observed_delayed, expected_delayed, rel_tol=0.0, abs_tol=1.0e-15):
        raise RuntimeError(f"Delayed rate closure failed: {observed_delayed} vs {expected_delayed}")
    balloon_rate = expected_prompt + expected_delayed

    timeline_rows = read_csv(MISSION_TIMELINE)
    days = np.asarray([float(row["day_mid"]) for row in timeline_rows])
    transmission = np.asarray([float(row["T_atm_511_slant45"]) for row in timeline_rows])
    accidental = np.asarray([float(row["conditional_signal_accidental_survival"]) for row in timeline_rows])
    mean_transmission = float(np.trapezoid(transmission * accidental, days) / np.trapezoid(accidental, days))
    official_fmin = float(mission["fmin_ph_cm2_s"]["fmin_3sigma_gauss_ph_cm2_s"])
    official_fmin_sigma = float(mission["fmin_3sigma_gaussian_standard_error_ph_cm2_s"])
    signal_relative_sigma = float(mission["statistical_uncertainty"]["signal_combined_relative_sigma"])
    aeff = float(mission["aeff_w2_final_cm2"])

    estimates: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        prompt = math.fsum(component[(environment, "prompt", family)]["rate"] for family in FAMILIES)
        delayed = math.fsum(component[(environment, "delayed", family)]["rate"] for family in FAMILIES)
        variance = math.fsum(
            component[(environment, stream, family)]["variance"]
            for stream in ("prompt", "delayed")
            for family in FAMILIES
        )
        total = prompt + delayed
        conditional_sigma = math.sqrt(variance)
        spectrum_relative = math.sqrt(total / balloon_rate)
        if environment == "balloon_38km":
            mission_relative = 1.0
            estimated_fmin = official_fmin
            signal_transmission = mean_transmission
        else:
            mission_relative = mean_transmission * spectrum_relative
            estimated_fmin = official_fmin * mission_relative
            signal_transmission = 1.0
        conditional_background_relative_sigma = conditional_sigma / total if total > 0 else math.inf
        conditional_fmin_relative_sigma = math.sqrt(
            (0.5 * conditional_background_relative_sigma) ** 2 + signal_relative_sigma**2
        )
        conditional_fmin_sigma = estimated_fmin * conditional_fmin_relative_sigma
        if environment == "balloon_38km":
            conditional_fmin_relative_sigma = official_fmin_sigma / official_fmin
            conditional_fmin_sigma = official_fmin_sigma
        estimates.append(
            {
                "environment": environment,
                "geometry": "SH3_OPTV3_60cm",
                "prompt_rate_cps": prompt,
                "delayed_rate_cps": delayed,
                "total_rate_cps": total,
                "background_ratio_to_balloon": total / balloon_rate,
                "conditional_mc_sigma_cps": conditional_sigma,
                "conditional_background_relative_sigma": conditional_background_relative_sigma,
                "weighted_effective_selected_events": total * total / variance if variance > 0 else 0.0,
                "signal_effective_area_cm2": aeff,
                "exposure_days": 20.0,
                "assumed_signal_transmission": signal_transmission,
                "spectrum_only_relative_F3_to_balloon": spectrum_relative,
                "mission_relative_F3_to_SH3_balloon_including_signal_transmission": mission_relative,
                "estimated_20d_F3_ph_cm2_s": estimated_fmin,
                "estimated_20d_F3_conditional_MC_relative_sigma": conditional_fmin_relative_sigma,
                "estimated_20d_F3_conditional_MC_sigma_ph_cm2_s": conditional_fmin_sigma,
                "delayed_fraction_of_projected_background": delayed / total if total > 0 else 0.0,
                **dominance[environment],
                "SH3_balloon_official_F3_ph_cm2_s": official_fmin,
                "SH3_balloon_official_statistical_sigma_ph_cm2_s": official_fmin_sigma,
            }
        )
    write_csv(TABLES / "sh3_environment_performance_estimates.csv", estimates)

    response_values: dict[str, list[float]] = defaultdict(list)
    response_weights: dict[str, list[float]] = defaultdict(list)
    for row in prompt_rows:
        family = str(row["family"])
        response_values[family].append(float(row["primary_energy_MeV_total"]))
        response_weights[family].append(float(row["event_weight_cps"]))
    for row in delayed_rows:
        family = row["family"]
        key = (
            family,
            row["source_volume"],
            int(row["source_parent_ZA"]),
            canonical_excitation(row["excitation_keV"]),
        )
        energies = np.asarray(activation[key], dtype=float) / 1000.0
        per_record_weight = float(row["day15_event_weight_cps"]) / len(energies)
        response_values[family].extend(energies.tolist())
        response_weights[family].extend([per_record_weight] * len(energies))
    bands: list[dict[str, object]] = []
    for family in RESPONSE_PANELS:
        values = np.asarray(response_values[family], dtype=float)
        weights = np.asarray(response_weights[family], dtype=float)
        family_rate = math.fsum(component[("balloon_38km", stream, family)]["rate"] for stream in ("prompt", "delayed"))
        bands.append(
            {
                "family": family,
                "response_weighted_primary_energy_p10_MeV": weighted_quantile(values, weights, 0.10),
                "response_weighted_primary_energy_p50_MeV": weighted_quantile(values, weights, 0.50),
                "response_weighted_primary_energy_p90_MeV": weighted_quantile(values, weights, 0.90),
                "balloon_W2_final_rate_cps": family_rate,
                "fraction_of_balloon_W2_final": family_rate / balloon_rate,
                "response_weight_sum_cps": float(np.sum(weights)),
            }
        )
    write_csv(TABLES / "sh3_response_weighted_primary_energy_bands.csv", bands)

    configure_plotting()
    plot_full_spectra(models)
    plot_response_bands(models, bands)
    plot_performance(estimates)

    by_env = {str(row["environment"]): row for row in estimates}
    summary = {
        "schema_version": 1,
        "status": "PASS__SH3_FOUR_ENVIRONMENT_SOURCE_SPECTRUM_PROJECTION",
        "geometry": "SH3_OPTV3_60cm",
        "authority_boundary": "SOURCE_SPECTRUM_RESPONSE_PROJECTION__NOT_ENVIRONMENT_MATCHED_TRANSPORT",
        "SH3_event_closure": {
            "prompt_W2_final_events": len(prompt_rows),
            "prompt_W2_final_rate_cps": observed_prompt,
            "delayed_W2_final_events": len(delayed_rows),
            "delayed_W2_final_rate_cps": observed_delayed,
            "total_direct_no_coincidence_rate_cps": balloon_rate,
        },
        "SH3_balloon_20d": {
            "F3_ph_cm2_s": official_fmin,
            "statistical_sigma_ph_cm2_s": official_fmin_sigma,
            "Aeff_cm2": aeff,
            "effective_20d_slant45_signal_transmission_holding_accidentals_common": mean_transmission,
        },
        "L2_source_contract": {
            "location_semantics": "Sun-Earth L2 treated as near-Earth interplanetary space at approximately 1 AU",
            "gamma": "COSI DC4 cosmic-photon intensity expanded from LEO unocculted sky to full 4pi",
            "charged_primaries": "same COSI 1-AU p/alpha/e-/e+ parent spectra as LEO with 12.6-GV geomagnetic transmission removed, full 4pi",
            "removed_LEO_components": ["Earth albedo photons", "atmospheric 511", "atmospheric/albedo neutrons", "secondary charged particles", "SAA"],
            "not_in_baseline": ["SEP", "GCR Z>2 heavy ions", "directional Galactic diffuse sky", "spacecraft-local secondaries beyond retained SH3 response"],
            "integrated_flux_over_fixed_model_support_cm2_s": l2_source_integrals,
            "SH3_activation_RP_mapping_status_counts": dict(sorted(l2_activation_mapping_status.items())),
        },
        "environment_estimates": by_env,
        "main_L2_result": by_env["sun_earth_l2_quiet_1au_proxy"],
        "cautions": [
            "Target spectra reweight retained balloon transport at incident primary energy; no target-environment transport was run.",
            "Activation ratios are averaged within exact incident-family x source-volume x parent-ZA x excitation keys.",
            "The L2 central value has sparse conditional response statistics; five delayed selected events supply about 91% of the projected delayed rate.",
            "Six of 85 activation RP records fall below the retained L2 electron/positron support and are numerical coverage gaps, not physical zero-flux claims; their current W2 contribution is negligible.",
            "The L2 estimate excludes SEP and heavy ions because the retained eight-family SH3 response has no corresponding source families.",
            "Target-environment accidental-coincidence changes and orbit/site time histories are not modeled.",
        ],
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
