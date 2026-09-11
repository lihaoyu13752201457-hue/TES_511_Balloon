#!/usr/bin/env python3
"""Quantify why delayed activation needs exact production-position sampling."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

import build_step03_exactpos_distribution_figure as distfig


ROOT = Path(__file__).resolve().parents[3]
STEP = Path(__file__).resolve().parents[1]
OUT = STEP / "outputs"
PAPER_FIG = ROOT / "core_md" / "balloon511_nima_latex_drafts" / "paper_source_figure_table"
TABLE = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2" / "exactpos_weighted_rpip_table_m50000_s260613.csv"
SUMMARY = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2" / "fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json"

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


def weighted_quantile(values: list[float], weights: list[float], quantiles: list[float]) -> list[float]:
    pairs = sorted(zip(values, weights), key=lambda item: item[0])
    total = sum(weight for _, weight in pairs)
    if total <= 0.0:
        return [math.nan for _ in quantiles]
    out: list[float] = []
    for q in quantiles:
        target = q * total
        acc = 0.0
        chosen = pairs[-1][0]
        for value, weight in pairs:
            acc += weight
            if acc >= target:
                chosen = value
                break
        out.append(float(chosen))
    return out


def total_variation(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return float(0.5 * sum(abs(a.get(key, 0.0) - b.get(key, 0.0)) for key in keys))


def load_table() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        source_col = "source_file" if "source_file" in (reader.fieldnames or []) else "source_sim"
        for row in reader:
            weight = float(row["sample_weight"])
            if weight <= 0.0:
                continue
            x = float(row["x_cm"])
            y = float(row["y_cm"])
            z = float(row["z_cm"])
            rows.append(
                {
                    "x_cm": x,
                    "y_cm": y,
                    "z_cm": z,
                    "r_cm": math.sqrt(x * x + y * y),
                    "sample_weight": weight,
                    "tag": tag_from_source_file(row.get(source_col, "")),
                    "category": distfig.category_for_volume(row["VN"]),
                    "nuclide": distfig.nuclide_label(int(row["ZA"])),
                }
            )
    return rows


def summarize(rows: list[dict[str, float | str]]) -> tuple[dict[str, float], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    by_tag: defaultdict[str, float] = defaultdict(float)
    category: defaultdict[str, defaultdict[str, float]] = defaultdict(lambda: defaultdict(float))
    nuclide: defaultdict[str, defaultdict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        tag = str(row["tag"])
        weight = float(row["sample_weight"])
        by_tag[tag] += weight
        category[tag][str(row["category"])] += weight
        nuclide[tag][str(row["nuclide"])] += weight
    return dict(by_tag), {k: dict(v) for k, v in category.items()}, {k: dict(v) for k, v in nuclide.items()}


def category_fractions(category: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    fractions: dict[str, dict[str, float]] = {}
    for tag, row in category.items():
        total = sum(row.values())
        fractions[tag] = {cat: (row.get(cat, 0.0) / total if total > 0.0 else 0.0) for cat in CATEGORY_ORDER}
    return fractions


def build_summary(rows: list[dict[str, float | str]]) -> dict:
    by_tag, category, nuclide = summarize(rows)
    fractions = category_fractions(category)

    material_tv: dict[str, float] = {}
    for i, tag_a in enumerate(SELECTED_TAGS):
        for tag_b in SELECTED_TAGS[i + 1 :]:
            if tag_a in fractions and tag_b in fractions:
                material_tv[f"{tag_a}_vs_{tag_b}"] = total_variation(fractions[tag_a], fractions[tag_b])

    spatial_quantiles: dict[str, dict[str, float | list[float]]] = {}
    rows_by_tag: defaultdict[str, list[dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        rows_by_tag[str(row["tag"])].append(row)
    for tag, group in rows_by_tag.items():
        weights = [float(row["sample_weight"]) for row in group]
        spatial_quantiles[tag] = {
            "activity_Bq": sum(weights),
            "x_cm_q05_q50_q95": weighted_quantile([float(row["x_cm"]) for row in group], weights, [0.05, 0.50, 0.95]),
            "z_cm_q05_q50_q95": weighted_quantile([float(row["z_cm"]) for row in group], weights, [0.05, 0.50, 0.95]),
            "r_cm_q05_q50_q95": weighted_quantile([float(row["r_cm"]) for row in group], weights, [0.05, 0.50, 0.95]),
        }

    top_nuclides_by_tag = {
        tag: [[name, value] for name, value in sorted(row.items(), key=lambda kv: kv[1], reverse=True)[:10]]
        for tag, row in nuclide.items()
    }

    return {
        "status": "PASS_FIX5_EXACTPOS_SAMPLING_NECESSITY_AUDIT",
        "source_table": str(TABLE.relative_to(ROOT)),
        "source_summary": str(SUMMARY.relative_to(ROOT)),
        "rows": len(rows),
        "total_activity_Bq": sum(by_tag.values()),
        "activity_by_incident_family_Bq": {str(k): float(v) for k, v in sorted(by_tag.items(), key=lambda kv: kv[1], reverse=True)},
        "category_activity_Bq_by_incident_family": category,
        "category_fraction_by_incident_family": fractions,
        "material_total_variation_distances": material_tv,
        "spatial_weighted_quantiles_by_incident_family": spatial_quantiles,
        "top_nuclides_by_incident_family": top_nuclides_by_tag,
        "interpretation": {
            "primary_test": "Incident families do not share a common material or spatial activation distribution.",
            "n_vs_muminus_material_TV": material_tv.get("n_vs_muminus"),
            "p_vs_muminus_material_TV": material_tv.get("p_vs_muminus"),
            "mu_minus_csi_fraction": fractions.get("muminus", {}).get("CsI active shield"),
            "neutron_csi_fraction": fractions.get("n", {}).get("CsI active shield"),
        },
    }


def plot_weighted_xz(ax, rows: list[dict[str, float | str]], tag: str, title: str) -> None:
    subset = [row for row in rows if row["tag"] == tag]
    distfig.draw_geometry(ax)
    if not subset:
        ax.set_title(title)
        return
    ax.hist2d(
        [float(row["x_cm"]) for row in subset],
        [float(row["z_cm"]) for row in subset],
        weights=[float(row["sample_weight"]) for row in subset],
        bins=[90, 90],
        range=[[-32, 34], [-32, 36]],
        cmap="magma",
        cmin=0.0,
    )
    ax.set_xlim(-32, 34)
    ax.set_ylim(-32, 36)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("z (cm)")


def make_plot(rows: list[dict[str, float | str]], out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_tag, category, nuclide = summarize(rows)
    fractions = category_fractions(category)

    top_nuclides: list[str] = []
    for tag in SELECTED_TAGS:
        for name, _ in sorted(nuclide.get(tag, {}).items(), key=lambda kv: kv[1], reverse=True)[:4]:
            if name not in top_nuclides:
                top_nuclides.append(name)

    heat = np.zeros((len(SELECTED_TAGS), len(top_nuclides)))
    for i, tag in enumerate(SELECTED_TAGS):
        total = by_tag.get(tag, 0.0)
        for j, name in enumerate(top_nuclides):
            heat[i, j] = nuclide.get(tag, {}).get(name, 0.0) / total if total > 0.0 else 0.0

    fig = plt.figure(figsize=(15.8, 10.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[0.92, 1.08])

    ax_mat = fig.add_subplot(gs[0, 0])
    left = np.zeros(len(SELECTED_TAGS))
    y = np.arange(len(SELECTED_TAGS))
    for cat in CATEGORY_ORDER:
        values = np.asarray([fractions.get(tag, {}).get(cat, 0.0) for tag in SELECTED_TAGS])
        ax_mat.barh(y, values, left=left, color=CATEGORY_COLORS[cat], label=cat)
        left += values
    ylabels = [f"{TAG_LABELS[tag]}  ({by_tag.get(tag, 0.0):.3g} Bq)" for tag in SELECTED_TAGS]
    ax_mat.set_yticks(y)
    ax_mat.set_yticklabels(ylabels)
    ax_mat.invert_yaxis()
    ax_mat.set_xlabel("fraction of activity")
    ax_mat.set_title("Material distribution by incident family")
    ax_mat.legend(loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2, fontsize=8, frameon=False)

    ax_heat = fig.add_subplot(gs[0, 1])
    vmax = max(0.01, float(heat.max()) if heat.size else 0.01)
    im = ax_heat.imshow(heat, aspect="auto", cmap="viridis", vmin=0.0, vmax=vmax)
    ax_heat.set_title("Nuclide mix within each family")
    ax_heat.set_xticks(np.arange(len(top_nuclides)))
    ax_heat.set_xticklabels(top_nuclides, rotation=55, ha="right", fontsize=8)
    ax_heat.set_yticks(np.arange(len(SELECTED_TAGS)))
    ax_heat.set_yticklabels([TAG_LABELS[tag] for tag in SELECTED_TAGS])
    cbar = fig.colorbar(im, ax=ax_heat, shrink=0.86)
    cbar.set_label("within-family fraction")

    ax_abs = fig.add_subplot(gs[0, 2])
    shown = [(tag, value) for tag, value in sorted(by_tag.items(), key=lambda kv: kv[1], reverse=True) if tag in TAG_LABELS]
    ax_abs.bar([TAG_LABELS[tag] for tag, _ in shown], [value for _, value in shown], color="#555555")
    ax_abs.set_yscale("log")
    ax_abs.set_ylabel("activity (Bq)")
    ax_abs.set_title("Day-15 activity by production family")
    ax_abs.grid(axis="y", alpha=0.25)

    plot_weighted_xz(fig.add_subplot(gs[1, 0]), rows=rows, tag="n", title="Recorded positions: neutron-induced")
    plot_weighted_xz(fig.add_subplot(gs[1, 1]), rows=rows, tag="p", title="Recorded positions: proton-induced")
    plot_weighted_xz(fig.add_subplot(gs[1, 2]), rows=rows, tag="muminus", title=r"Recorded positions: $\mu^-$-induced")

    fig.suptitle("Exact-position necessity: activation depends on incident family, material, and coordinates", fontsize=13)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    rows = load_table()
    summary = build_summary(rows)

    out_png = OUT / "exactpos_sampling_necessity.png"
    paper_png = PAPER_FIG / "fig_exactpos_sampling_necessity.png"
    summary_json = OUT / "exactpos_sampling_necessity_summary.json"

    make_plot(rows, out_png)
    paper_png.write_bytes(out_png.read_bytes())
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[OK] rows={len(rows)} total_activity={summary['total_activity_Bq']:.12g} Bq")
    print(f"[OK] wrote {out_png.relative_to(ROOT)}")
    print(f"[OK] wrote {paper_png.relative_to(ROOT)}")
    print(f"[OK] wrote {summary_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
