#!/usr/bin/env python3
"""Recovery0008: r7 continuation with current-attempt-only disk admission.

The event plan, seeds, sources, geometry, physics, deadline, output caps,
target-six/cap-ten concurrency, and 1.5-GiB MemAvailable gate are inherited
unchanged.  Disk admission reserves only each active current attempt's
remaining hard cap plus the candidate current attempt's hard cap.  A failed
attempt returns to the coordinator and attempt 2 is admitted as a fresh
candidate through the complete memory/disk/deadline gate; workers never retry
immediately on their own.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import multiprocessing as mp
import os
import re
import shutil
import signal
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6
import resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler as r7
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0008_current_attempt_disk_admission"
R7_NS = campaign.RUN_ROOT / "recovery0007_efficiency_scheduler"
RUN_NS = campaign.RUN_ROOT / "recovery0008_current_attempt_disk_admission"
AUTHORITY = RUN_NS / "authority.json"
CUTOVER_RECEIPT = RUN_NS / "cutover_receipt.json"
SEED_REGISTRY = RUN_NS / "seed_registry.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
FINAL_VALIDATION = RUN_NS / "final_validation.json"
FINAL_LEDGER = RUN_NS / "final_ledger.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"
CUTOVER_COMPLETION = campaign.RUN_ROOT / "recovery0008_disk_admission_cutover_completion.json"
R7_CONTROLLER_NAME = "resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler.py"
R7_CALIBRATIONS = {
    mode: R7_NS / f"stage20_{mode}_2048_calibration.json" for mode in campaign.MODES
}

_PRIOR: dict[str, dict[str, Any]] = {}
_RETRY_REQUESTED: set[str] = set()
_R7_RUN_STAGE = r7.run_stage


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def r7_receipt_path(job: dict[str, Any]) -> Path:
    return R7_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def r8_receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def receipt_path(job: dict[str, Any]) -> Path:
    row = _PRIOR.get(str(job["job_id"]))
    return campaign.ROOT / str(row["path"]) if row is not None else r8_receipt_path(job)


def structural_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    if payload.get("status") != "PASS" or payload.get("job") != job:
        return False
    attempt = payload.get("selected_attempt")
    directory = campaign.ROOT / str(payload.get("attempt_dir", ""))
    framing = payload.get("sim", {}).get("strict_framing", {})
    events = int(job["events"])
    return (
        attempt in (1, 2) and directory.is_dir()
        and framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == events
        and int(framing.get("ID_second_count", -1)) == events
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == events
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == events
    )


def validate_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    # Existing r6/r7 sidecars are trusted structurally; no artifact hash/gzip
    # replay occurs at cutover or startup.  New r8 validation is generated in
    # the attempt itself and only structurally re-read after publication.
    return structural_receipt(job, payload)


def prior_receipts(pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in pending:
        candidates = (r7.r6_receipt_path(job), r7_receipt_path(job))
        present = [path for path in candidates if path.is_file()]
        if len(present) > 1:
            raise RuntimeError(f"duplicate prior receipt publications: {job['job_id']}")
        if not present:
            continue
        payload = load(present[0])
        if not structural_receipt(job, payload):
            raise RuntimeError(f"prior receipt structural declaration failed: {job['job_id']}")
        job_id = str(job["job_id"])
        if job_id in seen:
            raise RuntimeError(f"duplicate prior receipt id: {job_id}")
        seen.add(job_id)
        rows.append({
            "job_id": job_id, "path": rel(present[0]), "events": int(job["events"]),
            "selected_attempt": int(payload["selected_attempt"]),
            "declared_recovery_authority_sha256": payload.get("recovery_authority_sha256"),
        })
    return rows


def process_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ns = str(R7_NS.resolve())
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc.name)
            if pid == os.getpid():
                continue
            cmd = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            comm = proc.joinpath("comm").read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if R7_CONTROLLER_NAME in cmd or (comm == "cosima" and ns in cmd):
            rows.append({"pid": pid, "comm": comm})
    partials = sorted(
        rel(path) for namespace in (R7_NS, RUN_NS)
        for path in namespace.glob("attempts/**/.attempt*.partial") if path.is_dir()
    )
    return {"matching_r7_processes": rows, "unresolved_partials": partials}


def disk_projection(
    contract: dict[str, Any], stage: str, active: list[r6.Worker], candidate: dict[str, Any],
) -> dict[str, Any]:
    used = campaign.campaign_bytes()
    free = shutil.disk_usage(campaign.RUN_ROOT).free
    active_remaining = 0
    for worker in active:
        frozen = {key: value for key, value in worker.job.items() if not key.startswith("_runtime_")}
        active_remaining += max(0, r6.job_cap(frozen) - r6.attempt_bytes_for_active(worker))
    candidate_cap = r6.job_cap(candidate)
    reserve = 20_000_000_000 if stage == "stage10_seven_family" else campaign.CAMPAIGN_EMERGENCY_BYTES
    limit = int(contract["disk"]["effective_campaign_cap_bytes"]) - reserve
    errors: list[str] = []
    if used + active_remaining + candidate_cap > limit:
        errors.append("campaign_cap_after_current_attempt_reservations")
    if free < campaign.FILESYSTEM_RESERVE_BYTES + active_remaining + candidate_cap:
        errors.append("filesystem_reserve_after_current_attempt_reservations")
    return {
        "status": "PASS" if not errors else "PAUSE", "campaign_bytes": used,
        "free_bytes": free, "active_current_attempt_remaining_cap_bytes": active_remaining,
        "candidate_current_attempt_cap_bytes": candidate_cap, "campaign_reserve_bytes": reserve,
        "stage_limit_bytes": limit, "potential_future_retries_reserved_early": False, "errors": errors,
    }


def inherited_stage20_calibration(
    mode: str, pending: list[dict[str, Any]], authority: dict[str, Any],
    registry: dict[str, Any], *, publish: bool,
) -> dict[str, Any] | None:
    """Read the frozen r7 sidecar structurally; never hash or republish it."""
    del authority, registry, publish
    if mode not in campaign.MODES:
        raise RuntimeError(f"unknown stage20 calibration mode: {mode}")
    path = R7_CALIBRATIONS[mode]
    if not path.is_file():
        return None
    payload = load(path)
    if (
        payload.get("status") != "PASS__STAGE20_PAIRED_512_1024_CANARIES__2048_BUDGET_FROZEN"
        or payload.get("mode") != mode
    ):
        raise RuntimeError(f"r7 stage20 {mode} calibration declaration is not PASS")
    budgets = payload.get("planned_peak_rss_budget_2048_bytes")
    walls = payload.get("planned_wall_budget_2048_s")
    if not isinstance(budgets, dict) or not isinstance(walls, dict):
        raise RuntimeError(f"r7 stage20 {mode} calibration lacks budget declarations")
    for geometry in campaign.GEOMETRY_ORDER:
        if int(budgets.get(geometry, 0)) < 1024**3 or float(walls.get(geometry, 0.0)) <= 0:
            raise RuntimeError(f"r7 stage20 {mode} calibration budget invalid: {geometry}")
    canaries = r6.stage20_canary_jobs(mode, pending)
    declared = payload.get("canary_receipts")
    if len(canaries) != 4 or not isinstance(declared, list) or len(declared) != 4:
        raise RuntimeError(f"r7 stage20 {mode} calibration canary declaration count drift")
    expected = {
        (str(job["job_id"]), int(job["events"]), int(job["seed"])) for job in canaries
    }
    observed = {
        (str(row.get("job_id")), int(row.get("events", -1)), int(row.get("seed", -1)))
        for row in declared if isinstance(row, dict)
    }
    if observed != expected:
        raise RuntimeError(f"r7 stage20 {mode} calibration canary identity drift")
    return payload


def runtime_job_budget(
    job: dict[str, Any], pending: list[dict[str, Any]], authority: dict[str, Any], registry: dict[str, Any],
) -> int:
    if not job.get("requires_stage20_canary_calibration"):
        return int(job["planned_peak_rss_budget_bytes"])
    payload = inherited_stage20_calibration(str(job["mode"]), pending, authority, registry, publish=False)
    if payload is None:
        raise RuntimeError("missing inherited r7 stage20 calibration sidecar")
    return int(payload["planned_peak_rss_budget_2048_bytes"][str(job["geometry"])])


def runtime_job_wall_budget(
    job: dict[str, Any], pending: list[dict[str, Any]], authority: dict[str, Any], registry: dict[str, Any],
) -> float:
    if not job.get("requires_stage20_canary_calibration"):
        return float(job["planned_wall_budget_s"])
    payload = inherited_stage20_calibration(str(job["mode"]), pending, authority, registry, publish=False)
    if payload is None:
        raise RuntimeError("missing inherited r7 stage20 calibration sidecar")
    return float(payload["planned_wall_budget_2048_s"][str(job["geometry"])])


def prior_exact_attempts(job: dict[str, Any]) -> set[int]:
    """Count attempts across every preserved namespace; read JSON only."""
    roots = [
        campaign.RUN_ROOT / "failed_attempts" / str(job["job_id"]),
        campaign.RUN_ROOT / "failed_attempts" / "recovery0006_cutover_orphan" / str(job["job_id"]),
        r7.R6_NS / "failed_attempts" / str(job["job_id"]),
        R7_NS / "failed_attempts" / str(job["job_id"]),
        RUN_NS / "failed_attempts" / str(job["job_id"]),
    ]
    identity = ("job_id", "seed", "events", "geometry", "mode", "family", "source_tag")
    used: set[int] = set()
    for root in roots:
        for path in root.glob("attempt*/validation.json"):
            match = re.fullmatch(r"attempt(\d+)", path.parent.name)
            if not match:
                continue
            old = load(path).get("job", {})
            if all(old.get(key) == job.get(key) for key in identity):
                used.add(int(match.group(1)))
    return used


def ensure_one_attempt(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str],
    hard_deadline: datetime, runtime_wall_budget_s: float | None,
) -> tuple[str, dict[str, Any]]:
    path = receipt_path(job)
    if path.is_file():
        payload = load(path)
        if not validate_receipt(job, payload):
            raise RuntimeError(f"receipt structural closure failed: {job['job_id']}")
        return "PASS", payload
    used = r6.prior_exact_attempts(job)
    available = [attempt for attempt in range(1, campaign.MAX_ATTEMPTS + 1) if attempt not in used]
    if not available:
        raise RuntimeError(f"{job['job_id']} exhausted two total exact attempts")
    attempt = available[0]
    wall = float(runtime_wall_budget_s if runtime_wall_budget_s is not None else job["planned_wall_budget_s"])
    if campaign._STOP_REQUESTED or datetime.now(timezone.utc) >= hard_deadline:
        raise RuntimeError("stop/deadline before exact attempt")
    if datetime.now(timezone.utc) + timedelta(seconds=wall + r6.VALIDATION_PUBLICATION_MARGIN_S) > hard_deadline:
        raise RuntimeError("insufficient hard-deadline budget before exact attempt")
    free = shutil.disk_usage(campaign.RUN_ROOT).free
    used_bytes = campaign.campaign_bytes()
    cap = r6.job_cap(job)
    reserve = 20_000_000_000 if job["stage"] == "stage10_seven_family" else campaign.CAMPAIGN_EMERGENCY_BYTES
    if free < campaign.FILESYSTEM_RESERVE_BYTES + cap:
        raise RuntimeError("insufficient filesystem reserve before exact attempt")
    if used_bytes + cap > int(contract["disk"]["effective_campaign_cap_bytes"]) - reserve:
        raise RuntimeError("insufficient campaign cap before exact attempt")
    result = r6.run_attempt(job, attempt, contract, environment, hard_deadline)
    if result["status"] == "PASS":
        return "PASS", result
    if result.get("watchdog_reason") == "recovery0006_job_hard_cap_exceeded__stop_stage":
        raise RuntimeError("job hard cap exceeded; evidence preserved and stage must stop")
    remaining = [number for number in range(1, campaign.MAX_ATTEMPTS + 1) if number not in r6.prior_exact_attempts(job)]
    return ("RETRY", result) if remaining else ("FAIL", result)


def worker_entry(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_end_iso: str,
    runtime_wall_budget_s: float | None, connection: Any,
) -> None:
    r6.configure_validator()
    campaign._STOP_REQUESTED = False
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, campaign._signal_handler)
    try:
        status, result = ensure_one_attempt(
            job, contract, environment, datetime.fromisoformat(hard_end_iso), runtime_wall_budget_s,
        )
        connection.send({
            "status": status, "job_id": job["job_id"], "events": job["events"],
            "receipt": rel(receipt_path(job)) if status == "PASS" else None,
            "wall_s": result.get("wall_s"),
        })
    except BaseException as exc:
        connection.send({"status": "FAIL", "job_id": job["job_id"], "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
        connection.close()


def reap(active: list[r6.Worker], failures: list[str]) -> list[r6.Worker]:
    keep: list[r6.Worker] = []
    for worker in active:
        if worker.process.is_alive():
            keep.append(worker)
            continue
        worker.process.join(timeout=1)
        if worker.connection.poll():
            try:
                message = worker.connection.recv()
            except EOFError:
                message = {"status": "FAIL", "error": "pipe EOF"}
        else:
            message = {"status": "FAIL", "error": f"exit {worker.process.exitcode} without result"}
        worker.connection.close()
        r6._ACTIVE_WORKERS.pop(worker.process.pid, None)
        frozen = {key: value for key, value in worker.job.items() if not key.startswith("_runtime_")}
        status = message.get("status")
        if status == "PASS" and receipt_path(frozen).is_file() and validate_receipt(frozen, load(receipt_path(frozen))):
            r6.append_event("worker_reaped_PASS", job_id=worker.job["job_id"], worker_pid=worker.process.pid)
        elif status == "RETRY":
            _RETRY_REQUESTED.add(str(worker.job["job_id"]))
            r6.append_event(
                "worker_reaped_RETRY_REQUEUED", job_id=worker.job["job_id"],
                worker_pid=worker.process.pid, next_attempt_requires_full_global_admission=True,
            )
        else:
            failures.append(f"{worker.job['job_id']}: {message.get('error', 'receipt closure failed')}")
            r6.append_event("worker_reaped_FAIL", job_id=worker.job["job_id"], worker_pid=worker.process.pid, detail=message)
    return keep


def run_stage(
    stage: str, pending_plan: list[dict[str, Any]], original: list[dict[str, Any]],
    contract: dict[str, Any], environment: dict[str, str], authority: dict[str, Any], registry: dict[str, Any],
) -> str | None:
    passes = 0
    while True:
        passes += 1
        _RETRY_REQUESTED.clear()
        reason = _R7_RUN_STAGE(stage, pending_plan, original, contract, environment, authority, registry)
        if reason:
            return reason
        missing = [job for job in pending_plan if job["stage"] == stage and not receipt_path(job).is_file()]
        if not missing:
            return None
        missing_ids = {str(job["job_id"]) for job in missing}
        if not missing_ids.issubset(_RETRY_REQUESTED):
            return f"stage ended with unscheduled missing jobs: {sorted(missing_ids - _RETRY_REQUESTED)[:4]}"
        r6.append_event(
            "retry_admission_epoch_start", stage=stage, pass_number=passes + 1,
            retry_jobs=sorted(missing_ids), full_global_memory_disk_deadline_gate=True,
        )


def structural_publish_final(
    original: list[dict[str, Any]], manifest: list[dict[str, Any]], pending: list[dict[str, Any]],
    authority: dict[str, Any], fatal: str | None,
) -> None:
    """Publish declaration-only final closure without hashing or gzip reads."""
    if r6._ACTIVE_WORKERS or list(RUN_NS.glob("attempts/**/.attempt*.partial")):
        raise RuntimeError("r8 final publication requires quiescence and zero partial attempts")
    terminal_paths = (FINAL_VALIDATION, FINAL_LEDGER, FINAL_UMBRELLA)
    existing = [path.is_file() for path in terminal_paths]
    if any(existing):
        if not all(existing):
            raise RuntimeError("partial pre-existing r8 final publication set")
        return
    by_id = {str(job["job_id"]): job for job in original}
    selected: list[dict[str, Any]] = []
    cell_totals: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    def add(kind: str, job: dict[str, Any], path: Path) -> None:
        payload = load(path)
        if not structural_receipt(job, payload):
            raise RuntimeError(f"r8 final receipt declaration failed: {job['job_id']}")
        isotope = payload.get("isotope_dat") if isinstance(payload.get("isotope_dat"), dict) else {}
        tt = float(isotope.get("TT_s", 0.0))
        rp = int(isotope.get("RP_record_count", 0))
        row = {
            "kind": kind, "job_id": str(job["job_id"]), "events": int(job["events"]),
            "path": rel(path), "declared_status": payload.get("status"),
            "selected_attempt": int(payload["selected_attempt"]),
            "declared_recovery_authority_sha256": payload.get("recovery_authority_sha256"),
            "declared_TT_s": tt, "declared_RP_record_count": rp,
            "declared_strict_framing": payload.get("sim", {}).get("strict_framing"),
        }
        selected.append(row)
        key = (str(job["stage"]), str(job["geometry"]), str(job["mode"]), str(job["family"]))
        cell = cell_totals.setdefault(key, {
            "stage": key[0], "geometry": key[1], "mode": key[2], "family": key[3],
            "events": 0, "receipts": 0, "TT_s": 0.0, "RP_count": 0,
        })
        cell["events"] += int(job["events"])
        cell["receipts"] += 1
        cell["TT_s"] = math.fsum((float(cell["TT_s"]), tt))
        cell["RP_count"] += rp

    for declared in manifest:
        job_id = str(declared["job_id"])
        if job_id not in by_id:
            raise RuntimeError(f"r8 final inherited job absent from original plan: {job_id}")
        path = campaign.ROOT / str(declared["path"])
        if not path.is_file():
            raise RuntimeError(f"r8 final inherited receipt missing: {job_id}")
        add("inherited_original", by_id[job_id], path)
    missing: list[str] = []
    for job in pending:
        path = receipt_path(job)
        if not path.is_file():
            missing.append(str(job["job_id"]))
            continue
        add(str(job.get("replan_kind", "retained_old_exact_mate")), job, path)

    original_cells: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for job in original:
        key = (str(job["stage"]), str(job["geometry"]), str(job["mode"]), str(job["family"]))
        original_cells[key] += int(job["events"])
    cells = [cell_totals[key] for key in sorted(cell_totals)]
    cell_errors = [
        cell for cell in cells
        if int(cell["events"]) != original_cells[(cell["stage"], cell["geometry"], cell["mode"], cell["family"])]
    ]
    events = sum(int(row["events"]) for row in selected)
    complete = (
        fatal is None and not missing and len(selected) == r6.EXPECTED_FINAL_RECEIPTS
        and events == r6.EXPECTED_TOTAL_EVENTS and not cell_errors
    )
    status = (
        "PASS__REPLANNED_MAINLINE_EVENT_TARGET_COMPLETE"
        if complete else "FAIL__RECOVERY0008_INCOMPLETE_OR_RESOURCE_AUTHORITY_ERROR"
    )
    calibrations = {
        mode: {
            "path": rel(path),
            "declared_status": load(path).get("status") if path.is_file() else None,
            "inherited_read_only": True,
        }
        for mode, path in R7_CALIBRATIONS.items()
    }
    validation = {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "closure_mode": "receipt_JSON_declarations_only",
        "artifact_hashes_recomputed": False, "gzip_reopened": False,
        "errors": [fatal] if fatal else [], "missing_jobs": missing,
        "selected_receipts": selected, "validated_receipts": len(selected),
        "validated_events": events, "cells": cells, "cell_errors": cell_errors,
        "stage20_calibrations": calibrations,
        "effective_pending_plan_declared_sha256": authority.get("effective_pending_plan_declared_sha256"),
    }
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    ledger = {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "validation": rel(FINAL_VALIDATION), "selected_receipts": selected,
        "artifact_hashes_recomputed": False, "gzip_reopened": False,
        "errors": validation["errors"], "missing_jobs": missing,
    }
    campaign.atomic_write_once_json(FINAL_LEDGER, ledger)
    campaign.atomic_write_once_json(FINAL_UMBRELLA, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "authority": rel(AUTHORITY), "cutover_receipt": rel(CUTOVER_RECEIPT),
        "seed_registry": rel(SEED_REGISTRY), "final_validation": rel(FINAL_VALIDATION),
        "final_ledger": rel(FINAL_LEDGER), "stage20_calibrations": calibrations,
        "closure_mode": "structural_declarations_only", "artifact_hashes_recomputed": False,
        "gzip_reopened": False, "errors": validation["errors"],
    })


def bind(prior: list[dict[str, Any]]) -> None:
    global _PRIOR
    _PRIOR = {str(row["job_id"]): row for row in prior}
    r7.bind_recovery0007([])
    for module in (r7, r6):
        module.RECOVERY_ID = RECOVERY_ID
        module.RUN_NS = RUN_NS
        module.AUTHORITY = AUTHORITY
        module.CUTOVER_RECEIPT = CUTOVER_RECEIPT
        module.SCHEDULER_EVENTS = SCHEDULER_EVENTS
        module.EXECUTION_STATE = EXECUTION_STATE
        module.FINAL_VALIDATION = FINAL_VALIDATION
        module.FINAL_LEDGER = FINAL_LEDGER
        module.FINAL_UMBRELLA = FINAL_UMBRELLA
    r6.REPLAN_SEED_REGISTRY = SEED_REGISTRY
    r7.SEED_REGISTRY = SEED_REGISTRY
    r7._R6_INHERITED = _PRIOR
    r7.receipt_path = receipt_path
    r7.validate_replan_receipt = validate_receipt
    r6.receipt_path = receipt_path
    r6.validate_replan_receipt = validate_receipt
    r6.disk_projection = disk_projection
    r6.prior_exact_attempts = prior_exact_attempts
    r7.prior_exact_attempts = prior_exact_attempts
    r6.load_or_publish_stage20_calibration = inherited_stage20_calibration
    r6.runtime_job_budget = runtime_job_budget
    r6.runtime_job_wall_budget = runtime_job_wall_budget
    r7.inherited_stage20_calibration = inherited_stage20_calibration
    r7.runtime_job_budget = runtime_job_budget
    r7.runtime_job_wall_budget = runtime_job_wall_budget
    r6.worker_entry = worker_entry
    r6.reap = reap
    r6.run_stage = run_stage
    r7.run_stage = run_stage
    r6.publish_final = structural_publish_final


def self_test() -> dict[str, Any]:
    assert campaign.MAX_ATTEMPTS == 2
    assert r7.MINIMUM_TARGET_WORKERS == 6 and r7.ABSOLUTE_MAX_WORKERS == 10
    assert r7.PROJECTED_FLOOR_BYTES == int(1.5 * 1024**3)
    dummy = {"stage": "stage20_proton", "replan_kind": "fresh_balanced_bundle"}
    assert r6.job_cap(dummy) == 6_000_000_000
    contract, original, original_manifest, pending, registry = r7.load_frozen_inputs()
    del contract, original, original_manifest
    for mode in campaign.MODES:
        calibration = inherited_stage20_calibration(mode, pending, {}, registry, publish=True)
        assert calibration is not None
        assert R7_CALIBRATIONS[mode].parent == R7_NS
    return {
        "status": "PASS__RECOVERY0008_MINIMAL_STATIC_SELF_TEST", "tests": 8,
        "transport_launched": False, "hashes_recomputed": False, "gzip_reopened": False,
        "calibrations_republished": False, "structural_final_bound": True,
    }


def proposed_authority(
    contract: dict[str, Any], pending: list[dict[str, Any]], prior: list[dict[str, Any]], completion: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1, "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__CURRENT_ATTEMPT_ONLY_DISK_ADMISSION__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "controller": {"path": rel(Path(__file__).resolve()), "hash_computed_or_required": False},
        "cutover_completion": completion,
        "effective_pending_plan": pending,
        "effective_pending_plan_declared_sha256": r7.EXPECTED_PENDING_PLAN_SHA256,
        "prior_pass_receipts": prior, "prior_pass_count": len(prior),
        "scheduler": {
            "minimum_target_workers": 6, "absolute_worker_cap": 10,
            "launch_stagger_s": r7.LAUNCH_STAGGER_S,
            "projected_mem_available_floor_bytes": r7.PROJECTED_FLOOR_BYTES,
            "maximum_exact_attempts": 2,
            "disk_admission": "active current-attempt remaining cap + candidate current-attempt cap only",
            "potential_future_retry_reserved_early": False,
            "retry_policy": "failed attempt returns to coordinator; attempt02 is a new candidate and must pass the full global memory/disk/deadline gate",
        },
        "unchanged": {
            "seeds_events_sources_spectra_geometry_physics_cuts_detector_veto": True,
            "job_output_caps": True, "deadline": True, "event_target": r6.EXPECTED_TOTAL_EVENTS,
        },
        "startup_validation": {"hashes_recomputed": False, "gzip_reopened": False, "artifacts_revalidated": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    contract, original, original_manifest, pending, registry = r7.load_frozen_inputs()
    prior = prior_receipts(pending)
    completion = load(CUTOVER_COMPLETION) if CUTOVER_COMPLETION.is_file() else None
    proposed = proposed_authority(contract, pending, prior, completion or {})
    if args.print_recovery_plan:
        print(json.dumps({
            "status": "PASS__READ_ONLY_RECOVERY0008_PLAN", "scheduler": proposed["scheduler"],
            "prior_pass_count": len(prior), "cutover_completion_present": completion is not None,
            "transport_launched": False, "hashes_recomputed": False, "gzip_reopened": False,
        }, indent=2, sort_keys=True))
        return 0
    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        snapshot = process_snapshot()
        if snapshot["matching_r7_processes"] or snapshot["unresolved_partials"]:
            raise RuntimeError(f"r7 cutover is not clean: {snapshot}")
        if completion is None or not str(completion.get("status", "")).startswith("PASS"):
            raise RuntimeError("missing PASS r7->r8 cutover completion")
        required = (
            completion.get("zero_r6_related_non_z_processes") is True,
            completion.get("zero_partial_attempts") is True,
            completion.get("exclusive_campaign_flock_held_during_publication") is True,
            completion.get("hashes_computed") is False,
        )
        if not all(required):
            raise RuntimeError("r7->r8 cutover completion lacks structural closure")
        prior = prior_receipts(pending)
        proposed = proposed_authority(contract, pending, prior, completion)
        RUN_NS.mkdir(parents=True, exist_ok=True)
        if AUTHORITY.exists():
            authority = load(AUTHORITY)
            for key in (
                "recovery_id", "cutover_completion", "effective_pending_plan",
                "effective_pending_plan_declared_sha256", "prior_pass_receipts",
                "scheduler", "unchanged", "startup_validation",
            ):
                if authority.get(key) != proposed.get(key):
                    raise RuntimeError(f"existing recovery0008 authority differs: {key}")
        else:
            campaign.atomic_write_once_json(AUTHORITY, proposed)
            authority = load(AUTHORITY)
        if not SEED_REGISTRY.exists():
            campaign.atomic_write_once_json(SEED_REGISTRY, registry)
        if not CUTOVER_RECEIPT.exists():
            campaign.atomic_write_once_json(CUTOVER_RECEIPT, {
                "schema_version": 1, "status": "PASS__RECOVERY0008_EXCLUSIVE_SCHEDULING_ONLY_CUTOVER",
                "authority": rel(AUTHORITY), "exclusive_controller_lock_held": True,
                "zero_r7_processes_and_partials": True, "transport_launched_by_receipt": False,
                "hashes_recomputed": False, "gzip_reopened": False,
            })
        bind(prior)
        r6.configure_validator()
        environment = r7.load_runtime_without_hash_revalidation(contract, args.cosima.resolve())
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, r6.coordinator_signal)
        r7.update_state(
            contract, status="RUNNING__RECOVERY0008__TARGET_MIN_6_CAP_10",
            stage="stage20_proton", completed=sum(receipt_path(job).is_file() for job in pending),
        )
        r6.append_event(
            "controller_started", minimum_target_workers=6, absolute_worker_cap=10,
            current_attempt_only_disk_admission=True, potential_future_retries_reserved_early=False,
        )
        return r6.run_campaign(original, original_manifest, pending, contract, environment, authority, registry)
    finally:
        for worker in list(r6._ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                try:
                    os.kill(worker.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                worker.process.join(timeout=30)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
