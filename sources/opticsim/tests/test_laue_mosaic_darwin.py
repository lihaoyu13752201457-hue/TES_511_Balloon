from __future__ import annotations

import unittest

from external_baseline.laue_raytrace_py.mosaic_darwin import (
    darwin_mosaic_probabilities,
    d_spacing_A,
    optimal_mosaic_thickness_mm,
)


class LaueMosaicDarwinTest(unittest.TestCase):
    def test_au_benchmarks_match_barriere_2009_table4(self) -> None:
        cases = [
            (299.0, 30.0, 46.0, 0.47, 0.12),
            (399.0, 24.0, 52.0, 0.47, 0.22),
            (494.0, 24.0, 57.0, 0.46, 0.26),
            (588.0, 18.0, 65.0, 0.45, 0.29),
        ]
        for energy, mosaic, crystallite, expected_eff, expected_reflectivity in cases:
            with self.subTest(energy=energy):
                result = darwin_mosaic_probabilities(
                    energy_keV=energy,
                    material="Au",
                    h=1,
                    k=1,
                    l=1,
                    mosaic_fwhm_arcsec=mosaic,
                    thickness_mm=2.0,
                    crystallite_thickness_um=crystallite,
                )
                self.assertAlmostEqual(result.diffraction_efficiency_no_abs, expected_eff, delta=0.03)
                self.assertAlmostEqual(result.p_diff, expected_reflectivity, delta=0.03)

    def test_cu_benchmarks_match_barriere_2009_table2(self) -> None:
        cases = [
            (299.0, 25.0, 3.0, 60.0, 0.46, 0.34),
            (589.0, 14.0, 9.0, 129.0, 0.47, 0.26),
        ]
        for energy, mosaic, thickness, crystallite, expected_eff, expected_reflectivity in cases:
            with self.subTest(energy=energy):
                result = darwin_mosaic_probabilities(
                    energy_keV=energy,
                    material="Cu",
                    h=1,
                    k=1,
                    l=1,
                    mosaic_fwhm_arcsec=mosaic,
                    thickness_mm=thickness,
                    crystallite_thickness_um=crystallite,
                )
                self.assertAlmostEqual(result.diffraction_efficiency_no_abs, expected_eff, delta=0.03)
                self.assertAlmostEqual(result.p_diff, expected_reflectivity, delta=0.03)

    def test_ge111_500kev_optimum_is_in_reported_ge_efficiency_band(self) -> None:
        thickness_mm = optimal_mosaic_thickness_mm(
            energy_keV=500.0,
            material="Ge",
            h=1,
            k=1,
            l=1,
            mosaic_fwhm_arcsec=30.0,
            crystallite_thickness_um=5.0,
        )
        result = darwin_mosaic_probabilities(
            energy_keV=500.0,
            material="Ge",
            h=1,
            k=1,
            l=1,
            mosaic_fwhm_arcsec=30.0,
            thickness_mm=thickness_mm,
            crystallite_thickness_um=5.0,
        )
        self.assertAlmostEqual(d_spacing_A("Ge", 1, 1, 1), 3.2666, places=3)
        self.assertGreaterEqual(result.p_diff, 0.20)
        self.assertLessEqual(result.p_diff, 0.31)

    def test_probabilities_sum_to_one(self) -> None:
        result = darwin_mosaic_probabilities(
            energy_keV=511.0,
            material="Ge",
            h=1,
            k=1,
            l=1,
            mosaic_fwhm_arcsec=30.0,
            thickness_mm=10.0,
            crystallite_thickness_um=5.0,
            delta_theta_rad=1.0e-4,
        )
        self.assertAlmostEqual(result.p_diff + result.p_abs + result.p_trans, 1.0, places=12)
        self.assertGreaterEqual(result.p_diff, 0.0)
        self.assertGreaterEqual(result.p_abs, 0.0)
        self.assertGreaterEqual(result.p_trans, 0.0)


if __name__ == "__main__":
    unittest.main()
