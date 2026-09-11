#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tile-table",
        default=str(ROOT / "benchmarks/reference_outputs/external_lens_oracle_tiles.csv"),
    )
    parser.add_argument("--out", required=True, help="Combined HEART-compatible HDF5 output path.")
    parser.add_argument("--summary", required=True, help="JSON summary path.")
    parser.add_argument("--ring-id", type=int)
    parser.add_argument("--tile-id", type=int)
    parser.add_argument("--max-tiles", type=int)
    parser.add_argument("--photons-per-tile", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=511)
    parser.add_argument("--nproc", type=int, default=1)
    parser.add_argument("--detector-half-width-mm", type=float, default=10.0)
    parser.add_argument("--detector-pixel-mm", type=float, default=0.05)
    parser.add_argument("--source-offset-mm", type=float, default=50.0)
    parser.add_argument("--mosaic-fwhm-arcsec", type=float, default=30.0)
    parser.add_argument("--mosaic-func", choices=["G", "L"], default="G")
    parser.add_argument("--planar-mosaic-pdf", action="store_true")
    parser.add_argument("--rocking-curve-fwhm-urad", type=float, default=1.0)
    parser.add_argument(
        "--detector-hit-model",
        choices=["heart", "guan_direction_perturbation"],
        default="heart",
        help="Use HEART detector hits, or keep HEART detector counts and bin hits with the current Geant4/Guan direction perturbation model.",
    )
    parser.add_argument(
        "--source-jitter-mm",
        type=float,
        default=0.3,
        help="Uniform source-target jitter width used by guan_direction_perturbation.",
    )
    args = parser.parse_args()

    rows = _select_rows(_read_csv(Path(args.tile_table)), args.ring_id, args.tile_id, args.max_tiles)
    if not rows:
        raise SystemExit("no tile rows selected")

    output = run_oracle(rows, args)
    _write_combined_hdf5(Path(args.out), output)
    Path(args.summary).write_text(json.dumps(output["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


def run_oracle(rows: list[dict[str, str]], args: argparse.Namespace) -> dict[str, object]:
    from HEART import Spectrometer, __version__ as heart_version
    from HEART.spectrometer import run_ray_trace

    detector_length = 2.0 * args.detector_half_width_mm
    detector_px = (args.detector_pixel_mm, args.detector_pixel_mm)
    detector_shape = (
        int(round(detector_length / args.detector_pixel_mm)),
        int(round(detector_length / args.detector_pixel_mm)),
    )
    combined_image = np.zeros(detector_shape, dtype=np.float64)
    combined_image_keV = np.zeros(detector_shape, dtype=np.float64)
    rng = np.random.default_rng(args.seed)

    spec = Spectrometer(silence=True, output_dir=None, output_file_name=None, save_ray_data=False)
    spec.add_detector(
        x_center_mm=np.array([0.0, 0.0, float(rows[0]["focal_z_mm"])]),
        axis_L=np.array([1.0, 0.0, 0.0]),
        length=detector_length,
        axis_W=np.array([0.0, 1.0, 0.0]),
        width=detector_length,
        px_size_mm=detector_px,
    )

    tile_summaries: list[dict[str, object]] = []
    total_hit_crystal = 0
    total_absorbed = 0
    total_photons = 0
    for index, row in enumerate(rows):
        tile_seed = args.seed + index * 1009
        local_rng = np.random.default_rng(tile_seed)
        _configure_crystal(spec, row, args)
        rays, origins, energies, polarizations = _tile_rays(row, args.photons_per_tile, args.source_offset_mm, local_rng)

        spec.detector.detector_image[...] = 0.0
        spec.detector.detector_image_keV[...] = 0.0
        hit_crystal, absorbed = run_ray_trace(
            spec,
            args.nproc,
            energies,
            rays,
            origins,
            polarizations,
            spec.detector.detector_image,
            spec.detector.detector_image_keV,
            False,
            tile_seed,
            False,
            rng,
        )
        heart_detector_weight = float(np.sum(spec.detector.detector_image))
        tile_image = spec.detector.detector_image
        tile_image_keV = spec.detector.detector_image_keV
        if args.detector_hit_model == "guan_direction_perturbation":
            tile_image, tile_image_keV = _guan_direction_detector_image(
                row,
                int(round(heart_detector_weight)),
                np.asarray(spec.detector.detector_L, dtype=np.float64),
                np.asarray(spec.detector.detector_W, dtype=np.float64),
                float(args.detector_half_width_mm),
                float(args.detector_pixel_mm),
                float(args.mosaic_fwhm_arcsec),
                float(args.source_jitter_mm),
                local_rng,
            )
        detector_weight = float(np.sum(tile_image))
        combined_image += tile_image
        combined_image_keV += tile_image_keV
        total_hit_crystal += int(hit_crystal)
        total_absorbed += int(absorbed)
        total_photons += args.photons_per_tile
        tile_summaries.append(
            {
                "ring_id": int(float(row["ring_id"])),
                "tile_id": int(float(row["tile_id"])),
                "photons": args.photons_per_tile,
                "hit_crystal": int(hit_crystal),
                "absorbed": int(absorbed),
                "detector_weight": detector_weight,
                "heart_detector_weight": heart_detector_weight,
            }
        )

    summary = {
        "ok": True,
        "heart_version": heart_version,
        "tiles": len(rows),
        "photons_per_tile": args.photons_per_tile,
        "total_photons": total_photons,
        "total_hit_crystal": total_hit_crystal,
        "total_absorbed": total_absorbed,
        "detector_weight": float(np.sum(combined_image)),
        "nonzero_detector_pixels": int(np.count_nonzero(combined_image)),
        "detector_half_width_mm": args.detector_half_width_mm,
        "detector_pixel_mm": args.detector_pixel_mm,
        "mosaic_fwhm_arcsec": args.mosaic_fwhm_arcsec,
        "mosaic_func": args.mosaic_func,
        "planar_mosaic_pdf": bool(args.planar_mosaic_pdf),
        "rocking_curve_fwhm_urad": args.rocking_curve_fwhm_urad,
        "detector_hit_model": args.detector_hit_model,
        "source_jitter_mm": args.source_jitter_mm,
        "used_independent_diff_plane_normal": True,
        "tile_summaries": tile_summaries,
    }
    return {
        "summary": summary,
        "detector_l": np.array(spec.detector.detector_L, dtype=np.float64),
        "detector_w": np.array(spec.detector.detector_W, dtype=np.float64),
        "image": combined_image,
        "image_keV": combined_image_keV,
    }


def _configure_crystal(spec: object, row: dict[str, str], args: argparse.Namespace) -> None:
    spec.add_flat_crystal(
        x_center_mm=_vec(row, "center"),
        axis_L=_vec(row, "tangential_axis"),
        length=float(row["tile_size_mm"]),
        axis_W=_vec(row, "radial_axis"),
        width=float(row["tile_size_mm"]),
        axis_N=_vec(row, "slab_normal"),
        Tc_mm=float(row["thickness_mm"]),
        diff_plane_N=_vec(row, "ideal_plane_normal"),
    )
    spec.crystal.physical_properties(
        material=str(row["material"]),
        miller_indices=(int(float(row["h"])), int(float(row["k"])), int(float(row["l"]))),
        first_order_indices=(int(float(row["h"])), int(float(row["k"])), int(float(row["l"]))),
        Debye_temp_K=0.0,
    )
    spec.crystal.prepare_mosaic_crystal(
        fwhm_deg=float(args.mosaic_fwhm_arcsec) / 3600.0,
        mosaic_func=str(args.mosaic_func),
        planar_mosaic_PDF=bool(args.planar_mosaic_pdf),
        target_E_keV=float(row["design_energy_keV"]),
        energy_dependent=False,
    )
    spec.crystal.define_rocking_curve(
        fwhm_urad_Gauss=float(args.rocking_curve_fwhm_urad),
        fwhm_urad_Lorentz=0.0,
        rc_center_urad=0.0,
        target_E_keV=float(row["design_energy_keV"]),
        energy_dependent=False,
    )
    spec.crystal.reflection_model_options(
        consider_polarization=False,
        use_rotating_normal=False,
        reflect_integ_steps=80,
    )


def _tile_rays(
    row: dict[str, str],
    photons: int,
    source_offset_mm: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    center = _vec(row, "center")
    axis_l = _unit(_vec(row, "tangential_axis"))
    axis_w = _unit(_vec(row, "radial_axis"))
    slab = _unit(_vec(row, "slab_normal"))
    tile_size = float(row["tile_size_mm"])
    offsets_l = rng.uniform(-0.5 * tile_size, 0.5 * tile_size, photons)
    offsets_w = rng.uniform(-0.5 * tile_size, 0.5 * tile_size, photons)
    face_points = center[np.newaxis, :] + offsets_l[:, np.newaxis] * axis_l + offsets_w[:, np.newaxis] * axis_w
    origins = face_points - float(source_offset_mm) * slab[np.newaxis, :]
    rays = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float64), (photons, 1))
    polarizations = np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float64), (photons, 1))
    energies = np.full(photons, float(row["design_energy_keV"]), dtype=np.float64)
    return rays, origins.astype(np.float64), energies, polarizations


def _write_combined_hdf5(path: Path, output: dict[str, object]) -> None:
    import h5py

    summary = output["summary"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h5:
        h5.create_dataset("Version", data=str(summary["heart_version"]))
        detector = h5.create_group("Detector")
        detector.create_dataset("detector_L_pos", data=output["detector_l"])
        detector.create_dataset("detector_W_pos", data=output["detector_w"])
        results = h5.create_group("Results")
        results.create_dataset("detector_image", data=output["image"])
        results.create_dataset("detector_image_keV", data=output["image_keV"])
        diagnostics = h5.create_group("Diagnostics")
        diagnostics.create_dataset("Number_of_Photons", data=float(summary["total_photons"]))
        diagnostics.create_dataset("Number_of_Photons_on_Crystal", data=float(summary["total_hit_crystal"]))
        diagnostics.create_dataset("Number_of_Photons_on_Detector", data=float(summary["detector_weight"]))
        diagnostics.create_dataset("Number_of_Absorbed_Photons", data=float(summary["total_absorbed"]))
        diagnostics.create_dataset("Tile_Count", data=int(summary["tiles"]))
        diagnostics.create_dataset("Photons_Per_Tile", data=int(summary["photons_per_tile"]))
        diagnostics.create_dataset("Detector_Hit_Model", data=str(summary["detector_hit_model"]))
        diagnostics.create_dataset("Source_Jitter_mm", data=float(summary["source_jitter_mm"]))


def _guan_direction_detector_image(
    row: dict[str, str],
    n_hits: int,
    detector_l: np.ndarray,
    detector_w: np.ndarray,
    detector_half_width_mm: float,
    detector_pixel_mm: float,
    mosaic_fwhm_arcsec: float,
    source_jitter_mm: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    image = np.zeros((detector_w.size, detector_l.size), dtype=np.float64)
    image_keV = np.zeros_like(image)
    if n_hits <= 0:
        return image, image_keV

    center = _vec(row, "center")
    axis_l = _unit(_vec(row, "tangential_axis"))
    axis_w = _unit(_vec(row, "radial_axis"))
    outgoing = _unit(
        np.array(
            [
                float(row["expected_diffracted_ux"]),
                float(row["expected_diffracted_uy"]),
                float(row["expected_diffracted_uz"]),
            ],
            dtype=np.float64,
        )
    )
    basis_1, basis_2 = _perturbation_basis(outgoing)
    sigma_rad = math.radians(mosaic_fwhm_arcsec / 3600.0) / 2.355
    focal_z = float(row["focal_z_mm"])
    energy = float(row["design_energy_keV"])

    offsets_l = rng.uniform(-0.5 * source_jitter_mm, 0.5 * source_jitter_mm, n_hits)
    offsets_w = rng.uniform(-0.5 * source_jitter_mm, 0.5 * source_jitter_mm, n_hits)
    perturb_1 = rng.normal(0.0, sigma_rad, n_hits)
    perturb_2 = rng.normal(0.0, sigma_rad, n_hits)
    for offset_l, offset_w, delta_1, delta_2 in zip(offsets_l, offsets_w, perturb_1, perturb_2):
        pos = center + offset_l * axis_l + offset_w * axis_w
        ray = _unit(outgoing + delta_1 * basis_1 + delta_2 * basis_2)
        if ray[2] <= 0.0:
            continue
        distance = (focal_z - pos[2]) / ray[2]
        hit = pos + distance * ray
        l_index = int(math.floor((float(hit[0]) + detector_half_width_mm) / detector_pixel_mm))
        w_index = int(math.floor((float(hit[1]) + detector_half_width_mm) / detector_pixel_mm))
        if 0 <= l_index < detector_l.size and 0 <= w_index < detector_w.size:
            image[w_index, l_index] += 1.0
            image_keV[w_index, l_index] += energy
    return image, image_keV


def _perturbation_basis(base: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    axis_z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    axis_x = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    e1 = np.cross(base, axis_z)
    if float(np.dot(e1, e1)) < 1.0e-24:
        e1 = np.cross(base, axis_x)
    e1 = _unit(e1)
    e2 = _unit(np.cross(base, e1))
    return e1, e2


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _select_rows(
    rows: list[dict[str, str]],
    ring_id: int | None,
    tile_id: int | None,
    max_tiles: int | None,
) -> list[dict[str, str]]:
    selected = rows
    if ring_id is not None:
        selected = [row for row in selected if int(float(row["ring_id"])) == ring_id]
    if tile_id is not None:
        selected = [row for row in selected if int(float(row["tile_id"])) == tile_id]
    if max_tiles is not None:
        selected = selected[:max_tiles]
    return selected


def _vec(row: dict[str, str], prefix: str) -> np.ndarray:
    return np.array(
        [
            float(row[f"{prefix}_x"] if f"{prefix}_x" in row else row[f"{prefix}_x_mm"]),
            float(row[f"{prefix}_y"] if f"{prefix}_y" in row else row[f"{prefix}_y_mm"]),
            float(row[f"{prefix}_z"] if f"{prefix}_z" in row else row[f"{prefix}_z_mm"]),
        ],
        dtype=np.float64,
    )


def _unit(v: np.ndarray) -> np.ndarray:
    n = math.sqrt(float(np.dot(v, v)))
    if n == 0.0:
        raise ValueError("zero-length vector")
    return v / n


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
