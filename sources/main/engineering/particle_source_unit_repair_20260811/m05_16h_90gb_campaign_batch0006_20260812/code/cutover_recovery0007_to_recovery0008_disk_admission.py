#!/usr/bin/env python3
"""Scheduling-only r7 -> r8 cutover using the proven coordinator freezer."""

from __future__ import annotations

import json
from pathlib import Path

import cutover_recovery0006_to_recovery0007_scheduler as cutover


ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
R7_ROOT = RUN_ROOT / "recovery0007_efficiency_scheduler"

cutover.R6_ROOT = R7_ROOT
cutover.R6_AUTHORITY = R7_ROOT / "authority.json"
cutover.R6_SEED_REGISTRY = R7_ROOT / "seed_registry.json"
cutover.R6_FINAL = R7_ROOT / "final_umbrella.json"
cutover.CONTROLLER_NAME = "resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler.py"
cutover.INTENT = RUN_ROOT / "recovery0008_disk_admission_cutover_intent.json"
cutover.COMPLETION = RUN_ROOT / "recovery0008_disk_admission_cutover_completion.json"


def authority_declarations() -> dict[str, object]:
    authority = cutover.load_json(cutover.R6_AUTHORITY)
    controller = authority.get("controller") if isinstance(authority.get("controller"), dict) else {}
    return {
        "authority_path": cutover.relative(cutover.R6_AUTHORITY),
        "authority_status": authority.get("status"),
        "recovery_id": authority.get("recovery_id"),
        "controller_path": controller.get("path"),
        "controller_hash_computed_or_required": controller.get("hash_computed_or_required"),
        "effective_pending_plan_declared_sha256": authority.get("effective_pending_plan_sha256"),
        "seed_registry_path": cutover.relative(cutover.R6_SEED_REGISTRY),
        "note": "declarations copied without computing hashes or reopening gzip artifacts",
    }


cutover.authority_declarations = authority_declarations


if __name__ == "__main__":
    raise SystemExit(cutover.main())
