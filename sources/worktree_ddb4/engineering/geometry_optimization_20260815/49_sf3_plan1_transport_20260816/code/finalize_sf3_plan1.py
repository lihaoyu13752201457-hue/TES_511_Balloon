#!/usr/bin/env python3
"""Finalize the SF3 Plan-1 screen from compact, write-once authorities.

The finalizer is deliberately incapable of launching transport or full-stat
top-up.  It reads the canonical 30-row plan, compact receipts/audits and
stage-01--06 JSON/CSV products.  A SIM path is retained as receipt metadata
only: this program never opens, stats, discovers, decompresses or hashes a SIM
payload.

``--check-prerequisites`` is read-only.  ``--build`` atomically publishes the
write-once ``outputs/07_final_audit`` directory after every contract closes.
That Plan-1 closure is the authority consumed later by the conditional
full-stat adapter when, and only when, the central mission ratio is <= 0.75.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve()
DEFAULT_PACKAGE_ROOT = HERE.parent.parent
DEFAULT_CONFIG = DEFAULT_PACKAGE_ROOT / "analysis_inputs.json"

PROFILE_ID = "SF3_PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN"
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
PASSIVE_W_VOLUMES = (
    "SF3_W_NearField_FrontWindowPlate_2p9mm",
    "SF3_W_NearField_SideSleeve_2p9mm",
    "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
)
EXPECTED_PLAN_ROWS = 30
EXPECTED_BACKGROUND_JOBS = 21
EXPECTED_INSTANT_JOBS = 11
EXPECTED_BUILDUP_JOBS = 10
EXPECTED_INSTANT_HISTORIES = 1_280_693
EXPECTED_BUILDUP_HISTORIES = 1_015_492
EXPECTED_DELAYED_REGISTERED = 8
EXPECTED_DELAYED_EVENTS = 83_334
EXPECTED_SIGNAL_EVENTS = 37_194
EXPECTED_CANARY = "sf3_instant_gamma_shard0001"
EXPECTED_CANARY_EVENTS = 267_312
EXPECTED_MISSION_NODES = 81
EXPECTED_MISSION_DAYS = 20.0
EXPECTED_FOLLOWUP_RESOURCE_SESSIONS = {
    "build_prompt", "transport_delayed", "analyze_delayed",
    "transport_signal", "build_common_response",
}
FULLSTAT_GATE = 0.75
MEMORY_FLOOR_BYTES = 1_610_612_736
SWAP_FLOOR_BYTES = 8 * 1024**3
DYNAMIC_RESERVE_BYTES = 8 * 1024**3
MAX_SMALL_BYTES = 64 * 1024**2
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")

EXPECTED_STAGE_STATUS = {
    "stage00": "PASS",
    "stage01": "PASS__SF3_PLAN1_PROMPT_COMPLETE",
    "stage02": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
    "stage03": "PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
    "stage04": "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
    "stage05": "PASS__SF3_VS_FROZEN_SE3_DAY15_AND_FULL_ENVELOPE_COMPARISON",
    "stage06": "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE",
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


def reject_sim_payload_path(path: Path) -> None:
    """Reject before any filesystem query can be made on a SIM path."""
    lower = os.fspath(path).lower()
    if lower.endswith(SIM_SUFFIXES):
        raise RuntimeError(f"SIM payload access is forbidden in finalizer: {path}")


def sha256_small(path: Path) -> str:
    reject_sim_payload_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact-authority size ({size}): {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def small_record(path: Path) -> dict[str, Any]:
    reject_sim_payload_path(path)
    return {
        "path": norm(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_small(path),
    }


def load_small_json(path: Path) -> dict[str, Any]:
    reject_sim_payload_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact JSON size ({size}): {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_nonfinite)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_small_csv(path: Path) -> list[dict[str, str]]:
    reject_sim_payload_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact CSV size ({size}): {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader)


def load_small_jsonl(path: Path) -> list[dict[str, Any]]:
    reject_sim_payload_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid compact JSONL size ({size}): {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line, parse_constant=reject_nonfinite)
            if not isinstance(value, dict):
                raise RuntimeError(f"JSONL row {line_number} is not an object: {path}")
            rows.append(value)
    return rows


def close(
    actual: Any,
    expected: Any,
    *,
    rel: float = 2.0e-11,
    absolute: float = 2.0e-12,
) -> bool:
    try:
        return math.isclose(
            float(actual), float(expected), rel_tol=rel, abs_tol=absolute
        )
    except (TypeError, ValueError):
        return False


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def has_four_three_four_quota_cycle(values: Any) -> bool:
    """Accept one or more safe throttle cycles, ending restored at four cores."""
    if not isinstance(values, list) or not values:
        return False
    try:
        cores = [int(value) for value in values]
    except (TypeError, ValueError):
        return False
    return (
        cores[0] == 4
        and 3 in cores
        and cores[-1] == 4
        and set(cores) <= {3, 4}
    )


def valid_guard_session_summary(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("allowed_quota_core_interval") == [3, 4]
        and value.get("all_sessions_closed") is True
        and value.get("all_quotas_within_3_to_4_cores") is True
        and value.get("all_throttled_sessions_restored_to_four") is True
        and value.get("all_sampled_hard_floors_pass") is True
        and value.get("safe_all_four_core_session_is_PASS") is True
        and value.get("artificial_throttle_required") is False
    )


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def json(self, label: str, path: Path) -> dict[str, Any] | None:
        reject_sim_payload_path(path)
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
        reject_sim_payload_path(path)
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

    def jsonl(self, label: str, path: Path) -> list[dict[str, Any]] | None:
        reject_sim_payload_path(path)
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_jsonl(path)
            self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None


def cast_plan(rows: Sequence[dict[str, str]], check: Checker) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        try:
            item: dict[str, Any] = dict(row)
            for key in (
                "ordinal", "shard", "events", "s3d_histories",
                "target_histories", "seed", "estimated_bytes",
            ):
                item[key] = int(row[key])
            item["paired_seed_exception"] = parse_bool(row["paired_seed_exception"])
            item["production_canary"] = parse_bool(row["production_canary"])
            output.append(item)
        except Exception as exc:
            check.errors.append(f"job plan row {index} invalid: {exc}")
    return output


def validate_plan(plan: Sequence[dict[str, Any]], config: dict[str, Any], check: Checker) -> None:
    check.expect(len(plan) == EXPECTED_PLAN_ROWS, f"job plan rows {len(plan)} != 30")
    check.expect(
        [row.get("ordinal") for row in plan] == list(range(1, EXPECTED_PLAN_ROWS + 1)),
        "job plan ordinals are not exactly 1..30",
    )
    ids = [str(row.get("job_id")) for row in plan]
    check.expect(len(ids) == len(set(ids)), "job plan contains duplicate job IDs")
    check.expect(
        all(row.get("geometry") == "SF3" for row in plan),
        "job plan is not strictly SF3-only",
    )
    setup = norm(config.get("geometry", {}).get("sf3_setup", ""))
    check.expect(
        all(norm(str(row.get("setup_path", ""))) == setup for row in plan),
        "job plan setup paths do not all bind the SF3 authority",
    )
    seeds = [int(row["seed"]) for row in plan if "seed" in row]
    check.expect(len(seeds) == len(set(seeds)), "job plan seeds are not fresh and unique")
    check.expect(
        all(not row.get("paired_seed_exception") for row in plan),
        "SF3 plan unexpectedly contains a paired-seed exception",
    )

    background = [row for row in plan if row.get("stage") == "background"]
    instant = [row for row in background if row.get("mode") == "instant"]
    buildup = [row for row in background if row.get("mode") == "buildup"]
    check.expect(len(background) == EXPECTED_BACKGROUND_JOBS, "background jobs != 21")
    check.expect(len(instant) == EXPECTED_INSTANT_JOBS, "instant jobs != 11")
    check.expect(len(buildup) == EXPECTED_BUILDUP_JOBS, "buildup jobs != 10")
    check.expect(
        sum(int(row["events"]) for row in instant) == EXPECTED_INSTANT_HISTORIES,
        "instant Plan-1 history total differs",
    )
    check.expect(
        sum(int(row["events"]) for row in buildup) == EXPECTED_BUILDUP_HISTORIES,
        "buildup Plan-1 history total differs",
    )
    for mode in ("instant", "buildup"):
        for family in FAMILIES:
            cell = [
                row for row in background
                if row.get("mode") == mode and row.get("family") == family
            ]
            check.expect(bool(cell), f"missing background cell {mode}/{family}")
            if not cell:
                continue
            s3d_values = {int(row["s3d_histories"]) for row in cell}
            targets = {int(row["target_histories"]) for row in cell}
            check.expect(len(s3d_values) == 1, f"S3d authority drift {mode}/{family}")
            check.expect(len(targets) == 1, f"target drift {mode}/{family}")
            if len(s3d_values) != 1 or len(targets) != 1:
                continue
            target = next(iter(targets))
            s3d = next(iter(s3d_values))
            check.expect(target == math.ceil(s3d / 3), f"ceil(1/3) mismatch {mode}/{family}")
            check.expect(
                sum(int(row["events"]) for row in cell) == target,
                f"shard history closure mismatch {mode}/{family}",
            )
            if target <= 100_000:
                check.expect(len(cell) == 1, f"target <=100k was split {mode}/{family}")
            else:
                check.expect(
                    all(int(row["events"]) >= 100_000 for row in cell),
                    f"target >100k has sub-100k shard {mode}/{family}",
                )

    delayed = [row for row in plan if row.get("stage") == "delayed"]
    check.expect(len(delayed) == EXPECTED_DELAYED_REGISTERED, "delayed rows != 8")
    check.expect(
        {row.get("family") for row in delayed} == set(FAMILIES),
        "delayed registered-family closure differs",
    )
    check.expect(
        all(
            row.get("mode") == "delayed"
            and int(row.get("events", -1)) == EXPECTED_DELAYED_EVENTS
            and int(row.get("s3d_histories", -1)) == 250_000
            and int(row.get("target_histories", -1)) == EXPECTED_DELAYED_EVENTS
            for row in delayed
        ),
        "delayed 250000->83334 registered-cell contract differs",
    )
    signal = [row for row in plan if row.get("stage") == "signal"]
    check.expect(len(signal) == 1, "fresh signal rows != 1")
    if len(signal) == 1:
        row = signal[0]
        check.expect(row.get("job_id") == "signal_full_envelope_sf3", "signal job ID differs")
        check.expect(row.get("family") == "focused_gamma", "signal family differs")
        check.expect(int(row.get("events", -1)) == EXPECTED_SIGNAL_EVENTS, "signal trials != 37194")
    canaries = [row for row in background if row.get("production_canary")]
    check.expect(
        len(canaries) == 1
        and canaries[0].get("job_id") == EXPECTED_CANARY
        and int(canaries[0].get("events", -1)) == EXPECTED_CANARY_EVENTS,
        "counted gamma 267312 production canary registration differs",
    )


def validate_seed_registry(
    rows: Sequence[dict[str, str]], plan: Sequence[dict[str, Any]], check: Checker
) -> None:
    by_id = {row.get("job_id", ""): row for row in rows}
    check.expect(len(rows) == EXPECTED_PLAN_ROWS, "seed registry rows != 30")
    check.expect(
        set(by_id) == {str(row["job_id"]) for row in plan},
        "seed registry/job plan key closure differs",
    )
    for job in plan:
        row = by_id.get(str(job["job_id"]))
        if row is None:
            continue
        try:
            check.expect(int(row["seed"]) == int(job["seed"]), f"seed mismatch {job['job_id']}")
        except Exception:
            check.errors.append(f"non-integer seed registry value {job['job_id']}")
        check.expect(
            row.get("seed_identity") == job.get("seed_identity"),
            f"seed identity mismatch {job['job_id']}",
        )
        check.expect(
            str(row.get("collision_with_prior", "")).lower() == "false",
            f"registered seed collision {job['job_id']}",
        )
        check.expect(
            row.get("namespace") == PROFILE_ID,
            f"seed namespace mismatch {job['job_id']}",
        )


def stage_files(config: dict[str, Any]) -> dict[str, dict[str, Path]]:
    outputs = config["outputs"]
    roots = {
        key: Path(outputs[f"stage_{index:02d}"])
        for index, key in enumerate(
            ("stage00", "stage01", "stage02", "stage03", "stage04", "stage05", "stage06")
        )
    }
    return {
        "stage00": {"summary": roots["stage00"] / "input_audit.json"},
        "stage01": {
            "summary": roots["stage01"] / "summary.json",
            "manifest": roots["stage01"] / "manifest.json",
            "w": roots["stage01"] / "prompt_w_diagnostics.csv",
        },
        "stage02": {
            "summary": roots["stage02"] / "day15_summary.json",
            "manifest": roots["stage02"] / "manifest.json",
            "inventory": roots["stage02"] / "day15_inventory.csv",
            "source_index": roots["stage02"] / "delayed_source_index.csv",
        },
        "stage03": {
            "summary": roots["stage03"] / "summary.json",
            "manifest": roots["stage03"] / "manifest.json",
            "coverage": roots["stage03"] / "delayed_cell_coverage.csv",
            "w": roots["stage03"] / "delayed_w_diagnostics.csv",
        },
        "stage04": {
            "summary": roots["stage04"] / "summary.json",
            "manifest": roots["stage04"] / "manifest.json",
            "cutflow": roots["stage04"] / "common_cutflow.csv",
            "signal": roots["stage04"] / "signal_acceptance_effective_area.csv",
            "w": roots["stage04"] / "passive_w_diagnostics.csv",
            "zero": roots["stage04"] / "delayed_zero_A15_provenance.csv",
        },
        "stage05": {
            "summary": roots["stage05"] / "summary.json",
            "manifest": roots["stage05"] / "manifest.json",
        },
        "stage06": {
            "summary": roots["stage06"] / "summary.json",
            "timeline": roots["stage06"] / "mission_timeline.csv",
            "comparison": roots["stage06"] / "se3_o8_vs_sf3_mission.csv",
        },
    }


def validate_w_contract(config: dict[str, Any], check: Checker) -> dict[str, Any]:
    geometry = config.get("geometry", {})
    passive = tuple(str(value) for value in geometry.get("passive_w_volumes", []))
    active = tuple(str(value) for value in geometry.get("active_veto_volumes", []))
    shield = tuple(str(value) for value in geometry.get("shield_veto_volumes", []))
    plastic = tuple(str(value) for value in geometry.get("plastic_veto_volumes", []))
    check.expect(passive == PASSIVE_W_VOLUMES, "passive-W three-volume authority differs")
    check.expect(geometry.get("passive_w_never_active_veto") is True, "passive-W never-veto flag is not true")
    check.expect(len(active) == 6, "active veto does not contain exactly six volumes")
    check.expect(set(active) == set(shield) | set(plastic), "active veto is not exactly 3 BGO + 3 plastic")
    check.expect(len(shield) == 3 and len(plastic) == 3, "BGO/plastic veto cardinality differs")
    check.expect(not (set(passive) & set(active)), "passive W appears in the active veto")
    check.expect(geometry.get("apply_plastic_veto") is True, "plastic veto is not enabled")
    return {
        "passive_w_volumes": list(passive),
        "active_veto_volumes": list(active),
        "disjoint": not bool(set(passive) & set(active)),
        "role": "PASSIVE_DIAGNOSTIC_ONLY__NEVER_BGO_OR_PLASTIC_VETO",
    }


def validate_geometry_authorities(
    stage00: dict[str, Any] | None, config: dict[str, Any], check: Checker
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if stage00 is None:
        return result
    check.expect(stage00.get("status") == "PASS", "stage00 input audit is not PASS")
    small = stage00.get("small_authorities") or {}
    geometry_records = small.get("sf3_geometry_authorities") or {}
    configured = config.get("geometry", {}).get("sf3_geometry_authorities") or {}
    expected_names = {
        "static": "sf3_geometry_validation.json",
        "mesh": "sf3_mesh_clearance_prefilter.json",
        "native": "sf3_native_navigation_audit.json",
        "overlap": "sf3_overlap_validation.json",
    }
    for role, name in expected_names.items():
        record = geometry_records.get(name)
        path_value = configured.get(role)
        check.expect(isinstance(record, dict), f"stage00 missing geometry authority {name}")
        check.expect(bool(path_value), f"config missing geometry authority role {role}")
        if not isinstance(record, dict) or not path_value:
            continue
        path = Path(str(path_value))
        payload = check.json(f"geometry_{role}", path)
        if payload is None:
            continue
        digest = check.authorities[f"geometry_{role}"]["sha256"]
        check.expect(norm(path) == norm(str(record.get("path", ""))), f"geometry path drift {role}")
        check.expect(digest == record.get("sha256"), f"geometry digest drift {role}")
        check.expect(payload.get("status") == record.get("status"), f"geometry status drift {role}")
        result[role] = {
            "path": norm(path), "sha256": digest, "status": payload.get("status")
        }
        if role == "native":
            check.expect(payload.get("rows") == EXPECTED_SIGNAL_EVENTS, "native frozen-ray count != 37194")
            check.expect(nested(payload, "added_W_focused_chord", "zero_rays") == EXPECTED_SIGNAL_EVENTS, "focused added-W zero-chord count differs")
            check.expect(nested(payload, "added_W_focused_chord", "sf3_minus_se3_cm", "max") == 0, "focused rays acquire an added-W chord")
            witnesses = nested(payload, "W_presence_witnesses", "delta_W_cm") or []
            check.expect(len(witnesses) == 3, "native W witness count differs")
            check.expect(all(close(value, 0.29, rel=0.0, absolute=2.0e-6) for value in witnesses), "native W witness thickness differs from 0.29 cm")

    setup_record = small.get("sf3_setup") or {}
    setup = Path(str(config.get("geometry", {}).get("sf3_setup", "")))
    if str(setup):
        if not setup.is_file():
            check.missing.append(f"sf3_setup:{norm(setup)}")
        else:
            try:
                observed = small_record(setup)
                check.authorities["sf3_setup"] = observed
                check.expect(observed["sha256"] == setup_record.get("sha256"), "SF3 setup digest drift")
            except Exception as exc:
                check.errors.append(f"SF3 setup invalid: {exc}")
    source_contract = nested(config, "source", "contract_path")
    source_record = small.get("source_contract") or {}
    if source_contract:
        path = Path(str(source_contract))
        if not path.is_file():
            check.missing.append(f"source_contract:{norm(path)}")
        else:
            try:
                observed = small_record(path)
                check.authorities["source_contract"] = observed
                check.expect(observed["sha256"] == source_record.get("sha256"), "corrected-keV source contract digest drift")
            except Exception as exc:
                check.errors.append(f"source contract invalid: {exc}")
    return result


def validate_source_index(
    rows: Sequence[dict[str, str]],
    plan: Sequence[dict[str, Any]],
    check: Checker,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    delayed_plan = {
        str(row["family"]): row for row in plan if row.get("stage") == "delayed"
    }
    selected = [row for row in rows if row.get("geometry") == "SF3"]
    check.expect(len(selected) == EXPECTED_DELAYED_REGISTERED, "stage02 delayed source index rows != 8")
    check.expect(
        {row.get("incident_family") for row in selected} == set(FAMILIES),
        "stage02 delayed source-index family closure differs",
    )
    dispositions: dict[str, str] = {}
    records: dict[str, dict[str, Any]] = {}
    for row in selected:
        family = str(row.get("incident_family"))
        disposition = str(row.get("execution_disposition"))
        dispositions[family] = disposition
        check.expect(
            disposition in {"RUN_83334", "SKIP_ZERO_A15"},
            f"unknown delayed disposition {family}: {disposition}",
        )
        job = delayed_plan.get(family)
        check.expect(job is not None, f"source index family absent from plan: {family}")
        if job is None:
            continue
        source = Path(str(row.get("source_path", "")))
        check.expect(norm(source) == norm(job["source_path"]), f"delayed source path differs {family}")
        if not source.is_file():
            check.missing.append(f"delayed_source_{family}:{norm(source)}")
            continue
        try:
            authority = small_record(source)
            check.authorities[f"delayed_source_{family}"] = authority
            check.expect(authority["sha256"] == row.get("source_sha256"), f"delayed source digest differs {family}")
        except Exception as exc:
            check.errors.append(f"delayed source {family} invalid: {exc}")
            continue
        activity = float(row.get("transported_ground_activity_Bq") or 0.0)
        if disposition == "RUN_83334":
            check.expect(str(row.get("source_status", "")).startswith("PASS__"), f"RUN source status differs {family}")
            check.expect(activity > 0.0, f"RUN source activity is not positive {family}")
        elif disposition == "SKIP_ZERO_A15":
            check.expect(str(row.get("source_status", "")).startswith("ZERO_SOURCE__"), f"zero-A15 status differs {family}")
            check.expect(activity == 0.0, f"zero-A15 source activity is nonzero {family}")
            check.expect(bool(row.get("zero_A15_upper_provenance")), f"zero-A15 finite upper provenance absent {family}")
            check.expect(float(row.get("transported_ground_A15_upper95_Bq_conservative") or 0.0) > 0.0, f"zero-A15 finite upper absent {family}")
        records[family] = {
            "execution_disposition": disposition,
            "source_status": row.get("source_status"),
            "source_path": norm(source),
            "source_sha256": row.get("source_sha256"),
            "transported_ground_activity_Bq": activity,
            "finite_A15_upper95_Bq": (
                float(row.get("transported_ground_A15_upper95_Bq_conservative") or 0.0)
                if disposition == "SKIP_ZERO_A15" else None
            ),
        }
    return dispositions, records


def validate_stage_chain(
    config: dict[str, Any],
    plan: Sequence[dict[str, Any]],
    check: Checker,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    files = stage_files(config)
    payloads: dict[str, Any] = {}
    bindings: dict[str, Any] = {}
    csvs: dict[str, list[dict[str, str]]] = {}
    for stage, members in files.items():
        summary = check.json(f"{stage}_summary", members["summary"])
        payloads[stage] = summary
        binding: dict[str, Any] = {
            "expected_status": EXPECTED_STAGE_STATUS[stage],
            "summary_path": norm(members["summary"]),
            "observed_status": summary.get("status") if summary else None,
        }
        if summary is not None:
            check.expect(summary.get("status") == EXPECTED_STAGE_STATUS[stage], f"{stage} status differs")
        if "manifest" in members:
            manifest = check.json(f"{stage}_manifest", members["manifest"])
            binding["manifest_path"] = norm(members["manifest"])
            binding["manifest_status"] = manifest.get("status") if manifest else None
            if manifest is not None:
                check.expect(manifest.get("status") == EXPECTED_STAGE_STATUS[stage], f"{stage} manifest status differs")
        for label, path in members.items():
            if label in {"summary", "manifest"}:
                continue
            rows = check.csv(f"{stage}_{label}", path)
            if rows is not None:
                csvs[f"{stage}_{label}"] = rows
        bindings[stage] = binding

    stage00 = payloads.get("stage00")
    validate_geometry_authorities(stage00, config, check)
    if stage00:
        check.expect(nested(stage00, "plan", "jobs") == EXPECTED_PLAN_ROWS, "stage00 plan rows differ")
        check.expect(nested(stage00, "plan", "background_jobs") == EXPECTED_BACKGROUND_JOBS, "stage00 background jobs differ")
        check.expect(nested(stage00, "plan", "instant_histories") == EXPECTED_INSTANT_HISTORIES, "stage00 instant total differs")
        check.expect(nested(stage00, "plan", "buildup_histories") == EXPECTED_BUILDUP_HISTORIES, "stage00 buildup total differs")
        check.expect(nested(stage00, "sources", "count") == EXPECTED_BACKGROUND_JOBS, "stage00 source count differs")
        check.expect(nested(stage00, "sources", "all_sf3_geometry") is True, "stage00 sources are not SF3-only")
        check.expect(nested(stage00, "sources", "legacy_reference_count") == 0, "stage00 includes legacy spectrum references")
        check.expect(nested(stage00, "seed_audit", "status") == "PASS", "stage00 seed audit not PASS")
        check.expect(nested(stage00, "seed_audit", "new_unique_seed_count") == EXPECTED_PLAN_ROWS, "stage00 new seed count differs")
        check.expect(nested(stage00, "seed_audit", "collisions") == [], "stage00 seed collision list nonempty")

    stage01 = payloads.get("stage01")
    if stage01:
        check.expect(stage01.get("selected_jobs") == EXPECTED_INSTANT_JOBS, "stage01 selected instant jobs differ")
        check.expect(stage01.get("selected_histories") == EXPECTED_INSTANT_HISTORIES, "stage01 instant histories differ")
        check.expect(tuple(nested(stage01, "passive_w_diagnostics", "passive_w_volumes") or []) == PASSIVE_W_VOLUMES, "stage01 passive-W volume list differs")
        check.expect("STRICTLY_DISJOINT" in str(nested(stage01, "passive_w_diagnostics", "role")), "stage01 passive-W role differs")
        policy = stage01.get("active_veto") or {}
        check.expect(set(policy.get("passive_w_volumes") or []) == set(PASSIVE_W_VOLUMES), "stage01 veto policy passive-W list differs")
        check.expect(policy.get("passive_w_role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage01 W was not excluded from veto")
    stage01_w = csvs.get("stage01_w", [])
    if stage01_w:
        check.expect(len(stage01_w) == EXPECTED_INSTANT_JOBS, "stage01 W diagnostic rows differ")
        check.expect(all(row.get("geometry") == "SF3" for row in stage01_w), "stage01 W diagnostics are not SF3-only")
        check.expect(all("NOT_BGO_OR_PLASTIC_VETO" in row.get("veto_role", "") for row in stage01_w), "stage01 W diagnostic gained a veto role")

    source_index = csvs.get("stage02_source_index", [])
    dispositions, disposition_records = validate_source_index(source_index, plan, check) if source_index else ({}, {})
    run_families = [family for family in FAMILIES if dispositions.get(family) == "RUN_83334"]
    zero_families = [family for family in FAMILIES if dispositions.get(family) == "SKIP_ZERO_A15"]
    stage02 = payloads.get("stage02")
    if stage02:
        check.expect(stage02.get("selected_buildup_jobs") == EXPECTED_BUILDUP_JOBS, "stage02 buildup jobs differ")
        check.expect(stage02.get("selected_buildup_histories") == EXPECTED_BUILDUP_HISTORIES, "stage02 buildup histories differ")
        check.expect(stage02.get("registered_delayed_source_cells") == EXPECTED_DELAYED_REGISTERED, "stage02 registered delayed cells differ")
        check.expect(stage02.get("delayed_transport_jobs_planned") == len(run_families), "stage02 RUN disposition count differs")
        check.expect(stage02.get("delayed_zero_source_jobs_skipped") == len(zero_families), "stage02 zero-A15 skip count differs")
        check.expect(set(stage02.get("zero_source_families") or []) == set(zero_families), "stage02 zero-A15 family list differs")
    inventory = csvs.get("stage02_inventory", [])
    if inventory:
        check.expect(all(row.get("geometry") == "SF3" for row in inventory), "stage02 inventory is not SF3-only")
        for row in inventory:
            if row.get("source_volume") in PASSIVE_W_VOLUMES:
                check.expect(row.get("material_category") == "passive_w_or_collimator", f"SF3 W inventory row misclassified: {row.get('source_volume')}")

    stage03 = payloads.get("stage03")
    if stage03:
        check.expect(stage03.get("registered_source_cells") == EXPECTED_DELAYED_REGISTERED, "stage03 registered delayed cells differ")
        check.expect(stage03.get("transport_jobs") == len(run_families), "stage03 transport jobs differ")
        check.expect(stage03.get("skipped_zero_A15_jobs") == len(zero_families), "stage03 zero-A15 skips differ")
        check.expect(stage03.get("transport_triggers") == EXPECTED_DELAYED_EVENTS * len(run_families), "stage03 delayed trigger total differs")
        check.expect(tuple(nested(stage03, "passive_w_diagnostics", "passive_w_volumes") or []) == PASSIVE_W_VOLUMES, "stage03 passive-W volume list differs")
        check.expect("STRICTLY_DISJOINT" in str(nested(stage03, "passive_w_diagnostics", "role")), "stage03 passive-W role differs")
    coverage = csvs.get("stage03_coverage", [])
    if coverage:
        check.expect(len(coverage) == EXPECTED_DELAYED_REGISTERED, "stage03 coverage rows != 8")
        observed = {row.get("family"): row.get("execution_disposition") for row in coverage}
        check.expect(observed == dispositions, "stage03/source-index delayed disposition closure differs")
    stage03_w = csvs.get("stage03_w", [])
    if stage03_w:
        check.expect(len(stage03_w) == EXPECTED_DELAYED_REGISTERED, "stage03 W diagnostic rows != 8")
        check.expect(all("NOT_BGO_OR_PLASTIC_VETO" in row.get("veto_role", "") or "NO_SIM_FOR_ZERO_A15" in row.get("veto_role", "") for row in stage03_w), "stage03 W diagnostic gained a veto role")

    stage04 = payloads.get("stage04")
    if stage04:
        check.expect(stage04.get("signal_scope") == "FULL_ENVELOPE_SF3_ONLY", "stage04 signal scope differs")
        check.expect(nested(stage04, "catalogs", "prompt") == len(FAMILIES), "stage04 prompt catalog closure differs")
        check.expect(nested(stage04, "catalogs", "delayed_registered_cells") == len(FAMILIES), "stage04 delayed registered closure differs")
        check.expect(set(nested(stage04, "delayed_dispositions", "RUN_83334") or []) == set(run_families), "stage04 RUN family closure differs")
        check.expect(set(nested(stage04, "delayed_dispositions", "SKIP_ZERO_A15") or []) == set(zero_families), "stage04 zero-A15 family closure differs")
        check.expect(nested(stage04, "signal", "eventlist_rows") == EXPECTED_SIGNAL_EVENTS, "stage04 signal eventlist rows differ")
        check.expect(tuple(nested(stage04, "passive_w", "volumes") or []) == tuple(sorted(PASSIVE_W_VOLUMES)), "stage04 passive-W volume list differs")
        check.expect(nested(stage04, "passive_w", "role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage04 passive-W role differs")
        response_veto = nested(stage04, "response", "active_veto") or {}
        check.expect(
            set(response_veto.get("active_veto_volumes") or [])
            == set(config.get("geometry", {}).get("active_veto_volumes") or []),
            "stage04 active-veto volume set differs from config",
        )
        check.expect(
            set(response_veto.get("passive_w_volumes") or [])
            == set(PASSIVE_W_VOLUMES),
            "stage04 response passive-W list differs",
        )
        check.expect(
            response_veto.get("passive_w_role")
            == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
            "stage04 response assigned W an active-veto role",
        )
        check.expect(nested(stage04, "frozen_se3", "SIMs_or_receipts_opened") == 0, "stage04 opened frozen SE3 transport")
    stage04_w = csvs.get("stage04_w", [])
    if stage04_w:
        check.expect(all(row.get("geometry") == "SF3" for row in stage04_w), "stage04 W diagnostics are not SF3-only")
        check.expect(all(row.get("passive_w_role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO" for row in stage04_w), "stage04 W diagnostics gained a veto role")
    signal_rows = csvs.get("stage04_signal", [])
    final_signal = [
        row for row in signal_rows
        if row.get("geometry") == "SF3"
        and row.get("signal_scope") == "FULL_ENVELOPE_SF3_ONLY"
        and row.get("response_state") == "measured"
        and row.get("stage") == "side_compton_fov_pass"
        and row.get("window_id") == "w2_510p58_511p42"
    ]
    check.expect(len(final_signal) == 1, "stage04 final measured-W2 signal row closure differs")
    if final_signal:
        check.expect(int(final_signal[0].get("trials", -1)) == EXPECTED_SIGNAL_EVENTS, "stage04 final signal trials differ")
    cutflow = csvs.get("stage04_cutflow", [])
    final_background = [
        row for row in cutflow
        if row.get("geometry") == "SF3"
        and row.get("stream") in {"prompt", "delayed"}
        and row.get("response_state") == "measured"
        and row.get("stage") == "side_compton_fov_pass"
        and row.get("window_id") == "w2_510p58_511p42"
    ]
    check.expect(
        {(row.get("stream"), row.get("family")) for row in final_background}
        == {(stream, family) for stream in ("prompt", "delayed") for family in FAMILIES},
        "stage04 final background family/stream closure differs",
    )

    stage05 = payloads.get("stage05")
    if stage05:
        check.expect(nested(stage05, "fresh_sf3", "signal", "trials") == EXPECTED_SIGNAL_EVENTS, "stage05 fresh SF3 trials differ")
        check.expect(nested(stage05, "frozen_se3", "signal", "trials") == EXPECTED_SIGNAL_EVENTS, "stage05 frozen SE3 trials differ")
        check.expect(nested(stage05, "fresh_sf3", "signal", "signal_scope") == "FULL_ENVELOPE_SF3_ONLY", "stage05 fresh signal scope differs")
        check.expect(nested(stage05, "frozen_se3", "signal", "signal_scope") == "FULL_ENVELOPE_SE3_ONLY", "stage05 frozen signal scope differs")
        check.expect(nested(stage05, "passive_w", "role") == "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO", "stage05 passive-W role differs")
        check.expect(nested(stage05, "f3_gate", "status") == "DEFERRED_TO_STAGE06_81NODE_MISSION_FOLD", "stage05 improperly decided the F3 gate")
        check.expect(nested(stage05, "f3_gate", "proxy_is_not_a_gate") is True, "stage05 proxy was made a gate")

    stage06 = payloads.get("stage06")
    mission_result: dict[str, Any] = {}
    if stage06:
        mission_result = validate_mission(stage06, config, csvs, check)
    return bindings, dispositions, {
        "payloads": payloads,
        "disposition_records": disposition_records,
        "run_families": run_families,
        "zero_families": zero_families,
        "mission": mission_result,
        "final_signal": final_signal[0] if final_signal else None,
    }


def validate_mission(
    stage06: dict[str, Any],
    config: dict[str, Any],
    csvs: dict[str, list[dict[str, str]]],
    check: Checker,
) -> dict[str, Any]:
    contract = stage06.get("mission_contract") or {}
    check.expect(contract.get("time_nodes") == EXPECTED_MISSION_NODES, "mission nodes != 81")
    check.expect(close(contract.get("duration_days"), EXPECTED_MISSION_DAYS, rel=0.0, absolute=0.0), "mission duration != 20 days")
    check.expect(nested(stage06, "ratio_contract", "status") == "FAIR_MATCHED_37194_RAY_FULL_ENVELOPE", "mission fair-ratio contract differs")
    check.expect(nested(stage06, "ratio_contract", "frozen_se3_transport_or_receipt_required") is False, "mission required fresh SE3 transport/receipts")
    check.expect(nested(stage06, "ratio_contract", "gate_uses") == "central_identity_only", "mission gate is not central-only")
    check.expect("never_gate" in str(nested(stage06, "ratio_contract", "proxy_uses")), "mission proxy gate role differs")
    geometries = stage06.get("geometries") or {}
    sf3 = geometries.get("SF3") or {}
    se3 = geometries.get("SE3") or {}
    frozen = config.get("frozen_se3") or {}
    for observed, expected, label in (
        (se3.get("source_counts_20d"), frozen.get("S20_counts"), "SE3 S20"),
        (se3.get("background_counts_20d"), frozen.get("B20_counts"), "SE3 B20"),
        (se3.get("F3_20d_ph_cm2_s"), frozen.get("F3_ph_cm2_s"), "SE3 F3"),
        (se3.get("F3_20d_componentwise_proxy_ph_cm2_s"), frozen.get("F3_proxy_ph_cm2_s"), "SE3 F3 proxy"),
        (se3.get("signal_selected_events"), frozen.get("signal_selected"), "SE3 selected rays"),
        (se3.get("signal_trials"), frozen.get("signal_trials"), "SE3 trials"),
        (se3.get("selected_effective_area_cm2"), frozen.get("signal_aeff_cm2"), "SE3 Aeff"),
    ):
        check.expect(close(observed, expected), f"frozen {label} anchor differs")
    check.expect(sf3.get("signal_scope") == "FULL_ENVELOPE_SF3_ONLY", "mission SF3 signal scope differs")
    check.expect(se3.get("signal_scope") == "FULL_ENVELOPE_SE3_ONLY", "mission SE3 signal scope differs")
    check.expect(sf3.get("signal_trials") == EXPECTED_SIGNAL_EVENTS, "mission SF3 trials differ")

    ratios = stage06.get("fair_full_envelope_ratios") or {}
    central = ratios.get("F3_SF3_over_SE3_full_envelope")
    proxy = ratios.get("F3_componentwise_proxy_SF3_over_SE3_full_envelope")
    check.expect(close(central, float(sf3.get("F3_20d_ph_cm2_s")) / float(se3.get("F3_20d_ph_cm2_s"))), "reported central F3 ratio differs from geometry values")
    check.expect(close(proxy, float(sf3.get("F3_20d_componentwise_proxy_ph_cm2_s")) / float(se3.get("F3_20d_componentwise_proxy_ph_cm2_s"))), "reported proxy F3 ratio differs from geometry values")
    gate = stage06.get("fullstat_gate") or {}
    expected_topup = bool(float(central) <= FULLSTAT_GATE) if central is not None else False
    expected_decision = "TOPUP_TO_S3D_FULL_STAT_REQUIRED" if expected_topup else "STOP__NO_FULLSTAT_TOPUP"
    check.expect(gate.get("metric") == "F3_SF3_over_SE3_full_envelope", "full-stat gate metric differs")
    check.expect(gate.get("operator") == "<=", "full-stat gate operator differs")
    check.expect(close(gate.get("threshold"), FULLSTAT_GATE, rel=0.0, absolute=0.0), "full-stat gate threshold differs")
    check.expect(close(gate.get("observed_central_ratio"), central), "full-stat gate observed central ratio differs")
    check.expect(gate.get("topup_required") is expected_topup, "full-stat top-up boolean differs")
    check.expect(gate.get("decision") == expected_decision, "full-stat gate decision differs")
    check.expect(gate.get("proxy_controls_gate") is False, "componentwise proxy controls the gate")
    check.expect(close(gate.get("proxy_ratio_reported_only"), proxy), "reported-only proxy ratio differs")

    timeline = csvs.get("stage06_timeline", [])
    check.expect(len(timeline) == EXPECTED_MISSION_NODES * 2, "mission timeline rows != 162")
    for geometry in ("SE3", "SF3"):
        rows = [row for row in timeline if row.get("geometry") == geometry]
        check.expect(len(rows) == EXPECTED_MISSION_NODES, f"mission timeline {geometry} rows != 81")
        check.expect(len({row.get("time_bin_id") for row in rows}) == EXPECTED_MISSION_NODES, f"mission timeline {geometry} node IDs differ")
    comparison = csvs.get("stage06_comparison", [])
    check.expect({row.get("geometry") for row in comparison} == {"SE3", "SF3"}, "mission comparison geometry closure differs")
    return {
        "SF3": sf3,
        "SE3": se3,
        "central_F3_ratio": central,
        "componentwise_proxy_F3_ratio": proxy,
        "gate_threshold": FULLSTAT_GATE,
        "topup_required": expected_topup,
        "decision": expected_decision,
        "proxy_controls_gate": False,
    }


def validate_receipt(
    job: dict[str, Any],
    payload: dict[str, Any],
    path: Path,
    check: Checker,
) -> dict[str, Any]:
    """Validate compact receipt fields without querying any artifact path."""
    job_id = str(job["job_id"])
    check.expect(payload.get("status") == "PASS", f"non-PASS receipt {job_id}")
    check.expect(payload.get("errors") in (None, []), f"receipt errors nonempty {job_id}")
    check.expect(payload.get("profile_id") == PROFILE_ID, f"receipt profile differs {job_id}")
    for key in (
        "job_id", "stage", "geometry", "mode", "family", "events", "seed",
        "source_path", "setup_path",
    ):
        check.expect(payload.get(key) == job.get(key), f"receipt {job_id} {key} differs from plan")
    check.expect(payload.get("returncode") == 0, f"receipt returncode differs {job_id}")
    check.expect(payload.get("watchdog_reason") == "completed", f"receipt watchdog status differs {job_id}")
    log = payload.get("log") or {}
    header = payload.get("sim_header") or {}
    check.expect(log.get("generated_events") == job["events"], f"generated events differ {job_id}")
    check.expect(log.get("graphics_terminal_marker") is True, f"graphics terminal marker absent {job_id}")
    check.expect(log.get("error_marker") is False, f"error marker present {job_id}")
    check.expect(norm(str(header.get("geometry", ""))) == norm(job["setup_path"]), f"SIM header geometry metadata differs {job_id}")
    check.expect(header.get("seed") == job["seed"], f"SIM header seed metadata differs {job_id}")
    check.expect(header.get("policy") == "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST", f"SIM header policy differs {job_id}")
    check.expect(payload.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", f"SIM digest policy differs {job_id}")
    check.expect(SHA256_RE.fullmatch(str(payload.get("source_sha256", ""))) is not None, f"source digest metadata invalid {job_id}")
    for key in ("source_path", "setup_path", "sim_path", "log_path", "attempt_dir"):
        check.expect(os.path.isabs(str(payload.get(key, ""))), f"receipt path is not absolute {job_id}/{key}")
    sim_path = str(payload.get("sim_path", ""))
    check.expect(sim_path.lower().endswith((".sim", ".sim.gz")), f"receipt SIM path suffix differs {job_id}")
    source = Path(str(payload.get("source_path", "")))
    if not source.is_file():
        check.missing.append(f"receipt_source_{job_id}:{norm(source)}")
    else:
        try:
            source_digest = sha256_small(source)
            check.expect(source_digest == payload.get("source_sha256"), f"receipt source digest differs {job_id}")
        except Exception as exc:
            check.errors.append(f"receipt source invalid {job_id}: {exc}")
    isotope = payload.get("isotope_dat") or {}
    if job.get("stage") == "background":
        check.expect(isinstance(isotope.get("TT_s"), (int, float)) and isotope.get("TT_s", 0) > 0, f"background TT is not positive {job_id}")
        check.expect(isotope.get("terminal_EN") is True, f"background DAT terminal marker absent {job_id}")
    sim_bytes = int(payload.get("sim_bytes", -1))
    log_bytes = int(payload.get("log_bytes", -1))
    dat_bytes = int(payload.get("isotope_dat_bytes", 0) or 0)
    artifact_bytes = int(payload.get("artifact_bytes", -1))
    check.expect(sim_bytes > 0 and log_bytes > 0 and dat_bytes >= 0, f"receipt byte metadata invalid {job_id}")
    check.expect(artifact_bytes == sim_bytes + log_bytes + dat_bytes, f"receipt artifact-byte closure differs {job_id}")
    return {
        "job_id": job_id,
        "receipt_path": norm(path),
        "receipt_sha256": sha256_small(path),
        "stage": job["stage"],
        "geometry": job["geometry"],
        "mode": job["mode"],
        "family": job["family"],
        "events": int(job["events"]),
        "seed": int(job["seed"]),
        "attempt": int(payload.get("attempt", 0)),
        "started_at": payload.get("started_at"),
        "ended_at": payload.get("ended_at"),
        "source_path": norm(payload.get("source_path", "")),
        "source_sha256": payload.get("source_sha256"),
        "setup_path": norm(payload.get("setup_path", "")),
        "header_geometry": norm(header.get("geometry", "")),
        "header_seed": header.get("seed"),
        "sim_path": sim_path,
        "sim_bytes": sim_bytes,
        "log_path": str(payload.get("log_path", "")),
        "log_bytes": log_bytes,
        "isotope_dat_bytes": dat_bytes,
        "artifact_bytes": artifact_bytes,
        "peak_process_group_rss_bytes": int(payload.get("peak_process_group_rss_bytes", 0)),
        "wall_s": float(payload.get("wall_s", 0.0)),
        "beam_on_cpu_s": float(log.get("beam_on_cpu_s", 0.0) or 0.0),
        "TT_s": isotope.get("TT_s"),
        "RP_record_count": isotope.get("RP_record_count"),
    }


def validate_receipts(
    config: dict[str, Any],
    plan: Sequence[dict[str, Any]],
    dispositions: dict[str, str],
    audits: dict[str, dict[str, Any] | None],
    check: Checker,
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    run_root = Path(str(config["run_root"]))
    receipt_root = run_root / "receipts"
    background_ids = {str(row["job_id"]) for row in plan if row.get("stage") == "background"}
    delayed_run_ids = {
        str(row["job_id"]) for row in plan
        if row.get("stage") == "delayed" and dispositions.get(str(row["family"])) == "RUN_83334"
    }
    delayed_zero_ids = {
        str(row["job_id"]) for row in plan
        if row.get("stage") == "delayed" and dispositions.get(str(row["family"])) == "SKIP_ZERO_A15"
    }
    signal_ids = {str(row["job_id"]) for row in plan if row.get("stage") == "signal"}
    expected_ids = background_ids | delayed_run_ids | signal_ids
    plan_by_id = {str(row["job_id"]): row for row in plan}
    if not receipt_root.is_dir():
        check.missing.append(f"canonical_receipt_root:{norm(receipt_root)}")
        return [], expected_ids, delayed_zero_ids
    observed_files = {
        path.stem: path for path in receipt_root.iterdir()
        if path.is_file() and path.suffix == ".json"
    }
    check.expect(set(observed_files) == expected_ids, "canonical receipt file set differs from effective 30-row plan")
    check.expect(not (set(observed_files) & delayed_zero_ids), "zero-A15 skip has a forbidden receipt")
    rows: list[dict[str, Any]] = []
    receipt_payloads: dict[str, dict[str, Any]] = {}
    for job_id in sorted(expected_ids):
        path = receipt_root / f"{job_id}.json"
        payload = check.json(f"receipt_{job_id}", path)
        if payload is None:
            continue
        receipt_payloads[job_id] = payload
        rows.append(validate_receipt(plan_by_id[job_id], payload, path, check))
    check.expect(len(rows) == len(expected_ids), "effective receipt count differs")
    check.expect(len({row["sim_path"] for row in rows}) == len(rows), "duplicate SIM path metadata in receipts")
    check.expect(all(row["geometry"] == "SF3" for row in rows), "effective receipts are not SF3-only")
    check.expect(sum(row["events"] for row in rows if row["mode"] == "instant") == EXPECTED_INSTANT_HISTORIES, "receipt instant total differs")
    check.expect(sum(row["events"] for row in rows if row["mode"] == "buildup") == EXPECTED_BUILDUP_HISTORIES, "receipt buildup total differs")
    check.expect(sum(row["events"] for row in rows if row["stage"] == "delayed") == EXPECTED_DELAYED_EVENTS * len(delayed_run_ids), "receipt delayed trigger total differs")
    check.expect(sum(row["events"] for row in rows if row["stage"] == "signal") == EXPECTED_SIGNAL_EVENTS, "receipt signal trials differ")

    canary = next((row for row in rows if row["job_id"] == EXPECTED_CANARY), None)
    check.expect(canary is not None and canary["events"] == EXPECTED_CANARY_EVENTS, "counted production canary receipt differs")
    if canary is not None:
        try:
            canary_end = datetime.fromisoformat(str(canary["ended_at"]))
            other_starts = [
                datetime.fromisoformat(str(row["started_at"])) for row in rows
                if row["stage"] == "background" and row["job_id"] != EXPECTED_CANARY
            ]
            check.expect(bool(other_starts) and canary_end <= min(other_starts), "gamma canary was not completed before remaining counted background production")
        except Exception as exc:
            check.errors.append(f"canary chronology invalid: {exc}")

    all_audit = audits.get("all_receipts") or {}
    record_map = {str(item.get("job_id")): item for item in all_audit.get("receipt_records", [])}
    check.expect(set(record_map) == expected_ids, "all-receipt audit record set differs")
    for row in rows:
        record = record_map.get(row["job_id"])
        if record:
            check.expect(norm(record.get("path", "")) == row["receipt_path"], f"all-audit receipt path differs {row['job_id']}")
            check.expect(record.get("sha256") == row["receipt_sha256"], f"all-audit receipt digest differs {row['job_id']}")
    aggregate = audits.get("transport_receipts") or {}
    aggregate_map = {str(item.get("job_id")): item for item in aggregate.get("selected_receipts", [])}
    check.expect(set(aggregate_map) == expected_ids, "aggregate receipt set differs")
    for row in rows:
        item = aggregate_map.get(row["job_id"])
        if item:
            check.expect(item.get("sha256") == row["receipt_sha256"], f"aggregate receipt digest differs {row['job_id']}")
            check.expect(item.get("sim_path") == row["sim_path"], f"aggregate SIM path metadata differs {row['job_id']}")
            check.expect(int(item.get("sim_bytes", -1)) == row["sim_bytes"], f"aggregate SIM byte metadata differs {row['job_id']}")
    return rows, expected_ids, delayed_zero_ids


def validate_audits(
    config: dict[str, Any],
    plan: Sequence[dict[str, Any]],
    dispositions: dict[str, str],
    check: Checker,
) -> dict[str, dict[str, Any] | None]:
    package_root = Path(str(config["package_root"]))
    paths = {
        "source_validation": package_root / "audit/sf3_plan1_source_validation.json",
        "background_receipts": package_root / "audit/sf3_plan1_background_receipt_validation.json",
        "delayed_receipts": package_root / "audit/sf3_plan1_delayed_receipt_validation.json",
        "signal_receipts": package_root / "audit/sf3_plan1_signal_receipt_validation.json",
        "all_receipts": package_root / "audit/sf3_plan1_all_receipt_validation.json",
        "statistics": package_root / "audit/sf3_plan1_statistics_validation.json",
        "transport_receipts": package_root / "audit/sf3_plan1_transport_receipts.json",
        "activation": package_root / "audit/sf3_activation_validation.json",
        "signal_static": package_root / "audit/full_envelope_signal_static_audit.json",
        "signal_gate": package_root / "audit/full_envelope_signal_transport_gate.json",
        "interrupt_recovery": package_root / "audit/controller_interruption_recovery_20260816.json",
        "controller_interruption_recovery_latest": package_root / "audit/controller_interruption_recovery_20260816T031021.json",
        "systemd_oomd_recovery": package_root / "audit/systemd_oomd_recovery_20260816T032354.json",
        "manual_quota_recovery": package_root / "audit/sf3_manual_quota_recovery_20260816.json",
        "resource_timeline": package_root / "audit/sf3_resource_timeline_audit.json",
    }
    audits = {name: check.json(f"audit_{name}", path) for name, path in paths.items()}
    source = audits["source_validation"]
    if source:
        check.expect(source.get("status") == "PASS", "source validation is not PASS")
        check.expect(nested(source, "sources", "count") == EXPECTED_BACKGROUND_JOBS, "validated background source count differs")
        check.expect(nested(source, "sources", "all_sf3_geometry") is True, "validated background sources are not all SF3")
        check.expect(nested(source, "sources", "legacy_reference_count") == 0, "legacy source references present")
    run_count = sum(value == "RUN_83334" for value in dispositions.values())
    effective_count = EXPECTED_BACKGROUND_JOBS + run_count + 1
    expected_events = EXPECTED_INSTANT_HISTORIES + EXPECTED_BUILDUP_HISTORIES + run_count * EXPECTED_DELAYED_EVENTS + EXPECTED_SIGNAL_EVENTS
    expected_scopes = {
        "background_receipts": ("background", EXPECTED_BACKGROUND_JOBS, EXPECTED_INSTANT_HISTORIES + EXPECTED_BUILDUP_HISTORIES),
        "delayed_receipts": ("delayed", run_count, run_count * EXPECTED_DELAYED_EVENTS),
        "signal_receipts": ("signal", 1, EXPECTED_SIGNAL_EVENTS),
        "all_receipts": ("all", effective_count, expected_events),
    }
    for name, (scope, jobs, events) in expected_scopes.items():
        payload = audits[name]
        if payload:
            check.expect(payload.get("status") == "PASS", f"{name} is not PASS")
            check.expect(payload.get("scope") == scope, f"{name} scope differs")
            check.expect(payload.get("validated_jobs_in_scope") == jobs, f"{name} job count differs")
            check.expect(payload.get("validated_events_in_scope") == events, f"{name} event total differs")
            check.expect(payload.get("errors") == [], f"{name} errors nonempty")
            check.expect(payload.get("dynamic_reserve_pass") is True, f"{name} dynamic disk reserve failed")
    statistics = audits["statistics"]
    if statistics:
        check.expect(statistics.get("status") == "PASS", "statistics validation is not PASS")
        check.expect(len(statistics.get("cell_summary") or []) == 16, "statistics cell closure != 16")
        check.expect(statistics.get("errors") == [], "statistics errors nonempty")
    aggregate = audits["transport_receipts"]
    zero_ids = {
        str(row["job_id"]) for row in plan
        if row.get("stage") == "delayed" and dispositions.get(str(row["family"])) == "SKIP_ZERO_A15"
    }
    expected_exclusions = {job_id: "ZERO_A15__NO_DELAYED_TRANSPORT__FINITE_UPPER_LIMIT_ONLY" for job_id in zero_ids}
    if aggregate:
        check.expect(aggregate.get("status") == f"PASS__ALL_{effective_count}_EFFECTIVE_SF3_ONLY_TRANSPORT_JOBS", "aggregate transport status differs")
        check.expect(aggregate.get("planned_jobs") == EXPECTED_PLAN_ROWS, "aggregate planned jobs != 30")
        check.expect(aggregate.get("effective_planned_jobs") == effective_count, "aggregate effective job count differs")
        check.expect(aggregate.get("validated_jobs") == effective_count, "aggregate validated job count differs")
        check.expect(aggregate.get("background_validated_jobs") == EXPECTED_BACKGROUND_JOBS, "aggregate background receipt closure differs")
        check.expect(aggregate.get("execution_exclusions") == expected_exclusions, "aggregate dynamic zero-A15 exclusions differ")
        check.expect(nested(aggregate, "projection", "pass") is True, "aggregate dynamic disk projection failed")
    activation = audits["activation"]
    if activation:
        check.expect(activation.get("status") == "PASS", "activation launch audit is not PASS")
        check.expect(activation.get("geometry") == "SF3", "activation launch audit geometry differs")
        check.expect(activation.get("registered_delayed_source_cells") == EXPECTED_DELAYED_REGISTERED, "activation registered cells != 8")
        check.expect(activation.get("transport_delayed_jobs") == run_count, "activation RUN job count differs")
        check.expect(activation.get("skipped_zero_A15_jobs") == len(zero_ids), "activation zero-A15 skip count differs")
        cards = activation.get("source_cards") or []
        check.expect(len(cards) == EXPECTED_DELAYED_REGISTERED, "activation source-card records != 8")
        observed = {str(row.get("family")): str(row.get("execution_disposition")) for row in cards}
        check.expect(observed == dispositions, "activation/source-index disposition closure differs")
        plan_delayed = {
            str(row["family"]): row
            for row in plan if row.get("stage") == "delayed"
        }
        for card in cards:
            family = str(card.get("family"))
            job = plan_delayed.get(family)
            if job is None:
                continue
            check.expect(card.get("job_id") == job.get("job_id"), f"activation job ID differs {family}")
            check.expect(card.get("seed") == job.get("seed"), f"activation seed differs {family}")
            check.expect(card.get("registered_events") == EXPECTED_DELAYED_EVENTS, f"activation registered events differ {family}")
            authority = check.authorities.get(f"delayed_source_{family}") or {}
            check.expect(card.get("sha256") == authority.get("sha256"), f"activation delayed source digest differs {family}")
    static = audits["signal_static"]
    if static:
        check.expect(static.get("status") == "PASS__SF3_FULL_ENVELOPE_SIGNAL_STATIC_AUDIT", "signal static audit status differs")
        check.expect(static.get("geometry") == "SF3", "signal static geometry differs")
        check.expect(static.get("rows") == EXPECTED_SIGNAL_EVENTS, "signal frozen-bank rows differ")
        check.expect(nested(static, "frozen_bank", "input_sha256") == nested(config, "signal", "eventlist_frozen_sha256"), "frozen 37194-ray bank digest differs")
        check.expect(nested(static, "sf3_native_navigation", "added_w_chord_contract") == "ZERO_FOR_ALL_FOCUSED_RAYS", "signal navigation added-W chord contract differs")
        check.expect(nested(static, "signal", "job", "job_id") == "signal_full_envelope_sf3", "signal static job differs")
    signal_gate = audits["signal_gate"]
    if signal_gate:
        check.expect(signal_gate.get("status") == "PASS", "signal transport gate is not PASS")
        check.expect(signal_gate.get("transport_scope") == "FULL_ENVELOPE_SF3_ONLY", "signal transport scope differs")
        check.expect(signal_gate.get("permitted_signal_jobs") == ["signal_full_envelope_sf3"], "signal transport gate is not exact SF3-only")
        check.expect("NO_SE3_SIGNAL_RERUN" in str(signal_gate.get("frozen_se3_policy")), "signal gate does not prohibit SE3 rerun")
        static_record = check.authorities.get("audit_signal_static") or {}
        check.expect(
            norm(nested(signal_gate, "authority", "path") or "")
            == norm(paths["signal_static"]),
            "signal gate static-authority path differs",
        )
        check.expect(
            nested(signal_gate, "authority", "sha256") == static_record.get("sha256"),
            "signal gate static-authority digest differs",
        )
        check.expect(
            nested(signal_gate, "authority", "status")
            == "PASS__SF3_FULL_ENVELOPE_SIGNAL_STATIC_AUDIT",
            "signal gate static-authority status differs",
        )
    recovery = audits["interrupt_recovery"]
    if recovery:
        check.expect(recovery.get("status") == "PASS__SF3_INTERRUPTED_PARTIALS_AUDITED_FOR_RECOVERY", "GUI interruption recovery audit differs")
        check.expect(recovery.get("statistics_policy") == "FAILED_PARTIALS_EXCLUDED", "failed partials were not excluded")
        check.expect("EVENT_ZERO" in str(recovery.get("retry_policy")), "interrupted jobs were not retried whole from event zero")
        check.expect(nested(recovery, "resource_gate_at_recovery", "pass") is True, "resource gate failed at GUI recovery")
        check.expect(nested(recovery, "resource_gate_at_recovery", "mem_floor_bytes") == MEMORY_FLOOR_BYTES, "recovery memory floor differs")
        check.expect(nested(recovery, "resource_gate_at_recovery", "swap_floor_bytes") == SWAP_FLOOR_BYTES, "recovery swap floor differs")
        check.expect(nested(recovery, "resource_gate_at_recovery", "disk_reserve_bytes") == DYNAMIC_RESERVE_BYTES, "recovery disk reserve differs")
    latest_recovery = audits["controller_interruption_recovery_latest"]
    if latest_recovery:
        check.expect(latest_recovery.get("status") == "PASS__SF3_INTERRUPTED_PARTIALS_AUDITED_FOR_RECOVERY", "latest controller interruption recovery audit differs")
        check.expect(latest_recovery.get("statistics_policy") == "INTERRUPTED_PARTIALS_EXCLUDED", "latest interrupted partials were not excluded")
        check.expect("EVENT_ZERO" in str(latest_recovery.get("retry_policy")), "latest interrupted jobs were not retried whole from event zero")
        check.expect(latest_recovery.get("partial_sim_digest_policy") == "NOT_HASHED_BY_CONTRACT", "latest interrupted SIM partials were hashed")
        check.expect(nested(latest_recovery, "process_audit", "controller_alive") is False, "latest recovery still reports a live interrupted controller")
        check.expect(nested(latest_recovery, "process_audit", "cosima_workers_alive") == 0, "latest recovery still reports interrupted Cosima workers")
        check.expect(nested(latest_recovery, "resource_gate_at_recovery", "pass") is True, "resource gate failed at latest controller recovery")
        check.expect(nested(latest_recovery, "resource_gate_at_recovery", "mem_floor_bytes") == MEMORY_FLOOR_BYTES, "latest recovery memory floor differs")
        check.expect(nested(latest_recovery, "resource_gate_at_recovery", "swap_floor_bytes") == SWAP_FLOOR_BYTES, "latest recovery swap floor differs")
        check.expect(nested(latest_recovery, "resource_gate_at_recovery", "disk_reserve_bytes") == DYNAMIC_RESERVE_BYTES, "latest recovery disk reserve differs")
    oomd = audits["systemd_oomd_recovery"]
    if oomd:
        check.expect(oomd.get("status") == "PASS__SF3_SYSTEMD_OOMD_INTERRUPTION_AUDITED_FOR_FOUR_WORKER_RECOVERY", "systemd-oomd recovery audit differs")
        check.expect(oomd.get("root_cause") == "SYSTEMD_OOMD_KILLED_12_PROCESSES_IN_SF3_PLAN1_SERVICE_CGROUP", "systemd-oomd root cause differs")
        check.expect(oomd.get("statistics_policy") == "INTERRUPTED_PARTIALS_EXCLUDED", "systemd-oomd partials were not excluded")
        check.expect("EVENT_ZERO" in str(oomd.get("retry_policy")), "systemd-oomd jobs were not retried whole from event zero")
        check.expect(oomd.get("partial_sim_digest_policy") == "NOT_HASHED_BY_CONTRACT", "systemd-oomd interrupted SIM partials were hashed")
        stability = oomd.get("stability_policy_change") or {}
        check.expect(stability.get("old_controller_cpu_budget") == 6, "pre-recovery controller CPU budget differs")
        check.expect(stability.get("new_controller_cpu_budget") == 4, "stable controller did not fall back to four workers")
        check.expect(stability.get("new_systemd_cpu_quota_cores") == 4, "stable systemd quota did not fall back to four cores")
        check.expect(stability.get("global_oom_protection_disabled") is False, "global OOM protection was disabled")
        check.expect(nested(oomd, "resource_snapshot_after_kill", "pass") is True, "resource snapshot failed after systemd-oomd recovery")
        check.expect(nested(oomd, "resource_snapshot_after_kill", "mem_floor_bytes") == MEMORY_FLOOR_BYTES, "systemd-oomd recovery memory floor differs")
        check.expect(nested(oomd, "resource_snapshot_after_kill", "swap_floor_bytes") == SWAP_FLOOR_BYTES, "systemd-oomd recovery swap floor differs")
        check.expect(nested(oomd, "resource_snapshot_after_kill", "disk_reserve_bytes") == DYNAMIC_RESERVE_BYTES, "systemd-oomd recovery disk reserve differs")
    manual_quota = audits["manual_quota_recovery"]
    if manual_quota:
        check.expect(manual_quota.get("status") == "PASS__SF3_MANUAL_QUOTA_PRESSURE_RECOVERY_AUDITED", "manual quota recovery audit status differs")
        check.expect(manual_quota.get("actual_controller_workers") == 4, "manual quota recovery actual workers differ")
        check.expect(nested(manual_quota, "quota_recovery", "quota_core_sequence") == [4, 3, 4], "manual quota recovery sequence differs")
        check.expect(nested(manual_quota, "quota_recovery", "restored_quota_cores") == 4, "manual quota recovery did not restore four cores")
        check.expect(nested(manual_quota, "quota_recovery", "job_terminated_by_recovery_action") is False, "manual quota recovery terminated a job")
        check.expect(close(nested(manual_quota, "pressure_recovery", "pre_throttle_avg10_percent"), 43.42), "manual pressure peak differs")
        check.expect(close(nested(manual_quota, "pressure_recovery", "systemd_oomd_kill_gate_percent"), 50.0), "manual pressure kill gate differs")
        check.expect(close(nested(manual_quota, "pressure_recovery", "approximately_20_seconds_later_avg10_percent"), 3.67), "manual 20-second pressure recovery differs")
        check.expect(close(nested(manual_quota, "pressure_recovery", "later_avg10_percent"), 0.0), "manual later pressure recovery differs")
        check.expect(manual_quota.get("service_mutated_by_audit") is False, "manual quota audit mutated a service")
    resource_timeline = audits["resource_timeline"]
    if resource_timeline:
        check.expect(
            resource_timeline.get("status")
            == "PASS__SF3_RESOURCE_TIMELINE_ALL_EFFECTIVE_TRANSPORT_RECEIPTS_AND_RESOURCE_SESSIONS",
            "resource timeline audit status differs",
        )
        check.expect(resource_timeline.get("ready") is True, "resource timeline audit is not ready")
        check.expect(nested(resource_timeline, "configuration", "maximum_cpu_budget_cores") == 6, "resource timeline configured CPU maximum differs")
        check.expect(nested(resource_timeline, "configuration", "maximum_is_budget_not_observed_execution") is True, "resource timeline confuses configured maximum with observed execution")
        check.expect(nested(resource_timeline, "recovery", "recovery_records") == 3, "resource timeline does not bind all three recovery audits")
        check.expect(nested(resource_timeline, "recovery", "post_oomd_actual_controller_workers") == 4, "resource timeline actual controller worker count differs")
        check.expect(nested(resource_timeline, "actual_execution", "controller_workers") == 4, "resource timeline execution workers differ")
        guard_sessions = nested(resource_timeline, "actual_execution", "guard_sessions") or {}
        check.expect(valid_guard_session_summary(guard_sessions), "resource guard-session summary contract differs")
        check.expect(guard_sessions.get("all_sessions_closed") is True, "resource guard sessions are not all closed")
        check.expect(guard_sessions.get("all_quotas_within_3_to_4_cores") is True, "resource guard quota left the 3-to-4 core band")
        check.expect(guard_sessions.get("all_throttled_sessions_restored_to_four") is True, "a throttled resource session did not restore four cores")
        check.expect(guard_sessions.get("all_sampled_hard_floors_pass") is True, "resource guard samples breached a hard floor")
        check.expect(guard_sessions.get("safe_all_four_core_session_is_PASS") is True, "resource audit does not accept safe all-four-core sessions")
        check.expect(guard_sessions.get("artificial_throttle_required") is False, "resource audit requires an artificial throttle")
        expected_guard_stages = {"background", "signal"} | ({"delayed"} if run_count else set())
        check.expect(set(guard_sessions.get("required_stage_coverage") or []) == expected_guard_stages, "resource guard required-stage set differs")
        check.expect(expected_guard_stages <= set(guard_sessions.get("observed_closed_stage_coverage") or []), "resource guard closed-stage coverage is incomplete")
        check.expect(set(guard_sessions.get("required_followup_session_labels") or []) == EXPECTED_FOLLOWUP_RESOURCE_SESSIONS, "resource guard required followup-session labels differ")
        check.expect(EXPECTED_FOLLOWUP_RESOURCE_SESSIONS <= set(guard_sessions.get("observed_closed_followup_session_labels") or []), "resource guard followup-session closure is incomplete")
        expected_exact_guard_bindings = {
            "background_transport": "background",
            "transport_signal": "signal",
        }
        if run_count:
            expected_exact_guard_bindings["transport_delayed"] = "delayed"
        check.expect(
            guard_sessions.get("required_exact_label_stage_coverage")
            == expected_exact_guard_bindings,
            "resource guard exact label-to-stage requirements differ",
        )
        observed_exact_guard_bindings = (
            guard_sessions.get("observed_closed_exact_label_stage_coverage") or {}
        )
        check.expect(
            observed_exact_guard_bindings
            == {label: [stage] for label, stage in expected_exact_guard_bindings.items()},
            "resource guard exact label-to-stage receipt coverage is incomplete",
        )
        check.expect(
            guard_sessions.get("all_required_exact_label_stage_bindings_pass") is True,
            "resource guard accepted a mislabeled transport session",
        )
        check.expect(nested(resource_timeline, "manual_pressure_recovery_event", "quota_core_sequence") == [4, 3, 4], "resource timeline did not bind the historical manual quota event")
        check.expect(nested(resource_timeline, "manual_pressure_recovery_event", "event_is_not_a_requirement_to_force_future_throttling") is True, "resource timeline treats the manual event as a future throttle requirement")
        check.expect(nested(resource_timeline, "background_receipts", "validated_jobs") == EXPECTED_BACKGROUND_JOBS, "resource timeline background receipt count differs")
        check.expect(nested(resource_timeline, "background_receipts", "all_canonical_PASS") is True, "resource timeline background receipts are not all canonical PASS")
        check.expect(nested(resource_timeline, "transport_receipts", "validated_jobs") == effective_count, "resource timeline effective transport receipt count differs")
        check.expect(nested(resource_timeline, "transport_receipts", "all_canonical_PASS") is True, "resource timeline effective receipts are not all canonical PASS")
        check.expect(nested(resource_timeline, "completion_resources", "validated_jobs") == effective_count, "resource completion metric count differs")
        check.expect(nested(resource_timeline, "completion_resources", "all_completion_rows_pass_dynamic_reserve") is True, "resource completion dynamic reserve failed")
        check.expect(set(nested(resource_timeline, "delayed_dispositions", "RUN_83334_families") or []) == {family for family, value in dispositions.items() if value == "RUN_83334"}, "resource timeline RUN_83334 families differ")
        check.expect(set(nested(resource_timeline, "delayed_dispositions", "SKIP_ZERO_A15_families") or []) == {family for family, value in dispositions.items() if value == "SKIP_ZERO_A15"}, "resource timeline zero-A15 families differ")
        check.expect(resource_timeline.get("sim_opened_statted_discovered_or_hashed") is False, "resource timeline reports SIM access")
        check.expect(resource_timeline.get("systemd_or_service_action_performed") is False, "resource timeline adapter changed a service")
        authority_pairs = (
            ("analysis_inputs", "analysis_inputs"),
            ("canonical_30_row_plan", "job_plan"),
            ("recovery_controller_gui_recovery", "audit_interrupt_recovery"),
            ("recovery_controller_external_recovery", "audit_controller_interruption_recovery_latest"),
            ("recovery_systemd_oomd_recovery", "audit_systemd_oomd_recovery"),
            ("manual_quota_recovery", "audit_manual_quota_recovery"),
            ("stage02_activation_summary", "stage02_summary"),
            ("stage02_delayed_source_index", "stage02_source_index"),
        )
        timeline_authorities = resource_timeline.get("authorities") or {}
        for timeline_label, finalizer_label in authority_pairs:
            check.expect(
                nested(timeline_authorities, timeline_label, "sha256")
                == (check.authorities.get(finalizer_label) or {}).get("sha256"),
                f"resource timeline authority digest differs: {timeline_label}",
            )
    return audits


def validate_resource_contract(
    config: dict[str, Any],
    receipt_rows: Sequence[dict[str, Any]],
    expected_ids: set[str],
    audits: dict[str, dict[str, Any] | None],
    check: Checker,
) -> dict[str, Any]:
    transport = config.get("transport") or {}
    check.expect(transport.get("cpu_budget") == 6, "CPU budget differs from six")
    check.expect(transport.get("max_cpu_budget") == 6, "maximum CPU budget differs from six")
    check.expect(transport.get("adaptive_min_workers") == 4, "adaptive minimum workers differs from four")
    check.expect(transport.get("adaptive_live_target_workers") == 6, "adaptive live target differs from six")
    check.expect(transport.get("memory_headroom_bytes") == MEMORY_FLOOR_BYTES, "MemAvailable floor differs from 1.5 GiB")
    check.expect(transport.get("aggressive_min_swap_free_bytes") == SWAP_FLOOR_BYTES, "SwapFree floor differs from 8 GiB")
    check.expect(transport.get("dynamic_reserve_bytes") == DYNAMIC_RESERVE_BYTES, "dynamic disk reserve differs from 8 GiB")
    package_root = Path(str(config["package_root"]))
    current_free = shutil.disk_usage(package_root).free
    check.expect(current_free >= DYNAMIC_RESERVE_BYTES, "current disk free is below the 8 GiB reserve")
    metrics_path = Path(str(config["run_root"])) / "resource_metrics.jsonl"
    metrics = check.jsonl("resource_metrics", metrics_path)
    if metrics is None:
        metrics = []
    metric_ids = [str(row.get("job_id")) for row in metrics]
    check.expect(len(metric_ids) == len(set(metric_ids)), "resource metrics contain duplicate successful jobs")
    check.expect(set(metric_ids) == expected_ids, "resource metrics successful-job set differs")
    receipt_map = {row["job_id"]: row for row in receipt_rows}
    for metric in metrics:
        job_id = str(metric.get("job_id"))
        receipt = receipt_map.get(job_id)
        if receipt is None:
            continue
        check.expect(metric.get("status") == "PASS", f"resource metric is non-PASS {job_id}")
        check.expect(int(metric.get("artifact_bytes", -1)) == receipt["artifact_bytes"], f"resource artifact bytes differ {job_id}")
        check.expect(int(metric.get("peak_rss", -1)) == receipt["peak_process_group_rss_bytes"], f"resource peak RSS differs {job_id}")
        check.expect(int(metric.get("free_bytes", -1)) >= DYNAMIC_RESERVE_BYTES, f"completion disk reserve failed {job_id}")
    resource_timeline = audits.get("resource_timeline") or {}
    if resource_timeline:
        check.expect(
            nested(resource_timeline, "authorities", "completion_resource_metrics", "sha256")
            == (check.authorities.get("resource_metrics") or {}).get("sha256"),
            "resource timeline completion-metrics digest differs",
        )
    actual_workers = nested(resource_timeline, "actual_execution", "controller_workers")
    guard_sessions = nested(resource_timeline, "actual_execution", "guard_sessions") or {}
    manual_pressure = resource_timeline.get("manual_pressure_recovery_event") or {}
    historical_quota_core_sequence = manual_pressure.get("quota_core_sequence")
    check.expect(actual_workers == 4, "audited actual execution worker count differs from four")
    check.expect(guard_sessions.get("all_quotas_within_3_to_4_cores") is True, "audited execution quota left the 3-to-4 core band")
    check.expect(guard_sessions.get("all_throttled_sessions_restored_to_four") is True, "audited throttled session did not restore four cores")
    check.expect(has_four_three_four_quota_cycle(historical_quota_core_sequence), "historical manual 4-to-3-to-4 recovery event differs")
    timeline_receipts = nested(resource_timeline, "transport_receipts", "receipt_records") or []
    timeline_receipt_map = {
        str(row.get("job_id")): row for row in timeline_receipts
        if isinstance(row, dict)
    }
    finalizer_receipt_map = {str(row.get("job_id")): row for row in receipt_rows}
    if resource_timeline:
        check.expect(set(timeline_receipt_map) == set(finalizer_receipt_map), "resource timeline effective receipt set differs from finalizer receipts")
        for job_id, receipt in finalizer_receipt_map.items():
            timeline_receipt = timeline_receipt_map.get(job_id)
            if timeline_receipt is None:
                continue
            check.expect(timeline_receipt.get("receipt_sha256") == receipt.get("receipt_sha256"), f"resource timeline receipt digest differs {job_id}")
            check.expect(norm(timeline_receipt.get("receipt_path", "")) == norm(receipt.get("receipt_path", "")), f"resource timeline receipt path differs {job_id}")
            check.expect(timeline_receipt.get("peak_process_group_rss_bytes") == receipt.get("peak_process_group_rss_bytes"), f"resource timeline receipt peak RSS differs {job_id}")
            check.expect(timeline_receipt.get("sim_path_metadata") == receipt.get("sim_path"), f"resource timeline SIM path metadata differs {job_id}")
    return {
        "configured_max_cpu_budget_cores": 6,
        "configured_adaptive_workers": [4, 6],
        "actual_controller_workers_after_oomd_recovery": actual_workers,
        "historical_manual_quota_core_sequence": historical_quota_core_sequence,
        "guard_session_count": guard_sessions.get("session_count"),
        "guard_session_stage_coverage": guard_sessions.get("observed_closed_stage_coverage"),
        "guard_quota_core_interval": guard_sessions.get("allowed_quota_core_interval"),
        "all_guard_sessions_closed": guard_sessions.get("all_sessions_closed"),
        "safe_all_four_core_guard_session_is_PASS": guard_sessions.get("safe_all_four_core_session_is_PASS"),
        "artificial_throttle_required": guard_sessions.get("artificial_throttle_required"),
        "execution_summary": "MAXIMUM_6_CPU_BUDGET__ACTUAL_4_WORKERS__GUARD_QUOTA_BOUNDED_3_TO_4__HISTORICAL_MANUAL_4_TO_3_TO_4",
        "peak_cgroup_pressure": {
            "some_avg10_percent": manual_pressure.get("peak_some_avg10_percent"),
            "oomd_kill_gate_some_avg10_percent": manual_pressure.get("oomd_kill_gate_percent"),
        },
        "approximately_20s_after_pressure_peak": {
            "some_avg10_percent": manual_pressure.get("approximately_20_seconds_later_avg10_percent"),
        },
        "later_zero_avg10_recovery": {
            "some_avg10_percent": manual_pressure.get("later_avg10_percent"),
        },
        "pressure_guard_did_not_signal_or_terminate_workers": nested(resource_timeline, "pressure_guard_policy", "worker_signal_or_termination_action") is False,
        "MemAvailable_floor_bytes": MEMORY_FLOOR_BYTES,
        "SwapFree_floor_bytes": SWAP_FLOOR_BYTES,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "current_disk_free_bytes": current_free,
        "current_disk_reserve_pass": current_free >= DYNAMIC_RESERVE_BYTES,
        "completion_metric_rows": len(metrics),
        "max_receipt_process_group_rss_bytes": max((row["peak_process_group_rss_bytes"] for row in receipt_rows), default=0),
        "background_receipt_peak_RSS": (resource_timeline.get("background_receipts") or {}).get("maximum_peak_rss"),
        "background_per_family_peak_RSS": (resource_timeline.get("background_receipts") or {}).get("per_family_max_peak_rss"),
        "all_effective_transport_receipt_peak_RSS": (resource_timeline.get("transport_receipts") or {}).get("maximum_peak_rss"),
    }


def fullstat_disposition(topup_required: bool | None) -> str:
    if topup_required is True:
        return "PREPARE_PROMPT_BUILDUP_TOPUP_THEN_REBUILD_FULL_INVENTORY_AND_APPLY_DELAYED_MIXTURE_HARD_GATE"
    if topup_required is False:
        return "STOP__NO_FULLSTAT_TOPUP"
    return "WAITING__MISSION_GATE_NOT_AVAILABLE"


def validate_fullstat_contract(
    config: dict[str, Any], mission: dict[str, Any], check: Checker
) -> dict[str, Any]:
    contract_path = Path(str(nested(config, "fullstat", "topup_contract") or ""))
    rows = check.csv("fullstat_topup_contract", contract_path)
    if rows is not None:
        families = [row for row in rows if row.get("family") != "TOTAL"]
        total = [row for row in rows if row.get("family") == "TOTAL"]
        check.expect({row.get("family") for row in families} == set(FAMILIES), "full-stat top-up contract family closure differs")
        check.expect(len(total) == 1, "full-stat top-up contract TOTAL row differs")
        if total:
            check.expect(total[0].get("instant_increment_jobs") == "15_jobs", "full-stat instant increment jobs differ")
            check.expect(total[0].get("buildup_increment_jobs") == "13_jobs", "full-stat buildup increment jobs differ")
            check.expect(int(total[0].get("instant_increment", -1)) == 2_561_382, "full-stat instant increment differs")
            check.expect(int(total[0].get("buildup_increment", -1)) == 2_030_976, "full-stat buildup increment differs")
    check.expect(nested(config, "fullstat", "gate_max_central_R_F3") == FULLSTAT_GATE, "configured full-stat central gate differs")
    check.expect(nested(config, "fullstat", "default_delayed_policy") == "REBUILD_FULL_INVENTORY_AND_RERUN_FULL_250000", "full-stat delayed default policy differs")
    check.expect(nested(config, "fullstat", "delayed_full_rerun_triggers_per_positive_family") == 250_000, "full-stat delayed complete rerun events differ")
    required = mission.get("topup_required") if mission else None
    check.expect(required in (True, False, None), "mission top-up requirement is not boolean/unknown")
    decision = mission.get("decision") if mission else None
    expected = fullstat_disposition(required)
    known_outputs = [
        Path(str(config["package_root"])) / "audit/sf3_fullstat_topup_static_audit.json",
        Path(str(config["package_root"])) / "audit/sf3_fullstat_topup_transport_receipts.json",
        Path(str(config["package_root"])) / "data/sf3_fullstat_topup_job_plan.csv",
    ]
    preclosure_present = [norm(path) for path in known_outputs if path.exists()]
    check.expect(not preclosure_present, "conditional full-stat artifacts exist before write-once Plan-1 closure")
    return {
        "gate_metric": "central F3_SF3/F3_SE3",
        "observed_central_ratio": mission.get("central_F3_ratio") if mission else None,
        "threshold": FULLSTAT_GATE,
        "topup_required": required,
        "mission_decision": decision,
        "disposition_after_plan1_closure": expected,
        "proxy_controls_gate": False,
        "finalizer_triggered_transport_or_topup": False,
        "preclosure_topup_artifacts_present": preclosure_present,
        "if_required_delayed_default": "REBUILD_FULL_INVENTORY_THEN_FRESH_COMPLETE_250000_PER_POSITIVE_FAMILY",
        "screening_83334_plus_166666_default_merge": "FORBIDDEN",
    }


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    check = Checker()
    config_path = config_path.resolve()
    config = check.json("analysis_inputs", config_path)
    if config is None:
        return {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "NOT_READY__SF3_FINAL_CHAIN_INPUTS_INCOMPLETE",
            "ready": False,
            "checked_at": utc_now(),
            "missing": sorted(set(check.missing)),
            "errors": check.errors,
            "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__RECEIPT_METADATA_ONLY",
        }
    package_root = Path(str(config.get("package_root", config_path.parent))).resolve()
    run_root = Path(str(config.get("run_root", "")))
    output_root = Path(str(nested(config, "outputs", "stage_07") or package_root / "outputs/07_final_audit"))
    check.expect(config.get("profile_id") == PROFILE_ID, "profile_id differs")
    check.expect(package_root == config_path.parent, "package_root differs from config parent")
    check.expect(run_root.is_absolute(), "run_root is not absolute")
    check.expect(config.get("authority_boundary") == "PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN__NO_AUTOMATIC_PROMOTION", "Plan-1 authority boundary differs")
    w_contract = validate_w_contract(config, check)

    plan_path = Path(str(nested(config, "transport", "job_plan") or ""))
    seed_path = Path(str(nested(config, "transport", "seed_registry") or ""))
    plan_csv = check.csv("job_plan", plan_path)
    seed_csv = check.csv("seed_registry", seed_path)
    plan = cast_plan(plan_csv or [], check)
    if plan_csv is not None:
        validate_plan(plan, config, check)
    if seed_csv is not None and plan_csv is not None:
        validate_seed_registry(seed_csv, plan, check)
    stage_bindings, dispositions, stage_details = validate_stage_chain(config, plan, check)
    audits = validate_audits(config, plan, dispositions, check)
    receipt_rows, expected_ids, zero_ids = validate_receipts(
        config, plan, dispositions, audits, check
    )
    resources = validate_resource_contract(config, receipt_rows, expected_ids, audits, check)
    fullstat = validate_fullstat_contract(config, stage_details["mission"], check)

    source_validation = audits.get("source_validation") or {}
    if plan_path.is_file() and seed_path.is_file():
        check.expect(nested(source_validation, "plan", "plan_sha256") == sha256_small(plan_path), "source-validation job-plan digest differs")
        check.expect(nested(source_validation, "plan", "seed_registry_sha256") == sha256_small(seed_path), "source-validation seed-registry digest differs")
    output_exists = output_root.exists()
    if output_exists:
        check.errors.append(f"write-once stage07 output already exists: {output_root}")
    ready = not check.errors and not check.missing
    status = (
        "READY__SF3_PLAN1_FINAL_AUDIT"
        if ready
        else "FAIL__SF3_FINAL_CHAIN_CONTRACT"
        if check.errors
        else "NOT_READY__SF3_FINAL_CHAIN_INPUTS_INCOMPLETE"
    )
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "checked_at": utc_now(),
        "package_root": norm(package_root),
        "run_root": norm(run_root),
        "output_root": norm(output_root),
        "scope": "FRESH_SF3_PLAN1_NUMERATOR__FROZEN_47_SE3_SMALL_TABLE_DENOMINATOR",
        "plan": {
            "registered_jobs": len(plan),
            "background_jobs": EXPECTED_BACKGROUND_JOBS,
            "instant_histories": EXPECTED_INSTANT_HISTORIES,
            "buildup_histories": EXPECTED_BUILDUP_HISTORIES,
            "delayed_registered_cells": EXPECTED_DELAYED_REGISTERED,
            "delayed_RUN_83334_families": stage_details["run_families"],
            "delayed_SKIPPED_ZERO_A15_families": stage_details["zero_families"],
            "fresh_SF3_signal_jobs": 1,
            "fresh_SF3_signal_trials": EXPECTED_SIGNAL_EVENTS,
            "effective_receipt_count": len(expected_ids),
            "effective_job_ids": sorted(expected_ids),
            "zero_A15_receipt_exclusions": sorted(zero_ids),
        },
        "delayed_disposition_records": stage_details["disposition_records"],
        "stage_bindings": stage_bindings,
        "passive_w_contract": w_contract,
        "mission_results": stage_details["mission"],
        "fullstat_disposition": fullstat,
        "job_receipts": receipt_rows,
        "resource_contract": resources,
        "input_authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "errors": check.errors,
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__CANONICAL_RECEIPT_PATH_SIZE_HEADER_FIELDS_ONLY",
        "transport_or_topup_launched_by_finalizer": False,
        "authority_boundary": "PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN__NO_AUTOMATIC_GEOMETRY_PROMOTION",
    }


RECEIPT_FIELDS = (
    "job_id", "receipt_path", "receipt_sha256", "stage", "geometry", "mode",
    "family", "events", "seed", "attempt", "started_at", "ended_at",
    "source_path", "source_sha256", "setup_path", "header_geometry", "header_seed",
    "sim_path", "sim_bytes", "log_path", "log_bytes", "isotope_dat_bytes",
    "artifact_bytes", "peak_process_group_rss_bytes", "wall_s", "beam_on_cpu_s",
    "TT_s", "RP_record_count",
)


def csv_text(rows: Sequence[dict[str, Any]], fields: Iterable[str]) -> str:
    stream = io.StringIO(newline="")
    names = list(fields)
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in names})
    return stream.getvalue()


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def report_text(audit: dict[str, Any]) -> str:
    mission = audit["mission_results"]
    sf3 = mission.get("SF3") or {}
    se3 = mission.get("SE3") or {}
    fullstat = audit["fullstat_disposition"]
    plan = audit["plan"]
    resources = audit["resource_contract"]
    pressure_peak = resources.get("peak_cgroup_pressure") or {}
    pressure_20s = resources.get("approximately_20s_after_pressure_peak") or {}
    pressure_zero = resources.get("later_zero_avg10_recovery") or {}
    quota_sequence = resources.get("historical_manual_quota_core_sequence") or []
    quota_text = "→".join(str(value) for value in quota_sequence) or "N/A"
    lines = [
        "# SF3 Plan-1 final chain audit",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This closes the fresh SF3 approximately one-third screen against the frozen 47/SE3 small-table denominator. No SE3/S3d transport was rerun, and this finalizer did not open, stat, discover or hash a SIM payload.",
        "",
        "## Chain closure",
        "",
        "| Stage | Status | Summary |",
        "|---|---|---|",
    ]
    for stage in sorted(audit["stage_bindings"]):
        row = audit["stage_bindings"][stage]
        lines.append(f"| {stage} | {row['observed_status']} | `{row['summary_path']}` |")
    lines.extend([
        "",
        "## Central 20-day result and sole full-stat gate",
        "",
        "| Quantity | SF3 | Frozen SE3 |",
        "|---|---:|---:|",
        f"| Full-envelope selected rays | {fmt(sf3.get('signal_selected_events'))} / {EXPECTED_SIGNAL_EVENTS} | {fmt(se3.get('signal_selected_events'))} / {EXPECTED_SIGNAL_EVENTS} |",
        f"| Full-envelope Aeff (cm²) | {fmt(sf3.get('selected_effective_area_cm2'))} | {fmt(se3.get('selected_effective_area_cm2'))} |",
        f"| S20 (counts) | {fmt(sf3.get('source_counts_20d'))} | {fmt(se3.get('source_counts_20d'))} |",
        f"| B20 (counts) | {fmt(sf3.get('background_counts_20d'))} | {fmt(se3.get('background_counts_20d'))} |",
        f"| F3 central (ph cm⁻² s⁻¹) | {fmt(sf3.get('F3_20d_ph_cm2_s'))} | {fmt(se3.get('F3_20d_ph_cm2_s'))} |",
        f"| F3 componentwise proxy | {fmt(sf3.get('F3_20d_componentwise_proxy_ph_cm2_s'))} | {fmt(se3.get('F3_20d_componentwise_proxy_ph_cm2_s'))} |",
        "",
        f"Central F3 ratio SF3/SE3: **{fmt(fullstat['observed_central_ratio'])}**; threshold: **<= {FULLSTAT_GATE}**; decision: `{fullstat['mission_decision']}`. The componentwise proxy is reported only and never controls this gate.",
        "",
        f"Conditional disposition: `{fullstat['disposition_after_plan1_closure']}`. The finalizer launched neither transport nor top-up.",
        "",
        "## Transport closure",
        "",
        f"- 21 background jobs: {EXPECTED_INSTANT_HISTORIES:,} instant and {EXPECTED_BUILDUP_HISTORIES:,} buildup histories.",
        f"- Eight delayed cells registered: {len(plan['delayed_RUN_83334_families'])} RUN_83334 and {len(plan['delayed_SKIPPED_ZERO_A15_families'])} auditable SKIP_ZERO_A15.",
        f"- One fresh SF3 full-envelope signal: {EXPECTED_SIGNAL_EVENTS:,} rays.",
        f"- Effective canonical receipts: {plan['effective_receipt_count']}.",
        "- The three SF3 W volumes remain passive diagnostics, disjoint from the three-BGO plus three-plastic active veto.",
        "",
        "## Resource contract",
        "",
        f"- Configured ceiling: {resources['configured_max_cpu_budget_cores']} CPU cores with an adaptive {resources['configured_adaptive_workers'][0]}–{resources['configured_adaptive_workers'][1]} worker design; this is a budget, not the observed execution setting.",
        f"- Actual controller after systemd-oomd recovery: {resources['actual_controller_workers_after_oomd_recovery']} workers. The completed manual pressure episode used the observed quota sequence {quota_text}; all logged guard sessions stayed within {resources['guard_quota_core_interval']} cores and any throttle had to close restored at four cores.",
        f"- Guard-session coverage: {resources['guard_session_count']} closed sessions spanning {resources['guard_session_stage_coverage']}. A safe all-four-core session passes and no artificial throttle is required.",
        f"- Peak cgroup memory-pressure some avg10: {fmt(pressure_peak.get('some_avg10_percent'))}% against the recorded {fmt(pressure_peak.get('oomd_kill_gate_some_avg10_percent'))}% kill gate; approximately 20 s later: {fmt(pressure_20s.get('some_avg10_percent'))}%; later recovery: {fmt(pressure_zero.get('some_avg10_percent'))}%.",
        f"- MemAvailable floor: {resources['MemAvailable_floor_bytes']:,} bytes; SwapFree floor: {resources['SwapFree_floor_bytes']:,} bytes.",
        f"- Dynamic disk reserve: {resources['dynamic_disk_reserve_bytes']:,} bytes; final check free: {resources['current_disk_free_bytes']:,} bytes.",
        "- The pressure guard changed only aggregate CPUQuota, retained the four admitted workers, and did not signal or terminate a job.",
        "- GUI-disconnected partial attempts are retained in the recovery audit, excluded from statistics, and whole-job retries start from event zero with the registered seed.",
        "",
        f"Machine-readable audit: `{audit['final_paths']['final_audit']}`",
        f"Canonical receipt table: `{audit['final_paths']['job_receipts']}`",
        "",
    ])
    return "\n".join(lines)


def build(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    checked = check_prerequisites(config_path)
    if not checked.get("ready"):
        raise RuntimeError(json_text(checked))
    output = Path(str(checked["output_root"]))
    if output.exists():
        raise FileExistsError(f"write-once stage07 output exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".07_final_audit.work-", dir=output.parent))
    try:
        final_paths = {
            "final_audit": norm(output / "final_audit.json"),
            "job_receipts": norm(output / "job_receipts.csv"),
            "final_report": norm(output / "FINAL_REPORT.md"),
        }
        audit = dict(checked)
        audit.update({
            "status": "PASS__SF3_PLAN1_CHAIN_COMPLETE__CENTRAL_FULLSTAT_GATE_RECORDED",
            "ready": True,
            "finalized_at": utc_now(),
            "final_paths": final_paths,
            "write_contract": "ATOMIC_DIRECTORY_RENAME__WRITE_ONCE",
        })
        (work / "job_receipts.csv").write_text(
            csv_text(audit["job_receipts"], RECEIPT_FIELDS), encoding="utf-8"
        )
        (work / "FINAL_REPORT.md").write_text(report_text(audit), encoding="utf-8")
        (work / "final_audit.json").write_text(json_text(audit), encoding="utf-8")
        for path in work.iterdir():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        os.replace(work, output)
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            "schema_version": 1,
            "status": audit["status"],
            "output_root": norm(output),
            "final_paths": final_paths,
            "effective_receipt_count": audit["plan"]["effective_receipt_count"],
            "central_F3_SF3_over_SE3": audit["mission_results"]["central_F3_ratio"],
            "fullstat_topup_required": audit["fullstat_disposition"]["topup_required"],
            "fullstat_disposition": audit["fullstat_disposition"]["disposition_after_plan1_closure"],
            "transport_or_topup_launched_by_finalizer": False,
        }
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    """Exercise compact receipt, W and central-gate logic with no SIM access."""
    with tempfile.TemporaryDirectory(prefix="sf3_finalizer_selftest_") as temp:
        root = Path(temp)
        source = root / "synthetic.source"
        source.write_text("Geometry /synthetic/SF3.geo.setup\nSeed 11\n", encoding="utf-8")
        source_digest = sha256_small(source)
        receipt_path = root / "synthetic.json"
        job = {
            "job_id": "synthetic", "stage": "background", "geometry": "SF3",
            "mode": "instant", "family": "gamma", "events": 7, "seed": 11,
            "source_path": str(source), "setup_path": "/synthetic/SF3.geo.setup",
        }
        payload = {
            **job,
            "profile_id": PROFILE_ID, "status": "PASS", "errors": [],
            "returncode": 0, "watchdog_reason": "completed", "attempt": 1,
            "started_at": "2026-08-16T00:00:00+00:00",
            "ended_at": "2026-08-16T00:00:01+00:00",
            "source_sha256": source_digest,
            "sim_path": "/synthetic/not-opened.sim.gz",
            "log_path": "/synthetic/not-opened.log",
            "attempt_dir": "/synthetic/attempt01",
            "sim_bytes": 100, "log_bytes": 20, "isotope_dat_bytes": 3,
            "artifact_bytes": 123, "peak_process_group_rss_bytes": 50,
            "wall_s": 1.5,
            "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
            "sim_header": {
                "geometry": job["setup_path"], "seed": 11,
                "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST",
            },
            "log": {
                "generated_events": 7, "graphics_terminal_marker": True,
                "error_marker": False, "beam_on_cpu_s": 1.0,
            },
            "isotope_dat": {"TT_s": 2.0, "RP_record_count": 0, "terminal_EN": True},
        }
        receipt_path.write_text(json_text(payload), encoding="utf-8")
        checker = Checker()
        row = validate_receipt(job, load_small_json(receipt_path), receipt_path, checker)
        if checker.errors or row["artifact_bytes"] != 123:
            raise AssertionError(f"synthetic receipt fixture failed: {checker.errors}")
        try:
            load_small_json(root / "must-not-stat.sim.gz")
        except RuntimeError as exc:
            if "SIM payload access is forbidden" not in str(exc):
                raise
        else:
            raise AssertionError("SIM-path guard did not fail before filesystem access")
        for ratio, required, decision in (
            (0.75, True, "TOPUP_TO_S3D_FULL_STAT_REQUIRED"),
            (0.7500001, False, "STOP__NO_FULLSTAT_TOPUP"),
        ):
            observed_required = ratio <= FULLSTAT_GATE
            observed_decision = "TOPUP_TO_S3D_FULL_STAT_REQUIRED" if observed_required else "STOP__NO_FULLSTAT_TOPUP"
            if observed_required is not required or observed_decision != decision:
                raise AssertionError("central-only gate boundary self-test failed")
        if fullstat_disposition(None) != "WAITING__MISSION_GATE_NOT_AVAILABLE":
            raise AssertionError("missing mission gate did not retain the waiting disposition")
        if fullstat_disposition(False) != "STOP__NO_FULLSTAT_TOPUP":
            raise AssertionError("explicit non-top-up mission gate did not stop")
        if not has_four_three_four_quota_cycle([4, 3, 4]):
            raise AssertionError("dynamic 4-to-3-to-4 resource cycle was rejected")
        for invalid_cycle in ([4], [4, 3], [3, 4], [4, 5, 3, 4]):
            if has_four_three_four_quota_cycle(invalid_cycle):
                raise AssertionError(f"invalid resource quota cycle was accepted: {invalid_cycle}")
        safe_guard = {
            "allowed_quota_core_interval": [3, 4],
            "all_sessions_closed": True,
            "all_quotas_within_3_to_4_cores": True,
            "all_throttled_sessions_restored_to_four": True,
            "all_sampled_hard_floors_pass": True,
            "safe_all_four_core_session_is_PASS": True,
            "artificial_throttle_required": False,
        }
        if not valid_guard_session_summary(safe_guard):
            raise AssertionError("safe all-four-core guard-session contract was rejected")
        w_config = {
            "geometry": {
                "passive_w_volumes": list(PASSIVE_W_VOLUMES),
                "passive_w_never_active_veto": True,
                "shield_veto_volumes": ["B1", "B2", "B3"],
                "plastic_veto_volumes": ["P1", "P2", "P3"],
                "active_veto_volumes": ["B1", "B2", "B3", "P1", "P2", "P3"],
                "apply_plastic_veto": True,
            }
        }
        w_checker = Checker()
        validate_w_contract(w_config, w_checker)
        if w_checker.errors:
            raise AssertionError(f"passive-W contract fixture failed: {w_checker.errors}")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FINALIZER_SYNTHETIC_SMALL_AUTHORITY_SELF_TEST",
        "checks": [
            "compact_receipt_plan_header_seed_event_source_binding",
            "artifact_byte_metadata_closure",
            "SIM_path_rejected_before_stat_open_or_hash",
            "three_passive_W_volumes_disjoint_from_six_active_veto_volumes",
            "central_ratio_equal_0p75_triggers_topup",
            "central_ratio_above_0p75_stops_without_proxy_gate",
            "missing_mission_gate_waits_instead_of_stopping",
            "actual_four_worker_dynamic_quota_4_to_3_to_4_contract",
            "safe_all_four_core_guard_session_requires_no_artificial_throttle",
        ],
        "files_written_outside_temporary_directory": False,
        "sim_opened_statted_discovered_or_hashed": False,
        "transport_or_topup_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-prerequisites", action="store_true", help="read-only compact-authority readiness check")
    actions.add_argument("--build", action="store_true", help="atomically publish write-once outputs/07_final_audit")
    actions.add_argument("--self-test", action="store_true", help="run synthetic compact-authority tests in /tmp")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites:
            result = check_prerequisites(args.config)
        else:
            result = build(args.config)
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready", False):
            return 1 if result.get("errors") else 2
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "status": "FAIL__SF3_FINALIZER",
            "error": str(exc),
            "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__CANONICAL_RECEIPT_METADATA_ONLY",
            "transport_or_topup_launched_by_finalizer": False,
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
