#!/usr/bin/env python3
"""Wait for one transport profile to complete, then launch another safely.

This controller reads only small JSON state/plan/config authorities.  It never
opens, scans, stats individually, or hashes SIM payloads.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from common import atomic_json, load_config, load_json, load_plan, utc_now


PACKAGE_ROOT = Path(__file__).resolve().parent


def publish(path: Path, status: str, **payload: Any) -> None:
    atomic_json(path, {
        "schema_version": 1,
        "status": status,
        "updated_at": utc_now(),
        "large_sim_policy": "NO_SCAN_NO_HASH_SMALL_AUTHORITIES_ONLY",
        **payload,
    })


def current_complete(config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    state_path = Path(config["run_root"]) / "controller_state.json"
    state = load_json(state_path) if state_path.is_file() else {"status": "NOT_STARTED"}
    complete = (
        state.get("status") == "COMPLETE"
        and state.get("profile_id") == config["profile_id"]
        and int(state.get("completed_count", -1)) == int(config["expected_jobs"])
        and not state.get("active")
        and not state.get("error")
    )
    return complete, state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-config", required=True)
    parser.add_argument("--next-config", required=True)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()

    current_path = Path(args.current_config).expanduser().resolve()
    next_path = Path(args.next_config).expanduser().resolve()
    current = load_config(current_path)
    following = load_config(next_path)
    if current["profile_id"] == following["profile_id"]:
        raise RuntimeError("current and next profiles must differ")
    if args.workers < 1 or args.workers > int(following["max_workers"]):
        raise RuntimeError("requested workers exceed next-profile contract")

    next_root = Path(following["run_root"])
    next_root.mkdir(parents=True, exist_ok=True)
    chain_state = next_root / "chain_state.json"
    plan = load_plan(following)
    estimated_artifacts = sum(int(job["estimated_bytes"]) for job in plan)
    required_free = int(following["dynamic_reserve_bytes"]) + estimated_artifacts

    while True:
        complete, state = current_complete(current)
        if state.get("status") == "FAILED":
            publish(
                chain_state,
                "CURRENT_FAILED__NO_NEXT_LAUNCH",
                current_profile_id=current["profile_id"],
                next_profile_id=following["profile_id"],
                current_error=state.get("error"),
            )
            return 1
        if not complete:
            publish(
                chain_state,
                "WAITING_FOR_CURRENT_COMPLETE",
                current_profile_id=current["profile_id"],
                current_status=state.get("status", "NOT_STARTED"),
                current_completed_count=state.get("completed_count", 0),
                next_profile_id=following["profile_id"],
            )
            time.sleep(args.interval)
            continue

        disk_free = shutil.disk_usage(next_root).free
        if disk_free < required_free:
            publish(
                chain_state,
                "WAITING_FOR_FULL_PLAN_DISK_BUDGET",
                current_profile_id=current["profile_id"],
                next_profile_id=following["profile_id"],
                disk_free_bytes=disk_free,
                required_free_bytes=required_free,
                estimated_artifact_bytes=estimated_artifacts,
                dynamic_reserve_bytes=int(following["dynamic_reserve_bytes"]),
            )
            time.sleep(args.interval)
            continue

        subprocess.run(
            [sys.executable, str(PACKAGE_ROOT / "prepare.py"), "--config", str(next_path), "--check"],
            cwd=PACKAGE_ROOT.parent.parent,
            check=True,
        )
        publish(
            chain_state,
            "LAUNCHING_NEXT_PROFILE",
            current_profile_id=current["profile_id"],
            next_profile_id=following["profile_id"],
            workers=args.workers,
            disk_free_bytes=disk_free,
            required_free_bytes=required_free,
        )
        os.execv(
            sys.executable,
            [
                sys.executable,
                str(PACKAGE_ROOT / "run.py"),
                "--config",
                str(next_path),
                "--workers",
                str(args.workers),
            ],
        )


if __name__ == "__main__":
    raise SystemExit(main())
