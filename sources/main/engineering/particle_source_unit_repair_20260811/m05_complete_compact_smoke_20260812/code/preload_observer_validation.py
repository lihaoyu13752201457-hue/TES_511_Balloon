#!/usr/bin/env python3
"""Strict zero-RNG validation for an F/U post-GPS observer transaction.

The observer transaction is only one component of a transport job.  Passing
this validator never means that Cosima, native SIM/DAT, RP, or the outer job
receipt passed.  It proves only the ordered tape -> actual post-GPS generated
tuple boundary recorded by the installed-Cosima preload observer.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import stat
import struct
from pathlib import Path
from typing import Any

from preflight_common import (
    PACKAGE,
    assert_canonical_json,
    canonical_json_bytes,
    reject_lexical_symlinks,
    sha256,
    strict_json,
)
from tape_contract import (
    _binary64_hash,
    _parse_rows,
    _primary_from_row,
    runtime_projected_primary,
    runtime_source_time_projection,
    validate_sidecar,
)


SCHEMA = PACKAGE / "schema/preload_generated_observation_v1.schema.json"
COMMIT_NAME = "observer_generated_only.json"
DATA_NAME = "generated_observations.tsv"
STATUS = "PASS__GENERATED_OBSERVATIONS_ONLY__NOT_JOB_PASS"
PINNED_LIBCOSIMA_PATH = "/home/ubuntu/MEGAlib_Install/megalib-main/lib/libCosima.so"
PINNED_LIBCOSIMA_SHA256 = "0656a54e0351a72347ad70437a96097b4d37688d10ac9059038e0b697ce6a495"
DIGEST = re.compile(r"[0-9a-f]{64}")
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*")
FINITE_NUMBER = re.compile(r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?")
OBSERVATION_COLUMNS = (
    "simulation_event_id",
    "stable_root_id",
    "eventlist_id",
    "arm",
    "observed_particle",
    "observed_excitation_keV",
    "expected_source_time_s",
    "observed_source_time_s",
    "observed_x_cm",
    "observed_y_cm",
    "observed_z_cm",
    "observed_dx",
    "observed_dy",
    "observed_dz",
    "observed_px",
    "observed_py",
    "observed_pz",
    "observed_energy_keV",
    "expected_generated_binary64_sha256",
    "observed_generated_binary64_sha256",
)
COMMIT_KEYS = {
    "arm",
    "artifact_is_transport_authority",
    "event_count",
    "generated_observations_path",
    "generated_observations_sha256",
    "generated_observations_size_bytes",
    "resolved_original_library_path",
    "resolved_original_library_sha256",
    "schema_version",
    "status",
    "tape_root_sidecar_sha256",
}


def validate_observer_schema() -> dict[str, Any]:
    schema = assert_canonical_json(SCHEMA)
    if (
        schema.get("$id") != "urn:tes511:m05-preload-generated-observation-v1"
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
        or tuple(schema.get("required", [])) != OBSERVATION_COLUMNS
        or tuple(schema.get("x-tsv-columns", [])) != OBSERVATION_COLUMNS
        or set(schema.get("properties", {})) != set(OBSERVATION_COLUMNS)
    ):
        raise ValueError("preload observer executable schema drift")
    return {
        "path": str(SCHEMA),
        "sha256": sha256(SCHEMA),
        "size_bytes": SCHEMA.stat().st_size,
        "column_count": len(OBSERVATION_COLUMNS),
        "status": "PASS",
    }


def _regular_single_link(path: Path) -> None:
    reject_lexical_symlinks(path)
    state = os.lstat(path)
    if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise ValueError(f"observer artifact is not a single-link regular file: {path}")


def _strict_positive_integer(text: str, field: str) -> int:
    if POSITIVE_INTEGER.fullmatch(text) is None:
        raise ValueError(f"invalid positive integer {field}: {text!r}")
    return int(text)


def _strict_finite(text: str, field: str) -> float:
    if FINITE_NUMBER.fullmatch(text) is None:
        raise ValueError(f"invalid numeric syntax {field}: {text!r}")
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}")
    return value


def _same_binary64(left: float, right: float) -> bool:
    return struct.pack(">d", left) == struct.pack(">d", right)


def _parse_observations(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("observer TSV is not UTF-8") from error
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("observer TSV must use one final LF and no CR bytes")
    lines = text.split("\n")
    if lines[-1] != "":
        raise AssertionError("split final sentinel mismatch")
    lines.pop()
    if not lines or tuple(lines[0].split("\t")) != OBSERVATION_COLUMNS:
        raise ValueError("observer TSV exact header mismatch")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if not line:
            raise ValueError("blank observer TSV row")
        fields = line.split("\t")
        if len(fields) != len(OBSERVATION_COLUMNS):
            raise ValueError("observer TSV row has missing/extra columns")
        rows.append(dict(zip(OBSERVATION_COLUMNS, fields, strict=True)))
    if not rows:
        raise ValueError("observer TSV has no rows")
    return rows


def validate_observer_transaction(
    observer_directory: Path,
    tape: Path,
    tape_root_sidecar: Path,
    *,
    expected_arm: str,
    verify_tape_authorities: bool = True,
    verify_tape_sampler: bool = True,
) -> dict[str, Any]:
    """Validate one committed observer directory against one exact tape shard."""

    if expected_arm not in {"F", "U"}:
        raise ValueError("observer validator permits only F/U")
    observer_directory = observer_directory.absolute()
    tape = tape.absolute()
    tape_root_sidecar = tape_root_sidecar.absolute()
    for path in (observer_directory, tape, tape_root_sidecar):
        reject_lexical_symlinks(path)
    directory_state = os.lstat(observer_directory)
    if not stat.S_ISDIR(directory_state.st_mode) or observer_directory.name.endswith(".gpsobs") is False:
        raise ValueError("observer authority must be a non-symlink .gpsobs directory")
    partial = observer_directory.with_name(observer_directory.name + ".partial")
    if os.path.lexists(partial):
        raise ValueError("observer final and partial transaction coexist")
    names = {entry.name for entry in observer_directory.iterdir()}
    if names != {COMMIT_NAME, DATA_NAME}:
        raise ValueError(f"observer transaction has missing/extra artifacts: {sorted(names)}")
    commit_path = observer_directory / COMMIT_NAME
    data_path = observer_directory / DATA_NAME
    _regular_single_link(commit_path)
    _regular_single_link(data_path)
    commit = strict_json(commit_path)
    if canonical_json_bytes(commit) != commit_path.read_bytes() or set(commit) != COMMIT_KEYS:
        raise ValueError("observer commit is non-canonical or has missing/extra keys")
    if (
        commit["schema_version"] != 2
        or commit["status"] != STATUS
        or commit["artifact_is_transport_authority"] is not False
        or commit["arm"] != expected_arm
        or commit["generated_observations_path"] != DATA_NAME
        or isinstance(commit["event_count"], bool)
        or not isinstance(commit["event_count"], int)
        or commit["event_count"] <= 0
        or isinstance(commit["generated_observations_size_bytes"], bool)
        or not isinstance(commit["generated_observations_size_bytes"], int)
        or commit["generated_observations_size_bytes"] <= 0
        or not isinstance(commit["generated_observations_sha256"], str)
        or DIGEST.fullmatch(commit["generated_observations_sha256"]) is None
        or not isinstance(commit["tape_root_sidecar_sha256"], str)
        or DIGEST.fullmatch(commit["tape_root_sidecar_sha256"]) is None
        or commit["resolved_original_library_path"] != PINNED_LIBCOSIMA_PATH
        or commit["resolved_original_library_sha256"] != PINNED_LIBCOSIMA_SHA256
    ):
        raise ValueError("observer commit field contract failed")
    if (
        sha256(data_path) != commit["generated_observations_sha256"]
        or data_path.stat().st_size != commit["generated_observations_size_bytes"]
        or sha256(tape_root_sidecar) != commit["tape_root_sidecar_sha256"]
        or sha256(Path(PINNED_LIBCOSIMA_PATH)) != PINNED_LIBCOSIMA_SHA256
    ):
        raise ValueError("observer commit data/tape hash or size binding failed")

    schema = validate_observer_schema()
    tape_check = validate_sidecar(
        tape,
        tape_root_sidecar,
        verify_authorities=verify_tape_authorities,
        verify_sampler=verify_tape_sampler,
    )
    tape_rows = _parse_rows(tape_root_sidecar)
    observed_rows = _parse_observations(data_path)
    if len(observed_rows) != len(tape_rows) or len(observed_rows) != commit["event_count"]:
        raise ValueError("observer/tape/commit row-count closure failed")

    seen_ids: set[int] = set()
    seen_roots: set[str] = set()
    previous_runtime_internal_time = 0.0
    for index, (observed, root) in enumerate(zip(observed_rows, tape_rows, strict=True), start=1):
        simulation_event_id = _strict_positive_integer(observed["simulation_event_id"], "simulation_event_id")
        eventlist_id = _strict_positive_integer(observed["eventlist_id"], "eventlist_id")
        particle = _strict_positive_integer(observed["observed_particle"], "observed_particle")
        if (
            simulation_event_id != index
            or eventlist_id != index
            or simulation_event_id in seen_ids
            or observed["stable_root_id"] in seen_roots
            or observed["stable_root_id"] != root["stable_root_id"]
            or observed["arm"] != expected_arm
            or particle != int(root["particle"])
        ):
            raise ValueError("observer ordered key/arm/particle tape join failed")
        seen_ids.add(simulation_event_id)
        seen_roots.add(observed["stable_root_id"])
        if DIGEST.fullmatch(observed["stable_root_id"]) is None:
            raise ValueError("invalid observer stable-root digest")

        values = {
            name: _strict_finite(observed[name], name)
            for name in OBSERVATION_COLUMNS
            if name.startswith("observed_") and name not in {
                "observed_particle", "observed_generated_binary64_sha256"
            }
        }
        expected_source_time = _strict_finite(observed["expected_source_time_s"], "expected_source_time_s")
        primary = _primary_from_row(root)
        runtime_time, previous_runtime_internal_time = runtime_source_time_projection(
            primary.source_time_s, previous_runtime_internal_time
        )
        projected = runtime_projected_primary(primary, runtime_source_time_s=runtime_time)
        expected_values = {
            "observed_excitation_keV": projected.excitation_keV,
            "observed_source_time_s": projected.source_time_s,
            "observed_x_cm": projected.position_cm[0],
            "observed_y_cm": projected.position_cm[1],
            "observed_z_cm": projected.position_cm[2],
            "observed_dx": projected.direction[0],
            "observed_dy": projected.direction[1],
            "observed_dz": projected.direction[2],
            "observed_px": projected.polarization[0],
            "observed_py": projected.polarization[1],
            "observed_pz": projected.polarization[2],
            "observed_energy_keV": projected.energy_keV,
        }
        if not _same_binary64(expected_source_time, primary.source_time_s):
            raise ValueError("observer raw expected source time differs from tape bits")
        if any(not _same_binary64(values[name], expected) for name, expected in expected_values.items()):
            raise ValueError("observer actual post-GPS binary64 fields differ from runtime projection")
        direction_norm = math.sqrt(sum(values[name] ** 2 for name in ("observed_dx", "observed_dy", "observed_dz")))
        if not math.isfinite(direction_norm) or abs(direction_norm - 1.0) > 2e-15:
            raise ValueError("observer direction norm invalid")
        expected_digest = root["expected_generated_binary64_sha256"]
        if (
            DIGEST.fullmatch(observed["expected_generated_binary64_sha256"]) is None
            or DIGEST.fullmatch(observed["observed_generated_binary64_sha256"]) is None
            or observed["expected_generated_binary64_sha256"] != expected_digest
            or observed["observed_generated_binary64_sha256"] != expected_digest
            or _binary64_hash(projected, projected.direction) != expected_digest
        ):
            raise ValueError("observer generated binary64 digest closure failed")

    return {
        "schema_version": 1,
        "status": "PASS__OBSERVER_TRANSACTION_ONLY__NOT_JOB_PASS",
        "artifact_is_transport_authority": False,
        "arm": expected_arm,
        "event_count": len(observed_rows),
        "unique_event_count": len(seen_ids),
        "unique_root_count": len(seen_roots),
        "observer_directory": str(observer_directory),
        "commit_sha256": sha256(commit_path),
        "generated_observations_sha256": sha256(data_path),
        "tape_root_sidecar_sha256": sha256(tape_root_sidecar),
        "tape_validation": tape_check,
        "schema": schema,
        "outer_job_receipt_still_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observer-directory", type=Path, required=True)
    parser.add_argument("--tape", type=Path, required=True)
    parser.add_argument("--tape-root-sidecar", type=Path, required=True)
    parser.add_argument("--arm", choices=("F", "U"), required=True)
    args = parser.parse_args()
    result = validate_observer_transaction(
        args.observer_directory,
        args.tape,
        args.tape_root_sidecar,
        expected_arm=args.arm,
    )
    os.write(1, canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
