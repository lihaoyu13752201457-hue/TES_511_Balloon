from __future__ import annotations

import argparse
import csv
from pathlib import Path

from external_baseline.laue_raytrace_py.mosaic_darwin import (
    bragg_angle_rad,
    darwin_mosaic_probabilities,
    d_spacing_A,
    optimal_mosaic_thickness_mm,
)


TABLE_FIELDS = [
    "E_keV",
    "theta_B_rad",
    "delta_theta_rad",
    "material",
    "h",
    "k",
    "l",
    "mosaic_fwhm_arcmin",
    "thickness_mm",
    "p_diff",
    "p_abs",
    "p_trans",
    "source",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Zachariasen/Darwin mosaic Laue efficiency table.")
    parser.add_argument("--ring-config", required=True)
    parser.add_argument("--out-table", required=True)
    parser.add_argument("--out-ring-config")
    parser.add_argument("--mosaic-arcsec", type=float, default=30.0)
    parser.add_argument("--crystallite-um", type=float, default=5.0)
    parser.add_argument("--delta-multiple", type=float, default=4.0)
    parser.add_argument("--n-delta", type=int, default=81)
    parser.add_argument("--tile-size-mm", type=float)
    parser.add_argument("--optimize-thickness", action="store_true")
    args = parser.parse_args()

    if args.n_delta < 3 or args.n_delta % 2 == 0:
        raise SystemExit("--n-delta must be an odd integer >= 3")

    rows = _read_rows(Path(args.ring_config))
    if args.tile_size_mm is not None:
        rows = [{**row, "tile_size_mm": f"{args.tile_size_mm:.9g}"} for row in rows]
    if args.optimize_thickness:
        rows = [_with_optimized_thickness(row, args.mosaic_arcsec, args.crystallite_um) for row in rows]

    if args.out_ring_config:
        _write_ring_config(Path(args.out_ring_config), rows)

    delta_max = args.delta_multiple * args.mosaic_arcsec / 3600.0 * 3.141592653589793 / 180.0
    delta_values = [
        -delta_max + 2.0 * delta_max * i / (args.n_delta - 1)
        for i in range(args.n_delta)
    ]
    _write_table(Path(args.out_table), rows, delta_values, args.mosaic_arcsec, args.crystallite_um)
    return 0


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _with_optimized_thickness(row: dict[str, str], mosaic_arcsec: float, crystallite_um: float) -> dict[str, str]:
    out = dict(row)
    material = out["material"]
    h, k, l = int(out["h"]), int(out["k"]), int(out["l"])
    energy = float(out["design_energy_keV"])
    out["d_spacing_A"] = f"{d_spacing_A(material, h, k, l):.9f}"
    out["thickness_mm"] = f"{optimal_mosaic_thickness_mm(energy_keV=energy, material=material, h=h, k=k, l=l, mosaic_fwhm_arcsec=mosaic_arcsec, crystallite_thickness_um=crystallite_um):.6f}"
    return out


def _write_ring_config(path: Path, rows: list[dict[str, str]]) -> None:
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
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def _write_table(
    path: Path,
    ring_rows: list[dict[str, str]],
    delta_values: list[float],
    mosaic_arcsec: float,
    crystallite_um: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TABLE_FIELDS)
        writer.writeheader()
        for row in ring_rows:
            material = row["material"]
            h, k, l = int(row["h"]), int(row["k"]), int(row["l"])
            energy = float(row["design_energy_keV"])
            thickness_mm = float(row["thickness_mm"])
            theta_b = bragg_angle_rad(energy, float(row["d_spacing_A"]))
            for delta in delta_values:
                probs = darwin_mosaic_probabilities(
                    energy_keV=energy,
                    material=material,
                    h=h,
                    k=k,
                    l=l,
                    mosaic_fwhm_arcsec=mosaic_arcsec,
                    thickness_mm=thickness_mm,
                    crystallite_thickness_um=crystallite_um,
                    delta_theta_rad=delta,
                )
                writer.writerow(
                    {
                        "E_keV": f"{energy:.9g}",
                        "theta_B_rad": f"{theta_b:.12g}",
                        "delta_theta_rad": f"{delta:.12g}",
                        "material": material,
                        "h": h,
                        "k": k,
                        "l": l,
                        "mosaic_fwhm_arcmin": f"{mosaic_arcsec / 60.0:.9g}",
                        "thickness_mm": f"{thickness_mm:.9g}",
                        "p_diff": f"{probs.p_diff:.12g}",
                        "p_abs": f"{probs.p_abs:.12g}",
                        "p_trans": f"{probs.p_trans:.12g}",
                        "source": probs.source,
                    }
                )


if __name__ == "__main__":
    raise SystemExit(main())
