#!/usr/bin/env python3
"""Build the manuscript Figure 9 background-composition donuts.

Only the compact, formal Section-4 JSON product is read.  No transport output,
SIM/NPZ payload, or job catalogue is opened.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_fig09_composition_mpl")

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "M05_SECTION4_REFERENCE_FLUX_20260830.json"
OUTDIR = HERE / "figures" / "section4_current"
STEMS = ("prompt_seven", "gamma_continuum", "delayed")
LABELS = (
    r"Seven non-$\gamma$ prompt families",
    r"Broadband atmospheric $\gamma$",
    "Delayed activation",
)
COLORS = ("#0072B2", "#009E73", "#CC79A7")


def load_rates() -> dict[str, list[float]]:
    with SOURCE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("status") != "PASS__M05_SECTION4_V2_FORMAL_RESULTS":
        raise RuntimeError("unexpected Section-4 result status")

    rates: dict[str, list[float]] = {}
    for model in ("A", "B"):
        streams = payload["models"][model]["day15_final_physical_streams"]
        rates[model] = [float(streams[key]["rate_cps"]) for key in STEMS]
        total = sum(rates[model])
        expected = float(
            payload["models"][model]["day15_cutflow"]["compton_trajectory_veto"][
                "rate_cps"
            ]
        )
        if abs(total - expected) > 1.0e-12:
            raise RuntimeError(f"model {model} component sum does not close")
    return rates


def percent_label(pct: float) -> str:
    return f"{pct:.1f}%" if pct >= 0.05 else ""


def main() -> None:
    rates = load_rates()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.0,
            "axes.titlesize": 11.0,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(7.20, 3.25), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.04, h_pad=0.04, wspace=0.08, hspace=0.04)

    for ax, model in zip(axes, ("A", "B"), strict=True):
        values = rates[model]
        total = sum(values)
        exponent = math.floor(math.log10(total))
        mantissa = total / (10.0**exponent)
        wedges, _, autotexts = ax.pie(
            values,
            colors=COLORS,
            startangle=90,
            counterclock=False,
            radius=1.0,
            wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 1.5},
            autopct=percent_label,
            pctdistance=0.81,
        )
        for text in autotexts:
            text.set_color("white")
            text.set_fontweight("bold")
            text.set_fontsize(9.2)
        ax.text(
            0,
            0.06,
            "Total",
            ha="center",
            va="center",
            color="#4B5563",
            fontsize=8.5,
        )
        ax.text(
            0,
            -0.11,
            rf"${mantissa:.2f}\times10^{{{exponent}}}\ \mathrm{{s}}^{{-1}}$",
            ha="center",
            va="center",
            color="#202124",
            fontsize=10.0,
            fontweight="bold",
        )
        ax.set_title(f"Mass model {model}", pad=7)
        ax.set_aspect("equal")

    legend_handles = [axes[1].patches[index] for index in range(3)]
    fig.legend(
        legend_handles,
        LABELS,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.015),
        ncol=3,
        frameon=False,
        handlelength=1.2,
        handletextpad=0.45,
        columnspacing=1.35,
    )

    pdf = OUTDIR / "fig09_background_composition.pdf"
    png = OUTDIR / "fig09_background_composition.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(pdf)
    print(png)


if __name__ == "__main__":
    main()
