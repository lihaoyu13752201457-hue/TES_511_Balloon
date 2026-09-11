#!/usr/bin/env python3
"""Plot a data-driven candidate-C Si phonon/TES energy map with Matplotlib.

The plotted field is the time-integrated terminal phonon energy absorbed on
the sensor and bath surfaces in the existing G4CMP candidate-C replicates. It
is an athermal energy-density map, not a calibrated temperature field.
"""

from __future__ import annotations

import argparse
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
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402


SI_HALF_WIDTH_MM = 18.0
PIXEL_SIDE_MM = 1.5
EXPECTED_PIXELS = 376
EXPECTED_DEPOSITS = 43
EXPECTED_INPUT_KEV = 387.3621815


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=ROOT / "outputs/figures/sh3_candidate_C_matplotlib_energy_map",
    )
    parser.add_argument("--bins", type=int, default=180)
    parser.add_argument("--smoothing-mm", type=float, default=0.30)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def robust_lognorm(values: np.ndarray, low_percentile: float = 2.0) -> colors.LogNorm:
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        raise ValueError("Cannot construct a log scale without positive values")
    vmin = max(float(np.percentile(positive, low_percentile)), float(positive.max()) * 1e-5)
    return colors.LogNorm(vmin=vmin, vmax=float(positive.max()))


def main() -> None:
    args = parse_args()
    if args.bins < 36:
        raise ValueError("--bins must be at least 36")
    if args.smoothing_mm < 0:
        raise ValueError("--smoothing-mm must be non-negative")

    pixel_path = ROOT / "outputs/tes_pixel_map.csv"
    deposit_path = ROOT / "outputs/g4cmp_inputs/02c_candidate_C.csv"
    direct_path = ROOT / "outputs/candidate_direct_tes_channels.csv"
    hit_paths = sorted(
        (ROOT / "runs/staircase/02c_candidate_C_replicates").glob("rep*/hits.csv")
    )
    if not hit_paths:
        raise FileNotFoundError("No candidate-C replicate hit files found")

    pixels = read_csv(pixel_path)
    deposits = read_csv(deposit_path)
    direct = read_csv(direct_path)
    if len(pixels) != EXPECTED_PIXELS:
        raise ValueError(f"Expected {EXPECTED_PIXELS} pixels, found {len(pixels)}")
    if len(deposits) != EXPECTED_DEPOSITS:
        raise ValueError(f"Expected {EXPECTED_DEPOSITS} deposits, found {len(deposits)}")

    pixel_centers = {
        int(row["pixel_id"]): (float(row["y_mm"]), float(row["z_mm"]))
        for row in pixels
    }
    deposit_y = np.asarray([float(row["local_y_mm"]) for row in deposits])
    deposit_z = np.asarray([float(row["local_z_mm"]) for row in deposits])
    deposit_e = np.asarray([float(row["energy_keV"]) for row in deposits])
    input_kev = float(deposit_e.sum())
    if not np.isclose(input_kev, EXPECTED_INPUT_KEV, rtol=0, atol=1e-7):
        raise ValueError(f"Unexpected candidate-C input energy: {input_kev:.10f} keV")

    all_y: list[float] = []
    all_z: list[float] = []
    all_weight_kev: list[float] = []
    sensor_by_pixel_kev: defaultdict[int, float] = defaultdict(float)
    replicate_energy_kev: list[float] = []
    replicate_sensor_kev: list[float] = []

    for hit_path in hit_paths:
        hits = read_csv(hit_path)
        rep_total = 0.0
        rep_sensor = 0.0
        for row in hits:
            surface = row["surface_class"]
            if surface not in {"sensor", "bath"}:
                raise ValueError(f"Unexpected terminal surface class {surface!r}")
            weight_kev = float(row["weighted_energy_eV"]) / 1000.0
            all_y.append(float(row["end_local_y_mm"]))
            all_z.append(float(row["end_local_z_mm"]))
            all_weight_kev.append(weight_kev)
            rep_total += weight_kev
            if surface == "sensor":
                pixel_id = int(row["pixel_id"])
                sensor_by_pixel_kev[pixel_id] += weight_kev
                rep_sensor += weight_kev
        replicate_energy_kev.append(rep_total)
        replicate_sensor_kev.append(rep_sensor)

    n_replicates = len(hit_paths)
    for total in replicate_energy_kev:
        if not np.isclose(total, input_kev, rtol=0, atol=1e-6):
            raise ValueError(f"G4CMP energy closure failed: {total:.9f} vs {input_kev:.9f} keV")

    y = np.asarray(all_y)
    z = np.asarray(all_z)
    weights = np.asarray(all_weight_kev) / n_replicates
    edges = np.linspace(-SI_HALF_WIDTH_MM, SI_HALF_WIDTH_MM, args.bins + 1)
    terminal_grid, z_edges, y_edges = np.histogram2d(
        z, y, bins=(edges, edges), weights=weights
    )
    bin_width_mm = float(edges[1] - edges[0])
    sigma_bins = args.smoothing_mm / bin_width_mm
    if sigma_bins > 0:
        terminal_grid = gaussian_filter(terminal_grid, sigma=sigma_bins, mode="constant")
    terminal_density = terminal_grid / (bin_width_mm**2)

    sensor_mean_kev = {
        pixel_id: value / n_replicates for pixel_id, value in sensor_by_pixel_kev.items()
    }
    sensor_values = np.asarray([sensor_mean_kev.get(pid, 0.0) for pid in sorted(pixel_centers)])
    mean_sensor_kev = float(np.mean(replicate_sensor_kev))
    sensor_eta = mean_sensor_kev / input_kev

    direct_c_rows = [row for row in direct if row["candidate"] == "C"]
    direct_c_kev = sum(float(row["energy_keV"]) for row in direct_c_rows)
    direct_pixel_ids = sorted(int(row["pixel_id"]) for row in direct_c_rows)
    reconstructed_kev = direct_c_kev + mean_sensor_kev

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.titlesize": 15,
        }
    )
    fig, (ax0, ax1) = plt.subplots(
        1,
        2,
        figsize=(14.2, 7.35),
        gridspec_kw={"width_ratios": [1.18, 1.0]},
        constrained_layout=True,
    )

    substrate = Rectangle(
        (-SI_HALF_WIDTH_MM, -SI_HALF_WIDTH_MM),
        2 * SI_HALF_WIDTH_MM,
        2 * SI_HALF_WIDTH_MM,
        facecolor="#dbe8ef",
        edgecolor="#17324d",
        linewidth=2.0,
        zorder=0,
    )
    ax0.add_patch(substrate)
    heat_cmap = plt.colormaps["inferno"].copy()
    # Keep zero/below-scale bins visible as the low end of the energy scale.
    # Transparency here would expose the pale substrate patch and look like
    # unphysical holes in the map.
    heat_cmap.set_under(heat_cmap(0.0))
    im0 = ax0.imshow(
        terminal_density,
        origin="lower",
        extent=[y_edges[0], y_edges[-1], z_edges[0], z_edges[-1]],
        cmap=heat_cmap,
        norm=robust_lognorm(terminal_density),
        interpolation="bilinear",
        zorder=1,
    )

    outline_patches = [
        Rectangle(
            (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
            PIXEL_SIDE_MM,
            PIXEL_SIDE_MM,
        )
        for y0, z0 in pixel_centers.values()
    ]
    outlines = PatchCollection(
        outline_patches,
        facecolor="none",
        edgecolor=(0.80, 0.94, 1.0, 0.50),
        linewidth=0.27,
        zorder=2,
    )
    ax0.add_collection(outlines)

    marker_sizes = 12.0 + 70.0 * np.sqrt(deposit_e / deposit_e.max())
    ax0.scatter(
        deposit_y,
        deposit_z,
        s=marker_sizes,
        c=deposit_e,
        cmap="viridis",
        edgecolors="white",
        linewidths=0.55,
        alpha=0.92,
        zorder=4,
        label="43 Geant4 Si deposits",
    )
    for pixel_id in direct_pixel_ids:
        y0, z0 = pixel_centers[pixel_id]
        ax0.add_patch(
            Rectangle(
                (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
                fill=False,
                edgecolor="#00e5ff",
                linestyle="--",
                linewidth=1.8,
                zorder=5,
            )
        )
        ax0.annotate(
            f"L1 P{pixel_id}\n(projected)",
            xy=(y0, z0),
            xytext=(5, 8),
            textcoords="offset points",
            color="#00e5ff",
            fontsize=8,
            weight="bold",
            zorder=6,
        )

    cb0 = fig.colorbar(im0, ax=ax0, fraction=0.046, pad=0.025)
    cb0.set_label("Mean terminal phonon energy density [keV mm$^{-2}$]")
    ax0.set_title("(a) L0 Si substrate: terminal absorption map")
    ax0.set_xlabel("local y [mm]")
    ax0.set_ylabel("local z [mm]")
    ax0.set_xlim(-18.6, 18.6)
    ax0.set_ylim(-18.6, 18.6)
    ax0.set_aspect("equal")
    ax0.legend(loc="upper left", frameon=True, fontsize=8)

    ax1.add_patch(
        Rectangle(
            (-SI_HALF_WIDTH_MM, -SI_HALF_WIDTH_MM),
            2 * SI_HALF_WIDTH_MM,
            2 * SI_HALF_WIDTH_MM,
            facecolor="#eef3f6",
            edgecolor="#17324d",
            linewidth=2.0,
            zorder=0,
        )
    )
    pixel_cmap = plt.colormaps["magma"].copy()
    pixel_cmap.set_under("#d4dde3")
    pixel_norm = robust_lognorm(sensor_values, low_percentile=1.0)
    pixel_patches = []
    pixel_colors = []
    for pixel_id, (y0, z0) in pixel_centers.items():
        pixel_patches.append(
            Rectangle(
                (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
            )
        )
        pixel_colors.append(sensor_mean_kev.get(pixel_id, 0.0))
    collection = PatchCollection(
        pixel_patches,
        cmap=pixel_cmap,
        norm=pixel_norm,
        edgecolor=(0.13, 0.20, 0.27, 0.80),
        linewidth=0.30,
        zorder=2,
    )
    collection.set_array(np.asarray(pixel_colors))
    ax1.add_collection(collection)
    for pixel_id in direct_pixel_ids:
        y0, z0 = pixel_centers[pixel_id]
        ax1.add_patch(
            Rectangle(
                (y0 - PIXEL_SIDE_MM / 2, z0 - PIXEL_SIDE_MM / 2),
                PIXEL_SIDE_MM,
                PIXEL_SIDE_MM,
                fill=False,
                edgecolor="#00a9c7",
                linestyle="--",
                linewidth=1.8,
                zorder=4,
            )
        )
        ax1.annotate(
            f"L1 P{pixel_id}",
            xy=(y0, z0),
            xytext=(5, 7),
            textcoords="offset points",
            color="#006a80",
            fontsize=8,
            weight="bold",
            zorder=5,
        )

    cb1 = fig.colorbar(collection, ax=ax1, fraction=0.046, pad=0.025)
    cb1.set_label("Mean G4CMP sensor energy per L0 pixel [keV]")
    ax1.set_title("(b) L0 TES pixel response (376 physical pixels)")
    ax1.set_xlabel("local y [mm]")
    ax1.set_ylabel("local z [mm]")
    ax1.set_xlim(-18.6, 18.6)
    ax1.set_ylim(-18.6, 18.6)
    ax1.set_aspect("equal")

    fig.suptitle("SH3 candidate C — data-driven Si phonon / TES energy distribution")
    fig.text(
        0.5,
        -0.005,
        (
            f"G4CMP v10.05 / Geant4 11.4.0; tuned-C interface scenario; "
            f"{n_replicates} independent runs × 8192 weighted phonon packets; time-integrated.  "
            f"Si input = {input_kev:.3f} keV, mean L0 sensor = {mean_sensor_kev:.3f} keV "
            f"(η = {sensor_eta:.4f}), direct L1 TES = {direct_c_kev:.3f} keV, "
            f"sum = {reconstructed_kev:.3f} keV.  Colors are athermal energy, not temperature."
        ),
        ha="center",
        va="bottom",
        fontsize=8.3,
    )

    output_prefix = args.output_prefix.resolve()
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    metadata_path = output_prefix.with_name(output_prefix.name + "_metadata.json")
    fig.savefig(
        png_path,
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": "Matplotlib; plot_candidate_c_heatmap.py"},
    )
    fig.savefig(
        pdf_path,
        bbox_inches="tight",
        facecolor="white",
        metadata={
            "Creator": "Matplotlib; plot_candidate_c_heatmap.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)

    metadata = {
        "schema_version": 1,
        "description": "Candidate-C time-integrated terminal phonon energy and TES-pixel response map; not temperature.",
        "coordinate_plane": "Si local y-z plane; local x is the 0.30 mm thickness axis",
        "inputs": {
            "pixel_map": {"path": str(pixel_path), "sha256": sha256(pixel_path)},
            "si_deposits": {"path": str(deposit_path), "sha256": sha256(deposit_path)},
            "direct_tes": {"path": str(direct_path), "sha256": sha256(direct_path)},
            "g4cmp_hits": [
                {"path": str(path), "sha256": sha256(path)} for path in hit_paths
            ],
        },
        "plot_parameters": {
            "bins_per_axis": args.bins,
            "bin_width_mm": bin_width_mm,
            "gaussian_smoothing_sigma_mm": args.smoothing_mm,
            "replicate_averaging": n_replicates,
        },
        "geometry": {
            "si_width_mm": 36.0,
            "si_thickness_mm": 0.30,
            "pixel_count": len(pixels),
            "pixel_side_mm": PIXEL_SIDE_MM,
        },
        "energy_keV": {
            "si_input": input_kev,
            "replicate_terminal_totals": replicate_energy_kev,
            "replicate_sensor": replicate_sensor_kev,
            "mean_l0_sensor": mean_sensor_kev,
            "mean_l0_sensor_eta": sensor_eta,
            "direct_l1_tes": direct_c_kev,
            "direct_plus_mean_sensor": reconstructed_kev,
        },
        "direct_l1_pixels_projected_on_l0": direct_pixel_ids,
        "outputs": {"png": str(png_path), "pdf": str(pdf_path)},
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"png": str(png_path), "pdf": str(pdf_path), "metadata": str(metadata_path), "sensor_eta": sensor_eta, "reconstructed_keV": reconstructed_kev}, indent=2))


if __name__ == "__main__":
    main()
