from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "engineering/particle_source_unit_repair_20260811/code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import run_mergeable_two_geometry_seven_family_batch0001 as campaign  # noqa: E402
import validate_mergeable_two_geometry_seven_family_batch0001 as validator  # noqa: E402


def load_shared_runner():
    spec = importlib.util.spec_from_file_location("shared_equiv_runner_for_batch0001_test", campaign.RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SevenFamilyBatch0001ContractTests(unittest.TestCase):
    def test_exact_seven_family_statistics(self) -> None:
        expected = {
            "alpha": 239,
            "eminus": 4_146,
            "eplus": 2_437,
            "gamma": 100_000,
            "muminus": 104,
            "muplus": 116,
            "n": 9_631,
        }
        for source_dir in campaign.GEOMETRIES.values():
            self.assertEqual(campaign.expected_events_by_family(source_dir), expected)
        self.assertEqual(sum(expected.values()), 116_673)
        self.assertNotIn("p", campaign.FAMILIES)
        self.assertEqual(campaign.EXPECTED_JOBS_PER_CAMPAIGN, 10)

    def test_seed_registry_is_explicit_and_disjoint(self) -> None:
        prior = json.loads(campaign.PRIOR_LEDGER.read_text(encoding="utf-8"))
        prior_seeds = campaign.prior_seed_registry(prior)
        instant = set(campaign.expected_seeds("instant"))
        buildup = set(campaign.expected_seeds("buildup"))
        self.assertEqual(len(instant), 10)
        self.assertEqual(len(buildup), 10)
        self.assertTrue(instant.isdisjoint(buildup))
        self.assertTrue((instant | buildup).isdisjoint(prior_seeds))
        self.assertLess(max(instant | buildup), campaign.RESERVED_FULL_TARGET_SEED_START)

    def test_validator_job_contract_matches_shared_runner(self) -> None:
        runner = load_shared_runner()
        for mode in campaign.MODES:
            for geometry, source_dir in campaign.GEOMETRIES.items():
                args = argparse.Namespace(
                    source_dir=source_dir.resolve(),
                    outdir=Path("/tmp") / f"batch0001-contract-test-{geometry}-{mode}",
                    mode=mode,
                    gamma_events=campaign.GAMMA_EVENTS,
                    gamma_splits=campaign.GAMMA_SPLITS,
                    non_gamma_replicas=campaign.NON_GAMMA_REPLICAS,
                    particles=",".join(campaign.FAMILIES),
                    farfield_radius_cm=campaign.FARFIELD_RADIUS_CM,
                    seed_base=campaign.SEED_BASE_BY_MODE[mode],
                    seed_stride=campaign.SEED_STRIDE,
                    cosima="/nonexecuted/cosima",
                    force=False,
                    keep_sources=True,
                    disable_isotope_store=False,
                    max_jobs=None,
                )
                jobs, normalization = runner.build_jobs(args)
                expected = validator.expected_jobs(source_dir, mode)
                observed = {
                    job["job_name"]: {
                        "family": job["particle"],
                        "events": job["events"],
                        "rep": job["rep"],
                        "part": job["part"],
                        "seed": job["seed"],
                    }
                    for job in jobs
                }
                projected = {
                    name: {key: row[key] for key in ("family", "events", "rep", "part", "seed")}
                    for name, row in expected.items()
                }
                self.assertEqual(observed, projected)
                self.assertEqual(normalization["selected_particles"], sorted(campaign.FAMILIES))
                self.assertNotIn("p", normalization["selected_particles"])

    def test_estimator_uses_only_hash_pinned_corrected_smoke(self) -> None:
        prior = json.loads(campaign.PRIOR_LEDGER.read_text(encoding="utf-8"))
        estimate = campaign.build_corrected_smoke_estimates(prior)
        self.assertIn("corrected-keV", estimate["authority"])
        self.assertIn("legacy _2602units estimator is forbidden", estimate["authority"])
        self.assertEqual(len(estimate["campaigns"]), 4)
        self.assertGreater(estimate["point_estimated_output_bytes"], 0)
        self.assertEqual(
            estimate["gated_output_bytes"],
            estimate["point_estimated_output_bytes"] * campaign.DISK_SAFETY_FACTOR,
        )
        for item in estimate["campaigns"]:
            self.assertIn("mergeable_smoke_v1/run_summary.csv", item["smoke_summary_csv"])
            self.assertNotIn("2602units", item["smoke_summary_csv"])
            self.assertEqual(len(item["by_family"]), 7)

    def test_selected_cards_are_corrected_kev(self) -> None:
        for source_dir in campaign.GEOMETRIES.values():
            for family in campaign.FAMILIES:
                text = (source_dir / f"Background_{family}_fullsphere20.source").read_text(encoding="utf-8")
                self.assertNotIn("cosima_spectra_dp_2602units", text)
                self.assertEqual(
                    text.count(
                        "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
                    ),
                    20,
                )


if __name__ == "__main__":
    unittest.main()
