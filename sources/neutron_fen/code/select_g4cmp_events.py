#!/usr/bin/env python3
"""Select prepared G4CMP rows by candidate label without altering row content."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", action="append", required=True)
    args = parser.parse_args()
    wanted = set(args.candidate)
    with args.input.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = [row for row in reader if row.get("candidate") in wanted]
    found = {row["candidate"] for row in rows}
    if found != wanted:
        raise SystemExit(f"candidate selection mismatch: wanted={wanted}, found={found}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "schema_version": 1,
        "status": "PASS",
        "input": {"path": str(args.input.resolve()), "sha256": sha(args.input)},
        "output": {"path": str(args.output.resolve()), "sha256": sha(args.output)},
        "candidates": sorted(wanted),
        "rows": len(rows),
        "energy_keV": sum(float(row["energy_keV"]) for row in rows),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
