#!/usr/bin/env python3
"""Recover complete canonical delayed attempts after controller loss.

This does not repair or reinterpret transport.  It calls the canonical
executor validator, requires every stale active attempt to pass unchanged,
then performs the same active -> attempts move and receipt publication that
run_attempt() would have performed after a normal child-process exit.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


EXECUTE = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
CONFIG = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_sharded_v2/config.json")
sys.path.insert(0, str(EXECUTE))

from common import load_config, load_json, load_plan, utc_now, write_once_json  # noqa: E402
from run import append_resource, receipt_path, validate_attempt  # noqa: E402


def assert_transport_stopped(target: str) -> None:
    matches: list[str] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if target in command and ("cosima" in command or "tool/execute/run.py" in command):
            matches.append(f"{entry.name}: {command}")
    if matches:
        raise RuntimeError(f"refusing recovery while transport/controller is live: {matches}")


def main() -> int:
    config = load_config(CONFIG)
    plan = load_plan(config)
    run_root = Path(config["run_root"])
    assert_transport_stopped(str(run_root.parent))
    state = load_json(run_root / "controller_state.json")
    recovered: list[dict[str, object]] = []
    for job in plan:
        job_id = job["job_id"]
        active = run_root / "jobs" / job_id / "active"
        if not active.is_dir():
            continue
        log = active / f"{job_id}.log"
        first = json.loads(log.open("r", encoding="utf-8", errors="replace").readline())
        attempt = int(first["attempt"])
        started = datetime.fromisoformat(str(first["started_at"]).replace("Z", "+00:00"))
        ended = datetime.fromtimestamp(log.stat().st_mtime, timezone.utc)
        wall_s = max(0.0, (ended - started).total_seconds())
        peak = int((state.get("active", {}).get(job_id, {}) or {}).get("peak_rss_bytes", 0))
        result = validate_attempt(
            config,
            job,
            active,
            0,
            wall_s,
            peak,
            "completed__receipt_recovered_after_controller_loss",
        )
        if result["status"] != "PASS":
            raise RuntimeError(f"recovery validation failed for {job_id}: {result['errors']}")
        final = run_root / "jobs" / job_id / "attempts" / f"attempt{attempt:02d}"
        receipt = receipt_path(config, job_id)
        if final.exists() or receipt.exists():
            raise RuntimeError(f"recovery destination already exists for {job_id}")
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(active, final)
        result.update({
            "attempt": attempt,
            "started_at": first["started_at"],
            "ended_at": ended.isoformat(),
            "attempt_dir": str(final),
            "sim_path": str(final / f"{job_id}.inc1.id1.sim.gz"),
            "isotope_dat_path": str(final / f"{job_id}.dat.inc1.dat"),
            "log_path": str(final / f"{job_id}.log"),
            "recovery_provenance": "CANONICAL_VALIDATE_ATTEMPT_PASS_AFTER_CONTROLLER_LOSS_POST_COSIMA_EXIT",
        })
        write_once_json(receipt, result)
        append_resource(config, {
            "at": utc_now(),
            "job_id": job_id,
            "attempt": attempt,
            "status": "PASS",
            "wall_s": wall_s,
            "peak_rss_bytes": peak,
            "artifact_bytes": result["artifact_bytes"],
            "free_disk_bytes": os.statvfs(run_root).f_bavail * os.statvfs(run_root).f_frsize,
            "recovery": True,
        })
        recovered.append({
            "job_id": job_id,
            "attempt": attempt,
            "events": job["events"],
            "seed": job["seed"],
            "source_sha256": result["source_sha256"],
            "sim_path": result["sim_path"],
            "sim_bytes": result["sim_bytes"],
            "log_path": result["log_path"],
            "log_generated_events": result["log"]["generated_events"],
            "terminal_marker": result["log"]["graphics_terminal_marker"],
            "sim_header": result["sim_header"],
            "receipt_path": str(receipt),
        })
    if len(recovered) != 8 or sum(int(row["events"]) for row in recovered) != 2_000_000:
        raise RuntimeError(f"recovery closure differs from 8 jobs / 2,000,000 events: {len(recovered)}")
    audit = {
        "schema_version": 1,
        "status": "PASS__8_COMPLETE_ACTIVE_ATTEMPTS_RECOVERED_WITH_CANONICAL_VALIDATOR",
        "created_at": utc_now(),
        "controller_state_before_recovery": state,
        "recovered_jobs": recovered,
        "recovered_events": sum(int(row["events"]) for row in recovered),
        "policy": "NO_SIM_CONTENT_MODIFICATION_OR_RETRANSPORT; CANONICAL VALIDATION THEN ATOMIC PROMOTION",
    }
    write_once_json(run_root.parent / "recovery_after_controller_loss.json", audit)
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
