#!/usr/bin/env python3
"""Build event-level material ledgers for prompt e+ 511 leakage diagnostics.

The SIM files provide interaction points and CC hit volumes, not a full
boundary-step history.  The path lengths reported here are therefore
interaction-to-interaction straight-line distances, grouped by the material at
the downstream interaction point.  They are a diagnostic proxy for where the
511 branches interact/terminate, not exact geometric chord lengths through
every passive volume.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_prompt511_prompt_incidence_figure as base  # noqa: E402
import build_prompt511_track_interaction_figure as track  # noqa: E402


ROOT = base.ROOT
OUTDIR = base.OUTDIR

EVENT_CSV = OUTDIR / "prompt511_material_ledger_events.csv"
SEGMENT_CSV = OUTDIR / "prompt511_material_ledger_segments.csv"
SUMMARY_JSON = OUTDIR / "prompt511_material_ledger_summary.json"
REPORT_MD = OUTDIR / "prompt511_material_ledger.md"
PNG_PATH = OUTDIR / "prompt511_material_path_stacks.png"
SVG_PATH = OUTDIR / "prompt511_material_path_stacks.svg"

SHIELDED_MAX_PER_CASE = track.SHIELD_MAX_PER_CASE
SELECTED_MAX_PER_CASE = track.SELECTED_TRACK_MAX_PER_CASE
PLOT_EVENTS_PER_PANEL = 12
REPORT_EVENTS_PER_GROUP = 12
NEAREST_CC_MAX_CM = 0.35
MAX_LOCAL_SEGMENT_CM = 120.0

MATERIAL_ORDER = [
    "Ta/TES",
    "CsI",
    "Aluminium",
    "Copper",
    "W",
    "Be",
    "Kapton",
    "StainlessSteel",
    "LowCarbonSteel",
    "other",
    "unknown",
]

MATERIAL_COLOR = {
    "Ta/TES": "#5477C4",
    "CsI": "#A3D576",
    "Aluminium": "#A3BEFA",
    "Copper": "#F0986E",
    "W": "#464C55",
    "Be": "#BEEB96",
    "Kapton": "#F390CA",
    "StainlessSteel": "#A7ADB8",
    "LowCarbonSteel": "#7A828F",
    "other": "#C5CAD3",
    "unknown": "#E2E5EA",
}

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def dist3(a: dict, b: dict) -> float:
    return math.sqrt((a["xp"] - b["xp"]) ** 2 + (a["yp"] - b["yp"]) ** 2 + (a["zp"] - b["zp"]) ** 2)


def compact_counter(counter: dict[str, float], *, digits: int = 3, max_items: int = 5) -> str:
    items = [(k, v) for k, v in counter.items() if v > 0]
    items.sort(key=lambda kv: (-kv[1], MATERIAL_ORDER.index(kv[0]) if kv[0] in MATERIAL_ORDER else 999))
    if not items:
        return ""
    return "; ".join(f"{k}:{v:.{digits}g}" for k, v in items[:max_items])


def compact_sequence(labels: Iterable[str], *, max_items: int = 6) -> str:
    seq: list[str] = []
    last = None
    for label in labels:
        if not label or label == last:
            continue
        seq.append(label)
        last = label
    if len(seq) > max_items:
        return " -> ".join(seq[:max_items]) + " -> ..."
    return " -> ".join(seq)


def nearest_cc(ia: dict, cc_hits: list[dict]) -> tuple[dict | None, float]:
    best = None
    best_dist = float("inf")
    for cc in cc_hits:
        if not (finite(cc.get("xp")) and finite(cc.get("yp")) and finite(cc.get("zp"))):
            continue
        d = dist3(ia, cc)
        if d < best_dist:
            best = cc
            best_dist = d
    if best is not None and best_dist <= NEAREST_CC_MAX_CM:
        return best, best_dist
    return None, best_dist


def annotate_ia_volumes(event: dict) -> None:
    for ia in event["ias"]:
        cc, d = nearest_cc(ia, event["cc_hits"])
        if cc is None:
            ia["nearest_volume"] = ""
            ia["nearest_material"] = "unknown"
            ia["nearest_cc_distance_cm"] = d
        else:
            ia["nearest_volume"] = cc["volume"]
            ia["nearest_material"] = cc["material"]
            ia["nearest_cc_distance_cm"] = d


def ia_has_anni_ancestor(ia: dict, by_id: dict[int, dict], memo: dict[int, bool]) -> bool:
    ia_id = ia["ia_id"]
    if ia_id in memo:
        return memo[ia_id]
    parent = by_id.get(ia["parent_id"])
    if parent is None:
        memo[ia_id] = False
    elif parent["proc"] == "ANNI":
        memo[ia_id] = True
    else:
        memo[ia_id] = ia_has_anni_ancestor(parent, by_id, memo)
    return memo[ia_id]


def event_segments(event: dict) -> list[dict]:
    by_id = {ia["ia_id"]: ia for ia in event["ias"]}
    memo: dict[int, bool] = {}
    rows = []
    for ia in event["ias"]:
        if ia["proc"] in {"INIT", "ANNI"}:
            continue
        parent = by_id.get(ia["parent_id"])
        if parent is None:
            continue
        if not (parent["proc"] == "ANNI" or ia_has_anni_ancestor(ia, by_id, memo)):
            continue
        if ia["proc"] == "ESCP":
            continue
        if not all(finite(v) for v in (parent["xp"], parent["yp"], parent["zp"], ia["xp"], ia["yp"], ia["zp"])):
            continue
        length = math.sqrt((ia["xp"] - parent["xp"]) ** 2 + (ia["yp"] - parent["yp"]) ** 2 + (ia["zp"] - parent["zp"]) ** 2)
        if not finite(length) or length <= 0.0 or length > MAX_LOCAL_SEGMENT_CM:
            continue
        material = ia.get("nearest_material") or "unknown"
        rows.append(
            {
                "case": event["case"],
                "cohort": event["event_kind"],
                "source_file": event["source_file"],
                "local_id": event["local_id"],
                "parent_ia_id": parent["ia_id"],
                "child_ia_id": ia["ia_id"],
                "parent_process": parent["proc"],
                "child_process": ia["proc"],
                "length_cm": length,
                "endpoint_material": material,
                "endpoint_volume": ia.get("nearest_volume", ""),
                "endpoint_x_cm": ia["xp"],
                "endpoint_y_cm": ia["yp"],
                "endpoint_z_cm": ia["zp"],
                "nearest_cc_distance_cm": ia.get("nearest_cc_distance_cm", float("nan")),
            }
        )
    return rows


def cc_edep_by_material(event: dict) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    for cc in event["cc_hits"]:
        edep = cc.get("edep_keV", 0.0)
        if finite(edep) and edep > 0:
            totals[cc["material"]] += edep
    return dict(totals)


def tes_edep(event: dict) -> float:
    total = 0.0
    for cc in event["cc_hits"]:
        if track.TP_RE.match(cc["volume"]):
            edep = cc.get("edep_keV", 0.0)
            if finite(edep):
                total += edep
    return total


def last_cc(event: dict) -> dict | None:
    hits = [cc for cc in event["cc_hits"] if finite(cc.get("time_s"))]
    if hits:
        return max(hits, key=lambda cc: cc["time_s"])
    return event["cc_hits"][-1] if event["cc_hits"] else None


def top_tes_hit(event: dict) -> dict | None:
    hits = [cc for cc in event["cc_hits"] if track.TP_RE.match(cc["volume"])]
    if not hits:
        return None
    return max(hits, key=lambda cc: cc.get("edep_keV", 0.0) if finite(cc.get("edep_keV", 0.0)) else 0.0)


def stop_summary(event: dict) -> dict:
    tes_hit = top_tes_hit(event)
    if tes_hit is not None:
        return {
            "stop_class": "TES hit",
            "stop_process": "CC_TES",
            "stop_material": "Ta/TES",
            "stop_volume": tes_hit["volume"],
        }

    non_escape = [ia for ia in event["ias"] if ia["proc"] not in {"INIT", "ESCP"} and finite(ia.get("time_s"))]
    last_ia = max(non_escape, key=lambda ia: ia["time_s"]) if non_escape else None
    cc = last_cc(event)
    material = "unknown"
    volume = ""
    if last_ia is not None and last_ia.get("nearest_volume"):
        material = last_ia.get("nearest_material", "unknown")
        volume = last_ia.get("nearest_volume", "")
    elif cc is not None:
        material = cc["material"]
        volume = cc["volume"]

    proc = last_ia["proc"] if last_ia is not None else "unknown"
    if proc == "PHOT":
        cls = "absorbed before TES"
    elif proc in {"COMP", "RAYL", "BREM", "PAIR"}:
        cls = "scattered/no TES"
    else:
        cls = "no TES"
    return {
        "stop_class": cls,
        "stop_process": proc,
        "stop_material": material,
        "stop_volume": volume,
    }


def event_row(event: dict, segment_rows: list[dict], record: dict | None) -> dict:
    length_by_material: defaultdict[str, float] = defaultdict(float)
    endpoint_sequence = []
    for row in segment_rows:
        material = row["endpoint_material"] or "unknown"
        length_by_material[material] += row["length_cm"]
        endpoint_sequence.append(material)
    edep = cc_edep_by_material(event)
    stop = stop_summary(event)
    source_name = Path(event["source_file"]).name
    leakage_class = record.get("side_window_leakage_class", "") if record else ""
    first_primary_volume = record.get("first_primary_volume", "") if record else ""
    last_primary_volume = record.get("last_primary_volume", "") if record else ""
    primary_seq = record.get("primary_volume_sequence_compact", []) if record else []
    return {
        "case": event["case"],
        "cohort": event["event_kind"],
        "source_name": source_name,
        "source_file": event["source_file"],
        "local_id": event["local_id"],
        "leakage_class": leakage_class,
        "has_tes_hit": event["has_tes_hit"],
        "stop_class": stop["stop_class"],
        "stop_process": stop["stop_process"],
        "stop_material": stop["stop_material"],
        "stop_volume": stop["stop_volume"],
        "n_ia": len(event["ias"]),
        "n_cc_hits": len(event["cc_hits"]),
        "n_segments_after_annihilation": len(segment_rows),
        "path_length_total_cm": sum(length_by_material.values()),
        "path_length_by_endpoint_material_cm": compact_counter(length_by_material, digits=3, max_items=8),
        "path_endpoint_material_sequence": compact_sequence(endpoint_sequence, max_items=8),
        "cc_edep_total_keV": sum(edep.values()),
        "cc_edep_by_material_keV": compact_counter(edep, digits=3, max_items=8),
        "shield_edep_keV": event["shield_edep_keV"],
        "tes_edep_keV": tes_edep(event),
        "first_primary_volume": first_primary_volume,
        "last_primary_volume": last_primary_volume,
        "primary_volume_sequence": compact_sequence(primary_seq, max_items=8) if primary_seq else "",
        **{f"path_cm_{mat}": length_by_material.get(mat, 0.0) for mat in MATERIAL_ORDER},
        **{f"edep_keV_{mat}": edep.get(mat, 0.0) for mat in MATERIAL_ORDER},
    }


def collect_selected(case: str, records: list[dict], frame: str) -> tuple[list[dict], dict[tuple[str, int], dict]]:
    wanted_by_file: dict[str, set[int]] = defaultdict(set)
    record_lookup: dict[tuple[str, int], dict] = {}
    for row in records:
        key = (row["source_file"], int(row["local_id"]))
        wanted_by_file[row["source_file"]].add(int(row["local_id"]))
        record_lookup[key] = row

    events = []
    found_by_file: dict[str, set[int]] = defaultdict(set)
    for source_file, wanted in sorted(wanted_by_file.items()):
        for local_id, block in track.iter_sim_blocks(Path(source_file)):
            if local_id not in wanted:
                continue
            key = (source_file, local_id)
            record = record_lookup[key]
            tes = tuple(record["tes_centroid_local_cm"]) if case == "current" else tuple(record["tes_centroid_cm"])
            parsed = track.parse_event_block(block, case, frame, "selected", source_file, local_id, tes)
            annotate_ia_volumes(parsed)
            events.append(parsed)
            found_by_file[source_file].add(local_id)
            if found_by_file[source_file] >= wanted:
                break

    missing = {
        source_file: sorted(wanted_by_file[source_file] - found_by_file.get(source_file, set()))
        for source_file in wanted_by_file
        if wanted_by_file[source_file] - found_by_file.get(source_file, set())
    }
    if missing:
        raise RuntimeError(f"Missing selected SIM event blocks for {case}: {missing}")
    return events, record_lookup


def collect_shielded(case: str, records: list[dict], frame: str, max_events: int) -> list[dict]:
    selected_ids_by_file: dict[str, set[int]] = defaultdict(set)
    for row in records:
        selected_ids_by_file[row["source_file"]].add(int(row["local_id"]))

    xlim, zlim = ((-22.0, 22.0), (-22.0, 22.0)) if case == "current" else ((-16.0, 16.0), (-16.0, 18.0))
    shield_tokens = track.CURRENT_SHIELD_TOKENS if case == "current" else track.OLD_SHIELD_TOKENS
    events = []
    for source_file in sorted(selected_ids_by_file):
        for local_id, block in track.iter_sim_blocks(Path(source_file)):
            if local_id in selected_ids_by_file[source_file]:
                continue
            if any("CC HIT TP_L" in line for line in block):
                continue
            if not any(line.startswith("CC HIT ") and any(token in line for token in shield_tokens) for line in block):
                continue
            if not any(line.startswith("IA ") and not line.startswith("IA INIT") and not line.startswith("IA ESCP") for line in block):
                continue
            parsed = track.parse_event_block(block, case, frame, "shielded_sample", source_file, local_id, None)
            annotate_ia_volumes(parsed)
            if (
                not parsed["has_tes_hit"]
                and parsed["shield_hits"] > 0
                and parsed["shield_edep_keV"] > 0.0
                and track.event_has_side_shield_hit(parsed)
                and track.event_has_visible_ia(parsed, xlim, zlim)
            ):
                events.append(parsed)
                if len(events) >= max_events:
                    return events
    return events


def summarize_group(rows: list[dict]) -> dict:
    if not rows:
        return {}
    stop_counter = Counter(row["stop_material"] for row in rows)
    stop_class_counter = Counter(row["stop_class"] for row in rows)
    length_totals = {mat: sum(float(row[f"path_cm_{mat}"]) for row in rows) for mat in MATERIAL_ORDER}
    edep_totals = {mat: sum(float(row[f"edep_keV_{mat}"]) for row in rows) for mat in MATERIAL_ORDER}
    path_lengths = [float(row["path_length_total_cm"]) for row in rows]
    shield_edep = [float(row["shield_edep_keV"]) for row in rows]
    tes_hits = sum(1 for row in rows if row["has_tes_hit"])
    return {
        "events": len(rows),
        "tes_hit_events": tes_hits,
        "stop_material_counts": dict(stop_counter),
        "stop_class_counts": dict(stop_class_counter),
        "path_length_total_cm_median": statistics.median(path_lengths),
        "path_length_total_cm_sum": sum(path_lengths),
        "shield_edep_keV_median": statistics.median(shield_edep),
        "shield_edep_keV_sum": sum(shield_edep),
        "path_length_by_endpoint_material_cm_sum": {k: v for k, v in length_totals.items() if v > 0},
        "cc_edep_by_material_keV_sum": {k: v for k, v in edep_totals.items() if v > 0},
    }


def choose_representative(rows: list[dict], group: str, limit: int) -> list[dict]:
    filtered = [row for row in rows if row["group"] == group]
    if group == "current_selected":
        non_window = [row for row in filtered if row["leakage_class"] == "non_window_no_window_disk_intersection"]
        filtered = non_window or filtered
    filtered.sort(key=lambda row: (row["source_name"], int(row["local_id"])))
    return filtered[:limit]


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_path_stacks(event_rows: list[dict]) -> None:
    panels = [
        ("old_selected", "Old selected W2 prompt e+", "final W2 selected; axial/top stack"),
        ("current_selected", "Current selected W2 prompt e+", "final W2 selected; non-window side-port paths first"),
        ("old_shielded", "Old no-TES side-region shield sample", "side-material events with no TES hit"),
        ("current_shielded", "Current no-TES side-port shield sample", "side-material events with no TES hit"),
    ]
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "font.family": ["DejaVu Sans", "sans-serif"],
            "font.size": 8.2,
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["ink"],
            "ytick.color": TOKENS["ink"],
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(16.0, 11.5), constrained_layout=False)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.875, bottom=0.105, hspace=0.36, wspace=0.22)
    for ax, (group, title, subtitle) in zip(axes.ravel(), panels):
        sample = choose_representative(event_rows, group, PLOT_EVENTS_PER_PANEL)
        y_labels = [f"{row['source_name'].split('.')[0].replace('Background_eplus_fullsphere20_', '')}:{row['local_id']}" for row in sample]
        y_positions = list(range(len(sample)))
        left = [0.0] * len(sample)
        for mat in MATERIAL_ORDER:
            vals = [float(row[f"path_cm_{mat}"]) for row in sample]
            if not any(v > 0 for v in vals):
                continue
            ax.barh(
                y_positions,
                vals,
                left=left,
                height=0.66,
                color=MATERIAL_COLOR.get(mat, "#C5CAD3"),
                edgecolor="#FFFFFF",
                linewidth=0.35,
                label=mat,
            )
            left = [l + v for l, v in zip(left, vals)]
        ax.set_title(title, loc="left", fontsize=10.8, fontweight="bold", color=TOKENS["ink"], pad=17)
        ax.text(0.0, 1.015, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.1, color=TOKENS["muted"])
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels, fontsize=6.9)
        ax.invert_yaxis()
        ax.set_xlabel("IA-to-IA straight-line length ending in material [cm]")
        ax.grid(True, axis="x", color=TOKENS["grid"], alpha=0.75, lw=0.6)
        ax.grid(False, axis="y")
        for spine in ax.spines.values():
            spine.set_color(TOKENS["axis"])
        xmax = max(left) if left else 1.0
        ax.set_xlim(0, max(1.0, xmax * 1.18))
        for ypos, total, row in zip(y_positions, left, sample):
            label = row["stop_material"] if row["stop_material"] else row["stop_class"]
            ax.text(total + max(xmax * 0.012, 0.05), ypos, label, va="center", ha="left", fontsize=6.9, color=TOKENS["muted"])

    fig.text(
        0.075,
        0.93,
        "Prompt e+ 511 material ledger: selected leakage versus side-region events that stop before TES",
        fontsize=14.5,
        fontweight="bold",
        color=TOKENS["ink"],
        ha="left",
    )
    fig.text(
        0.075,
        0.905,
        "Lengths are SIM interaction-to-interaction chord proxies grouped by downstream interaction material; they are not exact boundary-crossing thicknesses.",
        fontsize=9.2,
        color=TOKENS["muted"],
        ha="left",
    )
    handles = [Patch(facecolor=MATERIAL_COLOR[mat], edgecolor="#FFFFFF", label=mat) for mat in MATERIAL_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=10, frameon=False, fontsize=7.6, bbox_to_anchor=(0.5, 0.022))
    fig.savefig(PNG_PATH, dpi=220)
    fig.savefig(SVG_PATH)
    plt.close(fig)


def md_table(rows: list[dict]) -> str:
    header = "| group | source:id | leak class | primary / key volume | path endpoint material cm | CC edep keV | stop |\n|---|---|---|---|---|---|---|\n"
    lines = []
    for row in rows:
        sid = f"{row['source_name'].split('.')[0].replace('Background_eplus_fullsphere20_', '')}:{row['local_id']}"
        leak = row["leakage_class"].replace("_", " ") if row["leakage_class"] else "-"
        stop = f"{row['stop_class']} / {row['stop_material']} / `{row['stop_volume']}`"
        key_volume = row["primary_volume_sequence"] or row["last_primary_volume"] or row["stop_volume"] or "-"
        lines.append(
            f"| {row['group']} | `{sid}` | {leak} | `{key_volume}` | {row['path_length_by_endpoint_material_cm'] or '-'} | {row['cc_edep_by_material_keV'] or '-'} | {stop} |"
        )
    return header + "\n".join(lines)


def write_report(event_rows: list[dict], summary: dict) -> None:
    reps = []
    for group in ("current_selected", "current_shielded", "old_shielded", "old_selected"):
        reps.extend(choose_representative(event_rows, group, REPORT_EVENTS_PER_GROUP))

    current_selected = summary["groups"]["current_selected"]
    current_shielded = summary["groups"]["current_shielded"]
    old_shielded = summary["groups"]["old_shielded"]
    old_selected = summary["groups"]["old_selected"]

    text = f"""# Prompt 511 Material Ledger

This is a diagnostic companion to `prompt511_entry_audit.md`.

## Scope And Caveat

The SIM files record IA interaction points and CC hit volumes. They do not store a full material-boundary step history. Therefore the "path cm" below is the straight-line distance from one post-annihilation IA point to the next, grouped by the downstream interaction material inferred from the nearest CC hit within `{NEAREST_CC_MAX_CM}` cm. This is useful for seeing where 511 branches interact or terminate, but it is not an exact chord-length integral through every passive boundary.

The selected-event sample is the same round-robin low-ID sample used by the interaction-track figure: up to `{SELECTED_MAX_PER_CASE}` final W2 selected prompt-eplus events per geometry. The side/shield blocked sample uses up to `{SHIELDED_MAX_PER_CASE}` no-TES side-region events per geometry.

## Group Summary

| group | events | TES hits | stop materials | median path cm | median shield edep keV |
|---|---:|---:|---|---:|---:|
| old selected | {old_selected['events']} | {old_selected['tes_hit_events']} | {old_selected['stop_material_counts']} | {old_selected['path_length_total_cm_median']:.3g} | {old_selected['shield_edep_keV_median']:.3g} |
| current selected | {current_selected['events']} | {current_selected['tes_hit_events']} | {current_selected['stop_material_counts']} | {current_selected['path_length_total_cm_median']:.3g} | {current_selected['shield_edep_keV_median']:.3g} |
| old shielded sample | {old_shielded['events']} | {old_shielded['tes_hit_events']} | {old_shielded['stop_material_counts']} | {old_shielded['path_length_total_cm_median']:.3g} | {old_shielded['shield_edep_keV_median']:.3g} |
| current shielded sample | {current_shielded['events']} | {current_shielded['tes_hit_events']} | {current_shielded['stop_material_counts']} | {current_shielded['path_length_total_cm_median']:.3g} | {current_shielded['shield_edep_keV_median']:.3g} |

## Representative Event Ledger

{md_table(reps)}

## Files

- Event ledger CSV: `{EVENT_CSV.relative_to(ROOT)}`
- Segment ledger CSV: `{SEGMENT_CSV.relative_to(ROOT)}`
- Summary JSON: `{SUMMARY_JSON.relative_to(ROOT)}`
- Stack figure PNG: `{PNG_PATH.relative_to(ROOT)}`
- Stack figure SVG: `{SVG_PATH.relative_to(ROOT)}`

## Interpretation

Current selected prompt-eplus W2 events should not be read as photons punching through a thick, continuous passive column. Most are born in or near side-port/side-wall materials and then have a short local post-annihilation branch whose first hard endpoint is the TES stack. The side-region no-TES samples show the complementary behavior: the branch terminates in side shield materials, with substantial CC energy deposition and no TP_L hit.

Old `new_geo_re` does not reproduce the same side-port leak topology; the side-region sample is stopped in the solid old side material column, while the old selected W2 events remain tied to the old axial/top-stack geometry.
"""
    REPORT_MD.write_text(text, encoding="utf-8")


def main() -> int:
    old_records = load_json(base.OLD_RECORDS)
    current_records = load_json(base.CURRENT_RECORDS)

    old_selected, old_shielded = track.collect_case("old", old_records, "old_global", (-16.0, 16.0), (-16.0, 18.0))
    current_selected, current_shielded = track.collect_case("current", current_records, "current_local", (-22.0, 22.0), (-22.0, 22.0))
    for event in [*old_selected, *current_selected, *old_shielded, *current_shielded]:
        annotate_ia_volumes(event)
    old_lookup = {(row["source_file"], int(row["local_id"])): row for row in old_records}
    current_lookup = {(row["source_file"], int(row["local_id"])): row for row in current_records}

    all_groups = [
        ("old_selected", old_selected, old_lookup),
        ("current_selected", current_selected, current_lookup),
        ("old_shielded", old_shielded, {}),
        ("current_shielded", current_shielded, {}),
    ]

    event_rows = []
    segment_rows = []
    for group, events, lookup in all_groups:
        for event in events:
            record = lookup.get((event["source_file"], int(event["local_id"])))
            segs = event_segments(event)
            for seg in segs:
                seg["group"] = group
            row = event_row(event, segs, record)
            row["group"] = group
            event_rows.append(row)
            segment_rows.extend(segs)

    write_csv(EVENT_CSV, event_rows)
    write_csv(SEGMENT_CSV, segment_rows)

    summary = {
        "status": "PASS_PROMPT511_MATERIAL_LEDGER",
        "method": {
            "path_length_definition": "Straight-line IA parent-child distance after e+ annihilation, excluding ESCP world-escape legs and grouped by downstream interaction material inferred from nearest CC hit.",
            "nearest_cc_max_cm": NEAREST_CC_MAX_CM,
            "max_local_segment_cm": MAX_LOCAL_SEGMENT_CM,
            "shielded_sample_policy": "No TP_L hit, positive shield/side-material CC edep, side-region shield hit, visible non-INIT/non-ESCP IA point.",
            "shielded_max_per_case": SHIELDED_MAX_PER_CASE,
            "selected_max_per_case": SELECTED_MAX_PER_CASE,
            "selected_sample_policy": "Round-robin low-local-id sample across source files from final W2 selected prompt e+ records, matching prompt511_track_interactions_xz_comparison.",
        },
        "outputs": {
            "event_csv": str(EVENT_CSV.relative_to(ROOT)),
            "segment_csv": str(SEGMENT_CSV.relative_to(ROOT)),
            "report_md": str(REPORT_MD.relative_to(ROOT)),
            "png": str(PNG_PATH.relative_to(ROOT)),
            "svg": str(SVG_PATH.relative_to(ROOT)),
        },
        "groups": {
            group: summarize_group([row for row in event_rows if row["group"] == group])
            for group, _, _ in all_groups
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    plot_path_stacks(event_rows)
    write_report(event_rows, summary)
    print(json.dumps({"status": summary["status"], "outputs": summary["outputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
