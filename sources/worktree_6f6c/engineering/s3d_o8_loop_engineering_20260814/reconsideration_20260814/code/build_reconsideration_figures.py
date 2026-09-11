#!/usr/bin/env python3
"""Build compact decision figures for the S3d-O8 scheme reconsideration."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3d_o8_reconsideration_matplotlib")
import matplotlib.pyplot as plt
import numpy as np


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
FIGURES = PACKAGE / "figures"
PROMPT_EVENTS = PACKAGE / (
    "focused_prompt_repeat64/three_cell_event_summary_repeat64.csv"
)
SIGNAL = PACKAGE / "focused_signal/candidate_signal_result.json"

P = 55398.97943402516
C = 59252.57645915347
M = 27605.141950180394
O = 1947.144242542067


def build_frontier() -> list[dict[str, float]]:
    signal = json.loads(SIGNAL.read_text(encoding="utf-8"))
    gate = float(signal["candidate_B20_max_counts"])
    rows: list[dict[str, float]] = []
    for magnetic_suppression in (0.50, 0.75, 0.90):
        for copper_suppression in np.linspace(0.75, 1.0, 101):
            prompt_suppression = 1.0 - (
                gate
                - C * (1.0 - copper_suppression)
                - M * (1.0 - magnetic_suppression)
                - O
            ) / P
            rows.append(
                {
                    "copper_net_suppression": float(copper_suppression),
                    "nbmu_effective_suppression": magnetic_suppression,
                    "minimum_prompt_suppression": prompt_suppression,
                    "candidate_count_gate": gate,
                }
            )
    path = DATA / "candidate_signal_joint_suppression_frontier.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def clean_pair_hosts() -> list[dict[str, object]]:
    counts: Counter[tuple[str, str]] = Counter()
    named = {"Copper", "Aluminium", "StainlessSteel", "W", "Ta"}
    with PROMPT_EVENTS.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["pair_count"]) > 0 and int(row["veto50_pass"]) == 1:
                material = row["first_pair_material"]
                counts[(row["geometry_key"], material if material in named else "Other")] += 1
    materials = sorted({material for _, material in counts})
    rows = [
        {
            "geometry_key": geometry,
            "material": material,
            "active_veto_clean_first_pair_events": counts[(geometry, material)],
        }
        for geometry in ("baseline", "AF1_48")
        for material in materials
    ]
    path = DATA / "p1_active_veto_clean_pair_hosts.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    frontier = build_frontier()
    hosts = clean_pair_hosts()

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
            "figure.dpi": 140,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.05), constrained_layout=False)
    fig.subplots_adjust(top=0.78, bottom=0.13, left=0.075, right=0.985, wspace=0.24)

    ax = axes[0]
    colors = {0.50: "#8c6bb1", 0.75: "#2b8cbe", 0.90: "#2ca25f"}
    for magnetic in (0.50, 0.75, 0.90):
        subset = [row for row in frontier if row["nbmu_effective_suppression"] == magnetic]
        x = [row["copper_net_suppression"] for row in subset]
        y = [row["minimum_prompt_suppression"] for row in subset]
        ax.plot(x, y, lw=2, color=colors[magnetic], label=f"Nb+Mu suppression = {magnetic:.0%}")
    ax.scatter([0.95], [0.80], marker="*", s=145, color="#d7301f", zorder=5, label="pre-registered anchor")
    ax.axvline(0.87487971715, ls="--", lw=1.2, color="#d7301f", alpha=0.75)
    ax.text(0.876, 0.49, "Cu min at anchor\n87.49%", color="#b21f12", va="top")
    ax.set_xlim(0.75, 1.002)
    ax.set_ylim(0.0, 1.02)
    ax.set_xlabel("Net suppression of 48-volume Cu term")
    ax.set_ylabel("Minimum prompt suppression")
    ax.set_title("Candidate-own signal gate: 27,341.9 counts")
    ax.grid(alpha=0.22)
    ax.legend(loc="upper right", frameon=False)

    ax = axes[1]
    material_order = ["Copper", "Aluminium", "StainlessSteel", "W", "Ta", "Other"]
    palette = {
        "Copper": "#b87333",
        "Aluminium": "#9ecae1",
        "StainlessSteel": "#969696",
        "W": "#252525",
        "Ta": "#756bb1",
        "Other": "#d9d9d9",
    }
    by = {(str(row["geometry_key"]), str(row["material"])): int(row["active_veto_clean_first_pair_events"]) for row in hosts}
    bottoms = np.zeros(2)
    for material in material_order:
        values = np.array([by.get(("baseline", material), 0), by.get(("AF1_48", material), 0)])
        ax.bar([0, 1], values, bottom=bottoms, width=0.58, color=palette[material], label=material)
        bottoms += values
    ax.set_xticks([0, 1], ["Baseline", "AF1-48"])
    ax.set_ylabel("First-pair events with active veto < 50 keV")
    ax.set_title(
        "P1: 257 states x 64 repeats per geometry\n"
        "clean-pair ratio 0.65; one-sided 95% upper 0.805"
    )
    ax.set_ylim(0, max(bottoms) * 1.16)
    for index, total in enumerate(bottoms):
        ax.text(index, total + 0.55, f"n={int(total)}", ha="center", fontweight="bold")
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper right", frameon=False, ncol=2)

    fig.suptitle(
        "S3d-O8 AF1-48: arithmetic feasibility vs measured prompt mechanism",
        fontsize=13,
        fontweight="bold",
        y=0.96,
    )
    output = FIGURES / "af1_48_decision_evidence.png"
    fig.savefig(output)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
