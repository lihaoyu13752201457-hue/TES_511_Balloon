#!/usr/bin/env python3
"""Publish durable zero-transport standalone-SIM consumer evidence.

This fixture materializes synthetic compact records against the real Mass
geometry, runs the installed MFileEventsSim/in-process-Revan consumer and the
real Revan CLI, and binds all inputs and outputs in a final commit marker.  It
never invokes Cosima, EventList, Geant4 transport, or a shadow transport binary.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


PACKAGE = Path(__file__).resolve().parents[1]
CODE = PACKAGE / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

import build_mfileeventssim_roundtrip  # noqa: E402
import geometry_classification  # noqa: E402
import materialize_standalone_sim as materializer  # noqa: E402
import revan_zero_transport_gate  # noqa: E402
from tests.test_standalone_materializer import build_fixture  # noqa: E402


EVIDENCE_VERSION = "m05-standalone-consumer-durable-fixture-v1"
PASS_STATUS = "PASS__DURABLE_REAL_MFILEEVENTSSIM_AND_REVAN_ZERO_TRANSPORT_FIXTURE"


class EvidenceError(ValueError):
    """A durable-evidence contract violation."""


def _binding(path: Path) -> dict[str, Any]:
    path = Path(os.path.abspath(os.fspath(path)))
    if not path.is_file() or path.is_symlink():
        raise EvidenceError(f"evidence member is not a real regular file: {path}")
    return {
        "path": os.fspath(path),
        "sha256": materializer.sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _assert_binding(binding: Mapping[str, Any]) -> None:
    path = Path(binding["path"])
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != binding["size_bytes"]
        or materializer.sha256_file(path) != binding["sha256"]
    ):
        raise EvidenceError(f"size/hash binding failed: {path}")


def _mass_geometry() -> Path:
    classification = geometry_classification.build_geometry_classification()
    matches = [
        row["geometry_setup"] for row in classification["geometries"]
        if row["geometry"] == "mass_model_511"
    ]
    if len(matches) != 1:
        raise EvidenceError("canonical classification lacks one Mass geometry")
    path = Path(matches[0])
    if not path.is_absolute():
        path = PACKAGE.parents[2] / path
    path = Path(os.path.abspath(os.fspath(path)))
    if not path.is_file() or path.is_symlink():
        raise EvidenceError(f"canonical Mass geometry is unavailable: {path}")
    return path


def _parse_roundtrip(output: bytes) -> dict[str, Any]:
    try:
        text = output.decode("utf-8")
    except UnicodeError as error:
        raise EvidenceError("round-trip consumer log is not UTF-8") from error
    records = [
        json.loads(line.split(" ", 1)[1]) for line in text.splitlines()
        if line.startswith("M05_ROUNDTRIP_JSON ")
    ]
    if len(records) != 1:
        raise EvidenceError("round-trip log lacks exactly one machine record")
    return records[0]


def run(output_directory: Path) -> dict[str, Any]:
    output_directory = Path(os.path.abspath(os.fspath(output_directory)))
    if output_directory.exists() or output_directory.is_symlink():
        raise FileExistsError(f"write-once evidence directory exists: {output_directory}")
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    output_directory.mkdir(mode=0o775)

    geometry = _mass_geometry()
    consumer, build_manifest = build_mfileeventssim_roundtrip.build_consumer()
    build_manifest_path = Path(os.fspath(consumer) + ".json")
    if build_manifest.get("transport_events_launched") != 0:
        raise EvidenceError("consumer build manifest is not zero-transport")
    megalib_root = Path(build_manifest["identity"]["megalib_root"])
    revan_executable = megalib_root / "bin/revan"
    if not revan_executable.is_file() or revan_executable.is_symlink():
        raise EvidenceError(f"real Revan executable is unavailable: {revan_executable}")

    fixture = build_fixture(output_directory / "compact_fixture", geometry=geometry)
    standalone = materializer.materialize(
        record_bundle=fixture["bundle"],
        tape_path=fixture["tape"],
        tape_roots_path=fixture["tape_roots"],
        geometry_path=geometry,
        geometry_sha256=materializer.sha256_file(geometry),
        output_prefix=output_directory / "materialized",
        geometry_classification_path=fixture["classification"],
        _verify_tape_authorities=False,
    )
    sim_path = output_directory / "materialized.standalone/events.sim"
    index_path = output_directory / "materialized.standalone/index.tsv"
    standalone_manifest_path = output_directory / "materialized.standalone/manifest.json"

    environment = os.environ.copy()
    environment["MEGALIB"] = os.fspath(megalib_root)
    roundtrip_command = [os.fspath(consumer), os.fspath(geometry), os.fspath(sim_path), os.fspath(index_path)]
    completed = subprocess.run(
        roundtrip_command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        env=environment,
    )
    roundtrip_log = output_directory / "mfileeventssim_roundtrip.log"
    materializer._durable_write(roundtrip_log, completed.stdout)
    if completed.returncode != 0:
        raise EvidenceError(f"real MFileEventsSim/Revan consumer failed: exit {completed.returncode}")
    roundtrip = _parse_roundtrip(completed.stdout)
    if (
        roundtrip.get("status") != "PASS__REAL_MFILEEVENTSSIM_ROUNDTRIP__REAL_REVAN_INPUT_AND_ANALYZE"
        or roundtrip.get("event_ia_ht_hash_sha256")
        != standalone["mfileeventssim_roundtrip"]["expected_event_ia_ht_hash_sha256"]
    ):
        raise EvidenceError("real round-trip result does not close to materializer expectation")

    revan = revan_zero_transport_gate.run_gate(
        standalone_manifest=standalone_manifest_path,
        revan_executable=revan_executable,
        revan_config=materializer.FROZEN_REVAN_CONFIG,
        output_prefix=output_directory / "revan_consumer",
    )
    if revan.get("status") != revan_zero_transport_gate.PASS_STATUS:
        raise EvidenceError("real Revan CLI attestation did not pass")

    files = {
        "geometry": _binding(geometry),
        "frozen_revan_configuration": _binding(materializer.FROZEN_REVAN_CONFIG),
        "consumer_source": _binding(PACKAGE / "code/mfileeventssim_roundtrip.cc"),
        "consumer_build_helper": _binding(PACKAGE / "code/build_mfileeventssim_roundtrip.py"),
        "consumer_executable": _binding(consumer),
        "consumer_build_manifest": _binding(build_manifest_path),
        "record_bundle": _binding(fixture["bundle"]),
        "eventlist_tape": _binding(fixture["tape"]),
        "tape_root_sidecar": _binding(fixture["tape_roots"]),
        "standalone_sim": _binding(sim_path),
        "standalone_index": _binding(index_path),
        "standalone_manifest": _binding(standalone_manifest_path),
        "mfileeventssim_roundtrip_log": _binding(roundtrip_log),
        "revan_attestation": _binding(output_directory / "revan_consumer.revan/attestation.json"),
        "revan_log": _binding(output_directory / "revan_consumer.revan/revan.log"),
        "revan_tra": _binding(output_directory / "revan_consumer.revan/output.tra"),
        "revan_post_run_configuration": _binding(output_directory / "revan_consumer.revan/revan.cfg"),
    }
    for binding in files.values():
        _assert_binding(binding)

    result = {
        "schema_version": EVIDENCE_VERSION,
        "status": PASS_STATUS,
        "files": files,
        "commands": {
            "mfileeventssim_roundtrip_argv": roundtrip_command,
            "revan_argv": revan["command_argv"],
        },
        "observations": {
            "mfileeventssim_roundtrip": roundtrip,
            "revan": {
                "status": revan["status"],
                "consumer": revan["consumer"],
                "counts": revan["counts"],
            },
        },
        "scope": {
            "fixture_only_not_production_physics": True,
            "representation_and_consumer_gate": True,
            "transport_events_launched": 0,
            "cosima_invoked": False,
            "eventlist_transport_invoked": False,
            "family_clock_semantics": (
                "Per-family/per-mode independent Poisson cell clocks only; not a global seven-family accidental timeline."
            ),
        },
    }
    commit_path = output_directory / "commit.json"
    materializer._durable_write(commit_path, materializer.canonical_json_bytes(result))
    directory_fd = os.open(output_directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = run(args.output_directory)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
