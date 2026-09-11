#!/usr/bin/env python3
"""Append-only corrected delayed partial-screening recovery.

Prerequisite: spectrum_epsilon_repair_smoke0001 must PASS in both geometries.
This controller then builds and, behind a separate gate, transports exactly
p/n/alpha x Mass_model_511/S3d_O8.  Each source deterministically selects
every fifth block from the original 50,000 sampled exact-position blocks
(10,000 retained), adds ``Spectrum Mono 1e-6`` keV to every retained ion,
rescales each equal block flux by five to preserve the cell's total activity,
and requests 250,000 triggers.  Seeds are fresh and matched by family across
the two geometries.  Six workers share a live 20-GiB reserve and 2-GB/job cap.

The result is corrected-keV delayed *partial screening transport* only.  It is
not full-family delayed response, mission sensitivity, paper closure, or a
geometry-promotion authority.  All invalid attempt01 artifacts remain
read-only and excluded.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
import shutil
import signal
import subprocess
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
IMPLEMENTATION_FILE = THIS_FILE
ROOT = THIS_FILE.parents[5]
SMOKE_FILE = THIS_FILE.with_name("build_and_run_spectrum_epsilon_smoke0001.py")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1"
PACKAGE_ROOT = RUN_ROOT / "delayed_phase02/state_aware_exactpos_v1"
ORIGINAL_PLAN = PACKAGE_ROOT / "transport_jobs.json"
SMOKE_SUMMARY = PACKAGE_ROOT / "spectrum_epsilon_repair_smoke0001/smoke_validation.json"
RECOVERY_ROOT = PACKAGE_ROOT / "spectrum_epsilon_formal_partial_recovery0001"
RECOVERY_PLAN = RECOVERY_ROOT / "formal_partial_jobs.json"
RECOVERY_SUMMARY = RECOVERY_ROOT / "formal_partial_validation.json"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")

GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("p", "n", "alpha")
OMITTED_FAMILIES = ("gamma", "eminus", "muminus", "eplus", "muplus")
ORIGINAL_BLOCKS = 50_000
POSITION_STRIDE = 5
RETAINED_BLOCKS = 10_000
TRIGGERS = 250_000
EPSILON_KEV = 1.0e-6
WORKERS = 6
RESERVE_BYTES = 20 * 1024**3
JOB_CAP_BYTES = 2_000_000_000
FRESH_MATCHED_SEEDS = {"p": 2_068_510_001, "n": 2_068_610_001, "alpha": 2_068_710_001}


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SMOKE = load_module(SMOKE_FILE, "epsilon_smoke0001_retained")
BASE = SMOKE.BASE


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"write-once target exists: {path}")
    partial = path.with_name(f".{path.name}.partial.{os.getpid()}")
    with partial.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def atomic_json_once(path: Path, payload: Any) -> None:
    atomic_text_once(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def require_smoke_pass() -> dict[str, Any]:
    if not SMOKE_SUMMARY.is_file():
        raise RuntimeError(f"epsilon smoke authority is missing: {SMOKE_SUMMARY}")
    payload = load_json(SMOKE_SUMMARY)
    if payload.get("status") != "PASS__EPSILON_MONO_TWO_GEOMETRY_SMOKE":
        raise RuntimeError(f"epsilon smoke is not PASS: {payload.get('status')}")
    if int(payload.get("passed_jobs", -1)) != 2 or float(payload.get("epsilon_keV", -1)) != EPSILON_KEV:
        raise RuntimeError("epsilon smoke coverage/energy binding mismatch")
    return {
        "path": rel(SMOKE_SUMMARY),
        "sha256": sha256(SMOKE_SUMMARY),
        "status": payload["status"],
        "passed_jobs": payload["passed_jobs"],
        "epsilon_keV": payload["epsilon_keV"],
    }


def selected_original_jobs() -> list[dict[str, Any]]:
    all_jobs = list(load_json(ORIGINAL_PLAN)["jobs"])
    by_key = {(row["geometry"], row["family"]): dict(row) for row in all_jobs}
    selected = []
    for family in FAMILIES:
        for geometry in GEOMETRIES:
            key = (geometry, family)
            if key not in by_key:
                raise RuntimeError(f"original prepared job missing: {key}")
            selected.append(by_key[key])
    if len(selected) != 6:
        raise AssertionError("formal recovery matrix must contain six cells")
    return selected


def parse_selected_blocks(path: Path) -> dict[str, Any]:
    geometry = ""
    original_triggers = None
    registrations = 0
    spectrum_lines = 0
    selected: dict[str, dict[str, str]] = {}
    all_flux_values: list[float] = []
    selected_flux_values: list[float] = []
    selected_indices = set(range(0, ORIGINAL_BLOCKS, POSITION_STRIDE))
    text = path.read_text(encoding="utf-8", errors="strict")
    for raw in text.splitlines():
        fields = raw.split(maxsplit=1)
        if not fields:
            continue
        key = fields[0]
        if key == "Geometry" and len(fields) == 2:
            geometry = fields[1].strip()
        elif key == "DecayRun.Triggers" and len(fields) == 2:
            original_triggers = int(fields[1])
        elif key == "DecayRun.Source" and len(fields) == 2:
            registrations += 1
        elif key.endswith(".Spectrum"):
            spectrum_lines += 1
        if key.startswith("RP_") and "." in key:
            name, field = key.split(".", 1)
            try:
                index = int(name.split("_", 1)[1])
            except ValueError:
                continue
            if field == "Flux" and len(fields) == 2:
                all_flux_values.append(float(fields[1]))
            if index in selected_indices:
                selected.setdefault(name, {})[field] = raw
                if field == "Flux" and len(fields) == 2:
                    selected_flux_values.append(float(fields[1]))
    required = {"ParticleType", "Beam", "Flux"}
    incomplete = {name: sorted(values) for name, values in selected.items() if set(values) != required}
    if (
        not geometry or original_triggers != 1_000_000 or registrations != ORIGINAL_BLOCKS
        or spectrum_lines != 0 or len(selected) != RETAINED_BLOCKS or incomplete
        or len(all_flux_values) != ORIGINAL_BLOCKS or len(selected_flux_values) != RETAINED_BLOCKS
    ):
        raise RuntimeError(
            f"prepared source contract failed {path}: geometry={geometry}, triggers={original_triggers}, "
            f"registrations={registrations}, spectra={spectrum_lines}, selected={len(selected)}, "
            f"all_flux={len(all_flux_values)}, selected_flux={len(selected_flux_values)}, "
            f"incomplete_first={list(incomplete.items())[:3]}"
        )
    return {
        "geometry": str(Path(geometry).resolve()),
        "selected": selected,
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "original_registrations": registrations,
        "original_spectrum_lines": spectrum_lines,
        "original_all_50000_sum_flux_Bq": math.fsum(all_flux_values),
        "selected_10000_original_sum_flux_Bq": math.fsum(selected_flux_values),
    }


def make_source(parsed: dict[str, Any], output_prefix: Path) -> str:
    names = [f"RP_{index:07d}" for index in range(0, ORIGINAL_BLOCKS, POSITION_STRIDE)]
    lines = [
        "Version 1", f"Geometry {parsed['geometry']}", "",
        "PhysicsListHD qgsp-bic-hp", "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true", "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all", "StoreIsotopes true", "DetectorTimeConstant 1e-9", "",
        "Run DecayRun", f"DecayRun.FileName {output_prefix.resolve()}",
        f"DecayRun.Triggers {TRIGGERS}", "",
    ]
    lines.extend(f"DecayRun.Source {name}" for name in names)
    lines.extend(("", "# Deterministic stride-5 subset of exact prepared RP blocks."))
    for name in names:
        values = parsed["selected"][name]
        lines.append(values["ParticleType"])
        lines.append(values["Beam"])
        lines.append(f"{name}.Spectrum Mono {EPSILON_KEV:.9g}")
        original_flux = float(values["Flux"].split(maxsplit=1)[1])
        lines.append(f"{name}.Flux {original_flux * POSITION_STRIDE:.12e}")
        lines.append("")
    text = "\n".join(lines) + "\n"
    if text.count("DecayRun.Source RP_") != RETAINED_BLOCKS:
        raise RuntimeError("recovery source registration count is not 10,000")
    if text.count(".ParticleType ") != RETAINED_BLOCKS or text.count(".Beam PointSource ") != RETAINED_BLOCKS:
        raise RuntimeError("recovery source particle/position count is not 10,000")
    if text.count(f".Spectrum Mono {EPSILON_KEV:.9g}") != RETAINED_BLOCKS:
        raise RuntimeError("not every recovery RP has explicit epsilon Mono")
    if text.count(".Flux ") != RETAINED_BLOCKS:
        raise RuntimeError("recovery source flux count is not 10,000")
    return text


def build_job(staging: Path, original: dict[str, Any]) -> dict[str, Any]:
    geometry, family = str(original["geometry"]), str(original["family"])
    parsed = parse_selected_blocks(ROOT / original["source"])
    partial = RECOVERY_ROOT / "transport" / geometry / family / ".attempt01.partial"
    final = partial.parent / "attempt01"
    prefix_name = f"EpsilonFormalPartial_{geometry}_{family}_M10000_N250000"
    prefix = partial / prefix_name
    source_name = f"epsilon_formal_partial_{geometry}_{family}_M10000.source"
    source = staging / "source_cards" / geometry / family / source_name
    source.parent.mkdir(parents=True, exist_ok=False)
    text = make_source(parsed, prefix)
    with source.open("x", encoding="utf-8") as handle:
        handle.write(text); handle.flush(); os.fsync(handle.fileno())
    original_sum_flux = float(parsed["original_all_50000_sum_flux_Bq"])
    selected_original_sum_flux = float(parsed["selected_10000_original_sum_flux_Bq"])
    recovery_sum_flux = selected_original_sum_flux * POSITION_STRIDE
    closure_abs = recovery_sum_flux - original_sum_flux
    closure_rel = closure_abs / original_sum_flux if original_sum_flux else float("inf")
    if not math.isclose(recovery_sum_flux, original_sum_flux, rel_tol=1.0e-10, abs_tol=1.0e-12):
        raise RuntimeError(
            f"stride-5 flux rescaling did not close for {geometry}/{family}: "
            f"original={original_sum_flux}, recovery={recovery_sum_flux}, rel={closure_rel}"
        )
    published_source = RECOVERY_ROOT / "source_cards" / geometry / family / source_name
    return {
        "job_id": f"epsilon_formal_partial_{family}_{geometry}",
        "geometry": geometry, "family": family,
        "seed": FRESH_MATCHED_SEEDS[family],
        "matched_geometry_seed_key": f"epsilon_formal_partial_recovery0001|{family}",
        "triggers": TRIGGERS, "epsilon_keV": EPSILON_KEV,
        "selected_position_blocks": RETAINED_BLOCKS,
        "selection_rule": "original_RP_index_mod_5_equals_0__indices_0_to_49995",
        "flux_rule": "each_retained_equal_flux_multiplied_by_5_to_preserve_total_activity",
        "sum_flux_closure": {
            "original_50000_sum_flux_Bq": original_sum_flux,
            "selected_10000_before_scale_sum_flux_Bq": selected_original_sum_flux,
            "recovery_10000_after_x5_sum_flux_Bq": recovery_sum_flux,
            "recovery_minus_original_Bq": closure_abs,
            "relative_difference": closure_rel,
            "status": "PASS",
        },
        "source": rel(published_source), "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "prepared_source": str(original["source"]),
        "prepared_source_sha256": parsed["source_sha256"],
        "expected_geometry": parsed["geometry"],
        "attempt_partial_dir": rel(partial), "attempt_final_dir": rel(final),
        "expected_sim": rel(prefix.with_suffix(".inc1.id1.sim.gz")),
        "published_sim": rel((final / prefix_name).with_suffix(".inc1.id1.sim.gz")),
        "declared_cap_bytes": JOB_CAP_BYTES,
    }


def prepare() -> dict[str, Any]:
    smoke = require_smoke_pass()
    if RECOVERY_ROOT.exists():
        manifest = RECOVERY_ROOT / "manifest.json"
        if not manifest.is_file():
            raise RuntimeError(f"recovery root exists without manifest: {RECOVERY_ROOT}")
        return load_json(manifest)
    staging = RECOVERY_ROOT.with_name(f".{RECOVERY_ROOT.name}.partial.{os.getpid()}")
    if staging.exists():
        raise FileExistsError(f"staging exists: {staging}")
    staging.mkdir(parents=True)
    jobs = [build_job(staging, row) for row in selected_original_jobs()]
    for family in FAMILIES:
        pair = [row for row in jobs if row["family"] == family]
        if len(pair) != 2 or len({row["seed"] for row in pair}) != 1:
            raise RuntimeError(f"matched geometry seed proof failed: {family}")
    plan = {
        "schema_version": 1,
        "status": "READY__EPSILON_FORMAL_PARTIAL_SCREENING_NOT_LAUNCHED",
        "created_utc": now_utc(), "jobs": jobs, "workers": WORKERS,
        "families": list(FAMILIES), "geometries": list(GEOMETRIES),
        "omitted_families": list(OMITTED_FAMILIES),
        "fresh_matched_family_seeds": FRESH_MATCHED_SEEDS,
        "original_position_blocks": ORIGINAL_BLOCKS, "position_stride": POSITION_STRIDE,
        "selected_position_blocks_per_job": RETAINED_BLOCKS,
        "retained_block_flux_scale": POSITION_STRIDE,
        "triggers_per_job": TRIGGERS, "epsilon_keV": EPSILON_KEV,
        "filesystem_reserve_bytes": RESERVE_BYTES, "declared_job_cap_bytes": JOB_CAP_BYTES,
        "epsilon_smoke_authority": smoke,
        "sum_flux_closure_by_job": [
            {"job_id": row["job_id"], **row["sum_flux_closure"]} for row in jobs
        ],
    }
    atomic_json_once(staging / "formal_partial_jobs.json", plan)
    manifest = {
        "schema_version": 1,
        "status": "PASS__EPSILON_FORMAL_PARTIAL_RECOVERY_PREPARED__NOT_LAUNCHED",
        "created_utc": now_utc(), "controller": rel(THIS_FILE),
        "controller_sha256": sha256(THIS_FILE),
        "implementation": rel(IMPLEMENTATION_FILE),
        "implementation_sha256": sha256(IMPLEMENTATION_FILE),
        "epsilon_smoke_authority": smoke,
        "original_transport_plan": rel(ORIGINAL_PLAN),
        "formal_partial_plan": rel(RECOVERY_PLAN),
        "job_count": 6, "total_requested_triggers": 6 * TRIGGERS,
        "sum_flux_closure_by_job": [
            {"job_id": row["job_id"], **row["sum_flux_closure"]} for row in jobs
        ],
        "invalid_attempt01_policy": "EXCLUDED_READ_ONLY_NO_SALVAGE_NO_MOVE_NO_DELETE",
        "transport_launched": False, "paper_closure_claimed": False,
        "authority_boundary": (
            "P_N_ALPHA_TWO_GEOMETRY_CORRECTED_DELAYED_PARTIAL_SCREENING_TRANSPORT_ONLY__"
            "NO_FULL_DELAYED_RESPONSE_MISSION_SENSITIVITY_PAPER_CLOSURE_OR_GEOMETRY_PROMOTION"
        ),
    }
    atomic_json_once(staging / "manifest.json", manifest)
    RECOVERY_ROOT.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, RECOVERY_ROOT)
    return manifest


def validate_sim(path: Path, job: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "FAIL", "problem": "missing_sim", "path": rel(path)}
    geometry = ""; seed = None; spectral = []; se = ids = en = 0
    id_sequence = True; init_count = 0; init_min = None; init_max = None
    two_mev = 0; deca_events: set[int] = set(); current_event = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                stripped = raw.strip(); fields = stripped.split()
                if not fields: continue
                tag = fields[0]
                if tag == "Geometry" and not geometry: geometry = " ".join(fields[1:])
                elif tag == "Seed" and seed is None: seed = int(fields[1])
                elif tag == "SpectralType": spectral.append(stripped)
                elif stripped == "SE": se += 1; current_event = se
                elif tag == "ID":
                    ids += 1
                    if len(fields) != 3 or int(fields[1]) != ids or int(fields[2]) != ids: id_sequence = False
                elif stripped == "EN": en += 1
                elif stripped.startswith("IA INIT"):
                    value = float(stripped.rsplit(";", 1)[1].strip()); init_count += 1
                    init_min = value if init_min is None else min(init_min, value)
                    init_max = value if init_max is None else max(init_max, value)
                    if abs(value - 2000.0) <= 0.0005: two_mev += 1
                elif stripped.startswith("IA DECA"): deca_events.add(current_event)
    except (OSError, EOFError, ValueError) as exc:
        return {"status": "FAIL", "problem": f"gzip_or_parse:{exc}", "path": rel(path), "gzip_eof": False}
    expected_spectral = f"SpectralType Mono {EPSILON_KEV:g}"
    problems = []
    if se != TRIGGERS or ids != TRIGGERS or en != 1 or not id_sequence: problems.append("SE_ID_EN_contract")
    if Path(geometry).resolve() != Path(job["expected_geometry"]).resolve(): problems.append("geometry")
    if seed != int(job["seed"]): problems.append("seed")
    if not spectral or any(row != expected_spectral for row in spectral): problems.append("SpectralType")
    if init_count != TRIGGERS or init_min is None or init_max is None or abs(init_min) > 0.0005001 or abs(init_max) > 0.0005001:
        problems.append("IA_INIT_epsilon")
    if two_mev: problems.append("2MeV_primary_artifact")
    if len(deca_events) != TRIGGERS: problems.append("IA_DECA_event_coverage")
    return {
        "status": "PASS" if not problems else "FAIL", "problem": None if not problems else ";".join(problems),
        "path": rel(path), "gzip_eof": True, "SE": se, "ID": ids, "EN": en,
        "ID_sequence_1_to_N": id_sequence, "geometry": str(Path(geometry).resolve()), "seed": seed,
        "spectral_lines": spectral, "expected_spectral_line": expected_spectral,
        "IA_INIT_count": init_count, "IA_INIT_energy_min_keV": init_min, "IA_INIT_energy_max_keV": init_max,
        "IA_INIT_2MeV_artifact_count": two_mev, "events_with_IA_DECA": len(deca_events),
    }


def disk_snapshot(active: dict[int, dict[str, Any]], candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    usage = [{
        "job_id": item["job"]["job_id"],
        "current_bytes": int(BASE.tree_bytes(ROOT / item["job"]["attempt_partial_dir"])),
        "cap_bytes": JOB_CAP_BYTES,
    } for item in active.values()]
    candidate_cap = JOB_CAP_BYTES if candidate is not None else 0
    result = BASE.disk_admission_decision(shutil.disk_usage(ROOT).free, usage, candidate_cap, RESERVE_BYTES)
    result["active_usage"] = usage
    result["candidate_job_id"] = candidate["job_id"] if candidate else None
    return result


def run_transport() -> dict[str, Any]:
    require_smoke_pass()
    if not RECOVERY_PLAN.is_file(): raise RuntimeError("run --prepare first")
    if RECOVERY_SUMMARY.exists(): raise FileExistsError(f"summary exists: {RECOVERY_SUMMARY}")
    plan = load_json(RECOVERY_PLAN); jobs_list = list(plan["jobs"])
    if len(jobs_list) != 6: raise RuntimeError("formal partial plan is not six cells")
    for job in jobs_list:
        partial, final = ROOT / job["attempt_partial_dir"], ROOT / job["attempt_final_dir"]
        if partial.exists() or final.exists(): raise RuntimeError(f"write-once attempt exists: {partial} or {final}")
    environment, env_provenance = BASE.clean_cosima_env()
    queue = deque(jobs_list); active: dict[int, dict[str, Any]] = {}; exited = []
    launches = []; minimum_free = shutil.disk_usage(ROOT).free; maximum_bytes: dict[str, int] = defaultdict(int)

    def observe(snapshot: dict[str, Any]) -> None:
        nonlocal minimum_free
        minimum_free = min(minimum_free, int(snapshot["free_bytes"]))
        for row in snapshot["active_usage"]:
            maximum_bytes[row["job_id"]] = max(maximum_bytes[row["job_id"]], int(row["current_bytes"]))

    def terminate() -> None:
        for item in active.values():
            try: os.killpg(item["process"].pid, signal.SIGTERM)
            except ProcessLookupError: pass

    while queue or active:
        guard = disk_snapshot(active); observe(guard)
        if active and not guard["admitted"]:
            terminate(); raise RuntimeError(f"live disk/cap guard stopped formal partial recovery: {guard}")
        while queue and len(active) < WORKERS:
            admission = disk_snapshot(active, queue[0]); observe(admission)
            if not admission["admitted"]: break
            job = queue.popleft(); partial = ROOT / job["attempt_partial_dir"]
            partial.mkdir(parents=True, exist_ok=False); log = (partial / "cosima.log").open("x", encoding="utf-8")
            process = subprocess.Popen(
                [str(COSIMA), "-s", str(job["seed"]), str(ROOT / job["source"])],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=environment,
            )
            active[process.pid] = {"job": job, "process": process, "log": log, "started": time.monotonic()}
            launches.append({**admission, "launched_job_id": job["job_id"], "pid": process.pid})
        if not active and queue:
            blocked = disk_snapshot(active, queue[0]); observe(blocked)
            raise RuntimeError(f"20-GiB admission blocks next job: {blocked}")
        time.sleep(1)
        for pid, item in list(active.items()):
            code = item["process"].poll()
            if code is None: continue
            item["log"].close(); item["returncode"] = code; item["wall_s"] = time.monotonic() - item["started"]
            exited.append(item); del active[pid]
            if code != 0:
                terminate(); raise RuntimeError(f"Cosima returncode {code}: {item['job']['job_id']}")

    receipts = []
    for item in exited:
        job = item["job"]; partial = ROOT / job["attempt_partial_dir"]; final = ROOT / job["attempt_final_dir"]
        sim_check = validate_sim(ROOT / job["expected_sim"], job)
        log_check = SMOKE.validate_log(partial / "cosima.log")
        observed = int(BASE.tree_bytes(partial))
        status = "PASS" if sim_check["status"] == "PASS" and log_check["status"] == "PASS" and observed <= JOB_CAP_BYTES else "FAIL"
        receipt = {
            "schema_version": 1, "status": status, "job": job,
            "returncode": item["returncode"], "wall_s": item["wall_s"],
            "observed_output_bytes_before_receipt": observed, "declared_cap_bytes": JOB_CAP_BYTES,
            "sim_validation": sim_check, "log_validation": log_check, "runtime_environment": env_provenance,
        }
        atomic_json_once(partial / "receipt.json", receipt)
        if status == "PASS": os.replace(partial, final)
        receipts.append(receipt)
    passed = len(receipts) == 6 and all(row["status"] == "PASS" for row in receipts)
    summary = {
        "schema_version": 1,
        "status": "PASS__EPSILON_FORMAL_PARTIAL_SCREENING_SIX_CELL_TRANSPORT" if passed else "FAIL__EPSILON_FORMAL_PARTIAL_SCREENING",
        "created_utc": now_utc(), "coverage_status": "PARTIAL_SCREENING__P_N_ALPHA_ONLY",
        "jobs": receipts, "passed_jobs": sum(row["status"] == "PASS" for row in receipts), "expected_jobs": 6,
        "total_validated_events": sum(row["sim_validation"].get("SE", 0) for row in receipts),
        "families": list(FAMILIES), "omitted_families": list(OMITTED_FAMILIES),
        "geometries": list(GEOMETRIES), "matched_family_seeds": FRESH_MATCHED_SEEDS,
        "selected_position_blocks_per_job": RETAINED_BLOCKS, "triggers_per_job": TRIGGERS,
        "retained_block_flux_scale": POSITION_STRIDE,
        "epsilon_keV": EPSILON_KEV,
        "sum_flux_closure_by_job": plan["sum_flux_closure_by_job"],
        "dynamic_disk_admission": {
            "policy": "live_free_minus_active_remaining_caps_minus_candidate_cap_ge_20GiB_reserve",
            "workers": WORKERS, "reserve_bytes": RESERVE_BYTES, "job_cap_bytes": JOB_CAP_BYTES,
            "minimum_observed_free_bytes": minimum_free, "launch_admissions": launches,
            "maximum_active_bytes_by_job": dict(sorted(maximum_bytes.items())),
        },
        "invalid_attempt01_included": False, "paper_closure_claimed": False,
        "authority_boundary": (
            "P_N_ALPHA_TWO_GEOMETRY_CORRECTED_DELAYED_PARTIAL_SCREENING_TRANSPORT_ONLY__"
            "NO_FULL_DELAYED_RESPONSE_MISSION_SENSITIVITY_PAPER_CLOSURE_OR_GEOMETRY_PROMOTION"
        ),
    }
    atomic_json_once(RECOVERY_SUMMARY, summary)
    if not passed: raise RuntimeError("formal partial recovery validation failed; see write-once summary")
    return summary


def print_plan() -> dict[str, Any]:
    smoke = require_smoke_pass()
    return {
        "status": "READY_TO_PREPARE" if not RECOVERY_ROOT.exists() else "RECOVERY_NAMESPACE_EXISTS",
        "controller": rel(THIS_FILE), "output": rel(RECOVERY_ROOT),
        "epsilon_smoke_authority": smoke, "families": list(FAMILIES), "geometries": list(GEOMETRIES),
        "jobs": 6, "workers": WORKERS, "original_positions": ORIGINAL_BLOCKS,
        "deterministic_stride": POSITION_STRIDE, "selected_positions_per_job": RETAINED_BLOCKS,
        "retained_block_flux_scale": POSITION_STRIDE,
        "triggers_per_job": TRIGGERS, "total_triggers": 6 * TRIGGERS,
        "epsilon_keV": EPSILON_KEV, "fresh_matched_family_seeds": FRESH_MATCHED_SEEDS,
        "reserve_bytes": RESERVE_BYTES, "job_cap_bytes": JOB_CAP_BYTES,
        "formal_transport_launched": False, "claim": "partial_screening_only",
    }


def self_test() -> dict[str, Any]:
    smoke = require_smoke_pass(); jobs = selected_original_jobs()
    assert len(jobs) == 6 and len(set(FRESH_MATCHED_SEEDS.values())) == 3
    for family in FAMILIES:
        assert len([row for row in jobs if row["family"] == family]) == 2
    parsed = parse_selected_blocks(ROOT / jobs[0]["source"])
    assert len(parsed["selected"]) == RETAINED_BLOCKS
    assert math.isclose(
        parsed["selected_10000_original_sum_flux_Bq"] * POSITION_STRIDE,
        parsed["original_all_50000_sum_flux_Bq"], rel_tol=1.0e-10, abs_tol=1.0e-12,
    )
    text = make_source(parsed, Path("/tmp/epsilon_formal_partial_selftest"))
    assert text.count("DecayRun.Source RP_") == RETAINED_BLOCKS
    assert text.count(f".Spectrum Mono {EPSILON_KEV:.9g}") == RETAINED_BLOCKS
    admission = BASE.disk_admission_decision(
        40 * 1024**3,
        [{"job_id": f"j{i}", "current_bytes": 0, "cap_bytes": JOB_CAP_BYTES} for i in range(5)],
        JOB_CAP_BYTES, RESERVE_BYTES,
    )
    assert admission["admitted"] and admission["active_jobs"] == 5
    return {
        "status": "PASS__EPSILON_FORMAL_PARTIAL_RECOVERY_STATIC_SELF_TEST",
        "tests": 14, "smoke_authority": smoke, "cells": 6,
        "selected_positions_tested": RETAINED_BLOCKS,
        "explicit_spectra_tested": RETAINED_BLOCKS,
        "matched_seed_pairs": 3, "disk_admission_tested": True,
        "campaign_files_written": False, "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--run-transport", action="store_true")
    parser.add_argument("--execute-transport", action="store_true")
    args = parser.parse_args()
    if args.execute_transport and not args.run_transport:
        parser.error("--execute-transport is only valid with --run-transport")
    if args.print_plan: payload = print_plan()
    elif args.self_test: payload = self_test()
    elif args.prepare: payload = prepare()
    else:
        if not args.execute_transport: raise SystemExit("--run-transport requires --execute-transport")
        payload = run_transport()
    print(json.dumps(payload, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
