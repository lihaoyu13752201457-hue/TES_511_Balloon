#!/usr/bin/env python3
"""Build the SF3 Plan-1 delayed raw catalogs and source-mixture QA.

This candidate-owned adapter consumes the eight-row SF3 activation
``delayed_source_index.csv`` and canonical local delayed PASS receipts only for
rows marked ``RUN_83334``.  ``SKIP_ZERO_A15`` rows require no receipt or SIM and
retain central zero plus a finite upper-limit record.  Every selected rich SIM
is decompressed exactly once.  The single pass retains raw TES hits,
the explicit three-BGO plus three-plastic deposits, and exact-position
activation-parent lineage.  Detector response, pixel thresholding, veto cuts,
W2 selection, and Step05 are deliberately deferred to stage 04.

``--check-prerequisites`` reads only small plans, receipts, activation tables,
and file metadata.  It never opens or hashes a rich SIM payload.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import shutil
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_prompt_analysis as prompt
from sf3_plan1_common import DELAYED_EVENTS, FAMILIES, PACKAGE_ROOT, PROFILE_ID, REPO_ROOT


HERE = Path(__file__).resolve()
DEFAULT_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
FAMILY_ORDER = tuple(FAMILIES)
EXPECTED_JOBS = len(FAMILY_ORDER)
EXPECTED_EVENTS_PER_JOB = int(DELAYED_EVENTS)
EXPECTED_TOTAL_EVENTS = EXPECTED_JOBS * EXPECTED_EVENTS_PER_JOB
FULL_POSITION_BLOCKS = 50_000
POSITION_STRIDE = 5
SELECTED_POSITION_BLOCKS = FULL_POSITION_BLOCKS // POSITION_STRIDE
EPSILON_SPECTRAL_HEADER = "SpectralType Mono 1e-06"
SOURCE_STATUS_PREFIX = "PASS__"
RUN_DISPOSITION = "RUN_83334"
ZERO_DISPOSITION = "SKIP_ZERO_A15"
ZERO_STATUS_PREFIX = "ZERO_SOURCE__"
ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER = 3.6888794541139363
INIT_ZA_LINEAGE_POLICY = (
    "IA_INIT_PART15_IS_TRANSPORT_OR_DAUGHTER_ZA__"
    "SOURCE_PARENT_ZA_COMES_FROM_UNIQUE_EXACT_POSITION_MAPPING"
)
M_SAMPLING_LINEAGE_AUTHORITY = (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "01_m_sampling_validation_20260810/README.md#line-65"
)
SAME_SOURCE_PARENT_ZA = "SAME_AS_SOURCE_PARENT_ZA"
TRANSPORT_DAUGHTER_ZA = "TRANSPORT_OR_DAUGHTER_ZA_DIFFERS_FROM_SOURCE_PARENT"


def load_json(path: Path) -> dict[str, Any]:
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


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str] | None = None,
) -> None:
    if not rows and fields is None:
        raise RuntimeError(f"refusing to write schema-less empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def init_source_za_relation(sim_initial_za: int, source_parent_za: int) -> str:
    """Classify, but never gate lineage on, the serialized INIT ZA.

    IA INIT field 15 is the transported/daughter state.  The sampled parent is
    instead identified by the already-strict exact-position mapping.
    """
    return (
        SAME_SOURCE_PARENT_ZA
        if sim_initial_za == source_parent_za
        else TRANSPORT_DAUGHTER_ZA
    )


def activation_index_path(config: dict[str, Any]) -> Path:
    return Path(config["outputs"]["stage_02"]) / "delayed_source_index.csv"


def resolve_declared_path(value: str) -> Path:
    """Resolve fresh absolute paths and retained repository-relative paths."""
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    candidates = (
        REPO_ROOT / path,
        Path("/home/ubuntu/TES_511_Balloon") / path,
        PACKAGE_ROOT / path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def delayed_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in prompt.read_plan(config)
        if row["stage"] == "delayed" and row["mode"] == "delayed"
    ]
    return sorted(rows, key=lambda row: int(row["ordinal"]))


def read_source_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"activation delayed-source index is empty: {path}")
    return rows


def source_index_by_family(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("geometry") != "SF3":
            continue
        family = str(row.get("incident_family", row.get("family", "")))
        if not family:
            raise RuntimeError("SF3 delayed-source row lacks incident_family/family")
        if family in selected:
            raise RuntimeError(f"duplicate SF3 delayed-source row: {family}")
        selected[family] = row
    return selected


def first_present(row: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        value = row.get(name, "").strip()
        if value:
            return value
    raise KeyError(f"none of the required fields are populated: {names}")


def activity_bq(row: dict[str, str]) -> float:
    return float(first_present(
        row,
        (
            "transported_ground_activity_Bq",
            "included_ground_activity_Bq",
            "activity_Bq",
        ),
    ))


def int_field(row: dict[str, str], name: str, default: int = 0) -> int:
    value = row.get(name, "").strip()
    return int(value) if value else default


def float_field(row: dict[str, str], name: str, default: float = 0.0) -> float:
    value = row.get(name, "").strip()
    return float(value) if value else default


def source_paths(row: dict[str, str]) -> dict[str, Path]:
    return {
        "transport_source": resolve_declared_path(first_present(
            row, ("source_path", "activation_source_path", "prepared_source_path")
        )),
        "positions": resolve_declared_path(first_present(
            row, ("sampled_positions_path", "positions_path")
        )),
        "manifest": resolve_declared_path(first_present(
            row, ("source_manifest_path", "manifest_path")
        )),
    }


def validate_source_row(
    family: str,
    row: dict[str, str],
    plan_row: dict[str, Any],
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    try:
        activity = activity_bq(row)
    except Exception as exc:
        return [f"{family} activation activity is unreadable: {exc}"], None
    source_status = row.get("source_status", "").strip()
    execution_disposition = row.get("execution_disposition", "").strip()
    is_run = execution_disposition == RUN_DISPOSITION
    is_zero = execution_disposition == ZERO_DISPOSITION
    if is_run:
        if not source_status.startswith(SOURCE_STATUS_PREFIX):
            errors.append(f"{family} RUN source status is not PASS: {source_status}")
        if not math.isfinite(activity) or activity <= 0.0:
            errors.append(f"{family} RUN transported ground activity is not positive finite")
    elif is_zero:
        if not source_status.startswith(ZERO_STATUS_PREFIX):
            errors.append(f"{family} zero-source status differs: {source_status}")
        if not math.isfinite(activity) or activity != 0.0:
            errors.append(f"{family} SKIP_ZERO_A15 activity must be exactly zero")
    else:
        errors.append(
            f"{family} unknown execution_disposition {execution_disposition!r}; "
            f"expected {RUN_DISPOSITION}|{ZERO_DISPOSITION}"
        )
    explicit_dual_fields = (
        "original_blocks",
        "transport_blocks",
        "position_stride",
        "original_block_flux_Bq",
        "transport_block_flux_Bq",
        "original_total_Bq",
        "transport_total_Bq",
        "original_closure_Bq",
        "transport_closure_Bq",
    )
    present_dual = [name for name in explicit_dual_fields if name in row]
    if present_dual and len(present_dual) != len(explicit_dual_fields):
        errors.append(
            f"{family} activation index has a partial original/transport mixture contract"
        )
    has_explicit_dual = len(present_dual) == len(explicit_dual_fields)
    if has_explicit_dual:
        original_blocks = int(row["original_blocks"])
        transport_blocks = int(row["transport_blocks"])
        position_stride = int(row["position_stride"])
        original_flux = float_field(row, "original_block_flux_Bq")
        transport_flux = float_field(row, "transport_block_flux_Bq")
        original_total = float(row["original_total_Bq"])
        transport_total = float(row["transport_total_Bq"])
        original_closure = float(row["original_closure_Bq"])
        transport_closure = float(row["transport_closure_Bq"])
        expected_original_blocks = FULL_POSITION_BLOCKS if is_run else 0
        expected_transport_blocks = SELECTED_POSITION_BLOCKS if is_run else 0
        if original_blocks != expected_original_blocks:
            errors.append(
                f"{family} original position blocks {original_blocks} != {expected_original_blocks}"
            )
        if transport_blocks != expected_transport_blocks:
            errors.append(
                f"{family} transport position blocks {transport_blocks} != {expected_transport_blocks}"
            )
        if int_field(row, "original_pointsource_blocks", -1) != expected_original_blocks:
            errors.append(
                f"{family} original_pointsource_blocks is not {expected_original_blocks}"
            )
        if int_field(row, "pointsource_blocks", -1) != expected_transport_blocks:
            errors.append(f"{family} pointsource_blocks is not {expected_transport_blocks}")
        if position_stride != POSITION_STRIDE:
            errors.append(f"{family} source position stride {position_stride} != 5")
        if not math.isclose(
            original_flux * original_blocks, activity, rel_tol=2.0e-12, abs_tol=1.0e-12
        ):
            errors.append(f"{family} original 50k block flux does not close to A15")
        if not math.isclose(
            transport_flux * transport_blocks, activity, rel_tol=2.0e-12, abs_tol=1.0e-12
        ):
            errors.append(f"{family} transport 10k block flux does not close to A15")
        if not math.isclose(
            transport_flux, original_flux * POSITION_STRIDE, rel_tol=2.0e-12, abs_tol=1.0e-18
        ):
            errors.append(f"{family} transport block flux is not original flux times five")
        if not math.isclose(original_total, activity, rel_tol=2.0e-12, abs_tol=1.0e-12):
            errors.append(f"{family} declared original total Bq does not close to A15")
        if not math.isclose(transport_total, activity, rel_tol=2.0e-12, abs_tol=1.0e-12):
            errors.append(f"{family} declared transport total Bq does not close to A15")
        if not math.isclose(original_closure, original_total - activity, rel_tol=0.0, abs_tol=1.0e-12):
            errors.append(f"{family} declared original closure residual differs")
        if not math.isclose(transport_closure, transport_total - activity, rel_tol=0.0, abs_tol=1.0e-12):
            errors.append(f"{family} declared transport closure residual differs")
        if is_zero and any(
            value != 0.0
            for value in (
                original_flux,
                transport_flux,
                original_total,
                transport_total,
                original_closure,
                transport_closure,
            )
        ):
            errors.append(f"{family} SKIP_ZERO_A15 mixture values must all be zero")
    else:
        # Compatibility with the retained M05 source index.  Fresh SF3 stage02
        # always publishes the explicit dual-layer fields above.
        original_blocks = int_field(row, "pointsource_blocks", FULL_POSITION_BLOCKS)
        transport_blocks = SELECTED_POSITION_BLOCKS
        position_stride = POSITION_STRIDE
        original_flux = float_field(row, "flux_per_point_Bq", activity / FULL_POSITION_BLOCKS)
        transport_flux = original_flux * POSITION_STRIDE
        original_total = original_flux * original_blocks
        transport_total = transport_flux * transport_blocks
        original_closure = original_total - activity
        transport_closure = transport_total - activity
        if is_zero:
            errors.append(f"{family} SKIP_ZERO_A15 requires the fresh explicit dual-layer schema")
        elif original_blocks != FULL_POSITION_BLOCKS:
            errors.append(f"{family} legacy source index does not declare 50000 original blocks")
    flux_per_point = float_field(row, "flux_per_point_Bq", transport_flux)
    if not math.isclose(flux_per_point, transport_flux, rel_tol=2.0e-12, abs_tol=1.0e-18):
        errors.append(f"{family} flux_per_point_Bq is not the transport-card block flux")
    requested = int_field(row, "requested_decay_triggers", EXPECTED_EVENTS_PER_JOB)
    if requested != EXPECTED_EVENTS_PER_JOB:
        errors.append(
            f"{family} requested delayed triggers {requested} != {EXPECTED_EVENTS_PER_JOB}"
        )
    if not all(math.isfinite(value) for value in (
        flux_per_point, original_flux, transport_flux, original_total, transport_total,
        original_closure, transport_closure,
    )):
        errors.append(f"{family} source-mixture closure contains non-finite values")
    buildup_sum_tt_s = float_field(row, "buildup_sum_TT_s", math.nan)
    zero_count_upper = float_field(row, "zero_count_garwood_two_sided95_upper", math.nan)
    rate_upper95 = float_field(row, "transported_ground_rate_upper95_s-1", math.nan)
    a15_upper95 = float_field(
        row, "transported_ground_A15_upper95_Bq_conservative", math.nan
    )
    zero_upper_provenance = row.get("zero_A15_upper_provenance", "").strip()
    holdout_separate = (
        row.get("upper_excludes_known_and_unresolved_holdout", "").strip().lower() == "true"
    )
    known_holdout_activity = float_field(row, "known_holdout_activity_Bq")
    unknown_holdout_states = int_field(row, "unknown_activity_state_count")
    if not math.isfinite(known_holdout_activity) or known_holdout_activity < 0.0:
        errors.append(f"{family} known holdout activity is invalid")
    if unknown_holdout_states < 0:
        errors.append(f"{family} unknown holdout state count is negative")
    if not math.isfinite(buildup_sum_tt_s) or buildup_sum_tt_s <= 0.0:
        errors.append(f"{family} source row lacks positive buildup sumTT")
    if is_zero:
        if not math.isclose(
            zero_count_upper,
            ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            errors.append(f"{family} zero-source two-sided 95% count upper differs")
        expected_rate_upper = (
            ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / buildup_sum_tt_s
            if math.isfinite(buildup_sum_tt_s) and buildup_sum_tt_s > 0.0
            else math.nan
        )
        if not math.isclose(rate_upper95, expected_rate_upper, rel_tol=2.0e-12, abs_tol=1.0e-18):
            errors.append(f"{family} zero-source upper rate is not 3.688879/sumTT")
        if not math.isclose(a15_upper95, rate_upper95, rel_tol=0.0, abs_tol=1.0e-18):
            errors.append(f"{family} conservative zero-source A15 upper differs from upper rate")
        if "3.6888794541139363/sumTT" not in zero_upper_provenance:
            errors.append(f"{family} zero-source upper provenance is missing")
        if not holdout_separate:
            errors.append(f"{family} zero-source upper does not explicitly separate holdout")
    else:
        # Positive cells use their measured A15/event weight.  The special
        # zero-count upper fields must remain absent rather than being mixed
        # into their central normalization.
        if any(row.get(name, "").strip() for name in (
            "zero_count_garwood_two_sided95_upper",
            "transported_ground_rate_upper95_s-1",
            "transported_ground_A15_upper95_Bq_conservative",
            "zero_A15_upper_provenance",
        )):
            errors.append(f"{family} RUN source unexpectedly publishes zero-source upper fields")
        zero_count_upper = math.nan
        rate_upper95 = math.nan
        a15_upper95 = math.nan
    try:
        paths = source_paths(row)
    except Exception as exc:
        return errors + [f"{family} source provenance paths are unreadable: {exc}"], None
    for role, path in paths.items():
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"{family} {role} is missing or empty: {path}")

    manifest: dict[str, Any] | None = None
    if paths["manifest"].is_file():
        try:
            manifest = load_json(paths["manifest"])
            manifest_activity = manifest.get(
                "included_ground_activity_Bq",
                manifest.get("transported_ground_activity_Bq"),
            )
            if manifest_activity is not None and not math.isclose(
                float(manifest_activity), activity, rel_tol=2.0e-12, abs_tol=1.0e-12
            ):
                errors.append(f"{family} source-manifest activity binding differs")
            if manifest.get("geometry") not in (None, "SF3"):
                errors.append(f"{family} source manifest names a non-SF3 geometry")
            if manifest.get("family") not in (None, family):
                errors.append(f"{family} source manifest family binding differs")
            if manifest.get("execution_disposition") != execution_disposition:
                errors.append(f"{family} source manifest execution disposition differs")
            if manifest.get("source") is not None and resolve_declared_path(
                str(manifest["source"])
            ) != paths["transport_source"]:
                errors.append(f"{family} source manifest transport-card binding differs")
            if manifest.get("sampled_positions_table") is not None and resolve_declared_path(
                str(manifest["sampled_positions_table"])
            ) != paths["positions"]:
                errors.append(f"{family} source manifest sampled-position binding differs")
            if manifest.get("triggers_requested") not in (None, EXPECTED_EVENTS_PER_JOB):
                errors.append(f"{family} source manifest delayed-trigger binding differs")
            if manifest.get("transport_seed") not in (None, int(plan_row["seed"])):
                errors.append(f"{family} source manifest transport-seed binding differs")
            if manifest.get("sampling_seed") not in (None, int_field(row, "sampling_seed")):
                errors.append(f"{family} source manifest sampling-seed binding differs")
            if row.get("source_sha256") and manifest.get("source_sha256") != row.get(
                "source_sha256"
            ):
                errors.append(f"{family} source-index/manifest digest binding differs")
            manifest_sum_tt = manifest.get("buildup_sum_TT_s")
            if manifest_sum_tt is None or not math.isclose(
                float(manifest_sum_tt), buildup_sum_tt_s, rel_tol=0.0, abs_tol=1.0e-12
            ):
                errors.append(f"{family} source-manifest buildup sumTT differs")
            if is_zero:
                for key, expected in (
                    ("zero_count_garwood_two_sided95_upper", zero_count_upper),
                    ("transported_ground_rate_upper95_s-1", rate_upper95),
                    ("transported_ground_A15_upper95_Bq_conservative", a15_upper95),
                ):
                    observed = manifest.get(key)
                    if observed is None or not math.isclose(
                        float(observed), float(expected), rel_tol=2.0e-12, abs_tol=1.0e-18
                    ):
                        errors.append(f"{family} source-manifest zero upper differs for {key}")
                if manifest.get("zero_A15_upper_provenance") != zero_upper_provenance:
                    errors.append(f"{family} source-manifest zero upper provenance differs")
            manifest_closure = manifest.get("position_and_flux_closure")
            if has_explicit_dual:
                if not isinstance(manifest_closure, dict):
                    errors.append(f"{family} source manifest lacks dual-layer flux closure")
                else:
                    expected_manifest_values = {
                        "original_blocks": original_blocks,
                        "transport_blocks": transport_blocks,
                        "stride": position_stride,
                        "original_block_flux_Bq": original_flux,
                        "transport_block_flux_Bq": transport_flux,
                        "original_total_Bq": original_total,
                        "transport_total_Bq": transport_total,
                        "original_closure_Bq": original_closure,
                        "transport_closure_Bq": transport_closure,
                    }
                    for key, expected in expected_manifest_values.items():
                        observed = manifest_closure.get(key)
                        if observed is None or not math.isclose(
                            float(observed), float(expected), rel_tol=2.0e-12, abs_tol=1.0e-12
                        ):
                            errors.append(
                                f"{family} source-manifest mixture binding differs for {key}"
                            )
        except Exception as exc:
            errors.append(f"{family} source manifest is unreadable: {exc}")

    transport_source = Path(str(plan_row["source_path"]))
    if not transport_source.is_file() or transport_source.stat().st_size <= 0:
        errors.append(f"{family} stride-5 transport source is missing or empty: {transport_source}")
    if paths["transport_source"] != transport_source.resolve():
        errors.append(f"{family} delayed-source index transport-source binding differs")
    if int_field(row, "transport_seed", int(plan_row["seed"])) != int(plan_row["seed"]):
        errors.append(f"{family} delayed-source transport seed differs from the job plan")
    if int_field(row, "sampling_seed", int(plan_row["seed"])) != int(plan_row["seed"]):
        errors.append(f"{family} delayed-source sampling seed differs from the registered plan seed")
    if transport_source.is_file():
        source_directives = [
            line
            for line in transport_source.read_text(encoding="utf-8", errors="strict").splitlines()
            if line.startswith("DecayRun.Source ")
        ]
        if is_run and len(source_directives) != SELECTED_POSITION_BLOCKS:
            errors.append(f"{family} RUN source does not contain 10000 DecayRun.Source directives")
        if is_zero and source_directives:
            errors.append(f"{family} SKIP_ZERO_A15 source contains DecayRun.Source")

    return errors, {
        "family": family,
        "source_status": source_status,
        "execution_disposition": execution_disposition,
        "transport_eligible": is_run,
        "activity_Bq": activity,
        "buildup_sum_TT_s": buildup_sum_tt_s,
        "zero_count_garwood_two_sided95_upper": zero_count_upper if is_zero else None,
        "transported_ground_rate_upper95_s-1": rate_upper95 if is_zero else None,
        "transported_ground_A15_upper95_Bq_conservative": a15_upper95 if is_zero else None,
        "zero_A15_upper_provenance": zero_upper_provenance if is_zero else None,
        "upper_excludes_known_and_unresolved_holdout": holdout_separate,
        "known_holdout_activity_Bq": known_holdout_activity,
        "unknown_activity_state_count": unknown_holdout_states,
        "included_state_count": int_field(row, "included_state_count"),
        "holdout_state_count": int_field(row, "holdout_state_count"),
        "RPIP_points": int_field(row, "RPIP_points"),
        "original_position_blocks": original_blocks,
        "transport_position_blocks": transport_blocks,
        "position_stride": position_stride,
        "requested_decay_triggers": requested,
        "sampling_seed": int_field(row, "sampling_seed"),
        "flux_per_point_Bq": flux_per_point,
        "original_block_flux_Bq": original_flux,
        "transport_block_flux_Bq": transport_flux,
        "original_total_Bq": original_total,
        "transport_total_Bq": transport_total,
        "original_closure_Bq": original_closure,
        "transport_closure_Bq": transport_closure,
        "sampled_positions_path": str(paths["positions"]),
        "source_manifest_path": str(paths["manifest"]),
        "transport_source_path": str(transport_source.resolve()),
    }


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Validate stage-03 inputs without opening or hashing any rich SIM."""
    config_path = config_path.resolve()
    errors: list[str] = []
    missing_inputs: list[str] = []
    missing_receipts: list[str] = []
    validated_sources: dict[str, dict[str, Any]] = {}
    validated_receipts: list[dict[str, Any]] = []
    try:
        config = load_json(config_path)
    except Exception as exc:
        return {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "FAIL__SF3_DELAYED_CONFIG",
            "ready": False,
            "errors": [str(exc)],
            "missing_inputs": [],
            "missing_receipts": [],
            "sim_access_policy": "NO_SIM_OPEN_OR_HASH",
        }

    if not prompt.OLD_CATALOG_PARSER.is_file():
        errors.append(f"retained compact parser missing: {prompt.OLD_CATALOG_PARSER}")
    try:
        policy = prompt.explicit_veto_policy(config)
        if (
            len(policy["shield_volumes"]) != 3
            or len(policy["plastic_volumes"]) != 3
            or len(policy["active_veto_volumes"]) != 6
            or not policy["apply_plastic_veto"]
        ):
            errors.append("SF3 delayed catalog requires explicit 3-BGO + 3-plastic policy")
        if set(policy["shield_volumes"]) | set(policy["plastic_volumes"]) != set(
            policy["active_veto_volumes"]
        ):
            errors.append("SF3 delayed shield/plastic volumes do not partition active volumes")
        passive_w = set(prompt.passive_w_volumes(config))
        if passive_w != set(prompt.PASSIVE_W_VOLUMES):
            errors.append("SF3 delayed passive-W role list differs from the frozen contract")
        if passive_w & set(policy["active_veto_volumes"]):
            errors.append("SF3 delayed passive W overlaps the six active-veto volumes")
    except Exception as exc:
        policy = {}
        errors.append(f"invalid explicit SF3 veto policy: {exc}")

    try:
        plan = delayed_plan(config)
    except Exception as exc:
        plan = []
        errors.append(f"delayed job plan is unreadable: {exc}")
    if len(plan) != EXPECTED_JOBS:
        errors.append(f"delayed job count {len(plan)} != {EXPECTED_JOBS}")
    if {str(row["family"]) for row in plan} != set(FAMILY_ORDER):
        errors.append("delayed plan does not close the eight-family contract")
    if any(row.get("geometry") != "SF3" for row in plan):
        errors.append("delayed plan contains a non-SF3 geometry")
    if any(int(row["events"]) != EXPECTED_EVENTS_PER_JOB for row in plan):
        errors.append(f"every delayed family must have {EXPECTED_EVENTS_PER_JOB} triggers")
    if sum(int(row["events"]) for row in plan) != EXPECTED_TOTAL_EVENTS:
        errors.append("delayed trigger total differs from the frozen Plan-1 target")
    if len({int(row["seed"]) for row in plan}) != len(plan):
        errors.append("delayed transport seeds are not unique across families")

    index_path = activation_index_path(config)
    source_rows: dict[str, dict[str, str]] = {}
    if not index_path.is_file():
        missing_inputs.append(str(index_path))
    else:
        try:
            source_rows = source_index_by_family(read_source_index(index_path))
            missing_families = sorted(set(FAMILY_ORDER) - set(source_rows))
            extra_families = sorted(set(source_rows) - set(FAMILY_ORDER))
            if missing_families or extra_families or len(source_rows) != EXPECTED_JOBS:
                errors.append(
                    "SF3 activation source index family closure differs: "
                    f"missing={missing_families} extra={extra_families}"
                )
            plan_by_family = {str(row["family"]): row for row in plan}
            for family in FAMILY_ORDER:
                if family not in source_rows or family not in plan_by_family:
                    continue
                row_errors, normalized = validate_source_row(
                    family, source_rows[family], plan_by_family[family]
                )
                errors.extend(row_errors)
                if normalized is not None:
                    validated_sources[family] = normalized
        except Exception as exc:
            errors.append(f"activation delayed-source index is unreadable: {exc}")

    aggregate_selected: dict[str, dict[str, Any]] = {}
    aggregate_path = Path(config["transport"]["receipts"])
    if aggregate_path.is_file():
        try:
            aggregate = load_json(aggregate_path)
            aggregate_selected = {
                str(row["job_id"]): row for row in aggregate.get("selected_receipts", [])
            }
        except Exception as exc:
            errors.append(f"aggregate receipt ledger is unreadable: {exc}")

    if source_rows:
        transport_families = {
            family
            for family, source in validated_sources.items()
            if source["execution_disposition"] == RUN_DISPOSITION
        }
        zero_families = {
            family
            for family, source in validated_sources.items()
            if source["execution_disposition"] == ZERO_DISPOSITION
        }
    else:
        # Before stage02 exists the only safe readiness forecast is the full
        # registered eight-job plan.  Once the index exists, zero-A15 cells are
        # removed from receipt/SIM requirements by its audited disposition.
        transport_families = set(FAMILY_ORDER)
        zero_families = set()

    seen_sim: set[str] = set()
    for row in plan:
        family = str(row["family"])
        if family not in transport_families:
            continue
        job_id = str(row["job_id"])
        path = prompt.receipt_path(config, job_id)
        if not path.is_file():
            missing_receipts.append(job_id)
            continue
        try:
            receipt = load_json(path)
        except Exception as exc:
            errors.append(f"receipt unreadable {job_id}: {exc}")
            continue
        if receipt.get("status") != "PASS" or receipt.get("errors") not in ([], None):
            errors.append(f"canonical receipt is not a clean PASS: {job_id}")
        expected = {
            "profile_id": PROFILE_ID,
            "job_id": job_id,
            "stage": "delayed",
            "geometry": "SF3",
            "mode": "delayed",
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "source_path": row["source_path"],
            "setup_path": row["setup_path"],
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                errors.append(
                    f"{job_id} receipt {key}={receipt.get(key)!r}, expected {value!r}"
                )
        sim = Path(str(receipt.get("sim_path", "")))
        source = Path(str(receipt.get("source_path", "")))
        if not sim.is_file() or sim.stat().st_size != int(receipt.get("sim_bytes", -1)):
            errors.append(f"SIM path/size declaration failed: {job_id}")
        if not source.is_file():
            errors.append(f"transport source path is missing: {job_id}")
        indexed_source = source_rows.get(str(row["family"]), {})
        if indexed_source.get("source_sha256") and receipt.get("source_sha256") != indexed_source.get(
            "source_sha256"
        ):
            errors.append(f"activation-index/receipt source digest binding differs: {job_id}")
        isotope = receipt.get("isotope_dat", {})
        tt_s = isotope.get("TT_s")
        expected_delayed_normalization = (
            "NOT_APPLICABLE__DELAYED_USES_A15_PER_TRIGGER__SIGNAL_USES_FIXED_TRIALS"
        )
        if tt_s is not None or isotope.get("normalization") != expected_delayed_normalization:
            errors.append(f"delayed receipt must mark TT not applicable: {job_id}")
        if receipt.get("isotope_dat_path") is not None:
            errors.append(f"delayed receipt unexpectedly publishes an isotope DAT path: {job_id}")
        if receipt.get("log", {}).get("generated_events") != row["events"]:
            errors.append(f"generated-event receipt mismatch: {job_id}")
        if receipt.get("log", {}).get("graphics_terminal_marker") is not True:
            errors.append(f"terminal marker receipt mismatch: {job_id}")
        header = receipt.get("sim_header", {})
        try:
            header_geometry_matches = (
                Path(str(header.get("geometry"))).resolve()
                == Path(str(row["setup_path"])).resolve()
            )
        except Exception:
            header_geometry_matches = False
        if not header_geometry_matches or header.get("seed") != row["seed"]:
            errors.append(f"SIM header receipt mismatch: {job_id}")
        if receipt.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
            errors.append(f"SIM no-digest policy differs: {job_id}")
        resolved_sim = str(sim.resolve()) if sim.exists() else str(sim)
        if resolved_sim in seen_sim:
            errors.append(f"duplicate selected delayed SIM: {resolved_sim}")
        seen_sim.add(resolved_sim)
        aggregate_row = aggregate_selected.get(job_id)
        if aggregate_row is None:
            errors.append(f"canonical aggregate omits delayed PASS receipt: {job_id}")
        elif aggregate_row.get("sim_path") != str(sim):
            errors.append(f"aggregate delayed SIM binding differs: {job_id}")
        validated_receipts.append({
            "job_id": job_id,
            "family": row["family"],
            "events": int(row["events"]),
            "seed": int(row["seed"]),
            "receipt_path": str(path.resolve()),
            "sim_path": str(sim),
            "sim_bytes": receipt.get("sim_bytes"),
            "receipt_TT_s": tt_s,
            "receipt_normalization": isotope.get("normalization"),
        })

    ready = (
        not errors
        and not missing_inputs
        and not missing_receipts
        and len(validated_sources) == EXPECTED_JOBS
        and len(validated_receipts) == len(transport_families)
        and len(transport_families) + len(zero_families) == EXPECTED_JOBS
    )
    required_transport_triggers = len(transport_families) * EXPECTED_EVENTS_PER_JOB
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": (
            "READY__SF3_PLAN1_DELAYED_RECEIPTS_AND_ACTIVATION_COMPLETE"
            if ready
            else "NOT_READY__SF3_PLAN1_DELAYED_RECEIPTS_OR_ACTIVATION_INCOMPLETE"
        ),
        "ready": ready,
        "config": str(config_path),
        "activation_source_index": str(index_path),
        "registered_source_cells": EXPECTED_JOBS,
        "required_jobs": len(transport_families),
        "transport_jobs_required": len(transport_families),
        "zero_source_jobs_skipped": len(zero_families),
        "zero_source_families": sorted(zero_families, key=FAMILY_ORDER.index),
        "required_triggers_per_family": EXPECTED_EVENTS_PER_JOB,
        "required_triggers": required_transport_triggers,
        "validated_source_families": len(validated_sources),
        "validated_transport_source_families": sum(
            source["execution_disposition"] == RUN_DISPOSITION
            for source in validated_sources.values()
        ),
        "validated_zero_source_families": sum(
            source["execution_disposition"] == ZERO_DISPOSITION
            for source in validated_sources.values()
        ),
        "validated_receipt_jobs": len(validated_receipts),
        "validated_receipt_triggers": sum(row["events"] for row in validated_receipts),
        "missing_inputs": missing_inputs,
        "missing_receipts": missing_receipts,
        "errors": errors,
        "veto_policy_recorded_for_stage04": policy,
        "response_policy": "RESPONSE_NEUTRAL_STAGE03__DEFER_TO_STAGE04",
        "sim_access_policy": "STAT_ONLY__NO_SIM_OPEN_OR_HASH",
        "selected_receipts": validated_receipts,
        "zero_source_cells": [
            validated_sources[family]
            for family in FAMILY_ORDER
            if family in zero_families
        ],
    }


def selected_delayed_jobs(
    config_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prerequisites = check_prerequisites(config_path)
    if not prerequisites["ready"]:
        raise RuntimeError(json.dumps(prerequisites, indent=2, sort_keys=True))
    config = load_json(config_path)
    index_path = activation_index_path(config)
    rows = source_index_by_family(read_source_index(index_path))
    policy = prompt.explicit_veto_policy(config)
    jobs: list[dict[str, Any]] = []
    zero_sources: list[dict[str, Any]] = []
    for scan_index, plan_row in enumerate(delayed_plan(config)):
        family = str(plan_row["family"])
        source_errors, source = validate_source_row(family, rows[family], plan_row)
        if source_errors or source is None:
            raise RuntimeError(f"{family} activation source binding failed: {source_errors}")
        if source["execution_disposition"] == ZERO_DISPOSITION:
            zero_sources.append({
                **plan_row,
                **source,
                "scan_index": scan_index,
                "input_id": "sf3_plan1_zero_A15_no_transport_receipt",
                "batch_id": PROFILE_ID,
                "geometry": "SF3",
                "mode": "delayed",
                "actual_transport_triggers": 0,
                "event_weight_cps": 0.0,
                "equivalent_time_s": None,
                "activation_source_index_path": str(index_path.resolve()),
            })
            continue
        rpath = prompt.receipt_path(config, str(plan_row["job_id"]))
        receipt = load_json(rpath)
        activity = float(source["activity_Bq"])
        events = int(plan_row["events"])
        jobs.append({
            **plan_row,
            **source,
            "scan_index": scan_index,
            "input_id": "sf3_plan1_delayed_canonical_receipt",
            "batch_id": PROFILE_ID,
            "geometry": "SF3",
            "mode": "delayed",
            "sim_path": str(Path(receipt["sim_path"]).resolve()),
            "receipt_path": str(rpath.resolve()),
            "receipt_sim_bytes": int(receipt["sim_bytes"]),
            "expected_geometry": str(Path(str(plan_row["setup_path"])).resolve()),
            "shield_volumes": list(policy["shield_volumes"]),
            "plastic_volumes": list(policy["plastic_volumes"]),
            "passive_w_volumes": list(policy["passive_w_volumes"]),
            "veto_policy": policy,
            "event_weight_cps": activity / events,
            "equivalent_time_s": events / activity,
            "activation_source_index_path": str(index_path.resolve()),
        })
    return config, jobs, zero_sources, prerequisites


def position_locator(path: Path) -> dict[str, Any]:
    """Build the retained exact-position KD-tree for one activation cell."""
    import numpy as np
    from scipy.spatial import cKDTree

    unique: dict[tuple[float, float, float], tuple[str, int, float]] = {}
    full_mix: Counter[tuple[str, int]] = Counter()
    selected_mix: Counter[tuple[str, int]] = Counter()
    sample_indices: set[int] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sample_index", "volume", "ZA", "excitation_keV", "x_cm", "y_cm", "z_cm"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise RuntimeError(f"sampled-position schema differs in {path}")
        for row in reader:
            sample_index = int(row["sample_index"])
            if sample_index in sample_indices:
                raise RuntimeError(f"duplicate sample_index {sample_index} in {path}")
            sample_indices.add(sample_index)
            position = (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            value = (row["volume"], int(row["ZA"]), float(row["excitation_keV"]))
            full_mix[(value[0], value[1])] += 1
            if sample_index % POSITION_STRIDE:
                continue
            selected_mix[(value[0], value[1])] += 1
            old = unique.setdefault(position, value)
            if old != value:
                raise RuntimeError(f"ambiguous source position in {path}: {position}")
    if len(sample_indices) != FULL_POSITION_BLOCKS:
        raise RuntimeError(
            f"full sampled-position count {len(sample_indices)} != {FULL_POSITION_BLOCKS}: {path}"
        )
    if len(sample_indices) and sample_indices != set(range(FULL_POSITION_BLOCKS)):
        raise RuntimeError(f"sample_index support is not contiguous 0..49999: {path}")
    if sum(selected_mix.values()) != SELECTED_POSITION_BLOCKS:
        raise RuntimeError(
            f"stride-5 selected positions {sum(selected_mix.values())} != {SELECTED_POSITION_BLOCKS}"
        )
    coordinates = np.asarray(list(unique), dtype=np.float64)
    if len(coordinates) == 0:
        raise RuntimeError(f"no unique stride-5 source positions: {path}")
    return {
        "tree": cKDTree(coordinates),
        "metadata": list(unique.values()),
        "cache": {},
        "full_mix": full_mix,
        "selected_mix": selected_mix,
        "full_blocks": len(sample_indices),
        "selected_blocks": sum(selected_mix.values()),
        "unique_selected_positions": len(unique),
    }


def locate_source(
    locator: dict[str, Any],
    position: tuple[float, float, float],
) -> tuple[tuple[str, int, float], float]:
    """Map five-decimal IA INIT coordinates to six-decimal source support."""
    import numpy as np

    observed_key = tuple(f"{axis:.5f}" for axis in position)
    cached = locator["cache"].get(observed_key)
    if cached is not None:
        return cached
    count = len(locator["metadata"])
    k = min(8, count)
    nearest = second = math.inf
    chosen: tuple[str, int, float] | None = None
    while True:
        distances, neighbors = locator["tree"].query(
            np.asarray(position, dtype=np.float64), k=k, p=math.inf, workers=1
        )
        distance_values = np.atleast_1d(distances)
        neighbor_values = np.atleast_1d(neighbors)
        chosen = locator["metadata"][int(neighbor_values[0])]
        nearest = float(distance_values[0])
        for distance, neighbor in zip(distance_values[1:], neighbor_values[1:]):
            if locator["metadata"][int(neighbor)] != chosen:
                second = float(distance)
                break
        if math.isfinite(second) or k == count:
            break
        k = min(2 * k, count)
    accepted = (
        chosen is not None
        and nearest <= 1.0e-3
        and second - nearest >= 1.102e-5
        and second >= 2.0 * max(nearest, 1.0e-30)
    )
    if not accepted or chosen is None:
        raise RuntimeError(
            "source-position lineage is not uniquely resolved: "
            f"nearest={nearest:.9g} cm, second={second:.9g} cm"
        )
    result = (chosen, nearest)
    locator["cache"][observed_key] = result
    return result


def scan_job(job: dict[str, Any], cache_dir: str) -> dict[str, Any]:
    """Decompress one delayed rich SIM once and retain raw detector facts."""
    parser = prompt.old_parser()
    locator = position_locator(Path(job["sampled_positions_path"]))
    catalog = parser.empty_catalog()
    extras: dict[str, list[Any]] = {
        "input_id": [],
        "batch_id": [],
        "job_name": [],
        "seed": [],
        "plastic_total_keV": [],
        "has_pair_ia": [],
        "has_annihilation_ia": [],
        "w_total_keV": [],
        "first_interaction_volume": [],
        "first_interaction_resolution": [],
        "first_interaction_in_passive_w": [],
        "w_pair_ia_count": [],
        "w_annihilation_ia_count": [],
        "pair_ia_unresolved_count": [],
        "annihilation_ia_unresolved_count": [],
        "sim_initial_ZA": [],
        "source_parent_ZA": [],
        "source_volume": [],
        "source_volume_is_passive_w": [],
        "source_excitation_keV": [],
        "parent_match_distance_cm": [],
        "production_x_cm": [],
        "production_y_cm": [],
        "production_z_cm": [],
        "has_deca": [],
    }
    shield = set(job["shield_volumes"])
    plastic = set(job["plastic_volumes"])
    passive_w = set(job["passive_w_volumes"])
    if passive_w & (shield | plastic):
        raise RuntimeError(f"{job['job_id']}: passive W overlaps the active-veto volumes")
    current_id: int | None = None
    pixels: dict[str, dict[str, float | int]] = {}
    shield_total = 0.0
    plastic_total = 0.0
    w_total = 0.0
    sim_initial_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    has_deca = False
    has_pair = False
    has_annihilation = False
    interactions: list[dict[str, Any]] = []
    primary_hits: list[dict[str, Any]] = []
    all_meta_hits: list[dict[str, Any]] = []
    generated = 0
    total_init = 0
    deca_events = 0
    active_only = 0
    exact_print_matches = 0
    nearest_distance_max_cm = 0.0
    parent_za_mismatches = 0
    realized_mix: Counter[tuple[str, int]] = Counter()
    w_source_parent_mix: Counter[tuple[str, int]] = Counter()
    w_source_events = 0
    w_deposit_events = 0
    w_deposit_keV_sum = 0.0
    w_first_interaction_events = 0
    w_pair_events = 0
    w_annihilation_events = 0
    pair_ia_count = 0
    w_pair_ia_count = 0
    pair_ia_unresolved_count = 0
    annihilation_ia_count = 0
    w_annihilation_ia_count = 0
    annihilation_ia_unresolved_count = 0
    header_geometry = ""
    header_seed: int | None = None
    spectral: list[str] = []
    terminal_en = 0

    def flush() -> None:
        nonlocal current_id, pixels, shield_total, plastic_total, w_total
        nonlocal sim_initial_za, production_xyz, init_count
        nonlocal has_deca, has_pair, has_annihilation
        nonlocal interactions, primary_hits, all_meta_hits
        nonlocal active_only, deca_events, exact_print_matches
        nonlocal nearest_distance_max_cm, parent_za_mismatches
        nonlocal w_source_events, w_deposit_events, w_deposit_keV_sum
        nonlocal w_first_interaction_events, w_pair_events, w_annihilation_events
        nonlocal pair_ia_count, w_pair_ia_count, pair_ia_unresolved_count
        nonlocal annihilation_ia_count, w_annihilation_ia_count
        nonlocal annihilation_ia_unresolved_count
        if current_id is None:
            return
        if init_count != 1 or sim_initial_za is None or production_xyz is None:
            raise RuntimeError(f"{job['job_id']} event {current_id}: IA INIT count={init_count}")
        source, nearest_distance = locate_source(locator, production_xyz)
        nearest_distance_max_cm = max(nearest_distance_max_cm, nearest_distance)
        exact_print_matches += int(nearest_distance <= 5.51e-6)
        parent_za_mismatches += int(
            init_source_za_relation(sim_initial_za, source[1]) == TRANSPORT_DAUGHTER_ZA
        )
        realized_mix[(source[0], source[1])] += 1
        source_is_w = source[0] in passive_w
        w_source_events += int(source_is_w)
        if source_is_w:
            w_source_parent_mix[(source[0], source[1])] += 1
        w_diag = prompt.event_w_diagnostics(
            interactions, primary_hits, all_meta_hits, passive_w
        )
        w_deposit_events += int(w_total > 0.0)
        w_deposit_keV_sum += w_total
        w_first_interaction_events += int(w_diag["first_interaction_in_passive_w"])
        pair_ia_count += int(w_diag["pair_ia_count"])
        w_pair_ia_count += int(w_diag["w_pair_ia_count"])
        pair_ia_unresolved_count += int(w_diag["pair_ia_unresolved_count"])
        annihilation_ia_count += int(w_diag["annihilation_ia_count"])
        w_annihilation_ia_count += int(w_diag["w_annihilation_ia_count"])
        annihilation_ia_unresolved_count += int(w_diag["annihilation_ia_unresolved_count"])
        w_pair_events += int(int(w_diag["w_pair_ia_count"]) > 0)
        w_annihilation_events += int(int(w_diag["w_annihilation_ia_count"]) > 0)
        if has_deca:
            deca_events += 1
        if pixels:
            before = len(catalog["stream"])
            parser.append_event(
                catalog,
                "delayed",
                job["family"],
                job["sim_path"],
                current_id,
                job["event_weight_cps"],
                shield_total,
                pixels,
            )
            if len(catalog["stream"]) == before + 1:
                extras["input_id"].append(job["input_id"])
                extras["batch_id"].append(job["batch_id"])
                extras["job_name"].append(job["job_id"])
                extras["seed"].append(job["seed"])
                extras["plastic_total_keV"].append(plastic_total)
                extras["has_pair_ia"].append(has_pair)
                extras["has_annihilation_ia"].append(has_annihilation)
                extras["w_total_keV"].append(w_total)
                extras["first_interaction_volume"].append(w_diag["first_interaction_volume"])
                extras["first_interaction_resolution"].append(
                    w_diag["first_interaction_resolution"]
                )
                extras["first_interaction_in_passive_w"].append(
                    w_diag["first_interaction_in_passive_w"]
                )
                extras["w_pair_ia_count"].append(w_diag["w_pair_ia_count"])
                extras["w_annihilation_ia_count"].append(w_diag["w_annihilation_ia_count"])
                extras["pair_ia_unresolved_count"].append(
                    w_diag["pair_ia_unresolved_count"]
                )
                extras["annihilation_ia_unresolved_count"].append(
                    w_diag["annihilation_ia_unresolved_count"]
                )
                extras["sim_initial_ZA"].append(sim_initial_za)
                extras["source_parent_ZA"].append(source[1])
                extras["source_volume"].append(source[0])
                extras["source_volume_is_passive_w"].append(source_is_w)
                extras["source_excitation_keV"].append(source[2])
                extras["parent_match_distance_cm"].append(nearest_distance)
                extras["production_x_cm"].append(production_xyz[0])
                extras["production_y_cm"].append(production_xyz[1])
                extras["production_z_cm"].append(production_xyz[2])
                extras["has_deca"].append(has_deca)
        elif shield_total > 0.0 or plastic_total > 0.0:
            active_only += 1
        current_id = None
        pixels = {}
        shield_total = 0.0
        plastic_total = 0.0
        w_total = 0.0
        sim_initial_za = None
        production_xyz = None
        init_count = 0
        has_deca = False
        has_pair = False
        has_annihilation = False
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
            elif line.startswith("SpectralType "):
                spectral.append(line)
            if line == "EN":
                terminal_en += 1
                continue
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise RuntimeError(f"{job['job_id']}: ID before prior event boundary")
                current_id = int(match.group(1))
                generated += 1
                if current_id != generated:
                    raise RuntimeError(
                        f"{job['job_id']}: non-contiguous local ID {current_id} at {generated}"
                    )
                continue
            if line.startswith("IA INIT"):
                fields = [value.strip() for value in line.split(";")]
                if len(fields) < 16:
                    raise RuntimeError(f"malformed IA INIT: {job['job_id']}")
                init_count += 1
                total_init += 1
                production_xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
                sim_initial_za = int(fields[15])
                continue
            interaction = prompt.parse_ia(line)
            if interaction is not None:
                interactions.append(interaction)
                has_deca = has_deca or interaction["process"] == "DECA"
                has_pair = has_pair or interaction["process"] == "PAIR"
                has_annihilation = has_annihilation or interaction["process"] == "ANNI"
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parser.parse_cc_hit(line)
            if hit is None:
                continue
            volume, edep, x, y, z = hit
            meta = prompt.CC_META_RE.search(line)
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
                record = pixels.setdefault(
                    volume,
                    {
                        "e": 0.0,
                        "wx": 0.0,
                        "wy": 0.0,
                        "wz": 0.0,
                        "layer": int(pixel_match.group("layer")),
                    },
                )
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in shield:
                shield_total += edep
            elif volume in plastic:
                plastic_total += edep
            elif volume in passive_w:
                w_total += edep
    flush()

    events = int(job["events"])
    if generated != events or total_init != events:
        raise RuntimeError(f"{job['job_id']}: events={generated}, INIT={total_init}, expected={events}")
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve():
        raise RuntimeError(f"{job['job_id']}: geometry header differs: {header_geometry}")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: seed header differs: {header_seed}")
    if spectral != [EPSILON_SPECTRAL_HEADER]:
        raise RuntimeError(f"{job['job_id']}: epsilon spectral header differs: {spectral}")
    if terminal_en != 1:
        raise RuntimeError(f"{job['job_id']}: terminal EN count {terminal_en} != 1")
    if sum(realized_mix.values()) != events:
        raise RuntimeError(f"{job['job_id']}: realized source mixture does not close triggers")

    catalog.update(extras)
    catalog["n_generated_events_seen"] = generated
    catalog["generated_events"] = generated
    catalog["active_only_events"] = active_only
    catalog["active_only_rate_hz"] = active_only * float(job["event_weight_cps"])
    catalog["cell_metadata"] = {
        "profile_id": PROFILE_ID,
        "geometry": "SF3",
        "family": job["family"],
        "mode": "delayed",
        "jobs": 1,
        "generated_events": generated,
        "TT_s": float(job["equivalent_time_s"]),
        "event_weight_cps": float(job["event_weight_cps"]),
        "included_ground_activity_Bq": float(job["activity_Bq"]),
        "known_holdout_activity_Bq": float(job["known_holdout_activity_Bq"]),
        "unknown_activity_state_count": int(job["unknown_activity_state_count"]),
        "veto_policy": job["veto_policy"],
        "response_geometry_key": "sf3",
        "response_state": "raw_response_neutral__deferred_to_stage04",
        "authority_status": "SF3_PLAN1_DELAYED_CANONICAL_RECEIPT_AND_EXACT_POSITION_LINEAGE",
        "normalization": f"transported ground-state day15 activity / {events} triggers",
    }
    cache = Path(cache_dir) / f"job_{int(job['scan_index']):02d}.pkl"
    with cache.open("xb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return {
        "scan_index": int(job["scan_index"]),
        "path": str(cache),
        "geometry": "SF3",
        "family": job["family"],
        "events": generated,
        "deca_events": deca_events,
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": active_only,
        "pixel_hits": len(catalog["pix_e"]),
        "sim_bytes": int(job["receipt_sim_bytes"]),
        "exact_print_matches": exact_print_matches,
        "nearest_distance_max_cm": nearest_distance_max_cm,
        "parent_za_mismatches": parent_za_mismatches,
        "same_source_parent_za_events": generated - parent_za_mismatches,
        "init_za_lineage_policy": INIT_ZA_LINEAGE_POLICY,
        "m_sampling_lineage_authority": M_SAMPLING_LINEAGE_AUTHORITY,
        "terminal_en": terminal_en,
        "semantic_sim_scans": 1,
        "w_source_events": w_source_events,
        "w_deposit_events": w_deposit_events,
        "w_deposit_keV_sum": w_deposit_keV_sum,
        "w_first_interaction_events": w_first_interaction_events,
        "w_pair_events": w_pair_events,
        "w_annihilation_events": w_annihilation_events,
        "pair_ia_count": pair_ia_count,
        "w_pair_ia_count": w_pair_ia_count,
        "pair_ia_unresolved_count": pair_ia_unresolved_count,
        "annihilation_ia_count": annihilation_ia_count,
        "w_annihilation_ia_count": w_annihilation_ia_count,
        "annihilation_ia_unresolved_count": annihilation_ia_unresolved_count,
        "w_source_parent_mix": [
            [volume, za, count]
            for (volume, za), count in sorted(w_source_parent_mix.items())
        ],
        "full_blocks": locator["full_blocks"],
        "selected_blocks": locator["selected_blocks"],
        "unique_selected_positions": locator["unique_selected_positions"],
        "full_mix": [
            [volume, za, count]
            for (volume, za), count in sorted(locator["full_mix"].items())
        ],
        "selected_mix": [
            [volume, za, count]
            for (volume, za), count in sorted(locator["selected_mix"].items())
        ],
        "realized_mix": [
            [volume, za, count]
            for (volume, za), count in sorted(realized_mix.items())
        ],
    }


def distribution_tv(left: Counter[Any], right: Counter[Any]) -> float:
    left_total = math.fsum(left.values())
    right_total = math.fsum(right.values())
    if left_total <= 0.0 or right_total <= 0.0:
        raise RuntimeError("cannot compute total variation for an empty distribution")
    keys = set(left) | set(right)
    return 0.5 * math.fsum(
        abs(left.get(key, 0) / left_total - right.get(key, 0) / right_total)
        for key in keys
    )


def aggregate_mix(rows: list[list[Any]], field: str) -> Counter[Any]:
    if field not in ("volume", "ZA", "joint"):
        raise ValueError(field)
    result: Counter[Any] = Counter()
    for volume, za, count in rows:
        if field == "volume":
            key: Any = str(volume)
        elif field == "ZA":
            key = int(za)
        else:
            key = (str(volume), int(za))
        result[key] += int(count)
    return result


def build_report(summary: dict[str, Any]) -> str:
    scan = summary["semantic_scan"]
    return "\n".join([
        "# SF3 Plan-1 delayed raw catalog",
        "",
        f"Status: `{summary['status']}`",
        "",
        (
            f"Eight SF3 incident-family cells are registered; {summary['transport_jobs']} positive-A15 "
            f"cells contribute {summary['transport_triggers']:,} delayed triggers and "
            f"{summary['skipped_zero_A15_jobs']} zero-A15 cells are not launched. Each transported "
            "family rate uses its own day-15 ground-state "
            f"activity divided by {EXPECTED_EVENTS_PER_JOB:,} triggers."
        ),
        (
            f"The semantic pass retained {scan['TES_positive_events']:,} TES-positive events "
            f"and {scan['pixel_hits']:,} pixel hits while resolving lineage for all "
            f"{scan['events']:,} triggers."
        ),
        (
            f"IA INIT recorded a transport/daughter ZA different from the exact-position "
            f"source parent in {scan['INIT_transport_daughter_ZA_differs_from_source_parent_events']:,} "
            "events; this is a diagnostic, not a lineage failure. Both ZA values are retained."
        ),
        "",
        (
            "Each rich SIM was decompressed once and was not hashed. The source-mixture tables "
            "separate the original 50,000-position distribution, the stride-5 10,000-position "
            "transport support, and the realized 83,334-trigger mixture."
        ),
        (
            "Every skipped zero source has 0 blocks, no receipt or SIM, central delayed rate 0, "
            "and a finite two-sided-95% 3.688879/sumTT upper-rate with a conservative "
            "day-15 saturation-factor<=1 upper. Known and unresolved holdouts remain separate."
        ),
        "",
        (
            "This is a response-neutral stage: raw TES, explicit three-BGO/three-plastic deposits, "
            "passive-W deposit/interaction diagnostics, and activation-parent lineage only. "
            f"The scan records {summary['passive_w_diagnostics']['w_source_events']:,} triggers "
            "whose exact-position source volume is W and "
            f"{summary['passive_w_diagnostics']['w_first_interaction_events']:,} triggers whose "
            "first resolvable primary interaction is W. Keyed response, 0.3-keV pixel threshold, W2, "
            "veto, and Step05 are deferred to stage 04."
        ),
        "",
    ])


def self_test() -> dict[str, Any]:
    """Exercise RUN/zero index contracts without opening any SIM payload."""
    with tempfile.TemporaryDirectory(prefix="sf3_delayed_contract_selftest_") as raw:
        root = Path(raw)
        plan_template = {
            "family": "p",
            "events": EXPECTED_EVENTS_PER_JOB,
            "seed": 411155092,
        }

        def check_case(*, zero: bool) -> None:
            label = "zero" if zero else "run"
            source = root / f"{label}.source"
            positions = root / f"{label}_positions.csv"
            manifest_path = root / f"{label}_manifest.json"
            positions.write_text(
                "sample_index,volume,ZA,excitation_keV,x_cm,y_cm,z_cm\n",
                encoding="utf-8",
            )
            if zero:
                source_lines = [
                    "Version 1",
                    "Seed 411155092",
                    f"DecayRun.Triggers {EXPECTED_EVENTS_PER_JOB}",
                    "# ZERO_SOURCE_NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
                ]
                activity = 0.0
                original_blocks = 0
                transport_blocks = 0
                original_flux = 0.0
                transport_flux = 0.0
                disposition = ZERO_DISPOSITION
                source_status = "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY"
                sum_tt = 10.0
                count_upper: float | str = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER
                rate_upper: float | str = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / sum_tt
                a15_upper: float | str = rate_upper
                provenance = (
                    "two-sided 95% Garwood upper for zero transportable-ground RP: "
                    "3.6888794541139363/sumTT; conservative day-15 saturation factor <= 1; "
                    "known and unresolved holdout activity is reported separately"
                )
            else:
                source_lines = [
                    "Version 1",
                    "Seed 411155092",
                    f"DecayRun.Triggers {EXPECTED_EVENTS_PER_JOB}",
                    *(f"DecayRun.Source RP_{index:07d}" for index in range(SELECTED_POSITION_BLOCKS)),
                ]
                activity = 1.0
                original_blocks = FULL_POSITION_BLOCKS
                transport_blocks = SELECTED_POSITION_BLOCKS
                original_flux = activity / original_blocks
                transport_flux = activity / transport_blocks
                disposition = RUN_DISPOSITION
                source_status = "PASS__STRIDE5_M10000_DELAYED_SOURCE_READY"
                sum_tt = 10.0
                count_upper = ""
                rate_upper = ""
                a15_upper = ""
                provenance = ""
            source.write_text("\n".join(source_lines) + "\n", encoding="utf-8")
            closure = {
                "original_blocks": original_blocks,
                "transport_blocks": transport_blocks,
                "stride": POSITION_STRIDE,
                "original_block_flux_Bq": original_flux,
                "transport_block_flux_Bq": transport_flux,
                "original_total_Bq": activity,
                "transport_total_Bq": activity,
                "original_closure_Bq": 0.0,
                "transport_closure_Bq": 0.0,
            }
            manifest = {
                "geometry": "SF3",
                "family": "p",
                "execution_disposition": disposition,
                "included_ground_activity_Bq": activity,
                "source": str(source),
                "sampled_positions_table": str(positions),
                "triggers_requested": EXPECTED_EVENTS_PER_JOB,
                "transport_seed": 411155092,
                "sampling_seed": 411155092,
                "source_sha256": f"synthetic-{label}",
                "position_and_flux_closure": closure,
                "buildup_sum_TT_s": sum_tt,
                "zero_count_garwood_two_sided95_upper": count_upper or None,
                "transported_ground_rate_upper95_s-1": rate_upper or None,
                "transported_ground_A15_upper95_Bq_conservative": a15_upper or None,
                "zero_A15_upper_provenance": provenance or None,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            row = {
                "geometry": "SF3",
                "incident_family": "p",
                "source_status": source_status,
                "execution_disposition": disposition,
                "transported_ground_activity_Bq": str(activity),
                "buildup_sum_TT_s": str(sum_tt),
                "zero_count_garwood_two_sided95_upper": str(count_upper),
                "transported_ground_rate_upper95_s-1": str(rate_upper),
                "transported_ground_A15_upper95_Bq_conservative": str(a15_upper),
                "zero_A15_upper_provenance": provenance,
                "upper_excludes_known_and_unresolved_holdout": "True",
                "known_holdout_activity_Bq": "0.25",
                "unknown_activity_state_count": "1",
                "included_state_count": "0" if zero else "1",
                "holdout_state_count": "1",
                "RPIP_points": "0" if zero else "1",
                "pointsource_blocks": str(transport_blocks),
                "original_pointsource_blocks": str(original_blocks),
                "original_blocks": str(original_blocks),
                "transport_blocks": str(transport_blocks),
                "position_stride": str(POSITION_STRIDE),
                "requested_decay_triggers": str(EXPECTED_EVENTS_PER_JOB),
                "sampling_seed": "411155092",
                "transport_seed": "411155092",
                "flux_per_point_Bq": str(transport_flux) if not zero else "",
                "original_block_flux_Bq": str(original_flux) if not zero else "",
                "transport_block_flux_Bq": str(transport_flux) if not zero else "",
                "original_total_Bq": str(activity),
                "transport_total_Bq": str(activity),
                "original_closure_Bq": "0.0",
                "transport_closure_Bq": "0.0",
                "source_path": str(source),
                "source_sha256": f"synthetic-{label}",
                "sampled_positions_path": str(positions),
                "source_manifest_path": str(manifest_path),
            }
            plan = {**plan_template, "source_path": str(source)}
            errors, normalized = validate_source_row("p", row, plan)
            if errors or normalized is None:
                raise AssertionError(f"{label} source-row self-test failed: {errors}")
            if bool(normalized["transport_eligible"]) == zero:
                raise AssertionError(f"{label} transport eligibility self-test failed")

        check_case(zero=False)
        check_case(zero=True)
        if init_source_za_relation(26056, 25056) != TRANSPORT_DAUGHTER_ZA:
            raise AssertionError("transport/daughter INIT ZA difference was not retained")
        if init_source_za_relation(25056, 25056) != SAME_SOURCE_PARENT_ZA:
            raise AssertionError("same INIT/source-parent ZA relation was not retained")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_DELAYED_ANALYZER_SELF_TEST",
        "checks": [
            "RUN_83334_positive_A15_50k_to_10k_contract",
            "SKIP_ZERO_A15_zero_blocks_no_DecayRun_Source",
            "zero_two_sided95_3p688879_over_sumTT_finite_upper",
            "known_and_unresolved_holdout_reported_separately",
            "INIT_transport_or_daughter_ZA_is_diagnostic_not_parent_lineage_gate",
            "source_parent_ZA_remains_unique_exact_position_mapping_authority",
        ],
        "sim_opened": False,
    }


def run(config_path: Path, output: Path, workers: int) -> dict[str, Any]:
    config, jobs, zero_sources, prerequisites = selected_delayed_jobs(config_path)
    max_workers = int(config["transport"]["max_cpu_budget"])
    if workers < 1 or workers > max_workers:
        raise ValueError(f"workers must be in 1..{max_workers}")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite delayed output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    cache_dir = work / "job_cache"
    cache_dir.mkdir()
    started = time.monotonic()
    results: dict[int, dict[str, Any]] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scan_job, job, str(cache_dir)): job for job in jobs}
            for completed, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results[int(result["scan_index"])] = result
                print(json.dumps({
                    "event": "delayed_sim_scanned_once",
                    "completed": completed,
                    "total": len(jobs),
                    "job_id": futures[future]["job_id"],
                    "generated_events": result["events"],
                }, sort_keys=True), flush=True)

        expected_transport_jobs = len(jobs)
        expected_transport_events = sum(int(job["events"]) for job in jobs)
        if len(results) != expected_transport_jobs:
            raise RuntimeError("delayed semantic scan result count differs")
        if sum(row["semantic_sim_scans"] for row in results.values()) != expected_transport_jobs:
            raise RuntimeError("one-pass delayed SIM scan closure failed")
        if sum(row["events"] for row in results.values()) != expected_transport_events:
            raise RuntimeError("delayed semantic scan trigger closure failed")

        input_rows: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []
        mix_rows: list[dict[str, Any]] = []
        mix_tv_rows: list[dict[str, Any]] = []
        catalog_dir = work / "catalog" / "SF3"
        for job in jobs:
            result = results[int(job["scan_index"])]
            with Path(result["path"]).open("rb") as handle:
                catalog = pickle.load(handle)
            target = catalog_dir / f"{job['family']}.pkl"
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)

            input_rows.append({
                "geometry": "SF3",
                "family": job["family"],
                "source_status": "TRANSPORT_AND_RAW_SEMANTIC_SCAN_COMPLETE",
                "execution_disposition": RUN_DISPOSITION,
                "job_id": job["job_id"],
                "seed": job["seed"],
                "triggers": job["events"],
                "included_ground_activity_Bq": job["activity_Bq"],
                "transported_ground_rate_upper95_s-1": "",
                "transported_ground_A15_upper95_Bq_conservative": "",
                "zero_A15_upper_provenance": "",
                "event_weight_cps": job["event_weight_cps"],
                "equivalent_time_s": job["equivalent_time_s"],
                "subsample_rule": "sample_index modulo 5 equals 0; retained block flux multiplied by 5",
                "transport_source_path": job["transport_source_path"],
                "source_manifest_path": job["source_manifest_path"],
                "sampled_positions_path": job["sampled_positions_path"],
                "sim_path": job["sim_path"],
                "sim_bytes": job["receipt_sim_bytes"],
                "receipt_path": job["receipt_path"],
                "known_holdout_activity_Bq": job["known_holdout_activity_Bq"],
                "unknown_activity_state_count": job["unknown_activity_state_count"],
                "original_position_blocks": job["original_position_blocks"],
                "transport_position_blocks": job["transport_position_blocks"],
                "position_stride": job["position_stride"],
                "original_block_flux_Bq": job["original_block_flux_Bq"],
                "transport_block_flux_Bq": job["transport_block_flux_Bq"],
                "original_total_Bq": job["original_total_Bq"],
                "transport_total_Bq": job["transport_total_Bq"],
                "original_closure_Bq": job["original_closure_Bq"],
                "transport_closure_Bq": job["transport_closure_Bq"],
                "semantic_sim_scans": 1,
                "sim_hash_recomputed": False,
            })
            coverage.append({
                "geometry": "SF3",
                "family": job["family"],
                "source_status": "TRANSPORT_AND_SEMANTIC_SCAN_COMPLETE",
                "execution_disposition": RUN_DISPOSITION,
                "triggers": job["events"],
                "included_ground_activity_Bq": job["activity_Bq"],
                "central_delayed_rate_cps": "DEFERRED_TO_STAGE04_FROM_RAW_CATALOG",
                "transported_ground_rate_upper95_s-1": "",
                "transported_ground_A15_upper95_Bq_conservative": "",
                "finite_upper_limit_status": "NOT_APPLICABLE_TO_POSITIVE_A15_CELL",
                "event_weight_cps": job["event_weight_cps"],
                "equivalent_time_s": job["equivalent_time_s"],
                "TES_positive_events": result["tes_positive_events"],
                "active_only_events": result["active_only_events"],
                "pixel_hits": result["pixel_hits"],
                "w_source_events": result["w_source_events"],
                "w_deposit_events": result["w_deposit_events"],
                "w_deposit_keV_sum": result["w_deposit_keV_sum"],
                "w_first_interaction_events": result["w_first_interaction_events"],
                "w_pair_ia_count": result["w_pair_ia_count"],
                "w_annihilation_ia_count": result["w_annihilation_ia_count"],
                "events_with_IA_DECA": result["deca_events"],
                "events_without_IA_DECA": job["events"] - result["deca_events"],
                "lineage_matched_events": job["events"],
                "lineage_ambiguous_events": 0,
                "lineage_unmatched_events": 0,
                "INIT_parent_ZA_mismatches": result["parent_za_mismatches"],
                "INIT_transport_daughter_ZA_differs_from_source_parent_events": result[
                    "parent_za_mismatches"
                ],
                "INIT_ZA_lineage_policy": result["init_za_lineage_policy"],
                "M_sampling_lineage_authority": result["m_sampling_lineage_authority"],
                "exact_print_lineage_matches": result["exact_print_matches"],
                "parent_match_distance_max_cm": result["nearest_distance_max_cm"],
                "full_position_blocks": result["full_blocks"],
                "selected_position_blocks": result["selected_blocks"],
                "unique_selected_positions": result["unique_selected_positions"],
                "header_geometry_seed_epsilon_terminal_match": True,
                "response_applied": False,
                "catalog_path": prompt.display_path(output / "catalog" / "SF3" / f"{job['family']}.pkl"),
                "sim_path": job["sim_path"],
                "receipt_path": job["receipt_path"],
            })

            full = {(str(v), int(z)): int(c) for v, z, c in result["full_mix"]}
            selected = {(str(v), int(z)): int(c) for v, z, c in result["selected_mix"]}
            realized = {(str(v), int(z)): int(c) for v, z, c in result["realized_mix"]}
            if sum(full.values()) != FULL_POSITION_BLOCKS:
                raise RuntimeError(f"{job['family']}: full source-mix count differs")
            if sum(selected.values()) != SELECTED_POSITION_BLOCKS:
                raise RuntimeError(f"{job['family']}: selected source-mix count differs")
            if sum(realized.values()) != EXPECTED_EVENTS_PER_JOB:
                raise RuntimeError(f"{job['family']}: realized source-mix count differs")
            for volume, parent_za in sorted(set(full) | set(selected) | set(realized)):
                mix_rows.append({
                    "geometry": "SF3",
                    "family": job["family"],
                    "execution_disposition": RUN_DISPOSITION,
                    "source_volume": volume,
                    "source_volume_is_passive_w": volume in set(prompt.PASSIVE_W_VOLUMES),
                    "source_parent_ZA": parent_za,
                    "full_50000_blocks": full.get((volume, parent_za), 0),
                    "full_50000_fraction": full.get((volume, parent_za), 0) / FULL_POSITION_BLOCKS,
                    "selected_10000_blocks": selected.get((volume, parent_za), 0),
                    "selected_10000_fraction": selected.get((volume, parent_za), 0) / SELECTED_POSITION_BLOCKS,
                    "realized_83334_triggers": realized.get((volume, parent_za), 0),
                    "realized_83334_fraction": realized.get((volume, parent_za), 0) / EXPECTED_EVENTS_PER_JOB,
                })
            full_rows = result["full_mix"]
            selected_rows = result["selected_mix"]
            realized_rows = result["realized_mix"]
            mix_tv_rows.append({
                "geometry": "SF3",
                "family": job["family"],
                "execution_disposition": RUN_DISPOSITION,
                "full_to_selected_volume_tv": distribution_tv(
                    aggregate_mix(full_rows, "volume"), aggregate_mix(selected_rows, "volume")
                ),
                "full_to_selected_parent_ZA_tv": distribution_tv(
                    aggregate_mix(full_rows, "ZA"), aggregate_mix(selected_rows, "ZA")
                ),
                "full_to_selected_joint_tv": distribution_tv(
                    aggregate_mix(full_rows, "joint"), aggregate_mix(selected_rows, "joint")
                ),
                "selected_to_realized_joint_tv": distribution_tv(
                    aggregate_mix(selected_rows, "joint"), aggregate_mix(realized_rows, "joint")
                ),
                "full_to_realized_joint_tv": distribution_tv(
                    aggregate_mix(full_rows, "joint"), aggregate_mix(realized_rows, "joint")
                ),
            })

        for source in zero_sources:
            family = str(source["family"])
            input_rows.append({
                "geometry": "SF3",
                "family": family,
                "source_status": source["source_status"],
                "execution_disposition": ZERO_DISPOSITION,
                "job_id": source["job_id"],
                "seed": source["seed"],
                "triggers": 0,
                "included_ground_activity_Bq": 0.0,
                "transported_ground_rate_upper95_s-1": source[
                    "transported_ground_rate_upper95_s-1"
                ],
                "transported_ground_A15_upper95_Bq_conservative": source[
                    "transported_ground_A15_upper95_Bq_conservative"
                ],
                "zero_A15_upper_provenance": source["zero_A15_upper_provenance"],
                "event_weight_cps": 0.0,
                "equivalent_time_s": "",
                "subsample_rule": "NOT_APPLICABLE__ZERO_A15_NO_POSITION_MIXTURE",
                "transport_source_path": source["transport_source_path"],
                "source_manifest_path": source["source_manifest_path"],
                "sampled_positions_path": source["sampled_positions_path"],
                "sim_path": "",
                "sim_bytes": 0,
                "receipt_path": "",
                "known_holdout_activity_Bq": source["known_holdout_activity_Bq"],
                "unknown_activity_state_count": source["unknown_activity_state_count"],
                "original_position_blocks": 0,
                "transport_position_blocks": 0,
                "position_stride": source["position_stride"],
                "original_block_flux_Bq": 0.0,
                "transport_block_flux_Bq": 0.0,
                "original_total_Bq": 0.0,
                "transport_total_Bq": 0.0,
                "original_closure_Bq": 0.0,
                "transport_closure_Bq": 0.0,
                "semantic_sim_scans": 0,
                "sim_hash_recomputed": False,
            })
            coverage.append({
                "geometry": "SF3",
                "family": family,
                "source_status": source["source_status"],
                "execution_disposition": ZERO_DISPOSITION,
                "triggers": 0,
                "included_ground_activity_Bq": 0.0,
                "central_delayed_rate_cps": 0.0,
                "transported_ground_rate_upper95_s-1": source[
                    "transported_ground_rate_upper95_s-1"
                ],
                "transported_ground_A15_upper95_Bq_conservative": source[
                    "transported_ground_A15_upper95_Bq_conservative"
                ],
                "finite_upper_limit_status": (
                    "FINITE_TWO_SIDED95_GARWOOD_3P688879_OVER_BUILDUP_SUMTT__"
                    "CONSERVATIVE_A15_SATURATION_FACTOR_LE_1__HOLDOUT_SEPARATE"
                ),
                "event_weight_cps": 0.0,
                "equivalent_time_s": "",
                "TES_positive_events": 0,
                "active_only_events": 0,
                "pixel_hits": 0,
                "w_source_events": 0,
                "w_deposit_events": 0,
                "w_deposit_keV_sum": 0.0,
                "w_first_interaction_events": 0,
                "w_pair_ia_count": 0,
                "w_annihilation_ia_count": 0,
                "events_with_IA_DECA": 0,
                "events_without_IA_DECA": 0,
                "lineage_matched_events": 0,
                "lineage_ambiguous_events": 0,
                "lineage_unmatched_events": 0,
                "INIT_parent_ZA_mismatches": 0,
                "INIT_transport_daughter_ZA_differs_from_source_parent_events": 0,
                "INIT_ZA_lineage_policy": INIT_ZA_LINEAGE_POLICY,
                "M_sampling_lineage_authority": M_SAMPLING_LINEAGE_AUTHORITY,
                "exact_print_lineage_matches": 0,
                "parent_match_distance_max_cm": "",
                "full_position_blocks": 0,
                "selected_position_blocks": 0,
                "unique_selected_positions": 0,
                "header_geometry_seed_epsilon_terminal_match": "NOT_APPLICABLE__NO_SIM",
                "response_applied": False,
                "catalog_path": "",
                "sim_path": "",
                "receipt_path": "",
            })
            mix_rows.append({
                "geometry": "SF3",
                "family": family,
                "execution_disposition": ZERO_DISPOSITION,
                "source_volume": "__ZERO_A15_NO_TRANSPORT__",
                "source_volume_is_passive_w": False,
                "source_parent_ZA": "",
                "full_50000_blocks": 0,
                "full_50000_fraction": 0.0,
                "selected_10000_blocks": 0,
                "selected_10000_fraction": 0.0,
                "realized_83334_triggers": 0,
                "realized_83334_fraction": 0.0,
            })
            mix_tv_rows.append({
                "geometry": "SF3",
                "family": family,
                "execution_disposition": ZERO_DISPOSITION,
                "full_to_selected_volume_tv": "",
                "full_to_selected_parent_ZA_tv": "",
                "full_to_selected_joint_tv": "",
                "selected_to_realized_joint_tv": "",
                "full_to_realized_joint_tv": "",
            })

        w_rows = [{
            "geometry": "SF3",
            "family": job["family"],
            "execution_disposition": RUN_DISPOSITION,
            "job_id": job["job_id"],
            "generated_events": results[int(job["scan_index"])]["events"],
            "tes_positive_events": results[int(job["scan_index"])]["tes_positive_events"],
            "w_source_events": results[int(job["scan_index"])]["w_source_events"],
            "w_source_parent_mix_json": json.dumps(
                results[int(job["scan_index"])]["w_source_parent_mix"],
                separators=(",", ":"),
            ),
            "w_deposit_events": results[int(job["scan_index"])]["w_deposit_events"],
            "w_deposit_keV_sum": results[int(job["scan_index"])]["w_deposit_keV_sum"],
            "w_first_interaction_events": results[int(job["scan_index"])][
                "w_first_interaction_events"
            ],
            "pair_ia_count": results[int(job["scan_index"])]["pair_ia_count"],
            "w_pair_ia_count": results[int(job["scan_index"])]["w_pair_ia_count"],
            "pair_ia_unresolved_count": results[int(job["scan_index"])][
                "pair_ia_unresolved_count"
            ],
            "annihilation_ia_count": results[int(job["scan_index"])]["annihilation_ia_count"],
            "w_annihilation_ia_count": results[int(job["scan_index"])][
                "w_annihilation_ia_count"
            ],
            "annihilation_ia_unresolved_count": results[int(job["scan_index"])][
                "annihilation_ia_unresolved_count"
            ],
            "passive_w_volumes_json": json.dumps(
                list(prompt.PASSIVE_W_VOLUMES), separators=(",", ":")
            ),
            "veto_role": "PASSIVE_DIAGNOSTIC_ONLY__NOT_BGO_OR_PLASTIC_VETO",
        } for job in jobs]
        w_rows.extend({
            "geometry": "SF3",
            "family": source["family"],
            "execution_disposition": ZERO_DISPOSITION,
            "job_id": source["job_id"],
            "generated_events": 0,
            "tes_positive_events": 0,
            "w_source_events": 0,
            "w_source_parent_mix_json": "[]",
            "w_deposit_events": 0,
            "w_deposit_keV_sum": 0.0,
            "w_first_interaction_events": 0,
            "pair_ia_count": 0,
            "w_pair_ia_count": 0,
            "pair_ia_unresolved_count": 0,
            "annihilation_ia_count": 0,
            "w_annihilation_ia_count": 0,
            "annihilation_ia_unresolved_count": 0,
            "passive_w_volumes_json": json.dumps(
                list(prompt.PASSIVE_W_VOLUMES), separators=(",", ":")
            ),
            "veto_role": "PASSIVE_DIAGNOSTIC_ONLY__NO_SIM_FOR_ZERO_A15",
        } for source in zero_sources)
        w_rows.sort(key=lambda row: FAMILY_ORDER.index(str(row["family"])))
        w_summary = {
            key: (
                math.fsum(float(row[key]) for row in w_rows)
                if key == "w_deposit_keV_sum"
                else sum(int(row[key]) for row in w_rows)
            )
            for key in (
                "w_source_events", "w_deposit_events", "w_deposit_keV_sum",
                "w_first_interaction_events", "pair_ia_count", "w_pair_ia_count",
                "pair_ia_unresolved_count", "annihilation_ia_count",
                "w_annihilation_ia_count", "annihilation_ia_unresolved_count",
            )
        }
        w_summary.update({
            "passive_w_volumes": list(prompt.PASSIVE_W_VOLUMES),
            "role": "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES",
            "source_parent_method": "EXACT_POSITION_SOURCE_VOLUME_AND_PARENT_ZA_LINEAGE",
            "first_interaction_method": (
                "FIRST_PARENT_ID_1_IA_MATCHED_TO_PRIMARY_CC_HIT_BY_TIME_AND_PROCESS"
            ),
            "pair_annihilation_locality_method": (
                "IA_MATCHED_TO_RECORDED_CC_HIT_BY_TIME_AND_PROCESS__UNRESOLVED_REPORTED_SEPARATELY"
            ),
        })

        write_csv(work / "delayed_input_manifest.csv", input_rows)
        write_csv(work / "delayed_cell_coverage.csv", coverage)
        write_csv(work / "delayed_source_mix.csv", mix_rows)
        write_csv(work / "delayed_source_mix_tv.csv", mix_tv_rows)
        write_csv(work / "delayed_w_diagnostics.csv", w_rows)

        elapsed = time.monotonic() - started
        registered_sources = sorted(
            [*jobs, *zero_sources], key=lambda row: FAMILY_ORDER.index(str(row["family"]))
        )
        zero_source_cells = [{
            "family": source["family"],
            "execution_disposition": ZERO_DISPOSITION,
            "transported_ground_activity_Bq": 0.0,
            "central_delayed_rate_cps": 0.0,
            "buildup_sum_TT_s": source["buildup_sum_TT_s"],
            "zero_count_garwood_two_sided95_upper": source[
                "zero_count_garwood_two_sided95_upper"
            ],
            "transported_ground_rate_upper95_s-1": source[
                "transported_ground_rate_upper95_s-1"
            ],
            "transported_ground_A15_upper95_Bq_conservative": source[
                "transported_ground_A15_upper95_Bq_conservative"
            ],
            "upper_provenance": source["zero_A15_upper_provenance"],
            "known_holdout_activity_Bq_reported_separately": source[
                "known_holdout_activity_Bq"
            ],
            "unknown_holdout_state_count_reported_separately": source[
                "unknown_activity_state_count"
            ],
            "sim_opened": False,
            "receipt_required": False,
        } for source in zero_sources]
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
            "scope": "SF3-own day15 transported-ground exact-position delayed transport",
            "registered_source_cells": EXPECTED_JOBS,
            "transport_jobs": len(jobs),
            "skipped_zero_A15_jobs": len(zero_sources),
            "transport_triggers_per_family": EXPECTED_EVENTS_PER_JOB,
            "transport_triggers": expected_transport_events,
            "zero_source_cells": zero_source_cells,
            "activity_and_weights": [{
                "family": job["family"],
                "execution_disposition": job["execution_disposition"],
                "transported_ground_activity_Bq": job["activity_Bq"],
                "event_weight_cps": job["event_weight_cps"],
                "equivalent_time_s": job["equivalent_time_s"],
                "transported_ground_rate_upper95_s-1": job[
                    "transported_ground_rate_upper95_s-1"
                ],
                "transported_ground_A15_upper95_Bq_conservative": job[
                    "transported_ground_A15_upper95_Bq_conservative"
                ],
                "known_holdout_activity_Bq": job["known_holdout_activity_Bq"],
                "unknown_activity_state_count": job["unknown_activity_state_count"],
                "original_position_blocks": job["original_position_blocks"],
                "transport_position_blocks": job["transport_position_blocks"],
                "position_stride": job["position_stride"],
                "original_block_flux_Bq": job["original_block_flux_Bq"],
                "transport_block_flux_Bq": job["transport_block_flux_Bq"],
                "original_total_Bq": job["original_total_Bq"],
                "transport_total_Bq": job["transport_total_Bq"],
            } for job in registered_sources],
            "semantic_scan": {
                "workers": workers,
                "events": sum(row["events"] for row in results.values()),
                "events_with_IA_DECA": sum(row["deca_events"] for row in results.values()),
                "TES_positive_events": sum(row["tes_positive_events"] for row in results.values()),
                "active_only_events": sum(row["active_only_events"] for row in results.values()),
                "pixel_hits": sum(row["pixel_hits"] for row in results.values()),
                "lineage_matched_events": sum(row["events"] for row in results.values()),
                "lineage_ambiguous_events": 0,
                "lineage_unmatched_events": 0,
                "INIT_transport_daughter_ZA_differs_from_source_parent_events": sum(
                    row["parent_za_mismatches"] for row in results.values()
                ),
                "INIT_ZA_lineage_policy": INIT_ZA_LINEAGE_POLICY,
                "M_sampling_lineage_authority": M_SAMPLING_LINEAGE_AUTHORITY,
                "elapsed_s": elapsed,
            },
            "normalization": (
                f"selected events * family transported-ground day15 activity / "
                f"{EXPECTED_EVENTS_PER_JOB} triggers; delayed receipt TT is explicitly not applicable"
            ),
            "source_mixture_qa": {
                "per_family_full_position_blocks": FULL_POSITION_BLOCKS,
                "selection_rule": "sample_index modulo 5 equals 0",
                "per_family_selected_position_blocks": SELECTED_POSITION_BLOCKS,
                "selected_block_flux_multiplier": POSITION_STRIDE,
                "per_family_realized_triggers": EXPECTED_EVENTS_PER_JOB,
                "zero_source_policy": "0 blocks, 0 triggers, no SIM, central 0 plus finite upper",
                "total_variation_rows": mix_tv_rows,
                "uncertainty_boundary": "position-mixture uncertainty is separate from transport counting error",
            },
            "passive_w_diagnostics": w_summary,
            "raw_catalog": {
                "retained": [
                    "TES per-pixel energy and energy-weighted position",
                    "three-volume BGO total",
                    "three-volume plastic total",
                    "three-volume passive-W total with no veto role",
                    "first-primary-interaction W resolution and unresolved state",
                    "W-local PAIR/ANNI counts with unresolved counts kept separate",
                    "source-parent ZA/volume/excitation from exact-position lineage",
                    "source-volume-is-passive-W exact-position lineage flag",
                    "separate serialized transport/daughter INIT ZA and relation diagnostic",
                    "DECA/PAIR/ANNI indicators",
                ],
                "response_applied": False,
                "deferred_to_stage04": [
                    "keyed 0.42 keV FWHM response",
                    "0.3 keV measured pixel threshold",
                    "W2 510.58--511.42 keV",
                    "explicit six-volume veto",
                    "retained Step05",
                ],
                "veto_policy_recorded": prompt.explicit_veto_policy(config),
            },
            "known_exclusions": {
                "known_holdout_activity_Bq_sum": math.fsum(
                    float(job["known_holdout_activity_Bq"]) for job in registered_sources
                ),
                "unknown_activity_state_count_sum": sum(
                    int(job["unknown_activity_state_count"]) for job in registered_sources
                ),
                "state_policy": (
                    "non-ground and unresolved NUBASE states remain fail-closed holdouts; "
                    "they are not folded into zero-source central values or Garwood upper rates"
                ),
            },
            "sim_scan_policy": {
                "selected_sim_count": len(jobs),
                "semantic_scans": len(jobs),
                "zero_source_sim_count": 0,
                "zero_source_cells_not_opened": len(zero_sources),
                "scans_per_sim": 1,
                "scan_count_scope": "CURRENT_SUCCESSFUL_AUTHORITATIVE_EXECUTION_ONLY",
                "prior_nonpublished_recovery_audit": prompt.display_path(
                    PACKAGE_ROOT / "audit" / "delayed_parent_za_gate_recovery_20260815.json"
                ),
                "sim_hashes_recomputed": 0,
            },
            "receipt_prerequisite_status": prerequisites["status"],
            "authority_boundary": "DELAYED_RAW_CATALOG_ONLY__NOT_COMMON_RESPONSE_MISSION_F3_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        write_json(work / "summary.json", summary)
        (work / "REPORT.md").write_text(build_report(summary), encoding="utf-8")
        shutil.rmtree(cache_dir)
        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": summary["status"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_code": prompt.display_path(HERE),
            "reused_code": [
                str(prompt.OLD_CATALOG_PARSER),
                str(Path(
                    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/"
                    "engineering/particle_source_unit_repair_20260811/"
                    "m05_corrected_reanalysis_20260813/code/analyze_delayed_stage.py"
                )),
            ],
            "method": "retained exact-position infinity-norm cKDTree lineage with candidate-owned SF3 receipt binding",
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in files
            ],
            "hash_note": (
                "No rich SIM payload hash was computed; within this successful authoritative "
                "execution each selected SIM was semantically scanned once. The prior nonpublished "
                "parent-ZA gate failure is recorded separately in the recovery audit."
            ),
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(json.dumps({
            "status": summary["status"],
            "registered_source_cells": EXPECTED_JOBS,
            "jobs": len(jobs),
            "skipped_zero_A15_jobs": len(zero_sources),
            "triggers": expected_transport_events,
            "output": str(output),
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--check-prerequisites", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites(config_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    config = load_json(config_path)
    output = args.output or Path(config["outputs"]["stage_03"])
    workers = args.workers or int(config["transport"]["cpu_budget"])
    run(config_path, output.resolve(), workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
