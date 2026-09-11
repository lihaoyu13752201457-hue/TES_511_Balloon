#!/usr/bin/env python3
"""Read-only live terminal dashboard for the SF3 Plan-1 chain.

This is the SF3 counterpart of the retained M05 campaign monitor.  It reads
only small plans/configuration/receipts/authorities, the head and tail of an
*active* text log, Linux ``/proc`` counters, and filesystem usage.  It never
opens, stats for progress, decompresses, or hashes a SIM payload.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sf3_plan1_common import PROFILE_ID, RUN_ROOT


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PACKAGE_ROOT / "analysis_inputs.json"
INPUT_AUDIT = PACKAGE_ROOT / "outputs/00_input_audit/input_audit.json"
ACTIVATION_AUDIT = PACKAGE_ROOT / "audit/sf3_activation_validation.json"
TRANSPORT_AGGREGATE = PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"
FINAL_AUDIT = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"
CAMPAIGN_ID = "SF3_PLAN1_ONE_THIRD_TRANSPORT_V1_20260816"
CAMPAIGN_CONTRACT = RUN_ROOT / "campaign_contract.json"

STORE_RE = re.compile(rb"Storing event\s+(\d+)(?:\s+of\s+\d+)?")
LOG_TAIL_BYTES = 512 * 1024
LOG_HEAD_BYTES = 64 * 1024
PROJECTION_MARGIN = 1.02
AUXILIARY_OVERHEAD_BYTES = 500_000_000
DEFAULT_RESERVE_BYTES = 8 * 1024**3

PROCESS_LABELS = {
    "run_sf3_plan1.py": "transport controller",
    "validate_sf3_receipts.py": "receipt validation",
    "run_prompt_analysis.py": "prompt analysis",
    "build_sf3_activation.py": "activation/source build",
    "analyze_delayed_stage.py": "delayed analysis",
    "build_common_response.py": "common response",
    "build_matched_comparison.py": "matched comparison",
    "build_mission_stage.py": "mission/F3 fold",
    "finalize_sf3_plan1.py": "final audit",
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def sha256_small(path: Path, maximum_bytes: int = 16 * 1024**2) -> str:
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise RuntimeError(f"not a small hashable authority: {path} ({size} bytes)")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_bytes(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(number) < 1024.0 or unit == "TiB":
            return f"{number:.2f} {unit}"
        number /= 1024.0
    return f"{number:.2f} TiB"


def human_duration(value: float | None) -> str:
    if value is None or not math.isfinite(value) or value < 0:
        return "--:--:--"
    seconds = int(round(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def bar(done: int | float, total: int | float, width: int = 24) -> str:
    fraction = 0.0 if total <= 0 else min(1.0, max(0.0, float(done) / float(total)))
    filled = min(width, int(fraction * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {fraction * 100:6.2f}%"


def iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def read_plan(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            for key in ("ordinal", "shard", "events", "estimated_bytes", "seed"):
                row[key] = int(row[key])
            rows.append(row)
    return rows


def execution_exclusions(config: dict[str, Any]) -> dict[str, str]:
    raw = config.get("transport", {}).get("execution_exclusions", {})
    exclusions = {str(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}
    audit = load_json(ACTIVATION_AUDIT, {})
    if isinstance(audit, dict) and audit.get("status") == "PASS":
        for row in audit.get("source_cards", []):
            if str(row.get("source_status", "")).startswith("ZERO_SOURCE"):
                exclusions[str(row.get("job_id"))] = "ZERO_A15__NO_DELAYED_TRANSPORT"
    return exclusions


def load_receipts(
    receipt_root: Path, campaign_contract_sha256: str | None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    receipts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not receipt_root.is_dir():
        return receipts, errors
    # Canonical receipt JSONs are small.  No referenced artifact is touched.
    for path in sorted(receipt_root.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            errors.append(f"unreadable:{path.name}")
            continue
        job_id = str(payload.get("job_id") or path.stem)
        if payload.get("status") != "PASS" or payload.get("errors"):
            errors.append(f"non-PASS:{job_id}")
            continue
        if payload.get("campaign_id") != CAMPAIGN_ID:
            errors.append(f"wrong-campaign:{job_id}")
            continue
        if (
            campaign_contract_sha256 is None
            or payload.get("campaign_contract_sha256") != campaign_contract_sha256
        ):
            errors.append(f"contract-drift:{job_id}")
            continue
        receipts[job_id] = payload
    return receipts, errors


def meminfo() -> dict[str, int]:
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    result = {key: 0 for key in wanted}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key = line.split(":", 1)[0]
            if key in wanted:
                result[key] = int(line.split()[1]) * 1024
    except OSError:
        pass
    return result


def parse_proc_row(entry: Path, ticks: int) -> dict[str, Any] | None:
    try:
        raw = (entry / "stat").read_text(encoding="utf-8")
        fields = raw[raw.rfind(")") + 2 :].split()
        cmdline = (entry / "cmdline").read_bytes()
        args = [
            field.decode(errors="replace")
            for field in cmdline.split(b"\0")
            if field
        ]
        command = " ".join(args).strip()
        if not command:
            return None
        status = (entry / "status").read_text(encoding="utf-8", errors="replace")
        rss_match = re.search(r"^VmRSS:\s+(\d+) kB", status, re.MULTILINE)
        hwm_match = re.search(r"^VmHWM:\s+(\d+) kB", status, re.MULTILINE)
        return {
            "pid": int(entry.name),
            "pgrp": int(fields[2]),
            "cpu_s": (int(fields[11]) + int(fields[12])) / ticks,
            "start_ticks": int(fields[19]),
            "rss_bytes": int(rss_match.group(1)) * 1024 if rss_match else 0,
            "hwm_bytes": int(hwm_match.group(1)) * 1024 if hwm_match else 0,
            "command": command,
            "args": args,
            "cwd": os.readlink(entry / "cwd"),
        }
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, ValueError, IndexError):
        return None


def process_snapshot(plan: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        pid1 = Path("/proc/1/cmdline").read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
    except OSError:
        pid1 = ""
    host_pid_namespace_visible = not any(
        marker in pid1 for marker in ("--unshare-pid", "codex-linux-sandbox")
    )
    ticks = int(os.sysconf(os.sysconf_names["SC_CLK_TCK"]))
    try:
        uptime = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        uptime = 0.0
    rows: list[dict[str, Any]] = []
    try:
        entries = list(Path("/proc").glob("[0-9]*"))
    except OSError:
        entries = []
    for entry in entries:
        row = parse_proc_row(entry, ticks)
        if row is not None:
            rows.append(row)

    job_ids = [str(row["job_id"]) for row in plan]
    seed_rows: dict[str, list[dict[str, Any]]] = {job_id: [] for job_id in job_ids}
    cosima_pgrps: dict[str, set[int]] = {job_id: set() for job_id in job_ids}
    relevant: list[dict[str, Any]] = []
    controller_pids: list[int] = []
    external_controller_pids: list[int] = []
    unbound_sf3_cosima_pids: list[int] = []
    canonical_runner = str((PACKAGE_ROOT / "code/run_sf3_plan1.py").resolve())
    canonical_config_path = (PACKAGE_ROOT / "config").resolve()
    for row in rows:
        command = row["command"]
        args = [str(value) for value in row.get("args", [])]
        cwd = Path(str(row.get("cwd", "/")))
        labels = [label for marker, label in PROCESS_LABELS.items() if marker in command]
        runner_args = [Path(arg) for arg in args if Path(arg).name == "run_sf3_plan1.py"]
        if args and Path(args[0]).name.startswith("python") and runner_args:
            resolved_runners = {
                str((path if path.is_absolute() else cwd / path).resolve())
                for path in runner_args
            }
            if canonical_runner in resolved_runners:
                controller_pids.append(int(row["pid"]))
            else:
                external_controller_pids.append(int(row["pid"]))
        if labels or "/bin/cosima" in command:
            relevant.append({**row, "label": labels[0] if labels else "Cosima worker"})
        if "/bin/cosima" in command:
            matched = False
            source_args = [
                (Path(arg) if Path(arg).is_absolute() else cwd / arg).resolve()
                for arg in args
                if arg.endswith(".source")
            ]
            canonical_source = any(
                path == canonical_config_path or canonical_config_path in path.parents
                for path in source_args
            )
            if canonical_source:
                for job_id in job_ids:
                    if job_id in command:
                        cosima_pgrps[job_id].add(int(row["pgrp"]))
                        matched = True
                        break
            if not matched and any(
                "49_sf3_plan1_transport_20260816/config/" in path.as_posix()
                for path in source_args
            ):
                unbound_sf3_cosima_pids.append(int(row["pid"]))
    for job_id, groups in cosima_pgrps.items():
        if groups:
            seed_rows[job_id] = [row for row in rows if int(row["pgrp"]) in groups]

    jobs: dict[str, dict[str, Any]] = {}
    for job_id, members in seed_rows.items():
        if not members:
            continue
        cpu_s = sum(float(row["cpu_s"]) for row in members)
        earliest_start_ticks = min(int(row["start_ticks"]) for row in members)
        elapsed = max(0.001, uptime - earliest_start_ticks / ticks) if uptime else 0.001
        jobs[job_id] = {
            "pids": sorted(int(row["pid"]) for row in members),
            "cpu_s": cpu_s,
            "lifetime_cpu_percent": 100.0 * cpu_s / elapsed,
            "rss_bytes": sum(int(row["rss_bytes"]) for row in members),
            "hwm_bytes": sum(int(row["hwm_bytes"]) for row in members),
        }
    return {
        "jobs": jobs,
        "relevant": relevant,
        "host_pid_namespace_visible": host_pid_namespace_visible,
        "controller_alive": bool(controller_pids),
        "controller_pids": sorted(set(controller_pids)),
        "external_controller_pids": sorted(set(external_controller_pids)),
        "duplicate_controller": bool(external_controller_pids) or len(set(controller_pids)) > 1,
        "unbound_sf3_cosima_pids": sorted(set(unbound_sf3_cosima_pids)),
        "cosima_workers": len(jobs),
    }


def read_log_head(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            first = handle.read(LOG_HEAD_BYTES).splitlines()[0]
        payload = json.loads(first.decode("utf-8", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except (FileNotFoundError, OSError, IndexError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def parse_log_tail(raw: bytes) -> int | None:
    matches = list(STORE_RE.finditer(raw))
    return int(matches[-1].group(1)) if matches else None


def tail_progress(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - LOG_TAIL_BYTES))
            return parse_log_tail(handle.read())
    except OSError:
        return None


class RollingRates:
    """Keep short rolling rates without writing any monitor state to disk."""

    def __init__(self) -> None:
        self.events: dict[str, deque[tuple[float, int]]] = {}
        self.cpu: dict[str, deque[tuple[float, float]]] = {}
        self.sampled_peak: dict[str, int] = {}

    @staticmethod
    def _trim(values: deque[tuple[float, Any]], now: float, horizon: float = 45.0) -> None:
        while len(values) > 2 and now - values[0][0] > horizon:
            values.popleft()

    def event_rate(self, job_id: str, now: float, current: int, elapsed: float) -> float:
        values = self.events.setdefault(job_id, deque())
        values.append((now, current))
        self._trim(values, now)
        if len(values) >= 2 and values[-1][0] - values[0][0] >= 3.0:
            rate = (values[-1][1] - values[0][1]) / (values[-1][0] - values[0][0])
            if rate > 0:
                return rate
        return current / elapsed if current > 0 and elapsed > 0 else 0.0

    def cpu_percent(self, job_id: str, now: float, cpu_s: float, fallback: float) -> float:
        values = self.cpu.setdefault(job_id, deque())
        values.append((now, cpu_s))
        self._trim(values, now, 20.0)
        if len(values) >= 2 and values[-1][0] - values[0][0] >= 1.0:
            delta = values[-1][1] - values[0][1]
            if delta >= 0:
                return 100.0 * delta / (values[-1][0] - values[0][0])
        return fallback

    def peak(self, job_id: str, current_rss: int, hwm: int) -> int:
        value = max(current_rss, hwm, self.sampled_peak.get(job_id, 0))
        self.sampled_peak[job_id] = value
        return value


def active_attempts(
    plan: list[dict[str, Any]],
    receipts: dict[str, dict[str, Any]],
    run_root: Path,
    processes: dict[str, Any],
    rates: RollingRates,
    now_wall: datetime,
    now_mono: float,
) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    for job in plan:
        job_id = str(job["job_id"])
        if job_id in receipts:
            continue
        log = run_root / "jobs" / job_id / "active" / f"{job_id}.log"
        proc = processes["jobs"].get(job_id)
        if not log.is_file() and proc is None:
            continue
        header = read_log_head(log) if log.is_file() else {}
        started = iso_datetime(header.get("started_at"))
        elapsed = max(0.0, (now_wall - started).total_seconds()) if started else 0.0
        current = tail_progress(log) if log.is_file() else None
        total = int(job["events"])
        current = min(total, max(0, current)) if current is not None else None
        event_rate = (
            rates.event_rate(job_id, now_mono, current, elapsed)
            if current is not None
            else 0.0
        )
        eta = (total - current) / event_rate if current is not None and event_rate > 0 else None
        if proc:
            cpu_percent = rates.cpu_percent(
                job_id, now_mono, float(proc["cpu_s"]), float(proc["lifetime_cpu_percent"])
            )
            peak = rates.peak(job_id, int(proc["rss_bytes"]), int(proc["hwm_bytes"]))
        else:
            cpu_percent = 0.0
            peak = 0
        active.append(
            {
                "job_id": job_id,
                "stage": job["stage"],
                "mode": job["mode"],
                "family": job["family"],
                "events_current": current,
                "events_total": total,
                "event_rate": event_rate,
                "eta_s": eta,
                "elapsed_s": elapsed,
                "process_visible": proc is not None,
                "pids": proc["pids"] if proc else [],
                "cpu_percent": cpu_percent,
                "rss_bytes": int(proc["rss_bytes"]) if proc else 0,
                "peak_bytes": peak,
            }
        )
    return sorted(active, key=lambda row: row["job_id"])


def estimate_job_bytes(
    job: dict[str, Any], receipts: dict[str, dict[str, Any]], plan_by_id: dict[str, dict[str, Any]]
) -> int:
    same_cell: list[dict[str, Any]] = []
    for job_id, receipt in receipts.items():
        planned = plan_by_id.get(job_id)
        if planned is None or planned["stage"] != job["stage"]:
            continue
        if planned["mode"] == job["mode"] and planned["family"] == job["family"]:
            same_cell.append(receipt)
    if same_cell:
        total_bytes = sum(int(row.get("artifact_bytes", 0)) for row in same_cell)
        total_events = sum(int(row.get("events", 0)) for row in same_cell)
        if total_bytes > 0 and total_events > 0:
            return int(math.ceil(total_bytes / total_events * int(job["events"]) * PROJECTION_MARGIN))
    return int(math.ceil(int(job["estimated_bytes"]) * PROJECTION_MARGIN))


def disk_projection(
    plan: list[dict[str, Any]],
    receipts: dict[str, dict[str, Any]],
    active: list[dict[str, Any]],
    exclusions: dict[str, str],
    free_bytes: int,
    reserve_bytes: int,
) -> dict[str, Any]:
    active_by_id = {row["job_id"]: row for row in active}
    plan_by_id = {str(row["job_id"]): row for row in plan}
    pending_bytes = 0
    pending_jobs = 0
    for job in plan:
        job_id = str(job["job_id"])
        if job_id in exclusions or job_id in receipts:
            continue
        estimate = estimate_job_bytes(job, receipts, plan_by_id)
        attempt = active_by_id.get(job_id)
        if attempt and attempt["events_current"] is not None and int(job["events"]) > 0:
            remaining_fraction = 1.0 - attempt["events_current"] / int(job["events"])
            estimate = int(math.ceil(estimate * max(0.0, remaining_fraction)))
        pending_bytes += estimate
        pending_jobs += 1
    if pending_jobs:
        pending_bytes += AUXILIARY_OVERHEAD_BYTES
    projected = free_bytes - pending_bytes
    return {
        "free_bytes": free_bytes,
        "pending_estimated_bytes": pending_bytes,
        "pending_jobs": pending_jobs,
        "projected_final_free_bytes": projected,
        "reserve_bytes": reserve_bytes,
        "reserve_margin_bytes": projected - reserve_bytes,
        "pass": projected >= reserve_bytes,
        "method": "RECEIPTS_PLUS_ACTIVE_LOG_EVENT_FRACTION__NO_SIM_ACCESS",
    }


def pass_json(path: Path) -> bool:
    payload = load_json(path, {})
    return isinstance(payload, dict) and str(payload.get("status", "")).startswith("PASS")


def output_complete(directory: Path, primary: str, require_manifest: bool = True) -> bool:
    if not pass_json(directory / primary):
        return False
    return not require_manifest or (directory / "manifest.json").is_file()


def pipeline_stages(
    config: dict[str, Any],
    plan: list[dict[str, Any]],
    receipts: dict[str, dict[str, Any]],
    exclusions: dict[str, str],
) -> list[dict[str, Any]]:
    outputs = config.get("outputs", {})
    effective = [row for row in plan if str(row["job_id"]) not in exclusions]

    def transport_stage(stage: str) -> tuple[int, int, int, int]:
        rows = [row for row in effective if row["stage"] == stage]
        done = [row for row in rows if str(row["job_id"]) in receipts]
        return len(done), len(rows), sum(int(row["events"]) for row in done), sum(int(row["events"]) for row in rows)

    background = transport_stage("background")
    delayed = transport_stage("delayed")
    signal = transport_stage("signal")
    stage01 = Path(outputs.get("stage_01", PACKAGE_ROOT / "outputs/01_prompt"))
    stage02 = Path(outputs.get("stage_02", PACKAGE_ROOT / "outputs/02_activation"))
    stage03 = Path(outputs.get("stage_03", PACKAGE_ROOT / "outputs/03_delayed"))
    stage04 = Path(outputs.get("stage_04", PACKAGE_ROOT / "outputs/04_common_response"))
    stage05 = Path(outputs.get("stage_05", PACKAGE_ROOT / "outputs/05_matched_comparison"))
    stage06 = Path(outputs.get("stage_06", PACKAGE_ROOT / "outputs/06_mission"))
    stages = [
        {"label": "00 input/source audit", "done": pass_json(INPUT_AUDIT)},
        {"label": "01 SF3 background transport", "done": background[0] == background[1], "counts": background},
        {"label": "02 prompt raw analysis", "done": output_complete(stage01, "summary.json")},
        {"label": "03 activation + delayed sources", "done": output_complete(stage02, "day15_summary.json")},
        {"label": "04 SF3 delayed transport", "done": delayed[0] == delayed[1], "counts": delayed},
        {"label": "05 delayed raw analysis", "done": output_complete(stage03, "summary.json")},
        {"label": "06 SF3 full-envelope signal", "done": signal[0] == signal[1], "counts": signal},
        {"label": "07 common response / W2 / F3 input", "done": output_complete(stage04, "summary.json")},
        {"label": "08 matched SF3 vs frozen-S3d", "done": output_complete(stage05, "summary.json")},
        {"label": "09 20-day mission / F3", "done": output_complete(stage06, "summary.json", False)},
        {"label": "10 final audit + receipts", "done": pass_json(FINAL_AUDIT)},
    ]
    current_found = False
    for row in stages:
        if row["done"]:
            row["state"] = "DONE"
        elif not current_found:
            row["state"] = "RUN"
            current_found = True
        else:
            row["state"] = "WAIT"
    return stages


def stage_processes(processes: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[tuple[int, str]] = set()
    result: list[dict[str, Any]] = []
    for row in processes.get("relevant", []):
        label = str(row.get("label"))
        key = (int(row["pid"]), label)
        if key in seen or label == "Cosima worker":
            continue
        seen.add(key)
        result.append(row)
    return sorted(result, key=lambda row: int(row["pid"]))


def snapshot(rates: RollingRates) -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    if not isinstance(config, dict):
        raise RuntimeError(f"unreadable SF3 config: {CONFIG_PATH}")
    if config.get("profile_id") != PROFILE_ID:
        raise RuntimeError(
            f"SF3 dashboard profile drift: {config.get('profile_id')} != {PROFILE_ID}"
        )
    plan_path = Path(config["transport"]["job_plan"])
    run_root = Path(config["run_root"])
    if run_root.resolve() != RUN_ROOT.resolve():
        raise RuntimeError(f"non-canonical SF3 run root: {run_root}")
    plan = read_plan(plan_path)
    if len(plan) != 30:
        raise RuntimeError(f"SF3 plan must contain exactly 30 rows, got {len(plan)}")
    signal_rows = [row for row in plan if row.get("stage") == "signal"]
    if (
        len(signal_rows) != 1
        or signal_rows[0].get("job_id") != "signal_full_envelope_sf3"
        or int(signal_rows[0].get("events", 0)) != 37_194
    ):
        raise RuntimeError(f"SF3 exact signal row contract differs: {signal_rows}")
    campaign_contract = load_json(CAMPAIGN_CONTRACT, {})
    campaign_contract_sha256: str | None = None
    contract_error: str | None = None
    if (
        isinstance(campaign_contract, dict)
        and campaign_contract.get("status") == "PASS__SF3_CANONICAL_CAMPAIGN_CONTRACT"
        and campaign_contract.get("campaign_id") == CAMPAIGN_ID
    ):
        try:
            campaign_contract_sha256 = sha256_small(CAMPAIGN_CONTRACT)
        except Exception as exc:
            contract_error = str(exc)
    else:
        contract_error = "campaign contract not yet published or identity differs"
    receipts, receipt_errors = load_receipts(
        run_root / "receipts", campaign_contract_sha256,
    )
    exclusions = execution_exclusions(config)
    processes = process_snapshot(plan)
    now_wall = datetime.now(timezone.utc)
    now_mono = time.monotonic()
    active = active_attempts(plan, receipts, run_root, processes, rates, now_wall, now_mono)
    memory = meminfo()
    disk = shutil.disk_usage(run_root if run_root.exists() else PACKAGE_ROOT)
    reserve = int(config.get("transport", {}).get("dynamic_reserve_bytes", DEFAULT_RESERVE_BYTES))
    projection = disk_projection(plan, receipts, active, exclusions, disk.free, reserve)
    stages = pipeline_stages(config, plan, receipts, exclusions)
    effective_plan = [row for row in plan if str(row["job_id"]) not in exclusions]
    latest = None
    if receipts:
        latest = max(
            receipts.values(),
            key=lambda row: iso_datetime(row.get("ended_at")) or datetime.min.replace(tzinfo=timezone.utc),
        )
    aggregate = load_json(TRANSPORT_AGGREGATE, {})
    return {
        "updated_at": now_wall.isoformat(),
        "profile_id": config.get("profile_id"),
        "expected_profile_id": PROFILE_ID,
        "campaign_id": CAMPAIGN_ID,
        "campaign_contract_sha256": campaign_contract_sha256,
        "campaign_contract_error": contract_error,
        "run_root": str(run_root),
        "config": config,
        "plan": plan,
        "effective_jobs": len(effective_plan),
        "effective_events": sum(int(row["events"]) for row in effective_plan),
        "receipts": receipts,
        "receipt_errors": receipt_errors,
        "latest_receipt": latest,
        "exclusions": exclusions,
        "active": active,
        "processes": processes,
        "stage_processes": stage_processes(processes),
        "stages": stages,
        "memory": memory,
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "projection": projection,
        "aggregate_status": aggregate.get("status") if isinstance(aggregate, dict) else None,
    }


def render(data: dict[str, Any], refresh_seconds: float) -> str:
    updated = datetime.fromisoformat(data["updated_at"]).astimezone()
    memory = data["memory"]
    transport = data["config"].get("transport", {})
    headroom = int(transport.get("memory_headroom_bytes", 0))
    mem_available = int(memory.get("MemAvailable", 0))
    swap_total = int(memory.get("SwapTotal", 0))
    swap_free = int(memory.get("SwapFree", 0))
    stages = data["stages"]
    completed_stages = sum(bool(row["done"]) for row in stages)
    active = data["active"]
    total_cpu = sum(float(row["cpu_percent"]) for row in active)
    worker_count = int(data["processes"]["cosima_workers"])
    controller = "RUNNING" if data["processes"]["controller_alive"] else "not visible / between stages"
    singleton_ok = (
        data["processes"].get("host_pid_namespace_visible") is True
        and
        not data["processes"].get("duplicate_controller")
        and not data["processes"].get("unbound_sf3_cosima_pids")
    )
    lines = [
        "SF3 Plan 1 — LIVE READ-ONLY DASHBOARD",
        f"更新 {updated:%Y-%m-%d %H:%M:%S %Z} | refresh {refresh_seconds:g}s | Ctrl-C 只关闭仪表盘",
        "=" * 112,
        f"Controller: {controller} | Cosima workers: {worker_count} | sampled CPU: {total_cpu / 100.0:.2f} cores "
        f"| transport PASS receipts: {len(data['receipts'])}/{data['effective_jobs']}",
        f"Singleton: {'PASS' if singleton_ok else 'FAIL-CLOSED'} | controller PIDs "
        f"{data['processes'].get('controller_pids', [])} | external controller PIDs "
        f"{data['processes'].get('external_controller_pids', [])} | unbound SF3 Cosima PIDs "
        f"{data['processes'].get('unbound_sf3_cosima_pids', [])}",
        f"Host PID namespace visible: {data['processes'].get('host_pid_namespace_visible')} "
        "(False means controller/Cosima counts are not authoritative)",
        f"Campaign contract: {data.get('campaign_contract_sha256') or 'not yet published'}"
        + (f" | {data['campaign_contract_error']}" if data.get("campaign_contract_error") else ""),
        f"Full chain: {bar(completed_stages, len(stages), 32)}  stages {completed_stages}/{len(stages)}",
        "",
        "全链阶段（只以 PASS receipt / 原子发布的小型 authority 计完成）:",
    ]
    for stage in stages:
        token = {"DONE": "[OK]", "RUN": "[>>]", "WAIT": "[  ]"}[stage["state"]]
        suffix = ""
        if "counts" in stage:
            done_jobs, total_jobs, done_events, total_events = stage["counts"]
            suffix = f"  jobs {done_jobs}/{total_jobs}, events {done_events:,}/{total_events:,}"
        lines.append(f"  {token} {stage['label']:<38s}{suffix}")
    lines.append("")

    if active:
        finite_etas = [row["eta_s"] for row in active if row["eta_s"] is not None]
        wave_eta = max(finite_etas) if finite_etas else None
        lines.append(f"Active transport jobs ({len(active)}), current-wave ETA ≈ {human_duration(wave_eta)}:")
        for row in active:
            current = row["events_current"]
            total = row["events_total"]
            event_text = (
                f"{bar(current, total, 22)}  {current:,}/{total:,}"
                if current is not None
                else "[initializing / no Storing-event line yet]"
            )
            state = "RUN" if row["process_visible"] else "FINALIZING / process not visible"
            lines.append(
                f"  {row['job_id']}  ({row['mode']}/{row['family']})  {state}  elapsed {human_duration(row['elapsed_s'])}"
            )
            lines.append(
                f"    Events {event_text} | {row['event_rate']:.2f} evt/s | ETA {human_duration(row['eta_s'])}"
            )
            lines.append(
                f"    CPU {row['cpu_percent']:.1f}% | RSS {human_bytes(row['rss_bytes'])} | peak≥ {human_bytes(row['peak_bytes'])}"
                f" | PID {','.join(map(str, row['pids'])) or 'n/a'}"
            )
        lines.append("")
    else:
        lines.extend(["Active transport jobs: none (between stages / stopped)", ""])

    if data["stage_processes"]:
        process_text = ", ".join(
            f"{row['label']}[pid={row['pid']}, RSS={human_bytes(row['rss_bytes'])}]"
            for row in data["stage_processes"]
        )
        lines.extend([f"Visible controllers/post-processors: {process_text}", ""])

    projection = data["projection"]
    mem_margin = mem_available - headroom
    swap_used = max(0, swap_total - swap_free)
    lines.extend(
        [
            "Resources:",
            f"  RAM total {human_bytes(memory.get('MemTotal', 0))} | available {human_bytes(mem_available)} | "
            f"launch floor {human_bytes(headroom)} | floor margin {human_bytes(mem_margin)} "
            f"({'OK' if mem_margin >= 0 else 'LOW'})",
            f"  Swap used {human_bytes(swap_used)} / {human_bytes(swap_total)} | free {human_bytes(swap_free)}",
            f"  Disk free {human_bytes(data['disk']['free'])} | pending transport est. {human_bytes(projection['pending_estimated_bytes'])} "
            f"({projection['pending_jobs']} jobs)",
            f"  Projected final free {human_bytes(projection['projected_final_free_bytes'])} | reserve "
            f"{human_bytes(projection['reserve_bytes'])} | reserve margin {human_bytes(projection['reserve_margin_bytes'])} "
            f"({'PASS' if projection['pass'] else 'TIGHT'})",
        ]
    )
    latest = data.get("latest_receipt")
    if latest:
        lines.append(
            f"Latest PASS: {latest.get('job_id')} | wall {float(latest.get('wall_s', 0)):.1f}s | "
            f"peak RSS {human_bytes(int(latest.get('peak_process_group_rss_bytes', 0)))} | "
            f"artifact {human_bytes(int(latest.get('artifact_bytes', 0)))}"
        )
    if data["receipt_errors"]:
        lines.append("Receipt warnings: " + ", ".join(data["receipt_errors"]))
    lines.extend(
        [
            "",
            "I/O policy: small JSON/CSV + active .log head/tail + /proc + df; no .sim open, stat-for-progress, gzip scan, or hash.",
            f"Run root: {data['run_root']}",
        ]
    )
    return "\n".join(lines)


def self_test() -> None:
    assert human_bytes(1024) == "1.00 KiB"
    assert human_duration(3661) == "01:01:01"
    assert parse_log_tail(b"x\nStoring event 7 of 7\nStoring event 19 of 19\n") == 19
    assert parse_log_tail(b"no progress") is None
    assert "50.00%" in bar(1, 2)
    synthetic_plan = [
        {
            "job_id": "a",
            "stage": "background",
            "mode": "instant",
            "family": "gamma",
            "events": 100,
            "estimated_bytes": 1_000,
        },
        {
            "job_id": "b",
            "stage": "signal",
            "mode": "signal",
            "family": "focused_gamma",
            "events": 20,
            "estimated_bytes": 200,
        },
    ]
    projection = disk_projection(
        synthetic_plan,
        {},
        [{"job_id": "a", "events_current": 50}],
        {"b": "scope exclusion"},
        10_000_000_000,
        8_000_000_000,
    )
    assert projection["pending_jobs"] == 1
    assert projection["pending_estimated_bytes"] == 500_000_510
    assert projection["method"].endswith("NO_SIM_ACCESS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="render one snapshot and exit")
    parser.add_argument(
        "--refresh-seconds", type=float, default=2.0, metavar="SECONDS",
        help="TTY refresh interval (default: 2; minimum: 0.5)",
    )
    parser.add_argument("--json", action="store_true", help="emit the one-shot snapshot as JSON")
    parser.add_argument("--self-test", action="store_true", help="run pure-function tests and exit")
    args = parser.parse_args()
    if args.refresh_seconds < 0.5:
        parser.error("--refresh-seconds must be at least 0.5")
    if args.self_test:
        self_test()
        print("PASS watch_sf3_plan1 self-test")
        return 0
    rates = RollingRates()
    watch = not args.once and not args.json and sys.stdout.isatty()
    while True:
        try:
            data = snapshot(rates)
            output = (
                json.dumps(data, indent=2, ensure_ascii=False, default=str)
                if args.json
                else render(data, args.refresh_seconds)
            )
        except Exception as exc:  # Keep a read-only dashboard alive across atomic renames.
            output = f"SF3 dashboard snapshot error: {type(exc).__name__}: {exc}"
        if watch:
            sys.stdout.write("\033[2J\033[H" + output + "\n")
            sys.stdout.flush()
            try:
                time.sleep(args.refresh_seconds)
            except KeyboardInterrupt:
                sys.stdout.write("\nSF3 dashboard closed; campaign was not signalled.\n")
                return 0
        else:
            print(output)
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
