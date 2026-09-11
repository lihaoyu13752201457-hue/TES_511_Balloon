#!/usr/bin/env python3
"""Shard the prepared SG3B M05 delayed sources for guarded 5-worker transport."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROFILE_ID = "SG3B_M05_DAY15_DELAYED_1M_SHARDED_20260817_V2"
CANDIDATE = "SG3B"
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
BASE = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_v1")
TARGET = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_sharded_v2")
GENERATED = TARGET / "generated"
RUN_ROOT = TARGET / "run"
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")
PROGRESS = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/progress.py")
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"
SHARDS = {
    "p": (50_000, 250_000, 250_000, 250_000, 200_000),
    "n": (250_000, 250_000, 250_000, 250_000),
    "alpha": (250_000, 250_000, 250_000, 250_000),
    "gamma": (250_000, 250_000, 250_000, 250_000),
    "eminus": (250_000, 250_000, 250_000, 250_000),
    "eplus": (250_000, 250_000, 250_000, 250_000),
    "muminus": (250_000, 250_000, 250_000, 250_000),
    "muplus": (250_000, 250_000, 250_000, 250_000),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def recursive_seeds(value: Any) -> Iterable[int]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "seed" and isinstance(item, int) and item > 0:
                yield item
            yield from recursive_seeds(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_seeds(item)


def seed_authorities() -> tuple[set[int], list[dict[str, Any]]]:
    occupied: set[int] = set()
    records: list[dict[str, Any]] = []
    paths: set[Path] = set()
    for path in Path("/mnt/data/TES_Balloon_511_data/SG3").glob("**/receipts/*.json"):
        paths.add(path)
    for root in (Path("/home/ubuntu/TES_511_Balloon"), Path("/home/ubuntu/.codex/worktrees")):
        for pattern in ("**/*seed_registry*.json", "**/*seed_registry*.csv"):
            paths.update(root.glob(pattern))
    for path in sorted(paths):
        try:
            before = len(occupied)
            if path.suffix == ".json":
                value = json.loads(path.read_text(encoding="utf-8"))
                occupied.update(recursive_seeds(value))
            else:
                with path.open(newline="", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        raw = row.get("seed")
                        if raw and int(raw) > 0:
                            occupied.add(int(raw))
            records.append({
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "new_unique_seeds": len(occupied) - before,
            })
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return occupied, records


def derive_seed(identity: str, occupied: set[int]) -> int:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{PROFILE_ID}|{identity}|{counter}".encode()).digest()
        seed = 1 + int.from_bytes(digest[:8], "big") % 2_147_483_646
        if seed not in occupied:
            occupied.add(seed)
            return seed
        counter += 1


def patch_card(base_text: str, *, seed: int, events: int, output_prefix: Path, job_id: str) -> str:
    lines = base_text.splitlines()
    counts = {"seed": 0, "triggers": 0, "filename": 0}
    output: list[str] = []
    for line in lines:
        if line.startswith("Seed "):
            output.append(f"Seed {seed}")
            counts["seed"] += 1
        elif line.startswith("DecayRun.Triggers "):
            output.append(f"DecayRun.Triggers {events}")
            counts["triggers"] += 1
        elif line.startswith("DecayRun.FileName "):
            output.append(f"DecayRun.FileName {output_prefix}")
            counts["filename"] += 1
        else:
            output.append(line)
    if counts != {"seed": 1, "triggers": 1, "filename": 1}:
        raise RuntimeError(f"base card binding count drift for {job_id}: {counts}")
    output.insert(2, f"# Transport shard {job_id}; source mixture is unchanged from the audited family-level M05 draw.")
    return "\n".join(output) + "\n"


def prepare() -> Path:
    if TARGET.exists():
        raise RuntimeError(f"write-once target already exists: {TARGET}")
    manifest_path = BASE / "generated/activation/manifest.json"
    base_manifest = load_json(manifest_path)
    if base_manifest.get("status") != "PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY":
        raise RuntimeError("base SG3B activation manifest is not PASS")
    if set(base_manifest.get("planned_positive_families", [])) != set(FAMILIES):
        raise RuntimeError("base positive-family closure differs from eight families")
    if any(sum(SHARDS[family]) != 1_000_000 for family in FAMILIES):
        raise RuntimeError("per-family shard sum differs from 1,000,000")

    occupied, authorities = seed_authorities()
    occupied_before = set(occupied)
    sources = GENERATED / "sources"
    sources.mkdir(parents=True, exist_ok=False)
    jobs: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    ordinal = 0
    for family in FAMILIES:
        base_source = BASE / "generated/sources" / f"sg3b_delayed_{family}.source"
        if not base_source.is_file():
            raise RuntimeError(f"missing base delayed source: {base_source}")
        base_text = base_source.read_text(encoding="utf-8")
        if FORBIDDEN_TOKEN in base_text or base_text.count(f"Geometry {GEOMETRY}") != 1:
            raise RuntimeError(f"base source authority/geometry drift: {family}")
        base_seed = next(int(line.split()[1]) for line in base_text.splitlines() if line.startswith("Seed "))
        occupied.add(base_seed)
        family_rows.append({
            "family": family,
            "family_total_events": sum(SHARDS[family]),
            "shards": len(SHARDS[family]),
            "source_mixture_sampling_seed": base_seed,
            "base_source_path": str(base_source),
            "base_source_sha256": sha256(base_source),
        })
        for shard_index, events in enumerate(SHARDS[family], 1):
            ordinal += 1
            job_id = f"sg3b_delayed_{family}_shard{shard_index:04d}"
            seed_identity = f"SG3B|delayed|{family}|shard{shard_index:04d}|events{events}"
            seed = derive_seed(seed_identity, occupied)
            source = sources / f"{job_id}.source"
            output_prefix = RUN_ROOT / "jobs" / job_id / "active" / job_id
            source.write_text(
                patch_card(base_text, seed=seed, events=events, output_prefix=output_prefix, job_id=job_id),
                encoding="utf-8",
            )
            job = {
                "ordinal": ordinal,
                "job_id": job_id,
                "candidate": CANDIDATE,
                "stage": "delayed",
                "mode": "delayed",
                "family": family,
                "events": events,
                "seed": seed,
                "source_path": str(source),
                "setup_path": str(GEOMETRY),
                "output_prefix": str(output_prefix),
                "estimated_bytes": 2 * 1024**3,
                "requires_isotope_dat": False,
                "production_canary": family == "p" and shard_index == 1,
            }
            jobs.append(job)
            seed_rows.append({
                "job_id": job_id,
                "family": family,
                "shard": shard_index,
                "events": events,
                "seed": seed,
                "seed_identity": seed_identity,
                "collision_with_prior": seed in occupied_before,
                "source_mixture_sampling_seed": base_seed,
                "transport_seed_role": "FRESH_PER_SHARD_GEANT4_RANDOM_STREAM",
            })
            source_rows.append({
                "job_id": job_id,
                "mode": "delayed",
                "family": family,
                "events": events,
                "seed": seed,
                "source_path": str(source),
                "setup_path": str(GEOMETRY),
                "source_sha256": sha256(source),
            })
    if len(jobs) != 33 or sum(int(row["events"]) for row in jobs) != 8_000_000:
        raise RuntimeError("global shard count/event closure differs from 33/8,000,000")
    if len({int(row["seed"]) for row in jobs}) != len(jobs):
        raise RuntimeError("shard transport seeds are not unique")
    if any(row["collision_with_prior"] for row in seed_rows):
        raise RuntimeError("fresh shard transport seed collides with prior registry")
    if sum(bool(row["production_canary"]) for row in jobs) != 1:
        raise RuntimeError("canary closure differs from exactly one")

    totals = {"jobs": len(jobs), "instant_histories": 0, "buildup_histories": 0}
    write_json(GENERATED / "job_plan.json", {
        "schema_version": 1,
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "candidate": CANDIDATE,
        "jobs": jobs,
        "totals": totals,
    })
    write_json(GENERATED / "seed_registry.json", {
        "schema_version": 1,
        "status": "PASS__FRESH_GLOBALLY_DISJOINT_SHARD_SEEDS",
        "profile_id": PROFILE_ID,
        "occupied_prior_seed_count": len(occupied_before),
        "fresh_seed_count": len(seed_rows),
        "authorities": authorities,
        "seeds": seed_rows,
    })
    write_json(GENERATED / "source_manifest.json", {
        "schema_version": 1,
        "status": "PASS__SG3B_M05_SHARDED_DELAYED_SOURCES",
        "profile_id": PROFILE_ID,
        "sources": source_rows,
    })
    write_json(GENERATED / "preflight.json", {
        "schema_version": 1,
        "status": "PASS__SG3B_M05_SHARDED_DELAYED_PREFLIGHT",
        "profile_id": PROFILE_ID,
        "candidate": CANDIDATE,
        "job_plan": totals,
    })
    write_json(GENERATED / "sharding_manifest.json", {
        "schema_version": 1,
        "status": "PASS__SG3B_M05_8M_SHARD_AND_SEED_CLOSURE",
        "created_at": utc_now(),
        "candidate": CANDIDATE,
        "geometry": str(GEOMETRY),
        "base_activation_manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path)},
        "families": family_rows,
        "jobs": 33,
        "events_per_family": 1_000_000,
        "total_events": 8_000_000,
        "canary": {"job_id": jobs[0]["job_id"], "events": jobs[0]["events"]},
        "workers": 8,
        "merge_boundary": "ONLY_WITHIN_IDENTICAL_SG3B_GEOMETRY_DELAYED_MODE_AND_INCIDENT_FAMILY",
        "source_policy": "All shards of a family reuse its audited 50k-to-10k exact-position activity mixture; every shard has a fresh transport seed.",
    })
    free = os.statvfs(TARGET).f_bavail * os.statvfs(TARGET).f_frsize
    config = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "candidate": CANDIDATE,
        "allowed_stages": ["delayed"],
        "source_policy": "m05_exact_position_delayed_sharded",
        "preflight_pass_status": "PASS__SG3B_M05_SHARDED_DELAYED_PREFLIGHT",
        "source_manifest_pass_status": "PASS__SG3B_M05_SHARDED_DELAYED_SOURCES",
        "seed_registry_pass_status": "PASS__FRESH_GLOBALLY_DISJOINT_SHARD_SEEDS",
        "geometry_setup": str(GEOMETRY),
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "cosima_workdir": "/home/ubuntu/TES_511_Balloon",
        "generated_root": str(GENERATED),
        "run_root": str(RUN_ROOT),
        "workers": 8,
        "max_workers": 8,
        "max_attempts": 2,
        "canary_job_id": jobs[0]["job_id"],
        "start_free_bytes": 100 * 1024**3,
        "dynamic_reserve_bytes": 64 * 1024**3,
        "launch_mem_available_bytes": 1536 * 1024**2,
        "runtime_mem_floor_bytes": 1536 * 1024**2,
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 1024**3,
        "launch_worker_reservation_bytes": 1280 * 1024**2,
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0,
        "runtime_memory_full_psi_avg10_max": 100.0,
        "poll_seconds": 2.0,
        "progress_interval_seconds": 2.0,
        "expected_jobs": len(jobs),
        "expected_instant_histories": 0,
        "expected_buildup_histories": 0,
        "prepared_free_bytes": free,
        "forbidden_legacy_token": FORBIDDEN_TOKEN,
    }
    write_json(TARGET / "config.json", config)
    write_json(TARGET / "launch.json", {
        "controller_command": ["python3", "-B", str(EXECUTOR), "--config", str(TARGET / "config.json"), "--workers", "8"],
        "progress_command": ["python3", "-B", str(PROGRESS), "--config", str(TARGET / "config.json")],
    })
    return TARGET / "config.json"


if __name__ == "__main__":
    print(prepare())
