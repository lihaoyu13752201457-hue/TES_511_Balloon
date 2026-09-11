#!/usr/bin/env python3
"""Execute the declared SH3 G4CMP scenario matrix for one prepared chunk set."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/neutron_fen")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunk_dir", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--scenario", action="append", help="run only named scenario(s)")
    parser.add_argument("--packets-scale", type=float, default=1.0)
    parser.add_argument("--seed-offset", type=int, default=0)
    args = parser.parse_args()
    config = json.loads((WORKSPACE / "config/staircase_scenarios.json").read_text())
    selected = set(args.scenario or [])
    ran = 0
    for scenario in config["scenarios"]:
        if selected and scenario["name"] not in selected:
            continue
        packets = max(1, round(scenario["packets_per_group"] * args.packets_scale))
        command = [
            sys.executable, str(WORKSPACE / "code/run_g4cmp_chunked.py"),
            str(args.chunk_dir), str(args.output_root / scenario["name"]),
            "--packets-per-group", str(packets),
            "--packet-energy-meV", str(scenario["packet_energy_meV"]),
            "--sensor-area-scale", str(scenario["sensor_area_scale"]),
            "--sensor-absorption", str(scenario["sensor_absorption"]),
            "--bath-absorption", str(scenario["bath_absorption"]),
            "--specular-probability", str(scenario["specular_probability"]),
            "--seed1", str(240903 + args.seed_offset),
            "--seed2", str(511420 + 3 * args.seed_offset),
        ]
        print(f"RUN {scenario['name']} packets/group={packets}", flush=True)
        subprocess.run(command, check=True)
        ran += 1
    if ran == 0:
        raise SystemExit("no scenario selected")


if __name__ == "__main__":
    main()
