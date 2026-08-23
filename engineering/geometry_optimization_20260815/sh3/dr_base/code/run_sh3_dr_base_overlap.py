#!/usr/bin/env python3
"""Construct the SH3 pure-DR base and audit overlaps without transport."""

from __future__ import annotations

import argparse
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
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"

SETUP = GEOMETRY / "SH3_PureDR_Base.geo.setup"
GEO = GEOMETRY / "SH3_PureDR_Base.geo"
MATERIALS = GEOMETRY / "Materials_SH3_DR_Base.geo"
MANIFEST = DATA / "dr_base_manifest.json"
STATIC = AUDIT / "dr_base_static_validation.json"
DEFAULT_OUTPUT = AUDIT / "dr_base_overlap_validation.json"
DEFAULT_LOG = AUDIT / "dr_base_overlap_cosima.log"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
DEFAULT_COSIMA = MEGALIB / "bin/cosima"
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
    "error while loading shared libraries",
    "Unable to initalize detector",
    "Unable to initialize detector",
    "Segmentation fault",
    "Aborted",
    "Killed",
)

TRANSPORT_PATTERNS = (
    re.compile(r"Total number of generated particles:\s*\d+", re.IGNORECASE),
    re.compile(r"Summary for run\s+", re.IGNORECASE),
    re.compile(r"/run/beamOn", re.IGNORECASE),
    re.compile(r"StartBeam", re.IGNORECASE),
    re.compile(r"###\s*Run\s+\d+\s+start", re.IGNORECASE),
)

EVENT_SUFFIXES = (".sim", ".sim.gz", ".tra", ".tra.gz", ".evta", ".evta.gz")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
            "# Parser-only placeholder; interactive mode exits before StartBeam.",
            "Run GeometryConstructOnly",
            f"GeometryConstructOnly.FileName {scratch / 'parser_init_empty'}",
            "GeometryConstructOnly.NEvents 1",
            "GeometryConstructOnly.Source GeometryConstructOnlySource",
            "GeometryConstructOnlySource.ParticleType 1",
            "GeometryConstructOnlySource.Beam PointSource 0 0 0",
            "GeometryConstructOnlySource.Spectrum Mono 511",
            "GeometryConstructOnlySource.Flux 1.0",
            "",
        )
    )


def artifact_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and any(path.name.lower().endswith(suffix) for suffix in EVENT_SUFFIXES)
    )


def artifact_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    event_lines = [line for line in text.splitlines() if re.match(r"^(?:SE|IA|HT|GR|PM)\s", line)]
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "event_record_line_count": len(event_lines),
        "head": text.splitlines()[:30],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cosima", type=Path, default=DEFAULT_COSIMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    output = args.output.resolve()
    log_path = args.log.resolve()
    cosima = args.cosima.resolve()
    report: dict[str, Any] = {
        "component_identity": "SH3_PureDR_Base",
        "status": "FAIL",
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "transport_launched": False,
        "check_for_overlaps": {"samples": 10000, "tolerance_cm": 0.0001},
        "evidence_role": (
            "Standalone pure-DR construct/overlap evidence only; chimney assembly and physics remain unknown."
        ),
    }
    log_text = ""
    try:
        required = (SETUP, GEO, MATERIALS, MANIFEST, STATIC, cosima)
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"missing pure-DR overlap prerequisite(s): {missing}")
        if args.timeout_seconds <= 0:
            raise ValueError("--timeout-seconds must be positive")

        static = json.loads(STATIC.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if static.get("status") != "PASS__SH3_PURE_DR_BASE_STATIC":
            raise RuntimeError("pure-DR static validation is not PASS")
        if manifest.get("status") != "PASS__SH3_PURE_DR_BASE_BUILT":
            raise RuntimeError("pure-DR manifest is not PASS")
        core = (SETUP, GEO, MATERIALS)
        current_hashes = {path.name: sha256(path) for path in core}
        stale = [
            name
            for name, current in current_hashes.items()
            if manifest.get("outputs", {}).get(name, {}).get("sha256") != current
        ]
        if stale:
            raise RuntimeError(f"pure-DR manifest is stale for: {stale}")

        with tempfile.TemporaryDirectory(prefix="sh3_dr_base_overlap_", dir="/tmp") as temporary:
            scratch = Path(temporary)
            card = scratch / "pure_dr_construct_overlap_no_transport.source"
            card_text = source_text(scratch)
            card.write_text(card_text, encoding="utf-8")
            exact_overlap = card_text.count("CheckForOverlaps 10000 0.0001") == 1
            no_beam_on = re.search(r"^\s*/run/beamOn\b", card_text, re.I | re.M) is None
            before = set(artifact_paths(scratch))
            command = [str(cosima), "-i", "-u", str(card)]
            try:
                completed = subprocess.run(
                    command,
                    cwd=scratch,
                    env=environment(),
                    input="exit\n",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    timeout=args.timeout_seconds,
                    check=False,
                )
                returncode: int | None = completed.returncode
                timed_out = False
                log_text = completed.stdout.replace("\r\n", "\n").replace("\r", "\n")
            except subprocess.TimeoutExpired as exc:
                returncode = None
                timed_out = True
                raw = exc.stdout or ""
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                log_text = raw.replace("\r\n", "\n").replace("\r", "\n")

            new_artifacts = sorted(set(artifact_paths(scratch)) - before)
            artifacts = [artifact_record(path) for path in new_artifacts]
            no_event_payload = all(record["event_record_line_count"] == 0 for record in artifacts)
            bad_lines = [
                line for line in log_text.splitlines() if any(pattern in line for pattern in BAD_PATTERNS)
            ]
            transport_lines = [
                line
                for line in log_text.splitlines()
                if any(pattern.search(line) for pattern in TRANSPORT_PATTERNS)
            ]
            generated = re.search(r"Total number of generated particles:\s*(\d+)", log_text)
            checks = {
                "static_and_manifest_pass_current": True,
                "cosima_returncode_zero": returncode == 0,
                "not_timed_out": not timed_out,
                "geometry_stage12_complete": "Stage 12 (volume tree optimization) finished" in log_text,
                "geant4_constructed": "Geant4 version Name: geant4-10-02-patch-03" in log_text,
                "interactive_started": "Starting interactive mode!" in log_text,
                "idle_exit_seen": "Idle>" in log_text and "Visualization Manager deleting..." in log_text,
                "exact_overlap_directive": exact_overlap,
                "bad_overlap_error_lines_absent": not bad_lines,
                "transport_markers_absent": not transport_lines,
                "generated_particle_summary_absent": generated is None,
                "event_payload_absent": no_event_payload,
                "beam_on_absent": no_beam_on,
            }
            status = (
                "PASS__SH3_PURE_DR_BASE_OVERLAP_NO_TRANSPORT"
                if all(checks.values())
                else "FAIL"
            )
            report.update(
                {
                    "status": status,
                    "command": command,
                    "returncode": returncode,
                    "timed_out": timed_out,
                    "checks": checks,
                    "bad_lines": bad_lines[:100],
                    "transport_lines": transport_lines[:100],
                    "generated_particles": int(generated.group(1)) if generated else None,
                    "initialized_artifacts": artifacts,
                    "files": {
                        name: {"path": str(path.resolve()), "sha256": current_hashes[name]}
                        for name, path in ((path.name, path) for path in core)
                    },
                }
            )
    except Exception as exc:
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}

    atomic_text(log_path, log_text)
    report["log"] = {
        "path": str(log_path),
        "sha256": sha256(log_path),
        "line_count": len(log_text.splitlines()),
        "tail": log_text.splitlines()[-100:],
    }
    report["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["transport_launched"] = False
    report["physics_status"] = (
        "PURE DR BASE GEOMETRY VALIDATED — CHIMNEY ASSEMBLY AND PHYSICS UNKNOWN"
        if report["status"] == "PASS__SH3_PURE_DR_BASE_OVERLAP_NO_TRANSPORT"
        else "PURE DR BASE OVERLAP AUDIT FAILED — PHYSICS UNKNOWN"
    )
    atomic_json(output, report)
    print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
    return 0 if report["status"] == "PASS__SH3_PURE_DR_BASE_OVERLAP_NO_TRANSPORT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
