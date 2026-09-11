#!/usr/bin/env python3
"""Read-only live terminal monitor for the M05 batch0006 campaign."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
R6_ROOT = RUN_ROOT / "recovery0006_six_to_one_replan"
R7_ROOT = RUN_ROOT / "recovery0007_efficiency_scheduler"
R8_ROOT = RUN_ROOT / "recovery0008_current_attempt_disk_admission"
C1_ROOT = RUN_ROOT / "continuation0001_balanced_non_gamma_deweight_gamma"
CONTRACT = RUN_ROOT / "global_contract.json"
MAINLINE_STATE = R8_ROOT / "execution_state.json"
STATE = C1_ROOT / "execution_state.json"
RECEIPTS = RUN_ROOT / "job_receipts"
R6_RECEIPTS = R6_ROOT / "job_receipts"
R7_RECEIPTS = R7_ROOT / "job_receipts"
R8_RECEIPTS = R8_ROOT / "job_receipts"
C1_RECEIPTS = C1_ROOT / "job_receipts"
FAILED = RUN_ROOT / "failed_attempts"
R6_FAILED = R6_ROOT / "failed_attempts"
R7_FAILED = R7_ROOT / "failed_attempts"
R8_FAILED = R8_ROOT / "failed_attempts"
C1_FAILED = C1_ROOT / "failed_attempts"
STORE_RE = re.compile(rb"Storing event\s+(\d+)(?:\s+of\s+\d+)?")
EVENTS_RE = re.compile(r"^\s*\S+\.Events\s+(\d+)\s*$", re.MULTILINE)
SCHEDULER_EVENTS = C1_ROOT / "scheduler_events.jsonl"
CONTROLLER_MARKERS = (
    "resume_m05_campaign_batch0006_recovery0001.py",
    "resume_m05_campaign_batch0006_recovery0002_early_stages.py",
    "resume_m05_campaign_batch0006_recovery0002_guard0001.py",
    "resume_m05_campaign_batch0006_recovery0003_powerloss_concurrent.py",
    "resume_m05_campaign_batch0006_recovery0004_live_memory_dynamic.py",
    "resume_m05_campaign_batch0006_recovery0006_six_to_one_replan.py",
    "resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler.py",
    "resume_m05_campaign_batch0006_recovery0008_disk_admission.py",
    "run_m05_campaign_batch0006_continuation0001.py",
)

STAGE_LABELS = {
    "stage00_mergeable_smoke": "Stage00 smoke",
    "stage10_seven_family": "Stage10 seven-family",
    "stage20_proton": "Stage20 proton",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def human_bytes(value: int | float) -> str:
    number = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(number) < 1024 or unit == "TiB":
            return f"{number:.2f} {unit}"
        number /= 1024
    return f"{number:.2f} TiB"


def human_duration(seconds: float) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"


def bar(done: int, total: int, width: int = 28) -> str:
    fraction = 0.0 if total <= 0 else min(1.0, max(0.0, done / total))
    filled = int(fraction * width)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {fraction * 100:6.2f}%"


def mem_available() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def process_rows() -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    rss_total = 0
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            if not command or (
                not any(marker in command for marker in CONTROLLER_MARKERS)
                and "/bin/cosima" not in command
            ):
                continue
            status = (entry / "status").read_text(encoding="utf-8", errors="replace")
            match = re.search(r"^VmRSS:\s+(\d+) kB", status, re.MULTILINE)
            rss = int(match.group(1)) * 1024 if match else 0
            rss_total += rss
            rows.append({"pid": int(entry.name), "rss": rss, "command": command})
        except (OSError, ValueError):
            continue
    return sorted(rows, key=lambda row: row["pid"]), rss_total


def tail_progress(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 512 * 1024))
            matches = list(STORE_RE.finditer(handle.read()))
        if matches:
            return int(matches[-1].group(1))
    except OSError:
        pass
    return None


def source_event_total(path: Path) -> int | None:
    try:
        match = EVENTS_RE.search(path.read_text(encoding="utf-8"))
        return int(match.group(1)) if match else None
    except OSError:
        return None


def active_attempts() -> list[dict[str, Any]]:
    attempt_roots = (
        R6_ROOT / "attempts",
        R7_ROOT / "attempts",
        R8_ROOT / "attempts",
        C1_ROOT / "attempts",
    )
    candidates = sorted(
        (
            (root, path)
            for root in attempt_roots
            for path in root.glob("stage*/**/.attempt*.partial")
            if path.is_dir()
        ),
        key=lambda item: item[1].stat().st_mtime_ns,
    )
    active: list[dict[str, Any]] = []
    for attempt_root, directory in candidates:
        try:
            sources = list(directory.glob("*.source"))
            logs = list(directory.glob("*.log"))
            job_id = sources[0].stem if sources else directory.parent.name
            current = tail_progress(logs[0]) if logs else None
            total = source_event_total(sources[0]) if sources else None
            relative = directory.relative_to(attempt_root)
            stage, geometry, mode, family = relative.parts[:4]
            active.append(
                {
                    "job_id": job_id,
                    "stage": stage,
                    "geometry": geometry,
                    "mode": mode,
                    "family": family,
                    "event_current": current,
                    "event_total": total,
                    "bytes": sum(
                        path.stat().st_size for path in directory.rglob("*") if path.is_file()
                    ),
                }
            )
        except (OSError, ValueError, IndexError):
            # Attempts are atomically renamed at completion; a disappearing
            # directory during a refresh is normal.
            continue
    return active


def scheduler_status() -> dict[str, Any]:
    latest: dict[str, Any] = {}
    try:
        with SCHEDULER_EVENTS.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 256 * 1024))
            for raw_line in handle.read().splitlines():
                try:
                    event = json.loads(raw_line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if event.get("event") in {
                    "worker_launched", "worker_reaped_PASS", "scheduler_checkpoint", "launch_PAUSE"
                }:
                    latest = event
    except OSError:
        pass
    return latest


def continuation_status() -> dict[str, Any]:
    authority_path = C1_ROOT / "authority.json"
    authority = load_json(authority_path) if authority_path.is_file() else {}
    plan = authority.get("plan", [])
    phase_a = [job for job in plan if job.get("continuation_phase") == 1]
    gamma = [job for job in plan if job.get("continuation_phase") == 3]
    valid: dict[str, dict[str, Any]] = {}
    receipt_errors = 0
    latest: dict[str, Any] | None = None
    receipt_paths = list(C1_RECEIPTS.rglob("*.json")) if C1_RECEIPTS.exists() else []
    for path in sorted(receipt_paths, key=lambda item: item.stat().st_mtime_ns):
        try:
            receipt = load_json(path)
            job = receipt["job"]
        except (OSError, KeyError, json.JSONDecodeError):
            receipt_errors += 1
            continue
        if receipt.get("status") != "PASS" or receipt.get("errors"):
            receipt_errors += 1
            continue
        valid[str(job["job_id"])] = receipt
        latest = receipt

    phase_a_done = [job for job in phase_a if str(job["job_id"]) in valid]
    gamma_done = [job for job in gamma if str(job["job_id"]) in valid]
    checkpoint_path = C1_ROOT / "deweighting_precision_checkpoint.json"
    unlock_path = C1_ROOT / "gamma_unlock.json"
    checkpoint = load_json(checkpoint_path) if checkpoint_path.is_file() else {}
    unlock = load_json(unlock_path) if unlock_path.is_file() else {}
    return {
        "authority_published": authority_path.is_file(),
        "authority": authority,
        "phase_a_jobs": len(phase_a),
        "phase_a_done": len(phase_a_done),
        "phase_a_events": sum(int(job["events"]) for job in phase_a),
        "phase_a_events_done": sum(int(job["events"]) for job in phase_a_done),
        "gamma_jobs": len(gamma),
        "gamma_done": len(gamma_done),
        "gamma_events": sum(int(job["events"]) for job in gamma),
        "gamma_events_done": sum(int(job["events"]) for job in gamma_done),
        "checkpoint_status": checkpoint.get("status", "pending"),
        "gamma_unlock_status": unlock.get("status", "absent"),
        "gamma_locked": unlock.get("status") != "PASS__CONTINUATION0001_GAMMA_UNLOCK",
        "receipts": len(valid),
        "receipt_errors": receipt_errors,
        "latest": latest,
        "final_published": (C1_ROOT / "final_umbrella.json").is_file(),
    }


def snapshot() -> dict[str, Any]:
    contract = load_json(CONTRACT)
    mainline_state = load_json(MAINLINE_STATE) if MAINLINE_STATE.is_file() else {}
    state = load_json(STATE) if STATE.is_file() else mainline_state
    original_plan = contract["planned_jobs"]
    original_by_id = {job["job_id"]: job for job in original_plan}
    authority_path = R8_ROOT / "authority.json"
    authority = load_json(authority_path) if authority_path.is_file() else None
    r6_authority_path = R6_ROOT / "authority.json"
    r6_authority = load_json(r6_authority_path) if r6_authority_path.is_file() else None
    if authority:
        inherited_jobs = [
            original_by_id[row["job_id"]] for row in r6_authority["inherited_pass_manifest"]
        ]
        plan = inherited_jobs + authority["effective_pending_plan"]
    else:
        plan = original_plan
    planned: dict[str, dict[str, int]] = defaultdict(lambda: {"jobs": 0, "events": 0})
    for job in plan:
        planned[job["stage"]]["jobs"] += 1
        planned[job["stage"]]["events"] += int(job["events"])

    complete: dict[str, dict[str, int]] = defaultdict(lambda: {"jobs": 0, "events": 0})
    if authority:
        receipt_paths = [ROOT / row["path"] for row in r6_authority["inherited_pass_manifest"]]
        receipt_paths.extend(ROOT / row["path"] for row in authority["prior_pass_receipts"])
        receipt_paths.extend(R8_RECEIPTS.rglob("*.json"))
    else:
        receipt_paths = list(RECEIPTS.rglob("*.json"))
    receipt_paths = sorted(receipt_paths, key=lambda path: path.stat().st_mtime_ns)
    valid_receipts: list[dict[str, Any]] = []
    receipt_errors = 0
    for path in receipt_paths:
        try:
            receipt = load_json(path)
        except (OSError, json.JSONDecodeError):
            receipt_errors += 1
            continue
        if receipt.get("status") != "PASS" or receipt.get("errors"):
            receipt_errors += 1
            continue
        valid_receipts.append(receipt)
        stage = receipt["job"]["stage"]
        complete[stage]["jobs"] += 1
        complete[stage]["events"] += int(receipt["job"]["events"])

    active = active_attempts()
    continuation = continuation_status()
    scheduler = scheduler_status()
    continuation_policy = continuation["authority"].get("resource_policy", {})
    scheduler.setdefault(
        "minimum_target_workers",
        continuation_policy.get("minimum_target_workers", state.get("minimum_target_workers", 6)),
    )
    scheduler.setdefault(
        "absolute_worker_cap",
        continuation_policy.get("absolute_worker_cap", state.get("absolute_worker_cap", 10)),
    )
    scheduler.setdefault("active_workers", len(active))
    processes, process_rss = process_rows()
    now = datetime.now(timezone.utc)
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    deadline = datetime.fromisoformat(contract["wall_clock"]["deadline"])
    campaign_bytes = sum(path.stat().st_size for path in RUN_ROOT.rglob("*") if path.is_file())
    disk = shutil.disk_usage(RUN_ROOT)
    latest = valid_receipts[-1] if valid_receipts else None
    recovery_smoke = RUN_ROOT / "smoke_decision.recovery0001.json"
    recovery_final = R8_ROOT / "final_umbrella.json"
    cosima_count = sum("/bin/cosima" in row["command"] for row in processes)
    return {
        "now": now.isoformat(),
        "t0": t0.isoformat(),
        "deadline": deadline.isoformat(),
        "elapsed_s": (now - t0).total_seconds(),
        "remaining_s": (deadline - now).total_seconds(),
        "controller_alive": any(
            any(marker in row["command"] for marker in CONTROLLER_MARKERS)
            for row in processes
        ),
        "cosima_alive": cosima_count > 0,
        "cosima_count": cosima_count,
        "processes": processes,
        "process_rss": process_rss,
        "mem_available": mem_available(),
        "disk_free": disk.free,
        "campaign_bytes": campaign_bytes,
        "state": state,
        "mainline_state": mainline_state,
        "planned": dict(planned),
        "complete": {stage: complete[stage] for stage in planned},
        "receipts": len(valid_receipts),
        "receipt_errors": receipt_errors,
        "failed_attempts": (
            (len(list(FAILED.rglob("validation.json"))) if FAILED.exists() else 0)
            + (len(list(R6_FAILED.rglob("validation.json"))) if R6_FAILED.exists() else 0)
            + (len(list(R7_FAILED.rglob("validation.json"))) if R7_FAILED.exists() else 0)
            + (len(list(R8_FAILED.rglob("validation.json"))) if R8_FAILED.exists() else 0)
            + (len(list(C1_FAILED.rglob("validation.json"))) if C1_FAILED.exists() else 0)
        ),
        "active": active,
        "scheduler": scheduler,
        "latest": latest,
        "continuation": continuation,
        "smoke_authority_published": recovery_smoke.is_file(),
        "recovery_authority_published": authority_path.is_file(),
        "final_authority_published": recovery_final.is_file(),
    }


def render(data: dict[str, Any]) -> str:
    now = datetime.fromisoformat(data["now"]).astimezone()
    lines = [
        "M05 corrected-keV batch0006 — LIVE (read-only)",
        f"Updated: {now:%Y-%m-%d %H:%M:%S %Z}    refresh: live",
        "=" * 84,
        f"Controller: {'RUNNING' if data['controller_alive'] else 'NOT RUNNING'}    "
        f"Cosima: {('RUNNING (' + str(data['cosima_count']) + ' cores)') if data['cosima_alive'] else 'between shards / stopped'}    "
        f"Elapsed: {human_duration(data['elapsed_s'])}    Remaining: {human_duration(data['remaining_s'])}",
        f"State: {data['state'].get('status')}    Stage: {data['state'].get('stage')}    "
        f"Last error: {data['state'].get('last_error') or 'none'}",
        f"Namespace: {data['state'].get('recovery_id')}    "
        f"Mainline authority: {data['mainline_state'].get('status')}",
        "",
        "Mainline frozen progress (PASS receipts only):",
    ]
    total_jobs = total_events = done_jobs = done_events = 0
    for stage in STAGE_LABELS:
        planned = data["planned"].get(stage, {"jobs": 0, "events": 0})
        complete = data["complete"].get(stage, {"jobs": 0, "events": 0})
        total_jobs += planned["jobs"]
        total_events += planned["events"]
        done_jobs += complete["jobs"]
        done_events += complete["events"]
        lines.append(
            f"  {STAGE_LABELS[stage]:24s} {bar(complete['jobs'], planned['jobs'])}  "
            f"jobs {complete['jobs']:3d}/{planned['jobs']:3d}  events {complete['events']:,}/{planned['events']:,}"
        )
    lines.extend(
        [
            f"  {'Mainline frozen':24s} {bar(done_jobs, total_jobs)}  "
            f"jobs {done_jobs:3d}/{total_jobs:3d}  events {done_events:,}/{total_events:,}",
            "",
        ]
    )
    continuation = data["continuation"]
    gamma_gate = (
        f"UNLOCKED ({continuation['gamma_unlock_status']})"
        if not continuation["gamma_locked"]
        else f"LOCKED ({continuation['gamma_unlock_status']})"
    )
    lines.extend(
        [
            "Continuation0001 — append-only statistics:",
            f"  {'Phase A non-gamma':24s} "
            f"{bar(continuation['phase_a_done'], continuation['phase_a_jobs'])}  "
            f"jobs {continuation['phase_a_done']:2d}/{continuation['phase_a_jobs']:2d}  "
            f"events {continuation['phase_a_events_done']:,}/{continuation['phase_a_events']:,}",
            f"  De-weight checkpoint: {continuation['checkpoint_status']}",
            f"  Gamma gate: {gamma_gate}    "
            f"jobs {continuation['gamma_done']}/{continuation['gamma_jobs']}  "
            f"events {continuation['gamma_events_done']:,}/{continuation['gamma_events']:,}",
            "",
        ]
    )
    scheduler = data.get("scheduler", {})
    if scheduler:
        lines.extend(
            [
                f"Dynamic scheduler: active={scheduler.get('active_workers', data['cosima_count'])}  "
                f"minimum={scheduler.get('minimum_target_workers', '?')}  "
                f"cap={scheduler.get('absolute_worker_cap', '?')}  "
                f"paused={scheduler.get('paused', False)}  "
                f"reason={scheduler.get('pause_reason') or 'none'}",
                "",
            ]
        )
    active = data.get("active", [])
    if active:
        lines.append(f"Active shards ({len(active)}):")
        for attempt in active:
            if attempt["event_current"] is not None and attempt["event_total"]:
                event_text = (
                    f"{bar(attempt['event_current'], attempt['event_total'], 16)}  "
                    f"{attempt['event_current']:,}/{attempt['event_total']:,}"
                )
            else:
                event_text = "initializing / no event line yet"
            lines.extend(
                [
                    f"  {attempt['geometry']} / {attempt['mode']} / {attempt['family']} — "
                    f"{attempt['job_id']}",
                    f"    Events: {event_text}    output: {human_bytes(attempt['bytes'])}",
                ]
            )
        lines.append("")
    latest = data.get("latest")
    if latest:
        lines.extend(
            [
                "Latest PASS receipt:",
                f"  {latest['job']['job_id']} — events={latest['job']['events']:,}, "
                f"wall={latest['wall_s']:.1f}s, RSS={human_bytes(latest['peak_process_group_rss_bytes'])}, "
                f"TT={latest['isotope_dat'].get('TT_s')}s, errors={len(latest.get('errors', []))}",
                "",
            ]
        )
    continuation_latest = continuation.get("latest")
    if continuation_latest:
        lines.extend(
            [
                "Latest continuation PASS receipt:",
                f"  {continuation_latest['job']['job_id']} — "
                f"events={continuation_latest['job']['events']:,}, "
                f"wall={continuation_latest['wall_s']:.1f}s, "
                f"RSS={human_bytes(continuation_latest['peak_process_group_rss_bytes'])}",
                "",
            ]
        )
    lines.extend(
        [
            "Resources / authority:",
            f"  Campaign files: {human_bytes(data['campaign_bytes'])}    Disk free: {human_bytes(data['disk_free'])}",
            f"  Process RSS: {human_bytes(data['process_rss'])}    MemAvailable: {human_bytes(data['mem_available'])}",
            f"  PASS receipts: {data['receipts']}    malformed/non-PASS receipts: {data['receipt_errors']}    "
            f"preserved failed attempts: {data['failed_attempts']}",
            f"  Continuation PASS receipts: {continuation['receipts']}    "
            f"malformed/non-PASS: {continuation['receipt_errors']}",
            f"  recovery0001 smoke authority: {'PUBLISHED' if data['smoke_authority_published'] else 'pending'}    "
            f"  recovery0008 authority: {'PUBLISHED' if data['recovery_authority_published'] else 'pending'}    "
            f"recovery0008 final: {'PUBLISHED' if data['final_authority_published'] else 'pending'}",
            f"  continuation0001 authority: "
            f"{'PUBLISHED' if continuation['authority_published'] else 'pending'}    "
            f"continuation0001 final: {'PUBLISHED' if continuation['final_published'] else 'pending'}",
            "",
            "Ctrl-C closes this monitor only; it does NOT stop the campaign.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", type=float, default=0.0, metavar="SECONDS")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.watch < 0:
        parser.error("--watch must be nonnegative")
    while True:
        try:
            data = snapshot()
            output = json.dumps(data, indent=2, ensure_ascii=False) if args.json else render(data)
        except Exception as exc:
            output = f"M05 live monitor error: {type(exc).__name__}: {exc}"
        if args.watch:
            sys.stdout.write("\033[2J\033[H" + output + "\n")
            sys.stdout.flush()
            time.sleep(max(1.0, args.watch))
        else:
            print(output)
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
