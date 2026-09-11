from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
import matplotlib.pyplot as plt


def read_event_energies(path: Path) -> list[float]:
    energies: list[float] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if float(row["total_tes_edep_keV"]) > 0.0:
                energies.append(float(row["reco_energy_keV"]))
    return energies


def read_pixel_counts(path: Path) -> list[list[int]]:
    counts = [[0 for _ in range(20)] for _ in range(20)]
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["detector_kind"] != "TES_PIXEL":
                continue
            i = int(row["pixel_i"])
            j = int(row["pixel_j"])
            if 0 <= i < 20 and 0 <= j < 20:
                counts[j][i] += 1
    return counts


def plot_spectrum(path: Path, energies: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=140)
    ax.hist(energies, bins=140, range=(0.0, 520.0), color="#2563eb", alpha=0.8)
    ax.axvspan(510.3, 511.8, color="#16a34a", alpha=0.18, label="510.3-511.8 keV")
    ax.set_xlabel("event TES reconstructed/raw energy [keV]")
    ax.set_ylabel("events")
    ax.set_title("Detector event spectrum")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_pixel_map(path: Path, counts: list[list[int]]) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 5.2), dpi=140)
    im = ax.imshow(counts, origin="lower", cmap="viridis")
    ax.set_xlabel("pixel i")
    ax.set_ylabel("pixel j")
    ax.set_title("TES raw hit map")
    fig.colorbar(im, ax=ax, label="hits")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot detector contract hits/event_summary outputs.")
    parser.add_argument("--hits", required=True)
    parser.add_argument("--event-summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plot_spectrum(out / "detector_contract_spectrum.png", read_event_energies(Path(args.event_summary)))
    plot_pixel_map(out / "detector_contract_pixel_map.png", read_pixel_counts(Path(args.hits)))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
