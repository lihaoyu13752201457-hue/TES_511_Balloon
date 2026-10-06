#!/usr/bin/env python3
"""Run robust corrected-keV instant-gamma batch0003.

The retained batch0000 and batch0001 instant-gamma samples contribute 101,000
primaries per geometry.  The registered ceiling adds exactly 9,899,000
primaries per geometry so the two pre-registered cumulative checkpoints are
exactly five and ten million primaries; default execution stops at the
independently merge-eligible 5M checkpoint.  Transport is split into
operationally paired 25k shards, except for the 24k shard that closes 5M.

The controller is deliberately independent of the generic multiprocessing
runner: every attempt has a write-once directory, Cosima is supervised with a
process-group watchdog, and a shard is credited only after the companion
validator atomically signs its receipt.  ``--print-plan`` performs read-only
preflight checks and never creates run output or launches transport.
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
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import run_mergeable_muminus_instant_pair_batch0002 as batch2  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


ROOT = smoke.ROOT
PACKAGE = smoke.PACKAGE
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
GENERIC_RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
BUILDER = smoke.BUILDER
STATIC_VALIDATOR = smoke.STATIC_VALIDATOR
SOURCE_CONTRACT = smoke.SOURCE_CONTRACT
VALIDATOR = PACKAGE / "code/validate_mergeable_gamma_instant_batch0003.py"
SMOKE_VALIDATOR = PACKAGE / "code/validate_mergeable_two_geometry_smoke.py"
SEVEN_VALIDATOR = PACKAGE / "code/validate_mergeable_two_geometry_seven_family_batch0001.py"
MUMINUS_VALIDATOR = PACKAGE / "code/validate_mergeable_muminus_instant_pair_batch0002.py"

SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
BATCH0000_LEDGER = RUN_ROOT / "mergeable_smoke_v1_ledger.json"
BATCH0000_SHA256 = "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f"
BATCH0000_ID = "corrected_original_all8_fullsphere20_batch0000"
BATCH0000_STATUS = "PASS__BATCH0000_MERGE_ELIGIBLE"
BATCH0001_LEDGER = RUN_ROOT / "seven_family_batch0001_v1_ledger.json"
BATCH0001_SHA256 = "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4"
BATCH0001_ID = "corrected_original_seven_family_fullsphere20_batch0001"
BATCH0001_STATUS = "PASS__BATCH0001_MERGE_ELIGIBLE"
BATCH0002_LEDGER = RUN_ROOT / "muminus_instant_pair_batch0002_v1_ledger.json"
BATCH0002_SHA256 = "742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62"
BATCH0002_ID = "corrected_original_muminus_instant_pair_batch0002"
BATCH0002_STATUS = "PASS__BATCH0002_MERGE_ELIGIBLE"

BATCH_ID = "corrected_original_gamma_instant_batch0003"
CAMPAIGN_VERSION = "mergeable_gamma_instant_10m_v1"
FAMILY = "gamma"
MODE = "instant"
GEOMETRIES = smoke.GEOMETRIES
FARFIELD_RADIUS_CM = 60.0

PRIOR_EVENTS_PER_GEOMETRY = 101_000
STAGE5_TOTAL_EVENTS_PER_GEOMETRY = 5_000_000
FINAL_TOTAL_EVENTS_PER_GEOMETRY = 10_000_000
NEW_EVENTS_PER_GEOMETRY = FINAL_TOTAL_EVENTS_PER_GEOMETRY - PRIOR_EVENTS_PER_GEOMETRY
STANDARD_SHARD_EVENTS = 25_000
STAGE5_SHORT_SHARD_EVENTS = 24_000
STAGE5_SHARD_COUNT = 196
FINAL_SHARD_COUNT = 396
SEED_BASE = 861_100_003
SEED_STRIDE = 7_919

DEFAULT_WORKERS = 4
MAX_WORKERS = 8
MIN_AVAILABLE_RAM_BYTES = 2_000_000_000
HARD_AVAILABLE_RAM_BYTES = 1_500_000_000
UNTRUSTED_RAM_BYTES_PER_WORKER = 1_000_000_000
DISK_RESERVE_BYTES = 20 * 1024**3
DISK_EMERGENCY_MARGIN_BYTES = 8 * 500_000_000 + 2 * 1024**3
DISK_SAFETY_FACTOR = 2.0
ATTEMPT_OUTPUT_SAFETY_FACTOR = 4.0
MIN_ATTEMPT_OUTPUT_CAP_BYTES = 500_000_000
MAX_WALL_HOURS = 12.0
STOP_LAUNCH_RESERVE_SECONDS = 4 * 60 * 60
VALIDATION_RESERVE_SECONDS = 3 * 60 * 60
HANG_SECONDS = 15 * 60
WATCHDOG_POLL_SECONDS = 2
HEARTBEAT_SECONDS = 60
MAX_ATTEMPTS = 2
PREFLIGHT_COMMAND_TIMEOUT_SECONDS = 30 * 60
SHARD_VALIDATION_TIMEOUT_SECONDS = 30 * 60

_STATE_LOCK = threading.Lock()
_ABORT_EVENT = threading.Event()

GLOBAL_CONTRACT = RUN_ROOT / "gamma_instant_batch0003_v1_contract.json"
EXECUTION_STATE = RUN_ROOT / "gamma_instant_batch0003_v1_state.json"
PAIR_RECEIPT_ROOT = RUN_ROOT / "gamma_instant_batch0003_v1_pair_receipts"
CONTROLLER_LOCK = RUN_ROOT / "gamma_instant_batch0003_v1_controller.lock"
STAGE5_VALIDATION_REPORT = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_validation.json"
STAGE5_LEDGER = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_ledger.json"
FINAL_VALIDATION_REPORT = RUN_ROOT / "gamma_instant_batch0003_v1_validation.json"
FINAL_LEDGER = RUN_ROOT / "gamma_instant_batch0003_v1_ledger.json"

PAIRING_RULE = (
    "equal-N same-seed operational paired commit/provenance; geometries remain "
    "separate aggregation domains"
)
PAIRING_STATISTICAL_SEMANTICS = (
    "geometry-dependent transport consumes RNG streams differently: this is not "
    "common-random-number pairing, gives no paired-estimator/variance-reduction "
    "authority, and geometry rates require independent normalization"
)
TT_AUTHORITY = (
    "per-job positive isotope-DAT TT matched to log observation time; "
    "aggregate within geometry+mode+family as sum(selected)/sum(TT)"
)

_ACTIVE_PROCESS_LOCK = threading.RLock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen[Any]] = {}
_SIGNAL_CLEANUP_IN_PROGRESS = False
STATE_IMMUTABLE_KEYS = frozenset({"started_utc", "deadline_utc", "global_contract_sha256"})


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_generic_runner() -> Any:
    spec = importlib.util.spec_from_file_location("equiv2602_batch0003_runtime", GENERIC_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GENERIC_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_write_once_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically create a JSON authority file without replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _load_json(path) != payload:
            raise RuntimeError(f"write-once JSON differs: {smoke.rel(path)}")
        return
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        os.link(temporary, path)
    except FileExistsError:
        if _load_json(path) != payload:
            raise RuntimeError(f"concurrent write-once JSON differs: {smoke.rel(path)}")
    finally:
        temporary.unlink(missing_ok=True)


def atomic_replace_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace mutable state with a per-call unique temporary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}-{time.time_ns()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _register_process(proc: subprocess.Popen[Any]) -> None:
    with _ACTIVE_PROCESS_LOCK:
        _ACTIVE_PROCESSES[proc.pid] = proc


def _unregister_process(proc: subprocess.Popen[Any]) -> None:
    with _ACTIVE_PROCESS_LOCK:
        _ACTIVE_PROCESSES.pop(proc.pid, None)


def _terminate_all_active_process_groups() -> None:
    with _ACTIVE_PROCESS_LOCK:
        processes = list(_ACTIVE_PROCESSES.values())
    for proc in processes:
        try:
            _terminate_process_group(proc)
        except Exception:
            # Continue through the full registry: one stale PGID must not leave
            # another live Cosima/validator process behind.
            pass


def _controller_signal_handler(signum: int, _frame: Any) -> None:
    global _SIGNAL_CLEANUP_IN_PROGRESS
    if _SIGNAL_CLEANUP_IN_PROGRESS:
        return
    _SIGNAL_CLEANUP_IN_PROGRESS = True
    _ABORT_EVENT.set()
    _terminate_all_active_process_groups()
    raise SystemExit(128 + signum)


def _acquire_controller_lock() -> Any:
    """Hold a process-wide non-blocking campaign lock until the caller closes it."""
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    handle = CONTROLLER_LOCK.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise SystemExit("another batch0003 controller already holds the campaign lock")
    return handle


def _live_batch0003_processes(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    """Find stale live children whose command line targets a batch0003 attempt."""
    markers = [str(campaign_dir(geometry).resolve()) for geometry in GEOMETRIES]
    markers.append("Background_gamma_fullsphere20_batch0003_shard")
    markers.append(str(VALIDATOR.resolve()))
    found: list[dict[str, Any]] = []
    for cmdline_path in proc_root.glob("[0-9]*/cmdline"):
        try:
            pid = int(cmdline_path.parent.name)
            if pid == os.getpid():
                continue
            raw = cmdline_path.read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue
        command = raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
        if command and any(marker in command for marker in markers):
            found.append({"pid": pid, "command": command})
    return sorted(found, key=lambda row: int(row["pid"]))


def _refuse_live_batch0003_processes() -> None:
    live = _live_batch0003_processes()
    if live:
        detail = "; ".join(f"pid={row['pid']} {row['command']}" for row in live[:4])
        raise SystemExit("live batch0003 transport/child detected; refusing concurrent resume: " + detail)


def _command_timeout(deadline: datetime | None, fixed_limit: float) -> float:
    if deadline is None:
        return fixed_limit
    remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        raise TimeoutError("global deadline reached before child command")
    return min(fixed_limit, remaining)


def _run_supervised_command(
    command: list[str],
    *,
    deadline: datetime | None,
    fixed_timeout_s: float,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a non-transport child with timeout and guaranteed group cleanup."""
    timeout = _command_timeout(deadline, fixed_timeout_s)
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        _register_process(proc)
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc)
            try:
                stdout, _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                stdout = "child output unavailable after forced process-group cleanup"
            raise TimeoutError(f"child command exceeded {timeout:.1f}s: {' '.join(command)}")
        return subprocess.CompletedProcess(command, int(proc.returncode), stdout, None)
    finally:
        if proc is not None:
            # The session leader can exit before a descendant.  Always probe
            # and clean the PGID, even when proc.poll() already has a result.
            try:
                _terminate_process_group(proc)
            finally:
                _unregister_process(proc)


def campaign_dir(geometry: str) -> Path:
    return RUN_ROOT / geometry / "instant_gamma_batch0003_v1"


def shard_dir(geometry: str, ordinal: int) -> Path:
    return campaign_dir(geometry) / "shards" / f"shard{ordinal:04d}"


def attempt_dir(geometry: str, ordinal: int, attempt: int) -> Path:
    return shard_dir(geometry, ordinal) / f"attempt{attempt:02d}"


def geometry_receipt_path(geometry: str, ordinal: int) -> Path:
    return shard_dir(geometry, ordinal) / "receipt.json"


def pair_receipt_path(ordinal: int) -> Path:
    return PAIR_RECEIPT_ROOT / f"shard{ordinal:04d}.json"


def source_manifest_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "source_migration_manifest.json"


def source_card_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "Background_gamma_fullsphere20.source"


def shard_events(ordinal: int) -> int:
    if not 1 <= ordinal <= FINAL_SHARD_COUNT:
        raise ValueError(f"shard ordinal out of range: {ordinal}")
    return STAGE5_SHORT_SHARD_EVENTS if ordinal == STAGE5_SHARD_COUNT else STANDARD_SHARD_EVENTS


def shard_seed(ordinal: int) -> int:
    if not 1 <= ordinal <= FINAL_SHARD_COUNT:
        raise ValueError(f"shard ordinal out of range: {ordinal}")
    return SEED_BASE + ordinal * SEED_STRIDE


def planned_shards() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    cumulative = PRIOR_EVENTS_PER_GEOMETRY
    for ordinal in range(1, FINAL_SHARD_COUNT + 1):
        events = shard_events(ordinal)
        cumulative += events
        checkpoint = "5m" if cumulative == STAGE5_TOTAL_EVENTS_PER_GEOMETRY else (
            "10m" if cumulative == FINAL_TOTAL_EVENTS_PER_GEOMETRY else ""
        )
        rows.append({
            "ordinal": ordinal,
            "events": events,
            "seed": shard_seed(ordinal),
            "cumulative_events_per_geometry": cumulative,
            "checkpoint": checkpoint,
        })
    if cumulative != FINAL_TOTAL_EVENTS_PER_GEOMETRY:
        raise AssertionError(f"internal shard schedule closes at {cumulative}, not 10M")
    return rows


def _prior_seeds(*ledgers: dict[str, Any]) -> set[int]:
    return batch2._prior_seeds(*ledgers)


def _campaign(ledger: dict[str, Any], geometry: str, mode: str) -> dict[str, Any]:
    matches = [
        row for row in ledger.get("campaigns", [])
        if row.get("geometry") == geometry and row.get("mode") == mode
    ]
    if len(matches) != 1:
        raise SystemExit(f"prior ledger campaign ambiguity: {geometry}/{mode}")
    return matches[0]


def _gamma_jobs(ledger: dict[str, Any], geometry: str) -> list[dict[str, Any]]:
    jobs = [
        job for job in _campaign(ledger, geometry, MODE).get("jobs", [])
        if job.get("family") == FAMILY
    ]
    if not jobs:
        raise SystemExit(f"prior ledger has no instant gamma jobs: {geometry}")
    return jobs


def _run_read_only_check(path: Path, deadline: datetime | None) -> dict[str, Any]:
    result = _run_supervised_command(
        [sys.executable, str(path), "--check"],
        deadline=deadline,
        fixed_timeout_s=PREFLIGHT_COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        raise SystemExit(f"read-only prior validation failed: {smoke.rel(path)}")
    return {
        "validator": smoke.rel(path),
        "validator_sha256": smoke.sha256(path),
        "command": [sys.executable, smoke.rel(path), "--check"],
        "returncode": result.returncode,
        "stdout_sha256": __import__("hashlib").sha256(result.stdout.encode("utf-8")).hexdigest(),
    }


def run_preflight(
    *,
    revalidate_prior: bool,
    deadline: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    required = (
        THIS_FILE, VALIDATOR, GENERIC_RUNNER, BUILDER, STATIC_VALIDATOR,
        SMOKE_VALIDATOR, SEVEN_VALIDATOR, MUMINUS_VALIDATOR, SOURCE_CONTRACT,
        BATCH0000_LEDGER, BATCH0001_LEDGER, BATCH0002_LEDGER,
    )
    missing = [smoke.rel(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing batch0003 input(s): " + ", ".join(missing))
    for path, expected in (
        (SOURCE_CONTRACT, SOURCE_CONTRACT_SHA256),
        (BATCH0000_LEDGER, BATCH0000_SHA256),
        (BATCH0001_LEDGER, BATCH0001_SHA256),
        (BATCH0002_LEDGER, BATCH0002_SHA256),
    ):
        if smoke.sha256(path) != expected:
            raise SystemExit(f"pinned hash mismatch: {smoke.rel(path)}")

    ledger0 = _load_json(BATCH0000_LEDGER)
    ledger1 = _load_json(BATCH0001_LEDGER)
    ledger2 = _load_json(BATCH0002_LEDGER)
    for ledger, batch_id, status in (
        (ledger0, BATCH0000_ID, BATCH0000_STATUS),
        (ledger1, BATCH0001_ID, BATCH0001_STATUS),
        (ledger2, BATCH0002_ID, BATCH0002_STATUS),
    ):
        if ledger.get("batch_id") != batch_id or ledger.get("status") != status:
            raise SystemExit(f"prior ledger is not merge eligible: {batch_id}")
        if ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256:
            raise SystemExit(f"prior source-contract binding mismatch: {batch_id}")
    if not any(row.get("ledger_sha256") == BATCH0000_SHA256 for row in ledger1.get("prior_batches", [])):
        raise SystemExit("batch0001 does not bind batch0000")
    if not any(row.get("ledger_sha256") == BATCH0001_SHA256 for row in ledger2.get("prior_batches", [])):
        raise SystemExit("batch0002 does not bind batch0001")
    if _transport_core(ledger0.get("transport", {})) != _transport_core(ledger1.get("transport", {})):
        raise SystemExit("batch0000/batch0001 credited transport cores differ")
    for geometry in GEOMETRIES:
        if ledger0.get("geometry_bundles", {}).get(geometry) != ledger1.get("geometry_bundles", {}).get(geometry):
            raise SystemExit(f"batch0000/batch0001 credited geometry bundles differ: {geometry}")

    for geometry in GEOMETRIES:
        credited0 = sum(int(job["events"]) for job in _gamma_jobs(ledger0, geometry))
        credited1 = sum(int(job["events"]) for job in _gamma_jobs(ledger1, geometry))
        if (credited0, credited1) != (1_000, 100_000):
            raise SystemExit(
                f"{geometry}: prior instant-gamma credit is {credited0}+{credited1}, expected 1000+100000"
            )
        card = source_card_path(geometry)
        text = card.read_text(encoding="utf-8", errors="replace")
        if text.count("engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/") != 20:
            raise SystemExit(f"{geometry}: corrected-keV gamma references are not exactly 20")
        if "cosima_spectra_dp_2602units" in text:
            raise SystemExit(f"{geometry}: legacy energy-axis reference remains")
        if text.count("StoreSimulationInfo all") != 1:
            raise SystemExit(f"{geometry}: StoreSimulationInfo all contract mismatch")
        if not source_manifest_path(geometry).is_file():
            raise SystemExit(f"{geometry}: source migration manifest missing")

    historical = _prior_seeds(ledger0, ledger1, ledger2)
    planned = [shard_seed(ordinal) for ordinal in range(1, FINAL_SHARD_COUNT + 1)]
    if len(planned) != len(set(planned)):
        raise SystemExit("batch0003 planned seed registry is not unique")
    overlap = historical & set(planned)
    if overlap:
        raise SystemExit(f"batch0003 planned seed collision(s): {sorted(overlap)[:10]}")

    checks: list[dict[str, Any]] = []
    if revalidate_prior:
        for validator in (SMOKE_VALIDATOR, SEVEN_VALIDATOR, MUMINUS_VALIDATOR):
            checks.append(_run_read_only_check(validator, deadline))
        for label, command in (
            ("corrected package deterministic check", [sys.executable, str(BUILDER), "--check"]),
            ("corrected package static validation", [sys.executable, str(STATIC_VALIDATOR), "--check"]),
        ):
            result = _run_supervised_command(
                command,
                deadline=deadline,
                fixed_timeout_s=PREFLIGHT_COMMAND_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                sys.stderr.write(result.stdout)
                raise SystemExit(f"preflight FAIL: {label}")
            checks.append({
                "label": label,
                "command": [smoke.rel(Path(command[1])), command[2]],
                "returncode": result.returncode,
                "stdout_sha256": __import__("hashlib").sha256(result.stdout.encode("utf-8")).hexdigest(),
            })
    return ledger0, ledger1, ledger2, checks


def _calibration(ledger1: dict[str, Any], geometry: str) -> dict[str, Any]:
    jobs = _gamma_jobs(ledger1, geometry)
    if sum(int(job["events"]) for job in jobs) != 100_000 or len(jobs) != 4:
        raise SystemExit(f"{geometry}: expected four 25k batch0001 gamma calibration jobs")
    runtime = _load_generic_runner()
    artifact_bytes = 0
    run_phase_s = 0.0
    artifacts: list[dict[str, Any]] = []
    for job in jobs:
        for key, hash_key in (
            ("sim", "sim_sha256"),
            ("isotope_dat", "isotope_dat_sha256"),
            ("log", "log_sha256"),
            ("job_source", "job_source_sha256"),
        ):
            path = ROOT / job[key]
            if not path.is_file() or path.stat().st_size <= 0:
                raise SystemExit(f"missing gamma calibration artifact: {smoke.rel(path)}")
            if smoke.sha256(path) != job[hash_key]:
                raise SystemExit(f"gamma calibration artifact hash changed: {smoke.rel(path)}")
            artifact_bytes += path.stat().st_size
            artifacts.append({
                "path": smoke.rel(path),
                "sha256": job[hash_key],
                "bytes": path.stat().st_size,
            })
        parsed = runtime.parse_log(ROOT / job["log"])
        if parsed.get("cpu_s") is None:
            raise SystemExit(f"gamma calibration log lacks run-phase time: {job['log']}")
        run_phase_s += float(parsed["cpu_s"])
    bytes_per_event = artifact_bytes / 100_000
    seconds_per_event = run_phase_s / 100_000
    return {
        "authority_batch": BATCH0001_ID,
        "events": 100_000,
        "jobs": 4,
        "artifact_bytes": artifact_bytes,
        "run_phase_s": run_phase_s,
        "observed_bytes_per_event": bytes_per_event,
        "observed_run_phase_s_per_event": seconds_per_event,
        "new_events": NEW_EVENTS_PER_GEOMETRY,
        "point_estimated_output_bytes": bytes_per_event * NEW_EVENTS_PER_GEOMETRY,
        "gated_estimated_output_bytes": bytes_per_event * NEW_EVENTS_PER_GEOMETRY * DISK_SAFETY_FACTOR,
        "point_estimated_run_phase_s": seconds_per_event * NEW_EVENTS_PER_GEOMETRY,
        "artifacts": artifacts,
    }


def _transport_core(transport: dict[str, Any]) -> dict[str, Any]:
    return batch2._transport_core(transport)


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def require_prior_credit_equivalence(
    ledger0: dict[str, Any],
    ledger1: dict[str, Any],
    current_transport: dict[str, Any],
    current_bundles: dict[str, Any],
) -> dict[str, Any]:
    """Prove that the credited 101k and new transport share physics inputs."""
    if "transport" not in ledger0 or "transport" not in ledger1:
        raise SystemExit("credited prior ledger lacks transport fingerprint")
    core0 = _transport_core(ledger0["transport"])
    core1 = _transport_core(ledger1["transport"])
    current_core = _transport_core(current_transport)
    if core0 != core1:
        raise SystemExit("batch0000/batch0001 credited transport cores differ")
    if core0 != current_core:
        raise SystemExit("credited 101k transport core differs from proposed batch0003 transport")
    for geometry in GEOMETRIES:
        bundle0 = ledger0.get("geometry_bundles", {}).get(geometry)
        bundle1 = ledger1.get("geometry_bundles", {}).get(geometry)
        current = current_bundles.get(geometry)
        if bundle0 is None or bundle1 is None:
            raise SystemExit(f"credited prior ledger lacks geometry bundle: {geometry}")
        if bundle0 != bundle1:
            raise SystemExit(f"batch0000/batch0001 credited geometry bundles differ: {geometry}")
        if bundle0 != current:
            raise SystemExit(f"credited 101k geometry bundle differs from batch0003: {geometry}")
    return {
        "status": "PASS__PRIOR_101K_PHYSICS_INPUTS_EQUAL_CURRENT",
        "credited_batches": [BATCH0000_ID, BATCH0001_ID],
        "transport_core_sha256": _json_sha256(current_core),
        "geometry_bundle_sha256": {
            geometry: str(current_bundles[geometry]["bundle_sha256"])
            for geometry in GEOMETRIES
        },
        "comparison": "exact normalized transport-core and exact full geometry-bundle equality",
    }


def build_contract(
    cosima_arg: str | None,
    workers: int,
    wall_limit_hours: float,
    *,
    deadline: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    if not 1 <= workers <= MAX_WORKERS:
        raise SystemExit(f"--workers must be within 1..{MAX_WORKERS}")
    if not 0 < wall_limit_hours <= MAX_WALL_HOURS:
        raise SystemExit(f"--wall-limit-hours must be within (0,{MAX_WALL_HOURS:g}]")
    frozen_deadline = deadline or (datetime.now(timezone.utc) + timedelta(hours=wall_limit_hours))
    frozen_started = frozen_deadline - timedelta(hours=wall_limit_hours)
    ledger0, ledger1, ledger2, prior_checks = run_preflight(
        revalidate_prior=True,
        deadline=deadline,
    )
    cosima = smoke.resolve_cosima(cosima_arg)
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    source_contract = _load_json(SOURCE_CONTRACT)
    bundles = {geometry: smoke.build_geometry_bundle(geometry, environment) for geometry in GEOMETRIES}
    prior_credit_equivalence = require_prior_credit_equivalence(
        ledger0,
        ledger1,
        transport,
        bundles,
    )
    campaigns: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        bundle = bundles[geometry]
        if common.source_contract_geometry_files(source_contract, geometry, environment) != bundle["files"]:
            raise SystemExit(f"source/runtime geometry bundle mismatch: {geometry}")
        migration = source_manifest_path(geometry)
        campaigns.append({
            "geometry": geometry,
            "mode": MODE,
            "family": FAMILY,
            "outdir": smoke.rel(campaign_dir(geometry)),
            "source_card": smoke.rel(source_card_path(geometry)),
            "source_card_sha256": smoke.sha256(source_card_path(geometry)),
            "source_migration_manifest": smoke.rel(migration),
            "source_migration_manifest_sha256": smoke.sha256(migration),
            "geometry_bundle": bundle,
            "prior_events": PRIOR_EVENTS_PER_GEOMETRY,
            "new_events": NEW_EVENTS_PER_GEOMETRY,
            "final_cumulative_events": FINAL_TOTAL_EVENTS_PER_GEOMETRY,
            "calibration": _calibration(ledger1, geometry),
        })
    point_bytes = math.fsum(row["calibration"]["point_estimated_output_bytes"] for row in campaigns)
    gated_bytes = point_bytes * DISK_SAFETY_FACTOR
    point_run_s = math.fsum(row["calibration"]["point_estimated_run_phase_s"] for row in campaigns)
    return ({
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__DYNAMIC_STAGE_PASS_REQUIRED_FOR_MERGE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "source_profile": "unit_only_total_gamma",
        "source_contract_manifest": smoke.rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "source_scope": {
            "included_families": [FAMILY],
            "excluded_families": ["alpha", "eminus", "eplus", "muminus", "muplus", "n", "p"],
            "mode": MODE,
            "angular_bins": 20,
            "mono_511_added": False,
            "store_simulation_info": "all",
        },
        "statistics": {
            "prior_events_per_geometry": PRIOR_EVENTS_PER_GEOMETRY,
            "new_events_per_geometry": NEW_EVENTS_PER_GEOMETRY,
            "stage5_cumulative_events_per_geometry": STAGE5_TOTAL_EVENTS_PER_GEOMETRY,
            "final_cumulative_events_per_geometry": FINAL_TOTAL_EVENTS_PER_GEOMETRY,
            "new_events_total": NEW_EVENTS_PER_GEOMETRY * len(GEOMETRIES),
            "shards_per_geometry": FINAL_SHARD_COUNT,
            "paired_shards": planned_shards(),
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
        },
        "pairing": {
            "policy": PAIRING_RULE,
            "statistical_semantics": PAIRING_STATISTICAL_SEMANTICS,
            "seed_base": SEED_BASE,
            "seed_stride": SEED_STRIDE,
            "planned_unique_seed_count": FINAL_SHARD_COUNT,
        },
        "lineage": [
            {"batch_id": BATCH0000_ID, "status": BATCH0000_STATUS,
             "ledger": smoke.rel(BATCH0000_LEDGER), "ledger_sha256": BATCH0000_SHA256,
             "credited_instant_gamma_events_per_geometry": 1_000},
            {"batch_id": BATCH0001_ID, "status": BATCH0001_STATUS,
             "ledger": smoke.rel(BATCH0001_LEDGER), "ledger_sha256": BATCH0001_SHA256,
             "credited_instant_gamma_events_per_geometry": 100_000},
            {"batch_id": BATCH0002_ID, "status": BATCH0002_STATUS,
             "ledger": smoke.rel(BATCH0002_LEDGER), "ledger_sha256": BATCH0002_SHA256,
             "credited_instant_gamma_events_per_geometry": 0},
        ],
        "prior_credit_equivalence": prior_credit_equivalence,
        "prior_read_only_revalidation": prior_checks,
        "resource_gate": {
            "authority": "actual corrected-keV batch0001 instant-gamma artifacts",
            "disk_safety_factor": DISK_SAFETY_FACTOR,
            "disk_reserve_bytes": DISK_RESERVE_BYTES,
            "point_estimated_output_bytes": point_bytes,
            "gated_estimated_output_bytes": gated_bytes,
            "point_estimated_run_phase_s": point_run_s,
            "automatic_delete": False,
        },
        "execution": {
            "requested_worker_cap": workers,
            "default_workers": DEFAULT_WORKERS,
            "absolute_worker_cap": MAX_WORKERS,
            "adaptive_ram_gate": "4-worker pilot; only measured process-group RSS can promote to 6 then 8",
            "min_available_ram_bytes": MIN_AVAILABLE_RAM_BYTES,
            "hard_available_ram_bytes": HARD_AVAILABLE_RAM_BYTES,
            "untrusted_initial_ram_bytes_per_worker": UNTRUSTED_RAM_BYTES_PER_WORKER,
            "wall_limit_hours": wall_limit_hours,
            "frozen_started_utc": frozen_started.isoformat(),
            "frozen_deadline_utc": frozen_deadline.isoformat(),
            "maximum_wall_limit_hours": MAX_WALL_HOURS,
            "stop_new_launch_reserve_seconds": STOP_LAUNCH_RESERVE_SECONDS,
            "validation_reserve_seconds": VALIDATION_RESERVE_SECONDS,
            "hang_rule": "terminate only after 15 minutes with neither process-group CPU progress nor output growth",
            "hang_seconds": HANG_SECONDS,
            "max_attempts_per_geometry_shard": MAX_ATTEMPTS,
            "retry_seed_policy": "same seed; replacement seeds are forbidden",
            "write_policy": "independent write-once attempt directories; atomic PASS receipts and ledgers",
            "resume_policy": (
                "revalidate immutable PASS receipts; never credit mere file existence; "
                "10M continuation is allowed only before frozen_deadline_utc, and later "
                "continuation requires a new non-overwriting disjoint-seed batch"
            ),
            "automatic_delete": False,
            "attempt_output_safety_factor": ATTEMPT_OUTPUT_SAFETY_FACTOR,
            "minimum_attempt_output_cap_bytes": MIN_ATTEMPT_OUTPUT_CAP_BYTES,
            "disk_emergency_margin_bytes": DISK_EMERGENCY_MARGIN_BYTES,
        },
        "aggregation_contract": {
            "pooling_boundary": "never pool across geometry, mode, or family",
            "TT_authority": TT_AUTHORITY,
            "stage5_acceptance": "only PASS stage5 dynamic report and ledger close cumulative 5M",
            "final_acceptance": "only PASS final dynamic report and ledger close cumulative 10M",
        },
        "toolchain": {
            "batch_runner": {"path": smoke.rel(THIS_FILE), "sha256": smoke.sha256(THIS_FILE)},
            "dynamic_validator": {"path": smoke.rel(VALIDATOR), "sha256": smoke.sha256(VALIDATOR)},
            "generic_runner_helpers": {"path": smoke.rel(GENERIC_RUNNER), "sha256": smoke.sha256(GENERIC_RUNNER)},
            "builder": {"path": smoke.rel(BUILDER), "sha256": smoke.sha256(BUILDER)},
            "static_validator": {"path": smoke.rel(STATIC_VALIDATOR), "sha256": smoke.sha256(STATIC_VALIDATOR)},
            "smoke_validator": {"path": smoke.rel(SMOKE_VALIDATOR), "sha256": smoke.sha256(SMOKE_VALIDATOR)},
            "seven_validator": {"path": smoke.rel(SEVEN_VALIDATOR), "sha256": smoke.sha256(SEVEN_VALIDATOR)},
            "muminus_validator": {"path": smoke.rel(MUMINUS_VALIDATOR), "sha256": smoke.sha256(MUMINUS_VALIDATOR)},
        },
        "transport": transport,
        "transport_core": _transport_core(transport),
        "geometry_bundles": bundles,
        "campaigns": campaigns,
    }, environment)


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/meminfo lacks MemAvailable")


def _validated_peak_rss_values() -> list[int]:
    values: list[int] = []
    for geometry in GEOMETRIES:
        root = campaign_dir(geometry) / "shards"
        if not root.is_dir():
            continue
        for receipt_path in root.glob("shard[0-9][0-9][0-9][0-9]/receipt.json"):
            try:
                value = int(_load_json(receipt_path).get("peak_process_group_rss_bytes", 0))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if value > 0:
                values.append(value)
    return values


def calibrated_worker_cap(requested_cap: int) -> tuple[int, int, int]:
    """Ramp 4 -> 6 -> 8 only after enough signed RSS observations."""
    peaks = sorted(_validated_peak_rss_values())
    assumed = UNTRUSTED_RAM_BYTES_PER_WORKER
    if peaks:
        p95_index = max(0, math.ceil(0.95 * len(peaks)) - 1)
        assumed = max(UNTRUSTED_RAM_BYTES_PER_WORKER, peaks[p95_index] * 2)
    cap = min(requested_cap, DEFAULT_WORKERS)
    current_available = mem_available_bytes()
    if requested_cap >= 6 and len(peaks) >= 8 and current_available >= MIN_AVAILABLE_RAM_BYTES + 6 * assumed:
        cap = 6
    if requested_cap >= 8 and len(peaks) >= 24 and current_available >= MIN_AVAILABLE_RAM_BYTES + 8 * assumed:
        cap = 8
    return cap, assumed, len(peaks)


def adaptive_worker_slots(requested_cap: int, running: int = 0) -> int:
    available = mem_available_bytes()
    if available <= MIN_AVAILABLE_RAM_BYTES:
        return 0
    calibrated_cap, bytes_per_worker, _ = calibrated_worker_cap(requested_cap)
    ram_slots = max(0, (available - MIN_AVAILABLE_RAM_BYTES) // bytes_per_worker)
    return max(0, min(calibrated_cap, int(ram_slots)) - running)


def _calibration_by_geometry(contract: dict[str, Any]) -> dict[str, float]:
    return {
        row["geometry"]: float(row["calibration"]["observed_bytes_per_event"])
        for row in contract["campaigns"]
    }


def _receipt_is_present(geometry: str, ordinal: int) -> bool:
    return geometry_receipt_path(geometry, ordinal).is_file()


def remaining_point_bytes(contract: dict[str, Any], stage_end: int = FINAL_SHARD_COUNT) -> float:
    rates = _calibration_by_geometry(contract)
    return math.fsum(
        shard_events(ordinal) * rates[geometry]
        for ordinal in range(1, stage_end + 1)
        for geometry in GEOMETRIES
        if not _receipt_is_present(geometry, ordinal)
    )


def _attempt_output_cap_bytes(contract: dict[str, Any], geometry: str, ordinal: int) -> int:
    rate = _calibration_by_geometry(contract)[geometry]
    point = rate * shard_events(ordinal)
    return int(math.ceil(max(MIN_ATTEMPT_OUTPUT_CAP_BYTES, ATTEMPT_OUTPUT_SAFETY_FACTOR * point)))


def disk_gate(
    contract: dict[str, Any],
    stage_end: int = FINAL_SHARD_COUNT,
    requested_workers: int | None = None,
) -> dict[str, Any]:
    free = shutil.disk_usage(RUN_ROOT).free
    remaining = remaining_point_bytes(contract, stage_end)
    worker_cap = int(requested_workers or contract["execution"]["requested_worker_cap"])
    largest_attempt = max(
        _attempt_output_cap_bytes(contract, geometry, ordinal)
        for geometry in GEOMETRIES
        for ordinal in (1, STAGE5_SHARD_COUNT)
    )
    active_burst = worker_cap * largest_attempt
    required = math.ceil(
        DISK_RESERVE_BYTES
        + DISK_SAFETY_FACTOR * remaining
        + max(active_burst, DISK_EMERGENCY_MARGIN_BYTES)
    )
    return {
        "free_bytes": free,
        "point_estimated_remaining_output_bytes": remaining,
        "safety_factor": DISK_SAFETY_FACTOR,
        "active_worker_burst_margin_bytes": active_burst,
        "emergency_abort_margin_bytes": DISK_EMERGENCY_MARGIN_BYTES,
        "reserve_bytes": DISK_RESERVE_BYTES,
        "required_free_bytes": required,
        "status": "PASS" if free >= required else "FAIL_INSUFFICIENT_FREE_SPACE",
    }


def _verify_toolchain_and_inputs(contract: dict[str, Any], environment: dict[str, str]) -> None:
    if smoke.sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("corrected source contract changed")
    for path, expected in (
        (BATCH0000_LEDGER, BATCH0000_SHA256),
        (BATCH0001_LEDGER, BATCH0001_SHA256),
        (BATCH0002_LEDGER, BATCH0002_SHA256),
    ):
        if smoke.sha256(path) != expected:
            raise RuntimeError(f"prior ledger changed: {smoke.rel(path)}")
    for name, record in contract["toolchain"].items():
        path = ROOT / record["path"]
        if not path.is_file() or smoke.sha256(path) != record["sha256"]:
            raise RuntimeError(f"toolchain changed: {name}")
    cosima = smoke.resolve_cosima(contract["transport"]["cosima"])
    current_environment, descriptor = smoke.resolve_transport_environment(cosima)
    current = smoke.build_transport_fingerprint(cosima, current_environment, descriptor)
    if _transport_core(current) != contract["transport_core"]:
        raise RuntimeError("transport fingerprint changed")
    source_contract = _load_json(SOURCE_CONTRACT)
    for geometry in GEOMETRIES:
        card = source_card_path(geometry)
        campaign = next(row for row in contract["campaigns"] if row["geometry"] == geometry)
        if smoke.sha256(card) != campaign["source_card_sha256"]:
            raise RuntimeError(f"corrected source card changed: {geometry}")
        migration = source_manifest_path(geometry)
        if smoke.sha256(migration) != campaign["source_migration_manifest_sha256"]:
            raise RuntimeError(f"source migration manifest changed: {geometry}")
        bundle = smoke.build_geometry_bundle(geometry, environment)
        if bundle != campaign["geometry_bundle"]:
            raise RuntimeError(f"geometry bundle changed: {geometry}")
        if common.source_contract_geometry_files(source_contract, geometry, environment) != bundle["files"]:
            raise RuntimeError(f"source/runtime geometry mismatch: {geometry}")
        for artifact in campaign["calibration"]["artifacts"]:
            path = ROOT / artifact["path"]
            if (
                not path.is_file()
                or path.stat().st_size != artifact["bytes"]
                or smoke.sha256(path) != artifact["sha256"]
            ):
                raise RuntimeError(f"calibration artifact changed: {artifact['path']}")


def _verify_attempt_inputs(
    contract: dict[str, Any],
    geometry: str,
    environment: dict[str, str],
) -> str:
    """Hash every live physics/tool input used by one attempt.

    This deliberately avoids invoking Cosima ``--help`` but hashes the pinned
    executable and shared libraries, source card and all 20 referenced spectra,
    the transitive geometry bundle, and controller/validator toolchain.
    """
    if not GLOBAL_CONTRACT.is_file() or _load_json(GLOBAL_CONTRACT) != contract:
        raise RuntimeError("global contract changed during campaign")
    records: list[dict[str, str]] = []

    def bind(path: Path, expected: str, label: str) -> None:
        if not path.is_file():
            raise RuntimeError(f"attempt input missing: {label}: {path}")
        observed = smoke.sha256(path)
        if observed != expected:
            raise RuntimeError(f"attempt input hash changed: {label}: {path}")
        records.append({"path": smoke.rel(path), "sha256": observed})

    bind(SOURCE_CONTRACT, SOURCE_CONTRACT_SHA256, "source contract")
    bind(BATCH0000_LEDGER, BATCH0000_SHA256, "batch0000 ledger")
    bind(BATCH0001_LEDGER, BATCH0001_SHA256, "batch0001 ledger")
    bind(BATCH0002_LEDGER, BATCH0002_SHA256, "batch0002 ledger")
    for name, record in contract["toolchain"].items():
        bind(ROOT / record["path"], record["sha256"], f"toolchain/{name}")
    cosima = Path(contract["transport"]["cosima"])
    bind(cosima, contract["transport"]["cosima_sha256"], "Cosima executable")
    for library in contract["transport"].get("shared_libraries", []):
        library_path = Path(library["path"])
        bind(library_path, library["sha256"], "transport shared library")
    relevant = contract["transport"]["environment"]["relevant_variables"]
    if {key: environment.get(key) for key in relevant} != relevant:
        raise RuntimeError("transport environment changed during campaign")

    campaign = next(row for row in contract["campaigns"] if row["geometry"] == geometry)
    bind(source_card_path(geometry), campaign["source_card_sha256"], f"{geometry} source card")
    bind(source_manifest_path(geometry), campaign["source_migration_manifest_sha256"],
         f"{geometry} source migration")
    source_contract = _load_json(SOURCE_CONTRACT)
    spectrum_hashes = {
        str(row["corrected_spectrum"]): str(row["corrected_sha256"])
        for row in source_contract["spectra"]["files"]
    }
    for line in source_card_path(geometry).read_text(encoding="utf-8", errors="replace").splitlines():
        match = common.SPECTRUM_RE.search(line)
        if not match:
            continue
        spectrum = common.resolve_repo_path(match.group(1))
        expected = spectrum_hashes.get(smoke.rel(spectrum))
        if expected is None:
            raise RuntimeError(f"unregistered spectrum in {geometry} gamma card: {spectrum}")
        bind(spectrum, expected, f"{geometry} corrected gamma spectrum")
    bundle = smoke.build_geometry_bundle(geometry, environment)
    if bundle != campaign["geometry_bundle"]:
        raise RuntimeError(f"geometry bundle changed during attempt: {geometry}")
    records.extend({"path": str(row["path"]), "sha256": str(row["sha256"])} for row in bundle["files"])
    records.sort(key=lambda row: (row["path"], row["sha256"]))
    return smoke.canonical_digest(records)


def _campaign_contract_payload(contract: dict[str, Any], geometry: str) -> dict[str, Any]:
    campaign = next(row for row in contract["campaigns"] if row["geometry"] == geometry)
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__SHARD_RECEIPTS_REQUIRED",
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "paired_shards": contract["statistics"]["paired_shards"],
        **campaign,
    }


def _normalization_payload(contract: dict[str, Any], geometry: str) -> dict[str, Any]:
    campaign_contract = campaign_dir(geometry) / "batch_contract.json"
    if not campaign_contract.is_file():
        raise RuntimeError(f"campaign contract missing before normalization: {geometry}")
    return {
        "schema_version": 1,
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": MODE,
        "selected_particles": [FAMILY],
        "excluded_particles": ["alpha", "eminus", "eplus", "muminus", "muplus", "n", "p"],
        "prior_events": PRIOR_EVENTS_PER_GEOMETRY,
        "new_events": NEW_EVENTS_PER_GEOMETRY,
        "final_cumulative_events": FINAL_TOTAL_EVENTS_PER_GEOMETRY,
        "jobs": FINAL_SHARD_COUNT,
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "store_simulation_info": "all",
        "store_isotopes": True,
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "batch_contract_sha256": smoke.sha256(campaign_contract),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "prior_merge_ledgers": [BATCH0000_SHA256, BATCH0001_SHA256, BATCH0002_SHA256],
        "aggregation": "sum(selected)/sum(TT) within this geometry+instant+gamma only",
        "automatic_delete": False,
        "raw_retention": "retain SIM/DAT/log/source and authority files; no controller deletion",
    }


def _prepare_campaign_roots(contract: dict[str, Any]) -> None:
    for geometry in GEOMETRIES:
        outdir = campaign_dir(geometry)
        outdir.mkdir(parents=True, exist_ok=True)
        campaign_contract = outdir / "batch_contract.json"
        payload = _campaign_contract_payload(contract, geometry)
        atomic_write_once_json(campaign_contract, payload)
        atomic_write_once_json(outdir / "normalization.json", _normalization_payload(contract, geometry))


def _execution_state(
    contract: dict[str, Any],
    proposed_started: datetime,
    proposed_deadline: datetime,
) -> dict[str, Any]:
    if EXECUTION_STATE.exists():
        state = _load_json(EXECUTION_STATE)
        _validate_execution_state(contract, state)
        return state
    frozen_started = datetime.fromisoformat(contract["execution"]["frozen_started_utc"])
    frozen_deadline = datetime.fromisoformat(contract["execution"]["frozen_deadline_utc"])
    state = {
        "schema_version": 1,
        "status": "RUNNING",
        "started_utc": frozen_started.isoformat(),
        "deadline_utc": frozen_deadline.isoformat(),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "completed_pair_shards": [],
        "heartbeat_utc": proposed_started.isoformat(),
    }
    atomic_replace_json(EXECUTION_STATE, state)
    _validate_execution_state(contract, state)
    return state


def _validate_execution_state(contract: dict[str, Any], state: dict[str, Any]) -> None:
    expected_hash = smoke.sha256(GLOBAL_CONTRACT)
    if state.get("global_contract_sha256") != expected_hash:
        raise RuntimeError("execution state belongs to a different global contract")
    try:
        started = datetime.fromisoformat(str(state["started_utc"]))
        deadline = datetime.fromisoformat(str(state["deadline_utc"]))
        frozen_started = datetime.fromisoformat(str(contract["execution"]["frozen_started_utc"]))
        frozen_deadline = datetime.fromisoformat(str(contract["execution"]["frozen_deadline_utc"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"execution state time contract is malformed: {exc}") from exc
    for label, value in (("started", started), ("deadline", deadline),
                         ("frozen_started", frozen_started), ("frozen_deadline", frozen_deadline)):
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise RuntimeError(f"execution state {label} is not aware UTC")
    if started != frozen_started or deadline != frozen_deadline:
        raise RuntimeError("execution state immutable start/deadline differs from global contract")
    if deadline <= started:
        raise RuntimeError("execution state deadline must be after start")
    expected_seconds = float(contract["execution"]["wall_limit_hours"]) * 3600.0
    if not math.isclose((deadline - started).total_seconds(), expected_seconds, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError("execution state window does not equal frozen wall limit")


def _update_state(**updates: Any) -> None:
    forbidden = STATE_IMMUTABLE_KEYS & set(updates)
    if forbidden:
        raise RuntimeError(f"refusing immutable execution-state update: {sorted(forbidden)}")
    with _STATE_LOCK:
        state = _load_json(EXECUTION_STATE)
        if GLOBAL_CONTRACT.is_file():
            _validate_execution_state(_load_json(GLOBAL_CONTRACT), state)
        state.update(updates)
        state["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_replace_json(EXECUTION_STATE, state)


def _job(geometry: str, ordinal: int, attempt: int, cosima: str) -> dict[str, Any]:
    outdir = attempt_dir(geometry, ordinal, attempt)
    name = f"Background_gamma_fullsphere20_batch0003_shard{ordinal:04d}"
    sim_prefix = outdir / name
    isotope_prefix = outdir / f"{name}.dat"
    return {
        "job_name": name,
        "particle": FAMILY,
        "mode": MODE,
        "events": shard_events(ordinal),
        "rep": ordinal,
        "part": 1,
        "seed": shard_seed(ordinal),
        "source": str(source_card_path(geometry).resolve()),
        "temp_source": str(outdir / f"{name}.source"),
        "sim_prefix": str(sim_prefix),
        "iso_prefix": str(isotope_prefix),
        "sim_path": str(Path(f"{sim_prefix}.inc1.id1.sim.gz")),
        "dat_path": str(Path(f"{isotope_prefix}.inc1.dat")),
        "log": str(outdir / f"{name}.log"),
        "cosima": cosima,
        "skip_existing": False,
        "cleanup_source": False,
        "store_isotopes": True,
        "geometry": geometry,
        "ordinal": ordinal,
        "attempt": attempt,
    }


def _attempt_contract_payload(
    contract: dict[str, Any],
    geometry: str,
    ordinal: int,
    attempt: int,
    job: dict[str, Any],
    input_digest_pre: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "FROZEN_ATTEMPT__DYNAMIC_VALIDATION_REQUIRED",
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "geometry": geometry,
        "mode": MODE,
        "family": FAMILY,
        "ordinal": ordinal,
        "attempt": attempt,
        "events": shard_events(ordinal),
        "seed": shard_seed(ordinal),
        "job_name": job["job_name"],
        "source_card": smoke.rel(source_card_path(geometry)),
        "source_card_sha256": smoke.sha256(source_card_path(geometry)),
        "job_source": smoke.rel(Path(job["temp_source"])),
        "job_source_sha256": smoke.sha256(Path(job["temp_source"])),
        "sim": smoke.rel(Path(job["sim_path"])),
        "isotope_dat": smoke.rel(Path(job["dat_path"])),
        "log": smoke.rel(Path(job["log"])),
        "cosima_command": [job["cosima"], "-s", str(job["seed"]), job["temp_source"]],
        "attempt_output_cap_bytes": _attempt_output_cap_bytes(contract, geometry, ordinal),
        "frozen_input_bundle_sha256_pre": input_digest_pre,
    }


def _process_group_cpu_ticks(pgid: int) -> int:
    total = 0
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat_path.read_text(encoding="utf-8").split()
            if int(fields[4]) == pgid:
                total += int(fields[13]) + int(fields[14])
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def _process_group_rss_bytes(pgid: int) -> int:
    total = 0
    page_size = os.sysconf("SC_PAGE_SIZE")
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat_path.read_text(encoding="utf-8").split()
            if int(fields[4]) != pgid:
                continue
            statm = stat_path.with_name("statm").read_text(encoding="utf-8").split()
            total += int(statm[1]) * page_size
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            continue
    return total


def _artifact_growth(job: dict[str, Any]) -> int:
    total = 0
    for key in ("sim_path", "dat_path", "log"):
        path = Path(job[key])
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def _terminate_process_group(proc: subprocess.Popen[Any]) -> None:
    pgid = proc.pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        if proc.poll() is None:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        return
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    group_deadline = time.monotonic() + 8
    group_exists = True
    while time.monotonic() < group_deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            group_exists = False
            break
        time.sleep(0.1)
    if group_exists:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def _run_attempt(
    contract: dict[str, Any],
    environment: dict[str, str],
    geometry: str,
    ordinal: int,
    attempt: int,
    deadline: datetime,
) -> dict[str, Any]:
    runtime = _load_generic_runner()
    input_digest_pre = _verify_attempt_inputs(contract, geometry, environment)
    outdir = attempt_dir(geometry, ordinal, attempt)
    outdir.mkdir(parents=True, exist_ok=False)
    job = _job(geometry, ordinal, attempt, contract["transport"]["cosima"])
    runtime.patch_source(job)
    attempt_contract = _attempt_contract_payload(
        contract, geometry, ordinal, attempt, job, input_digest_pre
    )
    atomic_write_once_json(outdir / "attempt_contract.json", attempt_contract)

    log_path = Path(job["log"])
    command = attempt_contract["cosima_command"]
    started = time.monotonic()
    last_activity = started
    last_heartbeat = started
    last_integrity_check = started
    reason = "process_exit"
    returncode: int | None = None
    peak_rss_bytes = 0
    caught: BaseException | None = None
    proc: subprocess.Popen[Any] | None = None
    with log_path.open("x", encoding="utf-8", buffering=1) as handle:
        handle.write(f"job_name={job['job_name']}\n")
        handle.write(
            f"geometry={geometry} mode={MODE} particle={FAMILY} ordinal={ordinal} "
            f"attempt={attempt} events={job['events']} seed={job['seed']}\n"
        )
        handle.write(f"source={job['source']}\n")
        handle.write(f"temp_source={job['temp_source']}\n")
        handle.write("-" * 72 + "\n")
        handle.write(f"cosima_command={' '.join(command)}\n")
        handle.flush()
        try:
            proc = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            _register_process(proc)
            previous_cpu = _process_group_cpu_ticks(proc.pid)
            previous_growth = _artifact_growth(job)
            peak_rss_bytes = _process_group_rss_bytes(proc.pid)
            while proc.poll() is None:
                time.sleep(WATCHDOG_POLL_SECONDS)
                now = time.monotonic()
                cpu = _process_group_cpu_ticks(proc.pid)
                growth = _artifact_growth(job)
                rss_bytes = _process_group_rss_bytes(proc.pid)
                peak_rss_bytes = max(peak_rss_bytes, rss_bytes)
                free_disk = shutil.disk_usage(RUN_ROOT).free
                available_ram = mem_available_bytes()
                if cpu > previous_cpu or growth > previous_growth:
                    last_activity = now
                previous_cpu = cpu
                previous_growth = growth
                if _ABORT_EVENT.is_set():
                    reason = "global_resource_abort"
                    _terminate_process_group(proc)
                    break
                if free_disk <= DISK_RESERVE_BYTES + DISK_EMERGENCY_MARGIN_BYTES:
                    reason = "hard_disk_floor_20GB_plus_margin"
                    _ABORT_EVENT.set()
                    _terminate_process_group(proc)
                    break
                if growth > int(attempt_contract["attempt_output_cap_bytes"]):
                    reason = "attempt_output_cap_exceeded"
                    _ABORT_EVENT.set()
                    _terminate_process_group(proc)
                    break
                if available_ram <= HARD_AVAILABLE_RAM_BYTES:
                    reason = "hard_low_memory_1p5GB"
                    _ABORT_EVENT.set()
                    _terminate_process_group(proc)
                    break
                if datetime.now(timezone.utc) >= deadline:
                    reason = "transport_drain_deadline"
                    _ABORT_EVENT.set()
                    _terminate_process_group(proc)
                    break
                if now - last_activity >= HANG_SECONDS:
                    reason = "watchdog_no_cpu_and_no_growth_15m"
                    _terminate_process_group(proc)
                    break
                if now - last_integrity_check >= HEARTBEAT_SECONDS:
                    heartbeat_digest = _verify_attempt_inputs(contract, geometry, environment)
                    if heartbeat_digest != input_digest_pre:
                        raise RuntimeError("frozen attempt input digest drifted during transport")
                    last_integrity_check = now
                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    _update_state(
                        last_worker_heartbeat={
                            "geometry": geometry,
                            "ordinal": ordinal,
                            "attempt": attempt,
                            "pid": proc.pid,
                            "cpu_ticks": cpu,
                            "artifact_bytes": growth,
                            "process_group_rss_bytes": rss_bytes,
                            "peak_process_group_rss_bytes": peak_rss_bytes,
                        },
                        free_disk_bytes=free_disk,
                        mem_available_bytes=available_ram,
                    )
                    last_heartbeat = now
        except BaseException as exc:
            caught = exc
            reason = f"supervisor_exception_{type(exc).__name__}"
            _ABORT_EVENT.set()
        finally:
            if proc is not None:
                # Unconditional PGID cleanup catches a leader-exited child.
                try:
                    _terminate_process_group(proc)
                    try:
                        returncode = proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        _terminate_process_group(proc)
                        returncode = proc.poll()
                finally:
                    _unregister_process(proc)
            final_growth = _artifact_growth(job)
            final_free_disk = shutil.disk_usage(RUN_ROOT).free
            if final_growth > int(attempt_contract["attempt_output_cap_bytes"]):
                _ABORT_EVENT.set()
                if caught is None:
                    caught = RuntimeError("attempt output cap exceeded by final flush")
                reason = "attempt_output_cap_exceeded_final_flush"
            if final_free_disk <= DISK_RESERVE_BYTES + DISK_EMERGENCY_MARGIN_BYTES:
                _ABORT_EVENT.set()
                if caught is None:
                    caught = RuntimeError("hard disk floor crossed by final flush")
                reason = "hard_disk_floor_crossed_final_flush"
            input_digest_post: str | None = None
            try:
                input_digest_post = _verify_attempt_inputs(contract, geometry, environment)
                if input_digest_post != input_digest_pre:
                    raise RuntimeError("frozen attempt input digest differs pre/post transport")
            except BaseException as integrity_exc:
                _ABORT_EVENT.set()
                if caught is None:
                    caught = integrity_exc
                reason = f"input_integrity_exception_{type(integrity_exc).__name__}"
            handle.write("-" * 72 + "\n")
            handle.write(f"watchdog_reason={reason}\n")
            handle.write(f"peak_process_group_rss_bytes={peak_rss_bytes}\n")
            handle.write(f"attempt_output_cap_bytes={attempt_contract['attempt_output_cap_bytes']}\n")
            handle.write(f"frozen_input_bundle_sha256_pre={input_digest_pre}\n")
            handle.write(f"frozen_input_bundle_sha256_post={input_digest_post or 'FAIL'}\n")
            handle.write(f"returncode={returncode if returncode is not None else -999}\n")
            handle.write(f"wall_s={time.monotonic() - started:.3f}\n")
    if caught is not None:
        raise caught
    return {
        "geometry": geometry,
        "ordinal": ordinal,
        "attempt": attempt,
        "seed": shard_seed(ordinal),
        "events": shard_events(ordinal),
        "returncode": returncode,
        "watchdog_reason": reason,
        "peak_process_group_rss_bytes": peak_rss_bytes,
        "attempt_dir": smoke.rel(outdir),
    }


def _invoke_shard_validator(
    geometry: str,
    ordinal: int,
    attempt: int,
    deadline: datetime,
) -> bool:
    result = _run_supervised_command(
        [
            sys.executable,
            str(VALIDATOR),
            "--shard",
            "--geometry",
            geometry,
            "--ordinal",
            str(ordinal),
            "--attempt",
            str(attempt),
        ],
        deadline=deadline,
        fixed_timeout_s=SHARD_VALIDATION_TIMEOUT_SECONDS,
    )
    return result.returncode == 0 and geometry_receipt_path(geometry, ordinal).is_file()


def _ensure_geometry_shard(
    contract: dict[str, Any],
    environment: dict[str, str],
    geometry: str,
    ordinal: int,
    deadline: datetime,
) -> dict[str, Any]:
    receipt_path = geometry_receipt_path(geometry, ordinal)
    if receipt_path.is_file():
        # A receipt is never trusted only because it exists.  The per-shard
        # validator verifies its bound attempt and all artifact hashes.
        receipt = _load_json(receipt_path)
        attempt = int(receipt["selected_attempt"])
        if _invoke_shard_validator(geometry, ordinal, attempt, deadline):
            return _load_json(receipt_path)
        raise RuntimeError(f"immutable receipt revalidation failed: {geometry}/shard{ordinal:04d}")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        outdir = attempt_dir(geometry, ordinal, attempt)
        if outdir.exists():
            if _invoke_shard_validator(geometry, ordinal, attempt, deadline):
                return _load_json(receipt_path)
            continue
        if _ABORT_EVENT.is_set():
            raise RuntimeError("global resource abort set; retry suppressed")
        if datetime.now(timezone.utc) >= deadline:
            raise RuntimeError("global 12h deadline reached before shard dispatch")
        _run_attempt(contract, environment, geometry, ordinal, attempt, deadline)
        if _invoke_shard_validator(geometry, ordinal, attempt, deadline):
            return _load_json(receipt_path)
        if _ABORT_EVENT.is_set():
            raise RuntimeError("global resource abort set after attempt; retry suppressed")
    raise RuntimeError(
        f"{geometry}/shard{ordinal:04d} failed {MAX_ATTEMPTS} same-seed attempts; manual review required"
    )


def _adopt_existing_geometry_shard(
    geometry: str,
    ordinal: int,
    validation_deadline: datetime,
) -> bool:
    """Revalidate existing receipt/attempt state without ever launching Cosima."""
    receipt_path = geometry_receipt_path(geometry, ordinal)
    if receipt_path.is_file():
        receipt = _load_json(receipt_path)
        attempt = int(receipt["selected_attempt"])
        if not _invoke_shard_validator(geometry, ordinal, attempt, validation_deadline):
            raise RuntimeError(f"immutable receipt revalidation failed: {geometry}/shard{ordinal:04d}")
        return True
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt_dir(geometry, ordinal, attempt).exists():
            if _invoke_shard_validator(geometry, ordinal, attempt, validation_deadline):
                return True
    return False


def _pair_receipt_payload(ordinal: int) -> dict[str, Any]:
    receipts: dict[str, dict[str, Any]] = {}
    for geometry in GEOMETRIES:
        path = geometry_receipt_path(geometry, ordinal)
        if not path.is_file():
            raise RuntimeError(f"cannot pair missing receipt: {geometry}/shard{ordinal:04d}")
        receipts[geometry] = {
            "path": smoke.rel(path),
            "sha256": smoke.sha256(path),
            "selected_attempt": _load_json(path)["selected_attempt"],
        }
    return {
        "schema_version": 1,
        "status": "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "ordinal": ordinal,
        "events_per_geometry": shard_events(ordinal),
        "paired_seed": shard_seed(ordinal),
        "pairing_rule": PAIRING_RULE,
        "statistical_semantics": PAIRING_STATISTICAL_SEMANTICS,
        "geometry_receipts": receipts,
    }


def _write_pair_receipt(ordinal: int) -> dict[str, Any]:
    payload = _pair_receipt_payload(ordinal)
    path = pair_receipt_path(ordinal)
    atomic_write_once_json(path, payload)
    return payload


def _remaining_seconds(deadline: datetime) -> float:
    return (deadline - datetime.now(timezone.utc)).total_seconds()


def _run_stage(
    contract: dict[str, Any],
    environment: dict[str, str],
    start_ordinal: int,
    end_ordinal: int,
    requested_workers: int,
    launch_deadline: datetime,
    transport_deadline: datetime,
    validation_deadline: datetime,
) -> None:
    # Adoption is a validation operation, not a new transport launch.  It is
    # therefore allowed in the reserved T+9..T+12 validation window while new
    # Cosima attempts remain subject to T+8/T+9 gates.
    existing = [
        (ordinal, geometry)
        for ordinal in range(start_ordinal, end_ordinal + 1)
        for geometry in GEOMETRIES
        if geometry_receipt_path(geometry, ordinal).is_file()
        or any(attempt_dir(geometry, ordinal, attempt).exists() for attempt in range(1, MAX_ATTEMPTS + 1))
    ]
    adoption_failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(requested_workers, DEFAULT_WORKERS)) as executor:
        futures = {
            executor.submit(_adopt_existing_geometry_shard, geometry, ordinal, validation_deadline):
            (ordinal, geometry)
            for ordinal, geometry in existing
        }
        for future in concurrent.futures.as_completed(futures):
            ordinal, geometry = futures[future]
            try:
                adopted = future.result()
            except Exception as exc:
                adoption_failures.append(f"{geometry}/shard{ordinal:04d}: {exc}")
                continue
            if adopted and all(geometry_receipt_path(name, ordinal).is_file() for name in GEOMETRIES):
                _write_pair_receipt(ordinal)
    if adoption_failures:
        _update_state(status="PAUSED_REQUIRES_REVIEW", errors=adoption_failures)
        raise SystemExit("batch0003 receipt adoption failed: " + " | ".join(adoption_failures))

    pending = [
        (ordinal, geometry)
        for ordinal in range(start_ordinal, end_ordinal + 1)
        for geometry in GEOMETRIES
        if not geometry_receipt_path(geometry, ordinal).is_file()
    ]
    failures: list[str] = []
    futures: dict[concurrent.futures.Future[dict[str, Any]], tuple[int, str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=requested_workers) as executor:
        while pending or futures:
            if failures:
                break
            if _ABORT_EVENT.is_set():
                failures.append("global resource abort set")
                break
            gate = disk_gate(contract, end_ordinal, requested_workers)
            if gate["status"] != "PASS":
                _ABORT_EVENT.set()
                failures.append("disk gate failed: " + json.dumps(gate, sort_keys=True))
                break
            if datetime.now(timezone.utc) >= launch_deadline and pending:
                failures.append("T+8h stop-launch gate reached before stage completion; active jobs drain to T+9h")
                break
            slots = adaptive_worker_slots(requested_workers, len(futures))
            while pending and slots > 0:
                ordinal, geometry = pending.pop(0)
                future = executor.submit(
                    _ensure_geometry_shard,
                    contract,
                    environment,
                    geometry,
                    ordinal,
                    transport_deadline,
                )
                futures[future] = (ordinal, geometry)
                slots -= 1
            if not futures:
                if pending:
                    _update_state(
                        status="PAUSED_RESOURCE_GATE",
                        free_disk_bytes=shutil.disk_usage(RUN_ROOT).free,
                        mem_available_bytes=mem_available_bytes(),
                    )
                    time.sleep(min(WATCHDOG_POLL_SECONDS, 10))
                    continue
                break
            done, _ = concurrent.futures.wait(
                futures,
                timeout=WATCHDOG_POLL_SECONDS,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                ordinal, geometry = futures.pop(future)
                try:
                    future.result()
                except Exception as exc:
                    failures.append(f"{geometry}/shard{ordinal:04d}: {exc}")
                    _ABORT_EVENT.set()
                    continue
                if all(geometry_receipt_path(name, ordinal).is_file() for name in GEOMETRIES):
                    _write_pair_receipt(ordinal)
            completed = [
                ordinal for ordinal in range(1, end_ordinal + 1)
                if pair_receipt_path(ordinal).is_file()
            ]
            _update_state(
                status="RUNNING",
                active_jobs=len(futures),
                pending_jobs=len(pending),
                completed_pair_shards=completed,
                free_disk_bytes=shutil.disk_usage(RUN_ROOT).free,
                mem_available_bytes=mem_available_bytes(),
                calibrated_worker_cap=calibrated_worker_cap(requested_workers)[0],
                signed_rss_observations=calibrated_worker_cap(requested_workers)[2],
            )
    if failures:
        _update_state(status="PAUSED_REQUIRES_REVIEW", errors=failures)
        raise SystemExit("batch0003 paused: " + " | ".join(failures))
    for ordinal in range(start_ordinal, end_ordinal + 1):
        if not pair_receipt_path(ordinal).is_file():
            _write_pair_receipt(ordinal)


def _run_stage_validator(stage: str, deadline: datetime) -> None:
    ledger = STAGE5_LEDGER if stage == "5m" else FINAL_LEDGER
    if ledger.exists():
        check = _run_supervised_command(
            [sys.executable, str(VALIDATOR), "--stage", stage, "--check"],
            deadline=deadline,
            fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
        )
        if check.returncode != 0:
            raise SystemExit(f"batch0003 {stage} existing authority revalidation failed")
        return
    result = _run_supervised_command(
        [sys.executable, str(VALIDATOR), "--stage", stage],
        deadline=deadline,
        fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
    )
    if result.returncode != 0:
        raise SystemExit(f"batch0003 {stage} dynamic validation failed")


def _load_or_create_contract(
    cosima_arg: str | None,
    workers: int,
    wall_limit_hours: float,
    preflight_deadline: datetime,
) -> tuple[dict[str, Any], dict[str, str]]:
    if GLOBAL_CONTRACT.exists():
        contract = _load_json(GLOBAL_CONTRACT)
        if contract.get("batch_id") != BATCH_ID or contract.get("campaign_version") != CAMPAIGN_VERSION:
            raise SystemExit("existing batch0003 contract identity mismatch")
        if int(contract["execution"]["requested_worker_cap"]) != workers:
            raise SystemExit("resume must use the worker cap frozen in the batch0003 contract")
        if not math.isclose(float(contract["execution"]["wall_limit_hours"]), wall_limit_hours):
            raise SystemExit("resume must use the wall limit frozen in the batch0003 contract")
        cosima = smoke.resolve_cosima(contract["transport"]["cosima"])
        environment, _ = smoke.resolve_transport_environment(cosima)
        _verify_toolchain_and_inputs(contract, environment)
        return contract, environment

    for path in (EXECUTION_STATE, STAGE5_VALIDATION_REPORT, STAGE5_LEDGER, FINAL_VALIDATION_REPORT, FINAL_LEDGER):
        if path.exists():
            raise SystemExit(f"batch0003 authority output exists without global contract: {smoke.rel(path)}")
    if PAIR_RECEIPT_ROOT.exists() or any(campaign_dir(geometry).exists() for geometry in GEOMETRIES):
        raise SystemExit("batch0003 shard outputs exist without global contract; refusing adoption")
    contract, environment = build_contract(
        cosima_arg,
        workers,
        wall_limit_hours,
        deadline=preflight_deadline,
    )
    atomic_write_once_json(GLOBAL_CONTRACT, contract)
    _verify_toolchain_and_inputs(contract, environment)
    return contract, environment


def _run(
    contract: dict[str, Any],
    environment: dict[str, str],
    workers: int,
    proposed_started: datetime,
    proposed_deadline: datetime,
    stop_after: str,
) -> int:
    _ABORT_EVENT.clear()
    _prepare_campaign_roots(contract)
    state = _execution_state(contract, proposed_started, proposed_deadline)
    deadline = datetime.fromisoformat(state["deadline_utc"])
    if datetime.now(timezone.utc) >= deadline:
        raise SystemExit("batch0003 frozen 12h deadline has expired; no transport launched")

    launch_deadline = deadline - timedelta(seconds=STOP_LAUNCH_RESERVE_SECONDS)
    transport_deadline = deadline - timedelta(seconds=VALIDATION_RESERVE_SECONDS)
    if FINAL_LEDGER.exists():
        _run_stage_validator("10m", deadline)
        _update_state(status="PASS__BATCH0003_10M_MERGE_ELIGIBLE", active_jobs=0, pending_jobs=0)
        return 0
    if not STAGE5_LEDGER.exists():
        _run_stage(
            contract,
            environment,
            1,
            STAGE5_SHARD_COUNT,
            workers,
            launch_deadline,
            transport_deadline,
            deadline,
        )
    _run_stage_validator("5m", deadline)
    if stop_after == "5m":
        _update_state(status="PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE", active_jobs=0, pending_jobs=0)
        return 0
    _run_stage(
        contract,
        environment,
        STAGE5_SHARD_COUNT + 1,
        FINAL_SHARD_COUNT,
        workers,
        launch_deadline,
        transport_deadline,
        deadline,
    )
    _run_stage_validator("10m", deadline)
    _update_state(status="PASS__BATCH0003_10M_MERGE_ELIGIBLE", active_jobs=0, pending_jobs=0)
    return 0


def plan_summary(contract: dict[str, Any], stop_after: str = "5m") -> dict[str, Any]:
    stage_end = STAGE5_SHARD_COUNT if stop_after == "5m" else FINAL_SHARD_COUNT
    cumulative_target = (
        STAGE5_TOTAL_EVENTS_PER_GEOMETRY if stop_after == "5m"
        else FINAL_TOTAL_EVENTS_PER_GEOMETRY
    )
    requested_new_per_geometry = cumulative_target - PRIOR_EVENTS_PER_GEOMETRY
    gate = disk_gate(
        contract,
        stage_end=stage_end,
        requested_workers=int(contract["execution"]["requested_worker_cap"]),
    )
    return {
        "batch_id": contract["batch_id"],
        "campaign_version": contract["campaign_version"],
        "transport_launched": False,
        "requested_stop_after": stop_after,
        "requested_stage": {
            "cumulative_events_per_geometry": cumulative_target,
            "new_events_per_geometry": requested_new_per_geometry,
            "new_events_total": requested_new_per_geometry * len(GEOMETRIES),
            "last_shard_ordinal": stage_end,
            "point_estimated_output_bytes": math.fsum(
                row["calibration"]["observed_bytes_per_event"] * requested_new_per_geometry
                for row in contract["campaigns"]
            ),
            "point_estimated_run_phase_s": math.fsum(
                row["calibration"]["observed_run_phase_s_per_event"] * requested_new_per_geometry
                for row in contract["campaigns"]
            ),
            "authority_on_pass": (
                "PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE" if stop_after == "5m"
                else "PASS__BATCH0003_10M_MERGE_ELIGIBLE"
            ),
        },
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "source_scope": contract["source_scope"],
        "statistics": {
            key: contract["statistics"][key]
            for key in (
                "prior_events_per_geometry",
                "new_events_per_geometry",
                "stage5_cumulative_events_per_geometry",
                "final_cumulative_events_per_geometry",
                "new_events_total",
                "shards_per_geometry",
            )
        },
        "checkpoints": [
            contract["statistics"]["paired_shards"][STAGE5_SHARD_COUNT - 1],
            contract["statistics"]["paired_shards"][FINAL_SHARD_COUNT - 1],
        ],
        "pairing": contract["pairing"],
        "lineage": contract["lineage"],
        "prior_read_only_revalidation": contract["prior_read_only_revalidation"],
        "campaigns": [
            {
                "geometry": row["geometry"],
                "outdir": row["outdir"],
                "source_card_sha256": row["source_card_sha256"],
                "geometry_bundle_sha256": row["geometry_bundle"]["bundle_sha256"],
                "requested_stage_new_events": requested_new_per_geometry,
                "requested_stage_point_estimated_output_bytes": (
                    row["calibration"]["observed_bytes_per_event"] * requested_new_per_geometry
                ),
                "requested_stage_point_estimated_run_phase_s": (
                    row["calibration"]["observed_run_phase_s_per_event"] * requested_new_per_geometry
                ),
                "calibration": {
                    key: row["calibration"][key]
                    for key in (
                        "events",
                        "observed_bytes_per_event",
                        "observed_run_phase_s_per_event",
                        "point_estimated_output_bytes",
                        "gated_estimated_output_bytes",
                        "point_estimated_run_phase_s",
                    )
                },
            }
            for row in contract["campaigns"]
        ],
        "resource_gate": {
            "scope": f"requested {stop_after} stage",
            "point_estimated_output_bytes": math.fsum(
                row["calibration"]["observed_bytes_per_event"] * requested_new_per_geometry
                for row in contract["campaigns"]
            ),
            "point_estimated_run_phase_s": math.fsum(
                row["calibration"]["observed_run_phase_s_per_event"] * requested_new_per_geometry
                for row in contract["campaigns"]
            ),
            "disk_safety_factor": DISK_SAFETY_FACTOR,
            "disk_reserve_bytes": DISK_RESERVE_BYTES,
            "automatic_delete": False,
        },
        "full_10m_resource_ceiling": contract["resource_gate"],
        "live_disk_gate": gate,
        "execution": contract["execution"],
        "transport": {
            "cosima": contract["transport"]["cosima"],
            "cosima_sha256": contract["transport"]["cosima_sha256"],
            "shared_libraries_bundle_sha256": contract["transport"]["shared_libraries_bundle_sha256"],
            "relevant_variables_sha256": contract["transport"]["environment"]["relevant_variables_sha256"],
        },
        "toolchain": contract["toolchain"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help=(
            "run read-only preflight gates and print the fixed plan; never launch transport "
            "(may invoke Cosima --help only for fingerprinting)"
        ),
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--wall-limit-hours", type=float, default=MAX_WALL_HOURS)
    parser.add_argument(
        "--stop-after",
        choices=("5m", "10m"),
        default="5m",
        help=(
            "publish 5M authority and exit (default), or explicitly continue toward 10M "
            "only before frozen_deadline_utc; later work requires a new batch"
        ),
    )
    parser.add_argument("--cosima", default=None)
    args = parser.parse_args()
    session_started = datetime.now(timezone.utc)
    session_deadline = session_started + timedelta(hours=args.wall_limit_hours)
    if args.print_plan:
        contract, _ = build_contract(
            args.cosima,
            args.workers,
            args.wall_limit_hours,
            deadline=session_deadline,
        )
        summary = plan_summary(contract, args.stop_after)
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if summary["live_disk_gate"]["status"] == "PASS" else 2
    lock_handle = _acquire_controller_lock()
    previous_handlers: dict[int, Any] = {}
    try:
        _refuse_live_batch0003_processes()
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, _controller_signal_handler)
        contract, environment = _load_or_create_contract(
            args.cosima,
            args.workers,
            args.wall_limit_hours,
            session_deadline,
        )
        return _run(
            contract,
            environment,
            args.workers,
            session_started,
            session_deadline,
            args.stop_after,
        )
    finally:
        _ABORT_EVENT.set()
        _terminate_all_active_process_groups()
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
