#!/usr/bin/env python3
"""Build a public-literature L2 source package and reweight retained SH3 response.

The calculation keeps the retained SH3 transport response and changes only the
incident-source spectrum.  It is therefore a response projection, not an
environment-matched prompt -> activation -> delayed rerun.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
BASE_PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "64_sh3_l2_environment_projection_20260820"
)
BASE_SCRIPT = BASE_PACKAGE / "code/build_sh3_environment_projection.py"
TABLES = PACKAGE / "outputs/tables"
FIGURES = PACKAGE / "outputs/figures"
SUMMARY = PACKAGE / "outputs/summary.json"
ELECTRON_DIGITIZED = PACKAGE / "data/athena_jovian_electron_digitized.csv"

CENTRAL_L2 = "sun_earth_l2_quiet_1au_proxy"
SOLAR_MAX_L2 = "sun_earth_l2_solar_max_2014"
CLASSIC_ENVIRONMENTS = (
    "balloon_38km",
    "leo530_quiet_proxy",
    "lunar_surface_proxy",
    CENTRAL_L2,
)
ALL_ENVIRONMENTS = CLASSIC_ENVIRONMENTS + (SOLAR_MAX_L2,)

PHI_2009_GV = 0.3793
PHI_2014_GV = 0.803
PROTON_RELEVANT_MIN_GEV = 1.366
PROTON_RELEVANT_MAX_GEV = 48.4


def load_base_module():
    spec = importlib.util.spec_from_file_location("sh3_l2_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load base analysis: {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = load_base_module()
ORIGINAL_EXTRACT_PROMPT = base.extract_prompt_rows
ORIGINAL_PLOT_RESPONSE = base.plot_response_bands


def athena_proton_intensity_per_gev(energy_gev: np.ndarray, phi_gv: float) -> np.ndarray:
    """Lotti et al. 2021 eqs. 1-2, based on Usoskin et al. 2005."""
    energy = np.asarray(energy_gev, dtype=float)
    rest = 0.938
    shifted = energy + phi_gv
    momentum2_shifted = shifted * (shifted + 2.0 * rest)
    lis = 1.9 * np.power(momentum2_shifted, -1.39) / (
        1.0 + 0.4866 * np.power(momentum2_shifted, -1.255)
    )
    return lis * energy * (energy + 2.0 * rest) / momentum2_shifted


def athena_alpha_intensity_per_mev(energy_mev_total: np.ndarray) -> np.ndarray:
    """Lotti et al. 2021 eq. 3, Kuznetsov quiet-Sun alpha model."""
    energy = np.asarray(energy_mev_total, dtype=float)
    return 1.085e5 * np.power(energy, -2.72) * np.power(energy / (energy + 2304.0), 3.7)


def tuerler_cxb_intensity_per_kev(energy_kev: np.ndarray) -> np.ndarray:
    """COSI/Cumani implementation of Tuerler et al. 2010 below 1 MeV."""
    energy = np.asarray(energy_kev, dtype=float)
    return 0.109 / (np.power(energy / 28.0, 1.4) + np.power(energy / 28.0, 2.88))


class CompleteL2Models(base.SourceModels):
    """Public mission-style L2 spectra with explicit solar-activity endpoints."""

    def __init__(self) -> None:
        super().__init__()
        original_l2 = dict(self.l2)
        self.original_eplus_min_keV = float(original_l2["eplus"].energy_keV[0])

        gamma = self._build_gamma(original_l2["gamma"])
        proton_2009 = self._build_proton(original_l2["p"], PHI_2009_GV)
        proton_2014 = self._build_proton(original_l2["p"], PHI_2014_GV)
        alpha_2009 = self._build_alpha_reference(original_l2["alpha"])
        alpha_2014 = self._build_alpha_solar_max(alpha_2009)
        eminus = self._build_electron(jovian_max=True)
        eplus = self._build_positron(original_l2["eplus"], eminus)

        self.l2 = {
            "gamma": gamma,
            "p": proton_2009,
            "alpha": alpha_2009,
            "eminus": eminus,
            "eplus": eplus,
        }
        self.l2_solar_max = {
            "gamma": gamma,
            "p": proton_2014,
            "alpha": alpha_2014,
            # Athena's Jovian-electron envelope is not a solar-cycle clock.
            # Keeping the maximum curve in both cases is conservative.
            "eminus": eminus,
            "eplus": eplus,
        }
        self.soft_proton_rows = self._build_soft_proton_rows()
        self.l2_rows = self._rows_for_environment(CENTRAL_L2, self.l2)
        self.l2_solar_max_rows = self._rows_for_environment(SOLAR_MAX_L2, self.l2_solar_max)

    @staticmethod
    def _curve(energy_keV: np.ndarray, full_sphere_flux_per_keV: np.ndarray) -> base.Curve:
        return base.Curve(
            np.asarray(energy_keV, dtype=float),
            np.asarray(full_sphere_flux_per_keV, dtype=float),
            "loglog",
        )

    def _build_gamma(self, original: base.Curve) -> base.Curve:
        energy = np.logspace(math.log10(3.0), math.log10(original.energy_keV[-1]), 520)
        flux = np.asarray(original.at(energy), dtype=float)
        low = energy < original.energy_keV[0]
        flux[low] = base.FULL_SKY_SR * tuerler_cxb_intensity_per_kev(energy[low])
        return self._curve(energy, flux)

    def _build_proton(self, original: base.Curve, phi_gv: float) -> base.Curve:
        energy = np.logspace(math.log10(5.0e3), math.log10(1.0e10), 560)
        energy_gev = energy * 1.0e-6
        flux = base.FULL_SKY_SR * athena_proton_intensity_per_gev(energy_gev, phi_gv) / 1.0e6

        # The Athena fit is the controlling model through the SH3 response band.
        # Above 100 GeV, retain the COSI/AMS high-energy shape and join it
        # continuously because solar modulation is already negligible there.
        join_keV = 1.0e8
        old_join = float(original.at(join_keV))
        new_join = float(
            base.FULL_SKY_SR * athena_proton_intensity_per_gev(np.asarray([100.0]), phi_gv)[0] / 1.0e6
        )
        high = energy > join_keV
        if old_join > 0:
            flux[high] = np.asarray(original.at(energy[high])) * (new_join / old_join)
        return self._curve(energy, flux)

    def _build_alpha_reference(self, original: base.Curve) -> base.Curve:
        """Kuznetsov inside 80--1e5 MeV/n; joined COSI shape outside."""
        energy = np.logspace(math.log10(1.0e4), math.log10(1.0e10), 560)
        energy_mev = energy / 1000.0
        low_valid_mev = 4.0 * 80.0
        high_valid_mev = 4.0 * 1.0e5
        full_flux = np.asarray(original.at(energy), dtype=float)
        low_join_keV = low_valid_mev * 1000.0
        high_join_keV = high_valid_mev * 1000.0
        model_low = float(
            base.FULL_SKY_SR
            * athena_alpha_intensity_per_mev(np.asarray([low_valid_mev]))[0]
            / 1000.0
        )
        model_high = float(
            base.FULL_SKY_SR
            * athena_alpha_intensity_per_mev(np.asarray([high_valid_mev]))[0]
            / 1000.0
        )
        old_low = float(original.at(low_join_keV))
        old_high = float(original.at(high_join_keV))
        below = energy < low_join_keV
        within = (energy >= low_join_keV) & (energy <= high_join_keV)
        above = energy > high_join_keV
        if old_low > 0:
            full_flux[below] *= model_low / old_low
        if old_high > 0:
            full_flux[above] *= model_high / old_high
        full_flux[within] = (
            base.FULL_SKY_SR
            * athena_alpha_intensity_per_mev(energy_mev[within])
            / 1000.0
        )
        return self._curve(energy, full_flux)

    @staticmethod
    def _loglog_with_high_extrapolation(curve: base.Curve, energy_keV: np.ndarray) -> np.ndarray:
        energy = np.asarray(energy_keV, dtype=float)
        out = np.asarray(curve.at(energy), dtype=float)
        high = energy > curve.energy_keV[-1]
        if np.any(high):
            slope = math.log(curve.value_per_keV[-1] / curve.value_per_keV[-2]) / math.log(
                curve.energy_keV[-1] / curve.energy_keV[-2]
            )
            out[high] = curve.value_per_keV[-1] * np.power(
                energy[high] / curve.energy_keV[-1], slope
            )
        return out

    def _build_alpha_solar_max(self, reference: base.Curve) -> base.Curve:
        """Project the 2009 alpha reference to 2014 with a relative FFA."""
        energy = reference.energy_keV.copy()
        energy_mev = energy / 1000.0
        delta_mev_total = 2.0 * (PHI_2014_GV - PHI_2009_GV) * 1000.0
        shifted_mev = energy_mev + delta_mev_total
        shifted_flux = self._loglog_with_high_extrapolation(reference, shifted_mev * 1000.0)
        mass_mev = 4.0 * 938.2720813
        p2 = energy_mev * (energy_mev + 2.0 * mass_mev)
        p2_shifted = shifted_mev * (shifted_mev + 2.0 * mass_mev)
        return self._curve(energy, shifted_flux * p2 / p2_shifted)

    def _electron_intensity_per_gev(self, energy_gev: np.ndarray, *, jovian_max: bool) -> np.ndarray:
        rows = base.read_csv(ELECTRON_DIGITIZED)
        table_energy = np.asarray([float(row["energy_GeV"]) for row in rows])
        field = "jovian_max_cm2_s_sr_GeV" if jovian_max else "jovian_min_cm2_s_sr_GeV"
        table_flux = np.asarray([float(row[field]) for row in rows])
        energy = np.asarray(energy_gev, dtype=float)
        out = np.empty_like(energy)
        low = energy < table_energy[0]
        middle = (energy >= table_energy[0]) & (energy <= table_energy[-1])
        high = energy > table_energy[-1]
        coefficient, index = (3.56, 1.5) if jovian_max else (1.02, 1.4)
        out[low] = coefficient * np.power(energy[low], -index) / 1.0e4
        out[middle] = np.exp(
            np.interp(
                np.log(energy[middle]),
                np.log(table_energy),
                np.log(table_flux),
            )
        )
        out[high] = 200.0 * np.power(energy[high], -3.14) / 1.0e4
        return out

    def _build_electron(self, *, jovian_max: bool) -> base.Curve:
        energy = np.logspace(3.0, 10.0, 560)
        intensity = self._electron_intensity_per_gev(energy * 1.0e-6, jovian_max=jovian_max)
        return self._curve(energy, base.FULL_SKY_SR * intensity / 1.0e6)

    def _build_positron(self, original: base.Curve, electron: base.Curve) -> base.Curve:
        energy = np.logspace(3.0, 10.0, 560)
        flux = np.asarray(original.at(energy), dtype=float)
        low_edge = float(original.energy_keV[0])
        high_edge = float(original.energy_keV[-1])
        electron_low = float(electron.at(low_edge))
        electron_high = float(electron.at(high_edge))
        low_ratio = float(original.at(low_edge)) / electron_low if electron_low > 0 else 0.0
        high_ratio = float(original.at(high_edge)) / electron_high if electron_high > 0 else low_ratio
        low = energy < low_edge
        high = energy > high_edge
        flux[low] = np.asarray(electron.at(energy[low])) * low_ratio
        flux[high] = np.asarray(electron.at(energy[high])) * high_ratio
        return self._curve(energy, flux)

    @staticmethod
    def _build_soft_proton_rows() -> list[dict[str, object]]:
        energy = np.logspace(math.log10(50.0), math.log10(5000.0), 180)
        cases = {
            "quiet_magnetosheath_L2": 8.6e5 * np.power(energy, -2.94),
            "worst_magnetosheath_L2": 7.0e6 * np.power(energy, -3.11),
        }
        rows: list[dict[str, object]] = []
        for case, flux in cases.items():
            for e, value in zip(energy, flux):
                rows.append(
                    {
                        "component": "directional_soft_proton",
                        "case": case,
                        "energy_keV_total": float(e),
                        "differential_intensity_cm2_s_sr_keV": float(value),
                        "validity_min_keV": 50.0,
                        "validity_max_keV": 5000.0,
                        "source": "Lotti_et_al_2021_Table_1__ARTEMIS_GEOTAIL_based",
                        "performance_role": "SEPARATE_DIRECTIONAL_SOURCE__NOT_MIXED_IN_QUIET_4PI_REWEIGHT",
                    }
                )
        return rows

    @staticmethod
    def _construction(family: str, environment: str) -> str:
        if environment == CENTRAL_L2:
            solar = "phi_0p3793GV_2009_full_GCR_max"
        else:
            solar = "phi_0p803GV_2014_GCR_min"
        return {
            "gamma": "COSI_CXB__Tuerler_low_energy_extension__4pi",
            "p": f"Athena_Usoskin_force_field_{solar}__COSI_AMS_above_100GeV__4pi",
            "alpha": f"Athena_Kuznetsov_within_0p32_400GeV__COSI_join_outside__relative_force_field_{solar}__4pi",
            "eminus": "Athena_Jovian_max_digitized_plus_published_asymptotes__4pi",
            "eplus": "COSI_AMS_support__constant_charge_ratio_extension_outside_support__4pi",
        }[family]

    def _rows_for_environment(
        self, environment: str, curves: dict[str, base.Curve]
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for family, curve in curves.items():
            for energy, value in zip(curve.energy_keV, curve.value_per_keV):
                rows.append(
                    {
                        "environment": environment,
                        "family": family,
                        "angular_domain": "full_sphere_4pi",
                        "solid_angle_sr": base.FULL_SKY_SR,
                        "energy_keV_total": float(energy),
                        "differential_flux_cm2_s_keV": float(value),
                        "construction": self._construction(family, environment),
                    }
                )
        return rows

    def target_flux(self, environment: str, family: str, energy_keV):
        if environment == CENTRAL_L2:
            curve = self.l2.get(family)
            return curve.at(energy_keV) if curve is not None else self.zero_like(energy_keV)
        if environment == SOLAR_MAX_L2:
            curve = self.l2_solar_max.get(family)
            return curve.at(energy_keV) if curve is not None else self.zero_like(energy_keV)
        return super().target_flux(environment, family, energy_keV)

    def ratio(self, environment: str, family: str, energy_keV: float) -> tuple[float, str]:
        if environment not in (CENTRAL_L2, SOLAR_MAX_L2):
            return super().ratio(environment, family, energy_keV)
        denominator_curve = self.balloon.get(family)
        denominator = float(denominator_curve.at(energy_keV)) if denominator_curve is not None else 0.0
        if denominator <= 0:
            return 0.0, "OUTSIDE_BALLOON_REFERENCE_SUPPORT"
        if family in ("n", "muminus", "muplus"):
            return 0.0, "L2_NO_EXTERNAL_PLANETARY_NEUTRON_OR_ATMOSPHERIC_MUON_COMPONENT"
        numerator = float(self.target_flux(environment, family, energy_keV))
        if family == "p":
            status = "L2_ATHENA_USOSKIN_GCR_PROTON_4PI"
        elif family == "alpha":
            status = "L2_ATHENA_KUZNETSOV_GCR_ALPHA_4PI"
        elif family == "eminus":
            status = "L2_ATHENA_JOVIAN_MAX_ELECTRON_4PI"
        elif family == "eplus" and energy_keV < self.original_eplus_min_keV:
            status = "L2_EPLUS_LOW_ENERGY_CHARGE_RATIO_EXTENSION_PROXY"
        elif family == "eplus":
            status = "L2_COSI_AMS_POSITRON_4PI"
        elif family == "gamma":
            status = "L2_COSI_CXB_4PI"
        else:
            status = "L2_UNMODELED_FAMILY"
        return numerator / denominator, status


def cached_prompt_extract(models: CompleteL2Models):
    """Reuse the already validated semantic checkpoint without rescanning SIM."""
    saved_tables = base.TABLES
    base.TABLES = BASE_PACKAGE / "outputs/tables"
    try:
        return ORIGINAL_EXTRACT_PROMPT(models)
    finally:
        base.TABLES = saved_tables


def plot_complete_environment_spectra(models: CompleteL2Models) -> None:
    fig, axes = base.plt.subplots(1, 4, figsize=(16, 6.25), sharex=True, sharey=True)
    grid_keV = np.logspace(math.log10(3.0), 10.0, 900)
    styles = {"gamma": "-", "eminus": "--", "eplus": "-.", "p": "-", "alpha": ":", "n": "--"}
    for ax, environment in zip(axes, CLASSIC_ENVIRONMENTS):
        for family in base.PLOT_FAMILIES:
            flux = np.asarray(models.target_flux(environment, family, grid_keV), dtype=float)
            base.positive_plot(
                ax,
                grid_keV / 1000.0,
                grid_keV * flux,
                color=base.FAMILY_COLOR[family],
                linestyle=styles[family],
                linewidth=2.0,
            )
        ax.axvline(0.511, color="#73808C", linewidth=0.8, linestyle=":")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(3.0e-3, 1.0e7)
        ax.set_ylim(1.0e-11, 3.0e3)
        ax.set_title(base.ENV_LABEL[environment], fontweight="bold", fontsize=13)
        ax.set_xlabel("初级粒子总动能 [MeV]")
    axes[0].set_ylabel(r"角域积分 $E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")
    axes[-1].axvspan(0.05, 5.0, color="#D7C6B2", alpha=0.22, zorder=0)
    axes[-1].text(
        0.04,
        0.07,
        "L2软质子具有方向性。",
        transform=axes[-1].transAxes,
        fontsize=8.7,
        color="#6C5744",
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 1.5},
    )
    fig.suptitle("大气、LEO、月面与日–地 L2 五族连续入射谱", x=0.045, ha="left", fontsize=20, fontweight="bold")
    fig.text(
        0.045,
        0.91,
        "总动能与角域积分通量统一；L2 quiet 五族延伸到声明支撑，HZE 因无 SH3 响应未画，方向性软质子不强行并入。",
        color="#596673",
        fontsize=11.3,
    )
    handles = [
        base.Line2D(
            [0], [0], color=base.FAMILY_COLOR[family], linestyle=styles[family], linewidth=2.2,
            label=base.FAMILY_LABEL[family]
        )
        for family in base.PLOT_FAMILIES
    ]
    handles.append(base.Line2D([0], [0], color="#73808C", linestyle=":", linewidth=1, label="511 keV"))
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False, bbox_to_anchor=(0.53, 0.075))
    fig.text(
        0.045,
        0.012,
        "L2：Athena/Usoskin p（2009, φ=0.3793 GV）；Kuznetsov α；Athena/Grimani e-；COSI/AMS e+；COSI CXB γ。",
        fontsize=8.5,
        color="#596673",
    )
    fig.subplots_adjust(left=0.055, right=0.985, top=0.82, bottom=0.19, wspace=0.10)
    base.save_figure(fig, "02_full_spectrum_comparison_sh3_l2")


def build_stream_response_bands() -> list[dict[str, object]]:
    """Build prompt/delayed primary-energy quantiles with their physical event weights."""
    prompt_rows = base.read_csv(TABLES / "sh3_prompt_w2_primary_energy.csv")
    delayed_rows = base.read_csv(base.DELAYED_SELECTED)
    activation = base.load_activation()
    samples: dict[tuple[str, str], dict[str, object]] = {}

    def bucket(stream: str, family: str) -> dict[str, object]:
        return samples.setdefault(
            (stream, family),
            {"values": [], "weights": [], "selected_events": 0, "primary_records": 0},
        )

    for row in prompt_rows:
        family = str(row["family"])
        item = bucket("prompt", family)
        item["values"].append(float(row["primary_energy_MeV_total"]))
        item["weights"].append(float(row["event_weight_cps"]))
        item["selected_events"] = int(item["selected_events"]) + 1
        item["primary_records"] = int(item["primary_records"]) + 1

    for row in delayed_rows:
        family = str(row["family"])
        key = (
            family,
            row["source_volume"],
            int(row["source_parent_ZA"]),
            base.canonical_excitation(row["excitation_keV"]),
        )
        energies = np.asarray(activation[key], dtype=float) / 1000.0
        per_record_weight = float(row["day15_event_weight_cps"]) / len(energies)
        item = bucket("delayed", family)
        item["values"].extend(energies.tolist())
        item["weights"].extend([per_record_weight] * len(energies))
        item["selected_events"] = int(item["selected_events"]) + 1
        item["primary_records"] = int(item["primary_records"]) + len(energies)

    total_rate = math.fsum(
        math.fsum(float(value) for value in item["weights"])
        for item in samples.values()
    )
    rows: list[dict[str, object]] = []
    for stream in ("prompt", "delayed"):
        for family in base.RESPONSE_PANELS:
            item = samples.get((stream, family))
            if item is None or not item["values"]:
                continue
            values = np.asarray(item["values"], dtype=float)
            weights = np.asarray(item["weights"], dtype=float)
            rate = float(np.sum(weights))
            rows.append(
                {
                    "stream": stream,
                    "family": family,
                    "selected_W2_final_events": int(item["selected_events"]),
                    "primary_energy_records": int(item["primary_records"]),
                    "response_weighted_primary_energy_p10_MeV": base.weighted_quantile(values, weights, 0.10),
                    "response_weighted_primary_energy_p50_MeV": base.weighted_quantile(values, weights, 0.50),
                    "response_weighted_primary_energy_p90_MeV": base.weighted_quantile(values, weights, 0.90),
                    "response_weight_sum_cps": rate,
                    "fraction_of_balloon_W2_final": rate / total_rate,
                }
            )
    base.write_csv(TABLES / "sh3_prompt_delayed_response_weighted_primary_energy_bands.csv", rows)
    return rows


def plot_response_without_solar_duplicate(models: CompleteL2Models, _bands) -> None:
    stream_rows = build_stream_response_bands()
    by_key = {(str(row["stream"]), str(row["family"])): row for row in stream_rows}
    stream_style = {
        "prompt": {"color": "#2A6FCB", "hatch": "///", "linestyle": "-", "label": "prompt 10–90% 能区"},
        "delayed": {"color": "#D97706", "hatch": "\\\\", "linestyle": "--", "label": "delayed 10–90% 能区"},
    }
    fig = base.plt.figure(figsize=(15, 8.3))
    grid = fig.add_gridspec(
        2, 3, left=0.055, right=0.985, top=0.83, bottom=0.09, wspace=0.28, hspace=0.48
    )
    positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
    xlimits = {
        "gamma": (1.0e-1, 1.0e6),
        "eplus": (1.0e0, 1.0e5),
        "p": (1.0e1, 1.0e6),
        "alpha": (1.0e2, 1.0e6),
        "n": (1.0e-2, 1.0e6),
    }
    for family, position in zip(base.RESPONSE_PANELS, positions):
        ax = fig.add_subplot(grid[position])
        xmin, xmax = xlimits[family]
        energy_mev = np.logspace(math.log10(xmin), math.log10(xmax), 600)
        energy_keV = energy_mev * 1000.0
        plotted_values: list[float] = []
        for environment in CLASSIC_ENVIRONMENTS:
            flux = np.asarray(models.target_flux(environment, family, energy_keV), dtype=float)
            y = energy_keV * flux
            base.positive_plot(
                ax,
                energy_mev,
                y,
                color=base.ENV_COLOR[environment],
                linestyle=base.ENV_STYLE[environment],
                linewidth=2.1,
                zorder=2,
            )
            plotted_values.extend(y[y > 0].tolist())

        annotation_y = 0.91
        for stream in ("prompt", "delayed"):
            row = by_key.get((stream, family))
            if row is None:
                continue
            style = stream_style[stream]
            low = float(row["response_weighted_primary_energy_p10_MeV"])
            high = float(row["response_weighted_primary_energy_p90_MeV"])
            ax.axvspan(
                low,
                high,
                facecolor=style["color"],
                edgecolor=style["color"],
                alpha=0.16,
                hatch=style["hatch"],
                linewidth=0.9,
                zorder=0.5,
            )
            ax.axvline(low, color=style["color"], linestyle=style["linestyle"], linewidth=1.0, alpha=0.9)
            ax.axvline(high, color=style["color"], linestyle=style["linestyle"], linewidth=1.0, alpha=0.9)
            ax.text(
                0.03,
                annotation_y,
                f"{stream}: {base.format_energy_interval(low, high)}",
                transform=ax.transAxes,
                color=style["color"],
                fontsize=9.0,
                bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 1.2},
            )
            annotation_y -= 0.09
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(xmin, xmax)
        if plotted_values:
            positive = np.asarray(plotted_values)
            ax.set_ylim(max(float(np.nanmin(positive)) / 3.0, 1.0e-12), float(np.nanmax(positive)) * 3.0)
        ax.set_title(
            base.FAMILY_CN[family],
            loc="left",
            color=base.FAMILY_COLOR[family],
            fontweight="bold",
            fontsize=13,
        )
        ax.set_xlabel("初级粒子总动能 [MeV]")
        ax.set_ylabel(r"角域积分 $E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")

    legend_ax = fig.add_subplot(grid[1, 2])
    legend_ax.axis("off")
    handles = [
        base.Line2D(
            [0],
            [0],
            color=base.ENV_COLOR[environment],
            linestyle=base.ENV_STYLE[environment],
            linewidth=2.4,
            label=base.ENV_LABEL[environment],
        )
        for environment in CLASSIC_ENVIRONMENTS
    ]
    for stream in ("prompt", "delayed"):
        style = stream_style[stream]
        handles.append(
            base.Patch(
                facecolor=style["color"],
                edgecolor=style["color"],
                alpha=0.28,
                hatch=style["hatch"],
                label=style["label"],
            )
        )
    legend_ax.legend(handles=handles, loc="center left", frameon=False, fontsize=10.5, handlelength=3.3)
    fig.suptitle(
        "四种环境入射谱与 SH3 prompt / delayed 本底能区",
        x=0.035,
        ha="left",
        fontsize=20,
        fontweight="bold",
    )
    fig.text(
        0.035,
        0.885,
        "曲线为环境源谱；蓝色/橙色阴影分别为 prompt/delayed 物理权重的 10–90% 初级能区。",
        fontsize=11.5,
        color="#596673",
    )
    base.save_figure(fig, "01_background_energy_bands_sh3_l2")


def plot_four_environment_performance(estimates) -> None:
    selected = [row for row in estimates if row["environment"] in CLASSIC_ENVIRONMENTS]
    saved = base.ENVIRONMENTS
    base.ENVIRONMENTS = CLASSIC_ENVIRONMENTS
    try:
        # This is the original compact chart, now using the literature-based
        # continuous five-family L2 solar-minimum row.
        original_plot = ORIGINAL_PLOT_PERFORMANCE
        original_plot(selected)
    finally:
        base.ENVIRONMENTS = saved


ORIGINAL_PLOT_PERFORMANCE = base.plot_performance


def plot_solar_activity(summary: dict[str, object], models: CompleteL2Models) -> None:
    by_env = summary["environment_estimates"]
    fig = base.plt.figure(figsize=(12.5, 5.8))
    gs = fig.add_gridspec(1, 2, width_ratios=(1.55, 1.05), left=0.075, right=0.97, top=0.78, bottom=0.22, wspace=0.31)
    ax = fig.add_subplot(gs[0, 0])
    energy_gev = np.logspace(-2, 3, 600)
    energy_keV = energy_gev * 1.0e6
    colors = {
        CENTRAL_L2: "#7A4CB3",
        SOLAR_MAX_L2: "#D97706",
    }
    labels = {
        CENTRAL_L2: "2009 full GCR 最大",
        SOLAR_MAX_L2: "2014 GCR 最小",
    }
    line_styles = {CENTRAL_L2: "-", SOLAR_MAX_L2: "--"}
    for environment in (CENTRAL_L2, SOLAR_MAX_L2):
        y = energy_keV * np.asarray(models.target_flux(environment, "p", energy_keV))
        base.positive_plot(
            ax,
            energy_gev,
            y,
            color=colors[environment],
            linestyle=line_styles[environment],
            linewidth=2.4,
            label=labels[environment],
        )
    ax.axvspan(PROTON_RELEVANT_MIN_GEV, PROTON_RELEVANT_MAX_GEV, color="#239344", alpha=0.14)
    ax.text(
        0.37,
        0.07,
        "SH3 p 响应 10–90%：1.37–48.4 GeV",
        transform=ax.transAxes,
        fontsize=9.2,
        color="#176C31",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1.0e-2, 1.0e3)
    ax.set_xlabel("质子总动能 [GeV]")
    ax.set_ylabel(r"4π 积分 $E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
    ax.set_title("Athena 1 AU 质子谱的太阳调制", loc="left", fontweight="bold", fontsize=14)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)

    bx = fig.add_subplot(gs[0, 1])
    environments = (CENTRAL_L2, SOLAR_MAX_L2)
    values = [float(by_env[env]["mission_relative_F3_to_SH3_balloon_including_signal_transmission"]) for env in environments]
    absolute = [float(by_env[env]["estimated_20d_F3_ph_cm2_s"]) for env in environments]
    errors = [
        float(by_env[env]["estimated_20d_F3_conditional_MC_sigma_ph_cm2_s"])
        / float(by_env[env]["SH3_balloon_official_F3_ph_cm2_s"])
        for env in environments
    ]
    bars = bx.bar(
        np.arange(2), values, width=0.52, color=[colors[env] for env in environments],
        yerr=errors, capsize=4, error_kw={"elinewidth": 1.0, "ecolor": "#4A535C", "capthick": 1.0}
    )
    bx.axhline(1.0, color="#7D8790", linewidth=1.0, linestyle="--")
    bx.set_xticks(
        [0, 1],
        ["2009 full\nGCR 最大", "2014\nGCR 最小"],
        fontsize=9.0,
    )
    bx.set_ylabel("相对 SH3 气球 Fmin")
    bx.set_ylim(0, max(values) * 1.32)
    bx.set_title("20 天安静期性能代理", loc="left", fontweight="bold", fontsize=14)
    for bar, value, flux in zip(bars, values, absolute):
        bx.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(values) * 0.045,
            f"{value:.2f}×\n{flux:.2e}",
            ha="center",
            va="bottom",
            fontsize=9.1,
            fontweight="bold",
        )

    fig.suptitle("L2 quiet-GCR 历史情景：太阳调制", x=0.045, ha="left", fontsize=19, fontweight="bold")
    fig.text(
        0.045,
        0.86,
        "2009 太阳活动极小 / GCR 最大（φ=0.3793 GV）；2014 太阳活动极大 / GCR 最小（φ=0.803 GV）。",
        color="#596673",
        fontsize=10.8,
    )
    fig.text(
        0.075,
        0.075,
        "仅表示 quiet-time 五族代理；跨周期 GCR 源模型散布、SEP/HZE/磁鞘软质子和单点 RP 相关误差未计。",
        fontsize=9.2,
        color="#596673",
    )
    base.save_figure(fig, "04_l2_solar_activity_sh3")


def integrate_curve(curve: base.Curve) -> float:
    return float(np.trapezoid(curve.value_per_keV, curve.energy_keV))


def configure_base() -> None:
    base.TABLES = TABLES
    base.FIGURES = FIGURES
    base.SUMMARY = SUMMARY
    base.ENVIRONMENTS = ALL_ENVIRONMENTS
    base.ENV_LABEL[SOLAR_MAX_L2] = "L2 太阳极大"
    base.ENV_SHORT[SOLAR_MAX_L2] = "L2 太阳极大"
    base.ENV_COLOR[SOLAR_MAX_L2] = "#D97706"
    base.ENV_STYLE[SOLAR_MAX_L2] = "--"
    base.SourceModels = CompleteL2Models
    base.extract_prompt_rows = cached_prompt_extract
    base.plot_full_spectra = plot_complete_environment_spectra
    base.plot_response_bands = plot_response_without_solar_duplicate
    base.plot_performance = plot_four_environment_performance


def postprocess() -> dict[str, object]:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    models = CompleteL2Models()
    base.write_csv(TABLES / "l2_solar_max_source_spectra.csv", models.l2_solar_max_rows)
    base.write_csv(TABLES / "l2_directional_soft_proton_spectra.csv", models.soft_proton_rows)

    central_integrals = {family: integrate_curve(curve) for family, curve in models.l2.items()}
    solar_max_integrals = {family: integrate_curve(curve) for family, curve in models.l2_solar_max.items()}
    by_env = summary["environment_estimates"]
    central = by_env[CENTRAL_L2]
    solar_max = by_env[SOLAR_MAX_L2]

    delayed_rows = [
        row
        for row in base.read_csv(TABLES / "sh3_projected_delayed_event_contributions.csv")
        if row["environment"] == CENTRAL_L2
    ]
    grouped_delayed: dict[tuple[str, str, str, str], dict[str, float | int]] = {}
    for row in delayed_rows:
        key = (
            row["family"],
            row["source_volume"],
            row["source_parent_ZA"],
            row["source_excitation_keV"],
        )
        group = grouped_delayed.setdefault(key, {"events": 0, "rate_cps": 0.0})
        group["events"] = int(group["events"]) + 1
        group["rate_cps"] = float(group["rate_cps"]) + float(row["projected_day15_event_rate_cps"])
    dominant_key, dominant_group = max(
        grouped_delayed.items(), key=lambda item: float(item[1]["rate_cps"])
    )
    response_rows = [
        row
        for row in base.read_csv(TABLES / "sh3_activation_key_energy_response.csv")
        if row["environment"] == CENTRAL_L2
        and (row["incident_family"], row["source_volume"], row["source_parent_ZA"], row["source_excitation_keV"])
        == dominant_key
    ]
    if len(response_rows) != 1:
        raise RuntimeError(f"Dominant activation key response lookup is not unique: {dominant_key}")
    dominant_response = response_rows[0]
    component_rows = [
        row
        for row in base.read_csv(TABLES / "sh3_projected_background_components.csv")
        if row["environment"] == CENTRAL_L2 and row["family"] == "eplus"
    ]
    eplus_rate = sum(float(row["projected_rate_cps"]) for row in component_rows)
    solar_rows = []
    for environment, phi, gcr_scale, role in (
        (CENTRAL_L2, PHI_2009_GV, 1.0, "observed_historical_endpoint_proxy"),
        (SOLAR_MAX_L2, PHI_2014_GV, 1.0, "observed_historical_endpoint_proxy"),
    ):
        row = by_env[environment]
        solar_rows.append(
            {
                "environment": environment,
                "modulation_potential_GV": phi,
                "charged_GCR_scale_relative_to_named_phi_curve": gcr_scale,
                "scenario_role": role,
                "projected_background_cps": row["total_rate_cps"],
                "relative_F3_to_SH3_balloon": row["mission_relative_F3_to_SH3_balloon_including_signal_transmission"],
                "estimated_20d_F3_ph_cm2_s": row["estimated_20d_F3_ph_cm2_s"],
                "conditional_MC_sigma_ph_cm2_s": row["estimated_20d_F3_conditional_MC_sigma_ph_cm2_s"],
            }
        )
    base.write_csv(TABLES / "l2_solar_activity_performance.csv", solar_rows)

    summary["schema_version"] = 2
    summary["status"] = "PASS__SH3_FIVE_FAMILY_CONTINUOUS_QUIET_L2_SOURCE_SET_AND_SOLAR_ACTIVITY_PROXY"
    summary["authority_boundary"] = "FIVE_FAMILY_PUBLIC_SOURCE_SET_RESPONSE_PROJECTION__NOT_COMPLETE_L2_ENVIRONMENT_OR_MATCHED_TRANSPORT"
    summary["L2_source_contract"] = {
        "location_semantics": "Sun-Earth L2 treated as near-Earth interplanetary space at approximately 1 AU",
        "central_quiet_case": "2009 solar minimum / GCR maximum; phi=0.3793 GV",
        "solar_activity_comparator": "2014 solar maximum / GCR minimum; phi=0.803 GV",
        "scope_name": "continuous five-family quiet-L2 source set; not a complete physical L2 environment because HZE response is absent",
        "isotropic_full_sphere_sources": {
            "gamma": "COSI cosmic background; Tuerler extension to 3 keV; 4pi",
            "p": "Athena/Usoskin force-field spectrum through 100 GeV; COSI/AMS high-energy continuation; 4pi",
            "alpha": "Athena/Kuznetsov quiet-Sun spectrum within 0.32-400 GeV total/nucleus; COSI shape joined outside; project-derived relative force-field solar-max transform; 4pi",
            "eminus": "Athena Jovian-maximum curve digitized from author source figure plus published low/high asymptotes; 4pi",
            "eplus": "COSI/AMS within measured table support; constant e+/e- charge-ratio continuation outside support; 4pi; proxy outside support",
        },
        "separate_non_isotropic_or_transient_sources": {
            "soft_protons": "Athena L2 quiet/worst magnetosheath power laws, 50-5000 keV, directional intensity; not included in quiet 4pi SH3 reweight",
            "SEP": "CREME96 worst-week/day/5-minute or mission-specific SAPPHIRE event scenarios; not a static mean",
            "Galactic_diffuse_gamma": "Fermi/COMPTEL spatial-spectral sky template; target-direction dependent; not collapsed into isotropic CXB",
        },
        "present_but_not_transportable_with_retained_SH3_families": {
            "GCR_Z_gt_2": "BON2020/CREME96/ISO-15390 static near-isotropic GCR component; physically part of quiet L2, but retained SH3 eight-family response has no HZE primary family",
        },
        "physically_absent_external_components": [
            "planetary atmospheric/regolith albedo neutrons",
            "atmospheric muons",
            "SAA/trapped-belt population",
        ],
        "full_sphere_integrated_flux_over_numeric_support_cm2_s": {
            "solar_min_2009": central_integrals,
            "solar_max_2014": solar_max_integrals,
        },
        "source_energy_support_MeV_total": {
            family: [float(curve.energy_keV[0] / 1000.0), float(curve.energy_keV[-1] / 1000.0)]
            for family, curve in models.l2.items()
        },
        "soft_proton_support_MeV_total": [0.05, 5.0],
        "unit_contract": {
            "energy": "kinetic energy per incident particle; alpha is total per nucleus, not MeV/n",
            "quiet_curve_flux": "dF/dE integrated over declared 4pi angular domain [cm^-2 s^-1 keV^-1]",
            "soft_proton_flux": "directional differential intensity [cm^-2 s^-1 sr^-1 keV^-1]",
            "angular_caveat": "4pi*J is an angular-domain integrated intensity, not the pi*J crossing rate of a flat plane; ratios are internally comparable only under the retained common source-card angular convention",
        },
        "public_mission_practice": {
            "Athena_XIFU": "Usoskin p + Kuznetsov alpha + Grimani/PAMELA electrons; soft protons modeled separately",
            "APT_L2_gamma": "BON solar-min GCR ions + Ulysses/ACE electron/quiet solar-proton fits + Fermi/COMPTEL gamma sky",
            "eROSITA_L2": "measured quiet-time soft-proton detector background used as an empirical constraint rather than an isotropic source",
        },
        "public_references": {
            "Athena_Lotti_2021": "https://arxiv.org/abs/2101.02526",
            "Usoskin_2005": "https://doi.org/10.1029/2005JA011250",
            "Kuznetsov_2017": "https://doi.org/10.1002/2016JA022920",
            "COSI_background": "https://github.com/cositools/cosi-background",
            "BON2020": "https://doi.org/10.1029/2020SW002456",
            "APT_L2_background_poster": "https://www.sudvarg.com/publications/HEAD2023_adapt_background_poster.pdf",
        },
        "Athena_reported_intercycle_GCR_maximum_sample_relative_spread": 0.26,
        "SH3_activation_RP_mapping_status_counts": summary["L2_source_contract"].get(
            "SH3_activation_RP_mapping_status_counts", {}
        ),
    }
    summary["main_L2_result"] = central
    summary["main_L2_result_solar_min_2009"] = central
    summary["L2_solar_activity_result"] = {
        "solar_min_2009": central,
        "solar_max_2014": solar_max,
        "quiet_background_ratio_solar_max_to_solar_min": float(solar_max["total_rate_cps"]) / float(central["total_rate_cps"]),
        "quiet_F3_ratio_solar_max_to_solar_min": float(solar_max["estimated_20d_F3_ph_cm2_s"]) / float(central["estimated_20d_F3_ph_cm2_s"]),
        "interpretation": "five-family quiet source-set proxy only; HZE is a missing static GCR component, while SEP duty cycle and directional soft protons are separate scenarios",
    }
    summary["dominant_L2_activation_key"] = {
        "incident_family": dominant_key[0],
        "source_volume": dominant_key[1],
        "source_parent_ZA": int(dominant_key[2]),
        "source_excitation_keV": float(dominant_key[3]),
        "shared_delayed_survivors": int(dominant_group["events"]),
        "activation_RP_records": int(dominant_response["rp_records"]),
        "primary_energy_MeV": float(dominant_response["primary_energy_p50_MeV"]),
        "source_ratio_L2_to_balloon": float(dominant_response["production_ratio_to_balloon"]),
        "projected_rate_cps": float(dominant_group["rate_cps"]),
        "fraction_of_total_L2_background": float(dominant_group["rate_cps"]) / float(central["total_rate_cps"]),
    }
    summary["eplus_coverage_proxy_impact"] = {
        "projected_rate_cps": eplus_rate,
        "fraction_of_total_L2_background": eplus_rate / float(central["total_rate_cps"]),
    }
    summary["cautions"] = [
        "The calculation reweights retained balloon transport at incident primary energy; no L2-matched prompt/activation/delayed transport was run.",
        "Four Cu-62 delayed survivors share one activation key represented by one 1.365984-GeV proton RP record; they supply about 88% of the solar-minimum total rate, and the top five delayed events supply about 95%.",
        "The reported conditional MC error does not include the correlated uncertainty of that shared RP point, angular-response mismatch, source-model uncertainty, HZE, or mission time history.",
        "Low-energy e+ outside the AMS table is a constant charge-ratio continuation and is a spectrum-coverage proxy, not a public L2 mission authority; its SH3 impact is negligible.",
        "GCR Z>2 heavy ions are a missing static quiet-L2 component; directional Galactic diffuse gamma, soft protons and SEP are separate scenarios. None can be mapped into the retained SH3 performance without a matched response.",
        "The 2014 alpha curve is a project-derived relative force-field transform, not a directly published Lotti alpha table; the SH3 alpha response band remains inside the cited Kuznetsov validity range.",
        "Athena reports about 26% sample spread between GCR maxima of different solar cycles; this source-model spread is not included in the plotted error bars.",
        "Solar maximum lowers quiet GCR, but it does not imply lower all-time operational background because SEP risk is not included.",
        "Target-environment accidental-coincidence changes and mission time histories are not modeled.",
    ]
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    plot_solar_activity(summary, models)
    return summary


def main() -> int:
    for path in (BASE_SCRIPT, ELECTRON_DIGITIZED):
        if not path.is_file():
            raise RuntimeError(f"Missing input: {path}")
    configure_base()
    base.main()
    summary = postprocess()
    result = summary["L2_solar_activity_result"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "solar_min_F3": result["solar_min_2009"]["estimated_20d_F3_ph_cm2_s"],
                "solar_max_F3": result["solar_max_2014"]["estimated_20d_F3_ph_cm2_s"],
                "solar_max_to_min_F3": result["quiet_F3_ratio_solar_max_to_solar_min"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
