#!/usr/bin/env python3
"""Build the local near-TES activation cross-section figure.

The geometry is intersected directly with the native Geant4 mesh at
InstrumentFrame y'=0.  Delayed source points retain their exact 3-D ledger
coordinates but are orthographically projected into x'-z'; labels explicitly
show the true y' offset so the projection is not mistaken for an in-plane
decay.  Prompt lines are recorded IA chords/CC-deposit polylines, not complete
Geant4 step paths.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "audit"
FIGURES = ROOT / "figures"

MATERIAL_COLORS = {
    "Copper": "#d66a1f",
    "Nb": "#3568c8",
    "MuMetal": "#75449c",
    "SilverSinterProxy": "#9da3aa",
    "CuNi": "#8a684d",
    "Ta": "#a51f2d",
    "W": "#25282b",
    "Silicon": "#d6b94f",
    "Aluminium": "#77a8d0",
    "Be": "#a5d7df",
}
DEFAULT_COLOR = "#8c959c"

FAMILY_MARKERS = {
    "alpha": "^",
    "eminus": "v",
    "eplus": "o",
    "gamma": "s",
    "muminus": "P",
    "n": "D",
    "p": "X",
}

PROMPT_COLORS = {3883: "#df4a32", 19932: "#1f6fc2", 8081: "#a236a8"}

X_LIMITS = (-5.1, 5.1)
Z_LIMITS = (-10.2, 2.5)


def triangle_plane_segments(vertices: np.ndarray, triangles: np.ndarray, axis: int, value: float):
    """Return one line segment per non-coplanar triangle/plane crossing."""
    segments: list[np.ndarray] = []
    owners: list[int] = []
    eps = 1.0e-9
    for owner, tri_index in enumerate(triangles):
        tri = vertices[tri_index]
        distances = tri[:, axis] - value
        if np.all(distances > eps) or np.all(distances < -eps):
            continue
        points: list[np.ndarray] = []
        for i in range(3):
            j = (i + 1) % 3
            p0, p1 = tri[i], tri[j]
            d0, d1 = distances[i], distances[j]
            if abs(d0) <= eps:
                points.append(p0)
            if d0 * d1 < 0:
                points.append(p0 + (-d0 / (d1 - d0)) * (p1 - p0))
        unique: list[np.ndarray] = []
        for point in points:
            if not any(np.linalg.norm(point - prior) < 1.0e-7 for prior in unique):
                unique.append(point)
        if len(unique) < 2:
            continue
        if len(unique) > 2:
            a, b = max(
                ((a, b) for a in unique for b in unique),
                key=lambda pair: np.linalg.norm(pair[0] - pair[1]),
            )
        else:
            a, b = unique
        segments.append(np.asarray([a, b]))
        owners.append(owner)
    return segments, owners


def exact_local_section(ax, mesh: np.lib.npyio.NpzFile) -> None:
    vertices = mesh["vertices_instrument_cm"]
    triangles = mesh["triangles"]
    triangle_solid_ids = mesh["triangle_solid_ids"]
    materials = mesh["materials"]

    lines: list[np.ndarray] = []
    colors: list[str] = []
    widths: list[float] = []
    for tri_id, tri_index in enumerate(triangles):
        tri = vertices[tri_index]
        distances = tri[:, 1]
        eps = 1.0e-9
        if np.all(distances > eps) or np.all(distances < -eps):
            continue
        points: list[np.ndarray] = []
        for i in range(3):
            j = (i + 1) % 3
            p0, p1 = tri[i], tri[j]
            d0, d1 = distances[i], distances[j]
            if abs(d0) <= eps:
                points.append(p0)
            if d0 * d1 < 0:
                points.append(p0 + (-d0 / (d1 - d0)) * (p1 - p0))
        unique: list[np.ndarray] = []
        for point in points:
            if not any(np.linalg.norm(point - prior) < 1.0e-7 for prior in unique):
                unique.append(point)
        if len(unique) < 2:
            continue
        if len(unique) > 2:
            a, b = max(
                ((a, b) for a in unique for b in unique),
                key=lambda pair: np.linalg.norm(pair[0] - pair[1]),
            )
        else:
            a, b = unique
        line = np.asarray([[a[0], a[2]], [b[0], b[2]]])
        if (
            line[:, 0].max() < X_LIMITS[0]
            or line[:, 0].min() > X_LIMITS[1]
            or line[:, 1].max() < Z_LIMITS[0]
            or line[:, 1].min() > Z_LIMITS[1]
        ):
            continue
        material = str(materials[int(triangle_solid_ids[tri_id])])
        lines.append(line)
        colors.append(MATERIAL_COLORS.get(material, DEFAULT_COLOR))
        widths.append(0.62 if material in {"Copper", "Nb", "MuMetal", "Ta", "W"} else 0.38)

    ax.add_collection(
        LineCollection(lines, colors=colors, linewidths=widths, alpha=0.84, rasterized=True, zorder=2)
    )


def scatter_sources(ax, points: pd.DataFrame) -> None:
    maximum = float(points["selected_w2_rate_cps"].max())
    visible = points[
        points["source_IF_x_cm"].between(*X_LIMITS)
        & points["source_IF_z_cm"].between(*Z_LIMITS)
    ].copy()
    for row in visible.itertuples(index=False):
        rate = float(row.selected_w2_rate_cps)
        linked = int(row.exact_origin_linked_event_rows) > 0
        ax.scatter(
            row.source_IF_x_cm,
            row.source_IF_z_cm,
            s=24.0 + 150.0 * math.sqrt(rate / maximum),
            marker=FAMILY_MARKERS.get(row.incident_family, "o"),
            facecolor=MATERIAL_COLORS.get(row.exact_material, DEFAULT_COLOR),
            edgecolor="#111820" if linked else "white",
            linewidth=1.05 if linked else 0.75,
            alpha=0.95,
            zorder=25,
        )

    offsets = {
        "P0060": (-92, 20), "P0061": (-106, 25), "P0062": (-102, -29),
        "P0063": (-115, 2), "P0064": (18, 13), "P0065": (-108, 15),
        "P0066": (-112, -38), "P0046": (18, 28), "P0055": (18, -28),
        "P0056": (18, -4),
    }
    top = points.nlargest(10, "selected_w2_rate_cps")
    for row in top.itertuples(index=False):
        if not (X_LIMITS[0] <= row.source_IF_x_cm <= X_LIMITS[1] and Z_LIMITS[0] <= row.source_IF_z_cm <= Z_LIMITS[1]):
            continue
        label = f"{row.source_point_id}  {row.source_isotope} / {row.incident_family}\ny'={row.source_IF_y_cm:+.2f} cm"
        ax.annotate(
            label,
            (row.source_IF_x_cm, row.source_IF_z_cm),
            xytext=offsets.get(row.source_point_id, (12, 12)),
            textcoords="offset points",
            fontsize=6.7,
            color="#1d2933",
            arrowprops={"arrowstyle": "-", "lw": 0.55, "color": "#54616b"},
            bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "#aab4bc", "alpha": 0.90},
            zorder=35,
        )


def prompt_local_paths(ax) -> None:
    segments = pd.read_csv(DATA / "prompt_track_segments.csv")
    events = pd.read_csv(DATA / "prompt_events.csv")
    uid_to_id = dict(zip(events["event_uid"], events["local_event_id"]))
    for row in segments.itertuples(index=False):
        event_id = int(uid_to_id[row.event_uid])
        x = [row.start_IF_x_cm, row.end_IF_x_cm]
        z = [row.start_IF_z_cm, row.end_IF_z_cm]
        if max(x) < X_LIMITS[0] or min(x) > X_LIMITS[1] or max(z) < Z_LIMITS[0] or min(z) > Z_LIMITS[1]:
            continue
        dotted = "deposit" in str(row.segment_kind).lower()
        ax.plot(
            x,
            z,
            color=PROMPT_COLORS[event_id],
            linewidth=0.75 if dotted else 1.0,
            linestyle=":" if dotted else "-",
            alpha=0.52,
            zorder=18,
        )


def source_volume_bars(ax, delayed: pd.DataFrame) -> None:
    grouped = (
        delayed.groupby(["source_volume", "exact_material"], as_index=False)
        .agg(rows=("w2_rate_cps", "size"), rate_cps=("w2_rate_cps", "sum"))
        .sort_values("rate_cps", ascending=False)
        .head(10)
        .sort_values("rate_cps", ascending=True)
    )
    total = float(delayed["w2_rate_cps"].sum())
    labels = [
        name.replace("Cu_SubstrateSupport_", "Cu support: ")
        .replace("ColdPlate_", "Cold plate: ")
        .replace("MagShield_", "shield: ")
        for name in grouped["source_volume"]
    ]
    colors = [MATERIAL_COLORS.get(mat, DEFAULT_COLOR) for mat in grouped["exact_material"]]
    values = 1_000.0 * grouped["rate_cps"].to_numpy(float)
    bars = ax.barh(np.arange(len(grouped)), values, color=colors, edgecolor="white", height=0.72)
    ax.set_yticks(np.arange(len(grouped)), labels, fontsize=7.1)
    ax.set_xlabel("delayed W2 rate [mHz]")
    ax.grid(axis="x", color="#d9e0e5", linewidth=0.55)
    ax.set_axisbelow(True)
    ax.set_title("b  Main delayed near-field hosts (full 420-event W2 ledger)", loc="left", fontweight="bold")
    for bar, rate, rows in zip(bars, grouped["rate_cps"], grouped["rows"]):
        ax.text(
            bar.get_width() + 0.18,
            bar.get_y() + bar.get_height() / 2,
            f"{100*rate/total:.1f}%  ({int(rows)} rows)",
            va="center",
            fontsize=6.8,
            color="#293640",
        )
    ax.set_xlim(0, max(values) * 1.42)
    for spine in ax.spines.values():
        spine.set_color("#7c8993")
        spine.set_linewidth(0.65)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    mesh = np.load(DATA / "geometry_mesh_products.npz", allow_pickle=False)
    points = pd.read_csv(DATA / "delayed_source_point_ledger.csv")
    delayed = pd.read_csv(DATA / "delayed_selected_event_ledger.csv")

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10.2,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    fig = plt.figure(figsize=(17.2, 10.4))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.34, 1.0], left=0.055, right=0.975, top=0.865, bottom=0.24, wspace=0.31)
    ax = fig.add_subplot(grid[0, 0])
    ax_bar = fig.add_subplot(grid[0, 1])

    exact_local_section(ax, mesh)
    prompt_local_paths(ax)
    scatter_sources(ax, points)
    ax.set_xlim(*X_LIMITS)
    ax.set_ylim(*Z_LIMITS)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("InstrumentFrame x' [cm]  (focused 511 keV propagates toward +x')")
    ax.set_ylabel("InstrumentFrame z' [cm]")
    ax.grid(color="#dce3e8", linewidth=0.45, alpha=0.72)
    ax.set_axisbelow(True)
    ax.set_title("a  Exact native-mesh section at y'=0 + projected activation points", loc="left", fontweight="bold")
    for spine in ax.spines.values():
        spine.set_color("#7c8993")
        spine.set_linewidth(0.65)

    # Component labels use their true section locations, not point-ledger inference.
    component_labels = [
        ("MXC Cu plate", (-0.1, 0.05), (-4.8, 1.3)),
        ("MuMetal 2 mm", (-4.32, -8.6), (-4.95, -9.95)),
        ("Nb 2 mm", (-3.82, -8.2), (-3.25, -9.45)),
        ("TES + Cu supports", (0.15, -5.2), (-1.3, -4.45)),
        ("50 mK Cu can bottom", (0.0, -9.8), (0.65, -10.05)),
        ("DR Cu / Ag proxy", (0.4, 1.25), (1.15, 2.05)),
    ]
    for text, xy, xytext in component_labels:
        ax.annotate(
            text, xy=xy, xytext=xytext, fontsize=7.0, color="#26333d",
            arrowprops={"arrowstyle": "-", "color": "#53616a", "lw": 0.65}, zorder=12,
        )
    ax.annotate(
        "focused 511 keV",
        xy=(-1.7, -5.2), xytext=(-4.7, -5.2),
        arrowprops={"arrowstyle": "-|>", "color": "#c33c2c", "lw": 1.45},
        color="#c33c2c", va="center", fontsize=7.4, zorder=40,
    )

    source_volume_bars(ax_bar, delayed)
    ax_bar.text(
        0.01, 0.02,
        "Prompt Step05: 0.0338429 cps from only two equal-weight gamma pair/annihilation chains:\n"
        "Nb inner cylinder -> MuMetal outer cylinder; MXC Cu -> MXC Cu.",
        transform=ax_bar.transAxes, fontsize=7.1, color="#26333d", ha="left", va="bottom",
        bbox={"boxstyle": "round,pad=0.35", "fc": "#f7f8f9", "ec": "#aeb7bd", "alpha": 0.96},
    )

    fig.suptitle(
        "S3d-O8 local near-field background: true geometry, activation coordinates, and prompt chords",
        x=0.055, y=0.965, ha="left", fontsize=15.0, fontweight="bold", color="#18242d",
    )
    fig.text(
        0.055, 0.917,
        "This is S3d-O8. Geometry is the native Cosima/Geant4 CSG mesh. Activation markers are exact 3-D decay-source coordinates projected into x'-z'; each top label reports the true y' offset.",
        ha="left", fontsize=8.8, color="#3f4d57",
    )

    material_handles = [
        Patch(facecolor=color, edgecolor="none", label=name)
        for name, color in MATERIAL_COLORS.items()
        if name in {"Copper", "Nb", "MuMetal", "SilverSinterProxy", "CuNi", "Ta", "Silicon", "Aluminium"}
    ]
    family_handles = [
        Line2D([0], [0], marker=marker, linestyle="none", markerfacecolor="#58636c", markeredgecolor="white", markersize=6, label=family)
        for family, marker in FAMILY_MARKERS.items()
    ]
    prompt_handles = [
        Line2D([0], [0], color=color, lw=1.4, label=f"prompt ID {event_id}")
        for event_id, color in PROMPT_COLORS.items()
    ]
    fig.legend(material_handles, [h.get_label() for h in material_handles], loc="lower left", bbox_to_anchor=(0.055, 0.105), ncol=8, frameon=False, title="Geometry / source material colour")
    fig.legend(family_handles + prompt_handles, [h.get_label() for h in family_handles + prompt_handles], loc="lower left", bbox_to_anchor=(0.055, 0.065), ncol=10, frameon=False, title="Activation incident-family branch / prompt chord")
    fig.text(
        0.055, 0.022,
        "Black marker rim: at least one exact production-origin link exists for that source point; white rim: direct interacting particle/process remains unscanned or unlinked.  "
        "Marker size follows selected W2 rate. Prompt lines connect recorded IA/CC vertices and are not complete transport tracks.\n"
        "Rate share mixes activation yield and exact-position detector coupling; it is not a mass fraction and cannot be read as proportional benefit from removing that material.",
        fontsize=7.1, color="#46545e", ha="left",
    )

    for suffix in ("png", "svg", "pdf"):
        path = FIGURES / f"s3d_o8_nearfield_activation_detail.{suffix}"
        kwargs = {"dpi": 360} if suffix == "png" else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.08, **kwargs)
    plt.close(fig)

    visible_points = points[
        points["source_IF_x_cm"].between(*X_LIMITS)
        & points["source_IF_z_cm"].between(*Z_LIMITS)
    ]
    prompt_ids = sorted(
        int(value)
        for value in pd.read_csv(DATA / "prompt_events.csv")["local_event_id"].unique()
    )
    checks = {
        "source_point_rows_66": len(points) == 66,
        "delayed_event_rows_420": len(delayed) == 420,
        "delayed_w2_rate_closure": math.isclose(
            float(delayed["w2_rate_cps"].sum()), 0.0544797522273, abs_tol=1.0e-12
        ),
        "prompt_ids_exact": prompt_ids == [3883, 8081, 19932],
        "native_mesh_coordinate_arrays_present": all(
            key in mesh for key in ("vertices_instrument_cm", "triangles", "triangle_solid_ids", "materials")
        ),
        "all_outputs_nonempty": all(
            (FIGURES / f"s3d_o8_nearfield_activation_detail.{suffix}").stat().st_size > 0
            for suffix in ("png", "svg", "pdf")
        ),
    }
    payload = {
        "status": "PASS_NEARFIELD_FIGURE" if all(checks.values()) else "FAIL_NEARFIELD_FIGURE",
        "checks": checks,
        "geometry": "S3d-O8 native Cosima/Geant4 CSG mesh",
        "section": {"plane": "InstrumentFrame y'=0", "x_cm": X_LIMITS, "z_cm": Z_LIMITS},
        "point_semantics": (
            "Exact 3-D decay-source coordinates orthographically projected into x'-z'; true y' is retained in labels/data."
        ),
        "source_points_total": int(len(points)),
        "source_points_visible_in_plot_range": int(len(visible_points)),
        "prompt_ids": prompt_ids,
    }
    with (AUDIT / "nearfield_figure_validation.json").open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
