#!/usr/bin/env python3
"""Build the two required SE3 geometry figure sets from the native mesh.

Inputs are the parser-validated NPZ/manifest and the exact hole/mass ledgers.
No historical transport overlays are read or drawn.  Native WRL coordinates
remain world millimetres; plotted coordinates are centimetres.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection, PatchCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Rectangle

from build_se3_mesh_products import (
    PLATES,
    ROOT,
    atomic_json,
    file_record,
    read_hole_ledger,
)


DATA_DIR = ROOT / "data"
FIGURE_DIR = ROOT / "figures"
AUDIT_DIR = ROOT / "audit"

DEFAULT_MESH = DATA_DIR / "se3_geometry_mesh_products.npz"
DEFAULT_MANIFEST = DATA_DIR / "se3_geometry_volume_manifest.csv"
DEFAULT_HOLES = DATA_DIR / "se3_hole_pattern.csv"
DEFAULT_MASS = DATA_DIR / "se3_mass_ledger.csv"
DEFAULT_MESH_AUDIT = AUDIT_DIR / "se3_mesh_validation.json"
DEFAULT_NAVIGATION_AUDIT = AUDIT_DIR / "se3_geometry_navigation.json"
DEFAULT_AUDIT = AUDIT_DIR / "se3_visual_validation.json"

DETAIL_STEM = "se3_mass_model_detail"
DIMENSION_STEM = "se3_dimensioned_sections"

MATERIAL_STYLE: dict[str, tuple[tuple[float, float, float], float]] = {
    "Ta": ((0.66, 0.10, 0.12), 0.50),
    "W": ((0.08, 0.09, 0.11), 0.46),
    "Copper": ((0.87, 0.36, 0.10), 0.28),
    "Aluminium": ((0.38, 0.62, 0.84), 0.18),
    "Silicon": ((0.90, 0.78, 0.35), 0.36),
    "BGO": ((0.10, 0.61, 0.33), 0.17),
    "PlasticScintillator": ((0.07, 0.70, 0.72), 0.14),
    "BoratedPolyethylene5wtB": ((0.72, 0.62, 0.31), 0.13),
    "Kapton": ((0.93, 0.53, 0.10), 0.19),
    "StainlessSteel": ((0.48, 0.53, 0.58), 0.22),
    "G10": ((0.39, 0.48, 0.24), 0.24),
    "CuNi": ((0.55, 0.37, 0.24), 0.28),
    "NbTiCableProxy": ((0.12, 0.52, 0.65), 0.28),
    "Be": ((0.74, 0.88, 0.91), 0.42),
    "SilverSinterProxy": ((0.76, 0.77, 0.80), 0.40),
    "CharcoalProxy": ((0.18, 0.18, 0.18), 0.34),
    "Vacuum": ((0.12, 0.42, 0.72), 0.0),
}
DEFAULT_STYLE = ((0.56, 0.58, 0.61), 0.22)

OUTER_PREFIXES = (
    "GeoOpt_S2B_CryoShell_BPE5_",
    "GeoOpt_S2B_CryoShell_Plastic_",
    "BGO_S3C_FullWrap_",
    "BGO_S3D_O8_FullWrap_",
    "ActiveShield_S3C_BGO_Kapton_",
    "Outer_Al_S3C_BGO_Mechanical_",
)

LAYER_SPECS = (
    ("BGO window", "BGO_S3C_FullWrap_SideShell_WindowCut_40mm", 4.0, "#1c9851"),
    ("uncut plastic", "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm", 1.0, "#10aeb2"),
    ("BPE focused port", "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm", 2.0, "#b99b39"),
)


class VisualError(RuntimeError):
    pass


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise VisualError(f"Empty SE3 mesh manifest: {path}")
    return rows


def read_mass_ledger(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row.get("component", ""): row for row in rows if row.get("component")}


def load_mesh(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    required = {
        "vertices_world_mm", "vertices_instrument_cm", "triangles", "triangle_solid_ids",
        "solid_names", "materials", "is_nonvacuum", "is_plate_hole",
        "instrument_bounds_per_solid_cm", "world_from_instrument_rotation",
        "instrument_position_world_cm", "instrument_rotation_xyz_deg",
    }
    missing = required - set(data)
    if missing:
        raise VisualError(f"Mesh NPZ lacks arrays: {sorted(missing)}")
    return data


def material_style(material: str) -> tuple[tuple[float, float, float], float]:
    return MATERIAL_STYLE.get(material, DEFAULT_STYLE)


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.3,
            "axes.titlesize": 10.0,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def axes_style(ax: plt.Axes, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color="#dbe2e8", linewidth=0.45, alpha=0.72)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#76828c")
        spine.set_linewidth(0.65)


def draw_projection(
    ax: plt.Axes,
    mesh: dict[str, np.ndarray],
    *,
    frame: str,
    axes: tuple[int, int],
    depth_axis: int,
    solid_mask: np.ndarray,
) -> None:
    vertices = (
        mesh["vertices_world_mm"] / 10.0 if frame == "world" else mesh["vertices_instrument_cm"]
    )
    triangle_solid_ids = mesh["triangle_solid_ids"]
    chosen = np.flatnonzero(solid_mask[triangle_solid_ids])
    triangles = mesh["triangles"][chosen]
    if len(triangles) == 0:
        raise VisualError("Projection selection contains no triangles")
    triangle_vertices = vertices[triangles]
    depths = triangle_vertices[:, :, depth_axis].mean(axis=1)
    order = np.argsort(depths)
    polygons = triangle_vertices[order][:, :, axes]
    materials = mesh["materials"]
    selected_solid_ids = triangle_solid_ids[chosen][order]
    colors = np.asarray(
        [(*material_style(str(materials[solid_id]))[0], material_style(str(materials[solid_id]))[1])
         for solid_id in selected_solid_ids],
        dtype=float,
    )
    ax.add_collection(
        PolyCollection(polygons, facecolors=colors, edgecolors="none", rasterized=True)
    )
    ax.autoscale_view()


def triangle_plane_segments(triangle: np.ndarray, axis: int, value: float = 0.0) -> list[np.ndarray]:
    distances = triangle[:, axis] - value
    epsilon = 1.0e-8
    points: list[np.ndarray] = []
    if np.all(np.abs(distances) <= epsilon):
        return [np.asarray((triangle[index], triangle[(index + 1) % 3])) for index in range(3)]
    for index in range(3):
        other = (index + 1) % 3
        start, stop = triangle[index], triangle[other]
        d_start, d_stop = distances[index], distances[other]
        if abs(d_start) <= epsilon:
            points.append(start)
        if d_start * d_stop < 0:
            fraction = -d_start / (d_stop - d_start)
            points.append(start + fraction * (stop - start))
    unique: list[np.ndarray] = []
    for point in points:
        if not any(np.linalg.norm(point - prior) < 1.0e-6 for prior in unique):
            unique.append(point)
    if len(unique) < 2:
        return []
    if len(unique) > 2:
        start, stop = max(
            ((a, b) for a in unique for b in unique),
            key=lambda pair: float(np.linalg.norm(pair[0] - pair[1])),
        )
        return [np.asarray((start, stop))]
    return [np.asarray((unique[0], unique[1]))]


def draw_exact_if_section(
    ax: plt.Axes,
    mesh: dict[str, np.ndarray],
    *,
    include_holes: bool = True,
    limits: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> None:
    vertices = mesh["vertices_instrument_cm"]
    triangles = mesh["triangles"]
    triangle_solid_ids = mesh["triangle_solid_ids"]
    bounds = mesh["instrument_bounds_per_solid_cm"]
    nonvacuum = mesh["is_nonvacuum"]
    holes = mesh["is_plate_hole"]
    crosses = (bounds[:, 0, 1] <= 1.0e-8) & (bounds[:, 1, 1] >= -1.0e-8)
    allowed = crosses & (nonvacuum | (holes if include_holes else False))
    chosen = np.flatnonzero(allowed[triangle_solid_ids])
    lines: list[np.ndarray] = []
    colors: list[tuple[float, float, float, float]] = []
    widths: list[float] = []
    materials = mesh["materials"]
    for triangle_id in chosen:
        solid_id = int(triangle_solid_ids[triangle_id])
        triangle = vertices[triangles[triangle_id]]
        for segment in triangle_plane_segments(triangle, axis=1):
            projected = segment[:, (0, 2)]
            if limits is not None:
                (xmin, xmax), (zmin, zmax) = limits
                if (
                    projected[:, 0].max() < xmin or projected[:, 0].min() > xmax
                    or projected[:, 1].max() < zmin or projected[:, 1].min() > zmax
                ):
                    continue
            if holes[solid_id]:
                colors.append((0.05, 0.30, 0.68, 0.92))
                widths.append(0.48)
            else:
                rgb, _ = material_style(str(materials[solid_id]))
                colors.append((*rgb, 0.84))
                widths.append(0.36 if str(materials[solid_id]) not in {"Ta", "W"} else 0.54)
            lines.append(projected)
    if not lines:
        raise VisualError("Exact y-prime=0 section contains no segments")
    ax.add_collection(LineCollection(lines, colors=colors, linewidths=widths, rasterized=True))
    ax.autoscale_view()


def solid_index(mesh: dict[str, np.ndarray], name: str) -> int:
    matches = np.flatnonzero(mesh["solid_names"] == name)
    if len(matches) != 1:
        raise VisualError(f"Expected one mesh solid named {name}, found {len(matches)}")
    return int(matches[0])


def if_to_world_cm(mesh: dict[str, np.ndarray], point_if_cm: np.ndarray) -> np.ndarray:
    return point_if_cm @ mesh["world_from_instrument_rotation"].T + mesh["instrument_position_world_cm"]


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for suffix in ("png", "svg", "pdf"):
        path = FIGURE_DIR / f"{stem}.{suffix}"
        kwargs: dict[str, Any] = {"dpi": 360} if suffix == "png" else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.08, **kwargs)
        outputs.append(path)
    return outputs


def build_detail_figure(mesh: dict[str, np.ndarray]) -> tuple[list[Path], dict[str, Any]]:
    configure_matplotlib()
    names = mesh["solid_names"].astype(str)
    nonvacuum = mesh["is_nonvacuum"]
    fig = plt.figure(figsize=(18.2, 13.4))
    grid = fig.add_gridspec(2, 2, left=0.055, right=0.985, top=0.90, bottom=0.10,
                            wspace=0.14, hspace=0.18)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    draw_projection(ax_a, mesh, frame="world", axes=(0, 2), depth_axis=1, solid_mask=nonvacuum)
    axes_style(ax_a, "world X [cm]", "world Z [cm] — SKY / UP")
    ax_a.set_xlim(-49, 61)
    ax_a.set_ylim(-46, 61)
    ax_a.set_title(f"a  Flight side view: all {int(nonvacuum.sum())} non-vacuum placements",
                   loc="left", fontweight="bold")
    ax_a.annotate("SKY / +Z", xy=(-43, 53), xytext=(-43, 40),
                  arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": "#174f77"},
                  color="#174f77", ha="center")
    window_id = solid_index(mesh, "Win_MagShield_Al_foil_side")
    window_center_if = mesh["instrument_bounds_per_solid_cm"][window_id].mean(axis=0)
    outward_end_if = window_center_if + np.asarray((-25.0, 0.0, 0.0))
    center_world = if_to_world_cm(mesh, window_center_if)[[0, 2]]
    outward_world = if_to_world_cm(mesh, outward_end_if)[[0, 2]]
    ax_a.annotate("sky-facing optical axis\n−x′, 45° elevation", xy=outward_world,
                  xytext=outward_world + np.asarray((-9.0, 4.0)),
                  arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": "#0b5e87"},
                  color="#0b5e87", ha="center")
    ax_a.annotate("incoming focused photons (+x′)", xy=center_world, xytext=outward_world,
                  arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": "#d6472f"},
                  color="#d6472f", ha="right")

    draw_exact_if_section(ax_b, mesh, include_holes=True)
    axes_style(ax_b, "InstrumentFrame x′ [cm]", "InstrumentFrame z′ [cm]")
    ax_b.set_xlim(-42, 48)
    ax_b.set_ylim(-32, 50)
    ax_b.set_title("b  Native-mesh section at y′ = 0 (visible Vacuum-hole boundaries)",
                   loc="left", fontweight="bold")

    outer = np.asarray([str(name).startswith(OUTER_PREFIXES) for name in names], dtype=bool)
    draw_projection(ax_c, mesh, frame="world", axes=(0, 2), depth_axis=1,
                    solid_mask=nonvacuum & ~outer)
    axes_style(ax_c, "world X [cm]", "world Z [cm] — SKY / UP")
    ax_c.set_xlim(-20, 20)
    ax_c.set_ylim(-20, 20)
    ax_c.set_title("c  Detector-bay zoom: outer veto envelopes hidden for internal detail",
                   loc="left", fontweight="bold")
    for shield_name in (
        "SE3_Al_Shield_Inner_Cylinder_2mm",
        "SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm",
    ):
        index = solid_index(mesh, shield_name)
        centre = (mesh["world_bounds_per_solid_mm"][index].mean(axis=0) / 10.0)[[0, 2]]
        ax_c.annotate("SE3 Al", xy=centre, xytext=centre + (2.0, 2.2), fontsize=6.9,
                      arrowprops={"arrowstyle": "->", "lw": 0.7, "color": "#275e91"},
                      color="#275e91")

    window_bounds = mesh["instrument_bounds_per_solid_cm"][window_id]
    aperture_center = window_bounds.mean(axis=0)[[1, 2]]
    aperture_span = (window_bounds[1] - window_bounds[0])[[1, 2]]
    y0, z0 = aperture_center
    half_y, half_z = aperture_span / 2.0
    ax_d.add_patch(Rectangle((y0 - 3.2, z0 - 3.2), 6.4, 6.4,
                             facecolor="#16aeb2", alpha=0.13, edgecolor="#0a8084",
                             hatch="////", linewidth=0.9, label="uncut 10 mm plastic"))
    ax_d.add_patch(Rectangle((y0 - half_y, z0 - half_z), aperture_span[0], aperture_span[1],
                             fill=False, edgecolor="#b99b39", linewidth=2.0,
                             label="BPE focused port"))
    ax_d.add_patch(Rectangle((y0 - half_y, z0 - half_z), aperture_span[0], aperture_span[1],
                             fill=False, edgecolor="#1c9851", linewidth=1.2, linestyle="--",
                             label="BGO/window registration"))
    grid_values = np.linspace(-0.82, 0.82, 7)
    ray_y, ray_z = np.meshgrid(y0 + half_y * grid_values, z0 + half_z * grid_values)
    ax_d.scatter(
        ray_y, ray_z, s=8, color="#d6472f", alpha=0.78,
        label="schematic focused bundle (not event data)",
    )
    ax_d.axhline(z0, color="#52616c", lw=0.55)
    ax_d.axvline(y0, color="#52616c", lw=0.55)
    axes_style(ax_d, "InstrumentFrame y′ [cm]", "InstrumentFrame z′ [cm]")
    ax_d.set_xlim(y0 - 3.4, y0 + 3.4)
    ax_d.set_ylim(z0 - 3.4, z0 + 3.4)
    ax_d.set_title("d  Focused window face, looking inward along +x′", loc="left", fontweight="bold")
    ax_d.legend(loc="upper right", frameon=True)
    ax_d.text(y0, z0 - 2.95,
              "37.96 × 37.96 mm; focused rays cross intact plastic (not vacuum)",
              ha="center", va="bottom", fontsize=7.1, color="#25333d",
              bbox={"facecolor": "white", "edgecolor": "#aab3bb", "alpha": 0.85})

    fig.suptitle("SE3 mass-model geometry detail", x=0.055, y=0.975, ha="left",
                 fontsize=15.0, fontweight="bold", color="#18232d")
    fig.text(0.055, 0.94,
             "Native Cosima/Geant4 tessellation; world +Z is sky/up; the −x′ aperture axis points 45° upward.  "
             "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN.",
             ha="left", fontsize=9.1, color="#3d4a54")
    material_order = [
        "BGO", "PlasticScintillator", "BoratedPolyethylene5wtB", "Aluminium",
        "Copper", "W", "Ta", "Silicon",
    ]
    handles = [Patch(facecolor=material_style(name)[0], edgecolor="none", label=name)
               for name in material_order]
    handles.append(Line2D([0], [0], color="#0d4cac", lw=1.2, label="Vacuum hole boundary"))
    fig.legend(handles=handles, loc="lower center", ncol=9, frameon=False,
               bbox_to_anchor=(0.52, 0.025), title="Exact geometry material / visible daughter boundary")
    outputs = save_figure(fig, DETAIL_STEM)
    plt.close(fig)
    return outputs, {
        "panel_count": 4,
        "aperture_center_yz_cm": aperture_center.tolist(),
        "aperture_span_yz_cm": aperture_span.tolist(),
        "window_center_if_cm": window_center_if.tolist(),
    }


def line_intervals_x_prime(
    mesh: dict[str, np.ndarray], name: str, *, y_cm: float, z_cm: float
) -> list[tuple[float, float]]:
    solid_id = solid_index(mesh, name)
    chosen = np.flatnonzero(mesh["triangle_solid_ids"] == solid_id)
    vertices = mesh["vertices_instrument_cm"]
    triangles = mesh["triangles"]
    point = np.asarray((y_cm, z_cm), dtype=float)
    intersections: list[float] = []
    tolerance = 1.0e-9
    for triangle_id in chosen:
        triangle = vertices[triangles[triangle_id]]
        a, b, c = triangle[:, (1, 2)]
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) <= tolerance:
            continue
        weight_a = ((b[1] - c[1]) * (point[0] - c[0]) + (c[0] - b[0]) * (point[1] - c[1])) / denominator
        weight_b = ((c[1] - a[1]) * (point[0] - c[0]) + (a[0] - c[0]) * (point[1] - c[1])) / denominator
        weight_c = 1.0 - weight_a - weight_b
        if min(weight_a, weight_b, weight_c) >= -1.0e-8:
            intersections.append(float(weight_a * triangle[0, 0] + weight_b * triangle[1, 0] + weight_c * triangle[2, 0]))
    intersections.sort()
    unique: list[float] = []
    for value in intersections:
        if not unique or abs(value - unique[-1]) > 2.0e-5:
            unique.append(value)
    if len(unique) % 2:
        raise VisualError(f"Odd number of native-mesh line intersections for {name}: {unique}")
    return list(zip(unique[0::2], unique[1::2]))


def negative_chord(intervals: list[tuple[float, float]]) -> float:
    return sum(max(0.0, min(stop, 0.0) - start) for start, stop in intervals if start < 0.0)


def build_dimension_figure(
    mesh: dict[str, np.ndarray], hole_records, mass_by_component: dict[str, dict[str, str]],
    navigation_audit: dict[str, Any],
) -> tuple[list[Path], dict[str, Any]]:
    configure_matplotlib()
    fig = plt.figure(figsize=(19.0, 18.5))
    outer = fig.add_gridspec(3, 1, left=0.055, right=0.985, top=0.93, bottom=0.06,
                             height_ratios=(1.05, 1.0, 0.62), hspace=0.30)
    ax_a = fig.add_subplot(outer[0, 0])
    draw_exact_if_section(ax_a, mesh, include_holes=True, limits=((-20, 20), (-9, 32)))
    axes_style(ax_a, "InstrumentFrame x′ [cm]", "InstrumentFrame z′ [cm]")
    ax_a.set_xlim(-20, 20)
    ax_a.set_ylim(-9, 32)
    ax_a.set_title("a  Dimensioned x′–z′ native-mesh section", loc="left", fontweight="bold")
    for plate in PLATES:
        mass = mass_by_component.get(plate.name, {})
        mass_text = f", {float(mass['mass_after_kg']):.3f} kg" if mass.get("mass_after_kg") else ""
        ax_a.plot((-plate.radius_cm, plate.radius_cm), (plate.center_z_cm, plate.center_z_cm),
                  color="#8e3b12", lw=0.7, ls="--")
        ax_a.text(plate.radius_cm + 0.35, plate.center_z_cm,
                  f"{plate.short_label}: R{plate.radius_cm*10:.0f}, t=4 mm{mass_text}",
                  va="center", fontsize=7.0, color="#7a2f10")
    ax_a.annotate("sky-facing −x′", xy=(-18.0, -7.3), xytext=(-10.0, -7.3),
                  arrowprops={"arrowstyle": "-|>", "lw": 1.4, "color": "#0b5e87"},
                  color="#0b5e87", ha="center")
    ax_a.annotate("world +Z / SKY", xy=(-15.2, 30.0), xytext=(-9.0, 24.0),
                  arrowprops={"arrowstyle": "-|>", "lw": 1.4, "color": "#174f77"},
                  color="#174f77", ha="center")
    ax_a.text(-19.2, -5.5,
              "SE3 Al shield: cylinder z_local −38.5…+41.0 mm; back annulus +41.0…+43.0 mm; wall 2 mm",
              fontsize=7.0, ha="left", color="#275e91",
              bbox={"facecolor": "white", "edgecolor": "#8aa9c2", "alpha": 0.87})

    plate_grid = outer[1, 0].subgridspec(1, 5, wspace=0.23)
    accepted_counts: dict[str, int] = {}
    skipped_counts: dict[str, int] = {}
    hole_diameters_mm: dict[str, float] = {}
    hole_radius_uniform: dict[str, bool] = {}
    accepted_hole_areas_cm2: dict[str, float] = {}
    mass_ledger_void_areas_cm2: dict[str, float] = {}
    hole_area_matches_mass_ledger: dict[str, bool] = {}
    keepout_reason_counts: dict[str, dict[str, int]] = {}
    candidate_decision_counts: dict[str, dict[str, int]] = {}
    for index, plate in enumerate(PLATES):
        ax = fig.add_subplot(plate_grid[0, index])
        rows = [record for record in hole_records if record.plate == plate.name]
        accepted = [record for record in rows if record.accepted]
        skipped = [record for record in rows if not record.accepted]
        accepted_counts[plate.name] = len(accepted)
        skipped_counts[plate.name] = len(skipped)
        accepted_radii = np.asarray([row.radius_cm for row in accepted], dtype=float)
        radius_uniform = bool(
            len(accepted_radii)
            and np.allclose(accepted_radii, accepted_radii[0], rtol=0.0, atol=1.0e-10)
        )
        hole_radius_uniform[plate.name] = radius_uniform
        diameter_mm = float(2.0 * accepted_radii[0] * 10.0) if radius_uniform else float("nan")
        hole_diameters_mm[plate.name] = diameter_mm
        accepted_area = float(sum(math.pi * row.radius_cm**2 for row in accepted))
        accepted_hole_areas_cm2[plate.name] = accepted_area
        mass_row = mass_by_component.get(plate.name, {})
        if mass_row.get("void_cm3") and mass_row.get("thickness_after_cm"):
            mass_area = float(mass_row["void_cm3"]) / float(mass_row["thickness_after_cm"])
            mass_ledger_void_areas_cm2[plate.name] = mass_area
            hole_area_matches_mass_ledger[plate.name] = math.isclose(
                accepted_area, mass_area, rel_tol=2.0e-10, abs_tol=2.0e-10
            )
        else:
            mass_ledger_void_areas_cm2[plate.name] = float("nan")
            hole_area_matches_mass_ledger[plate.name] = False
        reason_counts: Counter[str] = Counter()
        for record in skipped:
            tokens = {
                token.strip()
                for token in record.keepout_reason.split(";")
                if token.strip()
            }
            tokens.add(record.decision or "SKIPPED_UNSPECIFIED")
            reason_counts.update(tokens)
        keepout_reason_counts[plate.name] = dict(sorted(reason_counts.items()))
        candidate_decision_counts[plate.name] = dict(
            sorted(Counter(record.decision for record in rows).items())
        )
        if accepted:
            circles = [Circle((row.x_cm, row.y_cm), row.radius_cm) for row in accepted]
            collection = PatchCollection(
                circles,
                facecolor="#a9cce7",
                edgecolor="#0d5f98",
                linewidth=0.42,
                alpha=0.82,
                rasterized=True,
                label="accepted equivalent-area holes",
            )
            ax.add_collection(collection)
        if skipped:
            ax.scatter([row.x_cm for row in skipped], [row.y_cm for row in skipped], s=8.0,
                       marker="x", color="#d34a2f", linewidths=0.45, rasterized=True,
                       label=f"rejected candidates ({len(reason_counts)} audit labels)")
        ax.add_patch(Circle((0, 0), plate.radius_cm, fill=False, color="#3a454d", lw=1.0))
        ax.set_xlim(-plate.radius_cm - 0.5, plate.radius_cm + 0.5)
        ax.set_ylim(-plate.radius_cm - 0.5, plate.radius_cm + 0.5)
        axes_style(ax, "x′ [cm]", "y′ [cm]")
        diameter_label = f"Ø={diameter_mm:.3f} mm" if radius_uniform else "mixed radii (invalid)"
        ax.set_title(
            f"{plate.short_label}\nR={plate.radius_cm*10:.0f} mm; {diameter_label}\n"
            f"holes={len(accepted)}; rejected candidates={len(skipped)}",
            fontsize=8.2, fontweight="bold",
        )
        if index == 0:
            ax.legend(loc="lower left", fontsize=6.2, frameon=True)
    fig.text(0.055, 0.555,
             "b  48 equivalent-area holes per plate. Filled circles use the exact ledger diameter for each plate; "
             "red crosses are rejected candidate centres, with keep-out reason counts retained in the audit.",
             fontsize=9.6, fontweight="bold", color="#18232d")

    ax_c = fig.add_subplot(outer[2, 0])
    focused_y_cm, focused_z_cm = 0.0, -5.2
    layer_intervals: dict[str, list[tuple[float, float]]] = {}
    mesh_edge_residual_chords: dict[str, float] = {}
    navigator = navigation_audit["eventlist_navigation"]
    exact_gate_chords = {
        "BGO window": 0.0,
        "uncut plastic": float(navigator["plastic_chord_cm"]["mean"]),
        "BPE focused port": float(navigator["bpe_chord_cm"]["mean"]),
    }
    y_positions = {"BGO window": 2.0, "uncut plastic": 1.0, "BPE focused port": 0.0}
    for label, name, nominal_thickness, color in LAYER_SPECS:
        intervals = line_intervals_x_prime(mesh, name, y_cm=focused_y_cm, z_cm=focused_z_cm)
        mesh_chord = negative_chord(intervals)
        exact_chord = exact_gate_chords[label]
        layer_intervals[label] = intervals
        mesh_edge_residual_chords[label] = mesh_chord
        solid_id = solid_index(mesh, name)
        xmin = float(mesh["instrument_bounds_per_solid_cm"][solid_id, 0, 0])
        nominal_start, nominal_stop = xmin, xmin + nominal_thickness
        y = y_positions[label]
        ax_c.add_patch(Rectangle((nominal_start, y - 0.26), nominal_thickness, 0.52,
                                 fill=False, edgecolor=color, lw=1.4))
        negative_intervals = [(start, stop) for start, stop in intervals if start < 0]
        for start, stop in negative_intervals:
            clipped_stop = min(stop, 0.0)
            if clipped_stop > start:
                ax_c.add_patch(Rectangle((start, y - 0.26), clipped_stop - start, 0.52,
                                         facecolor=color, edgecolor="none", alpha=0.65))
        state = "OPEN" if exact_chord < 1.0e-9 else "MATERIAL"
        value_label = (
            "exact chord=0 mm" if label in {"BGO window", "BPE focused port"}
            else f"navigator mean={exact_chord*10:.3f} mm (nonzero)"
        )
        ax_c.text(nominal_stop + 0.25, y,
                  f"{label}: {state}; {value_label}",
                  va="center", fontsize=8.2, color=color)
    ax_c.annotate("incoming focused direction +x′", xy=(-26.0, -0.65), xytext=(-35.0, -0.65),
                  arrowprops={"arrowstyle": "-|>", "lw": 1.7, "color": "#d6472f"},
                  color="#d6472f", va="center")
    ax_c.set_xlim(-35.5, -24.0)
    ax_c.set_ylim(-1.1, 2.7)
    ax_c.set_yticks([0, 1, 2], ["BPE", "plastic", "BGO"])
    ax_c.set_xlabel("InstrumentFrame x′ [cm] along focused centreline (y′=0, z′=−5.2 cm)")
    ax_c.grid(axis="x", color="#dbe2e8", lw=0.5)
    ax_c.set_title("c  Focused layer stack: 37.96 mm square registration and intact plastic",
                   loc="left", fontweight="bold")
    ax_c.text(-35.2, 2.45,
              "BGO window and BPE port are open on the negative-x′ entrance. Plastic remains a full 10 mm layer.",
              fontsize=8.0, ha="left",
              bbox={"facecolor": "white", "edgecolor": "#aab3bb", "alpha": 0.88})
    ax_c.text(
        -35.2, -1.00,
        "Tessellation-edge residuals (visual mesh only, not physical chords): "
        f"BGO={mesh_edge_residual_chords['BGO window']*10:.3f} mm; "
        f"BPE={mesh_edge_residual_chords['BPE focused port']*10:.3f} mm.",
        fontsize=7.1, ha="left", va="bottom", color="#5b6670",
    )

    fig.suptitle("SE3 dimensioned sections and perforation ledgers", x=0.055, y=0.982,
                 ha="left", fontsize=15.2, fontweight="bold", color="#18232d")
    fig.text(0.055, 0.952,
             "All dimensions are derived from the candidate-owned geometry/mesh/ledgers.  "
             "World +Z is sky/up; −x′ is the outward 45° sky-facing optical direction.",
             ha="left", fontsize=9.2, color="#3d4a54")
    outputs = save_figure(fig, DIMENSION_STEM)
    plt.close(fig)
    return outputs, {
        "panel_count": 7,
        "accepted_hole_counts": accepted_counts,
        "skipped_hole_counts": skipped_counts,
        "hole_diameters_mm": hole_diameters_mm,
        "hole_radius_uniform_within_plate": hole_radius_uniform,
        "accepted_hole_areas_cm2": accepted_hole_areas_cm2,
        "mass_ledger_void_areas_cm2": mass_ledger_void_areas_cm2,
        "hole_area_matches_mass_ledger": hole_area_matches_mass_ledger,
        "keepout_reason_counts": keepout_reason_counts,
        "candidate_decision_counts": candidate_decision_counts,
        "focused_intervals_x_prime_cm": layer_intervals,
        "focused_exact_native_gate_chords_cm": exact_gate_chords,
        "focused_mesh_edge_residual_chords_cm": mesh_edge_residual_chords,
        "plastic_navigator_range_cm": navigator["plastic_chord_cm"],
    }


def validate_and_write(
    args: argparse.Namespace,
    mesh: dict[str, np.ndarray],
    hole_records,
    detail_outputs: list[Path],
    dimension_outputs: list[Path],
    detail_info: dict[str, Any],
    dimension_info: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    outputs = detail_outputs + dimension_outputs
    checks["six_required_figure_files"] = len(outputs) == 6 and all(path.is_file() for path in outputs)
    checks["all_figure_files_nonempty"] = all(path.stat().st_size > 1000 for path in outputs)
    checks["detail_four_panels"] = detail_info["panel_count"] == 4
    checks["dimension_seven_panels"] = dimension_info["panel_count"] == 7
    checks["native_world_unit_mm"] = str(mesh.get("world_length_unit", "")) == "mm"
    checks["instrument_plot_unit_cm"] = str(mesh.get("instrument_length_unit", "")) == "cm"
    checks["rotation_0_45_0"] = bool(
        np.allclose(mesh["instrument_rotation_xyz_deg"], (0, 45, 0), atol=1e-12)
    )
    expected_outward = np.asarray((-1 / math.sqrt(2), 0, 1 / math.sqrt(2)))
    outward = mesh["world_from_instrument_rotation"] @ np.asarray((-1.0, 0.0, 0.0))
    checks["minus_x_prime_is_45deg_sky_facing"] = bool(np.allclose(outward, expected_outward, atol=1e-12))
    checks["nonvacuum_3094"] = int(mesh["is_nonvacuum"].sum()) == 3094
    accepted = [record for record in hole_records if record.accepted]
    checks["visible_holes_equal_ledger"] = int(mesh["is_plate_hole"].sum()) == len(accepted)
    expected_plate_counts = {plate.name: 48 for plate in PLATES}
    checks["equivalent_hole_total_240"] = len(accepted) == 240
    checks["equivalent_holes_48_per_plate"] = (
        dimension_info["accepted_hole_counts"] == expected_plate_counts
    )
    checks["one_positive_equivalent_diameter_per_plate"] = bool(
        all(dimension_info["hole_radius_uniform_within_plate"].values())
        and all(
            math.isfinite(value) and value > 0.0
            for value in dimension_info["hole_diameters_mm"].values()
        )
    )
    checks["hole_area_closes_to_mass_ledger"] = all(
        dimension_info["hole_area_matches_mass_ledger"].values()
    )
    checks["aperture_center_yz"] = bool(
        np.allclose(detail_info["aperture_center_yz_cm"], (0, -5.2), atol=2e-3)
    )
    checks["aperture_37p96mm_square"] = bool(
        np.allclose(detail_info["aperture_span_yz_cm"], (3.796, 3.796), atol=2e-3)
    )
    chords = dimension_info["focused_exact_native_gate_chords_cm"]
    checks["bpe_focused_chord_zero"] = chords["BPE focused port"] <= 1e-3
    checks["bgo_focused_chord_zero"] = chords["BGO window"] <= 1e-3
    checks["plastic_uncut_about_1cm"] = 0.98 <= chords["uncut plastic"] <= 1.02
    svg_text = "\n".join(path.read_text(encoding="utf-8") for path in outputs if path.suffix == ".svg")
    forbidden_identity = "MASS" + "511"
    checks["no_forbidden_identity_in_figures"] = forbidden_identity.lower() not in svg_text.lower()
    forbidden_overlay_labels = (
        "prompt " + "event", "delayed " + "activation", "activation " + "point"
    )
    checks["no_historical_overlay_labels"] = all(
        token not in svg_text.lower() for token in forbidden_overlay_labels
    )
    mesh_audit_path = Path(args.mesh_audit).resolve()
    mesh_audit = json.loads(mesh_audit_path.read_text(encoding="utf-8"))
    checks["mesh_audit_pass"] = mesh_audit.get("status") == "PASS"
    navigation_audit_path = Path(args.navigation_audit).resolve()
    navigation_audit = json.loads(navigation_audit_path.read_text(encoding="utf-8"))
    checks["navigation_audit_pass"] = navigation_audit.get("status") == "PASS"
    navigation_holes = navigation_audit.get("hole_navigation", {})
    checks["navigation_audit_240_holes"] = navigation_holes.get("accepted_holes") == 240
    checks["navigation_audit_48_holes_per_plate"] = all(
        navigation_holes.get("by_plate", {}).get(key, {}).get("accepted_holes") == 48
        for key in ("MXC_50mK", "CP_100mK", "Still_0p7K", "4K", "60K")
    )
    navigation_hole_input = navigation_audit.get("input_integrity", {}).get("hole_csv", {})
    checks["navigation_audit_current_hole_csv"] = (
        navigation_hole_input.get("sha256") == file_record(Path(args.holes).resolve())["sha256"]
    )

    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema_version": "se3_visual_validation_v1",
        "status": status,
        "model_identity": "SE3",
        "physics_status": "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN",
        "inputs": {
            "mesh_npz": file_record(Path(args.mesh).resolve()),
            "manifest": file_record(Path(args.manifest).resolve()),
            "hole_pattern": file_record(Path(args.holes).resolve()),
            "mass_ledger": file_record(Path(args.mass).resolve()),
            "mesh_audit": file_record(mesh_audit_path),
            "navigation_audit": file_record(navigation_audit_path),
            "builder": file_record(Path(__file__).resolve()),
        },
        "outputs": [file_record(path) for path in outputs],
        "coordinate_convention": {
            "native_wrl_unit": "mm", "plot_unit": "cm", "world_plus_z": "sky/up",
            "sky_facing_axis_minus_x_prime_world": expected_outward.tolist(),
            "incoming_axis_plus_x_prime_world": (-expected_outward).tolist(),
            "elevation_deg": 45.0,
        },
        "detail": detail_info,
        "dimensioned_sections": dimension_info,
        "checks": checks,
    }
    atomic_json(Path(args.audit).resolve(), result)
    if status != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise VisualError(f"SE3 visual validation failed: {failed}; see {args.audit}")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--mesh", default=str(DEFAULT_MESH))
    result.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    result.add_argument("--holes", default=str(DEFAULT_HOLES))
    result.add_argument("--mass", default=str(DEFAULT_MASS))
    result.add_argument("--mesh-audit", default=str(DEFAULT_MESH_AUDIT))
    result.add_argument("--navigation-audit", default=str(DEFAULT_NAVIGATION_AUDIT))
    result.add_argument("--audit", default=str(DEFAULT_AUDIT))
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        mesh_path = Path(args.mesh).resolve()
        manifest_path = Path(args.manifest).resolve()
        holes_path = Path(args.holes).resolve()
        mass_path = Path(args.mass).resolve()
        for path in (
            mesh_path, manifest_path, holes_path, mass_path, Path(args.mesh_audit).resolve(),
            Path(args.navigation_audit).resolve(),
        ):
            if not path.is_file():
                raise VisualError(f"Required input is missing: {path}")
        mesh = load_mesh(mesh_path)
        read_manifest(manifest_path)
        hole_records, _ = read_hole_ledger(holes_path)
        mass_by_component = read_mass_ledger(mass_path)
        navigation_audit = json.loads(Path(args.navigation_audit).resolve().read_text(encoding="utf-8"))
        detail_outputs, detail_info = build_detail_figure(mesh)
        dimension_outputs, dimension_info = build_dimension_figure(
            mesh, hole_records, mass_by_component, navigation_audit
        )
        validate_and_write(
            args, mesh, hole_records, detail_outputs, dimension_outputs,
            detail_info, dimension_info,
        )
    except (VisualError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"PASS: wrote {len(detail_outputs) + len(dimension_outputs)} SE3 figure files")
    print(f"audit: {Path(args.audit).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
