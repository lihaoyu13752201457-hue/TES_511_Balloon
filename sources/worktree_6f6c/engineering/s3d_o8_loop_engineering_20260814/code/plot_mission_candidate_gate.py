#!/usr/bin/env python3
"""Plot the exact 81-node 20-day necessity gate for selected candidate scopes."""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3d_o8_loop_mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = {row["scope"]: row for row in csv.DictReader(handle)}

    baseline = rows["baseline_delayed"]
    signal = float(baseline["mission_source_counts_20d"])
    prompt = float(baseline["baseline_prompt_counts_20d"])
    delayed = float(baseline["baseline_delayed_counts_20d"])
    bmax = float(baseline["mission_background_count_ceiling_for_Z10"])

    cases = [
        ("baseline", prompt, delayed, "reference"),
        (
            "Nb inner 100%\n+ prompt=0",
            0.0,
            float(rows["Nb_inner"]["residual_mission_counts_20d_baseline_live"]),
            "KILL",
        ),
        (
            "MXC 100%\n+ prompt=0",
            0.0,
            float(rows["MXC"]["residual_mission_counts_20d_baseline_live"]),
            "KILL",
        ),
        (
            "all Cu 100%\n+ prompt=0",
            0.0,
            float(rows["all_Copper"]["residual_mission_counts_20d_baseline_live"]),
            "FAIL 9.07%",
        ),
        (
            "MXC+Nb+Mu+L0 100%\n+ prompt=0",
            0.0,
            float(
                rows["MXC_plus_Nb_plus_Mu_plus_L0"][
                    "residual_mission_counts_20d_baseline_live"
                ]
            ),
            "NON-ADMISSIBLE",
        ),
        ("prompt=0", 0.0, delayed, "mechanism bound"),
        ("delayed=0", prompt, 0.0, "mechanism bound"),
    ]

    x = list(range(len(cases)))
    p = [case[1] for case in cases]
    d = [case[2] for case in cases]
    totals = [a + b for a, b in zip(p, d)]

    fig, ax = plt.subplots(figsize=(12.8, 7.0), constrained_layout=True)
    ax.bar(x, p, color="#D55E00", label="20-day prompt counts")
    ax.bar(x, d, bottom=p, color="#0072B2", label="20-day delayed counts")
    ax.axhline(
        bmax,
        color="#009E73",
        lw=2.4,
        ls="--",
        label=f"exact mission gate B20,max=(S20/10)^2={bmax:,.1f}",
    )
    for i, (total, case) in enumerate(zip(totals, cases)):
        f3 = 3.0e-4 * math.sqrt(total) / signal
        ax.text(
            i,
            total + 3300,
            f"{total:,.0f}\nF3={f3:.2e}\n{case[3]}",
            ha="center",
            va="bottom",
            fontsize=8.4,
        )
    ax.set_xticks(x, [case[0] for case in cases], fontsize=8.5)
    ax.set_ylabel("Exact 81-node mission background counts in 20 days")
    ax.set_ylim(0, max(totals) * 1.22)
    ax.grid(axis="y", color="#AAAAAA", lw=0.45, alpha=0.35)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(
        "S3d-O8 mission gate: perfect-removal ceilings with exact parent half-life integration\n"
        "Every candidate scope also receives the impossible benefit prompt=0; baseline S20=1645.388"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=220, bbox_inches="tight")
    fig.savefig(args.output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
