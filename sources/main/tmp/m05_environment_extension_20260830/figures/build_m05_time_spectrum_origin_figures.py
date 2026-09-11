#!/usr/bin/env python3
"""Build the M05 trajectory, veto-spectrum, and background-origin figures.

Only compact derived CSV summaries are read.  No SIM, NPZ, or job-catalogue
payload is opened by this script.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

HIST = REPO / "engineering/trajectory_transport_validation_20260709/11_analytic_agreement_20260709"
HIST_POINTS = REPO / "engineering/trajectory_transport_validation_20260709/01_points/validation_points.csv"
P67 = REPO / "engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823"
TIMELINE = {
    "A": P67 / "outputs/03_fluxclosed_timeline_a",
    "B": P67 / "outputs/03_fluxclosed_timeline_b",
}
ORIGIN_A = REPO / "engineering/geometry_optimization_20260815/60_sg3b_time_audit_nuclide_section_20260818/outputs/selected_w2_activation_origin_groups.csv"
ORIGIN_B = REPO / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/optv3_delayed_origin_breakdown.csv"
REGIONS = REPO / "engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/data/cold_stage_origin_share.csv"

W2 = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
STAGES = (
    "pre_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)

COLORS = {
    "ink": "#222222",
    "muted": "#6B7280",
    "grid": "#D8DEE8",
    "A": "#0072B2",
    "B": "#D55E00",
    "corrected": "#198754",
    "old": "#7A7A7A",
    "pre_veto": "#222222",
    "combined_active_veto": "#56B4E9",
    "compton_trajectory_veto": "#D55E00",
    "copper": "#D49A00",
    "aluminium": "#56B4E9",
    "tungsten": "#6B7280",
    "bi_ta": "#CC79A7",
    "other": "#B8C0CC",
    "cold": "#009E73",
    "near": "#E69F00",
    "other_region": "#6B7280",
}


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def number(row: dict[str, str], key: str) -> float:
    return float(row[key])


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.5,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def tidy(ax: mpl.axes.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.85)
    ax.set_axisbelow(True)


def panel(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(-0.16, 1.08, label, transform=ax.transAxes, fontsize=9.0, fontweight="bold")


def save(fig: mpl.figure.Figure, basename: str) -> None:
    fig.savefig(HERE / f"{basename}.pdf", bbox_inches="tight")
    fig.savefig(HERE / f"{basename}.png", dpi=360, bbox_inches="tight")
    plt.close(fig)


def build_trajectory_validation() -> None:
    curve = rows(HIST / "claude_source_response_curve_by_time.csv")
    points = {row["point_id"]: row for row in rows(HIST_POINTS)}
    audit = {
        row["point_id"]: row
        for row in rows(HIST / "analytic_agreement_rows.csv")
        if row["scope"] == "combined_species"
        and row["metric"] == "band480_550"
        and row["model"] == "live_parma_species_weighted"
    }
    if len(curve) != 81 or set(audit) != {"L1", "H1", "L2"}:
        raise RuntimeError("historical prompt-validation summary is incomplete")

    day = [number(row, "day_mid") for row in curve]
    altitude = [number(row, "altitude_km") for row in curve]
    latitude = [number(row, "latitude_deg") for row in curve]
    longitude = [number(row, "longitude_deg") for row in curve]
    corrected = [number(row, "corrected_band_family_response") for row in curve]
    old = [number(row, "old_prompt_scale") for row in curve]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.15, 2.75),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [0.95, 1.0, 1.55]},
    )

    axes[0].plot(day, altitude, color=COLORS["A"])
    for name in ("L1", "H1", "REF", "L2"):
        p = points[name]
        axes[0].scatter(number(p, "day_mid"), number(p, "altitude_km"), s=20, color=COLORS["corrected"], edgecolor="white", linewidth=0.5, zorder=4)
        axes[0].annotate(name, (number(p, "day_mid"), number(p, "altitude_km")), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=6.2)
    axes[0].set(xlabel="Mission day", ylabel="Altitude (km)", title="Synthetic altitude profile")
    axes[0].set_xlim(0, 20)
    panel(axes[0], "(a)")
    tidy(axes[0])

    axes[1].plot(longitude, latitude, color=COLORS["muted"], linewidth=1.0)
    sample = list(range(0, len(day), 4))
    scatter = axes[1].scatter([longitude[i] for i in sample], [latitude[i] for i in sample], c=[day[i] for i in sample], cmap="viridis", s=14, edgecolor="white", linewidth=0.25, zorder=3)
    for name in ("L1", "H1", "REF", "L2"):
        p = points[name]
        axes[1].annotate(name, (number(p, "longitude_deg"), number(p, "latitude_deg")), xytext=(3, 3), textcoords="offset points", fontsize=6.2)
    cbar = fig.colorbar(scatter, ax=axes[1], fraction=0.08, pad=0.03)
    cbar.set_label("Mission day", fontsize=6.5)
    cbar.ax.tick_params(labelsize=5.8)
    axes[1].set(xlabel="Longitude (deg)", ylabel="Latitude (deg)", title="Reference ground track")
    panel(axes[1], "(b)")
    tidy(axes[1])

    axes[2].plot(day, corrected, color=COLORS["corrected"], label="Family-resolved prompt fold")
    axes[2].plot(day, old, color=COLORS["old"], linestyle="--", label="Former shared scalar")
    axes[2].axhline(1.0, color=COLORS["muted"], linestyle=":", linewidth=0.8)
    for name in ("L1", "H1", "L2"):
        p = points[name]
        a = audit[name]
        x = number(p, "day_mid")
        y = number(a, "mc_ratio_to_REF")
        yerr = number(a, "sigma_ratio")
        axes[2].errorbar(x, y, yerr=yerr, fmt="D", ms=4.0, color="#C43C2F", markerfacecolor="white", capsize=2.2, zorder=5)
        axes[2].annotate(f"{name}  Q={number(a, 'Q'):.3f}", (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=6.1, color="#7D241C")
    axes[2].scatter([15.0], [1.0], marker="D", s=24, color="#C43C2F", facecolor="white", zorder=5)
    axes[2].annotate("REF", (15.0, 1.0), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=6.1)
    axes[2].set(xlabel="Mission day", ylabel="Rate scale / day 15", title="Independent prompt-fold test")
    axes[2].set_xlim(0, 20)
    axes[2].set_ylim(0.86, 1.16)
    axes[2].legend(frameon=False, loc="lower right")
    panel(axes[2], "(c)")
    tidy(axes[2])
    save(fig, "fig04_trajectory_prompt_validation")


def _selected_anchor(model: str) -> list[dict[str, str]]:
    selected = [
        row
        for row in rows(TIMELINE[model] / "anchor_timeline_rates.csv")
        if row["window_id"] == W2 and row["stage"] == FINAL_STAGE
    ]
    selected.sort(key=lambda row: number(row, "day_mid"))
    if [number(row, "day_mid") for row in selected] != [0.0, 5.0, 10.0, 15.0, 20.0]:
        raise RuntimeError(f"model-{model} anchor grid differs")
    return selected


def build_anchor_diagnostic() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.9), constrained_layout=True)
    for model, linestyle, marker in (("A", "-", "o"), ("B", "--", "s")):
        mission = rows(TIMELINE[model] / "mission_timeline_81nodes.csv")
        anchor = _selected_anchor(model)
        day = [number(row, "day_mid") for row in mission]
        direct = [number(row, "direct_W2_final_no_coincidence_cps") for row in mission]
        common = [number(row, "mature_background_W2_final_cps") for row in mission]
        ratio = [number(row, "interpolated_background_timeline_ratio") for row in mission]
        survival = [number(row, "conditional_signal_accidental_survival") for row in mission]
        color = COLORS[model]
        axes[0].plot(day, direct, color=color, linestyle=":", linewidth=1.0, label=f"{model} direct")
        axes[0].plot(day, common, color=color, linestyle=linestyle, label=f"{model} common time")
        axes[0].errorbar(
            [number(row, "day_mid") for row in anchor],
            [number(row, "timeline_rate_cps") for row in anchor],
            yerr=[number(row, "timeline_rate_standard_error_cps") for row in anchor],
            fmt=marker,
            ms=3.2,
            color=color,
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
        axes[1].plot(day, ratio, color=color, linestyle=linestyle, label=rf"{model} $\rho$")
        axes[1].plot(day, survival, color=color, linestyle=":", label=rf"{model} $\eta$")
        axes[1].errorbar(
            [number(row, "day_mid") for row in anchor],
            [number(row, "timeline_to_direct_ratio") for row in anchor],
            yerr=[number(row, "timeline_rate_standard_error_cps") / number(row, "direct_no_coincidence_rate_cps") for row in anchor],
            fmt=marker,
            ms=3.0,
            color=color,
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
        axes[1].errorbar(
            [number(row, "day_mid") for row in anchor],
            [number(row, "signal_accidental_survival") for row in anchor],
            yerr=[number(row, "signal_survival_standard_error") for row in anchor],
            fmt="^" if model == "A" else "v",
            ms=3.0,
            color=color,
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
    axes[0].set(xlabel="Mission day", ylabel=r"Final-window rate (s$^{-1}$)", title="81-node rate curves and five anchors")
    axes[0].set_xlim(0, 20)
    axes[0].legend(frameon=False, ncol=2, loc="lower center")
    axes[1].axhline(1.0, color=COLORS["muted"], linestyle=(0, (3, 2)), linewidth=0.8)
    axes[1].set(xlabel="Mission day", ylabel="Dimensionless factor", title="Interpolated timing factors")
    axes[1].set_xlim(0, 20)
    axes[1].set_ylim(0.82, 1.02)
    axes[1].legend(frameon=False, ncol=2, loc="lower center")
    for label, ax in zip(("(a)", "(b)"), axes):
        panel(ax, label)
        tidy(ax)
    save(fig, "fig04_common_time_normalization")


def _broad_spectrum(model: str, stage: str, display_width_keV: float = 1.0) -> tuple[list[float], list[float], list[float]]:
    source = rows(TIMELINE[model] / "direct_measured_energy_day15_0p25keV.csv")
    selected = [
        row
        for row in source
        if row["stage"] == stage
        and row["stream"] == "all"
        and row["component"] in {"other", "gamma_continuum"}
    ]
    bins: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for row in selected:
        low = number(row, "energy_low_keV")
        index = int(math.floor((low - 480.0) / display_width_keV + 1.0e-9))
        bins[index][0] += number(row, "sumw_cps")
        bins[index][1] += number(row, "sumw2_cps2")
    expected = int(round(70.0 / display_width_keV))
    if set(bins) != set(range(expected)):
        raise RuntimeError(f"model-{model} {stage} broad spectrum is incomplete")
    x = [480.0 + (index + 0.5) * display_width_keV for index in range(expected)]
    y = [bins[index][0] for index in range(expected)]
    sigma = [math.sqrt(bins[index][1]) for index in range(expected)]
    return x, y, sigma


def build_veto_spectra() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.0), constrained_layout=True, sharey=True)
    labels = {
        "pre_veto": "Before active veto",
        "combined_active_veto": "After active veto",
        "compton_trajectory_veto": "After Compton veto",
    }
    styles = {
        "pre_veto": "-",
        "combined_active_veto": "--",
        "compton_trajectory_veto": "-.",
    }
    for ax, model, label in zip(axes, ("A", "B"), ("(a)", "(b)")):
        for stage in STAGES:
            x, y, _ = _broad_spectrum(model, stage)
            plotted = [value if value > 0.0 else math.nan for value in y]
            total = math.fsum(y)
            ax.step(x, plotted, where="mid", color=COLORS[stage], linestyle=styles[stage], label=f"{labels[stage]}  ({total:.3g} s$^{{-1}}$)")
        ax.set_yscale("log")
        ax.set_ylim(1.0e-6, 3.0)
        ax.set_xlim(480, 550)
        ax.set(xlabel="Measured TES energy (keV)", title=f"Mass model {model}")
        ax.legend(frameon=False, loc="upper right")
        panel(ax, label)
        tidy(ax)
    axes[0].set_ylabel(r"Rate per 1-keV display bin (s$^{-1}$)")
    save(fig, "fig05_broadband_veto_spectra")


def _family_rates(model: str) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for row in rows(TIMELINE[model] / "direct_cutflow_day15.csv"):
        if row["window_id"] != W2 or row["stage"] != FINAL_STAGE or row["component"] == "atm511":
            continue
        result[row["family"]] += number(row, "sumw_cps")
    return dict(result)


def _material_group(name: str) -> str:
    if name == "Copper":
        return "Copper"
    if name == "Aluminium":
        return "Aluminium"
    if name == "W":
        return "W"
    if name in {"Bi", "Ta"}:
        return "Bi/Ta"
    return "Other"


def _short_origin(text: str, limit: int = 29) -> str:
    replacements = {
        "L2 Cu open-ring +z' panel": "L2 Cu support ring",
        "MXC 50 mK Cu cold plate": "MXC 50 mK Cu plate",
        "SG3B L0 Cu heat-sink ring": "L0 Cu heat-sink ring",
        "SG3B Bi upper half-cylinder": "Bi upper half-cylinder",
    }
    text = replacements.get(text, text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_background_origins() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.15, 5.75), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.035, h_pad=0.045, wspace=0.06, hspace=0.09)

    family = {model: _family_rates(model) for model in ("A", "B")}
    display = ["p", "gamma", "alpha", "n", "eplus", "eminus", "muons"]
    label_map = {"p": "p", "gamma": r"$\gamma$", "alpha": r"$\alpha$", "n": "n", "eplus": r"$e^+$", "eminus": r"$e^-$", "muons": r"$\mu^\pm$"}
    positions = list(range(len(display)))
    width = 0.36
    for offset, model, hatch in ((-width / 2, "A", "//"), (width / 2, "B", "xx")):
        values = []
        for key in display:
            if key == "muons":
                values.append(family[model].get("muplus", 0.0) + family[model].get("muminus", 0.0))
            else:
                values.append(family[model].get(key, 0.0))
        axes[0, 0].bar([x + offset for x in positions], values, width=width, color=COLORS[model], hatch=hatch, edgecolor="white", linewidth=0.45, label=f"Mass model {model}")
    axes[0, 0].set_xticks(positions, [label_map[item] for item in display])
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_ylim(1.0e-7, 5.0e-2)
    axes[0, 0].set(ylabel=r"Final-window rate (s$^{-1}$)", title="Selected rate by incident family")
    axes[0, 0].legend(frameon=False)

    origin_a = rows(ORIGIN_A)
    origin_b = rows(ORIGIN_B)
    materials: dict[str, dict[str, float]] = {"A": defaultdict(float), "B": defaultdict(float)}
    for row in origin_a:
        materials["A"][_material_group(row["source_material"])] += number(row, "day15_noacc_cps")
    for row in origin_b:
        materials["B"][_material_group(row["source_material"])] += number(row, "day15_rate_cps")
    groups = ["Copper", "Aluminium", "W", "Bi/Ta", "Other"]
    group_colors = [COLORS["copper"], COLORS["aluminium"], COLORS["tungsten"], COLORS["bi_ta"], COLORS["other"]]
    group_hatches = ["//", "xx", "..", "\\\\", ""]
    left = [0.0, 0.0]
    totals = [sum(materials[model].values()) for model in ("A", "B")]
    for group, color, hatch in zip(groups, group_colors, group_hatches):
        values = [materials[model].get(group, 0.0) / total for model, total in zip(("A", "B"), totals)]
        axes[0, 1].barh([0, 1], values, left=left, color=color, hatch=hatch, edgecolor="white", linewidth=0.45, label=group)
        left = [a + b for a, b in zip(left, values)]
    copper_share = [materials[model]["Copper"] / total for model, total in zip(("A", "B"), totals)]
    for y, share in enumerate(copper_share):
        axes[0, 1].text(share / 2, y, f"Cu {100*share:.1f}%", ha="center", va="center", fontsize=7.0, fontweight="bold")
    axes[0, 1].set_yticks([0, 1], ["Mass model A", "Mass model B"])
    axes[0, 1].set_xlim(0, 1)
    axes[0, 1].set(xlabel="Fraction of selected delayed rate", title="Delayed source material")
    axes[0, 1].legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.42), fontsize=5.9)

    top = sorted(origin_a, key=lambda row: -number(row, "day15_noacc_cps"))
    kept = top[:6]
    remainder = sum(number(row, "day15_noacc_cps") for row in top[6:])
    labels = [f"{_short_origin(row['source_volume_short'])} · {row['nuclide']}" for row in kept] + ["Other"]
    values = [number(row, "day15_noacc_cps") for row in kept] + [remainder]
    labels.reverse()
    values.reverse()
    axes[1, 0].barh(range(len(values)), values, color=COLORS["A"], hatch="//", edgecolor="white", linewidth=0.45)
    axes[1, 0].set_yticks(range(len(values)), labels)
    axes[1, 0].tick_params(axis="y", labelsize=6.0)
    axes[1, 0].set(xlabel=r"Day-15 delayed rate (s$^{-1}$)", title="Leading mass-model-A origin groups")

    region_rows = rows(REGIONS)
    region_order = ["DR/MXC + staged cold plates", "TES-near structures", "other structures"]
    region_colors = [COLORS["cold"], COLORS["near"], COLORS["other_region"]]
    region_hatches = ["//", "xx", ".."]
    left = [0.0, 0.0]
    for region, color, hatch in zip(region_order, region_colors, region_hatches):
        values = []
        for geometry in ("SG3B", "SH3_OptV3"):
            match = next(row for row in region_rows if row["geometry"] == geometry and row["region"] == region)
            values.append(number(match, "fraction_of_delayed_W2_final"))
        axes[1, 1].barh([0, 1], values, left=left, color=color, hatch=hatch, edgecolor="white", linewidth=0.45, label=region.replace("DR/MXC + ", ""))
        left = [a + b for a, b in zip(left, values)]
    cold = [
        next(number(row, "fraction_of_delayed_W2_final") for row in region_rows if row["geometry"] == geometry and row["region"] == region_order[0])
        for geometry in ("SG3B", "SH3_OptV3")
    ]
    for y, share in enumerate(cold):
        if share > 0.12:
            axes[1, 1].text(share / 2, y, f"cold {100*share:.1f}%", ha="center", va="center", fontsize=6.6, color="white", fontweight="bold")
        else:
            axes[1, 1].text(share + 0.018, y, f"cold {100*share:.1f}%", ha="left", va="center", fontsize=6.6, color=COLORS["ink"], fontweight="bold")
    axes[1, 1].set_yticks([0, 1], ["Mass model A", "Mass model B"])
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set(xlabel="Fraction of selected delayed rate", title="Delayed-origin region")
    axes[1, 1].legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=2, fontsize=5.9)

    for label, ax in zip(("(a)", "(b)", "(c)", "(d)"), axes.flat):
        panel(ax, label)
        tidy(ax)
    save(fig, "fig08_background_origins")

    print(
        "origin shares:",
        f"Cu A={100*copper_share[0]:.3f}%",
        f"Cu B={100*copper_share[1]:.3f}%",
        f"cold A={100*cold[0]:.3f}%",
        f"cold B={100*cold[1]:.3f}%",
    )


def main() -> None:
    configure()
    build_trajectory_validation()
    build_anchor_diagnostic()
    build_veto_spectra()
    build_background_origins()
    for name in (
        "fig04_trajectory_prompt_validation",
        "fig04_common_time_normalization",
        "fig05_broadband_veto_spectra",
        "fig08_background_origins",
    ):
        print(HERE / f"{name}.pdf")


if __name__ == "__main__":
    main()
