#!/usr/bin/env python3
"""Run corrected-keV seven-family batch0001 for Mass_model_511 and S3d-O8.

This is the first production-contributing shard after the mergeable all-eight
smoke.  It deliberately excludes protons, retains the complete 20-bin source
for the other seven families, and runs both instant and buildup modes.  The
four output directories are write-once.  A completed batch is merge-eligible
only after the companion dynamic validator emits a PASS ledger.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import run_mergeable_two_geometry_smoke as smoke  # noqa: E402


PACKAGE = smoke.PACKAGE
ROOT = smoke.ROOT
RUNNER = smoke.RUNNER
BUILDER = smoke.BUILDER
STATIC_VALIDATOR = smoke.STATIC_VALIDATOR
SOURCE_CONTRACT = smoke.SOURCE_CONTRACT
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"

PRIOR_LEDGER = ROOT / "runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_ledger.json"
PRIOR_LEDGER_SHA256 = "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f"
PRIOR_BATCH_ID = "corrected_original_all8_fullsphere20_batch0000"
PRIOR_LEDGER_STATUS = "PASS__BATCH0000_MERGE_ELIGIBLE"

VALIDATOR = PACKAGE / "code/validate_mergeable_two_geometry_seven_family_batch0001.py"
SMOKE_HARNESS = PACKAGE / "code/run_mergeable_two_geometry_smoke.py"
SMOKE_VALIDATOR_COMMON = PACKAGE / "code/validate_mergeable_two_geometry_smoke.py"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
BATCH_ID = "corrected_original_seven_family_fullsphere20_batch0001"
CAMPAIGN_VERSION = "mergeable_seven_family_calibration_v1"

# Proton is intentionally absent.  Source cards remain the canonical all-eight
# directory; the runner's explicit --particles gate selects exactly this set.
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n")
ALL_SOURCE_FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
GEOMETRIES = smoke.GEOMETRIES
MODES = smoke.MODES

GAMMA_EVENTS = 100_000
GAMMA_SPLITS = 4
NON_GAMMA_REPLICAS = 1
FARFIELD_RADIUS_CM = 60.0
EXPECTED_JOBS_PER_CAMPAIGN = GAMMA_SPLITS + len(FAMILIES) - 1

# Same-mode equality across geometries is intentional matched-A/B provenance.
# Both namespaces are disjoint from batch0000 (81/82 million) and from the
# reserved full-target namespace (starts at 860,811,003).
SEED_BASE_BY_MODE = {"instant": 83_100_003, "buildup": 84_100_003}
SEED_STRIDE = 7_919
RESERVED_FULL_TARGET_SEED_START = 860_811_003

DISK_SAFETY_FACTOR = 2.0
DISK_RESERVE_BYTES = 20_000_000_000

GLOBAL_CONTRACT = RUN_ROOT / "seven_family_batch0001_v1_contract.json"
VALIDATION_REPORT = RUN_ROOT / "seven_family_batch0001_v1_validation.json"
MERGE_LEDGER = RUN_ROOT / "seven_family_batch0001_v1_ledger.json"


def output_dir(geometry: str, mode: str) -> Path:
    return RUN_ROOT / geometry / f"{mode}_seven_family_batch0001_v1"


def source_manifest_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "source_migration_manifest.json"


def expected_seeds(mode: str) -> list[int]:
    base = SEED_BASE_BY_MODE[mode]
    return [base + ordinal * SEED_STRIDE for ordinal in range(1, EXPECTED_JOBS_PER_CAMPAIGN + 1)]


def prior_seed_registry(ledger: dict[str, Any]) -> set[int]:
    return {
        int(job["seed"])
        for campaign in ledger.get("campaigns", [])
        for job in campaign.get("jobs", [])
        if isinstance(job, dict) and "seed" in job
    }


def runner_command(geometry: str, mode: str, workers: int, cosima: Path) -> list[str]:
    return [
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
        "--particles",
        ",".join(FAMILIES),
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


def _prior_campaign(ledger: dict[str, Any], geometry: str, mode: str) -> dict[str, Any]:
    matches = [
        item
        for item in ledger.get("campaigns", [])
        if item.get("geometry") == geometry and item.get("mode") == mode
    ]
    if len(matches) != 1:
        raise SystemExit(f"prior ledger has {len(matches)} entries for {geometry}/{mode}")
    return matches[0]


def _source_fluxes(source_dir: Path) -> dict[str, float]:
    fluxes: dict[str, float] = {}
    for source in sorted(source_dir.glob("Background_*_fullsphere20.source")):
        family = source.name.removeprefix("Background_").removesuffix("_fullsphere20.source")
        total = 0.0
        entries = 0
        for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
            if ".Flux" not in line:
                continue
            fields = line.split()
            total += float(fields[-1])
            entries += 1
        if entries != 20 or total <= 0.0 or not math.isfinite(total):
            raise SystemExit(f"{smoke.rel(source)}: expected 20 positive finite Flux entries")
        fluxes[family] = total
    if set(fluxes) != set(ALL_SOURCE_FAMILIES):
        raise SystemExit(f"{smoke.rel(source_dir)}: source family set mismatch {sorted(fluxes)}")
    return fluxes


def expected_events_by_family(source_dir: Path) -> dict[str, int]:
    fluxes = _source_fluxes(source_dir)
    gamma_flux = fluxes["gamma"]
    return {
        family: GAMMA_EVENTS
        if family == "gamma"
        else int(round(fluxes[family] / gamma_flux * GAMMA_EVENTS))
        for family in FAMILIES
    }


def build_corrected_smoke_estimates(prior_ledger: dict[str, Any]) -> dict[str, Any]:
    campaigns: list[dict[str, Any]] = []
    total_point = 0.0
    total_cpu = 0.0
    for mode in MODES:
        for geometry in GEOMETRIES:
            prior = _prior_campaign(prior_ledger, geometry, mode)
            summary_path = ROOT / prior["run_summary_csv"]
            if smoke.sha256(summary_path) != prior["run_summary_csv_sha256"]:
                raise SystemExit(f"corrected smoke summary hash mismatch: {smoke.rel(summary_path)}")
            with summary_path.open(newline="", encoding="utf-8") as handle:
                rows = {row["particle"]: row for row in csv.DictReader(handle)}
            events = expected_events_by_family(GEOMETRIES[geometry])
            by_family: list[dict[str, Any]] = []
            for family in FAMILIES:
                row = rows.get(family)
                if row is None or row.get("status") != "PASS":
                    raise SystemExit(f"{geometry}/{mode}: no PASS corrected smoke rate for {family}")
                sample_events = int(row["events"])
                if sample_events <= 0:
                    raise SystemExit(f"{geometry}/{mode}/{family}: nonpositive smoke sample")
                sample_bytes = int(row["sim_size_bytes"]) + int(row["dat_size_bytes"])
                sample_cpu = float(row["cpu_s"] or 0.0)
                point_bytes = events[family] * sample_bytes / sample_events
                point_cpu = events[family] * sample_cpu / sample_events
                total_point += point_bytes
                total_cpu += point_cpu
                by_family.append(
                    {
                        "family": family,
                        "events": events[family],
                        "smoke_events": sample_events,
                        "smoke_output_bytes": sample_bytes,
                        "output_bytes_per_event": sample_bytes / sample_events,
                        "cpu_s_per_event": sample_cpu / sample_events,
                        "point_estimated_output_bytes": point_bytes,
                        "gated_output_bytes": point_bytes * DISK_SAFETY_FACTOR,
                        "point_estimated_cpu_s": point_cpu,
                    }
                )
            point = math.fsum(item["point_estimated_output_bytes"] for item in by_family)
            campaigns.append(
                {
                    "geometry": geometry,
                    "mode": mode,
                    "smoke_summary_csv": smoke.rel(summary_path),
                    "smoke_summary_csv_sha256": smoke.sha256(summary_path),
                    "events": sum(events.values()),
                    "point_estimated_output_bytes": point,
                    "gated_output_bytes": point * DISK_SAFETY_FACTOR,
                    "by_family": by_family,
                }
            )
    return {
        "authority": "corrected-keV mergeable smoke batch0000; legacy _2602units estimator is forbidden",
        "method": "linear bytes/event and CPU/event scaling by geometry+mode+family",
        "small_sample_caveat": "rates are noisy, especially alpha and muon families; disk gate applies a fixed safety factor",
        "disk_safety_factor": DISK_SAFETY_FACTOR,
        "disk_reserve_bytes": DISK_RESERVE_BYTES,
        "campaigns": campaigns,
        "point_estimated_output_bytes": total_point,
        "gated_output_bytes": total_point * DISK_SAFETY_FACTOR,
        "point_estimated_cpu_s": total_cpu,
    }


def run_preflight() -> dict[str, Any]:
    required = (
        RUNNER,
        BUILDER,
        STATIC_VALIDATOR,
        VALIDATOR,
        SMOKE_HARNESS,
        SMOKE_VALIDATOR_COMMON,
        SOURCE_CONTRACT,
        PRIOR_LEDGER,
    )
    missing = [smoke.rel(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing fixed batch input(s): " + ", ".join(missing))
    if smoke.sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise SystemExit("source contract hash differs from the canonical corrected-keV contract")
    if smoke.sha256(PRIOR_LEDGER) != PRIOR_LEDGER_SHA256:
        raise SystemExit("batch0000 merge ledger hash changed")
    ledger = json.loads(PRIOR_LEDGER.read_text(encoding="utf-8"))
    if ledger.get("batch_id") != PRIOR_BATCH_ID or ledger.get("status") != PRIOR_LEDGER_STATUS:
        raise SystemExit("batch0000 lineage ledger is not merge-eligible")
    if ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256:
        raise SystemExit("batch0000 ledger is not bound to the corrected-keV source contract")

    planned_instant = set(expected_seeds("instant"))
    planned_buildup = set(expected_seeds("buildup"))
    prior = prior_seed_registry(ledger)
    if planned_instant & planned_buildup or (planned_instant | planned_buildup) & prior:
        raise SystemExit("batch0001 seed registry overlaps batch0000 or another mode")
    if max(planned_instant | planned_buildup) >= RESERVED_FULL_TARGET_SEED_START:
        raise SystemExit("batch0001 seed registry enters the reserved full-target namespace")

    for geometry, source_dir in GEOMETRIES.items():
        cards = sorted(source_dir.glob("Background_*_fullsphere20.source"))
        if len(cards) != 8:
            raise SystemExit(f"{geometry}: expected eight canonical source cards, found {len(cards)}")
        for family in FAMILIES:
            card = source_dir / f"Background_{family}_fullsphere20.source"
            text = card.read_text(encoding="utf-8", errors="replace")
            if "cosima_spectra_dp_2602units" in text:
                raise SystemExit(f"legacy spectrum reference in {smoke.rel(card)}")
            if "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/" not in text:
                raise SystemExit(f"corrected spectrum root missing in {smoke.rel(card)}")

    for label, command in (
        ("corrected package deterministic check", [sys.executable, str(BUILDER), "--check"]),
        ("corrected package fail-closed validation", [sys.executable, str(STATIC_VALIDATOR), "--check"]),
    ):
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
        print(f"preflight PASS: {label}", file=sys.stderr)
    return ledger


def _campaign_contract(global_contract: dict[str, Any], geometry: str, mode: str) -> dict[str, Any]:
    matches = [
        item
        for item in global_contract.get("campaigns", [])
        if item.get("geometry") == geometry and item.get("mode") == mode
    ]
    if len(matches) != 1:
        raise SystemExit(f"global contract has {len(matches)} entries for {geometry}/{mode}")
    return matches[0]


def build_contract(
    workers: int,
    cosima: Path,
    transport: dict[str, Any],
    transport_environment: dict[str, str],
    prior_ledger: dict[str, Any],
) -> dict[str, Any]:
    source_contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    geometry_bundles = {
        geometry: smoke.build_geometry_bundle(geometry, transport_environment) for geometry in GEOMETRIES
    }
    estimates = build_corrected_smoke_estimates(prior_ledger)
    campaigns: list[dict[str, Any]] = []
    for mode in MODES:
        for geometry in GEOMETRIES:
            migration = source_manifest_path(geometry)
            campaigns.append(
                {
                    "batch_id": BATCH_ID,
                    "campaign_version": CAMPAIGN_VERSION,
                    "geometry": geometry,
                    "mode": mode,
                    "outdir": smoke.rel(output_dir(geometry, mode)),
                    "source_dir": smoke.rel(GEOMETRIES[geometry]),
                    "source_migration_manifest": smoke.rel(migration),
                    "source_migration_manifest_sha256": smoke.sha256(migration),
                    "source_contract_manifest": smoke.rel(SOURCE_CONTRACT),
                    "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
                    "source_contract_geometry_bundle_sha256": source_contract["geometries"][geometry][
                        "geometry_bundle_sha256"
                    ],
                    "geometry_bundle": geometry_bundles[geometry],
                    "seed_base": SEED_BASE_BY_MODE[mode],
                    "seed_stride": SEED_STRIDE,
                    "expected_seeds": expected_seeds(mode),
                    "corrected_smoke_resource_estimate": next(
                        item
                        for item in estimates["campaigns"]
                        if item["geometry"] == geometry and item["mode"] == mode
                    ),
                    "command": runner_command(geometry, mode, workers, cosima),
                }
            )
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED_FOR_MERGE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "source_profile": "unit_only_total_gamma",
        "source_scope": {
            "included_families": list(FAMILIES),
            "excluded_families": ["p"],
            "angular_bins_per_family": 20,
            "policy": "canonical corrected-keV all-eight card directory with explicit seven-family runner selection",
        },
        "statistics": {
            "gamma_events": GAMMA_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
            "expected_jobs_per_campaign": EXPECTED_JOBS_PER_CAMPAIGN,
            "events_per_campaign": sum(expected_events_by_family(next(iter(GEOMETRIES.values()))).values()),
            "production_contribution": "merge with batch0000 and later batches by recorded TT, never raw-count concatenation",
        },
        "execution": {
            "workers": workers,
            "campaign_order": [f"{geometry}/{mode}" for mode in MODES for geometry in GEOMETRIES],
            "write_policy": "write-once; no force, overwrite, or partial resume",
        },
        "source_contract_manifest": smoke.rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "prior_merge_ledger": {
            "path": smoke.rel(PRIOR_LEDGER),
            "sha256": PRIOR_LEDGER_SHA256,
            "batch_id": PRIOR_BATCH_ID,
            "status": PRIOR_LEDGER_STATUS,
        },
        "runner": smoke.rel(RUNNER),
        "runner_sha256": smoke.sha256(RUNNER),
        "toolchain": {
            "batch_runner": {"path": smoke.rel(THIS_FILE), "sha256": smoke.sha256(THIS_FILE)},
            "builder": {"path": smoke.rel(BUILDER), "sha256": smoke.sha256(BUILDER)},
            "static_validator": {"path": smoke.rel(STATIC_VALIDATOR), "sha256": smoke.sha256(STATIC_VALIDATOR)},
            "dynamic_validator": {"path": smoke.rel(VALIDATOR), "sha256": smoke.sha256(VALIDATOR)},
            "smoke_harness": {"path": smoke.rel(SMOKE_HARNESS), "sha256": smoke.sha256(SMOKE_HARNESS)},
            "smoke_validator_common": {
                "path": smoke.rel(SMOKE_VALIDATOR_COMMON),
                "sha256": smoke.sha256(SMOKE_VALIDATOR_COMMON),
            },
        },
        "transport": transport,
        "geometry_bundles": geometry_bundles,
        "source_contract_geometry_bundle_sha256_by_geometry": {
            geometry: source_contract["geometries"][geometry]["geometry_bundle_sha256"]
            for geometry in GEOMETRIES
        },
        "resource_gate": estimates,
        "seed_registry": {
            "formula": "seed = seed_base + one_based_job_ordinal * seed_stride",
            "seed_base_by_mode": SEED_BASE_BY_MODE,
            "seed_stride": SEED_STRIDE,
            "expected_seeds_by_mode": {mode: expected_seeds(mode) for mode in MODES},
            "prior_registered_seeds": sorted(prior_seed_registry(prior_ledger)),
            "same_mode_cross_geometry_policy": "same explicit seeds are intentional matched-A/B transport",
            "cross_mode_policy": "instant and buildup sets are disjoint",
            "full_target_reserved_namespace": {
                "first_seed_base": RESERVED_FULL_TARGET_SEED_START,
                "policy": "batch0001 seeds must remain strictly below and disjoint from this namespace",
            },
        },
        "aggregation_contract": {
            "pooling_boundary": "never pool across geometry, mode, or family",
            "prompt": "within one geometry+mode+family: rate = sum(selected) / sum(TT)",
            "activation_isotope": (
                "within one geometry+mode+family+production-volume+isotope-state: production rate = "
                "sum(RP) / sum(TT), including registered zero-RP batch TT"
            ),
            "TT_authority": "positive matching isotope-DAT/log TT; events/(flux*pi*R^2) is expectation only",
            "acceptance": "batch0001 is merge-eligible only after seven_family_batch0001_v1_validation.json is PASS",
        },
        "campaigns": campaigns,
    }


def disk_gate(contract: dict[str, Any]) -> dict[str, Any]:
    usage = shutil.disk_usage(RUN_ROOT)
    gated = int(math.ceil(float(contract["resource_gate"]["gated_output_bytes"])))
    required = gated + DISK_RESERVE_BYTES
    result = {
        "filesystem": str(RUN_ROOT),
        "free_bytes": usage.free,
        "point_estimated_output_bytes": contract["resource_gate"]["point_estimated_output_bytes"],
        "gated_output_bytes": gated,
        "reserve_bytes": DISK_RESERVE_BYTES,
        "required_free_bytes": required,
        "status": "PASS" if usage.free >= required else "FAIL_INSUFFICIENT_FREE_SPACE",
    }
    return result


def remaining_disk_gate(contract: dict[str, Any], remaining_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    remaining = [
        item
        for item in contract["resource_gate"]["campaigns"]
        if (item["geometry"], item["mode"]) in set(remaining_pairs)
    ]
    usage = shutil.disk_usage(RUN_ROOT)
    gated = int(math.ceil(math.fsum(float(item["gated_output_bytes"]) for item in remaining)))
    required = gated + DISK_RESERVE_BYTES
    return {
        "remaining_campaigns": [f"{geometry}/{mode}" for geometry, mode in remaining_pairs],
        "free_bytes": usage.free,
        "gated_remaining_output_bytes": gated,
        "reserve_bytes": DISK_RESERVE_BYTES,
        "required_free_bytes": required,
        "status": "PASS" if usage.free >= required else "FAIL_INSUFFICIENT_FREE_SPACE",
    }


def reject_existing_outputs() -> None:
    targets = [output_dir(geometry, mode) for mode in MODES for geometry in GEOMETRIES]
    targets.extend((GLOBAL_CONTRACT, VALIDATION_REPORT, MERGE_LEDGER))
    existing = [smoke.rel(path) for path in targets if path.exists()]
    if existing:
        raise SystemExit("write-once batch0001 target already exists; refusing overwrite/resume: " + ", ".join(existing))


def write_campaign_contracts(global_contract: dict[str, Any]) -> None:
    smoke.atomic_json(GLOBAL_CONTRACT, global_contract)
    global_hash = smoke.sha256(GLOBAL_CONTRACT)
    for campaign in global_contract["campaigns"]:
        outdir = ROOT / campaign["outdir"]
        outdir.mkdir(parents=True, exist_ok=False)
        payload = {
            "schema_version": 1,
            "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED",
            "global_contract": smoke.rel(GLOBAL_CONTRACT),
            "global_contract_sha256": global_hash,
            **campaign,
        }
        smoke.atomic_json(outdir / "batch_contract.json", payload)


def bind_normalization(geometry: str, mode: str, global_contract: dict[str, Any]) -> None:
    outdir = output_dir(geometry, mode)
    path = outdir / "normalization.json"
    if not path.is_file():
        raise SystemExit(f"runner completed without {smoke.rel(path)}")
    normalization = json.loads(path.read_text(encoding="utf-8"))
    campaign = _campaign_contract(global_contract, geometry, mode)
    normalization["corrected_smoke_resource_estimate"] = campaign["corrected_smoke_resource_estimate"]
    normalization["legacy_runner_estimate_authority"] = False
    normalization["mergeable_batch_binding"] = {
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": mode,
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "batch_contract": smoke.rel(outdir / "batch_contract.json"),
        "batch_contract_sha256": smoke.sha256(outdir / "batch_contract.json"),
        "source_contract_manifest": smoke.rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "source_migration_manifest": smoke.rel(source_manifest_path(geometry)),
        "source_migration_manifest_sha256": smoke.sha256(source_manifest_path(geometry)),
        "geometry_bundle_sha256": campaign["geometry_bundle"]["bundle_sha256"],
        "source_contract_geometry_bundle_sha256": campaign["source_contract_geometry_bundle_sha256"],
        "prior_merge_ledger": smoke.rel(PRIOR_LEDGER),
        "prior_merge_ledger_sha256": PRIOR_LEDGER_SHA256,
        "transport_cosima": global_contract["transport"]["cosima"],
        "transport_cosima_sha256": global_contract["transport"]["cosima_sha256"],
        "transport_shared_libraries_bundle_sha256": global_contract["transport"]["shared_libraries_bundle_sha256"],
        "transport_environment_sha256": global_contract["transport"]["environment"]["relevant_variables_sha256"],
        "dynamic_validator_sha256": global_contract["toolchain"]["dynamic_validator"]["sha256"],
        "merge_acceptance": "requires PASS from seven_family_batch0001_v1_validation.json",
    }
    smoke.atomic_json(path, normalization)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cosima", default=None)
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="run all read-only gates and print the frozen plan; do not create outputs or launch Cosima",
    )
    args = parser.parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be positive")

    prior_ledger = run_preflight()
    cosima = smoke.resolve_cosima(args.cosima)
    transport_environment, environment_descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, transport_environment, environment_descriptor)
    contract = build_contract(args.workers, cosima, transport, transport_environment, prior_ledger)
    live_disk_gate = disk_gate(contract)
    if args.print_plan:
        print(
            json.dumps(
                {
                    "batch_id": contract["batch_id"],
                    "campaign_version": contract["campaign_version"],
                    "source_contract_manifest_sha256": contract["source_contract_manifest_sha256"],
                    "prior_merge_ledger": contract["prior_merge_ledger"],
                    "source_scope": contract["source_scope"],
                    "statistics": contract["statistics"],
                    "seed_registry": contract["seed_registry"],
                    "resource_gate": {
                        key: contract["resource_gate"][key]
                        for key in (
                            "authority",
                            "method",
                            "disk_safety_factor",
                            "disk_reserve_bytes",
                            "point_estimated_output_bytes",
                            "gated_output_bytes",
                            "point_estimated_cpu_s",
                        )
                    },
                    "campaigns": [
                        {
                            "geometry": item["geometry"],
                            "mode": item["mode"],
                            "outdir": item["outdir"],
                            "events": item["corrected_smoke_resource_estimate"]["events"],
                            "jobs": EXPECTED_JOBS_PER_CAMPAIGN,
                            "point_estimated_output_bytes": item["corrected_smoke_resource_estimate"][
                                "point_estimated_output_bytes"
                            ],
                            "seeds": item["expected_seeds"],
                        }
                        for item in contract["campaigns"]
                    ],
                    "live_disk_gate": live_disk_gate,
                    "transport": {
                        "cosima": transport["cosima"],
                        "cosima_sha256": transport["cosima_sha256"],
                        "shared_libraries_bundle_sha256": transport["shared_libraries_bundle_sha256"],
                        "environment_sha256": transport["environment"]["relevant_variables_sha256"],
                    },
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0 if live_disk_gate["status"] == "PASS" else 2
    if live_disk_gate["status"] != "PASS":
        raise SystemExit("disk gate FAIL before transport: " + json.dumps(live_disk_gate, sort_keys=True))

    reject_existing_outputs()
    write_campaign_contracts(contract)
    ordered_pairs = [(geometry, mode) for mode in MODES for geometry in GEOMETRIES]
    for index, (geometry, mode) in enumerate(ordered_pairs):
        live_remaining_gate = remaining_disk_gate(contract, ordered_pairs[index:])
        if live_remaining_gate["status"] != "PASS":
            raise SystemExit(
                f"disk gate FAIL before {geometry}/{mode}: "
                + json.dumps(live_remaining_gate, sort_keys=True)
            )
        smoke.verify_frozen_campaign(
            contract, geometry, mode, transport_environment, environment_descriptor, "pre-run"
        )
        command = runner_command(geometry, mode, args.workers, cosima)
        print(f"launching {geometry}/{mode}: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=transport_environment, check=False)
        if result.returncode != 0:
            raise SystemExit(f"{geometry}/{mode} runner failed with exit {result.returncode}")
        smoke.verify_frozen_campaign(
            contract, geometry, mode, transport_environment, environment_descriptor, "post-run"
        )
        bind_normalization(geometry, mode, contract)

    validator = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=False)
    return validator.returncode


if __name__ == "__main__":
    raise SystemExit(main())
