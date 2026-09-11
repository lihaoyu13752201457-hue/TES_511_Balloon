#!/usr/bin/env python3
"""Build SH3 OptV3 with a boolean-welded chimney/DR outer aluminium shell.

OptV3 preserves the raised axis, optical support cut, W square frame, and bent
cold finger from OptV2, but rejects the frustum/nozzle interface.  The complete
chimney side shell, its extension, the curved 300 K DR side shell, and the DR
bottom cap become one union/subtraction CSG solid with an open branch bore.
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
V2_BUILDER = SH3 / "assembly_opt_v2/code/build_sh3_assembly_opt_v2.py"

spec = importlib.util.spec_from_file_location("sh3_assembly_opt_v2_builder", V2_BUILDER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load OptV2 builder: {V2_BUILDER}")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"
FIGURES = PACKAGE / "figures"
OUTPUT_GEO = GEOMETRY / "SH3_Assembly_OptV3.geo"
OUTPUT_SETUP = GEOMETRY / "SH3_Assembly_OptV3.geo.setup"
OUTPUT_DET = GEOMETRY / "SH3_Assembly_OptV3.det"
OUTPUT_MATERIALS = GEOMETRY / "Materials_SH3_Assembly_OptV3.geo"
OUTPUT_DETAIL = FIGURES / "sh3_assembly_opt_v3_welded_saddle_detail.svg"
OUTPUT_MANIFEST = DATA / "assembly_opt_v3_manifest.json"
OUTPUT_STATIC = AUDIT / "assembly_opt_v3_static_validation.json"

PORT_CENTER_Z_CM = v2.PORT_CENTER_Z_CM
PORT_RADIUS_CM = v2.PORT_RADIUS_CM
CHIMNEY_ORIGIN_X_CM = v2.CHIMNEY_ORIGIN_X_CM
CHIMNEY_OUTER_RADIUS_CM = v2.CHIMNEY_OUTER_RADIUS_CM
CHIMNEY_INNER_RADIUS_CM = v2.TRANSITION_LARGE_INNER_RADIUS_CM
CHIMNEY_SIDE_X0_CM = CHIMNEY_ORIGIN_X_CM - 10.20
CHIMNEY_SIDE_X1_CM = CHIMNEY_ORIGIN_X_CM + 10.90
BRANCH_UNION_X0_CM = CHIMNEY_SIDE_X0_CM
BRANCH_UNION_X1_CM = -15.00
BRANCH_BORE_X0_CM = CHIMNEY_SIDE_X0_CM - 0.35
BRANCH_BORE_X1_CM = -14.50
DR_SIDE_INNER_RADIUS_CM = 20.10
DR_SIDE_OUTER_RADIUS_CM = 20.60
DR_SIDE_Z0_CM = -13.60
DR_SIDE_Z1_CM = 37.50
DR_BOTTOM_Z0_CM = -14.10
DR_BOTTOM_Z1_CM = -13.60
ABSORBED_CHIMNEY_SIDE_NAME = "SH3_BGO_MechanicalAl_SideShell_3mm"


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


def remove_absorbed_chimney_side_shell(chimney: str) -> str:
    pattern = re.compile(
        r"^Volume SH3_BGO_MechanicalAl_SideShell_3mm\n"
        r"(?:^SH3_BGO_MechanicalAl_SideShell_3mm\..*\n){6}",
        re.MULTILINE,
    )
    chimney, count = pattern.subn("", chimney, count=1)
    if count != 1:
        raise BuildError(f"expected one absorbed chimney side-shell block, removed {count}")
    return chimney


def welded_outer_shell_text() -> str:
    outer_half = 0.5 * (BRANCH_UNION_X1_CM-BRANCH_UNION_X0_CM)
    outer_center = 0.5 * (BRANCH_UNION_X0_CM+BRANCH_UNION_X1_CM)
    bore_half = 0.5 * (BRANCH_BORE_X1_CM-BRANCH_BORE_X0_CM)
    bore_center = 0.5 * (BRANCH_BORE_X0_CM+BRANCH_BORE_X1_CM)
    return f"""// OptV3: one welded 300 K Al shell. The chimney branch is unioned into the
// curved DR side shell and bottom cap; the branch bore and DR cavity are then
// subtracted. This creates a continuous saddle joint, not a plane/nozzle contact.
Shape PCON SH3_OptV3_DRFullSideShellShape
SH3_OptV3_DRFullSideShellShape.Parameters 0 360 2 {DR_SIDE_Z0_CM:.6f} {DR_SIDE_INNER_RADIUS_CM:.6f} {DR_SIDE_OUTER_RADIUS_CM:.6f} {DR_SIDE_Z1_CM:.6f} {DR_SIDE_INNER_RADIUS_CM:.6f} {DR_SIDE_OUTER_RADIUS_CM:.6f}
Shape PCON SH3_OptV3_DRBottomCapShape
SH3_OptV3_DRBottomCapShape.Parameters 0 360 2 {DR_BOTTOM_Z0_CM:.6f} 0 {DR_SIDE_OUTER_RADIUS_CM:.6f} {DR_BOTTOM_Z1_CM:.6f} 0 {DR_SIDE_OUTER_RADIUS_CM:.6f}
Orientation SH3_OptV3_IdentityOrientation
SH3_OptV3_IdentityOrientation.Position 0 0 0
Shape Union SH3_OptV3_DRSidePlusBottomShape
SH3_OptV3_DRSidePlusBottomShape.Parameters SH3_OptV3_DRFullSideShellShape SH3_OptV3_DRBottomCapShape SH3_OptV3_IdentityOrientation

Shape TUBS SH3_OptV3_ChimneyBranchOuterSolid
SH3_OptV3_ChimneyBranchOuterSolid.Parameters 0 {CHIMNEY_OUTER_RADIUS_CM:.6f} {outer_half:.6f} 0 360
Orientation SH3_OptV3_ChimneyBranchOuterOrientation
SH3_OptV3_ChimneyBranchOuterOrientation.Position {outer_center:.6f} 0 {PORT_CENTER_Z_CM:.6f}
SH3_OptV3_ChimneyBranchOuterOrientation.Rotation 0 90 0
Shape Union SH3_OptV3_DRPlusChimneyOuterUnionShape
SH3_OptV3_DRPlusChimneyOuterUnionShape.Parameters SH3_OptV3_DRSidePlusBottomShape SH3_OptV3_ChimneyBranchOuterSolid SH3_OptV3_ChimneyBranchOuterOrientation

Shape TUBS SH3_OptV3_ChimneyBranchInnerBore
SH3_OptV3_ChimneyBranchInnerBore.Parameters 0 {CHIMNEY_INNER_RADIUS_CM:.6f} {bore_half:.6f} 0 360
Orientation SH3_OptV3_ChimneyBranchInnerBoreOrientation
SH3_OptV3_ChimneyBranchInnerBoreOrientation.Position {bore_center:.6f} 0 {PORT_CENTER_Z_CM:.6f}
SH3_OptV3_ChimneyBranchInnerBoreOrientation.Rotation 0 90 0
Shape Subtraction SH3_OptV3_WeldedShellWithOpenBranchShape
SH3_OptV3_WeldedShellWithOpenBranchShape.Parameters SH3_OptV3_DRPlusChimneyOuterUnionShape SH3_OptV3_ChimneyBranchInnerBore SH3_OptV3_ChimneyBranchInnerBoreOrientation

Shape PCON SH3_OptV3_DRMainVacuumCavityShape
SH3_OptV3_DRMainVacuumCavityShape.Parameters 0 360 2 {DR_SIDE_Z0_CM:.6f} 0 {DR_SIDE_INNER_RADIUS_CM:.6f} {DR_SIDE_Z1_CM:.6f} 0 {DR_SIDE_INNER_RADIUS_CM:.6f}
Shape Subtraction SH3_OptV3_WeldedSaddleOuterShellShape
SH3_OptV3_WeldedSaddleOuterShellShape.Parameters SH3_OptV3_WeldedShellWithOpenBranchShape SH3_OptV3_DRMainVacuumCavityShape SH3_OptV3_IdentityOrientation

Volume SH3_DRBase_VacuumJacket_PortedSideShell
SH3_DRBase_VacuumJacket_PortedSideShell.Material Aluminium
SH3_DRBase_VacuumJacket_PortedSideShell.Visibility 1
SH3_DRBase_VacuumJacket_PortedSideShell.Shape SH3_OptV3_WeldedSaddleOuterShellShape
SH3_DRBase_VacuumJacket_PortedSideShell.Position 0 0 0
SH3_DRBase_VacuumJacket_PortedSideShell.Mother InstrumentFrame
"""


def patch_outer_shell_to_welded_boolean(dr_geometry: str) -> str:
    start = "// 300 K aluminium vacuum jacket; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.\n"
    end = "SH3_DRBase_VacuumJacket_BottomCap.Mother InstrumentFrame\n"
    if dr_geometry.count(start) != 1 or dr_geometry.count(end) != 1:
        raise BuildError("outer vacuum-jacket replacement boundary is not unique")
    i0 = dr_geometry.index(start)
    i1 = dr_geometry.index(end, i0) + len(end)
    return dr_geometry[:i0] + welded_outer_shell_text() + dr_geometry[i1:]


def geometry_text(dr_geometry: str, chimney: str) -> str:
    dr_geometry = dr_geometry.replace(
        "Include Materials_SH3_DR_Base.geo",
        "Include Materials_SH3_Assembly_OptV3.geo",
        1,
    )
    return (
        dr_geometry.rstrip()
        + "\n\n// BEGIN SH3_ASSEMBLY_OPT_V3\n"
        + "// Boolean-welded chimney/DR outer Al shell; no OptV2 frustum or nozzle.\n"
        + "// Geometry only; no structural, transport, timing, or sensitivity authority.\n"
        + "// BEGIN FLATTENED_SH3_CHIMNEY_OPT_V3\n"
        + chimney.rstrip()
        + "\n// END FLATTENED_SH3_CHIMNEY_OPT_V3\n\n"
        + v2.w_frame_text()
        + v2.cold_finger_text()
        + "// END SH3_ASSEMBLY_OPT_V3\n"
    )


def setup_text() -> str:
    return """Name SH3_Chimney_DR_Assembly_OptV3
Version 1
Include SH3_Assembly_OptV3.geo
Include SH3_Assembly_OptV3.det
SurroundingSphere 95 0 0 8 95
"""


def detail_svg_text() -> str:
    width, height = 1800, 1000
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="1800" height="1000" fill="#fff"/>
<text x="900" y="45" text-anchor="middle" font-family="DejaVu Sans" font-size="30" font-weight="700">SH3 OptV3 — boolean-welded saddle joint</text>
<text x="900" y="78" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">One aluminium CSG solid: DR side shell + bottom cap + chimney branch − branch bore − DR cavity</text>
<rect x="70" y="115" width="1040" height="790" fill="#f8fafc" stroke="#8796a5"/>
<text x="590" y="150" text-anchor="middle" font-family="DejaVu Sans" font-size="22" font-weight="700">x′/z′ section through branch axis</text>
<path d="M 820 190 L 820 760 Q 820 820 760 820 L 655 820 L 655 782 L 760 782 Q 782 782 782 760 L 782 190 Z" fill="#8b98a3" opacity="0.92"/>
<path d="M 140 305 L 630 305 Q 775 305 800 445 L 800 575 Q 770 695 630 695 L 140 695 Z" fill="#65757e"/>
<path d="M 140 318 L 630 318 Q 745 318 782 445 L 782 575 Q 740 682 630 682 L 140 682 Z" fill="#ffffff"/>
<line x1="140" y1="500" x2="970" y2="500" stroke="#c62828" stroke-width="2" stroke-dasharray="9 7"/>
<rect x="140" y="493" width="765" height="14" fill="#9a5414"/>
<text x="170" y="285" font-family="DejaVu Sans" font-size="18">3 mm chimney Al shell continues into the curved DR shell</text>
<text x="705" y="355" font-family="DejaVu Sans" font-size="17" fill="#34454d">continuous saddle intersection</text>
<text x="835" y="220" font-family="DejaVu Sans" font-size="17" fill="#34454d">300 K DR Al shell</text>
<text x="170" y="535" font-family="DejaVu Sans" font-size="17" fill="#9a5414">bent Cu cold finger on z′=-2.80 cm axis</text>
<text x="170" y="875" font-family="DejaVu Sans" font-size="17" fill="#2e7d32">chimney bottom z′=-13.85 cm; DR bottom z′=-14.10 cm; clearance 0.25 cm</text>
<rect x="1150" y="115" width="585" height="790" fill="#f8fafc" stroke="#8796a5"/>
<text x="1442" y="150" text-anchor="middle" font-family="DejaVu Sans" font-size="22" font-weight="700">CSG construction</text>
<rect x="1210" y="205" width="465" height="75" rx="8" fill="#dce4e9" stroke="#5f6d78"/>
<text x="1442" y="237" text-anchor="middle" font-family="DejaVu Sans" font-size="17">DR side shell ∪ DR bottom cap</text>
<text x="1442" y="262" text-anchor="middle" font-family="DejaVu Sans" font-size="15">retained 0.50 cm outer aluminium</text>
<text x="1442" y="323" text-anchor="middle" font-family="DejaVu Sans" font-size="28">∪</text>
<rect x="1210" y="350" width="465" height="75" rx="8" fill="#71828c" stroke="#40505a"/>
<text x="1442" y="382" text-anchor="middle" font-family="DejaVu Sans" font-size="17" fill="#fff">full chimney/extension outer solid</text>
<text x="1442" y="407" text-anchor="middle" font-family="DejaVu Sans" font-size="15" fill="#fff">R = {CHIMNEY_OUTER_RADIUS_CM:.2f} cm</text>
<text x="1442" y="470" text-anchor="middle" font-family="DejaVu Sans" font-size="28">−</text>
<rect x="1210" y="495" width="465" height="75" rx="8" fill="#fff" stroke="#c75b3b" stroke-width="3"/>
<text x="1442" y="527" text-anchor="middle" font-family="DejaVu Sans" font-size="17">open chimney branch bore</text>
<text x="1442" y="552" text-anchor="middle" font-family="DejaVu Sans" font-size="15">R = {CHIMNEY_INNER_RADIUS_CM:.2f} cm</text>
<text x="1442" y="614" text-anchor="middle" font-family="DejaVu Sans" font-size="28">−</text>
<rect x="1210" y="640" width="465" height="75" rx="8" fill="#fff" stroke="#4a79b8" stroke-width="3"/>
<text x="1442" y="672" text-anchor="middle" font-family="DejaVu Sans" font-size="17">main DR vacuum cavity</text>
<text x="1442" y="697" text-anchor="middle" font-family="DejaVu Sans" font-size="15">trims branch at the curved inner surface</text>
<text x="1442" y="775" text-anchor="middle" font-family="DejaVu Sans" font-size="18" font-weight="700" fill="#2e7d32">Result: one continuous Al saddle shell</text>
<text x="1442" y="815" text-anchor="middle" font-family="DejaVu Sans" font-size="16">No frustum · no small nozzle · no plane contact</text>
<text x="1442" y="855" text-anchor="middle" font-family="DejaVu Sans" font-size="15" fill="#b71c1c">Structural/FEA and weld-process closure still pending</text>
</svg>
'''


def validate(geometry: str, detector: str, flattened_names: list[str], dr_source: str) -> dict[str, object]:
    retained_names = [name for name in flattened_names if name != ABSORBED_CHIMNEY_SIDE_NAME]
    report = v2.validate(geometry, detector, retained_names, dr_source)
    checks = dict(report["checks"])
    for key in (
        "five_ports_moved_to_minus2p8",
        "transition_shell_present",
        "transition_large_end_matches_chimney",
        "transition_neck_present",
        "frustum_meets_interface_neck",
        "neck_crosses_outer_jacket_only",
        "outer_vacuum_port_is_diameter_2p10",
        "neck_matches_outer_interface_port",
    ):
        checks.pop(key, None)
    checks.update(
        {
            "four_inner_ports_moved_to_minus2p8": len(re.findall(
                r"^SH3_DRBase_(?:MXC50mK|Still|4K|60K)_ColdFingerPortCutOrientation\.Position\s+[-+0-9.eE]+\s+0\s+-2\.800000$",
                geometry,
                re.MULTILINE,
            )) == 4,
            "optv2_frustum_and_nozzle_absent": not any(token in geometry for token in (
                "SH3_OptV2_Al_VacuumJacketTransitionShroud",
                "SH3_OptV2_Al_VacuumJacketInterfaceNeck",
            )),
            "separate_chimney_side_shell_absent": f"Volume {ABSORBED_CHIMNEY_SIDE_NAME}" not in geometry,
            "separate_dr_bottom_cap_absent": "Volume SH3_DRBase_VacuumJacket_BottomCap" not in geometry,
            "dr_side_and_bottom_unioned": "Shape Union SH3_OptV3_DRSidePlusBottomShape" in geometry,
            "chimney_outer_unioned_into_dr": "Shape Union SH3_OptV3_DRPlusChimneyOuterUnionShape" in geometry,
            "open_branch_bore_subtracted": "Shape Subtraction SH3_OptV3_WeldedShellWithOpenBranchShape" in geometry,
            "dr_cavity_trims_branch_to_saddle": "Shape Subtraction SH3_OptV3_WeldedSaddleOuterShellShape" in geometry,
            "outer_jacket_uses_welded_saddle_shape": "SH3_DRBase_VacuumJacket_PortedSideShell.Shape SH3_OptV3_WeldedSaddleOuterShellShape" in geometry,
            "branch_shell_is_3mm_radial": math.isclose(CHIMNEY_OUTER_RADIUS_CM-CHIMNEY_INNER_RADIUS_CM, 0.30),
            "branch_extension_reaches_inside_curved_wall": BRANCH_UNION_X1_CM > -DR_SIDE_INNER_RADIUS_CM,
        }
    )
    report["checks"] = checks
    report["status"] = "PASS__SH3_ASSEMBLY_OPT_V3_STATIC" if all(checks.values()) else "FAIL"
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["physics_status"] = "BOOLEAN-WELDED ASSEMBLY GEOMETRY ONLY — UNSTRUCTURALLY/UNTHERMALLY-SIZED"
    report["csg_contract"] = {
        "branch_outer_radius_cm": CHIMNEY_OUTER_RADIUS_CM,
        "branch_inner_radius_cm": CHIMNEY_INNER_RADIUS_CM,
        "branch_union_x_extent_cm": [BRANCH_UNION_X0_CM, BRANCH_UNION_X1_CM],
        "branch_bore_x_extent_cm": [BRANCH_BORE_X0_CM, BRANCH_BORE_X1_CM],
        "outer_shell_formula": "((DR side shell UNION DR bottom cap) UNION chimney outer solid) MINUS chimney bore MINUS DR main cavity",
    }
    return report


def main() -> int:
    inputs = v2.base.verify_inputs()
    inputs[str(V2_BUILDER)] = file_record(V2_BUILDER)
    component = v2.patch_front_bgo_square_recess(
        v2.base.CHIMNEY_COMPONENT.read_text(encoding="utf-8")
    )
    chimney, flattened_names = v2.flatten_chimney(component)
    chimney = remove_absorbed_chimney_side_shell(chimney)
    dr_source = v2.base.DR_GEO.read_text(encoding="utf-8")
    dr_geometry = v2.patch_dr_ports_and_support_window(dr_source)
    dr_geometry = patch_outer_shell_to_welded_boolean(dr_geometry)
    detector = v2.base.CHIMNEY_DET.read_text(encoding="utf-8")
    geometry = geometry_text(dr_geometry, chimney)
    outputs = {
        OUTPUT_GEO: geometry,
        OUTPUT_SETUP: setup_text(),
        OUTPUT_DET: detector,
        OUTPUT_MATERIALS: v2.base.CHIMNEY_MATERIALS.read_text(encoding="utf-8"),
        OUTPUT_DETAIL: detail_svg_text(),
    }
    for path, text in outputs.items():
        atomic_text(path, text)
    validation = validate(geometry, detector, flattened_names, dr_source)
    atomic_json(OUTPUT_STATIC, validation)
    if validation["status"] != "PASS__SH3_ASSEMBLY_OPT_V3_STATIC":
        failed = [name for name, ok in validation["checks"].items() if not ok]
        raise BuildError(f"OptV3 static validation failed: {failed}")
    manifest = {
        "status": "PASS__SH3_ASSEMBLY_OPT_V3_BUILT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_Chimney_DR_Assembly_OptV3",
        "physics_status": "GEOMETRY ONLY — NO STRUCTURAL/TRANSPORT/RESPONSE/TIMING CLAIM",
        "interface_change": {
            "rejected": "OptV2 frustum plus diameter-2.10-cm nozzle",
            "adopted": "single boolean-unioned welded saddle shell",
            "outer_shell_formula": validation["csg_contract"]["outer_shell_formula"],
            "chimney_shell_radii_cm": [CHIMNEY_INNER_RADIUS_CM, CHIMNEY_OUTER_RADIUS_CM],
            "branch_union_x_extent_cm": [BRANCH_UNION_X0_CM, BRANCH_UNION_X1_CM],
            "raised_axis_z_cm": PORT_CENTER_Z_CM,
            "bottom_clearance_cm": PORT_CENTER_Z_CM-CHIMNEY_OUTER_RADIUS_CM-v2.DR_VACUUM_JACKET_BOTTOM_Z_CM,
            "inner_four_stage_port_diameter_cm": 2*PORT_RADIUS_CM,
        },
        "retained_from_opt_v2": [
            "diameter-6.00-cm optical cut through upper support",
            "four-bar W square frame with 5.40-cm clear inner square",
            "raised bent copper cold finger and MXC contact pad",
            "six TES and three active BGO detector declarations",
        ],
        "pinned_inputs": inputs,
        "not_claimed": [
            "weld process, flange, fastener, fatigue, FEA, vibration, pressure or structural closure",
            "thermal conductance or heat-load closure",
            "transport, activation, detector response, timing, background or sensitivity",
        ],
        "outputs": {path.name: file_record(path) for path in outputs},
        "static_validation": file_record(OUTPUT_STATIC),
    }
    atomic_json(OUTPUT_MANIFEST, manifest)
    print(json.dumps({
        "status": manifest["status"],
        "static": validation["status"],
        "manifest": str(OUTPUT_MANIFEST),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
