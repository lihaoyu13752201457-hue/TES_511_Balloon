#!/usr/bin/env python3
"""Shared contracts and helpers for the full-spectrum proton resource smoke."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
PACKAGE_ROOT = THIS_FILE.parents[1]
REPAIR_ROOT = THIS_FILE.parents[2]
ROOT = THIS_FILE.parents[4]
RUN_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "proton_fullsphere20_resource_smoke_20260812"
)
CONTRACT = RUN_ROOT / "frozen_contract.json"
STATE = RUN_ROOT / "execution_state.json"
VALIDATION_REPORT = RUN_ROOT / "validation_report.json"
SUMMARY = RUN_ROOT / "resource_summary.json"
SOURCE_CONTRACT = REPAIR_ROOT / "data/source_contract_manifest.json"
STATIC_VALIDATION = REPAIR_ROOT / "data/static_validation.json"
STATIC_VALIDATOR = REPAIR_ROOT / "code/validate_corrected_source_package.py"
RUNNER = CODE_DIR / "run_proton_fullsphere20_resource_smoke.py"
VALIDATOR = CODE_DIR / "validate_proton_fullsphere20_resource_smoke.py"
LIMIT_LAUNCHER = CODE_DIR / "launch_cosima_with_limits.py"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB_SETUP = COSIMA.parent / "source-megalib.sh"

SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
BATCH_ID = "corrected_kev_expacs_proton_fullsphere20_resource_smoke_20260812"
EVENTS_PER_JOB = 64
FLUX_CM2_S = 0.1123007216313341
FARFIELD_RADIUS_CM = 60.0
SEED_BY_MODE = {"instant": 983_127_922, "buildup": 984_127_922}
GEOMETRIES = ("mass_model_511", "s3d_o8")
MODES = ("instant", "buildup")

PER_FILE_CAP_BYTES = 1 * 1024**3
BATCH_OUTPUT_CAP_BYTES = 2 * 1024**3
FREE_DISK_FLOOR_BYTES = 80 * 1024**3
PROCESS_GROUP_RSS_CAP_BYTES = 4 * 1024**3
MEM_AVAILABLE_FLOOR_BYTES = 1_500_000_000
JOB_WALL_LIMIT_S = 15 * 60
NO_ACTIVITY_LIMIT_S = 3 * 60
WATCHDOG_POLL_S = 1.0

GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(-?\d+)\s*$", re.MULTILINE)
WALL_RE = re.compile(r"^wall_s=([-+0-9.eE]+)\s*$", re.MULTILINE)
PEAK_RSS_RE = re.compile(r"^peak_process_group_rss_bytes=(\d+)\s*$", re.MULTILINE)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_once_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_replace_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def source_card(geometry: str) -> Path:
    return REPAIR_ROOT / f"config/source_cards/{geometry}/Background_p_fullsphere20.source"


def source_migration_manifest(geometry: str) -> Path:
    return REPAIR_ROOT / f"config/source_cards/{geometry}/source_migration_manifest.json"


def job_specs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    # Instant first, then buildup, so prompt transport is characterized before
    # activation-build-up work is attempted.
    for mode in MODES:
        for geometry in GEOMETRIES:
            ordinal += 1
            key = f"{geometry}_{mode}"
            directory = RUN_ROOT / geometry / mode
            name = f"Background_p_fullsphere20_{geometry}_{mode}_resource_smoke"
            prefix = directory / name
            isotope_prefix = directory / f"{name}.dat"
            rows.append(
                {
                    "ordinal": ordinal,
                    "key": key,
                    "geometry": geometry,
                    "mode": mode,
                    "events": EVENTS_PER_JOB,
                    "seed": SEED_BY_MODE[mode],
                    "directory": directory,
                    "name": name,
                    "base_source": source_card(geometry),
                    "job_source": directory / f"{name}.source",
                    "sim_prefix": prefix,
                    "isotope_prefix": isotope_prefix,
                    "sim": Path(f"{prefix}.inc1.id1.sim.gz"),
                    "dat": Path(f"{isotope_prefix}.inc1.dat"),
                    "log": directory / f"{name}.log",
                    "receipt": RUN_ROOT / "job_receipts" / f"{ordinal:02d}_{key}.json",
                }
            )
    return rows


def serializable_job(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        key: rel(value) if isinstance(value, Path) else value
        for key, value in spec.items()
    }


def resolve_transport_environment() -> tuple[dict[str, str], dict[str, Any]]:
    if not COSIMA.is_file() or not os.access(COSIMA, os.X_OK):
        raise RuntimeError(f"Cosima executable is unavailable: {COSIMA}")
    environment = dict(os.environ)
    if MEGALIB_SETUP.is_file():
        result = subprocess.run(
            ["bash", "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(MEGALIB_SETUP)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to load MEGAlib environment: {MEGALIB_SETUP}")
        environment = {}
        for item in result.stdout.split(b"\0"):
            if item and b"=" in item:
                key, value = item.split(b"=", 1)
                environment[key.decode(errors="replace")] = value.decode(errors="replace")
    relevant = {
        key: value
        for key, value in sorted(environment.items())
        if key in {"MEGALIB", "ROOTSYS", "LD_LIBRARY_PATH"}
        or key.startswith("G4")
        or key.startswith("GEANT4")
    }
    descriptor = {
        "setup_script": rel(MEGALIB_SETUP) if MEGALIB_SETUP.is_file() else None,
        "setup_script_sha256": sha256(MEGALIB_SETUP) if MEGALIB_SETUP.is_file() else None,
        "relevant_variables": relevant,
        "relevant_variables_sha256": canonical_digest(relevant),
    }
    return environment, descriptor


def static_gate() -> dict[str, Any]:
    if sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("corrected source contract hash differs from the canonical pin")
    result = subprocess.run(
        [sys.executable, str(STATIC_VALIDATOR), "--check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"corrected source static validator failed:\n{result.stdout[-4000:]}")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("static validator did not emit one JSON report") from exc
    packages = report.get("source_packages", {})
    if (
        report.get("status") != "PASS"
        or report.get("errors") not in (None, [])
        or report.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
        or report.get("spectra", {}).get("files") != 160
        or packages.get("cards") != 24
        or packages.get("spectrum_references") != 480
        or packages.get("legacy_references") != 0
    ):
        raise RuntimeError("corrected source static report lacks the required clean PASS closure")
    return report


def proton_contract_records() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(SOURCE_CONTRACT)
    records: dict[str, dict[str, Any]] = {}
    for geometry in GEOMETRIES:
        matches = [
            row
            for row in manifest["geometries"][geometry]["cards"]
            if row.get("family") == "p"
        ]
        if len(matches) != 1:
            raise RuntimeError(f"source contract has {len(matches)} proton cards for {geometry}")
        record = matches[0]
        path = resolve_repo_path(record["source"])
        if path != source_card(geometry).resolve() or sha256(path) != record["source_sha256"]:
            raise RuntimeError(f"proton source identity/hash mismatch: {geometry}")
        if (
            record.get("spectrum_references") != 20
            or len(record.get("spectrum_files", [])) != 20
            or not math.isclose(float(record.get("flux_sum_cm2_s", -1)), FLUX_CM2_S, abs_tol=1e-14)
        ):
            raise RuntimeError(f"proton source 20-bin/Flux closure failed: {geometry}")
        records[geometry] = record
    if manifest.get("energy_contract", {}).get("output_energy_unit") != "keV_total":
        raise RuntimeError("source contract is not total-keV")
    if manifest.get("bins_per_family") != 20 or float(manifest.get("farfield_radius_cm", -1)) != 60.0:
        raise RuntimeError("source contract is not the R=60 cm, 20-bin package")
    return manifest, records


def expected_job_source(spec: dict[str, Any]) -> str:
    lines: list[str] = []
    counts = {"seed": 0, "events": 0, "file": 0, "isotope": 0, "decay": 0}
    for raw in Path(spec["base_source"]).read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("Seed "):
            counts["seed"] += 1
            lines.append(f"Seed {spec['seed']}")
        elif stripped.startswith("DecayMode"):
            counts["decay"] += 1
            if spec["mode"] == "buildup":
                lines.append("DecayMode ActivationBuildUp")
        elif ".Events" in raw:
            counts["events"] += 1
            prefix = raw.split(".Events", 1)[0].strip()
            lines.append(f"{prefix}.Events {spec['events']}")
        elif ".FileName" in raw:
            counts["file"] += 1
            prefix = raw.split(".FileName", 1)[0].strip()
            lines.append(f"{prefix}.FileName {spec['sim_prefix']}")
        elif ".IsotopeProductionFile" in raw:
            counts["isotope"] += 1
            prefix = raw.split(".IsotopeProductionFile", 1)[0].strip()
            lines.append(f"{prefix}.IsotopeProductionFile {spec['isotope_prefix']}")
        else:
            lines.append(raw)
    if counts != {"seed": 1, "events": 1, "file": 1, "isotope": 1, "decay": 1}:
        raise RuntimeError(f"unexpected base-source control-line counts: {counts}")
    text = "\n".join(lines) + "\n"
    if "cosima_spectra_dp_2602units" in text or text.count(".Spectrum File ") != 20:
        raise RuntimeError("patched source is not the corrected 20-spectrum card")
    if text.count(".ParticleType 4") != 20 or text.count("FarFieldAreaSource") != 20:
        raise RuntimeError("patched source is not a 20-bin proton far-field card")
    return text


def input_snapshots(environment: dict[str, str]) -> list[dict[str, Any]]:
    manifest, proton_records = proton_contract_records()
    paths_with_expected: dict[Path, str | None] = {
        SOURCE_CONTRACT.resolve(): SOURCE_CONTRACT_SHA256,
        STATIC_VALIDATION.resolve(): None,
        STATIC_VALIDATOR.resolve(): None,
        RUNNER.resolve(): None,
        VALIDATOR.resolve(): None,
        LIMIT_LAUNCHER.resolve(): None,
        THIS_FILE.resolve(): None,
        COSIMA.resolve(): None,
    }
    if MEGALIB_SETUP.is_file():
        paths_with_expected[MEGALIB_SETUP.resolve()] = None
    for geometry, record in proton_records.items():
        paths_with_expected[source_card(geometry).resolve()] = record["source_sha256"]
        paths_with_expected[source_migration_manifest(geometry).resolve()] = None
        bundle = manifest["geometries"][geometry]["geometry_bundle"]
        for row in bundle["files"]:
            if row["scope"] == "repository":
                path = resolve_repo_path(row["path"])
            elif row["scope"] == "megalib":
                megalib = environment.get("MEGALIB")
                if not megalib:
                    raise RuntimeError("MEGALIB is unset while resolving geometry bundle")
                path = (Path(megalib) / row["path_relative_to_megalib"]).resolve()
            else:
                raise RuntimeError(f"unknown geometry-bundle scope: {row['scope']}")
            paths_with_expected[path] = row["sha256"]
    for row in manifest["spectra"]["files"]:
        if row.get("family") == "p":
            paths_with_expected[resolve_repo_path(row["corrected_spectrum"])] = row["corrected_sha256"]
    snapshots: list[dict[str, Any]] = []
    for path, expected in sorted(paths_with_expected.items(), key=lambda item: rel(item[0])):
        if not path.is_file():
            raise RuntimeError(f"frozen input is missing: {path}")
        digest = sha256(path)
        if expected is not None and digest != expected:
            raise RuntimeError(f"frozen input hash mismatch: {rel(path)}")
        snapshots.append({"path": rel(path), "sha256": digest, "size_bytes": path.stat().st_size})
    return snapshots


def verify_input_snapshots(records: list[dict[str, Any]]) -> None:
    for record in records:
        path = resolve_repo_path(record["path"])
        if (
            not path.is_file()
            or path.stat().st_size != int(record["size_bytes"])
            or sha256(path) != record["sha256"]
        ):
            raise RuntimeError(f"frozen input drifted: {record['path']}")


def mem_available_bytes() -> int:
    for raw in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if raw.startswith("MemAvailable:"):
            return int(raw.split()[1]) * 1024
    raise RuntimeError("MemAvailable is unavailable")


def process_group_cpu_ticks(pgid: int) -> int:
    total = 0
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text(encoding="utf-8").split()
            if int(fields[4]) == pgid:
                total += int(fields[13]) + int(fields[14])
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def process_group_rss_bytes(pgid: int) -> int:
    total = 0
    page_size = os.sysconf("SC_PAGE_SIZE")
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text(encoding="utf-8").split()
            if int(fields[4]) != pgid:
                continue
            resident_pages = int(path.with_name("statm").read_text(encoding="utf-8").split()[1])
            total += resident_pages * page_size
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def tree_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for current, _directories, files in os.walk(path):
        for name in files:
            try:
                total += (Path(current) / name).stat().st_size
            except FileNotFoundError:
                continue
    return total


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

    def one(pattern: re.Pattern[str], cast: Any) -> Any:
        matches = pattern.findall(text)
        return cast(matches[-1]) if matches else None

    return {
        "generated_particles": one(GENERATED_RE, int),
        "cpu_s": one(CPU_RE, float),
        "observation_time_s": one(OBSERVATION_RE, float),
        "returncode": one(RETURN_RE, int),
        "wall_s": one(WALL_RE, float),
        "peak_process_group_rss_bytes": one(PEAK_RSS_RE, int),
        "has_error_marker": any(
            marker in text
            for marker in ("***  Error", "Segmentation fault", "Fatal Exception", "std::bad_alloc")
        ),
        "megalib_banner": "MEGAlib version" in text,
    }
