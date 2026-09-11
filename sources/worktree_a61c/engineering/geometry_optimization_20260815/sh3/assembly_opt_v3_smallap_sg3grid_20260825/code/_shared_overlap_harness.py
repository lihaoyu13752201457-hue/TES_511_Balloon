#!/usr/bin/env python3
"""Construct the full SH3 assembly and check overlaps without particle transport."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
GEOMETRY = PACKAGE / "geometry"
AUDIT = PACKAGE / "audit"
DATA = PACKAGE / "data"
SETUP = GEOMETRY / "SH3_Assembly.geo.setup"
GEO = GEOMETRY / "SH3_Assembly.geo"
DET = GEOMETRY / "SH3_Assembly.det"
MATERIALS = GEOMETRY / "Materials_SH3_Assembly.geo"
MANIFEST = DATA / "assembly_manifest.json"
STATIC = AUDIT / "assembly_static_validation.json"
OUTPUT = AUDIT / "assembly_overlap_validation.json"
LOG = AUDIT / "assembly_overlap_cosima.log"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
GEANT4 = MEGALIB / "external/geant4_v10.02.p03"
G4DATA = GEANT4 / "share/Geant4-10.2.3/data"

BAD_PATTERNS = (
    "Overlap is detected",
    "Overlap with volume",
    "overlapping by",
    "CheckOverlaps()",
    "GeomVol1002",
    "GeomVol1003",
    "G4Exception",
    "*** Error",
    "*** Fatal",
    "Fatal Exception",
    "COSIMA-ERROR:",
    "Unable to initalize detector",
    "Unable to initialize detector",
    "Segmentation fault",
    "Aborted",
    "Killed",
)

TRANSPORT_PATTERNS = (
    re.compile(r"Total number of generated particles:\s*\d+", re.I),
    re.compile(r"Summary for run\s+", re.I),
    re.compile(r"/run/beamOn", re.I),
    re.compile(r"StartBeam", re.I),
    re.compile(r"###\s*Run\s+\d+\s+start", re.I),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def environment() -> dict[str, str]:
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


def source_text(scratch: Path) -> str:
    return "\n".join(
        (
            "Version 1",
            f"Geometry {SETUP.resolve()}",
            "CheckForOverlaps 10000 0.0001",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo init-only",
            "",
            "# Parser scaffold only; interactive mode exits before StartBeam.",
            "Run AssemblyGeometryOnly",
            f"AssemblyGeometryOnly.FileName {scratch / 'parser_init_empty'}",
            "AssemblyGeometryOnly.NEvents 1",
            "AssemblyGeometryOnly.Source AssemblyGeometryOnlySource",
            "AssemblyGeometryOnlySource.ParticleType 1",
            "AssemblyGeometryOnlySource.Beam PointSource 0 0 0",
            "AssemblyGeometryOnlySource.Spectrum Mono 511",
            "AssemblyGeometryOnlySource.Flux 1.0",
            "",
        )
    )


def inspect_sim(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    events = [line for line in text.splitlines() if re.match(r"^(?:SE|IA|HT|GR|PM)\s", line)]
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "event_record_line_count": len(events),
    }


def verify_authority() -> dict[str, dict[str, object]]:
    core = (SETUP, GEO, DET, MATERIALS)
    required = core + (MANIFEST, STATIC, COSIMA)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing assembly prerequisite(s): {missing}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    static = json.loads(STATIC.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS__SH3_ASSEMBLY_BUILT":
        raise RuntimeError("assembly manifest is not PASS")
    if static.get("status") != "PASS__SH3_ASSEMBLY_STATIC":
        raise RuntimeError("assembly static validation is not PASS")
    records: dict[str, dict[str, object]] = {}
    stale: list[str] = []
    for path in core:
        current = sha256(path)
        expected = manifest.get("outputs", {}).get(path.name, {}).get("sha256")
        if current != expected:
            stale.append(path.name)
        records[path.name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": current,
            "manifest_sha256": expected,
        }
    if stale:
        raise RuntimeError(f"assembly manifest stale for: {stale}")
    return records


def main() -> int:
    started = dt.datetime.now(dt.timezone.utc)
    report: dict[str, Any] = {
        "status": "FAIL",
        "component_identity": "SH3_Chimney_DR_Assembly",
        "started_at_utc": started.isoformat(),
        "transport_launched": False,
        "check_for_overlaps": {"samples": 10000, "tolerance_cm": 0.0001},
        "evidence_role": "Full assembled geometry construction/overlap audit only; no physics claim.",
    }
    log_text = ""
    try:
        authority = verify_authority()
        with tempfile.TemporaryDirectory(prefix="sh3_assembly_overlap_", dir="/tmp") as temporary:
            scratch = Path(temporary)
            card = scratch / "assembly_overlap_no_transport.source"
            card_text = source_text(scratch)
            card.write_text(card_text, encoding="utf-8")
            command = [str(COSIMA), "-i", "-u", str(card)]
            completed = subprocess.run(
                command,
                cwd=scratch,
                env=environment(),
                input="exit\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=1800,
                check=False,
            )
            log_text = completed.stdout.replace("\r\n", "\n").replace("\r", "\n")
            sims = [inspect_sim(path) for path in sorted(scratch.glob("*.sim*"))]
            bad_lines = [
                line for line in log_text.splitlines() if any(pattern in line for pattern in BAD_PATTERNS)
            ]
            transport_lines = [
                line
                for line in log_text.splitlines()
                if any(pattern.search(line) for pattern in TRANSPORT_PATTERNS)
            ]
            checks = {
                "authority_current": True,
                "cosima_returncode_zero": completed.returncode == 0,
                "exact_overlap_directive": card_text.count("CheckForOverlaps 10000 0.0001") == 1,
                "beam_on_absent": "/run/beamOn" not in card_text,
                "geometry_stage12_complete": "Stage 12 (volume tree optimization) finished" in log_text,
                "geant4_constructed": "Geant4 version Name: geant4-10-02-patch-03" in log_text,
                "interactive_idle_exit_seen": "Idle>" in log_text and "Visualization Manager deleting..." in log_text,
                "overlap_bad_lines_absent": not bad_lines,
                "transport_markers_absent": not transport_lines,
                "generated_particle_summary_absent": "Total number of generated particles:" not in log_text,
                "event_payload_absent": all(item["event_record_line_count"] == 0 for item in sims),
            }
            status = "PASS__SH3_ASSEMBLY_OVERLAP_NO_TRANSPORT" if all(checks.values()) else "FAIL"
            report.update(
                {
                    "status": status,
                    "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "command": command,
                    "source_card": {
                        "sha256": sha256_bytes(card_text.encode("utf-8")),
                        "text": card_text,
                    },
                    "source_authority": authority,
                    "checks": checks,
                    "bad_lines": bad_lines[:200],
                    "transport_lines": transport_lines[:200],
                    "initialized_sim_artifacts": sims,
                    "returncode": completed.returncode,
                }
            )
    except Exception as exc:
        report["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    atomic_text(LOG, log_text)
    report["log"] = {
        "path": str(LOG),
        "bytes": len(log_text.encode("utf-8")),
        "sha256": sha256_bytes(log_text.encode("utf-8")),
        "line_count": len(log_text.splitlines()),
    }
    atomic_json(OUTPUT, report)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT)}, indent=2))
    return 0 if report["status"] == "PASS__SH3_ASSEMBLY_OVERLAP_NO_TRANSPORT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
