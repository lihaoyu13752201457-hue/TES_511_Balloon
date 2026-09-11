#!/usr/bin/env python3
"""Run Step11 upstream-optics smoke simulations and summarize closure evidence."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STEP = ROOT / "stepwise_maintenance" / "step11_upstream_optics_background"
META = STEP / "smoke_geometry" / "step11_smoke_input_summary.json"
COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"


def parse_log(text: str) -> dict:
    generated = re.search(r"Total number of generated particles:\s+(\d+)", text)
    cpu = re.search(r"Total CPU time spent in run:\s+([0-9.eE+-]+)\s+sec", text)
    per_event = re.search(r"Time spent per event:\s+([0-9.eE+-]+)\s+sec", text)
    obs = re.search(r"Observation time:\s+([0-9.eE+-]+)\s+sec", text)
    stored = len(re.findall(r"^Storing event ", text, flags=re.MULTILINE))
    return {
        "generated_particles": int(generated.group(1)) if generated else None,
        "stored_event_lines": stored,
        "cpu_seconds": float(cpu.group(1)) if cpu else None,
        "seconds_per_event": float(per_event.group(1)) if per_event else None,
        "observation_seconds": float(obs.group(1)) if obs else None,
        "outside_world_messages": len(re.findall(r"outside world volume", text, flags=re.IGNORECASE)),
        "exception_messages": len(re.findall(r"\bException\b|\bERROR\b|Fatal error", text)),
    }


def source_stem(source: Path) -> str:
    return source.name.removesuffix(".source")


def run_one(label: str, source: Path, run_dir: Path, log_dir: Path) -> dict:
    stem = source_stem(source)
    log_path = log_dir / f"{stem}.log"
    proc = subprocess.run(
        [COSIMA, str(source.relative_to(ROOT))],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log_path.write_text(proc.stdout)
    parsed = parse_log(proc.stdout)
    sim_files = sorted(str(p.relative_to(ROOT)) for p in run_dir.glob(f"{stem}*.sim.gz"))
    isotope_files = sorted(str(p.relative_to(ROOT)) for p in run_dir.glob(f"{stem}*.isotopes*"))
    return {
        "label": label,
        "source": str(source.relative_to(ROOT)),
        "returncode": proc.returncode,
        "log": str(log_path.relative_to(ROOT)),
        "sim_files": sim_files,
        "isotope_files": isotope_files,
        **parsed,
    }


def main() -> None:
    metadata = json.loads(META.read_text())
    run_dir = ROOT / metadata["run_dir"]
    log_dir = run_dir / "logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for particle, source in metadata["source_cards"].items():
        runs.append((f"expacs_{particle}", ROOT / source))
    runs.append(("forced_activation", ROOT / metadata["forced_activation_source"]))

    results = []
    for label, source in runs:
        print(f"[step11] running {label}: {source.relative_to(ROOT)}", flush=True)
        result = run_one(label, source, run_dir, log_dir)
        print(
            "[step11] done {label}: rc={rc} generated={gen} outside_world={ow} sim_files={sim} isotopes={iso}".format(
                label=label,
                rc=result["returncode"],
                gen=result["generated_particles"],
                ow=result["outside_world_messages"],
                sim=len(result["sim_files"]),
                iso=len(result["isotope_files"]),
            ),
            flush=True,
        )
        results.append(result)

    summary = {
        "status": "PASS" if all(r["returncode"] == 0 for r in results) else "FAIL",
        "input_metadata": str(META.relative_to(ROOT)),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "results": results,
    }
    out = run_dir / "step11_smoke_run_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
