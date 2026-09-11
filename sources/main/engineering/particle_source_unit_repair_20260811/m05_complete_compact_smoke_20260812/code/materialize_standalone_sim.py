#!/usr/bin/env python3
"""Materialize an M05 compact v2 record bundle as a standalone ASCII SIM.

The compact truth stream contains native ``MSimEvent::ToSimString()`` fragments
only for TES-selected/control roots.  This module validates every join and byte
range, embeds those native fragments unchanged, and creates an INIT-only event
from the hash-bound EventList tape for every other root.  Publication is
write-once and the JSON manifest is the final commit marker.

This is a representation consumer.  It never starts Cosima or Geant4.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tape_contract import SIDECAR_COLUMNS, validate_sidecar
from record_validation import (
    PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH,
    ValidationError as RecordValidationError,
    validate_bundle,
)
from preflight_common import fsync_directory, quarantine_directory_no_replace, rename_no_replace


PACKAGE = Path(__file__).resolve().parents[1]
RECORD_SCHEMA = PACKAGE / "schema/m05cc_v2.record_schema.json"
ACTIVE_WHITELIST = PACKAGE / "schema/active_volume_whitelist_v1.json"
FROZEN_REVAN_CONFIG = PACKAGE / "config/revan_zero_transport_fixture_v1.cfg"
MATERIALIZER_VERSION = "m05-standalone-sim-materializer-v1"
SIM_VERSION = 101  # Current installed MSimEvent::s_Version/default standalone SIM version.
HEX64 = re.compile(r"[0-9a-f]{64}")
INT = re.compile(r"(?:0|[1-9][0-9]*)")
SIGNED_INT = re.compile(r"(?:0|-?[1-9][0-9]*)")
FINITE = re.compile(r"[-+]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][-+]?[0-9]+)?")

OUTPUT_INDEX_COLUMNS = (
    "schema", "simulation_event_id", "eventlist_id", "stable_root_id", "representation",
    "selection_reason", "standalone_offset", "standalone_length", "standalone_sha256",
    "source_truth_offset", "source_truth_length", "source_truth_sha256", "ia_count", "ht_count",
    "init_tuple_sha256", "raw_tape_line_sha256", "expected_generated_tuple_sha256",
    "expected_eventlist_binary64_sha256", "expected_generated_binary64_sha256",
    "observed_generated_binary64_sha256",
    "serialized_ia_quantized_sha256",
)


class ContractError(ValueError):
    """Raised when an input or output violates the materialization contract."""


@dataclass(frozen=True)
class TapeRow:
    row_index0: int
    eventlist_id: int
    stable_root_id: str
    driver: str
    family: str
    mode: str
    particle: int
    excitation_keV: float
    source_time_s: float
    position_cm: tuple[float, float, float]
    direction: tuple[float, float, float]
    polarization: tuple[float, float, float]
    energy_keV: float
    raw_line_sha256: str
    expected_tuple_sha256: str
    eventlist_binary64_sha256: str
    generated_binary64_sha256: str
    control_flag: bool


@dataclass(frozen=True)
class EventSummary:
    event_id: int
    started_id: int
    time_s: float
    ia_count: int
    ht_count: int
    generated_tuple_sha256: str
    serialized_ia_tuple_sha256: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot parse strict JSON {path}: {error}") from error


def _declared_record_contract() -> tuple[
    dict[str, tuple[str, ...]], frozenset[str], frozenset[str], frozenset[str]
]:
    """Read exact table/blob declarations from the executable v2 schema.

    This deliberately avoids a second copied set of record headers.  The tape
    side follows the same rule via ``tape_contract.SIDECAR_COLUMNS``.
    """
    schema = strict_json(RECORD_SCHEMA)
    try:
        tables = schema["x-tsv-tables"]
        required_properties = frozenset(schema["required"])
        required_tables = frozenset(schema["properties"]["tables"]["required"])
        required_blobs = frozenset(schema["properties"]["blobs"]["required"])
    except (KeyError, TypeError) as error:
        raise ContractError(f"record schema lacks executable table/blob declarations: {error}") from error
    if not isinstance(tables, dict) or set(tables) != set(required_tables):
        raise ContractError("record schema table declarations disagree")
    headers: dict[str, tuple[str, ...]] = {}
    for name, declaration in tables.items():
        header = declaration.get("header") if isinstance(declaration, dict) else None
        if not isinstance(header, list) or not header or len(header) != len(set(header)) or not all(
            isinstance(column, str) and column for column in header
        ):
            raise ContractError(f"record schema has invalid {name} header")
        headers[name] = tuple(header)
    return headers, required_properties, required_tables, required_blobs


TABLE_COLUMNS, REQUIRED_BUNDLE_PROPERTIES, REQUIRED_TABLES, REQUIRED_BLOBS = _declared_record_contract()


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        raise ContractError(f"{where}: keys differ: missing={sorted(expected-set(value))}, extra={sorted(set(value)-expected)}")


def _check_no_symlink(path: Path, *, must_exist: bool = True, expect_file: bool = True) -> Path:
    absolute = path if path.is_absolute() else (Path.cwd() / path)
    absolute = Path(os.path.abspath(os.fspath(absolute)))
    parts = absolute.parts
    current = Path(parts[0])
    for part in parts[1:]:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            if must_exist:
                raise ContractError(f"missing path component: {current}")
            break
        if stat.S_ISLNK(mode):
            raise ContractError(f"symlink path component is forbidden: {current}")
    if must_exist:
        mode = absolute.stat().st_mode
        if expect_file and not stat.S_ISREG(mode):
            raise ContractError(f"not a regular file: {absolute}")
        if not expect_file and not stat.S_ISDIR(mode):
            raise ContractError(f"not a directory: {absolute}")
    return absolute


def _resolve_binding_path(manifest: Path, lexical: str) -> Path:
    if not isinstance(lexical, str) or not lexical or "\x00" in lexical:
        raise ContractError("invalid bound path")
    candidate = Path(lexical)
    if not candidate.is_absolute():
        candidate = manifest.parent / candidate
    return _check_no_symlink(candidate)


def _parse_int(value: str, name: str, *, minimum: int = 0) -> int:
    if INT.fullmatch(value) is None:
        raise ContractError(f"{name}: not a canonical nonnegative integer: {value!r}")
    parsed = int(value)
    if parsed < minimum:
        raise ContractError(f"{name}: below minimum {minimum}")
    return parsed


def _parse_signed_int(value: str, name: str) -> int:
    if SIGNED_INT.fullmatch(value) is None:
        raise ContractError(f"{name}: not a canonical integer: {value!r}")
    return int(value)


def _parse_float(value: str, name: str, *, minimum: float | None = None) -> float:
    if FINITE.fullmatch(value) is None:
        raise ContractError(f"{name}: not a canonical finite float: {value!r}")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ContractError(f"{name}: nonfinite")
    if minimum is not None and parsed < minimum:
        raise ContractError(f"{name}: below minimum {minimum}")
    return parsed


def _digest(value: str, name: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ContractError(f"{name}: not a lowercase SHA-256")
    return value


def _read_tsv(path: Path, expected: Sequence[str], *, allow_empty: bool) -> list[dict[str, str]]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ContractError(f"cannot read TSV {path}: {error}") from error
    if b"\r" in raw or b"\x00" in raw or not raw.endswith(b"\n"):
        raise ContractError(f"{path}: TSV must be NUL-free UTF-8/LF and newline terminated")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{path}: not UTF-8") from error
    reader = csv.reader(text.splitlines(), delimiter="\t", strict=True)
    rows = list(reader)
    if not rows or tuple(rows[0]) != tuple(expected):
        raise ContractError(f"{path}: wrong exact TSV header")
    body = rows[1:]
    if not allow_empty and not body:
        raise ContractError(f"{path}: empty table")
    if any(len(row) != len(expected) for row in body):
        raise ContractError(f"{path}: wrong TSV field count")
    return [dict(zip(expected, row, strict=True)) for row in body]


def _llround(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)


def tuple_hash(
    particle: int,
    excitation_keV: float,
    source_time_s: float,
    position: Sequence[float],
    direction: Sequence[float],
    polarization: Sequence[float],
    energy_keV: float,
) -> str:
    norm = math.sqrt(math.fsum(component * component for component in direction))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ContractError("zero/nonfinite primary direction")
    values = [
        particle,
        _llround(excitation_keV * 1.0e6),
        _llround(source_time_s * 1.0e12),
        *(_llround(value * 1.0e6) for value in position),
        *(_llround(value / norm * 1.0e9) for value in direction),
        *(_llround(value * 1.0e9) for value in polarization),
        _llround(energy_keV * 1.0e6),
    ]
    return sha256_bytes(canonical_json_bytes(values))


def ia_init_hash(
    particle: int,
    ia_time_s: float,
    position: Sequence[float],
    direction: Sequence[float],
    polarization: Sequence[float],
    energy_keV: float,
) -> str:
    """Hash only fields actually serialized by an IA INIT record."""
    norm = math.sqrt(math.fsum(component * component for component in direction))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ContractError("zero/nonfinite IA INIT direction")
    values = [
        particle,
        _llround(ia_time_s * 1.0e12),
        *(_llround(value * 1.0e6) for value in position),
        *(_llround(value / norm * 1.0e9) for value in direction),
        *(_llround(value * 1.0e9) for value in polarization),
        _llround(energy_keV * 1.0e6),
    ]
    canonical = canonical_json_bytes(values)
    return sha256_bytes(b"m05-ia-init-state-v1\0" + canonical)


def _load_bundle(manifest_path: Path) -> tuple[dict[str, Any], dict[str, Path], Path]:
    manifest_path = _check_no_symlink(manifest_path)
    bundle = strict_json(manifest_path)
    if not isinstance(bundle, dict):
        raise ContractError("record bundle manifest is not an object")
    _require_exact_keys(bundle, set(REQUIRED_BUNDLE_PROPERTIES), "record bundle")
    if bundle["schema_version"] != "m05cc-v2-record-bundle":
        raise ContractError("wrong record bundle schema_version")
    schema_sha = sha256_file(_check_no_symlink(RECORD_SCHEMA))
    whitelist_sha = sha256_file(_check_no_symlink(ACTIVE_WHITELIST))
    if _digest(bundle["record_schema_sha256"], "record_schema_sha256") != schema_sha:
        raise ContractError("record schema hash drift")
    if _digest(bundle["veto_whitelist_sha256"], "veto_whitelist_sha256") != whitelist_sha:
        raise ContractError("active whitelist hash drift")
    _digest(bundle["geometry_classification_sha256"], "geometry_classification_sha256")
    provenance = bundle["provenance"]
    _require_exact_keys(
        provenance,
        {
            "geometry_bundle_sha256", "tape_root_sidecar_sha256", "tape_root_sidecar_path",
            "source_card_sha256", "source_contract_sha256",
        },
        "record bundle provenance",
    )
    for key, value in provenance.items():
        if key == "tape_root_sidecar_path":
            if not isinstance(value, str) or not value:
                raise ContractError("provenance.tape_root_sidecar_path is empty/malformed")
            continue
        _digest(value, f"provenance.{key}")
    if not isinstance(bundle["tables"], dict) or set(bundle["tables"]) != REQUIRED_TABLES:
        raise ContractError("record bundle table set mismatch")
    if not isinstance(bundle["blobs"], dict) or set(bundle["blobs"]) != REQUIRED_BLOBS:
        raise ContractError("record bundle blob set mismatch")
    paths: dict[str, Path] = {}
    for name, binding in {**bundle["tables"], **bundle["blobs"]}.items():
        if not isinstance(binding, dict):
            raise ContractError(f"binding {name} is not an object")
        expected_keys = {"path", "sha256", "row_count"} if name in REQUIRED_TABLES else {"path", "sha256", "size_bytes"}
        _require_exact_keys(binding, expected_keys, f"binding {name}")
        path = _resolve_binding_path(manifest_path, binding["path"])
        expected_sha = _digest(binding["sha256"], f"{name}.sha256")
        if sha256_file(path) != expected_sha:
            raise ContractError(f"{name}: bound SHA-256 mismatch")
        if name in REQUIRED_TABLES:
            row_count = _parse_manifest_int(binding["row_count"], f"{name}.row_count")
            raw = path.read_bytes()
            if b"\r" in raw or not raw.endswith(b"\n"):
                raise ContractError(f"{name}: table is not LF/newline terminated")
            actual_rows = len(raw.splitlines()) - 1
            if actual_rows != row_count:
                raise ContractError(f"{name}: bound row_count mismatch")
        else:
            expected_size = _parse_manifest_int(binding["size_bytes"], f"{name}.size_bytes")
            if path.stat().st_size != expected_size:
                raise ContractError(f"{name}: bound size mismatch")
        paths[name] = path
    run = bundle["run"]
    if not isinstance(run, dict):
        raise ContractError("run is not an object")
    _require_exact_keys(
        run,
        {"arm", "geometry", "mode", "family", "job_id", "shard_index", "seed", "active_block_coverage", "expected_event_count"},
        "run",
    )
    if run["arm"] != "C" or run["geometry"] not in {"mass_model_511", "s3d_o8"}:
        raise ContractError("materializer requires a compact C arm with known geometry")
    if run["mode"] not in {"instant", "buildup"}:
        raise ContractError("invalid run mode")
    if run["family"] not in {"gamma", "n", "eminus", "eplus", "alpha", "muplus", "muminus"}:
        raise ContractError("invalid family")
    _parse_manifest_int(run["expected_event_count"], "expected_event_count", minimum=1)
    return bundle, paths, manifest_path


def _parse_manifest_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractError(f"{name}: invalid integer")
    return value


def _load_tape(tape_path: Path, sidecar_path: Path, *, verify_authorities: bool) -> list[TapeRow]:
    tape_path = _check_no_symlink(tape_path)
    sidecar_path = _check_no_symlink(sidecar_path)
    raw_tape = tape_path.read_bytes()
    if b"\r" in raw_tape or b"\x00" in raw_tape or not raw_tape.endswith(b"\n"):
        raise ContractError("EventList tape must be NUL-free UTF-8/LF and newline terminated")
    try:
        tape_lines = raw_tape.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ContractError("EventList tape is not UTF-8") from error
    try:
        validate_sidecar(
            tape_path,
            sidecar_path,
            verify_authorities=verify_authorities,
            verify_sampler=verify_authorities,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ContractError(f"independent tape_contract validation failed: {error}") from error
    rows = _read_tsv(sidecar_path, SIDECAR_COLUMNS, allow_empty=False)
    if len(rows) != len(tape_lines):
        raise ContractError("tape/root-sidecar count mismatch")
    result: list[TapeRow] = []
    roots: set[str] = set()
    previous_time = -math.inf
    for index, (line, row) in enumerate(zip(tape_lines, rows, strict=True)):
        fields = line.split(" ")
        if "" in fields or len(fields) != 15:
            raise ContractError(f"tape row {index}: expected exactly 15 single-space-separated fields")
        row_index = _parse_int(row["row_index0"], "row_index0")
        eventlist_id = _parse_int(row["eventlist_id"], "eventlist_id", minimum=1)
        if row["schema"] != "m05-tape-root-v2" or row_index != index or eventlist_id != index + 1:
            raise ContractError("tape order/schema/eventlist ID mismatch")
        if fields[0] != row["eventlist_id"] or fields[1] != "0":
            raise ContractError("tape row ID/successor mismatch")
        root = _digest(row["stable_root_id"], "stable_root_id")
        if root in roots:
            raise ContractError("duplicate stable root")
        roots.add(root)
        raw_hash = _digest(row["raw_eventlist_line_sha256"], "raw_eventlist_line_sha256")
        if sha256_bytes(line.encode("utf-8")) != raw_hash:
            raise ContractError("raw EventList line hash mismatch")
        for key in ("source_card_sha256", "source_contract_sha256", "spectrum_sha256"):
            _digest(row[key], key)
        expected_hash = _digest(row["expected_generated_tuple_sha256"], "expected_generated_tuple_sha256")
        eventlist_binary64_hash = _digest(row["expected_eventlist_binary64_sha256"], "expected_eventlist_binary64_sha256")
        generated_binary64_hash = _digest(
            row["expected_generated_binary64_sha256"], "expected_generated_binary64_sha256"
        )
        particle = _parse_int(row["particle"], "particle", minimum=1)
        excitation = _parse_float(row["excitation_keV"], "excitation_keV", minimum=0.0)
        source_time = _parse_float(row["source_time_s"], "source_time_s", minimum=0.0)
        position = tuple(_parse_float(row[name], name) for name in ("x_cm", "y_cm", "z_cm"))
        direction = tuple(_parse_float(row[name], name) for name in ("dx", "dy", "dz"))
        polarization = tuple(_parse_float(row[name], name) for name in ("px", "py", "pz"))
        energy = _parse_float(row["energy_keV"], "energy_keV", minimum=0.0)
        pairs = (
            (fields[2], row["particle"]), (fields[3], row["excitation_keV"]), (fields[4], row["source_time_s"]),
            (fields[5], row["x_cm"]), (fields[6], row["y_cm"]), (fields[7], row["z_cm"]),
            (fields[8], row["dx"]), (fields[9], row["dy"]), (fields[10], row["dz"]),
            (fields[11], row["px"]), (fields[12], row["py"]), (fields[13], row["pz"]),
            (fields[14], row["energy_keV"]),
        )
        if any(_parse_float(left, "tape value") != _parse_float(right, "sidecar value") for left, right in pairs):
            raise ContractError("tape/sidecar tuple mismatch")
        observed = tuple_hash(particle, excitation, source_time, position, direction, polarization, energy)
        if observed != expected_hash:
            raise ContractError("expected generated tuple hash is not reproducible")
        if source_time <= previous_time:
            raise ContractError("tape source times are not strictly increasing")
        previous_time = source_time
        if row["control_flag"] not in {"0", "1"}:
            raise ContractError("malformed pre-registered tape control flag")
        result.append(TapeRow(
            row_index, eventlist_id, root, row["driver"], row["family"], row["mode"], particle, excitation, source_time,
            position, direction, polarization, energy, raw_hash, expected_hash, eventlist_binary64_hash,
            generated_binary64_hash,
            row["control_flag"] == "1",
        ))
    return result


def _validate_tape_provenance(
    bundle: Mapping[str, Any], sidecar_path: Path, manifest_path: Path
) -> None:
    provenance = bundle["provenance"]
    declared_sidecar = _resolve_binding_path(manifest_path, provenance["tape_root_sidecar_path"])
    if declared_sidecar != sidecar_path:
        raise ContractError("record provenance tape-root-sidecar path differs from explicit materializer input")
    if sha256_file(sidecar_path) != provenance["tape_root_sidecar_sha256"]:
        raise ContractError("record provenance tape-root-sidecar digest mismatch")
    rows = _read_tsv(sidecar_path, SIDECAR_COLUMNS, allow_empty=False)
    for field in ("source_card_sha256", "source_contract_sha256"):
        values = {row[field] for row in rows}
        if values != {provenance[field]}:
            raise ContractError(f"record provenance {field} does not close to every tape row")


def _load_runtime_tables(
    paths: Mapping[str, Path], tape: Sequence[TapeRow], run: Mapping[str, Any]
) -> tuple[
    dict[int, dict[str, str]], dict[int, dict[str, str]],
    dict[int, dict[str, str]], dict[int, dict[str, str]],
]:
    roots_rows = _read_tsv(paths["roots"], TABLE_COLUMNS["roots"], allow_empty=False)
    observation_rows = _read_tsv(
        paths["generated_observations"], TABLE_COLUMNS["generated_observations"], allow_empty=False
    )
    event_rows = _read_tsv(paths["events"], TABLE_COLUMNS["events"], allow_empty=False)
    truth_rows = _read_tsv(paths["truth_index"], TABLE_COLUMNS["truth_index"], allow_empty=True)
    footer_rows = _read_tsv(paths["footer"], TABLE_COLUMNS["footer"], allow_empty=False)
    count = len(tape)
    if any(row.family != run["family"] or row.mode != run["mode"] for row in tape):
        raise ContractError("tape family/mode differs from record-bundle run")
    if len(roots_rows) != count or len(observation_rows) != count or len(event_rows) != count or len(footer_rows) != 1:
        raise ContractError("tape/root/generated-observation/event/footer cardinality mismatch")
    if count != _parse_manifest_int(run["expected_event_count"], "run.expected_event_count", minimum=1):
        raise ContractError("run expected_event_count differs from tape")
    roots: dict[int, dict[str, str]] = {}
    observations: dict[int, dict[str, str]] = {}
    events: dict[int, dict[str, str]] = {}
    truth: dict[int, dict[str, str]] = {}
    for expected_id, (tape_row, root) in enumerate(zip(tape, roots_rows, strict=True), 1):
        event_id = _parse_int(root["simulation_event_id"], "roots.simulation_event_id", minimum=1)
        if event_id != expected_id or _parse_int(root["row_index0"], "roots.row_index0") != tape_row.row_index0:
            raise ContractError("runtime roots are not contiguous/in tape order")
        if _parse_int(root["eventlist_id"], "roots.eventlist_id", minimum=1) != tape_row.eventlist_id:
            raise ContractError("runtime root EventList ID mismatch")
        if root["stable_root_id"] != tape_row.stable_root_id or root["family"] != tape_row.family:
            raise ContractError("runtime root/tape identity mismatch")
        if root["benchmark_driver_id"] != tape_row.driver:
            raise ContractError("runtime benchmark driver differs from the exact assigned tape driver")
        if (root["driver_inference"] != "" or root["driver_inference_quality"] != "unavailable"
                or root["driver_inference_ambiguity_set"] != "[]"):
            raise ContractError("runtime rounded-native driver inference must remain empty/unavailable/[]")
        if root["raw_tape_line_sha256"] != tape_row.raw_line_sha256:
            raise ContractError("runtime raw tape hash mismatch")
        for key in ("expected_generated_tuple_sha256", "observed_generated_tuple_sha256"):
            if _digest(root[key], f"roots.{key}") != tape_row.expected_tuple_sha256:
                raise ContractError(f"runtime root {key} does not close to tape")
        _digest(root["observed_ia_init_tuple_sha256"], "roots.observed_ia_init_tuple_sha256")
        for key in ("generated_flag", "started_flag", "native_event_populated", "completed_flag"):
            if root[key] != "1":
                raise ContractError(f"runtime root has {key} != 1")
        if root["aborted_flag"] != "0" or root["control_flag"] not in {"0", "1"}:
            raise ContractError("aborted root or malformed control flag")
        if (root["control_flag"] == "1") != tape_row.control_flag:
            raise ContractError("runtime root control flag differs from pre-registered tape")
        roots[event_id] = root
    for expected_id, (tape_row, observation) in enumerate(zip(tape, observation_rows, strict=True), 1):
        event_id = _parse_int(observation["simulation_event_id"], "generated_observations.simulation_event_id", minimum=1)
        if event_id != expected_id or observation["stable_root_id"] != tape_row.stable_root_id:
            raise ContractError("generated observation/root order or identity mismatch")
        if _parse_int(observation["eventlist_id"], "generated_observations.eventlist_id", minimum=1) != tape_row.eventlist_id:
            raise ContractError("generated observation EventList ID mismatch")
        if observation["raw_eventlist_binary64_sha256"] != tape_row.eventlist_binary64_sha256:
            raise ContractError("runtime raw EventList binary64 digest differs from tape")
        serialized_ia_hash = _digest(observation["serialized_ia_quantized_sha256"], "serialized_ia_quantized_sha256")
        if serialized_ia_hash != roots[event_id]["observed_ia_init_tuple_sha256"]:
            raise ContractError("runtime serialized IA digest differs from root IA digest")
        observed_generated_binary64 = _digest(
            observation["observed_generated_binary64_sha256"], "observed_generated_binary64_sha256"
        )
        if observed_generated_binary64 != tape_row.generated_binary64_sha256:
            raise ContractError("runtime generated binary64 digest differs from normalized tape expectation")
        if _parse_int(observation["observed_generated_particle"], "observed generated particle", minimum=1) != tape_row.particle:
            raise ContractError("runtime generated particle differs from tape")
        if _parse_int(observation["serialized_ia_particle"], "serialized IA particle", minimum=1) != tape_row.particle:
            raise ContractError("runtime serialized IA particle differs from tape")
        if _parse_float(observation["serialized_ia_time_s"], "serialized IA time", minimum=0.0) != 0.0:
            raise ContractError("runtime serialized IA INIT time is not zero")
        position_energy_absolute = _parse_float(
            observation["serialized_ia_position_energy_abs_tolerance"],
            "serialized IA position/energy absolute tolerance", minimum=0.0,
        )
        direction_polarization_absolute = _parse_float(
            observation["serialized_ia_direction_polarization_abs_tolerance"],
            "serialized IA direction/polarization absolute tolerance", minimum=0.0,
        )
        relative = _parse_float(observation["serialized_ia_rel_tolerance"], "serialized IA relative tolerance", minimum=0.0)
        if (
            position_energy_absolute != 1.0e-6
            or direction_polarization_absolute != 1.0e-9
            or relative != 1.0e-9
            or observation["precision_contract"] != "GENERATED_BINARY64_BE_V1__IA_SERIALIZED_17G_FIELD_TOL_V2"
        ):
            raise ContractError("runtime generated-observation precision contract drift")
        generated_values = (
            ("observed_generated_excitation_keV", tape_row.excitation_keV, position_energy_absolute),
            ("observed_generated_source_time_s", tape_row.source_time_s, position_energy_absolute),
            *((f"observed_generated_{axis}_cm", value, position_energy_absolute) for axis, value in zip("xyz", tape_row.position_cm, strict=True)),
            *((f"observed_generated_d{axis}", value, direction_polarization_absolute) for axis, value in zip("xyz", tape_row.direction, strict=True)),
            *((f"observed_generated_p{axis}", value, direction_polarization_absolute) for axis, value in zip("xyz", tape_row.polarization, strict=True)),
            ("observed_generated_energy_keV", tape_row.energy_keV, position_energy_absolute),
            *((f"serialized_ia_{axis}_cm", value, position_energy_absolute) for axis, value in zip("xyz", tape_row.position_cm, strict=True)),
            *((f"serialized_ia_d{axis}", value, direction_polarization_absolute) for axis, value in zip("xyz", tape_row.direction, strict=True)),
            *((f"serialized_ia_p{axis}", value, direction_polarization_absolute) for axis, value in zip("xyz", tape_row.polarization, strict=True)),
            ("serialized_ia_energy_keV", tape_row.energy_keV, position_energy_absolute),
        )
        for field, expected, absolute in generated_values:
            actual = _parse_float(observation[field], f"generated_observations.{field}")
            if not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
                raise ContractError(f"runtime {field} lies outside the tape precision contract")
        native_event_time = _parse_float(observation["native_event_time_s"], "native event time", minimum=0.0)
        if not math.isclose(native_event_time, tape_row.source_time_s, rel_tol=1.0e-12, abs_tol=1.1e-9):
            raise ContractError("runtime native event time differs from tape source time")
        observations[event_id] = observation
    for expected_id, (tape_row, event) in enumerate(zip(tape, event_rows, strict=True), 1):
        event_id = _parse_int(event["simulation_event_id"], "events.simulation_event_id", minimum=1)
        if event_id != expected_id or event["stable_root_id"] != tape_row.stable_root_id:
            raise ContractError("event/root ordering or identity mismatch")
        if event["geometry"] != run["geometry"] or event["control_flag"] != roots[event_id]["control_flag"]:
            raise ContractError("event geometry/control mismatch")
        if _parse_float(event["source_time_s"], "events.source_time_s", minimum=0.0) != tape_row.source_time_s:
            raise ContractError("event source time differs from tape")
        if _parse_float(event["root_weight"], "root_weight", minimum=0.0) <= 0.0:
            raise ContractError("root weight must be positive")
        tes = _parse_float(event["tes_raw_keV"], "tes_raw_keV", minimum=0.0)
        multiplicity = _parse_int(event["tes_multiplicity"], "tes_multiplicity")
        raw_positive = event["raw_tes_positive"]
        control = event["control_flag"]
        required = event["truth_required"]
        if raw_positive not in {"0", "1"} or required not in {"0", "1"}:
            raise ContractError("malformed truth boolean")
        if (raw_positive == "1") != (tes > 0.0 and multiplicity > 0):
            raise ContractError("raw TES-positive flag/energy/multiplicity mismatch")
        if (required == "1") != (raw_positive == "1" or control == "1"):
            raise ContractError("truth_required is not exactly TES-positive or control")
        events[event_id] = event
    for row in truth_rows:
        event_id = _parse_int(row["simulation_event_id"], "truth_index.simulation_event_id", minimum=1)
        if event_id not in roots or event_id in truth:
            raise ContractError("truth index has unknown/duplicate event")
        if row["stable_root_id"] != roots[event_id]["stable_root_id"]:
            raise ContractError("truth index root join failure")
        if row["reason"] not in {"candidate", "control", "candidate+control"}:
            raise ContractError("invalid truth selection reason")
        if events[event_id]["truth_required"] != "1":
            raise ContractError("truth exists for a non-required event")
        expected_reason = (
            "candidate+control" if events[event_id]["raw_tes_positive"] == "1" and events[event_id]["control_flag"] == "1"
            else "candidate" if events[event_id]["raw_tes_positive"] == "1" else "control"
        )
        if row["reason"] != expected_reason:
            raise ContractError("truth reason differs from TES/control selection")
        _parse_int(row["offset"], "truth offset")
        _parse_int(row["length"], "truth length", minimum=1)
        _digest(row["sha256"], "truth fragment sha256")
        truth[event_id] = row
    expected_truth = {event_id for event_id, event in events.items() if event["truth_required"] == "1"}
    if set(truth) != expected_truth:
        raise ContractError("truth index is not exactly the TES-selected/control root set")
    footer = footer_rows[0]
    for key in ("arm", "geometry", "mode", "family"):
        if footer[key] != str(run[key]):
            raise ContractError(f"footer {key} differs from run")
    if footer["job_id"] != str(run["job_id"]):
        raise ContractError("footer job_id differs from run")
    if _parse_int(footer["shard_index"], "footer.shard_index") != _parse_manifest_int(run["shard_index"], "run.shard_index"):
        raise ContractError("footer shard mismatch")
    if _parse_int(footer["seed"], "footer.seed", minimum=1) != _parse_manifest_int(run["seed"], "run.seed", minimum=1):
        raise ContractError("footer seed mismatch")
    for key in (
        "tape_count", "generated_count", "started_count", "completed_count", "native_populated_count",
        "root_count", "ia_init_count", "native_observed_simulation_event_id_count",
        "native_observed_event_id_count",
    ):
        if _parse_int(footer[key], f"footer.{key}", minimum=1) != count:
            raise ContractError(f"footer {key} does not equal tape length")
    if footer["aborted_count"] != "0" or footer["finalized"] != "1":
        raise ContractError("footer has aborts or is not finalized")
    if _parse_float(footer["TT_s"], "footer.TT_s", minimum=0.0) <= 0.0:
        raise ContractError("footer TT is not positive")
    if footer["record_schema_sha256"] != sha256_file(RECORD_SCHEMA):
        raise ContractError("footer record schema hash drift")
    if footer["veto_whitelist_sha256"] != sha256_file(ACTIVE_WHITELIST):
        raise ContractError("footer whitelist hash drift")
    return roots, observations, events, truth


def _parse_ia(line: str) -> tuple[str, list[str]]:
    match = re.fullmatch(r"IA ([A-Z0-9_+\-]{4}) (.+)", line)
    if match is None:
        raise ContractError(f"malformed IA line: {line!r}")
    fields = [field.strip() for field in match.group(2).split(";")]
    if len(fields) != 23:
        raise ContractError("IA line does not have exactly 23 fields")
    for index in (0, 1, 2, 7, 15):
        _parse_int(fields[index], f"IA field {index}")
    for index in (*range(3, 7), *range(8, 15), *range(16, 23)):
        _parse_float(fields[index], f"IA field {index}")
    return match.group(1), fields


def _parse_ht(line: str, ia_ids: set[int]) -> None:
    if not line.startswith("HTsim "):
        raise ContractError(f"malformed/unsupported HT line: {line!r}")
    fields = [field.strip() for field in line[len("HTsim "):].split(";")]
    if len(fields) < 7:
        raise ContractError("HTsim lacks detector/position/energy/time/origin")
    _parse_int(fields[0], "HT detector type")
    for index in range(1, 6):
        value = _parse_float(fields[index], f"HT field {index}")
        if index == 4 and value < 0.0:
            raise ContractError("negative HT energy")
    origins = [_parse_int(value, "HT origin", minimum=1) for value in fields[6:]]
    if len(origins) != len(set(origins)) or any(origin not in ia_ids for origin in origins):
        raise ContractError("HT origins are duplicate or do not join to IA IDs")


def inspect_event(fragment: bytes, tape: TapeRow) -> EventSummary:
    if not fragment.endswith(b"\n") or b"\r" in fragment or b"\x00" in fragment:
        raise ContractError("SIM event fragment must be NUL-free LF and newline terminated")
    try:
        lines = fragment.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ContractError("SIM event fragment is not UTF-8") from error
    if not lines or lines[0] != "SE" or lines.count("SE") != 1:
        raise ContractError("SIM event does not have exactly one leading SE")
    if any(line == "EN" or line.startswith(("Type ", "Version ", "Geometry ")) for line in lines):
        raise ContractError("nested SIM envelope/footer in event fragment")
    id_lines = [line for line in lines if line.startswith("ID ")]
    if len(id_lines) != 1:
        raise ContractError("SIM event does not have exactly one ID")
    match = re.fullmatch(r"ID ([1-9][0-9]*) ([1-9][0-9]*)", id_lines[0])
    if match is None:
        raise ContractError("malformed SIM ID line")
    event_id, started_id = (int(match.group(1)), int(match.group(2)))
    ti_lines = [line for line in lines if line.startswith("TI ")]
    if len(ti_lines) != 1:
        raise ContractError("SIM event does not have exactly one TI")
    time_s = _parse_float(ti_lines[0][3:], "SIM TI", minimum=0.0)
    if time_s != _m_time_seconds(tape.source_time_s):
        raise ContractError("SIM TI is not the canonical MTime projection of tape source time")
    ia_lines = [line for line in lines if line.startswith("IA")]
    parsed_ias = [_parse_ia(line) for line in ia_lines]
    ia_ids = [_parse_int(fields[0], "IA ID", minimum=1) for _, fields in parsed_ias]
    if len(ia_ids) != len(set(ia_ids)):
        raise ContractError("duplicate IA ID")
    init = [(process, fields) for process, fields in parsed_ias if process == "INIT"]
    if len(init) != 1 or init[0][1][0] != "1" or init[0][1][1] != "0":
        raise ContractError("event does not contain exactly one IA INIT 1/0")
    ia_id_set = set(ia_ids)
    for process, fields in parsed_ias:
        origin = int(fields[1])
        if process != "INIT" and origin != 0 and origin not in ia_id_set:
            raise ContractError("IA origin does not join to an IA ID")
    ht_lines = [line for line in lines if line.startswith("HT")]
    for line in ht_lines:
        _parse_ht(line, ia_id_set)
    init_fields = init[0][1]
    ia_time_s = _parse_float(init_fields[3], "IA INIT time", minimum=0.0)
    if ia_time_s != 0.0:
        raise ContractError("primary IA INIT time is not zero")
    serialized_ia_hash = ia_init_hash(
        int(init_fields[15]), ia_time_s,
        tuple(float(init_fields[i]) for i in (4, 5, 6)),
        tuple(float(init_fields[i]) for i in (16, 17, 18)),
        tuple(float(init_fields[i]) for i in (19, 20, 21)),
        float(init_fields[22]),
    )
    generated_hash = tuple_hash(
        int(init_fields[15]), tape.excitation_keV, tape.source_time_s,
        tuple(float(init_fields[i]) for i in (4, 5, 6)),
        tuple(float(init_fields[i]) for i in (16, 17, 18)),
        tuple(float(init_fields[i]) for i in (19, 20, 21)),
        float(init_fields[22]),
    )
    if generated_hash != tape.expected_tuple_sha256:
        raise ContractError("SIM IA INIT spatial/kinematic tuple differs from tape-generated tuple")
    return EventSummary(
        event_id, started_id, time_s, len(parsed_ias), len(ht_lines), generated_hash, serialized_ia_hash
    )


def _m_time_parts(value: float) -> tuple[int, int]:
    """Project a positive binary64 second value as installed MTime::Set(double)."""
    if not math.isfinite(value) or value < 0.0:
        raise ContractError("invalid nonnegative MTime source time")
    seconds = math.trunc(value)
    fraction = math.floor((value - seconds) * 1_000_000_000.0 + 0.5)
    if fraction >= 1_000_000_000:
        seconds += 1
        fraction -= 1_000_000_000
    return seconds, fraction


def _m_time_seconds(value: float) -> float:
    seconds, fraction = _m_time_parts(value)
    return seconds + fraction / 1_000_000_000.0


def _time_text(value: float) -> str:
    seconds, fraction = _m_time_parts(value)
    return f"{seconds}.{fraction:09d}"


def _scientific(value: float, precision: int, width: int) -> str:
    return f"{value:{width}.{precision}e}"


def _init_line(tape: TapeRow) -> str:
    # Exact MSimIA::ToSimString(ScientificPrecision=17, Version=101) layout.
    time0 = _scientific(0.0, 24, 28)
    position = [_scientific(value, 17, 24) for value in tape.position_cm]
    norm = math.sqrt(math.fsum(value * value for value in tape.direction))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ContractError("cannot serialize zero/nonfinite primary direction")
    direction = [_scientific(value / norm, 17, 24) for value in tape.direction]
    polarization = [_scientific(value, 17, 24) for value in tape.polarization]
    zeros_dir = [_scientific(0.0, 17, 24)] * 3
    zero_energy = _scientific(0.0, 17, 24)
    energy = _scientific(tape.energy_keV, 17, 24)
    fields = [
        " 1", " 0", "0", time0, *position, "0", *zeros_dir, *zeros_dir, zero_energy,
        str(tape.particle), *direction, *polarization, energy,
    ]
    if len(fields) != 23:
        raise AssertionError("INIT formatter field count")
    return "IA INIT " + ";".join(fields)


def minimal_event(tape: TapeRow, event_id: int) -> bytes:
    fragment = (
        f"SE\nID {event_id} {event_id}\nTI {_time_text(tape.source_time_s)}\n"
        f"ED 0\nEC 0\nNS 0\n{_init_line(tape)}\n"
    ).encode("utf-8")
    summary = inspect_event(fragment, tape)
    if summary.event_id != event_id or summary.started_id != event_id or summary.ia_count != 1 or summary.ht_count != 0:
        raise AssertionError("generated minimal event failed self-validation")
    return fragment


def _validate_truth_blob(
    blob: bytes,
    rows: Mapping[int, dict[str, str]],
    tape: Sequence[TapeRow],
    observations: Mapping[int, dict[str, str]],
) -> dict[int, tuple[bytes, EventSummary]]:
    if b"\r" in blob or b"\x00" in blob:
        raise ContractError("truth stream must be NUL-free LF")
    result: dict[int, tuple[bytes, EventSummary]] = {}
    cursor = 0
    for event_id in sorted(rows):
        row = rows[event_id]
        offset = int(row["offset"])
        length = int(row["length"])
        if offset != cursor or offset + length > len(blob):
            raise ContractError("truth fragments are not gap-free/in event order/in bounds")
        fragment = blob[offset:offset + length]
        if sha256_bytes(fragment) != row["sha256"]:
            raise ContractError("truth fragment SHA-256 mismatch")
        summary = inspect_event(fragment, tape[event_id - 1])
        if summary.event_id != event_id or summary.started_id != event_id:
            raise ContractError("native truth ID differs from runtime root")
        if summary.serialized_ia_tuple_sha256 != observations[event_id]["serialized_ia_quantized_sha256"]:
            raise ContractError("native truth IA INIT hash differs from generated-observation record")
        if summary.time_s != _parse_float(observations[event_id]["native_event_time_s"], "native event time"):
            raise ContractError("native truth TI differs from generated-observation native event time")
        result[event_id] = (fragment, summary)
        cursor += length
    if cursor != len(blob):
        raise ContractError("truth stream has unindexed trailing bytes")
    return result


def _sim_header(geometry: Path, geometry_sha256: str, tape_sha256: str, sidecar_sha256: str, bundle_sha256: str) -> bytes:
    geometry_text = os.fspath(geometry)
    if "\n" in geometry_text or "\r" in geometry_text:
        raise ContractError("geometry path contains a newline")
    return (
        "# M05 deterministic standalone SIM materialization\n"
        f"# Materializer {MATERIALIZER_VERSION}\n"
        f"# GeometrySHA256 {geometry_sha256}\n"
        f"# TapeSHA256 {tape_sha256}\n"
        f"# TapeRootSidecarSHA256 {sidecar_sha256}\n"
        f"# RecordBundleSHA256 {bundle_sha256}\n\n"
        "Type       SIM\n"
        f"Version    {SIM_VERSION}\n"
        f"Geometry   {geometry_text}\n\n"
        "MEGAlib    4.02.00\n\n"
        "TB 0\n\n"
    ).encode("utf-8")


def inspect_standalone(sim: bytes, index_rows: Sequence[Mapping[str, str]], tape: Sequence[TapeRow], geometry: Path) -> dict[str, Any]:
    if b"\r" in sim or b"\x00" in sim or not sim.endswith(b"\n"):
        raise ContractError("standalone SIM is not NUL-free LF/newline terminated")
    prefix = sim.split(b"SE\n", 1)[0].decode("utf-8")
    lines = prefix.splitlines()
    if sum(line.startswith("Type ") for line in lines) != 1 or "Type       SIM" not in lines:
        raise ContractError("standalone SIM lacks exact Type SIM")
    if sum(line.startswith("Version ") for line in lines) != 1 or f"Version    {SIM_VERSION}" not in lines:
        raise ContractError("standalone SIM lacks exact Version")
    if sum(line.startswith("Geometry ") for line in lines) != 1 or f"Geometry   {geometry}" not in lines:
        raise ContractError("standalone SIM lacks exact Geometry")
    if sim.count(b"\nEN\n") != 1:
        raise ContractError("standalone SIM does not have exactly one EN")
    if len(index_rows) != len(tape):
        raise ContractError("standalone index/tape count mismatch")
    total_ia = total_ht = 0
    for event_id, (row, tape_row) in enumerate(zip(index_rows, tape, strict=True), 1):
        if row["schema"] != MATERIALIZER_VERSION or int(row["simulation_event_id"]) != event_id:
            raise ContractError("standalone index schema/order mismatch")
        if int(row["eventlist_id"]) != tape_row.eventlist_id or row["stable_root_id"] != tape_row.stable_root_id:
            raise ContractError("standalone index/root join mismatch")
        if row["raw_tape_line_sha256"] != tape_row.raw_line_sha256 or row["expected_generated_tuple_sha256"] != tape_row.expected_tuple_sha256:
            raise ContractError("standalone index tape line/generated tuple hash mismatch")
        if row["expected_eventlist_binary64_sha256"] != tape_row.eventlist_binary64_sha256:
            raise ContractError("standalone index EventList binary64 hash mismatch")
        if row["expected_generated_binary64_sha256"] != tape_row.generated_binary64_sha256:
            raise ContractError("standalone index expected generated binary64 hash mismatch")
        serialized_ia_hash = _digest(row["serialized_ia_quantized_sha256"], "index serialized IA hash")
        if serialized_ia_hash != row["init_tuple_sha256"]:
            raise ContractError("standalone index serialized IA hash disagrees with INIT hash")
        observed_generated_binary64 = _digest(
            row["observed_generated_binary64_sha256"], "index observed generated binary64 hash"
        )
        if observed_generated_binary64 != tape_row.generated_binary64_sha256:
            raise ContractError("standalone index observed generated binary64 hash differs from tape expectation")
        offset, length = int(row["standalone_offset"]), int(row["standalone_length"])
        fragment = sim[offset:offset + length]
        if len(fragment) != length or sha256_bytes(fragment) != row["standalone_sha256"]:
            raise ContractError("standalone event byte range/hash mismatch")
        summary = inspect_event(fragment, tape_row)
        if summary.event_id != event_id or summary.started_id != event_id:
            raise ContractError("standalone event ID mismatch")
        if summary.ia_count != int(row["ia_count"]) or summary.ht_count != int(row["ht_count"]):
            raise ContractError("standalone IA/HT count mismatch")
        if summary.serialized_ia_tuple_sha256 != row["init_tuple_sha256"]:
            raise ContractError("standalone INIT tuple hash mismatch")
        if summary.generated_tuple_sha256 != row["expected_generated_tuple_sha256"]:
            raise ContractError("standalone generated-view tuple hash mismatch")
        total_ia += summary.ia_count
        total_ht += summary.ht_count
    event_end = max(int(row["standalone_offset"]) + int(row["standalone_length"]) for row in index_rows)
    if not sim[event_end:].startswith(b"EN\n"):
        raise ContractError("EN does not immediately follow final event")
    if sim.count(b"SE\n") != len(tape) or sim.count(b"\nID ") != len(tape):
        raise ContractError("standalone raw SE/ID counts differ from tape")
    return {
        "event_count": len(tape),
        "materialized_written_se_count": len(tape),
        "materialized_written_id_count": len(tape),
        "ia_count": total_ia,
        "ht_count": total_ht,
    }


def _index_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    lines = ["\t".join(OUTPUT_INDEX_COLUMNS)]
    for row in rows:
        if set(row) != set(OUTPUT_INDEX_COLUMNS):
            raise AssertionError("output index row keys")
        values = [str(row[name]) for name in OUTPUT_INDEX_COLUMNS]
        if any("\t" in value or "\n" in value or "\r" in value for value in values):
            raise ContractError("unsafe output index value")
        lines.append("\t".join(values))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _reserve(path: Path) -> int:
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)


def _durable_write(path: Path, payload: bytes) -> None:
    descriptor = _reserve(path)
    # A write/flush/fsync failure must retain its diagnostic bytes inside the
    # quarantined *.partial transaction.  Never delete or expose it as final.
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _publish_directory(final_dir: Path, files: Sequence[tuple[str, bytes]]) -> None:
    """Durably publish one directory with one atomic namespace transition."""
    if not files or files[-1][0] != "manifest.json":
        raise AssertionError("manifest.json must be the final commit-marker write")
    if len({name for name, _ in files}) != len(files):
        raise AssertionError("duplicate publication member")
    parent = final_dir.parent
    partial_dir = final_dir.with_name(final_dir.name + ".partial")
    _check_no_symlink(parent, must_exist=True, expect_file=False)
    if final_dir.exists() or final_dir.is_symlink() or partial_dir.exists() or partial_dir.is_symlink():
        raise FileExistsError(f"write-once output envelope already exists: {final_dir}")
    os.mkdir(partial_dir, 0o775)
    try:
        for name, payload in files:
            if Path(name).name != name or name in {".", ".."}:
                raise ContractError("unsafe materialization member name")
            member = partial_dir / name
            _durable_write(member, payload)
            if member.stat().st_size != len(payload) or sha256_file(member) != sha256_bytes(payload):
                raise ContractError(f"partial size/hash verification failed: {member}")
        directory_fd = os.open(partial_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            rename_no_replace(partial_dir, final_dir)
            fsync_directory(parent)
        except BaseException:
            # A namespace rename followed by parent-fsync failure must not
            # leave a final-looking directory. Move it to an unmistakable,
            # no-replace quarantine name and retain every byte for audit.
            if final_dir.exists() and not partial_dir.exists():
                quarantine_directory_no_replace(final_dir)
            raise
    except BaseException:
        # Failures retain only *.partial or *.failed evidence, never authority.
        raise


def materialize(
    *,
    record_bundle: Path,
    tape_path: Path,
    tape_roots_path: Path,
    geometry_path: Path,
    geometry_sha256: str,
    output_prefix: Path,
    geometry_classification_path: Path = PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH,
    _verify_tape_authorities: bool = True,
) -> dict[str, Any]:
    try:
        record_validation = validate_bundle(
            record_bundle, geometry_classification_path=geometry_classification_path
        )
    except RecordValidationError as error:
        raise ContractError(f"m05cc-v2 executable record validation failed: {error}") from error
    bundle, paths, manifest_path = _load_bundle(record_bundle)
    tape_path = _check_no_symlink(tape_path)
    tape_roots_path = _check_no_symlink(tape_roots_path)
    geometry_path = _check_no_symlink(geometry_path)
    if sha256_file(geometry_path) != _digest(geometry_sha256, "geometry_sha256"):
        raise ContractError("geometry SHA-256 mismatch")
    tape = _load_tape(tape_path, tape_roots_path, verify_authorities=_verify_tape_authorities)
    _validate_tape_provenance(bundle, tape_roots_path, manifest_path)
    roots, observations, events, truth_rows = _load_runtime_tables(paths, tape, bundle["run"])
    truth_blob = paths["truth_stream"].read_bytes()
    native = _validate_truth_blob(truth_blob, truth_rows, tape, observations)

    output_prefix = Path(os.path.abspath(os.fspath(output_prefix)))
    final_dir = Path(str(output_prefix) + ".standalone")
    sim_path = final_dir / "events.sim"
    index_path = final_dir / "index.tsv"
    output_manifest_path = final_dir / "manifest.json"
    if "\n" in os.fspath(final_dir) or "\r" in os.fspath(final_dir):
        raise ContractError("unsafe output path")
    output_parent = final_dir.parent
    if not output_parent.exists():
        raise ContractError("output parent must already exist")
    _check_no_symlink(output_parent, expect_file=False)

    input_hashes = {
        "record_bundle": sha256_file(manifest_path),
        "tape": sha256_file(tape_path),
        "tape_roots": sha256_file(tape_roots_path),
        "geometry": geometry_sha256,
        "geometry_classification": sha256_file(_check_no_symlink(geometry_classification_path)),
    }
    sim_parts = [_sim_header(
        geometry_path, geometry_sha256, input_hashes["tape"], input_hashes["tape_roots"], input_hashes["record_bundle"]
    )]
    index_rows: list[dict[str, Any]] = []
    offset = len(sim_parts[0])
    native_count = 0
    total_ia = total_ht = 0
    for event_id, tape_row in enumerate(tape, 1):
        if event_id in native:
            fragment, summary = native[event_id]
            representation = "native"
            reason = truth_rows[event_id]["reason"]
            source_offset = truth_rows[event_id]["offset"]
            source_length = truth_rows[event_id]["length"]
            source_sha = truth_rows[event_id]["sha256"]
            native_count += 1
        else:
            fragment = minimal_event(tape_row, event_id)
            summary = inspect_event(fragment, tape_row)
            representation = "minimal_init"
            reason = "nonselected"
            source_offset = -1
            source_length = 0
            source_sha = "-"
        fragment_sha = sha256_bytes(fragment)
        if representation == "native" and fragment_sha != source_sha:
            raise AssertionError("native fragment changed before embedding")
        index_rows.append({
            "schema": MATERIALIZER_VERSION,
            "simulation_event_id": event_id,
            "eventlist_id": tape_row.eventlist_id,
            "stable_root_id": tape_row.stable_root_id,
            "representation": representation,
            "selection_reason": reason,
            "standalone_offset": offset,
            "standalone_length": len(fragment),
            "standalone_sha256": fragment_sha,
            "source_truth_offset": source_offset,
            "source_truth_length": source_length,
            "source_truth_sha256": source_sha,
            "ia_count": summary.ia_count,
            "ht_count": summary.ht_count,
            "init_tuple_sha256": summary.serialized_ia_tuple_sha256,
            "raw_tape_line_sha256": tape_row.raw_line_sha256,
            "expected_generated_tuple_sha256": tape_row.expected_tuple_sha256,
            "expected_eventlist_binary64_sha256": tape_row.eventlist_binary64_sha256,
            "expected_generated_binary64_sha256": tape_row.generated_binary64_sha256,
            "observed_generated_binary64_sha256": observations[event_id]["observed_generated_binary64_sha256"],
            "serialized_ia_quantized_sha256": observations[event_id]["serialized_ia_quantized_sha256"],
        })
        sim_parts.append(fragment)
        offset += len(fragment)
        total_ia += summary.ia_count
        total_ht += summary.ht_count
    sim_parts.append(f"EN\n\nTE {_time_text(tape[-1].source_time_s)}\nTS {len(tape)}\n".encode("utf-8"))
    sim_payload = b"".join(sim_parts)
    index_payload = _index_bytes(index_rows)
    index_loaded = [dict(row) for row in index_rows]
    closure = inspect_standalone(sim_payload, index_loaded, tape, geometry_path)
    expectation_lines = [
        f"{row['simulation_event_id']}:{row['simulation_event_id']}:{row['ia_count']}:{row['ht_count']}:{row['standalone_sha256']}\n"
        for row in index_rows
    ]
    roundtrip_expectation_sha = sha256_bytes("".join(expectation_lines).encode("utf-8"))
    output_manifest = {
        "schema_version": MATERIALIZER_VERSION,
        "status": "PASS__PYTHON_STRICT_MATERIALIZATION__EXTERNAL_CONSUMER_ATTESTATIONS_REQUIRED_PER_OUTPUT",
        "sim_envelope": {"type": "SIM", "version": SIM_VERSION, "geometry": os.fspath(geometry_path), "geometry_sha256": geometry_sha256},
        "input": {
            "record_bundle": {"path": os.fspath(manifest_path), "sha256": input_hashes["record_bundle"], "size_bytes": manifest_path.stat().st_size},
            "tape": {"path": os.fspath(tape_path), "sha256": input_hashes["tape"], "size_bytes": tape_path.stat().st_size},
            "tape_roots": {"path": os.fspath(tape_roots_path), "sha256": input_hashes["tape_roots"], "size_bytes": tape_roots_path.stat().st_size},
            "truth_stream": {"path": os.fspath(paths["truth_stream"]), "sha256": sha256_file(paths["truth_stream"]), "size_bytes": len(truth_blob)},
            "native_dat": {
                "path": os.fspath(paths["native_dat"]),
                "sha256": sha256_file(paths["native_dat"]),
                "size_bytes": paths["native_dat"].stat().st_size,
            },
            "geometry_classification": {
                "path": os.fspath(geometry_classification_path),
                "sha256": input_hashes["geometry_classification"],
                "size_bytes": geometry_classification_path.stat().st_size,
            },
        },
        "counts": {
            **closure,
            "native_event_count": native_count,
            "minimal_init_event_count": len(tape) - native_count,
            "truth_index_count": len(truth_rows),
        },
        "record_validation": record_validation,
        "output": {
            "sim": {"path": os.fspath(sim_path), "sha256": sha256_bytes(sim_payload), "size_bytes": len(sim_payload)},
            "index": {"path": os.fspath(index_path), "sha256": sha256_bytes(index_payload), "size_bytes": len(index_payload), "row_count": len(index_rows)},
        },
        "mfileeventssim_roundtrip": {
            "required": True,
            "expected_event_ia_ht_hash_sha256": roundtrip_expectation_sha,
            "consumer_source": os.fspath(PACKAGE / "code/mfileeventssim_roundtrip.cc"),
        },
        "revan_consumer": {
            "required_for_m05_completion": True,
            "gate_source": os.fspath(PACKAGE / "code/revan_zero_transport_gate.py"),
            "frozen_configuration": {
                "path": os.fspath(FROZEN_REVAN_CONFIG),
                "sha256": sha256_file(_check_no_symlink(FROZEN_REVAN_CONFIG)),
                "size_bytes": FROZEN_REVAN_CONFIG.stat().st_size,
            },
            "attestation_status": "REQUIRED_PER_OUTPUT_NOT_RUN_BY_MATERIALIZER",
        },
        "invariants": {
            "native_fragments_embedded_byte_exact": True,
            "nonselected_roots_have_one_init_and_zero_ht": True,
            "native_object_event_ids_close_to_tape": True,
            "materialized_written_se_id_init_counts_close_to_tape": True,
            "transport_events_launched": 0,
            "independent_tape_authority_replayed": _verify_tape_authorities,
        },
    }
    manifest_payload = canonical_json_bytes(output_manifest)
    # The manifest is written last inside a quarantined directory; one atomic
    # directory rename then exposes the complete envelope.
    _publish_directory(
        final_dir,
        (("events.sim", sim_payload), ("index.tsv", index_payload), ("manifest.json", manifest_payload)),
    )
    return output_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-bundle", required=True, type=Path)
    parser.add_argument("--tape", required=True, type=Path)
    parser.add_argument("--tape-roots", required=True, type=Path)
    parser.add_argument("--geometry", required=True, type=Path)
    parser.add_argument("--geometry-sha256", required=True)
    parser.add_argument(
        "--geometry-classification", type=Path, default=PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH,
        help="canonical zero-transport geometry-classification manifest bound by the record bundle",
    )
    parser.add_argument("--output-prefix", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = materialize(
        record_bundle=args.record_bundle,
        tape_path=args.tape,
        tape_roots_path=args.tape_roots,
        geometry_path=args.geometry,
        geometry_sha256=args.geometry_sha256,
        output_prefix=args.output_prefix,
        geometry_classification_path=args.geometry_classification,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
