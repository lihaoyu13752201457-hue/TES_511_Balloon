#!/usr/bin/env python3
"""Run and attest a real Revan consumer over a materialized standalone SIM.

This is a reconstruction/representation consumer only.  It invokes Revan in
batch analysis mode and never invokes Cosima, EventList, Geant4, or transport.
Revan's zero exit status is not trusted by itself: the completion marker,
triggered input count, TRA envelope/geometry, event IDs, sizes, and hashes are
all checked before a write-once attestation directory is atomically published.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from materialize_standalone_sim import (
    MATERIALIZER_VERSION,
    OUTPUT_INDEX_COLUMNS,
    SIM_VERSION,
    FROZEN_REVAN_CONFIG,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json,
)
from preflight_common import fsync_directory, quarantine_directory_no_replace, rename_no_replace


GATE_VERSION = "m05-revan-zero-transport-gate-v1"
PASS_STATUS = "PASS__REAL_REVAN_CONSUMER_RECONSTRUCTION"
TRIGGERED_RE = re.compile(r"^\s*Number of triggered events: \.+\s+([0-9]+)\s*$", re.MULTILINE)
TRA_ID_RE = re.compile(rb"(?m)^ID ([1-9][0-9]*)$")


class GateError(ValueError):
    """A fail-closed real-consumer gate violation."""


def _regular_no_link(path: Path) -> Path:
    path = Path(os.path.abspath(os.fspath(path)))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            mode = os.lstat(current).st_mode
        except OSError as error:
            raise GateError(f"cannot lstat required path {current}: {error}") from error
        if stat.S_ISLNK(mode):
            raise GateError(f"symlink component is forbidden: {current}")
    if not path.is_file():
        raise GateError(f"not a regular file: {path}")
    return path


def _manifest_binding(binding: Mapping[str, Any], name: str) -> Path:
    if not {"path", "sha256", "size_bytes"} <= set(binding):
        raise GateError(f"materializer manifest lacks complete {name} binding")
    path = _regular_no_link(Path(binding["path"]))
    if path.stat().st_size != binding["size_bytes"] or sha256_file(path) != binding["sha256"]:
        raise GateError(f"materializer {name} size/hash binding failed")
    return path


def _load_index(path: Path, expected_rows: int) -> list[dict[str, str]]:
    payload = path.read_bytes()
    if b"\r" in payload or b"\x00" in payload or not payload.endswith(b"\n"):
        raise GateError("materializer index is not strict UTF-8/LF text")
    try:
        rows = list(csv.reader(payload.decode("utf-8").splitlines(), delimiter="\t", strict=True))
    except (UnicodeError, csv.Error) as error:
        raise GateError(f"cannot parse materializer index: {error}") from error
    if not rows or tuple(rows[0]) != OUTPUT_INDEX_COLUMNS:
        raise GateError("materializer index exact header mismatch")
    if len(rows) - 1 != expected_rows or any(len(row) != len(OUTPUT_INDEX_COLUMNS) for row in rows[1:]):
        raise GateError("materializer index cardinality/field-count mismatch")
    return [dict(zip(OUTPUT_INDEX_COLUMNS, row, strict=True)) for row in rows[1:]]


def _validate_sim_ranges(sim: bytes, rows: Sequence[Mapping[str, str]], geometry: str) -> None:
    prefix = sim.split(b"SE\n", 1)[0]
    required = (
        b"Type       SIM\n",
        f"Version    {SIM_VERSION}\n".encode("utf-8"),
        f"Geometry   {geometry}\n".encode("utf-8"),
    )
    if any(token not in prefix for token in required) or sim.count(b"SE\n") != len(rows):
        raise GateError("standalone SIM envelope/SE count mismatch")
    seen_ids: set[int] = set()
    for expected_id, row in enumerate(rows, 1):
        if row["schema"] != MATERIALIZER_VERSION or int(row["simulation_event_id"]) != expected_id:
            raise GateError("materializer index schema/event order mismatch")
        offset, length = int(row["standalone_offset"]), int(row["standalone_length"])
        fragment = sim[offset:offset + length]
        if len(fragment) != length or sha256_bytes(fragment) != row["standalone_sha256"]:
            raise GateError("standalone indexed event range/hash mismatch")
        match = re.search(rb"(?m)^ID ([1-9][0-9]*) ([1-9][0-9]*)$", fragment)
        if match is None or int(match.group(1)) != expected_id or int(match.group(2)) != expected_id:
            raise GateError("standalone indexed event ID mismatch")
        seen_ids.add(expected_id)
    if len(seen_ids) != len(rows):
        raise GateError("standalone event IDs are not unique")


def _validate_tra(payload: bytes, geometry: str, input_ids: set[int]) -> list[int]:
    if b"\r" in payload or b"\x00" in payload or not payload.endswith(b"\n"):
        raise GateError("Revan TRA is not NUL-free LF/newline-terminated text")
    prefix = payload.split(b"SE\n", 1)[0]
    if b"Type      tra\n" not in prefix or b"Version   1\n" not in prefix:
        raise GateError("Revan TRA lacks exact Type/Version envelope")
    if f"Geometry  {geometry}\n".encode("utf-8") not in prefix:
        raise GateError("Revan TRA geometry differs from materialized SIM")
    if payload.count(b"FT START\n") != 1 or payload.count(b"FT STOP\n") != 1:
        raise GateError("Revan TRA lacks one complete footer statistics block")
    ids = [int(match.group(1)) for match in TRA_ID_RE.finditer(payload)]
    if len(ids) != len(set(ids)) or any(event_id not in input_ids for event_id in ids):
        raise GateError("Revan TRA event IDs are duplicate or absent from standalone SIM")
    if payload.count(b"SE\n") != len(ids) or payload.count(b"\nEN\n") < len(ids):
        raise GateError("Revan TRA SE/ID/EN event closure failed")
    return ids


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def run_gate(
    *,
    standalone_manifest: Path,
    revan_executable: Path,
    revan_config: Path,
    output_prefix: Path,
    timeout_s: int = 120,
) -> dict[str, Any]:
    manifest_path = _regular_no_link(standalone_manifest)
    manifest = strict_json(manifest_path)
    if manifest.get("schema_version") != MATERIALIZER_VERSION:
        raise GateError("wrong standalone materializer manifest schema")
    if manifest.get("sim_envelope", {}).get("version") != SIM_VERSION:
        raise GateError("standalone manifest does not require SIM Version 101")
    if manifest.get("invariants", {}).get("transport_events_launched") != 0:
        raise GateError("standalone manifest is not a zero-transport representation")
    geometry = manifest["sim_envelope"]["geometry"]
    if sha256_file(_regular_no_link(Path(geometry))) != manifest["sim_envelope"]["geometry_sha256"]:
        raise GateError("standalone geometry binding failed")
    sim_path = _manifest_binding(manifest["output"]["sim"], "SIM")
    index_path = _manifest_binding(manifest["output"]["index"], "index")
    expected_count = manifest["counts"]["event_count"]
    rows = _load_index(index_path, expected_count)
    sim_payload = sim_path.read_bytes()
    _validate_sim_ranges(sim_payload, rows, geometry)

    executable = _regular_no_link(Path(revan_executable))
    source_config = _regular_no_link(revan_config)
    frozen_config = _regular_no_link(FROZEN_REVAN_CONFIG)
    declared_config = manifest.get("revan_consumer", {}).get("frozen_configuration", {})
    frozen_payload = frozen_config.read_bytes()
    if (
        declared_config.get("path") != os.fspath(frozen_config)
        or declared_config.get("sha256") != sha256_bytes(frozen_payload)
        or declared_config.get("size_bytes") != len(frozen_payload)
    ):
        raise GateError("standalone manifest has a stale/incomplete frozen Revan configuration binding")
    if source_config.read_bytes() != frozen_payload:
        raise GateError("supplied Revan configuration differs from the frozen package fixture")
    final_dir = Path(os.path.abspath(os.fspath(output_prefix) + ".revan"))
    partial_dir = Path(str(final_dir) + ".partial")
    if final_dir.exists() or partial_dir.exists() or final_dir.is_symlink() or partial_dir.is_symlink():
        raise FileExistsError(f"write-once Revan gate output exists: {final_dir}")
    if not final_dir.parent.is_dir() or final_dir.parent.is_symlink():
        raise GateError("Revan gate output parent must be an existing real directory")
    partial_dir.mkdir(mode=0o775)
    config_copy = partial_dir / "revan.cfg"
    tra_path = partial_dir / "output.tra"
    log_path = partial_dir / "revan.log"
    attestation_path = partial_dir / "attestation.json"
    try:
        _write_exclusive(config_copy, source_config.read_bytes())
        command = [
            os.fspath(executable), "-c", os.fspath(config_copy), "-a", "-n",
            "-g", geometry, "-f", os.fspath(sim_path), "-o", os.fspath(tra_path),
        ]
        try:
            completed = subprocess.run(
                command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=timeout_s, cwd=partial_dir,
            )
        except subprocess.TimeoutExpired as error:
            raise GateError(f"Revan exceeded {timeout_s}s timeout") from error
        log_payload = completed.stdout
        _write_exclusive(log_path, log_payload)
        try:
            log_text = log_payload.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise GateError("Revan log is not UTF-8") from error
        failure_markers = (
            "Event reconstruction: Initialization failed",
            "Event reconstruction: Postprocessing failed",
            "is no aceptable geometry file",
        )
        if completed.returncode != 0 or "Event reconstruction finished in " not in log_text or any(
            marker in log_text for marker in failure_markers
        ):
            raise GateError(f"Revan did not complete reconstruction (exit={completed.returncode})")
        version_match = re.search(r"MEGAlib version ([0-9.]+)", log_text)
        if version_match is None:
            raise GateError("Revan banner lacks an observable MEGAlib version")
        triggered = [int(value) for value in TRIGGERED_RE.findall(log_text)]
        if triggered != [expected_count]:
            raise GateError(f"Revan triggered-count closure failed: {triggered} != [{expected_count}]")
        if not tra_path.is_file():
            raise GateError("Revan completed without a TRA output")
        with tra_path.open("rb+") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tra_payload = tra_path.read_bytes()
        tra_ids = _validate_tra(tra_payload, geometry, set(range(1, expected_count + 1)))
        attestation = {
            "schema_version": GATE_VERSION,
            "status": PASS_STATUS,
            "consumer": {
                "name": "Revan",
                "observed_megalib_version": version_match.group(1),
                "executable": os.fspath(executable),
                "executable_sha256": sha256_file(executable),
                "configuration_source_sha256": sha256_file(source_config),
                "configuration_contract_path": os.fspath(frozen_config),
                "configuration_post_run_sha256": sha256_file(config_copy),
            },
            "command_argv": command,
            "input": {
                "standalone_manifest": {"path": os.fspath(manifest_path), "sha256": sha256_file(manifest_path)},
                "sim": {"path": os.fspath(sim_path), "sha256": sha256_file(sim_path), "size_bytes": len(sim_payload)},
                "index": {"path": os.fspath(index_path), "sha256": sha256_file(index_path), "row_count": len(rows)},
                "geometry": {"path": geometry, "sha256": manifest["sim_envelope"]["geometry_sha256"]},
            },
            "counts": {
                "standalone_event_count": expected_count,
                "revan_triggered_event_count": triggered[0],
                "tra_reconstructed_event_count": len(tra_ids),
                "tra_reconstructed_event_ids": tra_ids,
            },
            "output": {
                "tra": {"path": os.fspath(final_dir / "output.tra"), "sha256": sha256_bytes(tra_payload), "size_bytes": len(tra_payload)},
                "log": {"path": os.fspath(final_dir / "revan.log"), "sha256": sha256_bytes(log_payload), "size_bytes": len(log_payload)},
            },
            "invariants": {
                "real_revan_consumer_invoked": True,
                "completion_marker_observed": True,
                "triggered_count_closes_to_standalone": True,
                "tra_ids_are_unique_subset_of_standalone": True,
                "transport_events_launched": 0,
            },
        }
        _write_exclusive(attestation_path, canonical_json_bytes(attestation))
        directory_fd = os.open(partial_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            rename_no_replace(partial_dir, final_dir)
            fsync_directory(final_dir.parent)
        except BaseException:
            if final_dir.exists() and not partial_dir.exists():
                quarantine_directory_no_replace(final_dir)
            raise
        return attestation
    except BaseException:
        # Keep only the quarantined .partial evidence on failure; never expose
        # a final-looking attestation namespace.
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standalone-manifest", required=True, type=Path)
    parser.add_argument("--revan", required=True, type=Path)
    parser.add_argument("--revan-config", required=True, type=Path)
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--timeout-s", type=int, default=120)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = run_gate(
        standalone_manifest=args.standalone_manifest,
        revan_executable=args.revan,
        revan_config=args.revan_config,
        output_prefix=args.output_prefix,
        timeout_s=args.timeout_s,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
