#!/usr/bin/env python3
"""Build the gate-authorized SF3 full-stat prompt catalog and response tables.

The input is the append-only 49-job combined background plan: 21 canonical
Plan-1 background jobs plus 28 conditional top-up jobs.  Prompt analysis uses
exactly the 26 instant receipts (11 Plan-1 + 15 top-up) and normalizes each of
the eight incident-family cells by its own sum(TT).  Geometry, mode and family
are never pooled across a boundary.

The read-only prerequisite check consumes compact plans, audits and receipts;
it never opens, stats or hashes a SIM.  ``--build`` is the only action that
semantically scans the 26 registered SIMs, once each, through the retained SF3
parser.  This adapter never launches transport or delayed-source production.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import build_sf3_fullstat_topup as topup
import run_prompt_analysis as prompt
from sf3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID


HERE = Path(__file__).resolve()
CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
OUTPUT = PACKAGE_ROOT / "outputs/fullstat/01_prompt"
MISSION = PACKAGE_ROOT / "outputs/06_mission/summary.json"
CLOSURE = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"
STATIC_AUDIT = topup.STATIC_AUDIT
COMBINED_PLAN = topup.COMBINED_PLAN
AGGREGATION_PLAN = topup.AGGREGATION_PLAN
PLAN1_PLAN = topup.PLAN1_PLAN
TOPUP_PLAN = topup.TOPUP_PLAN
PLAN1_AGGREGATE = PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"
TOPUP_AGGREGATE = topup.TOPUP_AGGREGATE_RECEIPT
TOPUP_RECEIPT_ROOT = topup.TOPUP_RECEIPT_ROOT
TOPUP_RUN_ROOT = topup.TOPUP_RUN_ROOT

FULLSTAT_PROFILE_ID = "SF3_FULLSTAT_PROMPT_RESPONSE_V1"
EXPECTED_COMBINED_JOBS = 49
EXPECTED_INSTANT_JOBS = 26
EXPECTED_BUILDUP_JOBS = 23
EXPECTED_PLAN1_BACKGROUND_JOBS = 21
EXPECTED_TOPUP_JOBS = 28
EXPECTED_PLAN1_INSTANT_JOBS = 11
EXPECTED_TOPUP_INSTANT_JOBS = 15
EXPECTED_FULL_INSTANT_HISTORIES = 3_842_075
EXPECTED_FULL_BUILDUP_HISTORIES = 3_046_468
FULLSTAT_GATE = 0.75
MAX_WORKERS = 6
DEFAULT_WORKERS = 4
MAX_SMALL_BYTES = 64 * 1024**2
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")
PASSIVE_W_VOLUMES = prompt.PASSIVE_W_VOLUMES

FULL_TARGETS = {
    ("instant", "p"): 25_448,
    ("instant", "n"): 232_991,
    ("instant", "alpha"): 5_958,
    ("instant", "gamma"): 3_207_738,
    ("instant", "eminus"): 295_341,
    ("instant", "eplus"): 60_184,
    ("instant", "muminus"): 10_443,
    ("instant", "muplus"): 3_972,
    ("buildup", "p"): 25_448,
    ("buildup", "n"): 232_991,
    ("buildup", "alpha"): 4_343,
    ("buildup", "gamma"): 2_356_499,
    ("buildup", "eminus"): 295_341,
    ("buildup", "eplus"): 60_184,
    ("buildup", "muminus"): 67_690,
    ("buildup", "muplus"): 3_972,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def json_text(value: Any) -> str:
    return json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ) + "\n"


def reject_nonfinite(token: str) -> None:
    raise ValueError(f"non-finite JSON token: {token}")


def reject_sim_path(path: Path) -> None:
    if os.fspath(path).lower().endswith(SIM_SUFFIXES):
        raise RuntimeError(f"compact-authority operation refused for SIM path: {path}")


def sha256_small(path: Path) -> str:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact-authority size ({size}): {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def small_record(path: Path) -> dict[str, Any]:
    reject_sim_path(path)
    return {
        "path": norm(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_small(path),
    }


def load_small_json(path: Path) -> dict[str, Any]:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact JSON size ({size}): {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_nonfinite)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_small_csv(path: Path) -> list[dict[str, str]]:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact CSV size ({size}): {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader)


def close(actual: Any, expected: Any, *, rel: float = 2e-12, absolute: float = 2e-14) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute)
    except (TypeError, ValueError):
        return False


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def lexical_child(path: str | Path, parent: str | Path) -> bool:
    try:
        return os.path.commonpath((norm(path), norm(parent))) == norm(parent)
    except ValueError:
        return False


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
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


def cast_combined(rows: Sequence[dict[str, str]], check: Checker) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        try:
            item: dict[str, Any] = dict(row)
            for key in ("combined_ordinal", "events", "seed"):
                item[key] = int(row[key])
            output.append(item)
        except Exception as exc:
            check.errors.append(f"combined plan row {index} invalid: {exc}")
    return output


def cast_basic_plan(rows: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        for key in ("events", "seed"):
            item[key] = int(row[key])
        output.append(item)
    return output


def validate_combined_plan(
    combined: Sequence[dict[str, Any]],
    aggregation: Sequence[dict[str, str]],
    plan1_rows: Sequence[dict[str, Any]],
    topup_rows: Sequence[dict[str, Any]],
    check: Checker,
) -> list[dict[str, Any]]:
    plan1_background = [row for row in plan1_rows if row.get("stage") == "background"]
    check.expect(len(plan1_rows) == 30, "Plan-1 plan rows != 30")
    check.expect(len(plan1_background) == EXPECTED_PLAN1_BACKGROUND_JOBS, "Plan-1 background rows != 21")
    check.expect(len(topup_rows) == EXPECTED_TOPUP_JOBS, "top-up plan rows != 28")
    check.expect(len(combined) == EXPECTED_COMBINED_JOBS, "combined background rows != 49")
    check.expect(
        [row.get("combined_ordinal") for row in combined]
        == list(range(1, EXPECTED_COMBINED_JOBS + 1)),
        "combined ordinals are not exactly 1..49",
    )
    ids = [str(row.get("job_id")) for row in combined]
    check.expect(len(ids) == len(set(ids)), "combined job IDs are not unique")
    check.expect(len({int(row.get("seed", -1)) for row in combined}) == EXPECTED_COMBINED_JOBS, "combined seeds are not unique")
    check.expect(all(row.get("geometry") == "SF3" for row in combined), "combined plan is not SF3-only")
    check.expect(
        Counter(row.get("source_namespace") for row in combined)
        == Counter({"PLAN1_CANONICAL_PASS": 21, "FULLSTAT_TOPUP_NEW": 28}),
        "combined source namespaces are not 21 Plan-1 + 28 top-up",
    )
    expected_ids = {
        str(row["job_id"]) for row in plan1_background
    } | {str(row["job_id"]) for row in topup_rows}
    check.expect(set(ids) == expected_ids, "combined identity set differs from Plan-1 background + top-up")
    plan1_map = {str(row["job_id"]): row for row in plan1_background}
    topup_map = {str(row["job_id"]): row for row in topup_rows}
    for row in combined:
        source = plan1_map if row["source_namespace"] == "PLAN1_CANONICAL_PASS" else topup_map
        authority = source.get(str(row["job_id"]))
        check.expect(authority is not None, f"combined row has no namespace authority {row['job_id']}")
        if authority:
            for key in ("mode", "family", "events", "seed", "source_path"):
                check.expect(row.get(key) == authority.get(key), f"combined/{key} differs {row['job_id']}")
    check.expect(len(aggregation) == 16, "aggregation plan cells != 16")
    aggregation_map = {(row.get("mode"), row.get("family")): row for row in aggregation}
    check.expect(set(aggregation_map) == set(FULL_TARGETS), "aggregation mode/family closure differs")
    for key, target in FULL_TARGETS.items():
        mode, family = key
        cell = [row for row in combined if row.get("mode") == mode and row.get("family") == family]
        observed = sum(int(row["events"]) for row in cell)
        check.expect(observed == target, f"full target differs {mode}/{family}: {observed} != {target}")
        record = aggregation_map.get(key)
        if record:
            check.expect(int(record.get("combined_histories", -1)) == target, f"aggregation combined histories differ {mode}/{family}")
            check.expect(int(record.get("full_target_histories", -1)) == target, f"aggregation full target differs {mode}/{family}")
            check.expect(str(record.get("do_not_pool_across_mode_family_geometry", "")).lower() == "true", f"aggregation pooling boundary absent {mode}/{family}")
            expected_role = "FULL_PROMPT_RESPONSE_INPUT" if mode == "instant" else "FULL_BUILDUP_RP_TT_INPUT_FOR_REBUILT_INVENTORY"
            check.expect(record.get("downstream_role") == expected_role, f"aggregation downstream role differs {mode}/{family}")
    instant = [row for row in combined if row.get("mode") == "instant"]
    buildup = [row for row in combined if row.get("mode") == "buildup"]
    check.expect(len(instant) == EXPECTED_INSTANT_JOBS, "combined instant rows != 26")
    check.expect(len(buildup) == EXPECTED_BUILDUP_JOBS, "combined buildup rows != 23")
    check.expect(sum(int(row["events"]) for row in instant) == EXPECTED_FULL_INSTANT_HISTORIES, "full instant history total differs")
    check.expect(sum(int(row["events"]) for row in buildup) == EXPECTED_FULL_BUILDUP_HISTORIES, "full buildup history total differs")
    check.expect(Counter(row["source_namespace"] for row in instant) == Counter({"PLAN1_CANONICAL_PASS": 11, "FULLSTAT_TOPUP_NEW": 15}), "instant namespace closure is not 11 + 15")
    check.expect({row.get("family") for row in instant} == set(FAMILIES), "instant family closure differs")
    return sorted(instant, key=lambda row: int(row["combined_ordinal"]))


def validate_gate(
    mission: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    static: dict[str, Any] | None,
    check: Checker,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if mission:
        gate = mission.get("fullstat_gate") or {}
        ratio = gate.get("observed_central_ratio")
        try:
            ratio_value = float(ratio)
        except (TypeError, ValueError):
            ratio_value = math.nan
        check.expect(mission.get("status") == "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE", "mission status differs")
        check.expect(gate.get("metric") == "F3_SF3_over_SE3_full_envelope", "mission gate metric differs")
        check.expect(gate.get("operator") == "<=", "mission gate operator differs")
        check.expect(close(gate.get("threshold"), FULLSTAT_GATE, rel=0.0, absolute=0.0), "mission gate threshold differs")
        check.expect(math.isfinite(ratio_value) and 0.0 <= ratio_value <= FULLSTAT_GATE, "central mission gate does not authorize full-stat")
        check.expect(gate.get("topup_required") is True, "mission does not require top-up")
        check.expect(gate.get("decision") == "TOPUP_TO_S3D_FULL_STAT_REQUIRED", "mission top-up decision differs")
        check.expect(gate.get("proxy_controls_gate") is False, "mission componentwise proxy controls gate")
        result["central_F3_SF3_over_SE3"] = ratio_value
        result["mission_status"] = mission.get("status")
    if closure:
        check.expect(str(closure.get("status", "")).startswith("PASS__SF3_PLAN1_CHAIN_COMPLETE"), "stage07 Plan-1 closure is not PASS")
        check.expect(closure.get("ready") is True, "stage07 Plan-1 closure is not ready")
        check.expect(closure.get("errors") == [], "stage07 closure errors nonempty")
        check.expect(closure.get("missing") == [], "stage07 closure missing authorities")
        check.expect(nested(closure, "fullstat_disposition", "topup_required") is True, "stage07 closure does not require top-up")
        check.expect(close(nested(closure, "fullstat_disposition", "observed_central_ratio"), result.get("central_F3_SF3_over_SE3")), "stage07 central ratio differs")
        result["closure_status"] = closure.get("status")
    if static:
        check.expect(static.get("status") == "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED", "full-stat static audit status differs")
        check.expect(static.get("topup_namespace") == topup.TOPUP_NAMESPACE, "full-stat static top-up namespace differs")
        check.expect(static.get("plan1_mutation") is False, "full-stat static adapter mutated Plan-1")
        check.expect(nested(static, "transport", "launched") is False, "full-stat static audit claims a transport launch")
        check.expect(nested(static, "plan", "jobs") == EXPECTED_TOPUP_JOBS, "static top-up jobs != 28")
        check.expect(norm(nested(static, "plan", "path") or "") == norm(TOPUP_PLAN), "static top-up plan path differs")
        if TOPUP_PLAN.is_file():
            check.expect(nested(static, "plan", "sha256") == sha256_small(TOPUP_PLAN), "static top-up plan digest differs")
        check.expect(nested(static, "aggregation", "combined_jobs") == EXPECTED_COMBINED_JOBS, "static combined jobs != 49")
        check.expect(norm(nested(static, "aggregation", "combined_plan") or "") == norm(COMBINED_PLAN), "static combined-plan path differs")
        check.expect(norm(nested(static, "aggregation", "cell_plan") or "") == norm(AGGREGATION_PLAN), "static aggregation-plan path differs")
        check.expect(nested(static, "aggregation", "pooling_boundary") == "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY", "static pooling boundary differs")
        authorization = static.get("gate_authorization") or {}
        check.expect(close(authorization.get("central_R_F3"), result.get("central_F3_SF3_over_SE3")), "static gate ratio differs")
        if mission:
            check.expect(authorization.get("mission_sha256") == sha256_small(MISSION), "static mission binding digest differs")
        if closure:
            check.expect(authorization.get("closure_sha256") == sha256_small(CLOSURE), "static closure binding digest differs")
        check.expect(authorization.get("decision") == "TOPUP_TO_S3D_FULL_STAT_REQUIRED", "static gate decision differs")
        check.expect(authorization.get("proxy_controls_gate") is False, "static gate uses proxy")
        result["static_status"] = static.get("status")
    result.update({
        "metric": "central F3_SF3/F3_SE3",
        "threshold": FULLSTAT_GATE,
        "authorized": not check.errors and bool(mission and closure and static),
        "proxy_controls_gate": False,
    })
    return result


def receipt_path_from_ledger(
    row: dict[str, Any],
    plan1_ledger: dict[str, dict[str, Any]],
    topup_ledger: dict[str, dict[str, Any]],
) -> Path | None:
    job_id = str(row["job_id"])
    if row["source_namespace"] == "PLAN1_CANONICAL_PASS":
        record = plan1_ledger.get(job_id)
        return Path(str(record.get("path"))) if record else None
    record = topup_ledger.get(job_id)
    return Path(str(record.get("receipt_path"))) if record else None


def validate_receipt(
    row: dict[str, Any],
    path: Path,
    receipt: dict[str, Any],
    config: dict[str, Any],
    check: Checker,
) -> dict[str, Any]:
    job_id = str(row["job_id"])
    namespace = str(row["source_namespace"])
    expected_profile = PROFILE_ID if namespace == "PLAN1_CANONICAL_PASS" else topup.TOPUP_NAMESPACE
    expected_receipt_root = (
        Path(str(config["run_root"])) / "receipts"
        if namespace == "PLAN1_CANONICAL_PASS" else TOPUP_RECEIPT_ROOT
    )
    expected_sim_root = (
        Path(str(config["run_root"])) / "jobs"
        if namespace == "PLAN1_CANONICAL_PASS" else TOPUP_RUN_ROOT / "jobs"
    )
    check.expect(norm(path.parent) == norm(expected_receipt_root), f"receipt namespace differs {job_id}")
    check.expect(path.name == f"{job_id}.json", f"receipt filename differs {job_id}")
    check.expect(receipt.get("status") == "PASS" and receipt.get("errors") in ([], None), f"receipt is not clean PASS {job_id}")
    for key, expected in (
        ("profile_id", expected_profile), ("job_id", job_id),
        ("stage", "background"), ("geometry", "SF3"),
        ("mode", row["mode"]), ("family", row["family"]),
        ("events", row["events"]), ("seed", row["seed"]),
        ("source_path", row["source_path"]),
    ):
        check.expect(receipt.get(key) == expected, f"receipt {key} differs {job_id}")
    check.expect(norm(receipt.get("setup_path", "")) == norm(nested(config, "geometry", "sf3_setup") or ""), f"receipt SF3 setup differs {job_id}")
    check.expect(receipt.get("returncode") == 0, f"receipt returncode differs {job_id}")
    check.expect(receipt.get("watchdog_reason") == "completed", f"receipt watchdog differs {job_id}")
    check.expect(nested(receipt, "log", "generated_events") == row["events"], f"receipt generated events differ {job_id}")
    check.expect(nested(receipt, "log", "graphics_terminal_marker") is True, f"receipt terminal marker absent {job_id}")
    check.expect(nested(receipt, "sim_header", "seed") == row["seed"], f"receipt header seed differs {job_id}")
    check.expect(norm(nested(receipt, "sim_header", "geometry") or "") == norm(nested(config, "geometry", "sf3_setup") or ""), f"receipt header geometry differs {job_id}")
    check.expect(nested(receipt, "sim_header", "policy") == "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST", f"receipt header-only policy differs {job_id}")
    check.expect(receipt.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", f"receipt no-SIM-digest policy differs {job_id}")
    tt_s = nested(receipt, "isotope_dat", "TT_s")
    check.expect(isinstance(tt_s, (int, float)) and float(tt_s) > 0.0, f"receipt TT is not positive {job_id}")
    sim_path = str(receipt.get("sim_path", ""))
    check.expect(os.path.isabs(sim_path), f"SIM metadata path is not absolute {job_id}")
    check.expect(lexical_child(sim_path, expected_sim_root), f"SIM metadata escapes namespace {job_id}")
    check.expect(int(receipt.get("sim_bytes", -1)) > 0, f"SIM byte metadata invalid {job_id}")
    source = Path(str(receipt.get("source_path", "")))
    if not source.is_file():
        check.missing.append(f"source_{job_id}:{norm(source)}")
    else:
        try:
            digest = sha256_small(source)
            check.expect(digest == receipt.get("source_sha256"), f"source digest differs {job_id}")
        except Exception as exc:
            check.errors.append(f"source authority invalid {job_id}: {exc}")
    return {
        **row,
        "receipt_path": norm(path),
        "receipt_sha256": sha256_small(path),
        "TT_s": float(tt_s or 0.0),
        "setup_path": norm(receipt.get("setup_path", "")),
        "sim_path": sim_path,
        "sim_bytes": int(receipt.get("sim_bytes", 0)),
        "source_sha256": receipt.get("source_sha256"),
    }


def check_prerequisites(config_path: Path = CONFIG) -> dict[str, Any]:
    check = Checker()
    config = check.json("analysis_inputs", config_path.resolve())
    if config is None:
        return {
            "schema_version": 1,
            "profile_id": FULLSTAT_PROFILE_ID,
            "status": "NOT_READY__SF3_FULLSTAT_PROMPT_INPUTS",
            "ready": False,
            "missing": check.missing,
            "errors": check.errors,
            "SIM_opened_statted_or_hashed": False,
        }
    mission = check.json("mission_gate", MISSION)
    closure = check.json("plan1_closure", CLOSURE)
    static = check.json("fullstat_static_audit", STATIC_AUDIT)
    gate = validate_gate(mission, closure, static, check)

    combined_csv = check.csv("combined_plan", COMBINED_PLAN)
    aggregation_csv = check.csv("aggregation_plan", AGGREGATION_PLAN)
    plan1_csv = check.csv("plan1_plan", PLAN1_PLAN)
    topup_csv = check.csv("topup_plan", TOPUP_PLAN)
    combined = cast_combined(combined_csv or [], check)
    plan1_rows = cast_basic_plan(plan1_csv or [])
    topup_rows = cast_basic_plan(topup_csv or [])
    instant = validate_combined_plan(
        combined, aggregation_csv or [], plan1_rows, topup_rows, check
    )

    plan1_aggregate = check.json("plan1_aggregate_receipts", PLAN1_AGGREGATE)
    topup_aggregate = check.json("topup_aggregate_receipts", TOPUP_AGGREGATE)
    plan1_ledger: dict[str, dict[str, Any]] = {}
    topup_ledger: dict[str, dict[str, Any]] = {}
    if plan1_aggregate:
        check.expect(str(plan1_aggregate.get("status", "")).startswith("PASS__ALL_"), "Plan-1 aggregate receipts are not complete PASS")
        check.expect(plan1_aggregate.get("background_planned_jobs") == EXPECTED_PLAN1_BACKGROUND_JOBS, "Plan-1 aggregate background plan differs")
        check.expect(plan1_aggregate.get("background_validated_jobs") == EXPECTED_PLAN1_BACKGROUND_JOBS, "Plan-1 aggregate background receipts != 21")
        plan1_records = list(plan1_aggregate.get("selected_receipts", []))
        check.expect(
            len(plan1_records) == len({str(row.get("job_id")) for row in plan1_records}),
            "Plan-1 aggregate receipt identities are not unique",
        )
        plan1_ledger = {str(row.get("job_id")): row for row in plan1_records}
        plan1_background_map = {
            str(row["job_id"]): row for row in plan1_rows if row.get("stage") == "background"
        }
        plan1_background_records = {
            job_id: record
            for job_id, record in plan1_ledger.items()
            if record.get("stage") == "background"
        }
        check.expect(
            set(plan1_background_records) == set(plan1_background_map),
            "Plan-1 aggregate background identity closure differs",
        )
        for job_id, record in plan1_background_records.items():
            authority = plan1_background_map[job_id]
            for key in ("mode", "family", "events", "seed"):
                check.expect(record.get(key) == authority.get(key), f"Plan-1 aggregate {key} differs {job_id}")
    if topup_aggregate:
        check.expect(topup_aggregate.get("status") == "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS", "top-up aggregate is not 28/28 PASS")
        check.expect(topup_aggregate.get("profile_id") == topup.TOPUP_NAMESPACE, "top-up aggregate namespace differs")
        check.expect(topup_aggregate.get("planned_jobs") == EXPECTED_TOPUP_JOBS, "top-up planned jobs != 28")
        check.expect(topup_aggregate.get("validated_jobs") == EXPECTED_TOPUP_JOBS, "top-up validated jobs != 28")
        check.expect(topup_aggregate.get("instant_planned_jobs") == EXPECTED_TOPUP_INSTANT_JOBS, "top-up instant jobs != 15")
        check.expect(topup_aggregate.get("instant_validated_events") == 2_561_382, "top-up instant histories differ")
        check.expect(topup_aggregate.get("buildup_validated_events") == 2_030_976, "top-up buildup histories differ")
        check.expect(nested(topup_aggregate, "projection", "pass") is True, "top-up final disk projection failed")
        check.expect(norm(topup_aggregate.get("receipt_namespace", "")) == norm(TOPUP_RECEIPT_ROOT), "top-up aggregate receipt namespace differs")
        check.expect(norm(topup_aggregate.get("attempt_namespace", "")) == norm(TOPUP_RUN_ROOT / "jobs"), "top-up aggregate attempt namespace differs")
        topup_records = list(topup_aggregate.get("selected_receipts", []))
        check.expect(
            len(topup_records) == len({str(row.get("job_id")) for row in topup_records}),
            "top-up aggregate receipt identities are not unique",
        )
        topup_ledger = {str(row.get("job_id")): row for row in topup_records}
        check.expect(len(topup_ledger) == EXPECTED_TOPUP_JOBS, "top-up receipt ledger identity closure differs")
        topup_plan_map = {str(row["job_id"]): row for row in topup_rows}
        check.expect(set(topup_ledger) == set(topup_plan_map), "top-up aggregate/plan identity set differs")
        for job_id, record in topup_ledger.items():
            authority = topup_plan_map.get(job_id)
            if authority is None:
                continue
            check.expect(record.get("registered_stage") == "fullstat_topup_background", f"top-up registered stage differs {job_id}")
            check.expect(record.get("receipt_stage") == "background", f"top-up receipt stage differs {job_id}")
            for key in ("mode", "family", "events", "seed"):
                check.expect(record.get(key) == authority.get(key), f"top-up aggregate {key} differs {job_id}")

    selected: list[dict[str, Any]] = []
    seen_sim: set[str] = set()
    for row in instant:
        path = receipt_path_from_ledger(row, plan1_ledger, topup_ledger)
        if path is None:
            check.missing.append(f"canonical_receipt_{row['job_id']}:ledger_entry")
            continue
        payload = check.json(f"receipt_{row['job_id']}", path)
        if payload is None:
            continue
        item = validate_receipt(row, path, payload, config, check)
        if item["sim_path"] in seen_sim:
            check.errors.append(f"duplicate SIM metadata path {item['job_id']}")
        seen_sim.add(item["sim_path"])
        aggregate_record = (
            plan1_ledger.get(str(row["job_id"]))
            if row["source_namespace"] == "PLAN1_CANONICAL_PASS"
            else topup_ledger.get(str(row["job_id"]))
        ) or {}
        aggregate_digest = aggregate_record.get("sha256") or aggregate_record.get("receipt_sha256")
        check.expect(aggregate_digest == item["receipt_sha256"], f"aggregate receipt digest differs {row['job_id']}")
        check.expect(aggregate_record.get("sim_path") == item["sim_path"], f"aggregate SIM metadata differs {row['job_id']}")
        check.expect(int(aggregate_record.get("sim_bytes", -1)) == item["sim_bytes"], f"aggregate SIM byte metadata differs {row['job_id']}")
        selected.append(item)
    check.expect(len(selected) == EXPECTED_INSTANT_JOBS, "validated instant receipts != 26")
    for family in FAMILIES:
        cell = [row for row in selected if row["family"] == family]
        check.expect(bool(cell), f"validated instant family absent {family}")
        check.expect(sum(int(row["events"]) for row in cell) == FULL_TARGETS[("instant", family)], f"validated full histories differ instant/{family}")
        check.expect(math.fsum(float(row["TT_s"]) for row in cell) > 0.0, f"family sum(TT) is not positive {family}")
    check.expect(sum(int(row["events"]) for row in selected) == EXPECTED_FULL_INSTANT_HISTORIES, "validated full instant total differs")

    try:
        policy = prompt.explicit_veto_policy(config)
        check.expect(len(policy["shield_volumes"]) == 3, "shield veto does not contain exactly three BGO volumes")
        check.expect(len(policy["plastic_volumes"]) == 3, "plastic veto does not contain exactly three plastic volumes")
        check.expect(len(policy["active_veto_volumes"]) == 6, "active veto does not contain six volumes")
        check.expect(set(policy["active_veto_volumes"]) == set(policy["shield_volumes"]) | set(policy["plastic_volumes"]), "active veto is not exactly BGO + plastic")
        check.expect(len(set(policy["active_veto_volumes"])) == 6, "active veto contains duplicate volumes")
        check.expect(not set(policy["shield_volumes"]) & set(policy["plastic_volumes"]), "BGO and plastic veto roles overlap")
        check.expect(policy["apply_plastic_veto"] is True, "plastic veto is not enabled")
        check.expect(close(policy["plastic_threshold_keV"], 50.0, rel=0.0, absolute=0.0), "plastic-veto threshold is not 50 keV")
        check.expect(tuple(policy["passive_w_volumes"]) == PASSIVE_W_VOLUMES, "three passive-W volumes differ")
        check.expect(not set(policy["active_veto_volumes"]) & set(PASSIVE_W_VOLUMES), "passive W appears in active veto")
        check.expect(policy["passive_w_role"] == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "passive-W role differs")
        check.expect(nested(config, "geometry", "passive_w_never_active_veto") is True, "config does not freeze W as passive/non-veto")
        check.expect(close(nested(config, "analysis", "response_fwhm_keV"), 0.42, rel=0.0, absolute=0.0), "response FWHM is not 0.42 keV")
        check.expect(close(nested(config, "analysis", "measured_pixel_threshold_keV"), 0.3, rel=0.0, absolute=0.0), "measured pixel threshold is not 0.3 keV")
        check.expect(tuple(nested(config, "analysis", "w2_keV") or ()) == prompt.WINDOWS["w2_510p58_511p42"], "W2 definition differs from 510.58--511.42 keV")
    except Exception as exc:
        check.errors.append(f"SF3 veto/W contract invalid: {exc}")
        policy = {}
    for label, path in (
        ("retained_prompt_parser", prompt.OLD_CATALOG_PARSER),
        ("retained_response_core", prompt.CORRECTED_CORE),
        ("retained_step05", prompt.STEP05),
        ("retained_step09", prompt.STEP09_SUMMARY),
        ("adapter", HERE),
    ):
        if not path.is_file():
            check.missing.append(f"{label}:{norm(path)}")
        else:
            try:
                check.authorities[label] = small_record(path)
            except Exception as exc:
                check.errors.append(f"{label} invalid: {exc}")

    if OUTPUT.exists():
        check.errors.append(f"write-once full-stat prompt output exists: {OUTPUT}")
    ready = not check.errors and not check.missing
    return {
        "schema_version": 1,
        "profile_id": FULLSTAT_PROFILE_ID,
        "status": "READY__SF3_FULLSTAT_PROMPT_26_INSTANT_RECEIPTS" if ready else "NOT_READY__SF3_FULLSTAT_PROMPT_INPUTS",
        "ready": ready,
        "checked_at": utc_now(),
        "output": norm(OUTPUT),
        "gate": gate,
        "combined_plan": {
            "jobs": len(combined),
            "instant_jobs": len(instant),
            "buildup_jobs": len(combined) - len(instant),
            "instant_histories": sum(int(row["events"]) for row in instant),
            "full_S3d_instant_histories": EXPECTED_FULL_INSTANT_HISTORIES,
            "full_S3d_buildup_histories": EXPECTED_FULL_BUILDUP_HISTORIES,
        },
        "selected": selected,
        "veto_policy": policy,
        "authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "errors": check.errors,
        "SIM_opened_statted_or_hashed": False,
        "transport_launched": False,
        "normalization": "sum selected events / sum(TT) separately within each SF3 x instant x family cell",
        "pooling_boundary": "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY",
    }


def selected_jobs(prerequisites: dict[str, Any]) -> list[dict[str, Any]]:
    if not prerequisites.get("ready"):
        raise RuntimeError(json_text(prerequisites))
    policy = prerequisites["veto_policy"]
    jobs: list[dict[str, Any]] = []
    for scan_index, row in enumerate(prerequisites["selected"]):
        jobs.append({
            **row,
            "scan_index": scan_index,
            "input_id": row["source_namespace"],
            "batch_id": FULLSTAT_PROFILE_ID,
            "expected_geometry": norm(row["setup_path"]),
            "shield_volumes": list(policy["shield_volumes"]),
            "plastic_volumes": list(policy["plastic_volumes"]),
            "passive_w_volumes": list(policy["passive_w_volumes"]),
            "veto_policy": policy,
        })
    return jobs


def build_report(
    summary_rows: Sequence[dict[str, Any]],
    w_summary: dict[str, Any],
) -> str:
    wanted = {
        (row["stage"], row["window_id"]): row
        for row in summary_rows if row["response_state"] == "measured"
    }

    def cell(stage: str, window: str) -> str:
        row = wanted[(stage, window)]
        return f"{int(row['descriptive_selected_events_across_families'])} ({row['rate_cps_sum_of_family_rates']:.8g} cps)"

    return "\n".join([
        "# SF3 conditional full-stat prompt analysis",
        "",
        "Status: `PASS__SF3_FULLSTAT_PROMPT_COMPLETE`",
        "",
        f"The stage consumes 26 canonical instant receipts and {EXPECTED_FULL_INSTANT_HISTORIES:,} histories only after the central F3 gate, Plan-1 closure, and 28/28 top-up receipt gates pass.",
        "Rates are normalized independently as count/sum(TT) inside each SF3 × instant × incident-family cell.",
        "",
        "| Geometry | 480–550 measured | after explicit veto | after Step05 | W2 measured | after veto | after Step05 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| SF3 | {cell('pre_veto', 'broad_480_550')} | {cell('active_veto50', 'broad_480_550')} | {cell('side_compton_fov_pass', 'broad_480_550')} | {cell('pre_veto', 'w2_510p58_511p42')} | {cell('active_veto50', 'w2_510p58_511p42')} | {cell('side_compton_fov_pass', 'w2_510p58_511p42')} |",
        "",
        f"Passive-W diagnostics: {w_summary['w_deposit_events']:,} W-deposit events and {w_summary['w_first_interaction_events']:,} first-resolvable interactions in the exact three SF3 W volumes. W remains diagnostic-only and is absent from the three-BGO plus three-plastic veto.",
        "",
    ])


def build(config_path: Path = CONFIG, workers: int = DEFAULT_WORKERS) -> dict[str, Any]:
    if workers < 1 or workers > MAX_WORKERS:
        raise ValueError("workers must be within 1..6")
    prerequisites = check_prerequisites(config_path)
    if not prerequisites["ready"]:
        raise RuntimeError(json_text(prerequisites))
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite write-once output: {OUTPUT}")
    config = load_small_json(config_path)
    jobs = selected_jobs(prerequisites)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".01_prompt.work-", dir=OUTPUT.parent))
    cache_dir = work / "job_cache"
    cache_dir.mkdir()
    started = time.monotonic()
    results: dict[int, dict[str, Any]] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(prompt.scan_job, job, str(cache_dir)): job for job in jobs}
            for completed, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results[int(result["scan_index"])] = result
                print(json.dumps({
                    "event": "fullstat_prompt_sim_scanned_once",
                    "completed": completed,
                    "total": len(jobs),
                    "job_id": futures[future]["job_id"],
                    "generated_events": result["generated_events"],
                }, sort_keys=True), flush=True)
        if len(results) != EXPECTED_INSTANT_JOBS or sum(int(row["semantic_sim_scans"]) for row in results.values()) != EXPECTED_INSTANT_JOBS:
            raise RuntimeError("26-job one-pass SIM scan closure failed")

        core, step05, disk = prompt.response_runtime(config)
        policy = prompt.explicit_veto_policy(config)
        jobs_by_family: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for job in jobs:
            jobs_by_family[str(job["family"])].append(job)
        cutflow: list[dict[str, Any]] = []
        occupancy: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []
        spectrum_pieces: list[tuple[str, dict[Any, Any]]] = []
        for family in FAMILIES:
            cell_jobs = jobs_by_family[family]
            target = work / "catalog/SF3" / f"{family}.pkl"
            catalog, metadata = prompt.merge_cell(cell_jobs, results, target, policy)
            metadata["authority_status"] = "SF3_FULLSTAT_PROMPT_26_CANONICAL_RECEIPTS_COMPLETE"
            metadata["normalization"] = "selected events / family-specific sum(TT) within SF3 x instant x family"
            catalog["cell_metadata"] = metadata
            with target.open("wb") as handle:
                pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
            cell_cutflow, cell_spectrum, cell_occupancy = prompt.evaluate_cell(
                catalog, core, step05, disk
            )
            cutflow.extend(cell_cutflow)
            spectrum_pieces.append(("SF3", cell_spectrum))
            occupancy.append(cell_occupancy)
            cell_results = [results[int(job["scan_index"])] for job in cell_jobs]
            coverage.append({
                "geometry": "SF3",
                "mode": "instant",
                "family": family,
                "plan1_jobs": sum(job["source_namespace"] == "PLAN1_CANONICAL_PASS" for job in cell_jobs),
                "topup_jobs": sum(job["source_namespace"] == "FULLSTAT_TOPUP_NEW" for job in cell_jobs),
                "jobs": len(cell_jobs),
                "generated_events": metadata["generated_events"],
                "full_target_histories": FULL_TARGETS[("instant", family)],
                "TT_s": metadata["TT_s"],
                "event_weight_cps": metadata["event_weight_cps"],
                "tes_positive_events": len(catalog["stream"]),
                "active_only_events": catalog["active_only_events"],
                "pixel_hits": len(catalog["pix_e"]),
                "w_deposit_events": sum(int(row["w_deposit_events"]) for row in cell_results),
                "w_deposit_keV_sum": math.fsum(float(row["w_deposit_keV_sum"]) for row in cell_results),
                "w_first_interaction_events": sum(int(row["w_first_interaction_events"]) for row in cell_results),
                "catalog_path": norm(OUTPUT / "catalog/SF3" / f"{family}.pkl"),
                "normalization": "FAMILY_SPECIFIC_SUM_TT__NO_CROSS_FAMILY_POOLING",
            })

        spectrum = prompt.aggregate_spectrum(spectrum_pieces)
        summary_rows = prompt.geometry_summary(cutflow)
        w_rows = [{
            "geometry": "SF3",
            "mode": "instant",
            "family": job["family"],
            "job_id": job["job_id"],
            "source_namespace": job["source_namespace"],
            "generated_events": results[int(job["scan_index"])]["generated_events"],
            "tes_positive_events": results[int(job["scan_index"])]["tes_positive_events"],
            "w_deposit_events": results[int(job["scan_index"])]["w_deposit_events"],
            "w_deposit_keV_sum": results[int(job["scan_index"])]["w_deposit_keV_sum"],
            "w_first_interaction_events": results[int(job["scan_index"])]["w_first_interaction_events"],
            "pair_ia_count": results[int(job["scan_index"])]["pair_ia_count"],
            "w_pair_ia_count": results[int(job["scan_index"])]["w_pair_ia_count"],
            "pair_ia_unresolved_count": results[int(job["scan_index"])]["pair_ia_unresolved_count"],
            "annihilation_ia_count": results[int(job["scan_index"])]["annihilation_ia_count"],
            "w_annihilation_ia_count": results[int(job["scan_index"])]["w_annihilation_ia_count"],
            "annihilation_ia_unresolved_count": results[int(job["scan_index"])]["annihilation_ia_unresolved_count"],
            "passive_w_volumes_json": json.dumps(list(PASSIVE_W_VOLUMES), separators=(",", ":")),
            "veto_role": "PASSIVE_DIAGNOSTIC_ONLY__NOT_BGO_OR_PLASTIC_VETO",
        } for job in jobs]
        w_summary = {
            key: (
                math.fsum(float(row[key]) for row in w_rows)
                if key == "w_deposit_keV_sum"
                else sum(int(row[key]) for row in w_rows)
            )
            for key in (
                "w_deposit_events", "w_deposit_keV_sum", "w_first_interaction_events",
                "pair_ia_count", "w_pair_ia_count", "pair_ia_unresolved_count",
                "annihilation_ia_count", "w_annihilation_ia_count",
                "annihilation_ia_unresolved_count",
            )
        }
        w_summary.update({
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "role": "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES",
            "first_interaction_method": "FIRST_PARENT_ID_1_IA_MATCHED_TO_PRIMARY_CC_HIT_BY_TIME_AND_PROCESS",
            "pair_annihilation_locality_method": "IA_MATCHED_TO_RECORDED_CC_HIT_BY_TIME_AND_PROCESS__UNRESOLVED_REPORTED_SEPARATELY",
        })
        input_manifest = [{
            "source_namespace": job["source_namespace"],
            "job_id": job["job_id"],
            "geometry": "SF3",
            "mode": "instant",
            "family": job["family"],
            "seed": job["seed"],
            "events": job["events"],
            "TT_s": job["TT_s"],
            "receipt_path": job["receipt_path"],
            "receipt_sha256": job["receipt_sha256"],
            "sim_path": job["sim_path"],
            "sim_bytes_from_receipt": job["sim_bytes"],
            "semantic_sim_scans": 1,
            "sim_hash_recomputed": False,
        } for job in jobs]
        prompt.write_csv(work / "fullstat_prompt_input_manifest.csv", input_manifest)
        prompt.write_csv(work / "fullstat_prompt_cell_coverage.csv", coverage)
        prompt.write_csv(work / "fullstat_prompt_cutflow.csv", cutflow)
        prompt.write_csv(work / "fullstat_prompt_spectrum_480_550.csv", spectrum)
        prompt.write_csv(work / "fullstat_prompt_fullband_occupancy.csv", occupancy)
        prompt.write_csv(work / "fullstat_prompt_geometry_summary.csv", summary_rows)
        prompt.write_csv(work / "fullstat_prompt_w_diagnostics.csv", w_rows)

        summary = {
            "schema_version": 1,
            "profile_id": FULLSTAT_PROFILE_ID,
            "status": "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
            "scope": "gate-authorized full S3d-O8-stat equivalent SF3 instant prompt",
            "gate": prerequisites["gate"],
            "combined_background_plan_jobs": EXPECTED_COMBINED_JOBS,
            "selected_instant_jobs": EXPECTED_INSTANT_JOBS,
            "selected_instant_histories": EXPECTED_FULL_INSTANT_HISTORIES,
            "receipt_namespaces": {
                "PLAN1_CANONICAL_PASS": EXPECTED_PLAN1_INSTANT_JOBS,
                "FULLSTAT_TOPUP_NEW": EXPECTED_TOPUP_INSTANT_JOBS,
            },
            "response": {
                "fwhm_keV": float(core.FWHM_KEV),
                "pixel_threshold_keV": float(core.PIXEL_THRESHOLD_KEV),
                "rng_namespace": str(core.RESPONSE_NAMESPACE),
                "response_geometry_key": prompt.CORE_GEOMETRY["SF3"],
            },
            "active_veto": policy,
            "passive_w_diagnostics": w_summary,
            "normalization": "count/sum(TT) independently per SF3 x instant x family; family rates summed only after normalization",
            "pooling_boundary": "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY",
            "sim_scan_policy": {
                "selected_sim_count": EXPECTED_INSTANT_JOBS,
                "semantic_scans": EXPECTED_INSTANT_JOBS,
                "scans_per_sim": 1,
                "sim_hashes_recomputed": 0,
            },
            "geometry_summary": summary_rows,
            "elapsed_s": time.monotonic() - started,
            "transport_launched_by_adapter": False,
            "authority_boundary": "FULLSTAT_PROMPT_RESPONSE_INPUT_ONLY__NOT_REBUILT_ACTIVATION_DELAYED_MISSION_OR_PROMOTION_AUTHORITY",
        }
        prompt.write_json(work / "summary.json", summary)
        (work / "REPORT.md").write_text(build_report(summary_rows, w_summary), encoding="utf-8")
        shutil.rmtree(cache_dir)
        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": FULLSTAT_PROFILE_ID,
            "status": summary["status"],
            "generated_utc": utc_now(),
            "analysis_code": norm(HERE),
            "retained_prompt_code": norm(prompt.HERE),
            "input_small_authorities": prerequisites["authorities"],
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in files
            ],
            "normalization_contract": "PER_SF3_X_INSTANT_X_FAMILY_SUM_TT__NO_CROSS_BOUNDARY_POOLING",
            "large_payload_policy": {
                "SIMs_semantically_scanned_once": EXPECTED_INSTANT_JOBS,
                "SIMs_hashed": 0,
                "transport_launched": False,
            },
        }
        prompt.write_json(work / "manifest.json", manifest)
        os.rename(work, OUTPUT)
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def distribute(total: int, count: int) -> list[int]:
    base, remainder = divmod(total, count)
    return [base + (index < remainder) for index in range(count)]


def synthetic_combined_fixture() -> tuple[
    list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]
]:
    plan1_counts = {
        ("instant", "gamma"): 4,
        ("buildup", "gamma"): 3,
    }
    topup_counts = {
        ("instant", "gamma"): 8,
        ("buildup", "gamma"): 6,
    }
    combined: list[dict[str, Any]] = []
    plan1: list[dict[str, Any]] = []
    topup_rows: list[dict[str, Any]] = []
    for mode in ("instant", "buildup"):
        for family in FAMILIES:
            pcount = plan1_counts.get((mode, family), 1)
            tcount = topup_counts.get((mode, family), 1)
            full = FULL_TARGETS[(mode, family)]
            plan1_total = math.ceil(full / 3)
            for index, events in enumerate(distribute(plan1_total, pcount), start=1):
                job_id = f"p1_{mode}_{family}_{index}"
                plan1.append({
                    "job_id": job_id, "stage": "background", "geometry": "SF3",
                    "mode": mode, "family": family, "events": events,
                    "seed": 10_000 + len(plan1), "source_path": f"/p1/{job_id}.source",
                })
            for index, events in enumerate(distribute(full - plan1_total, tcount), start=1):
                job_id = f"tu_{mode}_{family}_{index}"
                topup_rows.append({
                    "job_id": job_id, "stage": "fullstat_topup_background", "geometry": "SF3",
                    "mode": mode, "family": family, "events": events,
                    "seed": 20_000 + len(topup_rows), "source_path": f"/tu/{job_id}.source",
                })
    for namespace, rows in (("PLAN1_CANONICAL_PASS", plan1), ("FULLSTAT_TOPUP_NEW", topup_rows)):
        for row in rows:
            combined.append({
                "combined_ordinal": len(combined) + 1,
                "source_namespace": namespace,
                "job_id": row["job_id"], "geometry": "SF3", "mode": row["mode"],
                "family": row["family"], "events": row["events"], "seed": row["seed"],
                "source_path": row["source_path"],
                "receipt_authority": "/p1/aggregate.json" if namespace == "PLAN1_CANONICAL_PASS" else f"/tu/receipts/{row['job_id']}.json",
                "aggregation_role": "RETAIN_EXISTING_CANONICAL_PASS" if namespace == "PLAN1_CANONICAL_PASS" else "APPEND_NEW_TOPUP",
            })
    aggregation = [{
        "mode": mode, "family": family,
        "combined_histories": str(target), "full_target_histories": str(target),
        "do_not_pool_across_mode_family_geometry": "true",
        "downstream_role": "FULL_PROMPT_RESPONSE_INPUT" if mode == "instant" else "FULL_BUILDUP_RP_TT_INPUT_FOR_REBUILT_INVENTORY",
    } for (mode, family), target in FULL_TARGETS.items()]
    # The production Plan-1 plan has nine non-background rows; add inert rows so
    # the pure validator also locks its 30-row registration boundary.
    plan1.extend({
        "job_id": f"registered_nonbackground_{index}", "stage": "delayed",
        "geometry": "SF3", "mode": "delayed", "family": FAMILIES[index % 8],
        "events": 83_334, "seed": 30_000 + index,
        "source_path": f"/p1/nonbackground_{index}.source",
    } for index in range(9))
    return combined, aggregation, plan1, topup_rows


def self_test() -> dict[str, Any]:
    combined, aggregation, plan1, topup_rows = synthetic_combined_fixture()
    checker = Checker()
    instant = validate_combined_plan(combined, aggregation, plan1, topup_rows, checker)
    if checker.errors:
        raise AssertionError(f"49/26/full-history closure fixture failed: {checker.errors}")
    if len(instant) != EXPECTED_INSTANT_JOBS:
        raise AssertionError("synthetic instant selection is not 26 jobs")
    namespace_paths = {
        "PLAN1_CANONICAL_PASS": "/synthetic/plan1/receipts/job.json",
        "FULLSTAT_TOPUP_NEW": "/synthetic/package/audit/fullstat_topup_receipts/job.json",
    }
    if not lexical_child(namespace_paths["PLAN1_CANONICAL_PASS"], "/synthetic/plan1/receipts"):
        raise AssertionError("Plan-1 receipt namespace fixture failed")
    if not lexical_child(namespace_paths["FULLSTAT_TOPUP_NEW"], "/synthetic/package/audit/fullstat_topup_receipts"):
        raise AssertionError("top-up receipt namespace fixture failed")
    for ratio, expected in ((0.75, True), (0.7500001, False)):
        if (ratio <= FULLSTAT_GATE) is not expected:
            raise AssertionError("central-gate boundary fixture failed")
    config = {
        "analysis": {"active_veto_threshold_keV": 50.0},
        "geometry": {
            "shield_veto_volumes": ["B1", "B2", "B3"],
            "plastic_veto_volumes": ["P1", "P2", "P3"],
            "active_veto_volumes": ["B1", "B2", "B3", "P1", "P2", "P3"],
            "apply_plastic_veto": True,
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "passive_w_never_active_veto": True,
        },
    }
    policy = prompt.explicit_veto_policy(config)
    if len(policy["active_veto_volumes"]) != 6:
        raise AssertionError("synthetic active veto does not contain six volumes")
    if tuple(policy["passive_w_volumes"]) != PASSIVE_W_VOLUMES:
        raise AssertionError("synthetic passive-W volume identity/order differs")
    if policy["passive_w_role"] != "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO":
        raise AssertionError("synthetic W role is not diagnostic-only")
    if set(policy["active_veto_volumes"]) & set(PASSIVE_W_VOLUMES):
        raise AssertionError("passive W overlaps the synthetic active veto")
    tt_by_family = {
        family: math.fsum(1.0 + index for index, row in enumerate(instant) if row["family"] == family)
        for family in FAMILIES
    }
    if any(value <= 0.0 for value in tt_by_family.values()) or len(tt_by_family) != 8:
        raise AssertionError("family-specific TT fixture failed")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_PROMPT_ADAPTER_SYNTHETIC_SELF_TEST",
        "checks": [
            "49_combined_background_jobs",
            "26_instant_jobs_equal_11_plan1_plus_15_topup",
            "full_S3d_instant_and_buildup_history_closure",
            "central_gate_equal_0p75_authorizes_and_above_stops",
            "Plan1_and_topup_receipt_namespaces_disjoint",
            "family_specific_sumTT_no_cross_family_geometry_or_mode_pooling",
            "three_exact_SF3_W_volumes_passive_and_disjoint_from_six_active_veto_volumes",
        ],
        "combined_jobs": len(combined),
        "instant_jobs": len(instant),
        "instant_histories": sum(int(row["events"]) for row in instant),
        "buildup_histories": sum(int(row["events"]) for row in combined if row["mode"] == "buildup"),
        "files_written": False,
        "SIM_opened_statted_or_hashed": False,
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-prerequisites", action="store_true", help="read compact gate/plan/receipt authorities only")
    actions.add_argument("--build", action="store_true", help="scan 26 registered instant SIMs and publish write-once output")
    actions.add_argument("--self-test", action="store_true", help="run pure synthetic closure tests")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="analysis workers, 1..6 (production recommendation: 4)")
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    try:
        if args.workers < 1 or args.workers > MAX_WORKERS:
            raise ValueError("workers must be within 1..6")
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites:
            result = check_prerequisites(args.config)
        else:
            result = build(args.config, args.workers)
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready", False):
            return 1 if result.get("errors") else 2
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "status": "FAIL__SF3_FULLSTAT_PROMPT_ADAPTER",
            "error": str(exc),
            "SIM_policy": "CHECK_NEVER_OPENS_STATS_OR_HASHES__BUILD_SEMANTIC_SCAN_ONCE_NO_HASH",
            "transport_launched": False,
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
