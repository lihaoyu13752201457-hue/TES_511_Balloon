#!/usr/bin/env python3
"""Prepare smoke and run a time-bounded adaptive OptV3 transport campaign."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import importlib.util
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[2]
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
RUNNER = EXECUTOR / "run.py"
SETUP = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup"
SURFACE_RECEIPT = PACKAGE / "audit/source_surface_60cm_validation.json"
SOURCE_ROOT = REPO / "engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8"
SOURCE_CONTRACT = REPO / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
SOURCE_STATIC = REPO / "engineering/particle_source_unit_repair_20260811/data/static_validation.json"
OPT_GEO = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.geo"
OPT_DET = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.det"
OPT_STATIC = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/audit/assembly_opt_v3_static_validation.json"
OPT_OVERLAP = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/audit/assembly_opt_v3_overlap_validation.json"
LINE_ROOT = REPO / "engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810"
LINE_FRAGMENT = LINE_ROOT / "line/PARMA_atm511_day15_fullsphere_80bins.inc.source"
LINE_CONTRACT = LINE_ROOT / "transport/line_only_transport_contract.json"
LINE_ENERGY_KEV = 510.99895
LINE_FLUX_4PI = 0.16651547160226118
SG3_INITIAL_PLAN = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/job_plan.json")
SG3_EXTRA_PLAN = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/sg3b_plan1_extra2x_v1/job_plan.json")
PARMA_FULL_EVENTS = [50_000] + [250_000] * 11 + [200_000]
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
SMOKE_EVENTS = {"p": 23, "n": 96, "alpha": 2, "gamma": 1000, "eminus": 41, "eplus": 24, "muminus": 1, "muplus": 1}
# Conservative 60 cm starting rates derived from the completed 95 cm receipts
# and reduced by the observed source-area ratio.  Every completed cycle replaces
# these values with measured 60 cm events/wall-second.
INITIAL_RATES = {"p": 47.0, "n": 335.0, "alpha": 11.0, "gamma": 1095.0, "eminus": 413.0, "eplus": 119.0, "muminus": 130.0, "muplus": 61.0}
INITIAL_PARMA_RATE = 2700.0
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"
STATE_LOCK = threading.Lock()
CHILDREN_LOCK = threading.Lock()
CHILDREN: set[subprocess.Popen[Any]] = set()
STOP = threading.Event()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(partial, path)


def import_prepare():
    sys.path.insert(0, str(EXECUTOR))
    spec = importlib.util.spec_from_file_location("canonical_prepare_60cm", EXECUTOR / "prepare.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical prepare helper unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority() -> dict[str, Any]:
    required = (SETUP, SURFACE_RECEIPT, SOURCE_CONTRACT, SOURCE_STATIC, OPT_GEO, OPT_DET, OPT_STATIC, OPT_OVERLAP, LINE_FRAGMENT, LINE_CONTRACT)
    if any(not path.is_file() for path in required):
        raise RuntimeError("required authority file is missing")
    surface = load(SURFACE_RECEIPT)
    if surface.get("status") != "PASS__SH3_OPTV3_SG3B_60CM_SURFACE_ENCLOSES_MATERIAL":
        raise RuntimeError("60 cm surface validation is not PASS")
    if SETUP.read_text(encoding="utf-8").count("SurroundingSphere 60 5 0 9 60") != 1:
        raise RuntimeError("setup source-surface contract drift")
    if load(SOURCE_STATIC).get("status") != "PASS":
        raise RuntimeError("corrected-keV static validation is not PASS")
    line = load(LINE_CONTRACT)
    if line.get("line_energy_keV") != LINE_ENERGY_KEV or not math.isclose(float(line.get("physical_4pi_flux_ph_cm2_s", -1)), LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError("PARMA511 line contract drift")
    return {
        "setup_path": str(SETUP), "setup_sha256": sha256(SETUP),
        "surface_receipt": str(SURFACE_RECEIPT), "surface_receipt_sha256": sha256(SURFACE_RECEIPT),
        "geo_path": str(OPT_GEO), "geo_sha256": sha256(OPT_GEO),
        "det_path": str(OPT_DET), "det_sha256": sha256(OPT_DET),
        "detector_contract": "6 TES MDCalorimeter + 3 BGO Scintillator; passive volumes remain transport mass",
        "source_contract": str(SOURCE_CONTRACT), "source_contract_sha256": sha256(SOURCE_CONTRACT),
        "source_surface": "60 5 0 9 60",
    }


def occupied_seeds(canonical) -> set[int]:
    config = load(EXECUTOR / "config.json")
    occupied, _ = canonical.occupied_seeds(config)
    roots = [EXECUTOR / "generated", Path("/mnt/data/TES_Balloon_511_data/SH3")]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("seed_registry.json"):
            try:
                rows = load(path).get("seeds", [])
            except Exception:
                continue
            for row in rows:
                seed = row.get("seed") if isinstance(row, dict) else None
                if isinstance(seed, int) and seed > 0:
                    occupied.add(seed)
    return occupied


def parma_source(job_id: str, events: int, seed: int, output_prefix: Path) -> str:
    fragment = LINE_FRAGMENT.read_text(encoding="utf-8").replace("PARMA511Day15", job_id)
    text = "\n".join([
        "# SH3 OptV3 60 cm standalone PARMA atmospheric 511-keV sidecar.",
        "# NON_ADDITIVE_SIDECAR: do not add to unit_only_total_gamma.",
        f"Geometry {SETUP}", "PhysicsListHD qgsp-bic-hp", "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all", "StoreIsotopes false", "DetectorTimeConstant 1e-9", f"Seed {seed}", "",
        f"Run {job_id}", f"{job_id}.Events {events}", f"{job_id}.FileName {output_prefix}", "", fragment.rstrip(), "",
    ])
    if text.count(f"{job_id}.Source ") != 80 or text.count(".Spectrum Mono 510.99895") != 80:
        raise RuntimeError("PARMA511 80-bin binding drift")
    flux = sum(float(line.rsplit(maxsplit=1)[-1]) for line in text.splitlines() if ".Flux " in line and not line.lstrip().startswith("#"))
    if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError("PARMA511 flux drift")
    return text


def build_bundle(kind: str, bundle: Path, specs: list[dict[str, Any]], canonical, occupied: set[int], auth: dict[str, Any]) -> Path:
    if bundle.exists():
        raise FileExistsError(f"non-overwrite cycle gate: {bundle}")
    generated = bundle / "generated"
    sources = generated / "sources"
    run_root = bundle / "run"
    sources.mkdir(parents=True)
    run_root.mkdir(parents=True)
    profile = f"SH3_OPTV3_60CM_{kind.upper()}_{bundle.parent.name}_{bundle.name}_20260818"
    jobs = []
    seed_rows = []
    source_rows = []
    for ordinal, spec in enumerate(specs, 1):
        family = spec["family"]
        mode = str(spec.get("mode", "instant" if kind == "corrected" else "atm511"))
        job_id = spec["job_id"]
        events = int(spec["events"])
        seed = canonical.derive_seed(profile, job_id, occupied)
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        source_path = sources / f"{job_id}.source"
        if kind == "corrected":
            base = SOURCE_ROOT / f"Background_{family}_fullsphere20.source"
            text = canonical.patch_source(
                base.read_text(encoding="utf-8"), setup=SETUP, output_prefix=output_prefix,
                job_id=job_id, run_name=job_id, mode=mode, seed=seed, events=events,
                config={"corrected_token": CORRECTED_TOKEN, "forbidden_legacy_token": FORBIDDEN_TOKEN},
            )
            if text.count(CORRECTED_TOKEN) != 20 or FORBIDDEN_TOKEN in text:
                raise RuntimeError(f"corrected source contract failed: {job_id}")
            requires_dat = True
        else:
            text = parma_source(job_id, events, seed, output_prefix)
            requires_dat = False
        source_path.write_text(text, encoding="utf-8")
        job = {
            "candidate": "SH3_OptV3_60cm", "estimated_bytes": max(256 * 1024**2, events * (2500 if kind == "corrected" else 700)),
            "events": events, "family": family, "job_id": job_id, "mode": mode,
            "ordinal": ordinal, "output_prefix": str(output_prefix), "production_canary": bool(spec.get("canary")),
            "requires_isotope_dat": requires_dat, "seed": seed, "setup_path": str(SETUP), "source_path": str(source_path), "stage": "background",
        }
        jobs.append(job)
        seed_rows.append({"job_id": job_id, "seed": seed, "namespace": profile})
        source_rows.append({
            "job_id": job_id, "mode": job["mode"], "family": family, "events": events, "seed": seed,
            "source_path": str(source_path), "setup_path": str(SETUP), "source_sha256": sha256(source_path),
            "source_surface": "60 5 0 9 60", "composition": "NON_ADDITIVE_SIDECAR" if kind == "parma511" else "unit_only_total_gamma_and_particle_family",
        })
    if sum(job["production_canary"] for job in jobs) != 1:
        raise RuntimeError("bundle must contain exactly one canary")
    totals = {
        "jobs": len(jobs),
        "instant_histories": sum(job["events"] for job in jobs if job["mode"] == "instant"),
        "buildup_histories": sum(job["events"] for job in jobs if job["mode"] == "buildup"),
    }
    plan = {"schema_version": 1, "profile_id": profile, "candidate": "SH3_OptV3_60cm", "status": "PASS", "jobs": jobs, "totals": totals}
    seed_status = "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS"
    source_status = "PASS__SH3_OPTV3_60CM_CORRECTED_INSTANT_SOURCES" if kind == "corrected" else "PASS__SH3_OPTV3_60CM_PARMA511_SOURCES"
    preflight_status = "PASS__SH3_OPTV3_60CM_CORRECTED_INSTANT_PREFLIGHT" if kind == "corrected" else "PASS__SH3_OPTV3_60CM_PARMA511_PREFLIGHT"
    atomic_dump(generated / "job_plan.json", plan)
    atomic_dump(generated / "seed_registry.json", {"schema_version": 1, "profile_id": profile, "status": seed_status, "seeds": seed_rows})
    atomic_dump(generated / "source_manifest.json", {"schema_version": 1, "profile_id": profile, "status": source_status, "sources": source_rows, "authority": auth})
    atomic_dump(generated / "preflight.json", {"schema_version": 1, "profile_id": profile, "candidate": "SH3_OptV3_60cm", "status": preflight_status, "job_plan": totals, "authority": auth})
    config = {
        "schema_version": 1, "profile_id": profile, "candidate": "SH3_OptV3_60cm", "display_title": f"SH3 OptV3 60 cm {kind} {bundle.name}",
        "generated_root": str(generated), "run_root": str(run_root), "geometry_setup": str(SETUP), "allowed_stages": ["background"],
        "expected_jobs": len(jobs), "expected_instant_histories": totals["instant_histories"], "expected_buildup_histories": totals["buildup_histories"],
        "canary_job_id": next(job["job_id"] for job in jobs if job["production_canary"]),
        "workers": 6 if kind == "corrected" else 2, "max_workers": 8, "max_attempts": 2,
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima", "cosima_workdir": str(REPO),
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh", "poll_seconds": 2.0, "progress_interval_seconds": 2.0,
        "start_free_bytes": 30 * 1024**3, "dynamic_reserve_bytes": 20 * 1024**3,
        "launch_mem_available_bytes": 1200 * 1024**2, "runtime_mem_floor_bytes": 700 * 1024**2,
        "launch_swap_free_bytes": 3 * 1024**3, "runtime_swap_floor_bytes": 1 * 1024**3,
        "launch_worker_reservation_bytes": 850 * 1024**2, "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0, "runtime_memory_full_psi_avg10_max": 100.0,
        "source_policy": "corrected_keV_background" if kind == "corrected" else "standalone_parma511_mono_line_80bin",
        "corrected_token": CORRECTED_TOKEN, "forbidden_legacy_token": FORBIDDEN_TOKEN,
        "seed_registry_pass_status": seed_status, "source_manifest_pass_status": source_status, "preflight_pass_status": preflight_status,
    }
    atomic_dump(bundle / "config.json", config)
    return bundle / "config.json"


def smoke_specs(kind: str) -> list[dict[str, Any]]:
    if kind == "corrected":
        ordered = ("gamma", "p", "n", "alpha", "eminus", "eplus", "muminus", "muplus")
        return [{"job_id": f"optv3_60cm_smoke_instant_{family}", "family": family, "events": SMOKE_EVENTS[family], "canary": index == 0} for index, family in enumerate(ordered)]
    return [{"job_id": "optv3_60cm_smoke_parma511", "family": "parma511", "events": 1000, "canary": True}]


def prepare_smoke(root: Path) -> None:
    if root.exists():
        raise FileExistsError(f"non-overwrite smoke gate: {root}")
    canonical = import_prepare()
    auth = authority()
    occupied = occupied_seeds(canonical)
    root.mkdir(parents=True)
    corrected = build_bundle("corrected", root / "corrected_kev", smoke_specs("corrected"), canonical, occupied, auth)
    parma = build_bundle("parma511", root / "parma511", smoke_specs("parma511"), canonical, occupied, auth)
    atomic_dump(root / "PREPARATION_RECEIPT.json", {"schema_version": 1, "status": "PASS__SH3_OPTV3_60CM_SMOKE_PREPARED", "prepared_at": utc_now(), "corrected_config": str(corrected), "parma511_config": str(parma), "authority": auth})


def run_config(config: Path, workers: int, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("x", encoding="utf-8", buffering=1) as handle:
        process = subprocess.Popen([sys.executable, str(RUNNER), "--config", str(config), "--workers", str(workers)], cwd=REPO, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        with CHILDREN_LOCK:
            CHILDREN.add(process)
        try:
            code = process.wait()
        finally:
            with CHILDREN_LOCK:
                CHILDREN.discard(process)
        if code != 0:
            raise RuntimeError(f"canonical runner failed ({code}): {config}")


def run_smoke(root: Path) -> None:
    threads = [
        threading.Thread(target=run_config, args=(root / "corrected_kev/config.json", 6, root / "corrected_kev/runner.log")),
        threading.Thread(target=run_config, args=(root / "parma511/config.json", 2, root / "parma511/runner.log")),
    ]
    errors: list[str] = []
    def guarded(thread_index: int) -> None:
        try:
            run_config(
                root / ("corrected_kev/config.json" if thread_index == 0 else "parma511/config.json"),
                6 if thread_index == 0 else 2,
                root / ("corrected_kev/runner.log" if thread_index == 0 else "parma511/runner.log"),
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    threads = [threading.Thread(target=guarded, args=(index,), daemon=False) for index in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    if errors: raise RuntimeError("; ".join(errors))
    counts = {}
    for name in ("corrected_kev", "parma511"):
        state = load(root / name / "run/controller_state.json")
        if state.get("status") != "COMPLETE": raise RuntimeError(f"smoke controller incomplete: {name}")
        counts[name] = state.get("completed_count")
    atomic_dump(root / "SMOKE_VALIDATION.json", {"schema_version": 1, "status": "PASS__SH3_OPTV3_60CM_INSTANT_SMOKE", "validated_at": utc_now(), "completed_jobs": counts})


def full_round_specs(kind: str, round_index: int, scale: float) -> list[dict[str, Any]]:
    """Return one complete fresh-seed transport unit at the requested scale."""
    if kind == "parma511":
        rows = []
        for index, base_events in enumerate(PARMA_FULL_EVENTS, 1):
            rows.append({
                "job_id": f"r{round_index:03d}_parma511_shard{index:04d}",
                "family": "parma511", "mode": "atm511",
                "events": max(1000, int(round(base_events * scale))),
                "canary": index == 1,
            })
        return rows
    rows = []
    ordinal = 0
    for batch, path in (("initial", SG3_INITIAL_PLAN), ("extra2x", SG3_EXTRA_PLAN)):
        for source in load(path)["jobs"]:
            if batch == "initial" and source["mode"] == "buildup" and source["family"] == "alpha":
                continue
            ordinal += 1
            events = max(SMOKE_EVENTS[source["family"]], int(round(int(source["events"]) * scale)))
            rows.append({
                "job_id": f"r{round_index:03d}_{batch}_{source['mode']}_{source['family']}_shard{int(source['shard']):04d}",
                "family": source["family"], "mode": source["mode"], "events": events,
                "canary": source["mode"] == "instant" and source["family"] == "gamma" and int(source["shard"]) == 1 and batch == "initial",
                "canonical_source_job_id": source["job_id"], "ordinal": ordinal,
            })
    if len(rows) != 41:
        raise RuntimeError("corrected full-round matrix is not 41 jobs")
    return rows


def _scan_rpip(receipt: dict[str, Any]) -> dict[str, Any]:
    count = 0
    malformed = 0
    volumes: set[str] = set()
    with gzip.open(receipt["sim_path"], "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.startswith("CC IP RP "):
                continue
            fields = raw.split()
            if len(fields) < 11:
                malformed += 1
                continue
            try:
                xyz = tuple(float(fields[index]) for index in (4, 5, 6))
                za = int(fields[7]); excitation = float(fields[8])
                if not all(math.isfinite(value) for value in (*xyz, excitation)) or za <= 0:
                    raise ValueError
            except ValueError:
                malformed += 1
                continue
            volumes.add(fields[3]); count += 1
    return {"job_id": receipt["job_id"], "count": count, "malformed": malformed, "volumes": sorted(volumes)}


def validate_activation_positions(bundle: Path) -> dict[str, Any]:
    receipts = [load(path) for path in sorted((bundle / "run/receipts").glob("*.json"))]
    buildup = [row for row in receipts if row.get("mode") == "buildup"]
    expected_instances = 0.0
    dat_rows = 0
    for receipt in buildup:
        with Path(receipt["isotope_dat_path"]).open(encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                if raw.startswith("RP "):
                    fields = raw.split(); dat_rows += 1; expected_instances += float(fields[3])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        scans = list(pool.map(_scan_rpip, buildup))
    observed = sum(row["count"] for row in scans)
    malformed = sum(row["malformed"] for row in scans)
    payload = {
        "schema_version": 1,
        "status": "PASS__BUILDUP_CC_IP_RP_MATCHES_DAT" if malformed == 0 and math.isclose(observed, expected_instances, rel_tol=0, abs_tol=1e-9) else "FAIL",
        "validated_at": utc_now(), "buildup_jobs": len(buildup), "DAT_RP_rows": dat_rows,
        "DAT_sum_RP_instances": expected_instances, "SIM_CC_IP_RP_instances": observed,
        "malformed_CC_IP_RP": malformed, "unique_physical_volumes": len({volume for row in scans for volume in row["volumes"]}),
        "jobs": scans,
        "contract": "exact positions are global MCSteppingAction CC IP RP records and do not require SensitiveVolume",
    }
    atomic_dump(bundle / "ACTIVATION_POSITION_VALIDATION.json", payload)
    if not payload["status"].startswith("PASS"):
        raise RuntimeError(f"activation exact-position validation failed: {bundle}")
    return payload


def run_full_adaptive(root: Path, hours: float) -> None:
    """Run full corrected+PARMA rounds, scaling repeats to a wall-time budget."""
    if root.exists():
        raise FileExistsError(f"non-overwrite full-adaptive gate: {root}")
    if not str(root.resolve()).startswith("/mnt/data/"):
        raise RuntimeError("full-adaptive output must be below /mnt/data")
    canonical = import_prepare()
    auth = authority()
    occupied = occupied_seeds(canonical)
    root.mkdir(parents=True)
    start_mono = time.monotonic()
    duration_s = hours * 3600.0
    deadline = start_mono + duration_s
    state_path = root / "adaptive_state.json"
    state: dict[str, Any] = {
        "schema_version": 1, "status": "RUNNING", "started_at": utc_now(),
        "duration_target_s": duration_s, "source_surface": "60 5 0 9 60",
        "worker_contract": {"corrected": 6, "parma511": 2, "total": 8},
        "round_definition": "41 corrected jobs (22 INSTANT + 19 BUILDUP) plus 13 standalone PARMA511 jobs",
        "first_round_targets": {"corrected_jobs": 41, "instant_events": 3_842_079, "buildup_events": 3_045_028, "parma511_jobs": 13, "parma511_events": 3_000_000},
        "authority": auth, "rounds_completed": 0, "rounds": [],
        "profiles": {
            "corrected": {"status": "STARTING", "current_cycle_config": None, "jobs_completed": 0, "events_completed": 0, "artifact_bytes": 0},
            "parma511": {"status": "STARTING", "current_cycle_config": None, "jobs_completed": 0, "events_completed": 0, "artifact_bytes": 0},
        },
    }
    update_master(state_path, state)
    round_index = 0
    scale = 1.0
    previous_round_wall = None
    errors: list[str] = []
    while not STOP.is_set():
        remaining = deadline - time.monotonic()
        if round_index > 0:
            if remaining < 90.0:
                break
            assert previous_round_wall is not None
            # Preserve the complete 54-job matrix and scale every cell together.
            # Startup/validation overhead is allowed 45 s; the 0.90 factor leaves
            # room to drain the last jobs rather than terminating them at deadline.
            scale = min(2.0, max(0.01, 0.90 * max(1.0, remaining - 45.0) / previous_round_wall))
        round_index += 1
        round_root = root / "rounds" / f"round{round_index:03d}"
        corrected_config = build_bundle("corrected", round_root / "corrected", full_round_specs("corrected", round_index, scale), canonical, occupied, auth)
        parma_config = build_bundle("parma511", round_root / "parma511", full_round_specs("parma511", round_index, scale), canonical, occupied, auth)
        with STATE_LOCK:
            state["current_round"] = round_index; state["current_round_scale"] = scale
            state["profiles"]["corrected"].update(status="RUNNING", current_cycle_config=str(corrected_config))
            state["profiles"]["parma511"].update(status="RUNNING", current_cycle_config=str(parma_config))
            state["updated_at"] = utc_now(); atomic_dump(state_path, state)
        started = time.monotonic()
        round_errors: list[str] = []
        def guarded(config: Path, workers: int, log_path: Path, name: str) -> None:
            try: run_config(config, workers, log_path)
            except Exception as exc: round_errors.append(f"{name}: {type(exc).__name__}: {exc}")
        threads = [
            threading.Thread(target=guarded, args=(corrected_config, 6, round_root / "corrected/runner.log", "corrected")),
            threading.Thread(target=guarded, args=(parma_config, 2, round_root / "parma511/runner.log", "parma511")),
        ]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        if round_errors:
            errors.extend(round_errors); break
        activation = validate_activation_positions(round_root / "corrected")
        round_wall = time.monotonic() - started
        previous_round_wall = round_wall
        round_entry: dict[str, Any] = {"round": round_index, "scale": scale, "wall_s": round_wall, "profiles": {}, "activation_position_validation": str(round_root / "corrected/ACTIVATION_POSITION_VALIDATION.json")}
        for name in ("corrected", "parma511"):
            bundle = round_root / name
            receipts = [load(path) for path in sorted((bundle / "run/receipts").glob("*.json"))]
            events = sum(row["events"] for row in receipts); size = sum(row["artifact_bytes"] for row in receipts)
            round_entry["profiles"][name] = {"jobs": len(receipts), "events": events, "artifact_bytes": size}
            state["profiles"][name]["jobs_completed"] += len(receipts)
            state["profiles"][name]["events_completed"] += events
            state["profiles"][name]["artifact_bytes"] += size
            state["profiles"][name]["status"] = "ROUND_COMPLETE"
            state["profiles"][name]["current_cycle_config"] = None
        round_entry["activation_counts"] = {"DAT_sum_RP_instances": activation["DAT_sum_RP_instances"], "SIM_CC_IP_RP_instances": activation["SIM_CC_IP_RP_instances"]}
        with STATE_LOCK:
            state["rounds_completed"] = round_index; state["rounds"].append(round_entry)
            state["updated_at"] = utc_now(); atomic_dump(state_path, state)
    elapsed = time.monotonic() - start_mono
    with STATE_LOCK:
        state["status"] = "FAILED" if errors else "COMPLETE_TIME_BUDGET_DRAINED"
        state["errors"] = errors; state["ended_at"] = utc_now(); state["elapsed_wall_s"] = elapsed
        state["total_jobs_completed"] = sum(row["jobs_completed"] for row in state["profiles"].values())
        state["total_events_completed"] = sum(row["events_completed"] for row in state["profiles"].values())
        state["total_artifact_bytes"] = sum(row["artifact_bytes"] for row in state["profiles"].values())
        state["updated_at"] = utc_now(); atomic_dump(state_path, state)
    if errors:
        raise RuntimeError("; ".join(errors))


def update_master(path: Path, state: dict[str, Any]) -> None:
    with STATE_LOCK:
        state["updated_at"] = utc_now()
        atomic_dump(path, state)


def cycle_specs(kind: str, cycle: int, rates: dict[str, float], target_s: float) -> list[dict[str, Any]]:
    if kind == "corrected":
        specs = [{"job_id": f"c{cycle:04d}_canary_gamma", "family": "gamma", "events": 1000, "canary": True, "main": False}]
        for family in FAMILIES:
            minimum = max(SMOKE_EVENTS[family] * 10, 10)
            events = max(minimum, int(round(rates[family] * target_s)))
            specs.append({"job_id": f"c{cycle:04d}_instant_{family}", "family": family, "events": events, "canary": False, "main": True})
        return specs
    events = max(50_000, int(round(rates["parma511"] * target_s)))
    return [
        {"job_id": f"c{cycle:04d}_canary_parma511", "family": "parma511", "events": 1000, "canary": True, "main": False},
        {"job_id": f"c{cycle:04d}_parma511_a", "family": "parma511", "events": events, "canary": False, "main": True},
        {"job_id": f"c{cycle:04d}_parma511_b", "family": "parma511", "events": events, "canary": False, "main": True},
    ]


def profile_loop(kind: str, root: Path, deadline: float, canonical, occupied: set[int], auth: dict[str, Any], state_path: Path, master: dict[str, Any]) -> None:
    rates = dict(INITIAL_RATES) if kind == "corrected" else {"parma511": INITIAL_PARMA_RATE}
    workers = 6 if kind == "corrected" else 2
    waves = 2.25 if kind == "corrected" else 1.25
    cycle = 0
    while not STOP.is_set():
        remaining = deadline - time.monotonic()
        target_s = min(90.0, (remaining - 25.0) / waves)
        if target_s < 12.0:
            break
        cycle += 1
        specs = cycle_specs(kind, cycle, rates, target_s)
        bundle = root / kind / "cycles" / f"cycle{cycle:04d}"
        config = build_bundle(kind, bundle, specs, canonical, occupied, auth)
        with STATE_LOCK:
            profile_state = master["profiles"][kind]
            profile_state.update(status="RUNNING", current_cycle=cycle, current_cycle_config=str(config), target_job_wall_s=target_s, rates_events_per_wall_s=rates)
            master["updated_at"] = utc_now()
            atomic_dump(state_path, master)
        started = time.monotonic()
        run_config(config, workers, bundle / "runner.log")
        elapsed = time.monotonic() - started
        receipts = [load(path) for path in sorted((bundle / "run/receipts").glob("*.json"))]
        if len(receipts) != len(specs) or any(row.get("status") != "PASS" for row in receipts):
            raise RuntimeError(f"cycle receipt closure failed: {bundle}")
        by_id = {row["job_id"]: row for row in receipts}
        measured: dict[str, list[float]] = {}
        for spec in specs:
            if not spec.get("main"): continue
            receipt = by_id[spec["job_id"]]
            rate = receipt["events"] / max(float(receipt["wall_s"]), 1e-9)
            measured.setdefault(spec["family"], []).append(rate)
        for family, values in measured.items():
            observed = sum(values) / len(values)
            rates[family] = 0.35 * rates[family] + 0.65 * observed
        cycle_events = sum(row["events"] for row in receipts)
        cycle_bytes = sum(row["artifact_bytes"] for row in receipts)
        with STATE_LOCK:
            profile_state = master["profiles"][kind]
            profile_state["cycles_completed"] += 1
            profile_state["jobs_completed"] += len(receipts)
            profile_state["events_completed"] += cycle_events
            profile_state["artifact_bytes"] += cycle_bytes
            profile_state["last_cycle_wall_s"] = elapsed
            profile_state["rates_events_per_wall_s"] = dict(rates)
            profile_state["cycle_history"].append({"cycle": cycle, "wall_s": elapsed, "events": cycle_events, "artifact_bytes": cycle_bytes, "target_job_wall_s": target_s, "bundle": str(bundle)})
            master["updated_at"] = utc_now()
            atomic_dump(state_path, master)
    with STATE_LOCK:
        master["profiles"][kind]["status"] = "COMPLETE_TIME_BUDGET_DRAINED"
        master["profiles"][kind]["current_cycle_config"] = None
        master["updated_at"] = utc_now()
        atomic_dump(state_path, master)


def request_stop(_signum: int, _frame: Any) -> None:
    STOP.set()
    with CHILDREN_LOCK:
        children = list(CHILDREN)
    for process in children:
        if process.poll() is None:
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass


def run_adaptive(root: Path, hours: float) -> None:
    if root.exists(): raise FileExistsError(f"non-overwrite adaptive gate: {root}")
    if not str(root.resolve()).startswith("/mnt/data/"):
        raise RuntimeError("adaptive output must be below /mnt/data")
    canonical = import_prepare()
    auth = authority()
    occupied = occupied_seeds(canonical)
    root.mkdir(parents=True)
    started_monotonic = time.monotonic()
    duration_s = hours * 3600.0
    deadline = started_monotonic + duration_s
    state_path = root / "adaptive_state.json"
    master: dict[str, Any] = {
        "schema_version": 1, "status": "RUNNING", "started_at": utc_now(), "duration_target_s": duration_s,
        "deadline_monotonic": deadline, "worker_contract": {"corrected": 6, "parma511": 2, "total": 8},
        "source_surface": "60 5 0 9 60", "authority": auth,
        "profiles": {
            kind: {"status": "STARTING", "current_cycle": 0, "current_cycle_config": None, "cycles_completed": 0, "jobs_completed": 0, "events_completed": 0, "artifact_bytes": 0, "cycle_history": []}
            for kind in ("corrected", "parma511")
        },
    }
    update_master(state_path, master)
    errors: list[str] = []
    def guarded(kind: str) -> None:
        try:
            profile_loop(kind, root, deadline, canonical, occupied, auth, state_path, master)
        except Exception as exc:
            STOP.set()
            errors.append(f"{kind}: {type(exc).__name__}: {exc}")
            with STATE_LOCK:
                master["profiles"][kind]["status"] = "FAILED"
                master["profiles"][kind]["error"] = str(exc)
                master["updated_at"] = utc_now()
                atomic_dump(state_path, master)
    threads = [threading.Thread(target=guarded, args=(kind,), daemon=False) for kind in ("corrected", "parma511")]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    elapsed = time.monotonic() - started_monotonic
    with STATE_LOCK:
        master["status"] = "FAILED" if errors else "COMPLETE_TIME_BUDGET_DRAINED"
        master["errors"] = errors
        master["ended_at"] = utc_now()
        master["elapsed_wall_s"] = elapsed
        master["total_jobs_completed"] = sum(profile["jobs_completed"] for profile in master["profiles"].values())
        master["total_events_completed"] = sum(profile["events_completed"] for profile in master["profiles"].values())
        master["total_artifact_bytes"] = sum(profile["artifact_bytes"] for profile in master["profiles"].values())
        master["updated_at"] = utc_now()
        atomic_dump(state_path, master)
    if errors: raise RuntimeError("; ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare-smoke"); p.add_argument("--root", type=Path, required=True)
    p = sub.add_parser("run-smoke"); p.add_argument("--root", type=Path, required=True)
    p = sub.add_parser("run-adaptive"); p.add_argument("--root", type=Path, required=True); p.add_argument("--hours", type=float, default=2.0)
    p = sub.add_parser("run-full-adaptive"); p.add_argument("--root", type=Path, required=True); p.add_argument("--hours", type=float, default=2.5)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    if args.command == "prepare-smoke": prepare_smoke(args.root.resolve())
    elif args.command == "run-smoke": run_smoke(args.root.resolve())
    elif args.command == "run-adaptive": run_adaptive(args.root.resolve(), args.hours)
    else: run_full_adaptive(args.root.resolve(), args.hours)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
