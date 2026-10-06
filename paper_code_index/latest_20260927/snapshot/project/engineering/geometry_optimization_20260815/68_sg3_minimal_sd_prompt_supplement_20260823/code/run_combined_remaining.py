#!/usr/bin/env python3
"""Run SG3-minimal remaining events beside the resumable SH3 remainder."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
MINIMAL_PREP = PACKAGE / "MINIMAL_PRODUCTION_PREPARATION.json"
OLD_PACKAGE = PACKAGE.parent / "67_m05new_zero_prompt_statistics_20260823"
OLD_PREP = OLD_PACKAGE / "PREPARATION.json"
RUNNER = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")
STATE = PACKAGE / "COMBINED_REMAINING_SUPERVISOR_STATE.json"
LOG_ROOT = PACKAGE / "production_logs"
FAMILY_ORDER = ("alpha", "p", "eplus", "n")
WORKER_CAP = 1
STOP = False
CHILDREN: dict[str, subprocess.Popen[str]] = {}
HANDLES: dict[str, Any] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path: Path, payload: dict) -> None:
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(partial, path)


def request_stop(signum, frame) -> None:
    del signum, frame
    global STOP
    STOP = True


def close_handles() -> None:
    for handle in HANDLES.values():
        try:
            handle.close()
        except OSError:
            pass
    HANDLES.clear()


def stop_children() -> None:
    for child in CHILDREN.values():
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 20
    for child in CHILDREN.values():
        if child.poll() is None:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()


def complete(row: dict) -> bool:
    state = Path(row["run_root"]) / "controller_state.json"
    return state.is_file() and load(state).get("status") == "COMPLETE"


def publish(status: str, completed: list[str], family: str | None, error: str | None = None) -> None:
    atomic(
        STATE,
        {
            "schema_version": 1,
            "status": status,
            "updated_at": now(),
            "family_order": list(FAMILY_ORDER),
            "completed_families": completed,
            "current_family": family,
            "worker_cap_per_geometry": WORKER_CAP,
            "active_controllers": {
                geometry: {"pid": child.pid, "returncode": child.poll()}
                for geometry, child in CHILDREN.items()
            },
            "error": error,
        },
    )


def rows() -> dict[tuple[str, str], dict]:
    minimal = load(MINIMAL_PREP)
    old = load(OLD_PREP)
    result = {("sg3_minimal", row["family"]): row for row in minimal["bundles"]}
    for row in old["bundles"]:
        if row["geometry"] == "sh3" and row["family"] in FAMILY_ORDER:
            result[("sh3", row["family"])] = row
    expected = {(geometry, family) for geometry in ("sg3_minimal", "sh3") for family in FAMILY_ORDER}
    if set(result) != expected:
        raise RuntimeError("combined remaining bundle matrix is incomplete")
    return result


def run_family(family: str, matrix: dict, completed: list[str]) -> None:
    CHILDREN.clear()
    HANDLES.clear()
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for geometry in ("sg3_minimal", "sh3"):
        row = matrix[(geometry, family)]
        if complete(row):
            continue
        log_path = LOG_ROOT / f"{geometry}_{family}.controller.log"
        handle = log_path.open("a", encoding="utf-8", buffering=1)
        handle.write(
            json.dumps(
                {
                    "event": "combined_supervisor_launch",
                    "at": now(),
                    "geometry": geometry,
                    "family": family,
                    "workers": WORKER_CAP,
                    "config": row["config"],
                },
                sort_keys=True,
            )
            + "\n"
        )
        child = subprocess.Popen(
            [sys.executable, str(RUNNER), "--config", row["config"], "--workers", str(WORKER_CAP)],
            cwd=str(PACKAGE),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        CHILDREN[geometry] = child
        HANDLES[geometry] = handle
    publish("RUNNING", completed, family)
    while CHILDREN:
        if STOP:
            raise RuntimeError("supervisor stop requested")
        codes = {geometry: child.poll() for geometry, child in CHILDREN.items()}
        failed = {geometry: code for geometry, code in codes.items() if code not in (None, 0)}
        if failed:
            raise RuntimeError(f"controller failed in {family}: {failed}")
        if all(code == 0 for code in codes.values()):
            break
        publish("RUNNING", completed, family)
        time.sleep(10)
    for geometry in CHILDREN:
        if not complete(matrix[(geometry, family)]):
            raise RuntimeError(f"zero exit without COMPLETE: {geometry}/{family}")


def main() -> int:
    if not MINIMAL_PREP.is_file() or not OLD_PREP.is_file() or not RUNNER.is_file():
        raise FileNotFoundError("required preparation/runner missing")
    matrix = rows()
    completed: list[str] = []
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    publish("STARTING", completed, None)
    try:
        for family in FAMILY_ORDER:
            run_family(family, matrix, completed)
            close_handles()
            CHILDREN.clear()
            completed.append(family)
            publish("RUNNING", completed, None)
        publish("COMPLETE", completed, None)
        return 0
    except BaseException as exc:
        stop_children()
        publish("STOPPED" if STOP else "FAILED", completed, family if "family" in locals() else None, str(exc))
        raise
    finally:
        close_handles()


if __name__ == "__main__":
    raise SystemExit(main())
