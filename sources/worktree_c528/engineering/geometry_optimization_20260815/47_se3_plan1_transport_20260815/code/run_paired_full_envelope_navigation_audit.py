#!/usr/bin/env python3
"""Check or run the paired native full-envelope signal navigator audit.

``--check`` is static and may be used while the production gamma canary is
active.  It validates the frozen paired bank, source/job bindings, setup text,
and native-audit inputs without invoking ROOT.  ``--run`` is fail-closed until
the canonical gamma-canary PASS receipt exists; it then runs the geometry-only
MEGAlib macro.  The signal transport authority is published only after every
native counter closes.  This program never discovers, opens, or hashes a SIM.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
REPO_ROOT = PACKAGE.parents[2]
RUN_ROOT = REPO_ROOT / "runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1"

MACRO = SCRIPT.with_name("paired_full_envelope_navigation_audit.C")
STATIC_AUDIT = PACKAGE / "audit/full_envelope_signal_static_audit.json"
NAVIGATION_PLAN = PACKAGE / "data/full_envelope_signal_navigation_plan.csv"
JOB_PLAN = PACKAGE / "data/se3_plan1_job_plan.csv"
SEED_REGISTRY = PACKAGE / "data/se3_plan1_seed_registry.csv"
PREFLIGHT_OUTPUT = PACKAGE / "audit/full_envelope_signal_navigation_preflight.json"
NAVIGATION_OUTPUT = PACKAGE / "audit/full_envelope_signal_navigation_audit.json"
NATIVE_FAILURE_OUTPUT = PACKAGE / "audit/full_envelope_signal_navigation_failure.json"
TRANSPORT_GATE_OUTPUT = PACKAGE / "audit/full_envelope_signal_transport_gate.json"

EVENTLISTS = {
    "S3d_O8": PACKAGE
    / "config/signal_eventlists/signal_full_envelope_s3d_o8.eventlist.dat",
    "SE3": PACKAGE
    / "config/signal_eventlists/signal_full_envelope_se3.eventlist.dat",
}
SOURCES = {
    "S3d_O8": PACKAGE
    / "config/signal_source_cards/signal_full_envelope_s3d_o8.source",
    "SE3": PACKAGE / "config/signal_source_cards/signal_full_envelope_se3.source",
}
JOBS = {
    "S3d_O8": "signal_full_envelope_s3d_o8",
    "SE3": "signal_full_envelope_se3",
}
OBSERVED_ORDERS = {
    "S3d_O8": "PLASTIC_THEN_BPE",
    "SE3": "PLASTIC_THEN_BPE_PORT",
}

EXPECTED_ROWS = 37_194
EXPECTED_FIELDS = 15
EXPECTED_BANK_SHA256 = "a709a6dcbf5eaebda60be7ec419f4c214979d4cb215254134568eccebe27e57e"
EXPECTED_SEED = 93_405_522
EXPECTED_SEED_IDENTITY = "full_envelope_signal_pair_37194"
INJECTION_XPRIME_CM = -30.0001
ROTATION_Y_DEG = 45.0
PLASTIC_OUTER_RADIUS_CM = 30.0
CHORD_CLOSURE_TOLERANCE_CM = 2.0e-5
BPE_ZERO_TOLERANCE_CM = 1.0e-9

CANARY_JOB_ID = "se3_instant_gamma_shard0001"
CANARY_RECEIPT = RUN_ROOT / "receipts" / f"{CANARY_JOB_ID}.json"
CANARY_ACTIVE_DIR = RUN_ROOT / "jobs" / CANARY_JOB_ID / "active"

DEFAULT_MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
DEFAULT_ROOT = DEFAULT_MEGALIB / "external/root_v6.36.6/bin/root"


class AuditError(RuntimeError):
    """A fail-closed static, admission, invocation, or result error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, *, digest: bool = True) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "bytes": path.stat().st_size}
    if digest:
        record["sha256"] = sha256_file(path)
    return record


def require_file(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise AuditError(f"{label} does not resolve: {path}: {exc}") from exc
    if not resolved.is_file():
        raise AuditError(f"{label} is not a regular file: {resolved}")
    return resolved


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} JSON is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} JSON root is not an object: {path}")
    return value


def read_csv(path: Path, label: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise AuditError(f"{label} has no header: {path}")
            rows = list(reader)
    except OSError as exc:
        raise AuditError(f"{label} is unreadable: {path}: {exc}") from exc
    if not rows:
        raise AuditError(f"{label} has no rows: {path}")
    return rows


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def world_to_instrument(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    angle = math.radians(ROTATION_Y_DEG)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    x, y, z = vector
    return cosine * x - sine * z, y, sine * x + cosine * z


def inspect_paired_bank() -> dict[str, Any]:
    paths = {key: require_file(path, f"{key} signal EventList") for key, path in EVENTLISTS.items()}
    raw = {key: path.read_bytes() for key, path in paths.items()}
    digests = {key: sha256_bytes(value) for key, value in raw.items()}
    if set(digests.values()) != {EXPECTED_BANK_SHA256}:
        raise AuditError(
            f"paired EventList SHA mismatch: {digests}; expected {EXPECTED_BANK_SHA256}"
        )
    if raw["S3d_O8"] != raw["SE3"]:
        raise AuditError("S3d-O8 and SE3 EventLists are not byte-identical")
    try:
        text = raw["S3d_O8"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError("paired EventList is not UTF-8") from exc

    rows = 0
    minimum_xprime = math.inf
    maximum_xprime = -math.inf
    minimum_outside = math.inf
    minimum_direction_xprime = math.inf
    maximum_norm_error = 0.0
    for physical_line, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        if len(tokens) != EXPECTED_FIELDS:
            raise AuditError(
                f"EventList line {physical_line}: {len(tokens)} fields, expected {EXPECTED_FIELDS}"
            )
        try:
            values = [float(token) for token in tokens]
        except ValueError as exc:
            raise AuditError(f"EventList line {physical_line}: non-numeric field") from exc
        if not all(math.isfinite(value) for value in values):
            raise AuditError(f"EventList line {physical_line}: non-finite field")
        event_id = int(round(values[0]))
        if not math.isclose(values[0], event_id, rel_tol=0.0, abs_tol=1.0e-12) or event_id != rows:
            raise AuditError(f"EventList line {physical_line}: non-sequential ID {values[0]}")
        if values[14] != 511.0:
            raise AuditError(f"EventList line {physical_line}: energy {values[14]} is not 511 keV")
        point = world_to_instrument((values[5], values[6], values[7]))
        direction = world_to_instrument((values[8], values[9], values[10]))
        norm = math.sqrt(math.fsum(component * component for component in direction))
        if not math.isclose(point[0], INJECTION_XPRIME_CM, rel_tol=0.0, abs_tol=1.0e-7):
            raise AuditError(
                f"EventList line {physical_line}: x'={point[0]} is not {INJECTION_XPRIME_CM}"
            )
        if direction[0] <= 0.999 or not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1.0e-8):
            raise AuditError(f"EventList line {physical_line}: direction contract failed")
        outside = math.hypot(point[0], point[1]) - PLASTIC_OUTER_RADIUS_CM
        if outside <= 0.0:
            raise AuditError(f"EventList line {physical_line}: start is not outside r=30 cm")
        minimum_xprime = min(minimum_xprime, point[0])
        maximum_xprime = max(maximum_xprime, point[0])
        minimum_outside = min(minimum_outside, outside)
        minimum_direction_xprime = min(minimum_direction_xprime, direction[0])
        maximum_norm_error = max(maximum_norm_error, abs(norm - 1.0))
        rows += 1
    if rows != EXPECTED_ROWS:
        raise AuditError(f"paired EventList rows={rows}, expected {EXPECTED_ROWS}")
    return {
        "status": "PASS",
        "byte_identical": True,
        "shared_sha256": EXPECTED_BANK_SHA256,
        "bytes_each": len(raw["S3d_O8"]),
        "rows": rows,
        "field_count": EXPECTED_FIELDS,
        "ids": {"first": 0, "last": rows - 1, "zero_based_sequential": True},
        "energy_keV": 511.0,
        "injection_xprime_cm": {
            "target": INJECTION_XPRIME_CM,
            "min": minimum_xprime,
            "max": maximum_xprime,
        },
        "minimum_analytic_outside_clearance_cm": minimum_outside,
        "minimum_direction_xprime": minimum_direction_xprime,
        "maximum_direction_norm_error": maximum_norm_error,
        "paths": {key: str(path) for key, path in paths.items()},
        "no_resampling": True,
    }


def setup_main_geometry(setup: Path) -> Path:
    includes = []
    for line in setup.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] == "Include" and fields[1].endswith(".geo"):
            includes.append(fields[1])
    if len(includes) != 1:
        raise AuditError(f"setup must have exactly one .geo Include: {setup}: {includes}")
    return require_file(setup.parent / includes[0], f"main geometry included by {setup.name}")


def inspect_geometry_contract(geometry: str, setup_path: Path) -> dict[str, Any]:
    setup = require_file(setup_path, f"{geometry} setup")
    setup_text = setup.read_text(encoding="utf-8")
    if geometry == "S3d_O8":
        required_setup_name = "Name DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
    else:
        required_setup_name = "Name DEMO2_DR_v3p5_SE3"
    if required_setup_name not in setup_text.splitlines():
        raise AuditError(f"{geometry} setup identity mismatch: {setup}")
    main_geo = setup_main_geometry(setup)
    text = main_geo.read_text(encoding="utf-8")
    common_required = (
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_FullShape.Parameters 0 360 2 -37.25 29 30 37.25 29 30",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm.Material PlasticScintillator",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm.Position 0 0 10.75",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_FullShape.Parameters 0 360 2 -35.25 27 29 35.25 27 29",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Material BoratedPolyethylene5wtB",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Position 0 0 10.75",
    )
    missing = [line for line in common_required if line not in text]
    if missing:
        raise AuditError(f"{geometry} frozen envelope contract missing lines: {missing}")
    port_tokens = (
        "SE3_BPE_FocusedPortCutShape.Parameters 14.5001 1.898 1.898",
        "SE3_BPE_FocusedPortCutOrientation.Position -14.5 0 -15.95",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape SE3_BPE_FocusedPortFinalShape",
    )
    if geometry == "SE3":
        port_missing = [line for line in port_tokens if line not in text]
        if port_missing:
            raise AuditError(f"SE3 BPE focused-port contract missing lines: {port_missing}")
        port_state = "BPE_ONLY_PORT_PRESENT__PLASTIC_UNCUT"
    else:
        unexpected = [line for line in port_tokens if line in text]
        if unexpected:
            raise AuditError(f"S3d-O8 unexpectedly contains SE3 BPE port lines: {unexpected}")
        port_state = "NO_BPE_FOCUSED_PORT__COMPLETE_BPE_SHELL"
    return {
        "status": "PASS",
        "setup": file_record(setup),
        "main_geometry": file_record(main_geo),
        "plastic_shell_radii_cm": [29.0, 30.0],
        "bpe_shell_radii_cm": [27.0, 29.0],
        "focused_port_state": port_state,
        "observed_forward_order": OBSERVED_ORDERS[geometry],
    }


def inspect_source_and_registry(
    geometry: str, setup: Path, eventlist: Path
) -> dict[str, Any]:
    source = require_file(SOURCES[geometry], f"{geometry} signal source")
    text = source.read_text(encoding="utf-8")
    job_id = JOBS[geometry]
    output_prefix = RUN_ROOT / "jobs" / job_id / "active" / job_id
    required_lines = {
        f"Geometry {setup}",
        f"Seed {EXPECTED_SEED}",
        f"Run {job_id}",
        f"{job_id}.FileName {output_prefix}",
        f"{job_id}.Triggers {EXPECTED_ROWS}",
        f"{job_id}_EventList.EventList {eventlist}",
    }
    missing = sorted(required_lines - set(text.splitlines()))
    if missing:
        raise AuditError(f"{geometry} signal source missing exact bindings: {missing}")

    job_rows = [row for row in read_csv(JOB_PLAN, "job plan") if row.get("job_id") == job_id]
    if len(job_rows) != 1:
        raise AuditError(f"job plan must contain exactly one row for {job_id}")
    job = job_rows[0]
    expected_job = {
        "stage": "signal",
        "geometry": geometry,
        "events": str(EXPECTED_ROWS),
        "seed": str(EXPECTED_SEED),
        "seed_identity": EXPECTED_SEED_IDENTITY,
        "paired_seed_exception": "True",
        "source_path": str(source),
        "setup_path": str(setup),
    }
    wrong = {
        key: {"actual": job.get(key), "expected": value}
        for key, value in expected_job.items()
        if job.get(key) != value
    }
    if wrong:
        raise AuditError(f"job-plan signal binding mismatch for {job_id}: {wrong}")

    seed_rows = [
        row for row in read_csv(SEED_REGISTRY, "seed registry") if row.get("job_id") == job_id
    ]
    if len(seed_rows) != 1:
        raise AuditError(f"seed registry must contain exactly one row for {job_id}")
    seed = seed_rows[0]
    expected_seed = {
        "seed": str(EXPECTED_SEED),
        "seed_identity": EXPECTED_SEED_IDENTITY,
        "paired_seed_exception": "True",
        "collision_with_prior": "False",
    }
    seed_wrong = {
        key: {"actual": seed.get(key), "expected": value}
        for key, value in expected_seed.items()
        if seed.get(key) != value
    }
    if seed_wrong:
        raise AuditError(f"seed-registry binding mismatch for {job_id}: {seed_wrong}")
    return {
        "status": "PASS",
        "job_id": job_id,
        "source": file_record(source),
        "setup": str(setup),
        "eventlist": str(eventlist),
        "shared_seed": EXPECTED_SEED,
        "seed_identity": EXPECTED_SEED_IDENTITY,
        "output_prefix": str(output_prefix),
        "runner_prefix_contract": "RUN_ROOT/jobs/<job_id>/active/<job_id>",
    }


def inspect_canary() -> dict[str, Any]:
    # Deliberately inspect only the canonical small receipt and active-directory
    # sentinel.  Never enumerate or touch files inside the active directory.
    if CANARY_RECEIPT.is_file():
        receipt = load_json(CANARY_RECEIPT, "gamma canary receipt")
        if receipt.get("status") == "PASS" and receipt.get("job_id") == CANARY_JOB_ID:
            return {
                "state": "PASS",
                "receipt_path": str(CANARY_RECEIPT),
                "receipt_status": "PASS",
                "active_directory_exists": CANARY_ACTIVE_DIR.is_dir(),
            }
        return {
            "state": "NON_PASS_RECEIPT",
            "receipt_path": str(CANARY_RECEIPT),
            "receipt_status": receipt.get("status"),
            "active_directory_exists": CANARY_ACTIVE_DIR.is_dir(),
        }
    return {
        "state": "ACTIVE" if CANARY_ACTIVE_DIR.is_dir() else "NOT_PASS",
        "receipt_path": str(CANARY_RECEIPT),
        "receipt_status": None,
        "active_directory_exists": CANARY_ACTIVE_DIR.is_dir(),
    }


def inspect_static_authority() -> tuple[dict[str, Any], dict[str, Path]]:
    static_path = require_file(STATIC_AUDIT, "full-envelope static audit")
    static = load_json(static_path, "full-envelope static audit")
    if static.get("status") != "PASS__FULL_ENVELOPE_SIGNAL_STATIC_PREPARATION":
        raise AuditError(f"static signal preparation is not PASS: {static.get('status')!r}")
    pair = static.get("pair")
    if not isinstance(pair, dict) or pair.get("byte_identical_geometry_banks") is not True:
        raise AuditError("static audit does not certify byte-identical geometry banks")
    if pair.get("shared_seed") != EXPECTED_SEED or pair.get("seed_identity") != EXPECTED_SEED_IDENTITY:
        raise AuditError("static audit paired seed identity mismatch")
    jobs = pair.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 2:
        raise AuditError("static audit must contain two paired jobs")
    setups: dict[str, Path] = {}
    for row in jobs:
        if not isinstance(row, dict) or row.get("geometry") not in JOBS:
            raise AuditError("static audit has malformed paired job")
        geometry = str(row["geometry"])
        if row.get("job_id") != JOBS[geometry] or row.get("events") != EXPECTED_ROWS:
            raise AuditError(f"static audit job binding mismatch for {geometry}")
        if row.get("eventlist_sha256") != EXPECTED_BANK_SHA256:
            raise AuditError(f"static audit bank SHA mismatch for {geometry}")
        if Path(str(row.get("eventlist_path"))).resolve() != EVENTLISTS[geometry].resolve():
            raise AuditError(f"static audit EventList path mismatch for {geometry}")
        setups[geometry] = require_file(Path(str(row.get("setup_path"))), f"{geometry} setup")
    return file_record(static_path) | {"status": static["status"]}, setups


def inspect_navigation_plan(setups: dict[str, Path]) -> dict[str, Any]:
    plan_path = require_file(NAVIGATION_PLAN, "full-envelope navigation plan")
    rows = read_csv(plan_path, "full-envelope navigation plan")
    if len(rows) != 2:
        raise AuditError(f"navigation plan has {len(rows)} rows, expected 2")
    by_geometry = {row.get("geometry", ""): row for row in rows}
    if set(by_geometry) != set(JOBS):
        raise AuditError(f"navigation plan geometry set mismatch: {sorted(by_geometry)}")
    for geometry, row in by_geometry.items():
        expected = {
            "job_id": JOBS[geometry],
            "setup_path": str(setups[geometry]),
            "eventlist_path": str(EVENTLISTS[geometry]),
            "eventlist_sha256": EXPECTED_BANK_SHA256,
            "rows": str(EXPECTED_ROWS),
            "shared_seed": str(EXPECTED_SEED),
            "injection_plane_xprime_cm": str(INJECTION_XPRIME_CM),
            "require_start_outside_geometry": "true",
            "require_forward_xprime": "true",
            "transport_gate": "NAVIGATOR_PASS_REQUIRED_BEFORE_LAUNCH",
        }
        wrong = {
            key: {"actual": row.get(key), "expected": value}
            for key, value in expected.items()
            if row.get(key) != value
        }
        if wrong:
            raise AuditError(f"navigation-plan mismatch for {geometry}: {wrong}")
    return file_record(plan_path) | {"status": "PASS", "rows": len(rows)}


def inspect_runtime(megalib: Path, root_binary: Path) -> dict[str, Any]:
    try:
        resolved_megalib = megalib.expanduser().resolve(strict=True)
    except OSError as exc:
        raise AuditError(f"MEGAlib root does not resolve: {megalib}: {exc}") from exc
    if not resolved_megalib.is_dir():
        raise AuditError(f"MEGAlib root is not a directory: {resolved_megalib}")
    root = require_file(root_binary, "ROOT binary")
    if not os.access(root, os.X_OK):
        raise AuditError(f"ROOT binary is not executable: {root}")
    macro = require_file(MACRO, "paired native audit macro")
    macro_text = macro.read_text(encoding="utf-8")
    required_tokens = (
        "MDGeometryQuest",
        "GetPathLengths",
        "GetVolumeSequence",
        "PLASTIC_THEN_BPE",
        "PLASTIC_THEN_BPE_PORT",
        "transport_launched",
    )
    missing = [token for token in required_tokens if token not in macro_text]
    if missing:
        raise AuditError(f"native macro missing required contract tokens: {missing}")
    return {
        "status": "PASS",
        "megalib_root": str(resolved_megalib),
        "root_binary": file_record(root),
        "native_macro": file_record(macro),
        "check_mode_invokes_root": False,
    }


def collect_preflight(megalib: Path, root_binary: Path) -> dict[str, Any]:
    started = time.monotonic()
    static_record, setups = inspect_static_authority()
    paired_bank = inspect_paired_bank()
    navigation_plan = inspect_navigation_plan(setups)
    geometries = {
        geometry: inspect_geometry_contract(geometry, setups[geometry])
        for geometry in JOBS
    }
    source_bindings = {
        geometry: inspect_source_and_registry(
            geometry, setups[geometry], EVENTLISTS[geometry].resolve()
        )
        for geometry in JOBS
    }
    runtime = inspect_runtime(megalib, root_binary)
    canary = inspect_canary()
    native_authority_exists = NAVIGATION_OUTPUT.is_file()
    return {
        "schema_version": 1,
        "status": "PASS__STATIC_PREFLIGHT_NATIVE_DEFERRED",
        "generated_utc": utc_now(),
        "elapsed_seconds": time.monotonic() - started,
        "transport_launched": False,
        "root_invoked": False,
        "sim_policy": "NO_SIM_DISCOVERY_OPEN_OR_HASH",
        "static_preparation_authority": static_record,
        "paired_bank": paired_bank,
        "navigation_plan": navigation_plan,
        "geometry_static_contracts": geometries,
        "source_job_seed_bindings": source_bindings,
        "runtime_inputs": runtime,
        "gamma_production_canary": canary,
        "native_run_admission": {
            "status": "PASS" if canary["state"] == "PASS" else "BLOCKED",
            "requirement": "canonical production gamma canary PASS receipt",
        },
        "signal_transport_gate": {
            "status": "PASS" if native_authority_exists else "BLOCKED_PENDING_NATIVE_PASS",
            "authoritative_navigation_audit": str(NAVIGATION_OUTPUT),
            "authoritative_navigation_audit_exists": native_authority_exists,
            "transport_gate_receipt": str(TRANSPORT_GATE_OUTPUT),
        },
        "wording_interpretation": {
            "handoff_phrase": "complete BPE then continuous plastic",
            "frozen_geometry_forward_order": (
                "outer plastic r=29..30 cm, then BPE/BPE-port r=27..29 cm"
            ),
            "resolution": (
                "native audit reports the physical forward order; the handoff phrase is "
                "treated as layer-coverage requirements and does not reverse frozen geometry"
            ),
            "observed_orders": OBSERVED_ORDERS,
        },
    }


def cpp_string(value: str) -> str:
    if "\x00" in value or "\n" in value or "\r" in value:
        raise AuditError("native-audit path contains a prohibited control character")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def prepend_env(env: dict[str, str], name: str, values: list[Path]) -> None:
    parts = [str(path) for path in values]
    existing = env.get(name, "")
    if existing:
        parts.append(existing)
    env[name] = os.pathsep.join(parts)


def tail_text(value: str | bytes | None, limit: int = 12_000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-limit:]


def nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise AuditError(f"native JSON missing {'.'.join(keys)}")
        value = value[key]
    return value


def finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise AuditError(f"native JSON {label} is not a finite number: {value!r}")
    return float(value)


def validate_native(native: dict[str, Any], returncode: int, stdout: str) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    def equal(name: str, actual: Any, expected: Any) -> None:
        checks[name] = actual == expected
        if not checks[name]:
            raise AuditError(f"native result {name}: got {actual!r}, expected {expected!r}")

    equal("root_returncode", returncode, 0)
    equal("native_status", native.get("status"), "PASS")
    equal("transport_not_launched", native.get("transport_launched"), False)
    equal("mglobal_initialized", native.get("mglobal_initialized"), True)
    equal("failure_count", native.get("failure_count"), 0)
    equal(
        "no_negative_path_length_warning",
        "Warning: Negative length in volume:" in stdout,
        False,
    )
    for geometry in JOBS:
        node = nested(native, "geometries", geometry)
        equal(f"{geometry}.status", node.get("status"), "PASS")
        equal(f"{geometry}.observed_order", node.get("observed_order"), OBSERVED_ORDERS[geometry])
        for field in (
            "logical_rows",
            "parsed_rows",
            "id_passes",
            "energy_511kev_passes",
            "input_plane_passes",
            "forward_direction_passes",
            "analytic_start_outside_passes",
            "native_start_outside_passes",
            "ordered_intersection_passes",
            "get_path_lengths_calls",
            "material_map_passes",
        ):
            equal(f"{geometry}.{field}", node.get(field), EXPECTED_ROWS)
        plastic = nested(node, "plastic")
        equal(f"{geometry}.plastic_positive", plastic.get("positive_chord_passes"), EXPECTED_ROWS)
        equal(f"{geometry}.plastic_full", plastic.get("full_chord_passes"), EXPECTED_ROWS)
        equal(f"{geometry}.plastic_probe_queries", plastic.get("continuity_probe_queries"), EXPECTED_ROWS * 5)
        equal(f"{geometry}.plastic_probe_passes", plastic.get("continuity_probe_passes"), EXPECTED_ROWS * 5)
        outside_min = finite_number(nested(node, "outside_clearance_cm", "min"), f"{geometry}.outside.min")
        if outside_min <= 0.0:
            raise AuditError(f"native result {geometry} outside clearance is not positive: {outside_min}")
        plastic_min = finite_number(nested(plastic, "native_chord_cm", "min"), f"{geometry}.plastic.min")
        plastic_error = finite_number(
            nested(plastic, "absolute_closure_error_cm", "max"), f"{geometry}.plastic.error.max"
        )
        if plastic_min <= 0.0 or plastic_error > CHORD_CLOSURE_TOLERANCE_CM:
            raise AuditError(
                f"native result {geometry} plastic closure failed: min={plastic_min}, error={plastic_error}"
            )
        bpe = nested(node, "bpe")
        equal(f"{geometry}.bpe_probe_queries", bpe.get("probe_queries"), EXPECTED_ROWS * 5)
        equal(f"{geometry}.bpe_probe_passes", bpe.get("probe_passes"), EXPECTED_ROWS * 5)
        if geometry == "S3d_O8":
            equal(f"{geometry}.bpe_positive", bpe.get("positive_chord_passes"), EXPECTED_ROWS)
            equal(f"{geometry}.bpe_full", bpe.get("full_chord_passes"), EXPECTED_ROWS)
            bpe_min = finite_number(nested(bpe, "native_chord_cm", "min"), "S3d_O8.bpe.min")
            bpe_error = finite_number(
                nested(bpe, "absolute_closure_error_cm", "max"), "S3d_O8.bpe.error.max"
            )
            if bpe_min <= 0.0 or bpe_error > CHORD_CLOSURE_TOLERANCE_CM:
                raise AuditError(f"native S3d-O8 full BPE closure failed: {bpe_min}, {bpe_error}")
        else:
            equal(f"{geometry}.bpe_zero", bpe.get("zero_chord_passes"), EXPECTED_ROWS)
            bpe_max = finite_number(nested(bpe, "native_chord_cm", "max"), "SE3.bpe.max")
            if abs(bpe_max) > BPE_ZERO_TOLERANCE_CM:
                raise AuditError(f"native SE3 BPE chord is not zero: {bpe_max}")
            port = nested(node, "focused_port")
            equal("SE3.port_clearance_passes", port.get("positive_clearance_passes"), EXPECTED_ROWS)
            clearance_min = finite_number(nested(port, "clearance_cm", "min"), "SE3.port.clearance.min")
            if clearance_min <= 0.0:
                raise AuditError(f"native SE3 aperture clearance is not positive: {clearance_min}")
    return checks


def build_transport_gate(final: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "PASS",
        "transport_scope": "FULL_ENVELOPE_SE3_ONLY",
        "scope_override_authority": str(
            PACKAGE / "audit/user_scope_override_no_s3d_rerun_20260815.json"
        ),
        "generated_utc": utc_now(),
        "transport_launched": False,
        "authority": {
            "path": str(NAVIGATION_OUTPUT),
            "sha256": sha256_file(NAVIGATION_OUTPUT),
            "status": final["status"],
        },
        "paired_bank_sha256": EXPECTED_BANK_SHA256,
        "paired_bank_rows": EXPECTED_ROWS,
        "shared_seed": EXPECTED_SEED,
        # The paired navigator evidence remains useful for proving that the
        # injection plane is outside both frozen envelopes.  The user scope,
        # however, explicitly forbids any fresh S3d transport: only SE3 is a
        # launch authority here.
        "permitted_signal_jobs": [JOBS["SE3"]],
        "excluded_signal_jobs": {
            JOBS["S3d_O8"]: (
                "USER_SCOPE_20260815__NO_S3D_RERUN__"
                "FROZEN_S3D_AUTHORITIES_ONLY"
            )
        },
        "evidence": {
            "same_plane_and_byte_identical_bank": True,
            "all_injection_points_outside_both_envelopes": True,
            "S3d_O8_observed_order": "PLASTIC_THEN_BPE",
            "S3d_O8_plastic_continuous_positive_full_chord": True,
            "S3d_O8_BPE_complete_positive_full_chord": True,
            "SE3_observed_order": "PLASTIC_THEN_BPE_PORT",
            "SE3_plastic_continuous_positive_full_chord": True,
            "SE3_BPE_port_zero_chord": True,
        },
    }


def run_native(
    preflight: dict[str, Any], megalib: Path, root_binary: Path, timeout: float
) -> int:
    canary = preflight["gamma_production_canary"]
    if canary["state"] != "PASS":
        raise AuditError(
            "native --run refused: production gamma canary canonical PASS receipt "
            f"is required; current state={canary['state']}"
        )

    if NAVIGATION_OUTPUT.is_file():
        existing = load_json(NAVIGATION_OUTPUT, "existing navigation authority")
        if existing.get("status") != "PASS":
            raise AuditError("existing authoritative navigation audit is not PASS")
        if nested(existing, "paired_bank_integrity", "shared_sha256") != EXPECTED_BANK_SHA256:
            raise AuditError("existing navigation authority is bound to a different bank")
        if not TRANSPORT_GATE_OUTPUT.is_file():
            atomic_json(TRANSPORT_GATE_OUTPUT, build_transport_gate(existing))
        print(json.dumps({"status": "SKIP__EXISTING_PASS", "output": str(NAVIGATION_OUTPUT)}, indent=2))
        return 0

    static_jobs = load_json(STATIC_AUDIT, "static audit")["pair"]["jobs"]
    setup_by_geometry = {
        str(row["geometry"]): Path(str(row["setup_path"])).resolve() for row in static_jobs
    }
    root = root_binary.expanduser().resolve()
    megalib_root = megalib.expanduser().resolve()
    env = os.environ.copy()
    rootsys = root.parents[1]
    env["MEGALIB"] = str(megalib_root)
    env["ROOTSYS"] = str(rootsys)
    prepend_env(env, "PATH", [megalib_root / "bin", rootsys / "bin"])
    prepend_env(env, "LD_LIBRARY_PATH", [megalib_root / "lib", rootsys / "lib"])
    prepend_env(env, "ROOT_INCLUDE_PATH", [megalib_root / "include"])

    started_utc = utc_now()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="paired_full_envelope_navigation_") as temp:
        temporary = Path(temp)
        raw_output = temporary / "native.json"
        build_dir = temporary / "aclic"
        build_dir.mkdir()
        macro_call = (
            f"{MACRO}+({cpp_string(str(setup_by_geometry['S3d_O8']))},"
            f"{cpp_string(str(EVENTLISTS['S3d_O8'].resolve()))},"
            f"{cpp_string(str(setup_by_geometry['SE3']))},"
            f"{cpp_string(str(EVENTLISTS['SE3'].resolve()))},"
            f"{cpp_string(str(raw_output))})"
        )
        command = [
            str(root),
            "-l",
            "-b",
            "-n",
            "-q",
            "-e",
            f"gSystem->SetBuildDir({cpp_string(str(build_dir))}, kTRUE);",
            macro_call,
        ]
        try:
            process = subprocess.run(
                command,
                cwd=MACRO.parent,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            failure = {
                "schema_version": 1,
                "status": "FAIL",
                "generated_utc": utc_now(),
                "transport_launched": False,
                "reason": f"native ROOT audit exceeded {timeout} seconds",
                "stdout_tail": tail_text(exc.stdout),
                "stderr_tail": tail_text(exc.stderr),
            }
            atomic_json(NATIVE_FAILURE_OUTPUT, failure)
            raise AuditError(failure["reason"]) from exc
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        invocation = {
            "engine": "ROOT ACLiC + MEGAlib MDGeometryQuest",
            "command": command,
            "cwd": str(MACRO.parent),
            "returncode": process.returncode,
            "timeout_seconds": timeout,
            "temporary_build_directory": True,
            "transport_launched": False,
            "stdout_sha256": sha256_bytes(stdout.encode("utf-8", errors="replace")),
            "stderr_sha256": sha256_bytes(stderr.encode("utf-8", errors="replace")),
            "stdout_tail": tail_text(stdout),
            "stderr_tail": tail_text(stderr),
        }
        if not raw_output.is_file():
            failure = {
                "schema_version": 1,
                "status": "FAIL",
                "generated_utc": utc_now(),
                "transport_launched": False,
                "reason": "native macro did not produce JSON",
                "driver_invocation": invocation,
            }
            atomic_json(NATIVE_FAILURE_OUTPUT, failure)
            raise AuditError(failure["reason"])
        native = load_json(raw_output, "native macro output")

    try:
        checks = validate_native(native, process.returncode, stdout)
    except AuditError as exc:
        failure = native | {
            "status": "FAIL",
            "generated_utc": utc_now(),
            "transport_launched": False,
            "reason": str(exc),
            "driver_invocation": invocation,
            "paired_bank_integrity": preflight["paired_bank"],
        }
        atomic_json(NATIVE_FAILURE_OUTPUT, failure)
        raise

    final = native | {
        "schema_version": 1,
  "status": "PASS",
        "generated_utc": utc_now(),
        "started_utc": started_utc,
        "elapsed_seconds": time.monotonic() - started,
        "transport_launched": False,
        "sim_policy": "NO_SIM_DISCOVERY_OPEN_OR_HASH",
        "paired_bank_integrity": preflight["paired_bank"],
        "static_preflight": {
            "path": str(PREFLIGHT_OUTPUT),
            "status": preflight["status"],
        },
        "gamma_production_canary": canary,
        "driver_invocation": invocation,
        "driver_validation": {"status": "PASS", "checks": checks},
    }
    atomic_json(NAVIGATION_OUTPUT, final)
    atomic_json(TRANSPORT_GATE_OUTPUT, build_transport_gate(final))
    if NATIVE_FAILURE_OUTPUT.exists():
        # Preserve historical failure evidence; never delete or overwrite it on PASS.
        pass
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(NAVIGATION_OUTPUT),
                "transport_gate": str(TRANSPORT_GATE_OUTPUT),
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="static check only; never invoke ROOT")
    mode.add_argument("--run", action="store_true", help="run native navigator after canary PASS")
    parser.add_argument("--megalib", type=Path, default=DEFAULT_MEGALIB)
    parser.add_argument("--root-binary", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--timeout", type=float, default=3600.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0.0:
        parser.error("--timeout must be a finite positive number of seconds")

    try:
        preflight = collect_preflight(args.megalib, args.root_binary)
        atomic_json(PREFLIGHT_OUTPUT, preflight)
        if args.check:
            print(
                json.dumps(
                    {
                        "status": preflight["status"],
                        "preflight": str(PREFLIGHT_OUTPUT),
                        "gamma_canary_state": preflight["gamma_production_canary"]["state"],
                        "native_run_admission": preflight["native_run_admission"]["status"],
                        "signal_transport_gate": preflight["signal_transport_gate"]["status"],
                        "root_invoked": False,
                    },
                    indent=2,
                )
            )
            return 0
        return run_native(preflight, args.megalib, args.root_binary, args.timeout)
    except (AuditError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
