#!/usr/bin/env python3
"""Draw the complete six-layer data record for SH3 candidate C.

L0 contains the measured Si deposits and their G4CMP phonon transport. L1
contains the two direct TES deposits. L2--L5 contain no deposit for this event.
TES-to-Si backflow and TES electrothermal spreading are not modeled.
"""

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


SI_HALF_WIDTH_MM = 18.0
PIXEL_SIDE_MM = 1.5


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def file_sha256(path: Path) -> str:
    """Return SHA-256 without relying on external utilities."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def log_norm(values: np.ndarray, floor_fraction: float = 1e-5) -> colors.LogNorm:
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        raise ValueError("No positive values for logarithmic color scale")
    vmax = float(positive.max())
    vmin = max(float(positive.min()), vmax * floor_fraction)
    return colors.LogNorm(vmin=vmin, vmax=vmax)


def main() -> None:
    pixel_path = ROOT / "outputs/tes_pixel_map.csv"
    deposit_path = ROOT / "outputs/g4cmp_inputs/02c_candidate_C.csv"
    direct_path = ROOT / "outputs/candidate_direct_tes_channels.csv"
    hit_paths = sorted(
        (ROOT / "runs/staircase/02c_candidate_C_replicates").glob("rep*/hits.csv")
    )
    output_prefix = ROOT / "outputs/figures/sh3_candidate_C_six_layer_matplotlib_map"

    pixels = read_csv(pixel_path)
    deposits = read_csv(deposit_path)
    direct_rows = [row for row in read_csv(direct_path) if row["candidate"] == "C"]
    if len(pixels) != 376 or len(deposits) != 43 or len(hit_paths) != 5:
        raise ValueError(
            f"Unexpected inputs: pixels={len(pixels)}, deposits={len(deposits)}, "
            f"replicates={len(hit_paths)}"
        )
    if {int(row["layer"]) for row in deposits} != {0}:
        raise ValueError("Candidate-C Si deposits are not confined to L0")
    if {int(row["layer"]) for row in direct_rows} != {1}:
        raise ValueError("Candidate-C direct TES deposits are not confined to L1")

    centers = {
        int(row["pixel_id"]): (float(row["y_mm"]), float(row["z_mm"]))
        for row in pixels
    }
    deposit_y = np.asarray([float(row["local_y_mm"]) for row in deposits])
    deposit_z = np.asarray([float(row["local_z_mm"]) for row in deposits])
    deposit_e = np.asarray([float(row["energy_keV"]) for row in deposits])
    si_input_kev = float(deposit_e.sum())

    l0_sensor_sum: defaultdict[int, float] = defaultdict(float)
    replicate_totals: list[float] = []
    replicate_sensor: list[float] = []
    for path in hit_paths:
        rep_total = 0.0
        rep_sensor = 0.0
        for row in read_csv(path):
            weight_kev = float(row["weighted_energy_eV"]) / 1000.0
            rep_total += weight_kev
            if row["surface_class"] == "sensor":
                pixel_id = int(row["pixel_id"])
                l0_sensor_sum[pixel_id] += weight_kev
                rep_sensor += weight_kev
            elif row["surface_class"] != "bath":
                raise ValueError(f"Unknown surface class {row['surface_class']!r}")
        replicate_totals.append(rep_total)
        replicate_sensor.append(rep_sensor)

    n_reps = len(hit_paths)
    if not all(np.isclose(value, si_input_kev, atol=1e-6, rtol=0) for value in replicate_totals):
        raise ValueError("At least one G4CMP replicate fails energy closure")
    l0_sensor = {pixel_id: energy / n_reps for pixel_id, energy in l0_sensor_sum.items()}
    mean_l0_sensor_kev = float(np.mean(replicate_sensor))
    dominant_l0_pixel, dominant_l0_energy = max(l0_sensor.items(), key=lambda item: item[1])

    direct_l1 = {
        int(row["pixel_id"]): float(row["energy_keV"]) for row in direct_rows
    }
    direct_l1_kev = float(sum(direct_l1.values()))
    combined_kev = mean_l0_sensor_kev + direct_l1_kev

    all_tes_values = np.asarray(list(l0_sensor.values()) + list(direct_l1.values()))
    tes_cmap = plt.colormaps["plasma"].copy()
    tes_cmap.set_under("#ffffff")
    tes_norm = log_norm(all_tes_values)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10.5,
            "axes.labelsize": 8.5,
            "figure.titlesize": 15,
        }
    )
    fig, axes = plt.subplots(2, 3, figsize=(15.8, 10.5))
    fig.subplots_adjust(left=0.055, right=0.88, bottom=0.13, top=0.90, wspace=0.25, hspace=0.28)

    layer_titles = {
        0: (
            "L0 — Si deposits and G4CMP energy delivered to pixels\n"
            f"Si = {si_input_kev:.3f} keV; sensor pixels = {mean_l0_sensor_kev:.3f} keV"
        ),
        1: (
            "L1 — direct pixel deposition\n"
            f"P231 = {direct_l1[231]:.3f} keV; P147 = {direct_l1[147]:.3f} keV"
        ),
        2: "L2 — no recorded deposition",
        3: "L3 — no recorded deposition",
        4: "L4 — no recorded deposition",
        5: "L5 — no recorded deposition",
    }

    for layer, ax in enumerate(axes.flat):
        ax.add_patch(
            Rectangle(
                (-18, -18),
                36,
                36,
                facecolor="#edf2f5",
                edgecolor="#17324d",
                linewidth=1.7,
                zorder=0,
            )
        )
        outlines = [
            Rectangle(
                (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
            )
            for y0, z0 in centers.values()
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

        layer_pixel_energy = l0_sensor if layer == 0 else direct_l1 if layer == 1 else {}
        active_patches = []
        active_values = []
        for pixel_id, energy in layer_pixel_energy.items():
            y0, z0 = centers[pixel_id]
            active_patches.append(
                Rectangle(
                    (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
                    PIXEL_SIDE_MM,
                    PIXEL_SIDE_MM,
                )
            )
            active_values.append(energy)
        if active_patches:
            active = PatchCollection(
                active_patches,
                cmap=tes_cmap,
                norm=tes_norm,
                edgecolor=(1.0, 1.0, 1.0, 0.42),
                linewidth=0.20,
                zorder=3,
            )
            active.set_array(np.asarray(active_values))
            ax.add_collection(active)

        if layer == 0:
            sizes = 8 + 48 * np.sqrt(deposit_e / deposit_e.max())
            ax.scatter(
                deposit_y,
                deposit_z,
                s=sizes,
                color="#00c9d8",
                edgecolors="#102a33",
                linewidths=0.40,
                zorder=5,
                label="43 Si deposits",
            )
            ax.legend(loc="upper left", fontsize=7.5, frameon=True)
            y0, z0 = centers[dominant_l0_pixel]
            ax.annotate(
                f"P{dominant_l0_pixel}: {dominant_l0_energy:.3f} keV",
                xy=(y0, z0),
                xytext=(-86, -30),
                textcoords="offset points",
                arrowprops={"arrowstyle": "->", "color": "#006d77", "lw": 1.1},
                color="#00515a",
                fontsize=8.2,
                weight="bold",
                zorder=6,
            )
        elif layer == 1:
            for pixel_id, energy in sorted(direct_l1.items()):
                y0, z0 = centers[pixel_id]
                offset = (18, 18) if pixel_id == 147 else (18, -28)
                ax.annotate(
                    f"P{pixel_id}: {energy:.3f} keV",
                    xy=(y0, z0),
                    xytext=offset,
                    textcoords="offset points",
                    arrowprops={"arrowstyle": "->", "color": "#006d77", "lw": 1.1},
                    color="#00515a",
                    fontsize=8.5,
                    weight="bold",
                    zorder=6,
                )
        else:
            ax.text(
                0.5,
                0.5,
                "0 keV in candidate C\n(Si and direct pixel records)",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=11,
                color="#506170",
                bbox={"facecolor": "white", "alpha": 0.84, "edgecolor": "#aebbc5"},
                zorder=5,
            )

        ax.set_title(layer_titles[layer])
        ax.set_xlabel("local y [mm]")
        ax.set_ylabel("local z [mm]")
        ax.set_xlim(-18.6, 18.6)
        ax.set_ylim(-18.6, 18.6)
        ax.set_aspect("equal")

    tes_cax = fig.add_axes([0.905, 0.22, 0.015, 0.52])
    tes_bar = fig.colorbar(ScalarMappable(norm=tes_norm, cmap=tes_cmap), cax=tes_cax)
    tes_bar.set_label("Energy delivered / deposited per independent pixel [keV]")

    fig.suptitle(
        "SH3 candidate C — energy delivered to each independent pixel\n"
        "sh3_sisd_n10m_shard0049, event 639"
    )
    fig.text(
        0.5,
        0.045,
        (
            f"Per-channel ledger: L0 Si input {si_input_kev:.3f} keV → mean L0 sensor collection "
            f"{mean_l0_sensor_kev:.3f} keV (η={mean_l0_sensor_kev / si_input_kev:.4f}); "
            f"L1 direct pixels {direct_l1_kev:.3f} keV. The {combined_kev:.3f} keV arithmetic sum is not a single-channel trigger."
        ),
        ha="center",
        fontsize=9.2,
    )
    fig.text(
        0.5,
        0.020,
        (
            "Cyan dots are L0 Si sources; colored cells are time-integrated athermal energy delivered to pixels. "
            "This is ∫P_i(t)dt, not temperature or a continuous heat-flux field."
        ),
        ha="center",
        fontsize=8.4,
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
        metadata={"Software": "Matplotlib; plot_candidate_c_six_layers.py"},
    )
    fig.savefig(
        pdf_path,
        facecolor="white",
        metadata={
            "Creator": "Matplotlib; plot_candidate_c_six_layers.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)

    metadata = {
        "schema_version": 1,
        "scope": "candidate C complete six-layer event record",
        "event": {"job_id": "sh3_sisd_n10m_shard0049", "event_id": 639},
        "interpretation": {
            "L0": "Measured Si deposits plus per-pixel time-integrated G4CMP sensor energy",
            "L1": "Measured direct pixel deposits only; pixel-to-Si backflow not modeled",
            "L2-L5": "No Si or direct pixel deposits in candidate C",
            "colors": "Athermal energy delivered/deposited per independent pixel, not temperature",
            "display": (
                "The full 1.5 mm pixel footprint is colored to make the per-channel energy readable; "
                "this does not claim full-area sensor coverage or a local heat-flux vector."
            ),
        },
        "energy_keV": {
            "L0_si_input": si_input_kev,
            "L0_mean_tes_phonon": mean_l0_sensor_kev,
            "L0_sensor_eta": mean_l0_sensor_kev / si_input_kev,
            "L1_direct_tes": direct_l1_kev,
            "L1_direct_by_pixel": {str(k): v for k, v in sorted(direct_l1.items())},
            "L2": 0.0,
            "L3": 0.0,
            "L4": 0.0,
            "L5": 0.0,
            "arithmetic_tes_sum": combined_kev,
        },
        "inputs": {
            "pixel_map": {"path": str(pixel_path), "sha256": file_sha256(pixel_path)},
            "si_deposits": {"path": str(deposit_path), "sha256": file_sha256(deposit_path)},
            "direct_tes": {"path": str(direct_path), "sha256": file_sha256(direct_path)},
            "g4cmp_hits": [
                {"path": str(path), "sha256": file_sha256(path)} for path in hit_paths
            ],
        },
        "outputs": {"png": str(png_path), "pdf": str(pdf_path)},
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "png": str(png_path),
                "pdf": str(pdf_path),
                "metadata": str(metadata_path),
                "L0_si_keV": si_input_kev,
                "L0_tes_phonon_keV": mean_l0_sensor_kev,
                "L1_direct_tes_keV": direct_l1_kev,
                "arithmetic_tes_sum_keV": combined_kev,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
