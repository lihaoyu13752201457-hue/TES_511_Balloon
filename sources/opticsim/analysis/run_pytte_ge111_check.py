from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for rel in [".tools/pytte", ".tools/crystalpy_base"]:
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import numpy as np

np.complex = complex  # pyTTE 1.0 compatibility with numpy >= 2
np.float = float

from pyTTE import Quantity, TTcrystal, TTscan, TakagiTaupin

from external_baseline.laue_raytrace_py.mosaic_darwin import darwin_mosaic_probabilities


def main() -> int:
    out = ROOT / "runs" / "laue_pytte_ge111_check"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    log_parts = []
    for energy_keV in [500.0, 511.0]:
        for polarization in ["sigma", "pi"]:
            result, log, warning_count = run_case(energy_keV, polarization)
            log_parts.append(f"===== {energy_keV:g} keV {polarization} =====\n{log}\n")
            rows.append(result | {"warning_count": warning_count})
    (out / "pytte_stdout.log").write_text("\n".join(log_parts), encoding="utf-8")
    with (out / "pytte_ge111_check.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "ok": all(row["pytte_peak_diffraction"] > row["darwin_mosaic_peak_no_abs"] for row in rows)
        and all(0.95 <= row["pytte_center_flux_sum"] <= 1.05 for row in rows),
        "n_cases": len(rows),
        "interpretation": (
            "PyTTE is an independent perfect-crystal Takagi-Taupin check. "
            "It is not a mosaic-crystal replacement table; it checks that a perfect Ge(111) Laue crystal "
            "has a higher peak diffracted branch than the mosaic Darwin table and near-conserved "
            "diffraction+forward flux in this setup."
        ),
        "max_warning_count": max(row["warning_count"] for row in rows),
        "cases": rows,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


def run_case(energy_keV: float, polarization: str) -> tuple[dict[str, float | str], str, int]:
    scan_points = np.linspace(-5.0, 5.0, 41)
    crystal = TTcrystal(
        crystal="Ge",
        hkl=[1, 1, 1],
        thickness=Quantity(10.0, "mm"),
        asymmetry=Quantity(90.0, "deg"),
    )
    scan = TTscan(
        constant=Quantity(energy_keV, "keV"),
        scan=Quantity(scan_points, "urad"),
        polarization=polarization,
        output_type="intensity",
        integration_step=Quantity(20.0, "um"),
    )
    tt = TakagiTaupin(crystal, scan)
    stream = io.StringIO()
    with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(stream):
        warnings.simplefilter("always")
        tt.run()
    solution = tt.solution
    diffraction = np.asarray(solution["diffraction"], dtype=float)
    forward = np.asarray(solution["forward_diffraction"], dtype=float)
    center = len(scan_points) // 2
    darwin = darwin_mosaic_probabilities(
        energy_keV=energy_keV,
        material="Ge",
        h=1,
        k=1,
        l=1,
        mosaic_fwhm_arcsec=30.0,
        thickness_mm=10.0,
        crystallite_thickness_um=5.0,
        delta_theta_rad=0.0,
    )
    return (
        {
            "tool": "PyTTE 1.0",
            "energy_keV": energy_keV,
            "polarization": polarization,
            "geometry": str(solution["geometry"]),
            "thickness_mm": 10.0,
            "scan_min_urad": float(scan_points.min()),
            "scan_max_urad": float(scan_points.max()),
            "bragg_angle_deg": float(solution["bragg_angle"].in_units("deg")),
            "pytte_peak_diffraction": float(diffraction.max()),
            "pytte_center_diffraction": float(diffraction[center]),
            "pytte_center_forward": float(forward[center]),
            "pytte_center_flux_sum": float(diffraction[center] + forward[center]),
            "darwin_mosaic_peak_no_abs": float(darwin.diffraction_efficiency_no_abs),
            "darwin_mosaic_peak_with_abs": float(darwin.p_diff),
            "darwin_absorption_transmission": float(darwin.absorption_transmission),
        },
        stream.getvalue(),
        len(caught),
    )


if __name__ == "__main__":
    raise SystemExit(main())
