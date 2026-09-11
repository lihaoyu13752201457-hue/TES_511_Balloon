#!/usr/bin/env python3
"""Build the S3d-O8 event-overlay WRL and the detailed 2-D audit figure.

The geometry surface is the Geant4 VRML2FILE tessellation produced by Cosima,
so all placed Boolean solids are already resolved by the transport geometry.
Coordinates in the native WRL are Geant4 millimetres.  Event ledgers are in
centimetres and are converted explicitly when written to WRL.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


OUT = Path(__file__).resolve().parents[1]
DATA = OUT / "data"
FIGURES = OUT / "figures"
GEOMETRY_OUT = OUT / "geometry"
AUDIT = OUT / "audit"

AUTH_ROOT = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
GEOMETRY_AUTH = AUTH_ROOT / (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry"
)
INTRO_GEO = GEOMETRY_AUTH / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
MAIN_GEO = GEOMETRY_AUTH / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
SETUP_GEO = GEOMETRY_AUTH / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
NATIVE_WRL = GEOMETRY_OUT / "s3d_o8_native_geant4_full.wrl"
FINAL_WRL = GEOMETRY_OUT / "s3d_o8_mass_model_activation_prompt_tracks.wrl"

DELAYED_POINTS = DATA / "delayed_source_point_ledger.csv"
DELAYED_EVENTS = DATA / "delayed_selected_event_ledger.csv"
DELAYED_ORIGINS = DATA / "delayed_partial_production_origin_links.csv"


@dataclass
class Solid:
    name: str
    material: str
    vertices_mm: np.ndarray
    faces: list[list[int]]
    block: str


# rgb, WRL transparency, 2-D projected alpha
MATERIAL_STYLE: dict[str, tuple[tuple[float, float, float], float, float]] = {
    "Ta": ((0.66, 0.10, 0.12), 0.18, 0.48),
    "W": ((0.08, 0.09, 0.11), 0.35, 0.42),
    "Copper": ((0.87, 0.36, 0.10), 0.56, 0.28),
    "Aluminium": ((0.38, 0.62, 0.84), 0.78, 0.13),
    "Silicon": ((0.90, 0.78, 0.35), 0.46, 0.32),
    "Nb": ((0.16, 0.36, 0.78), 0.48, 0.32),
    "MuMetal": ((0.43, 0.19, 0.63), 0.55, 0.28),
    "BGO": ((0.10, 0.61, 0.33), 0.78, 0.14),
    "PlasticScintillator": ((0.07, 0.70, 0.72), 0.84, 0.10),
    "BoratedPolyethylene5wtB": ((0.72, 0.62, 0.31), 0.86, 0.09),
    "Kapton": ((0.93, 0.53, 0.10), 0.76, 0.16),
    "StainlessSteel": ((0.48, 0.53, 0.58), 0.66, 0.20),
    "G10": ((0.39, 0.48, 0.24), 0.58, 0.22),
    "CuNi": ((0.55, 0.37, 0.24), 0.50, 0.26),
    "NbTiCableProxy": ((0.12, 0.52, 0.65), 0.52, 0.25),
    "Be": ((0.74, 0.88, 0.91), 0.32, 0.40),
    "SilverSinterProxy": ((0.76, 0.77, 0.80), 0.30, 0.38),
    "CharcoalProxy": ((0.18, 0.18, 0.18), 0.42, 0.30),
}
DEFAULT_STYLE = ((0.56, 0.58, 0.61), 0.68, 0.18)

EVENT_COLORS = {
    3883: (0.88, 0.25, 0.12),
    19932: (0.10, 0.42, 0.82),
    8081: (0.72, 0.18, 0.66),
}

FAMILY_MARKERS = {
    "alpha": "^",
    "eminus": "v",
    "eplus": "o",
    "gamma": "s",
    "muminus": "P",
    "n": "D",
    "p": "X",
}


def parse_geo_materials() -> tuple[dict[str, str], dict[str, str]]:
    direct: dict[str, str] = {}
    copy_source: dict[str, str] = {}
    for path in (INTRO_GEO, MAIN_GEO):
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            match = re.match(r"^(\S+)\.Material\s+(\S+)", line)
            if match:
                direct[match.group(1)] = match.group(2)
            match = re.match(r"^(\S+)\.Copy\s+(\S+)$", line)
            if match:
                copy_source[match.group(2)] = match.group(1)

    resolved: dict[str, str] = {}

    def resolve(name: str) -> str:
        if name in resolved:
            return resolved[name]
        seen: set[str] = set()
        current = name
        while current not in seen:
            seen.add(current)
            if current in direct:
                resolved[name] = direct[current]
                return direct[current]
            current = copy_source.get(current, "")
            if not current:
                break
        raise KeyError(f"No material authority for WRL placement {name}")

    for name in set(direct) | set(copy_source):
        try:
            resolve(name)
        except KeyError:
            pass
    return resolved, copy_source


def split_faces(index_text: str) -> list[list[int]]:
    values = [int(value) for value in re.findall(r"-?\d+", index_text)]
    faces: list[list[int]] = []
    current: list[int] = []
    for value in values:
        if value == -1:
            if len(current) >= 3:
                faces.append(current)
            current = []
        else:
            current.append(value)
    return faces


def parse_native_wrl(materials: dict[str, str]) -> tuple[str, list[Solid]]:
    text = NATIVE_WRL.read_text(encoding="utf-8")
    pattern = re.compile(
        r"#---------- SOLID: (.+?)\.0\n(.*?)(?=\n#---------- SOLID:|\n#End of file\.)",
        re.S,
    )
    solids: list[Solid] = []
    for match in pattern.finditer(text):
        name, block = match.group(1), match.group(2)
        point_match = re.search(r"point\s*\[(.*?)\]", block, re.S)
        face_match = re.search(r"coordIndex\s*\[(.*?)\]", block, re.S)
        if point_match is None or face_match is None:
            raise RuntimeError(f"Incomplete WRL mesh block: {name}")
        numbers = np.fromstring(point_match.group(1).replace(",", " "), sep=" ")
        if len(numbers) % 3:
            raise RuntimeError(f"Malformed WRL point list: {name}")
        solids.append(
            Solid(
                name=name,
                material=materials[name],
                vertices_mm=numbers.reshape(-1, 3),
                faces=split_faces(face_match.group(1)),
                block=block,
            )
        )
    return text, solids


def world_to_if(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    result = np.empty_like(points)
    root2 = math.sqrt(2.0)
    result[..., 0] = (points[..., 0] - points[..., 2]) / root2
    result[..., 1] = points[..., 1]
    result[..., 2] = (points[..., 0] + points[..., 2]) / root2
    return result


def isotope_colors(isotopes: Iterable[str]) -> dict[str, tuple[float, float, float, float]]:
    ordered = sorted(set(isotopes), key=lambda item: (int(item.split("-")[1]), item))
    cmap = mpl.colormaps["tab20"]
    return {name: cmap(index / max(1, len(ordered) - 1)) for index, name in enumerate(ordered)}


def load_optional(names: list[str]) -> pd.DataFrame:
    for name in names:
        path = DATA / name
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def first_column(frame: pd.DataFrame, *names: str) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def event_id_column(frame: pd.DataFrame) -> str | None:
    return first_column(frame, "local_event_id", "prompt_local_event_id", "event_id")


def xyz_columns(frame: pd.DataFrame, prefix: str = "world") -> tuple[str, str, str] | None:
    choices = [
        (f"{prefix}_x_cm", f"{prefix}_y_cm", f"{prefix}_z_cm"),
        (f"{prefix}_x", f"{prefix}_y", f"{prefix}_z"),
        ("x_cm", "y_cm", "z_cm"),
    ]
    return next((triple for triple in choices if all(item in frame.columns for item in triple)), None)


def load_prompt_tables() -> dict[str, pd.DataFrame]:
    tables = {
        "events": load_optional(["prompt_events.csv", "prompt_event_ledger.csv"]),
        "ia": load_optional(["prompt_ia_nodes.csv", "prompt_ia_node_ledger.csv"]),
        "cc": load_optional(["prompt_cc_hits.csv", "prompt_cc_hit_ledger.csv"]),
        "htsim": load_optional(["prompt_htsim_hits.csv", "prompt_htsim_hit_ledger.csv"]),
        "edges": load_optional(["prompt_ancestry_edges.csv"]),
        "segments": load_optional(["prompt_track_segments.csv"]),
        "vertices": load_optional(["prompt_track_vertices.csv"]),
    }
    events = tables["events"]
    if not events.empty and {"event_uid", "local_event_id"} <= set(events.columns):
        uid_to_id = events[["event_uid", "local_event_id"]].drop_duplicates()
        for key, frame in tables.items():
            if key == "events" or frame.empty or "local_event_id" in frame.columns:
                continue
            if "event_uid" in frame.columns:
                tables[key] = frame.merge(uid_to_id, on="event_uid", how="left", validate="many_to_one")
    return tables


def derive_prompt_segments(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    segments = tables["segments"].copy()
    if not segments.empty:
        return segments
    vertices = tables["vertices"].copy()
    if vertices.empty:
        return segments
    event_col = event_id_column(vertices)
    xyz = xyz_columns(vertices)
    sequence_col = first_column(vertices, "vertex_order", "sequence", "sequence_index", "time_order")
    path_col = first_column(vertices, "path_id", "track_id", "segment_group", "path_kind")
    if not event_col or not xyz or not sequence_col:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    groups = [event_col] + ([path_col] if path_col else [])
    for keys, group in vertices.groupby(groups, dropna=False):
        group = group.sort_values(sequence_col)
        records = group.to_dict("records")
        for start, stop in zip(records[:-1], records[1:]):
            row = {
                "local_event_id": int(start[event_col]),
                "segment_kind": start.get("path_kind", start.get("vertex_kind", "interaction_chord")),
                "start_world_x_cm": start[xyz[0]],
                "start_world_y_cm": start[xyz[1]],
                "start_world_z_cm": start[xyz[2]],
                "end_world_x_cm": stop[xyz[0]],
                "end_world_y_cm": stop[xyz[1]],
                "end_world_z_cm": stop[xyz[2]],
            }
            rows.append(row)
    return pd.DataFrame(rows)


def segment_columns(frame: pd.DataFrame):
    starts = [
        ("start_world_x_cm", "start_world_y_cm", "start_world_z_cm"),
        ("world_x0_cm", "world_y0_cm", "world_z0_cm"),
        ("x0_cm", "y0_cm", "z0_cm"),
    ]
    ends = [
        ("end_world_x_cm", "end_world_y_cm", "end_world_z_cm"),
        ("world_x1_cm", "world_y1_cm", "world_z1_cm"),
        ("x1_cm", "y1_cm", "z1_cm"),
    ]
    start = next((cols for cols in starts if all(col in frame.columns for col in cols)), None)
    end = next((cols for cols in ends if all(col in frame.columns for col in cols)), None)
    return start, end


def material_style(material: str):
    return MATERIAL_STYLE.get(material, DEFAULT_STYLE)


def projected_polygons(
    solids: list[Solid],
    *,
    frame: str,
    axes: tuple[int, int],
    depth_axis: int,
    name_filter=None,
):
    polygons: list[np.ndarray] = []
    colors: list[tuple[float, float, float, float]] = []
    depths: list[float] = []
    for solid in solids:
        if name_filter is not None and not name_filter(solid.name):
            continue
        vertices = world_to_if(solid.vertices_mm) if frame == "IF" else solid.vertices_mm
        vertices = vertices / 10.0  # native Geant4 WRL mm -> plotted cm
        rgb, _, alpha = material_style(solid.material)
        for face in solid.faces:
            face_vertices = vertices[np.asarray(face)]
            polygons.append(face_vertices[:, axes])
            colors.append((*rgb, alpha))
            depths.append(float(face_vertices[:, depth_axis].mean()))
    order = np.argsort(depths)
    return [polygons[index] for index in order], [colors[index] for index in order]


def draw_projection(
    ax,
    solids: list[Solid],
    *,
    frame: str,
    axes: tuple[int, int],
    depth_axis: int,
    name_filter=None,
):
    polygons, colors = projected_polygons(
        solids,
        frame=frame,
        axes=axes,
        depth_axis=depth_axis,
        name_filter=name_filter,
    )
    collection = PolyCollection(
        polygons,
        facecolors=colors,
        edgecolors="none",
        linewidths=0.0,
        rasterized=True,
    )
    ax.add_collection(collection)
    ax.autoscale_view()
    return collection


def triangle_plane_segment(triangle: np.ndarray, axis: int, value: float = 0.0):
    distances = triangle[:, axis] - value
    eps = 1e-8
    points: list[np.ndarray] = []
    if np.all(np.abs(distances) <= eps):
        return [(triangle[i], triangle[(i + 1) % 3]) for i in range(3)]
    for index in range(3):
        j = (index + 1) % 3
        p0, p1 = triangle[index], triangle[j]
        d0, d1 = distances[index], distances[j]
        if abs(d0) <= eps:
            points.append(p0)
        if d0 * d1 < 0.0:
            fraction = -d0 / (d1 - d0)
            points.append(p0 + fraction * (p1 - p0))
    unique: list[np.ndarray] = []
    for point in points:
        if not any(np.linalg.norm(point - prior) < 1e-6 for prior in unique):
            unique.append(point)
    if len(unique) < 2:
        return []
    if len(unique) > 2:
        best = max(
            ((a, b) for a in unique for b in unique),
            key=lambda pair: np.linalg.norm(pair[0] - pair[1]),
        )
        return [best]
    return [(unique[0], unique[1])]


def draw_exact_section(ax, solids: list[Solid], *, zoom: bool = False):
    segments: list[np.ndarray] = []
    colors: list[tuple[float, float, float, float]] = []
    widths: list[float] = []
    for solid in solids:
        rgb, _, _ = material_style(solid.material)
        vertices = world_to_if(solid.vertices_mm) / 10.0  # mm -> cm
        for face in solid.faces:
            for index in range(1, len(face) - 1):
                triangle = vertices[np.asarray([face[0], face[index], face[index + 1]])]
                for start, stop in triangle_plane_segment(triangle, axis=1, value=0.0):
                    line = np.asarray([[start[0], start[2]], [stop[0], stop[2]]])
                    if zoom and not np.any(
                        (np.abs(line[:, 0]) < 170.0) & (np.abs(line[:, 1]) < 170.0)
                    ):
                        continue
                    segments.append(line)
                    colors.append((*rgb, 0.82))
                    widths.append(0.35 if solid.material not in {"Ta", "W"} else 0.55)
    ax.add_collection(LineCollection(segments, colors=colors, linewidths=widths, rasterized=True))
    ax.autoscale_view()


def scatter_delayed(ax, frame: pd.DataFrame, *, plane: str, iso_colors, label_top: int = 0):
    if plane == "world_xz":
        xcol, ycol = "source_world_x_cm", "source_world_z_cm"
    elif plane == "IF_xz":
        xcol, ycol = "source_IF_x_cm", "source_IF_z_cm"
    elif plane == "IF_yz":
        xcol, ycol = "source_IF_y_cm", "source_IF_z_cm"
    else:
        raise ValueError(plane)
    maximum = float(frame["selected_w2_rate_cps"].max())
    for row in frame.itertuples(index=False):
        rate = float(row.selected_w2_rate_cps)
        size = 18.0 + 105.0 * math.sqrt(rate / maximum)
        ax.scatter(
            float(getattr(row, xcol)),
            float(getattr(row, ycol)),
            s=size,
            marker=FAMILY_MARKERS.get(row.incident_family, "o"),
            facecolor=iso_colors[row.source_isotope],
            edgecolor="white",
            linewidth=0.65,
            alpha=0.95,
            zorder=20,
        )
    if label_top:
        for row in frame.nlargest(label_top, "selected_w2_rate_cps").itertuples(index=False):
            x, y = float(getattr(row, xcol)), float(getattr(row, ycol))
            ax.annotate(
                f"{row.source_point_id} {row.source_isotope}",
                (x, y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=6.2,
                color="#18232d",
                zorder=25,
            )


def plot_prompt_segments(ax, segments: pd.DataFrame, *, frame: str, axes: tuple[int, int]):
    if segments.empty:
        return
    start_cols, end_cols = segment_columns(segments)
    event_col = event_id_column(segments)
    if not start_cols or not end_cols or not event_col:
        return
    kind_col = first_column(segments, "segment_kind", "path_kind", "edge_kind")
    for row in segments.to_dict("records"):
        event_id = int(row[event_col])
        start = np.asarray([row[col] for col in start_cols], dtype=float)
        stop = np.asarray([row[col] for col in end_cols], dtype=float)
        if frame == "IF":
            start, stop = world_to_if(np.asarray([start, stop]))
        kind = str(row.get(kind_col, "interaction_chord")) if kind_col else "interaction_chord"
        linestyle = ":" if "deposit" in kind.lower() else "-"
        ax.plot(
            [start[axes[0]], stop[axes[0]]],
            [start[axes[1]], stop[axes[1]]],
            color=EVENT_COLORS.get(event_id, (0.85, 0.15, 0.15)),
            linewidth=1.45 if linestyle == "-" else 1.0,
            linestyle=linestyle,
            alpha=0.92,
            zorder=30,
        )


def plot_prompt_nodes(ax, table: pd.DataFrame, *, frame: str, axes: tuple[int, int]):
    if table.empty:
        return
    event_col = event_id_column(table)
    xyz = xyz_columns(table)
    process_col = first_column(table, "interaction", "process", "ia_process", "node_type")
    if not event_col or not xyz:
        return
    key_processes = {"INIT", "PAIR", "ANNI", "COMP", "PHOT"}
    for row in table.to_dict("records"):
        process = str(row.get(process_col, "IA")) if process_col else "IA"
        if process.upper() not in key_processes:
            continue
        point = np.asarray([row[col] for col in xyz], dtype=float)
        if frame == "IF":
            point = world_to_if(point)
        event_id = int(row[event_col])
        ax.scatter(
            point[axes[0]],
            point[axes[1]],
            s=30 if process.upper() in {"PAIR", "ANNI"} else 16,
            marker="*" if process.upper() == "PAIR" else ("o" if process.upper() == "ANNI" else "."),
            facecolor=EVENT_COLORS.get(event_id, "red"),
            edgecolor="black",
            linewidth=0.4,
            zorder=34,
        )


def plot_prompt_tes_audit(ax, prompt: dict[str, pd.DataFrame]):
    """Plot real TES CC deposits and fixed HTsim pixel centers only."""
    cc = prompt["cc"]
    if not cc.empty and {"tes_pixel_uid", "IF_y_cm", "IF_z_cm"} <= set(cc.columns):
        tes = cc[cc["tes_pixel_uid"].notna()].copy()
        maximum = max(float(tes["edep_keV"].max()), 1.0) if not tes.empty else 1.0
        for event_id, group in tes.groupby("local_event_id"):
            sizes = 5.0 + 22.0 * np.sqrt(group["edep_keV"].to_numpy(float) / maximum)
            ax.scatter(
                group["IF_y_cm"], group["IF_z_cm"], s=sizes,
                marker=".", color=EVENT_COLORS[int(event_id)], alpha=0.72,
                zorder=31,
            )

    htsim = prompt["htsim"]
    if not htsim.empty:
        fixed = htsim[
            htsim["coordinate_frame"].astype(str).eq("world_fixed_tes_pixel_center")
            & htsim["matched_pixel_uid"].notna()
        ].copy()
        events = prompt["events"].set_index("local_event_id")
        for event_id, group in fixed.groupby("local_event_id"):
            event_id = int(event_id)
            center_y = float(np.average(group["IF_y_cm"], weights=group["energy_keV"]))
            center_z = float(np.average(group["IF_z_cm"], weights=group["energy_keV"]))
            ax.scatter(
                center_y, center_z, s=88, marker="*",
                facecolor=EVENT_COLORS[event_id], edgecolor="black", linewidth=0.7,
                zorder=36,
            )
            event = events.loc[event_id]
            decision = "frozen PASS" if bool(event["frozen_pass"]) else "frozen reject"
            offsets = {3883: (10, 8), 19932: (10, -16), 8081: (-42, 8)}
            ax.annotate(
                f"ID {event_id}\n{decision}, L{int(event['deepest_measured_layer'])}",
                (center_y, center_z), xytext=offsets.get(event_id, (5, 5)), textcoords="offset points",
                fontsize=6.6, color=EVENT_COLORS[event_id], zorder=37,
            )


def axes_style(ax, xlabel: str, ylabel: str):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color="#dbe2e8", linewidth=0.45, alpha=0.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#76828c")
        spine.set_linewidth(0.65)


def build_figure(solids: list[Solid], points: pd.DataFrame, prompt: dict[str, pd.DataFrame]):
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.4,
            "axes.titlesize": 10.0,
            "axes.labelsize": 8.7,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "legend.fontsize": 7.0,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    iso_colors = isotope_colors(points["source_isotope"])
    segments = derive_prompt_segments(prompt)

    fig = plt.figure(figsize=(18.2, 13.6), constrained_layout=False)
    grid = fig.add_gridspec(2, 2, left=0.055, right=0.985, top=0.91, bottom=0.175, wspace=0.15, hspace=0.18)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    # A: all 3096 solids, already tilted in world coordinates.
    draw_projection(ax_a, solids, frame="world", axes=(0, 2), depth_axis=1)
    scatter_delayed(ax_a, points, plane="world_xz", iso_colors=iso_colors)
    plot_prompt_segments(ax_a, segments, frame="world", axes=(0, 2))
    plot_prompt_nodes(ax_a, prompt["ia"], frame="world", axes=(0, 2))
    axes_style(ax_a, "world X [cm]", "world Z [cm] — sky/up")
    ax_a.set_xlim(-49, 61)
    ax_a.set_ylim(-46, 61)
    ax_a.set_title("a  Flight-frame side view: all 3096 non-vacuum placements", loc="left", fontweight="bold")
    ax_a.annotate(
        "SKY / +Z",
        xy=(-43, 52), xytext=(-43, 39),
        arrowprops={"arrowstyle": "-|>", "color": "#174f77", "lw": 1.5},
        color="#174f77", ha="center", fontsize=8.2,
    )
    # Outward line of sight is -x_IF; photons propagate inward along +x_IF.
    center = np.array([-5.8, -1.6])
    sky_end = center + np.array([-25.0, 25.0])
    ax_a.annotate(
        "sky-facing optical axis\n45° elevation",
        xy=sky_end, xytext=center + np.array([-35.0, 30.0]),
        arrowprops={"arrowstyle": "-|>", "color": "#0b5e87", "lw": 1.6},
        color="#0b5e87", ha="center", fontsize=7.7,
    )
    ax_a.annotate(
        "incoming focused 511 keV",
        xy=center, xytext=sky_end,
        arrowprops={"arrowstyle": "-|>", "color": "#d6472f", "lw": 1.6},
        color="#d6472f", ha="right", fontsize=7.7,
    )

    # B: true mesh/plane intersection, not a schematic.
    draw_exact_section(ax_b, solids)
    axes_style(ax_b, "InstrumentFrame x′ [cm]", "InstrumentFrame z′ [cm]")
    ax_b.set_xlim(-42, 48)
    ax_b.set_ylim(-32, 50)
    ax_b.set_title("b  Exact native-mesh section at y′ = 0 (Boolean openings retained)", loc="left", fontweight="bold")

    # C: detector bay with event projections.
    outer_prefixes = (
        "GeoOpt_S2B_CryoShell_BPE5_",
        "GeoOpt_S2B_CryoShell_Plastic_",
        "BGO_S3C_FullWrap_",
        "BGO_S3D_O8_FullWrap_",
        "ActiveShield_S3C_BGO_Kapton_",
        "Outer_Al_S3C_BGO_Mechanical_",
    )
    draw_projection(
        ax_c, solids, frame="world", axes=(0, 2), depth_axis=1,
        name_filter=lambda name: not name.startswith(outer_prefixes),
    )
    scatter_delayed(ax_c, points, plane="world_xz", iso_colors=iso_colors, label_top=10)
    plot_prompt_segments(ax_c, segments, frame="world", axes=(0, 2))
    plot_prompt_nodes(ax_c, prompt["ia"], frame="world", axes=(0, 2))
    axes_style(ax_c, "world X [cm]", "world Z [cm] — sky/up")
    ax_c.set_xlim(-20, 20)
    ax_c.set_ylim(-20, 20)
    ax_c.set_title("c  Detector-bay zoom: outer veto envelopes removed for internal detail", loc="left", fontweight="bold")
    ax_c.text(
        0.01, 0.02,
        "Solid line: recorded IA interaction chord   ··· dotted: CC deposit polyline\n"
        "All three prompt events have BGO = plastic = 0 keV raw deposit.",
        transform=ax_c.transAxes, fontsize=6.9, ha="left", va="bottom",
        bbox={"facecolor": "white", "edgecolor": "#aab3bb", "alpha": 0.86, "pad": 2.5},
        zorder=40,
    )

    # D: all TES pixels overlap by layer in transverse view; still preserves every copy.
    draw_projection(
        ax_d,
        solids,
        frame="IF",
        axes=(1, 2),
        depth_axis=0,
        name_filter=lambda name: name.startswith("TP_L") or name.startswith("Si_Substrate_Stack"),
    )
    plot_prompt_tes_audit(ax_d, prompt)
    frozen_circle = plt.Circle((0, -5.2), 1.35, fill=False, color="#263642", lw=1.0, ls="--", zorder=35)
    ax_d.add_patch(frozen_circle)
    axes_style(ax_d, "InstrumentFrame y′ [cm]", "InstrumentFrame z′ [cm]")
    ax_d.set_xlim(-4.2, 4.2)
    ax_d.set_ylim(-8.2, 3.2)
    ax_d.set_title("d  TES transverse audit: fixed pixel centers and r = 1.35 cm gate", loc="left", fontweight="bold")

    fig.suptitle(
        "S3d-O8 mass model with TES-selected delayed activation and prompt paths",
        fontsize=15.0, fontweight="bold", x=0.055, ha="left", y=0.975, color="#18232d",
    )
    fig.text(
        0.055, 0.941,
        "Native Cosima/Geant4 CSG tessellation — S3d-O8, not Mass_model_511.  World +Z is sky/up; "
        "the side aperture points 45° upward.",
        fontsize=9.2, ha="left", color="#3d4a54",
    )

    material_handles = [
        Patch(facecolor=material_style(name)[0], edgecolor="none", label=name)
        for name in [
            "BGO", "PlasticScintillator", "BoratedPolyethylene5wtB", "Aluminium",
            "Copper", "Nb", "MuMetal", "W", "Ta", "Silicon",
        ]
    ]
    isotope_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markerfacecolor=color,
               markeredgecolor="white", markersize=5.5, label=name)
        for name, color in iso_colors.items()
    ]
    family_handles = [
        Line2D([0], [0], marker=marker, linestyle="none", color="#273540", markersize=5.5, label=family)
        for family, marker in FAMILY_MARKERS.items()
    ]
    prompt_handles = [
        Line2D([0], [0], color=color, lw=1.7, label=f"prompt {event_id}")
        for event_id, color in EVENT_COLORS.items()
    ]
    fig.legend(material_handles, [h.get_label() for h in material_handles], loc="lower left",
               bbox_to_anchor=(0.055, 0.105), ncol=5, frameon=False, title="Exact geometry material")
    fig.legend(isotope_handles, [h.get_label() for h in isotope_handles], loc="lower center",
               bbox_to_anchor=(0.52, 0.095), ncol=8, frameon=False, title="Delayed parent isotope (colour)")
    fig.legend(family_handles + prompt_handles, [h.get_label() for h in family_handles + prompt_handles],
               loc="lower right", bbox_to_anchor=(0.985, 0.105), ncol=3, frameon=False,
               title="Incident family (shape) / prompt event (line)")
    fig.text(
        0.055, 0.025,
        "Delayed markers are 66 exact sampled decay-source points representing 420 selected W2 events; marker size is a visual rate scale, not physical nuclide size.  "
        "Prompt lines show recorded IA chords and deposit loci, not every Geant4 step.  Full metadata are in the CSV ledgers.",
        fontsize=7.4, ha="left", color="#46535d",
    )

    for suffix in ("png", "svg", "pdf"):
        path = FIGURES / f"s3d_o8_mass_model_activation_prompt_detail.{suffix}"
        kwargs = {"dpi": 360} if suffix == "png" else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.08, **kwargs)
    plt.close(fig)


def clean_description(value: object) -> str:
    text = str(value).replace('"', "'").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def wrl_shape_sphere(position_mm, radius_mm, rgb, description: str, tag: str) -> str:
    x, y, z = position_mm
    return f"""# EVENT_MARKER {tag}
Transform {{
 translation {x:.6f} {y:.6f} {z:.6f}
 children [
  Anchor {{
   description \"{clean_description(description)}\"
   url \"\"
   children [
    Shape {{
     appearance Appearance {{ material Material {{ diffuseColor {rgb[0]:.5f} {rgb[1]:.5f} {rgb[2]:.5f} transparency 0.0 }} }}
     geometry Sphere {{ radius {radius_mm:.5f} }}
    }}
   ]
  }}
 ]
}}
"""


def wrl_line(start_mm, stop_mm, rgb, description: str, tag: str) -> str:
    return f"""# EVENT_SEGMENT {tag}
Anchor {{
 description \"{clean_description(description)}\"
 url \"\"
 children [
  Shape {{
   appearance Appearance {{ material Material {{ emissiveColor {rgb[0]:.5f} {rgb[1]:.5f} {rgb[2]:.5f} }} }}
   geometry IndexedLineSet {{
    coord Coordinate {{ point [ {start_mm[0]:.6f} {start_mm[1]:.6f} {start_mm[2]:.6f}, {stop_mm[0]:.6f} {stop_mm[1]:.6f} {stop_mm[2]:.6f} ] }}
    coordIndex [ 0, 1, -1 ]
   }}
  }}
 ]
}}
"""


def recolor_native_blocks(native_text: str, materials: dict[str, str]) -> str:
    pattern = re.compile(
        r"(#---------- SOLID: (.+?)\.0\n)(.*?)(?=\n#---------- SOLID:|\n#End of file\.)",
        re.S,
    )
    pieces: list[str] = []
    cursor = 0
    for match in pattern.finditer(native_text):
        pieces.append(native_text[cursor:match.start()])
        name = match.group(2)
        block = match.group(3)
        material = materials[name]
        rgb, transparency, _ = material_style(material)
        block = re.sub(
            r"diffuseColor\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+",
            f"diffuseColor {rgb[0]:.5f} {rgb[1]:.5f} {rgb[2]:.5f}",
            block,
            count=1,
        )
        block = re.sub(
            r"transparency\s+[-+0-9.eE]+",
            f"transparency {transparency:.5f}",
            block,
            count=1,
        )
        block = block.replace(
            f'description "{name}.0"',
            f'description "{name}; exact_material={material}; coordinates=world_mm"',
            1,
        )
        pieces.append(match.group(1) + block)
        cursor = match.end()
    pieces.append(native_text[cursor:])
    return "".join(pieces)


def origin_summary_by_point(origins: pd.DataFrame) -> dict[str, str]:
    result: dict[str, str] = {}
    if origins.empty:
        return result
    for point_id, group in origins.groupby("source_point_id"):
        projectiles = sorted(set(group["interacting_particle"].astype(str)))
        processes = sorted(set(group["creator_process"].astype(str)))
        result[str(point_id)] = (
            f"exact production ancestry: interacting_particle={','.join(projectiles)}; "
            f"creator_process={','.join(processes)}; links={len(group)}"
        )
    return result


def build_wrl(
    native_text: str,
    materials: dict[str, str],
    points: pd.DataFrame,
    origins: pd.DataFrame,
    prompt: dict[str, pd.DataFrame],
):
    colored = recolor_native_blocks(native_text, materials)
    colored = re.sub(
        r"#---------- CAMERA\nViewpoint\s*\{.*?\}\s*",
        """#---------- CAMERA / CORRECT FLIGHT ORIENTATION
WorldInfo { title \"S3d-O8 mass model + TES-selected activation/prompt loci\" info [ \"Geant4 native CSG tessellation; coordinates in world mm\", \"World +Z is sky/up; sky-facing aperture axis is -x_IF=(-1/sqrt2,0,+1/sqrt2)\" ] }
NavigationInfo { type [ \"EXAMINE\", \"ANY\" ] headlight TRUE }
Viewpoint { description \"Flight side view: +Z sky/up\" position 0 -2600 0 orientation 1 0 0 1.5707963268 fieldOfView 0.48 }
Viewpoint { description \"Opposite flight side view\" position 0 2600 0 orientation 1 0 0 -1.5707963268 fieldOfView 0.48 }
Viewpoint { description \"Top view\" position 0 0 2600 fieldOfView 0.48 }

""",
        colored,
        count=1,
        flags=re.S,
    )
    colored = colored.replace("\n#End of file.\n", "\n")
    iso_colors = isotope_colors(points["source_isotope"])
    origin_by_point = origin_summary_by_point(origins)
    overlays: list[str] = ["\n#---------- DELAYED ACTIVATION SOURCE POINTS (visual markers; not physical size)\n"]
    maximum = float(points["selected_w2_rate_cps"].max())
    for row in points.itertuples(index=False):
        position_mm = 10.0 * np.asarray(
            [row.source_world_x_cm, row.source_world_y_cm, row.source_world_z_cm], dtype=float
        )
        radius_mm = 2.0 + 4.2 * math.sqrt(float(row.selected_w2_rate_cps) / maximum)
        origin_text = origin_by_point.get(
            str(row.source_point_id),
            f"production ancestry not exact-linked; status={row.origin_match_status}",
        )
        description = (
            f"DELAYED {row.source_point_id}; isotope={row.source_isotope}; ZA={row.source_parent_ZA}; "
            f"incident_family={row.incident_family}; volume={row.source_volume}; exact_material={row.exact_material}; "
            f"world_cm=({row.source_world_x_cm},{row.source_world_y_cm},{row.source_world_z_cm}); "
            f"IF_cm=({row.source_IF_x_cm},{row.source_IF_y_cm},{row.source_IF_z_cm}); "
            f"selected_events={row.selected_event_rows}; W2_cps={row.selected_w2_rate_cps}; {origin_text}"
        )
        overlays.append(
            wrl_shape_sphere(
                position_mm,
                radius_mm,
                iso_colors[row.source_isotope][:3],
                description,
                f"DELAYED_{row.source_point_id}",
            )
        )

    segments = derive_prompt_segments(prompt)
    overlays.append("\n#---------- PROMPT W2 VETO-SURVIVOR PATHS\n")
    if not segments.empty:
        start_cols, end_cols = segment_columns(segments)
        event_col = event_id_column(segments)
        kind_col = first_column(segments, "segment_kind", "path_kind", "edge_kind")
        if start_cols and end_cols and event_col:
            for index, row in enumerate(segments.to_dict("records")):
                event_id = int(row[event_col])
                start_mm = 10.0 * np.asarray([row[col] for col in start_cols], dtype=float)
                stop_mm = 10.0 * np.asarray([row[col] for col in end_cols], dtype=float)
                kind = str(row.get(kind_col, "interaction_chord")) if kind_col else "interaction_chord"
                overlays.append(
                    wrl_line(
                        start_mm,
                        stop_mm,
                        EVENT_COLORS.get(event_id, (0.9, 0.1, 0.1)),
                        f"PROMPT event={event_id}; segment_kind={kind}; coordinates=world_mm",
                        f"PROMPT_{event_id}_{index:04d}",
                    )
                )

    ia = prompt["ia"]
    event_col = event_id_column(ia)
    xyz = xyz_columns(ia)
    process_col = first_column(ia, "interaction", "process", "ia_process", "node_type")
    ia_id_col = first_column(ia, "ia_id", "node_id")
    volume_col = first_column(
        ia,
        "host_volume_nearest_cc_within_0p01cm",
        "nearest_cc_volume",
        "resolved_host",
        "host_volume",
        "volume",
    )
    if not ia.empty and event_col and xyz:
        for row in ia.to_dict("records"):
            process = str(row.get(process_col, "IA")) if process_col else "IA"
            if process.upper() not in {"INIT", "PAIR", "ANNI", "COMP", "PHOT"}:
                continue
            event_id = int(row[event_col])
            position_mm = 10.0 * np.asarray([row[col] for col in xyz], dtype=float)
            description = (
                f"PROMPT event={event_id}; IA={row.get(ia_id_col, '') if ia_id_col else ''}; "
                f"process={process}; host={row.get(volume_col, '') if volume_col else ''}; coordinates=world_mm"
            )
            overlays.append(
                wrl_shape_sphere(
                    position_mm,
                    2.3 if process.upper() in {"PAIR", "ANNI"} else 1.5,
                    EVENT_COLORS.get(event_id, (0.9, 0.1, 0.1)),
                    description,
                    f"PROMPT_NODE_{event_id}_{row.get(ia_id_col, 'x') if ia_id_col else 'x'}",
                )
            )

    # Coordinate triad and sky-facing axis; 100 mm = 10 cm.
    overlays.extend(
        [
            "\n#---------- ORIENTATION GUIDE\n",
            wrl_line(np.array([500.0, -500.0, -350.0]), np.array([600.0, -500.0, -350.0]), (0.85, 0.15, 0.10), "+world X", "AXIS_X"),
            wrl_line(np.array([500.0, -500.0, -350.0]), np.array([500.0, -400.0, -350.0]), (0.10, 0.65, 0.20), "+world Y", "AXIS_Y"),
            wrl_line(np.array([500.0, -500.0, -350.0]), np.array([500.0, -500.0, -250.0]), (0.10, 0.30, 0.85), "+world Z = SKY/UP", "AXIS_Z_SKY"),
            wrl_line(np.array([-58.0, 0.0, -16.0]), np.array([-305.5, 0.0, 231.5]), (0.05, 0.42, 0.68), "sky-facing aperture axis: -x_IF, 45 degrees upward", "SKY_AXIS"),
        ]
    )
    FINAL_WRL.write_text(colored + "".join(overlays) + "\n#End of file.\n", encoding="utf-8")


def validate(
    solids: list[Solid],
    points: pd.DataFrame,
    delayed_events: pd.DataFrame,
    prompt: dict[str, pd.DataFrame],
):
    material_counts = pd.Series([solid.material for solid in solids]).value_counts().to_dict()
    names = {solid.name for solid in solids}
    expected_active = {
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    }
    prompt_events = prompt["events"]
    event_col = event_id_column(prompt_events)
    prompt_ids = sorted(set(prompt_events[event_col].astype(int))) if event_col else []
    prompt_segments = derive_prompt_segments(prompt)
    checks = {
        "native_nonvacuum_solids_3096": len(solids) == 3096,
        "all_six_active_veto_volumes_present": expected_active <= names,
        "delayed_event_rows_420": len(delayed_events) == 420,
        "delayed_source_points_66": len(points) == 66,
        "delayed_isotopes_15": points["source_isotope"].nunique() == 15,
        "delayed_w2_rate_event_point_agreement": math.isclose(
            float(delayed_events["w2_rate_cps"].sum()),
            float(points["selected_w2_rate_cps"].sum()),
            rel_tol=0.0,
            abs_tol=1e-14,
        ),
        "prompt_three_leak_events": prompt_ids == [3883, 8081, 19932],
        "prompt_segments_262": len(prompt_segments) == 262,
        "prompt_active_deposit_zero": bool(
            not prompt_events.empty
            and (prompt_events["bgo_raw_sum_keV"] == 0.0).all()
            and (prompt_events["plastic_raw_sum_keV"] == 0.0).all()
            and (prompt_events["active_cc_hit_count"] == 0).all()
        ),
        "final_wrl_exists": FINAL_WRL.exists(),
        "all_three_figure_formats_exist": all(
            (FIGURES / f"s3d_o8_mass_model_activation_prompt_detail.{suffix}").exists()
            for suffix in ("png", "svg", "pdf")
        ),
    }
    if FINAL_WRL.exists():
        final_text = FINAL_WRL.read_text(encoding="utf-8")
        checks.update(
            {
                "final_wrl_geometry_solids_3096": final_text.count("#---------- SOLID:") == 3096,
                "final_wrl_delayed_markers_66": final_text.count("# EVENT_MARKER DELAYED_") == 66,
                "final_wrl_prompt_segments_262": final_text.count("# EVENT_SEGMENT PROMPT_") == 262,
                "final_wrl_contains_all_three_prompt_ids": all(
                    f"PROMPT event={event_id};" in final_text for event_id in (3883, 19932, 8081)
                ),
                "final_wrl_has_correct_sky_axis": "sky-facing aperture axis: -x_IF, 45 degrees upward" in final_text,
            }
        )
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "model_identity": "S3d_O8",
        "explicit_non_identity": "Mass_model_511 is not used as the geometry surface",
        "geometry_authority": str(SETUP_GEO),
        "native_wrl": str(NATIVE_WRL),
        "final_wrl": str(FINAL_WRL),
        "native_coordinate_unit": "mm",
        "event_ledger_coordinate_unit": "cm",
        "orientation": {
            "world_up_sky": [0.0, 0.0, 1.0],
            "sky_facing_axis_minus_IF_x": [-1 / math.sqrt(2), 0.0, 1 / math.sqrt(2)],
            "incoming_focused_photon_plus_IF_x": [1 / math.sqrt(2), 0.0, -1 / math.sqrt(2)],
            "elevation_deg": 45.0,
        },
        "counts": {
            "native_nonvacuum_solids": len(solids),
            "native_vertices": int(sum(len(solid.vertices_mm) for solid in solids)),
            "native_faces": int(sum(len(solid.faces) for solid in solids)),
            "materials": material_counts,
            "delayed_event_rows": len(delayed_events),
            "delayed_source_points": len(points),
            "delayed_isotopes": int(points["source_isotope"].nunique()),
            "delayed_w2_rate_cps": float(points["selected_w2_rate_cps"].sum()),
            "prompt_event_ids": prompt_ids,
            "prompt_track_segments": len(prompt_segments),
        },
        "checks": checks,
    }
    (AUDIT / "visualization_validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result["status"] != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"Visualization validation failed: {failed}")


def main():
    for directory in (DATA, FIGURES, GEOMETRY_OUT, AUDIT):
        directory.mkdir(parents=True, exist_ok=True)
    materials, _ = parse_geo_materials()
    native_text, solids = parse_native_wrl(materials)
    if len(solids) != 3096:
        raise RuntimeError(f"Expected 3096 native solids, found {len(solids)}")
    points = pd.read_csv(DELAYED_POINTS)
    delayed_events = pd.read_csv(DELAYED_EVENTS)
    origins = pd.read_csv(DELAYED_ORIGINS)
    prompt = load_prompt_tables()
    build_wrl(native_text, materials, points, origins, prompt)
    build_figure(solids, points, prompt)
    validate(solids, points, delayed_events, prompt)
    print(f"Wrote {FINAL_WRL}")
    print(f"Wrote {FIGURES / 's3d_o8_mass_model_activation_prompt_detail.png'}")


if __name__ == "__main__":
    main()
