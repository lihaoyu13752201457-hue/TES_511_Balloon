from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_baseline.laue_raytrace_py.mosaic_darwin import darwin_mosaic_probabilities


ENERGIES_KEV = [200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0]

# Kohnle 1998, thesis section 8.3.1, Ge(111) double-crystal APS measurement.
# The text reports a ray-tracing/Darwin-model inference for the second
# 3-mm-thick Ge(111) crystal with about 3 arcsec mosaicity: peak efficiency to
# monochromatic zero-divergence photons rises from 37% at 200 keV to 43% at
# 500 keV. The measured double/single flux ratio is a separate double-crystal
# observable and is therefore kept as provenance rather than used as a direct
# single-crystal benchmark.
PUBLISHED_ENDPOINTS = {
    200.0: 0.37,
    500.0: 0.43,
}


def main() -> int:
    out_dir = ROOT / "runs" / "laue_kohnle1998_ge111_benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for energy_keV in ENERGIES_KEV:
        result = darwin_mosaic_probabilities(
            energy_keV=energy_keV,
            material="Ge",
            h=1,
            k=1,
            l=1,
            mosaic_fwhm_arcsec=3.0,
            thickness_mm=3.0,
            crystallite_thickness_um=5.0,
        )
        row = {
            "energy_keV": energy_keV,
            "material": "Ge",
            "hkl": "111",
            "mosaic_fwhm_arcsec": 3.0,
            "thickness_mm": 3.0,
            "crystallite_um": 5.0,
            "calc_peak_eff_with_abs": result.p_diff,
            "calc_peak_eff_no_abs": result.diffraction_efficiency_no_abs,
            "absorption_transmission": result.absorption_transmission,
            "published_peak_eff_with_abs": PUBLISHED_ENDPOINTS.get(energy_keV, ""),
            "endpoint_abs_error": (
                abs(result.p_diff - PUBLISHED_ENDPOINTS[energy_keV])
                if energy_keV in PUBLISHED_ENDPOINTS
                else ""
            ),
            "source": result.source,
        }
        rows.append(row)

    endpoint_errors = [
        row["endpoint_abs_error"] for row in rows if row["endpoint_abs_error"] != ""
    ]
    summary = {
        "ok": max(endpoint_errors) <= 0.02
        and all(0.35 <= row["calc_peak_eff_with_abs"] <= 0.45 for row in rows),
        "n_cases": len(rows),
        "endpoint_max_abs_error": max(endpoint_errors),
        "benchmark_source": (
            "A. Kohnle, A Gamma-Ray Lens for Nuclear Astrophysics, "
            "PhD thesis, Universite Paul Sabatier, 1998, section 8.3.1"
        ),
        "local_source_pdf": "records/laue_external_sources/Diss_Kohnle_98.pdf",
        "published_ge111_context": {
            "crystal_setup": "two 3-mm Ge(111) crystals at APS, energies 200-500 keV",
            "mosaic_width_fit": "first crystal 5 arcsec FWHM, second crystal 3 arcsec FWHM",
            "published_peak_efficiency_range": "0.37 at 200 keV rising to 0.43 at 500 keV for monochromatic zero-divergence photons",
            "measured_double_to_single_ratio_range": "0.27-0.31 before absorption correction; 0.31-0.36 after absorption correction",
        },
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out_dir / "benchmark.csv").open("w", newline="") as f:
        fields = list(rows[0])
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
