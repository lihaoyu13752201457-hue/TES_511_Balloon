#!/usr/bin/env python3
"""Run a zero-transport overlap check for the SH3 small-aperture variant."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
HARNESS = SCRIPT.parent / "_shared_overlap_harness.py"

spec = importlib.util.spec_from_file_location("sh3_smallap_overlap_harness", HARNESS)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load vendored overlap harness: {HARNESS}")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

runner.PACKAGE = PACKAGE
runner.GEOMETRY = PACKAGE / "geometry"
runner.AUDIT = PACKAGE / "audit"
runner.DATA = PACKAGE / "data"
runner.SETUP = runner.GEOMETRY / "SH3_Assembly_OptV3.geo.setup"
runner.GEO = runner.GEOMETRY / "SH3_Assembly_OptV3.geo"
runner.DET = runner.GEOMETRY / "SH3_Assembly_OptV3.det"
runner.MATERIALS = runner.GEOMETRY / "Materials_SH3_Assembly_OptV3.geo"
runner.MANIFEST = runner.DATA / "smallap_sg3grid_manifest.json"
runner.STATIC = runner.AUDIT / "smallap_sg3grid_static_validation.json"
runner.OUTPUT = runner.AUDIT / "smallap_sg3grid_overlap_validation.json"
runner.LOG = runner.AUDIT / "smallap_sg3grid_overlap_cosima.log"

BUILD_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_BUILT"
STATIC_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_STATIC"
OVERLAP_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_OVERLAP_NO_TRANSPORT"
COMPONENT = "SH3_Chimney_DR_Assembly_OptV3_SmallAp_SG3Grid"


def verify_authority() -> dict[str, dict[str, object]]:
    core = (runner.SETUP, runner.GEO, runner.DET, runner.MATERIALS)
    required = core + (runner.MANIFEST, runner.STATIC, runner.COSIMA)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing small-aperture overlap prerequisite(s): {missing}")
    manifest = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    static = json.loads(runner.STATIC.read_text(encoding="utf-8"))
    if manifest.get("status") != BUILD_STATUS:
        raise RuntimeError("small-aperture manifest is not PASS")
    if static.get("status") != STATIC_STATUS:
        raise RuntimeError("small-aperture static validation is not PASS")
    records: dict[str, dict[str, object]] = {}
    stale: list[str] = []
    for path in core:
        current = runner.sha256(path)
        expected = manifest.get("outputs", {}).get(path.name, {}).get("sha256")
        if current != expected:
            stale.append(path.name)
        records[path.name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": current,
            "manifest_sha256": expected,
        }
    if stale:
        raise RuntimeError(f"small-aperture manifest stale for: {stale}")
    return records


runner.verify_authority = verify_authority


def main() -> int:
    result = runner.main()
    report = json.loads(runner.OUTPUT.read_text(encoding="utf-8"))
    report["component_identity"] = COMPONENT
    if report.get("status") == "PASS__SH3_ASSEMBLY_OVERLAP_NO_TRANSPORT":
        report["status"] = OVERLAP_STATUS
    runner.atomic_json(runner.OUTPUT, report)
    print(json.dumps({"status": report["status"], "output": str(runner.OUTPUT)}, indent=2))
    return 0 if report["status"] == OVERLAP_STATUS else result or 1


if __name__ == "__main__":
    raise SystemExit(main())
