#!/usr/bin/env python3
"""Build v3p5 center-finger full-sphere source cards.

The base atmospheric source cards define the EXPACS/PARMA spectra and
zenith-frame angular bins. This script only migrates the geometry authority and
records the detector pointing/far-field policy for the larger tilted v3p5 mass
model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20"
GEOM_DIR = ROOT / "outputs" / "geometry" / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEOM_VALIDATION = GEOM_DIR / "geometry_proxy_validation.json"
GEOM_SETUP = GEOM_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
OUT_DIR = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
MANIFEST = OUT_DIR / "source_migration_manifest.json"

GEOMETRY_LINE_RE = re.compile(r"^Geometry\s+.+$", re.MULTILINE)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if not BASE_SOURCE_DIR.exists():
        raise SystemExit(f"Missing base source directory: {BASE_SOURCE_DIR}")
    if not GEOM_SETUP.exists():
        raise SystemExit(f"Missing generated geometry setup: {GEOM_SETUP}")
    if not GEOM_VALIDATION.exists():
        raise SystemExit(f"Missing geometry validation: {GEOM_VALIDATION}")

    geom_validation = load_json(GEOM_VALIDATION)
    extents = geom_validation.get("geometry_extents", {})
    radius = float(extents.get("recommended_farfield_radius_cm", 50.0))
    instrument_frame = extents.get("instrument_frame", {})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_rows: list[dict[str, Any]] = []
    geometry_line = f"Geometry {rel(GEOM_SETUP)}"

    for src in sorted(BASE_SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = src.read_text(encoding="utf-8", errors="replace")
        if not GEOMETRY_LINE_RE.search(text):
            raise SystemExit(f"Source card has no Geometry line: {src}")
        header = "\n".join(
            [
                "# v3p5 center-finger migrated source card",
                f"# base_source={rel(src)}",
                f"# geometry_setup={rel(GEOM_SETUP)}",
                "# megalib_length_unit=cm",
                f"# farfield_radius_cm={radius:.9g}",
                "# pointing_policy=InstrumentFrame rotated 0 45 0 deg; local side-window -x looks 45 deg upward in global zenith frame",
                "",
            ]
        )
        migrated = GEOMETRY_LINE_RE.sub(geometry_line, text, count=1)
        out = OUT_DIR / src.name
        out.write_text(header + migrated, encoding="utf-8")
        source_rows.append(
            {
                "source": rel(out),
                "base_source": rel(src),
                "geometry_setup": rel(GEOM_SETUP),
            }
        )

    manifest = {
        "status": "PASS",
        "source_dir": rel(OUT_DIR),
        "base_source_dir": rel(BASE_SOURCE_DIR),
        "geometry_validation": rel(GEOM_VALIDATION),
        "geometry_setup": rel(GEOM_SETUP),
        "geometry_status": geom_validation.get("status"),
        "farfield_radius_cm": radius,
        "farfield_area_cm2": 3.141592653589793 * radius * radius,
        "geometry_extents": extents,
        "pointing_policy": {
            "megalib_length_unit": "cm",
            "zenith_frame": "FarFieldAreaSource theta/phi bins remain in global zenith coordinates",
            "implementation": "whole detector mass model is tilted through InstrumentFrame.Rotation 0 45 0",
            "side_window_local_look_axis": instrument_frame.get("side_window_local_look_axis", "-x"),
            "side_window_global_look_vector": instrument_frame.get("side_window_global_look_vector"),
            "side_window_look_elevation_deg": instrument_frame.get("side_window_look_elevation_deg"),
            "incoming_photon_global_axis": instrument_frame.get("incoming_photon_global_axis"),
        },
        "sources": source_rows,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "sources": len(source_rows), "out_dir": rel(OUT_DIR), "farfield_radius_cm": radius}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
