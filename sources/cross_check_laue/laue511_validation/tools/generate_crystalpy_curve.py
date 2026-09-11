#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/ubuntu/opticsim/.tools/crystalpy_base")

from crystalpy.util.calc_xcrystal import calc_xcrystal_angular_scan
from laue511.external_curve import summarize_external_curve


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/crystalpy"))
    parser.add_argument("--energy-kev", type=float, default=511.0)
    parser.add_argument("--thickness-mm", type=float, default=10.218801)
    parser.add_argument("--d-spacing-A", type=float, default=3.266590088)
    parser.add_argument("--scan-min-urad", type=float, default=-5.0)
    parser.add_argument("--scan-max-urad", type=float, default=5.0)
    parser.add_argument("--n-angle", type=int, default=101)
    args = parser.parse_args()

    os.environ.setdefault("MPLCONFIGDIR", "/tmp")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    curve_path = out_dir / "ge111_511keV_crystalpy_laue_curve.csv"
    log_path = out_dir / "crystalpy_stdout.log"

    reflectivity, transmittivity, deviations, log = _run_crystalpy(args)
    absorption = np.maximum(0.0, 1.0 - reflectivity - transmittivity)
    _write_curve(curve_path, deviations, reflectivity, transmittivity, absorption)
    log_path.write_text(log, encoding="utf-8")
    summary = summarize_external_curve(
        curve_path,
        energy_keV=args.energy_kev,
        d_spacing_A=args.d_spacing_A,
        thickness_mm=args.thickness_mm,
    )
    summary["curve_csv"] = str(curve_path)
    summary["interpretation"] = (
        "CrystalPy is used here as an independent perfect-crystal dynamical-diffraction "
        "rocking-curve check. It is not a mosaic Laue-lens replacement curve."
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_readme(out_dir, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _run_crystalpy(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    common = dict(
        crystal_name="Ge",
        miller_h=1,
        miller_k=1,
        miller_l=1,
        thickness=args.thickness_mm * 1.0e-3,
        asymmetry_angle=np.pi / 2.0,
        material_constants_library_flag=0,
        energy=args.energy_kev * 1000.0,
        angle_deviation_min=args.scan_min_urad * 1.0e-6,
        angle_deviation_max=args.scan_max_urad * 1.0e-6,
        angle_deviation_points=args.n_angle,
        do_plot=0,
        calculation_strategy_flag=1,
    )
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        diff, _, deviations = calc_xcrystal_angular_scan(geometry_type_index=1, **common)
        trans, _, _ = calc_xcrystal_angular_scan(geometry_type_index=3, **common)
    reflectivity = 0.5 * np.asarray(diff["intensity"], dtype=float)
    transmittivity = 0.5 * np.asarray(trans["intensity"], dtype=float)
    if not np.isfinite(reflectivity).all() or not np.isfinite(transmittivity).all():
        raise RuntimeError("CrystalPy returned non-finite intensities")
    return reflectivity, transmittivity, np.asarray(deviations, dtype=float), stream.getvalue()


def _write_curve(path: Path, deviations: np.ndarray, reflectivity: np.ndarray, transmittivity: np.ndarray, absorption: np.ndarray) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "delta_theta_rad",
                "reflectivity",
                "transmittivity",
                "absorption",
                "source_tool",
                "source_version",
            ],
        )
        writer.writeheader()
        for delta, refl, trans, absorb in zip(deviations, reflectivity, transmittivity, absorption):
            writer.writerow(
                {
                    "delta_theta_rad": f"{delta:.12g}",
                    "reflectivity": f"{refl:.12g}",
                    "transmittivity": f"{trans:.12g}",
                    "absorption": f"{absorb:.12g}",
                    "source_tool": "CrystalPy",
                    "source_version": "local_opticsim_tools",
                }
            )


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# CrystalPy Ge(111) Rocking Curve",
                "",
                "Independent perfect-crystal Laue rocking-curve benchmark generated with local CrystalPy.",
                "",
                f"- ok: {summary['ok']}",
                f"- rows: {summary['n_rows']}",
                f"- peak reflectivity: {summary['peak_reflectivity']:.6g}",
                f"- max flux conservation residual: {summary['max_flux_conservation_residual']:.6g}",
                "",
                "This is not a mosaic Laue-lens replacement curve.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
