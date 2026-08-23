#!/usr/bin/env python3
"""Export native zero-transport WRL for SH3 assembly OptV3."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
SH3 = PACKAGE.parent
V1_EXPORTER = SH3 / "assembly/code/export_sh3_assembly_wrl.py"

spec = importlib.util.spec_from_file_location("sh3_assembly_v1_wrl", V1_EXPORTER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load shared WRL exporter: {V1_EXPORTER}")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

exporter.PACKAGE = PACKAGE
exporter.GEOMETRY = PACKAGE / "geometry"
exporter.AUDIT = PACKAGE / "audit"
exporter.DATA = PACKAGE / "data"
exporter.FIGURES = PACKAGE / "figures"
exporter.SETUP = exporter.GEOMETRY / "SH3_Assembly_OptV3.geo.setup"
exporter.GEO = exporter.GEOMETRY / "SH3_Assembly_OptV3.geo"
exporter.DET = exporter.GEOMETRY / "SH3_Assembly_OptV3.det"
exporter.MATERIALS = exporter.GEOMETRY / "Materials_SH3_Assembly_OptV3.geo"
exporter.MANIFEST = exporter.DATA / "assembly_opt_v3_manifest.json"
exporter.STATIC = exporter.AUDIT / "assembly_opt_v3_static_validation.json"
exporter.OVERLAP = exporter.AUDIT / "assembly_opt_v3_overlap_validation.json"
exporter.OUTPUT = exporter.FIGURES / "SH3_Chimney_DR_Assembly_OptV3.wrl"
exporter.LOG = exporter.AUDIT / "assembly_opt_v3_wrl_export_cosima.log"
exporter.REPORT = exporter.AUDIT / "assembly_opt_v3_wrl_export_validation.json"


def verify_authority() -> dict[str, dict[str, object]]:
    core = (exporter.SETUP, exporter.GEO, exporter.DET, exporter.MATERIALS)
    required = core + (
        exporter.MANIFEST,
        exporter.STATIC,
        exporter.OVERLAP,
        exporter.COSIMA,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing OptV3 WRL prerequisite(s): {missing}")
    manifest = json.loads(exporter.MANIFEST.read_text(encoding="utf-8"))
    static = json.loads(exporter.STATIC.read_text(encoding="utf-8"))
    overlap = json.loads(exporter.OVERLAP.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_BUILT":
        raise RuntimeError("OptV3 manifest is not PASS")
    if static.get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_STATIC":
        raise RuntimeError("OptV3 static validation is not PASS")
    if overlap.get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_OVERLAP_NO_TRANSPORT":
        raise RuntimeError("OptV3 overlap validation is not PASS")
    records: dict[str, dict[str, object]] = {}
    stale: list[str] = []
    for path in core:
        current = exporter.sha256(path)
        expected = manifest.get("outputs", {}).get(path.name, {}).get("sha256")
        overlap_hash = overlap.get("source_authority", {}).get(path.name, {}).get("sha256")
        if current != expected or current != overlap_hash:
            stale.append(path.name)
        records[path.name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": current,
            "manifest_sha256": expected,
            "overlap_sha256": overlap_hash,
        }
    if stale:
        raise RuntimeError(f"OptV3 authority stale for: {stale}")
    return records


exporter.verify_authority = verify_authority


def main() -> int:
    result = exporter.main()
    report = json.loads(exporter.REPORT.read_text(encoding="utf-8"))
    report["component_identity"] = "SH3_Chimney_DR_Assembly_OptV3"
    if report.get("status") == "PASS__SH3_ASSEMBLY_NATIVE_WRL_NO_TRANSPORT":
        report["status"] = "PASS__SH3_ASSEMBLY_OPT_V3_NATIVE_WRL_NO_TRANSPORT"
    exporter.atomic_json(exporter.REPORT, report)
    print(json.dumps({"status": report["status"], "report": str(exporter.REPORT)}, indent=2))
    return 0 if report["status"] == "PASS__SH3_ASSEMBLY_OPT_V3_NATIVE_WRL_NO_TRANSPORT" else result or 1


if __name__ == "__main__":
    raise SystemExit(main())
