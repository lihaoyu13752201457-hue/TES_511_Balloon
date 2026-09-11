#!/usr/bin/env python3
"""Build detailed IA/CC interaction-track diagnostics for prompt e+ 511 events."""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_prompt511_prompt_incidence_figure as base  # noqa: E402


ROOT = base.ROOT
OUTDIR = base.OUTDIR
OLD_RECORDS = base.OLD_RECORDS
CURRENT_RECORDS = base.CURRENT_RECORDS
OLD_BOUNDS = base.OLD_BOUNDS
CURRENT_BOUNDS = base.CURRENT_BOUNDS
SUMMARY_JSON = base.SUMMARY_JSON

PNG_PATH = OUTDIR / "prompt511_track_interactions_xz_comparison.png"
SVG_PATH = OUTDIR / "prompt511_track_interactions_xz_comparison.svg"
CSV_PATH = OUTDIR / "prompt511_track_interaction_points.csv"
META_PATH = OUTDIR / "prompt511_track_interactions_metadata.json"

FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>[^\s]+)")
IA_RE = re.compile(r"^IA\s+(?P<proc>\S+)\s+(?P<body>.*)$")
CC_RE = re.compile(r"^CC\s+HIT\s+(?P<volume>\S+)\s+(?P<body>.*)$")
ID_RE = re.compile(r"^ID\s+(?P<id>\d+)")
TP_RE = re.compile(r"^TP_L\d+_", re.IGNORECASE)

SHIELD_MAX_PER_CASE = 100
SELECTED_TRACK_MAX_PER_CASE = 32

PROCESS_STYLE = {
    "ANNI": {"label": "annihilation", "marker": "*", "color": "#BD569B", "size": 34},
    "COMP": {"label": "Compton", "marker": "o", "color": "#F0986E", "size": 19},
    "PHOT": {"label": "photoelectric", "marker": "s", "color": "#FFE15B", "size": 20},
    "BREM": {"label": "bremsstrahlung", "marker": "^", "color": "#7A828F", "size": 18},
    "PAIR": {"label": "pair", "marker": "D", "color": "#71B436", "size": 20},
    "RAYL": {"label": "Rayleigh", "marker": "x", "color": "#464C55", "size": 18},
}
OTHER_STYLE = {"label": "other IA", "marker": ".", "color": "#464C55", "size": 12}

TRACK_COLOR = {
    "selected": "#5477C4",
    "shielded_sample": "#7A828F",
}

CURRENT_SHIELD_TOKENS = (
    "CsI",
    "Outer_Al_Mechanical_Shell",
    "ActiveShield",
    "Passive_W_Liner",
    "Passive_Cu_Liner",
    "Vacuum_Jacket_Al",
    "side_port",
    "side_wall",
)
OLD_SHIELD_TOKENS = (
    "CsI_Active_Shield",
    "Outer_Al_Mech_Shell",
    "ActiveShield",
    "Passive_W_Outer_Liner",
    "Passive_Cu_Inner_Liner",
    "Vacuum_Jacket_Al",
    "Thermal_60K_Al_Shield",
    "Thermal_4K_Al_Shield",
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_sim_blocks(path: Path):
    cur_id = None
    block: list[str] = []
    with open_text(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line == "SE":
                if block and cur_id is not None:
                    yield cur_id, block
                block = [line]
                cur_id = None
                continue
            block.append(line)
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group("id"))
        if block and cur_id is not None:
            yield cur_id, block


def parse_float(value: str, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_ia(line: str) -> dict | None:
    m = IA_RE.match(line)
    if not m:
        return None
    fields = [part.strip() for part in m.group("body").split(";")]
    if len(fields) < 7:
        return None
    try:
        ia_id = int(fields[0])
        parent_id = int(fields[1])
    except ValueError:
        return None
    return {
        "proc": m.group("proc").upper(),
        "ia_id": ia_id,
        "parent_id": parent_id,
        "time_s": parse_float(fields[3]),
        "x": parse_float(fields[4]),
        "y": parse_float(fields[5]),
        "z": parse_float(fields[6]),
        "raw_last_value": parse_float(fields[-1]) if fields else math.nan,
    }


def parse_cc(line: str) -> dict | None:
    m = CC_RE.match(line)
    if not m:
        return None
    fields = {fm.group("key"): fm.group("value") for fm in FIELD_RE.finditer(line)}
    return {
        "volume": m.group("volume"),
        "edep_keV": parse_float(fields.get("edep_keV", "")),
        "x": parse_float(fields.get("x", "")),
        "y": parse_float(fields.get("y", "")),
        "z": parse_float(fields.get("z", "")),
        "time_s": parse_float(fields.get("t", "")),
        "sec": fields.get("sec", ""),
        "sproc": fields.get("sproc", ""),
        "cproc": fields.get("cproc", ""),
        "prim": fields.get("prim", ""),
        "par": fields.get("par", ""),
    }


def transform(point: Iterable[float], frame: str) -> tuple[float, float, float]:
    if frame == "current_local":
        return base.global_to_current_local(point)
    x, y, z = point
    return (x, y, z)


def material_for_volume(volume: str) -> str:
    if volume.startswith("TP_L"):
        return "Ta/TES"
    if "CsI" in volume:
        return "CsI"
    if "W_" in volume or "_W_" in volume or volume.startswith("W"):
        return "W"
    if "Cu" in volume:
        return "Copper"
    if "Kapton" in volume:
        return "Kapton"
    if "Steel" in volume or "Stainless" in volume:
        return "StainlessSteel"
    if "Be" in volume:
        return "Be"
    if "Al" in volume or "Aluminium" in volume:
        return "Aluminium"
    return "other"


def is_shield_volume(volume: str, case: str) -> bool:
    tokens = CURRENT_SHIELD_TOKENS if case == "current" else OLD_SHIELD_TOKENS
    return any(token in volume for token in tokens)


def parse_event_block(block: list[str], case: str, frame: str, event_kind: str, source_file: str, local_id: int, tes: tuple | None) -> dict:
    ias = []
    cc_hits = []
    has_tes_hit = False
    shield_edep = 0.0
    shield_hits = 0
    for line in block:
        ia = parse_ia(line)
        if ia is not None:
            xp, yp, zp = transform((ia["x"], ia["y"], ia["z"]), frame)
            ia.update({"xp": xp, "yp": yp, "zp": zp})
            ias.append(ia)
            continue
        cc = parse_cc(line)
        if cc is not None:
            xp, yp, zp = transform((cc["x"], cc["y"], cc["z"]), frame)
            cc.update({"xp": xp, "yp": yp, "zp": zp, "material": material_for_volume(cc["volume"])})
            cc_hits.append(cc)
            if TP_RE.match(cc["volume"]):
                has_tes_hit = True
            if is_shield_volume(cc["volume"], case):
                shield_hits += 1
                if math.isfinite(cc["edep_keV"]):
                    shield_edep += cc["edep_keV"]
    return {
        "case": case,
        "event_kind": event_kind,
        "source_file": source_file,
        "local_id": local_id,
        "tes": tes,
        "ias": ias,
        "cc_hits": cc_hits,
        "has_tes_hit": has_tes_hit,
        "shield_hits": shield_hits,
        "shield_edep_keV": shield_edep,
    }


def event_has_visible_ia(event: dict, xlim: tuple[float, float], zlim: tuple[float, float]) -> bool:
    for ia in event["ias"]:
        if ia["proc"] in {"INIT", "ESCP"}:
            continue
        if xlim[0] <= ia["xp"] <= xlim[1] and zlim[0] <= ia["zp"] <= zlim[1]:
            return True
    return False


def event_has_side_shield_hit(event: dict) -> bool:
    """Require no-TES samples to touch the side-line or side-port neighborhood."""
    case = event["case"]
    for cc in event["cc_hits"]:
        if not is_shield_volume(cc["volume"], case):
            continue
        x, z = cc["xp"], cc["zp"]
        if not (math.isfinite(x) and math.isfinite(z)):
            continue
        if case == "current":
            if "side_port" in cc["volume"] or "side_wall" in cc["volume"]:
                return True
            if -21.0 <= x <= -5.0 and -10.5 <= z <= 1.5:
                return True
        else:
            if 7.0 <= abs(x) <= 15.5 and -10.5 <= z <= 1.5:
                return True
    return False


def collect_case(case: str, records: list[dict], frame: str, xlim: tuple[float, float], zlim: tuple[float, float]) -> tuple[list[dict], list[dict]]:
    records = choose_selected_records(records, SELECTED_TRACK_MAX_PER_CASE)
    selected_lookup: dict[tuple[str, int], tuple | None] = {}
    wanted_by_file: dict[str, set[int]] = defaultdict(set)
    for row in records:
        key = (row["source_file"], int(row["local_id"]))
        if case == "current":
            tes = tuple(row["tes_centroid_local_cm"])
        else:
            tes = tuple(row["tes_centroid_cm"])
        selected_lookup[key] = tes
        wanted_by_file[row["source_file"]].add(int(row["local_id"]))

    selected_events: list[dict] = []
    shielded_events: list[dict] = []
    found_by_file: dict[str, set[int]] = defaultdict(set)

    for source_file, wanted in sorted(wanted_by_file.items()):
        path = Path(source_file)
        shield_tokens = CURRENT_SHIELD_TOKENS if case == "current" else OLD_SHIELD_TOKENS
        for local_id, block in iter_sim_blocks(path):
            key = (source_file, local_id)
            is_selected = local_id in wanted
            parsed = None
            if is_selected:
                parsed = parse_event_block(block, case, frame, "selected", source_file, local_id, selected_lookup[key])
                selected_events.append(parsed)
                found_by_file[source_file].add(local_id)
            if len(shielded_events) < SHIELD_MAX_PER_CASE and not is_selected:
                has_tp = any("CC HIT TP_L" in line for line in block)
                if has_tp:
                    continue
                has_shield = any(line.startswith("CC HIT ") and any(token in line for token in shield_tokens) for line in block)
                if not has_shield:
                    continue
                has_track_ia = any(
                    line.startswith("IA ")
                    and not line.startswith("IA INIT")
                    and not line.startswith("IA ESCP")
                    for line in block
                )
                if not has_track_ia:
                    continue
                parsed = parsed or parse_event_block(block, case, frame, "shielded_sample", source_file, local_id, None)
                # No TES hit plus real shield/side material deposition: this is the closest
                # local proxy for "blocked before becoming a W2 TES event".
                if (
                    not parsed["has_tes_hit"]
                    and parsed["shield_hits"] > 0
                    and parsed["shield_edep_keV"] > 0.0
                    and event_has_side_shield_hit(parsed)
                    and event_has_visible_ia(parsed, xlim, zlim)
                ):
                    shielded_events.append(parsed)
            if found_by_file[source_file] >= wanted:
                break

    missing = {
        str(path): sorted(wanted_by_file[path] - found_by_file.get(path, set()))
        for path in wanted_by_file
        if wanted_by_file[path] - found_by_file.get(path, set())
    }
    if missing:
        raise RuntimeError(f"Missing selected SIM event blocks for {case}: {missing}")
    return selected_events, shielded_events


def choose_selected_records(records: list[dict], max_total: int) -> list[dict]:
    """Round-robin low-ID selected records across source files for fast readable plots."""
    by_file: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        by_file[row["source_file"]].append(row)
    for rows in by_file.values():
        rows.sort(key=lambda item: int(item["local_id"]))
    chosen: list[dict] = []
    positions = {source_file: 0 for source_file in by_file}
    files = sorted(by_file)
    while len(chosen) < max_total:
        added = False
        for source_file in files:
            pos = positions[source_file]
            rows = by_file[source_file]
            if pos >= len(rows):
                continue
            chosen.append(rows[pos])
            positions[source_file] = pos + 1
            added = True
            if len(chosen) >= max_total:
                break
        if not added:
            break
    return chosen


def event_segments(event: dict, xlim: tuple[float, float], zlim: tuple[float, float]) -> list[list[tuple[float, float]]]:
    by_id = {ia["ia_id"]: ia for ia in event["ias"]}
    segments = []
    for ia in event["ias"]:
        if ia["proc"] in {"INIT", "ESCP"}:
            continue
        parent = by_id.get(ia["parent_id"])
        if not parent or parent["proc"] in {"INIT", "ESCP"}:
            continue
        x0, z0 = parent["xp"], parent["zp"]
        x1, z1 = ia["xp"], ia["zp"]
        if not (math.isfinite(x0) and math.isfinite(z0) and math.isfinite(x1) and math.isfinite(z1)):
            continue
        # Keep lines that touch the displayed detector region.
        if (
            (xlim[0] <= x0 <= xlim[1] and zlim[0] <= z0 <= zlim[1])
            or (xlim[0] <= x1 <= xlim[1] and zlim[0] <= z1 <= zlim[1])
        ):
            segments.append([(x0, z0), (x1, z1)])
    return segments


def plot_events(ax, events: list[dict], xlim: tuple[float, float], zlim: tuple[float, float], *, show_cc: bool, title_note: str) -> dict:
    event_kind = events[0]["event_kind"] if events else "selected"
    segments = []
    for event in events:
        segments.extend(event_segments(event, xlim, zlim))
    if segments:
        lc = LineCollection(
            segments,
            colors=TRACK_COLOR.get(event_kind, "#7A828F"),
            linewidths=0.48 if event_kind == "selected" else 0.38,
            alpha=0.18 if event_kind == "selected" else 0.105,
            zorder=5,
        )
        ax.add_collection(lc)

    process_points: dict[str, list[tuple[float, float]]] = defaultdict(list)
    cc_points: dict[str, list[tuple[float, float]]] = defaultdict(list)
    tes_points: list[tuple[float, float]] = []
    for event in events:
        if event.get("tes"):
            tes_points.append((event["tes"][0], event["tes"][2]))
        if show_cc:
            for cc in event["cc_hits"]:
                if not is_shield_volume(cc["volume"], event["case"]):
                    continue
                if xlim[0] <= cc["xp"] <= xlim[1] and zlim[0] <= cc["zp"] <= zlim[1]:
                    cc_points[cc["material"]].append((cc["xp"], cc["zp"]))
        for ia in event["ias"]:
            proc = ia["proc"]
            if proc in {"INIT", "ESCP"}:
                continue
            if xlim[0] <= ia["xp"] <= xlim[1] and zlim[0] <= ia["zp"] <= zlim[1]:
                process_points[proc].append((ia["xp"], ia["zp"]))

    for material, points in cc_points.items():
        color = base.MATERIAL_COLOR.get(material, "#C5CAD3")
        ax.scatter(
            [p[0] for p in points],
            [p[1] for p in points],
            s=5,
            marker=".",
            color=color,
            alpha=0.16,
            linewidth=0,
            zorder=6,
        )

    for proc, points in sorted(process_points.items()):
        style = PROCESS_STYLE.get(proc, OTHER_STYLE)
        kwargs = {
            "s": style["size"],
            "marker": style["marker"],
            "color": style["color"],
            "linewidth": 0.7 if style["marker"] == "x" else 0.35,
            "alpha": 0.78,
            "zorder": 9,
        }
        if style["marker"] not in {".", "x"}:
            kwargs["edgecolor"] = "white"
        ax.scatter([p[0] for p in points], [p[1] for p in points], **kwargs)

    if tes_points:
        ax.scatter(
            [p[0] for p in tes_points],
            [p[1] for p in tes_points],
            s=14,
            marker="o",
            color=base.COLORS["tes"],
            edgecolor="white",
            linewidth=0.25,
            alpha=0.82,
            zorder=10,
        )

    process_counts = Counter()
    for event in events:
        process_counts.update(ia["proc"] for ia in event["ias"] if ia["proc"] not in {"INIT", "ESCP"})
    shield_edep = sum(float(event["shield_edep_keV"]) for event in events)
    ax.text(
        0.015,
        0.985,
        f"{title_note}\ntracks={len(events)}, IA points={sum(process_counts.values())}, shield edep={shield_edep:.3g} keV",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        color=base.TOKENS["ink"],
        bbox={"boxstyle": "round,pad=0.20", "fc": "white", "ec": "#E2E5EA", "alpha": 0.9},
        zorder=30,
    )
    return {
        "events": len(events),
        "segments": len(segments),
        "process_counts": dict(process_counts),
        "shield_edep_keV": shield_edep,
    }


def write_points_csv(events_by_panel: dict[str, list[dict]]) -> None:
    rows = []
    for panel, events in events_by_panel.items():
        for event in events:
            for ia in event["ias"]:
                if ia["proc"] in {"INIT", "ESCP"}:
                    continue
                rows.append(
                    {
                        "panel": panel,
                        "case": event["case"],
                        "event_kind": event["event_kind"],
                        "source_file": event["source_file"],
                        "local_id": event["local_id"],
                        "ia_id": ia["ia_id"],
                        "parent_id": ia["parent_id"],
                        "process": ia["proc"],
                        "x_plot_cm": ia["xp"],
                        "y_plot_cm": ia["yp"],
                        "z_plot_cm": ia["zp"],
                        "time_s": ia["time_s"],
                    }
                )
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["panel"])
        writer.writeheader()
        writer.writerows(rows)


def legend_handles() -> list:
    handles = []
    for proc in ("ANNI", "COMP", "PHOT", "BREM", "PAIR", "RAYL"):
        style = PROCESS_STYLE[proc]
        handles.append(
            Line2D(
                [0],
                [0],
                marker=style["marker"],
                color="none",
                markerfacecolor=style["color"],
                markeredgecolor="white" if style["marker"] not in {"x"} else style["color"],
                label=style["label"],
                markersize=7,
            )
        )
    handles.extend(
        [
            Line2D([0], [0], color=TRACK_COLOR["selected"], lw=1.1, alpha=0.55, label="selected IA parent-child link"),
            Line2D([0], [0], color=TRACK_COLOR["shielded_sample"], lw=1.1, alpha=0.55, label="no-TES shield sample link"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=base.COLORS["tes"], markeredgecolor="white", label="TES centroid", markersize=6),
            Patch(facecolor=base.COLORS["csi"], edgecolor=base.COLORS["csi"], alpha=0.32, label="CsI/shield geometry"),
        ]
    )
    return handles


def main() -> int:
    old_rows = load_json(OLD_RECORDS)
    current_rows = load_json(CURRENT_RECORDS)
    old_bounds = load_json(OLD_BOUNDS)
    current_bounds = load_json(CURRENT_BOUNDS)
    summary = load_json(SUMMARY_JSON)

    old_xlim, old_zlim = (-16.0, 16.0), (-16.0, 18.0)
    current_xlim, current_zlim = (-22.0, 22.0), (-22.0, 22.0)

    old_selected, old_shielded = collect_case("old", old_rows, "old_global", old_xlim, old_zlim)
    current_selected, current_shielded = collect_case("current", current_rows, "current_local", current_xlim, current_zlim)

    plt.rcParams.update(
        {
            "figure.facecolor": base.TOKENS["surface"],
            "axes.facecolor": base.TOKENS["panel"],
            "font.family": ["DejaVu Sans", "sans-serif"],
            "font.size": 8.7,
            "axes.titlesize": 11.0,
            "axes.titleweight": "bold",
            "axes.labelcolor": base.TOKENS["ink"],
            "xtick.color": base.TOKENS["ink"],
            "ytick.color": base.TOKENS["ink"],
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(16.0, 13.0), constrained_layout=False)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.895, bottom=0.105, hspace=0.18, wspace=0.11)

    panels = [
        (axes[0, 0], "old", "selected", old_selected, old_xlim, old_zlim, "old global x [cm]", "Old selected W2 prompt e+ tracks", False),
        (axes[0, 1], "current", "selected", current_selected, current_xlim, current_zlim, "current local x [cm]", "Current selected W2 prompt e+ tracks", False),
        (axes[1, 0], "old", "shielded", old_shielded, old_xlim, old_zlim, "old global x [cm]", "Old no-TES shield/side-material sample", True),
        (axes[1, 1], "current", "shielded", current_shielded, current_xlim, current_zlim, "current local x [cm]", "Current no-TES shield/side-material sample", True),
    ]

    stats = {}
    for ax, case, kind, events, xlim, zlim, xlabel, title, show_cc in panels:
        base.setup_axes(ax, xlim, zlim, xlabel)
        if case == "old":
            base.draw_old_geometry(ax, old_bounds, summary, annotate=(kind == "selected"))
        else:
            base.draw_current_geometry(ax, current_bounds)
        ax.set_title(title)
        note = "sampled final W2 selected" if kind == "selected" else "sampled no-TES shielded/non-selected"
        stats[f"{case}_{kind}"] = plot_events(ax, events, xlim, zlim, show_cc=show_cc, title_note=note)

    axes[1, 1].annotate(
        "current side-port region:\nside-wall interactions around open bore",
        xy=(-14.0, -5.2),
        xytext=(-21.0, -11.0),
        color="#386411",
        fontsize=8.0,
        arrowprops={"arrowstyle": "->", "color": "#386411", "lw": 1.0},
        zorder=40,
    )

    fig.suptitle(
        "Prompt 511 keV e+ SIM interaction tracks: selected leakage versus no-TES shielded samples",
        fontsize=15.0,
        color=base.TOKENS["ink"],
        y=0.972,
    )
    fig.text(
        0.055,
        0.924,
        "Markers are MEGAlib IA processes (Compton/photoelectric/annihilation/etc.); links follow IA parent-child relations. Bottom panels sample e+ events with shield/side-material energy deposition and no TES hit.",
        fontsize=9.0,
        color=base.TOKENS["muted"],
        ha="left",
    )
    fig.legend(handles=legend_handles(), loc="lower center", ncol=6, frameon=False, fontsize=7.8, bbox_to_anchor=(0.5, 0.018))

    fig.savefig(PNG_PATH, dpi=220)
    fig.savefig(SVG_PATH)
    plt.close(fig)

    events_by_panel = {
        "old_selected": old_selected,
        "current_selected": current_selected,
        "old_shielded_sample": old_shielded,
        "current_shielded_sample": current_shielded,
    }
    write_points_csv(events_by_panel)

    metadata = {
        "status": "PASS_PROMPT511_TRACK_INTERACTION_FIGURE",
        "png": str(PNG_PATH.relative_to(ROOT)),
        "svg": str(SVG_PATH.relative_to(ROOT)),
        "interaction_points_csv": str(CSV_PATH.relative_to(ROOT)),
        "panel_stats": stats,
        "shield_sample_policy": {
            "max_per_case": SHIELD_MAX_PER_CASE,
            "selection": "SIM e+ events not in final selected set, no TP_L TES CC hit, at least one shield/side-material CC HIT with positive edep, and at least one visible non-INIT/non-ESCP IA point",
        },
        "selected_track_sample_policy": {
            "max_per_case": SELECTED_TRACK_MAX_PER_CASE,
            "selection": "round-robin low-local-id sample across source files from the final W2 selected prompt e+ records; rate/count conclusions remain in prompt511_entry_audit_summary.json",
        },
        "coordinate_policy": {
            "old_panels": "old global x-z cm",
            "current_panels": "current v3p5 local side-entry x-z cm, global coordinates rotated by -45 deg about y",
        },
    }
    META_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": metadata["status"], "png": metadata["png"], "svg": metadata["svg"], "csv": metadata["interaction_points_csv"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
