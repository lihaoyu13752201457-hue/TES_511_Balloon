#!/usr/bin/env python3
"""Shared, fail-closed helpers for the dated S3d replay harnesses."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "42_geoopt_s3d_lightweight_20260712"
)
DATA = PACKAGE / "data"
S3D_GEOMETRY_DIR = PACKAGE / "geometry"
S3D_GEOMETRY_SETUP = (
    S3D_GEOMETRY_DIR
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
S3C_GEOMETRY_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
    / "geometry"
)
S3C_GEOMETRY_SETUP = (
    S3C_GEOMETRY_DIR
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_COMPONENTS = (
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det",
    "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "Materials_DEMO2_DR_v3p5.geo",
)
GEOMETRY_MANIFEST = DATA / "s3d_geometry_manifest.json"
GEOMETRY_VALIDATION = DATA / "s3d_independent_geometry_validation.json"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB_ENV_SCRIPT = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701"
    / "05_optics_migration/megalib_env.sh"
)
PINNED_MEGALIB_ENV_SHA256 = "0702319ea5d152912b68df65038c1a075cef48b39142d3c7311c7b305944fecd"


class AuditError(RuntimeError):
    """Raised when a replay contract is not safe to prepare or execute."""


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_write_text(path: Path, text: str) -> str:
    """Create a deterministic file, but never replace differing content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current != text:
            raise AuditError(f"refusing to overwrite non-identical file: {rel(path)}")
        return "REUSED_IDENTICAL"
    path.write_text(text, encoding="utf-8")
    return "CREATED"


def safe_write_json(path: Path, payload: Any) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    return safe_write_text(path, text)


def geometry_hashes(geometry_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in GEOMETRY_COMPONENTS:
        path = geometry_dir / name
        if not path.is_file():
            raise AuditError(f"missing geometry component: {rel(path)}")
        hashes[name] = sha256(path)
    return hashes


def audit_geometry_authority() -> dict[str, Any]:
    if not GEOMETRY_MANIFEST.is_file() or not GEOMETRY_VALIDATION.is_file():
        raise AuditError("S3d geometry manifest or independent validation is missing")
    manifest = load_json(GEOMETRY_MANIFEST)
    validation = load_json(GEOMETRY_VALIDATION)
    checks = {
        "manifest_status": manifest.get("status"),
        "static_diff_status": manifest.get("static_diff_status"),
        "overlap_status": manifest.get("overlap_validation", {}).get("status"),
        "independent_validation_status": validation.get("status"),
        "generated_geometry_matches": (
            manifest.get("generated_geometry") == rel(S3D_GEOMETRY_SETUP)
        ),
    }
    passed = (
        checks["manifest_status"] == "S3D_O9_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"
        and checks["static_diff_status"] == "PASS"
        and checks["overlap_status"] == "PASS"
        and checks["independent_validation_status"] == "PASS"
        and checks["generated_geometry_matches"]
    )
    if not passed:
        raise AuditError(f"S3d geometry authority is not transport-ready: {checks}")
    return {
        "status": "PASS",
        "checks": checks,
        "s3d_geometry_hashes": geometry_hashes(S3D_GEOMETRY_DIR),
        "s3c_geometry_hashes": geometry_hashes(S3C_GEOMETRY_DIR),
    }


def source_scalar(text: str, key: str) -> str:
    matches = re.findall(rf"^{re.escape(key)}\s+(.+?)\s*$", text, flags=re.M)
    if len(matches) != 1:
        raise AuditError(f"expected one `{key}` directive, found {len(matches)}")
    return matches[0]


def source_run_name(text: str) -> str:
    return source_scalar(text, "Run")


def canonicalize_source(
    text: str,
    *,
    run_name: str,
    geometry: str,
    output_prefix: str,
) -> str:
    """Normalize only the three authorized geometry-local source differences."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("Geometry "):
            out.append("Geometry <GEOMETRY>")
            continue
        if line == f"Run {run_name}":
            out.append("Run <RUN>")
            continue
        if line.startswith(f"{run_name}.FileName "):
            value = line.split(None, 1)[1]
            if value != output_prefix:
                raise AuditError(
                    f"unexpected output prefix in source: {value!r} != {output_prefix!r}"
                )
            out.append("<RUN>.FileName <OUTPUT_PREFIX>")
            continue
        line = line.replace(run_name, "<RUN>")
        out.append(line)
    if source_scalar(text, "Geometry") != geometry:
        raise AuditError("source Geometry directive does not match its declared contract")
    return "\n".join(out) + "\n"


def existing_run_artifacts(run_dir: Path, allowed: set[Path]) -> list[str]:
    if not run_dir.exists():
        return []
    allowed_resolved = {p.resolve() for p in allowed}
    found: list[str] = []
    for path in sorted(run_dir.iterdir()):
        if path.resolve() not in allowed_resolved:
            found.append(rel(path))
    return found


def assert_no_production_artifacts(run_dir: Path, allowed: set[Path]) -> None:
    found = existing_run_artifacts(run_dir, allowed)
    if found:
        raise AuditError(
            "refusing to run because the dated run directory already contains "
            f"non-source artifacts: {found}"
        )


def sim_header(sim: Path, *, count_events: bool = False) -> dict[str, Any]:
    if not sim.is_file():
        return {"status": "PENDING_TRANSPORT", "exists": False}
    result: dict[str, Any] = {"status": "PRESENT", "exists": True}
    se = 0
    ids = 0
    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry") and "geometry" not in result:
                parts = line.split(None, 1)
                result["geometry"] = parts[1].strip() if len(parts) == 2 else ""
            elif line.startswith("Seed") and "seed" not in result:
                parts = line.split()
                result["seed"] = int(parts[1]) if len(parts) > 1 else None
            elif count_events and line == "SE":
                se += 1
            elif count_events and line.startswith("ID "):
                ids += 1
            if not count_events and line == "SE":
                break
    if count_events:
        result["SE"] = se
        result["ID"] = ids
    return result


def geometry_header_matches(header_value: str | None, expected_setup: Path) -> bool:
    if not header_value:
        return False
    header = Path(str(header_value).strip()).resolve()
    return header == expected_setup.resolve()


def cosima_environment() -> tuple[dict[str, str], dict[str, Any]]:
    """Load and validate the retained project MEGAlib environment authority."""
    if not MEGALIB_ENV_SCRIPT.is_file():
        raise AuditError(f"missing MEGAlib environment authority: {rel(MEGALIB_ENV_SCRIPT)}")
    env_hash = sha256(MEGALIB_ENV_SCRIPT)
    if env_hash != PINNED_MEGALIB_ENV_SHA256:
        raise AuditError(
            f"MEGAlib environment authority changed: {env_hash} != {PINNED_MEGALIB_ENV_SHA256}"
        )
    proc = subprocess.run(
        [
            "/bin/bash",
            "-c",
            'source "$1"\nenv -0',
            "s3d-replay-env",
            str(MEGALIB_ENV_SCRIPT),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"unable to load {rel(MEGALIB_ENV_SCRIPT)}: {detail}")
    env: dict[str, str] = {}
    for item in proc.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        env[key.decode("utf-8", errors="strict")] = value.decode(
            "utf-8", errors="strict"
        )
    required = (
        "MEGALIB",
        "G4NEUTRONHPDATA",
        "G4LEDATA",
        "G4LEVELGAMMADATA",
        "G4RADIOACTIVEDATA",
        "G4NEUTRONXSDATA",
        "G4PIIDATA",
        "G4REALSURFACEDATA",
        "G4SAIDXSDATA",
        "G4ABLADATA",
        "G4ENSDFSTATEDATA",
    )
    missing_vars = [key for key in required if not env.get(key)]
    missing_paths = [key for key in required if env.get(key) and not Path(env[key]).exists()]
    cosima = Path(env.get("MEGALIB", "")) / "bin/cosima"
    if (
        missing_vars
        or missing_paths
        or not cosima.is_file()
        or not os.access(cosima, os.X_OK)
    ):
        raise AuditError(
            "invalid MEGAlib environment: "
            f"missing_vars={missing_vars}, missing_paths={missing_paths}, cosima={cosima}"
        )
    evidence = {
        "status": "PASS",
        "script": rel(MEGALIB_ENV_SCRIPT),
        "script_sha256": env_hash,
        "pinned_script_sha256": PINNED_MEGALIB_ENV_SHA256,
        "cosima": str(cosima),
        "required_dataset_paths": {key: env[key] for key in required if key != "MEGALIB"},
    }
    return env, evidence


def run_cosima(
    *,
    source: Path,
    log: Path,
    run_dir: Path,
    allowed_preexisting: set[Path],
    seed: int | None = None,
) -> int:
    env, evidence = cosima_environment()
    cosima = Path(evidence["cosima"])
    assert_no_production_artifacts(run_dir, allowed_preexisting)
    if log.exists():
        raise AuditError(f"refusing to overwrite log: {rel(log)}")
    command = [str(cosima)]
    if seed is not None:
        command.extend(["-s", str(seed)])
    command.append(rel(source))
    with log.open("x", encoding="utf-8") as handle:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return int(proc.returncode)


def selection_contract() -> dict[str, Any]:
    return {
        "energy_windows_keV": {
            "w2_510p58_511p42": [510.58, 511.42],
            "broad_480_550": [480.0, 550.0],
            "interval_policy": "lower-inclusive, upper-exclusive",
        },
        "active_veto_threshold_keV": 50.0,
        "active_veto_acceptance": "summed matched active energy < 50 keV",
        "active_veto_volume_rule": (
            "BGO/CsI active scintillator + ActiveShield/CEBR3 + "
            "GeoOpt_S2B_CryoShell_Plastic*; W/Al mechanical shell excluded"
        ),
        "side_compton_fov": {
            "implementation": "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py::side_keep_from_hits",
            "reject_policy": "keep",
            "knob0_policy": "frozen current monotonic policy; literal S0/S1-retain rule is not promoted",
        },
    }
