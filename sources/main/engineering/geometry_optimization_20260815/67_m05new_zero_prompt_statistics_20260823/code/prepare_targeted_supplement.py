#!/usr/bin/env python3
"""Prepare non-overwriting SG3/SH3 prompt-only statistics bundles.

The generated bundles deliberately reuse the corrected-keV source-card patcher
and guarded Cosima runner from the retained SG3/SH3 campaigns.  Only the seven
prompt families with zero W2-final survivors are included; gamma and delayed
transport are excluded by construction.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
EBB2 = Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
CANONICAL = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
BASE_PROFILE = CANONICAL / "profiles/sg3b_plan1_extra2x_20260816_v1.json"
BASE_SOURCE_ROOT = EBB2 / "engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8"
SG3_SUMMARY = EBB2 / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/outputs/01_event_catalog/summary.json"
SH3_SUMMARY = EBB2 / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json"
SG3_GAMMA_RECEIPTS = EBB2 / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/02_gamma_transport/receipts"
SG3_GAMMA_SOURCES = EBB2 / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/config/gamma_shards"
SG3_SETUP = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
SH3_SETUP = Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup")
DATA_ROOTS = {
    "sg3": Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_zero_prompt_supplement_20260823_v1"),
    "sh3": Path("/mnt/data/TES_Balloon_511_data/SH3/m05new_zero_prompt_supplement_20260823_v1"),
}
SH3_PRIOR_ROOTS = (
    Path("/mnt/data/TES_Balloon_511_data/SH3"),
    Path("/mnt/data/TES_511_Balloon_511_data/SH3"),
)
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"

FAMILY_ORDER = ("muplus", "muminus", "eminus", "alpha", "p", "eplus", "n")
TARGET_ADDITIONS = {
    "sg3": {
        "alpha": 33_092,
        "eminus": 379_716,
        "eplus": 333_933,
        "muminus": 6_164,
        "muplus": 15_399,
        "n": 1_333_471,
        "p": 355_380,
    },
    "sh3": {
        "alpha": 184_962,
        "eminus": 2_407_699,
        "eplus": 1_875_981,
        "muminus": 48_758,
        "muplus": 86_232,
        "n": 7_420_891,
        "p": 1_933_721,
    },
}

# Retained extra2x shard sizes: short enough for recovery, large enough to
# avoid thousands of tiny Cosima launches.
CHUNK_EVENTS = {
    "alpha": 3_972,
    "eminus": 196_894,
    "eplus": 40_124,
    "muminus": 6_962,
    "muplus": 2_648,
    "n": 155_328,
    "p": 16_966,
}

# Four total Cosima processes for moderate-memory families.  Neutron and
# positron phases are held at one worker per geometry after prior receipts
# showed about 1.77 GiB and 1.22 GiB peak RSS per process, respectively.
WORKERS_PER_GEOMETRY = {
    "muplus": 2,
    "muminus": 2,
    "eminus": 2,
    "alpha": 2,
    "p": 2,
    "eplus": 1,
    "n": 1,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, path)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def collect_occupied_seeds(prepare) -> set[int]:
    base_config = load_json(BASE_PROFILE)
    occupied, _ = prepare.occupied_seeds(base_config)

    # Current compact summaries cover the accepted SG3 and SH3 jobs.
    for summary in (SG3_SUMMARY, SH3_SUMMARY):
        for row in load_json(summary).get("jobs", []):
            seed = row.get("seed")
            if isinstance(seed, int) and seed > 0:
                occupied.add(seed)

    # Include every SG3 gamma receipt/source, including non-paper and failed
    # attempts, so the supplement cannot reuse their registered identities.
    for path in sorted(SG3_GAMMA_RECEIPTS.glob("*.json")):
        row = load_json(path)
        for key in ("source_seed", "sim_header_seed", "seed"):
            seed = row.get(key)
            if isinstance(seed, int) and seed > 0:
                occupied.add(seed)
    seed_re = re.compile(r"(?m)^Seed\s+(\d+)\s*$")
    for path in sorted(SG3_GAMMA_SOURCES.glob("*.source")):
        match = seed_re.search(path.read_text(encoding="utf-8", errors="replace"))
        if match:
            occupied.add(int(match.group(1)))

    # Round005 is intentionally absent from the final SH3 catalog, but its
    # canary/full seeds still count as occupied.  Small registry JSONs suffice;
    # no SIM content or digest is read.
    for root in SH3_PRIOR_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("seed_registry.json"):
            try:
                rows = load_json(path).get("seeds", [])
            except (OSError, json.JSONDecodeError):
                continue
            for row in rows:
                seed = row.get("seed") if isinstance(row, dict) else None
                if isinstance(seed, int) and seed > 0:
                    occupied.add(seed)
    return occupied


def family_bytes_per_event(summary: Path) -> dict[str, float]:
    payload = load_json(summary)
    result: dict[str, float] = {}
    for family in FAMILY_ORDER:
        rows = [
            row for row in payload["jobs"]
            if row.get("stream") == "prompt" and row.get("family") == family
        ]
        events = sum(int(row["events"]) for row in rows)
        size = sum(int(row["sim_bytes"]) for row in rows)
        if events <= 0 or size <= 0:
            raise RuntimeError(f"missing retained bytes/event calibration: {summary}: {family}")
        result[family] = size / events
    return result


def split_events(total: int, chunk: int) -> list[int]:
    if total <= 0 or chunk <= 0:
        raise ValueError("event totals and chunks must be positive")
    full, remainder = divmod(total, chunk)
    result = [chunk] * full
    if remainder:
        result.append(remainder)
    return result


def build_family_bundle(
    *,
    geometry: str,
    family: str,
    setup: Path,
    candidate: str,
    occupied: set[int],
    prepare,
    common,
    bytes_per_event: float,
) -> dict[str, Any]:
    target = TARGET_ADDITIONS[geometry][family]
    chunks = split_events(target, CHUNK_EVENTS[family])
    profile = f"M05NEW_ZERO_PROMPT_{geometry.upper()}_{family.upper()}_20260823_V1"
    bundle = PACKAGE / "bundles" / geometry / family
    generated = bundle / "generated"
    run_root = DATA_ROOTS[geometry] / family / "run"
    if bundle.exists():
        raise FileExistsError(f"non-overwrite local bundle gate: {bundle}")
    if run_root.exists():
        raise FileExistsError(f"non-overwrite external run gate: {run_root}")
    if not setup.is_file():
        raise FileNotFoundError(setup)
    base = BASE_SOURCE_ROOT / f"Background_{family}_fullsphere20.source"
    if not base.is_file():
        raise FileNotFoundError(base)

    source_dir = generated / "sources"
    source_dir.mkdir(parents=True)
    jobs: list[dict[str, Any]] = []
    seeds: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    point_estimate_bytes = 0.0
    for ordinal, events in enumerate(chunks, 1):
        job_id = f"m05z_{geometry}_instant_{family}_shard{ordinal:04d}"
        seed = prepare.derive_seed(profile, job_id, occupied)
        source_path = source_dir / f"{job_id}.source"
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        text = prepare.patch_source(
            base.read_text(encoding="utf-8"),
            setup=setup,
            output_prefix=output_prefix,
            job_id=job_id,
            run_name=job_id,
            mode="instant",
            seed=seed,
            events=events,
            config={"corrected_token": CORRECTED_TOKEN, "forbidden_legacy_token": FORBIDDEN_TOKEN},
        )
        source_path.write_text(text, encoding="utf-8")
        expected = events * bytes_per_event
        point_estimate_bytes += expected
        job = {
            "ordinal": ordinal,
            "job_id": job_id,
            "stage": "background",
            "candidate": candidate,
            "mode": "instant",
            "family": family,
            "shard": ordinal,
            "events": events,
            "seed": seed,
            "source_path": str(source_path),
            "setup_path": str(setup),
            "output_prefix": str(output_prefix),
            "estimated_bytes": max(64 * 1024**2, int(math.ceil(expected * 1.25))),
            "production_canary": ordinal == 1,
            "requires_isotope_dat": True,
        }
        jobs.append(job)
        seeds.append({"job_id": job_id, "seed": seed, "namespace": profile})
        sources.append({
            "job_id": job_id,
            "mode": "instant",
            "family": family,
            "events": events,
            "seed": seed,
            "source_path": str(source_path),
            "setup_path": str(setup),
            "source_sha256": common.sha256(source_path),
        })

    totals = {"jobs": len(jobs), "instant_histories": target, "buildup_histories": 0}
    statuses = {
        "seed": "PASS__M05ZERO_FRESH_DISJOINT_SEEDS",
        "source": "PASS__M05ZERO_CORRECTED_PROMPT_SOURCES",
        "preflight": "PASS__M05ZERO_PROMPT_TRANSPORT_PREFLIGHT",
    }
    atomic_json(generated / "job_plan.json", {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": candidate,
        "status": "PASS",
        "jobs": jobs,
        "totals": totals,
    })
    atomic_json(generated / "seed_registry.json", {
        "schema_version": 1,
        "profile_id": profile,
        "status": statuses["seed"],
        "seeds": seeds,
    })
    atomic_json(generated / "source_manifest.json", {
        "schema_version": 1,
        "profile_id": profile,
        "status": statuses["source"],
        "sources": sources,
        "source_policy": "corrected_keV_background",
    })
    atomic_json(generated / "preflight.json", {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": candidate,
        "status": statuses["preflight"],
        "job_plan": totals,
        "scope": "prompt-only; gamma and delayed excluded",
    })
    config = {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": candidate,
        "display_title": f"M05NEW zero-prompt supplement {geometry}/{family}",
        "generated_root": str(generated),
        "run_root": str(run_root),
        "geometry_setup": str(setup),
        "allowed_stages": ["background"],
        "expected_jobs": len(jobs),
        "expected_instant_histories": target,
        "expected_buildup_histories": 0,
        "canary_job_id": jobs[0]["job_id"],
        "workers": WORKERS_PER_GEOMETRY[family],
        "max_workers": 2,
        "max_attempts": 3,
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "cosima_workdir": str(EBB2),
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "poll_seconds": 5.0,
        "progress_interval_seconds": 5.0,
        "start_free_bytes": 150 * 1024**3,
        "dynamic_reserve_bytes": 120 * 1024**3,
        "launch_mem_available_bytes": 2 * 1024**3,
        "runtime_mem_floor_bytes": 1200 * 1024**2,
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 2 * 1024**3,
        "launch_worker_reservation_bytes": (2 * 1024**3 if family == "n" else 1400 * 1024**2),
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 10.0,
        "runtime_memory_full_psi_avg10_max": 25.0,
        "source_policy": "corrected_keV_background",
        "corrected_token": CORRECTED_TOKEN,
        "forbidden_legacy_token": FORBIDDEN_TOKEN,
        "seed_registry_pass_status": statuses["seed"],
        "source_manifest_pass_status": statuses["source"],
        "preflight_pass_status": statuses["preflight"],
    }
    atomic_json(bundle / "config.json", config)
    return {
        "geometry": geometry,
        "family": family,
        "target_events": target,
        "jobs": len(jobs),
        "workers": WORKERS_PER_GEOMETRY[family],
        "point_estimate_bytes": int(round(point_estimate_bytes)),
        "config": str(bundle / "config.json"),
        "run_root": str(run_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="write the 14 non-overwriting bundles")
    args = parser.parse_args()
    if not args.prepare:
        raise SystemExit("use --prepare to write bundles")
    if (PACKAGE / "bundles").exists():
        raise FileExistsError(f"non-overwrite preparation gate: {PACKAGE / 'bundles'}")
    for root in DATA_ROOTS.values():
        if root.exists():
            raise FileExistsError(f"non-overwrite data-root gate: {root}")

    sys.path.insert(0, str(CANONICAL))
    prepare = load_module("m05zero_canonical_prepare", CANONICAL / "prepare.py")
    common = load_module("m05zero_canonical_common", CANONICAL / "common.py")
    occupied = collect_occupied_seeds(prepare)
    initial_occupied = len(occupied)
    calibrations = {
        "sg3": family_bytes_per_event(SG3_SUMMARY),
        "sh3": family_bytes_per_event(SH3_SUMMARY),
    }
    geometry_contract = {
        "sg3": (SG3_SETUP, "SG3B"),
        "sh3": (SH3_SETUP, "SH3_OptV3_60cm"),
    }
    bundles = []
    for family in FAMILY_ORDER:
        for geometry in ("sg3", "sh3"):
            setup, candidate = geometry_contract[geometry]
            bundles.append(build_family_bundle(
                geometry=geometry,
                family=family,
                setup=setup,
                candidate=candidate,
                occupied=occupied,
                prepare=prepare,
                common=common,
                bytes_per_event=calibrations[geometry][family],
            ))
    payload = {
        "schema_version": 1,
        "status": "PREPARED__NOT_YET_TRANSPORTED",
        "scope": "SG3/SH3 seven zero-count prompt families; gamma and delayed excluded",
        "family_order": list(FAMILY_ORDER),
        "targets": TARGET_ADDITIONS,
        "total_target_events": sum(sum(rows.values()) for rows in TARGET_ADDITIONS.values()),
        "point_estimate_bytes": sum(row["point_estimate_bytes"] for row in bundles),
        "occupied_seeds_before": initial_occupied,
        "fresh_seeds": len(occupied) - initial_occupied,
        "bundles": bundles,
    }
    atomic_json(PACKAGE / "PREPARATION.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
