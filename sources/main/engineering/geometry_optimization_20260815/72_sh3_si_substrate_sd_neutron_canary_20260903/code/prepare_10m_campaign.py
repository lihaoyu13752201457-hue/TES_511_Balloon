#!/usr/bin/env python3
"""Prepare 9.9M fresh SH3 Si-SD neutrons with the retained guarded runner."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PRODUCTION = PACKAGE / "production_10m"
GENERATED = PRODUCTION / "generated"
RUN_ROOT = PRODUCTION / "run"
CANONICAL = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
BASE_PROFILE = CANONICAL / "profiles/sg3b_plan1_extra2x_20260816_v1.json"
BASE_SOURCE = Path(
    "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/config/source_cards/s3d_o8/"
    "Background_n_fullsphere20.source"
)
SETUP = PACKAGE / "geometry/SH3_Assembly_OptV3_SiSubstrateSD_60cm.geo.setup"
VALIDATION = PACKAGE / "HITSONLY_VALIDATION.json"
PROFILE = "SH3_SI_SUBSTRATE_SD_NEUTRON_10M_20260903_V1"
CANDIDATE = "SH3_OptV3_60cm_SiSubstrateSD"
ADDITIONAL_EVENTS = 9_900_000
CHUNK_EVENTS = 100_000
EXPECTED_JOBS = 99
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"
VALIDATION_EVENTS = 10_000
VALIDATION_BYTES = 10_391_613


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_occupied(prepare) -> tuple[set[int], dict]:
    base_config = load_json(BASE_PROFILE)
    occupied, audit = prepare.occupied_seeds(base_config)
    registry_paths = sorted(
        (PACKAGE.parents[1] / "geometry_optimization_20260815").glob(
            "**/seed_registry.json"
        )
    )
    rows = 0
    for path in registry_paths:
        payload = load_json(path)
        for row in payload.get("seeds", []):
            seed = row.get("seed") if isinstance(row, dict) else None
            if isinstance(seed, int) and seed > 0:
                occupied.add(seed)
                rows += 1
    seed_re = re.compile(r"(?m)^Seed\s+(\d+)\s*$")
    local_source_paths = sorted(PACKAGE.glob("**/*.source"))
    for path in local_source_paths:
        match = seed_re.search(path.read_text(encoding="utf-8", errors="replace"))
        if match:
            occupied.add(int(match.group(1)))
    audit.update(
        {
            "additional_seed_registry_files": len(registry_paths),
            "additional_seed_registry_rows": rows,
            "local_source_cards_checked": len(local_source_paths),
            "occupied_seed_count_after_extensions": len(occupied),
        }
    )
    return occupied, audit


def main() -> int:
    if PRODUCTION.exists():
        raise FileExistsError(f"non-overwrite production gate: {PRODUCTION}")
    validation = load_json(VALIDATION)
    if validation.get("status") != "PASS__EVERYEVENTWITHHITS_PRESERVES_ACTIVE_CC":
        raise RuntimeError("hits-only paired validation is not PASS")
    if not BASE_SOURCE.is_file() or not SETUP.is_file():
        raise FileNotFoundError("base source or geometry setup missing")

    sys.path.insert(0, str(CANONICAL))
    common = load_module("sh3_sisd_common", CANONICAL / "common.py")
    prepare = load_module("sh3_sisd_prepare", CANONICAL / "prepare.py")
    occupied, seed_audit = collect_occupied(prepare)
    occupied_before = len(occupied)

    source_dir = GENERATED / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    base_text = BASE_SOURCE.read_text(encoding="utf-8")
    jobs = []
    seeds = []
    sources = []
    per_job_point_bytes = math.ceil(VALIDATION_BYTES / VALIDATION_EVENTS * CHUNK_EVENTS)
    for ordinal in range(1, EXPECTED_JOBS + 1):
        job_id = f"sh3_sisd_n10m_shard{ordinal:04d}"
        seed = prepare.derive_seed(PROFILE, job_id, occupied)
        source_path = source_dir / f"{job_id}.source"
        output_prefix = RUN_ROOT / "jobs" / job_id / "active" / job_id
        text = prepare.patch_source(
            base_text,
            setup=SETUP,
            output_prefix=output_prefix,
            job_id=job_id,
            run_name=job_id,
            mode="instant",
            seed=seed,
            events=CHUNK_EVENTS,
            config={
                "corrected_token": CORRECTED_TOKEN,
                "forbidden_legacy_token": FORBIDDEN_TOKEN,
            },
        )
        text = text.replace(
            "StoreSimulationInfo all\n",
            "StoreSimulationInfo all\nPreTriggerMode everyeventwithhits\n",
            1,
        )
        if text.count("PreTriggerMode everyeventwithhits") != 1:
            raise RuntimeError(f"pre-trigger patch failed: {job_id}")
        source_path.write_text(text, encoding="utf-8")
        row = {
            "ordinal": ordinal,
            "job_id": job_id,
            "stage": "background",
            "candidate": CANDIDATE,
            "mode": "instant",
            "family": "n",
            "shard": ordinal,
            "events": CHUNK_EVENTS,
            "seed": seed,
            "source_path": str(source_path),
            "setup_path": str(SETUP),
            "output_prefix": str(output_prefix),
            "estimated_bytes": max(256 * 1024**2, per_job_point_bytes * 3),
            "production_canary": ordinal == 1,
            "requires_isotope_dat": True,
        }
        jobs.append(row)
        seeds.append({"job_id": job_id, "seed": seed, "namespace": PROFILE})
        sources.append(
            {
                "job_id": job_id,
                "mode": "instant",
                "family": "n",
                "events": CHUNK_EVENTS,
                "seed": seed,
                "source_path": str(source_path),
                "setup_path": str(SETUP),
                "source_sha256": common.sha256(source_path),
                "pretrigger_mode": "everyeventwithhits",
            }
        )

    totals = {
        "jobs": EXPECTED_JOBS,
        "instant_histories": ADDITIONAL_EVENTS,
        "buildup_histories": 0,
    }
    statuses = {
        "seed": "PASS__SH3_SISD_FRESH_DISJOINT_SEEDS",
        "source": "PASS__SH3_SISD_CORRECTED_HITSONLY_SOURCES",
        "preflight": "PASS__SH3_SISD_10M_TRANSPORT_PREFLIGHT",
    }
    common.atomic_json(
        GENERATED / "job_plan.json",
        {
            "schema_version": 1,
            "profile_id": PROFILE,
            "candidate": CANDIDATE,
            "status": "PASS",
            "jobs": jobs,
            "totals": totals,
        },
    )
    common.atomic_json(
        GENERATED / "seed_registry.json",
        {
            "schema_version": 1,
            "profile_id": PROFILE,
            "status": statuses["seed"],
            "seeds": seeds,
            "audit": seed_audit,
        },
    )
    common.atomic_json(
        GENERATED / "source_manifest.json",
        {
            "schema_version": 1,
            "profile_id": PROFILE,
            "status": statuses["source"],
            "sources": sources,
            "source_policy": "corrected_keV_background",
            "pretrigger_mode": "everyeventwithhits",
            "paired_validation": str(VALIDATION),
        },
    )
    common.atomic_json(
        GENERATED / "preflight.json",
        {
            "schema_version": 1,
            "profile_id": PROFILE,
            "candidate": CANDIDATE,
            "status": statuses["preflight"],
            "job_plan": totals,
            "scope": "SH3 Si-SD atmospheric neutrons; exact active CC retained",
            "existing_canary_histories": 100_000,
            "additional_histories": ADDITIONAL_EVENTS,
            "combined_histories": 10_000_000,
            "paired_storage_validation": validation,
            "storage_point_estimate_bytes": per_job_point_bytes * EXPECTED_JOBS,
        },
    )
    config = {
        "schema_version": 1,
        "profile_id": PROFILE,
        "candidate": CANDIDATE,
        "display_title": "SH3 Si-substrate SD neutron 10M campaign",
        "generated_root": str(GENERATED),
        "run_root": str(RUN_ROOT),
        "geometry_setup": str(SETUP),
        "allowed_stages": ["background"],
        "expected_jobs": EXPECTED_JOBS,
        "expected_instant_histories": ADDITIONAL_EVENTS,
        "expected_buildup_histories": 0,
        "canary_job_id": jobs[0]["job_id"],
        "workers": 3,
        "max_workers": 3,
        "max_attempts": 3,
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "cosima_workdir": "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon",
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "poll_seconds": 5.0,
        "progress_interval_seconds": 5.0,
        "start_free_bytes": 55 * 1024**3,
        "dynamic_reserve_bytes": 30 * 1024**3,
        "launch_mem_available_bytes": 4 * 1024**3,
        "runtime_mem_floor_bytes": 2 * 1024**3,
        "launch_swap_free_bytes": 8 * 1024**3,
        "runtime_swap_floor_bytes": 4 * 1024**3,
        "launch_worker_reservation_bytes": (5 * 1024**3) // 2,
        "aggregate_worker_rss_ceiling_bytes": 9 * 1024**3,
        "launch_memory_full_psi_avg10_max": 10.0,
        "runtime_memory_full_psi_avg10_max": 25.0,
        "source_policy": "corrected_keV_background",
        "corrected_token": CORRECTED_TOKEN,
        "forbidden_legacy_token": FORBIDDEN_TOKEN,
        "seed_registry_pass_status": statuses["seed"],
        "source_manifest_pass_status": statuses["source"],
        "preflight_pass_status": statuses["preflight"],
    }
    common.atomic_json(PRODUCTION / "config.json", config)
    preparation = {
        "schema_version": 1,
        "status": "PREPARED__NOT_YET_TRANSPORTED",
        "profile_id": PROFILE,
        "candidate": CANDIDATE,
        "jobs": EXPECTED_JOBS,
        "events_per_job": CHUNK_EVENTS,
        "additional_histories": ADDITIONAL_EVENTS,
        "existing_canary_histories": 100_000,
        "combined_histories": 10_000_000,
        "workers": 3,
        "fresh_seeds": len(occupied) - occupied_before,
        "storage_point_estimate_bytes": per_job_point_bytes * EXPECTED_JOBS,
        "config": str(PRODUCTION / "config.json"),
    }
    common.atomic_json(PRODUCTION / "PREPARATION.json", preparation)
    print(json.dumps(preparation, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
