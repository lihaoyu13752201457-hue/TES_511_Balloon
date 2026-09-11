#!/usr/bin/env python3
"""Build an energy-response reweighting proxy for balloon, LEO, and Moon.

The detector response comes only from the retained corrected balloon
transport.  LEO and lunar values are importance-reweighted source proxies;
they are not substitutes for orbit/surface-specific transport.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_response_projection_mpl"))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
M05 = ROOT / "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
M05_OUT = M05 / "outputs"
BASE = ROOT / "engineering/satellite_leo530_source_comparison_20260813"
LUNAR = ROOT / "engineering/lunar_surface_source_comparison_20260813"
ACTIVATION = PACKAGE / "outputs/tables/activation_rp_primary_energy.csv.gz"
ACTIVATION_SUMMARY = PACKAGE / "data/activation_scan_summary.json"
LINEAGE = M05_OUT / "04_common_response/selected_background_w2_lineage.csv"
SIGNAL = M05_OUT / "04_common_response/signal_acceptance_effective_area.csv"
STREAM_BUDGET = M05_OUT / "05_matched_comparison/w2_stream_family_budget.csv"
MISSION = M05_OUT / "06_mission/summary.json"
TABLES = PACKAGE / "outputs/tables"
FIGURES = PACKAGE / "outputs/figures"
SUMMARY = PACKAGE / "outputs/summary.json"

ENVIRONMENTS = ("balloon_38km", "leo530_quiet_proxy", "lunar_surface_proxy")
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("gamma", "p", "n", "alpha", "eplus", "eminus", "muminus", "muplus")
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
FAMILY_COLOR = {
    "gamma": "#2369BD",
    "p": "#2A9D45",
    "n": "#7651A8",
    "alpha": "#7C8B24",
    "eplus": "#CC5C91",
    "eminus": "#E07A1F",
    "muminus": "#777C82",
    "muplus": "#A0A4A8",
}
ENV_LABEL = {
    "balloon_38km": "38 km 大气环境",
    "leo530_quiet_proxy": "530 km 近赤道 LEO 代理",
    "lunar_surface_proxy": "暴露月面代理",
}
T_SECONDS = 20.0 * 86400.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fields: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            x = self.energy_keV[positive]
            y = self.value_per_keV[positive]
            valid = inside & (target >= x[0]) & (target <= x[-1])
            out[valid] = np.exp(np.interp(np.log(target[valid]), np.log(x), np.log(y)))
        if np.ndim(energy_keV) == 0:
            return float(out)
        return out


def curve_from_rows(
    rows: list[dict[str, str]], x_field: str, y_field: str, *, x_scale: float = 1.0,
    y_scale: float = 1.0, interpolation: str = "loglog"
) -> Curve:
    grouped: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(x_field, "") == "" or row.get(y_field, "") == "":
            continue
        x = float(row[x_field]) * x_scale
        y = float(row[y_field]) * y_scale
        if x > 0 and math.isfinite(x) and y >= 0 and math.isfinite(y):
            grouped[x].append(y)
    energy = np.asarray(sorted(grouped), dtype=float)
    values = np.asarray([float(np.mean(grouped[x])) for x in energy], dtype=float)
    return Curve(energy, values, interpolation)


class SourceModels:
    def __init__(self) -> None:
        balloon_rows = read_csv(BASE / "outputs/tables/balloon_aggregated_spectra.csv")
        leo_rows = read_csv(BASE / "outputs/tables/satellite_profile_spectra.csv")
        lunar_rows = read_csv(LUNAR / "outputs/tables/lunar_prompt_components.csv")
        lunar_gamma = read_csv(LUNAR / "outputs/tables/three_environment_gamma_spectra.csv")
        self.balloon: dict[str, Curve] = {}
        self.leo: dict[str, Curve] = {}
        self.lunar_components: dict[str, list[Curve]] = defaultdict(list)
        for family in FAMILIES:
            selected = [r for r in balloon_rows if r["family"] == family and r["domain"] == "full"]
            if selected:
                self.balloon[family] = curve_from_rows(
                    selected, "energy_keV_total", "differential_flux_cm2_s_keV", interpolation="linear"
                )
            selected = [r for r in leo_rows if r["family"] == family]
            if selected:
                self.leo[family] = curve_from_rows(
                    selected,
                    "energy_keV_total",
                    "validity_filtered_differential_flux_cm2_s_keV",
                    interpolation="loglog",
                )
        gamma_selected = [
            r for r in lunar_gamma
            if r["environment"] == "lunar_surface_proxy" and r["component"] == "total_prompt_gamma_proxy"
        ]
        self.lunar_components["gamma"].append(
            curve_from_rows(
                gamma_selected,
                "energy_keV_total",
                "differential_flux_cm2_s_keV",
                interpolation="nearest_log_bin",
            )
        )
        meta = {
            "gcr_proton_reference": "p",
            "secondary_proton": "p",
            "secondary_neutron": "n",
            "secondary_electron_positron": "epm",
        }
        for component, family in meta.items():
            selected = [r for r in lunar_rows if r["component"] == component]
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

    def target_flux(self, environment: str, family: str, energy_keV: float | np.ndarray) -> float | np.ndarray:
        if environment == "balloon_38km":
            return self.balloon[family].at(energy_keV)
        if environment == "leo530_quiet_proxy":
            curve = self.leo.get(family)
            if curve is None:
                target = np.asarray(energy_keV, dtype=float)
                out = np.zeros_like(target)
                return float(out) if np.ndim(energy_keV) == 0 else out
            return curve.at(energy_keV)
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
            # The REDMoon public Figure-5 table lacks a primary-alpha curve.
            # Transfer the measured lunar/balloon proton environment ratio at
            # the same energy per nucleon onto the retained balloon alpha
            # abundance.  This is an explicit scenario proxy, not source data.
            p_energy = target / 4.0
            lunar_p = np.zeros_like(target)
            for curve in self.lunar_components["p"]:
                lunar_p += np.asarray(curve.at(p_energy))
            balloon_p = np.asarray(self.balloon["p"].at(p_energy))
            ratio = np.divide(lunar_p, balloon_p, out=np.zeros_like(target), where=balloon_p > 0)
            out = np.asarray(self.balloon["alpha"].at(target)) * ratio
        elif family in ("muminus", "muplus"):
            # Numerically negligible in the retained W2 background.  Keep the
            # balloon value as a transparent carry-forward placeholder rather
            # than silently treating missing REDMoon muons as physical zero.
            out = np.asarray(self.balloon[family].at(target))
        else:
            out = np.zeros_like(target)
        return float(out) if np.ndim(energy_keV) == 0 else out

    def ratio(self, environment: str, family: str, energy_keV: float) -> tuple[float, str]:
        if environment == "balloon_38km":
            return 1.0, "DIRECT_REFERENCE"
        denominator = float(self.balloon[family].at(energy_keV))
        if denominator <= 0:
            return 0.0, "OUTSIDE_BALLOON_SUPPORT"
        numerator = float(self.target_flux(environment, family, energy_keV))
        if environment == "leo530_quiet_proxy" and family == "n":
            status = "LEO_10GV_NEUTRON_DIAGNOSTIC_PROXY"
        elif environment == "leo530_quiet_proxy" and family in ("muminus", "muplus"):
            status = "LEO_MUON_UNAVAILABLE_AS_ZERO_IN_PROFILE"
        elif environment == "lunar_surface_proxy" and family == "alpha":
            status = "LUNAR_ALPHA_PROTON_TRANSFER_PROXY"
        elif environment == "lunar_surface_proxy" and family in ("eplus", "eminus"):
            status = "LUNAR_EPM_EQUAL_CHARGE_SPLIT_PROXY"
        elif environment == "lunar_surface_proxy" and family in ("muminus", "muplus"):
            status = "LUNAR_MUON_BALLOON_CARRY_FORWARD_PLACEHOLDER"
        else:
            status = "SOURCE_SPECTRUM_DIRECT__ANGULAR_DOMAIN_MISMATCH"
        if numerator == 0.0 and status.startswith("SOURCE_"):
            status = "TARGET_MODEL_OUTSIDE_SUPPORT_AS_ZERO"
        return numerator / denominator, status


def parse_prompt_init(source_file: str, local_id: int) -> tuple[float, float, float, float, bool, bool]:
    current = False
    initial: tuple[float, float, float, float] | None = None
    has_pair = False
    has_annihilation = False
    with gzip.open(source_file, "rt", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            if raw.startswith("SE"):
                if current and initial is not None:
                    return (*initial, has_pair, has_annihilation)
                current = False
            elif raw.startswith("ID "):
                parts = raw.split()
                current = len(parts) >= 2 and int(parts[1]) == local_id
                if current:
                    initial = None
                    has_pair = False
                    has_annihilation = False
            elif current and raw.startswith("IA INIT"):
                fields = [item.strip() for item in raw[len("IA INIT") :].split(";")]
                initial = (float(fields[22]), float(fields[16]), float(fields[17]), float(fields[18]))
            elif current and raw.startswith("IA PAIR"):
                has_pair = True
            elif current and raw.startswith("IA ANNI"):
                has_annihilation = True
    if current and initial is not None:
        return (*initial, has_pair, has_annihilation)
    raise RuntimeError(f"Prompt IA INIT not found: {source_file} event {local_id}")


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    if len(values) == 0 or np.sum(weights) <= 0:
        return math.nan
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cdf = np.cumsum(weights) / np.sum(weights)
    return float(np.interp(q, cdf, values))


def load_activation() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with gzip.open(ACTIVATION, "rt", encoding="utf-8", newline="") as stream:
        for raw in csv.DictReader(stream):
            rows.append(
                {
                    "geometry": raw["geometry"],
                    "family": raw["incident_family"],
                    "energy_keV": float(raw["primary_energy_keV_total"]),
                    "volume": raw["logical_volume"],
                    "za": int(raw["source_parent_ZA"]),
                    "excitation_keV": float(raw["source_excitation_keV"]),
                }
            )
    return rows


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans CJK JP", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 9.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.5,
            "legend.fontsize": 8.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#D8DDE2",
            "grid.alpha": 0.7,
            "grid.linestyle": ":",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    required = [
        ACTIVATION,
        ACTIVATION_SUMMARY,
        LINEAGE,
        SIGNAL,
        STREAM_BUDGET,
        MISSION,
        BASE / "data/validation.json",
        LUNAR / "data/validation.json",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing required input: {path}")
    scan_summary = json.loads(ACTIVATION_SUMMARY.read_text(encoding="utf-8"))
    if scan_summary.get("status") != "PASS__ACTIVATION_RP_PRIMARY_ENERGY_EXACT_JOIN":
        raise RuntimeError("Activation primary-energy scan is not PASS")
    if json.loads((BASE / "data/validation.json").read_text()).get("status") != "PASS":
        raise RuntimeError("Balloon/LEO source package is not PASS")
    if not str(json.loads((LUNAR / "data/validation.json").read_text()).get("status", "")).startswith("PASS"):
        raise RuntimeError("Lunar source package is not PASS")

    models = SourceModels()
    lineage = read_csv(LINEAGE)
    prompt_rows: list[dict[str, object]] = []
    for row in lineage:
        if row["stream"] != "prompt":
            continue
        energy, dx, dy, dz, has_pair, has_annihilation = parse_prompt_init(
            row["source_file"], int(row["local_event_id"])
        )
        record: dict[str, object] = {
            "geometry": row["geometry"],
            "family": row["family"],
            "local_event_id": int(row["local_event_id"]),
            "primary_energy_MeV_total": energy / 1000.0,
            "primary_dir_x": dx,
            "primary_dir_y": dy,
            "primary_dir_z": dz,
            "primary_theta_deg": math.degrees(math.acos(max(-1.0, min(1.0, dz)))),
            "has_pair_ia": has_pair,
            "has_annihilation_ia": has_annihilation,
            "measured_total_keV": float(row["measured_total_keV"]),
            "event_weight_cps": float(row["event_weight_cps"]),
            "source_file": row["source_file"],
        }
        for environment in ENVIRONMENTS:
            ratio, status = models.ratio(environment, row["family"], energy)
            record[f"{environment}_source_ratio"] = ratio
            record[f"{environment}_mapping_status"] = status
        prompt_rows.append(record)
    prompt_rows.sort(key=lambda r: (str(r["geometry"]), str(r["family"]), float(r["primary_energy_MeV_total"])))
    write_csv(TABLES / "prompt_w2_primary_energy.csv", prompt_rows, prompt_rows[0].keys())

    activation = load_activation()
    rp_by_key: dict[tuple[str, str, str, int, float], list[dict[str, object]]] = defaultdict(list)
    for row in activation:
        key = (
            str(row["geometry"]), str(row["family"]), str(row["volume"]),
            int(row["za"]), float(row["excitation_keV"]),
        )
        rp_by_key[key].append(row)

    key_ratio: dict[tuple[str, tuple[str, str, str, int, float]], float] = {}
    activation_key_rows: list[dict[str, object]] = []
    for key, rows in sorted(rp_by_key.items()):
        geometry, family, volume, za, excitation = key
        energies = np.asarray([float(r["energy_keV"]) for r in rows])
        for environment in ENVIRONMENTS:
            ratios_and_status = [models.ratio(environment, family, float(e)) for e in energies]
            ratios = np.asarray([item[0] for item in ratios_and_status], dtype=float)
            statuses = Counter(item[1] for item in ratios_and_status)
            ratio = float(np.mean(ratios))
            key_ratio[(environment, key)] = ratio
            activation_key_rows.append(
                {
                    "environment": environment,
                    "geometry": geometry,
                    "incident_family": family,
                    "source_volume": volume,
                    "source_parent_ZA": za,
                    "source_excitation_keV": excitation,
                    "rp_records": len(rows),
                    "primary_energy_p10_MeV": weighted_quantile(energies / 1000.0, np.ones(len(rows)), 0.10),
                    "primary_energy_p50_MeV": weighted_quantile(energies / 1000.0, np.ones(len(rows)), 0.50),
                    "primary_energy_p90_MeV": weighted_quantile(energies / 1000.0, np.ones(len(rows)), 0.90),
                    "production_ratio_to_balloon": ratio,
                    "ratio_rms": float(np.sqrt(np.mean(ratios * ratios))),
                    "mapping_status_counts": json.dumps(dict(sorted(statuses.items())), sort_keys=True),
                }
            )
    write_csv(TABLES / "activation_key_energy_response.csv", activation_key_rows, activation_key_rows[0].keys())

    # Project final selected rates.  For delayed events, the source mixture was
    # sampled under the balloon activity.  Reweight each selected event by the
    # target/balloon production ratio for its parent-volume-state key.
    component: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0}
    )
    for environment in ENVIRONMENTS:
        for row in lineage:
            geometry, stream, family = row["geometry"], row["stream"], row["family"]
            weight = float(row["event_weight_cps"])
            if stream == "prompt":
                match = next(
                    item for item in prompt_rows
                    if item["geometry"] == geometry
                    and item["family"] == family
                    and int(item["local_event_id"]) == int(row["local_event_id"])
                    and item["source_file"] == row["source_file"]
                )
                ratio = float(match[f"{environment}_source_ratio"])
            else:
                key = (
                    geometry,
                    family,
                    row["source_volume"],
                    int(row["source_parent_ZA"]),
                    float(row["source_excitation_keV"]),
                )
                if (environment, key) not in key_ratio:
                    raise RuntimeError(f"Delayed lineage has no BUILDUP response key: {environment}, {key}")
                ratio = key_ratio[(environment, key)]
            projected = weight * ratio
            target = component[(environment, geometry, stream, family)]
            target["events"] += 1
            target["rate"] += projected
            target["variance"] += projected * projected

    component_rows: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        for geometry in GEOMETRIES:
            for stream in ("prompt", "delayed"):
                for family in FAMILIES:
                    item = component[(environment, geometry, stream, family)]
                    component_rows.append(
                        {
                            "environment": environment,
                            "geometry": geometry,
                            "stream": stream,
                            "family": family,
                            "selected_mc_events": int(item["events"]),
                            "projected_rate_cps": item["rate"],
                            "conditional_mc_sigma_cps": math.sqrt(item["variance"]),
                        }
                    )
    write_csv(TABLES / "projected_background_components.csv", component_rows, component_rows[0].keys())

    aeff_rows = [
        row for row in read_csv(SIGNAL)
        if row["response_state"] == "measured"
        and row["stage"] == "side_compton_fov_pass"
        and row["window_id"] == "w2_510p58_511p42"
    ]
    aeff = {row["geometry"]: float(row["selected_effective_area_cm2"]) for row in aeff_rows}
    estimates: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        for geometry in GEOMETRIES:
            prompt = sum(
                component[(environment, geometry, "prompt", family)]["rate"] for family in FAMILIES
            )
            delayed = sum(
                component[(environment, geometry, "delayed", family)]["rate"] for family in FAMILIES
            )
            variance_prompt = sum(
                component[(environment, geometry, "prompt", family)]["variance"] for family in FAMILIES
            )
            variance_delayed = sum(
                component[(environment, geometry, "delayed", family)]["variance"] for family in FAMILIES
            )
            total = prompt + delayed
            sigma = math.sqrt(variance_prompt + variance_delayed)
            f3 = 3.0 * math.sqrt(total) / (aeff[geometry] * math.sqrt(T_SECONDS)) if total > 0 else 0.0
            f3_prompt = 3.0 * math.sqrt(prompt) / (aeff[geometry] * math.sqrt(T_SECONDS)) if prompt > 0 else 0.0
            low_b = max(0.0, total - sigma)
            high_b = total + sigma
            estimates.append(
                {
                    "environment": environment,
                    "geometry": geometry,
                    "prompt_rate_cps": prompt,
                    "delayed_rate_cps": delayed,
                    "total_rate_cps": total,
                    "conditional_mc_sigma_cps": sigma,
                    "conditional_effective_mc_events": total * total / (sigma * sigma) if sigma > 0 else math.inf,
                    "signal_effective_area_cm2": aeff[geometry],
                    "exposure_days": 20.0,
                    "signal_transmission": 1.0,
                    "duty_cycle": 1.0,
                    "F3_mapped_prompt_continuum_proxy_ph_cm2_s": f3_prompt,
                    "F3_mapped_continuum_plus_activation_proxy_ph_cm2_s": f3,
                    "F3_mapped_conditional_mc_minus1sigma_ph_cm2_s": (
                        3.0 * math.sqrt(low_b) / (aeff[geometry] * math.sqrt(T_SECONDS)) if low_b > 0 else 0.0
                    ),
                    "F3_mapped_conditional_mc_plus1sigma_ph_cm2_s": (
                        3.0 * math.sqrt(high_b) / (aeff[geometry] * math.sqrt(T_SECONDS)) if high_b > 0 else 0.0
                    ),
                    "unmapped_native_511_status": (
                        "retained broadband total-gamma profile"
                        if environment == "balloon_38km"
                        else "LEO delta-511 omitted; requires dedicated transport"
                        if environment == "leo530_quiet_proxy"
                        else "REDMoon native 511-bin direct response omitted; requires dedicated transport"
                    ),
                    "scope": (
                        "20d exposure with static day-15 detector-plane rate, observed-candidate central proxy, "
                        "no-atmosphere, full-live; "
                        "target native/delta 511 and zero-survivor prompt upper limits excluded"
                    ),
                }
            )
    write_csv(TABLES / "f3_projection.csv", estimates, estimates[0].keys())

    # Allocate balloon delayed selected rates over the primary energies that
    # created each parent-volume-state source component.
    selected_rate_by_key: dict[tuple[str, str, str, int, float], float] = defaultdict(float)
    for row in lineage:
        if row["stream"] != "delayed":
            continue
        key = (
            row["geometry"], row["family"], row["source_volume"],
            int(row["source_parent_ZA"]), float(row["source_excitation_keV"]),
        )
        selected_rate_by_key[key] += float(row["event_weight_cps"])
    energy_contrib: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for key, rate in selected_rate_by_key.items():
        records = rp_by_key[key]
        share = rate / len(records)
        for record in records:
            energy_contrib[(key[0], key[1])].append((float(record["energy_keV"]) / 1000.0, share))
    for row in prompt_rows:
        energy_contrib[(str(row["geometry"]), str(row["family"]))].append(
            (float(row["primary_energy_MeV_total"]), float(row["event_weight_cps"]))
        )
    interval_rows: list[dict[str, object]] = []
    for (geometry, family), pairs in sorted(energy_contrib.items()):
        energy = np.asarray([item[0] for item in pairs])
        weights = np.asarray([item[1] for item in pairs])
        interval_rows.append(
            {
                "geometry": geometry,
                "family": family,
                "response_weighted_rate_cps": float(np.sum(weights)),
                "primary_energy_p10_MeV": weighted_quantile(energy, weights, 0.10),
                "primary_energy_p50_MeV": weighted_quantile(energy, weights, 0.50),
                "primary_energy_p90_MeV": weighted_quantile(energy, weights, 0.90),
                "energy_min_MeV": float(np.min(energy)),
                "energy_max_MeV": float(np.max(energy)),
                "note": "prompt exact survivors plus delayed parent/volume response-weighted BUILDUP RP distribution",
            }
        )
    write_csv(TABLES / "w2_primary_energy_intervals.csv", interval_rows, interval_rows[0].keys())

    # Net Mass-minus-O8 background reduction by family and energy decade.
    # The retained neutron source extends down to thermal/sub-thermal energies.
    # Start far below the plotting range so the CSV still closes exactly to the
    # family budget; the presentation view intentionally begins at 0.1 MeV.
    edges = np.logspace(-12, 6, 73)
    net_rows: list[dict[str, object]] = []
    for family in FAMILIES:
        hist = {}
        for geometry in GEOMETRIES:
            pairs = energy_contrib.get((geometry, family), [])
            histogram_energy = np.clip(
                np.asarray([item[0] for item in pairs], dtype=float),
                edges[0],
                np.nextafter(edges[-1], edges[0]),
            )
            h = np.histogram(
                histogram_energy, bins=edges, weights=[item[1] for item in pairs]
            )[0]
            hist[geometry] = h
        delta = hist["Mass_model_511"] - hist["S3d_O8"]
        for i, value in enumerate(delta):
            net_rows.append(
                {
                    "family": family,
                    "energy_lo_MeV": edges[i],
                    "energy_hi_MeV": edges[i + 1],
                    "energy_center_MeV": math.sqrt(edges[i] * edges[i + 1]),
                    "mass_minus_s3d_rate_cps": value,
                }
            )
    write_csv(TABLES / "net_background_reduction_by_primary_energy.csv", net_rows, net_rows[0].keys())

    configure_plotting()
    grid_mev = np.logspace(-1, math.log10(5.0e5), 760)
    fig, axes = plt.subplots(1, 3, figsize=(14.8, 5.4), sharex=True, sharey=True)
    plot_families = ("gamma", "p", "n", "alpha", "eplus")
    for ax, environment in zip(axes, ENVIRONMENTS):
        for family in plot_families:
            y = np.asarray(models.target_flux(environment, family, grid_mev * 1000.0)) * 1000.0
            style = "--" if environment == "lunar_surface_proxy" and family == "alpha" else "-"
            if environment == "leo530_quiet_proxy" and family == "n":
                style = ":"
            mask = y > 0
            ax.plot(grid_mev[mask], grid_mev[mask] * y[mask], color=FAMILY_COLOR[family], lw=1.55, ls=style)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.1, 5.0e5)
        ax.set_ylim(1e-6, 3e2)
        ax.set_title(ENV_LABEL[environment], loc="left", fontweight="bold")
        ax.set_xlabel("初级总动能 [MeV]")
        if environment != "balloon_38km":
            ax.axvline(0.511, color="#20262C", lw=1.0, ls="--", alpha=0.85)
            ax.text(
                0.511,
                0.69,
                "原生 511：未映射响应",
                rotation=90,
                va="bottom",
                ha="right",
                fontsize=7.2,
                color="#20262C",
                transform=ax.get_xaxis_transform(),
            )
        # Exact prompt survivor rugs.
        for row in prompt_rows:
            x = float(row["primary_energy_MeV_total"])
            color = FAMILY_COLOR[str(row["family"])]
            y0 = 0.84 if row["geometry"] == "Mass_model_511" else 0.80
            ax.vlines(x, y0, y0 + 0.032, color=color, lw=1.4, transform=ax.get_xaxis_transform())
        # Dominant delayed-response 10--90% bars for S3d-O8.
        ybars = {"p": 0.965, "n": 0.93, "alpha": 0.895}
        for family, ypos in ybars.items():
            match = next(
                r for r in interval_rows if r["geometry"] == "S3d_O8" and r["family"] == family
            )
            ax.hlines(
                ypos,
                float(match["primary_energy_p10_MeV"]),
                float(match["primary_energy_p90_MeV"]),
                color=FAMILY_COLOR[family],
                lw=4.0,
                transform=ax.get_xaxis_transform(),
            )
            ax.text(
                float(match["primary_energy_p90_MeV"]) * 1.06,
                ypos,
                f"{FAMILY_LABEL[family]}→活化",
                color=FAMILY_COLOR[family],
                va="center",
                fontsize=7.4,
                transform=ax.get_xaxis_transform(),
            )
    axes[0].set_ylabel(r"$E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")
    handles = [Line2D([0], [0], color=FAMILY_COLOR[f], lw=2, label=FAMILY_LABEL[f]) for f in plot_families]
    handles += [
        Line2D([0], [0], color="#333333", lw=1.4, marker="|", markersize=9, label="最终 prompt W2 初能"),
        Line2D([0], [0], color="#333333", lw=4, label="S3d delayed 10–90% 初能区"),
    ]
    axes[0].legend(handles=handles, loc="lower left", ncol=2, frameon=False)
    fig.suptitle("三种入射环境谱与已测 W2 响应能区", fontsize=15, fontweight="bold", x=0.06, ha="left")
    fig.text(
        0.06,
        0.925,
        "响应标记来自 corrected balloon transport；LEO/月面仅做一维角积分谱映射，原生/delta 511 线另需专门输运。",
        fontsize=9.2,
        color="#59636E",
    )
    save_figure(fig, "01_source_spectra_with_w2_response_energy")

    # Current balloon reduction: family bars and energy-resolved net histogram.
    budget_rows = read_csv(STREAM_BUDGET)
    delta_family: dict[str, float] = defaultdict(float)
    for family in FAMILIES:
        mass = sum(
            float(r["rate_cps"]) for r in budget_rows if r["geometry"] == "Mass_model_511" and r["family"] == family
        )
        o8 = sum(float(r["rate_cps"]) for r in budget_rows if r["geometry"] == "S3d_O8" and r["family"] == family)
        delta_family[family] = mass - o8
    # Keep the presentation panel to the five material contributors.  The
    # omitted e-/mu terms are retained in the CSV and sum to a small negative
    # counterterm; showing all eight made the near-zero labels unreadable.
    order = ["gamma", "p", "eplus", "alpha", "n"]
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13.4, 5.2), gridspec_kw={"width_ratios": [0.86, 1.5]})
    values = [delta_family[f] for f in order]
    total_delta = sum(delta_family.values())
    ax0.barh(range(len(order)), values, color=[FAMILY_COLOR[f] for f in order], alpha=0.9)
    ax0.set_yticks(range(len(order)), [FAMILY_LABEL[f] for f in order])
    ax0.invert_yaxis()
    ax0.axvline(0, color="#333333", lw=0.9)
    ax0.set_xlabel("Mass − S3d-O8 W2 本底 [cps]")
    ax0.set_title("主贡献粒子族（prompt + delayed 净值）", loc="left", fontweight="bold")
    for i, value in enumerate(values):
        fraction = 100.0 * value / total_delta
        ax0.text(value + 0.0015, i, f"{value:+.4f}  ({fraction:.1f}%)", va="center", ha="left", fontsize=8)
    ax0.set_xlim(-0.003, max(values) * 1.22)
    for family in ("gamma", "p", "n", "alpha", "eplus"):
        selected = [r for r in net_rows if r["family"] == family]
        x = np.asarray([float(r["energy_center_MeV"]) for r in selected])
        y = np.asarray([float(r["mass_minus_s3d_rate_cps"]) for r in selected])
        ax1.step(x, y, where="mid", color=FAMILY_COLOR[family], lw=1.7, label=FAMILY_LABEL[family])
    ax1.set_xscale("log")
    ax1.axhline(0, color="#333333", lw=0.8)
    ax1.set_xlim(0.1, 5e5)
    ax1.set_xlabel("造成 W2 候选/活化的初级总动能 [MeV]")
    ax1.set_ylabel("每对数能段的净本底降低 [cps]")
    ax1.set_title("性能改善来自哪些初级能量", loc="left", fontweight="bold")
    ax1.legend(frameon=False, ncol=3)
    fig.suptitle("S3d-O8 相对 Mass511 的 corrected day-15 W2 改善", fontsize=14.2, fontweight="bold", x=0.06, ha="left")
    fig.text(
        0.06, 0.925,
        "中央值；delayed 能量为母核-体积态内 RP 统计归因，不是逐候选唯一初能。低 MC 支持，零幸存族上限未画。",
        color="#59636E", fontsize=9,
    )
    save_figure(fig, "02_current_performance_contributors")

    # Projected background and F3 summary.
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13.6, 5.3))
    positions = np.arange(len(ENVIRONMENTS))
    width = 0.34
    for offset, geometry, hatch in [(-width / 2, "Mass_model_511", ""), (width / 2, "S3d_O8", "///")]:
        vals = [next(r for r in estimates if r["environment"] == e and r["geometry"] == geometry) for e in ENVIRONMENTS]
        prompt = np.asarray([float(r["prompt_rate_cps"]) for r in vals])
        delayed = np.asarray([float(r["delayed_rate_cps"]) for r in vals])
        ax0.bar(positions + offset, prompt, width, color="#4C86C6", hatch=hatch, edgecolor="white", label=f"{geometry} prompt")
        ax0.bar(positions + offset, delayed, width, bottom=prompt, color="#A6B7C8", hatch=hatch, edgecolor="white", label=f"{geometry} delayed")
    ax0.set_yscale("log")
    ax0.set_xticks(positions, ["Balloon", "LEO", "Moon"])
    ax0.set_ylabel("投影后 W2 本底率 [cps]")
    ax0.set_title("响应重加权后的本底", loc="left", fontweight="bold")
    ax0.legend(frameon=False, fontsize=7.2, ncol=2)
    for offset, geometry, color in [(-width / 2, "Mass_model_511", "#59636E"), (width / 2, "S3d_O8", "#D46A1F")]:
        vals = [next(r for r in estimates if r["environment"] == e and r["geometry"] == geometry) for e in ENVIRONMENTS]
        y = np.asarray([float(r["F3_mapped_continuum_plus_activation_proxy_ph_cm2_s"]) for r in vals])
        low = np.asarray([float(r["F3_mapped_conditional_mc_minus1sigma_ph_cm2_s"]) for r in vals])
        high = np.asarray([float(r["F3_mapped_conditional_mc_plus1sigma_ph_cm2_s"]) for r in vals])
        ax1.bar(positions + offset, y, width, color=color, alpha=0.88, label=geometry)
        ax1.errorbar(positions + offset, y, yerr=np.vstack([y - low, high - y]), fmt="none", ecolor="#222222", capsize=3, lw=0.9)
    ax1.set_yscale("log")
    ax1.set_xticks(positions, ["Balloon", "LEO", "Moon"])
    ax1.set_ylabel(r"20 d $F_{3\sigma}$ [ph cm$^{-2}$ s$^{-1}$]")
    ax1.set_title("已映射连续谱+活化的 F3 代理", loc="left", fontweight="bold")
    ax1.legend(frameon=False)
    fig.suptitle("LEO/月面性能估计：同一探测器响应的一维谱重加权", fontsize=14.2, fontweight="bold", x=0.06, ha="left")
    fig.text(
        0.06,
        0.925,
        "day-15 本底静态保持20 d、无大气吸收、100% live；中央代理，未映射原生511、零幸存族上限、SAA/SEP/基地材料。",
        fontsize=8.8,
        color="#59636E",
    )
    save_figure(fig, "03_projected_background_and_f3")

    mission = json.loads(MISSION.read_text(encoding="utf-8"))
    summary = {
        "schema_version": 1,
        "status": "PASS__ENERGY_RESPONSE_REWEIGHTING_PROXY__NOT_ENVIRONMENT_TRANSPORT_AUTHORITY",
        "prompt_exact_join_events": len(prompt_rows),
        "activation_exact_join_rp_records": len(activation),
        "selected_lineage_events": len(lineage),
        "balloon_closure": {
            geometry: next(r for r in estimates if r["environment"] == "balloon_38km" and r["geometry"] == geometry)
            for geometry in GEOMETRIES
        },
        "current_balloon_mission_F3": {
            geometry: mission["geometries"][geometry]["flux_3sigma_20d_ph_cm2_s"] for geometry in GEOMETRIES
        },
        "projections": estimates,
        "method": {
            "prompt": "candidate-wise target/balloon angle-integrated differential source-flux ratio at exact IA INIT energy",
            "activation": "RP-wise source-flux ratio at exact BUILDUP IA INIT energy, averaged within parent-volume-state; selected delayed events reweighted by that key ratio",
            "sensitivity": "F3=3*sqrt(B*T)/(Aeff*T), static day-15 detector-plane B held for 20 d, signal transmission=1, duty=1",
            "angular_boundary": "target and balloon angular domains are not matched; this is a one-dimensional spectral-response proxy",
        },
        "known_optimistic_or_scenario_terms": [
            "LEO SAA/trapped-particle activation and orbit-time weighting omitted",
            "LEO neutron uses the retained 10-GV diagnostic fallback",
            "lunar alpha uses a proton-transfer proxy at equal energy per nucleon",
            "lunar combined e-/e+ is split equally",
            "lunar muons use numerically negligible balloon carry-forward placeholders",
            "SEP, lunar-base/lander/RTG material, terrain and local south-pole regolith omitted",
            "no atmosphere, Earth/Moon occultation, pointing duty, accidental-veto change or detector-specific target-environment transport",
            "conditional MC uncertainty omits source-model, angular, activation-yield and physics-list systematics",
            "LEO delta-511 and REDMoon native 511-bin direct detector response are excluded from all projected F3 values",
            "prompt families with zero selected balloon survivors remain zero; their nonzero upper limits cannot be energy-reweighted",
            "conditional MC bars omit finite activation-RP/reweight uncertainty and are not coverage intervals",
            "target-only energy support outside the balloon proposal cannot be estimated by importance reweighting",
        ],
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in required},
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "projections": estimates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
