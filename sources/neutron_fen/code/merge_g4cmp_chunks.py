#!/usr/bin/env python3
"""Merge chunked SH3 G4CMP outputs into one analyzer-compatible run directory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("chunk_dirs", nargs="+", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    map_rows = []
    hit_rows = []
    next_event = 0
    for chunk_index, chunk in enumerate(args.chunk_dirs, start=1):
        summary = json.loads((chunk / "summary.json").read_text())
        if summary.get("status") != "COMPLETE":
            raise SystemExit(f"incomplete chunk: {chunk}")
        summaries.append(summary)
        old_to_new: dict[int, int] = {}
        with (chunk / "event_map.csv").open(newline="") as stream:
            for row in csv.DictReader(stream):
                old = int(row["sim_event_id"])
                new = next_event
                next_event += 1
                old_to_new[old] = new
                row["sim_event_id"] = str(new)
                row["transport_chunk"] = str(chunk_index)
                map_rows.append(row)
        with (chunk / "hits.csv").open(newline="") as stream:
            for row in csv.DictReader(stream):
                old = int(row["sim_event_id"])
                row["sim_event_id"] = str(old_to_new[old])
                row["transport_chunk"] = str(chunk_index)
                hit_rows.append(row)

    map_path = args.output_dir / "event_map.csv"
    hit_path = args.output_dir / "hits.csv"
    map_fields = list(map_rows[0])
    hit_fields = list(hit_rows[0])
    with map_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=map_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(map_rows)
    with hit_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=hit_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(hit_rows)

    first = summaries[0]
    energy_fields = ("input_weighted", "sensor", "bath", "bulk", "recorded_total")
    energy = {name: sum(float(s["energy_eV"][name]) for s in summaries) for name in energy_fields}
    counts = {
        name: sum(int(s["counts"][name]) for s in summaries)
        for name in ("groups", "deposits", "primary_packets", "recorded_terminal_hits")
    }
    summary = {
        "schema_version": 1,
        "status": "COMPLETE",
        "engine": first["engine"],
        "paths": {
            "input_csv": "chunked; see merge_manifest.json",
            "pixel_csv": first["paths"]["pixel_csv"],
            "hit_csv": str(hit_path.resolve()),
            "event_map_csv": str(map_path.resolve()),
        },
        "configuration": {
            **first["configuration"],
            "transport_chunk_count": len(summaries),
            "chunk_seeds": [s["configuration"]["seeds"] for s in summaries],
        },
        "counts": counts,
        "energy_eV": {
            **energy,
            "closure_fraction": energy["recorded_total"] / energy["input_weighted"],
            "sensor_eta": energy["sensor"] / energy["input_weighted"],
        },
        "wall_time_s": sum(float(s["wall_time_s"]) for s in summaries),
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = {
        "schema_version": 1,
        "status": "PASS",
        "chunk_dirs": [str(p.resolve()) for p in args.chunk_dirs],
        "counts": counts,
        "output_sha256": {
            "event_map.csv": sha256(map_path),
            "hits.csv": sha256(hit_path),
            "summary.json": sha256(summary_path),
        },
        "self_checks": {
            "unique_reindexed_sim_event_ids": len({int(r["sim_event_id"]) for r in map_rows}) == len(map_rows),
            "all_hit_event_ids_resolved": all(0 <= int(r["sim_event_id"]) < len(map_rows) for r in hit_rows),
            "closure_within_1e-9": abs(summary["energy_eV"]["closure_fraction"] - 1.0) < 1e-9,
        },
    }
    (args.output_dir / "merge_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    if not all(manifest["self_checks"].values()):
        raise SystemExit("merge self-check failed")
    print(f"PASS: merged {len(summaries)} chunks into {args.output_dir}")


if __name__ == "__main__":
    main()
