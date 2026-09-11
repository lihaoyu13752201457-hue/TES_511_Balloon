#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def detector_demo_path() -> Path:
    candidates = [
        Path("/tmp/opticsim-build-g4-11.4.0/detector_only_demo"),
        Path("/tmp/opticsim-build/detector_only_demo"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("detector_only_demo is not built in /tmp/opticsim-build-g4-11.4.0 or /tmp/opticsim-build")


def demo_env(demo: Path) -> dict[str, str]:
    env = dict(os.environ)
    if "opticsim-build-g4-11.4.0" in str(demo):
        for key in list(env):
            if key.startswith("G4") or key == "GEANT4_DATA_DIR":
                env.pop(key, None)
        lib = "/home/ubuntu/software/geant4-11.4.0-install/lib"
        env["LD_LIBRARY_PATH"] = lib + ":" + env.get("LD_LIBRARY_PATH", "")
        env["PATH"] = "/home/ubuntu/software/geant4-11.4.0-install/bin:" + env.get("PATH", "")
        env["GEANT4_DATA_DIR"] = "/home/ubuntu/software/geant4-11.4.0-install/share/Geant4/data"
    return env


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ensure_all_diffract_source(phase_space: Path, n: int) -> None:
    if phase_space.exists():
        return
    subprocess.run(
        [
            sys.executable,
            "analysis/test_laue_fake_table_no_double_absorption.py",
            "--n",
            str(n),
            "--run-dir",
            str(phase_space.parents[0].parents[0]),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regression for Laue all-diffract detector handoff.")
    parser.add_argument(
        "--phase-space",
        default="runs/laue_fake_table_no_double_absorption_regression/all_diffract/phase_space.csv",
    )
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--run-dir", default="runs/laue_all_diffract_detector_handoff")
    parser.add_argument(
        "--out",
        default="records/2026-05-24_optics_evidence_gap_closure/laue/laue_all_diffract_detector_handoff_regression.md",
    )
    args = parser.parse_args()

    phase_space = Path(args.phase_space)
    ensure_all_diffract_source(phase_space, args.n)
    detector = detector_demo_path()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    phase_rows = read_csv(phase_space)
    if not phase_rows:
        raise RuntimeError(f"phase-space source has no rows: {phase_space}")
    n_to_run = min(args.n, len(phase_rows))
    completed = subprocess.run(
        [str(detector), str(phase_space), str(run_dir), str(n_to_run), str(args.seed)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=demo_env(detector),
    )
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    event_rows = read_csv(run_dir / "event_summary.csv")

    sys.path.insert(0, str(ROOT))
    from external_baseline.io_contract_py.io_contract import validate_run_contract

    contract = validate_run_contract(
        phase_space=phase_space,
        hits=run_dir / "hits.csv",
        event_summary=run_dir / "event_summary.csv",
    )
    checks = {
        "phase_rows_equal_fake_all_diffract_n": len(phase_rows) == args.n,
        "detector_n_input_matches_phase_rows": summary.get("n_input_photons") == len(phase_rows),
        "detector_n_simulated_matches_requested": summary.get("n_simulated") == n_to_run,
        "detector_events_written_matches_requested": summary.get("n_events_written") == n_to_run,
        "event_summary_rows_match_requested": len(event_rows) == n_to_run,
        "source_detector_contract_passes": bool(contract["ok"]),
    }
    overall = all(checks.values())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_path.with_suffix(".json")
    payload = {
        "overall": overall,
        "checks": checks,
        "phase_space": str(phase_space),
        "detector_demo": str(detector),
        "run_dir": str(run_dir),
        "n_phase_rows": len(phase_rows),
        "n_requested": n_to_run,
        "detector_summary": summary,
        "contract": contract,
        "detector_stdout_tail": completed.stdout.strip().splitlines()[-20:],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Laue all-diffract detector-handoff regression",
        "",
        f"- phase_space: `{phase_space}`",
        f"- detector_demo: `{detector}`",
        f"- run_dir: `{run_dir}`",
        f"- n_phase_rows: {len(phase_rows)}",
        f"- n_requested: {n_to_run}",
        f"- summary_json: `{json_path}`",
        f"- overall_status: **{'PASS' if overall else 'FAIL'}**",
        "",
        "## Checks",
        "",
        "| check | status |",
        "|---|---|",
        *[f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in checks.items()],
        "",
        "## Detector summary",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| n_input_photons | {summary.get('n_input_photons')} |",
        f"| n_simulated | {summary.get('n_simulated')} |",
        f"| n_events_written | {summary.get('n_events_written')} |",
        f"| event_summary_rows | {len(event_rows)} |",
        f"| n_hits | {summary.get('n_hits')} |",
        "",
        "## Interpretation",
        "",
        "- The fake Laue table forces all optics decisions into `DIFFRACT`, so every input primary should produce one focused phase-space photon.",
        "- The detector-only handoff consumes the standard phase-space columns and writes one event summary per requested photon.",
        "- This guards against dropping Laue diffracted photons through parent-ID assumptions or schema filters at the optics-detector boundary.",
        "- It does not validate detector material response fidelity; it validates handoff completeness and IO contract compatibility.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
