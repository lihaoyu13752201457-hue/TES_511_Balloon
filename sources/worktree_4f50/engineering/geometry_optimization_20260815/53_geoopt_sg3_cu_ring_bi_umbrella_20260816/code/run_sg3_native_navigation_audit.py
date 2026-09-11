#!/usr/bin/env python3
"""Run native frozen-bank SF3/SG3 geometry comparison without transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
MACRO = SCRIPT.with_name("sg3_native_navigation_audit.C")
SG3_SETUP = PACKAGE / "geometry/DEMO2_DR_v3p5_SG3.geo.setup"
SG3_STATIC = PACKAGE / "audit/sg3_geometry_validation.json"
OUTPUT = PACKAGE / "audit/sg3_native_navigation_audit.json"
SF3_SETUP = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/"
    "geometry/DEMO2_DR_v3p5_SF3.geo.setup"
)
EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/"
    "signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)
MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
ROOT = MEGALIB / "external/root_v6.36.6/bin/root"

EXPECTED = {
    "sf3_setup": "9eb9ac18473ce516139e21983bc24c42906e066784a0e2a05e6b1d227029c0c3",
    "sg3_setup": "91fcdbfd74fca4f7a261e1ec27b39fcf2adc49f91ca9d7d1dff02591b26c16e6",
    "eventlist": "a709a6dcbf5eaebda60be7ec419f4c214979d4cb215254134568eccebe27e57e",
}


class AuditError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def quote_root(value: Path) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def environment() -> dict[str, str]:
    env = os.environ.copy()
    rootsys = ROOT.parents[1]
    env["MEGALIB"] = str(MEGALIB)
    env["ROOTSYS"] = str(rootsys)
    env["PATH"] = f"{MEGALIB / 'bin'}:{rootsys / 'bin'}:{env.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = ":".join(
        part
        for part in (str(MEGALIB / "lib"), str(rootsys / "lib"), env.get("LD_LIBRARY_PATH", ""))
        if part
    )
    env["ROOT_INCLUDE_PATH"] = ":".join(
        part for part in (str(MEGALIB / "include"), env.get("ROOT_INCLUDE_PATH", "")) if part
    )
    return env


def validate_native(native: dict[str, Any]) -> None:
    if native.get("status") != "PASS" or native.get("error_count") != 0:
        raise AuditError(f"native core failed: {native.get('errors')}")
    if native.get("transport_launched") is not False or native.get("rows") != 37_194:
        raise AuditError("transport/row boundary failed")
    path = native.get("material_path_contract", {})
    for key in (
        "all_non_Cu_non_Vacuum_material_equal_rays",
        "no_positive_Cu_delta_rays",
        "zero_Bi_chord_rays",
        "zero_W_delta_rays",
    ):
        if path.get(key) != 37_194:
            raise AuditError(f"material path closure failed: {key}={path.get(key)}")
    if not 0 < int(path.get("reduced_Cu_rays", 0)) <= 37_194:
        raise AuditError("Cu reduction population failed")
    clearance = native.get("bi_focused_clearance", {})
    if clearance.get("analytic_passes") != 37_194:
        raise AuditError("analytic Bi clearance failed")
    if clearance.get("native_queries") != 111_582 or clearance.get("native_no_Bi_passes") != 111_582:
        raise AuditError("native Bi focused probes failed")
    witnesses = native.get("presence_witnesses", {})
    if witnesses.get("volume_passes") != 3:
        raise AuditError("presence/opening witnesses failed")
    if abs(float(witnesses.get("Bi_thickness_cm")) - 0.4796) > 2.0e-5:
        raise AuditError("Bi thickness witness failed")
    if abs(float(witnesses.get("ring_minus_disk_Cu_path_cm")) + 0.4) > 2.0e-5:
        raise AuditError("Cu ring path witness failed")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        compare = dict(payload)
        for item in (existing, compare):
            for key in ("generated_at_utc", "elapsed_seconds", "driver"):
                item.pop(key, None)
        if existing != compare:
            raise AuditError(f"write-once audit exists with different contract: {path}")
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    args = parser.parse_args()
    started = datetime.now(timezone.utc)
    try:
        for path in (MACRO, SF3_SETUP, SG3_SETUP, SG3_STATIC, EVENTLIST, ROOT):
            if not path.is_file():
                raise AuditError(f"missing prerequisite: {path}")
        observed = {
            "sf3_setup": sha256(SF3_SETUP),
            "sg3_setup": sha256(SG3_SETUP),
            "eventlist": sha256(EVENTLIST),
        }
        if observed != EXPECTED:
            raise AuditError(f"input hash drift: observed={observed}")
        static = json.loads(SG3_STATIC.read_text(encoding="utf-8"))
        if static.get("status") != "PASS__SG3_TWO_CHANGE_BYTE_REVERSIBLE_SF3_CHILD":
            raise AuditError("SG3 static geometry authority is not PASS")
        if static.get("generated", {}).get("setup", {}).get("sha256") != EXPECTED["sg3_setup"]:
            raise AuditError("SG3 static authority is stale")

        with tempfile.TemporaryDirectory(prefix="sg3_native_navigation_", dir="/tmp") as tmp:
            tmpdir = Path(tmp)
            native_path = tmpdir / "native.json"
            build_dir = tmpdir / "aclic"
            expression = (
                f'{quote_root(MACRO)}+("{quote_root(SF3_SETUP)}",'
                f'"{quote_root(SG3_SETUP)}","{quote_root(EVENTLIST)}",'
                f'"{quote_root(native_path)}")'
            )
            command = [
                str(ROOT), "-l", "-b", "-n", "-q", "-e",
                f'gSystem->SetBuildDir("{quote_root(build_dir)}", kTRUE);',
                expression,
            ]
            completed = subprocess.run(
                command,
                cwd=PACKAGE,
                env=environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                timeout=args.timeout_seconds,
                check=False,
            )
            if completed.returncode != 0:
                native = (
                    json.loads(native_path.read_text(encoding="utf-8"))
                    if native_path.is_file()
                    else None
                )
                raise AuditError(
                    f"ROOT native audit failed rc={completed.returncode}; "
                    f"native={native}; stderr_tail={completed.stderr[-5000:]}"
                )
            if not native_path.is_file():
                raise AuditError("ROOT native audit did not create JSON")
            native = json.loads(native_path.read_text(encoding="utf-8"))
            validate_native(native)

        payload = dict(native)
        payload["status"] = "PASS__SG3_NATIVE_SF3_FROZEN_BANK_GEOMETRY_AUDIT"
        payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload["elapsed_seconds"] = (datetime.now(timezone.utc) - started).total_seconds()
        payload["inputs"] = {
            "sf3_setup": record(SF3_SETUP),
            "sg3_setup": record(SG3_SETUP),
            "eventlist": record(EVENTLIST),
            "sg3_static_validation": record(SG3_STATIC),
            "macro": record(MACRO),
        }
        payload["driver"] = {
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
            "stdout_tail": completed.stdout.splitlines()[-40:],
            "stderr_tail": completed.stderr.splitlines()[-40:],
            "temporary_build_directory": True,
        }
        payload["authority_boundary"] = "GEOMETRY_AND_NAVIGATION_ONLY__NO_TRANSPORT"
        atomic_json(OUTPUT, payload)
        print(json.dumps({"status": payload["status"], "output": str(OUTPUT)}, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "FAIL__SG3_NATIVE_NAVIGATION_AUDIT", "error": str(exc), "transport_launched": False},
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
