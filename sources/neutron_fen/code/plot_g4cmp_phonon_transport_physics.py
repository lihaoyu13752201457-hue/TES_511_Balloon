#!/usr/bin/env python3
"""Plot the Si phonon transport length scales used internally by G4CMP."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# G4CMP g4cmp-V10-05-00 Si CrystalMap/config.txt.
B_ISOTOPE_S3 = 2.43e-42
A_ANHARMONIC_S4 = 7.41e-56
PLANCK_EV_S = 4.135667696e-15
V_REPRESENTATIVE_M_S = 6000.0
V_LONGITUDINAL_M_S = 9000.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rates_and_lengths(energy_mev: np.ndarray):
    frequency_hz = energy_mev * 1e-3 / PLANCK_EV_S
    isotope_rate_hz = B_ISOTOPE_S3 * frequency_hz**4
    anharmonic_rate_hz = A_ANHARMONIC_S4 * frequency_hz**5
    isotope_length_mm = V_REPRESENTATIVE_M_S / isotope_rate_hz * 1e3
    anharmonic_length_mm = V_LONGITUDINAL_M_S / anharmonic_rate_hz * 1e3
    return frequency_hz, isotope_rate_hz, anharmonic_rate_hz, isotope_length_mm, anharmonic_length_mm


def main() -> None:
    config_path = (
        ROOT
        / "install/G4CMP-g4cmp-V10-05-00-g4.11.4.0/share/G4CMP/CrystalMaps/Si/config.txt"
    )
    output_prefix = ROOT / "outputs/figures/sh3_g4cmp_phonon_transport_physics"
    energy_mev = np.geomspace(0.1, 70.0, 900)
    _, _, _, isotope_mm, anharmonic_mm = rates_and_lengths(energy_mev)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.titlesize": 18,
            "axes.labelsize": 14,
        }
    )
    fig, ax = plt.subplots(figsize=(13.6, 7.65))
    ax.loglog(
        energy_mev,
        isotope_mm,
        color="#006a86",
        linewidth=3.0,
        label=r"isotope scattering: $\Gamma_{iso}=B\nu^4$",
    )
    ax.loglog(
        energy_mev,
        anharmonic_mm,
        color="#c15b2a",
        linewidth=3.0,
        label=r"L-mode anharmonic decay: $\Gamma_{anh}=A\nu^5$",
    )
    ax.axhline(0.3, color="#555555", linewidth=1.5, linestyle="--", label="Si thickness: 0.3 mm")
    ax.axhline(36.0, color="#777777", linewidth=1.5, linestyle=":", label="Si lateral size: 36 mm")

    marker_summary = {}
    for energy, label in [(62.0, "62 meV"), (30.0, "30 meV"), (2.7, "2.7 meV")]:
        frequency, iso_rate, anh_rate, iso_length, anh_length = rates_and_lengths(
            np.asarray([energy])
        )
        ax.scatter([energy], iso_length, s=62, color="#006a86", edgecolor="white", linewidth=0.8, zorder=5)
        ax.scatter([energy], anh_length, s=62, color="#c15b2a", edgecolor="white", linewidth=0.8, zorder=5)
        ax.axvline(energy, color="#aeb6bb", linewidth=0.8, alpha=0.7)
        ax.text(
            energy,
            2.1e4,
            label,
            rotation=90,
            va="top",
            ha="right",
            color="#4c555b",
            fontsize=11,
        )
        marker_summary[label] = {
            "frequency_THz": float(frequency[0] / 1e12),
            "isotope_rate_Hz": float(iso_rate[0]),
            "isotope_mean_free_path_mm_at_6000_m_s": float(iso_length[0]),
            "longitudinal_anharmonic_rate_Hz": float(anh_rate[0]),
            "longitudinal_anharmonic_mean_free_path_mm_at_9000_m_s": float(anh_length[0]),
        }

    ax.text(
        12.0,
        2.5e-4,
        "high-frequency start:\nstrong scattering + rapid downconversion",
        color="#343a3f",
        fontsize=12,
    )
    ax.text(
        0.16,
        1.5e3,
        "after energy falls:\nmean free path reaches detector scale → ballistic",
        color="#343a3f",
        fontsize=12,
    )
    ax.set_xlim(0.1, 70.0)
    ax.set_ylim(1e-5, 5e4)
    ax.set_xlabel("phonon energy [meV]")
    ax.set_ylabel("representative mean free path [mm]")
    ax.set_title("Why G4CMP phonons evolve from quasi-diffuse to ballistic transport")
    ax.grid(which="both", color="#d8dde0", linewidth=0.65, alpha=0.8)
    ax.legend(loc="lower left", frameon=False, fontsize=11.2)
    fig.text(
        0.5,
        0.018,
        (
            "G4CMP Si CrystalMap: B = 2.43×10⁻⁴² s³, A = 7.41×10⁻⁵⁶ s⁴. "
            "Lengths use representative 6 km/s and longitudinal 9 km/s velocities; exact v_g depends on mode and crystal direction."
        ),
        ha="center",
        fontsize=10.4,
        color="#4f5960",
    )
    fig.tight_layout(rect=(0.02, 0.055, 0.99, 0.98))

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=220, facecolor="white")
    fig.savefig(pdf_path, facecolor="white")
    plt.close(fig)

    metadata = {
        "schema_version": 1,
        "model": {
            "isotope_scattering_rate": "B*nu^4",
            "longitudinal_anharmonic_decay_rate": "A*nu^5",
            "B_s3": B_ISOTOPE_S3,
            "A_s4": A_ANHARMONIC_S4,
            "representative_velocity_m_s": V_REPRESENTATIVE_M_S,
            "longitudinal_velocity_m_s": V_LONGITUDINAL_M_S,
        },
        "input": {"path": str(config_path), "sha256": sha256(config_path)},
        "scenario_markers": marker_summary,
        "outputs": {"png": str(png_path), "pdf": str(pdf_path)},
        "limitations": [
            "Mean free path is rate-to-length conversion with representative velocities; G4CMP uses mode- and direction-dependent group velocity.",
            "Anharmonic bulk downconversion is applied to longitudinal phonons in this G4CMP implementation.",
        ],
    }
    metadata_path = output_prefix.with_name(output_prefix.name + "_metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(marker_summary, indent=2, sort_keys=True))
    print(png_path)


if __name__ == "__main__":
    main()
