#!/usr/bin/env python3
"""Scheduling-only live extension for the already-running exact attempt04.

If Cosima is still live immediately before the frozen controller hard end,
freeze only the controller (which owns the campaign flock), let the independent
Cosima process group continue under mirrored watchdogs until T-900, then resume
the controller for its normal validation/publication.  No transport input,
partial artifact, receipt, hash, or gzip is modified/read by this supervisor.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_m05_16h_campaign_batch0006 as campaign
import run_m05_campaign_batch0006_continuation0001_recovery0003_attempt04 as r3


PARENT_PID = 146670
CHILD_PID = 146708
CHILD_PGID = 146708
CUTOVER_AT = datetime.fromisoformat("2026-08-13T02:47:30+00:00")
EXTENDED_END = datetime.fromisoformat("2026-08-13T03:03:00+00:00")
ORIGINAL_DEADLINE = datetime.fromisoformat("2026-08-13T03:18:34.874118+00:00")
PARTIAL = r3.RUN_NS / "attempts/continuation_non_gamma_wave0001/S3d_O8/instant/eplus/c1_ng_eplus_instant_S3d_O8_wave0001/.attempt04.partial"
SOURCE = PARTIAL / "c1_ng_eplus_instant_S3d_O8_wave0001.source"
AUTHORITY = r3.RUN_NS / "attempt04_live_extension_authority.json"
EVENTS = r3.RUN_NS / "attempt04_live_extension_events.jsonl"
COMPLETION = r3.RUN_NS / "attempt04_live_extension_completion.json"
UMBRELLA = r3.RUN_NS / "attempt04_live_extension_umbrella.json"
TEMP_SWAP_PATH = "/home/ubuntu/TES_511_Balloon/.m05_attempt04_swap"
OUTPUT_CAP_BYTES = 2_000_000_000
MEM_FLOOR_BYTES = 256 * 1024**2
FS_FLOOR_BYTES = 20 * 1024**3
HANG_S = 15 * 60
POLL_S = 2.0
_STOP = False


def rel(path: Path) -> str:
    return campaign.rel(path)


def atomic_write_once(path: Path, payload: dict[str, Any]) -> None:
    campaign.atomic_write_once_json(path, payload)


def proc_fields(pid: int) -> dict[str, Any] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        tail = raw[raw.rfind(")") + 2 :].split()
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return {
            "pid": pid, "state": tail[0], "pgid": int(tail[2]),
            "utime_stime_ticks": int(tail[11]) + int(tail[12]),
            "starttime_ticks": int(tail[19]), "cmdline": cmd,
        }
    except (OSError, ValueError, IndexError):
        return None


def bind_identities() -> tuple[dict[str, Any], dict[str, Any]]:
    parent, child = proc_fields(PARENT_PID), proc_fields(CHILD_PID)
    if parent is None or child is None:
        raise RuntimeError("attempt04 parent/child is not live")
    if "run_m05_campaign_batch0006_continuation0001_recovery0003_attempt04.py" not in parent["cmdline"]:
        raise RuntimeError("parent cmdline identity mismatch")
    if child["pgid"] != CHILD_PGID or "/cosima -s 1800262155" not in child["cmdline"] or str(SOURCE.resolve()) not in child["cmdline"]:
        raise RuntimeError("child PGID/seed/source cmdline identity mismatch")
    return parent, child


def same_process(bound: dict[str, Any]) -> dict[str, Any] | None:
    current = proc_fields(int(bound["pid"]))
    if current is None or current["starttime_ticks"] != bound["starttime_ticks"] or current["cmdline"] != bound["cmdline"]:
        return None
    return current


def swap_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = Path("/proc/swaps").read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        fields = line.split()
        if len(fields) >= 5:
            rows.append({"path": fields[0], "type": fields[1], "size_kib": int(fields[2]), "used_kib": int(fields[3]), "priority": int(fields[4])})
    return rows


def mem_available() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.is_dir() else 0


def append_event(kind: str, **fields: Any) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "event": kind, **fields}, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno()); fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def authority(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    swaps = swap_rows()
    extra = next((row for row in swaps if row["path"] == TEMP_SWAP_PATH), None)
    if extra is None:
        raise RuntimeError("external attempt04 temporary swap evidence absent")
    return {
        "schema_version": 1,
        "status": "AUTHORIZED__ATTEMPT04_SCHEDULING_ONLY_LIVE_EXTENSION__PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "controller": rel(Path(__file__).resolve()),
        "bound_parent": parent, "bound_child": child,
        "attempt04_authority": rel(r3.AUTHORITY), "attempt": 4,
        "job_id": r3.r2.TARGET_JOB_ID, "seed": 1800262155, "events": 2500,
        "source": rel(SOURCE), "partial": rel(PARTIAL),
        "old_controller_hard_end": "2026-08-13T02:48:34.874118+00:00",
        "parent_freeze_at": CUTOVER_AT.isoformat(), "extended_child_end": EXTENDED_END.isoformat(),
        "original_deadline": ORIGINAL_DEADLINE.isoformat(),
        "mechanism": "SIGSTOP exact bound parent only; child PGID continues; SIGCONT parent on child exit/resource stop/T-900",
        "mirrored_watchdogs": {"MemAvailable_floor_bytes": MEM_FLOOR_BYTES, "filesystem_floor_bytes": FS_FLOOR_BYTES, "attempt_output_cap_bytes": OUTPUT_CAP_BYTES, "hang_s": HANG_S},
        "external_swap_evidence": {"all_swaps": swaps, "temporary_swap": extra},
        "temporary_swap_cleanup_policy": "never while controller/child is live; eligible only after terminal; this unprivileged supervisor records eligibility and does not unlink",
        "simulation_inputs_changed": False, "attempt05_authorized": False, "gamma_locked": True,
        "supersedes_only": "attempt04 scheduling hard_end/runtime cap; recovery0003 exact job and all transport inputs remain unchanged",
        "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
    }


def request_stop(_signum: int, _frame: Any) -> None:
    global _STOP
    _STOP = True


def stop_child(reason: str, child_bound: dict[str, Any]) -> None:
    current = same_process(child_bound)
    if current is None or current["state"] == "Z":
        return
    append_event("child_stop_requested", reason=reason, child_pid=CHILD_PID, child_pgid=CHILD_PGID)
    try: os.killpg(CHILD_PGID, signal.SIGTERM)
    except ProcessLookupError: return
    limit = time.monotonic() + 10
    while time.monotonic() < limit:
        current = same_process(child_bound)
        if current is None or current["state"] == "Z": return
        time.sleep(0.25)
    try: os.killpg(CHILD_PGID, signal.SIGKILL)
    except ProcessLookupError: pass
    # The controller must not be resumed until the child leader is either
    # gone or a zombie ready for the controller to reap.  In particular, do
    # not wait for /proc disappearance: only the stopped parent can reap it.
    limit = time.monotonic() + 5
    while time.monotonic() < limit:
        current = same_process(child_bound)
        if current is None or current["state"] == "Z":
            return
        time.sleep(0.1)
    raise RuntimeError("child remained running after SIGKILL")


def resume_parent(parent_bound: dict[str, Any], reason: str) -> None:
    current = same_process(parent_bound)
    if current is not None:
        os.kill(PARENT_PID, signal.SIGCONT)
        append_event("parent_resumed", reason=reason, parent_pid=PARENT_PID)


def self_test() -> dict[str, Any]:
    parent, child = bind_identities(); proposal = authority(parent, child)
    assert CUTOVER_AT < EXTENDED_END < ORIGINAL_DEADLINE
    assert proposal["external_swap_evidence"]["temporary_swap"]["size_kib"] >= 16_000_000
    assert child["pgid"] == CHILD_PGID and proposal["attempt05_authorized"] is False
    return {"status": "PASS__ATTEMPT04_LIVE_EXTENSION_STRUCTURAL_SELF_TEST", "tests": 5, "transport_or_signal_action": False, "parent": parent, "child": child, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args()
    parent, child = bind_identities(); proposal = authority(parent, child)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True)); return 0
    if args.print_plan:
        print(json.dumps({**proposal, "status": "PASS__READ_ONLY_ATTEMPT04_LIVE_EXTENSION_PLAN", "transport_or_signal_action": False}, indent=2, sort_keys=True)); return 0
    if AUTHORITY.is_file():
        existing = campaign.load_json(AUTHORITY)
        # Swap used-kib is live telemetry and can legitimately move between a
        # supervisor process replacement and its restart.  The write-once
        # authority already binds the external swap path/size/priority; keep
        # comparing every immutable scheduling and process identity field.
        for key in ("attempt04_authority", "attempt", "job_id", "seed", "events", "source", "partial", "parent_freeze_at", "extended_child_end", "original_deadline", "mechanism", "mirrored_watchdogs", "simulation_inputs_changed", "attempt05_authorized", "gamma_locked"):
            if existing.get(key) != proposal.get(key): raise RuntimeError(f"existing live extension authority differs: {key}")
        # State and accumulated CPU ticks are telemetry.  PID reuse safety is
        # provided by starttime + exact cmdline + PGID.
        for role in ("bound_parent", "bound_child"):
            old_proc, new_proc = existing.get(role, {}), proposal.get(role, {})
            for key in ("pid", "pgid", "starttime_ticks", "cmdline"):
                if old_proc.get(key) != new_proc.get(key):
                    raise RuntimeError(f"existing live extension {role} differs: {key}")
        old_swap = existing.get("external_swap_evidence", {}).get("temporary_swap", {})
        new_swap = proposal.get("external_swap_evidence", {}).get("temporary_swap", {})
        for key in ("path", "type", "size_kib", "priority"):
            if old_swap.get(key) != new_swap.get(key):
                raise RuntimeError(f"existing live extension swap binding differs: {key}")
    else:
        atomic_write_once(AUTHORITY, proposal)
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    for sig in previous: signal.signal(sig, request_stop)
    frozen = False; outcome = "unknown"; stop_reason: str | None = None
    try:
        append_event("supervisor_started", parent_pid=PARENT_PID, child_pid=CHILD_PID)
        while datetime.now(timezone.utc) < CUTOVER_AT and not _STOP:
            current = same_process(child)
            if current is None or current["state"] == "Z":
                outcome = "child_terminal_before_cutover_no_intervention"; break
            time.sleep(POLL_S)
        if outcome == "unknown" and not _STOP:
            if same_process(parent) is None or same_process(child) is None:
                outcome = "identity_lost_before_cutover_no_signal"
            else:
                os.kill(PARENT_PID, signal.SIGSTOP); frozen = True
                # A controller blocked in an uninterruptible kernel wait may
                # take a moment to report T.  Poll briefly instead of treating
                # a single early sample as failure.
                freeze_limit = time.monotonic() + 5
                stopped = same_process(parent)
                while stopped is not None and stopped["state"] not in {"T", "t"} and time.monotonic() < freeze_limit:
                    time.sleep(0.1)
                    stopped = same_process(parent)
                if stopped is None or stopped["state"] not in {"T", "t"}:
                    raise RuntimeError("parent did not enter stopped state within 5s")
                append_event("parent_frozen_child_continues", parent_pid=PARENT_PID, child_pid=CHILD_PID)
                last_cpu = int(child["utime_stime_ticks"]); last_bytes = directory_bytes(PARTIAL); last_activity = time.monotonic()
                while not _STOP:
                    now = datetime.now(timezone.utc); current = same_process(child)
                    if current is None or current["state"] == "Z":
                        outcome = "child_terminal_during_extension"; break
                    size = directory_bytes(PARTIAL); cpu = int(current["utime_stime_ticks"])
                    if size > last_bytes or cpu > last_cpu:
                        last_activity = time.monotonic(); last_bytes = size; last_cpu = cpu
                    if now >= EXTENDED_END: stop_reason = "extended_T_minus_900_boundary"
                    elif mem_available() < MEM_FLOOR_BYTES: stop_reason = "mirrored_256MiB_MemAvailable_floor"
                    elif os.statvfs(campaign.RUN_ROOT).f_bavail * os.statvfs(campaign.RUN_ROOT).f_frsize < FS_FLOOR_BYTES: stop_reason = "mirrored_20GiB_filesystem_floor"
                    elif size > OUTPUT_CAP_BYTES: stop_reason = "mirrored_2GB_attempt_output_cap"
                    elif time.monotonic() - last_activity > HANG_S: stop_reason = "mirrored_15m_no_CPU_or_output_growth"
                    if stop_reason:
                        stop_child(stop_reason, child); outcome = "child_stopped_by_extension_supervisor"; break
                    time.sleep(POLL_S)
                if _STOP and outcome == "unknown": outcome = "supervisor_stop_requested_parent_resumed"
        if frozen:
            resume_parent(parent, outcome); frozen = False
        # Keep temporary swap cleanup ineligible until the controller is truly terminal.
        while same_process(parent) is not None and datetime.now(timezone.utc) < ORIGINAL_DEADLINE and not _STOP:
            time.sleep(POLL_S)
        parent_terminal = same_process(parent) is None
        completion = {"schema_version": 1, "status": "PASS__LIVE_EXTENSION_SUPERVISION_COMPLETE" if parent_terminal else "INCOMPLETE__PARENT_NOT_TERMINAL", "outcome": outcome, "stop_reason": stop_reason, "parent_terminal": parent_terminal, "temporary_swap_path": TEMP_SWAP_PATH, "temporary_swap_cleanup_eligible": parent_terminal, "temporary_swap_removed_by_supervisor": False, "supersedes_only": "recovery0003 attempt04 scheduling hard_end/runtime cap", "same_exact_job_seed_events_source_geometry_physics": True, "attempt05_authorized": False, "gamma_locked": True, "simulation_inputs_changed": False, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False}
        atomic_write_once(COMPLETION, completion)
        atomic_write_once(UMBRELLA, {"schema_version": 1, "status": completion["status"], "authority": rel(AUTHORITY), "completion": rel(COMPLETION), "supersedes_only": completion["supersedes_only"], "same_exact_job_seed_events_source_geometry_physics": True, "attempt05_authorized": False, "gamma_locked": True})
        return 0 if parent_terminal else 1
    finally:
        # SIGCONT is harmless for a running process and prevents every error
        # path from leaving the bound controller stopped.
        resume_parent(parent, "supervisor_unconditional_finally_cleanup")
        for sig, handler in previous.items(): signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
