#!/usr/bin/env python3
"""Pure/read-only tests for the recovery0004 scheduler."""

from __future__ import annotations

import unittest
from collections import deque
from pathlib import Path

import resume_m05_campaign_batch0006_recovery0004_live_memory_dynamic as r4


GIB = 1024**3


def evidence(upper: int = GIB) -> dict:
    return {
        "recent_classes": {
            "unknown/unknown/S3d_O8/eplus": {
                "recent_p95_upper_bytes": upper,
                "recent_max_bytes": upper,
            }
        },
        "all_time_audit_only": {},
    }


def job(name: str = "j", geometry: str = "S3d_O8") -> dict:
    return {"job_id": name, "geometry": geometry, "family": "eplus"}


class DummyProcess:
    def __init__(self, pid: int):
        self.pid = pid


class Recovery0004Tests(unittest.TestCase):
    def test_global_limits_have_no_geometry_specific_cap(self) -> None:
        self.assertEqual(r4.NORMAL_TARGET_WORKERS, 6)
        self.assertEqual(r4.ABSOLUTE_MAX_WORKERS, 8)
        source = Path(r4.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "MAX_O8_WORKERS",
            "MAX_HEAVY_O8",
            "MAX_PROTON_WORKERS",
            "HISTORICAL_HEAVY_O8_RSS_BYTES",
        ):
            self.assertNotIn(forbidden, source)

    def test_target_raise_is_staggered_but_replacement_is_immediate(self) -> None:
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=4, target_workers=5, now=1,
                last_target_raise=0, last_launch=-100,
            ),
            (True, False),
        )
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=4, target_workers=5,
                now=r4.REPLACEMENT_STAGGER_S - 1,
                last_target_raise=0, last_launch=0,
            ),
            (False, False),
        )
        # A replacement launch updates last_launch; target promotion 0.5s later
        # must still wait the full 60-second promotion stagger.
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=5, target_workers=5, now=100.5,
                last_target_raise=0, last_launch=100,
            ),
            (False, False),
        )
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=5, target_workers=5,
                now=r4.LAUNCH_STAGGER_S, last_target_raise=0,
                last_launch=-100,
            ),
            (True, True),
        )
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=8, target_workers=8, now=10_000,
                last_target_raise=0, last_launch=-100,
            ),
            (False, False),
        )
        self.assertEqual(
            r4.launch_clock_decision(
                active_count=5, target_workers=5,
                now=r4.LAUNCH_STAGGER_S - 1, last_target_raise=0,
                last_launch=-100,
            ),
            (False, False),
        )

    def test_old_all_time_peak_is_audit_only(self) -> None:
        current = evidence(upper=700 * 1024**2)
        current["all_time_audit_only"] = {
            "classes": {
                "S3d_O8/eplus": {
                    "max_bytes": 5 * GIB,
                    "p95_upper_bytes": 5 * GIB,
                }
            }
        }
        upper = r4.class_upper_bytes(job(), current)
        self.assertLess(upper, 2 * GIB)

    def test_memavailable_projection_does_not_double_count_live_rss(self) -> None:
        candidate = job("candidate")
        worker = r4.Worker(
            job("active"), DummyProcess(101), None, "", 0.0
        )
        upper = r4.class_upper_bytes(candidate, evidence())
        actual = upper // 4
        result = r4.memory_projection(
            [worker], candidate, evidence(),
            available_bytes=6 * GIB, live_rss={101: actual},
        )
        self.assertEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - (upper - actual) - upper,
        )
        self.assertNotEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - actual - upper,
        )

    def test_live_rss_above_upper_is_not_subtracted_again(self) -> None:
        candidate = job("candidate")
        worker = r4.Worker(
            job("active"), DummyProcess(101), None, "", 0.0
        )
        upper = r4.class_upper_bytes(candidate, evidence())
        result = r4.memory_projection(
            [worker], candidate, evidence(),
            available_bytes=6 * GIB, live_rss={101: 2 * upper},
        )
        self.assertEqual(result["active_unrealised_growth_bytes"], 0)
        self.assertEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - result["candidate_class_upper_bytes"],
        )

    def test_soft_floor_and_resume_hysteresis(self) -> None:
        state = r4.HealthState()
        swap = {"growing": False}
        low = {
            "projected_mem_available_bytes":
                r4.SOFT_PROJECTED_FLOOR_BYTES - 1
        }
        self.assertFalse(
            r4.health_allows_launch(state, now=0, projection=low, swap=swap)[0]
        )
        high = {
            "projected_mem_available_bytes":
                r4.RESUME_PROJECTED_FLOOR_BYTES + 1
        }
        self.assertFalse(
            r4.health_allows_launch(state, now=1, projection=high, swap=swap)[0]
        )
        self.assertTrue(
            r4.health_allows_launch(
                state, now=1 + r4.RESUME_STABLE_S,
                projection=high, swap=swap,
            )[0]
        )

    def test_seventh_and_eighth_require_strong_surplus(self) -> None:
        state = r4.HealthState()
        projection = {
            "projected_mem_available_bytes":
                r4.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES + 1,
            "active": [{"live_rss_bytes": GIB}],
        }
        self.assertFalse(
            r4.strong_surplus_allows_launch(
                state, now=0, projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )
        self.assertFalse(
            r4.strong_surplus_allows_launch(
                state, now=1, projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )
        self.assertTrue(
            r4.strong_surplus_allows_launch(
                state, now=1 + r4.STRONG_SURPLUS_STABLE_S,
                projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )

    def test_strong_surplus_rejects_swap_psi_and_rss_growth(self) -> None:
        base = {
            "projected_mem_available_bytes":
                r4.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES + 1,
            "active": [{"live_rss_bytes": GIB}],
        }
        state = r4.HealthState()
        self.assertFalse(
            r4.strong_surplus_allows_launch(
                state, now=0, projection=base,
                swap={"growing": True}, psi_full_avg10=0,
            )[0]
        )
        state = r4.HealthState()
        self.assertFalse(
            r4.strong_surplus_allows_launch(
                state, now=0, projection=base,
                swap={"growing": False},
                psi_full_avg10=r4.STRONG_SURPLUS_MAX_PSI_FULL_AVG10 + 0.01,
            )[0]
        )
        grown = dict(base)
        grown["active"] = [{
            "live_rss_bytes": GIB + r4.STRONG_SURPLUS_MAX_RSS_GROWTH_BYTES + 1
        }]
        state = r4.HealthState(strong_rss_samples=deque([(0, GIB)]))
        self.assertFalse(
            r4.strong_surplus_allows_launch(
                state, now=r4.STRONG_SURPLUS_STABLE_S, projection=grown,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )

    def test_no_soft_preemption_or_extra_attempt_contract(self) -> None:
        source = Path(r4.__file__).read_text(encoding="utf-8")
        self.assertNotIn("emergency_withdraw_newest", source)
        self.assertNotIn("MAX_RESOURCE_ATTEMPTS", source)
        self.assertIn("range(1, campaign.MAX_ATTEMPTS + 1)", source)

    def test_swap_nonzero_but_flat_is_not_growth(self) -> None:
        used = 700_000
        self.assertFalse(
            r4.swap_growth([(0, used), (15, used), (31, used)])["growing"]
        )
        self.assertTrue(
            r4.swap_growth(
                [(0, used), (15, used + r4.SWAP_GROWTH_PAGES // 2),
                 (31, used + r4.SWAP_GROWTH_PAGES)]
            )["growing"]
        )

    def test_actual_fair_wave_preserves_frozen_plan(self) -> None:
        _contract, plan = r4.frozen_inputs()
        ordered = r4.fair_wave_jobs("stage10_seven_family", plan)
        original = [job for job in plan if job["stage"] == "stage10_seven_family"]
        self.assertEqual(len(ordered), len(original))
        self.assertEqual(
            {row["job_id"] for row in ordered},
            {row["job_id"] for row in original},
        )
        self.assertEqual(
            r4.campaign.json_sha256(plan),
            r4.campaign.load_json(r4.campaign.GLOBAL_CONTRACT)["planned_jobs_sha256"],
        )
        runs = []
        prior = None
        length = 0
        for row in ordered:
            geometry = row["geometry"]
            if geometry != prior:
                if length:
                    runs.append(length)
                prior, length = geometry, 1
            else:
                length += 1
        runs.append(length)
        self.assertLessEqual(max(runs), r4.FAIR_WAVE_SIZE)

    def test_stage20_preserves_frozen_round_robin_order(self) -> None:
        _contract, plan = r4.frozen_inputs()
        expected = [row for row in plan if row["stage"] == "stage20_proton"]
        self.assertEqual(r4.fair_wave_jobs("stage20_proton", plan), expected)

    def test_bounded_bypass_fills_light_work_then_honors_debt_barrier(self) -> None:
        head = {
            "job_id": "head", "stage": "stage10_seven_family",
            "mode": "instant", "geometry": "S3d_O8", "family": "gamma",
        }
        light = {
            "job_id": "light", "stage": "stage10_seven_family",
            "mode": "instant", "geometry": "Mass_model_511", "family": "gamma",
        }
        current = {
            "recent_classes": {
                r4.class_key(head): {
                    "recent_p95_upper_bytes": 6 * GIB,
                    "recent_max_bytes": 6 * GIB,
                },
                r4.class_key(light): {
                    "recent_p95_upper_bytes": 512 * 1024**2,
                    "recent_max_bytes": 512 * 1024**2,
                },
            },
            "all_time_audit_only": {},
        }
        index, _projection, observations = r4.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r4.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(index, 1)
        self.assertEqual([row["job_id"] for row in observations], ["head", "light"])
        index, _projection, observations = r4.choose_memory_candidate(
            [head, light], [], current, 4 * GIB,
            {"head": r4.MAX_BYPASS_DEBT},
            r4.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertIsNone(index)
        self.assertEqual(len(observations), 1)

    def test_strong_tier_bypasses_soft_fit_head_for_strong_fit_later(self) -> None:
        head = {
            "job_id": "soft-head", "stage": "stage10_seven_family",
            "mode": "instant", "geometry": "S3d_O8", "family": "gamma",
        }
        light = {
            "job_id": "strong-light", "stage": "stage10_seven_family",
            "mode": "instant", "geometry": "Mass_model_511", "family": "gamma",
        }
        current = {
            "recent_classes": {
                r4.class_key(head): {
                    "recent_p95_upper_bytes": int(1.3 * GIB),
                    "recent_max_bytes": int(1.3 * GIB),
                },
                r4.class_key(light): {
                    "recent_p95_upper_bytes": 512 * 1024**2,
                    "recent_max_bytes": 512 * 1024**2,
                },
            },
            "all_time_audit_only": {},
        }
        soft_index, soft_projection, _ = r4.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r4.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(soft_index, 0)
        self.assertGreaterEqual(
            soft_projection["projected_mem_available_bytes"],
            r4.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertLess(
            soft_projection["projected_mem_available_bytes"],
            r4.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        strong_index, strong_projection, observations = r4.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r4.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(strong_index, 1)
        self.assertGreaterEqual(
            strong_projection["projected_mem_available_bytes"],
            r4.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(
            [row["job_id"] for row in observations],
            ["soft-head", "strong-light"],
        )

    def test_read_only_status_constants(self) -> None:
        self.assertFalse(r4.AUTHORITY.exists())
        result = r4.self_test()
        self.assertFalse(result["transport_launched"])
        self.assertFalse(result["authority_published"])


if __name__ == "__main__":
    unittest.main()
