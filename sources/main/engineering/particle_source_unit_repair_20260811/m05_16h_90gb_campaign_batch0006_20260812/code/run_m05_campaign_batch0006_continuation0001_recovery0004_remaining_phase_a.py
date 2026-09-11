#!/usr/bin/env python3
"""Append-only continuation0001 recovery0004: finish the frozen Phase-A plan.

This controller structurally inherits the eleven original continuation PASS
receipts plus the exact attempt04 PASS receipt.  It runs only the sixteen
previously-unstarted non-gamma jobs, in the three remaining atomic balanced
waves (6, 6, 4).  Frozen transport inputs and seeds are unchanged; gamma is
locked.  Old SIM/gzip payloads and old artifact hashes are never reopened.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6
import resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler as r7
import resume_m05_campaign_batch0006_recovery0008_disk_admission as r8
import run_m05_16h_campaign_batch0006 as campaign
import run_m05_campaign_batch0006_continuation0001 as c1
import run_m05_campaign_batch0006_continuation0001_recovery0003_attempt04 as r3


RECOVERY_ID = "batch0006_continuation0001_recovery0004_remaining_phase_a"
RUN_NS = campaign.RUN_ROOT / "continuation0001_recovery0004_remaining_phase_a"
AUTHORITY = RUN_NS / "authority.json"
SEED_REGISTRY = RUN_NS / "seed_registry.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
CHECKPOINT = RUN_NS / "deweighting_precision_checkpoint.json"
FINAL_VALIDATION = RUN_NS / "final_validation.json"
FINAL_LEDGER = RUN_NS / "final_ledger.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"
STOP_LAUNCH = datetime.fromisoformat("2026-08-13T03:08:34.874118+00:00")
HARD_END = datetime.fromisoformat("2026-08-13T03:13:34.874118+00:00")
ORIGINAL_DEADLINE = datetime.fromisoformat("2026-08-13T03:18:34.874118+00:00")
ADMISSION_WALL_S = 240.0
ADMISSION_PUBLICATION_MARGIN_S = 60.0
WATCHDOG_FLOOR_BYTES = 512 * 1024**2
PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
_INHERITED: dict[str, Path] = {}
_PLAN: list[dict[str, Any]] = []


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def structural_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    framing = payload.get("sim", {}).get("strict_framing", {})
    events = int(job["events"])
    return (
        payload.get("status") == "PASS" and payload.get("job") == job
        and payload.get("selected_attempt") in (1, 2, 4)
        and (campaign.ROOT / str(payload.get("attempt_dir", ""))).is_dir()
        and framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == events
        and int(framing.get("ID_second_count", -1)) == events
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == events
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == events
    )


def new_receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def receipt_path(job: dict[str, Any]) -> Path:
    return _INHERITED.get(str(job["job_id"]), new_receipt_path(job))


def load_frozen() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path], list[list[dict[str, Any]]]]:
    old = load(c1.AUTHORITY)
    plan = old.get("plan")
    if not isinstance(plan, list) or len(plan) != 32:
        raise RuntimeError("frozen continuation0001 plan declaration drift")
    inherited: dict[str, Path] = {}
    for job in plan:
        if job["stage"] != c1.NON_GAMMA_STAGE:
            continue
        path = c1.RUN_NS / "job_receipts" / c1.NON_GAMMA_STAGE / f"{job['job_id']}.json"
        if path.is_file():
            if not structural_receipt(job, load(path)):
                raise RuntimeError(f"inherited continuation receipt declaration drift: {job['job_id']}")
            inherited[str(job["job_id"])] = path
    target = next(job for job in plan if job["job_id"] == r3.r2.TARGET_JOB_ID)
    target_path = r3.receipt_path(target)
    if not target_path.is_file() or not structural_receipt(target, load(target_path)):
        raise RuntimeError("attempt04 PASS receipt declaration missing or drifted")
    inherited[str(target["job_id"])] = target_path
    if len(inherited) != 12:
        raise RuntimeError(f"recovery0004 requires exactly 12 inherited PASS, found {len(inherited)}")
    ng = [job for job in plan if job["stage"] == c1.NON_GAMMA_STAGE]
    missing = [job for job in ng if str(job["job_id"]) not in inherited]
    if len(missing) != 16 or {job["family"] for job in missing} != {"muminus", "muplus", "neutron", "proton"}:
        raise RuntimeError("remaining frozen Phase-A difference is not exact 16-job mu/mu/n/p suffix")
    waves = [wave for wave in c1.balanced_waves(c1.NON_GAMMA_STAGE, plan) if any(str(job["job_id"]) not in inherited for job in wave)]
    if [len(wave) for wave in waves] != [6, 6, 4] or any(any(str(job["job_id"]) in inherited for job in wave) for wave in waves):
        raise RuntimeError("remaining Phase-A is not exact atomic waves [6,6,4]")
    return old, plan, inherited, waves


def prior_attempts(job: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for root in (c1.RUN_NS / "failed_attempts" / str(job["job_id"]), RUN_NS / "failed_attempts" / str(job["job_id"])):
        for path in root.glob("attempt*/validation.json"):
            try:
                attempt = int(path.parent.name.removeprefix("attempt"))
                old = load(path).get("job", {})
            except (ValueError, OSError):
                continue
            identity = ("job_id", "seed", "events", "geometry", "mode", "family", "source_tag")
            if all(old.get(key) == job.get(key) for key in identity):
                result.add(attempt)
    return result


def contract_with_live_boundaries(base: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(base))
    t0 = datetime.fromisoformat(value["wall_clock"]["t0"])
    value["wall_clock"]["stages"] = [{
        "id": c1.NON_GAMMA_STAGE,
        "start_s": 0,
        "stop_launch_s": int((STOP_LAUNCH - t0).total_seconds()),
        "hard_end_s": int((HARD_END - t0).total_seconds()),
        "declared_cap": 2_000_000_000,
    }]
    return value


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed: int, error: str | None = None) -> None:
    campaign.atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status, "stage": stage,
        "completed_jobs": completed, "phase_A_completed": sum(receipt_path(job).is_file() for job in _PLAN if job["stage"] == c1.NON_GAMMA_STAGE),
        "phase_A_target": 28, "remaining_target": 16, "minimum_target_workers": 6,
        "absolute_worker_cap": 10, "stop_launch": STOP_LAUNCH.isoformat(),
        "hard_end": HARD_END.isoformat(), "original_deadline": ORIGINAL_DEADLINE.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(), "mem_available_bytes": campaign.mem_available_bytes(),
        "free_disk_bytes": shutil.disk_usage(campaign.RUN_ROOT).free, "last_error": error, "gamma_locked": True,
    })


def bind(plan: list[dict[str, Any]], inherited: dict[str, Path]) -> None:
    global _PLAN, _INHERITED
    _PLAN, _INHERITED = plan, inherited
    for module in (r6, r7, r8):
        module.RECOVERY_ID = RECOVERY_ID; module.RUN_NS = RUN_NS; module.AUTHORITY = AUTHORITY
        module.SCHEDULER_EVENTS = SCHEDULER_EVENTS; module.EXECUTION_STATE = EXECUTION_STATE
        module.FINAL_VALIDATION = FINAL_VALIDATION; module.FINAL_LEDGER = FINAL_LEDGER; module.FINAL_UMBRELLA = FINAL_UMBRELLA
        module.receipt_path = receipt_path
    r6.REPLAN_SEED_REGISTRY = SEED_REGISTRY; r7.SEED_REGISTRY = SEED_REGISTRY; r8.SEED_REGISTRY = SEED_REGISTRY
    r6.validate_replan_receipt = structural_receipt; r7.validate_replan_receipt = structural_receipt; r8.validate_receipt = structural_receipt
    r6.job_cap = lambda job: int(job["declared_cap_bytes"])
    r6.prior_exact_attempts = prior_attempts; r7.prior_exact_attempts = prior_attempts
    r6.runtime_job_budget = lambda job, *_args: int(job["planned_peak_rss_budget_bytes"])
    r6.runtime_job_wall_budget = lambda _job, *_args: ADMISSION_WALL_S
    r6.disk_projection = r8.disk_projection
    r6.worker_entry = r8.worker_entry; r6.reap = r8.reap
    r7.rss_evidence = c1.cheap_rss_evidence; r7.ordered_stage_jobs = c1.ordered_jobs; r7.update_state = update_state
    r7.MINIMUM_TARGET_WORKERS = 6; r7.ABSOLUTE_MAX_WORKERS = 10; r7.PROJECTED_FLOOR_BYTES = PROJECTED_FLOOR_BYTES
    r7.LAUNCH_STAGGER_S = 15.0; r6.VALIDATION_PUBLICATION_MARGIN_S = ADMISSION_PUBLICATION_MARGIN_S
    r8._R7_RUN_STAGE = r7.run_stage
    c1.RUN_NS = RUN_NS; c1.AUTHORITY = AUTHORITY; c1.SEED_REGISTRY = SEED_REGISTRY
    c1.SCHEDULER_EVENTS = SCHEDULER_EVENTS; c1.EXECUTION_STATE = EXECUTION_STATE; c1.CHECKPOINT = CHECKPOINT
    c1.FINAL_VALIDATION = FINAL_VALIDATION; c1.FINAL_LEDGER = FINAL_LEDGER; c1.FINAL_UMBRELLA = FINAL_UMBRELLA
    c1.receipt_path = receipt_path; c1.structural_receipt = structural_receipt
    campaign.HARD_LOW_MEMORY_BYTES = WATCHDOG_FLOOR_BYTES


def proposal(old: dict[str, Any], plan: list[dict[str, Any]], inherited: dict[str, Path], waves: list[list[dict[str, Any]]]) -> dict[str, Any]:
    remaining = [job for wave in waves for job in wave]
    return {
        "schema_version": 1, "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__APPEND_ONLY_CONTINUATION0001_REMAINING_PHASE_A__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(), "controller": rel(Path(__file__).resolve()),
        "namespace": rel(RUN_NS), "prior_continuation_authority": rel(c1.AUTHORITY),
        "attempt04_umbrella": rel(r3.FINAL_UMBRELLA),
        "inherited_PASS_receipts": [{"job_id": job_id, "path": rel(path)} for job_id, path in sorted(inherited.items())],
        "inherited_PASS_count": 12, "remaining_plan": remaining, "remaining_jobs": 16,
        "remaining_events": sum(int(job["events"]) for job in remaining),
        "atomic_waves": [[job["job_id"] for job in wave] for wave in waves],
        "frozen_seed_registry": old["fresh_seed_registry"], "fresh_seed_allocation": False,
        "scheduler": {"target": 6, "cap": 10, "launch_stagger_s": 15.0,
                      "projected_MemAvailable_floor_bytes": PROJECTED_FLOOR_BYTES,
                      "current_attempt_only_disk": True, "maximum_exact_attempts_per_unstarted_job": 2,
                      "admission_wall_estimate_s": ADMISSION_WALL_S,
                      "admission_publication_margin_s": ADMISSION_PUBLICATION_MARGIN_S,
                      "admission_estimates_only_transport_hard_end_controls": True,
                      "stop_launch": STOP_LAUNCH.isoformat(), "hard_end": HARD_END.isoformat(),
                      "final_deadline": ORIGINAL_DEADLINE.isoformat()},
        "unchanged": {"original_plan_job_dicts": True, "seeds_events_sources_spectra_geometry_physics_cuts_detector_veto": True,
                      "job_caps": True, "watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES},
        "gamma_locked": True, "gamma_jobs_launched": False,
        "old_data_policy": {"old_receipt_JSON_structurally_read": True, "old_SIM_or_gzip_reopened": False,
                            "old_artifact_hashes_recomputed": False},
    }


def self_test() -> dict[str, Any]:
    old, plan, inherited, waves = load_frozen()
    assert len(inherited) == 12 and [len(wave) for wave in waves] == [6, 6, 4]
    remaining = [job for wave in waves for job in wave]
    assert len(remaining) == 16 and sum(int(job["events"]) for job in remaining) == 34_280
    assert all(not prior_attempts(job) for job in remaining)
    assert STOP_LAUNCH < HARD_END < ORIGINAL_DEADLINE and old["fresh_seed_registry"]["collision_count"] == 0
    return {"status": "PASS__CONTINUATION0001_RECOVERY0004_PURE_STRUCTURAL_SELF_TEST", "tests": 7,
            "inherited_PASS": 12, "remaining_jobs": 16, "remaining_events": 34_280,
            "waves": [len(wave) for wave in waves], "transport_launched": False,
            "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False, "gamma_locked": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true"); parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT); args = parser.parse_args()
    old, plan, inherited, waves = load_frozen(); proposed = proposal(old, plan, inherited, waves)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True)); return 0
    if args.print_plan:
        print(json.dumps({**proposed, "status": "PASS__READ_ONLY_RECOVERY0004_REMAINING_PHASE_A_PLAN", "transport_launched": False}, indent=2, sort_keys=True)); return 0
    if datetime.now(timezone.utc) >= STOP_LAUNCH:
        raise RuntimeError("recovery0004 reached frozen stop-launch before controller admission")
    base = load(campaign.GLOBAL_CONTRACT); contract = contract_with_live_boundaries(base)
    lock = campaign.acquire_lock(); previous: dict[int, Any] = {}; fatal: str | None = None
    try:
        RUN_NS.mkdir(parents=True, exist_ok=True)
        if AUTHORITY.is_file():
            authority = load(AUTHORITY)
            for key in ("recovery_id", "namespace", "inherited_PASS_receipts", "remaining_plan", "atomic_waves", "frozen_seed_registry", "scheduler", "unchanged", "gamma_locked", "old_data_policy"):
                if authority.get(key) != proposed.get(key): raise RuntimeError(f"existing recovery0004 authority differs: {key}")
        else:
            campaign.atomic_write_once_json(AUTHORITY, proposed); authority = load(AUTHORITY)
        if not SEED_REGISTRY.is_file():
            campaign.atomic_write_once_json(SEED_REGISTRY, {"schema_version": 1, "status": "PASS__REUSES_ONLY_FROZEN_CONTINUATION0001_REGISTERED_SEEDS", "fresh_seed_allocation": False, "frozen": old["fresh_seed_registry"], "remaining_jobs": [{"job_id": j["job_id"], "seed": j["seed"]} for wave in waves for j in wave]})
        bind(plan, inherited); r6.configure_validator()
        environment = r7.load_runtime_without_hash_revalidation(base, args.cosima.resolve())
        campaign._STOP_REQUESTED = False; r6._COORDINATOR_STOP = False
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum); signal.signal(signum, r6.coordinator_signal)
        r6.append_event("recovery0004_controller_started", inherited_PASS=12, remaining_jobs=16,
                        atomic_wave_sizes=[6, 6, 4], target_workers=6, cap=10, gamma_locked=True)
        for index, wave in enumerate(waves, 3):
            r6.append_event("balanced_matched_wave_start", wave_index=index, jobs=len(wave), matched_keys=sorted({j["matched_seed_key"] for j in wave}))
            reason = r8.run_stage(c1.NON_GAMMA_STAGE, wave, [], contract, environment, authority, {})
            if reason:
                fatal = f"wave{index}: {reason}"; break
            if not all(receipt_path(job).is_file() and structural_receipt(job, load(receipt_path(job))) for job in wave):
                fatal = f"wave{index}: atomic wave did not close"; break
            r6.append_event("balanced_matched_wave_PASS", wave_index=index, jobs=len(wave))
        checkpoint = c1.publish_checkpoint(plan)
        if not str(checkpoint.get("status", "")).startswith("PASS"):
            fatal = fatal or "non-gamma cumulative deweighting checkpoint did not PASS"
        c1.publish_final(plan, fatal)
        return 0 if str(load(FINAL_UMBRELLA).get("status", "")).startswith("PASS") else 1
    finally:
        for worker in list(r6._ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                try: os.kill(worker.process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                worker.process.join(timeout=30)
        for signum, handler in previous.items(): signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN); lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
