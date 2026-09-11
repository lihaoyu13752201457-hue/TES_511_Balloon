#!/usr/bin/env python3
"""Standalone corrected-keV M05 batch0006 campaign controller.

The controller is deliberately narrow: it owns one F-rich, two-geometry,
16-hour campaign and writes only below the batch0006 run root.  ``--print-plan``
performs read-only gates and never creates a file.  Normal execution freezes
the complete seed/job registry before invoking Cosima directly.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import gzip
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from validate_m05_campaign_batch0006 import patch_source_exact, verify_source_patch_exact

sys.dont_write_bytecode = True

THIS_FILE = Path(__file__).resolve()
ENGINEERING_ROOT = THIS_FILE.parents[1]
PACKAGE_ROOT = THIS_FILE.parents[2]
ROOT = THIS_FILE.parents[4]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
PRIOR_RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
SOURCE_CONTRACT = PACKAGE_ROOT / "data/source_contract_manifest.json"
STATIC_VALIDATOR = PACKAGE_ROOT / "code/validate_corrected_source_package.py"
ALLOCATION_CSV = ENGINEERING_ROOT / "seven_family_allocation.csv"
CONTRACT_TEMPLATE = ENGINEERING_ROOT / "campaign_contract.template.json"

BATCH_ID = "m05_16h_90gb_campaign_batch0006"
CAMPAIGN_VERSION = "v1"
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
FORBIDDEN_SPECTRUM = "cosima_spectra_dp_2602units"
CORRECTED_SPECTRUM_ROOT = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
COSIMA_DEFAULT = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
COSIMA_SHA256 = "3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a"

GEOMETRIES = {
    "Mass_model_511": {
        "source_dir": PACKAGE_ROOT / "config/source_cards/mass_model_511",
        "setup_sha256": "f6ee8c36f45b6a66efa5544daf58a3431c6833289e5658eb8b4452f6792205b0",
        "runtime_bundle_sha256": "6170bfaaefaea1f9a85b9ca6dc51117fb1c9e08ba10f52c9436cedc4b57a0b61",
    },
    "S3d_O8": {
        "source_dir": PACKAGE_ROOT / "config/source_cards/s3d_o8",
        "setup_sha256": "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
        "runtime_bundle_sha256": "8cdb6577489cd049c812dbce1f1ad46225332141c9754cdf5a2eda58f4a73492",
    },
}
GEOMETRY_ORDER = ("Mass_model_511", "S3d_O8")
MODES = ("instant", "buildup")
FAMILIES = ("gamma", "neutron", "eplus", "eminus", "alpha", "muplus", "muminus", "proton")
SEVEN_FAMILIES = FAMILIES[:-1]
SOURCE_TAG = {"neutron": "n", "proton": "p", **{x: x for x in FAMILIES if x not in {"neutron", "proton"}}}
PARTICLE_TYPE = {"alpha": 21, "eminus": 3, "eplus": 2, "gamma": 1, "muminus": 9, "muplus": 8, "neutron": 6, "proton": 4}

SMOKE_PATTERNS = {
    "gamma": (3334, 3333, 3333),
    "neutron": (667, 667, 666),
    "eplus": (167, 167, 166),
    "eminus": (167, 167, 166),
    "alpha": (34, 33, 33),
    "muplus": (84, 83, 83),
    "muminus": (84, 83, 83),
    "proton": (64, 64, 64, 64),
}
PROTON_SEQUENCE = (512, 1024, *(2048 for _ in range(10)), 1105)
SEED_BASE = 1_306_000_006
SEED_STRIDE = 104_729
FARFIELD_RADIUS_CM = 60.0

TOTAL_SECONDS = 57_600
STAGES = {
    "stage00_mergeable_smoke": {"start_s": 0, "stop_launch_s": 5_700, "hard_end_s": 7_200, "declared_cap": 2_000_000_000},
    "stage10_seven_family": {"start_s": 7_200, "stop_launch_s": 41_700, "hard_end_s": 43_200, "declared_cap": 1_500_000_000},
    "stage20_proton": {"start_s": 43_200, "stop_launch_s": 55_800, "hard_end_s": 57_600, "declared_cap": 2_000_000_000},
}
REQUESTED_CAP_BYTES = 90_000_000_000
FILESYSTEM_RESERVE_BYTES = 20 * 1024**3
CAMPAIGN_EMERGENCY_BYTES = 5_000_000_000
SMOKE_HARD_CAP_BYTES = 8_000_000_000
RSS_SCALE_HEADROOM_BYTES = 2 * 1024**3
HARD_LOW_MEMORY_BYTES = 512 * 1024**2
MAX_ATTEMPTS = 2
POLL_SECONDS = 2.0
HANG_SECONDS = 15 * 60
CHECKPOINT_SECONDS = 30 * 60

GLOBAL_CONTRACT = RUN_ROOT / "global_contract.json"
EXECUTION_STATE = RUN_ROOT / "execution_state.json"
SEED_REGISTRY = RUN_ROOT / "seed_registry.json"
SMOKE_DECISION = RUN_ROOT / "smoke_decision.json"
RESOURCE_JSONL = RUN_ROOT / "resource_metrics.jsonl"
CONTROLLER_LOCK = RUN_ROOT / "controller.lock"

GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBS_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$")
SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)\s*$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")
ID_RE = re.compile(r"^ID\s+(\d+)\s*$")
INCLUDE_RE = re.compile(r"^\s*Include\s+(.+?)\s*(?:#.*)?$")
ENV_TOKEN_RE = re.compile(r"\$\(([^)]+)\)|\$\{([^}]+)\}")

_ACTIVE_PROCESS: subprocess.Popen[Any] | None = None
_STOP_REQUESTED = False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_once_json(path: Path, payload: Any) -> None:
    """Publish canonical JSON using link(2), never replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise RuntimeError(f"write-once authority differs: {rel(path)}")
        return
    partial = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.partial")
    partial.write_text(rendered, encoding="utf-8")
    try:
        os.link(partial, path)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != rendered:
            raise RuntimeError(f"concurrent write-once authority differs: {rel(path)}")
    finally:
        partial.unlink(missing_ok=True)


def atomic_replace_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.partial")
    partial.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def append_resource(payload: dict[str, Any]) -> None:
    RESOURCE_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with RESOURCE_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def source_card(geometry: str, family: str) -> Path:
    return Path(GEOMETRIES[geometry]["source_dir"]) / f"Background_{SOURCE_TAG[family]}_fullsphere20.source"


def source_geometry(path: Path) -> Path:
    found = [m.group(1) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if (m := GEOMETRY_RE.match(line.strip()))]
    if len(found) != 1:
        raise ValueError(f"{rel(path)} has {len(found)} Geometry lines")
    value = Path(found[0])
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


def source_flux(path: Path) -> float:
    values = [float(m.group(1)) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if (m := FLUX_RE.search(line))]
    if len(values) != 20 or any(x <= 0 or not math.isfinite(x) for x in values):
        raise ValueError(f"{rel(path)} does not contain 20 positive flux entries")
    return math.fsum(values)


def spectrum_support(path: Path) -> tuple[float, float]:
    energies: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "DP":
            energies.append(float(fields[1]))
    if len(energies) < 2 or any(not math.isfinite(x) for x in energies):
        raise ValueError(f"invalid corrected spectrum: {rel(path)}")
    return min(energies), max(energies)


def source_supports(path: Path) -> dict[int, tuple[float, float]]:
    refs = [m.group(1) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if (m := SPECTRUM_RE.search(line))]
    if len(refs) != 20 or any(FORBIDDEN_SPECTRUM in ref for ref in refs):
        raise ValueError(f"{rel(path)} corrected Spectrum File contract failed")
    if any(CORRECTED_SPECTRUM_ROOT not in ref for ref in refs):
        raise ValueError(f"{rel(path)} contains a non-corrected Spectrum File")
    return {index: spectrum_support((ROOT / ref).resolve()) for index, ref in enumerate(refs)}


def split_exact(total: int, size: int) -> list[int]:
    full, remainder = divmod(total, size)
    return [size] * full + ([remainder] if remainder else [])


def build_plan() -> list[dict[str, Any]]:
    """Build all stages and pre-register matched geometry-pair seeds."""
    jobs: list[dict[str, Any]] = []
    seed_by_key: dict[tuple[Any, ...], int] = {}

    def seed_for(key: tuple[Any, ...]) -> int:
        if key not in seed_by_key:
            seed_by_key[key] = SEED_BASE + (len(seed_by_key) + 1) * SEED_STRIDE
        return seed_by_key[key]

    def add(stage: str, geometry: str, mode: str, family: str, shard: int, events: int) -> None:
        key = (stage, mode, family, shard)
        seed = seed_for(key)
        token = {"stage00_mergeable_smoke": "s00", "stage10_seven_family": "s10", "stage20_proton": "s20"}[stage]
        jobs.append({
            "job_id": f"{token}_{family}_{mode}_{geometry}_shard{shard:04d}",
            "stage": stage,
            "geometry": geometry,
            "mode": mode,
            "family": family,
            "source_tag": SOURCE_TAG[family],
            "shard_ordinal": shard,
            "events": int(events),
            "seed": seed,
            "matched_seed_key": "|".join(map(str, key)),
        })

    for family in FAMILIES:
        for mode in MODES:
            for shard, events in enumerate(SMOKE_PATTERNS[family], 1):
                for geometry in GEOMETRY_ORDER:
                    add("stage00_mergeable_smoke", geometry, mode, family, shard, events)

    with ALLOCATION_CSV.open(newline="", encoding="utf-8") as handle:
        allocation = list(csv.DictReader(handle))
    family_order = list(dict.fromkeys(row["family"] for row in allocation))
    family_alias = {"neutron": "neutron", "n": "neutron"}
    for raw_family in family_order:
        rows = [row for row in allocation if row["family"] == raw_family]
        chunks = {
            (row["geometry"], row["mode"]): split_exact(int(row["stage10_point_events"]), int(row["initial_shard_events"]))
            for row in rows
        }
        family = family_alias.get(raw_family, raw_family)
        for shard in range(1, max(map(len, chunks.values())) + 1):
            for mode in MODES:
                for geometry in GEOMETRY_ORDER:
                    values = chunks.get((geometry, mode), [])
                    if shard <= len(values):
                        add("stage10_seven_family", geometry, mode, family, shard, values[shard - 1])

    # Fixed fairness order: Mass instant, O8 instant, Mass buildup, O8 buildup.
    for shard, events in enumerate(PROTON_SEQUENCE, 1):
        for geometry, mode in (
            ("Mass_model_511", "instant"), ("S3d_O8", "instant"),
            ("Mass_model_511", "buildup"), ("S3d_O8", "buildup"),
        ):
            add("stage20_proton", geometry, mode, "proton", shard, events)

    expected = {
        "stage00_mergeable_smoke": (100, 55_424),
        "stage10_seven_family": (None, 6_001_652),
        "stage20_proton": (52, 92_484),
    }
    for stage, (job_count, event_count) in expected.items():
        selected = [row for row in jobs if row["stage"] == stage]
        if job_count is not None and len(selected) != job_count:
            raise AssertionError(f"{stage}: jobs={len(selected)} expected {job_count}")
        if sum(int(row["events"]) for row in selected) != event_count:
            raise AssertionError(f"{stage}: event allocation mismatch")
    for row in jobs:
        if row["events"] <= 0 or not 1 <= row["seed"] < 2**31:
            raise AssertionError("invalid planned event count or Cosima seed")
    return jobs


def plan_summary(plan: list[dict[str, Any]], gate: dict[str, Any] | None = None) -> dict[str, Any]:
    stages = {}
    for stage, timing in STAGES.items():
        rows = [row for row in plan if row["stage"] == stage]
        stages[stage] = {
            **timing,
            "jobs": len(rows),
            "events": sum(int(row["events"]) for row in rows),
            "unique_matched_seeds": len({int(row["seed"]) for row in rows}),
        }
    return {
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "status": "READ_ONLY_PLAN__NO_TRANSPORT_LAUNCHED",
        "run_root": rel(RUN_ROOT),
        "arm": "F_RICH_BASELINE",
        "compact_transport_authorized": False,
        "mono511_source_forbidden": True,
        "physics": "QGSP_BIC_HP + LivermorePol; CUT frozen by binary+geometry+source hashes",
        "wall_seconds": TOTAL_SECONDS,
        "initial_workers": 1,
        "scale_up": "only after >=8 complete receipts and p95 RSS + 2 GiB < MemAvailable",
        "stages": stages,
        "total_jobs": len(plan),
        "total_events": sum(int(row["events"]) for row in plan),
        "planned_seed_registry_sha256": json_sha256(sorted({int(row["seed"]) for row in plan})),
        "print_plan_is_read_only": True,
        "preflight_gate": gate,
    }


def _extract_seed_values(value: Any, out: set[int], key_hint: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if "seed" in key.lower():
                if isinstance(child, int) and not isinstance(child, bool):
                    out.add(child)
                elif isinstance(child, list):
                    out.update(x for x in child if isinstance(x, int) and not isinstance(x, bool))
            _extract_seed_values(child, out, key)
    elif isinstance(value, list):
        for child in value:
            _extract_seed_values(child, out, key_hint)


def prior_seed_registry() -> set[int]:
    seeds: set[int] = set()
    for path in PRIOR_RUN_ROOT.rglob("*.json"):
        if RUN_ROOT in path.parents:
            continue
        try:
            _extract_seed_values(load_json(path), seeds)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    seed_line = re.compile(r"^\s*Seed\s+(\d+)\s*$")
    for path in PRIOR_RUN_ROOT.rglob("*.source"):
        if RUN_ROOT in path.parents:
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if match := seed_line.match(line):
                    seeds.add(int(match.group(1)))
        except OSError:
            continue
    return seeds


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing from /proc/meminfo")


def _dedupe_path(value: str) -> str:
    seen: set[str] = set()
    rows = []
    for item in value.split(":"):
        if item and item not in seen:
            seen.add(item)
            rows.append(item)
    return ":".join(rows)


def clean_transport_environment(cosima: Path) -> tuple[dict[str, str], dict[str, Any]]:
    setup = cosima.parent / "source-megalib.sh"
    if not setup.is_file():
        raise RuntimeError(f"missing MEGAlib setup: {setup}")
    home = str(Path.home())
    command = [
        "/usr/bin/env", "-i", f"HOME={home}", "USER=ubuntu", "LOGNAME=ubuntu",
        "PATH=/usr/bin:/bin", "SHELL=/bin/bash", "/bin/bash", "--noprofile", "--norc",
        "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(setup),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"clean MEGAlib environment failed: {result.stderr.decode(errors='replace')}")
    environment: dict[str, str] = {}
    for item in result.stdout.split(b"\0"):
        if item and b"=" in item:
            key, raw = item.split(b"=", 1)
            environment[key.decode(errors="replace")] = raw.decode(errors="replace")
    for key in ("PATH", "LD_LIBRARY_PATH"):
        environment[key] = _dedupe_path(environment.get(key, ""))
    relevant = {
        key: value for key, value in sorted(environment.items())
        if key in {"MEGALIB", "ROOTSYS"} or key.startswith("G4") or key.startswith("GEANT4")
    }
    return environment, {
        "setup": str(setup),
        "setup_sha256": sha256(setup),
        "relevant_environment": relevant,
        "relevant_environment_sha256": json_sha256(relevant),
        "path_and_ld_library_path_excluded_from_physics_digest": True,
    }


def _expand_tokens(value: str, environment: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1) or match.group(2)
        if key not in environment:
            raise RuntimeError(f"unset geometry environment token: {key}")
        return environment[key]
    return ENV_TOKEN_RE.sub(replace, value)


def geometry_bundle(geometry: str, environment: dict[str, str]) -> dict[str, Any]:
    setup = source_geometry(source_card(geometry, "gamma"))
    pending = [setup]
    seen: set[Path] = set()
    while pending:
        current = pending.pop().resolve()
        if current in seen:
            continue
        if not current.is_file():
            raise RuntimeError(f"missing geometry include: {current}")
        seen.add(current)
        for line in current.read_text(encoding="utf-8", errors="replace").splitlines():
            if match := INCLUDE_RE.match(line):
                fields = shlex.split(match.group(1), comments=True, posix=True)
                if len(fields) != 1:
                    raise RuntimeError(f"malformed Include: {line}")
                child = Path(_expand_tokens(fields[0], environment))
                pending.append((child if child.is_absolute() else current.parent / child).resolve())
    entries = [{"path": rel(path), "sha256": sha256(path)} for path in sorted(seen, key=rel)]
    digest = hashlib.sha256("".join(f"{x['path']}\0{x['sha256']}\n" for x in entries).encode()).hexdigest()
    return {"setup": rel(setup), "setup_sha256": sha256(setup), "files": entries, "file_count": len(entries), "bundle_sha256": digest}


def transport_fingerprint(cosima: Path, environment: dict[str, str], descriptor: dict[str, Any]) -> dict[str, Any]:
    if sha256(cosima) != COSIMA_SHA256:
        raise RuntimeError("Cosima binary hash differs from frozen batch0006 authority")
    ldd = subprocess.run(["ldd", str(cosima)], env=environment, text=True, capture_output=True, check=False)
    if ldd.returncode != 0 or "not found" in ldd.stdout:
        raise RuntimeError("Cosima resolved-library gate failed")
    libraries: list[dict[str, Any]] = []
    for line in ldd.stdout.splitlines():
        candidate = line.split("=>", 1)[1].strip().split()[0] if "=>" in line else line.strip().split()[0]
        path = Path(candidate)
        if path.is_file():
            libraries.append({"path": str(path.resolve()), "sha256": sha256(path.resolve())})
    g4_rows: list[dict[str, Any]] = []
    for key, value in sorted(environment.items()):
        if key.startswith("G4") and key.endswith("DATA"):
            root = Path(value).resolve()
            if not root.is_dir():
                raise RuntimeError(f"{key} is not a directory")
            inventory = []
            for path in sorted((x for x in root.rglob("*") if x.is_file()), key=lambda x: x.relative_to(root).as_posix()):
                inventory.append({"path": path.relative_to(root).as_posix(), "sha256": sha256(path)})
            g4_rows.append({"variable": key, "root": str(root), "files": len(inventory), "content_sha256": json_sha256(inventory)})
    if not g4_rows:
        raise RuntimeError("no G4*DATA roots in clean environment")
    return {
        "cosima": str(cosima), "cosima_sha256": sha256(cosima),
        "resolved_libraries": libraries, "resolved_libraries_sha256": json_sha256(libraries),
        "g4_data": g4_rows, "g4_data_sha256": json_sha256(g4_rows),
        "environment": descriptor,
    }


def run_static_validator() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(STATIC_VALIDATOR), "--check"], cwd=ROOT,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=1200,
    )
    if result.returncode != 0:
        raise RuntimeError("corrected-keV static validator failed:\n" + result.stdout[-4000:])
    payload = json.loads(result.stdout)
    source_packages = payload.get("source_packages", {})
    totals = {
        "spectra": int(payload.get("spectra", {}).get("files", -1)),
        "cards": int(source_packages.get("cards", -1)),
        "corrected_references": int(source_packages.get("spectrum_references", -1)),
        "legacy_references": int(source_packages.get("legacy_references", -1)),
    }
    if payload.get("status") != "PASS" or totals != {"spectra": 160, "cards": 24, "corrected_references": 480, "legacy_references": 0}:
        raise RuntimeError(f"static source counts mismatch: {totals}")
    return {"command": [rel(STATIC_VALIDATOR), "--check"], "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(), **totals, "status": "PASS"}


def preflight(plan: list[dict[str, Any]], cosima: Path) -> tuple[dict[str, Any], dict[str, str]]:
    if sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("source contract SHA-256 mismatch")
    static = run_static_validator()
    sources: dict[str, Any] = {}
    for geometry in GEOMETRY_ORDER:
        for family in FAMILIES:
            card = source_card(geometry, family)
            text = card.read_text(encoding="utf-8", errors="replace")
            if FORBIDDEN_SPECTRUM in text or "mono511" in text.lower():
                raise RuntimeError(f"legacy or mono511 source forbidden: {rel(card)}")
            source_supports(card)
            sources[f"{geometry}/{family}"] = {"path": rel(card), "sha256": sha256(card), "flux_cm2_s": source_flux(card)}
    environment, env_descriptor = clean_transport_environment(cosima)
    fingerprint = transport_fingerprint(cosima, environment, env_descriptor)
    bundles = {geometry: geometry_bundle(geometry, environment) for geometry in GEOMETRY_ORDER}
    for geometry, bundle in bundles.items():
        expected = GEOMETRIES[geometry]
        if bundle["bundle_sha256"] != expected["runtime_bundle_sha256"] or bundle["setup_sha256"] != expected["setup_sha256"]:
            raise RuntimeError(f"{geometry} runtime geometry bundle hash mismatch")
    prior = prior_seed_registry()
    planned = {int(row["seed"]) for row in plan}
    collision = sorted(prior & planned)
    if collision:
        raise RuntimeError(f"planned seeds collide with batch0000-0005/diagnostic registry: {collision[:10]}")
    free = shutil.disk_usage(RUN_ROOT.parent).free
    effective_cap = min(REQUESTED_CAP_BYTES, free - FILESYSTEM_RESERVE_BYTES)
    available = mem_available_bytes()
    if effective_cap <= CAMPAIGN_EMERGENCY_BYTES or free < FILESYSTEM_RESERVE_BYTES + 2_000_000_000:
        raise RuntimeError("T0 disk gate failed")
    if available <= RSS_SCALE_HEADROOM_BYTES:
        raise RuntimeError("T0 MemAvailable gate failed for one-worker launch")
    gate = {
        "status": "PASS__BATCH0006_STATIC_GATE",
        "source_contract": {"path": rel(SOURCE_CONTRACT), "sha256": SOURCE_CONTRACT_SHA256},
        "static_validator": static,
        "sources": sources,
        "geometry_bundles": bundles,
        "transport": fingerprint,
        "compact": {"transport_authorized": False, "selected_arm": "F_RICH_BASELINE"},
        "prior_registered_seed_count": len(prior),
        "prior_registered_seed_list_sha256": json_sha256(sorted(prior)),
        "planned_seed_count": len(planned),
        "planned_seed_list_sha256": json_sha256(sorted(planned)),
        "free_bytes_at_t0": free,
        "effective_campaign_cap_bytes": effective_cap,
        "mem_available_bytes": available,
    }
    return gate, environment


def build_contract(plan: list[dict[str, Any]], gate: dict[str, Any], started: datetime) -> dict[str, Any]:
    template = load_json(CONTRACT_TEMPLATE)
    template.update({
        "schema_version": 2,
        "status": "FROZEN__STATIC_GATE_PASS__TRANSPORT_PENDING",
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "wall_clock": {
            "t0": started.isoformat(), "deadline": (started + timedelta(seconds=TOTAL_SECONDS)).isoformat(),
            "total_seconds": TOTAL_SECONDS, "stages": [{"id": key, **value} for key, value in STAGES.items()],
        },
        "selected_arm": "F_RICH_BASELINE",
        "compact_transport_authorized": False,
        "static_gate": gate,
        "controller": {"path": rel(THIS_FILE), "sha256": sha256(THIS_FILE)},
        "planned_jobs": plan,
        "planned_jobs_sha256": json_sha256(plan),
        "attempt_contract": {
            "maximum_attempts": MAX_ATTEMPTS,
            "retry": "same seed, base source SHA, event count, geometry, mode, family; output paths only are attempt-local",
            "failed_attempts": rel(RUN_ROOT / "failed_attempts"),
            "canonical_receipts": rel(RUN_ROOT / "job_receipts"),
        },
    })
    template["disk"]["free_bytes_at_t0"] = gate["free_bytes_at_t0"]
    template["disk"]["effective_campaign_cap_bytes"] = gate["effective_campaign_cap_bytes"]
    template["scheduler"]["initial_processes"] = 1
    return template


def build_seed_registry(plan: list[dict[str, Any]], gate: dict[str, Any], contract_sha: str) -> dict[str, Any]:
    uses: dict[int, list[str]] = defaultdict(list)
    for row in plan:
        uses[int(row["seed"])].append(str(row["job_id"]))
    bad = {seed: jobs for seed, jobs in uses.items() if len(jobs) != 2 or {next(x["geometry"] for x in plan if x["job_id"] == job) for job in jobs} != set(GEOMETRY_ORDER)}
    if bad:
        raise RuntimeError(f"planned matched-pair seed use is not exactly two geometries: {list(bad)[:5]}")
    return {
        "schema_version": 1, "batch_id": BATCH_ID, "status": "FROZEN__ALL_PLANNED_SEEDS_REGISTERED",
        "global_contract_sha256": contract_sha,
        "exclusion": {
            "scope": "all discoverable batch0000-0005 and diagnostic JSON/source seeds",
            "count": gate["prior_registered_seed_count"], "sha256": gate["prior_registered_seed_list_sha256"],
        },
        "seed_base": SEED_BASE, "seed_stride": SEED_STRIDE,
        "planned_unique_seed_count": len(uses), "planned_seed_list_sha256": json_sha256(sorted(uses)),
        "planned": [{"seed": seed, "matched_geometry_jobs": sorted(jobs)} for seed, jobs in sorted(uses.items())],
        "retry_policy": "same registered seed; never replace a slow/large seed",
    }


def patch_source(base: Path, target: Path, *, mode: str, events: int, seed: int, sim_prefix: Path, isotope_prefix: Path) -> None:
    """Apply the sole deterministic, physics-preserving per-attempt transform."""
    rendered = patch_source_exact(
        base.read_text(encoding="utf-8"),
        seed=seed,
        events=events,
        sim_prefix=str(sim_prefix),
        isotope_prefix=str(isotope_prefix),
        mode=mode,
    )
    with target.open("x", encoding="utf-8") as handle:
        handle.write(rendered)


def parse_isotope_dat(path: Path) -> dict[str, Any]:
    tt: list[float] = []
    rp_count = 0
    rp_sum = 0.0
    current_volume: str | None = None
    isotope_totals: dict[tuple[str, int, float], float] = defaultdict(float)
    errors: list[str] = []
    end_count = 0
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT":
            try:
                value = float(fields[1]) if len(fields) == 2 else float("nan")
            except ValueError:
                value = float("nan")
            if not math.isfinite(value) or value <= 0:
                errors.append(f"line {number}: invalid TT")
            else:
                tt.append(value)
        elif fields[0] == "VN":
            current_volume = line[2:].strip() or None
            if current_volume is None:
                errors.append(f"line {number}: empty VN")
        elif fields[0] == "RP":
            if len(fields) != 4 or current_volume is None:
                errors.append(f"line {number}: malformed RP")
                continue
            try:
                isotope, excitation, value = int(fields[1]), float(fields[2]), float(fields[3])
            except ValueError:
                errors.append(f"line {number}: invalid RP numbers")
                continue
            if isotope <= 0 or excitation < 0 or value < 0 or not all(map(math.isfinite, (excitation, value))):
                errors.append(f"line {number}: invalid RP value")
                continue
            rp_count += 1
            rp_sum = math.fsum((rp_sum, value))
            isotope_totals[(current_volume, isotope, excitation)] = math.fsum((isotope_totals[(current_volume, isotope, excitation)], value))
        elif fields == ["EN"]:
            end_count += 1
        else:
            errors.append(f"line {number}: unrecognized {fields[0]}")
    if len(tt) != 1:
        errors.append(f"TT count={len(tt)}, expected 1")
    if end_count != 1:
        errors.append(f"EN count={end_count}, expected 1")
    return {
        "TT_s": tt[0] if len(tt) == 1 else None, "RP_record_count": rp_count, "RP_sum": rp_sum,
        "RP_totals": [{"volume": key[0], "isotope_id": key[1], "excitation_keV": key[2], "sum_RP": value} for key, value in sorted(isotope_totals.items())],
        "errors": errors,
    }


def parse_init(line: str) -> dict[str, float | int]:
    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise ValueError("malformed IA INIT")
    return {"particle_type": int(fields[15]), "dir_x": float(fields[16]), "dir_y": float(fields[17]), "dir_z": float(fields[18]), "energy_keV": float(fields[22])}


def scan_sim(path: Path, job: dict[str, Any], expected_geometry: Path, supports: dict[int, tuple[float, float]]) -> dict[str, Any]:
    errors: list[str] = []
    header_geometry: str | None = None
    header_seed: int | None = None
    next_id = 1
    events = 0
    init_records = 0
    current_id: int | None = None
    current_init = 0
    energy_min: float | None = None
    energy_max: float | None = None

    def finish() -> None:
        nonlocal current_id, current_init
        if current_id is not None and current_init != 1:
            errors.append(f"ID {current_id}: IA INIT count={current_init}")
        current_id = None
        current_init = 0

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if header_geometry is None and (match := GEOMETRY_RE.match(line)):
                header_geometry = match.group(1)
            if header_seed is None and line.startswith("Seed "):
                try:
                    header_seed = int(line.split()[1])
                except (IndexError, ValueError):
                    errors.append("malformed SIM Seed header")
            if line == "SE":
                finish()
            elif match := ID_RE.match(line):
                finish()
                current_id = int(match.group(1))
                if current_id != next_id:
                    errors.append(f"SIM ID {current_id}, expected {next_id}")
                next_id += 1
                events += 1
            elif line.startswith("IA INIT"):
                if current_id is None:
                    errors.append("IA INIT outside event")
                    continue
                current_init += 1
                init_records += 1
                try:
                    init = parse_init(line)
                    if int(init["particle_type"]) != PARTICLE_TYPE[job["family"]]:
                        errors.append("wrong IA INIT particle type")
                    direction = (float(init["dir_x"]), float(init["dir_y"]), float(init["dir_z"]))
                    if not math.isclose(math.sqrt(math.fsum(x * x for x in direction)), 1.0, abs_tol=5e-4):
                        errors.append("non-unit IA INIT direction")
                    energy = float(init["energy_keV"])
                    energy_min = energy if energy_min is None else min(energy_min, energy)
                    energy_max = energy if energy_max is None else max(energy_max, energy)
                    angular = max(0, min(19, int(math.floor((1.0 + direction[2]) * 10.0))))
                    low, high = supports[angular]
                    tolerance = max(0.002, 1e-10 * max(abs(low), abs(high)))
                    neighbor = [supports[i] for i in (angular - 1, angular + 1) if i in supports]
                    if not low - tolerance <= energy <= high + tolerance and not any(lo - tolerance <= energy <= hi + tolerance for lo, hi in neighbor):
                        errors.append("IA INIT energy outside corrected-keV support")
                except Exception as exc:
                    errors.append(str(exc))
            if len(errors) > 50:
                break
        finish()
    observed_geometry = Path(header_geometry) if header_geometry else None
    if observed_geometry and not observed_geometry.is_absolute():
        observed_geometry = (ROOT / observed_geometry).resolve()
    if observed_geometry != expected_geometry.resolve():
        errors.append("wrong or missing SIM Geometry header")
    if header_seed != int(job["seed"]):
        errors.append("wrong SIM Seed header")
    if events != int(job["events"]) or init_records != int(job["events"]):
        errors.append(f"requested={job['events']} events={events} IA_INIT={init_records}")
    return {"events": events, "IA_INIT": init_records, "energy_min_keV": energy_min, "energy_max_keV": energy_max, "geometry_header": header_geometry, "seed_header": header_seed, "errors": errors[:50]}


def process_group_metrics(pgid: int) -> tuple[int, int]:
    rss = cpu = 0
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            raw = stat_path.read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            if int(tail[2]) != pgid:
                continue
            cpu += int(tail[11]) + int(tail[12])
            status = stat_path.with_name("status").read_text()
            match = re.search(r"^VmRSS:\s+(\d+) kB", status, re.MULTILINE)
            rss += int(match.group(1)) * 1024 if match else 0
        except (OSError, ValueError, IndexError):
            continue
    return cpu, rss


def terminate_group(proc: subprocess.Popen[Any]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def campaign_bytes() -> int:
    if not RUN_ROOT.exists():
        return 0
    return sum(path.stat().st_size for path in RUN_ROOT.rglob("*") if path.is_file())


def disk_launch_gate(contract: dict[str, Any], stage: str) -> dict[str, Any]:
    cap = int(contract["disk"]["effective_campaign_cap_bytes"])
    declared = int(STAGES[stage]["declared_cap"])
    used = campaign_bytes()
    free = shutil.disk_usage(RUN_ROOT).free
    stage_limit = cap - (20_000_000_000 if stage == "stage10_seven_family" else CAMPAIGN_EMERGENCY_BYTES)
    errors = []
    if used + declared > stage_limit:
        errors.append("campaign_cap_with_stage_reservation")
    if free < FILESYSTEM_RESERVE_BYTES + declared:
        errors.append("filesystem_20GiB_reserve_plus_active_cap")
    if stage == "stage00_mergeable_smoke" and used + declared > SMOKE_HARD_CAP_BYTES:
        errors.append("smoke_8GB_hard_cap")
    return {"status": "PASS" if not errors else "STOP_LAUNCH", "campaign_bytes": used, "free_bytes": free, "declared_active_cap_bytes": declared, "stage_limit_bytes": stage_limit, "errors": errors}


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_ROOT / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def canonical_attempt_dir(job: dict[str, Any], attempt: int) -> Path:
    return RUN_ROOT / str(job["stage"]) / str(job["geometry"]) / str(job["mode"]) / str(job["family"]) / f"shard{int(job['shard_ordinal']):04d}" / f"attempt{attempt:02d}"


def validate_attempt(job: dict[str, Any], attempt_dir: Path, returncode: int, peak_rss: int, wall_s: float, watchdog: str, contract: dict[str, Any]) -> dict[str, Any]:
    base = source_card(job["geometry"], job["family"])
    name = job["job_id"]
    patched = attempt_dir / f"{name}.source"
    sim = attempt_dir / f"{name}.inc1.id1.sim.gz"
    dat = attempt_dir / f"{name}.dat.inc1.dat"
    log = attempt_dir / f"{name}.log"
    errors: list[str] = []
    for path in (patched, sim, dat, log):
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"missing/empty {path.name}")
    source_scan: dict[str, Any] = {}
    sim_scan: dict[str, Any] = {}
    isotope: dict[str, Any] = {}
    log_scan: dict[str, Any] = {}
    if patched.is_file():
        text = patched.read_text(encoding="utf-8", errors="replace")
        try:
            verify_source_patch_exact(
                base.read_text(encoding="utf-8"),
                text,
                seed=int(job["seed"]),
                events=int(job["events"]),
                sim_prefix=str(attempt_dir / name),
                isotope_prefix=str(attempt_dir / f"{name}.dat"),
                mode=str(job["mode"]),
            )
        except Exception as exc:
            errors.append(f"patched source byte-exact contract failed: {exc}")
        source_scan = {
            "base_source": rel(base), "base_source_sha256": sha256(base), "patched_source_sha256": sha256(patched),
            "corrected_references": text.count(CORRECTED_SPECTRUM_ROOT), "legacy_references": text.count(FORBIDDEN_SPECTRUM),
            "seed_lines": text.count(f"Seed {job['seed']}"), "event_lines": sum(line.strip().endswith(f".Events {job['events']}") for line in text.splitlines()),
        }
        if source_scan["corrected_references"] != 20 or source_scan["legacy_references"] or source_scan["seed_lines"] != 1 or source_scan["event_lines"] != 1:
            errors.append("patched source deterministic contract failed")
        if source_geometry(patched) != source_geometry(base):
            errors.append("patched source geometry differs from base")
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")
        generated = GENERATED_RE.search(text)
        cpu = CPU_RE.search(text)
        observation = OBS_RE.search(text)
        log_scan = {
            "generated": int(generated.group(1)) if generated else None,
            "beam_on_cpu_s": float(cpu.group(1)) if cpu else None,
            "observation_time_s": float(observation.group(1)) if observation else None,
            "error_marker": "***  Error" in text or "Segmentation fault" in text or "Unable to parse" in text,
        }
        if returncode != 0 or log_scan["generated"] != int(job["events"]) or log_scan["error_marker"]:
            errors.append("Cosima return/generated/log error gate failed")
    if sim.is_file() and sim.stat().st_size:
        try:
            sim_scan = scan_sim(sim, job, source_geometry(base), source_supports(base))
            errors.extend(sim_scan["errors"])
        except Exception as exc:
            errors.append(f"SIM scan exception: {exc}")
    if dat.is_file() and dat.stat().st_size:
        isotope = parse_isotope_dat(dat)
        errors.extend(isotope["errors"])
        tt = isotope.get("TT_s")
        obs = log_scan.get("observation_time_s")
        if tt is not None and obs is not None and not math.isclose(float(tt), float(obs), rel_tol=2e-3, abs_tol=2e-6):
            errors.append(f"DAT TT={tt} differs from log observation={obs}")
    artifacts = {}
    for label, path in (("source", patched), ("sim", sim), ("dat", dat), ("log", log)):
        if path.is_file():
            artifacts[label] = {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
    return {
        "status": "PASS" if not errors else "FAIL", "errors": errors[:100],
        "global_contract_sha256": sha256(GLOBAL_CONTRACT), "job": job,
        "source": source_scan, "log": log_scan, "sim": sim_scan, "isotope_dat": isotope,
        "returncode": returncode, "watchdog_reason": watchdog, "wall_s": wall_s,
        "peak_process_group_rss_bytes": peak_rss, "artifacts": artifacts,
        "campaign_bytes_after_attempt": campaign_bytes(), "free_disk_bytes_after_attempt": shutil.disk_usage(RUN_ROOT).free,
        "mem_available_bytes_after_attempt": mem_available_bytes(),
    }


def receipt_hashes_valid(receipt: dict[str, Any]) -> bool:
    if receipt.get("status") != "PASS" or receipt.get("global_contract_sha256") != sha256(GLOBAL_CONTRACT):
        return False
    directory = ROOT / receipt["attempt_dir"]
    for artifact in receipt.get("artifacts", {}).values():
        path = directory / artifact["name"]
        if not path.is_file() or path.stat().st_size != int(artifact["bytes"]) or sha256(path) != artifact["sha256"]:
            return False
    return True


def run_attempt(job: dict[str, Any], attempt: int, contract: dict[str, Any], environment: dict[str, str], hard_deadline: datetime) -> dict[str, Any]:
    global _ACTIVE_PROCESS
    canonical = canonical_attempt_dir(job, attempt)
    partial = canonical.with_name(f".{canonical.name}.partial")
    if canonical.exists() or partial.exists():
        raise RuntimeError(f"attempt path already exists: {rel(canonical)}")
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.mkdir()
    name = str(job["job_id"])
    base = source_card(job["geometry"], job["family"])
    patched = partial / f"{name}.source"
    sim_prefix = partial / name
    isotope_prefix = partial / f"{name}.dat"
    log = partial / f"{name}.log"
    patch_source(base, patched, mode=str(job["mode"]), events=int(job["events"]), seed=int(job["seed"]), sim_prefix=sim_prefix, isotope_prefix=isotope_prefix)
    command = [contract["static_gate"]["transport"]["cosima"], "-s", str(job["seed"]), str(patched)]
    started = time.monotonic()
    peak_rss = 0
    watchdog = "completed"
    last_activity = started
    previous_cpu = previous_growth = 0
    returncode = -999
    with log.open("x", encoding="utf-8", buffering=1) as handle:
        handle.write(json.dumps({"job": job, "attempt": attempt, "base_source": rel(base), "base_source_sha256": sha256(base)}, sort_keys=True) + "\n")
        handle.write(f"cosima_command={' '.join(command)}\n")
        handle.flush()
        proc = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        _ACTIVE_PROCESS = proc
        while proc.poll() is None:
            time.sleep(POLL_SECONDS)
            now = time.monotonic()
            cpu, rss = process_group_metrics(proc.pid)
            peak_rss = max(peak_rss, rss)
            growth = sum(path.stat().st_size for path in partial.rglob("*") if path.is_file())
            if cpu > previous_cpu or growth > previous_growth:
                last_activity = now
            previous_cpu, previous_growth = cpu, growth
            reason: str | None = None
            if _STOP_REQUESTED:
                reason = "controller_stop_requested"
            elif datetime.now(timezone.utc) >= hard_deadline:
                reason = "stage_hard_deadline"
            elif growth > int(STAGES[str(job["stage"])]["declared_cap"]):
                reason = "attempt_declared_cap_exceeded"
            elif shutil.disk_usage(RUN_ROOT).free < FILESYSTEM_RESERVE_BYTES:
                reason = "filesystem_20GiB_floor"
            elif mem_available_bytes() < HARD_LOW_MEMORY_BYTES:
                reason = "hard_low_memory_512MiB"
            elif now - last_activity > HANG_SECONDS:
                reason = "watchdog_no_cpu_or_growth_15m"
            if reason:
                watchdog = reason
                terminate_group(proc)
                break
        returncode = proc.wait()
        _ACTIVE_PROCESS = None
        handle.write(f"watchdog_reason={watchdog}\npeak_process_group_rss_bytes={peak_rss}\nreturncode={returncode}\nwall_s={time.monotonic() - started:.6f}\n")
    wall_s = time.monotonic() - started
    validation = validate_attempt(job, partial, returncode, peak_rss, wall_s, watchdog, contract)
    if validation["status"] == "PASS":
        os.replace(partial, canonical)
        validation["selected_attempt"] = attempt
        validation["attempt_dir"] = rel(canonical)
        receipt = receipt_path(job)
        atomic_write_once_json(receipt, validation)
        append_resource({"at": datetime.now(timezone.utc).isoformat(), "job_id": job["job_id"], "attempt": attempt, "status": "PASS", "wall_s": wall_s, "beam_on_cpu_s": validation["log"].get("beam_on_cpu_s"), "bytes": sum(x["bytes"] for x in validation["artifacts"].values()), "peak_process_group_rss_bytes": peak_rss, "free_disk_bytes": validation["free_disk_bytes_after_attempt"], "TT_s": validation["isotope_dat"].get("TT_s"), "RP_count": validation["isotope_dat"].get("RP_record_count")})
        return validation
    failed = RUN_ROOT / "failed_attempts" / name / f"attempt{attempt:02d}"
    failed.parent.mkdir(parents=True, exist_ok=True)
    os.replace(partial, failed)
    atomic_write_once_json(failed / "validation.json", {**validation, "attempt_dir": rel(failed), "selected_attempt": None})
    append_resource({"at": datetime.now(timezone.utc).isoformat(), "job_id": job["job_id"], "attempt": attempt, "status": "FAIL", "errors": validation["errors"], "wall_s": wall_s, "peak_process_group_rss_bytes": peak_rss})
    return validation


def ensure_job(job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_deadline: datetime) -> dict[str, Any]:
    receipt = receipt_path(job)
    if receipt.is_file():
        payload = load_json(receipt)
        if not receipt_hashes_valid(payload):
            raise RuntimeError(f"immutable PASS receipt failed hash revalidation: {job['job_id']}")
        return payload
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if datetime.now(timezone.utc) >= hard_deadline:
            raise RuntimeError("stage hard deadline before attempt")
        result = run_attempt(job, attempt, contract, environment, hard_deadline)
        if result["status"] == "PASS":
            return result
    raise RuntimeError(f"{job['job_id']} failed {MAX_ATTEMPTS} exact same-seed attempts")


def stage_paths(stage: str) -> tuple[Path, Path]:
    if stage == "stage00_mergeable_smoke":
        return RUN_ROOT / "checkpoint_authority/smoke_validation.json", RUN_ROOT / "checkpoint_authority/smoke_ledger.json"
    if stage == "stage10_seven_family":
        return RUN_ROOT / "seven_family_validation.json", RUN_ROOT / "seven_family_ledger.json"
    return RUN_ROOT / "proton_validation.json", RUN_ROOT / "proton_ledger.json"


def publish_stage(stage: str, plan: list[dict[str, Any]], contract: dict[str, Any], failure: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    jobs = [row for row in plan if row["stage"] == stage]
    receipts = []
    missing = []
    for job in jobs:
        path = receipt_path(job)
        if path.is_file():
            receipt = load_json(path)
            if receipt_hashes_valid(receipt):
                receipts.append(receipt)
            else:
                missing.append({"job_id": job["job_id"], "reason": "receipt_hash_revalidation_failed"})
        else:
            missing.append({"job_id": job["job_id"], "reason": "missing_or_partial"})
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    for receipt in receipts:
        job = receipt["job"]
        key = (job["geometry"], job["mode"], job["family"])
        cell = cells.setdefault(key, {"geometry": key[0], "mode": key[1], "family": key[2], "events": 0, "TT_s": 0.0, "RP_count": 0, "jobs": 0})
        cell["events"] += int(job["events"])
        cell["TT_s"] = math.fsum((cell["TT_s"], float(receipt["isotope_dat"]["TT_s"])))
        cell["RP_count"] += int(receipt["isotope_dat"]["RP_record_count"])
        cell["jobs"] += 1
    complete = not missing and failure is None
    if stage == "stage00_mergeable_smoke" and not complete:
        status = "FAIL__F_SMOKE_NOT_COMPLETE__PRODUCTION_STOP"
    else:
        status = "PASS__COMPLETE_PREFIX" if complete else "PASS__VALIDATED_PARTIAL_PREFIX"
    validation = {
        "schema_version": 1, "batch_id": BATCH_ID, "stage": stage, "status": status,
        "errors": [failure] if failure else [], "global_contract_sha256": sha256(GLOBAL_CONTRACT),
        "planned_jobs": len(jobs), "validated_jobs": len(receipts), "planned_events": sum(int(x["events"]) for x in jobs),
        "validated_events": sum(int(x["job"]["events"]) for x in receipts), "missing_or_partial": missing,
        "cells": [cells[key] for key in sorted(cells)],
        "actual": {
            "wall_s": math.fsum(float(x["wall_s"]) for x in receipts),
            "beam_on_cpu_s": math.fsum(float(x["log"].get("beam_on_cpu_s") or 0) for x in receipts),
            "TT_s": math.fsum(float(x["isotope_dat"]["TT_s"]) for x in receipts),
            "RP_count": sum(int(x["isotope_dat"]["RP_record_count"]) for x in receipts),
            "peak_process_group_rss_bytes": max((int(x["peak_process_group_rss_bytes"]) for x in receipts), default=0),
            "artifact_bytes": sum(sum(int(a["bytes"]) for a in x["artifacts"].values()) for x in receipts),
        },
        "merge_domains": "never pool across geometry, mode, or family; prompt=sum(selected)/sum(TT); BUILDUP=sum(RP)/sum(TT) by volume+isotope-state",
    }
    report_path, ledger_path = stage_paths(stage)
    atomic_write_once_json(report_path, validation)
    ledger = {
        "schema_version": 1, "batch_id": BATCH_ID, "stage": stage,
        "status": ("PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE" if stage == "stage00_mergeable_smoke" and complete else status),
        "validation": rel(report_path), "validation_sha256": sha256(report_path),
        "global_contract_sha256": sha256(GLOBAL_CONTRACT),
        "selected_receipts": [{"job_id": x["job"]["job_id"], "path": rel(receipt_path(x["job"])), "sha256": sha256(receipt_path(x["job"]))} for x in receipts],
        "missing_or_partial": missing, "cells": validation["cells"], "errors": validation["errors"],
    }
    atomic_write_once_json(ledger_path, ledger)
    return validation, ledger


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed_jobs: int, last_error: str | None = None) -> None:
    atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1, "batch_id": BATCH_ID, "status": status, "stage": stage,
        "t0": contract["wall_clock"]["t0"], "deadline": contract["wall_clock"]["deadline"],
        "global_contract_sha256": sha256(GLOBAL_CONTRACT), "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_jobs": completed_jobs, "campaign_bytes": campaign_bytes(), "free_disk_bytes": shutil.disk_usage(RUN_ROOT).free,
        "mem_available_bytes": mem_available_bytes(), "last_error": last_error,
    })


def wait_until(moment: datetime, contract: dict[str, Any], stage: str, plan: list[dict[str, Any]]) -> None:
    last = time.monotonic()
    while datetime.now(timezone.utc) < moment and not _STOP_REQUESTED:
        time.sleep(min(30, max(0.1, (moment - datetime.now(timezone.utc)).total_seconds())))
        if time.monotonic() - last >= CHECKPOINT_SECONDS:
            completed = sum(receipt_path(job).is_file() for job in plan)
            update_state(contract, status="WAITING_FOR_FIXED_STAGE_BOUNDARY", stage=stage, completed_jobs=completed)
            last = time.monotonic()


def run_stage(stage: str, plan: list[dict[str, Any]], contract: dict[str, Any], environment: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    timing = STAGES[stage]
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    start = t0 + timedelta(seconds=int(timing["start_s"]))
    stop_launch = t0 + timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + timedelta(seconds=int(timing["hard_end_s"]))
    wait_until(start, contract, stage, plan)
    failure: str | None = None
    last_checkpoint = time.monotonic()
    for job in (row for row in plan if row["stage"] == stage):
        if receipt_path(job).is_file():
            if not receipt_hashes_valid(load_json(receipt_path(job))):
                failure = f"receipt revalidation failed: {job['job_id']}"
                break
            continue
        if _STOP_REQUESTED or datetime.now(timezone.utc) >= stop_launch:
            break
        gate = disk_launch_gate(contract, stage)
        if gate["status"] != "PASS":
            failure = "disk stop-launch gate: " + ",".join(gate["errors"])
            break
        if mem_available_bytes() <= RSS_SCALE_HEADROOM_BYTES:
            failure = "RSS/MemAvailable stop-launch gate"
            break
        try:
            ensure_job(job, contract, environment, hard_end)
        except Exception as exc:
            failure = str(exc)
            break
        if time.monotonic() - last_checkpoint >= CHECKPOINT_SECONDS:
            completed = sum(receipt_path(row).is_file() for row in plan)
            update_state(contract, status="RUNNING", stage=stage, completed_jobs=completed)
            last_checkpoint = time.monotonic()
    if stage == "stage00_mergeable_smoke":
        validation, ledger = publish_stage(stage, plan, contract, failure)
        atomic_write_once_json(SMOKE_DECISION, {
            "batch_id": BATCH_ID, "selected_arm": "F_RICH_BASELINE", "compact_transport_authorized": False,
            "status": ledger["status"], "F_validation": rel(stage_paths(stage)[0]), "F_validation_sha256": sha256(stage_paths(stage)[0]),
            "production_may_continue": ledger["status"] == "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE",
        })
        return validation, ledger
    return publish_stage(stage, plan, contract, failure)


def publish_final(plan: list[dict[str, Any]], contract: dict[str, Any], fatal: str | None = None) -> None:
    stages = {}
    for stage in STAGES:
        report, ledger = stage_paths(stage)
        stages[stage] = {
            "validation": rel(report) if report.exists() else None, "validation_sha256": sha256(report) if report.exists() else None,
            "ledger": rel(ledger) if ledger.exists() else None, "ledger_sha256": sha256(ledger) if ledger.exists() else None,
        }
    receipts = [load_json(receipt_path(job)) for job in plan if receipt_path(job).is_file()]
    missing = [job["job_id"] for job in plan if not receipt_path(job).is_file()]
    validation = {
        "schema_version": 1, "batch_id": BATCH_ID,
        "status": "PASS__VALIDATED_CAMPAIGN_PREFIX" if receipts else "FAIL__NO_VALIDATED_SHARDS",
        "errors": [fatal] if fatal else [], "authority_boundary": "CORRECTED_KEV_MERGEABLE_SCREENING_AND_PARTIAL_PRODUCTION_ONLY",
        "global_contract_sha256": sha256(GLOBAL_CONTRACT), "stages": stages,
        "validated_jobs": len(receipts), "validated_events": sum(int(x["job"]["events"]) for x in receipts),
        "missing_jobs": missing, "campaign_bytes": campaign_bytes(),
        "actual": {
            "wall_s": math.fsum(float(x["wall_s"]) for x in receipts), "beam_on_cpu_s": math.fsum(float(x["log"].get("beam_on_cpu_s") or 0) for x in receipts),
            "TT_s": math.fsum(float(x["isotope_dat"]["TT_s"]) for x in receipts), "RP_count": sum(int(x["isotope_dat"]["RP_record_count"]) for x in receipts),
            "peak_process_group_rss_bytes": max((int(x["peak_process_group_rss_bytes"]) for x in receipts), default=0),
        },
    }
    final_validation = RUN_ROOT / "final_validation.json"
    final_ledger = RUN_ROOT / "final_ledger.json"
    atomic_write_once_json(final_validation, validation)
    ledger = {
        "schema_version": 1, "batch_id": BATCH_ID, "status": validation["status"],
        "validation": rel(final_validation), "validation_sha256": sha256(final_validation), "stages": stages,
        "selected_receipts": [{"path": rel(receipt_path(x["job"])), "sha256": sha256(receipt_path(x["job"]))} for x in receipts],
        "missing_jobs": missing, "errors": validation["errors"],
    }
    atomic_write_once_json(final_ledger, ledger)
    atomic_write_once_json(RUN_ROOT / "final_umbrella.json", {
        "schema_version": 1, "batch_id": BATCH_ID, "status": validation["status"],
        "global_contract": rel(GLOBAL_CONTRACT), "global_contract_sha256": sha256(GLOBAL_CONTRACT),
        "seed_registry": rel(SEED_REGISTRY), "seed_registry_sha256": sha256(SEED_REGISTRY),
        "final_validation": rel(final_validation), "final_validation_sha256": sha256(final_validation),
        "final_ledger": rel(final_ledger), "final_ledger_sha256": sha256(final_ledger),
        "authority_exclusions": ["full eight-family delayed response", "mission sensitivity", "geometry promotion", "strict proton r1 convergence"],
    })


def _signal_handler(signum: int, _frame: Any) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    if _ACTIVE_PROCESS is not None:
        terminate_group(_ACTIVE_PROCESS)


def acquire_lock() -> Any:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    handle = CONTROLLER_LOCK.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise SystemExit("another batch0006 controller holds the lock")
    return handle


def create_or_load(plan: list[dict[str, Any]], cosima: Path, proposed_t0: datetime) -> tuple[dict[str, Any], dict[str, str]]:
    if GLOBAL_CONTRACT.exists():
        contract = load_json(GLOBAL_CONTRACT)
        if contract.get("batch_id") != BATCH_ID or contract.get("planned_jobs_sha256") != json_sha256(plan):
            raise RuntimeError("existing batch0006 global contract differs")
        environment, descriptor = clean_transport_environment(cosima)
        current = transport_fingerprint(cosima, environment, descriptor)
        frozen = contract["static_gate"]["transport"]
        for key in ("cosima_sha256", "resolved_libraries_sha256", "g4_data_sha256"):
            if current[key] != frozen[key]:
                raise RuntimeError(f"resume transport fingerprint drift: {key}")
        return contract, environment
    gate, environment = preflight(plan, cosima)
    contract = build_contract(plan, gate, proposed_t0)
    atomic_write_once_json(GLOBAL_CONTRACT, contract)
    registry = build_seed_registry(plan, gate, sha256(GLOBAL_CONTRACT))
    atomic_write_once_json(SEED_REGISTRY, registry)
    for path in (RUN_ROOT / "stage00_mergeable_smoke", RUN_ROOT / "stage10_seven_family", RUN_ROOT / "stage20_proton", RUN_ROOT / "job_receipts", RUN_ROOT / "checkpoint_authority", RUN_ROOT / "failed_attempts"):
        path.mkdir(parents=True, exist_ok=True)
    update_state(contract, status="PASS__STATIC_GATE__TRANSPORT_READY", stage="preflight", completed_jobs=0)
    return contract, environment


def run_campaign(plan: list[dict[str, Any]], contract: dict[str, Any], environment: dict[str, str]) -> int:
    fatal: str | None = None
    try:
        smoke_validation, smoke_ledger = run_stage("stage00_mergeable_smoke", plan, contract, environment)
        if smoke_ledger["status"] != "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE":
            raise RuntimeError("F smoke failed/incomplete; 14-hour production forbidden")
        run_stage("stage10_seven_family", plan, contract, environment)
        run_stage("stage20_proton", plan, contract, environment)
    except Exception as exc:
        fatal = str(exc)
    finally:
        publish_final(plan, contract, fatal)
        completed = sum(receipt_path(job).is_file() for job in plan)
        update_state(contract, status="FINALIZED" if fatal is None else "FINALIZED_WITH_ERROR", stage="final", completed_jobs=completed, last_error=fatal)
    if fatal:
        raise SystemExit(fatal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true", help="read-only full preflight and plan summary; never creates run output")
    parser.add_argument("--cosima", type=Path, default=COSIMA_DEFAULT)
    args = parser.parse_args()
    plan = build_plan()
    proposed_t0 = datetime.now(timezone.utc)
    if args.print_plan:
        if RUN_ROOT.exists():
            before = sorted((rel(path), path.stat().st_mtime_ns, path.stat().st_size) for path in RUN_ROOT.rglob("*") if path.is_file())
        else:
            before = []
        gate, _environment = preflight(plan, args.cosima.resolve())
        print(json.dumps(plan_summary(plan, gate), indent=2, ensure_ascii=False, sort_keys=True))
        after = sorted((rel(path), path.stat().st_mtime_ns, path.stat().st_size) for path in RUN_ROOT.rglob("*") if path.is_file()) if RUN_ROOT.exists() else []
        if before != after:
            raise RuntimeError("--print-plan read-only sentinel detected a run-root mutation")
        return 0
    lock = acquire_lock()
    previous = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, _signal_handler)
        contract, environment = create_or_load(plan, args.cosima.resolve(), proposed_t0)
        return run_campaign(plan, contract, environment)
    finally:
        if _ACTIVE_PROCESS is not None:
            terminate_group(_ACTIVE_PROCESS)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
