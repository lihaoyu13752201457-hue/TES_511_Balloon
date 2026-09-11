#!/usr/bin/env python3
"""Apply the frozen response to conditional SF3 full-stat background catalogs.

The adapter consumes future ``outputs/fullstat/01_prompt`` and
``outputs/fullstat/03_delayed`` catalogs.  It deliberately reuses the already
completed Plan-1 stage-04 small tables for the *same* fresh SF3 37,194-ray
full-envelope signal; no signal SIM, receipt artifact, or signal catalog is
reopened, rescanned, or rerun.

Production is locked behind the central <=0.75 gate, the Plan-1 stage-07
closure, and complete full-stat prompt/activation/delayed authorities.  The
response remains the exact keyed 0.42-keV FWHM implementation, 0.3-keV pixel
threshold, 50-keV three-BGO plus three-plastic active veto, W2, and retained
Step05.  The exact three added W volumes are diagnostic-only and never veto.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Sequence

import build_common_response as common
import build_sf3_fullstat_activation as activation
import build_sf3_fullstat_topup as topup
import run_prompt_analysis as prompt
import run_sf3_fullstat_delayed as delayed_transport
from sf3_plan1_common import FAMILIES, FULLSTAT_DELAYED_EVENTS, PACKAGE_ROOT, S3D_HISTORIES


CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
OUTPUT = PACKAGE_ROOT / "outputs/fullstat/04_common_response"
STAGE01 = PACKAGE_ROOT / "outputs/fullstat/01_prompt"
STAGE03 = PACKAGE_ROOT / "outputs/fullstat/03_delayed"
PLAN1_STAGE04 = PACKAGE_ROOT / "outputs/04_common_response"
MISSION = PACKAGE_ROOT / "outputs/06_mission/summary.json"
STAGE07 = PACKAGE_ROOT / "outputs/07_final_audit/final_audit.json"

TOPUP_STATIC_AUDIT = topup.STATIC_AUDIT
TOPUP_AGGREGATE = topup.TOPUP_AGGREGATE_RECEIPT
ACTIVATION_VALIDATION = activation.ACTIVATION_VALIDATION
FULLSTAT_DELAYED_AGGREGATE = activation.FULLSTAT_DELAYED_AGGREGATE

PROFILE_ID = "SF3_FULLSTAT_COMMON_RESPONSE_V1"
STATUS = "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE"
SIGNAL_REUSE_AUTHORITY = "REUSED_IDENTICAL_PLAN1_STAGE04_FRESH_SF3_37194_SMALL_TABLES"
BACKGROUND_AUTHORITY = "FRESH_SF3_FULLSTAT_PROMPT_DELAYED_COMMON_RESPONSE"
POSITIVE_DISPOSITION = activation.POSITIVE_DISPOSITION
ZERO_DISPOSITION = activation.ZERO_DISPOSITION
PASSIVE_W_VOLUMES = frozenset(activation.PASSIVE_W_VOLUMES)
ACTIVE_VETO_THRESHOLD_KEV = 50.0
EXPECTED_RNG_NAMESPACE = "TES511_CORRECTED_SEVEN_FAMILY_PROMPT_KEYED_PIXEL_RESPONSE_V1"
MAX_WORKERS = 6
DEFAULT_WORKERS = 4
MAX_SMALL_JSON_BYTES = 20 * 1024**2
MAX_SMALL_CSV_BYTES = 128 * 1024**2

SIGNAL_TABLES = {
    "acceptance": "signal_acceptance_effective_area.csv",
    "first_interaction": "signal_first_interaction_summary.csv",
    "failure": "signal_failure_summary.csv",
    "ray_diagnostics": "signal_ray_diagnostics.csv",
    "input_manifest": "signal_input_manifest.csv",
}

SELECTED_LINEAGE_FIELDS = (
    "geometry", "stream", "family", "local_event_id", "batch_id", "job_name",
    "transport_seed", "measured_total_keV", "measured_multiplicity", "shield_keV",
    "plastic_keV", "passive_w_keV", "first_interaction_volume",
    "first_interaction_resolution", "first_interaction_in_passive_w",
    "has_pair_ia", "has_annihilation_ia", "w_pair_ia_count",
    "w_annihilation_ia_count", "pair_ia_unresolved_count",
    "annihilation_ia_unresolved_count", "event_weight_cps", "source_parent_ZA",
    "source_volume", "source_excitation_keV", "sim_initial_ZA",
    "parent_match_distance_cm", "source_file", "signal_scope",
)
PASSIVE_W_LINEAGE_FIELDS = (
    "geometry", "stream", "family", "source_volume", "source_parent_ZA",
    "selected_measured_w2_events", "selected_measured_w2_rate_cps",
    "passive_w_role",
)
ZERO_PROVENANCE_FIELDS = (
    "geometry", "family", "execution_disposition", "central_delayed_rate_cps",
    "transported_ground_activity_Bq", "buildup_sum_TT_s",
    "transported_ground_rate_upper95_s-1",
    "transported_ground_A15_upper95_Bq_conservative",
    "zero_A15_upper_provenance", "upper_excludes_known_and_unresolved_holdout",
    "known_holdout_activity_Bq_reported_separately",
    "unknown_holdout_state_count_reported_separately", "catalog_origin",
    "stage03_catalog_opened", "SIM_opened",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_JSON_BYTES:
        raise RuntimeError(f"JSON authority is empty/oversized: {path} ({size})")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_CSV_BYTES:
        raise RuntimeError(f"CSV authority is empty/oversized: {path} ({size})")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: Iterable[dict[str, Any]],
    fields: Sequence[str] | None = None,
) -> None:
    materialized = list(rows)
    names = list(fields) if fields is not None else (list(materialized[0]) if materialized else [])
    if not names:
        raise RuntimeError(f"refusing schema-less CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def sha256_small(path: Path, *, limit: int = MAX_SMALL_CSV_BYTES) -> str:
    size = path.stat().st_size
    if size <= 0 or size > limit:
        raise RuntimeError(f"refusing empty/oversized small-table digest: {path} ({size})")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def small_record(path: Path, *, limit: int = MAX_SMALL_CSV_BYTES) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_small(path, limit=limit),
    }


def validate_response_config_payload(config: dict[str, Any]) -> dict[str, Any]:
    analysis = config.get("analysis") or {}
    if float(analysis.get("response_fwhm_keV", -1.0)) != 0.42:
        raise RuntimeError("response_fwhm_keV is not exactly 0.42")
    if float(analysis.get("measured_pixel_threshold_keV", -1.0)) != 0.3:
        raise RuntimeError("measured_pixel_threshold_keV is not exactly 0.3")
    if float(analysis.get("active_veto_threshold_keV", -1.0)) != ACTIVE_VETO_THRESHOLD_KEV:
        raise RuntimeError("active veto threshold is not exactly 50 keV")
    if tuple(float(value) for value in analysis.get("w2_keV", [])) != common.WINDOWS["w2_510p58_511p42"]:
        raise RuntimeError("configured W2 is not 510.58--511.42 keV")
    if analysis.get("step05_policy") != "retained_side_compton_fov_reject":
        raise RuntimeError("configured Step05 policy differs from the retained side-Compton/FoV reject")
    geometry = config.get("geometry") or {}
    shield = set(str(value) for value in geometry.get("shield_veto_volumes", []))
    plastic = set(str(value) for value in geometry.get("plastic_veto_volumes", []))
    active = set(str(value) for value in geometry.get("active_veto_volumes", []))
    passive = set(str(value) for value in geometry.get("passive_w_volumes", []))
    if len(shield) != 3 or len(plastic) != 3 or active != shield | plastic or len(active) != 6:
        raise RuntimeError("active veto is not exactly three BGO plus three plastic volumes")
    if passive != PASSIVE_W_VOLUMES:
        raise RuntimeError("exact three SF3 W volume whitelist differs")
    if active & passive:
        raise RuntimeError("passive W appears in the active-veto set")
    if geometry.get("passive_w_never_active_veto") is not True:
        raise RuntimeError("passive_w_never_active_veto is not true")
    return {
        "FWHM_keV": 0.42,
        "measured_pixel_threshold_keV": 0.3,
        "active_veto_threshold_keV": 50.0,
        "W2_keV": list(common.WINDOWS["w2_510p58_511p42"]),
        "step05_policy": "retained_side_compton_fov_reject",
        "shield_volumes": sorted(shield),
        "plastic_volumes": sorted(plastic),
        "active_veto_volumes": sorted(active),
        "passive_w_volumes": sorted(passive),
        "passive_w_role": "EXACT_WHITELIST_DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
    }


def validate_gate_and_stage07() -> dict[str, Any]:
    gate = topup.validate_gate(MISSION, STAGE07)
    static = load_json(TOPUP_STATIC_AUDIT)
    if static.get("status") != "PASS__SF3_FULLSTAT_TOPUP_STATIC_PACKAGE_PREPARED__TRANSPORT_NOT_LAUNCHED":
        raise RuntimeError("full-stat top-up static gate audit is not PASS")
    recorded = static.get("gate_authorization") or {}
    for key in ("mission_sha256", "closure_sha256", "central_R_F3", "decision"):
        if recorded.get(key) != gate.get(key):
            raise RuntimeError(f"top-up static gate binding differs: {key}")
    closure = load_json(STAGE07)
    if (
        not str(closure.get("status", "")).startswith("PASS__")
        or closure.get("ready") is False
        or closure.get("errors") not in (None, [])
        or closure.get("missing") not in (None, [])
    ):
        raise RuntimeError("Plan-1 stage07 closure is not complete PASS")
    return {
        **gate,
        "stage07": small_record(STAGE07, limit=MAX_SMALL_JSON_BYTES),
        "topup_static_audit": small_record(TOPUP_STATIC_AUDIT, limit=MAX_SMALL_JSON_BYTES),
    }


def validate_prompt_authority() -> dict[str, Any]:
    summary_path = STAGE01 / "summary.json"
    manifest_path = STAGE01 / "manifest.json"
    summary = load_json(summary_path)
    manifest = load_json(manifest_path)
    if summary.get("status") != "PASS__SF3_FULLSTAT_PROMPT_COMPLETE":
        raise RuntimeError("full-stat stage01 prompt status differs")
    if int(summary.get("selected_instant_jobs", -1)) != 26:
        raise RuntimeError("full-stat stage01 selected instant jobs != 26")
    if int(summary.get("selected_instant_histories", -1)) != 3_842_075:
        raise RuntimeError("full-stat stage01 instant histories != 3,842,075")
    response = summary.get("response") or {}
    if float(response.get("fwhm_keV", -1.0)) != 0.42 or float(response.get("pixel_threshold_keV", -1.0)) != 0.3:
        raise RuntimeError("full-stat stage01 response identity differs")
    veto = summary.get("active_veto") or {}
    if set(veto.get("active_veto_volumes", [])) & PASSIVE_W_VOLUMES:
        raise RuntimeError("full-stat stage01 placed passive W in active veto")
    w = summary.get("passive_w_diagnostics") or {}
    if set(w.get("passive_w_volumes", [])) != PASSIVE_W_VOLUMES:
        raise RuntimeError("full-stat stage01 passive-W diagnostic whitelist differs")
    if manifest.get("status") != summary["status"]:
        raise RuntimeError("full-stat stage01 manifest status differs")
    scan = summary.get("sim_scan_policy") or {}
    if int(scan.get("selected_sim_count", -1)) != 26 or int(scan.get("sim_hashes_recomputed", -1)) != 0:
        raise RuntimeError("full-stat stage01 one-pass/no-hash closure differs")
    catalogs: dict[str, str] = {}
    for family in FAMILIES:
        path = STAGE01 / "catalog/SF3" / f"{family}.pkl"
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(f"missing full-stat prompt catalog: {path}")
        catalogs[family] = str(path)
    return {
        "status": summary["status"],
        "summary": small_record(summary_path, limit=MAX_SMALL_JSON_BYTES),
        "manifest": small_record(manifest_path, limit=MAX_SMALL_JSON_BYTES),
        "catalogs": catalogs,
    }


def validate_fullstat_activation_and_transport() -> dict[str, Any]:
    act = load_json(ACTIVATION_VALIDATION)
    if act.get("status") != activation.FULLSTAT_VALIDATION_STATUS:
        raise RuntimeError("full-stat activation validation status differs")
    if act.get("hard_gates") != {
        "central_mission_topup_required_true": True,
        "all_28_topup_background_canonical_PASS": True,
    }:
        raise RuntimeError("full-stat activation double hard gate differs")
    if int(act.get("combined_buildup_jobs", -1)) != 23 or int(act.get("combined_buildup_histories", -1)) != 3_046_468:
        raise RuntimeError("full-stat activation 23-job/history closure differs")
    if act.get("plan1_delayed_consumed") is not False or act.get("incremental_83334_plus_166666_merge_allowed") is not False:
        raise RuntimeError("full-stat activation consumed/merged Plan-1 delayed")
    passive = act.get("passive_w") or {}
    if (
        set(passive.get("exact_volume_whitelist", [])) != PASSIVE_W_VOLUMES
        or passive.get("passive_w_never_veto") is not True
    ):
        raise RuntimeError("full-stat activation passive-W authority differs")

    topup_aggregate = load_json(TOPUP_AGGREGATE)
    if (
        topup_aggregate.get("status") != "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS"
        or int(topup_aggregate.get("planned_jobs", -1)) != 28
        or int(topup_aggregate.get("validated_jobs", -1)) != 28
        or len(topup_aggregate.get("selected_receipts") or []) != 28
    ):
        raise RuntimeError("full-stat top-up aggregate does not close 28 canonical PASS jobs")
    bound_topup = ((act.get("topup_receipt_gate") or {}).get("aggregate") or {})
    actual_topup = small_record(TOPUP_AGGREGATE, limit=MAX_SMALL_JSON_BYTES)
    if any(bound_topup.get(key) != actual_topup.get(key) for key in ("path", "bytes", "sha256")):
        raise RuntimeError("full-stat activation does not bind the current 28-job top-up aggregate")

    source_cards = act.get("source_cards")
    if not isinstance(source_cards, list) or len(source_cards) != 8:
        raise RuntimeError("full-stat activation source-card registry is not eight families")
    card_registry: dict[str, dict[str, Any]] = {}
    for row in source_cards:
        if not isinstance(row, dict):
            raise RuntimeError("full-stat activation source-card row is not an object")
        family = str(row.get("family", ""))
        if family not in FAMILIES or family in card_registry:
            raise RuntimeError(f"full-stat activation source-card family differs: {family!r}")
        disposition = str(row.get("execution_disposition", ""))
        if disposition not in (POSITIVE_DISPOSITION, ZERO_DISPOSITION):
            raise RuntimeError(f"full-stat activation disposition differs: {family}/{disposition}")
        if int(row.get("registered_events", -1)) != FULLSTAT_DELAYED_EVENTS:
            raise RuntimeError(f"full-stat activation registered events differ: {family}")
        expected_actual = FULLSTAT_DELAYED_EVENTS if disposition == POSITIVE_DISPOSITION else 0
        if int(row.get("actual_transport_events", -1)) != expected_actual:
            raise RuntimeError(f"full-stat activation actual transport events differ: {family}")
        activity_value = float(row.get("transported_ground_activity_Bq", math.nan))
        if not math.isfinite(activity_value) or (activity_value > 0.0) != (disposition == POSITIVE_DISPOSITION):
            raise RuntimeError(f"full-stat activation activity/disposition differs: {family}")
        card_registry[family] = row
    if set(card_registry) != set(FAMILIES):
        raise RuntimeError("full-stat activation source-card family closure differs")

    aggregate = load_json(FULLSTAT_DELAYED_AGGREGATE)
    if aggregate.get("status") != delayed_transport.FULLSTAT_COMPLETE_STATUS:
        raise RuntimeError("full-stat delayed aggregate is not PASS")
    registered = int(aggregate.get("registered_families", aggregate.get("registered_delayed_source_cells", -1)))
    planned = int(aggregate.get("planned_transport_jobs", -1))
    validated = int(aggregate.get("validated_transport_jobs", -1))
    if registered != 8 or planned < 0 or validated != planned:
        raise RuntimeError("full-stat delayed aggregate job closure differs")
    triggers = int(aggregate.get("fresh_triggers_per_positive_family", -1))
    if triggers != FULLSTAT_DELAYED_EVENTS:
        raise RuntimeError("full-stat delayed aggregate is not fresh 250k")
    if (
        aggregate.get("plan1_83334_read") is not False
        or aggregate.get("plan1_83334_pooled") is not False
        or aggregate.get("incremental_merge_used") is not False
    ):
        raise RuntimeError("full-stat delayed aggregate consumed or pooled Plan-1 delayed")
    positive = [family for family in FAMILIES if card_registry[family]["execution_disposition"] == POSITIVE_DISPOSITION]
    zero = [family for family in FAMILIES if card_registry[family]["execution_disposition"] == ZERO_DISPOSITION]
    if (
        aggregate.get("positive_A15_families") != positive
        or aggregate.get("zero_A15_families") != zero
        or int(aggregate.get("zero_A15_jobs_skipped", -1)) != len(zero)
        or len(aggregate.get("selected_receipts") or []) != len(positive)
        or int(aggregate.get("validated_fresh_triggers", -1)) != len(positive) * FULLSTAT_DELAYED_EVENTS
    ):
        raise RuntimeError("full-stat delayed aggregate family/trigger closure differs")
    return {
        "topup_aggregate": actual_topup,
        "activation_validation": small_record(ACTIVATION_VALIDATION, limit=MAX_SMALL_JSON_BYTES),
        "delayed_aggregate": small_record(FULLSTAT_DELAYED_AGGREGATE, limit=MAX_SMALL_JSON_BYTES),
        "positive_transport_jobs": planned,
        "zero_A15_skips": 8 - planned,
        "positive_families": positive,
        "zero_families": zero,
    }


def delayed_disposition_registry(
    summary: dict[str, Any], coverage_rows: Sequence[dict[str, str]]
) -> dict[str, dict[str, Any]]:
    status = str(summary.get("status", ""))
    if not status.startswith("PASS__SF3_FULLSTAT_DELAYED"):
        raise RuntimeError(f"full-stat stage03 status differs: {status}")
    activity_rows = summary.get("activity_and_weights")
    zero_rows = summary.get("zero_source_cells")
    if not isinstance(activity_rows, list) or not isinstance(zero_rows, list):
        raise RuntimeError("full-stat stage03 disposition arrays are malformed")
    coverage: dict[str, dict[str, str]] = {}
    for row in coverage_rows:
        if row.get("geometry") != "SF3":
            continue
        family = str(row.get("family", ""))
        if family not in FAMILIES or family in coverage:
            raise RuntimeError(f"full-stat stage03 coverage family differs: {family!r}")
        coverage[family] = row
    zero_by_family: dict[str, dict[str, Any]] = {}
    for raw in zero_rows:
        if not isinstance(raw, dict):
            raise RuntimeError("full-stat stage03 zero-source row is not an object")
        family = str(raw.get("family", ""))
        if family not in FAMILIES or family in zero_by_family:
            raise RuntimeError(f"full-stat stage03 zero family differs: {family!r}")
        zero_by_family[family] = raw
    registry: dict[str, dict[str, Any]] = {}
    for raw in activity_rows:
        if not isinstance(raw, dict):
            raise RuntimeError("full-stat stage03 activity row is not an object")
        family = str(raw.get("family", ""))
        if family not in FAMILIES or family in registry:
            raise RuntimeError(f"full-stat stage03 activity family differs: {family!r}")
        disposition = str(raw.get("execution_disposition", ""))
        if disposition not in (POSITIVE_DISPOSITION, ZERO_DISPOSITION):
            raise RuntimeError(f"full-stat delayed disposition differs: {family}/{disposition}")
        cell = coverage.get(family)
        if cell is None or cell.get("execution_disposition") != disposition:
            raise RuntimeError(f"full-stat stage03 coverage disposition differs: {family}")
        activity_value = float(raw.get("transported_ground_activity_Bq", math.nan))
        item: dict[str, Any] = {
            "family": family,
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": activity_value,
            "event_weight_cps": float(raw.get("event_weight_cps", 0.0) or 0.0),
            "equivalent_time_s": raw.get("equivalent_time_s"),
            "known_holdout_activity_Bq": float(raw.get("known_holdout_activity_Bq", 0.0)),
            "unknown_activity_state_count": int(raw.get("unknown_activity_state_count", 0)),
            "catalog_required": disposition == POSITIVE_DISPOSITION,
            "catalog_origin": (
                "FULLSTAT_STAGE03_FRESH250K_TRANSPORT_CATALOG"
                if disposition == POSITIVE_DISPOSITION
                else "STRUCTURAL_EMPTY_ZERO_RATE__NO_STAGE03_CATALOG_OR_SIM"
            ),
        }
        if disposition == POSITIVE_DISPOSITION:
            if not math.isfinite(activity_value) or activity_value <= 0.0:
                raise RuntimeError(f"full-stat positive delayed activity is not positive: {family}")
            triggers = int(float(cell.get("triggers", "-1")))
            if triggers != FULLSTAT_DELAYED_EVENTS:
                raise RuntimeError(f"full-stat positive delayed triggers are not 250k: {family}")
            expected_weight = activity_value / FULLSTAT_DELAYED_EVENTS
            if not math.isclose(item["event_weight_cps"], expected_weight, rel_tol=2.0e-12, abs_tol=1.0e-20):
                raise RuntimeError(f"full-stat positive delayed event weight differs: {family}")
            if family in zero_by_family or not str(cell.get("catalog_path", "")).strip():
                raise RuntimeError(f"full-stat positive delayed catalog/zero closure differs: {family}")
            item.update({
                "buildup_sum_TT_s": None,
                "transported_ground_rate_upper95_s-1": None,
                "transported_ground_A15_upper95_Bq_conservative": None,
                "zero_A15_upper_provenance": None,
                "upper_excludes_known_and_unresolved_holdout": None,
            })
        else:
            zero = zero_by_family.get(family)
            if zero is None:
                raise RuntimeError(f"full-stat stage03 zero registry omits {family}")
            if activity_value != 0.0 or int(float(cell.get("triggers", "-1"))) != 0:
                raise RuntimeError(f"full-stat zero delayed central/triggers differ: {family}")
            if any(str(cell.get(name, "")).strip() for name in ("catalog_path", "sim_path", "receipt_path")):
                raise RuntimeError(f"full-stat zero delayed publishes transport artifact: {family}")
            sum_tt = float(zero.get("buildup_sum_TT_s", math.nan))
            rate_upper = float(zero.get("transported_ground_rate_upper95_s-1", math.nan))
            a15_upper = float(zero.get("transported_ground_A15_upper95_Bq_conservative", math.nan))
            provenance = str(zero.get("upper_provenance", zero.get("zero_A15_upper_provenance", "")))
            if not all(math.isfinite(value) and value > 0.0 for value in (sum_tt, rate_upper, a15_upper)):
                raise RuntimeError(f"full-stat zero delayed finite upper differs: {family}")
            if not math.isclose(rate_upper, a15_upper, rel_tol=0.0, abs_tol=1.0e-18):
                raise RuntimeError(f"full-stat zero delayed rate/A15 upper differs: {family}")
            if not provenance or "sumTT" not in provenance:
                raise RuntimeError(f"full-stat zero delayed upper provenance absent: {family}")
            item.update({
                "event_weight_cps": 0.0,
                "equivalent_time_s": None,
                "buildup_sum_TT_s": sum_tt,
                "transported_ground_rate_upper95_s-1": rate_upper,
                "transported_ground_A15_upper95_Bq_conservative": a15_upper,
                "zero_A15_upper_provenance": provenance,
                "upper_excludes_known_and_unresolved_holdout": True,
            })
        registry[family] = item
    if set(registry) != set(FAMILIES) or set(coverage) != set(FAMILIES):
        raise RuntimeError("full-stat stage03 does not close eight families")
    zero_families = [family for family in FAMILIES if registry[family]["execution_disposition"] == ZERO_DISPOSITION]
    if set(zero_by_family) != set(zero_families):
        raise RuntimeError("full-stat stage03 zero-source family closure differs")
    positive_count = len(FAMILIES) - len(zero_families)
    if int(summary.get("registered_source_cells", -1)) != 8:
        raise RuntimeError("full-stat stage03 registered source cells != 8")
    if int(summary.get("transport_jobs", -1)) != positive_count:
        raise RuntimeError("full-stat stage03 transport-job count differs")
    if int(summary.get("skipped_zero_A15_jobs", -1)) != len(zero_families):
        raise RuntimeError("full-stat stage03 zero-skip count differs")
    trigger_policy = summary.get(
        "fresh_triggers_per_positive_family",
        summary.get("transport_triggers_per_family", -1),
    )
    if int(trigger_policy) != FULLSTAT_DELAYED_EVENTS:
        raise RuntimeError("full-stat stage03 fresh trigger policy differs")
    return registry


def validate_delayed_stage() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summary_path = STAGE03 / "summary.json"
    coverage_path = STAGE03 / "delayed_cell_coverage.csv"
    manifest_path = STAGE03 / "manifest.json"
    summary = load_json(summary_path)
    coverage = read_csv(coverage_path)
    manifest = load_json(manifest_path)
    registry = delayed_disposition_registry(summary, coverage)
    if manifest.get("status") != summary.get("status"):
        raise RuntimeError("full-stat stage03 manifest status differs")
    passive = summary.get("passive_w_diagnostics") or {}
    if (
        set(passive.get("passive_w_volumes") or []) != PASSIVE_W_VOLUMES
        or passive.get("role") != "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES"
    ):
        raise RuntimeError("full-stat stage03 passive-W diagnostic authority differs")
    raw = summary.get("raw_catalog") or {}
    veto = raw.get("veto_policy_recorded") or {}
    active = set(veto.get("active_veto_volumes") or [])
    if raw.get("response_applied") is not False or len(active) != 6 or active & PASSIVE_W_VOLUMES:
        raise RuntimeError("full-stat stage03 raw-catalog/active-veto boundary differs")
    scan = summary.get("sim_scan_policy") or {}
    positive_count = sum(row["catalog_required"] for row in registry.values())
    if (
        int(scan.get("selected_sim_count", -1)) != positive_count
        or int(scan.get("semantic_scans", -1)) != positive_count
        or int(scan.get("sim_hashes_recomputed", -1)) != 0
        or int(scan.get("zero_source_sim_count", -1)) != 0
    ):
        raise RuntimeError("full-stat stage03 one-pass/no-hash/zero-source SIM policy differs")
    catalogs: dict[str, str] = {}
    for family in FAMILIES:
        path = STAGE03 / "catalog/SF3" / f"{family}.pkl"
        if registry[family]["catalog_required"]:
            if not path.is_file() or path.stat().st_size <= 0:
                raise FileNotFoundError(f"missing full-stat delayed catalog: {path}")
            catalogs[family] = str(path)
        elif path.exists():
            raise RuntimeError(f"zero-A15 family unexpectedly has a stage03 catalog: {family}")
    return ({
        "status": summary["status"],
        "summary": small_record(summary_path, limit=MAX_SMALL_JSON_BYTES),
        "coverage": small_record(coverage_path),
        "manifest": small_record(manifest_path, limit=MAX_SMALL_JSON_BYTES),
        "catalogs": catalogs,
    }, registry)


def validate_signal_table_payloads(
    summary: dict[str, Any],
    manifest: dict[str, Any],
    acceptance: Sequence[dict[str, Any]],
    first_interaction: Sequence[dict[str, Any]],
    failure: Sequence[dict[str, Any]],
    cutflow: Sequence[dict[str, Any]],
    occupancy: Sequence[dict[str, Any]],
    diagnostics: Sequence[dict[str, Any]],
    passive_w: Sequence[dict[str, Any]],
    input_manifest: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if (
        summary.get("status") != "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE"
        or summary.get("profile_id") != common.PROFILE_ID
    ):
        raise RuntimeError("Plan-1 stage04 signal authority status differs")
    signal = summary.get("signal") or {}
    if (
        summary.get("signal_scope") != common.SIGNAL_SCOPE
        or signal.get("job_id") != common.SIGNAL_JOB_ID
        or int(signal.get("eventlist_rows", -1)) != common.SIGNAL_TRIALS
        or int(signal.get("ray_id_rows", -1)) != common.SIGNAL_TRIALS
        or int(signal.get("semantic_sim_scans", -1)) != 1
        or int(signal.get("sim_hashes_recomputed", -1)) != 0
    ):
        raise RuntimeError("Plan-1 stage04 fresh SF3 signal identity differs")
    if manifest.get("status") != summary.get("status") or manifest.get("profile_id") != common.PROFILE_ID:
        raise RuntimeError("Plan-1 stage04 manifest status differs")
    large = manifest.get("large_payload_policy") or {}
    if int(large.get("fresh_signal_SIM_semantic_scans", -1)) != 1 or int(large.get("fresh_signal_SIM_hashes", -1)) != 0:
        raise RuntimeError("Plan-1 stage04 signal one-pass/no-hash provenance differs")
    response = summary.get("response") or {}
    if float(response.get("FWHM_keV", -1.0)) != 0.42 or float(response.get("measured_pixel_threshold_keV", -1.0)) != 0.3:
        raise RuntimeError("Plan-1 signal response implementation identity differs")
    active_policy = response.get("active_veto") or {}
    active = set(active_policy.get("active_veto_volumes") or [])
    passive = summary.get("passive_w") or {}
    if (
        len(active) != 6
        or active & PASSIVE_W_VOLUMES
        or active_policy.get("policy_id") != "SF3_EXPLICIT_3BGO_PLUS_3PLASTIC"
        or active_policy.get("apply_plastic_veto") is not True
        or float(active_policy.get("plastic_threshold_keV", -1.0)) != 50.0
        or 50.0 not in [float(value) for value in active_policy.get("shield_thresholds_keV", [])]
        or set(active_policy.get("passive_w_volumes") or []) != PASSIVE_W_VOLUMES
        or active_policy.get("passive_w_role") != "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO"
    ):
        raise RuntimeError("Plan-1 signal active-veto identity differs")
    if response.get("step05_implementation") != str(prompt.STEP05):
        raise RuntimeError("Plan-1 signal Step05 implementation identity differs")
    if (
        response.get("rng_namespace") != EXPECTED_RNG_NAMESPACE
        or response.get("response_geometry_key") != "sf3"
    ):
        raise RuntimeError("Plan-1 keyed pixel-response namespace/geometry identity differs")
    if set(passive.get("volumes") or []) != PASSIVE_W_VOLUMES or passive.get("role") != "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO":
        raise RuntimeError("Plan-1 signal passive-W authority differs")

    if len(acceptance) != 2:
        raise RuntimeError("Plan-1 signal acceptance must contain broad and W2 rows")
    by_window = {str(row.get("window_id")): row for row in acceptance}
    if set(by_window) != set(common.FINAL_WINDOWS):
        raise RuntimeError("Plan-1 signal acceptance window closure differs")
    for window, row in by_window.items():
        if (
            row.get("geometry") != "SF3"
            or row.get("response_state") != common.FINAL_RESPONSE
            or row.get("stage") != common.FINAL_STAGE
            or int(row.get("trials", -1)) != common.SIGNAL_TRIALS
            or row.get("signal_scope") != common.SIGNAL_SCOPE
            or row.get("authority_status") != common.SIGNAL_AUTHORITY
        ):
            raise RuntimeError(f"Plan-1 signal acceptance identity differs: {window}")
        selected = int(row["selected_events"])
        if not math.isclose(float(row["acceptance"]), selected / common.SIGNAL_TRIALS, rel_tol=2.0e-12, abs_tol=1.0e-15):
            raise RuntimeError(f"Plan-1 signal acceptance arithmetic differs: {window}")

    signal_cutflow = [row for row in cutflow if row.get("stream") == "signal"]
    expected_keys = {
        (response, stage, window)
        for response, stage in common.CANONICAL_STAGES
        for window in common.FINAL_WINDOWS
    }
    observed_keys = {
        (row.get("response_state"), row.get("stage"), row.get("window_id"))
        for row in signal_cutflow
    }
    if observed_keys != expected_keys or len(signal_cutflow) != len(expected_keys):
        raise RuntimeError("Plan-1 signal common-cutflow key closure differs")
    for window in common.FINAL_WINDOWS:
        final = next(
            row for row in signal_cutflow
            if row["response_state"] == common.FINAL_RESPONSE
            and row["stage"] == common.FINAL_STAGE and row["window_id"] == window
        )
        if int(final["selected_events"]) != int(by_window[window]["selected_events"]):
            raise RuntimeError(f"Plan-1 signal cutflow/acceptance count differs: {window}")

    signal_occupancy = [row for row in occupancy if row.get("stream") == "signal"]
    if len(signal_occupancy) != 1 or signal_occupancy[0].get("family") != common.SIGNAL_FAMILY:
        raise RuntimeError("Plan-1 signal occupancy identity differs")
    if len(diagnostics) != common.SIGNAL_TRIALS:
        raise RuntimeError("Plan-1 signal diagnostic row count differs")
    ray_ids = [int(row.get("ray_id", -1)) for row in diagnostics]
    if ray_ids != list(range(common.SIGNAL_TRIALS)):
        raise RuntimeError("Plan-1 signal ray IDs are not exact 0..37193")
    final_passes = sum(str(row.get("final_w2_step05_pass", "")).lower() == "true" for row in diagnostics)
    if final_passes != int(by_window["w2_510p58_511p42"]["selected_events"]):
        raise RuntimeError("Plan-1 signal diagnostic final-pass count differs from W2 acceptance")
    first_counter = Counter((
        str(row.get("first_interaction_process", "")),
        str(row.get("first_interaction_volume", "")),
        str(row.get("first_interaction_material", "")),
        str(row.get("first_interaction_resolution", "")),
    ) for row in diagnostics)
    first_table: Counter[tuple[str, str, str, str]] = Counter()
    for row in first_interaction:
        if row.get("geometry") != "SF3" or row.get("signal_scope") != common.SIGNAL_SCOPE:
            raise RuntimeError("Plan-1 first-interaction table identity differs")
        key = (
            str(row.get("first_interaction_process", "")),
            str(row.get("first_interaction_volume", "")),
            str(row.get("first_interaction_material", "")),
            str(row.get("first_interaction_resolution", "")),
        )
        first_table[key] += int(row.get("rays", -1))
    if first_table != first_counter or sum(first_table.values()) != common.SIGNAL_TRIALS:
        raise RuntimeError("Plan-1 signal first-interaction summary does not close diagnostics")
    failure_counter = Counter(str(row.get("failure_category", "")) for row in diagnostics)
    failure_table: Counter[str] = Counter()
    for row in failure:
        if row.get("geometry") != "SF3" or row.get("signal_scope") != common.SIGNAL_SCOPE:
            raise RuntimeError("Plan-1 failure table identity differs")
        failure_table[str(row.get("failure_category", ""))] += int(row.get("rays", -1))
    if failure_table != failure_counter or sum(failure_table.values()) != common.SIGNAL_TRIALS:
        raise RuntimeError("Plan-1 signal failure summary does not close diagnostics")
    signal_w = [row for row in passive_w if row.get("stream") == "signal"]
    if (
        len(signal_w) != 1
        or signal_w[0].get("family") != common.SIGNAL_FAMILY
        or signal_w[0].get("passive_w_role") != "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO"
        or signal_w[0].get("normalization_unit") != "cm2"
    ):
        raise RuntimeError("Plan-1 signal passive-W diagnostic identity differs")
    if len(input_manifest) != 1:
        raise RuntimeError("Plan-1 signal input manifest row count differs")
    source = input_manifest[0]
    if (
        source.get("geometry") != "SF3"
        or source.get("job_id") != common.SIGNAL_JOB_ID
        or source.get("signal_scope") != common.SIGNAL_SCOPE
        or int(source.get("events", -1)) != common.SIGNAL_TRIALS
        or int(source.get("semantic_sim_scans", -1)) != 1
        or str(source.get("sim_hash_recomputed", "")).lower() != "false"
    ):
        raise RuntimeError("Plan-1 signal input-manifest identity differs")
    bank_sha = str(signal.get("eventlist_bank_sha256_from_static_audit", ""))
    if len(bank_sha) != 64 or source.get("eventlist_static_audit_sha256") != bank_sha:
        raise RuntimeError("Plan-1 signal frozen 37,194-ray bank identity differs")
    return {
        "status": "PASS__IDENTICAL_PLAN1_STAGE04_FRESH_SF3_SIGNAL_SMALL_TABLES",
        "job_id": common.SIGNAL_JOB_ID,
        "signal_scope": common.SIGNAL_SCOPE,
        "trials": common.SIGNAL_TRIALS,
        "ray_rows": len(diagnostics),
        "w2_selected_events": int(by_window["w2_510p58_511p42"]["selected_events"]),
        "semantic_signal_SIM_scans_in_this_adapter": 0,
        "signal_SIM_or_receipt_artifact_opened": False,
    }


def load_plan1_signal_authority() -> dict[str, Any]:
    """Load only the completed Plan-1 signal tables, never their SIM lineage."""
    paths = {
        "summary": PLAN1_STAGE04 / "summary.json",
        "manifest": PLAN1_STAGE04 / "manifest.json",
        "cutflow": PLAN1_STAGE04 / "common_cutflow.csv",
        "occupancy": PLAN1_STAGE04 / "common_fullband_occupancy.csv",
        "passive_w": PLAN1_STAGE04 / "passive_w_diagnostics.csv",
        **{name: PLAN1_STAGE04 / filename for name, filename in SIGNAL_TABLES.items()},
    }
    summary = load_json(paths["summary"])
    manifest = load_json(paths["manifest"])
    tables = {
        name: read_csv(path)
        for name, path in paths.items()
        if name not in ("summary", "manifest")
    }
    identity = validate_signal_table_payloads(
        summary,
        manifest,
        tables["acceptance"],
        tables["first_interaction"],
        tables["failure"],
        tables["cutflow"],
        tables["occupancy"],
        tables["ray_diagnostics"],
        tables["passive_w"],
        tables["input_manifest"],
    )
    signal_tables = {
        "cutflow": [row for row in tables["cutflow"] if row.get("stream") == "signal"],
        "occupancy": [row for row in tables["occupancy"] if row.get("stream") == "signal"],
        "passive_w": [row for row in tables["passive_w"] if row.get("stream") == "signal"],
        **{name: tables[name] for name in SIGNAL_TABLES},
    }
    records = {
        name: small_record(path, limit=(MAX_SMALL_JSON_BYTES if path.suffix == ".json" else MAX_SMALL_CSV_BYTES))
        for name, path in paths.items()
    }
    identity_material = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    identity["small_table_set_sha256"] = hashlib.sha256(identity_material).hexdigest()
    identity["source_stage04"] = records["summary"]
    return {
        "identity": identity,
        "summary": summary,
        "manifest": manifest,
        "tables": signal_tables,
        "records": records,
        "paths": paths,
    }


def nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def check_prerequisites(config_path: Path = CONFIG) -> dict[str, Any]:
    """Fail closed using named small authorities; never inspect a SIM payload."""
    errors: list[str] = []
    missing: list[str] = []
    authorities: dict[str, Any] = {}
    delayed_registry: dict[str, dict[str, Any]] = {}
    config: dict[str, Any] | None = None

    base_required: dict[str, Path] = {
        "config": config_path,
        "mission_central_gate": MISSION,
        "plan1_stage07": STAGE07,
        "fullstat_topup_static": TOPUP_STATIC_AUDIT,
        "fullstat_topup_aggregate": TOPUP_AGGREGATE,
        "fullstat_activation_validation": ACTIVATION_VALIDATION,
        "fullstat_delayed_aggregate": FULLSTAT_DELAYED_AGGREGATE,
        "fullstat_prompt_summary": STAGE01 / "summary.json",
        "fullstat_prompt_manifest": STAGE01 / "manifest.json",
        "fullstat_delayed_summary": STAGE03 / "summary.json",
        "fullstat_delayed_coverage": STAGE03 / "delayed_cell_coverage.csv",
        "fullstat_delayed_manifest": STAGE03 / "manifest.json",
        "retained_response_core": prompt.CORRECTED_CORE,
        "retained_step05": prompt.STEP05,
        "retained_step09": prompt.STEP09_SUMMARY,
        "plan1_stage04_summary": PLAN1_STAGE04 / "summary.json",
        "plan1_stage04_manifest": PLAN1_STAGE04 / "manifest.json",
        "plan1_signal_cutflow_rows": PLAN1_STAGE04 / "common_cutflow.csv",
        "plan1_signal_occupancy_row": PLAN1_STAGE04 / "common_fullband_occupancy.csv",
        "plan1_signal_passive_w_row": PLAN1_STAGE04 / "passive_w_diagnostics.csv",
    }
    for family in FAMILIES:
        base_required[f"fullstat_prompt_catalog_{family}"] = STAGE01 / "catalog/SF3" / f"{family}.pkl"
    for name, filename in SIGNAL_TABLES.items():
        base_required[f"plan1_signal_{name}"] = PLAN1_STAGE04 / filename
    for role, path in base_required.items():
        if not nonempty_file(path):
            missing.append(f"{role}:{path}")

    if nonempty_file(config_path):
        try:
            config = load_json(config_path)
            authorities["response_config"] = validate_response_config_payload(config)
            authorities["config"] = small_record(config_path, limit=MAX_SMALL_JSON_BYTES)
        except Exception as exc:
            errors.append(f"response config invalid: {exc}")
    runtime_inputs = [prompt.CORRECTED_CORE, prompt.STEP05, prompt.STEP09_SUMMARY]
    if config is not None and all(nonempty_file(path) for path in runtime_inputs):
        try:
            runtime_contract = common.response_contract(config)
            if (
                runtime_contract.get("rng_namespace") != EXPECTED_RNG_NAMESPACE
                or runtime_contract.get("response_geometry_key") != "sf3"
                or float(runtime_contract.get("FWHM_keV", -1.0)) != 0.42
                or float(runtime_contract.get("measured_pixel_threshold_keV", -1.0)) != 0.3
                or tuple(runtime_contract.get("W2_keV") or ()) != common.WINDOWS["w2_510p58_511p42"]
                or runtime_contract.get("step05_implementation") != str(prompt.STEP05)
            ):
                raise RuntimeError("retained keyed response/W2/Step05 implementation identity differs")
            authorities["retained_runtime_response"] = runtime_contract
        except Exception as exc:
            errors.append(f"retained response runtime invalid: {exc}")

    if all(nonempty_file(path) for path in (MISSION, STAGE07, TOPUP_STATIC_AUDIT)):
        try:
            authorities["central_gate_and_stage07"] = validate_gate_and_stage07()
        except Exception as exc:
            errors.append(f"central gate/stage07 invalid: {exc}")

    prompt_inputs = [STAGE01 / "summary.json", STAGE01 / "manifest.json"] + [
        STAGE01 / "catalog/SF3" / f"{family}.pkl" for family in FAMILIES
    ]
    if all(nonempty_file(path) for path in prompt_inputs):
        try:
            authorities["fullstat_prompt"] = validate_prompt_authority()
        except Exception as exc:
            errors.append(f"full-stat stage01 invalid: {exc}")

    activation_inputs = [
        ACTIVATION_VALIDATION, TOPUP_AGGREGATE, FULLSTAT_DELAYED_AGGREGATE,
    ]
    if all(nonempty_file(path) for path in activation_inputs):
        try:
            authorities["fullstat_activation_and_transport"] = validate_fullstat_activation_and_transport()
        except Exception as exc:
            errors.append(f"full-stat activation/transport invalid: {exc}")

    delayed_inputs = [
        STAGE03 / "summary.json", STAGE03 / "delayed_cell_coverage.csv", STAGE03 / "manifest.json",
    ]
    if all(nonempty_file(path) for path in delayed_inputs):
        try:
            delayed_authority, delayed_registry = validate_delayed_stage()
            authorities["fullstat_delayed"] = delayed_authority
        except FileNotFoundError as exc:
            missing.append(f"fullstat_delayed_catalog:{exc}")
        except Exception as exc:
            errors.append(f"full-stat stage03 invalid: {exc}")

    signal_inputs = [
        PLAN1_STAGE04 / "summary.json", PLAN1_STAGE04 / "manifest.json",
        PLAN1_STAGE04 / "common_cutflow.csv", PLAN1_STAGE04 / "common_fullband_occupancy.csv",
        PLAN1_STAGE04 / "passive_w_diagnostics.csv",
        *[PLAN1_STAGE04 / filename for filename in SIGNAL_TABLES.values()],
    ]
    if all(nonempty_file(path) for path in signal_inputs):
        try:
            signal_authority = load_plan1_signal_authority()
            authorities["reused_plan1_signal"] = signal_authority["identity"]
        except Exception as exc:
            errors.append(f"Plan-1 stage04 signal small-table authority invalid: {exc}")

    transport = authorities.get("fullstat_activation_and_transport") or {}
    if delayed_registry and transport:
        positive = [family for family in FAMILIES if delayed_registry[family]["execution_disposition"] == POSITIVE_DISPOSITION]
        zero = [family for family in FAMILIES if delayed_registry[family]["execution_disposition"] == ZERO_DISPOSITION]
        if positive != transport.get("positive_families") or zero != transport.get("zero_families"):
            errors.append("full-stat stage03 dispositions differ from activation/transport authorities")

    ready = not errors and not missing
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": (
            "READY__SF3_FULLSTAT_COMMON_RESPONSE_INPUTS"
            if ready else "NOT_READY__SF3_FULLSTAT_COMMON_RESPONSE_INPUTS_INCOMPLETE"
        ),
        "ready": ready,
        "config": str(config_path.resolve()),
        "output": str(OUTPUT),
        "output_already_exists": OUTPUT.exists(),
        "workers_allowed": [1, 2, 3, 4, 5, 6],
        "production_default_workers": DEFAULT_WORKERS,
        "missing": sorted(set(missing)),
        "errors": errors,
        "authorities": authorities,
        "delayed_dispositions": {
            family: delayed_registry[family]["execution_disposition"]
            for family in FAMILIES if family in delayed_registry
        },
        "signal_reuse_policy": SIGNAL_REUSE_AUTHORITY,
        "signal_SIM_or_receipt_artifact_opened": False,
        "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__NAMED_SMALL_AUTHORITIES_AND_COMPACT_CATALOG_STAT_ONLY",
    }


def validate_background_results(
    results: Sequence[dict[str, Any]],
    delayed_registry: dict[str, dict[str, Any]],
) -> None:
    expected = {(stream, family) for stream in ("prompt", "delayed") for family in FAMILIES}
    observed: set[tuple[str, str]] = set()
    for result in results:
        stream = str(result.get("stream", ""))
        family = str(result.get("family", ""))
        key = (stream, family)
        if key not in expected or key in observed:
            raise RuntimeError(f"full-stat response cell identity/duplication differs: {key}")
        observed.add(key)
        meta = result.get("meta") or {}
        if meta.get("geometry") != "SF3" or meta.get("family") != family:
            raise RuntimeError(f"full-stat response catalog geometry/family differs: {key}")
        expected_mode = "instant" if stream == "prompt" else "delayed"
        if meta.get("mode") != expected_mode:
            raise RuntimeError(f"full-stat response catalog mode differs: {key}")
        generated = int(meta.get("generated_events", -1))
        weight = float(meta.get("event_weight_cps", math.nan))
        if stream == "prompt":
            if generated != S3D_HISTORIES[("instant", family)]:
                raise RuntimeError(f"full-stat prompt family history count differs: {family}")
            if not math.isfinite(weight) or weight <= 0.0 or float(meta.get("TT_s", 0.0)) <= 0.0:
                raise RuntimeError(f"full-stat prompt normalization differs: {family}")
            if result.get("execution_disposition") != "NOT_APPLICABLE_PROMPT":
                raise RuntimeError(f"full-stat prompt disposition differs: {family}")
        else:
            registry = delayed_registry[family]
            disposition = registry["execution_disposition"]
            if result.get("execution_disposition") != disposition:
                raise RuntimeError(f"full-stat delayed disposition differs after catalog evaluation: {family}")
            if disposition == POSITIVE_DISPOSITION:
                expected_weight = float(registry["transported_ground_activity_Bq"]) / FULLSTAT_DELAYED_EVENTS
                if generated != FULLSTAT_DELAYED_EVENTS or not math.isclose(
                    weight, expected_weight, rel_tol=2.0e-12, abs_tol=1.0e-20
                ):
                    raise RuntimeError(f"full-stat fresh-250k delayed normalization differs: {family}")
            elif generated != 0 or weight != 0.0 or meta.get("sim_opened") is not False or meta.get("catalog_file_opened") is not False:
                raise RuntimeError(f"full-stat structural-zero delayed response differs: {family}")
    if observed != expected:
        raise RuntimeError("full-stat common response does not close prompt+delayed x eight families")


def combine_reused_rows(
    background: Sequence[dict[str, Any]],
    reused: Sequence[dict[str, Any]],
    *,
    label: str,
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in background]
    if not rows or not reused:
        raise RuntimeError(f"cannot combine empty {label} background/signal rows")
    fields = set(rows[0])
    for row in rows:
        if set(row) != fields:
            raise RuntimeError(f"generated {label} schema is internally inconsistent")
    for row in reused:
        if set(row) != fields:
            raise RuntimeError(f"reused Plan-1 signal {label} schema differs from full-stat background schema")
        rows.append(dict(row))
    return rows


def numeric_acceptance_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("trials", "selected_events"):
        output[key] = int(row[key])
    for key in (
        "acceptance", "acceptance_lower95", "acceptance_upper95",
        "input_optics_aeff_cm2", "selected_effective_area_cm2",
        "selected_effective_area_lower95_cm2", "selected_effective_area_upper95_cm2",
    ):
        output[key] = float(row[key])
    return output


def run(config_path: Path = CONFIG, output: Path = OUTPUT, workers: int = DEFAULT_WORKERS) -> dict[str, Any]:
    if workers < 1 or workers > MAX_WORKERS:
        raise ValueError("workers must be within 1..6")
    if output.resolve() != OUTPUT.resolve():
        raise ValueError(f"full-stat common-response output namespace is fixed: {OUTPUT}")
    prerequisite = check_prerequisites(config_path)
    if not prerequisite["ready"]:
        raise RuntimeError(json.dumps(prerequisite, indent=2, sort_keys=True))
    if output.exists():
        raise FileExistsError(f"refusing to overwrite write-once output: {output}")

    config = load_json(config_path)
    validate_response_config_payload(config)
    gate_authority = validate_gate_and_stage07()
    prompt_authority = validate_prompt_authority()
    fullstat_authority = validate_fullstat_activation_and_transport()
    delayed_authority, delayed_registry = validate_delayed_stage()
    signal_authority = load_plan1_signal_authority()
    positive_families = [
        family for family in FAMILIES
        if delayed_registry[family]["execution_disposition"] == POSITIVE_DISPOSITION
    ]
    zero_families = [
        family for family in FAMILIES
        if delayed_registry[family]["execution_disposition"] == ZERO_DISPOSITION
    ]
    if positive_families != fullstat_authority["positive_families"] or zero_families != fullstat_authority["zero_families"]:
        raise RuntimeError("stage03 delayed family dispositions differ from full-stat transport authority")

    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    started = time.monotonic()
    try:
        contract = common.response_contract(config)
        tasks = [{
            "path": prompt_authority["catalogs"][family],
            "stream": "prompt",
            "family": family,
            "execution_disposition": "NOT_APPLICABLE_PROMPT",
            "catalog_origin": "FULLSTAT_STAGE01_26_JOB_FAMILY_CATALOG",
        } for family in FAMILIES]
        tasks.extend({
            "path": delayed_authority["catalogs"][family],
            "stream": "delayed",
            "family": family,
            "execution_disposition": POSITIVE_DISPOSITION,
            "catalog_origin": "FULLSTAT_STAGE03_FRESH250K_TRANSPORT_CATALOG",
        } for family in positive_families)

        results: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(common.evaluate_catalog, task): task for task in tasks}
            for completed, future in enumerate(as_completed(futures), start=1):
                results.append(future.result())
                if completed % 4 == 0 or completed == len(tasks):
                    print(json.dumps({
                        "event": "sf3_fullstat_compact_background_catalog_response",
                        "completed": completed,
                        "total": len(tasks),
                    }, sort_keys=True), flush=True)
        results.extend(
            common.evaluate_structural_zero_delayed(family, delayed_registry[family])
            for family in zero_families
        )
        validate_background_results(results, delayed_registry)

        aeff_cm2 = float(config["signal"]["input_optics_aeff_cm2"])
        background_cutflow = common.common_cutflow(results, aeff_cm2)
        for row in background_cutflow:
            row["authority_status"] = BACKGROUND_AUTHORITY
        expected_background_keys = {
            (stream, family, response, stage, window)
            for stream in ("prompt", "delayed")
            for family in FAMILIES
            for response, stage in common.CANONICAL_STAGES
            for window in common.FINAL_WINDOWS
        }
        observed_background_keys = {
            (row["stream"], row["family"], row["response_state"], row["stage"], row["window_id"])
            for row in background_cutflow
        }
        if observed_background_keys != expected_background_keys or len(background_cutflow) != len(expected_background_keys):
            raise RuntimeError("full-stat background common-cutflow closure differs")
        cutflow = combine_reused_rows(
            background_cutflow, signal_authority["tables"]["cutflow"], label="common cutflow"
        )

        background = common.background_summary(background_cutflow)
        for row in background:
            row["authority_status"] = BACKGROUND_AUTHORITY
            row["comparison_role"] = "FRESH_SF3_FULLSTAT_CANDIDATE"
        background_occupancy = common.occupancy_rows(results, aeff_cm2)
        for row in background_occupancy:
            row["authority_status"] = BACKGROUND_AUTHORITY
        occupancy = combine_reused_rows(
            background_occupancy, signal_authority["tables"]["occupancy"], label="occupancy"
        )
        selected = [row for result in results for row in result["selected"]]
        background_passive_w = common.passive_w_summary_rows(results)
        passive_w_rows = combine_reused_rows(
            background_passive_w, signal_authority["tables"]["passive_w"], label="passive-W diagnostics"
        )
        if any(row["passive_w_role"] != "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO" for row in passive_w_rows):
            raise RuntimeError("passive W acquired a non-diagnostic response role")
        passive_w_lineage = common.passive_w_source_lineage_rows(selected)

        zero_rows = [{
            "geometry": "SF3",
            "family": family,
            "execution_disposition": ZERO_DISPOSITION,
            "central_delayed_rate_cps": 0.0,
            "transported_ground_activity_Bq": 0.0,
            "buildup_sum_TT_s": delayed_registry[family]["buildup_sum_TT_s"],
            "transported_ground_rate_upper95_s-1": delayed_registry[family]["transported_ground_rate_upper95_s-1"],
            "transported_ground_A15_upper95_Bq_conservative": delayed_registry[family]["transported_ground_A15_upper95_Bq_conservative"],
            "zero_A15_upper_provenance": delayed_registry[family]["zero_A15_upper_provenance"],
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq_reported_separately": delayed_registry[family]["known_holdout_activity_Bq"],
            "unknown_holdout_state_count_reported_separately": delayed_registry[family]["unknown_activity_state_count"],
            "catalog_origin": delayed_registry[family]["catalog_origin"],
            "stage03_catalog_opened": False,
            "SIM_opened": False,
        } for family in zero_families]

        write_csv(work / "common_cutflow.csv", sorted(cutflow, key=lambda row: (
            row["geometry"], row["stream"], row["family"], row["response_state"], row["stage"], row["window_id"],
        )))
        write_csv(work / "common_fullband_occupancy.csv", sorted(
            occupancy, key=lambda row: (row["stream"], row["family"])
        ))
        write_csv(work / "selected_background_w2_lineage.csv", sorted(
            selected, key=lambda row: (row["stream"], row["family"], row["job_name"], row["local_event_id"])
        ), SELECTED_LINEAGE_FIELDS)
        write_csv(work / "background_prompt_delayed_cutflow.csv", sorted(
            background, key=lambda row: (row["geometry"], row["response_state"], row["stage"], row["window_id"])
        ))
        write_csv(work / "passive_w_diagnostics.csv", passive_w_rows)
        write_csv(
            work / "passive_w_selected_delayed_source_lineage.csv",
            passive_w_lineage,
            PASSIVE_W_LINEAGE_FIELDS,
        )
        write_csv(work / "delayed_zero_A15_provenance.csv", zero_rows, ZERO_PROVENANCE_FIELDS)

        for name, filename in SIGNAL_TABLES.items():
            source = signal_authority["paths"][name]
            destination = work / filename
            shutil.copyfile(source, destination)
            if sha256_small(destination) != signal_authority["records"][name]["sha256"]:
                raise RuntimeError(f"byte-identical reused signal table copy failed: {name}")

        acceptance_by_window = {
            str(row["window_id"]): numeric_acceptance_row(row)
            for row in signal_authority["tables"]["acceptance"]
        }
        sf3_final_background = next(
            row for row in background
            if row["response_state"] == common.FINAL_RESPONSE
            and row["stage"] == common.FINAL_STAGE
            and row["window_id"] == "w2_510p58_511p42"
        )
        source_signal = signal_authority["summary"]["signal"]
        signal_summary = {
            **source_signal,
            "reuse_authority": SIGNAL_REUSE_AUTHORITY,
            "source_stage04_small_table_set_sha256": signal_authority["identity"]["small_table_set_sha256"],
            "semantic_signal_SIM_scans_in_this_adapter": 0,
            "signal_SIM_or_receipt_artifact_opened_in_this_adapter": False,
            "final_broad": acceptance_by_window["broad_480_550"],
            "final_w2": acceptance_by_window["w2_510p58_511p42"],
        }
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": STATUS,
            "signal_scope": common.SIGNAL_SCOPE,
            "scope": "conditional full-stat SF3 prompt+rebuilt-actual-position delayed response with byte-identical Plan-1 SF3 signal reuse",
            "response_workers": workers,
            "catalogs": {
                "prompt_registered": 8,
                "prompt_compact_catalogs_opened": 8,
                "delayed_registered": 8,
                "delayed_fresh250k_catalogs_opened": len(positive_families),
                "delayed_structural_zero_catalogs_opened": 0,
                "signal_catalogs_opened": 0,
                "signal_SIMs_or_receipts_opened": 0,
            },
            "delayed_dispositions": {
                POSITIVE_DISPOSITION: positive_families,
                ZERO_DISPOSITION: zero_families,
                "positive_policy": "FRESH_COMPLETE_250000_ONLY__NO_PLAN1_83334_MERGE_OR_REUSE",
                "zero_A15_central_rate_policy": "EXACT_ZERO__NO_CATALOG_OR_SIM_OPEN__FINITE_UPPER_RETAINED",
            },
            "response": contract,
            "signal": signal_summary,
            "final_measured_w2": {
                "SF3_background": sf3_final_background,
                "SF3_signal": acceptance_by_window["w2_510p58_511p42"],
            },
            "fullstat_gate": gate_authority,
            "fullstat_authorities": {
                "prompt": prompt_authority,
                "activation_and_transport": fullstat_authority,
                "delayed": delayed_authority,
            },
            "passive_w": {
                "volumes": sorted(PASSIVE_W_VOLUMES),
                "role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
                "active_veto_members": 0,
                "diagnostic_rows": len(passive_w_rows),
                "selected_delayed_source_lineage_rows": len(passive_w_lineage),
            },
            "outputs": {
                "common_cutflow_rows": len(cutflow),
                "common_fullband_occupancy_rows": len(occupancy),
                "selected_background_w2_lineage_rows": len(selected),
                "background_prompt_delayed_cutflow_rows": len(background),
                "signal_acceptance_rows_reused": len(signal_authority["tables"]["acceptance"]),
                "signal_ray_diagnostic_rows_reused": len(signal_authority["tables"]["ray_diagnostics"]),
                "passive_w_diagnostic_rows": len(passive_w_rows),
                "delayed_zero_A15_provenance_rows": len(zero_rows),
            },
            "elapsed_s": time.monotonic() - started,
            "sim_access": {
                "signal_SIM_opens": 0,
                "signal_receipt_opens": 0,
                "background_SIM_opens": 0,
                "Plan1_83334_delayed_catalog_or_SIM_opens": 0,
                "compact_background_catalog_opens": len(tasks),
            },
            "authority_boundary": "FULLSTAT_COMMON_RESPONSE_COMPLETE__NOT_UPDATED_MISSION_F3_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        write_json(work / "summary.json", summary)
        report = [
            "# Conditional SF3 full-stat common response",
            "",
            f"Status: `{STATUS}`",
            "",
            "The full-stat prompt and rebuilt actual-position delayed catalogs receive the frozen 0.42-keV/0.3-keV/50-keV/W2/Step05 response. The exact three W volumes remain diagnostic-only.",
            "",
            "The fresh SF3 37,194-ray signal is not reopened or recomputed: its Plan-1 signal tables are reused byte-for-byte, while only their already-published signal rows are joined to the new background cutflow, occupancy, and passive-W tables.",
            "",
            f"- Final W2 prompt rate: {sf3_final_background['prompt_rate_cps']:.9g} cps",
            f"- Final W2 delayed rate: {sf3_final_background['delayed_rate_cps']:.9g} cps",
            f"- Final W2 total background: {sf3_final_background['total_background_rate_cps']:.9g} cps",
            f"- Reused W2 signal rays: {acceptance_by_window['w2_510p58_511p42']['selected_events']} / {common.SIGNAL_TRIALS}",
            f"- Fresh-250k delayed catalogs opened: {len(positive_families)}",
            f"- Exact-zero delayed families: {len(zero_families)}",
            "",
        ]
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": STATUS,
            "generated_utc": common.utc_now(),
            "analysis_code": str(Path(__file__).resolve()),
            "reused_response_code": [str(prompt.CORRECTED_CORE), str(prompt.STEP05), str(prompt.STEP09_SUMMARY)],
            "input_small_authorities": {
                "central_gate_and_stage07": gate_authority,
                "fullstat_prompt": {key: value for key, value in prompt_authority.items() if key != "catalogs"},
                "fullstat_activation_and_transport": fullstat_authority,
                "fullstat_delayed": {key: value for key, value in delayed_authority.items() if key != "catalogs"},
                "reused_plan1_signal_records": signal_authority["records"],
            },
            "reused_signal": signal_authority["identity"],
            "files": [{
                "path": str(path.relative_to(work)), "bytes": path.stat().st_size,
            } for path in files],
            "large_payload_policy": {
                "signal_SIM_opens": 0,
                "signal_SIM_stats": 0,
                "signal_SIM_hashes": 0,
                "signal_receipt_opens": 0,
                "background_SIM_opens": 0,
                "background_compact_catalog_opens": len(tasks),
                "delayed_zero_A15_catalog_opens": 0,
                "Plan1_83334_delayed_artifact_opens": 0,
            },
            "write_policy": "WRITE_ONCE__ATOMIC_DIRECTORY_RENAME",
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(json.dumps({
            "status": STATUS,
            "output": str(output),
            "workers": workers,
            "signal_SIM_opens": 0,
            "signal_trials_reused": common.SIGNAL_TRIALS,
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    """Pure synthetic contract test; no production authority or payload is read."""
    if delayed_transport.FULLSTAT_COMPLETE_STATUS != (
        "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE"
    ):
        raise AssertionError("full-stat delayed producer/consumer PASS status drifted")
    shield = ["BGO_A", "BGO_B", "BGO_C"]
    plastic = ["PLASTIC_A", "PLASTIC_B", "PLASTIC_C"]
    config = {
        "analysis": {
            "response_fwhm_keV": 0.42,
            "measured_pixel_threshold_keV": 0.3,
            "active_veto_threshold_keV": 50.0,
            "w2_keV": [510.58, 511.42],
            "step05_policy": "retained_side_compton_fov_reject",
        },
        "geometry": {
            "shield_veto_volumes": shield,
            "plastic_veto_volumes": plastic,
            "active_veto_volumes": shield + plastic,
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "passive_w_never_active_veto": True,
        },
    }
    validate_response_config_payload(config)

    selected_w2 = 7
    selected_broad = 11
    diagnostics = [{
        "ray_id": index,
        "first_interaction_process": "PHOT",
        "first_interaction_volume": "TP_L00",
        "first_interaction_material": "TES_ACTIVE_PIXEL_MATERIAL",
        "first_interaction_resolution": "MATCHED_PRIMARY_CC_HIT_TIME_PROCESS",
        "final_w2_step05_pass": "True" if index < selected_w2 else "False",
        "failure_category": "PASS_W2_VETO_STEP05" if index < selected_w2 else "MEASURED_ENERGY_BELOW_W2",
    } for index in range(common.SIGNAL_TRIALS)]
    acceptance = []
    for window, selected in (
        ("broad_480_550", selected_broad),
        ("w2_510p58_511p42", selected_w2),
    ):
        acceptance.append({
            "geometry": "SF3",
            "response_state": common.FINAL_RESPONSE,
            "stage": common.FINAL_STAGE,
            "window_id": window,
            "trials": common.SIGNAL_TRIALS,
            "selected_events": selected,
            "acceptance": selected / common.SIGNAL_TRIALS,
            "acceptance_lower95": 0.0,
            "acceptance_upper95": 1.0,
            "input_optics_aeff_cm2": 20.08476,
            "selected_effective_area_cm2": 20.08476 * selected / common.SIGNAL_TRIALS,
            "selected_effective_area_lower95_cm2": 0.0,
            "selected_effective_area_upper95_cm2": 20.08476,
            "signal_scope": common.SIGNAL_SCOPE,
            "authority_status": common.SIGNAL_AUTHORITY,
        })
    cutflow = []
    for response, stage in common.CANONICAL_STAGES:
        for window in common.FINAL_WINDOWS:
            selected = (
                selected_w2 if window == "w2_510p58_511p42" else selected_broad
            ) if (response, stage) == (common.FINAL_RESPONSE, common.FINAL_STAGE) else 13
            cutflow.append({
                "geometry": "SF3",
                "stream": "signal",
                "family": common.SIGNAL_FAMILY,
                "response_state": response,
                "stage": stage,
                "window_id": window,
                "selected_events": selected,
            })
    occupancy = [{
        "geometry": "SF3", "stream": "signal", "family": common.SIGNAL_FAMILY,
    }]
    passive_w = [{
        "geometry": "SF3",
        "stream": "signal",
        "family": common.SIGNAL_FAMILY,
        "passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
        "normalization_unit": "cm2",
    }]
    input_manifest = [{
        "geometry": "SF3",
        "job_id": common.SIGNAL_JOB_ID,
        "signal_scope": common.SIGNAL_SCOPE,
        "events": common.SIGNAL_TRIALS,
        "semantic_sim_scans": 1,
        "sim_hash_recomputed": False,
        "eventlist_static_audit_sha256": "a" * 64,
        "sim_path": "/synthetic/not-opened/signal.sim.gz",
    }]
    first_interaction = [{
        "geometry": "SF3",
        "signal_scope": common.SIGNAL_SCOPE,
        "first_interaction_process": "PHOT",
        "first_interaction_volume": "TP_L00",
        "first_interaction_material": "TES_ACTIVE_PIXEL_MATERIAL",
        "first_interaction_resolution": "MATCHED_PRIMARY_CC_HIT_TIME_PROCESS",
        "rays": common.SIGNAL_TRIALS,
        "fraction_of_37194": 1.0,
    }]
    failure = [{
        "geometry": "SF3", "signal_scope": common.SIGNAL_SCOPE,
        "failure_category": "PASS_W2_VETO_STEP05", "rays": selected_w2,
        "fraction_of_37194": selected_w2 / common.SIGNAL_TRIALS,
    }, {
        "geometry": "SF3", "signal_scope": common.SIGNAL_SCOPE,
        "failure_category": "MEASURED_ENERGY_BELOW_W2",
        "rays": common.SIGNAL_TRIALS - selected_w2,
        "fraction_of_37194": (common.SIGNAL_TRIALS - selected_w2) / common.SIGNAL_TRIALS,
    }]
    summary = {
        "profile_id": common.PROFILE_ID,
        "status": "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
        "signal_scope": common.SIGNAL_SCOPE,
        "response": {
            "FWHM_keV": 0.42,
            "measured_pixel_threshold_keV": 0.3,
            "step05_implementation": str(prompt.STEP05),
            "rng_namespace": EXPECTED_RNG_NAMESPACE,
            "response_geometry_key": "sf3",
            "active_veto": {
                "policy_id": "SF3_EXPLICIT_3BGO_PLUS_3PLASTIC",
                "active_veto_volumes": shield + plastic,
                "apply_plastic_veto": True,
                "plastic_threshold_keV": 50.0,
                "shield_thresholds_keV": [0.0, 10.0, 25.0, 50.0],
                "passive_w_volumes": list(PASSIVE_W_VOLUMES),
                "passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
            },
        },
        "signal": {
            "job_id": common.SIGNAL_JOB_ID,
            "eventlist_rows": common.SIGNAL_TRIALS,
            "ray_id_rows": common.SIGNAL_TRIALS,
            "semantic_sim_scans": 1,
            "sim_hashes_recomputed": 0,
            "eventlist_bank_sha256_from_static_audit": "a" * 64,
        },
        "passive_w": {
            "volumes": list(PASSIVE_W_VOLUMES),
            "role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
        },
    }
    manifest = {
        "profile_id": common.PROFILE_ID,
        "status": summary["status"],
        "large_payload_policy": {
            "fresh_signal_SIM_semantic_scans": 1,
            "fresh_signal_SIM_hashes": 0,
        },
    }
    identity = validate_signal_table_payloads(
        summary, manifest, acceptance, first_interaction, failure, cutflow,
        occupancy, diagnostics, passive_w, input_manifest,
    )
    drifted = dict(summary)
    drifted["signal"] = {**summary["signal"], "job_id": "wrong_signal"}
    try:
        validate_signal_table_payloads(
            drifted, manifest, acceptance, first_interaction, failure, cutflow,
            occupancy, diagnostics, passive_w, input_manifest,
        )
    except RuntimeError:
        signal_drift_rejected = True
    else:
        raise AssertionError("synthetic signal identity drift was accepted")

    activity_rows: list[dict[str, Any]] = []
    zero_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, str]] = []
    zero_family = FAMILIES[-1]
    for index, family in enumerate(FAMILIES):
        is_zero = family == zero_family
        activity = 0.0 if is_zero else float(index + 1)
        disposition = ZERO_DISPOSITION if is_zero else POSITIVE_DISPOSITION
        activity_rows.append({
            "family": family,
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": activity,
            "event_weight_cps": 0.0 if is_zero else activity / FULLSTAT_DELAYED_EVENTS,
            "equivalent_time_s": None if is_zero else FULLSTAT_DELAYED_EVENTS / activity,
            "known_holdout_activity_Bq": 0.25 if is_zero else 0.0,
            "unknown_activity_state_count": 1 if is_zero else 0,
        })
        coverage_rows.append({
            "geometry": "SF3",
            "family": family,
            "execution_disposition": disposition,
            "triggers": "0" if is_zero else str(FULLSTAT_DELAYED_EVENTS),
            "catalog_path": "" if is_zero else f"/synthetic/catalog/{family}.pkl",
            "sim_path": "",
            "receipt_path": "",
        })
        if is_zero:
            zero_rows.append({
                "family": family,
                "buildup_sum_TT_s": 100.0,
                "transported_ground_rate_upper95_s-1": 0.03688879454113936,
                "transported_ground_A15_upper95_Bq_conservative": 0.03688879454113936,
                "upper_provenance": "3.6888794541139363/sumTT",
            })
    delayed_summary = {
        "status": "PASS__SF3_FULLSTAT_DELAYED_PURE_SYNTHETIC",
        "registered_source_cells": 8,
        "transport_jobs": 7,
        "skipped_zero_A15_jobs": 1,
        "fresh_triggers_per_positive_family": FULLSTAT_DELAYED_EVENTS,
        "activity_and_weights": activity_rows,
        "zero_source_cells": zero_rows,
        "passive_w_diagnostics": {
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "role": "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES",
        },
        "raw_catalog": {
            "response_applied": False,
            "veto_policy_recorded": {"active_veto_volumes": shield + plastic},
        },
        "sim_scan_policy": {
            "selected_sim_count": 7,
            "semantic_scans": 7,
            "sim_hashes_recomputed": 0,
            "zero_source_sim_count": 0,
        },
    }
    registry = delayed_disposition_registry(delayed_summary, coverage_rows)
    if registry[zero_family]["catalog_required"] or registry[zero_family]["event_weight_cps"] != 0.0:
        raise AssertionError("synthetic structural-zero delayed contract failed")

    def active_veto_pass(shield_keV: float, plastic_keV: float, passive_w_keV: float) -> bool:
        del passive_w_keV
        return shield_keV < ACTIVE_VETO_THRESHOLD_KEV and plastic_keV < ACTIVE_VETO_THRESHOLD_KEV

    if not active_veto_pass(49.999, 49.999, 1.0e12):
        raise AssertionError("passive W incorrectly vetoed a synthetic event")
    if active_veto_pass(50.0, 0.0, 0.0) or active_veto_pass(0.0, 50.0, 0.0):
        raise AssertionError("synthetic six-active-volume 50-keV veto boundary failed")
    drifted_config = json.loads(json.dumps(config))
    drifted_config["geometry"]["active_veto_volumes"].append(next(iter(PASSIVE_W_VOLUMES)))
    try:
        validate_response_config_payload(drifted_config)
    except RuntimeError:
        active_w_rejected = True
    else:
        raise AssertionError("synthetic passive W was accepted as active veto")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_COMMON_RESPONSE_PURE_SYNTHETIC_SELF_TEST",
        "production_authorities_accessed": False,
        "SIM_or_receipt_artifacts_accessed": False,
        "signal_identity": identity,
        "checks": [
            "exact_37194_zero_based_reused_signal_rows",
            "Plan1_signal_identity_drift_fail_closed",
            "byte_copy_source_contract_has_zero_signal_SIM_opens",
            "0p42keV_0p3keV_six_volume_50keV_W2_contract",
            "exact_three_W_whitelist_passive_even_with_arbitrarily_large_deposit",
            "W_in_active_veto_rejected",
            "eight_fullstat_delayed_cells_positive_fresh250k_or_exact_zero",
            "delayed_transport_canonical_PASS_status_bound_to_producer_constant",
            "Plan1_83334_delayed_not_merged",
            "workers_1_through_6_default_4",
        ],
        "signal_identity_drift_rejected": signal_drift_rejected,
        "passive_W_in_active_veto_rejected": active_w_rejected,
        "fullstat_delayed_positive_families": 7,
        "fullstat_delayed_zero_families": 1,
        "workers_allowed": [1, 2, 3, 4, 5, 6],
        "production_default_workers": DEFAULT_WORKERS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > MAX_WORKERS:
        parser.error("--workers must be within 1..6")
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites(args.config.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    run(args.config.resolve(), args.output.resolve(), args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
