#!/usr/bin/env python3
"""Run the append-only corrected-keV M05 paper-closure top-up batch0007.

This is a thin namespace/plan adapter around the validated batch0006
transport, validator, memory scheduler, and current-attempt disk admission.
It never reopens or rehashes an old SIM artifact.  Each new shard is validated
once by the inherited strict validator before its receipt is published.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import shutil
import signal
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[4]
BATCH0006_CODE = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_16h_90gb_campaign_batch0006_20260812/code"
)
sys.path.insert(0, str(BATCH0006_CODE))

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6  # noqa: E402
import resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler as r7  # noqa: E402
import resume_m05_campaign_batch0006_recovery0008_disk_admission as r8  # noqa: E402
import run_m05_16h_campaign_batch0006 as campaign  # noqa: E402


RECOVERY_ID = "m05_paper_closure_topup_batch0007_3h_20260813"
RUN_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
)
AUTHORITY = RUN_ROOT / "authority.json"
SEED_REGISTRY = RUN_ROOT / "seed_registry.json"
SCHEDULER_EVENTS = RUN_ROOT / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_ROOT / "execution_state.json"
FINAL_VALIDATION = RUN_ROOT / "final_validation.json"
FINAL_LEDGER = RUN_ROOT / "final_ledger.json"
FINAL_UMBRELLA = RUN_ROOT / "final_umbrella.json"
BASE_GLOBAL_CONTRACT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_16h_90gb_campaign_batch0006_v1/global_contract.json"
)

STAGE = "stage10_seven_family"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
WAVES = 4
TASKS = (
    ("eminus", "buildup", 55_000),
    ("muminus", "buildup", 16_000),
    ("eminus", "instant", 55_000),
)
SOURCE_TAG = {"eminus": "eminus", "muminus": "muminus"}
FRESH_SEED_BASE = 1_910_000_007
FRESH_SEED_STRIDE = 65_537
TOTAL_SECONDS = 10_800
STOP_LAUNCH_SECONDS = 9_000
HARD_END_SECONDS = 10_500
FILESYSTEM_RESERVE_BYTES = 20 * 1024**3
CAMPAIGN_CAP_BYTES = 45_000_000_000
PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
EXPECTED_JOBS = WAVES * len(TASKS) * len(GEOMETRIES)
EXPECTED_EVENTS = WAVES * sum(events for _family, _mode, events in TASKS) * len(GEOMETRIES)

_PLAN: list[dict[str, Any]] = []


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def named_seeds(value: Any, out: set[int], key: str = "") -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            named_seeds(child, out, str(child_key).lower())
    elif isinstance(value, list):
        for child in value:
            named_seeds(child, out, key)
    elif isinstance(value, int) and (key == "seed" or key.endswith("_seed")):
        if 1 <= value < 2**31:
            out.add(value)


def registered_seeds() -> tuple[set[int], list[str]]:
    """Read only JSON seed fields and generated source Seed lines."""
    root = ROOT / "runs/particle_source_unit_repair_20260811"
    seeds: set[int] = set()
    json_count = source_count = 0
    for path in sorted(root.rglob("*.json")):
        if RUN_ROOT == path or RUN_ROOT in path.parents:
            continue
        json_count += 1
        try:
            named_seeds(load(path), seeds)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    seed_line = re.compile(r"^\s*Seed\s+(\d+)\s*$", re.MULTILINE)
    for path in sorted(root.rglob("*.source")):
        if RUN_ROOT in path.parents:
            continue
        source_count += 1
        try:
            seeds.update(
                int(value)
                for value in seed_line.findall(
                    path.read_text(encoding="utf-8", errors="replace")
                )
            )
        except OSError:
            continue
    return seeds, [
        f"runs/particle_source_unit_repair_20260811/**/*.json named seed fields ({json_count})",
        f"runs/particle_source_unit_repair_20260811/**/*.source Seed lines ({source_count})",
    ]


def allocate_seeds(count: int, reserved: set[int]) -> list[int]:
    values: list[int] = []
    candidate = FRESH_SEED_BASE
    while len(values) < count:
        if candidate not in reserved and candidate not in values:
            values.append(candidate)
        candidate += FRESH_SEED_STRIDE
        if candidate >= 2**31:
            raise RuntimeError("fresh seed range exhausted")
    return values


def build_plan(reserved: set[int]) -> list[dict[str, Any]]:
    keys = [(wave, family, mode, events) for wave in range(1, WAVES + 1) for family, mode, events in TASKS]
    seeds = allocate_seeds(len(keys), reserved)
    jobs: list[dict[str, Any]] = []
    for (wave, family, mode, events), seed in zip(keys, seeds):
        for geometry in GEOMETRIES:
            is_mu = family == "muminus"
            jobs.append({
                "job_id": f"b7_{family}_{mode}_{geometry}_wave{wave:04d}",
                "stage": STAGE,
                "geometry": geometry,
                "mode": mode,
                "family": family,
                "source_tag": SOURCE_TAG[family],
                "shard_ordinal": wave,
                "events": events,
                "seed": seed,
                "matched_seed_key": f"batch0007|{family}|{mode}|wave{wave:04d}",
                "replan_kind": "fresh_balanced_bundle",
                "supplemental_priority": (
                    "P0_activation_family_precision" if mode == "buildup"
                    else "P1_prompt_zero_limit"
                ),
                "declared_cap_bytes": 1_000_000_000 if is_mu else 1_500_000_000,
                "planned_peak_rss_budget_bytes": 1024**3,
                "planned_wall_budget_s": 2_400.0,
            })
    return jobs


def wave_jobs(plan: list[dict[str, Any]], wave: int) -> list[dict[str, Any]]:
    rows = [job for job in plan if int(job["shard_ordinal"]) == wave]
    return sorted(rows, key=lambda job: (
        TASKS.index((str(job["family"]), str(job["mode"]), int(job["events"]))),
        GEOMETRIES.index(str(job["geometry"])),
    ))


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_ROOT / "job_receipts" / STAGE / f"{job['job_id']}.json"


def structural_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    framing = payload.get("sim", {}).get("strict_framing", {})
    events = int(job["events"])
    directory = ROOT / str(payload.get("attempt_dir", ""))
    return (
        payload.get("status") == "PASS"
        and payload.get("job") == job
        and payload.get("selected_attempt") in (1, 2)
        and directory.is_dir()
        and framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == events
        and int(framing.get("ID_second_count", -1)) == events
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == events
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == events
    )


def prior_attempts(job: dict[str, Any]) -> set[int]:
    used: set[int] = set()
    identity = ("job_id", "seed", "events", "geometry", "mode", "family", "source_tag")
    for path in (RUN_ROOT / "failed_attempts" / str(job["job_id"])).glob("attempt*/validation.json"):
        match = re.fullmatch(r"attempt(\d+)", path.parent.name)
        if not match:
            continue
        old = load(path).get("job", {})
        if all(old.get(key) == job.get(key) for key in identity):
            used.add(int(match.group(1)))
    return used


def rss_evidence(_original: list[dict[str, Any]], _pending: list[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for job in _PLAN:
        path = receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if not structural_receipt(job, payload):
            raise RuntimeError(f"published receipt declaration drift: {job['job_id']}")
        rows[r6.class_key(job)].append((path.stat().st_mtime_ns, int(payload["peak_process_group_rss_bytes"])))
    exact = {}
    for key, values in rows.items():
        recent = sorted(values, reverse=True)[:8]
        exact[key] = {"n": len(values), "recent_n": len(recent), "max_bytes": max(value for _mtime, value in recent)}
    return {"old_exact_classes": {}, "recovery0006_exact_classes": exact, "semantics": "batch0007 receipts only; no old artifact reads"}


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed: int, error: str | None = None) -> None:
    campaign.atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": status,
        "stage": stage,
        "completed_jobs": sum(receipt_path(job).is_file() for job in _PLAN),
        "target_jobs": len(_PLAN),
        "completed_events": sum(int(job["events"]) for job in _PLAN if receipt_path(job).is_file()),
        "target_events": sum(int(job["events"]) for job in _PLAN),
        "scheduler_completed_argument": completed,
        "minimum_target_workers": 6,
        "absolute_worker_cap": 10,
        "deadline": contract["wall_clock"]["deadline"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mem_available_bytes": campaign.mem_available_bytes(),
        "free_disk_bytes": shutil.disk_usage(RUN_ROOT).free,
        "last_error": error,
    })


def bind(plan: list[dict[str, Any]]) -> None:
    global _PLAN
    _PLAN = plan
    campaign.RUN_ROOT = RUN_ROOT
    campaign.RESOURCE_JSONL = RUN_ROOT / "resource_metrics.jsonl"
    campaign.EXECUTION_STATE = EXECUTION_STATE
    campaign.SEED_REGISTRY = SEED_REGISTRY
    campaign.CONTROLLER_LOCK = RUN_ROOT / "controller.lock"
    campaign.FILESYSTEM_RESERVE_BYTES = FILESYSTEM_RESERVE_BYTES

    for module in (r6, r7, r8):
        module.RECOVERY_ID = RECOVERY_ID
        module.RUN_NS = RUN_ROOT
        module.AUTHORITY = AUTHORITY
        module.SCHEDULER_EVENTS = SCHEDULER_EVENTS
        module.EXECUTION_STATE = EXECUTION_STATE
        module.FINAL_VALIDATION = FINAL_VALIDATION
        module.FINAL_LEDGER = FINAL_LEDGER
        module.FINAL_UMBRELLA = FINAL_UMBRELLA
        module.receipt_path = receipt_path

    r6.REPLAN_SEED_REGISTRY = SEED_REGISTRY
    r7.SEED_REGISTRY = SEED_REGISTRY
    r8.SEED_REGISTRY = SEED_REGISTRY
    r6.validate_replan_receipt = structural_receipt
    r7.validate_replan_receipt = structural_receipt
    r8.validate_receipt = structural_receipt
    r6.prior_exact_attempts = prior_attempts
    r7.prior_exact_attempts = prior_attempts
    r6.job_cap = lambda job: int(job["declared_cap_bytes"])
    r6.runtime_job_budget = lambda job, *_args: int(job["planned_peak_rss_budget_bytes"])
    r6.runtime_job_wall_budget = lambda job, *_args: float(job["planned_wall_budget_s"])
    r6.disk_projection = r8.disk_projection
    r6.worker_entry = r8.worker_entry
    r6.reap = r8.reap
    r7.rss_evidence = rss_evidence
    r7.update_state = update_state
    r7.MINIMUM_TARGET_WORKERS = 6
    r7.NORMAL_TARGET_WORKERS = 8
    r7.ABSOLUTE_MAX_WORKERS = 10
    r7.PROJECTED_FLOOR_BYTES = PROJECTED_FLOOR_BYTES
    r7.LAUNCH_STAGGER_S = 10.0
    r8._R7_RUN_STAGE = r7.run_stage
    r6.VALIDATION_PUBLICATION_MARGIN_S = 180.0
    campaign.HARD_LOW_MEMORY_BYTES = 512 * 1024**2


def live_contract(base: dict[str, Any], t0: datetime) -> dict[str, Any]:
    value = deepcopy(base)
    value["batch_id"] = RECOVERY_ID
    value["wall_clock"] = {
        "t0": t0.isoformat(),
        "deadline": (t0 + timedelta(seconds=TOTAL_SECONDS)).isoformat(),
        "total_seconds": TOTAL_SECONDS,
        "stages": [{
            "id": STAGE,
            "start_s": 0,
            "stop_launch_s": STOP_LAUNCH_SECONDS,
            "hard_end_s": HARD_END_SECONDS,
            "declared_cap": 1_500_000_000,
        }],
    }
    value["disk"] = {
        **value.get("disk", {}),
        "requested_campaign_cap_bytes": CAMPAIGN_CAP_BYTES,
        "effective_campaign_cap_bytes": CAMPAIGN_CAP_BYTES,
        "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
    }
    return value


def proposal(plan: list[dict[str, Any]], registry_scope: list[str], reserved_count: int, contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__APPEND_ONLY_CORRECTED_KEV_PAPER_CLOSURE_TOPUP__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "controller": rel(THIS_FILE),
        "namespace": rel(RUN_ROOT),
        "base_global_contract": rel(BASE_GLOBAL_CONTRACT),
        "base_global_contract_sha256": campaign.sha256(BASE_GLOBAL_CONTRACT),
        "source_contract_sha256": campaign.SOURCE_CONTRACT_SHA256,
        "live_contract": contract,
        "plan": plan,
        "planned_jobs": len(plan),
        "planned_events": sum(int(job["events"]) for job in plan),
        "priorities": {
            "P0": "BUILDUP e-/mu-: improve family, isotope-state, and production-position activation precision",
            "P1": "INSTANT e-: improve prompt W2/veto zero-count upper-limit screening",
            "deferred": "prompt gamma/e+ analogue top-up is low-yield and high-memory; delayed chain follows only after corrected inventory normalization",
        },
        "seed_policy": {
            "fresh_unique_seed_count": len({int(job["seed"]) for job in plan}),
            "matched_geometry_pair_uses_same_seed": True,
            "retry_reuses_exact_seed": True,
            "discovered_reserved_seed_count": reserved_count,
            "collision_scan_scope": registry_scope,
        },
        "scheduler": {
            "minimum_target_workers": 6,
            "normal_target_workers": 8,
            "absolute_worker_cap": 10,
            "projected_memavailable_floor_bytes": PROJECTED_FLOOR_BYTES,
            "swap_growth_pauses_launch": True,
            "matched_atomic_wave_jobs": 6,
        },
        "validation_policy": {
            "new_shard_strict_SIM_EOF_ID_IA_energy_geometry_seed_TT_log_and_artifact_hash": True,
            "old_SIM_or_gzip_reopened": False,
            "old_artifact_hashes_recomputed": False,
            "terminal_closure_uses_receipt_declarations": True,
        },
        "frozen": {
            "corrected_keV_sources": True,
            "legacy_2602units_forbidden": True,
            "extra_mono511_added": False,
            "geometry_physics_CUT_thresholds_unchanged": True,
        },
        "authority_boundary": "SUPPLEMENTAL_CORRECTED_KEV_TRANSPORT_AND_PARTIAL_PAPER_SCREENING_ONLY",
    }


def plan_summary(plan: list[dict[str, Any]], reserved_count: int, scope: list[str]) -> dict[str, Any]:
    return {
        "status": "PASS__READ_ONLY_BATCH0007_PLAN",
        "jobs": len(plan),
        "events": sum(int(job["events"]) for job in plan),
        "waves": WAVES,
        "jobs_per_wave": 6,
        "cells": sorted({f"{job['geometry']}/{job['mode']}/{job['family']}" for job in plan}),
        "events_by_cell": {
            key: sum(int(job["events"]) for job in plan if f"{job['geometry']}/{job['mode']}/{job['family']}" == key)
            for key in sorted({f"{job['geometry']}/{job['mode']}/{job['family']}" for job in plan})
        },
        "fresh_seeds": len({int(job["seed"]) for job in plan}),
        "fresh_seed_collision_count": 0,
        "reserved_seed_count": reserved_count,
        "collision_scan_scope": scope,
        "transport_launched": False,
        "run_root_created": RUN_ROOT.exists(),
    }


def process_gate() -> list[dict[str, Any]]:
    rows = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc.name)
            if pid == os.getpid():
                continue
            comm = proc.joinpath("comm").read_text(encoding="utf-8").strip()
            cmd = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ValueError):
            continue
        if comm == "cosima" or (comm.startswith("python") and "run_m05" in cmd and "monitor_" not in cmd):
            rows.append({"pid": pid, "comm": comm, "cmd": cmd[:500]})
    return rows


def publish_final(plan: list[dict[str, Any]], fatal: str | None) -> None:
    if any(path.is_file() for path in (FINAL_VALIDATION, FINAL_LEDGER, FINAL_UMBRELLA)):
        if not all(path.is_file() for path in (FINAL_VALIDATION, FINAL_LEDGER, FINAL_UMBRELLA)):
            raise RuntimeError("partial terminal publication set")
        return
    receipts = []
    missing = []
    for job in plan:
        path = receipt_path(job)
        if not path.is_file():
            missing.append(str(job["job_id"]))
            continue
        payload = load(path)
        if not structural_receipt(job, payload):
            raise RuntimeError(f"terminal receipt declaration drift: {job['job_id']}")
        receipts.append((job, path, payload))
    complete = fatal is None and not missing and len(receipts) == EXPECTED_JOBS
    status = (
        "PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE"
        if complete else "FAIL__BATCH0007_INCOMPLETE"
    )
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    for job, _path, payload in receipts:
        key = (str(job["geometry"]), str(job["mode"]), str(job["family"]))
        cell = cells.setdefault(key, {
            "geometry": key[0], "mode": key[1], "family": key[2],
            "jobs": 0, "events": 0, "TT_s": 0.0, "RP_record_count": 0,
            "RP_sum": 0.0, "artifact_bytes": 0, "wall_sum_s": 0.0,
            "max_process_group_rss_bytes": 0,
        })
        isotope = payload["isotope_dat"]
        cell["jobs"] += 1
        cell["events"] += int(job["events"])
        cell["TT_s"] = math.fsum((float(cell["TT_s"]), float(isotope["TT_s"])))
        cell["RP_record_count"] += int(isotope["RP_record_count"])
        cell["RP_sum"] = math.fsum((float(cell["RP_sum"]), float(isotope["RP_sum"])))
        cell["artifact_bytes"] += sum(int(row["bytes"]) for row in payload["artifacts"].values())
        cell["wall_sum_s"] = math.fsum((float(cell["wall_sum_s"]), float(payload["wall_s"])))
        cell["max_process_group_rss_bytes"] = max(
            int(cell["max_process_group_rss_bytes"]),
            int(payload["peak_process_group_rss_bytes"]),
        )
    selected = [{
        "job_id": job["job_id"], "path": rel(path), "events": job["events"],
        "selected_attempt": payload["selected_attempt"],
        "declared_artifacts": payload["artifacts"],
    } for job, path, payload in receipts]
    validation = {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "errors": [] if fatal is None else [fatal], "missing_jobs": missing,
        "validated_jobs": len(receipts),
        "validated_events": sum(int(job["events"]) for job, _path, _payload in receipts),
        "cells": [cells[key] for key in sorted(cells)],
        "selected_receipts": selected,
        "closure_mode": "new-shard strict validation plus terminal receipt declarations",
        "old_artifact_hashes_recomputed": False, "old_gzip_reopened": False,
        "authority_boundary": "supplemental corrected-keV transport; not delayed/mission-sensitivity/final geometry authority",
    }
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    campaign.atomic_write_once_json(FINAL_LEDGER, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "validation": rel(FINAL_VALIDATION), "selected_receipts": selected,
        "missing_jobs": missing, "errors": validation["errors"],
        "artifact_hashes_recomputed_at_terminal": False,
    })
    campaign.atomic_write_once_json(FINAL_UMBRELLA, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "authority": rel(AUTHORITY), "seed_registry": rel(SEED_REGISTRY),
        "final_validation": rel(FINAL_VALIDATION), "final_ledger": rel(FINAL_LEDGER),
        "authority_boundary": validation["authority_boundary"],
    })


def self_test() -> dict[str, Any]:
    reserved, scope = registered_seeds()
    plan = build_plan(reserved)
    assert len(plan) == EXPECTED_JOBS
    assert sum(int(job["events"]) for job in plan) == EXPECTED_EVENTS
    assert len({int(job["seed"]) for job in plan}) == WAVES * len(TASKS)
    assert not ({int(job["seed"]) for job in plan} & reserved)
    assert all(len(wave_jobs(plan, wave)) == 6 for wave in range(1, WAVES + 1))
    assert all(len({job["seed"] for job in wave_jobs(plan, wave)}) == 3 for wave in range(1, WAVES + 1))
    assert all(sum(job["geometry"] == geometry for job in wave_jobs(plan, wave)) == 3 for wave in range(1, WAVES + 1) for geometry in GEOMETRIES)
    return {
        "status": "PASS__BATCH0007_STATIC_SELF_TEST", "tests": 7,
        "jobs": len(plan), "events": EXPECTED_EVENTS, "waves": WAVES,
        "reserved_seeds": len(reserved), "scan_scope": scope,
        "transport_launched": False, "old_artifacts_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()

    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0

    if AUTHORITY.is_file():
        authority = load(AUTHORITY)
        plan = authority.get("plan")
        if not isinstance(plan, list) or len(plan) != EXPECTED_JOBS:
            raise RuntimeError("existing batch0007 authority plan drift")
        contract = authority.get("live_contract")
        if not isinstance(contract, dict):
            raise RuntimeError("existing batch0007 authority lacks live contract")
        scope = authority["seed_policy"]["collision_scan_scope"]
        reserved_count = int(authority["seed_policy"]["discovered_reserved_seed_count"])
    else:
        reserved, scope = registered_seeds()
        plan = build_plan(reserved)
        reserved_count = len(reserved)
        base = load(BASE_GLOBAL_CONTRACT)
        contract = live_contract(base, datetime.now(timezone.utc))
        authority = proposal(plan, scope, reserved_count, contract)

    if args.print_plan:
        print(json.dumps(plan_summary(plan, reserved_count, scope), indent=2, sort_keys=True))
        return 0

    if FINAL_UMBRELLA.is_file():
        payload = load(FINAL_UMBRELLA)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if str(payload.get("status", "")).startswith("PASS") else 1

    live = process_gate()
    if live:
        raise RuntimeError(f"live transport/controller process gate failed: {live}")
    if campaign.mem_available_bytes() < 7 * 1024**3:
        raise RuntimeError("startup MemAvailable below 7 GiB light-worker launch gate")
    if shutil.disk_usage(ROOT).free < FILESYSTEM_RESERVE_BYTES + 10_000_000_000:
        raise RuntimeError("startup disk lacks 20 GiB reserve plus first-wave admission")

    bind(plan)
    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    fatal: str | None = None
    try:
        if not AUTHORITY.is_file():
            campaign.atomic_write_once_json(AUTHORITY, authority)
        authority = load(AUTHORITY)
        if not SEED_REGISTRY.is_file():
            campaign.atomic_write_once_json(SEED_REGISTRY, {
                "schema_version": 1,
                "status": "FROZEN__BATCH0007_FRESH_MATCHED_SEEDS_REGISTERED",
                "seeds": [{
                    "seed": seed,
                    "jobs": sorted(job["job_id"] for job in plan if int(job["seed"]) == seed),
                } for seed in sorted({int(job["seed"]) for job in plan})],
                "retry_reuses_exact_seed": True,
                "collision_count_at_allocation": 0,
                "scan_scope": scope,
            })
        r6.configure_validator()
        environment = r7.load_runtime_without_hash_revalidation(
            load(BASE_GLOBAL_CONTRACT), args.cosima.resolve()
        )
        campaign._STOP_REQUESTED = False
        r6._COORDINATOR_STOP = False
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, r6.coordinator_signal)
        update_state(contract, status="RUNNING__BATCH0007__TARGET6_CAP10", stage=STAGE, completed=0)
        r6.append_event(
            "controller_started", jobs=len(plan), events=EXPECTED_EVENTS,
            minimum_target_workers=6, normal_target_workers=8, absolute_worker_cap=10,
            old_artifacts_rehashed=False,
        )
        for wave in range(1, WAVES + 1):
            rows = wave_jobs(plan, wave)
            r6.append_event(
                "matched_wave_start", wave=wave, jobs=len(rows),
                matched_seed_keys=sorted({job["matched_seed_key"] for job in rows}),
            )
            reason = r8.run_stage(STAGE, rows, [], contract, environment, authority, {})
            if reason:
                fatal = f"wave{wave}: {reason}"
                break
            if not all(receipt_path(job).is_file() and structural_receipt(job, load(receipt_path(job))) for job in rows):
                fatal = f"wave{wave}: matched wave did not close all six receipts"
                break
            r6.append_event("matched_wave_PASS", wave=wave, jobs=len(rows))
        publish_final(plan, fatal)
        completed = sum(receipt_path(job).is_file() for job in plan)
        update_state(
            contract,
            status="FINALIZED__PASS" if fatal is None and completed == len(plan) else "FINALIZED__INCOMPLETE",
            stage="final", completed=completed, error=fatal,
        )
        return 0 if fatal is None and completed == len(plan) else 1
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
