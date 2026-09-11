from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from external_baseline.io_contract_py.io_contract import validate_phase_space, validate_run_contract


class IOContractTest(unittest.TestCase):
    def test_phase_space_contract_accepts_valid_primary_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phase_space.csv"
            with path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["event_id", "E_keV", "x_mm", "y_mm", "z_mm", "ux", "uy", "uz", "weight", "source_tag"])
                writer.writerow([1, 511.0, 0.0, 0.0, 12000.0, 0.0, 0.0, 1.0, 1.0, "unit"])
            result = validate_phase_space(path)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.n_rows, 1)

    def test_detector_crosslinks_reject_mismatched_pixel_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            phase = tmp_path / "phase_space.csv"
            hits = tmp_path / "hits.csv"
            events = tmp_path / "event_summary.csv"
            optics = tmp_path / "optics_history.csv"
            with phase.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["event_id", "E_keV", "x_mm", "y_mm", "z_mm", "ux", "uy", "uz", "weight", "source_tag"])
                writer.writerow([1, 511.0, 0.0, 0.0, 12000.0, 0.0, 0.0, 1.0, 1.0, "unit"])
            with optics.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "event_id",
                        "track_id",
                        "optics_kind",
                        "stage",
                        "ring_id",
                        "tile_id",
                        "surface_id",
                        "E_keV",
                        "x_mm",
                        "y_mm",
                        "z_mm",
                        "ux_in",
                        "uy_in",
                        "uz_in",
                        "ux_out",
                        "uy_out",
                        "uz_out",
                        "grazing_angle_rad",
                        "p_reflect",
                        "p_absorb",
                        "p_transmit",
                        "n_bounce",
                        "weight",
                    ]
                )
                writer.writerow([1, 1, "CHANNEL", "EXIT", 0, -1, "surface", 511.0, 0, 0, 12000, 0, 0, 1, 0, 0, 1, "", 1, 0, 0, 1, 1])
            with hits.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "event_id",
                        "track_id",
                        "detector_kind",
                        "layer_id",
                        "pixel_i",
                        "pixel_j",
                        "pixel_uid",
                        "x_mm",
                        "y_mm",
                        "z_mm",
                        "edep_keV",
                        "process_name",
                        "time_ns",
                    ]
                )
                writer.writerow([1, 1, "TES_PIXEL", 0, 10, 10, "L00_I10_J10", 0, 0, 12000, 511.0, "unit", 0.0])
            with events.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "event_id",
                        "total_tes_edep_keV",
                        "n_tes_pixel_hits",
                        "is_singlehit",
                        "is_multihit",
                        "bgo_edep_keV",
                        "bgo_veto",
                        "reco_energy_keV",
                        "weight",
                    ]
                )
                writer.writerow([1, 511.0, 0, 1, 0, 0.0, 0, 511.0, 1.0])
            report = validate_run_contract(phase, optics, hits, events)

        self.assertFalse(report["ok"])
        detector_crosslinks = next(result for result in report["results"] if result["table"] == "detector_crosslinks")
        self.assertIn("n_tes_pixel_hits", detector_crosslinks["errors"][0])


if __name__ == "__main__":
    unittest.main()
