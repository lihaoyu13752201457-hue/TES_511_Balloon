#!/usr/bin/env python3
"""Prepare non-overwriting remaining-only SG3 minimal/init-only production."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
OLD_PACKAGE = PACKAGE.parent / "67_m05new_zero_prompt_statistics_20260823"
EBB2 = Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
CANONICAL = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
BASE_PROFILE = CANONICAL / "profiles/sg3b_plan1_extra2x_20260816_v1.json"
BASE_SOURCE_ROOT = (
    EBB2 / "engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8"
)
ORIGINAL_PREP_SCRIPT = OLD_PACKAGE / "code/prepare_targeted_supplement.py"
SETUP = PACKAGE / "geometry/DEMO2_DR_v3p5_SG3B_MINIMAL.geo.setup"
OLD_DATA = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/m05new_zero_prompt_supplement_20260823_v1"
)
NEW_DATA = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/"
    "m05new_zero_prompt_minimal_supplement_20260823_v1"
)
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"

FAMILY_ORDER = ("alpha", "p", "eplus", "n")
ORIGINAL_TARGETS = {
    "alpha": 33_092,
    "p": 355_380,
    "eplus": 333_933,
    "n": 1_333_471,
}
CHUNK_EVENTS = {"alpha": 3_972, "p": 16_966, "eplus": 40_124, "n": 155_328}
CONFIG_WORKERS = {"alpha": 2, "p": 2, "eplus": 1, "n": 1}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(partial, path)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def old_pass_events(family: str) -> int:
    receipts = OLD_DATA / family / "run/receipts"
    total = 0
    for path in sorted(receipts.glob("*.json")):
        row = load_json(path)
        if row.get("status") == "PASS" and row.get("family") == family:
            total += int(row["events"])
    return total


def split_events(total: int, chunk: int) -> list[int]:
    full, remainder = divmod(total, chunk)
    return [chunk] * full + ([remainder] if remainder else [])


def main() -> int:
    bundles_root = PACKAGE / "production_bundles"
    prep_path = PACKAGE / "MINIMAL_PRODUCTION_PREPARATION.json"
    if bundles_root.exists() or prep_path.exists() or NEW_DATA.exists():
        raise FileExistsError("non-overwrite minimal production gate")
    if not SETUP.is_file():
        raise FileNotFoundError(SETUP)

    sys.path.insert(0, str(CANONICAL))
    canonical_prepare = load_module("m05minimal_canonical_prepare", CANONICAL / "prepare.py")
    common = load_module("m05minimal_canonical_common", CANONICAL / "common.py")
    original = load_module("m05minimal_original_prepare", ORIGINAL_PREP_SCRIPT)
    prior_roots = original.SH3_PRIOR_ROOTS
    # Reuse all small registered authorities from the original preparer, but
    # replace its unrestricted recursive walk through large campaign trees by
    # the two known shallow registry layouts.
    original.SH3_PRIOR_ROOTS = ()
    occupied = original.collect_occupied_seeds(canonical_prepare)
    for root in prior_roots:
        if not root.is_dir():
            continue
        registry_paths = list(root.glob("*/generated/seed_registry.json"))
        registry_paths += list(root.glob("*/rounds/*/*/generated/seed_registry.json"))
        for path in sorted(set(registry_paths)):
            for row in load_json(path).get("seeds", []):
                if isinstance(row, dict) and isinstance(row.get("seed"), int):
                    occupied.add(int(row["seed"]))
    for path in sorted((OLD_PACKAGE / "bundles").rglob("seed_registry.json")):
        for row in load_json(path).get("seeds", []):
            occupied.add(int(row["seed"]))
    occupied_before = len(occupied)
    calibrations = original.family_bytes_per_event(original.SG3_SUMMARY)

    completed = {family: old_pass_events(family) for family in FAMILY_ORDER}
    remaining = {
        family: ORIGINAL_TARGETS[family] - completed[family] for family in FAMILY_ORDER
    }
    if any(value <= 0 for value in remaining.values()):
        raise RuntimeError(f"unexpected remaining targets: {remaining}")

    bundles = []
    for family in FAMILY_ORDER:
        target = remaining[family]
        chunks = split_events(target, CHUNK_EVENTS[family])
        profile = f"M05NEW_ZERO_PROMPT_SG3_MINIMAL_{family.upper()}_20260823_V1"
        bundle = bundles_root / family
        generated = bundle / "generated"
        source_dir = generated / "sources"
        source_dir.mkdir(parents=True)
        run_root = NEW_DATA / family / "run"
        base = BASE_SOURCE_ROOT / f"Background_{family}_fullsphere20.source"
        jobs = []
        seeds = []
        sources = []
        for ordinal, events in enumerate(chunks, 1):
            job_id = f"m05zm_sg3_instant_{family}_shard{ordinal:04d}"
            seed = canonical_prepare.derive_seed(profile, job_id, occupied)
            source_path = source_dir / f"{job_id}.source"
            output_prefix = run_root / "jobs" / job_id / "active" / job_id
            text = canonical_prepare.patch_source(
                base.read_text(encoding="utf-8"),
                setup=SETUP,
                output_prefix=output_prefix,
                job_id=job_id,
                run_name=job_id,
                mode="instant",
                seed=seed,
                events=events,
                config={"corrected_token": CORRECTED_TOKEN, "forbidden_legacy_token": FORBIDDEN_TOKEN},
            )
            if text.count("StoreSimulationInfo all") != 1:
                raise RuntimeError(f"unexpected storage directive: {job_id}")
            text = text.replace("StoreSimulationInfo all", "StoreSimulationInfo init-only", 1)
            source_path.write_text(text, encoding="utf-8")
            estimated = max(64 * 1024**2, int(math.ceil(events * calibrations[family] * 0.02)))
            jobs.append(
                {
                    "ordinal": ordinal,
                    "job_id": job_id,
                    "stage": "background",
                    "candidate": "SG3B_MINIMAL_SD",
                    "mode": "instant",
                    "family": family,
                    "shard": ordinal,
                    "events": events,
                    "seed": seed,
                    "source_path": str(source_path),
                    "setup_path": str(SETUP),
                    "output_prefix": str(output_prefix),
                    "estimated_bytes": estimated,
                    "production_canary": ordinal == 1,
                    "requires_isotope_dat": True,
                }
            )
            seeds.append({"job_id": job_id, "seed": seed, "namespace": profile})
            sources.append(
                {
                    "job_id": job_id,
                    "mode": "instant",
                    "family": family,
                    "events": events,
                    "seed": seed,
                    "source_path": str(source_path),
                    "setup_path": str(SETUP),
                    "store_simulation_info": "init-only",
                    "source_sha256": common.sha256(source_path),
                }
            )
        totals = {"jobs": len(jobs), "instant_histories": target, "buildup_histories": 0}
        statuses = {
            "seed": "PASS__M05ZERO_MINIMAL_FRESH_DISJOINT_SEEDS",
            "source": "PASS__M05ZERO_MINIMAL_CORRECTED_PROMPT_SOURCES",
            "preflight": "PASS__M05ZERO_MINIMAL_PROMPT_TRANSPORT_PREFLIGHT",
        }
        atomic_json(generated / "job_plan.json", {"schema_version": 1, "profile_id": profile, "candidate": "SG3B_MINIMAL_SD", "status": "PASS", "jobs": jobs, "totals": totals})
        atomic_json(generated / "seed_registry.json", {"schema_version": 1, "profile_id": profile, "status": statuses["seed"], "seeds": seeds})
        atomic_json(generated / "source_manifest.json", {"schema_version": 1, "profile_id": profile, "status": statuses["source"], "sources": sources, "source_policy": "corrected_keV_background__init_only"})
        atomic_json(generated / "preflight.json", {"schema_version": 1, "profile_id": profile, "candidate": "SG3B_MINIMAL_SD", "status": statuses["preflight"], "job_plan": totals, "scope": "prompt-only; minimal SD; init-only; gamma and delayed excluded"})
        config = {
            "schema_version": 1,
            "profile_id": profile,
            "candidate": "SG3B_MINIMAL_SD",
            "display_title": f"M05NEW zero-prompt minimal supplement sg3/{family}",
            "generated_root": str(generated),
            "run_root": str(run_root),
            "geometry_setup": str(SETUP),
            "allowed_stages": ["background"],
            "expected_jobs": len(jobs),
            "expected_instant_histories": target,
            "expected_buildup_histories": 0,
            "canary_job_id": jobs[0]["job_id"],
            "workers": CONFIG_WORKERS[family],
            "max_workers": 2,
            "max_attempts": 3,
            "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
            "cosima_workdir": str(EBB2),
            "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
            "poll_seconds": 5.0,
            "progress_interval_seconds": 5.0,
            "start_free_bytes": 50 * 1024**3,
            "dynamic_reserve_bytes": 30 * 1024**3,
            "launch_mem_available_bytes": 2 * 1024**3,
            "runtime_mem_floor_bytes": 1200 * 1024**2,
            "launch_swap_free_bytes": 4 * 1024**3,
            "runtime_swap_floor_bytes": 2 * 1024**3,
            "launch_worker_reservation_bytes": (2 * 1024**3 if family == "n" else 1300 * 1024**2),
            "aggregate_worker_rss_ceiling_bytes": 0,
            "launch_memory_full_psi_avg10_max": 10.0,
            "runtime_memory_full_psi_avg10_max": 25.0,
            "source_policy": "corrected_keV_background__init_only",
            "corrected_token": CORRECTED_TOKEN,
            "forbidden_legacy_token": FORBIDDEN_TOKEN,
            "seed_registry_pass_status": statuses["seed"],
            "source_manifest_pass_status": statuses["source"],
            "preflight_pass_status": statuses["preflight"],
        }
        atomic_json(bundle / "config.json", config)
        bundles.append({"family": family, "target_events": target, "prior_pass_events": completed[family], "jobs": len(jobs), "config": str(bundle / "config.json"), "run_root": str(run_root)})

    payload = {
        "schema_version": 1,
        "status": "PREPARED__MINIMAL_INIT_ONLY_NOT_YET_TRANSPORTED",
        "scope": "SG3 remaining-only zero-count prompt supplement",
        "family_order": list(FAMILY_ORDER),
        "original_targets": ORIGINAL_TARGETS,
        "prior_pass_events": completed,
        "remaining_targets": remaining,
        "total_remaining_events": sum(remaining.values()),
        "fresh_seeds": len(occupied) - occupied_before,
        "storage_policy": "StoreSimulationInfo init-only; HTsim bridge validated",
        "pooling_policy": "selected-count/equivalent-exposure strata only; no raw SIM/ledger merge",
        "bundles": bundles,
    }
    atomic_json(prep_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
