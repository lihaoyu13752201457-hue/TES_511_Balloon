#!/usr/bin/env python3
"""Build an uncalibrated W/Si Parratt reflectivity table for channeling optics."""

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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "optics" / "channeling_fp"))

from src.materials import material_density, optical_constants_from_xraydb  # noqa: E402
from src.multilayer import bilayer_stack_from_config, parratt_reflectivity  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="optics/channeling_fp/out/first_principles_fast/reflectivity_wsi_parratt.csv")
    ap.add_argument("--energies-keV", nargs="+", type=float, default=[500.0, 505.0, 511.0, 515.0, 522.0])
    ap.add_argument("--alpha-mrad-min", type=float, default=0.005)
    ap.add_argument("--alpha-mrad-max", type=float, default=5.0)
    ap.add_argument("--n-alpha", type=int, default=600)
    ap.add_argument("--roughness-nm", type=float, default=0.0)
    ap.add_argument("--material-a", default="W")
    ap.add_argument("--material-b", default="Si")
    ap.add_argument("--thickness-nm", nargs=2, type=float, default=[30.0, 150.0])
    ap.add_argument("--periods", type=int, default=30)
    ap.add_argument("--substrate", default="Si")
    return ap.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "energy_keV",
        "alpha_mrad",
        "R_multilayer",
        "delta_W",
        "beta_W",
        "delta_Si",
        "beta_Si",
        "roughness_nm",
        "cam511_calibration_used",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = {
        "multilayer": {
            "material_a": args.material_a,
            "material_b": args.material_b,
            "layer_a_thickness_nm": float(args.thickness_nm[0]),
            "layer_b_thickness_nm": float(args.thickness_nm[1]),
            "periods": int(args.periods),
            "substrate": args.substrate,
            "roughness_nm": float(args.roughness_nm),
        }
    }
    alphas = np.geomspace(float(args.alpha_mrad_min), float(args.alpha_mrad_max), int(args.n_alpha))
    rows: list[dict[str, Any]] = []
    by_energy: dict[str, list[float]] = {}
    for energy in args.energies_keV:
        layers, substrate = bilayer_stack_from_config(cfg, float(energy))
        oc_w = optical_constants_from_xraydb("W", material_density("W"), float(energy))
        oc_si = optical_constants_from_xraydb("Si", material_density("Si"), float(energy))
        refl_values: list[float] = []
        for alpha_mrad in alphas:
            r = parratt_reflectivity(float(energy), float(alpha_mrad) * 1.0e-3, layers, substrate)
            r = float(np.clip(r, 0.0, 1.0))
            refl_values.append(r)
            rows.append(
                {
                    "energy_keV": float(energy),
                    "alpha_mrad": float(alpha_mrad),
                    "R_multilayer": r,
                    "delta_W": oc_w.delta,
                    "beta_W": oc_w.beta,
                    "delta_Si": oc_si.delta,
                    "beta_Si": oc_si.beta,
                    "roughness_nm": float(args.roughness_nm),
                    "cam511_calibration_used": "false",
                }
            )
        by_energy[str(float(energy))] = refl_values

    finite = all(math.isfinite(float(row["R_multilayer"])) for row in rows)
    bounded = all(0.0 <= float(row["R_multilayer"]) <= 1.0 for row in rows)
    large_alpha_ok = True
    for energy in args.energies_keV:
        vals = by_energy[str(float(energy))]
        if vals[-1] > max(vals[0], 1.0e-30):
            large_alpha_ok = False
    summary = {
        "status": "PASS_PARRATT_TABLE_BUILT" if finite and bounded and large_alpha_ok else "FAIL_PARRATT_TABLE_CHECKS",
        "rows": len(rows),
        "energies_keV": [float(v) for v in args.energies_keV],
        "alpha_mrad_min": float(alphas[0]),
        "alpha_mrad_max": float(alphas[-1]),
        "n_alpha": len(alphas),
        "roughness_nm": float(args.roughness_nm),
        "calibration": "none",
        "cam511_calibration_used": False,
        "checks": {
            "finite": finite,
            "bounded_0_1": bounded,
            "large_alpha_not_above_small_alpha": large_alpha_ok,
        },
    }
    return rows, summary


def make_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.6), constrained_layout=True)
    energies = sorted({float(row["energy_keV"]) for row in rows})
    for energy in energies:
        sub = [row for row in rows if float(row["energy_keV"]) == energy]
        ax.plot([float(row["alpha_mrad"]) for row in sub], [float(row["R_multilayer"]) for row in sub], label=f"{energy:g} keV")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Grazing angle alpha (mrad)")
    ax.set_ylabel("Parratt multilayer reflectivity")
    ax.set_title("Uncalibrated W/Si multilayer reflectivity")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    out = ROOT / args.out
    rows, summary = build_rows(args)
    write_csv(out, rows)
    summary_path = out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    make_plot(out.with_suffix(".png"), rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
