#!/usr/bin/env python3
"""Plot all 86 unvetoed Si events as six layer-resolved G4CMP maps."""

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


HALF_MM = 18.0
PIXEL_SIDE_MM = 1.5


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def make_lognorm(values: np.ndarray) -> colors.LogNorm:
    positive = values[np.isfinite(values) & (values > 0)]
    if not positive.size:
        raise ValueError("No positive values for color scale")
    vmax = float(positive.max())
    return colors.LogNorm(vmin=max(float(positive.min()), vmax * 1e-5), vmax=vmax)


def main() -> None:
    pixel_path = ROOT / "outputs/tes_pixel_map.csv"
    deposit_path = ROOT / "outputs/unvetoed_events.csv"
    run_dir = ROOT / "runs/staircase/04_all86/tuned_c_area0p12"
    hit_path = run_dir / "hits.csv"
    event_path = run_dir / "events.csv"
    output_prefix = ROOT / "outputs/figures/sh3_all86_six_layer_matplotlib_map"

    pixel_rows = list(rows(pixel_path))
    if len(pixel_rows) != 376:
        raise ValueError(f"Expected 376 pixels, found {len(pixel_rows)}")
    centers = {
        int(row["pixel_id"]): (float(row["y_mm"]), float(row["z_mm"]))
        for row in pixel_rows
    }

    deposit_y: dict[int, list[float]] = defaultdict(list)
    deposit_z: dict[int, list[float]] = defaultdict(list)
    deposit_e: dict[int, list[float]] = defaultdict(list)
    event_keys_by_layer: dict[int, set[int]] = defaultdict(set)
    input_kev = np.zeros(6)
    n_deposits = np.zeros(6, dtype=int)
    for row in rows(deposit_path):
        layer = int(row["layer"])
        energy = float(row["edep_keV"])
        deposit_y[layer].append(float(row["slab_local_y_mm"]))
        deposit_z[layer].append(float(row["slab_local_z_mm"]))
        deposit_e[layer].append(energy)
        input_kev[layer] += energy
        n_deposits[layer] += 1
        event_keys_by_layer[layer].add(int(row["event_order"]))
    if sum(len(event_keys_by_layer[layer]) for layer in range(6)) != 87:
        raise ValueError("Expected 87 layer-event groups from 86 events")

    sensor_by_layer_pixel: defaultdict[tuple[int, int], float] = defaultdict(float)
    terminal_kev = np.zeros(6)
    sensor_kev = np.zeros(6)
    terminal_hits = np.zeros(6, dtype=int)
    for row in rows(hit_path):
        layer = int(row["layer"])
        energy = float(row["weighted_energy_eV"]) / 1000.0
        terminal_kev[layer] += energy
        terminal_hits[layer] += 1
        if row["surface_class"] == "sensor":
            pixel_id = int(row["pixel_id"])
            sensor_by_layer_pixel[layer, pixel_id] += energy
            sensor_kev[layer] += energy
        elif row["surface_class"] != "bath":
            raise ValueError(f"Unexpected surface {row['surface_class']!r}")

    if not np.allclose(terminal_kev, input_kev, atol=1e-5, rtol=0):
        raise ValueError(
            "Layer energy closure failed:\n"
            f"input={input_kev.tolist()}\nterminal={terminal_kev.tolist()}"
        )
    pixel_values = np.asarray(list(sensor_by_layer_pixel.values()))
    pixel_norm = make_lognorm(pixel_values)
    pixel_cmap = plt.colormaps["plasma"].copy()
    pixel_cmap.set_under("#ffffff")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10.3,
            "axes.labelsize": 8.5,
            "figure.titlesize": 15,
        }
    )
    fig, axes = plt.subplots(2, 3, figsize=(15.8, 10.5))
    fig.subplots_adjust(left=0.055, right=0.88, bottom=0.13, top=0.90, wspace=0.25, hspace=0.28)

    for layer, ax in enumerate(axes.flat):
        ax.add_patch(
            Rectangle(
                (-18, -18), 36, 36, facecolor="#edf2f5", edgecolor="#17324d", linewidth=1.7
            )
        )

        outlines = [
            Rectangle(
                (y - PIXEL_SIDE_MM / 2, z - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
            )
            for y, z in centers.values()
        ]
        ax.add_collection(
            PatchCollection(
                outlines,
                facecolor=(1.0, 1.0, 1.0, 0.68),
                edgecolor=(0.38, 0.49, 0.55, 0.52),
                linewidth=0.30,
                zorder=2,
            )
        )
        active_patches = []
        active_energies = []
        for pixel_id, (y, z) in centers.items():
            energy = sensor_by_layer_pixel.get((layer, pixel_id), 0.0)
            if energy <= 0:
                continue
            active_patches.append(
                Rectangle(
                    (y - PIXEL_SIDE_MM / 2, z - PIXEL_SIDE_MM / 2),
                    PIXEL_SIDE_MM,
                    PIXEL_SIDE_MM,
                )
            )
            active_energies.append(energy)
        active = PatchCollection(
            active_patches,
            cmap=pixel_cmap,
            norm=pixel_norm,
            edgecolor=(1.0, 1.0, 1.0, 0.42),
            linewidth=0.20,
            zorder=3,
        )
        active.set_array(np.asarray(active_energies))
        ax.add_collection(active)

        dep_e = np.asarray(deposit_e[layer])
        ax.scatter(
            deposit_y[layer],
            deposit_z[layer],
            s=5 + 28 * np.sqrt(dep_e / dep_e.max()),
            color="#00c9d8",
            edgecolors="#102a33",
            linewidths=0.30,
            alpha=0.90,
            zorder=5,
        )
        eta = sensor_kev[layer] / input_kev[layer]
        ax.set_title(
            f"L{layer}: {len(event_keys_by_layer[layer])} event groups, {n_deposits[layer]} deposits\n"
            f"Si {input_kev[layer]:.3f} keV → sensor pixels {sensor_kev[layer]:.3f} keV (η={eta:.3f})"
        )
        ax.set_xlabel("local y [mm]")
        ax.set_ylabel("local z [mm]")
        ax.set_xlim(-18.6, 18.6)
        ax.set_ylim(-18.6, 18.6)
        ax.set_aspect("equal")

    pixel_cax = fig.add_axes([0.905, 0.22, 0.015, 0.52])
    pixel_bar = fig.colorbar(
        ScalarMappable(norm=pixel_norm, cmap=pixel_cmap), cax=pixel_cax
    )
    pixel_bar.set_label("Time-integrated athermal energy delivered per sensor pixel [keV]")

    fig.suptitle(
        "SH3 all 86 unvetoed Si events — G4CMP energy flow into sensor pixels\n"
        "tuned-C interface scenario (comparative envelope point, not a calibrated prediction)"
    )
    fig.text(
        0.5,
        0.045,
        (
            f"Across six layers: 86 events / 87 layer-event groups / {int(n_deposits.sum())} Si deposits; "
            f"Si input {input_kev.sum():.3f} keV; G4CMP TES phonon collection {sensor_kev.sum():.3f} keV "
            f"(η={sensor_kev.sum() / input_kev.sum():.4f})."
        ),
        ha="center",
        fontsize=9.2,
    )
    fig.text(
        0.5,
        0.020,
        (
            "Cyan dots are original Si deposits; each colored 1.5 mm cell is the time-integrated athermal "
            "phonon energy delivered to that sensor pixel. This is ∫P_i(t)dt, not temperature or a heat-flux vector."
        ),
        ha="center",
        fontsize=8.2,
        color="#3b4650",
    )

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    metadata_path = output_prefix.with_name(output_prefix.name + "_metadata.json")
    fig.savefig(
        png_path,
        dpi=220,
        facecolor="white",
        metadata={"Software": "Matplotlib; plot_all86_six_layers.py"},
    )
    fig.savefig(
        pdf_path,
        facecolor="white",
        metadata={
            "Creator": "Matplotlib; plot_all86_six_layers.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)

    metadata = {
        "schema_version": 1,
        "scope": "all 86 unvetoed Si events, layer-resolved G4CMP phonon transport",
        "scenario": "tuned_c_area0p12",
        "warning": "Comparative interface-envelope point, not a calibrated thermal prediction",
        "visualization_meaning": (
            "Each colored full pixel footprint visualizes the time-integrated athermal energy intercepted by "
            "the sensor assigned to that pixel. Filling the full footprint is a categorical display choice; "
            "it does not claim that the physical sensor covers the full pixel. No temperature field or "
            "Fourier heat-flux vector is inferred from discrete G4CMP terminal records."
        ),
        "layers": {
            f"L{layer}": {
                "event_groups": len(event_keys_by_layer[layer]),
                "deposits": int(n_deposits[layer]),
                "si_input_keV": float(input_kev[layer]),
                "terminal_keV": float(terminal_kev[layer]),
                "sensor_keV": float(sensor_kev[layer]),
                "sensor_eta": float(sensor_kev[layer] / input_kev[layer]),
                "terminal_hits": int(terminal_hits[layer]),
            }
            for layer in range(6)
        },
        "totals": {
            "events": 86,
            "layer_event_groups": 87,
            "deposits": int(n_deposits.sum()),
            "si_input_keV": float(input_kev.sum()),
            "sensor_keV": float(sensor_kev.sum()),
            "sensor_eta": float(sensor_kev.sum() / input_kev.sum()),
        },
        "inputs": {
            "pixel_map": {"path": str(pixel_path), "sha256": digest(pixel_path)},
            "si_deposits": {"path": str(deposit_path), "sha256": digest(deposit_path)},
            "g4cmp_hits": {"path": str(hit_path), "sha256": digest(hit_path)},
            "g4cmp_events": {"path": str(event_path), "sha256": digest(event_path)},
        },
        "outputs": {"png": str(png_path), "pdf": str(pdf_path)},
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"png": str(png_path), "pdf": str(pdf_path), "metadata": str(metadata_path), "layers": metadata["layers"], "totals": metadata["totals"]}, indent=2))


if __name__ == "__main__":
    main()
