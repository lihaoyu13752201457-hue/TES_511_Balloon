import importlib.util
import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[1] / "code/analyze_composite_partial.py"
SPEC = importlib.util.spec_from_file_location("composite_partial_test_target", MODULE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class CompositePartialTests(unittest.TestCase):
    def test_pass_ledger_rounded_zero_neutron_energy_is_valid(self):
        self.assertTrue(mod._valid_printed_init_energy(0.0))
        self.assertTrue(mod._valid_printed_init_energy(1.0))
        self.assertFalse(mod._valid_printed_init_energy(-1.0))

    def test_exact_authority_snapshot_is_partial(self):
        snap = mod.build_authority_snapshot()
        self.assertEqual(snap["status"], "PASS__COMPOSITE_PARTIAL_AUTHORITIES_PINNED")
        self.assertFalse(snap["batch0004_final_authority_present"])
        self.assertTrue(snap["batch0005_is_addon_only"])
        self.assertEqual(len(snap["authorities"]), 9)

    def test_real_metadata_has_28_nonempty_separate_cells(self):
        mod.pin_authorities()
        jobs, _, _ = mod.collect_jobs()
        self.assertEqual(len(jobs), 28)
        self.assertTrue(all(rows for rows in jobs.values()))
        coverage = mod.coverage_rows(jobs)
        self.assertEqual(len(coverage), 28)
        self.assertTrue(all(row["data_present"] for row in coverage))

    def test_partial_targets_are_null_not_zero_when_not_applicable(self):
        mod.pin_authorities()
        jobs, _, _ = mod.collect_jobs()
        gamma_instant = next(
            row for row in mod.coverage_rows(jobs)
            if row["geometry"] == "mass_model_511"
            and row["family"] == "gamma" and row["mode"] == "instant"
        )
        self.assertIsNone(gamma_instant["batch0004_screening_reference_events"])
        self.assertIsNone(gamma_instant["screening_reference_fraction"])
        self.assertGreater(gamma_instant["observed_primary_count"], 0)


if __name__ == "__main__":
    unittest.main()
