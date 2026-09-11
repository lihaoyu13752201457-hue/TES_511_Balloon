#!/usr/bin/env python3
"""Close the conditional SF3 full-stat chain from compact authorities only.

This terminal adapter consumes the fixed full-stat stage 01/02/03/04/06
CSV/JSON products plus aggregate receipt metadata and the independent resource
timeline audit.  It never follows a SIM path, opens/stats/hashes a SIM, launches
transport, or creates a second top-up decision.  The sole top-up authorization
is the already-completed Plan-1 central ``F3_SF3/F3_SE3 <= 0.75`` entry gate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import analyze_sf3_fullstat_delayed as stage03
import build_sf3_fullstat_activation as stage02
import build_sf3_fullstat_common_response as stage04
import build_sf3_fullstat_mission as stage06
import build_sf3_fullstat_topup as topup
import run_sf3_fullstat_prompt_analysis as stage01
from sf3_plan1_common import (
    DYNAMIC_RESERVE_BYTES,
    FAMILIES,
    FULLSTAT_DELAYED_EVENTS,
    FULLSTAT_INCREMENT_SHARDS,
    PACKAGE_ROOT,
    S3D_HISTORIES,
    SHARDS,
)


HERE = Path(__file__).resolve()
OUTPUT = PACKAGE_ROOT / "outputs/fullstat/07_final_audit"
RESOURCE_AUDIT = PACKAGE_ROOT / "audit/sf3_fullstat_resource_timeline.json"

PLAN1_MISSION = PACKAGE_ROOT / "outputs/06_mission/summary.json"
PLAN1_CLOSURE = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"
PLAN1_SIGNAL = PACKAGE_ROOT / "outputs/04_common_response/signal_acceptance_effective_area.csv"
TOPUP_STATIC = topup.STATIC_AUDIT
TOPUP_AGGREGATE = topup.TOPUP_AGGREGATE_RECEIPT

STAGE01 = stage01.OUTPUT
STAGE02 = stage02.OUTPUT_ROOT
STAGE03 = stage03.OUTPUT_ROOT
STAGE04 = stage04.OUTPUT
STAGE06 = stage06.OUTPUT
ACTIVATION_VALIDATION = stage02.ACTIVATION_VALIDATION
DELAYED_AGGREGATE = stage02.FULLSTAT_DELAYED_AGGREGATE

PROFILE_ID = "SF3_FULLSTAT_TERMINAL_AUDIT_V1"
READY_STATUS = "READY__SF3_FULLSTAT_TERMINAL_AUDIT_SMALL_AUTHORITIES"
PASS_STATUS = "PASS__SF3_FULLSTAT_CHAIN_COMPLETE__TERMINAL_NO_SECOND_TOPUP"
NOT_READY_STATUS = "NOT_READY__SF3_FULLSTAT_TERMINAL_AUDIT_FUTURE_AUTHORITIES"
FAIL_STATUS = "FAIL__SF3_FULLSTAT_TERMINAL_AUDIT_CONTRACT"
RESOURCE_STATUS = "PASS__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_COMPLETE"
RESOURCE_PROFILE = "SF3_FULLSTAT_RESOURCE_TIMELINE_V1"
RESOURCE_SCOPE = "SF3_FULLSTAT_49_BACKGROUND_FRESH250K_DELAYED_AND_FIVE_GUARDED_HEAVY_STEPS"
RESOURCE_MANIFEST_STATUS = "PASS__SF3_FULLSTAT_CRASH_SAFE_FOLLOWUP_EXECUTION_MANIFEST_PREPARED"
RESOURCE_WRITE_CONTRACT = "ATOMIC_HARDLINK_PUBLICATION__WRITE_ONCE"
RESOURCE_GUARDED_PHASES = {
    "transport_topup": "FULLSTAT_TOPUP_TRANSPORT",
    "build_fullstat_prompt": "FULLSTAT_PROMPT_ANALYSIS",
    "transport_fullstat_delayed": "FULLSTAT_DELAYED_TRANSPORT",
    "analyze_fullstat_delayed": "FULLSTAT_DELAYED_ANALYSIS",
    "build_fullstat_common_response": "FULLSTAT_COMMON_RESPONSE",
}
RESOURCE_ALLOWED_QUOTAS = [300, 400]
RESOURCE_NORMAL_COMPLETION_MODE = "NORMAL_STAGE_RETURNCODE_ZERO"
RESOURCE_RECOVERED_COMPLETION_MODE = "RECOVERED_FROM_WAL_AND_ORIGINAL_GUARD_CLOSURE"
RESOURCE_COMPLETION_AUTHORITIES = {
    "transport_topup": (
        "audit/sf3_fullstat_topup_transport_receipts.json",
        "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
        None,
    ),
    "build_fullstat_prompt": (
        "outputs/fullstat/01_prompt/summary.json",
        "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
        "outputs/fullstat/01_prompt/manifest.json",
    ),
    "transport_fullstat_delayed": (
        "audit/sf3_fullstat_delayed_transport_receipts.json",
        "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
        None,
    ),
    "analyze_fullstat_delayed": (
        "outputs/fullstat/03_delayed/summary.json",
        "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "outputs/fullstat/03_delayed/manifest.json",
    ),
    "build_fullstat_common_response": (
        "outputs/fullstat/04_common_response/summary.json",
        "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
        "outputs/fullstat/04_common_response/manifest.json",
    ),
}
TERMINAL_DECISION = stage06.TERMINAL_DECISION

EXPECTED_BACKGROUND_JOBS = 49
EXPECTED_INSTANT_JOBS = 26
EXPECTED_BUILDUP_JOBS = 23
EXPECTED_INSTANT_HISTORIES = sum(S3D_HISTORIES[("instant", family)] for family in FAMILIES)
EXPECTED_BUILDUP_HISTORIES = sum(S3D_HISTORIES[("buildup", family)] for family in FAMILIES)
EXPECTED_SIGNAL_TRIALS = 37_194
EXPECTED_NODES_PER_GEOMETRY = 81
EXPECTED_TIMELINE_ROWS = 162
MEMORY_FLOOR_BYTES = int(1.5 * 1024**3)
SWAP_FLOOR_BYTES = 8 * 1024**3
MAX_SMALL_BYTES = 128 * 1024**2
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def json_text(value: Any) -> str:
    return json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ) + "\n"


def csv_text(
    rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None
) -> str:
    names = list(fields or (tuple(rows[0]) if rows else ()))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name) for name in names})
    return stream.getvalue()


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def close(
    actual: Any,
    expected: Any,
    *,
    rel: float = 2.0e-11,
    absolute: float = 2.0e-11,
) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute)
    except (TypeError, ValueError):
        return False


def as_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer field")
    parsed = float(value)
    if not math.isfinite(parsed) or not parsed.is_integer():
        raise ValueError(f"not an exact finite integer: {value!r}")
    return int(parsed)


def as_float(value: Any) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"not finite: {value!r}")
    return parsed


def as_bool(value: Any) -> bool:
    if value is True or value == 1 or str(value).strip().lower() == "true":
        return True
    if value is False or value == 0 or str(value).strip().lower() == "false":
        return False
    raise ValueError(f"not a boolean: {value!r}")


def parse_offset_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def is_offset_timestamp(value: Any) -> bool:
    return parse_offset_timestamp(value) is not None


def is_lower_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def reject_sim_path(path: Path) -> None:
    lowered = str(path).lower()
    if lowered.endswith(SIM_SUFFIXES):
        raise RuntimeError(f"SIM path rejected before filesystem query: {path}")


def sha256_small(path: Path, *, limit: int = MAX_SMALL_BYTES) -> str:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > limit:
        raise RuntimeError(f"small authority empty/oversized: {path} ({size} bytes)")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def small_record(path: Path, *, limit: int = MAX_SMALL_BYTES) -> dict[str, Any]:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > limit:
        raise RuntimeError(f"small authority empty/oversized: {path} ({size} bytes)")
    return {"path": norm(path), "bytes": size, "sha256": sha256_small(path, limit=limit)}


def load_small_json(path: Path) -> dict[str, Any]:
    reject_sim_path(path)
    record = small_record(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    del record
    return value


def load_small_csv(path: Path) -> list[dict[str, str]]:
    reject_sim_path(path)
    small_record(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader)


class Checker:
    def __init__(self) -> None:
        self.missing: list[str] = []
        self.errors: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def json(self, label: str, path: Path) -> dict[str, Any] | None:
        reject_sim_path(path)
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_json(path)
            self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def csv(self, label: str, path: Path) -> list[dict[str, str]] | None:
        reject_sim_path(path)
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_csv(path)
            self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def code(self, label: str, path: Path) -> None:
        reject_sim_path(path)
        if not path.is_file():
            self.errors.append(f"locked code authority missing {label}:{norm(path)}")
            return
        try:
            self.authorities[label] = small_record(path)
        except Exception as exc:
            self.errors.append(f"locked code authority invalid {label}: {exc}")


JSON_PATHS = {
    "plan1_mission": PLAN1_MISSION,
    "plan1_closure": PLAN1_CLOSURE,
    "topup_static": TOPUP_STATIC,
    "topup_aggregate": TOPUP_AGGREGATE,
    "full01_summary": STAGE01 / "summary.json",
    "full01_manifest": STAGE01 / "manifest.json",
    "full02_summary": STAGE02 / "day15_summary.json",
    "full02_manifest": STAGE02 / "manifest.json",
    "full02_passive_w": STAGE02 / "passive_w_activation_summary.json",
    "full02_validation": ACTIVATION_VALIDATION,
    "full03_summary": STAGE03 / "summary.json",
    "full03_manifest": STAGE03 / "manifest.json",
    "full03_aggregate": DELAYED_AGGREGATE,
    "full04_summary": STAGE04 / "summary.json",
    "full04_manifest": STAGE04 / "manifest.json",
    "full06_summary": STAGE06 / "summary.json",
    "full06_manifest": STAGE06 / "manifest.json",
    "fullstat_resource_timeline": RESOURCE_AUDIT,
}

CSV_PATHS = {
    "plan1_signal_acceptance": PLAN1_SIGNAL,
    "full01_input_manifest": STAGE01 / "fullstat_prompt_input_manifest.csv",
    "full01_cell_coverage": STAGE01 / "fullstat_prompt_cell_coverage.csv",
    "full01_w_diagnostics": STAGE01 / "fullstat_prompt_w_diagnostics.csv",
    "full02_buildup_manifest": STAGE02 / "buildup_input_manifest.csv",
    "full02_activation_cells": STAGE02 / "activation_cells.csv",
    "full02_inventory": STAGE02 / "day15_inventory.csv",
    "full02_source_index": STAGE02 / "delayed_source_index.csv",
    "full03_coverage": STAGE03 / "delayed_cell_coverage.csv",
    "full03_w_diagnostics": STAGE03 / "delayed_w_diagnostics.csv",
    "full04_cutflow": STAGE04 / "common_cutflow.csv",
    "full04_occupancy": STAGE04 / "common_fullband_occupancy.csv",
    "full04_lineage": STAGE04 / "selected_background_w2_lineage.csv",
    "full04_signal": STAGE04 / "signal_acceptance_effective_area.csv",
    "full04_zero_provenance": STAGE04 / "delayed_zero_A15_provenance.csv",
    "full04_passive_w": STAGE04 / "passive_w_diagnostics.csv",
    "full06_timeline": STAGE06 / "mission_timeline.csv",
    "full06_comparison": STAGE06 / "frozen47_se3_vs_sf3_fullstat_mission.csv",
}


def validate_stage_statuses(
    payloads: dict[str, dict[str, Any] | None], check: Checker
) -> dict[str, Any]:
    expected = {
        "full01": stage01.FULLSTAT_PROFILE_ID,
        "full02": stage02.FULLSTAT_STATUS,
        "full03": stage03.PASS_STATUS,
        "full04": stage04.STATUS,
        "full06": stage06.STATUS,
    }
    observed: dict[str, Any] = {}
    pairs = {
        "full01": (payloads.get("full01_summary"), payloads.get("full01_manifest"), "PASS__SF3_FULLSTAT_PROMPT_COMPLETE"),
        "full02": (payloads.get("full02_summary"), payloads.get("full02_manifest"), stage02.FULLSTAT_STATUS),
        "full03": (payloads.get("full03_summary"), payloads.get("full03_manifest"), stage03.PASS_STATUS),
        "full04": (payloads.get("full04_summary"), payloads.get("full04_manifest"), stage04.STATUS),
        "full06": (payloads.get("full06_summary"), payloads.get("full06_manifest"), stage06.STATUS),
    }
    for name, (summary, manifest, status) in pairs.items():
        if summary is None or manifest is None:
            observed[name] = {"ready": False, "expected_status": status}
            continue
        check.expect(summary.get("status") == status, f"{name} summary status differs")
        check.expect(manifest.get("status") == status, f"{name} manifest status differs")
        check.expect(manifest.get("status") == summary.get("status"), f"{name} manifest/summary status differs")
        observed[name] = {
            "ready": summary.get("status") == status and manifest.get("status") == status,
            "expected_status": status,
            "observed_status": summary.get("status"),
        }
    validation = payloads.get("full02_validation")
    if validation is not None:
        check.expect(
            validation.get("status") == stage02.FULLSTAT_VALIDATION_STATUS,
            "full02 activation validation status differs",
        )
        observed["full02_validation"] = {
            "ready": validation.get("status") == stage02.FULLSTAT_VALIDATION_STATUS,
            "expected_status": stage02.FULLSTAT_VALIDATION_STATUS,
            "observed_status": validation.get("status"),
        }
    aggregate = payloads.get("full03_aggregate")
    if aggregate is not None:
        check.expect(
            aggregate.get("status") == "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
            "full03 delayed aggregate status differs",
        )
        observed["full03_transport"] = {
            "ready": aggregate.get("status") == "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
            "expected_status": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
            "observed_status": aggregate.get("status"),
        }
    del expected
    return observed


def expected_namespace_shards(mode: str, family: str) -> dict[str, tuple[int, ...]]:
    return {
        "PLAN1_CANONICAL_PASS": tuple(SHARDS[(mode, family)]),
        (
            "FULLSTAT_TOPUP_NEW"
            if mode == "instant"
            else "FULLSTAT_TOPUP_CANONICAL_PASS"
        ): tuple(FULLSTAT_INCREMENT_SHARDS[(mode, family)]),
    }


def validate_background_contract(
    instant: Sequence[dict[str, Any]],
    buildup: Sequence[dict[str, Any]],
    check: Checker,
) -> list[dict[str, Any]]:
    check.expect(len(instant) == EXPECTED_INSTANT_JOBS, "fullstat instant receipt-metadata rows != 26")
    check.expect(len(buildup) == EXPECTED_BUILDUP_JOBS, "fullstat buildup receipt-metadata rows != 23")
    all_rows = [("instant", row) for row in instant] + [("buildup", row) for row in buildup]
    job_ids: list[str] = []
    closure: list[dict[str, Any]] = []
    for mode, rows in (("instant", instant), ("buildup", buildup)):
        for row in rows:
            job_id = str(row.get("job_id", ""))
            job_ids.append(job_id)
            check.expect(bool(job_id), f"{mode} receipt metadata has empty job_id")
            check.expect(str(row.get("geometry", "SF3")) == "SF3", f"{mode} metadata is not SF3")
            if row.get("mode") not in (None, "", mode):
                check.errors.append(f"{mode} metadata mode differs for {job_id}")
            check.expect(str(row.get("family", "")) in FAMILIES, f"{mode} metadata family differs for {job_id}")
            try:
                check.expect(as_int(row.get("events")) > 0, f"{mode} events are nonpositive for {job_id}")
            except Exception as exc:
                check.errors.append(f"{mode} events invalid for {job_id}: {exc}")
        for family in FAMILIES:
            cell = [row for row in rows if row.get("family") == family]
            observed_total = sum(as_int(row["events"]) for row in cell)
            target = S3D_HISTORIES[(mode, family)]
            check.expect(observed_total == target, f"fullstat {mode}/{family} histories differ")
            expected_by_namespace = expected_namespace_shards(mode, family)
            for namespace, shards in expected_by_namespace.items():
                observed = sorted(
                    as_int(row["events"])
                    for row in cell
                    if row.get("source_namespace") == namespace
                )
                check.expect(
                    observed == sorted(shards),
                    f"append-only shard multiset differs {mode}/{family}/{namespace}",
                )
            check.expect(
                len(cell) == sum(len(parts) for parts in expected_by_namespace.values()),
                f"fullstat {mode}/{family} job count differs",
            )
            closure.append(
                {
                    "geometry": "SF3",
                    "mode": mode,
                    "family": family,
                    "jobs": len(cell),
                    "histories": observed_total,
                    "S3d_fullstat_target": target,
                    "closure": "PASS" if observed_total == target else "FAIL",
                    "pooling_boundary": "SF3_X_MODE_X_FAMILY_ONLY",
                }
            )
    check.expect(len(job_ids) == len(set(job_ids)), "combined 49 background job IDs are not unique")
    check.expect(len(all_rows) == EXPECTED_BACKGROUND_JOBS, "combined background jobs != 49")
    check.expect(
        sum(as_int(row["events"]) for row in instant) == EXPECTED_INSTANT_HISTORIES,
        "fullstat instant total histories differ",
    )
    check.expect(
        sum(as_int(row["events"]) for row in buildup) == EXPECTED_BUILDUP_HISTORIES,
        "fullstat buildup total histories differ",
    )
    check.expect(
        Counter(str(row.get("source_namespace")) for row in instant)
        == Counter({"PLAN1_CANONICAL_PASS": 11, "FULLSTAT_TOPUP_NEW": 15}),
        "instant append-only namespace closure is not 11+15",
    )
    check.expect(
        Counter(str(row.get("source_namespace")) for row in buildup)
        == Counter({"PLAN1_CANONICAL_PASS": 10, "FULLSTAT_TOPUP_CANONICAL_PASS": 13}),
        "buildup append-only namespace closure is not 10+13",
    )
    return closure


def normalize_source_cells(
    source_rows: Sequence[dict[str, Any]], check: Checker
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    check.expect(len(source_rows) == 8, "fullstat delayed source index does not register 8 families")
    source_map = {str(row.get("incident_family")): row for row in source_rows}
    check.expect(set(source_map) == set(FAMILIES), "fullstat delayed source-index family closure differs")
    check.expect(len(source_map) == len(source_rows), "fullstat delayed source-index families duplicate")
    output: list[dict[str, Any]] = []
    positive: list[str] = []
    zero: list[str] = []
    upper_constant = stage03.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER
    for family in FAMILIES:
        row = source_map.get(family)
        if row is None:
            continue
        disposition = str(row.get("execution_disposition", ""))
        try:
            registered = as_int(row.get("registered_decay_triggers"))
            actual = as_int(row.get("actual_transport_triggers"))
            eligible = as_bool(row.get("transport_eligible"))
            activity = as_float(row.get("transported_ground_activity_Bq"))
        except Exception as exc:
            check.errors.append(f"fullstat delayed source cell invalid {family}: {exc}")
            continue
        check.expect(registered == FULLSTAT_DELAYED_EVENTS, f"registered delayed triggers !=250k {family}")
        record: dict[str, Any] = {
            "geometry": "SF3",
            "family": family,
            "execution_disposition": disposition,
            "registered_triggers": registered,
            "actual_transport_triggers": actual,
            "transport_eligible": eligible,
            "transported_ground_activity_Bq": activity,
            "plan1_83334_consumed_or_pooled": False,
        }
        if disposition == stage02.POSITIVE_DISPOSITION:
            positive.append(family)
            check.expect(actual == FULLSTAT_DELAYED_EVENTS, f"positive delayed cell is not fresh250k {family}")
            check.expect(eligible is True, f"positive delayed cell is not transport eligible {family}")
            check.expect(activity > 0.0, f"positive delayed cell activity is not positive {family}")
            record.update(
                {
                    "central_policy": "FRESH_COMPLETE_250000_ONLY",
                    "finite_upper95_rate_s-1": None,
                    "finite_upper95_A15_Bq": None,
                }
            )
        elif disposition == stage02.ZERO_DISPOSITION:
            zero.append(family)
            check.expect(actual == 0, f"zero-A15 delayed cell actual triggers are nonzero {family}")
            check.expect(eligible is False, f"zero-A15 delayed cell is transport eligible {family}")
            check.expect(activity == 0.0, f"zero-A15 delayed activity is nonzero {family}")
            try:
                sum_tt = as_float(row.get("buildup_sum_TT_s"))
                rate_upper = as_float(row.get("transported_ground_rate_upper95_s-1"))
                a15_upper = as_float(row.get("transported_ground_A15_upper95_Bq_conservative"))
                expected = upper_constant / sum_tt
                check.expect(sum_tt > 0.0, f"zero-A15 sumTT is not positive {family}")
                check.expect(rate_upper > 0.0 and close(rate_upper, expected, rel=2e-12, absolute=1e-18), f"zero-A15 finite rate upper differs {family}")
                check.expect(a15_upper > 0.0 and close(a15_upper, rate_upper, rel=2e-12, absolute=1e-18), f"zero-A15 finite A15 upper differs {family}")
                check.expect(bool(str(row.get("zero_A15_upper_provenance", ""))), f"zero-A15 upper provenance absent {family}")
                record.update(
                    {
                        "central_policy": "EXACT_ZERO__NO_TRANSPORT",
                        "buildup_sum_TT_s": sum_tt,
                        "finite_upper95_rate_s-1": rate_upper,
                        "finite_upper95_A15_Bq": a15_upper,
                        "finite_upper_provenance": row.get("zero_A15_upper_provenance"),
                    }
                )
            except Exception as exc:
                check.errors.append(f"zero-A15 finite-upper contract invalid {family}: {exc}")
        else:
            check.errors.append(f"unknown fullstat delayed disposition {family}/{disposition}")
        output.append(record)
    check.expect(len(positive) + len(zero) == 8, "fullstat delayed positive+zero closure !=8")
    return output, positive, zero


def validate_delayed_cross_stage(
    source_rows: Sequence[dict[str, Any]],
    activation_summary: dict[str, Any],
    activation_validation: dict[str, Any],
    aggregate: dict[str, Any],
    delayed_summary: dict[str, Any],
    coverage: Sequence[dict[str, Any]],
    zero_provenance: Sequence[dict[str, Any]],
    check: Checker,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    closure, positive, zero = normalize_source_cells(source_rows, check)
    check.expect(activation_summary.get("selected_buildup_jobs") == 23, "stage02 buildup jobs !=23")
    check.expect(activation_summary.get("selected_buildup_histories") == EXPECTED_BUILDUP_HISTORIES, "stage02 buildup histories differ")
    check.expect(activation_summary.get("registered_delayed_source_cells") == 8, "stage02 registered delayed cells !=8")
    check.expect(activation_summary.get("fresh_delayed_transport_jobs_planned") == len(positive), "stage02 positive delayed count differs")
    check.expect(activation_summary.get("delayed_zero_source_jobs_skipped") == len(zero), "stage02 zero delayed count differs")
    check.expect(activation_summary.get("plan1_83334_consumed_or_merged") is False, "stage02 consumed Plan1 83334")
    check.expect(activation_summary.get("incremental_166666_merge_allowed") is False, "stage02 permits 83334+166666 merge")

    check.expect(activation_validation.get("registered_delayed_source_cells") == 8, "activation validation registered cells !=8")
    check.expect(activation_validation.get("fresh_delayed_transport_jobs") == len(positive), "activation validation positive count differs")
    check.expect(activation_validation.get("zero_A15_skipped_jobs") == len(zero), "activation validation zero count differs")
    check.expect(activation_validation.get("registered_events_per_family") == FULLSTAT_DELAYED_EVENTS, "activation validation registered-event policy differs")
    check.expect(activation_validation.get("plan1_delayed_consumed") is False, "activation validation consumed Plan1 delayed")
    check.expect(activation_validation.get("incremental_83334_plus_166666_merge_allowed") is False, "activation validation permits incremental merge")
    cards = {str(row.get("family")): row for row in activation_validation.get("source_cards") or []}
    check.expect(set(cards) == set(FAMILIES), "activation validation source-card family closure differs")
    for record in closure:
        card = cards.get(record["family"])
        if card is None:
            continue
        check.expect(as_int(card.get("registered_events")) == FULLSTAT_DELAYED_EVENTS, f"activation card registered events differ {record['family']}")
        check.expect(as_int(card.get("actual_transport_events")) == record["actual_transport_triggers"], f"activation card actual events differ {record['family']}")
        check.expect(card.get("execution_disposition") == record["execution_disposition"], f"activation card disposition differs {record['family']}")

    check.expect(aggregate.get("registered_families") == 8, "delayed aggregate registered families !=8")
    check.expect(aggregate.get("positive_A15_families") == positive, "delayed aggregate positive-family order/set differs")
    check.expect(aggregate.get("zero_A15_families") == zero, "delayed aggregate zero-family order/set differs")
    check.expect(aggregate.get("planned_transport_jobs") == len(positive), "delayed aggregate planned jobs differ")
    check.expect(aggregate.get("validated_transport_jobs") == len(positive), "delayed aggregate validated jobs differ")
    check.expect(aggregate.get("fresh_triggers_per_positive_family") == FULLSTAT_DELAYED_EVENTS, "delayed aggregate positive trigger policy differs")
    check.expect(aggregate.get("validated_fresh_triggers") == len(positive) * FULLSTAT_DELAYED_EVENTS, "delayed aggregate total triggers differ")
    check.expect(aggregate.get("zero_A15_jobs_skipped") == len(zero), "delayed aggregate zero skips differ")
    check.expect(aggregate.get("plan1_83334_read") is False, "delayed aggregate read Plan1 83334")
    check.expect(aggregate.get("plan1_83334_pooled") is False, "delayed aggregate pooled Plan1 83334")
    check.expect(aggregate.get("incremental_merge_used") is False, "delayed aggregate used incremental merge")
    receipts = aggregate.get("selected_receipts") or []
    check.expect(len(receipts) == len(positive), "delayed aggregate selected receipt count differs")
    receipt_map = {str(row.get("family")): row for row in receipts}
    check.expect(set(receipt_map) == set(positive), "delayed aggregate receipt-family closure differs")
    for family, receipt in receipt_map.items():
        check.expect(as_int(receipt.get("registered_events")) == FULLSTAT_DELAYED_EVENTS, f"delayed receipt registered events differ {family}")
        check.expect(as_int(receipt.get("events")) == FULLSTAT_DELAYED_EVENTS, f"delayed receipt events differ {family}")
        check.expect(as_int(receipt.get("actual_transport_events")) == FULLSTAT_DELAYED_EVENTS, f"delayed receipt actual events differ {family}")
        check.expect(receipt.get("execution_disposition") == stage02.POSITIVE_DISPOSITION, f"delayed receipt disposition differs {family}")
        check.expect(as_bool(receipt.get("transport_eligible")) is True, f"delayed receipt eligibility differs {family}")
        check.expect(receipt.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", f"delayed receipt SIM digest policy differs {family}")

    check.expect(delayed_summary.get("registered_source_cells") == 8, "stage03 registered source cells !=8")
    check.expect(delayed_summary.get("transport_jobs") == len(positive), "stage03 positive transport jobs differ")
    check.expect(delayed_summary.get("skipped_zero_A15_jobs") == len(zero), "stage03 zero skips differ")
    check.expect(delayed_summary.get("transport_triggers_per_family") == FULLSTAT_DELAYED_EVENTS, "stage03 trigger policy differs")
    check.expect(delayed_summary.get("plan1_83334_read") is False, "stage03 read Plan1 83334")
    check.expect(delayed_summary.get("plan1_83334_pooled") is False, "stage03 pooled Plan1 83334")
    check.expect(delayed_summary.get("incremental_83334_plus_166666_merge_used") is False, "stage03 used incremental merge")
    coverage_map = {str(row.get("family")): row for row in coverage}
    check.expect(set(coverage_map) == set(FAMILIES), "stage03 coverage family closure differs")
    for record in closure:
        row = coverage_map.get(record["family"])
        if row is None:
            continue
        check.expect(row.get("execution_disposition") == record["execution_disposition"], f"stage03 coverage disposition differs {record['family']}")
        check.expect(as_int(row.get("triggers")) == record["actual_transport_triggers"], f"stage03 coverage triggers differ {record['family']}")
        if record["execution_disposition"] == stage02.ZERO_DISPOSITION:
            check.expect(as_float(row.get("central_delayed_rate_cps")) == 0.0, f"stage03 zero central rate differs {record['family']}")
            check.expect("FINITE" in str(row.get("finite_upper_limit_status", "")), f"stage03 finite upper status absent {record['family']}")

    zero_map = {str(row.get("family")): row for row in zero_provenance}
    check.expect(set(zero_map) == set(zero), "stage04 zero-provenance family closure differs")
    for family, row in zero_map.items():
        check.expect(row.get("execution_disposition") == stage02.ZERO_DISPOSITION, f"stage04 zero disposition differs {family}")
        check.expect(as_float(row.get("central_delayed_rate_cps")) == 0.0, f"stage04 zero central delayed rate differs {family}")
        check.expect(as_float(row.get("transported_ground_rate_upper95_s-1")) > 0.0, f"stage04 zero rate upper is not finite-positive {family}")
        check.expect(as_float(row.get("transported_ground_A15_upper95_Bq_conservative")) > 0.0, f"stage04 zero A15 upper is not finite-positive {family}")
        check.expect(as_bool(row.get("stage03_catalog_opened")) is False, f"stage04 opened zero catalog {family}")
        check.expect(as_bool(row.get("SIM_opened")) is False, f"stage04 opened zero SIM {family}")
    return closure, positive, zero


def validate_passive_w(
    prompt_summary: dict[str, Any],
    activation_w: dict[str, Any],
    delayed_summary: dict[str, Any],
    delayed_w_rows: Sequence[dict[str, Any]],
    response_summary: dict[str, Any],
    response_w_rows: Sequence[dict[str, Any]],
    check: Checker,
) -> dict[str, Any]:
    expected = tuple(stage01.PASSIVE_W_VOLUMES)
    policy = prompt_summary.get("active_veto") or {}
    shield = tuple(policy.get("shield_volumes") or ())
    plastic = tuple(policy.get("plastic_volumes") or ())
    active = tuple(policy.get("active_veto_volumes") or ())
    check.expect(len(shield) == 3 and len(set(shield)) == 3, "active BGO veto does not contain exactly 3 volumes")
    check.expect(len(plastic) == 3 and len(set(plastic)) == 3, "active plastic veto does not contain exactly 3 volumes")
    check.expect(len(active) == 6 and len(set(active)) == 6, "active veto does not contain 6 unique volumes")
    check.expect(set(active) == set(shield) | set(plastic), "active veto is not exactly 3 BGO + 3 plastic")
    check.expect(not set(shield) & set(plastic), "BGO and plastic active-veto sets overlap")
    check.expect(tuple(policy.get("passive_w_volumes") or ()) == expected, "stage01 exact passive-W list differs")
    check.expect(not set(active) & set(expected), "one of the three W volumes entered active veto")
    check.expect(policy.get("passive_w_role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage01 passive-W role differs")

    check.expect(activation_w.get("status") == "PASS__EXACT_THREE_SF3_W_VOLUMES_DIAGNOSTIC_AND_PASSIVE", "stage02 passive-W status differs")
    check.expect(tuple(activation_w.get("exact_volume_whitelist") or ()) == expected, "stage02 passive-W whitelist differs")
    check.expect(activation_w.get("passive_w_never_veto") is True, "stage02 permits passive-W veto")
    check.expect(activation_w.get("bgo_veto_members") == 0, "stage02 W entered BGO veto")
    check.expect(activation_w.get("plastic_veto_members") == 0, "stage02 W entered plastic veto")

    delayed_w = delayed_summary.get("passive_w_diagnostics") or {}
    check.expect(tuple(delayed_w.get("passive_w_volumes") or ()) == expected, "stage03 passive-W list differs")
    check.expect("DISJOINT_FROM_SIX_ACTIVE_VETO" in str(delayed_w.get("role", "")), "stage03 passive-W disjoint role absent")
    check.expect(len(delayed_w_rows) == 8, "stage03 passive-W diagnostic rows !=8")
    for row in delayed_w_rows:
        try:
            listed = tuple(json.loads(str(row.get("passive_w_volumes_json", "[]"))))
        except Exception as exc:
            check.errors.append(f"stage03 passive-W JSON invalid: {exc}")
            continue
        check.expect(listed == expected, f"stage03 passive-W row whitelist differs {row.get('family')}")
        check.expect(
            row.get("veto_role")
            in {
                "PASSIVE_DIAGNOSTIC_ONLY__NOT_BGO_OR_PLASTIC_VETO",
                "PASSIVE_DIAGNOSTIC_ONLY__NO_SIM_FOR_ZERO_A15",
            },
            f"stage03 W diagnostic role differs {row.get('family')}",
        )

    response_w = response_summary.get("passive_w") or {}
    check.expect(tuple(response_w.get("volumes") or ()) == expected, "stage04 passive-W list differs")
    check.expect(response_w.get("role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage04 passive-W role differs")
    check.expect(response_w.get("active_veto_members") == 0, "stage04 W entered active veto")
    check.expect(bool(response_w_rows), "stage04 passive-W diagnostics are empty")
    for row in response_w_rows:
        check.expect(row.get("passive_w_role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage04 passive-W table contains nonpassive role")
    return {
        "status": "PASS__EXACT_THREE_W_PASSIVE_AND_DISJOINT_FROM_SIX_ACTIVE_VETO",
        "passive_w_volumes": list(expected),
        "active_bgo_volumes": list(shield),
        "active_plastic_volumes": list(plastic),
        "active_veto_members": len(active),
        "passive_w_active_veto_members": len(set(active) & set(expected)),
    }


def validate_signal_anchor(
    plan1_rows: Sequence[dict[str, Any]],
    full_rows: Sequence[dict[str, Any]],
    response_summary: dict[str, Any],
    mission_summary: dict[str, Any],
    authorities: dict[str, dict[str, Any]],
    check: Checker,
) -> dict[str, Any]:
    plan1_record = authorities.get("plan1_signal_acceptance") or {}
    full_record = authorities.get("full04_signal") or {}
    check.expect(plan1_record.get("sha256") == full_record.get("sha256"), "fullstat signal acceptance is not byte-identical to Plan1 fresh 37194 table")
    check.expect(plan1_record.get("bytes") == full_record.get("bytes"), "fullstat signal acceptance byte size differs from Plan1")
    check.expect(bool(plan1_rows) and bool(full_rows), "signal acceptance table is empty")
    check.expect(plan1_rows == full_rows, "byte-matched signal tables parsed differently")
    for row in full_rows:
        check.expect(row.get("geometry") == "SF3", "fullstat signal table is not SF3")
        check.expect(as_int(row.get("trials")) == EXPECTED_SIGNAL_TRIALS, "fullstat signal trials !=37194")
    signal = response_summary.get("signal") or {}
    final_w2 = signal.get("final_w2") or {}
    check.expect(as_int(final_w2.get("trials")) == EXPECTED_SIGNAL_TRIALS, "stage04 W2 signal trials !=37194")
    check.expect(signal.get("reuse_authority") == stage04.SIGNAL_REUSE_AUTHORITY, "stage04 signal reuse authority differs")
    check.expect(signal.get("semantic_signal_SIM_scans_in_this_adapter") == 0, "stage04 rescanned signal SIM")
    check.expect(signal.get("signal_SIM_or_receipt_artifact_opened_in_this_adapter") is False, "stage04 opened signal SIM/receipt")
    reuse = mission_summary.get("signal_reuse") or {}
    check.expect(reuse.get("status") == "PASS__IDENTICAL_FRESH_SF3_37194_SIGNAL_ACCEPTANCE_SMALL_TABLE", "stage06 signal-reuse status differs")
    check.expect(reuse.get("trials") == EXPECTED_SIGNAL_TRIALS, "stage06 signal trials !=37194")
    check.expect(reuse.get("plan1_sha256") == plan1_record.get("sha256"), "stage06 Plan1 signal hash binding differs")
    check.expect(reuse.get("fullstat_sha256") == full_record.get("sha256"), "stage06 fullstat signal hash binding differs")
    check.expect(reuse.get("fresh_signal_transport_rerun_for_fullstat") is False, "stage06 claims a fullstat signal rerun")
    return {
        "status": "PASS__PLAN1_FRESH_37194_SIGNAL_ACCEPTANCE_BYTE_HASH_ANCHORED",
        "trials": EXPECTED_SIGNAL_TRIALS,
        "plan1_path": plan1_record.get("path"),
        "fullstat_path": full_record.get("path"),
        "bytes": full_record.get("bytes"),
        "sha256": full_record.get("sha256"),
        "signal_SIM_or_receipt_opened_by_finalizer": False,
        "fullstat_signal_transport_rerun": False,
    }


def validate_plan1_entry_gate(
    mission: dict[str, Any],
    closure: dict[str, Any],
    static: dict[str, Any],
    topup_receipts: dict[str, Any],
    fullstat_mission: dict[str, Any],
    authorities: dict[str, dict[str, Any]],
    check: Checker,
) -> dict[str, Any]:
    gate = mission.get("fullstat_gate") or {}
    ratio = as_float(gate.get("observed_central_ratio"))
    check.expect(mission.get("status") == "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE", "Plan1 mission gate status differs")
    check.expect(gate.get("metric") == "F3_SF3_over_SE3_full_envelope", "Plan1 entry metric differs")
    check.expect(gate.get("operator") == "<=", "Plan1 entry operator differs")
    check.expect(close(gate.get("threshold"), 0.75, rel=0.0, absolute=0.0), "Plan1 entry threshold differs")
    check.expect(0.0 <= ratio <= 0.75, "Plan1 central ratio does not authorize fullstat")
    check.expect(gate.get("topup_required") is True, "Plan1 gate did not require topup")
    check.expect(gate.get("decision") == "TOPUP_TO_S3D_FULL_STAT_REQUIRED", "Plan1 gate decision differs")
    check.expect(gate.get("proxy_controls_gate") is False, "Plan1 proxy controls entry gate")
    check.expect(str(closure.get("status", "")).startswith("PASS__SF3_PLAN1_CHAIN_COMPLETE"), "Plan1 closure is not PASS")
    check.expect(closure.get("ready") is True and closure.get("errors") == [] and closure.get("missing") == [], "Plan1 closure is not clean/ready")
    check.expect(nested(closure, "fullstat_disposition", "topup_required") is True, "Plan1 closure does not retain topup decision")
    check.expect(close(nested(closure, "fullstat_disposition", "observed_central_ratio"), ratio), "Plan1 mission/closure gate ratio differs")
    check.expect(static.get("status") == "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED", "topup static status differs")
    check.expect(nested(static, "plan", "jobs") == 28, "topup static plan jobs !=28")
    check.expect(nested(static, "aggregation", "combined_jobs") == 49, "topup static combined jobs !=49")
    check.expect(static.get("plan1_mutation") is False, "topup static mutated Plan1")
    check.expect(nested(static, "transport", "launched") is False, "topup static launched transport")
    check.expect(nested(static, "gate_authorization", "mission_sha256") == nested(authorities, "plan1_mission", "sha256"), "topup static Plan1 mission hash binding differs")
    check.expect(nested(static, "gate_authorization", "closure_sha256") == nested(authorities, "plan1_closure", "sha256"), "topup static Plan1 closure hash binding differs")
    check.expect(topup_receipts.get("status") == "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS", "topup aggregate status differs")
    check.expect(topup_receipts.get("planned_jobs") == 28 and topup_receipts.get("validated_jobs") == 28, "topup aggregate is not 28/28")
    check.expect(topup_receipts.get("instant_validated_events") == 2_561_382, "topup instant events differ")
    check.expect(topup_receipts.get("buildup_validated_events") == 2_030_976, "topup buildup events differ")

    terminal = fullstat_mission.get("terminal_fullstat_comparison") or {}
    entry = fullstat_mission.get("plan1_entry_gate") or {}
    ratio_contract = fullstat_mission.get("ratio_contract") or {}
    check.expect(entry.get("role") == "ONE_TIME_ENTRY_GATE_ONLY__NOT_REAPPLIED_AFTER_FULLSTAT", "stage06 does not mark Plan1 gate one-time-only")
    check.expect(entry.get("authorized") is True, "stage06 Plan1 entry gate is not authorized")
    check.expect(close(entry.get("observed_central_ratio"), ratio), "stage06 Plan1 entry ratio differs")
    check.expect(ratio_contract.get("phase_gate") == "NONE__FINAL_REPORT", "stage06 terminal phase created a gate")
    check.expect(ratio_contract.get("second_topup_authorized") is False, "stage06 authorized second topup")
    check.expect(terminal.get("second_topup_gate_evaluated") is False, "stage06 evaluated a second topup gate")
    check.expect(terminal.get("second_topup_authorized") is False, "stage06 authorized a second topup")
    check.expect(terminal.get("proxy_controls_any_gate") is False, "stage06 proxy controls a gate")
    check.expect(fullstat_mission.get("second_topup_evaluated_or_launched") is False, "stage06 evaluated/launched second topup")
    return {
        "status": "PASS__PLAN1_CENTRAL_GATE_APPLIED_ONCE_AS_FULLSTAT_ENTRY_ONLY",
        "metric": "central F3_SF3/F3_SE3",
        "operator": "<=",
        "threshold": 0.75,
        "observed_central_ratio": ratio,
        "authorization_evaluation_count": 1,
        "evaluated_phase": "PLAN1_ENTRY_ONLY",
        "proxy_controls_gate": False,
        "reapplied_after_fullstat": False,
    }


def validate_mission(
    summary: dict[str, Any],
    timeline: Sequence[dict[str, Any]],
    comparison: Sequence[dict[str, Any]],
    check: Checker,
) -> dict[str, Any]:
    check.expect(len(timeline) == EXPECTED_TIMELINE_ROWS, "fullstat mission timeline rows !=162")
    geometry_summaries = summary.get("geometries") or {}
    check.expect(set(geometry_summaries) == {"SE3", "SF3"}, "fullstat mission geometry summary closure differs")
    reference_flux = as_float(nested(summary, "mission_contract", "reference_flux_ph_cm2_s"))
    check.expect(close(reference_flux, 1.0e-4, rel=0.0, absolute=0.0), "fullstat mission reference flux differs")
    check.expect(nested(summary, "mission_contract", "time_nodes") == EXPECTED_NODES_PER_GEOMETRY, "mission time nodes !=81")
    terminal_rows: dict[str, dict[str, Any]] = {}
    for geometry in ("SE3", "SF3"):
        rows = [row for row in timeline if row.get("geometry") == geometry]
        check.expect(len(rows) == EXPECTED_NODES_PER_GEOMETRY, f"{geometry} mission nodes !=81")
        try:
            rows = sorted(rows, key=lambda row: as_int(row.get("time_bin_id")))
            check.expect([as_int(row.get("time_bin_id")) for row in rows] == list(range(81)), f"{geometry} mission node IDs differ")
            days = [as_float(row.get("day_mid")) for row in rows]
            check.expect(close(days[0], 0.0, rel=0.0, absolute=1e-12), f"{geometry} mission does not start day0")
            check.expect(close(days[-1], 20.0, rel=0.0, absolute=1e-12), f"{geometry} mission does not end day20")
            check.expect(all(a < b for a, b in zip(days, days[1:])), f"{geometry} mission days are not strictly increasing")
            final = rows[-1]
            terminal_rows[geometry] = final
            item = geometry_summaries[geometry]
            source = as_float(item["source_counts_20d"])
            background = as_float(item["background_counts_20d"])
            source_lower = as_float(item["source_lower95_counts_20d"])
            background_upper = as_float(item["background_upper95_proxy_counts_20d"])
            z = source / math.sqrt(background)
            z_proxy = source_lower / math.sqrt(background_upper)
            check.expect(close(item["Z20d"], z), f"{geometry} central Z arithmetic differs")
            check.expect(close(item["Z20d_componentwise_proxy"], z_proxy), f"{geometry} proxy Z arithmetic differs")
            check.expect(close(item["F3_20d_ph_cm2_s"], reference_flux * 3.0 / z), f"{geometry} central F3 arithmetic differs")
            check.expect(close(item["F3_20d_componentwise_proxy_ph_cm2_s"], reference_flux * 3.0 / z_proxy), f"{geometry} proxy F3 arithmetic differs")
            for timeline_field, summary_field in (
                ("cumulative_source_counts", "source_counts_20d"),
                ("cumulative_background_counts", "background_counts_20d"),
                ("cumulative_source_lower95_counts", "source_lower95_counts_20d"),
                ("cumulative_background_upper95_proxy_counts", "background_upper95_proxy_counts_20d"),
                ("counting_Z", "Z20d"),
                ("counting_Z_componentwise_proxy", "Z20d_componentwise_proxy"),
            ):
                check.expect(close(final[timeline_field], item[summary_field]), f"{geometry} timeline/summary {summary_field} differs")
        except Exception as exc:
            check.errors.append(f"{geometry} 81-node mission contract invalid: {exc}")

    terminal = summary.get("terminal_fullstat_comparison") or {}
    if set(geometry_summaries) == {"SE3", "SF3"}:
        se3 = geometry_summaries["SE3"]
        sf3 = geometry_summaries["SF3"]
        central_ratio = as_float(sf3["F3_20d_ph_cm2_s"]) / as_float(se3["F3_20d_ph_cm2_s"])
        proxy_ratio = as_float(sf3["F3_20d_componentwise_proxy_ph_cm2_s"]) / as_float(se3["F3_20d_componentwise_proxy_ph_cm2_s"])
        check.expect(close(terminal.get("F3_SF3_over_SE3_full_envelope"), central_ratio), "terminal central F3 ratio arithmetic differs")
        check.expect(close(terminal.get("F3_componentwise_proxy_SF3_over_SE3_full_envelope"), proxy_ratio), "terminal proxy F3 ratio arithmetic differs")
    else:
        central_ratio = math.nan
        proxy_ratio = math.nan
    check.expect(terminal.get("decision") == TERMINAL_DECISION, "terminal mission decision differs")
    check.expect(terminal.get("second_topup_gate_evaluated") is False, "terminal mission evaluated second topup")
    check.expect(terminal.get("second_topup_authorized") is False, "terminal mission authorized second topup")
    check.expect(len(comparison) == 2, "terminal comparison rows !=2")
    comparison_map = {str(row.get("geometry")): row for row in comparison}
    check.expect(set(comparison_map) == {"SE3", "SF3"}, "terminal comparison geometry closure differs")
    for geometry, row in comparison_map.items():
        item = geometry_summaries.get(geometry) or {}
        check.expect(close(row.get("F3_20d_ph_cm2_s"), item.get("F3_20d_ph_cm2_s")), f"{geometry} comparison central F3 differs")
        check.expect(close(row.get("F3_20d_componentwise_proxy_ph_cm2_s"), item.get("F3_20d_componentwise_proxy_ph_cm2_s")), f"{geometry} comparison proxy F3 differs")
        check.expect(row.get("terminal_disposition") == TERMINAL_DECISION, f"{geometry} comparison terminal disposition differs")
    return {
        "status": "PASS__162_NODE_CENTRAL_AND_PROXY_ARITHMETIC_CLOSED",
        "timeline_rows": len(timeline),
        "nodes_per_geometry": EXPECTED_NODES_PER_GEOMETRY,
        "central_F3_SF3_over_SE3": central_ratio,
        "componentwise_proxy_F3_SF3_over_SE3": proxy_ratio,
        "terminal_decision": TERMINAL_DECISION,
        "second_topup_gate_evaluated": False,
        "second_topup_authorized": False,
    }


def validate_resource_timeline(
    payload: dict[str, Any], positive_jobs: int, zero_jobs: int, check: Checker
) -> dict[str, Any]:
    expected_labels = list(RESOURCE_GUARDED_PHASES)

    def validate_record(value: Any, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            check.errors.append(f"resource {label} record is not an object")
            return {}
        try:
            path = str(value.get("path", ""))
            check.expect(bool(path) and os.path.isabs(path), f"resource {label} path is absent/non-absolute")
            check.expect(as_int(value.get("bytes")) > 0, f"resource {label} byte record is invalid")
            check.expect(is_lower_sha256(value.get("sha256")), f"resource {label} SHA256 record is invalid")
        except Exception as exc:
            check.errors.append(f"resource {label} record invalid: {exc}")
        return value

    check.expect(payload.get("schema_version") == 1, "resource timeline schema version differs")
    check.expect(payload.get("profile_id") == RESOURCE_PROFILE, "resource timeline profile differs")
    check.expect(payload.get("status") == RESOURCE_STATUS, "resource timeline status differs")
    check.expect(payload.get("scope") == RESOURCE_SCOPE, "resource timeline scope differs")
    check.expect(payload.get("ready") is True, "resource timeline is not ready")
    check.expect(payload.get("pass") is True, "resource actual timeline does not PASS")
    check.expect(is_offset_timestamp(payload.get("checked_at")), "resource checked_at is not an offset timestamp")
    check.expect(is_offset_timestamp(payload.get("built_at")), "resource built_at is not an offset timestamp")
    check.expect(payload.get("write_contract") == RESOURCE_WRITE_CONTRACT, "resource write-once contract differs")
    check.expect(payload.get("configured_cpu_budget_max") == 6, "resource CPU budget ceiling differs from 6")
    check.expect(payload.get("adaptive_workers_min") == 4, "resource adaptive worker minimum differs from 4")
    check.expect(payload.get("adaptive_workers_max") == 6, "resource adaptive worker maximum differs from 6")
    check.expect(payload.get("production_controller_workers") == 4, "resource production worker count differs from 4")
    check.expect(payload.get("mem_available_floor_bytes") == MEMORY_FLOOR_BYTES, "resource MemAvailable floor differs from 1.5GiB")
    check.expect(payload.get("swap_free_floor_bytes") == SWAP_FLOOR_BYTES, "resource SwapFree floor differs from 8GiB")
    check.expect(payload.get("dynamic_disk_reserve_bytes") == DYNAMIC_RESERVE_BYTES, "resource dynamic disk reserve differs from 8GiB")
    check.expect(payload.get("quota_percent_is_worker_count") is False, "resource audit conflates quota_percent with worker count")
    check.expect(payload.get("quota_transition_percent") == [400, 300, 400], "resource quota transition policy differs")
    check.expect(
        payload.get("quota_transition_field_semantics")
        == "NORMAL_THROTTLE_RESTORE_POLICY__300_IS_CONDITIONAL_AND_NEVER_A_WORKER_OR_STATISTICS_COUNT",
        "resource quota transition semantics differ",
    )
    check.expect(payload.get("quota_percent_allowed_values") == RESOURCE_ALLOWED_QUOTAS, "resource exact quota registry differs")
    check.expect(payload.get("safe_all_400_quota_sessions_are_pass_eligible") is True, "resource incorrectly rejects safe all-400 sessions")
    check.expect(payload.get("artificial_throttle_required") is False, "resource incorrectly requires artificial throttling")

    scope_raw = payload.get("job_scope")
    check.expect(isinstance(scope_raw, dict), "resource job_scope is not an object")
    scope = scope_raw if isinstance(scope_raw, dict) else {}
    check.expect(scope.get("plan1_background_jobs") == 21, "resource audit Plan-1 background job scope !=21")
    check.expect(scope.get("topup_background_jobs") == 28, "resource audit top-up job scope !=28")
    check.expect(scope.get("fullstat_background_jobs") == EXPECTED_BACKGROUND_JOBS, "resource audit full-stat background job scope !=49")
    check.expect(scope.get("delayed_registered_families") == 8, "resource audit delayed registered families !=8")
    check.expect(scope.get("delayed_positive_transport_jobs") == positive_jobs, "resource audit delayed positive job count differs")
    check.expect(scope.get("delayed_zero_skips") == zero_jobs, "resource audit delayed zero-skip count differs")
    check.expect(scope.get("total_transport_jobs") == EXPECTED_BACKGROUND_JOBS + positive_jobs, "resource audit total transport job scope differs")
    check.expect(scope.get("Plan1_83334_read_or_pooled") is False, "resource audit consumed/pooled Plan-1 delayed 83334")

    receipt_groups_raw = payload.get("transport_receipt_ids")
    check.expect(isinstance(receipt_groups_raw, dict), "resource transport_receipt_ids is not an object")
    receipt_groups = receipt_groups_raw if isinstance(receipt_groups_raw, dict) else {}
    expected_group_counts = {
        "plan1_background": 21,
        "topup_background": 28,
        "fresh250k_delayed": positive_jobs,
        "zero_A15_skips": zero_jobs,
    }
    normalized_groups: dict[str, list[str]] = {}
    all_receipt_ids: set[str] = set()
    for name, expected_count in expected_group_counts.items():
        values = receipt_groups.get(name) if isinstance(receipt_groups, dict) else None
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            check.errors.append(f"resource receipt identity group is malformed: {name}")
            normalized_groups[name] = []
            continue
        normalized_groups[name] = values
        check.expect(len(values) == expected_count and len(set(values)) == expected_count, f"resource receipt identity count/uniqueness differs: {name}")
        check.expect(values == sorted(values), f"resource receipt identities are not canonical-sorted: {name}")
        check.expect(all_receipt_ids.isdisjoint(values), f"resource receipt identities overlap another namespace: {name}")
        all_receipt_ids.update(values)
    check.expect(set(receipt_groups) == set(expected_group_counts), "resource receipt identity group registry differs")

    authorities_raw = payload.get("input_authorities")
    check.expect(isinstance(authorities_raw, dict), "resource input_authorities is not an object")
    authorities = authorities_raw if isinstance(authorities_raw, dict) else {}
    source = validate_record(payload.get("source_event_log"), "source-event-log")
    wal_log = validate_record(payload.get("guard_session_wal"), "guard-session-WAL")
    completion_log = validate_record(payload.get("resource_completion_event_log"), "resource-completion-event-log")
    manifest_raw = payload.get("followup_manifest_binding")
    check.expect(isinstance(manifest_raw, dict), "resource followup_manifest_binding is not an object")
    manifest = manifest_raw if isinstance(manifest_raw, dict) else {}
    check.expect(bool(str(manifest.get("path", ""))) and os.path.isabs(str(manifest.get("path", ""))), "resource manifest path is absent/non-absolute")
    try:
        check.expect(as_int(manifest.get("bytes")) > 0, "resource manifest byte record is invalid")
    except Exception as exc:
        check.errors.append(f"resource manifest byte record invalid: {exc}")
    check.expect(is_lower_sha256(manifest.get("sha256")), "resource manifest SHA256 record is invalid")
    check.expect(manifest.get("status") == RESOURCE_MANIFEST_STATUS, "resource manifest status differs")
    check.expect(manifest.get("guarded_steps") == expected_labels, "resource manifest guarded-step registry differs")
    manifest_authority = validate_record(
        authorities.get("fullstat_followup_manifest") if isinstance(authorities, dict) else None,
        "input followup manifest",
    )
    source_authority = validate_record(
        authorities.get("fullstat_guard_event_log") if isinstance(authorities, dict) else None,
        "input complete guard log",
    )
    wal_authority = validate_record(
        authorities.get("fullstat_guard_session_wal") if isinstance(authorities, dict) else None,
        "input guard-session WAL",
    )
    completion_authority = validate_record(
        authorities.get("fullstat_resource_completion_log") if isinstance(authorities, dict) else None,
        "input resource completion log",
    )
    check.expect(
        {key: manifest.get(key) for key in ("path", "bytes", "sha256")} == manifest_authority,
        "resource manifest binding differs from input authority",
    )
    check.expect(source == source_authority, "resource source-event-log differs from input authority")
    check.expect(wal_log == wal_authority, "resource guard-session WAL differs from input authority")
    check.expect(completion_log == completion_authority, "resource completion-event-log differs from input authority")

    completion_records_raw = payload.get("guarded_completion_authorities")
    check.expect(isinstance(completion_records_raw, dict), "resource guarded completion authorities is not an object")
    completion_records = completion_records_raw if isinstance(completion_records_raw, dict) else {}
    check.expect(set(completion_records) == set(expected_labels), "resource guarded completion authority labels differ")
    for label in expected_labels:
        relative, expected_status, companion_relative = RESOURCE_COMPLETION_AUTHORITIES[label]
        value = completion_records.get(label)
        if not isinstance(value, dict):
            check.errors.append(f"resource guarded completion authority is not an object: {label}")
            continue
        check.expect(value.get("relative_path") == relative, f"resource guarded completion relative path differs: {label}")
        check.expect(value.get("status") == expected_status, f"resource guarded completion status differs: {label}")
        check.expect(norm(value.get("path", "")) == norm(PACKAGE_ROOT / relative), f"resource guarded completion path differs: {label}")
        try:
            check.expect(as_int(value.get("bytes")) > 0, f"resource guarded completion bytes invalid: {label}")
        except Exception as exc:
            check.errors.append(f"resource guarded completion bytes invalid {label}: {exc}")
        check.expect(is_lower_sha256(value.get("sha256")), f"resource guarded completion digest invalid: {label}")
        input_record = validate_record(
            authorities.get(f"guarded_completion_{label}"),
            f"input guarded completion {label}",
        )
        check.expect(
            {key: value.get(key) for key in ("path", "bytes", "sha256")} == input_record,
            f"resource guarded completion differs from input authority: {label}",
        )
        companion = value.get("companion_manifest")
        if companion_relative is None:
            check.expect(companion is None, f"resource guarded transport authority unexpectedly has a companion manifest: {label}")
            continue
        if not isinstance(companion, dict):
            check.errors.append(f"resource guarded completion companion manifest absent/malformed: {label}")
            continue
        check.expect(companion.get("relative_path") == companion_relative, f"resource guarded companion relative path differs: {label}")
        check.expect(companion.get("status") == expected_status, f"resource guarded companion status differs: {label}")
        check.expect(norm(companion.get("path", "")) == norm(PACKAGE_ROOT / companion_relative), f"resource guarded companion path differs: {label}")
        try:
            check.expect(as_int(companion.get("bytes")) > 0, f"resource guarded companion bytes invalid: {label}")
        except Exception as exc:
            check.errors.append(f"resource guarded companion bytes invalid {label}: {exc}")
        check.expect(is_lower_sha256(companion.get("sha256")), f"resource guarded companion digest invalid: {label}")
        input_companion = validate_record(
            authorities.get(f"guarded_completion_{label}_manifest"),
            f"input guarded completion companion {label}",
        )
        check.expect(
            {key: companion.get(key) for key in ("path", "bytes", "sha256")} == input_companion,
            f"resource guarded companion differs from input authority: {label}",
        )
    check.expect(
        payload.get("all_guarded_completion_authorities_independently_validated") is True,
        "resource guarded completion authorities were not all independently validated",
    )

    check.expect(payload.get("required_guarded_session_labels") == expected_labels, "resource required guarded labels differ")
    check.expect(payload.get("observed_guarded_session_labels") == expected_labels, "resource observed guarded labels differ")
    check.expect(payload.get("exact_session_label_to_phase") == RESOURCE_GUARDED_PHASES, "resource exact label-to-phase registry differs")
    check.expect(payload.get("required_exact_label_stage_coverage") == RESOURCE_GUARDED_PHASES, "resource required exact label-stage coverage differs")
    expected_observed_coverage = {
        label: [phase] for label, phase in RESOURCE_GUARDED_PHASES.items()
    }
    check.expect(payload.get("observed_closed_exact_label_stage_coverage") == expected_observed_coverage, "resource observed exact label-stage coverage differs")
    check.expect(payload.get("all_required_exact_label_stage_bindings_pass") is True, "resource exact label-stage binding did not PASS")

    guard_sessions = payload.get("guard_sessions") or []
    check.expect(isinstance(guard_sessions, list) and len(guard_sessions) == len(expected_labels), "resource selected guard-session registry is not exactly five")
    guard_labels: list[str] = []
    guard_mins_mem: list[int] = []
    guard_mins_swap: list[int] = []
    guard_min_disks: list[int] = []
    guard_completion_mem: list[int] = []
    guard_completion_swap: list[int] = []
    guard_completion_disks: list[int] = []
    completion_modes: list[str] = []
    prior_guard_end = -1
    source_bytes = 0
    try:
        source_bytes = as_int(source.get("bytes"))
    except Exception:
        pass
    for index, row in enumerate(guard_sessions if isinstance(guard_sessions, list) else []):
        if not isinstance(row, dict):
            check.errors.append(f"resource guard session {index} is not an object")
            continue
        try:
            label = str(row.get("session_label", ""))
            guard_labels.append(label)
            check.expect(label in RESOURCE_GUARDED_PHASES, f"resource guard session label is unknown at {index}")
            if label in RESOURCE_GUARDED_PHASES:
                check.expect(row.get("phase") == RESOURCE_GUARDED_PHASES[label], f"resource guard session phase differs: {label}")
            check.expect(as_int(row.get("actual_workers")) == 4, f"resource guard session worker count differs: {label}")
            start = as_int(row.get("guard_log_start_byte"))
            end = as_int(row.get("guard_log_end_byte"))
            check.expect(0 <= start < end <= source_bytes, f"resource guard byte range is outside the complete log: {label}")
            check.expect(start >= prior_guard_end, f"resource guard byte ranges overlap/out-of-order: {label}")
            prior_guard_end = end
            check.expect(as_int(row.get("sample_count")) > 0, f"resource guard session has no sample: {label}")
            sequence = row.get("quota_percent_sequence")
            check.expect(
                isinstance(sequence, list)
                and bool(sequence)
                and all(as_int(value) in RESOURCE_ALLOWED_QUOTAS for value in sequence),
                f"resource guard session quota sequence differs: {label}",
            )
            if isinstance(sequence, list) and sequence:
                check.expect(as_int(sequence[-1]) == 400, f"resource guard session quota sequence does not restore400: {label}")
            check.expect(row.get("quota_values_allowed_exactly_300_or_400") is True, f"resource guard quota registry did not PASS: {label}")
            check.expect(as_int(row.get("terminal_quota_percent")) == 400, f"resource guard terminal quota differs: {label}")
            check.expect(row.get("closure") == "GUARD_EXIT_RESTORE_NORMAL", f"resource guard closure differs: {label}")
            check.expect(row.get("hard_floor_breach_observed") is False, f"resource guard hard-floor breach recorded: {label}")
            mem = as_int(row.get("minimum_mem_available_bytes"))
            swap = as_int(row.get("minimum_swap_free_bytes"))
            disk = as_int(row.get("minimum_disk_free_bytes"))
            completion_mem = as_int(row.get("completion_mem_available_bytes"))
            completion_swap = as_int(row.get("completion_swap_free_bytes"))
            completion_disk = as_int(row.get("completion_disk_free_bytes"))
            guard_mins_mem.append(mem)
            guard_mins_swap.append(swap)
            guard_min_disks.append(disk)
            guard_completion_mem.append(completion_mem)
            guard_completion_swap.append(completion_swap)
            guard_completion_disks.append(completion_disk)
            check.expect(mem >= MEMORY_FLOOR_BYTES, f"resource guard MemAvailable floor failed: {label}")
            check.expect(swap >= SWAP_FLOOR_BYTES, f"resource guard SwapFree floor failed: {label}")
            check.expect(disk >= DYNAMIC_RESERVE_BYTES, f"resource guard disk reserve failed: {label}")
            check.expect(completion_mem >= MEMORY_FLOOR_BYTES, f"resource guard completion MemAvailable floor failed: {label}")
            check.expect(completion_swap >= SWAP_FLOOR_BYTES, f"resource guard completion SwapFree floor failed: {label}")
            check.expect(completion_disk >= DYNAMIC_RESERVE_BYTES, f"resource guard completion disk reserve failed: {label}")
            mode = str(row.get("completion_record_mode", ""))
            completion_modes.append(mode)
            check.expect(
                mode in {RESOURCE_NORMAL_COMPLETION_MODE, RESOURCE_RECOVERED_COMPLETION_MODE},
                f"resource guard completion mode differs: {label}",
            )
            check.expect(is_offset_timestamp(row.get("guard_session_wal_started_at")), f"resource guard WAL timestamp invalid: {label}")
            check.expect(
                row.get("canonical_completion_authority") == completion_records.get(label),
                f"resource guard canonical completion authority binding differs: {label}",
            )
            check.expect(row.get("manifest_sha256") == manifest.get("sha256"), f"resource guard manifest binding differs: {label}")
        except Exception as exc:
            check.errors.append(f"resource guard session {index} invalid: {exc}")
    check.expect(guard_labels == expected_labels, "resource selected guard sessions are missing/duplicated/out-of-order")
    check.expect(payload.get("all_guard_sessions_closed") is True, "resource selected guard sessions are not all closed")
    check.expect(payload.get("all_guard_sessions_exactly_one_clean_closure") is True, "resource selected guard sessions lack exact single clean closure")
    check.expect(payload.get("all_guard_sessions_terminal_quota_400") is True, "resource selected guard sessions do not all terminate at quota400")
    check.expect(payload.get("all_guard_samples_hard_floors_pass") is True, "resource selected guard samples did not all pass hard floors")
    normal_count = sum(mode == RESOURCE_NORMAL_COMPLETION_MODE for mode in completion_modes)
    recovered_count = sum(mode == RESOURCE_RECOVERED_COMPLETION_MODE for mode in completion_modes)
    check.expect(payload.get("normal_completion_records") == normal_count, "resource normal completion-record count differs")
    check.expect(payload.get("crash_recovered_completion_records") == recovered_count, "resource recovered completion-record count differs")
    check.expect(normal_count + recovered_count == len(expected_labels), "resource normal/recovery completion modes do not form an exact five-row XOR")
    check.expect(payload.get("normal_or_crash_recovery_record_XOR_pass") is True, "resource normal/recovery XOR did not PASS")
    check.expect(
        payload.get("all_completion_resources_from_original_guard_closure_not_live_inference") is True,
        "resource completion resources permit live inference",
    )

    complete_guard_raw = payload.get("complete_guard_event_log_audit")
    check.expect(isinstance(complete_guard_raw, dict), "resource complete guard-log audit is not an object")
    complete_guard = complete_guard_raw if isinstance(complete_guard_raw, dict) else {}
    check.expect(complete_guard.get("all_bytes_audited") is True, "resource complete guard-log bytes were not all audited")
    check.expect(complete_guard.get("all_sessions_cleanly_closed") is True, "resource complete guard-log contains an unclean session")
    complete_sessions = complete_guard.get("sessions") or []
    check.expect(isinstance(complete_sessions, list), "resource complete guard-log sessions is not an array")
    complete_labels: list[str] = []
    complete_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    prior_complete_end = 0
    for index, row in enumerate(complete_sessions if isinstance(complete_sessions, list) else []):
        if not isinstance(row, dict):
            check.errors.append(f"resource complete guard-log session {index} is not an object")
            continue
        try:
            label = str(row.get("session_label", ""))
            complete_labels.append(label)
            check.expect(label in RESOURCE_GUARDED_PHASES, f"resource complete guard-log label is unknown: {label}")
            check.expect(as_int(row.get("sample_count")) > 0, f"resource complete guard-log session has no sample: {label}")
            sequence = row.get("quota_percent_sequence")
            check.expect(
                isinstance(sequence, list)
                and bool(sequence)
                and all(as_int(value) in RESOURCE_ALLOWED_QUOTAS for value in sequence),
                f"resource complete guard-log quota sequence differs: {label}",
            )
            if isinstance(sequence, list) and sequence:
                check.expect(as_int(sequence[-1]) == 400, f"resource complete guard-log session does not restore400: {label}")
            check.expect(row.get("closure") == "GUARD_EXIT_RESTORE_NORMAL", f"resource complete guard-log closure differs: {label}")
            start = as_int(row.get("guard_log_start_byte"))
            end = as_int(row.get("guard_log_end_byte"))
            check.expect(start == prior_complete_end and start < end <= source_bytes, f"resource complete guard-log byte partition differs: {label}")
            prior_complete_end = end
            key = (label, start)
            check.expect(key not in complete_by_key, f"resource complete guard-log session key is duplicate: {key}")
            complete_by_key[key] = row
            completion_mem = as_int(row.get("completion_mem_available_bytes"))
            completion_swap = as_int(row.get("completion_swap_free_bytes"))
            completion_disk = as_int(row.get("completion_disk_free_bytes"))
            check.expect(completion_mem >= MEMORY_FLOOR_BYTES, f"resource complete guard-log completion MemAvailable floor failed: {label}")
            check.expect(completion_swap >= SWAP_FLOOR_BYTES, f"resource complete guard-log completion SwapFree floor failed: {label}")
            check.expect(completion_disk >= DYNAMIC_RESERVE_BYTES, f"resource complete guard-log completion disk floor failed: {label}")
            started = parse_offset_timestamp(row.get("started_at"))
            closed = parse_offset_timestamp(row.get("closed_at"))
            check.expect(started is not None and closed is not None and started < closed, f"resource complete guard-log timestamps differ: {label}")
        except Exception as exc:
            check.errors.append(f"resource complete guard-log session {index} invalid: {exc}")
    complete_counts = dict(Counter(complete_labels))
    try:
        complete_count = as_int(complete_guard.get("session_count"))
    except Exception as exc:
        check.errors.append(f"resource complete guard-log session count invalid: {exc}")
        complete_count = -1
    check.expect(complete_count == len(complete_sessions), "resource complete guard-log session-count summary differs")
    check.expect(set(complete_counts) == set(expected_labels) and all(complete_counts.get(label, 0) >= 1 for label in expected_labels), "resource complete guard-log does not cover all five labels")
    check.expect(complete_guard.get("sessions_by_label") == {label: complete_counts.get(label, 0) for label in expected_labels}, "resource complete guard-log by-label summary differs")
    check.expect(payload.get("superseded_or_retried_clean_guard_sessions") == complete_count - len(expected_labels), "resource superseded/retried clean guard-session summary differs")
    check.expect(complete_count >= len(expected_labels), "resource complete guard-log session count is below five")
    check.expect(prior_complete_end == source_bytes, "resource complete guard-log audit does not account for every source byte")

    selected_closure_mem: list[int] = []
    selected_closure_swap: list[int] = []
    selected_closure_disk: list[int] = []
    for row in guard_sessions if isinstance(guard_sessions, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            label = str(row.get("session_label", ""))
            start = as_int(row.get("guard_log_start_byte"))
            complete = complete_by_key.get((label, start))
            check.expect(complete is not None, f"resource selected guard session is absent from the complete byte audit: {label}")
            if complete is None:
                continue
            check.expect(as_int(complete.get("guard_log_end_byte")) == as_int(row.get("guard_log_end_byte")), f"resource selected/complete guard end byte differs: {label}")
            check.expect(as_int(complete.get("sample_count")) == as_int(row.get("sample_count")), f"resource selected/complete guard sample count differs: {label}")
            check.expect(complete.get("quota_percent_sequence") == row.get("quota_percent_sequence"), f"resource selected/complete guard quota sequence differs: {label}")
            completion_mem = as_int(complete.get("completion_mem_available_bytes"))
            completion_swap = as_int(complete.get("completion_swap_free_bytes"))
            completion_disk = as_int(complete.get("completion_disk_free_bytes"))
            selected_closure_mem.append(completion_mem)
            selected_closure_swap.append(completion_swap)
            selected_closure_disk.append(completion_disk)
            check.expect(completion_mem == as_int(row.get("completion_mem_available_bytes")), f"resource selected guard completion does not preserve original closure MemAvailable: {label}")
            check.expect(completion_swap == as_int(row.get("completion_swap_free_bytes")), f"resource selected guard completion does not preserve original closure SwapFree: {label}")
            check.expect(completion_disk == as_int(row.get("completion_disk_free_bytes")), f"resource selected guard completion does not preserve original closure disk: {label}")
            wal_started = parse_offset_timestamp(row.get("guard_session_wal_started_at"))
            guard_started = parse_offset_timestamp(complete.get("started_at"))
            check.expect(wal_started is not None and guard_started is not None and wal_started < guard_started, f"resource selected guard WAL was not durable before the guard session: {label}")
        except Exception as exc:
            check.errors.append(f"resource selected/complete guard binding invalid: {exc}")

    wal_audit_raw = payload.get("guard_session_wal_audit")
    check.expect(isinstance(wal_audit_raw, dict), "resource guard-session WAL audit is not an object")
    wal_audit = wal_audit_raw if isinstance(wal_audit_raw, dict) else {}
    try:
        wal_rows = as_int(wal_audit.get("rows"))
        wal_keys = as_int(wal_audit.get("guard_session_keys"))
        orphan_rows = as_int(wal_audit.get("orphan_pre_guard_crash_rows"))
        check.expect(wal_rows >= 0 and wal_keys == complete_count and orphan_rows >= 0, "resource guard-session WAL count summary differs")
        check.expect(wal_rows >= wal_keys + orphan_rows, "resource guard-session WAL rows cannot cover clean keys plus legal pre-guard orphans")
    except Exception as exc:
        check.errors.append(f"resource guard-session WAL count summary invalid: {exc}")
    check.expect(wal_audit.get("all_clean_guard_sessions_have_write_ahead_start") is True, "resource clean guard sessions lack durable WAL starts")
    check.expect(
        wal_audit.get("duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct") is True,
        "resource WAL duplicate-key/orphan policy differs",
    )

    timeline = payload.get("timeline") or []
    check.expect(isinstance(timeline, list) and bool(timeline), "resource actual timeline is empty")
    workers: list[int] = []
    mem_values: list[int] = []
    swap_values: list[int] = []
    disk_values: list[int] = []
    quota_values: list[int] = []
    timeline_labels: list[str] = []
    for index, row in enumerate(timeline if isinstance(timeline, list) else []):
        if not isinstance(row, dict):
            check.errors.append(f"resource timeline row {index} is not an object")
            continue
        try:
            label = str(row.get("session_label", ""))
            worker = as_int(row.get("actual_workers"))
            quota = as_int(row.get("quota_percent"))
            mem = as_int(row.get("mem_available_bytes"))
            swap = as_int(row.get("swap_free_bytes"))
            disk = as_int(row.get("disk_free_after_projection_bytes"))
            timeline_labels.append(label)
            workers.append(worker)
            quota_values.append(quota)
            mem_values.append(mem)
            swap_values.append(swap)
            disk_values.append(disk)
            check.expect(label in RESOURCE_GUARDED_PHASES, f"resource timeline label is unknown at row {index}")
            if label in RESOURCE_GUARDED_PHASES:
                check.expect(row.get("phase") == RESOURCE_GUARDED_PHASES[label], f"resource timeline phase differs at row {index}")
            check.expect(worker == 4, f"resource actual workers differ from 4 at row {index}")
            check.expect(quota in RESOURCE_ALLOWED_QUOTAS, f"resource quota outside exact 300/400 at row {index}")
            check.expect(row.get("quota_percent_is_worker_count") is False, f"resource timeline conflates quota/workers at row {index}")
            check.expect(mem >= MEMORY_FLOOR_BYTES, f"resource MemAvailable floor failed at row {index}")
            check.expect(swap >= SWAP_FLOOR_BYTES, f"resource SwapFree floor failed at row {index}")
            check.expect(disk >= DYNAMIC_RESERVE_BYTES, f"resource dynamic disk reserve failed at row {index}")
            check.expect(is_offset_timestamp(row.get("at")), f"resource timeline timestamp invalid at row {index}")
            reasons = row.get("decision_reasons")
            check.expect(isinstance(reasons, list) and all(isinstance(reason, str) for reason in reasons), f"resource timeline decision reasons invalid at row {index}")
        except Exception as exc:
            check.errors.append(f"resource timeline row {index} invalid: {exc}")
    observed_workers = sorted(set(workers))
    observed_quotas = sorted(set(quota_values))
    check.expect(set(timeline_labels) == set(expected_labels), "resource timeline does not sample every exact guarded label")
    check.expect(observed_workers == [4], "resource observed actual workers differ from exact worker4")
    check.expect(payload.get("actual_workers_observed") == observed_workers, "resource observed-worker summary differs from timeline")
    check.expect(payload.get("quota_percent_observed") == observed_quotas, "resource observed-quota summary differs from timeline")
    check.expect(bool(observed_quotas) and set(observed_quotas).issubset(RESOURCE_ALLOWED_QUOTAS), "resource observed quota set is empty/outside exact 300/400")
    check.expect(payload.get("timeline_rows") == len(timeline), "resource timeline-row summary differs")
    all_resource_mem_values = mem_values + selected_closure_mem
    all_resource_swap_values = swap_values + selected_closure_swap
    all_resource_disk_values = disk_values + selected_closure_disk
    if mem_values:
        check.expect(payload.get("min_mem_available_bytes") == min(all_resource_mem_values), "resource minimum sampled/closure MemAvailable summary differs")
        check.expect(payload.get("min_swap_free_bytes") == min(all_resource_swap_values), "resource minimum sampled/closure SwapFree summary differs")
        check.expect(payload.get("min_disk_free_after_projection_bytes") == min(all_resource_disk_values), "resource minimum sampled/closure disk summary differs")
        check.expect(not guard_mins_mem or min(guard_mins_mem) == min(mem_values), "resource guard/timeline MemAvailable minima differ")
        check.expect(not guard_mins_swap or min(guard_mins_swap) == min(swap_values), "resource guard/timeline SwapFree minima differ")
        check.expect(not guard_min_disks or min(guard_min_disks) == min(disk_values), "resource guard/timeline sampled disk minima differ")
        check.expect(guard_completion_mem == selected_closure_mem, "resource guard/original-closure MemAvailable snapshots differ")
        check.expect(guard_completion_swap == selected_closure_swap, "resource guard/original-closure SwapFree snapshots differ")
        check.expect(guard_completion_disks == selected_closure_disk, "resource guard/original-closure disk snapshots differ")
        check.expect(payload.get("min_guard_sample_disk_free_bytes") == min(disk_values), "resource guard-sample disk minimum differs")
        check.expect(bool(selected_closure_disk), "resource selected guard closures have no disk snapshots")
        if selected_closure_disk:
            check.expect(payload.get("min_guard_completion_disk_free_bytes") == min(selected_closure_disk), "resource guard-completion disk minimum differs")

    def validate_transport_summary(
        value: Any,
        label: str,
        expected_ids: list[str],
        authority_label: str,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            check.errors.append(f"resource transport completion summary is not an object: {label}")
            return {}
        try:
            namespace = str(value.get("namespace", ""))
            metrics_path = str(value.get("resource_metrics_path", ""))
            check.expect(bool(namespace) and os.path.isabs(namespace), f"resource transport namespace invalid: {label}")
            if expected_ids:
                check.expect(bool(metrics_path) and os.path.isabs(metrics_path), f"resource metrics path invalid: {label}")
                if namespace and metrics_path:
                    check.expect(norm(Path(metrics_path).parent) == norm(namespace), f"resource metrics path leaves namespace: {label}")
            else:
                check.expect(not metrics_path, f"resource zero-job transport unexpectedly names a metrics path: {label}")
            check.expect(value.get("expected_successful_jobs") == len(expected_ids), f"resource expected successful jobs differ: {label}")
            successful = value.get("successful_jobs")
            if not isinstance(successful, list):
                raise ValueError("successful_jobs is not an array")
            successful_ids: list[str] = []
            successful_free: list[int] = []
            for index, row in enumerate(successful):
                if not isinstance(row, dict):
                    raise ValueError(f"successful row {index} is not an object")
                job_id = str(row.get("job_id", ""))
                successful_ids.append(job_id)
                check.expect(as_int(row.get("attempt")) > 0, f"resource successful attempt is nonpositive: {label}/{job_id}")
                check.expect(is_offset_timestamp(row.get("at")), f"resource successful attempt timestamp invalid: {label}/{job_id}")
                check.expect(as_float(row.get("wall_s")) >= 0.0, f"resource successful wall time negative: {label}/{job_id}")
                check.expect(as_int(row.get("peak_rss_bytes")) >= 0, f"resource successful RSS negative: {label}/{job_id}")
                check.expect(as_int(row.get("artifact_bytes")) >= 0, f"resource successful artifact bytes negative: {label}/{job_id}")
                free = as_int(row.get("free_bytes"))
                successful_free.append(free)
                check.expect(free >= DYNAMIC_RESERVE_BYTES, f"resource successful attempt disk reserve failed: {label}/{job_id}")
            check.expect(successful_ids == sorted(expected_ids), f"resource successful receipt identities differ: {label}")
            failed = as_int(value.get("failed_finalized_attempts"))
            total = as_int(value.get("total_finalized_attempts"))
            check.expect(failed >= 0 and total == len(expected_ids) + failed, f"resource finalized attempt counts differ: {label}")
            check.expect(value.get("dynamic_disk_reserve_bytes") == DYNAMIC_RESERVE_BYTES, f"resource transport reserve constant differs: {label}")
            check.expect(value.get("all_finalized_attempts_reserve_pass") is True, f"resource finalized attempt reserve did not PASS: {label}")
            check.expect(value.get("all_canonical_receipts_have_exactly_one_pass_metric") is True, f"resource canonical receipt PASS metrics did not close: {label}")
            if expected_ids:
                minimum = as_int(value.get("min_free_bytes"))
                check.expect(minimum >= DYNAMIC_RESERVE_BYTES, f"resource transport minimum disk reserve failed: {label}")
                check.expect(bool(successful_free) and minimum <= min(successful_free), f"resource transport minimum exceeds successful minima: {label}")
                if failed == 0:
                    check.expect(minimum == min(successful_free), f"resource no-failure transport minimum differs: {label}")
                metric_authority = validate_record(
                    authorities.get(authority_label) if isinstance(authorities, dict) else None,
                    f"input {label} resource metrics",
                )
                check.expect(metric_authority.get("path") == metrics_path, f"resource metrics path differs from input authority: {label}")
            else:
                check.expect(value.get("min_free_bytes") is None, f"resource zero-job transport minimum must be null: {label}")
                check.expect(successful == [] and failed == 0 and total == 0, f"resource zero-job transport summary differs: {label}")
                check.expect(value.get("zero_positive_transport_disposition") is True, f"resource zero-positive transport disposition differs: {label}")
        except Exception as exc:
            check.errors.append(f"resource transport completion summary invalid {label}: {exc}")
        return value

    transport_metrics_raw = payload.get("transport_completion_disk_metrics")
    check.expect(isinstance(transport_metrics_raw, dict), "resource transport_completion_disk_metrics is not an object")
    transport_metrics = transport_metrics_raw if isinstance(transport_metrics_raw, dict) else {}
    topup_metrics = validate_transport_summary(
        transport_metrics.get("topup_background"),
        "top-up background",
        normalized_groups.get("topup_background", []),
        "fullstat_topup_transport_resource_metrics",
    )
    delayed_metrics = validate_transport_summary(
        transport_metrics.get("fresh250k_delayed"),
        "fresh250k delayed",
        normalized_groups.get("fresh250k_delayed", []),
        "fullstat_fresh250k_delayed_transport_resource_metrics",
    )
    check.expect(transport_metrics.get("all_new_transport_receipts_have_exactly_one_pass_metric") is True, "resource all-new-receipt PASS metric closure failed")
    check.expect(transport_metrics.get("all_finalized_attempts_dynamic_8GiB_reserve_pass") is True, "resource finalized-attempt disk reserve closure failed")
    transport_minima: list[int] = []
    for summary in (topup_metrics, delayed_metrics):
        if isinstance(summary, dict) and summary.get("min_free_bytes") is not None:
            try:
                transport_minima.append(as_int(summary.get("min_free_bytes")))
            except Exception as exc:
                check.errors.append(f"resource transport minimum invalid: {exc}")
    expected_transport_minimum = min(transport_minima) if transport_minima else None
    check.expect(transport_metrics.get("min_free_bytes") == expected_transport_minimum, "resource combined transport minimum differs")
    check.expect(payload.get("min_new_transport_completion_free_bytes") == expected_transport_minimum, "resource new-transport completion minimum differs")
    if expected_transport_minimum is not None:
        check.expect(expected_transport_minimum >= DYNAMIC_RESERVE_BYTES, "resource new-transport completion reserve failed")
    all_dynamic = all_resource_disk_values + transport_minima
    expected_all_dynamic = min(all_dynamic) if all_dynamic else None
    check.expect(payload.get("min_all_dynamic_disk_observations_bytes") == expected_all_dynamic, "resource all-dynamic disk minimum differs")
    if expected_all_dynamic is not None:
        check.expect(expected_all_dynamic >= DYNAMIC_RESERVE_BYTES, "resource all-dynamic disk reserve failed")

    check.expect(payload.get("missing") == [], "resource audit missing authorities are nonempty")
    check.expect(payload.get("pending") == [], "resource audit pending authorities are nonempty")
    check.expect(payload.get("errors") == [], "resource audit errors are nonempty")
    check.expect(payload.get("SIM_opened_statted_discovered_or_hashed") is False, "resource audit accessed SIM")
    check.expect(payload.get("transport_launched_by_auditor") is False, "resource auditor launched transport")
    check.expect(payload.get("systemd_or_service_action_performed_by_auditor") is False, "resource auditor performed a systemd/service action")

    return {
        "status": RESOURCE_STATUS,
        "scope": RESOURCE_SCOPE,
        "job_scope": scope,
        "transport_receipt_ids": normalized_groups,
        "transport_completion_disk_metrics": transport_metrics,
        "followup_manifest_binding": manifest,
        "required_guarded_session_labels": expected_labels,
        "exact_session_label_to_phase": dict(RESOURCE_GUARDED_PHASES),
        "guarded_completion_authorities": completion_records,
        "all_guarded_completion_authorities_independently_validated": payload.get("all_guarded_completion_authorities_independently_validated"),
        "guard_sessions": guard_sessions,
        "guard_session_wal_audit": wal_audit,
        "normal_completion_records": normal_count,
        "crash_recovered_completion_records": recovered_count,
        "normal_or_crash_recovery_record_XOR_pass": payload.get("normal_or_crash_recovery_record_XOR_pass"),
        "all_completion_resources_from_original_guard_closure_not_live_inference": payload.get("all_completion_resources_from_original_guard_closure_not_live_inference"),
        "complete_guard_event_log_audit": complete_guard,
        "superseded_or_retried_clean_guard_sessions": payload.get("superseded_or_retried_clean_guard_sessions"),
        "actual_workers_observed": observed_workers,
        "quota_percent_observed": observed_quotas,
        "quota_percent_is_worker_count": False,
        "quota_note": "quota_percent is exactly 300 or 400 while the production controller remains fixed at four workers; quota is neither worker count nor statistical sample count",
        "timeline_rows": len(timeline),
        "min_mem_available_bytes": min(all_resource_mem_values) if all_resource_mem_values else None,
        "min_swap_free_bytes": min(all_resource_swap_values) if all_resource_swap_values else None,
        "min_disk_free_after_projection_bytes": min(all_resource_disk_values) if all_resource_disk_values else None,
        "min_guard_sample_disk_free_bytes": min(disk_values) if disk_values else None,
        "min_guard_completion_disk_free_bytes": min(selected_closure_disk) if selected_closure_disk else None,
        "min_new_transport_completion_free_bytes": expected_transport_minimum,
        "min_all_dynamic_disk_observations_bytes": expected_all_dynamic,
        "source_event_log": source,
        "guard_session_wal": wal_log,
        "resource_completion_event_log": completion_log,
    }


def validate_stage06_manifest(
    manifest: dict[str, Any], check: Checker
) -> None:
    records = {str(row.get("path")): row for row in manifest.get("files") or []}
    expected = {
        "mission_timeline.csv": "full06_timeline",
        "frozen47_se3_vs_sf3_fullstat_mission.csv": "full06_comparison",
        "summary.json": "full06_summary",
    }
    for filename, authority_name in expected.items():
        record = records.get(filename)
        authority = check.authorities.get(authority_name) or {}
        check.expect(record is not None, f"stage06 manifest omits {filename}")
        if record:
            check.expect(record.get("bytes") == authority.get("bytes"), f"stage06 manifest bytes differ {filename}")
            check.expect(record.get("sha256") == authority.get("sha256"), f"stage06 manifest SHA256 differs {filename}")
    check.expect(manifest.get("SIM_opened_statted_discovered_or_hashed") is False, "stage06 manifest claims SIM access")
    check.expect(manifest.get("transport_launched") is False, "stage06 manifest claims transport launch")
    check.expect(manifest.get("second_topup_authorized") is False, "stage06 manifest authorizes second topup")

    stage06_inputs = manifest.get("input_authorities") or {}
    bindings = {
        "plan1_mission": "plan1_mission",
        "plan1_closure": "plan1_closure",
        "plan1_stage04_signal": "plan1_signal_acceptance",
        "topup_static": "topup_static",
        "topup_aggregate": "topup_aggregate",
        "full01_summary": "full01_summary",
        "full01_manifest": "full01_manifest",
        "full02_summary": "full02_summary",
        "full02_manifest": "full02_manifest",
        "full02_inventory": "full02_inventory",
        "full02_source_index": "full02_source_index",
        "full02_validation": "full02_validation",
        "full03_summary": "full03_summary",
        "full03_manifest": "full03_manifest",
        "full03_aggregate": "full03_aggregate",
        "full04_summary": "full04_summary",
        "full04_manifest": "full04_manifest",
        "full04_cutflow": "full04_cutflow",
        "full04_occupancy": "full04_occupancy",
        "full04_lineage": "full04_lineage",
        "full04_signal": "full04_signal",
        "full04_zero_provenance": "full04_zero_provenance",
    }
    for mission_label, finalizer_label in bindings.items():
        observed = stage06_inputs.get(mission_label) or {}
        expected_record = check.authorities.get(finalizer_label) or {}
        check.expect(bool(observed), f"stage06 input authorities omit {mission_label}")
        check.expect(
            observed.get("sha256") == expected_record.get("sha256"),
            f"stage06 input SHA256 binding differs {mission_label}",
        )
        check.expect(
            observed.get("bytes") == expected_record.get("bytes"),
            f"stage06 input byte binding differs {mission_label}",
        )


def check_prerequisites() -> dict[str, Any]:
    check = Checker()
    for label, module in (
        ("stage01_code", stage01),
        ("stage02_code", stage02),
        ("stage03_code", stage03),
        ("stage04_code", stage04),
        ("stage06_code", stage06),
        ("finalizer_code", __import__(__name__)),
    ):
        path = HERE if label == "finalizer_code" else Path(module.__file__).resolve()
        check.code(label, path)

    payloads = {label: check.json(label, path) for label, path in JSON_PATHS.items()}
    tables = {label: check.csv(label, path) for label, path in CSV_PATHS.items()}
    stage_bindings = validate_stage_statuses(payloads, check)

    background_closure: list[dict[str, Any]] = []
    if tables["full01_input_manifest"] is not None and tables["full02_buildup_manifest"] is not None:
        try:
            background_closure = validate_background_contract(
                tables["full01_input_manifest"] or [],
                tables["full02_buildup_manifest"] or [],
                check,
            )
        except Exception as exc:
            check.errors.append(f"49-job fullstat background contract invalid: {exc}")

    delayed_closure: list[dict[str, Any]] = []
    positive: list[str] = []
    zero: list[str] = []
    delayed_inputs = (
        tables["full02_source_index"], payloads["full02_summary"],
        payloads["full02_validation"], payloads["full03_aggregate"],
        payloads["full03_summary"], tables["full03_coverage"],
        tables["full04_zero_provenance"],
    )
    if all(value is not None for value in delayed_inputs):
        try:
            delayed_closure, positive, zero = validate_delayed_cross_stage(
                tables["full02_source_index"] or [],
                payloads["full02_summary"] or {},
                payloads["full02_validation"] or {},
                payloads["full03_aggregate"] or {},
                payloads["full03_summary"] or {},
                tables["full03_coverage"] or [],
                tables["full04_zero_provenance"] or [],
                check,
            )
        except Exception as exc:
            check.errors.append(f"fullstat delayed cross-stage contract invalid: {exc}")

    passive_w: dict[str, Any] = {}
    w_inputs = (
        payloads["full01_summary"], payloads["full02_passive_w"],
        payloads["full03_summary"], tables["full03_w_diagnostics"],
        payloads["full04_summary"], tables["full04_passive_w"],
    )
    if all(value is not None for value in w_inputs):
        try:
            passive_w = validate_passive_w(
                payloads["full01_summary"] or {},
                payloads["full02_passive_w"] or {},
                payloads["full03_summary"] or {},
                tables["full03_w_diagnostics"] or [],
                payloads["full04_summary"] or {},
                tables["full04_passive_w"] or [],
                check,
            )
        except Exception as exc:
            check.errors.append(f"passive-W cross-stage contract invalid: {exc}")

    signal_anchor: dict[str, Any] = {}
    signal_inputs = (
        tables["plan1_signal_acceptance"], tables["full04_signal"],
        payloads["full04_summary"], payloads["full06_summary"],
    )
    if all(value is not None for value in signal_inputs):
        try:
            signal_anchor = validate_signal_anchor(
                tables["plan1_signal_acceptance"] or [],
                tables["full04_signal"] or [],
                payloads["full04_summary"] or {},
                payloads["full06_summary"] or {},
                check.authorities,
                check,
            )
        except Exception as exc:
            check.errors.append(f"fresh 37194 signal anchor invalid: {exc}")

    entry_gate: dict[str, Any] = {}
    gate_inputs = (
        payloads["plan1_mission"], payloads["plan1_closure"],
        payloads["topup_static"], payloads["topup_aggregate"],
        payloads["full06_summary"],
    )
    if all(value is not None for value in gate_inputs):
        try:
            entry_gate = validate_plan1_entry_gate(
                payloads["plan1_mission"] or {},
                payloads["plan1_closure"] or {},
                payloads["topup_static"] or {},
                payloads["topup_aggregate"] or {},
                payloads["full06_summary"] or {},
                check.authorities,
                check,
            )
        except Exception as exc:
            check.errors.append(f"one-time Plan1 entry gate invalid: {exc}")

    mission: dict[str, Any] = {}
    if (
        payloads["full06_summary"] is not None
        and tables["full06_timeline"] is not None
        and tables["full06_comparison"] is not None
    ):
        try:
            mission = validate_mission(
                payloads["full06_summary"] or {},
                tables["full06_timeline"] or [],
                tables["full06_comparison"] or [],
                check,
            )
        except Exception as exc:
            check.errors.append(f"fullstat 162-node mission arithmetic invalid: {exc}")
    if payloads["full06_manifest"] is not None:
        try:
            validate_stage06_manifest(payloads["full06_manifest"] or {}, check)
        except Exception as exc:
            check.errors.append(f"fullstat stage06 manifest binding invalid: {exc}")

    resource: dict[str, Any] = {}
    if payloads["fullstat_resource_timeline"] is not None and delayed_closure:
        try:
            resource = validate_resource_timeline(
                payloads["fullstat_resource_timeline"] or {},
                len(positive), len(zero), check,
            )
        except Exception as exc:
            check.errors.append(f"fullstat independent resource timeline invalid: {exc}")

    if OUTPUT.exists():
        check.errors.append(f"write-once fullstat final-audit output exists: {norm(OUTPUT)}")
    ready = not check.missing and not check.errors
    status = READY_STATUS if ready else FAIL_STATUS if check.errors else NOT_READY_STATUS
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "checked_at": utc_now(),
        "output_root": norm(OUTPUT),
        "scope": "SF3_FULLSTAT_49_BACKGROUND_FRESH250K_DELAYED_REUSED37194_SIGNAL_VS_FROZEN47_SE3",
        "stage_bindings": stage_bindings,
        "background_contract": {
            "jobs": EXPECTED_BACKGROUND_JOBS,
            "instant_jobs": EXPECTED_INSTANT_JOBS,
            "buildup_jobs": EXPECTED_BUILDUP_JOBS,
            "instant_histories": EXPECTED_INSTANT_HISTORIES,
            "buildup_histories": EXPECTED_BUILDUP_HISTORIES,
            "family_mode_closure": background_closure,
            "pooling_boundary": "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY",
        },
        "delayed_contract": {
            "registered_families": 8,
            "positive_fresh250k_families": positive,
            "zero_A15_skipped_families": zero,
            "cells": delayed_closure,
            "plan1_83334_read_or_pooled": False,
            "incremental_83334_plus_166666_merge_used": False,
        },
        "passive_w_contract": passive_w,
        "signal_anchor": signal_anchor,
        "one_time_plan1_entry_gate": entry_gate,
        "mission_contract": mission,
        "resource_timeline_binding": resource,
        "resource_authority_required": {
            "path": norm(RESOURCE_AUDIT),
            "status": RESOURCE_STATUS,
            "scope": RESOURCE_SCOPE,
            "fallback_to_live_inference": False,
            "required_top_level_fields": [
                "ready",
                "pass",
                "write_contract",
                "configured_cpu_budget_max",
                "adaptive_workers_min",
                "adaptive_workers_max",
                "production_controller_workers",
                "mem_available_floor_bytes",
                "swap_free_floor_bytes",
                "dynamic_disk_reserve_bytes",
                "quota_percent_allowed_values",
                "quota_percent_observed",
                "job_scope",
                "transport_receipt_ids",
                "transport_completion_disk_metrics",
                "followup_manifest_binding",
                "required_guarded_session_labels",
                "observed_guarded_session_labels",
                "exact_session_label_to_phase",
                "observed_closed_exact_label_stage_coverage",
                "all_required_exact_label_stage_bindings_pass",
                "guarded_completion_authorities",
                "all_guarded_completion_authorities_independently_validated",
                "guard_sessions",
                "guard_session_wal_audit",
                "normal_completion_records",
                "crash_recovered_completion_records",
                "normal_or_crash_recovery_record_XOR_pass",
                "all_completion_resources_from_original_guard_closure_not_live_inference",
                "complete_guard_event_log_audit",
                "superseded_or_retried_clean_guard_sessions",
                "all_guard_sessions_closed",
                "all_guard_sessions_exactly_one_clean_closure",
                "all_guard_sessions_terminal_quota_400",
                "all_guard_samples_hard_floors_pass",
                "actual_workers_observed",
                "min_mem_available_bytes",
                "min_swap_free_bytes",
                "min_disk_free_after_projection_bytes",
                "min_guard_sample_disk_free_bytes",
                "min_guard_completion_disk_free_bytes",
                "min_new_transport_completion_free_bytes",
                "min_all_dynamic_disk_observations_bytes",
                "timeline",
                "source_event_log",
                "guard_session_wal",
                "resource_completion_event_log",
                "input_authorities",
                "missing",
                "pending",
                "errors",
            ],
            "timeline_fields": [
                "at",
                "phase",
                "session_label",
                "actual_workers",
                "quota_percent",
                "quota_percent_is_worker_count",
                "mem_available_bytes",
                "swap_free_bytes",
                "disk_free_after_projection_bytes",
                "decision_reasons",
            ],
            "production_controller_workers": 4,
            "quota_percent_allowed_values": RESOURCE_ALLOWED_QUOTAS,
            "quota_percent_is_worker_or_statistical_count": False,
            "required_guarded_session_label_to_phase": dict(RESOURCE_GUARDED_PHASES),
            "required_guarded_completion_authorities": {
                label: {
                    "relative_path": relative,
                    "status": status,
                    "companion_manifest_relative_path": companion,
                }
                for label, (relative, status, companion) in RESOURCE_COMPLETION_AUTHORITIES.items()
            },
            "guard_session_wal_requirements": {
                "all_clean_guard_sessions_have_write_ahead_start": True,
                "legal_orphans": "PRE_GUARD_CONTROLLER_CRASH_ONLY",
                "duplicate_identity_rows": "REJECT",
                "same_key_distinct_timestamp_pre_guard_retries": "AUDITED_AND_COUNTED",
                "selected_completion_WAL_start_precedes_guard_start": True,
            },
            "normal_or_recovery_completion_requirements": {
                "exactly_one_mode_per_selected_session": True,
                "normal_mode": RESOURCE_NORMAL_COMPLETION_MODE,
                "recovered_mode": RESOURCE_RECOVERED_COMPLETION_MODE,
                "canonical_completion_authority_required": True,
                "resource_snapshot_source": "ORIGINAL_GUARD_CLOSURE_ONLY",
                "live_resource_inference": False,
            },
            "complete_guard_event_log_requirements": {
                "all_bytes_audited": True,
                "all_sessions_cleanly_closed": True,
                "every_guarded_label_covered": True,
                "clean_retries_retained_not_discarded": True,
            },
            "transport_job_scope": {
                "plan1_background_jobs": 21,
                "topup_background_jobs": 28,
                "fullstat_background_jobs": EXPECTED_BACKGROUND_JOBS,
                "delayed_positive_transport_jobs": len(positive),
                "total_transport_jobs": EXPECTED_BACKGROUND_JOBS + len(positive),
                "Plan1_83334_read_or_pooled": False,
            },
        },
        "terminal_disposition": {
            "decision": TERMINAL_DECISION,
            "second_topup_gate_evaluated": False,
            "second_topup_authorized": False,
            "terminal_no_second_topup": True,
            "proxy_controls_any_gate": False,
        },
        "input_authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "errors": check.errors,
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__FIXED_SMALL_CSV_JSON_AND_AGGREGATE_RECEIPT_METADATA_ONLY",
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_or_topup_launched_by_finalizer": False,
        "authority_boundary": "TERMINAL_FULLSTAT_AUDIT_ONLY__NO_SECOND_TOPUP_OR_AUTOMATIC_PROMOTION",
    }


def report_text(audit: dict[str, Any]) -> str:
    background = audit["background_contract"]
    delayed = audit["delayed_contract"]
    mission = audit["mission_contract"]
    gate = audit["one_time_plan1_entry_gate"]
    resource = audit["resource_timeline_binding"]
    return "\n".join(
        [
            "# SF3 terminal full-stat chain audit",
            "",
            f"Status: `{audit['status']}`",
            "",
            f"The full-stat SF3 background closes at {background['jobs']} jobs: {background['instant_jobs']} instant ({background['instant_histories']:,} histories) and {background['buildup_jobs']} buildup ({background['buildup_histories']:,} histories). Every family/mode equals the frozen S3d-O8 full-stat target.",
            "",
            f"Eight delayed families are registered. Positive cells are fresh complete 250,000-trigger transports ({', '.join(delayed['positive_fresh250k_families']) or 'none'}); zero-A15 cells are skipped with finite upper limits ({', '.join(delayed['zero_A15_skipped_families']) or 'none'}). Plan-1 83,334-trigger products are neither read nor pooled.",
            "",
            "The fresh Plan-1 SF3 37,194-ray signal acceptance is byte-hash anchored and reused. The three exact W volumes remain passive diagnostics and are disjoint from the three-BGO plus three-plastic active veto.",
            "",
            f"The Plan-1 central entry ratio was {gate.get('observed_central_ratio')}; it was evaluated once at the <=0.75 entry gate. The terminal 162-node central SF3/SE3 F3 ratio is {mission.get('central_F3_SF3_over_SE3')}, and the separately reported componentwise-proxy ratio is {mission.get('componentwise_proxy_F3_SF3_over_SE3')}.",
            "",
            f"The independent resource audit records workers {resource.get('actual_workers_observed')}, quota percentages {resource.get('quota_percent_observed')}, and the fixed 1.5-GiB MemAvailable, 8-GiB SwapFree, and 8-GiB dynamic-disk floors. A 300% quota can be shared by four workers; quota is not a worker or statistical count.",
            "",
            f"Terminal disposition: `{TERMINAL_DECISION}`. No second top-up gate is evaluated or authorized.",
            "",
        ]
    )


def build() -> dict[str, Any]:
    checked = check_prerequisites()
    if not checked.get("ready"):
        raise RuntimeError(json_text(checked))
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite write-once output: {OUTPUT}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".07_final_audit.work-", dir=OUTPUT.parent))
    try:
        audit = dict(checked)
        audit.update(
            {
                "status": PASS_STATUS,
                "ready": True,
                "finalized_at": utc_now(),
                "write_contract": "ATOMIC_DIRECTORY_RENAME__WRITE_ONCE",
                "final_paths": {
                    "final_audit": norm(OUTPUT / "final_audit.json"),
                    "background_closure": norm(OUTPUT / "background_family_mode_closure.csv"),
                    "delayed_closure": norm(OUTPUT / "delayed_family_closure.csv"),
                    "mission_comparison": norm(OUTPUT / "terminal_mission_comparison.csv"),
                    "report": norm(OUTPUT / "FINAL_REPORT.md"),
                },
            }
        )
        background_rows = audit["background_contract"]["family_mode_closure"]
        delayed_rows = audit["delayed_contract"]["cells"]
        mission = audit["mission_contract"]
        comparison_rows = [
            {
                "phase": "FULLSTAT_TERMINAL",
                "central_F3_SF3_over_SE3": mission["central_F3_SF3_over_SE3"],
                "componentwise_proxy_F3_SF3_over_SE3": mission[
                    "componentwise_proxy_F3_SF3_over_SE3"
                ],
                "entry_gate_reapplied": False,
                "second_topup_gate_evaluated": False,
                "second_topup_authorized": False,
                "terminal_decision": TERMINAL_DECISION,
            }
        ]
        (work / "background_family_mode_closure.csv").write_text(
            csv_text(background_rows), encoding="utf-8"
        )
        (work / "delayed_family_closure.csv").write_text(
            csv_text(delayed_rows), encoding="utf-8"
        )
        (work / "terminal_mission_comparison.csv").write_text(
            csv_text(comparison_rows), encoding="utf-8"
        )
        (work / "FINAL_REPORT.md").write_text(report_text(audit), encoding="utf-8")
        (work / "final_audit.json").write_text(json_text(audit), encoding="utf-8")
        generated = sorted(path for path in work.iterdir() if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": PASS_STATUS,
            "created_at": utc_now(),
            "output_root": norm(OUTPUT),
            "files": [
                {
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_small(path),
                }
                for path in generated
            ],
            "input_authorities": checked["input_authorities"],
            "write_contract": "ATOMIC_DIRECTORY_RENAME__WRITE_ONCE",
            "SIM_opened_statted_discovered_or_hashed": False,
            "transport_or_topup_launched": False,
            "second_topup_gate_evaluated": False,
            "second_topup_authorized": False,
        }
        (work / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
        for path in work.iterdir():
            if path.is_file():
                with path.open("rb") as handle:
                    os.fsync(handle.fileno())
        os.rename(work, OUTPUT)
        directory_fd = os.open(OUTPUT.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            "schema_version": 1,
            "status": PASS_STATUS,
            "output_root": norm(OUTPUT),
            "central_F3_SF3_over_SE3": mission["central_F3_SF3_over_SE3"],
            "componentwise_proxy_F3_SF3_over_SE3": mission[
                "componentwise_proxy_F3_SF3_over_SE3"
            ],
            "terminal_decision": TERMINAL_DECISION,
            "second_topup_authorized": False,
        }
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def fixture_background_rows(mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for family in FAMILIES:
        for namespace, shards in expected_namespace_shards(mode, family).items():
            for value in shards:
                rows.append(
                    {
                        "job_id": f"fixture_{mode}_{family}_{ordinal:02d}",
                        "geometry": "SF3",
                        "mode": mode,
                        "family": family,
                        "events": value,
                        "source_namespace": namespace,
                    }
                )
                ordinal += 1
    return rows


def fixture_source_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, family in enumerate(FAMILIES):
        zero = index == len(FAMILIES) - 1
        sum_tt = 10.0
        upper = stage03.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt
        rows.append(
            {
                "incident_family": family,
                "execution_disposition": stage02.ZERO_DISPOSITION if zero else stage02.POSITIVE_DISPOSITION,
                "registered_decay_triggers": FULLSTAT_DELAYED_EVENTS,
                "actual_transport_triggers": 0 if zero else FULLSTAT_DELAYED_EVENTS,
                "transport_eligible": not zero,
                "transported_ground_activity_Bq": 0.0 if zero else 1.0,
                "buildup_sum_TT_s": sum_tt,
                "transported_ground_rate_upper95_s-1": upper if zero else "",
                "transported_ground_A15_upper95_Bq_conservative": upper if zero else "",
                "zero_A15_upper_provenance": "synthetic finite upper" if zero else "",
            }
        )
    return rows


def fixture_mission() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    geometries: dict[str, dict[str, Any]] = {}
    timeline: list[dict[str, Any]] = []
    specs = {"SE3": (1000.0, 10000.0, 600.0, 10000.0), "SF3": (600.0, 14400.0, 360.0, 14400.0)}
    for geometry, (source, background, lower, upper) in specs.items():
        z = source / math.sqrt(background)
        z_proxy = lower / math.sqrt(upper)
        geometries[geometry] = {
            "source_counts_20d": source,
            "background_counts_20d": background,
            "source_lower95_counts_20d": lower,
            "background_upper95_proxy_counts_20d": upper,
            "Z20d": z,
            "Z20d_componentwise_proxy": z_proxy,
            "F3_20d_ph_cm2_s": 1e-4 * 3.0 / z,
            "F3_20d_componentwise_proxy_ph_cm2_s": 1e-4 * 3.0 / z_proxy,
        }
        for index in range(81):
            fraction = index / 80.0
            timeline.append(
                {
                    "geometry": geometry,
                    "time_bin_id": index,
                    "day_mid": 20.0 * fraction,
                    "cumulative_source_counts": source * fraction,
                    "cumulative_background_counts": background * fraction,
                    "cumulative_source_lower95_counts": lower * fraction,
                    "cumulative_background_upper95_proxy_counts": upper * fraction,
                    "counting_Z": z if index == 80 else 0.0,
                    "counting_Z_componentwise_proxy": z_proxy if index == 80 else 0.0,
                }
            )
    central_ratio = geometries["SF3"]["F3_20d_ph_cm2_s"] / geometries["SE3"]["F3_20d_ph_cm2_s"]
    proxy_ratio = geometries["SF3"]["F3_20d_componentwise_proxy_ph_cm2_s"] / geometries["SE3"]["F3_20d_componentwise_proxy_ph_cm2_s"]
    summary = {
        "geometries": geometries,
        "mission_contract": {"reference_flux_ph_cm2_s": 1e-4, "time_nodes": 81},
        "terminal_fullstat_comparison": {
            "F3_SF3_over_SE3_full_envelope": central_ratio,
            "F3_componentwise_proxy_SF3_over_SE3_full_envelope": proxy_ratio,
            "decision": TERMINAL_DECISION,
            "second_topup_gate_evaluated": False,
            "second_topup_authorized": False,
        },
    }
    comparison = [
        {
            "geometry": geometry,
            "F3_20d_ph_cm2_s": item["F3_20d_ph_cm2_s"],
            "F3_20d_componentwise_proxy_ph_cm2_s": item["F3_20d_componentwise_proxy_ph_cm2_s"],
            "terminal_disposition": TERMINAL_DECISION,
        }
        for geometry, item in geometries.items()
    ]
    return summary, timeline, comparison


def fixture_resource() -> dict[str, Any]:
    labels = list(RESOURCE_GUARDED_PHASES)
    manifest_sha = "a" * 64
    plan1_ids = [f"plan1_bg_{index:02d}" for index in range(21)]
    topup_ids = [f"topup_bg_{index:02d}" for index in range(28)]
    delayed_ids = sorted(f"fresh250k_{family}" for family in FAMILIES[:-1])
    zero_ids = [f"fresh250k_{FAMILIES[-1]}"]

    completion_records: dict[str, dict[str, Any]] = {}
    completion_input_records: dict[str, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        relative, status, companion_relative = RESOURCE_COMPLETION_AUTHORITIES[label]
        record: dict[str, Any] = {
            "path": norm(PACKAGE_ROOT / relative),
            "bytes": 500 + index,
            "sha256": f"{index + 1:064x}",
            "status": status,
            "relative_path": relative,
        }
        completion_input_records[f"guarded_completion_{label}"] = {
            key: record[key] for key in ("path", "bytes", "sha256")
        }
        if companion_relative is not None:
            companion = {
                "path": norm(PACKAGE_ROOT / companion_relative),
                "bytes": 700 + index,
                "sha256": f"{index + 11:064x}",
                "status": status,
                "relative_path": companion_relative,
            }
            record["companion_manifest"] = companion
            completion_input_records[f"guarded_completion_{label}_manifest"] = {
                key: companion[key] for key in ("path", "bytes", "sha256")
            }
        completion_records[label] = record

    timeline: list[dict[str, Any]] = []
    guard_sessions: list[dict[str, Any]] = []
    complete_sessions: list[dict[str, Any]] = [
        {
            "session_label": labels[0],
            "sample_count": 1,
            "quota_percent_sequence": [400],
            "closure": "GUARD_EXIT_RESTORE_NORMAL",
            "guard_log_start_byte": 0,
            "guard_log_end_byte": 200,
            "completion_mem_available_bytes": MEMORY_FLOOR_BYTES + 1000,
            "completion_swap_free_bytes": SWAP_FLOOR_BYTES + 1000,
            "completion_disk_free_bytes": DYNAMIC_RESERVE_BYTES + 1000,
            "started_at": "2026-08-15T22:00:00+00:00",
            "closed_at": "2026-08-15T22:00:05+00:00",
        }
    ]
    origin = datetime(2026, 8, 16, tzinfo=timezone.utc)
    for index, label in enumerate(labels):
        quota = 300 if index == 0 else 400
        mem = MEMORY_FLOOR_BYTES + 10 + index
        swap = SWAP_FLOOR_BYTES + 20 + index
        disk = DYNAMIC_RESERVE_BYTES + 300 + index
        closure_mem = MEMORY_FLOOR_BYTES + 5 + index
        closure_swap = SWAP_FLOOR_BYTES + 15 + index
        closure_disk = DYNAMIC_RESERVE_BYTES + 250 + index
        started_at = (origin + timedelta(hours=index)).isoformat()
        closed_at = (origin + timedelta(hours=index, seconds=5)).isoformat()
        wal_started_at = (origin + timedelta(hours=index, seconds=-1)).isoformat()
        quota_sequence = [300, 400] if index == 0 else [400]
        timeline.append({
            "at": started_at,
            "phase": RESOURCE_GUARDED_PHASES[label],
            "session_label": label,
            "actual_workers": 4,
            "quota_percent": quota,
            "quota_percent_is_worker_count": False,
            "mem_available_bytes": mem,
            "swap_free_bytes": swap,
            "disk_free_after_projection_bytes": disk,
            "decision_reasons": ["synthetic_sample"],
        })
        start = 200 + index * 180
        session = {
            "session_label": label,
            "phase": RESOURCE_GUARDED_PHASES[label],
            "actual_workers": 4,
            "guard_log_start_byte": start,
            "guard_log_end_byte": start + 180,
            "sample_count": 1,
            "quota_percent_sequence": quota_sequence,
            "quota_values_allowed_exactly_300_or_400": True,
            "terminal_quota_percent": 400,
            "closure": "GUARD_EXIT_RESTORE_NORMAL",
            "hard_floor_breach_observed": False,
            "minimum_mem_available_bytes": mem,
            "minimum_swap_free_bytes": swap,
            "minimum_disk_free_bytes": disk,
            "completion_mem_available_bytes": closure_mem,
            "completion_swap_free_bytes": closure_swap,
            "completion_disk_free_bytes": closure_disk,
            "completion_record_mode": (
                RESOURCE_RECOVERED_COMPLETION_MODE
                if index == 2 else RESOURCE_NORMAL_COMPLETION_MODE
            ),
            "guard_session_wal_started_at": wal_started_at,
            "canonical_completion_authority": completion_records[label],
            "manifest_sha256": manifest_sha,
        }
        guard_sessions.append(session)
        complete_sessions.append({
            "session_label": label,
            "sample_count": session["sample_count"],
            "quota_percent_sequence": session["quota_percent_sequence"],
            "closure": session["closure"],
            "guard_log_start_byte": start,
            "guard_log_end_byte": start + 180,
            "completion_mem_available_bytes": closure_mem,
            "completion_swap_free_bytes": closure_swap,
            "completion_disk_free_bytes": closure_disk,
            "started_at": started_at,
            "closed_at": closed_at,
        })
    complete_counts = dict(Counter(row["session_label"] for row in complete_sessions))

    def completion_summary(
        ids: list[str], namespace: str, free_base: int
    ) -> dict[str, Any]:
        successful = [
            {
                "job_id": job_id,
                "attempt": 1,
                "at": f"2026-08-16T12:00:{index:02d}+00:00",
                "wall_s": 1.0 + index,
                "peak_rss_bytes": 10_000 + index,
                "artifact_bytes": 20_000 + index,
                "free_bytes": free_base + index,
            }
            for index, job_id in enumerate(ids)
        ]
        return {
            "namespace": namespace,
            "resource_metrics_path": f"{namespace}/resource_metrics.jsonl",
            "expected_successful_jobs": len(ids),
            "successful_jobs": successful,
            "failed_finalized_attempts": 0,
            "total_finalized_attempts": len(ids),
            "min_free_bytes": free_base if ids else None,
            "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            "all_finalized_attempts_reserve_pass": True,
            "all_canonical_receipts_have_exactly_one_pass_metric": True,
        }

    topup_metrics = completion_summary(
        topup_ids, "/synthetic/topup", DYNAMIC_RESERVE_BYTES + 100
    )
    delayed_metrics = completion_summary(
        delayed_ids, "/synthetic/delayed", DYNAMIC_RESERVE_BYTES + 200
    )
    source_log = {
        "path": "/synthetic/guard.jsonl",
        "bytes": 1100,
        "sha256": "b" * 64,
    }
    wal_log = {
        "path": "/synthetic/guard_session_wal.jsonl",
        "bytes": 900,
        "sha256": "9" * 64,
    }
    completion_log = {
        "path": "/synthetic/resource.jsonl",
        "bytes": 700,
        "sha256": "c" * 64,
    }
    manifest_record = {
        "path": "/synthetic/followup_manifest.json",
        "bytes": 400,
        "sha256": manifest_sha,
    }
    return {
        "schema_version": 1,
        "profile_id": RESOURCE_PROFILE,
        "status": RESOURCE_STATUS,
        "ready": True,
        "pass": True,
        "checked_at": "2026-08-16T13:00:00+00:00",
        "built_at": "2026-08-16T13:00:01+00:00",
        "write_contract": RESOURCE_WRITE_CONTRACT,
        "scope": RESOURCE_SCOPE,
        "configured_cpu_budget_max": 6,
        "adaptive_workers_min": 4,
        "adaptive_workers_max": 6,
        "production_controller_workers": 4,
        "mem_available_floor_bytes": MEMORY_FLOOR_BYTES,
        "swap_free_floor_bytes": SWAP_FLOOR_BYTES,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "quota_percent_is_worker_count": False,
        "quota_transition_percent": [400, 300, 400],
        "quota_transition_field_semantics": "NORMAL_THROTTLE_RESTORE_POLICY__300_IS_CONDITIONAL_AND_NEVER_A_WORKER_OR_STATISTICS_COUNT",
        "quota_percent_allowed_values": RESOURCE_ALLOWED_QUOTAS,
        "quota_percent_observed": [300, 400],
        "safe_all_400_quota_sessions_are_pass_eligible": True,
        "artificial_throttle_required": False,
        "job_scope": {
            "plan1_background_jobs": 21,
            "topup_background_jobs": 28,
            "fullstat_background_jobs": 49,
            "delayed_registered_families": 8,
            "delayed_positive_transport_jobs": 7,
            "delayed_zero_skips": 1,
            "total_transport_jobs": 56,
            "Plan1_83334_read_or_pooled": False,
        },
        "transport_receipt_ids": {
            "plan1_background": plan1_ids,
            "topup_background": topup_ids,
            "fresh250k_delayed": delayed_ids,
            "zero_A15_skips": zero_ids,
        },
        "transport_completion_disk_metrics": {
            "topup_background": topup_metrics,
            "fresh250k_delayed": delayed_metrics,
            "all_new_transport_receipts_have_exactly_one_pass_metric": True,
            "all_finalized_attempts_dynamic_8GiB_reserve_pass": True,
            "min_free_bytes": DYNAMIC_RESERVE_BYTES + 100,
        },
        "followup_manifest_binding": {
            **manifest_record,
            "status": RESOURCE_MANIFEST_STATUS,
            "guarded_steps": labels,
        },
        "required_guarded_session_labels": labels,
        "observed_guarded_session_labels": labels,
        "guarded_completion_authorities": completion_records,
        "all_guarded_completion_authorities_independently_validated": True,
        "exact_session_label_to_phase": dict(RESOURCE_GUARDED_PHASES),
        "required_exact_label_stage_coverage": dict(RESOURCE_GUARDED_PHASES),
        "observed_closed_exact_label_stage_coverage": {
            label: [phase] for label, phase in RESOURCE_GUARDED_PHASES.items()
        },
        "all_required_exact_label_stage_bindings_pass": True,
        "guard_sessions": guard_sessions,
        "guard_session_wal_audit": {
            "rows": 7,
            "guard_session_keys": len(complete_sessions),
            "all_clean_guard_sessions_have_write_ahead_start": True,
            "orphan_pre_guard_crash_rows": 1,
            "duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct": True,
        },
        "normal_completion_records": 4,
        "crash_recovered_completion_records": 1,
        "normal_or_crash_recovery_record_XOR_pass": True,
        "all_completion_resources_from_original_guard_closure_not_live_inference": True,
        "complete_guard_event_log_audit": {
            "all_bytes_audited": True,
            "all_sessions_cleanly_closed": True,
            "session_count": len(complete_sessions),
            "sessions_by_label": {
                label: complete_counts.get(label, 0) for label in labels
            },
            "sessions": complete_sessions,
        },
        "superseded_or_retried_clean_guard_sessions": 1,
        "all_guard_sessions_closed": True,
        "all_guard_sessions_exactly_one_clean_closure": True,
        "all_guard_sessions_terminal_quota_400": True,
        "all_guard_samples_hard_floors_pass": True,
        "actual_workers_observed": [4],
        "timeline_rows": len(timeline),
        "min_mem_available_bytes": MEMORY_FLOOR_BYTES + 5,
        "min_swap_free_bytes": SWAP_FLOOR_BYTES + 15,
        "min_disk_free_after_projection_bytes": DYNAMIC_RESERVE_BYTES + 250,
        "min_guard_sample_disk_free_bytes": DYNAMIC_RESERVE_BYTES + 300,
        "min_guard_completion_disk_free_bytes": DYNAMIC_RESERVE_BYTES + 250,
        "min_new_transport_completion_free_bytes": DYNAMIC_RESERVE_BYTES + 100,
        "min_all_dynamic_disk_observations_bytes": DYNAMIC_RESERVE_BYTES + 100,
        "timeline": timeline,
        "source_event_log": source_log,
        "guard_session_wal": wal_log,
        "resource_completion_event_log": completion_log,
        "input_authorities": {
            "fullstat_followup_manifest": manifest_record,
            "fullstat_guard_event_log": source_log,
            "fullstat_guard_session_wal": wal_log,
            "fullstat_resource_completion_log": completion_log,
            "fullstat_topup_transport_resource_metrics": {
                "path": topup_metrics["resource_metrics_path"],
                "bytes": 1000,
                "sha256": "d" * 64,
            },
            "fullstat_fresh250k_delayed_transport_resource_metrics": {
                "path": delayed_metrics["resource_metrics_path"],
                "bytes": 800,
                "sha256": "e" * 64,
            },
            **completion_input_records,
        },
        "missing": [],
        "pending": [],
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched_by_auditor": False,
        "systemd_or_service_action_performed_by_auditor": False,
        "errors": [],
    }


def exercise_resource_negative_fixtures(check: Checker) -> None:
    all_zero = fixture_resource()
    all_delayed_ids = sorted(
        all_zero["transport_receipt_ids"]["fresh250k_delayed"]
        + all_zero["transport_receipt_ids"]["zero_A15_skips"]
    )
    all_zero["job_scope"].update({
        "delayed_positive_transport_jobs": 0,
        "delayed_zero_skips": 8,
        "total_transport_jobs": 49,
    })
    all_zero["transport_receipt_ids"]["fresh250k_delayed"] = []
    all_zero["transport_receipt_ids"]["zero_A15_skips"] = all_delayed_ids
    all_zero["transport_completion_disk_metrics"]["fresh250k_delayed"] = {
        "namespace": "/synthetic/delayed",
        "expected_successful_jobs": 0,
        "successful_jobs": [],
        "failed_finalized_attempts": 0,
        "total_finalized_attempts": 0,
        "min_free_bytes": None,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "all_finalized_attempts_reserve_pass": True,
        "all_canonical_receipts_have_exactly_one_pass_metric": True,
        "zero_positive_transport_disposition": True,
    }
    del all_zero["input_authorities"]["fullstat_fresh250k_delayed_transport_resource_metrics"]
    all_zero_check = Checker()
    validate_resource_timeline(all_zero, 0, 8, all_zero_check)
    check.expect(
        not all_zero_check.errors,
        f"synthetic all-zero delayed resource fixture was rejected: {all_zero_check.errors}",
    )

    def mutate_total(payload: dict[str, Any]) -> None:
        payload["job_scope"]["total_transport_jobs"] = 35

    def mutate_worker(payload: dict[str, Any]) -> None:
        payload["timeline"][0]["actual_workers"] = 6
        payload["actual_workers_observed"] = [4, 6]

    def mutate_quota(payload: dict[str, Any]) -> None:
        payload["timeline"][0]["quota_percent"] = 600
        payload["quota_percent_observed"] = [400, 600]

    def mutate_manifest(payload: dict[str, Any]) -> None:
        payload["guard_sessions"][0]["manifest_sha256"] = "f" * 64

    def mutate_missing_session(payload: dict[str, Any]) -> None:
        payload["guard_sessions"].pop()

    def mutate_phase(payload: dict[str, Any]) -> None:
        payload["timeline"][0]["phase"] = "FULLSTAT_DELAYED_TRANSPORT"

    def mutate_complete_guard(payload: dict[str, Any]) -> None:
        payload["complete_guard_event_log_audit"]["all_bytes_audited"] = False

    def mutate_superseded_count(payload: dict[str, Any]) -> None:
        payload["superseded_or_retried_clean_guard_sessions"] = 0

    def mutate_transport_disk(payload: dict[str, Any]) -> None:
        value = DYNAMIC_RESERVE_BYTES - 1
        payload["transport_completion_disk_metrics"]["topup_background"]["min_free_bytes"] = value
        payload["transport_completion_disk_metrics"]["min_free_bytes"] = value
        payload["min_new_transport_completion_free_bytes"] = value
        payload["min_all_dynamic_disk_observations_bytes"] = value

    def mutate_receipt_metric_closure(payload: dict[str, Any]) -> None:
        payload["transport_completion_disk_metrics"]["all_new_transport_receipts_have_exactly_one_pass_metric"] = False

    def mutate_completion_log(payload: dict[str, Any]) -> None:
        payload["resource_completion_event_log"]["sha256"] = "f" * 64

    def mutate_wal_log(payload: dict[str, Any]) -> None:
        payload["guard_session_wal"]["sha256"] = "f" * 64

    def mutate_wal_count(payload: dict[str, Any]) -> None:
        payload["guard_session_wal_audit"]["rows"] = 5

    def mutate_wal_duplicate_policy(payload: dict[str, Any]) -> None:
        payload["guard_session_wal_audit"]["duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct"] = False

    def mutate_wal_order(payload: dict[str, Any]) -> None:
        payload["guard_sessions"][0]["guard_session_wal_started_at"] = payload["complete_guard_event_log_audit"]["sessions"][1]["started_at"]

    def mutate_completion_registry(payload: dict[str, Any]) -> None:
        payload["guarded_completion_authorities"].pop("build_fullstat_prompt")

    def mutate_completion_registry_pass(payload: dict[str, Any]) -> None:
        payload["all_guarded_completion_authorities_independently_validated"] = False

    def mutate_session_canonical_authority(payload: dict[str, Any]) -> None:
        payload["guard_sessions"][0]["canonical_completion_authority"]["sha256"] = "f" * 64

    def mutate_completion_mode(payload: dict[str, Any]) -> None:
        payload["guard_sessions"][0]["completion_record_mode"] = "MIXED_NORMAL_AND_RECOVERED"

    def mutate_no_live_inference(payload: dict[str, Any]) -> None:
        payload["all_completion_resources_from_original_guard_closure_not_live_inference"] = False

    def mutate_original_closure(payload: dict[str, Any]) -> None:
        payload["guard_sessions"][0]["completion_disk_free_bytes"] += 1

    def mutate_complete_byte_partition(payload: dict[str, Any]) -> None:
        payload["complete_guard_event_log_audit"]["sessions"][1]["guard_log_start_byte"] += 1

    def mutate_guard_sample_minimum(payload: dict[str, Any]) -> None:
        payload["min_guard_sample_disk_free_bytes"] += 1

    mutations = {
        "old_28_plus_delayed_total": mutate_total,
        "worker6": mutate_worker,
        "quota600": mutate_quota,
        "manifest_digest_mismatch": mutate_manifest,
        "missing_guard_session": mutate_missing_session,
        "label_phase_mismatch": mutate_phase,
        "complete_guard_bytes_not_audited": mutate_complete_guard,
        "superseded_guard_count_mismatch": mutate_superseded_count,
        "transport_disk_below_8GiB": mutate_transport_disk,
        "receipt_metric_closure_false": mutate_receipt_metric_closure,
        "resource_completion_log_digest_mismatch": mutate_completion_log,
        "guard_session_WAL_digest_mismatch": mutate_wal_log,
        "guard_session_WAL_count_cannot_cover_keys_and_orphans": mutate_wal_count,
        "guard_session_WAL_duplicate_key_policy_false": mutate_wal_duplicate_policy,
        "guard_session_WAL_not_before_guard": mutate_wal_order,
        "missing_canonical_guarded_completion_authority": mutate_completion_registry,
        "guarded_completion_independent_validation_false": mutate_completion_registry_pass,
        "session_canonical_completion_binding_mismatch": mutate_session_canonical_authority,
        "mixed_normal_recovery_mode": mutate_completion_mode,
        "live_resource_inference_allowed": mutate_no_live_inference,
        "original_guard_closure_resource_mismatch": mutate_original_closure,
        "complete_guard_byte_partition_gap": mutate_complete_byte_partition,
        "guard_sample_disk_minimum_mismatch": mutate_guard_sample_minimum,
    }
    for label, mutate in mutations.items():
        payload = json.loads(json.dumps(fixture_resource()))
        mutate(payload)
        rejected = Checker()
        validate_resource_timeline(payload, 7, 1, rejected)
        check.expect(bool(rejected.errors), f"synthetic invalid resource fixture was accepted: {label}")


def exercise_delayed_cross_stage_fixture(check: Checker) -> None:
    sources = fixture_source_rows()
    positive = list(FAMILIES[:-1])
    zero = [FAMILIES[-1]]
    cards = [
        {
            "family": row["incident_family"],
            "registered_events": FULLSTAT_DELAYED_EVENTS,
            "actual_transport_events": row["actual_transport_triggers"],
            "execution_disposition": row["execution_disposition"],
        }
        for row in sources
    ]
    receipts = [
        {
            "family": family,
            "registered_events": FULLSTAT_DELAYED_EVENTS,
            "events": FULLSTAT_DELAYED_EVENTS,
            "actual_transport_events": FULLSTAT_DELAYED_EVENTS,
            "execution_disposition": stage02.POSITIVE_DISPOSITION,
            "transport_eligible": True,
            "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
        }
        for family in positive
    ]
    coverage = [
        {
            "family": row["incident_family"],
            "execution_disposition": row["execution_disposition"],
            "triggers": row["actual_transport_triggers"],
            "central_delayed_rate_cps": (
                0.0
                if row["execution_disposition"] == stage02.ZERO_DISPOSITION
                else "DEFERRED_TO_STAGE04_FROM_RAW_CATALOG"
            ),
            "finite_upper_limit_status": (
                "FINITE_TWO_SIDED95_GARWOOD"
                if row["execution_disposition"] == stage02.ZERO_DISPOSITION
                else "NOT_APPLICABLE_TO_POSITIVE_A15_CELL"
            ),
        }
        for row in sources
    ]
    upper = stage03.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / 10.0
    zero_rows = [
        {
            "family": zero[0],
            "execution_disposition": stage02.ZERO_DISPOSITION,
            "central_delayed_rate_cps": 0.0,
            "transported_ground_rate_upper95_s-1": upper,
            "transported_ground_A15_upper95_Bq_conservative": upper,
            "stage03_catalog_opened": False,
            "SIM_opened": False,
        }
    ]
    closure, observed_positive, observed_zero = validate_delayed_cross_stage(
        sources,
        {
            "selected_buildup_jobs": 23,
            "selected_buildup_histories": EXPECTED_BUILDUP_HISTORIES,
            "registered_delayed_source_cells": 8,
            "fresh_delayed_transport_jobs_planned": 7,
            "delayed_zero_source_jobs_skipped": 1,
            "plan1_83334_consumed_or_merged": False,
            "incremental_166666_merge_allowed": False,
        },
        {
            "registered_delayed_source_cells": 8,
            "fresh_delayed_transport_jobs": 7,
            "zero_A15_skipped_jobs": 1,
            "registered_events_per_family": FULLSTAT_DELAYED_EVENTS,
            "plan1_delayed_consumed": False,
            "incremental_83334_plus_166666_merge_allowed": False,
            "source_cards": cards,
        },
        {
            "registered_families": 8,
            "positive_A15_families": positive,
            "zero_A15_families": zero,
            "planned_transport_jobs": 7,
            "validated_transport_jobs": 7,
            "fresh_triggers_per_positive_family": FULLSTAT_DELAYED_EVENTS,
            "validated_fresh_triggers": 7 * FULLSTAT_DELAYED_EVENTS,
            "zero_A15_jobs_skipped": 1,
            "plan1_83334_read": False,
            "plan1_83334_pooled": False,
            "incremental_merge_used": False,
            "selected_receipts": receipts,
        },
        {
            "registered_source_cells": 8,
            "transport_jobs": 7,
            "skipped_zero_A15_jobs": 1,
            "transport_triggers_per_family": FULLSTAT_DELAYED_EVENTS,
            "plan1_83334_read": False,
            "plan1_83334_pooled": False,
            "incremental_83334_plus_166666_merge_used": False,
        },
        coverage,
        zero_rows,
        check,
    )
    check.expect(
        len(closure) == 8
        and observed_positive == positive
        and observed_zero == zero,
        "synthetic delayed cross-stage fixture did not close",
    )


def exercise_passive_w_fixture(check: Checker) -> None:
    volumes = list(stage01.PASSIVE_W_VOLUMES)
    delayed_w_rows = [
        {
            "family": family,
            "passive_w_volumes_json": json.dumps(volumes, separators=(",", ":")),
            "veto_role": (
                "PASSIVE_DIAGNOSTIC_ONLY__NO_SIM_FOR_ZERO_A15"
                if family == FAMILIES[-1]
                else "PASSIVE_DIAGNOSTIC_ONLY__NOT_BGO_OR_PLASTIC_VETO"
            ),
        }
        for family in FAMILIES
    ]
    result = validate_passive_w(
        {
            "active_veto": {
                "shield_volumes": ["B1", "B2", "B3"],
                "plastic_volumes": ["P1", "P2", "P3"],
                "active_veto_volumes": ["B1", "B2", "B3", "P1", "P2", "P3"],
                "passive_w_volumes": volumes,
                "passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
            }
        },
        {
            "status": "PASS__EXACT_THREE_SF3_W_VOLUMES_DIAGNOSTIC_AND_PASSIVE",
            "exact_volume_whitelist": volumes,
            "passive_w_never_veto": True,
            "bgo_veto_members": 0,
            "plastic_veto_members": 0,
        },
        {
            "passive_w_diagnostics": {
                "passive_w_volumes": volumes,
                "role": "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES",
            }
        },
        delayed_w_rows,
        {
            "passive_w": {
                "volumes": volumes,
                "role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
                "active_veto_members": 0,
            }
        },
        [{"passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO"}],
        check,
    )
    check.expect(
        result.get("passive_w_active_veto_members") == 0,
        "synthetic passive-W fixture did not remain disjoint",
    )


def exercise_signal_fixture(check: Checker) -> None:
    rows = [
        {
            "geometry": "SF3",
            "window_id": "w2_510p58_511p42",
            "trials": str(EXPECTED_SIGNAL_TRIALS),
            "selected_events": "20000",
        }
    ]
    authorities = {
        "plan1_signal_acceptance": {
            "path": "/synthetic/plan1_signal.csv",
            "bytes": 100,
            "sha256": "b" * 64,
        },
        "full04_signal": {
            "path": "/synthetic/fullstat_signal.csv",
            "bytes": 100,
            "sha256": "b" * 64,
        },
    }
    result = validate_signal_anchor(
        rows,
        [dict(row) for row in rows],
        {
            "signal": {
                "reuse_authority": stage04.SIGNAL_REUSE_AUTHORITY,
                "semantic_signal_SIM_scans_in_this_adapter": 0,
                "signal_SIM_or_receipt_artifact_opened_in_this_adapter": False,
                "final_w2": {"trials": EXPECTED_SIGNAL_TRIALS},
            }
        },
        {
            "signal_reuse": {
                "status": "PASS__IDENTICAL_FRESH_SF3_37194_SIGNAL_ACCEPTANCE_SMALL_TABLE",
                "trials": EXPECTED_SIGNAL_TRIALS,
                "plan1_sha256": "b" * 64,
                "fullstat_sha256": "b" * 64,
                "fresh_signal_transport_rerun_for_fullstat": False,
            }
        },
        authorities,
        check,
    )
    check.expect(
        result.get("sha256") == "b" * 64,
        "synthetic fresh-37194 signal hash anchor did not close",
    )


def exercise_entry_gate_fixture(check: Checker) -> None:
    authorities = {
        "plan1_mission": {"sha256": "c" * 64},
        "plan1_closure": {"sha256": "d" * 64},
    }
    result = validate_plan1_entry_gate(
        {
            "status": "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE",
            "fullstat_gate": {
                "observed_central_ratio": 0.75,
                "metric": "F3_SF3_over_SE3_full_envelope",
                "operator": "<=",
                "threshold": 0.75,
                "topup_required": True,
                "decision": "TOPUP_TO_S3D_FULL_STAT_REQUIRED",
                "proxy_controls_gate": False,
            },
        },
        {
            "status": "PASS__SF3_PLAN1_CHAIN_COMPLETE__SYNTHETIC",
            "ready": True,
            "errors": [],
            "missing": [],
            "fullstat_disposition": {
                "topup_required": True,
                "observed_central_ratio": 0.75,
            },
        },
        {
            "status": "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED",
            "plan": {"jobs": 28},
            "aggregation": {"combined_jobs": 49},
            "plan1_mutation": False,
            "transport": {"launched": False},
            "gate_authorization": {
                "mission_sha256": "c" * 64,
                "closure_sha256": "d" * 64,
            },
        },
        {
            "status": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
            "planned_jobs": 28,
            "validated_jobs": 28,
            "instant_validated_events": 2_561_382,
            "buildup_validated_events": 2_030_976,
        },
        {
            "plan1_entry_gate": {
                "role": "ONE_TIME_ENTRY_GATE_ONLY__NOT_REAPPLIED_AFTER_FULLSTAT",
                "authorized": True,
                "observed_central_ratio": 0.75,
            },
            "ratio_contract": {
                "phase_gate": "NONE__FINAL_REPORT",
                "second_topup_authorized": False,
            },
            "terminal_fullstat_comparison": {
                "second_topup_gate_evaluated": False,
                "second_topup_authorized": False,
                "proxy_controls_any_gate": False,
            },
            "second_topup_evaluated_or_launched": False,
        },
        authorities,
        check,
    )
    check.expect(
        result.get("authorization_evaluation_count") == 1
        and result.get("reapplied_after_fullstat") is False,
        "synthetic Plan1 one-time entry gate did not close",
    )


def self_test() -> dict[str, Any]:
    check = Checker()
    background = validate_background_contract(
        fixture_background_rows("instant"), fixture_background_rows("buildup"), check
    )
    delayed, positive, zero = normalize_source_cells(fixture_source_rows(), check)
    mission_summary, timeline, comparison = fixture_mission()
    mission = validate_mission(mission_summary, timeline, comparison, check)
    resource = validate_resource_timeline(fixture_resource(), len(positive), len(zero), check)
    exercise_resource_negative_fixtures(check)
    exercise_delayed_cross_stage_fixture(check)
    exercise_passive_w_fixture(check)
    exercise_signal_fixture(check)
    exercise_entry_gate_fixture(check)
    retained = stage06.self_test()
    check.expect(
        retained.get("status") == "PASS__SF3_FULLSTAT_FINAL_MISSION_SYNTHETIC_SELF_TEST",
        "locked stage06 synthetic arithmetic selftest did not PASS",
    )
    for ratio, allowed in ((0.75, True), (0.7500001, False)):
        check.expect((ratio <= 0.75) is allowed, "one-time central entry-gate boundary differs")
    try:
        sha256_small(Path("/synthetic/never-query.sim.gz"))
    except RuntimeError as exc:
        check.expect("before filesystem query" in str(exc), "SIM guard error occurred after filesystem query")
    else:
        check.errors.append("SIM guard did not reject before filesystem query")
    check.expect(len(background) == 16, "synthetic background family/mode closure !=16")
    check.expect(len(delayed) == 8 and len(positive) == 7 and len(zero) == 1, "synthetic delayed positive/zero closure differs")
    check.expect(mission.get("timeline_rows") == 162, "synthetic mission timeline closure differs")
    check.expect(resource.get("actual_workers_observed") == [4], "synthetic resource worker closure differs")
    check.expect(set(resource.get("quota_percent_observed", [])) == {300, 400}, "synthetic resource exact 300/400 quota closure differs")
    check.expect(resource.get("superseded_or_retried_clean_guard_sessions") == 1, "synthetic complete guard-log retry closure differs")
    check.expect(resource.get("normal_completion_records") == 4 and resource.get("crash_recovered_completion_records") == 1, "synthetic resource normal/recovery XOR closure differs")
    check.expect(resource.get("all_guarded_completion_authorities_independently_validated") is True, "synthetic independent guarded completion authority closure differs")
    check.expect((resource.get("guard_session_wal_audit") or {}).get("orphan_pre_guard_crash_rows") == 1, "synthetic legal pre-guard WAL orphan closure differs")
    if check.errors:
        raise AssertionError("; ".join(check.errors))
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": "PASS__SF3_FULLSTAT_TERMINAL_AUDIT_PURE_SYNTHETIC_SELF_TEST",
        "checks": [
            "49_background_jobs_equal_26_instant_plus_23_buildup",
            "append_only_shards_close_exactly_to_S3d_fullstat_per_family_mode",
            "eight_delayed_cells_positive_fresh250k_or_zero_finite_upper_skip",
            "delayed_02_03_04_cross_stage_receipt_and_zero_provenance_closure",
            "Plan1_83334_never_read_or_pooled",
            "three_exact_W_volumes_passive_across_01_02_03_04_and_disjoint_from_6_active_veto",
            "Plan1_and_fullstat_37194_signal_acceptance_byte_hash_anchor",
            "locked_stage06_81node_algorithm_selftest",
            "162_node_central_and_componentwise_proxy_arithmetic",
            "one_time_Plan1_central_gate_boundary_at_0p75",
            "terminal_no_second_topup_policy",
            "resource_actual_workers_exactly4_with_quota_exactly300_or400",
            "five_exact_guarded_labels_phases_and_manifest_digest_binding",
            "complete_guard_event_log_all_bytes_and_clean_retries_audited",
            "guard_session_WAL_bound_before_guard_with_legal_pre_guard_orphan_policy",
            "normal_XOR_crash_recovery_uses_original_guard_closure_without_live_inference",
            "five_independent_canonical_guarded_completion_authorities",
            "guard_sample_and_guard_completion_disk_minima_recomputed_separately",
            "21_Plan1_plus28_topup_plus_fresh250k_transport_resource_metrics",
            "resource_schema_negative_fixtures_reject_stale_or_noncanonical_evidence",
            "MemAvailable_1p5GiB_SwapFree_8GiB_dynamic_disk_8GiB_floors",
            "SIM_guard_rejects_before_open_stat_or_hash",
        ],
        "output": norm(OUTPUT),
        "files_written": False,
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_or_topup_launched": False,
        "second_topup_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true", help="pure/static synthetic contracts only")
    actions.add_argument("--check-prerequisites", action="store_true", help="fixed small CSV/JSON authorities only")
    actions.add_argument("--build", action="store_true", help="publish the write-once terminal audit; never transport/SIM")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites:
            result = check_prerequisites()
        else:
            result = build()
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready"):
            return 1 if result.get("errors") else 2
        return 0
    except Exception as exc:
        print(
            json_text(
                {
                    "schema_version": 1,
                    "profile_id": PROFILE_ID,
                    "status": "FAIL__SF3_FULLSTAT_TERMINAL_AUDIT_ADAPTER",
                    "error": str(exc),
                    "SIM_opened_statted_discovered_or_hashed": False,
                    "transport_or_topup_launched": False,
                    "second_topup_authorized": False,
                }
            ),
            end="",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
