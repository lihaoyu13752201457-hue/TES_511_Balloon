#!/usr/bin/env python3
"""Build reusable SE3-activation + SF3-prompt detailed section diagnostics.

The default path is deliberately lightweight: it consumes the retained SE3
selected-delayed origin CSVs and the already-derived SF3 route JSON.  It does
not open a SIM payload, start transport, or hash a large artifact.

Authority boundary
------------------
* geometry background: validated SE3 native mesh, exact y'=0 section;
* activation markers/statistics: SE3 delayed W2 selected-event origins;
* prompt routes: three SF3 prompt W2 survivor routes;
* SF3 W: passive material only, never drawn or counted as an active veto;
* proposal annotations: design ROIs, not implemented geometry or promotion.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/se3_sf3_activation_prompt_section_tool_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

import se3_section_adapter as local_visual


SCRIPT = Path(__file__).resolve()
TOOL = SCRIPT.parent
PACKAGE = TOOL.parent
REPO = SCRIPT.parents[4]
OUTPUT = TOOL / "outputs"
AUDIT = TOOL / "audit"
INPUTS = TOOL / "inputs"

DEFAULT_SE3_DATA = INPUTS
DEFAULT_ORIGINS = DEFAULT_SE3_DATA / "selected_delayed_event_origins.csv"
DEFAULT_VOLUME_REPORT = DEFAULT_SE3_DATA / "activation_origin_by_volume.csv"
DEFAULT_PARENT_REPORT = DEFAULT_SE3_DATA / "activation_origin_by_parent.csv"
DEFAULT_FAMILY_REPORT = DEFAULT_SE3_DATA / "activation_origin_by_incident_family.csv"

DEFAULT_SE3_VISUAL_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815"
)
DEFAULT_MESH = INPUTS / "se3_geometry_mesh_products.npz"
DEFAULT_SE3_VISUAL_CODE = DEFAULT_SE3_VISUAL_ROOT / "code/build_se3_visuals.py"
DEFAULT_DETAILED_ROUTE_STYLE = (
    REPO
    / "old/reports/prompt511_entry_audit_20260617/"
    "build_prompt511_track_interaction_figure.py"
)
DEFAULT_SF3_ROUTES = INPUTS / "sf3_background_routes_2d.json"
DEFAULT_SF3_ROUTE_BUILDER = Path(
    "/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/49_sf3_plan1_transport_20260816/"
    "code/build_sf3_background_routes_2d.py"
)

# Frozen SF3 coordinate/W contract from build_sf3_background_routes_2d.py.
CENTER_Z = -5.2
SIDE_X0, SIDE_X1 = -4.3575, 4.305
SIDE_RIN, SIDE_ROUT = 4.205, 4.495
FRONT_X0, FRONT_X1 = -4.6475, -4.3575
REAR_X0, REAR_X1 = 4.305, 4.595
REAR_RIN, CAP_ROUT = 1.85, 4.495
WINDOW_HALF = 1.9

NUCLIDE_LABELS = {
    "29061": "Cu-61",
    "29062": "Cu-62",
    "29064": "Cu-64",
    "19038": "K-38",
}
NUCLIDE_COLORS = {
    "Cu-61": "#3B82C4",
    "Cu-62": "#E6862A",
    "Cu-64": "#8B5FBF",
    "K-38": "#45A665",
}
PROMPT_EVENT_COLORS = {
    54078: "#D55E00",
    256781: "#0072B2",
    13313: "#009E73",
}
PROCESS_STYLE = {
    "PAIR": ("D", "#5B9F3A", 31),
    "ANNI": ("*", "#B84E8C", 46),
    "RAYL": ("x", "#285F7A", 32),
    "COMP": ("o", "#E88955", 23),
    "PHOT": ("s", "#D1A900", 10),
    "BREM": ("^", "#6C7480", 13),
}
MXC_VOLUME = "ColdPlate_MXC_50mK_SD_anchor"
BOTTOM_VOLUME = "Cu_50mK_StillLike_Can_bottom_cap_2mm"
L0_VOLUME = "Cu_SubstrateSupport_SolidDisk_L0_deepest"
K4_VOLUME = "ColdPlate_4K"


class ToolError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ToolError(f"empty CSV: {path}")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def nuclide(row: dict[str, str]) -> str:
    za = row["source_parent_ZA"]
    return NUCLIDE_LABELS.get(za, f"ZA={za}")


def weighted_stats(rows: Iterable[dict[str, str]]) -> dict[str, float | int]:
    values = [safe_float(row["event_weight_cps"]) for row in rows]
    rate = math.fsum(values)
    variance = math.fsum(value * value for value in values)
    return {
        "selected_events": len(values),
        "selected_rate_cps": rate,
        "selected_sigma_cps": math.sqrt(variance),
        "selected_Neff": rate * rate / variance if variance else 0.0,
    }


def report_lookup(
    rows: list[dict[str, str]], key: str, *, rate_field: str = "selected_rate_milli_cps"
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        activity = row.get("transported_day15_activity_Bq", row.get("activity_Bq"))
        events = row.get("selected_W2_events", row.get("selected_events"))
        if "selected_W2_rate_cps" in row:
            rate = safe_float(row["selected_W2_rate_cps"])
        else:
            rate = safe_float(row.get(rate_field)) / 1000.0
        result[row[key]] = {
            "activity_Bq": safe_float(activity),
            "report_selected_events": int(safe_float(events)),
            "report_selected_rate_cps": rate,
            "report_selected_rate_share": safe_float(row.get("selected_rate_share")),
        }
    return result


def group_activation(
    origins: list[dict[str, str]],
    key_fn,
    report: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in origins:
        grouped[str(key_fn(row))].append(row)
    total = weighted_stats(origins)["selected_rate_cps"]
    output: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        stats = weighted_stats(rows)
        reference = report.get(key, {})
        output.append(
            {
                "group": key,
                "report_present": key in report,
                "activity_Bq": reference.get("activity_Bq", ""),
                **stats,
                "selected_rate_share": (
                    safe_float(stats["selected_rate_cps"]) / safe_float(total)
                    if total
                    else 0.0
                ),
                "report_event_delta": int(stats["selected_events"])
                - int(reference.get("report_selected_events", stats["selected_events"])),
                "report_rate_delta_cps": safe_float(stats["selected_rate_cps"])
                - safe_float(reference.get("report_selected_rate_cps", stats["selected_rate_cps"])),
            }
        )
    return sorted(
        output,
        key=lambda row: (-safe_float(row["selected_rate_cps"]), row["group"]),
    )


def build_plot_points(origins: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, str]]] = defaultdict(list)
    for row in origins:
        key = (
            nuclide(row),
            row["source_volume"],
            safe_float(row["production_local_x_cm"]),
            safe_float(row["production_local_y_cm"]),
            safe_float(row["production_local_z_cm"]),
        )
        grouped[key].append(row)
    output: list[dict[str, Any]] = []
    for (label, volume, x, y, z), rows in grouped.items():
        stats = weighted_stats(rows)
        output.append(
            {
                "nuclide": label,
                "source_volume": volume,
                "is_MXC": volume == MXC_VOLUME,
                "xprime_cm": x,
                "yprime_cm": y,
                "zprime_cm": z,
                "radius_cm": math.hypot(y, z - CENTER_Z),
                **stats,
            }
        )
    return sorted(
        output,
        key=lambda row: (row["source_volume"], row["nuclide"], row["xprime_cm"], row["zprime_cm"]),
    )


def prompt_events(route_data: dict[str, Any]) -> list[dict[str, Any]]:
    events = [row for row in route_data["events"] if row["stream"] == "prompt"]
    return sorted(events, key=lambda row: int(row["local_event_id"]))


def prompt_event_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        interactions = event["interactions"]
        pairs = [row for row in interactions if row["process"] == "PAIR"]
        rays = [row for row in interactions if row["process"] == "RAYL"]
        w_points = [
            row for row in interactions if row["new_w_region"] != "OUTSIDE_NEW_SF3_W"
        ]
        pair = pairs[0] if pairs else {}
        tes = event.get("tes") or {}
        rows.append(
            {
                "local_event_id": int(event["local_event_id"]),
                "family": event["family"],
                "event_weight_cps": safe_float(event["event_weight_cps"]),
                "measured_total_keV": safe_float(event["measured_total_keV"]),
                "active_veto_edep_keV": safe_float(event["active_veto_edep_keV"]),
                "passive_W_recorded_edep_keV": safe_float(event["new_w_recorded_edep_keV"]),
                "pair_vertex_xprime_cm": pair.get("xprime_cm", ""),
                "pair_vertex_yprime_cm": pair.get("yprime_cm", ""),
                "pair_vertex_zprime_cm": (
                    safe_float(pair["z_centered_cm"]) + CENTER_Z if pair else ""
                ),
                "pair_vertex_radius_cm": pair.get("radius_cm", ""),
                "pair_vertex_region": pair.get("new_w_region", "NO_PAIR"),
                "new_W_interaction_points": len(w_points),
                "new_W_processes": ";".join(
                    sorted({row["process"] for row in w_points})
                ),
                "new_W_Rayleigh_regions": ";".join(
                    sorted({row["new_w_region"] for row in rays if row in w_points})
                ),
                "tes_pixels": ";".join(tes.get("pixels", [])),
                "tes_xprime_cm": tes.get("xprime_cm", ""),
                "tes_yprime_cm": tes.get("yprime_cm", ""),
                "tes_zprime_cm": (
                    safe_float(tes["z_centered_cm"]) + CENTER_Z if tes else ""
                ),
            }
        )
    return rows


def prompt_process_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    event_support: dict[tuple[str, str], set[int]] = defaultdict(set)
    for event in events:
        event_id = int(event["local_event_id"])
        for interaction in event["interactions"]:
            process = interaction["process"]
            if process in {"INIT", "ESCP"}:
                continue
            region = interaction["new_w_region"]
            counts[(process, region)] += 1
            event_support[(process, region)].add(event_id)
    return [
        {
            "process": process,
            "region": region,
            "interaction_points": count,
            "supporting_events": len(event_support[(process, region)]),
        }
        for (process, region), count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def draw_sf3_w_xz(ax: plt.Axes) -> None:
    style = {
        "facecolor": "#3A3A3A",
        "edgecolor": "#111111",
        "alpha": 0.16,
        "hatch": "////",
        "linewidth": 0.75,
        "zorder": 3,
    }
    bands = [
        (FRONT_X0, FRONT_X1, CENTER_Z + WINDOW_HALF, CENTER_Z + CAP_ROUT),
        (FRONT_X0, FRONT_X1, CENTER_Z - CAP_ROUT, CENTER_Z - WINDOW_HALF),
        (SIDE_X0, SIDE_X1, CENTER_Z + SIDE_RIN, CENTER_Z + SIDE_ROUT),
        (SIDE_X0, SIDE_X1, CENTER_Z - SIDE_ROUT, CENTER_Z - SIDE_RIN),
        (REAR_X0, REAR_X1, CENTER_Z + REAR_RIN, CENTER_Z + CAP_ROUT),
        (REAR_X0, REAR_X1, CENTER_Z - CAP_ROUT, CENTER_Z - REAR_RIN),
    ]
    for x0, x1, z0, z1 in bands:
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, **style))


def draw_sf3_w_axial(ax: plt.Axes) -> None:
    style = {
        "facecolor": "#3A3A3A",
        "edgecolor": "#111111",
        "alpha": 0.18,
        "hatch": "////",
        "linewidth": 0.75,
        "zorder": 2,
    }
    ax.add_patch(Rectangle((SIDE_X0, SIDE_RIN), SIDE_X1 - SIDE_X0, SIDE_ROUT - SIDE_RIN, **style))
    ax.add_patch(Rectangle((FRONT_X0, WINDOW_HALF), FRONT_X1 - FRONT_X0, CAP_ROUT - WINDOW_HALF, **style))
    ax.add_patch(Rectangle((REAR_X0, REAR_RIN), REAR_X1 - REAR_X0, CAP_ROUT - REAR_RIN, **style))


def section_bounds(mesh: dict[str, np.ndarray], visual: Any, name: str) -> tuple[float, float, float, float]:
    index = visual.solid_index(mesh, name)
    bounds = mesh["instrument_bounds_per_solid_cm"][index]
    return float(bounds[0, 0]), float(bounds[1, 0]), float(bounds[0, 2]), float(bounds[1, 2])


def draw_design_rois(ax: plt.Axes, mesh: dict[str, np.ndarray], visual: Any) -> None:
    specs = (
        (BOTTOM_VOLUME, "V2A ring-cap / opening ROI", "#D81B60", (5.0, -9.25)),
        (L0_VOLUME, "V2A L0 disk -> open ring", "#9C27B0", (3.7, -5.0)),
        (MXC_VOLUME, "V2B staggered MXC relief ROI", "#C2185B", (0.2, 0.45)),
    )
    for name, label, color, label_position in specs:
        x0, x1, z0, z1 = section_bounds(mesh, visual, name)
        ax.add_patch(
            Rectangle(
                (x0, z0),
                x1 - x0,
                max(z1 - z0, 0.12),
                fill=False,
                edgecolor=color,
                linewidth=1.15,
                linestyle=(0, (4, 2)),
                zorder=14,
            )
        )
        ax.annotate(
            label,
            xy=((x0 + x1) / 2.0, (z0 + z1) / 2.0),
            xytext=label_position,
            textcoords="data",
            color=color,
            fontsize=6.5,
            weight="bold",
            arrowprops={"arrowstyle": "-", "color": color, "lw": 0.7, "alpha": 0.7},
            zorder=25,
        )


def marker_size(rate: float, max_rate: float, count: int = 1) -> float:
    fraction = math.sqrt(rate / max_rate) if max_rate > 0 and rate > 0 else 0.0
    return 18.0 + 92.0 * fraction + 4.0 * math.log1p(max(count - 1, 0))


def draw_activation_points(
    ax: plt.Axes,
    points: list[dict[str, Any]],
    *,
    axial: bool = False,
) -> None:
    max_rate = max(safe_float(row["selected_rate_cps"]) for row in points)
    for label in sorted({row["nuclide"] for row in points}):
        subset = [row for row in points if row["nuclide"] == label]
        xs = [safe_float(row["xprime_cm"]) for row in subset]
        ys = [
            safe_float(row["radius_cm"] if axial else row["zprime_cm"])
            for row in subset
        ]
        sizes = [
            marker_size(
                safe_float(row["selected_rate_cps"]),
                max_rate,
                int(row["selected_events"]),
            )
            for row in subset
        ]
        ax.scatter(
            xs,
            ys,
            s=sizes,
            marker="o",
            color=NUCLIDE_COLORS.get(label, "#777777"),
            edgecolor="white",
            linewidth=0.55,
            alpha=0.82,
            zorder=18,
        )
    mxc = [row for row in points if row["is_MXC"]]
    ax.scatter(
        [safe_float(row["xprime_cm"]) for row in mxc],
        [safe_float(row["radius_cm"] if axial else row["zprime_cm"]) for row in mxc],
        s=[
            marker_size(safe_float(row["selected_rate_cps"]), max_rate, int(row["selected_events"])) + 28
            for row in mxc
        ],
        marker="o",
        facecolor="none",
        edgecolor="#111111",
        linewidth=1.45,
        zorder=19,
    )


def prompt_segments_xz(event: dict[str, Any]) -> list[dict[str, Any]]:
    interactions = event["interactions"]
    by_id = {int(row["ia_id"]): row for row in interactions}
    output: list[dict[str, Any]] = []
    tes = event.get("tes") or {}
    tes_point = (
        (safe_float(tes["xprime_cm"]), safe_float(tes["z_centered_cm"]) + CENTER_Z)
        if tes
        else None
    )
    for row in interactions:
        if row["process"] in {"INIT", "ESCP"}:
            continue
        parent = by_id.get(int(row["parent_id"]))
        if parent is None:
            continue
        child_point = (
            safe_float(row["xprime_cm"]),
            safe_float(row["z_centered_cm"]) + CENTER_Z,
        )
        output.append(
            {
                "segment": np.asarray(
                (
                    (safe_float(parent["xprime_cm"]), safe_float(parent["z_centered_cm"]) + CENTER_Z),
                    child_point,
                )
                ),
                "process": row["process"],
                "ends_at_tes": (
                    tes_point is not None
                    and math.hypot(child_point[0] - tes_point[0], child_point[1] - tes_point[1]) < 0.08
                ),
            }
        )
    return output


def draw_prompt_routes_xz(ax: plt.Axes, events: list[dict[str, Any]]) -> None:
    for event in events:
        event_id = int(event["local_event_id"])
        color = PROMPT_EVENT_COLORS.get(event_id, "#555555")
        segments = prompt_segments_xz(event)
        branches = [
            row["segment"] for row in segments
            if row["process"] in {"PHOT", "BREM"} and not row["ends_at_tes"]
        ]
        core = [
            row["segment"] for row in segments
            if row["process"] not in {"PHOT", "BREM"} or row["ends_at_tes"]
        ]
        if branches:
            ax.add_collection(
                LineCollection(branches, colors=color, linewidths=0.58, alpha=0.24, zorder=11)
            )
        if core:
            ax.add_collection(
                LineCollection(core, colors=color, linewidths=1.18, alpha=0.64, zorder=12)
            )
        for process, (marker, process_color, size) in PROCESS_STYLE.items():
            rows = [row for row in event["interactions"] if row["process"] == process]
            if not rows:
                continue
            kwargs: dict[str, Any] = {
                "s": size,
                "marker": marker,
                "color": process_color,
                "alpha": 0.82 if process != "PHOT" else 0.46,
                "zorder": 21,
            }
            if marker not in {"x"}:
                kwargs.update(edgecolor=color, linewidth=0.45)
            ax.scatter(
                [safe_float(row["xprime_cm"]) for row in rows],
                [safe_float(row["z_centered_cm"]) + CENTER_Z for row in rows],
                **kwargs,
            )
        tes = event.get("tes")
        if tes:
            ax.scatter(
                [safe_float(tes["xprime_cm"])],
                [safe_float(tes["z_centered_cm"]) + CENTER_Z],
                s=34,
                marker="o",
                color="#D62728",
                edgecolor="white",
                linewidth=0.7,
                zorder=24,
            )
        pairs = [row for row in event["interactions"] if row["process"] == "PAIR"]
        if pairs:
            pair = pairs[0]
            offsets = {13313: (8, 18), 54078: (12, -32), 256781: (8, 8)}
            ax.annotate(
                f"P{event_id}\n{pair['new_w_region'].replace('SF3_W_NearField_', '').replace('_2p9mm', '')}",
                xy=(safe_float(pair["xprime_cm"]), safe_float(pair["z_centered_cm"]) + CENTER_Z),
                xytext=offsets.get(event_id, (5, 4)),
                textcoords="offset points",
                fontsize=5.8,
                color=color,
                weight="bold",
                zorder=26,
            )


def draw_prompt_routes_axial(ax: plt.Axes, events: list[dict[str, Any]]) -> None:
    for event in events:
        event_id = int(event["local_event_id"])
        color = PROMPT_EVENT_COLORS.get(event_id, "#555555")
        segments = [
            np.asarray(((row["x0_cm"], row["r0_cm"]), (row["x1_cm"], row["r1_cm"])))
            for row in event["segments"]
        ]
        ax.add_collection(
            LineCollection(segments, colors=color, linewidths=1.1, alpha=0.60, zorder=9)
        )
        for process, (marker, process_color, size) in PROCESS_STYLE.items():
            rows = [row for row in event["interactions"] if row["process"] == process]
            if not rows:
                continue
            kwargs: dict[str, Any] = {
                "s": size,
                "marker": marker,
                "color": process_color,
                "alpha": 0.82 if process != "PHOT" else 0.46,
                "zorder": 14,
            }
            if marker != "x":
                kwargs.update(edgecolor=color, linewidth=0.45)
            ax.scatter(
                [safe_float(row["xprime_cm"]) for row in rows],
                [safe_float(row["radius_cm"]) for row in rows],
                **kwargs,
            )
        tes = event.get("tes")
        if tes:
            ax.scatter(
                [safe_float(tes["xprime_cm"])],
                [safe_float(tes["radius_cm"])],
                s=34,
                color="#D62728",
                edgecolor="white",
                linewidth=0.7,
                zorder=16,
            )


def figure_legend() -> list[Any]:
    handles: list[Any] = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor="white", label=label, markersize=7)
        for label, color in NUCLIDE_COLORS.items()
    ]
    handles.append(
        Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor="black", markeredgewidth=1.4, label="MXC source point", markersize=8)
    )
    for event_id, color in PROMPT_EVENT_COLORS.items():
        handles.append(Line2D([0], [0], color=color, lw=1.5, label=f"SF3 prompt P{event_id}"))
    for process, (marker, color, _) in PROCESS_STYLE.items():
        handles.append(
            Line2D([0], [0], marker=marker, color="none", markerfacecolor=color, markeredgecolor=color, label=process, markersize=6)
        )
    handles.extend(
        [
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#D62728", markeredgecolor="white", label="TES deposit centroid", markersize=6),
            Patch(facecolor="#3A3A3A", edgecolor="#111111", hatch="////", alpha=0.18, label="SF3 passive W (not veto)"),
            Line2D([0], [0], color="#D81B60", lw=1.2, ls="--", label="proposal-only design ROI"),
        ]
    )
    return handles


def save_figure(fig: plt.Figure, stem: str, output: Path) -> list[str]:
    paths: list[str] = []
    for suffix in ("png", "svg", "pdf"):
        path = output / f"{stem}.{suffix}"
        kwargs = {"dpi": 330} if suffix == "png" else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.09, **kwargs)
        paths.append(str(path))
    plt.close(fig)
    return paths


def build_section_figure(
    mesh: dict[str, np.ndarray],
    visual: Any,
    points: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    limits: tuple[tuple[float, float], tuple[float, float]],
    title: str,
    stem: str,
    output: Path,
) -> list[str]:
    fig, ax = plt.subplots(figsize=(10.8, 8.2))
    visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
    draw_sf3_w_xz(ax)
    draw_activation_points(ax, points)
    draw_prompt_routes_xz(ax, events)
    draw_design_rois(ax, mesh, visual)
    visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_title(title, weight="bold", pad=8)
    ax.text(
        0.01,
        0.985,
        "SE3 mesh: exact y'=0 section. Activation and SF3 route points: x'-z' projections.\n"
        "Marker area follows selected delayed W2 rate; repeated identical source points are aggregated.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.7,
        color="#263442",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#CCD5DD", "alpha": 0.90},
        zorder=40,
    )
    ax.legend(
        handles=figure_legend(),
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        ncol=1,
        fontsize=6.5,
    )
    fig.subplots_adjust(right=0.76)
    return save_figure(fig, stem, output)


def build_axial_figure(
    points: list[dict[str, Any]], events: list[dict[str, Any]], output: Path
) -> list[str]:
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13.8, 6.2), sharex=True, sharey=True)
    for ax in (ax_a, ax_b):
        draw_sf3_w_axial(ax)
        ax.set_xlim(-10.5, 11.0)
        ax.set_ylim(0.0, 15.5)
        ax.set_xlabel("InstrumentFrame x' [cm]")
        ax.grid(color="#DCE4EA", linewidth=0.45, alpha=0.75)
        ax.set_axisbelow(True)
    draw_activation_points(ax_a, points, axial=True)
    draw_prompt_routes_axial(ax_b, events)
    ax_a.set_ylabel("radius sqrt(y'^2 + (z'+5.2)^2) [cm]")
    ax_a.set_title("SE3 delayed-W2 activation origins", weight="bold")
    ax_b.set_title("SF3 prompt-W2 survivor routes", weight="bold")
    ax_a.text(0.02, 0.98, "47 selected events; sizes follow cps\nMXC points have black rings", transform=ax_a.transAxes, ha="left", va="top", fontsize=7)
    ax_b.text(0.02, 0.98, "3 prompt survivors; passive W is material, not veto", transform=ax_b.transAxes, ha="left", va="top", fontsize=7)
    fig.legend(handles=figure_legend(), loc="lower center", bbox_to_anchor=(0.5, -0.05), ncol=6, frameon=False, fontsize=6.5)
    fig.suptitle("SE3 activation + SF3 prompt route diagnostic in axial-radius coordinates", weight="bold", y=1.01)
    return save_figure(fig, "se3_activation_sf3_prompt_axial_radius", output)


def strict_validate(
    origins: list[dict[str, str]],
    parent_rows: list[dict[str, Any]],
    volume_rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    route_data: dict[str, Any],
) -> dict[str, Any]:
    total = weighted_stats(origins)
    mxc = [row for row in origins if row["source_volume"] == MXC_VOLUME]
    prompt_rows = prompt_event_rows(events)
    checks = {
        "se3_selected_delayed_events_47": len(origins) == 47,
        "se3_selected_delayed_rate_matches_0p0601133621": math.isclose(
            safe_float(total["selected_rate_cps"]), 0.06011336205846697, rel_tol=0.0, abs_tol=1e-14
        ),
        "se3_parent_reaggregation_matches_report": all(
            bool(row["report_present"])
            and int(row["report_event_delta"]) == 0
            and abs(safe_float(row["report_rate_delta_cps"])) < 1e-13
            for row in parent_rows
        ),
        "se3_volume_reaggregation_matches_report": all(
            bool(row["report_present"])
            and int(row["report_event_delta"]) == 0
            and abs(safe_float(row["report_rate_delta_cps"])) < 1e-13
            for row in volume_rows
        ),
        "se3_mxc_selected_events_7": len(mxc) == 7,
        "se3_mxc_selected_rate_matches_0p0150711950": math.isclose(
            safe_float(weighted_stats(mxc)["selected_rate_cps"]), 0.015071195046020287, rel_tol=0.0, abs_tol=1e-14
        ),
        "sf3_prompt_events_3": len(events) == 3,
        "sf3_prompt_all_active_veto_zero": all(
            safe_float(row["active_veto_edep_keV"]) == 0.0 for row in prompt_rows
        ),
        "sf3_prompt_pair_region_counts_match_route_summary": Counter(
            row["pair_vertex_region"] for row in prompt_rows
        )
        == Counter(route_data["summary"]["prompt_events_with_pair_by_region"]),
    }
    if not all(checks.values()):
        failed = [key for key, passed in checks.items() if not passed]
        raise ToolError(f"strict validation failed: {failed}")
    return {"status": "PASS", "checks": checks}


def optimization_summary(
    parent_rows: list[dict[str, Any]],
    volume_rows: list[dict[str, Any]],
    origins: list[dict[str, str]],
    prompt_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_parent = {row["group"]: row for row in parent_rows}
    by_volume = {row["group"]: row for row in volume_rows}
    copper_parent_share = math.fsum(
        safe_float(by_parent[label]["selected_rate_share"])
        for label in ("Cu-61", "Cu-62", "Cu-64")
    )
    v2a_share = math.fsum(
        safe_float(by_volume[volume]["selected_rate_share"])
        for volume in (BOTTOM_VOLUME, L0_VOLUME)
    )
    v2b_share = v2a_share + safe_float(by_volume[MXC_VOLUME]["selected_rate_share"])
    mxc_rows = [row for row in origins if row["source_volume"] == MXC_VOLUME]
    mxc_stats = weighted_stats(mxc_rows)
    mxc_parent = Counter()
    mxc_family = Counter()
    for row in mxc_rows:
        mxc_parent[nuclide(row)] += safe_float(row["event_weight_cps"])
        mxc_family[row["family"]] += safe_float(row["event_weight_cps"])
    pair_regions = Counter(row["pair_vertex_region"] for row in prompt_rows)
    return {
        "status": "DIAGNOSTIC_NOT_GEOMETRY_PROMOTION",
        "se3_activation": {
            "selected_delayed_W2_events": len(origins),
            "selected_delayed_W2_rate_cps": safe_float(weighted_stats(origins)["selected_rate_cps"]),
            "Cu61_Cu62_Cu64_rate_share": copper_parent_share,
            "V2A_bottom_plus_L0_observed_rate_share": v2a_share,
            "V2B_bottom_plus_L0_plus_MXC_observed_rate_share": v2b_share,
            "MXC": {
                **mxc_stats,
                "selected_rate_share": safe_float(mxc_stats["selected_rate_cps"])
                / safe_float(weighted_stats(origins)["selected_rate_cps"]),
                "parent_rate_cps": dict(mxc_parent),
                "incident_family_rate_cps": dict(mxc_family),
            },
        },
        "sf3_prompt": {
            "selected_events": len(prompt_rows),
            "selected_rate_cps": math.fsum(safe_float(row["event_weight_cps"]) for row in prompt_rows),
            "pair_event_regions": dict(pair_regions),
            "active_veto_edep_keV": [safe_float(row["active_veto_edep_keV"]) for row in prompt_rows],
            "interpretation": "near-field passive W creates/scatters survivor routes and provides no veto signal",
        },
        "optimization_order": [
            "V2A: convert L0 solid Cu disk to an open-ring implementation and replace the broad 50 mK bottom cap with an aperture/ring-cap variant, subject to thermal and mechanical constraints",
            "V2B: add staggered line-of-sight relief in the MXC plate; do not infer MXC is safe from SF3 delayed data because SF3 passive W perturbs activation",
            "Keep 4 K plate modification as a later engineering-risk branch despite its observed residual share",
            "Do not add or retain near-field high-Z passive W in the focused acceptance path unless a matched common-response/veto/Step05 run demonstrates benefit",
        ],
        "required_gates": [
            "matched corrected-keV prompt -> candidate-own activation/inventory -> actual-position delayed chain",
            "independent 37,194-ray focused-signal run",
            "shared detector response, active-veto policy, and Step05 selection",
            "81-node / 20-day F3 comparison",
        ],
        "hard_constraints": {
            "mono_511_enabled": False,
            "passive_W_is_veto": False,
            "SF3_full_stat_completion": False,
            "final_optimal_geometry_exists": False,
        },
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    activation = summary["se3_activation"]
    mxc = activation["MXC"]
    prompt = summary["sf3_prompt"]
    text = f"""# SE3 activation + SF3 prompt section diagnosis

## What is plotted

The geometry background is the validated SE3 native mesh.  Activation points are the
{activation['selected_delayed_W2_events']} SE3 delayed-W2 selected-event production origins,
weighted to {activation['selected_delayed_W2_rate_cps']:.12g} cps.  They are a distribution of
rate-contributing sources, not a map of every activated atom.  Prompt routes are the three SF3
prompt-W2 survivors from the compact route JSON.  The SF3 W overlays are passive material and
are **not** active veto volumes.

## Quantitative result

Cu-61/Cu-62/Cu-64 account for {activation['Cu61_Cu62_Cu64_rate_share']:.3%} of the SE3 delayed-W2
rate.  The MXC plate retains {mxc['selected_events']} selected events and
{mxc['selected_rate_cps']:.12g} cps ({mxc['selected_rate_share']:.3%}); therefore the MXC term
must not be dismissed using SF3 delayed activation, whose added W can perturb its irradiation.
The 50 mK bottom cap plus L0 disk cover {activation['V2A_bottom_plus_L0_observed_rate_share']:.3%}
of the observed residual rate; adding the MXC plate raises the covered share to
{activation['V2B_bottom_plus_L0_plus_MXC_observed_rate_share']:.3%}.

The SF3 prompt sample is {prompt['selected_events']} events / {prompt['selected_rate_cps']:.12g}
cps.  Two pair vertices lie in the new side W, while the third pairs outside the new W and then
has a Rayleigh interaction in the new front W.  Every event has zero active-veto deposit.  This
is direct negative evidence against near-field passive high-Z material in the focused acceptance
path; it is not a full-stat rate estimate.

## Optimization order

1. V2A: turn the L0 solid Cu disk into an open ring and test an aperture/ring-cap replacement for
   the broad 50 mK bottom cap, while preserving thermal/mechanical requirements.
2. V2B: add staggered line-of-sight relief to the MXC plate.  Do not remove the whole MXC plate;
   treat the dashed box as a design ROI and constrain the relief thermally.
3. Keep the 4 K plate as a later, higher-engineering-risk branch.
4. Reject near-field W concepts unless the complete matched chain reverses the observed prompt
   failure without harming focused signal.

No geometry is promoted here.  A candidate still needs corrected prompt, candidate-owned
activation/inventory, actual-position delayed transport, the independent 37,194-ray signal,
shared response/veto/Step05, and 81-node/20-day F3.  Mono-511 remains disabled, SF3 is not
full-stat, and there is no final optimal geometry.
"""
    path.write_text(text, encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--se3-origins", type=Path, default=DEFAULT_ORIGINS)
    result.add_argument("--se3-volume-report", type=Path, default=DEFAULT_VOLUME_REPORT)
    result.add_argument("--se3-parent-report", type=Path, default=DEFAULT_PARENT_REPORT)
    result.add_argument("--se3-family-report", type=Path, default=DEFAULT_FAMILY_REPORT)
    result.add_argument("--se3-mesh", type=Path, default=DEFAULT_MESH)
    result.add_argument("--sf3-routes", type=Path, default=DEFAULT_SF3_ROUTES)
    result.add_argument("--output", type=Path, default=OUTPUT)
    result.add_argument("--audit", type=Path, default=AUDIT / "tool_validation.json")
    return result


def main() -> int:
    args = parser().parse_args()
    inputs = {
        "se3_origins": args.se3_origins,
        "se3_volume_report": args.se3_volume_report,
        "se3_parent_report": args.se3_parent_report,
        "se3_family_report": args.se3_family_report,
        "se3_mesh": args.se3_mesh,
        "sf3_routes": args.sf3_routes,
    }
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise ToolError(f"missing inputs: {missing}")

    args.output.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    visual = local_visual
    visual.configure_matplotlib()
    mesh = visual.load_mesh(args.se3_mesh)
    origins = read_csv(args.se3_origins)
    volume_report_rows = read_csv(args.se3_volume_report)
    parent_report_rows = read_csv(args.se3_parent_report)
    family_report_rows = read_csv(args.se3_family_report)
    route_data = json.loads(args.sf3_routes.read_text(encoding="utf-8"))
    events = prompt_events(route_data)

    parent_report = report_lookup(parent_report_rows, "source_parent_ZA")
    known_labels = set(NUCLIDE_LABELS.values())
    parent_report = {
        (key if key in known_labels else NUCLIDE_LABELS.get(key, f"ZA={key}")): value
        for key, value in parent_report.items()
    }
    volume_report = report_lookup(volume_report_rows, "source_volume")
    family_report = report_lookup(family_report_rows, "incident_family")
    parent_stats = group_activation(origins, nuclide, parent_report)
    volume_stats = group_activation(origins, lambda row: row["source_volume"], volume_report)
    family_stats = group_activation(origins, lambda row: row["family"], family_report)
    plot_points = build_plot_points(origins)
    prompt_rows = prompt_event_rows(events)
    process_rows = prompt_process_rows(events)

    common_fields = [
        "group", "report_present", "activity_Bq", "selected_events", "selected_rate_cps",
        "selected_sigma_cps", "selected_Neff", "selected_rate_share",
        "report_event_delta", "report_rate_delta_cps",
    ]
    write_csv(args.output / "activation_nuclide_stats.csv", parent_stats, common_fields)
    write_csv(args.output / "activation_volume_stats.csv", volume_stats, common_fields)
    write_csv(args.output / "activation_incident_family_stats.csv", family_stats, common_fields)
    write_csv(
        args.output / "activation_plot_points.csv",
        plot_points,
        [
            "nuclide", "source_volume", "is_MXC", "xprime_cm", "yprime_cm",
            "zprime_cm", "radius_cm", "selected_events", "selected_rate_cps",
            "selected_sigma_cps", "selected_Neff",
        ],
    )
    write_csv(
        args.output / "sf3_prompt_event_routes.csv",
        prompt_rows,
        list(prompt_rows[0]),
    )
    write_csv(
        args.output / "sf3_prompt_process_regions.csv",
        process_rows,
        ["process", "region", "interaction_points", "supporting_events"],
    )

    validation = strict_validate(origins, parent_stats, volume_stats, events, route_data)
    summary = optimization_summary(parent_stats, volume_stats, origins, prompt_rows)
    write_json(args.output / "optimization_summary.json", summary)
    write_report(args.output / "ANALYSIS_REPORT.md", summary)

    figure_paths: list[str] = []
    figure_paths.extend(
        build_section_figure(
            mesh,
            visual,
            plot_points,
            events,
            limits=((-22.0, 22.0), (-16.0, 33.0)),
            title="Global detailed section: SE3 delayed-W2 activation + SF3 prompt-W2 routes",
            stem="se3_activation_sf3_prompt_global_detailed_section",
            output=args.output,
        )
    )
    figure_paths.extend(
        build_section_figure(
            mesh,
            visual,
            plot_points,
            events,
            limits=((-9.0, 10.5), (-15.5, 2.5)),
            title="Local near-field section: activation source points, prompt routes, and design ROIs",
            stem="se3_activation_sf3_prompt_local_nearfield_section",
            output=args.output,
        )
    )
    figure_paths.extend(build_axial_figure(plot_points, events, args.output))

    audit = {
        **validation,
        "authority_boundary": {
            "geometry": "SE3 native mesh exact y'=0 section",
            "activation": "SE3 selected delayed W2 origin positions and weights",
            "prompt": "SF3 selected prompt W2 route JSON",
            "passive_W_is_active_veto": False,
            "proposal_ROIs_are_implemented_geometry": False,
            "opens_SIM_payloads": False,
            "starts_transport": False,
            "hashes_large_payloads": False,
        },
        "coordinate_contract": {
            "frame": "InstrumentFrame",
            "section": "y'=0 exact mesh; event/source markers are x'-z' projections",
            "axial_radius": "sqrt(y'^2 + (z' + 5.2 cm)^2)",
        },
        "input_files": {
            key: {"path": str(path), "size_bytes": path.stat().st_size}
            for key, path in inputs.items()
        },
        "algorithm_provenance": {
            "se3_native_section_source": {
                "path": str(DEFAULT_SE3_VISUAL_CODE),
                "currently_exists": DEFAULT_SE3_VISUAL_CODE.is_file(),
            },
            "detailed_parent_child_route_style_source": {
                "path": str(DEFAULT_DETAILED_ROUTE_STYLE),
                "currently_exists": DEFAULT_DETAILED_ROUTE_STYLE.is_file(),
            },
            "sf3_compact_route_builder_source": {
                "path": str(DEFAULT_SF3_ROUTE_BUILDER),
                "currently_exists": DEFAULT_SF3_ROUTE_BUILDER.is_file(),
            },
            "local_section_adapter": str(TOOL / "se3_section_adapter.py"),
        },
        "outputs": figure_paths
        + [
            str(args.output / "activation_nuclide_stats.csv"),
            str(args.output / "activation_volume_stats.csv"),
            str(args.output / "activation_incident_family_stats.csv"),
            str(args.output / "activation_plot_points.csv"),
            str(args.output / "sf3_prompt_event_routes.csv"),
            str(args.output / "sf3_prompt_process_regions.csv"),
            str(args.output / "optimization_summary.json"),
            str(args.output / "ANALYSIS_REPORT.md"),
        ],
        "counts": {
            "se3_selected_activation_events": len(origins),
            "se3_aggregated_plot_points": len(plot_points),
            "sf3_prompt_events": len(events),
        },
    }
    write_json(args.audit, audit)
    print(json.dumps({"status": "PASS", "audit": str(args.audit), "outputs": len(audit["outputs"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
