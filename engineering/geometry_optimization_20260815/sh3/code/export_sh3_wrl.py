#!/usr/bin/env python3
"""Export the standalone SH3 chimney and pure-DR base to native Geant4 WRL.

The script starts Cosima in interactive mode, lets it construct the actual
MEGAlib/Geant4 CSG geometry, invokes the Geant4 ``VRML2FILE`` visualization
driver, and exits without starting a beam.  Thus named subtraction solids and
their 1.50 cm ports are exported by Geant4 rather than approximated by a
hand-written mesh converter.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
DR_BASE = PACKAGE / "dr_base"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
GEANT4 = MEGALIB / "external/geant4_v10.02.p03"
G4DATA = GEANT4 / "share/Geant4-10.2.3/data"

REPORT = PACKAGE / "audit/wrl_export_validation.json"

UI_COMMANDS = (
    "/vis/open VRML2FILE",
    "/vis/drawVolume",
    "/vis/viewer/flush",
    "exit",
)

TRANSPORT_PATTERNS = (
    re.compile(r"Total number of generated particles:\s*\d+", re.I),
    re.compile(r"Summary for run\s+", re.I),
    re.compile(r"/run/beamOn", re.I),
    re.compile(r"StartBeam", re.I),
    re.compile(r"###\s*Run\s+\d+\s+start", re.I),
)

BAD_PATTERNS = (
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


@dataclass(frozen=True)
class Target:
    identity: str
    setup: Path
    core_files: tuple[Path, ...]
    manifest: Path
    static: Path
    manifest_status: str
    static_status: str
    output: Path
    log: Path


TARGETS = (
    Target(
        identity="SH3_Chimney_Standalone",
        setup=PACKAGE / "geometry/SH3_Chimney_Standalone.geo.setup",
        core_files=(
            PACKAGE / "geometry/SH3_Chimney_Standalone.geo.setup",
            PACKAGE / "geometry/SH3_Chimney_Standalone.geo",
            PACKAGE / "geometry/SH3_Chimney_Component.geo",
            PACKAGE / "geometry/SH3_Chimney.det",
            PACKAGE / "geometry/Materials_SH3.geo",
        ),
        manifest=PACKAGE / "data/component_manifest.json",
        static=PACKAGE / "audit/static_validation.json",
        manifest_status="PASS__SH3_COMPONENT_BUILT",
        static_status="PASS__SH3_COMPONENT_STATIC",
        output=PACKAGE / "figures/SH3_Chimney_Standalone.wrl",
        log=PACKAGE / "audit/wrl_export_chimney_cosima.log",
    ),
    Target(
        identity="SH3_PureDR_Base",
        setup=DR_BASE / "geometry/SH3_PureDR_Base.geo.setup",
        core_files=(
            DR_BASE / "geometry/SH3_PureDR_Base.geo.setup",
            DR_BASE / "geometry/SH3_PureDR_Base.geo",
            DR_BASE / "geometry/Materials_SH3_DR_Base.geo",
        ),
        manifest=DR_BASE / "data/dr_base_manifest.json",
        static=DR_BASE / "audit/dr_base_static_validation.json",
        manifest_status="PASS__SH3_PURE_DR_BASE_BUILT",
        static_status="PASS__SH3_PURE_DR_BASE_STATIC",
        output=DR_BASE / "figures/SH3_PureDR_Base.wrl",
        log=DR_BASE / "audit/wrl_export_dr_base_cosima.log",
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def source_text(target: Target, scratch: Path) -> str:
    return "\n".join(
        (
            "Version 1",
            f"Geometry {target.setup.resolve()}",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo init-only",
            "",
            "# Parser scaffold only; interactive mode exits without StartBeam.",
            "Run GeometryViewOnly",
            f"GeometryViewOnly.FileName {scratch / 'parser_init_empty'}",
            "GeometryViewOnly.NEvents 1",
            "GeometryViewOnly.Source GeometryViewOnlySource",
            "GeometryViewOnlySource.ParticleType 1",
            "GeometryViewOnlySource.Beam PointSource 0 0 0",
            "GeometryViewOnlySource.Spectrum Mono 511",
            "GeometryViewOnlySource.Flux 1.0",
            "",
        )
    )


def verify_authority(target: Target) -> dict[str, dict[str, object]]:
    required = target.core_files + (target.manifest, target.static, COSIMA)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"{target.identity}: missing prerequisite(s): {missing}")

    manifest = json.loads(target.manifest.read_text(encoding="utf-8"))
    static = json.loads(target.static.read_text(encoding="utf-8"))
    if manifest.get("status") != target.manifest_status:
        raise RuntimeError(f"{target.identity}: manifest status is not {target.manifest_status}")
    if static.get("status") != target.static_status:
        raise RuntimeError(f"{target.identity}: static status is not {target.static_status}")

    records: dict[str, dict[str, object]] = {}
    stale: list[str] = []
    outputs = manifest.get("outputs", {})
    for path in target.core_files:
        current = sha256(path)
        expected = outputs.get(path.name, {}).get("sha256")
        if expected != current:
            stale.append(path.name)
        records[path.name] = {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": current,
            "manifest_sha256": expected,
        }
    if stale:
        raise RuntimeError(f"{target.identity}: stale manifest for {stale}")
    return records


def inspect_initialized_sim(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    event_lines = [line for line in text.splitlines() if re.match(r"^(?:SE|IA|HT|GR|PM)\s", line)]
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "event_record_line_count": len(event_lines),
    }


def export_target(target: Target) -> dict[str, object]:
    authority = verify_authority(target)
    started = dt.datetime.now(dt.timezone.utc)

    with tempfile.TemporaryDirectory(prefix="sh3_wrl_export_", dir="/tmp") as temporary:
        scratch = Path(temporary)
        card = scratch / "geometry_view_only.source"
        card_text = source_text(target, scratch)
        card.write_text(card_text, encoding="utf-8")

        ui_text = "\n".join((*UI_COMMANDS, ""))
        command = [str(COSIMA), "-i", "-u", str(card)]
        completed = subprocess.run(
            command,
            cwd=scratch,
            env=environment(),
            input=ui_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=900,
            check=False,
        )
        log_text = completed.stdout.replace("\r\n", "\n").replace("\r", "\n")
        atomic_text(target.log, log_text)

        native_outputs = sorted(scratch.glob("g4_*.wrl"))
        initialized = sorted(scratch.glob("*.sim")) + sorted(scratch.glob("*.sim.gz"))
        initialized_records = [inspect_initialized_sim(path) for path in initialized]
        transport_lines = [
            line
            for line in log_text.splitlines()
            if any(pattern.search(line) for pattern in TRANSPORT_PATTERNS)
        ]
        bad_lines = [
            line for line in log_text.splitlines() if any(pattern in line for pattern in BAD_PATTERNS)
        ]

        wrl_data = native_outputs[0].read_bytes() if len(native_outputs) == 1 else b""
        checks = {
            "authority_manifest_and_static_current": True,
            "cosima_returncode_zero": completed.returncode == 0,
            "geometry_stage12_complete": "Stage 12 (volume tree optimization) finished" in log_text,
            "geant4_constructed": "Geant4 version Name: geant4-10-02-patch-03" in log_text,
            "vrml2file_registered": "VRML2FILE (VRML2FILE)" in log_text,
            "vrml_generation_confirmed": "is generated." in log_text and "Output VRML 2.0 file:" in log_text,
            "exactly_one_native_wrl": len(native_outputs) == 1,
            "wrl_v2_header": wrl_data.startswith(b"#VRML V2.0 utf8"),
            "wrl_nontrivial_size": len(wrl_data) > 10_000,
            "ui_beam_on_absent": not any("/run/beamOn" in command_ for command_ in UI_COMMANDS),
            "transport_markers_absent": not transport_lines,
            "generated_particle_summary_absent": "Total number of generated particles:" not in log_text,
            "event_payload_absent": all(record["event_record_line_count"] == 0 for record in initialized_records),
            "bad_runtime_lines_absent": not bad_lines,
            "idle_exit_seen": "Idle>" in log_text and "Visualization Manager deleting..." in log_text,
        }
        status = "PASS__SH3_NATIVE_WRL_NO_TRANSPORT" if all(checks.values()) else "FAIL"
        if status == "PASS__SH3_NATIVE_WRL_NO_TRANSPORT":
            atomic_bytes(target.output, wrl_data)

        return {
            "identity": target.identity,
            "status": status,
            "started_at_utc": started.isoformat(),
            "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_authority": authority,
            "command": command,
            "ui_commands": list(UI_COMMANDS),
            "transport_launched": False,
            "checks": checks,
            "bad_lines": bad_lines[:100],
            "transport_lines": transport_lines[:100],
            "initialized_sim_artifacts": initialized_records,
            "output": {
                "path": str(target.output.resolve()),
                "bytes": len(wrl_data),
                "sha256": sha256_bytes(wrl_data),
                "shape_node_count": wrl_data.count(b"Shape {"),
                "indexed_face_set_count": wrl_data.count(b"IndexedFaceSet"),
                "source": "Geant4 VRML2FILE rendering of constructed CSG geometry",
            },
            "log": {
                "path": str(target.log.resolve()),
                "bytes": len(log_text.encode("utf-8")),
                "sha256": sha256_bytes(log_text.encode("utf-8")),
                "line_count": len(log_text.splitlines()),
            },
        }


def main() -> int:
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "FAIL",
        "evidence_role": (
            "Native geometry visualization only. No particle transport, activation, detector response, "
            "timing, background, or sensitivity claim."
        ),
        "targets": [],
    }
    try:
        results = [export_target(target) for target in TARGETS]
        report["targets"] = results
        report["status"] = (
            "PASS__SH3_TWO_NATIVE_WRL_NO_TRANSPORT"
            if all(result["status"] == "PASS__SH3_NATIVE_WRL_NO_TRANSPORT" for result in results)
            else "FAIL"
        )
    except Exception as exc:
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    report["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    atomic_json(REPORT, report)
    print(json.dumps({"status": report["status"], "report": str(REPORT)}, indent=2))
    return 0 if report["status"] == "PASS__SH3_TWO_NATIVE_WRL_NO_TRANSPORT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
