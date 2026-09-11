#!/usr/bin/env python3
"""Deterministically split prepared G4CMP CSVs without splitting event-layer groups."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import OrderedDict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--max-hits", type=int, default=48)
    parser.add_argument("--max-groups", type=int, default=8)
    args = parser.parse_args()
    if args.max_hits < 1:
        raise SystemExit("--max-hits must be positive")
    if args.max_groups < 1:
        raise SystemExit("--max-groups must be positive")

    with args.input.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields:
            raise SystemExit("empty input")
        groups: OrderedDict[tuple[str, str], list[dict[str, str]]] = OrderedDict()
        for row in reader:
            key = (row["input_event_key"], row["layer"])
            groups.setdefault(key, []).append(row)

    # Deposits are independent weighted source vertices in a linear transport
    # kernel.  Oversized event-layer groups may therefore span process chunks;
    # downstream aggregation rejoins them by the unchanged physical event key.
    units: list[list[dict[str, str]]] = []
    split_group_count = 0
    for rows in groups.values():
        if len(rows) > args.max_hits:
            split_group_count += 1
        units.extend(rows[i : i + args.max_hits] for i in range(0, len(rows), args.max_hits))

    chunks: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    current_units = 0
    for rows in units:
        if current and (len(current) + len(rows) > args.max_hits or current_units >= args.max_groups):
            chunks.append(current)
            current = []
            current_units = 0
        current.extend(rows)
        current_units += 1
    if current:
        chunks.append(current)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "input": {"path": str(args.input.resolve()), "sha256": sha256(args.input)},
        "policy": {
            "max_hits": args.max_hits,
            "max_groups_per_process_chunk": args.max_groups,
            "split_oversized_event_layer_groups_across_process_chunks": True,
            "physical_event_identity_columns_unchanged": True,
            "split_group_count": split_group_count,
        },
        "chunks": [],
    }
    total_rows = 0
    for index, rows in enumerate(chunks, start=1):
        path = args.output_dir / f"chunk_{index:03d}.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        total_rows += len(rows)
        manifest["chunks"].append(
            {
                "index": index,
                "path": str(path.resolve()),
                "rows": len(rows),
                "event_layer_groups": len({(r["input_event_key"], r["layer"]) for r in rows}),
                "sha256": sha256(path),
            }
        )
    manifest["self_check"] = {
        "input_rows": sum(len(rows) for rows in groups.values()),
        "output_rows": total_rows,
        "same_row_count": total_rows == sum(len(rows) for rows in groups.values()),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(chunks)} chunks, {total_rows} rows to {args.output_dir}")


if __name__ == "__main__":
    main()
