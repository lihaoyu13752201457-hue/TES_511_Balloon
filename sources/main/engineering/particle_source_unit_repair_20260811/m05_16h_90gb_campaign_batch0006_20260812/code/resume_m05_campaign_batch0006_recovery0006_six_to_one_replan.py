#!/usr/bin/env python3
"""Recovery0006: event-exact, balanced up-to-six replan of unfinished shards.

The original 638-job plan remains immutable.  This recovery selects the 238
PASS receipts frozen by the recovery0006 drain completion, retries each
one-sided missing geometry with its original job and seed, and replaces only
fully-missing matched pairs with balanced bundles of at most six old pairs.
Each fresh seed is used once in Mass_model_511 and once in S3d-O8.  The
effective closure is required to represent every old job exactly once and to
retain the original 6,149,560-event target exactly.

``--print-recovery-plan`` and ``--self-test`` are read-only.  They neither
publish authority nor launch Cosima.
"""

from __future__ import annotations

import argparse
import fcntl
import gzip
import json
import math
import multiprocessing as mp
import os
import re
import shutil
import signal
import subprocess
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import resume_m05_campaign_batch0006_recovery0001 as recovery1
import resume_m05_campaign_batch0006_recovery0005_short_job_concurrency as recovery5
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0006_six_to_one_replan"
RUN_NS = campaign.RUN_ROOT / "recovery0006_six_to_one_replan"
AUTHORITY = RUN_NS / "authority.json"
CUTOVER_RECEIPT = RUN_NS / "cutover_receipt.json"
REPLAN_SEED_REGISTRY = RUN_NS / "seed_registry.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
FINAL_VALIDATION = RUN_NS / "final_validation.json"
FINAL_LEDGER = RUN_NS / "final_ledger.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"

CUTOVER_INTENT = campaign.RUN_ROOT / "recovery0006_six_to_one_replan_cutover_intent.json"
DRAIN_COMPLETION = campaign.RUN_ROOT / "recovery0006_six_to_one_replan_drain_completion.json"
ORPHAN_EVIDENCE = campaign.RUN_ROOT / "recovery0006_six_to_one_replan_cutover_orphan_evidence.json"
RECOVERY4_AUTHORITY = campaign.RUN_ROOT / "recovery0004_live_memory_dynamic_authority.json"
RECOVERY4_CUTOVER = campaign.RUN_ROOT / "recovery0004_cutover_receipt.json"

EXPECTED_GLOBAL_SHA256 = "4586fb62a16c0145401a997f70a878bfaebd94529fe04c45da51a1abcf102275"
EXPECTED_ORIGINAL_PLAN_SHA256 = "d1d1abb26be31ebadf8932af57b61c744866b8293b437bd43e1b9c58805dc0ea"
EXPECTED_ORIGINAL_SEED_REGISTRY_SHA256 = "bb4020cfbd5195660ea5d599eef013e2b58d905592f2799fae3c5686b8caa0ec"
EXPECTED_CUTOVER_INTENT_SHA256 = "e773c979e02d4f202f629a4eb590a80dbf014a8c3ede97d93100a3203bc25828"
EXPECTED_DRAIN_COMPLETION_SHA256 = "f9f2f36ec3fd1f415517881825d79b7fc23cbe9a1aa25659946b81212512168d"
EXPECTED_ORPHAN_EVIDENCE_SHA256 = "af380fc8b342e6efaf76f3e4a289893f72ac41c719c75017b3d43f9b0334a33d"
EXPECTED_RECOVERY4_AUTHORITY_SHA256 = "ff4d69cfe202710e86537d6d7ea1d0b62444fe25bce80b55ffb25a50a22f56e6"
EXPECTED_RECOVERY4_CUTOVER_SHA256 = "a11ae6468117ae77d310e6797ae97a13c46ef1bf9a8571aaf44a0c2344a4fda2"
EXPECTED_INHERITED_RECEIPTS = 238
EXPECTED_INHERITED_EVENTS = 1_770_013
EXPECTED_ORIGINAL_JOBS = 638
EXPECTED_ORIGINAL_SEEDS = 319
EXPECTED_TOTAL_EVENTS = 6_149_560
EXPECTED_FRESH_MATCHED_SEEDS = 123
EXPECTED_STAGE10_FRESH_MATCHED_SEEDS = 97
EXPECTED_STAGE20_FRESH_MATCHED_SEEDS = 26
EXPECTED_FRESH_JOBS = 246
EXPECTED_RETAINED_OLD_JOBS = 4
EXPECTED_PENDING_JOBS = 250
EXPECTED_FINAL_RECEIPTS = 488

MAX_BUNDLE_PAIRS = 6
PLANNING_SINGLE_JOB_RSS_CEILING_BYTES = 6 * 1024**3
PLANNED_RSS_BUDGET_CEILING_BYTES = int(6.5 * 1024**3)
VALIDATION_PUBLICATION_MARGIN_S = 180.0
FRESH_SEED_BASE = 2_000_000_003
FRESH_SEED_STRIDE = 104_729
MAX_WORKERS = 8
NORMAL_TARGET_WORKERS = 8
LAUNCH_STAGGER_S = 15.0
SOFT_FLOOR_BYTES = int(1.5 * 1024**3)
RESUME_FLOOR_BYTES = 2 * 1024**3
RESUME_DWELL_S = 30.0
UNSEEN_CLASS_MIN_BYTES = 1024**3
CLASS_FACTOR = 1.15
CLASS_PAD_BYTES = 128 * 1024**2
ACTIVE_SAMPLE_INTERVAL_S = 5.0
ACTIVE_WINDOW_S = 90.0
ACTIVE_SLOPE_WINDOW_S = 30.0
ACTIVE_MATURITY_S = 60.0
ACTIVE_TRAJECTORY_S = 30.0
ACTIVE_HORIZON_S = 60.0
ACTIVE_PAD_BYTES = 64 * 1024**2
POLL_S = 0.5
EVIDENCE_REFRESH_S = 30.0
OLD_STAGE_CAPS = {
    "stage10_seven_family": 1_500_000_000,
    "stage20_proton": 2_000_000_000,
}
BUNDLE_STAGE_CAPS = {
    "stage10_seven_family": 2_000_000_000,
    "stage20_proton": 6_000_000_000,
}
# Independently audited conservative linear output-RSS envelopes.  They are
# multiplied by actual original-shard event equivalents below; each geometry
# boundary uses the stricter of its Mass/O8 predictions.  The receipt-derived
# anchor and this table are both printed and hash-bound before authority.
AUDITED_SIX_PAIR_RSS_GIB = {
    ("stage10_seven_family", "instant", "gamma"): 9.09,
    ("stage10_seven_family", "buildup", "gamma"): 8.91,
    ("stage10_seven_family", "buildup", "neutron"): 12.35,
    ("stage10_seven_family", "buildup", "eplus"): 11.20,
}
AUDITED_MAX_PAIRS = {
    ("stage10_seven_family", "instant", "gamma"): 1,
    ("stage10_seven_family", "instant", "neutron"): 3,
    ("stage10_seven_family", "instant", "eplus"): 6,
    ("stage10_seven_family", "instant", "eminus"): 6,
    ("stage10_seven_family", "instant", "alpha"): 6,
    ("stage10_seven_family", "instant", "muplus"): 6,
    ("stage10_seven_family", "instant", "muminus"): 6,
    ("stage10_seven_family", "buildup", "gamma"): 2,
    ("stage10_seven_family", "buildup", "neutron"): 1,
    ("stage10_seven_family", "buildup", "eplus"): 2,
    ("stage10_seven_family", "buildup", "eminus"): 6,
    ("stage10_seven_family", "buildup", "alpha"): 4,
    ("stage10_seven_family", "buildup", "muplus"): 6,
    ("stage10_seven_family", "buildup", "muminus"): 6,
    ("stage20_proton", "instant", "proton"): 1,
    ("stage20_proton", "buildup", "proton"): 1,
}
AUDITED_STAGE10_BUDGET_GIB = {
    ("buildup", "Mass_model_511", "alpha"): 2.058, ("buildup", "S3d_O8", "alpha"): 5.607,
    ("buildup", "Mass_model_511", "eminus"): 1.475, ("buildup", "S3d_O8", "eminus"): 1.049,
    ("buildup", "Mass_model_511", "eplus"): 1.226, ("buildup", "S3d_O8", "eplus"): 4.778,
    ("buildup", "Mass_model_511", "gamma"): 1.465, ("buildup", "S3d_O8", "gamma"): 5.314,
    ("buildup", "Mass_model_511", "muminus"): 1.0, ("buildup", "S3d_O8", "muminus"): 1.0,
    ("buildup", "Mass_model_511", "muplus"): 1.0, ("buildup", "S3d_O8", "muplus"): 1.0,
    ("buildup", "Mass_model_511", "neutron"): 2.549, ("buildup", "S3d_O8", "neutron"): 4.793,
    ("instant", "Mass_model_511", "alpha"): 3.237, ("instant", "S3d_O8", "alpha"): 5.226,
    ("instant", "Mass_model_511", "eminus"): 1.333, ("instant", "S3d_O8", "eminus"): 1.030,
    ("instant", "Mass_model_511", "eplus"): 5.662, ("instant", "S3d_O8", "eplus"): 3.713,
    ("instant", "Mass_model_511", "gamma"): 1.339, ("instant", "S3d_O8", "gamma"): 5.570,
    ("instant", "Mass_model_511", "muminus"): 1.0, ("instant", "S3d_O8", "muminus"): 1.0,
    ("instant", "Mass_model_511", "muplus"): 1.0, ("instant", "S3d_O8", "muplus"): 1.0,
    ("instant", "Mass_model_511", "neutron"): 3.790, ("instant", "S3d_O8", "neutron"): 5.538,
}
STAGE20_CANARY_PREBUDGET_GIB = {
    ("instant", "Mass_model_511", 512): 1.54,
    ("instant", "Mass_model_511", 1024): 2.14,
    ("instant", "S3d_O8", 512): 2.66,
    ("instant", "S3d_O8", 1024): 4.33,
    ("buildup", "Mass_model_511", 512): 2.91,
    ("buildup", "Mass_model_511", 1024): 4.85,
    ("buildup", "S3d_O8", 512): 1.50,
    ("buildup", "S3d_O8", 1024): 1.96,
}

_COORDINATOR_STOP = False
_ACTIVE_WORKERS: dict[int, "Worker"] = {}
_VALIDATED_ORIGINAL_RECEIPTS: dict[str, dict[str, Any]] = {}
_ORIGINAL_METRICS: dict[str, dict[str, Any]] = {}
_VALIDATED_REPLAN_RECEIPTS: dict[str, dict[str, Any]] = {}


@dataclass
class Worker:
    job: dict[str, Any]
    process: Any
    connection: Any
    launched_at: str
    launched_monotonic: float


@dataclass
class Health:
    paused: bool = False
    resume_since: float | None = None
    rss_samples: dict[int, deque[tuple[float, int]]] | None = None


def sha(path: Path) -> str:
    return campaign.sha256(path)


def jsha(value: Any) -> str:
    return campaign.json_sha256(value)


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def attempt_dir(job: dict[str, Any], attempt: int) -> Path:
    return (
        RUN_NS / "attempts" / str(job["stage"]) / str(job["geometry"])
        / str(job["mode"]) / str(job["family"]) / str(job["job_id"])
        / f"attempt{attempt:02d}"
    )


def failed_dir(job: dict[str, Any], attempt: int) -> Path:
    return RUN_NS / "failed_attempts" / str(job["job_id"]) / f"attempt{attempt:02d}"


def job_cap(job: dict[str, Any]) -> int:
    if job.get("replan_kind") == "fresh_balanced_bundle":
        return BUNDLE_STAGE_CAPS[str(job["stage"])]
    return OLD_STAGE_CAPS[str(job["stage"])]


def original_receipt_path(job: dict[str, Any]) -> Path:
    return campaign.RUN_ROOT / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def validate_original_receipt(job: dict[str, Any], path: Path) -> dict[str, Any]:
    cached = _VALIDATED_ORIGINAL_RECEIPTS.get(str(job["job_id"]))
    if cached is not None:
        if cached.get("job") != job:
            raise RuntimeError(f"cached inherited receipt job mismatch: {job['job_id']}")
        return cached
    payload = load(path)
    if payload.get("job") != job:
        raise RuntimeError(f"inherited receipt job mismatch: {job['job_id']}")
    if not campaign.receipt_hashes_valid(payload):
        raise RuntimeError(f"inherited receipt artifact/hash closure failed: {job['job_id']}")
    _VALIDATED_ORIGINAL_RECEIPTS[str(job["job_id"])] = payload
    return payload


def receipt_manifest_for_old_plan(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in plan:
        path = original_receipt_path(job)
        if not path.is_file():
            continue
        validate_original_receipt(job, path)
        rows.append({"job_id": job["job_id"], "path": rel(path), "sha256": sha(path), "events": int(job["events"])})
    return sorted(rows, key=lambda row: str(row["job_id"]))


def validated_original_metrics(original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not _ORIGINAL_METRICS:
        for job in original:
            path = original_receipt_path(job)
            if not path.is_file():
                continue
            payload = validate_original_receipt(job, path)
            _ORIGINAL_METRICS[str(job["job_id"])] = {
                "job": job, "receipt": payload,
                "artifact_bytes": sum(int(row["bytes"]) for row in payload["artifacts"].values()),
                "peak_rss_bytes": int(payload["peak_process_group_rss_bytes"]),
                "wall_s": float(payload["wall_s"]),
            }
    return list(_ORIGINAL_METRICS.values())


def verify_frozen_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    required = {
        campaign.GLOBAL_CONTRACT: EXPECTED_GLOBAL_SHA256,
        campaign.SEED_REGISTRY: EXPECTED_ORIGINAL_SEED_REGISTRY_SHA256,
        CUTOVER_INTENT: EXPECTED_CUTOVER_INTENT_SHA256,
        DRAIN_COMPLETION: EXPECTED_DRAIN_COMPLETION_SHA256,
        ORPHAN_EVIDENCE: EXPECTED_ORPHAN_EVIDENCE_SHA256,
        RECOVERY4_AUTHORITY: EXPECTED_RECOVERY4_AUTHORITY_SHA256,
        RECOVERY4_CUTOVER: EXPECTED_RECOVERY4_CUTOVER_SHA256,
    }
    for path, expected in required.items():
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"frozen input missing/drifted: {rel(path)}")
    contract = load(campaign.GLOBAL_CONTRACT)
    plan = campaign.build_plan()
    if len(plan) != EXPECTED_ORIGINAL_JOBS or jsha(plan) != EXPECTED_ORIGINAL_PLAN_SHA256:
        raise RuntimeError("original 638-job plan drift")
    if contract.get("planned_jobs") != plan or contract.get("planned_jobs_sha256") != EXPECTED_ORIGINAL_PLAN_SHA256:
        raise RuntimeError("global contract no longer embeds exact original plan")
    registry = load(campaign.SEED_REGISTRY)
    old_seeds = {int(row["seed"]) for row in registry.get("planned", [])}
    if len(old_seeds) != EXPECTED_ORIGINAL_SEEDS or old_seeds != {int(j["seed"]) for j in plan}:
        raise RuntimeError("all 319 original seeds are not exactly reserved")
    drain = load(DRAIN_COMPLETION)
    if drain.get("status") != "PASS__RECOVERY0004_DRAINED__READY_FOR_RECOVERY0006_REPLAN":
        raise RuntimeError("drain completion does not authorize replan")
    manifest = receipt_manifest_for_old_plan(plan)
    frozen_manifest = drain.get("receipt_manifest_before")
    if manifest != frozen_manifest or jsha(manifest) != drain.get("receipt_manifest_before_closure_sha256"):
        raise RuntimeError("current PASS manifest differs from frozen 238-receipt drain manifest")
    if len(manifest) != EXPECTED_INHERITED_RECEIPTS or sum(int(x["events"]) for x in manifest) != EXPECTED_INHERITED_EVENTS:
        raise RuntimeError("inherited receipt count/event target differs")
    return contract, plan, manifest


def balanced_sizes(n: int) -> list[int]:
    if n <= 0:
        return []
    groups = math.ceil(n / MAX_BUNDLE_PAIRS)
    q, r = divmod(n, groups)
    sizes = [q + 1] * r + [q] * (groups - r)
    if sum(sizes) != n or max(sizes) > MAX_BUNDLE_PAIRS or max(sizes) - min(sizes) > 1:
        raise AssertionError("invalid balanced bundle partition")
    return sizes


def all_discoverable_seeds() -> set[int]:
    """Conservative global scan; hash-like integers are harmless reservations."""
    seeds: set[int] = set()
    seed_line = re.compile(r"^\s*Seed\s+(\d+)\s*$", re.MULTILINE)
    scan_root = campaign.ROOT / "runs/particle_source_unit_repair_20260811"
    for path in scan_root.rglob("*.source"):
        try:
            seeds.update(int(x) for x in seed_line.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    for path in scan_root.rglob("*.json"):
        if RUN_NS in path.parents:
            continue
        try:
            value = load(path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        campaign._extract_seed_values(value, seeds)
    return seeds


def allocate_fresh_seeds(count: int, reserved: set[int]) -> list[int]:
    result: list[int] = []
    candidate = FRESH_SEED_BASE
    while len(result) < count:
        if 1 <= candidate < 2**31 and candidate not in reserved and candidate not in result:
            result.append(candidate)
        candidate += FRESH_SEED_STRIDE
        if candidate >= 2**31:
            candidate = 1_900_000_001 + len(result) * 2
    return result


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def planned_rss_budget(
    job: dict[str, Any], original: list[dict[str, Any]], *, group_pairs: int,
) -> tuple[int, dict[str, Any]]:
    rows: list[tuple[int, int]] = []
    scopes: list[str] = []
    metrics = validated_original_metrics(original)
    for metric in metrics:
        old_job = metric["job"]
        same = (
            old_job["stage"] == job["stage"] and old_job["mode"] == job["mode"]
            and old_job["geometry"] == job["geometry"] and old_job["family"] == job["family"]
        )
        if same:
            rows.append((int(metric["artifact_bytes"]), int(metric["peak_rss_bytes"])))
            scopes.append("same_stage_geometry_mode_family")
    if not rows:
        for metric in metrics:
            old_job = metric["job"]
            fallback = (
                old_job["mode"] == job["mode"] and old_job["family"] == job["family"]
                and (old_job["geometry"] == job["geometry"] or old_job["stage"] == "stage00_mergeable_smoke")
            )
            if fallback:
                rows.append((int(metric["artifact_bytes"]), int(metric["peak_rss_bytes"])))
                scopes.append("same_mode_family_geometry_or_smoke_fallback")
    if rows:
        xs = [float(x) for x, _y in rows]
        ys = [float(y) for _x, y in rows]
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        denominator = sum((x - mean_x) ** 2 for x in xs)
        slope = max(0.0, sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator) if denominator else 0.0
        intercept = mean_y - slope * mean_x
        residual_tail = max(0.0, max(y - (intercept + slope * x) for x, y in zip(xs, ys)))
        projected_artifact = max(xs) + max(0, group_pairs - 1) * median(xs)
        base = intercept + slope * projected_artifact + residual_tail
    else:
        slope = intercept = residual_tail = projected_artifact = 0.0
        base = float(UNSEEN_CLASS_MIN_BYTES)
        scopes.append("unseen_1GiB_floor")
    cell = (str(job["stage"]), str(job["mode"]), str(job["family"]))
    if cell in AUDITED_SIX_PAIR_RSS_GIB:
        single = max([float(y) for _x, y in rows], default=float(UNSEEN_CLASS_MIN_BYTES))
        six = AUDITED_SIX_PAIR_RSS_GIB[cell] * 1024**3
        audited = single + max(0, group_pairs - 1) * (six - single) / 5
        base = max(base, audited)
    padded = base * 1.25 + 256 * 1024**2
    audited_key = (str(job["mode"]), str(job["geometry"]), str(job["family"]))
    if job["stage"] == "stage10_seven_family" and audited_key in AUDITED_STAGE10_BUDGET_GIB:
        locally_recomputed_padded = padded
        padded = AUDITED_STAGE10_BUDGET_GIB[audited_key] * 1024**3
        scopes.append("independent_audited_conservative_stage10_budget_is_frozen_final_budget")
    canary_key = (str(job["mode"]), str(job["geometry"]), int(job["events"]))
    if job["stage"] == "stage20_proton" and canary_key in STAGE20_CANARY_PREBUDGET_GIB:
        padded = max(padded, STAGE20_CANARY_PREBUDGET_GIB[canary_key] * 1024**3)
        scopes.append("independent_audited_stage20_canary_prebudget")
    if job["stage"] == "stage20_proton" and int(job["events"]) > 1024:
        # The static plan cannot honestly budget 2048-event proton work from
        # smoke.  Runtime must hash-bind paired 512/1024 canaries first.
        padded = float(PLANNED_RSS_BUDGET_CEILING_BYTES)
        scopes.append("runtime_write_once_stage20_canary_calibration_required")
    budget = math.ceil(padded / (64 * 1024**2)) * 64 * 1024**2
    if budget > PLANNED_RSS_BUDGET_CEILING_BYTES and not (
        job["stage"] == "stage20_proton" and int(job["events"]) > 1024
    ):
        raise RuntimeError(
            f"audited group exceeds 6.5GiB plan ceiling and must be split: {job['job_id']} budget={budget}"
        )
    if job["stage"] == "stage20_proton" and int(job["events"]) > 1024:
        budget = PLANNED_RSS_BUDGET_CEILING_BYTES
    return int(budget), {
        "scope": sorted(set(scopes)), "receipt_count": len(rows), "group_pairs": group_pairs,
        "ols_slope_rss_per_artifact_byte": slope, "ols_intercept_bytes": intercept,
        "one_max_tail_residual_bytes": residual_tail, "median_plus_one_max_projected_artifact_bytes": projected_artifact,
        "unpadded_prediction_bytes": base, "formula": "(OLS_at_one_max_plus_median_tails + max_positive_residual)*1.25 + 256MiB; ceil64MiB; cap6.5GiB",
        "budget_ceiling_bytes": PLANNED_RSS_BUDGET_CEILING_BYTES,
        "locally_recomputed_padded_audit_only_bytes": (
            locally_recomputed_padded if job["stage"] == "stage10_seven_family" and audited_key in AUDITED_STAGE10_BUDGET_GIB else None
        ),
    }


def planned_wall_budget(job: dict[str, Any], original: list[dict[str, Any]], group_pairs: int) -> tuple[float, dict[str, Any]]:
    walls: list[float] = []
    metrics = validated_original_metrics(original)
    for metric in metrics:
        old_job = metric["job"]
        if (
            old_job["stage"] == job["stage"] and old_job["mode"] == job["mode"]
            and old_job["geometry"] == job["geometry"] and old_job["family"] == job["family"]
        ):
            walls.append(float(metric["wall_s"]))
    if not walls and job["stage"] == "stage20_proton":
        for metric in metrics:
            old_job = metric["job"]
            if old_job["stage"] == "stage00_mergeable_smoke" and old_job["mode"] == job["mode"] and old_job["geometry"] == job["geometry"] and old_job["family"] == job["family"]:
                walls.append(float(metric["wall_s"]))
    startup = 12.0
    beam = [max(0.0, wall - startup) for wall in walls] or [120.0]
    event_scale = 1.0
    if job["stage"] == "stage20_proton":
        event_scale = int(job["events"]) / 64.0
    raw = startup + max(beam) * event_scale + max(0, group_pairs - 1) * median(beam)
    budget = raw * 1.25 + 60.0
    return budget, {
        "formula": "(startup12s + one-max beam tail + (k-1)*median incremental beam)*1.25 + 60s",
        "receipt_count": len(walls), "group_pairs": group_pairs, "old_max_wall_s": max(walls) if walls else None,
        "old_median_beam_s": median(beam), "stage20_event_scale_from_64_event_smoke": event_scale,
        "planned_wall_budget_s": budget,
    }


def build_effective_plan(
    original: list[dict[str, Any]], manifest: list[dict[str, Any]], *,
    reserved: set[int] | None = None,
    max_group_by_cell: dict[tuple[str, str, str], int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    passed = {str(row["job_id"]) for row in manifest}
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in original:
        by_key[str(job["matched_seed_key"])].append(job)
    inherited = [job for job in original if job["job_id"] in passed]
    retained: list[dict[str, Any]] = []
    fully_missing: dict[tuple[str, str, str], list[list[dict[str, Any]]]] = defaultdict(list)
    for key, pair in by_key.items():
        pair = sorted(pair, key=lambda row: campaign.GEOMETRY_ORDER.index(str(row["geometry"])))
        if len(pair) != 2 or {j["geometry"] for j in pair} != set(campaign.GEOMETRY_ORDER):
            raise RuntimeError(f"original matched-pair contract failed: {key}")
        present = [job for job in pair if job["job_id"] in passed]
        if len(present) == 1:
            retained.append(next(job for job in pair if job["job_id"] not in passed))
        elif not present:
            cell = (str(pair[0]["stage"]), str(pair[0]["mode"]), str(pair[0]["family"]))
            fully_missing[cell].append(pair)
    for pairs in fully_missing.values():
        pairs.sort(key=lambda pair: int(pair[0]["shard_ordinal"]))
    bundle_specs: list[tuple[tuple[str, str, str], int, list[list[dict[str, Any]]]]] = []
    max_group_by_cell = max_group_by_cell or {cell: MAX_BUNDLE_PAIRS for cell in fully_missing}
    for cell in sorted(fully_missing):
        pairs = fully_missing[cell]
        offset = 0
        maximum = int(max_group_by_cell[cell])
        if not 1 <= maximum <= MAX_BUNDLE_PAIRS:
            raise RuntimeError(f"invalid resource-aware group maximum for {cell}: {maximum}")
        groups = math.ceil(len(pairs) / maximum)
        q, r = divmod(len(pairs), groups)
        sizes = [q + 1] * r + [q] * (groups - r)
        if max(sizes) > maximum or max(sizes) - min(sizes) > 1:
            raise AssertionError("resource-aware balanced partition failed")
        for ordinal, size in enumerate(sizes, 1):
            bundle_specs.append((cell, ordinal, pairs[offset : offset + size]))
            offset += size
        if offset != len(pairs):
            raise AssertionError("bundle partition did not consume cell")
    reserved_set = set(reserved or all_discoverable_seeds())
    reserved_set.update(int(job["seed"]) for job in original)
    fresh_seeds = allocate_fresh_seeds(len(bundle_specs), reserved_set)
    fresh: list[dict[str, Any]] = []
    for seed, (cell, bundle_ordinal, pairs) in zip(fresh_seeds, bundle_specs):
        stage, mode, family = cell
        stage_token = {"stage10_seven_family": "s10", "stage20_proton": "s20"}[stage]
        old_keys = [str(pair[0]["matched_seed_key"]) for pair in pairs]
        for geometry in campaign.GEOMETRY_ORDER:
            old_jobs = [next(job for job in pair if job["geometry"] == geometry) for pair in pairs]
            fresh.append({
                "job_id": f"r6_{stage_token}_{family}_{mode}_{geometry}_bundle{bundle_ordinal:04d}",
                "stage": stage,
                "geometry": geometry,
                "mode": mode,
                "family": family,
                "source_tag": str(old_jobs[0]["source_tag"]),
                "shard_ordinal": bundle_ordinal,
                "events": sum(int(job["events"]) for job in old_jobs),
                "seed": seed,
                "matched_seed_key": f"recovery0006|{stage}|{mode}|{family}|bundle{bundle_ordinal:04d}",
                "replan_kind": "fresh_balanced_bundle",
                "bundle_pair_count": len(pairs),
                "supersedes_old_job_ids": [str(job["job_id"]) for job in old_jobs],
                "supersedes_old_matched_seed_keys": old_keys,
            })
    for job in fresh:
        job["declared_cap_bytes"] = BUNDLE_STAGE_CAPS[str(job["stage"])]
        job["declared_cap_evidence"] = {
            "scope": "independently audited up-to-six retain-all projection",
            "stage10_measured_worst_up_to_six_O8_gamma_bytes": 1_396_000_000,
            "stage20_projected_worst_proton_bytes": 4_735_000_000,
            "hard_cap_bytes": job["declared_cap_bytes"],
        }
    for job in [*retained, *fresh]:
        group_pairs = int(job.get("bundle_pair_count", 1))
        budget, evidence = planned_rss_budget(job, original, group_pairs=group_pairs)
        job["planned_peak_rss_budget_bytes"] = budget
        job["planned_peak_rss_budget_evidence"] = evidence
        wall_budget, wall_evidence = planned_wall_budget(job, original, group_pairs)
        job["planned_wall_budget_s"] = wall_budget
        job["planned_wall_budget_evidence"] = wall_evidence
        if job["stage"] == "stage20_proton" and int(job["events"]) > 1024:
            job["requires_stage20_canary_calibration"] = True
    retained.sort(key=lambda job: original.index(job))
    fresh.sort(key=lambda job: (str(job["stage"]), str(job["mode"]), str(job["family"]), int(job["shard_ordinal"]), campaign.GEOMETRY_ORDER.index(str(job["geometry"]))))
    pending = retained + fresh
    covered: list[str] = [str(job["job_id"]) for job in inherited]
    covered.extend(str(job["job_id"]) for job in retained)
    for job in fresh:
        covered.extend(str(x) for x in job["supersedes_old_job_ids"])
    counts = {job_id: covered.count(job_id) for job_id in {str(j["job_id"]) for j in original}}
    if set(counts) != {str(j["job_id"]) for j in original} or any(value != 1 for value in counts.values()):
        raise RuntimeError("effective replan does not cover every original job exactly once")
    effective_events = sum(int(job["events"]) for job in inherited) + sum(int(job["events"]) for job in pending)
    fresh_uses: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for job in fresh:
        fresh_uses[int(job["seed"])].append(job)
    if any(len(rows) != 2 or {r["geometry"] for r in rows} != set(campaign.GEOMETRY_ORDER) for rows in fresh_uses.values()):
        raise RuntimeError("fresh matched seed use is not exactly one per geometry")
    stage_fresh = {stage: len({int(job["seed"]) for job in fresh if job["stage"] == stage}) for stage in ("stage10_seven_family", "stage20_proton")}
    if len(fresh_uses) != EXPECTED_FRESH_MATCHED_SEEDS or len(fresh) != EXPECTED_FRESH_JOBS:
        raise RuntimeError("fresh resource-aware bundle count differs from audited mapping")
    if stage_fresh != {"stage10_seven_family": EXPECTED_STAGE10_FRESH_MATCHED_SEEDS, "stage20_proton": EXPECTED_STAGE20_FRESH_MATCHED_SEEDS}:
        raise RuntimeError("per-stage fresh bundle count differs from audited mapping")
    if len(retained) != EXPECTED_RETAINED_OLD_JOBS or len(pending) != EXPECTED_PENDING_JOBS:
        raise RuntimeError("retained/pending mapping count differs from audited mapping")
    if effective_events != EXPECTED_TOTAL_EVENTS or len(inherited) + len(pending) != EXPECTED_FINAL_RECEIPTS:
        raise RuntimeError("effective receipt/event closure differs from target")
    summary = {
        "original_jobs": len(original), "original_events": sum(int(j["events"]) for j in original),
        "inherited_receipts": len(inherited), "inherited_events": sum(int(j["events"]) for j in inherited),
        "fresh_matched_seeds": len(fresh_uses), "fresh_jobs": len(fresh),
        "retained_original_jobs": len(retained), "pending_jobs": len(pending),
        "final_selected_receipts": len(inherited) + len(pending), "effective_events": effective_events,
        "max_group_by_cell": {"|".join(cell): int(size) for cell, size in sorted(max_group_by_cell.items())},
        "bundle_pair_sizes": [int(job["bundle_pair_count"]) for job in fresh if job["geometry"] == campaign.GEOMETRY_ORDER[0]],
        "original_job_coverage_sha256": jsha(sorted(covered)),
    }
    return pending, summary


def seed_registry_payload(
    original: list[dict[str, Any]], pending: list[dict[str, Any]], discoverable_reserved: set[int],
) -> dict[str, Any]:
    old = sorted({int(job["seed"]) for job in original})
    fresh: dict[int, list[str]] = defaultdict(list)
    for job in pending:
        if job.get("replan_kind") == "fresh_balanced_bundle":
            fresh[int(job["seed"])].append(str(job["job_id"]))
    intersection = sorted(set(fresh) & discoverable_reserved)
    if intersection:
        raise RuntimeError(f"fresh recovery0006 seeds intersect discoverable reserved set: {intersection[:10]}")
    return {
        "schema_version": 1,
        "status": "FROZEN__RECOVERY0006_ALL_OLD_SEEDS_RESERVED__FRESH_MATCHED_SEEDS_REGISTERED",
        "original_seed_registry": rel(campaign.SEED_REGISTRY),
        "original_seed_registry_sha256": EXPECTED_ORIGINAL_SEED_REGISTRY_SHA256,
        "reserved_original_seed_count": len(old),
        "reserved_original_seed_list_sha256": jsha(old),
        "fresh_unique_seed_count": len(fresh),
        "fresh_seed_list_sha256": jsha(sorted(fresh)),
        "fresh": [{"seed": seed, "matched_geometry_jobs": sorted(jobs)} for seed, jobs in sorted(fresh.items())],
        "discoverable_reserved_seed_count": len(discoverable_reserved),
        "discoverable_reserved_seed_list_sha256": jsha(sorted(discoverable_reserved)),
        "discoverable_scan_scope": "runs/particle_source_unit_repair_20260811 JSON seed-like integer fields and .source Seed lines; recovery0006 RUN_NS excluded",
        "fresh_intersection_with_discoverable_reserved": intersection,
        "retry_policy": "each recovery0006 job has at most two exact attempts with unchanged seed/events/source/geometry/mode/family",
    }


def inherited_manifest_hash_gate(manifest: list[dict[str, Any]]) -> None:
    current = receipt_manifest_for_old_plan(campaign.build_plan())
    if current != manifest:
        raise RuntimeError("old receipt set changed after recovery0006 plan construction")
    for row in current:
        path = campaign.ROOT / str(row["path"])
        if sha(path) != row["sha256"]:
            raise RuntimeError(f"inherited receipt hash drift: {row['job_id']}")


def proposed_authority(
    contract: dict[str, Any], original: list[dict[str, Any]], manifest: list[dict[str, Any]],
    pending: list[dict[str, Any]], summary: dict[str, Any], registry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__EVENT_EXACT_BALANCED_UP_TO_SIX_REPLAN__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "controller": {"path": rel(Path(__file__).resolve()), "sha256": sha(Path(__file__).resolve())},
        "authorization": {
            "source": "direct user instruction in controlling Codex task",
            "normal_target_workers": NORMAL_TARGET_WORKERS,
            "absolute_worker_cap": MAX_WORKERS,
            "projected_mem_available_floor_bytes": SOFT_FLOOR_BYTES,
            "fully_missing_pairs": "deterministic balanced groups up to six; group sizes differ by at most one",
            "one_sided_missing_geometry": "exact original job and original seed",
        },
        "inputs": {
            "global_contract": rel(campaign.GLOBAL_CONTRACT), "global_contract_sha256": EXPECTED_GLOBAL_SHA256,
            "original_plan_sha256": EXPECTED_ORIGINAL_PLAN_SHA256,
            "original_seed_registry": rel(campaign.SEED_REGISTRY),
            "original_seed_registry_sha256": EXPECTED_ORIGINAL_SEED_REGISTRY_SHA256,
            "cutover_intent": rel(CUTOVER_INTENT), "cutover_intent_sha256": EXPECTED_CUTOVER_INTENT_SHA256,
            "drain_completion": rel(DRAIN_COMPLETION), "drain_completion_sha256": EXPECTED_DRAIN_COMPLETION_SHA256,
            "orphan_evidence": rel(ORPHAN_EVIDENCE), "orphan_evidence_sha256": EXPECTED_ORPHAN_EVIDENCE_SHA256,
            "recovery0004_authority_sha256": EXPECTED_RECOVERY4_AUTHORITY_SHA256,
            "recovery0004_cutover_sha256": EXPECTED_RECOVERY4_CUTOVER_SHA256,
        },
        "frozen_clock": {
            "t0": contract["wall_clock"]["t0"], "deadline": contract["wall_clock"]["deadline"],
            "stages": contract["wall_clock"]["stages"],
        },
        "inherited_pass_manifest": manifest,
        "inherited_pass_manifest_sha256": jsha(manifest),
        "effective_pending_plan": pending,
        "effective_pending_plan_sha256": jsha(pending),
        "effective_closure_summary": summary,
        "fresh_seed_registry_payload_sha256": jsha(registry),
        "scheduler": {
            "mechanism": "independent single-thread Cosima processes",
            "normal_target_workers": NORMAL_TARGET_WORKERS,
            "absolute_worker_cap": MAX_WORKERS,
            "launch_stagger_s": LAUNCH_STAGGER_S,
            "admission": "current MemAvailable minus active unrealised trajectory growth minus candidate class upper must retain 1.5GiB",
            "unseen_large_exact_class": "fewer than two exact-class receipts permits at most one same-class active job; distinct audited classes may run concurrently",
            "soft_preemption": False,
            "maximum_exact_attempts": 2,
            "bundle_declared_cap": {
                "fixed_stage_caps": BUNDLE_STAGE_CAPS,
                "audit_basis": "measured worst up-to-six O8 gamma 1.30GiB; projected worst proton 4.41GiB",
                "old_exact_mate_caps": OLD_STAGE_CAPS,
                "disk_admission": "used + sum(active max(0, hardcap-current_attempt_bytes)) + candidate hardcap, plus filesystem/campaign reserves",
            },
        },
        "resource_plan": {
            "version": "recovery0006_resource_plan_v1_independent_audit_20260813",
            "evidence_receipt_manifest_sha256": jsha(manifest),
            "audited_max_pairs": {"|".join(key): value for key, value in sorted(AUDITED_MAX_PAIRS.items())},
            "stage10_geometry_specific_final_budget_GiB": {"|".join(key): value for key, value in sorted(AUDITED_STAGE10_BUDGET_GIB.items())},
            "stage10_budget_formula": "1.25*max(old maxRSS, OLS(a+b*(max artifact bytes+(k-1)*median artifact bytes)))+256MiB; b<0=>0,a=maxRSS; values in table are frozen final budgets then ceil64MiB",
            "stage20_canary_prebudget_GiB": {"|".join(map(str, key)): value for key, value in sorted(STAGE20_CANARY_PREBUDGET_GIB.items())},
            "planned_wall_budget_formula": "(startup12s+one-max beam tail+(k-1)*median beam)*1.25+60s",
            "validation_publication_margin_s": VALIDATION_PUBLICATION_MARGIN_S,
        },
        "publication_namespace": rel(RUN_NS),
        "unchanged": {
            "old_code_runs_papers_authorities_receipts_failed_artifacts": True,
            "source_spectra_geometry_physics_detector_cuts": True,
            "per_cell_original_event_target": True,
            "original_deadline": True,
            "compact_authorized": False,
            "mono511_added": False,
        },
    }


def load_or_publish_authority(
    contract: dict[str, Any], original: list[dict[str, Any]], manifest: list[dict[str, Any]],
    pending: list[dict[str, Any]], summary: dict[str, Any], registry: dict[str, Any], *, publish: bool,
) -> dict[str, Any]:
    proposed = proposed_authority(contract, original, manifest, pending, summary, registry)
    if AUTHORITY.is_file():
        payload = load(AUTHORITY)
    elif publish:
        RUN_NS.mkdir(parents=True, exist_ok=True)
        campaign.atomic_write_once_json(AUTHORITY, proposed)
        payload = load(AUTHORITY)
    else:
        return proposed
    checks = {
        "controller": proposed["controller"],
        "inputs": proposed["inputs"],
        "frozen_clock": proposed["frozen_clock"],
        "inherited_pass_manifest_sha256": proposed["inherited_pass_manifest_sha256"],
        "effective_pending_plan_sha256": proposed["effective_pending_plan_sha256"],
        "fresh_seed_registry_payload_sha256": proposed["fresh_seed_registry_payload_sha256"],
    }
    for key, expected in checks.items():
        if payload.get(key) != expected:
            raise RuntimeError(f"recovery0006 authority drift: {key}")
    return payload


def publish_registry_and_cutover(
    authority: dict[str, Any], registry: dict[str, Any], manifest: list[dict[str, Any]],
) -> None:
    if not REPLAN_SEED_REGISTRY.is_file():
        campaign.atomic_write_once_json(REPLAN_SEED_REGISTRY, registry)
    if jsha(load(REPLAN_SEED_REGISTRY)) != authority["fresh_seed_registry_payload_sha256"]:
        raise RuntimeError("published recovery0006 seed registry differs from authority")
    inherited_manifest_hash_gate(manifest)
    if not CUTOVER_RECEIPT.is_file():
        campaign.atomic_write_once_json(CUTOVER_RECEIPT, {
            "schema_version": 1,
            "status": "PASS__RECOVERY0006_EXCLUSIVE_DRAIN_BOUND_CUTOVER",
            "recovery_id": RECOVERY_ID,
            "authority": rel(AUTHORITY), "authority_sha256": sha(AUTHORITY),
            "seed_registry": rel(REPLAN_SEED_REGISTRY), "seed_registry_sha256": sha(REPLAN_SEED_REGISTRY),
            "drain_completion": rel(DRAIN_COMPLETION), "drain_completion_sha256": EXPECTED_DRAIN_COMPLETION_SHA256,
            "inherited_pass_manifest_sha256": jsha(manifest),
            "exclusive_controller_lock_held": True,
            "zero_old_partial_attempts": not list(campaign.RUN_ROOT.glob("stage*/**/.attempt*.partial")),
            "transport_launched_by_receipt": False,
        })
    payload = load(CUTOVER_RECEIPT)
    if payload.get("authority_sha256") != sha(AUTHORITY) or payload.get("seed_registry_sha256") != sha(REPLAN_SEED_REGISTRY):
        raise RuntimeError("recovery0006 cutover closure drift")


def configure_validator() -> None:
    campaign.ID_RE = re.compile(recovery1.CORRECT_ID_PATTERN)
    recovery1.RECOVERY_ID = RECOVERY_ID
    recovery1.RECOVERY_AUTHORITY = AUTHORITY
    campaign.validate_attempt = recovery1.strict_validate_attempt


def load_runtime(contract: dict[str, Any], cosima: Path) -> dict[str, str]:
    environment, descriptor = campaign.clean_transport_environment(cosima)
    current = campaign.transport_fingerprint(cosima, environment, descriptor)
    frozen = contract["static_gate"]["transport"]
    for key in ("cosima_sha256", "resolved_libraries_sha256", "g4_data_sha256"):
        if current[key] != frozen[key]:
            raise RuntimeError(f"resume transport fingerprint drift: {key}")
    return environment


def append_event(kind: str, **fields: Any) -> None:
    RUN_NS.mkdir(parents=True, exist_ok=True)
    with SCHEDULER_EVENTS.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps({
            "at": datetime.now(timezone.utc).isoformat(), "monotonic_s": time.monotonic(),
            "recovery_id": RECOVERY_ID, "event": kind, **fields,
        }, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed: int, error: str | None = None) -> None:
    campaign.atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status, "stage": stage,
        "completed_recovery0006_jobs": completed, "target_recovery0006_jobs": EXPECTED_PENDING_JOBS,
        "final_selected_receipt_target": EXPECTED_FINAL_RECEIPTS,
        "effective_event_target": EXPECTED_TOTAL_EVENTS,
        "deadline": contract["wall_clock"]["deadline"], "updated_at": datetime.now(timezone.utc).isoformat(),
        "mem_available_bytes": campaign.mem_available_bytes(), "campaign_bytes": campaign.campaign_bytes(),
        "free_disk_bytes": shutil.disk_usage(campaign.RUN_ROOT).free, "last_error": error,
    })


def validate_replan_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    cached = _VALIDATED_REPLAN_RECEIPTS.get(str(job["job_id"]))
    if cached is not None and cached == payload:
        return True
    if payload.get("status") != "PASS" or payload.get("job") != job:
        return False
    if payload.get("global_contract_sha256") != EXPECTED_GLOBAL_SHA256:
        return False
    if payload.get("recovery_authority_sha256") != (sha(AUTHORITY) if AUTHORITY.is_file() else None):
        return False
    directory = campaign.ROOT / str(payload.get("attempt_dir", ""))
    for artifact in payload.get("artifacts", {}).values():
        path = directory / str(artifact["name"])
        if not path.is_file() or path.stat().st_size != int(artifact["bytes"]) or sha(path) != artifact["sha256"]:
            return False
    sim_artifact = payload.get("artifacts", {}).get("sim")
    if not sim_artifact:
        return False
    try:
        with gzip.open(directory / sim_artifact["name"], "rb") as handle:
            while handle.read(1024 * 1024):
                pass
    except (OSError, EOFError):
        return False
    framing = payload.get("sim", {}).get("strict_framing", {})
    expected = int(job["events"])
    valid = (
        framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == expected
        and int(framing.get("ID_second_count", -1)) == expected
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == expected
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == expected
    )
    if valid:
        _VALIDATED_REPLAN_RECEIPTS[str(job["job_id"])] = payload
    return valid


def directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def prior_exact_attempts(job: dict[str, Any]) -> set[int]:
    used: set[int] = set()
    roots = [campaign.RUN_ROOT / "failed_attempts" / str(job["job_id"]), RUN_NS / "failed_attempts" / str(job["job_id"])]
    roots.extend((campaign.RUN_ROOT / "failed_attempts" / "recovery0006_cutover_orphan" / str(job["job_id"]),))
    for root in roots:
        for validation_path in root.glob("attempt*/validation.json"):
            match = re.fullmatch(r"attempt(\d+)", validation_path.parent.name)
            if not match:
                continue
            payload = load(validation_path)
            old = payload.get("job", {})
            identity = ("job_id", "seed", "events", "geometry", "mode", "family", "source_tag")
            if all(old.get(key) == job.get(key) for key in identity):
                used.add(int(match.group(1)))
    return used


def run_attempt(
    job: dict[str, Any], attempt: int, contract: dict[str, Any], environment: dict[str, str], hard_deadline: datetime,
) -> dict[str, Any]:
    canonical = attempt_dir(job, attempt)
    partial = canonical.with_name(f".{canonical.name}.partial")
    if canonical.exists() or partial.exists() or failed_dir(job, attempt).exists():
        raise RuntimeError(f"recovery0006 attempt path already exists: {rel(canonical)}")
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.mkdir()
    name = str(job["job_id"])
    base = campaign.source_card(str(job["geometry"]), str(job["family"]))
    patched = partial / f"{name}.source"
    sim_prefix = partial / name
    isotope_prefix = partial / f"{name}.dat"
    log = partial / f"{name}.log"
    campaign.patch_source(
        base, patched, mode=str(job["mode"]), events=int(job["events"]), seed=int(job["seed"]),
        sim_prefix=sim_prefix, isotope_prefix=isotope_prefix,
    )
    command = [contract["static_gate"]["transport"]["cosima"], "-s", str(job["seed"]), str(patched)]
    started = time.monotonic()
    peak_rss = 0
    watchdog = "completed"
    last_activity = started
    previous_cpu = previous_growth = 0
    returncode = -999
    with log.open("x", encoding="utf-8", buffering=1) as handle:
        handle.write(json.dumps({
            "job": job, "attempt": attempt, "base_source": rel(base), "base_source_sha256": sha(base),
            "recovery_authority_sha256": sha(AUTHORITY), "declared_cap_bytes": job_cap(job),
        }, sort_keys=True) + "\n")
        handle.write(f"cosima_command={' '.join(command)}\n")
        handle.flush()
        proc = subprocess.Popen(command, cwd=campaign.ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        campaign._ACTIVE_PROCESS = proc
        while proc.poll() is None:
            time.sleep(campaign.POLL_SECONDS)
            now = time.monotonic()
            cpu, rss = campaign.process_group_metrics(proc.pid)
            peak_rss = max(peak_rss, rss)
            growth = directory_bytes(partial)
            if cpu > previous_cpu or growth > previous_growth:
                last_activity = now
            previous_cpu, previous_growth = cpu, growth
            reason: str | None = None
            if campaign._STOP_REQUESTED:
                reason = "controller_stop_requested"
            elif datetime.now(timezone.utc) >= hard_deadline:
                reason = "stage_hard_deadline"
            elif growth > job_cap(job):
                reason = "recovery0006_job_hard_cap_exceeded__stop_stage"
            elif shutil.disk_usage(campaign.RUN_ROOT).free < campaign.FILESYSTEM_RESERVE_BYTES:
                reason = "filesystem_20GiB_floor"
            elif campaign.mem_available_bytes() < campaign.HARD_LOW_MEMORY_BYTES:
                reason = "hard_low_memory_512MiB"
            elif now - last_activity > campaign.HANG_SECONDS:
                reason = "watchdog_no_cpu_or_growth_15m"
            if reason:
                watchdog = reason
                campaign.terminate_group(proc)
                break
        returncode = proc.wait()
        campaign._ACTIVE_PROCESS = None
        handle.write(
            f"watchdog_reason={watchdog}\npeak_process_group_rss_bytes={peak_rss}\n"
            f"returncode={returncode}\nwall_s={time.monotonic() - started:.6f}\n"
        )
    wall_s = time.monotonic() - started
    validation = campaign.validate_attempt(job, partial, returncode, peak_rss, wall_s, watchdog, contract)
    validation["declared_cap_bytes"] = job_cap(job)
    if validation["status"] == "PASS":
        os.replace(partial, canonical)
        validation["selected_attempt"] = attempt
        validation["attempt_dir"] = rel(canonical)
        campaign.atomic_write_once_json(receipt_path(job), validation)
        if not validate_replan_receipt(job, load(receipt_path(job))):
            raise RuntimeError(f"new receipt post-publication closure failed: {job['job_id']}")
        append_event(
            "attempt_PASS", job_id=job["job_id"], attempt=attempt, events=job["events"],
            wall_s=wall_s, peak_rss_bytes=peak_rss, artifact_bytes=sum(int(x["bytes"]) for x in validation["artifacts"].values()),
        )
        return validation
    failed = failed_dir(job, attempt)
    failed.parent.mkdir(parents=True, exist_ok=True)
    os.replace(partial, failed)
    campaign.atomic_write_once_json(failed / "validation.json", {
        **validation, "attempt_dir": rel(failed), "selected_attempt": None,
    })
    append_event(
        "attempt_FAIL", job_id=job["job_id"], attempt=attempt, watchdog=watchdog,
        errors=validation.get("errors", []), wall_s=wall_s, peak_rss_bytes=peak_rss,
    )
    return validation


def ensure_job(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_deadline: datetime,
    runtime_wall_budget_s: float | None = None,
) -> dict[str, Any]:
    path = receipt_path(job)
    if path.is_file():
        payload = load(path)
        if not validate_replan_receipt(job, payload):
            raise RuntimeError(f"immutable recovery0006 receipt failed closure: {job['job_id']}")
        return payload
    used = prior_exact_attempts(job)
    for attempt in range(1, campaign.MAX_ATTEMPTS + 1):
        if attempt in used:
            continue
        if campaign._STOP_REQUESTED or datetime.now(timezone.utc) >= hard_deadline:
            raise RuntimeError("stop/deadline before recovery0006 exact attempt")
        if datetime.now(timezone.utc) + timedelta(
            seconds=float(runtime_wall_budget_s if runtime_wall_budget_s is not None else job["planned_wall_budget_s"])
            + VALIDATION_PUBLICATION_MARGIN_S
        ) > hard_deadline:
            raise RuntimeError("insufficient hard-deadline budget before exact attempt/retry")
        free = shutil.disk_usage(campaign.RUN_ROOT).free
        used_bytes = campaign.campaign_bytes()
        if free < campaign.FILESYSTEM_RESERVE_BYTES + job_cap(job):
            raise RuntimeError("insufficient filesystem reserve before exact attempt/retry")
        stage_reserve = 20_000_000_000 if job["stage"] == "stage10_seven_family" else campaign.CAMPAIGN_EMERGENCY_BYTES
        if used_bytes + job_cap(job) > int(contract["disk"]["effective_campaign_cap_bytes"]) - stage_reserve:
            raise RuntimeError("insufficient campaign cap before exact attempt/retry")
        errors = recovery1.input_hash_gate(job, contract)
        if errors:
            raise RuntimeError("pre-attempt frozen input hash gate: " + "; ".join(errors))
        result = run_attempt(job, attempt, contract, environment, hard_deadline)
        if result["status"] == "PASS":
            return result
        if result.get("watchdog_reason") == "recovery0006_job_hard_cap_exceeded__stop_stage":
            raise RuntimeError("job hard cap exceeded; evidence preserved and stage must stop")
    raise RuntimeError(f"{job['job_id']} exhausted two total exact attempts")


def worker_entry(
    job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_end_iso: str,
    runtime_wall_budget_s: float | None, connection: Any,
) -> None:
    configure_validator()
    campaign._STOP_REQUESTED = False
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, campaign._signal_handler)
    try:
        result = ensure_job(
            job, contract, environment, datetime.fromisoformat(hard_end_iso),
            runtime_wall_budget_s=runtime_wall_budget_s,
        )
        connection.send({
            "status": "PASS", "job_id": job["job_id"], "events": job["events"],
            "receipt": rel(receipt_path(job)), "receipt_sha256": sha(receipt_path(job)),
            "wall_s": result["wall_s"],
        })
    except BaseException as exc:
        connection.send({"status": "FAIL", "job_id": job["job_id"], "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
        connection.close()


def launch_worker(
    context: Any, job: dict[str, Any], contract: dict[str, Any], environment: dict[str, str], hard_end: datetime,
    *, runtime_peak_rss_budget_bytes: int | None = None,
    runtime_wall_budget_s: float | None = None,
) -> Worker:
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=worker_entry,
        args=(job, contract, environment, hard_end.isoformat(), runtime_wall_budget_s, child),
        name=f"m05-r6-{job['job_id']}",
    )
    process.start()
    child.close()
    now = time.monotonic()
    scheduler_job = dict(job)
    if runtime_peak_rss_budget_bytes is not None:
        scheduler_job["_runtime_peak_rss_budget_bytes"] = int(runtime_peak_rss_budget_bytes)
    if runtime_wall_budget_s is not None:
        scheduler_job["_runtime_wall_budget_s"] = float(runtime_wall_budget_s)
    worker = Worker(scheduler_job, process, parent, datetime.now(timezone.utc).isoformat(), now)
    _ACTIVE_WORKERS[process.pid] = worker
    return worker


def reap(active: list[Worker], failures: list[str]) -> list[Worker]:
    keep: list[Worker] = []
    for worker in active:
        if worker.process.is_alive():
            keep.append(worker)
            continue
        worker.process.join(timeout=1)
        if worker.connection.poll():
            try:
                message = worker.connection.recv()
            except EOFError:
                message = {"status": "FAIL", "job_id": worker.job["job_id"], "error": "pipe EOF"}
        else:
            message = {"status": "FAIL", "job_id": worker.job["job_id"], "error": f"exit {worker.process.exitcode} without result"}
        worker.connection.close()
        _ACTIVE_WORKERS.pop(worker.process.pid, None)
        frozen_job = {key: value for key, value in worker.job.items() if not key.startswith("_runtime_")}
        if message.get("status") == "PASS" and receipt_path(frozen_job).is_file() and validate_replan_receipt(frozen_job, load(receipt_path(frozen_job))):
            append_event("worker_reaped_PASS", job_id=worker.job["job_id"], worker_pid=worker.process.pid)
        else:
            failures.append(f"{worker.job['job_id']}: {message.get('error', 'receipt closure failed')}")
            append_event("worker_reaped_FAIL", job_id=worker.job["job_id"], worker_pid=worker.process.pid, detail=message)
    return keep


def class_key(job: dict[str, Any]) -> str:
    kind = "bundle" if job.get("replan_kind") == "fresh_balanced_bundle" else "old_exact_mate"
    return f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}/{kind}"


def rss_evidence(original: list[dict[str, Any]], pending: list[dict[str, Any]]) -> dict[str, Any]:
    old_classes: dict[str, list[int]] = defaultdict(list)
    for metric in validated_original_metrics(original):
        job = metric["job"]
        key = f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}"
        old_classes[key].append(int(metric["peak_rss_bytes"]))
    current: dict[str, list[int]] = defaultdict(list)
    for job in pending:
        path = receipt_path(job)
        if path.is_file():
            payload = load(path)
            if not validate_replan_receipt(job, payload):
                raise RuntimeError(f"RSS evidence receipt closure failed: {job['job_id']}")
            current[class_key(job)].append(int(payload["peak_process_group_rss_bytes"]))
    return {
        "old_exact_classes": {key: {"n": len(values), "max_bytes": max(values)} for key, values in sorted(old_classes.items())},
        "recovery0006_exact_classes": {key: {"n": len(values), "max_bytes": max(values)} for key, values in sorted(current.items())},
    }


def exact_class_count(job: dict[str, Any], evidence: dict[str, Any]) -> int:
    if job.get("replan_kind") == "fresh_balanced_bundle":
        return int(evidence["recovery0006_exact_classes"].get(class_key(job), {}).get("n", 0))
    old_key = f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}"
    return int(evidence["old_exact_classes"].get(old_key, {}).get("n", 0))


def class_upper(job: dict[str, Any], evidence: dict[str, Any], live_peer: int = 0) -> int:
    current = int(evidence["recovery0006_exact_classes"].get(class_key(job), {}).get("max_bytes", 0))
    old_key = f"{job['stage']}/{job['mode']}/{job['geometry']}/{job['family']}"
    historical = int(evidence["old_exact_classes"].get(old_key, {}).get("max_bytes", 0))
    if not historical and job["stage"] == "stage20_proton":
        smoke_key = f"stage00_mergeable_smoke/{job['mode']}/{job['geometry']}/{job['family']}"
        historical = int(evidence["old_exact_classes"].get(smoke_key, {}).get("max_bytes", 0))
    planned = int(job.get("_runtime_peak_rss_budget_bytes", job.get("planned_peak_rss_budget_bytes", 0)))
    observed_tail = max(current, historical, UNSEEN_CLASS_MIN_BYTES)
    return max(
        planned,
        math.ceil(observed_tail * CLASS_FACTOR) + CLASS_PAD_BYTES,
        live_peer + ACTIVE_PAD_BYTES,
        512 * 1024**2,
    )


def process_rows() -> dict[int, tuple[int, int]]:
    return recovery5._proc_rows()


def descendant_rss(pid: int, rows: dict[int, tuple[int, int]]) -> int:
    return recovery5.descendant_rss_bytes(pid, rows)


def sample_rss(active: list[Worker], health: Health, now: float) -> tuple[dict[int, int], dict[int, deque[tuple[float, int]]]]:
    rows = process_rows()
    live = {worker.process.pid: descendant_rss(worker.process.pid, rows) for worker in active}
    if health.rss_samples is None:
        health.rss_samples = {}
    for pid in list(health.rss_samples):
        if pid not in live:
            del health.rss_samples[pid]
    for pid, rss in live.items():
        history = health.rss_samples.setdefault(pid, deque())
        if not history or now - history[-1][0] >= ACTIVE_SAMPLE_INTERVAL_S:
            history.append((now, rss))
        while history and now - history[0][0] > ACTIVE_WINDOW_S:
            history.popleft()
    return live, health.rss_samples


def active_growth(current: int, samples: Iterable[tuple[float, int]], upper: int, age: float) -> dict[str, Any]:
    rows = sorted((float(at), max(0, int(rss))) for at, rss in samples)
    if rows:
        newest = rows[-1][0]
        rows = [row for row in rows if newest - row[0] <= ACTIVE_WINDOW_S]
    span = rows[-1][0] - rows[0][0] if len(rows) >= 2 else 0.0
    slope_rows = rows
    if rows:
        newest = rows[-1][0]
        slope_rows = [row for row in rows if newest - row[0] <= ACTIVE_SLOPE_WINDOW_S]
    slopes = [
        (slope_rows[j][1] - slope_rows[i][1]) / (slope_rows[j][0] - slope_rows[i][0])
        for i in range(len(slope_rows)) for j in range(i + 1, len(slope_rows))
        if slope_rows[j][0] > slope_rows[i][0] and slope_rows[j][1] > slope_rows[i][1]
    ]
    slope = max(slopes, default=0.0)
    peak_gap = max(0, max((rss for _at, rss in rows), default=current) - current)
    positive_trajectory = math.ceil(slope * ACTIVE_HORIZON_S) + ACTIVE_PAD_BYTES
    reserve = max(peak_gap, max(0, upper - current)) + positive_trajectory
    mature = age >= ACTIVE_MATURITY_S and span >= ACTIVE_TRAJECTORY_S
    return {
        "reserve_bytes": reserve, "current_rss_bytes": current, "class_upper_bytes": upper,
        "positive_slope_bytes_per_s": slope, "sample_span_s": span, "worker_age_s": age,
        "mature": mature, "planned_remaining_retained_for_entire_lifetime": True,
    }


def memory_projection(
    active: list[Worker], candidate: dict[str, Any], evidence: dict[str, Any], available: int,
    live: dict[int, int], histories: dict[int, Iterable[tuple[float, int]]], now: float,
) -> dict[str, Any]:
    active_reserve = 0
    rows: list[dict[str, Any]] = []
    for worker in active:
        peer = int(live.get(worker.process.pid, 0))
        upper = class_upper(worker.job, evidence, peer)
        forecast = active_growth(peer, histories.get(worker.process.pid, ()), upper, max(0.0, now - worker.launched_monotonic))
        active_reserve += int(forecast["reserve_bytes"])
        rows.append({"job_id": worker.job["job_id"], "trajectory": forecast})
    peer_live = max((int(live.get(w.process.pid, 0)) for w in active if class_key(w.job) == class_key(candidate)), default=0)
    candidate_upper = max(
        int(candidate.get("planned_peak_rss_budget_bytes", 0)),
        class_upper(candidate, evidence, peer_live),
        peer_live + ACTIVE_PAD_BYTES,
    )
    projected = available - active_reserve - candidate_upper
    return {
        "status": "PASS" if projected >= SOFT_FLOOR_BYTES else "PAUSE",
        "mem_available_bytes": available, "active_unrealised_growth_reserve_bytes": active_reserve,
        "candidate_class_upper_bytes": candidate_upper, "projected_mem_available_bytes": projected,
        "soft_floor_bytes": SOFT_FLOOR_BYTES, "active": rows,
    }


def global_active_projection(
    active: list[Worker], evidence: dict[str, Any], available: int,
    live: dict[int, int], histories: dict[int, Iterable[tuple[float, int]]], now: float,
) -> dict[str, Any]:
    reserve = 0
    for worker in active:
        current = int(live.get(worker.process.pid, 0))
        upper = class_upper(worker.job, evidence, current)
        reserve += int(active_growth(
            current, histories.get(worker.process.pid, ()), upper,
            max(0.0, now - worker.launched_monotonic),
        )["reserve_bytes"])
    return {
        "projected_mem_available_bytes": available - reserve,
        "mem_available_bytes": available,
        "active_unrealised_growth_reserve_bytes": reserve,
    }


def calibration_collision(candidate: dict[str, Any], active: list[Worker], evidence: dict[str, Any]) -> str | None:
    count = exact_class_count(candidate, evidence)
    if count < 2 and any(class_key(worker.job) == class_key(candidate) for worker in active):
        return "fewer_than_two_exact_class_receipts_same_class_active"
    return None


def attempt_bytes_for_active(worker: Worker) -> int:
    for attempt in range(1, campaign.MAX_ATTEMPTS + 1):
        partial = attempt_dir(worker.job, attempt).with_name(f".attempt{attempt:02d}.partial")
        if partial.is_dir():
            return directory_bytes(partial)
    return 0


def disk_projection(contract: dict[str, Any], stage: str, active: list[Worker], candidate: dict[str, Any]) -> dict[str, Any]:
    used = campaign.campaign_bytes()
    free = shutil.disk_usage(campaign.RUN_ROOT).free
    active_remaining = 0
    for worker in active:
        frozen = {key: value for key, value in worker.job.items() if not key.startswith("_runtime_")}
        already_used = len(prior_exact_attempts(frozen))
        future_retry_caps = max(0, campaign.MAX_ATTEMPTS - already_used - 1) * job_cap(frozen)
        active_remaining += max(0, job_cap(frozen) - attempt_bytes_for_active(worker)) + future_retry_caps
    candidate_attempts_remaining = max(0, campaign.MAX_ATTEMPTS - len(prior_exact_attempts(candidate)))
    candidate_cap = job_cap(candidate) * candidate_attempts_remaining
    campaign_reserve = 20_000_000_000 if stage == "stage10_seven_family" else campaign.CAMPAIGN_EMERGENCY_BYTES
    stage_limit = int(contract["disk"]["effective_campaign_cap_bytes"]) - campaign_reserve
    errors: list[str] = []
    if used + active_remaining + candidate_cap > stage_limit:
        errors.append("campaign_cap_after_unrealised_active_plus_candidate")
    if free < campaign.FILESYSTEM_RESERVE_BYTES + active_remaining + candidate_cap:
        errors.append("filesystem_reserve_after_unrealised_active_plus_candidate")
    return {
        "status": "PASS" if not errors else "PAUSE", "campaign_bytes": used, "free_bytes": free,
        "active_unrealised_cap_bytes": active_remaining, "candidate_cap_bytes": candidate_cap,
        "campaign_reserve_bytes": campaign_reserve, "stage_limit_bytes": stage_limit, "errors": errors,
    }


def health_allows(health: Health, projection: dict[str, Any], swap: dict[str, Any], now: float) -> tuple[bool, str]:
    projected = int(projection["projected_mem_available_bytes"])
    if swap.get("growing") or projected < SOFT_FLOOR_BYTES:
        health.paused = True
        health.resume_since = None
        return False, "swap_growth" if swap.get("growing") else "projected_below_1.5GiB"
    if not health.paused:
        return True, "admit"
    if projected <= RESUME_FLOOR_BYTES:
        health.resume_since = None
        return False, "resume_headroom_not_reached"
    if health.resume_since is None:
        health.resume_since = now
        return False, "resume_dwell"
    if now - health.resume_since < RESUME_DWELL_S:
        return False, "resume_dwell"
    health.paused = False
    health.resume_since = None
    return True, "resume_after_dwell"


def stage20_calibration_path(mode: str) -> Path:
    return RUN_NS / f"stage20_{mode}_2048_calibration.json"


def stage20_canary_jobs(mode: str, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [job for job in pending if job["stage"] == "stage20_proton" and job["mode"] == mode and int(job["events"]) in (512, 1024)]
    order = {512: 0, 1024: 1}
    return sorted(rows, key=lambda job: (order[int(job["events"])], campaign.GEOMETRY_ORDER.index(str(job["geometry"]))))


def load_or_publish_stage20_calibration(
    mode: str, pending: list[dict[str, Any]], authority: dict[str, Any], registry: dict[str, Any], *, publish: bool,
) -> dict[str, Any] | None:
    path = stage20_calibration_path(mode)
    canaries = stage20_canary_jobs(mode, pending)
    if len(canaries) != 4:
        raise RuntimeError(f"stage20 {mode} canary mapping is not paired 512+1024")
    if not all(receipt_path(job).is_file() for job in canaries):
        return None
    receipt_rows: list[dict[str, Any]] = []
    budgets: dict[str, int] = {}
    wall_budgets: dict[str, float] = {}
    for geometry in campaign.GEOMETRY_ORDER:
        geometry_jobs = sorted((j for j in canaries if j["geometry"] == geometry), key=lambda j: int(j["events"]))
        observed: list[tuple[int, int, float]] = []
        for job in geometry_jobs:
            receipt = load(receipt_path(job))
            if not validate_replan_receipt(job, receipt):
                raise RuntimeError(f"stage20 canary receipt closure failed: {job['job_id']}")
            observed.append((int(job["events"]), int(receipt["peak_process_group_rss_bytes"]), float(receipt["wall_s"])))
            receipt_rows.append({
                "job_id": job["job_id"], "events": job["events"], "seed": job["seed"],
                "path": rel(receipt_path(job)), "sha256": sha(receipt_path(job)),
                "artifacts": receipt["artifacts"], "strict_framing": receipt["sim"]["strict_framing"],
                "TT_s": receipt["isotope_dat"]["TT_s"], "RP_count": receipt["isotope_dat"]["RP_record_count"],
                "peak_rss_bytes": receipt["peak_process_group_rss_bytes"],
                "wall_s": receipt["wall_s"],
            })
        (e1, r1, w1), (e2, r2, w2) = observed
        slope = max(0.0, (r2 - r1) / (e2 - e1))
        fitted = r2 + slope * (2048 - e2)
        budget = math.ceil(max(1024**3, 1.25 * max(r1, r2, fitted) + 256 * 1024**2, max(int(j["planned_peak_rss_budget_bytes"]) for j in geometry_jobs if int(j["events"]) == 1024)) / (64 * 1024**2)) * 64 * 1024**2
        budgets[geometry] = int(budget)
        wall_slope = max(0.0, (w2 - w1) / (e2 - e1))
        fitted_wall = w2 + wall_slope * (2048 - e2)
        wall_budgets[geometry] = max(
            max(float(j["planned_wall_budget_s"]) for j in geometry_jobs if int(j["events"]) == 1024),
            1.25 * max(w1, w2, fitted_wall) + 60.0,
        )
    payload = {
        "schema_version": 1,
        "status": "PASS__STAGE20_PAIRED_512_1024_CANARIES__2048_BUDGET_FROZEN",
        "recovery_id": RECOVERY_ID, "mode": mode,
        "authority_sha256": sha(AUTHORITY), "effective_pending_plan_sha256": authority["effective_pending_plan_sha256"],
        "seed_registry_sha256": sha(REPLAN_SEED_REGISTRY), "global_contract_sha256": EXPECTED_GLOBAL_SHA256,
        "drain_completion_sha256": EXPECTED_DRAIN_COMPLETION_SHA256,
        "canary_receipts": receipt_rows,
        "formula": "ceil64MiB(max(1GiB,1.25*max(canaryMaxRSS,linear_fitted_2048)+256MiB,1024_prebudget))",
        "wall_formula": "max(1024_prebudget,1.25*max(canaryWall,linear_fitted_2048_wall)+60s)",
        "planned_peak_rss_budget_2048_bytes": budgets,
        "planned_wall_budget_2048_s": wall_budgets,
        "mem_available_bytes_before_publication": campaign.mem_available_bytes(),
        "runtime_floor_bytes": SOFT_FLOOR_BYTES,
    }
    if max(budgets.values()) > PLANNED_RSS_BUDGET_CEILING_BYTES:
        raise RuntimeError(f"stage20 {mode} calibrated 2048 budget exceeds frozen 6.5GiB model ceiling")
    if path.is_file():
        existing = load(path)
        for key in ("authority_sha256", "effective_pending_plan_sha256", "seed_registry_sha256", "global_contract_sha256", "drain_completion_sha256", "canary_receipts", "formula", "wall_formula", "planned_peak_rss_budget_2048_bytes", "planned_wall_budget_2048_s"):
            if existing.get(key) != payload.get(key):
                raise RuntimeError(f"stage20 {mode} calibration sidecar drift: {key}")
        return existing
    if not publish:
        return payload
    campaign.atomic_write_once_json(path, payload)
    return load(path)


def runtime_job_budget(job: dict[str, Any], pending: list[dict[str, Any]], authority: dict[str, Any], registry: dict[str, Any]) -> int:
    if not job.get("requires_stage20_canary_calibration"):
        return int(job["planned_peak_rss_budget_bytes"])
    calibration = load_or_publish_stage20_calibration(str(job["mode"]), pending, authority, registry, publish=True)
    if calibration is None:
        raise RuntimeError("stage20 2048 job is blocked until paired 512/1024 canaries PASS")
    return int(calibration["planned_peak_rss_budget_2048_bytes"][str(job["geometry"])])


def runtime_job_wall_budget(job: dict[str, Any], pending: list[dict[str, Any]], authority: dict[str, Any], registry: dict[str, Any]) -> float:
    if not job.get("requires_stage20_canary_calibration"):
        return float(job["planned_wall_budget_s"])
    calibration = load_or_publish_stage20_calibration(str(job["mode"]), pending, authority, registry, publish=True)
    if calibration is None:
        raise RuntimeError("stage20 runtime wall budget blocked until canary sidecar")
    return float(calibration["planned_wall_budget_2048_s"][str(job["geometry"])])


def stage20_ladder_block(job: dict[str, Any], pending: list[dict[str, Any]]) -> str | None:
    if job["stage"] != "stage20_proton":
        return None
    mode = str(job["mode"])
    canaries = stage20_canary_jobs(mode, pending)
    pass512 = all(receipt_path(row).is_file() and validate_replan_receipt(row, load(receipt_path(row))) for row in canaries if int(row["events"]) == 512)
    pass1024 = all(receipt_path(row).is_file() and validate_replan_receipt(row, load(receipt_path(row))) for row in canaries if int(row["events"]) == 1024)
    return stage20_ladder_decision(int(job["events"]), pass512=pass512, pass1024=pass1024)


def stage20_ladder_decision(events: int, *, pass512: bool, pass1024: bool) -> str | None:
    if events == 1024 and not pass512:
        return "stage20_mode_ladder_requires_both_512_geometry_receipts"
    if events > 1024 and not (pass512 and pass1024):
        return "stage20_mode_ladder_requires_512_pair_then_1024_pair"
    return None


def ordered_stage_jobs(stage: str, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [job for job in pending if job["stage"] == stage]
    if stage == "stage20_proton":
        event_order = {512: 0, 1024: 1, 2048: 2, 1105: 3}
        return sorted(rows, key=lambda job: (
            campaign.MODES.index(str(job["mode"])), event_order.get(int(job["events"]), 9),
            campaign.GEOMETRY_ORDER.index(str(job["geometry"])), int(job["shard_ordinal"]),
        ))
    # Round-robin geometry/mode/family so one heavy class cannot monopolize
    # the queue; admission remains resource- and calibration-gated.
    return sorted(rows, key=lambda job: (
        int(job["shard_ordinal"]), str(job["family"]), campaign.MODES.index(str(job["mode"])),
        campaign.GEOMETRY_ORDER.index(str(job["geometry"])),
    ))


def run_stage(
    stage: str, pending_plan: list[dict[str, Any]], original: list[dict[str, Any]],
    contract: dict[str, Any], environment: dict[str, str], authority: dict[str, Any], registry: dict[str, Any],
) -> str | None:
    timing = next(row for row in contract["wall_clock"]["stages"] if row["id"] == stage)
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    stop_launch = t0 + timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + timedelta(seconds=int(timing["hard_end_s"]))
    pending = [job for job in ordered_stage_jobs(stage, pending_plan) if not receipt_path(job).is_file()]
    active: list[Worker] = []
    failures: list[str] = []
    context = mp.get_context("fork")
    health = Health()
    evidence = rss_evidence(original, pending_plan)
    swap_samples: deque[tuple[float, int]] = deque()
    last_launch = -math.inf
    last_evidence = last_state = last_pause = 0.0
    stop_reason: str | None = None
    append_event("stage_start", stage=stage, pending_jobs=len(pending), stop_launch=stop_launch.isoformat(), hard_end=hard_end.isoformat())
    while pending or active:
        now_mono = time.monotonic()
        active = reap(active, failures)
        if failures and stop_reason is None:
            stop_reason = "worker failure: " + failures[0]
        if now_mono - last_evidence >= EVIDENCE_REFRESH_S:
            evidence = rss_evidence(original, pending_plan)
            last_evidence = now_mono
        live, histories = sample_rss(active, health, now_mono)
        swap_samples.append((now_mono, recovery5.read_pswpout_pages()))
        while swap_samples and now_mono - swap_samples[0][0] > recovery5.SWAP_WINDOW_S + 5:
            swap_samples.popleft()
        swap = recovery5.swap_growth(swap_samples)
        now = datetime.now(timezone.utc)
        global_projection = global_active_projection(
            active, evidence, campaign.mem_available_bytes(), live, histories, now_mono
        )
        global_healthy, global_health_decision = health_allows(
            health, global_projection, swap, now_mono
        )
        launch_allowed = (
            not _COORDINATOR_STOP and stop_reason is None and global_healthy
            and pending and len(active) < MAX_WORKERS
            and now < stop_launch and now_mono - last_launch >= LAUNCH_STAGGER_S
        )
        if launch_allowed:
            selected: tuple[int, dict[str, Any], dict[str, Any], int, float] | None = None
            observations: list[dict[str, Any]] = []
            for index, candidate in enumerate(pending[:16]):
                collision = calibration_collision(candidate, active, evidence)
                ladder_block = stage20_ladder_block(candidate, pending_plan)
                canary_block = False
                if candidate.get("requires_stage20_canary_calibration"):
                    canary_block = ladder_block is not None
                    calibration = None if canary_block else load_or_publish_stage20_calibration(str(candidate["mode"]), pending_plan, authority, registry, publish=True)
                    canary_block = canary_block or calibration is None
                runtime_budget = (
                    int(candidate["planned_peak_rss_budget_bytes"])
                    if canary_block else runtime_job_budget(candidate, pending_plan, authority, registry)
                )
                runtime_wall_budget = (
                    float(candidate["planned_wall_budget_s"])
                    if canary_block else runtime_job_wall_budget(candidate, pending_plan, authority, registry)
                )
                candidate_runtime = {**candidate, "planned_peak_rss_budget_bytes": runtime_budget}
                projection = memory_projection(active, candidate_runtime, evidence, campaign.mem_available_bytes(), live, histories, now_mono)
                disk = disk_projection(contract, stage, active, candidate)
                deadline_ok = (
                    now + timedelta(seconds=runtime_wall_budget + VALIDATION_PUBLICATION_MARGIN_S)
                    <= hard_end
                )
                observations.append({
                    "job_id": candidate["job_id"], "collision": collision, "ladder_block": ladder_block,
                    "canary_block": canary_block, "deadline_allows_completion": deadline_ok,
                    "runtime_wall_budget_s": runtime_wall_budget, "hard_end": hard_end.isoformat(),
                    "runtime_budget_bytes": runtime_budget, "projection": projection, "disk": disk,
                })
                candidate_fits = int(projection["projected_mem_available_bytes"]) >= SOFT_FLOOR_BYTES
                if not collision and not ladder_block and not canary_block and deadline_ok and candidate_fits and disk["status"] == "PASS":
                    selected = index, projection, disk, runtime_budget, runtime_wall_budget
                    break
            if selected is not None:
                index, projection, disk, runtime_budget, runtime_wall_budget = selected
                candidate = pending.pop(index)
                worker = launch_worker(
                    context, candidate, contract, environment, hard_end,
                    runtime_peak_rss_budget_bytes=runtime_budget,
                    runtime_wall_budget_s=runtime_wall_budget,
                )
                active.append(worker)
                last_launch = now_mono
                append_event(
                    "worker_launched", stage=stage, job_id=candidate["job_id"], worker_pid=worker.process.pid,
                    active_workers=len(active), target_workers=NORMAL_TARGET_WORKERS, projection=projection, disk=disk,
                    runtime_wall_budget_s=runtime_wall_budget,
                )
            elif now_mono - last_pause >= 30:
                append_event(
                    "launch_PAUSE", stage=stage, active_workers=len(active), mem_available_bytes=campaign.mem_available_bytes(),
                    swap=swap, global_projection=global_projection,
                    global_health_decision=global_health_decision, observations=observations,
                )
                last_pause = now_mono
        if stop_reason is not None and not active:
            break
        if _COORDINATOR_STOP and not active:
            stop_reason = stop_reason or "coordinator stop requested"
            break
        if now >= stop_launch and not active:
            stop_reason = stop_reason or "original stage stop-launch boundary reached"
            break
        if datetime.now(timezone.utc) >= hard_end and active:
            for worker in active:
                if worker.process.is_alive():
                    os.kill(worker.process.pid, signal.SIGTERM)
        if now_mono - last_state >= 30:
            completed = sum(receipt_path(job).is_file() for job in pending_plan)
            update_state(contract, status=f"RUNNING__RECOVERY0006__ACTIVE_{len(active)}", stage=stage, completed=completed, error=stop_reason)
            append_event(
                "scheduler_checkpoint", stage=stage, active_workers=len(active), pending_jobs=len(pending),
                mem_available_bytes=campaign.mem_available_bytes(), active_rss_bytes=sum(live.values()), swap=swap,
            )
            last_state = now_mono
        time.sleep(POLL_S)
    while active:
        active = reap(active, failures)
        if active:
            time.sleep(POLL_S)
    if failures and stop_reason is None:
        stop_reason = "worker failure: " + failures[0]
    append_event("stage_end", stage=stage, stop_reason=stop_reason, completed=sum(receipt_path(j).is_file() for j in pending_plan if j["stage"] == stage))
    return stop_reason


def selected_receipts(
    original: list[dict[str, Any]], manifest: list[dict[str, Any]], pending: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(job["job_id"]): job for job in original}
    selected: list[dict[str, Any]] = []
    for row in manifest:
        job = by_id[str(row["job_id"])]
        path = campaign.ROOT / str(row["path"])
        receipt = validate_original_receipt(job, path)
        selected.append({"kind": "inherited_original", "job": job, "receipt": receipt, "path": rel(path), "sha256": sha(path)})
    for job in pending:
        path = receipt_path(job)
        if not path.is_file():
            continue
        receipt = load(path)
        if not validate_replan_receipt(job, receipt):
            raise RuntimeError(f"final recovery0006 receipt closure failed: {job['job_id']}")
        selected.append({"kind": str(job.get("replan_kind", "retained_old_exact_mate")), "job": job, "receipt": receipt, "path": rel(path), "sha256": sha(path)})
    return selected


def effective_cell_closure(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cells: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in selected:
        job, receipt = row["job"], row["receipt"]
        key = (str(job["stage"]), str(job["geometry"]), str(job["mode"]), str(job["family"]))
        cell = cells.setdefault(key, {
            "stage": key[0], "geometry": key[1], "mode": key[2], "family": key[3],
            "events": 0, "receipts": 0, "TT_s": 0.0, "RP_count": 0,
        })
        cell["events"] += int(job["events"])
        cell["receipts"] += 1
        cell["TT_s"] = math.fsum((float(cell["TT_s"]), float(receipt["isotope_dat"]["TT_s"])))
        cell["RP_count"] += int(receipt["isotope_dat"]["RP_record_count"])
    return [cells[key] for key in sorted(cells)]


def publish_final(
    original: list[dict[str, Any]], manifest: list[dict[str, Any]], pending: list[dict[str, Any]],
    authority: dict[str, Any], fatal: str | None,
) -> None:
    if _ACTIVE_WORKERS or list(RUN_NS.glob("attempts/**/.attempt*.partial")):
        raise RuntimeError("final publication requires quiescence and zero partial attempts")
    # Scheduler validation is cached for performance, but final authority
    # deliberately re-hashes and re-drains every selected recovery0006 SIM.
    _VALIDATED_REPLAN_RECEIPTS.clear()
    selected = selected_receipts(original, manifest, pending)
    missing = [job["job_id"] for job in pending if not receipt_path(job).is_file()]
    selected_rows = [{
        "kind": row["kind"], "job_id": row["job"]["job_id"], "events": row["job"]["events"],
        "path": row["path"], "sha256": row["sha256"], "job_sha256": jsha(row["job"]),
    } for row in selected]
    complete = (
        fatal is None and not missing and len(selected) == EXPECTED_FINAL_RECEIPTS
        and sum(int(row["job"]["events"]) for row in selected) == EXPECTED_TOTAL_EVENTS
    )
    status = "PASS__REPLANNED_MAINLINE_EVENT_TARGET_COMPLETE" if complete else "FAIL__RECOVERY0006_INCOMPLETE_OR_RESOURCE_AUTHORITY_ERROR"
    cells = effective_cell_closure(selected)
    original_cells: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for job in original:
        original_cells[(str(job["stage"]), str(job["geometry"]), str(job["mode"]), str(job["family"]))] += int(job["events"])
    cell_errors = [cell for cell in cells if int(cell["events"]) != original_cells[(cell["stage"], cell["geometry"], cell["mode"], cell["family"])]]
    if complete and cell_errors:
        raise RuntimeError("per-cell event closure differs despite complete receipt target")
    calibrations = {
        mode: {
            "path": rel(stage20_calibration_path(mode)) if stage20_calibration_path(mode).is_file() else None,
            "sha256": sha(stage20_calibration_path(mode)) if stage20_calibration_path(mode).is_file() else None,
        }
        for mode in campaign.MODES
    }
    validation = {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "errors": [fatal] if fatal else [], "missing_jobs": missing,
        "global_contract_sha256": EXPECTED_GLOBAL_SHA256, "authority_sha256": sha(AUTHORITY),
        "cutover_receipt_sha256": sha(CUTOVER_RECEIPT), "seed_registry_sha256": sha(REPLAN_SEED_REGISTRY),
        "effective_pending_plan_sha256": authority["effective_pending_plan_sha256"],
        "selected_receipts": selected_rows, "selected_receipts_closure_sha256": jsha(selected_rows),
        "validated_receipts": len(selected), "validated_events": sum(int(row["job"]["events"]) for row in selected),
        "cells": cells, "cell_errors": cell_errors, "stage20_calibrations": calibrations,
    }
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    ledger = {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "validation": rel(FINAL_VALIDATION), "validation_sha256": sha(FINAL_VALIDATION),
        "selected_receipts": selected_rows, "selected_receipts_closure_sha256": jsha(selected_rows),
        "authority_sha256": sha(AUTHORITY), "seed_registry_sha256": sha(REPLAN_SEED_REGISTRY),
        "errors": validation["errors"], "missing_jobs": missing,
    }
    campaign.atomic_write_once_json(FINAL_LEDGER, ledger)
    campaign.atomic_write_once_json(FINAL_UMBRELLA, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status,
        "global_contract": rel(campaign.GLOBAL_CONTRACT), "global_contract_sha256": EXPECTED_GLOBAL_SHA256,
        "authority": rel(AUTHORITY), "authority_sha256": sha(AUTHORITY),
        "cutover_receipt": rel(CUTOVER_RECEIPT), "cutover_receipt_sha256": sha(CUTOVER_RECEIPT),
        "seed_registry": rel(REPLAN_SEED_REGISTRY), "seed_registry_sha256": sha(REPLAN_SEED_REGISTRY),
        "final_validation": rel(FINAL_VALIDATION), "final_validation_sha256": sha(FINAL_VALIDATION),
        "final_ledger": rel(FINAL_LEDGER), "final_ledger_sha256": sha(FINAL_LEDGER),
        "stage20_calibrations": calibrations, "errors": validation["errors"],
    })


def coordinator_signal(_signum: int, _frame: Any) -> None:
    global _COORDINATOR_STOP
    _COORDINATOR_STOP = True
    for worker in list(_ACTIVE_WORKERS.values()):
        if worker.process.is_alive():
            try:
                os.kill(worker.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def quiesce_workers() -> None:
    for worker in list(_ACTIVE_WORKERS.values()):
        if worker.process.is_alive():
            try:
                os.kill(worker.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            worker.process.join(timeout=30)
        if worker.process.is_alive():
            try:
                os.kill(worker.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            worker.process.join(timeout=10)
        if worker.process.is_alive():
            raise RuntimeError(f"worker remained alive after SIGKILL: {worker.process.pid}")
        _ACTIVE_WORKERS.pop(worker.process.pid, None)
    matching: list[int] = []
    run_text = str(RUN_NS.resolve())
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            cmd = proc.read_bytes().replace(b"\0", b" ").decode(errors="replace")
            if run_text in cmd and ("cosima" in cmd or "m05-r6-" in cmd):
                matching.append(int(proc.parent.name))
        except (OSError, ValueError):
            continue
    if matching:
        raise RuntimeError(f"recovery0006 final quiescence found processes: {matching}")


def run_campaign(
    original: list[dict[str, Any]], manifest: list[dict[str, Any]], pending: list[dict[str, Any]],
    contract: dict[str, Any], environment: dict[str, str], authority: dict[str, Any], registry: dict[str, Any],
) -> int:
    fatal: str | None = None
    try:
        for stage in ("stage10_seven_family", "stage20_proton"):
            reason = run_stage(stage, pending, original, contract, environment, authority, registry)
            if reason:
                raise RuntimeError(f"{stage}: {reason}")
    except Exception as exc:
        fatal = str(exc)
    finally:
        try:
            quiesce_workers()
        except Exception as exc:
            fatal = (fatal + "; " if fatal else "") + f"quiescence failure: {exc}"
        publish_final(original, manifest, pending, authority, fatal)
        update_state(
            contract, status="FINALIZED_RECOVERY0006" if fatal is None else "FINALIZED_RECOVERY0006_WITH_ERROR",
            stage="final", completed=sum(receipt_path(job).is_file() for job in pending), error=fatal,
        )
    if fatal:
        raise SystemExit(fatal)
    return 0


def self_test() -> dict[str, Any]:
    assert balanced_sizes(13) == [5, 4, 4]
    assert balanced_sizes(6) == [6]
    assert balanced_sizes(7) == [4, 3]
    gib = 1024**3
    ramp = active_growth(2 * gib, [(0, gib), (15, int(1.5 * gib)), (30, 2 * gib)], 5 * gib, 120)
    assert ramp["reserve_bytes"] >= 3 * gib
    stable = active_growth(2 * gib, [(0, 2 * gib), (30, 2 * gib)], 5 * gib, 120)
    assert stable["reserve_bytes"] > 3 * gib
    health = Health()
    assert not health_allows(health, {"projected_mem_available_bytes": SOFT_FLOOR_BYTES - 1}, {"growing": False}, 0)[0]
    assert not health_allows(health, {"projected_mem_available_bytes": RESUME_FLOOR_BYTES + 1}, {"growing": False}, 1)[0]
    assert health_allows(health, {"projected_mem_available_bytes": RESUME_FLOOR_BYTES + 1}, {"growing": False}, 1 + RESUME_DWELL_S)[0]
    dummy_job = {
        "stage": "stage10_seven_family", "mode": "instant", "geometry": "S3d_O8", "family": "gamma",
        "planned_peak_rss_budget_bytes": 5 * gib,
    }
    evidence = {"old_exact_classes": {}, "recovery0006_exact_classes": {}}
    assert class_upper(dummy_job, evidence) >= 5 * gib
    active_job = {
        "stage": "stage10_seven_family", "mode": "instant", "geometry": "S3d_O8",
        "family": "gamma", "replan_kind": "fresh_balanced_bundle", "job_id": "active",
    }
    distinct = {**active_job, "family": "neutron", "job_id": "distinct"}
    worker = Worker(active_job, type("P", (), {"pid": 999})(), None, "", 0.0)
    assert calibration_collision(active_job, [worker], evidence) is not None
    assert calibration_collision(distinct, [worker], evidence) is None
    original = campaign.build_plan()
    drain = load(DRAIN_COMPLETION)
    manifest = drain["receipt_manifest_before"]
    pending, summary = build_effective_plan(
        original, manifest, reserved={int(job["seed"]) for job in original}, max_group_by_cell=AUDITED_MAX_PAIRS,
    )
    assert summary["fresh_matched_seeds"] == EXPECTED_FRESH_MATCHED_SEEDS
    assert summary["pending_jobs"] == EXPECTED_PENDING_JOBS
    assert summary["final_selected_receipts"] == EXPECTED_FINAL_RECEIPTS
    assert summary["effective_events"] == EXPECTED_TOTAL_EVENTS
    assert len({int(j["seed"]) for j in pending if j.get("replan_kind") == "fresh_balanced_bundle"}) == EXPECTED_FRESH_MATCHED_SEEDS
    stage20 = [j for j in pending if j["stage"] == "stage20_proton"]
    for mode in campaign.MODES:
        canaries = stage20_canary_jobs(mode, pending)
        assert [int(j["events"]) for j in canaries] == [512, 512, 1024, 1024]
        assert all(int(j["events"]) <= 1024 or j.get("requires_stage20_canary_calibration") for j in stage20 if j["mode"] == mode)
    assert stage20_ladder_decision(512, pass512=False, pass1024=False) is None
    assert stage20_ladder_decision(1024, pass512=False, pass1024=False) is not None
    assert stage20_ladder_decision(1024, pass512=True, pass1024=False) is None
    assert stage20_ladder_decision(2048, pass512=True, pass1024=False) is not None
    assert stage20_ladder_decision(2048, pass512=True, pass1024=True) is None
    assert all(job_cap(job) == (2_000_000_000 if job["stage"] == "stage10_seven_family" else 6_000_000_000) for job in pending if job.get("replan_kind") == "fresh_balanced_bundle")
    return {
        "status": "PASS__RECOVERY0006_STATIC_SELF_TEST", "tests": 24,
        "transport_launched": False, "authority_published": AUTHORITY.exists(),
        "summary": summary,
    }


def partial_attempts() -> list[str]:
    return sorted(rel(path) for path in campaign.RUN_ROOT.glob("stage*/**/.attempt*.partial") if path.is_dir()) + sorted(rel(path) for path in RUN_NS.glob("attempts/**/.attempt*.partial") if path.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--publish-authority-only", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    if args.self_test and not args.print_recovery_plan:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    contract, original, manifest = verify_frozen_inputs()
    discoverable_reserved = all_discoverable_seeds()
    # Rebuild from the exact once-scanned set so allocation and audit registry
    # are bound to identical collision evidence.
    pending, summary = build_effective_plan(
        original, manifest, reserved=discoverable_reserved, max_group_by_cell=AUDITED_MAX_PAIRS
    )
    registry = seed_registry_payload(original, pending, discoverable_reserved)
    authority = load_or_publish_authority(contract, original, manifest, pending, summary, registry, publish=False)
    if args.print_recovery_plan:
        test_result = self_test() if args.self_test else None
        print(json.dumps({
            "status": "PASS__READ_ONLY_RECOVERY0006_RESOURCE_AWARE_UP_TO_SIX_PLAN",
            "controller_sha256": authority["controller"]["sha256"],
            "global_contract_sha256": EXPECTED_GLOBAL_SHA256,
            "drain_completion_sha256": EXPECTED_DRAIN_COMPLETION_SHA256,
            "inherited_pass_manifest_sha256": authority["inherited_pass_manifest_sha256"],
            "effective_pending_plan_sha256": authority["effective_pending_plan_sha256"],
            "fresh_seed_registry_payload_sha256": authority["fresh_seed_registry_payload_sha256"],
            "summary": summary,
            "audited_max_pairs": {"|".join(key): value for key, value in sorted(AUDITED_MAX_PAIRS.items())},
            "scheduler": authority["scheduler"], "frozen_clock": authority["frozen_clock"],
            "mem_available_bytes": campaign.mem_available_bytes(), "partial_attempts": partial_attempts(),
            "authority_published": AUTHORITY.exists(), "transport_launched": False,
            "self_test": test_result,
        }, indent=2, sort_keys=True))
        return 0
    if args.publish_authority_only:
        raise SystemExit("authority-only publication disabled; normal entry must acquire exclusive controller lock")
    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, coordinator_signal)
        if partial_attempts():
            raise RuntimeError("recovery0006 start requires zero unresolved partial attempts")
        inherited_manifest_hash_gate(manifest)
        authority = load_or_publish_authority(contract, original, manifest, pending, summary, registry, publish=True)
        publish_registry_and_cutover(authority, registry, manifest)
        configure_validator()
        environment = load_runtime(contract, args.cosima.resolve())
        update_state(contract, status="RUNNING__RECOVERY0006__TARGET_8", stage="stage10_seven_family", completed=sum(receipt_path(job).is_file() for job in pending))
        append_event("controller_started", authority_sha256=sha(AUTHORITY), cutover_receipt_sha256=sha(CUTOVER_RECEIPT), effective_pending_plan_sha256=authority["effective_pending_plan_sha256"])
        return run_campaign(original, manifest, pending, contract, environment, authority, registry)
    finally:
        for worker in list(_ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                try:
                    os.kill(worker.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                worker.process.join(timeout=30)
            if worker.process.is_alive():
                try:
                    os.kill(worker.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                worker.process.join(timeout=10)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
