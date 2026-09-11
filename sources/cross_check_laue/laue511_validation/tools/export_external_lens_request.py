#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.constants import DEFAULT_CRYSTALLITE_THICKNESS_UM, DEFAULT_FOCAL_LENGTH_MM, DEFAULT_MOSAIC_FWHM_ARCSEC
from laue511.geometry import direction_to_point, ideal_plane_normal
from laue511.rings import load_ring_config

DEFAULT_HEART_COMMIT = "d54196aaa787eaefef6df7c66255803f50ea8517"
TILE_FIELDS = [
    "ring_id",
    "tile_id",
    "design_energy_keV",
    "center_x_mm",
    "center_y_mm",
    "center_z_mm",
    "focal_x_mm",
    "focal_y_mm",
    "focal_z_mm",
    "incoming_ux",
    "incoming_uy",
    "incoming_uz",
    "expected_diffracted_ux",
    "expected_diffracted_uy",
    "expected_diffracted_uz",
    "ideal_plane_normal_x",
    "ideal_plane_normal_y",
    "ideal_plane_normal_z",
    "radial_axis_x",
    "radial_axis_y",
    "radial_axis_z",
    "tangential_axis_x",
    "tangential_axis_y",
    "tangential_axis_z",
    "slab_normal_x",
    "slab_normal_y",
    "slab_normal_z",
    "tile_size_mm",
    "thickness_mm",
    "material",
    "h",
    "k",
    "l",
    "d_spacing_A",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/reference_outputs"))
    parser.add_argument("--focal-length-mm", type=float, default=DEFAULT_FOCAL_LENGTH_MM)
    parser.add_argument("--heart-commit", default=DEFAULT_HEART_COMMIT)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    request = build_request(Path(args.config), args.focal_length_mm)
    heart_request = build_heart_adapter_request(request, args.heart_commit)
    request_path = out_dir / "external_lens_oracle_request.json"
    heart_path = out_dir / "heart_lens_adapter_request.json"
    rings_path = out_dir / "external_lens_oracle_rings.csv"
    tiles_path = out_dir / "external_lens_oracle_tiles.csv"
    example_path = out_dir / "external_lens_observables_schema_example.csv"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    heart_path.write_text(json.dumps(heart_request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_rings_csv(rings_path, request["rings"])
    _write_tiles_csv(tiles_path, build_tile_rows(request["rings"], args.focal_length_mm))
    _write_observables_example_csv(example_path, request["comparison_targets"])
    print(
        json.dumps(
            {
                "request_json": str(request_path),
                "heart_adapter_request_json": str(heart_path),
                "rings_csv": str(rings_path),
                "tiles_csv": str(tiles_path),
                "observables_example_csv": str(example_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_request(config_path: Path, focal_length_mm: float) -> dict[str, object]:
    rings = load_ring_config(config_path)
    full_lens = _load_json(ROOT / "reports/full_lens_observables/metrics.json")
    python_ref = _load_json(ROOT / "reports/python_full_lens_reference/metrics.json")
    return {
        "purpose": "external_full_lens_oracle_request",
        "status": "input_pack_for_LLL_HEART_or_equivalent_external_Laue_lens_run",
        "coordinate_convention": {
            "incident_direction": "+z",
            "lens_entry_z_mm": "approximately -thickness_mm/2 per tile in current opticsim output",
            "focal_plane_z_mm": focal_length_mm,
            "source": "parallel on-axis 480-550 keV photons, one design energy per ring",
        },
        "physics": {
            "material": "Ge",
            "hkl": [1, 1, 1],
            "mosaic_fwhm_arcsec": DEFAULT_MOSAIC_FWHM_ARCSEC,
            "crystallite_thickness_um": DEFAULT_CRYSTALLITE_THICKNESS_UM,
            "crystal_shape": "flat mosaic tile",
        },
        "requested_observables_schema": "EXTERNAL_LENS_OBSERVABLES_SCHEMA.md",
        "requested_hit_table_schema": "EXTERNAL_LENS_HITS_SCHEMA.md",
        "requested_tile_table": "external_lens_oracle_tiles.csv",
        "requested_lens_observables": [
            {"scope": "lens", "metric": "diffracted_area_cm2", "unit": "cm2"},
            {"scope": "lens", "metric": "spot_d90_cm", "unit": "cm"},
        ],
        "comparison_targets": {
            "current_opticsim_observed_diffracted_area_cm2": full_lens["observed_diffracted_area_cm2"],
            "current_opticsim_spot_d90_cm": full_lens["spot_d90_cm"],
            "python_reference_diffracted_area_cm2": python_ref["diffracted_area_reference_cm2"],
            "geometric_area_cm2": python_ref["geometric_area_cm2"],
        },
        "rings": [
            {
                "ring_id": ring.ring_id,
                "design_energy_keV": ring.design_energy_keV,
                "radius_mm": ring.radius_mm,
                "n_tiles": ring.n_tiles,
                "tile_size_mm": ring.tile_size_mm,
                "thickness_mm": ring.thickness_mm,
                "material": ring.material,
                "h": ring.h,
                "k": ring.k,
                "l": ring.l,
                "d_spacing_A": ring.d_spacing_A,
            }
            for ring in rings
        ],
    }


def build_heart_adapter_request(base_request: dict[str, object], heart_commit: str) -> dict[str, object]:
    return {
        "purpose": "heart_full_lens_adapter_request",
        "source_request": "external_lens_oracle_request.json",
        "heart": {
            "repository": "https://gitlab.com/heart-ray-tracing/HEART",
            "documentation": "https://heart-ray-tracing.gitlab.io/HEART/",
            "head_commit_checked": heart_commit,
            "checked_on": "2026-05-28",
            "notes": [
                "HEART uses mm for geometry and keV for photon energies.",
                "HEART HDF5 output stores detector images and detector pixel axes, not final per-photon detector hit coordinates.",
                "Use tools/import_heart_detector_image.py for HEART HDF5 detector-image exports.",
                "Use external_lens_oracle_tiles.csv as the per-tile geometry and crystallographic orientation handoff.",
                "A full lens can be adapted as a loop over flat tiles/rings only if the tile model maps each ideal_plane_normal_* row to the Ge(111) lattice-plane normal.",
            ],
        },
        "coordinate_convention": base_request["coordinate_convention"],
        "physics": base_request["physics"],
        "comparison_targets": base_request["comparison_targets"],
        "rings": base_request["rings"],
        "requested_tile_table": base_request["requested_tile_table"],
        "adapter_strategy": {
            "source": "parallel on-axis rays, +z direction, one ring design energy per ring unless the external oracle supports the whole 480-550 keV ring set in one run",
            "crystal_model": "flat Ge(111) mosaic tile, tile_size_mm by tile_size_mm, thickness_mm from each ring; use the tile table's ideal_plane_normal_* as the target diffracting-plane normal",
            "detector": "plane normal to +z at focal_plane_z_mm; export detector-plane coordinates relative to the optical axis",
            "full_lens_combination": "accumulate diffracted detector hits across all rings/tiles before computing lens-level observables",
            "comparability_boundary": "if HEART or another external tool cannot independently orient the diffracting lattice plane according to ideal_plane_normal_*, the run is a geometry smoke test rather than a current-lens oracle",
        },
        "requested_hit_table_schema": "EXTERNAL_LENS_HITS_SCHEMA.md",
        "requested_heart_hdf5_datasets": {
            "detector_image": "Results/detector_image",
            "detector_l_pos_mm": "Detector/detector_L_pos",
            "detector_w_pos_mm": "Detector/detector_W_pos",
            "number_of_photons": "Diagnostics/Number_of_Photons",
            "heart_version": "Version",
        },
        "requested_hit_columns": [
            {"name": "x_mm", "unit": "mm", "required": True},
            {"name": "y_mm", "unit": "mm", "required": True},
            {"name": "weight", "unit": "dimensionless", "required": False},
            {"name": "event_id", "unit": "index", "required": False},
            {"name": "ring_id", "unit": "index", "required": False},
            {"name": "tile_id", "unit": "index", "required": False},
            {"name": "energy_keV", "unit": "keV", "required": False},
        ],
        "import_command": (
            "python3 tools/import_heart_detector_image.py --input path/to/heart_output.h5 "
            "--incident-weight <total incident ray weight if not stored in HDF5>"
        ),
    }


def build_tile_rows(rings: list[dict[str, object]], focal_length_mm: float) -> list[dict[str, object]]:
    incoming = (0.0, 0.0, 1.0)
    focal_point = (0.0, 0.0, float(focal_length_mm))
    rows: list[dict[str, object]] = []
    for ring in rings:
        ring_id = int(ring["ring_id"])
        n_tiles = int(ring["n_tiles"])
        radius_mm = float(ring["radius_mm"])
        center_z_mm = -0.5 * float(ring["thickness_mm"])
        for tile_id in range(n_tiles):
            phi = 2.0 * math.pi * tile_id / n_tiles
            cos_phi = math.cos(phi)
            sin_phi = math.sin(phi)
            center = (radius_mm * cos_phi, radius_mm * sin_phi, center_z_mm)
            outgoing = direction_to_point(center, focal_point)
            plane_normal = ideal_plane_normal(incoming, outgoing)
            rows.append(
                {
                    "ring_id": ring_id,
                    "tile_id": tile_id,
                    "design_energy_keV": ring["design_energy_keV"],
                    "center_x_mm": center[0],
                    "center_y_mm": center[1],
                    "center_z_mm": center[2],
                    "focal_x_mm": focal_point[0],
                    "focal_y_mm": focal_point[1],
                    "focal_z_mm": focal_point[2],
                    "incoming_ux": incoming[0],
                    "incoming_uy": incoming[1],
                    "incoming_uz": incoming[2],
                    "expected_diffracted_ux": outgoing[0],
                    "expected_diffracted_uy": outgoing[1],
                    "expected_diffracted_uz": outgoing[2],
                    "ideal_plane_normal_x": plane_normal[0],
                    "ideal_plane_normal_y": plane_normal[1],
                    "ideal_plane_normal_z": plane_normal[2],
                    "radial_axis_x": cos_phi,
                    "radial_axis_y": sin_phi,
                    "radial_axis_z": 0.0,
                    "tangential_axis_x": -sin_phi,
                    "tangential_axis_y": cos_phi,
                    "tangential_axis_z": 0.0,
                    "slab_normal_x": 0.0,
                    "slab_normal_y": 0.0,
                    "slab_normal_z": 1.0,
                    "tile_size_mm": ring["tile_size_mm"],
                    "thickness_mm": ring["thickness_mm"],
                    "material": ring["material"],
                    "h": ring["h"],
                    "k": ring["k"],
                    "l": ring["l"],
                    "d_spacing_A": ring["d_spacing_A"],
                }
            )
    return rows


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_rings_csv(path: Path, rings: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rings[0]))
        writer.writeheader()
        writer.writerows(rings)


def _write_tiles_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TILE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_observables_example_csv(path: Path, targets: dict[str, object]) -> None:
    rows = [
        {
            "scope": "lens",
            "metric": "diffracted_area_cm2",
            "value": targets["current_opticsim_observed_diffracted_area_cm2"],
            "unit": "cm2",
            "source_tool": "current-opticsim-reference-example",
            "source_version": "not-external-oracle",
        },
        {
            "scope": "lens",
            "metric": "spot_d90_cm",
            "value": targets["current_opticsim_spot_d90_cm"],
            "unit": "cm",
            "source_tool": "current-opticsim-reference-example",
            "source_version": "not-external-oracle",
        },
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
