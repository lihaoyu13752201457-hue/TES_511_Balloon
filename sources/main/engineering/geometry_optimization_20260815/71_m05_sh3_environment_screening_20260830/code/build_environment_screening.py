#!/usr/bin/env python3
"""Build the M05 SH3 non-balloon environmental screening figure and tables.

This package performs no transport.  It reuses only compact, retained SH3
response summaries from package 65 and anchors the two represented streams
(broadband gamma continuum and delayed activation) to the current M05 model-B
rates.  The output is an exploratory screening index, not an orbit- or
surface-matched performance forecast.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PACKAGE65 = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "65_sh3_complete_l2_solar_activity_20260820"
)
PACKAGE65_SCRIPT = PACKAGE65 / "code/build_complete_l2_solar.py"
COMPONENTS = PACKAGE65 / "outputs/tables/sh3_projected_background_components.csv"
BANDS = PACKAGE65 / "outputs/tables/sh3_prompt_delayed_response_weighted_primary_energy_bands.csv"
TABLE_DIR = PACKAGE / "outputs/tables"
FIGURE_DIR = PACKAGE / "outputs/figures"
SUMMARY = PACKAGE / "outputs/summary.json"
VALIDATION = PACKAGE / "data/validation.json"
INPUT_MANIFEST = PACKAGE / "data/input_manifest.json"

DEFAULT_CURRENT_JSON = (
    Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
    / "core_md/balloon511_ea_latex_drafts/M05NEW/"
    "M05_SECTION4_REFERENCE_FLUX_20260830.json"
)

ENVIRONMENTS = (
    "balloon_38km",
    "leo530_quiet_proxy",
    "lunar_surface_proxy",
    "sun_earth_l2_solar_max_2014",
    "sun_earth_l2_quiet_1au_proxy",
)
TARGET_ENVIRONMENTS = ENVIRONMENTS[1:]

LABEL_EN = {
    "balloon_38km": "38 km balloon",
    "leo530_quiet_proxy": "530 km LEO\n(non-SAA)",
    "lunar_surface_proxy": "Lunar surface\nproxy",
    "sun_earth_l2_solar_max_2014": "Sun–Earth L2\n2014 GCR-low",
    "sun_earth_l2_quiet_1au_proxy": "Sun–Earth L2\n2009 GCR-high",
}
LABEL_ZH = {
    "balloon_38km": "38 km 气球",
    "leo530_quiet_proxy": "530 km LEO\n（非 SAA）",
    "lunar_surface_proxy": "月面代理",
    "sun_earth_l2_solar_max_2014": "日–地 L2\n2014 GCR 低",
    "sun_earth_l2_quiet_1au_proxy": "日–地 L2\n2009 GCR 高",
}

COLOR = {
    "balloon_38km": "#333333",
    "leo530_quiet_proxy": "#0072B2",
    "lunar_surface_proxy": "#D55E00",
    "sun_earth_l2_solar_max_2014": "#CC79A7",
    "sun_earth_l2_quiet_1au_proxy": "#009E73",
}
STYLE = {
    "balloon_38km": "-",
    "leo530_quiet_proxy": "--",
    "lunar_surface_proxy": "-.",
    "sun_earth_l2_solar_max_2014": ":",
    "sun_earth_l2_quiet_1au_proxy": "-",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_models_module():
    spec = importlib.util.spec_from_file_location("m05_package65_models", PACKAGE65_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {PACKAGE65_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def current_anchor(current_json: Path) -> dict[str, float]:
    data = json.loads(current_json.read_text(encoding="utf-8"))
    model = data["models"]["B"]
    streams = model["day15_final_physical_streams"]
    mission = model["mission_20d"]
    exposure_s = 20.0 * 86400.0
    aeff = float(model["signal_effective_area_cm2"])
    kernel = float(mission["signal_kernel_counts_per_unit_flux"])
    tau_balloon = kernel / (aeff * exposure_s)
    return {
        "gamma_continuum_cps": float(streams["gamma_continuum"]["rate_cps"]),
        "delayed_cps": float(streams["delayed"]["rate_cps"]),
        "prompt_eplus_unmapped_cps": float(streams["prompt_seven"]["rate_cps"]),
        "prompt_eplus_unmapped_fraction": float(streams["prompt_seven"]["fraction_of_final"]),
        "total_day15_cps": float(model["day15_cutflow"]["compton_trajectory_veto"]["rate_cps"]),
        "F3_gaussian_ph_cm2_s": float(mission["F3_gaussian"]),
        "F3_gaussian_sigma_ph_cm2_s": float(
            model["local_propagated_statistical_uncertainty"]["F3_gaussian"]["standard_error"]
        ),
        "signal_effective_area_cm2": aeff,
        "signal_kernel_counts_per_unit_flux": kernel,
        "effective_balloon_signal_transmission": tau_balloon,
    }


def aggregate_package65_components() -> dict[str, dict[str, float]]:
    rows = read_csv(COMPONENTS)
    aggregate: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "gamma_cps": 0.0,
            "gamma_variance_cps2": 0.0,
            "delayed_cps": 0.0,
            "delayed_variance_cps2": 0.0,
        }
    )
    for row in rows:
        environment = row["environment"]
        stream = row["stream"]
        family = row["family"]
        rate = float(row["projected_rate_cps"])
        variance = float(row["conditional_mc_sigma_cps"]) ** 2
        if stream == "prompt" and family == "gamma":
            aggregate[environment]["gamma_cps"] += rate
            aggregate[environment]["gamma_variance_cps2"] += variance
        elif stream == "delayed":
            aggregate[environment]["delayed_cps"] += rate
            aggregate[environment]["delayed_variance_cps2"] += variance
    missing = [environment for environment in ENVIRONMENTS if environment not in aggregate]
    if missing:
        raise RuntimeError(f"Missing package-65 environments: {missing}")
    return dict(aggregate)


def response_bands() -> dict[tuple[str, str], tuple[float, float, float]]:
    result: dict[tuple[str, str], tuple[float, float, float]] = {}
    for row in read_csv(BANDS):
        result[(row["stream"], row["family"])] = (
            float(row["response_weighted_primary_energy_p10_MeV"]),
            float(row["response_weighted_primary_energy_p50_MeV"]),
            float(row["response_weighted_primary_energy_p90_MeV"]),
        )
    return result


def build_estimates(
    anchor: dict[str, float],
    old: dict[str, dict[str, float]],
) -> tuple[list[dict[str, object]], dict[str, float]]:
    balloon_old = old["balloon_38km"]
    gamma_scale = anchor["gamma_continuum_cps"] / balloon_old["gamma_cps"]
    delayed_scale = anchor["delayed_cps"] / balloon_old["delayed_cps"]
    represented_balloon = anchor["gamma_continuum_cps"] + anchor["delayed_cps"]
    f3_anchor = anchor["F3_gaussian_ph_cm2_s"]
    tau_balloon = anchor["effective_balloon_signal_transmission"]

    rows: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        item = old[environment]
        gamma = gamma_scale * item["gamma_cps"]
        delayed = delayed_scale * item["delayed_cps"]
        variance = (
            gamma_scale**2 * item["gamma_variance_cps2"]
            + delayed_scale**2 * item["delayed_variance_cps2"]
        )
        represented = gamma + delayed
        ratio = represented / represented_balloon
        neff_weight = represented**2 / variance if variance > 0.0 else 0.0
        if environment == "balloon_38km":
            screening_factor = 1.0
        else:
            screening_factor = tau_balloon * math.sqrt(ratio)
        f3_screen = f3_anchor * screening_factor
        rows.append(
            {
                "environment": environment,
                "geometry": "SH3_model_B",
                "represented_streams": "gamma_continuum_plus_delayed_activation",
                "reanchored_gamma_cps": gamma,
                "reanchored_delayed_cps": delayed,
                "represented_background_cps": represented,
                "represented_background_ratio_to_balloon": ratio,
                "weight_concentration_Neff_w": neff_weight,
                "assumed_target_signal_transmission": (
                    tau_balloon if environment == "balloon_38km" else 1.0
                ),
                "F3_screening_factor_to_current_balloon": screening_factor,
                "F3_screening_ph_cm2_s": f3_screen,
                "authority": "EXPLORATORY_TWO_STREAM_SCREENING_INDEX",
            }
        )
    scales = {
        "package65_to_current_gamma_stream_scale": gamma_scale,
        "package65_to_current_delayed_stream_scale": delayed_scale,
    }
    return rows, scales


def positive_plot(ax, x: np.ndarray, y: np.ndarray, **kwargs) -> None:
    mask = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
    ax.plot(x[mask], y[mask], **kwargs)


def configure_plot(language: str) -> None:
    if language == "zh":
        cjk_font = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
        if not cjk_font.is_file():
            raise FileNotFoundError(cjk_font)
        font_manager.fontManager.addfont(cjk_font)
        sans = font_manager.FontProperties(fname=cjk_font).get_name()
    else:
        sans = "DejaVu Sans"
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [sans, "DejaVu Sans"],
            "font.size": 9.2,
            "axes.linewidth": 0.8,
            "axes.labelsize": 9.4,
            "axes.titlesize": 10.0,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 7.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
        }
    )


def make_figure(
    language: str,
    models,
    estimates: list[dict[str, object]],
    bands: dict[tuple[str, str], tuple[float, float, float]],
) -> None:
    configure_plot(language)
    labels = LABEL_ZH if language == "zh" else LABEL_EN
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(13.0, 4.05),
        gridspec_kw={"width_ratios": [1.15, 1.15, 0.92]},
    )
    gamma_ax, proton_ax, performance_ax = axes

    gamma_energy_mev = np.logspace(-1.2, 5.0, 700)
    gamma_energy_kev = gamma_energy_mev * 1.0e3
    proton_energy_gev = np.logspace(-2.0, 3.0, 700)
    proton_energy_kev = proton_energy_gev * 1.0e6

    spectrum_environments = (
        "balloon_38km",
        "leo530_quiet_proxy",
        "lunar_surface_proxy",
        "sun_earth_l2_quiet_1au_proxy",
    )
    for environment in spectrum_environments:
        gamma_y = gamma_energy_kev * np.asarray(
            models.target_flux(environment, "gamma", gamma_energy_kev), dtype=float
        )
        positive_plot(
            gamma_ax,
            gamma_energy_mev,
            gamma_y,
            color=COLOR[environment],
            linestyle=STYLE[environment],
            linewidth=1.7,
            label=labels[environment].replace("\n", " "),
        )

    proton_environments = spectrum_environments + ("sun_earth_l2_solar_max_2014",)
    for environment in proton_environments:
        proton_y = proton_energy_kev * np.asarray(
            models.target_flux(environment, "p", proton_energy_kev), dtype=float
        )
        positive_plot(
            proton_ax,
            proton_energy_gev,
            proton_y,
            color=COLOR[environment],
            linestyle=STYLE[environment],
            linewidth=1.7,
            label=labels[environment].replace("\n", " "),
        )

    gamma_low, _, gamma_high = bands[("prompt", "gamma")]
    proton_low_mev, _, proton_high_mev = bands[("delayed", "p")]
    gamma_ax.axvspan(gamma_low, gamma_high, color="#56B4E9", alpha=0.18, linewidth=0)
    proton_ax.axvspan(
        proton_low_mev / 1.0e3,
        proton_high_mev / 1.0e3,
        color="#E69F00",
        alpha=0.18,
        linewidth=0,
    )

    for ax in (gamma_ax, proton_ax):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(True, which="major", color="#D9DEE3", linewidth=0.6)
        ax.grid(True, which="minor", color="#EEF0F2", linewidth=0.35)
        ax.tick_params(direction="in", which="both")

    gamma_ax.set_xlim(7.0e-2, 1.0e5)
    proton_ax.set_xlim(1.0e-2, 1.0e3)
    gamma_ax.set_ylim(1.0e-10, 3.0e3)
    proton_ax.set_ylim(1.0e-9, 3.0e3)
    gamma_ax.set_xlabel(
        "Primary photon energy (MeV)" if language == "en" else "初级光子能量（MeV）"
    )
    proton_ax.set_xlabel(
        "Primary proton energy (GeV)" if language == "en" else "初级质子能量（GeV）"
    )
    gamma_ax.set_ylabel(
        r"Angle-integrated $E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)"
        if language == "en"
        else r"角域积分 $E\,d\Phi/dE$（cm$^{-2}$ s$^{-1}$）"
    )
    proton_ax.set_ylabel(
        r"Angle-integrated $E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)"
        if language == "en"
        else r"角域积分 $E\,d\Phi/dE$（cm$^{-2}$ s$^{-1}$）"
    )
    gamma_ax.set_title(
        "Photon fields and prompt response"
        if language == "en"
        else "光子环境与瞬发响应能区",
        loc="left",
    )
    proton_ax.set_title(
        "Proton fields and activation response"
        if language == "en"
        else "质子环境与活化响应能区",
        loc="left",
    )
    gamma_ax.text(
        0.03,
        0.04,
        f"{gamma_low:.3g}–{gamma_high:.3g} MeV",
        transform=gamma_ax.transAxes,
        color="#176B87",
        fontsize=8.0,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
    )
    proton_ax.text(
        0.03,
        0.04,
        f"{proton_low_mev / 1.0e3:.3g}–{proton_high_mev / 1.0e3:.3g} GeV",
        transform=proton_ax.transAxes,
        color="#965F00",
        fontsize=8.0,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
    )
    gamma_ax.legend(frameon=False, loc="upper right")
    proton_ax.legend(frameon=False, loc="upper right")

    by_env = {str(row["environment"]): row for row in estimates}
    display_env = (
        "balloon_38km",
        "leo530_quiet_proxy",
        "lunar_surface_proxy",
        "sun_earth_l2_solar_max_2014",
        "sun_earth_l2_quiet_1au_proxy",
    )
    x = np.arange(len(display_env), dtype=float)
    y = np.asarray(
        [float(by_env[environment]["F3_screening_ph_cm2_s"]) / 1.0e-5 for environment in display_env]
    )
    for index, environment in enumerate(display_env):
        performance_ax.scatter(
            x[index],
            y[index],
            s=54,
            facecolor="white",
            edgecolor=COLOR[environment],
            linewidth=1.8,
            zorder=3,
        )
        performance_ax.text(
            x[index],
            y[index] + 0.25,
            f"{y[index]:.2f}",
            ha="center",
            va="bottom",
            color=COLOR[environment],
            fontsize=7.8,
        )
    performance_ax.plot(
        x[-2:],
        y[-2:],
        color="#777777",
        linewidth=1.0,
        zorder=1,
    )
    performance_ax.axhline(y[0], color="#888888", linestyle="--", linewidth=0.9)
    performance_ax.set_xlim(-0.55, len(display_env) - 0.45)
    performance_ax.set_ylim(0.0, 8.4)
    performance_ax.set_xticks(x)
    performance_ax.set_xticklabels([labels[environment] for environment in display_env], rotation=28, ha="right")
    performance_ax.set_ylabel(
        r"20 d $3\sigma$ screening flux ($10^{-5}$ ph cm$^{-2}$ s$^{-1}$)"
        if language == "en"
        else r"20 d、$3\sigma$ 筛查通量（$10^{-5}$ ph cm$^{-2}$ s$^{-1}$）"
    )
    performance_ax.set_title(
        "Environmental screening flux"
        if language == "en"
        else "不同环境的筛查通量",
        loc="left",
    )
    performance_ax.grid(True, axis="y", color="#D9DEE3", linewidth=0.6)
    performance_ax.tick_params(direction="in", axis="y")

    for letter, ax in zip(("a", "b", "c"), axes):
        ax.text(
            -0.14,
            1.06,
            f"({letter})",
            transform=ax.transAxes,
            fontsize=11.2,
            fontweight="bold",
            va="bottom",
        )

    fig.subplots_adjust(left=0.068, right=0.992, top=0.90, bottom=0.22, wspace=0.32)
    basename = f"fig11_environment_transfer_{language}"
    fig.savefig(FIGURE_DIR / f"{basename}.pdf", bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{basename}.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-json", type=Path, default=DEFAULT_CURRENT_JSON)
    args = parser.parse_args()
    current_json = args.current_json.resolve()
    for path in (current_json, PACKAGE65_SCRIPT, COMPONENTS, BANDS):
        if not path.is_file():
            raise FileNotFoundError(path)

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    anchor = current_anchor(current_json)
    old = aggregate_package65_components()
    estimates, scales = build_estimates(anchor, old)
    bands = response_bands()
    module = load_models_module()
    models = module.CompleteL2Models()

    write_csv(TABLE_DIR / "m05_sh3_environment_screening.csv", estimates)
    compact_table = [
        {
            "environment": row["environment"],
            "represented_background_ratio_to_balloon": row[
                "represented_background_ratio_to_balloon"
            ],
            "F3_screening_factor_to_current_balloon": row[
                "F3_screening_factor_to_current_balloon"
            ],
            "F3_screening_ph_cm2_s": row["F3_screening_ph_cm2_s"],
            "weight_concentration_Neff_w": row["weight_concentration_Neff_w"],
        }
        for row in estimates
    ]
    write_csv(TABLE_DIR / "m05_sh3_environment_screening_compact.csv", compact_table)
    make_figure("en", models, estimates, bands)
    make_figure("zh", models, estimates, bands)

    manifest = {
        "current_m05_reference": {"path": str(current_json), "sha256": sha256(current_json)},
        "package65_component_table": {"path": str(COMPONENTS), "sha256": sha256(COMPONENTS)},
        "package65_response_bands": {"path": str(BANDS), "sha256": sha256(BANDS)},
        "package65_source_models": {
            "path": str(PACKAGE65_SCRIPT),
            "sha256": sha256(PACKAGE65_SCRIPT),
        },
    }
    write_json(INPUT_MANIFEST, manifest)

    by_env = {str(row["environment"]): row for row in estimates}
    validation = {
        "status": "PASS",
        "no_transport_or_large_catalog_access": True,
        "balloon_reanchored_gamma_closure": math.isclose(
            float(by_env["balloon_38km"]["reanchored_gamma_cps"]),
            anchor["gamma_continuum_cps"],
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ),
        "balloon_reanchored_delayed_closure": math.isclose(
            float(by_env["balloon_38km"]["reanchored_delayed_cps"]),
            anchor["delayed_cps"],
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ),
        "balloon_screening_anchor_closure": math.isclose(
            float(by_env["balloon_38km"]["F3_screening_ph_cm2_s"]),
            anchor["F3_gaussian_ph_cm2_s"],
            rel_tol=0.0,
            abs_tol=1.0e-16,
        ),
        "all_values_finite": all(
            math.isfinite(float(value))
            for row in estimates
            for key, value in row.items()
            if key
            in {
                "reanchored_gamma_cps",
                "reanchored_delayed_cps",
                "represented_background_cps",
                "represented_background_ratio_to_balloon",
                "weight_concentration_Neff_w",
                "F3_screening_factor_to_current_balloon",
                "F3_screening_ph_cm2_s",
            }
        ),
        "authority": "EXPLORATORY_RESPONSE_WEIGHTED_SCREENING_NOT_ENVIRONMENT_TRANSPORT_AUTHORITY",
    }
    if not all(value is True for key, value in validation.items() if key.endswith("closure")):
        validation["status"] = "FAIL"
    write_json(VALIDATION, validation)

    summary = {
        "status": validation["status"],
        "authority": validation["authority"],
        "method": {
            "represented_streams": ["gamma_continuum", "delayed_activation"],
            "stream_level_reanchoring": scales,
            "screening_equation": (
                "F3_screen/F3_balloon = (tau_balloon/tau_target) * "
                "sqrt(B2_target/B2_balloon), tau_target=1 for non-balloon scenarios"
            ),
            "full_background_fractional_change_closure": (
                "For the dimensionless index only, the fractional change of the "
                "complete background is assumed to follow B2_target/B2_balloon; "
                "this carries the unmapped prompt share with the aggregate two-stream "
                "ratio without claiming a family-resolved target prompt rate."
            ),
            "unmapped_current_stream": {
                "stream": "prompt_eplus",
                "balloon_rate_cps": anchor["prompt_eplus_unmapped_cps"],
                "fraction_of_current_balloon_final": anchor[
                    "prompt_eplus_unmapped_fraction"
                ],
                "reason": "no compact target-environment primary-energy response kernel",
            },
        },
        "current_balloon_anchor": anchor,
        "response_bands": {
            "prompt_gamma_p10_p90_MeV": [
                bands[("prompt", "gamma")][0],
                bands[("prompt", "gamma")][2],
            ],
            "delayed_proton_p10_p90_GeV": [
                bands[("delayed", "p")][0] / 1.0e3,
                bands[("delayed", "p")][2] / 1.0e3,
            ],
        },
        "environment_estimates": by_env,
        "limitations": [
            "stream-level rather than current event-level reanchoring",
            "current prompt-eplus stream is not independently transferred; the index "
            "assumes its fractional change follows the mapped two-stream aggregate",
            "no environment-matched prompt-to-activation-to-delayed transport",
            "no target-environment common-time veto or accidental-survival fold",
            "same detector-cryostat mass model, not a complete satellite or surface payload",
            "LEO SAA and trapped particles omitted",
            "lunar local terrain and lander infrastructure omitted",
            "Sun-Earth L2 SEP, HZE, and directional soft protons omitted",
            "weight-concentration Neff_w is diagnostic, not a confidence interval",
        ],
        "inputs": manifest,
    }
    write_json(SUMMARY, summary)
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
