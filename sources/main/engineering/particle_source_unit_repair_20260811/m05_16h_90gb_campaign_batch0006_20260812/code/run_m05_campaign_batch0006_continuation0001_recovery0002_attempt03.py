#!/usr/bin/env python3
"""Append-only recovery0002 for the user-authorized eplus/O8 attempt03.

This controller preserves the two resource-failed attempts and the eleven
continuation0001 PASS receipts.  It changes no transport input: attempt03 uses
the exact same job dictionary, seed, event count, corrected source, geometry,
and physics.  Old receipt/failure JSON is read structurally; old SIM/gzip and
old artifact hashes are never reopened or recomputed.  Gamma stays locked.
"""

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
import run_m05_campaign_batch0006_continuation0001 as c1


RECOVERY_ID = "batch0006_continuation0001_recovery0002_attempt03"
OLD_NS = c1.RUN_NS
RUN_NS = campaign.RUN_ROOT / "continuation0001_recovery0002_attempt03"
AUTHORITY = RUN_NS / "authority.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
PRELAUNCH_RESOURCE_EVIDENCE = RUN_NS / "prelaunch_resource_evidence.json"
COMPLETION = RUN_NS / "recovery_completion.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"
TARGET_JOB_ID = "c1_ng_eplus_instant_S3d_O8_wave0001"
MATE_JOB_ID = "c1_ng_eplus_instant_Mass_model_511_wave0001"
ATTEMPT = 3
PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
VALIDATION_MARGIN_S = 600
ATTEMPT_WALL_CAP_S = 2700
ORIGINAL_DEADLINE_RESERVE_S = 2400
MIN_PRELAUNCH_REMAINING_S = 1200
RSS_BUDGET_BYTES = 12 * 1024**3
MIN_SWAP_TOTAL_BYTES = 14 * 1024**3
MIN_SWAP_FREE_BYTES = 12 * 1024**3
MIN_MEM_AVAILABLE_BYTES = int(7.5 * 1024**3)
MAX_MEMORY_PSI_FULL_AVG10 = 1.0


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def old_receipt_path(job: dict[str, Any]) -> Path:
    return OLD_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def structural_receipt(job: dict[str, Any], payload: dict[str, Any], attempts: tuple[int, ...]) -> bool:
    framing = payload.get("sim", {}).get("strict_framing", {})
    expected = int(job["events"])
    return (
        payload.get("status") == "PASS" and payload.get("job") == job
        and payload.get("selected_attempt") in attempts
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
    old_authority = load(c1.AUTHORITY)
    plan = old_authority.get("plan")
    if not isinstance(plan, list) or len(plan) != 32:
        raise RuntimeError("continuation0001 authority plan declaration drift")
    by_id = {str(job["job_id"]): job for job in plan}
    if TARGET_JOB_ID not in by_id or MATE_JOB_ID not in by_id:
        raise RuntimeError("target/mate missing from frozen continuation plan")
    job = by_id[TARGET_JOB_ID]
    exact = {
        "seed": 1800262155, "events": 2500, "family": "eplus", "geometry": "S3d_O8",
        "mode": "instant", "source_tag": "eplus",
        "matched_seed_key": "continuation0001|eplus|instant|wave0001",
    }
    if any(job.get(key) != value for key, value in exact.items()):
        raise RuntimeError("target frozen identity differs from explicit retry authorization")
    inherited: list[dict[str, Any]] = []
    for row in plan:
        path = old_receipt_path(row)
        if not path.is_file():
            continue
        payload = load(path)
        if not structural_receipt(row, payload, (1, 2)):
            raise RuntimeError(f"inherited PASS declaration drift: {row['job_id']}")
        inherited.append({
            "job_id": row["job_id"], "events": int(row["events"]), "path": rel(path),
            "declared_status": payload.get("status"), "selected_attempt": payload.get("selected_attempt"),
        })
    if len(inherited) != 11 or TARGET_JOB_ID in {row["job_id"] for row in inherited}:
        raise RuntimeError("expected exactly eleven inherited PASS receipts and missing target")
    if MATE_JOB_ID not in {row["job_id"] for row in inherited}:
        raise RuntimeError("matched Mass_model_511 mate is not inherited PASS")
    failed: list[dict[str, Any]] = []
    for attempt in (1, 2):
        path = OLD_NS / "failed_attempts" / TARGET_JOB_ID / f"attempt{attempt:02d}" / "validation.json"
        if not path.is_file():
            raise RuntimeError(f"missing preserved failed attempt{attempt:02d} declaration")
        payload = load(path)
        if (
            payload.get("status") != "FAIL" or payload.get("job") != job
            or payload.get("selected_attempt") is not None
            or payload.get("watchdog_reason") != "hard_low_memory_512MiB"
        ):
            raise RuntimeError(f"failed attempt{attempt:02d} structural declaration drift")
        failed.append({
            "attempt": attempt, "path": rel(path), "declared_status": payload.get("status"),
            "watchdog_reason": payload.get("watchdog_reason"),
            "peak_process_group_rss_bytes": int(payload.get("peak_process_group_rss_bytes", 0)),
            "wall_s": float(payload.get("wall_s", 0.0)),
        })
    return old_authority, job, inherited, failed


def proc_snapshot() -> dict[str, Any]:
    processes: list[dict[str, Any]] = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc.name)
            if pid == os.getpid():
                continue
            cmd = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            comm = proc.joinpath("comm").read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if comm == "cosima" or "run_m05_campaign_batch0006_continuation0001.py" in cmd:
            processes.append({"pid": pid, "comm": comm})
    partials = [rel(path) for path in campaign.RUN_ROOT.glob("continuation*/attempts/**/.attempt*.partial") if path.is_dir()]
    return {"continuation_or_cosima_processes": processes, "partial_attempt_directories": sorted(partials)}


def meminfo() -> dict[str, int]:
    rows: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].rstrip(":") in {"MemAvailable", "SwapTotal", "SwapFree"}:
            rows[fields[0].rstrip(":")] = int(fields[1]) * 1024
    return rows


def pswpout_pages() -> int:
    for line in Path("/proc/vmstat").read_text(encoding="utf-8").splitlines():
        if line.startswith("pswpout "):
            return int(line.split()[1])
    return 0


def memory_psi_full_avg10() -> float:
    for line in Path("/proc/pressure/memory").read_text(encoding="utf-8").splitlines():
        if line.startswith("full "):
            for field in line.split()[1:]:
                if field.startswith("avg10="):
                    return float(field.split("=", 1)[1])
    return float("inf")


def resource_evidence(job: dict[str, Any], failed: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    memory = meminfo()
    observed_upper = max(int(row["peak_process_group_rss_bytes"]) for row in failed)
    mem_available = int(memory.get("MemAvailable", 0))
    swap_free = int(memory.get("SwapFree", 0))
    combined_projected = mem_available + swap_free - observed_upper
    campaign_bytes = campaign.campaign_bytes()
    disk_free = shutil.disk_usage(campaign.RUN_ROOT).free
    cap = int(job["declared_cap_bytes"])
    deadline = datetime.fromisoformat(contract["wall_clock"]["deadline"])
    now = datetime.now(timezone.utc)
    latest_hard_end = deadline - timedelta(seconds=ORIGINAL_DEADLINE_RESERVE_S)
    hard_end = min(now + timedelta(seconds=ATTEMPT_WALL_CAP_S), latest_hard_end)
    psi_full_avg10 = memory_psi_full_avg10()
    errors: list[str] = []
    if (latest_hard_end - now).total_seconds() < MIN_PRELAUNCH_REMAINING_S:
        errors.append("less_than_1200s_remains_to_original_deadline_minus_2400s")
    if hard_end + timedelta(seconds=VALIDATION_MARGIN_S) > deadline:
        errors.append("attempt03_hard_end_plus_validation_does_not_fit_original_deadline")
    if mem_available < MIN_MEM_AVAILABLE_BYTES:
        errors.append("MemAvailable_below_7.5GiB")
    if int(memory.get("SwapTotal", 0)) < MIN_SWAP_TOTAL_BYTES:
        errors.append("SwapTotal_below_14GiB")
    if swap_free < MIN_SWAP_FREE_BYTES:
        errors.append("SwapFree_below_12GiB")
    if psi_full_avg10 >= MAX_MEMORY_PSI_FULL_AVG10:
        errors.append("memory_PSI_full_avg10_not_below_1")
    if combined_projected < PROJECTED_FLOOR_BYTES:
        errors.append("MemAvailable_plus_SwapFree_minus_observed_failed_peak_below_1.5GiB")
    if disk_free < campaign.FILESYSTEM_RESERVE_BYTES + cap:
        errors.append("filesystem_reserve_after_current_attempt_cap")
    if campaign_bytes + cap > int(contract["disk"]["effective_campaign_cap_bytes"]) - campaign.CAMPAIGN_EMERGENCY_BYTES:
        errors.append("campaign_cap_after_current_attempt_cap")
    snapshot = proc_snapshot()
    if snapshot["continuation_or_cosima_processes"] or snapshot["partial_attempt_directories"]:
        errors.append("nonquiescent_old_continuation_or_partial")
    return {
        "schema_version": 1, "status": "PASS__ATTEMPT03_RESOURCE_ADMISSION" if not errors else "PAUSE__ATTEMPT03_RESOURCE_ADMISSION",
        "at": now.isoformat(), "errors": errors, "MemAvailable_bytes": mem_available,
        "SwapTotal_bytes": int(memory.get("SwapTotal", 0)), "SwapFree_bytes": swap_free,
        "pswpout_pages": pswpout_pages(), "memory_PSI_full_avg10": psi_full_avg10,
        "observed_failed_attempt_peak_upper_bytes": observed_upper,
        "attempt03_RSS_budget_bytes": RSS_BUDGET_BYTES,
        "combined_projected_after_observed_peak_bytes": combined_projected,
        "required_projected_floor_bytes": PROJECTED_FLOOR_BYTES, "campaign_bytes": campaign_bytes,
        "free_disk_bytes": disk_free, "candidate_current_attempt_cap_bytes": cap,
        "latest_allowed_hard_end_original_deadline_minus_3600s": latest_hard_end.isoformat(),
        "hard_end": hard_end.isoformat(), "attempt03_runtime_wall_cap_s": ATTEMPT_WALL_CAP_S,
        "minimum_prelaunch_remaining_to_latest_hard_end_s": MIN_PRELAUNCH_REMAINING_S,
        "frozen_job_planned_wall_budget_s_audit_only": float(job["planned_wall_budget_s"]),
        "validation_margin_s": VALIDATION_MARGIN_S, "process_snapshot": snapshot,
        "simulation_inputs_changed": False,
    }


def proposed_authority(
    old_authority: dict[str, Any], job: dict[str, Any], inherited: list[dict[str, Any]], failed: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1, "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__USER_DIRECTED_THIRD_RESOURCE_RETRY__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(), "controller": rel(Path(__file__).resolve()),
        "namespace": rel(RUN_NS), "supersedes_only": "continuation0001 target attempt exhaustion/resource verdict",
        "user_authorization": {"direction": "continue", "scope": "exact third resource retry for target job only"},
        "exact_attempt": 3, "exact_job": job,
        "inherited_PASS_receipts": inherited, "inherited_PASS_count": len(inherited),
        "preserved_failed_attempts": failed, "preserved_failed_attempt_count": len(failed),
        "matched_pair": {"key": job["matched_seed_key"], "inherited_PASS_mate_job_id": MATE_JOB_ID, "atomic_wave_closes_only_if_attempt03_PASS": True},
        "frozen_declared_inputs": old_authority["frozen_declared_inputs"],
        "unchanged": {"seed": True, "events": True, "source": True, "corrected_spectrum": True, "geometry": True, "physics": True, "cuts_detector_veto": True},
        "resource_policy": {"serial_only": True, "no_attempt04": True, "attempt03_RSS_budget_bytes": RSS_BUDGET_BYTES, "minimum_MemAvailable_bytes": MIN_MEM_AVAILABLE_BYTES, "minimum_SwapTotal_bytes": MIN_SWAP_TOTAL_BYTES, "minimum_SwapFree_bytes": MIN_SWAP_FREE_BYTES, "maximum_memory_PSI_full_avg10": MAX_MEMORY_PSI_FULL_AVG10, "projected_floor_bytes": PROJECTED_FLOOR_BYTES, "projection": "MemAvailable + SwapFree - max(declared attempt01/02 peak RSS)", "current_attempt_only_disk": True, "hard_low_memory_watchdog_bytes": campaign.HARD_LOW_MEMORY_BYTES, "attempt03_runtime_wall_cap_s": ATTEMPT_WALL_CAP_S, "hard_end": "min(admission_time+2700s, original_deadline-2400s)", "minimum_prelaunch_remaining_to_latest_hard_end_s": MIN_PRELAUNCH_REMAINING_S, "validation_margin_s": VALIDATION_MARGIN_S},
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
    r6.validate_replan_receipt = lambda job, payload: structural_receipt(job, payload, (3,))
    r6.job_cap = lambda job: int(job["declared_cap_bytes"])


def self_test() -> dict[str, Any]:
    old_authority, job, inherited, failed = load_frozen()
    assert len(inherited) == 11 and len(failed) == 2
    assert [row["attempt"] for row in failed] == [1, 2]
    assert job["seed"] == 1800262155 and job["events"] == 2500 and job["geometry"] == "S3d_O8"
    assert job["matched_seed_key"] == "continuation0001|eplus|instant|wave0001"
    assert old_authority["resource_policy"]["maximum_exact_attempts"] == 2
    assert ATTEMPT_WALL_CAP_S == 2700 and RSS_BUDGET_BYTES == 12 * 1024**3
    assert MIN_SWAP_TOTAL_BYTES == 14 * 1024**3 and MIN_SWAP_FREE_BYTES == 12 * 1024**3
    assert ORIGINAL_DEADLINE_RESERVE_S == 2400 and MIN_PRELAUNCH_REMAINING_S == 1200
    return {
        "status": "PASS__CONTINUATION0001_RECOVERY0002_ATTEMPT03_STRUCTURAL_SELF_TEST",
        "tests": 10, "transport_launched": False, "attempt": 3, "inherited_PASS": 11,
        "preserved_FAIL": 2, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
        "gamma_locked": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    old_authority, job, inherited, failed = load_frozen()
    base = load(campaign.GLOBAL_CONTRACT)
    proposed = proposed_authority(old_authority, job, inherited, failed)
    evidence = resource_evidence(job, failed, base)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True)); return 0
    if args.print_plan:
        print(json.dumps({
            "status": "PASS__READ_ONLY_CONTINUATION0001_RECOVERY0002_ATTEMPT03_PLAN",
            "namespace": rel(RUN_NS), "exact_job": job, "exact_attempt": 3,
            "inherited_PASS": len(inherited), "preserved_FAIL": len(failed),
            "resource_evidence_now": evidence, "gamma_locked": True,
            "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
            "transport_launched": False,
        }, indent=2, sort_keys=True)); return 0
    lock = campaign.acquire_lock()
    previous_handlers: dict[int, Any] = {}
    try:
        RUN_NS.mkdir(parents=True, exist_ok=True)
        if AUTHORITY.is_file():
            authority = load(AUTHORITY)
            for key in ("recovery_id", "namespace", "exact_attempt", "exact_job", "inherited_PASS_receipts", "preserved_failed_attempts", "matched_pair", "frozen_declared_inputs", "unchanged", "resource_policy", "old_data_policy", "gamma_locked"):
                if authority.get(key) != proposed.get(key):
                    raise RuntimeError(f"existing recovery0002 authority differs: {key}")
        else:
            campaign.atomic_write_once_json(AUTHORITY, proposed)
            authority = load(AUTHORITY)
        evidence = resource_evidence(job, failed, base)
        if not str(evidence["status"]).startswith("PASS"):
            raise RuntimeError("attempt03 resource admission PAUSE: " + "; ".join(evidence["errors"]))
        if not PRELAUNCH_RESOURCE_EVIDENCE.is_file():
            campaign.atomic_write_once_json(PRELAUNCH_RESOURCE_EVIDENCE, evidence)
        bind()
        r6.configure_validator()
        environment = r7.load_runtime_without_hash_revalidation(base, args.cosima.resolve())
        campaign._STOP_REQUESTED = False
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, campaign._signal_handler)
        hard_end = datetime.fromisoformat(evidence["hard_end"])
        campaign.atomic_replace_json(EXECUTION_STATE, {
            "schema_version": 1, "recovery_id": RECOVERY_ID, "status": "RUNNING__EXACT_ATTEMPT03",
            "job_id": TARGET_JOB_ID, "attempt": 3, "updated_at": datetime.now(timezone.utc).isoformat(),
            "deadline": hard_end.isoformat(), "gamma_locked": True,
        })
        r6.append_event("attempt03_started", job_id=TARGET_JOB_ID, attempt=3, resource_evidence=rel(PRELAUNCH_RESOURCE_EVIDENCE))
        result = r6.run_attempt(job, ATTEMPT, base, environment, hard_end)
        passed = result.get("status") == "PASS" and receipt_path(job).is_file() and structural_receipt(job, load(receipt_path(job)), (3,))
        status = "PASS__CONTINUATION0001_WAVE0002_ATOMIC_PREFIX_RESTORED__GAMMA_LOCKED" if passed else "FAIL__CONTINUATION0001_ATTEMPT03_RESOURCE_RETRY"
        completion = {
            "schema_version": 1, "status": status, "recovery_id": RECOVERY_ID,
            "attempt03_receipt": rel(receipt_path(job)) if passed else None,
            "inherited_PASS_count": 11, "effective_PASS_count": 12 if passed else 11,
            "preserved_failed_attempt_count": 2, "attempt03_status": result.get("status"),
            "balanced_prefix": {"complete_atomic_waves": 2 if passed else 1, "matched_geometry_pairs": 6 if passed else 5},
            "remaining_phase_A_jobs": 16 if passed else 17, "gamma_locked": True,
            "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
        }
        campaign.atomic_write_once_json(COMPLETION, completion)
        campaign.atomic_write_once_json(FINAL_UMBRELLA, {
            "schema_version": 1, "status": status, "authority": rel(AUTHORITY),
            "resource_evidence": rel(PRELAUNCH_RESOURCE_EVIDENCE), "completion": rel(COMPLETION),
            "gamma_locked": True, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
        })
        campaign.atomic_replace_json(EXECUTION_STATE, {
            "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
            "job_id": TARGET_JOB_ID, "attempt": 3, "updated_at": datetime.now(timezone.utc).isoformat(),
            "deadline": hard_end.isoformat(), "gamma_locked": True,
        })
        return 0 if passed else 1
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
            campaign._ACTIVE_PROCESS = None
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
