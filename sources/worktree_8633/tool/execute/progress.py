#!/usr/bin/env python3
"""Read-only terminal progress dashboard for the SG3B background run."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import canonical_receipt_path, load_bound_receipt, load_config, load_json, load_plan, meminfo


STORE_RE = re.compile(rb"Storing event\s+(\d+)(?:\s+of\s+\d+)?")
TAIL_BYTES = 512 * 1024


def human_bytes(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(number) < 1024 or unit == "TiB":
            return f"{number:.2f} {unit}"
        number /= 1024
    return f"{number:.2f} TiB"


def duration(value: float | None) -> str:
    if value is None or not math.isfinite(value) or value < 0:
        return "--:--:--"
    seconds = int(round(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def bar(done: int | float, total: int | float, width: int = 28) -> str:
    fraction = 0.0 if total <= 0 else min(1.0, max(0.0, float(done) / float(total)))
    filled = min(width, int(fraction * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {fraction * 100:6.2f}%"


def tail_event(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - TAIL_BYTES))
            matches = list(STORE_RE.finditer(handle.read()))
        return int(matches[-1].group(1)) if matches else None
    except OSError:
        return None


def started_at(path: Path) -> datetime | None:
    try:
        with path.open("rb") as handle:
            line = handle.readline()
        payload = json.loads(line.decode("utf-8", errors="replace"))
        value = payload.get("started_at")
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


class Rates:
    def __init__(self) -> None:
        self.samples: dict[str, deque[tuple[float, int]]] = {}

    def rate(self, job_id: str, now: float, current: int, elapsed: float) -> float:
        values = self.samples.setdefault(job_id, deque())
        values.append((now, current))
        while len(values) > 2 and now - values[0][0] > 45:
            values.popleft()
        if len(values) >= 2 and values[-1][0] - values[0][0] >= 3:
            value = (values[-1][1] - values[0][1]) / (values[-1][0] - values[0][0])
            if value > 0:
                return value
        return current / elapsed if current > 0 and elapsed > 0 else 0.0


def receipts(
    config: dict[str, Any],
    plan: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for job in plan:
        path = canonical_receipt_path(config, job["job_id"])
        if not path.is_file():
            continue
        try:
            payload = load_bound_receipt(config, job, require_artifacts=False)
        except Exception as exc:
            errors.append(f"{job['job_id']}: {exc}")
            continue
        if payload is not None:
            result[job["job_id"]] = payload
    return result, errors


def snapshot(config: dict[str, Any], plan: list[dict[str, Any]], rates: Rates) -> dict[str, Any]:
    run_root = Path(config["run_root"])
    state_path = run_root / "controller_state.json"
    state = load_json(state_path) if state_path.is_file() else {"status": "NOT_STARTED", "active": {}}
    done, receipt_errors = receipts(config, plan)
    active_rows: list[dict[str, Any]] = []
    now_wall = datetime.now(timezone.utc)
    now_mono = time.monotonic()
    active_state = state.get("active", {}) if isinstance(state.get("active"), dict) else {}
    for job in plan:
        job_id = job["job_id"]
        if job_id in done:
            continue
        log = run_root / "jobs" / job_id / "active" / f"{job_id}.log"
        if not log.is_file() and job_id not in active_state:
            continue
        current = tail_event(log) if log.is_file() else None
        current = max(0, min(int(job["events"]), current or 0))
        started = started_at(log) if log.is_file() else None
        elapsed = max(0.001, (now_wall - started).total_seconds()) if started else 0.001
        event_rate = rates.rate(job_id, now_mono, current, elapsed)
        remaining = max(0, int(job["events"]) - current)
        row_state = active_state.get(job_id, {}) if isinstance(active_state, dict) else {}
        active_rows.append({
            "job_id": job_id,
            "mode": job["mode"],
            "family": job["family"],
            "attempt": row_state.get("attempt"),
            "current": current,
            "total": int(job["events"]),
            "rate": event_rate,
            "eta_s": remaining / event_rate if event_rate > 0 else None,
            "elapsed_s": elapsed,
            "rss_bytes": row_state.get("rss_bytes"),
            "artifact_bytes": row_state.get("artifact_bytes"),
        })
    completed_events = sum(int(job["events"]) for job in plan if job["job_id"] in done)
    active_events = sum(row["current"] for row in active_rows)
    total_events = sum(int(job["events"]) for job in plan)
    memory = meminfo()
    return {
        "state": state,
        "done": done,
        "receipt_errors": receipt_errors,
        "active": active_rows,
        "completed_events": completed_events,
        "active_events": active_events,
        "total_events": total_events,
        "disk_free_bytes": shutil.disk_usage(run_root if run_root.exists() else Path.cwd()).free,
        "mem_available_bytes": memory["MemAvailable"],
        "swap_free_bytes": memory["SwapFree"],
    }


def render(config: dict[str, Any], plan: list[dict[str, Any]], snap: dict[str, Any]) -> str:
    state = snap["state"]
    done = snap["done"]
    current = snap["completed_events"] + snap["active_events"]
    lines = [
        f"{config['candidate']} corrected-keV background transport",
        f"status: {state.get('status', 'UNKNOWN')}    workers: {state.get('workers', config['workers'])}    "
        f"jobs: {len(done)}/{len(plan)}",
        f"events: {current:,}/{snap['total_events']:,} {bar(current, snap['total_events'])}",
        f"disk free: {human_bytes(snap['disk_free_bytes'])}    "
        f"MemAvailable: {human_bytes(snap['mem_available_bytes'])}    "
        f"SwapFree: {human_bytes(snap['swap_free_bytes'])}",
        "",
    ]
    if snap["active"]:
        lines.append("Active Cosima processes:")
        for row in snap["active"]:
            lines.append(
                f"  {row['job_id']:<38} a{row['attempt'] or '?'} "
                f"{bar(row['current'], row['total'], 20)} "
                f"{row['current']:,}/{row['total']:,}  "
                f"{row['rate']:.1f} ev/s  ETA {duration(row['eta_s'])}  "
                f"RSS {human_bytes(row['rss_bytes'])}"
            )
    else:
        lines.append("Active Cosima processes: none")
    pending = [job["job_id"] for job in plan if job["job_id"] not in done and not any(row["job_id"] == job["job_id"] for row in snap["active"])]
    lines.extend(["", f"Pending jobs: {len(pending)}"])
    if pending:
        lines.append("  " + ", ".join(pending[:5]) + (" ..." if len(pending) > 5 else ""))
    if state.get("error"):
        lines.extend(["", f"ERROR: {state['error']}"])
    if snap["receipt_errors"]:
        lines.extend(["", "INVALID RECEIPTS (not counted):"])
        lines.extend(f"  {message}" for message in snap["receipt_errors"][:4])
    lines.extend(["", "This dashboard reads logs/receipts only; it never scans or hashes SIM payloads."])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float)
    args = parser.parse_args()
    config = load_config(args.config)
    plan = load_plan(config)
    rates = Rates()
    interval = args.interval or float(config["progress_interval_seconds"])
    while True:
        snap = snapshot(config, plan, rates)
        if not args.once and sys.stdout.isatty():
            print("\033[2J\033[H", end="")
        print(render(config, plan, snap), flush=True)
        status = snap["state"].get("status")
        if args.once or status in ("COMPLETE", "FAILED"):
            return 0 if status != "FAILED" else 1
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
