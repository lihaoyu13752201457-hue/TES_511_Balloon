#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTICSIM_RUN = Path("/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    commands = _commands(skip_tests=args.skip_tests)
    if args.dry_run:
        print(json.dumps({"commands": commands}, indent=2))
        return 0

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("MPLCONFIGDIR", "/tmp")
    for command in commands:
        print("+ " + " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    return 0


def _commands(skip_tests: bool) -> list[list[str]]:
    phase = str(OPTICSIM_RUN / "phase_space.csv")
    transmitted = str(OPTICSIM_RUN / "transmitted_space.csv")
    history = str(OPTICSIM_RUN / "optics_history.csv")
    commands = [
        [
            "python3",
            "tools/compare_geant4_vs_reference.py",
            "--geant4-run",
            str(OPTICSIM_RUN),
            "--out",
            "reports/geant4_current_crosscheck",
        ],
        ["python3", "tools/audit_focal_convention.py"],
        [
            "python3",
            "tools/audit_cosima_bridge.py",
            "--input",
            phase,
            "--history",
            history,
            "--out-dir",
            "reports/cosima_bridge_current_audit",
        ],
        [
            "python3",
            "tools/audit_cosima_bridge.py",
            "--input",
            transmitted,
            "--history",
            history,
            "--out-dir",
            "reports/cosima_bridge_transmitted_current_audit",
        ],
        ["python3", "tools/audit_full_lens_observables.py"],
        ["python3", "tools/build_python_full_lens_reference.py"],
        ["python3", "tools/export_external_lens_request.py"],
        ["python3", "tools/audit_external_lens_handoff.py"],
        ["python3", "tools/import_opticsim_baselines.py"],
        ["python3", "tools/generate_crystalpy_curve.py"],
        ["python3", "tools/build_bfull_rocking_curve_map_status.py"],
        ["python3", "tools/build_validation_summary.py"],
        ["python3", "tools/audit_workspace.py"],
    ]
    if not skip_tests:
        commands.append(["python3", "-m", "unittest", "discover", "-s", "tests"])
    return commands


if __name__ == "__main__":
    raise SystemExit(main())
