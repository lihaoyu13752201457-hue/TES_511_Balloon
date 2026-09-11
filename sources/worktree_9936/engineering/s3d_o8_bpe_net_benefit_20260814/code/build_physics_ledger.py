#!/usr/bin/env python3
"""Build the current-S3d activation/coupling and BPE decision ledgers.

No counterfactual transport is inferred here.  The inventory and selected W2
tables describe the current 20 mm geometry only.  The candidate table is an
analytic signal/mass/break-even screen whose purpose is to decide which paired
simulation is worth running.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np
import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
MAIN = SOURCE_ROOT / "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
INVENTORY = MAIN / "outputs/02_activation/day15_inventory.csv"
LINEAGE = MAIN / "outputs/04_common_response/selected_background_w2_lineage.csv"
FROZEN = (
    SOURCE_ROOT
    / "engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/"
    "data/frozen_delayed_source_coordinates.csv"
)
CU_FOLD = (
    SOURCE_ROOT
    / "engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/"
    "outputs/cu_reaction_fold.csv"
)

ELEMENTS = {
    1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N", 8: "O",
    11: "Na", 12: "Mg", 13: "Al", 14: "Si", 19: "K", 20: "Ca", 22: "Ti",
    23: "V", 24: "Cr", 25: "Mn", 26: "Fe", 27: "Co", 28: "Ni", 29: "Cu",
    30: "Zn", 38: "Sr", 39: "Y", 40: "Zr", 41: "Nb", 42: "Mo", 73: "Ta",
    74: "W", 79: "Au", 83: "Bi",
}

RHO_BPE = 0.95
OUTER_RADIUS_CM = 29.0
SIDE_LENGTH_CM = 70.5
MU_MASS_BPE_511 = 0.09763
MU_MASS_PLASTIC_511 = 0.09293
RHO_PLASTIC = 1.03
PLASTIC_THICKNESS_CM = 1.0
BASELINE_TOTAL_W2_CPS = 0.08832268035815599
BASELINE_F3 = 6.923750509150677e-5
BASELINE_POST_BE_S20 = 1645.3877530659986


def isotope_label(za: float | int) -> str:
    za_i = int(round(float(za)))
    z, a = za_i // 1000, za_i % 1000
    return f"{ELEMENTS.get(z, f'Z{z}')}-{a}"


def neff_from_sums(weight_sum: float, weight_sq_sum: float) -> float:
    return weight_sum * weight_sum / weight_sq_sum if weight_sq_sum > 0 else math.nan


def aggregate_current_paths() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    inventory = pd.read_csv(INVENTORY)
    inventory = inventory[inventory["geometry"] == "S3d_O8"].copy()
    lineage = pd.read_csv(LINEAGE)
    lineage = lineage[(lineage["geometry"] == "S3d_O8") & (lineage["stream"] == "delayed")].copy()

    inv = (
        inventory.groupby(["incident_family", "source_volume", "source_parent_ZA"], as_index=False)
        .agg(day15_activity_Bq=("day15_activity_Bq", "sum"), material_category=("material_category", "first"))
        .rename(columns={"incident_family": "family"})
    )
    lineage["weight_sq"] = lineage["event_weight_cps"] ** 2
    w2 = (
        lineage.groupby(["family", "source_volume", "source_parent_ZA"], as_index=False)
        .agg(
            selected_W2_cps=("event_weight_cps", "sum"),
            weight_sq_sum=("weight_sq", "sum"),
            selected_rows=("event_weight_cps", "size"),
        )
    )
    paths = inv.merge(w2, how="outer", on=["family", "source_volume", "source_parent_ZA"])
    paths["day15_activity_Bq"] = paths["day15_activity_Bq"].fillna(0.0)
    paths["selected_W2_cps"] = paths["selected_W2_cps"].fillna(0.0)
    paths["weight_sq_sum"] = paths["weight_sq_sum"].fillna(0.0)
    paths["selected_rows"] = paths["selected_rows"].fillna(0).astype(int)
    volume_material = inventory.groupby("source_volume")["material_category"].first()
    paths["material_category"] = paths["material_category"].fillna(paths["source_volume"].map(volume_material))
    paths["isotope"] = paths["source_parent_ZA"].map(isotope_label)
    paths["selected_W2_per_Bq_cps_Bq"] = paths["selected_W2_cps"] / paths["day15_activity_Bq"].replace(0, np.nan)
    paths["selected_Neff"] = [neff_from_sums(w, q) for w, q in zip(paths["selected_W2_cps"], paths["weight_sq_sum"])]
    paths["support_flag"] = np.select(
        [
            (paths["day15_activity_Bq"] > 0) & (paths["selected_W2_cps"] > 0),
            (paths["day15_activity_Bq"] > 0) & (paths["selected_W2_cps"] == 0),
            (paths["day15_activity_Bq"] == 0) & (paths["selected_W2_cps"] > 0),
        ],
        ["FINITE_MC_COUPLING", "ZERO_SURVIVOR_NOT_ZERO_RATE", "INVENTORY_JOIN_GAP"],
        default="ZERO_ZERO",
    )
    paths = paths.sort_values("selected_W2_cps", ascending=False)

    aggregates: dict[str, pd.DataFrame] = {}
    for name, columns in {
        "family": ["family"],
        "material": ["material_category"],
        "isotope": ["isotope"],
        "volume": ["source_volume"],
        "family_material": ["family", "material_category"],
        "family_isotope": ["family", "isotope"],
    }.items():
        frame = (
            paths.groupby(columns, as_index=False, dropna=False)
            .agg(
                day15_activity_Bq=("day15_activity_Bq", "sum"),
                selected_W2_cps=("selected_W2_cps", "sum"),
                weight_sq_sum=("weight_sq_sum", "sum"),
                selected_rows=("selected_rows", "sum"),
                path_count=("source_volume", "size"),
            )
        )
        frame["selected_W2_per_Bq_cps_Bq"] = frame["selected_W2_cps"] / frame["day15_activity_Bq"].replace(0, np.nan)
        frame["selected_Neff"] = [neff_from_sums(w, q) for w, q in zip(frame["selected_W2_cps"], frame["weight_sq_sum"])]
        aggregates[name] = frame.sort_values("selected_W2_cps", ascending=False)
    return paths, aggregates


def raw_bpe_mass_kg(thickness_cm: float) -> tuple[float, float, float]:
    if thickness_cm == 0:
        return 0.0, 0.0, 0.0
    side = math.pi * (OUTER_RADIUS_CM**2 - (OUTER_RADIUS_CM - thickness_cm) ** 2) * SIDE_LENGTH_CM
    two_caps = 2.0 * math.pi * OUTER_RADIUS_CM**2 * thickness_cm
    return side * RHO_BPE / 1000.0, two_caps * RHO_BPE / 1000.0, (side + two_caps) * RHO_BPE / 1000.0


def build_candidate_table() -> pd.DataFrame:
    rows = []
    for thickness_mm in [0, 10, 20, 30]:
        thickness_cm = thickness_mm / 10.0
        side, caps, total = raw_bpe_mass_kg(thickness_cm)
        t_bpe = math.exp(-MU_MASS_BPE_511 * RHO_BPE * thickness_cm)
        t_plastic = math.exp(-MU_MASS_PLASTIC_511 * RHO_PLASTIC * PLASTIC_THICKNESS_CM)
        if thickness_mm == 30:
            feasibility = "INVALID_WITH_FROZEN_GEOMETRY: cap overlaps Al/Kapton; side consumes all clearance"
        else:
            feasibility = "geometrically screenable"
        rows.append(
            {
                "BPE_thickness_mm": thickness_mm,
                "fixed_outer_interface": "side r_out=29 cm; caps z_out=-26.5/+48 cm",
                "side_inner_radius_cm": OUTER_RADIUS_CM - thickness_cm if thickness_mm else math.nan,
                "bottom_inner_z_cm": -26.5 + thickness_cm if thickness_mm else math.nan,
                "top_inner_z_cm": 48.0 - thickness_cm if thickness_mm else math.nan,
                "raw_pre_relief_side_mass_kg": side,
                "raw_pre_relief_two_caps_mass_kg": caps,
                "raw_pre_relief_total_mass_kg": total,
                "mass_change_vs_20mm_kg": total - raw_bpe_mass_kg(2.0)[2],
                "normal_511_unscattered_T_BPE": t_bpe,
                "normal_511_unscattered_T_with_fixed_plastic": t_bpe * t_plastic,
                "relative_S20_vs_0mm": t_bpe,
                "relative_B20max_vs_0mm": t_bpe**2,
                "required_total_background_reduction_vs_0mm_for_net_F3_gain": 1.0 - t_bpe**2,
                "engineering_feasibility": feasibility,
            }
        )
    return pd.DataFrame(rows)


def plot_layer_cross_section(out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4), constrained_layout=True)
    ax = axes[0]
    layers = [
        (29.0, 30.0, "active plastic", "#60a5fa"),
        (27.0, 29.0, "5 wt% BPE", "#eab308"),
        (26.0, 27.0, "void", "#f8fafc"),
        (25.7, 26.0, "Al shell", "#94a3b8"),
        (25.4, 25.7, "gap", "#f8fafc"),
        (25.37, 25.40, "Kapton", "#f97316"),
        (25.2, 25.37, "gap", "#f8fafc"),
        (21.2, 25.2, "active BGO", "#22c55e"),
        (20.6, 21.2, "void", "#f8fafc"),
        (20.1, 20.6, "vacuum-jacket Al", "#64748b"),
    ]
    for r0, r1, label, color in layers:
        ax.barh(0, r1 - r0, left=r0, height=0.72, color=color, edgecolor="#334155", linewidth=0.5, label=label)
    ax.set_xlim(19.7, 30.4)
    ax.set_yticks([])
    ax.set_xlabel("InstrumentFrame side radius r (cm)")
    ax.set_title("Side-wall radial stack (general sector)", loc="left", weight="bold")
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), ncol=2, frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    ax.annotate("toward TES", xy=(20.0, -0.45), xytext=(23.5, -0.45), arrowprops=dict(arrowstyle="->", color="#111827"), va="center")
    ax.annotate("outside", xy=(30.2, 0.45), ha="right", va="center", fontsize=9)

    ax = axes[1]
    sequence = [
        ("outside", 0.8, "#f8fafc"),
        ("plastic\n10 mm", 1.0, "#60a5fa"),
        ("BPE\n20 mm", 2.0, "#eab308"),
        ("void / apertures", 1.5, "#f8fafc"),
        ("Be window", 0.55, "#c084fc"),
        ("cryostat → TES", 1.4, "#cbd5e1"),
    ]
    cursor = 0.0
    for label, width, color in sequence:
        ax.add_patch(Rectangle((cursor, -0.35), width, 0.7, facecolor=color, edgecolor="#334155"))
        ax.text(cursor + width / 2, 0, label, ha="center", va="center", fontsize=9)
        cursor += width
    ax.annotate("focused 511 keV", xy=(cursor, 0.55), xytext=(0.1, 0.55), arrowprops=dict(arrowstyle="->", lw=2, color="#dc2626"), color="#dc2626", va="center")
    ax.set_xlim(-0.1, cursor + 0.1)
    ax.set_ylim(-0.8, 0.9)
    ax.axis("off")
    ax.set_title("Focused side-window path", loc="left", weight="bold")
    ax.text(
        0.0,
        -0.72,
        "BGO/Al have a signal aperture; BPE and plastic do not.\nCurrent focused EventList begins post-Be and omits both outer layers.",
        fontsize=10,
        color="#7f1d1d",
    )
    fig.suptitle("Authoritative S3d-O8 layer order", fontsize=15, weight="bold")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_activation_coupling(aggregates: dict[str, pd.DataFrame], out: Path) -> None:
    nmat = aggregates["family_material"].query("family == 'n'").copy()
    nmat = nmat.sort_values("day15_activity_Bq", ascending=False)
    labels = nmat["material_category"].str.replace("_", " ").tolist()
    bq_share = nmat["day15_activity_Bq"] / nmat["day15_activity_Bq"].sum()
    w2_share = nmat["selected_W2_cps"] / nmat["selected_W2_cps"].sum()

    niso = aggregates["family_isotope"].query("family == 'n' and selected_W2_cps > 0").copy()
    niso = niso.sort_values("selected_W2_cps", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.7), constrained_layout=True)
    x = np.arange(len(labels))
    axes[0].bar(x - 0.2, bq_share, width=0.4, color="#94a3b8", label="day-15 production Bq share")
    axes[0].bar(x + 0.2, w2_share, width=0.4, color="#dc6b35", label="selected W2 share")
    axes[0].set_xticks(x, labels, rotation=35, ha="right", fontsize=8)
    axes[0].set_ylabel("Share within incident-neutron family")
    axes[0].set_title("Production is not detector coupling", loc="left", weight="bold")
    axes[0].legend(frameon=False)
    axes[0].spines[["top", "right"]].set_visible(False)
    axes[0].grid(axis="y", color="#e2e8f0", linewidth=0.7)

    x = np.arange(len(niso))
    axes[1].bar(x, niso["selected_W2_cps"], color="#4f6bed")
    axes[1].set_xticks(x, niso["isotope"], rotation=30, ha="right")
    axes[1].set_ylabel("Selected delayed W2 (cps)")
    axes[1].set_title("Current n-induced W2 isotope support", loc="left", weight="bold")
    for i, row in enumerate(niso.itertuples()):
        axes[1].text(i, row.selected_W2_cps, f"N={row.selected_rows}\nNeff={row.selected_Neff:.1f}", ha="center", va="bottom", fontsize=7)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].grid(axis="y", color="#e2e8f0", linewidth=0.7)
    fig.suptitle("Current 20 mm geometry only — no BPE/no-BPE causal contrast", fontsize=14, weight="bold")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_hotspots(out: Path) -> None:
    frozen = pd.read_csv(FROZEN)
    fig, ax = plt.subplots(figsize=(8.2, 8.2), constrained_layout=True)
    ax.add_patch(Rectangle((-29, -26.5), 58, 74.5, fill=False, edgecolor="#ca8a04", linewidth=2.0, label="BPE outer envelope projection"))
    ax.add_patch(Rectangle((-27, -24.5), 54, 70.5, fill=False, edgecolor="#eab308", linewidth=1.2, linestyle="--", label="BPE inner envelope projection"))
    colors = np.where(frozen["family"] == "n", "#dc2626", "#64748b")
    max_weight = frozen["event_weight_cps"].max()
    sizes = 18 + 780 * np.sqrt(frozen["event_weight_cps"] / max_weight)
    ax.scatter(frozen["instrument_x_cm"], frozen["instrument_z_cm"], s=sizes, c=colors, alpha=0.62, edgecolors="white", linewidths=0.4)
    ax.scatter([], [], color="#dc2626", label="n-induced selected event")
    ax.scatter([], [], color="#64748b", label="other family selected event")
    ax.plot([0], [-5.2], marker="*", markersize=15, color="#111827", label="TES plane reference")
    top = frozen.nlargest(6, "event_weight_cps")
    for row in top.itertuples():
        ax.annotate(row.source_volume.replace("_", " ")[:25], (row.instrument_x_cm, row.instrument_z_cm), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-31, 31)
    ax.set_ylim(-29, 50)
    ax.set_xlabel("InstrumentFrame x (cm)")
    ax.set_ylabel("InstrumentFrame z (cm)")
    ax.set_title("Frozen selected-W2 source positions", loc="left", weight="bold")
    ax.text(-30, 46.5, "Marker area ∝ √event weight; frozen Neff = 12.04", fontsize=9, color="#7f1d1d")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color="#e2e8f0", linewidth=0.6)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_physics_flow(aggregates: dict[str, pd.DataFrame], out: Path) -> None:
    fam = aggregates["family"].set_index("family")
    n_bq = float(fam.loc["n", "day15_activity_Bq"])
    n_w2 = float(fam.loc["n", "selected_W2_cps"])
    nmat = aggregates["family_material"].query("family=='n'").nlargest(4, "day15_activity_Bq")
    niso = aggregates["family_isotope"].query("family=='n'").nlargest(4, "selected_W2_cps")

    fig, ax = plt.subplots(figsize=(15, 6.1), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    nodes = [
        (0.02, 0.35, 0.14, 0.30, "Incident n\n100,000 histories", "#dbeafe"),
        (0.20, 0.25, 0.16, 0.50, "20 mm BPE boundary\n34,031 contacts\n22,988 primary reach inner\n3,876 inward 478-keV\ntrack-first-exits", "#fef3c7"),
        (0.43, 0.21, 0.16, 0.58, "Current material Bq\n" + "\n".join(f"{r.material_category[:17]} {r.day15_activity_Bq:.1f}" for r in nmat.itertuples()) + f"\nall n: {n_bq:.2f} Bq", "#e2e8f0"),
        (0.65, 0.27, 0.14, 0.46, "Current isotopes\n" + "\n".join(f"{r.isotope} {r.selected_W2_cps:.4f} cps" for r in niso.itertuples()), "#ede9fe"),
        (0.84, 0.35, 0.14, 0.30, f"Selected delayed W2\nn = {n_w2:.6f} cps\n43.46% of delayed", "#fee2e2"),
    ]
    for x, y, w, h, text, color in nodes:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="#334155", linewidth=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9)
    for start, end, label, dashed in [
        ((0.16, 0.50), (0.20, 0.50), "transport", False),
        ((0.36, 0.50), (0.43, 0.50), "A/B production\nUNMEASURED", True),
        ((0.59, 0.50), (0.65, 0.50), "decay", False),
        ((0.79, 0.50), (0.84, 0.50), "W2/Bq\ncoupling", False),
    ]:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", lw=1.8, linestyle="--" if dashed else "-", color="#b91c1c" if dashed else "#334155"))
        ax.text((start[0] + end[0]) / 2, 0.56, label, ha="center", va="bottom", fontsize=8, color="#b91c1c" if dashed else "#334155")
    ax.text(0.02, 0.92, "Incident n → BPE transport → material → isotope → day-15 Bq → selected W2", fontsize=15, weight="bold")
    ax.text(0.02, 0.84, "Only the BPE boundary and the current-geometry downstream columns exist. The dashed causal link has never been measured against 0 mm.", fontsize=10, color="#7f1d1d")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_decision_break_even(candidates: pd.DataFrame, out: Path) -> None:
    x = candidates["BPE_thickness_mm"].to_numpy()
    signal = candidates["relative_S20_vs_0mm"].to_numpy()
    b_limit = candidates["relative_B20max_vs_0mm"].to_numpy()
    mass = candidates["raw_pre_relief_total_mass_kg"].to_numpy()
    fig, ax = plt.subplots(figsize=(10.8, 5.8), constrained_layout=True)
    ax.plot(x, signal, marker="o", linewidth=2.2, color="#2563eb", label="relative focused S20 (XCOM narrow-line)")
    ax.plot(x, b_limit, marker="s", linewidth=2.2, color="#dc2626", label="max B/B(0 mm) for equal F3")
    ax.axhline(1, color="#94a3b8", linewidth=1)
    ax.set_ylim(0.5, 1.03)
    ax.set_xlabel("Global BPE thickness (mm)")
    ax.set_ylabel("Relative to 0 mm BPE")
    ax.set_title("Signal penalty sets a demanding background break-even", loc="left", weight="bold")
    ax.grid(color="#e2e8f0", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower left")
    ax2 = ax.twinx()
    ax2.bar(x, mass, width=4.5, alpha=0.17, color="#ca8a04", label="raw/pre-relief BPE mass")
    ax2.set_ylabel("Raw/pre-relief BPE mass (kg)")
    ax2.set_ylim(0, 58)
    ax2.spines["top"].set_visible(False)
    ax.annotate("20 mm must reduce total B by >31.0%\nto offset its 17.0% signal loss", xy=(20, b_limit[2]), xytext=(8, 0.57), arrowprops=dict(arrowstyle="->", color="#7f1d1d"), color="#7f1d1d", fontsize=9)
    ax.annotate("30 mm overlaps frozen cap mechanics", xy=(30, signal[3]), xytext=(22, 0.95), arrowprops=dict(arrowstyle="->", color="#7f1d1d"), color="#7f1d1d", fontsize=9)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_geometry_ledger(out: Path) -> None:
    rows = [
        {
            "component": "BPE side shell",
            "material": "BoratedPolyethylene5wtB",
            "density_g_cm3": 0.95,
            "composition": "C:H:B atoms = 1000:2000:68; 4.980 wt% natural B",
            "instrument_local_extent_cm": "r=27..29; z=-24.5..46; phi=0..360 deg",
            "nominal_thickness_cm": 2.0,
            "raw_pre_relief_volume_cm3": 24806.015592745,
            "raw_pre_relief_mass_kg": 23.5657148131,
            "coverage_note": "closed side; only NF2 support reliefs; no signal-window or pump-line cut",
        },
        {
            "component": "BPE bottom cap",
            "material": "BoratedPolyethylene5wtB",
            "density_g_cm3": 0.95,
            "composition": "C:H:B atoms = 1000:2000:68; 4.980 wt% natural B",
            "instrument_local_extent_cm": "solid r=0..29; z=-26.5..-24.5",
            "nominal_thickness_cm": 2.0,
            "raw_pre_relief_volume_cm3": 5284.158843338,
            "raw_pre_relief_mass_kg": 5.01995090117,
            "coverage_note": "solid cap; only NF2 support reliefs",
        },
        {
            "component": "BPE top cap",
            "material": "BoratedPolyethylene5wtB",
            "density_g_cm3": 0.95,
            "composition": "C:H:B atoms = 1000:2000:68; 4.980 wt% natural B",
            "instrument_local_extent_cm": "solid r=0..29; z=46..48",
            "nominal_thickness_cm": 2.0,
            "raw_pre_relief_volume_cm3": 5284.158843338,
            "raw_pre_relief_mass_kg": 5.01995090117,
            "coverage_note": "solid cap; only NF2 support reliefs; no top service opening",
        },
    ]
    pd.DataFrame(rows).to_csv(out, index=False)


def main() -> None:
    data_dir = PACKAGE / "data"
    figure_dir = PACKAGE / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    paths, aggregates = aggregate_current_paths()
    paths.to_csv(data_dir / "activation_coupling_by_path.csv", index=False)
    for name, frame in aggregates.items():
        frame.to_csv(data_dir / f"activation_coupling_by_{name}.csv", index=False)
    candidates = build_candidate_table()
    candidates.to_csv(data_dir / "bpe_candidate_analytic_screen.csv", index=False)
    write_geometry_ledger(data_dir / "geometry_material_ledger.csv")

    n_isotopes = aggregates["family_isotope"].query("family=='n'").set_index("isotope")
    n_cu_current = {isotope: float(n_isotopes.loc[isotope, "selected_W2_cps"]) for isotope in ["Cu-61", "Cu-62", "Cu-64"]}
    current_indices = {"Cu-61": 0.8847553386855576, "Cu-62": 0.8421455746190777, "Cu-64": 0.8965602431961425}
    proxy_no_bpe_cu = sum(n_cu_current[k] / current_indices[k] for k in current_indices)
    current_cu = sum(n_cu_current.values())
    proxy_total_no_bpe = BASELINE_TOTAL_W2_CPS + proxy_no_bpe_cu - current_cu
    t_bpe20 = float(candidates.loc[candidates["BPE_thickness_mm"] == 20, "relative_S20_vs_0mm"].iloc[0])
    t_plastic = math.exp(-MU_MASS_PLASTIC_511 * RHO_PLASTIC * PLASTIC_THICKNESS_CM)
    summary = {
        "current_geometry_only": {
            "inventory_total_Bq": float(aggregates["family"]["day15_activity_Bq"].sum()),
            "selected_delayed_W2_cps": float(aggregates["family"]["selected_W2_cps"].sum()),
            "incident_n_inventory_Bq": float(aggregates["family"].set_index("family").loc["n", "day15_activity_Bq"]),
            "incident_n_selected_W2_cps": float(aggregates["family"].set_index("family").loc["n", "selected_W2_cps"]),
            "bpe_self_inventory_Bq": float(paths.loc[paths["material_category"] == "bpe_neutron_shield", "day15_activity_Bq"].sum()),
            "bpe_self_selected_W2_cps": float(paths.loc[paths["material_category"] == "bpe_neutron_shield", "selected_W2_cps"].sum()),
            "bpe_zero_survivor_guard": "zero selected survivor is not zero physical coupling",
        },
        "analytic_signal_fold": {
            "mu_mass_BPE_511_cm2_g": MU_MASS_BPE_511,
            "normal_T_BPE_20mm": t_bpe20,
            "normal_T_fixed_plastic_10mm": t_plastic,
            "normal_T_full_outer_layers_20mm_BPE": t_bpe20 * t_plastic,
            "post_Be_S20": BASELINE_POST_BE_S20,
            "estimated_full_envelope_S20_20mm": BASELINE_POST_BE_S20 * t_bpe20 * t_plastic,
            "estimated_full_envelope_S20_0mm": BASELINE_POST_BE_S20 * t_plastic,
            "estimated_F3_20mm_if_background_unchanged": BASELINE_F3 / (t_bpe20 * t_plastic),
            "estimated_F3_0mm_if_background_unchanged": BASELINE_F3 / t_plastic,
            "break_even_B0_over_B20": 1.0 / t_bpe20**2,
        },
        "direct_Cu_boundary_proxy_not_prediction": {
            "current_selected_n_Cu_W2_cps": current_cu,
            "folded_proxy_no_BPE_selected_n_Cu_W2_cps": proxy_no_bpe_cu,
            "proxy_total_W2_no_BPE_cps": proxy_total_no_bpe,
            "proxy_total_background_ratio_B0_over_B20": proxy_total_no_bpe / BASELINE_TOTAL_W2_CPS,
            "conditional_F3_ratio_remove_over_20mm": t_bpe20 * math.sqrt(proxy_total_no_bpe / BASELINE_TOTAL_W2_CPS),
            "guard": "uses 13 current n-Cu survivor rows and boundary indices; excludes Nb/Mu/position/prompt/capture; scenario only",
        },
        "decision": {
            "single_engineering_conditional_verdict": "REMOVE",
            "partition": "remove all three BPE volumes: side r=27..29,z=-24.5..46; bottom r=0..29,z=-26.5..-24.5; top r=0..29,z=46..48 (InstrumentFrame cm)",
            "mass_change_raw_pre_relief_kg": -raw_bpe_mass_kg(2.0)[2],
            "mass_change_boolean_net_diagnostic_kg_approx": -33.16,
            "unique_blocker": "matched 0 mm versus 20 mm corrected-neutron causal pair, including volume×isotope inventory, capture/prompt veto guard, exact-position selected W2, and focused source launched outside the fixed plastic/BPE envelope",
        },
    }
    (data_dir / "physics_ledger_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    plot_layer_cross_section(figure_dir / "bpe_authoritative_layer_cross_section.png")
    plot_activation_coupling(aggregates, figure_dir / "activation_production_vs_coupling.png")
    plot_hotspots(figure_dir / "selected_w2_hotspot_map.png")
    plot_physics_flow(aggregates, figure_dir / "incident_to_selected_w2_flow.png")
    plot_decision_break_even(candidates, figure_dir / "bpe_signal_background_break_even.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
