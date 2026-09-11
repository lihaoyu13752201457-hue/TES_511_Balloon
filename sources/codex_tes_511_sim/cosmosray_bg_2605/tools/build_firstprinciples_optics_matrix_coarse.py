#!/usr/bin/env python3
"""Build a coarse first-principles optics response matrix from the L2 Parratt model."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "optics" / "channeling_fp"))

from src.bent_channel import run, weighted_quantile  # noqa: E402


OUT = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="optics/channeling_fp/configs/cam511_channeling_fp_firstprinciples_L2_parratt.json")
    ap.add_argument("--outdir", default="optics/channeling_fp/out/first_principles_fast")
    ap.add_argument("--energies-keV", nargs="+", type=float, default=[500.0, 505.0, 511.0, 515.0, 522.0])
    ap.add_argument("--theta-arcmin", nargs="+", type=float, default=[0.0, 1.0, 2.0, 3.0, 4.0, 4.47])
    ap.add_argument("--phi-deg", nargs="+", type=float, default=[0.0, 90.0, 180.0, 270.0])
    ap.add_argument("--n-rays-per-bin", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=511)
    return ap.parse_args()


class RunArgs:
    def __init__(self, n_rays: int, seed: int, offaxis_x_arcmin: float, offaxis_y_arcmin: float):
        self.n_rays = n_rays
        self.seed = seed
        self.offaxis_x_arcmin = offaxis_x_arcmin
        self.offaxis_y_arcmin = offaxis_y_arcmin


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def centroid(rows: dict[str, np.ndarray], weights: np.ndarray, key: str) -> float:
    total = float(np.sum(weights))
    if total <= 0.0:
        return float(np.mean(rows[key]))
    return float(np.sum(rows[key] * weights) / total)


def main() -> int:
    args = parse_args()
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    arrays: dict[str, list[float]] = {
        "energy_keV": [],
        "theta_arcmin": [],
        "phi_deg": [],
        "Aeff_cm2": [],
        "r50_mm": [],
        "r68_mm": [],
        "r90_mm": [],
        "r95_mm": [],
        "D95_mm": [],
    }

    idx = 0
    for energy in args.energies_keV:
        cfg["energy_keV"] = float(energy)
        for theta in args.theta_arcmin:
            for phi in args.phi_deg:
                theta_x = float(theta) * math.cos(math.radians(float(phi)))
                theta_y = float(theta) * math.sin(math.radians(float(phi)))
                run_args = RunArgs(int(args.n_rays_per_bin), int(args.seed + idx), theta_x, theta_y)
                rows, summary = run(cfg, run_args)
                w = rows["effective_area_term_mm2"]
                f_mm = float(cfg["focus_length_m"]) * 1000.0
                x0 = f_mm * math.tan(math.radians(theta_x / 60.0))
                y0 = f_mm * math.tan(math.radians(theta_y / 60.0))
                r = np.sqrt((rows["x_fp_mm"] - x0) ** 2 + (rows["y_fp_mm"] - y0) ** 2)
                rec = {
                    "energy_keV": float(energy),
                    "theta_arcmin": float(theta),
                    "phi_deg": float(phi),
                    "Aeff_cm2": float(summary["estimated_effective_area_cm2"]),
                    "r50_mm": weighted_quantile(r, w, 0.50),
                    "r68_mm": weighted_quantile(r, w, 0.68),
                    "r90_mm": weighted_quantile(r, w, 0.90),
                    "r95_mm": weighted_quantile(r, w, 0.95),
                    "D95_mm": 2.0 * weighted_quantile(r, w, 0.95),
                    "x_centroid_mm": centroid(rows, w, "x_fp_mm"),
                    "y_centroid_mm": centroid(rows, w, "y_fp_mm"),
                    "mean_bounce_count": float(summary["mean_bounce_count"]),
                    "median_alpha_mrad": float(summary["median_last_alpha_mrad"]),
                    "n_rays": int(args.n_rays_per_bin),
                    "weight_model": summary["weight_model"],
                    "cam511_calibration_used": bool(summary["cam511_calibration_used"]),
                }
                records.append(rec)
                for key in arrays:
                    arrays[key].append(float(rec[key]))
                idx += 1

    write_csv(outdir / "first_principles_matrix_summary.csv", records)
    np.savez(outdir / "optics_response_matrix_coarse.npz", **{key: np.asarray(values) for key, values in arrays.items()})
    summary = {
        "status": "PASS_FIRST_PRINCIPLES_MATRIX_COARSE",
        "rows": len(records),
        "n_rays_per_bin": int(args.n_rays_per_bin),
        "calibration": "none",
        "cam511_calibration_used": False,
    }
    (outdir / "optics_response_matrix_coarse_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
