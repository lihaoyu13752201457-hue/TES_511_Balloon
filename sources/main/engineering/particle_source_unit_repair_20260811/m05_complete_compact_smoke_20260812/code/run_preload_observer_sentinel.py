#!/usr/bin/env python3
"""Plan or, with separate one-shot authority, run the installed-Cosima sentinel.

The default action is read-only ``--print-plan``.  The execution path is
deliberately unreachable without a canonical, independently issued,
write-once authorization token that binds the exact plan and installed
closure.  This module never creates such a token and never updates the M05
top-level execution status.

The sentinel is a non-mergeable representation/no-perturbation benchmark:
28 geometry/family/mode cells x four frozen shards x the first three
pre-registered controls x baseline/preload = 672 transport events in 224
installed-Cosima invocations.  A pair shares one three-row EventList, root
sidecar, source card, and transport seed.  Shards are ordered AB/BA/AB/BA.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import resource
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from materialize_standalone_sim import (
    OUTPUT_INDEX_COLUMNS,
    TapeRow,
    _load_tape,
    inspect_event,
)
from preflight_common import (
    PACKAGE,
    ROOT,
    RUN_PACKAGE,
    canonical_json_bytes,
    fsync_directory,
    quarantine_directory_no_replace,
    rename_no_replace as _rename_noreplace,
    reject_lexical_symlinks,
    sha256,
    sha256_bytes,
    strict_json,
    strict_json_bytes,
)
from geometry_classification import validate_geometry_classification
from manifest_discovery import load_authority, verify_geometry_bundle
from record_validation import ValidationError as RecordValidationError
from record_validation import _parse_native_dat
from preload_observer_validation import validate_observer_transaction
from tape_contract import SIDECAR_COLUMNS, validate_schema_contract, validate_sidecar


SCHEMA_VERSION = "m05-installed-preload-observer-sentinel-plan-v1"
AUTHORIZATION_SCHEMA = "m05-installed-preload-observer-sentinel-authorization-v1"
AUTHORIZATION_STATUS = "AUTHORIZED__ONE_INSTALLED_PRELOAD_OBSERVER_SENTINEL_ONLY"
BENCHMARK_CLASS = "NON_MERGEABLE_BENCHMARK"
SEED_NAMESPACE = "m05-installed-cosima-preload-observer-sentinel-v1"

PREFLIGHT_ROOT = RUN_PACKAGE / "preflight/transport_preflight_v1"
PLANNED_JOB_MANIFEST = PREFLIGHT_ROOT / "planned_job_manifest.json"
TAPE_PROVENANCE_MANIFEST = PREFLIGHT_ROOT / "tape_provenance_manifest.json"
GEOMETRY_CLASSIFICATION_MANIFEST = PREFLIGHT_ROOT / "geometry_classification_manifest.json"
BENCHMARK_CONTRACT = PACKAGE / "benchmark_contract.json"
OBSERVER_BUILD_MANIFEST = RUN_PACKAGE / "preflight/preload_observer/build_manifest.json"
MFILE_BUILD_ROOT = PACKAGE / "build/nontransport/real_mfileeventssim_roundtrip"
TAPE_SCHEMA = PACKAGE / "schema/tape_root_v1.schema.json"
RECORD_SCHEMA = PACKAGE / "schema/m05cc_v2.record_schema.json"

COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
LIB_COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/lib/libCosima.so")
DEFAULT_OUTPUT_ROOT = RUN_PACKAGE / "sentinel/installed_preload_observer_sentinel_v1"

GEOMETRIES = ("mass_model_511", "s3d_o8")
FAMILIES = ("gamma", "n", "eplus", "eminus", "alpha", "muminus", "muplus")
MODES = ("instant", "buildup")
SHARDS = (0, 1, 2, 3)
PAIR_ARMS = ("baseline", "preload")

EVENTS_PER_ARM = 3
CELL_COUNT = 28
PAIR_COUNT = 112
INVOCATION_COUNT = 224
TRANSPORT_EVENT_COUNT = 672

MAXIMUM_NEW_BYTES = 1 * 1024**3
MINIMUM_LIVE_DISK_RESERVE_BYTES = 20 * 1024**3
MAXIMUM_PROCESS_GROUP_RSS_BYTES = 8 * 1024**3
MAXIMUM_PER_INVOCATION_BYTES = 2_000_000_000
MAXIMUM_WALL_SECONDS = 1800.0
TERMINATE_GRACE_SECONDS = 30.0
MAXIMUM_PRELOAD_RSS_DELTA_BYTES = 64 * 1024**2
OBSERVER_FIXED_BYTES = 4096
OBSERVER_BYTES_PER_EVENT = 256

COSIMA_SHA256 = "3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a"
LIB_COSIMA_SHA256 = "0656a54e0351a72347ad70437a96097b4d37688d10ac9059038e0b697ce6a495"

MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
GEANT4_ROOT = MEGALIB_ROOT / "external/geant4_v10.02.p03"
ROOT_ROOT = MEGALIB_ROOT / "external/root_v6.36.6"
FROZEN_RUNTIME_ENVIRONMENT = {
    "G4ABLADATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4ABLA3.0"),
    "G4ENSDFSTATEDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4ENSDFSTATE1.2.3"),
    "G4LEDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4EMLOW6.48"),
    "G4LEVELGAMMADATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/PhotonEvaporation3.2"),
    "G4NEUTRONHPDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4NDL4.5"),
    "G4NEUTRONXSDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4NEUTRONXS1.4"),
    "G4PIIDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4PII1.3"),
    "G4RADIOACTIVEDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/RadioactiveDecay4.3.2"),
    "G4REALSURFACEDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/RealSurface1.0"),
    "G4SAIDXSDATA": str(GEANT4_ROOT / "share/Geant4-10.2.3/data/G4SAIDDATA1.1"),
    "LD_LIBRARY_PATH": ":".join((str(MEGALIB_ROOT / "lib"), str(GEANT4_ROOT / "lib"), str(ROOT_ROOT / "lib"))),
    "MEGALIB": str(MEGALIB_ROOT),
    "PATH": ":".join((str(MEGALIB_ROOT / "bin"), str(GEANT4_ROOT / "bin"), "/usr/bin")),
    "ROOTSYS": str(ROOT_ROOT),
}
FIXED_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "OMP_NUM_THREADS": "1",
    "ROOT_HIST": "0",
    "TZ": "UTC",
}

OBSERVER_COLUMNS = (
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

HEX64 = re.compile(r"[0-9a-f]{64}")
AUTHORIZATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{7,127}")
RFC3339_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class SentinelError(RuntimeError):
    """A fail-closed sentinel contract or runtime failure."""


def _binding(path: Path) -> dict[str, Any]:
    path = _regular_no_symlink(path)
    return {"absolute_path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def _regular_no_symlink(path: Path) -> Path:
    path = path.absolute()
    reject_lexical_symlinks(path, stop=Path(path.anchor))
    try:
        state = os.lstat(path)
    except FileNotFoundError as exc:
        raise SentinelError(f"missing authority: {path}") from exc
    if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise SentinelError(f"authority is not a single-link regular file: {path}")
    return path


def _read_one_regular_descriptor(path: Path) -> tuple[bytes, str]:
    """Read and hash one immutable pathname identity through one descriptor."""

    path = path.absolute()
    reject_lexical_symlinks(path, stop=Path(path.anchor))
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SentinelError(f"authority is not a single-link regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = (
        before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
        before.st_size, before.st_mtime_ns, before.st_ctime_ns,
    )
    if identity != (
        after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
        after.st_size, after.st_mtime_ns, after.st_ctime_ns,
    ):
        raise SentinelError(f"authority changed while being read: {path}")
    current = os.lstat(path)
    if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1 or (
        current.st_dev, current.st_ino
    ) != (before.st_dev, before.st_ino):
        raise SentinelError(f"authority pathname changed while being read: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise SentinelError(f"authority size changed while being read: {path}")
    return payload, sha256_bytes(payload)


def _directory_no_symlink(path: Path) -> Path:
    path = path.absolute()
    reject_lexical_symlinks(path, stop=Path(path.anchor))
    try:
        state = os.lstat(path)
    except FileNotFoundError as exc:
        raise SentinelError(f"missing directory: {path}") from exc
    if not stat.S_ISDIR(state.st_mode):
        raise SentinelError(f"not a directory: {path}")
    return path


def _canonical_manifest(path: Path) -> dict[str, Any]:
    path = _regular_no_symlink(path)
    value = strict_json(path)
    if not isinstance(value, dict) or path.read_bytes() != canonical_json_bytes(value):
        raise SentinelError(f"manifest is not one canonical JSON object: {path}")
    return value


def _safe_output_root(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts or path.name in {"", ".", ".."}:
        raise SentinelError("unsafe output root")
    reject_lexical_symlinks(path, stop=Path(path.anchor))
    if path.parent.exists():
        _directory_no_symlink(path.parent)
    else:
        # Read-only planning may name one not-yet-created fixed output parent.
        # Execution creates that parent exclusively only after authorization.
        _directory_no_symlink(path.parent.parent)
        if path.parent.name in {"", ".", ".."}:
            raise SentinelError("unsafe missing output parent")
    return path


def _ensure_output_parent(path: Path) -> None:
    """Create at most the single parent permitted by read-only planning."""

    path = path.absolute()
    reject_lexical_symlinks(path, stop=Path(path.anchor))
    if path.exists():
        _directory_no_symlink(path)
        return
    _directory_no_symlink(path.parent)
    try:
        os.mkdir(path, 0o755)
    except FileExistsError:
        _directory_no_symlink(path)
    fsync_directory(path.parent)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o644) -> None:
    reject_lexical_symlinks(path.absolute(), stop=Path(path.anchor))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise OSError("short write")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)


def _fsync_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        state = os.lstat(path)
        if stat.S_ISLNK(state.st_mode):
            raise SentinelError(f"symlink in transaction tree: {path}")
        if stat.S_ISREG(state.st_mode):
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    directories = [path for path in root.rglob("*") if path.is_dir()]
    for path in sorted(directories, key=lambda value: len(value.parts), reverse=True):
        fsync_directory(path)
    fsync_directory(root)


def _tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        state = os.lstat(path)
        if stat.S_ISLNK(state.st_mode):
            raise SentinelError(f"symlink in sentinel output: {path}")
        if stat.S_ISREG(state.st_mode):
            total += state.st_size
    return total


def _disk_anchor(path: Path) -> Path:
    cursor = path.absolute()
    while not cursor.exists():
        if cursor == cursor.parent:
            raise SentinelError(f"no existing disk anchor for {path}")
        cursor = cursor.parent
    _directory_no_symlink(cursor if cursor.is_dir() else cursor.parent)
    return cursor if cursor.is_dir() else cursor.parent


def _resource_gate(
    *,
    roots: Sequence[Path],
    disk_path: Path,
    extra_bytes: int = 0,
    phase: str,
) -> int:
    """Enforce byte and free-space caps before writes/launch and after commit."""

    if extra_bytes < 0:
        raise SentinelError("negative projected resource bytes")
    new_bytes = sum(_tree_bytes(root) for root in roots) + extra_bytes
    if new_bytes > MAXIMUM_NEW_BYTES:
        raise SentinelError(f"{phase}: global new-byte hard cap would be exceeded")
    free = shutil.disk_usage(_disk_anchor(disk_path)).free
    if free - extra_bytes < MINIMUM_LIVE_DISK_RESERVE_BYTES:
        raise SentinelError(f"{phase}: minimum live disk reserve would be violated")
    return new_bytes


def _make_tree_read_only(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        state = os.lstat(path)
        if stat.S_ISLNK(state.st_mode):
            raise SentinelError(f"symlink in input tree: {path}")
        if stat.S_ISREG(state.st_mode):
            os.chmod(path, 0o444)
        elif stat.S_ISDIR(state.st_mode):
            os.chmod(path, 0o555)
    os.chmod(root, 0o555)
    _fsync_tree(root)


def _artifact(path: Path, base: Path) -> dict[str, Any]:
    path = _regular_no_symlink(path)
    try:
        relative = path.relative_to(base)
    except ValueError as exc:
        raise SentinelError(f"artifact is outside transaction: {path}") from exc
    return {"path": str(relative), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def _ldd_closure(binary: Path) -> list[dict[str, Any]]:
    environment = dict(FROZEN_RUNTIME_ENVIRONMENT)
    environment.update(FIXED_ENVIRONMENT)
    completed = subprocess.run(
        ["ldd", str(_regular_no_symlink(binary))],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        env=environment,
    )
    if completed.returncode != 0 or "not found" in completed.stdout:
        raise SentinelError(f"ldd closure failed for {binary}: {completed.stdout}")
    paths: set[Path] = set()
    for line in completed.stdout.splitlines():
        match = re.search(r"=>\s+(/\S+)\s+\(", line) or re.match(r"\s*(/\S+)\s+\(", line)
        if match is not None:
            paths.add(Path(match.group(1)).resolve(strict=True))
    return [_binding(path) for path in sorted(paths, key=str)]


def _discover_mfile_consumer() -> tuple[Path, Path, dict[str, Any]]:
    _directory_no_symlink(MFILE_BUILD_ROOT)
    candidates: list[tuple[Path, Path, dict[str, Any]]] = []
    for manifest_path in sorted(MFILE_BUILD_ROOT.iterdir()):
        if not manifest_path.is_file() or manifest_path.suffix != ".json":
            continue
        manifest = _canonical_manifest(manifest_path)
        if manifest.get("status") != "PASS__REAL_MEGALIB_REVAN_CONSUMER_BUILD__NO_TRANSPORT":
            continue
        binary = _regular_no_symlink(Path(manifest.get("binary_path", "")))
        if manifest.get("binary_sha256") != sha256(binary):
            raise SentinelError("MFileEventsSim consumer binary hash drift")
        candidates.append((binary, manifest_path, manifest))
    if len(candidates) != 1:
        raise SentinelError(f"expected exactly one bound real MFileEventsSim consumer, found {len(candidates)}")
    return candidates[0]


def _extract_seeds(value: Any, key: str | None = None) -> Iterable[int]:
    if key == "seed" and isinstance(value, int) and not isinstance(value, bool):
        yield value
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            yield from _extract_seeds(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _extract_seeds(child, key)


def _registered_seeds(benchmark: Mapping[str, Any], planned: Mapping[str, Any]) -> tuple[set[int], list[dict[str, Any]]]:
    used = set(_extract_seeds(planned))
    authorities = benchmark.get("pairing_contract", {}).get("seed_authorities")
    if not isinstance(authorities, list) or not authorities:
        raise SentinelError("benchmark seed-authority registry is absent")
    bindings: list[dict[str, Any]] = []
    for authority in authorities:
        if not isinstance(authority, Mapping):
            raise SentinelError("malformed seed authority")
        path = ROOT / str(authority.get("path", ""))
        path = _regular_no_symlink(path)
        if sha256(path) != authority.get("sha256"):
            raise SentinelError(f"registered seed authority hash drift: {path}")
        ledger = strict_json(path)
        if not isinstance(ledger, dict):
            raise SentinelError(f"registered seed authority is not a JSON object: {path}")
        seeds = set(_extract_seeds(ledger))
        if not seeds or len(seeds) != authority.get("unique_seed_count"):
            raise SentinelError(f"registered seed closure failed: {path}")
        used.update(seeds)
        bindings.append({
            "authority_id": authority.get("authority_id"),
            "path": str(path),
            "sha256": sha256(path),
            "status": authority.get("status"),
            "unique_seed_count": len(seeds),
        })
    return used, bindings


def _sentinel_seeds(forbidden: set[int]) -> dict[tuple[str, str, int], int]:
    selected: set[int] = set()
    result: dict[tuple[str, str, int], int] = {}
    for family in FAMILIES:
        for mode in MODES:
            for shard in SHARDS:
                nonce = 0
                while True:
                    payload = f"{SEED_NAMESPACE}|{family}|{mode}|{shard}|{nonce}".encode("utf-8")
                    candidate = 100_000_000 + int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 900_000_000
                    if candidate not in forbidden and candidate not in selected:
                        break
                    nonce += 1
                selected.add(candidate)
                result[(family, mode, shard)] = candidate
    if len(result) != 56 or len(selected) != 56:
        raise SentinelError("sentinel seed namespace uniqueness failed")
    return result


def _tsv_rows(data: bytes, expected_header: Sequence[str]) -> list[dict[str, str]]:
    if b"\r" in data or b"\x00" in data or not data.endswith(b"\n"):
        raise SentinelError("TSV is not NUL-free UTF-8/LF/newline-terminated")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SentinelError("TSV is not UTF-8") from exc
    records = list(csv.reader(text.splitlines(), delimiter="\t", strict=True))
    if not records or tuple(records[0]) != tuple(expected_header):
        raise SentinelError("wrong exact TSV header")
    if any(len(row) != len(expected_header) for row in records[1:]):
        raise SentinelError("wrong TSV field count")
    return [dict(zip(expected_header, row, strict=True)) for row in records[1:]]


def _first_three(parent_tape: Path, parent_sidecar: Path) -> tuple[bytes, bytes, list[dict[str, str]]]:
    tape = _regular_no_symlink(parent_tape).read_bytes()
    sidecar = _regular_no_symlink(parent_sidecar).read_bytes()
    if b"\r" in tape or b"\x00" in tape or not tape.endswith(b"\n"):
        raise SentinelError("parent tape lexical contract failed")
    tape_lines = tape.splitlines(keepends=True)
    sidecar_lines = sidecar.splitlines(keepends=True)
    if len(tape_lines) < 3 or len(sidecar_lines) < 4:
        raise SentinelError("parent shard has fewer than three rows")
    derived_tape = b"".join(tape_lines[:3])
    derived_sidecar = sidecar_lines[0] + b"".join(sidecar_lines[1:4])
    rows = _tsv_rows(derived_sidecar, SIDECAR_COLUMNS)
    if len(rows) != 3 or [row["row_index0"] for row in rows] != ["0", "1", "2"]:
        raise SentinelError("derived sentinel rows are not shard rows 0..2")
    if any(row["eventlist_id"] != str(index + 1) or row["control_flag"] != "1" for index, row in enumerate(rows)):
        raise SentinelError("derived sentinel rows are not the three mandatory controls")
    return derived_tape, derived_sidecar, rows


def _geometry_from_card(card: Path) -> Path:
    lines = card.read_text(encoding="utf-8").splitlines()
    values = [line.split(maxsplit=1)[1] for line in lines if line.startswith("Geometry ")]
    if len(values) != 1:
        raise SentinelError(f"source card has no unique Geometry: {card}")
    return _regular_no_symlink(Path(values[0]))


def _geometry_authority_record(bundle: Mapping[str, Any]) -> dict[str, Any]:
    checked = verify_geometry_bundle(dict(bundle))
    files = []
    for row in bundle["files"]:
        path = Path(row["path"])
        authority = path if path.is_absolute() else ROOT / path
        binding = _binding(authority)
        files.append({"ledger_path": row["path"], **binding})
    setup_path = Path(bundle["setup"])
    setup = setup_path if setup_path.is_absolute() else ROOT / setup_path
    return {
        "bundle_sha256": checked["bundle_sha256"],
        "digest_contract": bundle.get("digest_contract"),
        "file_count": checked["file_count"],
        "include_edge_count": checked["include_edge_count"],
        "include_closure_file_count": checked["include_closure_file_count"],
        "setup_ledger_path": bundle["setup"],
        "setup": _binding(setup),
        "files": sorted(files, key=lambda row: row["ledger_path"]),
    }


def _verify_geometry_authority(record: Mapping[str, Any]) -> dict[str, Any]:
    files = record.get("files")
    if not isinstance(files, list) or len(files) != record.get("file_count"):
        raise SentinelError("geometry runtime authority has wrong file count")
    raw = {
        "bundle_sha256": record.get("bundle_sha256"),
        "digest_contract": record.get("digest_contract"),
        "file_count": record.get("file_count"),
        "setup": record.get("setup_ledger_path"),
        "files": [
            {"path": row.get("ledger_path"), "sha256": row.get("sha256")}
            for row in files if isinstance(row, Mapping)
        ],
    }
    checked = verify_geometry_bundle(raw)
    for row in files:
        if not isinstance(row, Mapping):
            raise SentinelError("malformed geometry runtime file binding")
        path = _regular_no_symlink(Path(str(row.get("absolute_path", ""))))
        if path.stat().st_size != row.get("size_bytes") or sha256(path) != row.get("sha256"):
            raise SentinelError(f"geometry runtime file drift: {path}")
    setup = record.get("setup")
    if not isinstance(setup, Mapping):
        raise SentinelError("geometry setup binding is absent")
    setup_path = _regular_no_symlink(Path(str(setup.get("absolute_path", ""))))
    if setup_path.stat().st_size != setup.get("size_bytes") or sha256(setup_path) != setup.get("sha256"):
        raise SentinelError("geometry setup binding drift")
    if checked.get("include_closure_file_count") != record.get("include_closure_file_count"):
        raise SentinelError("geometry Include closure count drift")
    return checked


def _verify_file_binding(binding: Mapping[str, Any], *, label: str) -> Path:
    path = _regular_no_symlink(Path(str(binding.get("absolute_path", ""))))
    if path.stat().st_size != binding.get("size_bytes") or sha256(path) != binding.get("sha256"):
        raise SentinelError(f"{label} binding drift: {path}")
    return path


def _verify_pair_runtime_inputs(
    pair: Mapping[str, Any],
    plan: Mapping[str, Any],
    transaction_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    tape = _verify_file_binding(pair["shared_tape"], label="sentinel tape")
    sidecar = _verify_file_binding(pair["shared_root_sidecar"], label="sentinel root sidecar")
    card = _verify_file_binding(pair["shared_source_card"], label="sentinel source card")
    if tape.parent != sidecar.parent and tape.parent.parent != sidecar.parent.parent:
        raise SentinelError("sentinel tape/sidecar input roots differ")
    geometries = plan.get("authority_bindings", {}).get("geometry_bundles")
    if not isinstance(geometries, Mapping) or pair.get("geometry") not in geometries:
        raise SentinelError("sentinel plan lacks geometry bundle authority")
    geometry = geometries[pair["geometry"]]
    _verify_geometry_authority(geometry)
    setup = _verify_file_binding(geometry["setup"], label="geometry setup")
    if _geometry_from_card(card) != setup:
        raise SentinelError("sentinel source card Geometry differs from pinned bundle setup")
    if pair.get("geometry_bundle_sha256") != geometry.get("bundle_sha256"):
        raise SentinelError("sentinel pair geometry bundle digest drift")
    if transaction_bindings is not None:
        if set(transaction_bindings) != {"input_bundle_commit", "execution_plan"}:
            raise SentinelError("sentinel runtime transaction binding set drift")
        for label, binding in transaction_bindings.items():
            _verify_file_binding(binding, label=label)


def _verify_runtime_authorities(plan: Mapping[str, Any]) -> None:
    """Re-hash every executable/DSO authority before and after each child."""

    bindings = plan.get("authority_bindings")
    if not isinstance(bindings, Mapping):
        raise SentinelError("sentinel plan lacks runtime authority bindings")
    for key in (
        "observer_build_manifest", "observer_binary", "installed_cosima",
        "installed_libCosima", "mfile_consumer_manifest", "mfile_consumer_binary",
    ):
        binding = bindings.get(key)
        if not isinstance(binding, Mapping):
            raise SentinelError(f"sentinel runtime authority is absent: {key}")
        _verify_file_binding(binding, label=key)
    for key in ("installed_cosima_ldd_closure", "mfile_consumer_ldd_closure"):
        closure = bindings.get(key)
        if not isinstance(closure, list) or not closure:
            raise SentinelError(f"sentinel runtime DSO closure is absent: {key}")
        for index, binding in enumerate(closure):
            if not isinstance(binding, Mapping):
                raise SentinelError(f"malformed runtime DSO binding: {key}[{index}]")
            _verify_file_binding(binding, label=f"{key}[{index}]")


def _source_card_bytes(*, geometry: Path, mode: str, tape: Path) -> bytes:
    if mode not in MODES:
        raise SentinelError(f"unknown mode: {mode}")
    lines = [
        "# NON_MERGEABLE_BENCHMARK: installed no-preload/LD_PRELOAD sentinel",
        "# Exactly three pre-registered tape controls; no Spectrum/Flux/Beam source.",
        f"Geometry {geometry}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
    ]
    if mode == "buildup":
        lines.append("DecayMode ActivationBuildUp")
    lines.extend([
        "DetectorTimeConstant 1e-9",
        "StoreTextScientific true 17",
        "PreTriggerMode Everything",
        "",
        "Run M05Sentinel",
        "M05Sentinel.Events 3",
        "M05Sentinel.FileName rich",
        "M05Sentinel.IsotopeProductionFile native",
        "M05Sentinel.Source FrozenPrimary",
        f"FrozenPrimary.EventList {tape}",
        "",
    ])
    result = "\n".join(lines).encode("utf-8")
    forbidden = ("cosima_spectra_dp_2602units", "Spectrum File", ".Spectrum", ".Flux", ".Beam", ".ParticleType")
    if any(token.encode("utf-8") in result for token in forbidden):
        raise SentinelError("sentinel source card contains a forbidden source token")
    return result


def validate_pair_matrix(pairs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    expected = {
        (geometry, family, mode, shard)
        for geometry in GEOMETRIES for family in FAMILIES for mode in MODES for shard in SHARDS
    }
    observed = {
        (pair.get("geometry"), pair.get("family"), pair.get("mode"), pair.get("shard_index"))
        for pair in pairs
    }
    if len(pairs) != PAIR_COUNT or observed != expected:
        raise SentinelError("sentinel 2x7x2x4 pair matrix closure failed")
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            for mode in MODES:
                cell = [
                    pair for pair in pairs
                    if (pair.get("geometry"), pair.get("family"), pair.get("mode")) == (geometry, family, mode)
                ]
                if len(cell) != 4 or {pair.get("shard_index") for pair in cell} != set(SHARDS):
                    raise SentinelError("sentinel cell lacks four distinct shards")
                orders = Counter(tuple(pair.get("arm_order", ())) for pair in cell)
                if orders != Counter({("baseline", "preload"): 2, ("preload", "baseline"): 2}):
                    raise SentinelError("sentinel cell is not balanced two-AB/two-BA")
                if any(pair.get("events_per_arm") != EVENTS_PER_ARM for pair in cell):
                    raise SentinelError("sentinel pair does not use exactly three controls per arm")
    events = len(pairs) * len(PAIR_ARMS) * EVENTS_PER_ARM
    invocations = len(pairs) * len(PAIR_ARMS)
    if events != TRANSPORT_EVENT_COUNT or invocations != INVOCATION_COUNT:
        raise SentinelError("sentinel event/invocation arithmetic failed")
    return {"cells": CELL_COUNT, "pairs": len(pairs), "invocations": invocations, "events": events}


def _frozen_environment_contract() -> dict[str, Any]:
    for key, value in FROZEN_RUNTIME_ENVIRONMENT.items():
        if key.startswith("G4") or key in {"MEGALIB", "ROOTSYS"}:
            _directory_no_symlink(Path(value))
        elif key in {"PATH", "LD_LIBRARY_PATH"}:
            for member in value.split(":"):
                _directory_no_symlink(Path(member))
    frozen = dict(FROZEN_RUNTIME_ENVIRONMENT)
    return {
        "ambient_inheritance": "NONE",
        "frozen_runtime": frozen,
        "frozen_runtime_sha256": sha256_bytes(canonical_json_bytes(frozen)),
        "fixed": FIXED_ENVIRONMENT,
        "baseline_explicitly_unset": ["LD_AUDIT", "LD_PRELOAD"],
        "per_arm_only": ["HOME", "TMPDIR"],
        "preload_only": [
            "LD_PRELOAD",
            "TES511_PRELOAD_ALLOWED_ROOT",
            "TES511_PRELOAD_ARM",
            "TES511_PRELOAD_EXPECTED_LIBCOSIMA",
            "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256",
            "TES511_PRELOAD_OUTPUT_PREFIX",
            "TES511_PRELOAD_TAPE_ROOT_SIDECAR",
            "TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256",
        ],
    }


def _plan_authorities() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    Path, Path, dict[str, Any], dict[str, Any],
]:
    planned = _canonical_manifest(PLANNED_JOB_MANIFEST)
    tape_manifest = _canonical_manifest(TAPE_PROVENANCE_MANIFEST)
    benchmark = _canonical_manifest(BENCHMARK_CONTRACT)
    observer = _canonical_manifest(OBSERVER_BUILD_MANIFEST)
    geometry_classification = _canonical_manifest(GEOMETRY_CLASSIFICATION_MANIFEST)
    try:
        validate_geometry_classification(geometry_classification, verify_canonical_authority=True)
    except ValueError as exc:
        raise SentinelError(f"canonical geometry classification failed: {exc}") from exc
    ledger = load_authority("batch0001")
    bundles = ledger.get("geometry_bundles")
    if not isinstance(bundles, dict) or set(bundles) != set(GEOMETRIES):
        raise SentinelError("canonical geometry bundle set drift")
    geometry_authorities = {
        geometry: _geometry_authority_record(bundles[geometry]) for geometry in GEOMETRIES
    }
    classified = {
        row.get("geometry"): row for row in geometry_classification.get("geometries", [])
        if isinstance(row, Mapping)
    }
    benchmark_bundles = benchmark.get("physics_contract", {}).get("geometry_bundles")
    if set(classified) != set(GEOMETRIES) or not isinstance(benchmark_bundles, Mapping):
        raise SentinelError("geometry authorities are absent from classification/benchmark")
    for geometry in GEOMETRIES:
        authority = geometry_authorities[geometry]
        if (
            classified[geometry].get("geometry_bundle_sha256") != authority["bundle_sha256"]
            or classified[geometry].get("geometry_bundle_files") != bundles[geometry]["files"]
            or benchmark_bundles.get(geometry, {}).get("bundle_sha256") != authority["bundle_sha256"]
            or benchmark_bundles.get(geometry, {}).get("file_count") != authority["file_count"]
        ):
            raise SentinelError(f"geometry authority disagreement: {geometry}")
    if observer.get("status") != "PASS__PRELOAD_OBSERVER_BUILD_ONLY__NOT_EXECUTED":
        raise SentinelError("observer build is not the dormant compile-only PASS")
    observer_binary = _regular_no_symlink(Path(observer.get("binary", {}).get("path", "")))
    if sha256(observer_binary) != observer.get("binary", {}).get("sha256"):
        raise SentinelError("observer binary differs from its build manifest")
    mfile_binary, mfile_manifest_path, _ = _discover_mfile_consumer()
    if sha256(COSIMA) != COSIMA_SHA256 or sha256(LIB_COSIMA) != LIB_COSIMA_SHA256:
        raise SentinelError("installed production Cosima/libCosima drift")
    validate_schema_contract()
    return (
        planned, tape_manifest, benchmark, observer, observer_binary, mfile_binary,
        geometry_classification, geometry_authorities,
    )


def build_plan(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    """Return a deterministic plan envelope; perform no writes and no transport."""

    output_root = _safe_output_root(output_root)
    input_root = Path(str(output_root) + ".inputs")
    (
        planned, tape_manifest, benchmark, observer, observer_binary, mfile_binary,
        geometry_classification, geometry_authorities,
    ) = _plan_authorities()
    used_seeds, seed_authorities = _registered_seeds(benchmark, planned)
    seed_map = _sentinel_seeds(used_seeds)

    tape_cells = tape_manifest.get("cells")
    if not isinstance(tape_cells, list) or len(tape_cells) != 14:
        raise SentinelError("tape provenance does not contain exactly 14 family/mode cells")
    tape_cell_keys: set[tuple[str, str]] = set()
    for cell in tape_cells:
        if not isinstance(cell, Mapping):
            raise SentinelError("malformed tape-provenance cell")
        cell_key = (cell.get("family"), cell.get("mode"))
        if cell_key not in {(family, mode) for family in FAMILIES for mode in MODES} or cell_key in tape_cell_keys:
            raise SentinelError("tape-provenance family/mode identity closure failed")
        tape_cell_keys.add(cell_key)
        drivers = cell.get("driver_bindings")
        shards = cell.get("shards")
        if (
            not isinstance(drivers, list) or len(drivers) != 20
            or {driver.get("bin_index") for driver in drivers if isinstance(driver, Mapping)} != set(range(20))
            or not isinstance(shards, list) or [shard.get("shard_index") for shard in shards] != list(SHARDS)
        ):
            raise SentinelError(f"tape-provenance 20-driver/four-shard closure failed: {cell_key}")

    jobs = planned.get("jobs")
    if not isinstance(jobs, list):
        raise SentinelError("planned job manifest has no job list")
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            raise SentinelError("planned job is not an object")
        key = (job.get("geometry"), job.get("family"), job.get("mode"), job.get("shard_index"))
        if key[0] in GEOMETRIES and key[1] in FAMILIES and key[2] in MODES and key[3] in SHARDS:
            grouped.setdefault(key, []).append(job)
    expected_keys = {
        (geometry, family, mode, shard)
        for geometry in GEOMETRIES for family in FAMILIES for mode in MODES for shard in SHARDS
    }
    if set(grouped) != expected_keys:
        raise SentinelError("planned 2x7x2x4 cell/shard closure failed")

    validated_parent_tapes: set[tuple[Path, Path]] = set()
    derived_by_shard: dict[tuple[str, str, int], dict[str, Any]] = {}
    pairs: list[dict[str, Any]] = []
    geometry_bindings: dict[str, dict[str, Any]] = {}
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            for mode in MODES:
                for shard in SHARDS:
                    key = (geometry, family, mode, shard)
                    group = grouped[key]
                    arms = {job.get("arm"): job for job in group}
                    if set(arms) != {"F", "C", "U", "N1"} or len(group) != 4:
                        raise SentinelError(f"planned four-arm closure failed: {key}")
                    identities = {
                        (
                            job.get("tape_path"), job.get("tape_sha256"),
                            job.get("root_sidecar_path"), job.get("root_sidecar_sha256"),
                        )
                        for job in group
                    }
                    if len(identities) != 1:
                        raise SentinelError(f"planned same-tape closure failed: {key}")
                    reference = arms["F"]
                    geometry_authority = geometry_authorities[geometry]
                    for arm, job in arms.items():
                        source_card = _regular_no_symlink(ROOT / job["source_card_path"])
                        if (
                            source_card.stat().st_size != job["source_card_size_bytes"]
                            or sha256(source_card) != job["source_card_sha256"]
                            or job.get("geometry_bundle_sha256") != geometry_authority["bundle_sha256"]
                            or _geometry_from_card(source_card)
                            != Path(geometry_authority["setup"]["absolute_path"])
                        ):
                            raise SentinelError(f"planned source-card/geometry drift: {key}:{arm}")
                    parent_tape = _regular_no_symlink(ROOT / reference["tape_path"])
                    parent_sidecar = _regular_no_symlink(ROOT / reference["root_sidecar_path"])
                    if sha256(parent_tape) != reference["tape_sha256"] or sha256(parent_sidecar) != reference["root_sidecar_sha256"]:
                        raise SentinelError(f"planned tape hash drift: {key}")
                    parent_key = (parent_tape, parent_sidecar)
                    if parent_key not in validated_parent_tapes:
                        checked = validate_sidecar(parent_tape, parent_sidecar, verify_authorities=True, verify_sampler=True)
                        if checked["event_count"] != reference["events"]:
                            raise SentinelError(f"parent tape event count drift: {key}")
                        validated_parent_tapes.add(parent_key)
                    derived_tape, derived_sidecar, rows = _first_three(parent_tape, parent_sidecar)
                    shard_key = (family, mode, shard)
                    tape_relative = Path("tapes") / f"{family}_{mode}" / f"shard{shard:04d}.eventlist"
                    sidecar_relative = Path("tapes") / f"{family}_{mode}" / f"shard{shard:04d}.roots.tsv"
                    derived = {
                        "parent_tape": _binding(parent_tape),
                        "parent_root_sidecar": _binding(parent_sidecar),
                        "tape": {
                            "path": str(tape_relative),
                            "absolute_path": str(input_root / tape_relative),
                            "sha256": sha256_bytes(derived_tape),
                            "size_bytes": len(derived_tape),
                        },
                        "root_sidecar": {
                            "path": str(sidecar_relative),
                            "absolute_path": str(input_root / sidecar_relative),
                            "sha256": sha256_bytes(derived_sidecar),
                            "size_bytes": len(derived_sidecar),
                        },
                        "stable_root_ids": [row["stable_root_id"] for row in rows],
                        "driver_bin_bindings": [
                            {
                                "driver": row["driver"], "bin_index": int(row["bin_index"]),
                                "spectrum_sha256": row["spectrum_sha256"],
                            }
                            for row in rows
                        ],
                    }
                    if shard_key in derived_by_shard and derived_by_shard[shard_key] != derived:
                        raise SentinelError("cross-geometry derived tape differs")
                    derived_by_shard[shard_key] = derived

                    original_card = _regular_no_symlink(ROOT / reference["source_card_path"])
                    geometry_path = Path(geometry_authority["setup"]["absolute_path"])
                    geometry_binding = {
                        "setup": geometry_authority["setup"],
                        "bundle_sha256": geometry_authority["bundle_sha256"],
                    }
                    if geometry in geometry_bindings and geometry_bindings[geometry] != geometry_binding:
                        raise SentinelError(f"geometry binding differs across cells: {geometry}")
                    geometry_bindings[geometry] = geometry_binding
                    pair_id = f"{geometry}__{family}_{mode}__s{shard:04d}"
                    card_relative = Path("cards") / geometry / f"{pair_id}.source"
                    card_bytes = _source_card_bytes(
                        geometry=geometry_path,
                        mode=mode,
                        tape=Path(derived["tape"]["absolute_path"]),
                    )
                    order = ["baseline", "preload"] if shard % 2 == 0 else ["preload", "baseline"]
                    seed = seed_map[shard_key]
                    argv = [str(COSIMA), "-z", "-s", str(seed), str(input_root / card_relative)]
                    pairs.append({
                        "pair_id": pair_id,
                        "cell_id": f"{geometry}__{family}_{mode}",
                        "geometry": geometry,
                        "geometry_setup": geometry_binding["setup"],
                        "geometry_bundle_sha256": geometry_binding["bundle_sha256"],
                        "family": family,
                        "mode": mode,
                        "shard_index": shard,
                        "arm_order": order,
                        "events_per_arm": EVENTS_PER_ARM,
                        "transport_seed": seed,
                        "seed_namespace": SEED_NAMESPACE,
                        "shared_tape": derived["tape"],
                        "shared_root_sidecar": derived["root_sidecar"],
                        "parent_tape": derived["parent_tape"],
                        "parent_root_sidecar": derived["parent_root_sidecar"],
                        "stable_root_ids": derived["stable_root_ids"],
                        "sampled_driver_bin_bindings": derived["driver_bin_bindings"],
                        "all_20_driver_empirical_coverage_claim": False,
                        "shared_source_card": {
                            "path": str(card_relative),
                            "absolute_path": str(input_root / card_relative),
                            "sha256": sha256_bytes(card_bytes),
                            "size_bytes": len(card_bytes),
                        },
                        "baseline_command_argv": argv,
                        "preload_command_argv": argv,
                    })

    validate_pair_matrix(pairs)

    mfile_binary, mfile_manifest_path, _ = _discover_mfile_consumer()
    authority_bindings = {
        "harness": _binding(Path(__file__)),
        "planned_job_manifest": _binding(PLANNED_JOB_MANIFEST),
        "tape_provenance_manifest": _binding(TAPE_PROVENANCE_MANIFEST),
        "benchmark_contract": _binding(BENCHMARK_CONTRACT),
        "observer_build_manifest": _binding(OBSERVER_BUILD_MANIFEST),
        "observer_binary": _binding(observer_binary),
        "geometry_classification_manifest": _binding(GEOMETRY_CLASSIFICATION_MANIFEST),
        "geometry_classification_semantics_sha256": sha256_bytes(
            canonical_json_bytes(geometry_classification)
        ),
        "geometry_bundles": geometry_authorities,
        "installed_cosima": _binding(COSIMA),
        "installed_libCosima": _binding(LIB_COSIMA),
        "installed_cosima_ldd_closure": _ldd_closure(COSIMA),
        "mfile_consumer_manifest": _binding(mfile_manifest_path),
        "mfile_consumer_binary": _binding(mfile_binary),
        "mfile_consumer_ldd_closure": _ldd_closure(mfile_binary),
        "tape_schema": _binding(TAPE_SCHEMA),
        "record_schema": _binding(RECORD_SCHEMA),
        "tape_contract_code": _binding(PACKAGE / "code/tape_contract.py"),
        "materializer_code": _binding(PACKAGE / "code/materialize_standalone_sim.py"),
        "record_validation_code": _binding(PACKAGE / "code/record_validation.py"),
        "geometry_classification_code": _binding(PACKAGE / "code/geometry_classification.py"),
        "manifest_discovery_code": _binding(PACKAGE / "code/manifest_discovery.py"),
        "preload_observer_validation_code": _binding(PACKAGE / "code/preload_observer_validation.py"),
        "preload_observer_schema": _binding(PACKAGE / "schema/preload_generated_observation_v1.schema.json"),
        "seed_registry_authorities": seed_authorities,
    }
    plan = {
        "schema_version": SCHEMA_VERSION,
        "status": "PLAN_ONLY__NO_TRANSPORT_AUTHORITY",
        "benchmark_class": BENCHMARK_CLASS,
        "merge_eligible": False,
        "transport_authorized": False,
        "transport_events_launched": 0,
        "output_root": str(output_root),
        "input_bundle_root": str(input_root),
        "shape": {
            "geometry_count": 2,
            "family_count": 7,
            "mode_count": 2,
            "cell_count": CELL_COUNT,
            "shards_per_cell": 4,
            "controls_per_shard": 3,
            "arms_per_pair": 2,
            "pair_count": PAIR_COUNT,
            "installed_cosima_invocation_count": INVOCATION_COUNT,
            "transport_event_count": TRANSPORT_EVENT_COUNT,
            "events_per_arm": EVENTS_PER_ARM,
            "arm_order": "shards 0/2 AB; shards 1/3 BA; exactly two AB and two BA in every cell",
        },
        "seed_contract": {
            "namespace": SEED_NAMESPACE,
            "unique_seed_count": 56,
            "same_seed_scope": "baseline/preload pair and matched cross-geometry family/mode/shard",
            "forbidden_reuse": "sentinel seeds are disjoint from registered transport and planned full-smoke seeds; full smoke must not reuse sentinel seeds",
            "derivation": "nine-digit SHA256(namespace|family|mode|shard|nonce), nonce incremented on collision",
            "seeds": [
                {"family": family, "mode": mode, "shard_index": shard, "seed": seed_map[(family, mode, shard)]}
                for family in FAMILIES for mode in MODES for shard in SHARDS
            ],
        },
        "source_time_scope": {
            "clock_scope": "independent_per_family_mode_cell",
            "all_20_driver_definitions_hash_bound": True,
            "empirical_all_20_bin_coverage_claim": False,
            "cross_family_prohibition": "the seven independently sampled family clocks are not one global accidental/live-time timeline",
        },
        "environment_contract": _frozen_environment_contract(),
        "resource_contract": {
            "scheduler": "one installed-Cosima process at a time; each child starts a new process group",
            "maximum_new_bytes": MAXIMUM_NEW_BYTES,
            "minimum_live_disk_reserve_bytes": MINIMUM_LIVE_DISK_RESERVE_BYTES,
            "maximum_process_group_rss_bytes": MAXIMUM_PROCESS_GROUP_RSS_BYTES,
            "maximum_per_invocation_bytes": MAXIMUM_PER_INVOCATION_BYTES,
            "maximum_wall_seconds_per_invocation": MAXIMUM_WALL_SECONDS,
            "terminate_grace_seconds": TERMINATE_GRACE_SECONDS,
            "maximum_preload_peak_rss_delta_bytes": MAXIMUM_PRELOAD_RSS_DELTA_BYTES,
            "observer_maximum_bytes": f"{OBSERVER_FIXED_BYTES}+{OBSERVER_BYTES_PER_EVENT}*events",
            "aggregate_overhead_gate": "preload-baseline wall and OS CPU <= max(60 seconds, 5 percent of baseline aggregate)",
        },
        "validation_contract": {
            "shared_input": "pair arms use byte-identical EventList, 40-column root sidecar, source card, seed, geometry and argv",
            "observer": "all three rows join in exact order to SIDECAR_COLUMNS; IDs/root/particle/count and generated binary64 hashes exact; field tolerances match M05",
            "rich_sim": "Type SIM/Version 101/Geometry/Seed/3 SE-ID-TI/one INIT; IA/HT strict; only Date is canonicalized before byte-exact pair comparison",
            "native_dat": "exactly one native DAT per arm; raw bytes exact between pair; strict positive TT/VN/RP/EN parse",
            "mfileeventssim": "both rich SIM files must pass the bound real installed MFileEventsSim consumer",
            "logs": "stderr byte exact; stdout byte exact after only preregistered timing-line normalization; observer emits no successful output",
            "rng": "baseline explicitly unsets LD_PRELOAD/LD_AUDIT; preload adds only bound observer variables; observer build RNG scans remain PASS",
            "authority": "arm receipts, then pair receipts, then one top commit; fsync and atomic no-replace directory publication",
        },
        "authority_bindings": authority_bindings,
        "authorization_contract": {
            "default_action": "print-plan only",
            "token_created_by_harness": False,
            "token_schema": AUTHORIZATION_SCHEMA,
            "token_status": AUTHORIZATION_STATUS,
            "token_must_be_canonical_single_link_regular_file": True,
            "token_consumption": "O_EXCL write-once sibling receipt before first installed-Cosima process; any attempted reuse fails",
            "scope": "this 672-event sentinel only; never full smoke or M05_COMPLETE authority",
            "second_full_smoke_authorization_required_after_pass": True,
        },
        "pairs": pairs,
    }
    envelope = {"plan": plan, "plan_sha256": sha256_bytes(canonical_json_bytes(plan))}
    if len(pairs) * 2 * EVENTS_PER_ARM != TRANSPORT_EVENT_COUNT:
        raise SentinelError("transport event arithmetic failed")
    return envelope


def authorization_expected(envelope: Mapping[str, Any]) -> dict[str, Any]:
    plan = envelope["plan"]
    bindings = plan["authority_bindings"]
    return {
        "benchmark_class": BENCHMARK_CLASS,
        "cosima_sha256": bindings["installed_cosima"]["sha256"],
        "full_smoke_authorized": False,
        "harness_sha256": bindings["harness"]["sha256"],
        "installed_cosima_invocation_limit": INVOCATION_COUNT,
        "mfile_consumer_sha256": bindings["mfile_consumer_binary"]["sha256"],
        "observer_binary_sha256": bindings["observer_binary"]["sha256"],
        "observer_build_manifest_sha256": bindings["observer_build_manifest"]["sha256"],
        "output_root": plan["output_root"],
        "plan_sha256": envelope["plan_sha256"],
        "planned_job_manifest_sha256": bindings["planned_job_manifest"]["sha256"],
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": AUTHORIZATION_STATUS,
        "tape_provenance_manifest_sha256": bindings["tape_provenance_manifest"]["sha256"],
        "transport_event_limit": TRANSPORT_EVENT_COUNT,
    }


def validate_authorization_document(document: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    expected = authorization_expected(envelope)
    extra_keys = {"authorization_id", "independent_reviewer", "issued_utc", "one_time"}
    if set(document) != set(expected) | extra_keys:
        raise SentinelError("authorization token exact-key closure failed")
    for key, value in expected.items():
        if document.get(key) != value:
            raise SentinelError(f"authorization token binding mismatch: {key}")
    authorization_id = document.get("authorization_id")
    reviewer = document.get("independent_reviewer")
    issued = document.get("issued_utc")
    if not isinstance(authorization_id, str) or AUTHORIZATION_ID.fullmatch(authorization_id) is None:
        raise SentinelError("authorization_id is malformed")
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 3 or reviewer.strip().lower() in {"self", "harness"}:
        raise SentinelError("independent reviewer identity is absent")
    if not isinstance(issued, str) or RFC3339_UTC.fullmatch(issued) is None:
        raise SentinelError("authorization issued_utc is not canonical UTC")
    if document.get("one_time") is not True:
        raise SentinelError("authorization is not explicitly one-time")
    return dict(document)


def verify_authorization_token(path: Path, envelope: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    path = path.absolute()
    payload, token_sha256 = _read_one_regular_descriptor(path)
    document = strict_json_bytes(payload, source=str(path))
    if not isinstance(document, dict) or payload != canonical_json_bytes(document):
        raise SentinelError("authorization token is not one canonical JSON object")
    validated = validate_authorization_document(document, envelope)
    consumed = path.with_name(path.name + ".consumed.json")
    reject_lexical_symlinks(consumed.absolute(), stop=Path(consumed.anchor))
    if consumed.exists():
        raise SentinelError(f"authorization token already consumed: {consumed}")
    return validated, token_sha256


def _reconstruct_derived(pair: Mapping[str, Any]) -> tuple[bytes, bytes]:
    parent_tape = Path(pair["parent_tape"]["absolute_path"])
    parent_sidecar = Path(pair["parent_root_sidecar"]["absolute_path"])
    if sha256(parent_tape) != pair["parent_tape"]["sha256"] or sha256(parent_sidecar) != pair["parent_root_sidecar"]["sha256"]:
        raise SentinelError("parent tape changed after plan")
    tape, sidecar, _ = _first_three(parent_tape, parent_sidecar)
    if sha256_bytes(tape) != pair["shared_tape"]["sha256"] or sha256_bytes(sidecar) != pair["shared_root_sidecar"]["sha256"]:
        raise SentinelError("derived sentinel tape changed after plan")
    return tape, sidecar


def prepare_input_bundle(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Publish the deterministic, no-transport three-row inputs write-once."""

    plan = envelope["plan"]
    target = Path(plan["input_bundle_root"])
    _directory_no_symlink(target.parent)
    _resource_gate(roots=(), disk_path=target.parent, phase="before sentinel input write")
    partial = target.with_name(f".{target.name}.partial.inputs.{os.getpid()}")
    if target.exists() or partial.exists():
        raise FileExistsError(f"sentinel input publication target exists: {target} / {partial}")
    derived_payloads: dict[str, tuple[str, bytes, bytes]] = {}
    card_payloads: list[tuple[str, bytes]] = []
    card_paths: set[str] = set()
    for pair in plan["pairs"]:
        tape, sidecar = _reconstruct_derived(pair)
        tape_relative = pair["shared_tape"]["path"]
        sidecar_relative = pair["shared_root_sidecar"]["path"]
        payload = (sidecar_relative, tape, sidecar)
        if tape_relative in derived_payloads and derived_payloads[tape_relative] != payload:
            raise SentinelError("same sentinel tape path resolves to different bytes")
        derived_payloads[tape_relative] = payload
        card_relative = pair["shared_source_card"]["path"]
        if card_relative in card_paths:
            raise SentinelError("duplicate sentinel source-card path")
        card_paths.add(card_relative)
        card_bytes = _source_card_bytes(
            geometry=Path(pair["geometry_setup"]["absolute_path"]),
            mode=pair["mode"],
            tape=Path(pair["shared_tape"]["absolute_path"]),
        )
        if sha256_bytes(card_bytes) != pair["shared_source_card"]["sha256"]:
            raise SentinelError("sentinel source-card content differs from plan")
        card_payloads.append((card_relative, card_bytes))
    projected_payload_bytes = sum(
        len(tape) + len(sidecar) for _, tape, sidecar in derived_payloads.values()
    ) + sum(len(payload) for _, payload in card_payloads)
    _resource_gate(
        roots=(), disk_path=target.parent, extra_bytes=projected_payload_bytes,
        phase="before any sentinel input publication write",
    )
    tape_bindings: dict[str, dict[str, Any]] = {}
    card_bindings: list[dict[str, Any]] = []
    published = False
    partial_owned = False
    try:
        partial.mkdir(mode=0o755)
        partial_owned = True
        fsync_directory(target.parent)
        for tape_relative in sorted(derived_payloads):
            sidecar_relative, tape, sidecar = derived_payloads[tape_relative]
            tape_path = partial / tape_relative
            sidecar_path = partial / sidecar_relative
            _resource_gate(
                roots=(partial,), disk_path=target.parent, extra_bytes=len(tape),
                phase="before sentinel tape write",
            )
            _write_exclusive(tape_path, tape)
            _resource_gate(
                roots=(partial,), disk_path=target.parent, extra_bytes=len(sidecar),
                phase="before sentinel sidecar write",
            )
            _write_exclusive(sidecar_path, sidecar)
            checked = validate_sidecar(tape_path, sidecar_path, verify_authorities=True, verify_sampler=True)
            if checked["event_count"] != 3:
                raise SentinelError("published sentinel tape is not exactly three rows")
            tape_bindings[tape_relative] = {
                "tape": _artifact(tape_path, partial),
                "root_sidecar": _artifact(sidecar_path, partial),
                "validation": checked,
            }
        for card_relative, card_bytes in card_payloads:
            card_path = partial / card_relative
            _resource_gate(
                roots=(partial,), disk_path=target.parent, extra_bytes=len(card_bytes),
                phase="before sentinel card write",
            )
            _write_exclusive(card_path, card_bytes)
            card_bindings.append(_artifact(card_path, partial))
        manifest = {
            "schema_version": "m05-installed-preload-observer-sentinel-input-bundle-v1",
            "status": "PASS__WRITE_ONCE_SENTINEL_INPUTS__NO_TRANSPORT",
            "transport_events_launched": 0,
            "plan_sha256": envelope["plan_sha256"],
            "tapes": [tape_bindings[key] for key in sorted(tape_bindings)],
            "cards": sorted(card_bindings, key=lambda row: row["path"]),
        }
        commit_payload = canonical_json_bytes(manifest)
        _resource_gate(
            roots=(partial,), disk_path=target.parent, extra_bytes=len(commit_payload),
            phase="before sentinel input commit",
        )
        _write_exclusive(partial / "input_bundle.commit.json", commit_payload)
        commit_binding = {
            "absolute_path": str(target / "input_bundle.commit.json"),
            "sha256": sha256_bytes(commit_payload),
            "size_bytes": len(commit_payload),
        }
        _make_tree_read_only(partial)
        _resource_gate(roots=(partial,), disk_path=target.parent, phase="before sentinel input publication")
        _rename_noreplace(partial, target)
        published = True
        partial_owned = False
        fsync_directory(target.parent)
        _resource_gate(roots=(target,), disk_path=target.parent, phase="after sentinel input publication")
        return {**manifest, "commit": commit_binding}
    except BaseException as exc:
        # A namespace published before a failed parent fsync is never allowed
        # to remain at the authoritative target.  A collision never moves the
        # foreign target because ``published`` is set only after our rename.
        try:
            if published:
                quarantine_directory_no_replace(target)
            elif partial_owned:
                quarantine_directory_no_replace(partial)
        except BaseException as quarantine_error:
            raise SentinelError(
                f"sentinel input publication failed ({exc}); quarantine failed ({quarantine_error})"
            ) from exc
        raise


def _base_environment(plan: Mapping[str, Any]) -> dict[str, str]:
    contract = plan["environment_contract"]
    if contract.get("ambient_inheritance") != "NONE":
        raise SentinelError("sentinel runtime environment permits ambient inheritance")
    frozen = contract.get("frozen_runtime")
    if not isinstance(frozen, dict) or frozen != FROZEN_RUNTIME_ENVIRONMENT:
        raise SentinelError("frozen runtime environment differs from harness authority")
    if sha256_bytes(canonical_json_bytes(frozen)) != contract.get("frozen_runtime_sha256"):
        raise SentinelError("frozen runtime environment digest drift")
    result = dict(frozen)
    result.update(contract["fixed"])
    result.pop("LD_PRELOAD", None)
    result.pop("LD_AUDIT", None)
    return result


def _proc_group_sample(pgid: int) -> tuple[int, int, int, set[str]]:
    rss = 0
    read_bytes = 0
    write_bytes = 0
    maps: set[str] = set()
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat_text = (entry / "stat").read_text(encoding="utf-8")
            closing = stat_text.rfind(")")
            fields = stat_text[closing + 2:].split()
            if closing < 0 or len(fields) < 3 or int(fields[2]) != pgid:
                continue
            status = (entry / "status").read_text(encoding="utf-8")
            match = re.search(r"^VmRSS:\s+([0-9]+)\s+kB$", status, re.MULTILINE)
            if match:
                rss += int(match.group(1)) * 1024
            io_text = (entry / "io").read_text(encoding="utf-8")
            read_match = re.search(r"^read_bytes:\s+([0-9]+)$", io_text, re.MULTILINE)
            write_match = re.search(r"^write_bytes:\s+([0-9]+)$", io_text, re.MULTILINE)
            read_bytes += int(read_match.group(1)) if read_match else 0
            write_bytes += int(write_match.group(1)) if write_match else 0
            if int(entry.name) == pgid:
                for line in (entry / "maps").read_text(encoding="utf-8").splitlines():
                    pieces = line.split(maxsplit=5)
                    if len(pieces) == 6 and pieces[5].startswith("/"):
                        if pieces[5].endswith(" (deleted)"):
                            raise SentinelError("deleted mapped file in installed process")
                        maps.add(str(Path(pieces[5]).resolve(strict=True)))
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
    return rss, read_bytes, write_bytes, maps


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _run_supervised(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
    stage_root: Path,
    input_root: Path,
    expected_executable_sha256: str,
    input_validator: Callable[[], None],
) -> dict[str, Any]:
    executable = _regular_no_symlink(Path(argv[0]))
    if sha256(executable) != expected_executable_sha256:
        raise SentinelError(f"executable hash drift immediately before launch: {executable}")
    _resource_gate(
        roots=(stage_root, input_root), disk_path=stage_root.parent,
        phase="immediately before child launch",
    )
    input_validator()
    before_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start_ns = time.monotonic_ns()
    peak_rss = 0
    peak_read = 0
    peak_write = 0
    mapped_paths: set[str] = set()
    gate_failure: str | None = None
    process: subprocess.Popen[bytes] | None = None
    def child_limits() -> None:
        # subprocess creates the new session after this callback; this callback
        # only establishes a kernel-enforced per-file cap inherited by every
        # descendant in the process group.
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAXIMUM_PER_INVOCATION_BYTES, MAXIMUM_PER_INVOCATION_BYTES))

    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                preexec_fn=child_limits,
            )
            while process.poll() is None:
                rss, read_bytes, write_bytes, maps = _proc_group_sample(process.pid)
                peak_rss = max(peak_rss, rss)
                peak_read = max(peak_read, read_bytes)
                peak_write = max(peak_write, write_bytes)
                mapped_paths.update(maps)
                wall_s = (time.monotonic_ns() - start_ns) / 1e9
                new_bytes = _tree_bytes(stage_root) + _tree_bytes(input_root)
                invocation_bytes = _tree_bytes(cwd)
                disk_free = shutil.disk_usage(stage_root.parent).free
                if wall_s > MAXIMUM_WALL_SECONDS:
                    gate_failure = "wall_timeout"
                elif peak_rss > MAXIMUM_PROCESS_GROUP_RSS_BYTES:
                    gate_failure = "process_group_rss"
                elif invocation_bytes > MAXIMUM_PER_INVOCATION_BYTES:
                    gate_failure = "per_invocation_bytes"
                elif new_bytes > MAXIMUM_NEW_BYTES:
                    gate_failure = "global_new_bytes"
                elif disk_free < MINIMUM_LIVE_DISK_RESERVE_BYTES:
                    gate_failure = "minimum_live_disk_reserve"
                if gate_failure is not None:
                    _terminate_group(process)
                    break
                time.sleep(0.1)
            returncode = process.wait()
    except BaseException:
        if process is not None:
            _terminate_group(process)
            process.wait()
        raise
    end_ns = time.monotonic_ns()
    after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    if gate_failure is not None:
        raise SentinelError(f"process resource gate failed: {gate_failure}")
    if returncode != 0:
        raise SentinelError(f"process exited nonzero: {argv[0]}: {returncode}")
    input_validator()
    _resource_gate(
        roots=(stage_root, input_root), disk_path=stage_root.parent,
        phase="immediately after child exit",
    )
    if not mapped_paths:
        raise SentinelError("no runtime /proc maps attestation was captured")
    maps_path = cwd / "runtime_maps.paths"
    _write_exclusive(maps_path, ("\n".join(sorted(mapped_paths)) + "\n").encode("utf-8"))
    return {
        "command_argv": list(argv),
        "exit_code": returncode,
        "wall_monotonic_ns": end_ns - start_ns,
        "wall_s": (end_ns - start_ns) / 1e9,
        "cpu_user_s": after_usage.ru_utime - before_usage.ru_utime,
        "cpu_system_s": after_usage.ru_stime - before_usage.ru_stime,
        "peak_process_group_rss_bytes": peak_rss,
        "read_bytes": peak_read,
        "write_bytes": peak_write,
        "stdout": _artifact(stdout_path, stage_root),
        "stderr": _artifact(stderr_path, stage_root),
        "runtime_maps": _artifact(maps_path, stage_root),
        "runtime_mapped_paths": sorted(mapped_paths),
    }


def _discover_one(root: Path, suffix: str) -> Path:
    matches: list[Path] = []
    for path in root.iterdir():
        state = os.lstat(path)
        if stat.S_ISLNK(state.st_mode):
            raise SentinelError(f"symlink output is forbidden: {path}")
        if stat.S_ISREG(state.st_mode) and path.name.endswith(suffix):
            matches.append(path)
    if len(matches) != 1:
        raise SentinelError(f"expected exactly one {suffix} output in {root}, found {len(matches)}")
    return matches[0]


def _read_sim(path: Path) -> bytes:
    path = _regular_no_symlink(path)
    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            data = handle.read(MAXIMUM_PER_INVOCATION_BYTES + 1)
    else:
        data = path.read_bytes()
    if len(data) > MAXIMUM_PER_INVOCATION_BYTES:
        raise SentinelError("decompressed SIM exceeds per-invocation byte cap")
    if b"\r" in data or b"\x00" in data:
        raise SentinelError("rich SIM is not NUL-free LF text")
    return data


def canonicalize_rich_sim_date(data: bytes) -> bytes:
    matches = list(re.finditer(br"(?m)^Date[ \t]+[^\n]*\n", data))
    if len(matches) != 1:
        raise SentinelError(f"rich SIM has {len(matches)} Date records, expected one")
    match = matches[0]
    return data[:match.start()] + b"Date       <VOLATILE>\n" + data[match.end():]


def _record_counts(fragment: bytes) -> dict[str, int]:
    text = fragment.decode("utf-8")
    counts: Counter[str] = Counter()
    for line in text.splitlines():
        for record in ("ED", "EC", "NS", "PM", "CC", "IA"):
            if line == record or line.startswith(record + " "):
                counts[record] += 1
        if line.startswith("HT"):
            counts["HT"] += 1
    return {key: counts[key] for key in ("ED", "EC", "NS", "PM", "CC", "IA", "HT")}


def validate_rich_sim(path: Path, *, geometry: Path, seed: int, tape_rows: Sequence[TapeRow]) -> dict[str, Any]:
    data = _read_sim(path)
    canonical = canonicalize_rich_sim_date(data)
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    exact_headers = {
        "Type": [line.strip() for line in lines if line.startswith("Type")],
        "Version": [line.strip() for line in lines if line.startswith("Version")],
        "Geometry": [line.strip() for line in lines if line.startswith("Geometry")],
        "Seed": [line.strip() for line in lines if line.startswith("Seed")],
    }
    if exact_headers["Type"] != ["Type       SIM"]:
        raise SentinelError("rich SIM Type is not exactly SIM")
    if exact_headers["Version"] != ["Version    101"]:
        raise SentinelError("rich SIM Version is not 101")
    if exact_headers["Geometry"] != [f"Geometry   {geometry}"]:
        raise SentinelError("rich SIM Geometry differs from bound geometry")
    if exact_headers["Seed"] != [f"Seed       {seed}"]:
        raise SentinelError("rich SIM Seed differs from pair seed")
    if sum(line.strip() == "EN" for line in lines) != 1:
        raise SentinelError("rich SIM does not contain exactly one EN")
    te = [line.strip().split() for line in lines if line.startswith("TE ")]
    ts = [line.strip().split() for line in lines if line.startswith("TS ")]
    if len(te) != 1 or len(te[0]) != 2 or not math.isfinite(float(te[0][1])):
        raise SentinelError("rich SIM TE closure failed")
    if ts != [["TS", str(len(tape_rows))]]:
        raise SentinelError("rich SIM TS differs from sentinel event count")

    starts = [index for index, line in enumerate(lines) if line == "SE\n"]
    if len(starts) != len(tape_rows):
        raise SentinelError("rich SIM SE count differs from sentinel tape")
    en_index = next(index for index, line in enumerate(lines) if line.strip() == "EN")
    event_rows: list[dict[str, Any]] = []
    totals = Counter()
    fragments: list[bytes] = []
    for ordinal, start in enumerate(starts):
        end = starts[ordinal + 1] if ordinal + 1 < len(starts) else en_index
        fragment = "".join(lines[start:end]).encode("utf-8")
        while fragment.endswith(b"\n\n"):
            fragment = fragment[:-1]
        summary = inspect_event(fragment, tape_rows[ordinal])
        if summary.event_id != ordinal + 1 or summary.started_id != ordinal + 1:
            raise SentinelError("rich SIM ID/started-ID order differs from tape")
        counts = _record_counts(fragment)
        if counts["IA"] != summary.ia_count or counts["HT"] != summary.ht_count:
            raise SentinelError("rich SIM record count differs from strict event parser")
        totals.update(counts)
        digest = sha256_bytes(fragment)
        fragments.append(fragment)
        event_rows.append({
            "event_id": ordinal + 1,
            "event_sha256": digest,
            "event_size_bytes": len(fragment),
            "ia_count": summary.ia_count,
            "ht_count": summary.ht_count,
            "serialized_ia_quantized_sha256": summary.serialized_ia_tuple_sha256,
            "record_counts": counts,
        })
    return {
        "path": str(path),
        "compressed_sha256": sha256(path),
        "compressed_size_bytes": path.stat().st_size,
        "decompressed_sha256": sha256_bytes(data),
        "decompressed_size_bytes": len(data),
        "canonical_date_only_sha256": sha256_bytes(canonical),
        "canonical_bytes": canonical,
        "event_count": len(event_rows),
        "ia_count": sum(row["ia_count"] for row in event_rows),
        "ht_count": sum(row["ht_count"] for row in event_rows),
        "record_counts": {key: totals[key] for key in ("ED", "EC", "NS", "PM", "CC", "IA", "HT")},
        "TE_s": float(te[0][1]),
        "TS": int(ts[0][1]),
        "events": event_rows,
        "fragments": fragments,
    }


def _observer_binary64_hash(values: Sequence[float], particle: int) -> str:
    if len(values) != 12 or not all(math.isfinite(value) for value in values):
        raise SentinelError("observer binary64 tuple is malformed")
    payload = b"m05-eventlist-binary64-v1\0" + struct.pack(">i12d", particle, *values)
    return sha256_bytes(payload)


def _near(observed: float, expected: float, *, absolute: float, relative: float) -> bool:
    return math.isclose(observed, expected, abs_tol=absolute, rel_tol=relative)


def validate_observer_rows(path: Path, sidecar_path: Path) -> dict[str, Any]:
    rows = _tsv_rows(_regular_no_symlink(path).read_bytes(), OBSERVER_COLUMNS)
    tape_rows = _tsv_rows(_regular_no_symlink(sidecar_path).read_bytes(), SIDECAR_COLUMNS)
    if len(rows) != len(tape_rows) or not rows:
        raise SentinelError("observer/tape all-row count closure failed")
    roots: set[str] = set()
    for index, (row, tape) in enumerate(zip(rows, tape_rows, strict=True), 1):
        if row["simulation_event_id"] != str(index) or row["eventlist_id"] != str(index):
            raise SentinelError("observer ID order is not contiguous")
        if row["stable_root_id"] != tape["stable_root_id"] or row["stable_root_id"] in roots:
            raise SentinelError("observer stable-root join failed")
        roots.add(row["stable_root_id"])
        if row["arm"] not in {"F", "U"} or row["observed_particle"] != tape["particle"]:
            raise SentinelError("observer arm/particle join failed")
        expected_digest = tape["expected_generated_binary64_sha256"]
        if row["expected_generated_binary64_sha256"] != expected_digest:
            raise SentinelError("observer expected generated digest join failed")
        numbers = {key: float(value) for key, value in row.items() if key.startswith("observed_") and key not in {
            "observed_particle", "observed_generated_binary64_sha256",
        }}
        if not all(math.isfinite(value) for value in numbers.values()):
            raise SentinelError("observer contains a non-finite generated field")
        excitation = numbers["observed_excitation_keV"]
        source_time = numbers["observed_source_time_s"]
        position = [numbers[f"observed_{axis}_cm"] for axis in "xyz"]
        direction = [numbers[f"observed_d{axis}"] for axis in "xyz"]
        polarization = [numbers[f"observed_p{axis}"] for axis in "xyz"]
        energy = numbers["observed_energy_keV"]
        digest = _observer_binary64_hash(
            [excitation, source_time, *position, *direction, *polarization, energy],
            int(row["observed_particle"]),
        )
        if digest != row["observed_generated_binary64_sha256"] or digest != expected_digest:
            raise SentinelError("observer generated binary64 digest did not independently reproduce")
        if row["expected_source_time_s"] != tape["source_time_s"]:
            raise SentinelError("observer expected source-time text join failed")
        if not _near(source_time, float(tape["source_time_s"]), absolute=1.1e-9, relative=1e-12):
            raise SentinelError("observer native event time differs from tape")
        if excitation != float(tape["excitation_keV"]):
            raise SentinelError("observer excitation differs from tape")
        for observed, expected in zip(position, (float(tape[key]) for key in ("x_cm", "y_cm", "z_cm")), strict=True):
            if not _near(observed, expected, absolute=1e-6, relative=1e-9):
                raise SentinelError("observer position differs from tape")
        for observed, expected in zip(direction, (float(tape[key]) for key in ("dx", "dy", "dz")), strict=True):
            if not _near(observed, expected, absolute=1e-9, relative=1e-9):
                raise SentinelError("observer direction differs from tape")
        for observed, expected in zip(polarization, (float(tape[key]) for key in ("px", "py", "pz")), strict=True):
            if not _near(observed, expected, absolute=1e-9, relative=1e-9):
                raise SentinelError("observer polarization differs from tape")
        if not _near(energy, float(tape["energy_keV"]), absolute=1e-6, relative=1e-9):
            raise SentinelError("observer energy differs from tape")
        norm = math.sqrt(math.fsum(value * value for value in direction))
        if abs(norm - 1.0) > 2e-15:
            raise SentinelError("observer generated direction is not unit length")
    return {
        "status": "PASS__ALL_POST_GPS_OBSERVER_ROWS_JOIN_TAPE",
        "event_count": len(rows),
        "unique_root_count": len(roots),
        "observer": _binding(path),
        "root_sidecar": _binding(sidecar_path),
    }


def _write_mfile_index(path: Path, rich: Mapping[str, Any], tape_rows: Sequence[TapeRow]) -> None:
    lines = ["\t".join(OUTPUT_INDEX_COLUMNS)]
    offset = 0
    for index, (event, tape, fragment) in enumerate(zip(rich["events"], tape_rows, rich["fragments"], strict=True), 1):
        digest = event["event_sha256"]
        row = {
            "schema": "m05-standalone-sim-materializer-v1",
            "simulation_event_id": str(index),
            "eventlist_id": str(index),
            "stable_root_id": tape.stable_root_id,
            "representation": "native",
            "selection_reason": "installed_preload_observer_sentinel",
            "standalone_offset": str(offset),
            "standalone_length": str(len(fragment)),
            "standalone_sha256": digest,
            "source_truth_offset": str(offset),
            "source_truth_length": str(len(fragment)),
            "source_truth_sha256": digest,
            "ia_count": str(event["ia_count"]),
            "ht_count": str(event["ht_count"]),
            "init_tuple_sha256": event["serialized_ia_quantized_sha256"],
            "raw_tape_line_sha256": tape.raw_line_sha256,
            "expected_generated_tuple_sha256": tape.expected_tuple_sha256,
            "expected_eventlist_binary64_sha256": tape.eventlist_binary64_sha256,
            "expected_generated_binary64_sha256": tape.generated_binary64_sha256,
            "observed_generated_binary64_sha256": tape.generated_binary64_sha256,
            "serialized_ia_quantized_sha256": event["serialized_ia_quantized_sha256"],
        }
        lines.append("\t".join(row[column] for column in OUTPUT_INDEX_COLUMNS))
        offset += len(fragment)
    _write_exclusive(path, ("\n".join(lines) + "\n").encode("utf-8"))


def _parse_mfile_pass(stdout: Path, expected_events: int) -> dict[str, Any]:
    prefix = "M05_ROUNDTRIP_JSON "
    lines = stdout.read_text(encoding="utf-8", errors="strict").splitlines()
    matches = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if len(matches) != 1:
        raise SentinelError("real MFileEventsSim consumer emitted no unique result")
    value = json.loads(matches[0])
    if (
        value.get("status") != "PASS__REAL_MFILEEVENTSSIM_ROUNDTRIP__REAL_REVAN_INPUT_AND_ANALYZE"
        or value.get("event_count") != expected_events
        or value.get("unique_init_count") != expected_events
    ):
        raise SentinelError("real MFileEventsSim result closure failed")
    return value


def normalize_cosima_stdout(data: bytes) -> bytes:
    """Normalize only preregistered wall/CPU timing lines, never science text."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SentinelError("Cosima stdout is not UTF-8") from exc
    patterns = (
        (r"(?m)^(Stage [0-9]+ .* finished after )[0-9.eE+-]+( sec)$", r"\1<TIME>\2"),
        (r"(?m)^(Total CPU time spent in run:\s+)[0-9.eE+-]+( sec)$", r"\1<TIME>\2"),
        (r"(?m)^(Time spent per event:\s+)[0-9.eE+-]+( sec)$", r"\1<TIME>\2"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text.encode("utf-8")


def _validate_native_dat_file(path: Path) -> dict[str, Any]:
    blob = _regular_no_symlink(path).read_bytes()
    try:
        tt, totals = _parse_native_dat(blob)
    except RecordValidationError as exc:
        raise SentinelError(f"strict native DAT parse failed: {exc}") from exc
    return {
        "binding": _binding(path),
        "TT_s": tt,
        "rp_aggregate_key_count": len(totals),
        "rp_total_count": sum(totals.values()),
    }


def _runtime_closure_check(
    paths: Sequence[str], *, preload: bool, observer_binary: Path,
    executable: Mapping[str, Any], closure: Sequence[Mapping[str, Any]],
) -> None:
    resolved = {str(Path(path).resolve(strict=True)) for path in paths}
    required = {
        str(Path(str(executable["absolute_path"])).resolve(strict=True)),
        *(str(Path(str(row["absolute_path"])).resolve(strict=True)) for row in closure),
    }
    if not required.issubset(resolved):
        missing = sorted(required - resolved)
        raise SentinelError(f"runtime maps omit bound executable/DSO closure: {missing}")
    observer = str(observer_binary.resolve())
    if (observer in resolved) != preload:
        raise SentinelError("runtime observer mapping differs from arm contract")


def _run_arm(
    pair: Mapping[str, Any],
    arm: str,
    *,
    stage: Path,
    input_root: Path,
    plan: Mapping[str, Any],
    transaction_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _resource_gate(
        roots=(stage, input_root), disk_path=stage.parent,
        phase="before sentinel arm writes",
    )
    _verify_pair_runtime_inputs(pair, plan, transaction_bindings)
    _verify_runtime_authorities(plan)
    arm_root = stage / "pairs" / pair["pair_id"] / arm
    arm_root.mkdir(parents=True, exist_ok=False)
    (arm_root / "tmp").mkdir()
    (arm_root / "home").mkdir()
    base_env = _base_environment(plan)
    base_env["TMPDIR"] = str(arm_root / "tmp")
    base_env["HOME"] = str(arm_root / "home")
    observer_binary = Path(plan["authority_bindings"]["observer_binary"]["absolute_path"])
    if arm == "preload":
        base_env.update({
            "LD_PRELOAD": str(observer_binary),
            "TES511_PRELOAD_ALLOWED_ROOT": str(stage),
            "TES511_PRELOAD_ARM": "F",
            "TES511_PRELOAD_EXPECTED_LIBCOSIMA": plan["authority_bindings"]["installed_libCosima"]["absolute_path"],
            "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256": plan["authority_bindings"]["installed_libCosima"]["sha256"],
            "TES511_PRELOAD_OUTPUT_PREFIX": str(arm_root / "observer"),
            "TES511_PRELOAD_TAPE_ROOT_SIDECAR": pair["shared_root_sidecar"]["absolute_path"],
            "TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256": pair["shared_root_sidecar"]["sha256"],
        })
    else:
        for key in plan["environment_contract"]["preload_only"]:
            base_env.pop(key, None)
    cosima_stdout = arm_root / "cosima.stdout"
    cosima_stderr = arm_root / "cosima.stderr"
    def verify_inputs() -> None:
        _verify_pair_runtime_inputs(pair, plan, transaction_bindings)
        _verify_runtime_authorities(plan)
    metrics = _run_supervised(
        pair[f"{arm}_command_argv"],
        cwd=arm_root,
        environment=base_env,
        stdout_path=cosima_stdout,
        stderr_path=cosima_stderr,
        stage_root=stage,
        input_root=input_root,
        expected_executable_sha256=plan["authority_bindings"]["installed_cosima"]["sha256"],
        input_validator=verify_inputs,
    )
    _runtime_closure_check(
        metrics["runtime_mapped_paths"], preload=arm == "preload", observer_binary=observer_binary,
        executable=plan["authority_bindings"]["installed_cosima"],
        closure=plan["authority_bindings"]["installed_cosima_ldd_closure"],
    )
    sim_path = _discover_one(arm_root, ".sim.gz")
    dat_path = _discover_one(arm_root, ".dat")
    tape_rows = _load_tape(
        Path(pair["shared_tape"]["absolute_path"]),
        Path(pair["shared_root_sidecar"]["absolute_path"]),
        verify_authorities=True,
    )
    rich = validate_rich_sim(
        sim_path,
        geometry=Path(pair["geometry_setup"]["absolute_path"]),
        seed=pair["transport_seed"],
        tape_rows=tape_rows,
    )
    dat = _validate_native_dat_file(dat_path)
    observer: dict[str, Any] | None = None
    if arm == "preload":
        observer_root = arm_root / "observer.gpsobs"
        shared_validation = validate_observer_transaction(
            observer_root,
            Path(pair["shared_tape"]["absolute_path"]),
            Path(pair["shared_root_sidecar"]["absolute_path"]),
            expected_arm="F",
            verify_tape_authorities=True,
            verify_tape_sampler=True,
        )
        independent_validation = validate_observer_rows(
            observer_root / "generated_observations.tsv",
            Path(pair["shared_root_sidecar"]["absolute_path"]),
        )
        if (
            shared_validation.get("status") != "PASS__OBSERVER_TRANSACTION_ONLY__NOT_JOB_PASS"
            or shared_validation.get("event_count") != EVENTS_PER_ARM
            or independent_validation.get("event_count") != shared_validation.get("event_count")
            or independent_validation.get("unique_root_count") != shared_validation.get("unique_root_count")
            or independent_validation["observer"]["sha256"] != shared_validation.get("generated_observations_sha256")
        ):
            raise SentinelError("shared and independent observer validations disagree")
        observer = {
            "shared_validator": shared_validation,
            "independent_recomputation": independent_validation,
            "validator_origin": plan["authority_bindings"]["preload_observer_validation_code"],
            "schema_origin": plan["authority_bindings"]["preload_observer_schema"],
        }
        observer_bytes = _tree_bytes(observer_root)
        if observer_bytes > OBSERVER_FIXED_BYTES + OBSERVER_BYTES_PER_EVENT * EVENTS_PER_ARM:
            raise SentinelError("observer artifact exceeds deterministic byte bound")
        observer["tree_size_bytes"] = observer_bytes
        observer["generated_only_commit"] = _artifact(observer_root / "observer_generated_only.json", stage)
    elif any(path.name.startswith("observer") for path in arm_root.iterdir()):
        raise SentinelError("baseline unexpectedly produced an observer artifact")

    index_path = arm_root / "mfile_index.tsv"
    _write_mfile_index(index_path, rich, tape_rows)
    mfile_stdout = arm_root / "mfileeventssim.stdout"
    mfile_stderr = arm_root / "mfileeventssim.stderr"
    mfile_binary = Path(plan["authority_bindings"]["mfile_consumer_binary"]["absolute_path"])
    mfile_metrics = _run_supervised(
        [str(mfile_binary), pair["geometry_setup"]["absolute_path"], str(sim_path), str(index_path)],
        cwd=arm_root,
        environment=_base_environment(plan) | {
            "HOME": str(arm_root / "home"), "TMPDIR": str(arm_root / "tmp"),
        },
        stdout_path=mfile_stdout,
        stderr_path=mfile_stderr,
        stage_root=stage,
        input_root=input_root,
        expected_executable_sha256=plan["authority_bindings"]["mfile_consumer_binary"]["sha256"],
        input_validator=verify_inputs,
    )
    _runtime_closure_check(
        mfile_metrics["runtime_mapped_paths"], preload=False, observer_binary=observer_binary,
        executable=plan["authority_bindings"]["mfile_consumer_binary"],
        closure=plan["authority_bindings"]["mfile_consumer_ldd_closure"],
    )
    mfile_result = _parse_mfile_pass(mfile_stdout, EVENTS_PER_ARM)
    receipt = {
        "schema_version": "m05-installed-preload-observer-sentinel-arm-receipt-v1",
        "status": "PASS__ARM_OUTPUTS_VALIDATED__NOT_PAIR_OR_SENTINEL_PASS",
        "benchmark_class": BENCHMARK_CLASS,
        "pair_id": pair["pair_id"],
        "arm": arm,
        "events": EVENTS_PER_ARM,
        "seed": pair["transport_seed"],
        "shared_tape_sha256": pair["shared_tape"]["sha256"],
        "shared_card_sha256": pair["shared_source_card"]["sha256"],
        "cosima_metrics": metrics,
        "rich_sim": {
            key: value for key, value in rich.items() if key not in {"canonical_bytes", "fragments"}
        },
        "native_dat": dat,
        "observer": observer,
        "mfile_index": _artifact(index_path, stage),
        "mfile_metrics": mfile_metrics,
        "mfile_result": mfile_result,
    }
    receipt_path = arm_root / "arm.commit.json"
    _write_exclusive(receipt_path, canonical_json_bytes(receipt))
    receipt["commit"] = _artifact(receipt_path, stage)
    receipt["_canonical_sim_bytes"] = rich["canonical_bytes"]
    receipt["_dat_bytes"] = dat_path.read_bytes()
    receipt["_stdout_normalized"] = normalize_cosima_stdout(cosima_stdout.read_bytes())
    receipt["_stderr_bytes"] = cosima_stderr.read_bytes()
    return receipt


def _public_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if not key.startswith("_")}


def _compare_pair(pair: Mapping[str, Any], arms: Mapping[str, Mapping[str, Any]], stage: Path) -> dict[str, Any]:
    baseline = arms["baseline"]
    preload = arms["preload"]
    if baseline["_canonical_sim_bytes"] != preload["_canonical_sim_bytes"]:
        raise SentinelError("baseline/preload rich SIM differs after Date-only canonicalization")
    if baseline["_dat_bytes"] != preload["_dat_bytes"]:
        raise SentinelError("baseline/preload native DAT raw bytes differ")
    if baseline["native_dat"]["TT_s"] != preload["native_dat"]["TT_s"]:
        raise SentinelError("baseline/preload native TT differs")
    if baseline["_stdout_normalized"] != preload["_stdout_normalized"]:
        raise SentinelError("baseline/preload Cosima stdout differs beyond preregistered timing lines")
    if baseline["_stderr_bytes"] != preload["_stderr_bytes"]:
        raise SentinelError("baseline/preload Cosima stderr differs")
    baseline_rss = baseline["cosima_metrics"]["peak_process_group_rss_bytes"]
    preload_rss = preload["cosima_metrics"]["peak_process_group_rss_bytes"]
    if preload_rss - baseline_rss > MAXIMUM_PRELOAD_RSS_DELTA_BYTES:
        raise SentinelError("preload peak RSS exceeds paired bound")
    receipt = {
        "schema_version": "m05-installed-preload-observer-sentinel-pair-receipt-v1",
        "status": "PASS__PAIR_NO_PERTURBATION__NOT_SENTINEL_OR_FULL_SMOKE_PASS",
        "benchmark_class": BENCHMARK_CLASS,
        "pair_id": pair["pair_id"],
        "cell_id": pair["cell_id"],
        "geometry": pair["geometry"],
        "family": pair["family"],
        "mode": pair["mode"],
        "shard_index": pair["shard_index"],
        "arm_order": pair["arm_order"],
        "events_per_arm": EVENTS_PER_ARM,
        "seed": pair["transport_seed"],
        "shared_tape_sha256": pair["shared_tape"]["sha256"],
        "shared_root_sidecar_sha256": pair["shared_root_sidecar"]["sha256"],
        "shared_source_card_sha256": pair["shared_source_card"]["sha256"],
        "canonical_rich_sim_sha256": baseline["rich_sim"]["canonical_date_only_sha256"],
        "native_dat_sha256": baseline["native_dat"]["binding"]["sha256"],
        "native_TT_s": baseline["native_dat"]["TT_s"],
        "stdout_normalized_sha256": sha256_bytes(baseline["_stdout_normalized"]),
        "stderr_sha256": sha256_bytes(baseline["_stderr_bytes"]),
        "baseline_arm_commit": baseline["commit"],
        "preload_arm_commit": preload["commit"],
        "paired_wall_delta_s": preload["cosima_metrics"]["wall_s"] - baseline["cosima_metrics"]["wall_s"],
        "paired_cpu_delta_s": (
            preload["cosima_metrics"]["cpu_user_s"] + preload["cosima_metrics"]["cpu_system_s"]
            - baseline["cosima_metrics"]["cpu_user_s"] - baseline["cosima_metrics"]["cpu_system_s"]
        ),
        "paired_peak_rss_delta_bytes": preload_rss - baseline_rss,
    }
    pair_root = stage / "pairs" / pair["pair_id"]
    receipt_path = pair_root / "pair.commit.json"
    _write_exclusive(receipt_path, canonical_json_bytes(receipt))
    receipt["commit"] = _artifact(receipt_path, stage)
    return receipt


def _consume_authorization(
    token_path: Path,
    token: Mapping[str, Any],
    token_sha256: str,
    envelope: Mapping[str, Any],
    input_commit: Mapping[str, Any],
    stage: Path,
) -> Path:
    consumed = token_path.with_name(token_path.name + ".consumed.json")
    receipt = {
        "schema_version": "m05-installed-preload-observer-sentinel-authorization-consumption-v1",
        "status": "CONSUMED__BEFORE_FIRST_SENTINEL_TRANSPORT_EVENT",
        "authorization_id": token["authorization_id"],
        "authorization_token_sha256": token_sha256,
        "plan_sha256": envelope["plan_sha256"],
        "input_bundle_commit_sha256": input_commit["commit"]["sha256"],
        "candidate_stage": str(stage),
        "candidate_final": envelope["plan"]["output_root"],
        "transport_events_started_at_receipt": 0,
        "scope": "672-event installed no-preload/LD_PRELOAD sentinel only",
    }
    payload = canonical_json_bytes(receipt)
    input_root = Path(str(input_commit["commit"]["absolute_path"])).parent
    _resource_gate(
        roots=(stage, input_root), disk_path=consumed.parent,
        extra_bytes=len(payload), phase="before authorization-consumption write",
    )
    _write_exclusive(consumed, payload, 0o444)
    return consumed


def execute(envelope: Mapping[str, Any], authorization_token: Path | None) -> dict[str, Any]:
    """Execute only after exact one-shot authorization.  Never called by default."""

    if authorization_token is None:
        raise SentinelError("execution requires --authorization-token; no token is generated by this harness")
    plan = envelope["plan"]
    output_root = Path(plan["output_root"])
    # Invalid/stale authorization must fail before creating even an empty
    # output-parent namespace.
    token, token_sha = verify_authorization_token(authorization_token, envelope)
    _resource_gate(roots=(), disk_path=output_root.parent, phase="before sentinel input/stage writes")
    _ensure_output_parent(output_root.parent)
    if output_root.exists():
        raise FileExistsError(f"write-once candidate already exists: {output_root}")
    input_root = Path(plan["input_bundle_root"])
    stage = output_root.with_name(f".{output_root.name}.partial.{token['authorization_id']}")
    invocations = 0
    events = 0
    pair_receipts: list[dict[str, Any]] = []
    arm_receipts: list[dict[str, Any]] = []
    published = False
    input_published = False
    stage_owned = False
    consumed_path = authorization_token.with_name(authorization_token.name + ".consumed.json")
    try:
        input_commit = prepare_input_bundle(envelope)
        input_published = True
        _resource_gate(
            roots=(input_root,), disk_path=output_root.parent,
            phase="before sentinel stage write",
        )
        if stage.exists() or output_root.exists():
            raise FileExistsError(f"candidate stage/final exists: {stage} / {output_root}")
        stage.mkdir(parents=False, mode=0o755)
        stage_owned = True
        fsync_directory(stage.parent)
        execution_plan_payload = canonical_json_bytes(envelope)
        _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            extra_bytes=len(execution_plan_payload), phase="before execution-plan write",
        )
        _write_exclusive(stage / "execution_plan.json", execution_plan_payload)
        token_payload = canonical_json_bytes(token)
        _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            extra_bytes=len(token_payload), phase="before authorization-copy write",
        )
        _write_exclusive(stage / "authorization_token.json", token_payload, 0o444)
        consumed_path = _consume_authorization(
            authorization_token, token, token_sha, envelope, input_commit, stage,
        )
        transaction_bindings = {
            "input_bundle_commit": dict(input_commit["commit"]),
            "execution_plan": _binding(stage / "execution_plan.json"),
        }
        for pair in plan["pairs"]:
            arms: dict[str, dict[str, Any]] = {}
            for arm in pair["arm_order"]:
                if invocations >= token["installed_cosima_invocation_limit"]:
                    raise SentinelError("authorization invocation limit would be exceeded")
                if events + EVENTS_PER_ARM > token["transport_event_limit"]:
                    raise SentinelError("authorization transport-event limit would be exceeded")
                invocations += 1
                events += EVENTS_PER_ARM
                arms[arm] = _run_arm(
                    pair, arm, stage=stage, input_root=input_root, plan=plan,
                    transaction_bindings=transaction_bindings,
                )
                arm_receipts.append(_public_receipt(arms[arm]))
            pair_receipts.append(_compare_pair(pair, arms, stage))
        if invocations != INVOCATION_COUNT or events != TRANSPORT_EVENT_COUNT or len(pair_receipts) != PAIR_COUNT:
            raise SentinelError("executed sentinel shape differs from exact authorization")

        baseline_wall = sum(row["cosima_metrics"]["wall_s"] for row in arm_receipts if row["arm"] == "baseline")
        preload_wall = sum(row["cosima_metrics"]["wall_s"] for row in arm_receipts if row["arm"] == "preload")
        baseline_cpu = sum(
            row["cosima_metrics"]["cpu_user_s"] + row["cosima_metrics"]["cpu_system_s"]
            for row in arm_receipts if row["arm"] == "baseline"
        )
        preload_cpu = sum(
            row["cosima_metrics"]["cpu_user_s"] + row["cosima_metrics"]["cpu_system_s"]
            for row in arm_receipts if row["arm"] == "preload"
        )
        wall_limit = max(60.0, 0.05 * baseline_wall)
        cpu_limit = max(60.0, 0.05 * baseline_cpu)
        if preload_wall - baseline_wall > wall_limit or preload_cpu - baseline_cpu > cpu_limit:
            raise SentinelError("aggregate observer overhead gate failed")
        new_bytes = _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            phase="before sentinel final artifacts",
        )

        all_mapped = sorted({
            path
            for arm in arm_receipts
            for path in arm["cosima_metrics"]["runtime_mapped_paths"]
        })
        runtime_closure = {
            "schema_version": "m05-installed-preload-observer-sentinel-runtime-dso-closure-v1",
            "paths": [_binding(Path(path)) for path in all_mapped],
        }
        runtime_payload = canonical_json_bytes(runtime_closure)
        _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            extra_bytes=len(runtime_payload), phase="before runtime closure write",
        )
        _write_exclusive(stage / "runtime_dso_closure.json", runtime_payload)
        summary = {
            "schema_version": "m05-installed-preload-observer-sentinel-summary-v1",
            "status": "PASS__SENTINEL_ONLY__FULL_SMOKE_REQUIRES_SECOND_INDEPENDENT_AUTHORIZATION",
            "benchmark_class": BENCHMARK_CLASS,
            "merge_eligible": False,
            "M05_COMPLETE": False,
            "full_smoke_authorized": False,
            "plan_sha256": envelope["plan_sha256"],
            "authorization_token_sha256": token_sha,
            "authorization_consumption_receipt": _binding(consumed_path),
            "input_bundle_commit": input_commit["commit"],
            "transport_events": events,
            "installed_cosima_invocations": invocations,
            "pair_count": len(pair_receipts),
            "all_pairs_passed": True,
            "baseline_wall_s": baseline_wall,
            "preload_wall_s": preload_wall,
            "wall_overhead_s": preload_wall - baseline_wall,
            "wall_overhead_limit_s": wall_limit,
            "baseline_cpu_s": baseline_cpu,
            "preload_cpu_s": preload_cpu,
            "cpu_overhead_s": preload_cpu - baseline_cpu,
            "cpu_overhead_limit_s": cpu_limit,
            "new_bytes_before_final_commit": new_bytes,
            "maximum_new_bytes": MAXIMUM_NEW_BYTES,
            "runtime_dso_closure": _artifact(stage / "runtime_dso_closure.json", stage),
            "pair_commits": [row["commit"] for row in pair_receipts],
            "release_boundary": "a new independent write-once token bound to this immutable sentinel candidate and unchanged installed closure is required before full smoke",
            "N0_boundary": "sentinel PASS is no authority for a pure transport-stepping acceleration claim",
        }
        commit_path = stage / "sentinel.commit.json"
        summary_payload = canonical_json_bytes(summary)
        _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            extra_bytes=len(summary_payload), phase="before sentinel final commit",
        )
        _write_exclusive(commit_path, summary_payload)
        _fsync_tree(stage)
        _resource_gate(
            roots=(stage, input_root), disk_path=output_root.parent,
            phase="before sentinel final publication",
        )
        _rename_noreplace(stage, output_root)
        published = True
        stage_owned = False
        fsync_directory(output_root.parent)
        _resource_gate(
            roots=(output_root, input_root), disk_path=output_root.parent,
            phase="after sentinel final publication",
        )
        return summary
    except BaseException as exc:
        failure = {
            "schema_version": "m05-installed-preload-observer-sentinel-failure-v1",
            "status": "FAILED__QUARANTINED_TRANSACTION",
            "error": f"{type(exc).__name__}: {exc}",
            "transport_events_started_upper_bound": events,
            "installed_cosima_invocations_started_upper_bound": invocations,
            "plan_sha256": envelope["plan_sha256"],
            "authorization_token_sha256": token_sha,
            "authorization_consumption_receipt_exists": consumed_path.is_file(),
        }
        quarantine_errors: list[str] = []
        failed: Path | None = None
        try:
            if published:
                failed = quarantine_directory_no_replace(output_root)
            elif stage_owned:
                failed = quarantine_directory_no_replace(stage)
        except BaseException as quarantine_error:
            quarantine_errors.append(f"stage/final: {quarantine_error}")
        try:
            if input_published:
                quarantine_directory_no_replace(input_root)
        except BaseException as quarantine_error:
            quarantine_errors.append(f"input: {quarantine_error}")
        if quarantine_errors:
            raise SentinelError(
                f"sentinel failed ({exc}); collision-safe quarantine failed ({'; '.join(quarantine_errors)})"
            ) from exc
        if failed is not None:
            # Preserve the original transaction bytes first.  A diagnostic is
            # additive and never recreates a former authoritative pathname.
            failure_path = failed / "failure.json"
            if not failure_path.exists():
                _write_exclusive(failure_path, canonical_json_bytes(failure))
            _fsync_tree(failed)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--print-plan", action="store_true", help="read-only default; emit canonical plan JSON")
    action.add_argument("--execute", action="store_true", help="execute only with an exact independent one-shot token")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--authorization-token", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    envelope = build_plan(args.output_root)
    if not args.execute:
        if args.authorization_token is not None:
            raise SentinelError("--authorization-token is accepted only with --execute")
        sys.stdout.buffer.write(canonical_json_bytes(envelope))
        return 0
    summary = execute(envelope, args.authorization_token)
    sys.stdout.buffer.write(canonical_json_bytes(summary))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SentinelError, FileExistsError, OSError, ValueError) as error:
        print(json.dumps({"status": "FAIL__PRELOAD_OBSERVER_SENTINEL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
