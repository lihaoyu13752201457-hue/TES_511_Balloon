#!/usr/bin/env python3
"""Build the manuscript validation plot for the mission-time background fold.

Only compact, retained CSV products are read.  The curves are the 81-node
analytic direct rates; the symbols are the five independent common-time
Poisson replays.  This script does not open event catalogues or start transport.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


REPO = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "70_m05_sg3_sh3_prompt_statistics_integration_20260828"
)
OUT = (
    REPO
    / "tmp/m05_environment_extension_20260830"
    / "figures/section4_current"
)
TIMELINES = {
    "A": PACKAGE / "outputs/03_section4_timeline_a_authority_v2",
    "B": PACKAGE / "outputs/03_section4_timeline_b_authority_v2",
}
UNCERTAINTIES = {
    "A": PACKAGE / "outputs/04_uncertainty_products_a_formal_v2p1_20260829",
    "B": PACKAGE / "outputs/04_uncertainty_products_b_formal_v2p1_20260829",
}

WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
ANCHOR_DAYS = [0.0, 5.0, 10.0, 15.0, 20.0]
COLORS = {"A": "#0072B2", "B": "#D55E00", "grid": "#D8DEE8"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def load_model(model: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    mission = read_csv(TIMELINES[model] / "mission_timeline_81nodes.csv")
    replay = [
        row
        for row in read_csv(UNCERTAINTIES[model] / "five_anchor_replay_mc.csv")
        if row["window_id"] == WINDOW and row["stage"] == FINAL_STAGE
    ]
    replay.sort(key=lambda row: f(row, "day_mid"))

    days = [f(row, "day_mid") for row in mission]
    replay_days = [f(row, "day_mid") for row in replay]
    if days != [0.25 * index for index in range(81)]:
        raise RuntimeError(f"Model {model}: unexpected 81-node time grid")
    if replay_days != ANCHOR_DAYS:
        raise RuntimeError(f"Model {model}: unexpected replay anchors {replay_days}")
    return mission, replay


def style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.1,
            "axes.labelsize": 8.4,
            "axes.titlesize": 9.0,
            "legend.fontsize": 7.4,
            "xtick.labelsize": 7.7,
            "ytick.labelsize": 7.7,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def main() -> None:
    style()
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.15, 3.05),
        gridspec_kw={"width_ratios": [1.48, 1.0]},
        constrained_layout=True,
    )

    closures: dict[str, float] = {}
    for model, linestyle, marker in (("A", "-", "o"), ("B", "--", "s")):
        mission, replay = load_model(model)
        days = [f(row, "day_mid") for row in mission]
        analytic = [f(row, "direct_W2_final_no_coincidence_cps") for row in mission]
        transport_sigma = [f(row, "direct_transport_sigma_cps") for row in mission]
        lower = [max(0.0, rate - sigma) for rate, sigma in zip(analytic, transport_sigma)]
        upper = [rate + sigma for rate, sigma in zip(analytic, transport_sigma)]

        color = COLORS[model]
        axes[0].fill_between(days, lower, upper, color=color, alpha=0.12, linewidth=0)
        axes[0].plot(
            days,
            analytic,
            color=color,
            linestyle=linestyle,
            linewidth=1.55,
            label=f"Model {model}",
        )

        anchor_days = [f(row, "day_mid") for row in replay]
        replay_rates = [f(row, "timeline_rate_cps") for row in replay]
        replay_errors = [f(row, "replay_MC_standard_error_cps") for row in replay]
        direct_anchor = [f(row, "direct_no_coincidence_rate_cps") for row in replay]
        ratios = [rate / direct for rate, direct in zip(replay_rates, direct_anchor)]
        ratio_errors = [error / direct for error, direct in zip(replay_errors, direct_anchor)]
        pulls = [
            abs(rate - direct) / error
            for rate, direct, error in zip(replay_rates, direct_anchor, replay_errors)
        ]
        closures[model] = max(pulls)

        axes[0].errorbar(
            anchor_days,
            replay_rates,
            yerr=replay_errors,
            fmt=marker,
            ms=4.3,
            mew=1.0,
            color=color,
            markerfacecolor="white",
            capsize=2.4,
            elinewidth=0.9,
            zorder=5,
        )
        axes[1].errorbar(
            anchor_days,
            ratios,
            yerr=ratio_errors,
            fmt=marker,
            ms=4.3,
            mew=1.0,
            color=color,
            markerfacecolor="white",
            capsize=2.4,
            elinewidth=0.9,
            label=f"Model {model}",
        )

    axes[0].set(
        ylabel=r"Final science-window background rate (s$^{-1}$)",
        title="Analytic time fold and event-level replay",
        xlim=(-0.5, 20.5),
        ylim=(0.0, 0.070),
    )
    axes[0].set_xticks(ANCHOR_DAYS)
    axes[0].legend(frameon=False, loc="upper right", ncol=1)

    axes[1].axhline(1.0, color="#4B5563", linestyle=(0, (3, 2)), linewidth=0.9)
    axes[1].set(
        ylabel="Replay / analytic rate",
        title="Five-anchor closure",
        xlim=(-0.5, 20.5),
        ylim=(0.865, 1.07),
    )
    axes[1].set_xticks(ANCHOR_DAYS)
    axes[1].legend(frameon=False, loc="lower right")
    axes[1].text(
        0.04,
        0.07,
        rf"max $|\Delta|/\sigma_{{\rm replay}}$: "
        rf"A {closures['A']:.2f}, B {closures['B']:.2f}",
        transform=axes[1].transAxes,
        fontsize=7.2,
        color="#374151",
    )

    for label, ax in zip(("(a)", "(b)"), axes):
        ax.text(
            -0.13,
            1.04,
            label,
            transform=ax.transAxes,
            fontweight="bold",
            fontsize=9.3,
            va="bottom",
        )
        ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(direction="out", length=3.0, width=0.7)

    fig.supxlabel("Mission day", fontsize=8.4)

    stem = OUT / "fig04_time_fold_validation"
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=320, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {stem.with_suffix('.pdf')}")
    print(f"max replay-only pull: A={closures['A']:.6f}, B={closures['B']:.6f}")


if __name__ == "__main__":
    main()
