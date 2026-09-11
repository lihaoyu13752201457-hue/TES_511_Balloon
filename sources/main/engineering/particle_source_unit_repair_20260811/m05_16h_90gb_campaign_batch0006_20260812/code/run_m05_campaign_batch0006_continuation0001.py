#!/usr/bin/env python3
"""Append-only post-mainline continuation0001.

Phase A transports one complete balanced seven-non-gamma wave.  It then
publishes a declaration-only cumulative TT/RP de-weighting/precision
checkpoint.  Only a PASS checkpoint permits the matched full-spectrum gamma
wave.  Old SIM/gzip files and old artifact hashes are never reopened.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import shutil
import signal
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0006_six_to_one_replan as r6
import resume_m05_campaign_batch0006_recovery0007_efficiency_scheduler as r7
import resume_m05_campaign_batch0006_recovery0008_disk_admission as r8
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_continuation0001_balanced_deweight_gamma"
RUN_NS = campaign.RUN_ROOT / "continuation0001_balanced_non_gamma_deweight_gamma"
AUTHORITY = RUN_NS / "authority.json"
SEED_REGISTRY = RUN_NS / "seed_registry.json"
SCHEDULER_EVENTS = RUN_NS / "scheduler_events.jsonl"
EXECUTION_STATE = RUN_NS / "execution_state.json"
CHECKPOINT = RUN_NS / "deweighting_precision_checkpoint.json"
GAMMA_UNLOCK = RUN_NS / "gamma_unlock.json"
FINAL_VALIDATION = RUN_NS / "final_validation.json"
FINAL_LEDGER = RUN_NS / "final_ledger.json"
FINAL_UMBRELLA = RUN_NS / "final_umbrella.json"
INTENT = campaign.RUN_ROOT / "post_mainline_continuation_intent.json"
MAINLINE_FINAL = campaign.RUN_ROOT / "recovery0008_current_attempt_disk_admission/final_validation.json"

NON_GAMMA_STAGE = "continuation_non_gamma_wave0001"
GAMMA_STAGE = "continuation_gamma_wave0001"
NON_GAMMA = ("alpha", "eminus", "eplus", "muminus", "muplus", "neutron", "proton")
FAMILY_ORDER = {family: index for index, family in enumerate((*NON_GAMMA, "gamma"))}
EVENTS = {
    "alpha": {"instant": 250, "buildup": 250},
    "eminus": {"instant": 5000, "buildup": 5000},
    "eplus": {"instant": 2500, "buildup": 2500},
    "muminus": {"instant": 44, "buildup": 1000},
    "muplus": {"instant": 1000, "buildup": 1000},
    "neutron": {"instant": 5000, "buildup": 5000},
    "proton": {"instant": 2048, "buildup": 2048},
    "gamma": {"instant": 25000, "buildup": 25000},
}
SOURCE_TAG = {"neutron": "n", "proton": "p", **{x: x for x in (*NON_GAMMA, "gamma") if x not in {"neutron", "proton"}}}
RSS_GIB = {
    (mode, geometry, family): value
    for (mode, geometry, family), value in r6.AUDITED_STAGE10_BUDGET_GIB.items()
}
for mode in campaign.MODES:
    for geometry in campaign.GEOMETRY_ORDER:
        RSS_GIB[(mode, geometry, "proton")] = 2.0
VALIDATION_MARGIN_S = 600
STOP_LAUNCH_MARGIN_S = 1800
HARD_END_MARGIN_S = 600
FRESH_SEED_BASE = 1_800_000_007
FRESH_SEED_STRIDE = 65_537
_PLAN: list[dict[str, Any]] = []


def rel(path: Path) -> str:
    return campaign.rel(path)


def load(path: Path) -> Any:
    return campaign.load_json(path)


def extract_named_seeds(value: Any, out: set[int], key: str = "") -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            extract_named_seeds(child, out, str(child_key).lower())
    elif isinstance(value, list):
        for child in value:
            extract_named_seeds(child, out, key)
    elif isinstance(value, int) and (key == "seed" or key.endswith("_seed")) and 1 <= value < 2**31:
        out.add(value)


def registered_seeds() -> tuple[set[int], list[str]]:
    """Scan named seed fields in JSON and Seed lines, never SIM/gzip/hash."""
    roots = campaign.ROOT / "runs/particle_source_unit_repair_20260811"
    paths = sorted(path for path in roots.rglob("*.json") if RUN_NS not in path.parents)
    seeds: set[int] = set()
    for path in paths:
        try:
            extract_named_seeds(load(path), seeds)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    seed_line = re.compile(r"^\s*Seed\s+(\d+)\s*$", re.MULTILINE)
    sources = sorted(path for path in roots.rglob("*.source") if RUN_NS not in path.parents)
    for path in sources:
        try:
            seeds.update(int(value) for value in seed_line.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    scope = [f"{rel(roots)}/**/*.json ({len(paths)} JSON files; recursively named seed/_seed fields only)"]
    scope.append(f"{rel(roots)}/**/*.source ({len(sources)} generated source cards; Seed lines only)")
    return seeds, scope


def allocate_seeds(count: int, reserved: set[int]) -> list[int]:
    result: list[int] = []
    candidate = FRESH_SEED_BASE
    while len(result) < count:
        if candidate not in reserved and candidate not in result and candidate < 2**31:
            result.append(candidate)
        candidate += FRESH_SEED_STRIDE
    return result


def make_plan(reserved: set[int]) -> list[dict[str, Any]]:
    cells = [(NON_GAMMA_STAGE, family, mode) for family in NON_GAMMA for mode in campaign.MODES]
    cells += [(GAMMA_STAGE, "gamma", mode) for mode in campaign.MODES]
    seeds = allocate_seeds(len(cells), reserved)
    jobs: list[dict[str, Any]] = []
    for ordinal, ((stage, family, mode), seed) in enumerate(zip(cells, seeds), 1):
        for geometry in campaign.GEOMETRY_ORDER:
            events = EVENTS[family][mode]
            budget = math.ceil(RSS_GIB.get((mode, geometry, family), 5.75) * 1024**3 / (64 * 1024**2)) * (64 * 1024**2)
            jobs.append({
                "job_id": f"c1_{'ng' if stage == NON_GAMMA_STAGE else 'g'}_{family}_{mode}_{geometry}_wave0001",
                "stage": stage, "geometry": geometry, "mode": mode, "family": family,
                "source_tag": SOURCE_TAG[family], "shard_ordinal": 1, "events": events,
                "seed": seed, "matched_seed_key": f"continuation0001|{family}|{mode}|wave0001",
                "replan_kind": "continuation_balanced_matched_replica",
                "continuation_phase": 1 if stage == NON_GAMMA_STAGE else 3,
                "declared_cap_bytes": 2_000_000_000,
                "planned_peak_rss_budget_bytes": budget,
                "planned_wall_budget_s": 7200.0 if family == "gamma" else 3600.0,
            })
    return jobs


def ordered_jobs(stage: str, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [job for job in pending if job["stage"] == stage]
    return sorted(rows, key=lambda job: (
        int(job["shard_ordinal"]), FAMILY_ORDER[str(job["family"])],
        campaign.MODES.index(str(job["mode"])), campaign.GEOMETRY_ORDER.index(str(job["geometry"])),
    ))


def current_pair_wave(stage: str, plan: list[dict[str, Any]]) -> str | None:
    """Strict atomic prefix: only one family/mode matched geometry pair is eligible."""
    for job in ordered_jobs(stage, plan):
        key = str(job["matched_seed_key"])
        pair = [row for row in plan if row["stage"] == stage and row["matched_seed_key"] == key]
        if not all(receipt_path(row).is_file() for row in pair):
            return key
    return None


def pair_wave_ordered_jobs(stage: str, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    key = current_pair_wave(stage, pending)
    return [] if key is None else [job for job in ordered_jobs(stage, pending) if job["matched_seed_key"] == key]


def balanced_waves(stage: str, plan: list[dict[str, Any]], keys_per_wave: int = 3) -> list[list[dict[str, Any]]]:
    ordered = ordered_jobs(stage, plan)
    keys = list(dict.fromkeys(str(job["matched_seed_key"]) for job in ordered))
    waves: list[list[dict[str, Any]]] = []
    for offset in range(0, len(keys), keys_per_wave):
        selected = set(keys[offset : offset + keys_per_wave])
        wave = [job for job in ordered if str(job["matched_seed_key"]) in selected]
        if len(wave) != 2 * len(selected):
            raise RuntimeError("continuation matched wave is not exactly two geometries per key")
        waves.append(wave)
    return waves


def run_balanced_stage(
    stage: str, plan: list[dict[str, Any]], original: list[dict[str, Any]], contract: dict[str, Any],
    environment: dict[str, str], authority: dict[str, Any], registry: dict[str, Any],
) -> str | None:
    """Run up to three matched keys (six jobs) and close the wave before advancing."""
    for wave_index, wave in enumerate(balanced_waves(stage, plan), 1):
        r6.append_event("balanced_matched_wave_start", stage=stage, wave_index=wave_index,
                        matched_keys=sorted({j["matched_seed_key"] for j in wave}), jobs=len(wave))
        reason = r8.run_stage(stage, wave, original, contract, environment, authority, registry)
        if reason:
            return f"wave{wave_index}: {reason}"
        if not all(receipt_path(job).is_file() for job in wave):
            return f"wave{wave_index}: matched wave did not close all geometry jobs"
        r6.append_event("balanced_matched_wave_PASS", stage=stage, wave_index=wave_index,
                        matched_keys=sorted({j["matched_seed_key"] for j in wave}), jobs=len(wave))
    return None


def receipt_path(job: dict[str, Any]) -> Path:
    return RUN_NS / "job_receipts" / str(job["stage"]) / f"{job['job_id']}.json"


def structural_receipt(job: dict[str, Any], payload: dict[str, Any]) -> bool:
    framing = payload.get("sim", {}).get("strict_framing", {})
    expected = int(job["events"])
    return (
        payload.get("status") == "PASS" and payload.get("job") == job
        and payload.get("selected_attempt") in (1, 2)
        and (campaign.ROOT / str(payload.get("attempt_dir", ""))).is_dir()
        and framing.get("gzip_eof") is True
        and int(framing.get("ID_first_count", -1)) == expected
        and int(framing.get("ID_second_count", -1)) == expected
        and framing.get("ID_columns_equal") is True
        and int(framing.get("SE_count", -1)) == expected
        and int(framing.get("EN_count", -1)) == 1
        and int(framing.get("TS", -1)) == expected
    )


def cheap_rss_evidence(_original: list[dict[str, Any]], pending: list[dict[str, Any]]) -> dict[str, Any]:
    exact: dict[str, dict[str, int]] = {}
    for job in pending:
        path = receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if not structural_receipt(job, payload):
            raise RuntimeError(f"continuation receipt structural drift: {job['job_id']}")
        key = r6.class_key(job)
        row = exact.setdefault(key, {"n": 0, "recent_n": 0, "max_bytes": 0})
        row["n"] += 1
        row["recent_n"] += 1
        row["max_bytes"] = max(row["max_bytes"], int(payload.get("peak_process_group_rss_bytes", 0)))
    return {"old_exact_classes": {}, "recovery0006_exact_classes": exact, "semantics": "continuation declarations only"}


def prior_attempts(job: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for path in (RUN_NS / "failed_attempts" / str(job["job_id"])).glob("attempt*/validation.json"):
        try:
            result.add(int(path.parent.name.removeprefix("attempt")))
        except ValueError:
            pass
    return result


def update_state(contract: dict[str, Any], *, status: str, stage: str, completed: int, error: str | None = None) -> None:
    campaign.atomic_replace_json(EXECUTION_STATE, {
        "schema_version": 1, "recovery_id": RECOVERY_ID, "status": status, "stage": stage,
        "completed_jobs": completed, "target_jobs": len(_PLAN),
        "non_gamma_completed": sum(receipt_path(j).is_file() for j in _PLAN if j["stage"] == NON_GAMMA_STAGE),
        "gamma_completed": sum(receipt_path(j).is_file() for j in _PLAN if j["stage"] == GAMMA_STAGE),
        "minimum_target_workers": 6, "absolute_worker_cap": 10,
        "deadline": contract["wall_clock"]["deadline"], "updated_at": datetime.now(timezone.utc).isoformat(),
        "mem_available_bytes": campaign.mem_available_bytes(), "campaign_bytes": campaign.campaign_bytes(),
        "free_disk_bytes": shutil.disk_usage(campaign.RUN_ROOT).free, "last_error": error,
    })


def continuation_contract(base: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(base))
    t0 = datetime.fromisoformat(base["wall_clock"]["t0"])
    deadline = datetime.fromisoformat(base["wall_clock"]["deadline"])
    total = int((deadline - t0).total_seconds())
    value["wall_clock"]["stages"] = [
        {"id": stage, "start_s": 0, "stop_launch_s": total - STOP_LAUNCH_MARGIN_S,
         "hard_end_s": total - HARD_END_MARGIN_S, "declared_cap": 2_000_000_000}
        for stage in (NON_GAMMA_STAGE, GAMMA_STAGE)
    ]
    return value


def plan_summary(plan: list[dict[str, Any]], registry_paths: list[str], reserved: set[int]) -> dict[str, Any]:
    ng = [job for job in plan if job["stage"] == NON_GAMMA_STAGE]
    gamma = [job for job in plan if job["stage"] == GAMMA_STAGE]
    fresh = {int(job["seed"]) for job in plan}
    return {
        "status": "PASS__CONTINUATION0001_PLAN__TRANSPORT_NOT_LAUNCHED",
        "namespace": rel(RUN_NS), "non_gamma_jobs": len(ng),
        "non_gamma_matched_seeds": len({j["seed"] for j in ng}),
        "non_gamma_events": sum(int(j["events"]) for j in ng),
        "gamma_jobs_after_checkpoint": len(gamma), "gamma_events_after_checkpoint": sum(int(j["events"]) for j in gamma),
        "fresh_seed_count": len(fresh), "fresh_seed_collision_count": len(fresh & reserved),
        "collision_scan_scope": registry_paths,
        "discovered_reserved_seed_count": len(reserved),
        "scheduler": {"normal_minimum_target": 6, "absolute_cap": 10, "memavailable_floor_bytes": int(1.5 * 1024**3), "launch_stagger_s": 15.0, "disk": "current attempt only"},
        "ordered_phases": ["balanced_non_gamma", "deweighting_precision_checkpoint", "matched_gamma"],
        "default_phase_a_only": True, "gamma_unlock_created_by_controller": False,
        "old_sim_or_gzip_opened": False, "old_artifact_hashes_recomputed": False,
    }


def proposed_authority(base: dict[str, Any], plan: list[dict[str, Any]], registry_paths: list[str], reserved: set[int]) -> dict[str, Any]:
    fresh = sorted({int(job["seed"]) for job in plan})
    return {
        "schema_version": 1, "recovery_id": RECOVERY_ID,
        "status": "AUTHORIZED__APPEND_ONLY_CONTINUATION0001__TRANSPORT_PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(), "controller": rel(Path(__file__).resolve()),
        "namespace": rel(RUN_NS), "intent": rel(INTENT), "mainline_final": rel(MAINLINE_FINAL),
        "plan": plan,
        "fresh_seed_registry": {"seeds": fresh, "collision_count": len(set(fresh) & reserved), "discovered_reserved_seed_count": len(reserved), "matched_pair_use_exactly_two_jobs": True, "retry_reuses_exact_seed": True, "global_structural_scan_scope": registry_paths},
        "frozen_declared_inputs": {
            "sources": base["static_gate"]["sources"], "geometry_bundles": base["static_gate"]["geometry_bundles"],
            "transport": base["static_gate"]["transport"], "source_contract": base["static_gate"]["source_contract"],
            "corrected_spectrum_root": campaign.CORRECTED_SPECTRUM_ROOT, "forbidden_legacy_spectrum": campaign.FORBIDDEN_SPECTRUM,
        },
        "resource_policy": {"minimum_target_workers": 6, "absolute_worker_cap": 10, "launch_stagger_s": 15.0, "projected_memavailable_floor_bytes": int(1.5 * 1024**3), "hard_low_memory_watchdog_bytes": campaign.HARD_LOW_MEMORY_BYTES, "maximum_exact_attempts": 2, "current_attempt_only_disk_reservation": True, "deadline_validation_margin_s": VALIDATION_MARGIN_S},
        "phase_gate": "strict one-matched-seed-key pair wave; next family/mode key opens only after both geometry receipts PASS; controller defaults phase-A-only; gamma requires cumulative PASS checkpoint plus a separate pre-existing write-once gamma_unlock PASS authority",
        "normalization": {"prompt": "sum(selected)/sum(TT) within geometry/mode/family", "buildup": "sum(RP)/sum(TT) within geometry/mode/family/volume/isotope-state; retain positive-TT zero-RP shards", "bundle_divisor": None},
        "old_data_policy": {"trust_PASS_receipt_declarations": True, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False},
    }


def publish_checkpoint(plan: list[dict[str, Any]]) -> dict[str, Any]:
    if CHECKPOINT.is_file():
        return load(CHECKPOINT)
    ng = [job for job in plan if job["stage"] == NON_GAMMA_STAGE]
    missing = [job["job_id"] for job in ng if not receipt_path(job).is_file()]
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    state: dict[tuple[str, str, str, str, int, float], float] = defaultdict(float)
    errors: list[str] = []
    records: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    # Cumulative exposure means mainline plus continuation.  This reads only
    # published receipt JSON declarations; old SIM/gzip/artifact bytes and
    # their hashes remain untouched.
    mainline = load(MAINLINE_FINAL)
    for row in mainline.get("selected_receipts", []):
        path = campaign.ROOT / str(row.get("path", ""))
        if not path.is_file():
            errors.append(f"declared mainline receipt missing: {row.get('job_id')}")
            continue
        payload = load(path)
        job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
        if job.get("family") not in NON_GAMMA:
            continue
        if not structural_receipt(job, payload):
            errors.append(f"mainline receipt declaration drift: {row.get('job_id')}")
            continue
        records.append((job, payload, "mainline"))
    for job in ng:
        path = receipt_path(job)
        if not path.is_file():
            continue
        payload = load(path)
        if not structural_receipt(job, payload):
            errors.append(f"receipt declaration drift: {job['job_id']}")
            continue
        records.append((job, payload, "continuation"))
    for job, payload, kind in records:
        iso = payload.get("isotope_dat", {})
        tt = float(iso.get("TT_s", 0.0))
        if not math.isfinite(tt) or tt <= 0:
            errors.append(f"non-positive TT: {job['job_id']}")
        key = (str(job["geometry"]), str(job["mode"]), str(job["family"]))
        cell = cells.setdefault(key, {"geometry": key[0], "mode": key[1], "family": key[2], "receipts": 0, "mainline_receipts": 0, "continuation_receipts": 0, "events": 0, "sum_TT_s": 0.0, "sum_TT2_s2": 0.0, "sum_RP": 0.0})
        cell["receipts"] += 1; cell["events"] += int(job["events"])
        cell[f"{kind}_receipts"] += 1
        cell["sum_TT_s"] = math.fsum((cell["sum_TT_s"], tt)); cell["sum_TT2_s2"] = math.fsum((cell["sum_TT2_s2"], tt * tt))
        for row in iso.get("RP_totals", []):
            rp = float(row.get("sum_RP", 0.0)); cell["sum_RP"] = math.fsum((cell["sum_RP"], rp))
            state[(key[0], key[1], key[2], str(row.get("volume")), int(row.get("isotope_id")), float(row.get("excitation_keV", 0.0)))] += rp
    rows = []
    for key in sorted(cells):
        cell = cells[key]
        tt = float(cell["sum_TT_s"]); tt2 = float(cell.pop("sum_TT2_s2"))
        cell["transport_exposure_ESS"] = tt * tt / tt2 if tt2 > 0 else 0.0
        cell["RP_per_TT_s"] = float(cell["sum_RP"]) / tt if tt > 0 else None
        cell["zero_count_one_sided_95_rate_per_s"] = -math.log(0.05) / tt if tt > 0 else None
        rows.append(cell)
    pair_errors = []
    for family in NON_GAMMA:
        for mode in campaign.MODES:
            pair = [next((job for job in ng if job["geometry"] == geometry and job["mode"] == mode and job["family"] == family and receipt_path(job).is_file()), None) for geometry in campaign.GEOMETRY_ORDER]
            if any(job is None for job in pair):
                pair_errors.append(f"{family}/{mode}")
    errors.extend(f"unclosed matched pair: {item}" for item in pair_errors)
    status = "PASS__NON_GAMMA_BALANCED_PREFIX__DEWEIGHTING_PRECISION_CHECKPOINT" if not missing and not errors and len(rows) == 28 else "FAIL__NO_GAMMA_AUTHORITY"
    payload = {
        "schema_version": 1, "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "cumulative mainline plus continuation0001, within identical fixed geometry/mode/family pools",
        "non_gamma_receipts": len(ng) - len(missing), "non_gamma_events": sum(j["events"] for j in ng if receipt_path(j).is_file()),
        "cumulative_non_gamma_receipts": len(records), "cumulative_non_gamma_events": sum(int(job["events"]) for job, _payload, _kind in records),
        "missing": missing, "errors": errors, "cells": rows,
        "buildup_state_RP_sums": [{"geometry": k[0], "mode": k[1], "family": k[2], "volume": k[3], "isotope_id": k[4], "excitation_keV": k[5], "sum_RP": value, "sum_TT_s": cells[(k[0], k[1], k[2])]["sum_TT_s"], "RP_per_TT_s": value / cells[(k[0], k[1], k[2])]["sum_TT_s"] if cells[(k[0], k[1], k[2])]["sum_TT_s"] > 0 else None} for k, value in sorted(state.items())],
        "normalization": {"prompt": "sum(selected)/sum(TT), fixed geometry/mode/family", "buildup": "sum(RP)/sum(TT), fixed geometry/mode/family/volume/isotope-state", "positive_TT_zero_RP_retained": True, "replica_or_bundle_divisor": None},
        "gamma_transport_authorized": status.startswith("PASS"), "old_receipt_JSON_declarations_structurally_read": True, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False,
    }
    campaign.atomic_write_once_json(CHECKPOINT, payload)
    return payload


def publish_final(plan: list[dict[str, Any]], fatal: str | None) -> None:
    if FINAL_UMBRELLA.is_file():
        return
    selected = []
    for job in plan:
        path = receipt_path(job)
        if path.is_file() and structural_receipt(job, load(path)):
            selected.append({"job_id": job["job_id"], "stage": job["stage"], "geometry": job["geometry"], "mode": job["mode"], "family": job["family"], "events": job["events"], "receipt": rel(path)})
    ng_target = sum(j["stage"] == NON_GAMMA_STAGE for j in plan)
    gamma_target = sum(j["stage"] == GAMMA_STAGE for j in plan)
    ng = sum(row["stage"] == NON_GAMMA_STAGE for row in selected)
    gamma = sum(row["stage"] == GAMMA_STAGE for row in selected)
    checkpoint = load(CHECKPOINT) if CHECKPOINT.is_file() else None
    status = "PASS__CONTINUATION0001_NON_GAMMA_DEWEIGHT_GAMMA_COMPLETE" if fatal is None and ng == ng_target and gamma == gamma_target and checkpoint and str(checkpoint.get("status", "")).startswith("PASS") else ("PASS__CONTINUATION0001_NON_GAMMA_DEWEIGHT_COMPLETE__GAMMA_LOCKED" if ng == ng_target and checkpoint and str(checkpoint.get("status", "")).startswith("PASS") else "FAIL__CONTINUATION0001_NO_COMPLETE_BALANCED_PREFIX")
    validation = {"schema_version": 1, "status": status, "selected_receipts": selected, "non_gamma_receipts": ng, "non_gamma_target": ng_target, "gamma_receipts": gamma, "gamma_target": gamma_target, "events": sum(int(row["events"]) for row in selected), "fatal": fatal, "deweighting_checkpoint": rel(CHECKPOINT) if CHECKPOINT.is_file() else None, "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False}
    campaign.atomic_write_once_json(FINAL_VALIDATION, validation)
    campaign.atomic_write_once_json(FINAL_LEDGER, {"schema_version": 1, "status": status, "selected_receipts": selected, "normalization_checkpoint": validation["deweighting_checkpoint"]})
    campaign.atomic_write_once_json(FINAL_UMBRELLA, {"schema_version": 1, "status": status, "authority": rel(AUTHORITY), "seed_registry": rel(SEED_REGISTRY), "checkpoint": validation["deweighting_checkpoint"], "final_validation": rel(FINAL_VALIDATION), "final_ledger": rel(FINAL_LEDGER), "old_SIM_or_gzip_reopened": False, "old_artifact_hashes_recomputed": False})


def bind(plan: list[dict[str, Any]]) -> None:
    global _PLAN
    _PLAN = plan
    for module in (r6, r7, r8):
        module.RECOVERY_ID = RECOVERY_ID; module.RUN_NS = RUN_NS; module.AUTHORITY = AUTHORITY
        module.SCHEDULER_EVENTS = SCHEDULER_EVENTS; module.EXECUTION_STATE = EXECUTION_STATE
        module.FINAL_VALIDATION = FINAL_VALIDATION; module.FINAL_LEDGER = FINAL_LEDGER; module.FINAL_UMBRELLA = FINAL_UMBRELLA
    r6.REPLAN_SEED_REGISTRY = SEED_REGISTRY; r7.SEED_REGISTRY = SEED_REGISTRY; r8.SEED_REGISTRY = SEED_REGISTRY
    r7.MINIMUM_TARGET_WORKERS = 6; r7.ABSOLUTE_MAX_WORKERS = 10; r7.PROJECTED_FLOOR_BYTES = int(1.5 * 1024**3)
    r7.receipt_path = receipt_path; r6.receipt_path = receipt_path; r8.receipt_path = receipt_path
    r7.validate_replan_receipt = structural_receipt; r6.validate_replan_receipt = structural_receipt; r8.validate_receipt = structural_receipt
    r6.job_cap = lambda job: int(job["declared_cap_bytes"])
    r6.prior_exact_attempts = prior_attempts; r7.prior_exact_attempts = prior_attempts
    r6.runtime_job_budget = lambda job, *_args: int(job["planned_peak_rss_budget_bytes"])
    r6.runtime_job_wall_budget = lambda job, *_args: float(job["planned_wall_budget_s"])
    r6.disk_projection = r8.disk_projection; r6.worker_entry = r8.worker_entry; r6.reap = r8.reap
    r7.rss_evidence = cheap_rss_evidence; r7.ordered_stage_jobs = ordered_jobs; r7.update_state = update_state
    r8._R7_RUN_STAGE = r7.run_stage


def self_test() -> dict[str, Any]:
    reserved, paths = registered_seeds(); plan = make_plan(reserved); summary = plan_summary(plan, paths, reserved)
    assert len(plan) == 32 and summary["non_gamma_jobs"] == 28 and summary["non_gamma_matched_seeds"] == 14
    assert summary["non_gamma_events"] == 65_280 and summary["gamma_events_after_checkpoint"] == 100_000
    assert summary["fresh_seed_collision_count"] == 0
    for stage in (NON_GAMMA_STAGE, GAMMA_STAGE):
        for seed in {j["seed"] for j in plan if j["stage"] == stage}:
            pair = [j for j in plan if j["seed"] == seed]
            assert len(pair) == 2 and {j["geometry"] for j in pair} == set(campaign.GEOMETRY_ORDER)
            assert len({j["events"] for j in pair}) == 1
    first_key = ordered_jobs(NON_GAMMA_STAGE, plan)[0]["matched_seed_key"]
    assert {j["matched_seed_key"] for j in pair_wave_ordered_jobs(NON_GAMMA_STAGE, plan)} == {first_key}
    ng_waves = balanced_waves(NON_GAMMA_STAGE, plan)
    assert [len(wave) for wave in ng_waves] == [6, 6, 6, 6, 4]
    assert all(len({j["matched_seed_key"] for j in wave}) * 2 == len(wave) for wave in ng_waves)
    assert not GAMMA_UNLOCK.exists()
    return {**summary, "status": "PASS__CONTINUATION0001_PURE_STRUCTURAL_SELF_TEST", "tests": 7}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true"); parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--phase-a-only", action=argparse.BooleanOptionalAction, default=True,
                        help="default true; --no-phase-a-only still requires a separate PASS gamma_unlock.json")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT); args = parser.parse_args()
    reserved, registry_paths = registered_seeds(); plan = make_plan(reserved)
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True)); return 0
    if args.print_plan:
        print(json.dumps({**plan_summary(plan, registry_paths, reserved), "plan": plan}, indent=2, sort_keys=True)); return 0
    base = load(campaign.GLOBAL_CONTRACT); contract = continuation_contract(base)
    intent = load(INTENT); mainline = load(MAINLINE_FINAL)
    if intent.get("status") != "RECORDED__NO_TRANSPORT_AUTHORITY":
        raise RuntimeError("continuation intent status drift")
    if mainline.get("status") != "PASS__REPLANNED_MAINLINE_EVENT_TARGET_COMPLETE" or mainline.get("validated_receipts") != 488 or mainline.get("validated_events") != 6_149_560:
        raise RuntimeError("mainline declaration is not exact terminal PASS")
    deadline = datetime.fromisoformat(contract["wall_clock"]["deadline"])
    if datetime.now(timezone.utc) + timedelta(seconds=STOP_LAUNCH_MARGIN_S) >= deadline:
        raise RuntimeError("insufficient original campaign window for continuation")
    authority_proposal = proposed_authority(base, plan, registry_paths, reserved)
    lock = campaign.acquire_lock(); previous: dict[int, Any] = {}; fatal: str | None = None
    try:
        RUN_NS.mkdir(parents=True, exist_ok=True)
        if AUTHORITY.is_file():
            authority = load(AUTHORITY)
            for key in ("recovery_id", "namespace", "plan", "fresh_seed_registry", "frozen_declared_inputs", "resource_policy", "phase_gate", "normalization", "old_data_policy"):
                if authority.get(key) != authority_proposal.get(key): raise RuntimeError(f"existing continuation authority differs: {key}")
        else:
            campaign.atomic_write_once_json(AUTHORITY, authority_proposal); authority = load(AUTHORITY)
        if not SEED_REGISTRY.is_file():
            campaign.atomic_write_once_json(SEED_REGISTRY, {"schema_version": 1, "status": "PASS__FRESH_GLOBALLY_COLLISION_FREE_REGISTERED_SEEDS", "fresh": authority["fresh_seed_registry"], "plan_jobs": [{"job_id": j["job_id"], "seed": j["seed"], "matched_seed_key": j["matched_seed_key"]} for j in plan]})
        bind(plan); r6.configure_validator(); environment = r7.load_runtime_without_hash_revalidation(base, args.cosima.resolve())
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum); signal.signal(signum, r6.coordinator_signal)
        r6.append_event("continuation_controller_started", non_gamma_jobs=28, gamma_jobs=4, minimum_target_workers=6, absolute_worker_cap=10)
        reason = run_balanced_stage(NON_GAMMA_STAGE, plan, [], contract, environment, authority, {})
        if reason: fatal = reason
        checkpoint = publish_checkpoint(plan)
        if not str(checkpoint.get("status", "")).startswith("PASS"):
            fatal = fatal or "non-gamma/deweighting checkpoint did not PASS"
        if fatal is None and not args.phase_a_only:
            if not GAMMA_UNLOCK.is_file():
                fatal = "gamma requested but independent write-once gamma_unlock.json is absent"
            else:
                unlock = load(GAMMA_UNLOCK)
                if (
                    unlock.get("status") != "PASS__CONTINUATION0001_GAMMA_UNLOCK"
                    or unlock.get("authority") != rel(AUTHORITY)
                    or unlock.get("checkpoint") != rel(CHECKPOINT)
                    or unlock.get("gamma_plan_job_ids") != [j["job_id"] for j in plan if j["stage"] == GAMMA_STAGE]
                ):
                    fatal = "gamma_unlock.json does not structurally bind authority/checkpoint/exact gamma plan"
                else:
                    reason = run_balanced_stage(GAMMA_STAGE, plan, [], contract, environment, authority, {})
                    if reason: fatal = reason
        publish_final(plan, fatal)
        return 0 if str(load(FINAL_UMBRELLA)["status"]).startswith("PASS") else 1
    except BaseException as exc:
        fatal = f"{type(exc).__name__}: {exc}"
        if RUN_NS.is_dir():
            try: publish_final(plan, fatal)
            except BaseException: pass
        raise
    finally:
        for worker in list(r6._ACTIVE_WORKERS.values()):
            if worker.process.is_alive():
                try: os.kill(worker.process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                worker.process.join(timeout=30)
        for signum, handler in previous.items(): signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN); lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
