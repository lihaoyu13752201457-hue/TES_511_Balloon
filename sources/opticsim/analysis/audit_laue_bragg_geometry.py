from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_baseline.laue_raytrace_py.mosaic_darwin import bragg_angle_rad


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit vector Bragg geometry for the multiring Laue configuration.")
    parser.add_argument("--ring-config", default="data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    parser.add_argument("--focal-mm", type=float, default=8300.0)
    parser.add_argument("--out", default="runs/laue_bragg_geometry_audit")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((ROOT / args.ring_config).open(newline="")))
    audit_rows = []
    for row in rows:
        ring_id = int(row["ring_id"])
        energy = float(row["design_energy_keV"])
        radius = float(row["radius_mm"])
        n_tiles = int(row["n_tiles"])
        d_spacing = float(row["d_spacing_A"])
        theta_b = bragg_angle_rad(energy, d_spacing)
        theta_geom = 0.5 * math.atan2(radius, args.focal_mm)
        for tile_id in range(n_tiles):
            phi = 2.0 * math.pi * tile_id / n_tiles
            pos = (radius * math.cos(phi), radius * math.sin(phi), 0.0)
            out_dir = _unit((-pos[0], -pos[1], args.focal_mm))
            in_dir = (0.0, 0.0, 1.0)
            plane_normal = _unit((out_dir[0] - in_dir[0], out_dir[1] - in_dir[1], out_dir[2] - in_dir[2]))
            bragg_from_plane = math.asin(abs(_dot(in_dir, plane_normal)))
            deflection = math.acos(max(-1.0, min(1.0, _dot(in_dir, out_dir))))
            audit_rows.append(
                {
                    "ring_id": ring_id,
                    "tile_id": tile_id,
                    "phi_rad": phi,
                    "energy_keV": energy,
                    "radius_mm": radius,
                    "theta_B_rad": theta_b,
                    "theta_geom_rad": theta_geom,
                    "bragg_from_plane_rad": bragg_from_plane,
                    "deflection_rad": deflection,
                    "expected_deflection_rad": 2.0 * theta_b,
                    "theta_geom_minus_theta_B_rad": theta_geom - theta_b,
                    "plane_minus_theta_B_rad": bragg_from_plane - theta_b,
                    "deflection_minus_2theta_B_rad": deflection - 2.0 * theta_b,
                    "plane_normal_x": plane_normal[0],
                    "plane_normal_y": plane_normal[1],
                    "plane_normal_z": plane_normal[2],
                }
            )
    with (out / "bragg_vector_audit.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    radii = [float(row["radius_mm"]) for row in rows]
    tile_sizes = [float(row["tile_size_mm"]) for row in rows]
    radial_spacings = [abs(a - b) for a, b in zip(radii, radii[1:])]
    min_radial_clearance = min(radial_spacings) - max(tile_sizes) if radial_spacings else None
    max_tangential_overlap_margin = max(
        float(row["tile_size_mm"]) - 2.0 * math.pi * float(row["radius_mm"]) / int(row["n_tiles"])
        for row in rows
    )
    summary = {
        "ok": True,
        "n_rings": len(rows),
        "n_tiles_checked": len(audit_rows),
        "max_abs_theta_geom_minus_theta_B_rad": max(abs(float(r["theta_geom_minus_theta_B_rad"])) for r in audit_rows),
        "max_abs_plane_minus_theta_B_rad": max(abs(float(r["plane_minus_theta_B_rad"])) for r in audit_rows),
        "max_abs_deflection_minus_2theta_B_rad": max(abs(float(r["deflection_minus_2theta_B_rad"])) for r in audit_rows),
        "min_radial_clearance_mm": min_radial_clearance,
        "max_tangential_overlap_margin_mm": max_tangential_overlap_margin,
    }
    summary["ok"] = (
        summary["max_abs_theta_geom_minus_theta_B_rad"] < 1.0e-6
        and summary["max_abs_plane_minus_theta_B_rad"] < 1.0e-6
        and summary["max_abs_deflection_minus_2theta_B_rad"] < 2.0e-6
        and (min_radial_clearance is None or min_radial_clearance > 0.0)
        and max_tangential_overlap_margin < 0.0
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(_dot(v, v))
    if norm <= 0.0:
        raise ValueError("zero vector")
    return (v[0] / norm, v[1] / norm, v[2] / norm)


if __name__ == "__main__":
    raise SystemExit(main())
