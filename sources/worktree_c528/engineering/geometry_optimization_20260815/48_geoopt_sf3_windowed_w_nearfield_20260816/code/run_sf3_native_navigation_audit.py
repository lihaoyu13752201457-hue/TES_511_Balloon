#!/usr/bin/env python3
"""Run the native frozen-bank SE3/SF3 geometry comparison without transport."""

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
MACRO = SCRIPT.with_name("sf3_native_navigation_audit.C")
SF3_SETUP = PACKAGE / "geometry/DEMO2_DR_v3p5_SF3.geo.setup"
SF3_STATIC = PACKAGE / "audit/sf3_geometry_validation.json"
OUTPUT = PACKAGE / "audit/sf3_native_navigation_audit.json"

SE3_SETUP = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/geometry/"
    "DEMO2_DR_v3p5_SE3.geo.setup"
)
EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/"
    "signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)
MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
ROOT = MEGALIB / "external/root_v6.36.6/bin/root"

EXPECTED = {
    "se3_setup": "3e32bcd555a3c83cf8144949ad0bb31594f14f5204deb3784b2eb4cdd982ca98",
    "sf3_setup": "9eb9ac18473ce516139e21983bc24c42906e066784a0e2a05e6b1d227029c0c3",
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
        for part in (
            str(MEGALIB / "lib"),
            str(rootsys / "lib"),
            env.get("LD_LIBRARY_PATH", ""),
        )
        if part
    )
    env["ROOT_INCLUDE_PATH"] = ":".join(
        part for part in (str(MEGALIB / "include"), env.get("ROOT_INCLUDE_PATH", "")) if part
    )
    return env


def validate_native(native: dict[str, Any]) -> None:
    if native.get("status") != "PASS":
        raise AuditError(f"native audit status is not PASS: {native.get('errors')}")
    if native.get("transport_launched") is not False:
        raise AuditError("native audit transport boundary failed")
    if native.get("rows") != 37_194:
        raise AuditError("native audit row closure failed")
    path = native.get("full_path_material_comparison", {})
    if path.get("equal_rays") != 37_194:
        raise AuditError("SE3/SF3 full material-path equality failed")
    added = native.get("added_W_focused_chord", {})
    if added.get("zero_rays") != 37_194:
        raise AuditError("focused rays acquire nonzero SF3 W chord")
    for key in ("front_square", "side_inner_radius", "rear_service_aperture"):
        if native.get("analytic_clearance", {}).get(key, {}).get("passes") != 37_194:
            raise AuditError(f"analytic clearance failed: {key}")
    probes = native.get("native_focused_volume_probes", {})
    if probes.get("queries") != 111_582 or probes.get("no_SF3_W_passes") != 111_582:
        raise AuditError("native focused-volume probes did not close")
    witnesses = native.get("W_presence_witnesses", {})
    if witnesses.get("volume_passes") != 3:
        raise AuditError("SF3 W presence witnesses failed")
    delta_w = witnesses.get("delta_W_cm")
    if not isinstance(delta_w, list) or len(delta_w) != 3:
        raise AuditError("SF3 W thickness witnesses must contain exactly three values")
    for value in delta_w:
        if abs(float(value) - 0.29) > 2.0e-5:
            raise AuditError("SF3 W thickness witness failed")
    if native.get("error_count") != 0:
        raise AuditError("native audit reported errors")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        for key in ("generated_at_utc", "elapsed_seconds", "driver"):
            existing.pop(key, None)
        compare = dict(payload)
        for key in ("generated_at_utc", "elapsed_seconds", "driver"):
            compare.pop(key, None)
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
        for path in (MACRO, SF3_SETUP, SF3_STATIC, SE3_SETUP, EVENTLIST, ROOT):
            if not path.is_file():
                raise AuditError(f"missing prerequisite: {path}")
        observed = {
            "se3_setup": sha256(SE3_SETUP),
            "sf3_setup": sha256(SF3_SETUP),
            "eventlist": sha256(EVENTLIST),
        }
        if observed != EXPECTED:
            raise AuditError(f"input hash drift: observed={observed}, expected={EXPECTED}")
        static = json.loads(SF3_STATIC.read_text(encoding="utf-8"))
        if static.get("status") != "PASS__SF3_STRICT_ADDITIVE_GEOMETRY_DELTA":
            raise AuditError("SF3 static geometry authority is not PASS")
        if static.get("generated", {}).get("setup", {}).get("sha256") != EXPECTED["sf3_setup"]:
            raise AuditError("SF3 static authority is stale")

        with tempfile.TemporaryDirectory(prefix="sf3_native_navigation_", dir="/tmp") as tmp:
            tmpdir = Path(tmp)
            native_path = tmpdir / "native.json"
            build_dir = tmpdir / "aclic"
            expression = (
                f'{quote_root(MACRO)}+("{quote_root(SE3_SETUP)}",'
                f'"{quote_root(SF3_SETUP)}","{quote_root(EVENTLIST)}",'
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
                raise AuditError(
                    "ROOT native audit failed: "
                    f"rc={completed.returncode}; stderr_tail={completed.stderr[-5000:]}"
                )
            if not native_path.is_file():
                raise AuditError("ROOT native audit did not create JSON")
            native = json.loads(native_path.read_text(encoding="utf-8"))
            validate_native(native)

        payload = dict(native)
        payload["status"] = "PASS__SF3_NATIVE_FROZEN_BANK_AND_W_WITNESS_AUDIT"
        payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload["elapsed_seconds"] = (
            datetime.now(timezone.utc) - started
        ).total_seconds()
        payload["inputs"] = {
            "se3_setup": record(SE3_SETUP),
            "sf3_setup": record(SF3_SETUP),
            "eventlist": record(EVENTLIST),
            "sf3_static_validation": record(SF3_STATIC),
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
        payload["authority_boundary"] = (
            "GEOMETRY_AND_NAVIGATION_ONLY__NO_PARTICLE_SOURCE_OR_TRANSPORT"
        )
        atomic_json(OUTPUT, payload)
        print(json.dumps({"status": payload["status"], "output": str(OUTPUT)}, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL__SF3_NATIVE_NAVIGATION_AUDIT",
                    "error": str(exc),
                    "transport_launched": False,
                },
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
