#!/usr/bin/env python3
"""Run the corrected-keV batch0004 1M-equivalent screening checkpoint.

Batch0004 is a deliberately reduced-statistics, non-proton screening batch. It
adds gamma only in activation-buildup mode and adds alpha, electron, positron,
negative-muon, positive-muon, and neutron histories in instant and buildup
modes for both retained geometries.  Exact retained credit from batch0000 and
batch0001 is deducted; batch0002 also already closes the negative-muon instant
target.  Each family/mode is an independent write-once checkpoint.

The controller inherits (and never extends) batch0003's frozen 12-hour wall
window.  It refuses transport until canonical batch0003 prefix76 or stage5
instant-gamma authority is present and passes its profile-specific gates.  ``--print-plan`` is output-free
and never launches transport; it may invoke ``cosima --help`` solely to build a
transport fingerprint.
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
VALIDATOR = PACKAGE / "code/validate_mergeable_seven_family_1m_screening_batch0004.py"
SMOKE_RUNNER = PACKAGE / "code/run_mergeable_two_geometry_smoke.py"
MUMINUS_RUNNER = PACKAGE / "code/run_mergeable_muminus_instant_pair_batch0002.py"
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
BATCH0002_CONTRACT = RUN_ROOT / "muminus_instant_pair_batch0002_v1_contract.json"
BATCH0002_CONTRACT_SHA256 = "91b570b26524bc51394af065131da75e16d168e2567502f8ab0594a98dc40743"
BATCH0003_RUNNER = PACKAGE / "code/run_mergeable_gamma_instant_batch0003.py"
BATCH0003_VALIDATOR = PACKAGE / "code/validate_mergeable_gamma_instant_batch0003.py"
BATCH0003_CONTRACT = RUN_ROOT / "gamma_instant_batch0003_v1_contract.json"
BATCH0003_STATE = RUN_ROOT / "gamma_instant_batch0003_v1_state.json"
BATCH0003_REPORT = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_validation.json"
BATCH0003_LEDGER = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_ledger.json"
BATCH0003_ID = "corrected_original_gamma_instant_batch0003"
BATCH0003_STATUS = "PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE"
PREFIX_CHECKPOINT_ORDINAL = 76
PREFIX_PRIOR_EVENTS_PER_GEOMETRY = 101_000
PREFIX_NEW_EVENTS_PER_GEOMETRY = 1_900_000
PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY = 2_001_000
PREFIX_VALIDATION_STATUS = "PASS__PARTIAL_PREFIX_VALIDATED"
PREFIX_LEDGER_STATUS = "PARTIAL_PREFIX_MERGE_ELIGIBLE"
PREFIX_VALIDATOR = (
    PACKAGE
    / "gamma_prefix_checkpoint_20260811/code/validate_gamma_batch0003_prefix_checkpoint.py"
)
# Updated only after the independent prefix-package review freezes its source.
PREFIX_VALIDATOR_SHA256 = "636492766f70350f65907a957b723ec3465e65e42e71778ae52f57c1803a526d"
PREFIX_AUTHORITY_ROOT = RUN_ROOT / "gamma_instant_batch0003_prefix_checkpoints_20260811"
PREFIX_REPORT = (
    PREFIX_AUTHORITY_ROOT
    / "gamma_instant_batch0003_prefix_shard0076_v1_validation.json"
)
PREFIX_LEDGER = (
    PREFIX_AUTHORITY_ROOT
    / "gamma_instant_batch0003_prefix_shard0076_v1_ledger.json"
)

BATCH_ID = "corrected_original_seven_family_1m_screening_batch0004"
CAMPAIGN_VERSION = "mergeable_seven_family_1m_equivalent_screening_v1"
GEOMETRIES = smoke.GEOMETRIES
FARFIELD_RADIUS_CM = 60.0

FAMILIES = ("gamma", "n", "eplus", "alpha", "eminus", "muplus", "muminus")
MODES = ("instant", "buildup")
TARGET_EVENTS = {
    "gamma": 1_000_000,
    "n": 96_310,
    "eplus": 24_370,
    "alpha": 2_390,
    "eminus": 41_460,
    "muplus": 1_160,
    "muminus": 1_040,
}
PRIOR_EVENTS = {
    ("gamma", "buildup"): 101_000,
    ("n", "instant"): 9_727,
    ("n", "buildup"): 9_727,
    ("eplus", "instant"): 2_461,
    ("eplus", "buildup"): 2_461,
    ("alpha", "instant"): 241,
    ("alpha", "buildup"): 241,
    ("eminus", "instant"): 4_187,
    ("eminus", "buildup"): 4_187,
    ("muplus", "instant"): 117,
    ("muplus", "buildup"): 117,
    ("muminus", "instant"): 10_105,
    ("muminus", "buildup"): 105,
}
SHARD_EVENTS_BY_FAMILY = {
    "gamma": 25_000,
    "n": 5_000,
    "eplus": 2_500,
    "alpha": 250,
    "eminus": 5_000,
    "muplus": 2_000,
    "muminus": 2_000,
}
STAGE_ORDER = (
    "gamma_buildup",
    "n_instant", "n_buildup",
    "eplus_instant", "eplus_buildup",
    "alpha_instant", "alpha_buildup",
    "eminus_instant", "eminus_buildup",
    "muplus_instant", "muplus_buildup",
    "muminus_buildup",
)
SEED_BASE = 871_100_004
SEED_STRIDE = 7_927

DEFAULT_WORKERS = 4
MAX_WORKERS = 6
MIN_AVAILABLE_RAM_BYTES = 2_000_000_000
HARD_AVAILABLE_RAM_BYTES = 1_500_000_000
UNTRUSTED_RAM_BYTES_PER_WORKER = 1_000_000_000
DISK_RESERVE_BYTES = 20 * 1024**3
DISK_EMERGENCY_MARGIN_BYTES = MAX_WORKERS * 500_000_000 + 2 * 1024**3
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

GLOBAL_CONTRACT = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_contract.json"
EXECUTION_STATE = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_state.json"
PAIR_RECEIPT_ROOT = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_pair_receipts"
CONTROLLER_LOCK = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_controller.lock"
CHECKPOINT_ROOT = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_checkpoints"
FINAL_VALIDATION_REPORT = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_validation.json"
FINAL_LEDGER = RUN_ROOT / "seven_family_1m_screening_batch0004_v1_ledger.json"

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

TOOLCHAIN_PATHS = {
    "batch_runner": THIS_FILE,
    "dynamic_validator": VALIDATOR,
    "smoke_runner_helpers": SMOKE_RUNNER,
    "muminus_runner_helpers": MUMINUS_RUNNER,
    "generic_runner_helpers": GENERIC_RUNNER,
    "builder": BUILDER,
    "static_validator": STATIC_VALIDATOR,
    "smoke_validator": SMOKE_VALIDATOR,
    "seven_validator": SEVEN_VALIDATOR,
    "muminus_validator": MUMINUS_VALIDATOR,
    "batch0003_runner": BATCH0003_RUNNER,
    "batch0003_validator": BATCH0003_VALIDATOR,
    "batch0003_prefix_validator": PREFIX_VALIDATOR,
}


def toolchain_payload() -> dict[str, dict[str, str]]:
    return {
        name: {"path": smoke.rel(path), "sha256": smoke.sha256(path)}
        for name, path in TOOLCHAIN_PATHS.items()
    }

_ACTIVE_PROCESS_LOCK = threading.RLock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen[Any]] = {}
_SIGNAL_CLEANUP_IN_PROGRESS = False
STATE_IMMUTABLE_KEYS = frozenset({
    "started_utc", "deadline_utc", "global_contract_sha256", "parent_state_sha256"
})


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_authority_json(path: Path) -> tuple[dict[str, Any], str]:
    """Read one canonical authority once and reject symlink/TOCTOU changes."""
    if path.is_symlink():
        raise SystemExit(f"canonical authority must not be a symlink: {smoke.rel(path)}")
    try:
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise SystemExit(f"cannot read canonical authority {smoke.rel(path)}: {exc}") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != after_id or len(raw) != after.st_size or after.st_size <= 0:
        raise SystemExit(f"canonical authority changed while read: {smoke.rel(path)}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"canonical authority JSON invalid: {smoke.rel(path)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"canonical authority is not a JSON object: {smoke.rel(path)}")
    return payload, hashlib.sha256(raw).hexdigest()


def _validate_prefix76_authority() -> tuple[str, str]:
    report, report_hash = _stable_authority_json(PREFIX_REPORT)
    ledger, ledger_hash = _stable_authority_json(PREFIX_LEDGER)
    canonical_report_hash = hashlib.sha256(
        (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()
    canonical_ledger_hash = hashlib.sha256(
        (json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()
    if report_hash != canonical_report_hash or ledger_hash != canonical_ledger_hash:
        raise SystemExit("batch0003 prefix76 authority bytes are not canonical JSON")
    validator_path = smoke.rel(PREFIX_VALIDATOR)
    expected_common = {
        "batch_id": BATCH0003_ID,
        "campaign_version": "mergeable_gamma_instant_10m_v1",
        "prior_events_per_geometry": PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
        "new_events_per_geometry": PREFIX_NEW_EVENTS_PER_GEOMETRY,
        "cumulative_events_per_geometry": PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
        "validated_pair_count": PREFIX_CHECKPOINT_ORDINAL,
        "global_contract": smoke.rel(BATCH0003_CONTRACT),
        "global_contract_sha256": smoke.sha256(BATCH0003_CONTRACT),
        "validator": validator_path,
        "validator_sha256": PREFIX_VALIDATOR_SHA256,
    }
    for key, expected in expected_common.items():
        if report.get(key) != expected or ledger.get(key) != expected:
            raise SystemExit(f"batch0003 prefix76 authority field mismatch: {key}")
    if (
        report.get("status") != PREFIX_VALIDATION_STATUS
        or report.get("merge_eligibility") != PREFIX_LEDGER_STATUS
        or report.get("errors") != []
    ):
        raise SystemExit("batch0003 prefix76 validation report is not canonical PASS")
    selection = report.get("selection", {})
    if selection != {
        "selected_prefix_start_ordinal": 1,
        "selected_prefix_end_ordinal": PREFIX_CHECKPOINT_ORDINAL,
        "complete_contiguous_pairs_required_and_snapshotted": PREFIX_CHECKPOINT_ORDINAL,
        "preferred_ordinal": True,
    }:
        raise SystemExit("batch0003 prefix76 report selection mismatch")
    if (
        ledger.get("status") != PREFIX_LEDGER_STATUS
        or ledger.get("validation_status") != PREFIX_VALIDATION_STATUS
        or ledger.get("prefix_start_ordinal") != 1
        or ledger.get("prefix_end_ordinal") != PREFIX_CHECKPOINT_ORDINAL
        or ledger.get("validation_report") != smoke.rel(PREFIX_REPORT)
        or ledger.get("validation_report_sha256") != report_hash
        or ledger.get("errors") != []
    ):
        raise SystemExit("batch0003 prefix76 ledger is not canonical merge authority")
    if report.get("campaigns") != ledger.get("campaigns"):
        raise SystemExit("batch0003 prefix76 report/ledger campaigns differ")
    campaigns = ledger.get("campaigns", [])
    if (
        len(campaigns) != len(GEOMETRIES)
        or {row.get("geometry") for row in campaigns} != set(GEOMETRIES)
        or any(
            row.get("mode") != "instant"
            or row.get("family") != "gamma"
            or row.get("prefix_end_ordinal") != PREFIX_CHECKPOINT_ORDINAL
            or row.get("cumulative_events") != PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY
            for row in campaigns
        )
    ):
        raise SystemExit("batch0003 prefix76 campaign exposure mismatch")
    return report_hash, ledger_hash


def _validate_stage5_authority() -> tuple[str, str]:
    report, report_hash = _stable_authority_json(BATCH0003_REPORT)
    ledger, ledger_hash = _stable_authority_json(BATCH0003_LEDGER)
    if (
        report.get("batch_id") != BATCH0003_ID
        or report.get("status") != "PASS"
        or report.get("stage") != "5m"
        or report.get("cumulative_target_events_per_geometry") != 5_000_000
        or report.get("errors") != []
    ):
        raise SystemExit("batch0003 stage5 validation report is not canonical PASS")
    if (
        ledger.get("batch_id") != BATCH0003_ID
        or ledger.get("status") != BATCH0003_STATUS
        or ledger.get("stage") != "5m"
        or ledger.get("cumulative_target_events_per_geometry") != 5_000_000
        or ledger.get("validation_report") != smoke.rel(BATCH0003_REPORT)
        or ledger.get("validation_report_sha256") != report_hash
        or ledger.get("errors") != []
    ):
        raise SystemExit("batch0003 stage5 ledger is not canonical merge authority")
    return report_hash, ledger_hash


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
        raise SystemExit("another batch0004 controller already holds the campaign lock")
    return handle


def _live_batch0004_processes(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    """Find stale live children whose command line targets a batch0004 attempt."""
    markers = [
        str(campaign_dir(geometry, stage["key"]).resolve())
        for stage in stage_specs()
        for geometry in GEOMETRIES
    ]
    markers.append("_batch0004_")
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


def _refuse_live_batch0004_processes() -> None:
    live = _live_batch0004_processes()
    if live:
        detail = "; ".join(f"pid={row['pid']} {row['command']}" for row in live[:4])
        raise SystemExit("live batch0004 transport/child detected; refusing concurrent resume: " + detail)


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


def _split_stage_key(stage_key: str) -> tuple[str, str]:
    family, mode = stage_key.rsplit("_", 1)
    if family not in FAMILIES or mode not in MODES:
        raise ValueError(f"unknown batch0004 stage: {stage_key}")
    return family, mode


def stage_specs() -> list[dict[str, Any]]:
    """Return the immutable global-ordinal schedule in priority order."""
    rows: list[dict[str, Any]] = []
    next_global = 1
    for priority, key in enumerate(STAGE_ORDER, 1):
        family, mode = _split_stage_key(key)
        prior = PRIOR_EVENTS[(family, mode)]
        target = TARGET_EVENTS[family]
        new_events = target - prior
        if new_events <= 0:
            raise AssertionError(f"stage {key} has no positive increment")
        standard = SHARD_EVENTS_BY_FAMILY[family]
        full, remainder = divmod(new_events, standard)
        chunks = [standard] * full + ([remainder] if remainder else [])
        start = next_global
        end = start + len(chunks) - 1
        rows.append({
            "key": key,
            "priority": priority,
            "family": family,
            "mode": mode,
            "prior_events_per_geometry": prior,
            "target_events_per_geometry": target,
            "new_events_per_geometry": new_events,
            "standard_shard_events": standard,
            "shard_events": chunks,
            "paired_shards": len(chunks),
            "global_start_ordinal": start,
            "global_end_ordinal": end,
        })
        next_global = end + 1
    return rows


STAGE_SPECS = stage_specs()
STAGE_BY_KEY = {row["key"]: row for row in STAGE_SPECS}
FINAL_SHARD_COUNT = sum(int(row["paired_shards"]) for row in STAGE_SPECS)
FINAL_JOB_COUNT = FINAL_SHARD_COUNT * len(GEOMETRIES)
TOTAL_NEW_EVENTS = sum(
    int(row["new_events_per_geometry"]) * len(GEOMETRIES)
    for row in STAGE_SPECS
)


def shard_spec(ordinal: int) -> dict[str, Any]:
    if not 1 <= ordinal <= FINAL_SHARD_COUNT:
        raise ValueError(f"shard ordinal out of range: {ordinal}")
    for stage in STAGE_SPECS:
        start = int(stage["global_start_ordinal"])
        end = int(stage["global_end_ordinal"])
        if start <= ordinal <= end:
            local = ordinal - start + 1
            return {
                **stage,
                "global_ordinal": ordinal,
                "stage_ordinal": local,
                "events": int(stage["shard_events"][local - 1]),
            }
    raise AssertionError(f"unmapped shard ordinal: {ordinal}")


def campaign_dir(geometry: str, stage_key: str) -> Path:
    family, mode = _split_stage_key(stage_key)
    return RUN_ROOT / geometry / f"{mode}_{family}_screening_batch0004_v1"


def shard_dir(geometry: str, ordinal: int) -> Path:
    spec = shard_spec(ordinal)
    return campaign_dir(geometry, str(spec["key"])) / "shards" / f"shard{int(spec['stage_ordinal']):04d}"


def attempt_dir(geometry: str, ordinal: int, attempt: int) -> Path:
    return shard_dir(geometry, ordinal) / f"attempt{attempt:02d}"


def geometry_receipt_path(geometry: str, ordinal: int) -> Path:
    return shard_dir(geometry, ordinal) / "receipt.json"


def pair_receipt_path(ordinal: int) -> Path:
    spec = shard_spec(ordinal)
    return PAIR_RECEIPT_ROOT / str(spec["key"]) / f"shard{int(spec['stage_ordinal']):04d}.json"


def source_manifest_path(geometry: str) -> Path:
    return GEOMETRIES[geometry] / "source_migration_manifest.json"


def source_card_path(geometry: str, family: str) -> Path:
    return GEOMETRIES[geometry] / f"Background_{family}_fullsphere20.source"


def shard_events(ordinal: int) -> int:
    return int(shard_spec(ordinal)["events"])


def shard_seed(ordinal: int) -> int:
    if not 1 <= ordinal <= FINAL_SHARD_COUNT:
        raise ValueError(f"shard ordinal out of range: {ordinal}")
    return SEED_BASE + ordinal * SEED_STRIDE


def planned_shards() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for ordinal in range(1, FINAL_SHARD_COUNT + 1):
        spec = shard_spec(ordinal)
        stage = STAGE_BY_KEY[str(spec["key"])]
        before = sum(int(value) for value in stage["shard_events"][: int(spec["stage_ordinal"]) - 1])
        cumulative = int(stage["prior_events_per_geometry"]) + before + int(spec["events"])
        rows.append({
            "global_ordinal": ordinal,
            "stage": str(spec["key"]),
            "stage_ordinal": int(spec["stage_ordinal"]),
            "family": str(spec["family"]),
            "mode": str(spec["mode"]),
            "events": int(spec["events"]),
            "seed": shard_seed(ordinal),
            "cumulative_events_per_geometry": cumulative,
            "checkpoint": (
                "family_mode_1m_equivalent_screening"
                if int(spec["stage_ordinal"]) == int(stage["paired_shards"])
                else ""
            ),
        })
    for stage in STAGE_SPECS:
        final = next(row for row in reversed(rows) if row["stage"] == stage["key"])
        if int(final["cumulative_events_per_geometry"]) != int(stage["target_events_per_geometry"]):
            raise AssertionError(f"internal stage schedule does not close {stage['key']}")
    return rows


def checkpoint_report_path(stage_key: str) -> Path:
    if stage_key not in STAGE_BY_KEY:
        raise ValueError(f"unknown stage: {stage_key}")
    return CHECKPOINT_ROOT / f"{stage_key}_validation.json"


def checkpoint_ledger_path(stage_key: str) -> Path:
    if stage_key not in STAGE_BY_KEY:
        raise ValueError(f"unknown stage: {stage_key}")
    return CHECKPOINT_ROOT / f"{stage_key}_ledger.json"


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


def _family_jobs(
    ledger: dict[str, Any], geometry: str, mode: str, family: str
) -> list[dict[str, Any]]:
    jobs = [
        job for job in _campaign(ledger, geometry, mode).get("jobs", [])
        if job.get("family") == family
    ]
    if not jobs:
        raise SystemExit(f"prior ledger has no jobs: {geometry}/{mode}/{family}")
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
    require_predecessor_authority: bool,
    deadline: datetime | None = None,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]
]:
    required = (
        THIS_FILE, VALIDATOR, GENERIC_RUNNER, BUILDER, STATIC_VALIDATOR,
        SMOKE_RUNNER, MUMINUS_RUNNER,
        SMOKE_VALIDATOR, SEVEN_VALIDATOR, MUMINUS_VALIDATOR, SOURCE_CONTRACT,
        BATCH0000_LEDGER, BATCH0001_LEDGER, BATCH0002_LEDGER, BATCH0002_CONTRACT,
        BATCH0003_RUNNER, BATCH0003_VALIDATOR, PREFIX_VALIDATOR,
        BATCH0003_CONTRACT, BATCH0003_STATE,
    )
    missing = [smoke.rel(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing batch0004 input(s): " + ", ".join(missing))
    for path, expected in (
        (SOURCE_CONTRACT, SOURCE_CONTRACT_SHA256),
        (BATCH0000_LEDGER, BATCH0000_SHA256),
        (BATCH0001_LEDGER, BATCH0001_SHA256),
        (BATCH0002_LEDGER, BATCH0002_SHA256),
        (BATCH0002_CONTRACT, BATCH0002_CONTRACT_SHA256),
        (PREFIX_VALIDATOR, PREFIX_VALIDATOR_SHA256),
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
        for stage in STAGE_SPECS:
            family = str(stage["family"])
            mode = str(stage["mode"])
            credited0 = sum(int(job["events"]) for job in _family_jobs(ledger0, geometry, mode, family))
            credited1 = sum(int(job["events"]) for job in _family_jobs(ledger1, geometry, mode, family))
            credited2 = 0
            if family == "muminus" and mode == "instant":
                credited2 = sum(
                    int(job["events"])
                    for job in _family_jobs(ledger2, geometry, mode, family)
                )
            observed = credited0 + credited1 + credited2
            expected = int(PRIOR_EVENTS[(family, mode)])
            if observed != expected:
                raise SystemExit(
                    f"{geometry}/{stage['key']}: prior credit {credited0}+{credited1}+{credited2}="
                    f"{observed}, expected {expected}"
                )
            card = source_card_path(geometry, family)
            text = card.read_text(encoding="utf-8", errors="replace")
            corrected_root = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
            if text.count(corrected_root) != 20:
                raise SystemExit(f"{geometry}/{family}: corrected-keV references are not exactly 20")
            if "cosima_spectra_dp_2602units" in text:
                raise SystemExit(f"{geometry}/{family}: legacy energy-axis reference remains")
            if text.count("StoreSimulationInfo all") != 1:
                raise SystemExit(f"{geometry}/{family}: StoreSimulationInfo all contract mismatch")
        if not source_manifest_path(geometry).is_file():
            raise SystemExit(f"{geometry}: source migration manifest missing")
        credited_mu_instant = (
            sum(int(job["events"]) for job in _family_jobs(ledger0, geometry, "instant", "muminus"))
            + sum(int(job["events"]) for job in _family_jobs(ledger1, geometry, "instant", "muminus"))
            + sum(int(job["events"]) for job in _family_jobs(ledger2, geometry, "instant", "muminus"))
        )
        if credited_mu_instant != PRIOR_EVENTS[("muminus", "instant")]:
            raise SystemExit(f"{geometry}: muminus instant prior-only credit mismatch")

    parent_contract = _load_json(BATCH0003_CONTRACT)
    parent_state, parent_state_hash = _stable_authority_json(BATCH0003_STATE)
    if parent_contract.get("batch_id") != BATCH0003_ID:
        raise SystemExit("batch0003 global contract identity mismatch")
    parent_started = datetime.fromisoformat(str(parent_state.get("started_utc")))
    parent_deadline = datetime.fromisoformat(str(parent_state.get("deadline_utc")))
    if parent_started.tzinfo is None or parent_deadline.tzinfo is None:
        raise SystemExit("batch0003 inherited execution timestamps are not timezone-aware")
    if not math.isclose((parent_deadline - parent_started).total_seconds(), 12 * 3600, abs_tol=1e-6):
        raise SystemExit("batch0003 inherited execution window is not exactly 12 hours")
    if parent_state.get("global_contract_sha256") != smoke.sha256(BATCH0003_CONTRACT):
        raise SystemExit("batch0003 state/contract hash binding mismatch")
    parent_planned_seeds = [
        int(row["seed"])
        for row in parent_contract.get("statistics", {}).get("paired_shards", [])
    ]
    if len(parent_planned_seeds) != len(set(parent_planned_seeds)):
        raise SystemExit("batch0003 planned seed registry is not unique")

    dependency: dict[str, Any] = {
        "batch_id": BATCH0003_ID,
        "selection_policy": "prefer canonical prefix ordinal76; otherwise canonical stage5",
        "profile": "wait",
        "required_status": [PREFIX_LEDGER_STATUS, BATCH0003_STATUS],
        "contract": smoke.rel(BATCH0003_CONTRACT),
        "contract_sha256": smoke.sha256(BATCH0003_CONTRACT),
        "state": smoke.rel(BATCH0003_STATE),
        "state_sha256_at_batch0004_freeze": parent_state_hash,
        "inherited_started_utc": parent_started.isoformat(),
        "inherited_deadline_utc": parent_deadline.isoformat(),
        "prefix_validator": smoke.rel(PREFIX_VALIDATOR),
        "prefix_validator_sha256": PREFIX_VALIDATOR_SHA256,
        "candidate_prefix_report": smoke.rel(PREFIX_REPORT),
        "candidate_prefix_ledger": smoke.rel(PREFIX_LEDGER),
        "candidate_stage5_report": smoke.rel(BATCH0003_REPORT),
        "candidate_stage5_ledger": smoke.rel(BATCH0003_LEDGER),
        "gamma_exposure": None,
        "seed_exclusion": {
            "scope": "all batch0003 planned seeds, including ordinals beyond selected authority",
            "planned_seed_count": len(parent_planned_seeds),
            "planned_seed_list_sha256": _json_sha256(parent_planned_seeds),
        },
        "prior_credit_rule": (
            "batch0003 instant-gamma exposure is not deducted from batch0004 gamma-buildup "
            "or any non-gamma family+mode target"
        ),
        "gate": "WAIT__BATCH0003_PREFIX76_OR_STAGE5_NOT_YET_AUTHORITY",
    }
    prefix_exists = (PREFIX_REPORT.exists(), PREFIX_LEDGER.exists())
    stage5_exists = (BATCH0003_REPORT.exists(), BATCH0003_LEDGER.exists())
    if any(prefix_exists):
        if not all(prefix_exists):
            raise SystemExit("batch0003 prefix76 report/ledger authority pair is incomplete")
        report_hash, ledger_hash = _validate_prefix76_authority()
        dependency.update({
            "profile": "prefix_ordinal76",
            "selected_status": PREFIX_LEDGER_STATUS,
            "gate": "PASS__BATCH0003_PREFIX76_AUTHORITY_PRESENT",
            "report": smoke.rel(PREFIX_REPORT),
            "report_sha256": report_hash,
            "ledger": smoke.rel(PREFIX_LEDGER),
            "ledger_sha256": ledger_hash,
            "gamma_exposure": {
                "mode": "instant",
                "prefix_start_ordinal": 1,
                "prefix_end_ordinal": PREFIX_CHECKPOINT_ORDINAL,
                "prior_events_per_geometry": PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
                "new_events_per_geometry": PREFIX_NEW_EVENTS_PER_GEOMETRY,
                "cumulative_events_per_geometry": PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
                "credited_to_batch0004_buildup": False,
            },
        })
    elif any(stage5_exists):
        if not all(stage5_exists):
            raise SystemExit("batch0003 stage5 report/ledger authority pair is incomplete")
        report_hash, ledger_hash = _validate_stage5_authority()
        dependency.update({
            "profile": "stage5",
            "selected_status": BATCH0003_STATUS,
            "gate": "PASS__BATCH0003_STAGE5_AUTHORITY_PRESENT",
            "report": smoke.rel(BATCH0003_REPORT),
            "report_sha256": report_hash,
            "ledger": smoke.rel(BATCH0003_LEDGER),
            "ledger_sha256": ledger_hash,
            "gamma_exposure": {
                "mode": "instant",
                "stage": "5m",
                "prior_events_per_geometry": PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
                "new_events_per_geometry": 4_899_000,
                "cumulative_events_per_geometry": 5_000_000,
                "credited_to_batch0004_buildup": False,
            },
        })
    if require_predecessor_authority and not str(dependency["gate"]).startswith("PASS__"):
        raise SystemExit(
            "canonical batch0003 prefix76 or stage5 PASS authority is required before "
            "batch0004 transport"
        )

    historical = _prior_seeds(ledger0, ledger1, ledger2)
    historical.update(parent_planned_seeds)
    planned = [shard_seed(ordinal) for ordinal in range(1, FINAL_SHARD_COUNT + 1)]
    if len(planned) != len(set(planned)):
        raise SystemExit("batch0004 planned seed registry is not unique")
    overlap = historical & set(planned)
    if overlap:
        raise SystemExit(f"batch0004 planned seed collision(s): {sorted(overlap)[:10]}")

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
        if require_predecessor_authority:
            if dependency["profile"] == "stage5":
                result = _run_supervised_command(
                    [sys.executable, str(BATCH0003_VALIDATOR), "--stage", "5m", "--check"],
                    deadline=deadline,
                    fixed_timeout_s=PREFLIGHT_COMMAND_TIMEOUT_SECONDS,
                )
                if result.returncode != 0:
                    sys.stderr.write(result.stdout)
                    raise SystemExit("batch0003 stage5 read-only authority validation failed")
                checks.append({
                    "label": "batch0003 stage5 exact authority revalidation",
                    "command": [sys.executable, smoke.rel(BATCH0003_VALIDATOR), "--stage", "5m", "--check"],
                    "returncode": 0,
                    "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
                })
            elif dependency["profile"] == "prefix_ordinal76":
                checks.append({
                    "label": "batch0003 canonical prefix76 authority binding",
                    "mode": "canonical report/ledger only; no attempt read",
                    "validator": smoke.rel(PREFIX_VALIDATOR),
                    "validator_sha256": PREFIX_VALIDATOR_SHA256,
                    "report_sha256": dependency["report_sha256"],
                    "ledger_sha256": dependency["ledger_sha256"],
                })
    return ledger0, ledger1, ledger2, dependency, checks


def _calibration(
    ledger1: dict[str, Any],
    geometry: str,
    stage: dict[str, Any],
    *,
    verify_artifact_hashes: bool,
) -> dict[str, Any]:
    family = str(stage["family"])
    mode = str(stage["mode"])
    jobs = _family_jobs(ledger1, geometry, mode, family)
    calibration_events = sum(int(job["events"]) for job in jobs)
    if calibration_events <= 0:
        raise SystemExit(f"{geometry}/{stage['key']}: empty batch0001 calibration")
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
                raise SystemExit(f"missing calibration artifact: {smoke.rel(path)}")
            if verify_artifact_hashes and smoke.sha256(path) != job[hash_key]:
                raise SystemExit(f"calibration artifact hash changed: {smoke.rel(path)}")
            artifact_bytes += path.stat().st_size
            artifacts.append({
                "path": smoke.rel(path),
                "sha256": job[hash_key],
                "bytes": path.stat().st_size,
            })
        parsed = runtime.parse_log(ROOT / job["log"])
        if parsed.get("cpu_s") is None:
            raise SystemExit(f"calibration log lacks run-phase time: {job['log']}")
        run_phase_s += float(parsed["cpu_s"])
    bytes_per_event = artifact_bytes / calibration_events
    seconds_per_event = run_phase_s / calibration_events
    new_events = int(stage["new_events_per_geometry"])
    return {
        "authority_batch": BATCH0001_ID,
        "geometry": geometry,
        "mode": mode,
        "family": family,
        "events": calibration_events,
        "jobs": len(jobs),
        "artifact_bytes": artifact_bytes,
        "run_phase_s": run_phase_s,
        "observed_bytes_per_event": bytes_per_event,
        "observed_run_phase_s_per_event": seconds_per_event,
        "new_events": new_events,
        "point_estimated_output_bytes": bytes_per_event * new_events,
        "gated_estimated_output_bytes": bytes_per_event * new_events * DISK_SAFETY_FACTOR,
        "point_estimated_run_phase_s": seconds_per_event * new_events,
        "artifacts": artifacts,
    }


def _transport_core(transport: dict[str, Any]) -> dict[str, Any]:
    return batch2._transport_core(transport)


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _physics_record_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    """Return transport/geometry authority, following a pinned contract if needed."""
    if isinstance(ledger.get("transport"), dict) and isinstance(ledger.get("geometry_bundles"), dict):
        return ledger
    contract_value = ledger.get("global_contract")
    expected_hash = ledger.get("global_contract_sha256")
    if not isinstance(contract_value, str) or not isinstance(expected_hash, str):
        raise SystemExit(f"credited ledger lacks physics authority: {ledger.get('batch_id')}")
    path = common.resolve_repo_path(contract_value)
    if not path.is_file() or smoke.sha256(path) != expected_hash:
        raise SystemExit(f"credited ledger global contract changed: {ledger.get('batch_id')}")
    record = _load_json(path)
    if record.get("batch_id") != ledger.get("batch_id"):
        raise SystemExit(f"credited ledger/contract identity mismatch: {ledger.get('batch_id')}")
    return record


def require_prior_credit_equivalence(
    ledger0: dict[str, Any],
    ledger1: dict[str, Any],
    ledger2: dict[str, Any],
    dependency: dict[str, Any],
    current_transport: dict[str, Any],
    current_bundles: dict[str, Any],
) -> dict[str, Any]:
    """Prove all credited corrected-keV batches share the current physics inputs."""
    if "transport" not in ledger0 or "transport" not in ledger1:
        raise SystemExit("credited prior ledger lacks transport fingerprint")
    core0 = _transport_core(ledger0["transport"])
    core1 = _transport_core(ledger1["transport"])
    current_core = _transport_core(current_transport)
    if core0 != core1:
        raise SystemExit("batch0000/batch0001 credited transport cores differ")
    if core0 != current_core:
        raise SystemExit("credited batch0000/1 transport core differs from proposed batch0004 transport")
    physics2 = _physics_record_from_ledger(ledger2)
    if _transport_core(physics2.get("transport", {})) != current_core:
        raise SystemExit("batch0002 credited transport core differs from proposed batch0004 transport")
    profile = dependency.get("profile")
    if profile in ("stage5", "wait"):
        parent_record, observed = _stable_authority_json(BATCH0003_CONTRACT)
        if observed != dependency.get("contract_sha256"):
            raise SystemExit("batch0003 contract changed during predecessor equivalence gate")
        if _transport_core(parent_record.get("transport", {})) != current_core:
            raise SystemExit("batch0003 predecessor transport core differs from batch0004")
        parent_bundles = parent_record.get("geometry_bundles", {})
    elif profile == "prefix_ordinal76":
        parent_record, observed = _stable_authority_json(ROOT / dependency["report"])
        if observed != dependency.get("report_sha256"):
            raise SystemExit("batch0003 prefix76 report changed during equivalence gate")
        if (
            parent_record.get("transport_revalidation", {}).get("transport_core_sha256")
            != _json_sha256(current_core)
        ):
            raise SystemExit("batch0003 prefix76 transport core differs from batch0004")
        parent_bundles = parent_record.get("geometry_bundles", {})
    else:
        raise SystemExit("batch0003 predecessor authority profile is unknown")
    for geometry in GEOMETRIES:
        bundle0 = ledger0.get("geometry_bundles", {}).get(geometry)
        bundle1 = ledger1.get("geometry_bundles", {}).get(geometry)
        current = current_bundles.get(geometry)
        if bundle0 is None or bundle1 is None:
            raise SystemExit(f"credited prior ledger lacks geometry bundle: {geometry}")
        if bundle0 != bundle1:
            raise SystemExit(f"batch0000/batch0001 credited geometry bundles differ: {geometry}")
        if physics2.get("geometry_bundles", {}).get(geometry) != current:
            raise SystemExit(f"batch0002 credited geometry bundle differs from batch0004: {geometry}")
        if parent_bundles.get(geometry) != current:
            raise SystemExit(f"batch0003 credited geometry bundle differs from batch0004: {geometry}")
        if bundle0 != current:
            raise SystemExit(f"credited batch0000/1 geometry bundle differs from batch0004: {geometry}")
    return {
        "status": "PASS__ALL_CREDITED_PHYSICS_INPUTS_EQUAL_CURRENT",
        "credited_batches": [BATCH0000_ID, BATCH0001_ID, BATCH0002_ID]
        + ([BATCH0003_ID] if profile != "wait" else []),
        "batch0003_predecessor_credited": profile != "wait",
        "batch0003_predecessor_profile": profile,
        "batch0003_gamma_exposure": dependency.get("gamma_exposure"),
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
    *,
    require_predecessor_authority: bool,
    full_preflight: bool,
    deadline: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    if not 1 <= workers <= MAX_WORKERS:
        raise SystemExit(f"--workers must be within 1..{MAX_WORKERS}")
    ledger0, ledger1, ledger2, dependency, prior_checks = run_preflight(
        revalidate_prior=full_preflight,
        require_predecessor_authority=require_predecessor_authority,
        deadline=deadline,
    )
    frozen_started = datetime.fromisoformat(str(dependency["inherited_started_utc"]))
    frozen_deadline = datetime.fromisoformat(str(dependency["inherited_deadline_utc"]))
    if deadline is not None and deadline > frozen_deadline:
        raise SystemExit("batch0004 preflight deadline cannot extend batch0003 frozen deadline")
    cosima = smoke.resolve_cosima(cosima_arg)
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    source_contract = _load_json(SOURCE_CONTRACT)
    bundles = {geometry: smoke.build_geometry_bundle(geometry, environment) for geometry in GEOMETRIES}
    prior_credit_equivalence = require_prior_credit_equivalence(
        ledger0,
        ledger1,
        ledger2,
        dependency,
        transport,
        bundles,
    )
    campaigns: list[dict[str, Any]] = []
    for stage in STAGE_SPECS:
        for geometry in GEOMETRIES:
            bundle = bundles[geometry]
            if common.source_contract_geometry_files(source_contract, geometry, environment) != bundle["files"]:
                raise SystemExit(f"source/runtime geometry bundle mismatch: {geometry}")
            migration = source_manifest_path(geometry)
            family = str(stage["family"])
            campaigns.append({
                "stage": stage["key"],
                "priority": stage["priority"],
                "geometry": geometry,
                "mode": stage["mode"],
                "family": family,
                "outdir": smoke.rel(campaign_dir(geometry, str(stage["key"]))),
                "source_card": smoke.rel(source_card_path(geometry, family)),
                "source_card_sha256": smoke.sha256(source_card_path(geometry, family)),
                "source_migration_manifest": smoke.rel(migration),
                "source_migration_manifest_sha256": smoke.sha256(migration),
                "geometry_bundle": bundle,
                "prior_events": stage["prior_events_per_geometry"],
                "new_events": stage["new_events_per_geometry"],
                "final_cumulative_events": stage["target_events_per_geometry"],
                "global_start_ordinal": stage["global_start_ordinal"],
                "global_end_ordinal": stage["global_end_ordinal"],
                "paired_shards": stage["paired_shards"],
                "calibration": _calibration(
                    ledger1,
                    geometry,
                    stage,
                    verify_artifact_hashes=full_preflight,
                ),
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
            "included_families": list(FAMILIES),
            "excluded_families": ["p"],
            "modes": list(MODES),
            "gamma_modes": ["buildup"],
            "angular_bins_per_family": 20,
            "mono_511_added": False,
            "store_simulation_info": "all",
            "policy": "gamma buildup plus six non-proton families in instant and buildup",
        },
        "statistics": {
            "screening_semantics": (
                "reduced 1M gamma-equivalent checkpoint; not historical full-stat and not a "
                "replacement for isotope-volume resolved delayed authority"
            ),
            "historical_non_gamma_full_units": 800,
            "screening_units": 10,
            "historical_non_gamma_fraction": 0.0125,
            "new_events_total": TOTAL_NEW_EVENTS,
            "paired_shards_total": FINAL_SHARD_COUNT,
            "transport_jobs_total": FINAL_JOB_COUNT,
            "prior_only_closed_cells": [{
                "family": "muminus",
                "mode": "instant",
                "credited_events_per_geometry": PRIOR_EVENTS[("muminus", "instant")],
                "screening_target_events_per_geometry": TARGET_EVENTS["muminus"],
                "new_events": 0,
                "reason": "batch0002 already raises this cell above the 1M-equivalent target",
            }],
            "stages": STAGE_SPECS,
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
             "ledger": smoke.rel(BATCH0000_LEDGER), "ledger_sha256": BATCH0000_SHA256},
            {"batch_id": BATCH0001_ID, "status": BATCH0001_STATUS,
             "ledger": smoke.rel(BATCH0001_LEDGER), "ledger_sha256": BATCH0001_SHA256},
            {"batch_id": BATCH0002_ID, "status": BATCH0002_STATUS,
             "ledger": smoke.rel(BATCH0002_LEDGER), "ledger_sha256": BATCH0002_SHA256},
            dependency,
        ],
        "batch0003_predecessor_authority": dependency,
        "prior_credit_equivalence": prior_credit_equivalence,
        "prior_read_only_revalidation": prior_checks,
        "resource_gate": {
            "authority": "actual corrected-keV batch0001 geometry+mode+family artifacts",
            "calibration_caveat": (
                "point estimates; most non-gamma cells have one small calibration job and "
                "S3d gamma buildup has a large shower tail"
            ),
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
            "adaptive_ram_gate": "4-worker pilot; only signed measured process-group RSS can promote to 6",
            "min_available_ram_bytes": MIN_AVAILABLE_RAM_BYTES,
            "hard_available_ram_bytes": HARD_AVAILABLE_RAM_BYTES,
            "untrusted_initial_ram_bytes_per_worker": UNTRUSTED_RAM_BYTES_PER_WORKER,
            "wall_limit_hours": MAX_WALL_HOURS,
            "frozen_started_utc": frozen_started.isoformat(),
            "frozen_deadline_utc": frozen_deadline.isoformat(),
            "inherited_from": smoke.rel(BATCH0003_STATE),
            "parent_contract_sha256": dependency["contract_sha256"],
            "parent_state_sha256_at_freeze": dependency["state_sha256_at_batch0004_freeze"],
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
                "all transport remains inside batch0003 frozen_deadline_utc; later work "
                "requires a new non-overwriting disjoint-seed batch"
            ),
            "automatic_delete": False,
            "attempt_output_safety_factor": ATTEMPT_OUTPUT_SAFETY_FACTOR,
            "minimum_attempt_output_cap_bytes": MIN_ATTEMPT_OUTPUT_CAP_BYTES,
            "disk_emergency_margin_bytes": DISK_EMERGENCY_MARGIN_BYTES,
        },
        "aggregation_contract": {
            "pooling_boundary": "never pool across geometry, mode, or family",
            "TT_authority": TT_AUTHORITY,
            "checkpoint_acceptance": (
                "each family+mode needs an exact PASS report/ledger pair and remains an "
                "independent geometry-separated aggregation domain"
            ),
            "final_acceptance": "all twelve checkpoint ledgers plus final PASS umbrella authority",
        },
        "toolchain": toolchain_payload(),
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
    for stage in STAGE_SPECS:
        for geometry in GEOMETRIES:
            root = campaign_dir(geometry, str(stage["key"])) / "shards"
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
    """Ramp 4 -> 6 only after enough signed RSS observations."""
    peaks = sorted(_validated_peak_rss_values())
    assumed = UNTRUSTED_RAM_BYTES_PER_WORKER
    if peaks:
        p95_index = max(0, math.ceil(0.95 * len(peaks)) - 1)
        assumed = max(UNTRUSTED_RAM_BYTES_PER_WORKER, peaks[p95_index] * 2)
    cap = min(requested_cap, DEFAULT_WORKERS)
    current_available = mem_available_bytes()
    if requested_cap >= 6 and len(peaks) >= 8 and current_available >= MIN_AVAILABLE_RAM_BYTES + 6 * assumed:
        cap = 6
    return cap, assumed, len(peaks)


def adaptive_worker_slots(requested_cap: int, running: int = 0) -> int:
    available = mem_available_bytes()
    if available <= MIN_AVAILABLE_RAM_BYTES:
        return 0
    calibrated_cap, bytes_per_worker, _ = calibrated_worker_cap(requested_cap)
    ram_slots = max(0, (available - MIN_AVAILABLE_RAM_BYTES) // bytes_per_worker)
    return max(0, min(calibrated_cap, int(ram_slots)) - running)


def _calibration_by_campaign(contract: dict[str, Any]) -> dict[tuple[str, str], float]:
    return {
        (row["geometry"], row["stage"]): float(row["calibration"]["observed_bytes_per_event"])
        for row in contract["campaigns"]
    }


def _receipt_is_present(geometry: str, ordinal: int) -> bool:
    return geometry_receipt_path(geometry, ordinal).is_file()


def remaining_point_bytes(contract: dict[str, Any], stage_end: int = FINAL_SHARD_COUNT) -> float:
    rates = _calibration_by_campaign(contract)
    return math.fsum(
        shard_events(ordinal) * rates[(geometry, str(shard_spec(ordinal)["key"]))]
        for ordinal in range(1, stage_end + 1)
        for geometry in GEOMETRIES
        if not _receipt_is_present(geometry, ordinal)
    )


def _attempt_output_cap_bytes(contract: dict[str, Any], geometry: str, ordinal: int) -> int:
    rate = _calibration_by_campaign(contract)[(geometry, str(shard_spec(ordinal)["key"]))]
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
        for ordinal in range(1, min(stage_end, FINAL_SHARD_COUNT) + 1)
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
        (BATCH0002_CONTRACT, BATCH0002_CONTRACT_SHA256),
    ):
        if smoke.sha256(path) != expected:
            raise RuntimeError(f"prior ledger changed: {smoke.rel(path)}")
    if contract.get("toolchain") != toolchain_payload():
        raise RuntimeError("exact toolchain dependency closure changed")
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
    dependency = contract["batch0003_predecessor_authority"]
    for path_key, hash_key in (("contract", "contract_sha256"), ("report", "report_sha256"),
                               ("ledger", "ledger_sha256")):
        path = ROOT / dependency[path_key]
        if not path.is_file() or smoke.sha256(path) != dependency[hash_key]:
            raise RuntimeError(f"batch0003 dependency changed: {path_key}")
    for campaign in contract["campaigns"]:
        geometry = str(campaign["geometry"])
        family = str(campaign["family"])
        card = source_card_path(geometry, family)
        if smoke.sha256(card) != campaign["source_card_sha256"]:
            raise RuntimeError(f"corrected source card changed: {geometry}/{family}")
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
    ordinal: int,
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
    bind(BATCH0002_CONTRACT, BATCH0002_CONTRACT_SHA256, "batch0002 global contract")
    dependency = contract["batch0003_predecessor_authority"]
    bind(ROOT / dependency["contract"], dependency["contract_sha256"], "batch0003 contract")
    bind(ROOT / dependency["report"], dependency["report_sha256"], "batch0003 predecessor report")
    bind(ROOT / dependency["ledger"], dependency["ledger_sha256"], "batch0003 predecessor ledger")
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

    spec = shard_spec(ordinal)
    campaign = next(
        row for row in contract["campaigns"]
        if row["geometry"] == geometry and row["stage"] == spec["key"]
    )
    family = str(spec["family"])
    bind(source_card_path(geometry, family), campaign["source_card_sha256"],
         f"{geometry}/{family} source card")
    bind(source_manifest_path(geometry), campaign["source_migration_manifest_sha256"],
         f"{geometry} source migration")
    source_contract = _load_json(SOURCE_CONTRACT)
    spectrum_hashes = {
        str(row["corrected_spectrum"]): str(row["corrected_sha256"])
        for row in source_contract["spectra"]["files"]
    }
    for line in source_card_path(geometry, family).read_text(encoding="utf-8", errors="replace").splitlines():
        match = common.SPECTRUM_RE.search(line)
        if not match:
            continue
        spectrum = common.resolve_repo_path(match.group(1))
        expected = spectrum_hashes.get(smoke.rel(spectrum))
        if expected is None:
            raise RuntimeError(f"unregistered spectrum in {geometry}/{family} card: {spectrum}")
        bind(spectrum, expected, f"{geometry} corrected {family} spectrum")
    bundle = smoke.build_geometry_bundle(geometry, environment)
    if bundle != campaign["geometry_bundle"]:
        raise RuntimeError(f"geometry bundle changed during attempt: {geometry}")
    records.extend({"path": str(row["path"]), "sha256": str(row["sha256"])} for row in bundle["files"])
    records.sort(key=lambda row: (row["path"], row["sha256"]))
    return smoke.canonical_digest(records)


def _campaign_contract_payload(
    contract: dict[str, Any], geometry: str, stage_key: str
) -> dict[str, Any]:
    campaign = next(
        row for row in contract["campaigns"]
        if row["geometry"] == geometry and row["stage"] == stage_key
    )
    stage_rows = [row for row in contract["statistics"]["paired_shards"] if row["stage"] == stage_key]
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_TRANSPORT__SHARD_RECEIPTS_REQUIRED",
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "paired_shards": stage_rows,
        **campaign,
    }


def _normalization_payload(
    contract: dict[str, Any], geometry: str, stage_key: str
) -> dict[str, Any]:
    campaign = next(
        row for row in contract["campaigns"]
        if row["geometry"] == geometry and row["stage"] == stage_key
    )
    campaign_contract = campaign_dir(geometry, stage_key) / "batch_contract.json"
    if not campaign_contract.is_file():
        raise RuntimeError(f"campaign contract missing before normalization: {geometry}")
    return {
        "schema_version": 1,
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "geometry": geometry,
        "stage": stage_key,
        "mode": campaign["mode"],
        "selected_particles": [campaign["family"]],
        "excluded_particles": sorted(set(FAMILIES) - {campaign["family"]}) + ["p"],
        "prior_events": campaign["prior_events"],
        "new_events": campaign["new_events"],
        "final_cumulative_events": campaign["final_cumulative_events"],
        "jobs": campaign["paired_shards"],
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "store_simulation_info": "all",
        "store_isotopes": True,
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "batch_contract_sha256": smoke.sha256(campaign_contract),
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "prior_merge_ledgers": [
            BATCH0000_SHA256, BATCH0001_SHA256, BATCH0002_SHA256,
            contract["batch0003_predecessor_authority"]["ledger_sha256"],
        ],
        "aggregation": (
            f"sum(selected)/sum(TT) within {geometry}+{campaign['mode']}+"
            f"{campaign['family']} only"
        ),
        "automatic_delete": False,
        "raw_retention": "retain SIM/DAT/log/source and authority files; no controller deletion",
    }


def _prepare_campaign_roots(contract: dict[str, Any]) -> None:
    for stage in STAGE_SPECS:
        stage_key = str(stage["key"])
        for geometry in GEOMETRIES:
            outdir = campaign_dir(geometry, stage_key)
            outdir.mkdir(parents=True, exist_ok=True)
            campaign_contract = outdir / "batch_contract.json"
            payload = _campaign_contract_payload(contract, geometry, stage_key)
            atomic_write_once_json(campaign_contract, payload)
            atomic_write_once_json(
                outdir / "normalization.json",
                _normalization_payload(contract, geometry, stage_key),
            )


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
        "parent_state_sha256": contract["execution"]["parent_state_sha256_at_freeze"],
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
    if state.get("parent_state_sha256") != contract["execution"]["parent_state_sha256_at_freeze"]:
        raise RuntimeError("execution state parent-state binding differs from global contract")
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
    spec = shard_spec(ordinal)
    family = str(spec["family"])
    mode = str(spec["mode"])
    local = int(spec["stage_ordinal"])
    name = f"Background_{family}_fullsphere20_batch0004_{mode}_shard{local:04d}"
    sim_prefix = outdir / name
    isotope_prefix = outdir / f"{name}.dat"
    return {
        "job_name": name,
        "particle": family,
        "mode": mode,
        "events": shard_events(ordinal),
        "rep": ordinal,
        "part": 1,
        "seed": shard_seed(ordinal),
        "source": str(source_card_path(geometry, family).resolve()),
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
    spec = shard_spec(ordinal)
    family = str(spec["family"])
    mode = str(spec["mode"])
    return {
        "schema_version": 1,
        "status": "FROZEN_ATTEMPT__DYNAMIC_VALIDATION_REQUIRED",
        "global_contract": smoke.rel(GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(GLOBAL_CONTRACT),
        "geometry": geometry,
        "stage": spec["key"],
        "mode": mode,
        "family": family,
        "global_ordinal": ordinal,
        "stage_ordinal": spec["stage_ordinal"],
        "attempt": attempt,
        "events": shard_events(ordinal),
        "seed": shard_seed(ordinal),
        "job_name": job["job_name"],
        "source_card": smoke.rel(source_card_path(geometry, family)),
        "source_card_sha256": smoke.sha256(source_card_path(geometry, family)),
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
    spec = shard_spec(ordinal)
    input_digest_pre = _verify_attempt_inputs(contract, geometry, ordinal, environment)
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
            f"geometry={geometry} stage={spec['key']} mode={spec['mode']} "
            f"particle={spec['family']} global_ordinal={ordinal} "
            f"stage_ordinal={spec['stage_ordinal']} "
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
                    heartbeat_digest = _verify_attempt_inputs(contract, geometry, ordinal, environment)
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
                input_digest_post = _verify_attempt_inputs(contract, geometry, ordinal, environment)
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
    spec = shard_spec(ordinal)
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
        "stage": spec["key"],
        "family": spec["family"],
        "mode": spec["mode"],
        "global_ordinal": ordinal,
        "stage_ordinal": spec["stage_ordinal"],
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
        raise SystemExit("batch0004 receipt adoption failed: " + " | ".join(adoption_failures))

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
            # Reserve for the entire still-planned batch, not merely the
            # currently dispatched family/mode checkpoint.
            gate = disk_gate(contract, FINAL_SHARD_COUNT, requested_workers)
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
        raise SystemExit("batch0004 paused: " + " | ".join(failures))
    for ordinal in range(start_ordinal, end_ordinal + 1):
        if not pair_receipt_path(ordinal).is_file():
            _write_pair_receipt(ordinal)


def _run_stage_validator(stage: str, deadline: datetime) -> None:
    ledger = checkpoint_ledger_path(stage)
    if ledger.exists():
        check = _run_supervised_command(
            [sys.executable, str(VALIDATOR), "--stage", stage, "--check"],
            deadline=deadline,
            fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
        )
        if check.returncode != 0:
            raise SystemExit(f"batch0004 {stage} existing authority revalidation failed")
        return
    result = _run_supervised_command(
        [sys.executable, str(VALIDATOR), "--stage", stage],
        deadline=deadline,
        fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
    )
    if result.returncode != 0:
        raise SystemExit(f"batch0004 {stage} dynamic validation failed")


def _run_final_validator(deadline: datetime) -> None:
    command = [sys.executable, str(VALIDATOR), "--final"]
    if FINAL_LEDGER.exists():
        command.append("--check")
    result = _run_supervised_command(
        command,
        deadline=deadline,
        fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
    )
    if result.returncode != 0:
        raise SystemExit("batch0004 final umbrella authority validation failed")


def _revalidate_predecessor_authority(
    contract: dict[str, Any], deadline: datetime
) -> None:
    dependency = contract["batch0003_predecessor_authority"]
    if dependency["profile"] == "prefix_ordinal76":
        report_hash, ledger_hash = _validate_prefix76_authority()
        if (
            report_hash != dependency["report_sha256"]
            or ledger_hash != dependency["ledger_sha256"]
        ):
            raise SystemExit("batch0003 prefix76 authority changed after contract freeze")
        return
    if dependency["profile"] != "stage5":
        raise SystemExit("batch0003 predecessor authority profile is not executable")
    result = _run_supervised_command(
        [sys.executable, str(BATCH0003_VALIDATOR), "--stage", "5m", "--check"],
        deadline=deadline,
        fixed_timeout_s=max(1.0, _remaining_seconds(deadline)),
    )
    if result.returncode != 0:
        raise SystemExit("batch0003 stage5 authority revalidation failed")


def _load_or_create_contract(
    cosima_arg: str | None,
    workers: int,
    preflight_deadline: datetime,
) -> tuple[dict[str, Any], dict[str, str]]:
    if GLOBAL_CONTRACT.exists():
        contract = _load_json(GLOBAL_CONTRACT)
        if contract.get("batch_id") != BATCH_ID or contract.get("campaign_version") != CAMPAIGN_VERSION:
            raise SystemExit("existing batch0004 contract identity mismatch")
        if int(contract["execution"]["requested_worker_cap"]) != workers:
            raise SystemExit("resume must use the worker cap frozen in the batch0004 contract")
        cosima = smoke.resolve_cosima(contract["transport"]["cosima"])
        environment, _ = smoke.resolve_transport_environment(cosima)
        _verify_toolchain_and_inputs(contract, environment)
        _revalidate_predecessor_authority(contract, preflight_deadline)
        return contract, environment

    authority_paths = [EXECUTION_STATE, FINAL_VALIDATION_REPORT, FINAL_LEDGER]
    authority_paths.extend(checkpoint_report_path(key) for key in STAGE_ORDER)
    authority_paths.extend(checkpoint_ledger_path(key) for key in STAGE_ORDER)
    for path in authority_paths:
        if path.exists():
            raise SystemExit(f"batch0004 authority output exists without global contract: {smoke.rel(path)}")
    campaign_roots = [
        campaign_dir(geometry, str(stage["key"]))
        for stage in STAGE_SPECS for geometry in GEOMETRIES
    ]
    if PAIR_RECEIPT_ROOT.exists() or any(path.exists() for path in campaign_roots):
        raise SystemExit("batch0004 shard outputs exist without global contract; refusing adoption")
    contract, environment = build_contract(
        cosima_arg,
        workers,
        require_predecessor_authority=True,
        full_preflight=True,
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
) -> int:
    _ABORT_EVENT.clear()
    _prepare_campaign_roots(contract)
    state = _execution_state(contract, proposed_started, proposed_deadline)
    deadline = datetime.fromisoformat(state["deadline_utc"])
    if datetime.now(timezone.utc) >= deadline:
        raise SystemExit("inherited batch0003 12h deadline has expired; no batch0004 transport launched")

    launch_deadline = deadline - timedelta(seconds=STOP_LAUNCH_RESERVE_SECONDS)
    transport_deadline = deadline - timedelta(seconds=VALIDATION_RESERVE_SECONDS)
    if FINAL_LEDGER.exists():
        _run_final_validator(deadline)
        _update_state(
            status="PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE",
            active_jobs=0,
            pending_jobs=0,
        )
        return 0
    completed: list[str] = []
    for stage in STAGE_SPECS:
        key = str(stage["key"])
        if not checkpoint_ledger_path(key).exists():
            _run_stage(
                contract,
                environment,
                int(stage["global_start_ordinal"]),
                int(stage["global_end_ordinal"]),
                workers,
                launch_deadline,
                transport_deadline,
                deadline,
            )
        _run_stage_validator(key, deadline)
        completed.append(key)
        _update_state(status="RUNNING", completed_checkpoints=completed)
    _revalidate_predecessor_authority(contract, deadline)
    _run_final_validator(deadline)
    _update_state(
        status="PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE",
        active_jobs=0,
        pending_jobs=0,
    )
    return 0


def plan_summary(contract: dict[str, Any]) -> dict[str, Any]:
    gate = disk_gate(
        contract,
        stage_end=FINAL_SHARD_COUNT,
        requested_workers=int(contract["execution"]["requested_worker_cap"]),
    )
    return {
        "batch_id": contract["batch_id"],
        "campaign_version": contract["campaign_version"],
        "transport_launched": False,
        "screening_label": "1M gamma-equivalent reduced-statistics checkpoint; not historical full-stat",
        "batch0003_predecessor_authority": contract["batch0003_predecessor_authority"],
        "authority_on_pass": "PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE",
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "source_scope": contract["source_scope"],
        "statistics": {
            key: contract["statistics"][key]
            for key in (
                "screening_semantics",
                "historical_non_gamma_full_units",
                "screening_units",
                "historical_non_gamma_fraction",
                "new_events_total",
                "paired_shards_total",
                "transport_jobs_total",
                "prior_only_closed_cells",
            )
        },
        "checkpoints": [
            {
                "stage": stage["key"],
                "family": stage["family"],
                "mode": stage["mode"],
                "prior_events_per_geometry": stage["prior_events_per_geometry"],
                "new_events_per_geometry": stage["new_events_per_geometry"],
                "target_events_per_geometry": stage["target_events_per_geometry"],
                "paired_shards": stage["paired_shards"],
                "report": smoke.rel(checkpoint_report_path(str(stage["key"]))),
                "ledger": smoke.rel(checkpoint_ledger_path(str(stage["key"]))),
            }
            for stage in STAGE_SPECS
        ],
        "pairing": contract["pairing"],
        "lineage": contract["lineage"],
        "prior_read_only_revalidation": contract["prior_read_only_revalidation"],
        "campaigns": [
            {
                "geometry": row["geometry"],
                "stage": row["stage"],
                "mode": row["mode"],
                "family": row["family"],
                "outdir": row["outdir"],
                "source_card_sha256": row["source_card_sha256"],
                "geometry_bundle_sha256": row["geometry_bundle"]["bundle_sha256"],
                "prior_events": row["prior_events"],
                "new_events": row["new_events"],
                "final_cumulative_events": row["final_cumulative_events"],
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
            "scope": "all twelve independent family+mode checkpoints",
            "point_estimated_output_bytes": contract["resource_gate"]["point_estimated_output_bytes"],
            "point_estimated_run_phase_s": contract["resource_gate"]["point_estimated_run_phase_s"],
            "disk_safety_factor": DISK_SAFETY_FACTOR,
            "disk_reserve_bytes": DISK_RESERVE_BYTES,
            "automatic_delete": False,
        },
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
    parser.add_argument("--cosima", default=None)
    args = parser.parse_args()
    session_started = datetime.now(timezone.utc)
    if not BATCH0003_STATE.is_file():
        raise SystemExit("batch0003 execution state is required to inherit the frozen deadline")
    parent_state = _load_json(BATCH0003_STATE)
    session_deadline = datetime.fromisoformat(str(parent_state["deadline_utc"]))
    if args.print_plan:
        contract, _ = build_contract(
            args.cosima,
            args.workers,
            require_predecessor_authority=False,
            full_preflight=False,
            deadline=session_deadline,
        )
        summary = plan_summary(contract)
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if summary["live_disk_gate"]["status"] == "PASS" else 2
    lock_handle = _acquire_controller_lock()
    previous_handlers: dict[int, Any] = {}
    try:
        _refuse_live_batch0004_processes()
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, _controller_signal_handler)
        contract, environment = _load_or_create_contract(
            args.cosima,
            args.workers,
            session_deadline,
        )
        return _run(
            contract,
            environment,
            args.workers,
            session_started,
            session_deadline,
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
