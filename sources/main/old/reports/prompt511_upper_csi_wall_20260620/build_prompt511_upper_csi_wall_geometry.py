#!/usr/bin/env python3
"""Build an upper-side CsI wall variant from the current v3p5 geometry.

This candidate tests the old-like "material column above the side port" route:
add active CsI above the present top annulus so incoming side/top-side e+ must
cross CsI before reaching the OVC upper side wall.  It is a design smoke only.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_upper_csi_wall_20260620"
SRC_GEOM = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_GEOM = WORK / "geometry_upper_csi_wall"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_upper_csi_wall_z5p55_13p35"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_upper_csi_wall"
MANIFEST = WORK / "prompt511_upper_csi_wall_manifest.json"
README = WORK / "README_upper_csi_wall.md"

PHI_SEGMENTS = 8
R_IN_CM = 13.6
R_OUT_CM = 18.0
Z_MIN_CM = 5.55
Z_MAX_CM = 13.35
CSI_DENSITY_G_CM3 = 4.51


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def require_inputs() -> None:
    missing = [
        path
        for path in (
            SRC_GEOM,
            SRC_SETUP,
            SRC_GEOM / f"{SRC_NAME}.geo",
            SRC_GEOM / f"{SRC_NAME}.det",
            SOURCE_IN,
        )
        if not path.exists()
    ]
    if missing:
        joined = "\n".join(f"- {rel(path)}" for path in missing)
        raise FileNotFoundError(f"upper-CsI-wall inputs are missing:\n{joined}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def upper_wall_mass_kg() -> float:
    volume_cm3 = math.pi * (R_OUT_CM * R_OUT_CM - R_IN_CM * R_IN_CM) * (Z_MAX_CM - Z_MIN_CM)
    return volume_cm3 * CSI_DENSITY_G_CM3 / 1000.0


def upper_wall_geo_block() -> str:
    z_center = 0.5 * (Z_MIN_CM + Z_MAX_CM)
    z_half = 0.5 * (Z_MAX_CM - Z_MIN_CM)
    lines = [
        "",
        "// Prompt-511 upper-side-wall smoke: added active CsI above the current top annulus.",
        "// This is a local design-smoke volume set, not authority CAD.",
    ]
    for idx in range(PHI_SEGMENTS):
        phi0 = 45.0 * idx
        name = f"CsI_UpperSideWall_Prompt511_Segment_{idx:02d}"
        lines.extend(
            [
                f"// Volume {name}; material=CsI",
                f"Volume {name}",
                f"{name}.Material CsI",
                f"{name}.Visibility 1",
                f"{name}.Shape PCON {phi0:g} 45 2 {-z_half:g} {R_IN_CM:g} {R_OUT_CM:g} {z_half:g} {R_IN_CM:g} {R_OUT_CM:g}",
                "",
                f"{name}.Position 0 0 {z_center:g}",
                f"{name}.Mother InstrumentFrame",
                "",
            ]
        )
    return "\n".join(lines)


def upper_wall_det_block() -> str:
    lines = [
        "",
        "// Prompt-511 upper-side-wall smoke sensitive-volume entries.",
        "// Low detector threshold records CsI deposits; the Step05-like proxy applies the 50 keV veto threshold.",
    ]
    for idx in range(PHI_SEGMENTS):
        vol = f"CsI_UpperSideWall_Prompt511_Segment_{idx:02d}"
        sd = f"{vol}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {vol}",
                f"{sd}.DetectorVolume {vol}",
                f"{sd}.TriggerThreshold 0.001",
                f"{sd}.EnergyResolution Gauss 0.001 0.001 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    return "\n".join(lines)


def build_geometry() -> dict[str, object]:
    require_inputs()
    if OUT_GEOM.exists():
        shutil.rmtree(OUT_GEOM)
    shutil.copytree(SRC_GEOM, OUT_GEOM)

    for old in (
        OUT_GEOM / f"{SRC_NAME}.geo.setup",
        OUT_GEOM / f"{SRC_NAME}.geo",
        OUT_GEOM / f"{SRC_NAME}.det",
        OUT_GEOM / f"Intro_{SRC_NAME}.geo",
    ):
        old.rename(OUT_GEOM / old.name.replace(SRC_NAME, OUT_NAME))

    setup = replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8"))
    OUT_SETUP.write_text(setup, encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo = replace_geometry_names(geo_path.read_text(encoding="utf-8"))
    geo = geo.rstrip() + upper_wall_geo_block() + "\n"
    geo_path.write_text(geo, encoding="utf-8")

    intro_path = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
    intro_path.write_text(replace_geometry_names(intro_path.read_text(encoding="utf-8")), encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det = replace_geometry_names(det_path.read_text(encoding="utf-8"))
    det = det.rstrip() + upper_wall_det_block() + "\n"
    det_path.write_text(det, encoding="utf-8")

    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "added_material": "CsI",
        "added_segments": PHI_SEGMENTS,
        "added_envelope": {
            "r_cm": [R_IN_CM, R_OUT_CM],
            "z_cm": [Z_MIN_CM, Z_MAX_CM],
            "phi_deg": [0.0, 360.0],
        },
        "estimated_added_csi_mass_kg": upper_wall_mass_kg(),
        "active_veto_match": "Added CsI volumes have low-threshold Scintillator entries; Step05 proxy treats volume names starting with CsI_ as active veto volumes.",
    }


def migrate_sources() -> dict[str, object]:
    if SOURCE_OUT.exists():
        shutil.rmtree(SOURCE_OUT)
    SOURCE_OUT.mkdir(parents=True)

    rows = []
    for src in sorted(SOURCE_IN.glob("Background_*_fullsphere20.source")):
        text = re.sub(
            r"^Geometry\s+.+$",
            f"Geometry {OUT_SETUP}",
            src.read_text(encoding="utf-8"),
            count=1,
            flags=re.MULTILINE,
        )
        out = SOURCE_OUT / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})

    manifest = {
        "status": "PASS_PROMPT511_UPPER_CSI_WALL_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(OUT_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_overlap_source() -> dict[str, str]:
    source = WORK / "overlap_upper_csi_wall.source"
    log = WORK / "overlap_upper_csi_wall.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_upper_csi_wall_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
""",
        encoding="utf-8",
    )
    return {"overlap_source": rel(source), "overlap_log": rel(log)}


def write_readme(payload: dict[str, object]) -> None:
    geometry = payload["geometry"]
    assert isinstance(geometry, dict)
    lines = [
        "# Prompt-511 Upper CsI Wall Smoke",
        "",
        "Status: geometry/source-card candidate for prompt mechanism testing.",
        "",
        "Purpose:",
        "",
        "- Test the old-like upper side-wall material-column route without the repack inner collar.",
        "- Intercept incoming side/top-side e+ before they reach the OVC upper side wall, where current selected prompt events cluster.",
        "- Keep the side signal port unchanged; the added CsI starts above the present outer top annulus.",
        "",
        "Geometry change:",
        "",
        f"- base setup: `{payload['base_geometry']}`",
        f"- candidate setup: `{geometry['geometry_setup']}`",
        f"- added active CsI envelope: r `{R_IN_CM:g}..{R_OUT_CM:g} cm`, z `{Z_MIN_CM:g}..{Z_MAX_CM:g} cm`, full 360 deg in 8 segments.",
        f"- estimated added CsI mass: `{geometry['estimated_added_csi_mass_kg']:.6g} kg`.",
        "",
        "Claim boundary:",
        "",
        "- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.",
        "- The active-veto behavior is currently tested through added low-threshold `.det` sensitive-volume entries plus the Step05-like proxy volume-name matcher; authority trigger wiring still needs a separate implementation if this route survives.",
        "- Added CsI mass may create activation risk; activation/isotope smoke is required before promotion.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": "PASS_PROMPT511_UPPER_CSI_WALL_GEOMETRY_READY",
        "claim_level": "PROMPT511_UPPER_CSI_WALL_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "base_geometry": rel(SRC_SETUP),
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "readme": rel(README),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
