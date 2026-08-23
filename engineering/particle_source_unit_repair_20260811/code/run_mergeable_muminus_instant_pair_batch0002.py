#!/usr/bin/env python3
"""Run corrected-keV batch0002: paired 10k instant muminus transports.

This deliberately small, production-contributing batch runs Mass_model_511
and S3d-O8 with the same explicit seed.  Proton and buildup transport are out
of scope.  Outputs are write-once and become merge eligible only when the
companion dynamic validator writes a PASS ledger.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


ROOT = smoke.ROOT
PACKAGE = smoke.PACKAGE
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
GENERIC_RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
BUILDER = smoke.BUILDER
STATIC_VALIDATOR = smoke.STATIC_VALIDATOR
SOURCE_CONTRACT = smoke.SOURCE_CONTRACT
VALIDATOR = PACKAGE / "code/validate_mergeable_muminus_instant_pair_batch0002.py"
SMOKE_HARNESS = PACKAGE / "code/run_mergeable_two_geometry_smoke.py"
SMOKE_VALIDATOR_COMMON = PACKAGE / "code/validate_mergeable_two_geometry_smoke.py"

SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
BATCH0000_LEDGER = RUN_ROOT / "mergeable_smoke_v1_ledger.json"
BATCH0000_SHA256 = "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f"
BATCH0000_ID = "corrected_original_all8_fullsphere20_batch0000"
BATCH0000_STATUS = "PASS__BATCH0000_MERGE_ELIGIBLE"
BATCH0001_LEDGER = RUN_ROOT / "seven_family_batch0001_v1_ledger.json"
BATCH0001_SHA256 = "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4"
BATCH0001_ID = "corrected_original_seven_family_fullsphere20_batch0001"
BATCH0001_STATUS = "PASS__BATCH0001_MERGE_ELIGIBLE"

BATCH_ID = "corrected_original_muminus_instant_pair_batch0002"
CAMPAIGN_VERSION = "mergeable_muminus_instant_pair_10k_v1"
FAMILY = "muminus"
MODE = "instant"
EVENTS = 10_000
SEED = 860_915_732
FARFIELD_RADIUS_CM = 60.0
GEOMETRIES = smoke.GEOMETRIES
DISK_SAFETY_FACTOR = 2.0
DISK_RESERVE_BYTES = 20_000_000_000

GLOBAL_CONTRACT = RUN_ROOT / "muminus_instant_pair_batch0002_v1_contract.json"
VALIDATION_REPORT = RUN_ROOT / "muminus_instant_pair_batch0002_v1_validation.json"
MERGE_LEDGER = RUN_ROOT / "muminus_instant_pair_batch0002_v1_ledger.json"


def output_dir(geometry: str) -> Path:
    return RUN_ROOT / geometry / "instant_muminus_pair_batch0002_v1"


def source_manifest_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "source_migration_manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_generic_runner() -> Any:
    spec = importlib.util.spec_from_file_location("equiv2602_batch0002_runtime", GENERIC_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GENERIC_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _campaign(ledger: dict[str, Any], geometry: str) -> dict[str, Any]:
    rows = [
        row for row in ledger.get("campaigns", [])
        if row.get("geometry") == geometry and row.get("mode") == MODE
    ]
    if len(rows) != 1:
        raise SystemExit(f"prior ledger campaign ambiguity: {geometry}/{MODE}")
    return rows[0]


def _prior_seeds(*ledgers: dict[str, Any]) -> set[int]:
    seeds: set[int] = set()
    for ledger in ledgers:
        for campaign in ledger.get("campaigns", []):
            jobs = list(campaign.get("jobs", []))
            compatibility_job = campaign.get("job")
            if isinstance(compatibility_job, dict):
                jobs.append(compatibility_job)
            for job in jobs:
                if isinstance(job, dict) and "seed" in job:
                    seeds.add(int(job["seed"]))
    return seeds


def run_preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    required = (THIS_FILE, VALIDATOR, GENERIC_RUNNER, BUILDER, STATIC_VALIDATOR,
                SMOKE_HARNESS, SMOKE_VALIDATOR_COMMON,
                SOURCE_CONTRACT, BATCH0000_LEDGER, BATCH0001_LEDGER)
    missing = [smoke.rel(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing batch0002 input(s): " + ", ".join(missing))
    for path, expected in (
        (SOURCE_CONTRACT, SOURCE_CONTRACT_SHA256),
        (BATCH0000_LEDGER, BATCH0000_SHA256),
        (BATCH0001_LEDGER, BATCH0001_SHA256),
    ):
        if smoke.sha256(path) != expected:
            raise SystemExit(f"pinned hash mismatch: {smoke.rel(path)}")
    ledger0 = _load_json(BATCH0000_LEDGER)
    ledger1 = _load_json(BATCH0001_LEDGER)
    for ledger, batch_id, status in (
        (ledger0, BATCH0000_ID, BATCH0000_STATUS),
        (ledger1, BATCH0001_ID, BATCH0001_STATUS),
    ):
        if ledger.get("batch_id") != batch_id or ledger.get("status") != status:
            raise SystemExit(f"prior ledger is not merge eligible: {batch_id}")
        if ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256:
            raise SystemExit(f"prior source-contract binding mismatch: {batch_id}")
    if not any(row.get("ledger_sha256") == BATCH0000_SHA256 for row in ledger1.get("prior_batches", [])):
        raise SystemExit("batch0001 does not bind the pinned batch0000 ledger")
    if SEED in _prior_seeds(ledger0, ledger1):
        raise SystemExit(f"batch0002 seed already registered: {SEED}")
    for geometry, source_dir in GEOMETRIES.items():
        card = source_dir / f"Background_{FAMILY}_fullsphere20.source"
        text = card.read_text(encoding="utf-8", errors="replace")
        if "cosima_spectra_dp_2602units" in text:
            raise SystemExit(f"legacy spectrum reference: {smoke.rel(card)}")
        if "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/" not in text:
            raise SystemExit(f"corrected-keV spectrum root missing: {smoke.rel(card)}")
        if not source_manifest_path(geometry).is_file():
            raise SystemExit(f"source migration manifest missing: {geometry}")
    return ledger0, ledger1


def _calibration(ledger1: dict[str, Any], geometry: str) -> dict[str, Any]:
    jobs = [job for job in _campaign(ledger1, geometry)["jobs"] if job["family"] == FAMILY]
    if len(jobs) != 1:
        raise SystemExit(f"expected one batch0001 muminus calibration job: {geometry}")
    job = jobs[0]
    artifact_bytes = 0
    artifacts = []
    for key in ("sim", "isotope_dat", "log", "job_source"):
        path = ROOT / job[key]
        if not path.is_file() or path.stat().st_size <= 0:
            raise SystemExit(f"missing calibration artifact: {smoke.rel(path)}")
        artifact_bytes += path.stat().st_size
        artifacts.append({"path": smoke.rel(path), "sha256": smoke.sha256(path), "bytes": path.stat().st_size})
    rate = artifact_bytes / int(job["events"])
    return {
        "authority_batch": BATCH0001_ID,
        "events": int(job["events"]),
        "artifact_bytes": artifact_bytes,
        "observed_bytes_per_event": rate,
        "point_estimated_output_bytes": rate * EVENTS,
        "gated_estimated_output_bytes": rate * EVENTS * DISK_SAFETY_FACTOR,
        "artifacts": artifacts,
    }


def _transport_core(transport: dict[str, Any]) -> dict[str, Any]:
    environment = dict(transport["environment"])
    # PATH is recorded for diagnosis but explicitly excluded from the physics
    # digest; sourcing the same setup twice may prepend equivalent entries.
    environment.pop("observed_PATH_not_in_physics_digest", None)
    environment["g4_data_roots"] = [
        {key: value for key, value in row.items() if key != "stat_inventory_sha256"}
        for row in environment.get("g4_data_roots", [])
    ]
    return {
        key: transport[key]
        for key in ("cosima", "cosima_sha256", "help_returncode", "help_banner_sha256",
                    "shared_libraries", "shared_libraries_bundle_sha256")
    } | {"environment": environment}


def build_contract(cosima_arg: str | None) -> tuple[dict[str, Any], dict[str, str]]:
    _, ledger1 = run_preflight()
    cosima = smoke.resolve_cosima(cosima_arg)
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    source_contract = _load_json(SOURCE_CONTRACT)
    bundles = {geometry: smoke.build_geometry_bundle(geometry, environment) for geometry in GEOMETRIES}
    campaigns = []
    for geometry in GEOMETRIES:
        bundle = bundles[geometry]
        if common.source_contract_geometry_files(source_contract, geometry, environment) != bundle["files"]:
            raise SystemExit(f"source/runtime geometry bundle mismatch: {geometry}")
        migration = source_manifest_path(geometry)
        campaigns.append({
            "geometry": geometry,
            "mode": MODE,
            "family": FAMILY,
            "events": EVENTS,
            "seed": SEED,
            "outdir": smoke.rel(output_dir(geometry)),
            "source_card": smoke.rel(GEOMETRIES[geometry] / f"Background_{FAMILY}_fullsphere20.source"),
            "source_card_sha256": smoke.sha256(
                GEOMETRIES[geometry] / f"Background_{FAMILY}_fullsphere20.source"
            ),
            "source_migration_manifest": smoke.rel(migration),
            "source_migration_manifest_sha256": smoke.sha256(migration),
            "geometry_bundle": bundle,
            "calibration": _calibration(ledger1, geometry),
        })
    point = math.fsum(row["calibration"]["point_estimated_output_bytes"] for row in campaigns)
    gated = math.fsum(row["calibration"]["gated_estimated_output_bytes"] for row in campaigns)
    return ({
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_PASS_REQUIRED_FOR_MERGE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "source_profile": "unit_only_total_gamma",
        "source_contract_manifest": smoke.rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "source_scope": {"included_families": [FAMILY], "excluded_families": ["p"], "angular_bins": 20},
        "statistics": {"events_per_geometry": EVENTS, "jobs_per_geometry": 1,
                       "events_total": EVENTS * len(GEOMETRIES), "farfield_radius_cm": FARFIELD_RADIUS_CM},
        "pairing": {"policy": "same explicit seed for matched Mass_model_511/S3d-O8 A/B transport",
                    "seed": SEED, "mode": MODE, "buildup_included": False},
        "lineage": [
            {"batch_id": BATCH0000_ID, "status": BATCH0000_STATUS,
             "ledger": smoke.rel(BATCH0000_LEDGER), "ledger_sha256": BATCH0000_SHA256},
            {"batch_id": BATCH0001_ID, "status": BATCH0001_STATUS,
             "ledger": smoke.rel(BATCH0001_LEDGER), "ledger_sha256": BATCH0001_SHA256},
        ],
        "resource_gate": {"authority": "actual corrected-keV batch0001 exact campaign/family artifacts",
                          "disk_safety_factor": DISK_SAFETY_FACTOR,
                          "disk_reserve_bytes": DISK_RESERVE_BYTES,
                          "point_estimated_output_bytes": point,
                          "gated_estimated_output_bytes": gated,
                          "automatic_delete": False},
        "aggregation_contract": {"pooling_boundary": "never pool across geometry, mode, or family",
                                 "TT_authority": "positive matching isotope-DAT/log TT",
                                 "acceptance": "only the batch0002 PASS dynamic ledger permits merge"},
        "execution": {"write_once": True, "automatic_delete": False,
                      "campaign_order": [row["geometry"] for row in campaigns]},
        "toolchain": {
            "batch_runner": {"path": smoke.rel(THIS_FILE), "sha256": smoke.sha256(THIS_FILE)},
            "dynamic_validator": {"path": smoke.rel(VALIDATOR), "sha256": smoke.sha256(VALIDATOR)},
            "generic_runner": {"path": smoke.rel(GENERIC_RUNNER), "sha256": smoke.sha256(GENERIC_RUNNER)},
            "builder": {"path": smoke.rel(BUILDER), "sha256": smoke.sha256(BUILDER)},
            "static_validator": {"path": smoke.rel(STATIC_VALIDATOR), "sha256": smoke.sha256(STATIC_VALIDATOR)},
            "smoke_harness": {"path": smoke.rel(SMOKE_HARNESS), "sha256": smoke.sha256(SMOKE_HARNESS)},
            "smoke_validator_common": {
                "path": smoke.rel(SMOKE_VALIDATOR_COMMON), "sha256": smoke.sha256(SMOKE_VALIDATOR_COMMON)
            },
        },
        "transport": transport,
        "transport_core": _transport_core(transport),
        "geometry_bundles": bundles,
        "campaigns": campaigns,
    }, environment)


def disk_gate(contract: dict[str, Any]) -> dict[str, Any]:
    free = shutil.disk_usage(RUN_ROOT).free
    gated = math.ceil(contract["resource_gate"]["gated_estimated_output_bytes"])
    required = gated + DISK_RESERVE_BYTES
    return {"free_bytes": free, "gated_estimated_output_bytes": gated,
            "reserve_bytes": DISK_RESERVE_BYTES, "required_free_bytes": required,
            "status": "PASS" if free >= required else "FAIL_INSUFFICIENT_FREE_SPACE"}


def reject_existing_outputs() -> None:
    targets = [GLOBAL_CONTRACT, VALIDATION_REPORT, MERGE_LEDGER]
    targets.extend(output_dir(geometry) for geometry in GEOMETRIES)
    existing = [smoke.rel(path) for path in targets if path.exists()]
    if existing:
        raise SystemExit("write-once batch0002 target exists: " + ", ".join(existing))


def verify_frozen_campaign(
    contract: dict[str, Any], geometry: str, environment: dict[str, str], stage: str
) -> None:
    """Fail closed on every immutable input immediately around each job."""
    if not GLOBAL_CONTRACT.is_file() or _load_json(GLOBAL_CONTRACT) != contract:
        raise SystemExit(f"{geometry} {stage}: frozen global contract changed")
    if smoke.sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise SystemExit(f"{geometry} {stage}: source contract changed")
    if smoke.sha256(BATCH0000_LEDGER) != BATCH0000_SHA256:
        raise SystemExit(f"{geometry} {stage}: batch0000 ledger changed")
    if smoke.sha256(BATCH0001_LEDGER) != BATCH0001_SHA256:
        raise SystemExit(f"{geometry} {stage}: batch0001 ledger changed")
    for name, record in contract["toolchain"].items():
        path = ROOT / record["path"]
        if not path.is_file() or smoke.sha256(path) != record["sha256"]:
            raise SystemExit(f"{geometry} {stage}: toolchain changed: {name}")
    campaign = next(row for row in contract["campaigns"] if row["geometry"] == geometry)
    source_card = ROOT / campaign["source_card"]
    migration = ROOT / campaign["source_migration_manifest"]
    if not source_card.is_file() or smoke.sha256(source_card) != campaign["source_card_sha256"]:
        raise SystemExit(f"{geometry} {stage}: corrected source card changed")
    if not migration.is_file() or smoke.sha256(migration) != campaign["source_migration_manifest_sha256"]:
        raise SystemExit(f"{geometry} {stage}: source migration manifest changed")
    for artifact in campaign["calibration"]["artifacts"]:
        path = ROOT / artifact["path"]
        if (not path.is_file() or path.stat().st_size != artifact["bytes"]
                or smoke.sha256(path) != artifact["sha256"]):
            raise SystemExit(f"{geometry} {stage}: batch0001 calibration artifact changed")
    cosima = smoke.resolve_cosima(contract["transport"]["cosima"])
    current_environment, descriptor = smoke.resolve_transport_environment(cosima)
    if {
        key: current_environment.get(key)
        for key in contract["transport"]["environment"]["relevant_variables"]
    } != contract["transport"]["environment"]["relevant_variables"]:
        raise SystemExit(f"{geometry} {stage}: relevant transport environment changed")
    current_transport = smoke.build_transport_fingerprint(cosima, current_environment, descriptor)
    if _transport_core(current_transport) != contract["transport_core"]:
        raise SystemExit(f"{geometry} {stage}: transport core changed")
    bundle = smoke.build_geometry_bundle(geometry, environment)
    if bundle != contract["geometry_bundles"][geometry] or bundle != campaign["geometry_bundle"]:
        raise SystemExit(f"{geometry} {stage}: geometry bundle changed")
    source_contract = _load_json(SOURCE_CONTRACT)
    if common.source_contract_geometry_files(source_contract, geometry, environment) != bundle["files"]:
        raise SystemExit(f"{geometry} {stage}: source/runtime geometry mismatch")
    # Re-run the package's fail-closed validator immediately around transport.
    # This resolves every source-card Spectrum File reference and checks the
    # entity SHA-256 against the canonical 160-file corrected-keV inventory;
    # for this job that includes exactly its 20 muminus spectra.
    static = subprocess.run(
        [sys.executable, str(STATIC_VALIDATOR), "--check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if static.returncode != 0:
        sys.stderr.write(static.stdout)
        raise SystemExit(f"{geometry} {stage}: corrected spectrum entity/hash gate FAIL")


def _job(geometry: str, cosima: str) -> dict[str, Any]:
    outdir = output_dir(geometry)
    name = f"Background_{FAMILY}_fullsphere20_batch0002_pair"
    sim_prefix = outdir / name
    isotope_prefix = outdir / f"{name}.dat"
    return {
        "job_name": name, "particle": FAMILY, "mode": MODE, "events": EVENTS,
        "rep": 1, "part": 1, "seed": SEED,
        "source": str((GEOMETRIES[geometry] / f"Background_{FAMILY}_fullsphere20.source").resolve()),
        "temp_source": str(outdir / "job_sources" / f"{name}.source"),
        "sim_prefix": str(sim_prefix), "iso_prefix": str(isotope_prefix),
        "sim_path": str(Path(f"{sim_prefix}.inc1.id1.sim.gz")),
        "dat_path": str(Path(f"{isotope_prefix}.inc1.dat")),
        "log": str(outdir / "logs" / f"{name}.log"),
        "cosima": cosima, "skip_existing": False, "cleanup_source": False,
        "store_isotopes": True,
    }


def _run_job(runtime: Any, job: dict[str, Any], environment: dict[str, str]) -> dict[str, Any]:
    runtime.patch_source(job)
    log_path = Path(job["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"job_name={job['job_name']}\n")
        handle.write(f"mode={job['mode']} particle={job['particle']} events={job['events']} seed={job['seed']}\n")
        handle.write(f"source={job['source']}\n")
        handle.write(f"temp_source={job['temp_source']}\n")
        handle.write("-" * 72 + "\n")
        command = [job["cosima"], "-s", str(job["seed"]), job["temp_source"]]
        handle.write(f"cosima_command={' '.join(command)}\n")
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=handle,
                                stderr=subprocess.STDOUT, check=False)
        handle.write("-" * 72 + "\n")
        handle.write(f"returncode={result.returncode}\n")
        handle.write(f"wall_s={time.time() - started:.3f}\n")
    parsed = runtime.parse_log(log_path)
    sim = Path(job["sim_path"])
    dat = Path(job["dat_path"])
    problems = []
    if result.returncode:
        problems.append(f"returncode={result.returncode}")
    if parsed["has_error"]:
        problems.append("log_error")
    if parsed["generated_particles"] != EVENTS:
        problems.append(f"generated={parsed['generated_particles']} expected={EVENTS}")
    if not sim.is_file():
        problems.append("missing_sim")
    if not dat.is_file():
        problems.append("missing_dat")
    return {**job, "status": "FAIL" if problems else "PASS",
            "details": "; ".join(problems) if problems else "completed",
            "returncode": result.returncode, "sim_exists": sim.is_file(), "dat_exists": dat.is_file(),
            "sim_size_bytes": sim.stat().st_size if sim.is_file() else 0,
            "dat_size_bytes": dat.stat().st_size if dat.is_file() else 0, **parsed}


def _run(contract: dict[str, Any], environment: dict[str, str]) -> int:
    gate = disk_gate(contract)
    if gate["status"] != "PASS":
        raise SystemExit("disk gate FAIL before transport: " + json.dumps(gate, sort_keys=True))
    reject_existing_outputs()
    for label, command in (
        ("corrected package deterministic check", [sys.executable, str(BUILDER), "--check"]),
        ("corrected package static validation", [sys.executable, str(STATIC_VALIDATOR), "--check"]),
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            sys.stderr.write(result.stdout)
            raise SystemExit(f"preflight FAIL: {label}")
    smoke.atomic_json(GLOBAL_CONTRACT, contract)
    contract_hash = smoke.sha256(GLOBAL_CONTRACT)
    runtime = _load_generic_runner()
    for geometry in contract["execution"]["campaign_order"]:
        verify_frozen_campaign(contract, geometry, environment, "pre-job")
        outdir = output_dir(geometry)
        outdir.mkdir(parents=True, exist_ok=False)
        campaign = next(row for row in contract["campaigns"] if row["geometry"] == geometry)
        smoke.atomic_json(outdir / "batch_contract.json", {
            "schema_version": 1, "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_PASS_REQUIRED",
            "global_contract": smoke.rel(GLOBAL_CONTRACT), "global_contract_sha256": contract_hash,
            **campaign,
        })
        job = _job(geometry, contract["transport"]["cosima"])
        normalization = {
            "schema_version": 1, "batch_id": BATCH_ID, "campaign_version": CAMPAIGN_VERSION,
            "geometry": geometry, "mode": MODE, "selected_particles": [FAMILY],
            "excluded_particles": ["p"], "events": EVENTS, "jobs": 1,
            "farfield_radius_cm": FARFIELD_RADIUS_CM, "store_isotopes": True,
            "seed": SEED, "global_contract": smoke.rel(GLOBAL_CONTRACT),
            "global_contract_sha256": contract_hash,
            "batch_contract_sha256": smoke.sha256(outdir / "batch_contract.json"),
            "prior_merge_ledger_sha256": BATCH0001_SHA256,
            "resource_calibration": campaign["calibration"],
        }
        runtime.write_manifest(outdir, [job], normalization)
        row = _run_job(runtime, job, environment)
        runtime.write_summary(outdir, [row])
        if row["status"] != "PASS":
            raise SystemExit(f"{geometry}/{MODE}/{FAMILY} failed; batch0002 is not merge eligible")
        verify_frozen_campaign(contract, geometry, environment, "post-job")
    # Validate from the base shell.  The validator resolves/sources the pinned
    # MEGAlib environment itself; passing the already sourced transport env can
    # duplicate LD_LIBRARY_PATH entries and create a false fingerprint change.
    result = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true",
                        help="run read-only preflight and print plan; do not create outputs or launch Cosima")
    parser.add_argument("--cosima", default=None)
    args = parser.parse_args()
    contract, environment = build_contract(args.cosima)
    gate = disk_gate(contract)
    if args.print_plan:
        print(json.dumps({
            "batch_id": contract["batch_id"], "campaign_version": contract["campaign_version"],
            "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
            "source_scope": contract["source_scope"], "statistics": contract["statistics"],
            "pairing": contract["pairing"], "lineage": contract["lineage"],
            "campaigns": [
                {
                    "geometry": row["geometry"], "mode": row["mode"], "family": row["family"],
                    "events": row["events"], "seed": row["seed"], "outdir": row["outdir"],
                    "source_card_sha256": row["source_card_sha256"],
                    "source_migration_manifest_sha256": row["source_migration_manifest_sha256"],
                    "geometry_bundle_sha256": row["geometry_bundle"]["bundle_sha256"],
                    "calibration_events": row["calibration"]["events"],
                    "observed_bytes_per_event": row["calibration"]["observed_bytes_per_event"],
                    "point_estimated_output_bytes": row["calibration"]["point_estimated_output_bytes"],
                    "gated_estimated_output_bytes": row["calibration"]["gated_estimated_output_bytes"],
                }
                for row in contract["campaigns"]
            ],
            "resource_gate": contract["resource_gate"], "live_disk_gate": gate,
            "transport": {
                "cosima": contract["transport"]["cosima"],
                "cosima_sha256": contract["transport"]["cosima_sha256"],
                "shared_libraries_bundle_sha256": contract["transport"]["shared_libraries_bundle_sha256"],
                "relevant_variables_sha256": contract["transport"]["environment"]["relevant_variables_sha256"],
            },
            "toolchain": contract["toolchain"],
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if gate["status"] == "PASS" else 2
    return _run(contract, environment)


if __name__ == "__main__":
    raise SystemExit(main())
