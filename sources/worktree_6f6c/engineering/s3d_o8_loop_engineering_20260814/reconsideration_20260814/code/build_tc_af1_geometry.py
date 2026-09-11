#!/usr/bin/env python3
"""Build the single TC-AF1 transparent-core geometry for falsification.

TC-AF1 is deliberately a system topology rather than a component-by-component
rate subtraction:

* every explicitly modeled passive Copper volume is changed in-place to the
  existing Aluminium transport material (names/interfaces/CSG stay fixed);
* the Nb and MuMetal sleeves and back caps retain their clear bores and axial
  envelopes but use 0.5 mm functional walls instead of 2 mm walls;
* the existing one-channel 10 mm top BGO annulus is extended inward from
  r=20.9 cm to r=4.0 cm, preserving one central service opening, every
  existing NF2 relief, and 12 clearance holes around the modeled top pipes.

The result is a transport proxy for a focused paired test.  It is not a claim
that Aluminium is a qualified 50 mK thermal material or that the smaller top
service keep-out is compatible with as-built hardware.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parents[2]
OUT = PACKAGE / "geometry"
DATA = PACKAGE / "data"
BASE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
)
BASE_GEO = BASE / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
BASE_DET = BASE / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
BASE_INTRO = BASE / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
BASE_MATERIALS = BASE / "Materials_DEMO2_DR_v3p5.geo"

NAME = "DEMO2_DR_v3p5_S3d_O8_TC_AF1_AlCu_Mag0p5_TopBGO4cm12hole_20260814"


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, dict[str, str]]:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one token, found {count}")
    return text.replace(old, new, 1), {"label": label, "old": old, "new": new}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    text = BASE_GEO.read_text(encoding="utf-8")
    edits: list[dict[str, str]] = []

    # Apply one material rule to every explicit passive Copper volume while
    # keeping volume and detector names stable.  The source geometry contains
    # no separately modeled readout-Cu trace or readout channel volume.
    lines = text.splitlines()
    current_volume: str | None = None
    copper_volumes: list[str] = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"Volume\s+(\S+)", line)
        if match:
            current_volume = match.group(1)
        material = re.fullmatch(r"(\S+)\.Material Copper", line)
        if not material:
            continue
        if current_volume is None or material.group(1) != current_volume:
            raise RuntimeError(f"unresolved Copper material declaration at line {index + 1}")
        lines[index] = f"{current_volume}.Material Aluminium"
        copper_volumes.append(current_volume)
    if len(copper_volumes) != 60 or len(copper_volumes) != len(set(copper_volumes)):
        raise RuntimeError(f"Copper volume census drift: {len(copper_volumes)}")
    text = "\n".join(lines) + "\n"
    edits.append(
        {
            "label": "all 60 explicitly modeled passive Copper volumes -> Aluminium in place",
            "old": "<60 volume-specific .Material Copper declarations>",
            "new": "<same 60 volume-specific .Material Aluminium declarations>",
        }
    )

    shape_edits = [
        (
            "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2",
            "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.05 4.1 4 4.05",
            "Nb sleeve wall 2.0 -> 0.5 mm at fixed r=4.0 cm bore",
        ),
        (
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2",
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.05 4.15 1.85 4.05",
            "Nb back cap 2.0 -> 0.5 mm with unchanged r=1.85 cm opening",
        ),
        (
            "MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.45 4.3 4.25 4.45",
            "MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.3 4.3 4.25 4.3",
            "MuMetal sleeve wall 2.0 -> 0.5 mm at fixed r=4.25 cm bore",
        ),
        (
            "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.45 4.5 1.85 4.45",
            "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.3 4.35 1.85 4.3",
            "MuMetal back cap 2.0 -> 0.5 mm with unchanged r=1.85 cm opening",
        ),
        (
            "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters 0 360 2 -0.5 20.9 25.2 0.5 20.9 25.2",
            "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters 0 360 2 -0.5 4 25.2 0.5 4 25.2",
            "existing top BGO channel inner radius 20.9 -> 4.0 cm at fixed 10 mm thickness",
        ),
    ]
    for old, new, label in shape_edits:
        text, record = replace_once(text, old, new, label)
        edits.append(record)

    # The first solid-fill attempt was killed by CheckForOverlaps: all three
    # large top pipes and all nine micro-conduits intersect the added BGO.
    # Use explicit macroscopic clearances around the *modeled* service axes.
    # Radii are the transported pipe outer radii plus 1 mm clearance.
    top_holes = [
        ("GasReturn_A", 5.0, 3.2, 2.0),
        ("PumpFill_B", 7.4, -2.8, 1.75),
        ("VacuumService_C", -4.5, 6.5, 1.35),
        ("Micro01", -2.4, 8.8, 0.75),
        ("Micro02", -0.2, 8.9, 0.75),
        ("Micro03", 2.0, 8.8, 0.75),
        ("Micro04", 4.2, 8.6, 0.75),
        ("Micro05", 6.4, 8.3, 0.75),
        ("Micro06", -1.3, 10.9, 0.75),
        ("Micro07", 0.9, 11.1, 0.75),
        ("Micro08", 3.1, 10.9, 0.75),
        ("Micro09", 5.3, 10.5, 0.75),
    ]
    previous_shape = "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_ReliefStep06Shape"
    hole_lines: list[str] = []
    for number, (label, x_cm, y_cm, radius_cm) in enumerate(top_holes, start=1):
        stem = f"TC_AF1_TopBGO_ServiceHole_{number:02d}_{label}"
        hole_lines.extend(
            [
                f"Shape PCON {stem}Shape",
                f"{stem}Shape.Parameters 0 360 2 -1 0 {radius_cm:g} 1 0 {radius_cm:g}",
                f"Orientation {stem}Orientation",
                f"{stem}Orientation.Position {x_cm:g} {y_cm:g} 0",
                f"Shape Subtraction {stem}SubtractionShape",
                f"{stem}SubtractionShape.Parameters {previous_shape} {stem}Shape {stem}Orientation",
            ]
        )
        previous_shape = f"{stem}SubtractionShape"
    marker = "// Volume BGO_S3D_O8_FullWrap_TopAnnulus_10mm; kind=pcon;"
    if text.count(marker) != 1:
        raise RuntimeError("top BGO volume marker drift")
    text = text.replace(marker, "\n".join(hole_lines) + "\n" + marker, 1)
    old_top_shape = (
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape "
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_ReliefStep06Shape"
    )
    new_top_shape = f"BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape {previous_shape}"
    text, record = replace_once(
        text,
        old_top_shape,
        new_top_shape,
        "subtract 12 modeled top-service clearances from the same top BGO volume",
    )
    edits.append(record)

    geo = OUT / f"{NAME}.geo"
    det = OUT / f"{NAME}.det"
    setup = OUT / f"{NAME}.geo.setup"
    intro = OUT / BASE_INTRO.name
    materials = OUT / BASE_MATERIALS.name
    geo.write_text(text, encoding="utf-8")
    shutil.copyfile(BASE_DET, det)
    shutil.copyfile(BASE_INTRO, intro)
    shutil.copyfile(BASE_MATERIALS, materials)
    setup.write_text(
        f"Name {NAME}\nVersion 1\nInclude {geo.resolve()}\n"
        f"Include {det.resolve()}\nSurroundingSphere 60 5 0 9 60\n",
        encoding="utf-8",
    )

    overlap = OUT / "overlap_check_tc_af1.source"
    overlap.write_text(
        "Version                     1\n"
        f"Geometry                    {setup.resolve()}\n"
        "CheckForOverlaps            10000 0.0001\n"
        "PhysicsListEM               LivermorePol\n"
        "Run Minimum\n"
        "Minimum.FileName            /tmp/DelMe_s3d_o8_tc_af1_overlap\n"
        "Minimum.NEvents             1\n"
        "Minimum.Source MinimumS\n"
        "MinimumS.ParticleType       1\n"
        "MinimumS.Beam               PointSource 0 0 0\n"
        "MinimumS.Spectrum           Mono 511\n"
        "MinimumS.Flux               1.0\n",
        encoding="utf-8",
    )

    rho_cu = 8.954
    rho_al = 2.7
    rho_nb = 8.57
    rho_mu = 8.7
    rho_bgo = 7.1
    named_cu_baseline_kg = 19.8563
    named_cu_candidate_kg = named_cu_baseline_kg * rho_al / rho_cu
    nb_baseline_kg = (
        math.pi * (4.2**2 - 4.0**2) * 7.95 * rho_nb
        + math.pi * (4.2**2 - 1.85**2) * 0.2 * rho_nb
    ) / 1000
    nb_candidate_kg = (
        math.pi * (4.05**2 - 4.0**2) * 7.95 * rho_nb
        + math.pi * (4.05**2 - 1.85**2) * 0.05 * rho_nb
    ) / 1000
    mu_baseline_kg = (
        math.pi * (4.45**2 - 4.25**2) * 8.65 * rho_mu
        + math.pi * (4.45**2 - 1.85**2) * 0.2 * rho_mu
    ) / 1000
    mu_candidate_kg = (
        math.pi * (4.30**2 - 4.25**2) * 8.65 * rho_mu
        + math.pi * (4.30**2 - 1.85**2) * 0.05 * rho_mu
    ) / 1000
    top_bgo_added_gross_kg = math.pi * (20.9**2 - 4.0**2) * 1.0 * rho_bgo / 1000
    top_bgo_nominal_hole_kg = (
        math.pi * math.fsum(radius**2 for _, _, _, radius in top_holes) * 1.0 * rho_bgo / 1000
    )
    known_net_mass_delta_kg = (
        named_cu_candidate_kg - named_cu_baseline_kg
        + nb_candidate_kg - nb_baseline_kg
        + mu_candidate_kg - mu_baseline_kg
        + top_bgo_added_gross_kg
    )

    manifest = {
        "schema_version": 1,
        "candidate": "TC-AF1",
        "status": "BUILT_PROXY_FOR_FOCUSED_FALSIFICATION__NOT_ENGINEERING_RELEASE",
        "base_geometry": str(BASE_GEO),
        "geometry": str(geo.relative_to(REPO)),
        "detector": str(det.relative_to(REPO)),
        "setup": str(setup.relative_to(REPO)),
        "overlap_source": str(overlap.relative_to(REPO)),
        "copper_material_substitution_count": len(copper_volumes),
        "copper_material_substitution_volumes": copper_volumes,
        "declared_edits": edits,
        "known_proxy_mass_kg": {
            "named_Cu_baseline": named_cu_baseline_kg,
            "same_named_volume_as_Al": named_cu_candidate_kg,
            "Nb_baseline": nb_baseline_kg,
            "Nb_0p5mm": nb_candidate_kg,
            "Mu_baseline": mu_baseline_kg,
            "Mu_0p5mm": mu_candidate_kg,
            "top_BGO_added_gross_before_12_pipe_holes": top_bgo_added_gross_kg,
            "top_BGO_nominal_12_pipe_hole_subtraction": top_bgo_nominal_hole_kg,
            "top_BGO_nominal_net_added_no_hole_overlap_correction": (
                top_bgo_added_gross_kg - top_bgo_nominal_hole_kg
            ),
            "known_net_candidate_minus_baseline": known_net_mass_delta_kg,
        },
        "mass_boundary": (
            "Named 19.8563 kg Cu is a lower-bound proxy census.  Additional coarse Copper "
            "volumes are substituted too but lack a configuration-controlled post-CSG mass; "
            "therefore the true candidate mass saving is larger in this transport proxy."
        ),
        "physics_falsifiers": [
            "Al activation or source-host migration prevents >=95% net suppression of baseline Copper delayed counts.",
            "Candidate Nb+Mu production-times-coupling suppression is <75% after exact inventory and decay transport.",
            "Candidate prompt suppression is <80% after denominator-complete gamma transport.",
            "Candidate signal retention is <95% or central F3 remains above 3e-5 photon cm^-2 s^-1.",
        ],
        "engineering_falsifiers": [
            "Any substituted Cu volume is an irreplaceable readout conductor rather than passive thermal/structural bulk.",
            "Aluminium at the relevant thermal stage cannot meet heat-flow, contact, stiffness, magnetic, or launch requirements.",
            "0.5 mm Nb or MuMetal fails the agreed magnetic field/noise/field-cool qualification.",
            "The as-built top-service axes/clearances differ from the 12 proxy holes or cannot share the existing top-BGO readout.",
        ],
    }
    manifest_path = DATA / "tc_af1_geometry_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
