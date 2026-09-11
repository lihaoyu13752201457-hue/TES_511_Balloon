#!/usr/bin/env python3
"""Strict post-run validator for the shadow N1 transaction.

N1 deliberately has no compact event/pixel/veto/truth/RP representation.  It
retains only the exact primary/root observer, lifecycle footer, copied tape
sidecar, and the native aggregate isotope DAT.  Consequently this validator is
separate from the C-arm ``record_validation`` authority and never accepts a C
``record_bundle.json`` as input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence

from preflight_common import (
    ROOT,
    canonical_json_bytes,
    repo_path,
    reject_lexical_symlinks,
    sha256,
    sha256_bytes,
    strict_json_bytes,
)
from record_validation import (
    ValidationError as RecordValidationError,
    _ia_init_digest,
    _parse_cell,
    _parse_native_dat,
    _validate_generated_observations,
    _validate_keys,
)
from tape_contract import (
    SIDECAR_COLUMNS,
    SOURCE_CONTRACT_SHA256,
    _primary_from_row,
    _root_payload,
    eventlist_binary64_hash,
    generated_binary64_hash,
    generated_tuple_hash,
    runtime_source_time_projection,
    validate_sidecar,
)


PACKAGE = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PACKAGE / "schema/m05cc_n1_v1.commit_schema.json"
WHITELIST_PATH = PACKAGE / "schema/active_volume_whitelist_v1.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
NATIVE_DAT_RE = re.compile(r"^native(?:\.p[1-9][0-9]*)?\.inc(?:0|[1-9][0-9]*)\.dat$")
FAMILIES = {"gamma", "n", "eminus", "eplus", "alpha", "muplus", "muminus"}
GEOMETRIES = {"mass_model_511", "s3d_o8"}
MODES = {"instant", "buildup"}
TOP_LEVEL_KEYS = {
    "arm", "corrected_source_card_sha256", "footer", "generated_observations",
    "geometry_bundle_sha256", "geometry_classification_sha256", "n1_commit_schema_sha256",
    "native_added_isotope_count", "native_dat", "roots", "run", "runtime_source_card_sha256",
    "schema_version", "source_contract_sha256", "status", "tape_root_sidecar",
    "veto_whitelist_sha256",
}
RUN_KEYS = {"arm", "expected_event_count", "family", "geometry", "job_id", "mode", "seed", "shard_index"}
TABLE_KEYS = {"path", "row_count", "sha256", "size_bytes"}
BLOB_KEYS = {"path", "sha256", "size_bytes"}
TABLE_NAMES = ("footer", "generated_observations", "roots")
TABLE_FILES = {
    "footer": "footer.tsv",
    "generated_observations": "generated_observations.tsv",
    "roots": "roots.tsv",
    "tape_root_sidecar": "tape_roots.tsv",
}


class N1ValidationError(ValueError):
    """A deterministic N1 transaction-contract violation."""


def _exact_keys(value: Any, expected: set[str], context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = set(value) if isinstance(value, dict) else set()
        raise N1ValidationError(
            f"{context}: exact properties mismatch; missing={sorted(expected-actual)}, extra={sorted(actual-expected)}"
        )
    return value


def _digest(value: Any, context: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise N1ValidationError(f"{context}: malformed SHA-256")
    return value


def _integer(value: Any, context: str, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or (
        maximum is not None and value > maximum
    ):
        raise N1ValidationError(f"{context}: invalid integer")
    return value


def _read_regular_one_descriptor(path: Path, context: str) -> bytes:
    """Read and bind one regular, single-link file through one O_NOFOLLOW fd."""

    path = path.absolute()
    reject_lexical_symlinks(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise N1ValidationError(f"{context}: cannot open one-descriptor authority: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise N1ValidationError(f"{context}: expected a regular single-link file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    try:
        pathname = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise N1ValidationError(f"{context}: authority pathname disappeared: {exc}") from exc
    if identity_before != identity_after or (pathname.st_dev, pathname.st_ino) != (before.st_dev, before.st_ino):
        raise N1ValidationError(f"{context}: authority changed during one-descriptor read")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise N1ValidationError(f"{context}: short one-descriptor read")
    return payload


def _canonical_object(payload: bytes, context: str) -> dict[str, Any]:
    try:
        value = strict_json_bytes(payload, source=context)
        expected = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise N1ValidationError(f"{context}: invalid strict JSON: {exc}") from exc
    if not isinstance(value, dict) or payload != expected:
        raise N1ValidationError(f"{context}: root must be a canonical JSON object")
    return value


def _validate_binding(value: Any, context: str, *, table: bool) -> Mapping[str, Any]:
    binding = _exact_keys(value, TABLE_KEYS if table else BLOB_KEYS, context)
    if not isinstance(binding["path"], str) or not binding["path"] or Path(binding["path"]).name != binding["path"]:
        raise N1ValidationError(f"{context}.path: must be one basename")
    _digest(binding["sha256"], f"{context}.sha256")
    _integer(binding["size_bytes"], f"{context}.size_bytes", 0 if table else 1)
    if table:
        _integer(binding["row_count"], f"{context}.row_count", 0)
    return binding


def _manifest_shape(commit: dict[str, Any], schema: dict[str, Any], schema_digest: str) -> None:
    _exact_keys(commit, TOP_LEVEL_KEYS, "commit")
    if set(schema.get("required", [])) != TOP_LEVEL_KEYS or schema.get("additionalProperties") is not False:
        raise N1ValidationError("N1 commit schema does not declare the frozen exact top-level properties")
    if commit["arm"] != "N1" or commit["schema_version"] != "m05cc-n1-v1-commit":
        raise N1ValidationError("commit: wrong arm/schema_version")
    if commit["status"] != "PASS__N1_TRANSACTION_COMPLETE":
        raise N1ValidationError("commit: transaction status is not PASS")
    for name in (
        "corrected_source_card_sha256", "geometry_bundle_sha256", "geometry_classification_sha256",
        "n1_commit_schema_sha256", "runtime_source_card_sha256", "source_contract_sha256",
        "veto_whitelist_sha256",
    ):
        _digest(commit[name], f"commit.{name}")
    if commit["n1_commit_schema_sha256"] != schema_digest:
        raise N1ValidationError("commit: N1 schema digest differs from exact schema bytes")
    _integer(commit["native_added_isotope_count"], "commit.native_added_isotope_count", 0)
    run = _exact_keys(commit["run"], RUN_KEYS, "commit.run")
    if run["arm"] != "N1" or run["geometry"] not in GEOMETRIES or run["mode"] not in MODES or run["family"] not in FAMILIES:
        raise N1ValidationError("commit.run: invalid arm/geometry/mode/family")
    if not isinstance(run["job_id"], str) or JOB_ID_RE.fullmatch(run["job_id"]) is None:
        raise N1ValidationError("commit.run.job_id: malformed")
    _integer(run["expected_event_count"], "commit.run.expected_event_count", 1)
    _integer(run["shard_index"], "commit.run.shard_index", 0)
    _integer(run["seed"], "commit.run.seed", 1, 2_147_483_646)
    for name in TABLE_NAMES:
        binding = _validate_binding(commit[name], f"commit.{name}", table=True)
        if binding["path"] != TABLE_FILES[name]:
            raise N1ValidationError(f"commit.{name}.path: must be {TABLE_FILES[name]!r}")
    tape = _validate_binding(commit["tape_root_sidecar"], "commit.tape_root_sidecar", table=True)
    if tape["path"] != TABLE_FILES["tape_root_sidecar"]:
        raise N1ValidationError("commit.tape_root_sidecar.path: must be 'tape_roots.tsv'")
    native = _validate_binding(commit["native_dat"], "commit.native_dat", table=False)
    if NATIVE_DAT_RE.fullmatch(native["path"]) is None:
        raise N1ValidationError("commit.native_dat.path: wrong native incarnation basename")


def _read_table_bytes(
    payload: bytes, name: str, contract: Mapping[str, Any], declared_rows: int,
) -> list[dict[str, Any]]:
    if b"\r" in payload or b"\x00" in payload:
        raise N1ValidationError(f"{name}: only UTF-8 LF text is allowed")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise N1ValidationError(f"{name}: invalid UTF-8") from exc
    if not text.endswith("\n"):
        raise N1ValidationError(f"{name}: missing final LF")
    lines = text.splitlines()
    header = lines[0].split("\t") if lines else []
    if header != contract["header"] or len(header) != len(set(header)):
        raise N1ValidationError(f"{name}: exact header/order mismatch")
    rows: list[dict[str, Any]] = []
    try:
        reader = csv.reader(lines[1:], delimiter="\t", quoting=csv.QUOTE_NONE, strict=True)
        for line_number, fields in enumerate(reader, 2):
            if len(fields) != len(header):
                raise N1ValidationError(f"{name}:{line_number}: wrong field count")
            raw = dict(zip(header, fields, strict=True))
            rows.append({
                column: _parse_cell(raw[column], contract["columns"][column], f"{name}:{line_number}:{column}")
                for column in header
            })
    except (csv.Error, RecordValidationError) as exc:
        raise N1ValidationError(f"{name}: invalid typed TSV: {exc}") from exc
    if len(rows) != declared_rows or (not contract["allow_empty"] and not rows):
        raise N1ValidationError(f"{name}: declared/actual/allow-empty row closure failed")
    try:
        _validate_keys(name, rows, [contract["primary_key"], *contract.get("unique_keys", [])])
    except RecordValidationError as exc:
        raise N1ValidationError(str(exc)) from exc
    return rows


def _parse_tape_sidecar(payload: bytes) -> list[dict[str, str]]:
    if b"\r" in payload or b"\x00" in payload or not payload.endswith(b"\n"):
        raise N1ValidationError("tape_roots: invalid LF/byte envelope")
    try:
        lines = payload.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise N1ValidationError("tape_roots: invalid UTF-8") from exc
    if not lines or tuple(lines[0].split("\t")) != SIDECAR_COLUMNS:
        raise N1ValidationError("tape_roots: exact 40-column header mismatch")
    rows: list[dict[str, str]] = []
    for number, line in enumerate(lines[1:], 2):
        fields = line.split("\t")
        if len(fields) != len(SIDECAR_COLUMNS):
            raise N1ValidationError(f"tape_roots:{number}: wrong field count")
        rows.append(dict(zip(SIDECAR_COLUMNS, fields, strict=True)))
    return rows


def _validate_roots(run: Mapping[str, Any], roots: list[dict[str, Any]]) -> None:
    expected = run["expected_event_count"]
    if len(roots) != expected:
        raise N1ValidationError("roots: row count differs from expected_event_count")
    if sum(row["control_flag"] for row in roots) < min(3, expected):
        raise N1ValidationError("roots: missing the deterministic first-three pre-registered controls")
    for index, root in enumerate(sorted(roots, key=lambda row: row["simulation_event_id"])):
        event_id = index + 1
        if (root["simulation_event_id"], root["row_index0"], root["eventlist_id"]) != (event_id, index, event_id):
            raise N1ValidationError(f"roots: noncontiguous event/row/EventList IDs at event {event_id}")
        if root["family"] != run["family"]:
            raise N1ValidationError(f"roots: family differs from run at event {event_id}")
        if any(root[name] != 1 for name in ("generated_flag", "started_flag", "native_event_populated", "completed_flag")):
            raise N1ValidationError(f"roots: incomplete lifecycle at event {event_id}")
        if root["aborted_flag"] != 0 or root["expected_generated_tuple_sha256"] != root["observed_generated_tuple_sha256"]:
            raise N1ValidationError(f"roots: aborted or altered generated tuple at event {event_id}")
        if root["driver_inference_quality"] != "unavailable" or root["driver_inference"] or root["driver_inference_ambiguity_set"]:
            raise N1ValidationError(f"roots: N1 must preserve sampled driver and unavailable inference at event {event_id}")


def _validate_tape_join(
    commit: Mapping[str, Any], tape_rows: list[dict[str, str]], roots: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> None:
    roots = sorted(roots, key=lambda row: row["simulation_event_id"])
    observations = sorted(observations, key=lambda row: row["simulation_event_id"])
    if len(tape_rows) != len(roots) or len(observations) != len(roots):
        raise N1ValidationError("tape/root/generated-observation row-count closure failed")
    previous_internal = 0.0
    for event_id, (tape, root, observation) in enumerate(zip(tape_rows, roots, observations, strict=True), 1):
        if tape.get("family") != commit["run"]["family"]:
            raise N1ValidationError(f"tape_roots: event {event_id} family differs from commit.run")
        if tape.get("mode") != commit["run"]["mode"]:
            raise N1ValidationError(f"tape_roots: event {event_id} mode differs from commit.run")
        try:
            primary = _primary_from_row(tape)
            raw_binary = eventlist_binary64_hash(primary)
            runtime_time, previous_internal = runtime_source_time_projection(primary.source_time_s, previous_internal)
            generated_binary = generated_binary64_hash(primary, runtime_source_time_s=runtime_time)
            generated_tuple = generated_tuple_hash(primary)
            stable_root = sha256_bytes(canonical_json_bytes(_root_payload(
                row=tape,
                raw_line_sha256=tape["raw_eventlist_line_sha256"],
                eventlist_binary64_sha256=raw_binary,
                generated_binary64_sha256=generated_binary,
                tuple_sha256=generated_tuple,
            )))
        except (KeyError, TypeError, ValueError) as exc:
            raise N1ValidationError(f"tape_roots: invalid row {event_id}: {exc}") from exc
        exact = (
            (event_id, observation["simulation_event_id"], "observation simulation event ID"),
            (int(tape["row_index0"]), root["row_index0"], "row index"),
            (int(tape["eventlist_id"]), root["eventlist_id"], "EventList ID"),
            (int(tape["eventlist_id"]), observation["eventlist_id"], "observation EventList ID"),
            (tape["stable_root_id"], root["stable_root_id"], "stable root"),
            (tape["stable_root_id"], observation["stable_root_id"], "observation stable root"),
            (tape["driver"], root["benchmark_driver_id"], "sampled driver"),
            (tape["family"], root["family"], "family"),
            (tape["raw_eventlist_line_sha256"], root["raw_tape_line_sha256"], "raw line hash"),
            (tape["expected_generated_tuple_sha256"], root["expected_generated_tuple_sha256"], "tuple hash"),
            (int(tape["control_flag"]), root["control_flag"], "control flag"),
            (tape["expected_eventlist_binary64_sha256"], observation["raw_eventlist_binary64_sha256"], "raw binary64"),
            (tape["expected_generated_binary64_sha256"], observation["observed_generated_binary64_sha256"], "generated binary64"),
            (raw_binary, tape["expected_eventlist_binary64_sha256"], "recomputed raw binary64"),
            (generated_binary, tape["expected_generated_binary64_sha256"], "recomputed generated binary64"),
            (generated_tuple, tape["expected_generated_tuple_sha256"], "recomputed generated tuple"),
            (stable_root, tape["stable_root_id"], "recomputed stable root"),
            (commit["corrected_source_card_sha256"], tape["source_card_sha256"], "corrected source card"),
            (commit["source_contract_sha256"], tape["source_contract_sha256"], "source contract"),
        )
        for expected, actual, label in exact:
            if actual != expected:
                raise N1ValidationError(f"tape_roots: event {event_id} {label} mismatch")


def _validate_footer(
    commit: Mapping[str, Any], footer_rows: list[dict[str, Any]], roots: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(footer_rows) != 1:
        raise N1ValidationError("footer: exactly one row required")
    footer = footer_rows[0]
    run = commit["run"]
    for name in ("arm", "geometry", "mode", "family", "job_id", "shard_index", "seed"):
        if footer[name] != run[name]:
            raise N1ValidationError(f"footer.{name}: differs from commit.run")
    if footer["active_block_coverage"] != "geometry_specific":
        raise N1ValidationError("footer: active_block_coverage drift")
    if footer["veto_whitelist_sha256"] != commit["veto_whitelist_sha256"]:
        raise N1ValidationError("footer: whitelist hash differs from commit")
    if footer["record_schema_sha256"] != commit["n1_commit_schema_sha256"]:
        raise N1ValidationError("footer: schema hash is not the independent N1 commit schema")
    expected = run["expected_event_count"]
    for name in (
        "tape_count", "generated_count", "started_count", "completed_count", "native_populated_count",
        "root_count", "ia_init_count", "native_observed_simulation_event_id_count",
        "native_observed_event_id_count",
    ):
        if footer[name] != expected:
            raise N1ValidationError(f"footer.{name}: must equal expected_event_count")
    if footer["aborted_count"] != 0 or footer["rp_row_count"] != 0 or footer["finalized"] != 1:
        raise N1ValidationError("footer: N1 requires aborted=0, RP-sidecar rows=0, finalized=1")
    if not footer["TT_s"] > 0.0:
        raise N1ValidationError("footer: positive finite TT is required, including zero-RP jobs")
    lifecycle = {
        "generated_count": sum(row["generated_flag"] for row in roots),
        "started_count": sum(row["started_flag"] for row in roots),
        "completed_count": sum(row["completed_flag"] for row in roots),
        "native_populated_count": sum(row["native_event_populated"] for row in roots),
        "root_count": len(roots),
        "aborted_count": sum(row["aborted_flag"] for row in roots),
    }
    for name, value in lifecycle.items():
        if footer[name] != value:
            raise N1ValidationError(f"footer.{name}: differs from root lifecycle rows")
    return footer


def _validate_runtime_source_card(
    path: Path, commit: Mapping[str, Any], eventlist_path: Path, geometry_setup: str,
    native_isotope_base: str,
) -> None:
    payload = _read_regular_one_descriptor(path, "runtime source card")
    if sha256_bytes(payload) != commit["runtime_source_card_sha256"]:
        raise N1ValidationError("runtime source card: digest differs from commit")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise N1ValidationError("runtime source card: invalid UTF-8") from exc
    run = commit["run"]
    run_name = f"M05_{run['family']}_{run['mode']}_s{run['shard_index']}_N1"
    expected_lines = [
        "# NON_MERGEABLE_BENCHMARK: isolated matched M05 compact smoke",
        "# Frozen EventList is the only source input; no spectrum/beam/flux source is permitted.",
        f"# canonical_geometry_bundle_sha256={commit['geometry_bundle_sha256']}",
        f"# corrected_source_contract_sha256={commit['source_contract_sha256']}",
        f"Geometry {geometry_setup}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreOneHitPerEvent false",
        "StoreIsotopes true",
    ]
    if run["mode"] == "buildup":
        expected_lines.append("DecayMode ActivationBuildUp")
    expected_lines.extend([
        "DetectorTimeConstant 1e-9",
        "StoreTextScientific true 17",
        "PreTriggerMode Everything",
        "",
        f"Run {run_name}",
        f"{run_name}.Events {run['expected_event_count']}",
        f"{run_name}.IsotopeProductionFile {native_isotope_base}",
        f"{run_name}.Source FrozenPrimary",
        f"FrozenPrimary.EventList {eventlist_path.resolve()}",
        "",
    ])
    expected_payload = "\n".join(expected_lines).encode("utf-8")
    if payload != expected_payload:
        raise N1ValidationError(
            "runtime source card: exact directive/comment/order/newline closure failed"
        )

def validate_n1_commit(
    commit_path: Path | str,
    *,
    eventlist_path: Path | str,
    runtime_source_card_path: Path | str,
    geometry_classification_path: Path | str,
    schema_path: Path | str = SCHEMA_PATH,
    whitelist_path: Path | str = WHITELIST_PATH,
    expected_output_prefix: Path | str,
    expected_job_id: str,
    expected_geometry: str,
    expected_mode: str,
    expected_family: str,
    expected_shard_index: int,
    expected_seed: int,
    expected_event_count: int,
    expected_eventlist_sha256: str,
    expected_tape_root_sidecar_sha256: str,
    expected_runtime_source_card_sha256: str,
    expected_geometry_bundle_sha256: str,
    expected_geometry_classification_sha256: str,
    expected_corrected_source_card_sha256: str,
    verify_external_authorities: bool = True,
) -> dict[str, Any]:
    """Validate one finalized N1 ``commit.json`` and all exact dependencies."""

    commit_path = Path(commit_path).absolute()
    eventlist_path = Path(eventlist_path).absolute()
    runtime_source_card_path = Path(runtime_source_card_path).absolute()
    geometry_classification_path = Path(geometry_classification_path).absolute()
    schema_path = Path(schema_path).absolute()
    whitelist_path = Path(whitelist_path).absolute()
    expected_output_prefix = Path(expected_output_prefix).absolute()
    expected_commit_path = Path(str(expected_output_prefix) + ".m05cc") / "commit.json"
    if commit_path != expected_commit_path or commit_path.name != "commit.json" or not commit_path.parent.name.endswith(".m05cc"):
        raise N1ValidationError("N1 validator accepts only the externally planned <output>.m05cc/commit.json")
    commit_payload = _read_regular_one_descriptor(commit_path, "commit")
    schema_payload = _read_regular_one_descriptor(schema_path, "N1 schema")
    canonical_schema_payload = _read_regular_one_descriptor(SCHEMA_PATH, "canonical N1 schema")
    if schema_path != SCHEMA_PATH.absolute() or schema_payload != canonical_schema_payload:
        raise N1ValidationError("N1 schema: substitute/self-signed schema authority is forbidden")
    commit = _canonical_object(commit_payload, "commit")
    schema = _canonical_object(schema_payload, "N1 schema")
    schema_digest = sha256_bytes(schema_payload)
    _manifest_shape(commit, schema, schema_digest)
    expected_run = {
        "arm": "N1",
        "expected_event_count": expected_event_count,
        "family": expected_family,
        "geometry": expected_geometry,
        "job_id": expected_job_id,
        "mode": expected_mode,
        "seed": expected_seed,
        "shard_index": expected_shard_index,
    }
    if commit["run"] != expected_run:
        raise N1ValidationError("commit.run: differs from externally planned exact job identity")
    expected_digests = {
        "corrected_source_card_sha256": expected_corrected_source_card_sha256,
        "geometry_bundle_sha256": expected_geometry_bundle_sha256,
        "geometry_classification_sha256": expected_geometry_classification_sha256,
        "runtime_source_card_sha256": expected_runtime_source_card_sha256,
    }
    for name, expected_digest in expected_digests.items():
        _digest(expected_digest, f"expected.{name}")
        if commit[name] != expected_digest:
            raise N1ValidationError(f"commit.{name}: differs from externally planned digest")
    for name, value in (
        ("expected_eventlist_sha256", expected_eventlist_sha256),
        ("expected_tape_root_sidecar_sha256", expected_tape_root_sidecar_sha256),
    ):
        _digest(value, name)
    if commit["tape_root_sidecar"]["sha256"] != expected_tape_root_sidecar_sha256:
        raise N1ValidationError("commit.tape_root_sidecar: differs from externally planned digest")

    member_names: set[str] = set()
    reject_lexical_symlinks(commit_path.parent)
    try:
        with os.scandir(commit_path.parent) as iterator:
            for entry in iterator:
                if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                    raise N1ValidationError(f"transaction directory has a non-regular member: {entry.name}")
                member_names.add(entry.name)
    except OSError as exc:
        raise N1ValidationError(f"cannot enumerate N1 transaction: {exc}") from exc
    expected_members = {
        "commit.json", "footer.tsv", "generated_observations.tsv", "roots.tsv", "tape_roots.tsv",
        commit["native_dat"]["path"],
    }
    if member_names != expected_members:
        raise N1ValidationError(
            f"transaction exact member closure failed; missing={sorted(expected_members-member_names)}, "
            f"extra={sorted(member_names-expected_members)}"
        )

    payloads: dict[str, bytes] = {"commit.json": commit_payload}
    bindings = {name: commit[name] for name in (*TABLE_NAMES, "tape_root_sidecar", "native_dat")}
    for name, binding in bindings.items():
        member = commit_path.parent / binding["path"]
        payload = _read_regular_one_descriptor(member, name)
        payloads[binding["path"]] = payload
        if len(payload) != binding["size_bytes"] or sha256_bytes(payload) != binding["sha256"]:
            raise N1ValidationError(f"commit.{name}: size/SHA binding mismatch")

    contracts = schema["x-tsv-tables"]
    tables = {
        name: _read_table_bytes(payloads[commit[name]["path"]], name, contracts[name], commit[name]["row_count"])
        for name in TABLE_NAMES
    }
    tape_rows = _parse_tape_sidecar(payloads[commit["tape_root_sidecar"]["path"]])
    if len(tape_rows) != commit["tape_root_sidecar"]["row_count"]:
        raise N1ValidationError("tape_roots: declared row count mismatch")
    _validate_roots(commit["run"], tables["roots"])
    try:
        _validate_generated_observations(tables)
    except (KeyError, RecordValidationError) as exc:
        raise N1ValidationError(f"generated observations: {exc}") from exc
    _validate_tape_join(commit, tape_rows, tables["roots"], tables["generated_observations"])
    footer = _validate_footer(commit, tables["footer"], tables["roots"])

    try:
        native_tt, native_totals = _parse_native_dat(payloads[commit["native_dat"]["path"]])
    except RecordValidationError as exc:
        raise N1ValidationError(f"native DAT: {exc}") from exc
    native_count = sum(native_totals.values())
    if native_count != commit["native_added_isotope_count"]:
        raise N1ValidationError("native DAT aggregate count differs from native AddIsotope count")
    if not math.isclose(footer["TT_s"], native_tt, rel_tol=5.0e-6, abs_tol=5.0e-12):
        raise N1ValidationError("native DAT TT differs from footer beyond native serialization precision")

    whitelist_payload = _read_regular_one_descriptor(whitelist_path, "active whitelist")
    canonical_whitelist_payload = _read_regular_one_descriptor(WHITELIST_PATH, "canonical active whitelist")
    if whitelist_path != WHITELIST_PATH.absolute() or whitelist_payload != canonical_whitelist_payload:
        raise N1ValidationError("active whitelist: substitute/self-signed authority is forbidden")
    if sha256_bytes(whitelist_payload) != commit["veto_whitelist_sha256"]:
        raise N1ValidationError("active whitelist digest differs from commit")
    try:
        whitelist_value = strict_json_bytes(whitelist_payload, source="active whitelist")
    except ValueError as exc:
        raise N1ValidationError(f"active whitelist: invalid strict JSON: {exc}") from exc
    if not isinstance(whitelist_value, dict):
        raise N1ValidationError("active whitelist: JSON root must be an object")
    classification_payload = _read_regular_one_descriptor(geometry_classification_path, "geometry classification")
    classification = _canonical_object(classification_payload, "geometry classification")
    if sha256_bytes(classification_payload) != commit["geometry_classification_sha256"]:
        raise N1ValidationError("geometry classification digest differs from commit")
    if classification.get("active_volume_whitelist_sha256") != commit["veto_whitelist_sha256"]:
        raise N1ValidationError("geometry classification/active whitelist digest join failed")
    try:
        from geometry_classification import validate_geometry_classification
        validate_geometry_classification(classification, verify_canonical_authority=verify_external_authorities)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise N1ValidationError(f"geometry classification authority failed: {exc}") from exc
    geometry_rows = [row for row in classification["geometries"] if row["geometry"] == commit["run"]["geometry"]]
    if len(geometry_rows) != 1 or geometry_rows[0]["geometry_bundle_sha256"] != commit["geometry_bundle_sha256"]:
        raise N1ValidationError("geometry bundle differs from classification authority")
    try:
        geometry_setup = repo_path(geometry_rows[0]["geometry_setup"])
    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
        raise N1ValidationError(f"geometry setup authority failed: {exc}") from exc

    _validate_runtime_source_card(
        runtime_source_card_path,
        commit,
        eventlist_path,
        str(geometry_setup),
        str(commit_path.parent) + ".partial/native",
    )
    if verify_external_authorities and commit["source_contract_sha256"] != SOURCE_CONTRACT_SHA256:
        raise N1ValidationError("corrected-keV source contract digest drift")
    eventlist_payload = _read_regular_one_descriptor(eventlist_path, "EventList tape")
    if sha256_bytes(eventlist_payload) != expected_eventlist_sha256:
        raise N1ValidationError("EventList tape differs from externally planned digest")
    try:
        tape_result = validate_sidecar(
            eventlist_path, commit_path.parent / commit["tape_root_sidecar"]["path"],
            verify_authorities=verify_external_authorities,
            verify_sampler=verify_external_authorities,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise N1ValidationError(f"EventList/tape-roots authority validation failed: {exc}") from exc
    if (
        tape_result["event_count"] != commit["run"]["expected_event_count"]
        or tape_result["family"] != commit["run"]["family"]
        or tape_result["mode"] != commit["run"]["mode"]
    ):
        raise N1ValidationError("EventList/tape-roots family/mode/event count differs from commit")
    # The external validator may reopen files internally; prove it observed the
    # same frozen transaction bytes and runtime inputs before accepting PASS.
    if (
        sha256(commit_path.parent / commit["tape_root_sidecar"]["path"])
        != commit["tape_root_sidecar"]["sha256"]
        or sha256(runtime_source_card_path) != commit["runtime_source_card_sha256"]
        or sha256(eventlist_path) != sha256_bytes(eventlist_payload)
    ):
        raise N1ValidationError("tape/source authority changed during external validation")

    return {
        "schema_version": "m05cc-n1-v1-validation",
        "status": "PASS__M05CC_N1_V1_COMMIT",
        "arm": "N1",
        "commit_path": str(commit_path),
        "commit_sha256": sha256_bytes(commit_payload),
        "n1_commit_schema_path": str(schema_path),
        "n1_commit_schema_sha256": schema_digest,
        "runtime_source_card_path": str(runtime_source_card_path),
        "runtime_source_card_sha256": commit["runtime_source_card_sha256"],
        "eventlist_path": str(eventlist_path),
        "eventlist_sha256": sha256(eventlist_path),
        "tape_root_sidecar_sha256": commit["tape_root_sidecar"]["sha256"],
        "geometry_classification_path": str(geometry_classification_path),
        "geometry_classification_sha256": commit["geometry_classification_sha256"],
        "geometry_bundle_sha256": commit["geometry_bundle_sha256"],
        "expected_event_count": commit["run"]["expected_event_count"],
        "root_count": len(tables["roots"]),
        "generated_observation_count": len(tables["generated_observations"]),
        "native_added_isotope_count": native_count,
        "native_dat_TT_s": native_tt,
        "native_dat_evidence_grain": "AGGREGATE_ONLY__NO_N1_RP_SIDECAR_OR_LINEAGE_CLAIM",
        "materializer_eligible": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit", type=Path, help="final <output>.m05cc/commit.json")
    parser.add_argument("--eventlist", required=True, type=Path)
    parser.add_argument("--runtime-source-card", required=True, type=Path)
    parser.add_argument("--geometry-classification", required=True, type=Path)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--whitelist", type=Path, default=WHITELIST_PATH)
    parser.add_argument("--expected-output-prefix", required=True, type=Path)
    parser.add_argument("--expected-job-id", required=True)
    parser.add_argument("--expected-geometry", required=True, choices=sorted(GEOMETRIES))
    parser.add_argument("--expected-mode", required=True, choices=sorted(MODES))
    parser.add_argument("--expected-family", required=True, choices=sorted(FAMILIES))
    parser.add_argument("--expected-shard-index", required=True, type=int)
    parser.add_argument("--expected-seed", required=True, type=int)
    parser.add_argument("--expected-event-count", required=True, type=int)
    parser.add_argument("--expected-eventlist-sha256", required=True)
    parser.add_argument("--expected-tape-root-sidecar-sha256", required=True)
    parser.add_argument("--expected-runtime-source-card-sha256", required=True)
    parser.add_argument("--expected-geometry-bundle-sha256", required=True)
    parser.add_argument("--expected-geometry-classification-sha256", required=True)
    parser.add_argument("--expected-corrected-source-card-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_n1_commit(
            args.commit,
            eventlist_path=args.eventlist,
            runtime_source_card_path=args.runtime_source_card,
            geometry_classification_path=args.geometry_classification,
            schema_path=args.schema,
            whitelist_path=args.whitelist,
            expected_output_prefix=args.expected_output_prefix,
            expected_job_id=args.expected_job_id,
            expected_geometry=args.expected_geometry,
            expected_mode=args.expected_mode,
            expected_family=args.expected_family,
            expected_shard_index=args.expected_shard_index,
            expected_seed=args.expected_seed,
            expected_event_count=args.expected_event_count,
            expected_eventlist_sha256=args.expected_eventlist_sha256,
            expected_tape_root_sidecar_sha256=args.expected_tape_root_sidecar_sha256,
            expected_runtime_source_card_sha256=args.expected_runtime_source_card_sha256,
            expected_geometry_bundle_sha256=args.expected_geometry_bundle_sha256,
            expected_geometry_classification_sha256=args.expected_geometry_classification_sha256,
            expected_corrected_source_card_sha256=args.expected_corrected_source_card_sha256,
        )
    except N1ValidationError as exc:
        print(json.dumps({"status": "FAIL__M05CC_N1_V1_COMMIT", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
