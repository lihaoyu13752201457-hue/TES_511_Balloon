#!/usr/bin/env python3
"""Shared immutable contract for the SE3 Plan-1 one-third screen."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[2]
RUN_ROOT = REPO_ROOT / "runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1"

SOURCE_WORKTREE = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
PRIMARY_ROOT = Path("/home/ubuntu/TES_511_Balloon")
HANDOFF_WORKTREE = Path("/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon")
HANDOFF = HANDOFF_WORKTREE / (
    "engineering/geometry_optimization_20260815/"
    "46_se3_one_third_transport_handoff_20260815/SE3_ONE_THIRD_TRANSPORT_HANDOFF.md"
)
SE3_SETUP = HANDOFF_WORKTREE / (
    "engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/"
    "geometry/DEMO2_DR_v3p5_SE3.geo.setup"
)
S3D_SETUP = SOURCE_WORKTREE / (
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASE_SOURCE_ROOT = SOURCE_WORKTREE / (
    "engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8"
)
SOURCE_CONTRACT = SOURCE_WORKTREE / (
    "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
)
M05_ROOT = SOURCE_WORKTREE / (
    "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
)
S3D_STATS_ROOT = HANDOFF_WORKTREE / (
    "engineering/geometry_optimization_20260815/45_s3d_o8_particle_statistics_20260815"
)
EVENTLIST = PRIMARY_ROOT / (
    "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB_ENV = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")

PROFILE_ID = "SE3_PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN"
SCHEMA_VERSION = 1
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
MODES = ("instant", "buildup")
SOURCE_TAG = {family: family for family in FAMILIES}
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"

START_FREE_GATE_BYTES = 30_000_000_000
DYNAMIC_RESERVE_BYTES = 8 * 1024**3
CPU_BUDGET = 6
MAX_CPU_BUDGET = 8
MAX_ATTEMPTS = 2

S3D_HISTORIES = {
    ("instant", "p"): 25_448,
    ("instant", "n"): 232_991,
    ("instant", "alpha"): 5_958,
    ("instant", "gamma"): 3_207_738,
    ("instant", "eminus"): 295_341,
    ("instant", "eplus"): 60_184,
    ("instant", "muminus"): 10_443,
    ("instant", "muplus"): 3_972,
    ("buildup", "p"): 25_448,
    ("buildup", "n"): 232_991,
    ("buildup", "alpha"): 4_343,
    ("buildup", "gamma"): 2_356_499,
    ("buildup", "eminus"): 295_341,
    ("buildup", "eplus"): 60_184,
    ("buildup", "muminus"): 67_690,
    ("buildup", "muplus"): 3_972,
}

SHARDS = {
    ("instant", "p"): (8_483,),
    ("instant", "n"): (77_664,),
    ("instant", "alpha"): (1_986,),
    ("instant", "gamma"): (267_312, 267_312, 267_311, 267_311),
    ("instant", "eminus"): (98_447,),
    ("instant", "eplus"): (20_062,),
    ("instant", "muminus"): (3_481,),
    ("instant", "muplus"): (1_324,),
    ("buildup", "p"): (8_483,),
    ("buildup", "n"): (77_664,),
    ("buildup", "alpha"): (1_448,),
    ("buildup", "gamma"): (261_834, 261_833, 261_833),
    ("buildup", "eminus"): (98_447,),
    ("buildup", "eplus"): (20_062,),
    ("buildup", "muminus"): (22_564,),
    ("buildup", "muplus"): (1_324,),
}

# Handoff estimates, decimal bytes, for launch admission only.  Receipts replace
# the estimate with actual bytes as soon as a job completes.
CELL_ESTIMATED_BYTES = {
    ("instant", "p"): 1_769_000_000,
    ("instant", "n"): 1_724_000_000,
    ("instant", "alpha"): 1_186_000_000,
    ("instant", "gamma"): 3_121_000_000,
    ("instant", "eminus"): 1_034_000_000,
    ("instant", "eplus"): 1_430_000_000,
    ("instant", "muminus"): 45_000_000,
    ("instant", "muplus"): 17_000_000,
    ("buildup", "p"): 1_661_000_000,
    ("buildup", "n"): 1_533_000_000,
    ("buildup", "alpha"): 787_000_000,
    ("buildup", "gamma"): 2_414_000_000,
    ("buildup", "eminus"): 1_025_000_000,
    ("buildup", "eplus"): 1_239_000_000,
    ("buildup", "muminus"): 290_000_000,
    ("buildup", "muplus"): 16_000_000,
}

DELAYED_EVENTS = 83_334
DELAYED_TOTAL_ESTIMATED_BYTES = 839_000_000
SIGNAL_EVENTS = 37_194
SIGNAL_ESTIMATED_BYTES = 24_000_000
INPUT_OPTICS_AEFF_CM2 = 20.08476
SIGNAL_INJECTION_XPRIME_CM = -30.0001

S3D_BACKGROUND = {
    "day15_prompt_cps": 0.0338429281309,
    "day15_delayed_cps": 0.0544797522273,
    "day15_total_cps": 0.0883226803582,
    "mission20_prompt_counts": 55_398.9794340,
    "mission20_delayed_counts": 88_804.8626519,
    "mission20_background_counts": 144_203.8420859011,
    "mission20_background_upper95_proxy": 1_249_284.0948305726,
}


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def write_once_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"write-once file differs: {path}")
        return
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(text, encoding="utf-8")
    try:
        os.link(partial, path)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"concurrent write-once file differs: {path}")
    finally:
        partial.unlink(missing_ok=True)


def write_once_json(path: Path, value: Any) -> None:
    write_once_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(partial, path)


def base_source(family: str) -> Path:
    return BASE_SOURCE_ROOT / f"Background_{SOURCE_TAG[family]}_fullsphere20.source"


def background_job_id(mode: str, family: str, shard: int) -> str:
    return f"se3_{mode}_{family}_shard{shard:04d}"


def background_run_name(mode: str, family: str, shard: int) -> str:
    return f"SE3_{mode}_{family}_{shard:04d}"


def job_source_path(job_id: str) -> Path:
    return PACKAGE_ROOT / "config/source_cards" / f"{job_id}.source"


def active_prefix(job_id: str) -> Path:
    return RUN_ROOT / "jobs" / job_id / "active" / job_id


def expected_background_bytes(mode: str, family: str, events: int) -> int:
    target = math.ceil(S3D_HISTORIES[(mode, family)] / 3)
    return int(round(CELL_ESTIMATED_BYTES[(mode, family)] * events / target))


def validate_shards() -> None:
    for cell, s3d_events in S3D_HISTORIES.items():
        target = math.ceil(s3d_events / 3)
        parts = SHARDS[cell]
        if sum(parts) != target:
            raise AssertionError(f"ceil(1/3) closure failed for {cell}: {parts} != {target}")
        if target <= 100_000 and len(parts) != 1:
            raise AssertionError(f"sub-100k target was split for {cell}")
        if target > 100_000 and any(value < 100_000 for value in parts):
            raise AssertionError(f"subshard below 100k for {cell}: {parts}")
    if sum(sum(SHARDS[("instant", f)]) for f in FAMILIES) != 1_280_693:
        raise AssertionError("instant target total differs")
    if sum(sum(SHARDS[("buildup", f)]) for f in FAMILIES) != 1_015_492:
        raise AssertionError("buildup target total differs")


def build_job_plan(seed_by_identity: dict[str, int]) -> list[dict[str, Any]]:
    validate_shards()
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for mode in MODES:
        for family in FAMILIES:
            parts = SHARDS[(mode, family)]
            target = sum(parts)
            for shard, events in enumerate(parts, 1):
                ordinal += 1
                job_id = background_job_id(mode, family, shard)
                identity = job_id
                rows.append({
                    "ordinal": ordinal,
                    "job_id": job_id,
                    "stage": "background",
                    "geometry": "SE3",
                    "mode": mode,
                    "family": family,
                    "shard": shard,
                    "events": events,
                    "s3d_histories": S3D_HISTORIES[(mode, family)],
                    "target_histories": target,
                    "seed": seed_by_identity[identity],
                    "seed_identity": identity,
                    "paired_seed_exception": False,
                    "source_path": str(job_source_path(job_id)),
                    "setup_path": str(SE3_SETUP),
                    "estimated_bytes": expected_background_bytes(mode, family, events),
                    "production_canary": mode == "instant" and family == "gamma" and shard == 1,
                })
    for family in FAMILIES:
        ordinal += 1
        job_id = f"se3_delayed_{family}"
        rows.append({
            "ordinal": ordinal,
            "job_id": job_id,
            "stage": "delayed",
            "geometry": "SE3",
            "mode": "delayed",
            "family": family,
            "shard": 1,
            "events": DELAYED_EVENTS,
            "s3d_histories": 250_000,
            "target_histories": DELAYED_EVENTS,
            "seed": seed_by_identity[job_id],
            "seed_identity": job_id,
            "paired_seed_exception": False,
            "source_path": str(PACKAGE_ROOT / "config/delayed_source_cards" / f"{job_id}.source"),
            "setup_path": str(SE3_SETUP),
            "estimated_bytes": int(round(DELAYED_TOTAL_ESTIMATED_BYTES / len(FAMILIES))),
            "production_canary": False,
        })
    pair_identity = "full_envelope_signal_pair_37194"
    for geometry, setup in (("S3d_O8", S3D_SETUP), ("SE3", SE3_SETUP)):
        ordinal += 1
        job_id = f"signal_full_envelope_{geometry.lower()}"
        rows.append({
            "ordinal": ordinal,
            "job_id": job_id,
            "stage": "signal",
            "geometry": geometry,
            "mode": "signal",
            "family": "focused_gamma",
            "shard": 1,
            "events": SIGNAL_EVENTS,
            "s3d_histories": SIGNAL_EVENTS,
            "target_histories": SIGNAL_EVENTS,
            "seed": seed_by_identity[pair_identity],
            "seed_identity": pair_identity,
            "paired_seed_exception": True,
            "source_path": str(PACKAGE_ROOT / "config/signal_source_cards" / f"{job_id}.source"),
            "setup_path": str(setup),
            "estimated_bytes": SIGNAL_ESTIMATED_BYTES,
            "production_canary": False,
        })
    if len(rows) != 31:
        raise AssertionError(f"expected 31 jobs, got {len(rows)}")
    return rows


def plan_identities() -> list[str]:
    result = [
        background_job_id(mode, family, shard)
        for mode in MODES
        for family in FAMILIES
        for shard in range(1, len(SHARDS[(mode, family)]) + 1)
    ]
    result.extend(f"se3_delayed_{family}" for family in FAMILIES)
    result.append("full_envelope_signal_pair_37194")
    return result


def derive_seed(identity: str, occupied: set[int], *, namespace: str = PROFILE_ID) -> int:
    for probe in range(100_000):
        digest = hashlib.sha256(f"{namespace}\x1e{identity}\x1e{probe}".encode()).digest()
        candidate = 1 + int.from_bytes(digest[:8], "big") % 2_147_483_646
        if candidate not in occupied:
            return candidate
    raise RuntimeError("unable to derive a collision-free transport seed")


def derive_seed_plan(occupied: Iterable[int]) -> dict[str, int]:
    reserved = set(occupied)
    result: dict[str, int] = {}
    for identity in plan_identities():
        seed = derive_seed(identity, reserved)
        result[identity] = seed
        reserved.add(seed)
    return result


def read_job_plan(path: Path | None = None) -> list[dict[str, str]]:
    target = path or PACKAGE_ROOT / "data/se3_plan1_job_plan.csv"
    with target.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_once(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if not rows:
        raise ValueError("cannot write empty CSV")
    import io

    output = io.StringIO(newline="")
    names = fieldnames or list(rows[0])
    writer = csv.DictWriter(output, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    write_once_text(path, output.getvalue())
