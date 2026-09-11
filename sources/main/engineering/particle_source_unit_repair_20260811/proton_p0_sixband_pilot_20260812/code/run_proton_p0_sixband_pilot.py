#!/usr/bin/env python3
"""Run the corrected-keV, full-support, weighted proton P0 six-band pilot.

The execution path is fail-closed and non-overwriting.  ``--print-plan`` never
launches transport and writes nothing.  A real run requires the frozen P0
conditional-source manifest, canonical batch0004 final PASS authority, and
remaining time inside batch0003's original (never extended) 12-hour window.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
REPAIR_CODE = THIS_FILE.parents[2] / "code"
for directory in (CODE_DIR, REPAIR_CODE):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import p0_common as p0  # noqa: E402
import build_proton_p0_sixband_sources as source_builder  # noqa: E402
import run_mergeable_seven_family_1m_screening_batch0004 as batch4  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as source_validation  # noqa: E402


ROOT = p0.ROOT
P0_ROOT = p0.P0_ROOT
RUN_ROOT = p0.RUN_ROOT
REPAIR_ROOT = p0.REPAIR_ROOT
GENERIC_RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
VALIDATOR = CODE_DIR / "validate_proton_p0_sixband_pilot.py"
BUILDER = CODE_DIR / "build_proton_p0_sixband_sources.py"
COMMON = CODE_DIR / "p0_common.py"
LIMIT_LAUNCHER = CODE_DIR / "launch_cosima_with_limits.py"
SMOKE_RUNNER = REPAIR_CODE / "run_mergeable_two_geometry_smoke.py"
SMOKE_VALIDATOR = REPAIR_CODE / "validate_mergeable_two_geometry_smoke.py"
BATCH4_RUNNER = REPAIR_CODE / "run_mergeable_seven_family_1m_screening_batch0004.py"
BATCH4_VALIDATOR = REPAIR_CODE / "validate_mergeable_seven_family_1m_screening_batch0004.py"

BATCH_ID = "corrected_proton_p0_sixband_weighted_pilot_20260812"
CAMPAIGN_VERSION = "proton_p0_full_support_sixband_weighted_pilot_v1"
GEOMETRIES = p0.GEOMETRIES
MODES = p0.MODES

BATCH3_CONTRACT = batch4.BATCH0003_CONTRACT
BATCH3_STATE = batch4.BATCH0003_STATE
BATCH4_CONTRACT = batch4.GLOBAL_CONTRACT
BATCH4_REPORT = batch4.FINAL_VALIDATION_REPORT
BATCH4_LEDGER = batch4.FINAL_LEDGER
BATCH4_STATUS = "PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE"

GLOBAL_CONTRACT = RUN_ROOT / "proton_p0_sixband_pilot_v1_contract.json"
EXECUTION_STATE = RUN_ROOT / "proton_p0_sixband_pilot_v1_state.json"
RECEIPT_ROOT = RUN_ROOT / "proton_p0_sixband_pilot_v1_receipts"
CELL_AUTHORITY_ROOT = RUN_ROOT / "proton_p0_sixband_pilot_v1_cell_authorities"
FINAL_REPORT = RUN_ROOT / "proton_p0_sixband_pilot_v1_validation.json"
FINAL_LEDGER = RUN_ROOT / "proton_p0_sixband_pilot_v1_ledger.json"
CONTROLLER_LOCK = RUN_ROOT / "proton_p0_sixband_pilot_v1_controller.lock"

DEFAULT_WORKERS = 2
MAX_WORKERS = 4
MIN_AVAILABLE_RAM_BYTES = 2_500_000_000
HARD_AVAILABLE_RAM_BYTES = 1_700_000_000
UNTRUSTED_RAM_BYTES_PER_WORKER = 1_500_000_000
DISK_RESERVE_BYTES = 20 * 1024**3
ATTEMPT_OUTPUT_CAP_BYTES = 2 * 1024**3
PER_FILE_CAP_BYTES = 2 * 1024**3
ACTIVE_BURST_MARGIN_BYTES = MAX_WORKERS * (ATTEMPT_OUTPUT_CAP_BYTES + 128 * 1024**2)
DISK_SAFETY_FACTOR = 2.0
POINT_ESTIMATE_TAIL_MULTIPLIER = 12.0
STOP_LAUNCH_RESERVE_SECONDS = 2 * 60 * 60
VALIDATION_RESERVE_SECONDS = 60 * 60
HANG_SECONDS = 15 * 60
WATCHDOG_POLL_SECONDS = 2
HEARTBEAT_SECONDS = 60
MAX_ATTEMPTS = 2
COMMAND_TIMEOUT_SECONDS = 30 * 60

SEED_BASE = 883_120_001
SEED_STRIDE = 104_729

_STATE_LOCK = threading.RLock()
_CELL_PUBLISH_LOCK = threading.RLock()
_ABORT_EVENT = threading.Event()
_ACTIVE_LOCK = threading.RLock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen[Any]] = {}
_SIGNAL_CLEANUP = False
STATE_IMMUTABLE_KEYS = frozenset(
    {"started_utc", "deadline_utc", "global_contract_sha256", "batch0003_state_sha256_at_freeze"}
)


def _strict_json(path: Path) -> dict[str, Any]:
    return p0.load_json_strict(path)


def _load_generic_runner() -> Any:
    spec = importlib.util.spec_from_file_location("p0_generic_runner", GENERIC_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import generic Cosima runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _transport_core(payload: dict[str, Any]) -> dict[str, Any]:
    return batch4._transport_core(payload)


def _toolchain_paths() -> dict[str, Path]:
    return {
        "p0_runner": THIS_FILE,
        "p0_validator": VALIDATOR,
        "p0_common": COMMON,
        "p0_source_builder": BUILDER,
        "p0_limit_launcher": LIMIT_LAUNCHER,
        "generic_runner": GENERIC_RUNNER,
        "smoke_runner_helpers": SMOKE_RUNNER,
        "smoke_validator_helpers": SMOKE_VALIDATOR,
        "batch0004_runner": BATCH4_RUNNER,
        "batch0004_validator": BATCH4_VALIDATOR,
    }


def toolchain_payload() -> dict[str, dict[str, str]]:
    return {
        name: {"path": p0.rel(path), "sha256": p0.sha256(path)}
        for name, path in _toolchain_paths().items()
    }


def cells(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    bands = p0.bands_from_manifest(manifest)
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for band in bands:
        for mode in MODES:
            for geometry in GEOMETRIES:
                ordinal += 1
                rows.append(
                    {
                        "cell_ordinal": ordinal,
                        "cell_key": f"{geometry}_{mode}_{band.key}",
                        "geometry": geometry,
                        "mode": mode,
                        "family": "p",
                        "band": band.key,
                        "band_index": band.index,
                        "band_low_keV": p0.decimal_to_json(band.low_keV),
                        "band_high_keV": p0.decimal_to_json(band.high_keV),
                        "band_high_inclusive": band.high_inclusive,
                        "band_flux_cm2_s": p0.decimal_to_json(band.flux_cm2_s),
                        "band_flux_weight": p0.decimal_to_json(band.weight),
                        "events": p0.EVENTS_PER_CELL,
                        "shards": p0.SHARDS_PER_CELL,
                        "events_per_shard": p0.EVENTS_PER_SHARD,
                        "source_card": p0.rel(p0.band_source_path(geometry, band.key)),
                    }
                )
    if len(rows) != 24:
        raise RuntimeError("P0 cell count is not 24")
    return rows


def jobs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    job_ordinal = 0
    for cell in cells(manifest):
        for shard in range(1, p0.SHARDS_PER_CELL + 1):
            job_ordinal += 1
            rows.append(
                {
                    "job_ordinal": job_ordinal,
                    "cell_ordinal": cell["cell_ordinal"],
                    "cell_key": cell["cell_key"],
                    "geometry": cell["geometry"],
                    "mode": cell["mode"],
                    "family": "p",
                    "band": cell["band"],
                    "band_index": cell["band_index"],
                    "shard": shard,
                    "events": p0.EVENTS_PER_SHARD,
                    "seed": SEED_BASE + SEED_STRIDE * job_ordinal,
                }
            )
    if len(rows) != p0.JOB_COUNT or sum(int(row["events"]) for row in rows) != p0.PRIMARY_COUNT:
        raise RuntimeError("P0 96-job/6144-primary schedule closure failed")
    seeds = [int(row["seed"]) for row in rows]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("P0 planned seeds are not unique")
    return rows


def job_spec(job_ordinal: int, manifest: dict[str, Any]) -> dict[str, Any]:
    planned = jobs(manifest)
    if not 1 <= job_ordinal <= len(planned):
        raise ValueError(f"P0 job ordinal outside 1..{len(planned)}")
    return planned[job_ordinal - 1]


def cell_dir(cell_key: str) -> Path:
    return RUN_ROOT / "cells" / cell_key


def attempt_dir(job_ordinal: int, attempt: int) -> Path:
    return RUN_ROOT / "attempts" / f"job{job_ordinal:04d}" / f"attempt{attempt:02d}"


def receipt_path(job_ordinal: int) -> Path:
    return RECEIPT_ROOT / f"job{job_ordinal:04d}_receipt.json"


def cell_report_path(cell_key: str) -> Path:
    return CELL_AUTHORITY_ROOT / f"{cell_key}_validation.json"


def cell_ledger_path(cell_key: str) -> Path:
    return CELL_AUTHORITY_ROOT / f"{cell_key}_ledger.json"


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    snapshot = p0.stable_file_snapshot(path)
    payload = _strict_json(path)
    if p0.sha256(path) != snapshot["sha256"]:
        raise RuntimeError(f"authority changed after parsing: {p0.rel(path)}")
    return payload, str(snapshot["sha256"])


def _run_supervised(
    command: list[str],
    *,
    deadline: datetime,
    fixed_timeout_s: float,
) -> subprocess.CompletedProcess[str]:
    timeout = min(fixed_timeout_s, max(0.1, (deadline - datetime.now(timezone.utc)).total_seconds()))
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    _register_process(proc)
    try:
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc)
            stdout, _ = proc.communicate(timeout=10)
            return subprocess.CompletedProcess(command, 124, stdout, "")
        return subprocess.CompletedProcess(command, int(proc.returncode or 0), stdout, "")
    finally:
        _terminate_process_group(proc)
        _unregister_process(proc)


def _validate_batch4_authority(
    *,
    require: bool,
    deadline: datetime,
    run_check: bool,
) -> dict[str, Any]:
    exists = (BATCH4_REPORT.is_file(), BATCH4_LEDGER.is_file())
    waiting = {
        "profile": "batch0004_final",
        "gate": "WAIT__BATCH0004_FINAL_AUTHORITY_NOT_YET_PUBLISHED",
        "report": p0.rel(BATCH4_REPORT),
        "ledger": p0.rel(BATCH4_LEDGER),
    }
    if not any(exists):
        if require:
            raise RuntimeError("batch0004 canonical final report/ledger pair is not published")
        return waiting
    if not all(exists):
        raise RuntimeError("batch0004 canonical final authority is an incomplete pair")
    if run_check:
        result = _run_supervised(
            [sys.executable, str(BATCH4_VALIDATOR), "--final", "--check"],
            deadline=deadline,
            fixed_timeout_s=COMMAND_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(f"batch0004 canonical --check failed: {result.stdout[-2000:]}")
    report, report_hash = _stable_json(BATCH4_REPORT)
    ledger, ledger_hash = _stable_json(BATCH4_LEDGER)
    if report.get("status") != "PASS" or report.get("errors") not in (None, []):
        raise RuntimeError("batch0004 final report is not a clean PASS")
    if (
        ledger.get("schema_version") != 1
        or ledger.get("batch_id") != batch4.BATCH_ID
        or ledger.get("status") != BATCH4_STATUS
        or ledger.get("stage") != "final"
        or ledger.get("errors") not in (None, [])
        or ledger.get("source_contract_manifest_sha256") != p0.SOURCE_CONTRACT_SHA256
        or ledger.get("validation_report") != p0.rel(BATCH4_REPORT)
        or ledger.get("validation_report_sha256") != report_hash
    ):
        raise RuntimeError("batch0004 final ledger identity/hash/source contract mismatch")
    contract_path = p0.resolve_path(str(ledger.get("global_contract")))
    if contract_path != BATCH4_CONTRACT.resolve() or not contract_path.is_file():
        raise RuntimeError("batch0004 ledger global-contract path is not canonical")
    if ledger.get("global_contract_sha256") != p0.sha256(contract_path):
        raise RuntimeError("batch0004 ledger global-contract hash binding failed")
    return {
        "profile": "batch0004_final",
        "gate": "PASS__BATCH0004_FINAL_AUTHORITY",
        "status": BATCH4_STATUS,
        "report": p0.rel(BATCH4_REPORT),
        "report_sha256": report_hash,
        "ledger": p0.rel(BATCH4_LEDGER),
        "ledger_sha256": ledger_hash,
        "global_contract": p0.rel(contract_path),
        "global_contract_sha256": p0.sha256(contract_path),
    }


def _parent_execution_window() -> tuple[datetime, datetime, str, dict[str, Any]]:
    if not BATCH3_CONTRACT.is_file() or not BATCH3_STATE.is_file():
        raise RuntimeError("batch0003 contract/state are required for the inherited deadline")
    state, state_hash = _stable_json(BATCH3_STATE)
    contract = _strict_json(BATCH3_CONTRACT)
    started = datetime.fromisoformat(str(state.get("started_utc")))
    deadline = datetime.fromisoformat(str(state.get("deadline_utc")))
    if started.tzinfo is None or deadline.tzinfo is None:
        raise RuntimeError("batch0003 execution timestamps are not timezone-aware")
    if not math.isclose((deadline - started).total_seconds(), 12 * 3600, abs_tol=1e-6):
        raise RuntimeError("batch0003 inherited wall window is not exactly 12 hours")
    if state.get("global_contract_sha256") != p0.sha256(BATCH3_CONTRACT):
        raise RuntimeError("batch0003 state/global-contract hash binding failed")
    execution = contract.get("execution", {})
    if (
        execution.get("frozen_started_utc") != started.isoformat()
        or execution.get("frozen_deadline_utc") != deadline.isoformat()
        or float(execution.get("wall_limit_hours", -1)) != 12.0
    ):
        raise RuntimeError("batch0003 contract/state frozen execution window differs")
    return started, deadline, state_hash, state


def _prior_seed_registry(manifest: dict[str, Any]) -> set[int]:
    seeds: set[int] = set()
    for path in (batch4.BATCH0000_LEDGER, batch4.BATCH0001_LEDGER, batch4.BATCH0002_LEDGER):
        ledger = _strict_json(path)
        for campaign in ledger.get("campaigns", []):
            for row in campaign.get("jobs", []):
                seed = row.get("seed")
                if type(seed) is int:
                    # Historical two-geometry operational pairs intentionally
                    # used the same seed on both geometries.  They represent a
                    # single reserved seed value, not a registry corruption.
                    seeds.add(seed)
    batch3 = _strict_json(BATCH3_CONTRACT)
    for row in batch3.get("statistics", {}).get("paired_shards", []):
        seed = row.get("seed")
        if type(seed) is not int:
            raise RuntimeError("batch0003 planned seed is not an integer")
        seeds.add(seed)
    for row in batch4.planned_shards():
        seed = row.get("seed")
        if type(seed) is not int:
            raise RuntimeError("batch0004 planned seed is not an integer")
        seeds.add(seed)
    planned = {int(row["seed"]) for row in jobs(manifest)}
    overlap = sorted(planned & seeds)
    if overlap:
        raise RuntimeError(f"P0 seed collision with historical/planned registry: {overlap[:10]}")
    return seeds


def _calibration() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    total_bytes = 0
    total_events = 0
    total_wall_s = 0.0
    for geometry in GEOMETRIES:
        for mode in MODES:
            directory = (
                ROOT
                / "runs/particle_source_unit_repair_20260811"
                / geometry
                / f"{mode}_mergeable_smoke_v1"
            )
            sims = sorted(directory.glob("Background_p*.sim.gz"))
            dats = sorted(directory.glob("Background_p*.dat"))
            logs = sorted((directory / "logs").glob("Background_p*.log"))
            if len(sims) != 1 or len(dats) != 1 or len(logs) != 1:
                raise RuntimeError(f"missing unique batch0000 proton calibration: {geometry}/{mode}")
            log_text = logs[0].read_text(encoding="utf-8", errors="replace")
            generated = source_validation.GENERATED_RE.findall(log_text)
            wall_matches = __import__("re").findall(r"^wall_s=([-+0-9.eE]+)$", log_text, flags=__import__("re").MULTILINE)
            if len(generated) != 1 or int(generated[0]) != 23 or len(wall_matches) != 1:
                raise RuntimeError(f"invalid batch0000 proton calibration log: {geometry}/{mode}")
            artifact_bytes = sum(path.stat().st_size for path in (*sims, *dats, *logs))
            wall_s = float(wall_matches[0])
            record = {
                "geometry": geometry,
                "mode": mode,
                "events": 23,
                "artifact_bytes": artifact_bytes,
                "wall_s": wall_s,
                "artifacts": [p0.stable_file_snapshot(path) for path in (*sims, *dats, *logs)],
            }
            records.append(record)
            total_bytes += artifact_bytes
            total_events += 23
            total_wall_s += wall_s
    point_bytes = math.ceil(
        total_bytes / total_events * p0.PRIMARY_COUNT * POINT_ESTIMATE_TAIL_MULTIPLIER
    )
    point_cpu_s = total_wall_s / total_events * p0.PRIMARY_COUNT * POINT_ESTIMATE_TAIL_MULTIPLIER
    return {
        "authority": "batch0000 corrected-keV full-spectrum proton smoke; 23 events per geometry+mode",
        "caveat": (
            "no calibrated >100 GeV event exists; 12x tail multiplier is a planning estimate, "
            "not a guarantee; per-file RLIMIT and aggregate attempt cap are authoritative"
        ),
        "tail_multiplier": POINT_ESTIMATE_TAIL_MULTIPLIER,
        "records": records,
        "point_estimated_output_bytes": point_bytes,
        "point_estimated_cpu_s": point_cpu_s,
    }


def build_contract(
    *,
    cosima_arg: str | None,
    workers: int,
    require_predecessor: bool,
    run_predecessor_check: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    if not 1 <= workers <= MAX_WORKERS:
        raise RuntimeError(f"workers must be in 1..{MAX_WORKERS}")
    manifest = p0.load_source_manifest(required=True)
    assert manifest is not None
    source_builder.validate_published_package_exact(manifest)
    started, deadline, parent_state_hash, _ = _parent_execution_window()
    dependency = _validate_batch4_authority(
        require=require_predecessor,
        deadline=deadline,
        run_check=run_predecessor_check,
    )
    prior_seeds = _prior_seed_registry(manifest)
    cosima = smoke.resolve_cosima(cosima_arg)
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    bundles = {geometry: smoke.build_geometry_bundle(geometry, environment) for geometry in GEOMETRIES}
    calibration = _calibration()
    schedule = jobs(manifest)
    manifest_hash = p0.sha256(p0.SOURCE_MANIFEST)
    contract = {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__P0_JOB_RECEIPTS_AND_FINAL_VALIDATION_REQUIRED",
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "authority_boundary": (
            "full-support six-stratum weighted proton pilot only; not an unweighted full-spectrum "
            "sample, historical full-stat result, sensitivity, or geometry-promotion authority"
        ),
        "source": {
            "corrected_source_contract": p0.rel(p0.SOURCE_CONTRACT),
            "corrected_source_contract_sha256": p0.SOURCE_CONTRACT_SHA256,
            "science_contract": p0.rel(p0.SCIENCE_CONTRACT),
            "science_contract_sha256": manifest["science_contract_sha256"],
            "conditional_source_manifest": p0.rel(p0.SOURCE_MANIFEST),
            "conditional_source_manifest_sha256": manifest_hash,
            "total_flux_cm2_s": p0.decimal_to_json(p0.TOTAL_FLUX_DECIMAL),
            "bands": manifest["bands"],
            "only_allowed_parent_to_band_card_differences": [
                "20 Spectrum File paths to package-owned conditional PDFs",
                "20 Flux values proven as angular-bin partial Flux",
            ],
            "geant4_cut_changes": False,
        },
        "statistics": {
            "geometries": list(GEOMETRIES),
            "modes": list(MODES),
            "bands": 6,
            "events_per_cell": p0.EVENTS_PER_CELL,
            "shards_per_cell": p0.SHARDS_PER_CELL,
            "events_per_shard": p0.EVENTS_PER_SHARD,
            "cell_count": 24,
            "transport_jobs": len(schedule),
            "primaries": sum(int(row["events"]) for row in schedule),
            "cells": cells(manifest),
            "jobs": schedule,
        },
        "seed_registry": {
            "policy": "every job has a unique seed; no cross-geometry same-seed pairing",
            "seed_base": SEED_BASE,
            "seed_stride": SEED_STRIDE,
            "planned_unique_count": len(schedule),
            "prior_and_reserved_seed_count": len(prior_seeds),
            "planned_seed_list_sha256": p0.canonical_digest([row["seed"] for row in schedule]),
        },
        "predecessor": dependency,
        "execution": {
            "requested_worker_cap": workers,
            "default_workers": DEFAULT_WORKERS,
            "absolute_worker_cap": MAX_WORKERS,
            "adaptive_policy": "start <=2; promote only after >=8 signed peak-RSS receipts",
            "frozen_started_utc": started.isoformat(),
            "frozen_deadline_utc": deadline.isoformat(),
            "inherited_from": p0.rel(BATCH3_STATE),
            "batch0003_state_sha256_at_freeze": parent_state_hash,
            "wall_limit_hours": 12.0,
            "stop_new_launch_reserve_seconds": STOP_LAUNCH_RESERVE_SECONDS,
            "validation_reserve_seconds": VALIDATION_RESERVE_SECONDS,
            "hang_seconds": HANG_SECONDS,
            "max_attempts": MAX_ATTEMPTS,
            "retry_seed_policy": "same seed only",
            "automatic_delete": False,
        },
        "resource_gate": {
            **calibration,
            "disk_reserve_bytes": DISK_RESERVE_BYTES,
            "disk_safety_factor": DISK_SAFETY_FACTOR,
            "attempt_output_cap_bytes": ATTEMPT_OUTPUT_CAP_BYTES,
            "per_file_RLIMIT_FSIZE_bytes": PER_FILE_CAP_BYTES,
            "active_burst_margin_bytes": ACTIVE_BURST_MARGIN_BYTES,
            "min_available_ram_bytes": MIN_AVAILABLE_RAM_BYTES,
            "hard_available_ram_bytes": HARD_AVAILABLE_RAM_BYTES,
            "automatic_delete": False,
        },
        "normalization": manifest["normalization"],
        "postprocess_contract": {
            "instant": (
                "stream SIM event IDs/IA INIT and CC HIT; aggregate real TES pixel UIDs and exact "
                "physical CsI or BGO+plastic veto volumes; publish per-band count/TT contributions"
            ),
            "buildup": (
                "retain and hash SIM+DAT; parse every TT/VN/RP; aggregate RP/TT only after "
                "geometry+band+volume+isotope-state provenance closes"
            ),
        },
        "toolchain": toolchain_payload(),
        "transport": transport,
        "transport_core": _transport_core(transport),
        "geometry_bundles": bundles,
    }
    if dependency.get("gate", "").startswith("PASS"):
        ledger = _strict_json(BATCH4_LEDGER)
        if ledger.get("transport_core") != contract["transport_core"]:
            raise RuntimeError("batch0004/current transport cores differ")
        for geometry in GEOMETRIES:
            if ledger.get("geometry_bundles", {}).get(geometry) != bundles[geometry]:
                raise RuntimeError(f"batch0004/current geometry bundle differs: {geometry}")
    return contract, environment


def remaining_point_bytes(contract: dict[str, Any]) -> int:
    receipts = sum(1 for row in contract["statistics"]["jobs"] if receipt_path(int(row["job_ordinal"])).is_file())
    fraction = max(0.0, (len(contract["statistics"]["jobs"]) - receipts) / len(contract["statistics"]["jobs"]))
    return math.ceil(float(contract["resource_gate"]["point_estimated_output_bytes"]) * fraction)


def disk_gate(contract: dict[str, Any], *, active_workers: int) -> dict[str, Any]:
    free = shutil.disk_usage(RUN_ROOT.parent).free
    remaining = remaining_point_bytes(contract)
    required = (
        DISK_RESERVE_BYTES
        + math.ceil(DISK_SAFETY_FACTOR * remaining)
        + max(1, active_workers) * (ATTEMPT_OUTPUT_CAP_BYTES + 128 * 1024**2)
    )
    return {
        "status": "PASS" if free >= required else "FAIL",
        "free_bytes": free,
        "required_bytes": required,
        "reserve_bytes": DISK_RESERVE_BYTES,
        "remaining_point_estimate_bytes": remaining,
        "active_burst_bytes": max(1, active_workers) * (ATTEMPT_OUTPUT_CAP_BYTES + 128 * 1024**2),
    }


def mem_available_bytes() -> int:
    for raw in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if raw.startswith("MemAvailable:"):
            return int(raw.split()[1]) * 1024
    raise RuntimeError("MemAvailable is absent from /proc/meminfo")


def _validated_rss() -> list[int]:
    values: list[int] = []
    if not RECEIPT_ROOT.is_dir():
        return values
    for path in RECEIPT_ROOT.glob("job*_receipt.json"):
        try:
            payload = _strict_json(path)
            value = payload.get("peak_process_group_rss_bytes")
            if payload.get("status") == "PASS" and type(value) is int and value > 0:
                values.append(value)
        except Exception:
            continue
    return values


def adaptive_worker_cap(requested: int) -> int:
    available = mem_available_bytes()
    values = sorted(_validated_rss())
    cap = min(requested, DEFAULT_WORKERS)
    if len(values) >= 8:
        p95 = values[min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)]
        evidence_cap = max(1, int((available - MIN_AVAILABLE_RAM_BYTES) // max(1, math.ceil(p95 * 1.35))))
        cap = min(requested, MAX_WORKERS, max(DEFAULT_WORKERS, evidence_cap))
    else:
        cap = min(cap, max(1, int((available - MIN_AVAILABLE_RAM_BYTES) // UNTRUSTED_RAM_BYTES_PER_WORKER)))
    return max(0, cap)


def _register_process(proc: subprocess.Popen[Any]) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES[proc.pid] = proc


def _unregister_process(proc: subprocess.Popen[Any]) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES.pop(proc.pid, None)


def _terminate_process_group(proc: subprocess.Popen[Any]) -> None:
    pgid = proc.pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def _terminate_all() -> None:
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES.values())
    for proc in processes:
        _terminate_process_group(proc)


def _signal_handler(_signum: int, _frame: Any) -> None:
    global _SIGNAL_CLEANUP
    if _SIGNAL_CLEANUP:
        return
    _SIGNAL_CLEANUP = True
    _ABORT_EVENT.set()
    _terminate_all()


def _process_group_cpu_ticks(pgid: int) -> int:
    total = 0
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text(encoding="utf-8").split()
            if int(fields[4]) == pgid:
                total += int(fields[13]) + int(fields[14])
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def _process_group_rss_bytes(pgid: int) -> int:
    total = 0
    page_size = os.sysconf("SC_PAGE_SIZE")
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text(encoding="utf-8").split()
            if int(fields[4]) != pgid:
                continue
            statm = path.with_name("statm").read_text(encoding="utf-8").split()
            total += int(statm[1]) * page_size
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def _job_paths(spec: dict[str, Any], attempt: int) -> dict[str, Path]:
    directory = attempt_dir(int(spec["job_ordinal"]), attempt)
    name = (
        f"Background_p_p0_{spec['band']}_{spec['geometry']}_{spec['mode']}_"
        f"shard{int(spec['shard']):02d}"
    )
    sim_prefix = directory / name
    isotope_prefix = directory / f"{name}.dat"
    return {
        "directory": directory,
        "name": Path(name),
        "source": directory / f"{name}.source",
        "sim_prefix": sim_prefix,
        "isotope_prefix": isotope_prefix,
        "sim": Path(f"{sim_prefix}.inc1.id1.sim.gz"),
        "dat": Path(f"{isotope_prefix}.inc1.dat"),
        "log": directory / f"{name}.log",
        "attempt_contract": directory / "attempt_contract.json",
    }


def _generic_job(spec: dict[str, Any], attempt: int, cosima: str) -> dict[str, Any]:
    paths = _job_paths(spec, attempt)
    source = p0.band_source_path(str(spec["geometry"]), str(spec["band"]))
    return {
        "job_name": paths["name"].name,
        "particle": "p",
        "mode": spec["mode"],
        "events": spec["events"],
        "rep": spec["job_ordinal"],
        "part": 1,
        "seed": spec["seed"],
        "source": str(source.resolve()),
        "temp_source": str(paths["source"]),
        "sim_prefix": str(paths["sim_prefix"]),
        "iso_prefix": str(paths["isotope_prefix"]),
        "sim_path": str(paths["sim"]),
        "dat_path": str(paths["dat"]),
        "log": str(paths["log"]),
        "cosima": cosima,
        "skip_existing": False,
        "cleanup_source": False,
        "store_isotopes": True,
        "geometry": spec["geometry"],
        "attempt": attempt,
    }


def _attempt_input_digest(contract: dict[str, Any], spec: dict[str, Any]) -> str:
    records: list[dict[str, str]] = []
    paths = [
        GLOBAL_CONTRACT,
        p0.SOURCE_CONTRACT,
        p0.SCIENCE_CONTRACT,
        p0.SOURCE_MANIFEST,
        BATCH3_CONTRACT,
        BATCH3_STATE,
        BATCH4_CONTRACT,
        BATCH4_REPORT,
        BATCH4_LEDGER,
        p0.band_source_path(str(spec["geometry"]), str(spec["band"])),
    ]
    paths.extend(Path(record["path"]) if Path(record["path"]).is_absolute() else ROOT / record["path"] for record in contract["toolchain"].values())
    paths.append(Path(contract["transport"]["cosima"]))
    paths.extend(Path(row["path"]) for row in contract["transport"].get("shared_libraries", []))
    source_manifest = p0.load_source_manifest(required=True)
    assert source_manifest is not None
    for row in source_manifest["conditional_spectra"]:
        if row["band"] == spec["band"]:
            paths.append(p0.resolve_path(row["path"]))
    paths.extend(p0.resolve_path(row["path"]) for row in contract["geometry_bundles"][spec["geometry"]]["files"])
    expected: dict[Path, str] = {
        p0.SOURCE_CONTRACT.resolve(): p0.SOURCE_CONTRACT_SHA256,
        p0.SCIENCE_CONTRACT.resolve(): contract["source"]["science_contract_sha256"],
        p0.SOURCE_MANIFEST.resolve(): contract["source"]["conditional_source_manifest_sha256"],
        BATCH3_STATE.resolve(): contract["execution"]["batch0003_state_sha256_at_freeze"],
        BATCH4_REPORT.resolve(): contract["predecessor"]["report_sha256"],
        BATCH4_LEDGER.resolve(): contract["predecessor"]["ledger_sha256"],
        BATCH4_CONTRACT.resolve(): contract["predecessor"]["global_contract_sha256"],
    }
    unique: dict[Path, str] = {}
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise RuntimeError(f"attempt input is missing: {p0.rel(resolved)}")
        digest = p0.sha256(resolved)
        if resolved in expected and digest != expected[resolved]:
            raise RuntimeError(f"attempt input hash differs from frozen contract: {p0.rel(resolved)}")
        unique[resolved] = digest
    records.extend({"path": p0.rel(path), "sha256": digest} for path, digest in unique.items())
    return p0.canonical_digest(sorted(records, key=lambda row: row["path"]))


def _attempt_contract(
    contract: dict[str, Any],
    spec: dict[str, Any],
    attempt: int,
    job: dict[str, Any],
    input_digest: str,
) -> dict[str, Any]:
    paths = _job_paths(spec, attempt)
    command = [
        sys.executable,
        str(LIMIT_LAUNCHER),
        "--file-size-limit-bytes",
        str(PER_FILE_CAP_BYTES),
        "--cosima",
        job["cosima"],
        "--seed",
        str(spec["seed"]),
        "--source",
        job["temp_source"],
    ]
    return {
        "schema_version": 1,
        "status": "FROZEN_ATTEMPT__P0_DYNAMIC_VALIDATION_REQUIRED",
        "global_contract": p0.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": p0.sha256(GLOBAL_CONTRACT),
        "job_ordinal": spec["job_ordinal"],
        "cell_ordinal": spec["cell_ordinal"],
        "cell_key": spec["cell_key"],
        "geometry": spec["geometry"],
        "mode": spec["mode"],
        "family": "p",
        "band": spec["band"],
        "band_index": spec["band_index"],
        "shard": spec["shard"],
        "attempt": attempt,
        "events": spec["events"],
        "seed": spec["seed"],
        "base_band_source": p0.rel(Path(job["source"])),
        "base_band_source_sha256": p0.sha256(Path(job["source"])),
        "job_source": p0.rel(paths["source"]),
        "job_source_sha256": p0.sha256(paths["source"]),
        "sim": p0.rel(paths["sim"]),
        "isotope_dat": p0.rel(paths["dat"]),
        "log": p0.rel(paths["log"]),
        "command": command,
        "attempt_output_cap_bytes": ATTEMPT_OUTPUT_CAP_BYTES,
        "per_file_RLIMIT_FSIZE_bytes": PER_FILE_CAP_BYTES,
        "frozen_input_bundle_sha256_pre": input_digest,
    }


def _artifact_bytes(paths: dict[str, Path]) -> int:
    total = 0
    for key in ("sim", "dat", "log"):
        try:
            total += paths[key].stat().st_size
        except FileNotFoundError:
            pass
    return total


def _update_state(**updates: Any) -> None:
    with _STATE_LOCK:
        if not EXECUTION_STATE.is_file():
            raise RuntimeError("P0 execution state is absent")
        state = _strict_json(EXECUTION_STATE)
        if any(key in STATE_IMMUTABLE_KEYS for key in updates):
            raise RuntimeError("attempted to mutate an immutable P0 execution-state field")
        state.update(updates)
        state["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
        p0.atomic_replace_json(EXECUTION_STATE, state)


def _run_attempt(
    contract: dict[str, Any],
    environment: dict[str, str],
    spec: dict[str, Any],
    attempt: int,
    transport_deadline: datetime,
) -> None:
    input_pre = _attempt_input_digest(contract, spec)
    paths = _job_paths(spec, attempt)
    paths["directory"].mkdir(parents=True, exist_ok=False)
    job = _generic_job(spec, attempt, str(contract["transport"]["cosima"]))
    _load_generic_runner().patch_source(job)
    attempt_payload = _attempt_contract(contract, spec, attempt, job, input_pre)
    p0.atomic_write_once_json(paths["attempt_contract"], attempt_payload)
    started = time.monotonic()
    last_activity = started
    last_integrity = started
    last_heartbeat = started
    peak_rss = 0
    caught: BaseException | None = None
    reason = "process_exit"
    returncode: int | None = None
    proc: subprocess.Popen[Any] | None = None
    with paths["log"].open("x", encoding="utf-8", buffering=1) as handle:
        handle.write(
            f"job_ordinal={spec['job_ordinal']} cell={spec['cell_key']} shard={spec['shard']} "
            f"attempt={attempt} events={spec['events']} seed={spec['seed']}\n"
        )
        handle.write(f"cosima_command={' '.join(attempt_payload['command'])}\n")
        handle.flush()
        try:
            proc = subprocess.Popen(
                attempt_payload["command"],
                cwd=ROOT,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            _register_process(proc)
            previous_cpu = _process_group_cpu_ticks(proc.pid)
            previous_growth = _artifact_bytes(paths)
            while proc.poll() is None:
                time.sleep(WATCHDOG_POLL_SECONDS)
                now = time.monotonic()
                cpu = _process_group_cpu_ticks(proc.pid)
                growth = _artifact_bytes(paths)
                rss = _process_group_rss_bytes(proc.pid)
                peak_rss = max(peak_rss, rss)
                if cpu > previous_cpu or growth > previous_growth:
                    last_activity = now
                previous_cpu, previous_growth = cpu, growth
                free = shutil.disk_usage(RUN_ROOT).free
                available = mem_available_bytes()
                if _ABORT_EVENT.is_set():
                    reason = "global_abort"
                    break
                if free <= DISK_RESERVE_BYTES + ACTIVE_BURST_MARGIN_BYTES:
                    reason = "hard_disk_floor_20GiB_plus_active_margin"
                    _ABORT_EVENT.set()
                    break
                if growth > ATTEMPT_OUTPUT_CAP_BYTES:
                    reason = "aggregate_attempt_output_cap_exceeded"
                    _ABORT_EVENT.set()
                    break
                if available <= HARD_AVAILABLE_RAM_BYTES:
                    reason = "hard_low_memory"
                    _ABORT_EVENT.set()
                    break
                if datetime.now(timezone.utc) >= transport_deadline:
                    reason = "inherited_transport_deadline"
                    _ABORT_EVENT.set()
                    break
                if now - last_activity >= HANG_SECONDS:
                    reason = "watchdog_no_cpu_and_no_growth_15m"
                    break
                if now - last_integrity >= HEARTBEAT_SECONDS:
                    if _attempt_input_digest(contract, spec) != input_pre:
                        raise RuntimeError("P0 frozen input bundle drifted during attempt")
                    last_integrity = now
                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    _update_state(
                        last_worker_heartbeat={
                            "job_ordinal": spec["job_ordinal"],
                            "cell_key": spec["cell_key"],
                            "attempt": attempt,
                            "pid": proc.pid,
                            "cpu_ticks": cpu,
                            "artifact_bytes": growth,
                            "process_group_rss_bytes": rss,
                            "peak_process_group_rss_bytes": peak_rss,
                        },
                        free_disk_bytes=free,
                        mem_available_bytes=available,
                    )
                    last_heartbeat = now
        except BaseException as exc:
            caught = exc
            reason = f"supervisor_exception_{type(exc).__name__}"
            _ABORT_EVENT.set()
        finally:
            if proc is not None:
                try:
                    _terminate_process_group(proc)
                    returncode = proc.poll()
                finally:
                    _unregister_process(proc)
            final_growth = _artifact_bytes(paths)
            final_free = shutil.disk_usage(RUN_ROOT).free
            if final_growth > ATTEMPT_OUTPUT_CAP_BYTES and caught is None:
                caught = RuntimeError("P0 aggregate output cap exceeded by final flush")
                _ABORT_EVENT.set()
                reason = "aggregate_output_cap_final_flush"
            if final_free <= DISK_RESERVE_BYTES + ACTIVE_BURST_MARGIN_BYTES and caught is None:
                caught = RuntimeError("P0 hard disk floor crossed by final flush")
                _ABORT_EVENT.set()
                reason = "disk_floor_final_flush"
            input_post = "FAIL"
            try:
                input_post = _attempt_input_digest(contract, spec)
                if input_post != input_pre:
                    raise RuntimeError("P0 frozen input digest differs pre/post attempt")
            except BaseException as exc:
                if caught is None:
                    caught = exc
                _ABORT_EVENT.set()
            handle.write(f"watchdog_reason={reason}\n")
            handle.write(f"peak_process_group_rss_bytes={peak_rss}\n")
            handle.write(f"attempt_output_cap_bytes={ATTEMPT_OUTPUT_CAP_BYTES}\n")
            handle.write(f"per_file_RLIMIT_FSIZE_bytes={PER_FILE_CAP_BYTES}\n")
            handle.write(f"frozen_input_bundle_sha256_pre={input_pre}\n")
            handle.write(f"frozen_input_bundle_sha256_post={input_post}\n")
            handle.write(f"returncode={returncode if returncode is not None else -999}\n")
            handle.write(f"wall_s={time.monotonic()-started:.3f}\n")
    if caught is not None:
        raise caught


def _invoke_validator(spec: dict[str, Any], attempt: int, deadline: datetime) -> bool:
    result = _run_supervised(
        [
            sys.executable,
            str(VALIDATOR),
            "--job",
            str(spec["job_ordinal"]),
            "--attempt",
            str(attempt),
        ],
        deadline=deadline,
        fixed_timeout_s=COMMAND_TIMEOUT_SECONDS,
    )
    return result.returncode == 0 and receipt_path(int(spec["job_ordinal"])).is_file()


def _maybe_publish_cell(spec: dict[str, Any], deadline: datetime) -> None:
    """Commit a completed 4x64 cell promptly, before the final 24-cell scan."""

    with _CELL_PUBLISH_LOCK:
        manifest = p0.load_source_manifest(required=True)
        assert manifest is not None
        members = [row for row in jobs(manifest) if row["cell_key"] == spec["cell_key"]]
        if len(members) != p0.SHARDS_PER_CELL:
            raise RuntimeError(f"P0 cell membership mismatch: {spec['cell_key']}")
        if not all(receipt_path(int(row["job_ordinal"])).is_file() for row in members):
            return
        result = _run_supervised(
            [sys.executable, str(VALIDATOR), "--cell", str(spec["cell_key"])],
            deadline=deadline,
            fixed_timeout_s=COMMAND_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"P0 completed-cell authority failed: {spec['cell_key']}: {result.stdout[-2000:]}"
            )


def _validate_and_checkpoint(spec: dict[str, Any], attempt: int, deadline: datetime) -> bool:
    if not _invoke_validator(spec, attempt, deadline):
        return False
    _maybe_publish_cell(spec, deadline)
    return True


def _ensure_job(
    contract: dict[str, Any],
    environment: dict[str, str],
    spec: dict[str, Any],
    transport_deadline: datetime,
    validation_deadline: datetime,
) -> None:
    receipt = receipt_path(int(spec["job_ordinal"]))
    if receipt.is_file():
        selected = _strict_json(receipt).get("selected_attempt")
        if type(selected) is int and _validate_and_checkpoint(spec, selected, validation_deadline):
            return
        raise RuntimeError(f"immutable P0 receipt revalidation failed: job{spec['job_ordinal']:04d}")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        directory = attempt_dir(int(spec["job_ordinal"]), attempt)
        if directory.exists():
            if _validate_and_checkpoint(spec, attempt, validation_deadline):
                return
            continue
        if _ABORT_EVENT.is_set():
            raise RuntimeError("global resource abort set")
        _run_attempt(contract, environment, spec, attempt, transport_deadline)
        if _validate_and_checkpoint(spec, attempt, validation_deadline):
            return
        if _ABORT_EVENT.is_set():
            raise RuntimeError("global resource abort after P0 attempt")
    raise RuntimeError(f"job{spec['job_ordinal']:04d} exhausted two same-seed attempts")


def _execution_state(contract: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "status": "RUNNING",
        "started_utc": contract["execution"]["frozen_started_utc"],
        "deadline_utc": contract["execution"]["frozen_deadline_utc"],
        "global_contract_sha256": p0.sha256(GLOBAL_CONTRACT),
        "batch0003_state_sha256_at_freeze": contract["execution"]["batch0003_state_sha256_at_freeze"],
        "completed_jobs": [],
        "active_jobs": 0,
        "pending_jobs": p0.JOB_COUNT,
        "free_disk_bytes": shutil.disk_usage(RUN_ROOT).free,
        "mem_available_bytes": mem_available_bytes(),
    }
    if EXECUTION_STATE.is_file():
        existing = _strict_json(EXECUTION_STATE)
        for key in STATE_IMMUTABLE_KEYS:
            if existing.get(key) != payload[key]:
                raise RuntimeError(f"P0 execution-state immutable mismatch: {key}")
        return existing
    p0.atomic_write_once_json(EXECUTION_STATE, payload)
    return payload


def _prepare_contract(contract: dict[str, Any]) -> None:
    if GLOBAL_CONTRACT.is_file():
        if _strict_json(GLOBAL_CONTRACT) != contract:
            raise RuntimeError("existing P0 global contract differs")
        return
    p0.atomic_write_once_json(GLOBAL_CONTRACT, contract)


def _run_transport(contract: dict[str, Any], environment: dict[str, str], requested_workers: int) -> int:
    _ABORT_EVENT.clear()
    state = _execution_state(contract)
    deadline = datetime.fromisoformat(str(state["deadline_utc"]))
    launch_deadline = deadline - timedelta(seconds=STOP_LAUNCH_RESERVE_SECONDS)
    transport_deadline = deadline - timedelta(seconds=VALIDATION_RESERVE_SECONDS)
    if FINAL_LEDGER.is_file():
        result = _run_supervised(
            [sys.executable, str(VALIDATOR), "--final", "--check"],
            deadline=deadline,
            fixed_timeout_s=COMMAND_TIMEOUT_SECONDS,
        )
        return 0 if result.returncode == 0 else 1
    planned = contract["statistics"]["jobs"]
    # Revalidate/adopt all existing attempts before applying new-launch gates.
    existing = [
        row for row in planned
        if receipt_path(int(row["job_ordinal"])).is_file()
        or any(attempt_dir(int(row["job_ordinal"]), attempt).exists() for attempt in range(1, MAX_ATTEMPTS + 1))
    ]
    for spec in existing:
        _ensure_job(contract, environment, spec, transport_deadline, deadline)
    pending = [row for row in planned if not receipt_path(int(row["job_ordinal"])).is_file()]
    failures: list[str] = []
    futures: dict[concurrent.futures.Future[None], dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=requested_workers) as executor:
        while pending or futures:
            if failures or _ABORT_EVENT.is_set():
                break
            gate = disk_gate(contract, active_workers=max(1, len(futures)))
            if gate["status"] != "PASS":
                failures.append("disk gate failed: " + json.dumps(gate, sort_keys=True))
                _ABORT_EVENT.set()
                break
            if datetime.now(timezone.utc) >= launch_deadline and pending:
                failures.append("inherited stop-launch gate reached")
                break
            slots = adaptive_worker_cap(requested_workers) - len(futures)
            while pending and slots > 0:
                spec = pending.pop(0)
                future = executor.submit(
                    _ensure_job,
                    contract,
                    environment,
                    spec,
                    transport_deadline,
                    deadline,
                )
                futures[future] = spec
                slots -= 1
            if not futures:
                _update_state(status="PAUSED_RESOURCE_GATE")
                time.sleep(WATCHDOG_POLL_SECONDS)
                continue
            done, _ = concurrent.futures.wait(
                futures,
                timeout=WATCHDOG_POLL_SECONDS,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                spec = futures.pop(future)
                try:
                    future.result()
                except Exception as exc:
                    failures.append(f"job{spec['job_ordinal']:04d}: {exc}")
                    _ABORT_EVENT.set()
            completed = [
                int(row["job_ordinal"])
                for row in planned
                if receipt_path(int(row["job_ordinal"])).is_file()
            ]
            _update_state(
                status="RUNNING",
                completed_jobs=completed,
                active_jobs=len(futures),
                pending_jobs=len(pending),
                free_disk_bytes=shutil.disk_usage(RUN_ROOT).free,
                mem_available_bytes=mem_available_bytes(),
            )
    if failures:
        _update_state(status="PAUSED_REQUIRES_REVIEW", errors=failures)
        raise RuntimeError("P0 paused: " + " | ".join(failures))
    result = _run_supervised(
        [sys.executable, str(VALIDATOR), "--final"],
        deadline=deadline,
        fixed_timeout_s=max(1.0, (deadline - datetime.now(timezone.utc)).total_seconds()),
    )
    if result.returncode != 0:
        raise RuntimeError(f"P0 final validation failed: {result.stdout[-3000:]}")
    _update_state(
        status="PASS__PROTON_P0_SIXBAND_WEIGHTED_PILOT",
        active_jobs=0,
        pending_jobs=0,
    )
    return 0


def plan_summary(contract: dict[str, Any]) -> dict[str, Any]:
    deadline = datetime.fromisoformat(contract["execution"]["frozen_deadline_utc"])
    remaining_s = max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
    gate = disk_gate(contract, active_workers=int(contract["execution"]["requested_worker_cap"]))
    predecessor_ready = contract["predecessor"].get("gate", "").startswith("PASS")
    deadline_ready = remaining_s > STOP_LAUNCH_RESERVE_SECONDS
    return {
        "status": (
            "PASS__P0_PLAN_READY"
            if predecessor_ready and deadline_ready and gate["status"] == "PASS"
            else contract["predecessor"].get("gate")
            if not predecessor_ready
            else "WAIT__INHERITED_DEADLINE_OR_RESOURCE_GATE"
        ),
        "transport_launched": False,
        "batch_id": BATCH_ID,
        "authority_boundary": contract["authority_boundary"],
        "statistics": {
            "geometries": 2,
            "modes": 2,
            "bands": 6,
            "events_per_cell": p0.EVENTS_PER_CELL,
            "shards_per_cell": p0.SHARDS_PER_CELL,
            "events_per_shard": p0.EVENTS_PER_SHARD,
            "jobs": p0.JOB_COUNT,
            "primaries": p0.PRIMARY_COUNT,
        },
        "bands": contract["source"]["bands"],
        "predecessor": contract["predecessor"],
        "execution": {
            **contract["execution"],
            "remaining_seconds_at_plan": remaining_s,
            "deadline_gate": "PASS" if deadline_ready else "FAIL",
        },
        "resource_gate": {
            **gate,
            "point_estimated_output_bytes": contract["resource_gate"]["point_estimated_output_bytes"],
            "point_estimated_cpu_s": contract["resource_gate"]["point_estimated_cpu_s"],
            "tail_multiplier": POINT_ESTIMATE_TAIL_MULTIPLIER,
            "attempt_output_cap_bytes": ATTEMPT_OUTPUT_CAP_BYTES,
            "per_file_RLIMIT_FSIZE_bytes": PER_FILE_CAP_BYTES,
            "reserve_bytes": DISK_RESERVE_BYTES,
            "automatic_delete": False,
        },
        "seed_registry": contract["seed_registry"],
        "normalization": contract["normalization"],
        "toolchain": contract["toolchain"],
    }


def _acquire_lock() -> Any:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    handle = CONTROLLER_LOCK.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise RuntimeError("another P0 controller holds the campaign lock") from exc
    return handle


def _live_p0_children() -> list[dict[str, Any]]:
    """Refuse resume while an orphaned P0 transport/validator still exists."""

    markers = (
        str(RUN_ROOT.resolve()),
        str(LIMIT_LAUNCHER.resolve()),
        str(VALIDATOR.resolve()),
    )
    found: list[dict[str, Any]] = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            pid = int(path.parent.name)
            if pid == os.getpid():
                continue
            command = path.read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
        except (FileNotFoundError, PermissionError, ValueError, OSError):
            continue
        if command and any(marker in command for marker in markers):
            found.append({"pid": pid, "command": command})
    return sorted(found, key=lambda row: int(row["pid"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--cosima", default=None)
    args = parser.parse_args()
    if not p0.SOURCE_MANIFEST.is_file():
        if args.print_plan:
            print(
                json.dumps(
                    {
                        "status": "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN",
                        "transport_launched": False,
                        "source_manifest": p0.rel(p0.SOURCE_MANIFEST),
                        "jobs": p0.JOB_COUNT,
                        "primaries": p0.PRIMARY_COUNT,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        raise RuntimeError("P0 source manifest is absent; no transport launched")
    contract, environment = build_contract(
        cosima_arg=args.cosima,
        workers=args.workers,
        require_predecessor=not args.print_plan,
        run_predecessor_check=not args.print_plan,
    )
    if args.print_plan:
        print(json.dumps(plan_summary(contract), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 0
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(contract["execution"]["frozen_deadline_utc"])
    if now >= deadline - timedelta(seconds=STOP_LAUNCH_RESERVE_SECONDS):
        raise RuntimeError("insufficient inherited wall time; no P0 transport launched")
    gate = disk_gate(contract, active_workers=args.workers)
    if gate["status"] != "PASS":
        raise RuntimeError("P0 pre-write disk gate failed: " + json.dumps(gate, sort_keys=True))
    lock = _acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, _signal_handler)
        live = _live_p0_children()
        if live:
            raise RuntimeError("stale/live P0 child processes prevent resume: " + json.dumps(live))
        # Recheck time and disk after acquiring the single-controller lock.
        if datetime.now(timezone.utc) >= deadline - timedelta(seconds=STOP_LAUNCH_RESERVE_SECONDS):
            raise RuntimeError("inherited stop-launch gate closed while acquiring lock")
        gate = disk_gate(contract, active_workers=args.workers)
        if gate["status"] != "PASS":
            raise RuntimeError("P0 post-lock disk gate failed: " + json.dumps(gate, sort_keys=True))
        _prepare_contract(contract)
        return _run_transport(contract, environment, args.workers)
    finally:
        _ABORT_EVENT.set()
        _terminate_all()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
