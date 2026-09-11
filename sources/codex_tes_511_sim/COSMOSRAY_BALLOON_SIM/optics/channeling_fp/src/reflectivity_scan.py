"""Scan multilayer reflectivity versus grazing angle for the channeling project."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.materials import fresnel_surface_reflectivity, material_density, optical_constants_from_xraydb
    from src.multilayer import bilayer_stack_from_config, parratt_reflectivity
else:
    from .materials import fresnel_surface_reflectivity, material_density, optical_constants_from_xraydb
    from .multilayer import bilayer_stack_from_config, parratt_reflectivity


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Reflectivity scan for channeling_fp")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/reflectivity_scan", help="Output directory")
    ap.add_argument("--amin-mrad", type=float, default=0.01, help="Minimum grazing angle [mrad]")
    ap.add_argument("--amax-mrad", type=float, default=10.0, help="Maximum grazing angle [mrad]")
    ap.add_argument("--npts", type=int, default=800, help="Number of scan points")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    energy_keV = float(cfg["energy_keV"])
    layers, substrate = bilayer_stack_from_config(cfg, energy_keV)
    wall_material = cfg["multilayer"].get("material_a", "W")
    wall_optics = optical_constants_from_xraydb(wall_material, material_density(wall_material), energy_keV)

    angles_mrad = np.geomspace(float(args.amin_mrad), float(args.amax_mrad), int(args.npts))
    angles_rad = angles_mrad * 1.0e-3
    refl_stack = np.array(
        [parratt_reflectivity(energy_keV, float(alpha), layers, substrate) for alpha in angles_rad],
        dtype=float,
    )
    refl_surface = np.array(
        [fresnel_surface_reflectivity(wall_optics, float(alpha)) for alpha in angles_rad],
        dtype=float,
    )

    peak_idx = int(np.argmax(refl_stack))
    peak_idx_surface = int(np.argmax(refl_surface))
    summary = {
        "energy_keV": energy_keV,
        "peak_reflectivity_stack": float(refl_stack[peak_idx]),
        "peak_angle_mrad_stack": float(angles_mrad[peak_idx]),
        "peak_reflectivity_surface": float(refl_surface[peak_idx_surface]),
        "peak_angle_mrad_surface": float(angles_mrad[peak_idx_surface]),
        "amin_mrad": float(args.amin_mrad),
        "amax_mrad": float(args.amax_mrad),
        "npts": int(args.npts),
    }

    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    ax.plot(angles_mrad, refl_stack, color="#2563eb", linewidth=2.0, label="bilayer Parratt")
    ax.plot(angles_mrad, refl_surface, color="#dc2626", linewidth=2.0, label=f"{wall_material} surface Fresnel")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Grazing angle [mrad]")
    ax.set_ylabel("Reflectivity")
    ax.set_title(f"W/Si multilayer reflectivity at {energy_keV:.1f} keV")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(outdir / "reflectivity_vs_grazing_angle.png", dpi=180)
    plt.close(fig)

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    np.savetxt(
        outdir / "reflectivity_scan.csv",
        np.column_stack([angles_mrad, refl_stack, refl_surface]),
        delimiter=",",
        header="grazing_angle_mrad,reflectivity_stack,reflectivity_surface",
        comments="",
    )

    print("[OK] wrote", outdir / "reflectivity_vs_grazing_angle.png")
    print("[OK] wrote", outdir / "summary.json")
    print("[OK] wrote", outdir / "reflectivity_scan.csv")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
