#!/usr/bin/env python3
"""Prepare the conditional SF3 full-stat prompt/buildup top-up package.

This is deliberately a *static* append-only adapter.  It validates the exact
Section-10 CSV authority, derives fresh seeds, and can publish source cards and
explicit Plan-1-plus-top-up aggregation plans only after a completed mission
gate and final closure audit authorize the branch.  It never launches Cosima,
opens/stats/hashes SIM payloads, edits the 30-row Plan-1 registry, or constructs
delayed sources from the screening inventory.

The transport executor is intentionally outside this file.  Before any top-up
transport is launched, a separate runner must implement canonical receipts,
the 6-core/adaptive-memory gates, and the dynamic measured bytes/event disk
admission required by the SF3 handoff.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from build_sf3_sources import collect_occupied_seeds
from sf3_plan1_common import (
    CELL_ESTIMATED_BYTES,
    CORRECTED_TOKEN,
    DYNAMIC_RESERVE_BYTES,
    FAMILIES,
    FORBIDDEN_TOKEN,
    FULLSTAT_DELAYED_EVENTS,
    FULLSTAT_GATE_MAX_R_F3,
    FULLSTAT_INCREMENT_SHARDS,
    MODES,
    PACKAGE_ROOT,
    PROFILE_ID,
    RUN_ROOT,
    S3D_HISTORIES,
    SF3_PACKAGE,
    SF3_SETUP,
    SHARDS,
    base_source,
    derive_seed,
    sha256,
    utc_now,
    write_once_json,
    write_once_text,
)


AUTHORITY = PACKAGE_ROOT / "data/sf3_fullstat_topup_contract.csv"
UPSTREAM_AUTHORITY = SF3_PACKAGE / "data/sf3_fullstat_topup_contract.csv"
PLAN1_PLAN = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
PLAN1_SEEDS = PACKAGE_ROOT / "data/sf3_plan1_seed_registry.csv"
DEFAULT_MISSION_SUMMARY = PACKAGE_ROOT / "outputs/06_mission/summary.json"
DEFAULT_CLOSURE_AUDIT = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"

TOPUP_NAMESPACE = "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1"
TOPUP_RUN_ROOT = RUN_ROOT.parent / "sf3_fullstat_prompt_buildup_topup_v1"
TOPUP_PLAN = PACKAGE_ROOT / "data/sf3_fullstat_topup_job_plan.csv"
TOPUP_SEEDS = PACKAGE_ROOT / "data/sf3_fullstat_topup_seed_registry.csv"
TOPUP_SOURCES = PACKAGE_ROOT / "config/fullstat_topup_source_cards"
TOPUP_SOURCE_MANIFEST = PACKAGE_ROOT / "data/sf3_fullstat_topup_source_manifest.csv"
COMBINED_PLAN = PACKAGE_ROOT / "data/sf3_fullstat_combined_background_plan.csv"
AGGREGATION_PLAN = PACKAGE_ROOT / "data/sf3_fullstat_prompt_buildup_aggregation_plan.csv"
DELAYED_POLICY = PACKAGE_ROOT / "data/sf3_fullstat_delayed_rerun_policy.csv"
STATIC_AUDIT = PACKAGE_ROOT / "audit/sf3_fullstat_topup_static_audit.json"
TOPUP_RECEIPT_ROOT = PACKAGE_ROOT / "audit/fullstat_topup_receipts"
TOPUP_AGGREGATE_RECEIPT = PACKAGE_ROOT / "audit/sf3_fullstat_topup_transport_receipts.json"
TOPUP_RUNNER = PACKAGE_ROOT / "code/run_sf3_fullstat_topup.py"
TOPUP_RUNNER_SELF_TEST_STATUS = "PASS__SF3_FULLSTAT_TOPUP_CONTROLLER_STATIC_SELF_TEST"

EXPECTED_COLUMNS = (
    "family",
    "instant_full_target",
    "instant_validated_plan1",
    "instant_increment",
    "instant_increment_jobs",
    "buildup_full_target",
    "buildup_validated_plan1",
    "buildup_increment",
    "buildup_increment_jobs",
)

PLAN_FIELDS = (
    "ordinal",
    "job_id",
    "stage",
    "geometry",
    "mode",
    "family",
    "increment_shard",
    "events",
    "plan1_validated_histories",
    "full_target_histories",
    "seed",
    "seed_identity",
    "seed_namespace",
    "source_path",
    "setup_path",
    "run_root",
    "receipt_path",
    "aggregate_receipt_path",
    "estimated_bytes_from_plan1_calibration",
    "gate_authority_required",
    "transport_authorized_by_static_generator",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader)


def csv_text(rows: list[dict[str, Any]], fields: Iterable[str] | None = None) -> str:
    if not rows:
        raise RuntimeError("refusing to render empty CSV")
    names = list(fields or rows[0].keys())
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if set(row) != set(names):
            raise RuntimeError("CSV row schema drift")
        writer.writerow(row)
    return stream.getvalue()


def parse_positive_int(value: str, label: str) -> int:
    if not value or not value.isdigit() or int(value) <= 0:
        raise RuntimeError(f"{label} is not a positive decimal integer: {value!r}")
    return int(value)


def parse_job_expression(value: str, label: str) -> tuple[int, ...]:
    parts = tuple(parse_positive_int(token, label) for token in value.split("+"))
    if not parts:
        raise RuntimeError(f"empty shard expression for {label}")
    return parts


def validate_authority() -> dict[tuple[str, str], dict[str, Any]]:
    """Bind the exact upstream CSV and close every history/job invariant."""
    if not AUTHORITY.is_file() or not UPSTREAM_AUTHORITY.is_file():
        raise FileNotFoundError("missing local or upstream full-stat top-up authority")
    local = AUTHORITY.read_bytes()
    upstream = UPSTREAM_AUTHORITY.read_bytes()
    if local != upstream:
        raise RuntimeError("local full-stat top-up contract is not byte-identical to SF3 authority")

    with io.StringIO(local.decode("utf-8"), newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise RuntimeError(f"full-stat authority schema differs: {reader.fieldnames}")
        rows = list(reader)
    if [row["family"] for row in rows] != [*FAMILIES, "TOTAL"]:
        raise RuntimeError("full-stat authority family order/set differs")

    result: dict[tuple[str, str], dict[str, Any]] = {}
    mode_totals: dict[str, dict[str, int]] = {
        mode: {"full": 0, "plan1": 0, "increment": 0, "jobs": 0}
        for mode in MODES
    }
    for row in rows[:-1]:
        family = row["family"]
        for mode in MODES:
            full = parse_positive_int(row[f"{mode}_full_target"], f"{mode}/{family} full")
            plan1 = parse_positive_int(
                row[f"{mode}_validated_plan1"], f"{mode}/{family} Plan-1"
            )
            increment = parse_positive_int(
                row[f"{mode}_increment"], f"{mode}/{family} increment"
            )
            parts = parse_job_expression(
                row[f"{mode}_increment_jobs"], f"{mode}/{family} jobs"
            )
            expected_full = S3D_HISTORIES[(mode, family)]
            expected_plan1 = math.ceil(expected_full / 3)
            if full != expected_full or plan1 != expected_plan1:
                raise RuntimeError(f"full/Plan-1 authority mismatch for {mode}/{family}")
            if increment != full - plan1 or sum(parts) != increment:
                raise RuntimeError(f"increment closure failed for {mode}/{family}")
            if parts != FULLSTAT_INCREMENT_SHARDS[(mode, family)]:
                raise RuntimeError(f"literal/common shard mismatch for {mode}/{family}: {parts}")
            # Splitting is forbidden at <=100k.  Above 100k it is optional, but
            # every shard must remain >=100k whenever a split is used.
            if increment <= 100_000 and len(parts) != 1:
                raise RuntimeError(f"<=100k increment was split for {mode}/{family}")
            if increment > 100_000 and len(parts) > 1 and min(parts) < 100_000:
                raise RuntimeError(f">100k split has a sub-100k shard for {mode}/{family}")
            result[(mode, family)] = {
                "full": full,
                "plan1": plan1,
                "increment": increment,
                "parts": parts,
            }
            mode_totals[mode]["full"] += full
            mode_totals[mode]["plan1"] += plan1
            mode_totals[mode]["increment"] += increment
            mode_totals[mode]["jobs"] += len(parts)

    total = rows[-1]
    expected_totals = {
        "instant": {"full": 3_842_075, "plan1": 1_280_693, "increment": 2_561_382, "jobs": 15},
        "buildup": {"full": 3_046_468, "plan1": 1_015_492, "increment": 2_030_976, "jobs": 13},
    }
    if mode_totals != expected_totals:
        raise RuntimeError(f"full-stat aggregate totals differ: {mode_totals}")
    for mode in MODES:
        expected = expected_totals[mode]
        if parse_positive_int(total[f"{mode}_full_target"], f"TOTAL {mode} full") != expected["full"]:
            raise RuntimeError(f"TOTAL {mode} full differs")
        if parse_positive_int(total[f"{mode}_validated_plan1"], f"TOTAL {mode} Plan-1") != expected["plan1"]:
            raise RuntimeError(f"TOTAL {mode} Plan-1 differs")
        if parse_positive_int(total[f"{mode}_increment"], f"TOTAL {mode} increment") != expected["increment"]:
            raise RuntimeError(f"TOTAL {mode} increment differs")
        if total[f"{mode}_increment_jobs"] != f'{expected["jobs"]}_jobs':
            raise RuntimeError(f"TOTAL {mode} job count differs")
    return result


def load_small_json(path: Path, label: str) -> dict[str, Any]:
    """Open only named JSON authority files; never discover or inspect SIMs."""
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    # The file is already resolved by name.  This size guard applies to JSON
    # authorities only; no SIM path is ever accepted by this adapter.
    if path.suffix.lower() != ".json":
        raise RuntimeError(f"{label} must be JSON: {path}")
    payload = path.read_bytes()
    if len(payload) > 20_000_000:
        raise RuntimeError(f"refusing oversized {label}: {len(payload)} bytes")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} root is not an object")
    return value


def validate_runner_binding() -> dict[str, Any]:
    """Bind the separate controller and its no-transport static self-test.

    This proves that an executable runner exists without granting launch
    authority.  The prepared audit records the exact runner digest, and the
    runner rechecks that digest before production.
    """
    if not TOPUP_RUNNER.is_file():
        raise FileNotFoundError(f"missing independent full-stat runner: {TOPUP_RUNNER}")
    command = [sys.executable, "-B", str(TOPUP_RUNNER), "--self-test"]
    completed = subprocess.run(
        command,
        cwd=PACKAGE_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "full-stat runner static self-test failed: "
            f"returncode={completed.returncode}; stderr={completed.stderr[-2000:]}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("full-stat runner self-test did not emit one JSON object") from exc
    expected = {
        "status": TOPUP_RUNNER_SELF_TEST_STATUS,
        "cpu_budget": 6,
        "memory_headroom_floor_bytes": 1_610_612_736,
        "swap_free_floor_bytes": 8 * 1024**3,
        "dynamic_disk_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "production_artifacts_accessed": False,
        "SIM_accessed": False,
        "transport_launched": False,
    }
    differences = {
        key: {"expected": value, "observed": result.get(key)}
        for key, value in expected.items()
        if result.get(key) != value
    }
    if differences:
        raise RuntimeError(f"full-stat runner self-test contract differs: {differences}")
    return {
        "status": "PRESENT__STATIC_SELF_TEST_PASS__EXPLICIT_PHASE_REQUIRED_FOR_LAUNCH",
        "path": str(TOPUP_RUNNER),
        "sha256": sha256(TOPUP_RUNNER),
        "self_test_command": "python3 -B code/run_sf3_fullstat_topup.py --self-test",
        "self_test_status": result["status"],
        "self_test_transport_launched": False,
        "transport_authorized_by_static_adapter": False,
    }


def validate_gate(mission_path: Path, closure_path: Path) -> dict[str, Any]:
    mission = load_small_json(mission_path, "mission gate authority")
    closure = load_small_json(closure_path, "Plan-1 closure audit")
    if not str(mission.get("status", "")).startswith("PASS__"):
        raise RuntimeError("mission summary is not PASS")
    gate = mission.get("fullstat_gate")
    if not isinstance(gate, dict):
        raise RuntimeError("mission summary has no fullstat_gate object")
    if gate.get("metric") != "F3_SF3_over_SE3_full_envelope":
        raise RuntimeError("full-stat gate metric is not the central matched F3 ratio")
    if gate.get("operator") != "<=" or float(gate.get("threshold", -1)) != FULLSTAT_GATE_MAX_R_F3:
        raise RuntimeError("full-stat gate operator/threshold differs")
    ratio = float(gate.get("observed_central_ratio"))
    if not math.isfinite(ratio) or ratio < 0 or ratio > FULLSTAT_GATE_MAX_R_F3:
        raise RuntimeError(f"central full-stat gate did not authorize top-up: R_F3={ratio}")
    if gate.get("topup_required") is not True:
        raise RuntimeError("mission gate does not explicitly require top-up")
    if gate.get("decision") != "TOPUP_TO_S3D_FULL_STAT_REQUIRED":
        raise RuntimeError("mission gate decision string differs")
    if gate.get("proxy_controls_gate") is not False:
        raise RuntimeError("proxy was incorrectly made a top-up gate")

    if not str(closure.get("status", "")).startswith("PASS__"):
        raise RuntimeError("Plan-1 final closure audit is not PASS")
    if closure.get("ready") is False:
        raise RuntimeError("Plan-1 final closure audit says not ready")
    if closure.get("errors") not in (None, []):
        raise RuntimeError("Plan-1 final closure audit contains errors")
    if closure.get("missing") not in (None, []):
        raise RuntimeError("Plan-1 final closure audit contains missing authorities")
    boundary = str(closure.get("authority_boundary", ""))
    if "PLAN1" not in boundary or "NO_AUTOMATIC" not in boundary:
        raise RuntimeError("closure audit does not preserve the Plan-1/no-promotion boundary")
    return {
        "mission_path": str(mission_path),
        "mission_sha256": sha256(mission_path),
        "mission_status": mission["status"],
        "closure_path": str(closure_path),
        "closure_sha256": sha256(closure_path),
        "closure_status": closure["status"],
        "central_R_F3": ratio,
        "threshold": FULLSTAT_GATE_MAX_R_F3,
        "decision": gate["decision"],
        "proxy_controls_gate": False,
    }


def topup_job_id(mode: str, family: str, shard: int) -> str:
    return f"sf3_fullstat_topup_{mode}_{family}_inc_shard{shard:04d}"


def topup_run_name(mode: str, family: str, shard: int) -> str:
    return f"SF3_FULLSTAT_TOPUP_{mode}_{family}_{shard:04d}"


def topup_source_path(job_id: str) -> Path:
    return TOPUP_SOURCES / f"{job_id}.source"


def topup_active_prefix(job_id: str) -> Path:
    return TOPUP_RUN_ROOT / "jobs" / job_id / "active" / job_id


def topup_receipt_path(job_id: str) -> Path:
    return TOPUP_RECEIPT_ROOT / f"{job_id}.json"


def occupied_with_plan1() -> tuple[set[int], dict[str, Any]]:
    occupied, audit = collect_occupied_seeds()
    rows = read_csv(PLAN1_SEEDS)
    if len(rows) != 30:
        raise RuntimeError(f"SF3 Plan-1 seed registry must remain exactly 30 rows, got {len(rows)}")
    current = {parse_positive_int(row["seed"], f'Plan-1 seed {row.get("job_id")}') for row in rows}
    if len(current) != len(rows):
        raise RuntimeError("duplicate seed in SF3 Plan-1 seed registry")
    occupied.update(current)
    return occupied, {
        **audit,
        "sf3_plan1_seed_registry": str(PLAN1_SEEDS),
        "sf3_plan1_seed_registry_sha256": sha256(PLAN1_SEEDS),
        "sf3_plan1_seed_count": len(current),
        "occupied_seed_count_including_sf3_plan1": len(occupied),
    }


def derive_topup_seeds(
    contract: dict[tuple[str, str], dict[str, Any]], occupied: set[int]
) -> dict[str, int]:
    reserved = set(occupied)
    result: dict[str, int] = {}
    for mode in MODES:
        for family in FAMILIES:
            for shard in range(1, len(contract[(mode, family)]["parts"]) + 1):
                identity = topup_job_id(mode, family, shard)
                seed = derive_seed(identity, reserved, namespace=TOPUP_NAMESPACE)
                result[identity] = seed
                reserved.add(seed)
    if len(result) != 28 or len(set(result.values())) != 28:
        raise RuntimeError("expected 28 unique full-stat top-up seeds")
    if set(result.values()) & occupied:
        raise RuntimeError("top-up seed collision with frozen/current registries")
    return result


def build_topup_plan(
    contract: dict[tuple[str, str], dict[str, Any]], seeds: dict[str, int]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for mode in MODES:
        for family in FAMILIES:
            cell = contract[(mode, family)]
            for shard, events in enumerate(cell["parts"], 1):
                ordinal += 1
                job_id = topup_job_id(mode, family, shard)
                # Calibrate from the handoff's Plan-1 cell estimate, then force
                # the later runner to replace this with measured receipt data.
                estimate = int(round(
                    CELL_ESTIMATED_BYTES[(mode, family)] * events / cell["plan1"]
                ))
                row = {
                    "ordinal": ordinal,
                    "job_id": job_id,
                    "stage": "fullstat_topup_background",
                    "geometry": "SF3",
                    "mode": mode,
                    "family": family,
                    "increment_shard": shard,
                    "events": events,
                    "plan1_validated_histories": cell["plan1"],
                    "full_target_histories": cell["full"],
                    "seed": seeds[job_id],
                    "seed_identity": job_id,
                    "seed_namespace": TOPUP_NAMESPACE,
                    "source_path": str(topup_source_path(job_id)),
                    "setup_path": str(SF3_SETUP),
                    "run_root": str(TOPUP_RUN_ROOT),
                    "receipt_path": str(topup_receipt_path(job_id)),
                    "aggregate_receipt_path": str(TOPUP_AGGREGATE_RECEIPT),
                    "estimated_bytes_from_plan1_calibration": estimate,
                    "gate_authority_required": True,
                    # --prepare is static preparation, never launch authority.
                    "transport_authorized_by_static_generator": False,
                }
                if tuple(row) != PLAN_FIELDS:
                    raise RuntimeError("internal top-up plan schema drift")
                rows.append(row)
    if len(rows) != 28:
        raise RuntimeError(f"top-up plan is not 28 jobs: {len(rows)}")
    if sum(int(row["events"]) for row in rows if row["mode"] == "instant") != 2_561_382:
        raise RuntimeError("top-up instant plan total differs")
    if sum(int(row["events"]) for row in rows if row["mode"] == "buildup") != 2_030_976:
        raise RuntimeError("top-up buildup plan total differs")
    return rows


def _unique_index(lines: list[str], predicate, label: str) -> int:
    indices = [index for index, line in enumerate(lines) if predicate(line)]
    if len(indices) != 1:
        raise RuntimeError(f"base source requires exactly one {label}, got {len(indices)}")
    return indices[0]


def patch_topup_source(base_text: str, row: dict[str, Any]) -> str:
    mode = str(row["mode"])
    job_id = str(row["job_id"])
    run_name = topup_run_name(mode, str(row["family"]), int(row["increment_shard"]))
    seed = int(row["seed"])
    events = int(row["events"])
    lines = base_text.splitlines()
    geometry_i = _unique_index(lines, lambda x: x.strip().startswith("Geometry "), "Geometry")
    seed_i = _unique_index(lines, lambda x: x.strip().startswith("Seed "), "Seed")
    run_i = _unique_index(lines, lambda x: x.strip().startswith("Run "), "Run")
    decay_i = _unique_index(lines, lambda x: x.strip().startswith("DecayMode "), "DecayMode")
    _unique_index(lines, lambda x: x.strip() == "StoreSimulationInfo all", "StoreSimulationInfo")
    _unique_index(lines, lambda x: x.strip() == "StoreIsotopes true", "StoreIsotopes")
    old_run = lines[run_i].strip().split(maxsplit=1)[1]
    events_i = _unique_index(lines, lambda x: x.startswith(f"{old_run}.Events "), "Events")
    filename_i = _unique_index(lines, lambda x: x.startswith(f"{old_run}.FileName "), "FileName")
    isotope_i = _unique_index(
        lines, lambda x: x.startswith(f"{old_run}.IsotopeProductionFile "), "IsotopeProductionFile"
    )
    prefix = topup_active_prefix(job_id)
    patched: list[str] = []
    for index, raw in enumerate(lines):
        if index == geometry_i:
            patched.append(f"Geometry {SF3_SETUP}")
        elif index == seed_i:
            patched.append(f"Seed {seed}")
        elif index == run_i:
            patched.append(f"Run {run_name}")
        elif index == decay_i and mode == "instant":
            continue
        elif index == events_i:
            patched.append(f"{run_name}.Events {events}")
        elif index == filename_i:
            patched.append(f"{run_name}.FileName {prefix}")
        elif index == isotope_i:
            patched.append(f"{run_name}.IsotopeProductionFile {prefix}.dat")
        elif raw.startswith(f"{old_run}."):
            patched.append(run_name + raw[len(old_run):])
        else:
            patched.append(raw)
    text = "\n".join(patched) + "\n"
    validate_topup_source(text, row)
    return text


def validate_topup_source(text: str, row: dict[str, Any]) -> None:
    job_id = str(row["job_id"])
    mode = str(row["mode"])
    run_name = topup_run_name(mode, str(row["family"]), int(row["increment_shard"]))
    prefix = topup_active_prefix(job_id)
    exact = lambda value: sum(line.strip() == value for line in text.splitlines())
    required = (
        f"Geometry {SF3_SETUP}",
        f"Seed {row['seed']}",
        f"Run {run_name}",
        f"{run_name}.Events {row['events']}",
        f"{run_name}.FileName {prefix}",
        f"{run_name}.IsotopeProductionFile {prefix}.dat",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
    )
    bad = {item: exact(item) for item in required if exact(item) != 1}
    if bad:
        raise RuntimeError(f"top-up source control mismatch: {bad}")
    if exact("DecayMode ActivationBuildUp") != (1 if mode == "buildup" else 0):
        raise RuntimeError("top-up DecayMode mismatch")
    if text.count(".Spectrum File ") != 20 or text.count(CORRECTED_TOKEN) != 20:
        raise RuntimeError("top-up corrected-keV 20-spectrum contract failed")
    if FORBIDDEN_TOKEN in text:
        raise RuntimeError("legacy factor-1000 spectrum token found in top-up source")
    if text.count(f"{run_name}.Source ") != 20 or text.count("Beam FarFieldAreaSource") != 20:
        raise RuntimeError("top-up source does not preserve the 20-source equal-mu model")
    if "mono511" in text.lower() or "mono_511" in text.lower():
        raise RuntimeError("forbidden additive mono-511 source marker found")
    if str(TOPUP_RUN_ROOT) not in text or str(RUN_ROOT / "jobs") in text:
        raise RuntimeError("top-up source output namespace is not isolated from Plan-1")


def plan1_background_rows() -> list[dict[str, str]]:
    rows = read_csv(PLAN1_PLAN)
    if len(rows) != 30:
        raise RuntimeError(f"Plan-1 job plan must remain 30 rows, got {len(rows)}")
    background = [row for row in rows if row["stage"] == "background"]
    if len(background) != 21:
        raise RuntimeError(f"Plan-1 background plan must remain 21 rows, got {len(background)}")
    if any(row["geometry"] != "SF3" for row in background):
        raise RuntimeError("Plan-1 background plan contains non-SF3 geometry")
    return background


def build_combined_and_aggregation(
    contract: dict[tuple[str, str], dict[str, Any]],
    plan1: list[dict[str, str]],
    topup: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    combined: list[dict[str, Any]] = []
    for namespace, rows in (("PLAN1_CANONICAL_PASS", plan1), ("FULLSTAT_TOPUP_NEW", topup)):
        for row in rows:
            combined.append({
                "combined_ordinal": len(combined) + 1,
                "source_namespace": namespace,
                "job_id": row["job_id"],
                "geometry": "SF3",
                "mode": row["mode"],
                "family": row["family"],
                "events": int(row["events"]),
                "seed": int(row["seed"]),
                "source_path": row["source_path"],
                "receipt_authority": (
                    str(PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json")
                    if namespace == "PLAN1_CANONICAL_PASS" else row["receipt_path"]
                ),
                "aggregation_role": "RETAIN_EXISTING_CANONICAL_PASS" if namespace == "PLAN1_CANONICAL_PASS" else "APPEND_NEW_TOPUP",
            })
    if len(combined) != 49 or len({row["job_id"] for row in combined}) != 49:
        raise RuntimeError("combined Plan-1 plus top-up job identity closure failed")

    aggregation: list[dict[str, Any]] = []
    for mode in MODES:
        for family in FAMILIES:
            old = [row for row in plan1 if row["mode"] == mode and row["family"] == family]
            new = [row for row in topup if row["mode"] == mode and row["family"] == family]
            cell = contract[(mode, family)]
            old_events = sum(int(row["events"]) for row in old)
            new_events = sum(int(row["events"]) for row in new)
            if old_events != cell["plan1"] or new_events != cell["increment"]:
                raise RuntimeError(f"combined cell closure failed for {mode}/{family}")
            aggregation.append({
                "mode": mode,
                "family": family,
                "plan1_job_ids": "+".join(row["job_id"] for row in old),
                "plan1_histories": old_events,
                "topup_job_ids": "+".join(str(row["job_id"]) for row in new),
                "topup_histories": new_events,
                "combined_histories": old_events + new_events,
                "full_target_histories": cell["full"],
                "plan1_receipt_authority": str(PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"),
                "topup_receipt_authority": str(TOPUP_AGGREGATE_RECEIPT),
                "downstream_role": (
                    "FULL_PROMPT_RESPONSE_INPUT"
                    if mode == "instant"
                    else "FULL_BUILDUP_RP_TT_INPUT_FOR_REBUILT_INVENTORY"
                ),
                "do_not_pool_across_mode_family_geometry": True,
            })
    if len(aggregation) != 16:
        raise RuntimeError("expected 16 mode/family aggregation rows")
    return combined, aggregation


def delayed_policy_rows() -> list[dict[str, Any]]:
    return [{
        "geometry": "SF3",
        "family": family,
        "decision_point": "AFTER_FULL_BUILDUP_RP_TT_AND_REBUILT_EXACT_POSITION_INVENTORY",
        "if_full_inventory_positive": "RUN_FRESH_COMPLETE_250000",
        "fresh_delayed_triggers": FULLSTAT_DELAYED_EVENTS,
        "if_full_inventory_zero": "SKIP_ZERO_A15_WITH_FINITE_UPPER_PROVENANCE",
        "plan1_83334_role": "SCREENING_AUTHORITY_ONLY__DO_NOT_POOL",
        "forbidden_default_merge": "83334_PLUS_166666",
        "incremental_merge_allowed": False,
        "incremental_merge_missing_gates": "source_support_inclusion+importance_reweight+original_transport_Bq+mixture_TV+ESS+lineage_closure",
        "source_cards_generated_by_this_adapter": False,
    } for family in FAMILIES]


def build_static_payloads() -> dict[str, Any]:
    contract = validate_authority()
    occupied, seed_audit = occupied_with_plan1()
    seeds = derive_topup_seeds(contract, occupied)
    topup = build_topup_plan(contract, seeds)
    sources: dict[Path, str] = {}
    source_rows: list[dict[str, Any]] = []
    for row in topup:
        source = base_source(str(row["family"]))
        text = patch_topup_source(source.read_text(encoding="utf-8"), row)
        path = Path(str(row["source_path"]))
        sources[path] = text
        source_rows.append({
            "job_id": row["job_id"],
            "mode": row["mode"],
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "source_path": str(path),
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "setup_path": str(SF3_SETUP),
            "corrected_references": text.count(CORRECTED_TOKEN),
            "legacy_references": text.count(FORBIDDEN_TOKEN),
            "transport_launched": False,
        })
    plan1 = plan1_background_rows()
    combined, aggregation = build_combined_and_aggregation(contract, plan1, topup)
    delayed = delayed_policy_rows()
    if set(seeds.values()) & {int(row["seed"]) for row in plan1}:
        raise RuntimeError("top-up/Plan-1 background seed collision")
    return {
        "contract": contract,
        "seed_audit": seed_audit,
        "seeds": seeds,
        "topup": topup,
        "sources": sources,
        "source_rows": source_rows,
        "combined": combined,
        "aggregation": aggregation,
        "delayed": delayed,
    }


def self_test() -> dict[str, Any]:
    payloads = build_static_payloads()
    runner_binding = validate_runner_binding()
    topup = payloads["topup"]
    # Render every output in memory.  No package output is created by self-test.
    csv_text(topup, PLAN_FIELDS)
    csv_text(payloads["source_rows"])
    csv_text(payloads["combined"])
    csv_text(payloads["aggregation"])
    csv_text(payloads["delayed"])
    if any(path.exists() for path in payloads["sources"]):
        # Existing exact outputs are allowed after an authorized --prepare, but
        # self-test must still prove that it is not the writer.
        existing_note = "EXISTING_PREPARED_SOURCES_LEFT_UNCHANGED"
    else:
        existing_note = "NO_TOPUP_SOURCES_PRESENT__SELF_TEST_WROTE_NOTHING"
    return {
        "status": "PASS__SF3_FULLSTAT_TOPUP_STATIC_ADAPTER_SELF_TEST",
        "authority_sha256": sha256(AUTHORITY),
        "topup_jobs": len(topup),
        "instant_jobs": sum(row["mode"] == "instant" for row in topup),
        "buildup_jobs": sum(row["mode"] == "buildup" for row in topup),
        "instant_increment_histories": sum(int(row["events"]) for row in topup if row["mode"] == "instant"),
        "buildup_increment_histories": sum(int(row["events"]) for row in topup if row["mode"] == "buildup"),
        "combined_background_jobs": len(payloads["combined"]),
        "aggregation_cells": len(payloads["aggregation"]),
        "delayed_policy_families": len(payloads["delayed"]),
        "delayed_positive_family_policy": "FRESH_COMPLETE_250000_ONLY",
        "topup_seed_count": len(payloads["seeds"]),
        "topup_seed_collisions": [],
        "source_cards_validated_in_memory": len(payloads["sources"]),
        "side_effect": existing_note,
        "sim_access_policy": "NO_SIM_DISCOVERY_OPEN_STAT_OR_HASH",
        "transport_launched": False,
        "runner_status": runner_binding["status"],
        "runner_binding": runner_binding,
    }


def prepare(mission_path: Path, closure_path: Path) -> dict[str, Any]:
    gate = validate_gate(mission_path, closure_path)
    payloads = build_static_payloads()
    runner_binding = validate_runner_binding()
    topup = payloads["topup"]

    # Fully render/validate all small artifacts before the first append-only
    # publication.  Existing Plan-1 plan/seed/source/receipt paths are never
    # write targets in this function.
    rendered = {
        TOPUP_PLAN: csv_text(topup, PLAN_FIELDS),
        TOPUP_SEEDS: csv_text([{
            "job_id": row["job_id"],
            "seed_identity": row["seed_identity"],
            "seed": row["seed"],
            "namespace": TOPUP_NAMESPACE,
            "collision_with_prior_or_plan1": False,
        } for row in topup]),
        TOPUP_SOURCE_MANIFEST: csv_text(payloads["source_rows"]),
        COMBINED_PLAN: csv_text(payloads["combined"]),
        AGGREGATION_PLAN: csv_text(payloads["aggregation"]),
        DELAYED_POLICY: csv_text(payloads["delayed"]),
        **payloads["sources"],
    }
    forbidden_targets = {PLAN1_PLAN.resolve(), PLAN1_SEEDS.resolve()}
    if forbidden_targets & {path.resolve() for path in rendered}:
        raise RuntimeError("internal error: attempted to target Plan-1 write-once authority")
    for path, text in rendered.items():
        write_once_text(path, text)

    audit = {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED",
        "created_at": utc_now(),
        "profile_id": PROFILE_ID,
        "topup_namespace": TOPUP_NAMESPACE,
        "gate_authorization": gate,
        "contract": {
            "local": str(AUTHORITY),
            "upstream": str(UPSTREAM_AUTHORITY),
            "byte_identical": True,
            "sha256": sha256(AUTHORITY),
        },
        "plan": {
            "path": str(TOPUP_PLAN),
            "sha256": sha256(TOPUP_PLAN),
            "jobs": 28,
            "instant_jobs": 15,
            "buildup_jobs": 13,
            "instant_increment_histories": 2_561_382,
            "buildup_increment_histories": 2_030_976,
        },
        "seed_registry": {
            "path": str(TOPUP_SEEDS),
            "sha256": sha256(TOPUP_SEEDS),
            "namespace": TOPUP_NAMESPACE,
            "count": 28,
            "collisions": [],
            "prior_authority": payloads["seed_audit"],
        },
        "sources": {
            "manifest": str(TOPUP_SOURCE_MANIFEST),
            "count": 28,
            "all_sf3_setup": True,
            "corrected_references": 560,
            "legacy_references": 0,
            "source_namespace": str(TOPUP_SOURCES),
            "run_namespace": str(TOPUP_RUN_ROOT),
        },
        "aggregation": {
            "combined_plan": str(COMBINED_PLAN),
            "combined_jobs": 49,
            "cell_plan": str(AGGREGATION_PLAN),
            "cells": 16,
            "plan1_receipts_retained_append_only": True,
            "pooling_boundary": "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY",
        },
        "delayed": {
            "policy": str(DELAYED_POLICY),
            "inventory": "MUST_REBUILD_FROM_FULL_BUILDUP_RP_TT_AT_ACTUAL_POSITIONS",
            "positive_family_default": "FRESH_COMPLETE_250000",
            "screening_83334_role": "SCREENING_ONLY__DO_NOT_POOL",
            "merge_83334_plus_166666": "FORBIDDEN_BY_DEFAULT",
            "delayed_source_cards_generated": False,
        },
        "resource_gate": {
            "must_be_recomputed_by_runner_from_sf3_measured_bytes_per_event_and_rss": True,
            "formula": "free_bytes >= projected_remaining_bytes*1.02 + auxiliary_overhead + 8_GiB",
            "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            "static_adapter_performed_launch_admission": False,
        },
        "transport": {
            "launched": False,
            "runner_status": runner_binding["status"],
            "runner_binding": runner_binding,
            "receipt_namespace": str(TOPUP_RECEIPT_ROOT),
            "aggregate_receipt": str(TOPUP_AGGREGATE_RECEIPT),
        },
        "plan1_mutation": False,
        "sim_access_policy": "NO_SIM_DISCOVERY_OPEN_STAT_OR_HASH__SMALL_CSV_JSON_AND_SOURCE_ONLY",
        "authority_boundary": "CONDITIONAL_FULLSTAT_PREPARATION_ONLY__NO_AUTOMATIC_GEOMETRY_PROMOTION",
    }
    write_once_json(STATIC_AUDIT, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true", help="validate entirely in memory; publish nothing")
    actions.add_argument("--prepare", action="store_true", help="publish append-only static package after strict gate")
    parser.add_argument("--mission-summary", type=Path, default=DEFAULT_MISSION_SUMMARY)
    parser.add_argument("--closure-audit", type=Path, default=DEFAULT_CLOSURE_AUDIT)
    args = parser.parse_args()
    result = self_test() if args.self_test else prepare(args.mission_summary, args.closure_audit)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
