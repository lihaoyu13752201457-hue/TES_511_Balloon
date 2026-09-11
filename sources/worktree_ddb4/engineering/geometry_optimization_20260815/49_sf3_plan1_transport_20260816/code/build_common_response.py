#!/usr/bin/env python3
"""Apply the frozen measured-response contract to fresh SF3 Plan-1 data.

Only the fresh SF3 prompt, actual-position delayed, and one 37,194-ray
full-envelope SF3 signal product are accepted.  The three added SF3 tungsten
volumes are diagnostic, passive material: they are fail-closed disjoint from
the unchanged three-BGO plus three-plastic active-veto set.

The fresh signal SIM is decompressed exactly once to build a compact response
catalog and one diagnostic row for every frozen ray ID.  No SIM digest is
computed.  ``--check-prerequisites`` and ``--self-test`` are metadata/static
only and never open a SIM or pickle catalog.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import re
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import run_prompt_analysis as prompt
from sf3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID, REPO_ROOT


HERE = Path(__file__).resolve()
DEFAULT_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
SOURCE_WORKTREE = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
MAIN_WORKTREE = Path("/home/ubuntu/TES_511_Balloon")
HANDOFF_WORKTREE = Path("/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon")

SIGNAL_JOB_ID = "signal_full_envelope_sf3"
SIGNAL_GEOMETRY = "SF3"
SIGNAL_FAMILY = "focused_gamma"
SIGNAL_TRIALS = 37_194
SIGNAL_SCOPE = "FULL_ENVELOPE_SF3_ONLY"
SIGNAL_AUTHORITY = "FRESH_SF3_FULL_ENVELOPE_37194_SINGLE_SEMANTIC_SCAN"
BACKGROUND_AUTHORITY = "FRESH_SF3_PLAN1_PROMPT_DELAYED_COMMON_RESPONSE"
PASSIVE_W_VOLUMES = frozenset({
    "SF3_W_NearField_FrontWindowPlate_2p9mm",
    "SF3_W_NearField_SideSleeve_2p9mm",
    "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
})

FAMILY_ORDER = tuple(FAMILIES)
STREAMS = ("prompt", "delayed")
DELAYED_RUN_DISPOSITION = "RUN_83334"
DELAYED_ZERO_DISPOSITION = "SKIP_ZERO_A15"
WINDOWS = prompt.WINDOWS
CANONICAL_STAGES = {
    ("raw", "pre_veto"),
    ("raw", "active_veto50"),
    ("measured", "pre_veto"),
    ("measured", "active_veto50"),
    ("measured", "side_compton_fov_pass"),
}
FINAL_RESPONSE = "measured"
FINAL_STAGE = "side_compton_fov_pass"
FINAL_WINDOWS = ("broad_480_550", "w2_510p58_511p42")

MAX_SMALL_JSON_BYTES = 16 * 1024**2
MAX_SMALL_CSV_BYTES = 128 * 1024**2
IA_RE = re.compile(r"^IA\s+(?P<process>\S+)\s+(?P<body>.*)$")
CC_META_RE = re.compile(
    r"\bt=(?P<time>[-+0-9.eE]+)\s+sec=(?P<secondary>\S+)\s+"
    r"tid=(?P<tid>\d+)\s+pid=(?P<pid>\d+)\s+sproc=(?P<sproc>\S+)"
)
SOURCE_EVENTLIST_RE = re.compile(r"\.EventList\s+(?P<path>\S+)\s*$")
VOLUME_MATERIAL_RE = re.compile(r"^(?P<volume>\S+)\.Material\s+(?P<material>\S+)\s*$")
INCLUDE_RE = re.compile(r"^Include\s+(?P<path>\S+)\s*$")

_RUNTIME: tuple[Any, Any, dict[str, Any]] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, *, small_only: bool = False) -> dict[str, Any]:
    if small_only and path.stat().st_size > MAX_SMALL_JSON_BYTES:
        raise RuntimeError(f"refusing non-small JSON authority: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_csv(path: Path, *, small_only: bool = False) -> list[dict[str, str]]:
    if small_only and path.stat().st_size > MAX_SMALL_CSV_BYTES:
        raise RuntimeError(f"refusing non-small CSV authority: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: Iterable[dict[str, Any]],
    fields: list[str] | tuple[str, ...] | None = None,
) -> None:
    materialized = list(rows)
    names = list(fields) if fields is not None else (list(materialized[0]) if materialized else [])
    if not names:
        raise RuntimeError(f"refusing schema-less CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def sha256_small(path: Path, *, max_bytes: int = MAX_SMALL_JSON_BYTES) -> str:
    if path.stat().st_size > max_bytes:
        raise RuntimeError(f"refusing large-payload digest: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def repository_tail(path: Path) -> Path | None:
    parts = path.parts
    try:
        index = parts.index("TES_511_Balloon")
    except ValueError:
        return None
    return Path(*parts[index + 1 :])


def resolve_declared_path(value: str | Path) -> Path:
    """Resolve an authority without erasing its cross-worktree provenance.

    Existing absolute paths win.  A missing absolute path receives explicit
    repository-tail fallbacks across the current, retained, handoff, and main
    worktrees.  Relative paths use the same ordered roots.
    """
    declared = Path(value).expanduser()
    candidates: list[Path] = []
    if declared.is_absolute():
        candidates.append(declared)
        tail = repository_tail(declared)
        if tail is not None:
            candidates.extend(root / tail for root in (
                REPO_ROOT, SOURCE_WORKTREE, HANDOFF_WORKTREE, MAIN_WORKTREE
            ))
    else:
        candidates.extend(root / declared for root in (
            REPO_ROOT, PACKAGE_ROOT, SOURCE_WORKTREE, HANDOFF_WORKTREE, MAIN_WORKTREE
        ))
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def input_paths(config: dict[str, Any]) -> dict[str, Path]:
    stage01 = resolve_declared_path(config["outputs"]["stage_01"])
    stage03 = resolve_declared_path(config["outputs"]["stage_03"])
    audits = config.get("audits") or {}
    geometry_authorities = config.get("geometry", {}).get("sf3_geometry_authorities", {})
    return {
        "prompt_summary": stage01 / "summary.json",
        "prompt_catalog": stage01 / "catalog/SF3",
        "delayed_summary": stage03 / "summary.json",
        "delayed_coverage": stage03 / "delayed_cell_coverage.csv",
        "delayed_catalog": stage03 / "catalog/SF3",
        "sf3_native_navigation": resolve_declared_path(
            geometry_authorities["native"]
        ),
        "signal_transport_gate": resolve_declared_path(
            audits.get(
                "signal_transport_gate",
                PACKAGE_ROOT / "audit/full_envelope_signal_transport_gate.json",
            )
        ),
        "signal_static_audit": resolve_declared_path(
            audits.get(
                "signal_static",
                PACKAGE_ROOT / "audit/full_envelope_signal_static_audit.json",
            )
        ),
    }


def signal_plan_row(config: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row for row in prompt.read_plan(config)
        if row["job_id"] == SIGNAL_JOB_ID
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected one {SIGNAL_JOB_ID} plan row, found {len(rows)}")
    row = rows[0]
    expected = {
        "stage": "signal",
        "geometry": SIGNAL_GEOMETRY,
        "mode": "signal",
        "family": SIGNAL_FAMILY,
        "events": SIGNAL_TRIALS,
    }
    for name, value in expected.items():
        if row[name] != value:
            raise RuntimeError(f"signal plan {name}={row[name]!r}, expected {value!r}")
    return row


def receipt_path(config: dict[str, Any]) -> Path:
    return resolve_declared_path(config["run_root"]) / "receipts" / f"{SIGNAL_JOB_ID}.json"


def source_eventlist(path: Path) -> Path:
    matches = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = SOURCE_EVENTLIST_RE.search(line.strip())
        if match:
            matches.append(resolve_declared_path(match.group("path")))
    if len(matches) != 1:
        raise RuntimeError(f"expected one EventList declaration in {path}, found {len(matches)}")
    return matches[0]


def delayed_disposition_registry(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """Read the stage-03 eight-family disposition contract from small tables.

    A ``SKIP_ZERO_A15`` cell intentionally has no delayed pickle and no SIM.
    Its central response contribution is zero, while its finite activation
    upper limit remains separate provenance.  This function never opens a
    catalog or a SIM.
    """
    summary = load_json(paths["delayed_summary"], small_only=True)
    status = str(summary.get("status", ""))
    if not status.startswith("PASS__"):
        raise RuntimeError(f"delayed_summary status is not PASS: {status}")
    activity_rows = summary.get("activity_and_weights", [])
    zero_rows = summary.get("zero_source_cells", [])
    if not isinstance(activity_rows, list) or not isinstance(zero_rows, list):
        raise RuntimeError("stage03 delayed disposition arrays are malformed")

    coverage_rows = read_csv(paths["delayed_coverage"], small_only=True)
    coverage_by_family: dict[str, dict[str, str]] = {}
    for row in coverage_rows:
        if row.get("geometry") != SIGNAL_GEOMETRY:
            continue
        family = str(row.get("family", ""))
        if not family or family in coverage_by_family:
            raise RuntimeError(f"stage03 delayed coverage family key differs: {family!r}")
        coverage_by_family[family] = row

    zero_by_family: dict[str, dict[str, Any]] = {}
    for row in zero_rows:
        if not isinstance(row, dict):
            raise RuntimeError("stage03 zero-source record is not an object")
        family = str(row.get("family", ""))
        if not family or family in zero_by_family:
            raise RuntimeError(f"stage03 zero-source family key differs: {family!r}")
        zero_by_family[family] = row

    registry: dict[str, dict[str, Any]] = {}
    for row in activity_rows:
        if not isinstance(row, dict):
            raise RuntimeError("stage03 activity/weight record is not an object")
        family = str(row.get("family", ""))
        if family not in FAMILY_ORDER or family in registry:
            raise RuntimeError(f"stage03 delayed family key differs: {family!r}")
        disposition = str(row.get("execution_disposition", ""))
        if disposition not in (DELAYED_RUN_DISPOSITION, DELAYED_ZERO_DISPOSITION):
            raise RuntimeError(
                f"stage03 delayed disposition differs for {family}: {disposition!r}"
            )
        coverage = coverage_by_family.get(family)
        if coverage is None:
            raise RuntimeError(f"stage03 delayed coverage omits {family}")
        if coverage.get("execution_disposition") != disposition:
            raise RuntimeError(f"stage03 summary/coverage disposition differs for {family}")
        activity = float(row.get("transported_ground_activity_Bq", math.nan))
        item: dict[str, Any] = {
            "family": family,
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": activity,
            "event_weight_cps": float(row.get("event_weight_cps", 0.0) or 0.0),
            "equivalent_time_s": row.get("equivalent_time_s"),
            "known_holdout_activity_Bq": float(row.get("known_holdout_activity_Bq", 0.0)),
            "unknown_activity_state_count": int(row.get("unknown_activity_state_count", 0)),
            "catalog_required": disposition == DELAYED_RUN_DISPOSITION,
            "catalog_origin": (
                "STAGE03_TRANSPORT_CATALOG"
                if disposition == DELAYED_RUN_DISPOSITION
                else "STRUCTURAL_EMPTY_ZERO_RATE__NO_STAGE03_CATALOG_OR_SIM"
            ),
        }
        if disposition == DELAYED_RUN_DISPOSITION:
            if not math.isfinite(activity) or activity <= 0.0:
                raise RuntimeError(f"stage03 RUN delayed activity is not positive: {family}")
            if family in zero_by_family:
                raise RuntimeError(f"stage03 RUN family appears in zero-source records: {family}")
            if not str(coverage.get("catalog_path", "")).strip():
                raise RuntimeError(f"stage03 RUN delayed coverage lacks catalog path: {family}")
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
                raise RuntimeError(f"stage03 zero-source records omit {family}")
            rate_upper = float(zero.get("transported_ground_rate_upper95_s-1", math.nan))
            a15_upper = float(
                zero.get("transported_ground_A15_upper95_Bq_conservative", math.nan)
            )
            buildup_sum_tt = float(zero.get("buildup_sum_TT_s", math.nan))
            provenance = str(zero.get("upper_provenance", ""))
            if activity != 0.0 or float(coverage.get("central_delayed_rate_cps", "nan")) != 0.0:
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 central value is not zero: {family}")
            if int(float(coverage.get("triggers", "-1"))) != 0:
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 coverage has triggers: {family}")
            if any(str(coverage.get(name, "")).strip() for name in (
                "catalog_path", "sim_path", "receipt_path"
            )):
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 publishes transport artifacts: {family}")
            if not all(math.isfinite(value) and value > 0.0 for value in (
                rate_upper, a15_upper, buildup_sum_tt
            )):
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 finite upper differs: {family}")
            if not math.isclose(rate_upper, a15_upper, rel_tol=0.0, abs_tol=1.0e-18):
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 rate/A15 upper differs: {family}")
            if not provenance or "sumTT" not in provenance:
                raise RuntimeError(f"stage03 SKIP_ZERO_A15 upper provenance is absent: {family}")
            item.update({
                "event_weight_cps": 0.0,
                "equivalent_time_s": None,
                "buildup_sum_TT_s": buildup_sum_tt,
                "transported_ground_rate_upper95_s-1": rate_upper,
                "transported_ground_A15_upper95_Bq_conservative": a15_upper,
                "zero_A15_upper_provenance": provenance,
                "upper_excludes_known_and_unresolved_holdout": True,
            })
        registry[family] = item

    if set(registry) != set(FAMILY_ORDER) or set(coverage_by_family) != set(FAMILY_ORDER):
        raise RuntimeError("stage03 delayed summary/coverage does not close all eight families")
    zero_families = {
        family for family, row in registry.items()
        if row["execution_disposition"] == DELAYED_ZERO_DISPOSITION
    }
    if set(zero_by_family) != zero_families:
        raise RuntimeError("stage03 delayed zero-source registry closure differs")
    if int(summary.get("registered_source_cells", -1)) != len(FAMILY_ORDER):
        raise RuntimeError("stage03 registered delayed source-cell count differs")
    if int(summary.get("transport_jobs", -1)) != len(FAMILY_ORDER) - len(zero_families):
        raise RuntimeError("stage03 delayed transport-job count differs")
    if int(summary.get("skipped_zero_A15_jobs", -1)) != len(zero_families):
        raise RuntimeError("stage03 skipped-zero delayed count differs")
    return registry


def _retired_se3_check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Validate metadata and small tables without opening a SIM or catalog."""
    config_path = config_path.resolve()
    errors: list[str] = []
    missing_inputs: list[str] = []
    validated: dict[str, Any] = {}
    try:
        config = load_json(config_path, small_only=True)
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "FAIL__SE3_COMMON_RESPONSE_CONFIG",
            "ready": False,
            "errors": [str(exc)],
            "missing_inputs": [],
            "sim_access_policy": "NO_SIM_OPEN_OR_HASH",
        }

    paths = input_paths(config)
    required_files: dict[str, Path] = {
        "prompt_summary": paths["prompt_summary"],
        "delayed_summary": paths["delayed_summary"],
        "delayed_coverage": paths["delayed_coverage"],
        "signal_navigation_audit": paths["signal_navigation_audit"],
        "signal_transport_gate": paths["signal_transport_gate"],
        "signal_static_audit": paths["signal_static_audit"],
        "user_scope_override": paths["user_scope_override"],
        "frozen_s3d_background": paths["frozen_s3d_background"],
        "job_plan": resolve_declared_path(config["transport"]["job_plan"]),
        "retained_response_core": prompt.CORRECTED_CORE,
        "retained_step05": prompt.STEP05,
        "retained_catalog_parser": prompt.OLD_CATALOG_PARSER,
        "retained_step09_bridge": prompt.STEP09_SUMMARY,
    }
    for family in FAMILY_ORDER:
        required_files[f"prompt_catalog_{family}"] = paths["prompt_catalog"] / f"{family}.pkl"
    delayed_registry: dict[str, dict[str, Any]] = {}
    if (
        paths["delayed_summary"].is_file()
        and paths["delayed_summary"].stat().st_size > 0
        and paths["delayed_coverage"].is_file()
        and paths["delayed_coverage"].stat().st_size > 0
    ):
        try:
            delayed_registry = delayed_disposition_registry(paths)
            for family, row in delayed_registry.items():
                if row["catalog_required"]:
                    required_files[f"delayed_catalog_{family}"] = (
                        paths["delayed_catalog"] / f"{family}.pkl"
                    )
            zero_families = [
                family for family in FAMILY_ORDER
                if delayed_registry[family]["execution_disposition"] == DELAYED_ZERO_DISPOSITION
            ]
            validated.update({
                "delayed_registered_source_cells": len(delayed_registry),
                "delayed_transport_catalogs_required": len(delayed_registry) - len(zero_families),
                "delayed_structural_zero_catalogs": len(zero_families),
                "delayed_zero_A15_families": zero_families,
                "delayed_zero_A15_catalog_or_SIM_required": False,
            })
        except Exception as exc:
            errors.append(f"stage03 delayed disposition contract invalid: {exc}")
    for role, path in required_files.items():
        if not path.is_file() or path.stat().st_size <= 0:
            missing_inputs.append(f"{role}:{path}")

    analysis = config.get("analysis", {})
    if not math.isclose(float(analysis.get("response_fwhm_keV", -1)), 0.42, rel_tol=0.0, abs_tol=0.0):
        errors.append("response_fwhm_keV is not 0.42")
    if not math.isclose(float(analysis.get("measured_pixel_threshold_keV", -1)), 0.3, rel_tol=0.0, abs_tol=0.0):
        errors.append("measured_pixel_threshold_keV is not 0.3")
    if tuple(float(value) for value in analysis.get("w2_keV", [])) != WINDOWS["w2_510p58_511p42"]:
        errors.append("configured W2 differs from 510.58--511.42 keV")
    try:
        policy = prompt.explicit_veto_policy(config)
        if len(policy["shield_volumes"]) != 3 or len(policy["plastic_volumes"]) != 3:
            errors.append("explicit veto policy is not exactly 3 BGO plus 3 plastic volumes")
        if not policy["apply_plastic_veto"]:
            errors.append("SE3 plastic veto is not enabled")
    except Exception as exc:
        errors.append(f"explicit veto policy invalid: {exc}")

    plan: dict[str, Any] | None = None
    try:
        plan = signal_plan_row(config)
        exclusion = config.get("transport", {}).get("execution_exclusions", {})
        if "signal_full_envelope_s3d_o8" not in exclusion:
            errors.append("config lacks explicit fresh-S3d transport exclusion")
    except Exception as exc:
        errors.append(str(exc))

    stage_status: dict[str, str] = {}
    if not missing_inputs:
        try:
            for role in ("prompt_summary", "delayed_summary"):
                summary = load_json(paths[role], small_only=True)
                stage_status[role] = str(summary.get("status", ""))
                if not stage_status[role].startswith("PASS__"):
                    errors.append(f"{role} status is not PASS: {stage_status[role]}")

            navigation = load_json(paths["signal_navigation_audit"], small_only=True)
            gate = load_json(paths["signal_transport_gate"], small_only=True)
            static = load_json(paths["signal_static_audit"], small_only=True)
            scope_override = load_json(paths["user_scope_override"], small_only=True)
            nav_se3 = navigation.get("geometries", {}).get("SE3", {})
            if navigation.get("driver_validation", {}).get("status") != "PASS":
                errors.append("native signal navigation driver status is not PASS")
            if nav_se3.get("status") != "PASS":
                errors.append("native SE3 navigation status is not PASS")
            if int(nav_se3.get("parsed_rows", -1)) != SIGNAL_TRIALS:
                errors.append("native SE3 navigation row count differs")
            if int(nav_se3.get("bpe", {}).get("zero_chord_passes", -1)) != SIGNAL_TRIALS:
                errors.append("SE3 full-envelope ray bank is not fully through the BPE port")
            if int(nav_se3.get("plastic", {}).get("full_chord_passes", -1)) != SIGNAL_TRIALS:
                errors.append("SE3 full-envelope ray bank lacks full plastic-chord closure")
            nav_sha = sha256_small(paths["signal_navigation_audit"])
            if gate.get("status") != "PASS" or gate.get("authority", {}).get("sha256") != nav_sha:
                errors.append("signal transport gate does not bind the current PASS navigation audit")
            if gate.get("transport_scope") != SIGNAL_SCOPE:
                errors.append("signal transport gate scope is not FULL_ENVELOPE_SE3_ONLY")
            if set(gate.get("permitted_signal_jobs", [])) != {SIGNAL_JOB_ID}:
                errors.append("signal transport gate permitted jobs are not exactly SE3-only")
            gate_exclusions = gate.get("excluded_signal_jobs", {})
            s3d_exclusion = str(gate_exclusions.get("signal_full_envelope_s3d_o8", ""))
            if "USER_SCOPE" not in s3d_exclusion or "NO_S3D_RERUN" not in s3d_exclusion:
                errors.append("signal transport gate lacks the user-scope S3d exclusion")
            configured_exclusion = str(
                config.get("transport", {}).get("execution_exclusions", {}).get(
                    "signal_full_envelope_s3d_o8", ""
                )
            )
            if configured_exclusion != s3d_exclusion:
                errors.append("config/gate S3d user-scope exclusion binding differs")
            declared_scope_override = resolve_declared_path(
                str(gate.get("scope_override_authority", ""))
            )
            if declared_scope_override != paths["user_scope_override"]:
                errors.append("signal gate scope_override_authority path binding differs")
            if not str(scope_override.get("status", "")).startswith("PASS__"):
                errors.append("user scope-override authority status is not PASS")
            override_exclusion = str(
                scope_override.get("excluded_transport_jobs", {}).get(
                    "signal_full_envelope_s3d_o8", ""
                )
            )
            if "USER_EXPLICITLY_FORBADE_S3D_RERUN" not in override_exclusion:
                errors.append("scope override does not explicitly forbid the S3d rerun")
            if int(gate.get("paired_bank_rows", -1)) != SIGNAL_TRIALS:
                errors.append("signal transport gate ray count differs")
            static_se3 = [
                row for row in static.get("pair", {}).get("jobs", [])
                if row.get("job_id") == SIGNAL_JOB_ID
            ]
            if len(static_se3) != 1 or int(static_se3[0].get("events", -1)) != SIGNAL_TRIALS:
                errors.append("static audit lacks one 37,194-ray SE3 signal job")
            frozen_bank = static.get("frozen_bank", {})
            if (
                int(frozen_bank.get("data_rows", -1)) != SIGNAL_TRIALS
                or int(frozen_bank.get("first_id", -1)) != 0
                or int(frozen_bank.get("last_id", -1)) != SIGNAL_TRIALS - 1
                or frozen_bank.get("zero_based_sequential_ids") is not True
            ):
                errors.append("static audit does not bind zero-based ray IDs 0..37193")
            if gate.get("paired_bank_sha256") != frozen_bank.get("output_sha256"):
                errors.append("navigation transport gate and static audit bank digests differ")
            if static.get("pair", {}).get("no_resampling_or_bootstrap") is not True:
                errors.append("static signal audit does not forbid resampling/bootstrap")

            frozen_rows = validate_frozen_background(paths["frozen_s3d_background"])
            validated["frozen_s3d_background_rows"] = frozen_rows
            validated["frozen_s3d_signal_tables_opened"] = 0
            validated["fresh_s3d_receipt_required"] = False
        except Exception as exc:
            errors.append(str(exc))

    receipt = receipt_path(config)
    if not receipt.is_file() or receipt.stat().st_size <= 0:
        missing_inputs.append(f"signal_receipt:{receipt}")
    elif plan is not None:
        try:
            payload = load_json(receipt, small_only=True)
            if payload.get("status") != "PASS":
                errors.append("SE3 signal receipt status is not PASS")
            for name, expected in (
                ("job_id", SIGNAL_JOB_ID),
                ("stage", "signal"),
                ("geometry", SIGNAL_GEOMETRY),
                ("mode", "signal"),
                ("events", SIGNAL_TRIALS),
                ("seed", int(plan["seed"])),
            ):
                if payload.get(name) != expected:
                    errors.append(f"SE3 signal receipt {name} differs")
            if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
                errors.append("SE3 signal receipt violates the no-SIM-digest contract")
            sim_path = resolve_declared_path(str(payload.get("sim_path", "")))
            source_path = resolve_declared_path(str(payload.get("source_path", "")))
            log_path = resolve_declared_path(str(payload.get("log_path", "")))
            for role, artifact, size_field in (
                ("signal_sim", sim_path, "sim_bytes"),
                ("signal_source", source_path, None),
                ("signal_log", log_path, "log_bytes"),
            ):
                if not artifact.is_file() or artifact.stat().st_size <= 0:
                    missing_inputs.append(f"{role}:{artifact}")
                elif size_field and artifact.stat().st_size != int(payload.get(size_field, -1)):
                    errors.append(f"{role} byte count differs from receipt")
            if source_path.is_file():
                if sha256_small(source_path) != payload.get("source_sha256"):
                    errors.append("SE3 signal source digest differs from receipt")
                eventlist = source_eventlist(source_path)
                if not eventlist.is_file() or eventlist.stat().st_size <= 0:
                    missing_inputs.append(f"signal_eventlist:{eventlist}")
                else:
                    validated["eventlist_path"] = str(eventlist)
                    static = load_json(paths["signal_static_audit"], small_only=True)
                    static_jobs = [
                        row for row in static.get("pair", {}).get("jobs", [])
                        if row.get("job_id") == SIGNAL_JOB_ID
                    ]
                    if len(static_jobs) != 1:
                        errors.append("static audit SE3 signal job binding differs")
                    else:
                        declared_eventlist = resolve_declared_path(
                            str(static_jobs[0].get("eventlist_path", ""))
                        )
                        if eventlist != declared_eventlist:
                            errors.append("receipt source EventList differs from static audit")
                        expected_bank_sha = str(static["frozen_bank"]["output_sha256"])
                        if static_jobs[0].get("eventlist_sha256") != expected_bank_sha:
                            errors.append("static SE3 job EventList digest differs from frozen bank")
                        if sha256_small(eventlist) != expected_bank_sha:
                            errors.append("on-disk projected SE3 EventList digest differs from static audit")
            header = payload.get("sim_header", {})
            if resolve_declared_path(str(header.get("geometry", ""))) != resolve_declared_path(plan["setup_path"]):
                errors.append("SE3 signal receipt header geometry differs from the plan")
            if header.get("seed") != int(plan["seed"]):
                errors.append("SE3 signal receipt header seed differs from the plan")
            validated.update({
                "signal_receipt": str(receipt),
                "signal_sim_path": str(sim_path),
                "signal_sim_bytes": payload.get("sim_bytes"),
                "signal_events": SIGNAL_TRIALS,
                "signal_seed": plan["seed"],
            })
        except Exception as exc:
            errors.append(f"SE3 signal receipt invalid: {exc}")

    ready = not errors and not missing_inputs
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": (
            "READY__SE3_COMMON_RESPONSE_INPUTS_AND_FULL_ENVELOPE_SIGNAL"
            if ready else "NOT_READY__SE3_COMMON_RESPONSE_INPUTS_INCOMPLETE"
        ),
        "ready": ready,
        "config": str(config_path),
        "signal_scope": SIGNAL_SCOPE,
        "fresh_s3d_transport_required": False,
        "fresh_s3d_signal_required": False,
        "old_post_be_signal_permitted_as_ratio_denominator": False,
        "missing_inputs": sorted(set(missing_inputs)),
        "errors": errors,
        "stage_status": stage_status,
        "validated": validated,
        "delayed_dispositions": {
            family: row["execution_disposition"]
            for family, row in delayed_registry.items()
        },
        "input_paths": {name: display_path(path) for name, path in paths.items()},
        "sim_access_policy": "STAT_ONLY__NO_SIM_OR_CATALOG_OPEN_OR_HASH",
    }


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Fail-closed SF3 metadata gate; never opens a SIM or pickle catalog."""
    config_path = config_path.resolve()
    errors: list[str] = []
    missing_inputs: list[str] = []
    validated: dict[str, Any] = {}
    try:
        config = load_json(config_path, small_only=True)
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "FAIL__SF3_COMMON_RESPONSE_CONFIG",
            "ready": False,
            "errors": [str(exc)],
            "missing_inputs": [],
            "sim_access_policy": "NO_SIM_OPEN_OR_HASH",
        }

    paths = input_paths(config)
    geometry = config.get("geometry", {})
    geometry_authorities = geometry.get("sf3_geometry_authorities", {})
    required_files: dict[str, Path] = {
        "prompt_summary": paths["prompt_summary"],
        "delayed_summary": paths["delayed_summary"],
        "delayed_coverage": paths["delayed_coverage"],
        "sf3_native_navigation": paths["sf3_native_navigation"],
        "signal_transport_gate": paths["signal_transport_gate"],
        "signal_static_audit": paths["signal_static_audit"],
        "job_plan": resolve_declared_path(config["transport"]["job_plan"]),
        "retained_response_core": prompt.CORRECTED_CORE,
        "retained_step05": prompt.STEP05,
        "retained_catalog_parser": prompt.OLD_CATALOG_PARSER,
        "retained_step09_bridge": prompt.STEP09_SUMMARY,
    }
    for role in ("static", "mesh", "overlap", "native"):
        declared = geometry_authorities.get(role)
        if not declared:
            errors.append(f"SF3 geometry authority is not configured: {role}")
        else:
            required_files[f"sf3_geometry_{role}"] = resolve_declared_path(declared)
    for family in FAMILY_ORDER:
        required_files[f"prompt_catalog_{family}"] = paths["prompt_catalog"] / f"{family}.pkl"

    delayed_registry: dict[str, dict[str, Any]] = {}
    if paths["delayed_summary"].is_file() and paths["delayed_coverage"].is_file():
        try:
            delayed_registry = delayed_disposition_registry(paths)
            for family, row in delayed_registry.items():
                if row["catalog_required"]:
                    required_files[f"delayed_catalog_{family}"] = (
                        paths["delayed_catalog"] / f"{family}.pkl"
                    )
            zero_families = sorted(
                family for family, row in delayed_registry.items()
                if not row["catalog_required"]
            )
            validated.update({
                "delayed_registered_source_cells": len(delayed_registry),
                "delayed_transport_catalogs_required": len(delayed_registry) - len(zero_families),
                "delayed_structural_zero_catalogs": len(zero_families),
                "delayed_zero_A15_families": zero_families,
            })
        except Exception as exc:
            errors.append(f"stage03 delayed disposition contract invalid: {exc}")

    for role, path in required_files.items():
        if not path.is_file() or path.stat().st_size <= 0:
            missing_inputs.append(f"{role}:{path}")

    analysis = config.get("analysis", {})
    if float(analysis.get("response_fwhm_keV", -1)) != 0.42:
        errors.append("response_fwhm_keV is not exactly 0.42")
    if float(analysis.get("measured_pixel_threshold_keV", -1)) != 0.3:
        errors.append("measured_pixel_threshold_keV is not exactly 0.3")
    if tuple(float(value) for value in analysis.get("w2_keV", [])) != WINDOWS["w2_510p58_511p42"]:
        errors.append("configured W2 differs from 510.58--511.42 keV")
    if float(analysis.get("active_veto_threshold_keV", -1)) != 50.0:
        errors.append("active-veto threshold is not exactly 50 keV")

    try:
        policy = prompt.explicit_veto_policy(config)
        shield = set(policy["shield_volumes"])
        plastic = set(policy["plastic_volumes"])
        active = set(policy["active_veto_volumes"])
        passive_w = set(geometry.get("passive_w_volumes", []))
        if len(shield) != 3 or len(plastic) != 3 or active != shield | plastic:
            errors.append("active-veto policy is not exactly 3 BGO plus 3 plastic volumes")
        if not policy["apply_plastic_veto"]:
            errors.append("SF3 plastic veto is not enabled")
        if passive_w != PASSIVE_W_VOLUMES:
            errors.append(f"passive SF3 W closure differs: {sorted(passive_w)}")
        if active & passive_w:
            errors.append("passive SF3 W appears in the active-veto set")
        if geometry.get("passive_w_never_active_veto") is not True:
            errors.append("passive_w_never_active_veto is not true")
        validated["active_veto_volumes"] = sorted(active)
        validated["passive_w_volumes"] = sorted(passive_w)
    except Exception as exc:
        errors.append(f"explicit veto policy invalid: {exc}")

    plan: dict[str, Any] | None = None
    try:
        plan = signal_plan_row(config)
        if resolve_declared_path(plan["setup_path"]) != resolve_declared_path(geometry["sf3_setup"]):
            errors.append("SF3 signal plan setup differs from configured SF3 setup")
    except Exception as exc:
        errors.append(str(exc))

    stage_status: dict[str, str] = {}
    if not missing_inputs:
        try:
            for role in ("prompt_summary", "delayed_summary"):
                summary = load_json(paths[role], small_only=True)
                stage_status[role] = str(summary.get("status", ""))
                if not stage_status[role].startswith("PASS__SF3"):
                    errors.append(f"{role} status is not SF3 PASS: {stage_status[role]}")

            for role in ("static", "mesh", "overlap", "native"):
                authority = load_json(
                    resolve_declared_path(geometry_authorities[role]), small_only=True
                )
                status = str(authority.get("status", ""))
                if status != "PASS" and not status.startswith("PASS__SF3"):
                    errors.append(f"SF3 geometry {role} status is not PASS: {status}")

            native = load_json(paths["sf3_native_navigation"], small_only=True)
            if int(native.get("rows", -1)) != SIGNAL_TRIALS:
                errors.append("SF3 native-navigation ray count differs")
            added_w = native.get("added_W_focused_chord", {})
            if int(added_w.get("zero_rays", -1)) != SIGNAL_TRIALS:
                errors.append("SF3 focused rays do not all have zero added-W chord")
            if int(native.get("W_presence_witnesses", {}).get("volume_passes", -1)) != 3:
                errors.append("SF3 native-navigation audit lacks three W-presence witnesses")

            static = load_json(paths["signal_static_audit"], small_only=True)
            if not str(static.get("status", "")).startswith("PASS__SF3"):
                errors.append("SF3 signal static audit is not PASS")
            if static.get("geometry") != SIGNAL_GEOMETRY or int(static.get("rows", -1)) != SIGNAL_TRIALS:
                errors.append("SF3 signal static geometry/ray closure differs")
            static_job = static.get("signal", {}).get("job", {})
            if static_job.get("job_id") != SIGNAL_JOB_ID or int(static_job.get("events", -1)) != SIGNAL_TRIALS:
                errors.append("SF3 signal static audit job binding differs")
            if static.get("signal", {}).get("no_resampling_or_bootstrap") is not True:
                errors.append("SF3 signal static audit does not forbid resampling/bootstrap")
            frozen_bank = static.get("frozen_bank", {})
            if (
                int(frozen_bank.get("data_rows", -1)) != SIGNAL_TRIALS
                or int(frozen_bank.get("first_id", -1)) != 0
                or int(frozen_bank.get("last_id", -1)) != SIGNAL_TRIALS - 1
                or frozen_bank.get("zero_based_sequential_ids") is not True
            ):
                errors.append("SF3 signal static audit ray-ID closure differs")

            gate = load_json(paths["signal_transport_gate"], small_only=True)
            static_sha = sha256_small(paths["signal_static_audit"])
            if gate.get("status") != "PASS" or gate.get("authority", {}).get("sha256") != static_sha:
                errors.append("SF3 signal gate does not bind the current static audit")
            if gate.get("transport_scope") != SIGNAL_SCOPE:
                errors.append("SF3 signal gate scope differs")
            if set(gate.get("permitted_signal_jobs", [])) != {SIGNAL_JOB_ID}:
                errors.append("SF3 signal gate permitted-job closure differs")
            if gate.get("frozen_se3_policy") != "SMALL_TABLE_ONLY__NO_SE3_SIGNAL_RERUN":
                errors.append("SF3 signal gate does not lock frozen SE3 to small tables")
            validated["frozen_se3_SIMs_or_receipts_opened"] = 0
        except Exception as exc:
            errors.append(str(exc))

    receipt = receipt_path(config)
    if not receipt.is_file() or receipt.stat().st_size <= 0:
        missing_inputs.append(f"signal_receipt:{receipt}")
    elif plan is not None:
        try:
            payload = load_json(receipt, small_only=True)
            if payload.get("status") != "PASS":
                errors.append("SF3 signal receipt status is not PASS")
            for name, expected in (
                ("job_id", SIGNAL_JOB_ID), ("stage", "signal"),
                ("geometry", SIGNAL_GEOMETRY), ("mode", "signal"),
                ("events", SIGNAL_TRIALS), ("seed", int(plan["seed"])),
            ):
                if payload.get(name) != expected:
                    errors.append(f"SF3 signal receipt {name} differs")
            if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
                errors.append("SF3 signal receipt violates the no-SIM-digest contract")
            sim_path = resolve_declared_path(str(payload.get("sim_path", "")))
            source_path = resolve_declared_path(str(payload.get("source_path", "")))
            log_path = resolve_declared_path(str(payload.get("log_path", "")))
            for role, artifact, size_field in (
                ("signal_sim", sim_path, "sim_bytes"),
                ("signal_source", source_path, None),
                ("signal_log", log_path, "log_bytes"),
            ):
                if not artifact.is_file() or artifact.stat().st_size <= 0:
                    missing_inputs.append(f"{role}:{artifact}")
                elif size_field and artifact.stat().st_size != int(payload.get(size_field, -1)):
                    errors.append(f"{role} byte count differs from receipt")
            if source_path.is_file():
                if sha256_small(source_path) != payload.get("source_sha256"):
                    errors.append("SF3 signal source digest differs from receipt")
                eventlist = source_eventlist(source_path)
                if not eventlist.is_file() or eventlist.stat().st_size <= 0:
                    missing_inputs.append(f"signal_eventlist:{eventlist}")
                else:
                    static = load_json(paths["signal_static_audit"], small_only=True)
                    static_job = static["signal"]["job"]
                    expected_bank_sha = str(static["frozen_bank"]["output_sha256"])
                    if eventlist != resolve_declared_path(static_job["eventlist_path"]):
                        errors.append("SF3 receipt source EventList differs from static audit")
                    if static_job.get("eventlist_sha256") != expected_bank_sha:
                        errors.append("SF3 static EventList digest differs from frozen bank")
                    if sha256_small(eventlist) != expected_bank_sha:
                        errors.append("on-disk SF3 EventList digest differs from static audit")
                    validated["eventlist_path"] = str(eventlist)
            header = payload.get("sim_header", {})
            if resolve_declared_path(str(header.get("geometry", ""))) != resolve_declared_path(plan["setup_path"]):
                errors.append("SF3 signal receipt header geometry differs from plan")
            if header.get("seed") != int(plan["seed"]):
                errors.append("SF3 signal receipt header seed differs from plan")
            validated.update({
                "signal_receipt": str(receipt),
                "signal_sim_path": str(sim_path),
                "signal_sim_bytes": payload.get("sim_bytes"),
                "signal_events": SIGNAL_TRIALS,
                "signal_seed": plan["seed"],
            })
        except Exception as exc:
            errors.append(f"SF3 signal receipt invalid: {exc}")

    ready = not errors and not missing_inputs
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": (
            "READY__SF3_COMMON_RESPONSE_INPUTS_AND_FULL_ENVELOPE_SIGNAL"
            if ready else "NOT_READY__SF3_COMMON_RESPONSE_INPUTS_INCOMPLETE"
        ),
        "ready": ready,
        "config": str(config_path),
        "signal_scope": SIGNAL_SCOPE,
        "fresh_sf3_transport_required": True,
        "fresh_se3_transport_required": False,
        "missing_inputs": sorted(set(missing_inputs)),
        "errors": errors,
        "stage_status": stage_status,
        "validated": validated,
        "delayed_dispositions": {
            family: row["execution_disposition"] for family, row in delayed_registry.items()
        },
        "input_paths": {name: display_path(path) for name, path in paths.items()},
        "sim_access_policy": "STAT_ONLY__NO_SIM_OR_CATALOG_OPEN_OR_HASH",
    }


def response_runtime() -> tuple[Any, Any, dict[str, Any]]:
    global _RUNTIME
    if _RUNTIME is None:
        core = prompt.load_module("sf3_stage04_response_core", prompt.CORRECTED_CORE).core
        step05 = prompt.load_module("sf3_stage04_step05", prompt.STEP05)
        step05.ROOT = SOURCE_WORKTREE
        step05.STEP09_SUMMARY = prompt.STEP09_SUMMARY
        _RUNTIME = core, step05, step05.side_entry_disk()
    return _RUNTIME


def geometry_sources(setup: Path) -> list[Path]:
    pending = [setup.resolve()]
    result: list[Path] = []
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            continue
        result.append(path)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = INCLUDE_RE.match(line.strip())
            if match:
                pending.append((path.parent / match.group("path")).resolve())
    return result


def volume_material_map(setup: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in geometry_sources(setup):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = VOLUME_MATERIAL_RE.match(line.strip())
            if not match:
                continue
            volume = match.group("volume")
            material = match.group("material")
            previous = mapping.setdefault(volume, material)
            if previous != material:
                raise RuntimeError(f"volume has conflicting materials: {volume}")
    return mapping


def infer_material(volume: str, mapping: dict[str, str]) -> str:
    if not volume:
        return ""
    if volume in mapping:
        return mapping[volume]
    if volume in PASSIVE_W_VOLUMES:
        return "W"
    if volume.upper().startswith("TP_L"):
        return "TES_ACTIVE_PIXEL_MATERIAL"
    if "BGO" in volume.upper():
        return "BGO"
    if "PLASTIC" in volume.upper():
        return "PlasticScintillator"
    if "BPE" in volume.upper():
        return "BoratedPolyethylene5wtB"
    return "UNRESOLVED_VOLUME_MATERIAL"


def parse_ia(line: str) -> dict[str, Any] | None:
    match = IA_RE.match(line)
    if not match or match.group("process") == "INIT":
        return None
    fields = [field.strip() for field in match.group("body").split(";")]
    if len(fields) < 7:
        return None
    try:
        return {
            "process": match.group("process"),
            "interaction_id": int(fields[0]),
            "parent_id": int(fields[1]),
            "time_s": float(fields[3]),
            "x_cm": float(fields[4]),
            "y_cm": float(fields[5]),
            "z_cm": float(fields[6]),
        }
    except (TypeError, ValueError):
        return None


def match_first_interaction_volume(
    interaction: dict[str, Any] | None,
    primary_hits: list[dict[str, Any]],
    material_map: dict[str, str],
) -> tuple[str, str, str]:
    if interaction is None:
        return "", "", "NO_NON_INIT_IA"
    process_aliases = {
        "COMP": {"compt"},
        "PHOT": {"phot"},
        "RAYL": {"rayl"},
        "PAIR": {"conv", "pair"},
    }
    expected = process_aliases.get(str(interaction["process"]).upper(), set())
    time_s = float(interaction["time_s"])
    tolerance = max(5.0e-15, abs(time_s) * 2.0e-5)
    candidates = [
        hit for hit in primary_hits
        if abs(float(hit["time_s"]) - time_s) <= tolerance
        and (not expected or str(hit["sproc"]).lower() in expected)
    ]
    if not candidates:
        candidates = [
            hit for hit in primary_hits
            if abs(float(hit["time_s"]) - time_s) <= tolerance
        ]
    if not candidates:
        return "", "", "UNRESOLVED_ZERO_EDEP_OR_UNRECORDED_IA"
    selected = min(candidates, key=lambda hit: abs(float(hit["time_s"]) - time_s))
    volume = str(selected["volume"])
    return volume, infer_material(volume, material_map), "MATCHED_PRIMARY_CC_HIT_TIME_PROCESS"


def empty_ray_row(ray_id: int) -> dict[str, Any]:
    return {
        "geometry": SIGNAL_GEOMETRY,
        "signal_scope": SIGNAL_SCOPE,
        "ray_id": ray_id,
        "sim_local_event_id": ray_id + 1,
        "sim_event_seen": False,
        "first_interaction_process": "",
        "first_interaction_time_s": "",
        "first_interaction_x_cm": "",
        "first_interaction_y_cm": "",
        "first_interaction_z_cm": "",
        "first_interaction_volume": "",
        "first_interaction_material": "",
        "first_interaction_resolution": "",
        "bpe_deposit_keV": 0.0,
        "plastic_deposit_keV": 0.0,
        "bgo_deposit_keV": 0.0,
        "passive_w_deposit_keV": 0.0,
        "first_interaction_in_passive_w": False,
        "pair_ia_count": 0,
        "w_pair_ia_count": 0,
        "pair_ia_unresolved_count": 0,
        "annihilation_ia_count": 0,
        "w_annihilation_ia_count": 0,
        "annihilation_ia_unresolved_count": 0,
        "raw_tes_total_keV": 0.0,
        "measured_tes_total_keV": 0.0,
        "measured_multiplicity": 0,
        "measured_w2_pass": False,
        "bgo_veto50_pass": False,
        "plastic_veto50_pass": False,
        "step05_pass": False,
        "final_w2_step05_pass": False,
        "failure_category": "NO_SIM_EVENT_RECORD",
    }


def scan_signal_once(
    job: dict[str, Any],
    target: Path,
    diagnostics_target: Path,
    config: dict[str, Any],
    bank_sha256: str,
) -> dict[str, Any]:
    """Perform the sole semantic pass over the fresh SF3 signal SIM."""
    parser = prompt.old_parser()
    catalog = parser.empty_catalog()
    policy = prompt.explicit_veto_policy(config)
    shield = set(policy["shield_volumes"])
    plastic = set(policy["plastic_volumes"])
    passive_w = set(prompt.passive_w_volumes(config))
    if passive_w != PASSIVE_W_VOLUMES or passive_w & (shield | plastic):
        raise RuntimeError("SF3 signal passive-W/active-veto closure differs")
    setup = resolve_declared_path(job["setup_path"])
    materials = volume_material_map(setup)
    if {volume for volume in passive_w if materials.get(volume) == "W"} != passive_w:
        raise RuntimeError("SF3 signal setup does not map all three passive volumes to W")
    bpe = {
        volume for volume, material in materials.items()
        if material == "BoratedPolyethylene5wtB"
    }
    if len(bpe) != 3:
        raise RuntimeError(f"SF3 BPE volume closure differs: {sorted(bpe)}")

    diagnostics = [empty_ray_row(index) for index in range(SIGNAL_TRIALS)]
    extras: dict[str, list[Any]] = {
        "input_id": [],
        "batch_id": [],
        "job_name": [],
        "seed": [],
        "plastic_total_keV": [],
        "bpe_total_keV": [],
        "w_total_keV": [],
        "has_pair_ia": [],
        "has_annihilation_ia": [],
        "first_interaction_volume": [],
        "first_interaction_resolution": [],
        "first_interaction_in_passive_w": [],
        "w_pair_ia_count": [],
        "w_annihilation_ia_count": [],
        "pair_ia_unresolved_count": [],
        "annihilation_ia_unresolved_count": [],
        "eventlist_id": [],
    }
    current_id: int | None = None
    pixels: dict[str, dict[str, float | int]] = {}
    bpe_total = plastic_total = shield_total = w_total = 0.0
    interactions: list[dict[str, Any]] = []
    primary_hits: list[dict[str, Any]] = []
    all_meta_hits: list[dict[str, Any]] = []
    generated = terminal_en = active_only = 0
    header_geometry = ""
    header_seed: int | None = None
    seen_ids: set[int] = set()

    def flush() -> None:
        nonlocal current_id, pixels, bpe_total, plastic_total, shield_total, w_total
        nonlocal interactions, primary_hits, all_meta_hits, active_only
        if current_id is None:
            return
        if not (1 <= current_id <= SIGNAL_TRIALS):
            raise RuntimeError(f"signal SIM event ID outside 1..{SIGNAL_TRIALS}: {current_id}")
        ray_id = current_id - 1
        row = diagnostics[ray_id]
        row["sim_event_seen"] = True
        first = min(
            (item for item in interactions if int(item["parent_id"]) == 1),
            key=lambda item: (float(item["time_s"]), int(item["interaction_id"])),
            default=None,
        )
        volume, material, resolution = match_first_interaction_volume(first, primary_hits, materials)
        w_diag = prompt.event_w_diagnostics(
            interactions, primary_hits, all_meta_hits, passive_w
        )
        if first is not None:
            row.update({
                "first_interaction_process": first["process"],
                "first_interaction_time_s": first["time_s"],
                "first_interaction_x_cm": first["x_cm"],
                "first_interaction_y_cm": first["y_cm"],
                "first_interaction_z_cm": first["z_cm"],
            })
        row.update({
            "first_interaction_volume": volume,
            "first_interaction_material": material,
            "first_interaction_resolution": resolution,
            "bpe_deposit_keV": bpe_total,
            "plastic_deposit_keV": plastic_total,
            "bgo_deposit_keV": shield_total,
            "passive_w_deposit_keV": w_total,
            "first_interaction_in_passive_w": bool(
                w_diag["first_interaction_in_passive_w"]
            ),
            "pair_ia_count": int(w_diag["pair_ia_count"]),
            "w_pair_ia_count": int(w_diag["w_pair_ia_count"]),
            "pair_ia_unresolved_count": int(w_diag["pair_ia_unresolved_count"]),
            "annihilation_ia_count": int(w_diag["annihilation_ia_count"]),
            "w_annihilation_ia_count": int(w_diag["w_annihilation_ia_count"]),
            "annihilation_ia_unresolved_count": int(
                w_diag["annihilation_ia_unresolved_count"]
            ),
            "raw_tes_total_keV": math.fsum(float(item["e"]) for item in pixels.values()),
            "bgo_veto50_pass": shield_total < 50.0,
            "plastic_veto50_pass": plastic_total < float(policy["plastic_threshold_keV"]),
        })
        if pixels:
            before = len(catalog["stream"])
            parser.append_event(
                catalog,
                "signal",
                SIGNAL_FAMILY,
                job["sim_path"],
                current_id,
                0.0,
                shield_total,
                pixels,
            )
            if len(catalog["stream"]) != before + 1:
                raise RuntimeError(f"positive-TES signal event was not retained: {current_id}")
            extras["input_id"].append("sf3_full_envelope_eventlist")
            extras["batch_id"].append(f"eventlist_sha256:{bank_sha256}")
            extras["job_name"].append(SIGNAL_JOB_ID)
            extras["seed"].append(int(job["seed"]))
            extras["plastic_total_keV"].append(plastic_total)
            extras["bpe_total_keV"].append(bpe_total)
            extras["w_total_keV"].append(w_total)
            extras["has_pair_ia"].append(any(
                str(item["process"]).upper() == "PAIR" for item in interactions
            ))
            extras["has_annihilation_ia"].append(any(
                str(item["process"]).upper() == "ANNI" for item in interactions
            ))
            extras["first_interaction_volume"].append(volume)
            extras["first_interaction_resolution"].append(resolution)
            extras["first_interaction_in_passive_w"].append(
                bool(w_diag["first_interaction_in_passive_w"])
            )
            extras["w_pair_ia_count"].append(int(w_diag["w_pair_ia_count"]))
            extras["w_annihilation_ia_count"].append(
                int(w_diag["w_annihilation_ia_count"])
            )
            extras["pair_ia_unresolved_count"].append(
                int(w_diag["pair_ia_unresolved_count"])
            )
            extras["annihilation_ia_unresolved_count"].append(
                int(w_diag["annihilation_ia_unresolved_count"])
            )
            extras["eventlist_id"].append(ray_id)
            row["failure_category"] = "PENDING_COMMON_RESPONSE"
        elif shield_total > 0.0 or plastic_total > 0.0:
            active_only += 1
            row["failure_category"] = "NO_TES_DEPOSIT__ACTIVE_VETO_DEPOSIT_ONLY"
        else:
            row["failure_category"] = "NO_TES_DEPOSIT"
        current_id = None
        pixels = {}
        bpe_total = plastic_total = shield_total = w_total = 0.0
        interactions = []
        primary_hits = []
        all_meta_hits = []

    with parser.open_text(job["sim_path"]) as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            if line == "EN":
                terminal_en += 1
                continue
            if line == "SE":
                flush()
                continue
            id_match = parser.ID_RE.match(line)
            if id_match:
                current_id = int(id_match.group(1))
                if current_id in seen_ids:
                    raise RuntimeError(f"duplicate signal SIM event ID: {current_id}")
                seen_ids.add(current_id)
                generated += 1
                continue
            interaction = parse_ia(line)
            if interaction is not None:
                interactions.append(interaction)
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parser.parse_cc_hit(line)
            if hit is None:
                continue
            volume, edep, x, y, z = hit
            meta = CC_META_RE.search(line)
            if meta:
                meta_hit = {
                    "volume": volume,
                    "time_s": float(meta.group("time")),
                    "sproc": meta.group("sproc"),
                }
                all_meta_hits.append(meta_hit)
                if int(meta.group("tid")) == 1 and int(meta.group("pid")) == 0:
                    primary_hits.append(meta_hit)
            pixel_match = parser.TP_RE.match(volume)
            if pixel_match:
                record = pixels.setdefault(volume, {
                    "e": 0.0,
                    "wx": 0.0,
                    "wy": 0.0,
                    "wz": 0.0,
                    "layer": int(pixel_match.group("layer")),
                })
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in shield:
                shield_total += edep
            elif volume in plastic:
                plastic_total += edep
            elif volume in bpe:
                bpe_total += edep
            elif volume in passive_w:
                w_total += edep
    flush()

    if generated != SIGNAL_TRIALS or seen_ids != set(range(1, SIGNAL_TRIALS + 1)):
        raise RuntimeError(
            f"signal SIM ID closure differs: IDs={len(seen_ids)}, generated={generated}, "
            f"expected={SIGNAL_TRIALS}"
        )
    if resolve_declared_path(header_geometry) != setup:
        raise RuntimeError(f"signal SIM semantic header geometry differs: {header_geometry}")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"signal SIM semantic header seed differs: {header_seed}")
    if terminal_en != 1:
        raise RuntimeError(f"signal SIM terminal EN count {terminal_en} != 1")

    catalog.update(extras)
    weight = float(config["signal"]["input_optics_aeff_cm2"]) / SIGNAL_TRIALS
    catalog["rate_hz"] = [weight] * len(catalog["stream"])
    catalog["n_generated_events_seen"] = generated
    catalog["generated_events"] = generated
    catalog["active_only_events"] = active_only
    catalog["active_only_rate_hz"] = active_only * weight
    catalog["cell_metadata"] = {
        "profile_id": PROFILE_ID,
        "geometry": SIGNAL_GEOMETRY,
        "family": SIGNAL_FAMILY,
        "mode": "signal",
        "jobs": 1,
        "generated_events": SIGNAL_TRIALS,
        "TT_s": SIGNAL_TRIALS / float(config["signal"]["input_optics_aeff_cm2"]),
        "event_weight_cps": weight,
        "event_weight_unit": "cm2",
        "effective_area_input_cm2": float(config["signal"]["input_optics_aeff_cm2"]),
        "eventlist_sha256": bank_sha256,
        "transport_header_seed": header_seed,
        "veto_policy": policy,
        "response_geometry_key": "sf3",
        "authority_status": SIGNAL_AUTHORITY,
        "signal_scope": SIGNAL_SCOPE,
        "normalization": f"Aeff_input * selected / {SIGNAL_TRIALS}",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    write_csv(diagnostics_target, diagnostics)
    return {
        "catalog": catalog,
        "diagnostics": diagnostics,
        "generated_events": generated,
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": active_only,
        "pixel_hits": len(catalog["pix_e"]),
        "semantic_sim_scans": 1,
        "sim_hashes_recomputed": 0,
        "header_geometry": header_geometry,
        "header_seed": header_seed,
        "terminal_en": terminal_en,
        "bpe_volumes": sorted(bpe),
        "passive_w_volumes": sorted(passive_w),
        "passive_w_never_active_veto": True,
        "passive_w_deposit_events": sum(
            float(row["passive_w_deposit_keV"]) > 0.0 for row in diagnostics
        ),
        "passive_w_deposit_keV_sum": math.fsum(
            float(row["passive_w_deposit_keV"]) for row in diagnostics
        ),
        "passive_w_first_interaction_events": sum(
            bool(row["first_interaction_in_passive_w"]) for row in diagnostics
        ),
        "passive_w_pair_events": sum(
            int(row["w_pair_ia_count"]) > 0 for row in diagnostics
        ),
        "passive_w_annihilation_events": sum(
            int(row["w_annihilation_ia_count"]) > 0 for row in diagnostics
        ),
        "material_map_entries": len(materials),
    }


def structural_zero_delayed_catalog(
    family: str, disposition: dict[str, Any]
) -> dict[str, Any]:
    """Build an in-memory zero-rate catalog without inventing a transport file."""
    if disposition["execution_disposition"] != DELAYED_ZERO_DISPOSITION:
        raise RuntimeError(f"structural zero requested for non-zero delayed family: {family}")
    return {
        "stream": [],
        "pix_e": [],
        "active_only_events": 0,
        "cell_metadata": {
            "geometry": SIGNAL_GEOMETRY,
            "family": family,
            "mode": "delayed",
            "generated_events": 0,
            # This is provenance for the zero-RP upper, not a delayed exposure.
            # The event weight is exactly zero, so no Garwood response rate is
            # inferred from this bookkeeping value.
            "TT_s": float(disposition["buildup_sum_TT_s"]),
            "event_weight_cps": 0.0,
            "authority_status": BACKGROUND_AUTHORITY,
            "execution_disposition": DELAYED_ZERO_DISPOSITION,
            "catalog_origin": disposition["catalog_origin"],
            "transported_ground_activity_Bq": 0.0,
            "transported_ground_rate_upper95_s-1": disposition[
                "transported_ground_rate_upper95_s-1"
            ],
            "transported_ground_A15_upper95_Bq_conservative": disposition[
                "transported_ground_A15_upper95_Bq_conservative"
            ],
            "zero_A15_upper_provenance": disposition["zero_A15_upper_provenance"],
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq": disposition["known_holdout_activity_Bq"],
            "unknown_activity_state_count": disposition["unknown_activity_state_count"],
            "sim_opened": False,
            "catalog_file_opened": False,
        },
    }


def evaluate_catalog_payload(
    catalog: dict[str, Any], task: dict[str, Any]
) -> dict[str, Any]:
    core, step05, disk = response_runtime()
    cutflow, _spectrum, occupancy = prompt.evaluate_cell(catalog, core, step05, disk)
    selected: list[dict[str, Any]] = []

    def event_value(name: str, event_index: int, default: Any) -> Any:
        values = catalog.get(name)
        if not isinstance(values, (list, tuple)) or event_index >= len(values):
            return default
        return values[event_index]

    for event_index in range(len(catalog["stream"])):
        event = prompt.evaluate_event(catalog, event_index, core, step05, disk)
        final = (
            prompt.in_window(event["measured_total_keV"], WINDOWS["w2_510p58_511p42"])
            and event["active_pass"][50.0]
            and event["topology_pass"]
        )
        if not final:
            continue
        row = {
            "geometry": SIGNAL_GEOMETRY,
            "stream": task["stream"],
            "family": task["family"],
            "local_event_id": int(catalog["local_id"][event_index]),
            "batch_id": catalog["batch_id"][event_index],
            "job_name": catalog["job_name"][event_index],
            "transport_seed": int(catalog["seed"][event_index]),
            "measured_total_keV": event["measured_total_keV"],
            "measured_multiplicity": len(event["measured_hits"]),
            "shield_keV": event["shield_keV"],
            "plastic_keV": event["plastic_keV"],
            "passive_w_keV": float(event_value("w_total_keV", event_index, 0.0)),
            "first_interaction_volume": str(event_value(
                "first_interaction_volume", event_index, ""
            )),
            "first_interaction_resolution": str(event_value(
                "first_interaction_resolution", event_index, "NOT_RECORDED_BY_STAGE"
            )),
            "first_interaction_in_passive_w": bool(event_value(
                "first_interaction_in_passive_w", event_index, False
            )),
            "has_pair_ia": bool(event_value("has_pair_ia", event_index, False)),
            "has_annihilation_ia": bool(event_value(
                "has_annihilation_ia", event_index, False
            )),
            "w_pair_ia_count": int(event_value("w_pair_ia_count", event_index, 0)),
            "w_annihilation_ia_count": int(event_value(
                "w_annihilation_ia_count", event_index, 0
            )),
            "pair_ia_unresolved_count": int(event_value(
                "pair_ia_unresolved_count", event_index, 0
            )),
            "annihilation_ia_unresolved_count": int(event_value(
                "annihilation_ia_unresolved_count", event_index, 0
            )),
            "event_weight_cps": float(catalog["cell_metadata"]["event_weight_cps"]),
            "source_parent_ZA": "",
            "source_volume": "",
            "source_excitation_keV": "",
            "sim_initial_ZA": "",
            "parent_match_distance_cm": "",
            "source_file": catalog["source_file"][event_index],
            "signal_scope": "NOT_APPLICABLE_BACKGROUND",
        }
        if task["stream"] == "delayed":
            row.update({
                "source_parent_ZA": int(catalog["source_parent_ZA"][event_index]),
                "source_volume": catalog["source_volume"][event_index],
                "source_excitation_keV": float(catalog["source_excitation_keV"][event_index]),
                "sim_initial_ZA": int(catalog["sim_initial_ZA"][event_index]),
                "parent_match_distance_cm": float(catalog["parent_match_distance_cm"][event_index]),
            })
        selected.append(row)

    count = len(catalog["stream"])
    source_volumes = catalog.get("source_volume", [])
    passive_w = set(PASSIVE_W_VOLUMES)
    event_weight = float(catalog["cell_metadata"].get("event_weight_cps", 0.0))
    w_deposit_events = sum(
        float(event_value("w_total_keV", index, 0.0)) > 0.0 for index in range(count)
    )
    w_first_events = sum(
        bool(event_value("first_interaction_in_passive_w", index, False))
        for index in range(count)
    )
    w_pair_events = sum(
        int(event_value("w_pair_ia_count", index, 0)) > 0 for index in range(count)
    )
    w_annihilation_events = sum(
        int(event_value("w_annihilation_ia_count", index, 0)) > 0
        for index in range(count)
    )
    w_source_events = sum(
        index < len(source_volumes) and str(source_volumes[index]) in passive_w
        for index in range(count)
    )
    return {
        "geometry": SIGNAL_GEOMETRY,
        "stream": task["stream"],
        "family": task["family"],
        "meta": catalog["cell_metadata"],
        "execution_disposition": task.get("execution_disposition", ""),
        "catalog_origin": task.get("catalog_origin", "STAGE_CATALOG"),
        "cutflow": cutflow,
        "occupancy": occupancy,
        "selected": selected,
        "w_diagnostics": {
            "tes_positive_events": count,
            "passive_w_deposit_events": w_deposit_events,
            "passive_w_deposit_keV_sum": math.fsum(
                float(event_value("w_total_keV", index, 0.0)) for index in range(count)
            ),
            "passive_w_first_interaction_events": w_first_events,
            "passive_w_pair_events": w_pair_events,
            "passive_w_annihilation_events": w_annihilation_events,
            "passive_w_source_events": w_source_events,
            "passive_w_selected_w2_events": sum(
                float(row["passive_w_keV"]) > 0.0 for row in selected
            ),
            "passive_w_source_selected_w2_events": sum(
                str(row["source_volume"]) in passive_w for row in selected
            ),
            "event_weight_cps": event_weight,
        },
    }


def evaluate_catalog(task: dict[str, Any]) -> dict[str, Any]:
    with Path(task["path"]).open("rb") as handle:
        catalog = pickle.load(handle)
    return evaluate_catalog_payload(catalog, task)


def evaluate_structural_zero_delayed(
    family: str, disposition: dict[str, Any]
) -> dict[str, Any]:
    catalog = structural_zero_delayed_catalog(family, disposition)
    return evaluate_catalog_payload(catalog, {
        "stream": "delayed",
        "family": family,
        "execution_disposition": DELAYED_ZERO_DISPOSITION,
        "catalog_origin": disposition["catalog_origin"],
    })


def evaluate_signal(
    catalog: dict[str, Any], diagnostics: list[dict[str, Any]]
) -> dict[str, Any]:
    core, step05, disk = response_runtime()
    cutflow, _spectrum, occupancy = prompt.evaluate_cell(catalog, core, step05, disk)
    by_ray = {int(row["ray_id"]): row for row in diagnostics}
    for event_index in range(len(catalog["stream"])):
        event = prompt.evaluate_event(catalog, event_index, core, step05, disk)
        ray_id = int(catalog["eventlist_id"][event_index])
        row = by_ray[ray_id]
        measured = float(event["measured_total_keV"])
        w2_pass = prompt.in_window(measured, WINDOWS["w2_510p58_511p42"])
        bgo_pass = float(event["shield_keV"]) < 50.0
        plastic_pass = float(event["plastic_keV"]) < 50.0
        step05_pass = bool(event["topology_pass"]) if w2_pass and bgo_pass and plastic_pass else False
        final = w2_pass and bgo_pass and plastic_pass and step05_pass
        if measured < WINDOWS["w2_510p58_511p42"][0]:
            failure = "MEASURED_ENERGY_BELOW_W2"
        elif measured >= WINDOWS["w2_510p58_511p42"][1]:
            failure = "MEASURED_ENERGY_ABOVE_W2"
        elif not bgo_pass:
            failure = "BGO_VETO50_FAIL"
        elif not plastic_pass:
            failure = "PLASTIC_VETO50_FAIL"
        elif not step05_pass:
            failure = "STEP05_FAIL"
        else:
            failure = "PASS_W2_VETO_STEP05"
        row.update({
            "measured_tes_total_keV": measured,
            "measured_multiplicity": len(event["measured_hits"]),
            "measured_w2_pass": w2_pass,
            "bgo_veto50_pass": bgo_pass,
            "plastic_veto50_pass": plastic_pass,
            "step05_pass": step05_pass,
            "final_w2_step05_pass": final,
            "failure_category": failure,
        })
    if len(by_ray) != SIGNAL_TRIALS:
        raise RuntimeError("signal diagnostic ray-ID closure differs after response")
    return {
        "geometry": SIGNAL_GEOMETRY,
        "stream": "signal",
        "family": SIGNAL_FAMILY,
        "meta": catalog["cell_metadata"],
        "cutflow": cutflow,
        "occupancy": occupancy,
        "selected": [],
        "diagnostics": diagnostics,
        "w_diagnostics": {
            "tes_positive_events": len(catalog["stream"]),
            "passive_w_deposit_events": sum(
                float(row["passive_w_deposit_keV"]) > 0.0 for row in diagnostics
            ),
            "passive_w_deposit_keV_sum": math.fsum(
                float(row["passive_w_deposit_keV"]) for row in diagnostics
            ),
            "passive_w_first_interaction_events": sum(
                bool(row["first_interaction_in_passive_w"]) for row in diagnostics
            ),
            "passive_w_pair_events": sum(
                int(row["w_pair_ia_count"]) > 0 for row in diagnostics
            ),
            "passive_w_annihilation_events": sum(
                int(row["w_annihilation_ia_count"]) > 0 for row in diagnostics
            ),
            "passive_w_source_events": 0,
            "passive_w_selected_w2_events": sum(
                float(row["passive_w_deposit_keV"]) > 0.0
                and bool(row["final_w2_step05_pass"])
                for row in diagnostics
            ),
            "passive_w_source_selected_w2_events": 0,
            "event_weight_cps": float(catalog["cell_metadata"]["event_weight_cps"]),
        },
    }


def clopper_pearson(count: int, trials: int) -> tuple[float, float]:
    from scipy.stats import beta

    lower = 0.0 if count == 0 else float(beta.ppf(0.025, count, trials - count + 1))
    upper = 1.0 if count == trials else float(beta.ppf(0.975, count + 1, trials - count))
    return lower, upper


def common_cutflow(results: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        stream = result["stream"]
        meta = result["meta"]
        disposition = str(result.get("execution_disposition", ""))
        for source in result["cutflow"]:
            key = (source["response_state"], source["stage"])
            if key not in CANONICAL_STAGES:
                continue
            count = int(source["selected_events"])
            if stream == "signal":
                probability = count / SIGNAL_TRIALS
                lower, upper = clopper_pearson(count, SIGNAL_TRIALS)
                weight = aeff_cm2 / SIGNAL_TRIALS
                weighted = count * weight
                sigma = aeff_cm2 * math.sqrt(probability * (1.0 - probability) / SIGNAL_TRIALS)
                lower_weighted = aeff_cm2 * lower
                upper_weighted = aeff_cm2 * upper
                unit = "cm2"
                exposure = SIGNAL_TRIALS / aeff_cm2
                exposure_unit = "cm-2"
                scope = SIGNAL_SCOPE
            else:
                weight = float(source["event_weight_cps"])
                weighted = float(source["rate_cps"])
                sigma = float(source["rate_stat_sigma_cps"])
                lower_weighted = float(source["rate_lower95_cps"])
                upper_weighted = float(source["rate_upper95_cps"])
                unit = "cps"
                exposure = float(source["TT_s"])
                exposure_unit = "s"
                scope = "NOT_APPLICABLE_BACKGROUND"
            rows.append({
                "geometry": SIGNAL_GEOMETRY,
                "stream": stream,
                "family": result["family"],
                "response_state": source["response_state"],
                "stage": source["stage"],
                "window_id": source["window_id"],
                "energy_lo_keV": source["energy_lo_keV"],
                "energy_hi_keV": source["energy_hi_keV"],
                "generated_events": source["generated_events"],
                "normalization_exposure": exposure,
                "normalization_exposure_unit": exposure_unit,
                "selected_events": count,
                "event_weight": weight,
                "weighted_value": weighted,
                "weighted_stat_sigma": sigma,
                "weighted_lower95": lower_weighted,
                "weighted_upper95": upper_weighted,
                "weighted_unit": unit,
                "authority_status": meta.get(
                    "authority_status",
                    SIGNAL_AUTHORITY if stream == "signal" else BACKGROUND_AUTHORITY,
                ),
                "signal_scope": scope,
                "execution_disposition": disposition,
                "catalog_origin": result.get("catalog_origin", ""),
                "transported_ground_rate_upper95_s-1": meta.get(
                    "transported_ground_rate_upper95_s-1"
                ),
                "transported_ground_A15_upper95_Bq_conservative": meta.get(
                    "transported_ground_A15_upper95_Bq_conservative"
                ),
                "zero_A15_upper_provenance": meta.get("zero_A15_upper_provenance"),
                "upper_excludes_known_and_unresolved_holdout": meta.get(
                    "upper_excludes_known_and_unresolved_holdout"
                ),
            })
    return rows


def background_summary(cutflow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: defaultdict[tuple[str, str, str, str], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0]
    )
    for row in cutflow:
        if row["stream"] not in STREAMS:
            continue
        key = (row["stream"], row["response_state"], row["stage"], row["window_id"])
        item = totals[key]
        item[0] += int(row["selected_events"])
        item[1] += float(row["weighted_value"])
        item[2] += float(row["weighted_stat_sigma"]) ** 2
    rows: list[dict[str, Any]] = []
    for response, stage in sorted(CANONICAL_STAGES):
        for window in FINAL_WINDOWS:
            p = totals[("prompt", response, stage, window)]
            d = totals[("delayed", response, stage, window)]
            rows.append({
                "geometry": SIGNAL_GEOMETRY,
                "response_state": response,
                "stage": stage,
                "window_id": window,
                "prompt_events": int(p[0]),
                "prompt_rate_cps": p[1],
                "prompt_stat_sigma_cps": math.sqrt(p[2]),
                "delayed_events": int(d[0]),
                "delayed_rate_cps": d[1],
                "delayed_stat_sigma_cps": math.sqrt(d[2]),
                "total_background_rate_cps": p[1] + d[1],
                "total_background_stat_sigma_cps": math.sqrt(p[2] + d[2]),
                "authority_status": BACKGROUND_AUTHORITY,
                "comparison_role": "FRESH_SF3_CANDIDATE",
                "signal_scope": "NOT_APPLICABLE_BACKGROUND",
            })
    return rows


def occupancy_rows(results: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        occ = result["occupancy"]
        meta = result["meta"]
        stream = result["stream"]
        events = int(occ["detector_occupancy_events"])
        tes_events = int(occ["tes_positive_events"])
        active_events = int(occ["active_only_events"])
        if stream == "signal":
            weight = aeff_cm2 / SIGNAL_TRIALS

            def sigma(count: int) -> float:
                probability = count / SIGNAL_TRIALS
                return aeff_cm2 * math.sqrt(probability * (1.0 - probability) / SIGNAL_TRIALS)

            unit = "cm2"
            model = "binomial"
            scope = SIGNAL_SCOPE
        else:
            weight = float(meta["event_weight_cps"])

            def sigma(count: int) -> float:
                return math.sqrt(count) * weight

            unit = "cps"
            model = "poisson_mc"
            scope = "NOT_APPLICABLE_BACKGROUND"
        rows.append({
            "geometry": SIGNAL_GEOMETRY,
            "stream": stream,
            "family": result["family"],
            "generated_events": occ["generated_events"],
            "detector_occupancy_events": events,
            "tes_positive_events": tes_events,
            "active_only_events": active_events,
            "pixel_hits": occ["pixel_hits"],
            "weighted_occupancy": events * weight,
            "weighted_tes": tes_events * weight,
            "weighted_active_only": active_events * weight,
            "weighted_stat_sigma": sigma(events),
            "weighted_occupancy_stat_sigma": sigma(events),
            "weighted_tes_stat_sigma": sigma(tes_events),
            "weighted_active_only_stat_sigma": sigma(active_events),
            "weighted_unit": unit,
            "statistical_model": model,
            "signal_scope": scope,
            "authority_status": SIGNAL_AUTHORITY if stream == "signal" else BACKGROUND_AUTHORITY,
            "execution_disposition": result.get("execution_disposition", ""),
            "catalog_origin": result.get("catalog_origin", ""),
            "transported_ground_rate_upper95_s-1": meta.get(
                "transported_ground_rate_upper95_s-1"
            ),
            "transported_ground_A15_upper95_Bq_conservative": meta.get(
                "transported_ground_A15_upper95_Bq_conservative"
            ),
            "zero_A15_upper_provenance": meta.get("zero_A15_upper_provenance"),
        })
    return rows


def signal_acceptance(cutflow: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in cutflow:
        if not (
            row["stream"] == "signal"
            and row["response_state"] == FINAL_RESPONSE
            and row["stage"] == FINAL_STAGE
            and row["window_id"] in FINAL_WINDOWS
        ):
            continue
        count = int(row["selected_events"])
        lower, upper = clopper_pearson(count, SIGNAL_TRIALS)
        rows.append({
            "geometry": SIGNAL_GEOMETRY,
            "response_state": FINAL_RESPONSE,
            "stage": FINAL_STAGE,
            "window_id": row["window_id"],
            "trials": SIGNAL_TRIALS,
            "selected_events": count,
            "acceptance": count / SIGNAL_TRIALS,
            "acceptance_lower95": lower,
            "acceptance_upper95": upper,
            "input_optics_aeff_cm2": aeff_cm2,
            "selected_effective_area_cm2": aeff_cm2 * count / SIGNAL_TRIALS,
            "selected_effective_area_lower95_cm2": aeff_cm2 * lower,
            "selected_effective_area_upper95_cm2": aeff_cm2 * upper,
            "signal_scope": SIGNAL_SCOPE,
            "authority_status": SIGNAL_AUTHORITY,
        })
    if {(row["response_state"], row["stage"], row["window_id"]) for row in rows} != {
        (FINAL_RESPONSE, FINAL_STAGE, window) for window in FINAL_WINDOWS
    }:
        raise RuntimeError("final SF3 full-envelope signal acceptance key closure differs")
    return rows


def aggregate_diagnostics(
    diagnostics: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    first_counts: Counter[tuple[str, str, str, str]] = Counter()
    failure_counts: Counter[str] = Counter()
    for row in diagnostics:
        first_counts[(
            str(row["first_interaction_process"]),
            str(row["first_interaction_volume"]),
            str(row["first_interaction_material"]),
            str(row["first_interaction_resolution"]),
        )] += 1
        failure_counts[str(row["failure_category"])] += 1
    first_rows = [{
        "geometry": SIGNAL_GEOMETRY,
        "signal_scope": SIGNAL_SCOPE,
        "first_interaction_process": key[0],
        "first_interaction_volume": key[1],
        "first_interaction_material": key[2],
        "first_interaction_resolution": key[3],
        "rays": count,
        "fraction_of_37194": count / SIGNAL_TRIALS,
    } for key, count in sorted(first_counts.items())]
    failure_rows = [{
        "geometry": SIGNAL_GEOMETRY,
        "signal_scope": SIGNAL_SCOPE,
        "failure_category": category,
        "rays": count,
        "fraction_of_37194": count / SIGNAL_TRIALS,
    } for category, count in sorted(failure_counts.items())]
    if sum(row["rays"] for row in first_rows) != SIGNAL_TRIALS:
        raise RuntimeError("first-interaction diagnostic closure differs")
    if sum(row["rays"] for row in failure_rows) != SIGNAL_TRIALS:
        raise RuntimeError("signal failure-category closure differs")
    return first_rows, failure_rows


def passive_w_summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize passive-W evidence without giving W an active-veto role."""
    rows: list[dict[str, Any]] = []
    for result in results:
        diagnostic = result["w_diagnostics"]
        weight = float(diagnostic["event_weight_cps"])
        unit = "cm2" if result["stream"] == "signal" else "cps"
        rows.append({
            "geometry": SIGNAL_GEOMETRY,
            "stream": result["stream"],
            "family": result["family"],
            "passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
            "tes_positive_events": int(diagnostic["tes_positive_events"]),
            "passive_w_deposit_events": int(diagnostic["passive_w_deposit_events"]),
            "passive_w_deposit_keV_sum": float(diagnostic["passive_w_deposit_keV_sum"]),
            "passive_w_first_interaction_events": int(
                diagnostic["passive_w_first_interaction_events"]
            ),
            "passive_w_pair_events": int(diagnostic["passive_w_pair_events"]),
            "passive_w_annihilation_events": int(
                diagnostic["passive_w_annihilation_events"]
            ),
            "passive_w_source_events": int(diagnostic["passive_w_source_events"]),
            "passive_w_selected_w2_events": int(
                diagnostic["passive_w_selected_w2_events"]
            ),
            "passive_w_source_selected_w2_events": int(
                diagnostic["passive_w_source_selected_w2_events"]
            ),
            "normalization_weight": weight,
            "normalization_unit": unit,
            "passive_w_deposit_weighted": int(
                diagnostic["passive_w_deposit_events"]
            ) * weight,
            "passive_w_first_interaction_weighted": int(
                diagnostic["passive_w_first_interaction_events"]
            ) * weight,
            "passive_w_pair_weighted": int(
                diagnostic["passive_w_pair_events"]
            ) * weight,
            "passive_w_annihilation_weighted": int(
                diagnostic["passive_w_annihilation_events"]
            ) * weight,
            "passive_w_source_weighted": int(
                diagnostic["passive_w_source_events"]
            ) * weight,
        })
    return rows


def passive_w_source_lineage_rows(
    selected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: defaultdict[tuple[str, str, int], list[float]] = defaultdict(
        lambda: [0.0, 0.0]
    )
    for row in selected:
        if row["stream"] != "delayed" or str(row["source_volume"]) not in PASSIVE_W_VOLUMES:
            continue
        key = (row["family"], str(row["source_volume"]), int(row["source_parent_ZA"]))
        grouped[key][0] += 1
        grouped[key][1] += float(row["event_weight_cps"])
    return [{
        "geometry": SIGNAL_GEOMETRY,
        "stream": "delayed",
        "family": key[0],
        "source_volume": key[1],
        "source_parent_ZA": key[2],
        "selected_measured_w2_events": int(value[0]),
        "selected_measured_w2_rate_cps": value[1],
        "passive_w_role": "SOURCE_LINEAGE_DIAGNOSTIC__NEVER_ACTIVE_VETO",
    } for key, value in sorted(grouped.items())]


def response_contract(config: dict[str, Any]) -> dict[str, Any]:
    core, _step05, _disk = response_runtime()
    if not math.isclose(float(core.FWHM_KEV), 0.42, rel_tol=0.0, abs_tol=0.0):
        raise RuntimeError("retained response implementation FWHM differs from 0.42 keV")
    if not math.isclose(float(core.PIXEL_THRESHOLD_KEV), 0.3, rel_tol=0.0, abs_tol=0.0):
        raise RuntimeError("retained response measured-pixel threshold differs from 0.3 keV")
    return {
        "implementation": str(prompt.CORRECTED_CORE),
        "rng_namespace": str(core.RESPONSE_NAMESPACE),
        "FWHM_keV": float(core.FWHM_KEV),
        "measured_pixel_threshold_keV": float(core.PIXEL_THRESHOLD_KEV),
        "W2_keV": list(WINDOWS["w2_510p58_511p42"]),
        "active_veto": prompt.explicit_veto_policy(config),
        "step05_implementation": str(prompt.STEP05),
        "response_geometry_key": "sf3",
    }


def run(config_path: Path, output: Path, workers: int) -> dict[str, Any]:
    prerequisite = check_prerequisites(config_path)
    if not prerequisite["ready"]:
        raise RuntimeError(json.dumps(prerequisite, indent=2, sort_keys=True))
    config = load_json(config_path, small_only=True)
    max_workers = int(config["transport"].get(
        "max_cpu_budget", config["transport"]["cpu_budget"]
    ))
    if workers < 1 or workers > max_workers:
        raise ValueError(f"workers must be within 1..{max_workers}")
    paths = input_paths(config)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite common-response output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    started = time.monotonic()
    try:
        contract = response_contract(config)
        plan = signal_plan_row(config)
        receipt = load_json(receipt_path(config), small_only=True)
        static = load_json(paths["signal_static_audit"], small_only=True)
        bank_sha = str(static["frozen_bank"]["output_sha256"])
        signal_job = {
            **plan,
            "sim_path": str(resolve_declared_path(receipt["sim_path"])),
            "receipt_path": str(receipt_path(config)),
        }
        diagnostics_path = work / "signal_ray_diagnostics.csv"
        scan = scan_signal_once(
            signal_job,
            work / "catalog/signal/SF3.pkl",
            diagnostics_path,
            config,
            bank_sha,
        )
        if scan["semantic_sim_scans"] != 1 or scan["sim_hashes_recomputed"] != 0:
            raise RuntimeError("signal one-pass/no-hash closure failed")
        signal_result = evaluate_signal(scan["catalog"], scan["diagnostics"])
        # Rewrite the initially emitted raw diagnostic rows with response results.
        write_csv(diagnostics_path, signal_result["diagnostics"])

        delayed_registry = delayed_disposition_registry(paths)
        delayed_run_families = [
            family for family in FAMILY_ORDER
            if delayed_registry[family]["execution_disposition"] == DELAYED_RUN_DISPOSITION
        ]
        delayed_zero_families = [
            family for family in FAMILY_ORDER
            if delayed_registry[family]["execution_disposition"] == DELAYED_ZERO_DISPOSITION
        ]
        tasks = [
            {
                "path": str(paths["prompt_catalog"] / f"{family}.pkl"),
                "stream": "prompt",
                "family": family,
                "execution_disposition": "NOT_APPLICABLE_PROMPT",
                "catalog_origin": "STAGE01_TRANSPORT_CATALOG",
            }
            for family in FAMILY_ORDER
        ]
        tasks.extend({
            "path": str(paths["delayed_catalog"] / f"{family}.pkl"),
            "stream": "delayed",
            "family": family,
            "execution_disposition": DELAYED_RUN_DISPOSITION,
            "catalog_origin": "STAGE03_TRANSPORT_CATALOG",
        } for family in delayed_run_families)
        results: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(evaluate_catalog, task): task for task in tasks}
            for completed, future in enumerate(as_completed(futures), start=1):
                results.append(future.result())
                if completed % 4 == 0 or completed == len(tasks):
                    print(json.dumps({
                        "event": "compact_background_catalog_response",
                        "completed": completed,
                        "total": len(tasks),
                    }, sort_keys=True), flush=True)
        # A zero-A15 cell has deliberately produced no stage03 pickle or SIM.
        # Supply its all-zero response rows from a structural in-memory catalog;
        # retain the activation upper as provenance, never as a central rate.
        results.extend(
            evaluate_structural_zero_delayed(family, delayed_registry[family])
            for family in delayed_zero_families
        )
        results.append(signal_result)
        aeff_cm2 = float(config["signal"]["input_optics_aeff_cm2"])
        cutflow = common_cutflow(results, aeff_cm2)
        expected_background_keys = {
            (stream, family, response, stage, window)
            for stream in STREAMS
            for family in FAMILY_ORDER
            for response, stage in CANONICAL_STAGES
            for window in FINAL_WINDOWS
        }
        observed_background_keys = {
            (row["stream"], row["family"], row["response_state"], row["stage"], row["window_id"])
            for row in cutflow if row["stream"] in STREAMS
        }
        if observed_background_keys != expected_background_keys:
            raise RuntimeError("fresh SF3 background common-cutflow closure differs")
        background = background_summary(cutflow)
        occupancy = occupancy_rows(results, aeff_cm2)
        acceptance = signal_acceptance(cutflow, aeff_cm2)
        selected = [row for result in results if result["stream"] in STREAMS for row in result["selected"]]
        first_rows, failure_rows = aggregate_diagnostics(signal_result["diagnostics"])
        passive_w_rows = passive_w_summary_rows(results)
        passive_w_lineage = passive_w_source_lineage_rows(selected)

        write_csv(
            work / "common_cutflow.csv",
            sorted(cutflow, key=lambda row: (
                row["geometry"], row["stream"], row["family"], row["response_state"],
                row["stage"], row["window_id"],
            )),
        )
        write_csv(
            work / "common_fullband_occupancy.csv",
            sorted(occupancy, key=lambda row: (row["stream"], row["family"])),
        )
        write_csv(
            work / "selected_background_w2_lineage.csv",
            sorted(selected, key=lambda row: (
                row["stream"], row["family"], row["job_name"], row["local_event_id"],
            )),
            fields=[
                "geometry", "stream", "family", "local_event_id", "batch_id", "job_name",
                "transport_seed", "measured_total_keV", "measured_multiplicity", "shield_keV",
                "plastic_keV", "passive_w_keV", "first_interaction_volume",
                "first_interaction_resolution", "first_interaction_in_passive_w",
                "has_pair_ia", "has_annihilation_ia", "w_pair_ia_count",
                "w_annihilation_ia_count", "pair_ia_unresolved_count",
                "annihilation_ia_unresolved_count", "event_weight_cps",
                "source_parent_ZA", "source_volume",
                "source_excitation_keV", "sim_initial_ZA", "parent_match_distance_cm",
                "source_file", "signal_scope",
            ],
        )
        write_csv(
            work / "background_prompt_delayed_cutflow.csv",
            sorted(background, key=lambda row: (
                row["geometry"], row["response_state"], row["stage"], row["window_id"],
            )),
        )
        write_csv(work / "signal_acceptance_effective_area.csv", acceptance)
        write_csv(work / "signal_first_interaction_summary.csv", first_rows)
        write_csv(work / "signal_failure_summary.csv", failure_rows)
        write_csv(work / "signal_ray_diagnostics.csv", signal_result["diagnostics"])
        write_csv(work / "passive_w_diagnostics.csv", passive_w_rows)
        write_csv(
            work / "passive_w_selected_delayed_source_lineage.csv",
            passive_w_lineage,
            fields=[
                "geometry", "stream", "family", "source_volume", "source_parent_ZA",
                "selected_measured_w2_events", "selected_measured_w2_rate_cps",
                "passive_w_role",
            ],
        )
        zero_upper_rows = [{
            "geometry": SIGNAL_GEOMETRY,
            "family": family,
            "execution_disposition": DELAYED_ZERO_DISPOSITION,
            "central_delayed_rate_cps": 0.0,
            "transported_ground_activity_Bq": 0.0,
            "buildup_sum_TT_s": delayed_registry[family]["buildup_sum_TT_s"],
            "transported_ground_rate_upper95_s-1": delayed_registry[family][
                "transported_ground_rate_upper95_s-1"
            ],
            "transported_ground_A15_upper95_Bq_conservative": delayed_registry[family][
                "transported_ground_A15_upper95_Bq_conservative"
            ],
            "zero_A15_upper_provenance": delayed_registry[family][
                "zero_A15_upper_provenance"
            ],
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq_reported_separately": delayed_registry[family][
                "known_holdout_activity_Bq"
            ],
            "unknown_holdout_state_count_reported_separately": delayed_registry[family][
                "unknown_activity_state_count"
            ],
            "catalog_origin": delayed_registry[family]["catalog_origin"],
            "stage03_catalog_opened": False,
            "SIM_opened": False,
        } for family in delayed_zero_families]
        write_csv(
            work / "delayed_zero_A15_provenance.csv",
            zero_upper_rows,
            fields=[
                "geometry", "family", "execution_disposition",
                "central_delayed_rate_cps", "transported_ground_activity_Bq",
                "buildup_sum_TT_s", "transported_ground_rate_upper95_s-1",
                "transported_ground_A15_upper95_Bq_conservative",
                "zero_A15_upper_provenance",
                "upper_excludes_known_and_unresolved_holdout",
                "known_holdout_activity_Bq_reported_separately",
                "unknown_holdout_state_count_reported_separately", "catalog_origin",
                "stage03_catalog_opened", "SIM_opened",
            ],
        )
        write_csv(work / "signal_input_manifest.csv", [{
            "geometry": SIGNAL_GEOMETRY,
            "job_id": SIGNAL_JOB_ID,
            "signal_scope": SIGNAL_SCOPE,
            "events": SIGNAL_TRIALS,
            "seed": plan["seed"],
            "receipt_path": str(receipt_path(config)),
            "sim_path": signal_job["sim_path"],
            "sim_bytes": receipt["sim_bytes"],
            "eventlist_path": prerequisite["validated"]["eventlist_path"],
            "eventlist_static_audit_sha256": bank_sha,
            "navigation_audit_path": str(paths["sf3_native_navigation"]),
            "semantic_sim_scans": 1,
            "sim_hash_recomputed": False,
            "frozen_se3_transport_required": False,
        }])

        def signal_cell(window: str) -> dict[str, Any]:
            return next(row for row in acceptance if row["window_id"] == window)

        sf3_final_background = next(
            row for row in background
            if row["geometry"] == "SF3" and row["response_state"] == FINAL_RESPONSE
            and row["stage"] == FINAL_STAGE and row["window_id"] == "w2_510p58_511p42"
        )
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
            "signal_scope": SIGNAL_SCOPE,
            "scope": "fresh SF3 prompt+delayed+full-envelope signal with passive-W diagnostics",
            "response_workers": workers,
            "catalogs": {
                "prompt": len(FAMILY_ORDER),
                "delayed": len(FAMILY_ORDER),
                "prompt_transport_opened": len(FAMILY_ORDER),
                "delayed_registered_cells": len(FAMILY_ORDER),
                "delayed_transport_opened": len(delayed_run_families),
                "delayed_structural_zero_rate": len(delayed_zero_families),
                "delayed_total_response_cells": len(FAMILY_ORDER),
                "signal": 1,
            },
            "delayed_dispositions": {
                "RUN_83334": delayed_run_families,
                "SKIP_ZERO_A15": delayed_zero_families,
                "zero_A15_central_rate_policy": "EXACT_ZERO__NO_CATALOG_OR_SIM_OPEN",
                "finite_upper_provenance": zero_upper_rows,
            },
            "response": contract,
            "signal": {
                "job_id": SIGNAL_JOB_ID,
                "receipt": str(receipt_path(config)),
                "sim_path": signal_job["sim_path"],
                "sim_digest": "OMITTED_BY_CONTRACT",
                "eventlist_rows": SIGNAL_TRIALS,
                "eventlist_bank_sha256_from_static_audit": bank_sha,
                "navigation_audit": str(paths["sf3_native_navigation"]),
                "input_optics_aeff_cm2": aeff_cm2,
                "normalization": f"Aeff_selected = {aeff_cm2} cm2 * N_selected/{SIGNAL_TRIALS}",
                "semantic_sim_scans": scan["semantic_sim_scans"],
                "sim_hashes_recomputed": scan["sim_hashes_recomputed"],
                "ray_id_rows": len(signal_result["diagnostics"]),
                "first_interaction_resolution_counts": dict(sorted(Counter(
                    str(row["first_interaction_resolution"]) for row in signal_result["diagnostics"]
                ).items())),
                "failure_category_counts": dict(sorted(Counter(
                    str(row["failure_category"]) for row in signal_result["diagnostics"]
                ).items())),
                "final_broad": signal_cell("broad_480_550"),
                "final_w2": signal_cell("w2_510p58_511p42"),
            },
            "final_measured_w2": {
                "SF3_background": sf3_final_background,
                "SF3_signal": signal_cell("w2_510p58_511p42"),
            },
            "frozen_se3": {
                "role": "DEFERRED_TO_MISSION_STAGE_SMALL_TABLE_DENOMINATOR",
                "SIMs_or_receipts_opened": 0,
            },
            "passive_w": {
                "volumes": sorted(PASSIVE_W_VOLUMES),
                "role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
                "diagnostic_rows": passive_w_rows,
                "selected_delayed_source_lineage_rows": len(passive_w_lineage),
            },
            "statistical_notes": {
                "background": "independent family MC components use sqrt(sum(w_i^2)); cutflow retains per-cell Garwood bounds",
                "signal": "fixed-N acceptance uses exact two-sided 95% Clopper-Pearson bounds scaled by input optics Aeff",
            },
            "outputs": {
                "common_cutflow_rows": len(cutflow),
                "common_fullband_occupancy_rows": len(occupancy),
                "selected_background_w2_lineage_rows": len(selected),
                "background_prompt_delayed_cutflow_rows": len(background),
                "signal_acceptance_rows": len(acceptance),
                "signal_ray_diagnostic_rows": len(signal_result["diagnostics"]),
                "delayed_zero_A15_provenance_rows": len(zero_upper_rows),
                "passive_w_diagnostic_rows": len(passive_w_rows),
                "passive_w_selected_delayed_source_lineage_rows": len(passive_w_lineage),
            },
            "elapsed_s": time.monotonic() - started,
            "known_exclusions": [
                "No fresh SE3 or S3d transport is run or required by this stage.",
                "Frozen SE3 enters only later through 47 small-table authorities.",
                "Mission folding, F3, and automatic geometry promotion remain outside stage04 authority.",
            ],
            "authority_boundary": "COMMON_RESPONSE_COMPLETE__FRESH_SF3_ONLY__NOT_MISSION_F3_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        write_json(work / "summary.json", summary)
        report = [
            "# SF3 Plan-1 common response",
            "",
            f"Status: `{summary['status']}`",
            "",
            "Only fresh SF3 prompt, delayed and 37,194-ray full-envelope signal transport is used. Frozen SE3 is consumed later as small-table comparison authority.",
            "",
            "| Quantity | Value |",
            "|---|---:|",
            f"| SF3 prompt W2 (cps) | {sf3_final_background['prompt_rate_cps']:.9g} |",
            f"| SF3 delayed W2 (cps) | {sf3_final_background['delayed_rate_cps']:.9g} |",
            f"| SF3 total W2 (cps) | {sf3_final_background['total_background_rate_cps']:.9g} |",
            f"| SF3 full-envelope W2 selected rays | {signal_cell('w2_510p58_511p42')['selected_events']} / {SIGNAL_TRIALS} |",
            f"| SF3 full-envelope W2 Aeff (cm2) | {signal_cell('w2_510p58_511p42')['selected_effective_area_cm2']:.9g} |",
            f"| Delayed RUN_83334 catalogs opened | {len(delayed_run_families)} |",
            f"| Delayed SKIP_ZERO_A15 structural zero cells | {len(delayed_zero_families)} |",
            "",
            "A SKIP_ZERO_A15 family contributes an exact central zero through an in-memory structural catalog. No nonexistent stage03 pickle or SIM is opened; its finite activation upper and separate holdout provenance are retained in delayed_zero_A15_provenance.csv.",
            "",
            "The signal diagnostic table retains every zero-based frozen ray ID, first recorded interaction evidence, BPE/plastic/BGO deposits, response decisions, and the final failure category. First-interaction volume is resolved by a same-time primary CC-hit when available; zero-deposit interactions remain explicitly unresolved rather than guessed.",
            "",
        ]
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": summary["status"],
            "generated_utc": utc_now(),
            "analysis_code": display_path(HERE),
            "reused_code": [
                str(prompt.OLD_CATALOG_PARSER), str(prompt.CORRECTED_CORE), str(prompt.STEP05),
            ],
            "cross_worktree_provenance": {
                "current_package": str(PACKAGE_ROOT),
                "retained_response_worktree": str(SOURCE_WORKTREE),
                "handoff_geometry_worktree": str(HANDOFF_WORKTREE),
                "absolute_path_fallback_enabled": True,
            },
            "input_small_authorities": [{
                "role": role,
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_small(path, max_bytes=MAX_SMALL_CSV_BYTES),
            } for role, path in (
                ("prompt_summary", paths["prompt_summary"]),
                ("delayed_summary", paths["delayed_summary"]),
                ("delayed_cell_coverage", paths["delayed_coverage"]),
                ("signal_receipt", receipt_path(config)),
                ("sf3_native_navigation_audit", paths["sf3_native_navigation"]),
                ("signal_transport_gate", paths["signal_transport_gate"]),
                ("signal_static_audit", paths["signal_static_audit"]),
            )],
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in files
            ],
            "large_payload_policy": {
                "fresh_signal_SIM_semantic_scans": 1,
                "fresh_signal_SIM_hashes": 0,
                "frozen_SE3_SIM_opens": 0,
                "fresh_S3d_SIM_opens": 0,
                "background_rich_SIM_opens": 0,
                "background_compact_catalog_opens": len(FAMILY_ORDER) + len(delayed_run_families),
                "delayed_zero_A15_catalog_opens": 0,
                "delayed_zero_A15_SIM_opens": 0,
            },
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(json.dumps({
            "status": summary["status"],
            "signal_scope": SIGNAL_SCOPE,
            "signal_trials": SIGNAL_TRIALS,
            "frozen_se3_transport_required": False,
            "output": str(output),
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def legacy_se3_synthetic_prerequisite_self_test() -> dict[str, Any]:
    """Prove the metadata gate accepts an invalid-gzip SIM without opening it."""
    root = Path(tempfile.mkdtemp(prefix="se3_common_prereq_selftest_", dir="/tmp"))
    try:
        stage01 = root / "01"
        stage03 = root / "03"
        run_root = root / "run"
        audits = root / "audit"
        frozen = root / "frozen/04_common_response"
        setup = root / "SE3.geo.setup"
        setup.write_text("Name synthetic\n", encoding="utf-8")
        write_json(stage01 / "summary.json", {"status": "PASS__SYNTHETIC_PROMPT"})
        zero_family = FAMILY_ORDER[0]
        buildup_sum_tt_s = 100.0
        zero_rate_upper = 3.6888794541139363 / buildup_sum_tt_s
        activity_rows: list[dict[str, Any]] = []
        coverage_rows: list[dict[str, Any]] = []
        for family in FAMILY_ORDER:
            prompt_catalog = stage01 / "catalog/SE3" / f"{family}.pkl"
            prompt_catalog.parent.mkdir(parents=True, exist_ok=True)
            prompt_catalog.write_bytes(b"synthetic-prompt-not-opened")
            is_zero = family == zero_family
            disposition = (
                DELAYED_ZERO_DISPOSITION if is_zero else DELAYED_RUN_DISPOSITION
            )
            activity_rows.append({
                "family": family,
                "execution_disposition": disposition,
                "transported_ground_activity_Bq": 0.0 if is_zero else 1.0,
                "event_weight_cps": 0.0 if is_zero else 1.0 / 83_334,
                "equivalent_time_s": None if is_zero else 83_334.0,
                "transported_ground_rate_upper95_s-1": (
                    zero_rate_upper if is_zero else None
                ),
                "transported_ground_A15_upper95_Bq_conservative": (
                    zero_rate_upper if is_zero else None
                ),
                "known_holdout_activity_Bq": 0.25 if is_zero else 0.0,
                "unknown_activity_state_count": 1 if is_zero else 0,
            })
            delayed_catalog = stage03 / "catalog/SE3" / f"{family}.pkl"
            if not is_zero:
                delayed_catalog.parent.mkdir(parents=True, exist_ok=True)
                delayed_catalog.write_bytes(b"synthetic-delayed-RUN-not-opened")
            coverage_rows.append({
                "geometry": SIGNAL_GEOMETRY,
                "family": family,
                "source_status": (
                    "ZERO_SOURCE__SYNTHETIC" if is_zero else "TRANSPORT_COMPLETE__SYNTHETIC"
                ),
                "execution_disposition": disposition,
                "triggers": 0 if is_zero else 83_334,
                "central_delayed_rate_cps": 0.0 if is_zero else "DEFERRED",
                "transported_ground_rate_upper95_s-1": (
                    zero_rate_upper if is_zero else ""
                ),
                "transported_ground_A15_upper95_Bq_conservative": (
                    zero_rate_upper if is_zero else ""
                ),
                "catalog_path": "" if is_zero else str(delayed_catalog),
                "sim_path": "" if is_zero else "/synthetic/not-opened.sim.gz",
                "receipt_path": "" if is_zero else "/synthetic/not-opened.receipt.json",
            })
        write_json(stage03 / "summary.json", {
            "status": "PASS__SYNTHETIC_DELAYED_RUN_PLUS_ZERO",
            "registered_source_cells": len(FAMILY_ORDER),
            "transport_jobs": len(FAMILY_ORDER) - 1,
            "skipped_zero_A15_jobs": 1,
            "activity_and_weights": activity_rows,
            "zero_source_cells": [{
                "family": zero_family,
                "execution_disposition": DELAYED_ZERO_DISPOSITION,
                "transported_ground_activity_Bq": 0.0,
                "central_delayed_rate_cps": 0.0,
                "buildup_sum_TT_s": buildup_sum_tt_s,
                "zero_count_garwood_two_sided95_upper": 3.6888794541139363,
                "transported_ground_rate_upper95_s-1": zero_rate_upper,
                "transported_ground_A15_upper95_Bq_conservative": zero_rate_upper,
                "upper_provenance": (
                    "synthetic two-sided95 3.6888794541139363/sumTT; holdout separate"
                ),
            }],
        })
        write_csv(stage03 / "delayed_cell_coverage.csv", coverage_rows)

        source = root / "signal.source"
        eventlist = root / "signal.eventlist.dat"
        eventlist_bytes = b"synthetic-eventlist-not-opened\n"
        eventlist.write_bytes(eventlist_bytes)
        bank_sha = hashlib.sha256(eventlist_bytes).hexdigest()
        navigation = audits / "navigation.json"
        write_json(navigation, {
            "driver_validation": {"status": "PASS"},
            "geometries": {"SE3": {
                "status": "PASS", "parsed_rows": SIGNAL_TRIALS,
                "bpe": {"zero_chord_passes": SIGNAL_TRIALS},
                "plastic": {"full_chord_passes": SIGNAL_TRIALS},
            }},
        })
        scope_override = audits / "scope_override.json"
        write_json(scope_override, {
            "status": "PASS__SE3_ONLY_TRANSPORT_SCOPE_LOCKED",
            "excluded_transport_jobs": {
                "signal_full_envelope_s3d_o8": "USER_EXPLICITLY_FORBADE_S3D_RERUN"
            },
        })
        s3d_exclusion = "USER_SCOPE_SYNTHETIC__NO_S3D_RERUN"
        write_json(audits / "gate.json", {
            "status": "PASS",
            "transport_scope": SIGNAL_SCOPE,
            "authority": {"sha256": sha256_small(navigation)},
            "permitted_signal_jobs": [SIGNAL_JOB_ID],
            "excluded_signal_jobs": {
                "signal_full_envelope_s3d_o8": s3d_exclusion,
            },
            "scope_override_authority": str(scope_override),
            "paired_bank_rows": SIGNAL_TRIALS,
            "paired_bank_sha256": bank_sha,
        })
        write_json(audits / "static.json", {
            "frozen_bank": {
                "output_sha256": bank_sha,
                "data_rows": SIGNAL_TRIALS,
                "first_id": 0,
                "last_id": SIGNAL_TRIALS - 1,
                "zero_based_sequential_ids": True,
            },
            "pair": {
                "no_resampling_or_bootstrap": True,
                "jobs": [{
                    "job_id": SIGNAL_JOB_ID,
                    "events": SIGNAL_TRIALS,
                    "eventlist_path": str(eventlist),
                    "eventlist_sha256": bank_sha,
                }],
            },
        })

        frozen_rows = []
        for response, stage in sorted(CANONICAL_STAGES):
            for window in FINAL_WINDOWS:
                frozen_rows.append({
                    "geometry": "S3d_O8", "response_state": response, "stage": stage,
                    "window_id": window, "prompt_events": 0, "prompt_rate_cps": 0,
                    "prompt_stat_sigma_cps": 0, "delayed_events": 0,
                    "delayed_rate_cps": 0, "delayed_stat_sigma_cps": 0,
                    "total_background_rate_cps": 0,
                    "total_background_stat_sigma_cps": 0,
                })
        write_csv(frozen / "background_prompt_delayed_cutflow.csv", frozen_rows)

        source.write_text(
            f"Geometry {setup}\nSeed 93405522\n"
            f"synthetic.EventList {eventlist}\n",
            encoding="utf-8",
        )
        sim = root / "signal.sim.gz"
        sim.write_bytes(b"this-is-not-a-gzip-stream")
        log = root / "signal.log"
        log.write_text("synthetic\n", encoding="utf-8")
        receipt = run_root / "receipts" / f"{SIGNAL_JOB_ID}.json"
        write_json(receipt, {
            "status": "PASS", "job_id": SIGNAL_JOB_ID, "stage": "signal",
            "geometry": SIGNAL_GEOMETRY, "mode": "signal", "events": SIGNAL_TRIALS,
            "seed": 93405522, "source_path": str(source),
            "source_sha256": sha256_small(source), "sim_path": str(sim),
            "sim_bytes": sim.stat().st_size, "log_path": str(log),
            "log_bytes": log.stat().st_size,
            "sim_header": {"geometry": str(setup), "seed": 93405522},
            "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
        })
        plan = root / "job_plan.csv"
        write_csv(plan, [{
            "ordinal": 1, "job_id": SIGNAL_JOB_ID, "stage": "signal",
            "geometry": SIGNAL_GEOMETRY, "mode": "signal", "family": SIGNAL_FAMILY,
            "shard": 1, "events": SIGNAL_TRIALS, "s3d_histories": SIGNAL_TRIALS,
            "target_histories": SIGNAL_TRIALS, "seed": 93405522,
            "seed_identity": "synthetic", "paired_seed_exception": "True",
            "source_path": str(source), "setup_path": str(setup), "estimated_bytes": 1,
            "production_canary": "False",
        }])
        config = root / "config.json"
        write_json(config, {
            "schema_version": 1,
            "analysis": {
                "response_fwhm_keV": 0.42,
                "measured_pixel_threshold_keV": 0.3,
                "active_veto_threshold_keV": 50.0,
                "w2_keV": [510.58, 511.42],
            },
            "outputs": {"stage_01": str(stage01), "stage_03": str(stage03)},
            "frozen_s3d": {"m05_outputs": str(root / "frozen")},
            "transport": {
                "job_plan": str(plan),
                "execution_exclusions": {
                    "signal_full_envelope_s3d_o8": s3d_exclusion
                },
            },
            "run_root": str(run_root),
            "geometry": {
                "shield_veto_volumes": ["bgo1", "bgo2", "bgo3"],
                "plastic_veto_volumes": ["plastic1", "plastic2", "plastic3"],
                "active_veto_volumes": [
                    "bgo1", "bgo2", "bgo3", "plastic1", "plastic2", "plastic3"
                ],
                "apply_plastic_veto": True,
            },
            "signal": {"eventlist_rows": SIGNAL_TRIALS, "input_optics_aeff_cm2": 20.08476},
            "audits": {
                "signal_navigation": str(navigation),
                "signal_transport_gate": str(audits / "gate.json"),
                "signal_static": str(audits / "static.json"),
                "user_scope_override": str(scope_override),
            },
        })
        ready = check_prerequisites(config)
        if not ready["ready"]:
            raise RuntimeError(json.dumps(ready, indent=2, sort_keys=True))
        gate_path = audits / "gate.json"
        valid_gate = load_json(gate_path, small_only=True)
        drift_cases = (
            (
                "transport_scope", "FULL_ENVELOPE_PAIRED",
                "scope is not FULL_ENVELOPE_SE3_ONLY",
            ),
            (
                "permitted_signal_jobs", [SIGNAL_JOB_ID, "signal_full_envelope_s3d_o8"],
                "permitted jobs are not exactly SE3-only",
            ),
            (
                "excluded_signal_jobs", {"signal_full_envelope_s3d_o8": "STALE_GENERIC_EXCLUSION"},
                "lacks the user-scope S3d exclusion",
            ),
            (
                "scope_override_authority", str(audits / "wrong_scope_override.json"),
                "scope_override_authority path binding differs",
            ),
        )
        for field, value, expected_error in drift_cases:
            drifted_gate = json.loads(json.dumps(valid_gate))
            drifted_gate[field] = value
            write_json(gate_path, drifted_gate)
            drifted = check_prerequisites(config)
            if drifted["ready"] or not any(
                expected_error in error for error in drifted["errors"]
            ):
                raise RuntimeError(
                    f"synthetic signal-scope drift was not rejected: {field}"
                )
        write_json(gate_path, valid_gate)
        zero_catalog_path = stage03 / "catalog/SE3" / f"{zero_family}.pkl"
        if zero_catalog_path.exists() or any(
            item.startswith(f"delayed_catalog_{zero_family}:")
            for item in ready["missing_inputs"]
        ):
            raise RuntimeError("synthetic SKIP_ZERO_A15 unexpectedly required a pickle")
        registry = delayed_disposition_registry(input_paths(load_json(config, small_only=True)))
        zero_result = evaluate_structural_zero_delayed(zero_family, registry[zero_family])
        zero_cutflow = common_cutflow([zero_result], 20.08476)
        observed_zero_keys = {
            (row["stream"], row["family"], row["response_state"], row["stage"], row["window_id"])
            for row in zero_cutflow
        }
        expected_zero_keys = {
            ("delayed", zero_family, response, stage, window)
            for response, stage in CANONICAL_STAGES
            for window in FINAL_WINDOWS
        }
        if observed_zero_keys != expected_zero_keys or any(
            int(row["selected_events"]) != 0
            or float(row["weighted_value"]) != 0.0
            or row["execution_disposition"] != DELAYED_ZERO_DISPOSITION
            or not row["zero_A15_upper_provenance"]
            for row in zero_cutflow
        ):
            raise RuntimeError("synthetic SKIP_ZERO_A15 structural cutflow closure failed")

        run_family = next(family for family in FAMILY_ORDER if family != zero_family)
        run_catalog = stage03 / "catalog/SE3" / f"{run_family}.pkl"
        run_catalog.unlink()
        missing_run = check_prerequisites(config)
        if missing_run["ready"] or not any(
            item.startswith(f"delayed_catalog_{run_family}:")
            for item in missing_run["missing_inputs"]
        ):
            raise RuntimeError("synthetic RUN_83334 missing-catalog NOT_READY gate failed")
        run_catalog.write_bytes(b"synthetic-delayed-RUN-not-opened")
        receipt.unlink()
        missing = check_prerequisites(config)
        if missing["ready"] or not any(
            item.startswith("signal_receipt:") for item in missing["missing_inputs"]
        ):
            raise RuntimeError("synthetic missing-receipt NOT_READY gate failed")
        return {
            "status": "PASS__SYNTHETIC_RUN_PLUS_ZERO_PREREQUISITE_NO_SIM_OPEN",
            "invalid_gzip_SIM_was_accepted_by_metadata_gate": True,
            "RUN_83334_catalog_required": True,
            "SKIP_ZERO_A15_catalog_or_SIM_required": False,
            "SKIP_ZERO_A15_structural_cutflow_rows": len(zero_cutflow),
            "SKIP_ZERO_A15_finite_upper_provenance_retained": True,
            "S3d_signal_scope_drift_rejected": True,
            "missing_receipt_NOT_READY_gate": True,
            "fresh_s3d_receipt_required": False,
            "signal_scope": SIGNAL_SCOPE,
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def synthetic_prerequisite_self_test() -> dict[str, Any]:
    """Exercise the SF3-only static contract without touching a SIM payload."""
    config = load_json(DEFAULT_CONFIG, small_only=True)
    geometry = config["geometry"]
    passive = frozenset(str(value) for value in geometry["passive_w_volumes"])
    active = frozenset(str(value) for value in geometry["active_veto_volumes"])
    shield = frozenset(str(value) for value in geometry["shield_veto_volumes"])
    plastic = frozenset(str(value) for value in geometry["plastic_veto_volumes"])
    if passive != PASSIVE_W_VOLUMES:
        raise AssertionError("SF3 passive-W closure differs")
    if len(active) != 6 or active != shield | plastic or passive & active:
        raise AssertionError("six-volume active-veto/passive-W separation failed")
    analysis = config["analysis"]
    if (
        float(analysis["response_fwhm_keV"]) != 0.42
        or float(analysis["measured_pixel_threshold_keV"]) != 0.3
        or float(analysis["active_veto_threshold_keV"]) != 50.0
        or [float(value) for value in analysis["w2_keV"]] != [510.58, 511.42]
    ):
        raise AssertionError("frozen measured-response contract differs")
    if SIGNAL_JOB_ID != "signal_full_envelope_sf3" or SIGNAL_TRIALS != 37_194:
        raise AssertionError("single fresh-SF3 signal contract differs")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_COMMON_RESPONSE_STATIC_SELF_TEST",
        "sim_opened": False,
        "checks": [
            "six_active_BGO_plus_plastic_volumes",
            "three_SF3_W_volumes_passive_and_disjoint",
            "frozen_measured_response_veto_W2_contract",
            "single_fresh_37194_ray_SF3_signal",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--check-prerequisites", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(synthetic_prerequisite_self_test(), indent=2, sort_keys=True))
        return 0
    config_path = args.config.resolve()
    if args.check_prerequisites:
        result = check_prerequisites(config_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    config = load_json(config_path, small_only=True)
    output = args.output or resolve_declared_path(config["outputs"]["stage_04"])
    workers = (
        args.workers if args.workers is not None
        else int(config["transport"]["cpu_budget"])
    )
    run(config_path, output.resolve(), workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
