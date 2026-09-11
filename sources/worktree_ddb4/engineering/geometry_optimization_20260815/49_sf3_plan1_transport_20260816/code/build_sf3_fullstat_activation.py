#!/usr/bin/env python3
"""Build the gate-authorized, full-stat SF3 activation/delayed package.

``--check-prerequisites`` reads only named small CSV/JSON/source authorities.
It never opens, stats, or hashes a SIM.  ``--prepare`` is intentionally gated
twice: the completed central mission ratio must explicitly require top-up and
all 28 full-stat top-up background jobs must have canonical PASS receipts.

After those gates, preparation combines the 10 Plan-1 and 13 top-up BUILDUP
receipts.  It retains TT from all 23 DAT files (including zero-RP files),
rebuilds the day-15 inventory, performs one semantic ``CC IP RP`` pass over
each selected SIM for actual production positions, and creates an independent
50k-to-10k exact-position mixture.  Positive families receive one fresh
250,000-trigger delayed job; exact-zero families remain registered but are
skipped with a finite upper limit.  Plan-1's 83,334-trigger delayed products
are neither consumed nor merged.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import build_sf3_activation as base
import build_sf3_fullstat_topup as topup
from build_sf3_sources import collect_occupied_seeds
from sf3_plan1_common import (
    FAMILIES,
    FULLSTAT_DELAYED_EVENTS,
    FULLSTAT_GATE_MAX_R_F3,
    FULLSTAT_INCREMENT_SHARDS,
    PACKAGE_ROOT,
    RUN_ROOT,
    S3D_HISTORIES,
    SF3_SETUP,
    SHARDS,
    derive_seed,
    sha256,
    utc_now,
    write_once_json,
    write_once_text,
)


OUTPUT_ROOT = PACKAGE_ROOT / "outputs/fullstat/02_activation"
DELAYED_CARD_ROOT = PACKAGE_ROOT / "config/fullstat_delayed_source_cards"
DELAYED_JOB_PLAN = PACKAGE_ROOT / "data/sf3_fullstat_delayed_job_plan.csv"
DELAYED_SEED_REGISTRY = PACKAGE_ROOT / "data/sf3_fullstat_delayed_seed_registry.csv"
ACTIVATION_VALIDATION = PACKAGE_ROOT / "audit/sf3_fullstat_activation_validation.json"
SOURCE_INDEX = OUTPUT_ROOT / "delayed_source_index.csv"

MISSION_SUMMARY = PACKAGE_ROOT / "outputs/06_mission/summary.json"
PLAN1_JOB_PLAN = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
PLAN1_SEED_REGISTRY = PACKAGE_ROOT / "data/sf3_plan1_seed_registry.csv"
PLAN1_BACKGROUND_VALIDATION = PACKAGE_ROOT / "audit/sf3_plan1_background_receipt_validation.json"
PLAN1_RECEIPT_ROOT = RUN_ROOT / "receipts"
TOPUP_PLAN = topup.TOPUP_PLAN
TOPUP_SEEDS = topup.TOPUP_SEEDS
TOPUP_STATIC_AUDIT = topup.STATIC_AUDIT
TOPUP_AGGREGATE = topup.TOPUP_AGGREGATE_RECEIPT
TOPUP_RECEIPT_ROOT = topup.TOPUP_RECEIPT_ROOT
TOPUP_RUN_ROOT = topup.TOPUP_RUN_ROOT

FULLSTAT_DELAYED_NAMESPACE = "SF3_FULLSTAT_DELAYED_V1"
FULLSTAT_DELAYED_RUN_ROOT = RUN_ROOT.parent / "sf3_fullstat_delayed_v1"
FULLSTAT_DELAYED_RECEIPT_ROOT = PACKAGE_ROOT / "audit/fullstat_delayed_receipts"
FULLSTAT_DELAYED_AGGREGATE = PACKAGE_ROOT / "audit/sf3_fullstat_delayed_transport_receipts.json"

FULLSTAT_STATUS = "PASS__SF3_FULLSTAT_ACTIVATION_AND_FRESH_DELAYED_SOURCES_READY"
FULLSTAT_VALIDATION_STATUS = "PASS__SF3_FULLSTAT_ACTIVATION_VALIDATION"
POSITIVE_DISPOSITION = "RUN_FRESH_250000"
ZERO_DISPOSITION = "SKIP_ZERO_A15"
PLAN1_DELAYED_ROLE = "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE"
SMALL_JSON_MAX_BYTES = 20_000_000

PASSIVE_W_VOLUMES = (
    "SF3_W_NearField_FrontWindowPlate_2p9mm",
    "SF3_W_NearField_SideSleeve_2p9mm",
    "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
)

DELAYED_PLAN_FIELDS = (
    "ordinal",
    "job_id",
    "stage",
    "geometry",
    "mode",
    "family",
    "registered_events",
    "events",
    "actual_transport_events",
    "seed",
    "sampling_seed",
    "seed_identity",
    "seed_namespace",
    "source_path",
    "setup_path",
    "run_root",
    "receipt_path",
    "aggregate_receipt_path",
    "source_status",
    "execution_disposition",
    "transport_eligible",
    "plan1_83334_role",
    "incremental_merge_allowed",
    "source_support",
)


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    """Read a named compact JSON authority; SIM paths are never accepted."""
    if path.suffix.lower() != ".json" or not path.is_file():
        raise FileNotFoundError(f"missing named JSON {label}: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > SMALL_JSON_MAX_BYTES:
        raise RuntimeError(f"{label} is empty or oversized: {path} ({len(raw)} bytes)")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} root must be an object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader)


def csv_text(rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def lexical_absolute_path(value: str | Path) -> Path:
    """Normalize a declared path without resolving/statting the final target."""
    return Path(os.path.abspath(os.path.normpath(os.fspath(value))))


def small_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def validate_mission_gate_payload(mission: dict[str, Any]) -> dict[str, Any]:
    if not str(mission.get("status", "")).startswith("PASS__"):
        raise RuntimeError("mission summary is not PASS")
    gate = mission.get("fullstat_gate")
    if not isinstance(gate, dict):
        raise RuntimeError("mission summary lacks fullstat_gate")
    if gate.get("metric") != "F3_SF3_over_SE3_full_envelope":
        raise RuntimeError("full-stat gate is not the central matched F3 ratio")
    if gate.get("operator") != "<=" or float(gate.get("threshold", -1.0)) != FULLSTAT_GATE_MAX_R_F3:
        raise RuntimeError("full-stat gate operator/threshold differs")
    ratio = float(gate.get("observed_central_ratio"))
    if not math.isfinite(ratio) or ratio < 0.0 or ratio > FULLSTAT_GATE_MAX_R_F3:
        raise RuntimeError(f"central gate does not authorize full-stat activation: {ratio}")
    if gate.get("topup_required") is not True:
        raise RuntimeError("mission gate does not explicitly set topup_required=true")
    if gate.get("decision") != "TOPUP_TO_S3D_FULL_STAT_REQUIRED":
        raise RuntimeError("mission full-stat decision differs")
    if gate.get("proxy_controls_gate") is not False:
        raise RuntimeError("proxy was incorrectly allowed to control the full-stat gate")
    return {
        "status": "PASS__CENTRAL_FULLSTAT_GATE_AUTHORIZES_REBUILD",
        "central_R_F3": ratio,
        "threshold": FULLSTAT_GATE_MAX_R_F3,
        "topup_required": True,
        "decision": gate["decision"],
        "proxy_controls_gate": False,
    }


def validate_mission_gate(path: Path = MISSION_SUMMARY) -> dict[str, Any]:
    result = validate_mission_gate_payload(load_small_json(path, "mission summary"))
    return {**result, "path": str(path.resolve()), "sha256": sha256(path)}


def cast_plan1_row(raw: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = dict(raw)
    for key in ("ordinal", "shard", "events", "s3d_histories", "target_histories", "seed", "estimated_bytes"):
        row[key] = int(raw[key])
    row["run_root"] = str(RUN_ROOT)
    row["receipt_path"] = str(PLAN1_RECEIPT_ROOT / f"{row['job_id']}.json")
    row["source_namespace"] = "PLAN1_CANONICAL_PASS"
    return row


def cast_topup_row(raw: dict[str, str]) -> dict[str, Any]:
    required = set(topup.PLAN_FIELDS)
    if set(raw) != required:
        raise RuntimeError(f"top-up plan schema differs for {raw.get('job_id')}")
    row: dict[str, Any] = dict(raw)
    for key in (
        "ordinal", "increment_shard", "events", "plan1_validated_histories",
        "full_target_histories", "seed", "estimated_bytes_from_plan1_calibration",
    ):
        row[key] = int(raw[key])
    row["source_namespace"] = "FULLSTAT_TOPUP_CANONICAL_PASS"
    return row


def plan1_background_rows() -> list[dict[str, Any]]:
    rows = [cast_plan1_row(row) for row in read_csv(PLAN1_JOB_PLAN)]
    background = [row for row in rows if row["stage"] == "background"]
    if len(rows) != 30 or len(background) != 21:
        raise RuntimeError(f"Plan-1 plan closure differs: total={len(rows)} background={len(background)}")
    return background


def topup_background_rows() -> list[dict[str, Any]]:
    rows = [cast_topup_row(row) for row in read_csv(TOPUP_PLAN)]
    if len(rows) != 28:
        raise RuntimeError(f"top-up plan must contain 28 rows, got {len(rows)}")
    if any(row["stage"] != "fullstat_topup_background" for row in rows):
        raise RuntimeError("top-up plan contains a non-background row")
    return rows


def combined_buildup_rows(
    plan1_rows: Sequence[dict[str, Any]],
    topup_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected = [row for row in plan1_rows if row["mode"] == "buildup"] + [
        row for row in topup_rows if row["mode"] == "buildup"
    ]
    if len(selected) != 23:
        raise RuntimeError(f"combined full-stat buildup selection must be 23 jobs, got {len(selected)}")
    if len({str(row["job_id"]) for row in selected}) != 23:
        raise RuntimeError("combined buildup job identities are not unique")
    for family in FAMILIES:
        rows = [row for row in selected if row["family"] == family]
        total = sum(int(row["events"]) for row in rows)
        expected = S3D_HISTORIES[("buildup", family)]
        if total != expected:
            raise RuntimeError(f"full-stat buildup history closure differs for {family}: {total} != {expected}")
    if sum(int(row["events"]) for row in selected) != 3_046_468:
        raise RuntimeError("combined full-stat buildup total is not 3,046,468")
    return selected


def validate_receipt_metadata(
    job: dict[str, Any],
    payload: dict[str, Any],
    *,
    profile_id: str,
    run_root: Path,
) -> list[str]:
    """Validate receipt metadata without touching any referenced artifact."""
    errors: list[str] = []
    expected = {
        "status": "PASS",
        "profile_id": profile_id,
        "job_id": job["job_id"],
        "stage": "background",
        "geometry": "SF3",
        "mode": job["mode"],
        "family": job["family"],
        "events": int(job["events"]),
        "seed": int(job["seed"]),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key}={payload.get(key)!r} != {value!r}")
    try:
        if Path(str(payload.get("source_path"))).resolve() != Path(str(job["source_path"])).resolve():
            errors.append("source_path differs")
        if Path(str(payload.get("setup_path"))).resolve() != SF3_SETUP.resolve():
            errors.append("setup_path is not SF3")
    except (OSError, TypeError):
        errors.append("source/setup path metadata is invalid")
    attempt = payload.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt not in (1, 2):
        errors.append("attempt ordinal is not 1 or 2")
    else:
        expected_dir = (run_root / "jobs" / str(job["job_id"]) / "attempts" / f"attempt{attempt:02d}").resolve()
        try:
            actual_dir = Path(str(payload.get("attempt_dir"))).resolve()
            if actual_dir != expected_dir:
                errors.append("attempt_dir is not canonical attempts/attemptNN")
            exact_paths = {
                "sim_path": expected_dir / f"{job['job_id']}.inc1.id1.sim.gz",
                "isotope_dat_path": expected_dir / f"{job['job_id']}.dat.inc1.dat",
                "log_path": expected_dir / f"{job['job_id']}.log",
            }
            for key, value in exact_paths.items():
                if lexical_absolute_path(str(payload.get(key))) != lexical_absolute_path(value):
                    errors.append(f"{key} escapes canonical PASS attempt")
        except (OSError, TypeError):
            errors.append("canonical artifact path metadata is invalid")
    for key in ("sim_bytes", "isotope_dat_bytes", "log_bytes", "artifact_bytes"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"{key} metadata is not a positive integer")
    isotope = payload.get("isotope_dat") or {}
    if not isinstance(isotope.get("TT_s"), (int, float)) or float(isotope["TT_s"]) <= 0.0:
        errors.append("receipt TT is not positive")
    if not isinstance(isotope.get("RP_record_count"), int) or int(isotope["RP_record_count"]) < 0:
        errors.append("receipt RP_record_count is invalid")
    if isotope.get("terminal_EN") is not True or isotope.get("errors") not in (None, []):
        errors.append("receipt DAT terminal/error metadata differs")
    header = payload.get("sim_header") or {}
    try:
        if Path(str(header.get("geometry"))).resolve() != SF3_SETUP.resolve():
            errors.append("receipt SIM header geometry metadata is not SF3")
    except (OSError, TypeError):
        errors.append("receipt SIM header geometry metadata is invalid")
    if header.get("seed") != int(job["seed"]):
        errors.append("receipt SIM header seed metadata differs")
    if header.get("policy") != "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST":
        errors.append("receipt SIM header policy differs")
    if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
        errors.append("receipt SIM digest policy differs")
    return errors


def validate_plan1_receipt_gate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    authority = load_small_json(PLAN1_BACKGROUND_VALIDATION, "Plan-1 background validation")
    if authority.get("status") != "PASS" or authority.get("scope") not in ("background", "all"):
        raise RuntimeError("Plan-1 background receipt validation is not PASS")
    if int(authority.get("planned_jobs_in_scope", -1)) != 21 or int(authority.get("validated_jobs_in_scope", -1)) != 21:
        raise RuntimeError("Plan-1 background receipt validation does not close 21/21")
    records = {str(row.get("job_id")): row for row in authority.get("receipt_records", [])}
    if len(records) != 21:
        raise RuntimeError("Plan-1 validation receipt-record set is not exactly 21")
    validated: list[dict[str, Any]] = []
    for job in rows:
        path = PLAN1_RECEIPT_ROOT / f"{job['job_id']}.json"
        payload = load_small_json(path, f"Plan-1 receipt {job['job_id']}")
        errors = validate_receipt_metadata(job, payload, profile_id=base.PROFILE_ID, run_root=RUN_ROOT)
        digest = sha256(path)
        record = records.get(str(job["job_id"])) or {}
        if record.get("sha256") != digest or Path(str(record.get("path", ""))).resolve() != path.resolve():
            errors.append("receipt differs from Plan-1 validation authority")
        if errors:
            raise RuntimeError(f"Plan-1 receipt {job['job_id']} invalid: {errors}")
        validated.append({
            "job_id": job["job_id"], "mode": job["mode"], "family": job["family"],
            "events": int(job["events"]), "seed": int(job["seed"]),
            "receipt_path": str(path.resolve()), "receipt_sha256": digest,
            "TT_s": float(payload["isotope_dat"]["TT_s"]),
            "RP_record_count": int(payload["isotope_dat"]["RP_record_count"]),
        })
    return {
        "status": "PASS__ALL_21_PLAN1_BACKGROUND_CANONICAL_RECEIPTS_METADATA",
        "authority": small_record(PLAN1_BACKGROUND_VALIDATION),
        "validated_jobs": len(validated),
        "validated_buildup_jobs": sum(row["mode"] == "buildup" for row in validated),
        "records": validated,
        "sim_access": "NONE__RECEIPT_METADATA_ONLY",
    }


def validate_topup_receipt_gate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    aggregate = load_small_json(TOPUP_AGGREGATE, "full-stat top-up aggregate")
    if aggregate.get("status") != "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS":
        raise RuntimeError("top-up aggregate is not complete PASS")
    if int(aggregate.get("planned_jobs", -1)) != 28 or int(aggregate.get("validated_jobs", -1)) != 28:
        raise RuntimeError("top-up aggregate does not close 28/28")
    selected = {str(row.get("job_id")): row for row in aggregate.get("selected_receipts", [])}
    if len(selected) != 28:
        raise RuntimeError("top-up aggregate selected receipt set is not exactly 28")
    validated: list[dict[str, Any]] = []
    for job in rows:
        path = TOPUP_RECEIPT_ROOT / f"{job['job_id']}.json"
        if Path(str(job["receipt_path"])).resolve() != path.resolve():
            raise RuntimeError(f"top-up plan receipt target differs: {job['job_id']}")
        payload = load_small_json(path, f"top-up receipt {job['job_id']}")
        errors = validate_receipt_metadata(
            job, payload, profile_id=topup.TOPUP_NAMESPACE, run_root=TOPUP_RUN_ROOT
        )
        digest = sha256(path)
        record = selected.get(str(job["job_id"])) or {}
        if record.get("receipt_sha256") != digest:
            errors.append("receipt digest differs from top-up aggregate")
        if Path(str(record.get("receipt_path", ""))).resolve() != path.resolve():
            errors.append("receipt path differs from top-up aggregate")
        for key in ("mode", "family", "events", "seed"):
            if record.get(key) != job[key]:
                errors.append(f"aggregate {key} differs")
        if errors:
            raise RuntimeError(f"top-up receipt {job['job_id']} invalid: {errors}")
        validated.append({
            "job_id": job["job_id"], "mode": job["mode"], "family": job["family"],
            "events": int(job["events"]), "seed": int(job["seed"]),
            "receipt_path": str(path.resolve()), "receipt_sha256": digest,
            "TT_s": float(payload["isotope_dat"]["TT_s"]),
            "RP_record_count": int(payload["isotope_dat"]["RP_record_count"]),
        })
    return {
        "status": "PASS__ALL_28_FULLSTAT_TOPUP_CANONICAL_RECEIPTS_METADATA",
        "aggregate": small_record(TOPUP_AGGREGATE),
        "validated_jobs": len(validated),
        "validated_buildup_jobs": sum(row["mode"] == "buildup" for row in validated),
        "records": validated,
        "sim_access": "NONE__RECEIPT_METADATA_ONLY",
    }


def prerequisite_status(mission_path: Path = MISSION_SUMMARY) -> dict[str, Any]:
    missing: list[str] = []
    errors: list[str] = []
    authorities: dict[str, Any] = {}
    gate_ready = False
    topup_receipts_ready = False
    plan1_rows: list[dict[str, Any]] = []
    topup_rows: list[dict[str, Any]] = []

    if not mission_path.is_file():
        missing.append(str(mission_path))
    else:
        try:
            authorities["central_mission_gate"] = validate_mission_gate(mission_path)
            gate_ready = True
        except Exception as exc:
            errors.append(f"central mission gate: {exc}")

    required_small = (
        PLAN1_JOB_PLAN, PLAN1_SEED_REGISTRY, PLAN1_BACKGROUND_VALIDATION,
        TOPUP_PLAN, TOPUP_SEEDS, TOPUP_STATIC_AUDIT, TOPUP_AGGREGATE,
        base.NUBASE, SF3_SETUP,
    )
    for path in required_small:
        if not path.is_file():
            missing.append(str(path))

    if TOPUP_STATIC_AUDIT.is_file():
        try:
            static_audit = load_small_json(TOPUP_STATIC_AUDIT, "top-up static audit")
            if static_audit.get("status") != "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED":
                raise RuntimeError("status differs")
            gate_record = static_audit.get("gate_authorization") or {}
            if gate_record.get("central_R_F3") != authorities.get("central_mission_gate", {}).get("central_R_F3"):
                raise RuntimeError("top-up static audit is not bound to the current central ratio")
            authorities["topup_static_audit"] = small_record(TOPUP_STATIC_AUDIT)
        except Exception as exc:
            errors.append(f"top-up static audit: {exc}")

    if PLAN1_JOB_PLAN.is_file():
        try:
            plan1_rows = plan1_background_rows()
            if PLAN1_BACKGROUND_VALIDATION.is_file():
                authorities["plan1_receipt_gate"] = validate_plan1_receipt_gate(plan1_rows)
        except Exception as exc:
            errors.append(f"Plan-1 background authority: {exc}")
    if TOPUP_PLAN.is_file():
        try:
            topup_rows = topup_background_rows()
            if TOPUP_AGGREGATE.is_file():
                authorities["topup_receipt_gate"] = validate_topup_receipt_gate(topup_rows)
                topup_receipts_ready = True
        except Exception as exc:
            errors.append(f"top-up background authority: {exc}")
    if plan1_rows and topup_rows:
        try:
            combined = combined_buildup_rows(plan1_rows, topup_rows)
            authorities["combined_buildup"] = {
                "status": "PASS__23_BUILDUP_RECEIPTS_AT_S3D_FULL_STAT",
                "jobs": len(combined),
                "plan1_jobs": sum(row["source_namespace"] == "PLAN1_CANONICAL_PASS" for row in combined),
                "topup_jobs": sum(row["source_namespace"] == "FULLSTAT_TOPUP_CANONICAL_PASS" for row in combined),
                "histories": sum(int(row["events"]) for row in combined),
            }
        except Exception as exc:
            errors.append(f"combined buildup closure: {exc}")

    existing_manifest = OUTPUT_ROOT / "manifest.json"
    already_prepared = False
    if existing_manifest.is_file():
        try:
            already_prepared = load_small_json(existing_manifest, "full-stat activation manifest").get("status") == FULLSTAT_STATUS
        except Exception as exc:
            errors.append(f"existing full-stat activation manifest: {exc}")
    elif OUTPUT_ROOT.exists() and (not OUTPUT_ROOT.is_dir() or any(OUTPUT_ROOT.iterdir())):
        errors.append(f"non-empty full-stat activation output lacks manifest: {OUTPUT_ROOT}")

    ready = (
        gate_ready
        and topup_receipts_ready
        and not missing
        and not errors
        and len(plan1_rows) == 21
        and len(topup_rows) == 28
    )
    if already_prepared and ready:
        status = "PASS__SF3_FULLSTAT_ACTIVATION_ALREADY_PREPARED"
    elif ready:
        status = "READY__SF3_FULLSTAT_ACTIVATION_DOUBLE_GATE"
    elif errors:
        status = "FAIL__SF3_FULLSTAT_ACTIVATION_PREREQUISITES"
    else:
        status = "WAITING__CENTRAL_GATE_AND_28_TOPUP_RECEIPTS"
    return {
        "schema_version": 1,
        "status": status,
        "ready": ready,
        "already_prepared": already_prepared,
        "checked_at": utc_now(),
        "hard_gates": {
            "central_mission_topup_required_true": gate_ready,
            "all_28_topup_background_canonical_PASS": topup_receipts_ready,
        },
        "authorities": authorities,
        "plan1_background_jobs": len(plan1_rows),
        "topup_background_jobs": len(topup_rows),
        "combined_buildup_jobs": authorities.get("combined_buildup", {}).get("jobs", 0),
        "missing": sorted(set(missing)),
        "errors": errors,
        "output_root": str(OUTPUT_ROOT),
        "delayed_card_root": str(DELAYED_CARD_ROOT),
        "sim_access_policy": "CHECK_PREREQUISITES_NEVER_OPENS_STATS_OR_HASHES_SIM",
        "transport_launched": False,
    }


def occupied_for_fullstat_delayed(
    plan1_rows: Sequence[dict[str, Any]], topup_rows: Sequence[dict[str, Any]]
) -> tuple[set[int], dict[str, Any]]:
    occupied, authority = collect_occupied_seeds()
    with PLAN1_SEED_REGISTRY.open(newline="", encoding="utf-8") as handle:
        plan1_seeds = {int(row["seed"]) for row in csv.DictReader(handle)}
    with TOPUP_SEEDS.open(newline="", encoding="utf-8") as handle:
        topup_seeds = {int(row["seed"]) for row in csv.DictReader(handle)}
    if len(plan1_seeds) != 30 or len(topup_seeds) != 28:
        raise RuntimeError("Plan-1/top-up seed registry count differs from 30/28")
    if plan1_seeds & topup_seeds:
        raise RuntimeError("Plan-1 and top-up seed registries collide")
    if {int(row["seed"]) for row in plan1_rows} - plan1_seeds:
        raise RuntimeError("Plan-1 plan seed absent from registry")
    if {int(row["seed"]) for row in topup_rows} - topup_seeds:
        raise RuntimeError("top-up plan seed absent from registry")
    occupied.update(plan1_seeds)
    occupied.update(topup_seeds)
    return occupied, {
        **authority,
        "plan1_seed_registry": small_record(PLAN1_SEED_REGISTRY),
        "topup_seed_registry": small_record(TOPUP_SEEDS),
        "occupied_including_plan1_and_topup": len(occupied),
    }


def derive_fullstat_delayed_seeds(occupied: set[int]) -> dict[str, int]:
    reserved = set(occupied)
    result: dict[str, int] = {}
    for family in FAMILIES:
        identity = f"sf3_fullstat_delayed_{family}"
        seed = derive_seed(identity, reserved, namespace=FULLSTAT_DELAYED_NAMESPACE)
        result[family] = seed
        reserved.add(seed)
    if len(result) != 8 or len(set(result.values())) != 8 or set(result.values()) & occupied:
        raise RuntimeError("fresh full-stat delayed seed derivation failed")
    return result


def delayed_source_path(family: str) -> Path:
    return DELAYED_CARD_ROOT / f"sf3_fullstat_delayed_{family}.source"


def delayed_active_prefix(job_id: str) -> Path:
    return FULLSTAT_DELAYED_RUN_ROOT / "jobs" / job_id / "active" / job_id


def delayed_receipt_path(job_id: str) -> Path:
    return FULLSTAT_DELAYED_RECEIPT_ROOT / f"{job_id}.json"


def build_delayed_plan(
    seeds: dict[str, int], decisions: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal, family in enumerate(FAMILIES, 1):
        job_id = f"sf3_fullstat_delayed_{family}"
        decision = decisions[family]
        disposition = str(decision["execution_disposition"])
        eligible = disposition == POSITIVE_DISPOSITION
        if not eligible and disposition != ZERO_DISPOSITION:
            raise RuntimeError(f"unknown full-stat delayed disposition: {family}/{disposition}")
        actual = FULLSTAT_DELAYED_EVENTS if eligible else 0
        row = {
            "ordinal": ordinal,
            "job_id": job_id,
            "stage": "fullstat_delayed",
            "geometry": "SF3",
            "mode": "delayed",
            "family": family,
            "registered_events": FULLSTAT_DELAYED_EVENTS,
            "events": actual,
            "actual_transport_events": actual,
            "seed": int(seeds[family]),
            "sampling_seed": int(seeds[family]),
            "seed_identity": job_id,
            "seed_namespace": FULLSTAT_DELAYED_NAMESPACE,
            "source_path": str(delayed_source_path(family)),
            "setup_path": str(SF3_SETUP),
            "run_root": str(FULLSTAT_DELAYED_RUN_ROOT),
            "receipt_path": str(delayed_receipt_path(job_id)),
            "aggregate_receipt_path": str(FULLSTAT_DELAYED_AGGREGATE),
            "source_status": decision["source_status"],
            "execution_disposition": disposition,
            "transport_eligible": bool_text(eligible),
            "plan1_83334_role": PLAN1_DELAYED_ROLE,
            "incremental_merge_allowed": "false",
            "source_support": "REBUILT_FULLSTAT_23_BUILDUP_RECEIPTS_ACTUAL_RPIP_POSITIONS",
        }
        if tuple(row) != DELAYED_PLAN_FIELDS:
            raise RuntimeError("internal full-stat delayed plan schema drift")
        rows.append(row)
    if len(rows) != 8 or len({int(row["seed"]) for row in rows}) != 8:
        raise RuntimeError("full-stat delayed plan does not contain eight fresh seed rows")
    if any(int(row["registered_events"]) != 250_000 for row in rows):
        raise RuntimeError("full-stat delayed registered event count differs from 250,000")
    if any("83334" in str(row["events"]) or "166666" in str(row["events"]) for row in rows):
        raise RuntimeError("forbidden Plan-1/incremental delayed event count entered full-stat plan")
    return rows


def aggregate_family_production(
    family: str, entries: Sequence[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aggregate one family while retaining TT from every selected DAT."""
    if not entries:
        raise RuntimeError(f"full-stat/{family}: no buildup DAT entries")
    sum_tt = math.fsum(float(item["parsed_dat"]["TT_s"]) for item in entries)
    if not math.isfinite(sum_tt) or sum_tt <= 0.0:
        raise RuntimeError(f"full-stat/{family}: non-positive sum(TT)")
    state_values: dict[tuple[str, int, float], list[float]] = defaultdict(list)
    positive_dat: dict[tuple[str, int, float], set[str]] = defaultdict(set)
    for item in entries:
        for key, value in item["parsed_dat"]["totals"].items():
            state_values[key].append(float(value))
            if float(value) > 0.0:
                positive_dat[key].add(str(item["job"]["job_id"]))
    rows: list[dict[str, Any]] = []
    for key, values in sorted(state_values.items()):
        sum_rp = math.fsum(values)
        za = int(key[1])
        rows.append({
            "geometry": "SF3",
            "family": family,
            "volume": key[0],
            "isotope_id": za,
            "Z": za // 1000,
            "A": za % 1000,
            "excitation_keV": key[2],
            "sum_RP": sum_rp,
            "sum_TT_s_including_zero_RP_DAT": sum_tt,
            "production_rate_s-1": sum_rp / sum_tt,
            "N_DAT_denominator": len(entries),
            "N_DAT_with_positive_RP_for_state": len(positive_dat[key]),
            "N_DAT_with_zero_RP_for_state": len(entries) - len(positive_dat[key]),
        })
    sum_rp = math.fsum(float(item["parsed_dat"]["sum_RP"]) for item in entries)
    cell = {
        "geometry": "SF3",
        "incident_family": family,
        "N_BUILDUP_files": len(entries),
        "generated_primaries": sum(int(item["job"]["events"]) for item in entries),
        "sum_TT_s": sum_tt,
        "sum_RP": sum_rp,
        "production_rate_s-1": sum_rp / sum_tt,
        "zero_RP_files": sum(float(item["parsed_dat"]["sum_RP"]) == 0.0 for item in entries),
        "cell_status": "PENDING_STATE_AND_RPIP_CLASSIFICATION",
    }
    return rows, cell


def render_fullstat_delayed_source(
    job: dict[str, Any],
    sampled: Sequence[dict[str, Any]],
    total_activity: float,
) -> tuple[str, dict[str, Any]]:
    """Render a fresh 250k card from a full-stat 50k -> 10k mixture."""
    retained = list(sampled[:: base.POSITION_STRIDE])
    if sampled and len(sampled) != base.ORIGINAL_POSITION_BLOCKS:
        raise RuntimeError(
            f"{job['job_id']}: full-stat original sample count {len(sampled)} "
            f"!= {base.ORIGINAL_POSITION_BLOCKS}"
        )
    if sampled and len(retained) != base.TRANSPORT_POSITION_BLOCKS:
        raise RuntimeError(
            f"{job['job_id']}: full-stat transport block count {len(retained)} "
            f"!= {base.TRANSPORT_POSITION_BLOCKS}"
        )
    if sampled and (not math.isfinite(total_activity) or total_activity <= 0.0):
        raise RuntimeError(f"{job['job_id']}: sampled source has non-positive activity")
    if not sampled and total_activity != 0.0:
        raise RuntimeError(f"{job['job_id']}: positive activity lacks exact-position support")
    original_flux = total_activity / base.ORIGINAL_POSITION_BLOCKS if sampled else 0.0
    transport_flux = original_flux * base.POSITION_STRIDE
    prefix = delayed_active_prefix(str(job["job_id"]))
    lines = [
        "# Fresh SF3 full-stat day-15 exact-position delayed source",
        "# Rebuilt from 23 full-stat BUILDUP receipts; Plan-1 delayed is not consumed or merged.",
        f"# original_blocks={len(sampled)} stride={base.POSITION_STRIDE} retained_blocks={len(retained)}",
        f"# original_flux_Bq={original_flux:.17g} retained_flux_Bq={transport_flux:.17g}",
        "Version 1",
        f"Geometry {SF3_SETUP}",
        f"Seed {job['seed']}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {prefix}",
        f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}",
        "",
    ]
    if retained:
        lines.extend(f"DecayRun.Source RP_{int(row['sample_index']):07d}" for row in retained)
        lines.extend(("", "# Exact full-stat RPIP positions; excited states are fail-closed upstream."))
        for row in retained:
            name = f"RP_{int(row['sample_index']):07d}"
            lines.extend([
                f"# state VN={row['volume']} ZA={row['ZA']} excitation_keV={float(row['excitation_keV']):.2f}",
                f"{name}.ParticleType {int(row['ZA'])}",
                f"{name}.Beam PointSource {float(row['x_cm']):.8g} {float(row['y_cm']):.8g} {float(row['z_cm']):.8g}",
                f"{name}.Spectrum Mono {base.MONO_EPSILON_KEV:.8g}",
                f"{name}.Flux {transport_flux:.17g}",
                "",
            ])
        source_status = "PASS__SF3_FULLSTAT_STRIDE5_M10000_DELAYED_SOURCE_READY"
        disposition = POSITIVE_DISPOSITION
    else:
        lines.extend([
            "# ZERO_SOURCE_NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
            "# Registered at 250000 but actual transport is exactly skipped; no DecayRun.Source.",
        ])
        source_status = "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY"
        disposition = ZERO_DISPOSITION
    original_total = original_flux * len(sampled)
    transport_total = transport_flux * len(retained)
    original_closure = original_total - total_activity
    transport_closure = transport_total - total_activity
    if retained and not math.isclose(
        transport_total, total_activity, rel_tol=2.0e-15, abs_tol=1.0e-18
    ):
        raise RuntimeError(f"{job['job_id']}: full-stat stride-five flux closure failed")
    return "\n".join(lines) + "\n", {
        "source_status": source_status,
        "execution_disposition": disposition,
        "registered_events": FULLSTAT_DELAYED_EVENTS,
        "actual_transport_events": FULLSTAT_DELAYED_EVENTS if retained else 0,
        "original_blocks": len(sampled),
        "position_stride": base.POSITION_STRIDE,
        "transport_blocks": len(retained),
        "original_block_flux_Bq": original_flux,
        "transport_block_flux_Bq": transport_flux,
        "original_total_Bq": original_total,
        "transport_total_Bq": transport_total,
        "original_closure_Bq": original_closure,
        "transport_closure_Bq": transport_closure,
        "spectrum_epsilon_keV": base.MONO_EPSILON_KEV,
        "plan1_83334_consumed": False,
        "incremental_merge_allowed": False,
    }


def build_passive_w_diagnostics(inventory: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for family in FAMILIES:
        for volume in PASSIVE_W_VOLUMES:
            rows = [
                row for row in inventory
                if row["incident_family"] == family and row["source_volume"] == volume
            ]
            if base.material_category(volume) != "passive_w_or_collimator":
                raise RuntimeError(f"exact SF3 W volume is not classified passive: {volume}")
            known = math.fsum(
                float(row["day15_activity_Bq"])
                for row in rows if row["day15_activity_Bq"] != ""
            )
            transported = math.fsum(
                float(row["day15_activity_Bq"])
                for row in rows
                if row["day15_activity_Bq"] != ""
                and row["source_disposition"] == "transported_ground_state"
            )
            holdout = math.fsum(
                float(row["day15_activity_Bq"])
                for row in rows
                if row["day15_activity_Bq"] != ""
                and row["source_disposition"] != "transported_ground_state"
            )
            diagnostics.append({
                "geometry": "SF3",
                "incident_family": family,
                "source_volume": volume,
                "volume_role": "PASSIVE_W_NEARFIELD__DIAGNOSTIC_ONLY",
                "material_category": "passive_w_or_collimator",
                "state_rows": len(rows),
                "sum_RP": math.fsum(float(row["sum_RP"]) for row in rows),
                "known_day15_activity_Bq": known,
                "transported_ground_activity_Bq": transported,
                "known_holdout_activity_Bq": holdout,
                "unknown_activity_state_count": sum(row["day15_activity_Bq"] == "" for row in rows),
                "bgo_veto_member": False,
                "plastic_veto_member": False,
                "veto_disposition": "PASSIVE__NEVER_BGO_OR_PLASTIC_VETO",
            })
    if len(diagnostics) != len(FAMILIES) * len(PASSIVE_W_VOLUMES):
        raise RuntimeError("exact passive-W family/volume diagnostic grid is incomplete")
    summary = {
        "schema_version": 1,
        "status": "PASS__EXACT_THREE_SF3_W_VOLUMES_DIAGNOSTIC_AND_PASSIVE",
        "geometry": "SF3",
        "exact_volume_whitelist": list(PASSIVE_W_VOLUMES),
        "diagnostic_rows": len(diagnostics),
        "families": list(FAMILIES),
        "known_day15_activity_Bq": math.fsum(float(row["known_day15_activity_Bq"]) for row in diagnostics),
        "transported_ground_activity_Bq": math.fsum(float(row["transported_ground_activity_Bq"]) for row in diagnostics),
        "known_holdout_activity_Bq": math.fsum(float(row["known_holdout_activity_Bq"]) for row in diagnostics),
        "bgo_veto_members": 0,
        "plastic_veto_members": 0,
        "passive_w_never_veto": True,
        "selection_policy": "EXACT_SOURCE_VOLUME_WHITELIST_ONLY__NO_BROAD_W_SUBSTRING_MATCH",
    }
    return diagnostics, summary


def receipt_path_for_job(job: dict[str, Any]) -> Path:
    if job["source_namespace"] == "PLAN1_CANONICAL_PASS":
        return PLAN1_RECEIPT_ROOT / f"{job['job_id']}.json"
    if job["source_namespace"] == "FULLSTAT_TOPUP_CANONICAL_PASS":
        return TOPUP_RECEIPT_ROOT / f"{job['job_id']}.json"
    raise RuntimeError(f"unknown buildup receipt namespace: {job['source_namespace']}")


def receipt_binding_for_job(job: dict[str, Any]) -> tuple[str, Path]:
    if job["source_namespace"] == "PLAN1_CANONICAL_PASS":
        return base.PROFILE_ID, RUN_ROOT
    if job["source_namespace"] == "FULLSTAT_TOPUP_CANONICAL_PASS":
        return topup.TOPUP_NAMESPACE, TOPUP_RUN_ROOT
    raise RuntimeError(f"unknown buildup receipt namespace: {job['source_namespace']}")


def build_prepare_payload(
    staging_output: Path,
    staging_cards: Path,
    buildup_jobs: Sequence[dict[str, Any]],
    seeds: dict[str, int],
    prerequisite: dict[str, Any],
    seed_authority: dict[str, Any],
) -> dict[str, Any]:
    """Build full-stat outputs; this is the only path that semantically opens SIMs."""
    nubase = base.load_nubase_states()
    copy_map = base.geometry_copy_map(SF3_SETUP)
    parsed_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    receipt_authorities: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    dat_entries: list[dict[str, Any]] = []

    for job in buildup_jobs:
        receipt_path = receipt_path_for_job(job)
        receipt = load_small_json(receipt_path, f"selected buildup receipt {job['job_id']}")
        profile, run_root = receipt_binding_for_job(job)
        errors = validate_receipt_metadata(job, receipt, profile_id=profile, run_root=run_root)
        if errors:
            raise RuntimeError(f"{job['job_id']}: receipt metadata drift before prepare: {errors}")
        dat_path = Path(str(receipt["isotope_dat_path"]))
        parsed = base.parse_dat(dat_path)
        declared = receipt.get("isotope_dat") or {}
        if not math.isclose(parsed["TT_s"], float(declared["TT_s"]), rel_tol=0.0, abs_tol=1.0e-12):
            raise RuntimeError(f"{job['job_id']}: parsed DAT TT differs from canonical receipt")
        if parsed["RP_record_count"] != int(declared["RP_record_count"]):
            raise RuntimeError(f"{job['job_id']}: parsed DAT RP count differs from canonical receipt")
        receipt_digest = sha256(receipt_path)
        item = {
            "job": job,
            "receipt": receipt,
            "receipt_path": receipt_path,
            "dat_path": dat_path,
            "sim_path": Path(str(receipt["sim_path"])),
            "parsed_dat": parsed,
        }
        parsed_by_family[str(job["family"])].append(item)
        receipt_authorities.append({
            "job_id": job["job_id"],
            "source_namespace": job["source_namespace"],
            "path": str(receipt_path.resolve()),
            "sha256": receipt_digest,
        })
        dat_digest = sha256(dat_path)
        dat_entry = {
            "geometry": "SF3",
            "family": job["family"],
            "mode": "buildup",
            "source_namespace": job["source_namespace"],
            "job_id": job["job_id"],
            "events": int(job["events"]),
            "seed": int(job["seed"]),
            "receipt_path": str(receipt_path.resolve()),
            "receipt_sha256": receipt_digest,
            "dat_path": str(dat_path.resolve()),
            "dat_bytes": dat_path.stat().st_size,
            "dat_sha256": dat_digest,
            "TT_s": parsed["TT_s"],
            "RP_record_count": parsed["RP_record_count"],
            "sum_RP": parsed["sum_RP"],
            "zero_RP": parsed["sum_RP"] == 0.0,
            "sim_reference": {
                "path": str(Path(str(receipt["sim_path"])).resolve()),
                "declared_bytes": int(receipt["sim_bytes"]),
                "sha256": None,
                "policy": "ONE_SEMANTIC_CC_IP_RP_PASS__NO_SIM_HASH",
            },
        }
        dat_entries.append(dat_entry)
        input_rows.append({
            "job_id": job["job_id"],
            "source_namespace": job["source_namespace"],
            "family": job["family"],
            "events": int(job["events"]),
            "seed": int(job["seed"]),
            "receipt_path": str(receipt_path.resolve()),
            "receipt_sha256": receipt_digest,
            "dat_path": str(dat_path.resolve()),
            "dat_sha256": dat_digest,
            "sim_path": str(Path(str(receipt["sim_path"])).resolve()),
            "sim_declared_bytes": int(receipt["sim_bytes"]),
            "sim_sha256": "OMITTED_BY_CONTRACT",
            "TT_s": parsed["TT_s"],
            "RP_record_count": parsed["RP_record_count"],
            "sum_RP": parsed["sum_RP"],
            "zero_RP": parsed["sum_RP"] == 0.0,
        })

    if sum(len(rows) for rows in parsed_by_family.values()) != 23:
        raise RuntimeError("parsed full-stat buildup DAT count is not exactly 23")
    production_by_family: dict[str, list[dict[str, Any]]] = {}
    activation_cells: list[dict[str, Any]] = []
    for family in FAMILIES:
        rows, cell = aggregate_family_production(family, parsed_by_family[family])
        expected_histories = S3D_HISTORIES[("buildup", family)]
        if int(cell["generated_primaries"]) != expected_histories:
            raise RuntimeError(f"{family}: parsed full-stat generated history closure differs")
        production_by_family[family] = rows
        activation_cells.append(cell)

    scan_audits: list[dict[str, Any]] = []
    all_points: dict[str, dict[tuple[str, int, float], list[tuple[float, float, float]]]] = {}
    for family in FAMILIES:
        production_keys = {
            base.state_key(row["volume"], row["isotope_id"], row["excitation_keV"])
            for row in production_by_family[family]
        }
        family_points: dict[tuple[str, int, float], list[tuple[float, float, float]]] = defaultdict(list)
        for item in parsed_by_family[family]:
            points, audit = base.parse_rpip_file(item["sim_path"], production_keys, copy_map)
            if int(audit["sim_bytes"]) != int(item["receipt"]["sim_bytes"]):
                raise RuntimeError(f"{item['job']['job_id']}: SIM size changed before semantic scan")
            audit.update({
                "job_id": item["job"]["job_id"],
                "family": family,
                "source_namespace": item["job"]["source_namespace"],
                "sim_digest": None,
            })
            scan_audits.append(audit)
            for key, values in points.items():
                family_points[key].extend(values)
        all_points[family] = dict(family_points)

    staging_cards.mkdir(parents=True, exist_ok=False)
    sampled_root = staging_output / "exact_position_sources"
    sampled_root.mkdir(parents=True, exist_ok=False)
    inventory: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    source_manifests: list[dict[str, Any]] = []
    state_summary: list[dict[str, Any]] = []
    card_payloads: dict[str, str] = {}
    decisions: dict[str, dict[str, Any]] = {}

    for family in FAMILIES:
        rows = production_by_family[family]
        points = all_points[family]
        cell = activation_cells[FAMILIES.index(family)]
        included, holdout = base.classify_states(rows, points, nubase)
        base.require_complete_positive_ground(family, holdout)
        included_activity = math.fsum(float(row["day15_activity_Bq"]) for row in included)
        known_holdout_activity = math.fsum(
            float(row["day15_activity_Bq"])
            for row in holdout if row["day15_activity_Bq"] is not None
        )
        unknown_count = sum(row["day15_activity_Bq"] is None for row in holdout)
        seed = int(seeds[family])
        sampled = base.weighted_sample(included, points, base.ORIGINAL_POSITION_BLOCKS, seed)
        if included_activity > 0.0 and len(sampled) != base.ORIGINAL_POSITION_BLOCKS:
            raise RuntimeError(f"full-stat/{family}: failed to generate exact 50k sample")
        family_dir = sampled_root / family
        family_dir.mkdir(parents=True, exist_ok=False)
        sampled_path = family_dir / "sampled_exact_positions_m50000.csv"
        base.write_csv(
            sampled_path,
            sampled,
            ("sample_index", "volume", "ZA", "excitation_keV", "x_cm", "y_cm", "z_cm"),
        )
        job = {"job_id": f"sf3_fullstat_delayed_{family}", "seed": seed}
        card_text, closure = render_fullstat_delayed_source(job, sampled, included_activity)
        staged_card = staging_cards / f"{job['job_id']}.source"
        staged_card.write_text(card_text, encoding="utf-8")
        card_payloads[family] = card_text
        source_status = closure["source_status"]
        disposition = closure["execution_disposition"]
        decisions[family] = {
            "source_status": source_status,
            "execution_disposition": disposition,
        }
        sum_tt = float(cell["sum_TT_s"])
        zero_count_upper = (
            base.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER
            if disposition == ZERO_DISPOSITION else None
        )
        rate_upper = zero_count_upper / sum_tt if zero_count_upper is not None else None
        a15_upper = rate_upper
        cell.update({
            "cell_status": source_status,
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": included_activity,
            "transported_ground_rate_upper95_s-1": rate_upper,
            "transported_ground_A15_upper95_Bq_conservative": a15_upper,
        })
        drawn = Counter((row["volume"], row["ZA"], row["excitation_keV"]) for row in sampled)
        family_scans = [row for row in scan_audits if row["family"] == family]
        source_manifest = {
            "schema_version": 1,
            "status": source_status,
            "execution_disposition": disposition,
            "geometry": "SF3",
            "family": family,
            "job_id": job["job_id"],
            "source": str(delayed_source_path(family).resolve()),
            "source_sha256": hashlib.sha256(card_text.encode("utf-8")).hexdigest(),
            "sampled_positions_table": str((OUTPUT_ROOT / sampled_path.relative_to(staging_output)).resolve()),
            "geometry_path": str(SF3_SETUP.resolve()),
            "sampling_seed": seed,
            "transport_seed": seed,
            "seed_namespace": FULLSTAT_DELAYED_NAMESPACE,
            "registered_triggers": FULLSTAT_DELAYED_EVENTS,
            "actual_transport_triggers": int(closure["actual_transport_events"]),
            "included_ground_activity_Bq": included_activity,
            "buildup_sum_TT_s": sum_tt,
            "zero_count_garwood_two_sided95_upper": zero_count_upper,
            "transported_ground_rate_upper95_s-1": rate_upper,
            "transported_ground_A15_upper95_Bq_conservative": a15_upper,
            "zero_A15_upper_provenance": base.ZERO_A15_UPPER_PROVENANCE if zero_count_upper is not None else None,
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_count,
            "included_states": included,
            "holdout_states": holdout,
            "sampled_state_counts": [
                {"volume": key[0], "ZA": key[1], "excitation_keV": key[2], "drawn": count}
                for key, count in drawn.most_common()
            ],
            "position_and_flux_closure": closure,
            "RPIP_audit": {
                "sim_files": len(family_scans),
                "CC_IP_RP_lines": sum(int(row["CC_IP_RP_lines"]) for row in family_scans),
                "matched_points": sum(int(row["matched_points"]) for row in family_scans),
                "unmatched_volume_points": sum(int(row["unmatched_volume_points"]) for row in family_scans),
                "unmatched_state_points": sum(int(row["unmatched_state_points"]) for row in family_scans),
                "files": family_scans,
            },
            "plan1_delayed_policy": PLAN1_DELAYED_ROLE,
            "incremental_merge_allowed": False,
            "passive_w_policy": "EXACT_THREE_VOLUME_DIAGNOSTIC_ONLY__NEVER_BGO_OR_PLASTIC_VETO",
        }
        base.write_json(family_dir / "source_manifest.json", source_manifest)
        source_manifests.append(source_manifest)
        source_index.append({
            "geometry": "SF3",
            "incident_family": family,
            "job_id": job["job_id"],
            "source_status": source_status,
            "execution_disposition": disposition,
            "transport_eligible": bool_text(disposition == POSITIVE_DISPOSITION),
            "registered_decay_triggers": FULLSTAT_DELAYED_EVENTS,
            "actual_transport_triggers": int(closure["actual_transport_events"]),
            "transported_ground_activity_Bq": included_activity,
            "buildup_sum_TT_s": sum_tt,
            "zero_count_garwood_two_sided95_upper": zero_count_upper if zero_count_upper is not None else "",
            "transported_ground_rate_upper95_s-1": rate_upper if rate_upper is not None else "",
            "transported_ground_A15_upper95_Bq_conservative": a15_upper if a15_upper is not None else "",
            "zero_A15_upper_provenance": base.ZERO_A15_UPPER_PROVENANCE if zero_count_upper is not None else "",
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_count,
            "included_state_count": len(included),
            "holdout_state_count": len(holdout),
            "RPIP_points": sum(len(values) for values in points.values()),
            "original_blocks": int(closure["original_blocks"]),
            "transport_blocks": int(closure["transport_blocks"]),
            "position_stride": int(closure["position_stride"]),
            "sampling_seed": seed,
            "transport_seed": seed,
            "seed_namespace": FULLSTAT_DELAYED_NAMESPACE,
            "original_block_flux_Bq": closure["original_block_flux_Bq"] if sampled else "",
            "transport_block_flux_Bq": closure["transport_block_flux_Bq"] if sampled else "",
            "original_total_Bq": closure["original_total_Bq"],
            "transport_total_Bq": closure["transport_total_Bq"],
            "original_closure_Bq": closure["original_closure_Bq"],
            "transport_closure_Bq": closure["transport_closure_Bq"],
            "source_path": str(delayed_source_path(family).resolve()),
            "source_sha256": source_manifest["source_sha256"],
            "sampled_positions_path": source_manifest["sampled_positions_table"],
            "source_manifest_path": str((OUTPUT_ROOT / family_dir.relative_to(staging_output) / "source_manifest.json").resolve()),
            "plan1_83334_role": PLAN1_DELAYED_ROLE,
            "incremental_merge_allowed": False,
        })
        for group, included_flag in ((included, True), (holdout, False)):
            for state in group:
                za = int(state["ZA"])
                activity = state["day15_activity_Bq"]
                inventory.append({
                    "geometry": "SF3",
                    "incident_family": family,
                    "source_volume": state["volume"],
                    "material_category": base.material_category(str(state["volume"])),
                    "source_parent_ZA": za,
                    "Z": za // 1000,
                    "A": za % 1000,
                    "excitation_keV": state["excitation_keV"],
                    "state_designator": state["state_designator"] if state["state_designator"] is not None else "",
                    "sum_RP": state["sum_RP"],
                    "sum_TT_s": state["sum_TT_s"],
                    "production_rate_s-1": state["production_rate_s-1"],
                    "half_life_s": state["half_life_s"] if state["half_life_s"] is not None else "",
                    "half_life_source": state["half_life_provenance"],
                    "day15_activity_Bq": activity if activity is not None else "",
                    "RPIP_support_count": state["RPIP_points"],
                    "source_disposition": (
                        "transported_ground_state" if included_flag else
                        "stable_or_zero_activity" if state.get("holdout_reason") == "zero_day15_activity" else
                        "excited_or_unresolved_holdout"
                    ),
                    "holdout_reason": state.get("holdout_reason", ""),
                })
        reason_counts = Counter(row.get("holdout_reason", "included_ground_state") for row in included + holdout)
        for reason, count in sorted(reason_counts.items()):
            selected = [
                row for row in included + holdout
                if row.get("holdout_reason", "included_ground_state") == reason
            ]
            state_summary.append({
                "geometry": "SF3",
                "incident_family": family,
                "state_class": reason,
                "state_rows": count,
                "sum_RP": math.fsum(float(row["sum_RP"]) for row in selected),
                "known_day15_activity_Bq": math.fsum(
                    float(row["day15_activity_Bq"])
                    for row in selected if row["day15_activity_Bq"] is not None
                ),
                "unknown_activity_state_count": sum(row["day15_activity_Bq"] is None for row in selected),
            })

    inventory.sort(key=lambda row: (
        FAMILIES.index(row["incident_family"]), row["source_volume"],
        row["source_parent_ZA"], row["excitation_keV"],
    ))
    all_production = [row for family in FAMILIES for row in production_by_family[family]]
    if len(inventory) != len(all_production):
        raise RuntimeError("full-stat day-15 inventory does not cover every production state")
    delayed_plan = build_delayed_plan(seeds, decisions)
    plan_by_family = {row["family"]: row for row in delayed_plan}
    for row in source_index:
        plan_row = plan_by_family[row["incident_family"]]
        if int(row["actual_transport_triggers"]) != int(plan_row["actual_transport_events"]):
            raise RuntimeError(f"source-index/job-plan event mismatch: {row['incident_family']}")
    seed_rows = [{
        "job_id": row["job_id"],
        "family": row["family"],
        "seed_identity": row["seed_identity"],
        "seed": row["seed"],
        "namespace": FULLSTAT_DELAYED_NAMESPACE,
        "collision_with_prior_plan1_or_topup": False,
        "sampling_and_transport_seed_shared_within_job": True,
    } for row in delayed_plan]

    family_summary = base.aggregate_known(inventory)
    passive_w_rows, passive_w_summary = build_passive_w_diagnostics(inventory)
    zero_families = [
        row["incident_family"] for row in source_index
        if row["execution_disposition"] == ZERO_DISPOSITION
    ]
    catalog = {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_CORRECTED_BUILDUP_CATALOG_READY",
        "authority_class": "SF3_FULLSTAT_23_BUILDUP_DAT_AND_ACTUAL_POSITION_CATALOG",
        "geometry": "SF3",
        "mode": "buildup_only",
        "selected_buildup_jobs": 23,
        "selected_buildup_histories": 3_046_468,
        "normalization": {
            "production_rate": "sum(RP)/sum(TT) within each SF3 incident family across all Plan-1+top-up buildup DAT",
            "zero_RP_DAT_TT_retained": True,
            "state_key": "logical volume x ZA x excitation rounded to 0.01 keV",
        },
        "plan1_delayed_consumed": False,
        "dat_entries": dat_entries,
        "cells": activation_cells,
        "production_rows": all_production,
        "sim_payload_policy": "ONE_CC_IP_RP_SEMANTIC_PASS_FOR_ACTUAL_POSITIONS__NO_SIM_HASH",
    }
    base.write_json(staging_output / "corrected_buildup_catalog.json", catalog)
    base.write_json(staging_output / "production_position_scan.json", {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_23_SIM_RPIP_SEMANTIC_SCAN_COMPLETE",
        "sim_files_scanned": len(scan_audits),
        "sim_bytes_scanned_compressed": sum(int(row["sim_bytes"]) for row in scan_audits),
        "matched_points": sum(int(row["matched_points"]) for row in scan_audits),
        "files": scan_audits,
        "policy": "ONE_SEMANTIC_CC_IP_RP_PASS_PER_SELECTED_SIM__NO_SIM_DIGEST",
    })

    activation_fields = (
        "geometry", "incident_family", "N_BUILDUP_files", "generated_primaries", "sum_TT_s",
        "sum_RP", "production_rate_s-1", "zero_RP_files", "cell_status",
        "execution_disposition", "transported_ground_activity_Bq",
        "transported_ground_rate_upper95_s-1", "transported_ground_A15_upper95_Bq_conservative",
    )
    inventory_fields = (
        "geometry", "incident_family", "source_volume", "material_category", "source_parent_ZA",
        "Z", "A", "excitation_keV", "state_designator", "sum_RP", "sum_TT_s",
        "production_rate_s-1", "half_life_s", "half_life_source", "day15_activity_Bq",
        "RPIP_support_count", "source_disposition", "holdout_reason",
    )
    source_fields = tuple(source_index[0])
    passive_w_fields = tuple(passive_w_rows[0])
    base.write_csv(staging_output / "activation_cells.csv", activation_cells, activation_fields)
    base.write_csv(staging_output / "day15_inventory.csv", inventory, inventory_fields)
    base.write_csv(staging_output / "delayed_source_index.csv", source_index, source_fields)
    base.write_csv(staging_output / "passive_w_activation_diagnostics.csv", passive_w_rows, passive_w_fields)
    base.write_json(staging_output / "passive_w_activation_summary.json", passive_w_summary)
    base.write_csv(
        staging_output / "state_holdout_summary.csv", state_summary,
        ("geometry", "incident_family", "state_class", "state_rows", "sum_RP", "known_day15_activity_Bq", "unknown_activity_state_count"),
    )
    base.write_csv(
        staging_output / "buildup_input_manifest.csv", input_rows,
        (
            "job_id", "source_namespace", "family", "events", "seed", "receipt_path",
            "receipt_sha256", "dat_path", "dat_sha256", "sim_path", "sim_declared_bytes",
            "sim_sha256", "TT_s", "RP_record_count", "sum_RP", "zero_RP",
        ),
    )

    summary = {
        "schema_version": 1,
        "status": FULLSTAT_STATUS,
        "scope": "SF3 full-stat corrected-keV buildup production, day-15 inventory, and fresh exact-position delayed preparation",
        "geometry": "SF3",
        "selected_buildup_jobs": len(buildup_jobs),
        "selected_plan1_buildup_jobs": sum(row["source_namespace"] == "PLAN1_CANONICAL_PASS" for row in buildup_jobs),
        "selected_topup_buildup_jobs": sum(row["source_namespace"] == "FULLSTAT_TOPUP_CANONICAL_PASS" for row in buildup_jobs),
        "selected_buildup_histories": sum(int(row["events"]) for row in buildup_jobs),
        "sum_RP": math.fsum(float(row["sum_RP"]) for row in activation_cells),
        "sum_TT_s": math.fsum(float(row["sum_TT_s"]) for row in activation_cells),
        "production_state_rows": len(inventory),
        "matched_RPIP_points": sum(int(row["matched_points"]) for row in scan_audits),
        "positive_transport_source_cells": len(FAMILIES) - len(zero_families),
        "zero_source_cells": len(zero_families),
        "zero_source_families": zero_families,
        "zero_source_upper_limits": [
            {
                "family": row["incident_family"],
                "buildup_sum_TT_s": row["buildup_sum_TT_s"],
                "zero_count_garwood_two_sided95_upper": row["zero_count_garwood_two_sided95_upper"],
                "transported_ground_rate_upper95_s-1": row["transported_ground_rate_upper95_s-1"],
                "transported_ground_A15_upper95_Bq_conservative": row["transported_ground_A15_upper95_Bq_conservative"],
                "provenance": row["zero_A15_upper_provenance"],
            }
            for row in source_index if row["execution_disposition"] == ZERO_DISPOSITION
        ],
        "registered_delayed_source_cells": 8,
        "fresh_delayed_transport_jobs_planned": len(FAMILIES) - len(zero_families),
        "delayed_zero_source_jobs_skipped": len(zero_families),
        "registered_delayed_triggers_per_family": FULLSTAT_DELAYED_EVENTS,
        "actual_delayed_triggers_total": sum(int(row["actual_transport_triggers"]) for row in source_index),
        "day15_by_family": family_summary,
        "normalization": "sum(RP)/sum(TT) per SF3 family across all 23 buildup DAT; every zero-RP DAT TT included",
        "state_policy": "NUBASE-2020 state-aware; excited and unresolved states fail closed",
        "source_mixture_policy": "50k deterministic actual-position draws; stride 5 to 10k; retained flux multiplied by 5",
        "plan1_delayed_role": PLAN1_DELAYED_ROLE,
        "plan1_83334_consumed_or_merged": False,
        "incremental_166666_merge_allowed": False,
        "passive_w": passive_w_summary,
        "sim_policy": "one semantic CC IP RP pass per 23 selected SIM; no SIM digest",
        "authority_boundary": "FULLSTAT_ACTIVATION_AND_SOURCE_PREPARATION_ONLY__NO_DELAYED_TRANSPORT_RESPONSE_MISSION_F3_OR_PROMOTION_AUTHORITY",
    }
    base.write_json(staging_output / "day15_summary.json", summary)
    manifest = {
        **summary,
        "created_at": utc_now(),
        "output_root": str(OUTPUT_ROOT.resolve()),
        "hard_gates": prerequisite["hard_gates"],
        "gate_authorities": prerequisite["authorities"],
        "job_plan_target": str(DELAYED_JOB_PLAN.resolve()),
        "seed_registry_target": str(DELAYED_SEED_REGISTRY.resolve()),
        "seed_authority": seed_authority,
        "fresh_delayed_seeds": seeds,
        "receipt_authorities": receipt_authorities,
        "source_cells": source_manifests,
        "nubase": small_record(base.NUBASE),
    }
    base.write_json(staging_output / "manifest.json", manifest)
    report = (
        "# SF3 full-stat activation and fresh delayed-source preparation\n\n"
        f"Status: {FULLSTAT_STATUS}\n\n"
        "This package is authorized only by the central F3 gate and complete 28-job top-up receipt gate. "
        "It combines 10 Plan-1 plus 13 top-up BUILDUP jobs (23 total; 3,046,468 histories), "
        "retaining TT from every DAT including zero-RP files.\n\n"
        "Every positive family is registered as a fresh 250,000-trigger delayed job built from a new "
        "50,000-draw actual-position mixture reduced to 10,000 blocks by stride five. Exact-zero "
        "families are skipped with a finite 3.688879/sumTT upper. Plan-1 83,334-trigger delayed "
        "products and a default 83,334+166,666 merge are forbidden.\n\n"
        "The three exact SF3 near-field W volumes are reported diagnostically and remain passive; "
        "none enters BGO or plastic veto. SIMs are used only for one CC IP RP semantic pass and are never hashed.\n"
    )
    (staging_output / "REPORT.md").write_text(report, encoding="utf-8")
    return {
        "summary": summary,
        "manifest": manifest,
        "card_payloads": card_payloads,
        "delayed_plan": delayed_plan,
        "seed_rows": seed_rows,
        "source_index": source_index,
        "passive_w_summary": passive_w_summary,
    }


def publish_activation_validation(
    manifest: dict[str, Any], prerequisite: dict[str, Any]
) -> dict[str, Any]:
    if manifest.get("status") != FULLSTAT_STATUS:
        raise RuntimeError("full-stat activation manifest semantic status differs")
    if prerequisite.get("hard_gates") != {
        "central_mission_topup_required_true": True,
        "all_28_topup_background_canonical_PASS": True,
    }:
        raise RuntimeError("full-stat activation hard gates are not both true")
    manifest_path = OUTPUT_ROOT / "manifest.json"
    summary_path = OUTPUT_ROOT / "day15_summary.json"
    index_path = SOURCE_INDEX
    w_summary_path = OUTPUT_ROOT / "passive_w_activation_summary.json"
    for path in (
        manifest_path, summary_path, index_path, w_summary_path,
        DELAYED_JOB_PLAN, DELAYED_SEED_REGISTRY,
    ):
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"full-stat validation input missing/empty: {path}")
    plan_rows = read_csv(DELAYED_JOB_PLAN)
    seed_rows = read_csv(DELAYED_SEED_REGISTRY)
    index_rows = read_csv(index_path)
    if len(plan_rows) != 8 or len(seed_rows) != 8 or len(index_rows) != 8:
        raise RuntimeError("full-stat delayed plan/seed/index is not 8/8/8")
    if {row["family"] for row in plan_rows} != set(FAMILIES):
        raise RuntimeError("full-stat delayed plan family closure differs")
    if len({int(row["seed"]) for row in plan_rows}) != 8:
        raise RuntimeError("full-stat delayed plan seeds are not unique")
    seeds_from_registry = {row["family"]: int(row["seed"]) for row in seed_rows}
    plan_by_family = {row["family"]: row for row in plan_rows}
    index_by_family = {row["incident_family"]: row for row in index_rows}
    if set(index_by_family) != set(FAMILIES) or set(seeds_from_registry) != set(FAMILIES):
        raise RuntimeError("full-stat delayed index/seed family closure differs")

    source_records: list[dict[str, Any]] = []
    for family in FAMILIES:
        plan = plan_by_family[family]
        index = index_by_family[family]
        seed = int(plan["seed"])
        if seed != seeds_from_registry[family] or seed != int(index["transport_seed"]):
            raise RuntimeError(f"full-stat delayed seed binding differs: {family}")
        if int(plan["registered_events"]) != FULLSTAT_DELAYED_EVENTS:
            raise RuntimeError(f"full-stat delayed registered events differ: {family}")
        if plan["plan1_83334_role"] != PLAN1_DELAYED_ROLE:
            raise RuntimeError(f"Plan-1 delayed role differs: {family}")
        if plan["incremental_merge_allowed"].lower() != "false":
            raise RuntimeError(f"incremental delayed merge enabled: {family}")
        card = Path(plan["source_path"])
        if card.resolve() != delayed_source_path(family).resolve() or not card.is_file():
            raise RuntimeError(f"full-stat delayed card missing/wrong path: {family}")
        text = card.read_text(encoding="utf-8", errors="strict")
        for token in (
            f"Geometry {SF3_SETUP}", f"Seed {seed}",
            f"DecayRun.FileName {delayed_active_prefix(plan['job_id'])}",
            f"DecayRun.Triggers {FULLSTAT_DELAYED_EVENTS}",
        ):
            if text.count(token) != 1:
                raise RuntimeError(f"full-stat delayed source binding differs for {family}: {token}")
        if "DecayRun.Triggers 83334" in text or "DecayRun.Triggers 166666" in text:
            raise RuntimeError(f"Plan-1/incremental trigger count leaked into full-stat source: {family}")
        digest = sha256(card)
        if digest != index["source_sha256"]:
            raise RuntimeError(f"full-stat delayed source/index digest differs: {family}")
        disposition = plan["execution_disposition"]
        activity = float(index["transported_ground_activity_Bq"])
        directives = [line for line in text.splitlines() if line.startswith("DecayRun.Source ")]
        if disposition == POSITIVE_DISPOSITION:
            if plan["transport_eligible"].lower() != "true":
                raise RuntimeError(f"positive full-stat delayed row is not transport eligible: {family}")
            if int(plan["events"]) != FULLSTAT_DELAYED_EVENTS or int(plan["actual_transport_events"]) != FULLSTAT_DELAYED_EVENTS:
                raise RuntimeError(f"positive full-stat delayed event count differs: {family}")
            if activity <= 0.0 or len(directives) != base.TRANSPORT_POSITION_BLOCKS:
                raise RuntimeError(f"positive full-stat delayed source/activity differs: {family}")
            if int(index["original_blocks"]) != base.ORIGINAL_POSITION_BLOCKS or int(index["transport_blocks"]) != base.TRANSPORT_POSITION_BLOCKS:
                raise RuntimeError(f"positive full-stat delayed 50k/10k mixture differs: {family}")
            upper_rate = None
            upper_a15 = None
        elif disposition == ZERO_DISPOSITION:
            if plan["transport_eligible"].lower() != "false":
                raise RuntimeError(f"zero full-stat delayed row is transport eligible: {family}")
            if int(plan["events"]) != 0 or int(plan["actual_transport_events"]) != 0:
                raise RuntimeError(f"zero full-stat delayed actual events are not zero: {family}")
            if activity != 0.0 or directives:
                raise RuntimeError(f"zero full-stat delayed source/activity differs: {family}")
            sum_tt = float(index["buildup_sum_TT_s"])
            upper_rate = float(index["transported_ground_rate_upper95_s-1"])
            upper_a15 = float(index["transported_ground_A15_upper95_Bq_conservative"])
            expected_upper = base.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt
            if not math.isclose(upper_rate, expected_upper, rel_tol=2.0e-15, abs_tol=1.0e-18):
                raise RuntimeError(f"zero full-stat delayed finite upper differs: {family}")
            if not math.isclose(upper_a15, upper_rate, rel_tol=0.0, abs_tol=1.0e-18):
                raise RuntimeError(f"zero full-stat delayed conservative A15 upper differs: {family}")
            if index["zero_A15_upper_provenance"] != base.ZERO_A15_UPPER_PROVENANCE:
                raise RuntimeError(f"zero full-stat delayed upper provenance differs: {family}")
        else:
            raise RuntimeError(f"unknown full-stat delayed disposition: {family}/{disposition}")
        source_records.append({
            "family": family,
            "job_id": plan["job_id"],
            "path": str(card.resolve()),
            "sha256": digest,
            "seed": seed,
            "registered_events": FULLSTAT_DELAYED_EVENTS,
            "actual_transport_events": int(plan["actual_transport_events"]),
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": activity,
            "transported_ground_rate_upper95_s-1": upper_rate,
            "transported_ground_A15_upper95_Bq_conservative": upper_a15,
            "original_blocks": int(index["original_blocks"]),
            "transport_blocks": int(index["transport_blocks"]),
            "position_stride": int(index["position_stride"]),
        })

    w_summary = load_small_json(w_summary_path, "full-stat passive-W summary")
    if (
        w_summary.get("status") != "PASS__EXACT_THREE_SF3_W_VOLUMES_DIAGNOSTIC_AND_PASSIVE"
        or w_summary.get("exact_volume_whitelist") != list(PASSIVE_W_VOLUMES)
        or w_summary.get("passive_w_never_veto") is not True
        or int(w_summary.get("bgo_veto_members", -1)) != 0
        or int(w_summary.get("plastic_veto_members", -1)) != 0
    ):
        raise RuntimeError("full-stat exact passive-W diagnostic gate differs")
    validation = {
        "schema_version": 1,
        "status": FULLSTAT_VALIDATION_STATUS,
        "created_at": utc_now(),
        "profile_id": FULLSTAT_DELAYED_NAMESPACE,
        "geometry": "SF3",
        "hard_gates": prerequisite["hard_gates"],
        "central_gate": prerequisite["authorities"]["central_mission_gate"],
        "topup_receipt_gate": prerequisite["authorities"]["topup_receipt_gate"],
        "plan1_receipt_gate": prerequisite["authorities"]["plan1_receipt_gate"],
        "combined_buildup_jobs": 23,
        "combined_buildup_histories": 3_046_468,
        "registered_delayed_source_cells": 8,
        "fresh_delayed_transport_jobs": sum(row["execution_disposition"] == POSITIVE_DISPOSITION for row in source_records),
        "zero_A15_skipped_jobs": sum(row["execution_disposition"] == ZERO_DISPOSITION for row in source_records),
        "registered_events_per_family": FULLSTAT_DELAYED_EVENTS,
        "actual_transport_events_total": sum(int(row["actual_transport_events"]) for row in source_records),
        "manifest": small_record(manifest_path),
        "day15_summary": small_record(summary_path),
        "delayed_source_index": small_record(index_path),
        "delayed_job_plan": small_record(DELAYED_JOB_PLAN),
        "delayed_seed_registry": small_record(DELAYED_SEED_REGISTRY),
        "source_cards": source_records,
        "plan1_delayed_consumed": False,
        "plan1_83334_role": PLAN1_DELAYED_ROLE,
        "incremental_83334_plus_166666_merge_allowed": False,
        "passive_w": w_summary,
        "sim_digest_policy": "OMITTED_BY_CONTRACT__ONE_SEMANTIC_RPIP_PASS_ONLY",
        "transport_launched": False,
        "authority_boundary": "FULLSTAT_DELAYED_LAUNCH_GATE_ONLY__NOT_TRANSPORT_RESPONSE_MISSION_OR_PROMOTION_AUTHORITY",
    }
    write_once_json(ACTIVATION_VALIDATION, validation)
    return validation


def prepare(mission_path: Path = MISSION_SUMMARY) -> dict[str, Any]:
    prerequisite = prerequisite_status(mission_path)
    if prerequisite["already_prepared"] and prerequisite["ready"]:
        manifest = load_small_json(OUTPUT_ROOT / "manifest.json", "full-stat activation manifest")
        if not ACTIVATION_VALIDATION.is_file():
            publish_activation_validation(manifest, prerequisite)
        return manifest
    if not prerequisite["ready"]:
        raise RuntimeError(json.dumps(prerequisite, indent=2, ensure_ascii=False))
    if prerequisite["hard_gates"] != {
        "central_mission_topup_required_true": True,
        "all_28_topup_background_canonical_PASS": True,
    }:
        raise RuntimeError("full-stat activation double hard gate is not satisfied")

    plan1_rows = plan1_background_rows()
    topup_rows = topup_background_rows()
    buildup_jobs = combined_buildup_rows(plan1_rows, topup_rows)
    occupied, seed_authority = occupied_for_fullstat_delayed(plan1_rows, topup_rows)
    seeds = derive_fullstat_delayed_seeds(occupied)
    if set(seeds.values()) & {int(row["seed"]) for row in plan1_rows + topup_rows}:
        raise RuntimeError("fresh full-stat delayed seed collides with Plan-1/top-up plan")

    work = PACKAGE_ROOT / f".sf3_fullstat_activation_work_{os.getpid()}"
    output_is_empty_directory = OUTPUT_ROOT.is_dir() and not any(OUTPUT_ROOT.iterdir())
    if work.exists() or (OUTPUT_ROOT.exists() and not output_is_empty_directory):
        raise RuntimeError(
            f"write-once full-stat activation target/work exists: "
            f"{OUTPUT_ROOT if OUTPUT_ROOT.exists() else work}"
        )
    staging_output = work / "02_activation"
    staging_cards = work / "fullstat_delayed_source_cards"
    work.mkdir(parents=True, exist_ok=False)
    staging_output.mkdir(parents=True, exist_ok=False)
    try:
        built = build_prepare_payload(
            staging_output, staging_cards, buildup_jobs, seeds,
            prerequisite, seed_authority,
        )
        plan_text = csv_text(built["delayed_plan"], DELAYED_PLAN_FIELDS)
        seed_fields = tuple(built["seed_rows"][0])
        seed_text = csv_text(built["seed_rows"], seed_fields)
        write_once_text(DELAYED_JOB_PLAN, plan_text)
        write_once_text(DELAYED_SEED_REGISTRY, seed_text)
        for family in FAMILIES:
            write_once_text(delayed_source_path(family), built["card_payloads"][family])
        OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
        if output_is_empty_directory:
            OUTPUT_ROOT.rmdir()
        os.replace(staging_output, OUTPUT_ROOT)
        manifest = load_small_json(OUTPUT_ROOT / "manifest.json", "full-stat activation manifest")
        publish_activation_validation(manifest, prerequisite)
        return manifest
    finally:
        if work.exists():
            shutil.rmtree(work)


def synthetic_combined_buildup_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan1: list[dict[str, Any]] = []
    increments: list[dict[str, Any]] = []
    seed = 1000
    for family in FAMILIES:
        for shard, events in enumerate(SHARDS[("buildup", family)], 1):
            seed += 1
            plan1.append({
                "job_id": f"synthetic_plan1_buildup_{family}_{shard}",
                "mode": "buildup", "family": family, "events": events,
                "seed": seed, "source_namespace": "PLAN1_CANONICAL_PASS",
            })
        for shard, events in enumerate(FULLSTAT_INCREMENT_SHARDS[("buildup", family)], 1):
            seed += 1
            increments.append({
                "job_id": f"synthetic_topup_buildup_{family}_{shard}",
                "mode": "buildup", "family": family, "events": events,
                "seed": seed, "source_namespace": "FULLSTAT_TOPUP_CANONICAL_PASS",
            })
    return plan1, increments


def self_test() -> dict[str, Any]:
    """Pure synthetic contract test: no production file or SIM access."""
    valid_gate = {
        "status": "PASS__SYNTHETIC_MISSION",
        "fullstat_gate": {
            "metric": "F3_SF3_over_SE3_full_envelope",
            "observed_central_ratio": 0.75,
            "operator": "<=",
            "threshold": 0.75,
            "topup_required": True,
            "decision": "TOPUP_TO_S3D_FULL_STAT_REQUIRED",
            "proxy_controls_gate": False,
            "proxy_ratio_reported_only": 9.0,
        },
    }
    gate = validate_mission_gate_payload(valid_gate)
    if gate["central_R_F3"] != 0.75 or gate["topup_required"] is not True:
        raise AssertionError("synthetic central gate acceptance failed")
    rejected = 0
    for mutate in ("ratio", "topup", "proxy"):
        payload = json.loads(json.dumps(valid_gate))
        if mutate == "ratio":
            payload["fullstat_gate"]["observed_central_ratio"] = 0.7500000001
        elif mutate == "topup":
            payload["fullstat_gate"]["topup_required"] = False
        else:
            payload["fullstat_gate"]["proxy_controls_gate"] = True
        try:
            validate_mission_gate_payload(payload)
        except RuntimeError:
            rejected += 1
    if rejected != 3:
        raise AssertionError("synthetic central-gate fail-closed cases differ")

    plan1, increments = synthetic_combined_buildup_rows()
    combined = combined_buildup_rows(plan1, increments)
    if len(plan1) != 10 or len(increments) != 13 or len(combined) != 23:
        raise AssertionError("synthetic 10+13=23 buildup job closure failed")
    if sum(int(row["events"]) for row in combined) != 3_046_468:
        raise AssertionError("synthetic full-stat buildup history total failed")

    parsed_positive = base.parse_dat_lines(
        ["TT 10", "VN TEST_VOL", "RP 11024 0 2", "EN"], "synthetic-positive"
    )
    parsed_zero = base.parse_dat_lines(["TT 20", "EN"], "synthetic-zero")
    production, cell = aggregate_family_production("p", [
        {"job": {"job_id": "a", "events": 1}, "parsed_dat": parsed_positive},
        {"job": {"job_id": "b", "events": 1}, "parsed_dat": parsed_zero},
    ])
    if (
        cell["sum_TT_s"] != 30.0
        or cell["sum_RP"] != 2.0
        or cell["zero_RP_files"] != 1
        or not math.isclose(production[0]["production_rate_s-1"], 2.0 / 30.0)
    ):
        raise AssertionError("synthetic all-TT including zero-RP aggregation failed")

    occupied = {int(row["seed"]) for row in combined} | set(range(1, 100))
    seeds = derive_fullstat_delayed_seeds(occupied)
    if set(seeds.values()) & occupied or len(set(seeds.values())) != 8:
        raise AssertionError("synthetic fresh delayed seed disjointness failed")
    decisions = {
        family: {
            "source_status": (
                "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY"
                if family == FAMILIES[-1]
                else "PASS__SF3_FULLSTAT_STRIDE5_M10000_DELAYED_SOURCE_READY"
            ),
            "execution_disposition": ZERO_DISPOSITION if family == FAMILIES[-1] else POSITIVE_DISPOSITION,
        }
        for family in FAMILIES
    }
    delayed_plan = build_delayed_plan(seeds, decisions)
    positive = [row for row in delayed_plan if row["execution_disposition"] == POSITIVE_DISPOSITION]
    zero = [row for row in delayed_plan if row["execution_disposition"] == ZERO_DISPOSITION]
    if len(positive) != 7 or len(zero) != 1:
        raise AssertionError("synthetic positive/zero delayed plan split failed")
    if any(int(row["events"]) != 250_000 for row in positive):
        raise AssertionError("synthetic positive delayed plan is not fresh 250k")
    if int(zero[0]["events"]) != 0 or int(zero[0]["registered_events"]) != 250_000:
        raise AssertionError("synthetic zero delayed skip/registration failed")
    if any(
        row["plan1_83334_role"] != PLAN1_DELAYED_ROLE
        or row["incremental_merge_allowed"] != "false"
        for row in delayed_plan
    ):
        raise AssertionError("synthetic Plan-1 delayed no-consume/no-merge policy failed")

    sampled = [{
        "sample_index": index,
        "volume": "TEST_VOL",
        "ZA": 11024,
        "excitation_keV": 0.0,
        "x_cm": 1.0,
        "y_cm": 2.0,
        "z_cm": 3.0,
    } for index in range(base.ORIGINAL_POSITION_BLOCKS)]
    render_job = {"job_id": "sf3_fullstat_delayed_p", "seed": seeds["p"]}
    source, closure = render_fullstat_delayed_source(render_job, sampled, 1.0)
    if (
        closure["original_blocks"] != 50_000
        or closure["transport_blocks"] != 10_000
        or closure["actual_transport_events"] != 250_000
        or source.count("DecayRun.Source ") != 10_000
        or "DecayRun.Triggers 250000" not in source
        or "DecayRun.Triggers 83334" in source
        or "DecayRun.Triggers 166666" in source
    ):
        raise AssertionError("synthetic fresh 250k/50k-to-10k source contract failed")
    zero_source, zero_closure = render_fullstat_delayed_source(render_job, [], 0.0)
    if (
        zero_closure["execution_disposition"] != ZERO_DISPOSITION
        or zero_closure["actual_transport_events"] != 0
        or any(line.startswith("DecayRun.Source ") for line in zero_source.splitlines())
    ):
        raise AssertionError("synthetic zero-A15 source skip failed")
    finite_upper = base.ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / 30.0
    if not math.isfinite(finite_upper) or finite_upper <= 0.0:
        raise AssertionError("synthetic zero-A15 finite upper failed")
    if any(base.material_category(volume) != "passive_w_or_collimator" for volume in PASSIVE_W_VOLUMES):
        raise AssertionError("exact three SF3 W volumes are not passive diagnostics")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_ACTIVATION_BUILDER_PURE_SYNTHETIC_SELF_TEST",
        "checks": [
            "central_ratio_0p75_topup_true_gate_and_ratio_topup_proxy_fail_closed",
            "combined_10_plan1_plus_13_topup_equals_23_buildup_jobs",
            "combined_buildup_histories_equal_3046468_and_each_family_S3d_full_target",
            "all_DAT_TT_including_zero_RP_enters_family_denominator",
            "eight_fresh_fullstat_delayed_seeds_disjoint_from_prior_sets",
            "positive_families_are_fresh_complete_250000_and_zero_family_is_exact_skip",
            "50k_actual_position_mixture_stride5_to_10k_with_flux_closure",
            "Plan1_83334_and_default_83334_plus_166666_merge_are_not_consumed",
            "zero_A15_has_no_source_directive_and_retains_finite_upper_policy",
            "exact_three_SF3_W_volumes_are_passive_diagnostics_never_veto",
        ],
        "synthetic_combined_buildup_jobs": len(combined),
        "synthetic_combined_buildup_histories": sum(int(row["events"]) for row in combined),
        "synthetic_delayed_rows": len(delayed_plan),
        "synthetic_positive_250k_rows": len(positive),
        "synthetic_zero_skip_rows": len(zero),
        "synthetic_seed_collisions": [],
        "production_artifacts_accessed": False,
        "SIM_opened": False,
        "SIM_statted": False,
        "SIM_hashed": False,
        "files_written": False,
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--status", action="store_true", help="alias of --check-prerequisites")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--prepare", action="store_true")
    parser.add_argument("--mission-summary", type=Path, default=MISSION_SUMMARY)
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.prepare:
            result = prepare(args.mission_summary)
        else:
            result = prerequisite_status(args.mission_summary)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
        if (args.check_prerequisites or args.status or not any((args.self_test, args.prepare))) and not result.get("ready", False):
            return 2 if str(result.get("status", "")).startswith("WAITING__") else 1
        return 0
    except Exception as exc:
        print(json.dumps({
            "schema_version": 1,
            "status": "FAIL__SF3_FULLSTAT_ACTIVATION_BUILDER",
            "error": str(exc),
        }, indent=2, sort_keys=True, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
