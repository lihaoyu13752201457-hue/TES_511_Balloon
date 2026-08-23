#!/usr/bin/env python3
"""Build SH3 optimized assembly v2 without overwriting assembly v1.

Changes relative to v1:
- lift all five DR ports and the chimney axis from z'=-5.2 to -2.8 cm;
- move the chimney outward and join it to the curved vacuum jacket with a
  3 mm aluminium frustum plus a short aluminium nozzle through the outer shell;
- cut a diameter-6 cm optical-axis clearance through the NF2 upper mount plate;
- replace the circular front-BGO recess with a square recess containing a
  simple four-bar tungsten frame (no multihole/grid collimator);
- reroute the copper cold finger to the retained MXC plate contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
SH3 = PACKAGE.parent
V1_BUILDER = SH3 / "assembly/code/build_sh3_assembly.py"

spec = importlib.util.spec_from_file_location("sh3_assembly_v1_builder", V1_BUILDER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load v1 assembly builder: {V1_BUILDER}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"
FIGURES = PACKAGE / "figures"
OUTPUT_GEO = GEOMETRY / "SH3_Assembly_OptV2.geo"
OUTPUT_SETUP = GEOMETRY / "SH3_Assembly_OptV2.geo.setup"
OUTPUT_DET = GEOMETRY / "SH3_Assembly_OptV2.det"
OUTPUT_MATERIALS = GEOMETRY / "Materials_SH3_Assembly_OptV2.geo"
OUTPUT_FIGURE = FIGURES / "sh3_assembly_opt_v2_local_xz_section.svg"
OUTPUT_DETAIL_FIGURE = FIGURES / "sh3_assembly_opt_v2_interface_optics_detail.svg"
OUTPUT_MANIFEST = DATA / "assembly_opt_v2_manifest.json"
OUTPUT_STATIC = AUDIT / "assembly_opt_v2_static_validation.json"

PORT_CENTER_Z_CM = -2.80
DR_VACUUM_JACKET_BOTTOM_Z_CM = -14.10
DR_OUTER_NEGATIVE_X_CM = -20.60
CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM = 10.90
TRANSITION_X0_CM = -24.65
TRANSITION_X1_CM = -20.95
CHIMNEY_ORIGIN_X_CM = TRANSITION_X0_CM - CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM
CHIMNEY_ORIGIN_Z_CM = PORT_CENTER_Z_CM

CHIMNEY_OUTER_RADIUS_CM = 11.05
TRANSITION_LARGE_INNER_RADIUS_CM = 10.75
TRANSITION_LARGE_OUTER_RADIUS_CM = 11.05
TRANSITION_SMALL_INNER_RADIUS_CM = 0.75
TRANSITION_SMALL_OUTER_RADIUS_CM = 1.05
TRANSITION_NECK_X0_CM = TRANSITION_X1_CM
TRANSITION_NECK_X1_CM = -20.10
TRANSITION_NECK_INNER_RADIUS_CM = 0.75
TRANSITION_NECK_OUTER_RADIUS_CM = 1.05
VACUUM_JACKET_INTERFACE_PORT_RADIUS_CM = 1.05

PORT_RADIUS_CM = 0.75
COLD_HALF_CM = 0.16
CHIMNEY_STUB_LOCAL_X1_CM = 6.80
PORT_RUN_X0_CM = CHIMNEY_ORIGIN_X_CM + CHIMNEY_STUB_LOCAL_X1_CM
PORT_RUN_X1_CM = -14.86
DOGLEG_X0_CM = -14.86
DOGLEG_X1_CM = -14.54
DOGLEG_Y1_CM = 1.10
INTERNAL_X0_CM = -14.54
INTERNAL_X1_CM = 5.89
STEM_X_CM = 6.05
STEM_Y_CM = 1.10
STEM_Z0_CM = PORT_CENTER_Z_CM + COLD_HALF_CM
STEM_Z1_CM = -0.55
PAD_RADIUS_CM = 0.35
PAD_Z0_CM = -0.55
PAD_Z1_CM = -0.20
MXC_PLATE_BOTTOM_Z_CM = -0.20
MXC_HOLE_RADIUS_CM = 1.1629703349613

BGO_FRONT_LOCAL_X0_CM = -10.15
BGO_FRONT_LOCAL_X1_CM = -6.15
W_FRAME_X0_CM = CHIMNEY_ORIGIN_X_CM + BGO_FRONT_LOCAL_X0_CM
W_FRAME_X1_CM = W_FRAME_X0_CM + 2.00
W_FRAME_OUTER_HALF_CM = 3.00
W_FRAME_INNER_HALF_CM = 2.70
SUPPORT_OPTICAL_CUT_RADIUS_CM = 3.00

TOP_MOUNT_POS_X_CM = -24.7487373
TOP_MOUNT_POS_Z_CM = 31.8198052
TOP_MOUNT_CUT_LOCAL_X_CM = math.sqrt(2.0) * (
    PORT_CENTER_Z_CM - TOP_MOUNT_POS_Z_CM
)


class BuildError(RuntimeError):
    pass


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def patch_front_bgo_square_recess(component: str) -> str:
    marker = "Volume SH3_BGO40_FrontOpticalAnnulus\n"
    if component.count(marker) != 1:
        raise BuildError("front BGO marker is not unique")
    shapes = f"""// OptV2: square BGO-front recess for a simple W frame.
Shape TUBS SH3_OptV2_BGOFront_FullCylinderShape
SH3_OptV2_BGOFront_FullCylinderShape.Parameters 0 10.700000 2.000000 0 360
Shape BRIK SH3_OptV2_BGOFront_SquareRecessCutShape
SH3_OptV2_BGOFront_SquareRecessCutShape.Parameters {W_FRAME_OUTER_HALF_CM:.6f} {W_FRAME_OUTER_HALF_CM:.6f} 2.100000
Orientation SH3_OptV2_BGOFront_SquareRecessCutOrientation
SH3_OptV2_BGOFront_SquareRecessCutOrientation.Position 0 0 0
Shape Subtraction SH3_OptV2_BGOFront_SquareRecessShape
SH3_OptV2_BGOFront_SquareRecessShape.Parameters SH3_OptV2_BGOFront_FullCylinderShape SH3_OptV2_BGOFront_SquareRecessCutShape SH3_OptV2_BGOFront_SquareRecessCutOrientation

"""
    component = component.replace(marker, shapes + marker, 1)
    old = "SH3_BGO40_FrontOpticalAnnulus.Shape TUBS 2.700000 10.700000 2.000000 0 360"
    new = "SH3_BGO40_FrontOpticalAnnulus.Shape SH3_OptV2_BGOFront_SquareRecessShape"
    if component.count(old) != 1:
        raise BuildError("front BGO native shape line is not unique")
    return component.replace(old, new, 1)


def flatten_chimney(component: str) -> tuple[str, list[str]]:
    names = re.findall(r"^(\S+)\.Mother SH3_ChimneyFrame\s*$", component, re.MULTILINE)
    if not names:
        raise BuildError("no chimney top-level placements found")
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}\.Position\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            re.MULTILINE,
        )
        match = pattern.search(component)
        if match is None:
            raise BuildError(f"top-level volume lacks a position: {name}")
        x, y, z = (float(value) for value in match.groups())
        replacement = (
            f"{name}.Position {x + CHIMNEY_ORIGIN_X_CM:.12g} "
            f"{y:.12g} {z + CHIMNEY_ORIGIN_Z_CM:.12g}"
        )
        component, count = pattern.subn(replacement, component, count=1)
        if count != 1:
            raise BuildError(f"failed to translate {name}")
        component = component.replace(
            f"{name}.Mother SH3_ChimneyFrame", f"{name}.Mother InstrumentFrame", 1
        )
    if re.search(r"^\S+\.Mother SH3_ChimneyFrame\s*$", component, re.MULTILINE):
        raise BuildError("unflattened chimney mother remains")
    return component, names


def patch_dr_ports_and_support_window(dr_geometry: str) -> str:
    pattern = re.compile(
        r"^(SH3_DRBase_\S+_ColdFingerPortCutOrientation\.Position\s+[-+0-9.eE]+\s+0\s+)"
        r"-5\.200000\s*$",
        re.MULTILINE,
    )
    dr_geometry, count = pattern.subn(
        lambda match: match.group(1) + f"{PORT_CENTER_Z_CM:.6f}", dr_geometry
    )
    if count != 5:
        raise BuildError(f"expected five DR port moves, changed {count}")

    # The transition nozzle penetrates only the 300 K vacuum jacket. Keep the
    # four colder interfaces at the requested diameter 1.50 cm.
    outer_port_old = (
        "SH3_DRBase_VacuumJacket_ColdFingerPortCutShape.Parameters "
        "0 0.750000 0.450000 0 360"
    )
    outer_port_new = (
        "SH3_DRBase_VacuumJacket_ColdFingerPortCutShape.Parameters "
        f"0 {VACUUM_JACKET_INTERFACE_PORT_RADIUS_CM:.6f} 0.450000 0 360"
    )
    if dr_geometry.count(outer_port_old) != 1:
        raise BuildError("vacuum-jacket port shape line is not unique")
    dr_geometry = dr_geometry.replace(outer_port_old, outer_port_new, 1)

    marker = "// Volume NF2_OuterSupport_Al_TopMountAnnulus;"
    if dr_geometry.count(marker) != 1:
        raise BuildError("NF2 upper mount marker is not unique")
    shapes = f"""// OptV2: optical-axis clearance through the upper NF2 aluminium mount plate.
Shape PCON SH3_OptV2_NF2_TopMount_BaseShape
SH3_OptV2_NF2_TopMount_BaseShape.Parameters 0 360 2 -0.25 34.9765777 48.8250037 0.25 34.9765777 48.8250037
Shape TUBS SH3_OptV2_NF2_TopMount_OpticalCutShape
SH3_OptV2_NF2_TopMount_OpticalCutShape.Parameters 0 {SUPPORT_OPTICAL_CUT_RADIUS_CM:.6f} 5.000000 0 360
Orientation SH3_OptV2_NF2_TopMount_OpticalCutOrientation
SH3_OptV2_NF2_TopMount_OpticalCutOrientation.Position {TOP_MOUNT_CUT_LOCAL_X_CM:.6f} 0 0
SH3_OptV2_NF2_TopMount_OpticalCutOrientation.Rotation 0 135 0
Shape Subtraction SH3_OptV2_NF2_TopMount_WithOpticalCutShape
SH3_OptV2_NF2_TopMount_WithOpticalCutShape.Parameters SH3_OptV2_NF2_TopMount_BaseShape SH3_OptV2_NF2_TopMount_OpticalCutShape SH3_OptV2_NF2_TopMount_OpticalCutOrientation

"""
    dr_geometry = dr_geometry.replace(marker, shapes + marker, 1)
    old = "NF2_OuterSupport_Al_TopMountAnnulus.Shape PCON 0 360 2 -0.25 34.9765777 48.8250037 0.25 34.9765777 48.8250037"
    new = "NF2_OuterSupport_Al_TopMountAnnulus.Shape SH3_OptV2_NF2_TopMount_WithOpticalCutShape"
    if dr_geometry.count(old) != 1:
        raise BuildError("NF2 upper mount native shape line is not unique")
    return dr_geometry.replace(old, new, 1)


def brik_volume(name: str, material: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> str:
    return "\n".join(
        (
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape BRIK {(x1-x0)/2:.6f} {(y1-y0)/2:.6f} {(z1-z0)/2:.6f}",
            f"{name}.Position {(x0+x1)/2:.6f} {(y0+y1)/2:.6f} {(z0+z1)/2:.6f}",
            f"{name}.Mother InstrumentFrame",
            "",
        )
    )


def transition_text() -> str:
    half = 0.5 * (TRANSITION_X1_CM - TRANSITION_X0_CM)
    center = 0.5 * (TRANSITION_X0_CM + TRANSITION_X1_CM)
    neck_half = 0.5 * (TRANSITION_NECK_X1_CM - TRANSITION_NECK_X0_CM)
    neck_center = 0.5 * (TRANSITION_NECK_X0_CM + TRANSITION_NECK_X1_CM)
    return "\n".join(
        (
            "// BEGIN SH3_OPTV2_ALUMINIUM_TRANSITION_SHROUD",
            "// 3 mm outer Al frustum plus an Al nozzle through the 300 K vacuum jacket.",
            "Volume SH3_OptV2_Al_VacuumJacketTransitionShroud",
            "SH3_OptV2_Al_VacuumJacketTransitionShroud.Material Aluminium",
            "SH3_OptV2_Al_VacuumJacketTransitionShroud.Visibility 1",
            f"SH3_OptV2_Al_VacuumJacketTransitionShroud.Shape PCON 0 360 2 {-half:.6f} {TRANSITION_LARGE_INNER_RADIUS_CM:.6f} {TRANSITION_LARGE_OUTER_RADIUS_CM:.6f} {half:.6f} {TRANSITION_SMALL_INNER_RADIUS_CM:.6f} {TRANSITION_SMALL_OUTER_RADIUS_CM:.6f}",
            f"SH3_OptV2_Al_VacuumJacketTransitionShroud.Position {center:.6f} 0 {PORT_CENTER_Z_CM:.6f}",
            "SH3_OptV2_Al_VacuumJacketTransitionShroud.Rotation 0 90 0",
            "SH3_OptV2_Al_VacuumJacketTransitionShroud.Mother InstrumentFrame",
            "Volume SH3_OptV2_Al_VacuumJacketInterfaceNeck",
            "SH3_OptV2_Al_VacuumJacketInterfaceNeck.Material Aluminium",
            "SH3_OptV2_Al_VacuumJacketInterfaceNeck.Visibility 1",
            f"SH3_OptV2_Al_VacuumJacketInterfaceNeck.Shape TUBS {TRANSITION_NECK_INNER_RADIUS_CM:.6f} {TRANSITION_NECK_OUTER_RADIUS_CM:.6f} {neck_half:.6f} 0 360",
            f"SH3_OptV2_Al_VacuumJacketInterfaceNeck.Position {neck_center:.6f} 0 {PORT_CENTER_Z_CM:.6f}",
            "SH3_OptV2_Al_VacuumJacketInterfaceNeck.Rotation 0 90 0",
            "SH3_OptV2_Al_VacuumJacketInterfaceNeck.Mother InstrumentFrame",
            "// END SH3_OPTV2_ALUMINIUM_TRANSITION_SHROUD",
            "",
        )
    )


def w_frame_text() -> str:
    o = W_FRAME_OUTER_HALF_CM
    i = W_FRAME_INNER_HALF_CM
    zc = PORT_CENTER_Z_CM
    return (
        "// BEGIN SH3_OPTV2_SIMPLE_W_SQUARE_FRAME\n"
        "// Four passive W bars only; no multihole/grid collimator. Inner square contains the r=2.70 cm optical circle.\n"
        + brik_volume("SH3_OptV2_W_Frame_Top", "W", W_FRAME_X0_CM, W_FRAME_X1_CM, -o, o, zc + i, zc + o)
        + brik_volume("SH3_OptV2_W_Frame_Bottom", "W", W_FRAME_X0_CM, W_FRAME_X1_CM, -o, o, zc - o, zc - i)
        + brik_volume("SH3_OptV2_W_Frame_PosY", "W", W_FRAME_X0_CM, W_FRAME_X1_CM, i, o, zc - i, zc + i)
        + brik_volume("SH3_OptV2_W_Frame_NegY", "W", W_FRAME_X0_CM, W_FRAME_X1_CM, -o, -i, zc - i, zc + i)
        + "// END SH3_OPTV2_SIMPLE_W_SQUARE_FRAME\n"
    )


def cold_finger_text() -> str:
    h = COLD_HALF_CM
    pad_half = 0.5 * (PAD_Z1_CM - PAD_Z0_CM)
    pad_center = 0.5 * (PAD_Z1_CM + PAD_Z0_CM)
    return (
        "// BEGIN SH3_OPTV2_BENT_COLD_FINGER_TO_MXC\n"
        + brik_volume("SH3_OptV2_Cu_ColdFinger_PortRun", "Copper", PORT_RUN_X0_CM, PORT_RUN_X1_CM, -h, h, PORT_CENTER_Z_CM-h, PORT_CENTER_Z_CM+h)
        + brik_volume("SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg", "Copper", DOGLEG_X0_CM, DOGLEG_X1_CM, 0.0, DOGLEG_Y1_CM, PORT_CENTER_Z_CM-h, PORT_CENTER_Z_CM+h)
        + brik_volume("SH3_OptV2_Cu_ColdFinger_InternalRun", "Copper", INTERNAL_X0_CM, INTERNAL_X1_CM, STEM_Y_CM-h, STEM_Y_CM+h, PORT_CENTER_Z_CM-h, PORT_CENTER_Z_CM+h)
        + brik_volume("SH3_OptV2_Cu_ColdFinger_MXCStem", "Copper", STEM_X_CM-h, STEM_X_CM+h, STEM_Y_CM-h, STEM_Y_CM+h, STEM_Z0_CM, STEM_Z1_CM)
        + "\n".join(
            (
                "Volume SH3_OptV2_Cu_MXC_ContactPad",
                "SH3_OptV2_Cu_MXC_ContactPad.Material Copper",
                "SH3_OptV2_Cu_MXC_ContactPad.Visibility 1",
                f"SH3_OptV2_Cu_MXC_ContactPad.Shape PCON 0 360 2 {-pad_half:.6f} 0 {PAD_RADIUS_CM:.6f} {pad_half:.6f} 0 {PAD_RADIUS_CM:.6f}",
                f"SH3_OptV2_Cu_MXC_ContactPad.Position {STEM_X_CM:.6f} {STEM_Y_CM:.6f} {pad_center:.6f}",
                "SH3_OptV2_Cu_MXC_ContactPad.Mother InstrumentFrame",
                "// Pad upper face touches the retained MXC copper plate underside at z'=-0.20 cm.",
                "// END SH3_OPTV2_BENT_COLD_FINGER_TO_MXC",
                "",
            )
        )
    )


def geometry_text(dr_geometry: str, chimney: str) -> str:
    dr_geometry = dr_geometry.replace(
        "Include Materials_SH3_DR_Base.geo",
        "Include Materials_SH3_Assembly_OptV2.geo",
        1,
    )
    return (
        dr_geometry.rstrip()
        + "\n\n// BEGIN SH3_ASSEMBLY_OPT_V2\n"
        + "// Raised port/chimney, curved-wall Al transition, optical baffle cut, simple W frame.\n"
        + "// Geometry only; no transport/timing/sensitivity authority.\n"
        + "// BEGIN FLATTENED_SH3_CHIMNEY_OPT_V2\n"
        + chimney.rstrip()
        + "\n// END FLATTENED_SH3_CHIMNEY_OPT_V2\n\n"
        + transition_text()
        + w_frame_text()
        + cold_finger_text()
        + "// END SH3_ASSEMBLY_OPT_V2\n"
    )


def setup_text() -> str:
    return """Name SH3_Chimney_DR_Assembly_OptV2
Version 1
Include SH3_Assembly_OptV2.geo
Include SH3_Assembly_OptV2.det
SurroundingSphere 95 0 0 8 95
"""


def frustum_annular_volume_cm3() -> float:
    length = TRANSITION_X1_CM - TRANSITION_X0_CM
    outer = (
        TRANSITION_LARGE_OUTER_RADIUS_CM**2
        + TRANSITION_LARGE_OUTER_RADIUS_CM * TRANSITION_SMALL_OUTER_RADIUS_CM
        + TRANSITION_SMALL_OUTER_RADIUS_CM**2
    )
    inner = (
        TRANSITION_LARGE_INNER_RADIUS_CM**2
        + TRANSITION_LARGE_INNER_RADIUS_CM * TRANSITION_SMALL_INNER_RADIUS_CM
        + TRANSITION_SMALL_INNER_RADIUS_CM**2
    )
    return math.pi * length * (outer - inner) / 3.0


def mass_proxy() -> dict[str, float]:
    w_volume = 2 * (W_FRAME_X1_CM-W_FRAME_X0_CM) * (2*W_FRAME_OUTER_HALF_CM) * (W_FRAME_OUTER_HALF_CM-W_FRAME_INNER_HALF_CM)
    w_volume += 2 * (W_FRAME_X1_CM-W_FRAME_X0_CM) * (W_FRAME_OUTER_HALF_CM-W_FRAME_INNER_HALF_CM) * (2*W_FRAME_INNER_HALF_CM)
    frustum_volume = frustum_annular_volume_cm3()
    neck_volume = math.pi * (
        TRANSITION_NECK_OUTER_RADIUS_CM**2
        - TRANSITION_NECK_INNER_RADIUS_CM**2
    ) * (TRANSITION_NECK_X1_CM-TRANSITION_NECK_X0_CM)
    transition_volume = frustum_volume + neck_volume
    square_area = (2*COLD_HALF_CM)**2
    cold_volume = (
        (PORT_RUN_X1_CM-PORT_RUN_X0_CM)*square_area
        + (DOGLEG_X1_CM-DOGLEG_X0_CM)*DOGLEG_Y1_CM*(2*COLD_HALF_CM)
        + (INTERNAL_X1_CM-INTERNAL_X0_CM)*square_area
        + (STEM_Z1_CM-STEM_Z0_CM)*square_area
        + math.pi*PAD_RADIUS_CM**2*(PAD_Z1_CM-PAD_Z0_CM)
    )
    bgo_removed = ((2*W_FRAME_OUTER_HALF_CM)**2 - math.pi*2.7**2) * 4.0
    return {
        "transition_frustum_al_volume_cm3": frustum_volume,
        "transition_neck_al_volume_cm3": neck_volume,
        "transition_al_volume_cm3": transition_volume,
        "transition_al_mass_kg_at_2p699": transition_volume*2.699/1000.0,
        "w_frame_volume_cm3": w_volume,
        "w_frame_mass_kg_at_19p3": w_volume*19.3/1000.0,
        "cold_finger_volume_cm3": cold_volume,
        "cold_finger_copper_mass_g_at_8p96": cold_volume*8.96,
        "additional_bgo_removed_for_square_recess_cm3": bgo_removed,
        "additional_bgo_removed_mass_kg_at_7p13": bgo_removed*7.13/1000.0,
    }


def svg_text() -> str:
    width, height = 2000, 1180
    x_min, x_max = -48.0, 24.0
    z_min, z_max = -16.0, 48.0
    left, right, top, bottom = 120.0, 1580.0, 120.0, 1070.0
    def sx(x: float) -> float:
        return left + (x-x_min)/(x_max-x_min)*(right-left)
    def sz(z: float) -> float:
        return bottom - (z-z_min)/(z_max-z_min)*(bottom-top)
    def rect(x0: float, x1: float, z0: float, z1: float, fill: str, opacity: float=0.85, stroke: str="none") -> str:
        return f'<rect x="{sx(x0):.2f}" y="{sz(z1):.2f}" width="{sx(x1)-sx(x0):.2f}" height="{sz(z0)-sz(z1):.2f}" fill="{fill}" opacity="{opacity}" stroke="{stroke}"/>'
    shells = (
        (15.1,15.3,-9.7,-0.3,"#2457d6"),(15.5,15.8,-10.4,10.7,"#367ee8"),
        (17.7,18.0,-11.4,19.7,"#49a6e9"),(18.2,18.5,-12.4,28.65,"#79c8e8"),
        (20.1,20.6,-13.6,37.5,"#9aa5b1"),
    )
    items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="#fff"/>','<text x="1000" y="42" text-anchor="middle" font-family="DejaVu Sans" font-size="29" font-weight="700">SH3 optimized assembly v2 — raised chimney, transition shell, clear optical path</text>','<text x="1000" y="76" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">DR-local x′/z′ section; whole InstrumentFrame retains Rotation 0 45 0</text>']
    g0,g1=PORT_CENTER_Z_CM-PORT_RADIUS_CM,PORT_CENTER_Z_CM+PORT_RADIUS_CM
    for ri,ro,z0,z1,color in reversed(shells):
        items += [rect(ri,ro,z0,z1,color),rect(-ro,-ri,z0,g0,color),rect(-ro,-ri,g1,z1,color)]
    for z,r in ((0,15),(5,15),(10.5,15),(19.5,17.5),(28.5,18)):
        items.append(rect(-r,r,z-.2,z+.2,"#b87333",.72))
    ox,oz=CHIMNEY_ORIGIN_X_CM,CHIMNEY_ORIGIN_Z_CM
    for sign in (1,-1):
        a,b=sorted((oz+sign*6.7,oz+sign*10.7)); items.append(rect(ox-6.15,ox+6.85,a,b,"#156c3c",.82))
        a,b=sorted((oz+sign*3.0,oz+sign*10.7)); items.append(rect(ox-10.15,ox-6.15,a,b,"#1f9d55",.82))
        a,b=sorted((oz+sign*.75,oz+sign*10.7)); items.append(rect(ox+6.85,ox+10.85,a,b,"#2bb673",.82))
        a,b=sorted((oz+sign*10.75,oz+sign*11.05)); items.append(rect(ox-10.2,ox+10.9,a,b,"#697780",.95))
    for x in (-3,-1.8,-.6,.6,1.8,3): items.append(rect(ox+x-.15,ox+x+.15,oz-1.8,oz+1.8,"#c62828",.75))
    # Frustum projected envelope and hollow centre.
    p=[f'{sx(TRANSITION_X0_CM):.2f},{sz(oz+TRANSITION_LARGE_OUTER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X1_CM):.2f},{sz(oz+TRANSITION_SMALL_OUTER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X1_CM):.2f},{sz(oz+TRANSITION_SMALL_INNER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X0_CM):.2f},{sz(oz+TRANSITION_LARGE_INNER_RADIUS_CM):.2f}']
    items.append(f'<polygon points="{" ".join(p)}" fill="#6f7f87" opacity="0.92"/>')
    p=[f'{sx(TRANSITION_X0_CM):.2f},{sz(oz-TRANSITION_LARGE_OUTER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X1_CM):.2f},{sz(oz-TRANSITION_SMALL_OUTER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X1_CM):.2f},{sz(oz-TRANSITION_SMALL_INNER_RADIUS_CM):.2f}',f'{sx(TRANSITION_X0_CM):.2f},{sz(oz-TRANSITION_LARGE_INNER_RADIUS_CM):.2f}']
    items.append(f'<polygon points="{" ".join(p)}" fill="#6f7f87" opacity="0.92"/>')
    # Short aluminium nozzle crosses only the outer vacuum jacket.
    items += [
        rect(TRANSITION_NECK_X0_CM, TRANSITION_NECK_X1_CM,
             oz+TRANSITION_NECK_INNER_RADIUS_CM,
             oz+TRANSITION_NECK_OUTER_RADIUS_CM, "#596970", .96),
        rect(TRANSITION_NECK_X0_CM, TRANSITION_NECK_X1_CM,
             oz-TRANSITION_NECK_OUTER_RADIUS_CM,
             oz-TRANSITION_NECK_INNER_RADIUS_CM, "#596970", .96),
    ]
    # W top/bottom bars in this y=0 section.
    items += [rect(W_FRAME_X0_CM,W_FRAME_X1_CM,oz+W_FRAME_INNER_HALF_CM,oz+W_FRAME_OUTER_HALF_CM,"#4b3b21",1),rect(W_FRAME_X0_CM,W_FRAME_X1_CM,oz-W_FRAME_OUTER_HALF_CM,oz-W_FRAME_INNER_HALF_CM,"#4b3b21",1)]
    h=COLD_HALF_CM
    items += [rect(PORT_RUN_X0_CM,PORT_RUN_X1_CM,oz-h,oz+h,"#7b3f00",1),rect(INTERNAL_X0_CM,INTERNAL_X1_CM,oz-h,oz+h,"#7b3f00",1),rect(STEM_X_CM-h,STEM_X_CM+h,STEM_Z0_CM,STEM_Z1_CM,"#7b3f00",1),rect(STEM_X_CM-PAD_RADIUS_CM,STEM_X_CM+PAD_RADIUS_CM,PAD_Z0_CM,PAD_Z1_CM,"#a95f20",1)]
    bottom=oz-CHIMNEY_OUTER_RADIUS_CM
    items += [f'<line x1="{sx(x_min):.2f}" y1="{sz(DR_VACUUM_JACKET_BOTTOM_Z_CM):.2f}" x2="{sx(-20.6):.2f}" y2="{sz(DR_VACUUM_JACKET_BOTTOM_Z_CM):.2f}" stroke="#d32f2f" stroke-dasharray="7 5"/>',f'<line x1="{sx(x_min):.2f}" y1="{sz(bottom):.2f}" x2="{sx(TRANSITION_X0_CM):.2f}" y2="{sz(bottom):.2f}" stroke="#2e7d32" stroke-dasharray="7 5"/>',f'<text x="{sx(-46.8):.2f}" y="{sz(bottom+.7):.2f}" font-family="DejaVu Sans" font-size="15" fill="#2e7d32">chimney bottom z′={bottom:.2f}</text>',f'<text x="{sx(-46.8):.2f}" y="{sz(DR_VACUUM_JACKET_BOTTOM_Z_CM-.5):.2f}" font-family="DejaVu Sans" font-size="15" fill="#d32f2f">DR base z′=-14.10; clearance 0.25 cm</text>',f'<text x="{sx(-25.0):.2f}" y="{sz(9):.2f}" font-family="DejaVu Sans" font-size="17">3 mm Al frustum + Ø2.10 nozzle</text>',f'<text x="{sx(W_FRAME_X0_CM):.2f}" y="{sz(1.2):.2f}" font-family="DejaVu Sans" font-size="16" fill="#4b3b21">simple W square frame</text>',f'<text x="{sx(-19):.2f}" y="{sz(-1.6):.2f}" font-family="DejaVu Sans" font-size="16" fill="#7b3f00">raised/bent cold finger</text>','<text x="850" y="1142" text-anchor="middle" font-family="DejaVu Sans" font-size="18">DR local x′ (cm)</text>','<text x="38" y="590" text-anchor="middle" font-family="DejaVu Sans" font-size="18" transform="rotate(-90 38 590)">DR local z′ (cm)</text>','<rect x="1620" y="145" width="345" height="410" fill="#f7f9fb" stroke="#99a"/>','<text x="1792" y="183" text-anchor="middle" font-family="DejaVu Sans" font-size="18" font-weight="700">OptV2 dimensions</text>',f'<text x="1640" y="225" font-family="DejaVu Sans" font-size="15">port/chimney z′: {PORT_CENTER_Z_CM:.2f} cm</text>','<text x="1640" y="260" font-family="DejaVu Sans" font-size="15">bottom clearance: 0.25 cm</text>','<text x="1640" y="295" font-family="DejaVu Sans" font-size="15">transition: R11.05 → R1.05 + neck</text>','<text x="1640" y="330" font-family="DejaVu Sans" font-size="15">support aperture: Ø6.00 cm</text>','<text x="1640" y="365" font-family="DejaVu Sans" font-size="15">W outer/inner: 6.0/5.4 cm</text>','<text x="1640" y="400" font-family="DejaVu Sans" font-size="15">W axial depth: 2.0 cm</text>','<text x="1640" y="435" font-family="DejaVu Sans" font-size="15">no W grid/multihole bars</text>','<text x="1640" y="485" font-family="DejaVu Sans" font-size="15" fill="#b71c1c">geometry only; physics pending</text>','</svg>','']
    return "\n".join(items)


def detail_svg_text() -> str:
    """Return a review-oriented exact-dimension interface/optics detail."""
    width, height = 1800, 1040
    lx0, lx1, lz0, lz1 = -25.5, -13.5, -15.0, 10.0
    left, right, top, bottom = 95.0, 955.0, 135.0, 935.0

    def sx(x: float) -> float:
        return left + (x-lx0)/(lx1-lx0)*(right-left)

    def sz(z: float) -> float:
        return bottom - (z-lz0)/(lz1-lz0)*(bottom-top)

    def rect(x0: float, x1: float, z0: float, z1: float, fill: str,
             opacity: float = 1.0, stroke: str = "none") -> str:
        return (
            f'<rect x="{sx(x0):.2f}" y="{sz(z1):.2f}" '
            f'width="{sx(x1)-sx(x0):.2f}" height="{sz(z0)-sz(z1):.2f}" '
            f'fill="{fill}" opacity="{opacity}" stroke="{stroke}"/>'
        )

    oz = PORT_CENTER_Z_CM
    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="900" y="42" text-anchor="middle" font-family="DejaVu Sans" font-size="30" font-weight="700">SH3 OptV2 — curved-wall interface and optical-clearance detail</text>',
        '<text x="900" y="76" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">Exact nominal geometry dimensions; not a thermal/manufacturing drawing</text>',
        '<rect x="55" y="105" width="940" height="865" fill="#f8fafc" stroke="#8090a0"/>',
        '<text x="525" y="127" text-anchor="middle" font-family="DejaVu Sans" font-size="21" font-weight="700">A. DR-local x′/z′ interface zoom</text>',
    ]

    # Curved-shell projections with the raised common service opening.
    gap0, gap1 = oz-PORT_RADIUS_CM, oz+PORT_RADIUS_CM
    for ri, ro, z0, z1, color, label in (
        (20.10, 20.60, -13.60, 9.5, "#7b8791", "300 K Al vacuum jacket"),
        (18.20, 18.50, -12.40, 9.5, "#74bfe5", "60 K"),
        (17.70, 18.00, -11.40, 9.5, "#459ee1", "4 K"),
        (15.50, 15.80, -10.40, 9.5, "#3378db", "Still"),
        (15.10, 15.30, -9.70, -0.30, "#214fc4", "MXC"),
    ):
        x0, x1 = -ro, -ri
        items += [rect(x0, x1, z0, gap0, color, .92), rect(x0, x1, gap1, z1, color, .92)]

    # Frustum and nozzle projected material bands.
    top_band = [
        f'{sx(TRANSITION_X0_CM):.2f},{sz(oz+TRANSITION_LARGE_OUTER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X1_CM):.2f},{sz(oz+TRANSITION_SMALL_OUTER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X1_CM):.2f},{sz(oz+TRANSITION_SMALL_INNER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X0_CM):.2f},{sz(oz+TRANSITION_LARGE_INNER_RADIUS_CM):.2f}',
    ]
    bottom_band = [
        f'{sx(TRANSITION_X0_CM):.2f},{sz(oz-TRANSITION_LARGE_OUTER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X1_CM):.2f},{sz(oz-TRANSITION_SMALL_OUTER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X1_CM):.2f},{sz(oz-TRANSITION_SMALL_INNER_RADIUS_CM):.2f}',
        f'{sx(TRANSITION_X0_CM):.2f},{sz(oz-TRANSITION_LARGE_INNER_RADIUS_CM):.2f}',
    ]
    items += [
        f'<polygon points="{" ".join(top_band)}" fill="#596970" opacity="0.96"/>',
        f'<polygon points="{" ".join(bottom_band)}" fill="#596970" opacity="0.96"/>',
        rect(TRANSITION_NECK_X0_CM, TRANSITION_NECK_X1_CM,
             oz+TRANSITION_NECK_INNER_RADIUS_CM,
             oz+TRANSITION_NECK_OUTER_RADIUS_CM, "#46565d"),
        rect(TRANSITION_NECK_X0_CM, TRANSITION_NECK_X1_CM,
             oz-TRANSITION_NECK_OUTER_RADIUS_CM,
             oz-TRANSITION_NECK_INNER_RADIUS_CM, "#46565d"),
        rect(-25.5, PORT_RUN_X1_CM, oz-COLD_HALF_CM, oz+COLD_HALF_CM, "#9a5414"),
        f'<line x1="{sx(lx0):.2f}" y1="{sz(oz):.2f}" x2="{sx(lx1):.2f}" y2="{sz(oz):.2f}" stroke="#c62828" stroke-width="2" stroke-dasharray="9 7"/>',
        f'<text x="{sx(-24.9):.2f}" y="{sz(8.8):.2f}" font-family="DejaVu Sans" font-size="17" fill="#34454d">3 mm Al frustum</text>',
        f'<text x="{sx(-21.55):.2f}" y="{sz(-.95):.2f}" font-family="DejaVu Sans" font-size="15" fill="#34454d">Ø2.10 nozzle</text>',
        f'<text x="{sx(-19.8):.2f}" y="{sz(1.2):.2f}" font-family="DejaVu Sans" font-size="15" fill="#6b7780">outer hole Ø2.10</text>',
        f'<text x="{sx(-18.2):.2f}" y="{sz(-4.1):.2f}" font-family="DejaVu Sans" font-size="15" fill="#2457a6">four inner holes Ø1.50</text>',
        f'<text x="{sx(-18.3):.2f}" y="{sz(-2.15):.2f}" font-family="DejaVu Sans" font-size="15" fill="#9a5414">3.2 mm Cu cold finger</text>',
        f'<text x="{sx(-24.9):.2f}" y="{sz(-14.2):.2f}" font-family="DejaVu Sans" font-size="15" fill="#2e7d32">chimney bottom z′=-13.85 cm</text>',
        f'<text x="{sx(-20.4):.2f}" y="{sz(-14.2):.2f}" font-family="DejaVu Sans" font-size="15" fill="#b71c1c">DR bottom z′=-14.10 cm</text>',
        '<text x="525" y="998" text-anchor="middle" font-family="DejaVu Sans" font-size="16">Common raised axis: y′=0, z′=-2.80 cm; vertical clearance = 0.25 cm</text>',
    ]

    # Optical-axis front view: support cut, W frame, and nominal signal circle.
    cx, cy, scale = 1395.0, 385.0, 72.0
    outer = 2*W_FRAME_OUTER_HALF_CM*scale
    inner = 2*W_FRAME_INNER_HALF_CM*scale
    items += [
        '<rect x="1025" y="105" width="720" height="865" fill="#f8fafc" stroke="#8090a0"/>',
        '<text x="1385" y="127" text-anchor="middle" font-family="DejaVu Sans" font-size="21" font-weight="700">B. View along the TES optical axis</text>',
        f'<circle cx="{cx}" cy="{cy}" r="{SUPPORT_OPTICAL_CUT_RADIUS_CM*scale:.2f}" fill="#dce3e8" stroke="#65737e" stroke-width="3" stroke-dasharray="9 6"/>',
        f'<rect x="{cx-outer/2:.2f}" y="{cy-outer/2:.2f}" width="{outer:.2f}" height="{outer:.2f}" fill="#4b3b21"/>',
        f'<rect x="{cx-inner/2:.2f}" y="{cy-inner/2:.2f}" width="{inner:.2f}" height="{inner:.2f}" fill="#ffffff"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{2.7*scale:.2f}" fill="#ffe3a3" opacity="0.70" stroke="#d84315" stroke-width="4"/>',
        f'<line x1="{cx-230}" y1="{cy}" x2="{cx+230}" y2="{cy}" stroke="#c62828" stroke-width="2" stroke-dasharray="8 6"/>',
        f'<line x1="{cx}" y1="{cy-230}" x2="{cx}" y2="{cy+230}" stroke="#c62828" stroke-width="2" stroke-dasharray="8 6"/>',
        '<text x="1075" y="650" font-family="DejaVu Sans" font-size="17" fill="#4b3b21">dark: four solid W bars, 2.0 cm deep</text>',
        '<text x="1075" y="685" font-family="DejaVu Sans" font-size="17" fill="#d84315">orange circle: retained Ø5.40 cm signal opening</text>',
        '<text x="1075" y="720" font-family="DejaVu Sans" font-size="17" fill="#65737e">dashed circle: support-baffle Ø6.00 cm cut</text>',
        '<text x="1075" y="755" font-family="DejaVu Sans" font-size="17">W outer/inner square: 6.00 / 5.40 cm</text>',
        '<text x="1075" y="805" font-family="DejaVu Sans" font-size="16" fill="#b71c1c">Nominal circle is tangent to the W inner square.</text>',
        '<text x="1075" y="834" font-family="DejaVu Sans" font-size="16" fill="#b71c1c">Add fabrication/pointing margin only after optics review.</text>',
        '<text x="1075" y="892" font-family="DejaVu Sans" font-size="16" fill="#333">No grid, mesh, or multihole collimator is present.</text>',
        '<text x="1075" y="922" font-family="DejaVu Sans" font-size="16" fill="#333">The upper DR support plate is cut on this same axis.</text>',
        '</svg>',
        '',
    ]
    return "\n".join(items)


def validate(geometry: str, detector: str, flattened_names: list[str], dr_source: str) -> dict[str, object]:
    declared=re.findall(r"^Volume\s+(\S+)\s*$",geometry,re.MULTILINE)
    copies=re.findall(r"^\S+\.Copy\s+(\S+)\s*$",geometry,re.MULTILINE)
    mothers=re.findall(r"^\S+\.Mother\s+(\S+)\s*$",geometry,re.MULTILINE)
    names=set(declared)|set(copies)|{"0"}
    holes=[(float(x),float(y)) for x,y in re.findall(r"^SE3_HOLE_MXC_50mK_\d+\.Position\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+0\s*$",dr_source,re.MULTILINE)]
    nearest=min(math.hypot(x-STEM_X_CM,y-STEM_Y_CM) for x,y in holes)
    pad_clearance=nearest-MXC_HOLE_RADIUS_CM-PAD_RADIUS_CM
    chimney_bottom=PORT_CENTER_Z_CM-CHIMNEY_OUTER_RADIUS_CM
    checks={
        "one_world_and_instrument_frame":declared.count("WorldVolume")==1 and declared.count("InstrumentFrame")==1,
        "retained_45deg_parent_rotation":"InstrumentFrame.Rotation 0 45 0" in geometry,
        "five_ports_moved_to_minus2p8":len(re.findall(r"^SH3_DRBase_\S+_ColdFingerPortCutOrientation\.Position\s+[-+0-9.eE]+\s+0\s+-2\.800000$",geometry,re.MULTILINE))==5,
        "old_port_center_absent":not re.search(r"^SH3_DRBase_\S+_ColdFingerPortCutOrientation\.Position.*-5\.200000$",geometry,re.MULTILINE),
        "chimney_bottom_above_dr_base_bottom":chimney_bottom>DR_VACUUM_JACKET_BOTTOM_Z_CM,
        "bottom_clearance_0p25cm":math.isclose(chimney_bottom-DR_VACUUM_JACKET_BOTTOM_Z_CM,0.25),
        "transition_shell_present":"Volume SH3_OptV2_Al_VacuumJacketTransitionShroud" in geometry,
        "transition_large_end_matches_chimney":"SH3_OptV2_Al_VacuumJacketTransitionShroud.Shape PCON" in geometry and math.isclose(CHIMNEY_ORIGIN_X_CM+CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM,TRANSITION_X0_CM),
        "transition_neck_present":"Volume SH3_OptV2_Al_VacuumJacketInterfaceNeck" in geometry,
        "frustum_meets_interface_neck":math.isclose(TRANSITION_X1_CM,TRANSITION_NECK_X0_CM),
        "neck_crosses_outer_jacket_only":TRANSITION_NECK_X0_CM < DR_OUTER_NEGATIVE_X_CM and math.isclose(TRANSITION_NECK_X1_CM,-20.10),
        "outer_vacuum_port_is_diameter_2p10":len(re.findall(r"^SH3_DRBase_VacuumJacket_ColdFingerPortCutShape\.Parameters\s+0\s+1\.050000\s+0\.450000\s+0\s+360$",geometry,re.MULTILINE))==1,
        "four_inner_ports_remain_diameter_1p50":len(re.findall(r"^SH3_DRBase_(?:MXC50mK|Still|4K|60K)_ColdFingerPortCutShape\.Parameters\s+0\s+0\.750000\s+",geometry,re.MULTILINE))==4,
        "neck_matches_outer_interface_port":math.isclose(TRANSITION_NECK_OUTER_RADIUS_CM,VACUUM_JACKET_INTERFACE_PORT_RADIUS_CM),
        "upper_support_optical_cut_present":"NF2_OuterSupport_Al_TopMountAnnulus.Shape SH3_OptV2_NF2_TopMount_WithOpticalCutShape" in geometry,
        "support_cut_exceeds_signal_radius":SUPPORT_OPTICAL_CUT_RADIUS_CM>2.7,
        "front_bgo_square_recess_present":"SH3_BGO40_FrontOpticalAnnulus.Shape SH3_OptV2_BGOFront_SquareRecessShape" in geometry,
        "four_w_frame_bars":len(re.findall(r"^Volume SH3_OptV2_W_Frame_",geometry,re.MULTILINE))==4,
        "no_w_grid_or_multihole_collimator":not any(token in geometry for token in ("W_Multihole_Collimator","W_Grid","W_Mesh")),
        "w_inner_square_does_not_clip_r2p7_circle":W_FRAME_INNER_HALF_CM>=2.7,
        "five_bent_cold_finger_parts":len(re.findall(r"^Volume SH3_OptV2_Cu_",geometry,re.MULTILINE))==5,
        "cold_finger_fits_port":math.sqrt(2)*COLD_HALF_CM<PORT_RADIUS_CM,
        "mxc_pad_touches_plate":math.isclose(PAD_Z1_CM,MXC_PLATE_BOTTOM_Z_CM),
        "mxc_pad_clears_holes":pad_clearance>0,
        "all_flattened_chimney_volumes_present":all(name in declared for name in flattened_names),
        "no_chimney_container_mother":not re.search(r"^\S+\.Mother SH3_ChimneyFrame$",geometry,re.MULTILINE),
        "unique_volume_and_copy_names":len(declared)==len(set(declared)) and len(copies)==len(set(copies)),
        "all_mothers_resolve":all(m in names for m in mothers),
        "detector_retains_6tes_3bgo":len(re.findall(r"^MDCalorimeter D\d$",detector,re.MULTILINE))==6 and len(re.findall(r"^Scintillator SH3_BGO40_",detector,re.MULTILINE))==3,
    }
    return {"status":"PASS__SH3_ASSEMBLY_OPT_V2_STATIC" if all(checks.values()) else "FAIL","generated_at_utc":datetime.now(timezone.utc).isoformat(),"physics_status":"OPTIMIZED ASSEMBLY GEOMETRY ONLY — UNTRANSPORTED/UNTHERMALLY-SIZED","checks":checks,"counts":{"declared_volumes":len(declared),"copy_placements":len(copies),"flattened_chimney_top_levels":len(flattened_names)},"clearances":{"chimney_bottom_z_cm":chimney_bottom,"dr_vacuum_jacket_bottom_z_cm":DR_VACUUM_JACKET_BOTTOM_Z_CM,"bottom_clearance_cm":chimney_bottom-DR_VACUUM_JACKET_BOTTOM_Z_CM,"cold_finger_corner_to_port_clearance_cm":PORT_RADIUS_CM-math.sqrt(2)*COLD_HALF_CM,"mxc_pad_to_nearest_hole_edge_cm":pad_clearance,"support_optical_cut_radius_cm":SUPPORT_OPTICAL_CUT_RADIUS_CM}}


def main() -> int:
    inputs=base.verify_inputs()
    component=patch_front_bgo_square_recess(base.CHIMNEY_COMPONENT.read_text(encoding="utf-8"))
    chimney,flattened_names=flatten_chimney(component)
    dr_source=base.DR_GEO.read_text(encoding="utf-8")
    dr_geometry=patch_dr_ports_and_support_window(dr_source)
    detector=base.CHIMNEY_DET.read_text(encoding="utf-8")
    geometry=geometry_text(dr_geometry,chimney)
    outputs={OUTPUT_GEO:geometry,OUTPUT_SETUP:setup_text(),OUTPUT_DET:detector,OUTPUT_MATERIALS:base.CHIMNEY_MATERIALS.read_text(encoding="utf-8"),OUTPUT_FIGURE:svg_text(),OUTPUT_DETAIL_FIGURE:detail_svg_text()}
    for path,text in outputs.items(): atomic_text(path,text)
    validation=validate(geometry,detector,flattened_names,dr_source)
    atomic_json(OUTPUT_STATIC,validation)
    if validation["status"]!="PASS__SH3_ASSEMBLY_OPT_V2_STATIC": raise BuildError("OptV2 static validation failed")
    manifest={"status":"PASS__SH3_ASSEMBLY_OPT_V2_BUILT","generated_at_utc":datetime.now(timezone.utc).isoformat(),"component_identity":"SH3_Chimney_DR_Assembly_OptV2","physics_status":"GEOMETRY ONLY — NO TRANSPORT/ACTIVATION/RESPONSE/TIMING CLAIM","pinned_inputs":inputs,"changes_from_v1":{"port_center_z_cm":{"old":-5.2,"new":PORT_CENTER_Z_CM},"chimney_origin_local_cm":[CHIMNEY_ORIGIN_X_CM,0.0,CHIMNEY_ORIGIN_Z_CM],"bottom_clearance_cm":PORT_CENTER_Z_CM-CHIMNEY_OUTER_RADIUS_CM-DR_VACUUM_JACKET_BOTTOM_Z_CM,"al_transition":{"frustum_x_extent_cm":[TRANSITION_X0_CM,TRANSITION_X1_CM],"large_radii_cm":[TRANSITION_LARGE_INNER_RADIUS_CM,TRANSITION_LARGE_OUTER_RADIUS_CM],"small_radii_cm":[TRANSITION_SMALL_INNER_RADIUS_CM,TRANSITION_SMALL_OUTER_RADIUS_CM],"interface_neck_x_extent_cm":[TRANSITION_NECK_X0_CM,TRANSITION_NECK_X1_CM],"interface_neck_radii_cm":[TRANSITION_NECK_INNER_RADIUS_CM,TRANSITION_NECK_OUTER_RADIUS_CM],"outer_vacuum_jacket_interface_diameter_cm":2*VACUUM_JACKET_INTERFACE_PORT_RADIUS_CM,"inner_four_cold_stage_port_diameter_cm":2*PORT_RADIUS_CM},"upper_support_optical_cut_radius_cm":SUPPORT_OPTICAL_CUT_RADIUS_CM,"w_frame":{"type":"four-bar square frame; no grid/multihole structure","x_extent_cm":[W_FRAME_X0_CM,W_FRAME_X1_CM],"outer_side_cm":2*W_FRAME_OUTER_HALF_CM,"inner_clear_side_cm":2*W_FRAME_INNER_HALF_CM},"cold_finger_route":{"port_run_x_cm":[PORT_RUN_X0_CM,PORT_RUN_X1_CM],"dogleg_y_cm":[0.0,DOGLEG_Y1_CM],"mxc_pad_z_cm":[PAD_Z0_CM,PAD_Z1_CM]}},"mass_proxy":mass_proxy(),"not_claimed":["thermal conductance, heat load, vibration, structural or manufacturing closure","transport, activation, detector response, Poisson timing, background or sensitivity"],"outputs":{path.name:file_record(path) for path in outputs},"static_validation":file_record(OUTPUT_STATIC)}
    atomic_json(OUTPUT_MANIFEST,manifest)
    print(json.dumps({"status":manifest["status"],"static":validation["status"],"manifest":str(OUTPUT_MANIFEST)},indent=2))
    return 0


if __name__=="__main__": raise SystemExit(main())
