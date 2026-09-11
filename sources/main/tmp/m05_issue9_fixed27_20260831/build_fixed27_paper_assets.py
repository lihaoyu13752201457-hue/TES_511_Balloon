#!/usr/bin/env python3
"""Build the fixed-27-degree paper-only mission-fold assets.

This script reads only the retained 81-node CSV summaries and compact JSON/CSV
products.  It does not read event catalogues, SIM, or NPZ files and does not
launch transport.  Detector response, background rates, five-anchor accidental
survival, and effective area remain fixed; only the atmospheric signal slant
factor is changed from 45 to 27 degrees.
"""

from __future__ import annotations

import copy
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = Path("/home/ubuntu/TES_511_Balloon")
PAPER = HERE / "paper_new"
PACKAGE70 = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "70_m05_sg3_sh3_prompt_statistics_integration_20260828"
    / "outputs"
)
TIMELINES = {
    "A": PACKAGE70 / "03_section4_timeline_a_authority_v2" / "mission_timeline_81nodes.csv",
    "B": PACKAGE70 / "03_section4_timeline_b_authority_v2" / "mission_timeline_81nodes.csv",
}
CURRENT_REPORT = (
    REPO
    / "tmp/m05_environment_extension_20260830"
    / "M05_SECTION4_REFERENCE_FLUX_20260830.json"
)
ENVIRONMENT_SCRIPT = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "71_m05_sh3_environment_screening_20260830"
    / "code/build_environment_screening.py"
)
ENVIRONMENT_RENDER_SCRIPT = HERE / "build_environment_screening_fixed27.py"
CURRENT_ENVIRONMENT_COMPACT = (
    ENVIRONMENT_SCRIPT.parents[1]
    / "outputs/tables/m05_sh3_environment_screening_compact.csv"
)

F_REF = 2.4e-4
OLD_ELEVATION_DEG = 45.0
NEW_ELEVATION_DEG = 27.0
SECONDS_PER_DAY = 86400.0
COLORS = {"A": "#0072B2", "B": "#D55E00", "muted": "#6B7280", "grid": "#D8DEE8"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def asimov_significance(signal: float, background: float) -> float:
    if signal <= 0.0:
        return 0.0
    if background <= 0.0:
        return math.sqrt(2.0 * signal)
    return math.sqrt(2.0 * ((signal + background) * math.log1p(signal / background) - signal))


def asimov_required_signal(background: float, target_z: float) -> float:
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)
    while asimov_significance(high, background) < target_z:
        high *= 2.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if asimov_significance(middle, background) < target_z:
            low = middle
        else:
            high = middle
    return high


def crossing_day(days: list[float], values: list[float], target: float) -> float:
    matches = [i for i in range(len(days) - 1) if values[i] < target <= values[i + 1]]
    if len(matches) != 1:
        raise RuntimeError(f"threshold {target} has {len(matches)} upcrossings")
    left = matches[0]
    fraction = (target - values[left]) / (values[left + 1] - values[left])
    return days[left] + fraction * (days[left + 1] - days[left])


def fold_model(model: str) -> dict[str, Any]:
    rows = read_csv(TIMELINES[model])
    if len(rows) != 81:
        raise RuntimeError(f"model {model}: expected 81 nodes")
    days = [float(row["day_mid"]) for row in rows]
    if days != [0.25 * i for i in range(81)]:
        raise RuntimeError(f"model {model}: unexpected time grid")

    exponent = math.sin(math.radians(OLD_ELEVATION_DEG)) / math.sin(
        math.radians(NEW_ELEVATION_DEG)
    )
    old_transmission = [float(row["T_atm_511_slant45"]) for row in rows]
    new_transmission = [value**exponent for value in old_transmission]
    aeff = [float(row["conditional_signal_Aeff_cm2"]) for row in rows]
    survival = [float(row["conditional_signal_accidental_survival"]) for row in rows]
    old_kernel_rate = [float(row["conditional_signal_kernel_cm2"]) for row in rows]
    new_kernel_rate = [a * eta * transmission for a, eta, transmission in zip(aeff, survival, new_transmission)]

    old_cumulative_kernel = [float(row["cumulative_signal_counts_per_unit_flux"]) for row in rows]
    recomputed_old = [0.0]
    new_cumulative_kernel = [0.0]
    for index in range(1, len(rows)):
        dt_s = (days[index] - days[index - 1]) * SECONDS_PER_DAY
        recomputed_old.append(
            recomputed_old[-1]
            + 0.5 * (old_kernel_rate[index - 1] + old_kernel_rate[index]) * dt_s
        )
        new_cumulative_kernel.append(
            new_cumulative_kernel[-1]
            + 0.5 * (new_kernel_rate[index - 1] + new_kernel_rate[index]) * dt_s
        )
    max_kernel_error = max(
        abs(expected - actual)
        for expected, actual in zip(old_cumulative_kernel, recomputed_old)
    )
    if max_kernel_error > 1.0e-7:
        raise RuntimeError(f"model {model}: old-kernel integration closure failed: {max_kernel_error}")

    background = [float(row["cumulative_background_counts"]) for row in rows]
    old_signal = [F_REF * value for value in old_cumulative_kernel]
    new_signal = [F_REF * value for value in new_cumulative_kernel]
    old_z = [signal / math.sqrt(bg) if bg > 0.0 else 0.0 for signal, bg in zip(old_signal, background)]
    new_z = [signal / math.sqrt(bg) if bg > 0.0 else 0.0 for signal, bg in zip(new_signal, background)]
    old_z_asimov = [asimov_significance(signal, bg) if bg > 0.0 else 0.0 for signal, bg in zip(old_signal, background)]
    new_z_asimov = [asimov_significance(signal, bg) if bg > 0.0 else 0.0 for signal, bg in zip(new_signal, background)]
    old_f3 = [3.0 * math.sqrt(bg) / kernel if kernel > 0.0 else math.nan for bg, kernel in zip(background, old_cumulative_kernel)]
    new_f3 = [3.0 * math.sqrt(bg) / kernel if kernel > 0.0 else math.nan for bg, kernel in zip(background, new_cumulative_kernel)]

    endpoint_bg = background[-1]
    old_endpoint_kernel = old_cumulative_kernel[-1]
    new_endpoint_kernel = new_cumulative_kernel[-1]
    current = read_json(CURRENT_REPORT)["models"][model]
    old_uncertainty = current["local_propagated_statistical_uncertainty"]
    scale = old_endpoint_kernel / new_endpoint_kernel

    gaussian = {
        "F3": 3.0 * math.sqrt(endpoint_bg) / new_endpoint_kernel,
        "F5": 5.0 * math.sqrt(endpoint_bg) / new_endpoint_kernel,
    }
    asimov = {
        "F3": asimov_required_signal(endpoint_bg, 3.0) / new_endpoint_kernel,
        "F5": asimov_required_signal(endpoint_bg, 5.0) / new_endpoint_kernel,
    }
    uncertainty = {
        "F3_gaussian": float(old_uncertainty["F3_gaussian"]["standard_error"]) * scale,
        "F5_gaussian": float(old_uncertainty["F5_gaussian"]["standard_error"]) * scale,
        "F3_asimov": float(old_uncertainty["F3_asimov"]["standard_error"]) * scale,
        "F5_asimov": float(old_uncertainty["F5_asimov"]["standard_error"]) * scale,
    }

    return {
        "days": days,
        "background": background,
        "old_transmission": old_transmission,
        "new_transmission": new_transmission,
        "old_kernel_rate": old_kernel_rate,
        "new_kernel_rate": new_kernel_rate,
        "old_cumulative_kernel": old_cumulative_kernel,
        "new_cumulative_kernel": new_cumulative_kernel,
        "old_signal": old_signal,
        "new_signal": new_signal,
        "old_z": old_z,
        "new_z": new_z,
        "old_z_asimov": old_z_asimov,
        "new_z_asimov": new_z_asimov,
        "old_f3": old_f3,
        "new_f3": new_f3,
        "day15": {
            "old_transmission": old_transmission[60],
            "new_transmission": new_transmission[60],
            "old_signal_rate_cps": F_REF * old_kernel_rate[60],
            "new_signal_rate_cps": F_REF * new_kernel_rate[60],
        },
        "mission_20d": {
            "background_counts": endpoint_bg,
            "old_signal_kernel": old_endpoint_kernel,
            "new_signal_kernel": new_endpoint_kernel,
            "old_signal_counts": old_signal[-1],
            "new_signal_counts": new_signal[-1],
            "old_Z_gaussian": old_z[-1],
            "new_Z_gaussian": new_z[-1],
            "new_Z_asimov": new_z_asimov[-1],
            "new_T3_gaussian_days": crossing_day(days, new_z, 3.0),
            "new_T5_gaussian_days": crossing_day(days, new_z, 5.0),
            "new_T3_asimov_days": crossing_day(days, new_z_asimov, 3.0),
            "new_T5_asimov_days": crossing_day(days, new_z_asimov, 5.0),
            "new_F3_gaussian": gaussian["F3"],
            "new_F5_gaussian": gaussian["F5"],
            "new_F3_asimov": asimov["F3"],
            "new_F5_asimov": asimov["F5"],
            **{f"new_sigma_{key}": value for key, value in uncertainty.items()},
        },
    }


def configure_plot() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def panel(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(-0.16, 1.08, label, transform=ax.transAxes, fontsize=9.0, fontweight="bold")


def tidy(ax: mpl.axes.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.85)
    ax.set_axisbelow(True)


def build_figure10(folds: dict[str, dict[str, Any]]) -> Path:
    configure_plot()
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.05), constrained_layout=True)
    for model, linestyle, marker in (("A", "-", "o"), ("B", "--", "s")):
        values = folds[model]
        axes[0].plot(
            values["days"], values["new_z"], color=COLORS[model], ls=linestyle,
            marker=marker, markevery=10, ms=3, label=f"Model {model}",
        )
        axes[1].plot(
            values["days"], values["new_f3"], color=COLORS[model], ls=linestyle,
            marker=marker, markevery=10, ms=3, label=f"Model {model}",
        )
        endpoint = values["mission_20d"]
        axes[1].errorbar(
            [values["days"][-1]], [endpoint["new_F3_gaussian"]],
            yerr=[endpoint["new_sigma_F3_gaussian"]], fmt=marker,
            color=COLORS[model], capsize=3, ms=4,
        )
    for threshold, label in ((3.0, "3σ"), (5.0, "5σ")):
        axes[0].axhline(
            threshold, color=COLORS["muted"], linewidth=0.8,
            linestyle="--" if threshold == 3.0 else ":",
        )
        axes[0].text(20.05, threshold, label, va="center", fontsize=6.8, color=COLORS["muted"])
    axes[0].set(
        xlabel="Mission day",
        ylabel=r"Counting significance $S/\sqrt{B}$",
        title=r"81-node fold at $F_{\mathrm{ref}}=2.4\times10^{-4}$ ph cm$^{-2}$ s$^{-1}$",
    )
    axes[0].set_xlim(0.0, 20.8)
    axes[0].legend(frameon=False)
    axes[1].set_yscale("log")
    axes[1].set(
        xlabel="Mission day",
        ylabel=r"3σ $F_{\min}$ (ph cm$^{-2}$ s$^{-1}$)",
        title="3σ minimum resolvable line flux",
    )
    axes[1].legend(frameon=False, fontsize=6.5)
    for label, ax in zip(("(a)", "(b)"), axes):
        panel(ax, label)
        tidy(ax)
    output = PAPER / "figures/section4_reference_flux_20260830/fig10_mission_performance_gaussian.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", metadata={"Title": output.stem, "Creator": Path(__file__).name})
    fig.savefig(output.with_suffix(".png"), dpi=360, bbox_inches="tight", metadata={"Title": output.stem, "Creator": Path(__file__).name})
    plt.close(fig)
    return output


def fixed_report(folds: dict[str, dict[str, Any]]) -> dict[str, Any]:
    report = copy.deepcopy(read_json(CURRENT_REPORT))
    for model in ("A", "B"):
        folded = folds[model]
        mission = report["models"][model]["mission_20d"]
        endpoint = folded["mission_20d"]
        report["models"][model]["day15_signal_rate_at_F_TOA_ref_cps"] = folded["day15"]["new_signal_rate_cps"]
        mission["signal_counts_F0"] = endpoint["new_signal_counts"]
        mission["signal_kernel_counts_per_unit_flux"] = endpoint["new_signal_kernel"]
        mission["Z_gaussian"] = endpoint["new_Z_gaussian"]
        mission["Z_asimov"] = endpoint["new_Z_asimov"]
        mission["threshold_days"] = {
            "T3_gaussian": endpoint["new_T3_gaussian_days"],
            "T5_gaussian": endpoint["new_T5_gaussian_days"],
            "T3_asimov": endpoint["new_T3_asimov_days"],
            "T5_asimov": endpoint["new_T5_asimov_days"],
        }
        for name in ("F3_gaussian", "F5_gaussian", "F3_asimov", "F5_asimov"):
            mission[name] = endpoint[f"new_{name}"]
            item = report["models"][model]["local_propagated_statistical_uncertainty"][name]
            item["value"] = endpoint[f"new_{name}"]
            item["standard_error"] = endpoint[f"new_sigma_{name}"]
            item["relative_standard_error"] = item["standard_error"] / item["value"]
    a = report["models"]["A"]["mission_20d"]
    b = report["models"]["B"]["mission_20d"]
    report["comparisons"]["mission20_signal_kernel_B_over_A"] = (
        b["signal_kernel_counts_per_unit_flux"] / a["signal_kernel_counts_per_unit_flux"]
    )
    report["comparisons"]["F3_gaussian_A_over_B"] = a["F3_gaussian"] / b["F3_gaussian"]
    report["comparisons"]["F3_gaussian_B_over_A"] = b["F3_gaussian"] / a["F3_gaussian"]
    report["fixed_elevation_paper_fold"] = {
        "old_elevation_deg": OLD_ELEVATION_DEG,
        "new_elevation_deg": NEW_ELEVATION_DEG,
        "scope": "signal atmospheric slant factor and derived 81-node mission quantities only",
        "detector_transport_rerun": False,
        "visibility_mask_applied": False,
    }
    return report


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build_figure11(report_path: Path) -> tuple[Path, dict[str, float]]:
    module = load_module(ENVIRONMENT_RENDER_SCRIPT, "m05_fixed27_environment_screening")
    module.FIGURE_DIR = PAPER / "figures/environment_screening_20260830"
    module.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    anchor = module.current_anchor(report_path)
    old = module.aggregate_package65_components()
    estimates, _ = module.build_estimates(anchor, old)
    bands = module.response_bands()
    models = module.load_models_module().CompleteL2Models()
    module.make_figure("en", models, estimates, bands)

    new_values = {str(row["environment"]): float(row["F3_screening_ph_cm2_s"]) for row in estimates}
    current_values = {
        row["environment"]: float(row["F3_screening_ph_cm2_s"])
        for row in read_csv(CURRENT_ENVIRONMENT_COMPACT)
    }
    for environment, value in new_values.items():
        if environment == "balloon_38km":
            continue
        if not math.isclose(value, current_values[environment], rel_tol=2.0e-15, abs_tol=1.0e-18):
            raise RuntimeError(f"non-balloon screening flux changed for {environment}: {value}")
    output = module.FIGURE_DIR / "fig11_environment_transfer_en.pdf"
    return output, new_values


def main() -> None:
    for path in (
        *TIMELINES.values(),
        CURRENT_REPORT,
        ENVIRONMENT_SCRIPT,
        ENVIRONMENT_RENDER_SCRIPT,
        CURRENT_ENVIRONMENT_COMPACT,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    folds = {model: fold_model(model) for model in ("A", "B")}
    figure10 = build_figure10(folds)
    report = fixed_report(folds)
    report_path = HERE / "M05_SECTION4_FIXED27_REFERENCE_FLUX_20260831.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    figure11, environment_values = build_figure11(report_path)
    audit = {
        "status": "PASS",
        "scope": "fixed 27 degree paper-only signal fold",
        "no_transport_or_large_catalog_access": True,
        "models": {
            model: {"day15": folds[model]["day15"], "mission_20d": folds[model]["mission_20d"]}
            for model in ("A", "B")
        },
        "comparisons": report["comparisons"],
        "environment_screening_fluxes": environment_values,
        "outputs": [str(figure10), str(figure11), str(report_path)],
    }
    audit_path = HERE / "fixed27_paper_asset_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(audit_path)
    print(figure10)
    print(figure11)


if __name__ == "__main__":
    main()
