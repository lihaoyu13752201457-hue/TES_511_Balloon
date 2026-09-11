#!/usr/bin/env python3
"""Build the geometry-only BG-J4 S3d-O8 proxy.

BG-J4 leaves the complete cold core, Cu/Ni inventory, cold plates, Nb/Mu and
service hardware identical to baseline.  It adds 4 cm to the existing BGO
side/bottom/top channel volumes, closes the old top annular opening except for
the 12 real service penetrations and six NF2 reliefs, and moves the existing
outer Kapton/Al/BPE/plastic layers outward without changing their thickness or
logical volume names.  No transport is launched by this script.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


SOURCE_DIR = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
)
SOURCE_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUTPUT_STEM = "S3D_O8_BG_J4_fullwrap_BGO4cm_proxy"
DELTA_CM = 4.0


# Maximal pipe/sleeve outer radius intersecting z=40.9--45.9 cm, plus 0.5 mm.
TOP_SERVICE_RELIEFS = (
    ("GasReturn_A", 5.0, 3.2, 2.45),
    ("PumpFill_B", 7.4, -2.8, 2.15),
    ("Vacuum_C", -4.5, 6.5, 1.69),
    ("Micro_01", -2.4, 8.8, 0.95),
    ("Micro_02", -0.2, 8.9, 0.95),
    ("Micro_03", 2.0, 8.8, 0.95),
    ("Micro_04", 4.2, 8.6, 0.95),
    ("Micro_05", 6.4, 8.3, 0.95),
    ("Micro_06", -1.3, 10.9, 0.95),
    ("Micro_07", 0.9, 11.1, 0.95),
    ("Micro_08", 3.1, 10.9, 0.95),
    ("Micro_09", 5.3, 10.5, 0.95),
)


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, got {count}: {old}")
    return text.replace(old, new, 1)


def shift_component(
    text: str,
    volume: str,
    old_center: float,
    new_center: float,
    relief_prefix: str,
) -> str:
    """Move one cap and keep all subtraction tools fixed in world space."""
    text = replace_once(
        text,
        f"{volume}.Position 0 0 {old_center:g}",
        f"{volume}.Position 0 0 {new_center:g}",
    )
    dz = new_center - old_center
    pattern = re.compile(
        rf"^({re.escape(relief_prefix)}\S*ReliefOrientation\.Position "
        rf"[-+0-9.eE]+ [-+0-9.eE]+ )([-+0-9.eE]+)$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError(f"no relief positions found for {relief_prefix}")
    return pattern.sub(lambda m: m.group(1) + f"{float(m.group(2)) - dz:.12g}", text)


def top_service_block(half_height: float) -> tuple[str, str]:
    prefix = "BGO_S3D_O8_FullWrap_TopAnnulus_10mm"
    previous = f"{prefix}_NF2_ReliefStep06Shape"
    lines = [
        "",
        "// BG-J4: old top opening closed; only 12 measured service envelopes remain.",
    ]
    for index, (label, x, y, radius) in enumerate(TOP_SERVICE_RELIEFS, start=1):
        shape = f"{prefix}_BGJ4_Service_{label}_ReliefShape"
        orientation = f"{prefix}_BGJ4_Service_{label}_ReliefOrientation"
        result = f"{prefix}_BGJ4_ServiceReliefStep{index:02d}Shape"
        lines.extend(
            [
                f"Shape PCON {shape}",
                f"{shape}.Parameters 0 360 2 {-half_height:.12g} 0 {radius:.12g} "
                f"{half_height:.12g} 0 {radius:.12g}",
                f"Orientation {orientation}",
                f"{orientation}.Position {x:.12g} {y:.12g} 0",
                f"Shape Subtraction {result}",
                f"{result}.Parameters {previous} {shape} {orientation}",
            ]
        )
        previous = result
    lines.append("")
    return "\n".join(lines), previous


def add_side_optical_relief(text: str, prefix: str, outer_radius: float) -> str:
    """Continue the existing rectangular signal aperture through BPE/plastic."""
    old_shape = f"{prefix}_NF2ReliefStep08Shape"
    shape = f"{prefix}_BGJ4_OpticalWindowReliefShape"
    orient = f"{prefix}_BGJ4_OpticalWindowReliefOrientation"
    result = f"{prefix}_BGJ4_OpticalWindowReliefResultShape"
    half_x = outer_radius / 2.0 + 0.0001
    center_x = -outer_radius / 2.0
    block = "\n".join(
        [
            "",
            "// BG-J4: continue the frozen side optical aperture through this shifted layer.",
            f"Shape BRIK {shape}",
            f"{shape}.Parameters {half_x:.12g} 1.898 1.898",
            f"Orientation {orient}",
            f"{orient}.Position {center_x:.12g} 0 -15.95",
            f"Shape Subtraction {result}",
            f"{result}.Parameters {old_shape} {shape} {orient}",
            "",
        ]
    )
    marker = f"// Volume {prefix};"
    if text.count(marker) != 1:
        raise RuntimeError(f"volume marker not unique: {marker}")
    text = text.replace(marker, block + marker, 1)
    return replace_once(text, f"{prefix}.Shape {old_shape}", f"{prefix}.Shape {result}")


def add_nf2_mount_reliefs(
    text: str,
    prefix: str,
    base_local_z: float,
    top_local_z: float,
) -> str:
    """Relieve the two fixed NF2 support annuli from a shifted outer cap."""
    previous = f"{prefix}_NF2_ReliefStep06Shape"
    lines = ["", "// BG-J4: shifted cap reliefs for the two immutable NF2 mount annuli."]
    specifications = (
        ("BaseMount", 0.8, 34.9, 49.0, 19.7989899, base_local_z),
        ("TopMount", 0.55, 34.1, 49.8, -24.7487373, top_local_z),
    )
    for index, (label, half_z, r_in, r_out, x, z) in enumerate(specifications, start=1):
        shape = f"{prefix}_BGJ4_{label}Annulus_ReliefShape"
        orientation = f"{prefix}_BGJ4_{label}Annulus_ReliefOrientation"
        result = f"{prefix}_BGJ4_MountReliefStep{index:02d}Shape"
        lines.extend(
            [
                f"Shape PCON {shape}",
                f"{shape}.Parameters 0 360 2 {-half_z:.12g} {r_in:.12g} {r_out:.12g} "
                f"{half_z:.12g} {r_in:.12g} {r_out:.12g}",
                f"Orientation {orientation}",
                f"{orientation}.Position {x:.12g} 0 {z:.12g}",
                f"{orientation}.Rotation 0 -45 0",
                f"Shape Subtraction {result}",
                f"{result}.Parameters {previous} {shape} {orientation}",
            ]
        )
        previous = result
    lines.append("")
    marker = f"// Volume {prefix};"
    if text.count(marker) != 1:
        raise RuntimeError(f"cap marker not unique: {marker}")
    text = text.replace(marker, "\n".join(lines) + marker, 1)
    return replace_once(
        text,
        f"{prefix}.Shape {prefix}_NF2_ReliefStep06Shape",
        f"{prefix}.Shape {previous}",
    )


def build(output_dir: Path) -> Path:
    source_geo = SOURCE_DIR / f"{SOURCE_STEM}.geo"
    text = source_geo.read_text()

    text = replace_once(
        text,
        "// Exact-copy S3c-C0 base; the original side40 block is untouched, bottom/top become 30/10 mm, and only outer W2 is removed.",
        "// BG-J4 base: cold core exact; existing BGO channels gain a 4 cm closed full-wrap shell.",
    )

    # Active BGO: closed outer cylinder around the unchanged cavity.  Enlarging
    # cap radii with the side avoids an unshielded oblique corner seam.
    text = replace_once(
        text,
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_FullShellShape.Parameters 0 360 2 -30.15 21.2 25.2 30.15 21.2 25.2",
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_FullShellShape.Parameters 0 360 2 -30.15 21.2 29.2 30.15 21.2 29.2",
    )
    text = replace_once(
        text,
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_RectWindowCutShape.Parameters 12.6001 1.898 1.898",
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_RectWindowCutShape.Parameters 14.6001 1.898 1.898",
    )
    text = replace_once(
        text,
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_RectWindowCutOrientation.Position -12.6 0 -15.95",
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_RectWindowCutOrientation.Position -14.6 0 -15.95",
    )

    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_BottomCap_30mm_BasePconShape.Parameters 0 360 2 -1.5 0 25.2 1.5 0 25.2",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm_BasePconShape.Parameters 0 360 2 -3.5 0 29.2 3.5 0 29.2",
    )
    text = shift_component(
        text,
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        -20.9,
        -22.9,
        "BGO_S3D_O8_FullWrap_BottomCap_30mm_NF2_",
    )

    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters 0 360 2 -0.5 20.9 25.2 0.5 20.9 25.2",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters 0 360 2 -2.5 0 29.2 2.5 0 29.2",
    )
    text = shift_component(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
        41.4,
        43.4,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_",
    )
    service_block, final_top_shape = top_service_block(2.51)
    marker = "// Volume BGO_S3D_O8_FullWrap_TopAnnulus_10mm; kind=pcon;"
    if text.count(marker) != 1:
        raise RuntimeError("top BGO marker not unique")
    text = text.replace(marker, service_block + marker, 1)
    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_ReliefStep06Shape",
        f"BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape {final_top_shape}",
    )

    # Existing Kapton and Al packaging follows the enlarged BGO outward.  Names
    # and thicknesses are unchanged; cap relief tools remain fixed in world.
    text = replace_once(
        text,
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_FullShellShape.Parameters 0 360 2 -34.32 25.37 25.4 34.32 25.37 25.4",
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_FullShellShape.Parameters 0 360 2 -38.32 29.37 29.4 38.32 29.37 29.4",
    )
    text = replace_once(
        text,
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_RectWindowCutShape.Parameters 12.7001 1.898 1.898",
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_RectWindowCutShape.Parameters 14.7001 1.898 1.898",
    )
    text = replace_once(
        text,
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_RectWindowCutOrientation.Position -12.7 0 -15.95",
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm_RectWindowCutOrientation.Position -14.7 0 -15.95",
    )
    text = add_nf2_mount_reliefs(
        text,
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
        -23.4779221,
        21.0698052,
    )
    text = replace_once(
        text,
        "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm_BasePconShape.Parameters 0 360 2 -0.015 0 25.4 0.015 0 25.4",
        "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm_BasePconShape.Parameters 0 360 2 -0.015 0 29.4 0.015 0 29.4",
    )
    text = shift_component(
        text,
        "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
        -23.585,
        -27.585,
        "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm_NF2_",
    )
    text = replace_once(
        text,
        "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm_BasePconShape.Parameters 0 360 2 -0.015 20.9 25.4 0.015 20.9 25.4",
        "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm_BasePconShape.Parameters 0 360 2 -0.015 20.9 29.4 0.015 20.9 29.4",
    )
    text = shift_component(
        text,
        "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
        45.085,
        49.085,
        "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm_NF2_",
    )

    text = replace_once(
        text,
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_FullShellShape.Parameters 0 360 2 -34.45 25.7 26 34.45 25.7 26",
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_FullShellShape.Parameters 0 360 2 -38.45 29.7 30 38.45 29.7 30",
    )
    text = replace_once(
        text,
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_RectWindowCutShape.Parameters 13.0001 1.898 1.898",
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_RectWindowCutShape.Parameters 15.0001 1.898 1.898",
    )
    text = replace_once(
        text,
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_RectWindowCutOrientation.Position -13 0 -15.95",
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm_RectWindowCutOrientation.Position -15 0 -15.95",
    )
    text = add_nf2_mount_reliefs(
        text,
        "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm",
        -23.4779221,
        21.0698052,
    )
    text = replace_once(
        text,
        "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm_BasePconShape.Parameters 0 360 2 -0.15 0 26 0.15 0 26",
        "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm_BasePconShape.Parameters 0 360 2 -0.15 0 30 0.15 0 30",
    )
    text = shift_component(
        text,
        "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
        -24.05,
        -28.05,
        "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm_NF2_",
    )
    text = add_nf2_mount_reliefs(
        text,
        "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
        15.3220779,
        59.8698052,
    )
    text = replace_once(
        text,
        "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm_BasePconShape.Parameters 0 360 2 -0.15 20.9 26 0.15 20.9 26",
        "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm_BasePconShape.Parameters 0 360 2 -0.15 20.9 30 0.15 20.9 30",
    )
    text = shift_component(
        text,
        "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
        45.55,
        49.55,
        "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm_NF2_",
    )
    text = add_nf2_mount_reliefs(
        text,
        "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
        -62.2779221,
        -17.7301948,
    )

    # Passive BPE and the existing active plastic channel are rigidly displaced
    # outwards.  Thicknesses and volume/scorer identities remain unchanged.
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_FullShape.Parameters 0 360 2 -35.25 27 29 35.25 27 29",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_FullShape.Parameters 0 360 2 -39.25 31 33 39.25 31 33",
    )
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm_FullShape.Parameters 0 360 2 -1 0 29 1 0 29",
        "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm_FullShape.Parameters 0 360 2 -1 0 33 1 0 33",
    )
    text = shift_component(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm",
        -25.5,
        -29.5,
        "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm_NF2_",
    )
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm_FullShape.Parameters 0 360 2 -1 0 29 1 0 29",
        "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm_FullShape.Parameters 0 360 2 -1 0 33 1 0 33",
    )
    text = shift_component(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm",
        47.0,
        51.0,
        "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm_NF2_",
    )
    text = add_side_optical_relief(text, "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm", 33.0)

    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_FullShape.Parameters 0 360 2 -37.25 29 30 37.25 29 30",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_FullShape.Parameters 0 360 2 -41.25 33 34 41.25 33 34",
    )
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm_FullShape.Parameters 0 360 2 -0.5 0 30 0.5 0 30",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm_FullShape.Parameters 0 360 2 -0.5 0 34 0.5 0 34",
    )
    text = shift_component(
        text,
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        -27.0,
        -31.0,
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm_NF2_",
    )
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm_FullShape.Parameters 0 360 2 -0.5 0 30 0.5 0 30",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm_FullShape.Parameters 0 360 2 -0.5 0 34 0.5 0 34",
    )
    text = shift_component(
        text,
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
        48.5,
        52.5,
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm_NF2_",
    )
    text = add_side_optical_relief(text, "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm", 34.0)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_geo = output_dir / f"{OUTPUT_STEM}.geo"
    output_geo.write_text(text)
    shutil.copy2(SOURCE_DIR / f"{SOURCE_STEM}.det", output_dir / f"{OUTPUT_STEM}.det")
    shutil.copy2(SOURCE_DIR / f"Intro_{SOURCE_STEM}.geo", output_dir / f"Intro_{SOURCE_STEM}.geo")
    shutil.copy2(SOURCE_DIR / "Materials_DEMO2_DR_v3p5.geo", output_dir / "Materials_DEMO2_DR_v3p5.geo")
    setup = (
        f"Name {OUTPUT_STEM}\n"
        "Version 1\n"
        f"Include {OUTPUT_STEM}.geo\n"
        f"Include {OUTPUT_STEM}.det\n"
        "SurroundingSphere 60 5 0 9 60\n"
    )
    output_setup = output_dir / f"{OUTPUT_STEM}.geo.setup"
    output_setup.write_text(setup)
    return output_setup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_setup = build(args.output_dir)
    print(f"output_setup={output_setup}")
    print("cold_core=exact_baseline")
    print("bgo_added_normal_thickness_cm=4")
    print("top_service_reliefs=12")
    print("nf2_reliefs_per_face=6")
    print("outer_radius_cm=34")


if __name__ == "__main__":
    main()
