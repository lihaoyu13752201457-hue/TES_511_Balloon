#!/usr/bin/env python3
"""Build a non-authoritative SF3 W2 background interaction-route diagnostic.

This diagnostic reuses the selected-event block parsing and IA parent/child
route construction from
``old/reports/prompt511_entry_audit_20260617/
build_prompt511_track_interaction_figure.py``.  It opens only the explicitly
named fresh-SF3 SIM files referenced by the canonical Stage04 selected-lineage
table, stops after all requested event IDs have been found, and never hashes a
SIM payload.  It does not rerun transport and is not a replacement for the
Stage04/Stage06 rate authorities.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]
LINEAGE = PACKAGE / "outputs/04_common_response/selected_background_w2_lineage.csv"
DELAYED_CATALOG_ROOT = PACKAGE / "outputs/03_delayed/catalog/SF3"
OUT = PACKAGE / "diagnostics/sf3_background_routes_2d"
JSON_OUT = OUT / "sf3_background_routes_2d.json"
CSV_OUT = OUT / "sf3_background_route_vertices.csv"
PNG_OUT = OUT / "sf3_background_routes_axial_radius.png"
SVG_OUT = OUT / "sf3_background_routes_axial_radius.svg"

REUSED_ALGORITHM = (
    REPO
    / "old/reports/prompt511_entry_audit_20260617/"
    "build_prompt511_track_interaction_figure.py"
)

FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>[^\s]+)")
IA_RE = re.compile(r"^IA\s+(?P<proc>\S+)\s+(?P<body>.*)$")
CC_RE = re.compile(r"^CC\s+HIT\s+(?P<volume>\S+)\s+(?P<body>.*)$")
ID_RE = re.compile(r"^ID\s+(?P<id>\d+)")
TP_RE = re.compile(r"^TP_L\d+_\d+$", re.IGNORECASE)

# Frozen InstrumentFrame inverse world rotation from the SF3 mesh authority.
SQRT_HALF = math.sqrt(0.5)
INSTRUMENT_FROM_WORLD = (
    (SQRT_HALF, 0.0, -SQRT_HALF),
    (0.0, 1.0, 0.0),
    (SQRT_HALF, 0.0, SQRT_HALF),
)

SIDE_X0, SIDE_X1 = -4.3575, 4.305
SIDE_RIN, SIDE_ROUT = 4.205, 4.495
FRONT_X0, FRONT_X1 = -4.6475, -4.3575
REAR_X0, REAR_X1 = 4.305, 4.595
REAR_RIN, CAP_ROUT = 1.85, 4.495
WINDOW_HALF = 1.9
CENTER_Z = -5.2

KEY_PROCESSES = {"DECA", "PAIR", "ANNI", "RAYL", "COMP", "PHOT", "BREM"}
PROCESS_COLORS = {
    "DECA": "#7B61A8",
    "PAIR": "#5B9F3A",
    "ANNI": "#B84E8C",
    "RAYL": "#3E657B",
    "COMP": "#E88955",
    "PHOT": "#D1A900",
    "BREM": "#6C7480",
}
PROCESS_MARKERS = {
    "DECA": "P",
    "PAIR": "D",
    "ANNI": "*",
    "RAYL": "x",
    "COMP": "o",
    "PHOT": "s",
    "BREM": "^",
}
PROMPT_EVENT_COLORS = {
    54078: "#D55E00",
    256781: "#0072B2",
    13313: "#009E73",
}
FAMILY_COLORS = {
    "p": "#4C78A8",
    "n": "#72B7B2",
    "alpha": "#F58518",
    "gamma": "#E45756",
    "eminus": "#B279A2",
    "eplus": "#FF9DA6",
    "muminus": "#9D755D",
    "muplus": "#BAB0AC",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def world_to_instrument(point: Iterable[float]) -> tuple[float, float, float]:
    x, y, z = (float(value) for value in point)
    return (
        SQRT_HALF * x - SQRT_HALF * z,
        y,
        SQRT_HALF * x + SQRT_HALF * z,
    )


def axial_radius(point: Iterable[float]) -> tuple[float, float, float, float]:
    xp, yp, zp = world_to_instrument(point)
    zc = zp - CENTER_Z
    return xp, math.hypot(yp, zc), yp, zc


def sf3_w_region(point: Iterable[float]) -> str:
    xp, radius, yp, zc = axial_radius(point)
    if (
        FRONT_X0 <= xp <= FRONT_X1
        and radius <= CAP_ROUT
        and not (abs(yp) <= WINDOW_HALF and abs(zc) <= WINDOW_HALF)
    ):
        return "SF3_W_NearField_FrontWindowPlate_2p9mm"
    if SIDE_X0 <= xp <= SIDE_X1 and SIDE_RIN <= radius <= SIDE_ROUT:
        return "SF3_W_NearField_SideSleeve_2p9mm"
    if REAR_X0 <= xp <= REAR_X1 and REAR_RIN <= radius <= CAP_ROUT:
        return "SF3_W_NearField_RearColdFingerAnnulus_2p9mm"
    return "OUTSIDE_NEW_SF3_W"


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_wanted_blocks(path: Path, wanted: set[int]):
    current_id: int | None = None
    block: list[str] = []
    found: set[int] = set()
    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                if current_id in wanted:
                    found.add(int(current_id))
                    yield int(current_id), block
                    if found == wanted:
                        return
                current_id = None
                block = []
                continue
            match = ID_RE.match(line)
            if match:
                current_id = int(match.group("id"))
            if current_id in wanted:
                block.append(line)
    if current_id in wanted and current_id not in found:
        yield int(current_id), block


def parse_float(value: str, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_ia(line: str) -> dict[str, Any] | None:
    match = IA_RE.match(line)
    if not match:
        return None
    fields = [part.strip() for part in match.group("body").split(";")]
    if len(fields) < 7:
        return None
    try:
        ia_id = int(fields[0])
        parent_id = int(fields[1])
        point = (float(fields[4]), float(fields[5]), float(fields[6]))
    except (TypeError, ValueError):
        return None
    xp, radius, yp, zc = axial_radius(point)
    return {
        "process": match.group("proc").upper(),
        "ia_id": ia_id,
        "parent_id": parent_id,
        "time_s": parse_float(fields[3]),
        "world_cm": list(point),
        "xprime_cm": xp,
        "radius_cm": radius,
        "yprime_cm": yp,
        "z_centered_cm": zc,
        "new_w_region": sf3_w_region(point),
        "last_energy_keV": parse_float(fields[-1]),
    }


def parse_cc(line: str) -> dict[str, Any] | None:
    match = CC_RE.match(line)
    if not match:
        return None
    fields = {item.group("key"): item.group("value") for item in FIELD_RE.finditer(line)}
    point = (
        parse_float(fields.get("x", "")),
        parse_float(fields.get("y", "")),
        parse_float(fields.get("z", "")),
    )
    if not all(math.isfinite(value) for value in point):
        return None
    xp, radius, yp, zc = axial_radius(point)
    return {
        "volume": match.group("volume"),
        "edep_keV": parse_float(fields.get("edep_keV", ""), 0.0),
        "world_cm": list(point),
        "xprime_cm": xp,
        "radius_cm": radius,
        "yprime_cm": yp,
        "z_centered_cm": zc,
        "time_s": parse_float(fields.get("t", "")),
        "secondary": fields.get("sec", ""),
        "secondary_process": fields.get("sproc", ""),
        "creator_process": fields.get("cproc", ""),
    }


def load_delayed_production_lookup() -> dict[tuple[str, int], dict[str, Any]]:
    lookup: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(DELAYED_CATALOG_ROOT.glob("*.pkl")):
        with path.open("rb") as handle:
            catalog = pickle.load(handle)
        for index, local_id in enumerate(catalog.get("local_id", [])):
            source_file = str(catalog["source_file"][index])
            point = (
                float(catalog["production_x_cm"][index]),
                float(catalog["production_y_cm"][index]),
                float(catalog["production_z_cm"][index]),
            )
            xp, radius, yp, zc = axial_radius(point)
            lookup[(source_file, int(local_id))] = {
                "world_cm": list(point),
                "xprime_cm": xp,
                "radius_cm": radius,
                "yprime_cm": yp,
                "z_centered_cm": zc,
                "source_volume": str(catalog["source_volume"][index]),
                "source_parent_ZA": int(catalog["source_parent_ZA"][index]),
                "new_w_region": sf3_w_region(point),
            }
    return lookup


def parse_event(
    row: dict[str, str],
    block: list[str],
    production_lookup: dict[tuple[str, int], dict[str, Any]],
) -> dict[str, Any]:
    interactions = [value for line in block if (value := parse_ia(line)) is not None]
    hits = [value for line in block if (value := parse_cc(line)) is not None]
    tes_hits = [hit for hit in hits if TP_RE.match(str(hit["volume"]))]
    tes_edep = math.fsum(float(hit["edep_keV"]) for hit in tes_hits)
    if tes_edep <= 0.0:
        raise RuntimeError(f"selected event has no positive TES deposit: {row['source_file']}:{row['local_event_id']}")
    tes_world = [
        math.fsum(float(hit["edep_keV"]) * float(hit["world_cm"][axis]) for hit in tes_hits)
        / tes_edep
        for axis in range(3)
    ]
    tx, tr, ty, tz = axial_radius(tes_world)
    tes = {
        "world_cm": tes_world,
        "xprime_cm": tx,
        "radius_cm": tr,
        "yprime_cm": ty,
        "z_centered_cm": tz,
        "raw_edep_keV": tes_edep,
        "pixels": sorted({str(hit["volume"]) for hit in tes_hits}),
    }
    by_id = {int(item["ia_id"]): item for item in interactions}
    segments = []
    for item in interactions:
        if item["process"] in {"INIT", "ESCP"}:
            continue
        parent = by_id.get(int(item["parent_id"]))
        if parent is None or parent["process"] == "ESCP":
            continue
        segments.append({
            "process": item["process"],
            "x0_cm": float(parent["xprime_cm"]),
            "r0_cm": float(parent["radius_cm"]),
            "x1_cm": float(item["xprime_cm"]),
            "r1_cm": float(item["radius_cm"]),
        })
    source_file = str(row["source_file"])
    local_id = int(row["local_event_id"])
    production = production_lookup.get((source_file, local_id))
    if row["stream"] == "delayed" and production is None:
        raise RuntimeError(f"missing exact production position: {source_file}:{local_id}")
    return {
        "stream": str(row["stream"]),
        "family": str(row["family"]),
        "local_event_id": local_id,
        "job_name": str(row["job_name"]),
        "source_file": source_file,
        "measured_total_keV": float(row["measured_total_keV"]),
        "event_weight_cps": float(row["event_weight_cps"]),
        "source_volume": str(row.get("source_volume", "")),
        "production": production,
        "interactions": interactions,
        "segments": segments,
        "tes": tes,
        "active_veto_edep_keV": float(row["shield_keV"]) + float(row["plastic_keV"]),
        "new_w_recorded_edep_keV": float(row["passive_w_keV"]),
    }


def draw_w(ax) -> None:
    style = {"facecolor": "#6B7078", "edgecolor": "#3E4248", "alpha": 0.24, "lw": 0.9}
    ax.add_patch(Rectangle((SIDE_X0, SIDE_RIN), SIDE_X1 - SIDE_X0, SIDE_ROUT - SIDE_RIN, **style))
    ax.add_patch(Rectangle((FRONT_X0, 0.0), FRONT_X1 - FRONT_X0, CAP_ROUT, **style))
    ax.add_patch(Rectangle((REAR_X0, REAR_RIN), REAR_X1 - REAR_X0, CAP_ROUT - REAR_RIN, **style))
    ax.text((SIDE_X0 + SIDE_X1) / 2, 4.66, "new W side sleeve", ha="center", va="bottom", fontsize=8)
    ax.text((FRONT_X0 + FRONT_X1) / 2, 7.6, "front W", rotation=90, ha="center", va="center", fontsize=7.5)
    ax.text((REAR_X0 + REAR_X1) / 2, 7.6, "rear W", rotation=90, ha="center", va="center", fontsize=7.5)


def draw_panel(ax, events: list[dict[str, Any]], stream: str) -> None:
    draw_w(ax)
    for event in events:
        color = (
            PROMPT_EVENT_COLORS.get(int(event["local_event_id"]), "#222222")
            if stream == "prompt"
            else FAMILY_COLORS.get(str(event["family"]), "#777777")
        )
        for segment in event["segments"]:
            if max(segment["x0_cm"], segment["x1_cm"]) < -12.0 or min(segment["x0_cm"], segment["x1_cm"]) > 8.0:
                continue
            ax.plot(
                [segment["x0_cm"], segment["x1_cm"]],
                [segment["r0_cm"], segment["r1_cm"]],
                color=color,
                lw=0.9 if stream == "prompt" else 0.38,
                alpha=0.62 if stream == "prompt" else 0.14,
                zorder=3,
            )
        for point in event["interactions"]:
            process = str(point["process"])
            if process not in KEY_PROCESSES or not (-12.0 <= float(point["xprime_cm"]) <= 8.0):
                continue
            ax.scatter(
                [point["xprime_cm"]],
                [point["radius_cm"]],
                s=34 if process == "ANNI" else 19,
                marker=PROCESS_MARKERS[process],
                c=PROCESS_COLORS[process],
                edgecolors="white" if PROCESS_MARKERS[process] not in {"x"} else PROCESS_COLORS[process],
                linewidths=0.35,
                alpha=0.88 if stream == "prompt" else 0.48,
                zorder=6,
            )
        if event.get("production") is not None:
            source = event["production"]
            ax.scatter([source["xprime_cm"]], [source["radius_cm"]], s=13, marker="+", c=color, alpha=0.55, zorder=7)
        tes = event["tes"]
        ax.scatter([tes["xprime_cm"]], [tes["radius_cm"]], s=24, marker="o", c="#00A6D6", edgecolors="white", linewidths=0.5, zorder=8)
        if stream == "prompt":
            ax.annotate(
                str(event["local_event_id"]),
                (float(tes["xprime_cm"]), float(tes["radius_cm"])),
                xytext=(4, 4), textcoords="offset points", fontsize=7.2, color=color,
            )
    ax.set_xlim(-12.0, 8.0)
    ax.set_ylim(0.0, 12.0)
    ax.set_xlabel("Instrument axial coordinate x′ [cm]")
    ax.set_ylabel("Radius from W axis r [cm]")
    ax.grid(True, color="#D8DDE3", lw=0.45, alpha=0.7)
    ax.set_aspect("equal", adjustable="box")


def write_outputs(events: list[dict[str, Any]], sim_scans: list[dict[str, Any]]) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    prompt = [event for event in events if event["stream"] == "prompt"]
    delayed = [event for event in events if event["stream"] == "delayed"]
    prompt_pair_regions = Counter(
        point["new_w_region"]
        for event in prompt
        for point in event["interactions"]
        if point["process"] == "PAIR"
    )
    prompt_pair_event_regions = Counter()
    for event in prompt:
        regions = {
            point["new_w_region"]
            for point in event["interactions"]
            if point["process"] == "PAIR"
        }
        for region in regions:
            prompt_pair_event_regions[region] += 1
    delayed_source_regions = Counter(
        event["production"]["new_w_region"] for event in delayed if event.get("production")
    )
    payload = {
        "status": "PASS__SF3_SELECTED_W2_BACKGROUND_2D_ROUTE_DIAGNOSTIC",
        "authority_boundary": "DIAGNOSTIC_ONLY__RATE_AUTHORITY_REMAINS_STAGE04_AND_STAGE06",
        "sim_access": {
            "fresh_sf3_named_sim_files_opened": len(sim_scans),
            "historical_se3_or_s3d_sim_opened": False,
            "sim_payload_hashes_computed": False,
            "transport_rerun": False,
            "scans": sim_scans,
        },
        "inputs": {
            "selected_lineage": str(LINEAGE),
            "reused_parser_and_route_algorithm": str(REUSED_ALGORITHM),
        },
        "geometry_projection": {
            "coordinate_system": "InstrumentFrame xprime versus r=hypot(yprime,zprime+5.2)",
            "front_square_window_note": "front W rectangle in axial-radius view is a projection; point membership uses exact |y|<=1.9 and |z+5.2|<=1.9 square cut",
        },
        "summary": {
            "selected_events": len(events),
            "prompt_selected_events": len(prompt),
            "delayed_selected_events": len(delayed),
            "prompt_pair_vertex_rows_by_region": dict(sorted(prompt_pair_regions.items())),
            "prompt_events_with_pair_by_region": dict(sorted(prompt_pair_event_regions.items())),
            "delayed_selected_source_positions_by_region": dict(sorted(delayed_source_regions.items())),
            "delayed_selected_families": dict(sorted(Counter(event["family"] for event in delayed).items())),
        },
        "events": events,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for event in events:
        for point in event["interactions"]:
            rows.append({
                "stream": event["stream"],
                "family": event["family"],
                "job_name": event["job_name"],
                "local_event_id": event["local_event_id"],
                "point_kind": "IA",
                "process": point["process"],
                "ia_id": point["ia_id"],
                "parent_id": point["parent_id"],
                "xprime_cm": point["xprime_cm"],
                "radius_cm": point["radius_cm"],
                "yprime_cm": point["yprime_cm"],
                "z_centered_cm": point["z_centered_cm"],
                "new_w_region": point["new_w_region"],
            })
        if event.get("production") is not None:
            point = event["production"]
            rows.append({
                "stream": event["stream"], "family": event["family"],
                "job_name": event["job_name"], "local_event_id": event["local_event_id"],
                "point_kind": "PRODUCTION", "process": "SOURCE", "ia_id": "", "parent_id": "",
                "xprime_cm": point["xprime_cm"], "radius_cm": point["radius_cm"],
                "yprime_cm": point["yprime_cm"], "z_centered_cm": point["z_centered_cm"],
                "new_w_region": point["new_w_region"],
            })
        point = event["tes"]
        rows.append({
            "stream": event["stream"], "family": event["family"],
            "job_name": event["job_name"], "local_event_id": event["local_event_id"],
            "point_kind": "TES", "process": "TES", "ia_id": "", "parent_id": "",
            "xprime_cm": point["xprime_cm"], "radius_cm": point["radius_cm"],
            "yprime_cm": point["yprime_cm"], "z_centered_cm": point["z_centered_cm"],
            "new_w_region": "TES",
        })
    with CSV_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 11.0, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 7.0), constrained_layout=True)
    draw_panel(axes[0], prompt, "prompt")
    axes[0].set_title("SF3 final-W2 prompt routes: 3 selected gamma events")
    draw_panel(axes[1], delayed, "delayed")
    axes[1].set_title("SF3 final-W2 delayed routes: 53 selected events")
    handles = [
        Line2D([0], [0], marker=PROCESS_MARKERS[p], color="none", markerfacecolor=PROCESS_COLORS[p],
               markeredgecolor=PROCESS_COLORS[p], label=p, markersize=6)
        for p in ("DECA", "PAIR", "ANNI", "RAYL", "COMP", "PHOT")
    ]
    handles.extend([
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#00A6D6", markeredgecolor="white", label="TES", markersize=6),
        Line2D([0], [0], marker="+", color="#555555", label="delayed production position", markersize=7),
    ])
    fig.legend(handles=handles, loc="lower center", ncol=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("SF3 selected 510.58–511.42 keV background interaction routes", fontsize=14)
    fig.savefig(PNG_OUT, dpi=220)
    fig.savefig(SVG_OUT)
    plt.close(fig)
    return payload


def main() -> int:
    if not LINEAGE.is_file():
        raise RuntimeError(f"missing selected lineage: {LINEAGE}")
    rows = read_csv(LINEAGE)
    if len(rows) != 56:
        raise RuntimeError(f"expected 56 selected W2 rows, found {len(rows)}")
    production_lookup = load_delayed_production_lookup()
    wanted_by_file: dict[str, set[int]] = defaultdict(set)
    row_by_key: dict[tuple[str, int], dict[str, str]] = {}
    for row in rows:
        key = (str(row["source_file"]), int(row["local_event_id"]))
        if key in row_by_key:
            raise RuntimeError(f"duplicate selected lineage identity: {key}")
        row_by_key[key] = row
        wanted_by_file[key[0]].add(key[1])

    events: list[dict[str, Any]] = []
    scans: list[dict[str, Any]] = []
    for source_file, wanted in sorted(wanted_by_file.items()):
        path = Path(source_file)
        if not path.is_file():
            raise RuntimeError(f"missing named fresh SF3 SIM: {path}")
        found: set[int] = set()
        for local_id, block in iter_wanted_blocks(path, wanted):
            events.append(parse_event(row_by_key[(source_file, local_id)], block, production_lookup))
            found.add(local_id)
        missing = wanted - found
        if missing:
            raise RuntimeError(f"missing target event blocks in {path}: {sorted(missing)}")
        scans.append({
            "source_file": source_file,
            "target_event_ids": sorted(wanted),
            "found_event_ids": sorted(found),
            "stopped_after_target_event_id": max(wanted),
        })
    events.sort(key=lambda event: (event["stream"], event["family"], event["job_name"], event["local_event_id"]))
    payload = write_outputs(events, scans)
    print(json.dumps({
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(JSON_OUT),
        "csv": str(CSV_OUT),
        "png": str(PNG_OUT),
        "svg": str(SVG_OUT),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
