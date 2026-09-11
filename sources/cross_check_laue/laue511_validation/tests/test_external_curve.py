from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from laue511.external_curve import convert_diffpat_to_external_curve, import_external_curve, summarize_external_curve


class ExternalCurveTest(unittest.TestCase):
    def test_import_valid_external_curve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            curve = tmp_path / "curve.csv"
            _write_curve(curve)
            summary = import_external_curve(
                curve,
                tmp_path / "xop_crystal",
                energy_keV=511.0,
                d_spacing_A=3.266590088,
                thickness_mm=10.218801,
            )
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["n_rows"], 3)
            self.assertTrue((tmp_path / "xop_crystal/ge111_511keV_rocking_curve.csv").exists())

    def test_missing_columns_fail_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("delta_theta_rad,reflectivity\n0,0.2\n", encoding="utf-8")
            summary = summarize_external_curve(path, energy_keV=511.0, d_spacing_A=3.266590088, thickness_mm=10.218801)
            self.assertFalse(summary["ok"])
            self.assertIn("missing columns", summary["errors"][0])

    def test_convert_diffpat_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dat = tmp_path / "diff_pat.dat"
            par = tmp_path / "diff_pat.par"
            out = tmp_path / "curve.csv"
            dat.write_text(
                "\n".join(
                    [
                        "#L  Th-ThB{in} [arcsec]  Th-ThB{out} [arcsec]  phase_p[rad]  phase_s[rad]  Circ Polariz  p-polarized  s-polarized",
                        " -6.0000000 -6.0000000 0 0 0 0.24479682 0.24480329",
                        "  0.0000000  0.0000000 0 0 0 0.25747813 0.25748432",
                        "  6.0000000  6.0000000 0 0 0 0.24479682 0.24480329",
                    ]
                ),
                encoding="utf-8",
            )
            par.write_text(
                "\n".join(
                    [
                        "            **  DIFF_PAT  v1.8  (24 Mar 2014) **",
                        " Absorption coeff =   0.39751335887816963       cm^-1",
                        " Gamma0 =  VIN_BRAGG(3) =  -0.99999310240931960",
                    ]
                ),
                encoding="utf-8",
            )
            conversion = convert_diffpat_to_external_curve(dat, out, thickness_mm=10.218801, diffpat_par=par)
            summary = summarize_external_curve(out, energy_keV=511.0, d_spacing_A=3.266590088, thickness_mm=10.218801)
            self.assertEqual(conversion["n_rows"], 3)
            self.assertTrue(summary["ok"], summary)
            self.assertAlmostEqual(summary["peak_reflectivity"], 0.257481225)


def _write_curve(path: Path) -> None:
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
        writer.writerow({"delta_theta_rad": -1.0e-6, "reflectivity": 0.20, "transmittivity": 0.44, "absorption": 0.36, "source_tool": "unit", "source_version": "0"})
        writer.writerow({"delta_theta_rad": 0.0, "reflectivity": 0.25, "transmittivity": 0.39, "absorption": 0.36, "source_tool": "unit", "source_version": "0"})
        writer.writerow({"delta_theta_rad": 1.0e-6, "reflectivity": 0.20, "transmittivity": 0.44, "absorption": 0.36, "source_tool": "unit", "source_version": "0"})


if __name__ == "__main__":
    unittest.main()
