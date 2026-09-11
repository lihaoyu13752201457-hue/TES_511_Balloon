#!/usr/bin/env python3
"""Resource-admitted, resumable Cosima controller for SF3 Plan 1."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import fcntl
import gzip
import json
import math
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sf3_plan1_common import (
    COSIMA,
    CPU_BUDGET,
    DYNAMIC_RESERVE_BYTES,
    MAX_ATTEMPTS,
    MAX_CPU_BUDGET,
    MEGALIB_ENV,
    PACKAGE_ROOT,
    PROFILE_ID,
    RUN_ROOT,
    SF3_SETUP,
    SOURCE_WORKTREE,
    START_FREE_GATE_BYTES,
    atomic_json,
    read_job_plan,
    sha256,
    utc_now,
    write_once_json,
)


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBS_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
SIM_GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$", re.MULTILINE)
SIM_SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$", re.MULTILINE)
POLL_SECONDS = 2.0
PROGRESS_SECONDS = 30.0
HANG_SECONDS = 20 * 60
MIN_MEMORY_HEADROOM_BYTES = 1_610_612_736  # user-authorized 1.5 GiB floor
MIN_AGGRESSIVE_SWAP_FREE_BYTES = 8 * 1024**3
DEFAULT_ADAPTIVE_MIN_WORKERS = 4
DEFAULT_ADAPTIVE_LIVE_TARGET_WORKERS = 6
MIN_EXTRA_WORKER_COOLDOWN_SECONDS = 30
DEFAULT_SIGNIFICANT_SWAP_PAGES_PER_SECOND = 2048.0  # 8 MiB/s at 4-KiB pages
DEFAULT_PSI_SOME_AVG10_LIMIT = 10.0
DEFAULT_PSI_FULL_AVG10_LIMIT = 2.0
PROJECTION_MARGIN = 1.02
AUXILIARY_OVERHEAD_BYTES = 500_000_000  # logs, DAT, compact catalogs, source tables
RSS_MULTIPLIER = {
    "gamma": 1.0,
    "n": 1.35,
    "p": 1.45,
    "alpha": 1.65,
    "eminus": 1.10,
    "eplus": 1.25,
    "muminus": 1.15,
    "muplus": 1.10,
    "focused_gamma": 1.05,
}
SIGNAL_SF3_JOB_ID = "signal_full_envelope_sf3"
SIGNAL_TRANSPORT_SCOPE = "FULL_ENVELOPE_SF3_ONLY"
SMALL_AUTHORITY_MAX_BYTES = 16 * 1024**2

_active_lock = threading.Lock()
_active: dict[str, dict[str, Any]] = {}
_stop = threading.Event()
_paging_lock = threading.Lock()
_paging_last_sample: tuple[float, int, int] | None = None
_paging_consecutive_high_intervals = 0


def package_path(value: str | Path, *, base: Path = PACKAGE_ROOT) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"{label} missing/empty: {path}")
    if path.stat().st_size > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"{label} is not a small JSON authority: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object: {path}")
    return payload


def configured_memory_headroom_bytes(config_path: Path | None = None) -> int:
    """Read the live launch headroom contract without caching it.

    The controller calls this for every RSS admission, so a future controller
    invocation uses the current small-table configuration.  The current
    process is never signalled or restarted by a configuration edit.  Values
    below the user-authorized 1.5-GiB floor fail closed.
    """
    path = (
        config_path.resolve()
        if config_path is not None
        else (PACKAGE_ROOT / "analysis_inputs.json").resolve()
    )
    config = load_small_json(path, "SF3 Plan-1 analysis config")
    transport = config.get("transport")
    if not isinstance(transport, dict):
        raise RuntimeError("analysis_inputs transport must be an object")
    value = transport.get("memory_headroom_bytes")
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError("transport.memory_headroom_bytes must be an integer")
    if value < MIN_MEMORY_HEADROOM_BYTES:
        raise RuntimeError(
            "transport.memory_headroom_bytes is below the authorized 1.5-GiB floor"
        )
    return value


def configured_adaptive_concurrency_policy(
    config_path: Path | None = None,
) -> dict[str, int | float]:
    """Read and validate the user-authorized adaptive six-worker policy.

    Workers one through three retain the bounded predicted-RSS policy.  Workers
    four through six use a live empirical-candidate check, with the same
    MemAvailable/swap/PSI guards and a mandatory observation interval before
    worker six.  This avoids letting stale cross-mode peak projections prevent
    the user-authorized four-worker floor while retaining every live guard.
    """
    path = (
        config_path.resolve()
        if config_path is not None
        else (PACKAGE_ROOT / "analysis_inputs.json").resolve()
    )
    config = load_small_json(path, "SF3 Plan-1 analysis config")
    transport = config.get("transport")
    if not isinstance(transport, dict):
        raise RuntimeError("analysis_inputs transport must be an object")

    integer_fields = {
        "adaptive_min_workers": DEFAULT_ADAPTIVE_MIN_WORKERS,
        "aggressive_min_swap_free_bytes": MIN_AGGRESSIVE_SWAP_FREE_BYTES,
        "significant_swap_pages_per_second": int(
            DEFAULT_SIGNIFICANT_SWAP_PAGES_PER_SECOND
        ),
    }
    parsed: dict[str, int | float] = {}
    for key, default in integer_fields.items():
        value = transport.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(f"transport.{key} must be an integer")
        parsed[key] = value
    required_integer_fields = (
        "adaptive_live_target_workers",
        "aggressive_extra_worker_cooldown_seconds",
    )
    for key in required_integer_fields:
        value = transport.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(f"transport.{key} must be an explicit integer")
        parsed[key] = value
    float_fields = {
        "memory_psi_some_avg10_limit": DEFAULT_PSI_SOME_AVG10_LIMIT,
        "memory_psi_full_avg10_limit": DEFAULT_PSI_FULL_AVG10_LIMIT,
    }
    for key, default in float_fields.items():
        value = transport.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"transport.{key} must be numeric")
        parsed[key] = float(value)

    if parsed["adaptive_min_workers"] != DEFAULT_ADAPTIVE_MIN_WORKERS:
        raise RuntimeError("transport.adaptive_min_workers must remain exactly 4")
    if parsed["adaptive_live_target_workers"] != DEFAULT_ADAPTIVE_LIVE_TARGET_WORKERS:
        raise RuntimeError("transport.adaptive_live_target_workers must remain exactly 6")
    if (
        parsed["aggressive_extra_worker_cooldown_seconds"]
        < MIN_EXTRA_WORKER_COOLDOWN_SECONDS
    ):
        raise RuntimeError(
            "transport.aggressive_extra_worker_cooldown_seconds must be at least 30"
        )
    if parsed["aggressive_min_swap_free_bytes"] < MIN_AGGRESSIVE_SWAP_FREE_BYTES:
        raise RuntimeError(
            "transport.aggressive_min_swap_free_bytes is below the 8-GiB floor"
        )
    if not (
        0 < parsed["significant_swap_pages_per_second"]
        <= DEFAULT_SIGNIFICANT_SWAP_PAGES_PER_SECOND
    ):
        raise RuntimeError(
            "significant swap-page rate must be positive and no weaker than default"
        )
    if (
        parsed["memory_psi_some_avg10_limit"] <= 0
        or parsed["memory_psi_full_avg10_limit"] <= 0
        or parsed["memory_psi_some_avg10_limit"] > DEFAULT_PSI_SOME_AVG10_LIMIT
        or parsed["memory_psi_full_avg10_limit"] > DEFAULT_PSI_FULL_AVG10_LIMIT
    ):
        raise RuntimeError("memory PSI limits must be positive and no weaker than default")
    return parsed


def execution_exclusions() -> dict[str, str]:
    config = json.loads((PACKAGE_ROOT / "analysis_inputs.json").read_text(encoding="utf-8"))
    raw = config.get("transport", {}).get("execution_exclusions", {})
    if not isinstance(raw, dict):
        raise RuntimeError("transport.execution_exclusions must be an object")
    exclusions = {str(key): str(value) for key, value in raw.items()}
    # W3 can legitimately produce a zero-activity family.  Its audit is the
    # launch authority: retain the planned row and finite-UL bookkeeping, but
    # never start an empty delayed source card.
    activation_gate = PACKAGE_ROOT / "audit/sf3_activation_validation.json"
    if activation_gate.is_file():
        payload = json.loads(activation_gate.read_text(encoding="utf-8"))
        if payload.get("status") == "PASS":
            for row in payload.get("source_cards", []):
                if str(row.get("source_status", "")).startswith("ZERO_SOURCE"):
                    exclusions[str(row["job_id"])] = (
                        "ZERO_A15__NO_DELAYED_TRANSPORT__FINITE_UPPER_LIMIT_ONLY"
                    )
    return exclusions


def configured_audit_path(
    config: dict[str, Any], key: str, default_name: str, *, config_root: Path
) -> Path:
    audits = config.get("audits") or {}
    if not isinstance(audits, dict):
        raise RuntimeError("analysis_inputs audits must be an object or null")
    value = audits.get(key, config_root / "audit" / default_name)
    return package_path(str(value), base=config_root)


def validate_signal_launch_gate(
    plan: list[dict[str, Any]], config_path: Path | None = None
) -> dict[str, Any]:
    """Fail closed before launching the only fresh SF3 signal transport."""
    config_path = (
        config_path.resolve()
        if config_path is not None
        else (PACKAGE_ROOT / "analysis_inputs.json").resolve()
    )
    config = load_small_json(config_path, "SF3 Plan-1 analysis config")
    config_root = config_path.parent
    signal_rows = [row for row in plan if row.get("stage") == "signal"]
    signal_ids = [str(row.get("job_id", "")) for row in signal_rows]
    if signal_ids != [SIGNAL_SF3_JOB_ID]:
        raise RuntimeError(f"signal plan is not exactly fresh SF3-only: {signal_ids}")
    row = signal_rows[0]
    if any(
        row.get(name) != value
        for name, value in (
            ("geometry", "SF3"), ("mode", "signal"), ("family", "focused_gamma")
        )
    ):
        raise RuntimeError("SF3 signal plan identity/geometry/mode/family differs")
    if Path(str(row["setup_path"])).resolve() != SF3_SETUP.resolve():
        raise RuntimeError("SF3 signal setup path differs from the frozen candidate setup")

    static_path = configured_audit_path(
        config,
        "signal_static",
        "full_envelope_signal_static_audit.json",
        config_root=config_root,
    )
    gate_path = configured_audit_path(
        config,
        "signal_transport_gate",
        "full_envelope_signal_transport_gate.json",
        config_root=config_root,
    )
    static = load_small_json(static_path, "SF3 signal static audit")
    gate = load_small_json(gate_path, "signal transport gate")
    if static.get("status") != "PASS__SF3_FULL_ENVELOPE_SIGNAL_STATIC_AUDIT":
        raise RuntimeError("SF3 signal static audit status differs")
    if static.get("rows") != 37_194 or static.get("geometry") != "SF3":
        raise RuntimeError("SF3 signal static row/geometry contract differs")
    if gate.get("status") != "PASS" or gate.get("transport_scope") != SIGNAL_TRANSPORT_SCOPE:
        raise RuntimeError("signal transport gate status/scope differs")
    if gate.get("permitted_signal_jobs") != [SIGNAL_SF3_JOB_ID]:
        raise RuntimeError("signal transport gate permitted jobs are not exactly SF3-only")
    authority = gate.get("authority") or {}
    if not isinstance(authority, dict):
        raise RuntimeError("signal gate static authority is malformed")
    declared_static = package_path(str(authority.get("path", "")), base=config_root)
    if declared_static != static_path:
        raise RuntimeError("signal gate static authority path binding differs")
    if authority.get("status") != static.get("status") or authority.get("sha256") != sha256(static_path):
        raise RuntimeError("signal gate does not bind the current PASS static audit")

    return {
        "status": "PASS__EXACT_SF3_ONLY_SIGNAL_LAUNCH_GATE",
        "signal_plan_ids": signal_ids,
        "effective_signal_job_ids": [SIGNAL_SF3_JOB_ID],
        "transport_gate": str(gate_path),
        "static_audit": str(static_path),
    }


def cast_row(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    for key in ("ordinal", "shard", "events", "s3d_histories", "target_histories", "seed", "estimated_bytes"):
        result[key] = int(row[key])
    for key in ("paired_seed_exception", "production_canary"):
        result[key] = row[key].strip().lower() == "true"
    return result


def load_plan() -> list[dict[str, Any]]:
    return [cast_row(row) for row in read_job_plan()]


def receipt_path(job_id: str) -> Path:
    return RUN_ROOT / "receipts" / f"{job_id}.json"


def load_receipt(job_id: str) -> dict[str, Any] | None:
    path = receipt_path(job_id)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError(f"non-PASS canonical receipt: {path}")
    if payload.get("job_id") != job_id:
        raise RuntimeError(f"canonical receipt job identity mismatch: {path}")
    attempt = payload.get("attempt")
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or attempt < 1
        or attempt > MAX_ATTEMPTS
    ):
        raise RuntimeError(f"canonical receipt attempt ordinal invalid: {path}")
    expected_attempt_dir = (
        RUN_ROOT / "jobs" / job_id / "attempts" / f"attempt{attempt:02d}"
    ).resolve()
    try:
        actual_attempt_dir = Path(str(payload["attempt_dir"])).resolve()
    except KeyError as exc:
        raise RuntimeError(f"canonical receipt lacks attempt_dir: {path}") from exc
    if actual_attempt_dir != expected_attempt_dir:
        raise RuntimeError(
            "canonical receipt is not bound to jobs/<id>/attempts/attemptNN "
            f"(interrupted/failed artifacts are ineligible): {path}"
        )
    source = Path(payload["source_path"])
    sim = Path(payload["sim_path"])
    log = Path(payload["log_path"])
    if sim.resolve() != (expected_attempt_dir / f"{job_id}.inc1.id1.sim.gz").resolve():
        raise RuntimeError(f"canonical receipt SIM path escapes its PASS attempt: {path}")
    if log.resolve() != (expected_attempt_dir / f"{job_id}.log").resolve():
        raise RuntimeError(f"canonical receipt log path escapes its PASS attempt: {path}")
    isotope_path = payload.get("isotope_dat_path")
    if payload.get("stage") == "background":
        expected_dat = (expected_attempt_dir / f"{job_id}.dat.inc1.dat").resolve()
        if isotope_path is None or Path(str(isotope_path)).resolve() != expected_dat:
            raise RuntimeError(f"canonical receipt DAT path escapes its PASS attempt: {path}")
    elif isotope_path is not None:
        raise RuntimeError(f"non-background canonical receipt unexpectedly names DAT: {path}")
    if not source.is_file() or sha256(source) != payload["source_sha256"]:
        raise RuntimeError(f"source provenance failed for {job_id}")
    artifacts = [(sim, "sim_bytes"), (log, "log_bytes")]
    if payload.get("isotope_dat_path"):
        artifacts.append((Path(payload["isotope_dat_path"]), "isotope_dat_bytes"))
    for artifact, key in artifacts:
        if not artifact.is_file() or artifact.stat().st_size != int(payload[key]):
            raise RuntimeError(f"artifact stat revalidation failed for {job_id}: {artifact}")
    # Deliberately no SIM digest or full gzip reopen here.
    return payload


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable unavailable")


def swap_free_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("SwapFree:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("SwapFree unavailable")


def _swap_page_counters() -> tuple[int, int]:
    counters: dict[str, int] = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] in {"pswpin", "pswpout"}:
            counters[fields[0]] = int(fields[1])
    if set(counters) != {"pswpin", "pswpout"}:
        raise RuntimeError("pswpin/pswpout unavailable")
    return counters["pswpin"], counters["pswpout"]


def _memory_psi_avg10() -> tuple[float, float]:
    values: dict[str, float] = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        for field in fields[1:]:
            if field.startswith("avg10="):
                values[fields[0]] = float(field.split("=", 1)[1])
                break
    if set(values) != {"some", "full"}:
        raise RuntimeError("memory PSI avg10 unavailable")
    return values["some"], values["full"]


def memory_pressure_snapshot(policy: dict[str, int | float]) -> dict[str, Any]:
    """Return live swap/PSI evidence for the optional sub-fourth-worker burst.

    A high swap rate must persist across two scheduler samples before the
    counter alone is called thrashing; PSI avg10 independently catches recent
    sustained memory stalls.  If the evidence sources cannot be read, only
    strict RSS admission remains available.
    """
    global _paging_last_sample, _paging_consecutive_high_intervals

    try:
        swap_free = swap_free_bytes()
        pswpin, pswpout = _swap_page_counters()
        psi_some, psi_full = _memory_psi_avg10()
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError):
        return {
            "evidence_available": False,
            "swap_free_bytes": None,
            "swap_pages_per_second": None,
            "consecutive_high_paging_intervals": None,
            "psi_some_avg10": None,
            "psi_full_avg10": None,
            "thrashing_detected": True,
        }

    now = time.monotonic()
    rate: float | None = None
    with _paging_lock:
        if _paging_last_sample is not None:
            previous_at, previous_in, previous_out = _paging_last_sample
            elapsed = now - previous_at
            if elapsed >= 1.0:
                delta_pages = max(0, pswpin - previous_in) + max(
                    0, pswpout - previous_out
                )
                rate = delta_pages / elapsed
                if rate >= float(policy["significant_swap_pages_per_second"]):
                    _paging_consecutive_high_intervals += 1
                else:
                    _paging_consecutive_high_intervals = 0
                _paging_last_sample = (now, pswpin, pswpout)
        else:
            _paging_last_sample = (now, pswpin, pswpout)
        high_intervals = _paging_consecutive_high_intervals

    thrashing = (
        high_intervals >= 2
        or psi_some >= float(policy["memory_psi_some_avg10_limit"])
        or psi_full >= float(policy["memory_psi_full_avg10_limit"])
    )
    return {
        "evidence_available": True,
        "swap_free_bytes": swap_free,
        "swap_pages_per_second": rate,
        "consecutive_high_paging_intervals": high_intervals,
        "psi_some_avg10": psi_some,
        "psi_full_avg10": psi_full,
        "thrashing_detected": thrashing,
    }


def process_group_metrics(pgid: int) -> tuple[float, int]:
    ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    cpu_ticks = 0
    rss = 0
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            if int(tail[2]) != pgid:  # state, ppid, pgrp
                continue
            cpu_ticks += int(tail[11]) + int(tail[12])
            for line in (entry / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    rss += int(line.split()[1]) * 1024
                    break
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, IndexError):
            continue
    return cpu_ticks / ticks, rss


def load_megalib_environment() -> dict[str, str]:
    command = [
        "/bin/bash", "--noprofile", "--norc", "-c",
        'source "$1" >/dev/null 2>&1 && env -0', "bash", str(MEGALIB_ENV),
    ]
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE)
    env: dict[str, str] = {}
    for field in result.stdout.split(b"\0"):
        if not field or b"=" not in field:
            continue
        key, value = field.split(b"=", 1)
        env[key.decode(errors="surrogateescape")] = value.decode(errors="surrogateescape")
    env["LC_ALL"] = "C"
    return env


def parse_dat(path: Path) -> dict[str, Any]:
    tt_values: list[float] = []
    rp_count = 0
    terminal_en = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            stripped = raw.strip()
            if stripped.startswith("TT "):
                tt_values.append(float(stripped.split()[1]))
            elif stripped.startswith("RP "):
                rp_count += 1
            elif stripped == "EN":
                terminal_en = True
    errors: list[str] = []
    if len(tt_values) != 1 or not math.isfinite(tt_values[0]) or tt_values[0] <= 0:
        errors.append(f"expected one positive TT, got {tt_values}")
    if not terminal_en:
        errors.append("isotope DAT lacks terminal EN")
    return {
        "TT_s": tt_values[0] if len(tt_values) == 1 else None,
        "RP_record_count": rp_count,
        "terminal_EN": terminal_en,
        "errors": errors,
    }


def read_sim_header(path: Path) -> dict[str, Any]:
    lines: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for _ in range(80):
            line = handle.readline()
            if not line:
                break
            lines.append(line)
            if line.startswith("SE"):
                break
    text = "".join(lines)
    geometry = SIM_GEOMETRY_RE.search(text)
    seed = SIM_SEED_RE.search(text)
    return {
        "geometry": geometry.group(1) if geometry else None,
        "seed": int(seed.group(1)) if seed else None,
        "header_bytes_uncompressed": len(text.encode("utf-8")),
        "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST",
    }


def artifact_paths(prefix: Path) -> tuple[Path, Path]:
    return (
        Path(f"{prefix}.inc1.id1.sim.gz"),
        Path(f"{prefix}.dat.inc1.dat"),
    )


def terminate_group(proc: subprocess.Popen[Any]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def validate_attempt(job: dict[str, Any], active_dir: Path, returncode: int, wall_s: float, peak_rss: int) -> dict[str, Any]:
    job_id = job["job_id"]
    prefix = active_dir / job_id
    sim, dat = artifact_paths(prefix)
    log = active_dir / f"{job_id}.log"
    source = Path(job["source_path"])
    errors: list[str] = []
    required_paths = [source, sim, log] + ([dat] if job["stage"] == "background" else [])
    for path in required_paths:
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"missing or empty artifact: {path}")
    log_scan: dict[str, Any] = {}
    dat_scan: dict[str, Any] = {}
    sim_header: dict[str, Any] = {}
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")
        generated = GENERATED_RE.search(text)
        cpu = CPU_RE.search(text)
        obs = OBS_RE.search(text)
        log_scan = {
            "generated_events": int(generated.group(1)) if generated else None,
            "beam_on_cpu_s": float(cpu.group(1)) if cpu else None,
            "observation_time_s": float(obs.group(1)) if obs else None,
            "graphics_terminal_marker": "Graphics systems deleted." in text,
            "visualization_terminal_marker": "Visualization Manager deleting" in text,
            "error_marker": any(marker in text for marker in ("***  Error", "Segmentation fault", "Unable to parse")),
        }
        if returncode != 0:
            errors.append(f"Cosima return code {returncode}")
        if log_scan["generated_events"] != job["events"]:
            errors.append(f"generated count {log_scan['generated_events']} != {job['events']}")
        if not log_scan["graphics_terminal_marker"] or log_scan["error_marker"]:
            errors.append("Cosima terminal/error marker gate failed")
    if job["stage"] == "background" and dat.is_file():
        dat_scan = parse_dat(dat)
        errors.extend(dat_scan["errors"])
        if dat_scan.get("TT_s") and log_scan.get("observation_time_s") and not math.isclose(
            float(dat_scan["TT_s"]), float(log_scan["observation_time_s"]), rel_tol=2e-3, abs_tol=2e-6
        ):
            errors.append("DAT TT differs from log observation time")
    elif job["stage"] != "background":
        dat_scan = {
            "TT_s": None,
            "RP_record_count": 0,
            "terminal_EN": None,
            "errors": [],
            "normalization": "NOT_APPLICABLE__DELAYED_USES_A15_PER_TRIGGER__SIGNAL_USES_FIXED_TRIALS",
        }
    if sim.is_file():
        try:
            sim_header = read_sim_header(sim)
            if Path(str(sim_header["geometry"])).resolve() != Path(job["setup_path"]).resolve():
                errors.append(f"SIM header geometry mismatch: {sim_header['geometry']}")
            if sim_header["seed"] != job["seed"]:
                errors.append(f"SIM header seed mismatch: {sim_header['seed']}")
        except Exception as exc:
            errors.append(f"SIM header read failed: {exc}")
    source_text = source.read_text(encoding="utf-8", errors="replace") if source.is_file() else ""
    if source_text.count(f"Geometry {job['setup_path']}") != 1:
        errors.append("source geometry mismatch")
    if source_text.count(f"Seed {job['seed']}") != 1:
        errors.append("source seed mismatch")
    count_token = ".Events" if job["stage"] == "background" else ".Triggers"
    if sum(line.strip().endswith(f"{count_token} {job['events']}") for line in source_text.splitlines()) != 1:
        errors.append(f"source {count_token} mismatch")
    if sum(
        line.strip().endswith(f".FileName {active_dir / job_id}")
        for line in source_text.splitlines()
    ) != 1:
        errors.append("source output prefix mismatch")
    if source_text.count("cosima_spectra_dp_2602units"):
        errors.append("legacy spectrum token in source")
    sim_bytes = sim.stat().st_size if sim.is_file() else 0
    dat_bytes = dat.stat().st_size if dat.is_file() else 0
    log_bytes = log.stat().st_size if log.is_file() else 0
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "profile_id": PROFILE_ID,
        "job_id": job_id,
        "stage": job["stage"],
        "geometry": job["geometry"],
        "mode": job["mode"],
        "family": job["family"],
        "events": job["events"],
        "seed": job["seed"],
        "source_path": str(source),
        "source_sha256": sha256(source) if source.is_file() else None,
        "setup_path": job["setup_path"],
        "returncode": returncode,
        "wall_s": wall_s,
        "peak_process_group_rss_bytes": peak_rss,
        "log": log_scan,
        "isotope_dat": dat_scan,
        "sim_header": sim_header,
        "sim_bytes": sim_bytes,
        "isotope_dat_bytes": dat_bytes,
        "log_bytes": log_bytes,
        "artifact_bytes": sim_bytes + dat_bytes + log_bytes,
        "bytes_per_event": (sim_bytes + dat_bytes + log_bytes) / job["events"] if job["events"] else None,
        "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
    }


def run_attempt(job: dict[str, Any], attempt: int, env: dict[str, str]) -> dict[str, Any]:
    job_id = job["job_id"]
    source = Path(job["source_path"])
    if not source.is_file():
        raise FileNotFoundError(source)
    job_root = RUN_ROOT / "jobs" / job_id
    active_dir = job_root / "active"
    if active_dir.exists():
        raise RuntimeError(f"stale active attempt must be audited manually: {active_dir}")
    active_dir.mkdir(parents=True)
    log = active_dir / f"{job_id}.log"
    command = [str(COSIMA), "-s", str(job["seed"]), str(source)]
    started_iso = utc_now()
    started = time.monotonic()
    peak_rss = 0
    watchdog = "completed"
    last_activity = started
    last_report = started
    last_cpu = 0.0
    last_bytes = 0
    with log.open("x", encoding="utf-8", buffering=1) as handle:
        handle.write(json.dumps({
            "job_id": job_id,
            "attempt": attempt,
            "source": str(source),
            "source_sha256": sha256(source),
            "setup": job["setup_path"],
            "events": job["events"],
            "seed": job["seed"],
            "started_at": started_iso,
            "command": command,
        }, sort_keys=True) + "\n")
        handle.flush()
        proc = subprocess.Popen(
            command,
            cwd=SOURCE_WORKTREE,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        with _active_lock:
            _active[job_id] = {
                "pid": proc.pid,
                "started": started,
                "rss": 0,
                "live_rss_samples": 0,
                "last_live_rss_sample_at": None,
                "bytes": 0,
                "estimate": job["estimated_bytes"],
                "family": job["family"],
            }
        while proc.poll() is None:
            time.sleep(POLL_SECONDS)
            cpu, rss = process_group_metrics(proc.pid)
            peak_rss = max(peak_rss, rss)
            current_bytes = sum(path.stat().st_size for path in active_dir.iterdir() if path.is_file())
            if cpu > last_cpu or current_bytes > last_bytes:
                last_activity = time.monotonic()
            last_cpu, last_bytes = cpu, current_bytes
            with _active_lock:
                if job_id in _active:
                    _active[job_id].update(
                        rss=rss,
                        bytes=current_bytes,
                        cpu_s=cpu,
                        live_rss_samples=int(
                            _active[job_id].get("live_rss_samples", 0)
                        ) + 1,
                        last_live_rss_sample_at=time.monotonic(),
                    )
            if time.monotonic() - last_report >= PROGRESS_SECONDS:
                print(json.dumps({
                    "event": "job_progress", "job_id": job_id,
                    "elapsed_s": time.monotonic() - started, "cpu_s": cpu,
                    "rss_bytes": rss, "peak_rss_bytes": peak_rss,
                    "artifact_bytes_so_far": current_bytes,
                    "free_disk_bytes": shutil.disk_usage(RUN_ROOT).free,
                    "mem_available_bytes": mem_available_bytes(),
                }, sort_keys=True), flush=True)
                last_report = time.monotonic()
            reason = None
            if _stop.is_set():
                reason = "controller_stop_requested"
            elif shutil.disk_usage(RUN_ROOT).free < DYNAMIC_RESERVE_BYTES:
                reason = "dynamic_8GiB_reserve_breached"
            elif mem_available_bytes() < 384 * 1024**2:
                reason = "hard_low_memory_384MiB"
            elif time.monotonic() - last_activity > HANG_SECONDS:
                reason = "watchdog_no_cpu_or_growth_20m"
            if reason:
                watchdog = reason
                terminate_group(proc)
                break
        returncode = proc.wait()
        with _active_lock:
            _active.pop(job_id, None)
        wall_s = time.monotonic() - started
        handle.write(
            f"watchdog_reason={watchdog}\npeak_process_group_rss_bytes={peak_rss}\n"
            f"returncode={returncode}\nwall_s={wall_s:.6f}\n"
        )
    result = validate_attempt(job, active_dir, returncode, wall_s, peak_rss)
    result.update({
        "attempt": attempt,
        "started_at": started_iso,
        "ended_at": utc_now(),
        "watchdog_reason": watchdog,
    })
    if result["status"] == "PASS":
        final = job_root / "attempts" / f"attempt{attempt:02d}"
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            raise RuntimeError(f"attempt destination exists: {final}")
        os.replace(active_dir, final)
        result["attempt_dir"] = str(final)
        result["sim_path"] = str(final / f"{job_id}.inc1.id1.sim.gz")
        result["isotope_dat_path"] = (
            str(final / f"{job_id}.dat.inc1.dat") if job["stage"] == "background" else None
        )
        result["log_path"] = str(final / f"{job_id}.log")
        write_once_json(receipt_path(job_id), result)
    else:
        final = job_root / "failed" / f"attempt{attempt:02d}"
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(active_dir, final)
        result["attempt_dir"] = str(final)
        write_once_json(final / "validation.json", result)
    resource_log = RUN_ROOT / "resource_metrics.jsonl"
    resource_log.parent.mkdir(parents=True, exist_ok=True)
    with resource_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "at": utc_now(), "job_id": job_id, "attempt": attempt,
            "status": result["status"], "wall_s": wall_s, "peak_rss": peak_rss,
            "artifact_bytes": result["artifact_bytes"], "free_bytes": shutil.disk_usage(RUN_ROOT).free,
        }, sort_keys=True) + "\n")
    return result


def used_attempt_ordinals(job_id: str, *, run_root: Path | None = None) -> set[int]:
    """Count only runner-finalized PASS/FAIL attempts, never interruptions.

    A controller/GUI interruption is environmental rather than a completed
    Cosima attempt.  Recovery material lives under ``jobs/*/interrupted`` and
    therefore cannot consume either registered retry ordinal.
    """
    job_root = (run_root if run_root is not None else RUN_ROOT) / "jobs" / job_id
    used: set[int] = set()
    for parent in (job_root / "attempts", job_root / "failed"):
        if not parent.is_dir():
            continue
        for path in parent.iterdir():
            match = re.fullmatch(r"attempt(\d+)", path.name)
            if path.is_dir() and match:
                used.add(int(match.group(1)))
    return used


def next_attempt_ordinal(job_id: str) -> int | None:
    used = used_attempt_ordinals(job_id)
    return next((attempt for attempt in range(1, MAX_ATTEMPTS + 1) if attempt not in used), None)


def failed_peak_rss_bytes(validation: dict[str, Any]) -> int | None:
    """Accept both interrupted-recovery and ordinary runner validation schemas."""
    observed: list[int] = []
    for key in (
        "peak_process_group_rss_bytes_observed",
        "peak_process_group_rss_bytes",
    ):
        value = validation.get(key)
        if value is None:
            continue
        parsed = int(value)
        if parsed >= 0:
            observed.append(parsed)
    return max(observed) if observed else None


def ensure_job(job: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Run at most one attempt under the admission that scheduled this call.

    A failed attempt is returned to the controller.  It must leave the worker
    and re-enter disk/RSS admission before the same registered seed may use the
    next ordinal.  This prevents a resource-watchdog failure from immediately
    launching attempt 2 inside an already-admitted worker.
    """
    existing = load_receipt(job["job_id"])
    if existing is not None:
        return existing
    attempt = next_attempt_ordinal(job["job_id"])
    if attempt is None:
        raise RuntimeError(f"{job['job_id']} exhausted both allowed attempts")
    result = run_attempt(job, attempt, env)
    print(json.dumps({
        "event": "attempt_complete", "job_id": job["job_id"], "attempt": attempt,
        "status": result["status"], "wall_s": result["wall_s"],
        "peak_rss": result["peak_process_group_rss_bytes"],
        "artifact_bytes": result["artifact_bytes"], "errors": result["errors"],
        "retry_requires_fresh_admission": (
            result["status"] != "PASS" and next_attempt_ordinal(job["job_id"]) is not None
        ),
    }, sort_keys=True), flush=True)
    return result


def calibrated_estimate(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    receipts = [load_receipt(row["job_id"]) for row in plan if row["stage"] == job["stage"]]
    same_cell = [
        receipt for receipt in receipts if receipt is not None
        and receipt["mode"] == job["mode"] and receipt["family"] == job["family"]
    ]
    if same_cell:
        total_bytes = sum(int(receipt["artifact_bytes"]) for receipt in same_cell)
        total_events = sum(int(receipt["events"]) for receipt in same_cell)
        return int(math.ceil(total_bytes / total_events * job["events"] * PROJECTION_MARGIN))
    return int(math.ceil(job["estimated_bytes"] * PROJECTION_MARGIN))


def projection(plan: list[dict[str, Any]]) -> dict[str, Any]:
    active_snapshot: dict[str, dict[str, Any]]
    with _active_lock:
        active_snapshot = {key: dict(value) for key, value in _active.items()}
    pending = []
    total = 0
    exclusions = execution_exclusions()
    for job in plan:
        if job["job_id"] in exclusions:
            continue
        if load_receipt(job["job_id"]) is not None:
            continue
        estimate = calibrated_estimate(job, plan)
        produced = int(active_snapshot.get(job["job_id"], {}).get("bytes", 0))
        remaining = max(0, estimate - produced)
        total += remaining
        pending.append({"job_id": job["job_id"], "remaining_estimated_bytes": remaining})
    if pending:
        total += AUXILIARY_OVERHEAD_BYTES
    free = shutil.disk_usage(RUN_ROOT if RUN_ROOT.exists() else PACKAGE_ROOT).free
    return {
        "free_bytes": free,
        "pending_estimated_bytes": total,
        "auxiliary_overhead_bytes": AUXILIARY_OVERHEAD_BYTES if pending else 0,
        "projected_final_free_bytes": free - total,
        "reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "pass": free - total >= DYNAMIC_RESERVE_BYTES,
        "pending_jobs": len(pending),
        "excluded_jobs": exclusions,
    }


def canary_receipt(plan: list[dict[str, Any]]) -> dict[str, Any] | None:
    canaries = [row for row in plan if row["production_canary"]]
    if len(canaries) != 1:
        raise RuntimeError("plan must contain exactly one production canary")
    return load_receipt(canaries[0]["job_id"])


def candidate_rss(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    canary = canary_receipt(plan)
    if canary is None:
        return 900 * 1024**2
    base = int(canary["peak_process_group_rss_bytes"])
    # The production canary is the initial admission authority.  Once real
    # jobs from the same particle family have completed, do not keep admitting
    # against a lower canary-only ceiling: retain 5% above the largest observed
    # process-group peak.  Receipts are stat-checked only; SIM payloads are not
    # reopened or hashed here.
    observed_peaks = []
    for row in plan:
        if row["family"] != job["family"]:
            continue
        receipt = load_receipt(row["job_id"])
        if receipt is not None:
            observed_peaks.append(int(receipt["peak_process_group_rss_bytes"]))
        failed_root = RUN_ROOT / "jobs" / row["job_id"] / "failed"
        if failed_root.is_dir():
            for validation_path in sorted(failed_root.glob("attempt*/validation.json")):
                validation = json.loads(validation_path.read_text(encoding="utf-8"))
                observed = failed_peak_rss_bytes(validation)
                if observed is not None:
                    observed_peaks.append(int(observed))
    observed_budget = max(observed_peaks, default=0) * 1.05
    return int(max(
        512 * 1024**2,
        base * RSS_MULTIPLIER.get(job["family"], 1.25),
        observed_budget,
    ))


def adaptive_memory_decision(
    *,
    predicted_growth_bytes: int,
    candidate_rss_budget_bytes: int,
    mem_available: int,
    headroom: int,
    scheduled_workers: int,
    pressure: dict[str, Any],
    policy: dict[str, int | float],
    extra_worker_live_age_seconds: float | None = None,
    extra_worker_has_live_rss_sample: bool = False,
) -> dict[str, Any]:
    """Apply bounded predicted RSS to three workers and live RSS to four-six.

    Workers one through three preserve the prior predicted-growth behavior.
    Workers four through six deliberately do not sum hypothetical future peaks of
    already-running processes: MemAvailable already reflects their live RSS.
    They instead reserve only the empirical RSS budget for the new candidate,
    while retaining the exact 1.5-GiB post-launch floor, 8-GiB SwapFree floor,
    and no-thrashing guards.  Worker six additionally requires at least one
    live RSS sample from worker five after the configured observation window.
    """
    if predicted_growth_bytes < 0 or candidate_rss_budget_bytes < 0:
        raise RuntimeError("RSS admission budgets must be non-negative")
    strict_capacity = max(0, mem_available - headroom)
    strict_pass = (
        mem_available >= headroom
        and predicted_growth_bytes <= strict_capacity
    )
    worker_ordinal = scheduled_workers + 1
    minimum_target = int(policy["adaptive_min_workers"])
    predicted_rss_worker_limit = minimum_target - 1
    live_target = int(policy["adaptive_live_target_workers"])
    cooldown_seconds = int(policy["aggressive_extra_worker_cooldown_seconds"])
    swap_floor = int(policy["aggressive_min_swap_free_bytes"])
    swap_free = pressure.get("swap_free_bytes")
    swap_burst_capacity = (
        max(0, int(swap_free) - swap_floor)
        if pressure.get("evidence_available") and swap_free is not None
        else 0
    )
    aggressive_eligible = worker_ordinal <= predicted_rss_worker_limit
    live_burst_guards_pass = (
        aggressive_eligible
        and mem_available >= headroom
        and pressure.get("evidence_available") is True
        and swap_free is not None
        and int(swap_free) >= swap_floor
        and pressure.get("thrashing_detected") is False
    )
    aggressive_capacity = strict_capacity + swap_burst_capacity
    aggressive_pass = (
        not strict_pass
        and live_burst_guards_pass
        and predicted_growth_bytes <= aggressive_capacity
    )

    extra_eligible = predicted_rss_worker_limit < worker_ordinal <= live_target
    post_launch_mem_available = mem_available - candidate_rss_budget_bytes
    extra_live_guards_pass = (
        extra_eligible
        and post_launch_mem_available >= headroom
        and pressure.get("evidence_available") is True
        and swap_free is not None
        and int(swap_free) >= swap_floor
        and pressure.get("thrashing_detected") is False
    )
    cooldown_required = worker_ordinal > minimum_target + 1
    cooldown_pass = (
        not cooldown_required
        or (
            extra_worker_has_live_rss_sample
            and extra_worker_live_age_seconds is not None
            and extra_worker_live_age_seconds >= cooldown_seconds
        )
    )
    extra_live_pass = extra_live_guards_pass and cooldown_pass

    if worker_ordinal <= predicted_rss_worker_limit:
        passed = strict_pass or aggressive_pass
        if strict_pass:
            admission_mode = "STRICT_PREDICTED_RSS"
        elif aggressive_pass:
            admission_mode = "PREDICTED_RSS_SLOT_1_TO_3__BOUNDED_BY_SWAP_SURPLUS"
        else:
            admission_mode = "PREDICTED_RSS_SLOT_1_TO_3_GUARDS_OR_BUDGET_REJECTED"
    elif extra_live_pass:
        passed = True
        admission_mode = (
            f"ADAPTIVE_LIVE_EXTRA_WORKER_{worker_ordinal}"
            "__EMPIRICAL_CANDIDATE_RSS"
        )
    elif not extra_eligible:
        passed = False
        admission_mode = "ADAPTIVE_LIVE_TARGET_SIX_EXCEEDED__REJECTED"
    elif not cooldown_pass:
        passed = False
        admission_mode = "WORKER_6_LIVE_RSS_COOLDOWN_PENDING__REJECTED"
    else:
        passed = False
        admission_mode = "EXTRA_WORKER_LIVE_FLOOR_SWAP_OR_PSI_GUARD_REJECTED"
    return {
        "pass": passed,
        "admission_mode": admission_mode,
        "worker_ordinal": worker_ordinal,
        "adaptive_min_workers": minimum_target,
        "predicted_rss_worker_limit": predicted_rss_worker_limit,
        "adaptive_live_target_workers": live_target,
        "strict_capacity_bytes": strict_capacity,
        "strict_pass": strict_pass,
        "predicted_growth_bytes": predicted_growth_bytes,
        "predicted_overcommit_bytes": max(
            0, predicted_growth_bytes - strict_capacity
        ),
        "aggressive_eligible": aggressive_eligible,
        "live_burst_guards_pass": live_burst_guards_pass,
        "swap_burst_capacity_bytes": swap_burst_capacity,
        "aggressive_capacity_bytes": aggressive_capacity,
        "aggressive_pass": aggressive_pass,
        "candidate_rss_budget_bytes": candidate_rss_budget_bytes,
        "post_launch_mem_available_bytes": post_launch_mem_available,
        "extra_worker_eligible": extra_eligible,
        "extra_worker_live_guards_pass": extra_live_guards_pass,
        "extra_worker_cooldown_required": cooldown_required,
        "extra_worker_cooldown_seconds": cooldown_seconds,
        "extra_worker_live_age_seconds": extra_worker_live_age_seconds,
        "extra_worker_has_live_rss_sample": extra_worker_has_live_rss_sample,
        "extra_worker_cooldown_pass": cooldown_pass,
        "extra_worker_live_pass": extra_live_pass,
    }


def memory_admission(
    job: dict[str, Any], plan: list[dict[str, Any]], scheduled: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    with _active_lock:
        active_snapshot = {key: dict(value) for key, value in _active.items()}
    scheduled = scheduled or []
    active_rss = sum(int(row.get("rss", 0)) for row in active_snapshot.values())
    active_growth = 0
    for active_job in scheduled:
        observed = int(active_snapshot.get(active_job["job_id"], {}).get("rss", 0))
        active_growth += max(0, candidate_rss(active_job, plan) - observed)
    candidate = candidate_rss(job, plan)
    available = mem_available_bytes()
    headroom = configured_memory_headroom_bytes()
    concurrency_policy = configured_adaptive_concurrency_policy()
    pressure = memory_pressure_snapshot(concurrency_policy)
    minimum_target = int(concurrency_policy["adaptive_min_workers"])
    extra_worker_has_live_rss_sample = False
    extra_worker_live_age_seconds: float | None = None
    # For the sixth slot, worker five is the first scheduled row beyond the
    # retained four-worker target.  Require a real /proc RSS observation from
    # that process after the full cooldown; merely submitting its Future is
    # insufficient authority for another launch.
    if len(scheduled) > minimum_target:
        worker_five = scheduled[minimum_target]
        worker_five_state = active_snapshot.get(worker_five["job_id"], {})
        started_at = worker_five_state.get("started")
        sampled_at = worker_five_state.get("last_live_rss_sample_at")
        sample_count = int(worker_five_state.get("live_rss_samples", 0))
        if (
            sample_count > 0
            and isinstance(started_at, (int, float))
            and isinstance(sampled_at, (int, float))
        ):
            extra_worker_has_live_rss_sample = True
            extra_worker_live_age_seconds = max(0.0, sampled_at - started_at)
    # MemAvailable already excludes current active RSS.  Reserve only each
    # scheduled worker's not-yet-realized growth for slots one through three.
    # Slots four through six use candidate alone inside adaptive_memory_decision.
    decision = adaptive_memory_decision(
        predicted_growth_bytes=active_growth + candidate,
        candidate_rss_budget_bytes=candidate,
        mem_available=available,
        headroom=headroom,
        scheduled_workers=len(scheduled),
        pressure=pressure,
        policy=concurrency_policy,
        extra_worker_live_age_seconds=extra_worker_live_age_seconds,
        extra_worker_has_live_rss_sample=extra_worker_has_live_rss_sample,
    )
    return {
        **decision,
        "mem_available_bytes": available,
        "active_rss_bytes": active_rss,
        "active_reserved_growth_bytes": active_growth,
        "candidate_rss_budget_bytes": candidate,
        "headroom_bytes": headroom,
        "memory_pressure": pressure,
    }


def launch_admission(
    job: dict[str, Any],
    plan: list[dict[str, Any]],
    scheduled: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    disk = projection(plan)
    memory = memory_admission(job, plan, scheduled)
    if not disk["pass"]:
        blocked = {"kind": "DYNAMIC_DISK_RESERVE", "disk": disk}
    elif not memory["pass"]:
        blocked = {"kind": "DYNAMIC_RSS_ADMISSION", "memory": memory}
    else:
        blocked = None
    return {
        "pass": blocked is None,
        "disk": disk,
        "memory": memory,
        "blocked_reason": blocked,
    }


def first_fit_launch_admission(
    jobs: list[dict[str, Any]],
    plan: list[dict[str, Any]],
    scheduled: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select the first resource-fitting pending job without forcing launch.

    This reuses the retained M05 efficiency-scheduler policy: a heavy job that
    cannot retain the configured MemAvailable floor does not head-of-line
    block a later light family.  Disk failure is global and therefore stops
    the scan.  Every selected job still passes the identical disk/RSS gate.
    """
    rss_rejections: list[dict[str, Any]] = []
    for index, job in enumerate(jobs):
        admission = launch_admission(job, plan, scheduled)
        if admission["pass"]:
            return {
                "pass": True,
                "index": index,
                "job": job,
                "admission": admission,
                "rss_bypassed_job_ids": [row["job_id"] for row in rss_rejections],
            }
        blocked = admission["blocked_reason"] or {}
        if blocked.get("kind") == "DYNAMIC_DISK_RESERVE":
            return {
                "pass": False,
                "index": None,
                "job": None,
                "admission": admission,
                "rss_bypassed_job_ids": [row["job_id"] for row in rss_rejections],
                "blocked_reason": blocked,
            }
        rss_rejections.append({
            "job_id": job["job_id"],
            "family": job.get("family"),
            "memory": admission["memory"],
        })
    return {
        "pass": False,
        "index": None,
        "job": None,
        "admission": None,
        "rss_bypassed_job_ids": [row["job_id"] for row in rss_rejections],
        "blocked_reason": {
            "kind": "DYNAMIC_RSS_ADMISSION",
            "policy": "FULL_PENDING_QUEUE_FIRST_FIT__NO_FORCED_LAUNCH",
            "rejected_candidates": rss_rejections,
        },
    }


def refresh_aggregate(plan: list[dict[str, Any]]) -> dict[str, Any]:
    exclusions = execution_exclusions()
    effective_job_ids = {row["job_id"] for row in plan if row["job_id"] not in exclusions}
    selected = []
    for job in plan:
        if job["job_id"] in exclusions:
            continue
        receipt = load_receipt(job["job_id"])
        if receipt is None:
            continue
        path = receipt_path(job["job_id"])
        selected.append({
            "job_id": job["job_id"], "path": str(path), "sha256": sha256(path),
            "stage": job["stage"], "mode": job["mode"], "family": job["family"],
            "events": job["events"], "seed": job["seed"], "sim_path": receipt["sim_path"],
            "sim_bytes": receipt["sim_bytes"], "TT_s": receipt["isotope_dat"]["TT_s"],
            "RP_record_count": receipt["isotope_dat"]["RP_record_count"],
        })
    background = [row for row in plan if row["stage"] == "background"]
    background_done = {row["job_id"] for row in selected if row["stage"] == "background"}
    selected_job_ids = {row["job_id"] for row in selected}
    all_effective_done = selected_job_ids == effective_job_ids
    effective_planned_jobs = len(effective_job_ids)
    aggregate = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "updated_at": utc_now(),
        "status": (
            f"PASS__ALL_{effective_planned_jobs}_EFFECTIVE_SF3_ONLY_TRANSPORT_JOBS"
            if all_effective_done else "PARTIAL__VALIDATED_RECEIPTS_ONLY"
        ),
        "sim_digest_policy": "NO_REOPEN_OR_REHASH__RECEIPT_PATH_SIZE_HEADER_ONLY",
        "planned_jobs": len(plan),
        # Count only exclusions which actually intersect this plan.  The
        # configuration may retain documentary exclusions for jobs that are no
        # longer present, and zero-A15 delayed cells are added dynamically.
        "effective_planned_jobs": effective_planned_jobs,
        "execution_exclusions": exclusions,
        "validated_jobs": len(selected),
        "background_planned_jobs": len(background),
        "background_validated_jobs": len(background_done),
        "background_validated_events": sum(row["events"] for row in background if row["job_id"] in background_done),
        "selected_receipts": selected,
        "projection": projection(plan),
    }
    atomic_json(PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json", aggregate)
    return aggregate


def run_canary(plan: list[dict[str, Any]], env: dict[str, str]) -> None:
    job = next(row for row in plan if row["production_canary"])
    existing = load_receipt(job["job_id"])
    if existing is not None:
        print(json.dumps({"status": "SKIP__CANARY_ALREADY_PASS", "job_id": job["job_id"]}), flush=True)
        return
    free = shutil.disk_usage(PACKAGE_ROOT).free
    if free < START_FREE_GATE_BYTES:
        raise RuntimeError(f"R0 failed immediately before canary: {free} < {START_FREE_GATE_BYTES}")
    admission = launch_admission(job, plan)
    if not admission["pass"]:
        raise RuntimeError(f"canary launch admission failed: {admission['blocked_reason']}")
    print(json.dumps({
        "event": "canary_launch", "job": job,
        "disk": admission["disk"], "mem": admission["memory"],
    }, sort_keys=True), flush=True)
    result = ensure_job(job, env)
    if result["status"] != "PASS":
        raise RuntimeError(
            "production canary attempt failed; retry requires a fresh controller admission"
        )


def run_job_queue(
    plan: list[dict[str, Any]], env: dict[str, str], jobs: list[dict[str, Any]],
    cpu_budget: int, progress_label: str,
) -> None:
    jobs = [row for row in jobs if load_receipt(row["job_id"]) is None]
    concurrency_policy = configured_adaptive_concurrency_policy()
    worker_limit = min(
        cpu_budget, int(concurrency_policy["adaptive_live_target_workers"])
    )
    futures: dict[concurrent.futures.Future[dict[str, Any]], dict[str, Any]] = {}
    blocked_reason: dict[str, Any] | None = None
    last_progress = 0.0
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_limit) as pool:
        while jobs or futures:
            made_launch = False
            while jobs and len(futures) < worker_limit and not _stop.is_set():
                selection = first_fit_launch_admission(
                    jobs, plan, list(futures.values())
                )
                if not selection["pass"]:
                    blocked_reason = selection["blocked_reason"]
                    break
                job = selection["job"]
                admission = selection["admission"]
                # Disk or RSS availability can recover after active work exits
                # or an audited cleanup.  Never carry a stale failure through a
                # newly successful admission.
                blocked_reason = None
                jobs.pop(int(selection["index"]))
                print(json.dumps({
                    "event": "launch", "job_id": job["job_id"], "family": job["family"],
                    "mode": job["mode"], "events": job["events"],
                    "disk": admission["disk"], "memory": admission["memory"],
                    "scheduler_policy": "FULL_PENDING_QUEUE_FIRST_FIT",
                    "rss_bypassed_job_ids": selection["rss_bypassed_job_ids"],
                }, sort_keys=True), flush=True)
                futures[pool.submit(ensure_job, job, env)] = job
                made_launch = True
            done = [future for future in futures if future.done()]
            for future in done:
                job = futures.pop(future)
                result = future.result()
                if result["status"] != "PASS":
                    next_attempt = next_attempt_ordinal(job["job_id"])
                    if next_attempt is None:
                        raise RuntimeError(f"{job['job_id']} failed both allowed attempts")
                    # Leave the worker before retrying.  Appending to the queue
                    # forces the next attempt through launch_admission(), with
                    # the same registered seed and the next unused ordinal.
                    jobs.append(job)
                    print(json.dumps({
                        "event": "retry_requeued_for_fresh_admission",
                        "job_id": job["job_id"],
                        "failed_attempt": result.get("attempt"),
                        "next_attempt": next_attempt,
                        "watchdog_reason": result.get("watchdog_reason"),
                    }, sort_keys=True), flush=True)
                else:
                    refresh_aggregate(plan)
            now = time.monotonic()
            if now - last_progress >= PROGRESS_SECONDS:
                with _active_lock:
                    active = {key: {
                        "elapsed_s": now - value["started"], "rss": value.get("rss", 0),
                        "bytes": value.get("bytes", 0), "cpu_s": value.get("cpu_s", 0),
                    } for key, value in _active.items()}
                print(json.dumps({
                    "event": "progress", "scope": progress_label, "active": active, "queued": len(jobs),
                    "completed_scope": sum(load_receipt(row["job_id"]) is not None for row in plan if row["stage"] == progress_label),
                    "disk": projection(plan), "mem_available_bytes": mem_available_bytes(),
                    "blocked_reason": blocked_reason,
                }, sort_keys=True), flush=True)
                last_progress = now
            if blocked_reason and not futures:
                raise RuntimeError(f"launch admission blocked with no active work: {blocked_reason}")
            if not made_launch and not done:
                time.sleep(2.0)


def run_remaining_background(plan: list[dict[str, Any]], env: dict[str, str], cpu_budget: int) -> None:
    if canary_receipt(plan) is None:
        raise RuntimeError("production canary must PASS before W2")
    jobs = [row for row in plan if row["stage"] == "background" and not row["production_canary"]]
    # Calibrate the remainder of the gamma cells first, then mix the other families.
    jobs.sort(key=lambda row: (0 if row["family"] == "gamma" else 1, row["ordinal"]))
    run_job_queue(plan, env, jobs, cpu_budget, "background")


def run_postbackground_stage(
    plan: list[dict[str, Any]], env: dict[str, str], stage: str, cpu_budget: int,
) -> None:
    background = [row for row in plan if row["stage"] == "background"]
    missing_background = [row["job_id"] for row in background if load_receipt(row["job_id"]) is None]
    if missing_background:
        raise RuntimeError(f"{stage} requires all background receipts: {missing_background}")
    jobs = [row for row in plan if row["stage"] == stage]
    signal_gate: dict[str, Any] | None = None
    if stage == "signal":
        signal_gate = validate_signal_launch_gate(plan)
    exclusions = execution_exclusions()
    jobs = [row for row in jobs if row["job_id"] not in exclusions]
    if stage == "signal" and {row["job_id"] for row in jobs} != {SIGNAL_SF3_JOB_ID}:
        raise RuntimeError(
            f"post-exclusion signal queue is not exactly SF3-only: "
            f"{sorted(row['job_id'] for row in jobs)}"
        )
    missing_sources = [row["source_path"] for row in jobs if not Path(row["source_path"]).is_file()]
    if missing_sources:
        raise RuntimeError(f"{stage} source preparation incomplete: {missing_sources}")
    if stage == "delayed":
        authority = PACKAGE_ROOT / "audit/sf3_activation_validation.json"
        if not authority.is_file() or json.loads(authority.read_text()).get("status") != "PASS":
            raise RuntimeError("delayed transport requires PASS SF3 activation authority")
    elif stage == "signal":
        print(json.dumps({
            "event": "signal_launch_gate_pass",
            "gate": signal_gate,
        }, sort_keys=True), flush=True)
    jobs.sort(key=lambda row: row["ordinal"])
    run_job_queue(plan, env, jobs, cpu_budget, stage)


def self_test() -> dict[str, Any]:
    """Synthetic launch-gate and retry tests; no production artifact access."""
    # The inherited SE3 test body below is retained as provenance but is not a
    # valid SF3 paired-signal test: SF3 deliberately registers one fresh signal
    # row and consumes frozen SE3 small tables.  The live canary and launch
    # gates exercise the production paths; this smoke locks the SF3 invariants.
    plan = load_plan()
    signal_rows = [row for row in plan if row["stage"] == "signal"]
    if [row["job_id"] for row in signal_rows] != [SIGNAL_SF3_JOB_ID]:
        raise AssertionError("SF3 signal plan is not exactly one fresh job")
    if any(row["geometry"] != "SF3" for row in plan):
        raise AssertionError("non-SF3 transport row found in effective plan")
    policy = configured_adaptive_concurrency_policy()
    if policy["adaptive_live_target_workers"] != 6:
        raise AssertionError("adaptive six-worker target differs")
    interruption_root = Path(tempfile.mkdtemp(prefix="sf3_interruption_selftest_", dir="/tmp"))
    try:
        job_root = interruption_root / "jobs" / "synthetic"
        (job_root / "interrupted" / "controller_interrupt_attempt01").mkdir(parents=True)
        (job_root / "interrupted" / "controller_interrupt_attempt02").mkdir(parents=True)
        (job_root / "failed" / "attempt01").mkdir(parents=True)
        if used_attempt_ordinals("synthetic", run_root=interruption_root) != {1}:
            raise AssertionError("interrupted recovery directories consumed attempt ordinals")
    finally:
        shutil.rmtree(interruption_root, ignore_errors=True)
    return {
        "schema_version": 1,
        "status": "PASS__SF3_RUNNER_STATIC_SELF_TEST",
        "checks": [
            "exact_single_fresh_SF3_signal_job",
            "all_effective_transport_rows_are_SF3",
            "adaptive_target_six_with_memory_swap_PSI_gates",
            "production_canary_and_live_attempt_validation_remain_authoritative",
            "interrupted_recovery_directories_do_not_consume_attempt_ordinals",
            "canonical_receipts_are_bound_to_PASS_attempt_directories",
        ],
        "production_artifacts_accessed": False,
        "SIM_accessed": False,
    }
    import contextlib
    import io

    root = Path(tempfile.mkdtemp(prefix="sf3_runner_selftest_", dir="/tmp"))
    saved_globals = {
        name: globals()[name]
        for name in (
            "RUN_ROOT", "load_receipt", "run_attempt", "projection",
            "memory_admission", "launch_admission", "refresh_aggregate",
            "mem_available_bytes", "configured_adaptive_concurrency_policy",
        )
    }
    try:
        audit = root / "audit"
        audit.mkdir(parents=True)

        def write_json(path: Path, payload: dict[str, Any]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        navigation_path = audit / "navigation.json"
        gate_path = audit / "gate.json"
        override_path = audit / "scope_override.json"
        config_path = root / "analysis_inputs.json"
        navigation = {
            "status": "PASS",
            "driver_validation": {"status": "PASS"},
            "geometries": {"SF3": {"status": "PASS"}},
        }
        write_json(navigation_path, navigation)
        write_json(override_path, {
            "status": "PASS__SF3_ONLY_TRANSPORT_SCOPE_LOCKED",
            "excluded_transport_jobs": {
                SIGNAL_S3D_JOB_ID: "USER_EXPLICITLY_FORBADE_S3D_RERUN"
            },
        })
        exclusion_reason = "USER_SCOPE_SYNTHETIC__NO_S3D_RERUN"
        valid_gate = {
            "status": "PASS",
            "transport_scope": SIGNAL_TRANSPORT_SCOPE,
            "permitted_signal_jobs": [SIGNAL_SF3_JOB_ID],
            "excluded_signal_jobs": {SIGNAL_S3D_JOB_ID: exclusion_reason},
            "scope_override_authority": str(override_path),
            "authority": {
                "path": str(navigation_path),
                "sha256": sha256(navigation_path),
                "status": "PASS",
            },
        }
        write_json(gate_path, valid_gate)
        valid_config = {
            "transport": {
                "memory_headroom_bytes": MIN_MEMORY_HEADROOM_BYTES,
                "adaptive_min_workers": 4,
                "adaptive_live_target_workers": 6,
                "aggressive_extra_worker_cooldown_seconds": 30,
                "aggressive_min_swap_free_bytes": 8 * 1024**3,
                "significant_swap_pages_per_second": 2048,
                "memory_psi_some_avg10_limit": 10.0,
                "memory_psi_full_avg10_limit": 2.0,
                "execution_exclusions": {SIGNAL_S3D_JOB_ID: exclusion_reason}
            },
            "audits": {
                "signal_navigation": str(navigation_path),
                "signal_transport_gate": str(gate_path),
                "user_scope_override": str(override_path),
            },
        }
        write_json(config_path, valid_config)
        if configured_memory_headroom_bytes(config_path) != 1_610_612_736:
            raise AssertionError("configured exact 1.5-GiB headroom self-test failed")
        low_headroom_config = json.loads(json.dumps(valid_config))
        low_headroom_config["transport"]["memory_headroom_bytes"] = 1_610_612_735
        write_json(config_path, low_headroom_config)
        try:
            configured_memory_headroom_bytes(config_path)
        except RuntimeError:
            pass
        else:
            raise AssertionError("sub-1.5-GiB headroom did not fail closed")
        write_json(config_path, valid_config)
        adaptive_policy = configured_adaptive_concurrency_policy(config_path)
        if (
            adaptive_policy["adaptive_min_workers"] != 4
            or adaptive_policy["adaptive_live_target_workers"] != 6
            or adaptive_policy["aggressive_extra_worker_cooldown_seconds"] != 30
            or adaptive_policy["aggressive_min_swap_free_bytes"] != 8 * 1024**3
        ):
            raise AssertionError("adaptive six-worker policy config differs")
        low_swap_floor_config = json.loads(json.dumps(valid_config))
        low_swap_floor_config["transport"]["aggressive_min_swap_free_bytes"] = (
            8 * 1024**3 - 1
        )
        write_json(config_path, low_swap_floor_config)
        try:
            configured_adaptive_concurrency_policy(config_path)
        except RuntimeError:
            pass
        else:
            raise AssertionError("sub-8-GiB free-swap floor did not fail closed")
        for key, value in (
            ("adaptive_live_target_workers", 7),
            ("aggressive_extra_worker_cooldown_seconds", 29),
        ):
            weakened_config = json.loads(json.dumps(valid_config))
            weakened_config["transport"][key] = value
            write_json(config_path, weakened_config)
            try:
                configured_adaptive_concurrency_policy(config_path)
            except RuntimeError:
                pass
            else:
                raise AssertionError(f"unsafe {key} did not fail closed")
        missing_live_target_config = json.loads(json.dumps(valid_config))
        del missing_live_target_config["transport"]["adaptive_live_target_workers"]
        write_json(config_path, missing_live_target_config)
        try:
            configured_adaptive_concurrency_policy(config_path)
        except RuntimeError:
            pass
        else:
            raise AssertionError("missing adaptive live target did not fail closed")
        write_json(config_path, valid_config)

        gib = 1024**3
        healthy_pressure = {
            "evidence_available": True,
            "swap_free_bytes": int(10.5 * gib),
            "thrashing_detected": False,
        }
        live_four = adaptive_memory_decision(
            predicted_growth_bytes=3 * gib,
            candidate_rss_budget_bytes=gib,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=3,
            pressure=healthy_pressure,
            policy=adaptive_policy,
        )
        if (
            not live_four["pass"]
            or live_four["admission_mode"]
            != "ADAPTIVE_LIVE_EXTRA_WORKER_4__EMPIRICAL_CANDIDATE_RSS"
            or live_four["strict_pass"]
        ):
            raise AssertionError("healthy live fourth worker was not admitted")
        live_five = adaptive_memory_decision(
            predicted_growth_bytes=9 * gib,
            candidate_rss_budget_bytes=gib,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=4,
            pressure=healthy_pressure,
            policy=adaptive_policy,
        )
        if (
            not live_five["pass"]
            or live_five["admission_mode"]
            != "ADAPTIVE_LIVE_EXTRA_WORKER_5__EMPIRICAL_CANDIDATE_RSS"
            or live_five["strict_pass"]
        ):
            raise AssertionError("healthy fifth worker was not admitted from live RSS")
        sixth_cooldown_pending = adaptive_memory_decision(
            predicted_growth_bytes=9 * gib,
            candidate_rss_budget_bytes=gib,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=5,
            pressure=healthy_pressure,
            policy=adaptive_policy,
            extra_worker_live_age_seconds=29.999,
            extra_worker_has_live_rss_sample=True,
        )
        if (
            sixth_cooldown_pending["pass"]
            or sixth_cooldown_pending["extra_worker_cooldown_pass"]
        ):
            raise AssertionError("sixth worker bypassed the 30-second live cooldown")
        sixth_without_sample = adaptive_memory_decision(
            predicted_growth_bytes=9 * gib,
            candidate_rss_budget_bytes=gib,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=5,
            pressure=healthy_pressure,
            policy=adaptive_policy,
            extra_worker_live_age_seconds=60.0,
            extra_worker_has_live_rss_sample=False,
        )
        if sixth_without_sample["pass"]:
            raise AssertionError("sixth worker launched without a live worker-five RSS sample")
        live_six = adaptive_memory_decision(
            predicted_growth_bytes=9 * gib,
            candidate_rss_budget_bytes=gib,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=5,
            pressure=healthy_pressure,
            policy=adaptive_policy,
            extra_worker_live_age_seconds=30.0,
            extra_worker_has_live_rss_sample=True,
        )
        if (
            not live_six["pass"]
            or live_six["admission_mode"]
            != "ADAPTIVE_LIVE_EXTRA_WORKER_6__EMPIRICAL_CANDIDATE_RSS"
        ):
            raise AssertionError("healthy sixth worker was not admitted after cooldown")
        live_seven = adaptive_memory_decision(
            predicted_growth_bytes=1,
            candidate_rss_budget_bytes=1,
            mem_available=MIN_MEMORY_HEADROOM_BYTES + gib,
            headroom=MIN_MEMORY_HEADROOM_BYTES,
            scheduled_workers=6,
            pressure=healthy_pressure,
            policy=adaptive_policy,
            extra_worker_live_age_seconds=60.0,
            extra_worker_has_live_rss_sample=True,
        )
        if live_seven["pass"] or live_seven["worker_ordinal"] != 7:
            raise AssertionError("worker seven exceeded the live target of six")
        for label, available, pressure in (
            (
                "live_mem_floor",
                MIN_MEMORY_HEADROOM_BYTES - 1,
                healthy_pressure,
            ),
            (
                "swap_floor",
                MIN_MEMORY_HEADROOM_BYTES + gib,
                {**healthy_pressure, "swap_free_bytes": 8 * gib - 1},
            ),
            (
                "sustained_thrashing",
                MIN_MEMORY_HEADROOM_BYTES + gib,
                {**healthy_pressure, "thrashing_detected": True},
            ),
        ):
            rejected = adaptive_memory_decision(
                predicted_growth_bytes=3 * gib,
                candidate_rss_budget_bytes=3 * gib,
                mem_available=available,
                headroom=MIN_MEMORY_HEADROOM_BYTES,
                scheduled_workers=3,
                pressure=pressure,
                policy=adaptive_policy,
            )
            if rejected["pass"]:
                raise AssertionError(f"fourth-worker {label} guard did not fail closed")
        for label, available, pressure in (
            (
                "post_launch_floor",
                MIN_MEMORY_HEADROOM_BYTES + gib - 1,
                healthy_pressure,
            ),
            (
                "swap_floor",
                MIN_MEMORY_HEADROOM_BYTES + gib,
                {**healthy_pressure, "swap_free_bytes": 8 * gib - 1},
            ),
            (
                "thrashing",
                MIN_MEMORY_HEADROOM_BYTES + gib,
                {**healthy_pressure, "thrashing_detected": True},
            ),
        ):
            rejected = adaptive_memory_decision(
                predicted_growth_bytes=gib,
                candidate_rss_budget_bytes=gib,
                mem_available=available,
                headroom=MIN_MEMORY_HEADROOM_BYTES,
                scheduled_workers=4,
                pressure=pressure,
                policy=adaptive_policy,
            )
            if rejected["pass"]:
                raise AssertionError(f"fifth-worker {label} guard did not fail closed")

        signal_plan = [
            {
                "stage": "signal", "job_id": SIGNAL_S3D_JOB_ID,
                "geometry": "S3d_O8", "mode": "signal", "family": "focused_gamma",
            },
            {
                "stage": "signal", "job_id": SIGNAL_SF3_JOB_ID,
                "geometry": "SF3", "mode": "signal", "family": "focused_gamma",
            },
        ]
        valid_result = validate_signal_launch_gate(signal_plan, config_path)
        if valid_result["effective_signal_job_ids"] != [SIGNAL_SF3_JOB_ID]:
            raise AssertionError("valid exact-SF3 signal gate self-test failed")

        drift_rejections: list[str] = []
        drift_config = json.loads(json.dumps(valid_config))
        drift_config["transport"]["execution_exclusions"] = {}
        write_json(config_path, drift_config)
        try:
            validate_signal_launch_gate(signal_plan, config_path)
        except RuntimeError:
            drift_rejections.append("config_exclusion_missing")
        else:
            raise AssertionError("config exclusion drift did not fail closed")
        write_json(config_path, valid_config)

        drift_gate = json.loads(json.dumps(valid_gate))
        drift_gate["permitted_signal_jobs"] = [SIGNAL_SF3_JOB_ID, SIGNAL_S3D_JOB_ID]
        write_json(gate_path, drift_gate)
        try:
            validate_signal_launch_gate(signal_plan, config_path)
        except RuntimeError:
            drift_rejections.append("gate_permitted_jobs_drift")
        else:
            raise AssertionError("transport-gate permitted-job drift did not fail closed")
        write_json(gate_path, valid_gate)

        # With three 1-GiB workers already scheduled and 8 GiB available, a
        # measured 6.823-GiB heavy candidate must be bypassed; lighter 1-GiB
        # candidates may safely fill slots four through six, never slot seven.
        scheduler_headroom = configured_memory_headroom_bytes(config_path)

        def fake_launch_admission(
            job: dict[str, Any], _plan: list[dict[str, Any]],
            scheduled: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            scheduled = scheduled or []
            reserve = sum(int(row["rss_budget"]) for row in scheduled)
            candidate = int(job["rss_budget"])
            passes = reserve + candidate <= 8 * 1024**3 - scheduler_headroom
            memory = {
                "pass": passes,
                "mem_available_bytes": 8 * 1024**3,
                "active_reserved_growth_bytes": reserve,
                "candidate_rss_budget_bytes": candidate,
                "headroom_bytes": scheduler_headroom,
            }
            blocked = None if passes else {
                "kind": "DYNAMIC_RSS_ADMISSION", "memory": memory,
            }
            return {
                "pass": passes, "disk": {"pass": True}, "memory": memory,
                "blocked_reason": blocked,
            }

        globals()["launch_admission"] = fake_launch_admission
        synthetic_scheduled = [
            {"job_id": f"active_light_{index}", "rss_budget": gib}
            for index in range(1, 4)
        ]
        synthetic_pending = [
            {"job_id": "measured_heavy", "family": "n", "rss_budget": 7_325_569_843},
            {"job_id": "light_4", "family": "muplus", "rss_budget": gib},
            {"job_id": "light_5", "family": "muminus", "rss_budget": gib},
            {"job_id": "light_6", "family": "eplus", "rss_budget": gib},
        ]
        first_fit = first_fit_launch_admission(
            synthetic_pending, synthetic_pending, synthetic_scheduled
        )
        if (
            not first_fit["pass"]
            or first_fit["job"]["job_id"] != "light_4"
            or first_fit["rss_bypassed_job_ids"] != ["measured_heavy"]
        ):
            raise AssertionError("heavy-bypass/light-first-fit self-test failed")
        six_scheduled = synthetic_scheduled + synthetic_pending[1:]
        seventh = first_fit_launch_admission(
            [{"job_id": "unsafe_light_7", "family": "gamma", "rss_budget": gib}],
            synthetic_pending,
            six_scheduled,
        )
        if seventh["pass"] or seventh["blocked_reason"]["kind"] != "DYNAMIC_RSS_ADMISSION":
            raise AssertionError("unsafe seventh worker was not blocked by RSS admission")
        globals()["launch_admission"] = saved_globals["launch_admission"]

        retry_root = root / "retry_run"
        globals()["RUN_ROOT"] = retry_root
        globals()["load_receipt"] = lambda _job_id: None
        admission_state = {"disk_available": True, "memory_available": True}
        attempt_calls: list[int] = []

        def fake_run_attempt(
            job: dict[str, Any], attempt: int, _env: dict[str, str]
        ) -> dict[str, Any]:
            attempt_calls.append(attempt)
            status = "FAIL" if attempt == 1 else "PASS"
            parent = "failed" if status == "FAIL" else "attempts"
            (retry_root / "jobs" / job["job_id"] / parent / f"attempt{attempt:02d}").mkdir(
                parents=True, exist_ok=False
            )
            if status == "FAIL":
                admission_state["disk_available"] = False
                admission_state["memory_available"] = False
            return {
                "status": status,
                "attempt": attempt,
                "wall_s": 0.0,
                "peak_process_group_rss_bytes": 3 * 1024**3,
                "artifact_bytes": 1,
                "errors": (
                    ["watchdog: dynamic_8GiB_reserve_breached"]
                    if status == "FAIL" else []
                ),
                "watchdog_reason": (
                    "dynamic_8GiB_reserve_breached" if status == "FAIL" else "completed"
                ),
            }

        def fake_projection(_plan: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "pass": admission_state["disk_available"],
                "projected_final_free_bytes": (
                    DYNAMIC_RESERVE_BYTES + 1 if admission_state["disk_available"]
                    else DYNAMIC_RESERVE_BYTES - 1
                ),
                "reserve_bytes": DYNAMIC_RESERVE_BYTES,
            }

        def fake_memory_admission(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {
                "pass": admission_state["memory_available"],
                "candidate_rss_budget_bytes": 3 * 1024**3,
            }

        globals()["run_attempt"] = fake_run_attempt
        globals()["projection"] = fake_projection
        globals()["memory_admission"] = fake_memory_admission
        globals()["refresh_aggregate"] = lambda _plan: {}
        globals()["mem_available_bytes"] = lambda: 16 * 1024**3
        globals()["configured_adaptive_concurrency_policy"] = lambda: adaptive_policy
        retry_job = {
            "job_id": "synthetic_resource_retry", "stage": "background",
            "family": "gamma", "mode": "instant", "events": 1,
        }
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            try:
                run_job_queue([retry_job], {}, [retry_job], 1, "background")
            except RuntimeError as exc:
                if "DYNAMIC_DISK_RESERVE" not in str(exc):
                    raise
            else:
                raise AssertionError("resource-failed retry did not stop at fresh admission")
        if attempt_calls != [1]:
            raise AssertionError("resource failure launched attempt 2 without fresh admission")

        admission_state["disk_available"] = True
        with contextlib.redirect_stdout(captured):
            try:
                run_job_queue([retry_job], {}, [retry_job], 1, "background")
            except RuntimeError as exc:
                if "DYNAMIC_RSS_ADMISSION" not in str(exc):
                    raise
            else:
                raise AssertionError("RSS-blocked retry did not stop at fresh admission")
        if attempt_calls != [1]:
            raise AssertionError("RSS failure launched attempt 2 without a passing admission")

        admission_state["memory_available"] = True
        with contextlib.redirect_stdout(captured):
            run_job_queue([retry_job], {}, [retry_job], 1, "background")
        if attempt_calls != [1, 2]:
            raise AssertionError("recovered admission did not launch the second same-seed attempt")

        if (
            failed_peak_rss_bytes({"peak_process_group_rss_bytes_observed": 11}) != 11
            or failed_peak_rss_bytes({"peak_process_group_rss_bytes": 12}) != 12
            or failed_peak_rss_bytes({
                "peak_process_group_rss_bytes_observed": 11,
                "peak_process_group_rss_bytes": 13,
            }) != 13
        ):
            raise AssertionError("failed-peak dual-schema compatibility self-test failed")

        return {
            "schema_version": 1,
            "status": "PASS__SF3_RUNNER_SYNTHETIC_SELF_TEST",
            "checks": [
                "exact_SF3_only_effective_signal_job",
                "config_and_transport_gate_drift_fail_closed_before_launch",
                "resource_failure_does_not_immediately_launch_attempt2",
                "recovered_disk_RSS_admission_allows_same_seed_attempt2",
                "failed_peak_interrupted_and_ordinary_validation_schema_compatible",
                "configured_exact_1.5GiB_headroom_and_lower_value_fails_closed",
                "live_worker_4_requires_post_launch_1.5GiB_floor",
                "live_worker_4_requires_8GiB_free_swap_and_no_thrashing",
                "adaptive_predicted_overcommit_is_bounded_by_swap_surplus",
                "workers_4_to_6_use_live_empirical_candidate_RSS_without_active_future_peak_sum",
                "worker_6_requires_30s_live_RSS_sample_cooldown",
                "workers_4_to_6_retain_1.5GiB_SwapFree_and_no-thrash_guards",
                "adaptive_live_target_hard_caps_at_6_workers",
                "measured_heavy_job_bypassed_for_safe_light_first_fit_slots_4_to_6",
                "RSS_gate_blocks_unsafe_slot_7_without_forced_launch",
            ],
            "signal_gate_drift_rejections": drift_rejections,
            "attempt_ordinals": attempt_calls,
            "production_artifacts_accessed": False,
            "SIM_accessed": False,
        }
    finally:
        for name, value in saved_globals.items():
            globals()[name] = value
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--phase",
        choices=("status", "canary", "remaining-background", "background", "delayed", "signal"),
    )
    actions.add_argument("--self-test", action="store_true")
    parser.add_argument("--cpu-budget", type=int, default=CPU_BUDGET)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.cpu_budget < 1 or args.cpu_budget > MAX_CPU_BUDGET:
        raise ValueError("cpu budget must be 1..6")
    plan = load_plan()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = RUN_ROOT / "controller.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another Plan-1 controller holds {lock_path}") from exc
        aggregate = refresh_aggregate(plan)
        if args.phase == "status":
            print(json.dumps(aggregate, indent=2))
            return 0
        env = load_megalib_environment()
        if not COSIMA.is_file():
            raise FileNotFoundError(COSIMA)
        if args.phase in ("canary", "background"):
            run_canary(plan, env)
            refresh_aggregate(plan)
        if args.phase in ("remaining-background", "background"):
            run_remaining_background(plan, env, args.cpu_budget)
            refresh_aggregate(plan)
        if args.phase in ("delayed", "signal"):
            run_postbackground_stage(plan, env, args.phase, args.cpu_budget)
            refresh_aggregate(plan)
    print(json.dumps({"status": "PASS", "phase": args.phase, "aggregate": str(PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json")}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        _stop.set()
        raise
