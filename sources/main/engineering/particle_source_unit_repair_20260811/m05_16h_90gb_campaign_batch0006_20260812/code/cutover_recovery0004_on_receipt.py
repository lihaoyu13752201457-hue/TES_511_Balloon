#!/usr/bin/env python3
"""Kill the frozen recovery0003 coordinator at one atomic PASS-receipt boundary."""

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
PID = 8165
PROC_STARTTIME_TICKS = 107494
JOB_ID = "s10_neutron_buildup_S3d_O8_shard0004"
RECEIPT = RUN_ROOT / "job_receipts/stage10_seven_family" / f"{JOB_ID}.json"
OUTPUT = RUN_ROOT / "recovery0004_cutover_kill_completion.json"


def proc_starttime(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return int(raw[raw.rfind(")") + 2 :].split()[19])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite {OUTPUT}")
    if proc_starttime(PID) != PROC_STARTTIME_TICKS:
        raise SystemExit("recovery0003 PID starttime differs before watcher arm")
    armed_at = datetime.now(timezone.utc).isoformat()
    while not RECEIPT.is_file():
        if not Path(f"/proc/{PID}").exists():
            raise SystemExit("recovery0003 coordinator exited before target receipt")
        time.sleep(0.005)
    observed_at = datetime.now(timezone.utc).isoformat()
    if proc_starttime(PID) != PROC_STARTTIME_TICKS:
        raise SystemExit("recovery0003 PID starttime differs at receipt boundary")
    os.kill(PID, signal.SIGKILL)
    killed_at = datetime.now(timezone.utc).isoformat()
    for _ in range(1000):
        if not Path(f"/proc/{PID}").exists():
            break
        time.sleep(0.005)
    else:
        raise SystemExit("recovery0003 coordinator remained after SIGKILL")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or receipt.get("errors"):
        raise SystemExit("target receipt is not a clean PASS")
    if receipt.get("job", {}).get("job_id") != JOB_ID:
        raise SystemExit("target receipt job differs")
    payload = {
        "schema_version": 1,
        "status": "PASS__RECOVERY0003_KILLED_AT_ATOMIC_PASS_RECEIPT_BOUNDARY",
        "armed_at": armed_at,
        "receipt_observed_at": observed_at,
        "coordinator_killed_at": killed_at,
        "coordinator_pid": PID,
        "coordinator_proc_starttime_ticks": PROC_STARTTIME_TICKS,
        "boundary_job_id": JOB_ID,
        "boundary_receipt": str(RECEIPT.relative_to(ROOT)),
        "boundary_receipt_sha256": sha256(RECEIPT),
        "note": "SIGKILL intentionally avoided stale recovery0003 finally/publication; recovery0004 must still prove zero legacy processes and zero partial attempts before authority publication.",
    }
    with OUTPUT.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
