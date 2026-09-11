#!/usr/bin/env python3
"""Run and record the authoritative Cosima load/overlap smoke for S3d."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
GEOMETRY = WORK / "geometry"
DATA = WORK / "data"
VALIDATION = WORK / "validation"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

SOURCE = GEOMETRY / "overlap_check_s3d.source"
SETUP = GEOMETRY / f"{STEM}.geo.setup"
GEO = GEOMETRY / f"{STEM}.geo"
DET = GEOMETRY / f"{STEM}.det"
LOG = VALIDATION / "cosima_overlap_s3d.log"
SUMMARY = DATA / "cosima_overlap_s3d_summary.json"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
GEANT4 = MEGALIB / "external/geant4_v10.02.p03"
G4DATA = GEANT4 / "share/Geant4-10.2.3/data"

BAD_PATTERNS = (
    "Overlap is detected",
    "Overlap with volume",
    "overlapping by",
    "CheckOverlaps()",
    "GeomVol",
    "G4Exception",
    "*** Error",
    "*** Fatal",
    "Fatal Exception",
    "error while loading shared libraries",
    "cannot open shared object",
    "Segmentation fault",
    "Aborted",
    "Killed",
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cosima_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["MEGALIB"] = str(MEGALIB)
    env["LD_LIBRARY_PATH"] = ":".join(
        part
        for part in (
            str(MEGALIB / "lib"),
            str(MEGALIB / "external/root_v6.36.6/lib"),
            str(GEANT4 / "lib"),
            env.get("LD_LIBRARY_PATH", ""),
        )
        if part
    )
    env["PATH"] = f"{MEGALIB / 'bin'}:{env.get('PATH', '')}"
    env.update(
        {
            "G4NEUTRONHPDATA": str(G4DATA / "G4NDL4.5"),
            "G4LEDATA": str(G4DATA / "G4EMLOW6.48"),
            "G4LEVELGAMMADATA": str(G4DATA / "PhotonEvaporation3.2"),
            "G4RADIOACTIVEDATA": str(G4DATA / "RadioactiveDecay4.3.2"),
            "G4NEUTRONXSDATA": str(G4DATA / "G4NEUTRONXS1.4"),
            "G4PIIDATA": str(G4DATA / "G4PII1.3"),
            "G4REALSURFACEDATA": str(G4DATA / "RealSurface1.0"),
            "G4SAIDXSDATA": str(G4DATA / "G4SAIDDATA1.1"),
            "G4ABLADATA": str(G4DATA / "G4ABLA3.0"),
            "G4ENSDFSTATEDATA": str(G4DATA / "G4ENSDFSTATE1.2.3"),
        }
    )
    return env


def main() -> int:
    required = (SOURCE, SETUP, GEO, DET, COSIMA)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing overlap prerequisite(s): {missing}")

    VALIDATION.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    command = [str(COSIMA), str(SOURCE.resolve())]
    started = dt.datetime.now(dt.timezone.utc)
    captured: list[str] = []

    with LOG.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=cosima_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            captured.append(line)
            log.write(line)
            sys.stdout.write(line)
        returncode = process.wait()

    text = "".join(captured)
    bad_lines = [
        line
        for line in text.splitlines()
        if any(pattern in line for pattern in BAD_PATTERNS)
    ]
    generated_match = re.search(
        r"Total number of generated particles:\s*(\d+)", text
    )
    generated = int(generated_match.group(1)) if generated_match else None
    parameter_file_match = (
        f"Using parameter file {SOURCE.resolve()}" in text
        or f"Using parameter file {SOURCE.resolve().relative_to(ROOT)}" in text
    )
    run_summary_present = "Summary for run Minimum" in text
    stages_complete = "Stage 12 (volume tree optimization) finished" in text
    status = (
        "PASS"
        if returncode == 0
        and not bad_lines
        and parameter_file_match
        and generated == 1
        and run_summary_present
        and stages_complete
        else "FAIL"
    )

    summary = {
        "status": status,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": command,
        "returncode": returncode,
        "check_for_overlaps": {"samples": 10000, "tolerance_cm": 0.0001},
        "bad_patterns": list(BAD_PATTERNS),
        "bad_lines": bad_lines[:50],
        "generated_particles": generated,
        "parameter_file_match": parameter_file_match,
        "run_summary_present": run_summary_present,
        "geometry_stage12_complete": stages_complete,
        "files": {
            "source": {"path": rel(SOURCE), "sha256": sha256(SOURCE)},
            "setup": {"path": rel(SETUP), "sha256": sha256(SETUP)},
            "geo": {"path": rel(GEO), "sha256": sha256(GEO)},
            "det": {"path": rel(DET), "sha256": sha256(DET)},
            "log": {"path": rel(LOG), "sha256": sha256(LOG)},
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "summary": rel(SUMMARY)}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
