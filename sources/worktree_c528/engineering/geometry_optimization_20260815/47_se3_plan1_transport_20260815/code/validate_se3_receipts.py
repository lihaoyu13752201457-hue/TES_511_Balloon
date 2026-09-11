#!/usr/bin/env python3
"""Validate Plan-1 receipts without reopening or hashing large SIM files."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from run_se3_plan1 import (
    execution_exclusions,
    load_plan,
    load_receipt,
    refresh_aggregate,
    receipt_path,
)
from se3_plan1_common import (
    DYNAMIC_RESERVE_BYTES,
    FAMILIES,
    PACKAGE_ROOT,
    PROFILE_ID,
    SE3_SETUP,
    SHARDS,
    S3D_HISTORIES,
    atomic_json,
    sha256,
    utc_now,
    validate_shards,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("background", "delayed", "signal", "all"), default="background")
    args = parser.parse_args()
    validate_shards()
    plan = load_plan()
    exclusions = execution_exclusions()
    selected_plan = plan if args.stage == "all" else [row for row in plan if row["stage"] == args.stage]
    selected_plan = [row for row in selected_plan if row["job_id"] not in exclusions]
    errors: list[str] = []
    receipts: list[dict[str, Any]] = []
    receipt_records: list[dict[str, Any]] = []
    for job in selected_plan:
        receipt = load_receipt(job["job_id"])
        if receipt is None:
            errors.append(f"missing PASS receipt: {job['job_id']}")
            continue
        receipts.append(receipt)
        path = receipt_path(job["job_id"])
        receipt_records.append({"job_id": job["job_id"], "path": str(path), "sha256": sha256(path)})
        for key in ("geometry", "mode", "family", "events", "seed", "source_path", "setup_path"):
            expected = job[key]
            if receipt.get(key) != expected:
                errors.append(f"{job['job_id']} {key}: receipt={receipt.get(key)!r} plan={expected!r}")
        if receipt["log"].get("generated_events") != job["events"]:
            errors.append(f"generated event mismatch: {job['job_id']}")
        if not receipt["log"].get("graphics_terminal_marker"):
            errors.append(f"terminal marker missing: {job['job_id']}")
        if job["stage"] == "background" and (
            not receipt["isotope_dat"].get("TT_s") or receipt["isotope_dat"]["TT_s"] <= 0
        ):
            errors.append(f"non-positive TT: {job['job_id']}")
        if Path(str(receipt["sim_header"].get("geometry"))).resolve() != Path(job["setup_path"]).resolve():
            errors.append(f"SIM header setup mismatch: {job['job_id']}")
        if receipt["sim_header"].get("seed") != job["seed"]:
            errors.append(f"SIM header seed mismatch: {job['job_id']}")
        if receipt.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
            errors.append(f"SIM digest policy mismatch: {job['job_id']}")

    sim_paths = [receipt["sim_path"] for receipt in receipts]
    duplicates = [path for path, count in Counter(sim_paths).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate selected SIM paths: {duplicates}")
    seeds: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for job in selected_plan:
        seeds[job["seed"]].append(job)
    for seed, rows in seeds.items():
        if len(rows) == 1:
            continue
        if not (len(rows) == 2 and all(row["paired_seed_exception"] for row in rows) and len({row["seed_identity"] for row in rows}) == 1):
            errors.append(f"unapproved repeated seed {seed}: {[row['job_id'] for row in rows]}")

    cell_summary: list[dict[str, Any]] = []
    if args.stage in ("background", "all"):
        background_plan = [row for row in selected_plan if row["stage"] == "background"]
        background_receipts = {receipt["job_id"]: receipt for receipt in receipts if receipt["stage"] == "background"}
        for mode in ("instant", "buildup"):
            for family in FAMILIES:
                rows = [row for row in background_plan if row["mode"] == mode and row["family"] == family]
                target = math.ceil(S3D_HISTORIES[(mode, family)] / 3)
                if sum(row["events"] for row in rows) != target:
                    errors.append(f"ceil target mismatch: {mode}/{family}")
                if target <= 100_000 and len(rows) != 1:
                    errors.append(f"target <=100k was split: {mode}/{family}")
                if target > 100_000 and any(row["events"] < 100_000 for row in rows):
                    errors.append(f"shard <100k: {mode}/{family}")
                selected = [background_receipts[row["job_id"]] for row in rows if row["job_id"] in background_receipts]
                cell_summary.append({
                    "mode": mode,
                    "family": family,
                    "s3d_histories": S3D_HISTORIES[(mode, family)],
                    "target_histories": target,
                    "planned_jobs": len(rows),
                    "validated_jobs": len(selected),
                    "validated_histories": sum(int(receipt["events"]) for receipt in selected),
                    "sum_TT_s": math.fsum(float(receipt["isotope_dat"]["TT_s"]) for receipt in selected),
                    "RP_record_count": sum(int(receipt["isotope_dat"]["RP_record_count"]) for receipt in selected),
                    "sim_bytes": sum(int(receipt["sim_bytes"]) for receipt in selected),
                    "artifact_bytes": sum(int(receipt["artifact_bytes"]) for receipt in selected),
                    "seeds": [int(receipt["seed"]) for receipt in selected],
                })
        if len(background_plan) != 21:
            errors.append(f"background job count {len(background_plan)} != 21")
        if sum(row["events"] for row in background_plan if row["mode"] == "instant") != 1_280_693:
            errors.append("instant total mismatch")
        if sum(row["events"] for row in background_plan if row["mode"] == "buildup") != 1_015_492:
            errors.append("buildup total mismatch")

    aggregate = refresh_aggregate(plan)
    validation = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "validated_at": utc_now(),
        "scope": args.stage,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "sim_validation_policy": "RECEIPT_PATH_SIZE_AND_PREVIOUS_HEADER_EVIDENCE_ONLY__NO_SIM_REOPEN_OR_HASH",
        "planned_jobs_in_scope": len(selected_plan),
        "execution_exclusions": exclusions,
        "validated_jobs_in_scope": len(receipts),
        "validated_events_in_scope": sum(int(receipt["events"]) for receipt in receipts),
        "receipt_records": receipt_records,
        "cell_summary": cell_summary,
        "projection": aggregate["projection"],
        "dynamic_reserve_pass": aggregate["projection"]["projected_final_free_bytes"] >= DYNAMIC_RESERVE_BYTES,
    }
    atomic_json(PACKAGE_ROOT / f"audit/se3_plan1_{args.stage}_receipt_validation.json", validation)
    atomic_json(PACKAGE_ROOT / "audit/se3_plan1_statistics_validation.json", validation)
    print(json.dumps(validation, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
