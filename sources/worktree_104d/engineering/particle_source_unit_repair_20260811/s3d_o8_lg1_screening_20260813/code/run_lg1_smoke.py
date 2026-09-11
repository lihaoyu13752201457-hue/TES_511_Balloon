#!/usr/bin/env python3
"""Print or explicitly launch the frozen serial LG1 first-pass smoke plan.

Nothing runs unless both ``--launch`` and the exact confirmation token are
provided.  Attempts are write-once, serial, and guarded by disk, file-size,
aggregate-output, and wall-time limits.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_lg1_smoke_inputs as build
import validate_lg1_smoke as validate


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tree_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return 0
    for directory, _, files in os.walk(root):
        base = Path(directory)
        for name in files:
            try:
                total += (base / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def nearest_existing_ancestor(path: Path) -> Path:
    candidate = path.absolute()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise RuntimeError(f"no existing disk-usage anchor for {path}")
        candidate = parent
    return candidate


def free_bytes_for(path: Path) -> int:
    return shutil.disk_usage(nearest_existing_ancestor(path)).free


def sim_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*.sim*") if path.is_file()]


def terminate(proc: subprocess.Popen[Any]) -> None:
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


def child_limits(file_limit: int) -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def transport_environment(cosima: Path) -> tuple[dict[str, str], dict[str, Any]]:
    environment = dict(os.environ)
    setup = cosima.parent / "source-megalib.sh"
    if setup.is_file():
        result = subprocess.run(
            ["bash", "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(setup)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to load MEGAlib environment from {setup}")
        environment = {}
        for item in result.stdout.split(b"\0"):
            if item and b"=" in item:
                key, value = item.split(b"=", 1)
                environment[key.decode(errors="strict")] = value.decode(errors="strict")
    descriptor = {
        key: environment[key]
        for key in sorted(environment)
        if key in {"MEGALIB", "ROOTSYS", "LD_LIBRARY_PATH"} or key.startswith("G4") or key.startswith("GEANT4")
    }
    return environment, {"setup_script": str(setup) if setup.is_file() else None, "relevant_variables": descriptor}


def print_plan(plan: dict[str, Any]) -> None:
    preflight = validate.validate_preflight(plan, require_clean_output=True, rescan_registry=True)
    free = free_bytes_for(Path(plan["run_root"]))
    payload = {
        "status": "PRINT_ONLY__NO_COSIMA_RUN",
        "static_preflight": preflight["status"],
        "run_root": plan["run_root"],
        "jobs": plan["totals"]["jobs"],
        "paired_cells": plan["totals"]["paired_cells"],
        "events_if_launched": plan["totals"]["transport_events_if_launched"],
        "current_free_bytes": free,
        "minimum_free_bytes": plan["limits"]["minimum_free_bytes"],
        "free_space_gate_now": "PASS" if free >= plan["limits"]["minimum_free_bytes"] else "FAIL",
        "aggregate_output_cap_bytes": plan["limits"]["aggregate_output_max_bytes"],
        "single_sim_cap_bytes": plan["limits"]["single_sim_max_bytes"],
        "per_job_timeout_seconds": plan["limits"]["per_job_timeout_seconds"],
        "worst_case_serial_wall_seconds": plan["limits"]["worst_case_wall_seconds"],
        "confirmation_token": plan["confirmation_token"],
        "jobs_detail": [
            {
                "job_id": job["job_id"],
                "geometry": job["geometry_key"],
                "seed": job["seed"],
                "n_events": job["n_events"],
                "eventlist": job["eventlist"],
            }
            for job in plan["jobs"]
        ],
        "claim_boundary": plan["claim_boundary"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_job(job: dict[str, Any], plan: dict[str, Any], environment: dict[str, str], environment_descriptor: dict[str, Any]) -> dict[str, Any]:
    limits = plan["limits"]
    run_root = Path(plan["run_root"])
    partial = Path(job["partial_attempt_dir"])
    final = Path(job["final_attempt_dir"])
    job_root = partial.parent
    if job_root.exists() or partial.exists() or final.exists():
        raise RuntimeError(f"write-once job path already exists: {job['job_id']}")
    free = free_bytes_for(run_root)
    if free < limits["minimum_free_bytes"]:
        raise RuntimeError(f"free-space floor failed before {job['job_id']}: {free} < {limits['minimum_free_bytes']}")
    if tree_bytes(run_root) >= limits["aggregate_output_max_bytes"]:
        raise RuntimeError("aggregate output cap already reached")

    partial.mkdir(parents=True, exist_ok=False)
    log_path = partial / "cosima.log"
    receipt_path = partial / "receipt.json"
    command = [plan["cosima"]["path"], "-s", str(job["seed"]), job["source"]]
    started = time.monotonic()
    failure = None
    with log_path.open("x", encoding="utf-8") as log:
        log.write(f"# started_utc={utc_now()}\n# command={json.dumps(command)}\n")
        log.flush()
        proc = subprocess.Popen(
            command,
            cwd=build.ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=lambda: child_limits(limits["single_sim_max_bytes"]),
        )
        while proc.poll() is None:
            elapsed = time.monotonic() - started
            aggregate = tree_bytes(run_root)
            free = free_bytes_for(run_root)
            oversized = [path for path in sim_files(run_root) if path.stat().st_size >= limits["single_sim_max_bytes"]]
            if elapsed >= limits["per_job_timeout_seconds"]:
                failure = f"per-job timeout at {elapsed:.1f}s"
            elif free < limits["minimum_free_bytes"]:
                failure = f"free-space floor crossed: {free}"
            elif aggregate >= limits["aggregate_output_max_bytes"]:
                failure = f"aggregate output cap crossed: {aggregate}"
            elif oversized:
                failure = f"single-SIM cap crossed: {oversized[0]}"
            if failure:
                terminate(proc)
                break
            time.sleep(1.0)
        returncode = proc.wait()
        elapsed = time.monotonic() - started
        log.write(f"\n# ended_utc={utc_now()}\n# returncode={returncode}\n# elapsed_seconds={elapsed:.6f}\n")
        log.flush()

    base_receipt = {
        "schema_version": 1,
        "job_id": job["job_id"],
        "cell_id": job["cell_id"],
        "geometry_key": job["geometry_key"],
        "seed": job["seed"],
        "source": job["source"],
        "source_sha256": job["source_sha256"],
        "command": command,
        "elapsed_seconds": elapsed,
        "returncode": returncode,
        "environment": environment_descriptor,
        "limits": limits,
    }
    if failure or returncode != 0:
        write_json_exclusive(receipt_path, {**base_receipt, "status": "FAILED_WRITE_ONCE_ATTEMPT", "failure": failure or f"Cosima exit {returncode}"})
        raise RuntimeError(f"{job['job_id']} failed; partial attempt retained: {failure or returncode}")

    matches = sorted(path for path in partial.glob(f"{job['job_id']}*.sim.gz") if path.is_file())
    if len(matches) != 1:
        write_json_exclusive(receipt_path, {**base_receipt, "status": "FAILED_WRITE_ONCE_ATTEMPT", "failure": f"expected one SIM.gz, found {len(matches)}"})
        raise RuntimeError(f"{job['job_id']}: expected one SIM.gz, found {len(matches)}")
    record_validation = validate.validate_sim_file(job, matches[0], plan)
    write_json_exclusive(
        receipt_path,
        {**base_receipt, "status": "PASS_ATTEMPT_RECORD_INTEGRITY", "record_validation_before_atomic_promotion": record_validation},
    )
    partial.rename(final)
    return {"job_id": job["job_id"], "status": "PASS", "final_attempt_dir": str(final), "elapsed_seconds": elapsed}


def launch(plan: dict[str, Any], confirmation: str) -> None:
    if confirmation != plan["confirmation_token"]:
        raise RuntimeError(f"launch requires --confirm {plan['confirmation_token']}")
    preflight = validate.validate_preflight(plan, require_clean_output=True, rescan_registry=True)
    run_root = Path(plan["run_root"])
    if run_root.exists():
        raise RuntimeError(f"write-once run root already exists: {run_root}")
    free = free_bytes_for(run_root)
    if free < plan["limits"]["minimum_free_bytes"]:
        raise RuntimeError(f"free-space floor failed: {free} < {plan['limits']['minimum_free_bytes']}")
    environment, descriptor = transport_environment(Path(plan["cosima"]["path"]))
    run_root.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(exist_ok=False)
    results = []
    for job in plan["jobs"]:
        results.append(run_job(job, plan, environment, descriptor))
    dynamic = validate.validate_outputs(plan)
    print(
        json.dumps(
            {
                "status": dynamic["status"],
                "static_preflight": preflight["status"],
                "jobs": results,
                "aggregate_sim_bytes": dynamic["aggregate_sim_bytes"],
                "claim_boundary": plan["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print-plan", action="store_true", help="print the validated plan without running Cosima")
    mode.add_argument("--launch", action="store_true", help="launch only with the exact confirmation token")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--plan", type=Path, default=build.PLAN)
    args = parser.parse_args()
    plan = validate.load_plan(args.plan)
    if args.print_plan:
        if args.confirm:
            parser.error("--confirm is meaningful only with --launch")
        print_plan(plan)
    else:
        launch(plan, args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
