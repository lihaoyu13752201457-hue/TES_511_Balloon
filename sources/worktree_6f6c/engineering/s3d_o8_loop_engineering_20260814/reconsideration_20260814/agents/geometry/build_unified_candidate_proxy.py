#!/usr/bin/env python3
"""Build the single S3d-O8 cold-core/partner-catch geometry proxy.

This is a geometry-only generator.  It never launches transport.  The source
package is read-only; the four small Geomega files are materialized under the
requested output directory.
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
OUTPUT_STEM = "S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy"


CU_TO_AL_VOLUMES = {
    *(f"Cu_SubstrateSupport_OpenRing_L{layer}_{face}_panel"
      for layer in range(1, 6) for face in ("ZP", "ZM", "YP", "YM")),
    "Cu_SubstrateSupport_SolidDisk_L0_deepest",
    *(f"Cu_SubstrateSupport_EdgeRod_{index}" for index in range(1, 5)),
    *(f"Cu_ColdFinger_OffAxis_{side}_{end}_from_Disk_to_Stem"
      for side in ("YP", "YM") for end in ("ZP", "ZM")),
    *(f"Cu_ColdFinger_Stem_{side}_{end}_to_MXC"
      for side in ("YP", "YM") for end in ("ZP", "ZM")),
    *(f"Cu_MXC_Clamp_Pad_{side}_{end}_for_OffAxisStem"
      for side in ("YP", "YM") for end in ("ZP", "ZM")),
    "Cu_50mK_StillLike_Can_bottom_cap_2mm",
    "Cu_50mK_StillLike_Can_side_wall_below_side_port",
    "Cu_50mK_StillLike_Can_side_wall_above_side_port",
    "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
    "ColdPlate_MXC_50mK_SD_anchor",
    "ColdPlate_CP_100mK_intercept",
    "ColdPlate_Still_0p7K",
    "ColdPlate_4K",
    "DR_MixingChamber_Cu",
    "DR_Still_Pot_Cu",
    "DR_4K_Condenser_Cu",
}


# Existing top-pipe outer radii at z=40.9--41.9 cm, plus 0.5 mm clearance.
TOP_SERVICE_RELIEFS = (
    ("GasReturn_A", 5.0, 3.2, 1.95),
    ("PumpFill_B", 7.4, -2.8, 1.69),
    ("Vacuum_C", -4.5, 6.5, 1.29),
    # The candidate top extends into the micro-conduits' r=0.9 cm top-sleeve
    # axial envelope; relieve that larger envelope, not only the r=0.64 tube.
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


NF2_RELIEFS = (
    ("01", 23.2447686, 21.0, 24.5155838),
    ("02", -2.47487373, 42.0, -1.20405845),
    ("03", -28.194516, 21.0, -26.9237008),
    ("04", -28.194516, -21.0, -26.9237008),
    ("05", -2.47487373, -42.0, -1.20405845),
    ("06", 23.2447686, -21.0, 24.5155838),
)


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, got {count}: {old}")
    return text.replace(old, new, 1)


def top_service_block(half_height: float) -> tuple[str, str]:
    prefix = "BGO_S3D_O8_FullWrap_TopAnnulus_10mm"
    previous = f"{prefix}_NF2_ReliefStep06Shape"
    lines = ["", "// Candidate: retain the central r<4 cm service opening and relieve all real top pipes."]
    for index, (label, x, y, radius) in enumerate(TOP_SERVICE_RELIEFS, start=1):
        shape = f"{prefix}_Service_{label}_ReliefShape"
        orientation = f"{prefix}_Service_{label}_ReliefOrientation"
        result = f"{prefix}_ServiceReliefStep{index:02d}Shape"
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


def inner_bpe_block() -> str:
    prefix = "Candidate_Inner_BPE5_Liner_5mm"
    lines = [
        "",
        "// Candidate: 5 mm inboard BPE liner in the proxy-clear 20.6--21.2 cm radial gap.",
        f"Shape PCON {prefix}_FullShape",
        f"{prefix}_FullShape.Parameters 0 360 2 -30.15 20.65 21.15 30.15 20.65 21.15",
        f"Shape BRIK {prefix}_SignalWindowReliefShape",
        f"{prefix}_SignalWindowReliefShape.Parameters 10.5751 1.898 1.898",
        f"Orientation {prefix}_SignalWindowReliefOrientation",
        f"{prefix}_SignalWindowReliefOrientation.Position -10.575 0 -15.95",
        f"Shape Subtraction {prefix}_ReliefStep00Shape",
        f"{prefix}_ReliefStep00Shape.Parameters {prefix}_FullShape {prefix}_SignalWindowReliefShape "
        f"{prefix}_SignalWindowReliefOrientation",
        f"Shape BRIK {prefix}_PumpLineReliefShape",
        f"{prefix}_PumpLineReliefShape.Parameters 0.75 0.75 13.25",
        f"Orientation {prefix}_PumpLineReliefOrientation",
        f"{prefix}_PumpLineReliefOrientation.Position 21.4 0 13.95",
        f"Shape Subtraction {prefix}_ReliefStep01Shape",
        f"{prefix}_ReliefStep01Shape.Parameters {prefix}_ReliefStep00Shape {prefix}_PumpLineReliefShape "
        f"{prefix}_PumpLineReliefOrientation",
    ]
    previous = f"{prefix}_ReliefStep01Shape"
    for step, (label, x, y, z) in enumerate(NF2_RELIEFS, start=2):
        shape = f"{prefix}_NF2_Rod{label}_ReliefShape"
        orientation = f"{prefix}_NF2_Rod{label}_ReliefOrientation"
        result = f"{prefix}_ReliefStep{step:02d}Shape"
        lines.extend(
            [
                f"Shape BRIK {shape}",
                f"{shape}.Parameters 2.4 2.4 32",
                f"Orientation {orientation}",
                f"{orientation}.Position {x:.12g} {y:.12g} {z:.12g}",
                f"{orientation}.Rotation 0 -45 0",
                f"Shape Subtraction {result}",
                f"{result}.Parameters {previous} {shape} {orientation}",
            ]
        )
        previous = result
    lines.extend(
        [
            f"Volume {prefix}",
            f"{prefix}.Material BoratedPolyethylene5wtB",
            f"{prefix}.Visibility 1",
            f"{prefix}.Shape {previous}",
            f"{prefix}.Position 0 0 10.75",
            f"{prefix}.Mother InstrumentFrame",
            "",
        ]
    )
    return "\n".join(lines)


def build(top_thickness_cm: float, output_dir: Path) -> None:
    if not 1.0 <= top_thickness_cm <= 4.16:
        raise ValueError("top thickness must preserve z=40.9 inner face and remain below the z=45.07 wrap")

    source_geo = SOURCE_DIR / f"{SOURCE_STEM}.geo"
    text = source_geo.read_text()
    text = replace_once(
        text,
        "// Exact-copy S3c-C0 base; the original side40 block is untouched, bottom/top become 30/10 mm, and only outer W2 is removed.",
        "// Candidate base: side40 and bottom30 remain; top is reprofiled below; outer W2 remains absent.",
    )

    current_volume = None
    changed = set()
    output_lines = []
    volume_re = re.compile(r"^Volume (\S+)$")
    for line in text.splitlines():
        match = volume_re.match(line)
        if match:
            current_volume = match.group(1)
        if current_volume in CU_TO_AL_VOLUMES and line == f"{current_volume}.Material Copper":
            line = f"{current_volume}.Material Aluminium"
            changed.add(current_volume)
        output_lines.append(line)
    if changed != CU_TO_AL_VOLUMES:
        missing = sorted(CU_TO_AL_VOLUMES - changed)
        extra = sorted(changed - CU_TO_AL_VOLUMES)
        raise RuntimeError(f"Cu->Al scope mismatch: missing={missing}, extra={extra}")
    text = "\n".join(output_lines) + "\n"

    # Preserve all inner magnetic-shield surfaces and openings; reduce only the outer faces.
    text = replace_once(
        text,
        "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2",
        "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.05 4.1 4 4.05",
    )
    text = replace_once(
        text,
        "MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.45 4.3 4.25 4.45",
        "MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.3 4.3 4.25 4.3",
    )
    text = replace_once(
        text,
        "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2",
        "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.05 4.15 1.85 4.05",
    )
    text = replace_once(
        text,
        "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.45 4.5 1.85 4.45",
        "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.3 4.35 1.85 4.3",
    )

    half_height = top_thickness_cm / 2.0
    top_center = 40.9 + half_height
    center_shift = top_center - 41.4
    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters "
        "0 360 2 -0.5 20.9 25.2 0.5 20.9 25.2",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_BasePconShape.Parameters "
        f"0 360 2 {-half_height:.12g} 4 25.2 {half_height:.12g} 4 25.2",
    )
    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Position 0 0 41.4",
        f"BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Position 0 0 {top_center:.12g}",
    )
    for label in ("01", "02", "03", "04", "05", "06"):
        pattern = re.compile(
            rf"(BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_Rod{label}_ReliefOrientation\.Position "
            rf"[-+0-9.eE]+ [-+0-9.eE]+ )([-+0-9.eE]+)"
        )
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"missing top NF2 relief position: {label}")
        old_z = float(match.group(2))
        text = text[: match.start()] + match.group(1) + f"{old_z - center_shift:.12g}" + text[match.end() :]

    service_block, final_top_shape = top_service_block(half_height + 0.01)
    marker = "// Volume BGO_S3D_O8_FullWrap_TopAnnulus_10mm; kind=pcon;"
    if text.count(marker) != 1:
        raise RuntimeError("top-BGO insertion marker is not unique")
    candidate_marker = (
        "// Volume BGO_S3D_O8_FullWrap_TopAnnulus_10mm; candidate top catch; "
        f"z=40.9..{40.9 + top_thickness_cm:.12g} cm; r=4..25.2 cm; "
        "legacy volume/channel name retained"
    )
    source_comment_end = text.find("\n", text.index(marker))
    source_comment = text[text.index(marker):source_comment_end]
    text = text.replace(source_comment, service_block + "\n" + candidate_marker, 1)
    text = replace_once(
        text,
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape "
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_NF2_ReliefStep06Shape",
        f"BGO_S3D_O8_FullWrap_TopAnnulus_10mm.Shape {final_top_shape}",
    )

    end_marker = "// END GEOOPT_S3D_O8_FALLBACK_MINPATCH"
    if text.count(end_marker) != 1:
        raise RuntimeError("candidate insertion marker is not unique")
    text = text.replace(end_marker, inner_bpe_block() + "\n" + end_marker, 1)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_geo = output_dir / f"{OUTPUT_STEM}.geo"
    output_geo.write_text(text)
    shutil.copy2(SOURCE_DIR / f"{SOURCE_STEM}.det", output_dir / f"{OUTPUT_STEM}.det")
    shutil.copy2(
        SOURCE_DIR / f"Intro_{SOURCE_STEM}.geo",
        output_dir / f"Intro_{SOURCE_STEM}.geo",
    )
    shutil.copy2(SOURCE_DIR / "Materials_DEMO2_DR_v3p5.geo", output_dir / "Materials_DEMO2_DR_v3p5.geo")
    setup = (
        f"Name {OUTPUT_STEM}\n"
        "Version 1\n"
        f"Include {OUTPUT_STEM}.geo\n"
        f"Include {OUTPUT_STEM}.det\n"
        "SurroundingSphere 60 5 0 9 60\n"
    )
    (output_dir / f"{OUTPUT_STEM}.geo.setup").write_text(setup)

    print(f"output_setup={output_dir / f'{OUTPUT_STEM}.geo.setup'}")
    print(f"cu_to_al_volume_count={len(changed)}")
    print(f"top_thickness_cm={top_thickness_cm:.12g}")
    print("top_inner_radius_cm=4")
    print(f"top_service_relief_count={len(TOP_SERVICE_RELIEFS)}")
    print("inner_bpe_radial_span_cm=20.65,21.15")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-thickness-cm", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build(args.top_thickness_cm, args.output_dir)


if __name__ == "__main__":
    main()
