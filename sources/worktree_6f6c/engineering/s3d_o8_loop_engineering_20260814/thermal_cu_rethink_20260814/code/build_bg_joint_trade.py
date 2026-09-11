#!/usr/bin/env python3
"""Build the denominator-explicit BG-J thickness/mass planning screen.

This is deliberately a *scale model*, not transport.  It applies an added
uncollided BGO factor to the already-selected baseline prompt and delayed
mission counts.  The delayed factor is conditional on the selected event's
anti-TES 511-keV sibling reaching the added BGO.  Real relief coverage,
threshold response, secondaries, activation and signal changes remain zero-
credit terms until candidate-own runs exist.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"

PROMPT_COUNTS = 55398.97943402516
DELAYED_COUNTS = 88804.86265187593
SIGNAL_COUNTS_AT_3E5 = 1645.387753066
COUNT_GATE = (SIGNAL_COUNTS_AT_3E5 / 10.0) ** 2
DELAYED_ACTUAL_OUTER_REACH_COUNTS = 9406.613
DELAYED_ACTUAL_OUTER_REACH_FRACTION = DELAYED_ACTUAL_OUTER_REACH_COUNTS / DELAYED_COUNTS

# Scale values already used in the independent prompt review.
MU_BGO_5P77_MEV_PER_CM = 0.276
MU_BGO_511_KEV_PER_CM = 0.986

# Analytic pre-relief S3d-O8 primitives, used only for mass scale.
BGO_DENSITY_G_CM3 = 7.1
SIDE_R0_CM = 25.2
SIDE_LENGTH_CM = 60.3
TOP_BASE_RIN_CM = 20.9
TOP_CLOSED_RIN_CM = 4.0


def added_bgo_mass_kg(thickness_cm: float) -> tuple[float, float, float, float]:
    side = (
        math.pi
        * ((SIDE_R0_CM + thickness_cm) ** 2 - SIDE_R0_CM**2)
        * SIDE_LENGTH_CM
        * BGO_DENSITY_G_CM3
        / 1000.0
    )
    bottom = (
        math.pi
        * SIDE_R0_CM**2
        * thickness_cm
        * BGO_DENSITY_G_CM3
        / 1000.0
    )
    top_closure = (
        math.pi
        * (TOP_BASE_RIN_CM**2 - TOP_CLOSED_RIN_CM**2)
        * 1.0
        * BGO_DENSITY_G_CM3
        / 1000.0
    )
    top_extra = (
        math.pi
        * (SIDE_R0_CM**2 - TOP_CLOSED_RIN_CM**2)
        * thickness_cm
        * BGO_DENSITY_G_CM3
        / 1000.0
    )
    top = top_closure + top_extra
    return side, bottom, top, side + bottom + top


def row(thickness_cm: float) -> dict[str, float | str]:
    prompt_survival = math.exp(-MU_BGO_5P77_MEV_PER_CM * thickness_cm)
    delayed_survival = math.exp(-MU_BGO_511_KEV_PER_CM * thickness_cm)
    prompt = PROMPT_COUNTS * prompt_survival
    delayed = DELAYED_COUNTS * delayed_survival
    total = prompt + delayed
    delayed_actual_reach_proxy = DELAYED_COUNTS * (
        1.0
        - DELAYED_ACTUAL_OUTER_REACH_FRACTION
        + DELAYED_ACTUAL_OUTER_REACH_FRACTION * delayed_survival
    )
    total_actual_reach_proxy = prompt + delayed_actual_reach_proxy
    side, bottom, top, mass = added_bgo_mass_kg(thickness_cm)
    relief_headroom = COUNT_GATE - total
    all_count_bypass = (
        relief_headroom / (PROMPT_COUNTS + DELAYED_COUNTS - total)
        if relief_headroom > 0
        else 0.0
    )
    prompt_only_bypass = (
        relief_headroom / (PROMPT_COUNTS - prompt)
        if relief_headroom > 0 and prompt < PROMPT_COUNTS
        else 0.0
    )
    delayed_only_bypass = (
        relief_headroom / (DELAYED_COUNTS - delayed)
        if relief_headroom > 0 and delayed < DELAYED_COUNTS
        else 0.0
    )
    sensitivity = (
        3.0e-5 * 10.0 * math.sqrt(total) / SIGNAL_COUNTS_AT_3E5
        if total > 0
        else 0.0
    )
    return {
        "added_bgo_cm": thickness_cm,
        "prompt_survival_scale": prompt_survival,
        "delayed_sibling_survival_scale": delayed_survival,
        "prompt_mission_counts_proxy": prompt,
        "delayed_mission_counts_proxy": delayed,
        "total_mission_counts_proxy": total,
        "delayed_actual_outer_reach_fraction": DELAYED_ACTUAL_OUTER_REACH_FRACTION,
        "delayed_counts_with_actual_outer_reach_proxy": delayed_actual_reach_proxy,
        "total_counts_with_actual_outer_reach_proxy": total_actual_reach_proxy,
        "count_gate": COUNT_GATE,
        "margin_to_gate_counts": COUNT_GATE - total,
        "max_common_uncovered_fraction_at_gate": all_count_bypass,
        "max_prompt_only_uncovered_fraction_at_gate": prompt_only_bypass,
        "max_delayed_only_uncovered_fraction_at_gate": delayed_only_bypass,
        "central_f3_proxy_photon_cm-2_s-1": sensitivity,
        "added_side_bgo_kg_pre_relief": side,
        "added_bottom_bgo_kg_pre_relief": bottom,
        "added_top_bgo_kg_pre_relief": top,
        "added_total_bgo_kg_pre_relief": mass,
        "status": "SCALE_ONLY__NOT_TRANSPORT",
    }


def solve_minimum_thickness() -> float:
    lo, hi = 0.0, 10.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if row(mid)["total_mission_counts_proxy"] <= COUNT_GATE:
            hi = mid
        else:
            lo = mid
    return hi


def write_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    minimum = solve_minimum_thickness()
    grid = [row(float(x)) for x in np.arange(0.0, 6.001, 0.05)]
    write_csv(DATA / "bg_joint_optical_depth_trade.csv", grid)

    selected = [0.0, 1.0, 2.0, 3.0, minimum, 3.5, 4.0, 5.0, 5.831]
    summary = [row(x) for x in selected]
    for item in summary:
        item["candidate_label"] = (
            "BG-J4_KILLED_BY_ACTUAL_BRANCH_REACH" if abs(float(item["added_bgo_cm"]) - 4.0) < 1e-9
            else "MATHEMATICAL_ZERO_MARGIN" if abs(float(item["added_bgo_cm"]) - minimum) < 1e-6
            else "TRADE_POINT"
        )
    write_csv(DATA / "bg_j4_budget_screen.csv", summary)

    x = np.array([float(item["added_bgo_cm"]) for item in grid])
    p = np.array([float(item["prompt_mission_counts_proxy"]) for item in grid])
    d = np.array([float(item["delayed_mission_counts_proxy"]) for item in grid])
    actual = np.array([float(item["total_counts_with_actual_outer_reach_proxy"]) for item in grid])
    m = np.array([float(item["added_total_bgo_kg_pre_relief"]) for item in grid])

    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)

    ax = axes[0]
    ax.stackplot(x, d, p, labels=["delayed 511 sibling proxy", "prompt primary proxy"],
                 colors=["#4C78A8", "#F58518"], alpha=0.9)
    ax.plot(x, actual, color="#222222", linewidth=2.4,
            label="actual outer-reach ceiling (q=10.59%)")
    ax.axhline(COUNT_GATE, color="#B22222", linewidth=2, label="candidate count gate")
    ax.axvline(minimum, color="#666666", linestyle="--", linewidth=1.5)
    ax.axvline(4.0, color="#2E8B57", linestyle="-.", linewidth=1.8)
    ax.annotate(f"zero-margin scale\n{minimum:.2f} cm", (minimum, COUNT_GATE),
                xytext=(2.05, 45500),
                arrowprops={"arrowstyle": "->", "color": "#666666"})
    j4 = row(4.0)
    ax.annotate(f"BG-J4 killed\nactual-reach proxy {j4['total_counts_with_actual_outer_reach_proxy']:.0f}",
                (4.0, float(j4["total_counts_with_actual_outer_reach_proxy"])),
                xytext=(4.25, 127000),
                arrowprops={"arrowstyle": "->", "color": "#2E8B57"})
    ax.set(xlabel="additional BGO path (cm)", ylabel="20-day mission counts (scale only)",
           xlim=(0, 6), ylim=(0, 155000))
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.2)

    ax2 = axes[1]
    ax2.plot(x, m, color="#7A5195", linewidth=2.4, label="added BGO mass")
    ax2.scatter([4.0], [float(j4["added_total_bgo_kg_pre_relief"])],
                color="#2E8B57", zorder=3)
    ax2.annotate(f"analytic ~{j4['added_total_bgo_kg_pre_relief']:.0f} kg\nCSG proxy +470 kg BGO",
                 (4.0, float(j4["added_total_bgo_kg_pre_relief"])),
                 xytext=(2.5, 535), arrowprops={"arrowstyle": "->", "color": "#2E8B57"})
    ax2.set(xlabel="additional BGO path (cm)", ylabel="analytic added BGO mass (kg, pre-relief)",
            xlim=(0, 6), ylim=(0, 660))
    ax2.grid(alpha=0.2)
    ax2.legend(frameon=False, loc="upper left")

    fig.suptitle("S3d-O8 Cu-preserving joint BGO falsification screen")
    fig.text(0.5, -0.015,
             "Exponential uncollided scale only; assumes complete added-channel coverage, unchanged signal, and zero new activation.",
             ha="center", color="#555555")
    fig.savefig(FIGURES / "bg_j4_joint_budget_mass_trade.png", dpi=220, bbox_inches="tight")
    fig.savefig(FIGURES / "bg_j4_joint_budget_mass_trade.svg", bbox_inches="tight")


if __name__ == "__main__":
    main()
