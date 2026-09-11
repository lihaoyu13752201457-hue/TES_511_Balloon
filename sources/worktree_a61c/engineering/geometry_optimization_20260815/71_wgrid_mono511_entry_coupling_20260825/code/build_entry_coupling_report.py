#!/usr/bin/env python3
"""Build a reproducible W-grid -> SH3 TES atmospheric-511 coupling report.

The inputs are frozen outputs from the completed W-grid monoenergetic run and
the compact, selected-event IA audit produced by ``extract_selected_paths.py``.
No transport is launched.  The script writes only a bounded report bundle.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle


CJK_FONT_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
if CJK_FONT_PATH.is_file():
    font_manager.fontManager.addfont(str(CJK_FONT_PATH))
    CJK_FONT_FAMILY = font_manager.FontProperties(fname=str(CJK_FONT_PATH)).get_name()
else:
    CJK_FONT_FAMILY = "DejaVu Sans"


PKG68_REL = "engineering/geometry_optimization_20260815/68_sh3_wgrid_mono511_statistics_20260824"
COMPARE_REL = f"{PKG68_REL}/outputs/01_wgrid_mono511_response_comparison_20260825/comparison_summary.json"
CATALOG_REL = f"{PKG68_REL}/outputs/01_wgrid_mono511_response_comparison_20260825/response/mono_line_event_catalog.npz"
GEOMETRY_REL = f"{PKG68_REL}/transport_authority/geometry/SH3_Assembly_OptV3.geo"
PARMA_REL = f"{PKG68_REL}/outputs/01_wgrid_mono511_response_comparison_20260825/frozen_parma_authority/parma511_day15_80bins.csv"
OUT_REL = "engineering/geometry_optimization_20260815/71_wgrid_mono511_entry_coupling_20260825/outputs/01_entry_path_diagnosis_20260825"
EVENTS_REL = f"{OUT_REL}/selected_event_paths.csv"
SUMMARY_REL = f"{OUT_REL}/path_summary.json"

ROUTE_LABELS = {
    "full_grid_envelope_crossing": "完整跨越前网格包络",
    "partial_or_grazing_grid_envelope_contact": "部分/掠过前网格包络",
    "grid_facing_bypass_outside_envelope": "朝前但从包络外绕过",
    "rear_or_side_bypass": "从后方或侧方绕过",
}
ROUTE_ORDER = list(ROUTE_LABELS)
ROUTE_COLORS = {
    "完整跨越前网格包络": "#2774AE",
    "部分/掠过前网格包络": "#78B7D0",
    "朝前但从包络外绕过": "#E29036",
    "从后方或侧方绕过": "#68727D",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    require(bool(rows), f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def wilson95(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return center - half, center + half


def sqlite_type(rows: list[dict[str, Any]], field: str) -> str:
    values = [row.get(field) for row in rows if row.get(field) is not None]
    if any(isinstance(value, str) for value in values):
        return "TEXT"
    if any(isinstance(value, float) for value in values):
        return "REAL"
    return "INTEGER"


def build_sqlite_snapshot(path: Path, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    connection.row_factory = sqlite3.Row
    queried: dict[str, list[dict[str, Any]]] = {}
    try:
        for table, rows in datasets.items():
            require(bool(rows), f"dataset {table} is empty")
            ordered = [{"_row_order": index, **row} for index, row in enumerate(rows)]
            fields = list(ordered[0])
            require(all(list(row) == fields for row in ordered), f"dataset {table} has inconsistent fields")
            columns = ", ".join(f'"{field}" {sqlite_type(ordered, field)}' for field in fields)
            connection.execute(f'CREATE TABLE "{table}" ({columns})')
            placeholders = ", ".join("?" for _ in fields)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                [[row[field] for field in fields] for row in ordered],
            )
            queried[table] = [
                dict(row)
                for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY _row_order').fetchall()
            ]
        connection.commit()
    finally:
        connection.close()
    os.replace(temp, path)
    return queried


def make_schematic(
    output_dir: Path,
    route_by_sample: dict[str, Counter[str]],
    atmospheric_near: int,
    grid_near: int,
    direct: int,
    rayleigh_first: int,
) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [CJK_FONT_FAMILY, "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 10.5,
    })
    fig = plt.figure(figsize=(16, 10), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=(1.2, 1.0), height_ratios=(1.1, 0.9))

    # Panel A: local x'-z' cross-section.  It is explicitly schematic because
    # the 3-D y' routes are projected onto the page.
    ax = fig.add_subplot(grid[0, 0])
    ax.set_title("A  几何耦合示意（InstrumentFrame 的 x′–z′ 投影，非比例图）", loc="left", weight="bold")
    ax.add_patch(Rectangle((-45.1, -5.5), 0.8, 5.4, facecolor="#D6A43B", edgecolor="#7C5A16", lw=1.5, zorder=3))
    for center in (-4.8, -4.05, -3.3, -2.55, -1.8, -1.05, -0.3):
        ax.add_patch(Rectangle((-45.13, center - 0.23), 0.86, 0.46, facecolor="white", edgecolor="none", zorder=4))
    ax.text(-44.7, -6.05, "W-grid\n0.798 cm 深，5.4 cm 包络", ha="center", va="top", color="#6B4B13")

    tes_centers = (-38.55, -37.35, -36.15, -34.95, -33.75, -32.55)
    for layer, center in enumerate(tes_centers):
        ax.add_patch(Rectangle((center - 0.15, -4.6), 0.30, 3.6, facecolor="#B9D9EE", edgecolor="#2774AE", lw=1.0))
        ax.text(center, -2.8, str(layer), ha="center", va="center", fontsize=8, color="#154C73")
    ax.text(-35.55, -5.05, "TES L0–L5", ha="center", va="top", color="#154C73", weight="bold")
    ax.add_patch(Rectangle((-39.2, -5.25), 7.3, 4.9, fill=False, edgecolor="#A4ABB2", lw=1.2, ls="--"))

    def arrow(points: list[tuple[float, float]], color: str, label: str, label_xy: tuple[float, float], style: str = "-") -> None:
        for start, end in zip(points[:-1], points[1:]):
            ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                                         lw=2.4, color=color, linestyle=style, zorder=6))
        ax.text(*label_xy, label, color=color, fontsize=9.5, weight="bold", ha="left", va="center")

    arrow([(-50.2, 3.0), (-44.7, -1.0), (-38.6, -3.4)], "#2774AE", "前向进入网格包络", (-50.0, 2.25))
    arrow([(-50.0, -7.1), (-38.6, -3.9)], "#E29036", "前向但绕过 5.4 cm 包络", (-49.8, -7.55))
    arrow([(-29.7, -7.2), (-34.2, -4.3)], "#68727D", "后/侧向进入 TES", (-34.2, -7.6))
    arrow([(-50.0, 0.0), (-47.0, -0.9), (-38.6, -2.0)], "#9C6BB3", "少量 TES 前 Rayleigh 折线", (-49.8, 0.6), ":")

    ax.annotate("网格/TES 法线 +x′", xy=(-40.5, 1.7), xytext=(-45.0, 1.7),
                arrowprops=dict(arrowstyle="->", lw=1.8, color="#154C73"), color="#154C73", va="center")
    ax.annotate("大气竖直向下\n在本坐标中与 +x′ 相差 45°", xy=(-40.7, 0.7), xytext=(-36.8, 3.0),
                arrowprops=dict(arrowstyle="->", lw=1.5, color="#333333"), color="#333333", ha="center")
    ax.set_xlim(-51, -28.5)
    ax.set_ylim(-8.3, 4.2)
    ax.set_xlabel("局部 x′ / cm（向右为网格正面到 TES）")
    ax.set_ylabel("局部 z′ / cm")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.15, lw=0.6)

    # Panel B: actual IA polyline x grid-envelope intersection.
    ax = fig.add_subplot(grid[0, 1])
    ax.set_title("B  最终幸存事件的实际预‑TES 路径", loc="left", weight="bold")
    samples = ["全部 151", "down 60", "up 91"]
    keys = ["all", "down", "up"]
    left = [0.0, 0.0, 0.0]
    for route in ROUTE_ORDER:
        label = ROUTE_LABELS[route]
        values = [route_by_sample[key][route] for key in keys]
        bars = ax.barh(samples, values, left=left, color=ROUTE_COLORS[label], label=label, height=0.55)
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                        str(value), ha="center", va="center", color="white" if value >= 5 else "#15374D",
                        weight="bold", fontsize=9 if value >= 5 else 7)
        left = [left[index] + values[index] for index in range(3)]
    ax.invert_yaxis()
    ax.set_xlabel("选后事件数（各行分量互斥且闭合）")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=2, frameon=False, fontsize=8.7)
    ax.grid(axis="x", alpha=0.2)
    ax.text(0.99, 0.04, "所有 up 残余均绕开前网格包络", transform=ax.transAxes,
            ha="right", va="bottom", color="#4B5563", weight="bold")

    # Panel C: answer the user's vertical-incidence question directly.
    ax = fig.add_subplot(grid[1, 0])
    ax.set_title("C  ‘接近垂直’的事件占比", loc="left", weight="bold")
    labels = ["大气竖直\n|μz|≥0.8", "网格双侧法线\n|cos α|≥0.8"]
    values = [100 * atmospheric_near / 151, 100 * grid_near / 151]
    bars = ax.bar(labels, values, color=["#E29036", "#2774AE"], width=0.58)
    for bar, count, value in zip(bars, (atmospheric_near, grid_near), values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 2.0, f"{count}/151 = {value:.1f}%",
                ha="center", va="bottom", weight="bold")
    ax.axhline(50, color="#6B7280", lw=1.2, ls="--")
    ax.text(1.47, 50.8, "多数门槛", ha="right", va="bottom", color="#6B7280", fontsize=9)
    ax.set_ylim(0, 62)
    ax.set_ylabel("最终幸存事件占比 / %")
    ax.grid(axis="y", alpha=0.2)
    ax.text(0.02, 0.95, "结论：两种‘垂直’定义下都不是多数", transform=ax.transAxes,
            ha="left", va="top", weight="bold", color="#8B4D17")

    # Panel D: physical coupling mechanism (independent of the geometry split).
    ax = fig.add_subplot(grid[1, 1])
    ax.set_title("D  首次到达 TES 前的物理过程（独立分解）", loc="left", weight="bold")
    values = [direct, rayleigh_first]
    labels = ["首次物理相互作用就在 TES", "TES 前仅有弹性 Rayleigh"]
    colors = ["#2774AE", "#9C6BB3"]
    left_value = 0
    for value, label, color in zip(values, labels, colors):
        ax.barh([0], [value], left=[left_value], color=color, height=0.42, label=label)
        ax.text(left_value + value / 2, 0, f"{value}\n({100*value/151:.1f}%)", ha="center", va="center",
                color="white", weight="bold")
        left_value += value
    ax.set_xlim(0, 151)
    ax.set_ylim(-0.65, 0.65)
    ax.set_yticks([])
    ax.set_xlabel("选后事件数")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.35), frameon=False, ncol=1)
    ax.text(0.02, 0.94, "TES 前没有 Compton 或光电能损；窄线主要直接耦合。", transform=ax.transAxes,
            ha="left", va="top", weight="bold", color="#374151")
    ax.text(0.02, 0.80, "几何路径分解与本物理过程分解不可相加。", transform=ax.transAxes,
            ha="left", va="top", color="#6B7280")

    fig.suptitle("PARMA 大气 510.99895 keV：W-grid 后进入 SH3 TES 的耦合路径", fontsize=17, weight="bold")
    fig.text(0.5, 0.004,
             "N=151 个 W2 末级幸存事件；路径由 IA 折线与前网格包络求交。比例描述幸存者组成，不是所有入射光子的吸收率。",
             ha="center", va="bottom", fontsize=9, color="#4B5563")
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(output_dir / f"wgrid_tes_coupling_schematic.{suffix}", dpi=210 if suffix == "png" else None,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--transport-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    authority_root = args.authority_root.resolve()
    transport_root = args.transport_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    event_rows = load_csv(authority_root / EVENTS_REL)
    path_summary = load_json(authority_root / SUMMARY_REL)
    comparison = load_json(transport_root / COMPARE_REL)
    for relative in (CATALOG_REL, GEOMETRY_REL, PARMA_REL):
        require((transport_root / relative).is_file(), f"missing transport authority: {relative}")

    n = len(event_rows)
    require(n == 151, f"expected 151 selected events, found {n}")
    require(int(path_summary["selected_events"]) == n, "path summary count mismatch")
    weights = {float(row["base_event_weight_cps"]) for row in event_rows}
    require(len(weights) == 1, "selected events do not share one common weight")
    weight = weights.pop()
    require(math.isclose(n * weight, float(comparison["key_comparisons"]["w2_final"]["new_rate_cps"]), rel_tol=1e-12),
            "selected event rate does not close to comparison authority")

    route_all = Counter(row["actual_route_class"] for row in event_rows)
    route_down = Counter(row["actual_route_class"] for row in event_rows if row["source_hemisphere"] == "down")
    route_up = Counter(row["actual_route_class"] for row in event_rows if row["source_hemisphere"] == "up")
    expected_all = {
        "full_grid_envelope_crossing": 42,
        "partial_or_grazing_grid_envelope_contact": 2,
        "grid_facing_bypass_outside_envelope": 42,
        "rear_or_side_bypass": 65,
    }
    require(dict(route_all) == expected_all, f"unexpected full-polyline route split: {dict(route_all)}")
    require(sum(route_down.values()) == 60 and sum(route_up.values()) == 91, "hemisphere closure failed")
    require(route_down == Counter({
        "full_grid_envelope_crossing": 42,
        "partial_or_grazing_grid_envelope_contact": 2,
        "grid_facing_bypass_outside_envelope": 8,
        "rear_or_side_bypass": 8,
    }), f"down route split mismatch: {route_down}")
    require(route_up == Counter({
        "grid_facing_bypass_outside_envelope": 34,
        "rear_or_side_bypass": 57,
    }), f"up route split mismatch: {route_up}")

    atmospheric_near = sum(float(row["source_abs_mu_z"]) >= 0.8 for row in event_rows)
    atmospheric_tight = sum(float(row["source_abs_mu_z"]) >= 0.9 for row in event_rows)
    atmospheric_within30 = sum(
        min(float(row["source_theta_atmospheric_deg"]), 180.0 - float(row["source_theta_atmospheric_deg"])) <= 30.0
        for row in event_rows
    )
    atmospheric_within20 = sum(
        min(float(row["source_theta_atmospheric_deg"]), 180.0 - float(row["source_theta_atmospheric_deg"])) <= 20.0
        for row in event_rows
    )
    grid_near = sum(abs(float(row["initial_dx_local_grid_normal"])) >= 0.8 for row in event_rows)
    grid_tight = sum(abs(float(row["initial_dx_local_grid_normal"])) >= 0.9 for row in event_rows)
    grid_within10 = sum(float(row["initial_angle_to_nearest_grid_normal_deg"]) < 10.0 for row in event_rows)
    direct = sum(int(row["pre_tes_interaction_count"]) == 0 for row in event_rows)
    rayleigh_first = n - direct
    pre_processes = Counter(row["pre_tes_processes"] for row in event_rows if int(row["pre_tes_interaction_count"]) > 0)
    require(pre_processes == Counter({"RAYL": 17, "RAYL+RAYL": 3}), f"unexpected pre-TES processes: {pre_processes}")
    first_tes_process = Counter(row["first_tes_process"] for row in event_rows)
    require(first_tes_process == Counter({"PHOT": 82, "COMP": 66, "RAYL": 3}), f"first TES process mismatch: {first_tes_process}")
    hit_multiplicity = Counter(int(row["tes_hit_count"]) for row in event_rows)
    require(hit_multiplicity == Counter({1: 112, 2: 34, 3: 4, 4: 1}), f"hit multiplicity mismatch: {hit_multiplicity}")

    grid_low, grid_high = wilson95(grid_near, n)
    atmospheric_low, atmospheric_high = wilson95(atmospheric_near, n)
    require(grid_high < 0.5, "grid-near-normal Wilson upper bound unexpectedly reaches majority")

    route_rows: list[dict[str, Any]] = []
    for sample_label, sample_key, counts, total in (
        ("全部幸存", "all", route_all, n),
        ("down", "down", route_down, 60),
        ("up", "up", route_up, 91),
    ):
        for route in ROUTE_ORDER:
            count = counts[route]
            route_rows.append({
                "sample": sample_label,
                "sample_key": sample_key,
                "route": ROUTE_LABELS[route],
                "route_key": route,
                "selected_events": count,
                "within_sample_fraction": count / total,
                "rate_cps": count * weight,
            })

    angle_specs = [
        ("大气竖直", "|μz| ≥ 0.8（距任一竖直方向 ≤36.87°）", atmospheric_near),
        ("大气竖直", "|μz| ≥ 0.9（≤25.84°）", atmospheric_tight),
        ("大气竖直", "距任一竖直方向 ≤30°", atmospheric_within30),
        ("大气竖直", "距任一竖直方向 ≤20°", atmospheric_within20),
        ("网格双侧法线", "|cos α| ≥ 0.8（≤36.87°）", grid_near),
        ("网格双侧法线", "|cos α| ≥ 0.9（≤25.84°）", grid_tight),
        ("网格双侧法线", "α < 10°", grid_within10),
    ]
    angle_rows: list[dict[str, Any]] = []
    for axis, definition, count in angle_specs:
        low, high = wilson95(count, n)
        angle_rows.append({
            "axis": axis,
            "definition": definition,
            "selected_events": count,
            "selected_fraction": count / n,
            "wilson95_low": low,
            "wilson95_high": high,
            "majority": "否" if high < 0.5 else "未排除",
        })
    angle_wide_rows = [angle_rows[0], angle_rows[4]]

    mechanism_rows = [
        {"mechanism": "首次物理相互作用就在 TES", "selected_events": direct, "selected_fraction": direct / n,
         "interpretation": "直接/未在 TES 前发生可记录相互作用"},
        {"mechanism": "TES 前仅有 Rayleigh", "selected_events": rayleigh_first, "selected_fraction": rayleigh_first / n,
         "interpretation": "17 条一次、3 条两次；无 TES 前 Compton/光电能损"},
    ]
    process_rows = [
        {"process": process, "selected_events": first_tes_process[process], "selected_fraction": first_tes_process[process] / n}
        for process in ("PHOT", "COMP", "RAYL")
    ]

    compare_w2 = comparison["key_comparisons"]["w2_final"]
    down_authority = comparison["direction_aggregates"]["down"]
    up_authority = comparison["direction_aggregates"]["up"]
    hemisphere_rows = [
        {
            "hemisphere": label,
            "parma_flux_ph_cm2_s": float(authority["parma_line_flux_ph_cm2_s"]),
            "parma_flux_share": float(authority["parma_line_flux_ph_cm2_s"]) / float(comparison["parma_day15_full_space_flux_ph_cm2_s"]),
            "selected_events": int(authority["new_selected_events"]),
            "selected_residual_share": int(authority["new_selected_events"]) / n,
            "wgrid_over_open_ratio": float(authority["new_over_old_ratio"]),
            "suppression_fraction": float(authority["suppression_fraction"]),
            "difference_z": float(authority["difference_z"]),
        }
        for label, authority in (("down", down_authority), ("up", up_authority))
    ]

    headline = [{
        "vertical_verdict": "不是",
        "vertical_context": f"大气竖直近锥仅 {atmospheric_near}/151",
        "grid_normal_share": f"{100*grid_near/n:.1f}%",
        "grid_normal_context": "95% Wilson 上限仍 <50%",
        "bypass_share": f"{n - route_all['full_grid_envelope_crossing'] - route_all['partial_or_grazing_grid_envelope_contact']}/151",
        "bypass_context": "实际预‑TES 折线路径绕开前网格包络",
        "direct_share": f"{100*direct/n:.1f}%",
        "direct_context": "首次物理相互作用就在 TES",
    }]

    route_by_sample = {"all": route_all, "down": route_down, "up": route_up}
    make_schematic(output_dir, route_by_sample, atmospheric_near, grid_near, direct, rayleigh_first)

    write_csv(output_dir / "actual_pre_tes_route_composition.csv", route_rows)
    write_csv(output_dir / "incidence_angle_summary.csv", angle_rows)
    write_csv(output_dir / "physical_coupling_summary.csv", mechanism_rows)
    write_csv(output_dir / "first_tes_process_summary.csv", process_rows)
    write_csv(output_dir / "hemisphere_coupling_summary.csv", hemisphere_rows)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary = {
        "status": "PASS__WGRID_TES_ENTRY_COUPLING_CLOSED_FROM_EXISTING_TRANSPORT",
        "generated_at": generated_at,
        "line_source": {
            "provider": "PARMA dedicated atmospheric line parameterization",
            "energy_keV": float(comparison["line_energy_keV"]),
            "day15_full_space_flux_ph_cm2_s": float(comparison["parma_day15_full_space_flux_ph_cm2_s"]),
            "angular_components": 80,
        },
        "selected": {"events": n, "common_weight_cps": weight, "rate_cps": n * weight},
        "answer": {
            "mostly_atmospheric_vertical": False,
            "atmospheric_near_vertical_abs_mu_ge_0p8": {"count": atmospheric_near, "fraction": atmospheric_near / n, "wilson95": [atmospheric_low, atmospheric_high]},
            "mostly_grid_normal": False,
            "grid_near_normal_abs_cos_ge_0p8": {"count": grid_near, "fraction": grid_near / n, "wilson95": [grid_low, grid_high]},
            "actual_routes": dict(route_all),
            "bypass_front_grid_envelope": {"count": 107, "fraction": 107 / n},
            "first_interaction_in_tes": {"count": direct, "fraction": direct / n},
            "pre_tes_rayleigh_only": {"count": rayleigh_first, "fraction": rayleigh_first / n},
        },
        "response_context": {
            "wgrid_over_open_ratio": float(compare_w2["new_over_old_ratio"]),
            "ratio_sigma": float(compare_w2["independent_ratio_sigma"]),
            "suppression_fraction": float(compare_w2["suppression_fraction"]),
            "difference_z": float(compare_w2["difference_z"]),
        },
        "geometry": {
            "instrument_frame_rotation_y_deg": 45.0,
            "grid_normal_world": [math.sqrt(0.5), 0.0, -math.sqrt(0.5)],
            "grid_envelope_local_cm": {"x": [-45.1, -44.3], "y": [-2.7, 2.7], "z": [-5.5, -0.1]},
            "grid_to_first_tes_layer_center_cm": 6.15,
            "grid_depth_cm": 0.798,
        },
        "limitations": [
            "The route fractions describe final W2-selected survivors and are not incident-photon absorption probabilities.",
            "Cosima SIM does not record passive-volume boundary crossings; grid-envelope contact is reconstructed by IA-polyline/AABB intersection.",
            "Envelope contact cannot distinguish a vacuum-hole path from transmission through a thin W web without a recorded interaction.",
            "The open and W-grid runs use independent seeds, so no event-by-event absorption pairing exists.",
        ],
        "sources": {"events": EVENTS_REL, "catalog": CATALOG_REL, "comparison": COMPARE_REL, "parma": PARMA_REL, "geometry": GEOMETRY_REL},
    }
    with (output_dir / "entry_coupling_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    datasets = build_sqlite_snapshot(output_dir / "entry_coupling.sqlite", {
        "headline": headline,
        "route_composition": route_rows,
        "angle_summary": angle_rows,
        "angle_wide_cone": angle_wide_rows,
        "mechanism_summary": mechanism_rows,
        "first_tes_process": process_rows,
        "hemisphere_summary": hemisphere_rows,
    })
    descriptions = {
        "headline": "从 151 个 W2 末级幸存事件提取的四项标题结论。",
        "route_composition": "逐事件 IA 折线与完整 W-grid 包络求交后的互斥路径类别。",
        "angle_summary": "相对 global 大气竖直轴和 local W-grid/TES 法线的入射角宽锥计数。",
        "angle_wide_cone": "对两个参考轴采用共同 |cos|≥0.8 阈值的可比宽锥计数。",
        "mechanism_summary": "首次 TES 相互作用前的物理过程互斥分解。",
        "first_tes_process": "151 个事件在 TES 内的首次物理过程。",
        "hemisphere_summary": "PARMA 80 个等 μ 分量的 down/up 通量与选后响应。",
    }
    metric_definitions = {
        "headline": ["All displayed values come from entry_coupling_summary.json."],
        "route_composition": ["Actual route uses the IA INIT -> pre-TES IA -> first TES IA polyline intersected with the grid AABB."],
        "angle_summary": ["Atmospheric vertical uses |global dz|; grid normal uses |local dx|.", "Wilson95 is a binomial interval over the 151 selected survivors."],
        "angle_wide_cone": ["Both rows use the same absolute direction-cosine threshold 0.8 (36.87 degrees)."],
        "mechanism_summary": ["Direct means no recorded physical IA between INIT and the first TES IA."],
        "first_tes_process": ["PHOT, COMP, and RAYL are the process labels in the first IA geometrically inside a TES layer."],
        "hemisphere_summary": ["Suppression compares independent W-grid and open-SH3 transports with matched source normalization."],
    }
    dataset_sources = []
    for dataset_name in datasets:
        dataset_sources.append({
            "id": f"source_{dataset_name}",
            "label": descriptions[dataset_name],
            "path": f"{OUT_REL}/entry_coupling.sqlite",
            "query": {
                "engine": "sqlite3",
                "language": "sql",
                "sql": f'SELECT * FROM "{dataset_name}" ORDER BY _row_order',
                "description": descriptions[dataset_name],
                "executed_at": generated_at,
                "tables_used": [dataset_name],
                "filters": ["Final W2 selection only", "No sampling or truncation"],
                "metric_definitions": metric_definitions[dataset_name],
            },
        })
    main_source = {"id": "entry_coupling_bundle", "label": "W-grid 后大气 511 keV 进入 TES 的逐事件路径闭合", "path": f"{OUT_REL}/entry_coupling_summary.json"}

    blocks = [
        {"id": "title", "type": "markdown", "body": "# W-grid 后大气 511 keV 如何耦合进入 SH3 TES"},
        {"id": "technical_summary", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "## 技术结论\n\n"
            "**不是大多沿大气竖直方向入射，也不是大多垂直网络板。** 在 151 个 W2 末级幸存事件中，只有 21 个（13.91%）位于大气竖直轴两侧的 36.87° 锥内；相对网格双侧法线，57 个（37.75%）位于同样宽的锥内。两者都低于多数，且网格法线比例的 95% Wilson 上限为 45.69%，仍小于 50%。\n\n"
            "实际 IA 折线显示，42 个完整跨越前网格包络、2 个部分或掠过；其余 107 个绕开这个 5.4 cm 前向包络，其中 42 个朝前但从边外进入，65 个从后方或侧方进入。全部 91 个 up 残余都绕开前网格。"
        )},
        {"id": "headline_strip", "type": "metric-strip", "cardIds": ["card_vertical", "card_grid", "card_bypass", "card_direct"]},
        {"id": "route_heading", "type": "markdown", "body": "## 几何路径：前网格只控制有限孔径，不是 4π 准直器"},
        {"id": "route_chart", "type": "chart", "chartId": "route_split"},
        {"id": "route_text", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "InstrumentFrame 绕 global y 轴旋转 45°，因此网格/TES 的 local +x′ 法线在世界坐标中是约 (+0.707, 0, −0.707)：**网格正入射本身就不是大气竖直，而是相差 45°。** "
            "网格中心至 TES L0 中心约 6.15 cm，网格厚 0.798 cm、横向包络仅 5.4×5.4 cm；它只能约束一侧前孔径。down 的 60 个残余可拆成 42 完整跨越、2 掠过、8 前向绕边、8 后/侧绕行；up 的 91 个全部绕行。"
        )},
        {"id": "angle_heading", "type": "markdown", "body": "## 入射角：两种‘垂直’都不是多数"},
        {"id": "angle_chart", "type": "chart", "chartId": "near_axis_fraction"},
        {"id": "angle_table", "type": "table", "tableId": "angle_detail"},
        {"id": "mechanism_heading", "type": "markdown", "body": "## 物理过程：窄线主要直接到达 TES"},
        {"id": "mechanism_chart", "type": "chart", "chartId": "mechanism_split"},
        {"id": "mechanism_text", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "131/151（86.75%）的初级 511 keV 光子在 TES 前没有任何可记录的物理相互作用，首次相互作用就在 TES。其余 20 个在 TES 前只有弹性 Rayleigh（17 个一次、3 个两次）；没有 TES 前 Compton 或光电能损。"
            "TES 内首次过程合计为 82 次光电、66 次 Compton、3 次 Rayleigh。因此残余线项主要是直接或近直接的远场光子耦合，不是前网格诱发的活化或能损级联。"
        )},
        {"id": "response_context", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "## 为什么加网格后仍保留大量 511 keV\n\n"
            f"共同 PARMA 510.99895 keV 源和共同选择下，W-grid/open-SH3 末级率比为 {float(compare_w2['new_over_old_ratio']):.4f}±{float(compare_w2['independent_ratio_sigma']):.4f}，中心值抑制 {100*float(compare_w2['suppression_fraction']):.2f}%，差值为 {float(compare_w2['difference_z']):.2f}σ。"
            "逐事件路径说明了这个有限抑制的几何原因：前网格没有覆盖多数幸存路径，尤其没有覆盖任何 up 残余。路径组成与独立 open run 不能逐事件配对，所以不能把 42/2/42/65 直接解释成全体入射的吸收概率。"
        )},
        {"id": "hemisphere_table", "type": "table", "tableId": "hemisphere_detail"},
        {"id": "scope", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "## 数据、坐标与方法\n\n"
            "数值源严格为同一 day-15 大气状态下的 PARMA 专用线参数化：510.99895 keV、全空间通量 0.16651547160226118 ph cm⁻² s⁻¹、80 个等 μ 分量。这里没有使用 Mahoney/Harris 文献数值归一。"
            "逐事件源方向来自原始 SIM 的 IA INIT；TES 前相互作用位置来自后续 IA；路径按 INIT→预‑TES IA→首次 TES IA 的折线与网格 AABB x′=[−45.1,−44.3] cm、y′=[−2.7,2.7] cm、z′=[−5.5,−0.1] cm 求交。大气竖直用 |global dz|，网格法线用 |local dx′|。"
        )},
        {"id": "limitations", "type": "markdown", "sourceId": "entry_coupling_bundle", "body": (
            "## 局限性与稳健性\n\n"
            "- 比例是 **W-grid 最终幸存者组成**，存在 survivor bias；不能当作所有入射光子的透射率或吸收率。\n"
            "- SIM 没有被动体边界 crossing/step 日志；‘进入网格包络’是 IA 折线与几何盒求交。无相互作用的穿越者不能进一步区分真空孔道和穿过薄 W 筋但未相互作用。\n"
            "- open 与 W-grid 使用独立随机种子，不能对事件做一一去向配对。\n"
            "- 151 个等权选后事件给出总线率 8.14% MC 相对误差；宽锥比例用 Wilson 区间。路径结论对‘大多垂直’已足够，因为网格法线宽锥的 95% 上限仍低于 50%。"
        )},
        {"id": "next_steps", "type": "markdown", "body": (
            "## 建议的最小后续验证\n\n"
            "若设计目标是继续压低该线项，优先补的是覆盖侧/后向和 up 半球的被动/主动视场控制，而不是只继续缩小当前前网格孔。若需要把各绕行口的贡献分解到具体开口，应在不改变现有物理选择的前提下增加边界 crossing 或进入面 tally；现有 SIM 仅能可靠闭合到包络级。"
        )},
        {"id": "questions", "type": "markdown", "body": (
            "## 尚待回答的问题\n\n"
            "- 侧向、后向和 up 半球中，哪一个具体结构开口贡献最大？\n"
            "- 若封闭这些路径，信号视场和有效面积会损失多少？这需要与信号响应一起评估，不能只看本底线率。"
        )},
    ]

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "W-grid 后大气 511 keV 如何耦合进入 SH3 TES",
            "description": "用既有输运的逐事件 IA 折线、角方向和共同响应结果闭合前网格后的残余单能路径。",
            "generatedAt": generated_at,
            "sources": [main_source, *dataset_sources],
            "cards": [
                {"id": "card_vertical", "dataset": "headline", "sourceId": "source_headline", "description": "|global dz|≥0.8。", "metrics": [{"label": "大多大气竖直？", "field": "vertical_verdict"}, {"label": "证据", "field": "vertical_context"}]},
                {"id": "card_grid", "dataset": "headline", "sourceId": "source_headline", "description": "|local dx′|≥0.8。", "metrics": [{"label": "接近网格法线", "field": "grid_normal_share"}, {"label": "多数检验", "field": "grid_normal_context"}]},
                {"id": "card_bypass", "dataset": "headline", "sourceId": "source_headline", "description": "完整 IA 折线与网格包络求交。", "metrics": [{"label": "绕开前网格", "field": "bypass_share"}, {"label": "路径", "field": "bypass_context"}]},
                {"id": "card_direct", "dataset": "headline", "sourceId": "source_headline", "description": "INIT 后首个物理 IA 位于 TES。", "metrics": [{"label": "直接耦合", "field": "direct_share"}, {"label": "机制", "field": "direct_context"}]},
            ],
            "charts": [
                {
                    "id": "route_split", "title": "实际预‑TES 路径组成", "subtitle": "IA 折线 × 完整 W-grid 包络；事件数", "showDescription": True,
                    "intent": "composition", "question": "残余事件是穿过前网格还是从其他方向绕入？", "rationale": "down/up 的堆叠计数直接显示前网格覆盖边界。",
                    "comparisonContext": {"grain": "source hemisphere", "unit": "selected events", "denominator": "events within each displayed sample"},
                    "type": "stackedBar", "dataset": "route_composition", "sourceId": "source_route_composition",
                    "encodings": {
                        "x": {"field": "sample", "type": "nominal", "label": "样本"},
                        "y": {"field": "selected_events", "type": "quantitative", "aggregate": "sum", "label": "选后事件数", "unit": "events"},
                        "color": {"field": "route", "type": "nominal", "label": "路径"},
                        "tooltip": [{"field": "route", "type": "text", "label": "路径"}, {"field": "selected_events", "type": "quantitative", "label": "事件数"}, {"field": "within_sample_fraction", "type": "quantitative", "format": "percent", "label": "行内占比"}],
                    },
                    "xAxisTitle": "样本", "yAxisTitle": "选后事件数", "palette": {"kind": "categorical"}, "unit": "events", "layout": "full", "maxRows": 20,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                },
                {
                    "id": "near_axis_fraction", "title": "相对大气竖直轴与网格法线的近锥占比", "subtitle": "共同宽锥阈值 0.8；36.87°，N=151", "showDescription": True,
                    "intent": "comparison", "question": "残余事件大多垂直吗？", "rationale": "相同余弦阈值可直接比较两个物理轴。",
                    "comparisonContext": {"grain": "axis definition", "unit": "fraction", "denominator": "151 selected survivors"},
                    "type": "bar", "dataset": "angle_wide_cone", "sourceId": "source_angle_wide_cone",
                    "encodings": {
                        "x": {"field": "axis", "type": "nominal", "label": "参考轴"},
                        "y": {"field": "selected_fraction", "type": "quantitative", "label": "选后占比", "unit": "fraction"},
                        "color": {"field": "axis", "type": "nominal", "label": "参考轴"},
                        "tooltip": [{"field": "selected_events", "type": "quantitative", "label": "事件数"}, {"field": "selected_fraction", "type": "quantitative", "format": "percent", "label": "占比"}, {"field": "wilson95_high", "type": "quantitative", "format": "percent", "label": "95%上限"}],
                    },
                    "xAxisTitle": "参考轴", "yAxisTitle": "选后占比", "palette": {"kind": "categorical"}, "valueFormat": "percent", "unit": "fraction", "layout": "full", "maxRows": 10,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                },
                {
                    "id": "mechanism_split", "title": "首次到达 TES 前的物理过程", "subtitle": "与几何路径分解独立；N=151", "showDescription": True,
                    "intent": "composition", "question": "511 keV 线是直接到 TES，还是先在周围结构发生能损？", "rationale": "互斥计数直接区分直接耦合和 TES 前弹性散射。",
                    "comparisonContext": {"grain": "pre-TES process class", "unit": "selected events", "denominator": "151 selected survivors"},
                    "type": "bar", "dataset": "mechanism_summary", "sourceId": "source_mechanism_summary",
                    "encodings": {
                        "x": {"field": "mechanism", "type": "nominal", "label": "机制"},
                        "y": {"field": "selected_events", "type": "quantitative", "label": "选后事件数", "unit": "events"},
                        "color": {"field": "mechanism", "type": "nominal", "label": "机制"},
                        "tooltip": [{"field": "selected_events", "type": "quantitative", "label": "事件数"}, {"field": "selected_fraction", "type": "quantitative", "format": "percent", "label": "占比"}, {"field": "interpretation", "type": "text", "label": "解释"}],
                    },
                    "xAxisTitle": "机制", "yAxisTitle": "选后事件数", "palette": {"kind": "categorical"}, "unit": "events", "layout": "full", "maxRows": 10,
                    "surface": {"surface": "export", "showControls": False, "viewMode": "both"},
                },
            ],
            "tables": [
                {
                    "id": "angle_detail", "title": "入射角阈值与多数检验", "subtitle": "大气竖直与网格法线是不同轴；N=151", "showDescription": True,
                    "dataset": "angle_summary", "defaultSort": {"field": "axis", "direction": "asc"}, "density": "dense", "sourceId": "source_angle_summary", "layout": "full",
                    "columns": [{"field": "axis", "label": "参考轴", "type": "text"}, {"field": "definition", "label": "定义", "type": "text"}, {"field": "selected_events", "label": "事件数", "format": "number"}, {"field": "selected_fraction", "label": "占比", "format": "percent"}, {"field": "wilson95_low", "label": "95%低", "format": "percent"}, {"field": "wilson95_high", "label": "95%高", "format": "percent"}, {"field": "majority", "label": "可称多数？", "type": "text"}],
                },
                {
                    "id": "hemisphere_detail", "title": "PARMA 半球通量与 W-grid 残余", "subtitle": "共同 80 等 μ 源；W-grid/open 为独立种子率比", "showDescription": True,
                    "dataset": "hemisphere_summary", "defaultSort": {"field": "hemisphere", "direction": "asc"}, "density": "dense", "sourceId": "source_hemisphere_summary", "layout": "full",
                    "columns": [{"field": "hemisphere", "label": "半球", "type": "text"}, {"field": "parma_flux_ph_cm2_s", "label": "PARMA 通量", "format": "number"}, {"field": "parma_flux_share", "label": "源通量占比", "format": "percent"}, {"field": "selected_events", "label": "W-grid选后数", "format": "number"}, {"field": "selected_residual_share", "label": "残余占比", "format": "percent"}, {"field": "wgrid_over_open_ratio", "label": "W-grid/open", "format": "number"}, {"field": "suppression_fraction", "label": "抑制中心值", "format": "percent"}, {"field": "difference_z", "label": "差值 z", "format": "number"}],
                },
            ],
            "blocks": blocks,
        },
        "snapshot": {"version": 1, "generatedAt": generated_at, "status": "ready", "datasets": datasets},
        "sources": [main_source, *dataset_sources],
    }
    with (output_dir / "artifact.json").open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    receipt = {
        "status": "PASS__ENTRY_COUPLING_REPORT_BUNDLE_BUILT",
        "generated_at": generated_at,
        "authority_root": str(authority_root),
        "transport_root": str(transport_root),
        "output_dir": str(output_dir),
        "checks": {
            "selected_events": n,
            "actual_route_closure": sum(route_all.values()),
            "physical_mechanism_closure": direct + rayleigh_first,
            "common_weight_rate_closure_cps": n * weight,
            "grid_near_normal_wilson95_upper_below_half": grid_high < 0.5,
        },
        "outputs": [
            "entry_coupling_summary.json", "actual_pre_tes_route_composition.csv", "incidence_angle_summary.csv",
            "physical_coupling_summary.csv", "first_tes_process_summary.csv", "hemisphere_coupling_summary.csv",
            "entry_coupling.sqlite", "artifact.json", "wgrid_tes_coupling_schematic.png",
            "wgrid_tes_coupling_schematic.svg", "wgrid_tes_coupling_schematic.pdf",
        ],
    }
    with (output_dir / "report_bundle_receipt.json").open("w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": receipt["status"], "vertical": False, "actual_routes": dict(route_all), "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
