#!/usr/bin/env python3
"""Freeze a fixed-thickness Ge(111) angle-energy validation matrix.

The retained XOP/CRYSTAL curves were generated at five energies with the
energy-specific thicknesses used by the earlier multiring benchmark.  M08 needs
one physical tile thickness.  This script maps each raw XOP curve to the f10m
tile thickness by inverting and re-evaluating the Darwin-Hamilton slab form

  R = 0.5 (1 - exp(-2 sigma L)) exp(-mu L),
  A = 1 - exp(-mu L),
  T = 1 - R - A.

No curve width or peak position is fitted or shifted.  The raw files and their
hashes remain in the package, and every derived row carries the source path and
the thickness-rescale method.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "xop_raw"
OUT_DIR = ROOT / "data" / "xop_fixed_10p218801mm"
CONFIG_DIR = ROOT / "data" / "ring_configs"

ENERGIES_KEV = (480, 500, 511, 530, 550)
RAW_THICKNESS_MM = {
    480: 9.452263,
    500: 9.947306,
    511: 10.218801,
    530: 10.686285,
    550: 11.176250,
}
TARGET_THICKNESS_MM = 10.218801
D_SPACING_A = 3.266590088
FOCAL_LENGTH_MM = 10000.0
TILE_SIZE_MM = 18.0
HC_KEV_A = 12.398419843320026


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bragg_angle_rad(energy_keV: float) -> float:
    return math.asin(HC_KEV_A / energy_keV / (2.0 * D_SPACING_A))


def rescale_curve(energy_keV: int) -> dict[str, object]:
    source = RAW_DIR / f"ge111_{energy_keV}keV_rocking_curve.csv"
    target = OUT_DIR / source.name
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"empty XOP curve: {source}")

    output_rows: list[dict[str, object]] = []
    max_closure = 0.0
    for row in rows:
        reflectivity = float(row["reflectivity"])
        mu_cm_inv = float(row["absorption_mu_cm_inv"])
        source_path_cm = float(row["path_length_cm"])
        target_path_cm = source_path_cm * TARGET_THICKNESS_MM / RAW_THICKNESS_MM[energy_keV]
        source_survival = math.exp(-mu_cm_inv * source_path_cm)
        if source_survival <= 0.0:
            sigma_cm_inv = 0.0
        else:
            argument = min(1.0 - 1.0e-15, max(0.0, 2.0 * reflectivity / source_survival))
            sigma_cm_inv = -0.5 * math.log1p(-argument) / source_path_cm
        target_survival = math.exp(-mu_cm_inv * target_path_cm)
        target_reflectivity = 0.5 * (1.0 - math.exp(-2.0 * sigma_cm_inv * target_path_cm)) * target_survival
        target_absorption = 1.0 - target_survival
        target_transmittivity = target_survival - target_reflectivity
        closure = target_reflectivity + target_transmittivity + target_absorption
        max_closure = max(max_closure, abs(closure - 1.0))
        output_rows.append(
            {
                "delta_theta_rad": row["delta_theta_rad"],
                "reflectivity": f"{target_reflectivity:.16g}",
                "transmittivity": f"{target_transmittivity:.16g}",
                "absorption": f"{target_absorption:.16g}",
                "source_tool": "XOP/CRYSTAL-diff_pat-derived",
                "source_version": row["source_version"],
                "scan_arcsec": row["scan_arcsec"],
                "absorption_mu_cm_inv": row["absorption_mu_cm_inv"],
                "path_length_cm": f"{target_path_cm:.16g}",
                "source_thickness_mm": f"{RAW_THICKNESS_MM[energy_keV]:.9f}",
                "target_thickness_mm": f"{TARGET_THICKNESS_MM:.9f}",
                "darwin_sigma_cm_inv": f"{sigma_cm_inv:.16g}",
                "thickness_rescale_method": "invert_and_reapply_darwin_hamilton_slab",
                "raw_curve": source.name,
            }
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    peak = max(output_rows, key=lambda item: float(item["reflectivity"]))
    return {
        "energy_keV": energy_keV,
        "raw_curve": str(source.relative_to(ROOT)),
        "raw_sha256": sha256(source),
        "raw_thickness_mm": RAW_THICKNESS_MM[energy_keV],
        "target_curve": str(target.relative_to(ROOT)),
        "target_sha256": sha256(target),
        "target_thickness_mm": TARGET_THICKNESS_MM,
        "rows": len(output_rows),
        "peak_reflectivity": float(peak["reflectivity"]),
        "peak_scan_arcsec": float(peak["scan_arcsec"]),
        "max_rta_closure_error": max_closure,
    }


def write_ring_config(energy_keV: int) -> Path:
    theta_b = bragg_angle_rad(float(energy_keV))
    radius_mm = FOCAL_LENGTH_MM * math.tan(2.0 * theta_b)
    path = CONFIG_DIR / f"ge111_f10m_{energy_keV}keV_single_tile.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "ring_id": 0,
                "design_energy_keV": energy_keV,
                "radius_mm": f"{radius_mm:.9f}",
                "n_tiles": 1,
                "material": "Ge",
                "h": 1,
                "k": 1,
                "l": 1,
                "d_spacing_A": f"{D_SPACING_A:.9f}",
                "tile_size_mm": f"{TILE_SIZE_MM:.9f}",
                "thickness_mm": f"{TARGET_THICKNESS_MM:.9f}",
                "z_offset_mm": "0.000000000",
            }
        )
    return path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    curves = []
    configs = []
    for energy in ENERGIES_KEV:
        curves.append(rescale_curve(energy))
        config = write_ring_config(energy)
        configs.append(
            {
                "energy_keV": energy,
                "path": str(config.relative_to(ROOT)),
                "sha256": sha256(config),
                "bragg_angle_rad": bragg_angle_rad(float(energy)),
                "radius_mm": FOCAL_LENGTH_MM * math.tan(2.0 * bragg_angle_rad(float(energy))),
            }
        )

    summary = {
        "ok": all(item["max_rta_closure_error"] <= 1.0e-12 for item in curves),
        "energies_keV": list(ENERGIES_KEV),
        "focal_length_mm": FOCAL_LENGTH_MM,
        "tile_size_mm": TILE_SIZE_MM,
        "target_thickness_mm": TARGET_THICKNESS_MM,
        "d_spacing_A": D_SPACING_A,
        "curve_method": "XOP/CRYSTAL raw curve, fixed-thickness Darwin-Hamilton slab rescale",
        "curves": curves,
        "ring_configs": configs,
    }
    path = ROOT / "data" / "input_manifest.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "manifest": str(path), "curves": len(curves)}, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
