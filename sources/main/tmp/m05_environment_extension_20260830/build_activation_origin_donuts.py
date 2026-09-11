#!/usr/bin/env python3
"""Build the model-A delayed-activation origin donuts for Section 4.

The script reads only the compact, selected-event lineage catalogue already
used by the current manuscript figure audit.  It does not open transport
payloads, SIM/NPZ files, or job catalogues, and it starts no simulation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_activation_origin_donuts_mpl")

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "59_sg3b_prompt_activation_coupling_20260818"
    / "outputs/02_coupling_analysis/selected_event_lineage.csv"
)
AUDIT = (
    REPO
    / "core_md/balloon511_ea_latex_drafts/M05NEW"
    / "M05_SECTION4_PUBLICATION_FIGURES_20260829.json"
)
OUTDIR = HERE / "figures" / "section4_current"
OUTSTEM = "fig_activation_origin_donuts_model_a"

EXPECTED_ROWS = 394
EXPECTED_TOTAL = 0.037720860604326306

COMPONENT_ORDER = (
    "mxc_50mk_cu_plate",
    "tes_substrate_cu_panels",
    "al_cryostat_shields",
    "tes_cu_heat_sink",
    "nearfield_bi_liner",
    "other_dr_cold_hardware",
    "w_bottom_plate",
    "bpe_bgo_shielding",
)
COMPONENT_LABELS = (
    "50 mK MXC Cu cold plate",
    "TES substrate-support Cu panels",
    "Al cryostat/shield components",
    "TES-stack Cu heat-sink ring",
    "Near-field Bi liner",
    "Other DR/cold-stage hardware",
    "W detector-bay bottom plate",
    "BPE and residual BGO shielding",
)
COMPONENT_COLORS = (
    "#0072B2",
    "#E69F00",
    "#56B4E9",
    "#D55E00",
    "#CC79A7",
    "#009E73",
    "#8C564B",
    "#7A7A7A",
)

FAMILY_ORDER = ("p", "alpha", "n", "gamma", "electron_positron")
FAMILY_LABELS = (
    "Proton",
    r"$\alpha$ particle",
    "Neutron",
    r"$\gamma$ ray",
    r"$e^{\pm}$",
)
FAMILY_COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#7A7A7A")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_component(volume: str, material: str) -> str:
    if volume == "ColdPlate_MXC_50mK_SD_anchor":
        return "mxc_50mk_cu_plate"
    if volume in {
        "Cu_SubstrateSupport_OpenRing_L2_ZP_panel",
        "Cu_SubstrateSupport_OpenRing_L4_YP_panel",
    }:
        return "tes_substrate_cu_panels"
    if volume == "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm":
        return "tes_cu_heat_sink"
    if volume == "SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm":
        return "nearfield_bi_liner"
    if material == "Aluminium":
        return "al_cryostat_shields"
    if volume == "Passive_W_Bottom_Plate_detector_bay":
        return "w_bottom_plate"
    if material in {"BoratedPolyethylene5wtB", "BGO"}:
        return "bpe_bgo_shielding"
    return "other_dr_cold_hardware"


def load_breakdowns() -> tuple[list[float], list[float]]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    expected_hash = audit["input_sha256"].get(str(SOURCE))
    if expected_hash is None or sha256(SOURCE) != expected_hash:
        raise RuntimeError("selected-event lineage catalogue does not match the audited input")

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["stream"] == "delayed"]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"unexpected selected delayed row count: {len(rows)}")

    by_component: dict[str, float] = defaultdict(float)
    by_family: dict[str, float] = defaultdict(float)
    for row in rows:
        weight = float(row["day15_noacc_cps"])
        by_component[
            classify_component(row["source_volume"], row["source_material"])
        ] += weight
        family = row["family"]
        if family in {"eminus", "eplus"}:
            family = "electron_positron"
        by_family[family] += weight

    component_values = [by_component[key] for key in COMPONENT_ORDER]
    family_values = [by_family[key] for key in FAMILY_ORDER]
    for values, name in ((component_values, "component"), (family_values, "family")):
        if not math.isclose(math.fsum(values), EXPECTED_TOTAL, rel_tol=2.0e-12, abs_tol=1.0e-14):
            raise RuntimeError(f"{name} projection does not close to the final delayed rate")
    return component_values, family_values


def autopct_threshold(pct: float) -> str:
    return f"{pct:.1f}%" if pct >= 3.0 else ""


def draw_donut(
    ax: mpl.axes.Axes,
    values: list[float],
    labels: tuple[str, ...],
    colors: tuple[str, ...],
    title: str,
    *,
    legend_fontsize: float = 8.1,
) -> None:
    total = math.fsum(values)
    wedges, _, autotexts = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        radius=1.0,
        wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 1.4},
        autopct=autopct_threshold,
        pctdistance=0.815,
    )
    for wedge, text in zip(wedges, autotexts, strict=True):
        red, green, blue, _ = wedge.get_facecolor()
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        text.set_color("#161616" if luminance > 0.62 else "white")
        text.set_fontweight("bold")
        text.set_fontsize(8.6)

    ax.text(0.0, 0.14, "Model A", ha="center", va="center", fontsize=9.0, color="#4B5563")
    ax.text(0.0, -0.02, "selected activation", ha="center", va="center", fontsize=8.8, color="#4B5563")
    ax.text(0.0, -0.21, r"$3.77209\times10^{-2}$", ha="center", va="center", fontsize=10.1, fontweight="bold")
    ax.text(0.0, -0.35, r"$\mathrm{s}^{-1}$", ha="center", va="center", fontsize=8.8, color="#4B5563")
    ax.set_title(title, pad=8)
    ax.set_aspect("equal")

    legend_labels = [
        f"{label}  ({100.0 * value / total:.2f}%)"
        for label, value in zip(labels, values, strict=True)
    ]
    ax.legend(
        wedges,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.04),
        frameon=False,
        fontsize=legend_fontsize,
        handlelength=1.1,
        handletextpad=0.45,
        labelspacing=0.42,
    )


def main() -> None:
    component_values, family_values = load_breakdowns()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.8,
            "axes.titlesize": 10.4,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(7.20, 5.35), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.04, h_pad=0.04, wspace=0.10, hspace=0.04)
    draw_donut(
        axes[0],
        component_values,
        COMPONENT_LABELS,
        COMPONENT_COLORS,
        "Parent-nuclide production component",
        legend_fontsize=8.0,
    )
    draw_donut(axes[1], family_values, FAMILY_LABELS, FAMILY_COLORS, "Initiating primary particle")
    for label, ax in zip(("(a)", "(b)"), axes, strict=True):
        ax.text(-0.08, 1.04, label, transform=ax.transAxes, fontsize=10.0, fontweight="bold")

    for suffix in ("pdf", "png"):
        path = OUTDIR / f"{OUTSTEM}.{suffix}"
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.04}
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        print(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
