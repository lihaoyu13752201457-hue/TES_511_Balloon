#!/usr/bin/env python3
"""Build the response-neutral SF3 full-stat delayed raw catalog.

The adapter consumes only the full-stat activation source index and canonical
fresh-250k delayed receipts.  Positive-A15 cells must have one complete
250,000-trigger transport; exact-zero cells are registered, skipped, and keep
their finite upper-limit provenance.  Plan-1's 83,334-trigger products are
never read, credited, or pooled.

``--check-prerequisites`` reads compact authorities and receipt metadata only;
it never opens, stats, or hashes a SIM.  Production reuses the retained raw
parser, exact parent-position KD-tree lineage, exact three-W diagnostics, and
the disjoint three-BGO plus three-plastic bookkeeping.  Each selected new SIM
is semantically read once by the retained scanner.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import shutil
from pathlib import Path
from typing import Any

import analyze_delayed_stage as raw
import build_sf3_fullstat_activation as activation_builder
import run_prompt_analysis as prompt
import run_sf3_fullstat_delayed as transport_runner
from sf3_plan1_common import FAMILIES, FULLSTAT_DELAYED_EVENTS, PACKAGE_ROOT, SF3_SETUP, sha256, utc_now


HERE = Path(__file__).resolve()
POLICY_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
OUTPUT_ROOT = PACKAGE_ROOT / "outputs/fullstat/03_delayed"
SOURCE_INDEX = activation_builder.SOURCE_INDEX
JOB_PLAN = activation_builder.DELAYED_JOB_PLAN
SEED_REGISTRY = activation_builder.DELAYED_SEED_REGISTRY
ACTIVATION_VALIDATION = activation_builder.ACTIVATION_VALIDATION
DELAYED_AGGREGATE = activation_builder.FULLSTAT_DELAYED_AGGREGATE
RECEIPT_ROOT = activation_builder.FULLSTAT_DELAYED_RECEIPT_ROOT
RUN_ROOT = activation_builder.FULLSTAT_DELAYED_RUN_ROOT
MISSION_SUMMARY = activation_builder.MISSION_SUMMARY

PROFILE_ID = activation_builder.FULLSTAT_DELAYED_NAMESPACE
RUN_DISPOSITION = activation_builder.POSITIVE_DISPOSITION
ZERO_DISPOSITION = activation_builder.ZERO_DISPOSITION
PLAN1_DELAYED_ROLE = activation_builder.PLAN1_DELAYED_ROLE
PASS_STATUS = "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE"
READY_STATUS = "READY__SF3_FULLSTAT_DELAYED_RAW_ANALYSIS"
NOT_READY_STATUS = "NOT_READY__SF3_FULLSTAT_DELAYED_RAW_ANALYSIS_PREREQUISITES"
FAMILY_ORDER = tuple(FAMILIES)
EXPECTED_REGISTERED_CELLS = len(FAMILY_ORDER)
EXPECTED_EVENTS = int(FULLSTAT_DELAYED_EVENTS)
MAX_WORKERS = 6
DEFAULT_WORKERS = 4
SMALL_AUTHORITY_MAX_BYTES = 20_000_000
ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER = activation_builder.base.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER

_RAW_SCAN_JOB = raw.scan_job


def lexical_absolute_path(value: str | Path) -> Path:
    """Normalize a declared path without resolving/statting its final target."""
    return Path(os.path.abspath(os.path.normpath(os.fspath(value))))


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise FileNotFoundError(f"missing named JSON {label}: {path}")
    payload_bytes = path.read_bytes()
    if not payload_bytes or len(payload_bytes) > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"{label} is empty or oversized: {path} ({len(payload_bytes)} bytes)")
    value = json.loads(payload_bytes)
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} root must be an object: {path}")
    return value


def read_small_csv(path: Path, label: str) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"missing/empty named CSV {label}: {path}")
    if path.stat().st_size > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"{label} is oversized: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"missing CSV header for {label}: {path}")
        return list(reader)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_workers(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_WORKERS:
        raise RuntimeError("full-stat delayed analyzer workers must be in 1..6")
    return value


def configure_raw_contract() -> None:
    """Bind the retained scanner to this full-stat namespace in this process."""
    raw.PROFILE_ID = PROFILE_ID
    raw.EXPECTED_EVENTS_PER_JOB = EXPECTED_EVENTS
    raw.EXPECTED_TOTAL_EVENTS = EXPECTED_REGISTERED_CELLS * EXPECTED_EVENTS
    raw.RUN_DISPOSITION = RUN_DISPOSITION
    raw.ZERO_DISPOSITION = ZERO_DISPOSITION
    raw.HERE = HERE


def scan_job_fullstat(job: dict[str, Any], cache_dir: str) -> dict[str, Any]:
    """Process-pool entry point which rebinds globals before the retained scan."""
    configure_raw_contract()
    return _RAW_SCAN_JOB(job, cache_dir)


def veto_policy() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        config = load_small_json(POLICY_CONFIG, "SF3 policy config")
        policy = prompt.explicit_veto_policy(config)
        shield = list(policy["shield_volumes"])
        plastic = list(policy["plastic_volumes"])
        active = list(policy["active_veto_volumes"])
        passive_w = list(policy["passive_w_volumes"])
        if len(shield) != 3 or len(plastic) != 3 or len(active) != 6:
            errors.append("full-stat delayed policy is not exactly 3 BGO + 3 plastic active volumes")
        if set(shield).intersection(plastic) or set(shield).union(plastic) != set(active):
            errors.append("BGO/plastic policies are not a disjoint partition of six active veto volumes")
        if tuple(passive_w) != tuple(prompt.PASSIVE_W_VOLUMES):
            errors.append("exact three passive-W volume list differs")
        if set(passive_w).intersection(active):
            errors.append("passive W overlaps an active BGO/plastic veto volume")
        if policy.get("apply_plastic_veto") is not True:
            errors.append("plastic veto policy is not enabled for downstream stage04")
        return policy, errors
    except Exception as exc:
        return {}, [f"invalid fixed SF3 veto policy: {exc}"]


def source_rows_by_family(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("geometry") != "SF3":
            raise RuntimeError("full-stat source index contains a non-SF3 row")
        family = row.get("incident_family", "")
        if family not in FAMILY_ORDER or family in selected:
            raise RuntimeError(f"invalid/duplicate full-stat source-index family: {family!r}")
        selected[family] = row
    if tuple(selected) != FAMILY_ORDER:
        raise RuntimeError(f"full-stat source-index order/set differs: {tuple(selected)}")
    return selected


def optional_float(row: dict[str, str], key: str) -> float | None:
    value = str(row.get(key, "")).strip()
    return float(value) if value else None


def normalize_source_row(
    family: str,
    row: dict[str, str],
    plan_row: dict[str, Any],
    *,
    check_compact_files: bool,
) -> tuple[list[str], dict[str, Any] | None]:
    """Validate the builder's source-index semantics without touching a SIM."""
    errors: list[str] = []
    try:
        disposition = str(row["execution_disposition"])
        activity = float(row["transported_ground_activity_Bq"])
        registered = int(row["registered_decay_triggers"])
        actual = int(row["actual_transport_triggers"])
        eligible = str(row["transport_eligible"]).lower() == "true"
        original_blocks = int(row["original_blocks"])
        transport_blocks = int(row["transport_blocks"])
        stride = int(row["position_stride"])
        original_flux = float(row.get("original_block_flux_Bq") or 0.0)
        transport_flux = float(row.get("transport_block_flux_Bq") or 0.0)
        original_total = float(row["original_total_Bq"])
        transport_total = float(row["transport_total_Bq"])
        original_closure = float(row["original_closure_Bq"])
        transport_closure = float(row["transport_closure_Bq"])
        buildup_sum_tt = float(row["buildup_sum_TT_s"])
        sampling_seed = int(row["sampling_seed"])
        transport_seed = int(row["transport_seed"])
        known_holdout = float(row.get("known_holdout_activity_Bq") or 0.0)
        unknown_holdout = int(row.get("unknown_activity_state_count") or 0)
        source = lexical_absolute_path(row["source_path"])
        positions = lexical_absolute_path(row["sampled_positions_path"])
        source_manifest = lexical_absolute_path(row["source_manifest_path"])
    except Exception as exc:
        return [f"{family} full-stat source-index row is unreadable: {exc}"], None

    expected_source = lexical_absolute_path(plan_row["source_path"])
    if row.get("incident_family") != family or row.get("job_id") != plan_row["job_id"]:
        errors.append(f"{family} source-index identity differs from delayed plan")
    if row.get("source_status") != plan_row["source_status"]:
        errors.append(f"{family} source status differs from delayed plan")
    if disposition != plan_row["execution_disposition"]:
        errors.append(f"{family} execution disposition differs from delayed plan")
    if registered != EXPECTED_EVENTS or registered != int(plan_row["registered_events"]):
        errors.append(f"{family} registered delayed triggers are not 250000")
    if actual != int(plan_row["actual_transport_events"]) or actual != int(plan_row["events"]):
        errors.append(f"{family} actual transport triggers differ from delayed plan")
    if eligible != bool(plan_row["transport_eligible"]):
        errors.append(f"{family} transport eligibility differs from delayed plan")
    if sampling_seed != int(plan_row["sampling_seed"]) or transport_seed != int(plan_row["seed"]):
        errors.append(f"{family} source-index seed binding differs")
    if source != expected_source:
        errors.append(f"{family} source-index card path differs from delayed plan")
    if not math.isfinite(buildup_sum_tt) or buildup_sum_tt <= 0.0:
        errors.append(f"{family} buildup sumTT is not positive finite")
    if known_holdout < 0.0 or unknown_holdout < 0:
        errors.append(f"{family} holdout bookkeeping is invalid")
    if str(row.get("plan1_83334_role", "")) != PLAN1_DELAYED_ROLE:
        errors.append(f"{family} Plan-1 screening-only role differs")
    if str(row.get("incremental_merge_allowed", "")).lower() != "false":
        errors.append(f"{family} forbidden incremental delayed merge is enabled")

    rate_upper = optional_float(row, "transported_ground_rate_upper95_s-1")
    a15_upper = optional_float(row, "transported_ground_A15_upper95_Bq_conservative")
    count_upper = optional_float(row, "zero_count_garwood_two_sided95_upper")
    upper_provenance = str(row.get("zero_A15_upper_provenance", "")).strip()
    if disposition == RUN_DISPOSITION:
        if (
            not eligible
            or actual != EXPECTED_EVENTS
            or not math.isfinite(activity)
            or activity <= 0.0
            or original_blocks != raw.FULL_POSITION_BLOCKS
            or transport_blocks != raw.SELECTED_POSITION_BLOCKS
            or stride != raw.POSITION_STRIDE
        ):
            errors.append(f"{family} positive source is not complete fresh250k/50k-to-10k")
        if any(value is not None for value in (count_upper, rate_upper, a15_upper)) or upper_provenance:
            errors.append(f"{family} positive source publishes zero-source upper fields")
    elif disposition == ZERO_DISPOSITION:
        expected_upper = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / buildup_sum_tt
        if eligible or actual != 0 or activity != 0.0 or original_blocks != 0 or transport_blocks != 0:
            errors.append(f"{family} zero source is not an exact transport skip")
        if (
            count_upper is None
            or rate_upper is None
            or a15_upper is None
            or not math.isclose(count_upper, ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER, rel_tol=0.0, abs_tol=1e-15)
            or not math.isclose(rate_upper, expected_upper, rel_tol=2e-12, abs_tol=1e-18)
            or not math.isclose(a15_upper, rate_upper, rel_tol=0.0, abs_tol=1e-18)
            or not upper_provenance
        ):
            errors.append(f"{family} zero source finite upper/provenance differs")
    else:
        errors.append(f"{family} unknown delayed disposition: {disposition}")

    for label, value, expected in (
        ("original_total", original_total, activity),
        ("transport_total", transport_total, activity),
        ("original_flux_total", original_flux * original_blocks, activity),
        ("transport_flux_total", transport_flux * transport_blocks, activity),
    ):
        if not math.isclose(value, expected, rel_tol=2e-12, abs_tol=1e-12):
            errors.append(f"{family} source mixture {label} does not close to A15")
    if not math.isclose(original_closure, original_total - activity, rel_tol=0.0, abs_tol=1e-12):
        errors.append(f"{family} original source closure residual differs")
    if not math.isclose(transport_closure, transport_total - activity, rel_tol=0.0, abs_tol=1e-12):
        errors.append(f"{family} transport source closure residual differs")

    if check_compact_files:
        for label, path in (
            ("transport source", source),
            ("sampled positions", positions),
            ("source manifest", source_manifest),
        ):
            if not path.is_file() or path.stat().st_size <= 0:
                errors.append(f"{family} {label} is missing/empty: {path}")
        if source.is_file() and sha256(source) != row.get("source_sha256"):
            errors.append(f"{family} source-card digest differs from activation index")
        if source_manifest.is_file():
            try:
                manifest = load_small_json(source_manifest, f"{family} source manifest")
                if (
                    manifest.get("job_id") != plan_row["job_id"]
                    or manifest.get("family") != family
                    or manifest.get("execution_disposition") != disposition
                    or int(manifest.get("registered_triggers", -1)) != EXPECTED_EVENTS
                    or int(manifest.get("actual_transport_triggers", -1)) != actual
                    or lexical_absolute_path(manifest.get("source", "")) != source
                    or lexical_absolute_path(manifest.get("sampled_positions_table", "")) != positions
                ):
                    errors.append(f"{family} source-manifest identity differs")
            except Exception as exc:
                errors.append(f"{family} source manifest is unreadable: {exc}")

    return errors, {
        "family": family,
        "source_status": row.get("source_status"),
        "execution_disposition": disposition,
        "transport_eligible": eligible,
        "activity_Bq": activity,
        "buildup_sum_TT_s": buildup_sum_tt,
        "zero_count_garwood_two_sided95_upper": count_upper,
        "transported_ground_rate_upper95_s-1": rate_upper,
        "transported_ground_A15_upper95_Bq_conservative": a15_upper,
        "zero_A15_upper_provenance": upper_provenance or None,
        "upper_excludes_known_and_unresolved_holdout": (
            str(row.get("upper_excludes_known_and_unresolved_holdout", "")).lower() == "true"
        ),
        "known_holdout_activity_Bq": known_holdout,
        "unknown_activity_state_count": unknown_holdout,
        "included_state_count": int(row.get("included_state_count") or 0),
        "holdout_state_count": int(row.get("holdout_state_count") or 0),
        "RPIP_points": int(row.get("RPIP_points") or 0),
        "original_position_blocks": original_blocks,
        "transport_position_blocks": transport_blocks,
        "position_stride": stride,
        "requested_decay_triggers": registered,
        "sampling_seed": sampling_seed,
        "flux_per_point_Bq": transport_flux,
        "original_block_flux_Bq": original_flux,
        "transport_block_flux_Bq": transport_flux,
        "original_total_Bq": original_total,
        "transport_total_Bq": transport_total,
        "original_closure_Bq": original_closure,
        "transport_closure_Bq": transport_closure,
        "sampled_positions_path": str(positions),
        "source_manifest_path": str(source_manifest),
        "transport_source_path": str(source),
    }


def receipt_metadata_errors(
    receipt: dict[str, Any], plan_row: dict[str, Any], source: dict[str, Any]
) -> list[str]:
    """Validate a canonical receipt without probing its declared SIM path."""
    errors = transport_runner.receipt_contract_errors(receipt, plan_row)
    job_id = str(plan_row["job_id"])
    if receipt.get("status") != "PASS" or receipt.get("errors") not in (None, []):
        errors.append("receipt is not a clean PASS")
    attempt = receipt.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= 2:
        errors.append("attempt ordinal is not 1..2")
        attempt = 0
    expected_attempt = lexical_absolute_path(
        RUN_ROOT / "jobs" / job_id / "attempts" / f"attempt{attempt:02d}"
    )
    if lexical_absolute_path(receipt.get("attempt_dir", "")) != expected_attempt:
        errors.append("receipt attempt directory escapes the full-stat PASS namespace")
    expected_sim = lexical_absolute_path(expected_attempt / f"{job_id}.inc1.id1.sim.gz")
    declared_sim = lexical_absolute_path(receipt.get("sim_path", ""))
    if declared_sim != expected_sim:
        errors.append("receipt SIM path escapes its full-stat PASS attempt")
    sim_bytes = receipt.get("sim_bytes")
    if isinstance(sim_bytes, bool) or not isinstance(sim_bytes, int) or sim_bytes <= 0:
        errors.append("receipt declares no positive SIM byte count")
    if lexical_absolute_path(receipt.get("source_path", "")) != lexical_absolute_path(
        plan_row["source_path"]
    ):
        errors.append("receipt source path differs from full-stat plan")
    if receipt.get("source_sha256") != source.get("source_sha256"):
        errors.append("receipt/source-index source digest differs")
    log = receipt.get("log") or {}
    if log.get("generated_events") != EXPECTED_EVENTS or log.get("graphics_terminal_marker") is not True:
        errors.append("receipt generated-event/terminal marker differs")
    if "83334" in str(declared_sim) or "166666" in str(declared_sim):
        errors.append("screening/incremental delayed namespace leaked into receipt SIM path")
    return errors


def check_prerequisites() -> dict[str, Any]:
    """Validate fixed compact inputs; never open, stat, or hash a SIM."""
    missing: list[str] = []
    errors: list[str] = []
    authorities: dict[str, Any] = {}
    validated_sources: dict[str, dict[str, Any]] = {}
    validated_receipts: list[dict[str, Any]] = []
    plan: list[dict[str, Any]] = []
    policy, policy_errors = veto_policy()
    errors.extend(policy_errors)
    if not prompt.OLD_CATALOG_PARSER.is_file():
        missing.append(str(prompt.OLD_CATALOG_PARSER))

    required = (
        MISSION_SUMMARY,
        ACTIVATION_VALIDATION,
        JOB_PLAN,
        SEED_REGISTRY,
        SOURCE_INDEX,
        DELAYED_AGGREGATE,
    )
    for path in required:
        if not path.is_file():
            missing.append(str(path))

    gate: dict[str, Any] | None = None
    activation: dict[str, Any] | None = None
    if MISSION_SUMMARY.is_file():
        try:
            gate = transport_runner.validate_gate_authority()
            authorities["central_gate"] = gate
        except Exception as exc:
            errors.append(f"central full-stat gate validation failed: {exc}")
    if JOB_PLAN.is_file() and SEED_REGISTRY.is_file():
        try:
            plan = transport_runner.load_plan_unbound()
            seeds = transport_runner.load_seed_registry(plan)
            authorities["job_plan"] = {"path": str(JOB_PLAN), "sha256": sha256(JOB_PLAN), "rows": len(plan)}
            authorities["seed_registry"] = {
                "path": str(SEED_REGISTRY), "sha256": sha256(SEED_REGISTRY), "rows": len(seeds)
            }
        except Exception as exc:
            errors.append(f"full-stat delayed plan/seed validation failed: {exc}")
            plan = []
    if gate is not None and ACTIVATION_VALIDATION.is_file():
        try:
            validation = load_small_json(ACTIVATION_VALIDATION, "full-stat activation validation")
            activation = transport_runner.validate_activation_structure(validation, gate)
            if plan:
                plan = transport_runner.bind_activation_to_plan(plan, activation)
            authorities["activation_validation"] = {
                "path": str(ACTIVATION_VALIDATION),
                "sha256": sha256(ACTIVATION_VALIDATION),
                "status": validation.get("status"),
            }
        except Exception as exc:
            errors.append(f"full-stat activation validation failed: {exc}")
            plan = []

    source_rows: dict[str, dict[str, str]] = {}
    if plan and SOURCE_INDEX.is_file():
        try:
            source_rows = source_rows_by_family(read_small_csv(SOURCE_INDEX, "full-stat source index"))
            plan_by_family = {str(row["family"]): row for row in plan}
            for family in FAMILY_ORDER:
                row_errors, normalized = normalize_source_row(
                    family, source_rows[family], plan_by_family[family], check_compact_files=True
                )
                errors.extend(row_errors)
                if normalized is not None:
                    normalized["source_sha256"] = source_rows[family].get("source_sha256")
                    validated_sources[family] = normalized
            authorities["source_index"] = {
                "path": str(SOURCE_INDEX), "sha256": sha256(SOURCE_INDEX), "rows": len(source_rows)
            }
        except Exception as exc:
            errors.append(f"full-stat activation source index failed: {exc}")

    aggregate: dict[str, Any] | None = None
    aggregate_by_id: dict[str, dict[str, Any]] = {}
    if DELAYED_AGGREGATE.is_file():
        try:
            aggregate = load_small_json(DELAYED_AGGREGATE, "full-stat delayed aggregate")
            if (
                aggregate.get("status") != transport_runner.FULLSTAT_COMPLETE_STATUS
                or aggregate.get("profile_id") != PROFILE_ID
                or aggregate.get("registered_families") != EXPECTED_REGISTERED_CELLS
                or aggregate.get("fresh_triggers_per_positive_family") != EXPECTED_EVENTS
                or aggregate.get("plan1_83334_read") is not False
                or aggregate.get("plan1_83334_pooled") is not False
                or aggregate.get("incremental_merge_used") is not False
                or lexical_absolute_path(aggregate.get("run_root", "")) != lexical_absolute_path(RUN_ROOT)
                or lexical_absolute_path(aggregate.get("receipt_root", "")) != lexical_absolute_path(RECEIPT_ROOT)
            ):
                raise RuntimeError("full-stat delayed aggregate identity/status differs")
            selected = aggregate.get("selected_receipts")
            if not isinstance(selected, list):
                raise RuntimeError("full-stat delayed aggregate selected_receipts is not a list")
            aggregate_by_id = {str(row["job_id"]): row for row in selected}
            if len(aggregate_by_id) != len(selected):
                raise RuntimeError("duplicate receipt in full-stat delayed aggregate")
            authorities["delayed_aggregate"] = {
                "path": str(DELAYED_AGGREGATE), "sha256": sha256(DELAYED_AGGREGATE),
                "status": aggregate.get("status"),
            }
        except Exception as exc:
            errors.append(f"full-stat delayed aggregate validation failed: {exc}")
            aggregate = None

    missing_receipts: list[str] = []
    if plan and validated_sources:
        for row in plan:
            family = str(row["family"])
            source = validated_sources.get(family)
            if source is None:
                continue
            rpath = lexical_absolute_path(row["receipt_path"])
            if row["execution_disposition"] == ZERO_DISPOSITION:
                if rpath.is_file():
                    errors.append(f"zero-A15 cell has a forbidden transport receipt: {rpath}")
                continue
            if not rpath.is_file():
                missing_receipts.append(str(row["job_id"]))
                continue
            try:
                receipt = load_small_json(rpath, f"full-stat delayed receipt {row['job_id']}")
                receipt_errors = receipt_metadata_errors(receipt, row, source)
                errors.extend(f"{row['job_id']}: {message}" for message in receipt_errors)
                aggregate_row = aggregate_by_id.get(str(row["job_id"]))
                if aggregate_row is None:
                    errors.append(f"aggregate omits full-stat delayed receipt: {row['job_id']}")
                elif (
                    aggregate_row.get("receipt_path") != str(rpath)
                    or aggregate_row.get("events") != EXPECTED_EVENTS
                    or aggregate_row.get("actual_transport_events") != EXPECTED_EVENTS
                    or lexical_absolute_path(aggregate_row.get("sim_path", ""))
                    != lexical_absolute_path(receipt.get("sim_path", ""))
                ):
                    errors.append(f"aggregate/receipt binding differs: {row['job_id']}")
                validated_receipts.append({
                    "job_id": row["job_id"],
                    "family": family,
                    "events": EXPECTED_EVENTS,
                    "seed": row["seed"],
                    "receipt_path": str(rpath),
                    "sim_path": str(lexical_absolute_path(receipt.get("sim_path", ""))),
                    "sim_bytes": receipt.get("sim_bytes"),
                    "source_sha256": receipt.get("source_sha256"),
                })
            except Exception as exc:
                errors.append(f"full-stat delayed receipt unreadable {row['job_id']}: {exc}")

    positive_count = sum(row.get("execution_disposition") == RUN_DISPOSITION for row in plan)
    zero_count = sum(row.get("execution_disposition") == ZERO_DISPOSITION for row in plan)
    ready = (
        not missing
        and not missing_receipts
        and not errors
        and len(plan) == EXPECTED_REGISTERED_CELLS
        and len(validated_sources) == EXPECTED_REGISTERED_CELLS
        and len(validated_receipts) == positive_count
        and positive_count + zero_count == EXPECTED_REGISTERED_CELLS
        and aggregate is not None
    )
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": READY_STATUS if ready else NOT_READY_STATUS,
        "ready": ready,
        "checked_at": utc_now(),
        "fixed_inputs": {
            "activation_source_index": str(SOURCE_INDEX),
            "job_plan": str(JOB_PLAN),
            "activation_validation": str(ACTIVATION_VALIDATION),
            "receipt_root": str(RECEIPT_ROOT),
            "aggregate": str(DELAYED_AGGREGATE),
            "output": str(OUTPUT_ROOT),
        },
        "registered_source_cells": len(plan),
        "positive_fresh250k_jobs": positive_count,
        "zero_A15_skips": zero_count,
        "validated_source_cells": len(validated_sources),
        "validated_receipts": len(validated_receipts),
        "validated_receipt_triggers": sum(row["events"] for row in validated_receipts),
        "authorities": authorities,
        "veto_policy": policy,
        "missing_inputs": sorted(set(missing)),
        "missing_receipts": missing_receipts,
        "errors": errors,
        "selected_receipts": validated_receipts,
        "zero_source_cells": [
            validated_sources[family]
            for family in FAMILY_ORDER
            if family in validated_sources
            and validated_sources[family]["execution_disposition"] == ZERO_DISPOSITION
        ],
        "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__RECEIPT_METADATA_ONLY",
        "plan1_83334_read": False,
        "plan1_83334_pooled": False,
        "analysis_produced": False,
    }


def selected_delayed_jobs(
    _config_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prerequisites = check_prerequisites()
    if not prerequisites["ready"]:
        raise RuntimeError(json.dumps(prerequisites, indent=2, sort_keys=True))
    config = load_small_json(POLICY_CONFIG, "SF3 policy config")
    policy = prompt.explicit_veto_policy(config)
    plan = transport_runner.load_plan_unbound()
    index = source_rows_by_family(read_small_csv(SOURCE_INDEX, "full-stat source index"))
    jobs: list[dict[str, Any]] = []
    zero_sources: list[dict[str, Any]] = []
    for scan_index, plan_row in enumerate(plan):
        family = str(plan_row["family"])
        source_errors, source = normalize_source_row(
            family, index[family], plan_row, check_compact_files=True
        )
        if source_errors or source is None:
            raise RuntimeError(f"{family} full-stat source binding failed: {source_errors}")
        common = {
            **plan_row,
            **source,
            "scan_index": scan_index,
            "batch_id": PROFILE_ID,
            "geometry": "SF3",
            "mode": "delayed",
            "activation_source_index_path": str(SOURCE_INDEX),
        }
        if plan_row["execution_disposition"] == ZERO_DISPOSITION:
            zero_sources.append({
                **common,
                "input_id": "sf3_fullstat_zero_A15_no_transport_receipt",
                "actual_transport_triggers": 0,
                "event_weight_cps": 0.0,
                "equivalent_time_s": None,
            })
            continue
        receipt_path = lexical_absolute_path(plan_row["receipt_path"])
        receipt = load_small_json(receipt_path, f"full-stat delayed receipt {plan_row['job_id']}")
        jobs.append({
            **common,
            "input_id": "sf3_fullstat_delayed_fresh250k_canonical_receipt",
            "sim_path": str(lexical_absolute_path(receipt["sim_path"])),
            "receipt_path": str(receipt_path),
            "receipt_sim_bytes": int(receipt["sim_bytes"]),
            "expected_geometry": str(lexical_absolute_path(plan_row["setup_path"])),
            "shield_volumes": list(policy["shield_volumes"]),
            "plastic_volumes": list(policy["plastic_volumes"]),
            "passive_w_volumes": list(policy["passive_w_volumes"]),
            "veto_policy": policy,
            "event_weight_cps": float(source["activity_Bq"]) / EXPECTED_EVENTS,
            "equivalent_time_s": EXPECTED_EVENTS / float(source["activity_Bq"]),
        })
    return config, jobs, zero_sources, prerequisites


def rewrite_csv_columns(path: Path, renames: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or ())
        rows = list(reader)
    if not fields:
        raise RuntimeError(f"missing generated CSV header: {path}")
    new_fields = [renames.get(field, field) for field in fields]
    rewritten = [
        {renames.get(key, key): value for key, value in row.items()}
        for row in rows
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=new_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rewritten)


def fullstat_report(summary: dict[str, Any]) -> str:
    scan = summary["semantic_scan"]
    return (
        "# SF3 full-stat delayed raw catalog\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Eight source cells are registered: {summary['transport_jobs']} positive families use one "
        f"fresh {EXPECTED_EVENTS:,}-trigger transport each, while {summary['skipped_zero_A15_jobs']} "
        "exact-zero families are skipped with their finite upper-limit provenance retained.\n\n"
        f"The retained one-pass scanner resolved exact-position parent lineage for {scan['events']:,} "
        f"events and retained {scan['TES_positive_events']:,} TES-positive events. The exact three "
        "near-field W volumes remain passive diagnostics and are disjoint from the three BGO plus "
        "three plastic active-veto volumes.\n\n"
        "No Plan-1 83,334-trigger delayed SIM or receipt is read or pooled. Detector response, W2, "
        "the common six-volume veto, and Step05 remain deferred to stage 04.\n"
    )


def postprocess_staging(staging: Path, final_output: Path) -> dict[str, Any]:
    mix_path = staging / "delayed_source_mix.csv"
    rewrite_csv_columns(mix_path, {
        "realized_83334_triggers": "realized_250000_triggers",
        "realized_83334_fraction": "realized_250000_fraction",
    })
    coverage_path = staging / "delayed_cell_coverage.csv"
    with coverage_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or ())
        rows = list(reader)
    for row in rows:
        if row.get("catalog_path"):
            row["catalog_path"] = prompt.display_path(
                final_output / "catalog" / "SF3" / f"{row['family']}.pkl"
            )
    with coverage_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    for catalog_path in sorted((staging / "catalog" / "SF3").glob("*.pkl")):
        with catalog_path.open("rb") as handle:
            catalog = pickle.load(handle)
        metadata = catalog.get("cell_metadata") or {}
        metadata.update({
            "profile_id": PROFILE_ID,
            "authority_status": "SF3_FULLSTAT_DELAYED_FRESH250K_RECEIPT_AND_EXACT_POSITION_LINEAGE",
            "registered_events": EXPECTED_EVENTS,
            "actual_transport_events": EXPECTED_EVENTS,
            "plan1_83334_consumed_or_pooled": False,
        })
        catalog["cell_metadata"] = metadata
        with catalog_path.open("wb") as handle:
            pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)

    summary_path = staging / "summary.json"
    summary = load_small_json(summary_path, "generated full-stat delayed summary")
    summary.update({
        "profile_id": PROFILE_ID,
        "status": PASS_STATUS,
        "scope": "SF3 full-stat own-inventory exact-position delayed raw catalog",
        "transport_triggers_per_family": EXPECTED_EVENTS,
        "input_namespace": str(RECEIPT_ROOT),
        "activation_source_index": str(SOURCE_INDEX),
        "plan1_83334_read": False,
        "plan1_83334_pooled": False,
        "incremental_83334_plus_166666_merge_used": False,
        "authority_boundary": "FULLSTAT_DELAYED_RAW_CATALOG_ONLY__NOT_COMMON_RESPONSE_MISSION_F3_OR_PROMOTION_AUTHORITY",
    })
    summary["source_mixture_qa"]["per_family_realized_triggers"] = EXPECTED_EVENTS
    summary["source_mixture_qa"]["realized_trigger_field"] = "realized_250000_triggers"
    summary["sim_scan_policy"].pop("prior_nonpublished_recovery_audit", None)
    summary["sim_scan_policy"].update({
        "receipt_namespace": str(RECEIPT_ROOT),
        "selected_sim_scope": "FRESH_FULLSTAT_250000_ONLY",
        "plan1_83334_sim_count": 0,
        "plan1_83334_accessed": False,
    })
    write_json(summary_path, summary)
    (staging / "REPORT.md").write_text(fullstat_report(summary), encoding="utf-8")

    manifest_path = staging / "manifest.json"
    manifest = load_small_json(manifest_path, "generated full-stat delayed manifest")
    manifest.update({
        "profile_id": PROFILE_ID,
        "status": PASS_STATUS,
        "analysis_code": prompt.display_path(HERE),
        "method": "retained exact-position infinity-norm cKDTree lineage over fresh fullstat 250k receipts",
        "input_namespace": str(RECEIPT_ROOT),
        "activation_source_index": str(SOURCE_INDEX),
        "plan1_83334_read": False,
        "plan1_83334_pooled": False,
        "hash_note": "No SIM hash was computed; each selected fresh full-stat SIM was semantically scanned once.",
    })
    files = sorted(path for path in staging.rglob("*") if path.is_file() and path != manifest_path)
    manifest["files"] = [
        {"path": str(path.relative_to(staging)), "bytes": path.stat().st_size}
        for path in files
    ]
    write_json(manifest_path, manifest)
    return summary


def run(workers: int = DEFAULT_WORKERS) -> dict[str, Any]:
    validate_workers(workers)
    prerequisites = check_prerequisites()
    if not prerequisites["ready"]:
        raise RuntimeError(json.dumps(prerequisites, indent=2, sort_keys=True))
    if OUTPUT_ROOT.exists():
        raise FileExistsError(f"refusing to overwrite write-once full-stat delayed output: {OUTPUT_ROOT}")
    OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    staging = OUTPUT_ROOT.parent / f".{OUTPUT_ROOT.name}.adapter-{os.getpid()}"
    if staging.exists():
        raise FileExistsError(f"full-stat delayed adapter staging path exists: {staging}")
    configure_raw_contract()
    raw.scan_job = scan_job_fullstat
    raw.selected_delayed_jobs = selected_delayed_jobs
    try:
        raw.run(POLICY_CONFIG, staging, workers)
        summary = postprocess_staging(staging, OUTPUT_ROOT)
        if OUTPUT_ROOT.exists():
            raise FileExistsError(f"write-once full-stat delayed output appeared during run: {OUTPUT_ROOT}")
        os.rename(staging, OUTPUT_ROOT)
        print(json.dumps({
            "status": summary["status"],
            "output": str(OUTPUT_ROOT),
            "workers": workers,
            "plan1_83334_read": False,
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    """Pure/static contract tests; no production receipt or SIM is accessed."""
    configure_raw_contract()
    retained = raw.self_test()
    if retained.get("status") != "PASS__SF3_DELAYED_ANALYZER_SELF_TEST" or retained.get("sim_opened") is not False:
        raise AssertionError("retained delayed parser/source-contract self-test did not PASS")
    plan = transport_runner.fixture_plan_rows()
    positive = [row for row in plan if row["execution_disposition"] == RUN_DISPOSITION]
    zero = [row for row in plan if row["execution_disposition"] == ZERO_DISPOSITION]
    if len(positive) != 7 or len(zero) != 1:
        raise AssertionError("full-stat analyzer positive/zero fixture split differs")
    if any(row["events"] != EXPECTED_EVENTS for row in positive):
        raise AssertionError("full-stat analyzer accepted a non-250k positive row")
    if zero[0]["events"] != 0 or zero[0]["registered_events"] != EXPECTED_EVENTS:
        raise AssertionError("full-stat analyzer zero registration/skip fixture differs")

    def fixture_source(plan_row: dict[str, Any]) -> dict[str, str]:
        is_zero = plan_row["execution_disposition"] == ZERO_DISPOSITION
        activity = 0.0 if is_zero else 1.0
        original_blocks = 0 if is_zero else raw.FULL_POSITION_BLOCKS
        transport_blocks = 0 if is_zero else raw.SELECTED_POSITION_BLOCKS
        original_flux = 0.0 if is_zero else activity / original_blocks
        transport_flux = 0.0 if is_zero else activity / transport_blocks
        sum_tt = 10.0
        upper = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt
        return {
            "geometry": "SF3",
            "incident_family": str(plan_row["family"]),
            "job_id": str(plan_row["job_id"]),
            "source_status": str(plan_row["source_status"]),
            "execution_disposition": str(plan_row["execution_disposition"]),
            "transport_eligible": "false" if is_zero else "true",
            "registered_decay_triggers": str(EXPECTED_EVENTS),
            "actual_transport_triggers": "0" if is_zero else str(EXPECTED_EVENTS),
            "transported_ground_activity_Bq": str(activity),
            "buildup_sum_TT_s": str(sum_tt),
            "zero_count_garwood_two_sided95_upper": (
                str(ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER) if is_zero else ""
            ),
            "transported_ground_rate_upper95_s-1": str(upper) if is_zero else "",
            "transported_ground_A15_upper95_Bq_conservative": str(upper) if is_zero else "",
            "zero_A15_upper_provenance": "synthetic finite upper" if is_zero else "",
            "upper_excludes_known_and_unresolved_holdout": "True",
            "known_holdout_activity_Bq": "0",
            "unknown_activity_state_count": "0",
            "included_state_count": "0" if is_zero else "1",
            "holdout_state_count": "0",
            "RPIP_points": "0" if is_zero else "1",
            "original_blocks": str(original_blocks),
            "transport_blocks": str(transport_blocks),
            "position_stride": str(raw.POSITION_STRIDE),
            "sampling_seed": str(plan_row["sampling_seed"]),
            "transport_seed": str(plan_row["seed"]),
            "original_block_flux_Bq": str(original_flux),
            "transport_block_flux_Bq": str(transport_flux),
            "original_total_Bq": str(activity),
            "transport_total_Bq": str(activity),
            "original_closure_Bq": "0",
            "transport_closure_Bq": "0",
            "source_path": str(plan_row["source_path"]),
            "source_sha256": "synthetic-source-sha",
            "sampled_positions_path": str(PACKAGE_ROOT / "synthetic_positions.csv"),
            "source_manifest_path": str(PACKAGE_ROOT / "synthetic_manifest.json"),
            "plan1_83334_role": PLAN1_DELAYED_ROLE,
            "incremental_merge_allowed": "false",
        }

    normalized_fixture: dict[str, dict[str, Any]] = {}
    for plan_row in (positive[0], zero[0]):
        source_errors, source = normalize_source_row(
            str(plan_row["family"]), fixture_source(plan_row), plan_row,
            check_compact_files=False,
        )
        if source_errors or source is None:
            raise AssertionError(f"builder source-index interface self-test failed: {source_errors}")
        normalized_fixture[str(plan_row["family"])] = {
            **source, "source_sha256": "synthetic-source-sha"
        }

    receipt_plan = positive[0]
    attempt_dir = RUN_ROOT / "jobs" / receipt_plan["job_id"] / "attempts" / "attempt01"
    synthetic_receipt = {
        "status": "PASS",
        "errors": [],
        "profile_id": PROFILE_ID,
        "job_id": receipt_plan["job_id"],
        "stage": receipt_plan["stage"],
        "geometry": "SF3",
        "mode": "delayed",
        "family": receipt_plan["family"],
        "registered_events": EXPECTED_EVENTS,
        "events": EXPECTED_EVENTS,
        "actual_transport_events": EXPECTED_EVENTS,
        "seed": receipt_plan["seed"],
        "setup_path": str(SF3_SETUP),
        "source_path": receipt_plan["source_path"],
        "source_sha256": "synthetic-source-sha",
        "source_status": receipt_plan["source_status"],
        "execution_disposition": RUN_DISPOSITION,
        "transport_eligible": True,
        "seed_namespace": PROFILE_ID,
        "plan1_83334_role": PLAN1_DELAYED_ROLE,
        "incremental_merge_allowed": False,
        "receipt_namespace": str(RECEIPT_ROOT),
        "attempt": 1,
        "attempt_dir": str(attempt_dir),
        "sim_path": str(attempt_dir / f"{receipt_plan['job_id']}.inc1.id1.sim.gz"),
        "sim_bytes": 1,
        "isotope_dat_path": None,
        "log": {"generated_events": EXPECTED_EVENTS, "graphics_terminal_marker": True},
        "sim_header": {
            "geometry": str(SF3_SETUP),
            "seed": receipt_plan["seed"],
            "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST",
        },
        "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
    }
    receipt_errors = receipt_metadata_errors(
        synthetic_receipt,
        receipt_plan,
        normalized_fixture[str(receipt_plan["family"])],
    )
    if receipt_errors:
        raise AssertionError(f"fresh250k receipt metadata interface self-test failed: {receipt_errors}")
    policy, errors = veto_policy()
    if errors or len(policy.get("active_veto_volumes", [])) != 6:
        raise AssertionError(f"exact six-active/three-passive policy self-test failed: {errors}")
    for allowed in (1, 4, 6):
        if validate_workers(allowed) != allowed:
            raise AssertionError("workers 1..6 validation differs")
    for forbidden in (0, 7):
        try:
            validate_workers(forbidden)
        except RuntimeError:
            pass
        else:
            raise AssertionError("out-of-range analyzer worker count was accepted")
    if raw.position_locator is None or raw.locate_source is None or raw.scan_job is None:
        raise AssertionError("retained exact-position delayed scan functions are unavailable")
    if set(prompt.PASSIVE_W_VOLUMES).intersection(policy["active_veto_volumes"]):
        raise AssertionError("passive W entered the active veto set")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_DELAYED_ANALYZER_STATIC_SELF_TEST",
        "checks": [
            "fixed_fullstat_activation_source_index_and_fresh250k_receipt_namespace",
            "positive_rows_exactly_250000_and_zero_rows_exactly_skipped",
            "Plan1_83334_and_166666_not_read_or_pooled",
            "retained_delayed_raw_parser_and_exact_parent_position_KD_tree_lineage",
            "exact_three_passive_W_diagnostics_disjoint_from_six_active_veto_volumes",
            "workers_1_through_6_with_default_4",
            "write_once_fixed_outputs_fullstat_03_delayed",
        ],
        "profile_id": PROFILE_ID,
        "output": str(OUTPUT_ROOT),
        "registered_families": EXPECTED_REGISTERED_CELLS,
        "fresh_events_per_positive_family": EXPECTED_EVENTS,
        "workers_default": DEFAULT_WORKERS,
        "workers_allowed": [1, 2, 3, 4, 5, 6],
        "production_artifacts_accessed": False,
        "SIM_opened": False,
        "SIM_statted": False,
        "SIM_hashed": False,
        "analysis_produced": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    validate_workers(args.workers)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    run(args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
