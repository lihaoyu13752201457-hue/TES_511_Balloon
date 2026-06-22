#!/usr/bin/env python3
"""Build fix5 for the user cylindrical redesign with multihole W.

This candidate keeps the fix4 modeling basis and applies only the requested
review corrections:

1. The 50 mK Cu can is a full-azimuth z-axis Still-like local cold shield
   closed to the 50 mK cold plate, not an x-axis sample sleeve.
2. The x-axis MuMetal/Nb magnetic sleeves keep closed back-side caps with a
   cold-finger clearance hole, but their incident-side cap is a thin Al foil.
3. The side-wall aperture bands use Boolean subtraction with a cut box that
   reaches from outside the shell to the cylinder interior, so the projected
   window is actually open through every cylindrical wall.
4. The CsI bottom/side seam is closed in the simplified mass model.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621"
BASE_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_20260621_megalib_proxy"
OUT_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEO = OUT_DIR / f"{STEM}.geo"
DET = OUT_DIR / f"{STEM}.det"
SETUP = OUT_DIR / f"{STEM}.geo.setup"
MATERIALS = OUT_DIR / "Materials_DEMO2_DR_v3p5.geo"
MANIFEST = WORK / "user_cylmag_redesign_multiholeW_fix5_manifest.json"
MASS_CSV = WORK / "user_cylmag_redesign_multiholeW_fix5_mass_delta.csv"
SUMMARY_MD = WORK / "USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md"
WRL = WORK / "user_cylmag_redesign_multiholeW_fix5.wrl"
XZ_ZOOM_PNG = WORK / "user_cylmag_redesign_multiholeW_fix5_xz_projection_zoom.png"
XZ_ZOOM_SVG = WORK / "user_cylmag_redesign_multiholeW_fix5_xz_projection_zoom.svg"
XZ_FULL_PNG = WORK / "user_cylmag_redesign_multiholeW_fix5_xz_projection_full.png"
XZ_FULL_SVG = WORK / "user_cylmag_redesign_multiholeW_fix5_xz_projection_full.svg"
YZ_FACE_PNG = WORK / "user_cylmag_redesign_multiholeW_fix5_yz_side_window_face.png"
YZ_FACE_SVG = WORK / "user_cylmag_redesign_multiholeW_fix5_yz_side_window_face.svg"
OVERLAP_SOURCE = OUT_DIR / "overlap_check.source"

OLD_EXPORTER = ROOT / "outputs/reports/user_redesign_multiholeW_20260621/export_multiholeW_geo_to_wrl.py"


WINDOW_HALF_CM = 1.898
SIDE_CENTER_Z_CM = -5.2
RECTCUT_EPS_CM = 1.0e-4

CU50_RIN = 7.45
CU50_ROUT = 7.65
CU50_COLD_PLATE_ROUT = 7.80
WIN_50MK_X = -0.5 * (CU50_RIN + CU50_ROUT)
CU50_BOTTOM_ZMIN = -9.90
CU50_BOTTOM_ZMAX = -9.70
CU50_TOP_ZMAX = -0.30

NB_RIN = 4.00
NB_ROUT = 4.20
MUMETAL_RIN = 4.25
MUMETAL_ROUT = 4.45
MAG_BACK_COLD_FINGER_HOLE_RADIUS = 1.85
MAG_CAP_THICK = 0.20
MAG_FRONT_MUMETAL_XMIN = -4.35
MAG_FRONT_NB_XMIN = -3.85
MAG_BACK_NB_XMAX = 4.10
MAG_BACK_MUMETAL_XMAX = 4.30
MAG_INCIDENT_AL_WINDOW_HALF_THICK = 0.00125
MAG_INCIDENT_AL_WINDOW_NAME = "Win_MagShield_Al_foil_side"
MAG_INCIDENT_AL_WINDOW_X = MAG_FRONT_MUMETAL_XMIN - MAG_INCIDENT_AL_WINDOW_HALF_THICK
CSI_SIDE_BOTTOM_Z_CM = -14.40

DENSITY = {
    "Aluminium": 2.70,
    "Copper": 8.96,
    "Nb": 8.57,
    "MuMetal": 8.70,
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(value: float) -> str:
    if abs(value) < 5.0e-10:
        value = 0.0
    return f"{value:.9g}"


def pcon(phi0: float, dphi: float, z0: float, rin: float, rout: float, z1: float) -> str:
    return f"PCON {fmt(phi0)} {fmt(dphi)} 2 {fmt(z0)} {fmt(rin)} {fmt(rout)} {fmt(z1)} {fmt(rin)} {fmt(rout)}"


def brik(hx: float, hy: float, hz: float) -> str:
    return f"BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}"


def volume_blocks(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^Volume\s+(\S+)\s*$", text))
    blocks: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        prefix_start = text.rfind("\n// Volume ", 0, start)
        if prefix_start != -1 and prefix_start >= text.rfind("\n\n", 0, start):
            start = prefix_start + 1
        blocks[match.group(1)] = text[start:end]
    return blocks


def remove_blocks(text: str, names: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        maybe_comment = re.match(r"^// Volume\s+(\S+)", line)
        if maybe_comment and i + 1 < len(lines):
            maybe_volume = re.match(r"^Volume\s+(\S+)\s*$", lines[i + 1])
            if maybe_volume and maybe_volume.group(1) in names:
                i += 2
                while i < len(lines) and not re.match(r"^(// Volume\s+|Volume\s+)", lines[i]):
                    i += 1
                continue

        maybe_volume = re.match(r"^Volume\s+(\S+)\s*$", line)
        if maybe_volume and maybe_volume.group(1) in names:
            i += 1
            while i < len(lines) and not re.match(r"^(// Volume\s+|Volume\s+)", lines[i]):
                i += 1
            continue

        out.append(line)
        i += 1
    return "".join(out)


def replace_shape(text: str, name: str, shape: str, position: str | None = None) -> str:
    text, count = re.subn(
        rf"(?m)^({re.escape(name)}\.Shape)\s+.+$",
        rf"\1 {shape}",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"shape line not found for {name}")
    if position is not None:
        text, pcount = re.subn(
            rf"(?m)^({re.escape(name)}\.Position)\s+.+$",
            rf"\1 {position}",
            text,
            count=1,
        )
        if pcount != 1:
            raise RuntimeError(f"position line not found for {name}")
    return text


def replace_position(text: str, name: str, position: str) -> str:
    text, count = re.subn(
        rf"(?m)^({re.escape(name)}\.Position)\s+.+$",
        rf"\1 {position}",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"position line not found for {name}")
    return text


def shape_values(text: str, name: str) -> list[float]:
    match = re.search(rf"(?m)^{re.escape(name)}\.Shape\s+PCON\s+(.+)$", text)
    if match is None:
        raise RuntimeError(f"PCON shape not found for {name}")
    return [float(item) for item in match.group(1).split()]


def flush_half_gap_from_inner(rin: float) -> float:
    ratio = min(0.999, WINDOW_HALF_CM / rin)
    return math.degrees(math.asin(ratio))


def set_band_window(text: str, name: str, phi0: float, dphi: float, zhalf: float = WINDOW_HALF_CM) -> str:
    vals = shape_values(text, name)
    if int(vals[2]) != 2:
        raise RuntimeError(f"expected two-plane PCON for {name}")
    vals[0] = phi0
    vals[1] = dphi
    vals[3] = -zhalf
    vals[6] = zhalf
    return replace_shape(text, name, "PCON " + " ".join(fmt(v) for v in vals))


def flush_full360_side_group(text: str, prefix: str) -> str:
    band0 = f"{prefix}_side_port_band_00"
    band1 = f"{prefix}_side_port_band_01"
    rin = shape_values(text, band0)[4]
    gap = flush_half_gap_from_inner(rin)
    dphi = 180.0 - gap
    text = set_band_window(text, band0, 0.0, dphi)
    text = set_band_window(text, band1, 180.0 + gap, dphi)
    return text


def flush_csi_segment(text: str, seg: int) -> str:
    prefix = f"CsI_Side_Segment_{seg:02d}"
    band = f"{prefix}_side_port_band_00"
    rin = shape_values(text, band)[4]
    gap = flush_half_gap_from_inner(rin)
    if seg == 3:
        phi0 = 135.0
        dphi = 180.0 - gap - phi0
    elif seg == 4:
        phi0 = 180.0 + gap
        dphi = 225.0 - phi0
    else:
        raise ValueError(seg)
    return set_band_window(text, band, phi0, dphi)


def z_pcon_volume(name: str, material: str, shape: str, position: tuple[float, float, float]) -> str:
    return "\n".join(
        [
            f"// Fix5: {name}; material={material}",
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape {shape}",
            f"{name}.Position {fmt(position[0])} {fmt(position[1])} {fmt(position[2])}",
            f"{name}.Mother InstrumentFrame",
            "",
        ]
    )


def z_segment(name: str, material: str, rin: float, rout: float, zmin: float, zmax: float) -> str:
    half = 0.5 * (zmax - zmin)
    center = 0.5 * (zmin + zmax)
    return z_pcon_volume(name, material, pcon(0, 360, -half, rin, rout, half), (0, 0, center))


def x_pcon_volume(name: str, material: str, rin: float, rout: float, x0: float, x1: float) -> str:
    return "\n".join(
        [
            f"// Fix5: {name}; material={material}",
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape {pcon(0, 360, x0, rin, rout, x1)}",
            f"{name}.Position 0 0 {fmt(SIDE_CENTER_Z_CM)}",
            f"{name}.Rotation 0 90 0",
            f"{name}.Mother InstrumentFrame",
            "",
        ]
    )


def rectcut_side_band_volume(
    name: str,
    material: str,
    phi0: float,
    dphi: float,
    rin: float,
    rout: float,
    zhalf: float = WINDOW_HALF_CM,
    zcenter: float = SIDE_CENTER_Z_CM,
) -> str:
    """Cylindrical side band with an exact projected square side-window cut.

    The subtraction box is local to the cylindrical band volume.  It spans the
    whole -x shell chord from outside the wall to just past the cylinder
    centerline and has y/z half-size equal to the window half-size.  This keeps
    the same projected window boundary while guaranteeing that the curved shell
    is cut through its full thickness for every y point inside the aperture.
    """
    base = f"{name}_FullShellShape"
    cut = f"{name}_RectWindowCutShape"
    orient = f"{name}_RectWindowCutOrientation"
    sub = f"{name}_RectWindowSubtractionShape"
    cut_x_min = -rout - RECTCUT_EPS_CM
    cut_x_max = RECTCUT_EPS_CM
    xcenter = 0.5 * (cut_x_min + cut_x_max)
    hx = 0.5 * (cut_x_max - cut_x_min)
    return "\n".join(
        [
            f"// Fix5 Boolean shape for {name}: full side band minus rectangular through-window.",
            f"Shape PCON {base}",
            f"{base}.Parameters 0 360 2 {-zhalf:g} {rin:g} {rout:g} {zhalf:g} {rin:g} {rout:g}"
            if abs(dphi - 360.0) < 1.0e-9 and abs(phi0) < 1.0e-9
            else f"{base}.Parameters {phi0:g} {dphi:g} 2 {-zhalf:g} {rin:g} {rout:g} {zhalf:g} {rin:g} {rout:g}",
            f"Shape BRIK {cut}",
            f"{cut}.Parameters {hx:g} {WINDOW_HALF_CM:g} {zhalf:g}",
            f"Orientation {orient}",
            f"{orient}.Position {xcenter:g} 0 0",
            f"Shape Subtraction {sub}",
            f"{sub}.Parameters {base} {cut} {orient}",
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape {sub}",
            f"{name}.Position 0 0 {zcenter:g}",
            f"{name}.Mother InstrumentFrame",
            "",
        ]
    )


def x_cap_panel(name: str, material: str, x: float, y: float, z: float, hx: float, hy: float, hz: float) -> str:
    return "\n".join(
        [
            f"// Fix5 magnetic/window panel: {name}; material={material}",
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape {brik(hx, hy, hz)}",
            f"{name}.Position {fmt(x)} {fmt(y)} {fmt(z)}",
            f"{name}.Mother InstrumentFrame",
            "",
        ]
    )


def square_hole_cap_panels(
    prefix: str,
    material: str,
    x_center: float,
    outer_half: float,
    hole_half: float,
    thickness: float = MAG_CAP_THICK,
) -> tuple[str, list[str]]:
    if hole_half >= outer_half:
        raise ValueError("hole must be smaller than cap outer half-size")
    hx = thickness / 2.0
    side_half = (outer_half - hole_half) / 2.0
    side_center = (outer_half + hole_half) / 2.0
    names = [
        f"{prefix}_ZP_panel",
        f"{prefix}_ZM_panel",
        f"{prefix}_YP_panel",
        f"{prefix}_YM_panel",
    ]
    text = "\n".join(
        [
            x_cap_panel(names[0], material, x_center, 0, SIDE_CENTER_Z_CM + side_center, hx, outer_half, side_half),
            x_cap_panel(names[1], material, x_center, 0, SIDE_CENTER_Z_CM - side_center, hx, outer_half, side_half),
            x_cap_panel(names[2], material, x_center, side_center, SIDE_CENTER_Z_CM, hx, side_half, hole_half),
            x_cap_panel(names[3], material, x_center, -side_center, SIDE_CENTER_Z_CM, hx, side_half, hole_half),
        ]
    )
    return text, names


def cu50_still_like_block() -> tuple[str, list[str]]:
    names = [
        "Cu_50mK_StillLike_Can_bottom_cap_2mm",
        "Cu_50mK_StillLike_Can_side_wall_below_side_port",
        "Cu_50mK_StillLike_Can_side_wall_above_side_port",
        "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
    ]
    side_zmin = SIDE_CENTER_Z_CM - WINDOW_HALF_CM
    side_zmax = SIDE_CENTER_Z_CM + WINDOW_HALF_CM
    above_half = 0.5 * (CU50_TOP_ZMAX - side_zmax)
    above_center = 0.5 * (CU50_TOP_ZMAX + side_zmax)
    block = "\n".join(
        [
            "// Fix5: 50 mK Cu can is modeled as a full-azimuth z-axis Still-like local cold shield.",
            "// Its top edge touches the 50 mK MXC cold plate lower face at z=-0.3 cm.",
            "// Its radius is placed outside the existing cold-finger clamp/stem envelope so no side-wall notch is needed.",
            z_pcon_volume(
                names[0],
                "Copper",
                pcon(0, 360, -0.1, 0, CU50_ROUT, 0.1),
                (0, 0, 0.5 * (CU50_BOTTOM_ZMIN + CU50_BOTTOM_ZMAX)),
            ),
            z_segment(names[1], "Copper", CU50_RIN, CU50_ROUT, CU50_BOTTOM_ZMAX, side_zmin),
            z_pcon_volume(
                names[2],
                "Copper",
                pcon(
                    0.0,
                    360.0,
                    -above_half,
                    CU50_RIN,
                    CU50_ROUT,
                    above_half,
                ),
                (0, 0, above_center),
            ),
            rectcut_side_band_volume(
                names[3],
                "Copper",
                0.0,
                360.0,
                CU50_RIN,
                CU50_ROUT,
            ),
        ]
    )
    return block + "\n", names


def close_csi_bottom_side_seam(text: str) -> str:
    """Close the simplified CsI bottom/side seam without adding engineering detail."""
    full_side_segments = [0, 1, 2, 5, 6, 7]
    full_center_z = -6.10
    full_zmin_local = CSI_SIDE_BOTTOM_Z_CM - full_center_z
    for seg in full_side_segments:
        name = f"CsI_Side_Segment_{seg:02d}"
        text = replace_shape(text, name, pcon(seg * 45.0, 45.0, full_zmin_local, 14.0, 18.0, 8.1))

    below_center_z = -10.649
    below_zmin_local = CSI_SIDE_BOTTOM_Z_CM - below_center_z
    for seg in (3, 4):
        name = f"CsI_Side_Segment_{seg:02d}_below_side_port"
        text = replace_shape(text, name, pcon(seg * 45.0, 45.0, below_zmin_local, 14.0, 18.0, 3.551))
    return text


def magnetic_incident_al_window_block() -> str:
    return x_cap_panel(
        MAG_INCIDENT_AL_WINDOW_NAME,
        "Aluminium",
        MAG_INCIDENT_AL_WINDOW_X,
        0.0,
        SIDE_CENTER_Z_CM,
        MAG_INCIDENT_AL_WINDOW_HALF_THICK,
        WINDOW_HALF_CM,
        WINDOW_HALF_CM,
    )


def side_band_replacement_blocks() -> tuple[str, list[str], set[str], list[dict[str, object]]]:
    specs = [
        {
            "new": "Still_Shield_Al_side_window_side_wall_rectcut_window_band",
            "material": "Aluminium",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 8.5,
            "rout": 8.8,
            "old": [
                "Still_Shield_Al_side_window_side_wall_side_port_band_00",
                "Still_Shield_Al_side_window_side_wall_side_port_band_01",
            ],
        },
        {
            "new": "Shield_4K_Al_side_window_side_wall_rectcut_window_band",
            "material": "Aluminium",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 9.9,
            "rout": 10.2,
            "old": [
                "Shield_4K_Al_side_window_side_wall_side_port_band_00",
                "Shield_4K_Al_side_window_side_wall_side_port_band_01",
            ],
        },
        {
            "new": "Shield_60K_Al_side_window_side_wall_rectcut_window_band",
            "material": "Aluminium",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 11.4,
            "rout": 11.7,
            "old": [
                "Shield_60K_Al_side_window_side_wall_side_port_band_00",
                "Shield_60K_Al_side_window_side_wall_side_port_band_01",
            ],
        },
        {
            "new": "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_rectcut_window_band",
            "material": "Aluminium",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 12.9,
            "rout": 13.4,
            "old": [
                "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_side_port_band_00",
                "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_side_port_band_01",
            ],
        },
        {
            "new": "CsI_Side_Segment_03_rectcut_window_band",
            "material": "CsI",
            "phi0": 135.0,
            "dphi": 45.0,
            "rin": 14.0,
            "rout": 18.0,
            "old": ["CsI_Side_Segment_03_side_port_band_00"],
        },
        {
            "new": "CsI_Side_Segment_04_rectcut_window_band",
            "material": "CsI",
            "phi0": 180.0,
            "dphi": 45.0,
            "rin": 14.0,
            "rout": 18.0,
            "old": ["CsI_Side_Segment_04_side_port_band_00"],
        },
        {
            "new": "ActiveShield_Flex_Kapton_detector_bay_rectcut_window_band",
            "material": "Kapton",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 18.17,
            "rout": 18.2,
            "old": [
                "ActiveShield_Flex_Kapton_detector_bay_side_port_band_00",
                "ActiveShield_Flex_Kapton_detector_bay_side_port_band_01",
            ],
        },
        {
            "new": "Outer_Al_Mechanical_Shell_detector_bay_side_wall_rectcut_window_band",
            "material": "Aluminium",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": 18.3,
            "rout": 19.1,
            "old": [
                "Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_00",
                "Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01",
            ],
        },
    ]
    blocks = []
    new_names: list[str] = []
    old_names: set[str] = set()
    for spec in specs:
        new_names.append(str(spec["new"]))
        old_names.update(str(name) for name in spec["old"])
        blocks.append(
            rectcut_side_band_volume(
                str(spec["new"]),
                str(spec["material"]),
                float(spec["phi0"]),
                float(spec["dphi"]),
                float(spec["rin"]),
                float(spec["rout"]),
            )
        )
    return "\n".join(blocks) + "\n", new_names, old_names, specs


def scintillator_block(volume: str) -> str:
    name = f"{volume}_SD"
    return "\n".join(
        [
            f"Scintillator {name}",
            f"{name}.SensitiveVolume {volume}",
            f"{name}.DetectorVolume {volume}",
            f"{name}.TriggerThreshold 0.001",
            f"{name}.EnergyResolution Gauss 0.001 0.001 1",
            f"{name}.EnergyResolution Gauss 3000 3000 1",
            "",
        ]
    )


def remove_detector_blocks(text: str, volumes: set[str]) -> str:
    pattern = re.compile(
        r"(?ms)^(Scintillator|MDCalorimeter)\s+\S+\n.*?(?=\n\n(?:Scintillator|MDCalorimeter)\s+|\n// Native|\Z)"
    )

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        for volume in volumes:
            if re.search(rf"(?m)\.SensitiveVolume\s+{re.escape(volume)}\s*$", block):
                return ""
        return block

    return pattern.sub(repl, text)


def modify_geo() -> dict[str, object]:
    text = GEO.read_text(encoding="utf-8")
    old_cu = {"Cu_50mK_Local_Can_Cylinder_2mm"}
    side_block, side_new_names, side_old_names, side_specs = side_band_replacement_blocks()
    removed_volumes = set(old_cu) | side_old_names
    text = remove_blocks(text, removed_volumes)
    text = re.sub(
        r"(?m)^// User cylindrical redesign: Cu_50mK_Local_Can_Cylinder_2mm; material=Copper\n",
        "",
        text,
    )

    added_volumes: list[str] = []
    cu50_block, cu50_names = cu50_still_like_block()
    added_volumes.extend(cu50_names)
    added_volumes.extend(side_new_names)

    sleeve_limits = {
        "Nb_MagShield_Inner_Cylinder_2mm": (MAG_FRONT_NB_XMIN, MAG_BACK_NB_XMAX),
        "MuMetal_MagShield_Outer_Cylinder_2mm": (MAG_FRONT_MUMETAL_XMIN, MAG_BACK_MUMETAL_XMAX),
    }
    for sleeve, (xmin, xmax) in sleeve_limits.items():
        vals = shape_values(text, sleeve)
        vals[3] = xmin
        vals[6] = xmax
        text = replace_shape(text, sleeve, "PCON " + " ".join(fmt(v) for v in vals))

    cap_specs = [
        (
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
            "Nb",
            MAG_BACK_COLD_FINGER_HOLE_RADIUS,
            NB_ROUT,
            MAG_BACK_NB_XMAX,
            MAG_BACK_NB_XMAX + MAG_CAP_THICK,
        ),
        (
            "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm",
            "MuMetal",
            MAG_BACK_COLD_FINGER_HOLE_RADIUS,
            MUMETAL_ROUT,
            MAG_BACK_MUMETAL_XMAX,
            MAG_BACK_MUMETAL_XMAX + MAG_CAP_THICK,
        ),
    ]
    mag_blocks = [x_pcon_volume(name, material, rin, rout, x0, x1) for name, material, rin, rout, x0, x1 in cap_specs]
    cap_names = [name for name, *_ in cap_specs]
    added_volumes.extend(cap_names)
    mag_window_block = magnetic_incident_al_window_block()
    added_volumes.append(MAG_INCIDENT_AL_WINDOW_NAME)

    marker = "// Volume ColdPlate_MXC_50mK_SD_anchor; material=Copper"
    if marker not in text:
        raise RuntimeError("cold plate insertion marker not found")
    text = text.replace(marker, cu50_block + "\n".join(mag_blocks) + "\n" + mag_window_block + marker, 1)
    side_marker = "// Volume Win_50mK_Al_foil_side; material=Aluminium"
    if side_marker not in text:
        raise RuntimeError("50 mK side window insertion marker not found")
    text = text.replace(side_marker, side_block + side_marker, 1)
    text = replace_position(text, "Win_50mK_Al_foil_side", f"{fmt(WIN_50MK_X)} 0 {fmt(SIDE_CENTER_Z_CM)}")
    text = replace_shape(
        text,
        "ColdPlate_MXC_50mK_SD_anchor",
        pcon(0.0, 360.0, -0.3, 0.0, CU50_COLD_PLATE_ROUT, 0.3),
    )
    text = close_csi_bottom_side_seam(text)

    GEO.write_text(text, encoding="utf-8")
    return {
        "removed_volumes": sorted(removed_volumes),
        "added_volumes": added_volumes,
        "changed_existing_volumes": [
            "Win_50mK_Al_foil_side",
            "ColdPlate_MXC_50mK_SD_anchor",
            "CsI_Side_Segment_00",
            "CsI_Side_Segment_01",
            "CsI_Side_Segment_02",
            "CsI_Side_Segment_03_below_side_port",
            "CsI_Side_Segment_04_below_side_port",
            "CsI_Side_Segment_05",
            "CsI_Side_Segment_06",
            "CsI_Side_Segment_07",
        ],
        "side_wall_opening_model": "Boolean rectcut: full cylindrical side band minus BRIK through-window box with y/z half-size 1.898 cm and x extent from outside shell to cylinder center.",
        "side_wall_rectcut_replacements": side_specs,
        "cu50_can": {
            "model": "z-axis Still-like Copper local cold shield",
            "rin_cm": CU50_RIN,
            "rout_cm": CU50_ROUT,
            "side_window_x_cm": WIN_50MK_X,
            "bottom_z_range_cm": [CU50_BOTTOM_ZMIN, CU50_BOTTOM_ZMAX],
            "top_edge_z_cm": CU50_TOP_ZMAX,
            "cold_plate_rout_cm": CU50_COLD_PLATE_ROUT,
            "closed_by": "ColdPlate_MXC_50mK_SD_anchor lower face at z=-0.3 cm",
        },
        "magnetic_caps": {
            "incident_side": f"open magnetic science aperture with thin Aluminium foil {MAG_INCIDENT_AL_WINDOW_NAME}; no MuMetal/Nb incident cap in the line of sight",
            "incident_al_foil_x_cm": MAG_INCIDENT_AL_WINDOW_X,
            "incident_al_foil_half_thickness_cm": MAG_INCIDENT_AL_WINDOW_HALF_THICK,
            "back_cold_finger_hole_radius_cm": MAG_BACK_COLD_FINGER_HOLE_RADIUS,
            "back_nb_xmax_cm": MAG_BACK_NB_XMAX,
            "back_mumetal_xmax_cm": MAG_BACK_MUMETAL_XMAX,
            "front_mumetal_xmin_cm": MAG_FRONT_MUMETAL_XMIN,
            "front_nb_xmin_cm": MAG_FRONT_NB_XMIN,
            "cap_thickness_cm": MAG_CAP_THICK,
        },
        "csi_bottom_side_seam": {
            "model": "side CsI lower edges moved to touch the bottom CsI upper face",
            "bottom_top_z_cm": CSI_SIDE_BOTTOM_Z_CM,
            "side_inner_outer_r_cm": [14.0, 18.0],
        },
    }


def modify_det(removed_volumes: set[str], added_volumes: list[str]) -> dict[str, object]:
    text = DET.read_text(encoding="utf-8")
    text = remove_detector_blocks(text, removed_volumes)
    new_blocks = "".join(scintillator_block(volume) for volume in added_volumes)
    marker = "// Native MEGAlib Trigger/Veto blocks intentionally absent in this proxy scaffold."
    if marker in text:
        text = text.replace(marker, new_blocks + marker, 1)
    else:
        text = text.rstrip() + "\n\n" + new_blocks
    DET.write_text(text, encoding="utf-8")
    return {
        "removed_detector_sensitive_volumes": sorted(removed_volumes),
        "added_detector_sensitive_volumes": added_volumes,
    }


def shell_volume_kg(rin: float, rout: float, zmin: float, zmax: float, material: str) -> float:
    return math.pi * (rout * rout - rin * rin) * (zmax - zmin) * DENSITY[material] / 1000.0


def disk_volume_kg(rin: float, rout: float, thickness: float, material: str) -> float:
    return math.pi * (rout * rout - rin * rin) * thickness * DENSITY[material] / 1000.0


def panel_volume_kg(hx: float, hy: float, hz: float, material: str, count: int = 1) -> float:
    return count * (8.0 * hx * hy * hz) * DENSITY[material] / 1000.0


def rect_window_cut_mass_kg(rin: float, rout: float, material: str) -> float:
    return (rout - rin) * (2.0 * WINDOW_HALF_CM) * (2.0 * WINDOW_HALF_CM) * DENSITY[material] / 1000.0


def write_mass_delta() -> list[dict[str, object]]:
    cu50_mass = (
        disk_volume_kg(0, CU50_ROUT, CU50_BOTTOM_ZMAX - CU50_BOTTOM_ZMIN, "Copper")
        + shell_volume_kg(CU50_RIN, CU50_ROUT, CU50_BOTTOM_ZMAX, SIDE_CENTER_Z_CM - WINDOW_HALF_CM, "Copper")
        + shell_volume_kg(CU50_RIN, CU50_ROUT, SIDE_CENTER_Z_CM + WINDOW_HALF_CM, CU50_TOP_ZMAX, "Copper")
        + shell_volume_kg(CU50_RIN, CU50_ROUT, SIDE_CENTER_Z_CM - WINDOW_HALF_CM, SIDE_CENTER_Z_CM + WINDOW_HALF_CM, "Copper")
        - rect_window_cut_mass_kg(CU50_RIN, CU50_ROUT, "Copper")
    )
    def cap_mass(outer: float, hole: float, material: str) -> float:
        return disk_volume_kg(hole, outer, MAG_CAP_THICK, material)

    rows = [
        {
            "component": "Cu_50mK_Local_Can_Cylinder_2mm",
            "material": "Copper",
            "change": "removed incorrect x-axis open sleeve",
            "baseline_mass_kg_est": shell_volume_kg(4.5, 4.7, -6.6, 5.5, "Copper"),
            "candidate_mass_kg_est": 0.0,
        },
        {
            "component": "Cu_50mK_StillLike_Can",
            "material": "Copper",
            "change": "added z-axis 2 mm Still-like can closed to 50 mK cold plate with Boolean rectangular side window",
            "baseline_mass_kg_est": 0.0,
            "candidate_mass_kg_est": cu50_mass,
        },
        {
            "component": "Nb magnetic end caps",
            "material": "Nb",
            "change": "added back cold-finger-hole cap only; incident side left open behind thin Al window",
            "baseline_mass_kg_est": 0.0,
            "candidate_mass_kg_est": cap_mass(NB_ROUT, MAG_BACK_COLD_FINGER_HOLE_RADIUS, "Nb"),
        },
        {
            "component": "MuMetal magnetic end caps",
            "material": "MuMetal",
            "change": "added back cold-finger-hole cap only; incident side left open behind thin Al window",
            "baseline_mass_kg_est": 0.0,
            "candidate_mass_kg_est": disk_volume_kg(MAG_BACK_COLD_FINGER_HOLE_RADIUS, MUMETAL_ROUT, MAG_CAP_THICK, "MuMetal"),
        },
        {
            "component": MAG_INCIDENT_AL_WINDOW_NAME,
            "material": "Aluminium",
            "change": "added thin Al incident foil for magnetic-shield aperture",
            "baseline_mass_kg_est": 0.0,
            "candidate_mass_kg_est": panel_volume_kg(
                MAG_INCIDENT_AL_WINDOW_HALF_THICK,
                WINDOW_HALF_CM,
                WINDOW_HALF_CM,
                "Aluminium",
            ),
        },
    ]
    for row in rows:
        row["delta_kg_est"] = row["candidate_mass_kg_est"] - row["baseline_mass_kg_est"]
    with MASS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_overlap_source() -> None:
    OVERLAP_SOURCE.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {SETUP}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                "Minimum.FileName            /tmp/DelMe_user_multiholeW_fix5_overlap",
                "Minimum.NEvents             1",
                "Minimum.Source MinimumS",
                "MinimumS.ParticleType       1",
                "MinimumS.Beam               PointSource 0 0 0",
                "MinimumS.Spectrum           Mono 511",
                "MinimumS.Flux               1.0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def load_exporter():
    spec = importlib.util.spec_from_file_location("fix5_geo_exporter", OLD_EXPORTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {OLD_EXPORTER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEOM_DIR = OUT_DIR
    module.INTRO = OUT_DIR / f"Intro_{STEM}.geo"
    module.GEO = GEO
    module.OUT = WRL
    return module


def angle_in_span(phi: float, phi0: float, dphi: float) -> bool:
    phi = phi % 360.0
    start = phi0 % 360.0
    end = (phi0 + dphi) % 360.0
    if abs(dphi) >= 359.999:
        return True
    if start <= end:
        return start - 1.0e-9 <= phi <= end + 1.0e-9
    return phi >= start - 1.0e-9 or phi <= end + 1.0e-9


def subtract_interval(interval: tuple[float, float], hole: tuple[float, float]) -> list[tuple[float, float]]:
    a, b = interval
    h0, h1 = hole
    if b <= h0 or a >= h1:
        return [(a, b)]
    out = []
    if a < h0:
        out.append((a, h0))
    if h1 < b:
        out.append((h1, b))
    return [(x, y) for x, y in out if y - x > 1.0e-6]


def rectcut_side_band_mesh(
    phi0: float,
    dphi: float,
    rin: float,
    rout: float,
    zhalf: float = WINDOW_HALF_CM,
    zcenter: float = SIDE_CENTER_Z_CM,
) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    """Visualization mesh for the Boolean rectcut side band."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    def add_vertex(p: tuple[float, float, float]) -> int:
        vertices.append((p[0], p[1], p[2] + zcenter))
        return len(vertices) - 1

    def add_cyl_surface(radius: float, outward: bool) -> None:
        half_gap = math.degrees(math.asin(min(0.999999, WINDOW_HALF_CM / radius)))
        if abs(dphi) >= 359.999:
            base_intervals = [(0.0, 360.0)]
        else:
            base_intervals = [(phi0, phi0 + dphi)]
        intervals: list[tuple[float, float]] = []
        for interval in base_intervals:
            intervals.extend(subtract_interval(interval, (180.0 - half_gap, 180.0 + half_gap)))
        for start, end in intervals:
            steps = max(2, int(abs(end - start) / 4.0) + 1)
            prev = None
            for i in range(steps + 1):
                phi = math.radians(start + (end - start) * i / steps)
                x = radius * math.cos(phi)
                y = radius * math.sin(phi)
                pair = (add_vertex((x, y, -zhalf)), add_vertex((x, y, zhalf)))
                if prev is not None:
                    face = [prev[0], pair[0], pair[1], prev[1]]
                    faces.append(face if outward else list(reversed(face)))
                prev = pair

    def add_window_side(sign: float) -> None:
        # sign=+1 is +y boundary (phi<180), sign=-1 is -y boundary (phi>180).
        mid_r = 0.5 * (rin + rout)
        delta = math.degrees(math.asin(min(0.999999, WINDOW_HALF_CM / mid_r)))
        phi_mid = 180.0 - sign * delta
        if not angle_in_span(phi_mid, phi0, dphi):
            return
        steps = 10
        prev = None
        for i in range(steps + 1):
            r = rin + (rout - rin) * i / steps
            x = -math.sqrt(max(0.0, r * r - WINDOW_HALF_CM * WINDOW_HALF_CM))
            y = sign * WINDOW_HALF_CM
            pair = (add_vertex((x, y, -zhalf)), add_vertex((x, y, zhalf)))
            if prev is not None:
                faces.append([prev[0], pair[0], pair[1], prev[1]])
            prev = pair

    add_cyl_surface(rout, True)
    add_cyl_surface(rin, False)
    add_window_side(+1.0)
    add_window_side(-1.0)
    return vertices, faces


def boolean_side_band_specs() -> list[dict[str, object]]:
    specs = [
        {
            "new": "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
            "material": "Copper",
            "phi0": 0.0,
            "dphi": 360.0,
            "rin": CU50_RIN,
            "rout": CU50_ROUT,
        }
    ]
    specs.extend(side_band_replacement_blocks()[3])
    return specs


def instrument_frame_matrix(module):
    objs = module.parse_files([module.INTRO, module.GEO])
    if "InstrumentFrame" not in objs:
        return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    return module.global_matrix("InstrumentFrame", objs, {})


def write_wrl() -> None:
    module = load_exporter()
    module.main()
    frame_matrix = instrument_frame_matrix(module)
    additions = [
        "",
        "# Fix5 Boolean rectcut side-window bands appended by build script.",
        "# These meshes visualize the .geo Subtraction shapes whose projected aperture is 3.796 cm x 3.796 cm.",
        "# They are defined in InstrumentFrame-local coordinates and transformed to world coordinates here,",
        "# including InstrumentFrame.Rotation 0 45 0 from the Intro geometry.",
    ]
    for spec in boolean_side_band_specs():
        vertices, faces = rectcut_side_band_mesh(
            float(spec["phi0"]),
            float(spec["dphi"]),
            float(spec["rin"]),
            float(spec["rout"]),
        )
        vertices = [module.apply(frame_matrix, vertex) for vertex in vertices]
        additions.append(module.shape_record(str(spec["new"]), str(spec["material"]), 1, vertices, faces))
    with WRL.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(additions) + "\n")


def projected_segments(module):
    objs = module.parse_files([module.INTRO, module.GEO])
    memo = {}
    segments_by_material: dict[str, list[list[tuple[float, float]]]] = {}
    for name in sorted(objs):
        obj = objs[name]
        if obj.material == "Vacuum" and not name.startswith("W_Multihole_CollimatorVac"):
            continue
        mesh = module.mesh_for(obj)
        if mesh is None:
            continue
        vertices, faces = mesh
        matrix = module.global_matrix(name, objs, memo)
        projected = []
        for vertex in vertices:
            x, _y, z = module.apply(matrix, vertex)
            projected.append((x, z))
        bucket = segments_by_material.setdefault(obj.material, [])
        for face in faces:
            if len(face) < 2:
                continue
            for idx, a in enumerate(face):
                b = face[(idx + 1) % len(face)]
                bucket.append([projected[a], projected[b]])
    for spec in boolean_side_band_specs():
        vertices, faces = rectcut_side_band_mesh(
            float(spec["phi0"]),
            float(spec["dphi"]),
            float(spec["rin"]),
            float(spec["rout"]),
        )
        frame_matrix = module.global_matrix("InstrumentFrame", objs, memo) if "InstrumentFrame" in objs else None
        if frame_matrix is not None:
            vertices = [module.apply(frame_matrix, vertex) for vertex in vertices]
        projected = [(x, z) for x, _y, z in vertices]
        bucket = segments_by_material.setdefault(str(spec["material"]), [])
        for face in faces:
            if len(face) < 2:
                continue
            for idx, a in enumerate(face):
                b = face[(idx + 1) % len(face)]
                bucket.append([projected[a], projected[b]])
    return segments_by_material


def write_projection(path_png: Path, path_svg: Path, title: str, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
    module = load_exporter()
    segments_by_material = projected_segments(module)
    fig, ax = plt.subplots(figsize=(12, 7))
    priority = {
        "CsI": 4,
        "Aluminium": 3,
        "Copper": 5,
        "Nb": 6,
        "MuMetal": 6,
        "W": 8,
        "Be": 7,
        "Ta": 7,
        "Silicon": 6,
        "Kapton": 5,
    }
    for material, segments in sorted(segments_by_material.items(), key=lambda item: priority.get(item[0], 1)):
        if not segments:
            continue
        r, g, b, alpha = module.COLORS.get(material, (0.6, 0.6, 0.6, 0.55))
        color = (r, g, b, min(0.85, max(0.16, 1.0 - alpha)))
        lw = 0.18
        if material in {"W", "Nb", "MuMetal", "Copper"}:
            lw = 0.35
        if material == "CsI":
            lw = 0.28
        ax.add_collection(LineCollection(segments, colors=[color], linewidths=lw, label=material))
    ax.axhline(SIDE_CENTER_Z_CM, color="black", lw=0.55, ls="--", alpha=0.65)
    ax.axvline(-18.7, color="black", lw=0.45, ls=":", alpha=0.55)
    ax.set_title(title)
    ax.set_xlabel("x / side-entry axis (cm)")
    ax.set_ylabel("z (cm)")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.18)
    handles, labels = ax.get_legend_handles_labels()
    uniq = {}
    for handle, label in zip(handles, labels):
        uniq.setdefault(label, handle)
    ax.legend(uniq.values(), uniq.keys(), loc="upper right", fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(path_png, dpi=220)
    fig.savefig(path_svg)
    plt.close(fig)


def write_side_window_face_detail() -> None:
    module = load_exporter()
    fig, ax = plt.subplots(figsize=(7, 7))
    half = WINDOW_HALF_CM
    layers = [
        ("50mK Cu", "Copper", 0.00),
        ("Still Al", "Aluminium", 0.05),
        ("4K Al", "Aluminium", 0.10),
        ("60K Al", "Aluminium", 0.15),
        ("Vacuum jacket", "Aluminium", 0.20),
        ("CsI", "CsI", 0.25),
        ("Kapton", "Kapton", 0.30),
        ("Outer Al", "Aluminium", 0.35),
    ]
    for label, material, offset in layers:
        r, g, b, _alpha = module.COLORS.get(material, (0.6, 0.6, 0.6, 0.5))
        # Tiny offsets keep coincident outlines readable; the actual rectcut
        # half-size for every layer remains exactly WINDOW_HALF_CM in the .geo.
        y0 = -half - offset * 0.015
        y1 = half + offset * 0.015
        z0 = SIDE_CENTER_Z_CM - half - offset * 0.015
        z1 = SIDE_CENTER_Z_CM + half + offset * 0.015
        ax.plot([y0, y1, y1, y0, y0], [z0, z0, z1, z1, z0], color=(r, g, b), lw=1.4, label=label)
    ax.axhline(SIDE_CENTER_Z_CM, color="black", lw=0.5, ls="--", alpha=0.55)
    ax.axvline(0.0, color="black", lw=0.5, ls="--", alpha=0.55)
    ax.set_title("Fix5 Y-Z side-window face: all wall rectcuts match the window")
    ax.set_xlabel("y (cm)")
    ax.set_ylabel("z (cm)")
    ax.set_xlim(-2.35, 2.35)
    ax.set_ylim(SIDE_CENTER_Z_CM - 2.35, SIDE_CENTER_Z_CM + 2.35)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.18)
    ax.legend(loc="upper right", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(YZ_FACE_PNG, dpi=220)
    fig.savefig(YZ_FACE_SVG)
    plt.close(fig)


def write_projections() -> None:
    write_projection(
        XZ_ZOOM_PNG,
        XZ_ZOOM_SVG,
        "Fix5 world X-Z projection, 45 deg InstrumentFrame tilt applied",
        (-22.0, 8.5),
        (-11.0, 1.5),
    )
    write_projection(
        XZ_FULL_PNG,
        XZ_FULL_SVG,
        "Fix5 world X-Z projection, full instrument proxy with 45 deg tilt",
        (-25.0, 25.0),
        (-24.0, 40.0),
    )
    write_side_window_face_detail()


def opening_audit() -> list[dict[str, float | str]]:
    items = [
        ("50mK Cu Still-like can", CU50_RIN, CU50_ROUT),
        ("Still Al shield", 8.5, 8.8),
        ("4K Al shield", 9.9, 10.2),
        ("60K Al shield", 11.4, 11.7),
        ("Vacuum jacket Al", 12.9, 13.4),
        ("CsI side wall", 14.0, 18.0),
        ("Kapton flex", 18.17, 18.2),
        ("Outer Al shell", 18.3, 19.1),
    ]
    rows = []
    for name, rin, rout in items:
        rows.append(
            {
                "layer": name,
                "r_inner_cm": rin,
                "r_outer_cm": rout,
                "rectcut_window_y_half_cm": WINDOW_HALF_CM,
                "rectcut_window_z_half_cm": WINDOW_HALF_CM,
                "rectcut_x_center_cm": 0.5 * ((-rout - RECTCUT_EPS_CM) + RECTCUT_EPS_CM),
                "rectcut_x_half_cm": 0.5 * (RECTCUT_EPS_CM - (-rout - RECTCUT_EPS_CM)),
                "nominal_shell_thickness_cm": rout - rin,
            }
        )
    return rows


def write_summary(payload: dict[str, object], mass_rows: list[dict[str, object]]) -> None:
    total_delta = sum(float(row["delta_kg_est"]) for row in mass_rows)
    audit = opening_audit()
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# User Cylindrical Redesign Multihole-W Fix5",
                "",
                "Status: `TOPOLOGY_FIXES_APPLIED_NOT_MC_VALIDATED`",
                "",
                "This candidate keeps the fix4 mass-model topology and applies only the requested review corrections in a new derived directory.",
                "It is still not a prompt-511 minimal-addition candidate because the parent user redesign modifies baseline Cryoperm/50mK geometry.",
                "",
                "## Implemented Fixes",
                "",
                "- Replaced incorrect `Cu_50mK_Local_Can_Cylinder_2mm` x-axis open sleeve with a z-axis Still-like 2 mm Copper local cold shield.",
                f"- The 50 mK Cu can uses r=`{CU50_RIN:.2f}-{CU50_ROUT:.2f} cm`, bottom cap z=`-9.90..-9.70 cm`, and a full-azimuth top edge at z=`-0.30 cm`, touching the 50 mK cold plate lower face.",
                f"- The 50 mK cold plate radius is set to `{CU50_COLD_PLATE_ROUT:.2f} cm` so it actually closes the larger no-notch Cu can.",
                f"- Moved `Win_50mK_Al_foil_side` to x=`{WIN_50MK_X:.2f} cm` so it sits on the new 50 mK Cu can side wall.",
                "- The 50 mK Cu can has no +x service notch; its radius is placed outside the existing cold-finger clamp/stem envelope so those structures clear inside the can.",
                f"- Replaced the former solid MuMetal/Nb incident caps with `{MAG_INCIDENT_AL_WINDOW_NAME}`, a thin Al foil at x=`{MAG_INCIDENT_AL_WINDOW_X:.5f} cm` with half-thickness `{MAG_INCIDENT_AL_WINDOW_HALF_THICK:.5f} cm`.",
                f"- Shortened the x-axis magnetic sleeve incident side to MuMetal x=`{MAG_FRONT_MUMETAL_XMIN:.2f} cm` and Nb x=`{MAG_FRONT_NB_XMIN:.2f} cm` so the magnetic shield remains inside the 50 mK Cu can.",
                f"- Shortened the x-axis Nb sleeve back edge to x=`{MAG_BACK_NB_XMAX:.2f} cm` and the MuMetal sleeve back edge to x=`{MAG_BACK_MUMETAL_XMAX:.2f} cm`; added back PCON end caps with central cold-finger clearance hole radius `{MAG_BACK_COLD_FINGER_HOLE_RADIUS:.2f} cm` in both layers.",
                "- Recut every side-wall window band listed below with a Boolean through-window: full side band minus a BRIK box with y/z half-size `1.898 cm` and x extent from outside shell to the cylinder centerline.",
                f"- Closed the simplified CsI bottom/side seam by moving side CsI lower edges to z=`{CSI_SIDE_BOTTOM_Z_CM:.2f} cm`, matching the bottom CsI top face.",
                "",
                "## Side-Window Model",
                "",
                "The side-wall openings are now true Boolean rectangular cuts in the `.geo`: each side-window band uses `Shape Subtraction full_PCON rect_window_BRIK orientation`.",
                "The projected aperture is `3.796 cm x 3.796 cm` for the 50 mK Cu can, Still Al, 4K Al, 60K Al, vacuum jacket, CsI side wall, Kapton flex, and outer Al shell.",
                "The x half-size is intentionally much larger than the shell thickness; that is what makes the curved side wall actually open all the way through while preserving the same y/z face aperture.",
                "The MEGAlib geometry is globally tilted through `InstrumentFrame.Rotation 0 45 0` in the Intro file; the WRL and X-Z projections apply that parent rotation.",
                "The Y-Z side-window face figure is explicitly a local InstrumentFrame face audit, because the real face is tilted in world coordinates.",
                "",
                "## Artifacts",
                "",
                f"- Geometry directory: `{payload['geometry_dir']}`",
                f"- Geometry setup: `{payload['setup']}`",
                f"- Detector map: `{payload['det']}`",
                f"- WRL visualization: `{rel(WRL)}`",
                f"- 2D X-Z projection zoom PNG: `{rel(XZ_ZOOM_PNG)}`",
                f"- 2D X-Z projection zoom SVG: `{rel(XZ_ZOOM_SVG)}`",
                f"- 2D X-Z projection full PNG: `{rel(XZ_FULL_PNG)}`",
                f"- 2D X-Z projection full SVG: `{rel(XZ_FULL_SVG)}`",
                f"- 2D Y-Z side-window face PNG: `{rel(YZ_FACE_PNG)}`",
                f"- 2D Y-Z side-window face SVG: `{rel(YZ_FACE_SVG)}`",
                f"- Mass delta CSV: `{rel(MASS_CSV)}`",
                f"- Candidate overlap source: `{rel(OVERLAP_SOURCE)}`",
                f"- `.det` reference check JSON: `{rel(WORK / 'geometry_det_reference_check.json')}`",
                f"- Side-window material-path audit JSON: `{rel(WORK / 'side_window_material_path_audit_fix5.json')}`",
                f"- cosima overlap log: `{rel(WORK / 'cosima_overlap_fix5_20260621.log')}`",
                f"- prompt-511 constraint log: `{rel(WORK / 'check_prompt511_constraints_fix5.log')}`",
                "",
                "## Side-Port Opening Audit",
                "",
                "| layer | r_inner cm | r_outer cm | rectcut y half cm | rectcut z half cm | rectcut x center cm | rectcut x half cm | shell thickness cm |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
                *[
                    f"| {row['layer']} | {float(row['r_inner_cm']):.2f} | {float(row['r_outer_cm']):.2f} | {float(row['rectcut_window_y_half_cm']):.4f} | {float(row['rectcut_window_z_half_cm']):.4f} | {float(row['rectcut_x_center_cm']):.4f} | {float(row['rectcut_x_half_cm']):.4f} | {float(row['nominal_shell_thickness_cm']):.4f} |"
                    for row in audit
                ],
                "",
                "## Mass Delta For Fix5 Components",
                "",
                f"Estimated fix5 mass delta over listed components: `{total_delta:+.4f} kg`.",
                "",
                "| component | material | baseline kg est. | candidate kg est. | delta kg |",
                "|---|---:|---:|---:|---:|",
                *[
                    f"| {row['component']} | {row['material']} | {float(row['baseline_mass_kg_est']):.5g} | {float(row['candidate_mass_kg_est']):.5g} | {float(row['delta_kg_est']):+.5g} |"
                    for row in mass_rows
                ],
                "",
                "## Validation Notes",
                "",
                "- No prompt, delayed, neutron, or signal MC closure has been run.",
                "- `.det` reference check is generated externally after the build; every existing passive sensitive detector concept is preserved for tracking.",
                "- The side-window material-path audit checks that every cut box covers the full -x shell chord for the square aperture and that no MuMetal/Nb incident cap remains.",
                "- `cosima CheckForOverlaps 10000 0.0001` must be read from the generated fix5 overlap log.",
                "- The prompt-511 constraint checker is expected to fail because this user redesign deliberately modifies/removes baseline Cryoperm/50mK/cold-plate structures.",
                "- Constraint-checker note: it also flags the new Boolean CsI rectcut bands as `r=0` cold-region additions because the checker does not infer radii from named Boolean shapes; the actual `.geo` PCON definitions are `rin=14 cm`, `rout=18 cm`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_readme(payload: dict[str, object]) -> None:
    readme = "\n".join(
        [
            "# DEMO2 DR v3p5 User Multihole-W Fix5",
            "",
            "Derived from the previous user cylindrical redesign with multihole W.",
            "Applies only the requested corrections: through-cut side windows, thin Al magnetic incident foil, CsI seam closure, and updated documentation/validation artifacts.",
            "The generated `.geo/.det/.geo.setup` files are the self-contained geometry handoff; the build script is a derivation record and depends on the parent candidate directory.",
            "",
            f"- Manifest: `{rel(MANIFEST)}`",
            f"- Summary: `{rel(SUMMARY_MD)}`",
            f"- WRL: `{rel(WRL)}`",
            f"- X-Z projection: `{rel(XZ_ZOOM_PNG)}`",
            f"- Y-Z side-window face: `{rel(YZ_FACE_PNG)}`",
            f"- Candidate overlap source: `{rel(OVERLAP_SOURCE)}`",
            "",
        ]
    ) + "\n"
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    (OUT_DIR / "README_USER_CYLMAG_REDESIGN.md").write_text(readme, encoding="utf-8")


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    shutil.copytree(BASE_DIR, OUT_DIR)

    for name in ("cosima_overlap.log", "cosima_overlap_multiholeW_20260621.log", "geometry_proxy_validation.json"):
        path = OUT_DIR / name
        if path.exists():
            path.unlink()

    geometry_payload = modify_geo()
    det_payload = modify_det(set(geometry_payload["removed_volumes"]), geometry_payload["added_volumes"])
    mass_rows = write_mass_delta()
    write_wrl()
    write_projections()
    write_overlap_source()

    payload = {
        "status": "TOPOLOGY_FIXES_APPLIED_NOT_MC_VALIDATED",
        "parent_geometry_dir": rel(BASE_DIR),
        "geometry_dir": rel(OUT_DIR),
        "setup": rel(SETUP),
        "geo": rel(GEO),
        "det": rel(DET),
        "materials": rel(MATERIALS),
        "geometry": geometry_payload,
        "detector_map": det_payload,
        "artifacts": {
            "wrl_from_geo": rel(WRL),
            "xz_projection_zoom_png": rel(XZ_ZOOM_PNG),
            "xz_projection_zoom_svg": rel(XZ_ZOOM_SVG),
            "xz_projection_full_png": rel(XZ_FULL_PNG),
            "xz_projection_full_svg": rel(XZ_FULL_SVG),
            "yz_side_window_face_png": rel(YZ_FACE_PNG),
            "yz_side_window_face_svg": rel(YZ_FACE_SVG),
            "mass_delta_csv": rel(MASS_CSV),
            "summary_md": rel(SUMMARY_MD),
            "overlap_source": rel(OVERLAP_SOURCE),
            "det_reference_check_json": rel(WORK / "geometry_det_reference_check.json"),
            "side_window_material_path_audit_json": rel(WORK / "side_window_material_path_audit_fix5.json"),
            "cosima_overlap_log": rel(WORK / "cosima_overlap_fix5_20260621.log"),
            "prompt511_constraint_log": rel(WORK / "check_prompt511_constraints_fix5.log"),
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_summary(payload, mass_rows)
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "geometry_dir": payload["geometry_dir"], "summary": rel(SUMMARY_MD)}, indent=2))


if __name__ == "__main__":
    main()
