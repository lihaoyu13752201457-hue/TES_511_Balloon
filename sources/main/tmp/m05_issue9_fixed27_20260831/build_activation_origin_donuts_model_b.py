#!/usr/bin/env python3
"""Build the model-B delayed-activation origin donuts for Section 4.

Only the compact selected-event origin catalogue and its audited, current
family-wise reweighting record are read.  No SIM/NPZ payload or job catalogue
is opened, and no transport or detector simulation is started.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_activation_origin_donuts_b_mpl")

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = Path("/home/ubuntu/TES_511_Balloon")
SOURCE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820"
    / "outputs/05_optv3_delayed_origins/optv3_delayed_selected_events.csv"
)
AUDIT = (
    REPO
    / "core_md/balloon511_ea_latex_drafts/M05NEW"
    / "M05_SECTION4_PUBLICATION_FIGURES_20260829.json"
)
OUTDIR = HERE / "paper_new" / "figures" / "section4_current"
OUTSTEM = "fig_activation_origin_donuts_model_b"

EXPECTED_ROWS = 111
EXPECTED_TOTAL = 0.003580537811785916

COMPONENT_ORDER = (
    "tes_substrate_cu_panels",
    "tes_cu_heat_sink",
    "al_chimney_cryostat",
    "w_focal_plane_frame",
    "tes_bottom_cold_spokes",
    "mxc_50mk_cu_plate",
    "cold_link_hardware",
    "tes_pixel_ta",
    "bgo_side_shield",
)
COMPONENT_LABELS = (
    "TES substrate-support Cu panels",
    "TES-stack Cu heat-sink ring",
    "Al chimney shells, lid, and annuli",
    "W focal-plane frame",
    "TES bottom Cu cold-plate spoke",
    "50 mK MXC Cu cold plate",
    "Cold-link hardware (Cu finger + SS rod)",
    "TES-pixel Ta volumes",
    "Residual BGO side shield",
)
COMPONENT_COLORS = (
    "#E69F00",
    "#D55E00",
    "#56B4E9",
    "#8C564B",
    "#009E73",
    "#0072B2",
    "#CC79A7",
    "#7A7A7A",
    "#F0E442",
)

FAMILY_ORDER = ("p", "alpha", "n", "gamma", "leptons")
FAMILY_LABELS = (
    "Proton",
    r"$\alpha$ particle",
    "Neutron",
    r"$\gamma$ ray",
    r"Leptons ($e^{\pm},\mu^{-}$)",
)
FAMILY_COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#7A7A7A")

TES_PANEL_VOLUMES = {
    "Cu_SubstrateSupport_OpenRing_L5_YP_panel",
    "Cu_SubstrateSupport_OpenRing_L4_YP_panel",
    "Cu_SubstrateSupport_OpenRing_L2_YM_panel",
    "Cu_SubstrateSupport_OpenRing_L5_ZP_panel",
}
AL_VOLUMES = {
    "SH3_Layer02_SideShell",
    "SH3_Layer04_SideShell",
    "SH3_Layer05_RearColdPortAnnulus",
    "Plate_300K_Top_Service_Lid",
    "SH3_Layer03_SideShell",
    "SH3_Layer02_RearColdPortAnnulus",
    "SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm",
    "SH3_Layer05_SideShell",
}
W_FRAME_VOLUMES = {
    "SH3_OptV2_W_Frame_Top",
    "SH3_OptV2_W_Frame_NegY",
    "SH3_OptV2_W_Frame_Bottom",
}
COLD_LINK_VOLUMES = {
    "XS400_Group1_SupportRod_Still_to_4K_single_edge_04",
    "SH3_OptV2_Cu_ColdFinger_PortRun",
}
TES_PIXEL_TA_VOLUMES = {
    "TES_Pixel_L1",
    "TES_Pixel_L4",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_component(volume: str) -> str:
    if volume in TES_PANEL_VOLUMES:
        return "tes_substrate_cu_panels"
    if volume == "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm":
        return "tes_cu_heat_sink"
    if volume in AL_VOLUMES:
        return "al_chimney_cryostat"
    if volume in W_FRAME_VOLUMES:
        return "w_focal_plane_frame"
    if volume == "SH3_TES_BottomColdPlate_Spoke_YM":
        return "tes_bottom_cold_spokes"
    if volume == "ColdPlate_MXC_50mK_SD_anchor":
        return "mxc_50mk_cu_plate"
    if volume in COLD_LINK_VOLUMES:
        return "cold_link_hardware"
    if volume in TES_PIXEL_TA_VOLUMES:
        return "tes_pixel_ta"
    if volume == "SH3_BGO40_SideShield":
        return "bgo_side_shield"
    raise RuntimeError(f"unclassified model-B source volume: {volume}")


def load_breakdowns() -> tuple[list[float], list[float]]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    expected_hash = audit["input_sha256"].get(str(SOURCE))
    if expected_hash is None or sha256(SOURCE) != expected_hash:
        raise RuntimeError("model-B origin catalogue does not match the audited input")
    scales = audit["geometry_response"]["model_B_family_reweight"]

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"unexpected model-B delayed row count: {len(rows)}")

    by_component: dict[str, float] = defaultdict(float)
    by_family: dict[str, float] = defaultdict(float)
    formal_check: dict[str, float] = defaultdict(float)
    for row in rows:
        family = row["family"]
        if family not in scales:
            raise RuntimeError(f"missing current family reweight for {family}")
        weight = float(row["day15_event_weight_cps"]) * float(
            scales[family]["rate_scale"]
        )
        by_component[classify_component(row["source_volume"])] += weight
        formal_check[family] += weight
        plotted_family = "leptons" if family in {"eminus", "eplus", "muminus"} else family
        by_family[plotted_family] += weight

    for family, rate in formal_check.items():
        expected = float(scales[family]["formal_rate"])
        if not math.isclose(rate, expected, rel_tol=2.0e-12, abs_tol=1.0e-14):
            raise RuntimeError(f"model-B {family} family reweight does not close")

    component_values = [by_component[key] for key in COMPONENT_ORDER]
    family_values = [by_family[key] for key in FAMILY_ORDER]
    for values, name in ((component_values, "component"), (family_values, "family")):
        if not math.isclose(math.fsum(values), EXPECTED_TOTAL, rel_tol=2.0e-12, abs_tol=1.0e-14):
            raise RuntimeError(f"model-B {name} projection does not close")
    return component_values, family_values


def autopct_threshold(pct: float) -> str:
    return f"{pct:.1f}%" if pct >= 3.0 else ""


def draw_donut(
    ax: mpl.axes.Axes,
    values: list[float],
    labels: tuple[str, ...],
    colors: tuple[str, ...],
    title: str,
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
    for wedge, label in zip(wedges, autotexts, strict=True):
        red, green, blue, _ = wedge.get_facecolor()
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        label.set_color("#161616" if luminance > 0.62 else "white")
        label.set_fontweight("bold")
        label.set_fontsize(8.6)

    ax.text(0.0, 0.14, "Model B", ha="center", va="center", fontsize=9.0, color="#4B5563")
    ax.text(0.0, -0.02, "selected activation", ha="center", va="center", fontsize=8.8, color="#4B5563")
    ax.text(0.0, -0.21, r"$3.581\times10^{-3}$", ha="center", va="center", fontsize=10.1, fontweight="bold")
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
        fontsize=8.0,
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
    )
    draw_donut(
        axes[1],
        family_values,
        FAMILY_LABELS,
        FAMILY_COLORS,
        "Initiating primary particle",
    )
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
