#!/usr/bin/env python3
"""Summarize completed Cosima smoke-test logs and SIM outputs."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RUNS = [
    {
        "name": "science511_focalbeam_smoke1k",
        "log": "reports/cosima_science511_smoke1k.log",
        "sim": "science_511_onaxis_source/Science_511_onaxis_focalbeam_smoke1k.inc1.id1.sim.gz",
        "expected_generated": 1000,
    },
    {
        "name": "fullsphere_static_smoke1k",
        "log": "reports/cosima_fullsphere_static_smoke1k.log",
        "sim": "expacs_fullsphere_20bin_sources/Background_atm_fullsphere_allparticles_20bins_smoke1k.sim.inc1.id1.sim.gz",
        "expected_generated": 1000,
    },
    {
        "name": "fullsphere_lightcurve_smoke100",
        "log": "reports/cosima_fullsphere_lightcurve_smoke100.log",
        "sim": "time_variable_balloon_background_curves_verified/Background_atm_fullsphere_allparticles_20bins_lightcurve_smoke100.sim.inc1.id1.sim.gz",
        "expected_generated": 100,
    },
    {
        "name": "delayfix_smoke1k",
        "log": "reports/cosima_delayfix_smoke1k.log",
        "sim": "delay_fix/DelayedDecayRPIPGroundStateFixedSmoke1k.inc1.id1.sim.gz",
        "expected_generated": 1000,
    },
]


def parse_log(path: Path) -> dict:
    text = path.read_text(errors="replace")
    generated_match = re.search(r"Total number of generated particles:\s+(\d+)", text)
    cpu_match = re.search(r"Total CPU time spent in run:\s+([0-9.eE+-]+) sec", text)
    obs_match = re.search(r"Observation time:\s+([0-9.eE+-]+) sec", text)
    return {
        "log_exists": path.exists(),
        "has_error": "***  Error" in text or "Unable to parse" in text,
        "generated_particles": int(generated_match.group(1)) if generated_match else None,
        "cpu_s": float(cpu_match.group(1)) if cpu_match else None,
        "observation_time_s": float(obs_match.group(1)) if obs_match else None,
    }


def parse_sim(path: Path) -> dict:
    event_count = 0
    htsim_count = 0
    tes_480_550_events = 0
    current_has_window = False
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if line.startswith("SE"):
                if event_count > 0 and current_has_window:
                    tes_480_550_events += 1
                current_has_window = False
            elif line.startswith("ID "):
                event_count += 1
            elif line.startswith("HTsim"):
                htsim_count += 1
                parts = [p.strip() for p in line.split(";")]
                if len(parts) >= 5:
                    try:
                        energy = float(parts[4])
                        if 480.0 <= energy <= 550.0:
                            current_has_window = True
                    except ValueError:
                        pass
        if event_count > 0 and current_has_window:
            tes_480_550_events += 1
    return {
        "sim_exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "event_count": event_count,
        "htsim_count": htsim_count,
        "tes_480_550_events": tes_480_550_events,
    }


def main() -> int:
    rows = []
    for run in RUNS:
        log = parse_log(ROOT / run["log"])
        sim = parse_sim(ROOT / run["sim"])
        status = "PASS"
        details = []
        if log["has_error"]:
            status = "FAIL"
            details.append("log has parse/runtime error")
        if log["generated_particles"] != run["expected_generated"]:
            status = "FAIL"
            details.append(f"generated={log['generated_particles']} expected={run['expected_generated']}")
        if sim["event_count"] <= 0:
            status = "FAIL"
            details.append("no events in sim")
        row = {
            "name": run["name"],
            "status": status,
            "details": "; ".join(details) if details else "completed",
            **log,
            **sim,
        }
        rows.append(row)

    outdir = ROOT / "reports"
    outdir.mkdir(exist_ok=True)
    (outdir / "cosima_smoke_summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = ["# Cosima Smoke Summary", ""]
    for r in rows:
        lines.append(
            f"- {r['status']}: {r['name']} - generated={r['generated_particles']}, "
            f"events={r['event_count']}, HTsim={r['htsim_count']}, "
            f"TES480_550_events={r['tes_480_550_events']}, obs_s={r['observation_time_s']}"
        )
    (outdir / "cosima_smoke_summary.md").write_text("\n".join(lines) + "\n")

    for r in rows:
        print(f"{r['status']:5} {r['name']}: {r['details']}")
    return 1 if any(r["status"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())

