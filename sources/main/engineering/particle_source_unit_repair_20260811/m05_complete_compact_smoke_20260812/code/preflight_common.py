#!/usr/bin/env python3
"""Fail-closed helpers for the isolated, non-mergeable M05 smoke preflight."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import ctypes
import errno
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[2]
RUN_PACKAGE = ROOT / "runs/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812"


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def strict_json_bytes(data: bytes, *, source: str = "<bytes>") -> Any:
    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r} in {source}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {source}")
            result[key] = value
        return result

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"JSON is not UTF-8: {source}") from error
    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)


def strict_json(path: Path) -> Any:
    return strict_json_bytes(path.read_bytes(), source=str(path))


def reject_lexical_symlinks(path: Path, *, stop: Path | None = None) -> None:
    """Reject every existing symlink component before any ``resolve()`` call.

    ``Path.is_symlink`` after resolution cannot detect an in-repository link that
    happens to point back into the repository.  Authority checks therefore walk
    the lexical path with ``lstat`` first.  Missing final components are allowed
    so the same helper can protect write-once output paths.
    """

    absolute = path.absolute()
    floor = (stop or Path(absolute.anchor)).absolute()
    try:
        relative = absolute.relative_to(floor)
    except ValueError as exc:
        raise ValueError(f"lexical path {path} is outside symlink-check root {floor}") from exc
    cursor = floor
    for part in relative.parts:
        cursor = cursor / part
        try:
            mode = os.lstat(cursor).st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError(f"symlinked authority/output component is forbidden: {cursor}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repo_path(value: str | Path, *, must_exist: bool = True) -> Path:
    candidate = Path(value)
    if ".." in candidate.parts:
        raise ValueError(f"parent traversal is forbidden in authority path: {value}")
    lexical = candidate if candidate.is_absolute() else ROOT / candidate
    try:
        lexical_relative = lexical.absolute().relative_to(ROOT.absolute())
    except ValueError as exc:
        raise ValueError(f"authority path is not lexically inside repository: {value}") from exc
    reject_lexical_symlinks(lexical, stop=ROOT.absolute())
    path = lexical.resolve()
    try:
        relative = path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {value}") from exc
    if must_exist:
        if not lexical.exists():
            raise FileNotFoundError(f"missing authority: {lexical}")
        # The lexical lstat walk above runs before resolve and also catches links
        # that resolve back inside ROOT.
    return path


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def verify_file(value: str | Path, expected_sha256: str) -> Path:
    path = repo_path(value)
    actual = sha256(path)
    if actual != expected_sha256:
        raise ValueError(f"SHA-256 mismatch for {rel(path)}: {actual} != {expected_sha256}")
    return path


def write_once(path: Path, data: bytes) -> None:
    reject_lexical_symlinks(path, stop=ROOT.absolute() if path.absolute().is_relative_to(ROOT.absolute()) else None)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o664)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(path.parent)
    except BaseException:
        _quarantine_failed_file(path)
        raise


def atomic_replace(path: Path, data: bytes) -> None:
    reject_lexical_symlinks(path, stop=ROOT.absolute() if path.absolute().is_relative_to(ROOT.absolute()) else None)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temp.exists():
        raise FileExistsError(temp)
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        fsync_directory(path.parent)
    finally:
        if temp.exists():
            _quarantine_failed_file(temp)


def _quarantine_failed_file(path: Path) -> Path | None:
    """Retain failed write bytes under an unmistakably non-authoritative name."""

    if not path.exists():
        return None
    for ordinal in range(10_000):
        suffix = f".failed.{os.getpid()}" + (f".{ordinal}" if ordinal else "")
        quarantine = path.with_name(f".{path.name}{suffix}")
        if quarantine.exists():
            continue
        os.replace(path, quarantine)
        fsync_directory(path.parent)
        return quarantine
    raise RuntimeError(f"cannot allocate quarantine name for failed file {path}")


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def rename_no_replace(source: Path, target: Path) -> None:
    """Atomically publish ``source`` without ever replacing ``target``.

    Linux ``rename(2)`` may replace an existing empty directory, so an
    existence check followed by :func:`os.rename` is not a write-once
    transaction.  This helper requires ``renameat2(RENAME_NOREPLACE)``.  A
    platform without that primitive fails closed; there is deliberately no
    ordinary-rename fallback.
    """

    source = source.absolute()
    target = target.absolute()
    reject_lexical_symlinks(source)
    reject_lexical_symlinks(target)
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "renameat2(RENAME_NOREPLACE) is required")
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    if renameat2(
        at_fdcwd,
        os.fsencode(source),
        at_fdcwd,
        os.fsencode(target),
        rename_noreplace,
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(target))
    # Durability is deliberately the caller's next operation.  Keeping the
    # namespace change separate lets the caller know with certainty whether a
    # later fsync failure happened before or after publication and quarantine
    # the published name accordingly.


def quarantine_directory_no_replace(path: Path) -> Path | None:
    """Move a failed directory to a non-authoritative name without replacement."""

    if not path.exists():
        return None
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"failed directory is missing, non-directory, or symlink: {path}")
    for ordinal in range(10_000):
        if ordinal == 0:
            suffix = ".failed"
        elif ordinal == 1:
            suffix = f".failed.{os.getpid()}"
        else:
            suffix = f".failed.{os.getpid()}.{ordinal - 1}"
        candidate = path.with_name(path.name + suffix)
        try:
            rename_no_replace(path, candidate)
        except FileExistsError:
            continue
        fsync_directory(candidate.parent)
        return candidate
    raise RuntimeError(f"cannot allocate no-replace quarantine directory for {path}")


def assert_canonical_json(path: Path) -> Any:
    value = strict_json(path)
    actual = path.read_bytes()
    expected = canonical_json_bytes(value)
    if actual != expected:
        raise ValueError(f"JSON is not canonical: {path}")
    return value
