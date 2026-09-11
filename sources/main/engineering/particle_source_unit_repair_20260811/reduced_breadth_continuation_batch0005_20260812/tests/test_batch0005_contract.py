#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[4]
RUNNER = pathlib.Path(__file__).resolve().parents[1] / "code/run_reduced_breadth_continuation_batch0005.py"
SPEC = importlib.util.spec_from_file_location("batch0005_runner_test", RUNNER)
batch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(batch)


class Batch0005ContractTests(unittest.TestCase):
    def test_fixed_reduced_schedule(self):
        self.assertEqual(len(batch.STAGE_SPECS), 7)
        self.assertEqual(batch.FINAL_SHARD_COUNT, 8)
        self.assertEqual(batch.FINAL_JOB_COUNT, 16)
        self.assertEqual(batch.TOTAL_NEW_EVENTS, 27_340)
        self.assertEqual(batch.STAGE_BY_KEY["alpha_instant"]["shard_events"], [250, 149])

    def test_worker_disk_deadline_boundaries(self):
        self.assertEqual(batch.DEFAULT_WORKERS, 2)
        self.assertEqual(batch.MAX_WORKERS, 2)
        self.assertEqual(batch.DISK_RESERVE_BYTES, 20 * 1024**3)
        self.assertEqual(batch.STOP_LAUNCH_RESERVE_SECONDS, 1800)
        self.assertEqual(batch.VALIDATION_RESERVE_SECONDS, 1800)

    def test_batch0004_partial_and_all_planned_seeds_are_bound(self):
        authority = batch._validate_batch0004_partial_authority()
        self.assertEqual(authority["registered_planned_seed_count"], 127)
        new = {batch.shard_seed(i) for i in range(1, batch.FINAL_SHARD_COUNT + 1)}
        self.assertTrue(new.isdisjoint(authority["registered_planned_seeds"]))

    def test_corrected_only_cells(self):
        self.assertEqual(set(batch.FAMILIES), {"alpha", "eminus", "muplus", "muminus"})
        for stage in batch.STAGE_SPECS:
            self.assertEqual(stage["prior_events_per_geometry"], 0)
            for geometry in batch.GEOMETRIES:
                text = batch.source_card_path(geometry, stage["family"]).read_text()
                spectrum_lines = [line for line in text.splitlines() if ".Spectrum File" in line]
                self.assertEqual(len(spectrum_lines), 20)
                self.assertTrue(all("correct_keV_total" in line for line in spectrum_lines))
                self.assertNotIn("cosima_spectra_dp_2602units", text)

    def test_does_not_target_frozen_batch0004_outputs(self):
        self.assertIn("batch0005", str(batch.GLOBAL_CONTRACT))
        self.assertNotIn("batch0004", str(batch.GLOBAL_CONTRACT))
        for stage in batch.STAGE_SPECS:
            for geometry in batch.GEOMETRIES:
                self.assertIn("batch0005", str(batch.campaign_dir(geometry, stage["key"])))

    def test_checkpoint_addon_and_composite_semantics_are_unambiguous(self):
        alpha = batch.STAGE_COMPOSITE_ACCOUNTING["alpha_instant"]
        self.assertEqual(alpha, {
            "before": 1991, "batch0005_addon": 399, "after": 2390, "target": 2390,
        })
        self.assertEqual(batch.STAGE_COMPOSITE_ACCOUNTING["alpha_buildup"]["after"], 491)
        self.assertEqual(batch.STAGE_COMPOSITE_ACCOUNTING["eminus_instant"]["after"], 9187)
        validator = (RUNNER.parent / "validate_reduced_breadth_continuation_batch0005.py").read_text()
        stage_body = validator.split("def validate_stage", 1)[1].split("def _write_stage", 1)[0]
        self.assertNotIn('"cumulative_target_events_per_geometry"', stage_body)
        self.assertNotIn('"cumulative_events"', stage_body)
        self.assertIn('"authority_scope": "batch0005_addon_only"', stage_body)


if __name__ == "__main__":
    unittest.main()
