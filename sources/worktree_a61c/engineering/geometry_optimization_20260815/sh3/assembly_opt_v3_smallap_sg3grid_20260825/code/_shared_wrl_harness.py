#!/usr/bin/env python3
"""Export the constructed SH3 assembly with Geant4 VRML2FILE, no transport."""

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
FIGURES = PACKAGE / "figures"
SETUP = GEOMETRY / "SH3_Assembly.geo.setup"
GEO = GEOMETRY / "SH3_Assembly.geo"
DET = GEOMETRY / "SH3_Assembly.det"
MATERIALS = GEOMETRY / "Materials_SH3_Assembly.geo"
MANIFEST = DATA / "assembly_manifest.json"
STATIC = AUDIT / "assembly_static_validation.json"
OVERLAP = AUDIT / "assembly_overlap_validation.json"
OUTPUT = FIGURES / "SH3_Chimney_DR_Assembly.wrl"
LOG = AUDIT / "assembly_wrl_export_cosima.log"
REPORT = AUDIT / "assembly_wrl_export_validation.json"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
GEANT4 = MEGALIB / "external/geant4_v10.02.p03"
G4DATA = GEANT4 / "share/Geant4-10.2.3/data"

UI_COMMANDS = (
    "/vis/open VRML2FILE",
    "/vis/drawVolume",
    "/vis/viewer/flush",
    "exit",
)
BAD_PATTERNS = (
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
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_text(path: Path, text: str) -> None:
    atomic_bytes(path, text.encode("utf-8"))


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
            "G4VRMLFILE_MAX_FILE_NUM": "100",
        }
    )
    return env


def source_text(scratch: Path) -> str:
    return "\n".join(
        (
            "Version 1",
            f"Geometry {SETUP.resolve()}",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo init-only",
            "",
            "# Parser scaffold only; interactive mode exits without StartBeam.",
            "Run AssemblyViewOnly",
            f"AssemblyViewOnly.FileName {scratch / 'parser_init_empty'}",
            "AssemblyViewOnly.NEvents 1",
            "AssemblyViewOnly.Source AssemblyViewOnlySource",
            "AssemblyViewOnlySource.ParticleType 1",
            "AssemblyViewOnlySource.Beam PointSource 0 0 0",
            "AssemblyViewOnlySource.Spectrum Mono 511",
            "AssemblyViewOnlySource.Flux 1.0",
            "",
        )
    )


def verify_authority() -> dict[str, dict[str, object]]:
    core = (SETUP, GEO, DET, MATERIALS)
    required = core + (MANIFEST, STATIC, OVERLAP, COSIMA)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing assembly WRL prerequisite(s): {missing}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    static = json.loads(STATIC.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS__SH3_ASSEMBLY_BUILT":
        raise RuntimeError("assembly manifest is not PASS")
    if static.get("status") != "PASS__SH3_ASSEMBLY_STATIC":
        raise RuntimeError("assembly static validation is not PASS")
    if overlap.get("status") != "PASS__SH3_ASSEMBLY_OVERLAP_NO_TRANSPORT":
        raise RuntimeError("assembly overlap validation is not PASS")
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
    overlap_files = overlap.get("source_authority", {})
    if any(overlap_files.get(path.name, {}).get("sha256") != sha256(path) for path in core):
        raise RuntimeError("assembly overlap receipt is stale")
    if stale:
        raise RuntimeError(f"assembly manifest stale for: {stale}")
    return records


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


def main() -> int:
    report: dict[str, Any] = {
        "status": "FAIL",
        "component_identity": "SH3_Chimney_DR_Assembly",
        "transport_launched": False,
        "evidence_role": "Native assembled-geometry visualization only; no physics claim.",
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    log_text = ""
    try:
        authority = verify_authority()
        with tempfile.TemporaryDirectory(prefix="sh3_assembly_wrl_", dir="/tmp") as temporary:
            scratch = Path(temporary)
            card = scratch / "assembly_view_no_transport.source"
            card.write_text(source_text(scratch), encoding="utf-8")
            completed = subprocess.run(
                [str(COSIMA), "-i", "-u", str(card)],
                cwd=scratch,
                env=environment(),
                input="\n".join((*UI_COMMANDS, "")),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=900,
                check=False,
            )
            log_text = completed.stdout.replace("\r\n", "\n").replace("\r", "\n")
            native = sorted(scratch.glob("g4_*.wrl"))
            wrl = native[0].read_bytes() if len(native) == 1 else b""
            sims = [inspect_sim(path) for path in sorted(scratch.glob("*.sim*"))]
            bad_lines = [line for line in log_text.splitlines() if any(p in line for p in BAD_PATTERNS)]
            transport_lines = [
                line for line in log_text.splitlines() if any(p.search(line) for p in TRANSPORT_PATTERNS)
            ]
            checks = {
                "authority_current_and_overlap_pass": True,
                "cosima_returncode_zero": completed.returncode == 0,
                "geometry_stage12_complete": "Stage 12 (volume tree optimization) finished" in log_text,
                "geant4_constructed": "Geant4 version Name: geant4-10-02-patch-03" in log_text,
                "vrml2file_registered": "VRML2FILE (VRML2FILE)" in log_text,
                "exactly_one_native_wrl": len(native) == 1,
                "wrl_v2_header": wrl.startswith(b"#VRML V2.0 utf8"),
                "wrl_nontrivial_size": len(wrl) > 10_000,
                "beam_on_absent": all("/run/beamOn" not in command for command in UI_COMMANDS),
                "transport_markers_absent": not transport_lines,
                "event_payload_absent": all(item["event_record_line_count"] == 0 for item in sims),
                "bad_runtime_lines_absent": not bad_lines,
                "idle_exit_seen": "Idle>" in log_text and "Visualization Manager deleting..." in log_text,
            }
            status = "PASS__SH3_ASSEMBLY_NATIVE_WRL_NO_TRANSPORT" if all(checks.values()) else "FAIL"
            if status.startswith("PASS"):
                atomic_bytes(OUTPUT, wrl)
            report.update(
                {
                    "status": status,
                    "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "source_authority": authority,
                    "ui_commands": list(UI_COMMANDS),
                    "checks": checks,
                    "bad_lines": bad_lines[:100],
                    "transport_lines": transport_lines[:100],
                    "initialized_sim_artifacts": sims,
                    "output": {
                        "path": str(OUTPUT),
                        "bytes": len(wrl),
                        "sha256": sha256_bytes(wrl),
                        "shape_node_count": wrl.count(b"Shape {"),
                        "indexed_face_set_count": wrl.count(b"IndexedFaceSet"),
                    },
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
    }
    atomic_json(REPORT, report)
    print(json.dumps({"status": report["status"], "report": str(REPORT)}, indent=2))
    return 0 if report["status"] == "PASS__SH3_ASSEMBLY_NATIVE_WRL_NO_TRANSPORT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
