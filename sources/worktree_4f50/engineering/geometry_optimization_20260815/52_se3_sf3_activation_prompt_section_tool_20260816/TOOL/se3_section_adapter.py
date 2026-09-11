"""Minimal native-SE3 section adapter for the reusable diagnostic TOOL.

This is the compact plotting subset of the validated
``44_geoopt_se3_minimal_20260815/code/build_se3_visuals.py`` implementation.
It intentionally does not contain mesh construction, geometry parsing, transport,
or artifact hashing.  It only loads the retained NPZ and draws its exact y'=0
triangle/plane intersection.
"""

from __future__ import annotations

from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection


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


class VisualError(RuntimeError):
    pass


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


def material_style(material: str) -> tuple[tuple[float, float, float], float]:
    return MATERIAL_STYLE.get(material, DEFAULT_STYLE)


def load_mesh(path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    required = {
        "vertices_instrument_cm",
        "triangles",
        "triangle_solid_ids",
        "solid_names",
        "materials",
        "is_nonvacuum",
        "is_plate_hole",
        "instrument_bounds_per_solid_cm",
    }
    missing = required - set(data)
    if missing:
        raise VisualError(f"mesh NPZ lacks arrays: {sorted(missing)}")
    return data


def triangle_plane_segments(
    triangle: np.ndarray, axis: int, value: float = 0.0
) -> list[np.ndarray]:
    distances = triangle[:, axis] - value
    epsilon = 1.0e-8
    points: list[np.ndarray] = []
    if np.all(np.abs(distances) <= epsilon):
        return [
            np.asarray((triangle[index], triangle[(index + 1) % 3]))
            for index in range(3)
        ]
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
                    projected[:, 0].max() < xmin
                    or projected[:, 0].min() > xmax
                    or projected[:, 1].max() < zmin
                    or projected[:, 1].min() > zmax
                ):
                    continue
            if holes[solid_id]:
                colors.append((0.05, 0.30, 0.68, 0.92))
                widths.append(0.48)
            else:
                rgb, _ = material_style(str(materials[solid_id]))
                colors.append((*rgb, 0.84))
                widths.append(
                    0.36 if str(materials[solid_id]) not in {"Ta", "W"} else 0.54
                )
            lines.append(projected)
    if not lines:
        raise VisualError("exact y-prime=0 section contains no segments")
    ax.add_collection(
        LineCollection(lines, colors=colors, linewidths=widths, rasterized=True)
    )
    ax.autoscale_view()


def solid_index(mesh: dict[str, np.ndarray], name: str) -> int:
    matches = np.flatnonzero(mesh["solid_names"] == name)
    if len(matches) != 1:
        raise VisualError(f"expected one mesh solid named {name}, found {len(matches)}")
    return int(matches[0])

