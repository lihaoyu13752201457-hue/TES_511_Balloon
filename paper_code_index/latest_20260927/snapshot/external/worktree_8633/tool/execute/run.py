#!/usr/bin/env python3
"""Canonical guarded Cosima executor for a prepared transport job plan."""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import gzip
import json
import math
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from common import (
    atomic_json,
    canonical_receipt_path,
    load_bound_receipt,
    load_config,
    load_json,
    load_megalib_environment,
    load_plan,
    meminfo,
    sha256,
    utc_now,
    validate_generated_bundle,
    write_once_json,
)


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBS_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
SIM_GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$", re.MULTILINE)
SIM_SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$", re.MULTILINE)

ACTIVE_LOCK = threading.Lock()
RESOURCE_LOCK = threading.Lock()
ACTIVE: dict[str, dict[str, Any]] = {}
STOP = threading.Event()


def receipt_path(config: dict[str, Any], job_id: str) -> Path:
    return canonical_receipt_path(config, job_id)


def load_receipt(config: dict[str, Any], job: dict[str, Any]) -> dict[str, Any] | None:
    return load_bound_receipt(config, job)


def attempt_ordinals(config: dict[str, Any], job_id: str) -> set[int]:
    root = Path(config["run_root"]) / "jobs" / job_id
    result: set[int] = set()
    for parent_name in ("attempts", "failed"):
        parent = root / parent_name
        if not parent.is_dir():
            continue
        for path in parent.iterdir():
            match = re.fullmatch(r"attempt(\d+)", path.name)
            if path.is_dir() and match:
                result.add(int(match.group(1)))
    return result


def next_attempt(config: dict[str, Any], job_id: str) -> int | None:
    used = attempt_ordinals(config, job_id)
    per_job = config.get("max_attempts_by_job", {})
    limit = int(per_job.get(job_id, config["max_attempts"]))
    return next(
        (value for value in range(1, limit + 1) if value not in used),
        None,
    )


def process_metrics(pid: int) -> tuple[float, int]:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = raw[raw.rfind(")") + 2 :].split()
        ticks = int(os.sysconf(os.sysconf_names["SC_CLK_TCK"]))
        cpu_s = (int(fields[11]) + int(fields[12])) / ticks
        status = Path(f"/proc/{pid}/status").read_text(encoding="ascii", errors="replace")
        match = re.search(r"^VmRSS:\s+(\d+) kB", status, re.MULTILINE)
        return cpu_s, int(match.group(1)) * 1024 if match else 0
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, IndexError, OSError):
        return 0.0, 0


def terminate_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        process.wait(timeout=15)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def terminate_all() -> None:
    with ACTIVE_LOCK:
        processes = [row.get("process") for row in ACTIVE.values()]
    for process in processes:
        if isinstance(process, subprocess.Popen):
            terminate_group(process)


def request_stop(_signum: int, _frame: Any) -> None:
    # Signal handlers must not acquire ACTIVE_LOCK: a signal can arrive while the
    # main thread already holds that non-reentrant lock. Worker watchdog loops
    # observe STOP within poll_seconds and terminate their own process groups.
    STOP.set()


def memory_full_psi_avg10() -> float:
    try:
        for line in Path("/proc/pressure/memory").read_text(encoding="ascii").splitlines():
            if not line.startswith("full "):
                continue
            match = re.search(r"\bavg10=([-+0-9.eE]+)", line)
            return float(match.group(1)) if match else 0.0
    except (FileNotFoundError, PermissionError, OSError, ValueError):
        pass
    return 0.0


def resource_pressure_victim(reason: str) -> str | None:
    """Select exactly one active attempt to shed under resource pressure.

    Memory pressure selects the largest current RSS consumer.  Disk pressure
    selects the largest artifact writer.  Stable job-id tie breaking ensures
    all watchdog threads agree on the same victim without setting controller
    STOP and killing unrelated attempts.
    """
    metric = "artifact_bytes" if reason == "dynamic_disk_reserve_breached" else "rss_bytes"
    with ACTIVE_LOCK:
        rows = [
            (int(row.get(metric, 0)), job_id)
            for job_id, row in ACTIVE.items()
        ]
    return max(rows, default=(0, None))[1]


def local_resource_guard_reason(
    config: dict[str, Any], run_root: Path, job_id: str
) -> str | None:
    """Return a resource reason only for the one selected local victim."""
    memory = meminfo()
    reason = None
    if shutil.disk_usage(run_root).free < int(config["dynamic_reserve_bytes"]):
        reason = "dynamic_disk_reserve_breached"
    elif memory["MemAvailable"] < int(config["runtime_mem_floor_bytes"]):
        reason = "runtime_MemAvailable_floor_breached"
    elif memory["SwapFree"] < int(config["runtime_swap_floor_bytes"]):
        reason = "runtime_SwapFree_floor_breached"
    else:
        with ACTIVE_LOCK:
            aggregate_rss = sum(int(row.get("rss_bytes", 0)) for row in ACTIVE.values())
        aggregate_ceiling = int(config.get("aggregate_worker_rss_ceiling_bytes", 0))
        if aggregate_ceiling > 0 and aggregate_rss > aggregate_ceiling:
            reason = "aggregate_worker_RSS_ceiling_breached"
        elif memory_full_psi_avg10() > float(config.get("runtime_memory_full_psi_avg10_max", 25.0)):
            reason = "runtime_memory_full_PSI_breached"
    if reason is None or resource_pressure_victim(reason) != job_id:
        return None
    return reason


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


def artifact_paths(active_dir: Path, job_id: str) -> tuple[Path, Path, Path]:
    return (
        active_dir / f"{job_id}.inc1.id1.sim.gz",
        active_dir / f"{job_id}.dat.inc1.dat",
        active_dir / f"{job_id}.log",
    )


def validate_attempt(
    config: dict[str, Any],
    job: dict[str, Any],
    active_dir: Path,
    returncode: int,
    wall_s: float,
    peak_rss: int,
    watchdog_reason: str,
) -> dict[str, Any]:
    job_id = job["job_id"]
    sim, dat, log = artifact_paths(active_dir, job_id)
    source = Path(job["source_path"])
    errors: list[str] = []
    required_paths = [source, sim, log]
    if job.get("requires_isotope_dat", True):
        required_paths.append(dat)
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
        observation = OBS_RE.search(text)
        log_scan = {
            "generated_events": int(generated.group(1)) if generated else None,
            "beam_on_cpu_s": float(cpu.group(1)) if cpu else None,
            "observation_time_s": float(observation.group(1)) if observation else None,
            "graphics_terminal_marker": "Graphics systems deleted." in text,
            "error_marker": any(
                marker in text for marker in ("***  Error", "Segmentation fault", "Unable to parse")
            ),
        }
        if returncode != 0:
            errors.append(f"Cosima return code {returncode}")
        if log_scan["generated_events"] != job["events"]:
            errors.append(f"generated count {log_scan['generated_events']} != {job['events']}")
        if not log_scan["graphics_terminal_marker"] or log_scan["error_marker"]:
            errors.append("Cosima terminal/error marker gate failed")
    if job.get("requires_isotope_dat", True) and dat.is_file():
        dat_scan = parse_dat(dat)
        errors.extend(dat_scan["errors"])
        if dat_scan.get("TT_s") and log_scan.get("observation_time_s") and not math.isclose(
            float(dat_scan["TT_s"]),
            float(log_scan["observation_time_s"]),
            rel_tol=2e-3,
            abs_tol=2e-6,
        ):
            errors.append("DAT TT differs from log observation time")
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
    if sum(
        line.strip().endswith(f"{count_token} {job['events']}")
        for line in source_text.splitlines()
    ) != 1:
        errors.append(f"source {count_token} count mismatch")
    if sum(
        line.strip().endswith(f".FileName {job['output_prefix']}")
        for line in source_text.splitlines()
    ) != 1:
        errors.append("source output prefix mismatch")
    if config.get("source_policy", "corrected_keV_background") == "corrected_keV_background":
        if source_text.count(config["corrected_token"]) != 20:
            errors.append("corrected-keV source token count mismatch")
        if config["forbidden_legacy_token"] in source_text:
            errors.append("legacy spectrum token in source")
        if "mono511" in source_text.lower() or "mono_511" in source_text.lower():
            errors.append("forbidden additive mono-511 marker in source")
    sizes = {
        "sim_bytes": sim.stat().st_size if sim.is_file() else 0,
        "isotope_dat_bytes": dat.stat().st_size if dat.is_file() else 0,
        "log_bytes": log.stat().st_size if log.is_file() else 0,
    }
    return {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "job_id": job_id,
        "candidate": config["candidate"],
        "mode": job["mode"],
        "family": job["family"],
        "events": job["events"],
        "seed": job["seed"],
        "source_path": str(source),
        "source_sha256": sha256(source) if source.is_file() else None,
        "setup_path": job["setup_path"],
        "returncode": returncode,
        "wall_s": wall_s,
        "peak_process_rss_bytes": peak_rss,
        "watchdog_reason": watchdog_reason,
        "log": log_scan,
        "isotope_dat": dat_scan,
        "sim_header": sim_header,
        **sizes,
        "artifact_bytes": sum(sizes.values()),
        "sim_digest_policy": "OMITTED__PATH_SIZE_AND_HEADER_ONLY",
    }


def append_resource(config: dict[str, Any], payload: dict[str, Any]) -> None:
    path = Path(config["run_root"]) / "resource_metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with RESOURCE_LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()


def run_attempt(
    config: dict[str, Any],
    job: dict[str, Any],
    attempt: int,
    environment: dict[str, str],
) -> dict[str, Any]:
    job_id = job["job_id"]
    run_root = Path(config["run_root"])
    job_root = run_root / "jobs" / job_id
    active_dir = job_root / "active"
    if active_dir.exists():
        raise RuntimeError(f"stale active attempt requires explicit recovery: {active_dir}")
    active_dir.mkdir(parents=True)
    log = active_dir / f"{job_id}.log"
    command = [config["cosima"], "-s", str(job["seed"]), job["source_path"]]
    started_iso = utc_now()
    started = time.monotonic()
    peak_rss = 0
    watchdog_reason = "completed"
    process: subprocess.Popen[Any] | None = None
    try:
        with log.open("x", encoding="utf-8", buffering=1) as handle:
            handle.write(json.dumps({
                "job_id": job_id,
                "attempt": attempt,
                "candidate": config["candidate"],
                "source": job["source_path"],
                "source_sha256": sha256(Path(job["source_path"])),
                "setup": job["setup_path"],
                "events": job["events"],
                "seed": job["seed"],
                "started_at": started_iso,
                "command": command,
            }, sort_keys=True) + "\n")
            handle.flush()
            process = subprocess.Popen(
                command,
                cwd=config["cosima_workdir"],
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            with ACTIVE_LOCK:
                ACTIVE[job_id] = {
                    "process": process,
                    "pid": process.pid,
                    "attempt": attempt,
                    "events": job["events"],
                    "mode": job["mode"],
                    "family": job["family"],
                    "started_at": started_iso,
                    "rss_bytes": 0,
                    "peak_rss_bytes": 0,
                    "artifact_bytes": 0,
                    "cpu_s": 0.0,
                }
            while process.poll() is None:
                time.sleep(float(config["poll_seconds"]))
                cpu_s, rss = process_metrics(process.pid)
                peak_rss = max(peak_rss, rss)
                artifact_bytes = sum(
                    path.stat().st_size for path in active_dir.iterdir() if path.is_file()
                )
                with ACTIVE_LOCK:
                    if job_id in ACTIVE:
                        ACTIVE[job_id].update(
                            cpu_s=cpu_s,
                            rss_bytes=rss,
                            peak_rss_bytes=peak_rss,
                            artifact_bytes=artifact_bytes,
                        )
                reason = None
                if STOP.is_set():
                    reason = "controller_stop_requested"
                else:
                    reason = local_resource_guard_reason(config, run_root, job_id)
                if reason:
                    watchdog_reason = reason
                    terminate_group(process)
                    break
            returncode = process.wait()
            wall_s = time.monotonic() - started
            handle.write(
                f"watchdog_reason={watchdog_reason}\npeak_process_rss_bytes={peak_rss}\n"
                f"returncode={returncode}\nwall_s={wall_s:.6f}\n"
            )
        result = validate_attempt(
            config, job, active_dir, returncode, wall_s, peak_rss, watchdog_reason
        )
    except BaseException as exc:
        if process is not None:
            terminate_group(process)
        wall_s = time.monotonic() - started
        result = {
            "schema_version": 1,
            "profile_id": config["profile_id"],
            "status": "FAIL",
            "errors": [f"runner exception: {type(exc).__name__}: {exc}"],
            "job_id": job_id,
            "candidate": config["candidate"],
            "mode": job["mode"],
            "family": job["family"],
            "events": job["events"],
            "seed": job["seed"],
            "wall_s": wall_s,
            "peak_process_rss_bytes": peak_rss,
            "watchdog_reason": "runner_exception",
            "artifact_bytes": sum(
                path.stat().st_size for path in active_dir.iterdir() if path.is_file()
            ) if active_dir.is_dir() else 0,
        }
    finally:
        with ACTIVE_LOCK:
            ACTIVE.pop(job_id, None)
    result.update({"attempt": attempt, "started_at": started_iso, "ended_at": utc_now()})
    if result["status"] == "PASS":
        final = job_root / "attempts" / f"attempt{attempt:02d}"
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            raise RuntimeError(f"attempt destination already exists: {final}")
        os.replace(active_dir, final)
        result["attempt_dir"] = str(final)
        result["sim_path"] = str(final / f"{job_id}.inc1.id1.sim.gz")
        result["isotope_dat_path"] = str(final / f"{job_id}.dat.inc1.dat")
        result["log_path"] = str(final / f"{job_id}.log")
        write_once_json(receipt_path(config, job_id), result)
    else:
        final = job_root / "failed" / f"attempt{attempt:02d}"
        final.parent.mkdir(parents=True, exist_ok=True)
        if active_dir.exists():
            os.replace(active_dir, final)
        else:
            final.mkdir(exist_ok=False)
        result["attempt_dir"] = str(final)
        write_once_json(final / "validation.json", result)
    append_resource(config, {
        "at": utc_now(),
        "job_id": job_id,
        "attempt": attempt,
        "status": result["status"],
        "wall_s": result.get("wall_s"),
        "peak_rss_bytes": result.get("peak_process_rss_bytes"),
        "artifact_bytes": result.get("artifact_bytes"),
        "free_disk_bytes": shutil.disk_usage(run_root).free,
    })
    return result


def admission(
    config: dict[str, Any],
    job: dict[str, Any],
    inflight_count: int = 0,
) -> tuple[bool, dict[str, Any]]:
    run_root = Path(config["run_root"])
    free = shutil.disk_usage(run_root).free
    memory = meminfo()
    required_disk = int(config["dynamic_reserve_bytes"]) + int(job["estimated_bytes"])
    worker_reservation = int(config.get("launch_worker_reservation_bytes", 1_610_612_736))
    aggregate_ceiling = int(config.get("aggregate_worker_rss_ceiling_bytes", 0))
    with ACTIVE_LOCK:
        active_rows = list(ACTIVE.values())
    unreported = max(0, inflight_count - len(active_rows))
    projected_worker_rss = (
        sum(max(worker_reservation, int(row.get("rss_bytes", 0))) for row in active_rows)
        + (unreported + 1) * worker_reservation
    )
    reasons: list[str] = []
    if free < required_disk:
        reasons.append(f"disk:{free}<{required_disk}")
    if memory["MemAvailable"] < int(config["launch_mem_available_bytes"]):
        reasons.append("MemAvailable_launch_floor")
    if memory["SwapFree"] < int(config["launch_swap_free_bytes"]):
        reasons.append("SwapFree_launch_floor")
    if aggregate_ceiling > 0 and projected_worker_rss > aggregate_ceiling:
        reasons.append(f"aggregate_worker_rss:{projected_worker_rss}>{aggregate_ceiling}")
    psi = memory_full_psi_avg10()
    if psi > float(config.get("launch_memory_full_psi_avg10_max", 10.0)):
        reasons.append(f"memory_full_psi_avg10:{psi}")
    return not reasons, {
        "reasons": reasons,
        "disk_free_bytes": free,
        "required_disk_bytes": required_disk,
        "mem_available_bytes": memory["MemAvailable"],
        "swap_free_bytes": memory["SwapFree"],
        "worker_reservation_bytes": worker_reservation,
        "projected_worker_rss_bytes": projected_worker_rss,
        "aggregate_worker_rss_ceiling_bytes": aggregate_ceiling,
        "memory_full_psi_avg10": psi,
    }


def active_snapshot() -> dict[str, Any]:
    with ACTIVE_LOCK:
        return {
            job_id: {key: value for key, value in row.items() if key != "process"}
            for job_id, row in ACTIVE.items()
        }


def publish_state(
    config: dict[str, Any],
    *,
    status: str,
    plan: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    error: str | None = None,
) -> None:
    completed = [job["job_id"] for job in plan if load_receipt(config, job) is not None]
    payload = {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "candidate": config["candidate"],
        "controller_pid": os.getpid(),
        "status": status,
        "updated_at": utc_now(),
        "workers": config["workers"],
        "planned_jobs": len(plan),
        "completed_jobs": completed,
        "completed_count": len(completed),
        "pending_jobs": [job["job_id"] for job in pending],
        "active": active_snapshot(),
        "resource": {
            "disk_free_bytes": shutil.disk_usage(Path(config["run_root"])).free,
            **{key.lower(): value for key, value in meminfo().items()},
        },
        "error": error,
    }
    atomic_json(Path(config["run_root"]) / "controller_state.json", payload)


def run_canary(
    config: dict[str, Any],
    job: dict[str, Any],
    environment: dict[str, str],
) -> None:
    if load_receipt(config, job) is not None:
        return
    while True:
        attempt = next_attempt(config, job["job_id"])
        if attempt is None:
            raise RuntimeError("production canary exhausted all attempts")
        allowed, evidence = admission(config, job, 0)
        if not allowed:
            raise RuntimeError(f"production canary admission failed: {evidence}")
        print(json.dumps({"event": "canary_start", "job_id": job["job_id"], "attempt": attempt}), flush=True)
        result = run_attempt(config, job, attempt, environment)
        print(json.dumps({"event": "canary_end", "status": result["status"], "errors": result.get("errors")}), flush=True)
        if result["status"] == "PASS":
            return
        if STOP.is_set():
            raise RuntimeError(f"canary stopped by resource guard: {result.get('watchdog_reason')}")


def run_queue(
    config: dict[str, Any],
    plan: list[dict[str, Any]],
    environment: dict[str, str],
    workers: int,
) -> None:
    pending = [
        job for job in plan
        if job["job_id"] != config["canary_job_id"] and load_receipt(config, job) is None
    ]
    futures: dict[concurrent.futures.Future[dict[str, Any]], dict[str, Any]] = {}
    exhausted: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while pending or futures:
            if STOP.is_set():
                raise RuntimeError("controller stop requested")
            launched = False
            blocked: list[dict[str, Any]] = []
            while pending and len(futures) < workers:
                selected_index = None
                selected_evidence = None
                for index, job in enumerate(pending):
                    allowed, evidence = admission(config, job, len(futures))
                    if allowed:
                        selected_index = index
                        selected_evidence = evidence
                        break
                    blocked.append({"job_id": job["job_id"], **evidence})
                if selected_index is None:
                    break
                job = pending.pop(selected_index)
                attempt = next_attempt(config, job["job_id"])
                if attempt is None:
                    exhausted.append({"job_id": job["job_id"], "reason": "attempts_exhausted_before_launch"})
                    print(json.dumps({
                        "event": "job_exhausted",
                        "job_id": job["job_id"],
                        "reason": "attempts_exhausted_before_launch",
                    }, sort_keys=True), flush=True)
                    continue
                print(json.dumps({
                    "event": "job_start",
                    "job_id": job["job_id"],
                    "attempt": attempt,
                    "workers_active_after_launch": len(futures) + 1,
                    "admission": selected_evidence,
                }, sort_keys=True), flush=True)
                futures[pool.submit(run_attempt, config, job, attempt, environment)] = job
                launched = True
            publish_state(config, status="RUNNING", plan=plan, pending=pending)
            if not futures and pending:
                raise RuntimeError(f"all pending jobs blocked by resource admission: {blocked[:4]}")
            done, _ = concurrent.futures.wait(
                futures,
                timeout=float(config["poll_seconds"]),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                job = futures.pop(future)
                result = future.result()
                print(json.dumps({
                    "event": "job_end",
                    "job_id": job["job_id"],
                    "attempt": result.get("attempt"),
                    "status": result["status"],
                    "errors": result.get("errors"),
                }, sort_keys=True), flush=True)
                if result["status"] != "PASS":
                    if STOP.is_set():
                        raise RuntimeError(
                            f"resource guard stopped {job['job_id']}: {result.get('watchdog_reason')}"
                        )
                    if next_attempt(config, job["job_id"]) is None:
                        exhausted.append({
                            "job_id": job["job_id"],
                            "reason": "failed_all_attempts",
                            "last_errors": result.get("errors"),
                        })
                    else:
                        pending.append(job)
            if not launched and not done:
                time.sleep(0.25)
    if exhausted:
        raise RuntimeError(f"jobs exhausted attempts after queue drain: {exhausted}")


def run(workers: int, config_path: str | Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    if workers < 1 or workers > int(config["max_workers"]):
        raise ValueError(f"workers must be within 1..{config['max_workers']}")
    config = dict(config, workers=workers)
    plan = load_plan(config)
    validate_generated_bundle(config, plan)
    run_root = Path(config["run_root"])
    run_root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(run_root).free < int(config["start_free_bytes"]):
        raise RuntimeError("start-free disk gate failed")
    memory = meminfo()
    if memory["MemAvailable"] < int(config["launch_mem_available_bytes"]):
        raise RuntimeError("start MemAvailable gate failed")
    if memory["SwapFree"] < int(config["launch_swap_free_bytes"]):
        raise RuntimeError("start SwapFree gate failed")
    environment = load_megalib_environment(Path(config["megalib_environment"]))
    cosima = Path(config["cosima"])
    if not cosima.is_file() or not os.access(cosima, os.X_OK):
        raise RuntimeError(f"Cosima executable unavailable: {cosima}")
    lock_path = run_root / "controller.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another controller holds {lock_path}") from exc
        publish_state(config, status="STARTING", plan=plan, pending=plan)
        canary = next(job for job in plan if job["job_id"] == config["canary_job_id"])
        try:
            run_canary(config, canary, environment)
            run_queue(config, plan, environment, workers)
            publish_state(config, status="COMPLETE", plan=plan, pending=[])
        except BaseException as exc:
            STOP.set()
            terminate_all()
            pending = [job for job in plan if load_receipt(config, job) is None]
            publish_state(config, status="FAILED", plan=plan, pending=pending, error=str(exc))
            raise
    return load_json(run_root / "controller_state.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.status:
        path = Path(config["run_root"]) / "controller_state.json"
        print(json.dumps(load_json(path) if path.is_file() else {"status": "NOT_STARTED"}, indent=2))
        return 0
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    result = run(args.workers or int(config["workers"]), args.config)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
