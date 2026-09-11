#!/usr/bin/env python3
"""Append-only recovery0003: authorized exact attempt04 with 256-MiB watchdog."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6
import resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler as r7
import run_m05_16h_campaign_batch0006 as campaign
import run_m05_campaign_batch0006_continuation0001_recovery0002_attempt03 as r2


RECOVERY_ID = "batch0006_continuation0001_recovery0003_attempt04"
RUN_NS = campaign.RUN_ROOT / "continuation0001_recovery0003_attempt04"
AUTHORITY = RUN_NS / "authority.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
PRELAUNCH_RESOURCE_EVIDENCE = RUN_NS / "prelaunch_resource_evidence.json"
COMPLETION = RUN_NS / "recovery_completion.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"
ATTEMPT = 4
WATCHDOG_FLOOR_BYTES = 256 * 1024**2
ATTEMPT_WALL_CAP_S = 1800
ORIGINAL_DEADLINE_RESERVE_S = 1800
MIN_PRELAUNCH_REMAINING_S = 900
VALIDATION_MARGIN_S = 600
RSS_BUDGET_BYTES = 12 * 1024**3
MIN_SWAP_TOTAL_BYTES = 14 * 1024**3
MIN_SWAP_FREE_BYTES = 12 * 1024**3
MIN_MEM_AVAILABLE_BYTES = int(7.5 * 1024**3)
MAX_MEMORY_PSI_FULL_AVG10 = 1.0
PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def structural_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    framing = payload.get("sim", {}).get("strict_framing", {})
    expected = int(job["events"])
    return (
        payload.get("status") == "PASS" and payload.get("job") == job
        and payload.get("selected_attempt") == ATTEMPT
        and (campaign.ROOT / str(payload.get("attempt_dir", ""))).is_dir()
        and framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == expected
        and int(framing.get("ID_second_count", -1)) == expected
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == expected
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == expected
    )


def load_frozen() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _c1_authority, job, inherited, failed = r2.load_frozen()
    r2_authority = load(r2.AUTHORITY)
    if r2_authority.get("exact_attempt") != 3 or r2_authority.get("exact_job") != job:
        raise RuntimeError("recovery0002 attempt03 authority structural drift")
    path = r2.RUN_NS / "failed_attempts" / r2.TARGET_JOB_ID / "attempt03" / "validation.json"
    if not path.is_file():
        raise RuntimeError("preserved attempt03 failure declaration missing")
    payload = load(path)
    if (
        payload.get("status") != "FAIL" or payload.get("job") != job
        or payload.get("selected_attempt") is not None
        or payload.get("watchdog_reason") != "hard_low_memory_512MiB"
    ):
        raise RuntimeError("attempt03 failure structural declaration drift")
    failed.append({
        "attempt": 3, "path": rel(path), "declared_status": "FAIL",
        "watchdog_reason": payload.get("watchdog_reason"),
        "peak_process_group_rss_bytes": int(payload.get("peak_process_group_rss_bytes", 0)),
        "wall_s": float(payload.get("wall_s", 0.0)),
    })
    if len(inherited) != 11 or len(failed) != 3:
        raise RuntimeError("recovery0003 requires exactly 11 inherited PASS and 3 preserved FAIL")
    return r2_authority, job, inherited, failed


def process_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc.name)
            if pid == os.getpid():
                continue
            comm = proc.joinpath("comm").read_text(encoding="utf-8").strip()
            cmd = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ValueError):
            continue
        if comm == "cosima" or "recovery0002_attempt03.py" in cmd:
            rows.append({"pid": pid, "comm": comm})
    partials = sorted(
        rel(path) for path in campaign.RUN_ROOT.glob("continuation*/attempts/**/.attempt*.partial")
        if path.is_dir()
    )
    return {"old_continuation_or_cosima_processes": rows, "partial_attempt_directories": partials}


def resource_evidence(job: dict[str, Any], failed: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    memory = r2.meminfo()
    mem_available = int(memory.get("MemAvailable", 0))
    swap_total = int(memory.get("SwapTotal", 0))
    swap_free = int(memory.get("SwapFree", 0))
    observed_upper = max(int(row["peak_process_group_rss_bytes"]) for row in failed)
    combined_projected = mem_available + swap_free - observed_upper
    psi = r2.memory_psi_full_avg10()
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(contract["wall_clock"]["deadline"])
    latest_hard_end = deadline - timedelta(seconds=ORIGINAL_DEADLINE_RESERVE_S)
    hard_end = min(now + timedelta(seconds=ATTEMPT_WALL_CAP_S), latest_hard_end)
    disk_free = shutil.disk_usage(campaign.RUN_ROOT).free
    campaign_bytes = campaign.campaign_bytes()
    cap = int(job["declared_cap_bytes"])
    snapshot = process_snapshot()
    errors: list[str] = []
    if (latest_hard_end - now).total_seconds() < MIN_PRELAUNCH_REMAINING_S:
        errors.append("less_than_900s_remains_to_original_deadline_minus_1800s")
    if hard_end + timedelta(seconds=VALIDATION_MARGIN_S) > deadline:
        errors.append("attempt04_hard_end_plus_validation_exceeds_original_deadline")
    if mem_available < MIN_MEM_AVAILABLE_BYTES:
        errors.append("MemAvailable_below_7.5GiB")
    if swap_total < MIN_SWAP_TOTAL_BYTES:
        errors.append("SwapTotal_below_14GiB")
    if swap_free < MIN_SWAP_FREE_BYTES:
        errors.append("SwapFree_below_12GiB")
    if psi >= MAX_MEMORY_PSI_FULL_AVG10:
        errors.append("memory_PSI_full_avg10_not_below_1")
    if combined_projected < PROJECTED_FLOOR_BYTES:
        errors.append("MemAvailable_plus_SwapFree_minus_observed_peak_below_1.5GiB")
    if disk_free < campaign.FILESYSTEM_RESERVE_BYTES + cap:
        errors.append("filesystem_reserve_after_current_attempt_cap")
    if campaign_bytes + cap > int(contract["disk"]["effective_campaign_cap_bytes"]) - campaign.CAMPAIGN_EMERGENCY_BYTES:
        errors.append("campaign_cap_after_current_attempt_cap")
    if snapshot["old_continuation_or_cosima_processes"] or snapshot["partial_attempt_directories"]:
        errors.append("nonquiescent_old_continuation_or_partial")
    return {
        "schema_version": 1,
        "status": "PASS__ATTEMPT04_RESOURCE_ADMISSION" if not errors else "PAUSE__ATTEMPT04_RESOURCE_ADMISSION",
        "at": now.isoformat(), "errors": errors,
        "MemAvailable_bytes": mem_available, "SwapTotal_bytes": swap_total, "SwapFree_bytes": swap_free,
        "memory_PSI_full_avg10": psi, "pswpout_pages": r2.pswpout_pages(),
        "observed_three_attempt_peak_upper_bytes": observed_upper,
        "combined_projected_after_observed_peak_bytes": combined_projected,
        "required_projected_floor_bytes": PROJECTED_FLOOR_BYTES,
        "attempt04_RSS_budget_bytes": RSS_BUDGET_BYTES,
        "attempt04_watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES,
        "campaign_bytes": campaign_bytes, "free_disk_bytes": disk_free,
        "candidate_current_attempt_cap_bytes": cap,
        "hard_end": hard_end.isoformat(),
        "latest_allowed_hard_end_original_deadline_minus_1800s": latest_hard_end.isoformat(),
        "attempt04_runtime_wall_cap_s": ATTEMPT_WALL_CAP_S,
        "minimum_prelaunch_remaining_to_latest_hard_end_s": MIN_PRELAUNCH_REMAINING_S,
        "validation_margin_s": VALIDATION_MARGIN_S, "process_snapshot": snapshot,
        "simulation_inputs_changed": False,
    }


def proposed_authority(
    prior_authority: dict[str, Any], job: dict[str, Any], inherited: list[dict[str, Any]], failed: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1, "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__USER_DIRECTED_EXACT_ATTEMPT04__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(), "controller": rel(Path(__file__).resolve()),
        "namespace": rel(RUN_NS), "prior_recovery0002_authority": rel(r2.AUTHORITY),
        "user_authorization": {"direction": "continue", "scope": "exact attempt04 plus 256MiB watchdog for this attempt only"},
        "exact_attempt": 4, "no_attempt05": True, "exact_job": job,
        "inherited_PASS_receipts": inherited, "inherited_PASS_count": 11,
        "preserved_failed_attempts": failed, "preserved_failed_attempt_count": 3,
        "matched_pair": {"key": job["matched_seed_key"], "inherited_PASS_mate_job_id": r2.MATE_JOB_ID, "atomic_wave_closes_only_if_attempt04_PASS": True},
        "frozen_declared_inputs": prior_authority["frozen_declared_inputs"],
        "unchanged": {"seed": True, "events": True, "source": True, "corrected_spectrum": True, "geometry": True, "physics": True, "cuts_detector_veto": True},
        "resource_policy": {
            "serial_only": True, "no_attempt05": True, "attempt04_RSS_budget_bytes": RSS_BUDGET_BYTES,
            "attempt04_only_watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES,
            "minimum_MemAvailable_bytes": MIN_MEM_AVAILABLE_BYTES,
            "minimum_SwapTotal_bytes": MIN_SWAP_TOTAL_BYTES, "minimum_SwapFree_bytes": MIN_SWAP_FREE_BYTES,
            "maximum_memory_PSI_full_avg10": MAX_MEMORY_PSI_FULL_AVG10,
            "current_attempt_only_disk": True, "attempt04_runtime_wall_cap_s": ATTEMPT_WALL_CAP_S,
            "hard_end": "min(admission_time+1800s, original_deadline-1800s)",
            "minimum_prelaunch_remaining_s": MIN_PRELAUNCH_REMAINING_S,
            "validation_margin_s": VALIDATION_MARGIN_S,
        },
        "post_PASS_policy": "close only the current atomic pair wave and evaluate remaining time/resources; never exceed original deadline",
        "old_data_policy": {"old_receipt_and_failure_JSON_structurally_read": True, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False},
        "gamma_locked": True,
    }


def bind() -> None:
    r6.RECOVERY_ID = RECOVERY_ID
    r6.RUN_NS = RUN_NS
    r6.AUTHORITY = AUTHORITY
    r6.SCHEDULER_EVENTS = SCHEDULER_EVENTS
    r6.EXECUTION_STATE = EXECUTION_STATE
    r6.receipt_path = receipt_path
    r6.validate_replan_receipt = structural_receipt
    r6.job_cap = lambda job: int(job["declared_cap_bytes"])


def self_test() -> dict[str, Any]:
    prior, job, inherited, failed = load_frozen()
    assert prior.get("exact_attempt") == 3
    assert len(inherited) == 11 and [row["attempt"] for row in failed] == [1, 2, 3]
    assert job["seed"] == 1800262155 and job["events"] == 2500 and job["geometry"] == "S3d_O8"
    assert ATTEMPT == 4 and WATCHDOG_FLOOR_BYTES == 256 * 1024**2
    assert ATTEMPT_WALL_CAP_S == 1800 and ORIGINAL_DEADLINE_RESERVE_S == 1800 and MIN_PRELAUNCH_REMAINING_S == 900
    assert MIN_SWAP_TOTAL_BYTES == 14 * 1024**3 and MIN_SWAP_FREE_BYTES == 12 * 1024**3
    return {
        "status": "PASS__CONTINUATION0001_RECOVERY0003_ATTEMPT04_STRUCTURAL_SELF_TEST",
        "tests": 9, "transport_launched": False, "attempt": 4, "no_attempt05": True,
        "inherited_PASS": 11, "preserved_FAIL": 3, "watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES,
        "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False, "gamma_locked": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    prior, job, inherited, failed = load_frozen()
    base = load(campaign.GLOBAL_CONTRACT)
    proposed = proposed_authority(prior, job, inherited, failed)
    evidence = resource_evidence(job, failed, base)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True)); return 0
    if args.print_plan:
        print(json.dumps({
            "status": "PASS__READ_ONLY_CONTINUATION0001_RECOVERY0003_ATTEMPT04_PLAN",
            "namespace": rel(RUN_NS), "exact_job": job, "exact_attempt": 4, "no_attempt05": True,
            "inherited_PASS": 11, "preserved_FAIL": 3, "resource_evidence_now": evidence,
            "gamma_locked": True, "old_SIM_or_gzip_reopened": False,
            "old_artifact_hashes_recomputed": False, "transport_launched": False,
        }, indent=2, sort_keys=True)); return 0
    lock = campaign.acquire_lock()
    previous_handlers: dict[int, Any] = {}
    original_watchdog = campaign.HARD_LOW_MEMORY_BYTES
    try:
        RUN_NS.mkdir(parents=True, exist_ok=True)
        if AUTHORITY.is_file():
            authority = load(AUTHORITY)
            for key in ("recovery_id", "namespace", "exact_attempt", "no_attempt05", "exact_job", "inherited_PASS_receipts", "preserved_failed_attempts", "matched_pair", "frozen_declared_inputs", "unchanged", "resource_policy", "post_PASS_policy", "old_data_policy", "gamma_locked"):
                if authority.get(key) != proposed.get(key):
                    raise RuntimeError(f"existing recovery0003 authority differs: {key}")
        else:
            campaign.atomic_write_once_json(AUTHORITY, proposed)
            authority = load(AUTHORITY)
        evidence = resource_evidence(job, failed, base)
        if not str(evidence["status"]).startswith("PASS"):
            raise RuntimeError("attempt04 resource admission PAUSE: " + "; ".join(evidence["errors"]))
        campaign.atomic_write_once_json(PRELAUNCH_RESOURCE_EVIDENCE, evidence)
        bind()
        r6.configure_validator()
        environment = r7.load_runtime_without_hash_revalidation(base, args.cosima.resolve())
        campaign._STOP_REQUESTED = False
        campaign.HARD_LOW_MEMORY_BYTES = WATCHDOG_FLOOR_BYTES
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, campaign._signal_handler)
        hard_end = datetime.fromisoformat(evidence["hard_end"])
        campaign.atomic_replace_json(EXECUTION_STATE, {
            "schema_version": 1, "recovery_id": RECOVERY_ID, "status": "RUNNING__EXACT_ATTEMPT04",
            "job_id": r2.TARGET_JOB_ID, "attempt": 4, "deadline": hard_end.isoformat(),
            "watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES, "gamma_locked": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        r6.append_event("attempt04_started", job_id=r2.TARGET_JOB_ID, attempt=4,
                        watchdog_floor_bytes=WATCHDOG_FLOOR_BYTES,
                        resource_evidence=rel(PRELAUNCH_RESOURCE_EVIDENCE))
        result = r6.run_attempt(job, ATTEMPT, base, environment, hard_end)
        passed = result.get("status") == "PASS" and receipt_path(job).is_file() and structural_receipt(job, load(receipt_path(job)))
        status = "PASS__CONTINUATION0001_WAVE0002_ATOMIC_PREFIX_RESTORED__GAMMA_LOCKED" if passed else "FAIL__CONTINUATION0001_ATTEMPT04_FINAL_EXACT_RETRY"
        completion = {
            "schema_version": 1, "status": status, "recovery_id": RECOVERY_ID,
            "attempt04_receipt": rel(receipt_path(job)) if passed else None,
            "inherited_PASS_count": 11, "effective_PASS_count": 12 if passed else 11,
            "preserved_prior_failed_attempt_count": 3, "attempt04_status": result.get("status"),
            "balanced_prefix": {"complete_atomic_waves": 2 if passed else 1, "matched_geometry_pairs": 6 if passed else 5},
            "remaining_phase_A_jobs": 16 if passed else 17,
            "post_PASS_next_action": "evaluate remaining time/resources; no automatic transport",
            "no_attempt05": True, "gamma_locked": True,
            "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
        }
        campaign.atomic_write_once_json(COMPLETION, completion)
        campaign.atomic_write_once_json(FINAL_UMBRELLA, {
            "schema_version": 1, "status": status, "authority": rel(AUTHORITY),
            "resource_evidence": rel(PRELAUNCH_RESOURCE_EVIDENCE), "completion": rel(COMPLETION),
            "no_attempt05": True, "gamma_locked": True,
            "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
        })
        campaign.atomic_replace_json(EXECUTION_STATE, {
            "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
            "job_id": r2.TARGET_JOB_ID, "attempt": 4, "deadline": hard_end.isoformat(),
            "watchdog_floor_bytes": WATCHDOG_FLOOR_BYTES, "gamma_locked": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return 0 if passed else 1
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
            campaign._ACTIVE_PROCESS = None
        campaign.HARD_LOW_MEMORY_BYTES = original_watchdog
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
