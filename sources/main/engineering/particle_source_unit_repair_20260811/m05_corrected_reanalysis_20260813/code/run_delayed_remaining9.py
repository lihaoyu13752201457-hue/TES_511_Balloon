#!/usr/bin/env python3
"""Run the nine corrected delayed cells not covered by p/n/alpha recovery0002.

Source reduction and flux closure reuse the retained epsilon partial controller:
every fifth block from the 50,000-point exact-position source is retained, its
flux is multiplied by five, and an explicit 1e-6 keV spectrum is attached.
Transport uses eight concurrent Cosima workers.  Semantic SIM parsing is left
to the 03 delayed analysis so the large files are read only once.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
ROOT = check_inputs.ROOT
RETAINED_RUNNER = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code"
    / "run_epsilon_formal_partial_recovery0001.py"
)
RUN_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/state_aware_exactpos_v1"
)
OUTPUT = RUN_ROOT / "m05_corrected_delayed_remaining9_v1"
PLAN = OUTPUT / "transport_jobs.json"
SUMMARY = OUTPUT / "transport_summary.json"

FAMILIES = ("gamma", "eminus", "muminus", "eplus", "muplus")
WORKERS = 8
SEEDS = {
    "gamma": 2_071_010_001,
    "eminus": 2_071_110_001,
    "muminus": 2_071_210_001,
    "eplus": 2_071_310_001,
    "muplus": 2_071_410_001,
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


IMPL = load_module("m05_retained_epsilon_delayed_controller", RETAINED_RUNNER)
IMPL.RECOVERY_ROOT = OUTPUT
IMPL.RECOVERY_PLAN = PLAN
IMPL.RECOVERY_SUMMARY = SUMMARY
IMPL.FAMILIES = FAMILIES
IMPL.OMITTED_FAMILIES = ("p", "n", "alpha")
IMPL.FRESH_MATCHED_SEEDS = SEEDS
IMPL.WORKERS = WORKERS


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def prepared_jobs() -> list[dict[str, Any]]:
    jobs = load_json(IMPL.ORIGINAL_PLAN)["jobs"]
    selected = [dict(row) for row in jobs if row["family"] in FAMILIES]
    selected.sort(key=lambda row: (FAMILIES.index(row["family"]), row["geometry"]))
    return selected


def prepare() -> dict[str, Any]:
    if OUTPUT.exists():
        return load_json(OUTPUT / "manifest.json")
    smoke = IMPL.require_smoke_pass()
    originals = prepared_jobs()
    if len(originals) != 9:
        raise RuntimeError(f"expected nine remaining positive cells, found {len(originals)}")
    staging = OUTPUT.with_name(f".{OUTPUT.name}.partial.{os.getpid()}")
    staging.mkdir(parents=True)
    try:
        jobs = [IMPL.build_job(staging, original) for original in originals]
        for job in jobs:
            job["job_id"] = f"m05_delayed_remaining_{job['family']}_{job['geometry']}"
            job["matched_geometry_seed_key"] = f"m05_corrected_delayed_remaining9_v1|{job['family']}"
        plan = {
            "schema_version": 1,
            "status": "READY__M05_CORRECTED_DELAYED_REMAINING9_NOT_LAUNCHED",
            "created_utc": now_utc(),
            "jobs": jobs,
            "job_count": len(jobs),
            "workers": WORKERS,
            "families": list(FAMILIES),
            "geometries": ["Mass_model_511", "S3d_O8"],
            "one_sided_cell": "S3d_O8/muplus; Mass_model_511/muplus has zero transportable activity",
            "selected_position_blocks_per_job": IMPL.RETAINED_BLOCKS,
            "retained_block_flux_scale": IMPL.POSITION_STRIDE,
            "triggers_per_job": IMPL.TRIGGERS,
            "total_requested_triggers": len(jobs) * IMPL.TRIGGERS,
            "epsilon_keV": IMPL.EPSILON_KEV,
            "matched_family_seeds": SEEDS,
            "epsilon_smoke_authority": smoke,
            "sum_flux_closure_by_job": [
                {"job_id": row["job_id"], **row["sum_flux_closure"]} for row in jobs
            ],
        }
        IMPL.atomic_json_once(staging / "transport_jobs.json", plan)
        manifest = {
            "schema_version": 1,
            "status": "PASS__M05_CORRECTED_DELAYED_REMAINING9_PREPARED__NOT_LAUNCHED",
            "created_utc": now_utc(),
            "controller": relative(HERE),
            "reused_source_builder": relative(RETAINED_RUNNER),
            "prepared_exactpos_plan": relative(IMPL.ORIGINAL_PLAN),
            "transport_jobs": relative(PLAN),
            "job_count": len(jobs),
            "workers": WORKERS,
            "transport_launched": False,
            "semantic_sim_scan_deferred_to_stage03": True,
            "authority_boundary": "CORRECTED_DELAYED_TRANSPORT_SCREENING_ONLY__NOT_COMMON_RESPONSE_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        IMPL.atomic_json_once(staging / "manifest.json", manifest)
        os.replace(staging, OUTPUT)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def run_one(job: dict[str, Any], environment: dict[str, str]) -> dict[str, Any]:
    partial = ROOT / job["attempt_partial_dir"]
    final = ROOT / job["attempt_final_dir"]
    partial.mkdir(parents=True, exist_ok=False)
    log_path = partial / "cosima.log"
    started = time.monotonic()
    with log_path.open("x", encoding="utf-8") as log:
        completed = subprocess.run(
            [str(IMPL.COSIMA), "-s", str(job["seed"]), str(ROOT / job["source"])],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment,
            check=False,
        )
    sim = ROOT / job["expected_sim"]
    status = "PASS" if completed.returncode == 0 and sim.is_file() and sim.stat().st_size > 0 else "FAIL"
    receipt = {
        "schema_version": 1,
        "status": status,
        "job": job,
        "returncode": completed.returncode,
        "wall_s": time.monotonic() - started,
        "sim_path": relative(sim) if sim.exists() else job["expected_sim"],
        "sim_bytes": sim.stat().st_size if sim.exists() else 0,
        "log_path": relative(log_path),
        "semantic_sim_scan": "DEFERRED_TO_STAGE03_SINGLE_PASS_ANALYSIS",
    }
    IMPL.atomic_json_once(partial / "receipt.json", receipt)
    if status == "PASS":
        os.replace(partial, final)
        receipt["sim_path"] = job["published_sim"]
        receipt["receipt_path"] = relative(final / "receipt.json")
    else:
        receipt["receipt_path"] = relative(partial / "receipt.json")
    return receipt


def run_transport() -> dict[str, Any]:
    if not PLAN.is_file():
        raise RuntimeError("run --prepare first")
    if SUMMARY.exists():
        raise FileExistsError(f"summary exists: {SUMMARY}")
    plan = load_json(PLAN)
    jobs = list(plan["jobs"])
    for job in jobs:
        if (ROOT / job["attempt_partial_dir"]).exists() or (ROOT / job["attempt_final_dir"]).exists():
            raise RuntimeError(f"write-once attempt already exists: {job['job_id']}")
    environment, environment_provenance = IMPL.BASE.clean_cosima_env()
    started = time.monotonic()
    receipts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(run_one, job, environment): job for job in jobs}
        for future in as_completed(futures):
            receipt = future.result()
            receipts.append(receipt)
            print(
                f"{receipt['status']} {receipt['job']['geometry']}/{receipt['job']['family']} "
                f"{receipt['sim_bytes']} bytes {receipt['wall_s']:.1f} s",
                flush=True,
            )
    receipts.sort(key=lambda row: (FAMILIES.index(row["job"]["family"]), row["job"]["geometry"]))
    passed = all(row["status"] == "PASS" for row in receipts) and len(receipts) == len(jobs)
    summary = {
        "schema_version": 1,
        "status": (
            "PASS__M05_CORRECTED_DELAYED_REMAINING9_TRANSPORT_PROCESS_COMPLETE__SEMANTIC_SCAN_DEFERRED"
            if passed else "FAIL__M05_CORRECTED_DELAYED_REMAINING9_TRANSPORT"
        ),
        "created_utc": now_utc(),
        "jobs": receipts,
        "passed_jobs": sum(row["status"] == "PASS" for row in receipts),
        "expected_jobs": len(jobs),
        "requested_triggers": len(jobs) * IMPL.TRIGGERS,
        "workers": WORKERS,
        "elapsed_s": time.monotonic() - started,
        "runtime_environment": environment_provenance,
        "semantic_sim_scan": "DEFERRED_TO_STAGE03_SINGLE_PASS_ANALYSIS",
        "authority_boundary": "PROCESS_COMPLETE_CORRECTED_DELAYED_SCREENING_TRANSPORT__NOT_YET_STAGE03_SEMANTIC_OR_RESPONSE_AUTHORITY",
    }
    IMPL.atomic_json_once(SUMMARY, summary)
    if not passed:
        raise RuntimeError("one or more delayed jobs failed; see transport_summary.json")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--run-transport", action="store_true")
    parser.add_argument("--execute-transport", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        payload = prepare()
    else:
        if not args.execute_transport:
            raise SystemExit("--run-transport requires --execute-transport")
        payload = run_transport()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
