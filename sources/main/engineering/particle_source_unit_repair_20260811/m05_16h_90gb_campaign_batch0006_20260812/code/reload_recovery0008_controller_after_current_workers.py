#!/usr/bin/env python3
"""Drain-only same-namespace hot reload helper for recovery0008.

This thin wrapper reuses the proven cgroup-v2 coordinator freezer.  It moves
only the live recovery0008 coordinator into a dedicated frozen child cgroup;
already-forked workers remain runnable and may finish/publish their current
receipts.  After zero descendants and zero partial attempts, it kills only the
frozen coordinator, proves the campaign flock is available, and writes the
reload completion once.  It neither publishes a final nor launches transport,
and it computes no hashes and opens no gzip artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cutover_recovery0006_to_recovery0007_scheduler as freezer


ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
R8_ROOT = RUN_ROOT / "recovery0008_current_attempt_disk_admission"

freezer.R6_ROOT = R8_ROOT
freezer.R6_AUTHORITY = R8_ROOT / "authority.json"
freezer.R6_SEED_REGISTRY = R8_ROOT / "seed_registry.json"
freezer.R6_FINAL = R8_ROOT / "final_umbrella.json"
freezer.CONTROLLER_NAME = "resume_m05_campaign_batch0006_recovery0008_disk_admission.py"
freezer.INTENT = RUN_ROOT / "recovery0008_controller_reload_intent.json"
freezer.COMPLETION = RUN_ROOT / "recovery0008_controller_reload_completion.json"
freezer.INTENT_STATUS = "INTENT__RECOVERY0008_SAME_NAMESPACE_CONTROLLER_RELOAD_AFTER_CURRENT_WORKERS"
freezer.COMPLETION_STATUS = "PASS__RECOVERY0008_CONTROLLER_FROZEN_DRAINED_AND_STOPPED__SAME_NAMESPACE_RELOAD_MAY_START"
_BASE_SELF_TEST = freezer.self_test


def authority_declarations() -> dict[str, Any]:
    authority = freezer.load_json(freezer.R6_AUTHORITY)
    controller = authority.get("controller") if isinstance(authority.get("controller"), dict) else {}
    scheduler = authority.get("scheduler") if isinstance(authority.get("scheduler"), dict) else {}
    return {
        "authority_path": freezer.relative(freezer.R6_AUTHORITY),
        "authority_status": authority.get("status"),
        "recovery_id": authority.get("recovery_id"),
        "controller_path": controller.get("path"),
        "controller_hash_computed_or_required": controller.get("hash_computed_or_required"),
        "effective_pending_plan_declared_sha256": authority.get(
            "effective_pending_plan_declared_sha256"
        ),
        "seed_registry_path": freezer.relative(freezer.R6_SEED_REGISTRY),
        "minimum_target_workers": scheduler.get("minimum_target_workers"),
        "absolute_worker_cap": scheduler.get("absolute_worker_cap"),
        "maximum_exact_attempts": scheduler.get("maximum_exact_attempts"),
        "note": "declarations copied without computing hashes or reopening gzip artifacts",
    }


def self_test() -> dict[str, Any]:
    result = _BASE_SELF_TEST()
    assert freezer.R6_ROOT == R8_ROOT
    assert freezer.COMPLETION.name == "recovery0008_controller_reload_completion.json"
    assert freezer.CONTROLLER_NAME == "resume_m05_campaign_batch0006_recovery0008_disk_admission.py"
    return {
        **result,
        "status": "PASS__RECOVERY0008_SAME_NAMESPACE_RELOAD_HELPER_SELF_TEST",
        "tests": int(result["tests"]) + 3,
        "same_namespace": True,
        "final_published": False,
        "receipt_modified": False,
        "hashes_computed": False,
        "gzip_reopened": False,
    }


freezer.authority_declarations = authority_declarations
freezer.self_test = self_test


if __name__ == "__main__":
    raise SystemExit(freezer.main())
