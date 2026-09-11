#!/usr/bin/env python3
"""Generate the f=10 m Ge(111) 511 keV single-ring Laue configs."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


HC_KEV_A = 12.398419843320026
ENERGY_KEV = 511.0
D_SPACING_A = 3.266590088
FOCAL_MM = 10000.0
Z_OFFSET_MM = 0.0
THICKNESS_MM = 10.218801
GE_DENSITY_G_CM3 = 5.3234
DIFFRACTED_FRACTION_REFERENCE = 0.25184

VARIANTS = {
    "a1": {"n_tiles": 25, "tile_size_mm": 18.0, "config_suffix": ""},
    "a2": {"n_tiles": 30, "tile_size_mm": 15.0, "config_suffix": "_a2"},
}


def bragg_radius_mm() -> tuple[float, float]:
    wavelength_a = HC_KEV_A / ENERGY_KEV
    theta_b = math.asin(wavelength_a / (2.0 * D_SPACING_A))
    radius = (FOCAL_MM - Z_OFFSET_MM) * math.tan(2.0 * theta_b)
    return theta_b, radius


def crystal_mass_g(n_tiles: int, tile_size_mm: float) -> float:
    tile_size_cm = tile_size_mm / 10.0
    thickness_cm = THICKNESS_MM / 10.0
    volume_cm3 = n_tiles * tile_size_cm * tile_size_cm * thickness_cm
    return volume_cm3 * GE_DENSITY_G_CM3


def write_config(path: Path, n_tiles: int, tile_size_mm: float, radius_mm: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ring_id",
                "design_energy_keV",
                "radius_mm",
                "n_tiles",
                "material",
                "h",
                "k",
                "l",
                "d_spacing_A",
                "tile_size_mm",
                "thickness_mm",
                "z_offset_mm",
            ]
        )
        writer.writerow(
            [
                0,
                f"{ENERGY_KEV:.1f}",
                f"{radius_mm:.6f}",
                n_tiles,
                "Ge",
                1,
                1,
                1,
                f"{D_SPACING_A:.9f}",
                f"{tile_size_mm:.6f}",
                f"{THICKNESS_MM:.6f}",
                f"{Z_OFFSET_MM:.6f}",
            ]
        )


def write_map(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ring_id", "design_energy_keV", "curve_csv", "source", "status"])
        writer.writerow([0, f"{ENERGY_KEV:.1f}", "ge111_511keV_rocking_curve.csv", "CRYSTAL-diff_pat", "covered"])


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data" / "laue"
    theta_b_rad, radius_mm = bragg_radius_mm()

    map_path = data_dir / "ge111_balloon511_f10m_511keV_xop_map.csv"
    map_a2_path = data_dir / "ge111_balloon511_f10m_511keV_xop_map_a2.csv"
    write_map(map_path)
    write_map(map_a2_path)

    summary = {
        "model": "balloon511_f10m_ge111_511line",
        "energy_keV": ENERGY_KEV,
        "focal_length_mm": FOCAL_MM,
        "theta_b_rad": theta_b_rad,
        "radius_mm": radius_mm,
        "d_spacing_A": D_SPACING_A,
        "thickness_mm": THICKNESS_MM,
        "z_offset_mm": Z_OFFSET_MM,
        "mosaic_fwhm_arcsec": 30.0,
        "natural_passband_fwhm_keV": [500.993937, 521.006063],
        "rocking_curve_map_csv": str(map_path.relative_to(repo_root)),
        "variants": {},
    }

    for variant, spec in VARIANTS.items():
        config_path = data_dir / f"ge111_balloon511_f10m_511keV_line_config{spec['config_suffix']}.csv"
        write_config(config_path, spec["n_tiles"], spec["tile_size_mm"], radius_mm)
        tile_size_cm = spec["tile_size_mm"] / 10.0
        geometric_area_cm2 = spec["n_tiles"] * tile_size_cm * tile_size_cm
        pitch_mm = 2.0 * math.pi * radius_mm / spec["n_tiles"]
        summary["variants"][variant] = {
            "config_csv": str(config_path.relative_to(repo_root)),
            "n_tiles": spec["n_tiles"],
            "tile_size_mm": spec["tile_size_mm"],
            "pitch_mm": pitch_mm,
            "gap_mm": pitch_mm - spec["tile_size_mm"],
            "geometric_area_cm2": geometric_area_cm2,
            "expected_aeff_cm2": geometric_area_cm2 * DIFFRACTED_FRACTION_REFERENCE,
            "ge_mass_g": crystal_mass_g(spec["n_tiles"], spec["tile_size_mm"]),
        }

    summary_path = data_dir / "ge111_balloon511_f10m_511keV_design_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(f"wrote {map_path.relative_to(repo_root)}")
    print(f"wrote {map_a2_path.relative_to(repo_root)}")
    for variant in VARIANTS:
        print(f"wrote {summary['variants'][variant]['config_csv']}")
    print(f"wrote {summary_path.relative_to(repo_root)}")
    print(f"radius_mm={radius_mm:.6f} theta_b_rad={theta_b_rad:.10f}")


if __name__ == "__main__":
    main()
