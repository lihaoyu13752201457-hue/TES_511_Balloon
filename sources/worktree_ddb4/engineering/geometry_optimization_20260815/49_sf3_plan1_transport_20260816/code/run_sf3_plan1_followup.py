#!/usr/bin/env python3
"""Crash-safe, authority-driven SF3 Plan-1 post-background sequencer.

The adapter starts no background work.  Once all 21 canonical background
receipts exist, it advances the frozen sequence one authority at a time:
receipt validation, prompt, activation/source preparation, guarded delayed
transport, delayed validation/analysis, guarded fresh SF3 signal, signal/all
receipt validation, common response, matched comparison, mission, compact
resource-session audit, and final audit.

Restart state is derived exclusively from canonical compact authorities.  The
append-only execution journal is operational evidence, never physics
authority.  Existing canonical receipts are passed back to the retained
runner, which skips them; interrupted/active attempts are never credited.
Read-only status and the pure synthetic self-test never open, stat, discover,
or hash a SIM payload.

``--wait-and-run-to-completion`` is the crash-resilient service entrypoint: it
holds the single-controller lock, emits a 30--60 second compact-authority
heartbeat while background is incomplete, then advances immediately at 21/21.
"""

from __future__ import annotations

import argparse
import contextlib
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
from typing import Any, Callable, Iterator, Sequence


HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parents[1]
CODE_ROOT = PACKAGE_ROOT / "code"
MANIFEST_PATH = PACKAGE_ROOT / "data/sf3_plan1_followup_execution_manifest.json"
CONFIG_PATH = PACKAGE_ROOT / "analysis_inputs.json"
PLAN_PATH = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
AUDIT_ROOT = PACKAGE_ROOT / "audit"
JOURNAL_PATH = AUDIT_ROOT / "sf3_plan1_followup_execution_journal.jsonl"
STATE_PATH = AUDIT_ROOT / "sf3_plan1_followup_state.json"
LOCK_PATH = AUDIT_ROOT / "sf3_plan1_followup_controller.lock"
GUARD_EVENT_LOG = AUDIT_ROOT / "sf3_plan1_followup_pressure_guard.jsonl"

PROFILE_ID = "SF3_PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN"
MANIFEST_STATUS = "PASS__SF3_PLAN1_CRASH_SAFE_FOLLOWUP_EXECUTION_MANIFEST_PREPARED"
COMPLETE_STATUS = "PASS__SF3_PLAN1_CRASH_SAFE_FOLLOWUP_COMPLETE"
DELAYED_EVENTS = 83_334
ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER = 3.6888794541139363
DEFAULT_SERVICE_UNIT = "sf3-plan1-followup.service"
DEFAULT_WAIT_POLL_SECONDS = 45.0
MAX_SMALL_JSON_BYTES = 32 * 1024**2
MAX_GUARD_EVENT_DELTA_BYTES = 1024 * 1024
ZERO_A15_EXCLUSION_REASON = (
    "ZERO_A15__NO_DELAYED_TRANSPORT__FINITE_UPPER_LIMIT_ONLY"
)
EXPECTED_STEP_IDS = (
    "await_background_transport",
    "validate_background_receipts",
    "build_prompt",
    "build_activation_and_delayed_sources",
    "transport_delayed",
    "validate_delayed_receipts",
    "analyze_delayed",
    "transport_signal",
    "validate_signal_receipt",
    "validate_all_receipts",
    "build_common_response",
    "build_matched_comparison",
    "build_mission",
    "build_resource_timeline",
    "finalize_plan1",
)

RESOURCE_TIMELINE_STATUS = (
    "PASS__SF3_RESOURCE_TIMELINE_ALL_EFFECTIVE_TRANSPORT_RECEIPTS_"
    "AND_RESOURCE_SESSIONS"
)

GUARDED_STEP_IDS = (
    "build_prompt",
    "transport_delayed",
    "analyze_delayed",
    "transport_signal",
    "build_common_response",
)

OUTPUT_STATUS = {
    "build_prompt": (
        "outputs/01_prompt", "PASS__SF3_PLAN1_PROMPT_COMPLETE", "summary.json", "manifest.json",
    ),
    "analyze_delayed": (
        "outputs/03_delayed",
        "PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "summary.json", "manifest.json",
    ),
    "build_common_response": (
        "outputs/04_common_response",
        "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
        "summary.json", "manifest.json",
    ),
    "build_matched_comparison": (
        "outputs/05_se3_vs_sf3_matched_comparison",
        "PASS__SF3_VS_FROZEN_SE3_DAY15_AND_FULL_ENVELOPE_COMPARISON",
        "summary.json", "manifest.json",
    ),
    "build_mission": (
        "outputs/06_mission",
        "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE",
        "summary.json", "manifest.json",
    ),
}

EXPECTED_COMMANDS = {
    "await_background_transport": [],
    "validate_background_receipts": [
        "{python}", "{code}/validate_sf3_receipts.py", "--stage", "background",
    ],
    "build_prompt": ["{python}", "{code}/run_prompt_analysis.py", "--workers", "4"],
    "build_activation_and_delayed_sources": [
        "{python}", "{code}/build_sf3_activation.py", "--prepare",
    ],
    "transport_delayed": [
        "{python}", "{code}/run_sf3_plan1.py", "--phase", "delayed", "--cpu-budget", "4",
    ],
    "validate_delayed_receipts": [
        "{python}", "{code}/validate_sf3_receipts.py", "--stage", "delayed",
    ],
    "analyze_delayed": [
        "{python}", "{code}/analyze_delayed_stage.py", "--workers", "4",
    ],
    "transport_signal": [
        "{python}", "{code}/run_sf3_plan1.py", "--phase", "signal", "--cpu-budget", "4",
    ],
    "validate_signal_receipt": [
        "{python}", "{code}/validate_sf3_receipts.py", "--stage", "signal",
    ],
    "validate_all_receipts": [
        "{python}", "{code}/validate_sf3_receipts.py", "--stage", "all",
    ],
    "build_common_response": [
        "{python}", "{code}/build_common_response.py", "--workers", "4",
    ],
    "build_matched_comparison": [
        "{python}", "{code}/build_matched_comparison.py", "--build",
    ],
    "build_mission": ["{python}", "{code}/build_mission_stage.py", "--build"],
    "build_resource_timeline": [
        "{python}", "{code}/build_sf3_resource_timeline.py", "--build",
    ],
    "finalize_plan1": ["{python}", "{code}/finalize_sf3_plan1.py", "--build"],
}

EXPECTED_PREFLIGHTS = {
    "build_prompt": ["{python}", "{code}/run_prompt_analysis.py", "--check-prerequisites"],
    "build_activation_and_delayed_sources": [
        "{python}", "{code}/build_sf3_activation.py", "--check-prerequisites",
    ],
    "analyze_delayed": [
        "{python}", "{code}/analyze_delayed_stage.py", "--check-prerequisites",
    ],
    "build_common_response": [
        "{python}", "{code}/build_common_response.py", "--check-prerequisites",
    ],
    "build_matched_comparison": [
        "{python}", "{code}/build_matched_comparison.py", "--check-prerequisites",
    ],
    "build_mission": [
        "{python}", "{code}/build_mission_stage.py", "--check-prerequisites",
    ],
    "build_resource_timeline": [
        "{python}", "{code}/build_sf3_resource_timeline.py", "--check-prerequisites",
    ],
    "finalize_plan1": [
        "{python}", "{code}/finalize_sf3_plan1.py", "--check-prerequisites",
    ],
}


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def sha256_small(path: Path, *, limit: int = MAX_SMALL_JSON_BYTES) -> str:
    size = path.stat().st_size
    if size <= 0 or size > limit:
        raise RuntimeError(f"small authority empty/oversized: {path} ({size})")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_small_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    sha256_small(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return load_small_json(path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    with temp.open("x", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def append_journal(payload: dict[str, Any]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_plan(root: Path) -> list[dict[str, str]]:
    path = root / "data/sf3_plan1_job_plan.csv"
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 30 or len({row.get("job_id") for row in rows}) != 30:
        raise RuntimeError("Plan-1 job plan is not exactly 30 unique registered rows")
    if sum(row.get("stage") == "background" for row in rows) != 21:
        raise RuntimeError("Plan-1 background row count is not 21")
    if sum(row.get("stage") == "delayed" for row in rows) != 8:
        raise RuntimeError("Plan-1 delayed registered-cell count is not 8")
    signal_rows = [row for row in rows if row.get("stage") == "signal"]
    if len(signal_rows) != 1 or signal_rows[0].get("job_id") != "signal_full_envelope_sf3":
        raise RuntimeError("Plan-1 signal row is not exactly fresh SF3")
    return rows


def validate_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if (
        payload.get("schema_version") != 1
        or payload.get("profile_id") != PROFILE_ID
        or payload.get("status") != MANIFEST_STATUS
        or payload.get("scope") != "POST_BACKGROUND_PLAN1_ONLY"
        or payload.get("required_service_unit") != DEFAULT_SERVICE_UNIT
    ):
        raise RuntimeError("followup execution manifest identity differs")
    steps = payload.get("steps")
    if not isinstance(steps, list) or tuple(row.get("id") for row in steps) != EXPECTED_STEP_IDS:
        raise RuntimeError("followup execution step order differs")
    ordinals = [int(row.get("ordinal", -1)) for row in steps]
    if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)):
        raise RuntimeError("followup step ordinals are not strictly ordered/unique")
    by_id = {row["id"]: row for row in steps}
    for step_id, expected in EXPECTED_COMMANDS.items():
        if by_id[step_id].get("command") != expected:
            raise RuntimeError(f"followup executable argv differs: {step_id}")
        if by_id[step_id].get("preflight") != EXPECTED_PREFLIGHTS.get(step_id):
            raise RuntimeError(f"followup preflight argv differs: {step_id}")
    if by_id["await_background_transport"].get("command") != []:
        raise RuntimeError("followup adapter is not allowed to launch background")
    for step_id in ("build_prompt", "analyze_delayed", "build_common_response"):
        command = by_id[step_id].get("command") or []
        if command[-2:] != ["--workers", "4"]:
            raise RuntimeError(f"analysis worker budget is not four: {step_id}")
    for step_id in ("transport_delayed", "transport_signal"):
        command = by_id[step_id].get("command") or []
        if command[-2:] != ["--cpu-budget", "4"]:
            raise RuntimeError(f"transport CPU budget is not four: {step_id}")
    for step_id in GUARDED_STEP_IDS:
        if (
            by_id[step_id].get("guard") is not True
            or by_id[step_id].get("kind") not in {
                "transport_with_pressure_guard", "analysis_with_pressure_guard",
            }
        ):
            raise RuntimeError(f"four-worker stage is not pressure-guarded: {step_id}")
    for step_id in (
        "build_activation_and_delayed_sources", "build_matched_comparison",
        "build_mission", "build_resource_timeline", "finalize_plan1",
    ):
        if by_id[step_id].get("guard") is not None:
            raise RuntimeError(f"small/nonparallel stage unexpectedly owns a pressure guard: {step_id}")
    policies = payload.get("policies") or {}
    guard = policies.get("pressure_guard") or {}
    handoff = policies.get("continuous_handoff") or {}
    if (
        int(policies.get("workers", -1)) != 4
        or guard.get("guarded_steps") != list(GUARDED_STEP_IDS)
        or int(guard.get("normal_quota_percent", -1)) != 400
        or int(guard.get("throttle_quota_percent", -1)) != 300
        or int(guard.get("mem_available_floor_bytes", -1)) != 1_610_612_736
        or int(guard.get("swap_free_floor_bytes", -1)) != 8 * 1024**3
        or guard.get("session_closure") != "GUARD_EXIT_RESTORE_NORMAL"
    ):
        raise RuntimeError("followup heavy-stage pressure-guard contract differs")
    if (
        handoff.get("entrypoint") != "--wait-and-run-to-completion"
        or int(handoff.get("default_heartbeat_seconds", -1)) != 45
        or handoff.get("allowed_heartbeat_seconds") != [30, 60]
        or handoff.get("wait_reads") != "NAMED_SMALL_AUTHORITIES_ONLY"
        or handoff.get("conflict_policy")
        != "AUTHORITY_OR_WRITE_ONCE_ERROR_FAILS_IMMEDIATELY"
    ):
        raise RuntimeError("followup continuous-handoff contract differs")
    for row in steps:
        for command_name in ("preflight", "command"):
            command = row.get(command_name) or []
            if not isinstance(command, list) or any(not isinstance(token, str) for token in command):
                raise RuntimeError(f"manifest argv is malformed: {row['id']}/{command_name}")
            if any(token in {"sh", "bash", "-c", "--phase=background"} for token in command):
                raise RuntimeError(f"manifest contains a shell/background escape: {row['id']}")
    return payload


def load_manifest() -> dict[str, Any]:
    return validate_manifest_payload(load_small_json(MANIFEST_PATH))


def state_result(
    complete: bool,
    *,
    details: dict[str, Any] | None = None,
    errors: Sequence[str] = (),
) -> dict[str, Any]:
    return {"complete": complete, "details": details or {}, "errors": list(errors)}


def current_validation_failure(
    validation: dict[str, Any] | None,
    aggregate: dict[str, Any] | None,
    label: str,
) -> list[str]:
    """Expose only a FAIL produced against the current receipt aggregate.

    Legacy/premature FAIL files predate the latest aggregate and are mutable
    operational snapshots, so they must not block the required revalidation.
    """
    if not validation or validation.get("status") != "FAIL" or not aggregate:
        return []
    validated_at = validation.get("validated_at")
    aggregate_at = aggregate.get("updated_at")
    if not validated_at or not aggregate_at:
        return []
    try:
        from datetime import datetime

        is_current = datetime.fromisoformat(str(validated_at)) >= datetime.fromisoformat(
            str(aggregate_at)
        )
    except ValueError:
        return [f"{label} FAIL/current-aggregate timestamps are invalid"]
    if not is_current:
        return []
    reported = validation.get("errors")
    count = len(reported) if isinstance(reported, list) else "unknown"
    return [f"{label} failed against the current receipt aggregate ({count} errors)"]


def aggregate_state(root: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    plan = load_plan(root)
    aggregate = optional_json(root / "audit/sf3_plan1_transport_receipts.json")
    return aggregate, plan


def activation_state(root: Path) -> tuple[dict[str, Any] | None, list[str], list[str], list[str]]:
    payload = optional_json(root / "audit/sf3_activation_validation.json")
    if payload is None:
        return None, [], [], []
    errors: list[str] = []
    if payload.get("status") != "PASS" or payload.get("semantic_status") != "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY":
        errors.append("activation validation status/semantic status differs")
    cards = payload.get("source_cards")
    if not isinstance(cards, list) or len(cards) != 8:
        errors.append("activation source-card registry is not eight cells")
        return payload, [], [], errors
    delayed_plan = [row for row in load_plan(root) if row.get("stage") == "delayed"]
    plan_by_family: dict[str, dict[str, str]] = {}
    for row in delayed_plan:
        family = str(row.get("family", ""))
        if not family or family in plan_by_family:
            errors.append(f"delayed plan family duplication/absence: {family!r}")
            continue
        plan_by_family[family] = row
    positive: list[str] = []
    zero: list[str] = []
    families: set[str] = set()
    for row in cards:
        if not isinstance(row, dict):
            errors.append("activation source-card row is not an object")
            continue
        family = str(row.get("family", ""))
        job_id = str(row.get("job_id", ""))
        if not family or family in families:
            errors.append(f"activation family duplication/absence: {family!r}")
        families.add(family)
        plan_row = plan_by_family.get(family)
        if plan_row is None:
            errors.append(f"activation family is absent from delayed plan: {family!r}")
            continue
        if job_id != str(plan_row.get("job_id", "")):
            errors.append(f"activation job identity differs from delayed plan: {family}/{job_id}")
        try:
            if int(row.get("seed", -1)) != int(plan_row.get("seed", -2)):
                errors.append(f"activation seed differs from delayed plan: {family}")
            if int(plan_row.get("events", -1)) != DELAYED_EVENTS:
                errors.append(f"delayed plan registered event count differs: {family}")
            if int(row.get("events", -1)) != DELAYED_EVENTS:
                errors.append(f"activation event count differs: {family}")
            if int(row.get("registered_events", -1)) != DELAYED_EVENTS:
                errors.append(f"activation registered event count differs: {family}")
        except (TypeError, ValueError):
            errors.append(f"activation seed/event binding is nonnumeric: {family}")
        disposition = row.get("execution_disposition")
        if disposition == "RUN_83334":
            if int(row.get("actual_transport_events", -1)) != DELAYED_EVENTS:
                errors.append(f"activation RUN_83334 event count differs: {family}")
            source_status = str(row.get("source_status", ""))
            try:
                activity = float(row.get("transported_ground_activity_Bq"))
            except (TypeError, ValueError):
                activity = math.nan
            if not source_status.startswith("PASS__") or not math.isfinite(activity) or activity <= 0.0:
                errors.append(f"activation positive status/activity differs: {family}")
            for field in (
                "zero_count_garwood_two_sided95_upper",
                "transported_ground_rate_upper95_s-1",
                "transported_ground_A15_upper95_Bq_conservative",
                "zero_A15_upper_provenance",
            ):
                if field not in row or row.get(field) is not None:
                    errors.append(f"activation positive publishes/misses zero-source upper field: {family}/{field}")
            positive.append(job_id)
        elif disposition == "SKIP_ZERO_A15":
            if int(row.get("actual_transport_events", -1)) != 0:
                errors.append(f"activation zero-A15 actual event count differs: {family}")
            source_status = str(row.get("source_status", ""))
            try:
                activity = float(row.get("transported_ground_activity_Bq"))
                sum_tt = float(row.get("buildup_sum_TT_s"))
                count_upper = float(row.get("zero_count_garwood_two_sided95_upper"))
                rate_upper = float(row.get("transported_ground_rate_upper95_s-1"))
                a15_upper = float(row.get("transported_ground_A15_upper95_Bq_conservative"))
            except (TypeError, ValueError):
                activity = sum_tt = count_upper = rate_upper = a15_upper = math.nan
            expected_rate = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt if math.isfinite(sum_tt) and sum_tt > 0.0 else math.nan
            if not source_status.startswith("ZERO_SOURCE__") or not math.isfinite(activity) or activity != 0.0:
                errors.append(f"activation zero-A15 status/activity differs: {family}")
            if not math.isfinite(sum_tt) or sum_tt <= 0.0:
                errors.append(f"activation zero-A15 buildup sumTT is not finite/positive: {family}")
            if not math.isclose(count_upper, ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER, rel_tol=0.0, abs_tol=1.0e-15):
                errors.append(f"activation zero-A15 Garwood count upper differs: {family}")
            if not math.isfinite(rate_upper) or rate_upper <= 0.0 or not math.isclose(
                rate_upper, expected_rate, rel_tol=2.0e-15, abs_tol=1.0e-18,
            ):
                errors.append(f"activation zero-A15 rate upper differs: {family}")
            if not math.isfinite(a15_upper) or not math.isclose(
                a15_upper, rate_upper, rel_tol=0.0, abs_tol=1.0e-18,
            ):
                errors.append(f"activation zero-A15 conservative A15 upper differs: {family}")
            if not str(row.get("zero_A15_upper_provenance", "")).strip():
                errors.append(f"activation zero-A15 upper provenance is empty: {family}")
            if row.get("upper_excludes_known_and_unresolved_holdout") is not True:
                errors.append(f"activation zero-A15 upper does not exclude holdout: {family}")
            zero.append(job_id)
        else:
            errors.append(f"activation disposition differs: {family}/{disposition}")
    if families != set(plan_by_family):
        errors.append("activation family set differs from the eight delayed plan cells")
    if len(set(positive + zero)) != len(positive) + len(zero):
        errors.append("activation delayed job identities are not unique")
    return payload, positive, zero, errors


def selected_receipt_ids(aggregate: dict[str, Any], stage: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    rows = aggregate.get("selected_receipts")
    if not isinstance(rows, list):
        return [], ["transport aggregate selected_receipts is not an array"]
    selected: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("transport aggregate receipt row is not an object")
            continue
        if row.get("stage") != stage:
            continue
        job_id = str(row.get("job_id", ""))
        if not job_id or job_id in selected:
            errors.append(f"duplicate/empty aggregate receipt identity: {job_id!r}")
        selected.append(job_id)
    return selected, errors


def output_pair_state(root: Path, step_id: str) -> dict[str, Any]:
    relative, expected, summary_name, manifest_name = OUTPUT_STATUS[step_id]
    output = root / relative
    summary_path = output / summary_name
    manifest_path = output / manifest_name
    if not summary_path.is_file() and not manifest_path.is_file():
        return state_result(False)
    try:
        summary = load_small_json(summary_path)
        manifest = load_small_json(manifest_path)
    except Exception as exc:
        return state_result(False, errors=[str(exc)])
    errors = []
    if summary.get("status") != expected:
        errors.append(f"{step_id} summary status differs: {summary.get('status')}")
    if manifest.get("status") != expected:
        errors.append(f"{step_id} manifest status differs: {manifest.get('status')}")
    return state_result(not errors, details={"status": expected}, errors=errors)


def completion_state(step_id: str, root: Path) -> dict[str, Any]:
    try:
        aggregate, plan = aggregate_state(root)
    except Exception as exc:
        return state_result(False, errors=[str(exc)])
    plan_ids = {
        stage: [str(row["job_id"]) for row in plan if row.get("stage") == stage]
        for stage in ("background", "delayed", "signal")
    }

    if step_id == "await_background_transport":
        if aggregate is None:
            return state_result(False, details={"validated": 0, "planned": 21})
        selected, errors = selected_receipt_ids(aggregate, "background")
        if set(selected) - set(plan_ids["background"]):
            errors.append("aggregate contains an unknown background receipt")
        complete = (
            not errors
            and int(aggregate.get("background_planned_jobs", -1)) == 21
            and int(aggregate.get("background_validated_jobs", -1)) == 21
            and set(selected) == set(plan_ids["background"])
        )
        return state_result(complete, details={"validated": len(selected), "planned": 21}, errors=errors)

    if step_id == "validate_background_receipts":
        validation = optional_json(root / "audit/sf3_plan1_background_receipt_validation.json")
        canonical = optional_json(root / "audit/sf3_plan1_statistics_validation.json")
        validation_errors = current_validation_failure(
            validation, aggregate, "background receipt validation",
        )
        complete = bool(
            validation
            and canonical
            and validation.get("status") == "PASS"
            and validation.get("scope") == "background"
            and int(validation.get("planned_jobs_in_scope", -1)) == 21
            and int(validation.get("validated_jobs_in_scope", -1)) == 21
            and validation.get("errors") == []
            and validation.get("canonical_statistics_publishable") is True
            and canonical.get("status") == "PASS"
            and canonical.get("scope") in ("background", "all")
        )
        return state_result(
            complete,
            details={
                "status": validation.get("status") if validation else None,
                "stale_premature_FAIL_is_not_authority": bool(
                    validation and validation.get("status") == "FAIL" and not validation_errors
                ),
            },
            errors=validation_errors,
        )

    if step_id in OUTPUT_STATUS:
        return output_pair_state(root, step_id)

    if step_id == "build_activation_and_delayed_sources":
        payload, positive, zero, errors = activation_state(root)
        summary = optional_json(root / "outputs/02_activation/day15_summary.json")
        manifest = optional_json(root / "outputs/02_activation/manifest.json")
        if summary and summary.get("status") != "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY":
            errors.append("activation day15 summary status differs")
        if manifest and manifest.get("status") != "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY":
            errors.append("activation manifest status differs")
        complete = payload is not None and summary is not None and manifest is not None and not errors
        return state_result(complete, details={"RUN_83334": positive, "SKIP_ZERO_A15": zero}, errors=errors)

    if step_id == "transport_delayed":
        activation, positive, zero, errors = activation_state(root)
        if activation is None:
            return state_result(False)
        if aggregate is None:
            return state_result(False, errors=errors)
        selected, aggregate_errors = selected_receipt_ids(aggregate, "delayed")
        errors.extend(aggregate_errors)
        raw_exclusions = aggregate.get("execution_exclusions")
        exclusions_are_an_object = isinstance(raw_exclusions, dict)
        exclusions = raw_exclusions if exclusions_are_an_object else {}
        if not exclusions_are_an_object:
            errors.append("transport aggregate execution_exclusions is not an object")
        exclusions_match = exclusions_are_an_object and set(exclusions) == set(zero) and not any(
            exclusions.get(job_id) != ZERO_A15_EXCLUSION_REASON for job_id in zero
        )
        pretransport_stale_background_aggregate = (
            exclusions_are_an_object and not selected and exclusions == {}
        )
        if not exclusions_match and not pretransport_stale_background_aggregate:
            errors.append("aggregate zero-A15 exclusion identities/reasons differ")
        complete = not errors and exclusions_match and set(selected) == set(positive)
        return state_result(complete, details={
            "validated_positive_receipts": len(selected), "planned_positive_receipts": len(positive),
            "zero_A15_skips": len(zero),
        }, errors=errors)

    if step_id == "validate_delayed_receipts":
        _activation, positive, zero, activation_errors = activation_state(root)
        validation = optional_json(root / "audit/sf3_plan1_delayed_receipt_validation.json")
        exclusions = (validation or {}).get("execution_exclusions") or {}
        complete = bool(
            not activation_errors
            and validation
            and validation.get("status") == "PASS"
            and validation.get("scope") == "delayed"
            and int(validation.get("planned_jobs_in_scope", -1)) == len(positive)
            and int(validation.get("validated_jobs_in_scope", -1)) == len(positive)
            and validation.get("errors") == []
            and set(exclusions) == set(zero)
            and all(
                exclusions.get(job_id) == ZERO_A15_EXCLUSION_REASON
                for job_id in zero
            )
        )
        return state_result(complete, details={"expected": len(positive)}, errors=activation_errors)

    if step_id == "transport_signal":
        if aggregate is None:
            return state_result(False)
        selected, errors = selected_receipt_ids(aggregate, "signal")
        complete = not errors and selected == ["signal_full_envelope_sf3"]
        return state_result(complete, details={"validated": len(selected), "planned": 1}, errors=errors)

    if step_id == "validate_signal_receipt":
        validation = optional_json(root / "audit/sf3_plan1_signal_receipt_validation.json")
        complete = bool(
            validation
            and validation.get("status") == "PASS"
            and validation.get("scope") == "signal"
            and int(validation.get("planned_jobs_in_scope", -1)) == 1
            and int(validation.get("validated_jobs_in_scope", -1)) == 1
            and validation.get("errors") == []
        )
        return state_result(complete)

    if step_id == "validate_all_receipts":
        _activation, positive, zero, activation_errors = activation_state(root)
        validation = optional_json(root / "audit/sf3_plan1_all_receipt_validation.json")
        expected = 21 + len(positive) + 1
        complete = bool(
            not activation_errors
            and validation
            and validation.get("status") == "PASS"
            and validation.get("scope") == "all"
            and int(validation.get("planned_jobs_in_scope", -1)) == expected
            and int(validation.get("validated_jobs_in_scope", -1)) == expected
            and validation.get("errors") == []
            and set((validation.get("execution_exclusions") or {})) == set(zero)
            and all(
                (validation.get("execution_exclusions") or {}).get(job_id)
                == ZERO_A15_EXCLUSION_REASON
                for job_id in zero
            )
            and validation.get("canonical_statistics_publishable") is True
        )
        return state_result(complete, details={"expected_effective_receipts": expected}, errors=activation_errors)

    if step_id == "build_resource_timeline":
        audit = optional_json(root / "audit/sf3_resource_timeline_audit.json")
        _activation, positive, _zero, activation_errors = activation_state(root)
        expected_jobs = 21 + len(positive) + 1
        expected_stages = {"background", "signal"}
        expected_label_stage = {
            "background_transport": "background",
            "transport_signal": "signal",
        }
        if positive:
            expected_stages.add("delayed")
            expected_label_stage["transport_delayed"] = "delayed"
        transport_receipts = (
            audit.get("transport_receipts") if isinstance(audit, dict) else {}
        ) or {}
        background_receipts = (
            audit.get("background_receipts") if isinstance(audit, dict) else {}
        ) or {}
        completion_resources = (
            audit.get("completion_resources") if isinstance(audit, dict) else {}
        ) or {}
        actual_execution = (
            audit.get("actual_execution") if isinstance(audit, dict) else {}
        ) or {}
        guard_sessions = actual_execution.get("guard_sessions") or {}
        complete = bool(
            not activation_errors
            and audit
            and audit.get("status") == RESOURCE_TIMELINE_STATUS
            and audit.get("ready") is True
            and audit.get("errors") == []
            and audit.get("missing") == []
            and audit.get("pending") == []
            and audit.get("sim_opened_statted_discovered_or_hashed") is False
            and audit.get("systemd_or_service_action_performed") is False
            and audit.get("transport_launched") is False
            and int(transport_receipts.get("validated_jobs", -1)) == expected_jobs
            and transport_receipts.get("all_canonical_PASS") is True
            and len(transport_receipts.get("receipt_records") or []) == expected_jobs
            and int(background_receipts.get("validated_jobs", -1)) == 21
            and background_receipts.get("all_canonical_PASS") is True
            and len(background_receipts.get("receipt_records") or []) == 21
            and int(completion_resources.get("validated_jobs", -1)) == expected_jobs
            and completion_resources.get("all_effective_jobs_present") is True
            and completion_resources.get("all_completion_rows_pass_dynamic_reserve") is True
            and len(completion_resources.get("records") or []) == expected_jobs
            and int(actual_execution.get("controller_workers", -1)) == 4
            and guard_sessions.get("all_sessions_closed") is True
            and guard_sessions.get("all_quotas_within_3_to_4_cores") is True
            and guard_sessions.get("all_throttled_sessions_restored_to_four") is True
            and guard_sessions.get("all_sampled_hard_floors_pass") is True
            and guard_sessions.get("safe_all_four_core_session_is_PASS") is True
            and guard_sessions.get("artificial_throttle_required") is False
            and set(guard_sessions.get("required_stage_coverage") or []) == expected_stages
            and set(guard_sessions.get("observed_closed_stage_coverage") or []) >= expected_stages
            and set(guard_sessions.get("required_followup_session_labels") or [])
            == set(GUARDED_STEP_IDS)
            and set(guard_sessions.get("observed_closed_followup_session_labels") or [])
            == set(GUARDED_STEP_IDS)
            and guard_sessions.get("required_exact_label_stage_coverage")
            == expected_label_stage
            and set((guard_sessions.get("observed_closed_exact_label_stage_coverage") or {}))
            == set(expected_label_stage)
            and all(
                set((guard_sessions.get("observed_closed_exact_label_stage_coverage") or {}).get(label) or [])
                == {stage}
                for label, stage in expected_label_stage.items()
            )
            and guard_sessions.get("all_required_exact_label_stage_bindings_pass") is True
        )
        return state_result(
            complete,
            details={
                "status": audit.get("status") if audit else None,
                "expected_effective_receipts": expected_jobs,
                "guarded_sessions": list(GUARDED_STEP_IDS),
            },
            errors=activation_errors,
        )

    if step_id == "finalize_plan1":
        audit = optional_json(root / "outputs/07_final_audit/final_audit.json")
        complete = bool(
            audit
            and audit.get("status") == "PASS__SF3_PLAN1_CHAIN_COMPLETE__CENTRAL_FULLSTAT_GATE_RECORDED"
            and audit.get("ready") is True
            and audit.get("errors") == []
            and audit.get("missing") == []
        )
        return state_result(complete)

    return state_result(False, errors=[f"unknown followup step: {step_id}"])


def safe_completion_state(step_id: str, root: Path) -> dict[str, Any]:
    try:
        return completion_state(step_id, root)
    except Exception as exc:
        return state_result(False, errors=[f"{step_id} authority inspection failed: {exc}"])


def inspect_chain(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    steps = manifest["steps"]
    states = [{"id": row["id"], **safe_completion_state(row["id"], root)} for row in steps]
    first_incomplete = next((index for index, row in enumerate(states) if not row["complete"]), None)
    errors: list[str] = []
    if first_incomplete is not None:
        for row in states[first_incomplete + 1:]:
            if row["complete"]:
                errors.append(f"out-of-order completed authority after gap: {row['id']}")
    if first_incomplete is not None:
        errors.extend(states[first_incomplete]["errors"])
        step = steps[first_incomplete]
        target_value = step.get("write_once_target")
        if target_value:
            target = root / str(target_value)
            recoverable = step.get("existing_target_policy") == "IDEMPOTENT_PREPARE_MAY_REPUBLISH_MISSING_SMALL_VALIDATION"
            if target.exists() and not recoverable:
                errors.append(f"existing noncanonical write-once target blocks restart: {target}")
    if errors:
        status = "BLOCKED__SF3_PLAN1_FOLLOWUP_AUTHORITY_OR_WRITE_ONCE_CONFLICT"
        ready = False
        next_step = steps[first_incomplete]["id"] if first_incomplete is not None else None
    elif first_incomplete is None:
        status = COMPLETE_STATUS
        ready = True
        next_step = None
    elif steps[first_incomplete]["kind"] == "wait":
        status = "NOT_READY__SF3_PLAN1_FOLLOWUP_WAITING_FOR_BACKGROUND"
        ready = False
        next_step = steps[first_incomplete]["id"]
    else:
        status = "READY__SF3_PLAN1_FOLLOWUP_NEXT_STEP"
        ready = True
        next_step = steps[first_incomplete]["id"]
    completed_prefix = [row["id"] for row in states[: first_incomplete if first_incomplete is not None else len(states)]]
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "complete": first_incomplete is None,
        "next_step": next_step,
        "completed_prefix": completed_prefix,
        "errors": errors,
        "step_states": states,
        "manifest": {
            "path": str(MANIFEST_PATH if root == PACKAGE_ROOT else root / "synthetic_manifest.json"),
            "status": manifest["status"],
        },
        "restart_policy": "RECOMPUTE_FROM_CANONICAL_SMALL_AUTHORITIES__NEVER_TRUST_JOURNAL_FOR_COMPLETION",
        "existing_receipt_policy": "SKIP_CANONICAL_PASS__NEVER_RERUN",
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__NAMED_SMALL_JSON_CSV_ONLY",
        "transport_or_analysis_launched": False,
    }


def expand_argv(raw: Sequence[str]) -> list[str]:
    replacements = {
        "{python}": sys.executable,
        "{code}": str(CODE_ROOT),
        "{package}": str(PACKAGE_ROOT),
    }
    expanded: list[str] = []
    for raw_token in raw:
        token = str(raw_token)
        for marker, replacement in replacements.items():
            token = token.replace(marker, replacement)
        if any(marker in token for marker in replacements):
            raise RuntimeError(f"unexpanded followup argv placeholder: {token}")
        expanded.append(token)
    return expanded


def parse_json_stdout(result: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f"{label} did not emit one JSON object: {exc}; stderr={result.stderr[-2000:]!r}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} JSON root is not an object")
    return payload


def run_preflight(raw: Sequence[str], step_id: str) -> dict[str, Any]:
    result = subprocess.run(
        expand_argv(raw), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    payload = parse_json_stdout(result, f"{step_id} preflight")
    if result.returncode != 0 or payload.get("ready") is not True:
        raise RuntimeError(json.dumps({
            "status": "NOT_READY__FOLLOWUP_STEP_PREFLIGHT",
            "step": step_id,
            "returncode": result.returncode,
            "preflight": payload,
        }, indent=2, sort_keys=True))
    return payload


def stale_active_attempts(root: Path) -> list[str]:
    config = load_small_json(root / "analysis_inputs.json")
    run_root = Path(str(config.get("run_root", "")))
    if not run_root.is_absolute():
        raise RuntimeError("configured Plan-1 run_root is not absolute")
    rows = load_plan(root)
    stale = []
    for row in rows:
        active = run_root / "jobs" / str(row["job_id"]) / "active"
        if active.exists():
            stale.append(str(active))
    return stale


def guard_events_since(initial_size: int) -> list[dict[str, Any]]:
    try:
        current_size = GUARD_EVENT_LOG.stat().st_size
    except FileNotFoundError:
        return []
    if current_size < initial_size:
        raise RuntimeError("pressure guard event log was truncated during startup")
    delta = current_size - initial_size
    if delta == 0:
        return []
    if delta > MAX_GUARD_EVENT_DELTA_BYTES:
        raise RuntimeError(f"pressure guard startup event delta is oversized: {delta}")
    with GUARD_EVENT_LOG.open("rb") as handle:
        handle.seek(initial_size)
        payload = handle.read(delta)
    complete_lines = payload.split(b"\n")
    if payload and not payload.endswith(b"\n"):
        complete_lines = complete_lines[:-1]
    events: list[dict[str, Any]] = []
    for raw in complete_lines:
        if not raw:
            continue
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"pressure guard emitted malformed JSONL: {exc}") from exc
        if not isinstance(event, dict):
            raise RuntimeError("pressure guard JSONL event is not an object")
        events.append(event)
    return events


def guard_readiness_from_events(events: Sequence[dict[str, Any]], step_id: str) -> bool:
    matching = [event for event in events if event.get("session_label") == step_id]
    if not matching:
        return False
    for event in matching:
        reasons = event.get("decision_reasons")
        if not isinstance(reasons, list) or any(not isinstance(item, str) for item in reasons):
            raise RuntimeError(f"pressure guard reasons are malformed for {step_id}")
        if any(reason.endswith("_hard_floor_breach") for reason in reasons):
            raise RuntimeError(
                f"pressure guard rejected startup at a hard resource floor: {step_id}: {reasons}"
            )
        if any(reason.startswith("guard_exit_restore_") for reason in reasons):
            raise RuntimeError(f"pressure guard exited before stage launch: {step_id}: {reasons}")
    event = matching[-1]
    if event.get("unit_state") not in ("active", "activating"):
        raise RuntimeError(
            f"pressure guard unit is not active at readiness: {step_id}: {event.get('unit_state')!r}"
        )
    try:
        quota = int(event.get("quota_percent"))
        mem = int(event.get("mem_available_bytes"))
        swap = int(event.get("swap_free_bytes"))
        mem_floor = int(event.get("mem_floor_bytes"))
        swap_floor = int(event.get("swap_floor_bytes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"pressure guard readiness sample is incomplete: {step_id}") from exc
    if quota not in (300, 400):
        raise RuntimeError(f"pressure guard readiness quota is outside 300/400: {step_id}/{quota}")
    if mem < mem_floor or swap < swap_floor:
        raise RuntimeError(f"pressure guard readiness sample breaches a hard floor: {step_id}")
    return True


def require_clean_guard_closure(events: Sequence[dict[str, Any]], step_id: str) -> None:
    matching = [event for event in events if event.get("session_label") == step_id]
    reasons = [
        reason
        for event in matching
        for reason in (event.get("decision_reasons") or [])
        if isinstance(reason, str)
    ]
    if any(reason.endswith("_hard_floor_breach") for reason in reasons):
        raise RuntimeError(f"guarded stage crossed a hard resource floor: {step_id}")
    if "guard_exit_restore_failed" in reasons:
        raise RuntimeError(f"pressure guard quota restoration failed: {step_id}")
    if reasons.count("guard_exit_restore_normal") != 1:
        raise RuntimeError(
            f"pressure guard session lacks one clean restoration closure: {step_id}"
        )


def wait_for_guard_event(
    guard: subprocess.Popen[Any], initial_size: int, step_id: str,
    timeout_s: float = 15.0,
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if guard.poll() is not None:
            raise RuntimeError(f"pressure guard exited before readiness event: rc={guard.returncode}")
        if guard_readiness_from_events(guard_events_since(initial_size), step_id):
            time.sleep(0.1)
            if guard.poll() is not None:
                raise RuntimeError(
                    f"pressure guard exited during readiness confirmation: {step_id}: rc={guard.returncode}"
                )
            return
        time.sleep(0.25)
    raise RuntimeError("pressure guard did not publish a readiness event within 15 seconds")


def terminate_process_group(process: subprocess.Popen[Any]) -> None:
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


def run_guarded_stage(raw: Sequence[str], unit: str, step_id: str) -> int:
    guard_script = CODE_ROOT / "guard_sf3_service_pressure.py"
    check = subprocess.run([
        sys.executable, str(guard_script), "--check-prerequisites", "--unit", unit,
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    live = parse_json_stdout(check, "pressure guard live check")
    if check.returncode != 0 or live.get("ready") is not True:
        raise RuntimeError(json.dumps(live, indent=2, sort_keys=True))
    initial_size = GUARD_EVENT_LOG.stat().st_size if GUARD_EVENT_LOG.is_file() else 0
    guard = subprocess.Popen([
        sys.executable, str(guard_script), "--unit", unit,
        "--event-log", str(GUARD_EVENT_LOG), "--normal-quota", "400",
        "--throttle-quota", "300", "--safe-samples", "6",
        "--session-label", step_id,
    ])
    transport: subprocess.Popen[Any] | None = None
    try:
        wait_for_guard_event(guard, initial_size, step_id)
        transport = subprocess.Popen(expand_argv(raw), start_new_session=True)
        while transport.poll() is None:
            if guard.poll() is not None:
                terminate_process_group(transport)
                raise RuntimeError(
                    "pressure guard exited while guarded stage was active: "
                    f"{step_id}: rc={guard.returncode}"
                )
            time.sleep(1.0)
        if guard.poll() is not None:
            raise RuntimeError(
                f"pressure guard exited before guarded stage completion was accepted: "
                f"{step_id}: rc={guard.returncode}"
            )
        return int(transport.returncode)
    finally:
        if transport is not None and transport.poll() is None:
            terminate_process_group(transport)
        if guard.poll() is None:
            guard.terminate()
            try:
                guard.wait(timeout=20)
            except subprocess.TimeoutExpired:
                guard.kill()
                guard.wait(timeout=10)
        restore = subprocess.run(
            [
                sys.executable, str(guard_script), "--restore-only", "--unit", unit,
                "--normal-quota", "400", "--throttle-quota", "300",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if restore.returncode != 0:
            raise RuntimeError(
                "pressure guard failed to restore the four-core quota: "
                f"stdout={restore.stdout[-1000:]!r} stderr={restore.stderr[-1000:]!r}"
            )
        require_clean_guard_closure(guard_events_since(initial_size), step_id)


def run_step(step: dict[str, Any], unit: str) -> None:
    step_id = str(step["id"])
    stale = stale_active_attempts(PACKAGE_ROOT)
    if step["kind"] in ("transport", "transport_with_pressure_guard") and stale:
        raise RuntimeError(json.dumps({
            "status": "BLOCKED__STALE_ACTIVE_ATTEMPT_REQUIRES_EXPLICIT_RECOVERY",
            "step": step_id,
            "stale_active_attempts": stale,
            "statistics_policy": "EXCLUDED__NEVER_CREDITED_OR_RERUN_IN_PLACE",
        }, indent=2, sort_keys=True))
    if step.get("preflight"):
        run_preflight(step["preflight"], step_id)
    command = step.get("command") or []
    if not command:
        raise RuntimeError(f"step has no executable command: {step_id}")
    event = {
        "at": utc_now(), "event": "step_start", "step": step_id,
        "argv": expand_argv(command), "journal_is_physics_authority": False,
    }
    append_journal(event)
    try:
        if step.get("guard") is True:
            returncode = run_guarded_stage(command, unit, step_id)
        else:
            returncode = subprocess.run(expand_argv(command), check=False).returncode
        if returncode != 0:
            raise RuntimeError(f"step command failed: {step_id}: rc={returncode}")
        completed = safe_completion_state(step_id, PACKAGE_ROOT)
        if not completed["complete"]:
            raise RuntimeError(json.dumps({
                "status": "FAIL__STEP_RETURNED_ZERO_WITHOUT_CANONICAL_COMPLETION_AUTHORITY",
                "step": step_id,
                "completion": completed,
            }, indent=2, sort_keys=True))
        append_journal({
            "at": utc_now(), "event": "step_complete", "step": step_id,
            "completion": completed["details"], "journal_is_physics_authority": False,
        })
    except BaseException as exc:
        append_journal({
            "at": utc_now(), "event": "step_failed", "step": step_id,
            "error": str(exc), "journal_is_physics_authority": False,
        })
        raise


def validate_service_unit(manifest: dict[str, Any], unit: str) -> None:
    if unit != manifest.get("required_service_unit"):
        raise RuntimeError(
            f"followup service unit must be exactly {manifest.get('required_service_unit')}: {unit}"
        )


@contextlib.contextmanager
def controller_lock() -> Iterator[None]:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another followup controller holds {LOCK_PATH}") from exc
        yield


def advance_locked(
    manifest: dict[str, Any], *, run_to_completion: bool, unit: str,
) -> dict[str, Any]:
    for _iteration in range(len(EXPECTED_STEP_IDS) + 1):
        status = inspect_chain(PACKAGE_ROOT, manifest)
        atomic_json(STATE_PATH, {**status, "updated_at": utc_now()})
        if status["complete"] or not status["ready"]:
            return status
        step = next(row for row in manifest["steps"] if row["id"] == status["next_step"])
        run_step(step, unit)
        if not run_to_completion:
            result = inspect_chain(PACKAGE_ROOT, manifest)
            atomic_json(STATE_PATH, {**result, "updated_at": utc_now()})
            return result
    raise RuntimeError("followup iteration bound exceeded")


def advance(*, run_to_completion: bool, unit: str) -> dict[str, Any]:
    manifest = load_manifest()
    validate_service_unit(manifest, unit)
    with controller_lock():
        return advance_locked(manifest, run_to_completion=run_to_completion, unit=unit)


def wait_for_runnable(
    status_provider: Callable[[], dict[str, Any]],
    heartbeat: Callable[[dict[str, Any]], None],
    sleeper: Callable[[float], None],
    *,
    poll_seconds: float,
) -> dict[str, Any]:
    """Wait on the background authority only, then hand off without a gap.

    Dependency errors and write-once conflicts are represented by ``errors``
    in the inspected chain and fail immediately.  ``sleeper`` is injectable so
    the synthetic self-test proves handoff without wall-clock waiting.
    """
    if not 30.0 <= poll_seconds <= 60.0:
        raise ValueError("wait heartbeat/poll seconds must be within 30..60")
    while True:
        status = status_provider()
        heartbeat(status)
        if status.get("errors"):
            raise RuntimeError(json.dumps({
                "status": "BLOCKED__SF3_PLAN1_WAIT_HANDOFF_AUTHORITY_CONFLICT",
                "next_step": status.get("next_step"),
                "errors": status["errors"],
            }, indent=2, sort_keys=True))
        if status.get("complete") or status.get("ready"):
            return status
        if (
            status.get("status") != "NOT_READY__SF3_PLAN1_FOLLOWUP_WAITING_FOR_BACKGROUND"
            or status.get("next_step") != "await_background_transport"
        ):
            raise RuntimeError(json.dumps({
                "status": "BLOCKED__SF3_PLAN1_WAIT_HANDOFF_UNEXPECTED_NOT_READY_STATE",
                "inspection": status,
            }, indent=2, sort_keys=True))
        sleeper(poll_seconds)


def publish_wait_heartbeat(status: dict[str, Any]) -> None:
    observed = utc_now()
    state = {**status, "updated_at": observed, "wait_mode": True}
    atomic_json(STATE_PATH, state)
    event = {
        "at": observed,
        "event": "wait_heartbeat",
        "status": status.get("status"),
        "next_step": status.get("next_step"),
        "background": (status.get("step_states") or [{}])[0].get("details", {}),
        "journal_is_physics_authority": False,
    }
    append_journal(event)
    print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)


def wait_and_advance(*, unit: str, poll_seconds: float) -> dict[str, Any]:
    manifest = load_manifest()
    validate_service_unit(manifest, unit)
    with controller_lock():
        handoff = wait_for_runnable(
            lambda: inspect_chain(PACKAGE_ROOT, manifest),
            publish_wait_heartbeat,
            time.sleep,
            poll_seconds=poll_seconds,
        )
        if handoff["complete"]:
            return handoff
        return advance_locked(manifest, run_to_completion=True, unit=unit)


def fixture_manifest() -> dict[str, Any]:
    # The versioned manifest is static adapter input, not a production result.
    return validate_manifest_payload(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))


def write_fixture_plan(root: Path) -> tuple[list[str], list[str], str]:
    path = root / "data/sf3_plan1_job_plan.csv"
    path.parent.mkdir(parents=True)
    fields = ("job_id", "stage", "family", "events", "seed")
    background = [f"bg_{index:02d}" for index in range(21)]
    delayed = [f"delayed_{index:02d}" for index in range(8)]
    signal_id = "signal_full_envelope_sf3"
    rows = [
        *({"job_id": job_id, "stage": "background", "family": f"f{index}", "events": "1", "seed": str(100 + index)} for index, job_id in enumerate(background)),
        *({"job_id": job_id, "stage": "delayed", "family": f"f{index}", "events": str(DELAYED_EVENTS), "seed": str(1_000 + index)} for index, job_id in enumerate(delayed)),
        {"job_id": signal_id, "stage": "signal", "family": "focused_gamma", "events": "37194", "seed": "2000"},
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return background, delayed, signal_id


def fixture_write_json(root: Path, relative: str, payload: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def fixture_pair(root: Path, relative: str, status: str) -> None:
    fixture_write_json(root, f"{relative}/summary.json", {"status": status})
    fixture_write_json(root, f"{relative}/manifest.json", {"status": status})


def self_test() -> dict[str, Any]:
    manifest = fixture_manifest()
    if expand_argv(["{code}/probe.py"]) != [str(CODE_ROOT / "probe.py")]:
        raise AssertionError("embedded {code}/... argv expansion failed")
    for step in manifest["steps"]:
        for argv_name in ("preflight", "command"):
            raw_argv = step.get(argv_name) or []
            expanded_argv = expand_argv(raw_argv)
            if any("{" in token or "}" in token for token in expanded_argv):
                raise AssertionError(
                    f"manifest argv retains a placeholder: {step['id']}/{argv_name}"
                )
    with tempfile.TemporaryDirectory(prefix="sf3_followup_selftest_", dir="/tmp") as temp:
        root = Path(temp)
        background, delayed, signal_id = write_fixture_plan(root)
        initial = inspect_chain(root, manifest)
        if initial["status"] != "NOT_READY__SF3_PLAN1_FOLLOWUP_WAITING_FOR_BACKGROUND":
            raise AssertionError("synthetic empty chain did not wait for background")
        ready_guard_event = {
            "session_label": "build_prompt",
            "unit_state": "active",
            "quota_percent": 400,
            "decision_reasons": ["hold"],
            "mem_available_bytes": 4 * 1024**3,
            "swap_free_bytes": 10 * 1024**3,
            "mem_floor_bytes": 1_610_612_736,
            "swap_floor_bytes": 8 * 1024**3,
        }
        if not guard_readiness_from_events([ready_guard_event], "build_prompt"):
            raise AssertionError("synthetic safe guard event was not launch-ready")
        hard_floor_event = dict(ready_guard_event)
        hard_floor_event.update({
            "decision_reasons": ["MemAvailable_hard_floor_breach"],
            "mem_available_bytes": 1_610_612_735,
        })
        try:
            guard_readiness_from_events([hard_floor_event], "build_prompt")
        except RuntimeError as exc:
            if "hard resource floor" not in str(exc):
                raise
        else:
            raise AssertionError("synthetic hard-floor guard event allowed stage launch")
        closure_event = dict(ready_guard_event)
        closure_event["decision_reasons"] = ["guard_exit_restore_normal"]
        try:
            guard_readiness_from_events([closure_event], "build_prompt")
        except RuntimeError as exc:
            if "exited before stage launch" not in str(exc):
                raise
        else:
            raise AssertionError("synthetic guard closure event allowed stage launch")
        require_clean_guard_closure([ready_guard_event, closure_event], "build_prompt")
        failed_closure = dict(closure_event)
        failed_closure["decision_reasons"] = ["guard_exit_restore_failed"]
        try:
            require_clean_guard_closure(
                [ready_guard_event, failed_closure], "build_prompt",
            )
        except RuntimeError as exc:
            if "restoration failed" not in str(exc):
                raise
        else:
            raise AssertionError("synthetic failed guard restoration was accepted")

        selected_background = [{"job_id": job_id, "stage": "background"} for job_id in background]
        fixture_write_json(root, "audit/sf3_plan1_transport_receipts.json", {
            "updated_at": "2026-08-16T00:00:00+00:00",
            "background_planned_jobs": 21,
            "background_validated_jobs": 21,
            "selected_receipts": selected_background,
            "execution_exclusions": {},
        })
        background_ready = inspect_chain(root, manifest)
        if background_ready["next_step"] != "validate_background_receipts":
            raise AssertionError("synthetic background completion did not select validation")
        wait_states = [initial, background_ready]
        cursor = [0]
        sleeps: list[float] = []
        heartbeats: list[str] = []

        def synthetic_status_provider() -> dict[str, Any]:
            return wait_states[cursor[0]]

        def synthetic_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            cursor[0] += 1

        handoff = wait_for_runnable(
            synthetic_status_provider,
            lambda status: heartbeats.append(str(status["status"])),
            synthetic_sleep,
            poll_seconds=45.0,
        )
        if (
            handoff["next_step"] != "validate_background_receipts"
            or sleeps != [45.0]
            or len(heartbeats) != 2
        ):
            raise AssertionError("synthetic wait mode did not hand off automatically at 21/21")
        blocked_wait = dict(initial)
        blocked_wait.update({"status": "BLOCKED__SYNTHETIC", "errors": ["write-once conflict"]})
        try:
            wait_for_runnable(
                lambda: blocked_wait,
                lambda _status: None,
                lambda _seconds: (_ for _ in ()).throw(
                    AssertionError("blocked wait slept instead of failing immediately")
                ),
                poll_seconds=45.0,
            )
        except RuntimeError as exc:
            if "write-once conflict" not in str(exc):
                raise
        else:
            raise AssertionError("synthetic wait mode ignored an authority conflict")
        fixture_write_json(root, "audit/sf3_plan1_background_receipt_validation.json", {
            "status": "FAIL", "scope": "background", "planned_jobs_in_scope": 21,
            "validated_jobs_in_scope": 1, "errors": ["premature"],
        })
        premature = inspect_chain(root, manifest)
        if premature["next_step"] != "validate_background_receipts" or premature["errors"]:
            raise AssertionError("premature mutable background FAIL incorrectly blocked recovery")
        fixture_write_json(root, "audit/sf3_plan1_background_receipt_validation.json", {
            "validated_at": "2026-08-16T00:00:01+00:00",
            "status": "FAIL", "scope": "background", "planned_jobs_in_scope": 21,
            "validated_jobs_in_scope": 21, "errors": ["synthetic current failure"],
            "canonical_statistics_action": "NOT_PUBLISHED__EXISTING_AUTHORITY_PRESERVED",
        })
        current_failure = inspect_chain(root, manifest)
        if not current_failure["status"].startswith("BLOCKED__") or not current_failure["errors"]:
            raise AssertionError("current complete-background validation FAIL did not block")
        complete_background_validation = {
            "status": "PASS", "scope": "background", "planned_jobs_in_scope": 21,
            "validated_jobs_in_scope": 21, "errors": [],
            "canonical_statistics_publishable": True,
        }
        fixture_write_json(root, "audit/sf3_plan1_background_receipt_validation.json", complete_background_validation)
        fixture_write_json(root, "audit/sf3_plan1_statistics_validation.json", complete_background_validation)

        invalid_prompt = root / "outputs/01_prompt"
        invalid_prompt.mkdir(parents=True)
        conflict = inspect_chain(root, manifest)
        if not conflict["status"].startswith("BLOCKED__"):
            raise AssertionError("synthetic noncanonical write-once prompt target did not block")
        shutil.rmtree(invalid_prompt)
        fixture_pair(root, "outputs/01_prompt", "PASS__SF3_PLAN1_PROMPT_COMPLETE")

        positive = delayed[:-1]
        zero = delayed[-1:]
        cards = []
        for index, job_id in enumerate(delayed):
            is_positive = job_id in positive
            sum_tt = 10.0
            rate_upper = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt
            cards.append({
                "family": f"f{index}", "job_id": job_id,
                "seed": 1_000 + index,
                "events": DELAYED_EVENTS,
                "registered_events": DELAYED_EVENTS,
                "execution_disposition": "RUN_83334" if is_positive else "SKIP_ZERO_A15",
                "actual_transport_events": DELAYED_EVENTS if is_positive else 0,
                "source_status": "PASS__SYNTHETIC" if is_positive else "ZERO_SOURCE__SYNTHETIC",
                "transported_ground_activity_Bq": 1.0 if is_positive else 0.0,
                "buildup_sum_TT_s": sum_tt,
                "zero_count_garwood_two_sided95_upper": None if is_positive else ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER,
                "transported_ground_rate_upper95_s-1": None if is_positive else rate_upper,
                "transported_ground_A15_upper95_Bq_conservative": None if is_positive else rate_upper,
                "zero_A15_upper_provenance": None if is_positive else "synthetic finite-upper provenance",
                "upper_excludes_known_and_unresolved_holdout": True,
            })
        fixture_write_json(root, "audit/sf3_activation_validation.json", {
            "status": "PASS",
            "semantic_status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
            "source_cards": cards,
        })
        fixture_write_json(root, "outputs/02_activation/day15_summary.json", {
            "status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
        })
        fixture_write_json(root, "outputs/02_activation/manifest.json", {
            "status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
        })
        bad_cards = [dict(row) for row in cards]
        bad_cards[-1]["transported_ground_rate_upper95_s-1"] = 1.0
        fixture_write_json(root, "audit/sf3_activation_validation.json", {
            "status": "PASS",
            "semantic_status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
            "source_cards": bad_cards,
        })
        if not activation_state(root)[3]:
            raise AssertionError("synthetic invalid zero-source finite upper was accepted")
        bad_cards = [dict(row) for row in cards]
        bad_cards[0]["seed"] += 1
        fixture_write_json(root, "audit/sf3_activation_validation.json", {
            "status": "PASS",
            "semantic_status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
            "source_cards": bad_cards,
        })
        if not activation_state(root)[3]:
            raise AssertionError("synthetic activation seed mismatch was accepted")
        fixture_write_json(root, "audit/sf3_activation_validation.json", {
            "status": "PASS",
            "semantic_status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
            "source_cards": cards,
        })
        delayed_ready = inspect_chain(root, manifest)
        if (
            delayed_ready["next_step"] != "transport_delayed"
            or delayed_ready["ready"] is not True
            or delayed_ready["errors"] != []
        ):
            raise AssertionError("synthetic activation did not select guarded delayed transport")
        fixture_write_json(root, "audit/sf3_plan1_transport_receipts.json", {
            "updated_at": "2026-08-16T00:00:02+00:00",
            "background_planned_jobs": 21,
            "background_validated_jobs": 21,
            "selected_receipts": selected_background,
            "execution_exclusions": {
                "delayed_unknown": ZERO_A15_EXCLUSION_REASON,
            },
        })
        wrong_nonempty_exclusion = inspect_chain(root, manifest)
        if (
            not wrong_nonempty_exclusion["status"].startswith("BLOCKED__")
            or wrong_nonempty_exclusion["next_step"] != "transport_delayed"
            or not wrong_nonempty_exclusion["errors"]
        ):
            raise AssertionError("synthetic wrong nonempty delayed exclusion was accepted")
        fixture_write_json(root, "audit/sf3_plan1_transport_receipts.json", {
            "updated_at": "2026-08-16T00:00:03+00:00",
            "background_planned_jobs": 21,
            "background_validated_jobs": 21,
            "selected_receipts": selected_background,
            "execution_exclusions": {},
        })

        selected_all = [
            *selected_background,
            *({"job_id": job_id, "stage": "delayed"} for job_id in positive),
        ]
        fixture_write_json(root, "audit/sf3_plan1_transport_receipts.json", {
            "background_planned_jobs": 21,
            "background_validated_jobs": 21,
            "selected_receipts": selected_all,
            "execution_exclusions": {zero[0]: ZERO_A15_EXCLUSION_REASON},
        })
        fixture_write_json(root, "audit/sf3_plan1_delayed_receipt_validation.json", {
            "status": "PASS", "scope": "delayed", "planned_jobs_in_scope": 7,
            "validated_jobs_in_scope": 7, "errors": [],
            "execution_exclusions": {zero[0]: ZERO_A15_EXCLUSION_REASON},
        })
        fixture_pair(
            root, "outputs/03_delayed",
            "PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        )
        selected_all.append({"job_id": signal_id, "stage": "signal"})
        fixture_write_json(root, "audit/sf3_plan1_transport_receipts.json", {
            "background_planned_jobs": 21,
            "background_validated_jobs": 21,
            "selected_receipts": selected_all,
            "execution_exclusions": {zero[0]: ZERO_A15_EXCLUSION_REASON},
        })
        fixture_write_json(root, "audit/sf3_plan1_signal_receipt_validation.json", {
            "status": "PASS", "scope": "signal", "planned_jobs_in_scope": 1,
            "validated_jobs_in_scope": 1, "errors": [],
        })
        fixture_write_json(root, "audit/sf3_plan1_all_receipt_validation.json", {
            "status": "PASS", "scope": "all", "planned_jobs_in_scope": 29,
            "validated_jobs_in_scope": 29, "errors": [],
            "execution_exclusions": {zero[0]: ZERO_A15_EXCLUSION_REASON},
            "canonical_statistics_publishable": True,
        })
        fixture_pair(
            root, "outputs/04_common_response",
            "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
        )
        fixture_pair(
            root, "outputs/05_se3_vs_sf3_matched_comparison",
            "PASS__SF3_VS_FROZEN_SE3_DAY15_AND_FULL_ENVELOPE_COMPARISON",
        )
        mission_status = "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE"
        fixture_write_json(root, "outputs/06_mission/summary.json", {
            "status": mission_status,
        })
        missing_manifest = output_pair_state(root, "build_mission")
        if missing_manifest["complete"] or not missing_manifest["errors"]:
            raise AssertionError("stage06 summary without producer manifest was accepted")
        fixture_write_json(root, "outputs/06_mission/manifest.json", {
            "status": "PASS__WRONG_STAGE06_STATUS",
        })
        wrong_manifest = output_pair_state(root, "build_mission")
        if wrong_manifest["complete"] or not wrong_manifest["errors"]:
            raise AssertionError("stage06 producer manifest with wrong status was accepted")
        fixture_write_json(root, "outputs/06_mission/manifest.json", {
            "status": mission_status,
        })
        accepted_manifest = output_pair_state(root, "build_mission")
        if not accepted_manifest["complete"] or accepted_manifest["errors"]:
            raise AssertionError("canonical stage06 producer manifest was rejected")
        timeline_ready = inspect_chain(root, manifest)
        if timeline_ready["next_step"] != "build_resource_timeline":
            raise AssertionError("synthetic mission did not select resource-session audit")
        synthetic_effective_receipts = [
            {"job_id": f"effective_{index:02d}"} for index in range(29)
        ]
        synthetic_background_receipts = [
            {"job_id": f"background_{index:02d}"} for index in range(21)
        ]
        fixture_write_json(root, "audit/sf3_resource_timeline_audit.json", {
            "status": RESOURCE_TIMELINE_STATUS,
            "ready": True,
            "errors": [],
            "missing": [],
            "pending": [],
            "sim_opened_statted_discovered_or_hashed": False,
            "systemd_or_service_action_performed": False,
            "transport_launched": False,
            "transport_receipts": {
                "validated_jobs": 29,
                "all_canonical_PASS": True,
                "receipt_records": synthetic_effective_receipts,
            },
            "background_receipts": {
                "validated_jobs": 21,
                "all_canonical_PASS": True,
                "receipt_records": synthetic_background_receipts,
            },
            "completion_resources": {
                "validated_jobs": 29,
                "all_effective_jobs_present": True,
                "all_completion_rows_pass_dynamic_reserve": True,
                "records": synthetic_effective_receipts,
            },
            "actual_execution": {
                "controller_workers": 4,
                "guard_sessions": {
                    "all_sessions_closed": True,
                    "all_quotas_within_3_to_4_cores": True,
                    "all_throttled_sessions_restored_to_four": True,
                    "all_sampled_hard_floors_pass": True,
                    "safe_all_four_core_session_is_PASS": True,
                    "artificial_throttle_required": False,
                    "required_stage_coverage": ["background", "delayed", "signal"],
                    "observed_closed_stage_coverage": ["background", "delayed", "signal"],
                    "required_followup_session_labels": list(GUARDED_STEP_IDS),
                    "observed_closed_followup_session_labels": list(GUARDED_STEP_IDS),
                    "required_exact_label_stage_coverage": {
                        "background_transport": "background",
                        "transport_delayed": "delayed",
                        "transport_signal": "signal",
                    },
                    "observed_closed_exact_label_stage_coverage": {
                        "background_transport": ["background"],
                        "transport_delayed": ["delayed"],
                        "transport_signal": ["signal"],
                    },
                    "all_required_exact_label_stage_bindings_pass": True,
                },
            },
        })
        fixture_write_json(root, "outputs/07_final_audit/final_audit.json", {
            "status": "PASS__SF3_PLAN1_CHAIN_COMPLETE__CENTRAL_FULLSTAT_GATE_RECORDED",
            "ready": True, "errors": [], "missing": [],
        })
        final = inspect_chain(root, manifest)
        if final["status"] != COMPLETE_STATUS or not final["complete"]:
            raise AssertionError(f"synthetic completed chain did not close: {final}")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_PLAN1_FOLLOWUP_ADAPTER_PURE_SYNTHETIC_SELF_TEST",
        "checks": [
            "background_is_wait_only_and_never_launched",
            "guard_readiness_and_clean_closure_reject_hard_floor_or_early_failed_exit",
            "wait_mode_45s_heartbeat_hands_off_automatically_at_21_of_21",
            "wait_mode_authority_or_write_once_conflict_fails_without_sleep",
            "premature_mutable_background_FAIL_can_be_revalidated",
            "current_background_validation_FAIL_blocks_immediately",
            "each_step_requires_complete_previous_authority_prefix",
            "noncanonical_existing_write_once_target_blocks",
            "activation_to_guarded_delayed_cpu4",
            "activation_exact_family_job_seed_registered_event_and_zero_upper_binding",
            "pretransport_empty_exclusions_ready_but_wrong_nonempty_exclusion_blocks",
            "prompt_delayed_analysis_and_common_workers4_are_pressure_guarded",
            "fresh_signal_transport_is_independently_guarded_at_cpu4",
            "canonical_receipt_set_resumes_without_rerunning_existing_receipts",
            "delayed_validation_then_analysis_then_signal_then_signal_all_validation",
            "common_comparison_mission_resource_timeline_finalizer_exact_order",
            "stage06_producer_manifest_required_status_matched_and_accepted",
            "journal_is_never_completion_or_physics_authority",
            "manifest_workers4_and_all_five_heavy_sessions_quota_400_to_300_to_400",
        ],
        "production_authorities_accessed": False,
        "transport_or_analysis_launched": False,
        "SIM_opened_statted_discovered_or_hashed": False,
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
    parser.add_argument(
        "--poll-seconds", type=float, default=DEFAULT_WAIT_POLL_SECONDS,
        help="wait-mode small-authority heartbeat interval; constrained to 30..60 seconds",
    )
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        manifest = load_manifest()
        result = inspect_chain(PACKAGE_ROOT, manifest)
        result["manifest"]["sha256"] = sha256_small(MANIFEST_PATH)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["complete"] or result["ready"]:
            return 0
        return 1 if result["errors"] else 2
    try:
        if args.wait_and_run_to_completion:
            result = wait_and_advance(
                unit=args.service_unit, poll_seconds=args.poll_seconds,
            )
        else:
            result = advance(run_to_completion=args.run_to_completion, unit=args.service_unit)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["complete"]:
            return 0
        return 2 if not result["errors"] else 1
    except Exception as exc:
        print(json.dumps({
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "FAIL__SF3_PLAN1_FOLLOWUP_ADAPTER",
            "error": str(exc),
            "existing_receipt_policy": "SKIP_CANONICAL_PASS__NEVER_RERUN",
            "SIM_adapter_access_policy": "NO_SIM_SCAN_OR_HASH",
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
