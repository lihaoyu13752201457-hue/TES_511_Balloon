from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "engineering/particle_source_unit_repair_20260811/code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import run_mergeable_muminus_instant_pair_batch0002 as batch  # noqa: E402


class MuminusInstantPairBatch0002ContractTests(unittest.TestCase):
    def test_fixed_scope(self) -> None:
        self.assertEqual(batch.MODE, "instant")
        self.assertEqual(batch.FAMILY, "muminus")
        self.assertEqual(batch.EVENTS, 10_000)
        self.assertEqual(set(batch.GEOMETRIES), {"mass_model_511", "s3d_o8"})

    def test_seed_collector_accepts_standard_and_compatibility_schema(self) -> None:
        jobs_only = {"campaigns": [{"jobs": [{"seed": 101}]}]}
        job_only = {"campaigns": [{"job": {"seed": 202}}]}
        both = {"campaigns": [{"jobs": [{"seed": 303}], "job": {"seed": 303}}]}
        self.assertEqual(batch._prior_seeds(jobs_only, job_only, both), {101, 202, 303})

    def test_batch0002_seed_is_disjoint_from_bound_ledgers(self) -> None:
        ledger0 = batch._load_json(batch.BATCH0000_LEDGER)
        ledger1 = batch._load_json(batch.BATCH0001_LEDGER)
        self.assertNotIn(batch.SEED, batch._prior_seeds(ledger0, ledger1))


if __name__ == "__main__":
    unittest.main()
