#!/usr/bin/env python3
"""Build the required real MEGAlib/Revan zero-transport consumer gate.

The output is content addressed and published transactionally.  This helper
never starts Cosima, EventList, or Geant4; it only invokes the host compiler
and linker against the already installed MEGAlib/ROOT libraries.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "code/mfileeventssim_roundtrip.cc"
DEFAULT_MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
BUILD_ROOT = PACKAGE / "build/nontransport/real_mfileeventssim_roundtrip"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _capture(argv: list[str]) -> str:
    completed = subprocess.run(
        argv, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {argv!r}\n{completed.stdout}")
    return completed.stdout.strip()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o644) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_consumer() -> tuple[Path, dict[str, Any]]:
    """Return a verified content-addressed executable and build manifest."""

    megalib = Path(os.environ.get("M05_MEGALIB_ROOT", str(DEFAULT_MEGALIB))).resolve()
    compiler_text = os.environ.get("CXX", "g++")
    compiler = Path(shutil.which(compiler_text) or compiler_text).resolve()
    root_config = megalib / "external/root_v6.36.6/bin/root-config"
    include = megalib / "include"
    library = megalib / "lib"
    for required in (SOURCE, compiler, root_config, include, library):
        if not required.exists():
            raise FileNotFoundError(required)
    compiler_version = _capture([str(compiler), "--version"])
    root_version = _capture([str(root_config), "--version"])
    root_cflags = shlex.split(_capture([str(root_config), "--cflags"]))
    root_glibs = shlex.split(_capture([str(root_config), "--glibs"]))
    fixed_args = [
        "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-isystem", str(include), *root_cflags, str(SOURCE),
        f"-L{library}", f"-Wl,-rpath,{library}", "-Wl,--no-as-needed",
        "-lRevan", "-lSpectralyze", "-lSivan", "-lGeomega",
        "-lCommonMisc", "-lCommonGui", "-lcrypto", *root_glibs,
    ]
    identity = {
        "schema_version": "m05-real-mfileeventssim-consumer-build-v1",
        "source_sha256": _sha256(SOURCE),
        "compiler": str(compiler),
        "compiler_version": compiler_version,
        "megalib_root": str(megalib),
        "root_config": str(root_config),
        "root_version": root_version,
        "compile_and_link_args_without_output": fixed_args,
    }
    fingerprint = hashlib.sha256(_canonical(identity)).hexdigest()
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    binary = BUILD_ROOT / f"mfileeventssim_roundtrip.{fingerprint}"
    manifest_path = BUILD_ROOT / f"mfileeventssim_roundtrip.{fingerprint}.json"

    if binary.exists() or manifest_path.exists():
        if not binary.is_file() or not manifest_path.is_file():
            raise FileExistsError("incomplete content-addressed consumer build")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("identity") != identity
            or manifest.get("binary_sha256") != _sha256(binary)
            or manifest.get("status") != "PASS__REAL_MEGALIB_REVAN_CONSUMER_BUILD__NO_TRANSPORT"
        ):
            raise RuntimeError("existing content-addressed consumer build failed verification")
        return binary, manifest

    partial = BUILD_ROOT / f".{binary.name}.partial.{os.getpid()}"
    if partial.exists():
        raise FileExistsError(partial)
    command = [str(compiler), *fixed_args, "-o", str(partial)]
    completed = subprocess.run(
        command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"consumer compile/link failed\n{completed.stdout}")
    if completed.stdout:
        raise RuntimeError(f"consumer compile/link emitted output under -Werror\n{completed.stdout}")
    os.chmod(partial, 0o755)
    with partial.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(partial, binary)
    _fsync_directory(BUILD_ROOT)
    ldd_output = _capture(["ldd", str(binary)])
    if "not found" in ldd_output:
        raise RuntimeError(f"linked consumer has unresolved libraries\n{ldd_output}")
    manifest = {
        "schema_version": "m05-real-mfileeventssim-consumer-build-manifest-v1",
        "status": "PASS__REAL_MEGALIB_REVAN_CONSUMER_BUILD__NO_TRANSPORT",
        "transport_events_launched": 0,
        "identity": identity,
        "command_argv": command[:-1] + ["<content-addressed-output>"],
        "binary_path": str(binary),
        "binary_sha256": _sha256(binary),
        "binary_size_bytes": binary.stat().st_size,
        "ldd_output": ldd_output,
    }
    partial_manifest = BUILD_ROOT / f".{manifest_path.name}.partial.{os.getpid()}"
    _write_exclusive(partial_manifest, _canonical(manifest))
    os.replace(partial_manifest, manifest_path)
    _fsync_directory(BUILD_ROOT)
    return binary, manifest


if __name__ == "__main__":
    executable, build_manifest = build_consumer()
    print(json.dumps({"executable": str(executable), **build_manifest}, sort_keys=True))
