from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_baseline.laue_raytrace_py.mosaic_darwin import darwin_mosaic_probabilities


BENCHMARKS = [
    {
        "case": "Barriere2009_Au111_299keV",
        "material": "Au",
        "hkl": [1, 1, 1],
        "energy_keV": 299.0,
        "mosaic_arcsec": 30.0,
        "thickness_mm": 2.0,
        "crystallite_um": 46.0,
        "observed_diff_eff": 0.47,
        "observed_reflectivity": 0.12,
    },
    {
        "case": "Barriere2009_Au111_399keV",
        "material": "Au",
        "hkl": [1, 1, 1],
        "energy_keV": 399.0,
        "mosaic_arcsec": 24.0,
        "thickness_mm": 2.0,
        "crystallite_um": 52.0,
        "observed_diff_eff": 0.47,
        "observed_reflectivity": 0.22,
    },
    {
        "case": "Barriere2009_Au111_494keV",
        "material": "Au",
        "hkl": [1, 1, 1],
        "energy_keV": 494.0,
        "mosaic_arcsec": 24.0,
        "thickness_mm": 2.0,
        "crystallite_um": 57.0,
        "observed_diff_eff": 0.46,
        "observed_reflectivity": 0.26,
    },
    {
        "case": "Barriere2009_Au111_588keV",
        "material": "Au",
        "hkl": [1, 1, 1],
        "energy_keV": 588.0,
        "mosaic_arcsec": 18.0,
        "thickness_mm": 2.0,
        "crystallite_um": 65.0,
        "observed_diff_eff": 0.45,
        "observed_reflectivity": 0.29,
    },
    {
        "case": "Barriere2009_Cu111_299keV",
        "material": "Cu",
        "hkl": [1, 1, 1],
        "energy_keV": 299.0,
        "mosaic_arcsec": 25.0,
        "thickness_mm": 3.0,
        "crystallite_um": 60.0,
        "observed_diff_eff": 0.46,
        "observed_reflectivity": 0.34,
    },
    {
        "case": "Barriere2009_Cu111_589keV",
        "material": "Cu",
        "hkl": [1, 1, 1],
        "energy_keV": 589.0,
        "mosaic_arcsec": 14.0,
        "thickness_mm": 9.0,
        "crystallite_um": 129.0,
        "observed_diff_eff": 0.47,
        "observed_reflectivity": 0.26,
    },
]


def main() -> int:
    out_dir = Path("runs/laue_darwin_benchmark")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in BENCHMARKS:
        h, k, l = case["hkl"]
        result = darwin_mosaic_probabilities(
            energy_keV=case["energy_keV"],
            material=case["material"],
            h=h,
            k=k,
            l=l,
            mosaic_fwhm_arcsec=case["mosaic_arcsec"],
            thickness_mm=case["thickness_mm"],
            crystallite_thickness_um=case["crystallite_um"],
        )
        rows.append(
            {
                **case,
                "calc_diff_eff": result.diffraction_efficiency_no_abs,
                "calc_reflectivity": result.p_diff,
                "abs_diff_eff": abs(result.diffraction_efficiency_no_abs - case["observed_diff_eff"]),
                "abs_reflectivity": abs(result.p_diff - case["observed_reflectivity"]),
                "extinction_length_um": result.extinction_length_um,
                "source": result.source,
            }
        )
    max_diff_eff_error = max(row["abs_diff_eff"] for row in rows)
    max_reflectivity_error = max(row["abs_reflectivity"] for row in rows)
    summary = {
        "ok": max_diff_eff_error <= 0.03 and max_reflectivity_error <= 0.03,
        "n_cases": len(rows),
        "max_abs_diff_eff_error": max_diff_eff_error,
        "max_abs_reflectivity_error": max_reflectivity_error,
        "benchmark_source": "Barriere et al. 2009 J. Appl. Cryst. Tables 2 and 4",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out_dir / "benchmark.csv").open("w", newline="") as f:
        fields = [
            "case",
            "material",
            "hkl",
            "energy_keV",
            "mosaic_arcsec",
            "thickness_mm",
            "crystallite_um",
            "observed_diff_eff",
            "calc_diff_eff",
            "abs_diff_eff",
            "observed_reflectivity",
            "calc_reflectivity",
            "abs_reflectivity",
            "extinction_length_um",
            "source",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
