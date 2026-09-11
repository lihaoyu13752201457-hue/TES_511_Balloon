#!/usr/bin/env python3
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

import numpy as np
import xraydb

from external_baseline.channel_raytrace_py.parratt_reflectivity import (
    MultilayerSpec,
    compute_reflectivity_rows,
    geometric_theta_grid,
    manual_parratt_reflectivity_s,
)


def fmt(value: float) -> str:
    return f"{value:.6g}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run W/Si reflectivity provenance and roughness systematic sweep.")
    parser.add_argument("--out-dir", default="records/2026-05-24_optics_evidence_gap_closure/reflectivity")
    parser.add_argument("--energy-kev", type=float, default=511.0)
    parser.add_argument("--theta-min", type=float, default=1.0e-8)
    parser.add_argument("--theta-max", type=float, default=5.0e-3)
    parser.add_argument("--n-theta", type=int, default=220)
    parser.add_argument("--roughness-nm", default="0,0.2,0.5,1,2,5,10")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    roughness_values = [float(item) for item in args.roughness_nm.split(",") if item.strip()]
    theta = geometric_theta_grid(args.theta_min, args.theta_max, args.n_theta)
    e_ev = args.energy_kev * 1000.0
    detail_csv = out_dir / "wsi_reflectivity_roughness_sweep.csv"
    summary_json = out_dir / "wsi_reflectivity_provenance_roughness_sweep.json"
    report_md = out_dir / "wsi_reflectivity_provenance_roughness_sweep.md"

    detail_fields = [
        "roughness_nm",
        "theta_rad",
        "R_xraydb_multilayer",
        "R_manual_parratt",
        "abs_delta_R",
        "A_stack_attenuation",
        "T_stack_attenuation",
    ]
    summary_rows: list[dict[str, float]] = []
    max_backend_delta = 0.0
    with detail_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields)
        writer.writeheader()
        for roughness in roughness_values:
            spec = MultilayerSpec(roughness_nm=roughness)
            api_rows = compute_reflectivity_rows(spec, E_keV=args.energy_kev, theta_rad=theta)
            manual_R = manual_parratt_reflectivity_s(spec, E_keV=args.energy_kev, theta_rad=theta)
            deltas = [abs(row.R - float(manual)) for row, manual in zip(api_rows, manual_R)]
            max_backend_delta = max(max_backend_delta, max(deltas))
            r_values = [row.R for row in api_rows]
            t_values = [row.T for row in api_rows]
            best = max(api_rows, key=lambda row: row.R)
            last_high = max((row.theta_rad for row in api_rows if row.R >= 0.5), default=0.0)
            summary_rows.append(
                {
                    "roughness_nm": roughness,
                    "max_R": max(r_values),
                    "theta_at_max_R_rad": best.theta_rad,
                    "theta_R_ge_0p5_max_rad": last_high,
                    "R_at_theta_min": r_values[0],
                    "R_at_theta_max": r_values[-1],
                    "mean_R": sum(r_values) / len(r_values),
                    "mean_T": sum(t_values) / len(t_values),
                    "max_abs_delta_manual_vs_xraydb": max(deltas),
                }
            )
            for row, manual, delta in zip(api_rows, manual_R, deltas):
                writer.writerow(
                    {
                        "roughness_nm": roughness,
                        "theta_rad": row.theta_rad,
                        "R_xraydb_multilayer": row.R,
                        "R_manual_parratt": float(manual),
                        "abs_delta_R": delta,
                        "A_stack_attenuation": row.A,
                        "T_stack_attenuation": row.T,
                    }
                )

    constants = {}
    for material, density in (("W", 19.3), ("Si", 2.33)):
        delta, beta, atlen = xraydb.xray_delta_beta(material, density, e_ev)
        constants[material] = {
            "density_g_cm3": density,
            "delta": float(delta),
            "beta": float(beta),
            "attenuation_length_cm": float(atlen),
            "material_mu_cm_inv": float(xraydb.material_mu(material, e_ev, density=density)),
        }

    summary = {
        "energy_keV": args.energy_kev,
        "theta_grid": {"min_rad": args.theta_min, "max_rad": args.theta_max, "n": args.n_theta},
        "roughness_nm": roughness_values,
        "xraydb_version": getattr(xraydb, "__version__", "unknown"),
        "backend_comparison": "xraydb.multilayer_reflectivity vs in-repo manual s-polarization Parratt recursion",
        "optical_constants": constants,
        "stack": {
            "high_Z": "W",
            "low_Z": "Si",
            "high_Z_thickness_nm": 30.0,
            "low_Z_thickness_nm": 150.0,
            "n_periods": 30,
            "polarization": "s",
        },
        "max_backend_abs_delta_R": max_backend_delta,
        "rows": summary_rows,
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ok = math.isfinite(max_backend_delta) and max_backend_delta < 1.0e-9
    lines = [
        "# W/Si reflectivity provenance and roughness sweep",
        "",
        f"- energy_keV: {args.energy_kev}",
        f"- theta_grid_rad: `{args.theta_min:g}..{args.theta_max:g}`, n={args.n_theta}",
        f"- roughness_nm: `{roughness_values}`",
        f"- xraydb_version: `{getattr(xraydb, '__version__', 'unknown')}`",
        f"- detail_csv: `{detail_csv}`",
        f"- summary_json: `{summary_json}`",
        f"- backend_crosscheck_status: **{'PASS' if ok else 'WARN'}**",
        "",
        "## Optical Constants",
        "",
        "| material | density_g_cm3 | delta | beta | mu_cm_inv | attenuation_length_cm |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for material, values in constants.items():
        lines.append(
            f"| {material} | {fmt(values['density_g_cm3'])} | {fmt(values['delta'])} | {fmt(values['beta'])} | "
            f"{fmt(values['material_mu_cm_inv'])} | {fmt(values['attenuation_length_cm'])} |"
        )
    lines.extend(
        [
            "",
            "## Roughness Sweep",
            "",
            "| roughness_nm | max_R | theta_at_max_R_rad | theta_R_ge_0p5_max_rad | R_at_theta_min | R_at_theta_max | max_abs_delta_manual_vs_xraydb |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {fmt(row['roughness_nm'])} | {fmt(row['max_R'])} | {fmt(row['theta_at_max_R_rad'])} | "
            f"{fmt(row['theta_R_ge_0p5_max_rad'])} | {fmt(row['R_at_theta_min'])} | "
            f"{fmt(row['R_at_theta_max'])} | {fmt(row['max_abs_delta_manual_vs_xraydb'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is an independent code-path provenance check: `xraydb.multilayer_reflectivity` is compared with the repository's manual s-polarization Parratt recursion using the same xraydb optical constants.",
            "- It is not an IMD/IDL source recovery. It closes the local implementation/provenance gap, not the unpublished 511-CAM production-table gap.",
            "- The sweep is a roughness systematic: it reports how W/Si reflectivity changes across the roughness values without tuning public wall-by-wall transmission toward 0.80.",
            "",
        ]
    )
    report_md.write_text("\n".join(lines), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
