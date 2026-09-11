#!/usr/bin/env python3
"""Publish a fail-closed, explicitly partial batch0004 prefix authority.

This program never launches Cosima.  It may adopt the already completed
alpha-instant shard 7 by revalidating both immutable geometry receipts and
then creating the missing write-once paired receipt.  It subsequently
publishes two authority pairs:

* an alpha-instant 7/9-shard partial-stage authority; and
* an umbrella authority for the contiguous batch0004 prefix through global
  ordinal 97 (five complete stages plus that partial alpha stage).

Neither output is the canonical 12-stage batch0004 final authority.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[4]
BATCH_CODE_DIR = (
    ROOT / "engineering" / "particle_source_unit_repair_20260811" / "code"
)
if str(BATCH_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(BATCH_CODE_DIR))

import run_mergeable_seven_family_1m_screening_batch0004 as batch  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_seven_family_1m_screening_batch0004 as validator  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


EXPECTED_SOURCE_CONTRACT_SHA256 = (
    "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
)
EXPECTED_GLOBAL_CONTRACT_SHA256 = (
    "c5069df77a264f8543b027be2af5304b160bf0ce22e7f24d7179605d980144d6"
)
EXPECTED_RUNNER_SHA256 = (
    "f53a9506979900e7b56e7e28df5f4216c8c32824de4ed038ae33e1b53be97163"
)
EXPECTED_VALIDATOR_SHA256 = (
    "33351eed53d1b52f2e566d58ece377a376d51347b7981756badaae70ea3fe109"
)

COMPLETE_STAGES = (
    "gamma_buildup",
    "n_instant",
    "n_buildup",
    "eplus_instant",
    "eplus_buildup",
)
ALPHA_STAGE = "alpha_instant"
ALPHA_PREFIX_STAGE_ORDINAL = 7
ALPHA_PREFIX_GLOBAL_START = 91
ALPHA_PREFIX_GLOBAL_END = 97
GLOBAL_PREFIX_START = 1
GLOBAL_PREFIX_END = 97

ALPHA_LEDGER_STATUS = (
    "PASS__BATCH0004_ALPHA_INSTANT_PARTIAL_PREFIX_SHARD0007_MERGE_ELIGIBLE"
)
OVERALL_LEDGER_STATUS = (
    "PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE"
)

OUTPUT_ROOT = (
    batch.RUN_ROOT
    / "seven_family_1m_screening_batch0004_partial_checkpoint_20260812"
)
STATE_SNAPSHOT = OUTPUT_ROOT / "execution_state_at_partial_publication.json"
ALPHA_VALIDATION = OUTPUT_ROOT / "alpha_instant_partial_shard0007_v1_validation.json"
ALPHA_LEDGER = OUTPUT_ROOT / "alpha_instant_partial_shard0007_v1_ledger.json"
OVERALL_VALIDATION = OUTPUT_ROOT / "batch0004_partial_through_ordinal0097_v1_validation.json"
OVERALL_LEDGER = OUTPUT_ROOT / "batch0004_partial_through_ordinal0097_v1_ledger.json"


class PublicationError(RuntimeError):
    """A fail-closed publication gate did not pass."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read JSON {smoke.rel(path)}: {exc}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def _require_file_hash(path: Path, expected: str, label: str) -> None:
    _require(path.is_file() and path.stat().st_size > 0, f"missing/empty {label}: {smoke.rel(path)}")
    observed = smoke.sha256(path)
    _require(observed == expected, f"{label} SHA-256 mismatch: {observed} != {expected}")


def _resolve_record_path(value: Any, label: str) -> Path:
    _require(isinstance(value, str) and value, f"missing path for {label}")
    path = common.resolve_repo_path(str(value))
    _require(common.is_within(path, ROOT), f"{label} escapes repository: {value}")
    return path


def _require_json_equal(path: Path, expected: Any, label: str) -> None:
    _require(path.is_file(), f"missing {label}: {smoke.rel(path)}")
    _require(_json(path) == expected, f"{label} differs from live expected payload")


def expected_alpha_ordinals() -> tuple[int, ...]:
    return tuple(range(ALPHA_PREFIX_GLOBAL_START, ALPHA_PREFIX_GLOBAL_END + 1))


def expected_global_prefix_ordinals() -> tuple[int, ...]:
    return tuple(range(GLOBAL_PREFIX_START, GLOBAL_PREFIX_END + 1))


def require_exact_contiguous_ordinals(observed: Iterable[int], expected: Iterable[int]) -> None:
    observed_tuple = tuple(sorted(int(value) for value in observed))
    expected_tuple = tuple(int(value) for value in expected)
    _require(observed_tuple == expected_tuple,
             f"ordinal coverage is not the exact required contiguous prefix: "
             f"observed={observed_tuple}, expected={expected_tuple}")


def _base_contract() -> dict[str, Any]:
    _require_file_hash(batch.SOURCE_CONTRACT, EXPECTED_SOURCE_CONTRACT_SHA256, "source contract")
    _require_file_hash(batch.GLOBAL_CONTRACT, EXPECTED_GLOBAL_CONTRACT_SHA256, "batch0004 contract")
    _require_file_hash(batch.THIS_FILE, EXPECTED_RUNNER_SHA256, "frozen batch0004 runner")
    _require_file_hash(validator.THIS_FILE, EXPECTED_VALIDATOR_SHA256, "frozen batch0004 validator")
    contract = _json(batch.GLOBAL_CONTRACT)
    gate = common.Gate()
    validator._light_contract_gate(contract, gate)
    _require(not gate.errors, "batch0004 light contract gate failed: " + " | ".join(gate.errors))
    _require(contract.get("batch_id") == batch.BATCH_ID, "batch0004 identity mismatch")
    _require(contract.get("campaign_version") == batch.CAMPAIGN_VERSION,
             "batch0004 campaign version mismatch")
    return contract


def _environment_from_contract(contract: dict[str, Any]) -> dict[str, str]:
    relevant = contract.get("transport", {}).get("environment", {}).get("relevant_variables")
    _require(isinstance(relevant, dict), "contract transport environment is missing")
    _require(all(isinstance(key, str) and isinstance(value, str) for key, value in relevant.items()),
             "contract transport environment is malformed")
    return dict(relevant)


def _state_snapshot_payload() -> dict[str, Any]:
    _require(batch.EXECUTION_STATE.is_file(), "batch0004 execution state is missing")
    state = _json(batch.EXECUTION_STATE)
    _require(state.get("status") == "PAUSED_REQUIRES_REVIEW",
             "first partial publication requires PAUSED_REQUIRES_REVIEW state")
    errors = state.get("errors")
    _require(isinstance(errors, list) and any("T+8h stop-launch gate" in str(item) for item in errors),
             "execution state does not record the frozen T+8 stop-launch condition")
    contract = _json(batch.GLOBAL_CONTRACT)
    try:
        batch._validate_execution_state(contract, state)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError,
            ValueError, RuntimeError) as exc:
        raise PublicationError(f"execution state validation failed: {exc}") from exc
    return {
        "schema_version": 1,
        "authority_class": "BATCH0004_PARTIAL_PUBLICATION_STATE_SNAPSHOT",
        "source_execution_state": smoke.rel(batch.EXECUTION_STATE),
        "source_execution_state_sha256": smoke.sha256(batch.EXECUTION_STATE),
        "state": state,
        "note": (
            "write-once snapshot; the mutable controller state may later change on an "
            "explicit resume without invalidating this already published prefix"
        ),
    }


def _ensure_state_snapshot(*, write: bool) -> dict[str, Any]:
    if STATE_SNAPSHOT.is_file():
        payload = _json(STATE_SNAPSHOT)
        _require(payload.get("authority_class") == "BATCH0004_PARTIAL_PUBLICATION_STATE_SNAPSHOT",
                 "state snapshot authority class mismatch")
        return payload
    _require(write, "partial-publication state snapshot is missing")
    payload = _state_snapshot_payload()
    batch.atomic_write_once_json(STATE_SNAPSHOT, payload)
    return payload


def _validate_geometry_shard(
    contract: dict[str, Any],
    geometry: str,
    ordinal: int,
    input_digest: str,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    receipt_path = batch.geometry_receipt_path(geometry, ordinal)
    _require(receipt_path.is_file(),
             f"missing geometry receipt: {geometry}/global ordinal {ordinal}")
    receipt = _json(receipt_path)
    _require(receipt.get("status") == "PASS__GEOMETRY_SHARD_MERGE_ELIGIBLE",
             f"geometry receipt is not exact PASS: {geometry}/ordinal{ordinal}")
    try:
        attempt = int(receipt["selected_attempt"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PublicationError(
            f"invalid selected attempt: {geometry}/ordinal{ordinal}: {exc}"
        ) from exc
    validation, errors = validator.validate_attempt(contract, geometry, ordinal, attempt)
    _require(validation.get("status") == "PASS" and not errors,
             f"live shard validation failed: {geometry}/ordinal{ordinal}: {' | '.join(errors)}")
    _require(validation.get("frozen_input_bundle_sha256") == input_digest,
             f"frozen input digest mismatch: {geometry}/ordinal{ordinal}")
    validation_path = validator._expected_attempt_paths(
        geometry, ordinal, attempt
    )["attempt_validation"]
    _require_json_equal(validation_path, validation, "immutable attempt validation")
    expected_receipt = validator._receipt_payload(validation, validation_path)
    _require(receipt == expected_receipt,
             f"immutable geometry receipt mismatch: {geometry}/ordinal{ordinal}")
    return validation, receipt, receipt_path


def _validate_pair_exact(ordinal: int) -> tuple[dict[str, Any], Path]:
    pair_path = batch.pair_receipt_path(ordinal)
    _require(pair_path.is_file(), f"missing pair receipt for global ordinal {ordinal}")
    pair = _json(pair_path)
    try:
        expected = batch._pair_receipt_payload(ordinal)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError,
            RuntimeError, ValueError) as exc:
        raise PublicationError(f"cannot build expected pair receipt for ordinal {ordinal}: {exc}") from exc
    _require(pair == expected, f"pair receipt payload mismatch for global ordinal {ordinal}")
    _require(pair.get("status") == "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
             f"pair receipt status mismatch for global ordinal {ordinal}")
    return pair, pair_path


def _adopt_alpha_shard7(contract: dict[str, Any], *, write: bool) -> None:
    ordinal = ALPHA_PREFIX_GLOBAL_END
    pair_path = batch.pair_receipt_path(ordinal)
    environment = _environment_from_contract(contract)
    input_digests: dict[str, str] = {}
    for geometry in batch.GEOMETRIES:
        try:
            digest = batch._verify_attempt_inputs(contract, geometry, ordinal, environment)
        except Exception as exc:
            raise PublicationError(
                f"cannot verify frozen input bundle for {geometry}/ordinal{ordinal}: {exc}"
            ) from exc
        input_digests[geometry] = digest
        _validate_geometry_shard(contract, geometry, ordinal, digest)
    expected_pair = batch._pair_receipt_payload(ordinal)
    if pair_path.exists():
        _require(_json(pair_path) == expected_pair,
                 "existing alpha shard7 pair receipt differs from exact expected payload")
        return
    _require(write, "alpha shard7 pair receipt is absent; read-only check cannot adopt it")
    # Recheck the inputs immediately before the write-once pair commit.
    for geometry in batch.GEOMETRIES:
        observed = batch._verify_attempt_inputs(contract, geometry, ordinal, environment)
        _require(observed == input_digests[geometry],
                 f"input bundle drifted while adopting {geometry}/ordinal{ordinal}")
    batch.atomic_write_once_json(pair_path, expected_pair)


def _rehash_job_artifacts(job: dict[str, Any], label: str) -> None:
    for path_key, hash_key in (
        ("job_source", "job_source_sha256"),
        ("sim", "sim_sha256"),
        ("isotope_dat", "isotope_dat_sha256"),
        ("log", "log_sha256"),
        ("geometry_receipt", "geometry_receipt_sha256"),
        ("pair_receipt", "pair_receipt_sha256"),
    ):
        path = _resolve_record_path(job.get(path_key), f"{label}/{path_key}")
        expected = job.get(hash_key)
        _require(isinstance(expected, str) and len(expected) == 64,
                 f"missing/malformed hash for {label}/{path_key}")
        _require_file_hash(path, expected, f"{label}/{path_key}")


def _validate_complete_checkpoint(stage: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _require(stage in COMPLETE_STAGES, f"stage is not in frozen complete prefix: {stage}")
    spec = batch.STAGE_BY_KEY[stage]
    report_path = batch.checkpoint_report_path(stage)
    ledger_path = batch.checkpoint_ledger_path(stage)
    _require(report_path.is_file() and ledger_path.is_file(),
             f"canonical checkpoint authority pair missing: {stage}")
    report = _json(report_path)
    ledger = _json(ledger_path)
    expected_status = (
        f"PASS__BATCH0004_{stage.upper()}_1M_SCREENING_MERGE_ELIGIBLE"
    )
    _require(report.get("status") == "PASS" and report.get("errors") == [],
             f"canonical checkpoint report is not clean PASS: {stage}")
    _require(ledger.get("status") == expected_status and ledger.get("errors") == [],
             f"canonical checkpoint ledger status mismatch: {stage}")
    for payload, label in ((report, "report"), (ledger, "ledger")):
        _require(payload.get("batch_id") == batch.BATCH_ID, f"{stage} {label} batch ID mismatch")
        _require(payload.get("campaign_version") == batch.CAMPAIGN_VERSION,
                 f"{stage} {label} campaign version mismatch")
        _require(payload.get("stage") == stage, f"{stage} {label} stage mismatch")
        _require(payload.get("global_contract_sha256") == EXPECTED_GLOBAL_CONTRACT_SHA256,
                 f"{stage} {label} global contract binding mismatch")
    _require(ledger.get("source_contract_manifest_sha256") == EXPECTED_SOURCE_CONTRACT_SHA256,
             f"{stage} source contract binding mismatch")
    _require(ledger.get("validation_report") == smoke.rel(report_path),
             f"{stage} validation report path mismatch")
    _require(ledger.get("validation_report_sha256") == smoke.sha256(report_path),
             f"{stage} validation report hash mismatch")
    _require(report.get("campaigns") == ledger.get("campaigns"),
             f"{stage} report/ledger campaigns differ")

    campaigns = report.get("campaigns")
    _require(isinstance(campaigns, list) and len(campaigns) == len(batch.GEOMETRIES),
             f"{stage} campaign count mismatch")
    seen_geometries: set[str] = set()
    seen_ordinals: set[int] = set()
    total_jobs = 0
    total_events = 0
    for campaign in campaigns:
        geometry = str(campaign.get("geometry"))
        seen_geometries.add(geometry)
        _require(geometry in batch.GEOMETRIES, f"{stage} unknown geometry {geometry}")
        _require(campaign.get("stage") == stage
                 and campaign.get("family") == spec["family"]
                 and campaign.get("mode") == spec["mode"],
                 f"{stage}/{geometry} campaign identity mismatch")
        _require(int(campaign.get("new_events_validated", -1)) == int(spec["new_events_per_geometry"]),
                 f"{stage}/{geometry} new event count mismatch")
        _require(int(campaign.get("validated_shards", -1)) == int(spec["paired_shards"]),
                 f"{stage}/{geometry} shard count mismatch")
        for control_key, hash_key in (
            ("campaign_contract", "campaign_contract_sha256"),
            ("normalization", "normalization_sha256"),
        ):
            control_path = _resolve_record_path(campaign.get(control_key),
                                                f"{stage}/{geometry}/{control_key}")
            _require_file_hash(control_path, str(campaign.get(hash_key)),
                               f"{stage}/{geometry}/{control_key}")
        jobs = campaign.get("jobs")
        _require(isinstance(jobs, list) and len(jobs) == int(spec["paired_shards"]),
                 f"{stage}/{geometry} job inventory mismatch")
        geometry_ordinals: set[int] = set()
        for job in jobs:
            ordinal = int(job.get("ordinal", -1))
            geometry_ordinals.add(ordinal)
            _require(job.get("stage") == stage and job.get("family") == spec["family"]
                     and job.get("mode") == spec["mode"],
                     f"{stage}/{geometry}/ordinal{ordinal} job identity mismatch")
            _require(int(job.get("events", -1)) == batch.shard_events(ordinal),
                     f"{stage}/{geometry}/ordinal{ordinal} event mismatch")
            _require(int(job.get("seed", -1)) == batch.shard_seed(ordinal),
                     f"{stage}/{geometry}/ordinal{ordinal} seed mismatch")
            _rehash_job_artifacts(job, f"{stage}/{geometry}/ordinal{ordinal}")
            receipt = _json(_resolve_record_path(job["geometry_receipt"], "geometry receipt"))
            _require(receipt.get("status") == "PASS__GEOMETRY_SHARD_MERGE_ELIGIBLE",
                     f"{stage}/{geometry}/ordinal{ordinal} receipt status mismatch")
            attempt_validation = _resolve_record_path(
                receipt.get("attempt_validation"), "attempt validation"
            )
            _require_file_hash(attempt_validation, str(receipt.get("attempt_validation_sha256")),
                               f"{stage}/{geometry}/ordinal{ordinal}/attempt_validation")
            signed_validation = _json(attempt_validation)
            _require(signed_validation.get("status") == "PASS"
                     and signed_validation.get("errors") == [],
                     f"{stage}/{geometry}/ordinal{ordinal} signed validation is not clean PASS")
            total_jobs += 1
            total_events += int(job["events"])
        expected_ordinals = set(range(int(spec["global_start_ordinal"]),
                                      int(spec["global_end_ordinal"]) + 1))
        _require(geometry_ordinals == expected_ordinals,
                 f"{stage}/{geometry} ordinal inventory mismatch")
        seen_ordinals.update(geometry_ordinals)
    _require(seen_geometries == set(batch.GEOMETRIES), f"{stage} geometry coverage mismatch")
    expected_ordinals = set(range(int(spec["global_start_ordinal"]),
                                  int(spec["global_end_ordinal"]) + 1))
    _require(seen_ordinals == expected_ordinals, f"{stage} global ordinal coverage mismatch")
    for ordinal in sorted(expected_ordinals):
        _validate_pair_exact(ordinal)
    _require(total_jobs == int(report.get("validated_job_count", -1)),
             f"{stage} validated job total mismatch")
    _require(total_events == int(report.get("validated_new_event_count", -1)),
             f"{stage} validated event total mismatch")
    _require(report.get("prior_credit_revalidation", {}).get("status") == "PASS",
             f"{stage} prior-credit revalidation is not PASS")
    authority = {
        "stage": stage,
        "completeness": "COMPLETE_STAGE_AT_FROZEN_SCREENING_TARGET",
        "report": smoke.rel(report_path),
        "report_sha256": smoke.sha256(report_path),
        "ledger": smoke.rel(ledger_path),
        "ledger_sha256": smoke.sha256(ledger_path),
        "status": ledger["status"],
    }
    return report, ledger, authority


def _validate_and_build_alpha_partial(
    contract: dict[str, Any], state_snapshot: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = batch.STAGE_BY_KEY[ALPHA_STAGE]
    _require(int(spec["global_start_ordinal"]) == ALPHA_PREFIX_GLOBAL_START,
             "alpha stage start ordinal changed")
    _require(int(spec["global_end_ordinal"]) == 99 and int(spec["paired_shards"]) == 9,
             "alpha stage schedule changed")
    _require(batch.shard_spec(ALPHA_PREFIX_GLOBAL_END)["stage_ordinal"]
             == ALPHA_PREFIX_STAGE_ORDINAL, "alpha prefix endpoint changed")
    environment = _environment_from_contract(contract)
    prior_ledgers = [_json(path) for path in (
        batch.BATCH0000_LEDGER, batch.BATCH0001_LEDGER, batch.BATCH0002_LEDGER
    )]
    prior_gate = common.Gate()
    prior_initial = validator._rehash_prior_credit(ALPHA_STAGE, prior_ledgers, prior_gate)
    _require(not prior_gate.errors and prior_initial.get("status") == "PASS",
             "alpha prior-credit revalidation failed: " + " | ".join(prior_gate.errors))

    campaigns: list[dict[str, Any]] = []
    validated_ordinals: set[int] = set()
    initial_digests: dict[str, str] = {}
    for geometry in batch.GEOMETRIES:
        try:
            digest = batch._verify_attempt_inputs(
                contract, geometry, ALPHA_PREFIX_GLOBAL_START, environment
            )
        except Exception as exc:
            raise PublicationError(f"alpha input verification failed for {geometry}: {exc}") from exc
        initial_digests[geometry] = digest
        jobs: list[dict[str, Any]] = []
        tt_values: list[float] = []
        for ordinal in expected_alpha_ordinals():
            validation, _, receipt_path = _validate_geometry_shard(
                contract, geometry, ordinal, digest
            )
            _, pair_path = _validate_pair_exact(ordinal)
            jobs.append(validator._ledger_job_payload(
                validation,
                ordinal,
                int(validation["attempt"]),
                receipt_path,
                pair_path,
            ))
            tt = validation.get("TT_s_from_isotope_dat")
            _require(isinstance(tt, (int, float)) and math.isfinite(float(tt)) and float(tt) > 0,
                     f"alpha TT is invalid: {geometry}/ordinal{ordinal}")
            tt_values.append(float(tt))
            validated_ordinals.add(ordinal)
        control_gate = common.Gate()
        campaign_contract, normalization = validator._validate_campaign_control_files(
            contract, geometry, ALPHA_STAGE, control_gate
        )
        _require(not control_gate.errors,
                 f"alpha campaign controls failed for {geometry}: "
                 + " | ".join(control_gate.errors))
        new_events = sum(int(job["events"]) for job in jobs)
        prior_events = int(spec["prior_events_per_geometry"])
        campaigns.append({
            "geometry": geometry,
            "mode": spec["mode"],
            "family": spec["family"],
            "stage": ALPHA_STAGE,
            "authority_completeness": "PARTIAL_CONTIGUOUS_STAGE_PREFIX_7_OF_9_SHARDS",
            "prior_events_credited": prior_events,
            "new_events_validated": new_events,
            "cumulative_events": prior_events + new_events,
            "full_stage_new_event_target": int(spec["new_events_per_geometry"]),
            "full_stage_cumulative_target": int(spec["target_events_per_geometry"]),
            "validated_shards": len(jobs),
            "full_stage_shard_target": int(spec["paired_shards"]),
            "TT_s_new_sum": math.fsum(tt_values),
            "flux_cm2_s": common.source_flux(
                batch.source_card_path(geometry, str(spec["family"]))
            ),
            "TT_authority": batch.TT_AUTHORITY,
            "campaign_contract": smoke.rel(campaign_contract),
            "campaign_contract_sha256": smoke.sha256(campaign_contract),
            "normalization": smoke.rel(normalization),
            "normalization_sha256": smoke.sha256(normalization),
            "jobs": jobs,
        })
        final_digest = batch._verify_attempt_inputs(
            contract, geometry, ALPHA_PREFIX_GLOBAL_START, environment
        )
        _require(final_digest == initial_digests[geometry],
                 f"alpha frozen inputs drifted during validation for {geometry}")

    require_exact_contiguous_ordinals(validated_ordinals, expected_alpha_ordinals())
    prior_final_gate = common.Gate()
    prior_final = validator._rehash_prior_credit(ALPHA_STAGE, prior_ledgers, prior_final_gate)
    _require(not prior_final_gate.errors and prior_final == prior_initial,
             "alpha prior credited artifacts drifted during partial validation")
    report = {
        "schema_version": 1,
        "status": "PASS",
        "authority_class": "BATCH0004_PARTIAL_STAGE_PREFIX",
        "canonical_full_stage_authority": False,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": ALPHA_STAGE,
        "family": spec["family"],
        "mode": spec["mode"],
        "prefix": {
            "global_start_ordinal": ALPHA_PREFIX_GLOBAL_START,
            "global_end_ordinal": ALPHA_PREFIX_GLOBAL_END,
            "stage_start_ordinal": 1,
            "stage_end_ordinal": ALPHA_PREFIX_STAGE_ORDINAL,
            "validated_pair_shards": ALPHA_PREFIX_STAGE_ORDINAL,
            "full_stage_pair_shards": int(spec["paired_shards"]),
            "missing_global_ordinals": [98, 99],
        },
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": EXPECTED_SOURCE_CONTRACT_SHA256,
        "execution_state_snapshot": smoke.rel(STATE_SNAPSHOT),
        "execution_state_snapshot_sha256": smoke.sha256(STATE_SNAPSHOT),
        "publisher": smoke.rel(THIS_FILE),
        "publisher_sha256": smoke.sha256(THIS_FILE),
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "validator_sha256": EXPECTED_VALIDATOR_SHA256,
        "campaigns": campaigns,
        "validated_new_event_count": sum(
            int(row["new_events_validated"]) for row in campaigns
        ),
        "validated_job_count": sum(len(row["jobs"]) for row in campaigns),
        "prior_credit_revalidation": prior_final,
        "downstream_boundary": {
            "usable": True,
            "allowed": (
                "alpha-instant per-geometry prompt/TES/veto diagnostics and TT-normalized "
                "merging for the listed seven paired shards only"
            ),
            "forbidden": (
                "claiming the 9-shard alpha target, seven-family completion, delayed-chain "
                "closure, sensitivity, or geometry promotion"
            ),
        },
        "checks": {
            "complete_pair_receipts": ALPHA_PREFIX_STAGE_ORDINAL,
            "validated_geometry_jobs": len(batch.GEOMETRIES) * ALPHA_PREFIX_STAGE_ORDINAL,
            "source_energy_contract": "CORRECTED_KEV_HASH_PINNED",
            "legacy_source_references": 0,
        },
        "errors": [],
    }
    ledger = {
        "schema_version": 1,
        "status": ALPHA_LEDGER_STATUS,
        "authority_class": report["authority_class"],
        "canonical_full_stage_authority": False,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": ALPHA_STAGE,
        "family": spec["family"],
        "mode": spec["mode"],
        "prefix": report["prefix"],
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": EXPECTED_SOURCE_CONTRACT_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "validation_report": smoke.rel(ALPHA_VALIDATION),
        "execution_state_snapshot": smoke.rel(STATE_SNAPSHOT),
        "execution_state_snapshot_sha256": smoke.sha256(STATE_SNAPSHOT),
        "publisher": smoke.rel(THIS_FILE),
        "publisher_sha256": smoke.sha256(THIS_FILE),
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_pairing_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": batch.TT_AUTHORITY,
        "prior_batches": contract.get("lineage", []),
        "prior_credit_equivalence": contract.get("prior_credit_equivalence"),
        "prior_credit_revalidation": prior_final,
        "transport": contract.get("transport"),
        "transport_core": contract.get("transport_core"),
        "geometry_bundles": contract.get("geometry_bundles"),
        "campaigns": campaigns,
        "downstream_boundary": report["downstream_boundary"],
        "errors": [],
    }
    return report, ledger


def _publish_or_check_pair(
    report_path: Path,
    ledger_path: Path,
    report: dict[str, Any],
    ledger: dict[str, Any],
    *,
    write: bool,
) -> None:
    if write:
        batch.atomic_write_once_json(report_path, report)
        expected_ledger = dict(ledger)
        expected_ledger["validation_report_sha256"] = smoke.sha256(report_path)
        batch.atomic_write_once_json(ledger_path, expected_ledger)
        return
    _require_json_equal(report_path, report, "canonical partial validation report")
    expected_ledger = dict(ledger)
    expected_ledger["validation_report_sha256"] = smoke.sha256(report_path)
    _require_json_equal(ledger_path, expected_ledger, "canonical partial ledger")


def _validate_alpha_authority_pair(
    expected_report: dict[str, Any], expected_ledger: dict[str, Any]
) -> dict[str, Any]:
    _require_json_equal(ALPHA_VALIDATION, expected_report, "alpha partial report")
    live_ledger = dict(expected_ledger)
    live_ledger["validation_report_sha256"] = smoke.sha256(ALPHA_VALIDATION)
    _require_json_equal(ALPHA_LEDGER, live_ledger, "alpha partial ledger")
    return {
        "stage": ALPHA_STAGE,
        "completeness": "PARTIAL_CONTIGUOUS_STAGE_PREFIX_7_OF_9_SHARDS",
        "report": smoke.rel(ALPHA_VALIDATION),
        "report_sha256": smoke.sha256(ALPHA_VALIDATION),
        "ledger": smoke.rel(ALPHA_LEDGER),
        "ledger_sha256": smoke.sha256(ALPHA_LEDGER),
        "status": live_ledger["status"],
    }


def _build_overall_partial(
    contract: dict[str, Any],
    state_snapshot: dict[str, Any],
    completed: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
    alpha_report: dict[str, Any],
    alpha_ledger: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    complete_authorities = [item[2] for item in completed]
    alpha_authority = _validate_alpha_authority_pair(alpha_report, alpha_ledger)
    all_campaigns: list[dict[str, Any]] = []
    for _, ledger, _ in completed:
        for campaign in ledger["campaigns"]:
            row = copy.deepcopy(campaign)
            row["authority_completeness"] = "COMPLETE_STAGE_AT_FROZEN_SCREENING_TARGET"
            all_campaigns.append(row)
    all_campaigns.extend(copy.deepcopy(alpha_ledger["campaigns"]))

    included_ordinals: set[int] = set()
    seen_geometry_seed: set[tuple[str, int]] = set()
    validated_jobs = 0
    validated_events = 0
    for campaign in all_campaigns:
        geometry = str(campaign.get("geometry"))
        for job in campaign.get("jobs", []):
            ordinal = int(job["ordinal"])
            seed = int(job["seed"])
            _require((geometry, seed) not in seen_geometry_seed,
                     f"duplicate geometry seed in partial umbrella: {geometry}/{seed}")
            seen_geometry_seed.add((geometry, seed))
            included_ordinals.add(ordinal)
            validated_jobs += 1
            validated_events += int(job["events"])
    require_exact_contiguous_ordinals(included_ordinals, expected_global_prefix_ordinals())
    _require(validated_jobs == 2 * len(expected_global_prefix_ordinals()),
             "partial umbrella job count is not two geometries per pair ordinal")
    for ordinal in expected_global_prefix_ordinals():
        _validate_pair_exact(ordinal)
    planned_events = int(contract["statistics"]["new_events_total"])
    planned_jobs = int(contract["statistics"]["transport_jobs_total"])
    _require(validated_events < planned_events and validated_jobs < planned_jobs,
             "partial umbrella unexpectedly equals or exceeds the full plan")
    missing_stages = []
    for spec in batch.STAGE_SPECS:
        stage = str(spec["key"])
        if stage in COMPLETE_STAGES:
            continue
        if stage == ALPHA_STAGE:
            missing_stages.append({
                "stage": stage,
                "missing_global_ordinals": [98, 99],
                "missing_pair_shards": 2,
                "missing_new_events_per_geometry": (
                    int(spec["new_events_per_geometry"])
                    - int(alpha_report["campaigns"][0]["new_events_validated"])
                ),
            })
        else:
            missing_stages.append({
                "stage": stage,
                "missing_global_ordinals": [
                    int(spec["global_start_ordinal"]),
                    int(spec["global_end_ordinal"]),
                ],
                "missing_pair_shards": int(spec["paired_shards"]),
                "missing_new_events_per_geometry": int(spec["new_events_per_geometry"]),
            })

    completeness = {
        "classification": "PARTIAL_CONTIGUOUS_BATCH_PREFIX",
        "canonical_batch0004_final_authority": False,
        "global_start_ordinal": GLOBAL_PREFIX_START,
        "global_end_ordinal": GLOBAL_PREFIX_END,
        "validated_pair_shards": len(expected_global_prefix_ordinals()),
        "planned_pair_shards": int(contract["statistics"]["paired_shards_total"]),
        "validated_transport_jobs": validated_jobs,
        "planned_transport_jobs": planned_jobs,
        "validated_new_events": validated_events,
        "planned_new_events": planned_events,
        "complete_stage_count": len(COMPLETE_STAGES),
        "planned_stage_count": len(batch.STAGE_ORDER),
        "partial_stage": ALPHA_STAGE,
        "remaining_global_ordinals": [98, int(contract["statistics"]["paired_shards_total"])],
        "missing_scope": missing_stages,
    }
    downstream = {
        "campaign_manifest_usable": True,
        "seven_family_total_eligible": False,
        "canonical_batch0004_final_eligible": False,
        "allowed": [
            "consume only the listed geometry+mode+family campaigns",
            "use sum(selected)/sum(TT) within one geometry+mode+family",
            "use sum(RP)/sum(TT) within one geometry+mode+family+volume+isotope-state",
            "produce explicitly partial TES/veto/activation diagnostics",
        ],
        "forbidden": [
            "treat absent families or modes as zero",
            "form a complete seven-family background total",
            "claim delayed-chain or detector-response closure",
            "claim sensitivity, mission rate, or geometry promotion",
            "substitute this ledger for the canonical batch0004 final ledger",
        ],
    }
    report = {
        "schema_version": 1,
        "status": "PASS",
        "authority_class": "BATCH0004_PARTIAL_CONTIGUOUS_PREFIX_CHECKPOINT",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": "partial_checkpoint_through_global_ordinal_0097",
        "completeness": completeness,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": EXPECTED_SOURCE_CONTRACT_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "execution_state_snapshot": smoke.rel(STATE_SNAPSHOT),
        "execution_state_snapshot_sha256": smoke.sha256(STATE_SNAPSHOT),
        "publisher": smoke.rel(THIS_FILE),
        "publisher_sha256": smoke.sha256(THIS_FILE),
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "validator_sha256": EXPECTED_VALIDATOR_SHA256,
        "complete_checkpoint_authorities": complete_authorities,
        "partial_stage_authorities": [alpha_authority],
        "campaigns": all_campaigns,
        "validated_new_event_count": validated_events,
        "validated_job_count": validated_jobs,
        "downstream_contract": downstream,
        "checks": {
            "contiguous_pair_ordinals": [GLOBAL_PREFIX_START, GLOBAL_PREFIX_END],
            "complete_pair_receipts": len(expected_global_prefix_ordinals()),
            "complete_checkpoint_authorities": len(complete_authorities),
            "partial_stage_authorities": 1,
            "source_energy_contract": "CORRECTED_KEV_HASH_PINNED",
            "legacy_source_references": 0,
        },
        "errors": [],
    }
    ledger = {
        "schema_version": 1,
        "status": OVERALL_LEDGER_STATUS,
        "authority_class": report["authority_class"],
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": report["stage"],
        "completeness": completeness,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": EXPECTED_SOURCE_CONTRACT_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "validation_report": smoke.rel(OVERALL_VALIDATION),
        "execution_state_snapshot": smoke.rel(STATE_SNAPSHOT),
        "execution_state_snapshot_sha256": smoke.sha256(STATE_SNAPSHOT),
        "publisher": smoke.rel(THIS_FILE),
        "publisher_sha256": smoke.sha256(THIS_FILE),
        "complete_checkpoint_authorities": complete_authorities,
        "partial_stage_authorities": [alpha_authority],
        "prior_batches": contract.get("lineage", []),
        "transport": contract.get("transport"),
        "transport_core": contract.get("transport_core"),
        "geometry_bundles": contract.get("geometry_bundles"),
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_pairing_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": batch.TT_AUTHORITY,
        "campaigns": all_campaigns,
        "downstream_contract": downstream,
        "errors": [],
    }
    return report, ledger


def run(*, write: bool) -> dict[str, Any]:
    contract = _base_contract()
    lock_handle = batch.CONTROLLER_LOCK.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PublicationError(
                "batch0004 controller lock is held; refusing concurrent partial publication"
            ) from exc
        _adopt_alpha_shard7(contract, write=write)
        state_snapshot = _ensure_state_snapshot(write=write)
        completed = [_validate_complete_checkpoint(stage) for stage in COMPLETE_STAGES]
        alpha_report, alpha_ledger = _validate_and_build_alpha_partial(
            contract, state_snapshot
        )
        _publish_or_check_pair(
            ALPHA_VALIDATION,
            ALPHA_LEDGER,
            alpha_report,
            alpha_ledger,
            write=write,
        )
        overall_report, overall_ledger = _build_overall_partial(
            contract,
            state_snapshot,
            completed,
            alpha_report,
            alpha_ledger,
        )
        _publish_or_check_pair(
            OVERALL_VALIDATION,
            OVERALL_LEDGER,
            overall_report,
            overall_ledger,
            write=write,
        )
    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()
    return {
        "status": "PASS",
        "mode": "PUBLISH" if write else "READ_ONLY_CHECK",
        "adopted_pair": smoke.rel(batch.pair_receipt_path(ALPHA_PREFIX_GLOBAL_END)),
        "alpha_partial_validation": smoke.rel(ALPHA_VALIDATION),
        "alpha_partial_ledger": smoke.rel(ALPHA_LEDGER),
        "overall_partial_validation": smoke.rel(OVERALL_VALIDATION),
        "overall_partial_ledger": smoke.rel(OVERALL_LEDGER),
        "overall_status": OVERALL_LEDGER_STATUS,
        "canonical_batch0004_final_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true", help="adopt shard7 and publish write-once partial authorities")
    mode.add_argument("--check", action="store_true", help="read-only exact revalidation of published authorities")
    args = parser.parse_args()
    try:
        result = run(write=bool(args.publish))
    except PublicationError as exc:
        print(json.dumps({
            "status": "FAIL",
            "mode": "PUBLISH" if args.publish else "READ_ONLY_CHECK",
            "authority_written": False,
            "error": str(exc),
        }, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
