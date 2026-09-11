#!/usr/bin/env python3
"""Build the non-overwriting SH3 chimney + pure-DR assembly.

The pure-DR base stays authoritative and the chimney component is flattened
into its retained 45-degree InstrumentFrame.  A new copper cold-finger route
continues the chimney stub through the five coaxial ports, doglegs inside the
MXC can, and terminates in a contact pad whose upper face touches the underside
of the retained MXC copper plate.  This is geometry authority only.
"""

from __future__ import annotations

import hashlib
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
DR_BASE = SH3 / "dr_base"

GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"
FIGURES = PACKAGE / "figures"

CHIMNEY_COMPONENT = SH3 / "geometry/SH3_Chimney_Component.geo"
CHIMNEY_DET = SH3 / "geometry/SH3_Chimney.det"
CHIMNEY_MATERIALS = SH3 / "geometry/Materials_SH3.geo"
CHIMNEY_MANIFEST = SH3 / "data/component_manifest.json"
CHIMNEY_STATIC = SH3 / "audit/static_validation.json"
CHIMNEY_OVERLAP = SH3 / "audit/overlap_validation.json"

DR_GEO = DR_BASE / "geometry/SH3_PureDR_Base.geo"
DR_MATERIALS = DR_BASE / "geometry/Materials_SH3_DR_Base.geo"
DR_MANIFEST = DR_BASE / "data/dr_base_manifest.json"
DR_STATIC = DR_BASE / "audit/dr_base_static_validation.json"
DR_OVERLAP = DR_BASE / "audit/dr_base_overlap_validation.json"

PINNED_INPUTS = {
    CHIMNEY_COMPONENT: "4064a17380d9cb23eadd8e5cad081bcdc9bd51a722fafb11adbc18862d23afee",
    CHIMNEY_DET: "12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9",
    CHIMNEY_MATERIALS: "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
    CHIMNEY_MANIFEST: "9bec3cd86815a8393446e428b59f5a33a27a3a9640698c0b43f0a96958dbe542",
    CHIMNEY_STATIC: "373757188c3bc2b020dbcdee389c68e2aac820121d2555089505cd1c6cf71c26",
    CHIMNEY_OVERLAP: "3672a7d4025aed59700d77292f38466be110cc592b32e5bfed9d9fb009880bc0",
    DR_GEO: "bef7520e6dec55baa61507c18b87df29b2124c89753ec8689817f20f423b9b32",
    DR_MATERIALS: "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
    DR_MANIFEST: "649ce222a6dd53411cf5a3213826095c06eed9ab1f5519fd0e91a2cad8896109",
    DR_STATIC: "3d11a79475a2d1a2b3a13a29afdb2a612b8bf0db15ff8fb2701bb82ff506a882",
    DR_OVERLAP: "0d612fcd69e6387147329aab3c1b7df53f7bd3fb1132f9b2ac9df3e1b3321d16",
}

OUTPUT_GEO = GEOMETRY / "SH3_Assembly.geo"
OUTPUT_SETUP = GEOMETRY / "SH3_Assembly.geo.setup"
OUTPUT_DET = GEOMETRY / "SH3_Assembly.det"
OUTPUT_MATERIALS = GEOMETRY / "Materials_SH3_Assembly.geo"
OUTPUT_FIGURE = FIGURES / "sh3_assembly_local_xz_section.svg"
OUTPUT_MANIFEST = DATA / "assembly_manifest.json"
OUTPUT_STATIC = AUDIT / "assembly_static_validation.json"

# Assembly coordinates are in the retained DR InstrumentFrame.
PORT_CENTER_Z_CM = -5.20
DR_OUTER_NEGATIVE_X_CM = -20.60
CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM = 10.90
DOCK_CLEARANCE_CM = 0.05
CHIMNEY_ORIGIN_X_CM = (
    DR_OUTER_NEGATIVE_X_CM
    - CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM
    - DOCK_CLEARANCE_CM
)
CHIMNEY_ORIGIN_Y_CM = 0.0
CHIMNEY_ORIGIN_Z_CM = PORT_CENTER_Z_CM

CHIMNEY_STUB_LOCAL_X1_CM = 6.80
COLD_FINGER_HALF_WIDTH_CM = 0.16
COLD_FINGER_PORT_RUN_X0_CM = CHIMNEY_ORIGIN_X_CM + CHIMNEY_STUB_LOCAL_X1_CM
COLD_FINGER_PORT_RUN_X1_CM = -14.86
COLD_FINGER_DOGLEG_X0_CM = -14.86
COLD_FINGER_DOGLEG_X1_CM = -14.54
COLD_FINGER_DOGLEG_Y0_CM = 0.0
COLD_FINGER_DOGLEG_Y1_CM = 1.10
COLD_FINGER_INTERNAL_X0_CM = -14.54
COLD_FINGER_INTERNAL_X1_CM = 5.89
COLD_FINGER_STEM_X_CM = 6.05
COLD_FINGER_STEM_Y_CM = 1.10
COLD_FINGER_STEM_Z0_CM = -5.04
COLD_FINGER_STEM_Z1_CM = -0.55
MXC_PAD_RADIUS_CM = 0.35
MXC_PAD_Z0_CM = -0.55
MXC_PAD_Z1_CM = -0.20
MXC_PLATE_BOTTOM_Z_CM = -0.20
MXC_HOLE_RADIUS_CM = 1.1629703349613
PORT_RADIUS_CM = 0.75


class BuildError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256_bytes(data)}


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


def verify_inputs() -> dict[str, dict[str, object]]:
    missing = [str(path) for path in PINNED_INPUTS if not path.is_file()]
    if missing:
        raise BuildError(f"missing pinned assembly input(s): {missing}")
    records: dict[str, dict[str, object]] = {}
    for path, expected in PINNED_INPUTS.items():
        current = sha256_path(path)
        if current != expected:
            raise BuildError(f"assembly input drift: {path}: {current} != {expected}")
        records[str(path)] = file_record(path)

    statuses = {
        CHIMNEY_MANIFEST: "PASS__SH3_COMPONENT_BUILT",
        CHIMNEY_STATIC: "PASS__SH3_COMPONENT_STATIC",
        CHIMNEY_OVERLAP: "PASS__SH3_STANDALONE_OVERLAP_NO_TRANSPORT",
        DR_MANIFEST: "PASS__SH3_PURE_DR_BASE_BUILT",
        DR_STATIC: "PASS__SH3_PURE_DR_BASE_STATIC",
        DR_OVERLAP: "PASS__SH3_PURE_DR_BASE_OVERLAP_NO_TRANSPORT",
    }
    for path, expected in statuses.items():
        actual = json.loads(path.read_text(encoding="utf-8")).get("status")
        if actual != expected:
            raise BuildError(f"input receipt is not authoritative: {path}: {actual}")
    return records


def flatten_chimney(component: str) -> tuple[str, list[str]]:
    """Reparent top-level chimney volumes and apply one rigid translation."""
    names = re.findall(r"^(\S+)\.Mother SH3_ChimneyFrame\s*$", component, re.MULTILINE)
    if not names:
        raise BuildError("no top-level SH3 chimney placements found")
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}\.Position\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            re.MULTILINE,
        )
        match = pattern.search(component)
        if match is None:
            raise BuildError(f"top-level chimney volume has no position: {name}")
        x, y, z = (float(value) for value in match.groups())
        replacement = (
            f"{name}.Position "
            f"{x + CHIMNEY_ORIGIN_X_CM:.12g} "
            f"{y + CHIMNEY_ORIGIN_Y_CM:.12g} "
            f"{z + CHIMNEY_ORIGIN_Z_CM:.12g}"
        )
        component, count = pattern.subn(replacement, component, count=1)
        if count != 1:
            raise BuildError(f"failed to translate chimney volume: {name}")
        component = component.replace(
            f"{name}.Mother SH3_ChimneyFrame", f"{name}.Mother InstrumentFrame", 1
        )
    if "Mother SH3_ChimneyFrame" in component:
        raise BuildError("unflattened SH3_ChimneyFrame mother remains")
    return component, names


def brik_volume(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> str:
    return "\n".join(
        (
            f"Volume {name}",
            f"{name}.Material Copper",
            f"{name}.Visibility 1",
            f"{name}.Shape BRIK {(x1-x0)/2:.6f} {(y1-y0)/2:.6f} {(z1-z0)/2:.6f}",
            f"{name}.Position {(x0+x1)/2:.6f} {(y0+y1)/2:.6f} {(z0+z1)/2:.6f}",
            f"{name}.Mother InstrumentFrame",
            "",
        )
    )


def cold_finger_text() -> str:
    h = COLD_FINGER_HALF_WIDTH_CM
    port_run = brik_volume(
        "SH3_Assembly_Cu_ColdFinger_PortRun",
        COLD_FINGER_PORT_RUN_X0_CM,
        COLD_FINGER_PORT_RUN_X1_CM,
        -h,
        h,
        PORT_CENTER_Z_CM - h,
        PORT_CENTER_Z_CM + h,
    )
    dogleg = brik_volume(
        "SH3_Assembly_Cu_ColdFinger_InsideMXC_Dogleg",
        COLD_FINGER_DOGLEG_X0_CM,
        COLD_FINGER_DOGLEG_X1_CM,
        COLD_FINGER_DOGLEG_Y0_CM,
        COLD_FINGER_DOGLEG_Y1_CM,
        PORT_CENTER_Z_CM - h,
        PORT_CENTER_Z_CM + h,
    )
    internal = brik_volume(
        "SH3_Assembly_Cu_ColdFinger_InternalRun",
        COLD_FINGER_INTERNAL_X0_CM,
        COLD_FINGER_INTERNAL_X1_CM,
        COLD_FINGER_STEM_Y_CM - h,
        COLD_FINGER_STEM_Y_CM + h,
        PORT_CENTER_Z_CM - h,
        PORT_CENTER_Z_CM + h,
    )
    stem = brik_volume(
        "SH3_Assembly_Cu_ColdFinger_MXCStem",
        COLD_FINGER_STEM_X_CM - h,
        COLD_FINGER_STEM_X_CM + h,
        COLD_FINGER_STEM_Y_CM - h,
        COLD_FINGER_STEM_Y_CM + h,
        COLD_FINGER_STEM_Z0_CM,
        COLD_FINGER_STEM_Z1_CM,
    )
    pad_half = 0.5 * (MXC_PAD_Z1_CM - MXC_PAD_Z0_CM)
    pad_center = 0.5 * (MXC_PAD_Z0_CM + MXC_PAD_Z1_CM)
    pad = "\n".join(
        (
            "Volume SH3_Assembly_Cu_MXC_ContactPad",
            "SH3_Assembly_Cu_MXC_ContactPad.Material Copper",
            "SH3_Assembly_Cu_MXC_ContactPad.Visibility 1",
            f"SH3_Assembly_Cu_MXC_ContactPad.Shape PCON 0 360 2 {-pad_half:.6f} 0 {MXC_PAD_RADIUS_CM:.6f} {pad_half:.6f} 0 {MXC_PAD_RADIUS_CM:.6f}",
            f"SH3_Assembly_Cu_MXC_ContactPad.Position {COLD_FINGER_STEM_X_CM:.6f} {COLD_FINGER_STEM_Y_CM:.6f} {pad_center:.6f}",
            "SH3_Assembly_Cu_MXC_ContactPad.Mother InstrumentFrame",
            "// Pad upper face z'=-0.20 cm is coplanar with the MXC plate underside.",
            "",
        )
    )
    return (
        "// BEGIN SH3_ASSEMBLY_COLD_FINGER_TO_MXC\n"
        "// 3.2 mm square copper proxy, matching the standalone radius-1.6 mm stub envelope.\n"
        + port_run
        + dogleg
        + internal
        + stem
        + pad
        + "// END SH3_ASSEMBLY_COLD_FINGER_TO_MXC\n"
    )


def geometry_text(dr_geometry: str, flattened_chimney: str) -> str:
    dr_geometry = dr_geometry.replace(
        "Include Materials_SH3_DR_Base.geo", "Include Materials_SH3_Assembly.geo", 1
    )
    header = """\n// BEGIN SH3_CHIMNEY_ASSEMBLY
// Chimney local +x' is aligned to the DR port +x' axis.
// Rigid local translation only; the retained InstrumentFrame.Rotation 0 45 0
// applies to the entire assembled system.
// Geometry status only: no transport, activation, timing, or sensitivity authority.
"""
    return (
        dr_geometry.rstrip()
        + header
        + "// BEGIN FLATTENED_PINNED_SH3_CHIMNEY_COMPONENT\n"
        + flattened_chimney.rstrip()
        + "\n// END FLATTENED_PINNED_SH3_CHIMNEY_COMPONENT\n\n"
        + cold_finger_text()
        + "// END SH3_CHIMNEY_ASSEMBLY\n"
    )


def setup_text() -> str:
    return """Name SH3_Chimney_DR_Assembly
Version 1
Include SH3_Assembly.geo
Include SH3_Assembly.det
SurroundingSphere 90 0 0 8 90
"""


def cold_finger_mass_proxy() -> dict[str, float]:
    h = COLD_FINGER_HALF_WIDTH_CM
    square_area = (2 * h) ** 2
    volumes = {
        "port_run_cm3": (COLD_FINGER_PORT_RUN_X1_CM - COLD_FINGER_PORT_RUN_X0_CM) * square_area,
        "dogleg_cm3": (COLD_FINGER_DOGLEG_X1_CM - COLD_FINGER_DOGLEG_X0_CM)
        * (COLD_FINGER_DOGLEG_Y1_CM - COLD_FINGER_DOGLEG_Y0_CM)
        * (2 * h),
        "internal_run_cm3": (COLD_FINGER_INTERNAL_X1_CM - COLD_FINGER_INTERNAL_X0_CM)
        * square_area,
        "mxc_stem_cm3": (COLD_FINGER_STEM_Z1_CM - COLD_FINGER_STEM_Z0_CM) * square_area,
        "mxc_contact_pad_cm3": math.pi
        * MXC_PAD_RADIUS_CM**2
        * (MXC_PAD_Z1_CM - MXC_PAD_Z0_CM),
    }
    total = sum(volumes.values())
    return volumes | {
        "total_cm3": total,
        "nominal_copper_mass_g_at_8p96": total * 8.96,
    }


def svg_text() -> str:
    width, height = 1900, 1120
    x_min, x_max = -44.0, 24.0
    z_min, z_max = -18.0, 48.0
    left, right, top, bottom = 115.0, 1510.0, 120.0, 1030.0

    def sx(x: float) -> float:
        return left + (x - x_min) / (x_max - x_min) * (right - left)

    def sz(z: float) -> float:
        return bottom - (z - z_min) / (z_max - z_min) * (bottom - top)

    def rect(x0: float, x1: float, z0: float, z1: float, fill: str, opacity: float = 0.85, stroke: str = "none") -> str:
        return (
            f'<rect x="{sx(x0):.2f}" y="{sz(z1):.2f}" width="{sx(x1)-sx(x0):.2f}" '
            f'height="{sz(z0)-sz(z1):.2f}" fill="{fill}" opacity="{opacity}" stroke="{stroke}"/>'
        )

    shell_rows = (
        (15.1, 15.3, -9.7, -0.3, "#2457d6"),
        (15.5, 15.8, -10.4, 10.7, "#367ee8"),
        (17.7, 18.0, -11.4, 19.7, "#49a6e9"),
        (18.2, 18.5, -12.4, 28.65, "#79c8e8"),
        (20.1, 20.6, -13.6, 37.5, "#9aa5b1"),
    )
    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="950" y="42" text-anchor="middle" font-family="DejaVu Sans" font-size="29" font-weight="700">SH3 chimney + pure DR assembly — local x′/z′ section</text>',
        '<text x="950" y="76" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">whole InstrumentFrame retains Rotation 0 45 0; signal enters from local −x′</text>',
    ]
    gap0, gap1 = PORT_CENTER_Z_CM - PORT_RADIUS_CM, PORT_CENTER_Z_CM + PORT_RADIUS_CM
    for ri, ro, z0, z1, color in reversed(shell_rows):
        items.append(rect(ri, ro, z0, z1, color))
        items.append(rect(-ro, -ri, z0, gap0, color))
        items.append(rect(-ro, -ri, gap1, z1, color))
    for z, radius, color in (
        (0.0, 15.0, "#b87333"),
        (5.0, 15.0, "#b87333"),
        (10.5, 15.0, "#b87333"),
        (19.5, 17.5, "#b87333"),
        (28.5, 18.0, "#c58a50"),
    ):
        items.append(rect(-radius, radius, z - 0.2, z + 0.2, color, 0.75))

    ox, oz = CHIMNEY_ORIGIN_X_CM, CHIMNEY_ORIGIN_Z_CM
    for sign in (1, -1):
        z0, z1 = sorted((oz + sign * 6.7, oz + sign * 10.7))
        items.append(rect(ox - 6.15, ox + 6.85, z0, z1, "#156c3c", 0.83))
        z0, z1 = sorted((oz + sign * 2.7, oz + sign * 10.7))
        items.append(rect(ox - 10.15, ox - 6.15, z0, z1, "#1f9d55", 0.83))
        z0, z1 = sorted((oz + sign * 0.75, oz + sign * 10.7))
        items.append(rect(ox + 6.85, ox + 10.85, z0, z1, "#2bb673", 0.83))
        z0, z1 = sorted((oz + sign * 10.75, oz + sign * 11.05))
        items.append(rect(ox - 10.2, ox + 10.9, z0, z1, "#697780", 0.95))
    for x in (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0):
        items.append(rect(ox + x - 0.15, ox + x + 0.15, oz - 1.8, oz + 1.8, "#c62828", 0.72))

    h = COLD_FINGER_HALF_WIDTH_CM
    items.append(rect(COLD_FINGER_PORT_RUN_X0_CM, COLD_FINGER_PORT_RUN_X1_CM, PORT_CENTER_Z_CM - h, PORT_CENTER_Z_CM + h, "#7b3f00", 1.0))
    items.append(rect(COLD_FINGER_INTERNAL_X0_CM, COLD_FINGER_INTERNAL_X1_CM, PORT_CENTER_Z_CM - h, PORT_CENTER_Z_CM + h, "#7b3f00", 1.0))
    items.append(rect(COLD_FINGER_STEM_X_CM - h, COLD_FINGER_STEM_X_CM + h, COLD_FINGER_STEM_Z0_CM, COLD_FINGER_STEM_Z1_CM, "#7b3f00", 1.0))
    items.append(rect(COLD_FINGER_STEM_X_CM - MXC_PAD_RADIUS_CM, COLD_FINGER_STEM_X_CM + MXC_PAD_RADIUS_CM, MXC_PAD_Z0_CM, MXC_PAD_Z1_CM, "#a95f20", 1.0))
    items.extend(
        (
            f'<line x1="{sx(x_min):.2f}" y1="{sz(0):.2f}" x2="{sx(x_max):.2f}" y2="{sz(0):.2f}" stroke="#333" stroke-width="1.5"/>',
            f'<line x1="{sx(0):.2f}" y1="{sz(z_min):.2f}" x2="{sx(0):.2f}" y2="{sz(z_max):.2f}" stroke="#777" stroke-width="1" stroke-dasharray="5 5"/>',
            f'<text x="{sx(-42.5):.2f}" y="{sz(7.0):.2f}" font-family="DejaVu Sans" font-size="17">optical front</text>',
            f'<text x="{sx(-33.0):.2f}" y="{sz(7.0):.2f}" font-family="DejaVu Sans" font-size="17" fill="#0d4f2c">40 mm BGO chimney</text>',
            f'<text x="{sx(-24.5):.2f}" y="{sz(-3.8):.2f}" font-family="DejaVu Sans" font-size="16" fill="#7b3f00">cold finger through Ø1.50 cm port stack</text>',
            f'<text x="{sx(5.4):.2f}" y="{sz(1.3):.2f}" font-family="DejaVu Sans" font-size="16" fill="#7b3f00">MXC contact pad</text>',
            f'<text x="{sx(-20.5):.2f}" y="{sz(39.0):.2f}" font-family="DejaVu Sans" font-size="17">retained pure-DR shells/plates</text>',
            '<text x="815" y="1090" text-anchor="middle" font-family="DejaVu Sans" font-size="18">DR local x′ (cm)</text>',
            '<text x="38" y="565" text-anchor="middle" font-family="DejaVu Sans" font-size="18" transform="rotate(-90 38 565)">DR local z′ (cm)</text>',
            '<rect x="1550" y="150" width="305" height="345" fill="#f7f9fb" stroke="#99a"/>',
            '<text x="1702" y="185" text-anchor="middle" font-family="DejaVu Sans" font-size="18" font-weight="700">assembly contract</text>',
            f'<text x="1570" y="225" font-family="DejaVu Sans" font-size="15">chimney origin: ({CHIMNEY_ORIGIN_X_CM:.2f}, 0, -5.20) cm</text>',
            '<text x="1570" y="258" font-family="DejaVu Sans" font-size="15">axis: chimney +x′ = DR +x′</text>',
            '<text x="1570" y="291" font-family="DejaVu Sans" font-size="15">dock clearance: 0.05 cm</text>',
            '<text x="1570" y="324" font-family="DejaVu Sans" font-size="15">port: Ø1.50 cm</text>',
            '<text x="1570" y="357" font-family="DejaVu Sans" font-size="15">cold finger: 3.2 mm square proxy</text>',
            '<text x="1570" y="390" font-family="DejaVu Sans" font-size="15">pad top / MXC bottom: z′=-0.20</text>',
            '<text x="1570" y="435" font-family="DejaVu Sans" font-size="15" fill="#b71c1c">geometry only; thermal sizing pending</text>',
            '</svg>',
            '',
        )
    )
    return "\n".join(items)


def validate(geometry: str, detector: str, flattened_names: list[str], dr_geometry: str) -> dict[str, object]:
    declared = re.findall(r"^Volume\s+(\S+)\s*$", geometry, re.MULTILINE)
    copies = re.findall(r"^\S+\.Copy\s+(\S+)\s*$", geometry, re.MULTILINE)
    mothers = re.findall(r"^\S+\.Mother\s+(\S+)\s*$", geometry, re.MULTILINE)
    names = set(declared) | set(copies) | {"0"}

    hole_points = [
        (float(x), float(y))
        for x, y in re.findall(
            r"^SE3_HOLE_MXC_50mK_\d+\.Position\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+0\s*$",
            dr_geometry,
            re.MULTILINE,
        )
    ]
    nearest_hole = min(
        math.hypot(x - COLD_FINGER_STEM_X_CM, y - COLD_FINGER_STEM_Y_CM)
        for x, y in hole_points
    )
    pad_to_hole_clearance = nearest_hole - MXC_HOLE_RADIUS_CM - MXC_PAD_RADIUS_CM
    port_corner_radius = math.sqrt(2.0) * COLD_FINGER_HALF_WIDTH_CM

    checks = {
        "one_world_volume": declared.count("WorldVolume") == 1,
        "one_retained_instrument_frame": declared.count("InstrumentFrame") == 1,
        "retained_instrument_frame_rotation_0_45_0": "InstrumentFrame.Rotation 0 45 0" in geometry,
        "no_chimney_container_or_mother_remains": not re.search(
            r"^(?:Volume SH3_ChimneyFrame|\S+\.Mother SH3_ChimneyFrame)\s*$",
            geometry,
            re.MULTILINE,
        ),
        "all_flattened_chimney_top_levels_present": all(name in declared for name in flattened_names),
        "all_volume_and_copy_names_unique": len(declared) == len(set(declared)) and len(copies) == len(set(copies)),
        "all_mothers_resolve": all(mother in names for mother in mothers),
        "six_tes_layers": len(re.findall(r"^Volume TES_L\d$", geometry, re.MULTILINE)) == 6,
        "2256_tes_pixel_copies": len(re.findall(r"^TES_Pixel_L\d+\.Copy\s+TP_L", geometry, re.MULTILINE)) == 2256,
        "three_active_bgo_volumes": len(re.findall(r"^Volume SH3_BGO40_", geometry, re.MULTILINE)) == 3,
        "five_new_cold_finger_parts": len(re.findall(r"^Volume SH3_Assembly_Cu_", geometry, re.MULTILINE)) == 5,
        "cold_finger_fits_round_port": port_corner_radius < PORT_RADIUS_CM,
        "contact_pad_touches_mxc_plate_underside": math.isclose(MXC_PAD_Z1_CM, MXC_PLATE_BOTTOM_Z_CM),
        "contact_pad_clear_of_mxc_vacuum_holes": pad_to_hole_clearance > 0,
        "chimney_and_port_center_z_match": math.isclose(CHIMNEY_ORIGIN_Z_CM, PORT_CENTER_Z_CM),
        "chimney_mechanical_shell_clears_dr_outer_tangent": math.isclose(
            CHIMNEY_ORIGIN_X_CM + CHIMNEY_MECHANICAL_REAR_LOCAL_X_CM,
            DR_OUTER_NEGATIVE_X_CM - DOCK_CLEARANCE_CM,
        ),
        "cold_finger_starts_at_chimney_stub_end": math.isclose(
            COLD_FINGER_PORT_RUN_X0_CM,
            CHIMNEY_ORIGIN_X_CM + CHIMNEY_STUB_LOCAL_X1_CM,
        ),
        "detector_retains_six_tes_and_three_bgo": len(re.findall(r"^MDCalorimeter D\d$", detector, re.MULTILINE)) == 6
        and len(re.findall(r"^Scintillator SH3_BGO40_", detector, re.MULTILINE)) == 3,
    }
    status = "PASS__SH3_ASSEMBLY_STATIC" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "physics_status": "FULL ASSEMBLY GEOMETRY ONLY — UNTRANSPORTED/UNTHERMALLY-SIZED",
        "checks": checks,
        "counts": {
            "declared_volumes": len(declared),
            "copy_placements": len(copies),
            "flattened_chimney_top_level_volumes": len(flattened_names),
            "mxc_hole_placements": len(hole_points),
        },
        "clearances": {
            "dock_clearance_cm": DOCK_CLEARANCE_CM,
            "cold_finger_square_corner_radius_cm": port_corner_radius,
            "cold_finger_to_port_corner_clearance_cm": PORT_RADIUS_CM - port_corner_radius,
            "nearest_mxc_hole_center_distance_cm": nearest_hole,
            "mxc_pad_edge_to_nearest_hole_edge_clearance_cm": pad_to_hole_clearance,
        },
    }


def main() -> int:
    inputs = verify_inputs()
    component = CHIMNEY_COMPONENT.read_text(encoding="utf-8")
    flattened, flattened_names = flatten_chimney(component)
    dr_geometry = DR_GEO.read_text(encoding="utf-8")
    detector = CHIMNEY_DET.read_text(encoding="utf-8")
    geometry = geometry_text(dr_geometry, flattened)
    outputs = {
        OUTPUT_GEO: geometry,
        OUTPUT_SETUP: setup_text(),
        OUTPUT_DET: detector,
        OUTPUT_MATERIALS: CHIMNEY_MATERIALS.read_text(encoding="utf-8"),
        OUTPUT_FIGURE: svg_text(),
    }
    for path, text in outputs.items():
        atomic_text(path, text)

    validation = validate(geometry, detector, flattened_names, dr_geometry)
    atomic_json(OUTPUT_STATIC, validation)
    if validation["status"] != "PASS__SH3_ASSEMBLY_STATIC":
        raise BuildError("SH3 assembly static validation failed")

    manifest = {
        "status": "PASS__SH3_ASSEMBLY_BUILT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_Chimney_DR_Assembly",
        "physics_status": "ASSEMBLED GEOMETRY ONLY — NO TRANSPORT/ACTIVATION/RESPONSE/TIMING CLAIM",
        "pinned_inputs": inputs,
        "coordinate_contract": {
            "parent_frame": "InstrumentFrame",
            "parent_rotation_deg": [0.0, 45.0, 0.0],
            "chimney_axis": "local +x' aligned with DR port +x'",
            "chimney_origin_local_cm": [CHIMNEY_ORIGIN_X_CM, 0.0, CHIMNEY_ORIGIN_Z_CM],
            "port_center_local_cm": [None, 0.0, PORT_CENTER_Z_CM],
            "dock_clearance_cm": DOCK_CLEARANCE_CM,
        },
        "cold_finger": {
            "material": "Copper",
            "square_width_cm": 2 * COLD_FINGER_HALF_WIDTH_CM,
            "port_run_x_extent_cm": [COLD_FINGER_PORT_RUN_X0_CM, COLD_FINGER_PORT_RUN_X1_CM],
            "inside_mxc_dogleg": {
                "x_extent_cm": [COLD_FINGER_DOGLEG_X0_CM, COLD_FINGER_DOGLEG_X1_CM],
                "y_extent_cm": [COLD_FINGER_DOGLEG_Y0_CM, COLD_FINGER_DOGLEG_Y1_CM],
            },
            "internal_run_x_extent_cm": [COLD_FINGER_INTERNAL_X0_CM, COLD_FINGER_INTERNAL_X1_CM],
            "mxc_stem_center_xy_cm": [COLD_FINGER_STEM_X_CM, COLD_FINGER_STEM_Y_CM],
            "mxc_stem_z_extent_cm": [COLD_FINGER_STEM_Z0_CM, COLD_FINGER_STEM_Z1_CM],
            "mxc_contact_pad_radius_cm": MXC_PAD_RADIUS_CM,
            "mxc_contact_pad_z_extent_cm": [MXC_PAD_Z0_CM, MXC_PAD_Z1_CM],
            "mxc_plate_underside_z_cm": MXC_PLATE_BOTTOM_Z_CM,
            "contact_definition": "pad upper face is coplanar with retained MXC copper plate underside",
            "mass_proxy": cold_finger_mass_proxy(),
        },
        "included": [
            "complete pinned pure-DR base with retained 45 degree InstrumentFrame tilt",
            "flattened pinned SH3 chimney component with six TES layers and 40 mm active BGO",
            "new copper cold-finger port run, internal dogleg, MXC stem, and contact pad",
        ],
        "not_claimed": [
            "thermal conductance, heat load, vibration, launch load, or manufacturability closure",
            "transport, activation, delayed background, detector response, Poisson timing, or sensitivity",
            "BGO optical coupling/readout and flight brackets",
        ],
        "outputs": {path.name: file_record(path) for path in outputs},
        "static_validation": file_record(OUTPUT_STATIC),
    }
    atomic_json(OUTPUT_MANIFEST, manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "static": validation["status"],
                "manifest": str(OUTPUT_MANIFEST),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
