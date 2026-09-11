#!/usr/bin/env python3
"""Build a prompt-511 minimum side-aperture geometry candidate.

This smoke candidate tests the side-port CSG/topology lever directly: keep the
physical window and W sleeve bore unchanged, but shrink the surrounding
annulus side-hole proxy to the Be/window half-side so existing passive/active
side-wall material is restored outside the focused-beam channel.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_min_side_aperture_20260620"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_min_side_aperture"
BUILDER_PATH = ROOT / "code/geometry/build_demo2_dr_v3p5_centerfinger_megalib.py"

OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_min_side_aperture_r1p90"
OUT_GEOM = WORK / "geometry_min_side_aperture"
GEO = OUT_GEOM / f"{OUT_NAME}.geo"
DET = OUT_GEOM / f"{OUT_NAME}.det"
SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
INTRO = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
MATERIALS = OUT_GEOM / "Materials_DEMO2_DR_v3p5.geo"
VALIDATION = OUT_GEOM / "geometry_proxy_validation.json"
OVERLAP_SOURCE = WORK / "overlap_min_side_aperture.source"
OVERLAP_LOG = WORK / "overlap_min_side_aperture.log"
MANIFEST = WORK / "prompt511_min_side_aperture_manifest.json"
README = WORK / "README_min_side_aperture.md"

TARGET_SIDE_HOLE_R_CM = 1.90
WINDOW_HALF_SIDE_CM = 1.898
UNCHANGED_COMPONENTS = {"W_Side_Aperture_Sleeve_collimator"}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_builder():
    spec = importlib.util.spec_from_file_location("v3p5_builder_min_side_aperture", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load geometry builder from {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEOM_NAME = OUT_NAME
    module.OUT = OUT_GEOM
    module.GEO = GEO
    module.DET = DET
    module.SETUP = SETUP
    module.INTRO = INTRO
    module.MATERIALS = MATERIALS
    module.VALIDATION = VALIDATION
    module.README = OUT_GEOM / "README.md"
    module.OVERLAP_SOURCE = OVERLAP_SOURCE
    module.OVERLAP_LOG = OVERLAP_LOG
    return module


def mutate_bounds(bounds: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    out = copy.deepcopy(bounds)
    modifications = []
    for comp in out["COMPONENTS"]:
        name = comp["name"]
        if name in UNCHANGED_COMPONENTS:
            continue
        params = comp.get("params", {})
        side_hole = params.get("side_hole")
        if not side_hole:
            continue
        old_r = float(side_hole["r_cm"])
        if old_r <= TARGET_SIDE_HOLE_R_CM:
            continue
        side_hole["r_cm"] = TARGET_SIDE_HOLE_R_CM
        if "side_port_radius_cm" in params:
            params["side_port_radius_cm"] = TARGET_SIDE_HOLE_R_CM
        modifications.append(
            {
                "action": "shrink_side_hole_radius",
                "component": name,
                "old_r_cm": old_r,
                "new_r_cm": TARGET_SIDE_HOLE_R_CM,
                "window_half_side_cm": WINDOW_HALF_SIDE_CM,
            }
        )
    out["META"]["prompt511_min_side_aperture_candidate"] = {
        "target_side_hole_r_cm": TARGET_SIDE_HOLE_R_CM,
        "window_half_side_cm": WINDOW_HALF_SIDE_CM,
        "intent": "Restore side-wall material outside the focused-beam channel without shrinking the physical window or W sleeve bore.",
        "no_roi_or_material_swap": True,
    }
    return out, modifications


def build_geometry() -> dict[str, Any]:
    builder = load_builder()
    bounds = builder.load_json(builder.REF_BOUNDS)
    candidate_bounds, modifications = mutate_bounds(bounds)

    if OUT_GEOM.exists():
        shutil.rmtree(OUT_GEOM)
    OUT_GEOM.mkdir(parents=True, exist_ok=True)

    builder.write_materials()
    builder.write_intro()
    geo_text, records, component_to_volumes = builder.build_geo(candidate_bounds)
    builder.write_text(GEO, geo_text)
    builder.write_det(records)
    extents = builder.parse_generated_geometry_extents(geo_text)
    builder.write_setup(extents)

    builder.write_text(
        OUT_GEOM / f"{OUT_NAME}_bounds.json",
        json.dumps(candidate_bounds, indent=2, ensure_ascii=False) + "\n",
    )
    validation = {
        "geometry_name": OUT_NAME,
        "status": "GEOMETRY_BUILT_OVERLAP_PENDING",
        "base_bounds": rel(builder.REF_BOUNDS),
        "generated_setup": rel(SETUP),
        "target_side_hole_r_cm": TARGET_SIDE_HOLE_R_CM,
        "window_half_side_cm": WINDOW_HALF_SIDE_CM,
        "modifications": modifications,
        "generated": builder.generated_summary(records),
        "detector_core": builder.detector_core_check(records, candidate_bounds),
        "component_to_generated_volumes": component_to_volumes,
        "beam_path_proxy": builder.beam_path_proxy_check(records),
        "geometry_extents": extents,
        "known_claim_boundary": "This is a prompt-511 side-port topology smoke, not authority CAD.",
    }
    problems = []
    if TARGET_SIDE_HOLE_R_CM < WINDOW_HALF_SIDE_CM:
        problems.append("side_hole_smaller_than_window_half_side")
    if validation["detector_core"]["status"] != "PASS":
        problems.append("detector_core_not_faithful")
    if validation["beam_path_proxy"]["status"] != "PASS":
        problems.append("beam_path_proxy_centerline_risk")
    validation["problems"] = problems
    validation["status"] = "GEOMETRY_BUILT_OVERLAP_PENDING" if not problems else "GEOMETRY_NEEDS_REVIEW"
    builder.write_text(VALIDATION, json.dumps(validation, indent=2, ensure_ascii=False) + "\n")
    return validation


def migrate_sources() -> dict[str, Any]:
    if SOURCE_OUT.exists():
        shutil.rmtree(SOURCE_OUT)
    SOURCE_OUT.mkdir(parents=True)

    rows = []
    for src in sorted(SOURCE_IN.glob("Background_*_fullsphere20.source")):
        text = re.sub(
            r"^Geometry\s+.+$",
            f"Geometry {SETUP}",
            src.read_text(encoding="utf-8"),
            count=1,
            flags=re.MULTILINE,
        )
        out = SOURCE_OUT / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})

    manifest = {
        "status": "PASS_PROMPT511_MIN_SIDE_APERTURE_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_overlap_source() -> dict[str, str]:
    OVERLAP_SOURCE.write_text(
        f"""Version                     1
Geometry                    {SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_min_side_aperture_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
""",
        encoding="utf-8",
    )
    return {"overlap_source": rel(OVERLAP_SOURCE), "overlap_log": rel(OVERLAP_LOG)}


def write_readme(payload: dict[str, Any]) -> None:
    geom = payload["geometry"]
    lines = [
        "# Prompt-511 Minimum Side-Aperture Candidate",
        "",
        "Status: geometry/source-card smoke candidate, not an authority result.",
        "",
        "Hypothesis:",
        "",
        "- Current prompt-e+ survives because the side-port proxy removes too much surrounding passive/active side-wall material.",
        "- Shrinking only the surrounding side-hole proxy to the physical Be/window half-side restores old-like material continuity while keeping the focused channel open.",
        "",
        "Geometry policy:",
        "",
        f"- target side-hole proxy radius: `{TARGET_SIDE_HOLE_R_CM:g} cm`.",
        f"- physical side-window half-side retained: `{WINDOW_HALF_SIDE_CM:g} cm`.",
        "- W sleeve bore is unchanged; no material swap, no ROI/spot cut, no new active material.",
        f"- modified side-hole components: `{len(geom['modifications'])}`.",
        "",
        "Outputs:",
        "",
        f"- geometry setup: `{geom['generated_setup']}`",
        f"- source cards: `{payload['sources']['source_dir']}`",
        f"- overlap source: `{payload['overlap']['overlap_source']}`",
        "",
        "Required gates before promotion:",
        "",
        "- Cosima overlap pass.",
        "- prompt-only e+, n, mu+ smoke with `--disable-isotope-store`.",
        "- activation-only buildup isotope recording from the same geometry if prompt passes.",
        "- no claim of new sensitivity authority until delayed/signal/time-axis closure is rebuilt.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": geometry["status"],
        "claim_level": "PROMPT511_MIN_SIDE_APERTURE_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "readme": rel(README),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0 if not geometry["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
