#!/usr/bin/env python3
"""Fail-closed validator for the m05cc-v2 physical TSV bundle.

This is deliberately dependency-free.  The JSON schema is both a published
contract and the executable source of exact TSV headers/scalar rules.  Cross-
table physics, hash, key, foreign-key, count, block, veto, and POST-time rules
are enforced below because JSON Schema alone cannot express them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PACKAGE = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PACKAGE / "schema/m05cc_v2.record_schema.json"
WHITELIST_PATH = PACKAGE / "schema/active_volume_whitelist_v1.json"
PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH = PACKAGE / "transport_preflight_v1/geometry_classification_manifest.json"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX16_RE = re.compile(r"^[0-9a-f]{16}$")
INT_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
FLOAT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TES_UID_RE = re.compile(r"^TP_L[0-5]_[0-9]+:[^\t\r\n/:]+:[0-9]+(?:/[^\t\r\n/:]+:[^\t\r\n/:]+:[0-9]+)*$")
FLOAT_ABS_TOL = 1.0e-6
FLOAT_REL_TOL = 1.0e-9


class ValidationError(ValueError):
    """A deterministic record-contract violation."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValidationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _assert_exact_keys(value: Mapping[str, Any], required: set[str], context: str) -> None:
    actual = set(value)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise ValidationError(f"{context}: exact properties mismatch; missing={missing}, extra={extra}")


def _manifest_shape(manifest: dict[str, Any], schema: dict[str, Any]) -> None:
    required = set(schema["required"])
    _assert_exact_keys(manifest, required, "manifest")
    if manifest["schema_version"] != "m05cc-v2-record-bundle":
        raise ValidationError("manifest: wrong schema_version")
    for name in ("record_schema_sha256", "veto_whitelist_sha256", "geometry_classification_sha256"):
        if not isinstance(manifest[name], str) or SHA256_RE.fullmatch(manifest[name]) is None:
            raise ValidationError(f"manifest.{name}: invalid SHA-256")
    provenance = manifest["provenance"]
    if not isinstance(provenance, dict):
        raise ValidationError("manifest.provenance must be an object")
    provenance_fields = {
        "geometry_bundle_sha256", "tape_root_sidecar_sha256",
        "tape_root_sidecar_path",
        "source_card_sha256", "source_contract_sha256",
    }
    _assert_exact_keys(provenance, provenance_fields, "manifest.provenance")
    for name in provenance_fields - {"tape_root_sidecar_path"}:
        if not isinstance(provenance[name], str) or SHA256_RE.fullmatch(provenance[name]) is None:
            raise ValidationError(f"manifest.provenance.{name}: invalid SHA-256")
    if not isinstance(provenance["tape_root_sidecar_path"], str) or not provenance["tape_root_sidecar_path"]:
        raise ValidationError("manifest.provenance.tape_root_sidecar_path: invalid")

    run = manifest["run"]
    if not isinstance(run, dict):
        raise ValidationError("manifest.run must be an object")
    run_schema = schema["properties"]["run"]
    _assert_exact_keys(run, set(run_schema["required"]), "manifest.run")
    run_enums = {
        "arm": {"C"},
        "geometry": {"mass_model_511", "s3d_o8"},
        "mode": {"instant", "buildup"},
        "family": {"gamma", "n", "eminus", "eplus", "alpha", "muplus", "muminus"},
        "active_block_coverage": {"geometry_specific"},
    }
    for name, values in run_enums.items():
        if run[name] not in values:
            raise ValidationError(f"manifest.run.{name}: invalid enum {run[name]!r}")
    if not isinstance(run["job_id"], str) or JOB_ID_RE.fullmatch(run["job_id"]) is None:
        raise ValidationError("manifest.run.job_id: malformed")
    for name, minimum, maximum in (
        ("shard_index", 0, None),
        ("seed", 1, 2_147_483_646),
        ("expected_event_count", 1, None),
    ):
        value = run[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum or (maximum is not None and value > maximum):
            raise ValidationError(f"manifest.run.{name}: invalid integer")

    declared_tables = set(schema["properties"]["tables"]["required"])
    tables = manifest["tables"]
    if not isinstance(tables, dict):
        raise ValidationError("manifest.tables must be an object")
    _assert_exact_keys(tables, declared_tables, "manifest.tables")
    for name, binding in tables.items():
        _validate_binding(binding, f"manifest.tables.{name}", count_name="row_count")
    blobs = manifest["blobs"]
    if not isinstance(blobs, dict):
        raise ValidationError("manifest.blobs must be an object")
    _assert_exact_keys(blobs, {"truth_stream", "native_dat"}, "manifest.blobs")
    for name in ("truth_stream", "native_dat"):
        _validate_binding(blobs[name], f"manifest.blobs.{name}", count_name="size_bytes")


def _validate_binding(binding: Any, context: str, *, count_name: str) -> None:
    if not isinstance(binding, dict):
        raise ValidationError(f"{context}: must be an object")
    _assert_exact_keys(binding, {"path", "sha256", count_name}, context)
    if not isinstance(binding["path"], str) or not binding["path"]:
        raise ValidationError(f"{context}.path: invalid")
    if not isinstance(binding["sha256"], str) or SHA256_RE.fullmatch(binding["sha256"]) is None:
        raise ValidationError(f"{context}.sha256: invalid")
    count = binding[count_name]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValidationError(f"{context}.{count_name}: invalid")


def _bound_path(manifest_path: Path, lexical: str, context: str) -> Path:
    relative = Path(lexical)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValidationError(f"{context}: path must be a normalized relative path")
    root = manifest_path.parent.resolve()
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink():
                raise ValidationError(f"{context}: symlink path component is forbidden: {current}")
        except OSError as exc:
            raise ValidationError(f"{context}: cannot lstat path component: {exc}") from exc
    resolved = current.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"{context}: path escapes manifest directory") from exc
    if not resolved.is_file():
        raise ValidationError(f"{context}: bound file is absent: {resolved}")
    return resolved


def _parse_int(raw: str, context: str) -> int:
    if INT_RE.fullmatch(raw) is None:
        raise ValidationError(f"{context}: malformed nonnegative integer {raw!r}")
    return int(raw)


def _parse_float(raw: str, context: str) -> float:
    if FLOAT_RE.fullmatch(raw) is None:
        raise ValidationError(f"{context}: malformed canonical finite float {raw!r}")
    value = float(raw)
    if not math.isfinite(value):
        raise ValidationError(f"{context}: nonfinite float")
    return value


def _parse_cell(raw: str, rule: Mapping[str, Any], context: str) -> Any:
    kind = rule["type"]
    if kind in {"nonnegative_int", "positive_int", "bounded_int"}:
        value = _parse_int(raw, context)
        minimum = rule.get("minimum", 1 if kind == "positive_int" else 0)
        maximum = rule.get("maximum")
        if value < minimum or (maximum is not None and value > maximum):
            raise ValidationError(f"{context}: integer outside range")
        return value
    if kind in {"finite_float", "nonnegative_float", "positive_float", "optional_nonnegative_float"}:
        if kind == "optional_nonnegative_float" and raw == "":
            return None
        value = _parse_float(raw, context)
        if kind in {"nonnegative_float", "optional_nonnegative_float"} and value < 0.0:
            raise ValidationError(f"{context}: negative value")
        if kind == "positive_float" and value <= 0.0:
            raise ValidationError(f"{context}: value is not positive")
        return value
    if kind == "bool01":
        if raw not in {"0", "1"}:
            raise ValidationError(f"{context}: expected 0 or 1")
        return int(raw)
    if kind == "sha256":
        if SHA256_RE.fullmatch(raw) is None:
            raise ValidationError(f"{context}: malformed SHA-256")
        return raw
    if kind == "hex16":
        if HEX16_RE.fullmatch(raw) is None:
            raise ValidationError(f"{context}: malformed 16-digit lowercase hex")
        return raw
    if kind == "enum":
        if raw not in rule["values"]:
            raise ValidationError(f"{context}: invalid enum {raw!r}")
        return raw
    if kind == "const":
        if raw != rule["value"]:
            raise ValidationError(f"{context}: expected constant {rule['value']!r}")
        return raw
    if kind == "nonempty_text":
        if not raw or any(char in raw for char in "\t\r\n"):
            raise ValidationError(f"{context}: expected nonempty escaped text")
        return raw
    if kind == "optional_text":
        if any(char in raw for char in "\t\r\n"):
            raise ValidationError(f"{context}: invalid escaped text")
        return raw
    if kind == "canonical_string_array":
        try:
            value = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValidationError(f"{context}: malformed JSON string array") from exc
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise ValidationError(f"{context}: expected nonempty-string array")
        if value != sorted(set(value), key=lambda item: item.encode("utf-8")):
            raise ValidationError(f"{context}: array must be sorted and unique")
        if json.dumps(value, ensure_ascii=False, separators=(",", ":")) != raw:
            raise ValidationError(f"{context}: array is not canonical JSON")
        return value
    if kind == "ancestry_edge_chain":
        if not raw:
            raise ValidationError(f"{context}: empty ancestry chain")
        edges: list[tuple[int, int]] = []
        for item in raw.split(","):
            if item.count(":") != 1:
                raise ValidationError(f"{context}: malformed ancestry edge")
            tid_raw, pid_raw = item.split(":")
            tid = _parse_int(tid_raw, context)
            pid = _parse_int(pid_raw, context)
            if tid <= 0 or tid == pid:
                raise ValidationError(f"{context}: invalid ancestry edge")
            edges.append((tid, pid))
        if len({tid for tid, _ in edges}) != len(edges):
            raise ValidationError(f"{context}: duplicate ancestry track ID")
        if edges[0][1] != 0 or any(edges[index - 1][0] != edges[index][1] for index in range(1, len(edges))):
            raise ValidationError(f"{context}: ancestry edges do not form one root-to-leaf chain")
        return edges
    if kind == "tes_uid":
        if TES_UID_RE.fullmatch(raw) is None:
            raise ValidationError(f"{context}: malformed TES touchable UID")
        return raw
    if kind == "job_id":
        if JOB_ID_RE.fullmatch(raw) is None:
            raise ValidationError(f"{context}: malformed job ID")
        return raw
    raise ValidationError(f"{context}: unsupported schema scalar type {kind!r}")


def _read_table(path: Path, name: str, contract: Mapping[str, Any], declared_rows: int) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"{name}: cannot read TSV: {exc}") from exc
    if b"\r" in payload or b"\x00" in payload:
        raise ValidationError(f"{name}: only UTF-8 LF text is allowed")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{name}: invalid UTF-8") from exc
    if not text.endswith("\n"):
        raise ValidationError(f"{name}: missing final LF")
    lines = text.splitlines()
    if not lines:
        raise ValidationError(f"{name}: missing header")
    expected_header = contract["header"]
    header = lines[0].split("\t")
    if header != expected_header:
        raise ValidationError(f"{name}: exact header mismatch; expected={expected_header}, actual={header}")
    if len(header) != len(set(header)):
        raise ValidationError(f"{name}: duplicate header column")
    rows: list[dict[str, Any]] = []
    reader = csv.reader(lines[1:], delimiter="\t", quoting=csv.QUOTE_NONE, strict=True)
    try:
        for line_number, fields in enumerate(reader, start=2):
            if len(fields) != len(header):
                raise ValidationError(f"{name}:{line_number}: field count {len(fields)} != {len(header)}")
            raw_row = dict(zip(header, fields, strict=True))
            typed = {
                column: _parse_cell(raw_row[column], contract["columns"][column], f"{name}:{line_number}:{column}")
                for column in header
            }
            rows.append(typed)
    except csv.Error as exc:
        raise ValidationError(f"{name}: malformed TSV: {exc}") from exc
    if len(rows) != declared_rows:
        raise ValidationError(f"{name}: declared row_count={declared_rows}, actual={len(rows)}")
    if not contract["allow_empty"] and not rows:
        raise ValidationError(f"{name}: empty table forbidden")
    _validate_keys(name, rows, [contract["primary_key"], *contract.get("unique_keys", [])])
    return rows


def _validate_keys(name: str, rows: Sequence[Mapping[str, Any]], keys: Sequence[Sequence[str]]) -> None:
    def freeze(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(freeze(item) for item in value)
        if isinstance(value, dict):
            return tuple((key, freeze(item)) for key, item in sorted(value.items()))
        return value

    if rows and len({tuple(freeze(row[column]) for column in rows[0]) for row in rows}) != len(rows):
        raise ValidationError(f"{name}: duplicate exact row")
    for key in keys:
        seen: set[tuple[Any, ...]] = set()
        for row in rows:
            value = tuple(row[column] for column in key)
            if value in seen:
                raise ValidationError(f"{name}: duplicate key {list(key)}={value!r}")
            seen.add(value)


def _near(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def _sum(values: Iterable[float]) -> float:
    return math.fsum(values)


def _expect_near(actual: float, expected: float, context: str) -> None:
    if not _near(actual, expected):
        raise ValidationError(f"{context}: {actual:.17g} != recomputed {expected:.17g}")


def _load_whitelist(path: Path) -> tuple[dict[str, Any], dict[str, tuple[str, str, str]]]:
    value = strict_json(path)
    expected = {
        "schema_version", "detector_uid_scheme", "active_detector_types",
        "tes_physical_volume_regex", "kapton_diagnostic_rule", "mass_csi_physical_volumes",
        "o8_bgo_physical_volumes", "o8_plastic_physical_volumes", "selection_rule",
        "passive_exclusions",
    }
    _assert_exact_keys(value, expected, "active whitelist")
    if value["schema_version"] != "m05-active-volume-whitelist-v1":
        raise ValidationError("active whitelist: wrong schema_version")
    if value["detector_uid_scheme"] != "<detector_type>:<physical_volume>":
        raise ValidationError("active whitelist: detector UID scheme drift")
    if value["active_detector_types"] != ["mass_csi", "o8_bgo", "o8_plastic"]:
        raise ValidationError("active whitelist: detector type order drift")
    mapping: dict[str, tuple[str, str, str]] = {}
    seen_volumes: set[str] = set()
    definitions = (
        ("mass_csi_physical_volumes", "mass_model_511", "mass_csi", 24),
        ("o8_bgo_physical_volumes", "s3d_o8", "o8_bgo", 3),
        ("o8_plastic_physical_volumes", "s3d_o8", "o8_plastic", 3),
    )
    for field, geometry, detector_type, expected_count in definitions:
        entries = value[field]
        if not isinstance(entries, list) or len(entries) != expected_count or len(set(entries)) != expected_count:
            raise ValidationError(f"active whitelist: {field} must contain exactly {expected_count} unique blocks")
        for volume in entries:
            if not isinstance(volume, str) or not volume or volume in seen_volumes:
                raise ValidationError(f"active whitelist: invalid/duplicate block {volume!r}")
            seen_volumes.add(volume)
            mapping[f"{detector_type}:{volume}"] = (geometry, detector_type, volume)
    if len(mapping) != 30:
        raise ValidationError("active whitelist: union is not exactly 30 blocks")
    passive_tokens = ("kapton", "bpe", "tungsten", "aluminum", "aluminium")
    exclusions = value["passive_exclusions"]
    if not isinstance(exclusions, list) or not exclusions or any(not isinstance(token, str) or not token for token in exclusions):
        raise ValidationError("active whitelist: malformed passive exclusions")
    for uid, (_, _, volume) in mapping.items():
        lowered = volume.lower()
        if any(token.lower() in lowered for token in exclusions) or any(token in lowered for token in passive_tokens):
            raise ValidationError(f"active whitelist: passive block included: {volume}")
    return value, mapping


def _foreign_keys(tables: Mapping[str, list[dict[str, Any]]]) -> None:
    roots = {row["simulation_event_id"]: row for row in tables["roots"]}
    events = {row["simulation_event_id"]: row for row in tables["events"]}
    observations = {row["simulation_event_id"]: row for row in tables["generated_observations"]}
    if set(roots) != set(events) or set(roots) != set(observations):
        raise ValidationError("roots/events/generated_observations: one-to-one event ID join failed")
    for name in ("generated_observations", "events", "pixels", "deposits", "veto_blocks", "activation", "truth_index"):
        for row in tables[name]:
            root = roots.get(row["simulation_event_id"])
            if root is None:
                raise ValidationError(f"{name}: orphan simulation_event_id={row['simulation_event_id']}")
            if row["stable_root_id"] != root["stable_root_id"]:
                raise ValidationError(f"{name}: stable_root_id join mismatch for event {row['simulation_event_id']}")
    for row in tables["activation"]:
        root = roots[row["simulation_event_id"]]
        if row["eventlist_id"] != root["eventlist_id"] or row["family"] != root["family"]:
            raise ValidationError(f"activation: broken root/eventlist/family join for serial {row['production_serial']}")
    for row in tables["generated_observations"]:
        root = roots[row["simulation_event_id"]]
        if row["eventlist_id"] != root["eventlist_id"]:
            raise ValidationError(f"generated_observations: EventList/root join mismatch at event {row['simulation_event_id']}")


def _binary64_digest(
    particle: int,
    excitation: float,
    source_time: float,
    position: Sequence[float],
    direction: Sequence[float],
    polarization: Sequence[float],
    energy: float,
) -> str:
    payload = b"m05-eventlist-binary64-v1\0" + struct.pack(
        ">i12d", particle, excitation, source_time, *position, *direction, *polarization, energy
    )
    return sha256_bytes(payload)


def _quantized_tuple_digest(
    particle: int,
    excitation: float,
    source_time: float,
    position: Sequence[float],
    direction: Sequence[float],
    polarization: Sequence[float],
    energy: float,
) -> str:
    norm = math.sqrt(math.fsum(value * value for value in direction))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValidationError("generated_observations: invalid direction norm")
    def llround(value: float) -> int:
        return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
    values = [
        particle, llround(excitation * 1.0e6), llround(source_time * 1.0e12),
        *(llround(value * 1.0e6) for value in position),
        *(llround(value / norm * 1.0e9) for value in direction),
        *(llround(value * 1.0e9) for value in polarization),
        llround(energy * 1.0e6),
    ]
    return sha256_bytes((json.dumps(values, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8"))


def _ia_init_digest(
    particle: int,
    ia_time: float,
    position: Sequence[float],
    direction: Sequence[float],
    polarization: Sequence[float],
    energy: float,
) -> str:
    norm = math.sqrt(math.fsum(value * value for value in direction))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValidationError("generated_observations: invalid IA direction norm")

    def llround(value: float) -> int:
        return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)

    values = [
        particle, llround(ia_time * 1.0e12),
        *(llround(value * 1.0e6) for value in position),
        *(llround(value / norm * 1.0e9) for value in direction),
        *(llround(value * 1.0e9) for value in polarization),
        llround(energy * 1.0e6),
    ]
    canonical = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    return sha256_bytes(b"m05-ia-init-state-v1\0" + canonical)


def _validate_generated_observations(tables: Mapping[str, list[dict[str, Any]]]) -> None:
    roots = {row["simulation_event_id"]: row for row in tables["roots"]}
    rows = sorted(tables["generated_observations"], key=lambda row: row["simulation_event_id"])
    if len(rows) != len(roots):
        raise ValidationError("generated_observations: count differs from roots")
    for row in rows:
        event_id = row["simulation_event_id"]
        root = roots[event_id]
        gp = row["observed_generated_particle"]
        ge = row["observed_generated_excitation_keV"]
        gt = row["observed_generated_source_time_s"]
        gpos = tuple(row[f"observed_generated_{axis}_cm"] for axis in "xyz")
        gdir = tuple(row[f"observed_generated_d{axis}"] for axis in "xyz")
        gpol = tuple(row[f"observed_generated_p{axis}"] for axis in "xyz")
        genergy = row["observed_generated_energy_keV"]
        native_event_time = row["native_event_time_s"]
        ia_time = float(row["serialized_ia_time_s"])
        observed_binary = _binary64_digest(gp, ge, gt, gpos, gdir, gpol, genergy)
        if observed_binary != row["observed_generated_binary64_sha256"]:
            raise ValidationError(f"generated_observations: actual generated binary64 digest mismatch at event {event_id}")
        norm = math.sqrt(math.fsum(value * value for value in gdir))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=2.0e-15):
            raise ValidationError(f"generated_observations: actual generated direction is not unit norm at event {event_id}")
        ip = row["serialized_ia_particle"]
        ipos = tuple(row[f"serialized_ia_{axis}_cm"] for axis in "xyz")
        idir = tuple(row[f"serialized_ia_d{axis}"] for axis in "xyz")
        ipol = tuple(row[f"serialized_ia_p{axis}"] for axis in "xyz")
        ienergy = row["serialized_ia_energy_keV"]
        if ip != gp:
            raise ValidationError(f"generated_observations: IA/generated particle mismatch at event {event_id}")
        # MSimEvent stores event time through MTime's integer-nanosecond
        # projection.  The generated observer retains the source binary64, so
        # equality is necessarily numerical rather than textual/bitwise.
        if not math.isclose(native_event_time, gt, rel_tol=1.0e-12, abs_tol=1.1e-9):
            raise ValidationError(f"generated_observations: native event time differs from generated source time at event {event_id}")
        position_energy_absolute = float(row["serialized_ia_position_energy_abs_tolerance"])
        direction_polarization_absolute = float(row["serialized_ia_direction_polarization_abs_tolerance"])
        relative = float(row["serialized_ia_rel_tolerance"])
        for actual, serialized, name, absolute in [
            *((actual, serialized, name, position_energy_absolute)
              for actual, serialized, name in zip(gpos, ipos, ("x", "y", "z"), strict=True)),
            *((actual, serialized, name, direction_polarization_absolute)
              for actual, serialized, name in zip(gdir, idir, ("dx", "dy", "dz"), strict=True)),
            *((actual, serialized, name, direction_polarization_absolute)
              for actual, serialized, name in zip(gpol, ipol, ("px", "py", "pz"), strict=True)),
            (genergy, ienergy, "energy", position_energy_absolute),
        ]:
            if not math.isclose(actual, serialized, rel_tol=relative, abs_tol=absolute):
                raise ValidationError(f"generated_observations: IA/generated {name} outside serialized tolerance at event {event_id}")
        # Native IA INIT stores its own record time (zero for the primary),
        # while the event/source time lives in the generated/native-event
        # observer.  These hashes therefore must not be equated.
        ia_quantized = _ia_init_digest(ip, ia_time, ipos, idir, ipol, ienergy)
        if ia_quantized != row["serialized_ia_quantized_sha256"] or ia_quantized != root["observed_ia_init_tuple_sha256"]:
            raise ValidationError(f"generated_observations: serialized IA quantized digest mismatch at event {event_id}")
        generated_quantized = _quantized_tuple_digest(gp, ge, gt, gpos, gdir, gpol, genergy)
        if generated_quantized != root["observed_generated_tuple_sha256"]:
            raise ValidationError(f"generated_observations: generated quantized digest mismatch at event {event_id}")
        # raw_eventlist_binary64_sha256 is joined against the 40-column tape by
        # materialize_standalone_sim._load_runtime_tables; it is intentionally
        # not required to equal the normalized post-GPS generated digest.


def _validate_roots_and_events(run: Mapping[str, Any], tables: Mapping[str, list[dict[str, Any]]]) -> None:
    roots = sorted(tables["roots"], key=lambda row: row["simulation_event_id"])
    events = {row["simulation_event_id"]: row for row in tables["events"]}
    expected = run["expected_event_count"]
    if len(roots) != expected or len(events) != expected:
        raise ValidationError("roots/events: row counts do not equal expected_event_count")
    if sum(root["control_flag"] for root in roots) < 1:
        raise ValidationError("roots: every job/shard requires at least one pre-registered control")
    if not any(
        root["control_flag"] == 1 and events[root["simulation_event_id"]]["raw_tes_positive"] == 0
        for root in roots
    ):
        raise ValidationError("roots/events: shard lacks a post-transport TES-zero pre-registered control")
    for index, root in enumerate(roots):
        event_id = index + 1
        if root["simulation_event_id"] != event_id or root["row_index0"] != index or root["eventlist_id"] != event_id:
            raise ValidationError(f"roots: IDs/order are not contiguous at row {index}")
        if root["family"] != run["family"]:
            raise ValidationError(f"roots: family differs from manifest at event {event_id}")
        if not root["benchmark_driver_id"]:
            raise ValidationError(f"roots: sampled benchmark driver is empty at event {event_id}")
        if any(root[name] != 1 for name in ("generated_flag", "started_flag", "native_event_populated", "completed_flag")):
            raise ValidationError(f"roots: incomplete lifecycle at event {event_id}")
        if root["aborted_flag"] != 0:
            raise ValidationError(f"roots: aborted event {event_id}")
        if root["expected_generated_tuple_sha256"] != root["observed_generated_tuple_sha256"]:
            raise ValidationError(f"roots: altered generated tuple hash at event {event_id}")
        quality = root["driver_inference_quality"]
        ambiguity = root["driver_inference_ambiguity_set"]
        inferred = root["driver_inference"]
        if quality in {"exact", "rounded_unique"} and (not inferred or ambiguity != [inferred]):
            raise ValidationError(f"roots: unique driver inference payload inconsistent at event {event_id}")
        if quality == "rounded_ambiguous" and (len(ambiguity) < 2 or inferred):
            raise ValidationError(f"roots: ambiguous driver inference payload inconsistent at event {event_id}")
        if quality == "unavailable" and (inferred or ambiguity):
            raise ValidationError(f"roots: unavailable driver inference must have empty values at event {event_id}")
        event = events[event_id]
        if event["geometry"] != run["geometry"] or event["control_flag"] != root["control_flag"]:
            raise ValidationError(f"events: manifest/root fields disagree at event {event_id}")
        raw_positive = int(event["tes_raw_keV"] > 0.0)
        active_positive = int(event["active_veto_total_keV"] > 0.0)
        if event["raw_tes_positive"] != raw_positive:
            raise ValidationError(f"events: raw_tes_positive mismatch at event {event_id}")
        expected_reason = (
            "tes+active_veto" if raw_positive and active_positive else
            "tes" if raw_positive else "active_veto" if active_positive else "none"
        )
        if event["candidate_reason"] != expected_reason:
            raise ValidationError(f"events: candidate_reason mismatch at event {event_id}")
        truth_required = int(bool(raw_positive or event["control_flag"]))
        if event["truth_required"] != truth_required:
            raise ValidationError(f"events: truth_required must be TES-positive OR control at event {event_id}")


def _validate_tape_root_join(
    manifest_path: Path, manifest: Mapping[str, Any], tables: Mapping[str, list[dict[str, Any]]]
) -> Path:
    """Join every runtime root to the exact transaction-bound 40-column tape sidecar."""

    provenance = manifest["provenance"]
    tape_path = _bound_path(
        manifest_path, provenance["tape_root_sidecar_path"],
        "manifest.provenance.tape_root_sidecar_path",
    )
    if sha256_file(tape_path) != provenance["tape_root_sidecar_sha256"]:
        raise ValidationError("manifest provenance: altered tape-root sidecar bytes")
    try:
        from tape_contract import (
            SIDECAR_COLUMNS, _primary_from_row, _root_payload,
            eventlist_binary64_hash, generated_binary64_hash, generated_tuple_hash,
            runtime_source_time_projection,
        )
        from preflight_common import canonical_json_bytes
    except ImportError as exc:
        raise ValidationError(f"tape contract implementation unavailable: {exc}") from exc
    lines = tape_path.read_text(encoding="utf-8").splitlines()
    if not lines or tuple(lines[0].split("\t")) != SIDECAR_COLUMNS:
        raise ValidationError("tape-root sidecar: exact 40-column header mismatch")
    tape_rows: list[dict[str, str]] = []
    for line_number, line in enumerate(lines[1:], 2):
        fields = line.split("\t")
        if len(fields) != len(SIDECAR_COLUMNS):
            raise ValidationError(f"tape-root sidecar:{line_number}: wrong field count")
        tape_rows.append(dict(zip(SIDECAR_COLUMNS, fields, strict=True)))
    roots = sorted(tables["roots"], key=lambda row: row["simulation_event_id"])
    observations = sorted(tables["generated_observations"], key=lambda row: row["simulation_event_id"])
    if len(tape_rows) != len(roots) or len(observations) != len(roots):
        raise ValidationError("tape-root sidecar: row count differs from runtime roots/observations")
    previous_runtime_internal_time = 0.0
    for event_id, (tape, root, observation) in enumerate(zip(tape_rows, roots, observations, strict=True), 1):
        try:
            primary = _primary_from_row(tape)
            raw_binary = eventlist_binary64_hash(primary)
            runtime_source_time_s, previous_runtime_internal_time = runtime_source_time_projection(
                primary.source_time_s, previous_runtime_internal_time
            )
            generated_binary = generated_binary64_hash(
                primary, runtime_source_time_s=runtime_source_time_s
            )
            generated_tuple = generated_tuple_hash(primary)
            stable_root = sha256_bytes(canonical_json_bytes(_root_payload(
                row=tape,
                raw_line_sha256=tape["raw_eventlist_line_sha256"],
                eventlist_binary64_sha256=raw_binary,
                generated_binary64_sha256=generated_binary,
                tuple_sha256=generated_tuple,
            )))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"tape-root sidecar: invalid row {event_id}: {exc}") from exc
        exact = (
            (int(tape["row_index0"]), root["row_index0"], "row_index0"),
            (int(tape["eventlist_id"]), root["eventlist_id"], "eventlist_id"),
            (tape["stable_root_id"], root["stable_root_id"], "stable_root_id"),
            (tape["driver"], root["benchmark_driver_id"], "benchmark_driver_id"),
            (tape["family"], root["family"], "family"),
            (tape["raw_eventlist_line_sha256"], root["raw_tape_line_sha256"], "raw tape hash"),
            (tape["expected_generated_tuple_sha256"], root["expected_generated_tuple_sha256"], "tuple hash"),
            (int(tape["control_flag"]), root["control_flag"], "control_flag"),
            (tape["expected_eventlist_binary64_sha256"], observation["raw_eventlist_binary64_sha256"], "raw binary64 hash"),
            (tape["expected_generated_binary64_sha256"], observation["observed_generated_binary64_sha256"], "generated binary64 digest mismatch"),
            (raw_binary, tape["expected_eventlist_binary64_sha256"], "recomputed raw binary64 hash"),
            (generated_binary, tape["expected_generated_binary64_sha256"], "recomputed generated binary64 hash"),
            (generated_tuple, tape["expected_generated_tuple_sha256"], "recomputed generated tuple hash"),
            (stable_root, tape["stable_root_id"], "recomputed stable_root_id"),
            (manifest["provenance"]["source_card_sha256"], tape["source_card_sha256"], "source card provenance"),
            (manifest["provenance"]["source_contract_sha256"], tape["source_contract_sha256"], "source contract provenance"),
        )
        for expected, actual, label in exact:
            if actual != expected:
                raise ValidationError(f"tape-root sidecar: event {event_id} {label} mismatch")
    return tape_path


def _validate_deposit_roles(
    tables: Mapping[str, list[dict[str, Any]]],
    whitelist: Mapping[str, tuple[str, str, str]],
) -> dict[tuple[int, str], list[dict[str, Any]]]:
    per_role: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    per_event_sequences: dict[int, list[int]] = defaultdict(list)
    for row in tables["deposits"]:
        event_id = row["simulation_event_id"]
        per_role[(event_id, row["role"])].append(row)
        per_event_sequences[event_id].append(row["sequence"])
        if row["post_time_s"] < row["pre_time_s"]:
            raise ValidationError(f"deposits: POST time precedes PRE time at event {event_id}, sequence {row['sequence']}")
        physical = row["physical_volume"]
        if row["role"] in {"mass_csi", "o8_bgo", "o8_plastic"}:
            expected = whitelist.get(f"{row['role']}:{physical}")
            if expected is None or expected[1] != row["role"] or expected[2] != physical:
                raise ValidationError(f"deposits: active role/whitelist mismatch for {physical!r}")
        elif row["role"] == "tes":
            if re.fullmatch(r"TP_L[0-5]_[0-9]+", physical) is None:
                raise ValidationError(f"deposits: malformed TES physical volume {physical!r}")
        elif row["role"] == "kapton" and "kapton" not in physical.lower():
            raise ValidationError(f"deposits: kapton role lacks Kapton physical name at event {event_id}")
    for event_id, sequences in per_event_sequences.items():
        if sorted(sequences) != list(range(1, len(sequences) + 1)):
            raise ValidationError(f"deposits: sequence is not contiguous for event {event_id}")
    return per_role


def _weighted_aggregate(rows: Sequence[Mapping[str, Any]]) -> tuple[float, float | None, float | None, float | None, int]:
    if not rows:
        return 0.0, None, None, None, 0
    energy = _sum(row["edep_keV"] for row in rows)
    times = [row["post_time_s"] for row in rows]
    weighted = _sum(row["edep_keV"] * row["post_time_s"] for row in rows) / energy
    return energy, min(times), max(times), weighted, len(rows)


def _validate_pixels(tables: Mapping[str, list[dict[str, Any]]]) -> None:
    pixels_by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    deposits_by_event_uid: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in tables["pixels"]:
        pixels_by_event[row["simulation_event_id"]].append(row)
        if row["tes_uid"] != row["touchable_copy_path"]:
            raise ValidationError(f"pixels: tes_uid must equal exact touchable_copy_path at event {row['simulation_event_id']}")
        if row["post_time_min_s"] > row["post_time_max_s"]:
            raise ValidationError(f"pixels: POST time interval is reversed at event {row['simulation_event_id']}")
        if not row["post_time_min_s"] <= row["post_time_energy_weighted_s"] <= row["post_time_max_s"]:
            raise ValidationError(f"pixels: POST weighted time outside interval at event {row['simulation_event_id']}")
    for row in tables["deposits"]:
        if row["role"] == "tes":
            deposits_by_event_uid[(row["simulation_event_id"], row["touchable_copy_path"])].append(row)
    pixel_keys = {(row["simulation_event_id"], row["tes_uid"]) for row in tables["pixels"]}
    have_step_diagnostics = bool(tables["deposits"])
    if have_step_diagnostics and pixel_keys != set(deposits_by_event_uid):
        raise ValidationError("pixels/deposits: exact TES UID coverage mismatch")
    for pixel in tables["pixels"]:
        key = (pixel["simulation_event_id"], pixel["tes_uid"])
        if pixel["first_sequence"] > pixel["last_sequence"]:
            raise ValidationError(f"pixels {key}: sequence range is reversed")
        if pixel["deposit_count"] > pixel["last_sequence"] - pixel["first_sequence"] + 1:
            raise ValidationError(f"pixels {key}: deposit_count exceeds sequence span")
        if have_step_diagnostics:
            deposits = deposits_by_event_uid[key]
            energy, post_min, post_max, weighted, count = _weighted_aggregate(deposits)
            for actual, expected, label in (
                (pixel["sum_energy_keV"], energy, "energy"),
                (pixel["post_time_min_s"], post_min, "POST min time"),
                (pixel["post_time_max_s"], post_max, "POST max time"),
                (pixel["post_time_energy_weighted_s"], weighted, "POST weighted time"),
            ):
                assert expected is not None
                _expect_near(actual, expected, f"pixels {key}: {label}")
            if pixel["deposit_count"] != count:
                raise ValidationError(f"pixels {key}: deposit_count mismatch")
            sequences = [row["sequence"] for row in deposits]
            if pixel["first_sequence"] != min(sequences) or pixel["last_sequence"] != max(sequences):
                raise ValidationError(f"pixels {key}: sequence range mismatch")
        expected_layer = int(re.search(r"(?:^|/)TP_L([0-5])_[0-9]+:", pixel["tes_uid"]).group(1))
        if pixel["layer"] != expected_layer:
            raise ValidationError(f"pixels {key}: layer differs from TES UID")
        if have_step_diagnostics:
            energy_total = energy
            for axis, column in enumerate(("centroid_x_cm", "centroid_y_cm", "centroid_z_cm")):
                expected_centroid = _sum(
                    row["edep_keV"] * row[("pre_x_cm", "pre_y_cm", "pre_z_cm")[axis]] for row in deposits
                ) / energy_total
                _expect_near(pixel[column], expected_centroid, f"pixels {key}: {column}")
    events = {row["simulation_event_id"]: row for row in tables["events"]}
    for event_id, event in events.items():
        rows = pixels_by_event.get(event_id, [])
        _expect_near(event["tes_raw_keV"], _sum(row["sum_energy_keV"] for row in rows), f"events {event_id}: TES total")
        if event["tes_multiplicity"] != len(rows):
            raise ValidationError(f"events {event_id}: TES multiplicity mismatch")
        if have_step_diagnostics:
            kapton = _sum(
                row["edep_keV"] for row in tables["deposits"]
                if row["simulation_event_id"] == event_id and row["role"] == "kapton"
            )
            _expect_near(event["kapton_diagnostic_keV"], kapton, f"events {event_id}: Kapton diagnostic total")


def _expected_blocks(
    run: Mapping[str, Any], whitelist: Mapping[str, tuple[str, str, str]]
) -> dict[str, tuple[str, str, str]]:
    if run["active_block_coverage"] != "geometry_specific":
        raise ValidationError("run: only geometry-specific active-block coverage is permitted")
    return {uid: value for uid, value in whitelist.items() if value[0] == run["geometry"]}


def _validate_blocks_and_veto(
    manifest: Mapping[str, Any],
    tables: Mapping[str, list[dict[str, Any]]],
    whitelist: Mapping[str, tuple[str, str, str]],
) -> None:
    run = manifest["run"]
    expected_blocks = _expected_blocks(run, whitelist)
    expected_uids = set(expected_blocks)
    rows_by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    deposits_by_event_volume: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in tables["deposits"]:
        if row["role"] in {"mass_csi", "o8_bgo", "o8_plastic"}:
            deposits_by_event_volume[(row["simulation_event_id"], row["physical_volume"])].append(row)
            uid = f"{row['role']}:{row['physical_volume']}"
            if uid not in expected_blocks:
                raise ValidationError(
                    f"deposits: active block {uid!r} is outside run geometry/coverage"
                )
    for row in tables["veto_blocks"]:
        event_id = row["simulation_event_id"]
        rows_by_event[event_id].append(row)
        uid = row["detector_uid"]
        expected = expected_blocks.get(uid)
        if expected is None:
            raise ValidationError(f"veto_blocks: unexpected block {uid!r} for coverage/geometry")
        source_geometry, detector_type, physical_volume = expected
        if row["detector_type"] != detector_type or row["physical_volume"] != physical_volume:
            raise ValidationError(f"veto_blocks: wrong detector_type/physical_volume for {uid!r}")
        if row["geometry"] != run["geometry"]:
            raise ValidationError(f"veto_blocks: row geometry differs from run at event {event_id}")
        if row["veto_whitelist_sha256"] != manifest["veto_whitelist_sha256"]:
            raise ValidationError(f"veto_blocks: altered whitelist hash at event {event_id}")
        deposits = deposits_by_event_volume.get((event_id, physical_volume), [])
        have_step_diagnostics = bool(tables["deposits"])
        energy, post_min, post_max, weighted, count = _weighted_aggregate(deposits)
        if have_step_diagnostics:
            _expect_near(row["sum_energy_keV"], energy, f"veto_blocks {(event_id, uid)}: energy")
            if row["deposit_count"] != count:
                raise ValidationError(f"veto_blocks {(event_id, uid)}: deposit_count mismatch")
        if row["deposit_count"] == 0:
            if row["sum_energy_keV"] != 0.0:
                raise ValidationError(f"veto_blocks {(event_id, uid)}: zero-deposit block has energy")
            if any(row[name] is not None for name in ("post_time_min_s", "post_time_max_s", "post_time_energy_weighted_s")):
                raise ValidationError(f"veto_blocks {(event_id, uid)}: zero block times must be empty")
        else:
            if source_geometry != run["geometry"]:
                raise ValidationError(f"veto_blocks {(event_id, uid)}: cross-geometry block is forbidden")
            if row["sum_energy_keV"] <= 0.0:
                raise ValidationError(f"veto_blocks {(event_id, uid)}: positive deposit count lacks energy")
            for actual, expected_value, label in (
                (row["post_time_min_s"], post_min if have_step_diagnostics else row["post_time_min_s"], "POST min time"),
                (row["post_time_max_s"], post_max if have_step_diagnostics else row["post_time_max_s"], "POST max time"),
                (row["post_time_energy_weighted_s"], weighted if have_step_diagnostics else row["post_time_energy_weighted_s"], "POST weighted time"),
            ):
                if actual is None or expected_value is None:
                    raise ValidationError(f"veto_blocks {(event_id, uid)}: missing {label}")
                _expect_near(actual, expected_value, f"veto_blocks {(event_id, uid)}: {label}")
            if not row["post_time_min_s"] <= row["post_time_energy_weighted_s"] <= row["post_time_max_s"]:
                raise ValidationError(f"veto_blocks {(event_id, uid)}: POST time interval invalid")

    events = {row["simulation_event_id"]: row for row in tables["events"]}
    for event_id, event in events.items():
        block_rows = rows_by_event.get(event_id, [])
        observed = {row["detector_uid"] for row in block_rows}
        if len(block_rows) != len(expected_uids) or observed != expected_uids:
            raise ValidationError(
                f"veto_blocks: incomplete event {event_id}; expected {len(expected_uids)} exact blocks, got {len(block_rows)}"
            )
        type_sums = {
            detector_type: _sum(row["sum_energy_keV"] for row in block_rows if row["detector_type"] == detector_type)
            for detector_type in ("mass_csi", "o8_bgo", "o8_plastic")
        }
        for detector_type, column in (
            ("mass_csi", "mass_csi_keV"),
            ("o8_bgo", "o8_bgo_keV"),
            ("o8_plastic", "o8_plastic_keV"),
        ):
            _expect_near(event[column], type_sums[detector_type], f"events {event_id}: {detector_type} block sum")
        expected_active_shield = event["mass_csi_keV"] if run["geometry"] == "mass_model_511" else event["o8_bgo_keV"]
        _expect_near(event["active_shield_keV"], expected_active_shield, f"events {event_id}: active_shield_keV")
        expected_total = event["mass_csi_keV"] + event["o8_bgo_keV"] + event["o8_plastic_keV"]
        _expect_near(event["active_veto_total_keV"], expected_total, f"events {event_id}: active_veto_total_keV")
        for threshold in (50, 70, 80):
            expected_pass = int(
                event["mass_csi_keV"] < threshold if run["geometry"] == "mass_model_511"
                else event["o8_bgo_keV"] < threshold and event["o8_plastic_keV"] < 50.0
            )
            if event[f"pass_veto{threshold}"] != expected_pass:
                raise ValidationError(f"events {event_id}: pass_veto{threshold} mismatch")


def _validate_activation(run: Mapping[str, Any], tables: Mapping[str, list[dict[str, Any]]]) -> None:
    rows = sorted(tables["activation"], key=lambda row: row["production_serial"])
    if [row["production_serial"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ValidationError("activation: production_serial is not contiguous")
    for row in rows:
        if row["za"] != 1000 * row["z"] + row["a"]:
            raise ValidationError(f"activation: ZA/Z/A mismatch at production_serial {row['production_serial']}")
        expected_bits = struct.pack(">d", row["excitation_keV"]).hex()
        if row["excitation_f64_bits"] != expected_bits:
            raise ValidationError(f"activation: excitation_f64_bits mismatch at serial {row['production_serial']}")
        chain = row["ancestry_chain"]
        if chain[-1][0] != row["track_id"] or chain[0][0] != row["primary_track_id"]:
            raise ValidationError(f"activation: ancestry endpoints mismatch at serial {row['production_serial']}")
        if row["parent_track_id"] == 0:
            if len(chain) != 1:
                raise ValidationError(f"activation: primary track ancestry mismatch at serial {row['production_serial']}")
        elif len(chain) < 2 or chain[-1][1] != row["parent_track_id"]:
            raise ValidationError(f"activation: parent track absent from chain at serial {row['production_serial']}")
        if row["family"] != run["family"]:
            raise ValidationError(f"activation: family differs from run at serial {row['production_serial']}")


def _parse_native_dat(blob: bytes) -> tuple[float, Counter[tuple[str, int, str]]]:
    """Parse the exact aggregate evidence emitted by MCIsotopeStore::Save.

    Native DAT is deliberately treated as aggregate evidence only.  It cannot
    establish a one-to-one identity for an individual AddIsotope call.
    """

    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("native_dat: is not UTF-8 text") from exc
    if "\r" in text:
        raise ValidationError("native_dat: CR newlines are forbidden")
    tt: float | None = None
    current_volume: str | None = None
    seen_volumes: set[str] = set()
    totals: Counter[tuple[str, int, str]] = Counter()
    en_count = 0
    ended = False
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ended:
            raise ValidationError(f"native_dat:{line_number}: record after EN")
        fields = line.split()
        record = fields[0]
        if record == "TT":
            if tt is not None or len(fields) != 2:
                raise ValidationError("native_dat: exactly one well-formed TT is required")
            tt = _parse_float(fields[1], f"native_dat:{line_number}.TT")
            if tt <= 0.0:
                raise ValidationError("native_dat: TT must be positive, including zero-RP BUILDUP")
        elif record == "VN":
            if len(fields) != 2 or not fields[1] or fields[1] in seen_volumes:
                raise ValidationError(f"native_dat:{line_number}: malformed or duplicate VN")
            current_volume = fields[1]
            seen_volumes.add(current_volume)
        elif record == "RP":
            if len(fields) != 4 or current_volume is None:
                raise ValidationError(f"native_dat:{line_number}: malformed or orphan RP")
            za = _parse_int(fields[1], f"native_dat:{line_number}.za")
            excitation = _parse_float(fields[2], f"native_dat:{line_number}.excitation_keV")
            count = _parse_float(fields[3], f"native_dat:{line_number}.count")
            if excitation < 0.0 or count < 0.0 or not count.is_integer():
                raise ValidationError(f"native_dat:{line_number}: invalid excitation/count")
            key = (current_volume, za, f"{excitation:.2f}")
            if key in totals:
                raise ValidationError(f"native_dat:{line_number}: duplicate aggregate RP key")
            totals[key] = int(count)
        elif record == "EN":
            if len(fields) != 1:
                raise ValidationError(f"native_dat:{line_number}: malformed EN")
            en_count += 1
            ended = True
        else:
            raise ValidationError(f"native_dat:{line_number}: unknown record {record!r}")
    if tt is None or en_count != 1:
        raise ValidationError("native_dat: TT/EN closure failed")
    return tt, totals


def _validate_native_dat(
    blob: bytes,
    tables: Mapping[str, list[dict[str, Any]]],
) -> tuple[float, int]:
    tt, native_totals = _parse_native_dat(blob)
    sidecar_totals: Counter[tuple[str, int, str]] = Counter()
    for row in tables["activation"]:
        sidecar_totals[(row["native_dat_volume"], row["za"], f"{row['excitation_keV']:.2f}")] += 1
    if native_totals != sidecar_totals:
        raise ValidationError(
            f"native_dat/activation: aggregate RP mismatch; native={dict(native_totals)}, "
            f"sidecar={dict(sidecar_totals)}"
        )
    footer = tables["footer"][0] if len(tables["footer"]) == 1 else None
    if footer is None:
        raise ValidationError("native_dat/footer: exactly one footer row is required")
    # MCIsotopeStore writes TT with the default six significant digits.  This
    # relative tolerance is therefore a serialization bound, not a physics
    # tolerance and not row-level RP identity.
    if not math.isclose(footer["TT_s"], tt, rel_tol=5.0e-6, abs_tol=5.0e-12):
        raise ValidationError("native_dat/footer: TT differs beyond native six-significant-digit serialization")
    if footer["rp_row_count"] != sum(native_totals.values()):
        raise ValidationError("native_dat/footer: aggregate RP count differs from footer")
    return tt, len(native_totals)


def _validate_truth(
    blob: bytes,
    tables: Mapping[str, list[dict[str, Any]]],
) -> None:
    rows = sorted(tables["truth_index"], key=lambda row: row["offset"])
    expected_events = {row["simulation_event_id"] for row in tables["events"] if row["truth_required"] == 1}
    actual_events = {row["simulation_event_id"] for row in rows}
    if actual_events != expected_events:
        raise ValidationError("truth_index/events: exact raw-TES/control selection coverage mismatch")
    cursor = 0
    events = {row["simulation_event_id"]: row for row in tables["events"]}
    for row in rows:
        if row["offset"] != cursor:
            raise ValidationError("truth_index: fragments must be contiguous, ordered, and non-overlapping")
        end = row["offset"] + row["length"]
        if end > len(blob):
            raise ValidationError(f"truth_index: fragment outside blob for event {row['simulation_event_id']}")
        fragment = blob[row["offset"]:end]
        if sha256_bytes(fragment) != row["sha256"]:
            raise ValidationError(f"truth_index: altered fragment hash for event {row['simulation_event_id']}")
        event = events[row["simulation_event_id"]]
        expected_reason = "candidate+control" if event["raw_tes_positive"] and event["control_flag"] else (
            "candidate" if event["raw_tes_positive"] else "control"
        )
        if row["reason"] != expected_reason:
            raise ValidationError(f"truth_index: reason mismatch for event {row['simulation_event_id']}")
        cursor = end
    if cursor != len(blob):
        raise ValidationError("truth_index: unindexed trailing truth bytes")


def _validate_footer(manifest: Mapping[str, Any], tables: Mapping[str, list[dict[str, Any]]]) -> None:
    if len(tables["footer"]) != 1:
        raise ValidationError("footer: exactly one row required")
    footer = tables["footer"][0]
    run = manifest["run"]
    for field in ("arm", "geometry", "mode", "family", "job_id", "shard_index", "seed", "active_block_coverage"):
        if footer[field] != run[field]:
            raise ValidationError(f"footer.{field}: differs from manifest.run")
    if footer["veto_whitelist_sha256"] != manifest["veto_whitelist_sha256"]:
        raise ValidationError("footer: altered whitelist hash")
    if footer["record_schema_sha256"] != manifest["record_schema_sha256"]:
        raise ValidationError("footer: altered record schema hash")
    expected = run["expected_event_count"]
    equal_event_counts = (
        "tape_count", "generated_count", "started_count", "completed_count",
        "native_populated_count", "root_count", "ia_init_count",
        "native_observed_simulation_event_id_count", "native_observed_event_id_count",
    )
    for name in equal_event_counts:
        if footer[name] != expected:
            raise ValidationError(f"footer.{name}: must equal expected event count {expected}")
    if footer["aborted_count"] != 0 or footer["finalized"] != 1:
        raise ValidationError("footer: aborted_count must be zero and finalized must be one")
    if footer["rp_row_count"] != len(tables["activation"]):
        raise ValidationError("footer: RP row count differs from activation table")
    if not footer["TT_s"] > 0.0:
        raise ValidationError("footer: TT must be positive even for zero RP")
    roots = tables["roots"]
    lifecycle_sums = {
        "generated_count": sum(row["generated_flag"] for row in roots),
        "started_count": sum(row["started_flag"] for row in roots),
        "native_populated_count": sum(row["native_event_populated"] for row in roots),
        "completed_count": sum(row["completed_flag"] for row in roots),
        "aborted_count": sum(row["aborted_flag"] for row in roots),
        "root_count": len(roots),
    }
    for name, value in lifecycle_sums.items():
        if footer[name] != value:
            raise ValidationError(f"footer.{name}: differs from root lifecycle rows")


def validate_bundle(
    manifest_path: Path | str,
    *,
    schema_path: Path | str = SCHEMA_PATH,
    whitelist_path: Path | str = WHITELIST_PATH,
    geometry_classification_path: Path | str = PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH,
) -> dict[str, Any]:
    """Validate a final compact bundle, returning only a PASS evidence object.

    Raises ValidationError on the first violation.  Callers must never publish
    or consume authority outputs after an exception.
    """

    manifest_path = Path(manifest_path)
    schema_path = Path(schema_path)
    whitelist_path = Path(whitelist_path)
    geometry_classification_path = Path(geometry_classification_path)
    schema = strict_json(schema_path)
    manifest = strict_json(manifest_path)
    _manifest_shape(manifest, schema)
    schema_digest = sha256_file(schema_path)
    whitelist_value, whitelist = _load_whitelist(whitelist_path)
    del whitelist_value
    whitelist_digest = sha256_file(whitelist_path)
    if manifest["record_schema_sha256"] != schema_digest:
        raise ValidationError("manifest: record schema digest does not match bytes")
    if manifest["veto_whitelist_sha256"] != whitelist_digest:
        raise ValidationError("manifest: active whitelist digest does not match bytes")
    try:
        from geometry_classification import build_geometry_classification, classification_index
        from preflight_common import canonical_json_bytes
    except ImportError as exc:
        raise ValidationError(f"geometry classification implementation unavailable: {exc}") from exc
    classification = strict_json(geometry_classification_path)
    classification_digest = sha256_file(geometry_classification_path)
    if manifest["geometry_classification_sha256"] != classification_digest:
        raise ValidationError("manifest: geometry classification digest does not match bytes")
    try:
        rebuilt_classification = build_geometry_classification()
    except (OSError, ValueError) as exc:
        raise ValidationError(f"canonical geometry classification rebuild failed: {exc}") from exc
    if canonical_json_bytes(rebuilt_classification) != geometry_classification_path.read_bytes():
        raise ValidationError("geometry classification manifest differs from canonical bundle rescan")
    try:
        run_classification = classification_index(classification, manifest["run"]["geometry"])
    except ValueError as exc:
        raise ValidationError(f"geometry classification index failed: {exc}") from exc
    geometry_entries = [
        entry for entry in classification["geometries"]
        if entry["geometry"] == manifest["run"]["geometry"]
    ]
    if len(geometry_entries) != 1 or (
        manifest["provenance"]["geometry_bundle_sha256"] != geometry_entries[0]["geometry_bundle_sha256"]
    ):
        raise ValidationError("manifest provenance geometry bundle differs from canonical classification")
    expected_active_from_geometry = {
        f"{row['active_detector_type']}:{physical}": (
            manifest["run"]["geometry"], row["active_detector_type"], physical
        )
        for physical, row in run_classification.items()
        if row["active_detector_type"] in {"mass_csi", "o8_bgo", "o8_plastic"}
    }
    expected_active_from_whitelist = {
        uid: value for uid, value in whitelist.items() if value[0] == manifest["run"]["geometry"]
    }
    if expected_active_from_geometry != expected_active_from_whitelist:
        raise ValidationError("active whitelist does not close against canonical geometry classification")

    contracts = schema["x-tsv-tables"]
    tables: dict[str, list[dict[str, Any]]] = {}
    paths: dict[str, Path] = {}
    for name, binding in manifest["tables"].items():
        path = _bound_path(manifest_path, binding["path"], f"manifest.tables.{name}.path")
        if not path.name.endswith(contracts[name]["suffix"]):
            raise ValidationError(f"manifest.tables.{name}.path: wrong suffix")
        if sha256_file(path) != binding["sha256"]:
            raise ValidationError(f"manifest.tables.{name}: altered file hash")
        paths[name] = path
        tables[name] = _read_table(path, name, contracts[name], binding["row_count"])

    tape_root_path = _validate_tape_root_join(manifest_path, manifest, tables)

    blob_binding = manifest["blobs"]["truth_stream"]
    truth_path = _bound_path(manifest_path, blob_binding["path"], "manifest.blobs.truth_stream.path")
    if not truth_path.name.endswith("truth.sim"):
        raise ValidationError("manifest.blobs.truth_stream.path: wrong suffix")
    truth_blob = truth_path.read_bytes()
    if len(truth_blob) != blob_binding["size_bytes"]:
        raise ValidationError("truth_stream: declared size differs from bytes")
    if sha256_bytes(truth_blob) != blob_binding["sha256"]:
        raise ValidationError("truth_stream: altered file hash")
    native_binding = manifest["blobs"]["native_dat"]
    native_dat_path = _bound_path(manifest_path, native_binding["path"], "manifest.blobs.native_dat.path")
    if not native_dat_path.name.endswith(".dat"):
        raise ValidationError("manifest.blobs.native_dat.path: wrong suffix")
    native_dat = native_dat_path.read_bytes()
    if len(native_dat) != native_binding["size_bytes"]:
        raise ValidationError("native_dat: declared size differs from bytes")
    if sha256_bytes(native_dat) != native_binding["sha256"]:
        raise ValidationError("native_dat: altered file hash")

    _foreign_keys(tables)
    _validate_roots_and_events(manifest["run"], tables)
    _validate_generated_observations(tables)
    _validate_deposit_roles(tables, whitelist)
    _validate_pixels(tables)
    _validate_blocks_and_veto(manifest, tables, whitelist)
    _validate_activation(manifest["run"], tables)
    native_tt, native_rp_key_count = _validate_native_dat(native_dat, tables)
    _validate_truth(truth_blob, tables)
    _validate_footer(manifest, tables)
    # Do not let the general record validator become a weaker substitute for
    # the dedicated RP/native-DAT authority.  The production post-run gate
    # invokes the independent reconciler over the exact already hash-bound
    # paths and embeds its result in the returned evidence object.  A caller
    # publishing a receipt must bind this whole validation result; no separate
    # optional RP pass exists.
    try:
        from rp_validation import reconcile as reconcile_rp

        rp_reconciliation = reconcile_rp(
            paths["activation"], native_dat_path, paths["footer"], paths["roots"], tape_root_path,
            geometry=manifest["run"]["geometry"],
            geometry_classification=classification,
            verify_geometry_authority=True,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ValidationError(f"dedicated RP/native-DAT reconciliation failed: {exc}") from exc
    if rp_reconciliation.get("status") != "PASS":
        raise ValidationError("dedicated RP/native-DAT reconciler did not return PASS")

    return {
        "schema_version": "m05cc-v2-record-validation",
        "status": "PASS__M05CC_V2_PHYSICAL_RECORD_BUNDLE",
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "record_schema_path": str(schema_path),
        "record_schema_sha256": schema_digest,
        "veto_whitelist_path": str(whitelist_path),
        "veto_whitelist_sha256": whitelist_digest,
        "geometry_classification_path": str(geometry_classification_path),
        "geometry_classification_sha256": classification_digest,
        "tape_root_sidecar_path": str(tape_root_path),
        "tape_root_sidecar_sha256": manifest["provenance"]["tape_root_sidecar_sha256"],
        "tape_runtime_root_driver_join": "PASS__EXACT_ALL_ROWS",
        "canonical_geometry_active_block_count": len(expected_active_from_geometry),
        "geometry": manifest["run"]["geometry"],
        "active_block_coverage": manifest["run"]["active_block_coverage"],
        "event_count": len(tables["events"]),
        "table_row_counts": {name: len(rows) for name, rows in sorted(tables.items())},
        "truth_size_bytes": len(truth_blob),
        "native_dat_size_bytes": len(native_dat),
        "native_dat_TT_s": native_tt,
        "native_dat_rp_aggregate_key_count": native_rp_key_count,
        "native_dat_evidence_grain": "AGGREGATE_ONLY__NOT_ROW_IDENTITY",
        "rp_reconciliation": rp_reconciliation,
        "rp_reconciliation_authority": "code/rp_validation.py::reconcile",
        "post_time_semantics": "POST_GLOBAL_V1",
        "veto_thresholds_keV": [50, 70, 80],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="m05cc-v2 bundle manifest JSON")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--whitelist", type=Path, default=WHITELIST_PATH)
    parser.add_argument("--geometry-classification", type=Path, default=PREFLIGHT_GEOMETRY_CLASSIFICATION_PATH)
    args = parser.parse_args(argv)
    try:
        result = validate_bundle(
            args.manifest,
            schema_path=args.schema,
            whitelist_path=args.whitelist,
            geometry_classification_path=args.geometry_classification,
        )
    except ValidationError as exc:
        print(json.dumps({"status": "FAIL__M05CC_V2_RECORD_VALIDATION", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
