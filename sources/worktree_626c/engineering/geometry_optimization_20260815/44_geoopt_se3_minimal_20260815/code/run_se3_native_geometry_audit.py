#!/usr/bin/env python3
"""Run and fail-close the native MEGAlib SE3 geometry/navigation audit.

The C++ macro performs every geometry query.  This driver pins the optics
EventList bytes, validates the input contracts, builds the macro in a temporary
directory, and refuses to publish PASS unless every native counter closes.
No particle source or transport executable is invoked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
DEFAULT_SETUP = PACKAGE / "geometry/DEMO2_DR_v3p5_SE3.geo.setup"
DEFAULT_HOLES = PACKAGE / "data/se3_hole_pattern.csv"
DEFAULT_OUTPUT = PACKAGE / "audit/se3_geometry_navigation.json"
DEFAULT_EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/stepwise_maintenance/"
    "step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
DEFAULT_MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")

EXPECTED_EVENTLIST_SHA256 = (
    "ee538d20d818baab94a5c3ebe01392a3ae9f278a231aa5b8938cdf23870f62b5"
)
EXPECTED_EVENT_COUNT = 37194
EXPECTED_PLATES = {
    "MXC_50mK",
    "CP_100mK",
    "Still_0p7K",
    "4K",
    "60K",
}
REQUIRED_HOLE_COLUMNS = {
    "status",
    "plate_key",
    "plate_volume",
    "plate_material",
    "plate_radius_cm",
    "plate_center_z_cm",
    "x_instrument_cm",
    "y_instrument_cm",
    "hole_radius_cm",
    "edge_solid_cm",
    "keepout_clearance_cm",
    "nearest_hole_web_cm",
    "copy_name",
}
EXPECTED_HOLES_PER_PLATE = 48
REQUIRED_SOLID_MARGIN_CM = 0.2


class AuditError(RuntimeError):
    """A fail-closed preflight, invocation, or result-contract error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require_regular_file(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise AuditError(f"{label} does not resolve: {path}: {exc}") from exc
    if not resolved.is_file():
        raise AuditError(f"{label} is not a regular file: {resolved}")
    return resolved


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


def inspect_setup(path: Path) -> dict[str, Any]:
    record = file_record(path)
    text = path.read_text(encoding="utf-8")
    required_lines = {
        "Name DEMO2_DR_v3p5_SE3",
        "Include DEMO2_DR_v3p5_SE3.geo",
        "Include DEMO2_DR_v3p5_SE3.det",
    }
    lines = set(text.splitlines())
    missing = sorted(required_lines - lines)
    if missing:
        raise AuditError(f"setup is not the SE3 entry file; missing exact lines: {missing}")
    authority_stem = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
    if authority_stem in text:
        raise AuditError("setup still contains the S3d-O8 entry stem")
    return record


def inspect_hole_csv(path: Path) -> dict[str, Any]:
    accepted_names: set[str] = set()
    accepted_by_plate: Counter[str] = Counter()
    radii_by_plate: dict[str, float] = {}
    candidate_rows = 0
    skipped_keep_out_rows = 0
    skipped_selection_rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AuditError("hole CSV has no header")
        missing = sorted(REQUIRED_HOLE_COLUMNS - set(reader.fieldnames))
        if missing:
            raise AuditError(f"hole CSV is missing required columns: {missing}")
        for line_number, row in enumerate(reader, start=2):
            candidate_rows += 1
            status = (row.get("status") or "").strip()
            key = (row.get("plate_key") or "").strip()
            copy_name = (row.get("copy_name") or "").strip()
            if status not in {
                "ACCEPTED",
                "SKIPPED_KEEP_OUT",
                "SKIPPED_EQUIVALENT_48_SELECTION",
            }:
                raise AuditError(f"hole CSV line {line_number}: invalid status {status!r}")
            if key not in EXPECTED_PLATES:
                raise AuditError(f"hole CSV line {line_number}: invalid plate_key {key!r}")
            for field in (
                "plate_radius_cm",
                "plate_center_z_cm",
                "x_instrument_cm",
                "y_instrument_cm",
                "hole_radius_cm",
            ):
                try:
                    value = float(row[field])
                except (TypeError, ValueError) as exc:
                    raise AuditError(
                        f"hole CSV line {line_number}: invalid {field}"
                    ) from exc
                if not math.isfinite(value):
                    raise AuditError(
                        f"hole CSV line {line_number}: non-finite {field}"
                    )
            hole_radius = float(row["hole_radius_cm"])
            if hole_radius <= 0:
                raise AuditError(
                    f"hole CSV line {line_number}: hole radius is not positive"
                )
            if status != "ACCEPTED":
                if status == "SKIPPED_KEEP_OUT":
                    skipped_keep_out_rows += 1
                else:
                    skipped_selection_rows += 1
                if copy_name:
                    raise AuditError(
                        f"hole CSV line {line_number}: skipped row has copy_name"
                    )
                continue
            for field in (
                "edge_solid_cm",
                "keepout_clearance_cm",
                "nearest_hole_web_cm",
            ):
                try:
                    clearance = float(row[field])
                except (TypeError, ValueError) as exc:
                    raise AuditError(
                        f"hole CSV line {line_number}: invalid {field}"
                    ) from exc
                if (
                    not math.isfinite(clearance)
                    or clearance < REQUIRED_SOLID_MARGIN_CM - 1.0e-9
                ):
                    raise AuditError(
                        f"hole CSV line {line_number}: {field} violates 0.2 cm"
                    )
            prior_radius = radii_by_plate.setdefault(key, hole_radius)
            if not math.isclose(prior_radius, hole_radius, rel_tol=0.0, abs_tol=1.0e-12):
                raise AuditError(
                    f"hole CSV line {line_number}: non-uniform radius on {key}"
                )
            expected_prefix = f"SE3_HOLE_{key}_"
            suffix = copy_name.removeprefix(expected_prefix)
            if (
                not copy_name.startswith(expected_prefix)
                or len(suffix) != 5
                or not suffix.isdigit()
            ):
                raise AuditError(
                    f"hole CSV line {line_number}: malformed copy_name {copy_name!r}"
                )
            if copy_name in accepted_names:
                raise AuditError(
                    f"hole CSV line {line_number}: duplicate copy_name {copy_name!r}"
                )
            accepted_names.add(copy_name)
            accepted_by_plate[key] += 1
    if candidate_rows == 0 or not accepted_names:
        raise AuditError("hole CSV has no candidates or no accepted holes")
    if set(accepted_by_plate) != EXPECTED_PLATES:
        raise AuditError(
            "hole CSV accepted-hole plate set mismatch: "
            f"{sorted(accepted_by_plate)}"
        )
    if any(count != EXPECTED_HOLES_PER_PLATE for count in accepted_by_plate.values()):
        raise AuditError(
            f"each plate must have exactly 48 holes: {dict(accepted_by_plate)}"
        )
    if len(accepted_names) != EXPECTED_HOLES_PER_PLATE * len(EXPECTED_PLATES):
        raise AuditError(f"accepted equivalent-hole total is {len(accepted_names)}, not 240")
    record = file_record(path)
    record.update(
        {
            "candidate_rows": candidate_rows,
            "accepted_holes": len(accepted_names),
            "skipped_keep_out_rows": skipped_keep_out_rows,
            "skipped_equivalent_selection_rows": skipped_selection_rows,
            "accepted_by_plate": dict(sorted(accepted_by_plate.items())),
            "hole_radius_cm_by_plate": dict(sorted(radii_by_plate.items())),
        }
    )
    return record


def inspect_eventlist(path: Path) -> dict[str, Any]:
    record = file_record(path)
    if record["sha256"] != EXPECTED_EVENTLIST_SHA256:
        raise AuditError(
            "EventList SHA-256 mismatch: "
            f"{record['sha256']} != {EXPECTED_EVENTLIST_SHA256}"
        )
    row_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                row_count += 1
    if row_count != EXPECTED_EVENT_COUNT:
        raise AuditError(
            f"EventList row count {row_count} != {EXPECTED_EVENT_COUNT}"
        )
    record.update(
        {
            "expected_sha256": EXPECTED_EVENTLIST_SHA256,
            "data_rows": row_count,
            "authority_bytes_match": True,
        }
    )
    return record


def cpp_string(value: str) -> str:
    if "\x00" in value or "\n" in value or "\r" in value:
        raise AuditError("a native audit path contains a prohibited control character")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def prepend_env(env: dict[str, str], name: str, values: list[Path]) -> None:
    parts = [str(path) for path in values]
    existing = env.get(name, "")
    if existing:
        parts.append(existing)
    env[name] = os.pathsep.join(parts)


def tail_text(value: str | bytes | None, limit: int = 12000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-limit:]


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def require_equal(
    checks: dict[str, bool], errors: list[str], name: str, actual: Any, expected: Any
) -> None:
    passed = actual == expected
    checks[name] = passed
    if not passed:
        errors.append(f"{name}: got {actual!r}, expected {expected!r}")


def nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise AuditError(f"native JSON missing {'.'.join(keys)}")
        value = value[key]
    return value


def validate_native(
    native: dict[str, Any], hole_record: dict[str, Any], returncode: int
) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    accepted = hole_record["accepted_holes"]
    try:
        require_equal(checks, errors, "root_returncode", returncode, 0)
        require_equal(checks, errors, "native_status", native.get("status"), "PASS")
        require_equal(
            checks, errors, "transport_not_launched", native.get("transport_launched"), False
        )
        require_equal(
            checks,
            errors,
            "geometry_scan_setup_file",
            nested(native, "geometry_load", "scan_setup_file"),
            True,
        )
        require_equal(
            checks,
            errors,
            "cross_section_creation_disabled",
            nested(native, "geometry_load", "allow_cross_section_creation"),
            False,
        )
        require_equal(
            checks,
            errors,
            "accepted_holes",
            nested(native, "hole_navigation", "accepted_holes"),
            accepted,
        )
        require_equal(
            checks,
            errors,
            "hole_probe_queries",
            nested(native, "hole_navigation", "hole_probe_queries"),
            accepted * 3,
        )
        require_equal(
            checks,
            errors,
            "hole_probe_passes",
            nested(native, "hole_navigation", "hole_probe_passes"),
            accepted * 3,
        )
        require_equal(
            checks,
            errors,
            "web_holes_checked",
            nested(native, "hole_navigation", "web_holes_checked"),
            accepted,
        )
        require_equal(
            checks,
            errors,
            "web_passes",
            nested(native, "hole_navigation", "web_passes"),
            accepted,
        )
        require_equal(
            checks,
            errors,
            "web_candidate_queries",
            nested(native, "hole_navigation", "web_candidate_queries"),
            accepted * 2,
        )
        require_equal(
            checks,
            errors,
            "nearest_pair_web_passes",
            nested(native, "hole_navigation", "nearest_pair_web_passes"),
            accepted,
        )
        require_equal(
            checks,
            errors,
            "outer_edge_web_passes",
            nested(native, "hole_navigation", "outer_edge_web_passes"),
            accepted,
        )
        by_plate = nested(native, "hole_navigation", "by_plate")
        require_equal(checks, errors, "native_plate_set", set(by_plate), EXPECTED_PLATES)
        for plate, plate_count in hole_record["accepted_by_plate"].items():
            require_equal(
                checks,
                errors,
                f"{plate}_accepted_holes",
                nested(by_plate, plate, "accepted_holes"),
                plate_count,
            )
            require_equal(
                checks,
                errors,
                f"{plate}_hole_probe_passes",
                nested(by_plate, plate, "hole_probe_passes"),
                plate_count * 3,
            )
            require_equal(
                checks,
                errors,
                f"{plate}_web_passes",
                nested(by_plate, plate, "web_passes"),
                plate_count,
            )
        for field in (
            "parsed_rows",
            "get_path_lengths_calls",
            "input_plane_passes",
            "forward_direction_passes",
            "bpe_zero_passes",
            "plastic_positive_passes",
        ):
            require_equal(
                checks,
                errors,
                field,
                nested(native, "eventlist_navigation", field),
                EXPECTED_EVENT_COUNT,
            )
        require_equal(
            checks,
            errors,
            "analytic_clearance_passes",
            nested(
                native,
                "eventlist_navigation",
                "analytic_aperture",
                "positive_clearance_passes",
            ),
            EXPECTED_EVENT_COUNT,
        )
        bpe_max = nested(
            native, "eventlist_navigation", "bpe_chord_cm", "max"
        )
        bpe_tolerance = nested(
            native, "eventlist_navigation", "bpe_zero_tolerance_cm"
        )
        checks["bpe_max_within_zero_tolerance"] = (
            isinstance(bpe_max, (int, float))
            and math.isfinite(bpe_max)
            and abs(bpe_max) <= bpe_tolerance
        )
        if not checks["bpe_max_within_zero_tolerance"]:
            errors.append(
                f"BPE max chord {bpe_max!r} exceeds zero tolerance {bpe_tolerance!r}"
            )
        plastic_min = nested(
            native, "eventlist_navigation", "plastic_chord_cm", "min"
        )
        plastic_tolerance = nested(
            native, "eventlist_navigation", "plastic_positive_tolerance_cm"
        )
        checks["plastic_min_positive"] = (
            isinstance(plastic_min, (int, float))
            and math.isfinite(plastic_min)
            and plastic_min > plastic_tolerance
        )
        if not checks["plastic_min_positive"]:
            errors.append(
                f"plastic min chord {plastic_min!r} is not > {plastic_tolerance!r}"
            )
        clearance_min = nested(
            native,
            "eventlist_navigation",
            "analytic_aperture",
            "clearance_cm",
            "min",
        )
        checks["analytic_clearance_min_positive"] = (
            isinstance(clearance_min, (int, float))
            and math.isfinite(clearance_min)
            and clearance_min > 0.0
        )
        if not checks["analytic_clearance_min_positive"]:
            errors.append(f"analytic aperture minimum clearance is {clearance_min!r}")
        require_equal(
            checks, errors, "native_failure_count", native.get("failure_count"), 0
        )
    except (AuditError, KeyError, TypeError, ValueError) as exc:
        checks["native_json_contract"] = False
        errors.append(str(exc))
    else:
        checks["native_json_contract"] = True
    return checks, errors


def failure_payload(
    message: str,
    output: Path,
    started_utc: str,
    started_monotonic: float,
    inputs: dict[str, Any] | None = None,
    invocation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "FAIL",
        "transport_launched": False,
        "generated_utc": utc_now(),
        "started_utc": started_utc,
        "elapsed_seconds": time.monotonic() - started_monotonic,
        "output": str(output),
        "input_integrity": inputs or {},
        "driver_invocation": invocation or {},
        "driver_validation": {"status": "FAIL", "errors": [message]},
    }


def run(args: argparse.Namespace) -> int:
    started_utc = utc_now()
    started_monotonic = time.monotonic()
    output = args.output.expanduser().resolve()
    input_records: dict[str, Any] = {}
    invocation: dict[str, Any] = {}
    try:
        setup = require_regular_file(args.setup, "SE3 setup")
        holes = require_regular_file(args.holes, "SE3 hole CSV")
        eventlist = require_regular_file(args.eventlist, "authority EventList")
        macro = require_regular_file(SCRIPT.with_name("se3_native_geometry_audit.C"), "audit macro")
        megalib = args.megalib.expanduser().resolve(strict=True)
        if not megalib.is_dir():
            raise AuditError(f"MEGAlib root is not a directory: {megalib}")
        root_binary = (
            require_regular_file(args.root_binary, "ROOT binary")
            if args.root_binary is not None
            else require_regular_file(
                megalib / "external/root_v6.36.6/bin/root", "ROOT binary"
            )
        )
        if not os.access(root_binary, os.X_OK):
            raise AuditError(f"ROOT binary is not executable: {root_binary}")

        input_records = {
            "setup": inspect_setup(setup),
            "hole_csv": inspect_hole_csv(holes),
            "eventlist": inspect_eventlist(eventlist),
            "native_macro": file_record(macro),
        }

        env = os.environ.copy()
        env["MEGALIB"] = str(megalib)
        rootsys = root_binary.parents[1]
        env["ROOTSYS"] = str(rootsys)
        prepend_env(env, "PATH", [megalib / "bin", rootsys / "bin"])
        prepend_env(env, "LD_LIBRARY_PATH", [megalib / "lib", rootsys / "lib"])
        prepend_env(env, "ROOT_INCLUDE_PATH", [megalib / "include"])

        with tempfile.TemporaryDirectory(prefix="se3_native_geometry_audit_") as temp:
            temp_root = Path(temp)
            raw_output = temp_root / "native.json"
            build_dir = temp_root / "aclic"
            build_dir.mkdir()
            macro_call = (
                f"{macro}+({cpp_string(str(setup))},{cpp_string(str(holes))},"
                f"{cpp_string(str(eventlist))},{cpp_string(str(raw_output))})"
            )
            build_expression = (
                f"gSystem->SetBuildDir({cpp_string(str(build_dir))}, kTRUE);"
            )
            command = [
                str(root_binary),
                "-l",
                "-b",
                "-n",
                "-q",
                "-e",
                build_expression,
                macro_call,
            ]
            invocation = {
                "engine": "ROOT ACLiC + MEGAlib MDGeometryQuest",
                "command": command,
                "cwd": str(macro.parent),
                "timeout_seconds": args.timeout,
                "temporary_build_directory": True,
                "transport_launched": False,
            }
            try:
                process = subprocess.run(
                    command,
                    cwd=macro.parent,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                invocation.update(
                    {
                        "timed_out": True,
                        "stdout_tail": tail_text(exc.stdout),
                        "stderr_tail": tail_text(exc.stderr),
                    }
                )
                raise AuditError(
                    f"native ROOT audit exceeded {args.timeout} seconds"
                ) from exc

            stdout = process.stdout or ""
            stderr = process.stderr or ""
            invocation.update(
                {
                    "returncode": process.returncode,
                    "timed_out": False,
                    "stdout_sha256": text_sha256(stdout),
                    "stderr_sha256": text_sha256(stderr),
                    "stdout_tail": tail_text(stdout),
                    "stderr_tail": tail_text(stderr),
                }
            )
            if not raw_output.is_file():
                raise AuditError(
                    "native macro did not produce JSON; "
                    f"ROOT return code was {process.returncode}"
                )
            try:
                native = json.loads(raw_output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise AuditError(f"native macro JSON is unreadable: {exc}") from exc
            if not isinstance(native, dict):
                raise AuditError("native macro JSON root is not an object")

        checks, errors = validate_native(
            native, input_records["hole_csv"], process.returncode
        )
        negative_length_marker = "Warning: Negative length in volume:"
        checks["no_negative_get_path_lengths_warning"] = (
            negative_length_marker not in stdout
        )
        if not checks["no_negative_get_path_lengths_warning"]:
            errors.append(
                "MEGAlib GetPathLengths reported a negative daughter-subtracted "
                "length, indicating an overlap along at least one audited ray"
            )
        final = native
        final.update(
            {
                "generated_utc": utc_now(),
                "started_utc": started_utc,
                "elapsed_seconds": time.monotonic() - started_monotonic,
                "output": str(output),
                "input_integrity": input_records,
                "driver_invocation": invocation,
                "driver_validation": {
                    "status": "PASS" if not errors and all(checks.values()) else "FAIL",
                    "checks": checks,
                    "errors": errors,
                },
            }
        )
        final["status"] = (
            "PASS"
            if native.get("status") == "PASS"
            and not errors
            and checks
            and all(checks.values())
            else "FAIL"
        )
        atomic_json(output, final)
        print(json.dumps({"status": final["status"], "output": str(output)}, indent=2))
        return 0 if final["status"] == "PASS" else 1
    except (AuditError, OSError, ValueError) as exc:
        final = failure_payload(
            str(exc), output, started_utc, started_monotonic, input_records, invocation
        )
        atomic_json(output, final)
        print(json.dumps({"status": "FAIL", "output": str(output), "error": str(exc)}, indent=2))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--holes", type=Path, default=DEFAULT_HOLES)
    parser.add_argument("--eventlist", type=Path, default=DEFAULT_EVENTLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--megalib", type=Path, default=DEFAULT_MEGALIB)
    parser.add_argument("--root-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=3600.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number of seconds")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
