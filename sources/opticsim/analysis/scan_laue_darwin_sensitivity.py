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

from external_baseline.laue_raytrace_py.mosaic_darwin import (
    darwin_mosaic_probabilities,
    optimal_mosaic_thickness_mm,
)


ENERGIES_KEV = [480.0, 500.0, 511.0, 530.0, 550.0]
MOSAIC_ARCSEC = [15.0, 20.0, 30.0, 45.0, 60.0, 90.0]
THICKNESS_SCALE = [0.5, 0.75, 1.0, 1.25, 1.5]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Darwin mosaic Laue sensitivity over mosaicity and thickness.")
    parser.add_argument("--out", default="runs/laue_darwin_sensitivity")
    parser.add_argument("--crystallite-um", type=float, default=5.0)
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for mosaic in MOSAIC_ARCSEC:
        optimum_by_energy = {
            energy: optimal_mosaic_thickness_mm(
                energy_keV=energy,
                material="Ge",
                h=1,
                k=1,
                l=1,
                mosaic_fwhm_arcsec=mosaic,
                crystallite_thickness_um=args.crystallite_um,
            )
            for energy in ENERGIES_KEV
        }
        for scale in THICKNESS_SCALE:
            values = []
            for energy in ENERGIES_KEV:
                thickness = optimum_by_energy[energy] * scale
                result = darwin_mosaic_probabilities(
                    energy_keV=energy,
                    material="Ge",
                    h=1,
                    k=1,
                    l=1,
                    mosaic_fwhm_arcsec=mosaic,
                    thickness_mm=thickness,
                    crystallite_thickness_um=args.crystallite_um,
                )
                values.append((energy, thickness, result))
            mean_p_diff = sum(result.p_diff for _, _, result in values) / len(values)
            mean_p_abs = sum(result.p_abs for _, _, result in values) / len(values)
            mean_p_trans = sum(result.p_trans for _, _, result in values) / len(values)
            rows.append(
                {
                    "mosaic_arcsec": mosaic,
                    "thickness_scale": scale,
                    "mean_thickness_mm": sum(thickness for _, thickness, _ in values) / len(values),
                    "mean_peak_p_diff": mean_p_diff,
                    "mean_p_abs": mean_p_abs,
                    "mean_p_trans": mean_p_trans,
                    "min_peak_p_diff": min(result.p_diff for _, _, result in values),
                    "max_peak_p_diff": max(result.p_diff for _, _, result in values),
                    "approx_focal_sigma_mm": 8300.0 * math.radians(mosaic / 3600.0) / 2.355,
                }
            )

    with (out / "sensitivity.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    best = max(rows, key=lambda row: row["mean_peak_p_diff"])
    nominal = next(row for row in rows if row["mosaic_arcsec"] == 30.0 and row["thickness_scale"] == 1.0)
    summary = {
        "ok": True,
        "n_cases": len(rows),
        "energies_keV": ENERGIES_KEV,
        "best_case": best,
        "nominal_case": nominal,
        "nominal_to_best_pdiff_ratio": nominal["mean_peak_p_diff"] / best["mean_peak_p_diff"],
        "interpretation": "Sensitivity scan only. It quantifies model dependence; it is not a substitute for measured Ge(111) validation.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
