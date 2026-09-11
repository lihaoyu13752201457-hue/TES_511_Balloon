#!/usr/bin/env python3
"""Launch a prepared next profile after the current canonical profile passes."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
sys.path.insert(0, str(EXECUTOR))

from common import load_config, load_json, load_plan, validate_generated_bundle  # noqa: E402


def dump(path: Path, status: str, **fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "large_sim_policy": "NO_SCAN_NO_HASH_SMALL_AUTHORITIES_ONLY",
        **fields,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-config", required=True)
    parser.add_argument("--next-config", required=True)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()
    current = load_config(args.current_config)
    following = load_config(args.next_config)
    if current["profile_id"] == following["profile_id"]:
        raise RuntimeError("profile identities must differ")
    if not 1 <= args.workers <= int(following["max_workers"]):
        raise RuntimeError("next-profile worker request is outside contract")
    next_plan = load_plan(following)
    validate_generated_bundle(following, next_plan)
    next_root = Path(following["run_root"])
    next_root.mkdir(parents=True, exist_ok=True)
    chain_state = next_root / "chain_state.json"
    required_free = int(following["dynamic_reserve_bytes"]) + sum(
        int(job["estimated_bytes"]) for job in next_plan
    )
    while True:
        state_path = Path(current["run_root"]) / "controller_state.json"
        state = load_json(state_path) if state_path.is_file() else {"status": "NOT_STARTED"}
        if state.get("status") == "FAILED":
            dump(chain_state, "CURRENT_FAILED__NO_NEXT_LAUNCH", current=state)
            return 1
        complete = (
            state.get("status") == "COMPLETE"
            and state.get("profile_id") == current["profile_id"]
            and state.get("completed_count") == current["expected_jobs"]
            and not state.get("active")
            and not state.get("error")
        )
        if not complete:
            dump(
                chain_state,
                "WAITING_FOR_CURRENT_COMPLETE",
                current_profile_id=current["profile_id"],
                current_status=state.get("status", "NOT_STARTED"),
                current_completed_count=state.get("completed_count", 0),
                next_profile_id=following["profile_id"],
            )
            time.sleep(args.interval)
            continue
        free = shutil.disk_usage(next_root).free
        if free < required_free:
            dump(
                chain_state,
                "WAITING_FOR_FULL_PLAN_DISK_BUDGET",
                disk_free_bytes=free,
                required_free_bytes=required_free,
            )
            time.sleep(args.interval)
            continue
        dump(
            chain_state,
            "LAUNCHING_NEXT_PROFILE",
            current_profile_id=current["profile_id"],
            next_profile_id=following["profile_id"],
            workers=args.workers,
            disk_free_bytes=free,
            required_free_bytes=required_free,
        )
        os.execv(
            sys.executable,
            [
                sys.executable,
                str(EXECUTOR / "run.py"),
                "--config",
                str(Path(args.next_config).resolve()),
                "--workers",
                str(args.workers),
            ],
        )


if __name__ == "__main__":
    raise SystemExit(main())
