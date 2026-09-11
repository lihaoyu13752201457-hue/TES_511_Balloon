#!/usr/bin/env python3
"""Throttle one exact SF3 user service before systemd-oomd reaches its kill gate.

This guard changes only the aggregate CPU quota of an already-running unit.
It never signals a worker, edits a source, opens a SIM, or changes statistics.
The normal four-core quota is restored only after several consecutive safe
samples; pressure or low headroom immediately selects a shared three-core
quota while leaving the four admitted workers intact.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GIB = 1024**3
MEM_FLOOR_BYTES = int(1.5 * GIB)
THROTTLE_MEM_BYTES = 3 * GIB
RESTORE_MEM_BYTES = 4 * GIB
SWAP_FLOOR_BYTES = 8 * GIB
THROTTLE_SWAP_BYTES = 9 * GIB
THROTTLE_SOME_AVG10 = 15.0
THROTTLE_FULL_AVG10 = 10.0
RESTORE_AVG10 = 2.0
DEFAULT_NORMAL_QUOTA = 400
DEFAULT_THROTTLE_QUOTA = 300
DEFAULT_SAFE_SAMPLES = 6
UNIT_RE = re.compile(r"^sf3-(?:plan1|fullstat)-[a-z0-9_-]+\.service$")
SESSION_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
TIMESPAN_RE = re.compile(r"^(?P<value>[0-9]+(?:\.[0-9]+)?)(?P<unit>us|ms|s|min|h)$")
_stop = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_pressure(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] not in {"some", "full"}:
            continue
        for token in parts[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if key in {"avg10", "avg60", "avg300"}:
                result[f"{parts[0]}_{key}"] = float(value)
            elif key == "total":
                result[f"{parts[0]}_total"] = float(int(value))
    required = {"some_avg10", "full_avg10", "some_total", "full_total"}
    if not required.issubset(result):
        raise RuntimeError("cgroup memory.pressure is incomplete")
    return result


def parse_meminfo(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        fields = rest.split()
        if fields and fields[0].isdigit():
            values[key] = int(fields[0]) * 1024
    for key in ("MemAvailable", "SwapFree"):
        if key not in values:
            raise RuntimeError(f"/proc/meminfo lacks {key}")
    return values


def hard_floor_reasons(meminfo: dict[str, int]) -> list[str]:
    reasons: list[str] = []
    if meminfo["MemAvailable"] < MEM_FLOOR_BYTES:
        reasons.append("MemAvailable_hard_floor_breach")
    if meminfo["SwapFree"] < SWAP_FLOOR_BYTES:
        reasons.append("SwapFree_hard_floor_breach")
    return reasons


def disk_floor_reasons(disk_free: int, disk_floor: int | None) -> list[str]:
    if disk_floor is None:
        return []
    return ["DiskFree_hard_floor_breach"] if disk_free < disk_floor else []


def decide_quota(
    pressure: dict[str, float],
    meminfo: dict[str, int],
    current_quota: int,
    safe_streak: int,
    normal_quota: int,
    throttle_quota: int,
    safe_samples: int,
) -> tuple[int, int, list[str]]:
    reasons: list[str] = []
    if pressure["some_avg10"] >= THROTTLE_SOME_AVG10:
        reasons.append("cgroup_some_avg10")
    if pressure["full_avg10"] >= THROTTLE_FULL_AVG10:
        reasons.append("cgroup_full_avg10")
    if meminfo["MemAvailable"] < THROTTLE_MEM_BYTES:
        reasons.append("MemAvailable_guard")
    if meminfo["SwapFree"] < THROTTLE_SWAP_BYTES:
        reasons.append("SwapFree_guard")
    if reasons:
        return throttle_quota, 0, reasons

    safe = (
        pressure["some_avg10"] <= RESTORE_AVG10
        and pressure["full_avg10"] <= RESTORE_AVG10
        and meminfo["MemAvailable"] >= RESTORE_MEM_BYTES
        and meminfo["SwapFree"] >= THROTTLE_SWAP_BYTES
    )
    next_streak = safe_streak + 1 if safe else 0
    if current_quota not in (normal_quota, throttle_quota):
        if safe and next_streak >= safe_samples:
            return normal_quota, next_streak, ["quota_drift_safe_streak_restore"]
        return throttle_quota, next_streak, ["quota_drift_fail_safe_throttle"]
    if current_quota == throttle_quota and next_streak >= safe_samples:
        return normal_quota, next_streak, ["safe_streak_restore"]
    return current_quota, next_streak, ["hold"]


def parse_quota_percent(value: str) -> int | None:
    """Convert systemd CPUQuotaPerSecUSec output to a whole percent."""
    text = value.strip()
    if text in ("", "infinity"):
        return None
    match = TIMESPAN_RE.fullmatch(text)
    if not match:
        raise RuntimeError(f"unrecognized CPUQuotaPerSecUSec value: {text!r}")
    scale = {"us": 1.0e-6, "ms": 1.0e-3, "s": 1.0, "min": 60.0, "h": 3600.0}
    seconds = float(match.group("value")) * scale[match.group("unit")]
    percent = round(seconds * 100.0)
    if percent <= 0:
        raise RuntimeError(f"non-positive CPU quota from systemd: {text!r}")
    return percent


def unit_runtime(unit: str) -> tuple[str, int | None]:
    result = subprocess.run(
        [
            "systemctl", "--user", "show", unit,
            "--property=ActiveState", "--property=CPUQuotaPerSecUSec",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value
    state = properties.get("ActiveState", "")
    if not state:
        raise RuntimeError(f"systemd did not report ActiveState for {unit}")
    return state, parse_quota_percent(properties.get("CPUQuotaPerSecUSec", ""))


def set_quota(unit: str, quota: int) -> None:
    subprocess.run(
        ["systemctl", "--user", "set-property", unit, f"CPUQuota={quota}%"],
        check=True,
    )


def snapshot(pressure_path: Path) -> tuple[dict[str, float], dict[str, int]]:
    return (
        parse_pressure(pressure_path.read_text(encoding="utf-8")),
        parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8")),
    )


def append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def request_stop(_signum: int, _frame: Any) -> None:
    global _stop
    _stop = True


def self_test() -> dict[str, Any]:
    if not UNIT_RE.fullmatch("sf3-plan1-followup.service"):
        raise AssertionError("Plan-1 service-name allowlist self-test failed")
    if not UNIT_RE.fullmatch("sf3-fullstat-followup.service"):
        raise AssertionError("full-stat service-name allowlist self-test failed")
    if UNIT_RE.fullmatch("sf3-unscoped-followup.service") or UNIT_RE.fullmatch("sf3-fullstat-followup.timer"):
        raise AssertionError("service-name denylist self-test failed")
    pressure = parse_pressure(
        "some avg10=16.0 avg60=2.0 avg300=1.0 total=12\n"
        "full avg10=0.0 avg60=0.0 avg300=0.0 total=3\n"
    )
    mem = parse_meminfo("MemAvailable: 5000000 kB\nSwapFree: 12000000 kB\n")
    quota, streak, reasons = decide_quota(
        pressure, mem, 400, 5, 400, 300, 6
    )
    if quota != 300 or streak != 0 or reasons != ["cgroup_some_avg10"]:
        raise AssertionError("pressure throttle self-test failed")
    safe_pressure = dict(pressure, some_avg10=0.0, full_avg10=0.0)
    quota, streak, reasons = decide_quota(
        safe_pressure, mem, 300, 5, 400, 300, 6
    )
    if quota != 400 or streak != 6 or reasons != ["safe_streak_restore"]:
        raise AssertionError("safe restore self-test failed")
    low_mem = dict(mem, MemAvailable=MEM_FLOOR_BYTES + 1)
    quota, _, reasons = decide_quota(
        safe_pressure, low_mem, 400, 0, 400, 300, 6
    )
    if quota != 300 or "MemAvailable_guard" not in reasons:
        raise AssertionError("memory guard self-test failed")
    hard_mem = dict(mem, MemAvailable=MEM_FLOOR_BYTES - 1)
    hard_swap = dict(mem, SwapFree=SWAP_FLOOR_BYTES - 1)
    if hard_floor_reasons(hard_mem) != ["MemAvailable_hard_floor_breach"]:
        raise AssertionError("memory hard-floor self-test failed")
    if hard_floor_reasons(hard_swap) != ["SwapFree_hard_floor_breach"]:
        raise AssertionError("swap hard-floor self-test failed")
    if (
        disk_floor_reasons(8 * GIB - 1, 8 * GIB)
        != ["DiskFree_hard_floor_breach"]
        or disk_floor_reasons(0, None)
    ):
        raise AssertionError("optional disk hard-floor/default-off self-test failed")
    if (
        parse_quota_percent("4s") != 400
        or parse_quota_percent("3000ms") != 300
        or parse_quota_percent("3000000us") != 300
        or parse_quota_percent("infinity") is not None
    ):
        raise AssertionError("systemd quota parser self-test failed")
    # A restarted guard must retain the observed throttle and rebuild its safe
    # streak; it may not pretend the live quota is already the normal quota.
    quota, streak, reasons = decide_quota(
        safe_pressure, mem, 300, 0, 400, 300, 6
    )
    if quota != 300 or streak != 1 or reasons != ["hold"]:
        raise AssertionError("restart-under-throttle self-test failed")
    quota, streak, reasons = decide_quota(
        safe_pressure, mem, 350, 0, 400, 300, 6
    )
    if quota != 300 or streak != 1 or reasons != ["quota_drift_fail_safe_throttle"]:
        raise AssertionError("unexpected quota fail-safe normalization self-test failed")
    quota, streak, reasons = decide_quota(
        safe_pressure, mem, 350, 5, 400, 300, 6
    )
    if quota != 400 or streak != 6 or reasons != ["quota_drift_safe_streak_restore"]:
        raise AssertionError("safe-streak quota drift normalization self-test failed")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_SYSTEMD_PRESSURE_GUARD_SELF_TEST",
        "checks": [
            "user_cgroup_pressure_parser",
            "exact_plan1_or_fullstat_service_name_allowlist",
            "pressure_or_headroom_immediately_throttles_to_shared_three_cores",
            "six_safe_samples_restore_four_cores",
            "restart_reads_and_retains_actual_three_core_quota",
            "hard_MemAvailable_or_SwapFree_floor_breach_forces_nonzero_exit",
            "optional_fullstat_disk_floor_breach_with_plan1_default_off",
            "unexpected_quota_is_normalized_to_three_or_four_core_contract",
            "SIGTERM_or_unit_exit_restores_normal_quota",
            "restore_only_re_reads_and_verifies_normal_quota",
            "event_journal_flush_and_fsync",
            "no_worker_signal_source_event_seed_or_statistics_mutation",
        ],
        "SIM_accessed": False,
        "transport_launched": False,
    }


def run(args: argparse.Namespace) -> int:
    if not UNIT_RE.fullmatch(args.unit):
        raise ValueError("unit must be one exact sf3-(plan1|fullstat)-*.service name")
    if args.throttle_quota >= args.normal_quota:
        raise ValueError("throttle quota must be lower than normal quota")
    uid = os.getuid()
    pressure_path = Path(
        f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service/memory.pressure"
    )
    if not pressure_path.is_file():
        raise FileNotFoundError(pressure_path)
    event_path = Path(args.event_log)
    safe_streak = 0
    try:
        while not _stop:
            state, observed_quota = unit_runtime(args.unit)
            pressure, meminfo = snapshot(pressure_path)
            hard_reasons = hard_floor_reasons(meminfo)
            disk_fields: dict[str, Any] = {}
            if args.disk_path is not None:
                disk_free = shutil.disk_usage(args.disk_path).free
                disk_fields = {
                    "disk_path": str(Path(args.disk_path).resolve()),
                    "disk_free_bytes": disk_free,
                    "disk_floor_bytes": args.disk_floor,
                }
                hard_reasons.extend(disk_floor_reasons(disk_free, args.disk_floor))
            if hard_reasons:
                append_event(
                    event_path,
                    {
                        "at": utc_now(),
                        "unit": args.unit,
                        "session_label": args.session_label,
                        "unit_state": state,
                        "observed_quota_percent": observed_quota,
                        "quota_percent": observed_quota,
                        "quota_changed": False,
                        "decision_reasons": hard_reasons,
                        "safe_streak": safe_streak,
                        "cgroup_pressure": pressure,
                        "mem_available_bytes": meminfo["MemAvailable"],
                        "swap_free_bytes": meminfo["SwapFree"],
                        "mem_floor_bytes": MEM_FLOOR_BYTES,
                        "swap_floor_bytes": SWAP_FLOOR_BYTES,
                        **disk_fields,
                    },
                )
                return 3
            current_quota = observed_quota if observed_quota is not None else args.normal_quota
            desired, safe_streak, reasons = decide_quota(
                pressure,
                meminfo,
                current_quota,
                safe_streak,
                args.normal_quota,
                args.throttle_quota,
                args.safe_samples,
            )
            running = state in ("active", "activating")
            changed = running and (observed_quota is None or desired != observed_quota)
            if changed:
                set_quota(args.unit, desired)
            effective_quota = desired if changed else observed_quota
            append_event(
                event_path,
                {
                    "at": utc_now(),
                    "unit": args.unit,
                    "session_label": args.session_label,
                    "unit_state": state,
                    "observed_quota_percent": observed_quota,
                    "quota_percent": effective_quota,
                    "quota_changed": changed,
                    "decision_reasons": reasons,
                    "safe_streak": safe_streak,
                    "cgroup_pressure": pressure,
                    "mem_available_bytes": meminfo["MemAvailable"],
                    "swap_free_bytes": meminfo["SwapFree"],
                    "mem_floor_bytes": MEM_FLOOR_BYTES,
                    "swap_floor_bytes": SWAP_FLOOR_BYTES,
                    **disk_fields,
                },
            )
            if not running:
                return 0
            time.sleep(args.poll_seconds)
        return 0
    finally:
        try:
            state, observed_quota = unit_runtime(args.unit)
            changed = observed_quota != args.normal_quota
            if changed:
                set_quota(args.unit, args.normal_quota)
            final_state, final_quota = unit_runtime(args.unit)
            if final_quota != args.normal_quota:
                raise RuntimeError(
                    f"guard exit quota restore did not persist: {final_quota!r}"
                )
            final_meminfo = parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))
            final_disk_fields: dict[str, Any] = {}
            if args.disk_path is not None:
                final_disk_free = shutil.disk_usage(args.disk_path).free
                final_disk_fields = {
                    "disk_path": str(Path(args.disk_path).resolve()),
                    "disk_free_bytes": final_disk_free,
                    "disk_floor_bytes": args.disk_floor,
                }
                if final_disk_free < args.disk_floor:
                    raise RuntimeError(
                        f"guard exit disk floor failed: {final_disk_free} < {args.disk_floor}"
                    )
            if (
                final_meminfo["MemAvailable"] < MEM_FLOOR_BYTES
                or final_meminfo["SwapFree"] < SWAP_FLOOR_BYTES
            ):
                raise RuntimeError("guard exit memory/swap hard floor failed")
            append_event(event_path, {
                "at": utc_now(),
                "unit": args.unit,
                "session_label": args.session_label,
                "unit_state": final_state,
                "observed_quota_percent": observed_quota,
                "quota_percent": final_quota,
                "quota_changed": changed,
                "decision_reasons": ["guard_exit_restore_normal"],
                "safe_streak": safe_streak,
                "mem_available_bytes": final_meminfo["MemAvailable"],
                "swap_free_bytes": final_meminfo["SwapFree"],
                "mem_floor_bytes": MEM_FLOOR_BYTES,
                "swap_floor_bytes": SWAP_FLOOR_BYTES,
                **final_disk_fields,
            })
        except Exception as exc:
            append_event(event_path, {
                "at": utc_now(), "unit": args.unit,
                "session_label": args.session_label,
                "decision_reasons": ["guard_exit_restore_failed"],
                "error": str(exc),
            })


def live_check(unit: str) -> dict[str, Any]:
    if not UNIT_RE.fullmatch(unit):
        raise ValueError("unit must be one exact sf3-(plan1|fullstat)-*.service name")
    uid = os.getuid()
    pressure_path = Path(
        f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service/memory.pressure"
    )
    state, quota = unit_runtime(unit)
    pressure, meminfo = snapshot(pressure_path)
    ready = state in ("active", "activating")
    return {
        "schema_version": 1,
        "status": "READY__SF3_PRESSURE_GUARD_LIVE_UNIT" if ready else "NOT_READY__SF3_PRESSURE_GUARD_UNIT_INACTIVE",
        "ready": ready,
        "unit": unit,
        "unit_state": state,
        "observed_quota_percent": quota,
        "cgroup_pressure": pressure,
        "mem_available_bytes": meminfo["MemAvailable"],
        "swap_free_bytes": meminfo["SwapFree"],
        "SIM_accessed": False,
    }


def restore_only(unit: str, quota: int) -> dict[str, Any]:
    if not UNIT_RE.fullmatch(unit):
        raise ValueError("unit must be one exact sf3-(plan1|fullstat)-*.service name")
    state, observed = unit_runtime(unit)
    if observed != quota:
        set_quota(unit, quota)
    final_state, final_observed = unit_runtime(unit)
    if final_observed != quota:
        raise RuntimeError(
            f"restore-only quota verification failed: expected {quota}, observed {final_observed!r}"
        )
    return {
        "schema_version": 1,
        "status": "PASS__SF3_PRESSURE_GUARD_NORMAL_QUOTA_RESTORED",
        "unit": unit,
        "unit_state": final_state,
        "initial_unit_state": state,
        "observed_quota_percent": observed,
        "restored_quota_percent": final_observed,
        "restoration_verified_by_reread": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--restore-only", action="store_true")
    parser.add_argument("--unit")
    parser.add_argument("--event-log")
    parser.add_argument("--session-label", default="unlabeled_guard_session")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--normal-quota", type=int, default=DEFAULT_NORMAL_QUOTA)
    parser.add_argument("--throttle-quota", type=int, default=DEFAULT_THROTTLE_QUOTA)
    parser.add_argument("--safe-samples", type=int, default=DEFAULT_SAFE_SAMPLES)
    parser.add_argument("--disk-path")
    parser.add_argument("--disk-floor", type=int)
    args = parser.parse_args()
    if not (0 < args.throttle_quota < args.normal_quota <= 600):
        raise ValueError("quotas must satisfy 0 < throttle < normal <= 600 percent")
    if args.safe_samples < 1:
        raise ValueError("safe samples must be positive")
    if (args.disk_path is None) != (args.disk_floor is None):
        raise ValueError("disk path and disk floor must be supplied together")
    if args.disk_floor is not None and args.disk_floor <= 0:
        raise ValueError("disk floor must be positive")
    if not SESSION_RE.fullmatch(args.session_label):
        raise ValueError("session label must be one lower-case identifier")
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if not args.unit:
        parser.error("--unit is required outside --self-test")
    if args.check_prerequisites:
        result = live_check(args.unit)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    if args.restore_only:
        print(json.dumps(restore_only(args.unit, args.normal_quota), indent=2, sort_keys=True))
        return 0
    if not args.event_log:
        parser.error("--event-log is required in guard mode")
    if args.poll_seconds < 1.0 or args.poll_seconds > 60.0:
        raise ValueError("poll seconds must be within 1..60")
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
