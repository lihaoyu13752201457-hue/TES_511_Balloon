#!/usr/bin/env python3
"""Unit and frozen-plan tests for batch0006 validation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPAIR_ROOT = PACKAGE_ROOT.parent
ROOT = REPAIR_ROOT.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "code"))

import validate_m05_campaign_batch0006 as campaign  # noqa: E402


class SeedTests(unittest.TestCase):
    def test_recursive_seed_evidence_excludes_metadata(self) -> None:
        payload = {
            "seed_registry": {
                "instant": 101,
                "buildup": 102,
                "seed_base": 900,
                "seed_stride": 7,
                "planned_seed_count": 2,
                "planned_seed_list_sha256": "0" * 64,
            },
            "statistics": {"jobs": [{"seed": 103}, {"paired_seed": 104}]},
            "frozen_planned_seeds": [105, 106],
        }
        evidence = campaign.extract_seed_evidence(payload)
        self.assertEqual(set(evidence), {101, 102, 103, 104, 105, 106})
        self.assertNotIn(900, evidence)
        self.assertNotIn(7, evidence)

    def test_fresh_seed_is_stable_unique_and_collision_safe(self) -> None:
        identity = ("stage00", "instant", "gamma", 1)
        first = campaign.derive_fresh_seed(identity, set())
        self.assertEqual(first, campaign.derive_fresh_seed(identity, set()))
        replacement = campaign.derive_fresh_seed(identity, {first})
        self.assertNotEqual(first, replacement)
        plan = campaign.derive_fresh_seed_plan(["a", "b", "c", "a"], {first})
        self.assertEqual(len(plan), len(set(plan)))
        self.assertTrue(all(1 <= value <= 2_147_483_646 for value in plan))


class PlanTests(unittest.TestCase):
    def test_frozen_csv_plans_close(self) -> None:
        report = campaign.validate_plan_files(
            PACKAGE_ROOT / "seven_family_allocation.csv",
            PACKAGE_ROOT / "smoke_matrix.csv",
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["seven_family"]["total_events"], 6_001_652)
        self.assertEqual(report["smoke"]["total_events"], 55_424)
        self.assertEqual(report["smoke"]["total_shards"], 100)

    def test_changed_allocation_fails(self) -> None:
        rows = campaign.read_csv_rows(PACKAGE_ROOT / "seven_family_allocation.csv")
        rows[0] = dict(rows[0])
        rows[0]["stage10_point_events"] = str(int(rows[0]["stage10_point_events"]) + 1)
        with self.assertRaises(campaign.CampaignValidationError):
            campaign.validate_seven_family_rows(rows)


class SourcePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_path = (
            REPAIR_ROOT / "config/source_cards/mass_model_511/Background_gamma_fullsphere20.source"
        )
        self.source = self.source_path.read_text(encoding="utf-8")

    def test_exact_instant_and_buildup_patch(self) -> None:
        kwargs = {
            "seed": 1_234_567,
            "events": 3334,
            "sim_prefix": "/tmp/batch0006/test_sim",
            "isotope_prefix": "/tmp/batch0006/test_dat",
        }
        instant = campaign.patch_source_exact(self.source, mode="instant", **kwargs)
        buildup = campaign.patch_source_exact(self.source, mode="buildup", **kwargs)
        self.assertIn("Seed 1234567\n", instant)
        self.assertIn(".Events 3334\n", instant)
        self.assertNotIn("DecayMode", instant)
        self.assertEqual(buildup.count("DecayMode ActivationBuildUp"), 1)
        campaign.verify_source_patch_exact(self.source, instant, mode="instant", **kwargs)
        with self.assertRaises(campaign.CampaignValidationError):
            campaign.verify_source_patch_exact(
                self.source, instant.replace("Seed 1234567", "Seed 1234568"), mode="instant", **kwargs
            )

    def test_duplicate_control_fails_closed(self) -> None:
        with self.assertRaises(campaign.CampaignValidationError):
            campaign.patch_source_exact(
                self.source + "Seed 9\n",
                seed=1,
                events=1,
                sim_prefix="sim",
                isotope_prefix="dat",
                mode="instant",
            )


class DecisionAndResourceGateTests(unittest.TestCase):
    def test_compact_defaults_to_f_only(self) -> None:
        fallback = campaign.decide_compact_arm(None)
        self.assertEqual(fallback["selected_launch_path"], "F_ONLY")
        authority = {
            "batch_id": campaign.BATCH_ID,
            "transport_authorized": True,
            "scope": "MATCHED_F_C_STAGE00_ALL_32_CELLS",
            "errors": [],
        }
        selected = campaign.decide_compact_arm(
            authority, authorization_is_write_once=True, preflight_elapsed_s=120
        )
        self.assertEqual(selected["selected_launch_path"], "MATCHED_F_C")
        late = campaign.decide_compact_arm(
            authority, authorization_is_write_once=True, preflight_elapsed_s=1201
        )
        self.assertEqual(late["selected_launch_path"], "F_ONLY")

    def test_disk_gate_uses_decimal_campaign_and_binary_filesystem_reserves(self) -> None:
        free = 106_437_652_480
        self.assertEqual(campaign.campaign_cap_at_t0(free), 84_962_816_000)
        passed = campaign.disk_launch_gate(
            stage="stage10",
            campaign_bytes=1_000_000_000,
            active_declared_caps_bytes=1_500_000_000,
            candidate_declared_cap_bytes=1_500_000_000,
            campaign_cap_bytes=84_962_816_000,
            filesystem_free_bytes=100_000_000_000,
        )
        self.assertEqual(passed["status"], "PASS")
        failed = campaign.disk_launch_gate(
            stage="stage20",
            campaign_bytes=80_000_000_001,
            active_declared_caps_bytes=0,
            candidate_declared_cap_bytes=0,
            campaign_cap_bytes=85_000_000_000,
            filesystem_free_bytes=100_000_000_000,
        )
        self.assertEqual(failed["status"], "FAIL_STOP_LAUNCH")

    def test_rss_gate_is_strict_and_calibrates_parallelism(self) -> None:
        one = campaign.rss_launch_gate(
            stage="stage20",
            mem_available_bytes=8 * 1024**3,
            active_p95_rss_upper_bytes=[],
            candidate_p95_rss_upper_bytes=4 * 1024**3,
            workers_after_launch=1,
            completed_same_arm_receipts=0,
        )
        self.assertEqual(one["status"], "PASS")
        early_two = campaign.rss_launch_gate(
            stage="stage20",
            mem_available_bytes=12 * 1024**3,
            active_p95_rss_upper_bytes=[4 * 1024**3],
            candidate_p95_rss_upper_bytes=4 * 1024**3,
            workers_after_launch=2,
            completed_same_arm_receipts=7,
        )
        self.assertEqual(early_two["status"], "FAIL_STOP_LAUNCH")
        calibrated_two = campaign.rss_launch_gate(
            stage="stage20",
            mem_available_bytes=12 * 1024**3 + 1,
            active_p95_rss_upper_bytes=[4 * 1024**3],
            candidate_p95_rss_upper_bytes=4 * 1024**3,
            workers_after_launch=2,
            completed_same_arm_receipts=8,
        )
        self.assertEqual(calibrated_two["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
