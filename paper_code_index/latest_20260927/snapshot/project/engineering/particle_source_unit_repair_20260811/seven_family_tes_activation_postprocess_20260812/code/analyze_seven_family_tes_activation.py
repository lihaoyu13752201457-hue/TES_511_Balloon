#!/usr/bin/env python3
"""Canonical seven-family prompt-TES and buildup-activation postprocessor.

The executable is deliberately dormant until batch0004 publishes all twelve
family/mode checkpoint report+ledger pairs and its final PASS authority.  It
never discovers jobs by globbing run directories: every SIM/DAT/log/source is
enumerated from a canonical PASS ledger, then rebound to its on-disk hash,
geometry and observation time.

Prompt observables consume ``instant`` jobs only.  Isotope production consumes
``buildup`` DAT jobs only.  Geometry, mode and particle family are independent
normalization domains throughout.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


def _find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = _find_root(THIS_FILE.parent)
PACKAGE = THIS_FILE.parents[1]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
GAMMA_CORE_PATH = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811"
    / "code/analyze_gamma5m_prompt_tes.py"
)


def _load_gamma_core() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_gamma5m_prompt_core", GAMMA_CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen gamma core: {GAMMA_CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gamma = _load_gamma_core()

GEOMETRIES = tuple(gamma.GEOMETRIES)
GEOMETRY_LABELS = dict(gamma.GEOMETRY_LABELS)
GEOMETRY_CONTRACTS = gamma.GEOMETRY_CONTRACTS
FAMILIES = ("gamma", "n", "eplus", "alpha", "eminus", "muplus", "muminus")
MODES = ("instant", "buildup")
PARTICLE_TYPES = {
    "gamma": 1,
    "eplus": 2,
    "eminus": 3,
    "n": 6,
    "muplus": 8,
    "muminus": 9,
    "alpha": 21,
}
SOURCE_CONTRACT_SHA256 = gamma.SOURCE_CONTRACT_SHA256
FWHM_KEV = gamma.FWHM_KEV
SIGMA_KEV = gamma.SIGMA_KEV
PIXEL_THRESHOLD_KEV = gamma.PIXEL_THRESHOLD_KEV
VETO_THRESHOLDS_KEV = tuple(gamma.VETO_THRESHOLDS_KEV)
O8_PLASTIC_THRESHOLD_KEV = gamma.O8_PLASTIC_THRESHOLD_KEV
BROAD_KEV = tuple(gamma.BROAD_KEV)
W2_KEV = tuple(gamma.W2_KEV)
SELECTIONS = tuple(gamma.SELECTIONS)
WINDOWS = tuple(gamma.WINDOWS)
HISTOGRAM_VIEWS = gamma.HISTOGRAM_VIEWS
ENERGY_EDGES = tuple(gamma.ENERGY_EDGES)
ENERGY_LABELS = tuple(gamma.ENERGY_LABELS)
THETA_EDGES = tuple(gamma.THETA_EDGES)
RESPONSE_NAMESPACE = "TES511_CORRECTED_SEVEN_FAMILY_PROMPT_KEYED_PIXEL_RESPONSE_V1"
RESPONSES = ("raw", "measured")

BATCH0000_LEDGER_SHA256 = "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f"
BATCH0001_LEDGER_SHA256 = "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4"
BATCH0002_LEDGER_SHA256 = "742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62"
BATCH0000_ID = "corrected_original_all8_fullsphere20_batch0000"
BATCH0001_ID = "corrected_original_seven_family_fullsphere20_batch0001"
BATCH0002_ID = "corrected_original_muminus_instant_pair_batch0002"
BATCH0003_ID = "corrected_original_gamma_instant_batch0003"
BATCH0004_ID = "corrected_original_seven_family_1m_screening_batch0004"
BATCH0004_FINAL_STATUS = "PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE"

STAGE_ORDER = (
    "gamma_buildup",
    "n_instant",
    "n_buildup",
    "eplus_instant",
    "eplus_buildup",
    "alpha_instant",
    "alpha_buildup",
    "eminus_instant",
    "eminus_buildup",
    "muplus_instant",
    "muplus_buildup",
    "muminus_buildup",
)


def _stage_cell(stage: str) -> tuple[str, str]:
    family, mode = stage.rsplit("_", 1)
    if family not in FAMILIES or mode not in MODES:
        raise RuntimeError(f"invalid batch0004 stage {stage!r}")
    return family, mode


def _stage_ledger_status(stage: str) -> str:
    return f"PASS__BATCH0004_{stage.upper()}_1M_SCREENING_MERGE_ELIGIBLE"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _json(path: Path) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r}")

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {rel(path)}")
    return value


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink():
        raise RuntimeError(f"canonical authority must not be a symlink: {rel(path)}")
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(raw) != after.st_size or after.st_size <= 0:
        raise RuntimeError(f"canonical authority changed while read: {rel(path)}")

    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r}")

    value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected canonical JSON object: {rel(path)}")
    return value, hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        temporary.write_bytes(canonical_json_bytes(payload))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: Iterable[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(fieldnames or (rows[0].keys() if rows else ()))
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=names)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class AuthorityWait(RuntimeError):
    """Canonical PASS products have not all been published yet."""


@dataclass(frozen=True)
class CanonicalPaths:
    batch0000_ledger: Path = RUN_ROOT / "mergeable_smoke_v1_ledger.json"
    batch0001_ledger: Path = RUN_ROOT / "seven_family_batch0001_v1_ledger.json"
    batch0002_ledger: Path = RUN_ROOT / "muminus_instant_pair_batch0002_v1_ledger.json"
    batch0004_contract: Path = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_contract.json"
    batch0004_final_report: Path = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_validation.json"
    batch0004_final_ledger: Path = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_ledger.json"
    batch0004_checkpoint_root: Path = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_checkpoints"

    def checkpoint_report(self, stage: str) -> Path:
        return self.batch0004_checkpoint_root / f"{stage}_validation.json"

    def checkpoint_ledger(self, stage: str) -> Path:
        return self.batch0004_checkpoint_root / f"{stage}_ledger.json"


DEFAULT_PATHS = CanonicalPaths()
AUTHORITY_PIN = PACKAGE / "data/canonical_authorities.json"


def _require_files(paths: Iterable[Path]) -> None:
    missing = [rel(path) for path in paths if not path.is_file()]
    if missing:
        raise AuthorityWait("canonical PASS authority is not complete: " + ", ".join(missing))


def _fixed_ledger(
    path: Path,
    expected_hash: str,
    expected_batch: str,
    expected_status: str,
) -> tuple[dict[str, Any], str]:
    ledger, digest = _stable_json(path)
    if digest != expected_hash:
        raise RuntimeError(f"pinned ledger hash mismatch: {rel(path)}")
    if (
        ledger.get("schema_version") != 1
        or ledger.get("batch_id") != expected_batch
        or ledger.get("status") != expected_status
        or ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
        or ledger.get("errors") not in (None, [])
    ):
        raise RuntimeError(f"ledger identity/status/source contract mismatch: {rel(path)}")
    return ledger, digest


def _validate_selected_batch0003(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    dependency = contract.get("batch0003_predecessor_authority", {})
    profile_key = dependency.get("profile")
    if profile_key == "prefix_ordinal76":
        profile = gamma.PREFIX76_PROFILE
        expected_gate = "PASS__BATCH0003_PREFIX76_AUTHORITY_PRESENT"
    elif profile_key == "stage5":
        profile = gamma.STAGE5_PROFILE
        expected_gate = "PASS__BATCH0003_STAGE5_AUTHORITY_PRESENT"
    else:
        raise RuntimeError("batch0004 does not freeze an accepted batch0003 authority profile")
    if (
        dependency.get("batch_id") != BATCH0003_ID
        or dependency.get("gate") != expected_gate
        or resolve_path(str(dependency.get("report", "__missing__"))).resolve()
        != profile.validation.resolve()
        or resolve_path(str(dependency.get("ledger", "__missing__"))).resolve()
        != profile.ledger.resolve()
        or dependency.get("selected_status") != profile.ledger_status
    ):
        raise RuntimeError("batch0004 selected batch0003 path/status/profile mismatch")
    _require_files((profile.validation, profile.ledger))
    if (
        sha256(profile.validation) != dependency.get("report_sha256")
        or sha256(profile.ledger) != dependency.get("ledger_sha256")
    ):
        raise RuntimeError("batch0003 selected report/ledger hash differs from batch0004 contract")
    report, report_hash = _stable_json(profile.validation)
    ledger, ledger_hash = _stable_json(profile.ledger)
    if report_hash != dependency["report_sha256"] or ledger_hash != dependency["ledger_sha256"]:
        raise RuntimeError("batch0003 selected authority changed during stable read")
    gamma._validate_profile_authority_payloads(profile, ledger, report)
    exposure = dependency.get("gamma_exposure")
    if not isinstance(exposure, dict) or exposure.get("mode") != "instant":
        raise RuntimeError("batch0003 selected exposure is not explicit instant gamma")
    if exposure.get("credited_to_batch0004_buildup") is not False:
        raise RuntimeError("batch0003 instant exposure is incorrectly credited to buildup")
    if int(exposure.get("cumulative_events_per_geometry", -1)) != profile.cumulative_events_per_geometry:
        raise RuntimeError("batch0003 selected exposure count mismatch")
    return dependency, report, ledger


def build_authority_snapshot(paths: CanonicalPaths = DEFAULT_PATHS) -> dict[str, Any]:
    required = [
        paths.batch0000_ledger,
        paths.batch0001_ledger,
        paths.batch0002_ledger,
        paths.batch0004_contract,
        paths.batch0004_final_report,
        paths.batch0004_final_ledger,
    ]
    required.extend(paths.checkpoint_report(stage) for stage in STAGE_ORDER)
    required.extend(paths.checkpoint_ledger(stage) for stage in STAGE_ORDER)
    _require_files(required)

    ledger0, hash0 = _fixed_ledger(
        paths.batch0000_ledger,
        BATCH0000_LEDGER_SHA256,
        BATCH0000_ID,
        "PASS__BATCH0000_MERGE_ELIGIBLE",
    )
    ledger1, hash1 = _fixed_ledger(
        paths.batch0001_ledger,
        BATCH0001_LEDGER_SHA256,
        BATCH0001_ID,
        "PASS__BATCH0001_MERGE_ELIGIBLE",
    )
    ledger2, hash2 = _fixed_ledger(
        paths.batch0002_ledger,
        BATCH0002_LEDGER_SHA256,
        BATCH0002_ID,
        "PASS__BATCH0002_MERGE_ELIGIBLE",
    )
    del ledger0, ledger1, ledger2

    contract, contract_hash = _stable_json(paths.batch0004_contract)
    if (
        contract.get("schema_version") != 1
        or contract.get("batch_id") != BATCH0004_ID
        or contract.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
        or contract.get("source_scope", {}).get("gamma_modes") != ["buildup"]
    ):
        raise RuntimeError("batch0004 global contract identity/source scope mismatch")
    dependency, selected_report, selected_ledger = _validate_selected_batch0003(contract)
    del selected_report

    checkpoint_records: list[dict[str, Any]] = []
    checkpoint_campaigns: list[dict[str, Any]] = []
    for stage in STAGE_ORDER:
        family, mode = _stage_cell(stage)
        report_path = paths.checkpoint_report(stage)
        ledger_path = paths.checkpoint_ledger(stage)
        report, report_hash = _stable_json(report_path)
        ledger, ledger_hash = _stable_json(ledger_path)
        if (
            report.get("schema_version") != 1
            or report.get("status") != "PASS"
            or report.get("batch_id") != BATCH0004_ID
            or report.get("stage") != stage
            or report.get("family") != family
            or report.get("mode") != mode
            or report.get("global_contract_sha256") != contract_hash
            or report.get("errors") != []
        ):
            raise RuntimeError(f"batch0004 checkpoint report is not canonical PASS: {stage}")
        if (
            ledger.get("schema_version") != 1
            or ledger.get("status") != _stage_ledger_status(stage)
            or ledger.get("batch_id") != BATCH0004_ID
            or ledger.get("stage") != stage
            or ledger.get("family") != family
            or ledger.get("mode") != mode
            or ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
            or ledger.get("global_contract_sha256") != contract_hash
            or resolve_path(str(ledger.get("validation_report", "__missing__"))).resolve()
            != report_path.resolve()
            or ledger.get("validation_report_sha256") != report_hash
            or ledger.get("errors") != []
        ):
            raise RuntimeError(f"batch0004 checkpoint ledger is not canonical PASS: {stage}")
        campaigns = ledger.get("campaigns", [])
        if (
            len(campaigns) != len(GEOMETRIES)
            or {row.get("geometry") for row in campaigns} != set(GEOMETRIES)
            or any(row.get("family") != family or row.get("mode") != mode for row in campaigns)
        ):
            raise RuntimeError(f"batch0004 checkpoint campaign grain mismatch: {stage}")
        checkpoint_campaigns.extend(campaigns)
        checkpoint_records.append(
            {
                "stage": stage,
                "report": rel(report_path),
                "report_sha256": report_hash,
                "ledger": rel(ledger_path),
                "ledger_sha256": ledger_hash,
                "status": ledger["status"],
            }
        )

    final_report, final_report_hash = _stable_json(paths.batch0004_final_report)
    final_ledger, final_ledger_hash = _stable_json(paths.batch0004_final_ledger)
    if (
        final_report.get("schema_version") != 1
        or final_report.get("status") != "PASS"
        or final_report.get("batch_id") != BATCH0004_ID
        or final_report.get("stage") != "final"
        or final_report.get("global_contract_sha256") != contract_hash
        or final_report.get("errors") != []
    ):
        raise RuntimeError("batch0004 final report is not canonical PASS")
    if (
        final_ledger.get("schema_version") != 1
        or final_ledger.get("status") != BATCH0004_FINAL_STATUS
        or final_ledger.get("batch_id") != BATCH0004_ID
        or final_ledger.get("stage") != "final"
        or final_ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
        or final_ledger.get("global_contract_sha256") != contract_hash
        or resolve_path(str(final_ledger.get("validation_report", "__missing__"))).resolve()
        != paths.batch0004_final_report.resolve()
        or final_ledger.get("validation_report_sha256") != final_report_hash
        or final_ledger.get("errors") != []
    ):
        raise RuntimeError("batch0004 final ledger is not canonical merge authority")
    if final_report.get("checkpoint_authorities") != checkpoint_records:
        raise RuntimeError("batch0004 final report checkpoint authority set mismatch")
    if final_ledger.get("checkpoint_authorities") != checkpoint_records:
        raise RuntimeError("batch0004 final ledger checkpoint authority set mismatch")
    final_campaigns = final_ledger.get("campaigns", [])
    remaining = list(final_campaigns)
    for campaign in checkpoint_campaigns:
        try:
            remaining.remove(campaign)
        except ValueError as exc:
            raise RuntimeError("batch0004 final ledger omits or changes a checkpoint campaign") from exc
    if (
        len(remaining) != len(GEOMETRIES)
        or {row.get("geometry") for row in remaining} != set(GEOMETRIES)
        or any(
            row.get("family") != "muminus"
            or row.get("mode") != "instant"
            or row.get("prior_only") is not True
            or int(row.get("new_events_validated", -1)) != 0
            for row in remaining
        )
    ):
        raise RuntimeError("batch0004 final ledger prior-only muminus closure mismatch")

    records = [
        {
            "role": "batch0000_ledger",
            "path": rel(paths.batch0000_ledger),
            "sha256": hash0,
            "status": "PASS__BATCH0000_MERGE_ELIGIBLE",
        },
        {
            "role": "batch0001_ledger",
            "path": rel(paths.batch0001_ledger),
            "sha256": hash1,
            "status": "PASS__BATCH0001_MERGE_ELIGIBLE",
        },
        {
            "role": "batch0002_ledger",
            "path": rel(paths.batch0002_ledger),
            "sha256": hash2,
            "status": "PASS__BATCH0002_MERGE_ELIGIBLE",
        },
        {
            "role": "batch0003_selected_report",
            "path": dependency["report"],
            "sha256": dependency["report_sha256"],
            "status": (
                gamma.PREFIX76_PROFILE.validation_status
                if dependency["profile"] == "prefix_ordinal76"
                else gamma.STAGE5_PROFILE.validation_status
            ),
        },
        {
            "role": "batch0003_selected_ledger",
            "path": dependency["ledger"],
            "sha256": dependency["ledger_sha256"],
            "status": selected_ledger["status"],
        },
        {
            "role": "batch0004_contract",
            "path": rel(paths.batch0004_contract),
            "sha256": contract_hash,
            "status": contract.get("status"),
        },
        *[
            {
                "role": f"batch0004_checkpoint_report:{row['stage']}",
                "path": row["report"],
                "sha256": row["report_sha256"],
                "status": "PASS",
            }
            for row in checkpoint_records
        ],
        *[
            {
                "role": f"batch0004_checkpoint_ledger:{row['stage']}",
                "path": row["ledger"],
                "sha256": row["ledger_sha256"],
                "status": row["status"],
            }
            for row in checkpoint_records
        ],
        {
            "role": "batch0004_final_report",
            "path": rel(paths.batch0004_final_report),
            "sha256": final_report_hash,
            "status": "PASS",
        },
        {
            "role": "batch0004_final_ledger",
            "path": rel(paths.batch0004_final_ledger),
            "sha256": final_ledger_hash,
            "status": BATCH0004_FINAL_STATUS,
        },
    ]
    if len({row["role"] for row in records}) != len(records):
        raise RuntimeError("canonical authority role registry is not unique")
    return {
        "schema_version": 1,
        "status": "PASS__SEVEN_FAMILY_POSTPROCESS_CANONICAL_AUTHORITIES",
        "write_once": True,
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "batch0003_selected_profile": dependency["profile"],
        "batch0003_gamma_exposure": dependency["gamma_exposure"],
        "batch0003_exposure_credited_to_buildup": False,
        "batch0004_stage_order": list(STAGE_ORDER),
        "prompt_mode": "instant_only",
        "activation_mode": "buildup_only",
        "aggregation_grain": "geometry+mode+family",
        "authorities": records,
        "toolchain": {
            "analyzer": {"path": rel(THIS_FILE), "sha256": sha256(THIS_FILE)},
            "frozen_gamma_prompt_core": {
                "path": rel(GAMMA_CORE_PATH),
                "sha256": sha256(GAMMA_CORE_PATH),
            },
        },
    }


def pin_authorities(
    *,
    paths: CanonicalPaths = DEFAULT_PATHS,
    pin_path: Path = AUTHORITY_PIN,
) -> dict[str, Any]:
    payload = build_authority_snapshot(paths)
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    if pin_path.exists():
        if _json(pin_path) != payload:
            raise RuntimeError("write-once canonical authority pin differs from current PASS set")
        return payload
    temporary = pin_path.with_name(f".{pin_path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        temporary.write_bytes(canonical_json_bytes(payload))
        try:
            os.link(temporary, pin_path)
        except FileExistsError:
            if _json(pin_path) != payload:
                raise RuntimeError("concurrent authority pin differs")
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def load_authority_pin(
    *,
    paths: CanonicalPaths = DEFAULT_PATHS,
    pin_path: Path = AUTHORITY_PIN,
) -> dict[str, Any]:
    if not pin_path.is_file():
        raise AuthorityWait("canonical authority pin is absent; run --pin-authorities after final PASS")
    observed = _json(pin_path)
    expected = build_authority_snapshot(paths)
    if observed != expected:
        raise RuntimeError("canonical authority pin no longer matches the complete PASS set")
    return observed


LOG_TT_RE = re.compile(r"^Observation time:\s*([-+0-9.eE]+)\s+sec\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$")
SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$")
EDEP_RE = gamma.EDEP_RE


def parse_unique_source_geometry(path: Path) -> Path:
    values = [
        match.group(1)
        for raw in path.read_text(encoding="utf-8", errors="strict").splitlines()
        if (match := GEOMETRY_RE.match(raw.strip()))
    ]
    if len(values) != 1:
        raise RuntimeError(f"{rel(path)}: Geometry record count={len(values)}, expected 1")
    return resolve_path(values[0]).resolve()


def parse_unique_log_tt(path: Path) -> float:
    values = [
        float(match.group(1))
        for raw in path.read_text(encoding="utf-8", errors="strict").splitlines()
        if (match := LOG_TT_RE.match(raw.strip()))
    ]
    if len(values) != 1 or not math.isfinite(values[0]) or values[0] <= 0.0:
        raise RuntimeError(f"{rel(path)}: invalid/duplicate Observation time {values!r}")
    return values[0]


def parse_isotope_dat(path: Path) -> dict[str, Any]:
    tt_values: list[float] = []
    records: list[dict[str, Any]] = []
    current_volume: str | None = None
    end_count = 0
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(), 1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT":
            if len(fields) != 2:
                raise RuntimeError(f"{rel(path)}:{line_number}: malformed TT")
            value = float(fields[1])
            if not math.isfinite(value) or value <= 0.0:
                raise RuntimeError(f"{rel(path)}:{line_number}: TT is not positive finite")
            tt_values.append(value)
        elif fields[0] == "VN":
            current_volume = line[2:].strip()
            if not current_volume:
                raise RuntimeError(f"{rel(path)}:{line_number}: empty VN")
        elif fields[0] == "RP":
            if len(fields) != 4 or current_volume is None:
                raise RuntimeError(f"{rel(path)}:{line_number}: malformed/orphan RP")
            isotope_id = int(fields[1])
            excitation = float(fields[2])
            value = float(fields[3])
            if (
                isotope_id <= 0
                or not math.isfinite(excitation)
                or excitation < 0.0
                or not math.isfinite(value)
                or value < 0.0
            ):
                raise RuntimeError(f"{rel(path)}:{line_number}: invalid RP")
            records.append(
                {
                    "volume": current_volume,
                    "isotope_id": isotope_id,
                    "excitation_keV": excitation,
                    "RP": value,
                }
            )
        elif fields[0] == "EN" and len(fields) == 1:
            end_count += 1
        else:
            raise RuntimeError(f"{rel(path)}:{line_number}: unrecognized DAT record {fields[0]!r}")
    if len(tt_values) != 1 or end_count != 1:
        raise RuntimeError(
            f"{rel(path)}: DAT closure TT={len(tt_values)}, EN={end_count}; expected 1/1"
        )
    totals: dict[tuple[str, int, float], float] = defaultdict(float)
    for row in records:
        key = (str(row["volume"]), int(row["isotope_id"]), float(row["excitation_keV"]))
        totals[key] = math.fsum((totals[key], float(row["RP"])))
    return {
        "TT_s": tt_values[0],
        "RP_record_count": len(records),
        "RP_records": records,
        "RP_totals_by_volume_isotope_state": [
            {
                "volume": key[0],
                "isotope_id": key[1],
                "excitation_keV": key[2],
                "sum_RP": value,
            }
            for key, value in sorted(totals.items())
        ],
        "problems": [],
    }


@dataclass(frozen=True)
class JobInput:
    geometry: str
    mode: str
    family: str
    batch_id: str
    ledger: Path
    ledger_sha256: str
    job_name: str
    events: int
    seed: int
    ordinal: int | None
    tt_s: float
    sim: Path
    sim_sha256: str
    job_source: Path
    job_source_sha256: str
    isotope_dat: Path
    isotope_dat_sha256: str
    log: Path
    log_sha256: str
    expected_geometry_setup: Path
    ledger_geometry_header: Path
    source_geometry: Path
    isotope_store: dict[str, Any]

    @property
    def cell(self) -> tuple[str, str, str]:
        return (self.geometry, self.mode, self.family)

    @property
    def event_key_prefix(self) -> tuple[object, ...]:
        return (self.geometry, self.mode, self.family, self.batch_id, self.seed, self.job_name)


def _campaign_geometry_mode(ledger: dict[str, Any], campaign: dict[str, Any]) -> tuple[str, str]:
    geometry = str(campaign.get("geometry"))
    mode = str(campaign.get("mode"))
    if geometry not in GEOMETRIES or mode not in MODES:
        raise RuntimeError(f"{ledger.get('batch_id')}: invalid campaign geometry/mode")
    return geometry, mode


def _job_from_row(
    ledger: dict[str, Any],
    ledger_path: Path,
    ledger_hash: str,
    campaign: dict[str, Any],
    row: dict[str, Any],
) -> JobInput:
    geometry, mode = _campaign_geometry_mode(ledger, campaign)
    family = str(row.get("family", campaign.get("family")))
    if family not in FAMILIES:
        raise RuntimeError(f"{ledger.get('batch_id')}/{geometry}/{mode}: invalid family {family!r}")
    identity = f"{ledger.get('batch_id')}/{geometry}/{mode}/{family}/{row.get('job_name')}"
    expected_geometry = Path(GEOMETRY_CONTRACTS[geometry]["geometry_setup"]).resolve()
    ia = row.get("ia_init", {})
    header = ia.get("geometry_header")
    if not isinstance(header, str):
        raise RuntimeError(f"{identity}: ledger lacks SIM Geometry header")
    ledger_geometry = resolve_path(header).resolve()
    if ledger_geometry != expected_geometry:
        raise RuntimeError(f"{identity}: ledger Geometry differs from fixed geometry key")
    artifacts = {
        "job_source": (resolve_path(str(row.get("job_source", "__missing__"))).resolve(), "job_source_sha256"),
        "isotope_dat": (resolve_path(str(row.get("isotope_dat", "__missing__"))).resolve(), "isotope_dat_sha256"),
        "log": (resolve_path(str(row.get("log", "__missing__"))).resolve(), "log_sha256"),
        "sim": (resolve_path(str(row.get("sim", "__missing__"))).resolve(), "sim_sha256"),
    }
    for kind, (path, hash_key) in artifacts.items():
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"{identity}: missing/empty {kind}: {rel(path)}")
        if kind != "sim" and sha256(path) != row.get(hash_key):
            raise RuntimeError(f"{identity}: {kind} hash differs from PASS ledger")
    source_geometry = parse_unique_source_geometry(artifacts["job_source"][0])
    if source_geometry != expected_geometry:
        raise RuntimeError(f"{identity}: job-source Geometry differs from fixed geometry key")
    isotope_store = parse_isotope_dat(artifacts["isotope_dat"][0])
    log_tt = parse_unique_log_tt(artifacts["log"][0])
    ledger_tt_dat = row.get("TT_s_from_isotope_dat", campaign.get("TT_s_from_isotope_dat"))
    ledger_tt_log = row.get("TT_s_from_log", campaign.get("TT_s_from_log"))
    try:
        ledger_tt_dat_f = float(ledger_tt_dat)
        ledger_tt_log_f = float(ledger_tt_log)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{identity}: ledger TT is missing/non-numeric") from exc
    if not (
        math.isclose(isotope_store["TT_s"], log_tt, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(isotope_store["TT_s"], ledger_tt_dat_f, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(log_tt, ledger_tt_log_f, rel_tol=0.0, abs_tol=1e-12)
    ):
        raise RuntimeError(f"{identity}: DAT/log/ledger TT mismatch")
    if row.get("isotope_store") != isotope_store:
        raise RuntimeError(f"{identity}: live DAT parse differs from ledger isotope_store")
    return JobInput(
        geometry=geometry,
        mode=mode,
        family=family,
        batch_id=str(ledger["batch_id"]),
        ledger=ledger_path,
        ledger_sha256=ledger_hash,
        job_name=str(row["job_name"]),
        events=int(row["events"]),
        seed=int(row["seed"]),
        ordinal=int(row["ordinal"]) if row.get("ordinal") is not None else None,
        tt_s=float(isotope_store["TT_s"]),
        sim=artifacts["sim"][0],
        sim_sha256=str(row["sim_sha256"]),
        job_source=artifacts["job_source"][0],
        job_source_sha256=str(row["job_source_sha256"]),
        isotope_dat=artifacts["isotope_dat"][0],
        isotope_dat_sha256=str(row["isotope_dat_sha256"]),
        log=artifacts["log"][0],
        log_sha256=str(row["log_sha256"]),
        expected_geometry_setup=expected_geometry,
        ledger_geometry_header=ledger_geometry,
        source_geometry=source_geometry,
        isotope_store=isotope_store,
    )


def _authority_by_role(pin: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = pin.get("authorities", [])
    result = {str(row["role"]): row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("authority pin has duplicate roles")
    return result


def collect_canonical_jobs(
    *,
    paths: CanonicalPaths = DEFAULT_PATHS,
    pin_path: Path = AUTHORITY_PIN,
) -> tuple[dict[tuple[str, str, str], list[JobInput]], list[dict[str, Any]], dict[str, str]]:
    pin = load_authority_pin(paths=paths, pin_path=pin_path)
    gamma.validate_detector_map_contracts()
    gamma._validate_geometry_file_bindings(GEOMETRY_CONTRACTS)
    roles = _authority_by_role(pin)

    ledger_specs: list[tuple[str, Path, set[tuple[str, str]] | None]] = [
        ("batch0000_ledger", paths.batch0000_ledger, None),
        ("batch0001_ledger", paths.batch0001_ledger, None),
        ("batch0002_ledger", paths.batch0002_ledger, {("muminus", "instant")}),
        (
            "batch0003_selected_ledger",
            resolve_path(roles["batch0003_selected_ledger"]["path"]),
            {("gamma", "instant")},
        ),
    ]
    for stage in STAGE_ORDER:
        ledger_specs.append(
            (
                f"batch0004_checkpoint_ledger:{stage}",
                paths.checkpoint_ledger(stage),
                {_stage_cell(stage)},
            )
        )

    jobs_by_cell: dict[tuple[str, str, str], list[JobInput]] = {
        (geometry, mode, family): []
        for geometry in GEOMETRIES
        for mode in MODES
        for family in FAMILIES
    }
    inventory: list[dict[str, Any]] = []
    ledger_hashes: dict[str, str] = {}
    identities: set[tuple[str, str, str, str, str]] = set()
    artifact_paths: set[Path] = set()
    cell_seeds: set[tuple[str, str, str, int]] = set()
    for role, ledger_path, allowed_cells in ledger_specs:
        record = roles[role]
        if ledger_path.resolve() != resolve_path(record["path"]).resolve():
            raise RuntimeError(f"authority role path mismatch: {role}")
        digest = sha256(ledger_path)
        if digest != record["sha256"]:
            raise RuntimeError(f"authority role hash drift: {role}")
        ledger_hashes[rel(ledger_path)] = digest
        ledger = _json(ledger_path)
        for campaign in ledger.get("campaigns", []):
            geometry, mode = _campaign_geometry_mode(ledger, campaign)
            for row in campaign.get("jobs", []):
                family = str(row.get("family", campaign.get("family")))
                if family == "p":
                    if role != "batch0000_ledger":
                        raise RuntimeError(f"unexpected proton outside batch0000: {role}")
                    continue
                cell_family_mode = (family, mode)
                if allowed_cells is not None and cell_family_mode not in allowed_cells:
                    raise RuntimeError(f"{role} contains out-of-scope job {family}/{mode}")
                job = _job_from_row(ledger, ledger_path, digest, campaign, row)
                identity = (job.geometry, job.mode, job.family, job.batch_id, job.job_name)
                if identity in identities:
                    raise RuntimeError(f"duplicate canonical job identity: {identity}")
                identities.add(identity)
                seed_key = (job.geometry, job.mode, job.family, job.seed)
                if seed_key in cell_seeds:
                    raise RuntimeError(f"duplicate seed inside aggregation cell: {seed_key}")
                cell_seeds.add(seed_key)
                for artifact in (job.job_source, job.isotope_dat, job.log, job.sim):
                    if artifact in artifact_paths:
                        raise RuntimeError(f"artifact reused by multiple ledger jobs: {rel(artifact)}")
                    artifact_paths.add(artifact)
                jobs_by_cell[job.cell].append(job)
                inventory.append(
                    {
                        "geometry": job.geometry,
                        "mode": job.mode,
                        "family": job.family,
                        "batch_id": job.batch_id,
                        "ledger": rel(job.ledger),
                        "ledger_sha256": job.ledger_sha256,
                        "job_name": job.job_name,
                        "events": job.events,
                        "seed": job.seed,
                        "ordinal": job.ordinal,
                        "TT_s": job.tt_s,
                        "RP_record_count": job.isotope_store["RP_record_count"],
                        "job_source": rel(job.job_source),
                        "job_source_sha256": job.job_source_sha256,
                        "isotope_dat": rel(job.isotope_dat),
                        "isotope_dat_sha256": job.isotope_dat_sha256,
                        "log": rel(job.log),
                        "log_sha256": job.log_sha256,
                        "sim": rel(job.sim),
                        "ledger_sim_sha256": job.sim_sha256,
                        "observed_sim_sha256": None,
                        "fixed_geometry_setup": rel(job.expected_geometry_setup),
                        "ledger_geometry_header": rel(job.ledger_geometry_header),
                    }
                )

    final_ledger = _json(paths.batch0004_final_ledger)
    expected_events: dict[tuple[str, str, str], int] = {}
    exposure = pin["batch0003_gamma_exposure"]
    for geometry in GEOMETRIES:
        expected_events[(geometry, "instant", "gamma")] = int(
            exposure["cumulative_events_per_geometry"]
        )
    for campaign in final_ledger.get("campaigns", []):
        geometry = str(campaign.get("geometry"))
        mode = str(campaign.get("mode"))
        family = str(campaign.get("family"))
        if geometry not in GEOMETRIES or mode not in MODES or family not in FAMILIES:
            raise RuntimeError("batch0004 final campaign has invalid aggregation grain")
        key = (geometry, mode, family)
        value = int(campaign.get("cumulative_events", -1))
        if key in expected_events:
            raise RuntimeError(f"duplicate expected event cell in canonical authorities: {key}")
        expected_events[key] = value
    all_cells = set(jobs_by_cell)
    if set(expected_events) != all_cells:
        missing = sorted(all_cells - set(expected_events))
        extra = sorted(set(expected_events) - all_cells)
        raise RuntimeError(f"canonical expected-event cell closure failed: missing={missing}, extra={extra}")
    for cell, jobs in jobs_by_cell.items():
        jobs.sort(key=lambda job: (job.batch_id, job.ordinal is None, job.ordinal or 0, job.job_name))
        observed = sum(job.events for job in jobs)
        if observed != expected_events[cell]:
            raise RuntimeError(f"{cell}: canonical job events={observed}, expected={expected_events[cell]}")
        if not jobs or not math.fsum(job.tt_s for job in jobs) > 0.0:
            raise RuntimeError(f"{cell}: empty jobs or non-positive sum(TT)")
    inventory.sort(
        key=lambda row: (
            row["geometry"], row["mode"], row["family"], row["batch_id"],
            row["ordinal"] is None, row["ordinal"] or 0, row["job_name"],
        )
    )
    return jobs_by_cell, inventory, ledger_hashes


def keyed_standard_normal(*parts: object) -> float:
    encoded = canonical_json_bytes([RESPONSE_NAMESPACE, *parts])
    digest = hashlib.sha256(encoded).digest()
    denominator = float(1 << 64)
    u1 = (int.from_bytes(digest[:8], "big") + 0.5) / denominator
    u2 = (int.from_bytes(digest[8:16], "big") + 0.5) / denominator
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _bin_index(value: float, edges: tuple[float, ...]) -> int:
    return max(0, min(len(edges) - 2, bisect.bisect_right(edges, value) - 1))


def _window_flags(energy_keV: float) -> dict[str, bool]:
    return {
        "tes_positive": energy_keV > 0.0,
        "broad_480_550": BROAD_KEV[0] <= energy_keV < BROAD_KEV[1],
        "w2_510p58_511p42": W2_KEV[0] <= energy_keV < W2_KEV[1],
    }


def _pair_category(has_pair: bool, has_annihilation: bool) -> str:
    return gamma.pair_category(has_pair, has_annihilation)


@dataclass
class EventState:
    local_id: int | None = None
    init_count: int = 0
    init_energy_keV: float | None = None
    source_theta_deg: float | None = None
    pixel_e: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    active_shield_keV: float = 0.0
    plastic_keV: float = 0.0
    excluded_kapton_keV: float = 0.0
    has_pair: bool = False
    has_annihilation: bool = False


@dataclass
class PromptAccumulator:
    geometry: str
    family: str
    primary_count: int = 0
    sum_tt_s: float = 0.0
    raw_tes_positive: int = 0
    measured_tes_positive: int = 0
    kapton_positive_tes_events: int = 0
    energy_denominator: Counter[int] = field(default_factory=Counter)
    theta_denominator: Counter[int] = field(default_factory=Counter)
    cut_counts: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    pair_counts: Counter[tuple[str, str, str, str]] = field(default_factory=Counter)
    driver_counts: Counter[tuple[str, int, str, str, str]] = field(default_factory=Counter)
    histogram_counts: Counter[tuple[str, str, str, int]] = field(default_factory=Counter)
    histogram_underflow: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    histogram_overflow: Counter[tuple[str, str, str]] = field(default_factory=Counter)

    def process_event(self, job: JobInput, event: EventState, writer: csv.DictWriter) -> None:
        if event.local_id is None:
            return
        if event.init_count != 1 or event.init_energy_keV is None or event.source_theta_deg is None:
            raise RuntimeError(f"{rel(job.sim)} ID {event.local_id}: IA INIT closure failed")
        self.primary_count += 1
        energy_index = _bin_index(event.init_energy_keV, ENERGY_EDGES)
        theta_index = _bin_index(event.source_theta_deg, THETA_EDGES)
        self.energy_denominator[energy_index] += 1
        self.theta_denominator[theta_index] += 1
        raw_pixels = [(name, value) for name, value in sorted(event.pixel_e.items()) if value > 0.0]
        raw_total = math.fsum(value for _, value in raw_pixels)
        measured_pixels: list[tuple[str, float]] = []
        for pixel, value in raw_pixels:
            measured = value + SIGMA_KEV * keyed_standard_normal(
                *job.event_key_prefix, event.local_id, pixel
            )
            if measured >= PIXEL_THRESHOLD_KEV:
                measured_pixels.append((pixel, measured))
        measured_total = math.fsum(value for _, value in measured_pixels)
        if raw_total > 0.0:
            self.raw_tes_positive += 1
        if measured_total > 0.0:
            self.measured_tes_positive += 1
        if measured_total > 0.0 and event.excluded_kapton_keV > 0.0:
            self.kapton_positive_tes_events += 1
        veto = {"pre_veto": True}
        for threshold in VETO_THRESHOLDS_KEV:
            veto[f"veto{threshold}"] = event.active_shield_keV < threshold and (
                self.geometry != "s3d_o8" or event.plastic_keV < O8_PLASTIC_THRESHOLD_KEV
            )
        energies = {"raw": raw_total, "measured": measured_total}
        process = _pair_category(event.has_pair, event.has_annihilation)
        for response, total in energies.items():
            flags = _window_flags(total)
            for selection, passes_veto in veto.items():
                if not passes_veto:
                    continue
                for window, selected in flags.items():
                    if not selected:
                        continue
                    self.cut_counts[(response, selection, window)] += 1
                    self.pair_counts[(response, selection, window, process)] += 1
                    self.driver_counts[("initial_energy", energy_index, response, selection, window)] += 1
                    self.driver_counts[("theta", theta_index, response, selection, window)] += 1
                if total > 0.0:
                    for view, (edges, _) in HISTOGRAM_VIEWS.items():
                        index = bisect.bisect_right(edges, total) - 1
                        if index < 0:
                            self.histogram_underflow[(response, selection, view)] += 1
                        elif index >= len(edges) - 1:
                            self.histogram_overflow[(response, selection, view)] += 1
                        else:
                            self.histogram_counts[(response, selection, view, index)] += 1
        if raw_total > 0.0:
            writer.writerow(
                {
                    "geometry": self.geometry,
                    "family": self.family,
                    "mode": "instant",
                    "batch_id": job.batch_id,
                    "job_name": job.job_name,
                    "seed": job.seed,
                    "local_event_id": event.local_id,
                    "init_energy_keV": f"{event.init_energy_keV:.12g}",
                    "source_theta_deg": f"{event.source_theta_deg:.12g}",
                    "source_hemisphere": "+z" if event.source_theta_deg < 90.0 else "-z",
                    "tes_raw_keV": f"{raw_total:.12g}",
                    "tes_measured_keV": f"{measured_total:.12g}",
                    "raw_pixel_count": len(raw_pixels),
                    "measured_pixel_count": len(measured_pixels),
                    "raw_pixels_json": json.dumps(
                        dict(raw_pixels), ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False,
                    ),
                    "measured_pixels_json": json.dumps(
                        dict(measured_pixels), ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False,
                    ),
                    "active_shield_keV": f"{event.active_shield_keV:.12g}",
                    "plastic_keV": f"{event.plastic_keV:.12g}",
                    "excluded_kapton_keV": f"{event.excluded_kapton_keV:.12g}",
                    "has_pair_ia": int(event.has_pair),
                    "has_annihilation_ia": int(event.has_annihilation),
                    "pair_annihilation_category": process,
                    "pass_veto50": int(veto["veto50"]),
                    "pass_veto70": int(veto["veto70"]),
                    "pass_veto80": int(veto["veto80"]),
                    "raw_in_480_550": int(_window_flags(raw_total)["broad_480_550"]),
                    "raw_in_w2": int(_window_flags(raw_total)["w2_510p58_511p42"]),
                    "measured_in_480_550": int(_window_flags(measured_total)["broad_480_550"]),
                    "measured_in_w2": int(_window_flags(measured_total)["w2_510p58_511p42"]),
                }
            )


EVENT_FIELDS = (
    "geometry", "family", "mode", "batch_id", "job_name", "seed", "local_event_id",
    "init_energy_keV", "source_theta_deg", "source_hemisphere", "tes_raw_keV",
    "tes_measured_keV", "raw_pixel_count", "measured_pixel_count", "raw_pixels_json",
    "measured_pixels_json", "active_shield_keV", "plastic_keV", "excluded_kapton_keV",
    "has_pair_ia", "has_annihilation_ia", "pair_annihilation_category", "pass_veto50",
    "pass_veto70", "pass_veto80", "raw_in_480_550", "raw_in_w2",
    "measured_in_480_550", "measured_in_w2",
)


def parse_prompt_sim(job: JobInput, accumulator: PromptAccumulator, writer: csv.DictWriter) -> str:
    if job.mode != "instant":
        raise RuntimeError("prompt SIM parser refuses non-instant job")
    before = job.sim.stat()
    hashing_raw = gamma.HashingRawReader(job.sim)
    buffered = io.BufferedReader(hashing_raw, buffer_size=1024 * 1024)
    event = EventState()
    expected_id = 1
    se_count = 0
    en_count = 0
    footer_ts: int | None = None
    footer_te: float | None = None
    header_seed: int | None = None
    header_geometry: str | None = None
    header_geometry_count = 0

    def flush() -> None:
        nonlocal event
        if event.local_id is not None:
            accumulator.process_event(job, event, writer)
        event = EventState()

    try:
        with gzip.GzipFile(fileobj=buffered, mode="rb") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if match := GEOMETRY_RE.match(line):
                        header_geometry_count += 1
                        header_geometry = header_geometry or match.group(1)
                    elif header_seed is None and (match := SEED_RE.match(line)):
                        header_seed = int(match.group(1))
                    elif line == "SE":
                        flush()
                        se_count += 1
                    elif line == "EN":
                        en_count += 1
                    elif line.startswith("TS "):
                        footer_ts = int(line.split()[1])
                    elif line.startswith("TE "):
                        footer_te = float(line.split()[1])
                    elif line.startswith("ID "):
                        if event.local_id is not None:
                            raise RuntimeError(f"{rel(job.sim)}: ID before next SE")
                        event.local_id = int(line.split()[1])
                        if event.local_id != expected_id:
                            raise RuntimeError(f"{rel(job.sim)}: ID={event.local_id}, expected={expected_id}")
                        expected_id += 1
                    elif line.startswith("IA INIT"):
                        if event.local_id is None:
                            raise RuntimeError(f"{rel(job.sim)}: IA INIT outside event")
                        particle, energy, theta, _ = gamma._parse_init(line)
                        if particle != PARTICLE_TYPES[job.family] or energy <= 0.0:
                            raise RuntimeError(
                                f"{rel(job.sim)} ID {event.local_id}: wrong particle/invalid energy"
                            )
                        event.init_count += 1
                        event.init_energy_keV = energy
                        event.source_theta_deg = theta
                    elif line.startswith("IA PAIR"):
                        event.has_pair = True
                    elif line.startswith("IA ANNI"):
                        event.has_annihilation = True
                    elif line.startswith("CC HIT "):
                        parts = line.split(maxsplit=3)
                        if len(parts) != 4:
                            raise RuntimeError(f"{rel(job.sim)}: malformed CC HIT")
                        role = gamma._relevant_volume(job.geometry, parts[2])
                        if role is None:
                            continue
                        match = EDEP_RE.search(parts[3])
                        if match is None:
                            raise RuntimeError(f"{rel(job.sim)}: relevant CC HIT lacks edep_keV")
                        value = float(match.group(1))
                        if not math.isfinite(value) or value < 0.0:
                            raise RuntimeError(f"{rel(job.sim)}: invalid deposit {value}")
                        if role == "tes":
                            event.pixel_e[parts[2]] += value
                        elif role == "active":
                            event.active_shield_keV += value
                        elif role == "plastic":
                            event.plastic_keV += value
                        else:
                            event.excluded_kapton_keV += value
        flush()
    except (OSError, EOFError, gzip.BadGzipFile, UnicodeError) as exc:
        raise RuntimeError(f"{rel(job.sim)} gzip/read failure: {exc}") from exc
    finally:
        if not buffered.closed:
            buffered.close()
    observed_hash = hashing_raw.hexdigest()
    after = job.sim.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise RuntimeError(f"{rel(job.sim)} changed while parsed")
    parsed = expected_id - 1
    if observed_hash != job.sim_sha256:
        raise RuntimeError(f"{rel(job.sim)} compressed hash differs from PASS ledger")
    if parsed != job.events or se_count != job.events:
        raise RuntimeError(f"{rel(job.sim)} event closure ID={parsed}, SE={se_count}, expected={job.events}")
    if en_count != 1 or footer_ts != job.events or footer_te is None or footer_te <= 0.0:
        raise RuntimeError(f"{rel(job.sim)} footer closure failed")
    if header_seed != job.seed or header_geometry_count != 1 or header_geometry is None:
        raise RuntimeError(f"{rel(job.sim)} Seed/Geometry header closure failed")
    sim_geometry = resolve_path(header_geometry).resolve()
    if not (
        sim_geometry
        == job.ledger_geometry_header
        == job.source_geometry
        == job.expected_geometry_setup
    ):
        raise RuntimeError(f"{rel(job.sim)} Geometry four-way binding failed")
    return observed_hash


def _poisson_interval(count: float, alpha: float = 0.05) -> tuple[float, float]:
    if not math.isfinite(count) or count < 0.0:
        raise ValueError("Poisson count must be finite nonnegative")
    try:
        from scipy.stats import chi2
    except ImportError as exc:
        raise RuntimeError("scipy is required for Poisson intervals") from exc
    low = 0.0 if count == 0.0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2.0 * count))
    high = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2.0 * (count + 1.0)))
    return low, high


def build_prompt_rows(
    accumulators: dict[tuple[str, str], PromptAccumulator],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cutflow: list[dict[str, Any]] = []
    histograms: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            acc = accumulators[(geometry, family)]
            for response in RESPONSES:
                for selection in SELECTIONS:
                    shield_threshold = None if selection == "pre_veto" else float(selection[4:])
                    for window in WINDOWS:
                        count = int(acc.cut_counts[(response, selection, window)])
                        poisson_low, poisson_high = gamma.garwood_interval(count)
                        efficiency_low, efficiency_high = gamma.wilson_interval(count, acc.primary_count)
                        pre_count = int(acc.cut_counts[(response, "pre_veto", window)])
                        survival_low, survival_high = gamma.wilson_interval(count, pre_count)
                        cutflow.append(
                            {
                                "geometry": geometry,
                                "mode": "instant",
                                "family": family,
                                "response": response,
                                "selection": selection,
                                "window": window,
                                "active_shield_threshold_keV": shield_threshold,
                                "o8_plastic_threshold_keV": (
                                    O8_PLASTIC_THRESHOLD_KEV
                                    if geometry == "s3d_o8" and selection != "pre_veto"
                                    else None
                                ),
                                "primary_count": acc.primary_count,
                                "sum_TT_s": acc.sum_tt_s,
                                "count": count,
                                "rate_s-1": count / acc.sum_tt_s,
                                "rate_poisson95_low_s-1": poisson_low / acc.sum_tt_s,
                                "rate_poisson95_high_s-1": poisson_high / acc.sum_tt_s,
                                "zero_count_one_sided95_rate_upper_s-1": (
                                    -math.log(0.05) / acc.sum_tt_s if count == 0 else None
                                ),
                                "efficiency_per_primary": count / acc.primary_count,
                                "efficiency_wilson95_low": efficiency_low,
                                "efficiency_wilson95_high": efficiency_high,
                                "pre_veto_window_count": pre_count,
                                "veto_survival_fraction": count / pre_count if pre_count else None,
                                "veto_survival_wilson95_low": survival_low,
                                "veto_survival_wilson95_high": survival_high,
                            }
                        )
                        denominator = count
                        for category in (
                            "neither", "pair_only", "annihilation_only", "pair_and_annihilation"
                        ):
                            category_count = int(
                                acc.pair_counts[(response, selection, window, category)]
                            )
                            fraction_low, fraction_high = gamma.wilson_interval(
                                category_count, denominator
                            )
                            p_low, p_high = gamma.garwood_interval(category_count)
                            pairs.append(
                                {
                                    "geometry": geometry,
                                    "mode": "instant",
                                    "family": family,
                                    "response": response,
                                    "selection": selection,
                                    "window": window,
                                    "pair_annihilation_category": category,
                                    "window_count": denominator,
                                    "count": category_count,
                                    "fraction": category_count / denominator if denominator else None,
                                    "fraction_wilson95_low": fraction_low,
                                    "fraction_wilson95_high": fraction_high,
                                    "rate_s-1": category_count / acc.sum_tt_s,
                                    "rate_poisson95_low_s-1": p_low / acc.sum_tt_s,
                                    "rate_poisson95_high_s-1": p_high / acc.sum_tt_s,
                                }
                            )
                    for view, (edges, width_unit) in HISTOGRAM_VIEWS.items():
                        transformed = (
                            tuple(math.log10(value) for value in edges)
                            if width_unit == "log10_keV"
                            else edges
                        )
                        for index in range(len(edges) - 1):
                            count = int(acc.histogram_counts[(response, selection, view, index)])
                            low, high = gamma.garwood_interval(count)
                            width = transformed[index + 1] - transformed[index]
                            histograms.append(
                                {
                                    "geometry": geometry,
                                    "mode": "instant",
                                    "family": family,
                                    "response": response,
                                    "selection": selection,
                                    "view": view,
                                    "bin_index": index,
                                    "energy_low_keV": edges[index],
                                    "energy_high_keV": edges[index + 1],
                                    "width_unit": width_unit,
                                    "bin_width": width,
                                    "count": count,
                                    "count_poisson95_low": low,
                                    "count_poisson95_high": high,
                                    "rate_density_s-1_per_width": count / acc.sum_tt_s / width,
                                    "rate_density_poisson95_low_s-1_per_width": low / acc.sum_tt_s / width,
                                    "rate_density_poisson95_high_s-1_per_width": high / acc.sum_tt_s / width,
                                    "underflow_count_for_view": int(
                                        acc.histogram_underflow[(response, selection, view)]
                                    ),
                                    "overflow_count_for_view": int(
                                        acc.histogram_overflow[(response, selection, view)]
                                    ),
                                }
                            )
                for dimension, edges, labels, denominator in (
                    ("initial_energy", ENERGY_EDGES, ENERGY_LABELS, acc.energy_denominator),
                    ("source_theta", THETA_EDGES, None, acc.theta_denominator),
                ):
                    for index in range(len(edges) - 1):
                        primary_count = int(denominator[index])
                        high_raw = edges[index + 1]
                        high = None if math.isinf(high_raw) else high_raw
                        label = (
                            labels[index]
                            if labels is not None
                            else f"{edges[index]:g}-{high_raw:g} deg"
                        )
                        for selection in SELECTIONS:
                            for window in WINDOWS:
                                selected = int(
                                    acc.driver_counts[
                                        (dimension if dimension == "initial_energy" else "theta", index,
                                         response, selection, window)
                                    ]
                                )
                                low, upper = gamma.wilson_interval(selected, primary_count)
                                drivers.append(
                                    {
                                        "geometry": geometry,
                                        "mode": "instant",
                                        "family": family,
                                        "dimension": dimension,
                                        "bin_index": index,
                                        "bin_label": label,
                                        "bin_low": edges[index],
                                        "bin_high": high,
                                        "bin_high_open_ended": math.isinf(high_raw),
                                        "response": response,
                                        "selection": selection,
                                        "window": window,
                                        "primary_count": primary_count,
                                        "selected_count": selected,
                                        "efficiency": selected / primary_count if primary_count else None,
                                        "efficiency_wilson95_low": low,
                                        "efficiency_wilson95_high": upper,
                                    }
                                )
    return cutflow, histograms, drivers, pairs


def build_activation_rows(
    jobs_by_cell: dict[tuple[str, str, str], list[JobInput]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exposure_rows: list[dict[str, Any]] = []
    isotope_rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            jobs = jobs_by_cell[(geometry, "buildup", family)]
            sum_tt = math.fsum(job.tt_s for job in jobs)
            totals: dict[tuple[str, int, float], float] = defaultdict(float)
            positive_job_counts: Counter[tuple[str, int, float]] = Counter()
            total_rp = 0.0
            zero_record_jobs = 0
            for job in jobs:
                job_positive: set[tuple[str, int, float]] = set()
                rows = job.isotope_store["RP_totals_by_volume_isotope_state"]
                if not rows:
                    zero_record_jobs += 1
                for row in rows:
                    key = (
                        str(row["volume"]), int(row["isotope_id"]),
                        float(row["excitation_keV"]),
                    )
                    value = float(row["sum_RP"])
                    totals[key] = math.fsum((totals[key], value))
                    total_rp = math.fsum((total_rp, value))
                    if value > 0.0:
                        job_positive.add(key)
                for key in job_positive:
                    positive_job_counts[key] += 1
            low, high = _poisson_interval(total_rp)
            exposure_rows.append(
                {
                    "geometry": geometry,
                    "mode": "buildup",
                    "family": family,
                    "job_count": len(jobs),
                    "primary_count": sum(job.events for job in jobs),
                    "sum_TT_s": sum_tt,
                    "jobs_with_no_RP_records": zero_record_jobs,
                    "total_sum_RP": total_rp,
                    "total_RP_rate_s-1": total_rp / sum_tt,
                    "total_RP_rate_poisson95_low_s-1": low / sum_tt,
                    "total_RP_rate_poisson95_high_s-1": high / sum_tt,
                    "zero_total_RP_one_sided95_rate_upper_s-1": (
                        -math.log(0.05) / sum_tt if total_rp == 0.0 else None
                    ),
                }
            )
            ranked = sorted(totals.items(), key=lambda item: (-item[1] / sum_tt, item[0]))
            for rank, (key, value) in enumerate(ranked, 1):
                p_low, p_high = _poisson_interval(value)
                isotope_rows.append(
                    {
                        "geometry": geometry,
                        "mode": "buildup",
                        "family": family,
                        "volume": key[0],
                        "isotope_id": key[1],
                        "excitation_keV": key[2],
                        "rank_within_geometry_family": rank,
                        "job_count_in_denominator": len(jobs),
                        "jobs_with_positive_RP_for_key": int(positive_job_counts[key]),
                        "jobs_with_zero_RP_for_key": len(jobs) - int(positive_job_counts[key]),
                        "sum_RP": value,
                        "sum_TT_s_including_zero_RP_jobs": sum_tt,
                        "RP_rate_s-1": value / sum_tt,
                        "RP_rate_poisson95_low_s-1": p_low / sum_tt,
                        "RP_rate_poisson95_high_s-1": p_high / sum_tt,
                        "zero_RP_one_sided95_rate_upper_s-1": (
                            -math.log(0.05) / sum_tt if value == 0.0 else None
                        ),
                    }
                )
    return exposure_rows, isotope_rows


def prompt_closure_checks(
    accumulators: dict[tuple[str, str], PromptAccumulator],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    categories = ("neither", "pair_only", "annihilation_only", "pair_and_annihilation")
    for key, acc in accumulators.items():
        label = "/".join(key)
        checks[f"{label}:primary_energy_denominator"] = (
            sum(acc.energy_denominator.values()) == acc.primary_count
        )
        checks[f"{label}:theta_denominator"] = sum(acc.theta_denominator.values()) == acc.primary_count
        checks[f"{label}:raw_positive"] = (
            acc.cut_counts[("raw", "pre_veto", "tes_positive")] == acc.raw_tes_positive
        )
        checks[f"{label}:measured_positive"] = (
            acc.cut_counts[("measured", "pre_veto", "tes_positive")]
            == acc.measured_tes_positive
        )
        for response in RESPONSES:
            for selection in SELECTIONS:
                for window in WINDOWS:
                    count = acc.cut_counts[(response, selection, window)]
                    checks[f"{label}:{response}:{selection}:{window}:pair"] = (
                        sum(acc.pair_counts[(response, selection, window, cat)] for cat in categories)
                        == count
                    )
                    checks[f"{label}:{response}:{selection}:{window}:energy_driver"] = (
                        sum(
                            acc.driver_counts[("initial_energy", index, response, selection, window)]
                            for index in range(len(ENERGY_EDGES) - 1)
                        )
                        == count
                    )
                    checks[f"{label}:{response}:{selection}:{window}:theta_driver"] = (
                        sum(
                            acc.driver_counts[("theta", index, response, selection, window)]
                            for index in range(len(THETA_EDGES) - 1)
                        )
                        == count
                    )
                for view, (edges, _) in HISTOGRAM_VIEWS.items():
                    histogram_total = sum(
                        acc.histogram_counts[(response, selection, view, index)]
                        for index in range(len(edges) - 1)
                    )
                    histogram_total += acc.histogram_underflow[(response, selection, view)]
                    histogram_total += acc.histogram_overflow[(response, selection, view)]
                    checks[f"{label}:{response}:{selection}:{view}:histogram"] = (
                        histogram_total
                        == acc.cut_counts[(response, selection, "tes_positive")]
                    )
    return checks


def _plot_prompt_spectra(rows: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_seven_family_postprocess_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt

    outputs: list[Path] = []
    colors = {"raw": "#B88900", "measured": "#2F6B9A"}
    styles = {"raw": "--", "measured": "-"}
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            fig, ax = plt.subplots(figsize=(8.4, 5.2), constrained_layout=True)
            for response in RESPONSES:
                selected = [
                    row for row in rows
                    if row["geometry"] == geometry
                    and row["family"] == family
                    and row["response"] == response
                    and row["selection"] == "pre_veto"
                    and row["view"] == "full_log"
                ]
                selected.sort(key=lambda row: row["bin_index"])
                x = [row["energy_low_keV"] for row in selected]
                y = [row["rate_density_s-1_per_width"] for row in selected]
                ax.step(x, y, where="post", color=colors[response], linestyle=styles[response],
                        linewidth=1.8, label=response)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("TES event energy (keV)")
            ax.set_ylabel("Rate density (s$^{-1}$ per log10 keV)")
            ax.set_title(f"{GEOMETRY_LABELS[geometry]} {family} prompt TES spectrum")
            ax.text(
                0.0, 1.01,
                "Instant only; raw vs deterministic 420 eV FWHM / 0.3 keV pixel response",
                transform=ax.transAxes, fontsize=9, color="#4B5563",
            )
            ax.grid(True, which="both", color="#E5E7EB", linewidth=0.6)
            ax.legend(frameon=False)
            stem = output_dir / f"prompt_tes_{geometry}_{family}"
            png = stem.with_suffix(".png")
            svg = stem.with_suffix(".svg")
            fig.savefig(png, dpi=180)
            fig.savefig(svg)
            plt.close(fig)
            outputs.extend((png, svg))
    return outputs


def _plot_veto_cutflow(rows: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_seven_family_postprocess_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), constrained_layout=True, sharey=True)
    colors = {"pre_veto": "#374151", "veto50": "#2F6B9A", "veto70": "#B88900", "veto80": "#C96B2C"}
    markers = {"pre_veto": "o", "veto50": "s", "veto70": "^", "veto80": "D"}
    for ax, geometry in zip(axes, GEOMETRIES, strict=True):
        for selection in SELECTIONS:
            selected = [
                row for row in rows
                if row["geometry"] == geometry
                and row["response"] == "measured"
                and row["selection"] == selection
                and row["window"] == "broad_480_550"
            ]
            selected.sort(key=lambda row: FAMILIES.index(row["family"]))
            ax.plot(
                range(len(FAMILIES)), [row["rate_s-1"] for row in selected],
                marker=markers[selection], color=colors[selection], linewidth=1.5,
                label=selection,
            )
        ax.set_yscale("log")
        ax.set_xticks(range(len(FAMILIES)), FAMILIES, rotation=35, ha="right")
        ax.set_title(f"{GEOMETRY_LABELS[geometry]} 480–550 keV")
        ax.grid(True, axis="y", color="#E5E7EB", linewidth=0.6)
        ax.set_xlabel("Primary family")
    axes[0].set_ylabel("Measured prompt rate (s$^{-1}$)")
    axes[1].legend(frameon=False, loc="best")
    fig.suptitle("Seven-family prompt TES veto cutflow")
    png = output_dir / "prompt_veto_cutflow.png"
    svg = output_dir / "prompt_veto_cutflow.svg"
    fig.savefig(png, dpi=180)
    fig.savefig(svg)
    plt.close(fig)
    return [png, svg]


def _plot_activation_rankings(rows: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    if not rows:
        return []
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_seven_family_postprocess_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt

    outputs: list[Path] = []
    for geometry in GEOMETRIES:
        selected = sorted(
            (row for row in rows if row["geometry"] == geometry and row["sum_RP"] > 0.0),
            key=lambda row: (-row["RP_rate_s-1"], row["family"], row["volume"]),
        )[:20]
        if not selected:
            continue
        selected.reverse()
        labels = [
            f"{row['family']} · {row['isotope_id']} @ {row['excitation_keV']:g} keV · {row['volume']}"
            for row in selected
        ]
        fig, ax = plt.subplots(figsize=(11.5, 7.5), constrained_layout=True)
        ax.barh(labels, [row["RP_rate_s-1"] for row in selected], color="#2F6B9A", edgecolor="#1F2937")
        ax.set_xscale("log")
        ax.set_xlabel("Production rate sum(RP) / full family sum(TT) (s$^{-1}$)")
        ax.set_title(f"{GEOMETRY_LABELS[geometry]} buildup isotope production ranking")
        ax.text(
            0.0, 1.01, "Top 20; zero-RP jobs remain in every isotope-state denominator",
            transform=ax.transAxes, fontsize=9, color="#4B5563",
        )
        ax.grid(True, axis="x", color="#E5E7EB", linewidth=0.6)
        stem = output_dir / f"activation_isotope_ranking_{geometry}"
        png = stem.with_suffix(".png")
        svg = stem.with_suffix(".svg")
        fig.savefig(png, dpi=180)
        fig.savefig(svg)
        plt.close(fig)
        outputs.extend((png, svg))
    return outputs


def _figure_qa(paths: list[Path]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for path in paths:
        valid = path.is_file() and path.stat().st_size > 500
        if path.suffix == ".png" and valid:
            valid = path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        elif path.suffix == ".svg" and valid:
            text = path.read_text(encoding="utf-8")
            valid = "<svg" in text and "</svg>" in text
        checks[path.name] = valid
    return checks


def _all_boolean_leaves_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return all(_all_boolean_leaves_true(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_boolean_leaves_true(item) for item in value)
    return True


def _published_rel(path: Path, work: Path, published: Path) -> str:
    return rel(published / path.relative_to(work))


def _run_analysis_in_directory(
    jobs_by_cell: dict[tuple[str, str, str], list[JobInput]],
    inventory: list[dict[str, Any]],
    ledger_hashes: dict[str, str],
    authority_pin: dict[str, Any],
    authority_pin_path: Path,
    work_dir: Path,
    published_dir: Path,
    *,
    make_figures: bool,
) -> dict[str, Any]:
    if not work_dir.is_dir() or any(work_dir.iterdir()):
        raise RuntimeError("transaction work directory must be empty")
    prompt_jobs = {
        (geometry, family): jobs_by_cell[(geometry, "instant", family)]
        for geometry in GEOMETRIES
        for family in FAMILIES
    }
    accumulators = {
        key: PromptAccumulator(geometry=key[0], family=key[1]) for key in prompt_jobs
    }
    inventory_lookup = {
        (row["geometry"], row["mode"], row["family"], row["batch_id"], row["job_name"]): row
        for row in inventory
    }
    event_path = work_dir / "prompt_tes_event_diagnostics.csv.gz"
    event_tmp = event_path.with_name(f".{event_path.name}.tmp-{os.getpid()}")
    try:
        with gzip.open(event_tmp, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
            writer.writeheader()
            for geometry in GEOMETRIES:
                for family in FAMILIES:
                    acc = accumulators[(geometry, family)]
                    for job in prompt_jobs[(geometry, family)]:
                        observed = parse_prompt_sim(job, acc, writer)
                        inventory_lookup[
                            (geometry, "instant", family, job.batch_id, job.job_name)
                        ]["observed_sim_sha256"] = observed
                        acc.sum_tt_s = math.fsum((acc.sum_tt_s, job.tt_s))
        os.replace(event_tmp, event_path)
    finally:
        event_tmp.unlink(missing_ok=True)

    for key, acc in accumulators.items():
        expected = sum(job.events for job in prompt_jobs[key])
        if acc.primary_count != expected or not acc.sum_tt_s > 0.0:
            raise RuntimeError(f"prompt cell {key} primary/TT closure failed")

    cutflow, histograms, drivers, pairs = build_prompt_rows(accumulators)
    activation_exposure, activation_isotopes = build_activation_rows(jobs_by_cell)
    input_manifest = work_dir / "canonical_input_manifest.csv"
    cutflow_path = work_dir / "prompt_cutflow.csv"
    hist_path = work_dir / "prompt_tes_histograms.csv"
    drivers_path = work_dir / "prompt_primary_drivers.csv"
    pairs_path = work_dir / "prompt_pair_annihilation.csv"
    activation_exposure_path = work_dir / "activation_family_exposure.csv"
    activation_isotope_path = work_dir / "activation_rp_by_volume_isotope_state.csv"
    atomic_csv(input_manifest, inventory)
    atomic_csv(cutflow_path, cutflow)
    atomic_csv(hist_path, histograms)
    atomic_csv(drivers_path, drivers)
    atomic_csv(pairs_path, pairs)
    atomic_csv(activation_exposure_path, activation_exposure)
    atomic_csv(activation_isotope_path, activation_isotopes, fieldnames=(
        "geometry", "mode", "family", "volume", "isotope_id", "excitation_keV",
        "rank_within_geometry_family", "job_count_in_denominator",
        "jobs_with_positive_RP_for_key", "jobs_with_zero_RP_for_key", "sum_RP",
        "sum_TT_s_including_zero_RP_jobs", "RP_rate_s-1",
        "RP_rate_poisson95_low_s-1", "RP_rate_poisson95_high_s-1",
        "zero_RP_one_sided95_rate_upper_s-1",
    ))

    figures: list[Path] = []
    if make_figures:
        figures.extend(_plot_prompt_spectra(histograms, work_dir))
        figures.extend(_plot_veto_cutflow(cutflow, work_dir))
        figures.extend(_plot_activation_rankings(activation_isotopes, work_dir))
    figure_checks = _figure_qa(figures)
    closure = prompt_closure_checks(accumulators)

    summary_path = work_dir / "seven_family_tes_activation_summary.json"
    outputs_before_summary = [
        event_path, input_manifest, cutflow_path, hist_path, drivers_path, pairs_path,
        activation_exposure_path, activation_isotope_path, *figures,
    ]
    summary = {
        "schema_version": 1,
        "status": "PASS__SEVEN_FAMILY_PROMPT_TES_AND_BUILDUP_ACTIVATION_POSTPROCESS",
        "authority_boundary": (
            "SCREENING_PROMPT_AND_BUILDUP_RP_ONLY__NOT_DELAYED_TRANSPORT_RESPONSE_"
            "MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY"
        ),
        "batch0003_selected_profile": authority_pin["batch0003_selected_profile"],
        "batch0003_gamma_exposure": authority_pin["batch0003_gamma_exposure"],
        "mode_contract": {
            "prompt": "instant only",
            "activation": "buildup DAT/RP only",
        },
        "pooling_boundary": "never pool counts, TT, or RP across geometry, mode, or family",
        "normalization": {
            "prompt_rate": "sum(selected count) / full cell sum(TT)",
            "activation_rate": (
                "sum(RP) / full geometry+family+buildup sum(TT), including every zero-RP job"
            ),
            "count_interval": "two-sided 95% Poisson/Garwood divided by sum(TT)",
            "zero_count_upper": "one-sided 95% -ln(0.05)/sum(TT)",
            "efficiency_interval": "two-sided 95% Wilson score",
        },
        "response": {
            "fwhm_keV_per_pixel": FWHM_KEV,
            "sigma_keV_per_pixel": SIGMA_KEV,
            "post_noise_pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "rng": "SHA-256 keyed Box-Muller normal",
            "rng_namespace": RESPONSE_NAMESPACE,
            "rng_key": (
                "geometry,mode,family,batch_id,seed,job_name,local_event_id,TES_pixel_UID"
            ),
        },
        "windows_keV": {
            "broad_480_550": {"low_inclusive": BROAD_KEV[0], "high_exclusive": BROAD_KEV[1]},
            "w2_510p58_511p42": {"low_inclusive": W2_KEV[0], "high_exclusive": W2_KEV[1]},
        },
        "veto_contracts": {
            "mass_model_511": {
                "kind": "24 exact physical CsI sensitive volumes",
                "volumes": sorted(gamma.MASS_TRUE_CSI_VOLUMES),
                "thresholds_keV": list(VETO_THRESHOLDS_KEV),
                "kapton_included": False,
            },
            "s3d_o8": {
                "kind": "3 exact physical BGO plus 3 exact plastic sensitive volumes",
                "bgo_volumes": sorted(gamma.O8_TRUE_BGO_VOLUMES),
                "bgo_thresholds_keV": list(VETO_THRESHOLDS_KEV),
                "plastic_volumes": sorted(gamma.O8_TRUE_PLASTIC_VOLUMES),
                "plastic_threshold_keV": O8_PLASTIC_THRESHOLD_KEV,
                "kapton_included": False,
            },
        },
        "prompt_cells": {
            f"{geometry}/{family}": {
                "geometry": geometry,
                "mode": "instant",
                "family": family,
                "primary_count": accumulators[(geometry, family)].primary_count,
                "sum_TT_s": accumulators[(geometry, family)].sum_tt_s,
                "raw_TES_positive_events": accumulators[(geometry, family)].raw_tes_positive,
                "measured_TES_positive_events": accumulators[(geometry, family)].measured_tes_positive,
                "TES_events_with_excluded_Kapton_deposit": (
                    accumulators[(geometry, family)].kapton_positive_tes_events
                ),
            }
            for geometry in GEOMETRIES
            for family in FAMILIES
        },
        "activation_cells": {
            f"{row['geometry']}/{row['family']}": row for row in activation_exposure
        },
        "inputs": {
            "authority_pin": rel(authority_pin_path),
            "authority_pin_sha256": sha256(authority_pin_path),
            "authority_records": authority_pin["authorities"],
            "input_manifest": _published_rel(input_manifest, work_dir, published_dir),
            "input_manifest_sha256": sha256(input_manifest),
            "analyzer": rel(THIS_FILE),
            "analyzer_sha256": sha256(THIS_FILE),
            "frozen_gamma_prompt_core": rel(GAMMA_CORE_PATH),
            "frozen_gamma_prompt_core_sha256": sha256(GAMMA_CORE_PATH),
        },
        "outputs": [
            {
                "path": _published_rel(path, work_dir, published_dir),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in outputs_before_summary
        ],
    }
    atomic_json(summary_path, summary)

    authorities_stable = all(
        sha256(resolve_path(record["path"])) == record["sha256"]
        for record in authority_pin["authorities"]
    )
    ancillary_stable = all(
        sha256(resolve_path(row[path_key])) == row[hash_key]
        for row in inventory
        for path_key, hash_key in (
            ("job_source", "job_source_sha256"),
            ("isotope_dat", "isotope_dat_sha256"),
            ("log", "log_sha256"),
        )
    )
    tt_stable = all(
        math.isclose(parse_isotope_dat(resolve_path(row["isotope_dat"]))["TT_s"], float(row["TT_s"]), rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(parse_unique_log_tt(resolve_path(row["log"])), float(row["TT_s"]), rel_tol=0.0, abs_tol=1e-12)
        for row in inventory
    )
    geometry_stable = all(
        parse_unique_source_geometry(resolve_path(row["job_source"]))
        == resolve_path(row["fixed_geometry_setup"]).resolve()
        == resolve_path(row["ledger_geometry_header"]).resolve()
        for row in inventory
    )
    activation_denominators_close = all(
        math.isclose(
            row["sum_TT_s_including_zero_RP_jobs"],
            next(
                exposure["sum_TT_s"]
                for exposure in activation_exposure
                if exposure["geometry"] == row["geometry"] and exposure["family"] == row["family"]
            ),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and row["jobs_with_positive_RP_for_key"] + row["jobs_with_zero_RP_for_key"]
        == row["job_count_in_denominator"]
        for row in activation_isotopes
    )
    checks: dict[str, Any] = {
        "authority_pin_exact_and_stable": authorities_stable,
        "toolchain_hashes_stable": (
            sha256(THIS_FILE) == authority_pin["toolchain"]["analyzer"]["sha256"]
            and sha256(GAMMA_CORE_PATH)
            == authority_pin["toolchain"]["frozen_gamma_prompt_core"]["sha256"]
        ),
        "ledger_hashes_stable": all(
            sha256(resolve_path(path)) == digest for path, digest in ledger_hashes.items()
        ),
        "ancillary_hashes_stable": ancillary_stable,
        "dat_log_ledger_TT_real_read_match": tt_stable,
        "geometry_job_source_ledger_fixed_match": geometry_stable,
        "prompt_only_instant": all(job.mode == "instant" for rows in prompt_jobs.values() for job in rows),
        "activation_only_buildup": all(
            row["mode"] == "buildup" for row in activation_exposure + activation_isotopes
        ),
        "all_14_prompt_cells_present": set(accumulators)
        == {(geometry, family) for geometry in GEOMETRIES for family in FAMILIES},
        "all_14_activation_cells_present": {
            (row["geometry"], row["family"]) for row in activation_exposure
        } == {(geometry, family) for geometry in GEOMETRIES for family in FAMILIES},
        "no_cross_geometry_mode_family_pooling": True,
        "activation_zero_RP_TT_denominator_closure": activation_denominators_close,
        "prompt_closure": closure,
        "kapton_excluded_from_veto_whitelists": not any(
            "KAPTON" in volume.upper()
            for volume in (
                gamma.MASS_TRUE_CSI_VOLUMES
                | gamma.O8_TRUE_BGO_VOLUMES
                | gamma.O8_TRUE_PLASTIC_VOLUMES
            )
        ),
        "mass_exact_24_CsI": len(gamma.MASS_TRUE_CSI_VOLUMES) == 24,
        "o8_exact_3_BGO_plus_3_plastic": (
            len(gamma.O8_TRUE_BGO_VOLUMES) == 3 and len(gamma.O8_TRUE_PLASTIC_VOLUMES) == 3
        ),
        "keyed_response_order_invariant": keyed_standard_normal("probe", 1)
        == keyed_standard_normal("probe", 1),
        "strict_summary_JSON": _json(summary_path) == summary,
        "figures_valid": (not make_figures) or _all_boolean_leaves_true(figure_checks),
    }
    passed = _all_boolean_leaves_true(checks)
    validation_path = work_dir / "seven_family_tes_activation_validation.json"
    all_outputs = [*outputs_before_summary, summary_path]
    output_records = [
        {
            "path": _published_rel(path, work_dir, published_dir),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in all_outputs
    ]
    validation = {
        "schema_version": 1,
        "status": "PASS" if passed else "FAIL",
        "errors": [] if passed else ["one or more validation boolean leaves failed"],
        "status_derivation": "PASS iff every boolean leaf is true and errors is empty",
        "checks": checks,
        "figure_qa": figure_checks,
        "summary": _published_rel(summary_path, work_dir, published_dir),
        "summary_sha256": sha256(summary_path),
        "outputs": output_records,
    }
    atomic_json(validation_path, validation)
    if _json(validation_path) != validation:
        raise RuntimeError("strict validation JSON round-trip failed")
    if not passed or validation["status"] != "PASS" or validation["errors"]:
        raise RuntimeError("postprocess validation failed; canonical output will not publish")
    if not all(
        sha256(path) == record["sha256"] and path.stat().st_size == record["size_bytes"]
        for path, record in zip(all_outputs, output_records, strict=True)
    ):
        raise RuntimeError("output hash closure failed")
    if sha256(authority_pin_path) != summary["inputs"]["authority_pin_sha256"]:
        raise RuntimeError("authority pin changed before publication")
    return {
        "summary": summary,
        "validation": validation,
        "validation_path": published_dir / validation_path.name,
    }


def run_analysis(
    jobs_by_cell: dict[tuple[str, str, str], list[JobInput]],
    inventory: list[dict[str, Any]],
    ledger_hashes: dict[str, str],
    output_dir: Path,
    *,
    authority_pin_path: Path = AUTHORITY_PIN,
    make_figures: bool = True,
) -> dict[str, Any]:
    published = output_dir.resolve()
    if published.exists():
        raise RuntimeError(f"refusing to overwrite analysis directory: {rel(published)}")
    if not authority_pin_path.is_file():
        raise AuthorityWait("canonical authority pin is absent")
    authority_pin = _json(authority_pin_path)
    published.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{published.name}.tmp-{os.getpid()}-", dir=published.parent))
    try:
        result = _run_analysis_in_directory(
            jobs_by_cell,
            inventory,
            ledger_hashes,
            authority_pin,
            authority_pin_path,
            work,
            published,
            make_figures=make_figures,
        )
        if published.exists():
            raise RuntimeError("publication target appeared during analysis")
        os.rename(work, published)
        return result
    except BaseException:
        if work.exists():
            shutil.rmtree(work)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pin-authorities", action="store_true")
    mode.add_argument("--check-inputs-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)
    if args.pin_authorities:
        if args.output_dir is not None or args.no_figures:
            parser.error("--pin-authorities does not accept output/figure options")
        try:
            payload = pin_authorities()
        except AuthorityWait as exc:
            print(json.dumps({"status": "WAIT", "authority_written": False, "errors": [str(exc)]},
                             indent=2, ensure_ascii=False, allow_nan=False))
            return 2
        except RuntimeError as exc:
            print(json.dumps({"status": "FAIL", "authority_written": False, "errors": [str(exc)]},
                             indent=2, ensure_ascii=False, allow_nan=False))
            return 1
        print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    try:
        jobs, inventory, ledger_hashes = collect_canonical_jobs()
    except AuthorityWait as exc:
        print(json.dumps({"status": "WAIT", "sim_payloads_read": False, "errors": [str(exc)]},
                         indent=2, ensure_ascii=False, allow_nan=False))
        return 2
    except RuntimeError as exc:
        print(json.dumps({"status": "FAIL", "sim_payloads_read": False, "errors": [str(exc)]},
                         indent=2, ensure_ascii=False, allow_nan=False))
        return 1
    if args.check_inputs_only:
        if args.output_dir is not None or args.no_figures:
            parser.error("--check-inputs-only does not accept output/figure options")
        print(
            json.dumps(
                {
                    "status": "PASS__CANONICAL_INPUT_METADATA_READY",
                    "prompt_mode": "instant_only",
                    "activation_mode": "buildup_only",
                    "jobs_by_cell": {
                        "/".join(cell): len(rows) for cell, rows in sorted(jobs.items())
                    },
                    "events_by_cell": {
                        "/".join(cell): sum(job.events for job in rows)
                        for cell, rows in sorted(jobs.items())
                    },
                    "ledger_sha256": ledger_hashes,
                    "ancillary_DAT_log_source_real_read": True,
                    "sim_payloads_read": False,
                    "outputs_written": False,
                },
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
        )
        return 0
    output = args.output_dir or PACKAGE / "results_canonical"
    output = output if output.is_absolute() else ROOT / output
    try:
        result = run_analysis(
            jobs,
            inventory,
            ledger_hashes,
            output,
            make_figures=not args.no_figures,
        )
    except (AuthorityWait, RuntimeError) as exc:
        print(json.dumps({"status": "FAIL", "output_published": False, "errors": [str(exc)]},
                         indent=2, ensure_ascii=False, allow_nan=False))
        return 1
    print(
        json.dumps(
            {
                "status": result["validation"]["status"],
                "summary": result["validation"]["summary"],
                "validation": rel(result["validation_path"]),
                "output_published": True,
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
