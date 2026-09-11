#!/usr/bin/env python3
"""Plot MEGAlib/Cosima Si deposit locations and energies for the 86 events."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


HALF_SIDE_MM = 18.0
PIXEL_SIDE_MM = 1.5


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    input_path = ROOT / "outputs/unvetoed_events.csv"
    pixel_path = ROOT / "outputs/tes_pixel_map.csv"
    output_prefix = ROOT / "outputs/figures/sh3_megalib_si_depositions_six_layers"

    pixel_rows = list(csv_rows(pixel_path))
    if len(pixel_rows) != 376:
        raise ValueError(f"Expected 376 pixels, found {len(pixel_rows)}")
    pixel_centers = [
        (float(row["y_mm"]), float(row["z_mm"])) for row in pixel_rows
    ]

    hits: dict[int, list[dict[str, str]]] = defaultdict(list)
    event_orders: dict[int, set[int]] = defaultdict(set)
    strict_event_orders: dict[int, set[int]] = defaultdict(set)
    for row in csv_rows(input_path):
        layer = int(row["layer"])
        hits[layer].append(row)
        event_order = int(row["event_order"])
        event_orders[layer].add(event_order)
        if int(row["strict_recoil_event"]):
            strict_event_orders[layer].add(event_order)

    if set(hits) != set(range(6)):
        raise ValueError(f"Expected layers 0..5, found {sorted(hits)}")

    all_energy = np.asarray(
        [float(row["edep_keV"]) for layer in range(6) for row in hits[layer]]
    )
    if len(all_energy) != 327 or not np.all(all_energy > 0):
        raise ValueError("Expected 327 positive Si deposits")
    if len({int(row["event_order"]) for layer in range(6) for row in hits[layer]}) != 86:
        raise ValueError("Expected 86 unique unvetoed events")

    norm = colors.LogNorm(vmin=max(float(all_energy.min()), 1e-4), vmax=float(all_energy.max()))
    cmap = plt.colormaps["viridis"]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.titlesize": 19,
        }
    )
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=False)
    fig.subplots_adjust(left=0.055, right=0.91, bottom=0.12, top=0.86, wspace=0.24, hspace=0.34)

    layer_summary: dict[str, dict[str, float | int]] = {}
    for layer, ax in enumerate(axes.flat):
        rows = hits[layer]
        y_mm = np.asarray([float(row["slab_local_y_mm"]) for row in rows])
        z_mm = np.asarray([float(row["slab_local_z_mm"]) for row in rows])
        energy = np.asarray([float(row["edep_keV"]) for row in rows])
        marker_size = 18.0 + 95.0 * np.sqrt(energy / all_energy.max())

        ax.add_patch(
            Rectangle(
                (-HALF_SIDE_MM, -HALF_SIDE_MM),
                2 * HALF_SIDE_MM,
                2 * HALF_SIDE_MM,
                facecolor="#f4f5f6",
                edgecolor="#222222",
                linewidth=1.2,
                zorder=0,
            )
        )
        footprints = [
            Rectangle(
                (y - PIXEL_SIDE_MM / 2, z - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
            )
            for y, z in pixel_centers
        ]
        ax.add_collection(
            PatchCollection(
                footprints,
                facecolor=(1.0, 1.0, 1.0, 0.52),
                edgecolor=(0.35, 0.45, 0.50, 0.48),
                linewidth=0.30,
                zorder=1,
            )
        )
        ax.scatter(
            y_mm,
            z_mm,
            s=marker_size,
            c=energy,
            cmap=cmap,
            norm=norm,
            edgecolors="#17242b",
            linewidths=0.38,
            alpha=0.92,
            zorder=3,
        )
        total_kev = float(energy.sum())
        ax.set_title(
            f"L{layer}  |  {len(event_orders[layer])} event groups, {len(rows)} HITs\n"
            f"deposited energy = {total_kev:.3f} keV"
        )
        ax.set_xlabel("substrate local y [mm]")
        ax.set_ylabel("substrate local z [mm]")
        ax.set_xlim(-18.8, 18.8)
        ax.set_ylim(-18.8, 18.8)
        ax.set_aspect("equal")
        ax.grid(color="#d5d8dc", linewidth=0.5, alpha=0.40)
        ax.set_axisbelow(True)

        layer_summary[f"L{layer}"] = {
            "event_groups": len(event_orders[layer]),
            "strict_event_groups": len(strict_event_orders[layer]),
            "hits": len(rows),
            "deposited_energy_keV": total_kev,
        }

    cax = fig.add_axes([0.93, 0.22, 0.016, 0.49])
    cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    cbar.set_label("single-HIT deposited energy [keV]")

    fig.suptitle(
        "SH3 MEGAlib/Cosima neutron histories — positive Si deposits in all six layers",
        y=0.96,
    )
    fig.text(
        0.5,
        0.055,
        (
            "10⁷ transported neutrons → 86 events with Si > 0 and BGO < 50 keV; "
            f"327 positive Si HITs, {all_energy.sum():.3f} keV deposited in total."
        ),
        ha="center",
        fontsize=11.5,
    )
    fig.text(
        0.5,
        0.024,
        (
            "Semi-transparent white squares are the 376 pixel footprints (1.5 × 1.5 mm²); dots are Si HITs. "
            "Overlaying them shows which pixel footprint lies beneath each deposit."
        ),
        ha="center",
        fontsize=9.8,
        color="#444444",
    )

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=220, facecolor="white")
    fig.savefig(pdf_path, facecolor="white")
    plt.close(fig)

    metadata = {
        "schema_version": 1,
        "scope": "all 86 unvetoed Si-positive events from the 10^7-neutron MEGAlib/Cosima transport",
        "inputs": {
            "si_deposits": {"path": str(input_path), "sha256": sha256(input_path)},
            "pixel_map": {"path": str(pixel_path), "sha256": sha256(pixel_path)},
        },
        "totals": {
            "events": 86,
            "layer_event_groups": sum(len(group) for group in event_orders.values()),
            "hits": int(len(all_energy)),
            "deposited_energy_keV": float(all_energy.sum()),
        },
        "layers": layer_summary,
        "outputs": {"png": str(png_path), "pdf": str(pdf_path)},
        "interpretation": (
            "Dots are positive Si energy-deposit hits in neutron histories, including direct neutron recoils "
            "and secondary gamma/electron cascades; semi-transparent white squares show the pixel footprints "
            "under the deposit coordinates."
        ),
    }
    metadata_path = output_prefix.with_name(output_prefix.name + "_metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata["totals"], sort_keys=True))
    print(png_path)


if __name__ == "__main__":
    main()
