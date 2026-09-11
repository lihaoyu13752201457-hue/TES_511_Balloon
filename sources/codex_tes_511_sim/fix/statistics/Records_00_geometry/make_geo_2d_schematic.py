#!/usr/bin/env python3
"""Generate the XZTES 2D geometry schematic used by this record.

The plot is intentionally derived from the Cosima geometry authority in
``XZTES`` instead of from hand-copied dimensions:

- ``XZTES/bounds.json`` supplies the shield, TES, window, collimator and
  support bounds used by downstream analysis scripts.
- ``XZTES/TibetTES_v5_6layers.geo`` supplies the individual TES pixel and
  collimator-bar placements for the inset projections.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_BOUNDS = ROOT / "XZTES" / "bounds.json"
DEFAULT_GEO = ROOT / "XZTES" / "TibetTES_v5_6layers.geo"
DEFAULT_OUT = HERE / "geo.png"

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
POS_RE = re.compile(rf"^(?P<name>\S+)\.Position\s+(?P<x>{FLOAT})\s+(?P<y>{FLOAT})\s+(?P<z>{FLOAT})$")
BRIK_RE = re.compile(rf"^(?P<name>\S+)\.Shape\s+BRIK\s+(?P<hx>{FLOAT})\s+(?P<hy>{FLOAT})\s+(?P<hz>{FLOAT})$")


COLORS = {
    "Al_Shell": "#D9B8A6",
    "BGO_Shield": "#82B366",
    "Cryo_Shell": "#BFC4CC",
    "W_Shield": "#666666",
    "Nb_Shield": "#5AC8D8",
    "Cu": "#C98942",
    "Substrate": "#303030",
    "TES": "#E45756",
    "Window": "#B279A2",
    "Collimator": "#262626",
    "Source": "#D62728",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_geo(path: Path) -> tuple[dict[str, tuple[float, float, float]], dict[str, tuple[float, float, float]]]:
    text = path.read_text(encoding="utf-8")
    positions: dict[str, tuple[float, float, float]] = {}
    briks: dict[str, tuple[float, float, float]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        m = POS_RE.match(line)
        if m:
            positions[m.group("name")] = (float(m.group("x")), float(m.group("y")), float(m.group("z")))
            continue
        m = BRIK_RE.match(line)
        if m:
            briks[m.group("name")] = (float(m.group("hx")), float(m.group("hy")), float(m.group("hz")))
    return positions, briks


def rect(ax, x: float, y: float, w: float, h: float, color: str, alpha: float = 0.45, *, ec: str | None = None, lw: float = 0.7, zorder: int = 1) -> None:
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=color,
            edgecolor=ec if ec is not None else color,
            linewidth=lw,
            alpha=alpha,
            zorder=zorder,
        )
    )


def draw_polycone_shell(ax, name: str, shell: dict, color: str) -> None:
    rout = float(shell["r_out"])
    rin = float(shell["r_in"])
    z0 = float(shell["z_out_bot"])
    z1 = float(shell["z_out_top"])
    zi0 = float(shell["z_in_bot"])
    zi1 = float(shell["z_in_top"])
    hole = float(shell.get("hole_r", rin))

    rect(ax, -rout, z0, rout - rin, z1 - z0, color, 0.34, ec=color)
    rect(ax, rin, z0, rout - rin, z1 - z0, color, 0.34, ec=color)
    rect(ax, -rout, z0, 2 * rout, max(zi0 - z0, 0.0), color, 0.34, ec=color)
    rect(ax, -rout, zi1, rout - hole, max(z1 - zi1, 0.0), color, 0.34, ec=color)
    rect(ax, hole, zi1, rout - hole, max(z1 - zi1, 0.0), color, 0.34, ec=color)
    ax.text(rout + 0.18, 0.5 * (z0 + z1), name, fontsize=7, va="center", color="#222222")


def layer0_pixels(positions: dict[str, tuple[float, float, float]]) -> list[tuple[float, float]]:
    pixels: list[tuple[float, float]] = []
    for name, (x, y, _z) in positions.items():
        if name.startswith("TP_L0_"):
            pixels.append((x, y))
    return sorted(pixels)


def draw_xz_main(ax, bounds: dict, pixels_xy: list[tuple[float, float]], briks: dict[str, tuple[float, float, float]], show_source: bool) -> None:
    ax.set_title("XZTES mass model: X-Z projection", fontsize=12)
    ax.set_xlabel("X / cm")
    ax.set_ylabel("Z / cm")

    for name in ["Al_Shell", "BGO_Shield", "Cryo_Shell", "W_Shield", "Nb_Shield"]:
        draw_polycone_shell(ax, name, bounds["SHIELDS"][name], COLORS[name])

    cu = bounds["CU_BASE"]
    rect(ax, -cu["r_max"], cu["z_bot"], 2 * cu["r_max"], cu["z_top"] - cu["z_bot"], COLORS["Cu"], 0.62, ec="#8A4D12", zorder=4)
    ax.text(float(cu["r_max"]) + 0.25, 0.5 * (cu["z_bot"] + cu["z_top"]), "Cu_Base", fontsize=7, va="center")

    pole = bounds["CU_SUPPORT"]
    rect(ax, -pole["r_max"], pole["z_bot"], 2 * pole["r_max"], pole["z_top"] - pole["z_bot"], COLORS["Cu"], 0.74, ec="#8A4D12", zorder=5)
    ax.text(float(pole["r_max"]) + 0.22, 0.5 * (pole["z_bot"] + pole["z_top"]), "Cu support", fontsize=7, va="center")

    pixel_hx, _pixel_hy, pixel_hz = briks.get("TES_Pixel_L0", (0.075, 0.075, 0.15))
    unique_x = sorted({round(x, 6) for x, _y in pixels_xy})
    for sub in bounds["SUBSTRATES"]:
        zc = float(sub["z_center"])
        hz = float(sub["hz"])
        rmax = float(sub["r_max"])
        rect(ax, -rmax, zc - hz, 2 * rmax, 2 * hz, COLORS["Substrate"], 0.55, ec="#111111", lw=0.35, zorder=8)

    for i, layer in enumerate(bounds["TES_LAYERS"]):
        zc = float(layer["z_center"])
        for x in unique_x:
            rect(ax, x - pixel_hx, zc - pixel_hz, 2 * pixel_hx, 2 * pixel_hz, COLORS["TES"], 0.36, ec="#8E2F2E", lw=0.25, zorder=9)
        ax.text(float(layer["r_max"]) + 0.25, zc, f"TES L{i}", fontsize=7, va="center", color="#8E2F2E")

    for win in bounds["WINDOWS"]:
        zc = float(win["z_center"])
        rmax = float(win["r_max"])
        h = max(float(win["thick"]), 0.036)
        rect(ax, -rmax, zc - 0.5 * h, 2 * rmax, h, COLORS["Window"], 0.58, ec="#7B4B84", lw=0.55, zorder=10)
        if win["name"] == "Win_Be":
            ax.text(rmax + 0.2, zc, "Win_Be", fontsize=7, va="center", color="#5C3566")

    col = bounds["COLLIMATOR"]
    rect(
        ax,
        -col["r_max"],
        col["z_center"] - col["hz"],
        2 * col["r_max"],
        2 * col["hz"],
        COLORS["Collimator"],
        0.68,
        ec="#111111",
        zorder=11,
    )
    ax.text(float(col["r_max"]) + 0.2, col["z_center"], "W collimator", fontsize=7, va="center")

    if show_source:
        z_source = float(bounds["META"].get("science_beam_z_cm", 12.766))
        r_source = float(bounds["META"].get("science_beam_radius_cm", 1.8))
        ax.plot([-r_source, r_source], [z_source, z_source], color=COLORS["Source"], lw=2.1, zorder=15)
        ax.annotate(
            f"511 keV source plane\nz={z_source:g} cm, r={r_source:g} cm, -Z",
            xy=(r_source, z_source),
            xytext=(r_source + 0.65, z_source - 1.05),
            arrowprops={"arrowstyle": "->", "lw": 0.9, "color": COLORS["Source"]},
            fontsize=7.2,
            color=COLORS["Source"],
        )

    ax.axvline(0, color="0.55", lw=0.5, ls=":", zorder=20)
    max_r = max(float(s["r_out"]) for s in bounds["SHIELDS"].values())
    z_min = min(float(s["z_out_bot"]) for s in bounds["SHIELDS"].values())
    z_max = max(float(s["z_out_top"]) for s in bounds["SHIELDS"].values())
    ax.set_xlim(-1.08 * max_r, 1.16 * max_r)
    ax.set_ylim(z_min - 0.5, z_max + 0.65)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.35, alpha=0.22)


def draw_tes_xy(ax, bounds: dict, pixels_xy: list[tuple[float, float]], briks: dict[str, tuple[float, float, float]]) -> None:
    ax.set_title("One TES layer: X-Y footprint", fontsize=11)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    substrate_r = float(bounds["SUBSTRATES"][0]["r_max"])
    active_r = float(bounds["META"].get("eff_r", bounds["TES_LAYERS"][0]["r_max"]))
    pixel_hx, pixel_hy, _pixel_hz = briks.get("TES_Pixel_L0", (0.075, 0.075, 0.15))

    ax.add_patch(Circle((0, 0), substrate_r, facecolor="#E5E5E5", edgecolor="#333333", lw=0.9, alpha=0.85, zorder=1))
    ax.add_patch(Circle((0, 0), active_r, fill=False, edgecolor=COLORS["TES"], lw=1.0, ls="--", zorder=4))
    for x, y in pixels_xy:
        rect(ax, x - pixel_hx, y - pixel_hy, 2 * pixel_hx, 2 * pixel_hy, COLORS["TES"], 0.54, ec="#8E2F2E", lw=0.25, zorder=3)
    ax.text(-1.15 * substrate_r, 1.12 * substrate_r, f"{len(pixels_xy)} Ta pixels\nsubstrate r={substrate_r:g} cm", fontsize=7, va="top")
    ax.set_xlim(-1.16 * substrate_r, 1.16 * substrate_r)
    ax.set_ylim(-1.16 * substrate_r, 1.16 * substrate_r)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.3, alpha=0.2)


def draw_collimator_xy(ax, positions: dict[str, tuple[float, float, float]], briks: dict[str, tuple[float, float, float]], bounds: dict) -> None:
    ax.set_title("Entrance W collimator: X-Y view", fontsize=11)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    rmax = float(bounds["COLLIMATOR"]["r_max"])
    ax.add_patch(Circle((0, 0), rmax, facecolor="#F4F4F4", edgecolor="#333333", lw=0.9, alpha=0.75, zorder=1))

    hx_x, hy_x, _hz_x = briks.get("CollBarX", (2.053, 0.0065, 0.05))
    hx_y, hy_y, _hz_y = briks.get("CollBarY", (0.0065, 2.053, 0.05))
    for name, (x, y, _z) in positions.items():
        if name.startswith("CollBarX_"):
            rect(ax, x - hx_x, y - hy_x, 2 * hx_x, 2 * hy_x, COLORS["Collimator"], 0.60, ec="#111111", lw=0.2, zorder=3)
        elif name.startswith("CollBarY_"):
            rect(ax, x - hx_y, y - hy_y, 2 * hx_y, 2 * hy_y, COLORS["Collimator"], 0.60, ec="#111111", lw=0.2, zorder=4)

    ax.text(-1.15 * rmax, 1.12 * rmax, f"pitch={bounds['META']['coll_pitch']:.3f} cm\nhole={bounds['META']['coll_hole']:.3f} cm", fontsize=7, va="top")
    ax.set_xlim(-1.16 * rmax, 1.16 * rmax)
    ax.set_ylim(-1.16 * rmax, 1.16 * rmax)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.3, alpha=0.2)


def make_figure(bounds: dict, positions: dict[str, tuple[float, float, float]], briks: dict[str, tuple[float, float, float]], output: Path, show_source: bool) -> None:
    pixels_xy = layer0_pixels(positions)
    if not pixels_xy:
        raise ValueError("No TP_L0_* pixel placements found in geometry file")

    fig = plt.figure(figsize=(12.6, 10.3), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.52, 1.0], height_ratios=[1.0, 1.0])
    ax_main = fig.add_subplot(gs[:, 0])
    ax_tes = fig.add_subplot(gs[0, 1])
    ax_coll = fig.add_subplot(gs[1, 1])

    draw_xz_main(ax_main, bounds, pixels_xy, briks, show_source=show_source)
    draw_tes_xy(ax_tes, bounds, pixels_xy, briks)
    draw_collimator_xy(ax_coll, positions, briks, bounds)

    legend = [
        Patch(facecolor=COLORS["TES"], edgecolor="#8E2F2E", alpha=0.5, label="Ta TES pixels"),
        Patch(facecolor=COLORS["Substrate"], edgecolor="#111111", alpha=0.55, label="Si substrates"),
        Patch(facecolor=COLORS["Cu"], edgecolor="#8A4D12", alpha=0.62, label="Cu base/support"),
        Patch(facecolor=COLORS["Collimator"], edgecolor="#111111", alpha=0.68, label="W collimator"),
        Patch(facecolor=COLORS["Window"], edgecolor="#7B4B84", alpha=0.58, label="thin entrance windows"),
        Patch(facecolor=COLORS["BGO_Shield"], edgecolor=COLORS["BGO_Shield"], alpha=0.34, label="BGO shield"),
    ]
    ax_main.legend(handles=legend, loc="lower left", fontsize=7, frameon=True)

    fig.suptitle("XZTES six-layer TES spectrometer geometry schematic", fontsize=14)
    fig.text(
        0.012,
        0.012,
        "Generated from XZTES/bounds.json and XZTES/TibetTES_v5_6layers.geo after cm scaling. "
        "Thin windows are vertically enlarged for visibility; TES pixels are shown by projection in X-Z.",
        fontsize=7.5,
        color="#333333",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bounds", type=Path, default=DEFAULT_BOUNDS, help="Path to XZTES bounds.json")
    parser.add_argument("--geo", type=Path, default=DEFAULT_GEO, help="Path to TibetTES_v5_6layers.geo")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output PNG path")
    parser.add_argument("--no-source", action="store_true", help="Do not draw the current 511 keV source plane")
    args = parser.parse_args()

    bounds = load_json(args.bounds)
    positions, briks = parse_geo(args.geo)
    make_figure(bounds, positions, briks, args.output, show_source=not args.no_source)
    print(f"[OK] wrote {args.output}")


if __name__ == "__main__":
    main()
