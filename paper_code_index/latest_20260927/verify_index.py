#!/usr/bin/env python3
"""Read-only verification; never imports or executes snapshotted science code."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-originals", action="store_true", help="Also compare original files and manuscript hashes on the source computer")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "INDEX.json").read_text())
    failures = []
    python_count = 0
    total_bytes = 0
    declared = set()
    originals = set()
    for row in manifest["files"]:
        rel = Path(row["snapshot_path"])
        path = root / rel
        if rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.parts[0] != "snapshot":
            failures.append("Unsafe manifest path: " + str(rel))
            continue
        if str(rel) in declared:
            failures.append("Duplicate manifest path: " + str(rel))
        declared.add(str(rel))
        originals.add(row["source_path"])
        if not path.is_file() or path.is_symlink():
            failures.append("Missing/nonregular snapshot: " + str(rel))
            continue
        data = path.read_bytes()
        total_bytes += len(data)
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            failures.append("Snapshot hash/size mismatch: " + str(rel))
        if bool(path.stat().st_mode & 0o111) != row["executable"]:
            failures.append("Snapshot executable mode mismatch: " + str(rel))
        if path.suffix == ".py":
            try:
                ast.parse(data.decode("utf-8-sig"), filename=str(rel))
                python_count += 1
            except (SyntaxError, UnicodeError) as error:
                failures.append("Python syntax error: " + str(rel) + ": " + str(error))
        if args.check_originals:
            source = Path(row["source_path"])
            if not source.is_file() or sha(source) != row["sha256"]:
                failures.append("Original missing or changed: " + str(source))
    actual = {p.relative_to(root).as_posix() for p in (root / "snapshot").rglob("*") if p.is_file()}
    if actual != declared:
        failures.append("Snapshot inventory differs from manifest: " + str(sorted(actual ^ declared)))
    edges_path = root / "DEPENDENCIES.json"
    edges = json.loads(edges_path.read_text())
    for edge in edges["code_edges"]:
        for endpoint in ("consumer", "provider"):
            if edge[endpoint] not in originals:
                failures.append("Dependency endpoint not frozen: " + edge[endpoint])
    if args.check_originals:
        for row in manifest["manuscripts"]:
            path = Path(row["path"])
            if not path.is_file() or sha(path) != row["sha256"]:
                failures.append("Manuscript identity differs: " + str(path))
    result = {
        "status": "FAIL" if failures else "PASS",
        "files_verified": len(declared),
        "python_sources_parsed": python_count,
        "source_bytes": total_bytes,
        "code_edges_verified": len(edges["code_edges"]),
        "originals_checked": args.check_originals,
        "scientific_code_executed": False,
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
