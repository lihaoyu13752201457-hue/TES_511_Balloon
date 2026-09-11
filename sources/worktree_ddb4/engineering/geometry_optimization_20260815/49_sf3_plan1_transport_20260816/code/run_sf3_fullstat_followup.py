#!/usr/bin/env python3
"""Crash-safe conditional SF3 full-stat sequencer.

The only entry authority is the write-once Plan-1 stage-07 audit.  A central
F3 ratio above 0.75 publishes one compact terminal STOP authority and exits
successfully.  A ratio at or below 0.75 permits exactly one ordered full-stat
chain.  Status/self-test paths read named compact CSV/JSON authorities only;
they never inspect a SIM payload or call systemd.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from sf3_plan1_common import FAMILIES


HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parent.parent
CODE_ROOT = PACKAGE_ROOT / "code"
MANIFEST_PATH = PACKAGE_ROOT / "data/sf3_fullstat_followup_execution_manifest.json"
AUDIT_ROOT = PACKAGE_ROOT / "audit"
STOP_AUTHORITY = AUDIT_ROOT / "sf3_fullstat_followup_terminal_stop.json"
JOURNAL_PATH = AUDIT_ROOT / "sf3_fullstat_followup_execution_journal.jsonl"
STATE_PATH = AUDIT_ROOT / "sf3_fullstat_followup_state.json"
LOCK_PATH = AUDIT_ROOT / "sf3_fullstat_followup_controller.lock"
GUARD_EVENT_LOG = AUDIT_ROOT / "sf3_fullstat_followup_pressure_guard.jsonl"
RESOURCE_EVENT_LOG = AUDIT_ROOT / "sf3_fullstat_followup_resource_events.jsonl"
GUARD_SESSION_WAL = AUDIT_ROOT / "sf3_fullstat_followup_guard_session_wal.jsonl"

PROFILE_ID = "SF3_FULLSTAT_CONDITIONAL_FOLLOWUP_V1"
MANIFEST_STATUS = "PASS__SF3_FULLSTAT_CRASH_SAFE_FOLLOWUP_EXECUTION_MANIFEST_PREPARED"
COMPLETE_STATUS = "PASS__SF3_FULLSTAT_CRASH_SAFE_FOLLOWUP_COMPLETE"
STOP_STATUS = "PASS__SF3_FULLSTAT_FOLLOWUP_STOPPED_BY_PLAN1_CENTRAL_GATE"
PLAN1_STATUS = "PASS__SF3_PLAN1_CHAIN_COMPLETE__CENTRAL_FULLSTAT_GATE_RECORDED"
PLAN1_MISSION_STATUS = "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE"
DEFAULT_SERVICE_UNIT = "sf3-fullstat-followup.service"
DEFAULT_WAIT_POLL_SECONDS = 45.0
CENTRAL_GATE = 0.75
WORKERS = 4
MAX_CPU_BUDGET = 6
MEM_FLOOR = 1_610_612_736
SWAP_FLOOR = 8 * 1024**3
DISK_RESERVE = 8 * 1024**3
MAX_SMALL_BYTES = 64 * 1024**2
MAX_GUARD_DELTA_BYTES = 4 * 1024**2
ZERO_REASON = "FULL_INVENTORY_EXACT_ZERO_A15__NO_TRANSPORT"

PLAN1_FINAL = "outputs/07_final_audit/final_audit.json"
PLAN1_MISSION = "outputs/06_mission/summary.json"
TOPUP_STATIC = "audit/sf3_fullstat_topup_static_audit.json"
TOPUP_PLAN = "data/sf3_fullstat_topup_job_plan.csv"
TOPUP_SEEDS = "data/sf3_fullstat_topup_seed_registry.csv"
PLAN1_SEEDS = "data/sf3_plan1_seed_registry.csv"
TOPUP_AGGREGATE = "audit/sf3_fullstat_topup_transport_receipts.json"
TOPUP_RECEIPT_ROOT = "audit/fullstat_topup_receipts"
FULLSTAT_ACTIVATION_VALIDATION = "audit/sf3_fullstat_activation_validation.json"
FULLSTAT_DELAYED_PLAN = "data/sf3_fullstat_delayed_job_plan.csv"
FULLSTAT_DELAYED_SEEDS = "data/sf3_fullstat_delayed_seed_registry.csv"
FULLSTAT_DELAYED_AGGREGATE = "audit/sf3_fullstat_delayed_transport_receipts.json"
FULLSTAT_DELAYED_RECEIPT_ROOT = "audit/fullstat_delayed_receipts"
FULLSTAT_RESOURCE = "audit/sf3_fullstat_resource_timeline.json"
FULLSTAT_FINAL = "outputs/fullstat/07_final_audit/final_audit.json"
FULLSTAT_DELAYED_NAMESPACE = "SF3_FULLSTAT_DELAYED_V1"
FULLSTAT_RESOURCE_STATUS = "PASS__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_COMPLETE"
FULLSTAT_RESOURCE_PROFILE = "SF3_FULLSTAT_RESOURCE_TIMELINE_V1"
FULLSTAT_RESOURCE_SCOPE = (
    "SF3_FULLSTAT_49_BACKGROUND_FRESH250K_DELAYED_AND_FIVE_GUARDED_HEAVY_STEPS"
)
FULLSTAT_RESOURCE_WRITE_CONTRACT = "ATOMIC_HARDLINK_PUBLICATION__WRITE_ONCE"

STEP_IDS = (
    "await_plan1_stage07",
    "prepare_topup",
    "transport_topup",
    "validate_topup_receipts",
    "build_fullstat_prompt",
    "build_fullstat_activation",
    "transport_fullstat_delayed",
    "validate_fullstat_delayed_receipts",
    "analyze_fullstat_delayed",
    "build_fullstat_common_response",
    "build_fullstat_mission",
    "build_fullstat_resource_timeline",
    "finalize_fullstat",
)
GUARDED_STEPS = (
    "transport_topup",
    "build_fullstat_prompt",
    "transport_fullstat_delayed",
    "analyze_fullstat_delayed",
    "build_fullstat_common_response",
)
TRANSPORT_STEPS = {"transport_topup", "transport_fullstat_delayed"}
VIRTUAL_STEPS = {"validate_topup_receipts", "validate_fullstat_delayed_receipts"}
PHASE_BY_GUARDED_STEP = {
    "transport_topup": "FULLSTAT_TOPUP_TRANSPORT",
    "build_fullstat_prompt": "FULLSTAT_PROMPT_ANALYSIS",
    "transport_fullstat_delayed": "FULLSTAT_DELAYED_TRANSPORT",
    "analyze_fullstat_delayed": "FULLSTAT_DELAYED_ANALYSIS",
    "build_fullstat_common_response": "FULLSTAT_COMMON_RESPONSE",
}

OUTPUT_PAIRS = {
    "build_fullstat_prompt": (
        "outputs/fullstat/01_prompt", "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
        "summary.json", "manifest.json",
    ),
    "analyze_fullstat_delayed": (
        "outputs/fullstat/03_delayed",
        "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "summary.json", "manifest.json",
    ),
    "build_fullstat_common_response": (
        "outputs/fullstat/04_common_response",
        "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
        "summary.json", "manifest.json",
    ),
    "build_fullstat_mission": (
        "outputs/fullstat/06_mission",
        "PASS__SF3_FULLSTAT_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_FINAL_F3",
        "summary.json", "manifest.json",
    ),
}

EXPECTED_COMMANDS = {
    "await_plan1_stage07": [],
    "prepare_topup": ["{python}", "{code}/build_sf3_fullstat_topup.py", "--prepare"],
    "transport_topup": ["{python}", "{code}/run_sf3_fullstat_topup.py", "--phase", "background", "--cpu-budget", "4"],
    "validate_topup_receipts": [],
    "build_fullstat_prompt": ["{python}", "{code}/run_sf3_fullstat_prompt_analysis.py", "--build", "--workers", "4"],
    "build_fullstat_activation": ["{python}", "{code}/build_sf3_fullstat_activation.py", "--prepare"],
    "transport_fullstat_delayed": ["{python}", "{code}/run_sf3_fullstat_delayed.py", "--phase", "delayed", "--cpu-budget", "4"],
    "validate_fullstat_delayed_receipts": [],
    "analyze_fullstat_delayed": ["{python}", "{code}/analyze_sf3_fullstat_delayed.py", "--workers", "4"],
    "build_fullstat_common_response": ["{python}", "{code}/build_sf3_fullstat_common_response.py", "--workers", "4"],
    "build_fullstat_mission": ["{python}", "{code}/build_sf3_fullstat_mission.py", "--build"],
    "build_fullstat_resource_timeline": ["{python}", "{code}/build_sf3_fullstat_resource_timeline.py", "--build"],
    "finalize_fullstat": ["{python}", "{code}/finalize_sf3_fullstat.py", "--build"],
}
EXPECTED_PREFLIGHTS = {
    "await_plan1_stage07": [],
    "prepare_topup": [],
    "transport_topup": ["{python}", "{code}/run_sf3_fullstat_topup.py", "--check-prerequisites", "--cpu-budget", "4"],
    "validate_topup_receipts": [],
    "build_fullstat_prompt": ["{python}", "{code}/run_sf3_fullstat_prompt_analysis.py", "--check-prerequisites", "--workers", "4"],
    "build_fullstat_activation": ["{python}", "{code}/build_sf3_fullstat_activation.py", "--check-prerequisites"],
    "transport_fullstat_delayed": ["{python}", "{code}/run_sf3_fullstat_delayed.py", "--check-prerequisites", "--cpu-budget", "4"],
    "validate_fullstat_delayed_receipts": [],
    "analyze_fullstat_delayed": ["{python}", "{code}/analyze_sf3_fullstat_delayed.py", "--check-prerequisites", "--workers", "4"],
    "build_fullstat_common_response": ["{python}", "{code}/build_sf3_fullstat_common_response.py", "--check-prerequisites", "--workers", "4"],
    "build_fullstat_mission": ["{python}", "{code}/build_sf3_fullstat_mission.py", "--check-prerequisites"],
    "build_fullstat_resource_timeline": ["{python}", "{code}/build_sf3_fullstat_resource_timeline.py", "--check-prerequisites"],
    "finalize_fullstat": ["{python}", "{code}/finalize_sf3_fullstat.py", "--check-prerequisites"],
}
EXPECTED_STEP_METADATA = {
    "await_plan1_stage07": (0, "wait", PLAN1_FINAL, None, None, None),
    "prepare_topup": (10, "static_prepare", TOPUP_STATIC, None, None, None),
    "transport_topup": (20, "transport_with_pressure_guard", TOPUP_AGGREGATE, None, None, True),
    "validate_topup_receipts": (30, "virtual_metadata_validation", TOPUP_AGGREGATE, None, None, None),
    "build_fullstat_prompt": (40, "analysis_with_pressure_guard", "outputs/fullstat/01_prompt/summary.json", "outputs/fullstat/01_prompt", None, True),
    "build_fullstat_activation": (50, "analysis", FULLSTAT_ACTIVATION_VALIDATION, "outputs/fullstat/02_activation", "IDEMPOTENT_PREPARE_MAY_REPUBLISH_MISSING_SMALL_VALIDATION", None),
    "transport_fullstat_delayed": (60, "transport_with_pressure_guard", FULLSTAT_DELAYED_AGGREGATE, None, None, True),
    "validate_fullstat_delayed_receipts": (70, "virtual_metadata_validation", FULLSTAT_DELAYED_AGGREGATE, None, None, None),
    "analyze_fullstat_delayed": (80, "analysis_with_pressure_guard", "outputs/fullstat/03_delayed/summary.json", "outputs/fullstat/03_delayed", None, True),
    "build_fullstat_common_response": (90, "analysis_with_pressure_guard", "outputs/fullstat/04_common_response/summary.json", "outputs/fullstat/04_common_response", None, True),
    "build_fullstat_mission": (100, "small_table_analysis", "outputs/fullstat/06_mission/summary.json", "outputs/fullstat/06_mission", None, None),
    "build_fullstat_resource_timeline": (110, "metadata_audit", FULLSTAT_RESOURCE, FULLSTAT_RESOURCE, None, None),
    "finalize_fullstat": (120, "small_table_finalizer", FULLSTAT_FINAL, "outputs/fullstat/07_final_audit", None, None),
}


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def sha256_small(path: Path) -> str:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"compact authority empty/oversized: {path} ({size})")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    sha256_small(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def optional_json(path: Path) -> dict[str, Any] | None:
    return load_json(path) if path.is_file() else None


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > MAX_SMALL_BYTES:
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV header missing: {path}")
        return list(reader)


def atomic_replace_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temp.open("x", encoding="utf-8") as handle:
        handle.write(json_text(payload))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def write_once_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.tmp-", delete=False,
        ) as handle:
            handle.write(json_text(payload))
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.link(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def state_result(complete: bool, details: dict[str, Any] | None = None, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {"complete": complete, "details": details or {}, "errors": list(errors)}


def finite_float(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"{label} is non-finite")
    return result


def validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if (
        payload.get("schema_version") != 1
        or payload.get("profile_id") != PROFILE_ID
        or payload.get("status") != MANIFEST_STATUS
        or payload.get("scope") != "CONDITIONAL_POST_PLAN1_STAGE07_FULLSTAT_ONLY"
        or payload.get("required_service_unit") != DEFAULT_SERVICE_UNIT
        or payload.get("terminal_stop_authority") != str(STOP_AUTHORITY.relative_to(PACKAGE_ROOT))
    ):
        raise RuntimeError("full-stat followup manifest identity differs")
    gate = payload.get("entry_gate") or {}
    if (
        gate.get("authority") != PLAN1_FINAL
        or gate.get("mission_authority") != PLAN1_MISSION
        or gate.get("metric") != "fullstat_gate.observed_central_ratio"
        or gate.get("closure_copy") != "mission_results.central_F3_ratio"
        or gate.get("operator") != "<="
        or gate.get("threshold") != CENTRAL_GATE
        or gate.get("proxy_controls_gate") is not False
    ):
        raise RuntimeError("manifest central-only entry gate differs")
    steps = payload.get("steps")
    if not isinstance(steps, list) or tuple(row.get("id") for row in steps) != STEP_IDS:
        raise RuntimeError("manifest step order differs")
    by_id = {str(row["id"]): row for row in steps}
    for step_id, command in EXPECTED_COMMANDS.items():
        row = by_id[step_id]
        if row.get("command") != command:
            raise RuntimeError(f"manifest command differs: {step_id}")
        if row.get("preflight", []) != EXPECTED_PREFLIGHTS[step_id]:
            raise RuntimeError(f"manifest preflight differs: {step_id}")
        ordinal, kind, authority, target, target_policy, guarded = EXPECTED_STEP_METADATA[step_id]
        if (
            row.get("ordinal") != ordinal
            or row.get("kind") != kind
            or row.get("completion_authority") != authority
            or row.get("write_once_target") != target
            or row.get("existing_target_policy") != target_policy
            or row.get("guard") is not guarded
        ):
            raise RuntimeError(f"manifest step descriptor differs: {step_id}")
    policies = payload.get("policies") or {}
    guard = policies.get("pressure_guard") or {}
    handoff = policies.get("continuous_handoff") or {}
    crash_recovery = policies.get("post_authority_resource_event_crash_recovery") or {}
    if (
        policies.get("workers") != WORKERS
        or policies.get("configured_cpu_budget_max") != MAX_CPU_BUDGET
        or policies.get("dynamic_disk_reserve_bytes") != DISK_RESERVE
        or guard.get("guarded_steps") != list(GUARDED_STEPS)
        or guard.get("normal_quota_percent") != 400
        or guard.get("throttle_quota_percent") != 300
        or guard.get("mem_available_floor_bytes") != MEM_FLOOR
        or guard.get("swap_free_floor_bytes") != SWAP_FLOOR
        or guard.get("disk_free_floor_bytes") != DISK_RESERVE
        or guard.get("disk_sampled_in_every_guard_event_and_closure") is not True
    ):
        raise RuntimeError("manifest worker/resource guard contract differs")
    if crash_recovery != {
        "write_ahead_log": str(GUARD_SESSION_WAL.relative_to(PACKAGE_ROOT)),
        "write_ahead_timing": "FSYNC_BEFORE_GUARD_OR_STAGE_LAUNCH",
        "normal_completion": "STAGE_RETURNCODE_0_AND_ORIGINAL_GUARD_CLOSURE_RESOURCES",
        "recovery_hard_gate": "CANONICAL_STEP_AUTHORITY_PLUS_SAME_MANIFEST_WAL_PLUS_EXACT_CLEAN_GUARD_BYTE_SEGMENT",
        "recovery_stage_returncode": None,
        "live_resource_inference_on_recovery": False,
        "rerun_canonical_stage_for_missing_resource_row": False,
    }:
        raise RuntimeError("manifest post-authority resource-event crash recovery contract differs")
    if (
        handoff.get("entrypoint") != "--wait-and-run-to-completion"
        or handoff.get("default_heartbeat_seconds") != 45
        or handoff.get("allowed_heartbeat_seconds") != [30, 60]
    ):
        raise RuntimeError("manifest continuous handoff differs")
    for step_id in GUARDED_STEPS:
        row = by_id[step_id]
        if row.get("guard") is not True or not str(row.get("kind", "")).endswith("_with_pressure_guard"):
            raise RuntimeError(f"heavy step is not guarded: {step_id}")
    for step_id, row in by_id.items():
        tokens = [*(row.get("command") or []), *(row.get("preflight") or [])]
        if any("83334" in str(token) for token in tokens):
            raise RuntimeError(f"manifest attempts to consume Plan-1 delayed 83334: {step_id}")
        if step_id in TRANSPORT_STEPS and (row.get("command") or [])[-2:] != ["--cpu-budget", "4"]:
            raise RuntimeError(f"transport step is not fixed to cpu4: {step_id}")
    return payload


def load_manifest() -> dict[str, Any]:
    return validate_manifest(load_json(MANIFEST_PATH))


def plan1_gate(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    final_path = root / PLAN1_FINAL
    mission_path = root / PLAN1_MISSION
    if not final_path.is_file():
        return None, []
    errors: list[str] = []
    try:
        final = load_json(final_path)
        mission = load_json(mission_path)
        if (
            final.get("status") != PLAN1_STATUS
            or final.get("ready") is not True
            or final.get("errors") != []
            or final.get("missing") != []
        ):
            errors.append("Plan-1 stage07 closure identity/readiness differs")
        gate = mission.get("fullstat_gate") or {}
        disposition = final.get("fullstat_disposition") or {}
        mission_results = final.get("mission_results") or {}
        ratio = finite_float(gate.get("observed_central_ratio"), "Plan-1 central ratio")
        threshold = finite_float(gate.get("threshold"), "Plan-1 central threshold")
        expected = ratio <= CENTRAL_GATE
        decision = "TOPUP_TO_S3D_FULL_STAT_REQUIRED" if expected else "STOP__NO_FULLSTAT_TOPUP"
        if (
            mission.get("status") != PLAN1_MISSION_STATUS
            or ratio < 0.0
            or gate.get("metric") != "F3_SF3_over_SE3_full_envelope"
            or gate.get("operator") != "<="
            or threshold != CENTRAL_GATE
            or gate.get("topup_required") is not expected
            or gate.get("decision") != decision
            or gate.get("proxy_controls_gate") is not False
        ):
            errors.append("Plan-1 mission central-only full-stat gate differs")
        if (
            disposition.get("topup_required") is not expected
            or disposition.get("threshold") != CENTRAL_GATE
            or disposition.get("mission_decision") != decision
            or disposition.get("proxy_controls_gate") is not False
            or not math.isclose(finite_float(disposition.get("observed_central_ratio"), "stage07 central ratio"), ratio, rel_tol=0.0, abs_tol=1e-15)
            or mission_results.get("topup_required") is not expected
            or not math.isclose(finite_float(mission_results.get("central_F3_ratio"), "stage07 mission central ratio"), ratio, rel_tol=0.0, abs_tol=1e-15)
        ):
            errors.append("Plan-1 stage07 gate copy differs from mission authority")
        return {
            "topup_required": expected,
            "central_ratio": ratio,
            "threshold": CENTRAL_GATE,
            "decision": decision,
            "proxy_controls_gate": False,
            "plan1_final_path": str(final_path.resolve()),
            "plan1_final_sha256": sha256_small(final_path),
            "plan1_mission_path": str(mission_path.resolve()),
            "plan1_mission_sha256": sha256_small(mission_path),
        }, errors
    except Exception as exc:
        errors.append(f"Plan-1 central gate inspection failed: {exc}")
        return None, errors


def fullstat_branch_artifacts(root: Path) -> list[str]:
    relatives = (
        TOPUP_STATIC, TOPUP_PLAN, TOPUP_SEEDS, TOPUP_AGGREGATE,
        "outputs/fullstat", FULLSTAT_ACTIVATION_VALIDATION,
        FULLSTAT_DELAYED_PLAN, FULLSTAT_DELAYED_AGGREGATE, FULLSTAT_RESOURCE,
        str(GUARD_EVENT_LOG.relative_to(PACKAGE_ROOT)),
        str(RESOURCE_EVENT_LOG.relative_to(PACKAGE_ROOT)),
        str(GUARD_SESSION_WAL.relative_to(PACKAGE_ROOT)),
    )
    return [str(root / relative) for relative in relatives if (root / relative).exists()]


def stop_state(root: Path, gate: dict[str, Any]) -> dict[str, Any]:
    path = root / str(STOP_AUTHORITY.relative_to(PACKAGE_ROOT))
    payload = optional_json(path)
    artifacts = fullstat_branch_artifacts(root)
    if payload is None:
        return state_result(False, errors=(
            [f"full-stat artifacts exist on a false central gate: {artifacts}"] if artifacts else []
        ))
    errors: list[str] = (
        [f"full-stat artifacts exist after terminal false-gate STOP: {artifacts}"]
        if artifacts else []
    )
    expected = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": STOP_STATUS,
        "topup_required": False,
        "central_F3_SF3_over_F3_SE3": gate["central_ratio"],
        "threshold": CENTRAL_GATE,
        "proxy_controls_gate": False,
        "plan1_final_sha256": gate["plan1_final_sha256"],
        "plan1_mission_sha256": gate["plan1_mission_sha256"],
        "terminal": True,
        "transport_or_analysis_launched": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"terminal STOP authority field differs: {key}")
    return state_result(not errors, {"status": payload.get("status")}, errors)


def publish_stop(root: Path, gate: dict[str, Any]) -> dict[str, Any]:
    existing = stop_state(root, gate)
    if existing["complete"]:
        return load_json(root / str(STOP_AUTHORITY.relative_to(PACKAGE_ROOT)))
    if existing["errors"]:
        raise RuntimeError(json.dumps(existing, sort_keys=True))
    payload = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": STOP_STATUS,
        "published_at": utc_now(),
        "topup_required": False,
        "central_F3_SF3_over_F3_SE3": gate["central_ratio"],
        "threshold": CENTRAL_GATE,
        "operator": "<=",
        "decision": "STOP__NO_FULLSTAT_TOPUP",
        "proxy_controls_gate": False,
        "plan1_final_path": gate["plan1_final_path"],
        "plan1_final_sha256": gate["plan1_final_sha256"],
        "plan1_mission_path": gate["plan1_mission_path"],
        "plan1_mission_sha256": gate["plan1_mission_sha256"],
        "terminal": True,
        "fullstat_artifacts_created": [],
        "transport_or_analysis_launched": False,
        "second_gate_authorized": False,
        "SIM_opened_statted_discovered_or_hashed": False,
    }
    write_once_json(root / str(STOP_AUTHORITY.relative_to(PACKAGE_ROOT)), payload)
    return payload


def output_pair_state(root: Path, step_id: str) -> dict[str, Any]:
    relative, expected, summary_name, manifest_name = OUTPUT_PAIRS[step_id]
    output = root / relative
    summary_path, manifest_path = output / summary_name, output / manifest_name
    if not summary_path.is_file() and not manifest_path.is_file():
        return state_result(False)
    try:
        summary, manifest = load_json(summary_path), load_json(manifest_path)
    except Exception as exc:
        return state_result(False, errors=[str(exc)])
    errors = []
    if summary.get("status") != expected:
        errors.append(f"{step_id} summary status differs")
    if manifest.get("status") != expected:
        errors.append(f"{step_id} manifest status differs")
    return state_result(not errors, {"status": expected}, errors)


def activation_validation_republishable(root: Path) -> bool:
    """Allow only the builder's documented post-rename validation recovery."""
    if (root / FULLSTAT_ACTIVATION_VALIDATION).exists():
        return False
    expected = "PASS__SF3_FULLSTAT_ACTIVATION_AND_FRESH_DELAYED_SOURCES_READY"
    try:
        summary = load_json(root / "outputs/fullstat/02_activation/day15_summary.json")
        manifest = load_json(root / "outputs/fullstat/02_activation/manifest.json")
        plan = load_csv(root / FULLSTAT_DELAYED_PLAN)
        seeds = load_csv(root / FULLSTAT_DELAYED_SEEDS)
    except Exception:
        return False
    plan_by_family = {row.get("family"): row for row in plan}
    seed_by_family = {row.get("family"): row for row in seeds}
    return bool(
        summary.get("status") == expected
        and manifest.get("status") == expected
        and summary.get("selected_buildup_jobs") == 23
        and summary.get("selected_plan1_buildup_jobs") == 10
        and summary.get("selected_topup_buildup_jobs") == 13
        and summary.get("selected_buildup_histories") == 3_046_468
        and summary.get("registered_delayed_source_cells") == 8
        and summary.get("registered_delayed_triggers_per_family") == 250_000
        and summary.get("plan1_83334_consumed_or_merged") is False
        and summary.get("incremental_166666_merge_allowed") is False
        and (manifest.get("hard_gates") or {}) == {
            "central_mission_topup_required_true": True,
            "all_28_topup_background_canonical_PASS": True,
        }
        and len(plan) == 8
        and set(plan_by_family) == set(FAMILIES)
        and len(seeds) == 8
        and set(seed_by_family) == set(FAMILIES)
        and (manifest.get("fresh_delayed_seeds") or {})
        == {family: int(plan_by_family[family]["seed"]) for family in FAMILIES}
        and all(
            seed_by_family[family].get("job_id") == plan_by_family[family].get("job_id")
            and int(seed_by_family[family].get("seed", "0")) == int(plan_by_family[family].get("seed", "-1"))
            and seed_by_family[family].get("namespace") == FULLSTAT_DELAYED_NAMESPACE
            and str(seed_by_family[family].get("collision_with_prior_plan1_or_topup", "")).lower() == "false"
            for family in FAMILIES
        )
    )


def topup_plan(root: Path) -> list[dict[str, str]]:
    rows = load_csv(root / TOPUP_PLAN)
    if len(rows) != 28 or len({row.get("job_id") for row in rows}) != 28:
        raise RuntimeError("full-stat top-up plan is not 28 unique jobs")
    if sum(row.get("mode") == "instant" for row in rows) != 15 or sum(row.get("mode") == "buildup" for row in rows) != 13:
        raise RuntimeError("full-stat top-up plan is not 15 instant + 13 buildup jobs")
    if any(row.get("stage") != "fullstat_topup_background" or row.get("geometry") != "SF3" for row in rows):
        raise RuntimeError("full-stat top-up plan stage/geometry differs")
    if any(int(row.get("events", "0")) <= 0 or int(row.get("seed", "0")) <= 0 for row in rows):
        raise RuntimeError("full-stat top-up plan events/seeds are invalid")
    return rows


def prepare_topup_state(root: Path) -> dict[str, Any]:
    audit = optional_json(root / TOPUP_STATIC)
    if audit is None:
        partial = [relative for relative in (TOPUP_PLAN, TOPUP_SEEDS) if (root / relative).exists()]
        errors: list[str] = []
        if partial:
            try:
                if not (root / TOPUP_PLAN).is_file():
                    raise RuntimeError("top-up seed registry exists without its preceding plan")
                plan = topup_plan(root)
                if (root / TOPUP_SEEDS).is_file():
                    seeds = load_csv(root / TOPUP_SEEDS)
                    if (
                        len(seeds) != 28
                        or {row.get("job_id"): int(row.get("seed", "0")) for row in seeds}
                        != {row["job_id"]: int(row["seed"]) for row in plan}
                    ):
                        raise RuntimeError("partial top-up seed registry differs from plan")
            except Exception as exc:
                errors.append(f"noncanonical partial static top-up package: {exc}")
        return state_result(False, {"idempotent_partial_outputs": partial}, errors)
    errors: list[str] = []
    try:
        plan = topup_plan(root)
        seeds = load_csv(root / TOPUP_SEEDS)
        plan_seed = {row["job_id"]: int(row["seed"]) for row in plan}
        seed_map = {row.get("job_id", ""): int(row.get("seed", "0")) for row in seeds}
        if len(seeds) != 28 or seed_map != plan_seed:
            errors.append("full-stat top-up seed registry differs from plan")
        if audit.get("status") != "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED":
            errors.append("full-stat top-up static audit status differs")
        if (audit.get("plan") or {}).get("jobs") != 28:
            errors.append("full-stat top-up static plan count differs")
        transport = audit.get("transport") or {}
        if transport.get("launched") is not False or transport.get("runner_status") != "PRESENT__STATIC_SELF_TEST_PASS__EXPLICIT_PHASE_REQUIRED_FOR_LAUNCH":
            errors.append("full-stat static runner binding differs")
        if audit.get("plan1_mutation") is not False:
            errors.append("full-stat top-up static audit mutates Plan-1")
    except Exception as exc:
        errors.append(str(exc))
    return state_result(not errors, {"jobs": 28}, errors)


def canonical_attempt_errors(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    try:
        attempt = int(payload.get("attempt", 0))
    except (TypeError, ValueError):
        attempt = 0
    attempt_dir = Path(str(payload.get("attempt_dir", "")))
    if (
        payload.get("status") != "PASS"
        or payload.get("errors") != []
        or attempt <= 0
        or attempt_dir.name != f"attempt{attempt:02d}"
        or attempt_dir.parent.name != "attempts"
        or any(part in {"active", "interrupted", "failed"} for part in attempt_dir.parts)
    ):
        errors.append(f"{label} is not one canonical PASS attempts/attemptNN receipt")
    return errors


def load_bound_receipt(
    root: Path, relative_root: str, job_id: str, selected: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    expected_path = (root / relative_root / f"{job_id}.json").resolve()
    observed_path = Path(str(selected.get("receipt_path", ""))).resolve()
    if observed_path != expected_path:
        errors.append(f"canonical receipt path differs: {job_id}")
    try:
        payload = load_json(expected_path)
        digest = sha256_small(expected_path)
        if selected.get("receipt_sha256") != digest:
            errors.append(f"canonical receipt digest differs: {job_id}")
    except Exception as exc:
        return {}, [*errors, f"canonical receipt unreadable: {job_id}: {exc}"]
    errors.extend(canonical_attempt_errors(payload, job_id))
    return payload, errors


def topup_receipt_state(root: Path) -> dict[str, Any]:
    payload = optional_json(root / TOPUP_AGGREGATE)
    if payload is None:
        return state_result(False)
    errors: list[str] = []
    try:
        plan = topup_plan(root)
        by_id = {row["job_id"]: row for row in plan}
        selected = payload.get("selected_receipts")
        if not isinstance(selected, list):
            raise RuntimeError("top-up aggregate selected_receipts is not an array")
        observed: set[str] = set()
        for row in selected:
            job_id = str(row.get("job_id", ""))
            expected = by_id.get(job_id)
            if expected is None or job_id in observed:
                errors.append(f"top-up aggregate unknown/duplicate job: {job_id!r}")
                continue
            observed.add(job_id)
            receipt, receipt_errors = load_bound_receipt(
                root, TOPUP_RECEIPT_ROOT, job_id, row,
            )
            errors.extend(receipt_errors)
            if (
                row.get("registered_stage") != "fullstat_topup_background"
                or row.get("receipt_stage") != "background"
                or row.get("geometry") != "SF3"
                or row.get("mode") != expected["mode"]
                or row.get("family") != expected["family"]
                or int(row.get("events", -1)) != int(expected["events"])
                or int(row.get("seed", -1)) != int(expected["seed"])
            ):
                errors.append(f"top-up aggregate receipt binding differs: {job_id}")
            setup = str(expected.get("setup_path", ""))
            header = receipt.get("sim_header") or {}
            dat = receipt.get("isotope_dat") or {}
            if (
                receipt.get("profile_id") != "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1"
                or receipt.get("job_id") != job_id
                or receipt.get("stage") != "background"
                or receipt.get("geometry") != "SF3"
                or receipt.get("mode") != expected["mode"]
                or receipt.get("family") != expected["family"]
                or int(receipt.get("events", -1)) != int(expected["events"])
                or int(receipt.get("seed", -1)) != int(expected["seed"])
                or Path(str(receipt.get("setup_path", ""))).resolve() != Path(setup).resolve()
                or Path(str(header.get("geometry", ""))).resolve() != Path(setup).resolve()
                or int(header.get("seed", -1)) != int(expected["seed"])
                or header.get("policy") != "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"
                or not isinstance(dat.get("TT_s"), (int, float))
                or float(dat.get("TT_s", 0.0)) <= 0.0
                or not isinstance(dat.get("RP_record_count"), int)
                or int(dat.get("RP_record_count", -1)) < 0
                or dat.get("terminal_EN") is not True
                or dat.get("errors") not in ([], None)
                or receipt.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY"
            ):
                errors.append(f"top-up canonical receipt payload differs: {job_id}")
        if (
            payload.get("profile_id") != "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1"
            or payload.get("status") != "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS"
            or int(payload.get("planned_jobs", -1)) != 28
            or int(payload.get("validated_jobs", -1)) != 28
            or int(payload.get("instant_validated_events", -1)) != 2_561_382
            or int(payload.get("buildup_validated_events", -1)) != 2_030_976
            or observed != set(by_id)
            or payload.get("plan1_mutation") is not False
        ):
            errors.append("top-up aggregate 28-job closure differs")
    except Exception as exc:
        errors.append(str(exc))
    return state_result(not errors, {"validated_jobs": len(payload.get("selected_receipts") or [])}, errors)


def activation_state(root: Path) -> tuple[dict[str, Any] | None, list[str], list[str], list[str]]:
    validation = optional_json(root / FULLSTAT_ACTIVATION_VALIDATION)
    if validation is None:
        return None, [], [], []
    errors: list[str] = []
    try:
        summary = load_json(root / "outputs/fullstat/02_activation/day15_summary.json")
        manifest = load_json(root / "outputs/fullstat/02_activation/manifest.json")
        plan = load_csv(root / FULLSTAT_DELAYED_PLAN)
        seed_registry = load_csv(root / FULLSTAT_DELAYED_SEEDS)
        if len(plan) != 8 or {row.get("family") for row in plan} != set(FAMILIES):
            errors.append("full-stat delayed plan is not eight unique families")
        plan_seeds = {int(row.get("seed", "0")) for row in plan}
        if len(plan_seeds) != 8:
            errors.append("full-stat delayed plan seeds are not eight unique values")
        if any(
            row.get("stage") != "fullstat_delayed"
            or row.get("geometry") != "SF3"
            or row.get("mode") != "delayed"
            or row.get("job_id") != f"sf3_fullstat_delayed_{row.get('family')}"
            or row.get("seed_namespace") != FULLSTAT_DELAYED_NAMESPACE
            or int(row.get("sampling_seed", "0")) != int(row.get("seed", "-1"))
            or row.get("seed_identity") != row.get("job_id")
            or row.get("source_support") != "REBUILT_FULLSTAT_23_BUILDUP_RECEIPTS_ACTUAL_RPIP_POSITIONS"
            or row.get("plan1_83334_role") != "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE"
            or str(row.get("incremental_merge_allowed", "")).lower() != "false"
            for row in plan
        ):
            errors.append("full-stat delayed plan stage/geometry/Plan1 exclusion differs")
        seeds_by_family = {row.get("family"): row for row in seed_registry}
        if len(seed_registry) != 8 or set(seeds_by_family) != set(FAMILIES):
            errors.append("full-stat delayed seed registry family closure differs")
        else:
            for row in plan:
                seed_row = seeds_by_family[row["family"]]
                if (
                    seed_row.get("job_id") != row.get("job_id")
                    or int(seed_row.get("seed", "0")) != int(row.get("seed", "-1"))
                    or seed_row.get("namespace") != FULLSTAT_DELAYED_NAMESPACE
                    or str(seed_row.get("collision_with_prior_plan1_or_topup", "")).lower() != "false"
                    or str(seed_row.get("sampling_and_transport_seed_shared_within_job", "")).lower() != "true"
                ):
                    errors.append(f"full-stat delayed seed registry binding differs: {row['family']}")
        prior_seed_rows = load_csv(root / PLAN1_SEEDS) + load_csv(root / TOPUP_SEEDS)
        prior_seeds = {int(row.get("seed", "0")) for row in prior_seed_rows}
        if len(prior_seed_rows) != 58 or len(prior_seeds) != 58 or plan_seeds & prior_seeds:
            errors.append("full-stat delayed seeds are not disjoint from 30 Plan-1 + 28 top-up seeds")
        if validation.get("status") != "PASS__SF3_FULLSTAT_ACTIVATION_VALIDATION":
            errors.append("full-stat activation validation status differs")
        if (
            validation.get("combined_buildup_jobs") != 23
            or validation.get("combined_buildup_histories") != 3_046_468
            or validation.get("registered_delayed_source_cells") != 8
            or validation.get("registered_events_per_family") != 250_000
            or validation.get("plan1_delayed_consumed") is not False
            or validation.get("incremental_83334_plus_166666_merge_allowed") is not False
        ):
            errors.append("full-stat activation full-inventory/fresh-only closure differs")
        seed_record = validation.get("delayed_seed_registry") or {}
        if (
            seed_record.get("sha256") != sha256_small(root / FULLSTAT_DELAYED_SEEDS)
            or int(seed_record.get("bytes", -1)) != (root / FULLSTAT_DELAYED_SEEDS).stat().st_size
        ):
            errors.append("full-stat activation validation does not bind delayed seed registry")
        expected_status = "PASS__SF3_FULLSTAT_ACTIVATION_AND_FRESH_DELAYED_SOURCES_READY"
        if summary.get("status") != expected_status or manifest.get("status") != expected_status:
            errors.append("full-stat activation output status differs")
        if (
            summary.get("selected_buildup_jobs") != 23
            or summary.get("selected_plan1_buildup_jobs") != 10
            or summary.get("selected_topup_buildup_jobs") != 13
            or summary.get("selected_buildup_histories") != 3_046_468
            or summary.get("registered_delayed_source_cells") != 8
            or summary.get("registered_delayed_triggers_per_family") != 250_000
            or summary.get("source_mixture_policy") != "50k deterministic actual-position draws; stride 5 to 10k; retained flux multiplied by 5"
            or summary.get("plan1_83334_consumed_or_merged") is not False
            or summary.get("incremental_166666_merge_allowed") is not False
            or (manifest.get("fresh_delayed_seeds") or {})
            != {row["family"]: int(row["seed"]) for row in plan}
        ):
            errors.append("full-stat activation summary/inventory/seed authority differs")
        cards = validation.get("source_cards")
        if not isinstance(cards, list) or len(cards) != 8:
            errors.append("full-stat activation card registry is not eight")
            return validation, [], [], errors
        by_family = {row.get("family"): row for row in plan}
        positive: list[str] = []
        zero: list[str] = []
        seen: set[str] = set()
        for card in cards:
            family = str(card.get("family", ""))
            row = by_family.get(family)
            if row is None or family in seen:
                errors.append(f"full-stat activation family unknown/duplicate: {family!r}")
                continue
            seen.add(family)
            job_id = str(card.get("job_id", ""))
            disposition = card.get("execution_disposition")
            if (
                job_id != row.get("job_id")
                or int(card.get("seed", -1)) != int(row.get("seed", -2))
                or int(card.get("registered_events", -1)) != 250_000
                or int(row.get("registered_events", -1)) != 250_000
                or int(card.get("actual_transport_events", -1)) != int(row.get("actual_transport_events", -2))
                or card.get("execution_disposition") != row.get("execution_disposition")
            ):
                errors.append(f"full-stat activation plan/card binding differs: {family}")
            activity = finite_float(
                card.get("transported_ground_activity_Bq"),
                f"{family} transported ground activity",
            )
            if disposition == "RUN_FRESH_250000":
                if (
                    int(row.get("events", -1)) != 250_000
                    or int(row.get("actual_transport_events", -1)) != 250_000
                    or str(row.get("transport_eligible", "")).lower() != "true"
                    or int(card.get("actual_transport_events", -1)) != 250_000
                    or activity <= 0.0
                    or int(card.get("original_blocks", -1)) != 50_000
                    or int(card.get("transport_blocks", -1)) != 10_000
                    or int(card.get("position_stride", -1)) != 5
                ):
                    errors.append(f"full-stat positive delayed event contract differs: {family}")
                positive.append(job_id)
            elif disposition == "SKIP_ZERO_A15":
                upper_rate = finite_float(card.get("transported_ground_rate_upper95_s-1"), f"{family} zero rate upper")
                upper = finite_float(card.get("transported_ground_A15_upper95_Bq_conservative"), f"{family} zero upper")
                if (
                    int(row.get("events", -1)) != 0
                    or int(row.get("actual_transport_events", -1)) != 0
                    or str(row.get("transport_eligible", "")).lower() != "false"
                    or int(card.get("actual_transport_events", -1)) != 0
                    or activity != 0.0
                    or upper_rate <= 0.0
                    or not math.isclose(upper, upper_rate, rel_tol=0.0, abs_tol=1e-18)
                    or int(card.get("original_blocks", -1)) != 0
                    or int(card.get("transport_blocks", -1)) != 0
                    or int(card.get("position_stride", -1)) != 5
                ):
                    errors.append(f"full-stat zero delayed contract differs: {family}")
                zero.append(job_id)
            else:
                errors.append(f"full-stat delayed disposition differs: {family}/{disposition}")
        if seen != set(by_family):
            errors.append("full-stat activation family closure differs")
        return validation, positive, zero, errors
    except Exception as exc:
        errors.append(str(exc))
        return validation, [], [], errors


def delayed_receipt_state(root: Path) -> dict[str, Any]:
    activation, positive, zero, errors = activation_state(root)
    payload = optional_json(root / FULLSTAT_DELAYED_AGGREGATE)
    if activation is None or payload is None:
        return state_result(False, errors=errors)
    selected = payload.get("selected_receipts")
    if not isinstance(selected, list):
        errors.append("full-stat delayed aggregate selected_receipts is not an array")
        selected = []
    plan_rows = load_csv(root / FULLSTAT_DELAYED_PLAN)
    by_id = {str(row.get("job_id", "")): row for row in plan_rows}
    ids: list[str] = []
    for row in selected:
        job_id = str(row.get("job_id", ""))
        ids.append(job_id)
        expected = by_id.get(job_id)
        if expected is None:
            errors.append(f"full-stat delayed aggregate has unknown job: {job_id!r}")
            continue
        receipt, receipt_errors = load_bound_receipt(
            root, FULLSTAT_DELAYED_RECEIPT_ROOT, job_id, row,
        )
        errors.extend(receipt_errors)
        if (
            row.get("family") != expected.get("family")
            or row.get("stage") != "fullstat_delayed"
            or int(row.get("registered_events", -1)) != 250_000
            or int(row.get("events", -1)) != 250_000
            or int(row.get("actual_transport_events", -1)) != 250_000
            or int(row.get("seed", -1)) != int(expected.get("seed", -2))
            or row.get("execution_disposition") != "RUN_FRESH_250000"
            or row.get("transport_eligible") is not True
        ):
            errors.append(f"full-stat delayed receipt is not fresh250k: {job_id}")
        setup = str(expected.get("setup_path", ""))
        header = receipt.get("sim_header") or {}
        if (
            receipt.get("profile_id") != FULLSTAT_DELAYED_NAMESPACE
            or receipt.get("job_id") != job_id
            or receipt.get("stage") != "fullstat_delayed"
            or receipt.get("geometry") != "SF3"
            or receipt.get("mode") != "delayed"
            or receipt.get("family") != expected.get("family")
            or int(receipt.get("registered_events", -1)) != 250_000
            or int(receipt.get("events", -1)) != 250_000
            or int(receipt.get("actual_transport_events", -1)) != 250_000
            or int(receipt.get("seed", -1)) != int(expected.get("seed", -2))
            or Path(str(receipt.get("setup_path", ""))).resolve() != Path(setup).resolve()
            or receipt.get("source_status") != expected.get("source_status")
            or receipt.get("execution_disposition") != "RUN_FRESH_250000"
            or receipt.get("transport_eligible") is not True
            or receipt.get("seed_namespace") != FULLSTAT_DELAYED_NAMESPACE
            or receipt.get("plan1_83334_role") != "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE"
            or receipt.get("incremental_merge_allowed") is not False
            or Path(str(receipt.get("receipt_namespace", ""))).resolve()
            != (root / FULLSTAT_DELAYED_RECEIPT_ROOT).resolve()
            or receipt.get("isotope_dat_path") is not None
            or Path(str(header.get("geometry", ""))).resolve() != Path(setup).resolve()
            or int(header.get("seed", -1)) != int(expected.get("seed", -2))
            or header.get("policy") != "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"
            or receipt.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY"
        ):
            errors.append(f"full-stat delayed canonical receipt payload differs: {job_id}")
    exclusions = payload.get("execution_exclusions") or {}
    positive_families = [row["family"] for row in plan_rows if row.get("job_id") in set(positive)]
    zero_families = [row["family"] for row in plan_rows if row.get("job_id") in set(zero)]
    if (
        payload.get("profile_id") != FULLSTAT_DELAYED_NAMESPACE
        or payload.get("status") != "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE"
        or int(payload.get("registered_families", -1)) != 8
        or payload.get("positive_A15_families") != positive_families
        or payload.get("zero_A15_families") != zero_families
        or int(payload.get("planned_transport_jobs", -1)) != len(positive)
        or int(payload.get("validated_transport_jobs", -1)) != len(positive)
        or int(payload.get("fresh_triggers_per_positive_family", -1)) != 250_000
        or int(payload.get("validated_fresh_triggers", -1)) != len(positive) * 250_000
        or int(payload.get("zero_A15_jobs_skipped", -1)) != len(zero)
        or set(ids) != set(positive)
        or len(ids) != len(set(ids))
        or set(exclusions) != set(zero)
        or any(exclusions.get(job_id) != ZERO_REASON for job_id in zero)
        or payload.get("plan1_83334_read") is not False
        or payload.get("plan1_83334_pooled") is not False
        or payload.get("incremental_merge_used") is not False
        or payload.get("delayed_strategy") != "FRESH_COMPLETE_250000_PER_POSITIVE_FULL_INVENTORY_FAMILY"
    ):
        errors.append("full-stat delayed aggregate identity/zero/fresh-only closure differs")
    return state_result(not errors, {"positive": len(positive), "zero": len(zero)}, errors)


def resource_timeline_state(root: Path) -> dict[str, Any]:
    """Validate the published resource audit as a restart authority.

    This deliberately rebinds the audit to the current small manifest, event
    logs, canonical guarded completion authorities, and delayed dispositions.
    It does not reopen any transport payload.
    """

    payload = optional_json(root / FULLSTAT_RESOURCE)
    if payload is None:
        return state_result(False)
    errors: list[str] = []
    expected_labels = list(GUARDED_STEPS)
    expected_phases = dict(PHASE_BY_GUARDED_STEP)

    def expect(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def exact_small_record(value: Any, relative: str, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            errors.append(f"resource {label} binding is not an object")
            return {}
        path = root / relative
        try:
            expected = {
                "path": str(path.resolve()),
                "bytes": path.stat().st_size,
                "sha256": sha256_small(path),
            }
            observed_path = Path(str(value.get("path", ""))).resolve()
            expect(observed_path == path.resolve(), f"resource {label} path differs")
            expect(value.get("bytes") == expected["bytes"], f"resource {label} byte count differs")
            expect(value.get("sha256") == expected["sha256"], f"resource {label} digest differs")
            return expected
        except Exception as exc:
            errors.append(f"resource {label} compact authority unavailable: {exc}")
            return {}

    expect(payload.get("schema_version") == 1, "resource timeline schema differs")
    expect(payload.get("profile_id") == FULLSTAT_RESOURCE_PROFILE, "resource timeline profile differs")
    expect(payload.get("status") == FULLSTAT_RESOURCE_STATUS, "resource timeline status differs")
    expect(payload.get("ready") is True and payload.get("pass") is True, "resource timeline is not canonical PASS")
    expect(payload.get("write_contract") == FULLSTAT_RESOURCE_WRITE_CONTRACT, "resource timeline write-once contract differs")
    expect(payload.get("scope") == FULLSTAT_RESOURCE_SCOPE, "resource timeline scope differs")
    expect(payload.get("configured_cpu_budget_max") == MAX_CPU_BUDGET, "resource CPU ceiling differs")
    expect(payload.get("adaptive_workers_min") == 4 and payload.get("adaptive_workers_max") == 6, "resource adaptive-worker range differs")
    expect(payload.get("production_controller_workers") == WORKERS, "resource actual controller workers differ from 4")
    expect(payload.get("mem_available_floor_bytes") == MEM_FLOOR, "resource MemAvailable floor differs")
    expect(payload.get("swap_free_floor_bytes") == SWAP_FLOOR, "resource SwapFree floor differs")
    expect(payload.get("dynamic_disk_reserve_bytes") == DISK_RESERVE, "resource disk reserve differs")
    expect(payload.get("quota_percent_is_worker_count") is False, "resource quota is conflated with workers")
    expect(payload.get("quota_percent_allowed_values") == [300, 400], "resource quota registry differs")
    observed_quotas = payload.get("quota_percent_observed")
    expect(
        isinstance(observed_quotas, list)
        and bool(observed_quotas)
        and set(observed_quotas).issubset({300, 400}),
        "resource observed quotas are outside exact 300/400",
    )

    _activation, positive, zero, activation_errors = activation_state(root)
    if activation_errors:
        errors.extend(f"resource delayed disposition binding: {error}" for error in activation_errors)
    scope = payload.get("job_scope")
    if not isinstance(scope, dict):
        errors.append("resource job_scope is not an object")
        scope = {}
    expect(scope.get("plan1_background_jobs") == 21, "resource Plan-1 background count differs")
    expect(scope.get("topup_background_jobs") == 28, "resource top-up background count differs")
    expect(scope.get("fullstat_background_jobs") == 49, "resource full-stat background count differs")
    expect(scope.get("delayed_registered_families") == 8, "resource delayed registered count differs")
    expect(scope.get("delayed_positive_transport_jobs") == len(positive), "resource positive delayed count differs")
    expect(scope.get("delayed_zero_skips") == len(zero), "resource zero delayed count differs")
    expect(scope.get("total_transport_jobs") == 49 + len(positive), "resource total transport count differs")
    expect(scope.get("Plan1_83334_read_or_pooled") is False, "resource consumed/pooled Plan-1 83334")

    receipt_groups = payload.get("transport_receipt_ids")
    if not isinstance(receipt_groups, dict):
        errors.append("resource transport receipt registry is not an object")
        receipt_groups = {}
    expected_counts = {
        "plan1_background": 21,
        "topup_background": 28,
        "fresh250k_delayed": len(positive),
        "zero_A15_skips": len(zero),
    }
    all_receipts: set[str] = set()
    for name, count in expected_counts.items():
        values = receipt_groups.get(name)
        valid = (
            isinstance(values, list)
            and all(isinstance(item, str) and item for item in values)
            and len(values) == count
            and len(set(values)) == count
            and values == sorted(values)
        )
        expect(valid, f"resource receipt identity registry differs: {name}")
        if valid:
            expect(all_receipts.isdisjoint(values), f"resource receipt namespaces overlap: {name}")
            all_receipts.update(values)
    expect(set(receipt_groups) == set(expected_counts), "resource receipt namespace keys differ")
    expect(set(receipt_groups.get("fresh250k_delayed", [])) == set(positive), "resource positive delayed identities differ")
    expect(set(receipt_groups.get("zero_A15_skips", [])) == set(zero), "resource zero delayed identities differ")

    metrics = payload.get("transport_completion_disk_metrics")
    if not isinstance(metrics, dict):
        errors.append("resource transport completion metrics are not an object")
        metrics = {}
    expect(metrics.get("all_new_transport_receipts_have_exactly_one_pass_metric") is True, "resource transport metric receipt closure failed")
    expect(metrics.get("all_finalized_attempts_dynamic_8GiB_reserve_pass") is True, "resource transport metric disk reserve failed")
    for name, count, identities in (
        ("topup_background", 28, set(receipt_groups.get("topup_background", []))),
        ("fresh250k_delayed", len(positive), set(positive)),
    ):
        summary = metrics.get(name)
        if not isinstance(summary, dict):
            errors.append(f"resource transport metric summary absent: {name}")
            continue
        successful = summary.get("successful_jobs")
        successful_ids = {
            str(row.get("job_id", ""))
            for row in successful
            if isinstance(row, dict)
        } if isinstance(successful, list) else set()
        expect(summary.get("expected_successful_jobs") == count, f"resource transport expected count differs: {name}")
        expect(isinstance(successful, list) and len(successful) == count and successful_ids == identities, f"resource successful transport identities differ: {name}")
        expect(summary.get("all_finalized_attempts_reserve_pass") is True, f"resource finalized transport reserve failed: {name}")
        expect(summary.get("all_canonical_receipts_have_exactly_one_pass_metric") is True, f"resource receipt metric uniqueness failed: {name}")
        minimum = summary.get("min_free_bytes")
        expect((count == 0 and minimum is None) or (isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= DISK_RESERVE), f"resource transport minimum disk differs: {name}")

    manifest_relative = "data/sf3_fullstat_followup_execution_manifest.json"
    manifest_expected = exact_small_record(
        (payload.get("followup_manifest_binding") or {}), manifest_relative,
        "followup manifest",
    )
    manifest_binding = payload.get("followup_manifest_binding")
    if not isinstance(manifest_binding, dict):
        manifest_binding = {}
    manifest_sha = manifest_expected.get("sha256")
    expect(manifest_binding.get("status") == MANIFEST_STATUS, "resource manifest status differs")
    expect(manifest_binding.get("guarded_steps") == expected_labels, "resource manifest guarded-step list differs")

    log_bindings = {
        "source_event_log": ("audit/sf3_fullstat_followup_pressure_guard.jsonl", "fullstat_guard_event_log"),
        "guard_session_wal": ("audit/sf3_fullstat_followup_guard_session_wal.jsonl", "fullstat_guard_session_wal"),
        "resource_completion_event_log": ("audit/sf3_fullstat_followup_resource_events.jsonl", "fullstat_resource_completion_log"),
    }
    authorities = payload.get("input_authorities")
    if not isinstance(authorities, dict):
        errors.append("resource input_authorities is not an object")
        authorities = {}
    manifest_input = authorities.get("fullstat_followup_manifest")
    expect(
        isinstance(manifest_input, dict)
        and {key: manifest_input.get(key) for key in ("path", "bytes", "sha256")} == manifest_expected,
        "resource manifest input binding differs",
    )
    for field, (relative, authority_key) in log_bindings.items():
        expected = exact_small_record(payload.get(field), relative, field)
        observed = authorities.get(authority_key)
        expect(
            isinstance(observed, dict)
            and {key: observed.get(key) for key in ("path", "bytes", "sha256")} == expected,
            f"resource input authority binding differs: {field}",
        )

    completion_statuses = {
        "transport_topup": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
        "build_fullstat_prompt": "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
        "transport_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
        "analyze_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "build_fullstat_common_response": "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
    }
    completion_authorities = payload.get("guarded_completion_authorities")
    if not isinstance(completion_authorities, dict):
        errors.append("resource guarded completion authority registry is not an object")
        completion_authorities = {}
    expect(set(completion_authorities) == set(expected_labels), "resource guarded completion authority labels differ")
    expect(payload.get("all_guarded_completion_authorities_independently_validated") is True, "resource guarded completion authorities were not independently validated")
    for label in expected_labels:
        relative = str(EXPECTED_STEP_METADATA[label][2])
        record = completion_authorities.get(label)
        expected = exact_small_record(record, relative, f"guarded completion {label}")
        if isinstance(record, dict):
            expect(record.get("relative_path") == relative, f"resource guarded completion relative path differs: {label}")
            expect(record.get("status") == completion_statuses[label], f"resource guarded completion status differs: {label}")
            if label in {"build_fullstat_prompt", "analyze_fullstat_delayed", "build_fullstat_common_response"}:
                companion_relative = str(Path(relative).parent / "manifest.json")
                companion = record.get("companion_manifest")
                exact_small_record(companion, companion_relative, f"guarded completion companion {label}")
                if isinstance(companion, dict):
                    expect(companion.get("relative_path") == companion_relative, f"resource guarded companion relative path differs: {label}")
                    expect(companion.get("status") == completion_statuses[label], f"resource guarded companion status differs: {label}")
        if expected:
            expect(record is not None, f"resource guarded completion absent: {label}")

    expect(payload.get("required_guarded_session_labels") == expected_labels, "resource required guard labels differ")
    expect(payload.get("observed_guarded_session_labels") == expected_labels, "resource observed guard labels differ")
    expect(payload.get("exact_session_label_to_phase") == expected_phases, "resource label/phase map differs")
    expect(payload.get("required_exact_label_stage_coverage") == expected_phases, "resource required stage coverage differs")
    expect(
        payload.get("observed_closed_exact_label_stage_coverage")
        == {label: [phase] for label, phase in expected_phases.items()},
        "resource observed stage coverage differs",
    )
    expect(payload.get("all_required_exact_label_stage_bindings_pass") is True, "resource exact guard stage binding failed")

    sessions = payload.get("guard_sessions")
    if not isinstance(sessions, list):
        errors.append("resource guard_sessions is not an array")
        sessions = []
    expect([row.get("session_label") for row in sessions if isinstance(row, dict)] == expected_labels, "resource selected guard sessions differ")
    for row in sessions:
        if not isinstance(row, dict):
            errors.append("resource selected guard session is not an object")
            continue
        label = str(row.get("session_label", ""))
        expect(row.get("phase") == expected_phases.get(label), f"resource guard phase differs: {label}")
        expect(row.get("actual_workers") == WORKERS, f"resource guard workers differ: {label}")
        expect(row.get("terminal_quota_percent") == 400, f"resource guard terminal quota differs: {label}")
        expect(row.get("closure") == "GUARD_EXIT_RESTORE_NORMAL", f"resource guard closure differs: {label}")
        expect(row.get("hard_floor_breach_observed") is False, f"resource guard hard floor failed: {label}")
        expect(row.get("manifest_sha256") == manifest_sha, f"resource guard manifest digest differs: {label}")
        expect(row.get("completion_record_mode") in {"NORMAL_STAGE_RETURNCODE_ZERO", "RECOVERED_FROM_WAL_AND_ORIGINAL_GUARD_CLOSURE"}, f"resource guard completion mode differs: {label}")
        expect(isinstance(row.get("guard_session_wal_started_at"), str) and bool(row.get("guard_session_wal_started_at")), f"resource guard WAL timestamp absent: {label}")
        expect(row.get("canonical_completion_authority") == completion_authorities.get(label), f"resource guard canonical completion binding differs: {label}")
        expect(isinstance(row.get("minimum_mem_available_bytes"), int) and row.get("minimum_mem_available_bytes") >= MEM_FLOOR, f"resource guard memory floor failed: {label}")
        expect(isinstance(row.get("minimum_swap_free_bytes"), int) and row.get("minimum_swap_free_bytes") >= SWAP_FLOOR, f"resource guard swap floor failed: {label}")
        expect(isinstance(row.get("completion_disk_free_bytes"), int) and row.get("completion_disk_free_bytes") >= DISK_RESERVE, f"resource guard disk floor failed: {label}")

    complete_guard = payload.get("complete_guard_event_log_audit")
    if not isinstance(complete_guard, dict):
        errors.append("resource complete guard audit is not an object")
        complete_guard = {}
    session_count = complete_guard.get("session_count")
    by_label = complete_guard.get("sessions_by_label")
    expect(complete_guard.get("all_bytes_audited") is True, "resource complete guard bytes were not audited")
    expect(complete_guard.get("all_sessions_cleanly_closed") is True, "resource complete guard sessions are not clean")
    expect(isinstance(session_count, int) and not isinstance(session_count, bool) and session_count >= len(expected_labels), "resource complete guard session count differs")
    expect(isinstance(by_label, dict) and set(by_label) == set(expected_labels) and all(isinstance(by_label[label], int) and by_label[label] >= 1 for label in expected_labels), "resource complete guard label coverage differs")
    if isinstance(session_count, int) and isinstance(by_label, dict):
        expect(sum(by_label.values()) == session_count, "resource complete guard by-label count differs")
        expect(payload.get("superseded_or_retried_clean_guard_sessions") == session_count - len(expected_labels), "resource retried guard count differs")

    wal_audit = payload.get("guard_session_wal_audit")
    if not isinstance(wal_audit, dict):
        errors.append("resource guard WAL audit is not an object")
        wal_audit = {}
    expect(wal_audit.get("all_clean_guard_sessions_have_write_ahead_start") is True, "resource clean guard sessions lack WAL starts")
    expect(wal_audit.get("duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct") is True, "resource WAL duplicate-key policy differs")
    if isinstance(session_count, int):
        expect(wal_audit.get("guard_session_keys") == session_count, "resource WAL clean-session key count differs")
        expect(isinstance(wal_audit.get("rows"), int) and wal_audit.get("rows") >= session_count, "resource WAL row count differs")
    expect(isinstance(wal_audit.get("orphan_pre_guard_crash_rows"), int) and wal_audit.get("orphan_pre_guard_crash_rows") >= 0, "resource WAL orphan summary differs")
    expect(payload.get("normal_or_crash_recovery_record_XOR_pass") is True, "resource normal/recovery XOR failed")
    expect(payload.get("all_completion_resources_from_original_guard_closure_not_live_inference") is True, "resource used live completion inference")
    normal = payload.get("normal_completion_records")
    recovered = payload.get("crash_recovered_completion_records")
    expect(isinstance(normal, int) and isinstance(recovered, int) and normal >= 0 and recovered >= 0 and normal + recovered == len(expected_labels), "resource normal/recovery record counts differ")
    expect(payload.get("all_guard_sessions_closed") is True, "resource selected guard sessions are not closed")
    expect(payload.get("all_guard_sessions_exactly_one_clean_closure") is True, "resource selected guard closures are not unique")
    expect(payload.get("all_guard_sessions_terminal_quota_400") is True, "resource selected guard sessions did not restore400")
    expect(payload.get("all_guard_samples_hard_floors_pass") is True, "resource selected guard hard floors failed")
    expect(payload.get("actual_workers_observed") == [WORKERS], "resource observed worker registry differs")
    timeline = payload.get("timeline")
    if not isinstance(timeline, list):
        errors.append("resource timeline is not an array")
        timeline = []
    expect(
        isinstance(payload.get("timeline_rows"), int)
        and payload.get("timeline_rows") == len(timeline)
        and bool(timeline),
        "resource timeline row count differs/is empty",
    )
    for index, row in enumerate(timeline):
        if not isinstance(row, dict):
            errors.append(f"resource timeline row {index} is not an object")
            continue
        label = str(row.get("session_label", ""))
        expect(label in expected_phases, f"resource timeline label differs at row {index}")
        expect(row.get("phase") == expected_phases.get(label), f"resource timeline phase differs at row {index}")
        expect(row.get("actual_workers") == WORKERS, f"resource timeline workers differ at row {index}")
        expect(row.get("quota_percent") in {300, 400}, f"resource timeline quota differs at row {index}")
        expect(row.get("quota_percent_is_worker_count") is False, f"resource timeline quota semantics differ at row {index}")
        expect(isinstance(row.get("mem_available_bytes"), int) and row.get("mem_available_bytes") >= MEM_FLOOR, f"resource timeline memory floor failed at row {index}")
        expect(isinstance(row.get("swap_free_bytes"), int) and row.get("swap_free_bytes") >= SWAP_FLOOR, f"resource timeline swap floor failed at row {index}")
        expect(isinstance(row.get("disk_free_after_projection_bytes"), int) and row.get("disk_free_after_projection_bytes") >= DISK_RESERVE, f"resource timeline disk floor failed at row {index}")
    expect(isinstance(payload.get("min_mem_available_bytes"), int) and payload.get("min_mem_available_bytes") >= MEM_FLOOR, "resource timeline memory minimum failed")
    expect(isinstance(payload.get("min_swap_free_bytes"), int) and payload.get("min_swap_free_bytes") >= SWAP_FLOOR, "resource timeline swap minimum failed")
    expect(isinstance(payload.get("min_disk_free_after_projection_bytes"), int) and payload.get("min_disk_free_after_projection_bytes") >= DISK_RESERVE, "resource timeline disk minimum failed")
    expect(isinstance(payload.get("min_new_transport_completion_free_bytes"), int) and payload.get("min_new_transport_completion_free_bytes") >= DISK_RESERVE, "resource transport disk minimum failed")
    expect(isinstance(payload.get("min_all_dynamic_disk_observations_bytes"), int) and payload.get("min_all_dynamic_disk_observations_bytes") >= DISK_RESERVE, "resource combined disk minimum failed")
    expect(payload.get("missing") == [] and payload.get("pending") == [] and payload.get("errors") == [], "resource authority records missing/pending/errors")
    expect(payload.get("SIM_opened_statted_discovered_or_hashed") is False, "resource audit accessed SIM")
    expect(payload.get("transport_launched_by_auditor") is False, "resource auditor launched transport")
    expect(payload.get("systemd_or_service_action_performed_by_auditor") is False, "resource auditor mutated systemd/service state")
    return state_result(not errors, {"status": payload.get("status"), "positive": len(positive), "zero": len(zero)}, errors)


def completion_state(step_id: str, root: Path) -> dict[str, Any]:
    if step_id == "await_plan1_stage07":
        gate, errors = plan1_gate(root)
        return state_result(gate is not None and not errors, gate or {}, errors)
    if step_id == "prepare_topup":
        return prepare_topup_state(root)
    if step_id in {"transport_topup", "validate_topup_receipts"}:
        return topup_receipt_state(root)
    if step_id in OUTPUT_PAIRS:
        return output_pair_state(root, step_id)
    if step_id == "build_fullstat_activation":
        payload, positive, zero, errors = activation_state(root)
        return state_result(payload is not None and not errors, {"positive": positive, "zero": zero}, errors)
    if step_id in {"transport_fullstat_delayed", "validate_fullstat_delayed_receipts"}:
        return delayed_receipt_state(root)
    if step_id == "build_fullstat_resource_timeline":
        return resource_timeline_state(root)
    if step_id == "finalize_fullstat":
        payload = optional_json(root / FULLSTAT_FINAL)
        if payload is None:
            return state_result(False)
        errors = []
        if (
            payload.get("status") != "PASS__SF3_FULLSTAT_CHAIN_COMPLETE__TERMINAL_NO_SECOND_TOPUP"
            or payload.get("ready") is not True
            or payload.get("errors") != []
            or payload.get("missing") != []
        ):
            errors.append("full-stat terminal final audit differs")
        return state_result(not errors, {"status": payload.get("status")}, errors)
    return state_result(False, errors=[f"unknown full-stat followup step: {step_id}"])


def safe_completion(step_id: str, root: Path) -> dict[str, Any]:
    try:
        return completion_state(step_id, root)
    except Exception as exc:
        return state_result(False, errors=[f"{step_id} compact authority inspection failed: {exc}"])


def inspect_chain(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    gate, gate_errors = plan1_gate(root)
    base = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "manifest": {"status": manifest["status"], "path": str(MANIFEST_PATH if root == PACKAGE_ROOT else root / "synthetic_manifest.json")},
        "restart_policy": "RECOMPUTE_FROM_CANONICAL_SMALL_AUTHORITIES__NEVER_TRUST_JOURNAL",
        "receipt_policy": "SKIP_CANONICAL_PASS__NEVER_RERUN",
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__NAMED_SMALL_AUTHORITIES_ONLY",
        "transport_or_analysis_launched": False,
    }
    if gate_errors:
        return {**base, "status": "BLOCKED__SF3_FULLSTAT_FOLLOWUP_PLAN1_GATE_CONFLICT", "ready": False, "complete": False, "terminal": False, "next_step": "await_plan1_stage07", "completed_prefix": [], "errors": gate_errors, "step_states": []}
    if gate is None:
        return {**base, "status": "NOT_READY__SF3_FULLSTAT_FOLLOWUP_WAITING_FOR_PLAN1_STAGE07", "ready": False, "complete": False, "terminal": False, "next_step": "await_plan1_stage07", "completed_prefix": [], "errors": [], "step_states": []}
    if gate["topup_required"] is False:
        stop = stop_state(root, gate)
        if stop["errors"]:
            status, ready, complete = "BLOCKED__SF3_FULLSTAT_FALSE_GATE_ARTIFACT_CONFLICT", False, False
        elif stop["complete"]:
            status, ready, complete = STOP_STATUS, True, True
        else:
            status, ready, complete = "READY__SF3_FULLSTAT_FOLLOWUP_PUBLISH_TERMINAL_STOP", True, False
        return {**base, "status": status, "ready": ready, "complete": complete, "terminal": complete, "next_step": None if complete else "publish_terminal_stop", "completed_prefix": ["await_plan1_stage07"], "errors": stop["errors"], "gate": gate, "step_states": [{"id": "await_plan1_stage07", **state_result(True, gate)}, {"id": "publish_terminal_stop", **stop}]}
    if (root / str(STOP_AUTHORITY.relative_to(PACKAGE_ROOT))).exists():
        return {**base, "status": "BLOCKED__SF3_FULLSTAT_TRUE_GATE_HAS_STOP_AUTHORITY", "ready": False, "complete": False, "terminal": False, "next_step": "prepare_topup", "completed_prefix": ["await_plan1_stage07"], "errors": ["terminal STOP authority exists although central gate requires full-stat"], "gate": gate, "step_states": []}
    states = [{"id": row["id"], **safe_completion(str(row["id"]), root)} for row in manifest["steps"]]
    first = next((index for index, row in enumerate(states) if not row["complete"]), None)
    errors: list[str] = []
    if first is not None:
        errors.extend(states[first]["errors"])
        current_step = manifest["steps"][first]
        current_target = current_step.get("write_once_target")
        current_recoverable = (
            current_step.get("id") == "build_fullstat_activation"
            and current_step.get("existing_target_policy")
            == "IDEMPOTENT_PREPARE_MAY_REPUBLISH_MISSING_SMALL_VALIDATION"
            and activation_validation_republishable(root)
        )
        if current_target and (root / str(current_target)).exists() and not current_recoverable:
            errors.append(f"existing noncanonical write-once target blocks restart: {root / str(current_target)}")
        for index, row in enumerate(states[first + 1:], first + 1):
            if row["errors"]:
                errors.extend(
                    f"downstream noncanonical authority before {states[first]['id']}: {row['id']}: {error}"
                    for error in row["errors"]
                )
            if row["complete"]:
                errors.append(f"out-of-order completed authority after gap: {row['id']}")
            target = manifest["steps"][index].get("write_once_target")
            if target and (root / str(target)).exists() and not row["complete"]:
                errors.append(f"downstream noncanonical write-once target exists before gap closes: {root / str(target)}")
    if errors:
        status, ready = "BLOCKED__SF3_FULLSTAT_FOLLOWUP_AUTHORITY_OR_WRITE_ONCE_CONFLICT", False
    elif first is None:
        status, ready = COMPLETE_STATUS, True
    else:
        status, ready = "READY__SF3_FULLSTAT_FOLLOWUP_NEXT_STEP", True
    completed_prefix = [row["id"] for row in states[: first if first is not None else len(states)]]
    return {**base, "status": status, "ready": ready, "complete": first is None, "terminal": first is None, "next_step": None if first is None else manifest["steps"][first]["id"], "completed_prefix": completed_prefix, "errors": errors, "gate": gate, "step_states": states}


def expand_argv(raw: Sequence[str]) -> list[str]:
    replacements = {"{python}": sys.executable, "{code}": str(CODE_ROOT), "{package}": str(PACKAGE_ROOT)}
    return [replacements.get(token, token) for token in raw]


def parse_json_stdout(result: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f"{label} did not emit one JSON object: {exc}; stderr={result.stderr[-2000:]!r}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} JSON root is not an object")
    return payload


def run_preflight(raw: Sequence[str], step_id: str) -> dict[str, Any]:
    result = subprocess.run(expand_argv(raw), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    payload = parse_json_stdout(result, f"{step_id} preflight")
    if result.returncode != 0 or payload.get("ready") is not True:
        raise RuntimeError(json.dumps({"status": "NOT_READY__SF3_FULLSTAT_STEP_PREFLIGHT", "step": step_id, "returncode": result.returncode, "preflight": payload}, sort_keys=True))
    return payload


def guard_events_since(initial_size: int) -> list[dict[str, Any]]:
    try:
        size = GUARD_EVENT_LOG.stat().st_size
    except FileNotFoundError:
        return []
    if size < initial_size or size - initial_size > MAX_GUARD_DELTA_BYTES:
        raise RuntimeError("full-stat guard event log was truncated or startup delta is oversized")
    if size == initial_size:
        return []
    with GUARD_EVENT_LOG.open("rb") as handle:
        handle.seek(initial_size)
        payload = handle.read(size - initial_size)
    lines = payload.split(b"\n") if payload.endswith(b"\n") else payload.split(b"\n")[:-1]
    events = []
    for raw in lines:
        if not raw:
            continue
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("full-stat guard event is not an object")
        events.append(value)
    return events


def read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"compact JSONL authority empty/oversized: {path} ({size})")
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise RuntimeError(f"JSONL authority lacks terminal newline: {path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"JSONL row is not an object: {path}:{index}")
        rows.append(value)
    return rows


def closed_guard_segments(root: Path) -> list[dict[str, Any]]:
    path = root / str(GUARD_EVENT_LOG.relative_to(PACKAGE_ROOT))
    if not path.is_file():
        return []
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_SMALL_BYTES or not raw.endswith(b"\n"):
        raise RuntimeError("full-stat guard log is empty, oversized, or not newline-closed")
    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_start = 0
    offset = 0
    for index, line in enumerate(raw.splitlines(keepends=True), 1):
        if not line.endswith(b"\n"):
            raise RuntimeError(f"full-stat guard row is not newline-closed: {index}")
        value = json.loads(line[:-1].decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"full-stat guard row is not an object: {index}")
        label = str(value.get("session_label", ""))
        if label not in GUARDED_STEPS:
            raise RuntimeError(f"full-stat guard row has unknown session label: {label!r}")
        if not current:
            current_start = offset
        elif label != current[0].get("session_label"):
            raise RuntimeError("full-stat guard session label changed before clean closure")
        current.append(value)
        offset += len(line)
        if value.get("decision_reasons") == ["guard_exit_restore_normal"]:
            summary = validate_closed_guard_session(current, label, 0, root)
            segments.append({
                "session_label": label,
                "guard_log_start_byte": current_start,
                "guard_log_end_byte": offset,
                "events": current,
                "summary": summary,
            })
            current = []
    if current:
        raise RuntimeError(
            f"full-stat guard log ends with unclosed session: {current[0].get('session_label')}"
        )
    return segments


def reconcile_guarded_resource_events(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Repair only the post-authority/pre-resource-row controller crash window."""
    resource_path = root / str(RESOURCE_EVENT_LOG.relative_to(PACKAGE_ROOT))
    wal_path = root / str(GUARD_SESSION_WAL.relative_to(PACKAGE_ROOT))
    root_manifest_path = root / "data/sf3_fullstat_followup_execution_manifest.json"
    manifest_sha = sha256_small(root_manifest_path)
    existing = read_jsonl_objects(resource_path)
    by_label: dict[str, dict[str, Any]] = {}
    for row in existing:
        label = str(row.get("session_label", ""))
        if label not in GUARDED_STEPS or label in by_label:
            raise RuntimeError(f"full-stat resource completion label unknown/duplicate: {label!r}")
        if (
            row.get("status") != "PASS"
            or row.get("followup_manifest_sha256") != manifest_sha
        ):
            raise RuntimeError(f"existing full-stat resource completion row differs: {label}")
        by_label[label] = row
    completed_labels = [
        label for label in GUARDED_STEPS
        if safe_completion(label, root)["complete"]
    ]
    missing_labels = [label for label in completed_labels if label not in by_label]
    if not missing_labels:
        return []
    wal_rows = read_jsonl_objects(wal_path)
    wal_by_key: dict[tuple[str, int], list[dict[str, Any]]] = {}
    wal_identities: set[tuple[str, int, str]] = set()
    for index, row in enumerate(wal_rows, 1):
        try:
            key = (str(row.get("session_label", "")), int(row.get("guard_log_start_byte", -1)))
            identity = (key[0], key[1], str(row.get("at", "")))
            if identity in wal_identities:
                raise RuntimeError(f"duplicate WAL row identity: {identity}")
            wal_identities.add(identity)
            if (
                row.get("schema_version") != 1
                or row.get("status") != "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE"
                or key[0] not in GUARDED_STEPS
                or key[1] < 0
                or not identity[2]
                or row.get("service_unit") != DEFAULT_SERVICE_UNIT
                or row.get("followup_manifest_sha256") != manifest_sha
                or row.get("completion_authority") != EXPECTED_STEP_METADATA[key[0]][2]
                or Path(str(row.get("disk_path", ""))).resolve() != root.resolve()
                or int(row.get("dynamic_disk_reserve_bytes", -1)) != DISK_RESERVE
                or row.get("stage_started") is not False
                or row.get("SIM_opened_statted_discovered_or_hashed") is not False
            ):
                raise RuntimeError(f"WAL contract fields differ: row {index}")
            wal_by_key.setdefault(key, []).append(row)
        except Exception as exc:
            raise RuntimeError(f"full-stat guard WAL row invalid: {index}: {exc}") from exc
    segments = closed_guard_segments(root)
    recovered: list[str] = []
    for label in missing_labels:
        candidates = [
            segment for segment in segments
            if segment["session_label"] == label
            and (label, int(segment["guard_log_start_byte"])) in wal_by_key
        ]
        if not candidates:
            raise RuntimeError(
                f"canonical guarded authority lacks write-ahead-bound clean guard session: {label}"
            )
        segment = candidates[-1]
        wal = wal_by_key[(label, int(segment["guard_log_start_byte"]))][-1]
        closed = segment["summary"]
        append_jsonl(resource_path, {
            "schema_version": 1,
            "status": "PASS",
            "at": utc_now(),
            "phase": PHASE_BY_GUARDED_STEP[label],
            "session_label": label,
            "service_unit": DEFAULT_SERVICE_UNIT,
            "followup_manifest_sha256": manifest_sha,
            "actual_workers": WORKERS,
            "configured_cpu_budget_max": MAX_CPU_BUDGET,
            "quota_percent": 400,
            "quota_percent_is_worker_count": False,
            "guard_log_start_byte": segment["guard_log_start_byte"],
            "guard_log_end_byte": segment["guard_log_end_byte"],
            "mem_floor_bytes": MEM_FLOOR,
            "swap_floor_bytes": SWAP_FLOOR,
            "dynamic_disk_reserve_bytes": DISK_RESERVE,
            "mem_available_bytes": closed["completion_mem_available_bytes"],
            "swap_free_bytes": closed["completion_swap_free_bytes"],
            "disk_free_after_projection_bytes": closed["completion_disk_free_bytes"],
            "stage_returncode": None,
            "completion_authority_inferred_success": True,
            "recovered_after_controller_crash": True,
            "guard_session_wal_started_at": wal.get("at"),
            "guard_session": closed,
            "SIM_opened_statted_discovered_or_hashed_by_controller": False,
        })
        append_jsonl(
            root / str(JOURNAL_PATH.relative_to(PACKAGE_ROOT)),
            {
                "at": utc_now(), "event": "resource_completion_recovered_after_controller_crash",
                "step": label, "guard_log_start_byte": segment["guard_log_start_byte"],
                "guard_log_end_byte": segment["guard_log_end_byte"],
                "journal_is_physics_authority": False,
            },
        )
        recovered.append(label)
    return recovered


def guard_ready(events: Sequence[dict[str, Any]], step_id: str) -> bool:
    matching = [row for row in events if row.get("session_label") == step_id]
    if not matching:
        return False
    for row in matching:
        reasons = row.get("decision_reasons")
        if not isinstance(reasons, list) or any(not isinstance(value, str) for value in reasons):
            raise RuntimeError(f"malformed full-stat guard reasons: {step_id}")
        if any(value.endswith("_hard_floor_breach") or value.startswith("guard_exit_restore_") for value in reasons):
            raise RuntimeError(f"full-stat guard rejected/closed before launch: {step_id}/{reasons}")
    row = matching[-1]
    try:
        quota = int(row.get("quota_percent"))
        mem = int(row.get("mem_available_bytes"))
        swap = int(row.get("swap_free_bytes"))
        disk = int(row.get("disk_free_bytes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"full-stat guard readiness sample incomplete: {step_id}") from exc
    if (
        row.get("unit") != DEFAULT_SERVICE_UNIT
        or row.get("unit_state") not in ("active", "activating")
        or quota not in (300, 400)
        or mem < MEM_FLOOR
        or swap < SWAP_FLOOR
        or disk < DISK_RESERVE
        or int(row.get("disk_floor_bytes", -1)) != DISK_RESERVE
    ):
        raise RuntimeError(f"full-stat guard readiness contract failed: {step_id}")
    return True


def validate_closed_guard_session(
    events: Sequence[dict[str, Any]], step_id: str, guard_returncode: int,
    disk_path: Path = PACKAGE_ROOT,
) -> dict[str, Any]:
    if guard_returncode != 0:
        raise RuntimeError(f"full-stat guard session exited nonzero: {step_id}/rc={guard_returncode}")
    if not events:
        raise RuntimeError(f"full-stat guard session emitted no events: {step_id}")
    unexpected = [row.get("session_label") for row in events if row.get("session_label") != step_id]
    if unexpected:
        raise RuntimeError(f"full-stat guard log delta contains other sessions: {step_id}/{unexpected}")
    closures: list[dict[str, Any]] = []
    samples = 0
    for row in events:
        if row.get("unit") != DEFAULT_SERVICE_UNIT:
            raise RuntimeError(f"full-stat guard session service unit differs: {step_id}")
        reasons = row.get("decision_reasons")
        if not isinstance(reasons, list) or any(not isinstance(value, str) for value in reasons):
            raise RuntimeError(f"malformed full-stat guard reasons in closed session: {step_id}")
        if any(value.endswith("_hard_floor_breach") for value in reasons):
            raise RuntimeError(f"full-stat guard hard floor breached during session: {step_id}/{reasons}")
        if "guard_exit_restore_failed" in reasons:
            raise RuntimeError(f"full-stat guard quota restore failed during session: {step_id}")
        if reasons == ["guard_exit_restore_normal"]:
            closures.append(row)
            continue
        try:
            quota = int(row.get("quota_percent"))
            observed_quota = int(row.get("observed_quota_percent"))
            mem = int(row.get("mem_available_bytes"))
            swap = int(row.get("swap_free_bytes"))
            disk = int(row.get("disk_free_bytes"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"full-stat guard pressure sample incomplete: {step_id}") from exc
        if (
            row.get("unit_state") not in ("active", "activating")
            or quota not in (300, 400)
            or observed_quota not in (300, 400)
            or not isinstance(row.get("quota_changed"), bool)
            or not isinstance(row.get("cgroup_pressure"), dict)
            or mem < MEM_FLOOR
            or swap < SWAP_FLOOR
            or disk < DISK_RESERVE
            or int(row.get("mem_floor_bytes", -1)) != MEM_FLOOR
            or int(row.get("swap_floor_bytes", -1)) != SWAP_FLOOR
            or int(row.get("disk_floor_bytes", -1)) != DISK_RESERVE
            or Path(str(row.get("disk_path", ""))).resolve() != disk_path.resolve()
        ):
            raise RuntimeError(f"full-stat guard pressure sample violates resource contract: {step_id}")
        samples += 1
    if len(closures) != 1 or events[-1] is not closures[0]:
        raise RuntimeError(f"full-stat guard session lacks one terminal clean closure: {step_id}")
    try:
        closure_quota = int(closures[0].get("quota_percent"))
        closure_observed_quota = int(closures[0].get("observed_quota_percent"))
        closure_mem = int(closures[0].get("mem_available_bytes"))
        closure_swap = int(closures[0].get("swap_free_bytes"))
        closure_disk = int(closures[0].get("disk_free_bytes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"full-stat guard closure resource snapshot missing: {step_id}") from exc
    if (
        closure_quota != 400
        or closure_observed_quota not in (300, 400)
        or not isinstance(closures[0].get("quota_changed"), bool)
        or closure_mem < MEM_FLOOR
        or closure_swap < SWAP_FLOOR
        or closure_disk < DISK_RESERVE
        or int(closures[0].get("mem_floor_bytes", -1)) != MEM_FLOOR
        or int(closures[0].get("swap_floor_bytes", -1)) != SWAP_FLOOR
        or int(closures[0].get("disk_floor_bytes", -1)) != DISK_RESERVE
        or Path(str(closures[0].get("disk_path", ""))).resolve() != disk_path.resolve()
    ):
        raise RuntimeError(f"full-stat guard closure did not restore four cores above hard floors: {step_id}")
    if samples < 1:
        raise RuntimeError(f"full-stat guard session has no pressure samples: {step_id}")
    return {
        "session_label": step_id,
        "samples": samples,
        "closure": "guard_exit_restore_normal",
        "restored_quota_percent": 400,
        "hard_floor_breaches": 0,
        "completion_mem_available_bytes": closure_mem,
        "completion_swap_free_bytes": closure_swap,
        "completion_disk_free_bytes": closure_disk,
    }


def wait_guard_ready(guard: subprocess.Popen[Any], initial_size: int, step_id: str, timeout_s: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if guard.poll() is not None:
            raise RuntimeError(f"full-stat guard exited before readiness: {step_id}/rc={guard.returncode}")
        if guard_ready(guard_events_since(initial_size), step_id):
            time.sleep(0.1)
            if guard.poll() is not None:
                raise RuntimeError(f"full-stat guard exited during readiness confirmation: {step_id}")
            return
        time.sleep(0.25)
    raise RuntimeError(f"full-stat guard did not publish readiness within 15 seconds: {step_id}")


def terminate_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def resource_snapshot() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        fields = rest.split()
        if fields and fields[0].isdigit():
            values[key] = int(fields[0]) * 1024
    mem, swap = values.get("MemAvailable", -1), values.get("SwapFree", -1)
    disk = shutil.disk_usage(PACKAGE_ROOT).free
    if mem < MEM_FLOOR or swap < SWAP_FLOOR or disk < DISK_RESERVE:
        raise RuntimeError(f"full-stat completion resource floor failed: mem={mem} swap={swap} disk={disk}")
    return {"mem_available_bytes": mem, "swap_free_bytes": swap, "disk_free_after_projection_bytes": disk}


def run_guarded(raw: Sequence[str], unit: str, step_id: str) -> int:
    guard_script = CODE_ROOT / "guard_sf3_service_pressure.py"
    check = subprocess.run([sys.executable, str(guard_script), "--check-prerequisites", "--unit", unit], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    live = parse_json_stdout(check, "full-stat pressure guard live check")
    if check.returncode != 0 or live.get("ready") is not True:
        raise RuntimeError(json.dumps(live, sort_keys=True))
    initial_size = GUARD_EVENT_LOG.stat().st_size if GUARD_EVENT_LOG.is_file() else 0
    wal_started_at = utc_now()
    append_jsonl(GUARD_SESSION_WAL, {
        "schema_version": 1,
        "status": "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE",
        "at": wal_started_at,
        "session_label": step_id,
        "service_unit": unit,
        "guard_log_start_byte": initial_size,
        "followup_manifest_sha256": sha256_small(MANIFEST_PATH),
        "completion_authority": EXPECTED_STEP_METADATA[step_id][2],
        "disk_path": str(PACKAGE_ROOT),
        "dynamic_disk_reserve_bytes": DISK_RESERVE,
        "stage_started": False,
        "SIM_opened_statted_discovered_or_hashed": False,
    })
    guard = subprocess.Popen([
        sys.executable, str(guard_script), "--unit", unit,
        "--event-log", str(GUARD_EVENT_LOG), "--normal-quota", "400",
        "--throttle-quota", "300", "--safe-samples", "6", "--session-label", step_id,
        "--disk-path", str(PACKAGE_ROOT), "--disk-floor", str(DISK_RESERVE),
    ])
    stage: subprocess.Popen[Any] | None = None
    returncode: int | None = None
    guard_returncode: int | None = None
    try:
        wait_guard_ready(guard, initial_size, step_id)
        stage = subprocess.Popen(expand_argv(raw), start_new_session=True)
        while stage.poll() is None:
            if guard.poll() is not None:
                terminate_group(stage)
                raise RuntimeError(f"full-stat guard exited while stage active: {step_id}/rc={guard.returncode}")
            time.sleep(1.0)
        if guard.poll() is not None:
            raise RuntimeError(f"full-stat guard exited before stage completion acceptance: {step_id}")
        returncode = int(stage.returncode)
    finally:
        if stage is not None and stage.poll() is None:
            terminate_group(stage)
        if guard.poll() is None:
            guard.terminate()
            try:
                guard.wait(timeout=20)
            except subprocess.TimeoutExpired:
                guard.kill()
                guard.wait(timeout=10)
        guard_returncode = int(guard.returncode if guard.returncode is not None else -1)
        restore = subprocess.run([
            sys.executable, str(guard_script), "--restore-only", "--unit", unit,
            "--normal-quota", "400", "--throttle-quota", "300",
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        restored = parse_json_stdout(restore, "full-stat pressure guard restore") if restore.stdout.strip() else {}
        if restore.returncode != 0 or restored.get("restoration_verified_by_reread") is not True or restored.get("restored_quota_percent") != 400:
            raise RuntimeError(f"full-stat guard failed verified quota restore: stdout={restore.stdout[-1000:]!r} stderr={restore.stderr[-1000:]!r}")
    final_size = GUARD_EVENT_LOG.stat().st_size
    closed_session = validate_closed_guard_session(
        guard_events_since(initial_size), step_id,
        int(guard_returncode if guard_returncode is not None else -1),
    )
    if returncode == 0:
        append_jsonl(RESOURCE_EVENT_LOG, {
            "schema_version": 1,
            "status": "PASS",
            "at": utc_now(),
            "phase": PHASE_BY_GUARDED_STEP[step_id],
            "session_label": step_id,
            "service_unit": unit,
            "followup_manifest_sha256": sha256_small(MANIFEST_PATH),
            "actual_workers": WORKERS,
            "configured_cpu_budget_max": MAX_CPU_BUDGET,
            "quota_percent": 400,
            "quota_percent_is_worker_count": False,
            "guard_log_start_byte": initial_size,
            "guard_log_end_byte": final_size,
            "mem_floor_bytes": MEM_FLOOR,
            "swap_floor_bytes": SWAP_FLOOR,
            "dynamic_disk_reserve_bytes": DISK_RESERVE,
            "mem_available_bytes": closed_session["completion_mem_available_bytes"],
            "swap_free_bytes": closed_session["completion_swap_free_bytes"],
            "disk_free_after_projection_bytes": closed_session["completion_disk_free_bytes"],
            "stage_returncode": 0,
            "completion_authority_inferred_success": False,
            "recovered_after_controller_crash": False,
            "guard_session_wal_started_at": wal_started_at,
            "guard_session": closed_session,
            "SIM_opened_statted_discovered_or_hashed_by_controller": False,
        })
    return int(returncode if returncode is not None else 1)


def stale_active(step_id: str) -> list[str]:
    if step_id == "transport_topup":
        rows = topup_plan(PACKAGE_ROOT)
    elif step_id == "transport_fullstat_delayed":
        rows = load_csv(PACKAGE_ROOT / FULLSTAT_DELAYED_PLAN)
    else:
        return []
    stale: list[str] = []
    for row in rows:
        run_root = Path(str(row.get("run_root", "")))
        if not run_root.is_absolute():
            raise RuntimeError(f"full-stat plan run_root is not absolute: {row.get('job_id')}")
        active = run_root / "jobs" / str(row.get("job_id")) / "active"
        if active.exists():
            stale.append(str(active))
    return stale


def run_step(step: dict[str, Any], unit: str) -> None:
    step_id = str(step["id"])
    if step_id in VIRTUAL_STEPS or not step.get("command"):
        raise RuntimeError(f"virtual/wait step unexpectedly selected for execution: {step_id}")
    if step_id in TRANSPORT_STEPS:
        stale = stale_active(step_id)
        if stale:
            raise RuntimeError(json.dumps({"status": "BLOCKED__SF3_FULLSTAT_STALE_ACTIVE_ATTEMPT", "step": step_id, "stale_active_attempts": stale}, sort_keys=True))
    if step.get("preflight"):
        run_preflight(step["preflight"], step_id)
    append_jsonl(JOURNAL_PATH, {"at": utc_now(), "event": "step_start", "step": step_id, "argv": expand_argv(step["command"]), "journal_is_physics_authority": False})
    try:
        returncode = run_guarded(step["command"], unit, step_id) if step.get("guard") is True else subprocess.run(expand_argv(step["command"]), check=False).returncode
        if returncode != 0:
            raise RuntimeError(f"full-stat step command failed: {step_id}/rc={returncode}")
        completed = safe_completion(step_id, PACKAGE_ROOT)
        if not completed["complete"]:
            raise RuntimeError(json.dumps({"status": "FAIL__SF3_FULLSTAT_STEP_DID_NOT_PUBLISH_AUTHORITY", "step": step_id, "completion": completed}, sort_keys=True))
        append_jsonl(JOURNAL_PATH, {"at": utc_now(), "event": "step_complete", "step": step_id, "journal_is_physics_authority": False})
    except Exception as exc:
        append_jsonl(JOURNAL_PATH, {"at": utc_now(), "event": "step_failed", "step": step_id, "error": str(exc), "journal_is_physics_authority": False})
        raise


def controller_lock() -> Any:
    class Lock:
        def __enter__(self) -> None:
            LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.handle = LOCK_PATH.open("a+")
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                self.handle.close()
                raise RuntimeError(f"another full-stat followup controller holds {LOCK_PATH}") from exc

        def __exit__(self, *_args: Any) -> None:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
            self.handle.close()
    return Lock()


def advance_locked(manifest: dict[str, Any], run_to_completion: bool, unit: str) -> dict[str, Any]:
    while True:
        gate, gate_errors = plan1_gate(PACKAGE_ROOT)
        if gate_errors:
            raise RuntimeError(json.dumps({"status": "BLOCKED__SF3_FULLSTAT_PLAN1_GATE_CONFLICT", "errors": gate_errors}, sort_keys=True))
        if gate is not None and gate.get("topup_required") is True:
            reconcile_guarded_resource_events(PACKAGE_ROOT, manifest)
        status = inspect_chain(PACKAGE_ROOT, manifest)
        atomic_replace_json(STATE_PATH, {**status, "updated_at": utc_now()})
        if status["errors"]:
            raise RuntimeError(json.dumps(status, sort_keys=True))
        if status["complete"]:
            return status
        if status["next_step"] == "await_plan1_stage07":
            return status
        if status["next_step"] == "publish_terminal_stop":
            publish_stop(PACKAGE_ROOT, status["gate"])
        else:
            by_id = {row["id"]: row for row in manifest["steps"]}
            run_step(by_id[status["next_step"]], unit)
        if not run_to_completion:
            return inspect_chain(PACKAGE_ROOT, manifest)


def advance(run_to_completion: bool, unit: str) -> dict[str, Any]:
    manifest = load_manifest()
    if unit != manifest["required_service_unit"]:
        raise ValueError(f"service unit must equal {manifest['required_service_unit']}")
    with controller_lock():
        return advance_locked(manifest, run_to_completion, unit)


def wait_and_advance(unit: str, poll_seconds: float) -> dict[str, Any]:
    if poll_seconds < 30.0 or poll_seconds > 60.0:
        raise ValueError("wait heartbeat must be within 30..60 seconds")
    manifest = load_manifest()
    if unit != manifest["required_service_unit"]:
        raise ValueError(f"service unit must equal {manifest['required_service_unit']}")
    with controller_lock():
        while True:
            status = inspect_chain(PACKAGE_ROOT, manifest)
            if status["errors"]:
                raise RuntimeError(json.dumps(status, sort_keys=True))
            atomic_replace_json(STATE_PATH, {**status, "updated_at": utc_now(), "wait_mode": True})
            append_jsonl(JOURNAL_PATH, {"at": utc_now(), "event": "wait_heartbeat", "status": status["status"], "next_step": status["next_step"], "journal_is_physics_authority": False})
            if status["next_step"] != "await_plan1_stage07" or status["complete"]:
                break
            time.sleep(poll_seconds)
        return advance_locked(manifest, True, unit)


def fixture_json(root: Path, relative: str, payload: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_text(payload), encoding="utf-8")


def fixture_csv(root: Path, relative: str, rows: list[dict[str, Any]]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fixture_gate(root: Path, required: bool) -> None:
    ratio = 0.70 if required else 0.80
    decision = "TOPUP_TO_S3D_FULL_STAT_REQUIRED" if required else "STOP__NO_FULLSTAT_TOPUP"
    fixture_json(root, PLAN1_MISSION, {
        "status": "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE",
        "fullstat_gate": {"metric": "F3_SF3_over_SE3_full_envelope", "operator": "<=", "threshold": CENTRAL_GATE, "observed_central_ratio": ratio, "topup_required": required, "decision": decision, "proxy_controls_gate": False},
    })
    fixture_json(root, PLAN1_FINAL, {
        "status": PLAN1_STATUS, "ready": True, "errors": [], "missing": [],
        "mission_results": {"central_F3_ratio": ratio, "topup_required": required},
        "fullstat_disposition": {"observed_central_ratio": ratio, "threshold": CENTRAL_GATE, "topup_required": required, "mission_decision": decision, "proxy_controls_gate": False},
    })


def fixture_resource_authority(
    root: Path,
    manifest: dict[str, Any],
    positive: Sequence[str],
    zero: Sequence[str],
) -> dict[str, Any]:
    """Build a producer-shaped compact resource authority for the pure self-test."""

    fixture_json(root, "data/sf3_fullstat_followup_execution_manifest.json", manifest)
    for relative, marker in (
        ("audit/sf3_fullstat_followup_pressure_guard.jsonl", "guard"),
        ("audit/sf3_fullstat_followup_guard_session_wal.jsonl", "wal"),
        ("audit/sf3_fullstat_followup_resource_events.jsonl", "resource"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"synthetic_compact_binding": marker}) + "\n", encoding="utf-8")

    def binding(relative: str) -> dict[str, Any]:
        path = root / relative
        return {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": sha256_small(path),
        }

    labels = list(GUARDED_STEPS)
    manifest_binding = {
        **binding("data/sf3_fullstat_followup_execution_manifest.json"),
        "status": MANIFEST_STATUS,
        "guarded_steps": labels,
    }
    completion_statuses = {
        "transport_topup": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
        "build_fullstat_prompt": "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
        "transport_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
        "analyze_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "build_fullstat_common_response": "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
    }
    completion_authorities: dict[str, dict[str, Any]] = {}
    for label in labels:
        relative = str(EXPECTED_STEP_METADATA[label][2])
        record = {
            **binding(relative),
            "relative_path": relative,
            "status": completion_statuses[label],
        }
        if label in {"build_fullstat_prompt", "analyze_fullstat_delayed", "build_fullstat_common_response"}:
            companion = str(Path(relative).parent / "manifest.json")
            record["companion_manifest"] = {
                **binding(companion),
                "relative_path": companion,
                "status": completion_statuses[label],
            }
        completion_authorities[label] = record

    plan1_ids = [f"synthetic_plan1_background_{index:02d}" for index in range(21)]
    topup_ids = sorted(str(row["job_id"]) for row in load_csv(root / TOPUP_PLAN))
    positive_ids = sorted(str(value) for value in positive)
    zero_ids = sorted(str(value) for value in zero)

    def metric_summary(name: str, identities: Sequence[str], offset: int) -> dict[str, Any]:
        successful = [
            {
                "job_id": job_id,
                "attempt": 1,
                "at": f"2026-08-16T12:{offset:02d}:{index:02d}+00:00",
                "wall_s": 1.0,
                "peak_rss_bytes": 1024 + index,
                "artifact_bytes": 2048 + index,
                "free_bytes": DISK_RESERVE + 4096 + index,
            }
            for index, job_id in enumerate(identities)
        ]
        return {
            "namespace": f"/synthetic/{name}",
            "resource_metrics_path": f"/synthetic/{name}/resource_metrics.jsonl",
            "expected_successful_jobs": len(identities),
            "successful_jobs": successful,
            "failed_finalized_attempts": 0,
            "total_finalized_attempts": len(identities),
            "min_free_bytes": DISK_RESERVE + 4096 if identities else None,
            "dynamic_disk_reserve_bytes": DISK_RESERVE,
            "all_finalized_attempts_reserve_pass": True,
            "all_canonical_receipts_have_exactly_one_pass_metric": True,
            **({"zero_positive_transport_disposition": True} if not identities else {}),
        }

    topup_metrics = metric_summary("topup", topup_ids, 10)
    delayed_metrics = metric_summary("delayed", positive_ids, 20)
    sessions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    for index, label in enumerate(labels):
        mem = MEM_FLOOR + 100 + index
        swap = SWAP_FLOOR + 100 + index
        disk = DISK_RESERVE + 100 + index
        timeline.append({
            "at": f"2026-08-16T0{index}:00:00+00:00",
            "phase": PHASE_BY_GUARDED_STEP[label],
            "session_label": label,
            "actual_workers": WORKERS,
            "quota_percent": 400,
            "quota_percent_is_worker_count": False,
            "mem_available_bytes": mem,
            "swap_free_bytes": swap,
            "disk_free_after_projection_bytes": disk,
            "decision_reasons": ["synthetic_sample"],
        })
        sessions.append({
            "session_label": label,
            "phase": PHASE_BY_GUARDED_STEP[label],
            "actual_workers": WORKERS,
            "guard_log_start_byte": index * 100,
            "guard_log_end_byte": index * 100 + 90,
            "sample_count": 1,
            "quota_percent_sequence": [400],
            "quota_values_allowed_exactly_300_or_400": True,
            "terminal_quota_percent": 400,
            "closure": "GUARD_EXIT_RESTORE_NORMAL",
            "hard_floor_breach_observed": False,
            "minimum_mem_available_bytes": mem,
            "minimum_swap_free_bytes": swap,
            "minimum_disk_free_bytes": disk,
            "completion_mem_available_bytes": mem,
            "completion_swap_free_bytes": swap,
            "completion_disk_free_bytes": disk,
            "completion_record_mode": (
                "RECOVERED_FROM_WAL_AND_ORIGINAL_GUARD_CLOSURE"
                if index == 2 else "NORMAL_STAGE_RETURNCODE_ZERO"
            ),
            "guard_session_wal_started_at": f"2026-08-16T0{index}:00:00+00:00",
            "canonical_completion_authority": completion_authorities[label],
            "manifest_sha256": manifest_binding["sha256"],
        })

    source_log = binding("audit/sf3_fullstat_followup_pressure_guard.jsonl")
    wal_log = binding("audit/sf3_fullstat_followup_guard_session_wal.jsonl")
    resource_log = binding("audit/sf3_fullstat_followup_resource_events.jsonl")
    return {
        "schema_version": 1,
        "profile_id": FULLSTAT_RESOURCE_PROFILE,
        "status": FULLSTAT_RESOURCE_STATUS,
        "ready": True,
        "pass": True,
        "checked_at": "2026-08-16T13:00:00+00:00",
        "built_at": "2026-08-16T13:00:01+00:00",
        "write_contract": FULLSTAT_RESOURCE_WRITE_CONTRACT,
        "scope": FULLSTAT_RESOURCE_SCOPE,
        "configured_cpu_budget_max": MAX_CPU_BUDGET,
        "adaptive_workers_min": 4,
        "adaptive_workers_max": 6,
        "production_controller_workers": WORKERS,
        "mem_available_floor_bytes": MEM_FLOOR,
        "swap_free_floor_bytes": SWAP_FLOOR,
        "dynamic_disk_reserve_bytes": DISK_RESERVE,
        "quota_percent_is_worker_count": False,
        "quota_transition_percent": [400, 300, 400],
        "quota_transition_field_semantics": "NORMAL_THROTTLE_RESTORE_POLICY__300_IS_CONDITIONAL_AND_NEVER_A_WORKER_OR_STATISTICS_COUNT",
        "quota_percent_allowed_values": [300, 400],
        "quota_percent_observed": [400],
        "safe_all_400_quota_sessions_are_pass_eligible": True,
        "artificial_throttle_required": False,
        "job_scope": {
            "plan1_background_jobs": 21,
            "topup_background_jobs": 28,
            "fullstat_background_jobs": 49,
            "delayed_registered_families": 8,
            "delayed_positive_transport_jobs": len(positive_ids),
            "delayed_zero_skips": len(zero_ids),
            "total_transport_jobs": 49 + len(positive_ids),
            "Plan1_83334_read_or_pooled": False,
        },
        "transport_receipt_ids": {
            "plan1_background": plan1_ids,
            "topup_background": topup_ids,
            "fresh250k_delayed": positive_ids,
            "zero_A15_skips": zero_ids,
        },
        "transport_completion_disk_metrics": {
            "topup_background": topup_metrics,
            "fresh250k_delayed": delayed_metrics,
            "all_new_transport_receipts_have_exactly_one_pass_metric": True,
            "all_finalized_attempts_dynamic_8GiB_reserve_pass": True,
            "min_free_bytes": DISK_RESERVE + 4096,
        },
        "followup_manifest_binding": manifest_binding,
        "required_guarded_session_labels": labels,
        "observed_guarded_session_labels": labels,
        "guarded_completion_authorities": completion_authorities,
        "all_guarded_completion_authorities_independently_validated": True,
        "exact_session_label_to_phase": dict(PHASE_BY_GUARDED_STEP),
        "required_exact_label_stage_coverage": dict(PHASE_BY_GUARDED_STEP),
        "observed_closed_exact_label_stage_coverage": {
            label: [PHASE_BY_GUARDED_STEP[label]] for label in labels
        },
        "all_required_exact_label_stage_bindings_pass": True,
        "guard_sessions": sessions,
        "guard_session_wal_audit": {
            "rows": 5,
            "guard_session_keys": 5,
            "all_clean_guard_sessions_have_write_ahead_start": True,
            "orphan_pre_guard_crash_rows": 0,
            "duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct": True,
        },
        "normal_completion_records": 4,
        "crash_recovered_completion_records": 1,
        "normal_or_crash_recovery_record_XOR_pass": True,
        "all_completion_resources_from_original_guard_closure_not_live_inference": True,
        "complete_guard_event_log_audit": {
            "all_bytes_audited": True,
            "all_sessions_cleanly_closed": True,
            "session_count": 5,
            "sessions_by_label": {label: 1 for label in labels},
            "sessions": [],
        },
        "superseded_or_retried_clean_guard_sessions": 0,
        "all_guard_sessions_closed": True,
        "all_guard_sessions_exactly_one_clean_closure": True,
        "all_guard_sessions_terminal_quota_400": True,
        "all_guard_samples_hard_floors_pass": True,
        "actual_workers_observed": [WORKERS],
        "timeline_rows": len(timeline),
        "min_mem_available_bytes": MEM_FLOOR + 100,
        "min_swap_free_bytes": SWAP_FLOOR + 100,
        "min_disk_free_after_projection_bytes": DISK_RESERVE + 100,
        "min_guard_sample_disk_free_bytes": DISK_RESERVE + 100,
        "min_guard_completion_disk_free_bytes": DISK_RESERVE + 100,
        "min_new_transport_completion_free_bytes": DISK_RESERVE + 4096,
        "min_all_dynamic_disk_observations_bytes": DISK_RESERVE + 100,
        "timeline": timeline,
        "source_event_log": source_log,
        "guard_session_wal": wal_log,
        "resource_completion_event_log": resource_log,
        "input_authorities": {
            "fullstat_followup_manifest": {
                key: manifest_binding[key] for key in ("path", "bytes", "sha256")
            },
            "fullstat_guard_event_log": source_log,
            "fullstat_guard_session_wal": wal_log,
            "fullstat_resource_completion_log": resource_log,
        },
        "missing": [],
        "pending": [],
        "errors": [],
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched_by_auditor": False,
        "systemd_or_service_action_performed_by_auditor": False,
    }


def self_test() -> dict[str, Any]:
    manifest = load_manifest()
    with tempfile.TemporaryDirectory(prefix="sf3-fullstat-followup-selftest-") as temporary:
        base = Path(temporary)
        false_root = base / "false"
        fixture_gate(false_root, False)
        stop_ready = inspect_chain(false_root, manifest)
        if stop_ready["next_step"] != "publish_terminal_stop" or not stop_ready["ready"]:
            raise AssertionError(f"false central gate did not select STOP publication: {stop_ready}")
        publish_stop(false_root, stop_ready["gate"])
        stopped = inspect_chain(false_root, manifest)
        if not stopped["complete"] or stopped["status"] != STOP_STATUS:
            raise AssertionError("terminal false-gate STOP did not close")
        fixture_csv(false_root, TOPUP_PLAN, [{"job_id": "forbidden_after_stop"}])
        if not inspect_chain(false_root, manifest)["status"].startswith("BLOCKED__"):
            raise AssertionError("full-stat artifact created after terminal STOP was accepted")

        wrong_status_root = base / "wrong_mission_status"
        fixture_gate(wrong_status_root, True)
        wrong_mission = load_json(wrong_status_root / PLAN1_MISSION)
        wrong_mission["status"] = "PASS__WRONG_MISSION_AUTHORITY"
        fixture_json(wrong_status_root, PLAN1_MISSION, wrong_mission)
        if not inspect_chain(wrong_status_root, manifest)["status"].startswith("BLOCKED__"):
            raise AssertionError("wrong Plan-1 mission status was accepted")

        negative_root = base / "negative_ratio"
        fixture_gate(negative_root, True)
        negative_mission = load_json(negative_root / PLAN1_MISSION)
        negative_final = load_json(negative_root / PLAN1_FINAL)
        negative_mission["fullstat_gate"]["observed_central_ratio"] = -0.1
        negative_final["mission_results"]["central_F3_ratio"] = -0.1
        negative_final["fullstat_disposition"]["observed_central_ratio"] = -0.1
        fixture_json(negative_root, PLAN1_MISSION, negative_mission)
        fixture_json(negative_root, PLAN1_FINAL, negative_final)
        if not inspect_chain(negative_root, manifest)["status"].startswith("BLOCKED__"):
            raise AssertionError("negative Plan-1 central ratio was accepted")

        mutated_manifest = json.loads(json.dumps(manifest))
        mutated_manifest["steps"][4]["preflight"] = []
        try:
            validate_manifest(mutated_manifest)
        except RuntimeError:
            pass
        else:
            raise AssertionError("mutated heavy-step preflight was accepted")

        downstream_root = base / "downstream_conflict"
        fixture_gate(downstream_root, True)
        relative, _status, summary_name, manifest_name = OUTPUT_PAIRS["build_fullstat_common_response"]
        fixture_json(downstream_root, f"{relative}/{summary_name}", {"status": "FAIL__SYNTHETIC_STALE"})
        fixture_json(downstream_root, f"{relative}/{manifest_name}", {"status": "FAIL__SYNTHETIC_STALE"})
        if not inspect_chain(downstream_root, manifest)["status"].startswith("BLOCKED__"):
            raise AssertionError("downstream noncanonical write-once target was not blocked immediately")

        root = base / "true"
        initial = inspect_chain(root, manifest)
        if initial["status"] != "NOT_READY__SF3_FULLSTAT_FOLLOWUP_WAITING_FOR_PLAN1_STAGE07":
            raise AssertionError("empty synthetic chain did not wait for Plan-1 stage07")
        fixture_gate(root, True)
        if inspect_chain(root, manifest)["next_step"] != "prepare_topup":
            raise AssertionError("true central gate did not select top-up preparation")
        topup_rows = [{
            "ordinal": index + 1, "job_id": f"topup_{index:02d}",
            "stage": "fullstat_topup_background", "geometry": "SF3",
            "mode": "instant" if index < 15 else "buildup",
            "family": FAMILIES[index % 8],
            "events": (
                (1_161_382 if index == 0 else 100_000)
                if index < 15 else (830_976 if index == 15 else 100_000)
            ),
            "seed": 10000 + index,
            "source_path": str((root / "config/topup" / f"topup_{index:02d}.source").resolve()),
            "setup_path": str((root / "geometry/SF3.geo.setup").resolve()),
            "run_root": str((root / "run_topup").resolve()),
            "receipt_path": str((root / TOPUP_RECEIPT_ROOT / f"topup_{index:02d}.json").resolve()),
        } for index in range(28)]
        partial_root = base / "idempotent_partial_topup"
        fixture_gate(partial_root, True)
        fixture_csv(partial_root, TOPUP_PLAN, topup_rows)
        fixture_csv(partial_root, TOPUP_SEEDS, [{"job_id": row["job_id"], "seed": row["seed"]} for row in topup_rows])
        partial_state = inspect_chain(partial_root, manifest)
        if partial_state["next_step"] != "prepare_topup" or partial_state["errors"]:
            raise AssertionError("canonical partial static top-up package was not resumable")
        fixture_csv(root, TOPUP_PLAN, topup_rows)
        fixture_csv(root, TOPUP_SEEDS, [{"job_id": row["job_id"], "seed": row["seed"]} for row in topup_rows])
        fixture_json(root, TOPUP_STATIC, {
            "status": "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED",
            "plan": {"jobs": 28}, "transport": {"launched": False, "runner_status": "PRESENT__STATIC_SELF_TEST_PASS__EXPLICIT_PHASE_REQUIRED_FOR_LAUNCH"}, "plan1_mutation": False,
        })
        selected_topup = []
        for row in topup_rows:
            receipt_relative = f"{TOPUP_RECEIPT_ROOT}/{row['job_id']}.json"
            fixture_json(root, receipt_relative, {
                "status": "PASS", "errors": [],
                "profile_id": "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1",
                "job_id": row["job_id"], "stage": "background", "geometry": "SF3",
                "mode": row["mode"], "family": row["family"],
                "events": int(row["events"]), "seed": int(row["seed"]),
                "source_path": row["source_path"], "source_sha256": "a" * 64,
                "setup_path": row["setup_path"],
                "attempt": 1,
                "attempt_dir": str((root / "run_topup/jobs" / row["job_id"] / "attempts/attempt01").resolve()),
                "sim_header": {"geometry": row["setup_path"], "seed": int(row["seed"]), "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"},
                "isotope_dat": {"TT_s": 1.0, "RP_record_count": 1, "terminal_EN": True, "errors": []},
                "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
                "peak_process_group_rss_bytes": 1024, "artifact_bytes": 2048,
            })
            receipt_path = root / receipt_relative
            selected_topup.append({
                "job_id": row["job_id"], "registered_stage": "fullstat_topup_background",
                "receipt_stage": "background", "geometry": "SF3", "mode": row["mode"],
                "family": row["family"], "events": int(row["events"]), "seed": int(row["seed"]),
                "receipt_path": str(receipt_path.resolve()),
                "receipt_sha256": sha256_small(receipt_path),
            })
        fixture_json(root, TOPUP_AGGREGATE, {
            "profile_id": "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1",
            "status": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
            "planned_jobs": 28, "validated_jobs": 28, "selected_receipts": selected_topup,
            "instant_validated_events": 2_561_382,
            "buildup_validated_events": 2_030_976,
            "plan1_mutation": False,
        })
        for step_id, (relative, status, summary_name, manifest_name) in OUTPUT_PAIRS.items():
            if step_id in {"analyze_fullstat_delayed", "build_fullstat_common_response", "build_fullstat_mission"}:
                continue
            fixture_json(root, f"{relative}/{summary_name}", {"status": status})
            fixture_json(root, f"{relative}/{manifest_name}", {"status": status})
        families = ["p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus"]
        delayed_rows = []
        cards = []
        for index, family in enumerate(families):
            positive = index < 7
            job_id = f"sf3_fullstat_delayed_{family}"
            delayed_rows.append({
                "ordinal": index + 1, "job_id": job_id, "stage": "fullstat_delayed",
                "geometry": "SF3", "mode": "delayed", "family": family,
                "registered_events": 250000, "events": 250000 if positive else 0,
                "actual_transport_events": 250000 if positive else 0,
                "seed": 20000 + index, "sampling_seed": 20000 + index,
                "seed_identity": job_id, "seed_namespace": FULLSTAT_DELAYED_NAMESPACE,
                "source_path": str((root / "config/fullstat_delayed_source_cards" / f"{job_id}.source").resolve()),
                "source_status": "PASS__SF3_FULLSTAT_STRIDE5_M10000_DELAYED_SOURCE_READY" if positive else "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
                "setup_path": str((root / "geometry/SF3.geo.setup").resolve()),
                "run_root": str((root / "run_delayed").resolve()),
                "receipt_path": str((root / FULLSTAT_DELAYED_RECEIPT_ROOT / f"{job_id}.json").resolve()),
                "execution_disposition": "RUN_FRESH_250000" if positive else "SKIP_ZERO_A15",
                "transport_eligible": str(positive).lower(),
                "plan1_83334_role": "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE",
                "incremental_merge_allowed": "false",
                "source_support": "REBUILT_FULLSTAT_23_BUILDUP_RECEIPTS_ACTUAL_RPIP_POSITIONS",
            })
            cards.append({
                "family": family, "job_id": job_id, "seed": 20000 + index,
                "registered_events": 250000,
                "actual_transport_events": 250000 if positive else 0,
                "execution_disposition": "RUN_FRESH_250000" if positive else "SKIP_ZERO_A15",
                "transported_ground_activity_Bq": float(index + 1) if positive else 0.0,
                "transported_ground_rate_upper95_s-1": None if positive else 0.01,
                "transported_ground_A15_upper95_Bq_conservative": None if positive else 0.01,
                "original_blocks": 50000 if positive else 0,
                "transport_blocks": 10000 if positive else 0,
                "position_stride": 5,
            })
        fixture_csv(root, FULLSTAT_DELAYED_PLAN, delayed_rows)
        delayed_seed_rows = [{
            "job_id": row["job_id"], "family": row["family"],
            "seed_identity": row["job_id"], "seed": row["seed"],
            "namespace": FULLSTAT_DELAYED_NAMESPACE,
            "collision_with_prior_plan1_or_topup": False,
            "sampling_and_transport_seed_shared_within_job": True,
        } for row in delayed_rows]
        fixture_csv(root, FULLSTAT_DELAYED_SEEDS, delayed_seed_rows)
        fixture_csv(root, PLAN1_SEEDS, [{"job_id": f"plan1_{index:02d}", "seed": 30000 + index} for index in range(30)])
        activation_status = "PASS__SF3_FULLSTAT_ACTIVATION_AND_FRESH_DELAYED_SOURCES_READY"
        activation_summary = {
            "status": activation_status,
            "selected_buildup_jobs": 23, "selected_plan1_buildup_jobs": 10,
            "selected_topup_buildup_jobs": 13, "selected_buildup_histories": 3_046_468,
            "registered_delayed_source_cells": 8,
            "registered_delayed_triggers_per_family": 250_000,
            "source_mixture_policy": "50k deterministic actual-position draws; stride 5 to 10k; retained flux multiplied by 5",
            "plan1_83334_consumed_or_merged": False,
            "incremental_166666_merge_allowed": False,
        }
        fixture_json(root, "outputs/fullstat/02_activation/day15_summary.json", activation_summary)
        fixture_json(root, "outputs/fullstat/02_activation/manifest.json", {
            **activation_summary,
            "hard_gates": {"central_mission_topup_required_true": True, "all_28_topup_background_canonical_PASS": True},
            "fresh_delayed_seeds": {row["family"]: int(row["seed"]) for row in delayed_rows},
        })
        delayed_seed_path = root / FULLSTAT_DELAYED_SEEDS
        fixture_json(root, FULLSTAT_ACTIVATION_VALIDATION, {
            "status": "PASS__SF3_FULLSTAT_ACTIVATION_VALIDATION",
            "combined_buildup_jobs": 23,
            "combined_buildup_histories": 3_046_468,
            "registered_delayed_source_cells": 8,
            "registered_events_per_family": 250_000,
            "plan1_delayed_consumed": False,
            "incremental_83334_plus_166666_merge_allowed": False,
            "delayed_seed_registry": {"path": str(delayed_seed_path.resolve()), "bytes": delayed_seed_path.stat().st_size, "sha256": sha256_small(delayed_seed_path)},
            "source_cards": cards,
        })
        positive_ids = [row["job_id"] for row in delayed_rows[:7]]
        zero_id = delayed_rows[-1]["job_id"]
        selected_delayed = []
        for row in delayed_rows[:7]:
            receipt_relative = f"{FULLSTAT_DELAYED_RECEIPT_ROOT}/{row['job_id']}.json"
            fixture_json(root, receipt_relative, {
                "status": "PASS", "errors": [], "profile_id": FULLSTAT_DELAYED_NAMESPACE,
                "job_id": row["job_id"], "stage": "fullstat_delayed", "geometry": "SF3",
                "mode": "delayed", "family": row["family"],
                "registered_events": 250000, "events": 250000,
                "actual_transport_events": 250000, "seed": int(row["seed"]),
                "source_status": row["source_status"],
                "execution_disposition": "RUN_FRESH_250000", "transport_eligible": True,
                "seed_namespace": FULLSTAT_DELAYED_NAMESPACE,
                "plan1_83334_role": "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE",
                "incremental_merge_allowed": False,
                "receipt_namespace": str((root / FULLSTAT_DELAYED_RECEIPT_ROOT).resolve()),
                "setup_path": row["setup_path"], "isotope_dat_path": None,
                "attempt": 1,
                "attempt_dir": str((root / "run_delayed/jobs" / row["job_id"] / "attempts/attempt01").resolve()),
                "sim_header": {"geometry": row["setup_path"], "seed": int(row["seed"]), "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"},
                "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
                "peak_process_group_rss_bytes": 2048, "artifact_bytes": 4096,
            })
            receipt_path = root / receipt_relative
            selected_delayed.append({
                "job_id": row["job_id"], "family": row["family"], "stage": "fullstat_delayed",
                "registered_events": 250000, "events": 250000,
                "actual_transport_events": 250000, "seed": int(row["seed"]),
                "execution_disposition": "RUN_FRESH_250000", "transport_eligible": True,
                "receipt_path": str(receipt_path.resolve()),
                "receipt_sha256": sha256_small(receipt_path),
            })
        fixture_json(root, FULLSTAT_DELAYED_AGGREGATE, {
            "profile_id": FULLSTAT_DELAYED_NAMESPACE,
            "status": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE", "registered_families": 8,
            "positive_A15_families": [row["family"] for row in delayed_rows[:7]],
            "zero_A15_families": [delayed_rows[-1]["family"]],
            "planned_transport_jobs": 7, "validated_transport_jobs": 7,
            "fresh_triggers_per_positive_family": 250000,
            "validated_fresh_triggers": 7 * 250000,
            "zero_A15_jobs_skipped": 1,
            "selected_receipts": selected_delayed,
            "execution_exclusions": {zero_id: ZERO_REASON}, "plan1_83334_read": False,
            "plan1_83334_pooled": False, "incremental_merge_used": False,
            "delayed_strategy": "FRESH_COMPLETE_250000_PER_POSITIVE_FULL_INVENTORY_FAMILY",
        })
        for step_id in ("analyze_fullstat_delayed", "build_fullstat_common_response", "build_fullstat_mission"):
            relative, status, summary_name, manifest_name = OUTPUT_PAIRS[step_id]
            fixture_json(root, f"{relative}/{summary_name}", {"status": status})
            fixture_json(root, f"{relative}/{manifest_name}", {"status": status})
        resource_fixture = fixture_resource_authority(root, manifest, positive_ids, [zero_id])
        fixture_json(root, FULLSTAT_RESOURCE, resource_fixture)
        if not resource_timeline_state(root)["complete"]:
            raise AssertionError(
                f"producer-shaped resource authority was rejected: {resource_timeline_state(root)}"
            )
        stale_resource = json.loads(json.dumps(resource_fixture))
        stale_resource["guard_session_wal"]["sha256"] = "0" * 64
        fixture_json(root, FULLSTAT_RESOURCE, stale_resource)
        if not resource_timeline_state(root)["errors"]:
            raise AssertionError("stale guard-session WAL digest was accepted")
        fixture_json(root, FULLSTAT_RESOURCE, resource_fixture)
        fixture_json(root, FULLSTAT_FINAL, {"status": "PASS__SF3_FULLSTAT_CHAIN_COMPLETE__TERMINAL_NO_SECOND_TOPUP", "ready": True, "errors": [], "missing": []})
        final = inspect_chain(root, manifest)
        if not final["complete"] or final["status"] != COMPLETE_STATUS:
            raise AssertionError(f"synthetic full-stat chain did not close: {final}")

        synthetic_guard_path = root / str(GUARD_EVENT_LOG.relative_to(PACKAGE_ROOT))
        synthetic_wal_path = root / str(GUARD_SESSION_WAL.relative_to(PACKAGE_ROOT))
        synthetic_resource_path = root / str(RESOURCE_EVENT_LOG.relative_to(PACKAGE_ROOT))
        for synthetic_log in (
            synthetic_guard_path, synthetic_wal_path, synthetic_resource_path,
        ):
            synthetic_log.unlink(missing_ok=True)
        for label in GUARDED_STEPS:
            start_byte = synthetic_guard_path.stat().st_size if synthetic_guard_path.is_file() else 0
            append_jsonl(synthetic_wal_path, {
                "schema_version": 1,
                "status": "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE",
                "at": "2026-08-16T00:00:00+00:00",
                "session_label": label,
                "service_unit": DEFAULT_SERVICE_UNIT,
                "guard_log_start_byte": start_byte,
                "followup_manifest_sha256": sha256_small(
                    root / "data/sf3_fullstat_followup_execution_manifest.json"
                ),
                "completion_authority": EXPECTED_STEP_METADATA[label][2],
                "disk_path": str(root.resolve()),
                "dynamic_disk_reserve_bytes": DISK_RESERVE,
                "stage_started": False,
                "SIM_opened_statted_discovered_or_hashed": False,
            })
            sample = {
                "at": "2026-08-16T00:00:01+00:00",
                "session_label": label, "unit": DEFAULT_SERVICE_UNIT,
                "unit_state": "active", "observed_quota_percent": 400,
                "quota_percent": 400, "quota_changed": False,
                "decision_reasons": ["hold"],
                "cgroup_pressure": {"some_avg10": 0.0, "full_avg10": 0.0},
                "mem_available_bytes": MEM_FLOOR + 1,
                "swap_free_bytes": SWAP_FLOOR + 1,
                "mem_floor_bytes": MEM_FLOOR,
                "swap_floor_bytes": SWAP_FLOOR,
                "disk_path": str(root.resolve()),
                "disk_free_bytes": DISK_RESERVE + 1,
                "disk_floor_bytes": DISK_RESERVE,
            }
            closure = {
                **sample,
                "at": "2026-08-16T00:00:02+00:00",
                "decision_reasons": ["guard_exit_restore_normal"],
            }
            append_jsonl(synthetic_guard_path, sample)
            append_jsonl(synthetic_guard_path, closure)
        recovered = reconcile_guarded_resource_events(root, manifest)
        recovered_rows = read_jsonl_objects(
            root / str(RESOURCE_EVENT_LOG.relative_to(PACKAGE_ROOT))
        )
        if (
            recovered != list(GUARDED_STEPS)
            or len(recovered_rows) != len(GUARDED_STEPS)
            or any(
                row.get("recovered_after_controller_crash") is not True
                or row.get("completion_authority_inferred_success") is not True
                or row.get("stage_returncode") is not None
                or int(row.get("disk_free_after_projection_bytes", 0)) < DISK_RESERVE
                for row in recovered_rows
            )
        ):
            raise AssertionError("write-ahead/guard-closure crash recovery did not restore five resource rows")

        topup_aggregate_fixture = load_json(root / TOPUP_AGGREGATE)
        mutated_topup_aggregate = json.loads(json.dumps(topup_aggregate_fixture))
        mutated_topup_aggregate["selected_receipts"][0]["receipt_sha256"] = "0" * 64
        fixture_json(root, TOPUP_AGGREGATE, mutated_topup_aggregate)
        if not topup_receipt_state(root)["errors"]:
            raise AssertionError("mutated canonical top-up receipt digest was accepted")
        fixture_json(root, TOPUP_AGGREGATE, topup_aggregate_fixture)

        delayed_aggregate_fixture = load_json(root / FULLSTAT_DELAYED_AGGREGATE)
        first_delayed_job = positive_ids[0]
        first_delayed_relative = f"{FULLSTAT_DELAYED_RECEIPT_ROOT}/{first_delayed_job}.json"
        first_delayed_receipt = load_json(root / first_delayed_relative)
        interrupted_receipt = json.loads(json.dumps(first_delayed_receipt))
        interrupted_receipt["attempt_dir"] = str(
            (root / "run_delayed/jobs" / first_delayed_job / "interrupted/attempt01").resolve()
        )
        fixture_json(root, first_delayed_relative, interrupted_receipt)
        mutated_delayed_aggregate = json.loads(json.dumps(delayed_aggregate_fixture))
        mutated_delayed_aggregate["selected_receipts"][0]["receipt_sha256"] = sha256_small(root / first_delayed_relative)
        fixture_json(root, FULLSTAT_DELAYED_AGGREGATE, mutated_delayed_aggregate)
        if not delayed_receipt_state(root)["errors"]:
            raise AssertionError("interrupted delayed attempt was accepted as canonical receipt")
        fixture_json(root, first_delayed_relative, first_delayed_receipt)
        fixture_json(root, FULLSTAT_DELAYED_AGGREGATE, delayed_aggregate_fixture)

        malformed = dict(load_json(root / PLAN1_MISSION))
        malformed["fullstat_gate"] = dict(malformed["fullstat_gate"], proxy_controls_gate=True)
        fixture_json(root, PLAN1_MISSION, malformed)
        if not inspect_chain(root, manifest)["status"].startswith("BLOCKED__"):
            raise AssertionError("proxy-controlled synthetic gate was accepted")
        ready_event = {
            "session_label": "transport_topup", "unit": DEFAULT_SERVICE_UNIT,
            "unit_state": "active", "observed_quota_percent": 400,
            "quota_percent": 400, "quota_changed": False,
            "decision_reasons": ["hold"],
            "cgroup_pressure": {"some_avg10": 0.0, "full_avg10": 0.0},
            "mem_available_bytes": MEM_FLOOR + 1,
            "swap_free_bytes": SWAP_FLOOR + 1,
            "mem_floor_bytes": MEM_FLOOR,
            "swap_floor_bytes": SWAP_FLOOR,
            "disk_path": str(PACKAGE_ROOT.resolve()),
            "disk_free_bytes": DISK_RESERVE + 1,
            "disk_floor_bytes": DISK_RESERVE,
        }
        if not guard_ready([ready_event], "transport_topup"):
            raise AssertionError("safe synthetic full-stat guard event was rejected")
        bad_event = dict(ready_event, decision_reasons=["SwapFree_hard_floor_breach"])
        try:
            guard_ready([bad_event], "transport_topup")
        except RuntimeError:
            pass
        else:
            raise AssertionError("hard-floor synthetic full-stat guard event was accepted")
        closure_event = {
            **ready_event,
            "decision_reasons": ["guard_exit_restore_normal"],
            "cgroup_pressure": None,
        }
        closed = validate_closed_guard_session(
            [ready_event, closure_event], "transport_topup", 0,
        )
        if closed["restored_quota_percent"] != 400:
            raise AssertionError("synthetic guard clean closure was rejected")
        try:
            validate_closed_guard_session(
                [ready_event, bad_event, closure_event], "transport_topup", 0,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("hard-floor race before guard exit was accepted")
        try:
            validate_closed_guard_session([ready_event], "transport_topup", 0)
        except RuntimeError:
            pass
        else:
            raise AssertionError("guard session without terminal clean closure was accepted")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_FOLLOWUP_ADAPTER_PURE_SYNTHETIC_SELF_TEST",
        "checks": [
            "waits_for_write_once_plan1_stage07",
            "central_ratio_only_false_branch_publishes_terminal_STOP_and_exits_complete",
            "proxy_never_controls_gate_negative_test",
            "mission_exact_PASS_and_nonnegative_central_ratio",
            "terminal_STOP_continues_to_forbid_fullstat_artifacts",
            "manifest_exact_preflight_and_step_descriptor_binding",
            "true_branch_exact_topup_prompt_activation_fresh250k_response_mission_resource_final_order",
            "28_topup_receipts_and_zero_A15_fresh250k_delayed_contract",
            "canonical_receipt_path_digest_payload_and_attempt_namespace_binding",
            "interrupted_attempt_never_counts_as_canonical_receipt",
            "activation_fixture_matches_producer_schema_without_events_or_transport_eligible",
            "five_cpu4_worker4_guarded_sessions",
            "hard_floor_guard_readiness_rejected",
            "hard_floor_race_and_missing_clean_guard_closure_rejected",
            "write_ahead_clean_guard_closure_recovers_post_authority_resource_row_crash_window",
            "locked_resource_schema_canonical_completion_WAL_digest_and_no_live_inference_binding",
            "canonical_authority_resume_and_write_once_conflict_policy",
            "canonical_partial_static_topup_files_resume_idempotently",
            "downstream_noncanonical_write_once_target_blocks_immediately",
            "Plan1_83334_never_read_or_merged",
        ],
        "production_authorities_accessed": False,
        "transport_or_analysis_launched": False,
        "SIM_opened_statted_discovered_or_hashed": False,
        "production_output_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--advance-one", action="store_true")
    actions.add_argument("--run-to-completion", action="store_true")
    actions.add_argument("--wait-and-run-to-completion", action="store_true")
    parser.add_argument("--service-unit", default=DEFAULT_SERVICE_UNIT)
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_WAIT_POLL_SECONDS)
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites:
            manifest = load_manifest()
            result = inspect_chain(PACKAGE_ROOT, manifest)
            result["manifest"]["sha256"] = sha256_small(MANIFEST_PATH)
        elif args.wait_and_run_to_completion:
            result = wait_and_advance(args.service_unit, args.poll_seconds)
        else:
            result = advance(args.run_to_completion, args.service_unit)
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready"):
            return 1 if result.get("errors") else 2
        return 0 if result.get("complete") or args.self_test else (1 if result.get("errors") else 2)
    except Exception as exc:
        print(json_text({"schema_version": 1, "profile_id": PROFILE_ID, "status": "FAIL__SF3_FULLSTAT_FOLLOWUP_ADAPTER", "error": str(exc), "SIM_opened_statted_discovered_or_hashed": False}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
