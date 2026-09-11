#!/usr/bin/env python3
"""Write-once evidence, then stop only the recovery0004 coordinator.

Already-forked workers inherit the campaign lock and ignore terminal SIGHUP.
They are deliberately left alive to finish their current exact attempts and
publish canonical PASS receipts.  This program neither launches transport nor
deletes or overwrites any campaign artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
CODE = ROOT / "engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/code"
CONTROLLER = CODE / "resume_m05_campaign_batch0006_recovery0004_live_memory_dynamic.py"
CONTROLLER_SHA256 = "5d7a58f9531e05b58dd552fd534704e039d7c2cd5628bf90972425dbe1854707"
COORDINATOR_PID = 28798
INTENT = RUN_ROOT / "recovery0006_six_to_one_replan_cutover_intent.json"
STOP_RECEIPT = RUN_ROOT / "recovery0006_replan_coordinator_stop.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: object) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def proc_row(pid: int) -> dict[str, object]:
    proc = Path(f"/proc/{pid}")
    raw = proc.joinpath("stat").read_text(encoding="utf-8")
    tail = raw[raw.rfind(")") + 2 :].split()
    cmdline = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").strip()
    return {
        "pid": pid,
        "ppid": int(tail[1]),
        "pgid": int(tail[2]),
        "proc_starttime_ticks": int(tail[19]),
        "cmdline": cmdline.decode("utf-8", errors="replace"),
        "cmdline_sha256": hashlib.sha256(cmdline).hexdigest(),
    }


def descendants(parent: int) -> list[dict[str, object]]:
    rows: dict[int, dict[str, object]] = {}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            row = proc_row(int(proc.name))
        except (OSError, ValueError, IndexError):
            continue
        rows[int(row["pid"])] = row
    selected: list[dict[str, object]] = []
    frontier = [parent]
    seen: set[int] = set()
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        children = [row for row in rows.values() if int(row["ppid"]) == current]
        selected.extend(children)
        frontier.extend(int(row["pid"]) for row in children)
    return sorted(selected, key=lambda row: int(row["pid"]))


def receipt_manifest() -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for path in sorted((RUN_ROOT / "job_receipts").rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS" or payload.get("errors"):
            raise RuntimeError(f"non-PASS canonical receipt at cutover: {path}")
        job = payload.get("job", {})
        manifest.append(
            {
                "job_id": str(job.get("job_id")),
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "events": int(job.get("events", 0)),
            }
        )
    return sorted(manifest, key=lambda row: str(row["job_id"]))


def partial_manifest() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(RUN_ROOT.glob("stage*/**/.attempt*.partial")):
        if not path.is_dir():
            continue
        sources = list(path.glob("*.source"))
        job_id = sources[0].stem if len(sources) == 1 else None
        rows.append({"job_id": job_id, "path": str(path.relative_to(ROOT))})
    return rows


def write_once(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    if INTENT.exists() or STOP_RECEIPT.exists():
        raise SystemExit("refusing to overwrite recovery0006 cutover evidence")
    if sha256(CONTROLLER) != CONTROLLER_SHA256:
        raise SystemExit("recovery0004 controller hash drift")
    coordinator = proc_row(COORDINATOR_PID)
    if CONTROLLER.name not in str(coordinator["cmdline"]):
        raise SystemExit("resolved PID is not the frozen recovery0004 coordinator")
    inputs = {
        "global_contract": RUN_ROOT / "global_contract.json",
        "seed_registry": RUN_ROOT / "seed_registry.json",
        "recovery0004_authority": RUN_ROOT / "recovery0004_live_memory_dynamic_authority.json",
        "recovery0004_cutover_receipt": RUN_ROOT / "recovery0004_cutover_receipt.json",
    }
    before = receipt_manifest()
    active = descendants(COORDINATOR_PID)
    partials = partial_manifest()
    intent = {
        "schema_version": 1,
        "status": "INTENT__USER_AUTHORIZED_SAVE_DRAIN_AND_REPLAN_6_TO_1",
        "created_at": utc_now(),
        "coordinator": coordinator,
        "controller_path": str(CONTROLLER.relative_to(ROOT)),
        "controller_sha256": CONTROLLER_SHA256,
        "input_hashes": {name: sha256(path) for name, path in inputs.items()},
        "receipt_manifest_before": before,
        "receipt_manifest_before_sha256": json_sha256(before),
        "pass_receipts_before": len(before),
        "pass_events_before": sum(int(row["events"]) for row in before),
        "active_descendants_before": active,
        "partial_attempts_before": partials,
        "authorization": {
            "stop_new_launches_now": True,
            "allow_active_attempts_to_finish_and_publish_receipts": True,
            "remaining_frozen_jobs_replaced_by_fresh_seed_six_to_one_super_shards": True,
            "absolute_worker_cap": 8,
            "projected_mem_available_floor_bytes": int(1.5 * 1024**3),
            "preserve_all_prior_artifacts": True,
        },
        "unchanged": [
            "base source spectra and flux",
            "geometry",
            "physics list and cuts",
            "detector and veto",
            "geometry/mode/family merge domains",
        ],
    }
    write_once(INTENT, intent)
    intent_sha = sha256(INTENT)

    # SIGKILL deliberately avoids recovery0004's signal handler and stale
    # partial-final publications.  Descendant workers are not signalled.
    os.kill(COORDINATOR_PID, signal.SIGKILL)
    killed_at = utc_now()
    for _ in range(1000):
        if not Path(f"/proc/{COORDINATOR_PID}").exists():
            break
        time.sleep(0.005)
    else:
        raise SystemExit("recovery0004 coordinator remained after SIGKILL")
    write_once(
        STOP_RECEIPT,
        {
            "schema_version": 1,
            "status": "PASS__RECOVERY0004_COORDINATOR_STOPPED__ACTIVE_WORKERS_LEFT_TO_DRAIN",
            "stopped_at": killed_at,
            "intent": str(INTENT.relative_to(ROOT)),
            "intent_sha256": intent_sha,
            "coordinator_pid": COORDINATOR_PID,
            "coordinator_proc_starttime_ticks": int(coordinator["proc_starttime_ticks"]),
            "signal": "SIGKILL",
            "descendants_not_signalled": True,
            "active_descendants_at_stop": active,
            "partial_attempts_at_stop": partials,
        },
    )
    print(json.dumps({"intent": str(INTENT), "intent_sha256": intent_sha,
                      "stop_receipt": str(STOP_RECEIPT), "active_to_drain": len(partials)},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
