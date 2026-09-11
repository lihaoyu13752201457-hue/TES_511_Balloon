#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build DIXE-style background component and delayed-geometry statistics."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Records/04_activation_rpip/dixe_equivalent_background_stats_20260522"
DELAYED_BY_VOLUME = ROOT / "reports2.0/03_NEXT_PHASE_SUPPORT/activation_511_diagnostics/delayed_511_by_nuclide_volume.csv"
DELAYED_SUMMARY = ROOT / "reports2.0/03_NEXT_PHASE_SUPPORT/activation_511_diagnostics/activation_511_diagnostic_summary.json"
IMAGE8_COMPONENT = ROOT / "reports2.0/02_PHASE2_CORE_MATERIALS/image8_tables/image8_style_component_rates.csv"
DAY15_COMPONENT = ROOT / "reports/day15_complete_report/image8_like_component_rates_with_science.csv"
BACKGROUND_TIME = ROOT / "reports_260516/source_time_update/background_time_variation.csv"
HALFLIFE_TOTAL = ROOT / "Records/03_mission_time_variation/activation_half_life_ode_total.csv"
PHYSICAL_ACTIVITY_GROUPS = ROOT / "reports2.0/03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/activation_geometry_volume_summary.csv"
WINDOWS = ["broad_480_550", "line_510p3_511p8", "near_506_516"]
WINDOW_LABELS = {
    "broad_480_550": "480-550 keV",
    "line_510p3_511p8": "510.3-511.8 keV",
    "near_506_516": "506-516 keV",
}
STAGES = ["raw", "bgo", "final"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row: dict[str, str] | dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(value: Any, digits: int = 4) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(val):
        return "nan"
    return f"{val:.{digits}g}"


def geometry_group(volume: str) -> str:
    if volume.startswith("TES") or volume.startswith("TP_"):
        return "TES/pixel"
    if volume.startswith("Substrate"):
        return "Substrate"
    if "BGO" in volume:
        return "BGO shield"
    if volume.startswith("Win_"):
        return "Windows"
    if "Nb_Shield" in volume:
        return "Nb shield"
    if "W_Shield" in volume or "Win_W" in volume or "Collimator" in volume:
        return "W/collimator"
    if volume.startswith("Cu_"):
        return "Cu support"
    if volume.startswith("Al_") or "Frame" in volume:
        return "Al support"
    return "Other"


def aggregate_delayed(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    volume_acc: dict[tuple[str, str], dict[str, Any]] = {}
    group_acc: dict[tuple[str, str], dict[str, Any]] = {}
    top_rows: list[dict[str, Any]] = []

    for row in rows:
        volume = row["source_volume_proxy"]
        group = geometry_group(volume)
        for window in WINDOWS:
            raw = f(row, f"{window}_raw_cps")
            bgo = f(row, f"{window}_bgo_cps")
            final = f(row, f"{window}_final_cps")
            key = (window, volume)
            rec = volume_acc.setdefault(
                key,
                {
                    "window": window,
                    "window_label": WINDOW_LABELS[window],
                    "source_volume_proxy": volume,
                    "geometry_group": group,
                    "raw_cps": 0.0,
                    "bgo_cps": 0.0,
                    "final_cps": 0.0,
                    "events_total": 0.0,
                    "events_with_tes": 0.0,
                    "nuclides": set(),
                },
            )
            rec["raw_cps"] += raw
            rec["bgo_cps"] += bgo
            rec["final_cps"] += final
            rec["events_total"] += f(row, "events_total")
            rec["events_with_tes"] += f(row, "events_with_tes")
            rec["nuclides"].add(row["nuclide"])

            gkey = (window, group)
            grec = group_acc.setdefault(
                gkey,
                {
                    "window": window,
                    "window_label": WINDOW_LABELS[window],
                    "geometry_group": group,
                    "raw_cps": 0.0,
                    "bgo_cps": 0.0,
                    "final_cps": 0.0,
                    "events_total": 0.0,
                    "events_with_tes": 0.0,
                    "volumes": set(),
                    "nuclides": set(),
                },
            )
            grec["raw_cps"] += raw
            grec["bgo_cps"] += bgo
            grec["final_cps"] += final
            grec["events_total"] += f(row, "events_total")
            grec["events_with_tes"] += f(row, "events_with_tes")
            grec["volumes"].add(volume)
            grec["nuclides"].add(row["nuclide"])

        top_rows.append(
            {
                "ZA": row["ZA"],
                "nuclide": row["nuclide"],
                "source_volume_proxy": volume,
                "geometry_group": group,
                "activity_Bq_total_by_ZA": f(row, "activity_Bq_total_by_ZA"),
                "events_total": f(row, "events_total"),
                "events_with_tes": f(row, "events_with_tes"),
                "broad_480_550_final_cps": f(row, "broad_480_550_final_cps"),
                "line_510p3_511p8_final_cps": f(row, "line_510p3_511p8_final_cps"),
                "near_506_516_final_cps": f(row, "near_506_516_final_cps"),
            }
        )

    totals_by_window: dict[str, float] = defaultdict(float)
    for (_window, _volume), rec in volume_acc.items():
        totals_by_window[rec["window"]] += rec["final_cps"]

    volume_rows: list[dict[str, Any]] = []
    for rec in volume_acc.values():
        total = totals_by_window[rec["window"]]
        raw = rec["raw_cps"]
        bgo = rec["bgo_cps"]
        final = rec["final_cps"]
        volume_rows.append(
            {
                "window": rec["window"],
                "window_label": rec["window_label"],
                "source_volume_proxy": rec["source_volume_proxy"],
                "proxy_definition": "first primary CC HIT volume, not decay-source geometry",
                "geometry_group": rec["geometry_group"],
                "raw_cps": raw,
                "bgo_cps": bgo,
                "final_cps": final,
                "bgo_rejected_cps": max(raw - bgo, 0.0),
                "compton_rejected_cps": max(bgo - final, 0.0),
                "final_fraction_of_window": final / total if total > 0.0 else 0.0,
                "bgo_survival": bgo / raw if raw > 0.0 else "",
                "final_survival": final / raw if raw > 0.0 else "",
                "events_total": rec["events_total"],
                "events_with_tes": rec["events_with_tes"],
                "nuclide_count": len(rec["nuclides"]),
                "nuclides": ";".join(sorted(rec["nuclides"])),
            }
        )

    group_rows: list[dict[str, Any]] = []
    for rec in group_acc.values():
        total = totals_by_window[rec["window"]]
        raw = rec["raw_cps"]
        bgo = rec["bgo_cps"]
        final = rec["final_cps"]
        group_rows.append(
            {
                "window": rec["window"],
                "window_label": rec["window_label"],
                "geometry_group": rec["geometry_group"],
                "proxy_definition": "first primary CC HIT volume group, not decay-source geometry group",
                "raw_cps": raw,
                "bgo_cps": bgo,
                "final_cps": final,
                "bgo_rejected_cps": max(raw - bgo, 0.0),
                "compton_rejected_cps": max(bgo - final, 0.0),
                "final_fraction_of_window": final / total if total > 0.0 else 0.0,
                "bgo_survival": bgo / raw if raw > 0.0 else "",
                "final_survival": final / raw if raw > 0.0 else "",
                "events_total": rec["events_total"],
                "events_with_tes": rec["events_with_tes"],
                "volume_count": len(rec["volumes"]),
                "nuclide_count": len(rec["nuclides"]),
                "volumes": ";".join(sorted(rec["volumes"])),
                "nuclides": ";".join(sorted(rec["nuclides"])),
            }
        )

    volume_rows.sort(key=lambda item: (item["window"], -float(item["final_cps"])))
    group_rows.sort(key=lambda item: (item["window"], -float(item["final_cps"])))
    top_rows.sort(key=lambda item: -float(item["broad_480_550_final_cps"]))
    return volume_rows, group_rows, top_rows


def build_component_stage_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if IMAGE8_COMPONENT.exists():
        for row in read_csv(IMAGE8_COMPONENT):
            component = row["component"]
            window = row["window"]
            rows.append(
                {
                    "source_table": str(IMAGE8_COMPONENT.relative_to(ROOT)),
                    "component": component,
                    "window": window,
                    "window_label": WINDOW_LABELS.get(window, window),
                    "raw_cps": f(row, "raw_cps"),
                    "bgo_cps": f(row, "bgo_cps"),
                    "final_cps": f(row, "final_cps"),
                    "available_stages": "raw,bgo,final",
                }
            )

    # Add the broad incident-component rate table for DIXE-style prompt component context.
    if DAY15_COMPONENT.exists():
        for row in read_csv(DAY15_COMPONENT):
            rows.append(
                {
                    "source_table": str(DAY15_COMPONENT.relative_to(ROOT)),
                    "component": row["component"],
                    "window": "broad_480_550",
                    "window_label": "480-550 keV",
                    "raw_cps": f(row, "rate_480_550_keV_cps"),
                    "bgo_cps": "",
                    "final_cps": "",
                    "available_stages": "raw_480_550_component_only",
                }
            )
    return rows


def build_physical_activity_rows() -> list[dict[str, Any]]:
    if not PHYSICAL_ACTIVITY_GROUPS.exists():
        return []
    rows: list[dict[str, Any]] = []
    for row in read_csv(PHYSICAL_ACTIVITY_GROUPS):
        rows.append(
            {
                "source_table": str(PHYSICAL_ACTIVITY_GROUPS.relative_to(ROOT)),
                "geometry_group": row["geometry_group"],
                "day15_parentfed_activity_Bq": f(row, "day15_parentfed_activity_Bq"),
                "broad_480_550_final_cps_first_hit_proxy": f(row, "broad_480_550_final_cps"),
                "line_510p3_511p8_final_cps_first_hit_proxy": f(row, "line_510p3_511p8_final_cps"),
                "geometry_note": row.get("geometry_note", ""),
                "interpretation": "physical activation inventory group plus first-hit transport proxy; zero activity with nonzero cps means this is not a source-location contribution",
            }
        )
    rows.sort(key=lambda item: -float(item["day15_parentfed_activity_Bq"]))
    return rows


def build_time_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(BACKGROUND_TIME):
        rows.append(
            {
                "source_table": str(BACKGROUND_TIME.relative_to(ROOT)),
                "time_bin_id": row["time_bin_id"],
                "day_mid": f(row, "day_mid"),
                "window": row["window"],
                "window_label": WINDOW_LABELS.get(row["window"], row["window"]),
                "altitude_km": f(row, "altitude_km"),
                "activation_driver": f(row, "activation_driver"),
                "total_delayed_activity_Bq": f(row, "total_delayed_activity_Bq"),
                "prompt_final_cps": f(row, "prompt_final_cps"),
                "delayed_final_cps": f(row, "delayed_final_cps_level1"),
                "total_background_final_cps": f(row, "total_background_final_cps_level1"),
                "time_series_mode": row.get("delayed_scaling_reference", ""),
            }
        )
    if HALFLIFE_TOTAL.exists():
        half_rows = read_csv(HALFLIFE_TOTAL)
        by_day: dict[float, dict[str, str]] = {round(f(row, "day_mid"), 6): row for row in half_rows}
        for row in rows:
            half = by_day.get(round(float(row["day_mid"]), 6))
            if half:
                row["half_life_ode_total_activity_Bq"] = f(half, "ode_total_activity_Bq")
                row["half_life_ode_total_scaled_delayed_final_cps"] = f(half, "ode_total_scaled_delayed_final_cps")
    return rows


def make_plots(
    volume_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    time_rows: list[dict[str, Any]],
    physical_activity_rows: list[dict[str, Any]],
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for window in ["broad_480_550", "line_510p3_511p8"]:
        use = [row for row in group_rows if row["window"] == window]
        labels = [row["geometry_group"] for row in use]
        raw = [float(row["raw_cps"]) for row in use]
        bgo_rej = [float(row["bgo_rejected_cps"]) for row in use]
        comp_rej = [float(row["compton_rejected_cps"]) for row in use]
        final = [float(row["final_cps"]) for row in use]
        x = range(len(use))
        fig, ax = plt.subplots(figsize=(9.0, 4.9))
        ax.bar(x, final, color="#4C78A8", label="final kept")
        ax.bar(x, comp_rej, bottom=final, color="#F58518", label="Compton/FoV rejected")
        ax.bar(
            x,
            bgo_rej,
            bottom=[final[i] + comp_rej[i] for i in range(len(use))],
            color="#E45756",
            label="BGO rejected",
        )
        ax.plot(x, raw, color="#333333", marker="o", ms=3, lw=1.0, label="raw")
        ax.set_xticks(list(x), labels, rotation=35, ha="right")
        ax.set_ylabel("delayed rate (cps)")
        ax.set_title(f"DIXE-style first-hit geometry proxy: {WINDOW_LABELS[window]}")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / f"dixe_delayed_geometry_group_{window}.png", dpi=220)
        plt.close(fig)

        vuse = [row for row in volume_rows if row["window"] == window][:20]
        fig, ax = plt.subplots(figsize=(10.0, 5.2))
        ax.barh(
            [row["source_volume_proxy"] for row in reversed(vuse)],
            [float(row["final_cps"]) for row in reversed(vuse)],
            color="#4C78A8",
        )
        ax.set_xlabel("final delayed rate (cps)")
        ax.set_title(f"Top delayed source-volume proxies: {WINDOW_LABELS[window]}")
        ax.grid(True, axis="x", alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / f"dixe_delayed_volume_top20_{window}.png", dpi=220)
        plt.close(fig)

    stage = [row for row in component_rows if row["source_table"].endswith("image8_style_component_rates.csv")]
    if stage:
        labels = [f"{row['component']}\n{row['window_label']}" for row in stage]
        x = range(len(stage))
        fig, ax = plt.subplots(figsize=(8.7, 4.9))
        width = 0.24
        for offset, stage_name, color in [(-width, "raw", "#4C78A8"), (0.0, "bgo", "#F58518"), (width, "final", "#54A24B")]:
            ax.bar(
                [idx + offset for idx in x],
                [float(row[f"{stage_name}_cps"]) for row in stage],
                width=width,
                label=stage_name,
                color=color,
            )
        ax.set_xticks(list(x), labels)
        ax.set_ylabel("rate (cps)")
        ax.set_yscale("log")
        ax.set_title("Image8/DIXE-style component-stage rates")
        ax.grid(True, axis="y", which="both", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "dixe_component_stage_rates.png", dpi=220)
        plt.close(fig)

    broad = [row for row in time_rows if row["window"] == "broad_480_550"]
    line = [row for row in time_rows if row["window"] == "line_510p3_511p8"]
    if broad and line:
        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        ax.plot([float(row["day_mid"]) for row in broad], [float(row["delayed_final_cps"]) for row in broad], lw=1.4, label="480-550 delayed final")
        ax.plot([float(row["day_mid"]) for row in line], [float(row["delayed_final_cps"]) for row in line], lw=1.4, label="510.3-511.8 delayed final")
        if "half_life_ode_total_scaled_delayed_final_cps" in broad[0]:
            ax.plot(
                [float(row["day_mid"]) for row in broad],
                [float(row.get("half_life_ode_total_scaled_delayed_final_cps", row["delayed_final_cps"])) for row in broad],
                lw=1.0,
                ls="--",
                color="#333333",
                label="half-life ODE total scaled",
            )
        ax.set_xlabel("mission day")
        ax.set_ylabel("delayed final rate (cps)")
        ax.set_title("Fig.13-like delayed time evolution proxy")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "dixe_delayed_time_evolution_proxy.png", dpi=220)
        plt.close(fig)

    if physical_activity_rows:
        top = physical_activity_rows[:10]
        labels = [row["geometry_group"] for row in reversed(top)]
        vals = [float(row["day15_parentfed_activity_Bq"]) for row in reversed(top)]
        fig, ax = plt.subplots(figsize=(9.0, 4.9))
        ax.barh(labels, vals, color="#4C78A8")
        ax.set_xlabel("day-15 parent-fed activity (Bq)")
        ax.set_title("Physical activation inventory by geometry group")
        ax.grid(True, axis="x", alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / "dixe_physical_activation_inventory_by_group.png", dpi=220)
        plt.close(fig)


def build_summary(
    volume_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    top_rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    time_rows: list[dict[str, Any]],
    physical_activity_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    broad_groups = [row for row in group_rows if row["window"] == "broad_480_550"]
    line_groups = [row for row in group_rows if row["window"] == "line_510p3_511p8"]
    broad_top = broad_groups[0] if broad_groups else {}
    line_top = line_groups[0] if line_groups else {}
    delayed_summary = load_json(DELAYED_SUMMARY) if DELAYED_SUMMARY.exists() else {}
    return {
        "status": "PASS",
        "claim_level": "DIXE_STYLE_EQUIVALENT_COMPONENT_STAGE_AND_DELAYED_GEOMETRY_STATS_FROM_LOCAL_SIMULATION_DATA",
        "literature_basis": {
            "paper": "Simulation of non X-ray background for the DIffuse X-ray Explorer (DIXE) mission",
            "arxiv": "https://arxiv.org/abs/2604.13569",
            "local_equivalence": "component rates, stage survival, delayed source-volume proxy, and delayed time-evolution proxy",
        },
        "inputs": {
            "delayed_by_nuclide_volume": str(DELAYED_BY_VOLUME.relative_to(ROOT)),
            "delayed_summary": str(DELAYED_SUMMARY.relative_to(ROOT)),
            "image8_component_rates": str(IMAGE8_COMPONENT.relative_to(ROOT)),
            "day15_component_rates": str(DAY15_COMPONENT.relative_to(ROOT)),
            "background_time_variation": str(BACKGROUND_TIME.relative_to(ROOT)),
            "half_life_total": str(HALFLIFE_TOTAL.relative_to(ROOT)) if HALFLIFE_TOTAL.exists() else "",
            "physical_activity_groups": str(PHYSICAL_ACTIVITY_GROUPS.relative_to(ROOT)) if PHYSICAL_ACTIVITY_GROUPS.exists() else "",
        },
        "totals_from_delayed_summary": delayed_summary.get("totals", {}),
        "row_counts": {
            "delayed_volume_rows": len(volume_rows),
            "delayed_group_rows": len(group_rows),
            "delayed_top_nuclide_volume_rows": len(top_rows),
            "component_rows": len(component_rows),
            "time_rows": len(time_rows),
            "physical_activity_rows": len(physical_activity_rows),
        },
        "key_results": {
            "broad_top_first_hit_proxy_group": broad_top.get("geometry_group"),
            "broad_top_first_hit_proxy_group_final_cps": broad_top.get("final_cps"),
            "broad_top_first_hit_proxy_group_fraction": broad_top.get("final_fraction_of_window"),
            "line_top_first_hit_proxy_group": line_top.get("geometry_group"),
            "line_top_first_hit_proxy_group_final_cps": line_top.get("final_cps"),
            "line_top_first_hit_proxy_group_fraction": line_top.get("final_fraction_of_window"),
            "top_nuclide_volume_by_broad_final": top_rows[0] if top_rows else {},
            "top_physical_activation_group_by_day15_activity": physical_activity_rows[0] if physical_activity_rows else {},
        },
        "caveats": [
            "DIXE Fig.11 tracks particle type, creation volume, and creation process for final absorber events. The local MEGAlib diagnostic table used here has source_volume_proxy and nuclide, but not a complete parent-process table for each final TES hit.",
            "source_volume_proxy is the first primary CC-HIT volume, not an exact decay-source block identity; Substrate being the largest proxy does not mean silicon substrate is the largest activated source location.",
            "The delayed time-evolution proxy is the balloon activation time series, not DIXE SAA orbital passage timing.",
        ],
    }


def write_readme(
    summary: dict[str, Any],
    group_rows: list[dict[str, Any]],
    top_rows: list[dict[str, Any]],
    physical_activity_rows: list[dict[str, Any]],
) -> None:
    broad_groups = [row for row in group_rows if row["window"] == "broad_480_550"][:5]
    line_groups = [row for row in group_rows if row["window"] == "line_510p3_511p8"][:5]
    lines = [
        "# DIXE-style Background Statistics",
        "",
        "Status: `PASS`",
        "",
        "This directory builds the local equivalent of the DIXE non-X-ray-background diagnostics: component rates, veto-stage survival, first-hit delayed geometry proxy, physical activation inventory groups, and a delayed time-evolution proxy.",
        "",
        "The DIXE paper uses a detailed Geant4 mass model, realistic radiation components, and tracks the particle types, creation locations, and production processes that generate absorber background events. It also studies delayed activation after SAA passages. Here the equivalent is constrained by the local tables available in this repository.",
        "",
        "## Inputs",
        "",
        f"- Delayed nuclide/volume diagnostic: `{summary['inputs']['delayed_by_nuclide_volume']}`",
        f"- Component-stage table: `{summary['inputs']['image8_component_rates']}`",
        f"- Day-15 incident-component table: `{summary['inputs']['day15_component_rates']}`",
        f"- Time-varying prompt/delayed ledger: `{summary['inputs']['background_time_variation']}`",
        f"- Physical activity group table: `{summary['inputs']['physical_activity_groups']}`",
        "",
        "## Interpretation Guard",
        "",
        "`source_volume_proxy` means the first primary `CC HIT` volume recorded by the diagnostic analyzer. It is not the physical decay-source geometry. Therefore the large Substrate proxy contribution below should be read as delayed particles first interacting in or passing through substrate layers before TES selection, not as silicon substrates being the dominant activated material.",
        "",
        "## First-hit Geometry Proxy Contributions",
        "",
        "Top broad-window geometry groups:",
        "",
        "| group | final cps | fraction | BGO survival | final/raw survival |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in broad_groups:
        lines.append(
            f"| {row['geometry_group']} | {fmt(row['final_cps'])} | {fmt(row['final_fraction_of_window'])} | {fmt(row['bgo_survival'])} | {fmt(row['final_survival'])} |"
        )
    lines.extend(
        [
            "",
            "Top line-window geometry groups:",
            "",
            "| group | final cps | fraction | BGO survival | final/raw survival |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in line_groups:
        lines.append(
            f"| {row['geometry_group']} | {fmt(row['final_cps'])} | {fmt(row['final_fraction_of_window'])} | {fmt(row['bgo_survival'])} | {fmt(row['final_survival'])} |"
        )
    if top_rows:
        top = top_rows[0]
        lines.extend(
            [
                "",
                "## Physical Activation Inventory",
                "",
                "| group | day15 activity Bq | broad first-hit proxy cps | note |",
                "|---|---:|---:|---|",
            ]
        )
        for row in physical_activity_rows[:8]:
            lines.append(
                f"| {row['geometry_group']} | {fmt(row['day15_parentfed_activity_Bq'])} | {fmt(row['broad_480_550_final_cps_first_hit_proxy'])} | {row['geometry_note']} |"
            )
        lines.extend(
            [
                "",
                "## Top Nuclide/Volume Row",
                "",
                f"- Broad-window top row: `{top['nuclide']}` in `{top['source_volume_proxy']}` / `{top['geometry_group']}`, final `{fmt(top['broad_480_550_final_cps'])}` cps.",
            ]
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `dixe_delayed_geometry_by_volume.csv`",
            "- `dixe_delayed_geometry_by_group.csv`",
            "- `dixe_delayed_top_nuclide_volume.csv`",
            "- `dixe_component_stage_rates.csv`",
            "- `dixe_delayed_time_evolution.csv`",
            "- `dixe_physical_activation_inventory_by_group.csv`",
            "- `dixe_delayed_geometry_group_broad_480_550.png`",
            "- `dixe_delayed_geometry_group_line_510p3_511p8.png`",
            "- `dixe_delayed_volume_top20_broad_480_550.png`",
            "- `dixe_delayed_volume_top20_line_510p3_511p8.png`",
            "- `dixe_component_stage_rates.png`",
            "- `dixe_delayed_time_evolution_proxy.png`",
            "- `dixe_physical_activation_inventory_by_group.png`",
            "- `summary.json`",
            "",
            "## Limits",
            "",
            "- This is not a full DIXE Fig.11 reproduction because the local final-event table does not retain complete particle-type and production-process ancestry for each final TES hit.",
            "- `source_volume_proxy` is a useful transport/first-hit diagnostic, but it is not an exact decay-source block identity.",
            "- The time plot is the balloon activation time series, not DIXE SAA decay timing.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    delayed_rows = read_csv(DELAYED_BY_VOLUME)
    volume_rows, group_rows, top_rows = aggregate_delayed(delayed_rows)
    component_rows = build_component_stage_rows()
    time_rows = build_time_rows()
    physical_activity_rows = build_physical_activity_rows()

    write_csv(OUT / "dixe_delayed_geometry_by_volume.csv", volume_rows)
    write_csv(OUT / "dixe_delayed_geometry_by_group.csv", group_rows)
    write_csv(OUT / "dixe_delayed_top_nuclide_volume.csv", top_rows)
    write_csv(OUT / "dixe_component_stage_rates.csv", component_rows)
    write_csv(OUT / "dixe_delayed_time_evolution.csv", time_rows)
    write_csv(OUT / "dixe_physical_activation_inventory_by_group.csv", physical_activity_rows)
    make_plots(volume_rows, group_rows, component_rows, time_rows, physical_activity_rows)

    summary = build_summary(volume_rows, group_rows, top_rows, component_rows, time_rows, physical_activity_rows)
    write_json(OUT / "summary.json", summary)
    write_readme(summary, group_rows, top_rows, physical_activity_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
