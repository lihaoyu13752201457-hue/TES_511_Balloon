#!/usr/bin/env python3
"""Build the candidate-owned SF3 activation and delayed-source package.

The default/status actions are read-only and intentionally do not open SIM
payloads.  ``--prepare`` is the W3 action: it requires the complete validated
W2 background receipt set, parses every selected BUILDUP DAT, then performs one
semantic pass over each selected BUILDUP SIM to recover ``CC IP RP`` production
positions.  It never hashes a SIM and never launches transport.

Normalization and state policy are retained from the corrected M05 chain:

* each family uses q(state) = sum(RP(state)) / sum(TT(family));
* TT from every selected family DAT is retained, including zero-RP DAT;
* day-15 activity uses state-aware NUBASE-2020 half-lives;
* unresolved or excited states fail closed as explicit holdouts;
* positive ground states require exact RPIP support equal to catalog sum(RP);
* 50,000 activity-weighted exact-position draws are reduced by stride 5 to
  10,000 transport blocks, with every retained block flux multiplied by 5.

The eight registered source rows use the already registered delayed job seeds.
Positive-A15 rows are marked ``RUN_83334``; exact-zero rows are marked
``SKIP_ZERO_A15`` with no ``DecayRun.Source`` and a finite two-sided-95% upper
derived from buildup sum(TT).  No S3d inventory or delayed source is consumed.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import io
import json
import math
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

from sf3_plan1_common import (
    ACTIVE_VETO_VOLUMES,
    DELAYED_EVENTS,
    FAMILIES,
    GEOMETRY_AUTHORITIES,
    PACKAGE_ROOT,
    PASSIVE_W_DIAGNOSTIC_VOLUMES,
    PROFILE_ID,
    REPO_ROOT,
    RUN_ROOT,
    SF3_SETUP,
    active_prefix,
    read_job_plan,
    sha256,
    utc_now,
    write_once_text,
)


OUTPUT_ROOT = PACKAGE_ROOT / "outputs/02_activation"
DELAYED_CARD_ROOT = PACKAGE_ROOT / "config/delayed_source_cards"
ACTIVATION_VALIDATION = PACKAGE_ROOT / "audit/sf3_activation_validation.json"
BACKGROUND_VALIDATION = PACKAGE_ROOT / "audit/sf3_plan1_background_receipt_validation.json"
SOURCE_VALIDATION = PACKAGE_ROOT / "audit/sf3_plan1_source_validation.json"
JOB_PLAN_PATH = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
SEED_REGISTRY_PATH = PACKAGE_ROOT / "data/sf3_plan1_seed_registry.csv"
NUBASE = REPO_ROOT / "inputs/nubase/nubase_2020.txt"
NUBASE_SHA256 = "1585a5eea86c5e17e90307c7e6e786d060049c4039e392a261ff6db977df9859"

FLIGHT_DAYS = 15.0
ORIGINAL_POSITION_BLOCKS = 50_000
POSITION_STRIDE = 5
TRANSPORT_POSITION_BLOCKS = ORIGINAL_POSITION_BLOCKS // POSITION_STRIDE
MIN_RPIP_POINTS = 1
MONO_EPSILON_KEV = 1.0e-6
ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER = 3.6888794541139363
ZERO_A15_UPPER_PROVENANCE = (
    "two-sided 95% Garwood upper for zero transportable-ground RP: "
    "3.6888794541139363/sumTT; conservative day-15 saturation factor <= 1; "
    "known and unresolved holdout activity is reported separately"
)

INCLUDE_RE = re.compile(r"^\s*Include\s+(\S+)\s*$")
COPY_RE = re.compile(r"^\s*(?P<logical>\S+)\.Copy\s+(?P<physical>\S+)\s*$")
CC_RP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<volume>\S+)\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+"
    r"(?P<z>[-+0-9.eE]+)\s+(?P<za>\d+)\s+"
    r"(?P<exc>[-+0-9.eE]+)\s+(?P<t>[-+0-9.eE]+)"
)

UNIT_SECONDS = {
    "fs": 1.0e-15,
    "as": 1.0e-18,
    "zs": 1.0e-21,
    "ys": 1.0e-24,
    "ps": 1.0e-12,
    "ns": 1.0e-9,
    "us": 1.0e-6,
    "ms": 1.0e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": 31_557_600.0,
    "ky": 1.0e3 * 31_557_600.0,
    "My": 1.0e6 * 31_557_600.0,
    "Gy": 1.0e9 * 31_557_600.0,
    "Ty": 1.0e12 * 31_557_600.0,
    "Py": 1.0e15 * 31_557_600.0,
    "Ey": 1.0e18 * 31_557_600.0,
    "Zy": 1.0e21 * 31_557_600.0,
    "Yy": 1.0e24 * 31_557_600.0,
}


def load_json(path: Path) -> dict[str, Any]:
    def reject(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def json_text(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json_text(value), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def csv_text(rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def canonical_excitation(value: float | str) -> float:
    raw = Decimal(str(value)).quantize(Decimal("0.01"))
    return 0.0 if raw == 0 else float(raw)


def state_key(volume: str, za: int, excitation_keV: float | str) -> tuple[str, int, float]:
    return str(volume), int(za), canonical_excitation(excitation_keV)


def cast_plan_row(raw: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = dict(raw)
    for key in (
        "ordinal",
        "shard",
        "events",
        "s3d_histories",
        "target_histories",
        "seed",
        "estimated_bytes",
    ):
        row[key] = int(row[key])
    for key in ("paired_seed_exception", "production_canary"):
        row[key] = str(row[key]).strip().lower() == "true"
    return row


def plan_rows() -> list[dict[str, Any]]:
    return [cast_plan_row(row) for row in read_job_plan(JOB_PLAN_PATH)]


def receipt_path(job_id: str) -> Path:
    return RUN_ROOT / "receipts" / f"{job_id}.json"


def small_file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def geometry_contract_status() -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Validate only the small immutable SF3 geometry/role authorities."""
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    missing: list[str] = []
    if set(ACTIVE_VETO_VOLUMES) & set(PASSIVE_W_DIAGNOSTIC_VOLUMES):
        errors.append("passive W volumes overlap the frozen six-volume active veto contract")
    if len(ACTIVE_VETO_VOLUMES) != 6 or len(PASSIVE_W_DIAGNOSTIC_VOLUMES) != 3:
        errors.append("SF3 active/passive volume cardinality differs from 6/3")
    for name, path in GEOMETRY_AUTHORITIES.items():
        if not path.is_file():
            missing.append(str(path))
            continue
        try:
            payload = load_json(path)
            status = str(payload.get("status", ""))
            if not status.startswith("PASS"):
                errors.append(f"SF3 geometry authority is not PASS: {name}: {status}")
            if payload.get("transport_launched") not in (None, False):
                errors.append(f"SF3 geometry authority unexpectedly launched transport: {name}")
            records.append({
                "name": name,
                **small_file_record(path),
                "status": status,
            })
        except Exception as exc:
            errors.append(f"SF3 geometry authority unreadable: {name}: {exc}")
    return records, errors, missing


def validate_plan_and_registry() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan = plan_rows()
    errors: list[str] = []
    buildup = [row for row in plan if row["stage"] == "background" and row["mode"] == "buildup"]
    delayed = [row for row in plan if row["stage"] == "delayed"]
    if len(buildup) != 10:
        errors.append(f"buildup job count {len(buildup)} != 10")
    if len(delayed) != len(FAMILIES):
        errors.append(f"delayed job count {len(delayed)} != {len(FAMILIES)}")
    if Counter(row["family"] for row in buildup) != Counter({family: 1 for family in FAMILIES}) + Counter({"gamma": 2}):
        errors.append("buildup family/shard coverage differs from 1,1,1,3,1,1,1,1")
    if {row["family"] for row in delayed} != set(FAMILIES):
        errors.append("delayed family coverage differs from the eight-family contract")
    for row in buildup:
        if row["geometry"] != "SF3" or Path(row["setup_path"]).resolve() != SF3_SETUP.resolve():
            errors.append(f"non-SF3 buildup binding: {row['job_id']}")
    for row in delayed:
        expected_id = f"sf3_delayed_{row['family']}"
        expected_source = DELAYED_CARD_ROOT / f"{expected_id}.source"
        if row["job_id"] != expected_id:
            errors.append(f"delayed job id mismatch: {row['job_id']} != {expected_id}")
        if row["events"] != DELAYED_EVENTS:
            errors.append(f"delayed trigger mismatch: {row['job_id']}")
        if Path(row["source_path"]).resolve() != expected_source.resolve():
            errors.append(f"delayed source path mismatch: {row['job_id']}")
        if Path(row["setup_path"]).resolve() != SF3_SETUP.resolve():
            errors.append(f"delayed setup mismatch: {row['job_id']}")

    if not SEED_REGISTRY_PATH.is_file():
        errors.append(f"missing seed registry: {SEED_REGISTRY_PATH}")
    else:
        with SEED_REGISTRY_PATH.open(newline="", encoding="utf-8") as handle:
            registry = {row["job_id"]: row for row in csv.DictReader(handle)}
        for row in delayed:
            registered = registry.get(row["job_id"])
            if registered is None:
                errors.append(f"delayed seed is not registered: {row['job_id']}")
            elif int(registered["seed"]) != row["seed"] or registered["seed_identity"] != row["seed_identity"]:
                errors.append(f"delayed seed registry mismatch: {row['job_id']}")
            elif registered.get("collision_with_prior", "").lower() != "false":
                errors.append(f"delayed seed registry collision: {row['job_id']}")
    if len({int(row["seed"]) for row in delayed}) != len(delayed):
        errors.append("delayed transport seeds are not unique")
    if errors:
        raise RuntimeError("; ".join(errors))
    return buildup, delayed


def validate_receipt_against_plan(
    job: dict[str, Any],
    payload: dict[str, Any],
    *,
    verify_small_source: bool,
) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "PASS":
        errors.append("status is not PASS")
    if payload.get("profile_id") != PROFILE_ID:
        errors.append("profile_id mismatch")
    for key in ("job_id", "stage", "geometry", "mode", "family", "events", "seed", "source_path", "setup_path"):
        if payload.get(key) != job[key]:
            errors.append(f"{key}: receipt={payload.get(key)!r} plan={job[key]!r}")
    if payload.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
        errors.append("SIM digest policy mismatch")
    isotope = payload.get("isotope_dat") or {}
    if not isinstance(isotope.get("TT_s"), (int, float)) or float(isotope["TT_s"]) <= 0.0:
        errors.append("receipt TT is not positive")
    if not isinstance(isotope.get("RP_record_count"), int) or int(isotope["RP_record_count"]) < 0:
        errors.append("receipt RP_record_count is invalid")
    header = payload.get("sim_header") or {}
    try:
        if Path(str(header.get("geometry"))).resolve() != SF3_SETUP.resolve():
            errors.append("SIM header geometry is not SF3")
    except (OSError, TypeError):
        errors.append("SIM header geometry is invalid")
    if header.get("seed") != job["seed"]:
        errors.append("SIM header seed mismatch")
    for path_key, size_key in (
        ("sim_path", "sim_bytes"),
        ("isotope_dat_path", "isotope_dat_bytes"),
        ("log_path", "log_bytes"),
    ):
        try:
            artifact = Path(str(payload[path_key]))
            expected_size = int(payload[size_key])
            if not artifact.is_file() or artifact.stat().st_size != expected_size or expected_size <= 0:
                errors.append(f"artifact stat mismatch: {path_key}")
        except (KeyError, OSError, TypeError, ValueError):
            errors.append(f"artifact declaration invalid: {path_key}")
    if verify_small_source:
        try:
            source = Path(str(payload["source_path"]))
            if not source.is_file() or sha256(source) != payload.get("source_sha256"):
                errors.append("small source provenance mismatch")
        except (KeyError, OSError, TypeError):
            errors.append("small source provenance is invalid")
    return errors


def prerequisite_status() -> dict[str, Any]:
    missing: list[str] = []
    errors: list[str] = []
    buildup: list[dict[str, Any]] = []
    delayed: list[dict[str, Any]] = []
    try:
        buildup, delayed = validate_plan_and_registry()
    except Exception as exc:
        errors.append(f"plan/seed contract: {exc}")

    if not SF3_SETUP.is_file():
        missing.append(str(SF3_SETUP))
    geometry_authorities, geometry_errors, geometry_missing = geometry_contract_status()
    errors.extend(geometry_errors)
    missing.extend(geometry_missing)
    if not NUBASE.is_file():
        missing.append(str(NUBASE))
    elif sha256(NUBASE) != NUBASE_SHA256:
        errors.append("retained NUBASE-2020 hash mismatch")
    if not SOURCE_VALIDATION.is_file():
        missing.append(str(SOURCE_VALIDATION))
    else:
        try:
            source_validation = load_json(SOURCE_VALIDATION)
            if not str(source_validation.get("status", "")).startswith("PASS"):
                errors.append("source-level validation is not PASS")
            sources = source_validation.get("sources") or {}
            all_sf3 = sources.get(
                "all_generated_cards_use_SF3", sources.get("all_sf3_geometry")
            )
            legacy_references = sources.get(
                "legacy_references", sources.get("legacy_reference_count", -1)
            )
            if all_sf3 is not True or int(legacy_references) != 0:
                errors.append("source-level corrected-keV/SF3 boundary mismatch")
        except Exception as exc:
            errors.append(f"source validation unreadable: {exc}")

    validation_records: dict[str, str] = {}
    if not BACKGROUND_VALIDATION.is_file():
        missing.append(str(BACKGROUND_VALIDATION))
    else:
        try:
            validation = load_json(BACKGROUND_VALIDATION)
            if validation.get("status") != "PASS" or validation.get("scope") not in ("background", "all"):
                errors.append("W2 background validation is not PASS")
            validation_records = {
                str(row.get("job_id")): str(row.get("sha256"))
                for row in validation.get("receipt_records", [])
            }
        except Exception as exc:
            errors.append(f"background validation unreadable: {exc}")

    ready_receipts = 0
    receipt_rows: list[dict[str, Any]] = []
    for job in buildup:
        path = receipt_path(job["job_id"])
        if not path.is_file():
            missing.append(str(path))
            receipt_rows.append({"job_id": job["job_id"], "status": "MISSING", "path": str(path)})
            continue
        try:
            payload = load_json(path)
            receipt_errors = validate_receipt_against_plan(job, payload, verify_small_source=True)
            digest = sha256(path)
            if validation_records and validation_records.get(job["job_id"]) != digest:
                receipt_errors.append("receipt is absent from or differs from W2 validation")
            if receipt_errors:
                errors.extend(f"{job['job_id']}: {item}" for item in receipt_errors)
                status = "INVALID"
            else:
                ready_receipts += 1
                status = "PASS"
            receipt_rows.append({
                "job_id": job["job_id"],
                "status": status,
                "path": str(path),
                "sha256": digest,
                "sim_bytes": payload.get("sim_bytes"),
                "dat_bytes": payload.get("isotope_dat_bytes"),
                "TT_s": (payload.get("isotope_dat") or {}).get("TT_s"),
                "RP_record_count": (payload.get("isotope_dat") or {}).get("RP_record_count"),
            })
        except Exception as exc:
            errors.append(f"{job['job_id']}: receipt unreadable: {exc}")
            receipt_rows.append({"job_id": job["job_id"], "status": "INVALID", "path": str(path)})

    existing_manifest = OUTPUT_ROOT / "manifest.json"
    existing_status = None
    if existing_manifest.is_file():
        try:
            existing_status = load_json(existing_manifest).get("status")
        except Exception as exc:
            errors.append(f"existing activation manifest unreadable: {exc}")
    elif OUTPUT_ROOT.exists() and (
        not OUTPUT_ROOT.is_dir() or any(OUTPUT_ROOT.iterdir())
    ):
        errors.append(f"non-empty activation output exists without manifest: {OUTPUT_ROOT}")

    already_prepared = bool(
        existing_status == "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY"
        and all((DELAYED_CARD_ROOT / f"sf3_delayed_{family}.source").is_file() for family in FAMILIES)
    )
    ready = not missing and not errors and ready_receipts == len(buildup) and len(buildup) == 10
    if already_prepared:
        status = "PASS__SF3_W3_ALREADY_PREPARED"
    elif ready:
        status = "PASS__SF3_W3_PREREQUISITES_READY"
    else:
        status = "WAITING__SF3_W2_BUILDUP_RECEIPTS_OR_VALIDATION"
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "checked_at": utc_now(),
        "status": status,
        "ready": ready,
        "already_prepared": already_prepared,
        "missing": sorted(set(missing)),
        "errors": errors,
        "buildup_jobs_expected": len(buildup),
        "buildup_receipts_ready": ready_receipts,
        "delayed_jobs_registered": len(delayed),
        "receipt_status": receipt_rows,
        "background_validation": str(BACKGROUND_VALIDATION),
        "geometry_setup": str(SF3_SETUP.resolve()),
        "geometry_authorities": geometry_authorities,
        "detector_roles": {
            "active_veto_volumes": list(ACTIVE_VETO_VOLUMES),
            "passive_w_volumes": list(PASSIVE_W_DIAGNOSTIC_VOLUMES),
            "passive_w_active_veto_eligible": False,
        },
        "output_root": str(OUTPUT_ROOT),
        "delayed_card_root": str(DELAYED_CARD_ROOT),
        "sim_policy": "STATUS_DOES_NOT_OPEN_OR_HASH_SIM__PREPARE_DOES_ONE_SEMANTIC_CC_IP_RP_SCAN_AND_NO_SIM_HASH",
    }


def parse_dat_lines(lines: Iterable[str], label: str) -> dict[str, Any]:
    tt_values: list[float] = []
    records: list[dict[str, Any]] = []
    current_volume: str | None = None
    end_count = 0
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        kind = fields[0]
        if kind == "TT":
            if len(fields) != 2:
                raise RuntimeError(f"{label}:{line_number}: malformed TT")
            value = float(fields[1])
            if not math.isfinite(value) or value <= 0.0:
                raise RuntimeError(f"{label}:{line_number}: TT is not positive finite")
            tt_values.append(value)
        elif kind == "VN":
            current_volume = line[2:].strip()
            if not current_volume:
                raise RuntimeError(f"{label}:{line_number}: empty VN")
        elif kind == "RP":
            if len(fields) != 4 or current_volume is None:
                raise RuntimeError(f"{label}:{line_number}: malformed or orphan RP")
            isotope_id = int(fields[1])
            excitation = float(fields[2])
            value = float(fields[3])
            z, a = divmod(isotope_id, 1000)
            if (
                z <= 0
                or a <= 0
                or not math.isfinite(excitation)
                or excitation < 0.0
                or not math.isfinite(value)
                or value < 0.0
            ):
                raise RuntimeError(f"{label}:{line_number}: invalid RP")
            records.append({
                "volume": current_volume,
                "isotope_id": isotope_id,
                "excitation_keV": canonical_excitation(excitation),
                "RP": value,
            })
        elif kind == "EN" and len(fields) == 1:
            end_count += 1
        else:
            raise RuntimeError(f"{label}:{line_number}: unrecognized DAT record {kind!r}")
    if len(tt_values) != 1 or end_count != 1:
        raise RuntimeError(f"{label}: DAT closure TT={len(tt_values)}, EN={end_count}; expected 1/1")
    grouped: dict[tuple[str, int, float], list[float]] = defaultdict(list)
    for row in records:
        grouped[state_key(row["volume"], row["isotope_id"], row["excitation_keV"])].append(float(row["RP"]))
    totals = {key: math.fsum(values) for key, values in grouped.items()}
    return {
        "TT_s": tt_values[0],
        "RP_record_count": len(records),
        "sum_RP": math.fsum(float(row["RP"]) for row in records),
        "records": records,
        "totals": totals,
    }


def parse_dat(path: Path) -> dict[str, Any]:
    return parse_dat_lines(path.read_text(encoding="utf-8", errors="strict").splitlines(), str(path))


def parse_half_life(value: str, unit: str, context: str) -> float | None:
    if "stbl" in context.lower() or "stable" in context.lower():
        return math.inf
    cleaned = re.sub(r"[#?><~*&]", "", value).strip()
    try:
        number = float(cleaned)
    except ValueError:
        return None
    multiplier = UNIT_SECONDS.get(unit.strip()) or UNIT_SECONDS.get(unit.strip().lower())
    return None if multiplier is None else number * multiplier


def load_nubase_states(path: Path = NUBASE) -> dict[int, list[dict[str, Any]]]:
    if sha256(path) != NUBASE_SHA256:
        raise RuntimeError("retained NUBASE-2020 hash mismatch")
    states: dict[int, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.startswith("#") or len(line) < 90:
                continue
            try:
                mass = int(line[0:3].strip())
                zstate = line[4:8].strip()
                z = int(zstate[:3])
            except ValueError:
                continue
            state_designator = zstate[3:] if len(zstate) > 3 else "0"
            is_ground = state_designator in ("", "0")
            excitation: float | None
            if is_ground:
                excitation = 0.0
            else:
                cleaned = re.sub(r"[#?><~*&]", "", line[42:54]).strip()
                try:
                    excitation = float(cleaned)
                except ValueError:
                    excitation = None
            states[1000 * z + mass].append({
                "state_designator": state_designator or "0",
                "is_ground": is_ground,
                "excitation_keV": excitation,
                "half_life_s": parse_half_life(line[69:78], line[78:80], line[69:90]),
                "nubase_line": line_number,
                "raw_half_life": line[69:80].strip(),
            })
    return dict(states)


def match_nubase_state(
    table: dict[int, list[dict[str, Any]]],
    za: int,
    excitation_keV: float,
) -> tuple[dict[str, Any] | None, str]:
    records = table.get(int(za), [])
    if excitation_keV == 0.0:
        matches = [row for row in records if row["is_ground"]]
        return (matches[0], "NUBASE2020_ground") if len(matches) == 1 else (None, "missing_or_ambiguous_ground")
    matches = [
        row
        for row in records
        if not row["is_ground"]
        and row["excitation_keV"] is not None
        and abs(float(row["excitation_keV"]) - excitation_keV) <= 0.51
    ]
    if len(matches) == 1:
        return matches[0], "NUBASE2020_unique_isomer_energy_within_0.51keV"
    return None, "missing_or_ambiguous_explicit_excited_state"


def activity_from_rate(rate_s: float, half_life_s: float | None) -> float | None:
    if rate_s <= 0.0:
        return 0.0
    if half_life_s is None:
        return None
    if math.isinf(half_life_s):
        return 0.0
    if half_life_s <= 0.0:
        return None
    lambda_t = math.log(2.0) * FLIGHT_DAYS * 86400.0 / half_life_s
    return rate_s * (-math.expm1(-lambda_t))


def geometry_copy_map(setup: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited or not resolved.is_file():
            return
        visited.add(resolved)
        for raw in resolved.read_text(encoding="utf-8", errors="replace").splitlines():
            include = INCLUDE_RE.match(raw)
            if include:
                child = Path(include.group(1))
                if not child.is_absolute():
                    child = resolved.parent / child
                visit(child)
                continue
            copy = COPY_RE.match(raw)
            if not copy:
                continue
            logical, physical = copy.group("logical"), copy.group("physical")
            old = mapping.get(physical)
            if old is not None and old != logical:
                raise RuntimeError(f"conflicting geometry Copy mapping: {physical}: {old} vs {logical}")
            mapping[physical] = logical

    visit(setup)
    return mapping


def map_logical_volume(physical: str, logical: set[str], copies: dict[str, str]) -> str | None:
    candidates: set[str] = set()
    if physical in logical:
        candidates.add(physical)
    target = copies.get(physical)
    if target in logical:
        candidates.add(str(target))
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        raise RuntimeError(f"ambiguous logical-volume mapping for {physical}: {sorted(candidates)}")
    return None


def parse_rpip_file(
    path: Path,
    production_keys: set[tuple[str, int, float]],
    copy_map: dict[str, str],
) -> tuple[dict[tuple[str, int, float], list[tuple[float, float, float]]], dict[str, Any]]:
    logical = {key[0] for key in production_keys}
    excitations: dict[tuple[str, int], list[float]] = defaultdict(list)
    for volume, za, excitation in production_keys:
        if excitation not in excitations[(volume, za)]:
            excitations[(volume, za)].append(excitation)
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]] = defaultdict(list)
    unmatched_volumes: Counter[str] = Counter()
    unmatched_states: Counter[tuple[str, int, str]] = Counter()
    parsed_lines = 0
    malformed_lines = 0
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.startswith("CC IP RP "):
                continue
            match = CC_RP_RE.match(raw)
            if not match:
                malformed_lines += 1
                continue
            parsed_lines += 1
            physical = match.group("volume")
            volume = map_logical_volume(physical, logical, copy_map)
            if volume is None:
                unmatched_volumes[physical] += 1
                continue
            za = int(match.group("za"))
            raw_exc = Decimal(match.group("exc"))
            candidates = [
                value
                for value in excitations.get((volume, za), [])
                if abs(Decimal(str(value)) - raw_exc) <= Decimal("0.0050001")
            ]
            if len(candidates) != 1:
                unmatched_states[(volume, za, str(raw_exc))] += 1
                continue
            xyz = tuple(float(match.group(axis)) for axis in ("x", "y", "z"))
            if not all(math.isfinite(value) for value in xyz):
                raise RuntimeError(f"non-finite RPIP coordinate in {path}")
            points[state_key(volume, za, candidates[0])].append(xyz)  # type: ignore[arg-type]
    audit = {
        "sim_path": str(path.resolve()),
        "sim_bytes": path.stat().st_size,
        "sim_digest": None,
        "sim_scan_policy": "ONE_SEMANTIC_CC_IP_RP_PASS__NO_SIM_HASH",
        "CC_IP_RP_lines": parsed_lines,
        "malformed_CC_IP_RP_lines": malformed_lines,
        "matched_points": sum(len(values) for values in points.values()),
        "matched_state_keys": len(points),
        "unmatched_volume_points": sum(unmatched_volumes.values()),
        "unmatched_state_points": sum(unmatched_states.values()),
        "top_unmatched_volumes": unmatched_volumes.most_common(20),
        "top_unmatched_states": [
            {"volume": key[0], "ZA": key[1], "raw_excitation_keV": key[2], "points": count}
            for key, count in unmatched_states.most_common(20)
        ],
    }
    return dict(points), audit


def material_category(volume: str) -> str:
    upper = volume.upper()
    if upper.startswith("CSI_") or upper.startswith("BGO_"):
        return "active_scintillator"
    if "BPE" in upper:
        return "bpe_neutron_shield"
    if "PLASTIC" in upper:
        return "plastic_positron_veto"
    if upper.startswith("TP_") or upper.startswith("TES_"):
        return "tes"
    # The SF3 front plate contains "Window" in its name; tungsten identity
    # must take precedence over the generic window label.
    if "W_" in upper or "TUNGSTEN" in upper or volume.startswith("Passive_W"):
        return "passive_w_or_collimator"
    if "WINDOW" in upper:
        return "window"
    if "COLDPLATE" in upper:
        return "cold_plates"
    if "VACUUM_JACKET" in upper or "OUTER_" in upper or "OUTERSUPPORT" in upper:
        return "outer_mechanics"
    if "COLL" in upper or "XS400" in upper:
        return "passive_w_or_collimator"
    return "other_internal"


def classify_states(
    production_rows: list[dict[str, Any]],
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]],
    nubase: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    for row in production_rows:
        key = state_key(row["volume"], row["isotope_id"], row["excitation_keV"])
        rate = float(row["production_rate_s-1"])
        match, provenance = match_nubase_state(nubase, key[1], key[2])
        half_life_raw = None if match is None else match["half_life_s"]
        activity = activity_from_rate(rate, half_life_raw)
        half_life_json: float | str | None
        if half_life_raw is not None and math.isinf(float(half_life_raw)):
            half_life_json = "stable"
        else:
            half_life_json = half_life_raw
        record = {
            "volume": key[0],
            "ZA": key[1],
            "excitation_keV": key[2],
            "state_designator": None if match is None else match["state_designator"],
            "production_rate_s-1": rate,
            "sum_RP": float(row["sum_RP"]),
            "sum_TT_s": float(row["sum_TT_s_including_zero_RP_DAT"]),
            "day15_activity_Bq": activity,
            "half_life_s": half_life_json,
            "half_life_provenance": provenance,
            "nubase_line": None if match is None else match["nubase_line"],
            "RPIP_points": len(points.get(key, [])),
        }
        record["RPIP_minus_sum_RP"] = float(record["RPIP_points"]) - float(record["sum_RP"])
        if rate <= 0.0 or activity == 0.0:
            record["holdout_reason"] = "zero_day15_activity"
            holdout.append(record)
        elif activity is None:
            record["holdout_reason"] = "state_half_life_not_explicitly_resolved"
            holdout.append(record)
        elif key[2] != 0.0:
            record["holdout_reason"] = "installed_PointSource_cannot_encode_nonzero_excitation_without_state_collapse"
            holdout.append(record)
        elif not math.isclose(float(record["RPIP_points"]), float(record["sum_RP"]), rel_tol=0.0, abs_tol=1.0e-9):
            record["holdout_reason"] = "RPIP_support_count_does_not_equal_catalog_sum_RP"
            holdout.append(record)
        elif len(points.get(key, [])) < MIN_RPIP_POINTS:
            record["holdout_reason"] = "no_exact_RPIP_support"
            holdout.append(record)
        else:
            record["transport_state"] = "included_ground_state_exact_position"
            included.append(record)
    return included, holdout


def require_complete_positive_ground(family: str, holdout: list[dict[str, Any]]) -> None:
    unresolved = [
        row
        for row in holdout
        if row["excitation_keV"] == 0.0
        and row["production_rate_s-1"] > 0.0
        and row["day15_activity_Bq"] is None
    ]
    if unresolved:
        raise RuntimeError(f"SF3/{family}: positive ground-state half-life unresolved: {unresolved[:5]}")
    incomplete = [
        row
        for row in holdout
        if row["excitation_keV"] == 0.0
        and row["production_rate_s-1"] > 0.0
        and isinstance(row["day15_activity_Bq"], (int, float))
        and float(row["day15_activity_Bq"]) > 0.0
        and row.get("holdout_reason") in (
            "no_exact_RPIP_support",
            "RPIP_support_count_does_not_equal_catalog_sum_RP",
        )
    ]
    if incomplete:
        raise RuntimeError(f"SF3/{family}: positive ground-state RPIP support incomplete: {incomplete[:5]}")


def weighted_sample(
    included: list[dict[str, Any]],
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    population: list[tuple[dict[str, Any], tuple[float, float, float]]] = []
    weights: list[float] = []
    for row in included:
        key = state_key(row["volume"], row["ZA"], row["excitation_keV"])
        support = points[key]
        per_point = float(row["day15_activity_Bq"]) / len(support)
        for point in support:
            population.append((row, point))
            weights.append(per_point)
    total = math.fsum(weights)
    if not population or total <= 0.0:
        return []
    cdf: list[float] = []
    running = 0.0
    for weight in weights:
        running += weight
        cdf.append(running)
    rng = random.Random(seed)
    sampled: list[dict[str, Any]] = []
    for index in range(n):
        selected = bisect.bisect_left(cdf, rng.random() * running)
        state, xyz = population[min(selected, len(population) - 1)]
        sampled.append({
            "sample_index": index,
            "volume": state["volume"],
            "ZA": state["ZA"],
            "excitation_keV": state["excitation_keV"],
            "x_cm": xyz[0],
            "y_cm": xyz[1],
            "z_cm": xyz[2],
        })
    return sampled


def render_delayed_source(
    job: dict[str, Any],
    sampled: list[dict[str, Any]],
    total_activity: float,
) -> tuple[str, dict[str, Any]]:
    prefix = active_prefix(job["job_id"])
    retained = sampled[::POSITION_STRIDE]
    if sampled and (not math.isfinite(total_activity) or total_activity <= 0.0):
        raise RuntimeError(f"{job['job_id']}: non-positive activity has sampled source positions")
    if not sampled and total_activity != 0.0:
        raise RuntimeError(f"{job['job_id']}: positive activity lacks sampled source positions")
    if sampled and len(sampled) != ORIGINAL_POSITION_BLOCKS:
        raise RuntimeError(f"{job['job_id']}: original sample count {len(sampled)} != {ORIGINAL_POSITION_BLOCKS}")
    if sampled and len(retained) != TRANSPORT_POSITION_BLOCKS:
        raise RuntimeError(f"{job['job_id']}: retained block count {len(retained)} != {TRANSPORT_POSITION_BLOCKS}")
    original_flux = total_activity / ORIGINAL_POSITION_BLOCKS if sampled else 0.0
    transport_flux = original_flux * POSITION_STRIDE
    lines = [
        "# Candidate-owned SF3 day-15 exact-position delayed source",
        "# Built from validated SF3 BUILDUP DAT/SIM only; no S3d inventory is consumed.",
        f"# original_blocks={len(sampled)} stride={POSITION_STRIDE} retained_blocks={len(retained)}",
        f"# original_flux_Bq={original_flux:.17g} retained_flux_Bq={transport_flux:.17g}",
        "Version 1",
        f"Geometry {SF3_SETUP}",
        f"Seed {job['seed']}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {prefix}",
        f"DecayRun.Triggers {DELAYED_EVENTS}",
        "",
    ]
    if retained:
        lines.extend(f"DecayRun.Source RP_{int(row['sample_index']):07d}" for row in retained)
        lines.extend(("", "# Exact RPIP positions; nonzero excitation states are excluded upstream."))
        for row in retained:
            name = f"RP_{int(row['sample_index']):07d}"
            lines.extend([
                f"# state VN={row['volume']} ZA={row['ZA']} excitation_keV={float(row['excitation_keV']):.2f}",
                f"{name}.ParticleType {int(row['ZA'])}",
                f"{name}.Beam PointSource {float(row['x_cm']):.8g} {float(row['y_cm']):.8g} {float(row['z_cm']):.8g}",
                f"{name}.Spectrum Mono {MONO_EPSILON_KEV:.8g}",
                f"{name}.Flux {transport_flux:.17g}",
                "",
            ])
        status = "PASS__STRIDE5_M10000_DELAYED_SOURCE_READY"
        execution_disposition = "RUN_83334"
    else:
        lines.extend([
            "# ZERO_SOURCE_NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
            "# This card deliberately has no DecayRun.Source and must not be launched as a physics job.",
        ])
        status = "ZERO_SOURCE__NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY"
        execution_disposition = "SKIP_ZERO_A15"
    original_total = original_flux * len(sampled)
    transport_total = transport_flux * len(retained)
    original_closure = original_total - total_activity
    transport_closure = transport_total - total_activity
    if retained and not math.isclose(transport_total, total_activity, rel_tol=2.0e-15, abs_tol=1.0e-18):
        raise RuntimeError(f"{job['job_id']}: stride-5 flux closure failed: {transport_closure}")
    return "\n".join(lines) + "\n", {
        "status": status,
        "execution_disposition": execution_disposition,
        "original_blocks": len(sampled),
        "stride": POSITION_STRIDE,
        "transport_blocks": len(retained),
        "original_flux_per_block_Bq": original_flux,
        "transport_flux_per_block_Bq": transport_flux,
        "original_block_flux_Bq": original_flux,
        "transport_block_flux_Bq": transport_flux,
        "original_total_Bq": original_total,
        "transport_total_Bq": transport_total,
        "original_flux_sum_Bq": original_total,
        "transport_flux_sum_Bq": transport_total,
        "target_transport_activity_Bq": total_activity,
        "original_closure_Bq": original_closure,
        "transport_closure_Bq": transport_closure,
        "flux_closure_Bq": transport_closure,
        "flux_closure_relative": transport_closure / total_activity if total_activity > 0.0 else 0.0,
        "spectrum_epsilon_keV": MONO_EPSILON_KEV,
    }


def aggregate_known(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for family in FAMILIES:
        rows = [row for row in inventory if row["incident_family"] == family]
        known_all = math.fsum(float(row["day15_activity_Bq"]) for row in rows if row["day15_activity_Bq"] != "")
        transported = math.fsum(
            float(row["day15_activity_Bq"])
            for row in rows
            if row["day15_activity_Bq"] != "" and row["source_disposition"] == "transported_ground_state"
        )
        holdout = math.fsum(
            float(row["day15_activity_Bq"])
            for row in rows
            if row["day15_activity_Bq"] != "" and row["source_disposition"] != "transported_ground_state"
        )
        output.append({
            "geometry": "SF3",
            "incident_family": family,
            "state_rows": len(rows),
            "known_all_state_activity_Bq": known_all,
            "transported_ground_activity_Bq": transported,
            "known_holdout_activity_Bq": holdout,
            "unknown_state_count": sum(row["day15_activity_Bq"] == "" for row in rows),
        })
    return output


def passive_w_activation_lineage(
    inventory: list[dict[str, Any]],
    activation_cells: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Emit 3 x 8 explicit W rows, including true zero-production cells."""
    active = set(ACTIVE_VETO_VOLUMES)
    passive = tuple(PASSIVE_W_DIAGNOSTIC_VOLUMES)
    if active & set(passive):
        raise RuntimeError("passive W leaked into the active-veto contract")
    sum_tt_by_family = {
        str(row["incident_family"]): float(row["sum_TT_s"])
        for row in activation_cells
    }
    rows: list[dict[str, Any]] = []
    for volume in passive:
        for family in FAMILIES:
            states = [
                row for row in inventory
                if row["source_volume"] == volume and row["incident_family"] == family
            ]
            if any(row["material_category"] != "passive_w_or_collimator" for row in states):
                raise RuntimeError(f"W activation state has a non-passive material category: {volume}/{family}")
            known = [row for row in states if row["day15_activity_Bq"] != ""]
            transported = [
                row for row in known
                if row["source_disposition"] == "transported_ground_state"
            ]
            holdout = [
                row for row in known
                if row["source_disposition"] != "transported_ground_state"
            ]
            sum_tt = sum_tt_by_family[family]
            sum_rp = math.fsum(float(row["sum_RP"]) for row in states)
            rows.append({
                "geometry": "SF3",
                "source_volume": volume,
                "incident_family": family,
                "passive_role": "NEARFIELD_W_DIAGNOSTIC_ONLY",
                "active_veto_eligible": False,
                "state_rows": len(states),
                "sum_RP": sum_rp,
                "sum_TT_s": sum_tt,
                "production_rate_s-1": sum_rp / sum_tt,
                "known_day15_activity_Bq": math.fsum(
                    float(row["day15_activity_Bq"]) for row in known
                ),
                "transported_ground_activity_Bq": math.fsum(
                    float(row["day15_activity_Bq"]) for row in transported
                ),
                "known_holdout_activity_Bq": math.fsum(
                    float(row["day15_activity_Bq"]) for row in holdout
                ),
                "unknown_activity_state_count": sum(
                    row["day15_activity_Bq"] == "" for row in states
                ),
                "RPIP_support_count": sum(
                    int(row["RPIP_support_count"]) for row in states
                ),
            })
    if len(rows) != len(passive) * len(FAMILIES):
        raise RuntimeError("passive-W activation lineage does not close 3 volumes x 8 families")
    by_volume = []
    for volume in passive:
        selected = [row for row in rows if row["source_volume"] == volume]
        by_volume.append({
            "source_volume": volume,
            "family_rows": len(selected),
            "state_rows": sum(int(row["state_rows"]) for row in selected),
            "sum_RP": math.fsum(float(row["sum_RP"]) for row in selected),
            "known_day15_activity_Bq": math.fsum(
                float(row["known_day15_activity_Bq"]) for row in selected
            ),
            "transported_ground_activity_Bq": math.fsum(
                float(row["transported_ground_activity_Bq"]) for row in selected
            ),
            "known_holdout_activity_Bq": math.fsum(
                float(row["known_holdout_activity_Bq"]) for row in selected
            ),
            "unknown_activity_state_count": sum(
                int(row["unknown_activity_state_count"]) for row in selected
            ),
            "active_veto_eligible": False,
        })
    summary = {
        "schema_version": 1,
        "status": "PASS__SF3_PASSIVE_W_ACTIVATION_LINEAGE_COMPLETE",
        "geometry": "SF3",
        "expected_passive_w_volumes": list(passive),
        "explicit_family_rows": len(rows),
        "zero_production_family_rows": sum(float(row["sum_RP"]) == 0.0 for row in rows),
        "all_three_volumes_explicit_even_if_zero": True,
        "active_veto_eligible": False,
        "volume_summary": by_volume,
    }
    return rows, summary


def build_prepare_payload(
    staging_output: Path,
    staging_cards: Path,
    buildup_jobs: list[dict[str, Any]],
    delayed_jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    geometry_authorities, geometry_errors, geometry_missing = geometry_contract_status()
    if geometry_errors or geometry_missing:
        raise RuntimeError(
            f"SF3 geometry contract failed: errors={geometry_errors} missing={geometry_missing}"
        )
    nubase = load_nubase_states()
    copies = geometry_copy_map(SF3_SETUP)
    delayed_by_family = {row["family"]: row for row in delayed_jobs}

    parsed_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    input_rows: list[dict[str, Any]] = []
    dat_entries: list[dict[str, Any]] = []
    receipt_authorities: list[dict[str, Any]] = []
    for job in buildup_jobs:
        receipt_file = receipt_path(job["job_id"])
        receipt = load_json(receipt_file)
        errors = validate_receipt_against_plan(job, receipt, verify_small_source=True)
        if errors:
            raise RuntimeError(f"{job['job_id']}: receipt validation drift: {errors}")
        dat_path = Path(receipt["isotope_dat_path"])
        parsed = parse_dat(dat_path)
        declared = receipt["isotope_dat"]
        if not math.isclose(parsed["TT_s"], float(declared["TT_s"]), rel_tol=0.0, abs_tol=1.0e-12):
            raise RuntimeError(f"{job['job_id']}: DAT TT differs from receipt")
        if parsed["RP_record_count"] != int(declared["RP_record_count"]):
            raise RuntimeError(f"{job['job_id']}: DAT RP count differs from receipt")
        item = {
            "job": job,
            "receipt": receipt,
            "receipt_path": receipt_file,
            "dat_path": dat_path,
            "sim_path": Path(receipt["sim_path"]),
            "parsed_dat": parsed,
        }
        parsed_by_family[job["family"]].append(item)
        receipt_record = small_file_record(receipt_file)
        receipt_record["job_id"] = job["job_id"]
        receipt_authorities.append(receipt_record)
        dat_entries.append({
            "geometry": "SF3",
            "family": job["family"],
            "mode": "buildup",
            "job_id": job["job_id"],
            "events": job["events"],
            "seed": job["seed"],
            "receipt_path": str(receipt_file.resolve()),
            "receipt_sha256": receipt_record["sha256"],
            "dat_path": str(dat_path.resolve()),
            "dat_bytes": dat_path.stat().st_size,
            "dat_sha256": sha256(dat_path),
            "TT_s": parsed["TT_s"],
            "RP_record_count": parsed["RP_record_count"],
            "sum_RP": parsed["sum_RP"],
            "zero_RP": parsed["sum_RP"] == 0.0,
            "sim_reference": {
                "path": str(Path(receipt["sim_path"]).resolve()),
                "bytes": int(receipt["sim_bytes"]),
                "sha256": None,
                "policy": "RECEIPT_PATH_AND_SIZE_PLUS_ONE_SEMANTIC_RPIP_SCAN__NO_SIM_HASH",
            },
        })
        input_rows.append({
            "job_id": job["job_id"],
            "family": job["family"],
            "events": job["events"],
            "seed": job["seed"],
            "receipt_path": str(receipt_file.resolve()),
            "receipt_sha256": receipt_record["sha256"],
            "dat_path": str(dat_path.resolve()),
            "dat_sha256": dat_entries[-1]["dat_sha256"],
            "sim_path": str(Path(receipt["sim_path"]).resolve()),
            "sim_bytes": int(receipt["sim_bytes"]),
            "sim_sha256": "OMITTED_BY_CONTRACT",
            "TT_s": parsed["TT_s"],
            "RP_record_count": parsed["RP_record_count"],
            "sum_RP": parsed["sum_RP"],
            "zero_RP": parsed["sum_RP"] == 0.0,
        })

    activation_cells: list[dict[str, Any]] = []
    production_by_family: dict[str, list[dict[str, Any]]] = {}
    for family in FAMILIES:
        entries = parsed_by_family[family]
        sum_tt = math.fsum(float(item["parsed_dat"]["TT_s"]) for item in entries)
        if sum_tt <= 0.0:
            raise RuntimeError(f"SF3/{family}: non-positive family sum(TT)")
        state_values: dict[tuple[str, int, float], list[float]] = defaultdict(list)
        positive_dat: dict[tuple[str, int, float], set[str]] = defaultdict(set)
        for item in entries:
            for key, value in item["parsed_dat"]["totals"].items():
                state_values[key].append(float(value))
                if value > 0.0:
                    positive_dat[key].add(item["job"]["job_id"])
        production_rows: list[dict[str, Any]] = []
        for key, values in sorted(state_values.items()):
            sum_rp = math.fsum(values)
            za = int(key[1])
            z, a = divmod(za, 1000)
            production_rows.append({
                "geometry": "SF3",
                "family": family,
                "volume": key[0],
                "isotope_id": za,
                "Z": z,
                "A": a,
                "excitation_keV": key[2],
                "sum_RP": sum_rp,
                "sum_TT_s_including_zero_RP_DAT": sum_tt,
                "production_rate_s-1": sum_rp / sum_tt,
                "N_DAT_denominator": len(entries),
                "N_DAT_with_positive_RP_for_state": len(positive_dat[key]),
                "N_DAT_with_zero_RP_for_state": len(entries) - len(positive_dat[key]),
            })
        production_by_family[family] = production_rows
        sum_rp_cell = math.fsum(float(item["parsed_dat"]["sum_RP"]) for item in entries)
        activation_cells.append({
            "geometry": "SF3",
            "incident_family": family,
            "N_BUILDUP_files": len(entries),
            "generated_primaries": sum(int(item["job"]["events"]) for item in entries),
            "sum_TT_s": sum_tt,
            "sum_RP": sum_rp_cell,
            "production_rate_s-1": sum_rp_cell / sum_tt,
            "zero_RP_files": sum(float(item["parsed_dat"]["sum_RP"]) == 0.0 for item in entries),
            "cell_status": "PENDING_STATE_AND_RPIP_CLASSIFICATION",
        })

    all_points: dict[str, dict[tuple[str, int, float], list[tuple[float, float, float]]]] = {}
    scan_audits: list[dict[str, Any]] = []
    for family in FAMILIES:
        production_keys = {
            state_key(row["volume"], row["isotope_id"], row["excitation_keV"])
            for row in production_by_family[family]
        }
        family_points: dict[tuple[str, int, float], list[tuple[float, float, float]]] = defaultdict(list)
        for item in parsed_by_family[family]:
            points, audit = parse_rpip_file(item["sim_path"], production_keys, copies)
            audit.update({"job_id": item["job"]["job_id"], "family": family})
            scan_audits.append(audit)
            for key, values in points.items():
                family_points[key].extend(values)
        all_points[family] = dict(family_points)

    inventory: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    source_manifests: list[dict[str, Any]] = []
    state_summary: list[dict[str, Any]] = []
    staging_cards.mkdir(parents=True, exist_ok=False)
    sampled_root = staging_output / "exact_position_sources"
    sampled_root.mkdir(parents=True, exist_ok=False)
    card_payloads: dict[str, str] = {}
    for family in FAMILIES:
        job = delayed_by_family[family]
        rows = production_by_family[family]
        points = all_points[family]
        activation_cell = activation_cells[FAMILIES.index(family)]
        buildup_sum_tt_s = float(activation_cell["sum_TT_s"])
        included, holdout = classify_states(rows, points, nubase)
        require_complete_positive_ground(family, holdout)
        included_activity = math.fsum(float(row["day15_activity_Bq"]) for row in included)
        known_holdout_activity = math.fsum(
            float(row["day15_activity_Bq"])
            for row in holdout
            if row["day15_activity_Bq"] is not None
        )
        unknown_count = sum(row["day15_activity_Bq"] is None for row in holdout)
        sampled = weighted_sample(included, points, ORIGINAL_POSITION_BLOCKS, int(job["seed"]))
        if included_activity > 0.0 and len(sampled) != ORIGINAL_POSITION_BLOCKS:
            raise RuntimeError(f"SF3/{family}: failed to generate the 50k exact-position sample")
        family_dir = sampled_root / family
        family_dir.mkdir(parents=True, exist_ok=False)
        sampled_path = family_dir / "sampled_exact_positions_m50000.csv"
        sample_fields = ("sample_index", "volume", "ZA", "excitation_keV", "x_cm", "y_cm", "z_cm")
        write_csv(sampled_path, sampled, sample_fields)
        card_text, closure = render_delayed_source(job, sampled, included_activity)
        staged_card = staging_cards / f"{job['job_id']}.source"
        staged_card.write_text(card_text, encoding="utf-8")
        card_payloads[family] = card_text
        card_final = Path(job["source_path"])
        source_status = closure["status"]
        execution_disposition = closure["execution_disposition"]
        zero_count_upper = (
            ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER
            if execution_disposition == "SKIP_ZERO_A15"
            else None
        )
        transported_ground_rate_upper95 = (
            zero_count_upper / buildup_sum_tt_s
            if zero_count_upper is not None
            else None
        )
        transported_ground_a15_upper95 = transported_ground_rate_upper95
        activation_cell.update({
            "cell_status": source_status,
            "execution_disposition": execution_disposition,
            "transported_ground_activity_Bq": included_activity,
            "transported_ground_rate_upper95_s-1": transported_ground_rate_upper95,
            "transported_ground_A15_upper95_Bq_conservative": transported_ground_a15_upper95,
        })
        drawn = Counter((row["volume"], row["ZA"], row["excitation_keV"]) for row in sampled)
        family_scan = [row for row in scan_audits if row["family"] == family]
        source_manifest = {
            "schema_version": 1,
            "status": source_status,
            "execution_disposition": execution_disposition,
            "geometry": "SF3",
            "family": family,
            "job_id": job["job_id"],
            "source": str(card_final.resolve()),
            "source_sha256": hashlib.sha256(card_text.encode("utf-8")).hexdigest(),
            "sampled_positions_table": str((OUTPUT_ROOT / sampled_path.relative_to(staging_output)).resolve()),
            "geometry_path": str(SF3_SETUP.resolve()),
            "sampling_seed": int(job["seed"]),
            "transport_seed": int(job["seed"]),
            "registered_seed_identity": job["seed_identity"],
            "triggers_requested": DELAYED_EVENTS,
            "included_ground_activity_Bq": included_activity,
            "buildup_sum_TT_s": buildup_sum_tt_s,
            "zero_count_garwood_two_sided95_upper": zero_count_upper,
            "transported_ground_rate_upper95_s-1": transported_ground_rate_upper95,
            "transported_ground_A15_upper95_Bq_conservative": transported_ground_a15_upper95,
            "zero_A15_upper_provenance": (
                ZERO_A15_UPPER_PROVENANCE if zero_count_upper is not None else None
            ),
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_count,
            "included_states": included,
            "holdout_states": holdout,
            "sampled_state_counts": [
                {"volume": key[0], "ZA": key[1], "excitation_keV": key[2], "drawn": count}
                for key, count in drawn.most_common()
            ],
            "position_and_flux_closure": closure,
            "RPIP_audit": {
                "sim_files": len(family_scan),
                "CC_IP_RP_lines": sum(int(row["CC_IP_RP_lines"]) for row in family_scan),
                "matched_points": sum(int(row["matched_points"]) for row in family_scan),
                "unmatched_volume_points": sum(int(row["unmatched_volume_points"]) for row in family_scan),
                "unmatched_state_points": sum(int(row["unmatched_state_points"]) for row in family_scan),
                "files": family_scan,
            },
            "boundary": [
                "SF3-only corrected-keV BUILDUP receipts, DAT, and exact RPIP positions are consumed.",
                "All zero-RP DAT TT remains in the incident-family denominator.",
                "Nonzero excitation and unresolved NUBASE states are explicit fail-closed holdouts.",
                "The 10k transport mixture is every fifth element of the 50k draw and each retained flux is multiplied by five.",
                "This artifact is not delayed detector-rate, response, mission, F3, or geometry-promotion authority.",
            ],
        }
        write_json(family_dir / "source_manifest.json", source_manifest)
        source_manifests.append(source_manifest)
        source_index.append({
            "geometry": "SF3",
            "incident_family": family,
            "source_status": source_status,
            "execution_disposition": execution_disposition,
            "transported_ground_activity_Bq": included_activity,
            "buildup_sum_TT_s": buildup_sum_tt_s,
            "zero_count_garwood_two_sided95_upper": zero_count_upper if zero_count_upper is not None else "",
            "transported_ground_rate_upper95_s-1": (
                transported_ground_rate_upper95 if transported_ground_rate_upper95 is not None else ""
            ),
            "transported_ground_A15_upper95_Bq_conservative": (
                transported_ground_a15_upper95 if transported_ground_a15_upper95 is not None else ""
            ),
            "zero_A15_upper_provenance": (
                ZERO_A15_UPPER_PROVENANCE if zero_count_upper is not None else ""
            ),
            "upper_excludes_known_and_unresolved_holdout": True,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_count,
            "included_state_count": len(included),
            "holdout_state_count": len(holdout),
            "RPIP_points": sum(len(values) for values in points.values()),
            "pointsource_blocks": closure["transport_blocks"],
            "original_pointsource_blocks": closure["original_blocks"],
            "original_blocks": closure["original_blocks"],
            "transport_blocks": closure["transport_blocks"],
            "position_stride": POSITION_STRIDE,
            "requested_decay_triggers": DELAYED_EVENTS,
            "sampling_seed": int(job["seed"]),
            "transport_seed": int(job["seed"]),
            "flux_per_point_Bq": closure["transport_flux_per_block_Bq"] if sampled else "",
            "original_block_flux_Bq": closure["original_block_flux_Bq"] if sampled else "",
            "transport_block_flux_Bq": closure["transport_block_flux_Bq"] if sampled else "",
            "original_total_Bq": closure["original_total_Bq"],
            "transport_total_Bq": closure["transport_total_Bq"],
            "original_closure_Bq": closure["original_closure_Bq"],
            "transport_closure_Bq": closure["transport_closure_Bq"],
            "source_path": str(card_final.resolve()),
            "source_sha256": source_manifest["source_sha256"],
            "sampled_positions_path": source_manifest["sampled_positions_table"],
            "source_manifest_path": str((OUTPUT_ROOT / family_dir.relative_to(staging_output) / "source_manifest.json").resolve()),
        })
        for group, included_flag in ((included, True), (holdout, False)):
            for state in group:
                za = int(state["ZA"])
                activity = state["day15_activity_Bq"]
                inventory.append({
                    "geometry": "SF3",
                    "incident_family": family,
                    "source_volume": state["volume"],
                    "material_category": material_category(str(state["volume"])),
                    "source_parent_ZA": za,
                    "Z": za // 1000,
                    "A": za % 1000,
                    "excitation_keV": state["excitation_keV"],
                    "state_designator": state["state_designator"] if state["state_designator"] is not None else "",
                    "sum_RP": state["sum_RP"],
                    "sum_TT_s": state["sum_TT_s"],
                    "production_rate_s-1": state["production_rate_s-1"],
                    "half_life_s": state["half_life_s"] if state["half_life_s"] is not None else "",
                    "half_life_source": state["half_life_provenance"],
                    "day15_activity_Bq": activity if activity is not None else "",
                    "RPIP_support_count": state["RPIP_points"],
                    "source_disposition": (
                        "transported_ground_state"
                        if included_flag
                        else "stable_or_zero_activity"
                        if state.get("holdout_reason") == "zero_day15_activity"
                        else "excited_or_unresolved_holdout"
                    ),
                    "holdout_reason": state.get("holdout_reason", ""),
                })
        reason_counts = Counter(row.get("holdout_reason", "included_ground_state") for row in included + holdout)
        for reason, count in sorted(reason_counts.items()):
            selected_states = [row for row in included + holdout if row.get("holdout_reason", "included_ground_state") == reason]
            state_summary.append({
                "geometry": "SF3",
                "incident_family": family,
                "state_class": reason,
                "state_rows": count,
                "sum_RP": math.fsum(float(row["sum_RP"]) for row in selected_states),
                "known_day15_activity_Bq": math.fsum(
                    float(row["day15_activity_Bq"])
                    for row in selected_states
                    if row["day15_activity_Bq"] is not None
                ),
                "unknown_activity_state_count": sum(row["day15_activity_Bq"] is None for row in selected_states),
            })

    inventory.sort(key=lambda row: (FAMILIES.index(row["incident_family"]), row["source_volume"], row["source_parent_ZA"], row["excitation_keV"]))
    all_production_rows = [row for family in FAMILIES for row in production_by_family[family]]
    if len(inventory) != len(all_production_rows):
        raise RuntimeError("day-15 inventory does not cover every production-state row")
    family_summary = aggregate_known(inventory)
    w_lineage, w_summary = passive_w_activation_lineage(inventory, activation_cells)
    zero_source_families = [row["incident_family"] for row in source_index if str(row["source_status"]).startswith("ZERO_SOURCE")]
    catalog = {
        "schema_version": 1,
        "status": "PASS__SF3_CORRECTED_BUILDUP_CATALOG_READY",
        "authority_class": "SF3_CANDIDATE_OWN_CORRECTED_KEV_BUILDUP_DAT_AND_RICH_SIM_REFERENCE_CATALOG",
        "geometry": "SF3",
        "geometry_setup": str(SF3_SETUP.resolve()),
        "geometry_authorities": geometry_authorities,
        "mode": "buildup_only",
        "normalization": {
            "production_rate": "sum(RP) / sum(TT) within each SF3 x incident-family cell",
            "zero_RP_DAT_TT_retained": True,
            "state_key": "logical volume x ZA x excitation rounded to 0.01 keV",
        },
        "legacy_factor1000_included": False,
        "s3d_inventory_included": False,
        "dat_entries": dat_entries,
        "cells": activation_cells,
        "production_rows": all_production_rows,
        "sim_payload_policy": "ONE_CC_IP_RP_SEMANTIC_PASS_FOR_EXACT_POSITIONS__NO_SIM_HASH",
    }
    write_json(staging_output / "corrected_buildup_catalog.json", catalog)
    write_json(staging_output / "production_position_scan.json", {
        "schema_version": 1,
        "status": "PASS__SF3_RPIP_SEMANTIC_SCAN_COMPLETE",
        "sim_files_scanned": len(scan_audits),
        "sim_bytes_scanned_compressed": sum(int(row["sim_bytes"]) for row in scan_audits),
        "matched_points": sum(int(row["matched_points"]) for row in scan_audits),
        "files": scan_audits,
        "policy": "SEMANTIC_SCAN_ONLY__NO_SIM_DIGEST",
    })
    activation_fields = (
        "geometry", "incident_family", "N_BUILDUP_files", "generated_primaries", "sum_TT_s",
        "sum_RP", "production_rate_s-1", "zero_RP_files", "cell_status",
        "execution_disposition", "transported_ground_activity_Bq",
        "transported_ground_rate_upper95_s-1", "transported_ground_A15_upper95_Bq_conservative",
    )
    inventory_fields = (
        "geometry", "incident_family", "source_volume", "material_category", "source_parent_ZA",
        "Z", "A", "excitation_keV", "state_designator", "sum_RP", "sum_TT_s",
        "production_rate_s-1", "half_life_s", "half_life_source", "day15_activity_Bq",
        "RPIP_support_count", "source_disposition", "holdout_reason",
    )
    source_fields = (
        "geometry", "incident_family", "source_status", "execution_disposition",
        "transported_ground_activity_Bq", "buildup_sum_TT_s",
        "zero_count_garwood_two_sided95_upper", "transported_ground_rate_upper95_s-1",
        "transported_ground_A15_upper95_Bq_conservative", "zero_A15_upper_provenance",
        "upper_excludes_known_and_unresolved_holdout",
        "known_holdout_activity_Bq", "unknown_activity_state_count", "included_state_count",
        "holdout_state_count", "RPIP_points", "pointsource_blocks", "original_pointsource_blocks",
        "original_blocks", "transport_blocks", "position_stride", "requested_decay_triggers",
        "sampling_seed", "transport_seed", "flux_per_point_Bq", "original_block_flux_Bq",
        "transport_block_flux_Bq", "original_total_Bq", "transport_total_Bq",
        "original_closure_Bq", "transport_closure_Bq", "source_path", "source_sha256", "sampled_positions_path",
        "source_manifest_path",
    )
    write_csv(staging_output / "activation_cells.csv", activation_cells, activation_fields)
    write_csv(staging_output / "day15_inventory.csv", inventory, inventory_fields)
    write_csv(staging_output / "delayed_source_index.csv", source_index, source_fields)
    write_csv(
        staging_output / "passive_w_activation_lineage.csv",
        w_lineage,
        (
            "geometry", "source_volume", "incident_family", "passive_role",
            "active_veto_eligible", "state_rows", "sum_RP", "sum_TT_s",
            "production_rate_s-1", "known_day15_activity_Bq",
            "transported_ground_activity_Bq", "known_holdout_activity_Bq",
            "unknown_activity_state_count", "RPIP_support_count",
        ),
    )
    write_json(staging_output / "passive_w_activation_summary.json", w_summary)
    write_csv(
        staging_output / "state_holdout_summary.csv",
        state_summary,
        ("geometry", "incident_family", "state_class", "state_rows", "sum_RP", "known_day15_activity_Bq", "unknown_activity_state_count"),
    )
    write_csv(
        staging_output / "buildup_input_manifest.csv",
        input_rows,
        ("job_id", "family", "events", "seed", "receipt_path", "receipt_sha256", "dat_path", "dat_sha256", "sim_path", "sim_bytes", "sim_sha256", "TT_s", "RP_record_count", "sum_RP", "zero_RP"),
    )

    summary = {
        "schema_version": 1,
        "status": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
        "scope": "SF3 corrected-keV BUILDUP production, day-15 state inventory, and exact-position delayed-source preparation",
        "geometry": "SF3",
        "geometry_setup": str(SF3_SETUP.resolve()),
        "geometry_authorities": geometry_authorities,
        "detector_roles": {
            "active_veto_volumes": list(ACTIVE_VETO_VOLUMES),
            "passive_w_volumes": list(PASSIVE_W_DIAGNOSTIC_VOLUMES),
            "passive_w_active_veto_eligible": False,
        },
        "selected_buildup_jobs": len(buildup_jobs),
        "selected_buildup_histories": sum(int(row["events"]) for row in buildup_jobs),
        "sum_RP": math.fsum(float(row["sum_RP"]) for row in activation_cells),
        "sum_TT_s": math.fsum(float(row["sum_TT_s"]) for row in activation_cells),
        "production_state_rows": len(inventory),
        "matched_RPIP_points": sum(int(row["matched_points"]) for row in scan_audits),
        "positive_transport_source_cells": len(FAMILIES) - len(zero_source_families),
        "zero_source_cells": len(zero_source_families),
        "zero_source_families": zero_source_families,
        "zero_source_upper_limits": [
            {
                "family": row["incident_family"],
                "buildup_sum_TT_s": row["buildup_sum_TT_s"],
                "zero_count_garwood_two_sided95_upper": row["zero_count_garwood_two_sided95_upper"],
                "transported_ground_rate_upper95_s-1": row["transported_ground_rate_upper95_s-1"],
                "transported_ground_A15_upper95_Bq_conservative": row[
                    "transported_ground_A15_upper95_Bq_conservative"
                ],
                "provenance": row["zero_A15_upper_provenance"],
                "known_holdout_activity_Bq_reported_separately": row["known_holdout_activity_Bq"],
                "unknown_holdout_state_count_reported_separately": row["unknown_activity_state_count"],
            }
            for row in source_index
            if row["execution_disposition"] == "SKIP_ZERO_A15"
        ],
        "delayed_cards_written": len(FAMILIES),
        "registered_delayed_source_cells": len(FAMILIES),
        "delayed_transport_jobs_planned": len(FAMILIES) - len(zero_source_families),
        "delayed_zero_source_jobs_skipped": len(zero_source_families),
        "delayed_triggers_per_family": DELAYED_EVENTS,
        "delayed_triggers_total_planned": DELAYED_EVENTS * (len(FAMILIES) - len(zero_source_families)),
        "day15_by_family": family_summary,
        "passive_w_activation": w_summary,
        "normalization": "sum(RP)/sum(TT) per SF3 incident family; all zero-RP DAT TT included",
        "state_policy": "NUBASE-2020 state-aware; nonzero excitation and unresolved states fail closed",
        "source_mixture_policy": "50k deterministic exact-position draws; stride 5 to 10k; retained flux multiplied by 5",
        "sim_policy": "one required semantic CC IP RP scan; no SIM digest",
        "authority_boundary": "ACTIVATION_AND_DELAYED_SOURCE_PREPARATION_ONLY__NO_DELAYED_TRANSPORT_RATE_RESPONSE_MISSION_F3_OR_PROMOTION_AUTHORITY",
    }
    write_json(staging_output / "day15_summary.json", summary)
    manifest = {
        **summary,
        "manifest_status": summary["status"],
        "created_at": utc_now(),
        "output_root": str(OUTPUT_ROOT.resolve()),
        "background_validation": small_file_record(BACKGROUND_VALIDATION),
        "source_validation": small_file_record(SOURCE_VALIDATION),
        "job_plan": small_file_record(JOB_PLAN_PATH),
        "seed_registry": small_file_record(SEED_REGISTRY_PATH),
        "geometry_setup_authority": small_file_record(SF3_SETUP),
        "geometry_authorities": geometry_authorities,
        "nubase": small_file_record(NUBASE),
        "receipt_authorities": receipt_authorities,
        "source_cells": source_manifests,
        "passive_w_activation_lineage": small_file_record(
            staging_output / "passive_w_activation_lineage.csv"
        ),
        "passive_w_activation_summary": small_file_record(
            staging_output / "passive_w_activation_summary.json"
        ),
    }
    write_json(staging_output / "manifest.json", manifest)
    report = (
        "# SF3 candidate-owned activation and delayed-source preparation\n\n"
        f"Status: {summary['status']}\n\n"
        f"The package consumes {len(buildup_jobs)} validated SF3 BUILDUP jobs and "
        f"{summary['selected_buildup_histories']:,} generated primaries. Production is normalized "
        "inside each incident family as sum(RP)/sum(TT), retaining TT from zero-RP DAT.\n\n"
        f"It contains {len(inventory):,} state rows and {summary['matched_RPIP_points']:,} matched exact "
        "production positions. Every positive family source starts from 50,000 deterministic draws, "
        "retains indices 0,5,...,49995, and multiplies block flux by five for 10,000-block closure. "
        f"The {summary['delayed_transport_jobs_planned']} positive-A15 cells each request "
        f"{DELAYED_EVENTS:,} triggers and use their registered job seeds; "
        f"{summary['delayed_zero_source_jobs_skipped']} zero-A15 cells remain registered but are not launched. "
        "Every zero source carries a two-sided 95% 3.688879/sumTT upper-rate and a conservative "
        "saturation-factor<=1 A15 upper; known and unresolved holdouts remain separate.\n\n"
        "The SIM inputs were read once for CC IP RP semantics and were not hashed. This stage is not "
        "detector-selected delayed-rate, common-response, mission, F3, or geometry-promotion authority.\n"
    )
    (staging_output / "REPORT.md").write_text(report, encoding="utf-8")
    return {"summary": summary, "card_payloads": card_payloads, "manifest": manifest}


def prepare() -> dict[str, Any]:
    status = prerequisite_status()
    if status["already_prepared"]:
        manifest = load_json(OUTPUT_ROOT / "manifest.json")
        publish_activation_validation(manifest)
        return manifest
    if not status["ready"]:
        raise RuntimeError(json.dumps(status, indent=2, ensure_ascii=False))
    buildup_jobs, delayed_jobs = validate_plan_and_registry()
    work = PACKAGE_ROOT / f".sf3_activation_work_{os.getpid()}"
    output_is_empty_directory = (
        OUTPUT_ROOT.is_dir() and not any(OUTPUT_ROOT.iterdir())
    )
    if work.exists() or (OUTPUT_ROOT.exists() and not output_is_empty_directory):
        raise RuntimeError(f"write-once activation target/work path already exists: {OUTPUT_ROOT if OUTPUT_ROOT.exists() else work}")
    staging_output = work / "02_activation"
    staging_cards = work / "delayed_source_cards"
    work.mkdir(parents=True, exist_ok=False)
    staging_output.mkdir(parents=True, exist_ok=False)
    try:
        built = build_prepare_payload(staging_output, staging_cards, buildup_jobs, delayed_jobs)
        for family in FAMILIES:
            final = DELAYED_CARD_ROOT / f"sf3_delayed_{family}.source"
            write_once_text(final, built["card_payloads"][family])
        OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
        if output_is_empty_directory:
            OUTPUT_ROOT.rmdir()
        os.replace(staging_output, OUTPUT_ROOT)
        manifest = load_json(OUTPUT_ROOT / "manifest.json")
        publish_activation_validation(manifest)
        return manifest
    finally:
        if work.exists():
            shutil.rmtree(work)


def publish_activation_validation(manifest: dict[str, Any]) -> dict[str, Any]:
    """Publish the deterministic small W4 gate after cards and stage02 exist."""
    semantic_status = str(manifest.get("status", ""))
    if semantic_status != "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY":
        raise RuntimeError(f"activation manifest semantic status is not ready: {semantic_status}")
    manifest_path = OUTPUT_ROOT / "manifest.json"
    summary_path = OUTPUT_ROOT / "day15_summary.json"
    index_path = OUTPUT_ROOT / "delayed_source_index.csv"
    w_lineage_path = OUTPUT_ROOT / "passive_w_activation_lineage.csv"
    w_summary_path = OUTPUT_ROOT / "passive_w_activation_summary.json"
    for path in (manifest_path, summary_path, index_path, w_lineage_path, w_summary_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"activation validation input missing/empty: {path}")
    with index_path.open(newline="", encoding="utf-8") as handle:
        index_rows = list(csv.DictReader(handle))
    selected: dict[str, dict[str, str]] = {}
    for row in index_rows:
        if row.get("geometry") != "SF3":
            continue
        family = str(row.get("incident_family", ""))
        if family in selected:
            raise RuntimeError(f"duplicate activation source-index row: {family}")
        selected[family] = row
    if set(selected) != set(FAMILIES):
        raise RuntimeError(f"activation source-index family closure mismatch: {sorted(set(selected) ^ set(FAMILIES))}")
    delayed_jobs = {
        row["family"]: row
        for row in plan_rows()
        if row["stage"] == "delayed" and row["mode"] == "delayed"
    }
    card_records: list[dict[str, Any]] = []
    for family in FAMILIES:
        job = delayed_jobs[family]
        row = selected[family]
        card = Path(job["source_path"])
        if not card.is_file() or card.stat().st_size <= 0:
            raise RuntimeError(f"delayed source card missing/empty: {card}")
        text = card.read_text(encoding="utf-8", errors="strict")
        if text.count(f"Geometry {SF3_SETUP}") != 1:
            raise RuntimeError(f"delayed source geometry binding mismatch: {family}")
        if text.count(f"Seed {job['seed']}") != 1:
            raise RuntimeError(f"delayed source seed binding mismatch: {family}")
        if text.count(f"DecayRun.Triggers {DELAYED_EVENTS}") != 1:
            raise RuntimeError(f"delayed source trigger binding mismatch: {family}")
        if text.count(f"DecayRun.FileName {active_prefix(job['job_id'])}") != 1:
            raise RuntimeError(f"delayed source runner-prefix binding mismatch: {family}")
        digest = sha256(card)
        if row.get("source_sha256") != digest:
            raise RuntimeError(f"delayed source/index digest mismatch: {family}")
        activity = float(row["transported_ground_activity_Bq"])
        source_status = str(row["source_status"])
        execution_disposition = str(row.get("execution_disposition", ""))
        original_blocks = int(row["original_blocks"])
        transport_blocks = int(row["transport_blocks"])
        original_block_flux = float(row["original_block_flux_Bq"] or 0.0)
        transport_block_flux = float(row["transport_block_flux_Bq"] or 0.0)
        known_holdout_activity = float(row["known_holdout_activity_Bq"])
        unknown_holdout_states = int(row["unknown_activity_state_count"])
        if not math.isfinite(known_holdout_activity) or known_holdout_activity < 0.0:
            raise RuntimeError(f"invalid known holdout activity: {family}")
        if unknown_holdout_states < 0:
            raise RuntimeError(f"invalid unknown holdout state count: {family}")
        source_directives = [
            line for line in text.splitlines() if line.startswith("DecayRun.Source ")
        ]
        if execution_disposition == "RUN_83334":
            if not source_status.startswith("PASS__") or not math.isfinite(activity) or activity <= 0.0:
                raise RuntimeError(f"positive delayed source status/activity mismatch: {family}")
            if original_blocks != ORIGINAL_POSITION_BLOCKS or transport_blocks != TRANSPORT_POSITION_BLOCKS:
                raise RuntimeError(f"positive delayed source block contract mismatch: {family}")
            if (
                int(row["original_pointsource_blocks"]) != ORIGINAL_POSITION_BLOCKS
                or int(row["pointsource_blocks"]) != TRANSPORT_POSITION_BLOCKS
                or original_block_flux <= 0.0
                or transport_block_flux <= 0.0
            ):
                raise RuntimeError(f"positive delayed source point/flux contract mismatch: {family}")
            if len(source_directives) != TRANSPORT_POSITION_BLOCKS:
                raise RuntimeError(f"positive delayed source directive count mismatch: {family}")
            if any(row[name] for name in (
                "zero_count_garwood_two_sided95_upper",
                "transported_ground_rate_upper95_s-1",
                "transported_ground_A15_upper95_Bq_conservative",
                "zero_A15_upper_provenance",
            )):
                raise RuntimeError(f"positive delayed source publishes zero-source upper fields: {family}")
            actual_transport_events = DELAYED_EVENTS
        elif execution_disposition == "SKIP_ZERO_A15":
            if not source_status.startswith("ZERO_SOURCE__") or activity != 0.0:
                raise RuntimeError(f"zero delayed source status/activity mismatch: {family}")
            if original_blocks != 0 or transport_blocks != 0:
                raise RuntimeError(f"zero delayed source must have 0/0 blocks: {family}")
            if (
                int(row["original_pointsource_blocks"]) != 0
                or int(row["pointsource_blocks"]) != 0
                or original_block_flux != 0.0
                or transport_block_flux != 0.0
                or float(row["flux_per_point_Bq"] or 0.0) != 0.0
            ):
                raise RuntimeError(f"zero delayed source must have zero points and flux: {family}")
            if source_directives:
                raise RuntimeError(f"zero delayed source publishes DecayRun.Source: {family}")
            buildup_sum_tt_s = float(row["buildup_sum_TT_s"])
            zero_count_upper = float(row["zero_count_garwood_two_sided95_upper"])
            rate_upper = float(row["transported_ground_rate_upper95_s-1"])
            a15_upper = float(row["transported_ground_A15_upper95_Bq_conservative"])
            if buildup_sum_tt_s <= 0.0:
                raise RuntimeError(f"zero delayed source lacks positive buildup sumTT: {family}")
            if not math.isclose(
                zero_count_upper,
                ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER,
                rel_tol=0.0,
                abs_tol=1.0e-15,
            ):
                raise RuntimeError(f"zero delayed source Garwood count upper mismatch: {family}")
            expected_rate_upper = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / buildup_sum_tt_s
            if not math.isclose(rate_upper, expected_rate_upper, rel_tol=2.0e-15, abs_tol=1.0e-18):
                raise RuntimeError(f"zero delayed source upper-rate mismatch: {family}")
            if not math.isclose(a15_upper, rate_upper, rel_tol=0.0, abs_tol=1.0e-18):
                raise RuntimeError(f"zero delayed source conservative A15 upper mismatch: {family}")
            if row.get("zero_A15_upper_provenance") != ZERO_A15_UPPER_PROVENANCE:
                raise RuntimeError(f"zero delayed source upper provenance mismatch: {family}")
            if str(row.get("upper_excludes_known_and_unresolved_holdout", "")).lower() != "true":
                raise RuntimeError(f"zero delayed source upper does not separate holdout: {family}")
            actual_transport_events = 0
        else:
            raise RuntimeError(f"unknown delayed execution disposition for {family}: {execution_disposition}")
        original_total = float(row["original_total_Bq"])
        transport_total = float(row["transport_total_Bq"])
        original_closure = float(row["original_closure_Bq"])
        transport_closure = float(row["transport_closure_Bq"])
        if not math.isclose(original_total, activity, rel_tol=2.0e-15, abs_tol=1.0e-18):
            raise RuntimeError(f"original 50k activity closure failed: {family}")
        if not math.isclose(transport_total, activity, rel_tol=2.0e-15, abs_tol=1.0e-18):
            raise RuntimeError(f"transport 10k activity closure failed: {family}")
        if not math.isclose(original_closure, original_total - activity, rel_tol=0.0, abs_tol=1.0e-18):
            raise RuntimeError(f"original closure residual is internally inconsistent: {family}")
        if not math.isclose(transport_closure, transport_total - activity, rel_tol=0.0, abs_tol=1.0e-18):
            raise RuntimeError(f"transport closure residual is internally inconsistent: {family}")
        card_records.append({
            "family": family,
            "job_id": job["job_id"],
            "path": str(card.resolve()),
            "bytes": card.stat().st_size,
            "sha256": digest,
            "seed": int(job["seed"]),
            "events": DELAYED_EVENTS,
            "registered_events": DELAYED_EVENTS,
            "actual_transport_events": actual_transport_events,
            "source_status": source_status,
            "execution_disposition": execution_disposition,
            "transported_ground_activity_Bq": activity,
            "buildup_sum_TT_s": float(row["buildup_sum_TT_s"]),
            "zero_count_garwood_two_sided95_upper": (
                float(row["zero_count_garwood_two_sided95_upper"])
                if row["zero_count_garwood_two_sided95_upper"]
                else None
            ),
            "transported_ground_rate_upper95_s-1": (
                float(row["transported_ground_rate_upper95_s-1"])
                if row["transported_ground_rate_upper95_s-1"]
                else None
            ),
            "transported_ground_A15_upper95_Bq_conservative": (
                float(row["transported_ground_A15_upper95_Bq_conservative"])
                if row["transported_ground_A15_upper95_Bq_conservative"]
                else None
            ),
            "zero_A15_upper_provenance": row["zero_A15_upper_provenance"] or None,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_holdout_states,
            "upper_excludes_known_and_unresolved_holdout": (
                str(row["upper_excludes_known_and_unresolved_holdout"]).lower() == "true"
            ),
            "original_blocks": original_blocks,
            "transport_blocks": transport_blocks,
            "position_stride": int(row["position_stride"]),
            "original_block_flux_Bq": original_block_flux if execution_disposition == "RUN_83334" else None,
            "transport_block_flux_Bq": transport_block_flux if execution_disposition == "RUN_83334" else None,
            "original_total_Bq": original_total,
            "transport_total_Bq": transport_total,
            "original_closure_Bq": original_closure,
            "transport_closure_Bq": transport_closure,
        })
    transport_records = [
        row for row in card_records if row["execution_disposition"] == "RUN_83334"
    ]
    zero_records = [
        row for row in card_records if row["execution_disposition"] == "SKIP_ZERO_A15"
    ]
    geometry_authorities, geometry_errors, geometry_missing = geometry_contract_status()
    if geometry_errors or geometry_missing:
        raise RuntimeError(
            f"SF3 geometry authority drift: errors={geometry_errors} missing={geometry_missing}"
        )
    payload = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": "PASS",
        "semantic_status": semantic_status,
        "geometry": "SF3",
        "geometry_setup": str(SF3_SETUP.resolve()),
        "geometry_authorities": geometry_authorities,
        "delayed_jobs": len(card_records),
        "registered_delayed_source_cells": len(card_records),
        "transport_delayed_jobs": len(transport_records),
        "skipped_zero_A15_jobs": len(zero_records),
        "skipped_zero_A15_families": [row["family"] for row in zero_records],
        "delayed_events_per_job": DELAYED_EVENTS,
        "delayed_events_total": sum(int(row["actual_transport_events"]) for row in card_records),
        "actual_transport_triggers": sum(
            int(row["actual_transport_events"]) for row in card_records
        ),
        "manifest": small_file_record(manifest_path),
        "day15_summary": small_file_record(summary_path),
        "delayed_source_index": small_file_record(index_path),
        "passive_w_activation_lineage": small_file_record(w_lineage_path),
        "passive_w_activation_summary": small_file_record(w_summary_path),
        "source_cards": card_records,
        "normalization": (
            "activation sum(RP)/sum(TT) with zero-RP TT; RUN cells use delayed event weight "
            "A15/83334; SKIP_ZERO_A15 cells have central 0 plus a separate finite two-sided-95% upper"
        ),
        "zero_source_upper_policy": ZERO_A15_UPPER_PROVENANCE,
        "sim_digest_policy": "OMITTED_BY_CONTRACT__ACTIVATION_USED_ONE_SEMANTIC_RPIP_SCAN_ONLY",
        "authority_boundary": "W4_LAUNCH_GATE_ONLY__NOT_DELAYED_RATE_RESPONSE_MISSION_F3_OR_PROMOTION_AUTHORITY",
    }
    write_once_text(ACTIVATION_VALIDATION, json_text(payload))
    return payload


def self_test() -> dict[str, Any]:
    parsed = parse_dat_lines(
        [
            "TT 10",
            "VN TEST_VOL",
            "RP 11024 0 2",
            "RP 11024 0.004 3",
            "EN",
        ],
        "synthetic",
    )
    if parsed["TT_s"] != 10.0 or parsed["RP_record_count"] != 2 or parsed["sum_RP"] != 5.0:
        raise AssertionError("DAT parser self-test failed")
    key = state_key("TEST_VOL", 11024, 0.0)
    if parsed["totals"][key] != 5.0:
        raise AssertionError("canonical state aggregation self-test failed")
    if activity_from_rate(2.0, math.inf) != 0.0:
        raise AssertionError("stable activity self-test failed")
    synthetic_nubase = {11024: [{
        "is_ground": True,
        "state_designator": "0",
        "excitation_keV": 0.0,
        "half_life_s": 3600.0,
        "nubase_line": 1,
    }]}
    matched, provenance = match_nubase_state(synthetic_nubase, 11024, 0.0)
    if matched is None or provenance != "NUBASE2020_ground":
        raise AssertionError("NUBASE matching self-test failed")
    included = [{
        "volume": "TEST_VOL",
        "ZA": 11024,
        "excitation_keV": 0.0,
        "day15_activity_Bq": 1.0,
    }]
    points = {key: [(1.0, 2.0, 3.0)]}
    sample = weighted_sample(included, points, ORIGINAL_POSITION_BLOCKS, 12345)
    job = {
        "job_id": "sf3_delayed_p",
        "seed": 411155092,
    }
    source, closure = render_delayed_source(job, sample, 1.0)
    if closure["transport_blocks"] != TRANSPORT_POSITION_BLOCKS:
        raise AssertionError("stride count self-test failed")
    if not math.isclose(closure["transport_flux_sum_Bq"], 1.0, rel_tol=2e-15, abs_tol=1e-18):
        raise AssertionError("stride flux closure self-test failed")
    for token in (
        f"Geometry {SF3_SETUP}",
        "Seed 411155092",
        f"DecayRun.Triggers {DELAYED_EVENTS}",
        ".Spectrum Mono 1e-06",
    ):
        if token not in source:
            raise AssertionError(f"source rendering self-test missing {token!r}")
    zero_source, zero_closure = render_delayed_source(job, [], 0.0)
    if zero_closure["execution_disposition"] != "SKIP_ZERO_A15":
        raise AssertionError("zero-A15 disposition self-test failed")
    if any(line.startswith("DecayRun.Source ") for line in zero_source.splitlines()):
        raise AssertionError("zero-A15 source unexpectedly contains DecayRun.Source")
    if zero_closure["original_blocks"] != 0 or zero_closure["transport_blocks"] != 0:
        raise AssertionError("zero-A15 block self-test failed")
    synthetic_sum_tt = 10.0
    synthetic_upper_rate = ZERO_COUNT_GARWOOD_TWO_SIDED95_UPPER / synthetic_sum_tt
    if not math.isclose(
        synthetic_upper_rate,
        0.36888794541139363,
        rel_tol=0.0,
        abs_tol=1.0e-16,
    ):
        raise AssertionError("zero-count Garwood upper-rate self-test failed")
    synthetic_cells = [
        {"incident_family": family, "sum_TT_s": 10.0}
        for family in FAMILIES
    ]
    w_rows, w_summary = passive_w_activation_lineage([], synthetic_cells)
    if len(w_rows) != 3 * len(FAMILIES) or not w_summary["all_three_volumes_explicit_even_if_zero"]:
        raise AssertionError("zero-production passive-W lineage closure failed")
    if any(row["active_veto_eligible"] for row in w_rows):
        raise AssertionError("passive W became veto-eligible")
    if material_category(PASSIVE_W_DIAGNOSTIC_VOLUMES[0]) != "passive_w_or_collimator":
        raise AssertionError("front-window W material precedence failed")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_ACTIVATION_BUILDER_SELF_TEST",
        "checks": [
            "DAT_TT_RP_EN_and_state_aggregation",
            "NUBASE_ground_state_matching",
            "stable_activity_zero",
            "deterministic_50k_sampling",
            "stride5_10k_flux_times5_closure",
            "SF3_setup_seed_83334_trigger_and_epsilon_source_syntax",
            "zero_A15_0blocks_no_DecayRun_Source_and_finite_3p688879_over_sumTT_upper",
            "three_passive_W_volumes_x_eight_families_explicit_even_if_zero",
            "passive_W_material_precedence_and_never_active_veto",
        ],
        "sim_opened": False,
        "files_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-prerequisites", action="store_true", help="read-only W2/W3 readiness report")
    actions.add_argument("--status", action="store_true", help="alias of --check-prerequisites")
    actions.add_argument("--prepare", action="store_true", help="build W3 outputs and eight source cards; no transport")
    actions.add_argument("--self-test", action="store_true", help="run pure parser/source-contract checks")
    args = parser.parse_args()
    try:
        if args.prepare:
            result = prepare()
        elif args.self_test:
            result = self_test()
        else:
            result = prerequisite_status()
        print(json_text(result), end="")
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "status": "FAIL__SF3_ACTIVATION_BUILDER",
            "error": str(exc),
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
