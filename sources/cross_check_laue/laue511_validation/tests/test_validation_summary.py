from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from laue511.validation_summary import _external_lens_curve_check, build_validation_manifest


ROOT = Path(__file__).resolve().parents[1]


class ValidationSummaryTest(unittest.TestCase):
    def test_manifest_reports_current_crosscheck_status(self) -> None:
        manifest = build_validation_manifest(ROOT)
        self.assertEqual(manifest["status"], "crosscheck_pass_external_lens_observables_imported")
        self.assertFalse(manifest["production_validation_ready"])
        self.assertTrue(manifest["checks"]["cosima_bridge_diffract"]["ok"])
        self.assertTrue(manifest["checks"]["external_lens_handoff"]["ok"])
        self.assertTrue(manifest["checks"]["external_lens_handoff"]["work_dir_removed"])
        self.assertTrue(manifest["checks"]["full_lens_observables"]["ok"])
        self.assertTrue(manifest["checks"]["python_full_lens_reference"]["ok"])
        self.assertTrue(manifest["checks"]["opticsim_table_lens_closure"]["ok"])
        self.assertTrue(manifest["checks"]["crystalpy_curve"]["ok"])
        self.assertTrue(manifest["checks"]["xop_crystal_curve"]["ok"])
        self.assertTrue(manifest["checks"]["external_lens_import_ready"]["ok"])
        self.assertEqual(manifest["checks"]["external_lens_import_ready"]["status"], "ready")
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["ok"])
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["comparison_targets_ok"])
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["request_rings_ok"])
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["rings_csv_ok"])
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["tiles_csv_ok"])
        self.assertTrue(manifest["checks"]["external_lens_request_ready"]["heart_adapter_ok"])
        self.assertEqual(
            manifest["artifacts"]["external_lens_tile_table"],
            "benchmarks/reference_outputs/external_lens_oracle_tiles.csv",
        )
        self.assertEqual(
            manifest["artifacts"]["heart_independent_plane_normal_patch"],
            "benchmarks/reference_outputs/heart_independent_plane_normal.patch",
        )
        self.assertEqual(manifest["checks"]["external_lens_curve"]["status"], "imported")
        self.assertTrue(manifest["checks"]["external_lens_curve"]["ok"])
        self.assertEqual(
            manifest["artifacts"]["heart_patched_full_lens_guan_direction_hdf5"],
            "benchmarks/reference_outputs/heart_patched_full_lens_guan_direction.h5",
        )
        self.assertEqual(
            manifest["artifacts"]["external_lens_observables"],
            "benchmarks/reference_outputs/external_lens_observables",
        )
        self.assertEqual(manifest["checks"]["bfull_rocking_curve_map_status"]["status"], "ready")
        self.assertEqual(manifest["checks"]["bfull_rocking_curve_map_status"]["covered_ring_ids"], [0, 1, 2, 3, 4])
        self.assertEqual(manifest["checks"]["bfull_rocking_curve_map_status"]["missing_ring_ids"], [])
        self.assertTrue(manifest["checks"]["bfull_offaxis_scan"]["all_process_base_g4vemprocess"])
        self.assertTrue(manifest["checks"]["bfull_single_tile_xop_scan"]["all_process_base_g4vemprocess"])
        self.assertTrue(manifest["checks"]["bfull_offaxis_scan"]["all_transmitted_space_rows_match_summary"])
        self.assertTrue(manifest["checks"]["bfull_single_tile_xop_scan"]["all_transmitted_space_rows_match_summary"])
        self.assertEqual(manifest["checks"]["bfull_full_lens_xop_map_scan"]["status"], "imported")
        self.assertTrue(manifest["checks"]["bfull_full_lens_xop_map_scan"]["all_per_ring_sources_external"])
        self.assertTrue(manifest["checks"]["bfull_full_lens_xop_map_scan"]["all_registered_in_geant4_em_category"])
        self.assertTrue(manifest["checks"]["bfull_full_lens_xop_map_scan"]["all_process_base_g4vemprocess"])
        self.assertTrue(manifest["checks"]["bfull_full_lens_xop_map_scan"]["all_transmitted_space_rows_match_summary"])

    def test_external_lens_curve_check_recognizes_imported_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "benchmarks/reference_outputs"
            summary_dir = root / "external_lens_observables"
            summary_dir.mkdir(parents=True)
            status = root / "EXTERNAL_SOURCE_STATUS.md"
            status.write_text("# status\n", encoding="utf-8")
            summary = summary_dir / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "n_rows": 2,
                        "source_tools": ["unit"],
                        "source_versions": ["0"],
                        "lens_metrics": {"diffracted_area_cm2": 0.57, "spot_d90_cm": 0.22},
                        "comparison": {
                            "diffracted_area_minus_current_observed_cm2": 0.001,
                            "spot_d90_minus_current_observed_cm": 0.002,
                        },
                    }
                ),
                encoding="utf-8",
            )
            check = _external_lens_curve_check(summary, status)
            self.assertTrue(check["ok"])
            self.assertEqual(check["status"], "imported")
            self.assertAlmostEqual(check["diffracted_area_cm2"], 0.57)

    def test_external_lens_curve_check_recognizes_failed_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "benchmarks/reference_outputs"
            summary_dir = root / "external_lens_observables"
            summary_dir.mkdir(parents=True)
            status = root / "EXTERNAL_SOURCE_STATUS.md"
            status.write_text("# status\n", encoding="utf-8")
            summary = summary_dir / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "n_rows": 2,
                        "source_tools": ["unit"],
                        "source_versions": ["0"],
                        "lens_metrics": {"diffracted_area_cm2": 0.80, "spot_d90_cm": 0.50},
                        "comparison": {
                            "diffracted_area_minus_current_observed_cm2": 0.23,
                            "spot_d90_minus_current_observed_cm": 0.28,
                        },
                    }
                ),
                encoding="utf-8",
            )
            check = _external_lens_curve_check(summary, status)
            self.assertFalse(check["ok"])
            self.assertEqual(check["status"], "needs_attention")


if __name__ == "__main__":
    unittest.main()
