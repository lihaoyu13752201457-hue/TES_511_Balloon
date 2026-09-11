#!/usr/bin/env python3
"""Build strict optimistic central-rate ceilings for simple S3d-O8 candidates.

This is a gate, not a performance prediction.  Every removal listed below is
deliberately more favorable than the corresponding physical geometry could be:
the named observed contribution is set to zero with no host migration and no
signal loss.  A case that still misses the unchanged-signal budget is therefore
killed before transport.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3d_o8_loop_mpl")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", type=Path, required=True)
    parser.add_argument("--prompt-meta", type=Path, required=True)
    parser.add_argument("--delayed-audit", type=Path, required=True)
    parser.add_argument("--delayed-key-flow", type=Path, required=True)
    parser.add_argument("--delayed-components", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-figure", type=Path, required=True)
    args = parser.parse_args()

    mission = load_json(args.mission)["geometries"]["S3d_O8"]
    prompt_meta = load_json(args.prompt_meta)
    delayed_audit = load_json(args.delayed_audit)

    prompt = float(prompt_meta["step05_prompt_w2_cps"])
    delayed = float(delayed_audit["selected_rate_cps"])
    baseline = prompt + delayed
    f3 = float(mission["flux_3sigma_20d_ph_cm2_s"])
    target_f3 = 3.0e-5
    unchanged_signal_budget = baseline * (target_f3 / f3) ** 2

    material_rate: dict[str, float] = {}
    with args.delayed_key_flow.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            material = row["material"]
            material_rate[material] = material_rate.get(material, 0.0) + float(
                row["selected_rate_cps_observed_mix"]
            )

    component_rate: dict[str, float] = {}
    with args.delayed_components.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            component_rate[row["component_group"]] = float(
                row["selected_rate_cps_observed_mix"]
            )

    # To make every impossibility test maximally favorable, all prompt is set
    # to zero for each component/material candidate.  The result is therefore
    # independent of trying to infer an all-sky prompt host fraction from two
    # Step05 events.
    cases = [
        {
            "case": "S3d-O8 baseline",
            "prompt_removed_cps": 0.0,
            "delayed_removed_cps": 0.0,
            "scope": "reference",
        },
        {
            "case": "G-Nb-S1: magical 100% removal of observed inner-Nb topology",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": component_rate["Nb_inner_cylinder"],
            "scope": "strict optimistic ceiling: all prompt also set to zero; physical 2->1 mm wall can only do less",
        },
        {
            "case": "MXC-only: magical 100% removal",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": component_rate["MXC_50mK_plate"],
            "scope": "strict optimistic ceiling: all prompt also set to zero",
        },
        {
            "case": "all observed Copper class: magical 100% removal",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": material_rate["Copper"],
            "scope": "unphysical class ceiling: all prompt also set to zero",
        },
        {
            "case": "all observed Nb+Mu classes: magical 100% removal",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": material_rate["Nb"] + material_rate["Mu-metal"],
            "scope": "unphysical class ceiling: all prompt also set to zero",
        },
        {
            "case": "MXC+Nb inner+Mu outer+L0: magical 100% removal",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": (
                component_rate["MXC_50mK_plate"]
                + component_rate["Nb_inner_cylinder"]
                + component_rate["MuMetal_outer_cylinder"]
                + component_rate["L0_Cu_disk"]
            ),
            "scope": "minimum named four-component central crossing; all prompt also set to zero; non-admissible",
        },
        {
            "case": "all observed Cu+Nb+Mu classes: magical 100% removal",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": (
                material_rate["Copper"]
                + material_rate["Nb"]
                + material_rate["Mu-metal"]
            ),
            "scope": "capability bound only; removes thermal and magnetic functional classes",
        },
        {
            "case": "all prompt magically removed",
            "prompt_removed_cps": prompt,
            "delayed_removed_cps": 0.0,
            "scope": "mechanism-necessity bound",
        },
        {
            "case": "all delayed magically removed",
            "prompt_removed_cps": 0.0,
            "delayed_removed_cps": delayed,
            "scope": "mechanism-necessity bound",
        },
    ]

    for row in cases:
        residual_prompt = prompt - row["prompt_removed_cps"]
        residual_delayed = delayed - row["delayed_removed_cps"]
        residual = residual_prompt + residual_delayed
        verdict = (
            "REFERENCE__MISSES_TARGET"
            if row["case"] == "S3d-O8 baseline"
            else (
                "CAPABLE_ONLY_IF_ENGINEERING_ADMISSIBLE"
                if residual <= unchanged_signal_budget
                else "KILL__MISSES_STRICT_OPTIMISTIC_CEILING"
            )
        )
        row.update(
            {
                "baseline_prompt_cps": prompt,
                "baseline_delayed_cps": delayed,
                "residual_prompt_cps": residual_prompt,
                "residual_delayed_cps": residual_delayed,
                "residual_total_cps": residual,
                "unchanged_signal_Bmax_cps": unchanged_signal_budget,
                "residual_over_budget": residual / unchanged_signal_budget,
                "unchanged_signal_F3_ph_cm2_s": f3 * math.sqrt(residual / baseline),
                "target_F3_ph_cm2_s": target_f3,
                "budget_verdict": verdict,
            }
        )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(cases[0])
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cases)

    # Plot the residual prompt and delayed central rates.  The target is only
    # valid for unchanged candidate signal and is labeled accordingly.
    labels = [
        "baseline",
        "Nb 100%\n(optimistic)",
        "MXC 100%\n(optimistic)",
        "all Cu 100%\n(unphysical)",
        "Nb+Mu 100%\n(unphysical)",
        "MXC+Nb+Mu+L0\n(non-admissible)",
        "Cu+Nb+Mu 100%\n(non-admissible)",
        "prompt=0",
        "delayed=0",
    ]
    residual_prompt = [float(row["residual_prompt_cps"]) for row in cases]
    residual_delayed = [float(row["residual_delayed_cps"]) for row in cases]
    x = list(range(len(cases)))
    fig, ax = plt.subplots(figsize=(12.5, 6.7), constrained_layout=True)
    ax.bar(x, residual_prompt, color="#D55E00", label="residual prompt")
    ax.bar(
        x,
        residual_delayed,
        bottom=residual_prompt,
        color="#0072B2",
        label="residual delayed",
    )
    ax.axhline(
        unchanged_signal_budget,
        color="#009E73",
        lw=2.2,
        ls="--",
        label=f"F3=3e-5 budget if S20 unchanged: {unchanged_signal_budget:.5f} cps",
    )
    for i, row in enumerate(cases):
        residual = float(row["residual_total_cps"])
        ax.text(
            i,
            residual + 0.0013,
            f"{residual:.5f}\nF3={float(row['unchanged_signal_F3_ph_cm2_s']):.2e}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_ylabel("Central constant-environment day-15 W2 rate (cps)")
    ax.set_ylim(0, max(float(row["residual_total_cps"]) for row in cases) * 1.18)
    ax.grid(axis="y", color="#AAAAAA", lw=0.45, alpha=0.35)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(
        "Simple-topology falsification by deliberately impossible 100% removals\n"
        "A case above the green line cannot meet F3 even before host migration, signal loss, or uncertainty"
    )
    args.output_figure.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_figure, dpi=220, bbox_inches="tight")
    fig.savefig(args.output_figure.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
