#!/usr/bin/env python3
"""Build a compact-upper-service prompt-511 geometry candidate.

This smoke candidate tests whether the current high prompt-e+ excess is driven
by the exposed, non-active upper OVC/service tower.  It removes or truncates the
upper service source zone while preserving the side-window aperture definition.
It is not an authority CAD or sensitivity result.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_compact_upper_service_20260620"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_compact_upper_service"
BUILDER_PATH = ROOT / "code/geometry/build_demo2_dr_v3p5_centerfinger_megalib.py"

OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_compact_upper_service_zcap5p2"
OUT_GEOM = WORK / "geometry_compact_upper_service"
GEO = OUT_GEOM / f"{OUT_NAME}.geo"
DET = OUT_GEOM / f"{OUT_NAME}.det"
SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
INTRO = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
MATERIALS = OUT_GEOM / "Materials_DEMO2_DR_v3p5.geo"
VALIDATION = OUT_GEOM / "geometry_proxy_validation.json"
OVERLAP_SOURCE = WORK / "overlap_compact_upper_service.source"
OVERLAP_LOG = WORK / "overlap_compact_upper_service.log"
MANIFEST = WORK / "prompt511_compact_upper_service_manifest.json"
README = WORK / "README_compact_upper_service.md"

Z_CAP_CM = 5.20
OUTER_TOP_THIN_CM = 0.01
TRUNCATE_OPEN_TOP = {
    "Still_Shield_Al_side_window",
    "Shield_4K_Al_side_window",
    "Shield_60K_Al_side_window",
    "Vacuum_Jacket_Al_266mmClass_side_port",
}
REMOVE_IF_STARTS_ABOVE_ZCAP_CATEGORIES = {
    "cold_plate",
    "dr_unit",
    "service_proxy",
    "support",
    "vacuum_jacket",
}
THIN_OUTER_TOP_COMPONENT = "Outer_Al_Mechanical_Shell_detector_bay"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_builder():
    spec = importlib.util.spec_from_file_location("v3p5_builder", BUILDER_PATH)
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


def z_extent(comp: dict[str, Any]) -> tuple[float, float] | None:
    p = comp["params"]
    if "z0_cm" in p and "z1_cm" in p:
        return float(p["z0_cm"]), float(p["z1_cm"])
    if "z_center_cm" in p and "h_cm" in p:
        zc = float(p["z_center_cm"])
        half = 0.5 * float(p["h_cm"])
        return zc - half, zc + half
    if "z_out_bot_cm" in p and "z_top_cm" in p:
        return float(p["z_out_bot_cm"]), float(p["z_top_cm"])
    if "z_in_bot_cm" in p and "z_top_cm" in p:
        return float(p["z_in_bot_cm"]), float(p["z_top_cm"])
    return None


def thin_outer_top(comp: dict[str, Any], modifications: list[dict[str, Any]]) -> None:
    p = comp["params"]
    if "top_ann_z0_cm" not in p or "top_ann_z1_cm" not in p:
        return
    old = [float(p["top_ann_z0_cm"]), float(p["top_ann_z1_cm"])]
    p["top_ann_z0_cm"] = Z_CAP_CM
    p["top_ann_z1_cm"] = Z_CAP_CM + OUTER_TOP_THIN_CM
    modifications.append(
        {
            "action": "thin_outer_top_annulus",
            "component": comp["name"],
            "old_top_ann_z_cm": old,
            "new_top_ann_z_cm": [p["top_ann_z0_cm"], p["top_ann_z1_cm"]],
        }
    )


def mutate_bounds(bounds: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    out = copy.deepcopy(bounds)
    kept = []
    removed = []
    modifications = []

    for comp in out["COMPONENTS"]:
        name = comp["name"]
        p = comp["params"]
        if name in TRUNCATE_OPEN_TOP:
            old = float(p["z_top_cm"])
            p["z_top_cm"] = min(old, Z_CAP_CM)
            modifications.append(
                {
                    "action": "truncate_open_top_shell",
                    "component": name,
                    "old_z_top_cm": old,
                    "new_z_top_cm": p["z_top_cm"],
                    "side_hole_preserved": p.get("side_hole"),
                }
            )
        if name == THIN_OUTER_TOP_COMPONENT:
            thin_outer_top(comp, modifications)

    for comp in out["COMPONENTS"]:
        ext = z_extent(comp)
        starts_above_cap = ext is not None and ext[0] >= Z_CAP_CM
        removable_category = comp["category"] in REMOVE_IF_STARTS_ABOVE_ZCAP_CATEGORIES
        if starts_above_cap and removable_category:
            removed.append(
                {
                    "cid": comp["cid"],
                    "name": comp["name"],
                    "category": comp["category"],
                    "material": comp["material"],
                    "shape": comp["shape"],
                    "z_extent_cm": list(ext),
                    "mass_kg": comp.get("mass_kg"),
                }
            )
            continue
        kept.append(comp)

    out["COMPONENTS"] = kept
    out["META"]["prompt511_compact_upper_service_candidate"] = {
        "z_cap_cm": Z_CAP_CM,
        "intent": "Remove or truncate the exposed non-active upper OVC/service source zone for prompt-511 smoke testing.",
        "side_window_policy": "Do not change side-window radii, side-hole radii, window foils, or W sleeve bore.",
    }
    return out, modifications, removed


def build_geometry() -> dict[str, Any]:
    builder = load_builder()
    bounds = builder.load_json(builder.REF_BOUNDS)
    candidate_bounds, modifications, removed = mutate_bounds(bounds)

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
        "z_cap_cm": Z_CAP_CM,
        "modifications": modifications,
        "removed_components": removed,
        "removed_original_mass_kg": sum(float(row.get("mass_kg") or 0.0) for row in removed),
        "generated": builder.generated_summary(records),
        "detector_core": builder.detector_core_check(records, candidate_bounds),
        "component_to_generated_volumes": component_to_volumes,
        "beam_path_proxy": builder.beam_path_proxy_check(records),
        "geometry_extents": extents,
        "known_claim_boundary": "This is a prompt-511 source-zone systematic, not authority CAD.",
    }
    problems = []
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
        "status": "PASS_PROMPT511_COMPACT_UPPER_SERVICE_SOURCE_CARDS",
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
Minimum.FileName            /tmp/prompt511_compact_upper_service_overlap
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
        "# Prompt-511 Compact Upper-Service Candidate",
        "",
        "Status: geometry/source-card smoke candidate, not an authority result.",
        "",
        "Hypothesis:",
        "",
        "- Current prompt-e+ is partly driven by exposed non-active upper OVC/service material outside the old-like active shield topology.",
        "- Removing or truncating that upper source zone should reduce prompt without adding high-activation W/CsI mass.",
        "",
        "Geometry policy:",
        "",
        f"- z cap for upper service source zone: `{Z_CAP_CM:g} cm`.",
        "- Preserve side-window axis, side-hole radii, window foils, and W sleeve bore.",
        "- Do not add new active material and do not use ROI/spot cuts.",
        f"- removed original mass estimate from fully removed components: `{geom['removed_original_mass_kg']:.6g} kg`.",
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
        "- activation-only buildup isotope recording from the same geometry.",
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
        "claim_level": "PROMPT511_COMPACT_UPPER_SERVICE_DESIGN_SMOKE_NO_RATE_AUTHORITY",
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
