#!/usr/bin/env python3
"""Export the SH3 OptV3 effective-small-aperture geometry as native WRL.

This is a construction/visualization run only.  The shared harness exits at
the Geant4 idle prompt without starting a particle beam.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
HARNESS = SCRIPT.with_name("_shared_wrl_harness.py")

spec = importlib.util.spec_from_file_location("sh3_smallap_wrl_harness", HARNESS)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load vendored WRL harness: {HARNESS}")
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
exporter.MANIFEST = exporter.DATA / "smallap_sg3grid_manifest.json"
exporter.STATIC = exporter.AUDIT / "smallap_sg3grid_static_validation.json"
exporter.OVERLAP = exporter.AUDIT / "smallap_sg3grid_overlap_validation.json"
exporter.OUTPUT = (
    exporter.FIGURES / "SH3_Chimney_DR_Assembly_OptV3_SmallAp_SG3Grid.wrl"
)
exporter.LOG = exporter.AUDIT / "smallap_sg3grid_wrl_export_cosima.log"
exporter.REPORT = exporter.AUDIT / "smallap_sg3grid_wrl_export_validation.json"

BUILD_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_BUILT"
STATIC_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_STATIC"
OVERLAP_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_OVERLAP_NO_TRANSPORT"
WRL_STATUS = "PASS__SH3_OPTV3_SMALLAP_SG3GRID_NATIVE_WRL_NO_TRANSPORT"


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
        raise RuntimeError(f"missing small-aperture WRL prerequisite(s): {missing}")

    manifest = json.loads(exporter.MANIFEST.read_text(encoding="utf-8"))
    static = json.loads(exporter.STATIC.read_text(encoding="utf-8"))
    overlap = json.loads(exporter.OVERLAP.read_text(encoding="utf-8"))
    if manifest.get("status") != BUILD_STATUS:
        raise RuntimeError("small-aperture build manifest is not PASS")
    if static.get("status") != STATIC_STATUS:
        raise RuntimeError("small-aperture static validation is not PASS")
    if overlap.get("status") != OVERLAP_STATUS:
        raise RuntimeError("small-aperture overlap validation is not PASS")

    records: dict[str, dict[str, object]] = {}
    stale: list[str] = []
    for path in core:
        current = exporter.sha256(path)
        expected = manifest.get("outputs", {}).get(path.name, {}).get("sha256")
        overlap_hash = overlap.get("source_authority", {}).get(path.name, {}).get(
            "sha256"
        )
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
        raise RuntimeError(f"small-aperture authority stale for: {stale}")
    return records


exporter.verify_authority = verify_authority


def main() -> int:
    result = exporter.main()
    report = json.loads(exporter.REPORT.read_text(encoding="utf-8"))
    report["component_identity"] = (
        "SH3_Chimney_DR_Assembly_OptV3_SmallAp_SG3Grid"
    )
    if report.get("status") == "PASS__SH3_ASSEMBLY_NATIVE_WRL_NO_TRANSPORT":
        wrl = exporter.OUTPUT.read_bytes()
        grid_solids = wrl.count(
            b"#---------- SOLID: W_Multihole_Collimator_"
        )
        mask_solids = wrl.count(b"#---------- SOLID: W_SmallAperture_Mask_")
        report.setdefault("checks", {})["exact_624_sg3_grid_solids"] = (
            grid_solids == 624
        )
        report["checks"]["exact_four_solid_w_mask_solids"] = mask_solids == 4
        report["checks"]["expected_total_shape_count_3324"] = (
            report.get("output", {}).get("shape_node_count") == 3324
            and report.get("output", {}).get("indexed_face_set_count") == 3324
        )
        report["output"]["grid_solid_count"] = grid_solids
        report["output"]["mask_solid_count"] = mask_solids
        if all(report["checks"].values()):
            report["status"] = WRL_STATUS
        else:
            report["status"] = "FAIL"
    exporter.atomic_json(exporter.REPORT, report)
    print(
        json.dumps(
            {"status": report["status"], "report": str(exporter.REPORT)},
            indent=2,
        )
    )
    return 0 if report["status"] == WRL_STATUS else result or 1


if __name__ == "__main__":
    raise SystemExit(main())
