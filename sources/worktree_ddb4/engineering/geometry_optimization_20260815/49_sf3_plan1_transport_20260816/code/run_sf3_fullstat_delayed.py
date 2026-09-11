#!/usr/bin/env python3
"""Gate-locked controller for fresh SF3 full-stat delayed transport.

This runner is intentionally independent of the SF3 Plan-1 delayed run.  It
accepts only the future full-stat activation adapter's fixed namespaces, runs
exactly 250,000 fresh triggers for each positive-A15 family, and excludes each
full-inventory zero-A15 family.  It never reads, merges, credits, or reweights
the Plan-1 83,334-trigger delayed products.

``--self-test`` is pure/in-memory.  ``--check-prerequisites`` reads named small
CSV/JSON/source authorities only and never launches Cosima.  Production remains
locked behind both the central full-stat gate and a PASS full-inventory
activation/exact-position-source authority.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import io
import json
import math
import os
from pathlib import Path
from typing import Any

import build_sf3_fullstat_activation as activation_builder
import run_sf3_plan1 as base
from sf3_plan1_common import (
    COSIMA,
    DELAYED_EVENTS,
    DELAYED_TOTAL_ESTIMATED_BYTES,
    DYNAMIC_RESERVE_BYTES,
    FAMILIES,
    FORBIDDEN_TOKEN,
    FULLSTAT_DELAYED_EVENTS,
    MEGALIB_ENV,
    PACKAGE_ROOT,
    SF3_SETUP,
    SOURCE_WORKTREE,
    atomic_json,
    sha256,
    utc_now,
)


PROFILE_ID = activation_builder.FULLSTAT_DELAYED_NAMESPACE
FULLSTAT_ACTIVATION_ROOT = activation_builder.OUTPUT_ROOT
FULLSTAT_SOURCE_ROOT = activation_builder.DELAYED_CARD_ROOT
FULLSTAT_JOB_PLAN = activation_builder.DELAYED_JOB_PLAN
FULLSTAT_SEED_REGISTRY = activation_builder.DELAYED_SEED_REGISTRY
FULLSTAT_ACTIVATION_VALIDATION = activation_builder.ACTIVATION_VALIDATION
FULLSTAT_MISSION_SUMMARY = activation_builder.MISSION_SUMMARY
FULLSTAT_RUN_ROOT = activation_builder.FULLSTAT_DELAYED_RUN_ROOT
FULLSTAT_RECEIPT_ROOT = activation_builder.FULLSTAT_DELAYED_RECEIPT_ROOT
FULLSTAT_AGGREGATE_RECEIPT = activation_builder.FULLSTAT_DELAYED_AGGREGATE

FULLSTAT_ACTIVATION_STATUS = activation_builder.FULLSTAT_STATUS
FULLSTAT_VALIDATION_STATUS = activation_builder.FULLSTAT_VALIDATION_STATUS
FRESH_DISPOSITION = activation_builder.POSITIVE_DISPOSITION
ZERO_DISPOSITION = activation_builder.ZERO_DISPOSITION
FRESH_STRATEGY = "FRESH_COMPLETE_250000_PER_POSITIVE_FULL_INVENTORY_FAMILY"
SEED_NAMESPACE = activation_builder.FULLSTAT_DELAYED_NAMESPACE
PLAN1_DELAYED_ROLE = activation_builder.PLAN1_DELAYED_ROLE
FULLSTAT_COMPLETE_STATUS = "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE"
FULLSTAT_PARTIAL_STATUS = "PARTIAL__VALIDATED_FULLSTAT_DELAYED_RECEIPTS_ONLY"

CPU_BUDGET = 6
MIN_CPU_BUDGET = 4
MAX_CPU_BUDGET = 6
MIN_MEMORY_HEADROOM_BYTES = 1_610_612_736
MIN_SWAP_FREE_BYTES = 8 * 1024**3
PROJECTION_MARGIN = 1.02
DEFAULT_CANDIDATE_RSS_BYTES = 1_288_490_188  # 1.2 GiB, no Plan-1 delayed calibration
SMALL_AUTHORITY_MAX_BYTES = 20_000_000
MIN_FRESH_DELAYED_ESTIMATED_BYTES = math.ceil(
    DELAYED_TOTAL_ESTIMATED_BYTES / len(FAMILIES)
    * FULLSTAT_DELAYED_EVENTS / DELAYED_EVENTS
)

PLAN_FIELDS = activation_builder.DELAYED_PLAN_FIELDS
SEED_FIELDS = (
    "job_id",
    "family",
    "seed_identity",
    "seed",
    "namespace",
    "collision_with_prior_plan1_or_topup",
    "sampling_and_transport_seed_shared_within_job",
)

_BASE_LOAD_RECEIPT = base.load_receipt
_BASE_LAUNCH_ADMISSION = base.launch_admission
_BASE_VALIDATE_ATTEMPT = base.validate_attempt
_runtime_plan: list[dict[str, Any]] = []
_runtime_by_id: dict[str, dict[str, Any]] = {}
_runtime_exclusions: dict[str, str] = {}


def read_csv(path: Path, label: str) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    if path.stat().st_size <= 0 or path.stat().st_size > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"{label} is empty or oversized: {path} ({path.stat().st_size} bytes)")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        if not fields:
            raise RuntimeError(f"missing CSV header for {label}: {path}")
        return fields, list(reader)


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise FileNotFoundError(f"missing named JSON {label}: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"{label} is empty or oversized: {path} ({len(raw)} bytes)")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} root is not an object: {path}")
    return payload


def parse_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{label} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} must be a positive integer: {value!r}") from exc
    if parsed <= 0 or str(value).strip() != str(parsed):
        raise RuntimeError(f"{label} must be a positive decimal integer: {value!r}")
    return parsed


def parse_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{label} must be a non-negative integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} must be a non-negative integer: {value!r}") from exc
    if parsed < 0 or str(value).strip() != str(parsed):
        raise RuntimeError(f"{label} must be a non-negative decimal integer: {value!r}")
    return parsed


def parse_csv_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text not in {"true", "false"}:
        raise RuntimeError(f"{label} must be true/false: {value!r}")
    return text == "true"


def delayed_job_id(family: str) -> str:
    return f"sf3_fullstat_delayed_{family}"


def source_path(family: str) -> Path:
    return FULLSTAT_SOURCE_ROOT / f"{delayed_job_id(family)}.source"


def active_prefix(job_id: str) -> Path:
    return FULLSTAT_RUN_ROOT / "jobs" / job_id / "active" / job_id


def receipt_path(job_id: str) -> Path:
    return FULLSTAT_RECEIPT_ROOT / f"{job_id}.json"


def cast_plan_row(raw: dict[str, Any]) -> dict[str, Any]:
    if tuple(raw) != PLAN_FIELDS:
        raise RuntimeError(f"full-stat delayed plan schema differs for {raw.get('job_id')}")
    row: dict[str, Any] = dict(raw)
    for key in ("ordinal", "registered_events", "seed", "sampling_seed"):
        row[key] = parse_positive_int(raw[key], f"{raw.get('job_id')} {key}")
    for key in ("events", "actual_transport_events"):
        row[key] = parse_nonnegative_int(raw[key], f"{raw.get('job_id')} {key}")
    for key in ("transport_eligible", "incremental_merge_allowed"):
        row[key] = parse_csv_bool(raw[key], f"{raw.get('job_id')} {key}")
    return row


def validate_plan_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) != len(FAMILIES):
        raise RuntimeError(f"full-stat delayed plan must contain 8 rows, got {len(rows)}")
    if [row["ordinal"] for row in rows] != list(range(1, len(FAMILIES) + 1)):
        raise RuntimeError("full-stat delayed plan ordinals are not exactly 1..8")
    if [row["family"] for row in rows] != list(FAMILIES):
        raise RuntimeError("full-stat delayed plan family order/set differs")
    if len({row["seed"] for row in rows}) != len(rows):
        raise RuntimeError("full-stat delayed plan seeds are not unique")
    for row in rows:
        family = str(row["family"])
        job_id = delayed_job_id(family)
        expected = {
            "job_id": job_id,
            "stage": "fullstat_delayed",
            "geometry": "SF3",
            "mode": "delayed",
            "registered_events": FULLSTAT_DELAYED_EVENTS,
            "sampling_seed": row["seed"],
            "seed_identity": job_id,
            "seed_namespace": SEED_NAMESPACE,
            "source_path": str(source_path(family)),
            "setup_path": str(SF3_SETUP),
            "run_root": str(FULLSTAT_RUN_ROOT),
            "receipt_path": str(receipt_path(job_id)),
            "aggregate_receipt_path": str(FULLSTAT_AGGREGATE_RECEIPT),
            "plan1_83334_role": PLAN1_DELAYED_ROLE,
            "incremental_merge_allowed": False,
            "source_support": "REBUILT_FULLSTAT_23_BUILDUP_RECEIPTS_ACTUAL_RPIP_POSITIONS",
        }
        differences = {
            key: {"expected": value, "observed": row.get(key)}
            for key, value in expected.items()
            if row.get(key) != value
        }
        if differences:
            raise RuntimeError(f"full-stat delayed plan row differs for {family}: {differences}")
        disposition = row["execution_disposition"]
        if disposition == FRESH_DISPOSITION:
            if (
                row["events"] != FULLSTAT_DELAYED_EVENTS
                or row["actual_transport_events"] != FULLSTAT_DELAYED_EVENTS
                or row["transport_eligible"] is not True
                or not str(row["source_status"]).startswith("PASS__")
            ):
                raise RuntimeError(f"positive full-stat delayed plan semantics differ for {family}")
            row["estimated_bytes"] = MIN_FRESH_DELAYED_ESTIMATED_BYTES
        elif disposition == ZERO_DISPOSITION:
            if (
                row["events"] != 0
                or row["actual_transport_events"] != 0
                or row["transport_eligible"] is not False
                or not str(row["source_status"]).startswith("ZERO_SOURCE__")
            ):
                raise RuntimeError(f"zero full-stat delayed plan semantics differ for {family}")
            row["estimated_bytes"] = 0
        else:
            raise RuntimeError(f"unknown full-stat delayed disposition for {family}: {disposition}")
        if any(
            value in {83_334, 166_666}
            for value in (row["registered_events"], row["events"], row["actual_transport_events"])
        ):
            raise RuntimeError(f"screening/incremental event count leaked into full-stat plan: {family}")
    return rows


def load_plan_unbound() -> list[dict[str, Any]]:
    fields, raw = read_csv(FULLSTAT_JOB_PLAN, "full-stat delayed job plan")
    if fields != PLAN_FIELDS:
        raise RuntimeError(f"full-stat delayed plan header differs: {fields}")
    return validate_plan_rows([cast_plan_row(row) for row in raw])


def validate_seed_rows(
    raw_rows: list[dict[str, Any]], plan: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(raw_rows) != len(FAMILIES):
        raise RuntimeError(f"full-stat delayed seed registry must contain 8 rows, got {len(raw_rows)}")
    result: list[dict[str, Any]] = []
    plan_by_id = {row["job_id"]: row for row in plan}
    for raw in raw_rows:
        if tuple(raw) != SEED_FIELDS:
            raise RuntimeError(f"full-stat delayed seed schema differs for {raw.get('job_id')}")
        job_id = raw["job_id"]
        seed = parse_positive_int(raw["seed"], f"{job_id} registered seed")
        row = {
            **raw,
            "seed": seed,
            "collision_with_prior_plan1_or_topup": parse_csv_bool(
                raw["collision_with_prior_plan1_or_topup"],
                f"{job_id} collision_with_prior_plan1_or_topup",
            ),
            "sampling_and_transport_seed_shared_within_job": parse_csv_bool(
                raw["sampling_and_transport_seed_shared_within_job"],
                f"{job_id} sampling_and_transport_seed_shared_within_job",
            ),
        }
        expected = plan_by_id.get(job_id)
        if expected is None:
            raise RuntimeError(f"seed registry job is absent from plan: {job_id}")
        if (
            row["family"] != expected["family"]
            or row["seed_identity"] != job_id
            or row["seed"] != expected["seed"]
            or row["namespace"] != SEED_NAMESPACE
            or row["collision_with_prior_plan1_or_topup"] is not False
            or row["sampling_and_transport_seed_shared_within_job"] is not True
        ):
            raise RuntimeError(f"fresh full-stat delayed seed binding differs: {job_id}")
        result.append(row)
    if {row["job_id"] for row in result} != set(plan_by_id):
        raise RuntimeError("full-stat delayed seed registry job closure differs")
    if len({row["seed"] for row in result}) != len(result):
        raise RuntimeError("duplicate full-stat delayed seed")
    return result


def load_seed_registry(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields, rows = read_csv(FULLSTAT_SEED_REGISTRY, "full-stat delayed seed registry")
    if fields != SEED_FIELDS:
        raise RuntimeError(f"full-stat delayed seed header differs: {fields}")
    return validate_seed_rows(rows, plan)


def validate_gate_authority() -> dict[str, Any]:
    current = activation_builder.validate_mission_gate(FULLSTAT_MISSION_SUMMARY)
    if (
        current.get("status") != "PASS__CENTRAL_FULLSTAT_GATE_AUTHORIZES_REBUILD"
        or current["central_R_F3"] > 0.75
        or current["topup_required"] is not True
        or current["proxy_controls_gate"] is not False
    ):
        raise RuntimeError("full-stat delayed runner is not authorized by the central-only gate")
    return current


def validate_named_record(record: Any, expected: Path, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RuntimeError(f"activation validation lacks {label} file record")
    path = Path(str(record.get("path", "")))
    if path.resolve() != expected.resolve():
        raise RuntimeError(f"activation {label} path differs: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"activation {label} is missing/empty: {path}")
    if path.stat().st_size > SMALL_AUTHORITY_MAX_BYTES:
        raise RuntimeError(f"activation {label} is oversized: {path} ({path.stat().st_size} bytes)")
    digest = sha256(path)
    if record.get("sha256") != digest:
        raise RuntimeError(f"activation {label} digest differs")
    return {"path": str(path), "sha256": digest, "bytes": path.stat().st_size}


def validate_activation_structure(payload: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    exact = {
        "status": FULLSTAT_VALIDATION_STATUS,
        "profile_id": PROFILE_ID,
        "geometry": "SF3",
        "hard_gates": {
            "central_mission_topup_required_true": True,
            "all_28_topup_background_canonical_PASS": True,
        },
        "combined_buildup_jobs": 23,
        "combined_buildup_histories": 3_046_468,
        "registered_delayed_source_cells": len(FAMILIES),
        "registered_events_per_family": FULLSTAT_DELAYED_EVENTS,
        "plan1_delayed_consumed": False,
        "plan1_83334_role": PLAN1_DELAYED_ROLE,
        "incremental_83334_plus_166666_merge_allowed": False,
        "transport_launched": False,
    }
    differences = {
        key: {"expected": value, "observed": payload.get(key)}
        for key, value in exact.items()
        if payload.get(key) != value
    }
    if differences:
        raise RuntimeError(f"full-stat activation launch authority differs: {differences}")
    activation_gate = payload.get("central_gate")
    if not isinstance(activation_gate, dict):
        raise RuntimeError("full-stat activation does not bind the central gate")
    for key in (
        "path", "sha256", "central_R_F3", "threshold", "topup_required",
        "decision", "proxy_controls_gate",
    ):
        if activation_gate.get(key) != gate.get(key):
            raise RuntimeError(f"activation central-gate binding differs: {key}")

    topup_gate = payload.get("topup_receipt_gate") or {}
    if (
        topup_gate.get("status") != "PASS__ALL_28_FULLSTAT_TOPUP_CANONICAL_RECEIPTS_METADATA"
        or topup_gate.get("validated_jobs") != 28
        or topup_gate.get("validated_buildup_jobs") != 13
    ):
        raise RuntimeError("activation validation top-up receipt gate differs")
    validate_named_record(
        topup_gate.get("aggregate"), activation_builder.TOPUP_AGGREGATE,
        "topup_receipt_gate.aggregate",
    )

    named = {
        "delayed_job_plan": validate_named_record(
            payload.get("delayed_job_plan"), FULLSTAT_JOB_PLAN, "delayed_job_plan"
        ),
        "delayed_seed_registry": validate_named_record(
            payload.get("delayed_seed_registry"), FULLSTAT_SEED_REGISTRY,
            "delayed_seed_registry",
        ),
        "manifest": validate_named_record(
            payload.get("manifest"), FULLSTAT_ACTIVATION_ROOT / "manifest.json", "manifest"
        ),
        "day15_summary": validate_named_record(
            payload.get("day15_summary"),
            FULLSTAT_ACTIVATION_ROOT / "day15_summary.json",
            "day15_summary",
        ),
        "delayed_source_index": validate_named_record(
            payload.get("delayed_source_index"),
            FULLSTAT_ACTIVATION_ROOT / "delayed_source_index.csv",
            "delayed_source_index",
        ),
    }
    for key in ("manifest", "day15_summary"):
        stage_payload = load_small_json(Path(named[key]["path"]), f"full-stat activation {key}")
        if stage_payload.get("status") != FULLSTAT_ACTIVATION_STATUS:
            raise RuntimeError(f"full-stat activation {key} semantic status differs")
    cards = payload.get("source_cards")
    if not isinstance(cards, list) or len(cards) != len(FAMILIES):
        raise RuntimeError("full-stat activation must publish exactly 8 source-card records")
    return {"payload": payload, "named": named, "source_cards": cards}


def validate_source_text(text: str, row: dict[str, Any], disposition: str) -> None:
    job_id = str(row["job_id"])
    required = (
        f"Geometry {SF3_SETUP}",
        f"Seed {row['seed']}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "Run DecayRun",
        f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}",
        f"DecayRun.FileName {active_prefix(job_id)}",
    )
    for token in required:
        if sum(line.strip() == token for line in text.splitlines()) != 1:
            raise RuntimeError(f"full-stat delayed source binding differs for {job_id}: {token}")
    if FORBIDDEN_TOKEN in text:
        raise RuntimeError(f"legacy corrected-keV token appears in full-stat delayed card: {job_id}")
    trigger_lines = [
        line.strip() for line in text.splitlines()
        if not line.lstrip().startswith("#") and ".Triggers " in line
    ]
    if trigger_lines != [f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}"]:
        raise RuntimeError(f"screening/incremental trigger directive appears in fresh card: {job_id}")
    source_directives = [line for line in text.splitlines() if line.startswith("DecayRun.Source ")]
    if disposition == FRESH_DISPOSITION and not source_directives:
        raise RuntimeError(f"positive full-stat delayed card has no exact-position sources: {job_id}")
    if disposition == ZERO_DISPOSITION and source_directives:
        raise RuntimeError(f"zero-A15 full-stat delayed card contains a source: {job_id}")


def bind_activation_to_plan(
    plan: list[dict[str, Any]], activation: dict[str, Any]
) -> list[dict[str, Any]]:
    raw_cards = activation["source_cards"]
    cards: dict[str, dict[str, Any]] = {}
    for item in raw_cards:
        if not isinstance(item, dict):
            raise RuntimeError("full-stat activation source-card record is not an object")
        family = str(item.get("family", ""))
        if family in cards:
            raise RuntimeError(f"duplicate full-stat activation source-card family: {family}")
        cards[family] = item
    if set(cards) != set(FAMILIES):
        raise RuntimeError("full-stat activation source-card family closure differs")

    bound: list[dict[str, Any]] = []
    positive: list[str] = []
    zero: list[str] = []
    for raw in plan:
        row = dict(raw)
        family = str(row["family"])
        record = cards[family]
        disposition = str(record.get("execution_disposition", ""))
        if disposition not in {FRESH_DISPOSITION, ZERO_DISPOSITION}:
            raise RuntimeError(f"unknown full-stat delayed disposition for {family}: {disposition}")
        if (
            record.get("job_id") != row["job_id"]
            or record.get("seed") != row["seed"]
            or record.get("registered_events") != FULLSTAT_DELAYED_EVENTS
            or record.get("actual_transport_events") != row["actual_transport_events"]
            or disposition != row["execution_disposition"]
            or Path(str(record.get("path", ""))).resolve() != source_path(family).resolve()
        ):
            raise RuntimeError(f"activation/plan/source identity differs for {family}")
        card = source_path(family)
        if not card.is_file() or card.stat().st_size <= 0:
            raise RuntimeError(f"full-stat delayed source card missing/empty: {card}")
        if card.stat().st_size > SMALL_AUTHORITY_MAX_BYTES:
            raise RuntimeError(f"full-stat delayed source card is oversized: {card}")
        digest = sha256(card)
        if record.get("sha256") != digest:
            raise RuntimeError(f"full-stat delayed source-card digest differs for {family}")
        text = card.read_text(encoding="utf-8", errors="strict")
        validate_source_text(text, row, disposition)
        activity = record.get("transported_ground_activity_Bq")
        if isinstance(activity, bool) or not isinstance(activity, (int, float)) or not math.isfinite(float(activity)):
            raise RuntimeError(f"invalid full-stat transported activity for {family}")
        if disposition == FRESH_DISPOSITION:
            if (
                float(activity) <= 0
                or record.get("actual_transport_events") != FULLSTAT_DELAYED_EVENTS
                or row["events"] != FULLSTAT_DELAYED_EVENTS
                or row["transport_eligible"] is not True
                or record.get("original_blocks") != activation_builder.base.ORIGINAL_POSITION_BLOCKS
                or record.get("transport_blocks") != activation_builder.base.TRANSPORT_POSITION_BLOCKS
            ):
                raise RuntimeError(f"positive-A15 fresh-250k contract differs for {family}")
            if any(record.get(key) is not None for key in (
                "transported_ground_A15_upper95_Bq_conservative", "zero_A15_upper_provenance"
            )):
                raise RuntimeError(f"positive-A15 cell publishes zero-source upper fields: {family}")
            positive.append(family)
        else:
            upper = record.get("transported_ground_A15_upper95_Bq_conservative")
            if (
                float(activity) != 0.0
                or record.get("actual_transport_events") != 0
                or row["events"] != 0
                or row["transport_eligible"] is not False
                or isinstance(upper, bool)
                or not isinstance(upper, (int, float))
                or not math.isfinite(float(upper))
                or float(upper) <= 0.0
                or not record.get("zero_A15_upper_provenance")
            ):
                raise RuntimeError(f"zero-A15 skip/finite-upper contract differs for {family}")
            zero.append(family)
        row["execution_disposition"] = disposition
        row["transported_ground_activity_Bq"] = float(activity)
        bound.append(row)

    payload = activation["payload"]
    if payload.get("fresh_delayed_transport_jobs") != len(positive):
        raise RuntimeError("full-stat activation positive-job count differs")
    if payload.get("zero_A15_skipped_jobs") != len(zero):
        raise RuntimeError("full-stat activation zero-job count differs")
    if payload.get("actual_transport_events_total") != FULLSTAT_DELAYED_EVENTS * len(positive):
        raise RuntimeError("full-stat activation trigger total differs")
    return bound


def install_runtime_plan(plan: list[dict[str, Any]]) -> None:
    global _runtime_plan, _runtime_by_id, _runtime_exclusions
    _runtime_plan = [dict(row) for row in plan]
    _runtime_by_id = {row["job_id"]: row for row in _runtime_plan}
    _runtime_exclusions = {
        row["job_id"]: "FULL_INVENTORY_EXACT_ZERO_A15__NO_TRANSPORT"
        for row in _runtime_plan
        if row.get("execution_disposition") == ZERO_DISPOSITION
    }


def execution_exclusions() -> dict[str, str]:
    return dict(_runtime_exclusions)


def validate_attempt(
    job: dict[str, Any], active_dir: Path, returncode: int, wall_s: float, peak_rss: int
) -> dict[str, Any]:
    """Extend the retained attempt receipt with the builder's delayed schema."""
    if (
        job.get("execution_disposition") != FRESH_DISPOSITION
        or job.get("transport_eligible") is not True
        or job.get("registered_events") != FULLSTAT_DELAYED_EVENTS
        or job.get("events") != FULLSTAT_DELAYED_EVENTS
        or job.get("actual_transport_events") != FULLSTAT_DELAYED_EVENTS
    ):
        raise RuntimeError(f"non-positive or non-250k job reached delayed attempt validation: {job.get('job_id')}")
    result = _BASE_VALIDATE_ATTEMPT(job, active_dir, returncode, wall_s, peak_rss)
    result.update({
        "registered_events": job["registered_events"],
        "actual_transport_events": job["actual_transport_events"],
        "source_status": job["source_status"],
        "execution_disposition": job["execution_disposition"],
        "transport_eligible": job["transport_eligible"],
        "seed_namespace": job["seed_namespace"],
        "plan1_83334_role": job["plan1_83334_role"],
        "incremental_merge_allowed": job["incremental_merge_allowed"],
        "receipt_namespace": str(FULLSTAT_RECEIPT_ROOT),
    })
    return result


def receipt_contract_errors(payload: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    checks = {
        "profile_id": PROFILE_ID,
        "job_id": expected["job_id"],
        "stage": expected["stage"],
        "geometry": "SF3",
        "mode": "delayed",
        "family": expected["family"],
        "registered_events": expected["registered_events"],
        "events": expected["events"],
        "actual_transport_events": expected["actual_transport_events"],
        "seed": expected["seed"],
        "setup_path": str(SF3_SETUP),
        "source_status": expected["source_status"],
        "execution_disposition": FRESH_DISPOSITION,
        "transport_eligible": True,
        "seed_namespace": SEED_NAMESPACE,
        "plan1_83334_role": PLAN1_DELAYED_ROLE,
        "incremental_merge_allowed": False,
        "receipt_namespace": str(FULLSTAT_RECEIPT_ROOT),
    }
    errors: list[str] = []
    for key, value in checks.items():
        observed = payload.get(key)
        if key == "setup_path":
            if Path(str(observed)).resolve() != Path(str(value)).resolve():
                errors.append(f"{key} differs")
        elif observed != value:
            errors.append(f"{key}={observed!r} != {value!r}")
    if payload.get("isotope_dat_path") is not None:
        errors.append("fresh delayed receipt unexpectedly names a DAT")
    header = payload.get("sim_header") or {}
    if Path(str(header.get("geometry", ""))).resolve() != SF3_SETUP.resolve():
        errors.append("SIM header geometry is not SF3")
    if header.get("seed") != expected["seed"]:
        errors.append("SIM header seed differs")
    if header.get("policy") != "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST":
        errors.append("SIM header-only policy differs")
    if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
        errors.append("SIM digest policy differs")
    return errors


def load_receipt(job_id: str) -> dict[str, Any] | None:
    payload = _BASE_LOAD_RECEIPT(job_id)
    if payload is None:
        return None
    expected = _runtime_by_id.get(job_id)
    if expected is None:
        raise RuntimeError(f"receipt is outside the bound full-stat delayed plan: {job_id}")
    if expected.get("execution_disposition") != FRESH_DISPOSITION:
        raise RuntimeError(f"zero-A15 job has a canonical transport receipt: {job_id}")
    errors = receipt_contract_errors(payload, expected)
    if errors:
        raise RuntimeError(f"canonical full-stat delayed receipt failed: {job_id}: {errors}")
    return payload


def calibrated_estimate(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    measurements = [
        load_receipt(row["job_id"])
        for row in plan
        if row.get("execution_disposition") == FRESH_DISPOSITION
    ]
    valid = [
        item for item in measurements
        if item is not None and int(item.get("events", 0)) > 0 and int(item.get("artifact_bytes", 0)) > 0
    ]
    if valid:
        measured = max(
            int(item["artifact_bytes"]) / int(item["events"])
            for item in valid
        )
        return int(max(
            math.ceil(measured * int(job["events"]) * PROJECTION_MARGIN),
            math.ceil(int(job["estimated_bytes"]) * PROJECTION_MARGIN),
        ))
    return int(math.ceil(int(job["estimated_bytes"]) * PROJECTION_MARGIN))


def candidate_rss(job: dict[str, Any], plan: list[dict[str, Any]]) -> int:
    observed: list[int] = []
    for row in plan:
        if row.get("execution_disposition") != FRESH_DISPOSITION:
            continue
        receipt = load_receipt(row["job_id"])
        if receipt is not None:
            observed.append(int(receipt["peak_process_group_rss_bytes"]))
        failed_root = FULLSTAT_RUN_ROOT / "jobs" / row["job_id"] / "failed"
        if failed_root.is_dir():
            for validation_path in sorted(failed_root.glob("attempt*/validation.json")):
                validation = load_small_json(validation_path, f"failed fresh-delayed attempt {row['job_id']}")
                peak = base.failed_peak_rss_bytes(validation)
                if peak is not None:
                    observed.append(peak)
    return int(max(DEFAULT_CANDIDATE_RSS_BYTES, max(observed, default=0) * 1.05))


def launch_admission(
    job: dict[str, Any], plan: list[dict[str, Any]], scheduled: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    admission = _BASE_LAUNCH_ADMISSION(job, plan, scheduled)
    policy = base.configured_adaptive_concurrency_policy()
    pressure = base.memory_pressure_snapshot(policy)
    global_pass = (
        pressure.get("evidence_available") is True
        and pressure.get("swap_free_bytes") is not None
        and int(pressure["swap_free_bytes"]) >= MIN_SWAP_FREE_BYTES
        and pressure.get("thrashing_detected") is False
        and base.mem_available_bytes() >= MIN_MEMORY_HEADROOM_BYTES
    )
    admission["global_memory_swap_psi_gate"] = {
        "pass": global_pass,
        "mem_available_floor_bytes": MIN_MEMORY_HEADROOM_BYTES,
        "swap_free_floor_bytes": MIN_SWAP_FREE_BYTES,
        "pressure": pressure,
    }
    if admission["pass"] and not global_pass:
        admission["pass"] = False
        admission["blocked_reason"] = {
            "kind": "GLOBAL_MEMORY_SWAP_PSI_GATE",
            "gate": admission["global_memory_swap_psi_gate"],
        }
    return admission


def refresh_aggregate(plan: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [row for row in plan if row["execution_disposition"] == FRESH_DISPOSITION]
    zero = [row for row in plan if row["execution_disposition"] == ZERO_DISPOSITION]
    selected: list[dict[str, Any]] = []
    for job in positive:
        receipt = load_receipt(job["job_id"])
        if receipt is None:
            continue
        path = receipt_path(job["job_id"])
        selected.append({
            "job_id": job["job_id"],
            "family": job["family"],
            "stage": job["stage"],
            "registered_events": job["registered_events"],
            "events": job["events"],
            "actual_transport_events": job["actual_transport_events"],
            "seed": job["seed"],
            "execution_disposition": job["execution_disposition"],
            "transport_eligible": job["transport_eligible"],
            "receipt_path": str(path),
            "receipt_sha256": sha256(path),
            "sim_path": receipt["sim_path"],
            "sim_bytes": receipt["sim_bytes"],
            "peak_process_group_rss_bytes": receipt["peak_process_group_rss_bytes"],
            "artifact_bytes": receipt["artifact_bytes"],
            "sim_digest_policy": receipt["sim_digest_policy"],
        })
    all_done = {row["job_id"] for row in selected} == {row["job_id"] for row in positive}
    aggregate = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "updated_at": utc_now(),
        "status": (
            FULLSTAT_COMPLETE_STATUS if all_done else FULLSTAT_PARTIAL_STATUS
        ),
        "registered_families": len(plan),
        "positive_A15_families": [row["family"] for row in positive],
        "zero_A15_families": [row["family"] for row in zero],
        "planned_transport_jobs": len(positive),
        "validated_transport_jobs": len(selected),
        "fresh_triggers_per_positive_family": FULLSTAT_DELAYED_EVENTS,
        "validated_fresh_triggers": sum(row["events"] for row in selected),
        "zero_A15_jobs_skipped": len(zero),
        "selected_receipts": selected,
        "execution_exclusions": execution_exclusions(),
        "projection": base.projection(plan),
        "run_root": str(FULLSTAT_RUN_ROOT),
        "receipt_root": str(FULLSTAT_RECEIPT_ROOT),
        "plan1_83334_read": False,
        "plan1_83334_pooled": False,
        "incremental_merge_used": False,
        "delayed_strategy": FRESH_STRATEGY,
        "sim_access_policy": "NEW_FULLSTAT_DELAYED_SIM_HEADER_ONLY__NO_SIM_DIGEST_OR_FULL_REOPEN",
    }
    atomic_json(FULLSTAT_AGGREGATE_RECEIPT, aggregate)
    return aggregate


def configure_runtime(cpu_budget: int = CPU_BUDGET) -> None:
    base.RUN_ROOT = FULLSTAT_RUN_ROOT
    base.PACKAGE_ROOT = PACKAGE_ROOT
    base.PROFILE_ID = PROFILE_ID
    base.SOURCE_WORKTREE = SOURCE_WORKTREE
    base.CPU_BUDGET = cpu_budget
    base.MAX_CPU_BUDGET = MAX_CPU_BUDGET
    base.DYNAMIC_RESERVE_BYTES = DYNAMIC_RESERVE_BYTES
    base.receipt_path = receipt_path
    base.load_receipt = load_receipt
    base.validate_attempt = validate_attempt
    base.execution_exclusions = execution_exclusions
    base.calibrated_estimate = calibrated_estimate
    base.candidate_rss = candidate_rss
    base.launch_admission = launch_admission
    base.refresh_aggregate = refresh_aggregate


def validate_cpu_budget(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_CPU_BUDGET <= value <= MAX_CPU_BUDGET:
        raise RuntimeError("fresh full-stat delayed cpu budget must be 4, 5, or 6")
    return value


def check_prerequisites(
    *, include_live_admission: bool = True, requested_cpu_budget: int = CPU_BUDGET
) -> dict[str, Any]:
    errors: list[str] = []
    missing: list[str] = []
    authorities: dict[str, Any] = {}
    plan: list[dict[str, Any]] = []
    gate: dict[str, Any] | None = None
    activation: dict[str, Any] | None = None

    try:
        validate_cpu_budget(requested_cpu_budget)
    except Exception as exc:
        errors.append(str(exc))

    for path in (
        FULLSTAT_MISSION_SUMMARY,
        FULLSTAT_ACTIVATION_VALIDATION,
        FULLSTAT_JOB_PLAN,
        FULLSTAT_SEED_REGISTRY,
    ):
        if not path.is_file():
            missing.append(str(path))

    if FULLSTAT_MISSION_SUMMARY.is_file():
        try:
            gate = validate_gate_authority()
            authorities["central_gate"] = gate
        except Exception as exc:
            errors.append(f"central full-stat gate validation failed: {exc}")

    if gate is not None and FULLSTAT_ACTIVATION_VALIDATION.is_file():
        try:
            raw_activation = load_small_json(
                FULLSTAT_ACTIVATION_VALIDATION, "full-stat activation launch authority"
            )
            activation = validate_activation_structure(raw_activation, gate)
            authorities["activation"] = {
                "path": str(FULLSTAT_ACTIVATION_VALIDATION),
                "sha256": sha256(FULLSTAT_ACTIVATION_VALIDATION),
                "status": raw_activation.get("status"),
                "profile_id": raw_activation.get("profile_id"),
                "named": activation["named"],
            }
        except Exception as exc:
            errors.append(f"full-stat activation validation failed: {exc}")

    if FULLSTAT_JOB_PLAN.is_file() and FULLSTAT_SEED_REGISTRY.is_file():
        try:
            plan = load_plan_unbound()
            seeds = load_seed_registry(plan)
            authorities["job_plan"] = {
                "path": str(FULLSTAT_JOB_PLAN), "sha256": sha256(FULLSTAT_JOB_PLAN), "rows": len(plan)
            }
            authorities["seed_registry"] = {
                "path": str(FULLSTAT_SEED_REGISTRY),
                "sha256": sha256(FULLSTAT_SEED_REGISTRY),
                "rows": len(seeds),
            }
        except Exception as exc:
            errors.append(f"full-stat delayed plan/seed validation failed: {exc}")
            plan = []

    if plan and activation is not None:
        try:
            plan = bind_activation_to_plan(plan, activation)
            install_runtime_plan(plan)
            for job in plan:
                active = FULLSTAT_RUN_ROOT / "jobs" / job["job_id"] / "active"
                if active.exists():
                    errors.append(f"stale active fresh-delayed attempt requires recovery: {active}")
                receipt = receipt_path(job["job_id"])
                if job["execution_disposition"] == ZERO_DISPOSITION and receipt.exists():
                    errors.append(f"zero-A15 job unexpectedly has a canonical receipt: {receipt}")
        except Exception as exc:
            errors.append(f"full-stat activation/plan/source binding failed: {exc}")
            plan = []

    resource: dict[str, Any] = {}
    if include_live_admission and plan and not errors and not missing:
        try:
            policy = base.configured_adaptive_concurrency_policy()
            pressure = base.memory_pressure_snapshot(policy)
            headroom = base.configured_memory_headroom_bytes()
            disk = base.projection(plan)
            resource = {
                "requested_cpu_budget": requested_cpu_budget,
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
                errors.append("dynamic full-stat delayed projection fails the 8 GiB reserve")
        except Exception as exc:
            errors.append(f"live resource admission check failed: {exc}")

    ready = not errors and not missing and bool(plan)
    return {
        "schema_version": 1,
        "status": (
            "READY__SF3_FULLSTAT_DELAYED_CONTROLLER"
            if ready else "NOT_READY__SF3_FULLSTAT_DELAYED_PREREQUISITES"
        ),
        "ready": ready,
        "checked_at": utc_now(),
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(FULLSTAT_RUN_ROOT),
        "receipt_root": str(FULLSTAT_RECEIPT_ROOT),
        "planned_families": len(plan),
        "planned_positive_A15_jobs": sum(
            row.get("execution_disposition") == FRESH_DISPOSITION for row in plan
        ),
        "planned_zero_A15_skips": sum(
            row.get("execution_disposition") == ZERO_DISPOSITION for row in plan
        ),
        "authorities": authorities,
        "hard_gates": {
            "central_mission_gate_PASS": gate is not None,
            "activation_validation_PASS": activation is not None,
        },
        "resource": resource,
        "missing": sorted(set(missing)),
        "errors": errors,
        "transport_launched": False,
        "plan1_83334_read": False,
        "plan1_83334_pooled": False,
        "sim_access_policy": "NO_HISTORICAL_OR_PLAN1_DELAYED_SIM_ACCESS__NEW_FULLSTAT_SIM_HEADER_ONLY_AFTER_RUN",
    }


def fixture_plan_rows() -> list[dict[str, Any]]:
    seeds = {family: 1_700_000_000 + ordinal for ordinal, family in enumerate(FAMILIES, 1)}
    decisions = {
        family: {
            "source_status": (
                "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY"
                if family == FAMILIES[-1]
                else "PASS__SF3_FULLSTAT_STRIDE5_M10000_DELAYED_SOURCE_READY"
            ),
            "execution_disposition": (
                ZERO_DISPOSITION if family == FAMILIES[-1] else FRESH_DISPOSITION
            ),
        }
        for family in FAMILIES
    }
    builder_rows = activation_builder.build_delayed_plan(seeds, decisions)
    stream = io.StringIO(activation_builder.csv_text(builder_rows, PLAN_FIELDS))
    csv_rows = list(csv.DictReader(stream))
    if tuple(csv_rows[0]) != PLAN_FIELDS:
        raise AssertionError("builder/runner CSV header interface differs")
    return validate_plan_rows([cast_plan_row(row) for row in csv_rows])


def self_test() -> dict[str, Any]:
    builder_test = activation_builder.self_test()
    if builder_test.get("status") != "PASS__SF3_FULLSTAT_ACTIVATION_BUILDER_PURE_SYNTHETIC_SELF_TEST":
        raise AssertionError("activation builder pure self-test did not PASS")
    plan = fixture_plan_rows()
    positive = [row for row in plan if row["execution_disposition"] == FRESH_DISPOSITION]
    zero = [row for row in plan if row["execution_disposition"] == ZERO_DISPOSITION]
    if len(positive) != 7 or len(zero) != 1:
        raise AssertionError("builder/runner positive/zero interface split differs")
    if any(row["events"] != FULLSTAT_DELAYED_EVENTS for row in positive):
        raise AssertionError("builder/runner positive rows are not fresh 250k")
    if (
        zero[0]["registered_events"] != FULLSTAT_DELAYED_EVENTS
        or zero[0]["events"] != 0
        or zero[0]["actual_transport_events"] != 0
        or zero[0]["transport_eligible"] is not False
    ):
        raise AssertionError("builder/runner explicit zero registration/skip interface differs")
    seed_rows = [{
        "job_id": row["job_id"],
        "family": row["family"],
        "seed_identity": row["seed_identity"],
        "seed": str(row["seed"]),
        "namespace": SEED_NAMESPACE,
        "collision_with_prior_plan1_or_topup": "False",
        "sampling_and_transport_seed_shared_within_job": "True",
    } for row in plan]
    validate_seed_rows(seed_rows, plan)

    positive_text = "\n".join((
        f"Geometry {SF3_SETUP}",
        f"Seed {positive[0]['seed']}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "Run DecayRun",
        f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}",
        f"DecayRun.FileName {active_prefix(positive[0]['job_id'])}",
        "DecayRun.Source FullInventoryPoint00001",
    )) + "\n"
    zero_text = "\n".join((
        f"Geometry {SF3_SETUP}",
        f"Seed {zero[0]['seed']}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "Run DecayRun",
        f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}",
        f"DecayRun.FileName {active_prefix(zero[0]['job_id'])}",
    )) + "\n"
    validate_source_text(positive_text, positive[0], FRESH_DISPOSITION)
    validate_source_text(zero_text, zero[0], ZERO_DISPOSITION)
    try:
        validate_source_text(
            positive_text.replace("250000", "83334"), positive[0], FRESH_DISPOSITION
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Plan-1 83334 source token was not rejected")

    weakened_zero = dict(zero[0])
    weakened_zero["events"] = FULLSTAT_DELAYED_EVENTS
    try:
        validate_plan_rows([dict(weakened_zero) if row is zero[0] else dict(row) for row in plan])
    except RuntimeError:
        pass
    else:
        raise AssertionError("runner accepted a builder-zero row weakened to 250k")

    synthetic_receipt = {
        "profile_id": PROFILE_ID,
        "job_id": positive[0]["job_id"],
        "stage": positive[0]["stage"],
        "geometry": "SF3",
        "mode": "delayed",
        "family": positive[0]["family"],
        "registered_events": FULLSTAT_DELAYED_EVENTS,
        "events": FULLSTAT_DELAYED_EVENTS,
        "actual_transport_events": FULLSTAT_DELAYED_EVENTS,
        "seed": positive[0]["seed"],
        "setup_path": str(SF3_SETUP),
        "source_status": positive[0]["source_status"],
        "execution_disposition": FRESH_DISPOSITION,
        "transport_eligible": True,
        "seed_namespace": SEED_NAMESPACE,
        "plan1_83334_role": PLAN1_DELAYED_ROLE,
        "incremental_merge_allowed": False,
        "receipt_namespace": str(FULLSTAT_RECEIPT_ROOT),
        "isotope_dat_path": None,
        "sim_header": {
            "geometry": str(SF3_SETUP),
            "seed": positive[0]["seed"],
            "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST",
        },
        "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
    }
    if receipt_contract_errors(synthetic_receipt, positive[0]):
        raise AssertionError("builder/runner in-memory receipt schema interface differs")
    queued = transport_queue_rows(plan)
    if len(queued) != len(positive) or any(row["events"] != 250_000 for row in queued):
        raise AssertionError("builder/runner in-memory positive-only queue interface differs")

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

    policy = {
        "adaptive_min_workers": 4,
        "adaptive_live_target_workers": 6,
        "aggressive_extra_worker_cooldown_seconds": 30,
        "aggressive_min_swap_free_bytes": MIN_SWAP_FREE_BYTES,
        "significant_swap_pages_per_second": 2048,
        "memory_psi_some_avg10_limit": 10.0,
        "memory_psi_full_avg10_limit": 2.0,
    }
    healthy = {
        "evidence_available": True,
        "swap_free_bytes": 10 * 1024**3,
        "thrashing_detected": False,
    }
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
        raise AssertionError("adaptive 4-to-6 worker decision fixture failed")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_FRESH250K_DELAYED_CONTROLLER_STATIC_SELF_TEST",
        "checks": [
            "fixed_fullstat_activation_source_plan_seed_namespaces",
            "exactly_8_registered_families",
            "positive_A15_fresh_complete_250000_only",
            "zero_A15_skip_contract",
            "Plan1_83334_and_166666_source_tokens_rejected",
            "separate_run_and_receipt_namespaces",
            "CLI_cpu_budget_4_5_or_6_with_hard_cap_6",
            "adaptive_workers_4_through_6_and_worker_7_rejected",
            "MemAvailable_1p5GiB_SwapFree_8GiB_dynamic_disk_8GiB",
        ],
        "required_activation_status": FULLSTAT_ACTIVATION_STATUS,
        "fresh_triggers_per_positive_family": FULLSTAT_DELAYED_EVENTS,
        "registered_families": len(FAMILIES),
        "cpu_budget_default": CPU_BUDGET,
        "cpu_budget_cli_allowed": [4, 5, 6],
        "memory_headroom_floor_bytes": MIN_MEMORY_HEADROOM_BYTES,
        "swap_free_floor_bytes": MIN_SWAP_FREE_BYTES,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "run_root": str(FULLSTAT_RUN_ROOT),
        "receipt_root": str(FULLSTAT_RECEIPT_ROOT),
        "production_artifacts_accessed": False,
        "SIM_accessed": False,
        "Plan1_83334_accessed": False,
        "transport_launched": False,
    }


def load_environment() -> dict[str, str]:
    if SOURCE_WORKTREE.resolve() != Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon").resolve():
        raise RuntimeError("Cosima cwd drifted from frozen 104d worktree")
    if not COSIMA.is_file() or not MEGALIB_ENV.is_file():
        raise FileNotFoundError("Cosima executable or MEGAlib environment is missing")
    env = base.load_megalib_environment()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    return env


def transport_queue_rows(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jobs = [
        row for row in plan
        if row["execution_disposition"] == FRESH_DISPOSITION
        and row["transport_eligible"] is True
    ]
    if any(
        row["registered_events"] != FULLSTAT_DELAYED_EVENTS
        or row["events"] != FULLSTAT_DELAYED_EVENTS
        or row["actual_transport_events"] != FULLSTAT_DELAYED_EVENTS
        for row in jobs
    ):
        raise RuntimeError("non-fresh-250k row entered the full-stat delayed queue")
    return jobs


def run_delayed(plan: list[dict[str, Any]], env: dict[str, str], cpu_budget: int) -> None:
    jobs = [
        row for row in transport_queue_rows(plan)
        if load_receipt(row["job_id"]) is None
    ]
    jobs.sort(key=lambda row: row["ordinal"])
    base.run_job_queue(plan, env, jobs, cpu_budget, "fullstat_delayed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--phase", choices=("delayed",))
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
    plan = list(_runtime_plan)
    FULLSTAT_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = FULLSTAT_RUN_ROOT / "controller.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another full-stat delayed controller holds {lock_path}") from exc
        gate = check_prerequisites(requested_cpu_budget=args.cpu_budget)
        if not gate["ready"]:
            raise RuntimeError(json.dumps(gate, indent=2, sort_keys=True))
        plan = list(_runtime_plan)
        refresh_aggregate(plan)
        env = load_environment()
        run_delayed(plan, env, args.cpu_budget)
        aggregate = refresh_aggregate(plan)
    print(json.dumps({
        "status": aggregate["status"],
        "phase": "delayed",
        "aggregate": str(FULLSTAT_AGGREGATE_RECEIPT),
        "transport_namespace": str(FULLSTAT_RUN_ROOT),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        base._stop.set()
        raise
