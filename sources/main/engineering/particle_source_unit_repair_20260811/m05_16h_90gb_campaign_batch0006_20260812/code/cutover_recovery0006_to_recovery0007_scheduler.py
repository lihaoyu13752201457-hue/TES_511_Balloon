#!/usr/bin/env python3
"""Minimal, non-validating recovery0006 -> recovery0007 scheduler cutover.

This helper changes no transport input and starts no transport.  It records
only declarations already present in recovery0006 JSON, freezes only the
coordinator in a dedicated cgroup-v2 child, lets its already-forked workers
finish naturally, then kills the frozen coordinator and proves the campaign lock is
available.  In particular, it never hashes or decompresses an artifact.

The intent and completion are write-once.  A rerun may resume an existing
intent for the same live PID/starttime, but neither record is overwritten.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
R6_ROOT = RUN_ROOT / "recovery0006_six_to_one_replan"
R6_AUTHORITY = R6_ROOT / "authority.json"
R6_SEED_REGISTRY = R6_ROOT / "seed_registry.json"
R6_FINAL = R6_ROOT / "final_umbrella.json"
CONTROLLER_LOCK = RUN_ROOT / "controller.lock"
CONTROLLER_NAME = "resume_m05_campaign_batch0006_recovery0006_six_to_one_replan.py"
INTENT = RUN_ROOT / "recovery0007_scheduler_cutover_intent.json"
COMPLETION = RUN_ROOT / "recovery0007_scheduler_cutover_completion.json"
CGROUP_ROOT = Path("/sys/fs/cgroup")
INTENT_STATUS = "INTENT__FREEZE_R6_SCHEDULER_ONLY_AND_DRAIN_EXISTING_WORK"
COMPLETION_STATUS = "PASS__R6_SCHEDULER_FROZEN_DRAINED_AND_STOPPED__R7_MAY_START"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_once(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        view = memoryview(encoded)
        while view:
            view = view[os.write(fd, view) :]
        os.fsync(fd)
    finally:
        os.close(fd)


def process_identity(pid: int, *, include_cmdline: bool = True) -> dict[str, Any] | None:
    proc = Path("/proc") / str(pid)
    try:
        raw = proc.joinpath("stat").read_text(encoding="utf-8")
        tail = raw[raw.rfind(")") + 2 :].split()
        cmdline = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        ).strip()
        row: dict[str, Any] = {
            "pid": pid,
            "state": tail[0],
            "ppid": int(tail[1]),
            "pgid": int(tail[2]),
            "sid": int(tail[3]),
            "proc_starttime_ticks": int(tail[19]),
            "comm": proc.joinpath("comm").read_text(encoding="utf-8").strip(),
        }
        if include_cmdline:
            row["cmdline"] = cmdline
        return row
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, ValueError, IndexError):
        return None


def all_processes() -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for proc in Path("/proc").glob("[0-9]*"):
        row = process_identity(int(proc.name))
        if row is not None:
            rows[int(row["pid"])] = row
    return rows


def discover_controller(explicit_pid: int | None = None) -> dict[str, Any]:
    rows = all_processes()
    matches = {
        pid: row
        for pid, row in rows.items()
        if CONTROLLER_NAME in str(row.get("cmdline", "")) and row["state"] != "Z"
    }
    if explicit_pid is not None:
        row = matches.get(explicit_pid)
        if row is None:
            raise RuntimeError(f"PID {explicit_pid} is not a live recovery0006 process")
        # Fork workers inherit the same command line.  Only the ancestry root
        # is the coordinator and may be signalled.
        ancestor = int(row["ppid"])
        if ancestor in matches:
            raise RuntimeError(f"PID {explicit_pid} is a recovery0006 worker, not coordinator")
        return row
    roots = [row for row in matches.values() if int(row["ppid"]) not in matches]
    if len(roots) != 1:
        raise RuntimeError(
            f"expected exactly one recovery0006 coordinator ancestry root, found "
            f"{[(r['pid'], r['state']) for r in roots]}"
        )
    return roots[0]


def same_process(expected: dict[str, Any]) -> dict[str, Any] | None:
    current = process_identity(int(expected["pid"]))
    if current is None or int(current["proc_starttime_ticks"]) != int(expected["proc_starttime_ticks"]):
        return None
    return current


def descendants(parent: int, rows: dict[int, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows or all_processes()
    selected: list[dict[str, Any]] = []
    frontier = [parent]
    seen: set[int] = set()
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        children = [row for row in rows.values() if int(row["ppid"]) == current]
        selected.extend(children)
        frontier.extend(int(row["pid"]) for row in children)
    return sorted(selected, key=lambda row: int(row["pid"]))


def public_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in ("pid", "state", "ppid", "pgid", "sid", "proc_starttime_ticks", "comm")}


def unified_cgroup(pid: int) -> Path:
    for line in (Path("/proc") / str(pid) / "cgroup").read_text(encoding="utf-8").splitlines():
        fields = line.split(":", 2)
        if len(fields) == 3 and fields[0] == "0" and fields[1] == "":
            return CGROUP_ROOT / fields[2].lstrip("/")
    raise RuntimeError(f"PID {pid} has no unified cgroup-v2 membership")


def cgroup_paths(coordinator: dict[str, Any]) -> tuple[Path, Path]:
    parent = unified_cgroup(int(coordinator["pid"]))
    child = parent / (
        f"m05_recovery0007_cutover_{int(coordinator['pid'])}_"
        f"{int(coordinator['proc_starttime_ticks'])}"
    )
    return parent, child


def cgroup_events(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in path.joinpath("cgroup.events").read_text(encoding="utf-8").splitlines():
        key, value = line.split(None, 1)
        result[key] = int(value)
    return result


def freeze_coordinator(coordinator: dict[str, Any], child: Path) -> None:
    child.mkdir(mode=0o755, exist_ok=True)
    child.joinpath("cgroup.procs").write_text(f"{int(coordinator['pid'])}\n", encoding="ascii")
    members = {int(value) for value in child.joinpath("cgroup.procs").read_text(encoding="ascii").split()}
    if members != {int(coordinator["pid"])}:
        raise RuntimeError(f"exclusive coordinator cgroup membership failed: {sorted(members)}")
    child.joinpath("cgroup.freeze").write_text("1\n", encoding="ascii")
    deadline = time.monotonic() + 5.0
    while cgroup_events(child).get("frozen") != 1:
        if time.monotonic() >= deadline:
            raise RuntimeError("dedicated coordinator cgroup did not report frozen=1")
        time.sleep(0.02)


def cgroup_is_frozen(child: Path, coordinator: dict[str, Any]) -> bool:
    if not child.is_dir() or cgroup_events(child).get("frozen") != 1:
        return False
    members = {int(value) for value in child.joinpath("cgroup.procs").read_text(encoding="ascii").split()}
    return members == {int(coordinator["pid"])}


def remove_empty_cutover_cgroup(child: Path) -> None:
    if not child.is_dir():
        return
    members = child.joinpath("cgroup.procs").read_text(encoding="ascii").split()
    if members:
        raise RuntimeError(f"cutover cgroup is not empty after coordinator kill: {members}")
    child.joinpath("cgroup.freeze").write_text("0\n", encoding="ascii")
    child.rmdir()


def partial_attempts() -> list[str]:
    paths = list(RUN_ROOT.glob("stage*/**/.attempt*.partial"))
    paths += list(R6_ROOT.glob("attempts/**/.attempt*.partial"))
    return sorted(relative(path) for path in paths if path.is_dir())


def receipt_declarations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(R6_ROOT.glob("job_receipts/**/*.json")):
        payload = load_json(path)
        job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
        artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
        rows.append(
            {
                "job_id": str(job.get("job_id", path.stem)),
                "receipt_path": relative(path),
                "declared_status": payload.get("status"),
                "declared_errors": payload.get("errors"),
                "declared_events": job.get("events"),
                "declared_selected_attempt": payload.get("selected_attempt"),
                "declared_attempt_dir": payload.get("attempt_dir"),
                "declared_recovery_authority_sha256": payload.get("recovery_authority_sha256"),
                "declared_artifacts": {
                    str(kind): {
                        "name": value.get("name"),
                        "bytes": value.get("bytes"),
                        "sha256": value.get("sha256"),
                    }
                    for kind, value in sorted(artifacts.items())
                    if isinstance(value, dict)
                },
            }
        )
    return rows


def failed_declarations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = R6_ROOT / "failed_attempts"
    if not root.is_dir():
        return rows
    for path in sorted(root.glob("**/validation.json")):
        attempt = path.parent.name
        job_id = path.parent.parent.name if path.parent.parent != root else None
        rows.append({"job_id": job_id, "attempt": attempt, "validation_path": relative(path)})
    return rows


def authority_declarations() -> dict[str, Any]:
    authority = load_json(R6_AUTHORITY)
    controller = authority.get("controller") if isinstance(authority.get("controller"), dict) else {}
    inputs = authority.get("inputs") if isinstance(authority.get("inputs"), dict) else {}
    return {
        "authority_path": relative(R6_AUTHORITY),
        "authority_status": authority.get("status"),
        "recovery_id": authority.get("recovery_id"),
        "controller_path": controller.get("path"),
        "controller_declared_sha256": controller.get("sha256"),
        "effective_pending_plan_declared_sha256": authority.get("effective_pending_plan_sha256"),
        "fresh_seed_registry_payload_declared_sha256": authority.get("fresh_seed_registry_payload_sha256"),
        "inherited_pass_manifest_declared_sha256": authority.get("inherited_pass_manifest_sha256"),
        "seed_registry_path": relative(R6_SEED_REGISTRY),
        "input_declarations": inputs,
        "note": "all sha256 strings are copied declarations; this helper computed none",
    }


def related_non_z_processes() -> list[dict[str, Any]]:
    run_text = str(R6_ROOT.resolve())
    rows: list[dict[str, Any]] = []
    for row in all_processes().values():
        if row["state"] == "Z" or int(row["pid"]) == os.getpid():
            continue
        cmdline = str(row.get("cmdline", ""))
        if CONTROLLER_NAME in cmdline or (row["comm"] == "cosima" and run_text in cmdline):
            rows.append(public_identity(row))
    return sorted(rows, key=lambda row: int(row["pid"]))


def intent_payload(coordinator: dict[str, Any]) -> dict[str, Any]:
    current_descendants = descendants(int(coordinator["pid"]))
    cgroup_parent, cgroup_child = cgroup_paths(coordinator)
    return {
        "schema_version": 1,
        "status": INTENT_STATUS,
        "created_at": utc_now(),
        "authorization": {
            "scheduler_only_change": True,
            "minimum_target_workers": 6,
            "absolute_worker_cap": 10,
            "live_mem_available_floor_bytes": int(1.5 * 1024**3),
            "no_transport_input_changes": True,
            "no_repeated_artifact_validation_or_hashing": True,
        },
        "r6_declarations": authority_declarations(),
        "coordinator": public_identity(coordinator),
        "coordinator_parent_cgroup": str(cgroup_parent),
        "dedicated_freezer_cgroup": str(cgroup_child),
        "initial_descendants": [public_identity(row) for row in current_descendants],
        "initial_direct_child_identities": [
            [int(row["pid"]), int(row["proc_starttime_ticks"])]
            for row in current_descendants
            if int(row["ppid"]) == int(coordinator["pid"])
        ],
        "receipt_declarations_before": receipt_declarations(),
        "failed_attempt_declarations_before": failed_declarations(),
        "partial_attempts_before": partial_attempts(),
        "r6_final_umbrella_absent_before": not R6_FINAL.exists(),
        "method": [
            "move coordinator only to a dedicated cgroup-v2 child and set cgroup.freeze=1",
            "allow already-forked descendants to finish without signalling them",
            "require cgroup.events frozen=1 and zero non-z descendants/partials",
            "SIGKILL cgroup-frozen coordinator",
            "acquire campaign flock exclusively before write-once completion",
        ],
    }


def preflight(explicit_pid: int | None) -> dict[str, Any]:
    coordinator = discover_controller(explicit_pid)
    cgroup_parent, cgroup_child = cgroup_paths(coordinator)
    return {
        "status": "PASS__READ_ONLY_R6_TO_R7_CUTOVER_PREFLIGHT",
        "coordinator": public_identity(coordinator),
        "coordinator_parent_cgroup": str(cgroup_parent),
        "dedicated_freezer_cgroup": str(cgroup_child),
        "parent_cgroup_freeze_writable": os.access(cgroup_parent / "cgroup.freeze", os.W_OK),
        "parent_cgroup_procs_writable": os.access(cgroup_parent / "cgroup.procs", os.W_OK),
        "descendants": [public_identity(row) for row in descendants(int(coordinator["pid"]))],
        "receipt_count": len(receipt_declarations()),
        "failed_attempt_count": len(failed_declarations()),
        "partial_attempts": partial_attempts(),
        "r6_final_umbrella_absent": not R6_FINAL.exists(),
        "intent_exists": INTENT.exists(),
        "completion_exists": COMPLETION.exists(),
        "transport_launched": False,
        "hashes_computed": False,
    }


def self_test() -> dict[str, Any]:
    identity = process_identity(os.getpid())
    assert identity is not None and identity["pid"] == os.getpid()
    assert same_process(identity) is not None
    with tempfile.TemporaryDirectory(prefix="m05-r7-cutover-selftest-") as directory:
        probe = Path(directory) / "once.json"
        write_once(probe, {"value": 1})
        assert load_json(probe) == {"value": 1}
        try:
            write_once(probe, {"value": 2})
        except FileExistsError:
            pass
        else:
            raise AssertionError("write_once overwrote an existing record")
    own_cgroup = unified_cgroup(os.getpid())
    assert own_cgroup.joinpath("cgroup.events").is_file()
    return {
        "status": "PASS__R6_TO_R7_CUTOVER_HELPER_SELF_TEST",
        "tests": 6,
        "unified_cgroup": str(own_cgroup),
        "transport_launched": False,
        "signals_sent": False,
        "hashes_computed": False,
    }


def cgroup_probe() -> dict[str, Any]:
    """Exercise a dedicated child freezer using only a disposable sleep."""
    process = subprocess.Popen(["/bin/sleep", "30"])
    identity: dict[str, Any] | None = None
    child: Path | None = None
    frozen = False
    try:
        identity = process_identity(process.pid)
        if identity is None:
            raise RuntimeError("dummy probe process vanished")
        _, child = cgroup_paths(identity)
        freeze_coordinator(identity, child)
        frozen = cgroup_is_frozen(child, identity)
        if not frozen:
            raise RuntimeError("dummy cgroup freezer proof failed")
        os.kill(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
        remove_empty_cutover_cgroup(child)
        return {
            "status": "PASS__DISPOSABLE_CGROUP_V2_FREEZER_PROBE",
            "dummy_pid": process.pid,
            "frozen_proved": True,
            "dummy_killed": True,
            "cgroup_removed": not child.exists(),
            "transport_launched": False,
            "hashes_computed": False,
        }
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if child is not None and child.is_dir():
            try:
                remove_empty_cutover_cgroup(child)
            except OSError:
                # Leave an explicit empty probe cgroup for manual inspection
                # rather than hiding the primary failure.
                pass


def execute(explicit_pid: int | None, timeout_s: float, stable_s: float) -> dict[str, Any]:
    if COMPLETION.exists():
        return load_json(COMPLETION)
    if R6_FINAL.exists():
        raise RuntimeError("r6 final umbrella already exists; scheduler cutover is not applicable")
    coordinator = discover_controller(explicit_pid)
    if INTENT.exists():
        intent = load_json(INTENT)
        frozen = intent.get("coordinator", {})
        if (
            int(frozen.get("pid", -1)) != int(coordinator["pid"])
            or int(frozen.get("proc_starttime_ticks", -1))
            != int(coordinator["proc_starttime_ticks"])
        ):
            raise RuntimeError("existing write-once intent binds a different coordinator identity")
    else:
        write_once(INTENT, intent_payload(coordinator))
        intent = load_json(INTENT)

    pid = int(coordinator["pid"])
    declared_child = Path(str(intent.get("dedicated_freezer_cgroup", "")))
    expected_parent = Path(str(intent.get("coordinator_parent_cgroup", "")))
    expected_child = declared_child
    if unified_cgroup(pid) not in {expected_parent, expected_child}:
        raise RuntimeError("write-once intent cgroup binding differs from live coordinator membership")
    freeze_coordinator(coordinator, expected_child)
    stop_requested_at = utc_now()

    initial_children = {
        (int(pair[0]), int(pair[1]))
        for pair in intent.get("initial_direct_child_identities", [])
    }
    # A legitimate launch can fall in the very short write-intent -> freezer
    # interval.  Freeze-time membership is the actual no-new-launch boundary.
    rows_at_freeze = all_processes()
    direct_children_at_freeze = {
        (int(row["pid"]), int(row["proc_starttime_ticks"]))
        for row in descendants(pid, rows_at_freeze)
        if int(row["ppid"]) == pid
    }
    initial_children |= direct_children_at_freeze
    deadline = time.monotonic() + timeout_s
    quiescent_since: float | None = None
    last_descendants: list[dict[str, Any]] = []
    while True:
        current = same_process(coordinator)
        if current is None:
            raise RuntimeError("coordinator vanished before authorized SIGKILL")
        if not cgroup_is_frozen(expected_child, coordinator):
            raise RuntimeError("dedicated coordinator cgroup lost frozen=1/exclusive membership")
        rows = all_processes()
        current_descendants = descendants(pid, rows)
        last_descendants = [public_identity(row) for row in current_descendants]
        direct = {
            (int(row["pid"]), int(row["proc_starttime_ticks"]))
            for row in current_descendants
            if int(row["ppid"]) == pid
        }
        if not direct.issubset(initial_children):
            raise RuntimeError(f"new direct coordinator child appeared after SIGSTOP: {sorted(direct - initial_children)}")
        non_z = [row for row in current_descendants if row["state"] != "Z"]
        partials = partial_attempts()
        if not non_z and not partials:
            quiescent_since = quiescent_since or time.monotonic()
            if time.monotonic() - quiescent_since >= stable_s:
                break
        else:
            quiescent_since = None
        if R6_FINAL.exists():
            raise RuntimeError("r6 final umbrella appeared while coordinator was cgroup-frozen")
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"timed out draining r6: non_z={len(non_z)} partials={len(partials)}"
            )
        time.sleep(0.2)

    stopped = same_process(coordinator)
    if stopped is None or not cgroup_is_frozen(expected_child, coordinator):
        raise RuntimeError("lost frozen-coordinator proof immediately before SIGKILL")
    if R6_FINAL.exists():
        raise RuntimeError("r6 final umbrella exists immediately before coordinator kill")
    os.kill(pid, signal.SIGKILL)
    killed_at = utc_now()
    gone_deadline = time.monotonic() + 10.0
    while same_process(coordinator) is not None:
        if time.monotonic() >= gone_deadline:
            raise RuntimeError("stopped r6 coordinator remained after SIGKILL")
        time.sleep(0.02)
    remove_empty_cutover_cgroup(expected_child)

    lock = CONTROLLER_LOCK.open("a+", encoding="utf-8")
    lock_deadline = time.monotonic() + 15.0
    while True:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= lock_deadline:
                lock.close()
                raise RuntimeError("campaign controller lock remained held after r6 drain/kill")
            time.sleep(0.05)
    try:
        process_deadline = time.monotonic() + 10.0
        while True:
            live = related_non_z_processes()
            if not live:
                break
            if time.monotonic() >= process_deadline:
                raise RuntimeError(f"r6-related non-z processes remained after kill: {live}")
            time.sleep(0.05)
        final_receipts = receipt_declarations()
        completion = {
            "schema_version": 1,
            "status": COMPLETION_STATUS,
            "completed_at": utc_now(),
            "intent_path": relative(INTENT),
            "r6_declarations": authority_declarations(),
            "coordinator": public_identity(coordinator),
            "stop_requested_at": stop_requested_at,
            "coordinator_killed_at": killed_at,
            "coordinator_control_sequence": [
                "DEDICATED_CGROUP_V2_FREEZE=1",
                "SIGKILL_AFTER_DRAIN_WHILE_FROZEN",
                "EMPTY_CGROUP_REMOVED",
            ],
            "dedicated_freezer_cgroup": str(expected_child),
            "dedicated_freezer_cgroup_removed": not expected_child.exists(),
            "descendants_at_quiescence": last_descendants,
            "direct_child_identities_at_freeze": [list(value) for value in sorted(direct_children_at_freeze)],
            "zero_r6_related_non_z_processes": True,
            "zero_partial_attempts": not partial_attempts(),
            "partial_attempts_after": partial_attempts(),
            "r6_final_umbrella_absent": not R6_FINAL.exists(),
            "exclusive_campaign_flock_held_during_publication": True,
            "controller_lock_path": relative(CONTROLLER_LOCK),
            "receipt_declarations_frozen": final_receipts,
            "receipt_count_frozen": len(final_receipts),
            "failed_attempt_declarations_frozen": failed_declarations(),
            "physics_transport_changes": False,
            "transport_launched_by_helper": False,
            "artifacts_revalidated": False,
            "hashes_computed": False,
        }
        if R6_FINAL.exists() or completion["partial_attempts_after"]:
            raise RuntimeError("final cutover publication gate changed while lock held")
        write_once(COMPLETION, completion)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
    return load_json(COMPLETION)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="explicit r6 coordinator PID; ancestry is still checked")
    parser.add_argument("--preflight", action="store_true", help="read-only process/evidence snapshot")
    parser.add_argument("--self-test", action="store_true", help="run transport-free helper tests")
    parser.add_argument("--cgroup-probe", action="store_true", help="test freezer with disposable sleep")
    parser.add_argument("--drain-timeout-s", type=float, default=3600.0)
    parser.add_argument("--stable-quiescence-s", type=float, default=2.0)
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    elif args.cgroup_probe:
        result = cgroup_probe()
    elif args.preflight:
        result = preflight(args.pid)
    else:
        if args.drain_timeout_s <= 0 or args.stable_quiescence_s < 1.0:
            raise SystemExit("positive drain timeout and >=1s stable quiescence are required")
        result = execute(args.pid, args.drain_timeout_s, args.stable_quiescence_s)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
