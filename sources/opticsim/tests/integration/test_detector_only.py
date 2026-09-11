from __future__ import annotations

import csv
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from external_baseline.detector_response_py.detector_response import load_detector_config, run_detector_only


class DetectorOnlyIntegrationTest(unittest.TestCase):
    def test_perfect_detector_response_on_synthetic_phase_space(self) -> None:
        base = load_detector_config("config/detector_tes_bgo.yaml")
        cfg = replace(
            base,
            absorber=replace(base.absorber, stack_detection_efficiency=1.0),
            tes=replace(
                base.tes,
                reconstructed_resolution_fwhm_eV_at_511=0.0,
                full_energy_peak_fraction=1.0,
                multihit_fraction=0.0,
            ),
            bgo=replace(base.bgo, enabled=False, signal_self_veto_probability=0.0, passthrough_detection_probability=0.0),
        )
        rows = [
            (0, 0.0, 0.0),
            (1, 14.49, 0.0),
            (2, 20.0, 0.0),
            (3, -14.49, -14.49),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "phase_space.csv"
            with source.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["event_id", "E_keV", "x_mm", "y_mm", "z_mm", "ux", "uy", "uz", "weight", "source_tag"])
                for event_id, x_mm, y_mm in rows:
                    writer.writerow([event_id, 511.0, x_mm, y_mm, 12000.0, 0.0, 0.0, 1.0, 1.0, "test_source"])
            summary = run_detector_only(cfg, source, tmp_path / "out", seed=7)

        self.assertEqual(summary["n_input_photons"], 4)
        self.assertEqual(summary["n_inside_active_pixel"], 3)
        self.assertEqual(summary["n_tes_detected"], 3)
        self.assertEqual(summary["n_selected_line_window"], 3)
        self.assertAlmostEqual(summary["geometric_acceptance"], 0.75)
        self.assertAlmostEqual(summary["line_window_fraction_of_unvetoed_detected"], 1.0)


if __name__ == "__main__":
    unittest.main()
