#!/usr/bin/env python3
"""Render SG3 global/local sections from the reusable SE3/SF3 TOOL inputs.

The inherited SE3 y'=0 mesh is exact. SG3's two physical edits are explicit
analytic overlays. Activation points and prompt tracks are retained SE3/SF3
diagnostics, not SG3 transport predictions.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3_diagnostic_sections_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
FIGURES = PACKAGE / "figures"
AUDIT = PACKAGE / "audit/sg3_section_figure_validation.json"
TOOL = (
    SCRIPT.parents[2]
    / "52_se3_sf3_activation_prompt_section_tool_20260816/TOOL"
)
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

BI = (-3.8, 4.0, -2.39, -1.9104)
RING_X = (3.245, 3.595)
RING_Z_BANDS = ((-8.0, -6.0), (-4.4, -2.4))
OLD_DISK = (3.245, 3.595, -7.4, -3.0)
CAN_BOTTOM_CAP = (-15.3, 15.3, -9.9, -9.7)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def draw_removed_sf3_w(ax: plt.Axes) -> None:
    bands = [
        (diagnostic.FRONT_X0, diagnostic.FRONT_X1, diagnostic.CENTER_Z + diagnostic.WINDOW_HALF, diagnostic.CENTER_Z + diagnostic.CAP_ROUT),
        (diagnostic.FRONT_X0, diagnostic.FRONT_X1, diagnostic.CENTER_Z - diagnostic.CAP_ROUT, diagnostic.CENTER_Z - diagnostic.WINDOW_HALF),
        (diagnostic.SIDE_X0, diagnostic.SIDE_X1, diagnostic.CENTER_Z + diagnostic.SIDE_RIN, diagnostic.CENTER_Z + diagnostic.SIDE_ROUT),
        (diagnostic.SIDE_X0, diagnostic.SIDE_X1, diagnostic.CENTER_Z - diagnostic.SIDE_ROUT, diagnostic.CENTER_Z - diagnostic.SIDE_RIN),
        (diagnostic.REAR_X0, diagnostic.REAR_X1, diagnostic.CENTER_Z + diagnostic.REAR_RIN, diagnostic.CENTER_Z + diagnostic.CAP_ROUT),
        (diagnostic.REAR_X0, diagnostic.REAR_X1, diagnostic.CENTER_Z - diagnostic.CAP_ROUT, diagnostic.CENTER_Z - diagnostic.REAR_RIN),
    ]
    for x0, x1, z0, z1 in bands:
        ax.add_patch(
            Rectangle(
                (x0, z0), x1 - x0, z1 - z0,
                fill=False, edgecolor="#606A73", linewidth=0.8,
                linestyle=(0, (2, 2)), alpha=0.70, zorder=7,
            )
        )


def draw_sg3(ax: plt.Axes, *, annotations: bool) -> None:
    x0, x1, z0, z1 = OLD_DISK
    ax.add_patch(
        Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor="white", edgecolor="none", zorder=6)
    )
    ax.add_patch(
        Rectangle(
            (x0, z0), x1 - x0, z1 - z0,
            fill=False, edgecolor="#A65B2A", linestyle=(0, (3, 2)),
            linewidth=0.8, alpha=0.72, zorder=8,
        )
    )
    for low, high in RING_Z_BANDS:
        ax.add_patch(
            Rectangle(
                (RING_X[0], low), RING_X[1] - RING_X[0], high - low,
                facecolor="#D56A2A", edgecolor="#78330E", hatch="\\\\",
                linewidth=0.9, alpha=0.78, zorder=10,
            )
        )
    bx0, bx1, bz0, bz1 = BI
    ax.add_patch(
        Rectangle(
            (bx0, bz0), bx1 - bx0, bz1 - bz0,
            facecolor="#9B7AB8", edgecolor="#4B2E66", hatch="....",
            linewidth=1.0, alpha=0.78, zorder=10,
        )
    )
    cx0, cx1, cz0, cz1 = CAN_BOTTOM_CAP
    ax.add_patch(
        Rectangle(
            (cx0, cz0), cx1 - cx0, cz1 - cz0,
            facecolor="#FFD166", edgecolor="#9B2C2C", hatch="----",
            linewidth=1.8, alpha=0.42, zorder=11,
        )
    )
    if annotations:
        ax.annotate(
            "4.796 mm passive Bi shadow umbrella\n0.164 kg; not veto",
            xy=(0.1, (bz0 + bz1) / 2), xytext=(-7.8, 1.4),
            fontsize=7, color="#4B2E66", weight="bold",
            arrowprops={"arrowstyle": "->", "color": "#4B2E66", "lw": 0.8}, zorder=30,
        )
        ax.annotate(
            "L0 Cu heat-sink ring\n1.0 cm substrate overlap + 1.0 cm edge protrusion",
            xy=(3.42, -2.9), xytext=(5.0, -1.0),
            fontsize=7, color="#78330E", weight="bold",
            arrowprops={"arrowstyle": "->", "color": "#78330E", "lw": 0.8}, zorder=30,
        )
        ax.annotate(
            "central Cu removed\n(high-weight SE3 L0 source lies here)",
            xy=(3.42, -4.67), xytext=(5.1, -5.6),
            fontsize=6.6, color="#9B2C2C",
            arrowprops={"arrowstyle": "->", "color": "#9B2C2C", "lw": 0.75}, zorder=30,
        )
        ax.annotate(
            "50 mK Cu can bottom cap (2 mm)\nR = 15.3 cm; NOT the TES L0 heat-sink ring",
            xy=(-3.9, -9.8), xytext=(-9.5, -8.75),
            fontsize=7.2, color="#7A1F1F", weight="bold",
            bbox={"boxstyle": "round,pad=0.24", "fc": "#FFF7D6", "ec": "#9B2C2C", "alpha": 0.94},
            arrowprops={"arrowstyle": "->", "color": "#9B2C2C", "lw": 1.05}, zorder=35,
        )


def signal_envelope(mesh: dict[str, np.ndarray], xmin: float, xmax: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    eventlist = np.loadtxt(EVENTLIST, dtype=np.float64)
    rotation = mesh["instrument_from_world_rotation"]
    points = eventlist[:, 5:8] @ rotation.T
    directions = eventlist[:, 8:11] @ rotation.T
    xs = np.linspace(xmin, xmax, 160)
    lower: list[float] = []
    upper: list[float] = []
    for x in xs:
        distance = (x - points[:, 0]) / directions[:, 0]
        z = points[:, 2] + distance * directions[:, 2]
        lower.append(float(np.min(z)))
        upper.append(float(np.max(z)))
    return xs, np.asarray(lower), np.asarray(upper)


def handles() -> list[object]:
    output: list[object] = [
        Patch(facecolor="#9B7AB8", edgecolor="#4B2E66", hatch="....", label="SG3 passive Bi umbrella (not veto)"),
        Patch(facecolor="#D56A2A", edgecolor="#78330E", hatch="\\\\", label="SG3 Cu L0 heat-sink ring"),
        Patch(facecolor="#FFD166", edgecolor="#9B2C2C", hatch="----", alpha=0.42, label="inherited 50 mK Cu-can bottom cap"),
        Line2D([0], [0], color="#606A73", ls=(0, (2, 2)), lw=1.0, label="removed SF3 W envelope"),
        Patch(facecolor="#7E57C2", edgecolor="none", alpha=0.14, label="37,194 focused-ray z' envelope"),
    ]
    output.extend(diagnostic.figure_legend()[:13])
    return output


def build_one(
    mesh: dict[str, np.ndarray],
    points: list[dict[str, object]],
    events: list[dict[str, object]],
    limits: tuple[tuple[float, float], tuple[float, float]],
    stem: str,
    title: str,
    *,
    annotations: bool,
) -> list[str]:
    fig, ax = plt.subplots(figsize=(11.4, 8.3))
    visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
    xs, lower, upper = signal_envelope(mesh, *limits[0])
    ax.fill_between(xs, lower, upper, color="#7E57C2", alpha=0.13, zorder=5)
    draw_removed_sf3_w(ax)
    draw_sg3(ax, annotations=annotations)
    diagnostic.draw_activation_points(ax, points)
    diagnostic.draw_prompt_routes_xz(ax, events)
    visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_title(title, weight="bold", pad=8)
    ax.text(
        0.01, 0.985,
        "Exact inherited SE3 y'=0 mesh + analytic SG3 overlays.\n"
        "Activation markers are retained SE3 delayed-W2 origins; tracks are retained SF3 prompt-W2 diagnostics, not SG3 predictions.",
        transform=ax.transAxes, ha="left", va="top", fontsize=6.7, color="#263442",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#CCD5DD", "alpha": 0.92}, zorder=40,
    )
    ax.legend(handles=handles(), loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=6.4)
    fig.subplots_adjust(right=0.76)
    return diagnostic.save_figure(fig, stem, FIGURES)


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    visual.configure_matplotlib()
    mesh = visual.load_mesh(MESH)
    origins = diagnostic.read_csv(ORIGINS)
    points = diagnostic.build_plot_points(origins)
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    events = diagnostic.prompt_events(routes)
    paths: list[str] = []
    paths.extend(
        build_one(
            mesh, points, events, ((-34.0, 34.0), (-22.0, 42.0)),
            "sg3_global_diagnostic_section",
            "SG3 global section: inherited geometry, activation origins, and diagnostic prompt routes",
            annotations=False,
        )
    )
    paths.extend(
        build_one(
            mesh, points, events, ((-10.5, 10.5), (-12.0, 3.0)),
            "sg3_local_nearfield_diagnostic_section",
            "SG3 local section: 1 cm Cu ring and compact Bi MXC-to-TES shadow umbrella",
            annotations=True,
        )
    )
    payload = {
        "status": "PASS__SG3_TWO_SECTION_DIAGNOSTIC_RENDER",
        "transport_launched": False,
        "authority_boundary": "GEOMETRY_VISUALIZATION_AND_RETAINED_DIAGNOSTICS_ONLY",
        "inputs": {
            "mesh": {"path": str(MESH), "sha256": sha256(MESH)},
            "activation_origins": {"path": str(ORIGINS), "sha256": sha256(ORIGINS), "rows": len(origins)},
            "sf3_routes": {"path": str(ROUTES), "sha256": sha256(ROUTES), "events": len(events)},
            "focused_eventlist": {"path": str(EVENTLIST), "sha256": sha256(EVENTLIST), "rows": 37194},
        },
        "figures": [{"path": path, "sha256": sha256(Path(path))} for path in paths],
        "disclaimer": "SE3 activation and SF3 prompt overlays are diagnostics, not SG3 candidate-own transport.",
    }
    AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "figures": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
