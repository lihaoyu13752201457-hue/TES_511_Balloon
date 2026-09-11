#!/usr/bin/env python3
"""Normalize, tabulate, and plot SG3B prompt/activation coupling to TES."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3b_prompt_activation_coupling_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
ROUTES = PACKAGE / "outputs/01_selected_routes/sg3b_selected_w2_routes.json"
OUT = PACKAGE / "outputs/02_coupling_analysis"
COMMON = ROOT / "engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817"
COMMON_CODE = COMMON / "code/analyze_sg3b_common_time.py"
COMMON_CONFIG = COMMON / "analysis_inputs.json"
MISSION = COMMON / "outputs/01_common_time_response/mission_time_resolved_flux_threshold.csv"
COMMON_SUMMARY = COMMON / "outputs/01_common_time_response/summary.json"
SECONDS_PER_DAY = 86400.0
CENTER_Z = -5.2

MATERIAL_COLORS = {
    "Copper": "#D66A2C",
    "Aluminium": "#4F9BC4",
    "Bi": "#8B5FA8",
    "W": "#343A40",
    "BoratedPolyethylene5wtB": "#B99A45",
    "SilverSinterProxy": "#A8ADB3",
    "BGO": "#2C9A63",
}
FAMILY_COLORS = {
    "p": "#4C78A8", "n": "#72B7B2", "alpha": "#F58518", "gamma": "#E45756",
    "eminus": "#B279A2", "eplus": "#FF9DA6", "muminus": "#9D755D", "muplus": "#BAB0AC",
}
PROCESS_STYLE = {
    "DECA": ("P", "#7B61A8", 28), "PAIR": ("D", "#4D9221", 34),
    "ANNI": ("*", "#C23B7A", 48), "RAYL": ("x", "#25647A", 28),
    "COMP": ("o", "#E88955", 19), "PHOT": ("s", "#D1A900", 11),
    "BREM": ("^", "#6C7480", 13),
}
ELEMENTS = (
    "n", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P",
    "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh",
    "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re",
    "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db",
    "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"refusing empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def nuclide_label(za: int) -> str:
    z, a = divmod(int(za), 1000)
    symbol = ELEMENTS[z] if 0 <= z < len(ELEMENTS) else f"Z{z}"
    return f"{symbol}-{a}"


def material_lookup(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r"(?m)^([^\s.]+)\.Material\s+(\S+)\s*$", text)
    }


def mission_event_counts(events: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    common = load_module("sg3b_common_mission_reuse", COMMON_CODE)
    common_config = json.loads(COMMON_CONFIG.read_text(encoding="utf-8"))
    scales = read_csv(ROOT / common_config["mission"]["family_scales"])
    mission_rows = [
        row for row in read_csv(MISSION)
        if row["stage"] == "compton_trajectory_veto"
    ]
    mission_rows.sort(key=lambda row: int(row["time_bin_id"]))
    if len(scales) != 81 or len(mission_rows) != 81:
        raise RuntimeError("81-node mission closure missing")
    manifest = json.loads(Path(config["activation_manifest"]).read_text(encoding="utf-8"))
    inventory = common.inventory_authority(manifest)
    curves = common.activity_curves(inventory, scales)
    days = [float(row["day_mid"]) for row in mission_rows]
    live = [float(row["poisson_accidental_live_factor"]) for row in mission_rows]

    for event in events:
        family = event["family"]
        if event["stream"] == "prompt":
            base = float(event["event_weight_cps_day15_or_reference"])
            rates = [base * float(row[f"scale_{family}_to_parma_reference"]) for row in scales]
        else:
            key = (family, int(event["source"]["source_parent_ZA"]))
            if key not in curves:
                raise RuntimeError(f"missing activity curve for selected event {key}")
            # Each family transport draws from a 10k-source activity mixture but
            # is normalized as A_family(day15)/1e6 per trigger.  A selected
            # event therefore retains its family-level day-15 weight and only
            # inherits the source parent's relative time evolution A_ZA(t)/A_ZA(15).
            # Using A_ZA(t)/1e6 here would incorrectly apply the source-mixture
            # fraction a second time.
            base = float(event["event_weight_cps_day15_or_reference"])
            reference = float(inventory[key]["day15_activity_Bq"])
            rates = [base * value / reference for value in curves[key]]
        counts = math.fsum(
            0.5 * (rates[index] * live[index] + rates[index + 1] * live[index + 1])
            * (days[index + 1] - days[index]) * SECONDS_PER_DAY
            for index in range(len(days) - 1)
        )
        event["mission20_live_counts"] = counts
        event["day15_noacc_cps"] = rates[60]
        event["day15_live_cps"] = rates[60] * live[60]

    prompt_counts = math.fsum(e["mission20_live_counts"] for e in events if e["stream"] == "prompt")
    delayed_counts = math.fsum(e["mission20_live_counts"] for e in events if e["stream"] == "delayed")
    expected = float(mission_rows[-1]["cumulative_background_counts"])
    observed = prompt_counts + delayed_counts
    if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=2.0e-8):
        raise RuntimeError(f"20-day event fold mismatch: {observed} vs {expected}")
    return {
        "prompt_mission20_live_counts": prompt_counts,
        "delayed_mission20_live_counts": delayed_counts,
        "total_mission20_live_counts": observed,
        "package58_cumulative_background_counts": expected,
        "absolute_closure_counts": observed - expected,
        "day15_live_factor": live[60],
    }


def activity_tables(manifest: dict[str, Any], materials: dict[str, str]) -> dict[str, dict[str, float]]:
    tables: dict[str, dict[str, float]] = {
        "volume": defaultdict(float), "material": defaultdict(float),
        "nuclide": defaultdict(float), "family": defaultdict(float),
    }
    for cell in manifest["source_cells"]:
        family = cell["family"]
        for state in cell["included_states"]:
            activity = float(state["day15_activity_Bq"])
            volume = state["volume"]
            tables["volume"][volume] += activity
            tables["material"][materials.get(volume, "UNKNOWN")] += activity
            tables["nuclide"][nuclide_label(int(state["ZA"]))] += activity
            tables["family"][family] += activity
    return tables


def group_stats(
    events: list[dict[str, Any]], key_name: str, key_fn: Callable[[dict[str, Any]], str],
    activity: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        groups[key_fn(event)].append(event)
    total_day15 = math.fsum(event["day15_noacc_cps"] for event in events)
    total_mission = math.fsum(event["mission20_live_counts"] for event in events)
    total_activity = math.fsum(activity.values()) if activity else 0.0
    rows = []
    keys = set(groups)
    if activity:
        keys.update(activity)
    for key in keys:
        group = groups.get(key, [])
        day15_weights = [float(event["day15_noacc_cps"]) for event in group]
        mission_weights = [float(event["mission20_live_counts"]) for event in group]
        rate = math.fsum(day15_weights)
        rate_variance = math.fsum(value * value for value in day15_weights)
        counts = math.fsum(mission_weights)
        count_variance = math.fsum(value * value for value in mission_weights)
        a15 = activity.get(key, 0.0) if activity else 0.0
        rows.append({
            key_name: key,
            "selected_events": len(group),
            "day15_selected_noacc_cps": rate,
            "day15_mc_sigma_cps": math.sqrt(rate_variance),
            "day15_Neff": rate * rate / rate_variance if rate_variance else 0.0,
            "day15_selected_rate_share": rate / total_day15 if total_day15 else 0.0,
            "mission20_live_counts": counts,
            "mission20_mc_sigma_counts": math.sqrt(count_variance),
            "mission20_Neff": counts * counts / count_variance if count_variance else 0.0,
            "mission20_delayed_count_share": counts / total_mission if total_mission else 0.0,
            "transported_day15_activity_Bq": a15 if activity else "",
            "transported_activity_share": a15 / total_activity if activity and total_activity else "",
            "selected_cps_per_Bq_day15": rate / a15 if activity and a15 else "",
        })
    return sorted(rows, key=lambda row: (-float(row["mission20_live_counts"]), str(row[key_name])))


def classify_mechanism(event: dict[str, Any]) -> str:
    processes = {row["process"] for row in event["interactions"]}
    if event["stream"] == "prompt" and {"PAIR", "ANNI"} <= processes:
        regions = {row["sg3b_key_region"] for row in event["interactions"] if row["process"] == "PAIR"}
        return "prompt gamma -> pair in " + "+".join(sorted(regions)) + " -> positron annihilation -> TES"
    deca_products = {row["secondary_particle_code"] for row in event["interactions"] if row["process"] == "DECA"}
    if event["stream"] == "delayed" and 2 in deca_products and "ANNI" in processes:
        return "beta+ decay -> positron annihilation -> TES"
    return "+".join(sorted(processes))


def event_rows(events: list[dict[str, Any]], materials: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        source = event.get("source") or {}
        tes_hits = [row for row in event["hit_groups"] if str(row["volume"]).startswith("TP_")]
        layers = sorted({int(re.search(r"TP_L(\d+)_", row["volume"]).group(1)) for row in tes_hits})
        pair_regions = sorted({
            row["sg3b_key_region"] for row in event["interactions"] if row["process"] == "PAIR"
        })
        rows.append({
            "stream": event["stream"], "family": event["family"],
            "batch_id": event["batch_id"], "job_id": event["job_id"],
            "local_event_id": event["local_event_id"],
            "source_volume": source.get("source_volume", "atmospheric boundary"),
            "source_material": materials.get(source.get("source_volume", ""), "atmosphere"),
            "source_parent_ZA": source.get("source_parent_ZA", ""),
            "source_nuclide": nuclide_label(int(source["source_parent_ZA"])) if source else "",
            "source_xprime_cm": source.get("xprime_cm", ""),
            "source_yprime_cm": source.get("yprime_cm", ""),
            "source_zprime_cm": source.get("zprime_cm", ""),
            "source_radius_cm": source.get("radius_cm", ""),
            "raw_total_keV": event["raw_total_keV"],
            "measured_total_keV": event["measured_total_keV"],
            "plastic_keV": event["plastic_keV"], "bgo_keV": event["bgo_keV"],
            "topology_class": event["topology_class"],
            "TES_layers": ";".join(map(str, layers)),
            "TES_pixels": ";".join(event["tes"]["pixels"]),
            "pair_regions": ";".join(pair_regions),
            "mechanism": classify_mechanism(event),
            "day15_noacc_cps": event["day15_noacc_cps"],
            "day15_live_cps": event["day15_live_cps"],
            "mission20_live_counts": event["mission20_live_counts"],
        })
    return rows


def segments(event: dict[str, Any]) -> list[tuple[np.ndarray, str]]:
    by_id = {int(row["ia_id"]): row for row in event["interactions"]}
    output = []
    for row in event["interactions"]:
        if row["process"] in {"INIT", "ESCP"}:
            continue
        parent = by_id.get(int(row["parent_id"]))
        if parent is None or parent["process"] == "ESCP":
            continue
        output.append((np.asarray(((parent["xprime_cm"], parent["zprime_cm"]), (row["xprime_cm"], row["zprime_cm"]))), row["process"]))
    return output


def axial_segments(event: dict[str, Any]) -> list[np.ndarray]:
    by_id = {int(row["ia_id"]): row for row in event["interactions"]}
    output = []
    for row in event["interactions"]:
        if row["process"] in {"INIT", "ESCP"}:
            continue
        parent = by_id.get(int(row["parent_id"]))
        if parent is None or parent["process"] == "ESCP":
            continue
        output.append(np.asarray(((parent["xprime_cm"], parent["radius_cm"]), (row["xprime_cm"], row["radius_cm"]))))
    return output


def draw_sg3b_overlays_xz(ax: plt.Axes) -> None:
    # Remove the inherited central L0 disk interior and draw the retained SG3 ring.
    ax.add_patch(Rectangle((3.245, -7.4), 0.35, 4.4, facecolor="white", edgecolor="none", zorder=6))
    for z0, z1 in ((-8.0, -6.0), (-4.4, -2.4)):
        ax.add_patch(Rectangle((3.245, z0), 0.35, z1-z0, facecolor="#D66A2C", edgecolor="#7A3511", hatch="\\", alpha=0.66, zorder=8))
    # At y'=0 the upper half-cylinder appears as the top radial band.
    for x0, x1 in ((-3.8, 3.24), (3.60, 4.0)):
        ax.add_patch(Rectangle((x0, -1.6846), x1-x0, 0.4796, facecolor="#8B5FA8", edgecolor="#4D2E66", hatch="....", alpha=0.62, zorder=8))
    # Material-only Cu->Al can substitution: exact inherited edges are overdrawn in Al.
    ax.plot([-15.3, 15.3], [-9.8, -9.8], color="#4F9BC4", lw=2.0, alpha=0.75, zorder=7)
    for x in (-15.2, 15.2):
        ax.plot([x, x], [-9.7, -0.3], color="#4F9BC4", lw=1.5, alpha=0.72, zorder=7)


def draw_points(ax: plt.Axes, events: list[dict[str, Any]], *, axial: bool = False) -> None:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        source = event["source"]
        key = (source["source_volume"], source["xprime_cm"], source["yprime_cm"], source["zprime_cm"], source["radius_cm"])
        groups[key].append(event)
    max_counts = max(math.fsum(e["mission20_live_counts"] for e in group) for group in groups.values())
    for (volume, xp, yp, zp, radius), group in groups.items():
        material = group[0]["source_material"]
        counts = math.fsum(e["mission20_live_counts"] for e in group)
        size = 10.0 + 78.0 * math.sqrt(counts / max_counts)
        ax.scatter([xp], [radius if axial else zp], s=size, color=MATERIAL_COLORS.get(material, "#777777"), edgecolor="white", linewidth=0.4, alpha=0.68, zorder=13)


def draw_routes_xz(ax: plt.Axes, delayed: list[dict[str, Any]], prompt: dict[str, Any]) -> None:
    delayed_lines = [segment for event in delayed for segment, _ in segments(event)]
    if delayed_lines:
        ax.add_collection(LineCollection(delayed_lines, colors="#59636D", linewidths=0.25, alpha=0.035, zorder=9, rasterized=True))
    prompt_segments = segments(prompt)
    branches = [segment for segment, proc in prompt_segments if proc in {"PHOT", "BREM"}]
    core = [segment for segment, proc in prompt_segments if proc not in {"PHOT", "BREM"}]
    if branches:
        ax.add_collection(LineCollection(branches, colors="#D00000", linewidths=0.7, alpha=0.35, zorder=15))
    if core:
        ax.add_collection(LineCollection(core, colors="#D00000", linewidths=1.4, alpha=0.85, zorder=16))
    for process, (marker, color, size) in PROCESS_STYLE.items():
        points = [row for row in prompt["interactions"] if row["process"] == process]
        if points:
            kwargs: dict[str, Any] = {"s": size, "marker": marker, "color": color, "linewidth": 0.4, "zorder": 18}
            if marker != "x":
                kwargs["edgecolor"] = "#6B0000"
            ax.scatter([row["xprime_cm"] for row in points], [row["zprime_cm"] for row in points], **kwargs)
    ax.scatter([prompt["tes"]["xprime_cm"]], [prompt["tes"]["zprime_cm"]], s=44, marker="o", color="#00A6D6", edgecolor="white", zorder=19)


def save(fig: plt.Figure, stem: str) -> list[str]:
    paths = []
    for suffix in ("png", "svg", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        fig.savefig(path, dpi=300 if suffix == "png" else None, bbox_inches="tight", pad_inches=0.08)
        paths.append(str(path))
    plt.close(fig)
    return paths


def section_figures(visual: Any, mesh: dict[str, np.ndarray], delayed: list[dict[str, Any]], prompt: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for stem, limits, title in (
        ("sg3b_prompt_activation_global_section", ((-22, 22), (-16, 34)), "SG3B global section: final-W2 activation origins and prompt route"),
        ("sg3b_prompt_activation_local_section", ((-9, 10.5), (-12, 2.5)), "SG3B local near-field: activation-to-TES coupling and the prompt Bi pair route"),
    ):
        fig, ax = plt.subplots(figsize=(11.2, 8.2))
        visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
        draw_sg3b_overlays_xz(ax)
        draw_points(ax, delayed)
        draw_routes_xz(ax, delayed, prompt)
        visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
        ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1]); ax.set_title(title, weight="bold")
        ax.text(0.01, 0.985, "Exact inherited y'=0 mesh + SG3B analytic change overlays. Event tracks/points are x'-z' projections; use axial-radius figure for Bi/ring membership.", transform=ax.transAxes, ha="left", va="top", fontsize=6.5, bbox={"boxstyle":"round,pad=0.25","fc":"white","ec":"#C7D0D8","alpha":0.93}, zorder=30)
        handles = [Patch(facecolor=color, label=f"activation source: {material}") for material, color in MATERIAL_COLORS.items()]
        handles += [Line2D([0],[0],color="#D00000",lw=1.5,label="single SG3B prompt survivor IA tree"), Line2D([0],[0],marker="o",color="none",markerfacecolor="#00A6D6",label="TES deposit centroid")]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=6.5)
        fig.subplots_adjust(right=0.76)
        paths.extend(save(fig, stem))

    fig, (axp, axd) = plt.subplots(1, 2, figsize=(14.2, 6.5), sharex=True, sharey=True)
    for ax in (axp, axd):
        for x0, x1 in ((-3.8, 3.24), (3.6, 4.0)):
            ax.add_patch(Rectangle((x0, 3.5154), x1-x0, 0.4796, facecolor="#8B5FA8", edgecolor="#4D2E66", hatch="....", alpha=0.35, zorder=2))
        ax.add_patch(Rectangle((3.245, 2.0), 0.35, 2.4, facecolor="#D66A2C", edgecolor="#7A3511", hatch="\\", alpha=0.35, zorder=2))
        ax.set_xlim(-10.5, 10.5); ax.set_ylim(0, 15.5); ax.grid(color="#DCE4EA", lw=0.45, alpha=0.75); ax.set_xlabel("InstrumentFrame x' [cm]")
    prompt_lines = axial_segments(prompt)
    axp.add_collection(LineCollection(prompt_lines, colors="#D00000", linewidths=1.15, alpha=0.72, zorder=8))
    for proc, (marker, color, size) in PROCESS_STYLE.items():
        pts = [row for row in prompt["interactions"] if row["process"] == proc]
        if pts: axp.scatter([p["xprime_cm"] for p in pts], [p["radius_cm"] for p in pts], s=size, marker=marker, color=color, zorder=10)
    axp.scatter([prompt["tes"]["xprime_cm"]], [prompt["tes"]["radius_cm"]], s=42, color="#00A6D6", edgecolor="white", zorder=11)
    delayed_lines = [line for event in delayed for line in axial_segments(event)]
    axd.add_collection(LineCollection(delayed_lines, colors="#59636D", linewidths=0.25, alpha=0.028, zorder=5, rasterized=True))
    draw_points(axd, delayed, axial=True)
    axp.set_ylabel("radius sqrt(y'^2+(z'+5.2)^2) [cm]")
    axp.set_title("Prompt: 4.404 MeV gamma pairs in passive Bi", weight="bold")
    axd.set_title("Delayed: beta+ source origins and annihilation routes", weight="bold")
    fig.suptitle("SG3B final-W2 coupling in axial-radius coordinates (authoritative key-material membership)", weight="bold")
    fig.legend(handles=[Patch(facecolor="#8B5FA8",label="SG3B passive Bi"),Patch(facecolor="#D66A2C",label="SG3B L0 Cu ring"),Line2D([0],[0],color="#D00000",label="prompt IA tree"),Line2D([0],[0],marker="o",color="none",markerfacecolor="#00A6D6",label="TES")], loc="lower center", ncol=4, frameon=False)
    paths.extend(save(fig, "sg3b_prompt_activation_axial_radius"))
    return paths


def material_figure(rows: list[dict[str, Any]]) -> list[str]:
    rows = [row for row in rows if float(row["mission20_live_counts"]) > 0]
    labels = [row["source_material"] for row in rows]
    day15 = np.asarray([float(row["day15_selected_rate_share"]) for row in rows]) * 100
    mission = np.asarray([float(row["mission20_delayed_count_share"]) for row in rows]) * 100
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(8.8, 5.1))
    ax.barh(y+0.18, day15, height=0.34, color="#7A8793", label="day-15 no-accidental rate share")
    ax.barh(y-0.18, mission, height=0.34, color=[MATERIAL_COLORS.get(label,"#777") for label in labels], label="20-day live-count share")
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel("share of delayed final-W2 background [%]"); ax.grid(axis="x", color="#DCE4EA", lw=0.5); ax.legend(frameon=False)
    ax.set_title("SG3B delayed background by activated source material", weight="bold")
    return save(fig, "sg3b_delayed_source_material_shares")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    data = json.loads(ROUTES.read_text(encoding="utf-8"))
    events = data["events"]
    materials = material_lookup(Path(config["geometry_geo"]))
    for event in events:
        if event["source"]:
            volume = event["source"]["source_volume"]
            if volume not in materials:
                raise RuntimeError(f"selected source volume lacks material: {volume}")
            event["source_material"] = materials[volume]
    mission_closure = mission_event_counts(events, config)
    prompt = [event for event in events if event["stream"] == "prompt"]
    delayed = [event for event in events if event["stream"] == "delayed"]
    if len(prompt) != 1 or len(delayed) != 394:
        raise RuntimeError("selected event count drift")
    manifest = json.loads(Path(config["activation_manifest"]).read_text(encoding="utf-8"))
    activities = activity_tables(manifest, materials)
    volume_rows = group_stats(delayed, "source_volume", lambda e: e["source"]["source_volume"], activities["volume"])
    material_rows = group_stats(delayed, "source_material", lambda e: e["source_material"], activities["material"])
    nuclide_rows = group_stats(delayed, "source_nuclide", lambda e: nuclide_label(int(e["source"]["source_parent_ZA"])), activities["nuclide"])
    family_rows = group_stats(delayed, "incident_family", lambda e: e["family"], activities["family"])
    rows = event_rows(events, materials)
    write_csv(OUT / "selected_event_lineage.csv", rows)
    common_fields = [
        "selected_events", "day15_selected_noacc_cps", "day15_mc_sigma_cps", "day15_Neff",
        "day15_selected_rate_share", "mission20_live_counts", "mission20_mc_sigma_counts",
        "mission20_Neff", "mission20_delayed_count_share", "transported_day15_activity_Bq",
        "transported_activity_share", "selected_cps_per_Bq_day15",
    ]
    write_csv(OUT / "activation_by_volume.csv", volume_rows, ["source_volume", *common_fields])
    write_csv(OUT / "activation_by_material.csv", material_rows, ["source_material", *common_fields])
    write_csv(OUT / "activation_by_nuclide.csv", nuclide_rows, ["source_nuclide", *common_fields])
    write_csv(OUT / "activation_by_incident_family.csv", family_rows, ["incident_family", *common_fields])

    process_support = []
    for stream, subset in (("prompt", prompt), ("delayed", delayed)):
        support: Counter[str] = Counter()
        for event in subset:
            support.update({row["process"] for row in event["interactions"]})
        for process, count in sorted(support.items(), key=lambda item: (-item[1], item[0])):
            process_support.append({"stream": stream, "process": process, "supporting_selected_events": count, "selected_events_total": len(subset), "support_fraction": count/len(subset)})
    write_csv(OUT / "interaction_process_event_support.csv", process_support)

    tool = Path(config["section_tool"])
    sys.path.insert(0, str(tool))
    visual = load_module("sg3b_reused_se3_section_adapter", tool / "se3_section_adapter.py")
    visual.configure_matplotlib()
    mesh = visual.load_mesh(Path(config["section_mesh"]))
    figure_paths = section_figures(visual, mesh, delayed, prompt[0])
    figure_paths.extend(material_figure(material_rows))

    prompt_event = prompt[0]
    pair = next(row for row in prompt_event["interactions"] if row["process"] == "PAIR")
    delayed_total = math.fsum(e["day15_noacc_cps"] for e in delayed)
    material_map = {row["source_material"]: row for row in material_rows}
    volume_map = {row["source_volume"]: row for row in volume_rows}
    top_volumes = volume_rows[:10]
    signal_proxy_rows = read_csv(Path(config["conditional_signal_first_interaction_proxy"]))
    signal_w = next(row for row in signal_proxy_rows if row["first_interaction"] == "W collimator")
    signal_w_events = int(signal_w["total_events"])
    signal_total_rays = 37194
    summary = {
        "status": "PASS__SG3B_PROMPT_ACTIVATION_TO_TES_COUPLING_DIAGNOSTIC",
        "authority_boundary": {
            "rate_and_selection": "package58 common measured response",
            "routes": "selected-event IA parent/child diagnostic",
            "activation_points": "audited exact-position source parent and volume",
            "activation_production_tracks_reconstructed": False,
            "transport_started": False,
            "large_SIM_hashes_computed": 0,
            "fresh_SG3B_signal_authority": False,
        },
        "normalization_closure": mission_closure,
        "prompt": {
            "selected_events": 1,
            "relative_mc_error": 1.0,
            "family": prompt_event["family"],
            "initial_gamma_energy_keV": prompt_event["interactions"][0]["secondary_energy_keV"],
            "pair_material": "Bi",
            "pair_region": pair["sg3b_key_region"],
            "pair_xprime_cm": pair["xprime_cm"],
            "pair_yprime_cm": pair["yprime_cm"],
            "pair_zprime_cm": pair["zprime_cm"],
            "pair_radius_cm": pair["radius_cm"],
            "mechanism": classify_mechanism(prompt_event),
            "TES_layers": sorted({int(re.search(r"TP_L(\d+)_", p).group(1)) for p in prompt_event["tes"]["pixels"]}),
            "TES_pixels": prompt_event["tes"]["pixels"],
            "active_veto_deposit_keV": prompt_event["plastic_keV"] + prompt_event["bgo_keV"],
            "mission20_live_counts": prompt_event["mission20_live_counts"],
        },
        "delayed": {
            "selected_events": len(delayed),
            "day15_noacc_cps": delayed_total,
            "all_selected_events_contain_beta_plus_decay_and_annihilation": all(
                2 in {row["secondary_particle_code"] for row in event["interactions"] if row["process"] == "DECA"}
                and any(row["process"] == "ANNI" for row in event["interactions"])
                for event in delayed
            ),
            "source_materials": material_rows,
            "top_source_volumes": top_volumes,
            "L0_Cu_ring": volume_map.get("SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm"),
            "MXC_Cu_plate": volume_map.get("ColdPlate_MXC_50mK_SD_anchor"),
            "SG3B_Bi_half_cylinder": volume_map.get("SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm"),
            "SG3A_Al_50mK_can_bottom": volume_map.get("SG3A_Al_50mK_StillLike_Can_bottom_cap_2mm"),
        },
        "w_collimator_context": {
            "mandatory_for_laue_focal_plane": False,
            "conditional_signal_proxy_only": True,
            "proxy_W_first_interactions": signal_w_events,
            "proxy_focused_rays": signal_total_rays,
            "proxy_W_first_interaction_fraction": signal_w_events / signal_total_rays,
            "proxy_W_first_interaction_pass_events": int(signal_w["pass_events"]),
            "SG3B_delayed_multihole_HBar": volume_map.get("W_Multihole_Collimator_HBar"),
            "SG3B_delayed_multihole_VBar_Center": volume_map.get("W_Multihole_Collimator_VBar_Center"),
            "SG3B_delayed_passive_bottom_W": volume_map.get("Passive_W_Bottom_Plate_detector_bay"),
            "decision_boundary": "benefit requires a matched W-collimator-on/off ablation; current data do not isolate its rejected-background benefit",
        },
        "figures": figure_paths,
        "tables": [
            str(OUT / "selected_event_lineage.csv"), str(OUT / "activation_by_volume.csv"),
            str(OUT / "activation_by_material.csv"), str(OUT / "activation_by_nuclide.csv"),
            str(OUT / "activation_by_incident_family.csv"), str(OUT / "interaction_process_event_support.csv"),
        ],
    }
    write_json(OUT / "summary.json", summary)
    report = f"""# SG3B prompt and activation coupling into TES

## Readout boundary

The selected sample is exactly one prompt event plus 394 delayed events, reproduced with the
package-58 keyed noise, 50 keV plastic/BGO veto, measured W2 window, and Step05 trajectory rule.
The event fold closes to {mission_closure['total_mission20_live_counts']:.9f} live background counts
over 20 days, matching package 58 within {mission_closure['absolute_closure_counts']:.3g} count.

## Prompt route

The sole prompt survivor is a {prompt_event['interactions'][0]['secondary_energy_keV']:.3f} keV
atmospheric gamma.  It undergoes pair production in the passive SG3B Bi upper half-cylinder at
`x'={pair['xprime_cm']:.3f}, y'={pair['yprime_cm']:.3f}, z'={pair['zprime_cm']:.3f} cm`
(`r={pair['radius_cm']:.3f} cm`).  The positron annihilates in the same Bi; one 510.999 keV photon
then Compton-scatters and photoabsorbs in two L5 TES pixels.  Plastic and BGO record 0 keV, so the
event is not vetoable by the present active layers.  This is direct route evidence that the Bi
half-cylinder can create a prompt W2 event.  With N=1, its rate has 100% relative MC uncertainty.

## Delayed route

Every delayed survivor contains a beta-plus decay and positron annihilation; the final TES energy
is carried by annihilation gamma interactions.  At day 15, activated Copper contributes
{float(material_map['Copper']['day15_selected_rate_share']):.2%} of delayed W2, Aluminium
{float(material_map['Aluminium']['day15_selected_rate_share']):.2%}, Bi
{float(material_map['Bi']['day15_selected_rate_share']):.2%}, and W
{float(material_map['W']['day15_selected_rate_share']):.2%}.  The SG3B Bi liner term is four
Po-199 events from proton activation: {float(volume_map['SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm']['day15_selected_noacc_cps']):.6g} cps,
with N_eff={float(volume_map['SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm']['day15_Neff']):.3g}; its
50% single-cell MC uncertainty prevents a precise Bi rate claim.

The largest normalized source volumes are listed in `activation_by_volume.csv`.  The diagnostic
separates selected-event source location from BUILDUP production history: it does not reconstruct
the earlier atmospheric-particle track that created each nuclide.

## W collimator context

A passive focal-plane W collimator is not intrinsically required by a Laue focusing telescope.
The inherited focused-signal proxy has {signal_w_events}/{signal_total_rays}
({signal_w_events/signal_total_rays:.2%}) rays interacting first in the W collimator, and none of
those rays pass the final signal selection.  In the SG3B delayed sample, the multihole HBar and
center VBar have 0 selected events despite 0.47142 Bq combined day-15 activity; the separate
passive W bottom plate contributes 3 selected events and 3.53% of 20-day delayed counts.  These
facts argue for a matched collimator-on/off ablation, not an unconditional keep/remove decision:
the current package does not measure how much off-axis background the collimator rejects, and the
signal result remains an unchanged-geometry SE3 proxy rather than fresh SG3B signal authority.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": summary["status"], "prompt": summary["prompt"], "mission": mission_closure}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
