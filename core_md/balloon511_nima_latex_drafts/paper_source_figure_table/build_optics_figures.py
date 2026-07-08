#!/usr/bin/env python3
"""Build manuscript-facing optics figures from the current Step04 outputs."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle


ROOT = Path(__file__).resolve().parents[3]
STEP04 = ROOT / "stepwise_maintenance" / "step04_opticsim"
RUN = STEP04 / "outputs" / "opticsim_laue_bfull_f10m_a1_r2_3seed"
OUTDIR = Path(__file__).resolve().parent

DESIGN_JSON = STEP04 / "ge111_balloon511_f10m_511keV_design_summary.json"
CONFIG_CSV = STEP04 / "ge111_balloon511_f10m_511KeV_line_config.csv"
if not CONFIG_CSV.exists():
    CONFIG_CSV = STEP04 / "ge111_balloon511_f10m_511keV_line_config.csv"
FOCAL_CSV = RUN / "focal_crossings.csv"

TRANSPORT_PNG = OUTDIR / "fig_optics_laue_transport_schematic.png"
SPOT_PNG = OUTDIR / "fig_optics_focal_crossings_xy.png"
METADATA_JSON = OUTDIR / "fig_optics_generation_metadata.json"


def read_one_config(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected one Laue ring row in {path}, found {len(rows)}")
    return rows[0]


def read_focal_crossings(path: Path, be_radius_mm: float) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("source_tag") != "laue_bfull_diffracted":
                continue
            x_mm = float(row["x_mm"])
            y_mm = float(row["y_mm"])
            radius_mm = math.hypot(x_mm, y_mm)
            if radius_mm <= be_radius_mm + 1.0e-9:
                rows.append(
                    {
                        "x_mm": x_mm,
                        "y_mm": y_mm,
                        "radius_mm": radius_mm,
                        "ux": float(row["ux"]),
                        "uy": float(row["uy"]),
                        "uz": float(row["uz"]),
                    }
                )
    if not rows:
        raise ValueError(f"No accepted focal crossings found in {path}")
    return rows


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    idx = q * (len(ordered) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    frac = idx - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def sample_evenly(rows: list[dict[str, float]], max_rows: int) -> list[dict[str, float]]:
    if len(rows) <= max_rows:
        return rows
    step = len(rows) / max_rows
    return [rows[min(int(i * step), len(rows) - 1)] for i in range(max_rows)]


def write_transport_figure(
    design: dict[str, float | str],
    config: dict[str, str],
    focal_rows: list[dict[str, float]],
    be_radius_mm: float,
) -> None:
    focal_m = float(design["focal_length_mm"]) / 1000.0
    ring_radius = float(config["radius_mm"])
    tile_size = float(config["tile_size_mm"])
    thickness = float(config["thickness_mm"])
    energy = float(config["design_energy_keV"])
    n_tiles = int(float(config["n_tiles"]))

    fig, ax = plt.subplots(figsize=(9.4, 5.35), dpi=220)

    ax.axvline(0.0, color="#111827", linewidth=1.0, alpha=0.75)
    ax.axvline(focal_m, color="#7c2d12", linewidth=1.0, alpha=0.75)
    ax.axhline(0.0, color="#4b5563", linewidth=0.8, alpha=0.4)

    half_tile = 0.5 * tile_size
    half_thick_m = 0.5 * thickness / 1000.0
    ax.add_patch(
        Rectangle(
            (-half_thick_m, ring_radius - half_tile),
            2.0 * half_thick_m,
            tile_size,
            facecolor="#0f766e",
            edgecolor="#0f766e",
            alpha=0.28,
            linewidth=0.8,
            label="projected Ge tile footprint",
        )
    )
    ax.scatter([0.0], [ring_radius], s=28, color="#047857", zorder=6)

    ax.plot([-0.5, 0.0], [ring_radius, ring_radius], color="#2563eb", linewidth=2.0)

    for row in sample_evenly(focal_rows, 4500):
        ax.plot(
            [0.0, focal_m],
            [ring_radius, row["radius_mm"]],
            color="#dc2626",
            alpha=0.028,
            linewidth=0.28,
            solid_capstyle="round",
        )

    focal_radii = [row["radius_mm"] for row in focal_rows]
    sampled_radii = [row["radius_mm"] for row in sample_evenly(focal_rows, 900)]
    ax.scatter(
        [focal_m] * len(sampled_radii),
        sampled_radii,
        s=4,
        color="#991b1b",
        alpha=0.35,
        zorder=5,
        linewidths=0,
    )
    ax.plot([focal_m, focal_m], [0.0, be_radius_mm], color="#f97316", linewidth=3.0, alpha=0.62)
    ax.plot(
        [focal_m - 0.08, focal_m + 0.08],
        [be_radius_mm, be_radius_mm],
        color="#f97316",
        linewidth=1.5,
        alpha=0.85,
    )

    ax.text(
        0.06,
        ring_radius + half_tile + 3.0,
        f"Ge(111), {energy:.0f} keV ring\nR = {ring_radius:.2f} mm; {n_tiles} tiles",
        color="#064e3b",
        fontsize=8.4,
        va="bottom",
    )
    ax.text(-0.48, ring_radius + 2.3, "incident beam", color="#1d4ed8", fontsize=8.2, va="bottom")
    ax.text(
        focal_m - 2.45,
        be_radius_mm - 7.0,
        "accepted focal crossings",
        color="#991b1b",
        fontsize=8.2,
        va="bottom",
    )
    ax.text(
        focal_m - 1.20,
        be_radius_mm + 2.5,
        "Be aperture radius",
        color="#9a3412",
        fontsize=8.2,
        va="bottom",
    )

    ax.set_xlim(-0.58, focal_m + 0.45)
    ax.set_ylim(0.0, ring_radius + half_tile + 17.0)
    ax.set_xlabel("z position from Laue ring plane (m)")
    ax.set_ylabel("radial distance from optical axis (mm)")
    ax.grid(True, color="#d1d5db", linewidth=0.45, alpha=0.72)
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color="#2563eb", lw=2.0, label="incident"),
            plt.Line2D([0], [0], color="#dc2626", lw=2.0, label="diffracted"),
            plt.Line2D([0], [0], color="#f97316", lw=2.0, label="entrance aperture"),
        ],
        loc="upper right",
        frameon=True,
        framealpha=0.93,
        fontsize=8.0,
    )
    fig.tight_layout()
    fig.savefig(TRANSPORT_PNG)
    plt.close(fig)


def write_spot_figure(focal_rows: list[dict[str, float]], be_radius_mm: float) -> None:
    x_cm = [row["x_mm"] / 10.0 for row in focal_rows]
    y_cm = [row["y_mm"] / 10.0 for row in focal_rows]
    be_radius_cm = be_radius_mm / 10.0

    fig, ax = plt.subplots(figsize=(5.4, 5.25), dpi=220)
    ax.scatter(x_cm, y_cm, s=2.2, color="#0f8b8d", alpha=0.23, linewidths=0, label="accepted focal crossings")
    ax.add_patch(
        Circle(
            (0.0, 0.0),
            be_radius_cm,
            fill=False,
            edgecolor="#dc2626",
            linewidth=2.0,
            label="Be-window aperture",
        )
    )
    limit = max(2.05, be_radius_cm * 1.08)
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("focal-plane transverse coordinate 1 (cm)")
    ax.set_ylabel("focal-plane transverse coordinate 2 (cm)")
    ax.grid(True, color="#cbd5e1", linewidth=0.45, alpha=0.72)
    ax.legend(loc="upper right", frameon=True, framealpha=0.93, fontsize=8.0)
    fig.tight_layout()
    fig.savefig(SPOT_PNG)
    plt.close(fig)


def main() -> None:
    design = json.loads(DESIGN_JSON.read_text())
    config = read_one_config(CONFIG_CSV)
    be_radius_mm = 18.98
    focal_rows = read_focal_crossings(FOCAL_CSV, be_radius_mm)

    write_transport_figure(design, config, focal_rows, be_radius_mm)
    write_spot_figure(focal_rows, be_radius_mm)

    radii = [row["radius_mm"] for row in focal_rows]
    metadata = {
        "inputs": {
            "design_summary": str(DESIGN_JSON.relative_to(ROOT)),
            "ring_config": str(CONFIG_CSV.relative_to(ROOT)),
            "focal_crossings": str(FOCAL_CSV.relative_to(ROOT)),
        },
        "outputs": {
            "transport_schematic": str(TRANSPORT_PNG.relative_to(ROOT)),
            "focal_spot": str(SPOT_PNG.relative_to(ROOT)),
        },
        "configuration": {
            "energy_keV": float(config["design_energy_keV"]),
            "focal_length_mm": float(design["focal_length_mm"]),
            "ring_radius_mm": float(config["radius_mm"]),
            "n_tiles": int(float(config["n_tiles"])),
            "tile_size_mm": float(config["tile_size_mm"]),
            "mosaic_fwhm_arcsec": float(design["mosaic_fwhm_arcsec"]),
            "be_radius_mm": be_radius_mm,
        },
        "focal_distribution": {
            "accepted_rows": len(focal_rows),
            "r50_mm": quantile(radii, 0.50),
            "r90_mm": quantile(radii, 0.90),
            "r99_mm": quantile(radii, 0.99),
            "rmax_mm": max(radii),
        },
        "note": "Figures are generated from the current f10m Ge(111) ring configuration and tracked diffracted focal-plane crossings accepted by the Be entrance aperture.",
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {TRANSPORT_PNG}")
    print(f"Wrote {SPOT_PNG}")
    print(f"Wrote {METADATA_JSON}")


if __name__ == "__main__":
    main()
