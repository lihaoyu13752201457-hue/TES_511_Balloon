#!/usr/bin/env python3
"""Power-loss recovery and resource-gated concurrent controller for batch0006.

This recovery preserves the frozen global contract, plan, seeds, event counts,
sources, geometries, physics, T0, stage stop-launch times, and campaign
deadline.  It archives a host-shutdown-interrupted attempt without deletion and
retries the same frozen job with the same seed.  Concurrency is process-level
because the installed Cosima is single-threaded.

The user explicitly requested parallel execution after reviewing live memory.
The scheduler may use four workers for measured light classes.  An O8 class
reduces the active set to at most three (one O8 plus two companions), with no
more than one heavy O8; proton remains capped at two.  Every launch is additionally
guarded by class RSS, current MemAvailable, active declared disk caps, and the
original stage deadlines.
"""

from __future__ import annotations

import argparse
import fcntl
import gzip
import json
import math
import multiprocessing as mp
import os
import re
import shutil
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0001 as recovery1
import resume_m05_campaign_batch0006_recovery0002_early_stages as recovery2
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0003_powerloss_concurrent"
AUTHORITY = campaign.RUN_ROOT / "recovery0003_powerloss_concurrent_authority.json"
RECOVERY2_AUTHORITY = campaign.RUN_ROOT / "recovery0002_early_stages_authority.json"
RECOVERY2_GUARD = (
    campaign.RUN_ROOT / "recovery0002_final_failure_guard0001_authority.json"
)
RECOVERY1_SMOKE_DECISION = campaign.RUN_ROOT / "smoke_decision.recovery0001.json"

STAGE_PATHS = {
    "stage00_mergeable_smoke": (
        campaign.RUN_ROOT / "checkpoint_authority/smoke_validation.recovery0001.json",
        campaign.RUN_ROOT / "checkpoint_authority/smoke_ledger.recovery0001.json",
    ),
    "stage10_seven_family": (
        campaign.RUN_ROOT / "seven_family_validation.recovery0003.json",
        campaign.RUN_ROOT / "seven_family_ledger.recovery0003.json",
    ),
    "stage20_proton": (
        campaign.RUN_ROOT / "proton_validation.recovery0003.json",
        campaign.RUN_ROOT / "proton_ledger.recovery0003.json",
    ),
}
FINAL_VALIDATION = campaign.RUN_ROOT / "final_validation.recovery0003.json"
FINAL_LEDGER = campaign.RUN_ROOT / "final_ledger.recovery0003.json"
FINAL_UMBRELLA = campaign.RUN_ROOT / "final_umbrella.recovery0003.json"
INTERRUPTION_RECEIPT = campaign.RUN_ROOT / "recovery0003_powerloss_interruption.json"

MAX_LIGHT_WORKERS = 4
MAX_HEAVY_O8_ACTIVE_SET = 3
MAX_PROTON_WORKERS = 2
HISTORICAL_HEAVY_O8_RSS_BYTES = int(4.98 * 1024**3)
HEAVY_O8_FAMILIES = {"neutron", "eplus", "alpha", "proton"}
SCHEDULER_POLL_S = 0.5

_COORDINATOR_STOP = False
_ACTIVE_WORKERS: dict[int, "Worker"] = {}


@dataclass
class Worker:
    job: dict[str, Any]
    process: Any
    connection: Any
    launched_at: str


def stage_paths(stage: str) -> tuple[Path, Path]:
    return STAGE_PATHS[stage]


def is_heavy_o8(job: dict[str, Any]) -> bool:
    return (
        job["geometry"] == "S3d_O8"
        and job["family"] in HEAVY_O8_FAMILIES
    )


def configure_runtime() -> None:
    campaign.ID_RE = recovery1.re.compile(recovery1.CORRECT_ID_PATTERN)
    recovery1.RECOVERY_ID = RECOVERY_ID
    recovery1.RECOVERY_AUTHORITY = AUTHORITY
    recovery1.RECOVERY_STAGE_PATHS = STAGE_PATHS
    recovery1.RECOVERY_FINAL_VALIDATION = FINAL_VALIDATION
    recovery1.RECOVERY_FINAL_LEDGER = FINAL_LEDGER
    recovery1.RECOVERY_FINAL_UMBRELLA = FINAL_UMBRELLA
    campaign.stage_paths = stage_paths
    campaign.validate_attempt = recovery1.strict_validate_attempt
    campaign.ensure_job = recovery1.strict_ensure_job
    # Recovery0002 already authorized early Stage10 and Stage20 starts.  Only
    # start waits are removed; stop-launch and hard-end values are untouched.
    campaign.STAGES["stage10_seven_family"]["start_s"] = 0
    campaign.STAGES["stage20_proton"]["start_s"] = 0


def frozen_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = recovery1.frozen_contract()
    plan = campaign.build_plan()
    if contract.get("planned_jobs_sha256") != campaign.json_sha256(plan):
        raise RuntimeError("current plan differs from frozen global contract")
    required = [
        campaign.GLOBAL_CONTRACT,
        campaign.SEED_REGISTRY,
        recovery1.RECOVERY_AUTHORITY,
        RECOVERY1_SMOKE_DECISION,
        STAGE_PATHS["stage00_mergeable_smoke"][0],
        STAGE_PATHS["stage00_mergeable_smoke"][1],
        RECOVERY2_AUTHORITY,
        RECOVERY2_GUARD,
    ]
    missing = [campaign.rel(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("missing recovery authority inputs: " + ", ".join(missing))
    smoke = campaign.load_json(RECOVERY1_SMOKE_DECISION)
    if (
        smoke.get("status") != "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE"
        or smoke.get("production_may_continue") is not True
    ):
        raise RuntimeError("recovery0001 smoke does not authorize production")
    validation = campaign.load_json(STAGE_PATHS["stage00_mergeable_smoke"][0])
    if validation.get("validated_jobs") != 100 or validation.get(
        "validated_events"
    ) != 55_424:
        raise RuntimeError("recovery0001 smoke closure differs")
    return contract, plan


def file_manifest(directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": campaign.sha256(path),
        }
        for path in sorted(directory.iterdir())
        if path.is_file()
    ]


def interrupted_partials(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jobs = {str(row["job_id"]): row for row in plan}
    rows: list[dict[str, Any]] = []
    for partial in sorted(
        path
        for path in campaign.RUN_ROOT.glob("stage*/**/.attempt*.partial")
        if path.is_dir()
    ):
        match = re.fullmatch(r"\.attempt(\d+)\.partial", partial.name)
        sources = list(partial.glob("*.source"))
        if not match or len(sources) != 1 or sources[0].stem not in jobs:
            raise RuntimeError(f"unrecognized interrupted attempt: {campaign.rel(partial)}")
        job = jobs[sources[0].stem]
        attempt = int(match.group(1))
        target = (
            campaign.RUN_ROOT
            / "failed_attempts"
            / str(job["job_id"])
            / f"attempt{attempt:02d}"
        )
        rows.append(
            {
                "job": job,
                "attempt": attempt,
                "partial_path": campaign.rel(partial),
                "archive_path": campaign.rel(target),
                "files": file_manifest(partial),
            }
        )
    return rows


def receipt_rss_summary() -> dict[str, Any]:
    by_geometry: dict[str, list[int]] = {name: [] for name in campaign.GEOMETRY_ORDER}
    by_class: dict[str, list[int]] = {}
    receipts = 0
    for path in campaign.RUN_ROOT.glob("job_receipts/**/*.json"):
        payload = campaign.load_json(path)
        if payload.get("status") != "PASS" or payload.get("errors"):
            continue
        receipts += 1
        job = payload["job"]
        value = int(payload["peak_process_group_rss_bytes"])
        geometry = str(job["geometry"])
        key = f"{geometry}/{job['family']}"
        by_geometry.setdefault(geometry, []).append(value)
        by_class.setdefault(key, []).append(value)

    def upper(values: list[int]) -> int:
        ordered = sorted(values)
        if not ordered:
            return 0
        return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]

    return {
        "complete_pass_receipts": receipts,
        "geometry": {
            key: {
                "n": len(values),
                "p95_upper_bytes": upper(values),
                "max_bytes": max(values, default=0),
            }
            for key, values in by_geometry.items()
        },
        "classes": {
            key: {
                "n": len(values),
                "p95_upper_bytes": upper(values),
                "max_bytes": max(values, default=0),
            }
            for key, values in sorted(by_class.items())
        },
    }


def proposed_authority(
    contract: dict[str, Any], plan: list[dict[str, Any]]
) -> dict[str, Any]:
    partials = interrupted_partials(plan)
    rss = receipt_rss_summary()
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "PASS__POWERLOSS_RECOVERY__USER_AUTHORIZED_RESOURCE_GATED_CONCURRENCY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authorization": {
            "source": "direct user instructions in controlling Codex thread",
            "instructions": [
                "continue after the computer unexpectedly powered off",
                "use parallel cores after checking live memory",
                "consider one additional core when memory permits",
            ],
            "scope": "recovery, process concurrency, and scheduling only",
        },
        "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "seed_registry": campaign.rel(campaign.SEED_REGISTRY),
        "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
        "planned_jobs_sha256": campaign.json_sha256(plan),
        "planned_jobs": len(plan),
        "planned_events": sum(int(row["events"]) for row in plan),
        "recovery0001_smoke_decision_sha256": campaign.sha256(
            RECOVERY1_SMOKE_DECISION
        ),
        "recovery0001_smoke_validation_sha256": campaign.sha256(
            STAGE_PATHS["stage00_mergeable_smoke"][0]
        ),
        "recovery0001_smoke_ledger_sha256": campaign.sha256(
            STAGE_PATHS["stage00_mergeable_smoke"][1]
        ),
        "recovery0002_scheduling_authority_sha256": campaign.sha256(
            RECOVERY2_AUTHORITY
        ),
        "recovery0002_final_guard_sha256": campaign.sha256(RECOVERY2_GUARD),
        "controller": {
            "path": campaign.rel(Path(__file__).resolve()),
            "sha256": campaign.sha256(Path(__file__).resolve()),
        },
        "frozen_clock": {
            "t0": contract["wall_clock"]["t0"],
            "deadline": contract["wall_clock"]["deadline"],
            "stage10_stop_launch_s": campaign.STAGES["stage10_seven_family"][
                "stop_launch_s"
            ],
            "stage10_hard_end_s": campaign.STAGES["stage10_seven_family"][
                "hard_end_s"
            ],
            "stage20_stop_launch_s": campaign.STAGES["stage20_proton"][
                "stop_launch_s"
            ],
            "stage20_hard_end_s": campaign.STAGES["stage20_proton"][
                "hard_end_s"
            ],
        },
        "concurrency": {
            "mechanism": "independent single-thread Cosima worker processes",
            "stage10_max_light_workers": MAX_LIGHT_WORKERS,
            "historical_heavy_o8_active_set_max": MAX_HEAVY_O8_ACTIVE_SET,
            "stage20_max_workers": MAX_PROTON_WORKERS,
            "heavy_o8_families": sorted(HEAVY_O8_FAMILIES),
            "historical_heavy_o8_rss_bytes": HISTORICAL_HEAVY_O8_RSS_BYTES,
            "launch_formula": "sum(class_rss_upper)+2GiB < current MemAvailable",
            "one_heavy_o8_at_a_time": True,
            "active_declared_caps_in_disk_gate": True,
        },
        "rss_evidence_at_authorization": rss,
        "mem_available_bytes_at_authorization": campaign.mem_available_bytes(),
        "interrupted_attempts": partials,
        "interruption_rule": (
            "archive without deletion; publish FAIL interruption receipt; exact "
            "same frozen seed/events/source job retries at next unused attempt ordinal"
        ),
        "unchanged": {
            "jobs_seeds_events": True,
            "sources_spectra_geometries": True,
            "physics_cut_detector_veto": True,
            "validation_and_merge_domains": True,
            "t0_stage_deadlines_campaign_deadline": True,
            "failed_and_canonical_artifacts": True,
        },
        "publication_namespace": {
            "stage00": "immutable recovery0001 smoke",
            "stage10": campaign.rel(STAGE_PATHS["stage10_seven_family"][1]),
            "stage20": campaign.rel(STAGE_PATHS["stage20_proton"][1]),
            "final": campaign.rel(FINAL_UMBRELLA),
        },
    }


def load_or_publish_authority(
    contract: dict[str, Any], plan: list[dict[str, Any]], *, publish: bool
) -> dict[str, Any]:
    if AUTHORITY.is_file():
        payload = campaign.load_json(AUTHORITY)
    else:
        payload = proposed_authority(contract, plan)
        if not publish:
            return payload
        campaign.atomic_write_once_json(AUTHORITY, payload)
        payload = campaign.load_json(AUTHORITY)
    expected = {
        "recovery_id": RECOVERY_ID,
        "status": "PASS__POWERLOSS_RECOVERY__USER_AUTHORIZED_RESOURCE_GATED_CONCURRENCY",
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
        "planned_jobs_sha256": campaign.json_sha256(plan),
        "recovery0002_scheduling_authority_sha256": campaign.sha256(
            RECOVERY2_AUTHORITY
        ),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"recovery0003 authority drift: {key}")
    if payload.get("controller", {}).get("sha256") != campaign.sha256(
        Path(__file__).resolve()
    ):
        raise RuntimeError("recovery0003 controller differs from authority")
    if payload.get("frozen_clock", {}).get("deadline") != contract[
        "wall_clock"
    ]["deadline"]:
        raise RuntimeError("recovery0003 deadline drift")
    return payload


def strict_gzip_observation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False}
    total = 0
    error: str | None = None
    try:
        with gzip.open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                total += len(chunk)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "present": True,
        "compressed_bytes": path.stat().st_size,
        "decompressed_bytes_before_error_or_eof": total,
        "strict_eof_pass": error is None,
        "error": error,
    }


def archive_powerloss_attempts(
    authority: dict[str, Any], plan: list[dict[str, Any]]
) -> None:
    jobs = {str(row["job_id"]): row for row in plan}
    published: list[dict[str, Any]] = []
    for row in authority.get("interrupted_attempts", []):
        job = row["job"]
        if jobs.get(str(job["job_id"])) != job:
            raise RuntimeError("interrupted job differs from frozen plan")
        partial = campaign.ROOT / row["partial_path"]
        target = campaign.ROOT / row["archive_path"]
        if partial.is_dir() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(partial, target)
        if not target.is_dir() or partial.exists():
            raise RuntimeError("power-loss attempt archive did not close atomically")
        current = [
            item for item in file_manifest(target) if item["name"] != "validation.json"
        ]
        if current != row["files"]:
            raise RuntimeError("power-loss archived artifact hashes differ")
        sim = target / f"{job['job_id']}.inc1.id1.sim.gz"
        observation = strict_gzip_observation(sim)
        validation_path = target / "validation.json"
        validation = {
            "schema_version": 1,
            "status": "FAIL",
            "errors": ["unexpected_host_shutdown_before_attempt_completion"],
            "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
            "recovery_authority_sha256": campaign.sha256(AUTHORITY),
            "job": job,
            "selected_attempt": None,
            "attempt": int(row["attempt"]),
            "attempt_dir": campaign.rel(target),
            "returncode": None,
            "watchdog_reason": "host_power_loss",
            "artifacts": current,
            "sim_gzip_observation": observation,
            "merge_eligible": False,
            "retry_contract": "exact_same_seed_events_source_job_at_next_unused_attempt",
        }
        campaign.atomic_write_once_json(validation_path, validation)
        published.append(
            {
                "job_id": job["job_id"],
                "attempt": row["attempt"],
                "archive": campaign.rel(target),
                "validation": campaign.rel(validation_path),
                "validation_sha256": campaign.sha256(validation_path),
                "files": current,
            }
        )
    campaign.atomic_write_once_json(
        INTERRUPTION_RECEIPT,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__INTERRUPTED_ATTEMPTS_PRESERVED__NOT_MERGEABLE",
            "authority_sha256": campaign.sha256(AUTHORITY),
            "interrupted_attempts": published,
        },
    )


def bind_stage(
    stage: str, validation: dict[str, Any], ledger: dict[str, Any]
) -> None:
    validation_path, ledger_path = stage_paths(stage)
    path = (
        campaign.RUN_ROOT
        / "checkpoint_authority"
        / f"{stage}.recovery0003.binding.json"
    )
    campaign.atomic_write_once_json(
        path,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__HASH_BOUND_RECOVERY0003_PUBLICATION",
            "recovery_authority": campaign.rel(AUTHORITY),
            "recovery_authority_sha256": campaign.sha256(AUTHORITY),
            "validation": campaign.rel(validation_path),
            "validation_sha256": campaign.sha256(validation_path),
            "ledger": campaign.rel(ledger_path),
            "ledger_sha256": campaign.sha256(ledger_path),
            "validation_status": validation["status"],
            "ledger_status": ledger["status"],
        },
    )


def rss_upper_for_job(job: dict[str, Any], evidence: dict[str, Any]) -> int:
    geometry = str(job["geometry"])
    key = f"{geometry}/{job['family']}"
    geo = evidence["geometry"].get(geometry, {})
    cls = evidence["classes"].get(key, {})
    value = max(
        int(geo.get("p95_upper_bytes", 0)),
        int(cls.get("p95_upper_bytes", 0)),
        int(cls.get("max_bytes", 0)),
        1024**3,
    )
    if is_heavy_o8(job):
        value = max(value, HISTORICAL_HEAVY_O8_RSS_BYTES)
    return value


def memory_launch_gate(
    jobs: list[dict[str, Any]], evidence: dict[str, Any]
) -> dict[str, Any]:
    required = sum(rss_upper_for_job(job, evidence) for job in jobs)
    required += campaign.RSS_SCALE_HEADROOM_BYTES
    available = campaign.mem_available_bytes()
    return {
        "status": "PASS" if required < available else "WAIT",
        "required_bytes": required,
        "mem_available_bytes": available,
        "margin_bytes": available - required,
    }


def parallel_disk_gate(
    contract: dict[str, Any], stage: str, active_after_launch: int
) -> dict[str, Any]:
    cap = int(contract["disk"]["effective_campaign_cap_bytes"])
    declared = int(campaign.STAGES[stage]["declared_cap"])
    active_cap = declared * active_after_launch
    used = campaign.campaign_bytes()
    free = shutil.disk_usage(campaign.RUN_ROOT).free
    stage_limit = cap - (
        20_000_000_000
        if stage == "stage10_seven_family"
        else campaign.CAMPAIGN_EMERGENCY_BYTES
    )
    errors: list[str] = []
    if used + active_cap > stage_limit:
        errors.append("campaign_cap_with_all_active_declared_caps")
    if free < campaign.FILESYSTEM_RESERVE_BYTES + active_cap:
        errors.append("filesystem_reserve_with_all_active_declared_caps")
    return {
        "status": "PASS" if not errors else "STOP_LAUNCH",
        "campaign_bytes": used,
        "free_bytes": free,
        "active_declared_caps_bytes": active_cap,
        "stage_limit_bytes": stage_limit,
        "errors": errors,
    }


def worker_entry(
    job: dict[str, Any],
    contract: dict[str, Any],
    environment: dict[str, str],
    hard_end_iso: str,
    connection: Any,
) -> None:
    configure_runtime()
    campaign._STOP_REQUESTED = False
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, campaign._signal_handler)
    try:
        result = concurrent_ensure_job(
            job,
            contract,
            environment,
            datetime.fromisoformat(hard_end_iso),
        )
        connection.send(
            {
                "status": "PASS",
                "job_id": job["job_id"],
                "receipt": campaign.rel(campaign.receipt_path(job)),
                "receipt_sha256": campaign.sha256(campaign.receipt_path(job)),
                "events": job["events"],
            }
        )
    except BaseException as exc:
        connection.send(
            {
                "status": "FAIL",
                "job_id": job["job_id"],
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
        connection.close()


def concurrent_ensure_job(
    job: dict[str, Any],
    contract: dict[str, Any],
    environment: dict[str, str],
    hard_deadline: datetime,
) -> dict[str, Any]:
    """Strict exact retry with a stop check between attempts."""
    receipt = campaign.receipt_path(job)
    if receipt.is_file():
        payload = campaign.load_json(receipt)
        if not campaign.receipt_hashes_valid(payload):
            raise RuntimeError(f"immutable PASS receipt failed: {job['job_id']}")
        return payload
    failures = campaign.RUN_ROOT / "failed_attempts" / str(job["job_id"])
    used = {
        int(match.group(1))
        for path in failures.glob("attempt*/validation.json")
        if (match := re.match(r"attempt(\d+)$", path.parent.name))
    }
    for attempt in range(1, campaign.MAX_ATTEMPTS + 1):
        if attempt in used:
            continue
        if campaign._STOP_REQUESTED:
            raise RuntimeError("worker stop requested before next exact attempt")
        if datetime.now(timezone.utc) >= hard_deadline:
            raise RuntimeError("stage hard deadline before attempt")
        errors = recovery1.input_hash_gate(job, contract)
        if errors:
            raise RuntimeError("pre-attempt input hash gate: " + "; ".join(errors))
        result = campaign.run_attempt(
            job, attempt, contract, environment, hard_deadline
        )
        if result["status"] == "PASS":
            return result
        if campaign._STOP_REQUESTED:
            raise RuntimeError("worker stopped after preserving interrupted attempt")
    raise RuntimeError(f"{job['job_id']} exhausted two exact same-seed attempts")


def launch_worker(
    context: Any,
    job: dict[str, Any],
    contract: dict[str, Any],
    environment: dict[str, str],
    hard_end: datetime,
) -> Worker:
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=worker_entry,
        args=(job, contract, environment, hard_end.isoformat(), child),
        name=f"m05-{job['job_id']}",
    )
    process.start()
    child.close()
    worker = Worker(job, process, parent, datetime.now(timezone.utc).isoformat())
    _ACTIVE_WORKERS[process.pid] = worker
    return worker


def reap_workers(
    active: list[Worker], failures: list[str]
) -> list[Worker]:
    remaining: list[Worker] = []
    for worker in active:
        if worker.process.is_alive():
            remaining.append(worker)
            continue
        worker.process.join(timeout=1)
        message: dict[str, Any]
        if worker.connection.poll():
            try:
                message = worker.connection.recv()
            except EOFError:
                message = {
                    "status": "FAIL",
                    "job_id": worker.job["job_id"],
                    "error": f"worker exited {worker.process.exitcode} with pipe EOF",
                }
        else:
            message = {
                "status": "FAIL",
                "job_id": worker.job["job_id"],
                "error": f"worker exited {worker.process.exitcode} without result",
            }
        worker.connection.close()
        _ACTIVE_WORKERS.pop(worker.process.pid, None)
        if message.get("status") != "PASS":
            failures.append(f"{message['job_id']}: {message.get('error')}")
            continue
        receipt = campaign.receipt_path(worker.job)
        if not receipt.is_file() or not campaign.receipt_hashes_valid(
            campaign.load_json(receipt)
        ):
            failures.append(f"{worker.job['job_id']}: PASS receipt hash closure failed")
    return remaining


def coordinator_signal(signum: int, _frame: Any) -> None:
    global _COORDINATOR_STOP
    _COORDINATOR_STOP = True
    for worker in list(_ACTIVE_WORKERS.values()):
        if worker.process.is_alive():
            try:
                os.kill(worker.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def choose_candidate(
    pending: list[dict[str, Any]], active: list[Worker], stage: str
) -> tuple[int, dict[str, Any]] | None:
    active_jobs = [worker.job for worker in active]
    active_o8 = sum(job["geometry"] == "S3d_O8" for job in active_jobs)
    active_heavy = sum(is_heavy_o8(job) for job in active_jobs)
    if stage == "stage20_proton":
        capacity = MAX_PROTON_WORKERS
    elif active_o8:
        capacity = MAX_HEAVY_O8_ACTIVE_SET
    else:
        capacity = MAX_LIGHT_WORKERS
    if len(active) >= capacity:
        return None

    # Do not skip a heavy O8 at the fair queue head indefinitely.  Drain light
    # workers until it can enter a two-process heavy set.
    first_o8 = next(
        (index for index, job in enumerate(pending) if job["geometry"] == "S3d_O8"),
        None,
    )
    if first_o8 is not None and first_o8 <= 2 and not active_o8:
        if len(active) >= MAX_HEAVY_O8_ACTIVE_SET:
            return None
        candidate = pending[first_o8]
        if is_heavy_o8(candidate) and active_heavy:
            return None
        return first_o8, candidate

    for index, job in enumerate(pending):
        if is_heavy_o8(job):
            if active_heavy or len(active) >= MAX_HEAVY_O8_ACTIVE_SET:
                continue
        if job["geometry"] == "S3d_O8" and len(active) >= MAX_HEAVY_O8_ACTIVE_SET:
            continue
        return index, job
    return None


def validate_existing_receipts(plan: list[dict[str, Any]]) -> None:
    for job in plan:
        path = campaign.receipt_path(job)
        if path.is_file() and not campaign.receipt_hashes_valid(
            campaign.load_json(path)
        ):
            raise RuntimeError(f"existing receipt hash revalidation failed: {job['job_id']}")


def run_parallel_stage(
    stage: str,
    plan: list[dict[str, Any]],
    contract: dict[str, Any],
    environment: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    timing = campaign.STAGES[stage]
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    stop_launch = t0 + timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + timedelta(seconds=int(timing["hard_end_s"]))
    ordered = recovery1.scheduled_jobs(stage, plan)
    pending = [job for job in ordered if not campaign.receipt_path(job).is_file()]
    active: list[Worker] = []
    failures: list[str] = []
    stop_reason: str | None = None
    context = mp.get_context("fork")
    evidence = receipt_rss_summary()
    last_state = 0.0

    while pending or active:
        active = reap_workers(active, failures)
        if failures and stop_reason is None:
            stop_reason = "worker failure after exact retry: " + failures[0]
        now = datetime.now(timezone.utc)
        launch_allowed = (
            not _COORDINATOR_STOP
            and stop_reason is None
            and now < stop_launch
        )
        launched = False
        while launch_allowed and pending:
            selected = choose_candidate(pending, active, stage)
            if selected is None:
                break
            index, job = selected
            prospective = [worker.job for worker in active] + [job]
            memory = memory_launch_gate(prospective, evidence)
            if memory["status"] != "PASS":
                break
            disk = parallel_disk_gate(contract, stage, len(prospective))
            if disk["status"] != "PASS":
                stop_reason = "disk stop-launch gate: " + ",".join(disk["errors"])
                launch_allowed = False
                break
            pending.pop(index)
            active.append(
                launch_worker(context, job, contract, environment, hard_end)
            )
            launched = True
            # A newly launched heavy O8 immediately reduces total capacity.
            if is_heavy_o8(job) and len(active) >= MAX_HEAVY_O8_ACTIVE_SET:
                break
        if now >= stop_launch and not active:
            break
        if stop_reason is not None and not active:
            break
        if _COORDINATOR_STOP and not active:
            stop_reason = stop_reason or "coordinator stop requested"
            break
        if datetime.now(timezone.utc) >= hard_end and active:
            for worker in active:
                if worker.process.is_alive():
                    os.kill(worker.process.pid, signal.SIGTERM)
        if time.monotonic() - last_state >= 30:
            completed = sum(campaign.receipt_path(job).is_file() for job in plan)
            campaign.update_state(
                contract,
                status=f"RUNNING__RECOVERY0003__CONCURRENT_{len(active)}",
                stage=stage,
                completed_jobs=completed,
                last_error=stop_reason,
            )
            last_state = time.monotonic()
        if not launched:
            time.sleep(SCHEDULER_POLL_S)

    while active:
        active = reap_workers(active, failures)
        if active:
            time.sleep(SCHEDULER_POLL_S)
    if failures and stop_reason is None:
        stop_reason = "worker failure after exact retry: " + failures[0]
    validation, ledger = campaign.publish_stage(stage, plan, contract, stop_reason)
    bind_stage(stage, validation, ledger)
    return validation, ledger


def publish_final(
    plan: list[dict[str, Any]], contract: dict[str, Any], fatal: str | None
) -> None:
    stages: dict[str, Any] = {}
    for stage, (validation_path, ledger_path) in STAGE_PATHS.items():
        stages[stage] = {
            "validation": campaign.rel(validation_path)
            if validation_path.exists()
            else None,
            "validation_sha256": campaign.sha256(validation_path)
            if validation_path.exists()
            else None,
            "ledger": campaign.rel(ledger_path) if ledger_path.exists() else None,
            "ledger_sha256": campaign.sha256(ledger_path)
            if ledger_path.exists()
            else None,
        }
    receipts = [
        campaign.load_json(campaign.receipt_path(job))
        for job in plan
        if campaign.receipt_path(job).is_file()
    ]
    missing = [
        job["job_id"] for job in plan if not campaign.receipt_path(job).is_file()
    ]
    status = (
        "FAIL__RECOVERY0003_TRANSPORT_RESOURCE_OR_AUTHORITY"
        if fatal
        else (
            "PASS__VALIDATED_CAMPAIGN_PREFIX"
            if receipts
            else "FAIL__NO_VALIDATED_SHARDS"
        )
    )
    validation = {
        "schema_version": 3,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": status,
        "errors": [fatal] if fatal else [],
        "authority_boundary": "CORRECTED_KEV_MERGEABLE_SCREENING_AND_PARTIAL_PRODUCTION_ONLY",
        "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(AUTHORITY),
        "powerloss_interruption_receipt": campaign.rel(INTERRUPTION_RECEIPT),
        "powerloss_interruption_receipt_sha256": campaign.sha256(
            INTERRUPTION_RECEIPT
        ),
        "stages": stages,
        "validated_jobs": len(receipts),
        "validated_events": sum(int(row["job"]["events"]) for row in receipts),
        "missing_jobs": missing,
        "campaign_bytes": campaign.campaign_bytes(),
        "actual": {
            "wall_s": math.fsum(float(row["wall_s"]) for row in receipts),
            "beam_on_cpu_s": math.fsum(
                float(row["log"].get("beam_on_cpu_s") or 0) for row in receipts
            ),
            "TT_s": math.fsum(
                float(row["isotope_dat"]["TT_s"]) for row in receipts
            ),
            "RP_count": sum(
                int(row["isotope_dat"]["RP_record_count"]) for row in receipts
            ),
            "peak_process_group_rss_bytes": max(
                (int(row["peak_process_group_rss_bytes"]) for row in receipts),
                default=0,
            ),
        },
    }
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    ledger = {
        "schema_version": 3,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": status,
        "validation": campaign.rel(FINAL_VALIDATION),
        "validation_sha256": campaign.sha256(FINAL_VALIDATION),
        "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(AUTHORITY),
        "stages": stages,
        "selected_receipts": [
            {
                "path": campaign.rel(campaign.receipt_path(row["job"])),
                "sha256": campaign.sha256(campaign.receipt_path(row["job"])),
            }
            for row in receipts
        ],
        "missing_jobs": missing,
        "errors": validation["errors"],
    }
    campaign.atomic_write_once_json(FINAL_LEDGER, ledger)
    campaign.atomic_write_once_json(
        FINAL_UMBRELLA,
        {
            "schema_version": 3,
            "batch_id": campaign.BATCH_ID,
            "recovery_id": RECOVERY_ID,
            "status": status,
            "errors": validation["errors"],
            "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
            "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
            "recovery_authority": campaign.rel(AUTHORITY),
            "recovery_authority_sha256": campaign.sha256(AUTHORITY),
            "seed_registry": campaign.rel(campaign.SEED_REGISTRY),
            "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
            "final_validation": campaign.rel(FINAL_VALIDATION),
            "final_validation_sha256": campaign.sha256(FINAL_VALIDATION),
            "final_ledger": campaign.rel(FINAL_LEDGER),
            "final_ledger_sha256": campaign.sha256(FINAL_LEDGER),
            "authority_exclusions": [
                "full eight-family delayed response",
                "mission sensitivity",
                "geometry promotion",
                "strict proton r1 convergence",
            ],
        },
    )


def run_campaign(
    plan: list[dict[str, Any]], contract: dict[str, Any], environment: dict[str, str]
) -> int:
    fatal: str | None = None
    try:
        validation10, _ledger10 = run_parallel_stage(
            "stage10_seven_family", plan, contract, environment
        )
        if validation10.get("errors"):
            raise RuntimeError(
                "Stage10 failed: "
                + "; ".join(str(value) for value in validation10["errors"][:10])
            )
        validation20, _ledger20 = run_parallel_stage(
            "stage20_proton", plan, contract, environment
        )
        if validation20.get("errors"):
            raise RuntimeError(
                "Stage20 failed: "
                + "; ".join(str(value) for value in validation20["errors"][:10])
            )
    except Exception as exc:
        fatal = str(exc)
    finally:
        publish_final(plan, contract, fatal)
        completed = sum(campaign.receipt_path(job).is_file() for job in plan)
        campaign.update_state(
            contract,
            status=(
                "FINALIZED_RECOVERY0003"
                if fatal is None
                else "FINALIZED_RECOVERY0003_WITH_ERROR"
            ),
            stage="final",
            completed_jobs=completed,
            last_error=fatal,
        )
    if fatal:
        raise SystemExit(fatal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--publish-authority-only", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    contract, plan = frozen_inputs()
    authority = load_or_publish_authority(contract, plan, publish=False)
    if args.print_recovery_plan:
        print(
            json.dumps(
                {
                    "status": "PASS__READ_ONLY_RECOVERY0003_PLAN",
                    "global_contract_sha256": authority["global_contract_sha256"],
                    "controller_sha256": authority["controller"]["sha256"],
                    "interrupted_attempts": authority["interrupted_attempts"],
                    "concurrency": authority["concurrency"],
                    "mem_available_bytes": campaign.mem_available_bytes(),
                    "frozen_clock": authority["frozen_clock"],
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.publish_authority_only:
        published = load_or_publish_authority(contract, plan, publish=True)
        print(
            json.dumps(
                {
                    "status": published["status"],
                    "authority": campaign.rel(AUTHORITY),
                    "authority_sha256": campaign.sha256(AUTHORITY),
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, coordinator_signal)
        authority = load_or_publish_authority(contract, plan, publish=True)
        archive_powerloss_attempts(authority, plan)
        configure_runtime()
        validate_existing_receipts(plan)
        loaded_contract, environment = campaign.create_or_load(
            plan, args.cosima.resolve(), datetime.now(timezone.utc)
        )
        campaign.update_state(
            loaded_contract,
            status="RUNNING__RECOVERY0003__POWERLOSS_RECOVERED__CONCURRENT",
            stage="stage10_seven_family",
            completed_jobs=sum(campaign.receipt_path(job).is_file() for job in plan),
        )
        return run_campaign(plan, loaded_contract, environment)
    finally:
        for worker in list(_ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                os.kill(worker.process.pid, signal.SIGTERM)
                worker.process.join(timeout=30)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
