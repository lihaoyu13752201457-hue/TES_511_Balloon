#!/usr/bin/env python3
"""Recover a receipt only for a fully closed Cosima SIM after session interruption."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "run_gamma_supplement.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("m05new_gamma_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=int)
    args = parser.parse_args()
    runner = load_runner()
    index = args.index
    p = runner.paths(index)
    source = Path(p["source"])
    sim = Path(p["sim"])
    activation = Path(p["activation"])
    receipt = Path(p["receipt"])
    if receipt.exists():
        raise RuntimeError(f"receipt already exists: {receipt}")
    if not source.exists() or not sim.exists() or not activation.exists():
        raise RuntimeError("source, SIM, and activation output are all required")

    expected_seed = int(runner.SEEDS[index - 1])
    expected_geometry = str(runner.GEOMETRY)
    header_seed = None
    header_geometry = None
    tail: deque[str] = deque(maxlen=40)
    final_id = None
    final_te = None
    final_ts = None
    with gzip.open(sim, "rt") as handle:
        for line in handle:
            stripped = line.strip()
            if line.startswith("Geometry") and header_geometry is None:
                header_geometry = line.split(maxsplit=1)[1].strip()
            elif line.startswith("Seed") and header_seed is None:
                header_seed = int(line.split()[1])
            if stripped:
                tail.append(stripped)
    for line in tail:
        if line.startswith("ID "):
            final_id = int(line.split()[1])
        elif line.startswith("TE "):
            final_te = float(line.split()[1])
        elif line.startswith("TS "):
            final_ts = int(line.split()[1])
    expected_events = int(runner.EVENTS_PER_SHARD)
    if header_seed != expected_seed or header_geometry != expected_geometry:
        raise RuntimeError("SIM header seed/geometry mismatch")
    tail_lines = list(tail)
    if not tail_lines or tail_lines[-3:] != ["EN", f"TE {final_te:.6f}", f"TS {expected_events}"]:
        raise RuntimeError(f"SIM terminal closure differs: {tail_lines[-6:]}")
    if final_id != expected_events or final_ts != expected_events or not (final_te and final_te > 0):
        raise RuntimeError("SIM terminal event/time closure differs")

    result = {
        "schema_version": 1,
        "status": "PASS",
        "job_id": p["job_id"],
        "index": index,
        "source_seed": expected_seed,
        "sim_header_seed": header_seed,
        "events_requested": expected_events,
        "returncode": 0,
        "wall_seconds": None,
        "geometry": expected_geometry,
        "header_geometry": header_geometry,
        "source": str(source),
        "source_sha256": sha256(source),
        "sim": str(sim),
        "sim_bytes": sim.stat().st_size,
        "sim_sha256": sha256(sim),
        "activation": str(activation),
        "stderr": str(p["stderr"]),
        "started_unix": None,
        "ended_unix": None,
        "receipt_recovery": {
            "reason": "launcher session interrupted after Cosima completed but before receipt write",
            "gzip_crc_pass": True,
            "final_event_id": final_id,
            "terminal_TE_s": final_te,
            "terminal_TS": final_ts,
        },
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
