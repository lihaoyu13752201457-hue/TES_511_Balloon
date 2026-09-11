#!/usr/bin/env python3
"""Publish a fail-closed merge ledger for a committed batch0003 pair prefix.

This program is deliberately separate from the running batch0003 controller.
It never reads controller state or lock files, never enumerates attempt
directories, and never starts Cosima.  An attempt becomes readable only after
an immutable PASS pair receipt and both receipt-bound geometry receipts have
been snapshotted and checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[4]
BATCH_CODE_DIR = (
    REPO_ROOT / "engineering/particle_source_unit_repair_20260811/code"
)
if str(BATCH_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(BATCH_CODE_DIR))

import run_mergeable_gamma_instant_batch0003 as batch  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_gamma_instant_batch0003 as stage_validator  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


SCHEMA_VERSION = 1
PUBLISHER_VERSION = "gamma_batch0003_committed_pair_prefix_v1_20260811"
MERGE_STATUS = "PARTIAL_PREFIX_MERGE_ELIGIBLE"
VALIDATION_STATUS = "PASS__PARTIAL_PREFIX_VALIDATED"
FAIL_STATUS = "FAIL_NOT_MERGE_ELIGIBLE"
PREFERRED_ORDINALS = (76, 116, 156)

EXPECTED_GLOBAL_CONTRACT_SHA256 = (
    "3447819ec2d69c371441576551188426ed4b25dd02177c7de6bebed3c1323583"
)
EXPECTED_BATCH_RUNNER_SHA256 = (
    "75d959ba0c13540dc305e29476d3a3ed1dd2aa424c81e8c2692e5f7c95a88b9f"
)
EXPECTED_BATCH_VALIDATOR_SHA256 = (
    "640da7e52f23c3413b154fd3f4c6c0a8f4c3741fafc4ab7cb66e69b0b22a25a7"
)
EXPECTED_STATIC_VALIDATION_SHA256 = (
    "d0d899dbe0ec787fd7863c2d37b0a6d5b73ce6ce6088f2ad829990a3c3aac4b6"
)

STATIC_VALIDATION = batch.PACKAGE / "data/static_validation.json"
OUTPUT_ROOT = (
    batch.RUN_ROOT / "gamma_instant_batch0003_prefix_checkpoints_20260811"
)

GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(-?\d+)\s*$", re.MULTILINE)


class PrefixValidationError(RuntimeError):
    """Raised before artifact traversal when no safe prefix can be selected."""


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    sha256: str
    size: int
    identity: tuple[int, int, int, int]
    payload: Any | None = None

    def record(self) -> dict[str, Any]:
        return {
            "path": smoke.rel(self.path),
            "sha256": self.sha256,
            "bytes": self.size,
        }


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot_file(path: Path, *, parse_json: bool = False) -> FileSnapshot:
    if path.is_symlink():
        raise PrefixValidationError(f"authority/artifact must not be a symlink: {path}")
    try:
        before = path.stat()
        if not path.is_file() or before.st_size <= 0:
            raise PrefixValidationError(f"missing/empty regular file: {path}")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise PrefixValidationError(f"cannot snapshot {path}: {exc}") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != after_id or len(raw) != after.st_size:
        raise PrefixValidationError(f"file changed while being snapshotted: {path}")
    payload: Any | None = None
    if parse_json:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PrefixValidationError(f"invalid JSON authority {path}: {exc}") from exc
    return FileSnapshot(
        path=path.resolve(),
        sha256=hashlib.sha256(raw).hexdigest(),
        size=after.st_size,
        identity=after_id,
        payload=payload,
    )


def _snapshot_hash(path: Path) -> FileSnapshot:
    """Stream-hash a potentially large artifact and verify file identity."""
    if path.is_symlink():
        raise PrefixValidationError(f"authority/artifact must not be a symlink: {path}")
    try:
        before = path.stat()
        if not path.is_file() or before.st_size <= 0:
            raise PrefixValidationError(f"missing/empty regular file: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
    except OSError as exc:
        raise PrefixValidationError(f"cannot hash {path}: {exc}") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != after_id:
        raise PrefixValidationError(f"file changed while being hashed: {path}")
    return FileSnapshot(
        path=path.resolve(),
        sha256=digest.hexdigest(),
        size=after.st_size,
        identity=after_id,
    )


def _require_unchanged(snapshot: FileSnapshot, gate: common.Gate, label: str) -> None:
    try:
        current = _snapshot_file(snapshot.path, parse_json=snapshot.payload is not None)
    except PrefixValidationError as exc:
        gate.problem(f"{label}: final stability check failed: {exc}", "artifact_stability")
        return
    gate.require(
        current.sha256 == snapshot.sha256
        and current.size == snapshot.size
        and current.identity == snapshot.identity,
        f"{label}: file changed across prefix validation: {smoke.rel(snapshot.path)}",
        "artifact_stability",
    )


def _pair_envelope_errors(payload: Any, ordinal: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"shard{ordinal:04d}: pair receipt is not a JSON object"]
    expected_scalars = {
        "schema_version": 1,
        "status": "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "ordinal": ordinal,
        "events_per_geometry": batch.shard_events(ordinal),
        "paired_seed": batch.shard_seed(ordinal),
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            errors.append(
                f"shard{ordinal:04d}: pair receipt {key}={payload.get(key)!r}, "
                f"expected {expected!r}"
            )
    bindings = payload.get("geometry_receipts")
    if not isinstance(bindings, dict) or set(bindings) != set(batch.GEOMETRIES):
        errors.append(
            f"shard{ordinal:04d}: pair geometry keys are not exactly "
            f"{sorted(batch.GEOMETRIES)}"
        )
        return errors
    for geometry in batch.GEOMETRIES:
        binding = bindings.get(geometry)
        expected_path = smoke.rel(batch.geometry_receipt_path(geometry, ordinal))
        if not isinstance(binding, dict):
            errors.append(f"shard{ordinal:04d}/{geometry}: invalid receipt binding")
            continue
        if binding.get("path") != expected_path:
            errors.append(
                f"shard{ordinal:04d}/{geometry}: pair receipt path mismatch"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("sha256", ""))):
            errors.append(
                f"shard{ordinal:04d}/{geometry}: pair receipt hash is malformed"
            )
        attempt = binding.get("selected_attempt")
        if type(attempt) is not int or not 1 <= attempt <= batch.MAX_ATTEMPTS:
            errors.append(
                f"shard{ordinal:04d}/{geometry}: invalid selected attempt {attempt!r}"
            )
    return errors


def discover_contiguous_pairs() -> list[FileSnapshot]:
    """Snapshot only pair receipts 1..first gap; never inspect attempts."""
    snapshots: list[FileSnapshot] = []
    for ordinal in range(1, batch.FINAL_SHARD_COUNT + 1):
        path = batch.pair_receipt_path(ordinal)
        if not path.exists():
            break
        snapshot = _snapshot_file(path, parse_json=True)
        problems = _pair_envelope_errors(snapshot.payload, ordinal)
        if problems:
            raise PrefixValidationError("; ".join(problems))
        snapshots.append(snapshot)
    return snapshots


def cumulative_events_per_geometry(prefix_ordinal: int) -> int:
    if not 1 <= prefix_ordinal <= batch.FINAL_SHARD_COUNT:
        raise ValueError(f"prefix ordinal outside 1..{batch.FINAL_SHARD_COUNT}")
    return batch.PRIOR_EVENTS_PER_GEOMETRY + sum(
        batch.shard_events(ordinal) for ordinal in range(1, prefix_ordinal + 1)
    )


def _select_prefix(requested: str, available: int) -> int:
    if requested == "auto":
        selected = available
    elif requested == "milestone":
        candidates = [value for value in PREFERRED_ORDINALS if value <= available]
        selected = max(candidates, default=0)
    else:
        try:
            selected = int(requested)
        except ValueError as exc:
            raise PrefixValidationError(
                "--prefix-ordinal must be auto, milestone, or an integer"
            ) from exc
        if not 1 <= selected <= batch.FINAL_SHARD_COUNT:
            raise PrefixValidationError(
                f"requested prefix ordinal must be within 1..{batch.FINAL_SHARD_COUNT}"
            )
    if selected <= 0:
        qualifier = "preferred milestone" if requested == "milestone" else "pair"
        raise PrefixValidationError(f"no complete contiguous {qualifier} is available")
    if selected > available:
        raise PrefixValidationError(
            f"requested prefix {selected} exceeds complete contiguous prefix {available}"
        )
    return selected


def _stable_expected_hash(
    path: Path, expected: str, gate: common.Gate, label: str
) -> FileSnapshot | None:
    try:
        snapshot = _snapshot_hash(path)
    except PrefixValidationError as exc:
        gate.problem(f"{label}: {exc}", "hashes")
        return None
    gate.require(
        snapshot.sha256 == expected,
        f"{label}: SHA-256 mismatch for {smoke.rel(path)}",
        "hashes",
    )
    return snapshot


def _load_required_json(
    path: Path, gate: common.Gate, label: str
) -> FileSnapshot | None:
    try:
        return _snapshot_file(path, parse_json=True)
    except PrefixValidationError as exc:
        gate.problem(f"{label}: {exc}", "authorities")
        return None


def _validate_prior_report(
    ledger: dict[str, Any], gate: common.Gate, label: str
) -> FileSnapshot | None:
    value = ledger.get("validation_report")
    path = common.resolve_repo_path(str(value or "__missing__"))
    snapshot = _load_required_json(path, gate, f"{label} validation report")
    if snapshot is None:
        return None
    report = snapshot.payload
    gate.require(report.get("status") == "PASS", f"{label}: prior report is not PASS", "lineage")
    gate.require(
        report.get("batch_id") == ledger.get("batch_id"),
        f"{label}: prior report/ledger batch ID mismatch",
        "lineage",
    )
    gate.require(
        report.get("campaigns") == ledger.get("campaigns"),
        f"{label}: prior report/ledger campaigns differ",
        "lineage",
    )
    expected_hash = ledger.get("validation_report_sha256")
    if expected_hash is not None:
        gate.require(
            snapshot.sha256 == expected_hash,
            f"{label}: prior validation-report hash mismatch",
            "lineage",
        )
    return snapshot


def _validate_transport_without_starting_cosima(
    contract: dict[str, Any], gate: common.Gate
) -> tuple[dict[str, str], dict[str, Any]]:
    """Rehash the frozen transport stack without executing Cosima or ldd."""
    transport = contract.get("transport", {})
    cosima = Path(str(transport.get("cosima", "__missing__"))).resolve()
    cosima_snapshot = _stable_expected_hash(
        cosima,
        str(transport.get("cosima_sha256", "")),
        gate,
        "Cosima executable (file-only revalidation)",
    )
    gate.require(os.access(cosima, os.X_OK), "Cosima executable bit is absent", "transport")

    libraries: list[dict[str, str]] = []
    for index, record in enumerate(transport.get("shared_libraries", [])):
        path = Path(str(record.get("path", "__missing__"))).resolve()
        snapshot = _stable_expected_hash(
            path,
            str(record.get("sha256", "")),
            gate,
            f"transport shared library {index}",
        )
        if snapshot is not None:
            libraries.append({"path": str(path), "sha256": snapshot.sha256})
    gate.require(bool(libraries), "transport shared-library inventory is empty", "transport")
    gate.require(
        libraries == transport.get("shared_libraries", []),
        "transport shared-library inventory/order differs from contract",
        "transport",
    )
    if libraries:
        gate.require(
            smoke.canonical_digest(libraries)
            == transport.get("shared_libraries_bundle_sha256"),
            "transport shared-library bundle digest mismatch",
            "transport",
        )

    descriptor = transport.get("environment", {})
    relevant = descriptor.get("relevant_variables", {})
    gate.require(isinstance(relevant, dict) and bool(relevant), "missing relevant transport environment", "transport")
    relevant_digest = hashlib.sha256(
        json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    gate.require(
        relevant_digest == descriptor.get("relevant_variables_sha256"),
        "transport relevant-variable digest mismatch",
        "transport",
    )
    setup_value = descriptor.get("setup_script")
    setup_snapshot: FileSnapshot | None = None
    if setup_value:
        setup_snapshot = _stable_expected_hash(
            common.resolve_repo_path(str(setup_value)),
            str(descriptor.get("setup_script_sha256", "")),
            gate,
            "MEGAlib setup script",
        )
    else:
        gate.require(
            descriptor.get("setup_script_sha256") is None,
            "setup script hash exists without setup path",
            "transport",
        )

    try:
        current_g4 = smoke.build_g4_data_fingerprint(
            {str(key): str(value) for key, value in relevant.items()},
            hash_contents=True,
        )
    except (OSError, RuntimeError, SystemExit, ValueError) as exc:
        gate.problem(f"G4 data fingerprint failed: {exc}", "transport")
        current_g4 = []
    gate.require(
        current_g4 == descriptor.get("g4_data_roots", []),
        "G4 data roots/content differ from frozen contract",
        "transport",
    )
    gate.require(
        platform.platform() == descriptor.get("platform"),
        "platform fingerprint differs from frozen contract",
        "transport",
    )
    gate.require(
        sys.version.splitlines()[0] == descriptor.get("python"),
        "Python fingerprint differs from frozen contract",
        "transport",
    )
    gate.require(
        batch._transport_core(transport) == contract.get("transport_core"),
        "contract transport-core self-binding mismatch",
        "transport",
    )

    environment = dict(os.environ)
    environment.update({str(key): str(value) for key, value in relevant.items()})
    record = {
        "mode": "file_hash_and_data_content_only__cosima_process_not_started",
        "cosima_process_started": False,
        "cosima": cosima_snapshot.record() if cosima_snapshot else None,
        "shared_libraries_count": len(libraries),
        "shared_libraries_bundle_sha256": (
            smoke.canonical_digest(libraries) if libraries else None
        ),
        "setup_script": setup_snapshot.record() if setup_snapshot else None,
        "relevant_variables_sha256": relevant_digest,
        "g4_data_roots": current_g4,
        "transport_core_sha256": batch._json_sha256(
            batch._transport_core(transport)
        ),
    }
    return environment, record


def _validate_static_inputs(
    gate: common.Gate,
) -> dict[str, Any] | None:
    contract_snapshot = _load_required_json(batch.GLOBAL_CONTRACT, gate, "global contract")
    source_snapshot = _load_required_json(batch.SOURCE_CONTRACT, gate, "source contract")
    static_snapshot = _load_required_json(STATIC_VALIDATION, gate, "static validation")
    if contract_snapshot is None or source_snapshot is None or static_snapshot is None:
        return None
    gate.require(
        contract_snapshot.sha256 == EXPECTED_GLOBAL_CONTRACT_SHA256,
        "global contract hash differs from frozen batch0003 contract",
        "contract",
    )
    gate.require(
        source_snapshot.sha256 == batch.SOURCE_CONTRACT_SHA256,
        "source contract hash mismatch",
        "source",
    )
    gate.require(
        static_snapshot.sha256 == EXPECTED_STATIC_VALIDATION_SHA256,
        "static validation hash mismatch",
        "source",
    )
    source = source_snapshot.payload
    static = static_snapshot.payload
    gate.require(source.get("status") == "CORRECTED_KEV_SOURCE_PACKAGE_GENERATED_NOT_TRANSPORT_VALIDATED", "unexpected source-contract status", "source")
    gate.require(source.get("source_model", {}).get("profile") == "unit_only_total_gamma", "source profile is not unit_only_total_gamma", "source")
    gate.require(source.get("policies", {}).get("additive_mono_511_allowed") is False, "source contract permits forbidden additive mono-511", "source")
    gate.require(static.get("status") == "PASS", "static source validation is not PASS", "source")
    gate.require(static.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256, "static validation/source hash mismatch", "source")
    gate.require(static.get("source_packages", {}).get("legacy_references") == 0, "static validation contains legacy references", "source")
    gate.require(static.get("source_packages", {}).get("spectrum_references") == 480, "static corrected-reference count mismatch", "source")

    contract = contract_snapshot.payload
    try:
        stage_validator._light_contract_gate(contract, gate)
    except (OSError, RuntimeError, SystemExit, TypeError, ValueError) as exc:
        gate.problem(f"batch0003 light contract gate raised: {exc}", "contract")
    gate.require(
        smoke.sha256(batch.THIS_FILE) == EXPECTED_BATCH_RUNNER_SHA256,
        "frozen batch0003 runner hash mismatch",
        "toolchain",
    )
    gate.require(
        smoke.sha256(stage_validator.THIS_FILE) == EXPECTED_BATCH_VALIDATOR_SHA256,
        "frozen batch0003 validator hash mismatch",
        "toolchain",
    )
    for name, record in contract.get("toolchain", {}).items():
        path = common.resolve_repo_path(str(record.get("path", "__missing__")))
        snapshot = _stable_expected_hash(
            path, str(record.get("sha256", "")), gate, f"toolchain/{name}"
        )
        if snapshot is None:
            continue

    ledger_specs = (
        (batch.BATCH0000_LEDGER, batch.BATCH0000_SHA256, batch.BATCH0000_ID, batch.BATCH0000_STATUS),
        (batch.BATCH0001_LEDGER, batch.BATCH0001_SHA256, batch.BATCH0001_ID, batch.BATCH0001_STATUS),
        (batch.BATCH0002_LEDGER, batch.BATCH0002_SHA256, batch.BATCH0002_ID, batch.BATCH0002_STATUS),
    )
    ledger_snapshots: list[FileSnapshot] = []
    report_snapshots: list[FileSnapshot] = []
    ledgers: list[dict[str, Any]] = []
    for path, expected_hash, expected_id, expected_status in ledger_specs:
        snapshot = _load_required_json(path, gate, expected_id)
        if snapshot is None:
            continue
        ledger_snapshots.append(snapshot)
        ledger = snapshot.payload
        ledgers.append(ledger)
        gate.require(snapshot.sha256 == expected_hash, f"prior ledger hash mismatch: {expected_id}", "lineage")
        gate.require(ledger.get("batch_id") == expected_id, f"prior ledger ID mismatch: {expected_id}", "lineage")
        gate.require(ledger.get("status") == expected_status, f"prior ledger status mismatch: {expected_id}", "lineage")
        gate.require(ledger.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256, f"prior ledger source binding mismatch: {expected_id}", "lineage")
        report_snapshot = _validate_prior_report(ledger, gate, expected_id)
        if report_snapshot is not None:
            report_snapshots.append(report_snapshot)
    if len(ledgers) != 3:
        return None

    for ledger, expected_id in zip(ledgers[:2], (batch.BATCH0000_ID, batch.BATCH0001_ID), strict=True):
        gate.require(
            batch._transport_core(ledger.get("transport", {}))
            == contract.get("transport_core"),
            f"prior transport core mismatch: {expected_id}",
            "lineage",
        )
        for geometry in batch.GEOMETRIES:
            gate.require(
                ledger.get("geometry_bundles", {}).get(geometry)
                == contract.get("geometry_bundles", {}).get(geometry),
                f"prior geometry bundle mismatch: {expected_id}/{geometry}",
                "lineage",
            )
    try:
        equivalence = batch.require_prior_credit_equivalence(
            ledgers[0], ledgers[1], contract.get("transport", {}),
            contract.get("geometry_bundles", {}),
        )
    except (KeyError, RuntimeError, SystemExit, TypeError, ValueError) as exc:
        gate.problem(f"prior 101k equivalence failed: {exc}", "lineage")
        equivalence = None
    gate.require(
        equivalence == contract.get("prior_credit_equivalence"),
        "prior 101k equivalence record mismatch",
        "lineage",
    )

    environment, transport_record = _validate_transport_without_starting_cosima(
        contract, gate
    )
    input_digests: dict[str, str] = {}
    geometry_records: dict[str, Any] = {}
    for geometry in batch.GEOMETRIES:
        try:
            bundle = smoke.build_geometry_bundle(geometry, environment)
            digest = batch._verify_attempt_inputs(contract, geometry, environment)
        except (KeyError, OSError, RuntimeError, SystemExit, TypeError, ValueError) as exc:
            gate.problem(f"{geometry}: frozen input validation failed: {exc}", "input_integrity")
            continue
        gate.require(
            bundle == contract.get("geometry_bundles", {}).get(geometry),
            f"current geometry bundle mismatch: {geometry}",
            "geometry",
        )
        try:
            source_files = common.source_contract_geometry_files(
                source, geometry, environment
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            gate.problem(f"{geometry}: source geometry resolution failed: {exc}", "geometry")
            source_files = []
        gate.require(
            source_files == bundle.get("files", []),
            f"source/runtime geometry files mismatch: {geometry}",
            "geometry",
        )
        input_digests[geometry] = digest
        geometry_records[geometry] = bundle
    return {
        "contract": contract,
        "source_contract": source,
        "ledgers": ledgers,
        "environment": environment,
        "transport_record": transport_record,
        "input_digests": input_digests,
        "geometry_records": geometry_records,
        "snapshots": [contract_snapshot, source_snapshot, static_snapshot, *ledger_snapshots, *report_snapshots],
    }


def _artifact_snapshots_from_job(
    job: dict[str, Any], gate: common.Gate, label: str
) -> dict[str, FileSnapshot]:
    snapshots: dict[str, FileSnapshot] = {}
    for key, hash_key in (
        ("job_source", "job_source_sha256"),
        ("sim", "sim_sha256"),
        ("isotope_dat", "isotope_dat_sha256"),
        ("log", "log_sha256"),
    ):
        path = common.resolve_repo_path(str(job.get(key, "__missing__")))
        try:
            snapshot = _snapshot_hash(path)
        except PrefixValidationError as exc:
            gate.problem(f"{label}/{key}: {exc}", "prior_credit")
            continue
        gate.require(
            snapshot.sha256 == job.get(hash_key),
            f"{label}/{key}: artifact hash mismatch",
            "prior_credit",
        )
        snapshots[key] = snapshot
    return snapshots


def _validate_prior_gamma_credit(
    ledgers: list[dict[str, Any]],
    source_contract: dict[str, Any],
    gate: common.Gate,
) -> dict[str, Any]:
    """Re-scan the credited 101k gamma events per geometry and their TT."""
    error_count = len(gate.errors)
    spectrum_hashes = stage_validator._spectrum_hashes(source_contract)
    gate.require(len(spectrum_hashes) == 160, "prior-credit spectrum inventory mismatch", "prior_credit")
    expected_per_ledger = (1_000, 100_000)
    credited = {geometry: 0 for geometry in batch.GEOMETRIES}
    rows: list[dict[str, Any]] = []
    seeds_by_ledger: dict[str, dict[str, list[int]]] = {}
    for ledger, expected_per_geometry in zip(ledgers[:2], expected_per_ledger, strict=True):
        ledger_id = str(ledger.get("batch_id"))
        seeds_by_ledger[ledger_id] = {}
        for geometry in batch.GEOMETRIES:
            matches = [
                campaign for campaign in ledger.get("campaigns", [])
                if campaign.get("geometry") == geometry
                and campaign.get("mode") == batch.MODE
            ]
            if len(matches) != 1:
                gate.problem(f"{ledger_id}/{geometry}: instant campaign ambiguity", "prior_credit")
                continue
            campaign = matches[0]
            jobs = [job for job in campaign.get("jobs", []) if job.get("family") == batch.FAMILY]
            events_sum = sum(int(job.get("events", 0)) for job in jobs)
            gate.require(
                events_sum == expected_per_geometry,
                f"{ledger_id}/{geometry}: credited gamma count={events_sum}, expected {expected_per_geometry}",
                "prior_credit",
            )
            credited[geometry] += events_sum
            seeds_by_ledger[ledger_id][geometry] = [int(job.get("seed", -1)) for job in jobs]
            outdir = common.resolve_repo_path(str(campaign.get("outdir", "__missing__")))
            base_source = batch.source_card_path(geometry)
            migration = json.loads(
                batch.source_manifest_path(geometry).read_text(encoding="utf-8")
            )
            expected_geometry = common.resolve_repo_path(migration["geometry_setup"])
            flux = common.source_flux(base_source)
            for job in jobs:
                label = f"{ledger_id}/{geometry}/{job.get('job_name')}"
                expected_events = int(job.get("events", -1))
                expected_seed = int(job.get("seed", -1))
                snapshots = _artifact_snapshots_from_job(job, gate, label)
                required = {"job_source", "sim", "isotope_dat", "log"}
                if set(snapshots) != required:
                    continue
                supports, corrected, legacy = common.validate_source_card(
                    gate,
                    base_source,
                    snapshots["job_source"].path,
                    batch.FAMILY,
                    batch.MODE,
                    str(job.get("job_name")),
                    expected_events,
                    expected_seed,
                    outdir,
                    spectrum_hashes,
                )
                gate.require(
                    corrected == 20 and legacy == 0,
                    f"{label}: corrected/legacy source reference mismatch",
                    "prior_credit",
                )
                if set(supports) == set(range(20)):
                    scan = stage_validator._scan_sim_exact(
                        snapshots["sim"].path,
                        expected_events,
                        expected_seed,
                        expected_geometry,
                        supports,
                    )
                else:
                    gate.problem(
                        f"{label}: incomplete corrected spectrum support prevents SIM scan",
                        "prior_credit",
                    )
                    scan = {
                        "events": 0,
                        "se_records": 0,
                        "id_records": 0,
                        "ia_init_records": 0,
                        "energy_min_keV": None,
                        "energy_max_keV": None,
                        "bad_energy_records": 0,
                        "bad_particle_records": 0,
                        "bad_direction_records": 0,
                        "geometry_header": None,
                        "seed_header": None,
                        "gzip_eof_read": False,
                        "problems": ["incomplete corrected spectrum support"],
                    }
                for problem in scan.get("problems", []):
                    gate.problem(f"{label}: prior SIM {problem}", "prior_credit")
                signed_scan = job.get("ia_init", {})
                for key, expected in signed_scan.items():
                    gate.require(
                        scan.get(key) == expected,
                        f"{label}: prior signed IA summary mismatch for {key}",
                        "prior_credit",
                    )
                log_text = snapshots["log"].path.read_text(
                    encoding="utf-8", errors="replace"
                )
                generated = GENERATED_RE.findall(log_text)
                observations = OBSERVATION_RE.findall(log_text)
                returns = RETURN_RE.findall(log_text)
                gate.require(
                    len(generated) == 1 and int(generated[0]) == expected_events,
                    f"{label}: prior generated event count mismatch",
                    "prior_credit",
                )
                gate.require(
                    len(returns) == 1 and int(returns[0]) == 0,
                    f"{label}: prior return code is not exactly zero",
                    "prior_credit",
                )
                log_tt = (
                    common.parse_float(observations[0])
                    if len(observations) == 1
                    else None
                )
                gate.require(
                    log_tt is not None and math.isfinite(log_tt) and log_tt > 0,
                    f"{label}: prior log TT is missing/invalid/duplicated",
                    "prior_credit",
                )
                isotope = common.parse_isotope_dat(snapshots["isotope_dat"].path)
                for problem in isotope.get("problems", []):
                    gate.problem(f"{label}: prior isotope DAT {problem}", "prior_credit")
                dat_tt = isotope.get("TT_s")
                gate.require(
                    isinstance(dat_tt, (int, float))
                    and math.isfinite(float(dat_tt))
                    and float(dat_tt) > 0,
                    f"{label}: prior DAT TT is invalid",
                    "prior_credit",
                )
                if log_tt is not None and isinstance(dat_tt, (int, float)):
                    gate.require(
                        math.isclose(float(dat_tt), log_tt, rel_tol=2e-3, abs_tol=2e-6),
                        f"{label}: prior DAT/log TT mismatch",
                        "prior_credit",
                    )
                gate.require(
                    isotope == job.get("isotope_store"),
                    f"{label}: prior isotope-store summary mismatch",
                    "prior_credit",
                )
                for key, observed in (
                    ("TT_s_from_log", log_tt),
                    ("TT_s_from_isotope_dat", dat_tt),
                    ("flux_cm2_s", flux),
                ):
                    signed = job.get(key)
                    gate.require(
                        isinstance(signed, (int, float))
                        and isinstance(observed, (int, float))
                        and math.isclose(float(signed), float(observed), rel_tol=0.0, abs_tol=1e-12),
                        f"{label}: prior {key} mismatch",
                        "prior_credit",
                    )
                expected_tt = expected_events / (
                    flux * math.pi * batch.FARFIELD_RADIUS_CM**2
                )
                gate.require(
                    math.isclose(
                        float(job.get("TT_s_expected_mean_from_events_flux_area", math.nan)),
                        expected_tt,
                        rel_tol=1e-14,
                        abs_tol=1e-14,
                    ),
                    f"{label}: prior expected-TT calculation mismatch",
                    "prior_credit",
                )
                post = _artifact_snapshots_from_job(job, gate, label + "/post")
                gate.require(
                    {
                        key: (value.sha256, value.size, value.identity)
                        for key, value in snapshots.items()
                    }
                    == {
                        key: (value.sha256, value.size, value.identity)
                        for key, value in post.items()
                    },
                    f"{label}: prior artifacts changed during revalidation",
                    "prior_credit",
                )
                rows.append({
                    "batch_id": ledger_id,
                    "geometry": geometry,
                    "job_name": job.get("job_name"),
                    "events": expected_events,
                    "seed": expected_seed,
                    "TT_s_from_log": log_tt,
                    "TT_s_from_isotope_dat": dat_tt,
                    "corrected_source_references": corrected,
                    "legacy_source_references": legacy,
                    "artifacts": {key: value.record() for key, value in snapshots.items()},
                    "sim_scan": scan,
                })
        left = seeds_by_ledger[ledger_id].get("mass_model_511", [])
        right = seeds_by_ledger[ledger_id].get("s3d_o8", [])
        gate.require(left == right, f"{ledger_id}: prior paired gamma seeds differ", "prior_credit")
    for geometry, count in credited.items():
        gate.require(
            count == batch.PRIOR_EVENTS_PER_GEOMETRY,
            f"{geometry}: revalidated prior gamma credit is {count}, not 101000",
            "prior_credit",
        )
    return {
        "status": "PASS" if len(gate.errors) == error_count else "FAIL",
        "credited_events_per_geometry": credited,
        "validated_jobs": len(rows),
        "job_records_sha256": _json_sha256(rows),
        "jobs": rows,
    }


def _receipt_envelope_valid(
    receipt: Any,
    geometry: str,
    ordinal: int,
    pair_binding: dict[str, Any],
    gate: common.Gate,
) -> bool:
    before = len(gate.errors)
    label = f"{geometry}/shard{ordinal:04d}"
    if not isinstance(receipt, dict):
        gate.problem(f"{label}: geometry receipt is not an object", "receipts")
        return False
    expected = {
        "schema_version": 1,
        "status": "PASS__GEOMETRY_SHARD_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": batch.MODE,
        "family": batch.FAMILY,
        "ordinal": ordinal,
        "events": batch.shard_events(ordinal),
        "seed": batch.shard_seed(ordinal),
    }
    for key, value in expected.items():
        gate.require(
            receipt.get(key) == value,
            f"{label}: geometry receipt {key} mismatch",
            "receipts",
        )
    attempt = receipt.get("selected_attempt")
    gate.require(
        type(attempt) is int and 1 <= attempt <= batch.MAX_ATTEMPTS,
        f"{label}: selected attempt is invalid",
        "receipts",
    )
    gate.require(
        pair_binding.get("selected_attempt") == attempt,
        f"{label}: pair/geometry selected-attempt mismatch",
        "receipts",
    )
    if type(attempt) is int and 1 <= attempt <= batch.MAX_ATTEMPTS:
        expected_validation = (
            batch.attempt_dir(geometry, ordinal, attempt) / "attempt_validation.json"
        )
        gate.require(
            receipt.get("attempt_validation") == smoke.rel(expected_validation),
            f"{label}: receipt attempt-validation path is not canonical",
            "receipts",
        )
        gate.require(
            common.is_within(expected_validation, batch.shard_dir(geometry, ordinal)),
            f"{label}: receipt-selected attempt escapes shard directory",
            "receipts",
        )
    return len(gate.errors) == before


def _job_payload(
    validation: dict[str, Any],
    receipt_snapshot: FileSnapshot,
    validation_snapshot: FileSnapshot,
    pair_snapshot: FileSnapshot,
) -> dict[str, Any]:
    artifacts = validation.get("artifacts", {})
    return {
        "job_name": stage_validator._expected_job_name(validation["ordinal"]),
        "family": batch.FAMILY,
        "events": validation["events"],
        "seed": validation["seed"],
        "ordinal": validation["ordinal"],
        "selected_attempt": validation["attempt"],
        "flux_cm2_s": validation.get("flux_cm2_s"),
        "TT_s_expected_mean_from_events_flux_area": validation.get("TT_s_expected_mean_from_events_flux_area"),
        "TT_s_from_log": validation.get("TT_s_from_log"),
        "TT_s_from_isotope_dat": validation.get("TT_s_from_isotope_dat"),
        "TT_authority": validation.get("TT_authority"),
        "job_source": artifacts.get("job_source", {}).get("path"),
        "job_source_sha256": artifacts.get("job_source", {}).get("sha256"),
        "sim": artifacts.get("sim", {}).get("path"),
        "sim_sha256": artifacts.get("sim", {}).get("sha256"),
        "isotope_dat": artifacts.get("isotope_dat", {}).get("path"),
        "isotope_dat_sha256": artifacts.get("isotope_dat", {}).get("sha256"),
        "log": artifacts.get("log", {}).get("path"),
        "log_sha256": artifacts.get("log", {}).get("sha256"),
        "attempt_contract": artifacts.get("attempt_contract", {}).get("path"),
        "attempt_contract_sha256": artifacts.get("attempt_contract", {}).get("sha256"),
        "attempt_validation": smoke.rel(validation_snapshot.path),
        "attempt_validation_sha256": validation_snapshot.sha256,
        "geometry_receipt": smoke.rel(receipt_snapshot.path),
        "geometry_receipt_sha256": receipt_snapshot.sha256,
        "pair_receipt": smoke.rel(pair_snapshot.path),
        "pair_receipt_sha256": pair_snapshot.sha256,
        "isotope_store": validation.get("isotope_store"),
        "ia_init": validation.get("sim_scan"),
    }


def _validate_committed_pairs(
    contract: dict[str, Any],
    pair_snapshots: list[FileSnapshot],
    gate: common.Gate,
    *,
    progress_every: int,
) -> tuple[list[dict[str, Any]], list[FileSnapshot]]:
    jobs_by_geometry: dict[str, list[dict[str, Any]]] = {
        geometry: [] for geometry in batch.GEOMETRIES
    }
    small_snapshots: list[FileSnapshot] = []
    pair_records: list[dict[str, Any]] = []
    for index, pair_snapshot in enumerate(pair_snapshots, 1):
        ordinal = index
        pair = pair_snapshot.payload
        label = f"shard{ordinal:04d}"
        envelope_errors = _pair_envelope_errors(pair, ordinal)
        for problem in envelope_errors:
            gate.problem(problem, "pairing")
        if envelope_errors:
            continue
        expected_bindings: dict[str, dict[str, Any]] = {}
        completed_geometries = 0
        for geometry in batch.GEOMETRIES:
            pair_binding = pair["geometry_receipts"][geometry]
            receipt_path = batch.geometry_receipt_path(geometry, ordinal)
            before_receipt_errors = len(gate.errors)
            try:
                receipt_snapshot = _snapshot_file(receipt_path, parse_json=True)
            except PrefixValidationError as exc:
                gate.problem(f"{label}/{geometry}: {exc}", "receipts")
                continue
            small_snapshots.append(receipt_snapshot)
            gate.require(
                receipt_snapshot.sha256 == pair_binding.get("sha256"),
                f"{label}/{geometry}: pair-to-geometry receipt hash mismatch",
                "pairing",
            )
            envelope_ok = _receipt_envelope_valid(
                receipt_snapshot.payload,
                geometry,
                ordinal,
                pair_binding,
                gate,
            )
            if not envelope_ok or len(gate.errors) != before_receipt_errors:
                # Do not follow an invalid receipt into an attempt directory.
                continue
            receipt = receipt_snapshot.payload
            attempt = int(receipt["selected_attempt"])
            validation_path = (
                batch.attempt_dir(geometry, ordinal, attempt)
                / "attempt_validation.json"
            )
            try:
                validation_snapshot = _snapshot_file(
                    validation_path, parse_json=True
                )
            except PrefixValidationError as exc:
                gate.problem(f"{label}/{geometry}: {exc}", "attempt_validation")
                continue
            small_snapshots.append(validation_snapshot)
            gate.require(
                validation_snapshot.sha256
                == receipt.get("attempt_validation_sha256"),
                f"{label}/{geometry}: receipt-to-attempt-validation hash mismatch",
                "attempt_validation",
            )
            if validation_snapshot.payload.get("status") != "PASS":
                gate.problem(
                    f"{label}/{geometry}: signed attempt validation is not PASS",
                    "attempt_validation",
                )
                continue
            try:
                recomputed, attempt_errors = stage_validator.validate_attempt(
                    contract, geometry, ordinal, attempt
                )
            except (
                KeyError,
                OSError,
                RuntimeError,
                SystemExit,
                TypeError,
                ValueError,
            ) as exc:
                gate.problem(
                    f"{label}/{geometry}: committed attempt revalidation raised: {exc}",
                    "attempt_validation",
                )
                continue
            for problem in attempt_errors:
                gate.problem(
                    f"{label}/{geometry}: {problem}", "attempt_validation"
                )
            gate.require(
                not attempt_errors and recomputed.get("status") == "PASS",
                f"{label}/{geometry}: committed attempt did not revalidate PASS",
                "attempt_validation",
            )
            gate.require(
                recomputed == validation_snapshot.payload,
                f"{label}/{geometry}: signed attempt validation differs from live revalidation",
                "attempt_validation",
            )
            try:
                expected_receipt = stage_validator._receipt_payload(
                    recomputed, validation_path
                )
            except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
                gate.problem(
                    f"{label}/{geometry}: cannot rebuild geometry receipt: {exc}",
                    "receipts",
                )
                continue
            gate.require(
                receipt == expected_receipt,
                f"{label}/{geometry}: geometry receipt payload mismatch",
                "receipts",
            )
            if attempt_errors or recomputed != validation_snapshot.payload or receipt != expected_receipt:
                continue
            expected_bindings[geometry] = {
                "path": smoke.rel(receipt_path),
                "sha256": receipt_snapshot.sha256,
                "selected_attempt": attempt,
            }
            jobs_by_geometry[geometry].append(
                _job_payload(
                    recomputed,
                    receipt_snapshot,
                    validation_snapshot,
                    pair_snapshot,
                )
            )
            completed_geometries += 1
        expected_pair = {
            "schema_version": 1,
            "status": "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
            "batch_id": batch.BATCH_ID,
            "campaign_version": batch.CAMPAIGN_VERSION,
            "ordinal": ordinal,
            "events_per_geometry": batch.shard_events(ordinal),
            "paired_seed": batch.shard_seed(ordinal),
            "pairing_rule": batch.PAIRING_RULE,
            "statistical_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
            "geometry_receipts": expected_bindings,
        }
        gate.require(
            completed_geometries == len(batch.GEOMETRIES),
            f"{label}: no credit without two fully revalidated geometry attempts",
            "pairing",
        )
        gate.require(
            pair == expected_pair,
            f"{label}: pair receipt is not the exact receipt-bound payload",
            "pairing",
        )
        if completed_geometries == len(batch.GEOMETRIES) and pair == expected_pair:
            pair_records.append({
                "ordinal": ordinal,
                "events_per_geometry": batch.shard_events(ordinal),
                "paired_seed": batch.shard_seed(ordinal),
                "path": smoke.rel(pair_snapshot.path),
                "sha256": pair_snapshot.sha256,
            })
        if progress_every > 0 and (ordinal % progress_every == 0 or ordinal == len(pair_snapshots)):
            print(
                f"validated committed pair prefix: {ordinal}/{len(pair_snapshots)}",
                file=sys.stderr,
                flush=True,
            )

    campaigns: list[dict[str, Any]] = []
    for geometry in batch.GEOMETRIES:
        jobs = jobs_by_geometry[geometry]
        expected_ordinals = list(range(1, len(pair_snapshots) + 1))
        observed_ordinals = [int(job["ordinal"]) for job in jobs]
        gate.require(
            observed_ordinals == expected_ordinals,
            f"{geometry}: validated jobs are not the exact continuous prefix",
            "campaigns",
        )
        new_events = sum(int(job["events"]) for job in jobs)
        expected_new = sum(
            batch.shard_events(ordinal) for ordinal in expected_ordinals
        )
        gate.require(
            new_events == expected_new,
            f"{geometry}: validated new-event count mismatch",
            "campaigns",
        )
        gate.require(
            len({int(job["seed"]) for job in jobs}) == len(jobs),
            f"{geometry}: duplicate prefix seed",
            "seeds",
        )
        tt_values = [float(job["TT_s_from_isotope_dat"]) for job in jobs]
        campaigns.append({
            "geometry": geometry,
            "mode": batch.MODE,
            "family": batch.FAMILY,
            "prefix_start_ordinal": 1,
            "prefix_end_ordinal": len(pair_snapshots),
            "prior_events_credited": batch.PRIOR_EVENTS_PER_GEOMETRY,
            "new_events_validated": new_events,
            "cumulative_events": batch.PRIOR_EVENTS_PER_GEOMETRY + new_events,
            "validated_shards": len(jobs),
            "TT_s_new_sum": math.fsum(tt_values),
            "flux_cm2_s": common.source_flux(batch.source_card_path(geometry)),
            "TT_authority": batch.TT_AUTHORITY,
            "jobs": jobs,
        })
    gate.require(
        len(pair_records) == len(pair_snapshots),
        "validated complete-pair count differs from selected prefix length",
        "pairing",
    )
    return campaigns, [*pair_snapshots, *small_snapshots]


def _build_outputs(
    selected: int,
    pair_snapshots: list[FileSnapshot],
    gate: common.Gate,
    *,
    progress_every: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _validate_static_inputs(gate)
    if context is None:
        return (
            {"schema_version": 1, "status": "FAIL", "errors": gate.errors},
            {"schema_version": 1, "status": FAIL_STATUS, "errors": gate.errors},
        )
    contract = context["contract"]
    ledgers = context["ledgers"]
    source_contract = context["source_contract"]

    prefix_seeds = {batch.shard_seed(value) for value in range(1, selected + 1)}
    try:
        prior_seeds = batch._prior_seeds(*ledgers)
    except (KeyError, RuntimeError, SystemExit, TypeError, ValueError) as exc:
        gate.problem(f"prior seed registry cannot be read: {exc}", "seeds")
        prior_seeds = set()
    gate.require(
        prefix_seeds.isdisjoint(prior_seeds),
        "prefix seed registry overlaps a prior accepted batch",
        "seeds",
    )

    prior_initial = _validate_prior_gamma_credit(
        ledgers, source_contract, gate
    )
    campaigns, authority_snapshots = _validate_committed_pairs(
        contract,
        pair_snapshots[:selected],
        gate,
        progress_every=progress_every,
    )

    final_input_digests: dict[str, str] = {}
    for geometry in batch.GEOMETRIES:
        try:
            digest = batch._verify_attempt_inputs(
                contract, geometry, context["environment"]
            )
        except (KeyError, OSError, RuntimeError, SystemExit, TypeError, ValueError) as exc:
            gate.problem(f"{geometry}: final frozen-input gate failed: {exc}", "input_integrity")
            continue
        final_input_digests[geometry] = digest
        gate.require(
            digest == context["input_digests"].get(geometry),
            f"{geometry}: frozen input bundle changed during prefix validation",
            "input_integrity",
        )
    _, transport_final = _validate_transport_without_starting_cosima(contract, gate)
    gate.require(
        transport_final == context["transport_record"],
        "transport files/data changed during prefix validation",
        "transport",
    )
    prior_final = _validate_prior_gamma_credit(ledgers, source_contract, gate)
    gate.require(
        prior_final == prior_initial,
        "prior 101k gamma credit changed during prefix validation",
        "prior_credit",
    )
    for snapshot in [*context["snapshots"], *authority_snapshots]:
        _require_unchanged(snapshot, gate, "authority")
    try:
        contract_final = _snapshot_file(batch.GLOBAL_CONTRACT, parse_json=True)
    except PrefixValidationError as exc:
        gate.problem(str(exc), "contract")
        contract_final = None
    gate.require(
        contract_final is not None
        and contract_final.sha256 == EXPECTED_GLOBAL_CONTRACT_SHA256
        and contract_final.payload == contract,
        "global contract changed during prefix validation",
        "contract",
    )

    cumulative = cumulative_events_per_geometry(selected)
    gate.require(
        all(row.get("cumulative_events") == cumulative for row in campaigns),
        "campaign cumulative counts disagree",
        "campaigns",
    )
    status = VALIDATION_STATUS if not gate.errors else "FAIL"
    validator_hash = smoke.sha256(THIS_FILE)
    pair_records = [
        {
            "ordinal": ordinal,
            "events_per_geometry": batch.shard_events(ordinal),
            "paired_seed": batch.shard_seed(ordinal),
            "path": smoke.rel(pair_snapshots[ordinal - 1].path),
            "sha256": pair_snapshots[ordinal - 1].sha256,
        }
        for ordinal in range(1, selected + 1)
    ]
    authority_boundary = {
        "merge_eligibility": MERGE_STATUS,
        "scope": "corrected-keV instant gamma only, separated by geometry and normalized with per-job TT",
        "full_batch0003_5m_or_10m_checkpoint_authority": False,
        "full_eight_family_authority": False,
        "physics_rate_sensitivity_or_geometry_promotion_authority": False,
        "note": "This is a safe committed-prefix fallback. It never substitutes for the canonical batch0003 5M/10M stage validator or for prompt-to-delayed detector-response closure.",
    }
    report_path, ledger_path = output_paths(selected)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "merge_eligibility": MERGE_STATUS if status == VALIDATION_STATUS else FAIL_STATUS,
        "publisher_version": PUBLISHER_VERSION,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "selection": {
            "selected_prefix_start_ordinal": 1,
            "selected_prefix_end_ordinal": selected,
            "complete_contiguous_pairs_required_and_snapshotted": selected,
            "preferred_ordinal": selected in PREFERRED_ORDINALS,
        },
        "prior_events_per_geometry": batch.PRIOR_EVENTS_PER_GEOMETRY,
        "new_events_per_geometry": cumulative - batch.PRIOR_EVENTS_PER_GEOMETRY,
        "cumulative_events_per_geometry": cumulative,
        "validated_pair_count": selected,
        "validated_geometry_job_count": sum(len(row.get("jobs", [])) for row in campaigns),
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "validator": smoke.rel(THIS_FILE),
        "validator_sha256": validator_hash,
        "reused_read_only_validator": smoke.rel(stage_validator.THIS_FILE),
        "reused_read_only_validator_sha256": EXPECTED_BATCH_VALIDATOR_SHA256,
        "live_files_forbidden": [
            "gamma_instant_batch0003_v1_state.json",
            "gamma_instant_batch0003_v1_controller.lock",
            "unreceipted attempt directories",
        ],
        "cosima_process_started": False,
        "transport_revalidation": context["transport_record"],
        "geometry_bundles": context["geometry_records"],
        "frozen_input_bundle_sha256_initial": context["input_digests"],
        "frozen_input_bundle_sha256_final": final_input_digests,
        "prior_credit_revalidation": prior_final,
        "pair_receipts": pair_records,
        "campaigns": campaigns,
        "authority_boundary": authority_boundary,
        "checks": dict(gate.checks),
        "errors": gate.errors,
    }
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "status": MERGE_STATUS if status == VALIDATION_STATUS else FAIL_STATUS,
        "validation_status": status,
        "publisher_version": PUBLISHER_VERSION,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "prefix_start_ordinal": 1,
        "prefix_end_ordinal": selected,
        "prior_events_per_geometry": batch.PRIOR_EVENTS_PER_GEOMETRY,
        "new_events_per_geometry": cumulative - batch.PRIOR_EVENTS_PER_GEOMETRY,
        "cumulative_events_per_geometry": cumulative,
        "validated_pair_count": selected,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": EXPECTED_GLOBAL_CONTRACT_SHA256,
        "prior_batches": contract.get("lineage", []),
        "prior_credit_revalidation": prior_final,
        "validation_report": smoke.rel(report_path),
        "validator": smoke.rel(THIS_FILE),
        "validator_sha256": validator_hash,
        "reused_read_only_validator": smoke.rel(stage_validator.THIS_FILE),
        "reused_read_only_validator_sha256": EXPECTED_BATCH_VALIDATOR_SHA256,
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_pairing_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": batch.TT_AUTHORITY,
        "prompt_merge_rule": "within one geometry+instant+gamma: sum(selected)/sum(TT)",
        "pair_receipts": pair_records,
        "campaigns": campaigns,
        "authority_boundary": authority_boundary,
        "errors": gate.errors,
    }
    return report, ledger


def output_paths(prefix_ordinal: int) -> tuple[Path, Path]:
    stem = f"gamma_instant_batch0003_prefix_shard{prefix_ordinal:04d}_v1"
    return (
        OUTPUT_ROOT / f"{stem}_validation.json",
        OUTPUT_ROOT / f"{stem}_ledger.json",
    )


def atomic_write_once_json(path: Path, payload: dict[str, Any]) -> None:
    """Create deterministic JSON once; never replace an authority file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(payload)
    if path.exists():
        existing = _snapshot_file(path, parse_json=True)
        if existing.payload != payload or existing.sha256 != hashlib.sha256(encoded).hexdigest():
            raise PrefixValidationError(
                f"write-once authority differs: {smoke.rel(path)}"
            )
        return
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    )
    temporary.write_bytes(encoded)
    try:
        os.link(temporary, path)
    except FileExistsError:
        existing = _snapshot_file(path, parse_json=True)
        if (
            existing.payload != payload
            or existing.sha256 != hashlib.sha256(encoded).hexdigest()
        ):
            raise PrefixValidationError(
                f"concurrent write-once authority differs: {smoke.rel(path)}"
            )
    finally:
        temporary.unlink(missing_ok=True)


def _authority_check(
    report: dict[str, Any], ledger: dict[str, Any], selected: int
) -> list[str]:
    report_path, ledger_path = output_paths(selected)
    errors: list[str] = []
    report_exists = report_path.exists()
    ledger_exists = ledger_path.exists()
    if report_exists != ledger_exists:
        return ["canonical prefix report and ledger are not a complete pair"]
    if not report_exists:
        return []
    try:
        report_snapshot = _snapshot_file(report_path, parse_json=True)
        ledger_snapshot = _snapshot_file(ledger_path, parse_json=True)
    except PrefixValidationError as exc:
        return [str(exc)]
    expected_report_sha256 = hashlib.sha256(
        _canonical_json_bytes(report)
    ).hexdigest()
    expected_ledger = dict(ledger)
    expected_ledger["validation_report_sha256"] = expected_report_sha256
    expected_ledger_sha256 = hashlib.sha256(
        _canonical_json_bytes(expected_ledger)
    ).hexdigest()
    if report_snapshot.payload != report:
        errors.append("canonical prefix report differs from live revalidation")
    if report_snapshot.sha256 != expected_report_sha256:
        errors.append(
            "existing prefix report bytes are not the expected canonical report bytes"
        )
    ledger_report_sha256 = ledger_snapshot.payload.get(
        "validation_report_sha256"
    )
    if not (
        ledger_report_sha256
        == report_snapshot.sha256
        == expected_report_sha256
    ):
        errors.append(
            "report SHA binding mismatch: actual report SHA, canonical report SHA, "
            "and ledger validation_report_sha256 must be identical"
        )
    if ledger_snapshot.payload != expected_ledger:
        errors.append("canonical prefix ledger differs from live revalidation")
    if ledger_snapshot.sha256 != expected_ledger_sha256:
        errors.append(
            "existing prefix ledger bytes are not the expected canonical ledger bytes"
        )
    return errors


def validate_prefix(
    requested: str,
    *,
    check: bool,
    progress_every: int = 10,
) -> tuple[dict[str, Any], int]:
    try:
        discovered = discover_contiguous_pairs()
        available = len(discovered)
        selected = _select_prefix(requested, available)
    except PrefixValidationError as exc:
        result = {
            "status": "FAIL",
            "merge_eligibility": FAIL_STATUS,
            "authority_written": False,
            "errors": [str(exc)],
        }
        return result, 1

    gate = common.Gate()
    try:
        report, ledger = _build_outputs(
            selected,
            discovered[:selected],
            gate,
            progress_every=progress_every,
        )
    except (Exception, SystemExit) as exc:
        return ({
            "status": "FAIL",
            "merge_eligibility": FAIL_STATUS,
            "selected_prefix_end_ordinal": selected,
            "cumulative_events_per_geometry": cumulative_events_per_geometry(selected),
            "authority_written": False,
            "errors": [f"fail-closed prefix revalidation exception: {exc}"],
        }, 1)
    if report.get("status") != VALIDATION_STATUS:
        return ({
            "status": "FAIL",
            "merge_eligibility": FAIL_STATUS,
            "selected_prefix_end_ordinal": selected,
            "cumulative_events_per_geometry": cumulative_events_per_geometry(selected),
            "authority_written": False,
            "errors": report.get("errors", []),
        }, 1)

    report_path, ledger_path = output_paths(selected)
    if check:
        authority_errors = _authority_check(report, ledger, selected)
        return ({
            "status": "PASS" if not authority_errors else "FAIL",
            "merge_eligibility": MERGE_STATUS if not authority_errors else FAIL_STATUS,
            "mode": "READ_ONLY_CHECK",
            "selected_prefix_end_ordinal": selected,
            "cumulative_events_per_geometry": cumulative_events_per_geometry(selected),
            "canonical_authority_present": report_path.exists() or ledger_path.exists(),
            "canonical_authority_pair_valid": report_path.exists() and ledger_path.exists() and not authority_errors,
            "authority_written": False,
            "errors": authority_errors,
        }, 0 if not authority_errors else 1)

    try:
        atomic_write_once_json(report_path, report)
        ledger["validation_report_sha256"] = _snapshot_file(report_path).sha256
        atomic_write_once_json(ledger_path, ledger)
    except PrefixValidationError as exc:
        return ({
            "status": "FAIL",
            "merge_eligibility": FAIL_STATUS,
            "selected_prefix_end_ordinal": selected,
            "authority_written": False,
            "errors": [str(exc)],
        }, 1)
    return ({
        "status": VALIDATION_STATUS,
        "merge_eligibility": MERGE_STATUS,
        "selected_prefix_end_ordinal": selected,
        "cumulative_events_per_geometry": cumulative_events_per_geometry(selected),
        "validation": smoke.rel(report_path),
        "ledger": smoke.rel(ledger_path),
        "authority_written": True,
        "errors": [],
    }, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix-ordinal",
        default="auto",
        help=(
            "auto selects the highest complete continuous pair prefix; milestone "
            "selects the highest available of 76/116/156; an integer selects that exact prefix"
        ),
    )
    parser.add_argument(
        "--check", action="store_true", help="read-only validation; write no authority files"
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="inspect only committed pair receipts and print available prefixes",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="write progress to stderr every N committed pairs; 0 disables",
    )
    args = parser.parse_args()
    if args.progress_every < 0:
        parser.error("--progress-every must be nonnegative")
    if args.discover:
        try:
            snapshots = discover_contiguous_pairs()
        except PrefixValidationError as exc:
            print(json.dumps({"status": "FAIL", "errors": [str(exc)]}, indent=2))
            return 1
        available = len(snapshots)
        print(json.dumps({
            "status": "PASS",
            "mode": "PAIR_RECEIPT_DISCOVERY_ONLY",
            "complete_contiguous_pair_prefix": available,
            "cumulative_events_per_geometry": (
                cumulative_events_per_geometry(available) if available else batch.PRIOR_EVENTS_PER_GEOMETRY
            ),
            "preferred_prefixes_available": [
                value for value in PREFERRED_ORDINALS if value <= available
            ],
            "attempt_directories_read": False,
            "execution_state_read": False,
            "cosima_process_started": False,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    result, returncode = validate_prefix(
        args.prefix_ordinal,
        check=args.check,
        progress_every=args.progress_every,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
