#!/usr/bin/env python3
"""Archive the single supervised-cutover orphan without deleting evidence."""

from __future__ import annotations

import os
from pathlib import Path

import resume_m05_campaign_batch0006_recovery0001 as recovery1
import resume_m05_campaign_batch0006_recovery0003_powerloss_concurrent as recovery3
import run_m05_16h_campaign_batch0006 as campaign


JOB_ID = "s10_gamma_buildup_S3d_O8_shard0008"
PARTIAL = (
    campaign.RUN_ROOT
    / "stage10_seven_family/S3d_O8/buildup/gamma/shard0008/.attempt01.partial"
)
TARGET = campaign.RUN_ROOT / "failed_attempts" / JOB_ID / "attempt01"
VALIDATION = TARGET / "validation.json"
RECEIPT = campaign.RUN_ROOT / "recovery0004_cutover_orphan_receipt.json"
CUTOVER_COMPLETION = campaign.RUN_ROOT / "recovery0004_cutover_kill_completion.json"
R3_AUTHORITY = campaign.RUN_ROOT / "recovery0003_powerloss_concurrent_authority.json"


def main() -> int:
    if RECEIPT.exists() or TARGET.exists() or not PARTIAL.is_dir():
        raise SystemExit("orphan archive precondition failed; refusing overwrite")
    if not CUTOVER_COMPLETION.is_file() or not R3_AUTHORITY.is_file():
        raise SystemExit("cutover evidence missing")
    plan = campaign.build_plan()
    jobs = {str(job["job_id"]): job for job in plan}
    job = jobs[JOB_ID]
    source = list(PARTIAL.glob("*.source"))
    if len(source) != 1 or source[0].stem != JOB_ID:
        raise SystemExit("orphan partial source differs from frozen job")
    before = recovery3.file_manifest(PARTIAL)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    os.replace(PARTIAL, TARGET)
    after = recovery3.file_manifest(TARGET)
    if before != after or PARTIAL.exists():
        raise SystemExit("atomic orphan archive hash closure failed")
    sim = TARGET / f"{JOB_ID}.inc1.id1.sim.gz"
    observation = recovery3.strict_gzip_observation(sim)
    validation = {
        "schema_version": 1,
        "status": "FAIL",
        "errors": ["cutover_companion_became_unsupervised_after_recovery0003_coordinator_boundary"],
        "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery0003_authority_sha256": campaign.sha256(R3_AUTHORITY),
        "cutover_kill_completion": campaign.rel(CUTOVER_COMPLETION),
        "cutover_kill_completion_sha256": campaign.sha256(CUTOVER_COMPLETION),
        "job": job,
        "selected_attempt": None,
        "attempt": 1,
        "attempt_dir": campaign.rel(TARGET),
        "returncode": None,
        "watchdog_reason": "orphan_transport_terminated_after_parent_cutover",
        "artifacts": after,
        "sim_gzip_observation": observation,
        "merge_eligible": False,
        "retry_contract": "exact_same_frozen_seed_events_source_job_at_attempt02",
    }
    campaign.atomic_write_once_json(VALIDATION, validation)
    campaign.atomic_write_once_json(
        RECEIPT,
        {
            "schema_version": 1,
            "status": "PASS__CUTOVER_ORPHAN_PRESERVED__NOT_MERGEABLE",
            "job_id": JOB_ID,
            "archive": campaign.rel(TARGET),
            "validation": campaign.rel(VALIDATION),
            "validation_sha256": campaign.sha256(VALIDATION),
            "artifacts_before_validation": after,
            "recovery0003_authority_sha256": campaign.sha256(R3_AUTHORITY),
            "cutover_kill_completion_sha256": campaign.sha256(CUTOVER_COMPLETION),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
