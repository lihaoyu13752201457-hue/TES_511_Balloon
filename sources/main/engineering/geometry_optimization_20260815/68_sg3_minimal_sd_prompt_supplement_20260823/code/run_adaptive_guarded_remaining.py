#!/usr/bin/env python3
"""Resume M05 SG3-minimal/SH3 with local adaptive concurrency and event alerts.

This process is deliberately self-contained: ordinary progress and transient
resource-pressure retries stay local and consume no Codex turns.  Only a
terminal failure or final completion resumes the owning Codex thread once.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
MINIMAL_PREP = PACKAGE / "MINIMAL_PRODUCTION_PREPARATION.json"
OLD_PACKAGE = PACKAGE.parent / "67_m05new_zero_prompt_statistics_20260823"
OLD_PREP = OLD_PACKAGE / "PREPARATION.json"
RUNNER = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")
CODEX = Path("/home/ubuntu/.local/bin/codex")
THREAD_ID = "01a02d17-690b-75b1-a8ba-35ed3aad414c"

STATE = PACKAGE / "ADAPTIVE_GUARD_STATE.json"
LAST_EVENT = PACKAGE / "ADAPTIVE_GUARD_LAST_EVENT.json"
EVENT_LOG = PACKAGE / "adaptive_guard_events.jsonl"
LOCK = PACKAGE / "adaptive_guard.lock"
LOG_ROOT = PACKAGE / "adaptive_production_logs"
RUNTIME_CONFIG_ROOT = PACKAGE / "adaptive_runtime_configs"
NOTIFIER_LOG = PACKAGE / "adaptive_guard_codex_notifier.jsonl"

DATA_MOUNT = Path("/mnt/data")
EXPECTED_SOURCE = "/dev/sdb2"
EXPECTED_UUID_LINK = Path("/dev/disk/by-uuid/903261CE3261BA3C")
SG3_NEW_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/"
    "m05new_zero_prompt_minimal_supplement_20260823_v1"
)
SH3_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/"
    "m05new_zero_prompt_supplement_20260823_v1"
)

FAMILY_ORDER = ("alpha", "p", "eplus", "n")
MIN_TOTAL_WORKERS = 3
MAX_TOTAL_WORKERS = 6
MAX_WORKERS_PER_GEOMETRY = 3
FIXED_TOTAL_WORKERS = int(os.environ.get("M05_FIXED_TOTAL_WORKERS", "0"))
LOCAL_RESOURCE_RETRIES = 3
RESOURCE_RETRY_SECONDS = 45
STATE_INTERVAL_SECONDS = 10
STORAGE_CHECK_SECONDS = 5
STOP = False
CHILDREN: dict[str, subprocess.Popen[str]] = {}
HANDLES: dict[str, Any] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, path)


def event(kind: str, **payload: Any) -> dict[str, Any]:
    row = {"at": now(), "kind": kind, **payload}
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
    return row


def request_stop(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, value = line.split(":", 1)
        if key in {"MemAvailable", "SwapFree"}:
            result[key] = int(value.split()[0]) * 1024
    return result


def memory_full_psi_avg10() -> float:
    for line in Path("/proc/pressure/memory").read_text(encoding="ascii").splitlines():
        if not line.startswith("full "):
            continue
        for token in line.split():
            if token.startswith("avg10="):
                return float(token.split("=", 1)[1])
    return 0.0


def mount_evidence() -> dict[str, Any]:
    proc = subprocess.run(
        ["findmnt", "-rn", str(DATA_MOUNT), "-o", "SOURCE,TARGET,FSTYPE,OPTIONS"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    fields = proc.stdout.strip().split(maxsplit=3)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "source": fields[0] if len(fields) >= 1 else None,
        "target": fields[1] if len(fields) >= 2 else None,
        "fstype": fields[2] if len(fields) >= 3 else None,
        "options": fields[3].split(",") if len(fields) >= 4 else [],
    }


def verify_storage(*, write_probe: bool) -> dict[str, Any]:
    evidence = mount_evidence()
    errors: list[str] = []
    if evidence["returncode"] != 0:
        errors.append("/mnt/data is not a mount point")
    if evidence.get("source") != EXPECTED_SOURCE:
        errors.append(f"unexpected source: {evidence.get('source')}")
    if evidence.get("target") != str(DATA_MOUNT):
        errors.append(f"unexpected target: {evidence.get('target')}")
    if evidence.get("fstype") not in {"ntfs3", "ntfs"}:
        errors.append(f"unexpected filesystem: {evidence.get('fstype')}")
    if "rw" not in evidence.get("options", []):
        errors.append("/mnt/data is not rw")
    try:
        if EXPECTED_UUID_LINK.resolve() != Path(EXPECTED_SOURCE):
            errors.append("UUID link no longer resolves to /dev/sdb2")
    except OSError as exc:
        errors.append(f"UUID link unavailable: {exc}")
    for root in (SG3_NEW_ROOT, SH3_ROOT):
        if not root.is_dir():
            errors.append(f"required data root unavailable: {root}")
    if write_probe and not errors:
        probe = DATA_MOUNT / f".m05_adaptive_write_probe_{os.getpid()}"
        try:
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(fd, b"M05 adaptive guard write probe\n")
                os.fsync(fd)
            finally:
                os.close(fd)
            probe.unlink()
        except OSError as exc:
            errors.append(f"write probe failed: {type(exc).__name__}: {exc}")
            try:
                probe.unlink()
            except OSError:
                pass
    evidence["errors"] = errors
    evidence["status"] = "PASS" if not errors else "FAIL"
    return evidence


def rows() -> dict[tuple[str, str], dict[str, Any]]:
    minimal = load(MINIMAL_PREP)
    old = load(OLD_PREP)
    result = {("sg3_minimal", row["family"]): dict(row) for row in minimal["bundles"]}
    for row in old["bundles"]:
        if row.get("geometry") == "sh3" and row.get("family") in FAMILY_ORDER:
            result[("sh3", row["family"])] = dict(row)
    expected = {
        (geometry, family)
        for geometry in ("sg3_minimal", "sh3")
        for family in FAMILY_ORDER
    }
    if set(result) != expected:
        raise RuntimeError("adaptive bundle matrix is incomplete")
    return result


def prepare_runtime_configs(matrix: dict[tuple[str, str], dict[str, Any]]) -> None:
    for (geometry, family), row in matrix.items():
        source = Path(row["config"])
        config = load(source)
        config["max_workers"] = MAX_WORKERS_PER_GEOMETRY
        config["workers"] = min(MAX_WORKERS_PER_GEOMETRY, max(1, int(config.get("workers", 1))))
        # Interrupted/resource-shed attempts never enter the statistical pool;
        # extra attempt slots only permit safe retries with the same registered seed.
        config["max_attempts"] = max(8, int(config.get("max_attempts", 3)))
        target = RUNTIME_CONFIG_ROOT / geometry / f"{family}.json"
        atomic(target, config)
        row["runtime_config"] = str(target)


def controller_state(row: dict[str, Any]) -> dict[str, Any] | None:
    path = Path(row["run_root"]) / "controller_state.json"
    return load(path) if path.is_file() else None


def complete(row: dict[str, Any]) -> bool:
    state = controller_state(row)
    return bool(state and state.get("status") == "COMPLETE")


def controller_lock_free(run_root: Path) -> bool:
    path = run_root / "controller.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        finally:
            try:
                fcntl.flock(handle, fcntl.LOCK_UN)
            except OSError:
                pass
    return True


def recover_stale_active(matrix: dict[tuple[str, str], dict[str, Any]], reason: str) -> list[str]:
    roots = sorted({Path(row["run_root"]) for row in matrix.values()})
    if any(not controller_lock_free(root) for root in roots):
        raise RuntimeError("cannot recover active directories while a controller lock is held")
    moved: list[str] = []
    ordinal = 0
    for root in roots:
        jobs = root / "jobs"
        if not jobs.is_dir():
            continue
        for active in sorted(jobs.glob("*/active")):
            ordinal += 1
            interrupted = active.parent / "interrupted"
            interrupted.mkdir(parents=True, exist_ok=True)
            target = interrupted / f"{stamp()}_{ordinal:03d}"
            if target.exists():
                raise RuntimeError(f"interrupted recovery target exists: {target}")
            os.replace(active, target)
            atomic(
                target / "INTERRUPTION_RECOVERY.json",
                {
                    "schema_version": 1,
                    "status": "PRESERVED__NOT_A_PASS_ATTEMPT",
                    "recovered_at": now(),
                    "reason": reason,
                    "original_active_dir": str(active),
                    "preserved_dir": str(target),
                },
            )
            moved.append(str(target))
    if moved:
        event("stale_active_preserved", reason=reason, paths=moved)
    return moved


def choose_total_workers(family: str, configs: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    memory = meminfo()
    psi = memory_full_psi_avg10()
    reservation = max(int(c.get("launch_worker_reservation_bytes", 1_610_612_736)) for c in configs)
    safety = 2_147_483_648
    affordable = math.floor(max(0, memory["MemAvailable"] - safety) / reservation)
    total = max(MIN_TOTAL_WORKERS, min(MAX_TOTAL_WORKERS, affordable))
    family_cap = {"alpha": 3, "p": 6, "eplus": 5, "n": 4}[family]
    if FIXED_TOTAL_WORKERS:
        if not MIN_TOTAL_WORKERS <= FIXED_TOTAL_WORKERS <= MAX_TOTAL_WORKERS:
            raise ValueError(
                f"M05_FIXED_TOTAL_WORKERS must be within "
                f"{MIN_TOTAL_WORKERS}..{MAX_TOTAL_WORKERS}"
            )
        total = FIXED_TOTAL_WORKERS
    else:
        if psi >= 5.0:
            total = MIN_TOTAL_WORKERS
        elif psi >= 1.0:
            total = min(total, 4)
        total = max(MIN_TOTAL_WORKERS, min(total, family_cap, MAX_TOTAL_WORKERS))
    return total, {
        "MemAvailable": memory["MemAvailable"],
        "SwapFree": memory["SwapFree"],
        "memory_full_psi_avg10": psi,
        "worker_reservation_bytes": reservation,
        "safety_bytes": safety,
        "affordable_before_family_cap": affordable,
        "family_cap": family_cap,
        "fixed_total_workers": FIXED_TOTAL_WORKERS or None,
    }


def allocation(total: int, unfinished: list[str]) -> dict[str, int]:
    if unfinished == ["sg3_minimal"] or unfinished == ["sh3"]:
        return {unfinished[0]: min(MAX_WORKERS_PER_GEOMETRY, total)}
    table = {
        3: {"sg3_minimal": 1, "sh3": 2},
        4: {"sg3_minimal": 2, "sh3": 2},
        5: {"sg3_minimal": 2, "sh3": 3},
        6: {"sg3_minimal": 3, "sh3": 3},
    }
    return table[total]


def close_handles() -> None:
    for handle in HANDLES.values():
        try:
            handle.close()
        except OSError:
            pass
    HANDLES.clear()


def terminate_children() -> None:
    for child in CHILDREN.values():
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 35
    for child in CHILDREN.values():
        if child.poll() is None:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
    CHILDREN.clear()
    close_handles()


def log_tail(path: Path, limit: int = 12000) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - limit))
        return handle.read().decode("utf-8", errors="replace")


def recoverable_resource_failure(text: str) -> bool:
    markers = (
        "resource admission",
        "resource guard",
        "memory_full_psi",
        "memory_full_PSI",
        "MemAvailable",
        "SwapFree",
        "dynamic_disk_reserve",
        "all pending jobs blocked",
    )
    fatal_markers = (
        "exhausted attempts",
        "failed_all_attempts",
        "receipt identity mismatch",
        "source manifest",
        "preflight",
        "geometry mismatch",
        "seed registry",
        "stale active",
    )
    return any(marker in text for marker in markers) and not any(
        marker in text for marker in fatal_markers
    )


def publish(
    status: str,
    *,
    family: str | None,
    completed: list[str],
    workers: dict[str, int] | None = None,
    resource: dict[str, Any] | None = None,
    retry: int = 0,
    error: str | None = None,
) -> None:
    atomic(
        STATE,
        {
            "schema_version": 1,
            "status": status,
            "updated_at": now(),
            "family_order": list(FAMILY_ORDER),
            "completed_families": completed,
            "current_family": family,
            "min_total_workers": MIN_TOTAL_WORKERS,
            "max_total_workers": MAX_TOTAL_WORKERS,
            "workers": workers or {},
            "resource_at_allocation": resource or {},
            "local_resource_retry": retry,
            "active_controllers": {
                name: {"pid": child.pid, "returncode": child.poll()}
                for name, child in CHILDREN.items()
            },
            "storage": mount_evidence(),
            "error": error,
        },
    )


def notify_codex(kind: str, message: str) -> None:
    payload = {
        "schema_version": 1,
        "event_id": f"{kind}:{stamp()}:{os.getpid()}",
        "kind": kind,
        "at": now(),
        "message": message,
        "state_path": str(STATE),
        "event_log": str(EVENT_LOG),
    }
    atomic(LAST_EVENT, payload)
    prompt = (
        f"M05 本地自适应守护触发了 {kind} 事件（事件触发，不是轮询）。"
        f"详情：{message}。先读取 {STATE}、{LAST_EVENT} 与 {EVENT_LOG} 的末尾，"
        "检查 /mnt/data 是否仍为 UUID 903261CE3261BA3C 对应设备的 rw 挂载，"
        "检查有无残留 M05 Cosima/controller/active 目录。保留所有 PASS receipt，"
        "严禁恢复旧 67 包的全-SD SG3；只恢复 SG3-minimal remaining-only 与 SH3。"
        "若安全可恢复，继续运行本自适应守护（总 Cosima 3--6）；不要创建定时轮询或心跳。"
        "若是 COMPLETE，则核验最终 receipts/events/等效时间/磁盘占用后向用户汇报。"
    )
    NOTIFIER_LOG.parent.mkdir(parents=True, exist_ok=True)
    handle = NOTIFIER_LOG.open("a", encoding="utf-8", buffering=1)
    handle.write(json.dumps({"event": "codex_resume_launch", **payload}, ensure_ascii=False) + "\n")
    handle.flush()
    try:
        subprocess.Popen(
            [str(CODEX), "exec", "resume", "--json", THREAD_ID, prompt],
            cwd=str(PACKAGE.parents[2]),
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
    except BaseException:
        handle.close()
        raise


def launch_family(
    family: str,
    matrix: dict[tuple[str, str], dict[str, Any]],
    completed: list[str],
    retry: int,
    total_override: int | None,
) -> tuple[dict[str, int], dict[str, Any]]:
    CHILDREN.clear()
    close_handles()
    unfinished = [
        geometry
        for geometry in ("sg3_minimal", "sh3")
        if not complete(matrix[(geometry, family)])
    ]
    if not unfinished:
        return {}, {}
    configs = [load(Path(matrix[(geometry, family)]["runtime_config"])) for geometry in unfinished]
    selected_total, resource = choose_total_workers(family, configs)
    if total_override is not None:
        selected_total = max(MIN_TOTAL_WORKERS, min(selected_total, total_override))
    workers = allocation(selected_total, unfinished)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for geometry in unfinished:
        row = matrix[(geometry, family)]
        log_path = LOG_ROOT / f"{geometry}_{family}.controller.log"
        handle = log_path.open("a", encoding="utf-8", buffering=1)
        handle.write(
            json.dumps(
                {
                    "event": "adaptive_controller_launch",
                    "at": now(),
                    "geometry": geometry,
                    "family": family,
                    "workers": workers[geometry],
                    "local_resource_retry": retry,
                    "config": row["runtime_config"],
                    "resource": resource,
                },
                sort_keys=True,
            )
            + "\n"
        )
        child = subprocess.Popen(
            [
                sys.executable,
                str(RUNNER),
                "--config",
                row["runtime_config"],
                "--workers",
                str(workers[geometry]),
            ],
            cwd=str(PACKAGE),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        CHILDREN[geometry] = child
        HANDLES[geometry] = handle
    event(
        "family_launch",
        family=family,
        workers=workers,
        total_workers=sum(workers.values()),
        retry=retry,
        resource=resource,
    )
    publish(
        "RUNNING",
        family=family,
        completed=completed,
        workers=workers,
        resource=resource,
        retry=retry,
    )
    return workers, resource


def run_guard() -> int:
    for required in (MINIMAL_PREP, OLD_PREP, RUNNER, CODEX):
        if not required.is_file():
            raise FileNotFoundError(f"required file unavailable: {required}")
    storage = verify_storage(write_probe=True)
    if storage["status"] != "PASS":
        raise RuntimeError(f"storage preflight failed: {storage}")
    matrix = rows()
    prepare_runtime_configs(matrix)
    moved = recover_stale_active(matrix, "host/process interruption before adaptive restart")
    completed: list[str] = []
    publish("STARTING", family=None, completed=completed)
    if moved:
        publish(
            "STARTING",
            family=None,
            completed=completed,
            error=f"preserved {len(moved)} interrupted active directories",
        )
    for family in FAMILY_ORDER:
        retry = 0
        total_override: int | None = None
        while True:
            if STOP:
                raise RuntimeError("adaptive guard received stop signal")
            if all(complete(matrix[(geometry, family)]) for geometry in ("sg3_minimal", "sh3")):
                break
            storage = verify_storage(write_probe=False)
            if storage["status"] != "PASS":
                raise RuntimeError(f"storage disappeared or became read-only: {storage}")
            while memory_full_psi_avg10() > 5.0:
                if STOP:
                    raise RuntimeError("adaptive guard stopped during resource backoff")
                time.sleep(RESOURCE_RETRY_SECONDS)
            workers, resource = launch_family(
                family,
                matrix,
                completed,
                retry,
                total_override,
            )
            if not CHILDREN:
                break
            last_state = 0.0
            failure: dict[str, int] = {}
            while CHILDREN:
                if STOP:
                    terminate_children()
                    raise RuntimeError("adaptive guard received stop signal")
                if time.monotonic() - last_state >= STATE_INTERVAL_SECONDS:
                    publish(
                        "RUNNING",
                        family=family,
                        completed=completed,
                        workers=workers,
                        resource=resource,
                        retry=retry,
                    )
                    last_state = time.monotonic()
                storage = verify_storage(write_probe=False)
                if storage["status"] != "PASS":
                    terminate_children()
                    raise RuntimeError(f"storage disappeared or became read-only: {storage}")
                codes = {name: child.poll() for name, child in CHILDREN.items()}
                failure = {name: code for name, code in codes.items() if code not in (None, 0)}
                if failure:
                    break
                if all(code == 0 for code in codes.values()):
                    break
                time.sleep(STORAGE_CHECK_SECONDS)
            if failure:
                terminate_children()
                tails = {
                    geometry: log_tail(LOG_ROOT / f"{geometry}_{family}.controller.log")
                    for geometry in ("sg3_minimal", "sh3")
                }
                combined = "\n".join(tails.values())
                event(
                    "controller_failure",
                    family=family,
                    returncodes=failure,
                    retry=retry,
                    log_tails=tails,
                )
                if recoverable_resource_failure(combined) and retry < LOCAL_RESOURCE_RETRIES:
                    retry += 1
                    total_override = max(MIN_TOTAL_WORKERS, sum(workers.values()) - 1)
                    recover_stale_active(matrix, f"local resource retry {retry} after controller failure")
                    publish(
                        "RESOURCE_BACKOFF",
                        family=family,
                        completed=completed,
                        workers=workers,
                        resource=resource,
                        retry=retry,
                        error=f"recoverable controller failure: {failure}",
                    )
                    time.sleep(RESOURCE_RETRY_SECONDS)
                    continue
                raise RuntimeError(
                    f"controller failure in {family}: {failure}; tails={tails}"
                )
            for name, child in list(CHILDREN.items()):
                child.wait()
                if child.returncode != 0:
                    raise RuntimeError(f"controller changed to failure after wait: {name}={child.returncode}")
            CHILDREN.clear()
            close_handles()
            missing = [
                geometry
                for geometry in ("sg3_minimal", "sh3")
                if not complete(matrix[(geometry, family)])
            ]
            if missing:
                raise RuntimeError(f"zero controller exits without COMPLETE: {family}/{missing}")
            break
        completed.append(family)
        event("family_complete", family=family)
        publish("RUNNING", family=None, completed=completed)
    publish("COMPLETE", family=None, completed=completed)
    event("production_complete", completed_families=completed)
    notify_codex("COMPLETE", "SG3-minimal remaining-only 与 SH3 所有受管 family 已完成")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run-notify", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(load(STATE) if STATE.is_file() else {"status": "NOT_STARTED"}, indent=2))
        return 0
    if args.dry_run_notify:
        print(
            json.dumps(
                {
                    "codex": str(CODEX),
                    "thread_id": THREAD_ID,
                    "state": str(STATE),
                    "mode": "event_only",
                },
                indent=2,
            )
        )
        return 0
    if args.preflight:
        matrix = rows()
        configs = [
            load(Path(matrix[(geometry, "alpha")]["config"]))
            for geometry in ("sg3_minimal", "sh3")
        ]
        total, resource = choose_total_workers("alpha", configs)
        active = []
        for root in sorted({Path(row["run_root"]) for row in matrix.values()}):
            jobs = root / "jobs"
            if jobs.is_dir():
                active.extend(str(path) for path in sorted(jobs.glob("*/active")))
        payload = {
            "storage": verify_storage(write_probe=True),
            "alpha_total_workers": total,
            "alpha_allocation": allocation(total, ["sg3_minimal", "sh3"]),
            "resource": resource,
            "stale_active_directories": active,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["storage"]["status"] == "PASS" else 1
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another adaptive M05 guard already holds the lock")
        try:
            return run_guard()
        except BaseException as exc:
            terminate_children()
            message = f"{type(exc).__name__}: {exc}"
            if STOP:
                publish("STOPPED", family=None, completed=[], error=message)
                event("guard_stopped_by_signal", error=message)
                return 0
            publish("FAILED", family=None, completed=[], error=message)
            event("guard_failure", error=message)
            try:
                notify_codex("FAILED", message)
            except BaseException as notify_exc:
                event(
                    "codex_notification_failure",
                    error=f"{type(notify_exc).__name__}: {notify_exc}",
                )
                return 2
            # A handled failure has already resumed the owning Codex thread.
            # Exit zero so systemd does not create duplicate notifications.
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
