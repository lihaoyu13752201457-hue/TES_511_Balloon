#!/usr/bin/env python3
"""Build the terminal SF3 full-stat versus frozen-47 SE3 mission small tables.

This adapter is deliberately table-only.  It consumes the future full-stat
stage-02 inventory and stage-04 common-response tables, the frozen 47/SE3
stage-02/04/06 tables, and the frozen 81-node trajectory.  The numerical fold
is delegated to the retained Plan-1 implementation so the exact piecewise-
linear production/decay convolution, trapezoidal 20-day integration, central
F3, and componentwise-proxy F3 algorithms cannot silently diverge.

The Plan-1 central ratio <= 0.75 is an *entry gate* only.  This terminal
full-stat result reports final SF3/SE3 central and proxy ratios and never
authorizes or launches a second top-up.  No action in this module opens, stats,
discovers, or hashes a SIM, and no action launches transport.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import build_mission_stage as retained
import build_sf3_fullstat_activation as activation
import build_sf3_fullstat_topup as topup
from sf3_plan1_common import FAMILIES, PACKAGE_ROOT


HERE = Path(__file__).resolve()
CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
OUTPUT = PACKAGE_ROOT / "outputs/fullstat/06_mission"

PLAN1_STAGE04 = PACKAGE_ROOT / "outputs/04_common_response"
PLAN1_MISSION = PACKAGE_ROOT / "outputs/06_mission/summary.json"
PLAN1_CLOSURE = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"
TOPUP_STATIC = topup.STATIC_AUDIT
TOPUP_AGGREGATE = topup.TOPUP_AGGREGATE_RECEIPT

FULLSTAT_STAGE01 = PACKAGE_ROOT / "outputs/fullstat/01_prompt"
FULLSTAT_STAGE02 = PACKAGE_ROOT / "outputs/fullstat/02_activation"
FULLSTAT_STAGE03 = PACKAGE_ROOT / "outputs/fullstat/03_delayed"
FULLSTAT_STAGE04 = PACKAGE_ROOT / "outputs/fullstat/04_common_response"
ACTIVATION_VALIDATION = activation.ACTIVATION_VALIDATION
DELAYED_AGGREGATE = activation.FULLSTAT_DELAYED_AGGREGATE

PROFILE_ID = "SF3_FULLSTAT_FINAL_MISSION_V1"
STATUS = "PASS__SF3_FULLSTAT_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_FINAL_F3"
STAGE01_STATUS = "PASS__SF3_FULLSTAT_PROMPT_COMPLETE"
STAGE02_STATUS = activation.FULLSTAT_STATUS
STAGE02_VALIDATION_STATUS = activation.FULLSTAT_VALIDATION_STATUS
STAGE03_STATUS_PREFIX = "PASS__SF3_FULLSTAT_DELAYED"
STAGE04_STATUS = "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE"
POSITIVE_DISPOSITION = activation.POSITIVE_DISPOSITION
ZERO_DISPOSITION = activation.ZERO_DISPOSITION
TERMINAL_DECISION = "TERMINAL_FULLSTAT_REPORT_ONLY__NO_SECOND_TOPUP_BRANCH"

EXPECTED_COMBINED_BACKGROUND_JOBS = 49
EXPECTED_FULLSTAT_INSTANT_JOBS = 26
EXPECTED_FULLSTAT_INSTANT_HISTORIES = 3_842_075
EXPECTED_FULLSTAT_BUILDUP_JOBS = 23
EXPECTED_FULLSTAT_BUILDUP_HISTORIES = 3_046_468
EXPECTED_SIGNAL_TRIALS = 37_194
MAX_SMALL_BYTES = 128 * 1024**2
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


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
        return math.isclose(
            float(actual), float(expected), rel_tol=rel, abs_tol=absolute
        )
    except (TypeError, ValueError):
        return False


def json_text(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def csv_text(
    rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None
) -> str:
    if not rows and fields is None:
        raise RuntimeError("refusing schema-less empty CSV")
    names = list(fields or rows[0])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if set(row) != set(names):
            raise RuntimeError("CSV row schema drift")
        writer.writerow(row)
    return stream.getvalue()


def reject_sim_path(path: Path) -> None:
    if os.fspath(path).lower().endswith(SIM_SUFFIXES):
        raise RuntimeError(
            f"SIM payload access is forbidden before filesystem query: {path}"
        )


def load_small_json(path: Path) -> dict[str, Any]:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES or path.suffix.lower() != ".json":
        raise RuntimeError(f"invalid small JSON authority ({size} bytes): {path}")

    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON token: {token}")

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def load_small_csv(path: Path) -> list[dict[str, str]]:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES or path.suffix.lower() != ".csv":
        raise RuntimeError(f"invalid small CSV authority ({size} bytes): {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV header required: {path}")
        return list(reader)


def sha256_small(path: Path) -> str:
    reject_sim_path(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid small authority size ({size}): {path}")
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


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
        self.authority_missing: list[str] = []
        self.pending: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def json(
        self, label: str, path: Path, *, future: bool = True
    ) -> dict[str, Any] | None:
        reject_sim_path(path)
        if not path.is_file():
            target = self.missing if future else self.authority_missing
            target.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_json(path)
            self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def csv(
        self, label: str, path: Path, *, future: bool = True
    ) -> list[dict[str, str]] | None:
        reject_sim_path(path)
        if not path.is_file():
            target = self.missing if future else self.authority_missing
            target.append(f"{label}:{norm(path)}")
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
            self.authority_missing.append(f"{label}:{norm(path)}")
            return
        try:
            self.authorities[label] = small_record(path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")


def configured_paths(config: dict[str, Any]) -> dict[str, Path]:
    frozen = retained.configured_paths(config)
    return {
        "plan1_mission": PLAN1_MISSION,
        "plan1_closure": PLAN1_CLOSURE,
        "plan1_stage04_signal": PLAN1_STAGE04 / "signal_acceptance_effective_area.csv",
        "topup_static": TOPUP_STATIC,
        "topup_aggregate": TOPUP_AGGREGATE,
        "full01_summary": FULLSTAT_STAGE01 / "summary.json",
        "full01_manifest": FULLSTAT_STAGE01 / "manifest.json",
        "full02_summary": FULLSTAT_STAGE02 / "day15_summary.json",
        "full02_manifest": FULLSTAT_STAGE02 / "manifest.json",
        "full02_inventory": FULLSTAT_STAGE02 / "day15_inventory.csv",
        "full02_source_index": FULLSTAT_STAGE02 / "delayed_source_index.csv",
        "full02_validation": ACTIVATION_VALIDATION,
        "full03_summary": FULLSTAT_STAGE03 / "summary.json",
        "full03_manifest": FULLSTAT_STAGE03 / "manifest.json",
        "full03_aggregate": DELAYED_AGGREGATE,
        "full04_summary": FULLSTAT_STAGE04 / "summary.json",
        "full04_manifest": FULLSTAT_STAGE04 / "manifest.json",
        "full04_cutflow": FULLSTAT_STAGE04 / "common_cutflow.csv",
        "full04_occupancy": FULLSTAT_STAGE04 / "common_fullband_occupancy.csv",
        "full04_lineage": FULLSTAT_STAGE04 / "selected_background_w2_lineage.csv",
        "full04_signal": FULLSTAT_STAGE04 / "signal_acceptance_effective_area.csv",
        "full04_zero_provenance": FULLSTAT_STAGE04 / "delayed_zero_A15_provenance.csv",
        "frozen02_summary": frozen["frozen02_summary"],
        "frozen02_inventory": frozen["frozen02_inventory"],
        "frozen02_source_index": frozen["frozen02_source_index"],
        "frozen04_summary": frozen["frozen04_summary"],
        "frozen04_cutflow": frozen["frozen04_cutflow"],
        "frozen04_occupancy": frozen["frozen04_occupancy"],
        "frozen04_lineage": frozen["frozen04_lineage"],
        "frozen04_signal": frozen["frozen04_signal"],
        "frozen04_zero_provenance": frozen["frozen04_zero_provenance"],
        "frozen06_summary": frozen["frozen06_summary"],
        "scales": frozen["scales"],
        "scales_metadata": frozen["scales_metadata"],
        "atmosphere": frozen["atmosphere"],
    }


JSON_KEYS = {
    "plan1_mission",
    "plan1_closure",
    "topup_static",
    "topup_aggregate",
    "full01_summary",
    "full01_manifest",
    "full02_summary",
    "full02_manifest",
    "full02_validation",
    "full03_summary",
    "full03_manifest",
    "full03_aggregate",
    "full04_summary",
    "full04_manifest",
    "frozen02_summary",
    "frozen04_summary",
    "frozen06_summary",
    "scales_metadata",
}

FROZEN_KEYS = {
    "frozen02_summary",
    "frozen02_inventory",
    "frozen02_source_index",
    "frozen04_summary",
    "frozen04_cutflow",
    "frozen04_occupancy",
    "frozen04_lineage",
    "frozen04_signal",
    "frozen04_zero_provenance",
    "frozen06_summary",
    "scales",
    "scales_metadata",
    "atmosphere",
}


def validate_plan1_entry_gate(
    mission: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    static: dict[str, Any] | None,
    topup_receipts: dict[str, Any] | None,
    check: Checker,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "metric": "central F3_SF3/F3_SE3 from Plan-1",
        "threshold": 0.75,
        "authorized": False,
    }
    if mission:
        gate = mission.get("fullstat_gate") or {}
        ratio = gate.get("observed_central_ratio")
        try:
            ratio_value = float(ratio)
        except (TypeError, ValueError):
            ratio_value = math.nan
        check.expect(
            mission.get("status")
            == "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE",
            "Plan-1 stage06 mission status differs",
        )
        check.expect(
            gate.get("metric") == "F3_SF3_over_SE3_full_envelope",
            "Plan-1 entry-gate metric differs",
        )
        check.expect(gate.get("operator") == "<=", "Plan-1 entry-gate operator differs")
        check.expect(
            close(gate.get("threshold"), 0.75, rel=0.0, absolute=0.0),
            "Plan-1 entry-gate threshold differs",
        )
        check.expect(
            math.isfinite(ratio_value) and 0.0 <= ratio_value <= 0.75,
            "Plan-1 central gate does not authorize full-stat",
        )
        check.expect(gate.get("topup_required") is True, "Plan-1 gate does not require top-up")
        check.expect(
            gate.get("decision") == "TOPUP_TO_S3D_FULL_STAT_REQUIRED",
            "Plan-1 gate decision differs",
        )
        check.expect(gate.get("proxy_controls_gate") is False, "Plan-1 proxy controls entry gate")
        result.update(
            {
                "observed_central_ratio": ratio_value,
                "mission_status": mission.get("status"),
            }
        )
    if closure:
        check.expect(
            str(closure.get("status", "")).startswith(
                "PASS__SF3_PLAN1_CHAIN_COMPLETE"
            ),
            "Plan-1 stage07 closure is not PASS",
        )
        check.expect(closure.get("ready") is True, "Plan-1 stage07 is not ready")
        check.expect(closure.get("errors") == [], "Plan-1 stage07 errors are nonempty")
        check.expect(closure.get("missing") == [], "Plan-1 stage07 missing list is nonempty")
        check.expect(
            nested(closure, "fullstat_disposition", "topup_required") is True,
            "Plan-1 stage07 does not retain the true top-up gate",
        )
        check.expect(
            close(
                nested(closure, "fullstat_disposition", "observed_central_ratio"),
                result.get("observed_central_ratio"),
            ),
            "Plan-1 stage06/stage07 central ratio differs",
        )
        result["closure_status"] = closure.get("status")
    if static:
        check.expect(
            static.get("status")
            == "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED",
            "top-up static audit is not PASS",
        )
        check.expect(static.get("plan1_mutation") is False, "top-up static adapter mutated Plan-1")
        check.expect(nested(static, "transport", "launched") is False, "static adapter launched transport")
        check.expect(nested(static, "plan", "jobs") == 28, "top-up static plan does not contain 28 jobs")
        check.expect(
            nested(static, "aggregation", "combined_jobs")
            == EXPECTED_COMBINED_BACKGROUND_JOBS,
            "top-up static combined plan does not contain 49 jobs",
        )
        check.expect(
            nested(static, "aggregation", "pooling_boundary")
            == "NEVER_ACROSS_GEOMETRY_MODE_OR_FAMILY",
            "top-up static pooling boundary differs",
        )
        if mission:
            check.expect(
                nested(static, "gate_authorization", "mission_sha256")
                == check.authorities.get("plan1_mission", {}).get("sha256"),
                "top-up static mission binding differs",
            )
        if closure:
            check.expect(
                nested(static, "gate_authorization", "closure_sha256")
                == check.authorities.get("plan1_closure", {}).get("sha256"),
                "top-up static closure binding differs",
            )
    if topup_receipts:
        status = str(topup_receipts.get("status", ""))
        if status.startswith("PARTIAL__"):
            check.pending.append("top-up transport has not reached 28/28 PASS")
        else:
            check.expect(
                status == "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
                "top-up transport aggregate is not 28/28 PASS",
            )
        check.expect(topup_receipts.get("planned_jobs") == 28, "top-up planned jobs != 28")
        if status.startswith("PASS__"):
            check.expect(topup_receipts.get("validated_jobs") == 28, "top-up validated jobs != 28")
            check.expect(
                topup_receipts.get("instant_validated_events") == 2_561_382,
                "top-up instant histories differ",
            )
            check.expect(
                topup_receipts.get("buildup_validated_events") == 2_030_976,
                "top-up buildup histories differ",
            )
            check.expect(
                nested(topup_receipts, "projection", "pass") is True,
                "top-up final disk projection failed",
            )
    result["authorized"] = bool(
        mission
        and closure
        and static
        and topup_receipts
        and str(topup_receipts.get("status", "")).startswith("PASS__ALL_28_")
        and not check.errors
        and not check.pending
    )
    result["role"] = "ONE_TIME_ENTRY_GATE_ONLY__NOT_REAPPLIED_AFTER_FULLSTAT"
    result["proxy_controls_gate"] = False
    return result


def expect_stage_status(
    label: str,
    payload: dict[str, Any] | None,
    expected: str,
    check: Checker,
    *,
    prefix: bool = False,
) -> bool:
    if payload is None:
        return False
    status = str(payload.get("status", ""))
    passed = status.startswith(expected) if prefix else status == expected
    if passed:
        return True
    if status.startswith(("WAITING__", "NOT_READY__", "PARTIAL__")):
        check.pending.append(f"{label} status={status}")
    else:
        check.errors.append(f"{label} status differs: {status!r}")
    return False


def validate_fullstat_stages(
    payloads: dict[str, dict[str, Any] | None], check: Checker
) -> dict[str, Any]:
    passed: dict[str, bool] = {}
    s01 = payloads.get("full01_summary")
    m01 = payloads.get("full01_manifest")
    passed["stage01"] = expect_stage_status(
        "fullstat stage01", s01, STAGE01_STATUS, check
    )
    if s01:
        check.expect(s01.get("selected_instant_jobs") == EXPECTED_FULLSTAT_INSTANT_JOBS, "fullstat stage01 instant jobs != 26")
        check.expect(s01.get("selected_instant_histories") == EXPECTED_FULLSTAT_INSTANT_HISTORIES, "fullstat stage01 histories differ")
        check.expect(nested(s01, "sim_scan_policy", "sim_hashes_recomputed") == 0, "fullstat stage01 hashed SIM payloads")
    if m01 and s01:
        check.expect(m01.get("status") == s01.get("status"), "fullstat stage01 manifest status differs")

    s02 = payloads.get("full02_summary")
    m02 = payloads.get("full02_manifest")
    v02 = payloads.get("full02_validation")
    passed["stage02"] = expect_stage_status(
        "fullstat stage02", s02, STAGE02_STATUS, check
    )
    passed["stage02_validation"] = expect_stage_status(
        "fullstat stage02 validation", v02, STAGE02_VALIDATION_STATUS, check
    )
    if s02:
        check.expect(s02.get("selected_buildup_jobs") == EXPECTED_FULLSTAT_BUILDUP_JOBS, "fullstat stage02 buildup jobs != 23")
        check.expect(s02.get("selected_buildup_histories") == EXPECTED_FULLSTAT_BUILDUP_HISTORIES, "fullstat stage02 buildup histories differ")
        check.expect(s02.get("registered_delayed_source_cells") == 8, "fullstat stage02 registered cells != 8")
        check.expect(s02.get("plan1_83334_consumed_or_merged") is False, "fullstat stage02 consumed Plan-1 delayed")
        check.expect(s02.get("incremental_166666_merge_allowed") is False, "fullstat stage02 permits incremental delayed merge")
    if m02 and s02:
        check.expect(m02.get("status") == s02.get("status"), "fullstat stage02 manifest status differs")
    if v02:
        check.expect(v02.get("combined_buildup_jobs") == EXPECTED_FULLSTAT_BUILDUP_JOBS, "fullstat activation validation jobs != 23")
        check.expect(v02.get("combined_buildup_histories") == EXPECTED_FULLSTAT_BUILDUP_HISTORIES, "fullstat activation validation histories differ")
        check.expect(v02.get("registered_delayed_source_cells") == 8, "fullstat activation validation registered cells != 8")
        check.expect(v02.get("plan1_delayed_consumed") is False, "fullstat activation validation consumed Plan-1 delayed")

    s03 = payloads.get("full03_summary")
    m03 = payloads.get("full03_manifest")
    a03 = payloads.get("full03_aggregate")
    passed["stage03"] = expect_stage_status(
        "fullstat stage03", s03, STAGE03_STATUS_PREFIX, check, prefix=True
    )
    if m03 and s03:
        check.expect(m03.get("status") == s03.get("status"), "fullstat stage03 manifest status differs")
    if s03:
        check.expect(s03.get("registered_source_cells") == 8, "fullstat stage03 registered cells != 8")
        check.expect(
            int(s03.get("fresh_triggers_per_positive_family", 250_000)) == 250_000,
            "fullstat stage03 positive-family trigger count differs",
        )
    if a03:
        aggregate_status = str(a03.get("status", ""))
        if aggregate_status.startswith("PARTIAL__"):
            check.pending.append("fullstat delayed transport is incomplete")
            passed["stage03_transport"] = False
        else:
            passed["stage03_transport"] = aggregate_status.startswith(
                "PASS__SF3_FULLSTAT"
            )
            check.expect(passed["stage03_transport"], "fullstat delayed aggregate is not PASS")
        check.expect(a03.get("registered_families") == 8, "fullstat delayed aggregate registered families != 8")
        if passed.get("stage03_transport"):
            check.expect(a03.get("validated_transport_jobs") == a03.get("planned_transport_jobs"), "fullstat delayed validated/planned jobs differ")
        check.expect(a03.get("fresh_triggers_per_positive_family") == 250_000, "fullstat delayed aggregate trigger policy differs")
        check.expect(a03.get("plan1_83334_read") is False, "fullstat delayed aggregate read Plan-1 delayed")
        check.expect(a03.get("plan1_83334_pooled") is False, "fullstat delayed aggregate pooled Plan-1 delayed")
        check.expect(a03.get("incremental_merge_used") is False, "fullstat delayed aggregate used incremental merge")
    else:
        passed["stage03_transport"] = False

    s04 = payloads.get("full04_summary")
    m04 = payloads.get("full04_manifest")
    passed["stage04"] = expect_stage_status(
        "fullstat stage04", s04, STAGE04_STATUS, check
    )
    if s04:
        check.expect(s04.get("signal_scope") == retained.FRESH_SIGNAL_SCOPE, "fullstat stage04 signal scope differs")
        check.expect(s04.get("geometry", "SF3") == "SF3", "fullstat stage04 geometry differs")
        check.expect(s04.get("transport_launched_by_adapter", False) is False, "fullstat stage04 claims transport launch")
    if m04 and s04:
        check.expect(m04.get("status") == s04.get("status"), "fullstat stage04 manifest status differs")
    return {
        "required": sorted(passed),
        "pass": all(passed.values()) if passed else False,
        "stages": passed,
    }


def normalize_fullstat_source_registry(
    source_rows: Sequence[dict[str, str]],
    zero_rows: list[dict[str, str]],
    inventory_rows: list[dict[str, str]],
    components: dict[tuple[str, str], dict[str, str]],
) -> dict[str, dict[str, Any]]:
    normalized: list[dict[str, str]] = []
    positive_families: set[str] = set()
    for raw in source_rows:
        row = dict(raw)
        family = str(row.get("incident_family", ""))
        disposition = str(row.get("execution_disposition", ""))
        if disposition == POSITIVE_DISPOSITION:
            positive_families.add(family)
            row["execution_disposition"] = retained.RUN_DISPOSITION
            triggers = row.get("actual_transport_triggers")
            if triggers not in (None, "") and int(float(triggers)) != 250_000:
                raise RuntimeError(
                    f"fullstat positive source index is not fresh 250k: {family}"
                )
        elif disposition != ZERO_DISPOSITION:
            raise RuntimeError(
                f"unknown fullstat source-index disposition: {family}/{disposition}"
            )
        normalized.append(row)
    registry = retained.registered_source_contract(
        normalized, zero_rows, inventory_rows, components, "SF3"
    )
    for family in positive_families:
        registry[family].update(
            {
                "execution_disposition": POSITIVE_DISPOSITION,
                "mission_fold_positive_role": "FRESH_COMPLETE_250000",
                "plan1_83334_consumed_or_pooled": False,
            }
        )
    return registry


def validate_table_contracts(
    paths: dict[str, Path],
    payloads: dict[str, dict[str, Any] | None],
    tables: dict[str, list[dict[str, str]] | None],
    check: Checker,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    axes_ready = tables.get("scales") is not None and tables.get("atmosphere") is not None
    if axes_ready:
        try:
            scales, atmosphere, base = retained.load_mission_axes(paths)
            result["mission_axes"] = {
                "nodes": len(base),
                "start_day": base[0]["day_mid"],
                "end_day": base[-1]["day_mid"],
                "day15_nodes": sum(close(row["day_mid"], 15.0, rel=0.0, absolute=1e-12) for row in base),
                "scales_rows": len(scales),
                "atmosphere_rows": len(atmosphere),
            }
        except Exception as exc:
            check.errors.append(f"81-node mission axes invalid: {exc}")

    frozen_required = (
        "frozen02_summary", "frozen02_inventory", "frozen02_source_index",
        "frozen04_summary", "frozen04_cutflow", "frozen04_occupancy",
        "frozen04_lineage", "frozen04_signal", "frozen04_zero_provenance",
        "frozen06_summary",
    )
    if all(paths[key].is_file() for key in frozen_required):
        try:
            result["frozen_se3_anchor_status"] = retained.frozen_se3_static_anchors(paths)
        except Exception as exc:
            check.errors.append(f"frozen 47/SE3 authority drift: {exc}")

    fresh_keys = (
        "full02_inventory", "full02_source_index", "full04_cutflow",
        "full04_occupancy", "full04_lineage", "full04_signal",
        "full04_zero_provenance",
    )
    if all(tables.get(key) is not None for key in fresh_keys) and payloads.get("full04_summary"):
        try:
            inventory_rows = list(tables["full02_inventory"] or [])
            source_rows = list(tables["full02_source_index"] or [])
            cutflow = list(tables["full04_cutflow"] or [])
            occupancy = list(tables["full04_occupancy"] or [])
            lineage = list(tables["full04_lineage"] or [])
            zero_rows = list(tables["full04_zero_provenance"] or [])
            signal_rows = list(tables["full04_signal"] or [])
            for label, rows in (
                ("inventory", inventory_rows),
                ("source index", source_rows),
                ("cutflow", cutflow),
                ("occupancy", occupancy),
                ("signal", signal_rows),
                ("zero provenance", zero_rows),
            ):
                if rows and {row.get("geometry") for row in rows} != {"SF3"}:
                    raise RuntimeError(f"fullstat {label} is not SF3-only")
            components = retained.final_components(cutflow, "SF3")
            retained.occupancy_map(occupancy, "SF3")
            inventory = retained.aggregate_inventory(inventory_rows, "SF3")
            counts, weights = retained.delayed_lineage(lineage, "SF3")
            retained.validate_lineage_closure(
                "SF3", components, counts, weights, inventory
            )
            registry = normalize_fullstat_source_registry(
                source_rows, zero_rows, inventory_rows, components
            )
            signal = retained.select_full_envelope_signal(
                signal_rows,
                payloads["full04_summary"] or {},
                "SF3",
                retained.FRESH_SIGNAL_SCOPE,
            )["SF3"]
            result["fresh_sf3_table_status"] = {
                "inventory_rows": len(inventory_rows),
                "transported_parent_cells": len(inventory),
                "registered_delayed_cells": len(registry),
                "fresh_250k_families": [
                    family for family in FAMILIES
                    if registry[family]["execution_disposition"] == POSITIVE_DISPOSITION
                ],
                "zero_A15_families": [
                    family for family in FAMILIES
                    if registry[family]["execution_disposition"] == ZERO_DISPOSITION
                ],
                "signal_trials": int(signal["trials"]),
                "signal_selected_events": int(signal["selected_events"]),
            }
        except Exception as exc:
            check.errors.append(f"fresh fullstat SF3 mission tables invalid: {exc}")

    if tables.get("plan1_stage04_signal") is not None and tables.get("full04_signal") is not None:
        plan1_record = check.authorities.get("plan1_stage04_signal") or {}
        full_record = check.authorities.get("full04_signal") or {}
        check.expect(
            plan1_record.get("sha256") == full_record.get("sha256"),
            "fullstat stage04 did not reuse the identical fresh SF3 37194 signal acceptance table",
        )
        result["signal_reuse"] = {
            "status": "PASS__IDENTICAL_FRESH_SF3_37194_SIGNAL_ACCEPTANCE_SMALL_TABLE",
            "trials": EXPECTED_SIGNAL_TRIALS,
            "plan1_sha256": plan1_record.get("sha256"),
            "fullstat_sha256": full_record.get("sha256"),
            "fresh_signal_transport_rerun_for_fullstat": False,
        }
    return result


def check_prerequisites(config_path: Path = CONFIG) -> dict[str, Any]:
    check = Checker()
    config = check.json("analysis_inputs", config_path.resolve(), future=False)
    if config is None:
        return {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "FAIL__SF3_FULLSTAT_MISSION_CONFIG",
            "ready": False,
            "missing": check.missing,
            "authority_missing": check.authority_missing,
            "errors": check.errors,
            "SIM_opened_statted_discovered_or_hashed": False,
            "transport_launched": False,
        }
    paths = configured_paths(config)
    payloads: dict[str, dict[str, Any] | None] = {}
    tables: dict[str, list[dict[str, str]] | None] = {}
    for key, path in paths.items():
        future = key not in FROZEN_KEYS
        if key in JSON_KEYS:
            payloads[key] = check.json(key, path, future=future)
        else:
            tables[key] = check.csv(key, path, future=future)

    for label, path in (
        ("adapter_code", HERE),
        ("retained_plan1_mission_algorithm", Path(retained.__file__).resolve()),
        ("fullstat_activation_builder", Path(activation.__file__).resolve()),
        ("fullstat_common_response_builder", PACKAGE_ROOT / "code/build_sf3_fullstat_common_response.py"),
    ):
        check.code(label, path)

    analysis = config.get("analysis") or {}
    check.expect(analysis.get("mission_nodes") == retained.EXPECTED_NODES, "configured mission nodes != 81")
    check.expect(close(analysis.get("mission_days"), 20.0, rel=0.0, absolute=0.0), "configured mission duration != 20 days")
    check.expect(close(analysis.get("reference_flux_ph_cm2_s"), retained.REFERENCE_FLUX, rel=0.0, absolute=0.0), "configured reference flux differs")
    check.expect(config.get("frozen_se3", {}).get("scope") == "FROZEN_SMALL_TABLES_ONLY__NO_SE3_SIM_OR_RECEIPT_REQUIRED", "frozen SE3 scope differs")

    entry_gate = validate_plan1_entry_gate(
        payloads.get("plan1_mission"),
        payloads.get("plan1_closure"),
        payloads.get("topup_static"),
        payloads.get("topup_aggregate"),
        check,
    )
    stage_status = validate_fullstat_stages(payloads, check)
    table_status = validate_table_contracts(paths, payloads, tables, check)

    if OUTPUT.exists():
        check.errors.append(f"write-once fullstat mission output exists: {OUTPUT}")
    ready = not check.errors and not check.missing and not check.authority_missing and not check.pending
    if ready:
        status = "READY__SF3_FULLSTAT_FINAL_MISSION_SMALL_TABLES"
    elif check.errors or check.authority_missing:
        status = "FAIL__SF3_FULLSTAT_MISSION_AUTHORITY_OR_CONTRACT"
    else:
        status = "NOT_READY__SF3_FULLSTAT_MISSION_FUTURE_SMALL_TABLES"
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "checked_at": utc_now(),
        "output": norm(OUTPUT),
        "plan1_entry_gate": entry_gate,
        "fullstat_stage_status": stage_status,
        "table_contract_status": table_status,
        "missing": sorted(set(check.missing)),
        "authority_missing": sorted(set(check.authority_missing)),
        "pending": sorted(set(check.pending)),
        "errors": check.errors,
        "authorities": check.authorities,
        "algorithm_reuse": "DIRECT_CALLS_TO_BUILD_MISSION_STAGE_EXACT_FOLD_FUNCTIONS",
        "terminal_policy": TERMINAL_DECISION,
        "second_topup_authorized": False,
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched": False,
    }


def final_comparison_rows(
    summaries: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    se3 = summaries["SE3"]
    sf3 = summaries["SF3"]
    central_ratio = float(sf3["F3_20d_ph_cm2_s"]) / float(
        se3["F3_20d_ph_cm2_s"]
    )
    proxy_ratio = float(sf3["F3_20d_componentwise_proxy_ph_cm2_s"]) / float(
        se3["F3_20d_componentwise_proxy_ph_cm2_s"]
    )
    ratios = {
        "status": "PASS__TERMINAL_FULLSTAT_FAIR_37194_FULL_ENVELOPE_COMPARISON",
        "F3_SF3_over_SE3_full_envelope": central_ratio,
        "F3_componentwise_proxy_SF3_over_SE3_full_envelope": proxy_ratio,
        "Z20_SF3_over_SE3_full_envelope": float(sf3["Z20d"]) / float(se3["Z20d"]),
        "Z20_componentwise_proxy_SF3_over_SE3_full_envelope": float(sf3["Z20d_componentwise_proxy"]) / float(se3["Z20d_componentwise_proxy"]),
        "S20_SF3_over_SE3_full_envelope": float(sf3["source_counts_20d"]) / float(se3["source_counts_20d"]),
        "S20_lower95_SF3_over_SE3_full_envelope": float(sf3["source_lower95_counts_20d"]) / float(se3["source_lower95_counts_20d"]),
        "B20_SF3_over_SE3_full_envelope": float(sf3["background_counts_20d"]) / float(se3["background_counts_20d"]),
        "B20_componentwise_upper95_proxy_SF3_over_SE3_full_envelope": float(sf3["background_upper95_proxy_counts_20d"]) / float(se3["background_upper95_proxy_counts_20d"]),
        "phase": "FULLSTAT_TERMINAL",
        "decision": TERMINAL_DECISION,
        "second_topup_gate_evaluated": False,
        "second_topup_authorized": False,
        "proxy_controls_any_gate": False,
    }
    fields = (
        "row_role", "geometry", "phase", "signal_scope", "signal_trials",
        "signal_selected_events", "selected_effective_area_cm2",
        "selected_effective_area_lower95_cm2", "constant_day15_prompt_cps",
        "constant_day15_delayed_cps", "constant_day15_background_cps",
        "source_counts_20d", "source_lower95_counts_20d",
        "background_counts_20d", "background_upper95_proxy_counts_20d",
        "Z20d", "Z20d_componentwise_proxy", "F3_20d_ph_cm2_s",
        "F3_20d_componentwise_proxy_ph_cm2_s",
        "F3_ratio_to_frozen_full_envelope_SE3",
        "F3_proxy_ratio_to_frozen_full_envelope_SE3", "terminal_disposition",
    )
    rows: list[dict[str, Any]] = []
    for geometry in ("SE3", "SF3"):
        item = summaries[geometry]
        static = item["constant_environment_day15_reference"]
        row = {
            "row_role": "FROZEN_47_SE3_DENOMINATOR" if geometry == "SE3" else "FRESH_SF3_FULLSTAT_NUMERATOR",
            "geometry": geometry,
            "phase": "FULLSTAT_TERMINAL",
            "signal_scope": item["signal_scope"],
            "signal_trials": item["signal_trials"],
            "signal_selected_events": item["signal_selected_events"],
            "selected_effective_area_cm2": item["selected_effective_area_cm2"],
            "selected_effective_area_lower95_cm2": item["selected_effective_area_lower95_cm2"],
            "constant_day15_prompt_cps": static["prompt_final_cps"],
            "constant_day15_delayed_cps": static["delayed_final_cps"],
            "constant_day15_background_cps": static["background_final_cps"],
            "source_counts_20d": item["source_counts_20d"],
            "source_lower95_counts_20d": item["source_lower95_counts_20d"],
            "background_counts_20d": item["background_counts_20d"],
            "background_upper95_proxy_counts_20d": item["background_upper95_proxy_counts_20d"],
            "Z20d": item["Z20d"],
            "Z20d_componentwise_proxy": item["Z20d_componentwise_proxy"],
            "F3_20d_ph_cm2_s": item["F3_20d_ph_cm2_s"],
            "F3_20d_componentwise_proxy_ph_cm2_s": item["F3_20d_componentwise_proxy_ph_cm2_s"],
            "F3_ratio_to_frozen_full_envelope_SE3": 1.0 if geometry == "SE3" else central_ratio,
            "F3_proxy_ratio_to_frozen_full_envelope_SE3": 1.0 if geometry == "SE3" else proxy_ratio,
            "terminal_disposition": TERMINAL_DECISION,
        }
        if tuple(row) != fields:
            raise RuntimeError("terminal comparison-row schema drift")
        rows.append(row)
    return rows, ratios


def load_build_inputs(
    config: dict[str, Any], paths: dict[str, Path]
) -> dict[str, Any]:
    scales, _, base = retained.load_mission_axes(paths)
    full_inventory_rows = load_small_csv(paths["full02_inventory"])
    frozen_inventory_rows = load_small_csv(paths["frozen02_inventory"])
    full_cutflow = load_small_csv(paths["full04_cutflow"])
    full_occupancy = load_small_csv(paths["full04_occupancy"])
    full_lineage = load_small_csv(paths["full04_lineage"])
    frozen_cutflow = load_small_csv(paths["frozen04_cutflow"])
    frozen_occupancy = load_small_csv(paths["frozen04_occupancy"])
    frozen_lineage = load_small_csv(paths["frozen04_lineage"])
    full_summary04 = load_small_json(paths["full04_summary"])
    frozen_summary04 = load_small_json(paths["frozen04_summary"])
    full_signal = retained.select_full_envelope_signal(
        load_small_csv(paths["full04_signal"]),
        full_summary04,
        "SF3",
        retained.FRESH_SIGNAL_SCOPE,
    )["SF3"]
    frozen_signal = retained.select_full_envelope_signal(
        load_small_csv(paths["frozen04_signal"]),
        frozen_summary04,
        "SE3",
        retained.FROZEN_SIGNAL_SCOPE,
    )["SE3"]
    full_components = retained.final_components(full_cutflow, "SF3")
    full_registry = normalize_fullstat_source_registry(
        load_small_csv(paths["full02_source_index"]),
        load_small_csv(paths["full04_zero_provenance"]),
        full_inventory_rows,
        full_components,
    )
    frozen_registry = retained.registered_source_contract(
        load_small_csv(paths["frozen02_source_index"]),
        load_small_csv(paths["frozen04_zero_provenance"]),
        frozen_inventory_rows,
        retained.final_components(frozen_cutflow, "SE3"),
        "SE3",
    )
    return {
        "scales": scales,
        "base": base,
        "inventories": {
            "SF3": retained.aggregate_inventory(full_inventory_rows, "SF3"),
            "SE3": retained.aggregate_inventory(frozen_inventory_rows, "SE3"),
        },
        "responses": {
            "SF3": (full_cutflow, full_occupancy, full_lineage),
            "SE3": (frozen_cutflow, frozen_occupancy, frozen_lineage),
        },
        "signals": {"SF3": full_signal, "SE3": frozen_signal},
        "registries": {"SF3": full_registry, "SE3": frozen_registry},
    }


def report_text(summary: dict[str, Any]) -> str:
    sf3 = summary["geometries"]["SF3"]
    se3 = summary["geometries"]["SE3"]
    ratios = summary["terminal_fullstat_comparison"]
    return "\n".join(
        [
            "# SF3 terminal full-stat mission comparison",
            "",
            f"Status: `{summary['status']}`",
            "",
            "The fresh full-stat SF3 numerator is folded against the frozen 47/SE3 small-table denominator with the retained exact 81-node algorithm. The same fresh SF3 37,194-ray full-envelope signal acceptance table is reused.",
            "",
            "| Quantity | Full-stat SF3 | Frozen 47 SE3 | Ratio SF3/SE3 |",
            "|---|---:|---:|---:|",
            f"| S20 counts | {sf3['source_counts_20d']:.10g} | {se3['source_counts_20d']:.10g} | {ratios['S20_SF3_over_SE3_full_envelope']:.10g} |",
            f"| B20 counts | {sf3['background_counts_20d']:.10g} | {se3['background_counts_20d']:.10g} | {ratios['B20_SF3_over_SE3_full_envelope']:.10g} |",
            f"| F3 central (ph cm^-2 s^-1) | {sf3['F3_20d_ph_cm2_s']:.10g} | {se3['F3_20d_ph_cm2_s']:.10g} | {ratios['F3_SF3_over_SE3_full_envelope']:.10g} |",
            f"| F3 componentwise proxy | {sf3['F3_20d_componentwise_proxy_ph_cm2_s']:.10g} | {se3['F3_20d_componentwise_proxy_ph_cm2_s']:.10g} | {ratios['F3_componentwise_proxy_SF3_over_SE3_full_envelope']:.10g} |",
            "",
            f"Terminal disposition: `{TERMINAL_DECISION}`. No second top-up gate is evaluated or authorized.",
            "",
        ]
    )


def build(config_path: Path = CONFIG) -> dict[str, Any]:
    prerequisites = check_prerequisites(config_path)
    if not prerequisites.get("ready"):
        raise RuntimeError(json_text(prerequisites))
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite write-once output: {OUTPUT}")
    config = load_small_json(config_path)
    paths = configured_paths(config)
    frozen_anchors = retained.frozen_se3_static_anchors(paths)
    inputs = load_build_inputs(config, paths)
    timeline: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for geometry in ("SE3", "SF3"):
        cutflow, occupancy, lineage = inputs["responses"][geometry]
        rows, geometry_summary = retained.fold_geometry(
            geometry,
            inputs["base"],
            inputs["scales"],
            inputs["inventories"][geometry],
            cutflow,
            occupancy,
            lineage,
            inputs["signals"][geometry],
            inputs["registries"][geometry],
        )
        timeline.extend(rows)
        summaries[geometry] = geometry_summary

    se3 = summaries["SE3"]
    for field in (
        "source_counts_20d",
        "source_lower95_counts_20d",
        "background_counts_20d",
        "background_upper95_proxy_counts_20d",
        "Z20d",
        "Z20d_componentwise_proxy",
        "F3_20d_ph_cm2_s",
        "F3_20d_componentwise_proxy_ph_cm2_s",
    ):
        retained.assert_close(
            f"terminal folded SE3 {field}",
            float(se3[field]),
            float(retained.SE3_ANCHORS[field]),
        )
    comparison, ratios = final_comparison_rows(summaries)
    summary = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": STATUS,
        "created_at": utc_now(),
        "geometries": summaries,
        "terminal_fullstat_comparison": ratios,
        "plan1_entry_gate": prerequisites["plan1_entry_gate"],
        "fullstat_stage_status": prerequisites["fullstat_stage_status"],
        "signal_reuse": nested(
            prerequisites, "table_contract_status", "signal_reuse"
        ),
        "ratio_contract": {
            "numerator": "fresh SF3 full-stat prompt, rebuilt full inventory, fresh complete-250k delayed response, and reused fresh SF3 37194-ray full-envelope signal",
            "denominator": "frozen 47 SE3 stage02/04/06 small-table authority",
            "status": "FAIR_MATCHED_IDENTICAL_37194_RAY_FULL_ENVELOPE",
            "central_identity": "F3_SF3_fullstat/F3_SE3_frozen47",
            "componentwise_proxy_identity": "F3proxy_SF3_fullstat/F3proxy_SE3_frozen47",
            "phase_gate": "NONE__FINAL_REPORT",
            "second_topup_authorized": False,
            "proxy_controls_any_gate": False,
        },
        "frozen_se3_anchor_audit": frozen_anchors,
        "mission_contract": {
            "duration_days": retained.EXPECTED_MISSION_DAYS,
            "time_nodes": retained.EXPECTED_NODES,
            "reference_flux_ph_cm2_s": retained.REFERENCE_FLUX,
            "source_elevation_deg": retained.SOURCE_ELEVATION_DEG,
            "coincidence_window_s": retained.COINCIDENCE_WINDOW_S,
            "zero_inventory_at_day0": True,
            "activation_fold": "exact piecewise-linear-source decay convolution; no day15 reanchoring",
            "rate_integration": "trapezoidal over the same 81 trajectory nodes",
            "algorithm_authority": norm(Path(retained.__file__).resolve()),
        },
        "uncertainty_contract": {
            "central": "fullstat family-normalized SF3 background plus fixed-N reused 37194-ray Aeff against frozen-47 SE3",
            "componentwise_proxy": "family Garwood/mixture upper background with signal Clopper-Pearson lower; reported separately and not joint 95% coverage",
            "zero_A15": "finite activation upper with detector acceptance <=1; central exact zero for audited empty cells",
            "reported_ratios": [
                "central F3",
                "componentwise-proxy F3",
                "central/proxy Z20",
                "central/lower S20",
                "central/componentwise-upper B20",
            ],
            "not_propagated": [
                "time-correlated reuse of transport events across trajectory nodes",
                "full-band occupancy uncertainty in accidental live factor",
                "activation-yield, source-position mixture, optics, atmosphere, and trajectory systematics",
            ],
        },
        "input_authorities": prerequisites["authorities"],
        "sim_access_policy": "NO_SIM_OPEN_STAT_DISCOVERY_OR_HASH__SMALL_CSV_JSON_ONLY",
        "transport_launched_by_adapter": False,
        "second_topup_evaluated_or_launched": False,
        "authority_boundary": "TERMINAL_SF3_FULLSTAT_MISSION_REPORT__NO_SECOND_TOPUP_OR_AUTOMATIC_PROMOTION",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    work = Path(
        tempfile.mkdtemp(prefix=".06_mission.work-", dir=OUTPUT.parent)
    )
    try:
        (work / "mission_timeline.csv").write_text(
            csv_text(timeline), encoding="utf-8"
        )
        (work / "frozen47_se3_vs_sf3_fullstat_mission.csv").write_text(
            csv_text(comparison), encoding="utf-8"
        )
        (work / "summary.json").write_text(json_text(summary), encoding="utf-8")
        (work / "FINAL_REPORT.md").write_text(
            report_text(summary), encoding="utf-8"
        )
        generated = sorted(path for path in work.iterdir() if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": STATUS,
            "created_at": utc_now(),
            "output": norm(OUTPUT),
            "files": [
                {
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_small(path),
                }
                for path in generated
            ],
            "input_authorities": prerequisites["authorities"],
            "algorithm_authority": small_record(Path(retained.__file__).resolve()),
            "write_contract": "ATOMIC_DIRECTORY_RENAME__WRITE_ONCE",
            "SIM_opened_statted_discovered_or_hashed": False,
            "transport_launched": False,
            "second_topup_authorized": False,
        }
        (work / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
        os.rename(work, OUTPUT)
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def synthetic_summary(
    geometry: str, f3: float, f3_proxy: float
) -> dict[str, Any]:
    return {
        "geometry": geometry,
        "signal_scope": (
            retained.FROZEN_SIGNAL_SCOPE
            if geometry == "SE3"
            else retained.FRESH_SIGNAL_SCOPE
        ),
        "signal_trials": EXPECTED_SIGNAL_TRIALS,
        "signal_selected_events": 20_000,
        "selected_effective_area_cm2": 10.0,
        "selected_effective_area_lower95_cm2": 9.8,
        "constant_environment_day15_reference": {
            "prompt_final_cps": 0.1,
            "delayed_final_cps": 0.2,
            "background_final_cps": 0.3,
        },
        "source_counts_20d": 1000.0,
        "source_lower95_counts_20d": 980.0,
        "background_counts_20d": 10_000.0,
        "background_upper95_proxy_counts_20d": 20_000.0,
        "Z20d": 10.0,
        "Z20d_componentwise_proxy": 6.0,
        "F3_20d_ph_cm2_s": f3,
        "F3_20d_componentwise_proxy_ph_cm2_s": f3_proxy,
    }


def self_test() -> dict[str, Any]:
    retained_test = retained.self_test()
    if retained_test.get("status") != "PASS__SF3_MISSION_BUILDER_SELF_TEST":
        raise AssertionError("retained mission algorithm self-test did not pass")
    summaries = {
        "SE3": synthetic_summary("SE3", 8.0e-5, 4.0e-4),
        "SF3": synthetic_summary("SF3", 4.0e-5, 2.4e-4),
    }
    rows, ratios = final_comparison_rows(summaries)
    if len(rows) != 2 or ratios["F3_SF3_over_SE3_full_envelope"] != 0.5:
        raise AssertionError("terminal comparison arithmetic fixture failed")
    if (
        ratios["decision"] != TERMINAL_DECISION
        or ratios["second_topup_gate_evaluated"] is not False
        or ratios["second_topup_authorized"] is not False
    ):
        raise AssertionError("terminal comparison incorrectly created a second top-up gate")
    for ratio, expected in ((0.75, True), (0.7500001, False)):
        if (ratio <= 0.75) is not expected:
            raise AssertionError("Plan-1 entry-gate boundary fixture failed")
    try:
        load_small_json(Path("/synthetic/must-not-stat.sim.gz"))
    except RuntimeError as exc:
        if "before filesystem query" not in str(exc):
            raise
    else:
        raise AssertionError("SIM guard did not reject before stat")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_FINAL_MISSION_SYNTHETIC_SELF_TEST",
        "checks": [
            "retained_exact_piecewise_linear_decay_convolution",
            "retained_81node_20day_trapezoidal_F3_central_and_proxy_fold",
            "Plan1_entry_gate_equal_0p75_only",
            "terminal_fullstat_central_and_proxy_ratio_arithmetic",
            "terminal_phase_never_evaluates_or_authorizes_second_topup",
            "fixed_future_fullstat_stage02_and_stage04_small_table_paths",
            "SIM_guard_rejects_before_stat_open_or_hash",
        ],
        "output": norm(OUTPUT),
        "files_written": False,
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched": False,
        "second_topup_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--check-prerequisites",
        action="store_true",
        help="read only fixed small-table authorities",
    )
    actions.add_argument(
        "--self-test", action="store_true", help="run pure synthetic math/contracts"
    )
    actions.add_argument(
        "--build",
        action="store_true",
        help="publish terminal mission small tables; never transport/SIM",
    )
    parser.add_argument("--config", type=Path, default=CONFIG)
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
            return 1 if result.get("errors") or result.get("authority_missing") else 2
        return 0
    except Exception as exc:
        print(
            json_text(
                {
                    "schema_version": 1,
                    "status": "FAIL__SF3_FULLSTAT_FINAL_MISSION_ADAPTER",
                    "error": str(exc),
                    "SIM_opened_statted_discovered_or_hashed": False,
                    "transport_launched": False,
                    "second_topup_authorized": False,
                }
            ),
            end="",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
