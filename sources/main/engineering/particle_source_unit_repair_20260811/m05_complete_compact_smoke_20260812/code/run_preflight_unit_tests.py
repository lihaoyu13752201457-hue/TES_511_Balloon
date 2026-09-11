#!/usr/bin/env python3
"""Run Python/patch preflight tests and freeze their zero-exit log; no transport."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from preflight_common import PACKAGE, RUN_PACKAGE, canonical_json_bytes, rel, sha256, write_once


LOG = RUN_PACKAGE / "preflight/preflight_unit_tests.log"
EVIDENCE = RUN_PACKAGE / "preflight/preflight_unit_tests.json"
TEST = PACKAGE / "tests/test_preflight.py"
TESTED_RELATIVE_PATHS = (
    "external_sources.json",
    "code/build_preflight.py",
    "code/build_mfileeventssim_roundtrip.py",
    "code/build_preload_observer.py",
    "code/build_shadow.py",
    "code/geometry_classification.py",
    "code/manifest_discovery.py",
    "code/materialize_standalone_sim.py",
    "code/mfileeventssim_roundtrip.cc",
    "code/n1_validation.py",
    "code/preflight_common.py",
    "code/preload_observer/M05GPSPreloadObserver.cc",
    "code/preload_observer/M05ObserverTransaction.hh",
    "code/preload_observer_validation.py",
    "code/record_bundle_validator.py",
    "code/record_validation.py",
    "code/representation_schema.py",
    "code/revan_zero_transport_gate.py",
    "code/rp_validation.py",
    "code/run_standalone_consumer_fixture.py",
    "code/run_preflight_unit_tests.py",
    "code/run_preload_observer_sentinel.py",
    "code/seven_family_projection.py",
    "code/tape_contract.py",
    "code/shadow_extensions/M05CompactScorer.cc",
    "code/shadow_extensions/M05CompactScorer.hh",
    "code/shadow_extensions/M05Cosima.cc",
    "code/shadow_extensions/M05DurableFile.cc",
    "code/shadow_extensions/M05DurableFile.hh",
    "code/shadow_extensions/M05FrozenInput.hh",
    "code/shadow_extensions/M05LifecycleState.hh",
    "code/shadow_extensions/M05NoReplace.hh",
    "code/shadow_extensions/M05VetoPolicy.hh",
    "code/shadow_extensions/Makefile.shadow",
    "patches/m05_shadow_hooks.patch",
    "schema/active_volume_whitelist_v1.json",
    "schema/m05cc_v1.mapping.json",
    "schema/m05cc_v1.schema.json",
    "schema/m05cc_v2.record_schema.json",
    "schema/m05cc_n1_v1.commit_schema.json",
    "schema/preload_generated_observation_v1.schema.json",
    "schema/tape_root_v1.schema.json",
    "schema/transport_authorization_v1.schema.json",
    "config/revan_zero_transport_fixture_v1.cfg",
    "tests/cpp/clhep_unit_golden.cc",
    "tests/cpp/generated_binary64_golden.cc",
    "tests/cpp/source_time_recurrence_golden.cc",
    "tests/cpp/test_durable_file.cc",
    "tests/cpp/test_lifecycle_state.cc",
    "tests/cpp/test_observer_transaction.cc",
    "tests/cpp/test_veto_policy.cc",
    "tests/test_preflight.py",
    "tests/test_n1_validation.py",
    "tests/test_preload_observer.py",
    "tests/test_preload_observer_sentinel.py",
    "tests/test_record_validation.py",
    "tests/test_shadow_feedback02.py",
    "tests/test_standalone_materializer.py",
)

REQUIRED_REAL_CONSUMER_ENV = (
    "M05_MFILE_CONSUMER",
    "M05_TEST_GEOMETRY",
    "M05_REVAN_EXECUTABLE",
)
TESTED_SOURCE_DIRECTORIES = ("code", "schema", "tests", "config", "patches")


def tested_file_manifest() -> list[dict[str, object]]:
    # EXECUTION_STATUS.json is intentionally mutable and is hash-bound by the
    # final preflight after the formal tests; including it here creates a
    # circular stale-evidence dependency when the terminal WAIT is published.
    discovered = {"external_sources.json"}
    for directory in TESTED_SOURCE_DIRECTORIES:
        for path in (PACKAGE / directory).rglob("*"):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                discovered.add(str(path.relative_to(PACKAGE)))
    declared = set(TESTED_RELATIVE_PATHS)
    if discovered != declared:
        raise RuntimeError(
            f"tested source inventory drift: missing={sorted(discovered-declared)}, stale={sorted(declared-discovered)}"
        )
    records = []
    for relative in TESTED_RELATIVE_PATHS:
        path = PACKAGE / relative
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"missing/non-regular tested source: {path}")
        records.append({"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size})
    return records


def main() -> int:
    if LOG.exists() or EVIDENCE.exists():
        raise FileExistsError("write-once preflight unit-test evidence already exists")
    consumer_bindings = {}
    for name in REQUIRED_REAL_CONSUMER_ENV:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"formal test evidence requires {name}; skipped real consumers are forbidden")
        path = Path(value)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"formal real-consumer authority is missing/non-regular/symlink: {name}={path}")
        consumer_bindings[name] = {
            "absolute_path": str(path.resolve()),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
    frozen_revan_config = PACKAGE / "config/revan_zero_transport_fixture_v1.cfg"
    if not frozen_revan_config.is_file() or frozen_revan_config.is_symlink():
        raise FileNotFoundError(f"missing/non-regular frozen Revan configuration: {frozen_revan_config}")
    consumer_bindings["FROZEN_REVAN_CONFIG"] = {
        "absolute_path": str(frozen_revan_config),
        "sha256": sha256(frozen_revan_config),
        "size_bytes": frozen_revan_config.stat().st_size,
    }
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(PACKAGE / "tests"),
        "-p",
        "test_*.py",
        "-v",
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=PACKAGE.parents[2],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        check=False,
    )
    output = completed.stdout or b""
    if completed.returncode != 0 or b"skipped" in output.lower():
        sys.stdout.buffer.write(output)
        raise RuntimeError("preflight unit tests failed/skipped a required real consumer; PASS evidence was not written")
    write_once(LOG, output)
    evidence = {
        "schema_version": 1,
        "status": "PASS__PREFLIGHT_UNIT_TESTS__NO_TRANSPORT",
        "command_argv": command,
        "exit_code": 0,
        "transport_events_launched": 0,
        "test_path": rel(TEST),
        "test_sha256": sha256(TEST),
        "tested_file_manifest": tested_file_manifest(),
        "real_consumer_authorities": consumer_bindings,
        "log_path": rel(LOG),
        "log_sha256": sha256(LOG),
        "log_size_bytes": LOG.stat().st_size,
        "scope": "Python unit tests, manifest/hash validation, and patch dry-run only; no Cosima executable launch",
    }
    write_once(EVIDENCE, canonical_json_bytes(evidence))
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
