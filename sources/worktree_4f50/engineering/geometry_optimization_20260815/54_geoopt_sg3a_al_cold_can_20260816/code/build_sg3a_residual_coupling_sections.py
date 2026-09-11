#!/usr/bin/env python3
"""Render SG3A residual-coupling diagnostics from retained compact evidence.

The base section is the reusable exact SE3 y'=0 mesh.  SG3/SG3A changes and
the NbTi x'-z' footprints are analytic overlays.  The curved Bi shell is a
clearly marked counterfactual, not part of SG3A.  Retained SE3 activation
origins and SF3 prompt routes are diagnostics, never candidate-own transport.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3a_residual_sections_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
FIGURES = PACKAGE / "figures"
AUDIT = PACKAGE / "audit/sg3a_residual_coupling_figure_validation.json"
TOOL = SCRIPT.parents[2] / "52_se3_sf3_activation_prompt_section_tool_20260816/TOOL"
sys.path.insert(0, str(TOOL))

import build_activation_prompt_sections as diagnostic  # noqa: E402
import se3_section_adapter as visual  # noqa: E402


MESH = TOOL / "inputs/se3_geometry_mesh_products.npz"
ORIGINS = TOOL / "inputs/selected_delayed_event_origins.csv"
ROUTES = TOOL / "inputs/sf3_background_routes_2d.json"
EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/"
    "signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)
MASS_TABLE = PACKAGE / "data/sg3a_residual_source_proxy_masses.csv"

BI = (-3.8, 4.0, -2.39, -1.9104)
RING_X = (3.245, 3.595)
RING_Z_BANDS = ((-8.0, -6.0), (-4.4, -2.4))
OLD_DISK = (3.245, 3.595, -7.4, -3.0)
AL_CAN_BOTTOM = (-15.3, 15.3, -9.9, -9.7)
TES_REFERENCE = (1.2, -8.3)
K38_POINT = (-8.360851793953174, 17.462235306639585)
L3_POINT = (-0.3427841543158032, -7.141714850373823)

# name, phi0 [deg], dphi [deg], z center, z half-length, r_in, r_out, mass [g]
NBTI = (
    ("bay-MXC", 59.4, 61.2, -4.2, 3.8, 6.6, 6.9, 106.851535),
    ("MXC-CP", 99.4, 61.2, 2.5, 2.1, 6.6, 6.9, 59.049533),
    ("CP-Still", 99.4, 61.2, 7.5, 2.1, 6.6, 6.9, 59.049533),
    ("Still-4K", 99.4, 61.2, 15.5, 4.1, 9.2, 9.5, 159.694098),
    ("4K-60K", 99.4, 61.2, 24.45, 4.05, 10.7, 11.0, 183.053551),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def projection_x(phi0: float, dphi: float, r_in: float, r_out: float) -> tuple[float, float]:
    phi = np.deg2rad(np.linspace(phi0, phi0 + dphi, 2001))
    x = np.concatenate((r_in * np.cos(phi), r_out * np.cos(phi)))
    return float(np.min(x)), float(np.max(x))


def signal_envelope(mesh: dict[str, np.ndarray], xmin: float, xmax: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    eventlist = np.loadtxt(EVENTLIST, dtype=np.float64)
    rotation = mesh["instrument_from_world_rotation"]
    points = eventlist[:, 5:8] @ rotation.T
    directions = eventlist[:, 8:11] @ rotation.T
    xs = np.linspace(xmin, xmax, 320)
    lower: list[float] = []
    upper: list[float] = []
    for x in xs:
        distance = (x - points[:, 0]) / directions[:, 0]
        z = points[:, 2] + distance * directions[:, 2]
        lower.append(float(np.min(z)))
        upper.append(float(np.max(z)))
    return xs, np.asarray(lower), np.asarray(upper)


def draw_sg3a(ax: plt.Axes) -> None:
    x0, x1, z0, z1 = OLD_DISK
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor="white", edgecolor="none", zorder=6))
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fill=False, edgecolor="#A65B2A", linestyle=(0, (3, 2)), linewidth=0.8, zorder=8))
    for low, high in RING_Z_BANDS:
        ax.add_patch(Rectangle((RING_X[0], low), RING_X[1] - RING_X[0], high - low, facecolor="#D56A2A", edgecolor="#78330E", hatch="\\\\", linewidth=0.9, alpha=0.78, zorder=10))
    bx0, bx1, bz0, bz1 = BI
    ax.add_patch(Rectangle((bx0, bz0), bx1 - bx0, bz1 - bz0, facecolor="#9B7AB8", edgecolor="#4B2E66", hatch="....", linewidth=1.0, alpha=0.78, zorder=10))
    cx0, cx1, cz0, cz1 = AL_CAN_BOTTOM
    ax.add_patch(Rectangle((cx0, cz0), cx1 - cx0, cz1 - cz0, facecolor="#A8DADC", edgecolor="#197A8A", hatch="----", linewidth=1.5, alpha=0.42, zorder=11))


def draw_nbti_projections(ax: plt.Axes) -> None:
    for name, phi0, dphi, zc, hz, r0, r1, _mass in NBTI:
        xmin, xmax = projection_x(phi0, dphi, r0, r1)
        selected = name == "Still-4K"
        ax.add_patch(
            Rectangle(
                (xmin, zc - hz), xmax - xmin, 2 * hz,
                facecolor="#6E9F55" if selected else "#A8C78E",
                edgecolor="#235B2A" if selected else "#607D52",
                hatch="xx" if selected else "//", linewidth=1.4 if selected else 0.7,
                alpha=0.30 if selected else 0.15, zorder=9,
            )
        )
    ax.plot(*K38_POINT, marker="o", markersize=9, markerfacecolor="#36A865", markeredgecolor="black", markeredgewidth=1.4, zorder=32)
    ax.plot([K38_POINT[0], TES_REFERENCE[0]], [K38_POINT[1], TES_REFERENCE[1]], color="#27864C", linestyle=(0, (5, 3)), linewidth=1.2, alpha=0.8, zorder=12)


def curved_bi_counterfactual(ax: plt.Axes, xs_env: np.ndarray, low: np.ndarray, high: np.ndarray) -> None:
    # Full upper half-cylinder whose top is tangent to the current flat umbrella.
    cx, cz, radius, thick = 0.1, -6.05, 3.9, 0.4796
    theta = np.linspace(0.0, math.pi, 500)
    outer = np.column_stack((cx + (radius + thick / 2) * np.cos(theta), cz + (radius + thick / 2) * np.sin(theta)))
    inner = np.column_stack((cx + (radius - thick / 2) * np.cos(theta[::-1]), cz + (radius - thick / 2) * np.sin(theta[::-1])))
    polygon = np.vstack((outer, inner))
    ax.add_patch(Polygon(polygon, closed=True, facecolor="#D6C1E5", edgecolor="#6B3E8E", linestyle=(0, (5, 3)), linewidth=1.4, alpha=0.26, zorder=9))

    xarc = np.linspace(cx - radius, cx + radius, 700)
    zarc = cz + np.sqrt(np.maximum(0.0, radius**2 - (xarc - cx) ** 2))
    lo = np.interp(xarc, xs_env, low)
    hi = np.interp(xarc, xs_env, high)
    conflict = (zarc + thick / 2 >= lo) & (zarc - thick / 2 <= hi)
    ax.plot(xarc[conflict], zarc[conflict], color="#C62828", linewidth=3.2, alpha=0.9, zorder=15)


def legend_handles() -> list[object]:
    items: list[object] = [
        Patch(facecolor="#9B7AB8", edgecolor="#4B2E66", hatch="....", label="current flat Bi umbrella: 164.1 g (passive)"),
        Patch(facecolor="#D6C1E5", edgecolor="#6B3E8E", label="conceptual full curved Bi shell (not SG3A)"),
        Patch(facecolor="#A8DADC", edgecolor="#197A8A", hatch="----", alpha=0.42, label="SG3A 50 mK Al-can bottom cap"),
        Patch(facecolor="#D56A2A", edgecolor="#78330E", hatch="\\\\", label="SG3A L0 Cu heat-sink ring"),
        Patch(facecolor="#6E9F55", edgecolor="#235B2A", hatch="xx", alpha=0.30, label="NbTi proxy x'-z' footprint (not y'=0 material)"),
        Line2D([0], [0], color="#27864C", ls=(0, (5, 3)), lw=1.2, label="source-to-TES sightline, not reconstructed track"),
        Line2D([0], [0], color="#C62828", lw=3.2, label="curved-shell overlap with focused-ray envelope"),
        Patch(facecolor="#7E57C2", edgecolor="none", alpha=0.14, label="37,194 focused-ray z' envelope"),
    ]
    items.extend(diagnostic.figure_legend()[:13])
    return items


def build_global(mesh: dict[str, np.ndarray], points: list[dict[str, object]], events: list[dict[str, object]]) -> list[str]:
    fig, ax = plt.subplots(figsize=(12.4, 8.6))
    limits = ((-34.0, 34.0), (-22.0, 42.0))
    visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
    xs, lower, upper = signal_envelope(mesh, *limits[0])
    ax.fill_between(xs, lower, upper, color="#7E57C2", alpha=0.13, zorder=5)
    draw_sg3a(ax)
    draw_nbti_projections(ax)
    diagnostic.draw_activation_points(ax, points)
    diagnostic.draw_prompt_routes_xz(ax, events)
    ax.annotate(
        "K-38 selected origin in NbTi_Bundle_Still_4K\n"
        "proxy segment = 159.69 g; all five proxy sectors = 567.70 g\n"
        "1 event, Neff=1: 7.0% of SE3; 11.4% only after SG3A residual renormalization",
        xy=K38_POINT, xytext=(-30.5, 31.0), fontsize=7.3, color="#154F2A", weight="bold",
        bbox={"boxstyle": "round,pad=0.28", "fc": "#F1F8EE", "ec": "#27864C", "alpha": 0.95},
        arrowprops={"arrowstyle": "->", "color": "#27864C", "lw": 1.0}, zorder=40,
    )
    ax.text(
        -31.0, 38.5,
        "Green bands are x'-z' projections of off-plane annular-sector cable proxies;\n"
        "they are deliberately shown even though the exact section is y'=0.",
        fontsize=6.8, color="#263442",
        bbox={"boxstyle": "round,pad=0.24", "fc": "white", "ec": "#A8B3BC", "alpha": 0.94}, zorder=40,
    )
    visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
    ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1])
    ax.set_title("SG3A global section: NbTi proxy mass and the single retained K-38 origin", weight="bold", pad=8)
    ax.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=6.2)
    fig.subplots_adjust(right=0.76)
    return diagnostic.save_figure(fig, "sg3a_global_nbti_k38_coupling_section", FIGURES)


def build_local(mesh: dict[str, np.ndarray], points: list[dict[str, object]], events: list[dict[str, object]]) -> list[str]:
    fig, ax = plt.subplots(figsize=(12.4, 8.6))
    limits = ((-10.5, 10.5), (-12.0, 3.0))
    visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
    xs, lower, upper = signal_envelope(mesh, *limits[0])
    ax.fill_between(xs, lower, upper, color="#7E57C2", alpha=0.13, zorder=5)
    draw_sg3a(ax)
    curved_bi_counterfactual(ax, xs, lower, upper)
    diagnostic.draw_activation_points(ax, points)
    diagnostic.draw_prompt_routes_xz(ax, events)
    ax.plot(*L3_POINT, marker="o", markersize=9, markerfacecolor="#8A63C7", markeredgecolor="black", markeredgewidth=1.2, zorder=33)
    ax.annotate(
        "L3 Cu open ring (four small bars): 13.02 g total\n"
        "selected source is ZM bar: one Cu-64 event, Neff=1\n"
        "NOT the 50 mK can; NOT the L0 heat-sink ring",
        xy=L3_POINT, xytext=(-9.7, -4.45), fontsize=7.1, color="#5C2D83", weight="bold",
        bbox={"boxstyle": "round,pad=0.28", "fc": "#F7F0FC", "ec": "#7B4DA0", "alpha": 0.95},
        arrowprops={"arrowstyle": "->", "color": "#7B4DA0", "lw": 1.0}, zorder=40,
    )
    ax.annotate(
        "full upper half-cylinder (concept)\n"
        "same 4.796 mm Bi: about 258 g\n"
        "1.57x flat mass; red arc crosses\n"
        "the 37,194-ray focused envelope",
        xy=(3.7, -5.2), xytext=(4.3, -0.85), fontsize=6.7, color="#6B3E8E", weight="bold",
        bbox={"boxstyle": "round,pad=0.25", "fc": "#FAF4FD", "ec": "#6B3E8E", "alpha": 0.95},
        arrowprops={"arrowstyle": "->", "color": "#C62828", "lw": 1.0}, zorder=40,
    )
    ax.annotate(
        "SG3A Al can bottom cap\n2 mm; whole four-piece can = 873.78 g",
        xy=(-4.0, -9.8), xytext=(-9.6, -11.15), fontsize=7.0, color="#126A77", weight="bold",
        bbox={"boxstyle": "round,pad=0.25", "fc": "#ECFAFC", "ec": "#197A8A", "alpha": 0.95},
        arrowprops={"arrowstyle": "->", "color": "#197A8A", "lw": 1.0}, zorder=40,
    )
    visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
    ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1])
    ax.set_title("SG3A local section: L3 source identity and curved-Bi aperture conflict", weight="bold", pad=8)
    ax.text(
        0.01, 0.985,
        "Exact inherited SE3 y'=0 mesh + analytic SG3A overlays. Curved Bi is a concept only.\n"
        "Activation markers are retained SE3 origins; tracks are retained SF3 prompt diagnostics, not SG3A predictions.",
        transform=ax.transAxes, ha="left", va="top", fontsize=6.6, color="#263442",
        bbox={"boxstyle": "round,pad=0.24", "fc": "white", "ec": "#CCD5DD", "alpha": 0.92}, zorder=40,
    )
    ax.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=6.2)
    fig.subplots_adjust(right=0.76)
    return diagnostic.save_figure(fig, "sg3a_local_l3_curved_bi_coupling_section", FIGURES)


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    visual.configure_matplotlib()
    mesh = visual.load_mesh(MESH)
    origins = diagnostic.read_csv(ORIGINS)
    points = diagnostic.build_plot_points(origins)
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    events = diagnostic.prompt_events(routes)
    paths = build_global(mesh, points, events) + build_local(mesh, points, events)
    with MASS_TABLE.open(newline="", encoding="utf-8") as handle:
        masses = list(csv.DictReader(handle))
    payload = {
        "status": "PASS__SG3A_RESIDUAL_COUPLING_SECTIONS",
        "transport_launched": False,
        "geometry_modified": False,
        "authority_boundary": "RETAINED_COMPACT_DIAGNOSTICS_AND_ANALYTIC_GEOMETRY_ONLY",
        "evidence": {
            "nbti_still_4k_proxy_mass_g": 159.694098,
            "nbti_all_proxy_mass_g": 567.698249,
            "nbti_selected_events": 1,
            "nbti_selected_neff": 1.0,
            "nbti_se3_selected_share": 0.07005367355364235,
            "l3_cu_ring_mass_g": 13.020672,
            "l3_selected_events": 1,
            "l3_selected_neff": 1.0,
            "flat_bi_mass_g": 164.080608,
            "naive_semicylinder_bi_mass_g": 257.737217,
        },
        "inputs": {
            "mesh": {"path": str(MESH), "sha256": sha256(MESH)},
            "activation_origins": {"path": str(ORIGINS), "sha256": sha256(ORIGINS), "rows": len(origins)},
            "sf3_routes": {"path": str(ROUTES), "sha256": sha256(ROUTES), "events": len(events)},
            "focused_eventlist": {"path": str(EVENTLIST), "sha256": sha256(EVENTLIST), "rows": 37194},
            "mass_table": {"path": str(MASS_TABLE), "sha256": sha256(MASS_TABLE), "rows": len(masses)},
        },
        "figures": [{"path": path, "sha256": sha256(Path(path))} for path in paths],
        "disclaimer": "The 11.4% NbTi and L3 numbers are residual-renormalized one-event projections, not robust candidate-own fractions.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "figures": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
