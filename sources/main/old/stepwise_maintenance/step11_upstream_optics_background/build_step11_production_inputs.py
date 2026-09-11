#!/usr/bin/env python3
"""Build production source inputs for upstream Laue hardware background.

The smoke builder creates the enlarged detector-plus-lens geometry.  This
script turns that geometry into a canonical per-particle source directory that
the existing full-statistics EXPACS/PARMA runner can consume.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STEP = ROOT / "stepwise_maintenance" / "step11_upstream_optics_background"
SMOKE_META = STEP / "smoke_geometry" / "step11_smoke_input_summary.json"
BASE_SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
OUT_DIR = STEP / "production_sources_r1060"

PARTICLES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def patch_source(text: str, geometry_setup: str, radius_cm: float) -> str:
    text = text.replace(
        "Geometry outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
        "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
        f"Geometry {geometry_setup}",
    )
    text = re.sub(r"# farfield_radius_cm=[0-9.eE+-]+", f"# farfield_radius_cm={radius_cm:g}", text)
    text = text.replace(
        "# v3p5 center-finger migrated source card",
        "# Step11 upstream Laue-lens hardware production source card",
    )
    return text


def main() -> None:
    if not SMOKE_META.exists():
        raise SystemExit(
            f"Missing {rel(SMOKE_META)}. Run build_step11_optics_background_smoke.py first "
            "to build the detector-plus-lens geometry."
        )
    meta = json.loads(SMOKE_META.read_text())
    geometry_setup = meta["geometry_setup"]
    source_surface = meta["source_surface"]
    radius_cm = float(source_surface["radius_cm"])
    area_cm2 = math.pi * radius_cm * radius_cm

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = []
    for particle in PARTICLES:
        src = BASE_SOURCE_DIR / f"Background_{particle}_fullsphere20.source"
        dst = OUT_DIR / src.name
        dst.write_text(patch_source(src.read_text(), geometry_setup, radius_cm))
        sources.append(
            {
                "source": rel(dst),
                "base_source": rel(src),
                "geometry_setup": geometry_setup,
            }
        )

    manifest = {
        "status": "PASS",
        "purpose": "Full-statistics upstream Laue-lens prompt/activation production inputs",
        "source_dir": rel(OUT_DIR),
        "base_source_dir": rel(BASE_SOURCE_DIR),
        "geometry_setup": geometry_setup,
        "geometry_status": "STEP11_DETECTOR_PLUS_LENS_PROXY",
        "farfield_radius_cm": radius_cm,
        "farfield_area_cm2": area_cm2,
        "source_surface": source_surface,
        "lens_proxy": meta["lens_proxy"],
        "pointing_policy": {
            "megalib_length_unit": "cm",
            "zenith_frame": "FarFieldAreaSource theta/phi bins remain in global zenith coordinates",
            "implementation": "detector local frame remains tilted 45 deg; lens proxy is placed at the 10 m upstream optical location",
            "closure_policy": "Source sphere encloses both detector and upstream lens proxy; full-stat runner supplies the production event counts.",
        },
        "sources": sources,
    }
    (OUT_DIR / "source_migration_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
