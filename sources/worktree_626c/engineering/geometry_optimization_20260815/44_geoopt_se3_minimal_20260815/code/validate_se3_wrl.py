#!/usr/bin/env python3
"""Load/convert the native SE3 WRL with an independent VRML/X3D parser."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_se3_mesh_products import ROOT, atomic_json, file_record


DEFAULT_WRL = ROOT / "geometry" / "se3_native_geant4_full.wrl"
DEFAULT_MANIFEST = ROOT / "data" / "se3_geometry_volume_manifest.csv"
DEFAULT_MESH_AUDIT = ROOT / "audit" / "se3_mesh_validation.json"
DEFAULT_AUDIT = ROOT / "audit" / "se3_wrl_parser_validation.json"
EXPECTED_NONVACUUM = 3094
EXPECTED_VISIBLE_HOLES = 240
EXPECTED_WRL_SOLIDS = EXPECTED_NONVACUUM + EXPECTED_VISIBLE_HOLES


class WrlValidationError(RuntimeError):
    pass


def balanced(text: str, opening: str, closing: str) -> bool:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_string


def count_manifest(path: Path) -> tuple[int, int, int]:
    import csv

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    nonvacuum = sum(row.get("is_nonvacuum", "").lower() == "true" for row in rows)
    holes = sum(row.get("is_plate_hole", "").lower() == "true" for row in rows)
    return len(rows), nonvacuum, holes


def validate(args: argparse.Namespace) -> dict[str, Any]:
    wrl = Path(args.wrl).resolve()
    manifest = Path(args.manifest).resolve()
    mesh_audit_path = Path(args.mesh_audit).resolve()
    audit_path = Path(args.audit).resolve()
    for path in (wrl, manifest, mesh_audit_path):
        if not path.is_file():
            raise WrlValidationError(f"Required input is missing: {path}")
    executable = shutil.which(args.parser)
    if executable is None:
        raise WrlValidationError(f"Independent parser is unavailable: {args.parser}")

    raw_text = wrl.read_text(encoding="utf-8")
    mesh_audit = json.loads(mesh_audit_path.read_text(encoding="utf-8"))
    manifest_total, manifest_nonvacuum, manifest_holes = count_manifest(manifest)
    solid_count = len(re.findall(r"(?m)^#---------- SOLID:\s+", raw_text))
    version_process = subprocess.run(
        [executable, "--version"], text=True, capture_output=True, timeout=30, check=False
    )
    parser_version = (version_process.stdout or version_process.stderr).strip().splitlines()[0]

    with tempfile.TemporaryDirectory(prefix="se3-wrl-parsecheck-") as temporary_dir:
        converted = Path(temporary_dir) / "se3_parsecheck.x3dv"
        with converted.open("wb") as output_handle:
            process = subprocess.run(
                [executable, "--write", "--write-encoding=classic", str(wrl)],
                stdout=output_handle,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
                check=False,
            )
        converted_size = converted.stat().st_size if converted.exists() else 0
        converted_header = ""
        converted_preamble = ""
        if converted_size:
            with converted.open("r", encoding="utf-8", errors="replace") as handle:
                converted_probe = handle.read(65536)
            converted_preamble = "\n".join(converted_probe.splitlines()[:8])
            header_match = re.search(r"(?m)^#(?:X3D|VRML)[^\r\n]*", converted_probe)
            if header_match:
                converted_header = header_match.group(0).strip()
        stderr_text = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""

    checks = {
        "vrml_header_v2_utf8": raw_text.startswith("#VRML V2.0 utf8\n"),
        "balanced_braces": balanced(raw_text, "{", "}"),
        "balanced_brackets": balanced(raw_text, "[", "]"),
        "ends_with_geant4_marker": raw_text.rstrip().endswith("#End of file."),
        "solid_count_matches_manifest": solid_count == manifest_total,
        "wrl_solid_count_3334": solid_count == EXPECTED_WRL_SOLIDS,
        "manifest_row_count_3334": manifest_total == EXPECTED_WRL_SOLIDS,
        "manifest_nonvacuum_3094": manifest_nonvacuum == EXPECTED_NONVACUUM,
        "manifest_visible_holes_240": manifest_holes == EXPECTED_VISIBLE_HOLES,
        "mesh_audit_pass": mesh_audit.get("status") == "PASS",
        "mesh_audit_counts_match_3334": (
            mesh_audit.get("counts", {}).get("wrl_solids") == EXPECTED_WRL_SOLIDS
            and mesh_audit.get("counts", {}).get("nonvacuum_solids") == EXPECTED_NONVACUUM
            and mesh_audit.get("counts", {}).get("visible_vacuum_holes") == EXPECTED_VISIBLE_HOLES
        ),
        "mesh_audit_world_unit_mm": (
            mesh_audit.get("coordinate_systems", {}).get("native_wrl", {}).get("length_unit") == "mm"
        ),
        "native_geant4_camera_unmodified": (
            "#---------- CAMERA" in raw_text[:3000]
            and "#---------- CAMERA / SE3 FLIGHT ORIENTATION" not in raw_text[:3000]
            and bool(re.search(r"position\s+0\s+0\s+[0-9.eE+-]+", raw_text[:3000]))
        ),
        "independent_parser_version_ok": version_process.returncode == 0 and bool(parser_version),
        "independent_load_convert_exit_zero": process.returncode == 0,
        "independent_conversion_nonempty": converted_size > 1000,
        "independent_conversion_header": converted_header.startswith(("#X3D", "#VRML")),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema_version": "se3_wrl_parser_validation_v1",
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_identity": "SE3",
        "parser": f"{Path(executable).name} {parser_version}",
        "operation": "load and convert with --write --write-encoding=classic",
        "exit_code": process.returncode,
        "parser_stderr_tail": stderr_text[-4000:],
        "converted_header": converted_header,
        "converted_preamble": converted_preamble,
        "converted_size_bytes": converted_size,
        "converted_parsecheck_retained": False,
        "inputs": {
            "native_wrl": file_record(wrl),
            "manifest": file_record(manifest),
            "mesh_audit": file_record(mesh_audit_path),
            "validator": file_record(Path(__file__).resolve()),
        },
        "counts": {
            "wrl_solids": solid_count,
            "manifest_rows": manifest_total,
            "manifest_nonvacuum": manifest_nonvacuum,
            "manifest_visible_holes": manifest_holes,
        },
        "coordinate_unit": "Geant4 world mm",
        "native_camera_note": (
            "Geant4 10.02 VRML2FILE hard-codes the raw camera on world +Z and ignores viewer "
            "direction commands. The native file is unmodified; audited figures use world -Y "
            "with world +Z screen-up."
        ),
        "checks": checks,
    }
    atomic_json(audit_path, result)
    if status != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise WrlValidationError(f"Independent SE3 WRL validation failed: {failed}; see {audit_path}")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--wrl", default=str(DEFAULT_WRL))
    result.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    result.add_argument("--mesh-audit", default=str(DEFAULT_MESH_AUDIT))
    result.add_argument("--audit", default=str(DEFAULT_AUDIT))
    result.add_argument("--parser", default="view3dscene")
    result.add_argument("--timeout", type=int, default=600)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        result = validate(args)
    except (WrlValidationError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(
        f"PASS: independent parser loaded {result['counts']['wrl_solids']} WRL solids "
        f"({result['counts']['manifest_visible_holes']} visible Vacuum holes)"
    )
    print(f"audit: {Path(args.audit).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
