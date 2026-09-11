#!/usr/bin/env python3
"""Recovery0007: scheduling-only efficiency continuation of recovery0006.

Recovery0007 does not rebuild or alter the recovery0006 effective plan.  It
hash-binds that controller, authority, cutover, seed registry, plan, deadline,
and every recovery0006 PASS receipt present at the exclusive clean cutover.
New attempts and publications use a separate recovery0007 namespace.

The only operational change is scheduling.  Linux ``MemAvailable`` already
accounts for every active process's current resident memory, so active workers
reserve only measured *future* growth: the maximum of 128 MiB, positive recent
30-second one-sided RSS slope projected for 60 seconds, and peak-to-current
rebound.  A new candidate still reserves its planned runtime budget or a
padded recent exact-class observation, never less than 1 GiB.  Admission must
leave at least 1.5 GiB projected MemAvailable.  The efficiency target is at
least six workers when those gates permit, with the identical gate used from
six through the absolute cap of ten and at least 15 seconds between launches.

``--print-recovery-plan`` and ``--self-test`` are read-only.  They neither
publish recovery0007 files nor launch transport.
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
import subprocess
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0007_efficiency_scheduler"
R6_NS = campaign.RUN_ROOT / "recovery0006_six_to_one_replan"
RUN_NS = campaign.RUN_ROOT / "recovery0007_efficiency_scheduler"
AUTHORITY = RUN_NS / "authority.json"
CUTOVER_RECEIPT = RUN_NS / "cutover_receipt.json"
SEED_REGISTRY = RUN_NS / "seed_registry.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
FINAL_VALIDATION = RUN_NS / "final_validation.json"
FINAL_LEDGER = RUN_NS / "final_ledger.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"

R6_AUTHORITY = R6_NS / "authority.json"
R6_CUTOVER = R6_NS / "cutover_receipt.json"
R6_SEED_REGISTRY = R6_NS / "seed_registry.json"
R6_CONTROLLER = Path(r6.__file__).resolve()
R6_CUTOVER_INTENT = campaign.RUN_ROOT / "recovery0006_six_to_one_replan_cutover_intent.json"
R6_COORDINATOR_STOP = campaign.RUN_ROOT / "recovery0006_replan_coordinator_stop.json"
R6_DRAIN_COMPLETION = campaign.RUN_ROOT / "recovery0006_six_to_one_replan_drain_completion.json"
CUTOVER_INTENT = campaign.RUN_ROOT / "recovery0007_scheduler_cutover_intent.json"
CUTOVER_COMPLETION = campaign.RUN_ROOT / "recovery0007_scheduler_cutover_completion.json"

EXPECTED_R6_CONTROLLER_SHA256 = "43edf4c671b535ae6b4328afdf53cf75ac04aaf5361fa4a0a7521452be9cada0"
EXPECTED_R6_AUTHORITY_SHA256 = "b7bc0cd38aee223f4631ffda7f86894be923a44c5ba7cc1d6fd1c6c3fa9bd45d"
EXPECTED_R6_CUTOVER_SHA256 = "b710bd566165a482e086268c79928cb5ef0327230d88833ca7b4f07ec02caca3"
EXPECTED_R6_SEED_REGISTRY_SHA256 = "696894175f63f4eb21f4874d0ada57eed4581ad042131dad5427dbb4b7392687"
EXPECTED_R6_CUTOVER_INTENT_SHA256 = "e773c979e02d4f202f629a4eb590a80dbf014a8c3ede97d93100a3203bc25828"
EXPECTED_R6_COORDINATOR_STOP_SHA256 = "912474bbc1c400d8c38cc15bcbe48d140e116332933a0b984f065f74f4475b24"
EXPECTED_R6_DRAIN_COMPLETION_SHA256 = "f9f2f36ec3fd1f415517881825d79b7fc23cbe9a1aa25659946b81212512168d"
EXPECTED_PENDING_PLAN_SHA256 = "c802beb2aa110f462057e4de35e98f9966a7adbdd284bfba0fc1b19349409574"
EXPECTED_R6_SEED_PAYLOAD_SHA256 = "a9c0b1399205906e5070328cc7e79fe3e5ef4d1963963775db49214cafa03737"

MINIMUM_TARGET_WORKERS = 6
NORMAL_TARGET_WORKERS = 6
ABSOLUTE_MAX_WORKERS = 10
LAUNCH_STAGGER_S = 15.0
PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
HARD_WATCHDOG_FLOOR_BYTES = 512 * 1024**2
ACTIVE_FUTURE_MIN_BYTES = 128 * 1024**2
ACTIVE_HISTORY_WINDOW_S = 90.0
ACTIVE_SLOPE_WINDOW_S = 30.0
ACTIVE_GROWTH_HORIZON_S = 60.0
CANDIDATE_MIN_BYTES = 1024**3
CANDIDATE_OBSERVED_FACTOR = 1.15
CANDIDATE_OBSERVED_PAD_BYTES = 128 * 1024**2
RECENT_EXACT_CLASS_RECEIPTS = 8

_R6_INHERITED: dict[str, dict[str, Any]] = {}
_RECEIPT_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_ORIGINAL_ORDERED_STAGE_JOBS = r6.ordered_stage_jobs
_ORIGINAL_VALIDATE_REPLAN_RECEIPT = r6.validate_replan_receipt


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def load_frozen_inputs() -> tuple[
    dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    """Validate and return contract, original plan/manifest, r6 plan/registry."""
    required = (
        campaign.GLOBAL_CONTRACT, campaign.SEED_REGISTRY, R6_CONTROLLER,
        R6_AUTHORITY, R6_CUTOVER, R6_SEED_REGISTRY, R6_CUTOVER_INTENT,
        R6_COORDINATOR_STOP, R6_DRAIN_COMPLETION,
    )
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("recovery0007 declared input missing: " + ", ".join(missing))
    contract = load(campaign.GLOBAL_CONTRACT)
    original = campaign.build_plan()
    authority = load(R6_AUTHORITY)
    original_manifest = authority.get("inherited_pass_manifest")
    if not isinstance(original_manifest, list) or len(original_manifest) != r6.EXPECTED_INHERITED_RECEIPTS:
        raise RuntimeError("recovery0006 declared inherited PASS manifest count drift")
    if any(not (campaign.ROOT / str(row.get("path", ""))).is_file() for row in original_manifest):
        raise RuntimeError("a recovery0006 declared inherited PASS sidecar is missing")
    if contract.get("planned_jobs_sha256") != r6.EXPECTED_ORIGINAL_PLAN_SHA256:
        raise RuntimeError("global contract declared original-plan hash string drift")
    if len(original) != r6.EXPECTED_ORIGINAL_JOBS or contract.get("planned_jobs") != original:
        raise RuntimeError("global contract declared original plan structure drift")
    pending = authority.get("effective_pending_plan")
    if not isinstance(pending, list) or len(pending) != r6.EXPECTED_PENDING_JOBS:
        raise RuntimeError("recovery0006 effective plan count drift")
    if authority.get("effective_pending_plan_sha256") != EXPECTED_PENDING_PLAN_SHA256:
        raise RuntimeError("recovery0006 declared effective-plan hash string drift")
    if authority.get("controller") != {"path": rel(R6_CONTROLLER), "sha256": EXPECTED_R6_CONTROLLER_SHA256}:
        raise RuntimeError("recovery0006 controller binding drift")
    if authority.get("fresh_seed_registry_payload_sha256") != EXPECTED_R6_SEED_PAYLOAD_SHA256:
        raise RuntimeError("recovery0006 seed payload binding drift")
    cutover = load(R6_CUTOVER)
    if cutover.get("authority_sha256") != EXPECTED_R6_AUTHORITY_SHA256:
        raise RuntimeError("recovery0006 cutover declared authority hash string drift")
    if cutover.get("seed_registry_sha256") != EXPECTED_R6_SEED_REGISTRY_SHA256:
        raise RuntimeError("recovery0006 cutover declared seed-registry hash string drift")
    if len({str(job["job_id"]) for job in pending}) != len(pending):
        raise RuntimeError("recovery0006 pending plan has duplicate job ids")
    if sum(int(job["events"]) for job in pending) + r6.EXPECTED_INHERITED_EVENTS != r6.EXPECTED_TOTAL_EVENTS:
        raise RuntimeError("recovery0006 effective event target drift")
    registry = load(R6_SEED_REGISTRY)
    if int(registry.get("fresh_unique_seed_count", -1)) != r6.EXPECTED_FRESH_MATCHED_SEEDS:
        raise RuntimeError("recovery0006 seed registry declared fresh count drift")
    return contract, original, original_manifest, pending, registry


def _structural_inherited_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Cutover check only: trust r6's PASS sidecar without re-hashing artifacts."""
    if payload.get("status") != "PASS" or payload.get("job") != job:
        return False
    if payload.get("global_contract_sha256") != r6.EXPECTED_GLOBAL_SHA256:
        return False
    if payload.get("recovery_authority_sha256") != EXPECTED_R6_AUTHORITY_SHA256:
        return False
    directory = campaign.ROOT / str(payload.get("attempt_dir", ""))
    attempt = payload.get("selected_attempt")
    if not directory.is_dir() or not isinstance(attempt, int) or attempt not in (1, 2):
        return False
    framing = payload.get("sim", {}).get("strict_framing", {})
    expected = int(job["events"])
    return (
        framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == expected
        and int(framing.get("ID_second_count", -1)) == expected
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == expected
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == expected
    )


def r6_receipt_path(job: dict[str, Any]) -> Path:
    return R6_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def r7_receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def receipt_path(job: dict[str, Any]) -> Path:
    inherited = _R6_INHERITED.get(str(job["job_id"]))
    return campaign.ROOT / str(inherited["path"]) if inherited is not None else r7_receipt_path(job)


def validate_replan_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    inherited = _R6_INHERITED.get(str(job["job_id"]))
    if inherited is not None:
        path = campaign.ROOT / str(inherited["path"])
        return path.is_file() and _structural_inherited_receipt(job, payload)
    # New recovery0007 outputs retain recovery0006's strict dynamic validator.
    # This branch runs only after transport, never during cutover/startup.
    return AUTHORITY.is_file() and _ORIGINAL_VALIDATE_REPLAN_RECEIPT(job, payload)


def r6_pass_manifest(pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in pending:
        path = r6_receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if not _structural_inherited_receipt(job, payload):
            raise RuntimeError(f"recovery0006 PASS sidecar structural closure failed: {job['job_id']}")
        rows.append({
            "job_id": str(job["job_id"]), "path": rel(path),
            "events": int(job["events"]), "selected_attempt": int(payload["selected_attempt"]),
            "peak_process_group_rss_bytes": int(payload["peak_process_group_rss_bytes"]),
            "declared_recovery_authority_sha256": str(payload["recovery_authority_sha256"]),
        })
    return rows


def file_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": rel(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*")) if path.is_file()
    ] if root.is_dir() else []


def r6_terminal_manifest() -> list[dict[str, Any]]:
    names = ("final_validation.json", "final_ledger.json", "final_umbrella.json", "execution_state.json")
    return [
        {"path": rel(R6_NS / name), "status": load(R6_NS / name).get("status")}
        for name in names if (R6_NS / name).is_file()
    ]


def load_cutover_completion(*, required: bool) -> dict[str, Any] | None:
    if not CUTOVER_COMPLETION.is_file():
        if required:
            raise RuntimeError(f"missing clean cutover completion: {rel(CUTOVER_COMPLETION)}")
        return None
    payload = load(CUTOVER_COMPLETION)
    if not str(payload.get("status", "")).startswith("PASS"):
        raise RuntimeError("recovery0007 cutover completion is not PASS")
    return payload


def validate_cutover_completion(
    completion: dict[str, Any], inherited: list[dict[str, Any]], failed: list[dict[str, Any]],
) -> None:
    """Bind helper declarations structurally; never recompute their hashes."""
    required_true = (
        "zero_r6_related_non_z_processes", "zero_partial_attempts",
        "exclusive_campaign_flock_held_during_publication", "r6_final_umbrella_absent",
    )
    if any(completion.get(key) is not True for key in required_true):
        raise RuntimeError("cutover completion lacks a required clean structural gate")
    if completion.get("partial_attempts_after") != []:
        raise RuntimeError("cutover completion declares remaining partial attempts")
    if completion.get("physics_transport_changes") is not False or completion.get("transport_launched_by_helper") is not False:
        raise RuntimeError("cutover completion is not scheduling-only")
    if completion.get("artifacts_revalidated") is not False or completion.get("hashes_computed") is not False:
        raise RuntimeError("cutover helper unexpectedly repeated artifact/hash validation")
    declarations = completion.get("r6_declarations")
    if not isinstance(declarations, dict):
        raise RuntimeError("cutover completion lacks recovery0006 declarations")
    expected_strings = {
        "controller_declared_sha256": EXPECTED_R6_CONTROLLER_SHA256,
        "effective_pending_plan_declared_sha256": EXPECTED_PENDING_PLAN_SHA256,
        "fresh_seed_registry_payload_declared_sha256": EXPECTED_R6_SEED_PAYLOAD_SHA256,
    }
    for key, expected in expected_strings.items():
        if declarations.get(key) != expected:
            raise RuntimeError(f"cutover completion declared string drift: {key}")
    frozen = completion.get("receipt_declarations_frozen")
    if not isinstance(frozen, list) or completion.get("receipt_count_frozen") != len(frozen):
        raise RuntimeError("cutover completion receipt count/list closure failed")
    local_by_id = {str(row["job_id"]): row for row in inherited}
    frozen_by_id = {str(row.get("job_id")): row for row in frozen}
    if set(local_by_id) != set(frozen_by_id):
        raise RuntimeError("current recovery0006 PASS sidecar job-id set differs from clean cutover")
    for job_id, local in local_by_id.items():
        row = frozen_by_id[job_id]
        if (
            row.get("receipt_path") != local["path"]
            or row.get("declared_status") != "PASS"
            or int(row.get("declared_events", -1)) != int(local["events"])
            or int(row.get("declared_selected_attempt", -1)) != int(local["selected_attempt"])
            or row.get("declared_recovery_authority_sha256") != EXPECTED_R6_AUTHORITY_SHA256
        ):
            raise RuntimeError(f"cutover completion PASS declaration drift: {job_id}")
    completion_failed = {
        str(row.get("validation_path")) for row in completion.get("failed_attempt_declarations_frozen", [])
    }
    local_failed = {str(row["path"]) for row in failed if str(row["path"]).endswith("/validation.json")}
    if completion_failed != local_failed:
        raise RuntimeError("current recovery0006 failed-attempt validation set differs from clean cutover")


def cutover_process_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    r6_name = R6_CONTROLLER.name
    r6_ns_text = str(R6_NS.resolve())
    for proc_dir in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc_dir.name)
            if pid == os.getpid():
                continue
            cmdline = proc_dir.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            comm = proc_dir.joinpath("comm").read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if (comm.startswith("python") and r6_name in cmdline) or (comm == "cosima" and r6_ns_text in cmdline):
            rows.append({"pid": pid, "comm": comm})
    partials = sorted(
        rel(path) for namespace in (R6_NS, RUN_NS)
        for path in namespace.glob("attempts/**/.attempt*.partial") if path.is_dir()
    )
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "matching_recovery0006_processes": sorted(rows, key=lambda row: int(row["pid"])),
        "unresolved_partial_attempts": partials,
    }


def assert_clean_cutover(snapshot: dict[str, Any]) -> None:
    if snapshot["matching_recovery0006_processes"]:
        raise RuntimeError("recovery0007 cutover found recovery0006 controller/worker/Cosima")
    if snapshot["unresolved_partial_attempts"]:
        raise RuntimeError("recovery0007 cutover found unresolved recovery0006/0007 partial attempts")


def proposed_authority(
    contract: dict[str, Any], pending: list[dict[str, Any]], inherited: list[dict[str, Any]],
    failed: list[dict[str, Any]], terminal: list[dict[str, Any]], snapshot: dict[str, Any],
    completion: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__RECOVERY0007_SCHEDULING_ONLY_EFFICIENCY_CONTINUATION__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "controller": {
            "path": rel(Path(__file__).resolve()),
            "exists_at_startup": Path(__file__).resolve().is_file(),
            "hash_computed_or_required": False,
        },
        "inputs": {
            "recovery0006_controller": rel(R6_CONTROLLER),
            "recovery0006_controller_sha256": EXPECTED_R6_CONTROLLER_SHA256,
            "recovery0006_authority": rel(R6_AUTHORITY),
            "recovery0006_authority_sha256": EXPECTED_R6_AUTHORITY_SHA256,
            "recovery0006_cutover_sha256": EXPECTED_R6_CUTOVER_SHA256,
            "recovery0006_seed_registry_sha256": EXPECTED_R6_SEED_REGISTRY_SHA256,
            "recovery0006_cutover_intent_sha256": EXPECTED_R6_CUTOVER_INTENT_SHA256,
            "recovery0006_coordinator_stop_sha256": EXPECTED_R6_COORDINATOR_STOP_SHA256,
            "recovery0006_drain_completion_sha256": EXPECTED_R6_DRAIN_COMPLETION_SHA256,
            "global_contract_sha256": r6.EXPECTED_GLOBAL_SHA256,
        },
        "effective_pending_plan": pending,
        "effective_pending_plan_sha256": EXPECTED_PENDING_PLAN_SHA256,
        "seed_policy": {
            "status": "EXACT_RECOVERY0006_REGISTRY_INHERITED__NO_ALLOCATION_OR_REUSE",
            "payload_sha256": EXPECTED_R6_SEED_PAYLOAD_SHA256,
            "file_sha256": EXPECTED_R6_SEED_REGISTRY_SHA256,
        },
        "inherited_recovery0006_pass_receipts": inherited,
        "inherited_recovery0006_pass_count": len(inherited),
        "inherited_recovery0006_pass_events": sum(int(row["events"]) for row in inherited),
        "preserved_recovery0006_failed_files": failed,
        "recovery0006_terminal_publications_at_cutover": terminal,
        "cutover_intent": rel(CUTOVER_INTENT),
        "cutover_completion": rel(CUTOVER_COMPLETION),
        "cutover_completion_declarations": completion,
        "cutover_process_snapshot": snapshot,
        "frozen_clock": {
            "t0": contract["wall_clock"]["t0"], "deadline": contract["wall_clock"]["deadline"],
            "stages": contract["wall_clock"]["stages"],
        },
        "scheduler": {
            "policy": "efficiency-first full-stage first-fit scan; bypass non-fitting heavy candidates and admit lighter eligible jobs",
            "minimum_target_workers": MINIMUM_TARGET_WORKERS,
            "normal_target_workers": NORMAL_TARGET_WORKERS,
            "absolute_worker_cap": ABSOLUTE_MAX_WORKERS,
            "launch_stagger_s": LAUNCH_STAGGER_S,
            "workers_6_through_10_use_identical_gate": True,
            "target_is_not_permission_to_cross_resource_gate": True,
            "memavailable_semantics": "Linux MemAvailable already includes every active worker's current RSS; current RSS is never subtracted again",
            "active_future_growth_reserve": "per active=max(128MiB, positive OLS slope over recent <=30s * 60s, recent peak RSS-current RSS rebound); no planned/class upper-current term",
            "new_candidate_reserve": "max(1GiB, planned runtime RSS budget, 1.15*recent exact-class max RSS+128MiB)",
            "admission": "MemAvailable-sum(active future-growth reserves)-candidate reserve >=1.5GiB",
            "pending_scan": "entire eligible stage queue is scanned on every launch opportunity; a heavy non-fit never blocks a later light fit",
            "soft_preemption": False,
            "hard_watchdog_floor_bytes": HARD_WATCHDOG_FLOOR_BYTES,
            "maximum_exact_attempts": campaign.MAX_ATTEMPTS,
            "disk_deadline_and_stage20_ladder_gates": "unchanged from recovery0006",
        },
        "publication_namespace": rel(RUN_NS),
        "unchanged": {
            "jobs_seeds_events_sources_spectra_geometry_physics_cuts_detector_veto": True,
            "job_output_caps": True, "deadline": True, "validation": True,
            "event_target": r6.EXPECTED_TOTAL_EVENTS, "mono511_added": False,
        },
        "startup_validation_scope": {
            "sha256_recomputed": False, "artifacts_rehashed": False, "gzip_reopened": False,
            "checks": ["controller lock", "process quiescence", "partial absence", "job-id/receipt existence", "attempt count", "static scheduler parameters"],
            "existing_hash_strings_are_declarations_only": True,
        },
    }


def load_or_publish_authority(proposed: dict[str, Any], *, publish: bool) -> dict[str, Any]:
    if AUTHORITY.is_file():
        payload = load(AUTHORITY)
    elif publish:
        campaign.atomic_write_once_json(AUTHORITY, proposed)
        payload = load(AUTHORITY)
    else:
        return proposed
    for key in (
        "controller", "inputs", "effective_pending_plan_sha256", "seed_policy",
        "inherited_recovery0006_pass_receipts", "preserved_recovery0006_failed_files",
        "recovery0006_terminal_publications_at_cutover", "cutover_completion_declarations",
        "frozen_clock", "scheduler", "unchanged", "startup_validation_scope",
    ):
        if payload.get(key) != proposed.get(key):
            raise RuntimeError(f"recovery0007 authority drift: {key}")
    return payload


def publish_registry_and_cutover(authority: dict[str, Any], registry: dict[str, Any]) -> None:
    campaign.atomic_write_once_json(SEED_REGISTRY, registry)
    campaign.atomic_write_once_json(CUTOVER_RECEIPT, {
        "schema_version": 1,
        "status": "PASS__RECOVERY0007_EXCLUSIVE_CLEAN_SCHEDULING_ONLY_CUTOVER",
        "recovery_id": RECOVERY_ID,
        "authority": rel(AUTHORITY),
        "seed_registry": rel(SEED_REGISTRY),
        "recovery0006_authority_sha256_declared": EXPECTED_R6_AUTHORITY_SHA256,
        "recovery0006_seed_registry_sha256_declared": EXPECTED_R6_SEED_REGISTRY_SHA256,
        "recovery0006_pass_count": authority["inherited_recovery0006_pass_count"],
        "recovery0006_pass_events": authority["inherited_recovery0006_pass_events"],
        "exclusive_controller_lock_held": True,
        "zero_recovery0006_processes": True,
        "zero_recovery0006_or_recovery0007_partial_attempts": True,
        "transport_launched_by_receipt": False,
        "sha256_recomputed_during_startup_or_cutover": False,
    })


def active_future_growth(
    current: int, samples: Iterable[tuple[float, int]], upper: int = 0, age: float = 0.0,
) -> dict[str, Any]:
    """Reserve only future growth not already included by MemAvailable."""
    rows = sorted((float(at), max(0, int(rss))) for at, rss in samples)
    if rows:
        newest = rows[-1][0]
        rows = [row for row in rows if newest - row[0] <= ACTIVE_HISTORY_WINDOW_S]
    slope_rows = rows
    if rows:
        newest = rows[-1][0]
        slope_rows = [row for row in rows if newest - row[0] <= ACTIVE_SLOPE_WINDOW_S]
    slope = 0.0
    if len(slope_rows) >= 2:
        mean_t = sum(row[0] for row in slope_rows) / len(slope_rows)
        mean_rss = sum(row[1] for row in slope_rows) / len(slope_rows)
        denominator = sum((row[0] - mean_t) ** 2 for row in slope_rows)
        if denominator:
            slope = max(0.0, sum((at - mean_t) * (rss - mean_rss) for at, rss in slope_rows) / denominator)
    slope_reserve = math.ceil(slope * ACTIVE_GROWTH_HORIZON_S)
    peak_rebound = max(0, max((rss for _at, rss in rows), default=current) - int(current))
    reserve = max(ACTIVE_FUTURE_MIN_BYTES, slope_reserve, peak_rebound)
    return {
        "reserve_bytes": reserve, "current_rss_bytes": int(current),
        "positive_recent_ols_slope_bytes_per_s": slope,
        "slope_horizon_s": ACTIVE_GROWTH_HORIZON_S,
        "slope_reserve_bytes": slope_reserve, "peak_current_rebound_bytes": peak_rebound,
        "minimum_future_reserve_bytes": ACTIVE_FUTURE_MIN_BYTES,
        "worker_age_s": age, "class_or_planned_upper_bytes_audit_only": int(upper),
        "class_or_planned_upper_minus_current_subtracted": False,
    }


def rss_evidence(original: list[dict[str, Any]], pending: list[dict[str, Any]]) -> dict[str, Any]:
    old_classes: dict[str, list[int]] = defaultdict(list)
    # Use only the peak-RSS declarations already present in PASS sidecars.
    # The r6 helper would re-hash every inherited multi-gigabyte artifact.
    for job in original:
        path = r6.original_receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if payload.get("status") != "PASS" or payload.get("job") != job:
            continue
        key = f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}"
        old_classes[key].append(int(payload["peak_process_group_rss_bytes"]))
    current: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for job in pending:
        path = receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if not validate_replan_receipt(job, payload):
            raise RuntimeError(f"recovery0007 RSS evidence receipt closure failed: {job['job_id']}")
        current[r6.class_key(job)].append((path.stat().st_mtime_ns, int(payload["peak_process_group_rss_bytes"])))
    exact: dict[str, dict[str, int]] = {}
    for key, values in sorted(current.items()):
        recent = sorted(values, reverse=True)[:RECENT_EXACT_CLASS_RECEIPTS]
        exact[key] = {"n": len(values), "recent_n": len(recent), "max_bytes": max(value for _at, value in recent)}
    return {
        "old_exact_classes": {key: {"n": len(values), "max_bytes": max(values)} for key, values in sorted(old_classes.items())},
        "recovery0006_exact_classes": exact,
        "semantics": "recovery0006_exact_classes max is the most recent up-to-eight exact-class PASS receipts across inherited r6 and new r7",
    }


def candidate_upper(job: dict[str, Any], evidence: dict[str, Any], live_peer: int = 0) -> int:
    del live_peer
    planned = int(job.get("_runtime_peak_rss_budget_bytes", job.get("planned_peak_rss_budget_bytes", 0)))
    observed = int(evidence.get("recovery0006_exact_classes", {}).get(r6.class_key(job), {}).get("max_bytes", 0))
    observed_upper = math.ceil(observed * CANDIDATE_OBSERVED_FACTOR) + CANDIDATE_OBSERVED_PAD_BYTES if observed else 0
    return max(CANDIDATE_MIN_BYTES, planned, observed_upper)


def memory_projection(
    active: list[r6.Worker], candidate: dict[str, Any], evidence: dict[str, Any], available: int,
    live: dict[int, int], histories: dict[int, Iterable[tuple[float, int]]], now: float,
) -> dict[str, Any]:
    active_reserve = 0
    rows: list[dict[str, Any]] = []
    for worker in active:
        current = int(live.get(worker.process.pid, 0))
        forecast = active_future_growth(
            current, histories.get(worker.process.pid, ()),
            candidate_upper(worker.job, evidence), max(0.0, now - worker.launched_monotonic),
        )
        active_reserve += int(forecast["reserve_bytes"])
        rows.append({"job_id": worker.job["job_id"], "trajectory": forecast})
    new_upper = candidate_upper(candidate, evidence)
    projected = int(available) - active_reserve - new_upper
    return {
        "status": "PASS" if projected >= PROJECTED_FLOOR_BYTES else "PAUSE",
        "mem_available_bytes": int(available),
        "active_current_rss_already_in_memavailable_bytes": sum(int(live.get(worker.process.pid, 0)) for worker in active),
        "active_future_growth_reserve_bytes": active_reserve,
        "active_unrealised_growth_reserve_bytes": active_reserve,
        "candidate_class_upper_bytes": new_upper,
        "projected_mem_available_bytes": projected,
        "soft_floor_bytes": PROJECTED_FLOOR_BYTES, "active": rows,
    }


def global_active_projection(
    active: list[r6.Worker], evidence: dict[str, Any], available: int,
    live: dict[int, int], histories: dict[int, Iterable[tuple[float, int]]], now: float,
) -> dict[str, Any]:
    reserve = sum(
        int(active_future_growth(
            int(live.get(worker.process.pid, 0)), histories.get(worker.process.pid, ()),
            candidate_upper(worker.job, evidence), max(0.0, now - worker.launched_monotonic),
        )["reserve_bytes"])
        for worker in active
    )
    return {
        "projected_mem_available_bytes": int(available) - reserve,
        "mem_available_bytes": int(available),
        "active_future_growth_reserve_bytes": reserve,
        "active_unrealised_growth_reserve_bytes": reserve,
    }


def health_allows(health: r6.Health, projection: dict[str, Any], swap: dict[str, Any], now: float) -> tuple[bool, str]:
    del now
    projected = int(projection["projected_mem_available_bytes"])
    if swap.get("growing"):
        health.paused = True
        return False, "swap_growth"
    if projected < PROJECTED_FLOOR_BYTES:
        health.paused = True
        return False, "projected_below_1.5GiB"
    health.paused = False
    health.resume_since = None
    return True, "admit_same_gate_1_through_10"


def ordered_stage_jobs(stage: str, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put light work first; r6 run_stage still scans the complete returned queue."""
    rows = _ORIGINAL_ORDERED_STAGE_JOBS(stage, pending)
    if stage == "stage20_proton":
        # Preserve the mandatory 512 -> 1024 -> calibrated 2048 ladder.
        event_order = {512: 0, 1024: 1, 2048: 2, 1105: 3}
        return sorted(rows, key=lambda job: (
            event_order.get(int(job["events"]), 9), int(job.get("planned_peak_rss_budget_bytes", CANDIDATE_MIN_BYTES)),
            rows.index(job),
        ))
    return sorted(rows, key=lambda job: (int(job.get("planned_peak_rss_budget_bytes", CANDIDATE_MIN_BYTES)), rows.index(job)))


def run_stage(
    stage: str, pending_plan: list[dict[str, Any]], original: list[dict[str, Any]],
    contract: dict[str, Any], environment: dict[str, str], authority: dict[str, Any], registry: dict[str, Any],
) -> str | None:
    """Full-queue, lowest-charge scheduler using the same live gate for 1..10."""
    timing = next(row for row in contract["wall_clock"]["stages"] if row["id"] == stage)
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    stop_launch = t0 + timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + timedelta(seconds=int(timing["hard_end_s"]))
    pending = [job for job in ordered_stage_jobs(stage, pending_plan) if not receipt_path(job).is_file()]
    active: list[r6.Worker] = []
    failures: list[str] = []
    context = mp.get_context("fork")
    health = r6.Health()
    evidence = rss_evidence(original, pending_plan)
    swap_samples: deque[tuple[float, int]] = deque()
    last_launch = -math.inf
    last_evidence = last_state = last_pause = 0.0
    stop_reason: str | None = None
    r6.append_event(
        "stage_start", stage=stage, pending_jobs=len(pending),
        stop_launch=stop_launch.isoformat(), hard_end=hard_end.isoformat(),
        full_queue_lowest_candidate_charge=True,
    )
    while pending or active:
        now_mono = time.monotonic()
        active = r6.reap(active, failures)
        if failures and stop_reason is None:
            stop_reason = "worker failure: " + failures[0]
        if now_mono - last_evidence >= r6.EVIDENCE_REFRESH_S:
            evidence = rss_evidence(original, pending_plan)
            last_evidence = now_mono
        live, histories = r6.sample_rss(active, health, now_mono)
        swap_samples.append((now_mono, r6.recovery5.read_pswpout_pages()))
        while swap_samples and now_mono - swap_samples[0][0] > r6.recovery5.SWAP_WINDOW_S + 5:
            swap_samples.popleft()
        swap = r6.recovery5.swap_growth(swap_samples)
        now = datetime.now(timezone.utc)
        available = campaign.mem_available_bytes()
        global_projection = global_active_projection(active, evidence, available, live, histories, now_mono)
        global_healthy, global_health_decision = health_allows(health, global_projection, swap, now_mono)
        launch_allowed = (
            not r6._COORDINATOR_STOP and stop_reason is None and global_healthy
            and pending and len(active) < ABSOLUTE_MAX_WORKERS
            and now < stop_launch and now_mono - last_launch >= LAUNCH_STAGGER_S
        )
        if launch_allowed:
            eligible: list[tuple[int, int, dict[str, Any], float]] = []
            blocked_counts: dict[str, int] = defaultdict(int)
            # Inspect the complete stage queue.  This phase is intentionally
            # cheap: it does not rescan campaign disk for every candidate.
            for index, candidate in enumerate(pending):
                collision = r6.calibration_collision(candidate, active, evidence)
                ladder_block = r6.stage20_ladder_block(candidate, pending_plan)
                canary_block = False
                if candidate.get("requires_stage20_canary_calibration"):
                    canary_block = ladder_block is not None
                    calibration = None if canary_block else r6.load_or_publish_stage20_calibration(
                        str(candidate["mode"]), pending_plan, authority, registry, publish=True,
                    )
                    canary_block = canary_block or calibration is None
                if collision:
                    blocked_counts["exact_class_collision"] += 1
                    continue
                if ladder_block or canary_block:
                    blocked_counts["stage20_ladder_or_calibration"] += 1
                    continue
                runtime_budget = r6.runtime_job_budget(candidate, pending_plan, authority, registry)
                runtime_wall = r6.runtime_job_wall_budget(candidate, pending_plan, authority, registry)
                if now + timedelta(seconds=runtime_wall + r6.VALIDATION_PUBLICATION_MARGIN_S) > hard_end:
                    blocked_counts["deadline"] += 1
                    continue
                eligible.append((runtime_budget, index, candidate, runtime_wall))
            selected: tuple[int, dict[str, Any], dict[str, Any], int, float] | None = None
            observations: list[dict[str, Any]] = []
            for runtime_budget, index, candidate, runtime_wall in sorted(eligible, key=lambda row: (row[0], row[1])):
                candidate_runtime = {**candidate, "planned_peak_rss_budget_bytes": runtime_budget}
                projection = memory_projection(active, candidate_runtime, evidence, campaign.mem_available_bytes(), live, histories, now_mono)
                if int(projection["projected_mem_available_bytes"]) < PROJECTED_FLOOR_BYTES:
                    blocked_counts["memory"] += 1
                    if len(observations) < 24:
                        observations.append({"job_id": candidate["job_id"], "runtime_budget_bytes": runtime_budget, "projection": projection, "decision": "memory_non_fit"})
                    continue
                disk = r6.disk_projection(contract, stage, active, candidate)
                if disk["status"] != "PASS":
                    blocked_counts["disk"] += 1
                    if len(observations) < 24:
                        observations.append({"job_id": candidate["job_id"], "runtime_budget_bytes": runtime_budget, "projection": projection, "disk": disk, "decision": "disk_non_fit"})
                    continue
                selected = index, projection, disk, runtime_budget, runtime_wall
                break
            if selected is not None:
                index, projection, disk, runtime_budget, runtime_wall = selected
                candidate = pending.pop(index)
                worker = launch_worker(
                    context, candidate, contract, environment, hard_end,
                    runtime_peak_rss_budget_bytes=runtime_budget, runtime_wall_budget_s=runtime_wall,
                )
                active.append(worker)
                last_launch = now_mono
                r6.append_event(
                    "worker_launched", stage=stage, job_id=candidate["job_id"], worker_pid=worker.process.pid,
                    active_workers=len(active), minimum_target_workers=MINIMUM_TARGET_WORKERS,
                    absolute_worker_cap=ABSOLUTE_MAX_WORKERS, projection=projection, disk=disk,
                    runtime_wall_budget_s=runtime_wall, scanned_pending_jobs=len(pending) + 1,
                    eligible_jobs=len(eligible), selected_lowest_candidate_charge=True,
                )
            elif now_mono - last_pause >= 30:
                r6.append_event(
                    "launch_PAUSE", stage=stage, active_workers=len(active),
                    minimum_target_workers=MINIMUM_TARGET_WORKERS, absolute_worker_cap=ABSOLUTE_MAX_WORKERS,
                    mem_available_bytes=campaign.mem_available_bytes(), swap=swap,
                    global_projection=global_projection, global_health_decision=global_health_decision,
                    scanned_pending_jobs=len(pending), eligible_jobs=len(eligible),
                    blocked_counts=dict(sorted(blocked_counts.items())), observations=observations,
                )
                last_pause = now_mono
        if stop_reason is not None and not active:
            break
        if r6._COORDINATOR_STOP and not active:
            stop_reason = stop_reason or "coordinator stop requested"
            break
        if now >= stop_launch and not active:
            stop_reason = stop_reason or "original stage stop-launch boundary reached"
            break
        if datetime.now(timezone.utc) >= hard_end and active:
            for worker in active:
                if worker.process.is_alive():
                    os.kill(worker.process.pid, signal.SIGTERM)
        if now_mono - last_state >= 30:
            completed = sum(receipt_path(job).is_file() for job in pending_plan)
            update_state(
                contract, status=f"RUNNING__RECOVERY0007__ACTIVE_{len(active)}",
                stage=stage, completed=completed, error=stop_reason,
            )
            r6.append_event(
                "scheduler_checkpoint", stage=stage, active_workers=len(active), pending_jobs=len(pending),
                minimum_target_workers=MINIMUM_TARGET_WORKERS, absolute_worker_cap=ABSOLUTE_MAX_WORKERS,
                mem_available_bytes=campaign.mem_available_bytes(), active_rss_bytes=sum(live.values()), swap=swap,
            )
            last_state = now_mono
        time.sleep(r6.POLL_S)
    while active:
        active = r6.reap(active, failures)
        if active:
            time.sleep(r6.POLL_S)
    if failures and stop_reason is None:
        stop_reason = "worker failure: " + failures[0]
    r6.append_event(
        "stage_end", stage=stage, stop_reason=stop_reason,
        completed=sum(receipt_path(job).is_file() for job in pending_plan if job["stage"] == stage),
    )
    return stop_reason


def prior_exact_attempts(job: dict[str, Any]) -> set[int]:
    used: set[int] = set()
    roots = [
        campaign.RUN_ROOT / "failed_attempts" / str(job["job_id"]),
        campaign.RUN_ROOT / "failed_attempts" / "recovery0006_cutover_orphan" / str(job["job_id"]),
        R6_NS / "failed_attempts" / str(job["job_id"]),
        RUN_NS / "failed_attempts" / str(job["job_id"]),
    ]
    identity = ("job_id", "seed", "events", "geometry", "mode", "family", "source_tag")
    for root in roots:
        for path in root.glob("attempt*/validation.json"):
            match = re.fullmatch(r"attempt(\d+)", path.parent.name)
            if not match:
                continue
            old = load(path).get("job", {})
            if all(old.get(key) == job.get(key) for key in identity):
                used.add(int(match.group(1)))
    return used


def launch_worker(
    context: Any, job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_end: datetime,
    *, runtime_peak_rss_budget_bytes: int | None = None, runtime_wall_budget_s: float | None = None,
) -> r6.Worker:
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=r6.worker_entry,
        args=(job, contract, environment, hard_end.isoformat(), runtime_wall_budget_s, child),
        name=f"m05-r7-{job['job_id']}",
    )
    process.start()
    child.close()
    now = time.monotonic()
    scheduler_job = dict(job)
    if runtime_peak_rss_budget_bytes is not None:
        scheduler_job["_runtime_peak_rss_budget_bytes"] = int(runtime_peak_rss_budget_bytes)
    if runtime_wall_budget_s is not None:
        scheduler_job["_runtime_wall_budget_s"] = float(runtime_wall_budget_s)
    worker = r6.Worker(scheduler_job, process, parent, datetime.now(timezone.utc).isoformat(), now)
    r6._ACTIVE_WORKERS[process.pid] = worker
    return worker


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed: int, error: str | None = None) -> None:
    status = status.replace("RECOVERY0006", "RECOVERY0007")
    campaign.atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status, "stage": stage,
        "completed_effective_pending_jobs": completed, "target_effective_pending_jobs": r6.EXPECTED_PENDING_JOBS,
        "inherited_recovery0006_pass_jobs": len(_R6_INHERITED),
        "final_selected_receipt_target": r6.EXPECTED_FINAL_RECEIPTS,
        "effective_event_target": r6.EXPECTED_TOTAL_EVENTS,
        "minimum_target_workers": MINIMUM_TARGET_WORKERS, "absolute_worker_cap": ABSOLUTE_MAX_WORKERS,
        "deadline": contract["wall_clock"]["deadline"], "updated_at": datetime.now(timezone.utc).isoformat(),
        "mem_available_bytes": campaign.mem_available_bytes(), "campaign_bytes": campaign.campaign_bytes(),
        "free_disk_bytes": shutil.disk_usage(campaign.RUN_ROOT).free, "last_error": error,
    })


def load_runtime_without_hash_revalidation(contract: dict[str, Any], cosima: Path) -> dict[str, str]:
    """Load the already-authorized runtime environment without fingerprinting it again."""
    resolved = cosima.resolve()
    declared = Path(str(contract["static_gate"]["transport"]["cosima"])).resolve()
    if resolved != declared or not resolved.is_file():
        raise RuntimeError("requested Cosima path differs from the already-authorized runtime path")
    setup = resolved.parent / "source-megalib.sh"
    if not setup.is_file():
        raise RuntimeError(f"missing already-authorized MEGAlib setup: {setup}")
    task_home = str(Path.home())
    command = [
        "/usr/bin/env", "-i", f"HOME={task_home}", "USER=ubuntu", "LOGNAME=ubuntu",
        "PATH=/usr/bin:/bin", "SHELL=/bin/bash", "/bin/bash", "--noprofile", "--norc",
        "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(setup),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"authorized MEGAlib environment load failed: {result.stderr.decode(errors='replace')}")
    environment: dict[str, str] = {}
    for item in result.stdout.split(b"\0"):
        if item and b"=" in item:
            key, raw = item.split(b"=", 1)
            environment[key.decode(errors="replace")] = raw.decode(errors="replace")
    for key in ("PATH", "LD_LIBRARY_PATH"):
        environment[key] = campaign._dedupe_path(environment.get(key, ""))
    return environment


def bind_recovery0007(inherited: list[dict[str, Any]]) -> None:
    global _R6_INHERITED
    _R6_INHERITED = {str(row["job_id"]): row for row in inherited}
    _RECEIPT_CACHE.clear()
    r6.RECOVERY_ID = RECOVERY_ID
    r6.RUN_NS = RUN_NS
    r6.AUTHORITY = AUTHORITY
    r6.CUTOVER_RECEIPT = CUTOVER_RECEIPT
    r6.REPLAN_SEED_REGISTRY = SEED_REGISTRY
    r6.SCHEDULER_EVENTS = SCHEDULER_EVENTS
    r6.EXECUTION_STATE = EXECUTION_STATE
    r6.FINAL_VALIDATION = FINAL_VALIDATION
    r6.FINAL_LEDGER = FINAL_LEDGER
    r6.FINAL_UMBRELLA = FINAL_UMBRELLA
    r6.MAX_WORKERS = ABSOLUTE_MAX_WORKERS
    r6.NORMAL_TARGET_WORKERS = NORMAL_TARGET_WORKERS
    r6.LAUNCH_STAGGER_S = LAUNCH_STAGGER_S
    r6.SOFT_FLOOR_BYTES = PROJECTED_FLOOR_BYTES
    r6.receipt_path = receipt_path
    r6.validate_replan_receipt = validate_replan_receipt
    r6.rss_evidence = rss_evidence
    r6.class_upper = candidate_upper
    r6.active_growth = active_future_growth
    r6.memory_projection = memory_projection
    r6.global_active_projection = global_active_projection
    r6.health_allows = health_allows
    r6.ordered_stage_jobs = ordered_stage_jobs
    r6.run_stage = run_stage
    r6.prior_exact_attempts = prior_exact_attempts
    r6.launch_worker = launch_worker
    r6.update_state = update_state


def self_test() -> dict[str, Any]:
    gib = 1024**3
    stable = active_future_growth(2 * gib, [(0.0, 2 * gib), (30.0, 2 * gib)], 6 * gib, 120.0)
    assert stable["reserve_bytes"] == ACTIVE_FUTURE_MIN_BYTES
    assert stable["class_or_planned_upper_minus_current_subtracted"] is False
    ramp = active_future_growth(gib, [(0.0, gib), (30.0, 2 * gib)], 6 * gib, 30.0)
    assert ramp["reserve_bytes"] == 2 * gib
    rebound = active_future_growth(gib, [(0.0, 3 * gib), (30.0, gib)], 6 * gib, 60.0)
    assert rebound["reserve_bytes"] == 2 * gib
    evidence = {"recovery0006_exact_classes": {}}
    light = {"stage": "stage10_seven_family", "mode": "instant", "geometry": "Mass_model_511", "family": "muplus", "replan_kind": "fresh_balanced_bundle", "planned_peak_rss_budget_bytes": gib, "shard_ordinal": 1}
    heavy = {**light, "family": "gamma", "planned_peak_rss_budget_bytes": 6 * gib}
    assert candidate_upper(light, evidence) == gib
    assert candidate_upper(heavy, evidence) == 6 * gib
    projection_light = memory_projection([], light, evidence, 3 * gib, {}, {}, 0.0)
    projection_heavy = memory_projection([], heavy, evidence, 3 * gib, {}, {}, 0.0)
    assert projection_light["status"] == "PASS" and projection_heavy["status"] == "PAUSE"
    fake_jobs = [{**heavy, "job_id": "heavy"}, {**light, "job_id": "light"}]
    assert ordered_stage_jobs("stage10_seven_family", fake_jobs)[0]["job_id"] == "light"
    health = r6.Health()
    assert health_allows(health, {"projected_mem_available_bytes": PROJECTED_FLOOR_BYTES}, {"growing": False}, 0)[0]
    assert not health_allows(health, {"projected_mem_available_bytes": PROJECTED_FLOOR_BYTES - 1}, {"growing": False}, 0)[0]
    return {
        "status": "PASS__RECOVERY0007_SCHEDULING_ONLY_STATIC_SELF_TEST",
        "tests": 13, "transport_launched": False, "authority_published": AUTHORITY.exists(),
        "minimum_target_workers": MINIMUM_TARGET_WORKERS, "absolute_worker_cap": ABSOLUTE_MAX_WORKERS,
        "sha256_recomputed": False, "artifacts_rehashed": False, "gzip_reopened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    contract, original, original_manifest, pending, registry = load_frozen_inputs()
    if args.self_test and not args.print_recovery_plan:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    inherited = r6_pass_manifest(pending)
    failed = file_manifest(R6_NS / "failed_attempts")
    terminal = r6_terminal_manifest()
    snapshot = cutover_process_snapshot()
    completion = load_cutover_completion(required=False)
    proposed = proposed_authority(contract, pending, inherited, failed, terminal, snapshot, completion)
    if args.print_recovery_plan:
        print(json.dumps({
            "status": "PASS__READ_ONLY_RECOVERY0007_SCHEDULING_ONLY_PLAN",
            "controller_path": proposed["controller"]["path"],
            "recovery0006_authority_sha256": EXPECTED_R6_AUTHORITY_SHA256,
            "effective_pending_plan_sha256": EXPECTED_PENDING_PLAN_SHA256,
            "inherited_recovery0006_pass_count_snapshot": len(inherited),
            "inherited_recovery0006_pass_events_snapshot": sum(int(row["events"]) for row in inherited),
            "scheduler": proposed["scheduler"], "cutover_snapshot": snapshot,
            "authority_published": AUTHORITY.exists(), "transport_launched": False,
            "self_test": self_test() if args.self_test else None,
        }, indent=2, sort_keys=True))
        return 0
    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        snapshot = cutover_process_snapshot()
        assert_clean_cutover(snapshot)
        completion = load_cutover_completion(required=True)
        inherited = r6_pass_manifest(pending)
        failed = file_manifest(R6_NS / "failed_attempts")
        terminal = r6_terminal_manifest()
        validate_cutover_completion(completion, inherited, failed)
        proposed = proposed_authority(contract, pending, inherited, failed, terminal, snapshot, completion)
        authority = load_or_publish_authority(proposed, publish=True)
        # A restart must see precisely the same frozen recovery0006 receipt set.
        if inherited != authority["inherited_recovery0006_pass_receipts"]:
            raise RuntimeError("recovery0006 PASS receipt set differs from recovery0007 cutover authority")
        publish_registry_and_cutover(authority, registry)
        bind_recovery0007(inherited)
        r6.configure_validator()
        environment = load_runtime_without_hash_revalidation(contract, args.cosima.resolve())
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, r6.coordinator_signal)
        update_state(
            contract, status="RUNNING__RECOVERY0007__TARGET_MIN_6_CAP_10", stage="stage10_seven_family",
            completed=sum(receipt_path(job).is_file() for job in pending),
        )
        r6.append_event(
            "controller_started", authority=rel(AUTHORITY), cutover_receipt=rel(CUTOVER_RECEIPT),
            effective_pending_plan_sha256=EXPECTED_PENDING_PLAN_SHA256,
            inherited_recovery0006_pass_count=len(inherited), minimum_target_workers=MINIMUM_TARGET_WORKERS,
            absolute_worker_cap=ABSOLUTE_MAX_WORKERS, sha256_recomputed_during_startup=False,
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
            if worker.process.is_alive():
                try:
                    os.kill(worker.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                worker.process.join(timeout=10)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
