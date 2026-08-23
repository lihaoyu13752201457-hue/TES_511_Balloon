#!/usr/bin/env python3
"""Quarantine interrupted prompt-gamma jobs before a RAM-safe rerun."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
RECEIPTS = PACKAGE / "outputs/02_gamma_transport/receipts"
RECEIPT_DEST = PACKAGE / "outputs/02_gamma_transport_interrupted_ram_safety_20260821"
DATA_JOBS = Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_sg3b_gamma_expansion_20260820/jobs")
DATA_DEST = Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_sg3b_gamma_expansion_20260820_interrupted_ram_safety_20260821")
LOGS = ROOT / "runs/m05new_sg3b_gamma_expansion_20260820/logs"
LOG_DEST = ROOT / "runs/m05new_sg3b_gamma_expansion_20260820/logs_interrupted_ram_safety_20260821"


def main() -> None:
    failed = []
    for receipt_path in sorted(RECEIPTS.glob("m05new_sg3b_gamma_shard*.json")):
        row = json.loads(receipt_path.read_text(encoding="utf-8"))
        if row.get("status") != "FAIL":
            continue
        index = int(row["index"])
        if index not in {41, 42, 43, 45, 46, 47, 48}:
            raise RuntimeError(f"unexpected FAIL receipt: {receipt_path}")
        failed.append((receipt_path, row))
    expected = {41, 42, 43, 45, 46, 47, 48}
    found = {int(row["index"]) for _, row in failed}
    if found != expected:
        raise RuntimeError(f"interrupted set mismatch: expected {sorted(expected)}, found {sorted(found)}")

    RECEIPT_DEST.mkdir(parents=True, exist_ok=True)
    DATA_DEST.mkdir(parents=True, exist_ok=True)
    LOG_DEST.mkdir(parents=True, exist_ok=True)
    moved = []
    for receipt_path, row in failed:
        job_id = str(row["job_id"])
        job_dir = DATA_JOBS / job_id
        stderr_path = Path(row["stderr"])
        if job_dir.exists():
            target = DATA_DEST / job_id
            if target.exists():
                raise RuntimeError(f"quarantine target already exists: {target}")
            shutil.move(str(job_dir), str(target))
        if stderr_path.exists():
            shutil.move(str(stderr_path), str(LOG_DEST / stderr_path.name))
        shutil.move(str(receipt_path), str(RECEIPT_DEST / receipt_path.name))
        moved.append({
            "job_id": job_id,
            "index": int(row["index"]),
            "returncode": int(row["returncode"]),
            "sim_bytes": int(row["sim_bytes"]),
            "wall_seconds": float(row["wall_seconds"]),
        })
    audit = {
        "schema_version": 1,
        "status": "QUARANTINED__INTERRUPTED_FOR_RAM_SAFETY",
        "jobs": moved,
        "count": len(moved),
        "retained_complete_job": "m05new_sg3b_gamma_shard0044",
        "disposition": "FAIL receipts, interrupted/empty job directories, and stderr logs moved; no event from these attempts may enter a catalog",
    }
    (RECEIPT_DEST / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
