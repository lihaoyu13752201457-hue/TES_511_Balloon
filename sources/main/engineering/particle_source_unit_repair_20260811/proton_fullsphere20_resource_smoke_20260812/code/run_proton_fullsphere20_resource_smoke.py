#!/usr/bin/env python3
"""Run a guarded, serial corrected-keV EXPACS proton resource smoke."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import smoke_common as common


_ACTIVE_PROCESS: subprocess.Popen[Any] | None = None
_INTERRUPTED = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_collisions() -> list[dict[str, Any]]:
    """Search prior small provenance files without reading transport products."""
    wanted = {str(value) for value in common.SEED_BY_MODE.values()}
    suffixes = {".json", ".source", ".csv", ".md", ".txt"}
    matches: list[dict[str, Any]] = []
    roots = (
        common.ROOT / "runs/particle_source_unit_repair_20260811",
        common.REPAIR_ROOT,
    )
    package = common.PACKAGE_ROOT.resolve()
    for root in roots:
        if not root.exists():
            continue
        for current, directories, files in os.walk(root):
            current_path = Path(current).resolve()
            directories[:] = [
                name
                for name in directories
                if not (current_path / name).resolve().is_relative_to(package)
            ]
            if current_path.is_relative_to(package):
                continue
            for name in files:
                path = current_path / name
                if path.suffix not in suffixes:
                    continue
                try:
                    if path.stat().st_size > 20 * 1024**2:
                        continue
                    text = path.read_text(encoding="utf-8", errors="replace")
                except (FileNotFoundError, PermissionError, OSError):
                    continue
                for seed in wanted:
                    if seed in text:
                        matches.append({"seed": int(seed), "path": common.rel(path)})
    return matches


def plan_payload() -> dict[str, Any]:
    return {
        "batch_id": common.BATCH_ID,
        "authority_boundary": "resource diagnostic only; not mergeable production or physics authority",
        "source": {
            "model": "EXPACS/PARMA atmospheric cosmic-ray proton",
            "energy_axis": "corrected total kinetic energy in keV",
            "angular_binning": "0--180 deg full sphere, 20 equal-mu bins",
            "flux_cm2_s": common.FLUX_CM2_S,
            "farfield_radius_cm": common.FARFIELD_RADIUS_CM,
            "energy_truncation": False,
            "conditional_or_stratified_source": False,
        },
        "statistics": {
            "events_per_geometry_mode": common.EVENTS_PER_JOB,
            "jobs": len(common.job_specs()),
            "total_primaries": common.EVENTS_PER_JOB * len(common.job_specs()),
            "workers": 1,
            "jobs_detail": [common.serializable_job(row) for row in common.job_specs()],
        },
        "resource_limits": {
            "per_file_bytes": common.PER_FILE_CAP_BYTES,
            "batch_output_bytes": common.BATCH_OUTPUT_CAP_BYTES,
            "free_disk_floor_bytes": common.FREE_DISK_FLOOR_BYTES,
            "process_group_rss_bytes": common.PROCESS_GROUP_RSS_CAP_BYTES,
            "mem_available_floor_bytes": common.MEM_AVAILABLE_FLOOR_BYTES,
            "job_wall_s": common.JOB_WALL_LIMIT_S,
            "no_activity_s": common.NO_ACTIVITY_LIMIT_S,
            "automatic_delete": False,
        },
        "run_root": common.rel(common.RUN_ROOT),
    }


def build_contract(environment: dict[str, str], descriptor: dict[str, Any]) -> dict[str, Any]:
    static_report = common.static_gate()
    manifest, records = common.proton_contract_records()
    collisions = seed_collisions()
    if collisions:
        raise RuntimeError(f"planned seed collision(s): {collisions[:10]}")
    inputs = common.input_snapshots(environment)
    free = shutil.disk_usage(common.ROOT).free
    available = common.mem_available_bytes()
    if free < common.FREE_DISK_FLOOR_BYTES + common.BATCH_OUTPUT_CAP_BYTES:
        raise RuntimeError(
            f"insufficient disk for frozen floor+batch cap: free={free}"
        )
    if available < common.MEM_AVAILABLE_FLOOR_BYTES + 512 * 1024**2:
        raise RuntimeError(f"insufficient available memory before launch: {available}")
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED",
        "batch_id": common.BATCH_ID,
        "created_utc": utc_now(),
        "authority_boundary": (
            "Resource/failure-mode diagnostic only. It is not mergeable production, a total "
            "background estimate, a sensitivity result, or geometry-promotion authority."
        ),
        "source": {
            "source_contract_manifest": common.rel(common.SOURCE_CONTRACT),
            "source_contract_manifest_sha256": common.SOURCE_CONTRACT_SHA256,
            "static_validation": common.rel(common.STATIC_VALIDATION),
            "static_validation_sha256": common.sha256(common.STATIC_VALIDATION),
            "static_gate_status": static_report["status"],
            "model": manifest["source_model"],
            "energy_contract": manifest["energy_contract"],
            "policies": manifest["policies"],
            "family": "p",
            "particle_type": 4,
            "flux_cm2_s": common.FLUX_CM2_S,
            "farfield_radius_cm": common.FARFIELD_RADIUS_CM,
            "angular_bins": 20,
            "theta_range_deg": [0.0, 180.0],
            "energy_truncation": False,
            "conditional_or_stratified_source": False,
            "cards": {
                geometry: {
                    "path": common.rel(common.source_card(geometry)),
                    "sha256": records[geometry]["source_sha256"],
                    "spectrum_files": records[geometry]["spectrum_files"],
                    "geometry_setup": records[geometry]["geometry_lines"][0],
                    "geometry_bundle_sha256": manifest["geometries"][geometry][
                        "geometry_bundle_sha256"
                    ],
                }
                for geometry in common.GEOMETRIES
            },
        },
        "statistics": {
            "events_per_job": common.EVENTS_PER_JOB,
            "jobs": [common.serializable_job(row) for row in common.job_specs()],
            "job_count": len(common.job_specs()),
            "total_primaries": common.EVENTS_PER_JOB * len(common.job_specs()),
            "execution_order": "mass instant, s3d instant, mass buildup, s3d buildup",
            "workers": 1,
        },
        "seed_registry": {
            "instant": common.SEED_BY_MODE["instant"],
            "buildup": common.SEED_BY_MODE["buildup"],
            "collision_scan": "PASS__NO_MATCH_IN_PRIOR_SMALL_PROVENANCE_FILES",
            "policy": (
                "same mode uses the same operational seed across geometries; modes use "
                "different seeds; this does not authorize a paired statistical estimator"
            ),
        },
        "transport": {
            "cosima": str(common.COSIMA),
            "cosima_sha256": common.sha256(common.COSIMA),
            "environment": descriptor,
            "physics_hd": "qgsp-bic-hp",
            "physics_em": "LivermorePol",
            "store_simulation_info": "all",
            "store_isotopes": True,
            "instant_decay_mode": None,
            "buildup_decay_mode": "ActivationBuildUp",
        },
        "resource_limits": plan_payload()["resource_limits"],
        "initial_resources": {
            "free_disk_bytes": free,
            "mem_available_bytes": available,
        },
        "frozen_inputs": inputs,
        "frozen_inputs_digest": common.canonical_digest(inputs),
    }


def update_state(**updates: Any) -> None:
    state = common.load_json(common.STATE)
    state.update(updates)
    state["heartbeat_utc"] = utc_now()
    common.atomic_replace_json(common.STATE, state)


def terminate_process(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def signal_handler(_signum: int, _frame: Any) -> None:
    global _INTERRUPTED
    _INTERRUPTED = True
    if _ACTIVE_PROCESS is not None:
        terminate_process(_ACTIVE_PROCESS)


def artifact_inventory(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*")):
        if path.is_file():
            rows.append(
                {
                    "path": common.rel(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": common.sha256(path),
                }
            )
    return rows


def run_job(
    spec: dict[str, Any],
    contract: dict[str, Any],
    environment: dict[str, str],
) -> dict[str, Any]:
    global _ACTIVE_PROCESS
    common.verify_input_snapshots(contract["frozen_inputs"])
    common.static_gate()
    if common.tree_size(common.RUN_ROOT) >= common.BATCH_OUTPUT_CAP_BYTES:
        raise RuntimeError("aggregate batch output cap already reached")
    free = shutil.disk_usage(common.ROOT).free
    available = common.mem_available_bytes()
    remaining_batch_allowance = max(
        0,
        common.BATCH_OUTPUT_CAP_BYTES - common.tree_size(common.RUN_ROOT),
    )
    if free <= common.FREE_DISK_FLOOR_BYTES + remaining_batch_allowance:
        raise RuntimeError(f"free disk is too close to the 80 GiB floor: {free}")
    if available <= common.MEM_AVAILABLE_FLOOR_BYTES:
        raise RuntimeError(f"MemAvailable is below the hard floor: {available}")

    directory = Path(spec["directory"])
    directory.mkdir(parents=True, exist_ok=False)
    source_text = common.expected_job_source(spec)
    job_source = Path(spec["job_source"])
    with job_source.open("x", encoding="utf-8") as handle:
        handle.write(source_text)
        handle.flush()
        os.fsync(handle.fileno())

    command = [
        sys.executable,
        str(common.LIMIT_LAUNCHER),
        "--file-size-limit-bytes",
        str(common.PER_FILE_CAP_BYTES),
        "--cosima",
        str(common.COSIMA),
        "--seed",
        str(spec["seed"]),
        "--source",
        str(job_source),
    ]
    started = time.monotonic()
    peak_rss = 0
    reason = "process_exit"
    returncode: int | None = None
    caught: BaseException | None = None
    log_path = Path(spec["log"])
    with log_path.open("x", encoding="utf-8", buffering=1) as log:
        log.write(
            f"batch_id={common.BATCH_ID}\njob={spec['key']} events={spec['events']} "
            f"seed={spec['seed']}\n"
        )
        log.write(f"base_source={spec['base_source']}\njob_source={job_source}\n")
        log.write(f"cosima_command={' '.join(command)}\n")
        log.flush()
        try:
            proc = subprocess.Popen(
                command,
                cwd=common.ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            _ACTIVE_PROCESS = proc
            previous_cpu = common.process_group_cpu_ticks(proc.pid)
            previous_growth = common.tree_size(directory)
            last_activity = time.monotonic()
            while proc.poll() is None:
                time.sleep(common.WATCHDOG_POLL_S)
                now = time.monotonic()
                cpu = common.process_group_cpu_ticks(proc.pid)
                growth = common.tree_size(directory)
                rss = common.process_group_rss_bytes(proc.pid)
                peak_rss = max(peak_rss, rss)
                if cpu > previous_cpu or growth > previous_growth:
                    last_activity = now
                previous_cpu, previous_growth = cpu, growth
                free = shutil.disk_usage(common.ROOT).free
                available = common.mem_available_bytes()
                batch_bytes = common.tree_size(common.RUN_ROOT)
                if _INTERRUPTED:
                    reason = "external_interrupt"
                    break
                if now - started > common.JOB_WALL_LIMIT_S:
                    reason = "job_wall_limit"
                    break
                if now - last_activity > common.NO_ACTIVITY_LIMIT_S:
                    reason = "no_cpu_or_output_activity"
                    break
                if batch_bytes > common.BATCH_OUTPUT_CAP_BYTES:
                    reason = "aggregate_batch_output_cap"
                    break
                if free <= common.FREE_DISK_FLOOR_BYTES:
                    reason = "free_disk_floor"
                    break
                if rss > common.PROCESS_GROUP_RSS_CAP_BYTES:
                    reason = "process_group_rss_cap"
                    break
                if available <= common.MEM_AVAILABLE_FLOOR_BYTES:
                    reason = "mem_available_floor"
                    break
            if proc.poll() is None:
                terminate_process(proc)
            returncode = proc.wait(timeout=10)
            if reason != "process_exit":
                caught = RuntimeError(f"watchdog stopped {spec['key']}: {reason}")
        except BaseException as exc:
            caught = exc
            reason = f"supervisor_exception_{type(exc).__name__}"
            if _ACTIVE_PROCESS is not None:
                terminate_process(_ACTIVE_PROCESS)
            returncode = _ACTIVE_PROCESS.poll() if _ACTIVE_PROCESS is not None else None
        finally:
            _ACTIVE_PROCESS = None
            log.write(f"watchdog_reason={reason}\n")
            log.write(f"peak_process_group_rss_bytes={peak_rss}\n")
            log.write(f"batch_output_bytes={common.tree_size(common.RUN_ROOT)}\n")
            log.write(f"free_disk_bytes={shutil.disk_usage(common.ROOT).free}\n")
            log.write(f"mem_available_bytes={common.mem_available_bytes()}\n")
            log.write(f"returncode={returncode if returncode is not None else -999}\n")
            log.write(f"wall_s={time.monotonic() - started:.3f}\n")

    receipt = {
        "schema_version": 1,
        "batch_id": common.BATCH_ID,
        "status": "PASS_TRANSPORT_EXIT" if returncode == 0 and caught is None else "FAIL_TRANSPORT",
        "completed_utc": utc_now(),
        "contract": common.rel(common.CONTRACT),
        "contract_sha256": common.sha256(common.CONTRACT),
        "job": common.serializable_job(spec),
        "job_source_sha256": common.sha256(job_source),
        "watchdog_reason": reason,
        "returncode": returncode,
        "wall_s": time.monotonic() - started,
        "peak_process_group_rss_bytes": peak_rss,
        "batch_output_bytes": common.tree_size(common.RUN_ROOT),
        "free_disk_bytes": shutil.disk_usage(common.ROOT).free,
        "mem_available_bytes": common.mem_available_bytes(),
        "artifacts": artifact_inventory(directory),
    }
    common.atomic_write_once_json(Path(spec["receipt"]), receipt)
    if caught is not None:
        raise caught
    if returncode != 0:
        raise RuntimeError(f"Cosima returned {returncode} for {spec['key']}")
    return receipt


def validate(job_key: str | None, *, write: bool) -> dict[str, Any]:
    command = [sys.executable, str(common.VALIDATOR)]
    if job_key is not None:
        command.extend(["--job", job_key])
    if not write:
        command.append("--check")
    result = subprocess.run(
        command,
        cwd=common.ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dynamic validation failed:\n{result.stdout[-6000:]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"dynamic validator emitted non-JSON output:\n{result.stdout[-3000:]}") from exc
    if payload.get("status") != "PASS" or payload.get("errors") not in (None, []):
        raise RuntimeError(f"dynamic validator did not return a clean PASS: {payload}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="print the fixed plan; write and run nothing")
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(plan_payload(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if common.RUN_ROOT.exists():
        raise SystemExit(f"refusing to overwrite existing run root: {common.RUN_ROOT}")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    environment, descriptor = common.resolve_transport_environment()
    contract = build_contract(environment, descriptor)
    common.RUN_ROOT.mkdir(parents=True, exist_ok=False)
    common.atomic_write_once_json(common.CONTRACT, contract)
    common.atomic_write_once_json(
        common.STATE,
        {
            "schema_version": 1,
            "batch_id": common.BATCH_ID,
            "status": "RUNNING_RESOURCE_DIAGNOSTIC",
            "started_utc": utc_now(),
            "contract_sha256": common.sha256(common.CONTRACT),
            "completed_jobs": [],
            "active_job": None,
        },
    )
    completed: list[str] = []
    try:
        for spec in common.job_specs():
            update_state(active_job=spec["key"], completed_jobs=completed)
            print(f"START {spec['ordinal']}/4 {spec['key']} events={spec['events']} seed={spec['seed']}", flush=True)
            receipt = run_job(spec, contract, environment)
            job_report = validate(spec["key"], write=False)
            completed.append(spec["key"])
            update_state(
                active_job=None,
                completed_jobs=completed,
                last_job={
                    "key": spec["key"],
                    "wall_s": receipt["wall_s"],
                    "peak_rss_bytes": receipt["peak_process_group_rss_bytes"],
                    "validation": job_report["status"],
                },
            )
            print(
                f"PASS {spec['key']} wall={receipt['wall_s']:.3f}s "
                f"peak_rss={receipt['peak_process_group_rss_bytes']}B",
                flush=True,
            )
        final_report = validate(None, write=True)
        update_state(
            status="PASS_RESOURCE_DIAGNOSTIC_VALIDATED__NOT_MERGE_AUTHORITY",
            active_job=None,
            completed_jobs=completed,
            completed_utc=utc_now(),
            validation_report=common.rel(common.VALIDATION_REPORT),
            validation_report_sha256=common.sha256(common.VALIDATION_REPORT),
            resource_summary=common.rel(common.SUMMARY),
            resource_summary_sha256=common.sha256(common.SUMMARY),
        )
        print(json.dumps(final_report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except BaseException as exc:
        update_state(
            status="FAIL_OR_STOPPED_RESOURCE_DIAGNOSTIC",
            active_job=None,
            completed_jobs=completed,
            failed_utc=utc_now(),
            error=f"{type(exc).__name__}: {exc}",
            batch_output_bytes=common.tree_size(common.RUN_ROOT),
            free_disk_bytes=shutil.disk_usage(common.ROOT).free,
            mem_available_bytes=common.mem_available_bytes(),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
