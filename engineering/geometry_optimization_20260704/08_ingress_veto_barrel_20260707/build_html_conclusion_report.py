#!/usr/bin/env python3
"""Build a self-contained HTML conclusion report for the ingress/veto branch."""

from __future__ import annotations

import base64
import csv
import gzip
import html
import importlib.util
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OUT = WORK / "html_conclusion_report_20260707"
CHART_DIR = OUT / "charts"
DATA_DIR = OUT / "data"

SLOW_SCRIPT = WORK / "build_ingress_veto_audit.py"
INGRESS_JSON = WORK / "ingress_summary.json"
VETO_JSON = WORK / "veto_efficiency_summary.json"
BARREL_JSON = WORK / "barrel_eplus_2M_summary.json"
GEOM_MANIFEST = WORK / "barrel_hypothesis_geometry_manifest.json"
ATM511_JSON = (
    ROOT
    / "engineering/geometry_optimization_20260704/06_atm511_replay_20260707"
    / "p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json"
)
REVIEW_FINAL = (
    ROOT
    / "engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review"
    / "REVIEW_FINAL.md"
)
GEOMETRY_2D = WORK / "figures/hyp_barrel_w_tes_csi_2d_detail.png"

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
NEUTRAL = {
    "xlight": "#F4F5F7",
    "light": "#E2E5EA",
    "base": "#C5CAD3",
    "mid": "#7A828F",
    "dark": "#464C55",
}
COLORS = {
    "blue": {"xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}

FAMILY_LABEL = {"eplus": "e+", "n": "n", "atm511": "atm511"}
STAGE_LABELS = ["Raw TES window", "Active pass", "Final pass"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_helpers():
    spec = importlib.util.spec_from_file_location("report_ingress_helpers", SLOW_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SLOW_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_chart_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.grid": True,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "text.color": TOKENS["ink"],
            "axes.titlecolor": TOKENS["ink"],
        }
    )


def add_chart_header(fig: Any, ax: Any, title: str, subtitle: str) -> None:
    ax.set_title("")
    fig.subplots_adjust(top=0.82)
    left = ax.get_position().x0
    fig.text(left, 0.975, title, ha="left", va="top", fontsize=13, fontweight="semibold", color=TOKENS["ink"])
    fig.text(left, 0.925, subtitle, ha="left", va="top", fontsize=9, color=TOKENS["muted"])
    for spine in ["top", "right"]:
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)


def savefig(fig: Any, name: str) -> Path:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / f"{name}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=TOKENS["surface"])
    plt.close(fig)
    return path


def img_data_uri(path: Path) -> str:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def html_escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{100.0 * float(value):.1f}%"


def rate(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.6g}"


def family_sort_key(row: dict[str, Any]) -> int:
    return {"eplus": 0, "n": 1, "atm511": 2}.get(str(row.get("family")), 99)


def extract_sector(region: str | None) -> int | None:
    if not region:
        return None
    match = re.search(r"phi(\d+)_", str(region))
    if not match:
        return None
    return int(match.group(1)) % 8


def collect_prompt_first_hit_metadata(event_rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    helpers = load_helpers()
    targets_by_file: dict[str, set[int]] = defaultdict(set)
    for row in event_rows:
        if row["family"] not in ("eplus", "n"):
            continue
        targets_by_file[str(ROOT / row["source_file"])].add(int(row["local_id"]))
    return helpers.collect_selected_event_metadata(targets_by_file)


def stage_counts_from_veto(veto: dict[str, Any]) -> list[dict[str, Any]]:
    def first_present(row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        raise KeyError(keys[0])

    rows = []
    for row in sorted(veto["summaries"], key=family_sort_key):
        rows.append(
            {
                "family": row["family"],
                "raw": int(row["raw_events"]),
                "active": int(row["active_veto_pass_events"]),
                "final": int(row["side_compton_fov_pass_events"]),
                "active_rejection": float(first_present(row, "active_veto_rejection_fraction_vs_raw_rate", "active_veto_rejection_fraction_vs_raw_count")),
                "compton_rejection": float(first_present(row, "side_compton_fov_rejection_fraction_vs_active_rate", "side_compton_fov_rejection_fraction_vs_active_count")),
                "final_survival": float(first_present(row, "final_survival_fraction_vs_raw_rate", "final_survival_fraction_vs_raw_count")),
            }
        )
    return rows


def final_rows_by_family(event_rows: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    return [
        r
        for r in event_rows
        if r.get("family") == family and r.get("window") == "w2_510p58_511p42" and bool(r.get("stage_side_compton_fov_pass"))
    ]


def chart_veto_stage_counts(stage_rows: list[dict[str, Any]]) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    families = [FAMILY_LABEL[r["family"]] for r in stage_rows]
    x = np.arange(len(families))
    width = 0.23
    values = [
        [r["raw"] for r in stage_rows],
        [r["active"] for r in stage_rows],
        [r["final"] for r in stage_rows],
    ]
    colors = [COLORS["blue"]["base"], COLORS["gold"]["base"], COLORS["olive"]["base"]]
    edges = [COLORS["blue"]["dark"], COLORS["gold"]["dark"], COLORS["olive"]["dark"]]
    for i, label in enumerate(STAGE_LABELS):
        bars = ax.bar(x + (i - 1) * width, values[i], width=width, label=label, color=colors[i], edgecolor=edges[i], linewidth=1.0)
        for bar, val in zip(bars, values[i]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.2, str(val), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, families)
    ax.set_ylabel("Events")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.set_ylim(0, max(max(v) for v in values) * 1.18)
    add_chart_header(fig, ax, "W2 veto cutflow by source family", "Counts in the 510.58-511.42 keV TES window; final means active-pass plus side Compton/FoV pass.")
    return savefig(fig, "veto_cutflow_w2")


def chart_rejection_fraction(stage_rows: list[dict[str, Any]]) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    families = [FAMILY_LABEL[r["family"]] for r in stage_rows]
    x = np.arange(len(families))
    width = 0.28
    active = [100 * r["active_rejection"] for r in stage_rows]
    compton = [100 * r["compton_rejection"] for r in stage_rows]
    b1 = ax.bar(x - width / 2, active, width=width, label="Active veto rejection", color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"])
    b2 = ax.bar(x + width / 2, compton, width=width, label="Compton/FoV rejection vs active", color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.2, f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, families)
    ax.set_ylabel("Rejected fraction")
    ax.set_ylim(0, 88)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    add_chart_header(fig, ax, "Active veto and Compton/FoV rejection are doing different jobs", "Active veto dominates neutron rejection; atmospheric 511 is only reduced by the Compton/FoV stage in this replay.")
    return savefig(fig, "veto_rejection_fraction")


def chart_entry_surface(event_rows: list[dict[str, Any]]) -> Path:
    families = ["eplus", "n", "atm511"]
    surfaces = ["side", "top", "bottom", "miss_current_outer_envelope", "other"]
    color_map = {
        "side": COLORS["blue"]["base"],
        "top": COLORS["gold"]["base"],
        "bottom": COLORS["olive"]["base"],
        "miss_current_outer_envelope": COLORS["orange"]["base"],
        "other": NEUTRAL["light"],
    }
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    y = np.arange(len(families))
    left = np.zeros(len(families))
    for surf in surfaces:
        vals = []
        for fam in families:
            rows = final_rows_by_family(event_rows, fam)
            total = max(1, len(rows))
            count = sum(1 for r in rows if (r.get("entry_surface_proxy") or "other") == surf)
            vals.append(count / total * 100.0)
        ax.barh(y, vals, left=left, color=color_map[surf], edgecolor=TOKENS["ink"], linewidth=0.6, label=surf.replace("miss_current_outer_envelope", "proxy miss"))
        left += np.asarray(vals)
    ax.set_yticks(y, [FAMILY_LABEL[f] for f in families])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of final W2 candidates")
    ax.xaxis.set_major_formatter(lambda v, pos: f"{v:.0f}%")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, ncol=3, fontsize=8, borderaxespad=0)
    add_chart_header(fig, ax, "Final W2 entry proxies differ by source", "Atmospheric 511 final candidates are mostly side-entry; e+ and n are low-stat and more diffuse.")
    return savefig(fig, "final_entry_surface_share")


def chart_direction_polar(event_rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.5), subplot_kw={"projection": "polar"})
    families = ["eplus", "n"]
    colors = [COLORS["orange"], COLORS["blue"]]
    theta = np.deg2rad(np.arange(0, 360, 45))
    width = np.deg2rad(38)
    for ax, fam, family_color in zip(axes, families, colors):
        counts = [0] * 8
        rows = final_rows_by_family(event_rows, fam)
        for row in rows:
            sector = extract_sector(row.get("entry_region_proxy"))
            if sector is not None:
                counts[sector] += 1
        ax.bar(theta, counts, width=width, color=family_color["base"], edgecolor=family_color["dark"], linewidth=1.0)
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(1)
        ax.set_title(f"{FAMILY_LABEL[fam]} final W2 sectors", fontsize=10, pad=14)
        ax.set_xticks(theta, [f"{i*45}°" for i in range(8)], fontsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(color=TOKENS["grid"], linewidth=0.8)
    fig.text(0.06, 0.98, "Positron and neutron final-candidate ingress directions", ha="left", va="top", fontsize=13, fontweight="semibold")
    fig.text(0.06, 0.925, "Counts by 45° local azimuth sector from the IA-INIT envelope-entry proxy; sample sizes are 35 e+ and 13 n final W2 candidates.", ha="left", va="top", fontsize=9, color=TOKENS["muted"])
    fig.subplots_adjust(top=0.78, wspace=0.32)
    return savefig(fig, "eplus_neutron_direction_polar")


def build_depth_records(event_rows: list[dict[str, Any]], metadata: dict[tuple[str, int], dict[str, Any]]) -> list[dict[str, Any]]:
    helpers = load_helpers()
    rows = []
    for row in event_rows:
        if row.get("family") != "n":
            continue
        key = (rel(ROOT / row["source_file"]), int(row["local_id"]))
        meta = metadata.get(key, {})
        required = [
            row.get("entry_local_x_cm"),
            row.get("entry_local_y_cm"),
            row.get("entry_local_z_cm"),
            row.get("dir_x"),
            row.get("dir_y"),
            row.get("dir_z"),
            row.get("init_energy_keV"),
            meta.get("first_hit_x_cm"),
            meta.get("first_hit_y_cm"),
            meta.get("first_hit_z_cm"),
        ]
        if any(v is None for v in required):
            rows.append(
                {
                    "local_id": row["local_id"],
                    "status": "missing coordinate",
                    "init_energy_keV": row.get("init_energy_keV"),
                    "depth_projection_cm": None,
                    "depth_distance_cm": None,
                    "first_hit_category": meta.get("first_hit_category"),
                    "first_hit_volume": meta.get("first_hit_volume"),
                    "plotted": False,
                }
            )
            continue
        entry = np.asarray([row["entry_local_x_cm"], row["entry_local_y_cm"], row["entry_local_z_cm"]], dtype=float)
        first_world = np.asarray([meta["first_hit_x_cm"], meta["first_hit_y_cm"], meta["first_hit_z_cm"]], dtype=float)
        first_local = helpers.rotate_y(first_world, -45.0)
        dir_local = helpers.rotate_y((row["dir_x"], row["dir_y"], row["dir_z"]), -45.0)
        norm = float(np.linalg.norm(dir_local))
        if norm <= 0:
            continue
        dir_local = dir_local / norm
        projection = float(np.dot(first_local - entry, dir_local))
        distance = float(np.linalg.norm(first_local - entry))
        if row.get("stage_side_compton_fov_pass"):
            status = "final pass"
        elif row.get("stage_active_veto_pass"):
            status = "active pass, Compton/FoV veto"
        else:
            status = "active veto reject"
        rows.append(
            {
                "local_id": row["local_id"],
                "status": status,
                "init_energy_keV": row.get("init_energy_keV"),
                "depth_projection_cm": projection,
                "depth_distance_cm": distance,
                "first_hit_category": meta.get("first_hit_category"),
                "first_hit_volume": meta.get("first_hit_volume"),
                "plotted": projection >= 0,
            }
        )
    return rows


def chart_neutron_energy_depth(depth_rows: list[dict[str, Any]]) -> Path:
    plot_rows = [r for r in depth_rows if r.get("plotted") and r.get("init_energy_keV") is not None]
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    color_by_status = {
        "active veto reject": COLORS["orange"]["base"],
        "active pass, Compton/FoV veto": COLORS["gold"]["base"],
        "final pass": COLORS["blue"]["base"],
    }
    edge_by_status = {
        "active veto reject": COLORS["orange"]["dark"],
        "active pass, Compton/FoV veto": COLORS["gold"]["dark"],
        "final pass": COLORS["blue"]["dark"],
    }
    for status in ["active veto reject", "active pass, Compton/FoV veto", "final pass"]:
        xs = [max(1e-3, float(r["init_energy_keV"])) for r in plot_rows if r["status"] == status]
        ys = [float(r["depth_projection_cm"]) for r in plot_rows if r["status"] == status]
        if xs:
            ax.scatter(xs, ys, s=42, color=color_by_status[status], edgecolor=edge_by_status[status], linewidth=0.8, label=status, alpha=0.86)
    ax.set_xscale("log")
    ax.set_xlabel("Initial neutron energy (keV, log scale)")
    ax.set_ylabel("First-hit depth proxy (cm)")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.axhline(0, color=NEUTRAL["dark"], linewidth=0.8)
    add_chart_header(fig, ax, "Neutron energy versus first-hit depth proxy", "W2 raw neutron candidates with usable coordinates; depth is the projected distance from the envelope-entry proxy to first recorded hit.")
    return savefig(fig, "neutron_energy_depth")


def chart_first_hit_categories(event_rows: list[dict[str, Any]]) -> Path:
    families = ["eplus", "n"]
    counters = {fam: Counter(r.get("first_hit_category") or "unknown" for r in final_rows_by_family(event_rows, fam)) for fam in families}
    categories = [c for c, _ in (counters["eplus"] + counters["n"]).most_common(8)]
    y = np.arange(len(categories))
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    width = 0.34
    e_vals = [counters["eplus"].get(c, 0) for c in categories]
    n_vals = [counters["n"].get(c, 0) for c in categories]
    ax.barh(y - width / 2, e_vals, height=width, color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"], label="e+ final")
    ax.barh(y + width / 2, n_vals, height=width, color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"], label="n final")
    ax.set_yticks(y, categories)
    ax.invert_yaxis()
    ax.set_xlabel("Final W2 events")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    add_chart_header(fig, ax, "First recorded volume class explains what the veto sees", "Current-geometry final W2 candidates; categories are parsed from the first recorded hit volume.")
    return savefig(fig, "first_hit_categories_final")


def chart_barrel_limit(stage_rows: list[dict[str, Any]], barrel: dict[str, Any]) -> Path:
    eplus = next(r for r in stage_rows if r["family"] == "eplus")
    barrel_w2 = next(r for r in barrel["rows"] if r["window"] == "w2_510p58_511p42")
    rows = [
        ("Current e+ raw", float(next(v["raw_rate_s-1"] for v in load_json(VETO_JSON)["summaries"] if v["family"] == "eplus"))),
        ("Current e+ active", float(next(v["active_veto_pass_rate_s-1"] for v in load_json(VETO_JSON)["summaries"] if v["family"] == "eplus"))),
        ("Current e+ final", float(next(v["side_compton_fov_pass_rate_s-1"] for v in load_json(VETO_JSON)["summaries"] if v["family"] == "eplus"))),
        ("Barrel 2M 95% upper", float(barrel_w2["final_zero_count_95cl_upper_rate_s-1"])),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = [NEUTRAL["base"], NEUTRAL["light"], COLORS["orange"]["base"], COLORS["blue"]["base"]]
    edges = [NEUTRAL["dark"], NEUTRAL["dark"], COLORS["orange"]["dark"], COLORS["blue"]["dark"]]
    bars = ax.barh(np.arange(len(labels)), vals, color=colors, edgecolor=edges, linewidth=1.0)
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("Rate or upper rate (cps)")
    for bar, val in zip(bars, vals):
        ax.text(val + max(vals) * 0.015, bar.get_y() + bar.get_height() / 2, f"{val:.4g}", va="center", fontsize=8)
    add_chart_header(fig, ax, "Barrel 2M e+ run sets a component upper rate", "Zero W2 candidates in 2M e+ events gives a 95% upper rate of 0.00352 cps, not an all-particle closure.")
    return savefig(fig, "barrel_eplus_upper_limit")


def chart_geometry_image() -> Path:
    # The 2D geometry detail is already a rendered PNG source artifact.
    return GEOMETRY_2D


def make_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["<table>", "<thead><tr>"]
    for h in headers:
        out.append(f"<th>{html_escape(h)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{html_escape(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def metric_card(label: str, value: str, sub: str) -> str:
    return f"<div class='metric'><div class='metric-label'>{html_escape(label)}</div><div class='metric-value'>{html_escape(value)}</div><div class='metric-sub'>{html_escape(sub)}</div></div>"


def write_report(
    chart_paths: dict[str, Path],
    stage_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    depth_rows: list[dict[str, Any]],
    barrel: dict[str, Any],
    geom: dict[str, Any],
    atm511: dict[str, Any],
) -> Path:
    final_counts = {fam: len(final_rows_by_family(event_rows, fam)) for fam in ["eplus", "n", "atm511"]}
    barrel_w2 = next(r for r in barrel["rows"] if r["window"] == "w2_510p58_511p42")
    eplus_final_rate = next(r["side_compton_fov_pass_rate_s-1"] for r in load_json(VETO_JSON)["summaries"] if r["family"] == "eplus")
    upper = float(barrel_w2["final_zero_count_95cl_upper_rate_s-1"])
    upper_share = upper / float(eplus_final_rate)
    harris = next(row for row in atm511["scenario_rows"] if row["scenario"] == "Harris_Rc_11_13_total_disk_no_alt_scale")
    neutron_depth_plotted = sum(1 for r in depth_rows if r.get("plotted"))
    neutron_depth_missing = sum(1 for r in depth_rows if r.get("status") == "missing coordinate")
    neutron_depth_negative = sum(1 for r in depth_rows if r.get("depth_projection_cm") is not None and float(r["depth_projection_cm"]) < 0)

    veto_table = []
    for r in stage_rows:
        veto_table.append(
            [
                FAMILY_LABEL[r["family"]],
                r["raw"],
                r["active"],
                r["final"],
                pct(r["active_rejection"]),
                pct(r["compton_rejection"]),
                pct(r["final_survival"]),
            ]
        )

    html_parts = [
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>TES 511 几何优化：入射、veto 与 W 桶假设结论</title>",
        "<style>",
        """
        :root {
          --surface: #FCFCFD; --panel: #FFFFFF; --ink: #1F2430; --muted: #6F768A;
          --grid: #E6E8F0; --axis: #D7DBE7; --blue: #5477C4; --orange: #CC6F47;
          --gold: #B8A037; --olive: #71B436;
        }
        * { box-sizing: border-box; }
        body { margin: 0; background: var(--surface); color: var(--ink);
          font-family: Inter, Aptos, "Segoe UI", Arial, "Noto Sans CJK SC", sans-serif; line-height: 1.58; }
        main { max-width: 1120px; margin: 0 auto; padding: 44px 28px 72px; }
        header { padding-bottom: 18px; border-bottom: 1px solid var(--grid); }
        h1 { font-size: clamp(30px, 4vw, 48px); line-height: 1.08; margin: 0 0 14px; letter-spacing: 0; }
        h2 { font-size: 25px; margin: 42px 0 12px; letter-spacing: 0; }
        h3 { font-size: 18px; margin: 26px 0 8px; letter-spacing: 0; }
        p { margin: 10px 0 14px; }
        .summary { font-size: 17px; color: #303645; max-width: 920px; }
        .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 22px 0 4px; }
        .metric { background: var(--panel); border: 1px solid var(--grid); border-radius: 8px; padding: 14px 16px; }
        .metric-label { color: var(--muted); font-size: 12px; }
        .metric-value { font-size: 24px; font-weight: 700; margin-top: 4px; }
        .metric-sub { color: var(--muted); font-size: 12px; margin-top: 2px; }
        section { margin-top: 30px; }
        figure { margin: 18px 0 28px; background: var(--panel); border: 1px solid var(--grid); border-radius: 8px; padding: 14px; }
        figure img { display: block; width: 100%; height: auto; border-radius: 4px; }
        figcaption { color: var(--muted); font-size: 13px; margin-top: 10px; }
        .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .note { border-left: 4px solid var(--blue); background: #F4F7FE; padding: 12px 14px; border-radius: 6px; color: #2A3348; }
        .warn { border-left-color: var(--orange); background: #FFF5EF; }
        table { width: 100%; border-collapse: collapse; margin: 14px 0 24px; background: var(--panel); border: 1px solid var(--grid); border-radius: 8px; overflow: hidden; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--grid); font-size: 14px; }
        th { background: #F4F5F7; color: #394150; }
        tr:last-child td { border-bottom: 0; }
        code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 0.93em; background: #F4F5F7; padding: 0 4px; border-radius: 4px; }
        ul { padding-left: 22px; }
        li { margin: 6px 0; }
        .small { color: var(--muted); font-size: 13px; }
        @media (max-width: 760px) {
          main { padding: 28px 16px 54px; }
          .metrics, .grid2 { grid-template-columns: 1fr; }
          h1 { font-size: 32px; }
        }
        """,
        "</style></head><body><main>",
        "<header>",
        "<h1>TES 511 几何优化结论：入射方向、veto 效率与外置 W 桶假设</h1>",
        "<p class='summary'><strong>结论先行。</strong> 当前几何中，active veto 对中子有效、对大气 511 无效；Compton/FoV 对 e+ 和大气 511 只提供约 12% 的条件拒绝。外置 W 桶简化假设在 2M 正电子输运中没有产生 W2 或 480-550 keV TES 候选，给出 e+ 分量 95% 上限 0.00352 cps，但这不是总本底或 20 天灵敏度闭合。</p>",
        "<div class='metrics'>",
        metric_card("e+ 当前 W2 final", "0.02377 cps", "当前 geo-opt e+ final rate"),
        metric_card("W 桶 2M e+ 上限", "0.00352 cps", "0 count, 95% upper rate"),
        metric_card("大气 511 active veto", "0%", "W2 108/108 active pass"),
        metric_card("Review verdict", "PASS_WITH_LIMITATIONS", "技术复核通过但有限制"),
        "</div>",
        "</header>",
    ]

    html_parts.extend(
        [
            "<section><h2>技术摘要：三个结论决定下一步怎么跑</h2>",
            "<p><strong>第一，当前主动 veto 的强弱高度依赖粒子类型。</strong> 中子 W2 raw 候选从 60 个降到 13 个，active rejection 为 78.33%；e+ 只有 35.48%；大气 511 完全没有 active veto rejection，因为它是外部 511 光子场，不伴随可被 CsI/塑闪捕获的带电粒子能量沉积。</p>",
            "<p><strong>第二，Compton/FoV 不是强屏蔽。</strong> 它对 e+ active-pass 候选拒绝 12.50%，对大气 511 拒绝 12.04%，对当前中子样本为 0%。因此它是几何/运动学一致性过滤，不应被期待替代物理屏蔽。</p>",
            "<p><strong>第三，W 桶假设强烈压低 e+ 分量，但证据边界必须清楚。</strong> 2M e+ only run 没有 W2 TES-window 候选，95% 上限约为当前 e+ final rate 的 14.8%。不过这个几何同时移除了许多内部被动材料，所以不能把下降纯归因于外层 W 桶，也不能外推为总本底闭合。</p>",
        ]
    )

    html_parts.extend(
        [
            "<h2>Key findings with visual evidence</h2>",
            "<h3>W2 cutflow 说明：中子靠 active veto，大气 511 只能靠 Compton/FoV</h3>",
            "<p>下面两张图用同一组 W2 候选数。active rejection 的分母是 raw TES-window 候选；Compton/FoV rejection 的分母是 active-pass 候选。这个分母定义避免把最终候选当作 veto 分母。</p>",
            f"<figure><img src='{img_data_uri(chart_paths['veto_cutflow'])}' alt='W2 veto cutflow'><figcaption>W2 事件数 cutflow：raw → active pass → final pass。</figcaption></figure>",
            f"<figure><img src='{img_data_uri(chart_paths['veto_rejection'])}' alt='Veto rejection fractions'><figcaption>active veto 与 Compton/FoV 条件拒绝率。大气 511 的 active rejection 为 0。</figcaption></figure>",
            make_table(["family", "raw", "active pass", "final pass", "active rejection", "Compton/FoV rejection", "final survival"], veto_table),
            "<h3>入射方向：大气 511 final 候选主要来自侧面，e+ 和 n 更分散</h3>",
            f"<figure><img src='{img_data_uri(chart_paths['entry_surface'])}' alt='Final entry surface share'><figcaption>final W2 候选的入口面 proxy。atm511 的 region 数据只覆盖 95 个 final 候选，不能读成 raw/active 的分区效率。</figcaption></figure>",
            f"<figure><img src='{img_data_uri(chart_paths['direction_polar'])}' alt='e+ and neutron ingress direction sectors'><figcaption>正电子和中子 final W2 候选的 45° 方位扇区图。低统计下只用于看形状，不用于优化具体开孔。</figcaption></figure>",
            "<h3>中子能量-深度图：W2 raw neutron 候选没有单一能量/深度族群</h3>",
            f"<figure><img src='{img_data_uri(chart_paths['neutron_depth'])}' alt='Neutron energy versus first-hit depth proxy'><figcaption>中子初始能量与 first-hit 深度 proxy。可绘制 {neutron_depth_plotted}/60 个 raw 中子候选；{neutron_depth_missing} 个缺坐标，{neutron_depth_negative} 个投影为负值未纳入散点。</figcaption></figure>",
            "<p class='note warn'><strong>深度定义是 proxy。</strong> 深度按 IA INIT 外包络入射点到 first recorded hit 的入射方向投影估计，不是 Geant4 边界 crossing scorer。这个图适合判断“样本是否集中在特定能量/浅层穿透”，不适合做材料厚度优化的唯一依据。</p>",
            "<h3>首个记录体类别解释 veto 行为</h3>",
            f"<figure><img src='{img_data_uri(chart_paths['first_hit'])}' alt='First hit categories'><figcaption>e+ final 候选常先打到 GeoOpt plastic 或外壳机构；n final 候选类别更散，低统计下不要过度解释单个类别。</figcaption></figure>",
            "<h3>外置 W 桶假设：2M e+ 给出分量上限，不是总本底闭合</h3>",
            f"<figure><img src='{img_data_uri(chart_paths['barrel_limit'])}' alt='Barrel e+ upper limit'><figcaption>2M e+ only 的零计数 95% 上限与当前 e+ W2 rate 对比。</figcaption></figure>",
            "<p>W 桶 2M run 的 W2 和 480-550 keV 均为 <code>0/0/0</code>。按 2.995732 个 Poisson 95% 上限除以 851.448 s，得到 <code>0.00351839721692 cps</code>。这说明 e+ 分量在这个简化假设下被强烈压低，但仍不能回答中子、gamma、muon、delayed activation 和 atmospheric 511 合成后的 20 天灵敏度。</p>",
            "<h3>几何假设图：保留 TES/CsI/外支架，移除内部被动复杂体，外加 W 桶</h3>",
            f"<figure><img src='{img_data_uri(chart_paths['geometry'])}' alt='W barrel hypothesis geometry detail'><figcaption>几何 2D 细节图。WRL 文件也已保留在同一分支的 figures 目录。</figcaption></figure>",
        ]
    )

    html_parts.extend(
        [
            "<section><h2>Scope, data, and metric definitions</h2>",
            "<p><strong>W2 窗口</strong>定义为 TES 总能量 <code>510.58-511.42 keV</code>。当前几何统计来自 <code>geo_opt_s1_bpe_w5_fullstat_v1</code> 的 Step05/审计输出；大气 511 来自 3M lower-hemisphere mono-511 replay；W 桶假设只跑 e+。</p>",
            "<ul>",
            "<li><strong>raw：</strong>TES 能窗候选。</li>",
            "<li><strong>active pass：</strong>active veto 能量低于 50 keV 后保留的候选。当前几何 active 体包括 CsI/BGO/legacy active token 和 GeoOpt plastic skin；W 桶假设分析只把 CsI 计入 active veto。</li>",
            "<li><strong>final pass：</strong>active-pass 后再通过 side Compton/FoV 选择。</li>",
            "<li><strong>入射方向：</strong>由 IA INIT ray 与当前外包络的交点得到，是 entry proxy，不是边界 scorer。</li>",
            "</ul>",
            "<h2>Methodology and robustness checks</h2>",
            "<p>报告图表由现有 JSON/CSV/SIM 输出生成，没有重新改几何，也没有改原始 <code>511_Mass</code> 或 <code>Mass_model_511</code>。为了补充中子能量-深度图，报告脚本只对 W2 prompt e+/n 候选的 SIM 事件补采 first-hit 坐标；这一步写入报告侧车数据，不覆盖主审计结果。</p>",
            "<p>本地环境缺少 <code>seaborn</code> 和 <code>pandas</code>，图表采用 Matplotlib-only fallback，但沿用 Data Visualization 模板的配色、标题、字幕和 PNG 静态输出规则；所有图均以 <code>data:image/png;base64</code> 内嵌在 HTML 中。</p>",
            "<h2>Limitations and uncertainty</h2>",
            "<ul>",
            "<li>大气 511 的入射区域只对 95 个 final 候选有 metadata；不能当作大气 511 raw/active 分区 veto 效率。</li>",
            "<li>中子能量-深度图是 first-hit projection proxy；负投影和缺坐标点未绘制，图中已标注数量。</li>",
            "<li>W 桶几何是 stress-test：W 质量约 797 kg，不是可直接飞行设计。</li>",
            "<li>W 桶 run 是 positron-only；它不包含中子、gamma、muon、delayed activation 或 atmospheric 511 的合成闭合。</li>",
            "<li>简化几何移除了大量内部被动材料，所以 e+ 降低不能纯归因于外层 W 桶。</li>",
            "</ul>",
            "<h2>Recommended next steps</h2>",
            "<ol>",
            "<li>如果要判断真实设计收益，下一步应跑 all-particle prompt + delayed + atmospheric 511 的同一选择链，而不是只看 e+。</li>",
            "<li>如果要优化中子屏蔽，需要加一个真正的 Geant4 boundary/depth scorer 或在 SIM 层记录材料穿透路径，替代当前 first-hit depth proxy。</li>",
            "<li>如果外置 W 桶只是验证方向，下一轮应做质量可接受的 SS/W/BPE 参数扫描，并保持内部被动材料不被过度简化，才能分离“移除被动材料”和“外部屏蔽”两种效应。</li>",
            "</ol>",
            "<h2>Further questions</h2>",
            "<ul>",
            "<li>大气 511 的绝对归一化和角分布是否采用 Harris 场景，还是需要按飞行高度/方位重新取 EXPACS/PARMA？</li>",
            "<li>当前 active skin 对 e+ 的作用，是捕获正电子本身，还是主要标记伴随二次粒子？需要专门的 hit-time/parentage 审计。</li>",
            "<li>中子活化降低是否真的来自含硼聚乙烯，还是因为几何简化改变了产生核素的位置分布？需要 activation inventory 对比。</li>",
            "</ul>",
            "<p class='small'>Generated by <code>build_html_conclusion_report.py</code>. Main supporting audit: <code>FINAL_COMPLETION_AUDIT.md</code>; review verdict: <code>REVIEW_FINAL.md</code>.</p>",
            "</section>",
            "</main></body></html>",
        ]
    )

    report = OUT / "report.html"
    report.write_text("".join(html_parts), encoding="utf-8")
    return report


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    setup_chart_theme()

    ingress = load_json(INGRESS_JSON)
    veto = load_json(VETO_JSON)
    barrel = load_json(BARREL_JSON)
    geom = load_json(GEOM_MANIFEST)
    atm511 = load_json(ATM511_JSON)
    event_rows = ingress["event_rows"]
    stage_rows = stage_counts_from_veto(veto)

    metadata = collect_prompt_first_hit_metadata(event_rows)
    depth_rows = build_depth_records(event_rows, metadata)
    write_csv(
        DATA_DIR / "neutron_energy_depth_proxy.csv",
        depth_rows,
        [
            "local_id",
            "status",
            "init_energy_keV",
            "depth_projection_cm",
            "depth_distance_cm",
            "first_hit_category",
            "first_hit_volume",
            "plotted",
        ],
    )

    chart_paths = {
        "veto_cutflow": chart_veto_stage_counts(stage_rows),
        "veto_rejection": chart_rejection_fraction(stage_rows),
        "entry_surface": chart_entry_surface(event_rows),
        "direction_polar": chart_direction_polar(event_rows),
        "neutron_depth": chart_neutron_energy_depth(depth_rows),
        "first_hit": chart_first_hit_categories(event_rows),
        "barrel_limit": chart_barrel_limit(stage_rows, barrel),
        "geometry": chart_geometry_image(),
    }

    chart_map = {
        "delivery_mode": "html_static_png_inline",
        "audience": "technical",
        "visual_runtime_note": "Matplotlib-only fallback because seaborn/pandas are unavailable in the local Python environment; palette and chart scaffolding follow the read Seaborn template tokens.",
        "charts": {name: rel(path) for name, path in chart_paths.items()},
        "data": {
            "ingress_summary": rel(INGRESS_JSON),
            "veto_efficiency_summary": rel(VETO_JSON),
            "barrel_2m_summary": rel(BARREL_JSON),
            "neutron_energy_depth_proxy": rel(DATA_DIR / "neutron_energy_depth_proxy.csv"),
            "atm511_replay_summary": rel(ATM511_JSON),
            "geometry_manifest": rel(GEOM_MANIFEST),
            "review_final": rel(REVIEW_FINAL),
        },
        "technical_report_required_structure": [
            "Title",
            "Technical summary",
            "Key findings with visual evidence",
            "Scope, data, and metric definitions",
            "Methodology",
            "Limitations, uncertainty, and robustness checks",
            "Recommended next steps",
            "Further questions",
        ],
    }
    (OUT / "chart_map_and_sources.json").write_text(json.dumps(chart_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = write_report(chart_paths, stage_rows, event_rows, depth_rows, barrel, geom, atm511)
    print(
        json.dumps(
            {
                "status": "PASS_HTML_CONCLUSION_REPORT_BUILT",
                "report": rel(report),
                "charts": {name: rel(path) for name, path in chart_paths.items()},
                "neutron_depth_rows": len(depth_rows),
                "neutron_depth_plotted": sum(1 for r in depth_rows if r.get("plotted")),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
