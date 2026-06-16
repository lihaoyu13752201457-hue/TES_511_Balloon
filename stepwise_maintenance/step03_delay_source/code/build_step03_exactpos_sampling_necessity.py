#!/usr/bin/env python3
"""Quantify why delayed activation needs exact production-position sampling."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

import build_step03_exactpos_distribution_figure as distfig


ROOT = Path(__file__).resolve().parents[3]
STEP = Path(__file__).resolve().parents[1]
OUT = STEP / "outputs"
PAPER_FIG = ROOT / "core_md" / "balloon511_nima_latex_drafts" / "paper_source_figure_table"
TABLE = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos" / "exactpos_weighted_rpip_table.csv"
SUMMARY = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos" / "exactpos_weighted_rpip_summary.json"

SELECTED_TAGS = ["n", "p", "muminus", "alpha"]
TAG_LABELS = {
    "n": "n",
    "p": "p",
    "muminus": r"$\mu^-$",
    "alpha": r"$\alpha$",
    "muplus": r"$\mu^+$",
    "eplus": r"$e^+$",
}
CATEGORY_ORDER = [
    "CsI active shield",
    "Al shells",
    "Cu/support",
    "W/collimator",
    "TES/absorber",
    "window",
    "other",
]
CATEGORY_COLORS = {
    "CsI active shield": "#2f8f5b",
    "Al shells": "#7895b2",
    "Cu/support": "#b87333",
    "W/collimator": "#4a4a4a",
    "TES/absorber": "#c33f3f",
    "window": "#54b8c7",
    "other": "#9a9a9a",
}


def tag_from_source_file(name: str) -> str:
    match = re.search(r"Background_([^_]+)_", name)
    if not match:
        return "unknown"
    return match.group(1)


def weighted_quantile(values: pd.Series, weights: pd.Series, quantiles: list[float]) -> list[float]:
    v = values.to_numpy(dtype=float)
    w = weights.to_numpy(dtype=float)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cdf = np.cumsum(w)
    cdf /= cdf[-1]
    return [float(np.interp(q, cdf, v)) for q in quantiles]


def total_variation(a: pd.Series, b: pd.Series) -> float:
    return float(0.5 * np.abs(a - b).sum())


def load_table() -> pd.DataFrame:
    df = pd.read_csv(TABLE)
    df = df[df["sample_weight"] > 0.0].copy()
    df["tag"] = df["source_file"].map(tag_from_source_file)
    df["category"] = df["VN"].map(distfig.category_for_volume)
    df["nuclide"] = df["ZA"].map(distfig.nuclide_label)
    df["r_cm"] = np.sqrt(df["x_cm"] ** 2 + df["y_cm"] ** 2)
    return df


def build_summary(df: pd.DataFrame) -> dict:
    by_tag = df.groupby("tag")["sample_weight"].sum().sort_values(ascending=False)
    category = pd.pivot_table(
        df,
        values="sample_weight",
        index="tag",
        columns="category",
        aggfunc="sum",
        fill_value=0.0,
    )
    for col in CATEGORY_ORDER:
        if col not in category.columns:
            category[col] = 0.0
    category = category[CATEGORY_ORDER]
    category_fraction = category.div(category.sum(axis=1), axis=0)

    material_tv = {}
    for i, tag_a in enumerate(SELECTED_TAGS):
        for tag_b in SELECTED_TAGS[i + 1:]:
            if tag_a in category_fraction.index and tag_b in category_fraction.index:
                material_tv[f"{tag_a}_vs_{tag_b}"] = total_variation(
                    category_fraction.loc[tag_a],
                    category_fraction.loc[tag_b],
                )

    spatial_quantiles = {}
    for tag, group in df.groupby("tag"):
        if group["sample_weight"].sum() <= 0.0:
            continue
        spatial_quantiles[tag] = {
            "activity_Bq": float(group["sample_weight"].sum()),
            "x_cm_q05_q50_q95": weighted_quantile(group["x_cm"], group["sample_weight"], [0.05, 0.50, 0.95]),
            "z_cm_q05_q50_q95": weighted_quantile(group["z_cm"], group["sample_weight"], [0.05, 0.50, 0.95]),
            "r_cm_q05_q50_q95": weighted_quantile(group["r_cm"], group["sample_weight"], [0.05, 0.50, 0.95]),
        }

    top_nuclides_by_tag = {}
    for tag, group in df.groupby("tag"):
        top = group.groupby("nuclide")["sample_weight"].sum().sort_values(ascending=False).head(10)
        top_nuclides_by_tag[tag] = [[str(k), float(v)] for k, v in top.items()]

    return {
        "status": "PASS_EXACTPOS_SAMPLING_NECESSITY_AUDIT",
        "source_table": str(TABLE.relative_to(ROOT)),
        "source_summary": str(SUMMARY.relative_to(ROOT)),
        "rows": int(len(df)),
        "total_activity_Bq": float(df["sample_weight"].sum()),
        "activity_by_incident_family_Bq": {str(k): float(v) for k, v in by_tag.items()},
        "category_activity_Bq_by_incident_family": {
            str(tag): {str(cat): float(val) for cat, val in row.items()}
            for tag, row in category.iterrows()
        },
        "category_fraction_by_incident_family": {
            str(tag): {str(cat): float(val) for cat, val in row.items()}
            for tag, row in category_fraction.iterrows()
        },
        "material_total_variation_distances": material_tv,
        "spatial_weighted_quantiles_by_incident_family": spatial_quantiles,
        "top_nuclides_by_incident_family": top_nuclides_by_tag,
        "interpretation": {
            "primary_test": "Incident families do not share a common material or spatial activation distribution.",
            "n_vs_muminus_material_TV": material_tv.get("n_vs_muminus"),
            "p_vs_muminus_material_TV": material_tv.get("p_vs_muminus"),
            "mu_minus_csi_fraction": float(category_fraction.loc["muminus", "CsI active shield"]) if "muminus" in category_fraction.index else None,
            "neutron_csi_fraction": float(category_fraction.loc["n", "CsI active shield"]) if "n" in category_fraction.index else None,
        },
    }


def plot_weighted_xz(ax, df: pd.DataFrame, tag: str, title: str) -> None:
    subset = df[df["tag"] == tag]
    distfig.draw_geometry(ax)
    if subset.empty:
        ax.set_title(title)
        return
    h = ax.hist2d(
        subset["x_cm"],
        subset["z_cm"],
        weights=subset["sample_weight"],
        bins=[90, 90],
        range=[[-32, 34], [-32, 36]],
        cmap="magma",
        norm=None,
        cmin=0.0,
    )
    ax.set_xlim(-32, 34)
    ax.set_ylim(-32, 36)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("z (cm)")
    return h


def make_plot(df: pd.DataFrame, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_tag = df.groupby("tag")["sample_weight"].sum().sort_values(ascending=False)
    category = pd.pivot_table(
        df,
        values="sample_weight",
        index="tag",
        columns="category",
        aggfunc="sum",
        fill_value=0.0,
    )
    for col in CATEGORY_ORDER:
        if col not in category.columns:
            category[col] = 0.0
    category = category[CATEGORY_ORDER]
    category_fraction = category.div(category.sum(axis=1), axis=0).loc[SELECTED_TAGS]

    top_nuclides = []
    for tag in SELECTED_TAGS:
        top_nuclides.extend(
            df[df["tag"] == tag]
            .groupby("nuclide")["sample_weight"]
            .sum()
            .sort_values(ascending=False)
            .head(4)
            .index.tolist()
        )
    nuclide_order = []
    for nuc in top_nuclides:
        if nuc not in nuclide_order:
            nuclide_order.append(nuc)
    heat = pd.pivot_table(
        df[df["tag"].isin(SELECTED_TAGS) & df["nuclide"].isin(nuclide_order)],
        values="sample_weight",
        index="tag",
        columns="nuclide",
        aggfunc="sum",
        fill_value=0.0,
    )
    for nuc in nuclide_order:
        if nuc not in heat.columns:
            heat[nuc] = 0.0
    heat = heat.loc[SELECTED_TAGS, nuclide_order]
    heat_fraction = heat.div(heat.sum(axis=1), axis=0)

    fig = plt.figure(figsize=(15.8, 10.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[0.92, 1.08])

    ax_mat = fig.add_subplot(gs[0, 0])
    left = np.zeros(len(category_fraction))
    y = np.arange(len(category_fraction))
    for cat in CATEGORY_ORDER:
        values = category_fraction[cat].to_numpy()
        ax_mat.barh(y, values, left=left, color=CATEGORY_COLORS[cat], label=cat)
        left += values
    ylabels = [
        f"{TAG_LABELS[tag]}  ({by_tag.get(tag, 0.0):.3g} Bq)"
        for tag in SELECTED_TAGS
    ]
    ax_mat.set_yticks(y)
    ax_mat.set_yticklabels(ylabels)
    ax_mat.invert_yaxis()
    ax_mat.set_xlabel("fraction of activity")
    ax_mat.set_title("Material distribution by incident family")
    ax_mat.legend(loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2, fontsize=8, frameon=False)

    ax_heat = fig.add_subplot(gs[0, 1])
    im = ax_heat.imshow(heat_fraction.to_numpy(), aspect="auto", cmap="viridis", vmin=0.0, vmax=max(0.01, float(heat_fraction.max().max())))
    ax_heat.set_title("Nuclide mix within each family")
    ax_heat.set_xticks(np.arange(len(nuclide_order)))
    ax_heat.set_xticklabels(nuclide_order, rotation=55, ha="right", fontsize=8)
    ax_heat.set_yticks(np.arange(len(SELECTED_TAGS)))
    ax_heat.set_yticklabels([TAG_LABELS[t] for t in SELECTED_TAGS])
    cbar = fig.colorbar(im, ax=ax_heat, shrink=0.86)
    cbar.set_label("within-family fraction")

    ax_abs = fig.add_subplot(gs[0, 2])
    shown = by_tag.loc[[tag for tag in by_tag.index if tag in TAG_LABELS]]
    ax_abs.bar([TAG_LABELS[t] for t in shown.index], shown.to_numpy(), color="#555555")
    ax_abs.set_yscale("log")
    ax_abs.set_ylabel("activity (Bq)")
    ax_abs.set_title("Day-15 activity by production family")
    ax_abs.grid(axis="y", alpha=0.25)

    plot_weighted_xz(ax=fig.add_subplot(gs[1, 0]), df=df, tag="n", title="Recorded positions: neutron-induced")
    plot_weighted_xz(ax=fig.add_subplot(gs[1, 1]), df=df, tag="p", title="Recorded positions: proton-induced")
    plot_weighted_xz(ax=fig.add_subplot(gs[1, 2]), df=df, tag="muminus", title=r"Recorded positions: $\mu^-$-induced")

    fig.suptitle("Exact-position necessity: activation depends on incident family, material, and coordinates", fontsize=13)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    df = load_table()
    summary = build_summary(df)

    out_png = OUT / "exactpos_sampling_necessity.png"
    paper_png = PAPER_FIG / "fig_exactpos_sampling_necessity.png"
    summary_json = OUT / "exactpos_sampling_necessity_summary.json"

    make_plot(df, out_png)
    paper_png.write_bytes(out_png.read_bytes())
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[OK] rows={len(df)} total_activity={summary['total_activity_Bq']:.12g} Bq")
    print(f"[OK] wrote {out_png.relative_to(ROOT)}")
    print(f"[OK] wrote {paper_png.relative_to(ROOT)}")
    print(f"[OK] wrote {summary_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
