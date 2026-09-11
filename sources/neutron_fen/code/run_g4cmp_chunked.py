#!/usr/bin/env python3
"""Run one deterministic chunked SH3 G4CMP scenario and merge its products."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/neutron_fen")
EXE = WORKSPACE / "build/g4cmp_si_tes/sh3_g4cmp_si_tes"
PIXELS = WORKSPACE / "outputs/tes_pixel_map.csv"


def inside(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORKSPACE)
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunk_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--packets-per-group", type=int, required=True)
    parser.add_argument("--packet-energy-meV", type=float, required=True)
    parser.add_argument("--sensor-area-scale", type=float, required=True)
    parser.add_argument("--sensor-absorption", type=float, required=True)
    parser.add_argument("--bath-absorption", type=float, required=True)
    parser.add_argument("--specular-probability", type=float, default=0.0)
    parser.add_argument("--max-phonon-bounces", type=int, default=20000)
    parser.add_argument("--seed1", type=int, default=240903)
    parser.add_argument("--seed2", type=int, default=511420)
    args = parser.parse_args()

    args.chunk_dir = args.chunk_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    if not inside(args.chunk_dir) or not inside(args.output_dir):
        raise SystemExit("all paths must be inside /home/ubuntu/neutron_fen")
    for needed in ("G4CMPINSTALL", "G4LATTICEDATA", "Geant4_DIR"):
        if not os.environ.get(needed):
            raise SystemExit(f"missing {needed}; source {WORKSPACE / 'env/g4cmp.sh'} first")
    chunks = sorted(args.chunk_dir.glob("chunk_*.csv"))
    if not chunks:
        raise SystemExit(f"no chunk CSVs in {args.chunk_dir}")

    run_dirs = []
    for index, input_csv in enumerate(chunks, start=1):
        run_dir = args.output_dir / "chunks" / f"chunk_{index:03d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        seed1 = args.seed1 + 101 * index
        seed2 = args.seed2 + 211 * index
        command = [
            str(EXE), "--input", str(input_csv), "--pixels", str(PIXELS),
            "--output", str(run_dir / "hits.csv"),
            "--event-map", str(run_dir / "event_map.csv"),
            "--summary", str(run_dir / "summary.json"),
            "--packets-per-group", str(args.packets_per_group),
            "--packet-energy-meV", str(args.packet_energy_meV),
            "--sensor-area-scale", str(args.sensor_area_scale),
            "--sensor-absorption", str(args.sensor_absorption),
            "--bath-absorption", str(args.bath_absorption),
            "--specular-probability", str(args.specular_probability),
            "--max-phonon-bounces", str(args.max_phonon_bounces),
            "--seed1", str(seed1), "--seed2", str(seed2),
        ]
        with (run_dir / "run.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            raise SystemExit(f"chunk {index} failed with exit {result.returncode}: {run_dir}")
        summary = json.loads((run_dir / "summary.json").read_text())
        if summary.get("status") != "COMPLETE" or abs(summary["energy_eV"]["closure_fraction"] - 1) > 1e-9:
            raise SystemExit(f"chunk {index} failed output validation: {run_dir}")
        run_dirs.append(run_dir)
        print(f"PASS chunk {index}/{len(chunks)}", flush=True)

    subprocess.run(
        [sys.executable, str(WORKSPACE / "code/merge_g4cmp_chunks.py"),
         str(args.output_dir), *(str(path) for path in run_dirs)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(WORKSPACE / "code/analyze_g4cmp_runs.py"),
         str(args.output_dir)],
        check=True,
    )


if __name__ == "__main__":
    main()
