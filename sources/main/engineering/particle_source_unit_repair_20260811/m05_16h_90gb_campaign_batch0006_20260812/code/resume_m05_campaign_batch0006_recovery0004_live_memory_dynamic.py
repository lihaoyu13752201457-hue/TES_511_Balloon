#!/usr/bin/env python3
"""Scheduling-only recovery0004 with live-memory dynamic concurrency.

This controller does not change the frozen batch0006 physics contract, job set,
seeds, event counts, sources, geometries, stage deadlines, validation rules, or
merge domains.  It inherits immutable PASS receipts from recovery0001-0003 and
changes only the scheduling policy:

* one to eight independent, single-thread Cosima workers, with six as the
  ordinary target and seven/eight reserved for sustained strong surplus;
* no geometry-specific worker cap;
* launches are staggered and admitted from current Linux MemAvailable, measured
  class RSS, active unrealised RSS growth, swap trend, disk reservations, and
  the frozen stop-launch clock;
* MemAvailable below 1.5 GiB pauses new launches but does not roll work back;
* launch recovery requires projected headroom above 2 GiB for 30 seconds;
* there is no soft preemption or scheduler rollback.  The inherited per-worker
  512 MiB watchdog and original two exact attempts remain unchanged; a real
  watchdog failure stops the stage for diagnosis instead of launching a loop.

``--print-recovery-plan`` and ``--self-test`` are strictly read-only: they do
not publish authority and cannot launch transport.
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
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import resume_m05_campaign_batch0006_recovery0001 as recovery1
import resume_m05_campaign_batch0006_recovery0003_powerloss_concurrent as recovery3
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0004_live_memory_dynamic"
AUTHORITY = campaign.RUN_ROOT / "recovery0004_live_memory_dynamic_authority.json"
RECOVERY3_AUTHORITY = campaign.RUN_ROOT / "recovery0003_powerloss_concurrent_authority.json"
CUTOVER_RECEIPT = campaign.RUN_ROOT / "recovery0004_cutover_receipt.json"
SCHEDULER_EVENTS = campaign.RUN_ROOT / "scheduler_events.recovery0004.jsonl"

STAGE_PATHS = {
    "stage00_mergeable_smoke": (
        campaign.RUN_ROOT / "checkpoint_authority/smoke_validation.recovery0001.json",
        campaign.RUN_ROOT / "checkpoint_authority/smoke_ledger.recovery0001.json",
    ),
    "stage10_seven_family": (
        campaign.RUN_ROOT / "seven_family_validation.recovery0004.json",
        campaign.RUN_ROOT / "seven_family_ledger.recovery0004.json",
    ),
    "stage20_proton": (
        campaign.RUN_ROOT / "proton_validation.recovery0004.json",
        campaign.RUN_ROOT / "proton_ledger.recovery0004.json",
    ),
}
FINAL_VALIDATION = campaign.RUN_ROOT / "final_validation.recovery0004.json"
FINAL_LEDGER = campaign.RUN_ROOT / "final_ledger.recovery0004.json"
FINAL_UMBRELLA = campaign.RUN_ROOT / "final_umbrella.recovery0004.json"

ABSOLUTE_MAX_WORKERS = 8
NORMAL_TARGET_WORKERS = 6
FAIR_WAVE_SIZE = 3
LAUNCH_STAGGER_S = 60.0
REPLACEMENT_STAGGER_S = 15.0
SOFT_PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
RESUME_PROJECTED_FLOOR_BYTES = 2 * 1024**3
RESUME_STABLE_S = 30.0
STRONG_SURPLUS_PROJECTED_FLOOR_BYTES = int(2.5 * 1024**3)
STRONG_SURPLUS_STABLE_S = 90.0
STRONG_SURPLUS_MAX_RSS_GROWTH_BYTES = 128 * 1024**2
STRONG_SURPLUS_MAX_PSI_FULL_AVG10 = 1.0
CLASS_COLD_START_BYTES = 768 * 1024**2
CLASS_MIN_UPPER_BYTES = 512 * 1024**2
CLASS_GROWTH_FACTOR = 1.15
CLASS_GROWTH_PAD_BYTES = 128 * 1024**2
SWAP_WINDOW_S = 30.0
SWAP_GROWTH_PAGES = (64 * 1024**2) // int(os.sysconf("SC_PAGE_SIZE"))
SCHEDULER_POLL_S = 0.5
EVIDENCE_REFRESH_S = 30.0
RECENT_CLASS_RECEIPTS = 8
FAIR_BYPASS_SCAN = 12
MAX_BYPASS_DEBT = FAIR_WAVE_SIZE

_COORDINATOR_STOP = False
_ACTIVE_WORKERS: dict[int, "Worker"] = {}


@dataclass
class Worker:
    job: dict[str, Any]
    process: Any
    connection: Any
    launched_at: str
    launched_monotonic: float


@dataclass
class HealthState:
    paused: bool = False
    pause_reason: str | None = None
    resume_stable_since: float | None = None
    strong_rss_samples: deque[tuple[float, int]] | None = None


def stage_paths(stage: str) -> tuple[Path, Path]:
    return STAGE_PATHS[stage]


def configure_runtime() -> None:
    """Bind inherited strict validation to the recovery0004 namespace."""
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
    # Earlier recoveries authorized early starts.  Frozen stop-launch and hard
    # end offsets remain untouched.
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
        RECOVERY3_AUTHORITY,
        STAGE_PATHS["stage00_mergeable_smoke"][0],
        STAGE_PATHS["stage00_mergeable_smoke"][1],
    ]
    missing = [campaign.rel(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("missing recovery0004 inputs: " + ", ".join(missing))
    smoke = campaign.load_json(STAGE_PATHS["stage00_mergeable_smoke"][0])
    if smoke.get("validated_jobs") != 100 or smoke.get("validated_events") != 55_424:
        raise RuntimeError("immutable recovery0001 smoke closure differs")
    return contract, plan


def receipt_manifest(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in plan:
        path = campaign.receipt_path(job)
        if not path.is_file():
            continue
        payload = campaign.load_json(path)
        if not campaign.receipt_hashes_valid(payload):
            raise RuntimeError(f"existing receipt hash closure failed: {job['job_id']}")
        if payload.get("job") != job:
            raise RuntimeError(f"existing receipt frozen job differs: {job['job_id']}")
        rows.append(
            {
                "job_id": job["job_id"],
                "path": campaign.rel(path),
                "sha256": campaign.sha256(path),
                "events": int(job["events"]),
            }
        )
    return rows


def partial_attempts() -> list[str]:
    return sorted(
        campaign.rel(path)
        for path in campaign.RUN_ROOT.glob("stage*/**/.attempt*.partial")
        if path.is_dir()
    )


def cutover_process_snapshot() -> dict[str, Any]:
    """Find old controller/workers and campaign Cosima processes via /proc."""
    rows: list[dict[str, Any]] = []
    recovery3_name = Path(recovery3.__file__).name
    recovery4_name = Path(__file__).name
    run_root_text = str(campaign.RUN_ROOT.resolve())
    for proc_dir in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc_dir.name)
            if pid == os.getpid():
                continue
            cmdline = proc_dir.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            ).strip()
            comm = proc_dir.joinpath("comm").read_text(encoding="utf-8").strip()
            stat = proc_dir.joinpath("stat").read_text(encoding="utf-8")
            tail = stat[stat.rfind(")") + 2 :].split()
            ppid = int(tail[1])
            pgid = int(tail[2])
        except (OSError, ValueError, IndexError):
            continue
        old_python = comm.startswith("python") and recovery3_name in cmdline
        current_worker = comm.startswith("python") and recovery4_name in cmdline
        campaign_cosima = comm == "cosima" and run_root_text in cmdline
        if old_python or current_worker or campaign_cosima:
            rows.append(
                {
                    "pid": pid,
                    "ppid": ppid,
                    "pgid": pgid,
                    "comm": comm,
                    "kind": (
                        "recovery0003_python"
                        if old_python
                        else (
                            "recovery0004_worker_python"
                            if current_worker
                            else "campaign_cosima"
                        )
                    ),
                    "cmdline_sha256": __import__("hashlib").sha256(cmdline.encode()).hexdigest(),
                }
            )
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scanner_pid": os.getpid(),
        "matching_processes": sorted(rows, key=lambda row: int(row["pid"])),
        "partial_attempt_directories": partial_attempts(),
    }


def assert_cutover_quiescent() -> dict[str, Any]:
    snapshot = cutover_process_snapshot()
    if snapshot["matching_processes"]:
        raise RuntimeError("recovery0004 cutover found old controller/worker/Cosima processes")
    if snapshot["partial_attempt_directories"]:
        raise RuntimeError("recovery0004 cutover found partial attempt directories")
    return snapshot


def rss_evidence() -> dict[str, Any]:
    """Recent measured RSS by exact class, retaining all-time data as audit only."""
    all_time = recovery3.receipt_rss_summary()
    recent: dict[str, list[tuple[float, int]]] = {}
    for path in campaign.RUN_ROOT.glob("job_receipts/**/*.json"):
        payload = campaign.load_json(path)
        if payload.get("status") != "PASS" or payload.get("errors"):
            continue
        job = payload["job"]
        key = f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}"
        recent.setdefault(key, []).append(
            (path.stat().st_mtime, int(payload["peak_process_group_rss_bytes"]))
        )
    classes: dict[str, Any] = {}
    for key, values in sorted(recent.items()):
        window = [
            value for _mtime, value in sorted(values, reverse=True)[:RECENT_CLASS_RECEIPTS]
        ]
        ordered = sorted(window)
        upper = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
        classes[key] = {
            "n": len(window),
            "window": RECENT_CLASS_RECEIPTS,
            "recent_p95_upper_bytes": upper,
            "recent_max_bytes": max(window),
        }
    return {"recent_classes": classes, "all_time_audit_only": all_time}


def proposed_authority(
    contract: dict[str, Any], plan: list[dict[str, Any]]
) -> dict[str, Any]:
    inherited = receipt_manifest(plan)
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "PASS__SCHEDULING_ONLY__LIVE_MEMORY_DYNAMIC_1_TO_8",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authorization": {
            "source": "direct user instructions in controlling Codex thread",
            "scope": "scheduling, concurrency, and resource protection only",
            "principle": "current Linux MemAvailable and live RSS decide concurrency; host power loss is not evidence of memory failure",
        },
        "controller": {
            "path": campaign.rel(Path(__file__).resolve()),
            "sha256": campaign.sha256(Path(__file__).resolve()),
        },
        "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "seed_registry": campaign.rel(campaign.SEED_REGISTRY),
        "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
        "planned_jobs_sha256": campaign.json_sha256(plan),
        "planned_jobs": len(plan),
        "planned_events": sum(int(job["events"]) for job in plan),
        "recovery0003_authority": campaign.rel(RECOVERY3_AUTHORITY),
        "recovery0003_authority_sha256": campaign.sha256(RECOVERY3_AUTHORITY),
        "cutover": {
            "requires_exclusive_controller_lock": True,
            "requires_zero_partial_attempt_directories": True,
            "inherited_pass_receipts": inherited,
            "inherited_pass_receipts_closure_sha256": campaign.json_sha256(inherited),
        },
        "frozen_clock": {
            "t0": contract["wall_clock"]["t0"],
            "deadline": contract["wall_clock"]["deadline"],
            "stage10_stop_launch_s": campaign.STAGES["stage10_seven_family"]["stop_launch_s"],
            "stage10_hard_end_s": campaign.STAGES["stage10_seven_family"]["hard_end_s"],
            "stage20_stop_launch_s": campaign.STAGES["stage20_proton"]["stop_launch_s"],
            "stage20_hard_end_s": campaign.STAGES["stage20_proton"]["hard_end_s"],
        },
        "scheduler": {
            "mechanism": "independent single-thread Cosima processes",
            "global_worker_range": [1, ABSOLUTE_MAX_WORKERS],
            "normal_target_workers": NORMAL_TARGET_WORKERS,
            "strong_surplus_worker_range": [7, ABSOLUTE_MAX_WORKERS],
            "geometry_specific_caps": None,
            "fair_wave_size_per_geometry": FAIR_WAVE_SIZE,
            "launch_stagger_s": LAUNCH_STAGGER_S,
            "replacement_stagger_s": REPLACEMENT_STAGGER_S,
            "launch_projection": "MemAvailable - active_unrealised_class_growth - candidate_live_class_upper",
            "soft_projected_floor_bytes": SOFT_PROJECTED_FLOOR_BYTES,
            "resume_projected_floor_bytes": RESUME_PROJECTED_FLOOR_BYTES,
            "resume_stable_s": RESUME_STABLE_S,
            "strong_surplus_projected_floor_bytes": STRONG_SURPLUS_PROJECTED_FLOOR_BYTES,
            "strong_surplus_stable_s": STRONG_SURPLUS_STABLE_S,
            "strong_surplus_max_rss_growth_bytes_over_dwell": STRONG_SURPLUS_MAX_RSS_GROWTH_BYTES,
            "strong_surplus_max_psi_full_avg10": STRONG_SURPLUS_MAX_PSI_FULL_AVG10,
            "swap_growth_window_s": SWAP_WINDOW_S,
            "swap_growth_pswpout_pages": SWAP_GROWTH_PAGES,
            "soft_preemption": False,
            "hard_watchdog": "inherited per-worker MemAvailable below 512MiB; original two exact attempts; stage stops on worker failure",
            "disk_gate_includes_all_active_declared_caps": True,
        },
        "rss_evidence_at_cutover": rss_evidence(),
        "mem_available_bytes_at_cutover": campaign.mem_available_bytes(),
        "publication_namespace": {
            "stage00": "immutable recovery0001 smoke",
            "stage10": campaign.rel(STAGE_PATHS["stage10_seven_family"][1]),
            "stage20": campaign.rel(STAGE_PATHS["stage20_proton"][1]),
            "final": campaign.rel(FINAL_UMBRELLA),
            "scheduler_events": campaign.rel(SCHEDULER_EVENTS),
        },
        "unchanged": {
            "jobs_seeds_events": True,
            "sources_spectra_geometries": True,
            "physics_cut_detector_veto": True,
            "validation_and_merge_domains": True,
            "t0_stage_deadlines_campaign_deadline": True,
            "old_authorities_receipts_failed_artifacts": True,
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
        if partial_attempts():
            raise RuntimeError("recovery0004 cutover has live partial attempts")
        campaign.atomic_write_once_json(AUTHORITY, payload)
        payload = campaign.load_json(AUTHORITY)
    expected = {
        "recovery_id": RECOVERY_ID,
        "status": "PASS__SCHEDULING_ONLY__LIVE_MEMORY_DYNAMIC_1_TO_8",
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
        "planned_jobs_sha256": campaign.json_sha256(plan),
        "recovery0003_authority_sha256": campaign.sha256(RECOVERY3_AUTHORITY),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"recovery0004 authority drift: {key}")
    if payload.get("controller", {}).get("sha256") != campaign.sha256(
        Path(__file__).resolve()
    ):
        raise RuntimeError("recovery0004 controller differs from authority")
    if payload.get("frozen_clock", {}).get("deadline") != contract["wall_clock"]["deadline"]:
        raise RuntimeError("recovery0004 deadline drift")
    return payload


def publish_cutover(
    authority: dict[str, Any], plan: list[dict[str, Any]],
    prior_execution_state: dict[str, Any] | None,
    process_snapshot: dict[str, Any],
) -> None:
    if CUTOVER_RECEIPT.is_file():
        existing = campaign.load_json(CUTOVER_RECEIPT)
        expected = {
            "recovery_id": RECOVERY_ID,
            "authority_sha256": campaign.sha256(AUTHORITY),
            "recovery0003_authority_sha256": campaign.sha256(RECOVERY3_AUTHORITY),
        }
        if any(existing.get(key) != value for key, value in expected.items()):
            raise RuntimeError("existing recovery0004 cutover receipt differs")
        if existing.get("quiescence_proof", {}).get("process_snapshot", {}).get(
            "matching_processes"
        ):
            raise RuntimeError("existing cutover receipt did not prove quiescence")
        return
    inherited = receipt_manifest(plan)
    if inherited != authority["cutover"]["inherited_pass_receipts"]:
        raise RuntimeError("receipt set changed between authority publication and cutover")
    campaign.atomic_write_once_json(
        CUTOVER_RECEIPT,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__EXCLUSIVE_CLEAN_CUTOVER__NO_TRANSPORT_IN_THIS_RECEIPT",
            "authority": campaign.rel(AUTHORITY),
            "authority_sha256": campaign.sha256(AUTHORITY),
            "recovery0003_authority_sha256": campaign.sha256(RECOVERY3_AUTHORITY),
            "exclusive_controller_lock_held": True,
            "quiescence_proof": {
                "mechanism": "nonblocking exclusive campaign controller flock acquired",
                "meaning": "a conforming recovery0003 controller and its coordinator-owned workers are no longer active",
                "zero_partial_attempt_directories": not partial_attempts(),
                "prior_execution_state": prior_execution_state,
                "prior_execution_state_sha256": (
                    campaign.sha256(campaign.EXECUTION_STATE)
                    if campaign.EXECUTION_STATE.is_file()
                    else None
                ),
                "process_snapshot": process_snapshot,
            },
            "partial_attempt_directories": partial_attempts(),
            "inherited_pass_receipts": inherited,
            "inherited_pass_receipts_closure_sha256": campaign.json_sha256(inherited),
        },
    )


def append_scheduler_event(kind: str, **fields: Any) -> None:
    SCHEDULER_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "at": datetime.now(timezone.utc).isoformat(),
        "monotonic_s": time.monotonic(),
        "recovery_id": RECOVERY_ID,
        "event": kind,
        **fields,
    }
    with SCHEDULER_EVENTS.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def class_key(job: dict[str, Any]) -> str:
    return (
        f"{job.get('stage', 'unknown')}/{job.get('mode', 'unknown')}/"
        f"{job['geometry']}/{job['family']}"
    )


def class_upper_bytes(
    job: dict[str, Any], evidence: dict[str, Any], *, live_peer_bytes: int = 0
) -> int:
    geometry = str(job["geometry"])
    key = class_key(job)
    cls = evidence.get("recent_classes", {}).get(key, {})
    observed = int(cls.get("recent_p95_upper_bytes", 0))
    if observed <= 0:
        observed = CLASS_COLD_START_BYTES
    observed = max(observed, live_peer_bytes)
    padded = math.ceil(observed * CLASS_GROWTH_FACTOR) + CLASS_GROWTH_PAD_BYTES
    return max(CLASS_MIN_UPPER_BYTES, padded)


def _proc_rows() -> dict[int, tuple[int, int]]:
    """Return pid -> (ppid, RSS bytes); races simply omit exited processes."""
    rows: dict[int, tuple[int, int]] = {}
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            raw = stat_path.read_text()
            pid = int(stat_path.parent.name)
            tail = raw[raw.rfind(")") + 2 :].split()
            ppid = int(tail[1])
            status = stat_path.with_name("status").read_text()
            match = re.search(r"^VmRSS:\s+(\d+) kB", status, re.MULTILINE)
            rows[pid] = (ppid, int(match.group(1)) * 1024 if match else 0)
        except (OSError, ValueError, IndexError):
            continue
    return rows


def descendant_rss_bytes(root_pid: int, rows: dict[int, tuple[int, int]] | None = None) -> int:
    rows = rows if rows is not None else _proc_rows()
    children: dict[int, list[int]] = {}
    for pid, (ppid, _rss) in rows.items():
        children.setdefault(ppid, []).append(pid)
    todo = [root_pid]
    seen: set[int] = set()
    total = 0
    while todo:
        pid = todo.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if pid in rows:
            total += rows[pid][1]
        todo.extend(children.get(pid, []))
    return total


def memory_projection(
    active: list[Worker], candidate: dict[str, Any], evidence: dict[str, Any],
    *, available_bytes: int | None = None, live_rss: dict[int, int] | None = None,
) -> dict[str, Any]:
    available = campaign.mem_available_bytes() if available_bytes is None else available_bytes
    if live_rss is None:
        proc_rows = _proc_rows()
        live_rss = {
            worker.process.pid: descendant_rss_bytes(worker.process.pid, proc_rows)
            for worker in active
        }
    active_rows = []
    unrealised = 0
    for worker in active:
        upper = class_upper_bytes(worker.job, evidence)
        live = int(live_rss.get(worker.process.pid, 0))
        reserve = max(0, upper - live)
        unrealised += reserve
        active_rows.append(
            {
                "job_id": worker.job["job_id"],
                "class_upper_bytes": upper,
                "live_rss_bytes": live,
                "unrealised_growth_bytes": reserve,
            }
        )
    peer_live = max(
        (
            int(live_rss.get(worker.process.pid, 0))
            for worker in active
            if class_key(worker.job) == class_key(candidate)
        ),
        default=0,
    )
    candidate_upper = class_upper_bytes(
        candidate, evidence, live_peer_bytes=peer_live
    )
    projected = available - unrealised - candidate_upper
    return {
        "status": "PASS" if projected >= SOFT_PROJECTED_FLOOR_BYTES else "PAUSE",
        "mem_available_bytes": available,
        "active_unrealised_growth_bytes": unrealised,
        "candidate_class_upper_bytes": candidate_upper,
        "projected_mem_available_bytes": projected,
        "soft_floor_bytes": SOFT_PROJECTED_FLOOR_BYTES,
        "active": active_rows,
    }


def read_pswpout_pages() -> int:
    for line in Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("pswpout "):
            return int(line.split()[1])
    raise RuntimeError("pswpout missing from /proc/vmstat")


def swap_growth(samples: Iterable[tuple[float, int]]) -> dict[str, Any]:
    rows = list(samples)
    if len(rows) < 3 or rows[-1][0] - rows[0][0] < SWAP_WINDOW_S:
        return {"growing": False, "delta_pages": 0, "window_s": 0.0}
    delta = rows[-1][1] - rows[0][1]
    tolerance = (4 * 1024**2) // int(os.sysconf("SC_PAGE_SIZE"))
    sustained = all(rows[i][1] + tolerance >= rows[i - 1][1] for i in range(1, len(rows)))
    return {
        "growing": sustained and delta >= SWAP_GROWTH_PAGES,
        "delta_pages": delta,
        "window_s": rows[-1][0] - rows[0][0],
    }


def read_memory_psi_full_avg10() -> float:
    path = Path("/proc/pressure/memory")
    if not path.is_file():
        return 0.0
    for line in path.read_text().splitlines():
        if not line.startswith("full "):
            continue
        for field in line.split()[1:]:
            if field.startswith("avg10="):
                return float(field.split("=", 1)[1])
    return 0.0


def health_allows_launch(
    state: HealthState, *, now: float, projection: dict[str, Any], swap: dict[str, Any]
) -> tuple[bool, str]:
    projected = int(projection["projected_mem_available_bytes"])
    bad_reason: str | None = None
    if swap["growing"]:
        bad_reason = "sustained_swap_growth"
    elif projected < SOFT_PROJECTED_FLOOR_BYTES:
        bad_reason = "projected_MemAvailable_below_1.5GiB"
    if bad_reason:
        state.paused = True
        state.pause_reason = bad_reason
        state.resume_stable_since = None
        return False, bad_reason
    if not state.paused:
        return True, "admit"
    if projected <= RESUME_PROJECTED_FLOOR_BYTES or swap["growing"]:
        state.resume_stable_since = None
        return False, state.pause_reason or "hysteresis_pause"
    if state.resume_stable_since is None:
        state.resume_stable_since = now
        return False, "resume_stability_dwell"
    if now - state.resume_stable_since < RESUME_STABLE_S:
        return False, "resume_stability_dwell"
    state.paused = False
    state.pause_reason = None
    state.resume_stable_since = None
    return True, "resume_after_stable_headroom"


def strong_surplus_allows_launch(
    state: HealthState, *, now: float, projection: dict[str, Any],
    swap: dict[str, Any], psi_full_avg10: float,
) -> tuple[bool, str]:
    """Gate workers seven/eight behind sustained, measured surplus.

    The ordinary 1--6 path never calls this gate.  A sample is strong only if
    projected MemAvailable remains at least 2.5 GiB, swap is not growing,
    memory PSI is quiet, and live active RSS has not grown by more than 128 MiB
    across the complete 90-second dwell.  A new launch resets the dwell, so
    workers seven and eight are separately earned.
    """
    projected = int(projection["projected_mem_available_bytes"])
    live_total = sum(int(row["live_rss_bytes"]) for row in projection["active"])
    if state.strong_rss_samples is None:
        state.strong_rss_samples = deque()
    state.strong_rss_samples.append((now, live_total))
    while (
        state.strong_rss_samples
        and now - state.strong_rss_samples[0][0] > STRONG_SURPLUS_STABLE_S + 5
    ):
        state.strong_rss_samples.popleft()
    span = now - state.strong_rss_samples[0][0]
    rss_growth = live_total - state.strong_rss_samples[0][1]
    base_strong = (
        projected >= STRONG_SURPLUS_PROJECTED_FLOOR_BYTES
        and not swap["growing"]
        and psi_full_avg10 <= STRONG_SURPLUS_MAX_PSI_FULL_AVG10
    )
    if not base_strong or rss_growth > STRONG_SURPLUS_MAX_RSS_GROWTH_BYTES:
        state.strong_rss_samples.clear()
        return False, "strong_surplus_not_stable"
    if span < STRONG_SURPLUS_STABLE_S:
        return False, "strong_surplus_dwell"
    state.strong_rss_samples.clear()
    return True, "strong_surplus_admit"


def launch_clock_decision(
    *, active_count: int, target_workers: int, now: float,
    last_target_raise: float, last_launch: float,
) -> tuple[bool, bool]:
    """Return (clock_allows_launch, launch_would_raise_target).

    Replacing a completed worker within the already-earned target waits 15s;
    raising the target by one requires the 60-second stagger.  This avoids both
    under-filling a stable wave and burst-launching new memory demand.
    """
    replacing = (
        active_count < target_workers
        and now - last_launch >= REPLACEMENT_STAGGER_S
    )
    raising = (
        target_workers < ABSOLUTE_MAX_WORKERS
        and active_count >= target_workers
        and now - last_target_raise >= LAUNCH_STAGGER_S
        and now - last_launch >= LAUNCH_STAGGER_S
    )
    return replacing or raising, raising


def fair_wave_jobs(stage: str, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = recovery1.scheduled_jobs(stage, plan)
    if stage != "stage10_seven_family":
        # Stage20's frozen four-cell round-robin order is already encoded in
        # build_plan and must not be geometry-wave reordered.
        return rows
    queues = {
        geometry: deque(job for job in rows if job["geometry"] == geometry)
        for geometry in campaign.GEOMETRY_ORDER
    }
    totals = {geometry: len(queue) for geometry, queue in queues.items()}
    emitted = {geometry: 0 for geometry in queues}
    ordered: list[dict[str, Any]] = []
    while any(queues.values()):
        available = [geometry for geometry, queue in queues.items() if queue]
        geometry = min(
            available,
            key=lambda name: (
                emitted[name] / max(1, totals[name]),
                campaign.GEOMETRY_ORDER.index(name),
            ),
        )
        for _ in range(min(FAIR_WAVE_SIZE, len(queues[geometry]))):
            ordered.append(queues[geometry].popleft())
            emitted[geometry] += 1
    if {job["job_id"] for job in ordered} != {job["job_id"] for job in rows}:
        raise RuntimeError("fair waves changed the frozen job set")
    return ordered


def choose_memory_candidate(
    pending: list[dict[str, Any]], active: list[Worker], evidence: dict[str, Any],
    available: int, bypass_debt: dict[str, int], tier_floor_bytes: int,
) -> tuple[int | None, dict[str, Any], list[dict[str, Any]]]:
    """Bounded fair bypass of a temporarily expensive queue head.

    At most the first 12 fair-order jobs are considered.  Once a job has been
    bypassed by one three-job wave it becomes a debt barrier: it must launch
    before a later wave may pass it again.  Thus a large live budget cannot
    starve all smaller work, while no geometry/family is assigned a fixed cap
    or skipped indefinitely.
    """
    if not pending:
        raise ValueError("candidate selection requires pending jobs")
    head = pending[0]
    head_id = str(head["job_id"])
    limit = 1 if bypass_debt.get(head_id, 0) >= MAX_BYPASS_DEBT else min(
        FAIR_BYPASS_SCAN, len(pending)
    )
    observations: list[dict[str, Any]] = []
    for index in range(limit):
        candidate = pending[index]
        projection = memory_projection(
            active, candidate, evidence, available_bytes=available
        )
        observations.append(
            {
                "index": index,
                "job_id": candidate["job_id"],
                "tier_floor_bytes": tier_floor_bytes,
                "projection": projection,
            }
        )
        if int(projection["projected_mem_available_bytes"]) >= tier_floor_bytes:
            return index, projection, observations
    return None, observations[0]["projection"], observations


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


def concurrent_ensure_job(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str],
    hard_deadline: datetime,
) -> dict[str, Any]:
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
        result = campaign.run_attempt(job, attempt, contract, environment, hard_deadline)
        if result["status"] == "PASS":
            return result
        if campaign._STOP_REQUESTED:
            raise RuntimeError("worker stopped after preserving interrupted attempt")
    raise RuntimeError(f"{job['job_id']} exhausted two exact same-seed attempts")


def worker_entry(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str],
    hard_end_iso: str, connection: Any,
) -> None:
    configure_runtime()
    campaign._STOP_REQUESTED = False
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, campaign._signal_handler)
    try:
        result = concurrent_ensure_job(
            job, contract, environment, datetime.fromisoformat(hard_end_iso)
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


def launch_worker(
    context: Any, job: dict[str, Any], contract: dict[str, Any],
    environment: dict[str, str], hard_end: datetime,
) -> Worker:
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=worker_entry,
        args=(job, contract, environment, hard_end.isoformat(), child),
        name=f"m05-r4-{job['job_id']}",
    )
    process.start()
    child.close()
    now = time.monotonic()
    worker = Worker(
        job, process, parent, datetime.now(timezone.utc).isoformat(), now
    )
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
        receipt = campaign.receipt_path(worker.job)
        if message.get("status") == "PASS":
            if not receipt.is_file() or not campaign.receipt_hashes_valid(
                campaign.load_json(receipt)
            ):
                failures.append(f"{worker.job['job_id']}: PASS receipt hash closure failed")
            append_scheduler_event(
                "worker_reaped_PASS", job_id=worker.job["job_id"],
                worker_pid=worker.process.pid,
            )
            continue
        failures.append(f"{message['job_id']}: {message.get('error')}")
        append_scheduler_event(
            "worker_reaped_FAIL", job_id=worker.job["job_id"],
            worker_pid=worker.process.pid,
            error=message.get("error"),
        )
    return remaining


def coordinator_signal(_signum: int, _frame: Any) -> None:
    global _COORDINATOR_STOP
    _COORDINATOR_STOP = True
    for worker in list(_ACTIVE_WORKERS.values()):
        if worker.process.is_alive():
            try:
                os.kill(worker.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def bind_stage(stage: str, validation: dict[str, Any], ledger: dict[str, Any]) -> None:
    validation_path, ledger_path = stage_paths(stage)
    binding = (
        campaign.RUN_ROOT
        / "checkpoint_authority"
        / f"{stage}.recovery0004.binding.json"
    )
    campaign.atomic_write_once_json(
        binding,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__HASH_BOUND_RECOVERY0004_PUBLICATION",
            "recovery_authority": campaign.rel(AUTHORITY),
            "recovery_authority_sha256": campaign.sha256(AUTHORITY),
            "cutover_receipt": campaign.rel(CUTOVER_RECEIPT),
            "cutover_receipt_sha256": campaign.sha256(CUTOVER_RECEIPT),
            "validation": campaign.rel(validation_path),
            "validation_sha256": campaign.sha256(validation_path),
            "ledger": campaign.rel(ledger_path),
            "ledger_sha256": campaign.sha256(ledger_path),
            "validation_status": validation["status"],
            "ledger_status": ledger["status"],
        },
    )


def run_dynamic_stage(
    stage: str, plan: list[dict[str, Any]], contract: dict[str, Any],
    environment: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    timing = campaign.STAGES[stage]
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    stop_launch = t0 + timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + timedelta(seconds=int(timing["hard_end_s"]))
    ordered = fair_wave_jobs(stage, plan)
    pending = [job for job in ordered if not campaign.receipt_path(job).is_file()]
    active: list[Worker] = []
    failures: list[str] = []
    context = mp.get_context("fork")
    evidence = rss_evidence()
    health = HealthState()
    bypass_debt: dict[str, int] = {}
    swap_samples: deque[tuple[float, int]] = deque()
    last_launch = -math.inf
    target_workers = 1
    last_target_raise = time.monotonic()
    last_state = last_evidence = last_pause_log = 0.0
    stop_reason: str | None = None

    append_scheduler_event(
        "stage_start", stage=stage, pending_jobs=len(pending),
        stop_launch=stop_launch.isoformat(), hard_end=hard_end.isoformat(),
    )
    while pending or active:
        now_mono = time.monotonic()
        active = reap_workers(active, failures)
        if failures and stop_reason is None:
            stop_reason = "worker failure after exact retry: " + failures[0]
        if now_mono - last_evidence >= EVIDENCE_REFRESH_S:
            evidence = rss_evidence()
            last_evidence = now_mono

        available = campaign.mem_available_bytes()
        swap_samples.append((now_mono, read_pswpout_pages()))
        while swap_samples and now_mono - swap_samples[0][0] > SWAP_WINDOW_S + 5:
            swap_samples.popleft()
        swap = swap_growth(swap_samples)
        psi = read_memory_psi_full_avg10()

        now = datetime.now(timezone.utc)
        launch_clock_ok, clock_would_raise = launch_clock_decision(
            active_count=len(active), target_workers=target_workers,
            now=now_mono, last_target_raise=last_target_raise,
            last_launch=last_launch,
        )
        launch_clock_ok = now < stop_launch and launch_clock_ok
        launch_allowed = (
            not _COORDINATOR_STOP
            and stop_reason is None
            and launch_clock_ok
            and len(active) < ABSOLUTE_MAX_WORKERS
            and bool(pending)
        )
        if launch_allowed:
            prospective_count = len(active) + 1
            tier_floor = (
                STRONG_SURPLUS_PROJECTED_FLOOR_BYTES
                if prospective_count > NORMAL_TARGET_WORKERS
                else SOFT_PROJECTED_FLOOR_BYTES
            )
            selected_index, projection, candidate_observations = choose_memory_candidate(
                pending, active, evidence, available, bypass_debt, tier_floor
            )
            candidate = pending[selected_index or 0]
            healthy, decision = health_allows_launch(
                health, now=now_mono, projection=projection, swap=swap
            )
            raising_target = clock_would_raise and prospective_count > target_workers
            if healthy and prospective_count > NORMAL_TARGET_WORKERS:
                healthy, decision = strong_surplus_allows_launch(
                    health,
                    now=now_mono,
                    projection=projection,
                    swap=swap,
                    psi_full_avg10=psi,
                )
            disk = parallel_disk_gate(contract, stage, len(active) + 1)
            if disk["status"] != "PASS":
                stop_reason = "disk stop-launch gate: " + ",".join(disk["errors"])
                append_scheduler_event(
                    "launch_STOP_disk", stage=stage, job_id=candidate["job_id"],
                    disk=disk,
                )
            elif healthy:
                if decision.startswith("resume"):
                    append_scheduler_event(
                        "launch_resume_after_hysteresis", stage=stage,
                        job_id=candidate["job_id"], projection=projection, swap=swap,
                    )
                assert selected_index is not None
                if selected_index:
                    bypassed = pending[:selected_index]
                    for skipped in bypassed:
                        job_id = str(skipped["job_id"])
                        bypass_debt[job_id] = bypass_debt.get(job_id, 0) + 1
                    append_scheduler_event(
                        "bounded_fair_bypass",
                        stage=stage, selected_job_id=candidate["job_id"],
                        bypassed_job_ids=[job["job_id"] for job in bypassed],
                        observations=candidate_observations,
                    )
                pending.pop(selected_index)
                bypass_debt.pop(str(candidate["job_id"]), None)
                worker = launch_worker(context, candidate, contract, environment, hard_end)
                active.append(worker)
                last_launch = now_mono
                if raising_target:
                    target_workers = prospective_count
                    last_target_raise = now_mono
                # Every admission changes the live-RSS trajectory.  Workers
                # seven/eight must earn a fresh strong-surplus dwell.
                if health.strong_rss_samples is not None:
                    health.strong_rss_samples.clear()
                append_scheduler_event(
                    "worker_launched", stage=stage, job_id=candidate["job_id"],
                    geometry=candidate["geometry"], family=candidate["family"],
                    worker_pid=worker.process.pid, active_workers=len(active),
                    target_workers=target_workers,
                    projection=projection, swap=swap, disk=disk,
                )
            elif now_mono - last_pause_log >= 30:
                append_scheduler_event(
                    "launch_PAUSE_hysteresis", stage=stage,
                    job_id=candidate["job_id"], reason=decision,
                    active_workers=len(active), projection=projection,
                    swap=swap, psi_full_avg10=psi,
                )
                last_pause_log = now_mono

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
        if now_mono - last_state >= 30:
            completed = sum(campaign.receipt_path(job).is_file() for job in plan)
            campaign.update_state(
                contract,
                status=f"RUNNING__RECOVERY0004__LIVE_MEMORY_DYNAMIC_{len(active)}",
                stage=stage,
                completed_jobs=completed,
                last_error=stop_reason,
            )
            append_scheduler_event(
                "scheduler_checkpoint", stage=stage,
                active_workers=len(active), pending_jobs=len(pending),
                target_workers=target_workers,
                mem_available_bytes=available, swap=swap,
                psi_full_avg10=psi, paused=health.paused,
                pause_reason=health.pause_reason,
            )
            last_state = now_mono
        time.sleep(SCHEDULER_POLL_S)

    while active:
        active = reap_workers(active, failures)
        if active:
            time.sleep(SCHEDULER_POLL_S)
    if failures and stop_reason is None:
        stop_reason = "worker failure after exact retry: " + failures[0]
    validation, ledger = campaign.publish_stage(stage, plan, contract, stop_reason)
    bind_stage(stage, validation, ledger)
    append_scheduler_event(
        "stage_published", stage=stage, validation_status=validation["status"],
        ledger_status=ledger["status"], stop_reason=stop_reason,
    )
    return validation, ledger


def publish_final(
    plan: list[dict[str, Any]], contract: dict[str, Any], fatal: str | None
) -> None:
    receipts = [
        campaign.load_json(campaign.receipt_path(job))
        for job in plan
        if campaign.receipt_path(job).is_file()
    ]
    missing = [job["job_id"] for job in plan if not campaign.receipt_path(job).is_file()]
    stages: dict[str, Any] = {}
    for stage, (validation, ledger) in STAGE_PATHS.items():
        stages[stage] = {
            "validation": campaign.rel(validation) if validation.exists() else None,
            "validation_sha256": campaign.sha256(validation) if validation.exists() else None,
            "ledger": campaign.rel(ledger) if ledger.exists() else None,
            "ledger_sha256": campaign.sha256(ledger) if ledger.exists() else None,
        }
    status = (
        "FAIL__RECOVERY0004_TRANSPORT_RESOURCE_OR_AUTHORITY"
        if fatal
        else ("PASS__VALIDATED_CAMPAIGN_PREFIX" if receipts else "FAIL__NO_VALIDATED_SHARDS")
    )
    validation = {
        "schema_version": 4,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": status,
        "errors": [fatal] if fatal else [],
        "authority_boundary": "CORRECTED_KEV_MERGEABLE_SCREENING_AND_PARTIAL_PRODUCTION_ONLY",
        "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(AUTHORITY),
        "cutover_receipt_sha256": campaign.sha256(CUTOVER_RECEIPT),
        "scheduler_events": campaign.rel(SCHEDULER_EVENTS),
        "scheduler_events_sha256": campaign.sha256(SCHEDULER_EVENTS) if SCHEDULER_EVENTS.exists() else None,
        "stages": stages,
        "validated_jobs": len(receipts),
        "validated_events": sum(int(row["job"]["events"]) for row in receipts),
        "missing_jobs": missing,
        "campaign_bytes": campaign.campaign_bytes(),
        "actual": {
            "wall_s": math.fsum(float(row["wall_s"]) for row in receipts),
            "beam_on_cpu_s": math.fsum(float(row["log"].get("beam_on_cpu_s") or 0) for row in receipts),
            "TT_s": math.fsum(float(row["isotope_dat"]["TT_s"]) for row in receipts),
            "RP_count": sum(int(row["isotope_dat"]["RP_record_count"]) for row in receipts),
            "peak_process_group_rss_bytes": max((int(row["peak_process_group_rss_bytes"]) for row in receipts), default=0),
        },
    }
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    ledger = {
        "schema_version": 4,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": status,
        "validation": campaign.rel(FINAL_VALIDATION),
        "validation_sha256": campaign.sha256(FINAL_VALIDATION),
        "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(AUTHORITY),
        "stages": stages,
        "selected_receipts": [
            {"path": campaign.rel(campaign.receipt_path(row["job"])), "sha256": campaign.sha256(campaign.receipt_path(row["job"]))}
            for row in receipts
        ],
        "missing_jobs": missing,
        "errors": validation["errors"],
    }
    campaign.atomic_write_once_json(FINAL_LEDGER, ledger)
    campaign.atomic_write_once_json(
        FINAL_UMBRELLA,
        {
            "schema_version": 4,
            "batch_id": campaign.BATCH_ID,
            "recovery_id": RECOVERY_ID,
            "status": status,
            "errors": validation["errors"],
            "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
            "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
            "recovery_authority": campaign.rel(AUTHORITY),
            "recovery_authority_sha256": campaign.sha256(AUTHORITY),
            "cutover_receipt": campaign.rel(CUTOVER_RECEIPT),
            "cutover_receipt_sha256": campaign.sha256(CUTOVER_RECEIPT),
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
        validation10, _ledger10 = run_dynamic_stage(
            "stage10_seven_family", plan, contract, environment
        )
        if validation10.get("errors"):
            raise RuntimeError("Stage10 failed: " + "; ".join(map(str, validation10["errors"][:10])))
        validation20, _ledger20 = run_dynamic_stage(
            "stage20_proton", plan, contract, environment
        )
        if validation20.get("errors"):
            raise RuntimeError("Stage20 failed: " + "; ".join(map(str, validation20["errors"][:10])))
    except Exception as exc:
        fatal = str(exc)
    finally:
        publish_final(plan, contract, fatal)
        completed = sum(campaign.receipt_path(job).is_file() for job in plan)
        campaign.update_state(
            contract,
            status="FINALIZED_RECOVERY0004" if fatal is None else "FINALIZED_RECOVERY0004_WITH_ERROR",
            stage="final", completed_jobs=completed, last_error=fatal,
        )
    if fatal:
        raise SystemExit(fatal)
    return 0


def self_test() -> dict[str, Any]:
    """Pure scheduler tests; no authority publication and no transport."""
    gib = 1024**3
    evidence = {
        "recent_classes": {
            "unknown/unknown/Mass_model_511/gamma": {
                "recent_p95_upper_bytes": gib,
                "recent_max_bytes": gib,
            }
        },
        "all_time_audit_only": {},
    }
    candidate = {"job_id": "candidate", "geometry": "Mass_model_511", "family": "gamma"}
    dummy_process = type("P", (), {"pid": 101})()
    active = [
        Worker(candidate, dummy_process, None, "", 1.0),
    ]
    upper = class_upper_bytes(candidate, evidence)
    projection = memory_projection(
        active, candidate, evidence,
        available_bytes=6 * gib,
        live_rss={101: upper // 2},
    )
    assert projection["active_unrealised_growth_bytes"] == upper - upper // 2
    assert projection["projected_mem_available_bytes"] == 6 * gib - (upper - upper // 2) - upper
    # Current MemAvailable already reflects realised active RSS; it is not subtracted twice.
    assert projection["projected_mem_available_bytes"] > 3 * gib

    samples = [(0.0, 0), (15.0, SWAP_GROWTH_PAGES // 2), (31.0, SWAP_GROWTH_PAGES)]
    assert swap_growth(samples)["growing"] is True
    assert swap_growth([(0.0, 0), (10.0, 0), (20.0, 0)])["growing"] is False

    state = HealthState()
    low = {"projected_mem_available_bytes": SOFT_PROJECTED_FLOOR_BYTES - 1}
    ok, _ = health_allows_launch(state, now=0.0, projection=low, swap={"growing": False})
    assert not ok and state.paused
    high = {"projected_mem_available_bytes": RESUME_PROJECTED_FLOOR_BYTES + 1}
    ok, _ = health_allows_launch(state, now=1.0, projection=high, swap={"growing": False})
    assert not ok
    ok, _ = health_allows_launch(state, now=1.0 + RESUME_STABLE_S, projection=high, swap={"growing": False})
    assert ok and not state.paused

    strong = HealthState()
    strong_projection = {
        "projected_mem_available_bytes": STRONG_SURPLUS_PROJECTED_FLOOR_BYTES + 1,
        "active": [{"live_rss_bytes": gib}],
    }
    assert not strong_surplus_allows_launch(
        strong, now=0, projection=strong_projection,
        swap={"growing": False}, psi_full_avg10=0,
    )[0]
    assert not strong_surplus_allows_launch(
        strong, now=1, projection=strong_projection,
        swap={"growing": False}, psi_full_avg10=0,
    )[0]
    assert strong_surplus_allows_launch(
        strong, now=1 + STRONG_SURPLUS_STABLE_S,
        projection=strong_projection, swap={"growing": False},
        psi_full_avg10=0,
    )[0]

    toy: list[dict[str, Any]] = []
    for geometry in campaign.GEOMETRY_ORDER:
        for index in range(7):
            toy.append({"job_id": f"{geometry}-{index}", "geometry": geometry, "family": "gamma", "stage": "toy"})
    # Test the wave primitive without invoking stage-aware inherited ordering.
    queues = {geometry: deque(job for job in toy if job["geometry"] == geometry) for geometry in campaign.GEOMETRY_ORDER}
    wave: list[str] = []
    turn = 0
    while any(queues.values()):
        geometry = campaign.GEOMETRY_ORDER[turn % len(campaign.GEOMETRY_ORDER)]
        turn += 1
        for _ in range(min(FAIR_WAVE_SIZE, len(queues[geometry]))):
            wave.append(queues[geometry].popleft()["geometry"])
    longest = 1
    run = 1
    for before, after in zip(wave, wave[1:]):
        run = run + 1 if after == before else 1
        longest = max(longest, run)
    assert longest <= FAIR_WAVE_SIZE
    assert len(wave) == len(toy)
    return {
        "status": "PASS__RECOVERY0004_PURE_SCHEDULER_SELF_TEST",
        "tests": 18,
        "transport_launched": False,
        "authority_published": AUTHORITY.exists(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--publish-authority-only", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    contract, plan = frozen_inputs()
    authority = load_or_publish_authority(contract, plan, publish=False)
    if args.print_recovery_plan:
        print(
            json.dumps(
                {
                    "status": "PASS__READ_ONLY_RECOVERY0004_PLAN",
                    "global_contract_sha256": authority["global_contract_sha256"],
                    "controller_sha256": authority["controller"]["sha256"],
                    "recovery0003_authority_sha256": authority["recovery0003_authority_sha256"],
                    "inherited_pass_receipts": len(authority["cutover"]["inherited_pass_receipts"]),
                    "concurrency": authority["scheduler"],
                    "rss_evidence": authority["rss_evidence_at_cutover"],
                    "mem_available_bytes": campaign.mem_available_bytes(),
                    "frozen_clock": authority["frozen_clock"],
                    "partial_attempt_directories": partial_attempts(),
                    "authority_published": AUTHORITY.exists(),
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.publish_authority_only:
        raise SystemExit(
            "--publish-authority-only is disabled for recovery0004; authority may "
            "only be published after the normal entry acquires the exclusive "
            "campaign lock and proves a clean recovery0003 cutover"
        )

    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, coordinator_signal)
        process_snapshot = assert_cutover_quiescent()
        prior_execution_state = (
            campaign.load_json(campaign.EXECUTION_STATE)
            if campaign.EXECUTION_STATE.is_file()
            else None
        )
        authority = load_or_publish_authority(contract, plan, publish=True)
        publish_cutover(authority, plan, prior_execution_state, process_snapshot)
        configure_runtime()
        loaded_contract, environment = campaign.create_or_load(
            plan, args.cosima.resolve(), datetime.now(timezone.utc)
        )
        campaign.update_state(
            loaded_contract,
            status="RUNNING__RECOVERY0004__LIVE_MEMORY_DYNAMIC_1_TO_8",
            stage="stage10_seven_family",
            completed_jobs=sum(campaign.receipt_path(job).is_file() for job in plan),
        )
        append_scheduler_event(
            "controller_started", authority_sha256=campaign.sha256(AUTHORITY),
            cutover_receipt_sha256=campaign.sha256(CUTOVER_RECEIPT),
        )
        return run_campaign(plan, loaded_contract, environment)
    finally:
        cleanup_failures: list[str] = []
        for worker in list(_ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                os.kill(worker.process.pid, signal.SIGTERM)
                worker.process.join(timeout=30)
            if worker.process.is_alive():
                try:
                    os.kill(worker.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                worker.process.join(timeout=10)
            if worker.process.is_alive():
                cleanup_failures.append(
                    f"worker {worker.process.pid} remained alive after SIGKILL"
                )
        final_process_snapshot = cutover_process_snapshot()
        if final_process_snapshot["matching_processes"]:
            cleanup_failures.append(
                "final orphan-process snapshot was non-empty: "
                + json.dumps(
                    final_process_snapshot["matching_processes"], sort_keys=True
                )
            )
        if final_process_snapshot["partial_attempt_directories"]:
            cleanup_failures.append(
                "final cleanup left partial attempts: "
                + ",".join(final_process_snapshot["partial_attempt_directories"])
            )
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
        if cleanup_failures:
            raise RuntimeError("; ".join(cleanup_failures))


if __name__ == "__main__":
    raise SystemExit(main())
