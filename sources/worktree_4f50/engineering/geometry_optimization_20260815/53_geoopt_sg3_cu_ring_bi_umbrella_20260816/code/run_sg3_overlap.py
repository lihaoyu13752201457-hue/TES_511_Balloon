#!/usr/bin/env python3
"""Run the permitted Cosima SG3 construct/load/overlap audit without transport.

Cosima's parameter parser requires a Run and a source even in interactive
mode.  This tool therefore supplies a parser-only placeholder, launches
Cosima with ``-i``, lets Geant4 construct the geometry (where
``CheckForOverlaps 10000 0.0001`` is executed), and immediately sends ``exit`` to
the idle UI.  It never invokes StartBeam or ``/run/beamOn``.

The high-sample Geant4 result is deliberately labelled as one component of the
SG3 overlap evidence.  The 10,000 samples per placement specifically strengthen
the gate around the replacement Cu ring and Bi umbrella; byte-reversible SF3
fidelity and frozen-bank navigation remain separate mandatory gates.
"""

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


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_DIR = PACKAGE_ROOT / "geometry"
AUDIT_DIR = PACKAGE_ROOT / "audit"
STEM = "DEMO2_DR_v3p5_SG3"

SETUP = GEOMETRY_DIR / f"{STEM}.geo.setup"
GEO = GEOMETRY_DIR / f"{STEM}.geo"
DET = GEOMETRY_DIR / f"{STEM}.det"
STATIC_VALIDATION = AUDIT_DIR / "sg3_geometry_validation.json"
DEFAULT_OUTPUT = AUDIT_DIR / "sg3_overlap_validation.json"
DEFAULT_LOG = AUDIT_DIR / "sg3_overlap_cosima.log"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
DEFAULT_COSIMA = MEGALIB / "bin/cosima"
GEANT4 = MEGALIB / "external/geant4_v10.02.p03"
G4DATA = GEANT4 / "share/Geant4-10.2.3/data"

OVERLAP_BAD_PATTERNS = (
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

TRANSPORT_OUTPUT_PATTERNS = (
    re.compile(r"Total number of generated particles:\s*\d+", re.IGNORECASE),
    re.compile(r"Summary for run\s+", re.IGNORECASE),
    re.compile(r"/run/beamOn", re.IGNORECASE),
    re.compile(r"StartBeam", re.IGNORECASE),
    re.compile(r"###\s*Run\s+\d+\s+start", re.IGNORECASE),
)

TRANSPORT_FILE_SUFFIXES = (
    ".sim",
    ".sim.gz",
    ".tra",
    ".tra.gz",
    ".evta",
    ".evta.gz",
    ".dat.gz",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


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


def parser_scaffold(setup: Path, scratch: Path) -> str:
    """Return the minimum source accepted by Cosima's mandatory parser checks."""
    return "\n".join(
        (
            "Version 1",
            f"Geometry {setup.resolve()}",
            "CheckForOverlaps 10000 0.0001",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo init-only",
            "",
            "# Parser-only placeholder. Interactive mode exits before StartBeam.",
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


def transport_artifacts(root: Path) -> list[str]:
    artifacts: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if any(lower.endswith(suffix) for suffix in TRANSPORT_FILE_SUFFIXES):
            artifacts.append(str(path))
    return sorted(artifacts)


def inspect_initialized_output(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    event_lines = [
        line
        for line in text.splitlines()
        if re.match(r"^(?:SE|IA|HT|GR|PM)\s", line)
    ]
    return {
        "path": str(path),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "event_record_line_count": len(event_lines),
        "event_record_line_head": event_lines[:20],
        "head": text.splitlines()[:30],
    }


def generated_count(text: str) -> int | None:
    match = re.search(r"Total number of generated particles:\s*(\d+)", text)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cosima", type=Path, default=DEFAULT_COSIMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    output = args.output.resolve()
    log_path = args.log.resolve()
    cosima = args.cosima.resolve()
    started = dt.datetime.now(dt.timezone.utc)
    report: dict[str, Any] = {
        "model_identity": "SG3",
        "status": "FAIL",
        "started_at_utc": started.isoformat(),
        "transport_launched": False,
        "check_for_overlaps": {"samples": 10000, "tolerance_cm": 0.0001},
        "evidence_role": {
            "classification": "COMPOSITE_OVERLAP_EVIDENCE_COMPONENT",
            "standalone_sufficiency": False,
            "statement": (
                "This is a real Cosima/Geant4 construct/load audit with 10,000 overlap "
                "samples per placement. It is combined with byte-reversible SF3 fidelity, "
                "static clearance checks, and the frozen-bank native navigator audit."
            ),
        },
    }

    log_text = ""
    try:
        required = (SETUP, GEO, DET, STATIC_VALIDATION, cosima)
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"missing overlap prerequisite(s): {missing}")
        if args.timeout_seconds <= 0:
            raise ValueError("--timeout-seconds must be positive")

        static = json.loads(STATIC_VALIDATION.read_text(encoding="utf-8"))
        if static.get("status") != "PASS__SG3_TWO_CHANGE_BYTE_REVERSIBLE_SF3_CHILD":
            raise RuntimeError("static SG3 validation is not PASS")
        static_core = static.get("generated", {})
        current_hashes = {"setup": sha256(SETUP), "geo": sha256(GEO), "det": sha256(DET)}
        stale = [
            key
            for key, current_hash in current_hashes.items()
            if static_core.get(key, {}).get("sha256") != current_hash
        ]
        if stale:
            raise RuntimeError(f"static validation is stale for core file(s): {stale}")

        with tempfile.TemporaryDirectory(prefix="sg3_overlap_", dir="/tmp") as temporary:
            scratch = Path(temporary)
            source_path = scratch / "sg3_construct_overlap_no_transport.source"
            source_text = parser_scaffold(SETUP, scratch)
            source_path.write_text(source_text, encoding="utf-8")

            exact_directive = source_text.count("CheckForOverlaps 10000 0.0001") == 1
            source_beam_on_absent = re.search(
                r"^\s*/run/beamOn\b", source_text, re.IGNORECASE | re.MULTILINE
            ) is None
            if not exact_directive or not source_beam_on_absent:
                raise RuntimeError("generated source violates overlap/no-beamOn contract")

            before_artifacts = transport_artifacts(scratch)
            command = [str(cosima), "-i", "-u", str(source_path)]
            try:
                completed = subprocess.run(
                    command,
                    cwd=scratch,
                    env=cosima_environment(),
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
                stdout = exc.stdout or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                log_text = stdout.replace("\r\n", "\n").replace("\r", "\n")

            after_artifacts = transport_artifacts(scratch)
            initialized_output_paths = sorted(set(after_artifacts) - set(before_artifacts))
            initialized_outputs = [
                inspect_initialized_output(Path(path)) for path in initialized_output_paths
            ]
            event_payload_absent = all(
                item["event_record_line_count"] == 0 for item in initialized_outputs
            )
            bad_lines = [
                line
                for line in log_text.splitlines()
                if any(pattern in line for pattern in OVERLAP_BAD_PATTERNS)
            ]
            transport_markers = [
                line
                for line in log_text.splitlines()
                if any(pattern.search(line) for pattern in TRANSPORT_OUTPUT_PATTERNS)
            ]

            parameter_file_match = f"Using parameter file {source_path}" in log_text
            stage12_complete = "Stage 12 (volume tree optimization) finished" in log_text
            geant4_constructed = "Geant4 version Name: geant4-10-02-patch-03" in log_text
            interactive_started = "Starting interactive mode!" in log_text
            # With a pipe rather than a PTY, G4UIterminal prints the prompt but
            # does not echo the supplied ``exit`` token.
            idle_exit_seen = (
                "Idle>" in log_text and "Visualization Manager deleting..." in log_text
            )
            particles = generated_count(log_text)
            no_transport = (
                particles is None
                and not transport_markers
                and event_payload_absent
                and source_beam_on_absent
                and "-i" in command
            )
            status = (
                "PASS"
                if returncode == 0
                and not timed_out
                and not bad_lines
                and parameter_file_match
                and stage12_complete
                and geant4_constructed
                and interactive_started
                and idle_exit_seen
                and exact_directive
                and no_transport
                else "FAIL"
            )

            report.update(
                {
                    "status": status,
                    "command": command,
                    "returncode": returncode,
                    "timed_out": timed_out,
                    "timeout_seconds": args.timeout_seconds,
                    "source_card": {
                        "ephemeral_path": str(source_path),
                        "sha256": sha256_text(source_text),
                        "text": source_text,
                        "cosima_parser_scaffold_run_declared": True,
                        "scaffold_executed": False,
                        "beam_on_command_present": not source_beam_on_absent,
                    },
                    "checks": {
                        "static_validation_pass_and_current": True,
                        "cosima_returncode_zero": returncode == 0,
                        "parameter_file_match": parameter_file_match,
                        "geant4_kernel_constructed": geant4_constructed,
                        "geometry_stage12_complete": stage12_complete,
                        "interactive_mode_started": interactive_started,
                        "idle_exit_seen": idle_exit_seen,
                        "exact_overlap_directive": exact_directive,
                        "overlap_bad_pattern_absent": not bad_lines,
                        "transport_output_marker_absent": not transport_markers,
                        "initialized_sim_event_payload_absent": event_payload_absent,
                        "generated_particle_summary_absent": particles is None,
                        "beam_on_command_absent": source_beam_on_absent,
                    },
                    "bad_patterns": list(OVERLAP_BAD_PATTERNS),
                    "bad_lines": bad_lines[:100],
                    "transport_output_markers": transport_markers[:100],
                    "generated_particles": particles,
                    "initialized_output_artifacts": initialized_outputs,
                    "initialized_output_note": (
                        "Cosima creates an empty SIM container while constructing its mandatory "
                        "Run object, before any event loop. The container is temporary and is "
                        "accepted only when it contains no event records."
                    ),
                    "files": {
                        "static_validation": {
                            "path": str(STATIC_VALIDATION.resolve()),
                            "sha256": sha256(STATIC_VALIDATION),
                        },
                        "setup": {"path": str(SETUP.resolve()), "sha256": current_hashes["setup"]},
                        "geo": {"path": str(GEO.resolve()), "sha256": current_hashes["geo"]},
                        "det": {"path": str(DET.resolve()), "sha256": current_hashes["det"]},
                        "cosima": {"path": str(cosima), "sha256": sha256(cosima)},
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
        "tail": log_text.splitlines()[-80:],
    }
    report["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["transport_launched"] = False
    report["physics_status"] = (
        "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN"
        if report["status"] == "PASS"
        else "GEOMETRY OVERLAP SMOKE FAILED — PHYSICS UNKNOWN"
    )
    atomic_json(output, report)
    print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
