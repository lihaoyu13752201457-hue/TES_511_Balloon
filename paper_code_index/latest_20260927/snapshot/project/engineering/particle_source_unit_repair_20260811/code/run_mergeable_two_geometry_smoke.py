#!/usr/bin/env python3
"""Run the corrected-source, production-mergeable two-geometry smoke.

This is deliberately a fixed campaign rather than a general simulation CLI.
It runs the complete retained eight-family/20-angular-bin source at small
statistics for Mass_model_511 and S3d-O8 in both prompt (``instant``) and
activation-build-up modes.  A mode uses the same seeds for the two geometries,
while the two modes use disjoint seed registries.

The four output directories are write-once.  A partial campaign is not resumed
or overwritten: recovery must use a new batch/version name and a new seed
registry so that every accepted batch remains auditable and mergeable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
BUILDER = PACKAGE / "code/build_corrected_source_package.py"
STATIC_VALIDATOR = PACKAGE / "code/validate_corrected_source_package.py"
DYNAMIC_VALIDATOR = PACKAGE / "code/validate_mergeable_two_geometry_smoke.py"
SOURCE_CONTRACT = PACKAGE / "data/source_contract_manifest.json"

BATCH_ID = "corrected_original_all8_fullsphere20_batch0000"
CAMPAIGN_VERSION = "mergeable_smoke_v1"
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
GEOMETRIES = {
    "mass_model_511": PACKAGE / "config/source_cards/mass_model_511",
    "s3d_o8": PACKAGE / "config/source_cards/s3d_o8",
}
MODES = ("instant", "buildup")

# The runner uses seed = seed_base + one_based_job_ordinal * seed_stride.
# Each mode has exactly eight jobs.  Sharing a mode's registry across geometry
# is intentional matched-A/B provenance; pooling across geometry is forbidden.
SEED_BASE_BY_MODE = {"instant": 81_100_003, "buildup": 82_100_003}
SEED_STRIDE = 7_919
GAMMA_EVENTS = 1_000
GAMMA_SPLITS = 1
NON_GAMMA_REPLICAS = 1
FARFIELD_RADIUS_CM = 60.0
EXPECTED_JOBS_PER_CAMPAIGN = 8

GLOBAL_CONTRACT = RUN_ROOT / "mergeable_smoke_v1_contract.json"
VALIDATION_REPORT = RUN_ROOT / "mergeable_smoke_v1_validation.json"
MERGE_LEDGER = RUN_ROOT / "mergeable_smoke_v1_ledger.json"
INCLUDE_RE = re.compile(r"^\s*Include\s+(.+?)\s*(?:#.*)?$")
ENV_TOKEN_RE = re.compile(r"\$\(([^)]+)\)|\$\{([^}]+)\}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_repo_path_for_harness(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def canonical_digest(entries: list[dict[str, str]]) -> str:
    payload = "".join(f"{entry['path']}\0{entry['sha256']}\n" for entry in entries)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _expand_environment_tokens(value: str, environment: dict[str, str]) -> str:
    def replacement(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in environment:
            raise SystemExit(f"geometry Include uses unset environment variable {name!r}")
        return environment[name]

    return ENV_TOKEN_RE.sub(replacement, value)


def geometry_setup_path(geometry: str) -> Path:
    manifest = json.loads(source_manifest_path(geometry).read_text(encoding="utf-8"))
    value = Path(str(manifest["geometry_setup"]))
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


def build_geometry_bundle(geometry: str, environment: dict[str, str]) -> dict[str, Any]:
    """Hash the setup and every transitively included geometry/material file."""
    setup = geometry_setup_path(geometry)
    pending = [setup]
    seen: set[Path] = set()
    while pending:
        current = pending.pop()
        current = current.resolve()
        if current in seen:
            continue
        if not current.is_file():
            raise SystemExit(f"{geometry}: missing transitive geometry Include {current}")
        seen.add(current)
        for raw in current.read_text(encoding="utf-8", errors="replace").splitlines():
            match = INCLUDE_RE.match(raw)
            if not match:
                continue
            fields = shlex.split(match.group(1), comments=True, posix=True)
            if len(fields) != 1:
                raise SystemExit(f"{geometry}: malformed Include in {current}: {raw}")
            expanded = _expand_environment_tokens(fields[0], environment)
            child = Path(expanded)
            if not child.is_absolute():
                child = current.parent / child
            pending.append(child.resolve())
    entries = [
        {"path": rel(path), "sha256": sha256(path)}
        for path in sorted(seen, key=lambda item: rel(item))
    ]
    suffixes = {Path(entry["path"]).suffix for entry in entries}
    for required in (".setup", ".geo", ".det"):
        if required not in suffixes:
            raise SystemExit(f"{geometry}: geometry bundle has no {required} file")
    return {
        "setup": rel(setup),
        "files": entries,
        "file_count": len(entries),
        "bundle_sha256": canonical_digest(entries),
        "digest_contract": "SHA256 of sorted path\\0sha256\\n records",
    }


def resolve_transport_environment(cosima: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Load the matching MEGAlib environment without changing this process."""
    environment = dict(os.environ)
    setup = cosima.parent / "source-megalib.sh"
    if setup.is_file():
        result = subprocess.run(
            ["bash", "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(setup)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(f"failed to load MEGAlib environment from {setup}")
        environment = {}
        for item in result.stdout.split(b"\0"):
            if not item or b"=" not in item:
                continue
            key, value = item.split(b"=", 1)
            environment[key.decode(errors="replace")] = value.decode(errors="replace")
    relevant = {
        key: value
        for key, value in sorted(environment.items())
        if key in {"MEGALIB", "ROOTSYS", "LD_LIBRARY_PATH"}
        or key.startswith("GEANT4")
        or key.startswith("G4")
    }
    relevant_payload = json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode("utf-8")
    descriptor = {
        "setup_script": rel(setup) if setup.is_file() else None,
        "setup_script_sha256": sha256(setup) if setup.is_file() else None,
        "relevant_variables": relevant,
        "relevant_variables_sha256": hashlib.sha256(relevant_payload).hexdigest(),
        "observed_PATH_not_in_physics_digest": environment.get("PATH"),
        "g4_data_roots": build_g4_data_fingerprint(environment, hash_contents=True),
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
    }
    return environment, descriptor


def build_g4_data_fingerprint(environment: dict[str, str], *, hash_contents: bool) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    for variable, value in sorted(environment.items()):
        if not (variable.startswith("G4") and variable.endswith("DATA")):
            continue
        root = Path(value).resolve()
        if not root.is_dir():
            raise SystemExit(f"{variable} is not a directory: {root}")
        stat_digest = hashlib.sha256()
        content_digest = hashlib.sha256() if hash_contents else None
        file_count = 0
        total_bytes = 0
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
            file_count += 1
            total_bytes += stat.st_size
            stat_digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
            if content_digest is not None:
                content_digest.update(f"{relative}\0{sha256(path)}\n".encode("utf-8"))
        roots.append(
            {
                "variable": variable,
                "path": str(root),
                "file_count": file_count,
                "total_bytes": total_bytes,
                "stat_inventory_sha256": stat_digest.hexdigest(),
                "content_inventory_sha256": content_digest.hexdigest() if content_digest is not None else None,
            }
        )
    if not roots:
        raise SystemExit("no G4*DATA roots found in the transport environment")
    return roots


def _transport_libraries(cosima: Path, environment: dict[str, str]) -> list[dict[str, str]]:
    result = subprocess.run(
        ["ldd", str(cosima)],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"ldd failed for {cosima}: {result.stdout.strip()}")
    paths: set[Path] = set()
    for line in result.stdout.splitlines():
        fields = line.strip().split()
        candidate: str | None = None
        if "=>" in fields:
            index = fields.index("=>")
            if index + 1 < len(fields) and fields[index + 1] != "not":
                candidate = fields[index + 1]
        elif fields and fields[0].startswith("/"):
            candidate = fields[0]
        if candidate:
            path = Path(candidate).resolve()
            if path.is_file():
                paths.add(path)
    entries = [{"path": str(path), "sha256": sha256(path)} for path in sorted(paths)]
    if not entries:
        raise SystemExit(f"no resolved shared libraries found for {cosima}")
    return entries


def build_transport_fingerprint(cosima: Path, environment: dict[str, str], descriptor: dict[str, Any]) -> dict[str, Any]:
    banner_result = subprocess.run(
        [str(cosima), "--help"],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    banner = banner_result.stdout[:20_000]
    if "Cosima" not in banner or "MEGAlib version" not in banner:
        raise SystemExit(f"unable to fingerprint Cosima banner from {cosima}")
    libraries = _transport_libraries(cosima, environment)
    return {
        "cosima": str(cosima),
        "cosima_sha256": sha256(cosima),
        "help_returncode": banner_result.returncode,
        "help_banner": banner,
        "help_banner_sha256": hashlib.sha256(banner.encode("utf-8")).hexdigest(),
        "shared_libraries": libraries,
        "shared_libraries_bundle_sha256": canonical_digest(libraries),
        "environment": descriptor,
    }


def resolve_cosima(value: str | None) -> Path:
    candidate = value or shutil.which("cosima") or "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"
    path = Path(candidate).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SystemExit(f"Cosima executable is missing or not executable: {path}")
    return path


def output_dir(geometry: str, mode: str) -> Path:
    return RUN_ROOT / geometry / f"{mode}_{CAMPAIGN_VERSION}"


def source_manifest_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "source_migration_manifest.json"


def expected_seeds(mode: str) -> list[int]:
    base = SEED_BASE_BY_MODE[mode]
    return [base + ordinal * SEED_STRIDE for ordinal in range(1, EXPECTED_JOBS_PER_CAMPAIGN + 1)]


def runner_command(geometry: str, mode: str, workers: int, cosima: Path) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--mode",
        mode,
        "--source-dir",
        str(GEOMETRIES[geometry]),
        "--outdir",
        str(output_dir(geometry, mode)),
        "--gamma-events",
        str(GAMMA_EVENTS),
        "--gamma-splits",
        str(GAMMA_SPLITS),
        "--non-gamma-replicas",
        str(NON_GAMMA_REPLICAS),
        "--farfield-radius-cm",
        f"{FARFIELD_RADIUS_CM:g}",
        "--seed-base",
        str(SEED_BASE_BY_MODE[mode]),
        "--seed-stride",
        str(SEED_STRIDE),
        "--workers",
        str(workers),
        "--keep-sources",
        "--cosima",
        str(cosima),
    ]
    return command


def run_preflight() -> None:
    checks = (
        ("corrected package deterministic check", [sys.executable, str(BUILDER), "--check"]),
        ("corrected package fail-closed validation", [sys.executable, str(STATIC_VALIDATOR), "--check"]),
    )
    for label, command in checks:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            raise SystemExit(f"preflight FAIL: {label} (exit {result.returncode})")
        print(f"preflight PASS: {label}")


def run_static_gate(phase: str) -> None:
    result = subprocess.run(
        [sys.executable, str(STATIC_VALIDATOR), "--check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        raise SystemExit(f"static source gate FAIL at {phase}")
    print(f"static source gate PASS: {phase}")


def _campaign_contract(global_contract: dict[str, Any], geometry: str, mode: str) -> dict[str, Any]:
    matches = [
        item
        for item in global_contract.get("campaigns", [])
        if item.get("geometry") == geometry and item.get("mode") == mode
    ]
    if len(matches) != 1:
        raise SystemExit(f"global contract has {len(matches)} entries for {geometry}/{mode}")
    return matches[0]


def verify_frozen_campaign(
    global_contract: dict[str, Any],
    geometry: str,
    mode: str,
    environment: dict[str, str],
    environment_descriptor: dict[str, Any],
    phase: str,
) -> None:
    """Close source/geometry/transport TOCTOU immediately around one run."""
    run_static_gate(f"{geometry}/{mode} {phase}")
    campaign = _campaign_contract(global_contract, geometry, mode)
    if sha256(RUNNER) != global_contract["runner_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: runner hash changed")
    for name, record in global_contract["toolchain"].items():
        if sha256(resolve_repo_path_for_harness(record["path"])) != record["sha256"]:
            raise SystemExit(f"{geometry}/{mode} {phase}: {name} hash changed")
    if sha256(SOURCE_CONTRACT) != global_contract["source_contract_manifest_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: source contract hash changed")
    source_payload = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    if source_payload["geometries"][geometry]["geometry_bundle_sha256"] != campaign[
        "source_contract_geometry_bundle_sha256"
    ]:
        raise SystemExit(f"{geometry}/{mode} {phase}: source-contract geometry bundle binding changed")
    migration_path = source_manifest_path(geometry)
    if sha256(migration_path) != campaign["source_migration_manifest_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: source migration manifest hash changed")
    migration = json.loads(migration_path.read_text(encoding="utf-8"))
    if migration.get("source_contract_manifest_sha256") != global_contract["source_contract_manifest_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: migration/source contract binding changed")
    if build_geometry_bundle(geometry, environment) != campaign["geometry_bundle"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: transitive geometry bundle changed")

    frozen_transport = global_contract["transport"]
    cosima = Path(frozen_transport["cosima"])
    if sha256(cosima) != frozen_transport["cosima_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: Cosima executable hash changed")
    libraries = _transport_libraries(cosima, environment)
    if canonical_digest(libraries) != frozen_transport["shared_libraries_bundle_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: transport shared-library bundle changed")
    if environment_descriptor["relevant_variables_sha256"] != frozen_transport["environment"]["relevant_variables_sha256"]:
        raise SystemExit(f"{geometry}/{mode} {phase}: transport environment fingerprint changed")
    setup_script = frozen_transport["environment"].get("setup_script")
    if setup_script and sha256(resolve_repo_path_for_harness(setup_script)) != frozen_transport["environment"].get(
        "setup_script_sha256"
    ):
        raise SystemExit(f"{geometry}/{mode} {phase}: MEGAlib environment setup script changed")
    current_g4 = build_g4_data_fingerprint(environment, hash_contents=False)
    frozen_g4 = frozen_transport["environment"]["g4_data_roots"]
    frozen_stat_projection = [
        {key: value for key, value in item.items() if key != "content_inventory_sha256"}
        for item in frozen_g4
    ]
    current_stat_projection = [
        {key: value for key, value in item.items() if key != "content_inventory_sha256"}
        for item in current_g4
    ]
    if current_stat_projection != frozen_stat_projection:
        raise SystemExit(f"{geometry}/{mode} {phase}: Geant4 data-root stat inventory changed")


def verify_fixed_inputs() -> None:
    required = (RUNNER, BUILDER, STATIC_VALIDATOR, DYNAMIC_VALIDATOR, SOURCE_CONTRACT)
    missing = [rel(path) for path in required if not path.is_file()]
    for geometry, source_dir in GEOMETRIES.items():
        if not source_dir.is_dir():
            missing.append(rel(source_dir))
        cards = sorted(source_dir.glob("Background_*_fullsphere20.source"))
        if len(cards) != len(FAMILIES):
            raise SystemExit(f"{geometry}: expected 8 complete source cards, found {len(cards)}")
        tags = tuple(sorted(path.name.removeprefix("Background_").removesuffix("_fullsphere20.source") for path in cards))
        if tags != tuple(sorted(FAMILIES)):
            raise SystemExit(f"{geometry}: source families differ from fixed all-eight contract: {tags}")
        if not source_manifest_path(geometry).is_file():
            missing.append(rel(source_manifest_path(geometry)))
    if missing:
        raise SystemExit("missing fixed smoke input(s): " + ", ".join(missing))


def reject_existing_outputs() -> None:
    targets = [output_dir(geometry, mode) for mode in MODES for geometry in GEOMETRIES]
    targets.extend([GLOBAL_CONTRACT, VALIDATION_REPORT, MERGE_LEDGER])
    existing = [rel(path) for path in targets if path.exists()]
    if existing:
        raise SystemExit(
            "write-once smoke target already exists; refusing overwrite/resume. "
            "Use a new campaign version and disjoint seeds: " + ", ".join(existing)
        )


def build_contract(
    workers: int,
    cosima: Path,
    transport: dict[str, Any],
    transport_environment: dict[str, str],
) -> dict[str, Any]:
    source_contract_hash = sha256(SOURCE_CONTRACT)
    source_contract_payload = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    runner_hash = sha256(RUNNER)
    geometry_bundles = {
        geometry: build_geometry_bundle(geometry, transport_environment) for geometry in GEOMETRIES
    }
    campaigns: list[dict[str, Any]] = []
    for mode in MODES:
        for geometry in GEOMETRIES:
            migration_manifest = source_manifest_path(geometry)
            campaigns.append(
                {
                    "batch_id": BATCH_ID,
                    "campaign_version": CAMPAIGN_VERSION,
                    "geometry": geometry,
                    "mode": mode,
                    "outdir": rel(output_dir(geometry, mode)),
                    "source_dir": rel(GEOMETRIES[geometry]),
                    "source_migration_manifest": rel(migration_manifest),
                    "source_migration_manifest_sha256": sha256(migration_manifest),
                    "source_contract_manifest": rel(SOURCE_CONTRACT),
                    "source_contract_manifest_sha256": source_contract_hash,
                    "geometry_bundle": geometry_bundles[geometry],
                    "source_contract_geometry_bundle_sha256": source_contract_payload["geometries"][geometry][
                        "geometry_bundle_sha256"
                    ],
                    "seed_base": SEED_BASE_BY_MODE[mode],
                    "seed_stride": SEED_STRIDE,
                    "expected_seeds": expected_seeds(mode),
                    "command": runner_command(geometry, mode, workers, cosima),
                }
            )
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__VALIDATION_REQUIRED_FOR_MERGE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "source_profile": "unit_only_total_gamma",
        "execution": {
            "workers": workers,
            "campaign_order": [f"{geometry}/{mode}" for mode in MODES for geometry in GEOMETRIES],
            "write_policy": "write-once; no force, skip, overwrite, or partial resume",
        },
        "source_scope": {
            "families": list(FAMILIES),
            "angular_bins_per_family": 20,
            "policy": "complete corrected retained original spectra; no synthetic subset and no additive mono-511",
        },
        "statistics": {
            "gamma_events": GAMMA_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
            "expected_jobs_per_campaign": EXPECTED_JOBS_PER_CAMPAIGN,
            "merge_compatibility": (
                "physics/source/geometry/transport invariants are frozen; later production may increase total "
                "statistics and may change split/replica partitioning, with explicit per-job TT and disjoint seeds"
            ),
        },
        "source_contract_manifest": rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": source_contract_hash,
        "runner": rel(RUNNER),
        "runner_sha256": runner_hash,
        "toolchain": {
            "builder": {"path": rel(BUILDER), "sha256": sha256(BUILDER)},
            "static_validator": {
                "path": rel(STATIC_VALIDATOR),
                "sha256": sha256(STATIC_VALIDATOR),
            },
            "dynamic_validator": {
                "path": rel(DYNAMIC_VALIDATOR),
                "sha256": sha256(DYNAMIC_VALIDATOR),
            },
        },
        "transport": transport,
        "geometry_bundles": geometry_bundles,
        "source_contract_geometry_bundle_sha256_by_geometry": {
            geometry: source_contract_payload["geometries"][geometry]["geometry_bundle_sha256"]
            for geometry in GEOMETRIES
        },
        "seed_registry": {
            "formula": "seed = seed_base + one_based_job_ordinal * seed_stride",
            "seed_base_by_mode": SEED_BASE_BY_MODE,
            "seed_stride": SEED_STRIDE,
            "same_mode_cross_geometry_policy": "same explicit seeds are intentional for matched A/B transport",
            "cross_mode_policy": "instant and buildup seed sets are disjoint",
            "future_batch_policy": (
                "within each geometry+mode registry, every future accepted batch must have an explicit seed set "
                "disjoint from batch0000; never infer safety from a nominal seed_base alone"
            ),
        },
        "aggregation_contract": {
            "pooling_boundary": "never pool across geometry, mode, or family",
            "prompt": "within one geometry+mode+family: rate = sum(selected) / sum(TT); then sum family rates if required",
            "activation_isotope": (
                "within one geometry+mode+family+production-volume+isotope-state: production rate = "
                "sum(RP) / sum(TT), including TT from zero-RP batches"
            ),
            "replica_policy": "derive TT and RP from each manifest/DAT; no hardcoded replica divisor",
            "TT_authority": (
                "use the positive matching DAT/log observation TT; events/(flux*pi*R^2) is its stochastic "
                "expectation, not an equality gate for a small sample"
            ),
            "acceptance": "this batch is merge-eligible only after mergeable_smoke_v1_validation.json is PASS",
        },
        "campaigns": campaigns,
    }


def write_campaign_contracts(global_contract: dict[str, Any]) -> None:
    atomic_json(GLOBAL_CONTRACT, global_contract)
    global_hash = sha256(GLOBAL_CONTRACT)
    for campaign in global_contract["campaigns"]:
        outdir = ROOT / campaign["outdir"]
        outdir.mkdir(parents=True, exist_ok=False)
        payload = {
            "schema_version": 1,
            "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED",
            "global_contract": rel(GLOBAL_CONTRACT),
            "global_contract_sha256": global_hash,
            **{key: value for key, value in campaign.items() if key != "command"},
            "command": campaign["command"],
        }
        atomic_json(outdir / "batch_contract.json", payload)


def bind_normalization(geometry: str, mode: str, global_contract: dict[str, Any]) -> None:
    outdir = output_dir(geometry, mode)
    normalization_path = outdir / "normalization.json"
    batch_contract_path = outdir / "batch_contract.json"
    if not normalization_path.is_file():
        raise SystemExit(f"runner completed without {rel(normalization_path)}")
    normalization = json.loads(normalization_path.read_text(encoding="utf-8"))
    campaign = _campaign_contract(global_contract, geometry, mode)
    normalization["mergeable_smoke_binding"] = {
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": mode,
        "global_contract": rel(GLOBAL_CONTRACT),
        "global_contract_sha256": sha256(GLOBAL_CONTRACT),
        "batch_contract": rel(batch_contract_path),
        "batch_contract_sha256": sha256(batch_contract_path),
        "source_contract_manifest": rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": sha256(SOURCE_CONTRACT),
        "source_migration_manifest": rel(source_manifest_path(geometry)),
        "source_migration_manifest_sha256": sha256(source_manifest_path(geometry)),
        "geometry_bundle_sha256": campaign["geometry_bundle"]["bundle_sha256"],
        "source_contract_geometry_bundle_sha256": campaign[
            "source_contract_geometry_bundle_sha256"
        ],
        "transport_cosima": global_contract["transport"]["cosima"],
        "transport_cosima_sha256": global_contract["transport"]["cosima_sha256"],
        "transport_shared_libraries_bundle_sha256": global_contract["transport"][
            "shared_libraries_bundle_sha256"
        ],
        "transport_environment_sha256": global_contract["transport"]["environment"][
            "relevant_variables_sha256"
        ],
        "dynamic_validator_sha256": global_contract["toolchain"]["dynamic_validator"]["sha256"],
        "merge_acceptance": "requires PASS from mergeable_smoke_v1_validation.json",
    }
    atomic_json(normalization_path, normalization)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--cosima", default=None, help="optional explicit Cosima executable")
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="run read-only static preflight and print the frozen plan; do not create outputs or launch Cosima",
    )
    args = parser.parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be positive")

    verify_fixed_inputs()
    run_preflight()
    cosima = resolve_cosima(args.cosima)
    transport_environment, environment_descriptor = resolve_transport_environment(cosima)
    transport = build_transport_fingerprint(cosima, transport_environment, environment_descriptor)
    contract = build_contract(args.workers, cosima, transport, transport_environment)
    if args.print_plan:
        print(json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    reject_existing_outputs()
    write_campaign_contracts(contract)
    for mode in MODES:
        for geometry in GEOMETRIES:
            verify_frozen_campaign(
                contract, geometry, mode, transport_environment, environment_descriptor, "pre-run"
            )
            command = runner_command(geometry, mode, args.workers, cosima)
            print(f"launching {geometry}/{mode}: {' '.join(command)}", flush=True)
            result = subprocess.run(command, cwd=ROOT, env=transport_environment, check=False)
            if result.returncode != 0:
                raise SystemExit(f"{geometry}/{mode} runner failed with exit {result.returncode}")
            verify_frozen_campaign(
                contract, geometry, mode, transport_environment, environment_descriptor, "post-run"
            )
            bind_normalization(geometry, mode, contract)

    # The validator resolves/sources the frozen MEGAlib environment itself.
    # Passing the already sourced transport environment would source it twice
    # and duplicate path entries, causing a provenance-only false failure.
    validator = subprocess.run([sys.executable, str(DYNAMIC_VALIDATOR)], cwd=ROOT, check=False)
    return validator.returncode


if __name__ == "__main__":
    raise SystemExit(main())
