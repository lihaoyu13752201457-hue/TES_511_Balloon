#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.run_patched_heart_lens_oracle import _guan_direction_detector_image, _write_combined_hdf5


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tile-table",
        default=str(ROOT / "benchmarks/reference_outputs/external_lens_oracle_tiles.csv"),
    )
    parser.add_argument(
        "--heart-summary",
        default=str(ROOT / "benchmarks/reference_outputs/heart_patched_full_lens_run_summary.json"),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--seed", type=int, default=511)
    parser.add_argument("--detector-half-width-mm", type=float, default=10.0)
    parser.add_argument("--detector-pixel-mm", type=float, default=0.05)
    parser.add_argument("--source-jitter-mm", type=float, default=0.3)
    parser.add_argument("--mosaic-fwhm-arcsec", type=float, default=30.0)
    args = parser.parse_args()

    heart = json.loads(Path(args.heart_summary).read_text(encoding="utf-8"))
    rows = _tile_rows_by_key(Path(args.tile_table))
    detector_l = _detector_axis(args.detector_half_width_mm, args.detector_pixel_mm)
    detector_w = _detector_axis(args.detector_half_width_mm, args.detector_pixel_mm)
    image = np.zeros((detector_w.size, detector_l.size), dtype=np.float64)
    image_keV = np.zeros_like(image)

    rebuilt_tiles = []
    for index, tile in enumerate(heart["tile_summaries"]):
        key = (int(tile["ring_id"]), int(tile["tile_id"]))
        row = rows[key]
        detector_weight = int(round(float(tile.get("heart_detector_weight", tile["detector_weight"]))))
        rng = np.random.default_rng(args.seed + index * 1009)
        tile_image, tile_image_keV = _guan_direction_detector_image(
            row,
            detector_weight,
            detector_l,
            detector_w,
            args.detector_half_width_mm,
            args.detector_pixel_mm,
            args.mosaic_fwhm_arcsec,
            args.source_jitter_mm,
            rng,
        )
        image += tile_image
        image_keV += tile_image_keV
        rebuilt_tiles.append(
            {
                "ring_id": key[0],
                "tile_id": key[1],
                "heart_detector_weight": detector_weight,
                "detector_weight": float(np.sum(tile_image)),
            }
        )

    detector_weight = float(np.sum(image))
    summary = {
        "ok": True,
        "heart_version": heart["heart_version"],
        "source_heart_summary": str(Path(args.heart_summary)),
        "tiles": int(heart["tiles"]),
        "photons_per_tile": int(heart["photons_per_tile"]),
        "total_photons": int(heart["total_photons"]),
        "total_hit_crystal": int(heart["total_hit_crystal"]),
        "total_absorbed": int(heart["total_absorbed"]),
        "detector_weight": detector_weight,
        "source_heart_detector_weight": float(heart["detector_weight"]),
        "nonzero_detector_pixels": int(np.count_nonzero(image)),
        "detector_half_width_mm": args.detector_half_width_mm,
        "detector_pixel_mm": args.detector_pixel_mm,
        "mosaic_fwhm_arcsec": args.mosaic_fwhm_arcsec,
        "mosaic_func": heart.get("mosaic_func"),
        "planar_mosaic_pdf": heart.get("planar_mosaic_pdf"),
        "rocking_curve_fwhm_urad": heart.get("rocking_curve_fwhm_urad"),
        "detector_hit_model": "guan_direction_perturbation_from_heart_tile_summary",
        "source_jitter_mm": args.source_jitter_mm,
        "used_independent_diff_plane_normal": heart.get("used_independent_diff_plane_normal"),
        "tile_summaries": rebuilt_tiles,
    }
    output = {
        "summary": summary,
        "detector_l": detector_l,
        "detector_w": detector_w,
        "image": image,
        "image_keV": image_keV,
    }
    _write_combined_hdf5(Path(args.out), output)
    Path(args.summary).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _tile_rows_by_key(path: Path) -> dict[tuple[int, int], dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {(int(float(row["ring_id"])), int(float(row["tile_id"]))): row for row in rows}


def _detector_axis(half_width_mm: float, pixel_mm: float) -> np.ndarray:
    n_pixels = int(round((2.0 * half_width_mm) / pixel_mm))
    return np.linspace(-half_width_mm + 0.5 * pixel_mm, half_width_mm - 0.5 * pixel_mm, n_pixels)


if __name__ == "__main__":
    raise SystemExit(main())
