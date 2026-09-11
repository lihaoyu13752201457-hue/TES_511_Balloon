#!/usr/bin/env python3
"""Prove and publish the write-once recovery0006 r4 drain completion.

This helper never sends a signal and never starts transport.  A separate,
already-published cutover intent is the only authority for stopping the exact
recovery0004 coordinator.  This program merely waits for its inherited fork
workers to finish their already-started jobs, proves receipt and process
closure, takes the campaign lock non-blockingly, and publishes one completion
record with link(2)-based write-once semantics.
"""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/TES_511_Balloon")
CODE = ROOT / "engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/code"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
INTENT = RUN_ROOT / "recovery0006_six_to_one_replan_cutover_intent.json"
COMPLETION = RUN_ROOT / "recovery0006_six_to_one_replan_drain_completion.json"
R4_AUTHORITY = RUN_ROOT / "recovery0004_live_memory_dynamic_authority.json"
R4_CUTOVER_RECEIPT = RUN_ROOT / "recovery0004_cutover_receipt.json"
GLOBAL_CONTRACT = RUN_ROOT / "global_contract.json"
SEED_REGISTRY = RUN_ROOT / "seed_registry.json"
CONTROLLER_LOCK = RUN_ROOT / "controller.lock"
R4_CONTROLLER_NAME = "resume_m05_campaign_batch0006_recovery0004_live_memory_dynamic.py"
ORPHAN_ROOT = RUN_ROOT / "failed_attempts/recovery0006_cutover_orphan"
ORPHAN_EVIDENCE = RUN_ROOT / "recovery0006_six_to_one_replan_cutover_orphan_evidence.json"

_VALIDATED_NEW_RECEIPTS: set[tuple[str, str]] = set()

sys.path.insert(0, str(CODE))
import run_m05_16h_campaign_batch0006 as campaign  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def proc_identity(pid: int) -> dict[str, Any] | None:
    proc = Path("/proc") / str(pid)
    try:
        raw = proc.joinpath("stat").read_text(encoding="utf-8")
        tail = raw[raw.rfind(")") + 2 :].split()
        cmdline = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        ).strip()
        return {
            "pid": pid,
            "state": tail[0],
            "ppid": int(tail[1]),
            "pgid": int(tail[2]),
            "sid": int(tail[3]),
            "proc_starttime_ticks": int(tail[19]),
            "comm": proc.joinpath("comm").read_text(encoding="utf-8").strip(),
            "cmdline_sha256": hashlib.sha256(cmdline.encode()).hexdigest(),
            "cmdline": cmdline,
        }
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, ValueError, IndexError):
        return None


def partial_attempts() -> list[str]:
    return sorted(
        campaign.rel(path)
        for path in RUN_ROOT.glob("stage*/**/.attempt*.partial")
        if path.is_dir()
    )


def live_transport_processes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_root_text = str(RUN_ROOT.resolve())
    for proc_dir in Path("/proc").glob("[0-9]*"):
        identity = proc_identity(int(proc_dir.name))
        if identity is None or identity["pid"] == os.getpid():
            continue
        cmdline = str(identity.pop("cmdline"))
        is_r4 = identity["comm"].startswith("python") and R4_CONTROLLER_NAME in cmdline
        is_cosima = identity["comm"] == "cosima" and run_root_text in cmdline
        if is_r4 or is_cosima:
            identity["kind"] = "recovery0004_python" if is_r4 else "campaign_cosima"
            rows.append(identity)
    return sorted(rows, key=lambda row: int(row["pid"]))


def planned_jobs() -> dict[str, dict[str, Any]]:
    contract = load_json(GLOBAL_CONTRACT)
    jobs = contract.get("planned_jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("global contract has no planned_jobs list")
    if campaign.json_sha256(jobs) != contract.get("planned_jobs_sha256"):
        raise RuntimeError("global contract planned_jobs hash closure failed")
    result = {str(job["job_id"]): job for job in jobs}
    if len(result) != len(jobs):
        raise RuntimeError("global contract contains duplicate job IDs")
    return result


def receipt_manifest(
    jobs: dict[str, dict[str, Any]], trusted_before: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    trusted_before = trusted_before or {}
    rows: list[dict[str, Any]] = []
    for job_id, job in sorted(jobs.items()):
        path = campaign.receipt_path(job)
        if not path.is_file():
            continue
        receipt = load_json(path)
        if receipt.get("status") != "PASS" or receipt.get("errors"):
            raise RuntimeError(f"receipt is not a clean PASS: {job_id}")
        if receipt.get("job") != job:
            raise RuntimeError(f"receipt frozen job differs: {job_id}")
        receipt_sha = sha256(path)
        if trusted_before.get(job_id) != receipt_sha:
            cache_key = (job_id, receipt_sha)
            if cache_key not in _VALIDATED_NEW_RECEIPTS:
                if not campaign.receipt_hashes_valid(receipt):
                    raise RuntimeError(f"new receipt artifact hash closure failed: {job_id}")
                _VALIDATED_NEW_RECEIPTS.add(cache_key)
        rows.append(
            {
                "job_id": job_id,
                "path": campaign.rel(path),
                "sha256": receipt_sha,
                "events": int(job["events"]),
            }
        )
    return rows


def normalize_manifest(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError("intent receipt_manifest_before must be a list")
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            raise RuntimeError("intent receipt manifest row is not an object")
        rows.append(
            {
                "job_id": str(row["job_id"]),
                "path": str(row["path"]),
                "sha256": str(row["sha256"]),
                "events": int(row["events"]),
            }
        )
    rows.sort(key=lambda row: row["job_id"])
    if len({row["job_id"] for row in rows}) != len(rows):
        raise RuntimeError("intent receipt manifest contains duplicate job IDs")
    return rows


def validate_intent(intent: dict[str, Any], jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    input_hashes = intent.get("input_hashes", {})
    required_hashes = {
        "recovery0004_authority": sha256(R4_AUTHORITY),
        "recovery0004_cutover_receipt": sha256(R4_CUTOVER_RECEIPT),
        "global_contract": sha256(GLOBAL_CONTRACT),
        "seed_registry": sha256(SEED_REGISTRY),
    }
    for key, expected in required_hashes.items():
        if input_hashes.get(key) != expected:
            raise RuntimeError(f"cutover intent binding differs: {key}")
    if intent.get("controller_sha256") != load_json(R4_AUTHORITY)["controller"]["sha256"]:
        raise RuntimeError("cutover intent binding differs: controller_sha256")
    controller_path = ROOT / str(intent.get("controller_path", ""))
    if not controller_path.is_file() or sha256(controller_path) != intent["controller_sha256"]:
        raise RuntimeError("frozen recovery0004 controller file hash closure failed")
    coordinator = intent.get("coordinator", {})
    pid = int(coordinator["pid"])
    starttime = int(coordinator["proc_starttime_ticks"])
    if pid <= 1 or starttime <= 0:
        raise RuntimeError("cutover intent coordinator identity is invalid")
    before = normalize_manifest(intent["receipt_manifest_before"])
    if campaign.json_sha256(before) != intent.get("receipt_manifest_before_sha256"):
        raise RuntimeError("cutover intent receipt manifest hash closure failed")
    for row in before:
        if row["job_id"] not in jobs:
            raise RuntimeError(f"intent receipt is outside frozen plan: {row['job_id']}")
    active_partials = intent.get("partial_attempts_before", [])
    if not isinstance(active_partials, list):
        raise RuntimeError("intent partial_attempts_before must be a list")
    active_jobs: set[str] = set()
    active_partial_paths: dict[str, str] = {}
    for row in active_partials:
        if not isinstance(row, dict):
            raise RuntimeError("intent active partial row is not an object")
        job_id = str(row["job_id"])
        if job_id not in jobs:
            raise RuntimeError(f"intent active partial job is outside frozen plan: {job_id}")
        active_jobs.add(job_id)
        active_partial_paths[job_id] = str(row["path"])
    if len(active_jobs) != len(active_partials):
        raise RuntimeError("intent active partial job IDs are not unique")
    descendants = intent.get("active_descendants_before", [])
    if not isinstance(descendants, list):
        raise RuntimeError("intent active_descendants_before must be a list")
    for row in descendants:
        if int(row["pid"]) <= 1 or int(row["proc_starttime_ticks"]) <= 0:
            raise RuntimeError("intent descendant identity is invalid")
    return {
        "before": before,
        "active_jobs": sorted(active_jobs),
        "active_partial_paths": active_partial_paths,
        "pid": pid,
        "starttime": starttime,
    }


def file_manifest(directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(directory).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "validation.json"
    ]


def gzip_observation(path: Path) -> dict[str, Any]:
    total = 0
    error: str | None = None
    try:
        with gzip.open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                total += len(chunk)
    except Exception as exc:  # evidence only: an orphan is never promoted to PASS
        error = f"{type(exc).__name__}: {exc}"
    return {
        "path": path.name,
        "compressed_bytes": path.stat().st_size,
        "decompressed_bytes_before_error_or_eof": total,
        "strict_eof_pass": error is None,
        "error": error,
    }


def orphan_validation_path(job_id: str) -> Path:
    return ORPHAN_ROOT / job_id / "attempt01/validation.json"


def validated_archived_jobs(validated: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for job_id in validated["active_jobs"]:
        path = orphan_validation_path(job_id)
        if not path.is_file():
            continue
        payload = load_json(path)
        expected = {
            "status": "FAIL__RECOVERY0006_CUTOVER_ORPHAN__NOT_MERGEABLE",
            "job_id": job_id,
            "cutover_intent_sha256": sha256(INTENT),
            "merge_eligible": False,
            "returncode": None,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError(f"existing orphan validation differs: {job_id}")
        archive = ROOT / payload["attempt_dir"]
        if not archive.is_dir():
            raise RuntimeError(f"orphan archive is missing: {job_id}")
        manifest = file_manifest(archive)
        if campaign.json_sha256(manifest) != payload.get("artifact_manifest_sha256"):
            raise RuntimeError(f"orphan archive artifact hash closure failed: {job_id}")
        rows[job_id] = {
            "job_id": job_id,
            "attempt_dir": campaign.rel(archive),
            "validation": campaign.rel(path),
            "validation_sha256": sha256(path),
            "artifact_manifest_sha256": payload["artifact_manifest_sha256"],
        }
    return rows


def archive_orphans_under_lock(
    intent: dict[str, Any], validated: dict[str, Any], jobs: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Preserve post-SIGKILL orphan partials as failed evidence, never PASS."""
    if live_transport_processes():
        return None
    identity = proc_identity(validated["pid"])
    if identity is not None and int(identity["proc_starttime_ticks"]) == validated["starttime"]:
        return None
    before_by_id = {row["job_id"]: row["sha256"] for row in validated["before"]}
    current = receipt_manifest(jobs, before_by_id)
    current_ids = {row["job_id"] for row in current}
    expected_partials = {
        path for job_id, path in validated["active_partial_paths"].items()
        if job_id not in current_ids and not orphan_validation_path(job_id).is_file()
    }
    actual_partials = set(partial_attempts())
    if actual_partials - expected_partials:
        raise RuntimeError(
            "refusing to archive partials outside cutover intent: "
            + ",".join(sorted(actual_partials - expected_partials))
        )
    archived_rows: list[dict[str, Any]] = []
    for job_id in validated["active_jobs"]:
        if job_id in current_ids:
            if validated["active_partial_paths"][job_id] in actual_partials:
                raise RuntimeError(f"PASS receipt and cutover partial coexist: {job_id}")
            continue
        source = ROOT / validated["active_partial_paths"][job_id]
        target = ORPHAN_ROOT / job_id / "attempt01"
        validation_path = target / "validation.json"
        if source.is_dir() and target.exists():
            raise RuntimeError(f"orphan source and archive target both exist: {job_id}")
        if not source.is_dir() and not target.is_dir():
            raise RuntimeError(f"cutover orphan evidence disappeared: {job_id}")
        if source.is_dir():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
        artifacts = file_manifest(target)
        names = {row["path"] for row in artifacts}
        required_suffixes = (".source", ".log", ".sim.gz")
        for suffix in required_suffixes:
            if len([name for name in names if name.endswith(suffix)]) != 1:
                raise RuntimeError(f"orphan {job_id} does not have exactly one {suffix} artifact")
        if jobs[job_id]["mode"] == "buildup" and not any(name.endswith(".dat") for name in names):
            raise RuntimeError(f"buildup orphan {job_id} has no isotope DAT artifact")
        sim = next(target / name for name in names if name.endswith(".sim.gz"))
        payload = {
            "schema_version": 1,
            "status": "FAIL__RECOVERY0006_CUTOVER_ORPHAN__NOT_MERGEABLE",
            "errors": [
                "recovery0004_worker_lost_when_tmux_delivered_SIGHUP_after_coordinator_SIGKILL",
                "Cosima_was_allowed_to_exit_naturally_but_no_supervising_worker_remained_to_observe_returncode_or_run_strict_attempt_validation",
            ],
            "job_id": job_id,
            "job": jobs[job_id],
            "attempt": 1,
            "selected_attempt": None,
            "attempt_dir": campaign.rel(target),
            "returncode": None,
            "watchdog_reason": "cutover_orphan_cosima_natural_exit_without_worker",
            "merge_eligible": False,
            "cutover_intent": campaign.rel(INTENT),
            "cutover_intent_sha256": sha256(INTENT),
            "artifact_manifest": artifacts,
            "artifact_manifest_sha256": campaign.json_sha256(artifacts),
            "sim_gzip_observation": gzip_observation(sim),
            "disposition": "preserved_failed_evidence_only; fresh-seed recovery0006 replan must replace this unaccepted frozen job",
        }
        campaign.atomic_write_once_json(validation_path, payload)
        archived_rows.append(
            {
                "job_id": job_id,
                "attempt_dir": campaign.rel(target),
                "validation": campaign.rel(validation_path),
                "validation_sha256": sha256(validation_path),
                "artifact_manifest_sha256": payload["artifact_manifest_sha256"],
            }
        )
    all_archived = validated_archived_jobs(validated)
    if ORPHAN_EVIDENCE.is_file():
        existing = load_json(ORPHAN_EVIDENCE)
        if existing.get("cutover_intent_sha256") != sha256(INTENT):
            raise RuntimeError("existing orphan evidence binds a different cutover intent")
        if existing.get("archived_orphans") != [all_archived[key] for key in sorted(all_archived)]:
            raise RuntimeError("existing orphan evidence archive closure differs")
        return existing
    evidence = {
        "schema_version": 1,
        "status": "PASS__CUTOVER_ORPHANS_PRESERVED_AS_FAILED__NONE_MERGEABLE",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "cutover_intent": campaign.rel(INTENT),
        "cutover_intent_sha256": sha256(INTENT),
        "archived_orphans": [all_archived[key] for key in sorted(all_archived)],
        "newly_archived_in_this_invocation": sorted(row["job_id"] for row in archived_rows),
        "transport_launched": False,
        "signals_sent": False,
        "files_deleted_or_overwritten": False,
    }
    campaign.atomic_write_once_json(ORPHAN_EVIDENCE, evidence)
    existing = load_json(ORPHAN_EVIDENCE)
    if existing.get("cutover_intent_sha256") != sha256(INTENT):
        raise RuntimeError("orphan evidence binds a different cutover intent")
    return existing


def closure_state(intent: dict[str, Any], validated: dict[str, Any], jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    before_sha = {row["job_id"]: row["sha256"] for row in validated["before"]}
    current = receipt_manifest(jobs, before_sha)
    current_by_id = {row["job_id"]: row for row in current}
    before = validated["before"]
    changed_before = [row["job_id"] for row in before if current_by_id.get(row["job_id"]) != row]
    added = [row for row in current if row["job_id"] not in {old["job_id"] for old in before}]
    archived = validated_archived_jobs(validated)
    unresolved_active = [
        job_id for job_id in validated["active_jobs"]
        if job_id not in current_by_id and job_id not in archived
    ]
    identity = proc_identity(validated["pid"])
    old_controller_still_present = bool(
        identity is not None
        and int(identity["proc_starttime_ticks"]) == validated["starttime"]
    )
    processes = live_transport_processes()
    partials = partial_attempts()
    ready_without_lock = not (
        changed_before or unresolved_active or old_controller_still_present or processes or partials
    )
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "old_controller_identity_present": old_controller_still_present,
        "old_controller_current_identity": (
            None if identity is None else {key: value for key, value in identity.items() if key != "cmdline"}
        ),
        "matching_processes": processes,
        "partial_attempt_directories": partials,
        "changed_or_missing_pre_cutover_receipts": changed_before,
        "active_jobs_without_pass_receipt": [
            job_id for job_id in validated["active_jobs"] if job_id not in current_by_id
        ],
        "active_jobs_archived_as_failed_not_mergeable": [archived[key] for key in sorted(archived)],
        "active_jobs_without_pass_or_failed_archive_resolution": unresolved_active,
        "receipt_manifest_after": current,
        "receipt_manifest_after_closure_sha256": campaign.json_sha256(current),
        "new_pass_receipts": added,
        "new_pass_receipts_closure_sha256": campaign.json_sha256(added),
        "ready_without_lock": ready_without_lock,
    }


def try_lock() -> Any | None:
    handle = CONTROLLER_LOCK.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def validate_existing_completion(intent_sha: str) -> dict[str, Any]:
    payload = load_json(COMPLETION)
    if payload.get("status") != "PASS__RECOVERY0004_DRAINED__READY_FOR_RECOVERY0006_REPLAN":
        raise RuntimeError("existing drain completion status differs")
    if payload.get("cutover_intent_sha256") != intent_sha:
        raise RuntimeError("existing drain completion binds a different intent")
    return payload


def publish_when_drained(timeout_s: float, poll_s: float) -> dict[str, Any]:
    if not INTENT.is_file():
        raise RuntimeError(f"missing cutover intent: {INTENT}")
    intent_sha = sha256(INTENT)
    intent = load_json(INTENT)
    jobs = planned_jobs()
    validated = validate_intent(intent, jobs)
    if COMPLETION.is_file():
        return validate_existing_completion(intent_sha)
    deadline = time.monotonic() + timeout_s
    last_report = 0.0
    while True:
        if sha256(INTENT) != intent_sha:
            raise RuntimeError("cutover intent changed while draining")
        state = closure_state(intent, validated, jobs)
        can_finalize_or_archive = (
            not state["old_controller_identity_present"]
            and not state["matching_processes"]
            and not state["changed_or_missing_pre_cutover_receipts"]
        )
        lock = try_lock() if can_finalize_or_archive else None
        if lock is not None:
            try:
                # Recompute under the exclusive lock.  Fork workers inherit the
                # controller's open-file description, so this also proves every
                # inherited worker has closed its copy of the campaign lock.
                orphan_evidence = archive_orphans_under_lock(intent, validated, jobs)
                final_state = closure_state(intent, validated, jobs)
                if not final_state["ready_without_lock"]:
                    raise RuntimeError(
                        "drain remains unresolved under exclusive lock: "
                        + json.dumps(final_state, sort_keys=True)
                    )
                if sha256(INTENT) != intent_sha:
                    raise RuntimeError("cutover intent changed before completion publication")
                payload = {
                    "schema_version": 1,
                    "status": "PASS__RECOVERY0004_DRAINED__READY_FOR_RECOVERY0006_REPLAN",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "cutover_intent": campaign.rel(INTENT),
                    "cutover_intent_sha256": intent_sha,
                    "helper": campaign.rel(Path(__file__).resolve()),
                    "helper_sha256": sha256(Path(__file__).resolve()),
                    "exclusive_controller_lock_acquired": True,
                    "coordinator_pid": validated["pid"],
                    "coordinator_proc_starttime_ticks": validated["starttime"],
                    "recovery0004_authority_sha256": sha256(R4_AUTHORITY),
                    "global_contract_sha256": sha256(GLOBAL_CONTRACT),
                    "seed_registry_sha256": sha256(SEED_REGISTRY),
                    "planned_jobs_sha256": load_json(GLOBAL_CONTRACT)["planned_jobs_sha256"],
                    "receipt_manifest_before": validated["before"],
                    "receipt_manifest_before_closure_sha256": campaign.json_sha256(validated["before"]),
                    "active_jobs_at_cutover": validated["active_jobs"],
                    "cutover_orphan_evidence": (
                        campaign.rel(ORPHAN_EVIDENCE) if orphan_evidence is not None else None
                    ),
                    "cutover_orphan_evidence_sha256": (
                        sha256(ORPHAN_EVIDENCE) if orphan_evidence is not None else None
                    ),
                    "drain_closure": final_state,
                    "unchanged": {
                        "old_authorities_and_final_publications": True,
                        "frozen_jobs_seeds_events_sources_geometries_physics": True,
                        "transport_launched_by_helper": False,
                        "signals_sent_by_helper": False,
                        "artifacts_deleted_or_overwritten": False,
                    },
                }
                campaign.atomic_write_once_json(COMPLETION, payload)
                return validate_existing_completion(intent_sha)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                lock.close()
        now = time.monotonic()
        if now >= deadline:
            raise TimeoutError("timed out waiting for recovery0004 drain: " + json.dumps(state, sort_keys=True))
        if now - last_report >= 10.0:
            print(
                json.dumps(
                    {
                        "status": "WAITING_FOR_RECOVERY0004_DRAIN",
                        "controller_present": state["old_controller_identity_present"],
                        "processes": len(state["matching_processes"]),
                        "partials": len(state["partial_attempt_directories"]),
                        "new_pass_receipts": len(state["new_pass_receipts"]),
                        "active_jobs_without_pass_receipt": state["active_jobs_without_pass_receipt"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            last_report = now
        time.sleep(poll_s)


def self_test() -> dict[str, Any]:
    toy = [
        {"job_id": "b", "path": "b.json", "sha256": "2", "events": 2},
        {"job_id": "a", "path": "a.json", "sha256": "1", "events": 1},
    ]
    normalized = normalize_manifest(toy)
    assert [row["job_id"] for row in normalized] == ["a", "b"]
    try:
        normalize_manifest(toy + [toy[0]])
    except RuntimeError:
        pass
    else:
        raise AssertionError("duplicate manifest test did not fail")
    identity = proc_identity(os.getpid())
    assert identity is not None and identity["proc_starttime_ticks"] > 0
    return {
        "status": "PASS__RECOVERY0006_DRAIN_HELPER_SELF_TEST",
        "tests": 3,
        "signals_sent": False,
        "transport_launched": False,
        "completion_published": COMPLETION.exists(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--wait-and-publish", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=1800.0)
    parser.add_argument("--poll-s", type=float, default=0.5)
    args = parser.parse_args()
    if args.self_test:
        payload = self_test()
    elif args.preflight:
        if not INTENT.is_file():
            payload = {
                "status": "WAITING_FOR_WRITE_ONCE_CUTOVER_INTENT",
                "intent": campaign.rel(INTENT),
                "signals_sent": False,
                "transport_launched": False,
            }
        else:
            intent = load_json(INTENT)
            jobs = planned_jobs()
            validated = validate_intent(intent, jobs)
            payload = closure_state(intent, validated, jobs)
            payload["status"] = "READY_FOR_LOCK_PROBE" if payload["ready_without_lock"] else "DRAIN_INCOMPLETE"
            payload["cutover_intent_sha256"] = sha256(INTENT)
            payload["completion_published"] = COMPLETION.exists()
    else:
        if args.timeout_s <= 0 or args.poll_s <= 0:
            raise SystemExit("timeout and poll interval must be positive")
        payload = publish_when_drained(args.timeout_s, args.poll_s)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
