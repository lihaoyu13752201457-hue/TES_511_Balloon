#!/usr/bin/env python3
"""Validate that the SG3B 60 cm surface encloses OptV3 material."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[2]
WRL = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/figures/SH3_Chimney_DR_Assembly_OptV3.wrl"
GEO = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.geo"
SETUP = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup"
CENTER_CM = (5.0, 0.0, 9.0)
RADIUS_CM = 60.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PACKAGE / "audit/source_surface_60cm_validation.json")
    args = parser.parse_args()
    points: list[tuple[float, float, float]] = []
    inside = False
    triple = re.compile(r"\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+),?\s*$")
    with WRL.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "point [" in line:
                inside = True
                continue
            if inside and "]" in line:
                inside = False
                continue
            if inside and (match := triple.match(line)):
                points.append(tuple(float(value) / 10.0 for value in match.groups()))
    if not points:
        raise RuntimeError("native WRL contains no vertices")
    distances = [math.dist(point, CENTER_CM) for point in points]
    farthest_index = max(range(len(points)), key=distances.__getitem__)
    hidden = sorted({
        line.split(".Visibility", 1)[0]
        for line in GEO.read_text(encoding="utf-8").splitlines()
        if line.endswith(".Visibility 0")
    })
    allowed_hidden_prefixes = ("WorldVolume", "InstrumentFrame", "TES_L", "TP_L")
    unexpected_hidden = [name for name in hidden if not name.startswith(allowed_hidden_prefixes)]
    setup_text = SETUP.read_text(encoding="utf-8")
    maximum = distances[farthest_index]
    checks = {
        "setup_has_exact_sg3b_surface": setup_text.count("SurroundingSphere 60 5 0 9 60") == 1,
        "native_wrl_has_vertices": bool(points),
        "visible_material_vertices_inside_surface": maximum < RADIUS_CM,
        "hidden_volume_classes_are_containers_or_tes": not unexpected_hidden,
        "positive_radial_margin": RADIUS_CM - maximum > 0,
    }
    receipt = {
        "schema_version": 1,
        "status": "PASS__SH3_OPTV3_SG3B_60CM_SURFACE_ENCLOSES_MATERIAL" if all(checks.values()) else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "surface": {"radius_cm": RADIUS_CM, "center_cm": CENTER_CM, "contract": "60 5 0 9 60"},
        "native_wrl": {
            "path": str(WRL), "sha256": sha256(WRL), "vertex_count": len(points),
            "maximum_radius_cm": maximum, "radial_margin_cm": RADIUS_CM - maximum,
            "farthest_vertex_cm": points[farthest_index],
            "axis_bounds_cm": {
                axis: [min(point[index] for point in points), max(point[index] for point in points)]
                for index, axis in enumerate(("x", "y", "z"))
            },
        },
        "hidden_geometry": {"names": hidden, "unexpected": unexpected_hidden},
        "setup": {"path": str(SETUP), "sha256": sha256(SETUP)},
        "scope_note": "World/InstrumentFrame are vacuum containers; hidden TES hierarchy lies within the visible cryostat/BGO envelope.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
