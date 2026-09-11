#!/usr/bin/env python3
"""Prepare SG3B M05 day-15 exact-position delayed transport on the data disk.

This is a thin SG3B adapter around the retained SF3 M05 activation primitives.
It consumes only validated SG3B BUILDUP receipts, retains every family TT,
uses NUBASE-2020 ground-state handling, performs one semantic RPIP scan, and
emits the schema consumed by the canonical tool/execute runner and dashboard.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import runpy
import sys
import types
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
PROFILE_ID = "SG3B_M05_DAY15_DELAYED_1M_20260817_V1"
CANDIDATE = "SG3B"
EVENTS = 1_000_000
REPO = Path("/home/ubuntu/TES_511_Balloon")
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
TARGET = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_v1")
GENERATED = TARGET / "generated"
RUN_ROOT = TARGET / "run"
INPUTS = (
    ("plan1_v1", "SG3B_PLAN1_BACKGROUND_20260816_V1", Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_plan1_background_v1")),
    ("extra2x_v1", "SG3B_PLAN1_BACKGROUND_EXTRA2X_20260816_V1", Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_plan1_background_extra2x_v1")),
)
REUSED_BUILDER = Path("/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/code/build_sf3_activation.py")
CANONICAL_EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")
CANONICAL_PROGRESS = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/progress.py")
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_reused_primitives() -> dict[str, Any]:
    """Load the retained M05 algorithms without invoking its SF3 CLI."""
    common = types.ModuleType("sf3_plan1_common")
    common.DELAYED_EVENTS = EVENTS
    common.FAMILIES = FAMILIES
    common.PACKAGE_ROOT = TARGET
    common.PROFILE_ID = PROFILE_ID
    common.REPO_ROOT = REPO
    common.RUN_ROOT = RUN_ROOT
    common.SF3_SETUP = GEOMETRY
    common.active_prefix = lambda job_id: RUN_ROOT / "jobs" / job_id / "active" / job_id
    common.read_job_plan = lambda _path: []
    common.sha256 = sha256
    common.utc_now = utc_now
    common.write_once_text = lambda path, text: Path(path).write_text(text, encoding="utf-8")
    previous = sys.modules.get("sf3_plan1_common")
    sys.modules["sf3_plan1_common"] = common
    try:
        module = runpy.run_path(str(REUSED_BUILDER), run_name="sg3b_reused_m05_primitives")
    finally:
        if previous is None:
            sys.modules.pop("sf3_plan1_common", None)
        else:
            sys.modules["sf3_plan1_common"] = previous
    module.update({
        "DELAYED_EVENTS": EVENTS,
        "FAMILIES": FAMILIES,
        "PROFILE_ID": PROFILE_ID,
        "REPO_ROOT": REPO,
        "RUN_ROOT": RUN_ROOT,
        "SF3_SETUP": GEOMETRY,
        "OUTPUT_ROOT": GENERATED / "activation",
        "NUBASE": REPO / "inputs/nubase/nubase_2020.txt",
        "active_prefix": common.active_prefix,
    })
    return module


def validate_receipt(path: Path, payload: dict[str, Any], expected_profile: str) -> None:
    errors: list[str] = []
    if payload.get("status") != "PASS" or payload.get("profile_id") != expected_profile:
        errors.append("status/profile mismatch")
    if payload.get("candidate") != CANDIDATE or payload.get("mode") != "buildup":
        errors.append("candidate/mode mismatch")
    if payload.get("family") not in FAMILIES:
        errors.append("family mismatch")
    if Path(str(payload.get("setup_path"))).resolve() != GEOMETRY.resolve():
        errors.append("setup mismatch")
    header = payload.get("sim_header") or {}
    if Path(str(header.get("geometry"))).resolve() != GEOMETRY.resolve() or header.get("seed") != payload.get("seed"):
        errors.append("SIM header geometry/seed mismatch")
    for path_key, size_key in (("sim_path", "sim_bytes"), ("isotope_dat_path", "isotope_dat_bytes"), ("log_path", "log_bytes")):
        artifact = Path(str(payload.get(path_key, "")))
        if not artifact.is_file() or artifact.stat().st_size != int(payload.get(size_key, -1)) or artifact.stat().st_size <= 0:
            errors.append(f"artifact mismatch: {path_key}")
    source = Path(str(payload.get("source_path", "")))
    if not source.is_file() or sha256(source) != payload.get("source_sha256"):
        errors.append("source digest mismatch")
    else:
        text = source.read_text(encoding="utf-8", errors="replace")
        if text.count(CORRECTED_TOKEN) != 20 or FORBIDDEN_TOKEN in text:
            errors.append("corrected-keV source boundary mismatch")
    if errors:
        raise RuntimeError(f"{path}: {'; '.join(errors)}")


def collect_inputs(core: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], set[int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    authorities: list[dict[str, Any]] = []
    occupied: set[int] = set()
    for namespace, profile, root in INPUTS:
        for receipt_path in sorted((root / "receipts").glob("*buildup*.json")):
            receipt = load_json(receipt_path)
            validate_receipt(receipt_path, receipt, profile)
            dat_path = Path(receipt["isotope_dat_path"])
            parsed = core["parse_dat"](dat_path)
            declared = receipt.get("isotope_dat") or {}
            if not math.isclose(float(parsed["TT_s"]), float(declared.get("TT_s", -1)), rel_tol=0.0, abs_tol=1e-12):
                raise RuntimeError(f"DAT TT differs from receipt: {receipt_path}")
            if int(parsed["RP_record_count"]) != int(declared.get("RP_record_count", -1)):
                raise RuntimeError(f"DAT RP count differs from receipt: {receipt_path}")
            item = {
                "namespace": namespace,
                "receipt_path": receipt_path,
                "receipt": receipt,
                "dat_path": dat_path,
                "sim_path": Path(receipt["sim_path"]),
                "parsed": parsed,
            }
            grouped[str(receipt["family"])].append(item)
            occupied.add(int(receipt["seed"]))
            authorities.append({
                "namespace": namespace,
                "job_id": receipt["job_id"],
                "family": receipt["family"],
                "events": receipt["events"],
                "seed": receipt["seed"],
                "receipt_path": str(receipt_path.resolve()),
                "receipt_sha256": sha256(receipt_path),
                "dat_path": str(dat_path.resolve()),
                "dat_sha256": sha256(dat_path),
                "sim_path": str(Path(receipt["sim_path"]).resolve()),
                "sim_bytes": receipt["sim_bytes"],
                "TT_s": parsed["TT_s"],
                "RP_record_count": parsed["RP_record_count"],
                "sum_RP": parsed["sum_RP"],
            })
    missing = set(FAMILIES) - set(grouped)
    if missing:
        raise RuntimeError(f"missing SG3B buildup family input: {sorted(missing)}")
    # Include every seed registered by the two source bundles, including instant jobs.
    for _, _, root in INPUTS:
        for path in (root / "receipts").glob("*.json"):
            occupied.add(int(load_json(path)["seed"]))
    return dict(grouped), authorities, occupied


def derive_seeds(occupied: set[int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for family in FAMILIES:
        counter = 0
        while True:
            token = f"{PROFILE_ID}|{CANDIDATE}|delayed|{family}|{counter}".encode()
            seed = 1 + int.from_bytes(hashlib.sha256(token).digest()[:8], "big") % 2_147_483_646
            if seed not in occupied and seed not in result.values():
                result[family] = seed
                break
            counter += 1
    return result


def prepare() -> Path:
    if TARGET.exists():
        raise RuntimeError(f"write-once target already exists: {TARGET}")
    if not GEOMETRY.is_file() or not REUSED_BUILDER.is_file() or not CANONICAL_EXECUTOR.is_file():
        raise RuntimeError("geometry/reused-builder/canonical-executor prerequisite missing")
    core = load_reused_primitives()
    grouped, authorities, occupied = collect_inputs(core)
    seeds = derive_seeds(occupied)
    TARGET.mkdir(parents=True, exist_ok=False)
    sources = GENERATED / "sources"
    sources.mkdir(parents=True)
    (GENERATED / "activation" / "exact_position_sources").mkdir(parents=True)

    nubase = core["load_nubase_states"](REPO / "inputs/nubase/nubase_2020.txt")
    copy_map = core["geometry_copy_map"](GEOMETRY)
    jobs: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    activation_rows: list[dict[str, Any]] = []
    scan_rows: list[dict[str, Any]] = []
    all_source_rows: list[dict[str, Any]] = []

    for family in FAMILIES:
        entries = grouped[family]
        sum_tt = math.fsum(float(item["parsed"]["TT_s"]) for item in entries)
        if sum_tt <= 0:
            raise RuntimeError(f"non-positive sum(TT): {family}")
        state_values: dict[tuple[str, int, float], list[float]] = defaultdict(list)
        for item in entries:
            for key, value in item["parsed"]["totals"].items():
                state_values[key].append(float(value))
        production: list[dict[str, Any]] = []
        for key, values in sorted(state_values.items()):
            sum_rp = math.fsum(values)
            production.append({
                "geometry": CANDIDATE,
                "family": family,
                "volume": key[0],
                "isotope_id": int(key[1]),
                "excitation_keV": float(key[2]),
                "sum_RP": sum_rp,
                "sum_TT_s_including_zero_RP_DAT": sum_tt,
                "production_rate_s-1": sum_rp / sum_tt,
            })
        keys = {core["state_key"](row["volume"], row["isotope_id"], row["excitation_keV"]) for row in production}
        points: dict[Any, list[Any]] = defaultdict(list)
        for item in entries:
            found, audit = core["parse_rpip_file"](item["sim_path"], keys, copy_map)
            audit.update({"namespace": item["namespace"], "job_id": item["receipt"]["job_id"], "family": family})
            scan_rows.append(audit)
            for key, values in found.items():
                points[key].extend(values)
        included, holdout = core["classify_states"](production, dict(points), nubase)
        core["require_complete_positive_ground"](family, holdout)
        activity = math.fsum(float(row["day15_activity_Bq"]) for row in included)
        job_id = f"sg3b_delayed_{family}"
        sampled = core["weighted_sample"](included, dict(points), 50_000, seeds[family])
        source_path = sources / f"{job_id}.source"
        text, closure = core["render_delayed_source"]({"job_id": job_id, "seed": seeds[family]}, sampled, activity)
        # The reused physics renderer's prose says SF3; bind authority explicitly to SG3B.
        text = text.replace("Candidate-owned SF3", "Candidate-owned SG3B").replace("validated SF3 BUILDUP", "validated SG3B BUILDUP")
        source_path.write_text(text, encoding="utf-8")
        positions_path = GENERATED / "activation" / "exact_position_sources" / f"{family}_m50000.csv"
        with positions_path.open("w", encoding="utf-8", newline="") as handle:
            fields = ("sample_index", "volume", "ZA", "excitation_keV", "x_cm", "y_cm", "z_cm")
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(sampled)
        disposition = closure["execution_disposition"]
        all_source_rows.append({
            "family": family,
            "seed": seeds[family],
            "source_path": str(source_path),
            "source_sha256": sha256(source_path),
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": activity,
            "sum_TT_s": sum_tt,
            "sum_RP": math.fsum(float(item["parsed"]["sum_RP"]) for item in entries),
            "buildup_files": len(entries),
            "sampled_positions": len(sampled),
            "transport_blocks": closure["transport_blocks"],
            "positions_path": str(positions_path),
            "included_states": included,
            "holdout_states": holdout,
            "closure": closure,
        })
        activation_rows.append({
            "family": family,
            "buildup_files": len(entries),
            "buildup_histories": sum(int(item["receipt"]["events"]) for item in entries),
            "sum_TT_s": sum_tt,
            "sum_RP": math.fsum(float(item["parsed"]["sum_RP"]) for item in entries),
            "transported_ground_activity_Bq": activity,
            "execution_disposition": disposition,
        })
        if disposition.startswith("RUN_"):
            jobs.append({
                "ordinal": len(jobs) + 1,
                "job_id": job_id,
                "candidate": CANDIDATE,
                "stage": "delayed",
                "mode": "delayed",
                "family": family,
                "events": EVENTS,
                "seed": seeds[family],
                "source_path": str(source_path),
                "setup_path": str(GEOMETRY),
                "output_prefix": str(RUN_ROOT / "jobs" / job_id / "active" / job_id),
                "estimated_bytes": 4 * 1024**3,
                "requires_isotope_dat": False,
                "production_canary": False,
            })
    if not jobs:
        raise RuntimeError("no positive delayed source family")
    jobs[0]["production_canary"] = True
    canary = jobs[0]["job_id"]
    totals = {"jobs": len(jobs), "instant_histories": 0, "buildup_histories": 0}
    plan = {"schema_version": 1, "status": "PASS", "profile_id": PROFILE_ID, "candidate": CANDIDATE, "jobs": jobs, "totals": totals}
    source_rows = [{
        "job_id": row["job_id"], "mode": row["mode"], "family": row["family"],
        "events": row["events"], "seed": row["seed"], "source_path": row["source_path"],
        "setup_path": row["setup_path"], "source_sha256": sha256(Path(row["source_path"])),
    } for row in jobs]
    write_json(GENERATED / "job_plan.json", plan)
    write_json(GENERATED / "seed_registry.json", {
        "schema_version": 1, "profile_id": PROFILE_ID,
        "status": "PASS__FRESH_GLOBALLY_DISJOINT_DELAYED_SEEDS",
        "seeds": [{"job_id": row["job_id"], "seed": row["seed"], "family": row["family"]} for row in jobs],
        "occupied_input_seed_count": len(occupied),
    })
    write_json(GENERATED / "source_manifest.json", {
        "schema_version": 1, "profile_id": PROFILE_ID,
        "status": "PASS__SG3B_M05_EXACT_POSITION_DELAYED_SOURCES",
        "sources": source_rows,
    })
    write_json(GENERATED / "preflight.json", {
        "schema_version": 1, "profile_id": PROFILE_ID, "candidate": CANDIDATE,
        "status": "PASS__SG3B_M05_DELAYED_PREFLIGHT", "job_plan": totals,
    })
    write_json(GENERATED / "activation" / "manifest.json", {
        "schema_version": 1,
        "status": "PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY",
        "created_at": utc_now(),
        "candidate": CANDIDATE,
        "geometry": str(GEOMETRY),
        "normalization": "sum(RP)/sum(TT) per incident family; TT from every selected zero-RP DAT retained",
        "state_policy": "NUBASE-2020 ground-state correction; excited/unresolved fail closed; positive ground states require exact RPIP support",
        "source_mixture_policy": "50,000 deterministic exact-position draws; stride 5 to 10,000 blocks; retained flux multiplied by 5",
        "registered_delayed_events_per_positive_family": EVENTS,
        "planned_positive_families": [row["family"] for row in jobs],
        "zero_source_families": [row["family"] for row in all_source_rows if row["execution_disposition"] == "SKIP_ZERO_A15"],
        "input_receipts": authorities,
        "activation_cells": activation_rows,
        "source_cells": all_source_rows,
        "rpip_scans": scan_rows,
        "reused_physics_builder": str(REUSED_BUILDER),
        "canonical_executor": str(CANONICAL_EXECUTOR),
        "canonical_progress": str(CANONICAL_PROGRESS),
    })
    free = os.statvfs(TARGET).f_bavail * os.statvfs(TARGET).f_frsize
    config = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "candidate": CANDIDATE,
        "allowed_stages": ["delayed"],
        "source_policy": "m05_exact_position_delayed",
        "preflight_pass_status": "PASS__SG3B_M05_DELAYED_PREFLIGHT",
        "source_manifest_pass_status": "PASS__SG3B_M05_EXACT_POSITION_DELAYED_SOURCES",
        "seed_registry_pass_status": "PASS__FRESH_GLOBALLY_DISJOINT_DELAYED_SEEDS",
        "geometry_setup": str(GEOMETRY),
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "cosima_workdir": str(REPO),
        "generated_root": str(GENERATED),
        "run_root": str(RUN_ROOT),
        "workers": 4,
        "max_workers": 4,
        "max_attempts": 2,
        "canary_job_id": canary,
        "start_free_bytes": 100 * 1024**3,
        "dynamic_reserve_bytes": 64 * 1024**3,
        "launch_mem_available_bytes": 1024**3,
        "runtime_mem_floor_bytes": 1024**3,
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 1024**3,
        "launch_worker_reservation_bytes": 1536 * 1024**2,
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 10.0,
        "runtime_memory_full_psi_avg10_max": 25.0,
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
        "controller_command": ["python3", str(CANONICAL_EXECUTOR), "--config", str(TARGET / "config.json"), "--workers", "4"],
        "progress_command": ["python3", str(CANONICAL_PROGRESS), "--config", str(TARGET / "config.json")],
    })
    return TARGET / "config.json"


if __name__ == "__main__":
    print(prepare())
