#!/usr/bin/env python3
"""Pure/read-only tests for the recovery0005 scheduler."""

from __future__ import annotations

import unittest
from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory

import resume_m05_campaign_batch0006_recovery0005_short_job_concurrency as r5


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


class Recovery0005Tests(unittest.TestCase):
    def test_global_limits_have_no_geometry_specific_cap(self) -> None:
        self.assertEqual(r5.NORMAL_TARGET_WORKERS, 6)
        self.assertEqual(r5.ABSOLUTE_MAX_WORKERS, 8)
        source = Path(r5.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "MAX_O8_WORKERS",
            "MAX_HEAVY_O8",
            "MAX_PROTON_WORKERS",
            "HISTORICAL_HEAVY_O8_RSS_BYTES",
        ):
            self.assertNotIn(forbidden, source)

    def test_normal_six_is_preearned_and_every_launch_waits_15s(self) -> None:
        self.assertEqual(
            r5.launch_clock_decision(
                active_count=4, target_workers=6, now=r5.REPLACEMENT_STAGGER_S,
                last_launch=0,
            ),
            (True, False),
        )
        self.assertEqual(
            r5.launch_clock_decision(
                active_count=4, target_workers=6,
                now=r5.REPLACEMENT_STAGGER_S - 1,
                last_launch=0,
            ),
            (False, False),
        )
        self.assertEqual(
            r5.launch_clock_decision(
                active_count=6, target_workers=6, now=100.5,
                last_launch=100,
            ),
            (False, False),
        )
        self.assertEqual(
            r5.launch_clock_decision(
                active_count=6, target_workers=6,
                now=r5.LAUNCH_STAGGER_S, last_launch=0,
            ),
            (True, True),
        )
        self.assertEqual(
            r5.launch_clock_decision(
                active_count=8, target_workers=8, now=10_000,
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
        upper = r5.class_upper_bytes(job(), current)
        self.assertLess(upper, 2 * GIB)

    def test_memavailable_projection_does_not_double_count_live_rss(self) -> None:
        candidate = job("candidate")
        worker = r5.Worker(
            job("active"), DummyProcess(101), None, "", 0.0
        )
        upper = r5.class_upper_bytes(candidate, evidence())
        actual = upper // 4
        result = r5.memory_projection(
            [worker], candidate, evidence(),
            available_bytes=6 * GIB, live_rss={101: actual},
            rss_history={101: deque([(0, actual), (15, actual), (30, actual)])},
            now_monotonic=61,
        )
        self.assertEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - r5.ACTIVE_GROWTH_PAD_BYTES - upper,
        )
        self.assertNotEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - (upper - actual) - upper,
        )

    def test_live_rss_above_upper_is_not_subtracted_again(self) -> None:
        candidate = job("candidate")
        worker = r5.Worker(
            job("active"), DummyProcess(101), None, "", 0.0
        )
        upper = r5.class_upper_bytes(candidate, evidence())
        result = r5.memory_projection(
            [worker], candidate, evidence(),
            available_bytes=6 * GIB, live_rss={101: 2 * upper},
            rss_history={101: deque([(0, 2 * upper), (15, 2 * upper), (30, 2 * upper)])},
            now_monotonic=61,
        )
        self.assertEqual(
            result["active_trajectory_growth_reserve_bytes"],
            r5.ACTIVE_GROWTH_PAD_BYTES,
        )
        self.assertEqual(
            result["projected_mem_available_bytes"],
            6 * GIB - r5.ACTIVE_GROWTH_PAD_BYTES - result["candidate_class_upper_bytes"],
        )

    def test_three_stable_point7g_workers_and_8g_available_admit_light_candidate(self) -> None:
        current = evidence(upper=700 * 1024**2)
        workers = [
            r5.Worker(job(f"active-{pid}"), DummyProcess(pid), None, "", 0.0)
            for pid in (101, 102, 103)
        ]
        live = {pid: int(0.7 * GIB) for pid in (101, 102, 103)}
        histories = {
            pid: deque([(0, live[pid]), (15, live[pid]), (30, live[pid])])
            for pid in live
        }
        result = r5.memory_projection(
            workers, job("light"), current, available_bytes=8 * GIB,
            live_rss=live, rss_history=histories,
            now_monotonic=61,
        )
        self.assertEqual(
            result["active_trajectory_growth_reserve_bytes"],
            3 * r5.ACTIVE_GROWTH_PAD_BYTES,
        )
        self.assertGreaterEqual(
            result["projected_mem_available_bytes"],
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )

    def test_fast_active_rss_growth_conservatively_pauses(self) -> None:
        heavy_key = "unknown/unknown/S3d_O8/eplus"
        light_key = "unknown/unknown/S3d_O8/gamma"
        current = {
            "recent_classes": {
                heavy_key: {"recent_p95_upper_bytes": 4 * GIB},
                light_key: {"recent_p95_upper_bytes": 512 * 1024**2},
            },
            "all_time_audit_only": {},
        }
        workers = [
            r5.Worker(job(f"growing-{pid}"), DummyProcess(pid), None, "", 0.0)
            for pid in (201, 202, 203)
        ]
        live = {pid: 2 * GIB for pid in (201, 202, 203)}
        histories = {
            pid: deque([(0, 256 * 1024**2), (15, GIB), (30, 2 * GIB)])
            for pid in live
        }
        candidate = {
            "job_id": "light", "geometry": "S3d_O8", "family": "gamma"
        }
        result = r5.memory_projection(
            workers, candidate, current, available_bytes=8 * GIB,
            live_rss=live, rss_history=histories,
            now_monotonic=61,
        )
        self.assertLess(
            result["projected_mem_available_bytes"],
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )
        state = r5.HealthState()
        allowed, _reason = r5.health_allows_launch(
            state, now=10, projection=result, swap={"growing": False}
        )
        self.assertFalse(allowed)

    def test_immature_worker_reserves_full_remaining_envelope(self) -> None:
        candidate = job("candidate")
        worker = r5.Worker(job("young"), DummyProcess(301), None, "", 100.0)
        current = evidence(upper=4 * GIB)
        upper = r5.class_upper_bytes(worker.job, current)
        live = 700 * 1024**2
        result = r5.memory_projection(
            [worker], candidate, current, available_bytes=8 * GIB,
            live_rss={301: live},
            rss_history={301: deque([(100, live), (105, live), (110, live)])},
            now_monotonic=115,
        )
        self.assertFalse(result["active"][0]["trajectory"]["mature"])
        self.assertGreaterEqual(
            result["active_trajectory_growth_reserve_bytes"], upper - live
        )

    def test_recent_ramp_not_diluted_by_old_flat_samples(self) -> None:
        forecast = r5.active_growth_forecast(
            current_bytes=2 * GIB,
            samples=[
                (0, GIB), (20, GIB), (40, GIB),
                (50, int(1.1 * GIB)), (60, int(1.5 * GIB)), (70, 2 * GIB),
            ],
            class_upper_bytes=3 * GIB,
            worker_age_s=100,
        )
        self.assertTrue(forecast["mature"])
        self.assertGreater(
            forecast["reserve_bytes"], forecast["remaining_class_envelope_bytes"]
        )

    def test_exact_class_tail_is_not_forgotten_after_eight_light_receipts(self) -> None:
        current = evidence(upper=512 * 1024**2)
        cls = current["recent_classes"][r5.class_key(job())]
        cls["current_campaign_exact_class_max_bytes"] = int(4.26 * GIB)
        cls["current_campaign_exact_class_receipts"] = 12
        self.assertGreater(r5.class_upper_bytes(job(), current), 4.8 * GIB)

    def test_stage20_uncalibrated_class_allows_only_one_active(self) -> None:
        first = {
            "job_id": "p1", "stage": "stage20_proton", "mode": "instant",
            "geometry": "S3d_O8", "family": "proton",
        }
        second = dict(first, job_id="p2")
        smoke_key = "stage00_mergeable_smoke/instant/S3d_O8/proton"
        current = {
            "recent_classes": {
                smoke_key: {
                    "n": 4, "current_campaign_exact_class_receipts": 4,
                    "recent_p95_upper_bytes": 800 * 1024**2,
                    "current_campaign_exact_class_max_bytes": 850 * 1024**2,
                }
            },
            "all_time_audit_only": {},
        }
        self.assertGreaterEqual(
            r5.class_upper_bytes(first, current),
            int(r5.CLASS_UNCALIBRATED_FLOOR_BYTES * r5.CLASS_GROWTH_FACTOR)
            + r5.CLASS_GROWTH_PAD_BYTES,
        )
        active = [r5.Worker(first, DummyProcess(401), None, "", 0.0)]
        index, _projection, observations = r5.choose_memory_candidate(
            [second], active, current, 8 * GIB, {},
            r5.SOFT_PROJECTED_FLOOR_BYTES,
            live_rss={401: 512 * 1024**2},
            rss_history={401: deque([(0, 512 * 1024**2)])},
            now_monotonic=15,
        )
        self.assertIsNone(index)
        self.assertTrue(observations[0]["uncalibrated_same_class_active"])

    def test_stage20_candidate_selection_never_bypasses_frozen_head(self) -> None:
        head = {
            "job_id": "heavy-head", "stage": "stage20_proton", "mode": "instant",
            "geometry": "S3d_O8", "family": "proton",
        }
        later = {
            "job_id": "light-later", "stage": "stage20_proton", "mode": "buildup",
            "geometry": "Mass_model_511", "family": "proton",
        }
        current = {
            "recent_classes": {
                r5.class_key(head): {
                    "n": 2, "current_campaign_exact_class_receipts": 2,
                    "recent_p95_upper_bytes": 6 * GIB,
                    "current_campaign_exact_class_max_bytes": 6 * GIB,
                },
                r5.class_key(later): {
                    "n": 2, "current_campaign_exact_class_receipts": 2,
                    "recent_p95_upper_bytes": 512 * 1024**2,
                    "current_campaign_exact_class_max_bytes": 512 * 1024**2,
                },
            },
            "all_time_audit_only": {},
        }
        index, _projection, observations = r5.choose_memory_candidate(
            [head, later], [], current, 4 * GIB, {},
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertIsNone(index)
        self.assertEqual([row["job_id"] for row in observations], ["heavy-head"])

    def test_stage20_allows_only_one_uncalibrated_active_across_classes(self) -> None:
        active_job = {
            "job_id": "instant-o8", "stage": "stage20_proton", "mode": "instant",
            "geometry": "S3d_O8", "family": "proton",
        }
        different_head = {
            "job_id": "buildup-mass", "stage": "stage20_proton", "mode": "buildup",
            "geometry": "Mass_model_511", "family": "proton",
        }
        active = [r5.Worker(active_job, DummyProcess(402), None, "", 0.0)]
        index, _projection, observations = r5.choose_memory_candidate(
            [different_head], active, {"recent_classes": {}, "all_time_audit_only": {}},
            8 * GIB, {}, r5.SOFT_PROJECTED_FLOOR_BYTES,
            live_rss={402: 512 * 1024**2},
            rss_history={402: deque([(0, 512 * 1024**2)])},
            now_monotonic=15,
        )
        self.assertIsNone(index)
        self.assertTrue(observations[0]["uncalibrated_stage20_active"])

    def test_final_publication_snapshot_is_restart_idempotent(self) -> None:
        original = r5.FINAL_PUBLICATION_SNAPSHOT
        with TemporaryDirectory() as directory:
            try:
                r5.FINAL_PUBLICATION_SNAPSHOT = Path(directory) / "snapshot.json"
                first = r5.load_or_publish_final_snapshot(
                    fatal=None, receipts_closure_sha256="receipts",
                    stages_closure_sha256="stages", authority_sha256="authority",
                    cutover_sha256="cutover", scheduler_events_sha256="events-before",
                    campaign_bytes=100,
                )
                after_restart = r5.load_or_publish_final_snapshot(
                    fatal=None, receipts_closure_sha256="receipts",
                    stages_closure_sha256="stages", authority_sha256="authority",
                    cutover_sha256="cutover", scheduler_events_sha256="events-after",
                    campaign_bytes=200,
                )
                self.assertEqual(first, after_restart)
                self.assertEqual(after_restart["scheduler_events_sha256"], "events-before")
                self.assertEqual(after_restart["campaign_bytes"], 100)
                with self.assertRaisesRegex(RuntimeError, "receipt"):
                    r5.load_or_publish_final_snapshot(
                        fatal=None, receipts_closure_sha256="changed-receipts",
                        stages_closure_sha256="stages", authority_sha256="authority",
                        cutover_sha256="cutover", scheduler_events_sha256="events-after",
                        campaign_bytes=200,
                    )
            finally:
                r5.FINAL_PUBLICATION_SNAPSHOT = original

    def test_soft_floor_and_resume_hysteresis(self) -> None:
        state = r5.HealthState()
        swap = {"growing": False}
        low = {
            "projected_mem_available_bytes":
                r5.SOFT_PROJECTED_FLOOR_BYTES - 1
        }
        self.assertFalse(
            r5.health_allows_launch(state, now=0, projection=low, swap=swap)[0]
        )
        high = {
            "projected_mem_available_bytes":
                r5.RESUME_PROJECTED_FLOOR_BYTES + 1
        }
        self.assertFalse(
            r5.health_allows_launch(state, now=1, projection=high, swap=swap)[0]
        )
        self.assertTrue(
            r5.health_allows_launch(
                state, now=1 + r5.RESUME_STABLE_S,
                projection=high, swap=swap,
            )[0]
        )

    def test_seventh_and_eighth_require_strong_surplus(self) -> None:
        state = r5.HealthState()
        projection = {
            "projected_mem_available_bytes":
                r5.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES + 1,
            "active": [{"live_rss_bytes": GIB}],
        }
        self.assertFalse(
            r5.strong_surplus_allows_launch(
                state, now=0, projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )
        self.assertFalse(
            r5.strong_surplus_allows_launch(
                state, now=1, projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )
        self.assertTrue(
            r5.strong_surplus_allows_launch(
                state, now=1 + r5.STRONG_SURPLUS_STABLE_S,
                projection=projection,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )

    def test_strong_surplus_rejects_swap_psi_and_rss_growth(self) -> None:
        base = {
            "projected_mem_available_bytes":
                r5.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES + 1,
            "active": [{"live_rss_bytes": GIB}],
        }
        state = r5.HealthState()
        self.assertFalse(
            r5.strong_surplus_allows_launch(
                state, now=0, projection=base,
                swap={"growing": True}, psi_full_avg10=0,
            )[0]
        )
        state = r5.HealthState()
        self.assertFalse(
            r5.strong_surplus_allows_launch(
                state, now=0, projection=base,
                swap={"growing": False},
                psi_full_avg10=r5.STRONG_SURPLUS_MAX_PSI_FULL_AVG10 + 0.01,
            )[0]
        )
        grown = dict(base)
        grown["active"] = [{
            "live_rss_bytes": GIB + r5.STRONG_SURPLUS_MAX_RSS_GROWTH_BYTES + 1
        }]
        state = r5.HealthState(strong_rss_samples=deque([(0, GIB)]))
        self.assertFalse(
            r5.strong_surplus_allows_launch(
                state, now=r5.STRONG_SURPLUS_STABLE_S, projection=grown,
                swap={"growing": False}, psi_full_avg10=0,
            )[0]
        )

    def test_no_soft_preemption_or_extra_attempt_contract(self) -> None:
        source = Path(r5.__file__).read_text(encoding="utf-8")
        self.assertNotIn("emergency_withdraw_newest", source)
        self.assertNotIn("MAX_RESOURCE_ATTEMPTS", source)
        self.assertIn("range(1, campaign.MAX_ATTEMPTS + 1)", source)

    def test_swap_nonzero_but_flat_is_not_growth(self) -> None:
        used = 700_000
        self.assertFalse(
            r5.swap_growth([(0, used), (15, used), (31, used)])["growing"]
        )
        self.assertTrue(
            r5.swap_growth(
                [(0, used), (15, used + r5.SWAP_GROWTH_PAGES // 2),
                 (31, used + r5.SWAP_GROWTH_PAGES)]
            )["growing"]
        )

    def test_actual_fair_wave_preserves_frozen_plan(self) -> None:
        _contract, plan = r5.frozen_inputs()
        ordered = r5.fair_wave_jobs("stage10_seven_family", plan)
        original = [job for job in plan if job["stage"] == "stage10_seven_family"]
        self.assertEqual(len(ordered), len(original))
        self.assertEqual(
            {row["job_id"] for row in ordered},
            {row["job_id"] for row in original},
        )
        self.assertEqual(
            r5.campaign.json_sha256(plan),
            r5.campaign.load_json(r5.campaign.GLOBAL_CONTRACT)["planned_jobs_sha256"],
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
        self.assertLessEqual(max(runs), r5.FAIR_WAVE_SIZE)

    def test_stage20_preserves_frozen_round_robin_order(self) -> None:
        _contract, plan = r5.frozen_inputs()
        expected = [row for row in plan if row["stage"] == "stage20_proton"]
        self.assertEqual(r5.fair_wave_jobs("stage20_proton", plan), expected)

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
                r5.class_key(head): {
                    "recent_p95_upper_bytes": 6 * GIB,
                    "recent_max_bytes": 6 * GIB,
                },
                r5.class_key(light): {
                    "recent_p95_upper_bytes": 512 * 1024**2,
                    "recent_max_bytes": 512 * 1024**2,
                },
            },
            "all_time_audit_only": {},
        }
        index, _projection, observations = r5.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(index, 1)
        self.assertEqual([row["job_id"] for row in observations], ["head", "light"])
        index, _projection, observations = r5.choose_memory_candidate(
            [head, light], [], current, 4 * GIB,
            {"head": r5.MAX_BYPASS_DEBT},
            r5.SOFT_PROJECTED_FLOOR_BYTES,
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
                r5.class_key(head): {
                    "recent_p95_upper_bytes": int(1.3 * GIB),
                    "recent_max_bytes": int(1.3 * GIB),
                },
                r5.class_key(light): {
                    "recent_p95_upper_bytes": 512 * 1024**2,
                    "recent_max_bytes": 512 * 1024**2,
                },
            },
            "all_time_audit_only": {},
        }
        soft_index, soft_projection, _ = r5.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(soft_index, 0)
        self.assertGreaterEqual(
            soft_projection["projected_mem_available_bytes"],
            r5.SOFT_PROJECTED_FLOOR_BYTES,
        )
        self.assertLess(
            soft_projection["projected_mem_available_bytes"],
            r5.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        strong_index, strong_projection, observations = r5.choose_memory_candidate(
            [head, light], [], current, 4 * GIB, {},
            r5.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(strong_index, 1)
        self.assertGreaterEqual(
            strong_projection["projected_mem_available_bytes"],
            r5.STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
        )
        self.assertEqual(
            [row["job_id"] for row in observations],
            ["soft-head", "strong-light"],
        )

    def test_read_only_status_constants(self) -> None:
        self.assertFalse(r5.AUTHORITY.exists())
        result = r5.self_test()
        self.assertFalse(result["transport_launched"])
        self.assertFalse(result["authority_published"])


if __name__ == "__main__":
    unittest.main()
