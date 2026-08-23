#!/usr/bin/env python3
"""Quarantine zero-byte launcher failures caused by a missing MEGAlib environment."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
RECEIPTS = PACKAGE / "outputs/02_gamma_transport/receipts"
RECEIPT_DEST = PACKAGE / "outputs/02_gamma_transport_failed_missing_megalib_env"
DATA_JOBS = Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_sg3b_gamma_expansion_20260820/jobs")
DATA_DEST = Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_sg3b_gamma_expansion_20260820_failed_missing_megalib_env")
LOGS = ROOT / "runs/m05new_sg3b_gamma_expansion_20260820/logs"
LOG_DEST = ROOT / "runs/m05new_sg3b_gamma_expansion_20260820/logs_failed_missing_megalib_env"


def main() -> None:
    failed = []
    for receipt_path in sorted(RECEIPTS.glob("m05new_sg3b_gamma_shard*.json")):
        row = json.loads(receipt_path.read_text(encoding="utf-8"))
        if row.get("status") != "FAIL":
            continue
        stderr_path = Path(row["stderr"])
        stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
        if not (
            int(row.get("returncode", -1)) == 127
            and int(row.get("sim_bytes", -1)) == 0
            and row.get("sim_header_seed") is None
            and "libSivan.so" in stderr
        ):
            raise RuntimeError(f"unexpected failure must be reviewed manually: {receipt_path}")
        failed.append((receipt_path, row, stderr_path))
    if not failed:
        raise RuntimeError("no matching failed receipts")

    RECEIPT_DEST.mkdir(parents=True, exist_ok=True)
    DATA_DEST.mkdir(parents=True, exist_ok=True)
    LOG_DEST.mkdir(parents=True, exist_ok=True)
    moved = []
    for receipt_path, row, stderr_path in failed:
        job_id = str(row["job_id"])
        job_dir = DATA_JOBS / job_id
        if job_dir.exists():
            target = DATA_DEST / job_id
            if target.exists():
                raise RuntimeError(f"quarantine target already exists: {target}")
            shutil.move(str(job_dir), str(target))
        if stderr_path.exists():
            shutil.move(str(stderr_path), str(LOG_DEST / stderr_path.name))
        shutil.move(str(receipt_path), str(RECEIPT_DEST / receipt_path.name))
        moved.append(job_id)
    audit = {
        "schema_version": 1,
        "status": "QUARANTINED__MISSING_MEGALIB_DYNAMIC_LIBRARY_ENV",
        "jobs": moved,
        "count": len(moved),
        "disposition": "zero-byte SIM directories, FAIL receipts, and stderr logs moved; no event entered any catalog",
    }
    (RECEIPT_DEST / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
