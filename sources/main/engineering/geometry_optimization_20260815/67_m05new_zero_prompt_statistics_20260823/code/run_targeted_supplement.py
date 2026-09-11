#!/usr/bin/env python3
"""Run the prepared SG3/SH3 zero-prompt supplement in bounded phases.

Each phase launches the retained guarded runner once for SG3 and once for SH3.
The per-geometry worker count is stored in PREPARATION.json, so the aggregate
Cosima concurrency is four for moderate families and two for eplus/neutrons.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


PACKAGE = Path(__file__).resolve().parents[1]
PREPARATION = PACKAGE / "PREPARATION.json"
STATE = PACKAGE / "SUPERVISOR_STATE.json"
LOG_ROOT = PACKAGE / "logs"
RUNNER = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")

# The first production pass showed that concurrent alpha transport can push
# memory full-stall PSI above the retained watchdog ceiling even while nominal
# MemAvailable remains healthy.  Resume alpha at one Cosima per geometry; all
# completed receipts remain reusable and the other phase limits are unchanged.
PHASE_WORKER_CAPS = {"alpha": 1}

STOP = False
CHILDREN: dict[str, subprocess.Popen[str]] = {}
HANDLES: dict[str, TextIO] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, path)


def request_stop(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True
    for child in tuple(CHILDREN.values()):
        if child.poll() is None:
            child.send_signal(signal.SIGTERM)


def close_handles() -> None:
    for handle in tuple(HANDLES.values()):
        try:
            handle.close()
        except OSError:
            pass
    HANDLES.clear()


def stop_children() -> None:
    for child in tuple(CHILDREN.values()):
        if child.poll() is None:
            child.send_signal(signal.SIGTERM)
    deadline = time.monotonic() + 45.0
    while time.monotonic() < deadline and any(child.poll() is None for child in CHILDREN.values()):
        time.sleep(0.5)
    # A retained runner normally exits within its five-second poll interval.
    # Escalate only the controller itself after that grace period; its own
    # signal path has already terminated and reaped active Cosima groups.
    for child in tuple(CHILDREN.values()):
        if child.poll() is None:
            child.kill()
    for child in tuple(CHILDREN.values()):
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def bundle_index(preparation: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in preparation.get("bundles", []):
        key = (str(row.get("geometry")), str(row.get("family")))
        if key in result:
            raise RuntimeError(f"duplicate prepared bundle: {key}")
        result[key] = row
    expected = {
        (geometry, family)
        for family in preparation["family_order"]
        for geometry in ("sg3", "sh3")
    }
    if set(result) != expected:
        raise RuntimeError("prepared bundle matrix is incomplete or contains extras")
    return result


def controller_complete(row: dict[str, Any]) -> bool:
    state = Path(row["run_root"]) / "controller_state.json"
    return state.is_file() and load_json(state).get("status") == "COMPLETE"


def publish(
    *,
    status: str,
    family_order: list[str],
    completed: list[str],
    current_family: str | None,
    phase: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    atomic_json(STATE, {
        "schema_version": 1,
        "status": status,
        "updated_at": utc_now(),
        "family_order": family_order,
        "completed_families": completed,
        "current_family": current_family,
        "active_controllers": {
            geometry: {"pid": child.pid, "returncode": child.poll()}
            for geometry, child in CHILDREN.items()
        },
        "phase": phase,
        "error": error,
    })


def run_phase(
    family: str,
    rows: dict[tuple[str, str], dict[str, Any]],
    family_order: list[str],
    completed: list[str],
) -> None:
    CHILDREN.clear()
    HANDLES.clear()
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    phase: dict[str, Any] = {
        "family": family,
        "started_at": utc_now(),
        "geometries": {},
    }
    for geometry in ("sg3", "sh3"):
        row = rows[(geometry, family)]
        workers = min(int(row["workers"]), PHASE_WORKER_CAPS.get(family, int(row["workers"])))
        if controller_complete(row):
            phase["geometries"][geometry] = {
                "status": "ALREADY_COMPLETE",
                "config": row["config"],
                "workers": workers,
            }
            continue
        log_path = LOG_ROOT / f"{geometry}_{family}.controller.log"
        handle = log_path.open("a", encoding="utf-8", buffering=1)
        handle.write(json.dumps({
            "event": "supervisor_launch",
            "at": utc_now(),
            "family": family,
            "geometry": geometry,
            "config": row["config"],
            "workers": workers,
        }, sort_keys=True) + "\n")
        command = [
            sys.executable,
            str(RUNNER),
            "--config",
            row["config"],
            "--workers",
            str(workers),
        ]
        child = subprocess.Popen(
            command,
            cwd=str(PACKAGE),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        CHILDREN[geometry] = child
        HANDLES[geometry] = handle
        phase["geometries"][geometry] = {
            "status": "RUNNING",
            "pid": child.pid,
            "config": row["config"],
            "workers": workers,
            "log": str(log_path),
        }
    publish(
        status="RUNNING",
        family_order=family_order,
        completed=completed,
        current_family=family,
        phase=phase,
    )
    if not CHILDREN:
        return
    while True:
        if STOP:
            raise RuntimeError("supervisor stop requested")
        returncodes = {geometry: child.poll() for geometry, child in CHILDREN.items()}
        failed = {geometry: rc for geometry, rc in returncodes.items() if rc not in (None, 0)}
        if failed:
            raise RuntimeError(f"controller failed in {family}: {failed}")
        if all(rc == 0 for rc in returncodes.values()):
            break
        publish(
            status="RUNNING",
            family_order=family_order,
            completed=completed,
            current_family=family,
            phase=phase,
        )
        time.sleep(10.0)
    for geometry in CHILDREN:
        if not controller_complete(rows[(geometry, family)]):
            raise RuntimeError(f"controller exited zero without COMPLETE state: {geometry}/{family}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(load_json(STATE) if STATE.is_file() else {"status": "NOT_STARTED"}, indent=2))
        return 0
    if not PREPARATION.is_file():
        raise FileNotFoundError(f"prepare bundles first: {PREPARATION}")
    if not RUNNER.is_file():
        raise FileNotFoundError(RUNNER)
    preparation = load_json(PREPARATION)
    if preparation.get("status") != "PREPARED__NOT_YET_TRANSPORTED":
        raise RuntimeError("preparation identity/status is not runnable")
    family_order = [str(item) for item in preparation["family_order"]]
    rows = bundle_index(preparation)
    completed: list[str] = []
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    publish(
        status="STARTING",
        family_order=family_order,
        completed=completed,
        current_family=None,
    )
    try:
        for family in family_order:
            run_phase(family, rows, family_order, completed)
            close_handles()
            CHILDREN.clear()
            completed.append(family)
            publish(
                status="RUNNING",
                family_order=family_order,
                completed=completed,
                current_family=None,
            )
        publish(
            status="COMPLETE",
            family_order=family_order,
            completed=completed,
            current_family=None,
        )
        return 0
    except BaseException as exc:
        stop_children()
        publish(
            status="STOPPED" if STOP else "FAILED",
            family_order=family_order,
            completed=completed,
            current_family=(family if "family" in locals() else None),
            error=str(exc),
        )
        raise
    finally:
        close_handles()


if __name__ == "__main__":
    raise SystemExit(main())
