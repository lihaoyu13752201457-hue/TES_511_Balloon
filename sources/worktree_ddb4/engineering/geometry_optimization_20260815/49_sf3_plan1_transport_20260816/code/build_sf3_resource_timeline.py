#!/usr/bin/env python3
"""Build the compact SF3 Plan-1 execution-resource timeline audit.

This adapter reads only the canonical Plan-1 CSV, compact JSON/JSONL control
records, and canonical receipt JSON metadata.  A receipt may name a SIM as
metadata, but this program never opens, stats, discovers, decompresses, or
hashes any SIM payload.  It never calls systemctl and cannot change a running
service.

``--check-prerequisites`` is read-only.  ``--build`` publishes exactly one
write-once JSON audit only after all effective Plan-1 transport receipts, the
background guard, and all five registered followup guard sessions close.
Quotas must stay in
the 3--4 core band and any throttle must restore four cores; a safe session
that remains at four cores passes without manufacturing a throttle event.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "audit/sf3_resource_timeline_audit.json"
PLAN_PATH = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
GUARD_PATH = PACKAGE_ROOT / "code/guard_sf3_service_pressure.py"
FOLLOWUP_MANIFEST_PATH = PACKAGE_ROOT / "data/sf3_plan1_followup_execution_manifest.json"
STAGE02_SUMMARY_PATH = PACKAGE_ROOT / "outputs/02_activation/day15_summary.json"
STAGE02_SOURCE_INDEX_PATH = PACKAGE_ROOT / "outputs/02_activation/delayed_source_index.csv"
MANUAL_QUOTA_AUDIT_PATH = PACKAGE_ROOT / "audit/sf3_manual_quota_recovery_20260816.json"
FOLLOWUP_PRESSURE_LOG_PATH = PACKAGE_ROOT / "audit/sf3_plan1_followup_pressure_guard.jsonl"

RECOVERY_PATHS = (
    (
        "controller_gui_recovery",
        PACKAGE_ROOT / "audit/controller_interruption_recovery_20260816.json",
    ),
    (
        "controller_external_recovery",
        PACKAGE_ROOT
        / "audit/controller_interruption_recovery_20260816T031021.json",
    ),
    (
        "systemd_oomd_recovery",
        PACKAGE_ROOT / "audit/systemd_oomd_recovery_20260816T032354.json",
    ),
)

PROFILE_ID = "SF3_PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN"
EXPECTED_PLAN_ROWS = 30
EXPECTED_BACKGROUND_JOBS = 21
EXPECTED_INSTANT_JOBS = 11
EXPECTED_BUILDUP_JOBS = 10
EXPECTED_DELAYED_CELLS = 8
EXPECTED_SIGNAL_JOBS = 1
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
FOLLOWUP_SESSION_LABELS = (
    "build_prompt",
    "transport_delayed",
    "analyze_delayed",
    "transport_signal",
    "build_common_response",
)

MAX_CPU_BUDGET_CORES = 6
ACTUAL_CONTROLLER_WORKERS = 4
NORMAL_QUOTA_PERCENT = 400
THROTTLE_QUOTA_PERCENT = 300
OOMD_KILL_GATE_SOME_AVG10_PERCENT = 50.0
NEAR_OOMD_GATE_MIN_PERCENT = 40.0
MEMORY_FLOOR_BYTES = 1_610_612_736
SWAP_FLOOR_BYTES = 8 * 1024**3
DYNAMIC_DISK_RESERVE_BYTES = 8 * 1024**3

MAX_SMALL_BYTES = 64 * 1024**2
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")
PASS_STATUS = (
    "PASS__SF3_RESOURCE_TIMELINE_ALL_EFFECTIVE_TRANSPORT_"
    "RECEIPTS_AND_RESOURCE_SESSIONS"
)


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


def reject_sim_payload_path(path: str | Path) -> None:
    """Reject a SIM path before making any filesystem query about it."""
    lower = os.fspath(path).lower()
    if lower.endswith(SIM_SUFFIXES):
        raise RuntimeError(f"SIM payload access is forbidden: {path}")


def read_small_bytes(path: Path) -> bytes:
    reject_sim_payload_path(path)
    with path.open("rb") as handle:
        payload = handle.read(MAX_SMALL_BYTES + 1)
    if not payload or len(payload) > MAX_SMALL_BYTES:
        raise RuntimeError(
            f"compact authority must contain 1..{MAX_SMALL_BYTES} bytes: {path}"
        )
    return payload


def authority_record(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": norm(path),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def parse_json_bytes(payload: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(
        payload.decode("utf-8"), parse_constant=reject_nonfinite
    )
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return value


def parse_jsonl_bytes(payload: bytes, path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line, parse_constant=reject_nonfinite)
        if not isinstance(value, dict):
            raise RuntimeError(f"JSONL row {line_number} is not an object: {path}")
        rows.append(value)
    if not rows:
        raise RuntimeError(f"compact JSONL contains no records: {path}")
    return rows


def parse_csv_bytes(payload: bytes, path: Path) -> list[dict[str, str]]:
    with io.StringIO(payload.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV header missing: {path}")
        return list(reader)


def parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} timestamp is invalid: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} timestamp lacks a UTC offset: {value}")
    return parsed.astimezone(timezone.utc)


def finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} is non-finite")
    return result


def exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} is boolean, not an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not an integer: {value!r}") from exc
    if str(value).strip() not in {str(result), f"{result}.0"} and not isinstance(value, int):
        raise ValueError(f"{label} is not an exact integer: {value!r}")
    return result


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
        self.pending: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def wait_for(self, condition: bool, message: str) -> None:
        if not condition:
            self.pending.append(message)

    def _bytes(self, label: str, path: Path) -> bytes | None:
        reject_sim_payload_path(path)
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            payload = read_small_bytes(path)
            self.authorities[label] = authority_record(path, payload)
            return payload
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def json(self, label: str, path: Path) -> dict[str, Any] | None:
        payload = self._bytes(label, path)
        if payload is None:
            return None
        try:
            return parse_json_bytes(payload, path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def jsonl(self, label: str, path: Path) -> list[dict[str, Any]] | None:
        payload = self._bytes(label, path)
        if payload is None:
            return None
        try:
            return parse_jsonl_bytes(payload, path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def csv(self, label: str, path: Path) -> list[dict[str, str]] | None:
        payload = self._bytes(label, path)
        if payload is None:
            return None
        try:
            return parse_csv_bytes(payload, path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def source(self, label: str, path: Path) -> str | None:
        payload = self._bytes(label, path)
        if payload is None:
            return None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            self.errors.append(f"{label} is not UTF-8: {exc}")
            return None


def cast_plan(rows: Sequence[dict[str, str]], check: Checker) -> list[dict[str, Any]]:
    cast: list[dict[str, Any]] = []
    required = {
        "ordinal", "job_id", "stage", "geometry", "mode", "family",
        "events", "seed", "source_path", "setup_path",
    }
    for index, row in enumerate(rows, 1):
        missing = sorted(required - set(row))
        if missing:
            check.errors.append(f"plan row {index} lacks columns {missing}")
            continue
        try:
            item: dict[str, Any] = dict(row)
            for key in ("ordinal", "events", "seed"):
                item[key] = exact_int(row[key], f"plan row {index} {key}")
            cast.append(item)
        except Exception as exc:
            check.errors.append(f"plan row {index} invalid: {exc}")
    return cast


def validate_plan(plan: Sequence[dict[str, Any]], check: Checker) -> list[dict[str, Any]]:
    check.expect(len(plan) == EXPECTED_PLAN_ROWS, "canonical plan does not contain 30 rows")
    check.expect(
        [row.get("ordinal") for row in plan] == list(range(1, EXPECTED_PLAN_ROWS + 1)),
        "canonical plan ordinals are not exactly 1..30",
    )
    ids = [str(row.get("job_id")) for row in plan]
    check.expect(len(ids) == len(set(ids)), "canonical plan job IDs are not unique")
    background = [row for row in plan if row.get("stage") == "background"]
    check.expect(len(background) == EXPECTED_BACKGROUND_JOBS, "background plan closure is not 21 jobs")
    check.expect(
        sum(row.get("mode") == "instant" for row in background) == EXPECTED_INSTANT_JOBS,
        "background instant plan closure is not 11 jobs",
    )
    check.expect(
        sum(row.get("mode") == "buildup" for row in background) == EXPECTED_BUILDUP_JOBS,
        "background buildup plan closure is not 10 jobs",
    )
    for row in background:
        job_id = str(row.get("job_id"))
        check.expect(row.get("geometry") == "SF3", f"background plan geometry differs: {job_id}")
        check.expect(row.get("mode") in {"instant", "buildup"}, f"background mode differs: {job_id}")
        check.expect(row.get("family") in FAMILIES, f"background family differs: {job_id}")
        check.expect(int(row.get("events", 0)) > 0, f"background events are nonpositive: {job_id}")
        check.expect(int(row.get("seed", 0)) > 0, f"background seed is nonpositive: {job_id}")
    return background


def validate_delayed_dispositions(
    summary: dict[str, Any] | None,
    rows: Sequence[dict[str, str]],
    plan: Sequence[dict[str, Any]],
    check: Checker,
) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    """Close eight registered cells and derive the effective delayed jobs."""
    delayed_plan = {
        str(row.get("family")): row for row in plan if row.get("stage") == "delayed"
    }
    selected = [row for row in rows if row.get("geometry") == "SF3"]
    check.expect(len(delayed_plan) == EXPECTED_DELAYED_CELLS, "canonical plan delayed cells are not 8")
    check.expect(len(selected) == EXPECTED_DELAYED_CELLS, "stage02 delayed source-index rows are not 8")
    check.expect(
        {str(row.get("incident_family")) for row in selected} == set(FAMILIES),
        "stage02 delayed source-index family closure differs",
    )
    dispositions: dict[str, str] = {}
    for row in selected:
        family = str(row.get("incident_family"))
        disposition = str(row.get("execution_disposition"))
        dispositions[family] = disposition
        check.expect(
            disposition in {"RUN_83334", "SKIP_ZERO_A15"},
            f"stage02 delayed disposition differs: {family}",
        )
        plan_row = delayed_plan.get(family)
        check.expect(plan_row is not None, f"stage02 family absent from delayed plan: {family}")
        if disposition == "RUN_83334":
            try:
                check.expect(
                    finite_float(row.get("transported_ground_activity_Bq"), f"{family} A15") > 0.0,
                    f"RUN_83334 family has nonpositive A15: {family}",
                )
            except Exception as exc:
                check.errors.append(str(exc))
        elif disposition == "SKIP_ZERO_A15":
            try:
                check.expect(
                    finite_float(row.get("transported_ground_activity_Bq") or 0.0, f"{family} zero A15") == 0.0,
                    f"SKIP_ZERO_A15 family has nonzero central A15: {family}",
                )
                check.expect(
                    finite_float(
                        row.get("transported_ground_A15_upper95_Bq_conservative"),
                        f"{family} finite A15 upper",
                    ) > 0.0,
                    f"SKIP_ZERO_A15 family lacks a finite positive upper: {family}",
                )
                check.expect(bool(row.get("zero_A15_upper_provenance")), f"SKIP_ZERO_A15 provenance is absent: {family}")
            except Exception as exc:
                check.errors.append(str(exc))
    run_rows = [delayed_plan[family] for family in FAMILIES if dispositions.get(family) == "RUN_83334"]
    zero_rows = [delayed_plan[family] for family in FAMILIES if dispositions.get(family) == "SKIP_ZERO_A15"]
    if summary:
        check.expect(summary.get("status") == "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY", "stage02 activation summary status differs")
        check.expect(summary.get("registered_delayed_source_cells") == EXPECTED_DELAYED_CELLS, "stage02 registered delayed cells differ")
        check.expect(summary.get("delayed_transport_jobs_planned") == len(run_rows), "stage02 positive delayed job count differs")
        check.expect(summary.get("delayed_zero_source_jobs_skipped") == len(zero_rows), "stage02 zero-A15 skip count differs")
        check.expect(set(summary.get("zero_source_families") or []) == {row["family"] for row in zero_rows}, "stage02 zero-A15 family list differs")
    return dispositions, run_rows, zero_rows


def effective_plan_rows(
    plan: Sequence[dict[str, Any]], delayed_run_rows: Sequence[dict[str, Any]],
    check: Checker,
) -> list[dict[str, Any]]:
    background = [row for row in plan if row.get("stage") == "background"]
    signal = [row for row in plan if row.get("stage") == "signal"]
    check.expect(len(background) == EXPECTED_BACKGROUND_JOBS, "effective plan background closure differs")
    check.expect(len(signal) == EXPECTED_SIGNAL_JOBS, "effective plan signal closure differs")
    effective = [*background, *delayed_run_rows, *signal]
    check.expect(
        len({str(row.get("job_id")) for row in effective}) == len(effective),
        "effective transport plan contains duplicate job IDs",
    )
    return effective


def validate_config(config: dict[str, Any], config_path: Path, check: Checker) -> tuple[Path, Path]:
    package_root = Path(str(config.get("package_root", "")))
    run_root = Path(str(config.get("run_root", "")))
    check.expect(config.get("profile_id") == PROFILE_ID, "resource config profile_id differs")
    check.expect(norm(package_root) == norm(config_path.parent), "resource config package_root differs from config parent")
    check.expect(norm(config_path.parent) == norm(PACKAGE_ROOT), "resource adapter is not bound to package 49")
    check.expect(run_root.is_absolute(), "resource config run_root is not absolute")
    transport = config.get("transport") or {}
    check.expect(transport.get("cpu_budget") == MAX_CPU_BUDGET_CORES, "configured CPU budget differs from 6")
    check.expect(transport.get("max_cpu_budget") == MAX_CPU_BUDGET_CORES, "configured maximum CPU budget differs from 6")
    check.expect(transport.get("adaptive_min_workers") == 4, "configured adaptive minimum differs from 4")
    check.expect(transport.get("adaptive_live_target_workers") == 6, "configured adaptive target differs from 6")
    check.expect(transport.get("memory_headroom_bytes") == MEMORY_FLOOR_BYTES, "configured MemAvailable floor differs from 1.5 GiB")
    check.expect(transport.get("aggressive_min_swap_free_bytes") == SWAP_FLOOR_BYTES, "configured SwapFree floor differs from 8 GiB")
    check.expect(transport.get("dynamic_reserve_bytes") == DYNAMIC_DISK_RESERVE_BYTES, "configured dynamic disk reserve differs from 8 GiB")
    check.expect(norm(transport.get("job_plan", "")) == norm(PLAN_PATH), "configured job plan path differs")
    return package_root, run_root


def _eval_static(node: ast.AST, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool)):
        return node.value
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_static(node.operand, names)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _eval_static(node.left, names)
        right = _eval_static(node.right, names)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "int"
        and len(node.args) == 1
        and not node.keywords
    ):
        return int(_eval_static(node.args[0], names))
    raise ValueError(f"unsupported static expression: {ast.dump(node)}")


def guard_policy(source: str, check: Checker) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        check.errors.append(f"pressure guard source is not valid Python: {exc}")
        return {}
    names: dict[str, Any] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            names[target.id] = _eval_static(statement.value, names)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    expected = {
        "MEM_FLOOR_BYTES": MEMORY_FLOOR_BYTES,
        "SWAP_FLOOR_BYTES": SWAP_FLOOR_BYTES,
        "THROTTLE_SOME_AVG10": 15.0,
        "THROTTLE_FULL_AVG10": 10.0,
        "RESTORE_AVG10": 2.0,
        "DEFAULT_NORMAL_QUOTA": NORMAL_QUOTA_PERCENT,
        "DEFAULT_THROTTLE_QUOTA": THROTTLE_QUOTA_PERCENT,
        "DEFAULT_SAFE_SAMPLES": 6,
    }
    for key, value in expected.items():
        check.expect(names.get(key) == value, f"pressure guard static constant differs: {key}")
    check.expect("CPUQuota=" in source, "pressure guard lacks aggregate CPUQuota action")
    check.expect("os.kill(" not in source, "pressure guard contains os.kill")
    check.expect("send_signal(" not in source, "pressure guard contains send_signal")
    check.expect("terminate(" not in source, "pressure guard contains terminate")
    return {
        "normal_quota_percent": names.get("DEFAULT_NORMAL_QUOTA"),
        "throttle_quota_percent": names.get("DEFAULT_THROTTLE_QUOTA"),
        "throttle_some_avg10_percent": names.get("THROTTLE_SOME_AVG10"),
        "throttle_full_avg10_percent": names.get("THROTTLE_FULL_AVG10"),
        "restore_avg10_percent": names.get("RESTORE_AVG10"),
        "safe_samples_to_restore": names.get("DEFAULT_SAFE_SAMPLES"),
        "action_scope": "AGGREGATE_CPU_QUOTA_ONLY__FOUR_ADMITTED_WORKERS_REMAIN",
        "worker_signal_or_termination_action": False,
    }


def _validate_floor_snapshot(snapshot: Any, prefix: str, check: Checker) -> None:
    if not isinstance(snapshot, dict):
        check.errors.append(f"{prefix} resource snapshot missing")
        return
    check.expect(snapshot.get("pass") is True, f"{prefix} resource snapshot is not PASS")
    check.expect(snapshot.get("mem_floor_bytes") == MEMORY_FLOOR_BYTES, f"{prefix} memory floor differs")
    check.expect(snapshot.get("swap_floor_bytes") == SWAP_FLOOR_BYTES, f"{prefix} swap floor differs")
    check.expect(snapshot.get("disk_reserve_bytes") == DYNAMIC_DISK_RESERVE_BYTES, f"{prefix} disk reserve differs")
    try:
        check.expect(int(snapshot.get("mem_available_bytes", -1)) >= MEMORY_FLOOR_BYTES, f"{prefix} MemAvailable breached floor")
        check.expect(int(snapshot.get("swap_free_bytes", -1)) >= SWAP_FLOOR_BYTES, f"{prefix} SwapFree breached floor")
        check.expect(int(snapshot.get("disk_free_bytes", -1)) >= DYNAMIC_DISK_RESERVE_BYTES, f"{prefix} disk reserve breached")
    except (TypeError, ValueError):
        check.errors.append(f"{prefix} resource snapshot contains non-integer byte fields")


def validate_recoveries(recoveries: dict[str, dict[str, Any] | None], check: Checker) -> dict[str, Any]:
    gui = recoveries.get("controller_gui_recovery")
    if gui:
        check.expect(gui.get("status") == "PASS__SF3_INTERRUPTED_PARTIALS_AUDITED_FOR_RECOVERY", "GUI recovery status differs")
        check.expect(gui.get("cause") == "GPT_GUI_AND_OWNING_PTY_DISCONNECTED", "GUI recovery cause differs")
        check.expect(gui.get("statistics_policy") == "FAILED_PARTIALS_EXCLUDED", "GUI failed partials were not excluded")
        check.expect(gui.get("partial_sim_digest_policy") == "NOT_HASHED_BY_CONTRACT", "GUI partial SIMs were hashed")
        _validate_floor_snapshot(gui.get("resource_gate_at_recovery"), "GUI recovery", check)
    external = recoveries.get("controller_external_recovery")
    if external:
        check.expect(external.get("status") == "PASS__SF3_INTERRUPTED_PARTIALS_AUDITED_FOR_RECOVERY", "external controller recovery status differs")
        check.expect(external.get("statistics_policy") == "INTERRUPTED_PARTIALS_EXCLUDED", "external interrupted partials were not excluded")
        check.expect(external.get("partial_sim_digest_policy") == "NOT_HASHED_BY_CONTRACT", "external interrupted SIMs were hashed")
        check.expect((external.get("process_audit") or {}).get("cosima_workers_alive") == 0, "external recovery retained interrupted workers")
        _validate_floor_snapshot(external.get("resource_gate_at_recovery"), "external controller recovery", check)
    oomd = recoveries.get("systemd_oomd_recovery")
    stability: dict[str, Any] = {}
    if oomd:
        check.expect(oomd.get("status") == "PASS__SF3_SYSTEMD_OOMD_INTERRUPTION_AUDITED_FOR_FOUR_WORKER_RECOVERY", "systemd-oomd recovery status differs")
        check.expect(oomd.get("statistics_policy") == "INTERRUPTED_PARTIALS_EXCLUDED", "systemd-oomd partials were not excluded")
        check.expect(oomd.get("partial_sim_digest_policy") == "NOT_HASHED_BY_CONTRACT", "systemd-oomd interrupted SIMs were hashed")
        stability = oomd.get("stability_policy_change") or {}
        check.expect(stability.get("old_controller_cpu_budget") == 6, "pre-oomd controller budget differs from 6")
        check.expect(stability.get("intermediate_systemd_cpu_quota_cores") == 5, "intermediate recovery quota differs from 5 cores")
        check.expect(stability.get("new_controller_cpu_budget") == ACTUAL_CONTROLLER_WORKERS, "post-oomd controller did not use 4 workers")
        check.expect(stability.get("new_systemd_cpu_quota_cores") == 4, "post-oomd systemd quota did not start at 4 cores")
        check.expect(stability.get("global_oom_protection_disabled") is False, "global OOM protection was disabled")
        _validate_floor_snapshot(oomd.get("resource_snapshot_after_kill"), "systemd-oomd recovery", check)
    return {
        "recovery_records": 3,
        "failed_or_interrupted_partials_excluded": True,
        "whole_job_event_zero_retry_policy": True,
        "initial_maximum_controller_budget_cores": stability.get("old_controller_cpu_budget"),
        "post_oomd_actual_controller_workers": stability.get("new_controller_cpu_budget"),
        "post_oomd_initial_quota_cores": stability.get("new_systemd_cpu_quota_cores"),
        "global_oom_protection_disabled": stability.get("global_oom_protection_disabled"),
    }


def _compressed(values: Iterable[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if not result or result[-1] != value:
            result.append(value)
    return result


def _normalize_pressure_row(
    row: dict[str, Any], source_label: str, index: int, check: Checker,
) -> dict[str, Any] | None:
    label = f"{source_label} row {index}"
    try:
        reasons = row.get("decision_reasons")
        if not isinstance(reasons, list) or not all(isinstance(value, str) for value in reasons):
            raise ValueError(f"{label} decision_reasons is invalid")
        if reasons == ["guard_exit_restore_failed"] or row.get("error"):
            raise ValueError(f"{label} records a failed quota restoration")
        unit = str(row.get("unit"))
        if not re.fullmatch(r"sf3-plan1-[a-z0-9_-]+\.service", unit):
            raise ValueError(f"{label} has an unapproved unit: {unit}")
        session_label = row.get("session_label")
        if source_label == "followup_pressure_guard_metrics":
            if session_label not in FOLLOWUP_SESSION_LABELS:
                raise ValueError(f"{label} has an unregistered followup session_label: {session_label!r}")
        elif session_label is None:
            session_label = "background_transport"
        quota = exact_int(row.get("quota_percent"), f"{label} quota_percent")
        if not THROTTLE_QUOTA_PERCENT <= quota <= NORMAL_QUOTA_PERCENT:
            raise ValueError(f"{label} quota is outside the allowed 3-to-4 core band")
        changed = row.get("quota_changed")
        if not isinstance(changed, bool):
            raise ValueError(f"{label} quota_changed is not boolean")
        terminal_restore = "guard_exit_restore_normal" in reasons
        pressure = row.get("cgroup_pressure")
        sampled = isinstance(pressure, dict)
        sample = {
            "at": parse_time(row.get("at"), label),
            "at_text": row.get("at"),
            "unit": unit,
            "session_label": str(session_label),
            "unit_state": str(row.get("unit_state", "")),
            "quota_percent": quota,
            "quota_changed": changed,
            "reasons": reasons,
            "safe_streak": exact_int(row.get("safe_streak", 0), f"{label} safe_streak"),
            "terminal_restore": terminal_restore,
            "sampled": sampled,
            "some_avg10": None,
            "full_avg10": None,
            "mem_available_bytes": None,
            "swap_free_bytes": None,
        }
        if sampled:
            sample.update({
                "some_avg10": finite_float(pressure.get("some_avg10"), f"{label} some_avg10"),
                "full_avg10": finite_float(pressure.get("full_avg10"), f"{label} full_avg10"),
                "mem_available_bytes": exact_int(row.get("mem_available_bytes"), f"{label} MemAvailable"),
                "swap_free_bytes": exact_int(row.get("swap_free_bytes"), f"{label} SwapFree"),
            })
            if exact_int(row.get("mem_floor_bytes"), f"{label} memory floor") != MEMORY_FLOOR_BYTES:
                raise ValueError(f"{label} memory floor differs")
            if exact_int(row.get("swap_floor_bytes"), f"{label} swap floor") != SWAP_FLOOR_BYTES:
                raise ValueError(f"{label} swap floor differs")
            if sample["mem_available_bytes"] < MEMORY_FLOOR_BYTES:
                raise ValueError(f"{label} MemAvailable floor breached")
            if sample["swap_free_bytes"] < SWAP_FLOOR_BYTES:
                raise ValueError(f"{label} SwapFree floor breached")
        elif not terminal_restore:
            raise ValueError(f"{label} lacks pressure/floor fields outside a terminal restore event")
        return sample
    except Exception as exc:
        check.errors.append(str(exc))
        return None


def _split_pressure_sessions(samples: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    sessions: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for sample in samples:
        if current and (
            sample["unit"] != current[-1]["unit"]
            or sample["session_label"] != current[-1]["session_label"]
            or current[-1]["terminal_restore"]
            or current[-1]["unit_state"] == "inactive"
        ):
            sessions.append(current)
            current = []
        current.append(sample)
        if sample["terminal_restore"] or sample["unit_state"] == "inactive":
            sessions.append(current)
            current = []
    if current:
        sessions.append(current)
    return sessions


def analyze_pressure_logs(
    logs: Sequence[tuple[str, Sequence[dict[str, Any]]]],
    receipt_records: Sequence[dict[str, Any]],
    require_stage_coverage: set[str],
    required_followup_session_labels: set[str],
    check: Checker,
) -> dict[str, Any]:
    normalized: list[tuple[str, dict[str, Any]]] = []
    for source_label, rows in logs:
        for index, row in enumerate(rows, 1):
            sample = _normalize_pressure_row(row, source_label, index, check)
            if sample is not None:
                normalized.append((source_label, sample))
    sessions: list[dict[str, Any]] = []
    for source_label in dict.fromkeys(label for label, _ in normalized):
        source_samples = [sample for label, sample in normalized if label == source_label]
        for ordinal, samples in enumerate(_split_pressure_sessions(source_samples), 1):
            for index in range(1, len(samples)):
                check.expect(samples[index]["at"] > samples[index - 1]["at"], f"{source_label} session {ordinal} timestamps are not increasing")
                changed = samples[index]["quota_percent"] != samples[index - 1]["quota_percent"]
                check.expect(samples[index]["quota_changed"] is changed, f"{source_label} session {ordinal} quota_changed disagrees with observed transition")
            sequence = _compressed(sample["quota_percent"] for sample in samples)
            closed = (
                samples[-1]["unit_state"] == "inactive"
                or (
                    samples[-1]["terminal_restore"]
                    and samples[-1]["quota_percent"] == NORMAL_QUOTA_PERCENT
                )
            )
            check.wait_for(closed, f"{source_label} session {ordinal} is not closed by inactive or guard_exit_restore_normal")
            if min(sequence) < NORMAL_QUOTA_PERCENT:
                check.expect(sequence[-1] == NORMAL_QUOTA_PERCENT, f"{source_label} session {ordinal} throttled but did not restore four cores")
            sampled = [sample for sample in samples if sample["sampled"]]
            check.expect(bool(sampled), f"{source_label} session {ordinal} has no pressure/floor samples")
            start = samples[0]["at"]
            end = samples[-1]["at"]
            covered_jobs: list[str] = []
            covered_stages: set[str] = set()
            for receipt in receipt_records:
                try:
                    receipt_start = parse_time(receipt["started_at"], f"{receipt['job_id']} receipt start")
                    receipt_end = parse_time(receipt["ended_at"], f"{receipt['job_id']} receipt end")
                except Exception as exc:
                    check.errors.append(str(exc))
                    continue
                if receipt_start <= end and receipt_end >= start:
                    covered_jobs.append(str(receipt["job_id"]))
                    covered_stages.add(str(receipt["stage"]))
            peak = max(sampled, key=lambda sample: sample["some_avg10"], default=None)
            sessions.append({
                "source_log": source_label,
                "session_ordinal_in_log": ordinal,
                "unit": samples[0]["unit"],
                "session_label": samples[0]["session_label"],
                "started_at": samples[0]["at_text"],
                "closed_at": samples[-1]["at_text"],
                "closure": (
                    "UNIT_INACTIVE"
                    if samples[-1]["unit_state"] == "inactive"
                    else "GUARD_EXIT_RESTORE_NORMAL"
                    if samples[-1]["terminal_restore"]
                    else "OPEN"
                ),
                "closed": closed,
                "sample_count": len(sampled),
                "quota_percent_sequence": sequence,
                "quota_core_sequence": [value / 100.0 for value in sequence],
                "quota_within_3_to_4_cores": all(300 <= value <= 400 for value in sequence),
                "throttle_observed": min(sequence) < NORMAL_QUOTA_PERCENT,
                "terminal_four_core_quota": sequence[-1] == NORMAL_QUOTA_PERCENT,
                "covered_job_ids": sorted(covered_jobs),
                "covered_stages": sorted(covered_stages),
                "peak_some_avg10_percent": None if peak is None else peak["some_avg10"],
                "peak_full_avg10_percent": None if peak is None else max(sample["full_avg10"] for sample in sampled),
                "minimum_MemAvailable_bytes": min((sample["mem_available_bytes"] for sample in sampled), default=None),
                "minimum_SwapFree_bytes": min((sample["swap_free_bytes"] for sample in sampled), default=None),
                "all_sampled_hard_floors_pass": all(
                    sample["mem_available_bytes"] >= MEMORY_FLOOR_BYTES
                    and sample["swap_free_bytes"] >= SWAP_FLOOR_BYTES
                    for sample in sampled
                ),
            })
    covered_stages = {
        stage for session in sessions if session["closed"]
        for stage in session["covered_stages"]
    }
    for stage in sorted(require_stage_coverage):
        check.wait_for(stage in covered_stages, f"closed pressure-guard session has not yet covered {stage} transport")
    observed_followup_labels = {
        str(session["session_label"])
        for session in sessions
        if session["source_log"] == "followup_pressure_guard_metrics"
        and session["closed"]
    }
    for label in sorted(required_followup_session_labels):
        check.wait_for(label in observed_followup_labels, f"followup pressure-guard session is not closed: {label}")
    required_label_stage_coverage = {
        "background_transport": "background",
        "transport_signal": "signal",
    }
    if "delayed" in require_stage_coverage:
        required_label_stage_coverage["transport_delayed"] = "delayed"
    observed_label_stage_coverage = {
        label: sorted({
            stage
            for session in sessions
            if session["closed"] and session["session_label"] == label
            for stage in session["covered_stages"]
        })
        for label in sorted(required_label_stage_coverage)
    }
    label_stage_bindings_pass = True
    for label, stage in sorted(required_label_stage_coverage.items()):
        bound = observed_label_stage_coverage[label] == [stage]
        label_stage_bindings_pass = label_stage_bindings_pass and bound
        check.wait_for(
            bound,
            f"closed pressure-guard session {label!r} does not overlap only its exact {stage!r} receipt stage",
        )
    check.wait_for(bool(sessions), "no pressure-guard sessions are available")
    return {
        "log_count": len(logs),
        "session_count": len(sessions),
        "actual_controller_workers": ACTUAL_CONTROLLER_WORKERS,
        "allowed_quota_core_interval": [3, 4],
        "all_sessions_closed": bool(sessions) and all(session["closed"] for session in sessions),
        "all_quotas_within_3_to_4_cores": bool(sessions) and all(session["quota_within_3_to_4_cores"] for session in sessions),
        "all_throttled_sessions_restored_to_four": all(
            (not session["throttle_observed"]) or session["terminal_four_core_quota"]
            for session in sessions
        ),
        "all_sampled_hard_floors_pass": bool(sessions) and all(session["all_sampled_hard_floors_pass"] for session in sessions),
        "required_stage_coverage": sorted(require_stage_coverage),
        "observed_closed_stage_coverage": sorted(covered_stages),
        "required_followup_session_labels": sorted(required_followup_session_labels),
        "observed_closed_followup_session_labels": sorted(observed_followup_labels),
        "required_exact_label_stage_coverage": required_label_stage_coverage,
        "observed_closed_exact_label_stage_coverage": observed_label_stage_coverage,
        "all_required_exact_label_stage_bindings_pass": label_stage_bindings_pass,
        "safe_all_four_core_session_is_PASS": True,
        "artificial_throttle_required": False,
        "sessions": sessions,
    }


def validate_manual_quota_audit(payload: dict[str, Any] | None, check: Checker) -> dict[str, Any]:
    if not payload:
        return {}
    check.expect(payload.get("status") == "PASS__SF3_MANUAL_QUOTA_PRESSURE_RECOVERY_AUDITED", "manual quota recovery audit status differs")
    check.expect(payload.get("actual_controller_workers") == ACTUAL_CONTROLLER_WORKERS, "manual quota recovery worker count differs")
    quota = payload.get("quota_recovery") or {}
    check.expect(quota.get("quota_core_sequence") == [4, 3, 4], "manual quota recovery sequence differs")
    check.expect(quota.get("restored_quota_cores") == 4, "manual quota recovery did not restore four cores")
    check.expect(quota.get("worker_count_changed") is False, "manual quota recovery changed worker count")
    check.expect(quota.get("job_terminated_by_recovery_action") is False, "manual quota recovery terminated a job")
    pressure = payload.get("pressure_recovery") or {}
    peak = finite_float(pressure.get("pre_throttle_avg10_percent"), "manual pressure peak")
    gate = finite_float(pressure.get("systemd_oomd_kill_gate_percent"), "manual pressure kill gate")
    after = finite_float(pressure.get("approximately_20_seconds_later_avg10_percent"), "manual 20-second pressure")
    later = finite_float(pressure.get("later_avg10_percent"), "manual later pressure")
    check.expect(math.isclose(peak, 43.42, abs_tol=1.0e-12), "manual pressure peak differs from 43.42%")
    check.expect(math.isclose(gate, 50.0, abs_tol=1.0e-12) and peak < gate, "manual pressure did not remain below the 50% kill gate")
    check.expect(math.isclose(after, 3.67, abs_tol=1.0e-12), "manual approximately-20-second pressure differs from 3.67%")
    check.expect(math.isclose(later, 0.0, abs_tol=1.0e-12), "manual later pressure did not recover to zero")
    check.expect(payload.get("service_mutated_by_audit") is False, "manual audit itself mutated a service")
    return {
        "event_occurred": True,
        "event_is_not_a_requirement_to_force_future_throttling": True,
        "actual_controller_workers": ACTUAL_CONTROLLER_WORKERS,
        "quota_core_sequence": quota.get("quota_core_sequence"),
        "peak_some_avg10_percent": peak,
        "oomd_kill_gate_percent": gate,
        "approximately_20_seconds_later_avg10_percent": after,
        "later_avg10_percent": later,
        "job_terminated_by_recovery_action": quota.get("job_terminated_by_recovery_action"),
    }


def validate_receipt(
    receipt: dict[str, Any], plan_row: dict[str, Any], receipt_path: Path,
    authority: dict[str, Any], check: Checker,
) -> dict[str, Any] | None:
    job_id = str(plan_row["job_id"])
    try:
        check.expect(receipt.get("status") == "PASS", f"background receipt is not PASS: {job_id}")
        check.expect(receipt.get("profile_id") == PROFILE_ID, f"background receipt profile differs: {job_id}")
        check.expect(receipt.get("job_id") == job_id, f"background receipt job ID differs: {job_id}")
        stage = str(plan_row["stage"])
        check.expect(receipt.get("stage") == stage, f"transport receipt stage differs: {job_id}")
        check.expect(receipt.get("geometry") == "SF3", f"background receipt geometry differs: {job_id}")
        check.expect(receipt.get("mode") == plan_row["mode"], f"background receipt mode differs: {job_id}")
        check.expect(receipt.get("family") == plan_row["family"], f"background receipt family differs: {job_id}")
        check.expect(exact_int(receipt.get("events"), f"{job_id} events") == plan_row["events"], f"background receipt events differ: {job_id}")
        check.expect(exact_int(receipt.get("seed"), f"{job_id} seed") == plan_row["seed"], f"background receipt seed differs: {job_id}")
        check.expect(receipt.get("returncode") == 0, f"background receipt return code differs: {job_id}")
        check.expect(receipt.get("errors") == [], f"background receipt errors are nonempty: {job_id}")
        check.expect(receipt.get("watchdog_reason") == "completed", f"background receipt watchdog outcome differs: {job_id}")
        check.expect(norm(receipt.get("source_path", "")) == norm(plan_row["source_path"]), f"background source path differs: {job_id}")
        check.expect(norm(receipt.get("setup_path", "")) == norm(plan_row["setup_path"]), f"background setup path differs: {job_id}")
        check.expect(receipt.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", f"background SIM digest policy differs: {job_id}")
        header = receipt.get("sim_header") or {}
        check.expect(header.get("policy") == "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST", f"background SIM header policy differs: {job_id}")
        check.expect(norm(header.get("geometry", "")) == norm(plan_row["setup_path"]), f"background SIM header geometry differs: {job_id}")
        check.expect(exact_int(header.get("seed"), f"{job_id} header seed") == plan_row["seed"], f"background SIM header seed differs: {job_id}")
        sim_path = str(receipt.get("sim_path", ""))
        check.expect(sim_path.lower().endswith(".sim.gz"), f"background receipt SIM metadata path suffix differs: {job_id}")
        check.expect(job_id in os.path.basename(sim_path), f"background receipt SIM metadata basename differs: {job_id}")
        # The SIM string is intentionally never passed to Path.is_file/stat/open/hash.
        peak = exact_int(receipt.get("peak_process_group_rss_bytes"), f"{job_id} peak RSS")
        sim_bytes = exact_int(receipt.get("sim_bytes"), f"{job_id} SIM byte metadata")
        artifact_bytes = exact_int(receipt.get("artifact_bytes"), f"{job_id} artifact bytes")
        check.expect(peak > 0, f"background peak RSS is nonpositive: {job_id}")
        check.expect(sim_bytes > 0, f"background SIM byte metadata is nonpositive: {job_id}")
        check.expect(artifact_bytes >= sim_bytes, f"background artifact bytes are smaller than SIM metadata: {job_id}")
        started = parse_time(receipt.get("started_at"), f"{job_id} started_at")
        ended = parse_time(receipt.get("ended_at"), f"{job_id} ended_at")
        check.expect(ended > started, f"background receipt interval is nonpositive: {job_id}")
        return {
            "job_id": job_id,
            "stage": stage,
            "mode": plan_row["mode"],
            "family": plan_row["family"],
            "events": plan_row["events"],
            "seed": plan_row["seed"],
            "attempt": receipt.get("attempt"),
            "started_at": receipt.get("started_at"),
            "ended_at": receipt.get("ended_at"),
            "peak_process_group_rss_bytes": peak,
            "peak_process_group_rss_GiB": peak / 1024**3,
            "artifact_bytes": artifact_bytes,
            "receipt_path": norm(receipt_path),
            "receipt_sha256": authority["sha256"],
            "sim_path_metadata": sim_path,
            "sim_bytes_metadata": sim_bytes,
            "sim_accessed_or_hashed": False,
        }
    except Exception as exc:
        check.errors.append(f"background receipt invalid {job_id}: {exc}")
        return None


def summarize_receipts(records: Sequence[dict[str, Any]], expected_jobs: int) -> dict[str, Any]:
    per_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    per_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        per_cell[(record["mode"], record["family"])].append(record)
        per_family[record["family"]].append(record)
    maximum = max(records, key=lambda record: record["peak_process_group_rss_bytes"], default=None)
    return {
        "planned_jobs": expected_jobs,
        "validated_jobs": len(records),
        "all_canonical_PASS": len(records) == expected_jobs,
        "jobs_by_stage": {
            stage: sum(record["stage"] == stage for record in records)
            for stage in ("background", "delayed", "signal")
        },
        "maximum_peak_rss": None if maximum is None else {
            "job_id": maximum["job_id"],
            "family": maximum["family"],
            "mode": maximum["mode"],
            "bytes": maximum["peak_process_group_rss_bytes"],
            "GiB": maximum["peak_process_group_rss_GiB"],
        },
        "per_family_max_peak_rss": {
            family: {
                "job_id": max(values, key=lambda row: row["peak_process_group_rss_bytes"])["job_id"],
                "bytes": max(row["peak_process_group_rss_bytes"] for row in values),
                "GiB": max(row["peak_process_group_rss_bytes"] for row in values) / 1024**3,
            }
            for family, values in sorted(per_family.items())
        },
        "per_mode_family_max_peak_rss": [
            {
                "mode": mode,
                "family": family,
                "jobs": len(values),
                "max_bytes": max(row["peak_process_group_rss_bytes"] for row in values),
                "max_GiB": max(row["peak_process_group_rss_bytes"] for row in values) / 1024**3,
            }
            for (mode, family), values in sorted(per_cell.items())
        ],
        "receipt_records": list(records),
    }


def collect_receipts(
    effective: Sequence[dict[str, Any]], receipt_root: Path, check: Checker,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for plan_row in effective:
        job_id = str(plan_row["job_id"])
        path = receipt_root / f"{job_id}.json"
        receipt = check.json(f"transport_receipt_{job_id}", path)
        if receipt is None:
            continue
        authority = check.authorities[f"transport_receipt_{job_id}"]
        record = validate_receipt(receipt, plan_row, path, authority, check)
        if record is not None:
            records.append(record)
    check.wait_for(len(records) == len(effective), f"canonical effective transport receipts are {len(records)}/{len(effective)}")
    return records, summarize_receipts(records, len(effective))


def validate_completion_metrics(
    rows: Sequence[dict[str, Any]], receipt_records: Sequence[dict[str, Any]],
    check: Checker,
) -> dict[str, Any]:
    expected = {str(record["job_id"]): record for record in receipt_records}
    observed: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        job_id = str(row.get("job_id"))
        if job_id not in expected:
            check.errors.append(f"resource metric has non-effective or unknown job ID: {job_id}")
            continue
        if job_id in observed:
            check.errors.append(f"resource metric duplicates canonical successful job: {job_id}")
            continue
        try:
            receipt = expected[job_id]
            check.expect(row.get("status") == "PASS", f"resource metric is not PASS: {job_id}")
            check.expect(exact_int(row.get("peak_rss"), f"{job_id} metric peak RSS") == receipt["peak_process_group_rss_bytes"], f"resource metric peak RSS differs: {job_id}")
            check.expect(exact_int(row.get("artifact_bytes"), f"{job_id} metric artifact bytes") == receipt["artifact_bytes"], f"resource metric artifact bytes differ: {job_id}")
            free_bytes = exact_int(row.get("free_bytes"), f"{job_id} completion free bytes")
            check.expect(free_bytes >= DYNAMIC_DISK_RESERVE_BYTES, f"dynamic disk reserve failed at completion: {job_id}")
            observed[job_id] = {
                "job_id": job_id,
                "stage": receipt["stage"],
                "at": row.get("at"),
                "peak_rss_bytes": receipt["peak_process_group_rss_bytes"],
                "free_bytes": free_bytes,
                "dynamic_disk_reserve_pass": free_bytes >= DYNAMIC_DISK_RESERVE_BYTES,
            }
        except Exception as exc:
            check.errors.append(f"resource metric row {index} invalid: {exc}")
    check.wait_for(set(observed) == set(expected), f"completion resource metrics are {len(observed)}/{len(expected)} effective jobs")
    return {
        "expected_jobs": len(expected),
        "validated_jobs": len(observed),
        "all_effective_jobs_present": set(observed) == set(expected),
        "dynamic_disk_reserve_bytes": DYNAMIC_DISK_RESERVE_BYTES,
        "minimum_completion_free_bytes": min((row["free_bytes"] for row in observed.values()), default=None),
        "all_completion_rows_pass_dynamic_reserve": bool(observed) and all(row["dynamic_disk_reserve_pass"] for row in observed.values()),
        "records": [observed[job_id] for job_id in sorted(observed)],
    }


def validate_followup_manifest(payload: dict[str, Any] | None, check: Checker) -> dict[str, Any]:
    if not payload:
        return {}
    check.expect(payload.get("status") == "PASS__SF3_PLAN1_CRASH_SAFE_FOLLOWUP_EXECUTION_MANIFEST_PREPARED", "followup execution manifest status differs")
    check.expect(payload.get("required_service_unit") == "sf3-plan1-followup.service", "followup service unit differs")
    policies = payload.get("policies") or {}
    check.expect(policies.get("workers") == ACTUAL_CONTROLLER_WORKERS, "followup actual worker count differs")
    guard = policies.get("pressure_guard") or policies.get("delayed_guard") or {}
    check.expect(guard.get("normal_quota_percent") == NORMAL_QUOTA_PERCENT, "followup normal quota differs")
    check.expect(guard.get("throttle_quota_percent") == THROTTLE_QUOTA_PERCENT, "followup throttle quota differs")
    check.expect(guard.get("mem_available_floor_bytes") == MEMORY_FLOOR_BYTES, "followup memory floor differs")
    check.expect(guard.get("swap_free_floor_bytes") == SWAP_FLOOR_BYTES, "followup swap floor differs")
    check.wait_for(set(guard.get("guarded_steps") or []) == set(FOLLOWUP_SESSION_LABELS), "followup pressure-guard session-label registry is incomplete")
    by_id = {
        str(row.get("id")): row for row in payload.get("steps", [])
        if isinstance(row, dict)
    }
    registered: list[str] = []
    for step_id in FOLLOWUP_SESSION_LABELS:
        step = by_id.get(step_id) or {}
        check.wait_for(
            str(step.get("kind", "")).endswith("_with_pressure_guard")
            and step.get("guard") is True,
            f"followup {step_id} has not yet been registered as a guarded session",
        )
        if str(step.get("kind", "")).endswith("_with_pressure_guard") and step.get("guard") is True:
            registered.append(step_id)
    return {
        "service_unit": payload.get("required_service_unit"),
        "workers": policies.get("workers"),
        "guarded_session_labels": registered,
        "pressure_log_path": norm(FOLLOWUP_PRESSURE_LOG_PATH),
    }


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    check = Checker()
    config = check.json("analysis_inputs", config_path)
    if config is None:
        return {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "NOT_READY__SF3_RESOURCE_TIMELINE_EVIDENCE_INCOMPLETE",
            "ready": False,
            "checked_at": utc_now(),
            "missing": sorted(set(check.missing)),
            "pending": sorted(set(check.pending)),
            "errors": check.errors,
            "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__RECEIPT_METADATA_ONLY",
        }
    package_root, run_root = validate_config(config, config_path, check)
    plan_rows = check.csv("canonical_30_row_plan", PLAN_PATH)
    plan = cast_plan(plan_rows or [], check)
    background = validate_plan(plan, check) if plan_rows is not None else []

    stage02_summary = check.json("stage02_activation_summary", STAGE02_SUMMARY_PATH)
    stage02_rows = check.csv("stage02_delayed_source_index", STAGE02_SOURCE_INDEX_PATH)
    dispositions, delayed_run_rows, delayed_zero_rows = (
        validate_delayed_dispositions(stage02_summary, stage02_rows, plan, check)
        if stage02_summary is not None and stage02_rows is not None
        else ({}, [], [])
    )
    effective = effective_plan_rows(plan, delayed_run_rows, check)

    guard_source = check.source("pressure_guard_code", GUARD_PATH)
    policy = guard_policy(guard_source, check) if guard_source is not None else {}

    recoveries: dict[str, dict[str, Any] | None] = {
        label: check.json(f"recovery_{label}", path)
        for label, path in RECOVERY_PATHS
    }
    recovery_summary = validate_recoveries(recoveries, check)

    manual_audit = check.json("manual_quota_recovery", MANUAL_QUOTA_AUDIT_PATH)
    manual_recovery = validate_manual_quota_audit(manual_audit, check)

    followup_manifest = check.json("followup_execution_manifest", FOLLOWUP_MANIFEST_PATH)
    followup_execution = validate_followup_manifest(followup_manifest, check)

    receipt_root = run_root / "receipts"
    receipt_records, receipts = collect_receipts(effective, receipt_root, check)
    background_records = [record for record in receipt_records if record["stage"] == "background"]
    background_receipts = summarize_receipts(background_records, EXPECTED_BACKGROUND_JOBS)

    background_pressure_path = run_root / "pressure_guard_metrics.jsonl"
    background_pressure_rows = check.jsonl("background_pressure_guard_metrics", background_pressure_path)
    followup_pressure_rows = check.jsonl("followup_pressure_guard_metrics", FOLLOWUP_PRESSURE_LOG_PATH)
    required_pressure_stages = {"background", "signal"}
    if delayed_run_rows:
        required_pressure_stages.add("delayed")
    pressure = analyze_pressure_logs(
        (
            ("background_pressure_guard_metrics", background_pressure_rows or []),
            ("followup_pressure_guard_metrics", followup_pressure_rows or []),
        ),
        receipt_records,
        required_pressure_stages,
        set(FOLLOWUP_SESSION_LABELS),
        check,
    )

    resource_metric_rows = check.jsonl("completion_resource_metrics", run_root / "resource_metrics.jsonl")
    completion_resources = validate_completion_metrics(
        resource_metric_rows or [], receipt_records, check
    )

    output_exists = DEFAULT_OUTPUT.exists()
    if output_exists:
        check.errors.append(f"write-once resource audit already exists: {DEFAULT_OUTPUT}")
    ready = not check.errors and not check.missing and not check.pending
    status = (
        "READY__SF3_RESOURCE_TIMELINE_SMALL_AUTHORITIES_COMPLETE"
        if ready
        else "FAIL__SF3_RESOURCE_TIMELINE_PREREQUISITES"
        if check.errors
        else "NOT_READY__SF3_RESOURCE_TIMELINE_EVIDENCE_INCOMPLETE"
    )
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "checked_at": utc_now(),
        "package_root": norm(package_root),
        "run_root": norm(run_root),
        "output_path": norm(DEFAULT_OUTPUT),
        "output_exists": output_exists,
        "configuration": {
            "maximum_cpu_budget_cores": MAX_CPU_BUDGET_CORES,
            "adaptive_design_workers": [4, 6],
            "maximum_is_budget_not_observed_execution": True,
            "MemAvailable_floor_bytes": MEMORY_FLOOR_BYTES,
            "SwapFree_floor_bytes": SWAP_FLOOR_BYTES,
            "dynamic_disk_reserve_bytes": DYNAMIC_DISK_RESERVE_BYTES,
        },
        "recovery": recovery_summary,
        "manual_pressure_recovery_event": manual_recovery,
        "followup_execution": followup_execution,
        "actual_execution": {
            "controller_workers": ACTUAL_CONTROLLER_WORKERS,
            "worker_evidence": "SYSTEMD_OOMD_RECOVERY_NEW_CONTROLLER_CPU_BUDGET_AND_BG4_GUARD_UNIT",
            "guard_sessions": pressure,
            "manual_historical_quota_core_sequence": manual_recovery.get("quota_core_sequence"),
            "summary": "MAX_CPU_6__ACTUAL_4_WORKERS__QUOTA_BOUNDED_3_TO_4__HISTORICAL_MANUAL_4_TO_3_TO_4_RECORDED_SEPARATELY",
        },
        "pressure_guard_policy": policy,
        "delayed_dispositions": {
            "registered_cells": EXPECTED_DELAYED_CELLS,
            "by_family": dispositions,
            "RUN_83334_families": [row["family"] for row in delayed_run_rows],
            "SKIP_ZERO_A15_families": [row["family"] for row in delayed_zero_rows],
            "zero_A15_receipt_policy": "NO_TRANSPORT_AND_NO_RECEIPT__FINITE_UPPER_PROVENANCE_RETAINED",
        },
        "transport_receipts": receipts,
        "effective_transport_job_ids": sorted(record["job_id"] for record in receipt_records),
        "background_receipts": background_receipts,
        "completion_resources": completion_resources,
        "authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "pending": sorted(set(check.pending)),
        "errors": check.errors,
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__RECEIPT_PATH_SIZE_HEADER_METADATA_ONLY",
        "sim_opened_statted_discovered_or_hashed": False,
        "systemd_or_service_action_performed": False,
        "transport_launched": False,
    }


def write_once_atomic_json(path: Path, payload: dict[str, Any]) -> None:
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


def build(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    checked = check_prerequisites(config_path)
    if not checked.get("ready"):
        raise RuntimeError(json_text(checked))
    payload = dict(checked)
    payload.update({
        "status": PASS_STATUS,
        "built_at": utc_now(),
        "write_contract": "ATOMIC_HARDLINK_PUBLICATION__WRITE_ONCE",
    })
    write_once_atomic_json(DEFAULT_OUTPUT, payload)
    return payload


def _pressure_fixture_row(
    origin: datetime, seconds: int, unit: str, *, inactive: bool = False,
    terminal_restore: bool = False, session_label: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "at": (origin + timedelta(seconds=seconds)).isoformat(),
        "unit": unit,
        "unit_state": "inactive" if inactive else "active",
        "quota_percent": 400,
        "quota_changed": False,
        "decision_reasons": ["guard_exit_restore_normal"] if terminal_restore else ["hold"],
        "safe_streak": 1,
    }
    if session_label is not None:
        row["session_label"] = session_label
    if not terminal_restore:
        row.update({
            "cgroup_pressure": {"some_avg10": 0.0, "full_avg10": 0.0},
            "mem_available_bytes": 6 * 1024**3,
            "swap_free_bytes": 12 * 1024**3,
            "mem_floor_bytes": MEMORY_FLOOR_BYTES,
            "swap_floor_bytes": SWAP_FLOOR_BYTES,
        })
    return row


def self_test() -> dict[str, Any]:
    origin = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)
    records: list[dict[str, Any]] = []
    specifications = [
        *(('background', index) for index in range(EXPECTED_BACKGROUND_JOBS)),
        ('delayed', EXPECTED_BACKGROUND_JOBS),
        ('delayed', EXPECTED_BACKGROUND_JOBS + 1),
        ('signal', EXPECTED_BACKGROUND_JOBS + 2),
    ]
    for stage, index in specifications:
        family = "gamma" if index < 7 else "alpha" if index == 7 else FAMILIES[index % len(FAMILIES)]
        peak = int(3.14 * 1024**3) if index == 0 else int(1.63 * 1024**3) if index == 7 else 1024**3
        start_seconds, end_seconds = (
            (5, 55) if stage == "background"
            else (125, 175) if stage == "delayed"
            else (245, 295)
        )
        records.append({
            "job_id": f"synthetic_{index:02d}",
            "stage": stage,
            "mode": "instant" if index < EXPECTED_INSTANT_JOBS else "buildup",
            "family": family,
            "events": 100,
            "seed": index + 1,
            "attempt": 1,
            "started_at": (origin + timedelta(seconds=start_seconds)).isoformat(),
            "ended_at": (origin + timedelta(seconds=end_seconds)).isoformat(),
            "peak_process_group_rss_bytes": peak,
            "peak_process_group_rss_GiB": peak / 1024**3,
            "artifact_bytes": 1000 + index,
            "receipt_path": f"/synthetic/{index}.json",
            "receipt_sha256": "0" * 64,
            "sim_path_metadata": f"/metadata/synthetic_{index}.sim.gz",
            "sim_bytes_metadata": 1,
            "sim_accessed_or_hashed": False,
        })
    receipt_summary = summarize_receipts(records, len(records))
    if receipt_summary["validated_jobs"] != 24 or not receipt_summary["all_canonical_PASS"]:
        raise AssertionError("synthetic all-effective receipt closure failed")
    if receipt_summary["jobs_by_stage"] != {"background": 21, "delayed": 2, "signal": 1}:
        raise AssertionError("synthetic stage receipt closure failed")
    if "gamma" not in receipt_summary["per_family_max_peak_rss"] or "alpha" not in receipt_summary["per_family_max_peak_rss"]:
        raise AssertionError("synthetic gamma/alpha peak RSS summary failed")

    background_log = [
        _pressure_fixture_row(origin, 0, "sf3-plan1-bg4.service"),
        _pressure_fixture_row(origin, 60, "sf3-plan1-bg4.service", inactive=True),
    ]
    followup_log: list[dict[str, Any]] = []
    for label, start, end in (
        ("build_prompt", 70, 90),
        ("transport_delayed", 120, 180),
        ("analyze_delayed", 190, 210),
        ("transport_signal", 240, 300),
        ("build_common_response", 310, 330),
    ):
        followup_log.extend([
            _pressure_fixture_row(origin, start, "sf3-plan1-followup.service", session_label=label),
            _pressure_fixture_row(origin, end, "sf3-plan1-followup.service", terminal_restore=True, session_label=label),
        ])
    pressure_check = Checker()
    pressure = analyze_pressure_logs(
        (("background_pressure_guard_metrics", background_log), ("followup_pressure_guard_metrics", followup_log)),
        records, {"background", "delayed", "signal"},
        set(FOLLOWUP_SESSION_LABELS), pressure_check,
    )
    if pressure_check.errors or pressure_check.pending:
        raise AssertionError(f"synthetic pressure sessions failed: {pressure_check.errors}; {pressure_check.pending}")
    if not pressure["all_sessions_closed"] or not pressure["all_quotas_within_3_to_4_cores"]:
        raise AssertionError("synthetic pressure session closure/bounds failed")
    if not pressure["safe_all_four_core_session_is_PASS"] or pressure["artificial_throttle_required"]:
        raise AssertionError("safe all-four-core sessions did not PASS without artificial throttle")
    if (
        not pressure["all_required_exact_label_stage_bindings_pass"]
        or pressure["observed_closed_exact_label_stage_coverage"]
        != {
            "background_transport": ["background"],
            "transport_delayed": ["delayed"],
            "transport_signal": ["signal"],
        }
    ):
        raise AssertionError("exact guard label-to-receipt-stage coverage failed")

    mislabeled_followup_log = [dict(row) for row in followup_log]
    for row in mislabeled_followup_log:
        if row.get("session_label") == "transport_delayed":
            row["session_label"] = "analyze_delayed"
        elif row.get("session_label") == "analyze_delayed":
            row["session_label"] = "transport_delayed"
    mislabeled_check = Checker()
    mislabeled_pressure = analyze_pressure_logs(
        (("background_pressure_guard_metrics", background_log), ("followup_pressure_guard_metrics", mislabeled_followup_log)),
        records, {"background", "delayed", "signal"},
        set(FOLLOWUP_SESSION_LABELS), mislabeled_check,
    )
    if (
        mislabeled_pressure["all_required_exact_label_stage_bindings_pass"]
        or not any(
            "transport_delayed" in pending and "delayed" in pending
            for pending in mislabeled_check.pending
        )
    ):
        raise AssertionError("mislabeled delayed guard session was not rejected")

    manual_check = Checker()
    manual = validate_manual_quota_audit({
        "status": "PASS__SF3_MANUAL_QUOTA_PRESSURE_RECOVERY_AUDITED",
        "actual_controller_workers": 4,
        "quota_recovery": {
            "quota_core_sequence": [4, 3, 4],
            "restored_quota_cores": 4,
            "worker_count_changed": False,
            "job_terminated_by_recovery_action": False,
        },
        "pressure_recovery": {
            "pre_throttle_avg10_percent": 43.42,
            "systemd_oomd_kill_gate_percent": 50.0,
            "approximately_20_seconds_later_avg10_percent": 3.67,
            "later_avg10_percent": 0.0,
        },
        "service_mutated_by_audit": False,
    }, manual_check)
    if manual_check.errors or manual.get("quota_core_sequence") != [4, 3, 4]:
        raise AssertionError(f"synthetic manual recovery event failed: {manual_check.errors}")

    metric_check = Checker()
    metrics = validate_completion_metrics([
        {
            "job_id": record["job_id"], "status": "PASS",
            "peak_rss": record["peak_process_group_rss_bytes"],
            "artifact_bytes": record["artifact_bytes"],
            "free_bytes": 10 * 1024**3, "at": record["ended_at"],
        }
        for record in records
    ], records, metric_check)
    if metric_check.errors or metric_check.pending or not metrics["all_completion_rows_pass_dynamic_reserve"]:
        raise AssertionError(f"synthetic completion resource metrics failed: {metric_check.errors}; {metric_check.pending}")

    try:
        read_small_bytes(Path("/definitely/not/queried.sim.gz"))
    except RuntimeError as exc:
        if "SIM payload access is forbidden" not in str(exc):
            raise
    else:
        raise AssertionError("SIM payload guard did not reject before filesystem access")

    with tempfile.TemporaryDirectory(prefix="sf3-resource-selftest-") as temporary:
        target = Path(temporary) / "audit.json"
        write_once_atomic_json(target, {"status": "PASS", "allow_nan": False})
        try:
            write_once_atomic_json(target, {"status": "OVERWRITE"})
        except FileExistsError:
            pass
        else:
            raise AssertionError("write-once atomic publisher allowed overwrite")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_RESOURCE_TIMELINE_SYNTHETIC_SELF_TEST",
        "checks": [
            "manual_historical_pressure_43p42_to_3p67_to_zero_and_4_to_3_to_4",
            "safe_all_four_core_guard_sessions_PASS_without_artificial_throttle",
            "background_delayed_signal_guard_session_closure",
            "five_followup_session_labels_closed",
            "exact_transport_guard_label_to_receipt_stage_binding",
            "mislabeled_transport_guard_negative_test",
            "synthetic_21_background_plus_positive_delayed_plus_signal_receipt_closure",
            "zero_A15_receipt_exclusion_contract",
            "completion_dynamic_disk_reserve_metrics",
            "gamma_and_alpha_family_peak_RSS_reporting",
            "SIM_rejected_before_stat_open_or_hash",
            "atomic_write_once_publication",
        ],
        "sim_opened_statted_discovered_or_hashed": False,
        "systemd_or_service_action_performed": False,
        "transport_launched": False,
        "production_output_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--build", action="store_true")
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
        if args.check_prerequisites and not result.get("ready"):
            return 1 if result.get("errors") else 2
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "status": "FAIL__SF3_RESOURCE_TIMELINE_ADAPTER",
            "error": str(exc),
            "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__RECEIPT_METADATA_ONLY",
            "systemd_or_service_action_performed": False,
            "transport_launched": False,
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
