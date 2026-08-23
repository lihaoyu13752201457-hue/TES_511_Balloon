#!/usr/bin/env python3
"""Build the standalone, mergeable SH3 TES chimney geometry component.

This is a geometry-only build.  It reuses the exact six-layer TES pixel,
silicon substrate, and copper support blocks from the pinned SG3B geometry,
then places them inside a new compact five-layer coaxial chimney extension.
The local shell layers intentionally have no assigned DR temperature stage:
they are not MXC, Still, 4 K, or 60 K plates/vessels.  This revision adds a
40 mm active-BGO side/front/rear shield with an open optical aperture and open
cold-finger port, plus a 3 mm external mechanical aluminium side/front shell.
No passive Bi, plastic veto, source, transport, activation, or detector-response
product is generated here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"
FIGURES = PACKAGE / "figures"

REFERENCE_PACKAGE = Path(
    "/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816"
)
REFERENCE_GEO = REFERENCE_PACKAGE / "geometry/DEMO2_DR_v3p5_SG3B.geo"
REFERENCE_DET = REFERENCE_PACKAGE / "geometry/DEMO2_DR_v3p5_SG3B.det"
REFERENCE_MATERIALS = REFERENCE_PACKAGE / "geometry/Materials_DEMO2_DR_v3p5.geo"
PINNED = {
    "geo": "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9",
    "det": "0a4e6cb6b17949d5593f46faae87d80b383f5c9c08cb5b3240b91131e8515e21",
    "materials": "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
}

COMPONENT = GEOMETRY / "SH3_Chimney_Component.geo"
STANDALONE = GEOMETRY / "SH3_Chimney_Standalone.geo"
SETUP = GEOMETRY / "SH3_Chimney_Standalone.geo.setup"
DET = GEOMETRY / "SH3_Chimney.det"
MATERIALS = GEOMETRY / "Materials_SH3.geo"
MANIFEST = DATA / "component_manifest.json"
STATIC = AUDIT / "static_validation.json"
FIGURE = FIGURES / "sh3_chimney_xr_cross_section.svg"


@dataclass(frozen=True)
class ShellLayer:
    key: str
    label: str
    material: str
    front_x_cm: float
    rear_x_cm: float
    inner_radius_cm: float
    wall_thickness_cm: float
    cap_thickness_cm: float
    window_material: str
    window_half_thickness_cm: float
    color: str

    @property
    def outer_radius_cm(self) -> float:
        return self.inner_radius_cm + self.wall_thickness_cm


SHELL_LAYERS = (
    ShellLayer("Layer01", "local inner aluminium liner", "Aluminium", -3.95, 4.15, 4.00, 0.20, 0.20, "Aluminium", 0.00125, "#2457d6"),
    ShellLayer("Layer02", "local aluminium shell layer 02", "Aluminium", -4.40, 4.60, 4.45, 0.30, 0.30, "Aluminium", 0.00125, "#367ee8"),
    ShellLayer("Layer03", "local aluminium shell layer 03", "Aluminium", -4.95, 5.15, 5.00, 0.30, 0.30, "Aluminium", 0.00125, "#49a6e9"),
    ShellLayer("Layer04", "local aluminium shell layer 04", "Aluminium", -5.50, 5.70, 5.55, 0.30, 0.30, "Aluminium", 0.00125, "#79c8e8"),
    ShellLayer("Layer05", "local outer mechanical jacket", "Aluminium", -6.05, 6.25, 6.10, 0.50, 0.50, "Be", 0.00750, "#9aa5b1"),
)

OPTICAL_APERTURE_RADIUS_CM = 2.70
COLD_PORT_RADIUS_CM = 0.75
WINDOW_RADIUS_CM = OPTICAL_APERTURE_RADIUS_CM
OUTER_FILTER_X_CM = -6.60
OUTER_FILTER_HALF_THICKNESS_CM = 0.00150
ASSEMBLY_CLEARANCE_CM = 0.10
BGO_THICKNESS_CM = 4.00
BGO_INNER_RADIUS_CM = SHELL_LAYERS[-1].outer_radius_cm + ASSEMBLY_CLEARANCE_CM
BGO_OUTER_RADIUS_CM = BGO_INNER_RADIUS_CM + BGO_THICKNESS_CM
BGO_FRONT_X1_CM = SHELL_LAYERS[-1].front_x_cm - ASSEMBLY_CLEARANCE_CM
BGO_FRONT_X0_CM = BGO_FRONT_X1_CM - BGO_THICKNESS_CM
BGO_SIDE_X0_CM = BGO_FRONT_X1_CM
BGO_SIDE_X1_CM = (
    SHELL_LAYERS[-1].rear_x_cm
    + SHELL_LAYERS[-1].cap_thickness_cm
    + ASSEMBLY_CLEARANCE_CM
)
BGO_REAR_X0_CM = BGO_SIDE_X1_CM
BGO_REAR_X1_CM = BGO_REAR_X0_CM + BGO_THICKNESS_CM
MECHANICAL_AL_CLEARANCE_CM = 0.05
MECHANICAL_AL_THICKNESS_CM = 0.30
MECHANICAL_AL_INNER_RADIUS_CM = BGO_OUTER_RADIUS_CM + MECHANICAL_AL_CLEARANCE_CM
MECHANICAL_AL_OUTER_RADIUS_CM = (
    MECHANICAL_AL_INNER_RADIUS_CM + MECHANICAL_AL_THICKNESS_CM
)
MECHANICAL_AL_SIDE_X0_CM = BGO_FRONT_X0_CM - MECHANICAL_AL_CLEARANCE_CM
MECHANICAL_AL_SIDE_X1_CM = BGO_REAR_X1_CM + MECHANICAL_AL_CLEARANCE_CM
MECHANICAL_AL_FRONT_X1_CM = MECHANICAL_AL_SIDE_X0_CM
MECHANICAL_AL_FRONT_X0_CM = MECHANICAL_AL_FRONT_X1_CM - MECHANICAL_AL_THICKNESS_CM
CHIMNEY_FRAME_HALF_CM = 12.0
TES_LAYER_X_CM = (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0)
TES_PIXELS_PER_LAYER = 376
TES_BOTTOM_PLATE_X_CM = 3.42
TES_BOTTOM_PLATE_OUTER_HALF_CM = 2.8
TES_BOTTOM_PLATE_INNER_HALF_CM = 0.8
TES_BOTTOM_PLATE_HALF_THICKNESS_CM = 0.175
COLD_STUB_RADIUS_CM = 0.16
COLD_STUB_X0_CM = 3.595
COLD_STUB_X1_CM = 6.80
REFERENCE_INSTRUMENT_TES_CENTER_Z_CM = -5.2


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


def verify_reference() -> dict[str, dict[str, object]]:
    paths = {"geo": REFERENCE_GEO, "det": REFERENCE_DET, "materials": REFERENCE_MATERIALS}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise BuildError(f"missing pinned SG3B reference file(s): {missing}")
    records: dict[str, dict[str, object]] = {}
    for key, path in paths.items():
        current = sha256_path(path)
        if current != PINNED[key]:
            raise BuildError(f"pinned SG3B {key} drift: {current} != {PINNED[key]}")
        records[key] = file_record(path)
    return records


def extract_between(text: str, start: str, stop: str) -> str:
    if text.count(start) != 1 or text.count(stop) != 1:
        raise BuildError(f"reference extraction markers are not unique: {start!r}, {stop!r}")
    return text[text.index(start) : text.index(stop)].rstrip() + "\n"


def reparent_and_recenter_instrument_volumes(block: str) -> str:
    """Move SG3B top-level TES/support volumes into the SH3 local frame.

    Pixel copies and other daughters retain their exact coordinates relative to
    their existing mothers.  Only volumes directly parented by the reference
    InstrumentFrame receive the +5.2 cm z translation.
    """
    names = re.findall(r"^(\S+)\.Mother InstrumentFrame\s*$", block, re.MULTILINE)
    for name in names:
        position_pattern = re.compile(
            rf"^{re.escape(name)}\.Position\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            re.MULTILINE,
        )
        match = position_pattern.search(block)
        if match is None:
            raise BuildError(f"top-level SG3B volume has no position: {name}")
        x, y, z = (float(value) for value in match.groups())
        local_z = z - REFERENCE_INSTRUMENT_TES_CENTER_Z_CM
        replacement = f"{name}.Position {x:.12g} {y:.12g} {local_z:.12g}"
        block, count = position_pattern.subn(replacement, block, count=1)
        if count != 1:
            raise BuildError(f"failed to recenter top-level SG3B volume: {name}")
        block = block.replace(
            f"{name}.Mother InstrumentFrame", f"{name}.Mother SH3_ChimneyFrame", 1
        )
    if "Mother InstrumentFrame" in block:
        raise BuildError("unconverted InstrumentFrame mother remains in inherited block")
    return block


def inherited_blocks() -> tuple[str, str, str]:
    geo = REFERENCE_GEO.read_text(encoding="utf-8")
    det = REFERENCE_DET.read_text(encoding="utf-8")
    tes = extract_between(
        geo,
        "// Volume TES_Pixel_L0; material=Ta",
        "// Volume Si_Substrate_Stack_side_entry_L0; material=Silicon",
    )
    supports = extract_between(
        geo,
        "// Volume Si_Substrate_Stack_side_entry_L0; material=Silicon",
        "// Volume Cu_ColdFinger_OffAxis_YP_ZP_from_Disk_to_Stem; material=Copper",
    )
    detector = extract_between(
        det,
        "// DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy detector map",
        "Scintillator Si_Substrate_Stack_side_entry_L0_SD",
    )
    tes = reparent_and_recenter_instrument_volumes(tes)
    supports = reparent_and_recenter_instrument_volumes(supports)
    return tes, supports, detector


def tube_volume(
    name: str,
    material: str,
    x0: float,
    x1: float,
    r0: float,
    r1: float,
    visibility: int = 1,
) -> str:
    half_height = 0.5 * (x1 - x0)
    center_x = 0.5 * (x0 + x1)
    return "\n".join(
        (
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility {visibility}",
            f"{name}.Shape TUBS {r0:.6f} {r1:.6f} {half_height:.6f} 0 360",
            f"{name}.Position {center_x:.6f} 0 0",
            f"{name}.Rotation 0 90 0",
            f"{name}.Mother SH3_ChimneyFrame",
            "",
        )
    )


def shell_block(layer: ShellLayer) -> str:
    prefix = f"SH3_{layer.key}"
    side_x0 = layer.front_x_cm + layer.cap_thickness_cm
    side = tube_volume(
        f"{prefix}_SideShell",
        layer.material,
        side_x0,
        layer.rear_x_cm,
        layer.inner_radius_cm,
        layer.outer_radius_cm,
    )
    front = tube_volume(
        f"{prefix}_FrontAnnulus",
        layer.material,
        layer.front_x_cm,
        side_x0,
        OPTICAL_APERTURE_RADIUS_CM,
        layer.outer_radius_cm,
    )
    rear = tube_volume(
        f"{prefix}_RearColdPortAnnulus",
        layer.material,
        layer.rear_x_cm,
        layer.rear_x_cm + layer.cap_thickness_cm,
        COLD_PORT_RADIUS_CM,
        layer.outer_radius_cm,
    )
    window_mid = layer.front_x_cm + 0.5 * layer.cap_thickness_cm
    window = tube_volume(
        f"{prefix}_OpticalWindow",
        layer.window_material,
        window_mid - layer.window_half_thickness_cm,
        window_mid + layer.window_half_thickness_cm,
        0.0,
        WINDOW_RADIUS_CM,
    )
    return f"// {layer.label}; thermal-stage ownership deliberately unset\n{side}{front}{rear}{window}"


def bgo_and_mechanical_shell_block() -> str:
    """Build active BGO around every non-window/non-cold-port surface.

    The rear BGO is annular, so the cold-finger path stays open.  The external
    aluminium has a side wall and an optical-front annulus only: no aluminium
    rear end cap is created on the cold-finger face.
    """
    return "".join(
        (
            "// BEGIN SH3_ACTIVE_BGO40_AND_MECHANICAL_AL3\n",
            "// 40 mm is the retained SG3 side-shield baseline; no >40 mm benefit is asserted.\n",
            tube_volume(
                "SH3_BGO40_SideShield",
                "BGO",
                BGO_SIDE_X0_CM,
                BGO_SIDE_X1_CM,
                BGO_INNER_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
            tube_volume(
                "SH3_BGO40_FrontOpticalAnnulus",
                "BGO",
                BGO_FRONT_X0_CM,
                BGO_FRONT_X1_CM,
                OPTICAL_APERTURE_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
            tube_volume(
                "SH3_BGO40_RearColdPortAnnulus",
                "BGO",
                BGO_REAR_X0_CM,
                BGO_REAR_X1_CM,
                COLD_PORT_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
            tube_volume(
                "SH3_BGO_MechanicalAl_SideShell_3mm",
                "Aluminium",
                MECHANICAL_AL_SIDE_X0_CM,
                MECHANICAL_AL_SIDE_X1_CM,
                MECHANICAL_AL_INNER_RADIUS_CM,
                MECHANICAL_AL_OUTER_RADIUS_CM,
            ),
            tube_volume(
                "SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm",
                "Aluminium",
                MECHANICAL_AL_FRONT_X0_CM,
                MECHANICAL_AL_FRONT_X1_CM,
                OPTICAL_APERTURE_RADIUS_CM,
                MECHANICAL_AL_OUTER_RADIUS_CM,
            ),
            "// Deliberately no mechanical-Al rear end cap on the cold-finger face.\n",
            "// END SH3_ACTIVE_BGO40_AND_MECHANICAL_AL3\n",
        )
    )


def bgo_detector_block() -> str:
    lines = [
        "",
        "// BEGIN SH3_ACTIVE_BGO40_DET",
        "// Native SG3B BGO scorer convention retained; timing/veto policy remains downstream.",
    ]
    for volume in (
        "SH3_BGO40_SideShield",
        "SH3_BGO40_FrontOpticalAnnulus",
        "SH3_BGO40_RearColdPortAnnulus",
    ):
        scorer = f"{volume}_SD"
        lines.extend(
            (
                f"Scintillator {scorer}",
                f"{scorer}.SensitiveVolume {volume}",
                f"{scorer}.DetectorVolume {volume}",
                f"{scorer}.TriggerThreshold 80",
                f"{scorer}.NoiseThresholdEqualsTriggerThreshold true",
                f"{scorer}.EnergyResolution Gauss 80 80 1",
                f"{scorer}.EnergyResolution Gauss 3000 3000 1",
                "",
            )
        )
    lines.extend(("// END SH3_ACTIVE_BGO40_DET", ""))
    return "\n".join(lines)


def local_cold_plate_additions() -> str:
    x0 = TES_BOTTOM_PLATE_X_CM - TES_BOTTOM_PLATE_HALF_THICKNESS_CM
    x1 = TES_BOTTOM_PLATE_X_CM + TES_BOTTOM_PLATE_HALF_THICKNESS_CM
    lines = [
        "// SH3 local TES cold plate completion; this is not the MXC plate.",
        tube_volume(
            "SH3_TES_BottomColdPlate_CentralHub",
            "Copper",
            x0,
            x1,
            0.0,
            COLD_STUB_RADIUS_CM,
        ).rstrip(),
    ]
    arm_specs = (
        ("YP", 0.48, 0.0, 0.32, 0.08),
        ("YM", -0.48, 0.0, 0.32, 0.08),
        ("ZP", 0.0, 0.48, 0.08, 0.32),
        ("ZM", 0.0, -0.48, 0.08, 0.32),
    )
    for suffix, y, z, hy, hz in arm_specs:
        name = f"SH3_TES_BottomColdPlate_Spoke_{suffix}"
        lines.extend(
            (
                "",
                f"Volume {name}",
                f"{name}.Material Copper",
                f"{name}.Visibility 1",
                f"{name}.Shape BRIK {TES_BOTTOM_PLATE_HALF_THICKNESS_CM:.6f} {hy:.6f} {hz:.6f}",
                f"{name}.Position {TES_BOTTOM_PLATE_X_CM:.6f} {y:.6f} {z:.6f}",
                f"{name}.Mother SH3_ChimneyFrame",
            )
        )
    lines.extend(
        (
            "",
            tube_volume(
                "SH3_TES_ColdFinger_InterfaceStub",
                "Copper",
                COLD_STUB_X0_CM,
                COLD_STUB_X1_CM,
                0.0,
                COLD_STUB_RADIUS_CM,
            ).rstrip(),
            "// The stub terminates at the SH3 merge plane; the main-DR cold finger is not included.",
            "",
        )
    )
    return "\n".join(lines)


def component_text(tes: str, supports: str) -> str:
    header = """// SH3 standalone/mergeable TES chimney component
// Local frame contract: x'=optical axis, signal travels from negative x' to positive x'.
// This file deliberately does not define SH3_ChimneyFrame or any World volume.
// A wrapper must define SH3_ChimneyFrame and then include this file.
// Pinned SG3B top-level TES/support placements are recentered from z=-5.2 cm to local z=0.
// The five local shell layers are not DR cold plates/vessels and have no thermal-stage assignment.
// Active BGO: 40 mm side plus 40 mm optical-front and cold-port-rear annuli.
// Mechanical Al: 3 mm side/front only; the cold-finger rear face has no Al end cap.
// Physics status: geometry and scorer definitions only; no Bi/plastic/transport/timing authority.

"""
    shell_layers = "\n".join(shell_block(layer) for layer in SHELL_LAYERS)
    outer_filter = tube_volume(
        "SH3_Outer_Al_OpticalFilter",
        "Aluminium",
        OUTER_FILTER_X_CM - OUTER_FILTER_HALF_THICKNESS_CM,
        OUTER_FILTER_X_CM + OUTER_FILTER_HALF_THICKNESS_CM,
        0.0,
        WINDOW_RADIUS_CM,
    )
    return (
        header
        + "// BEGIN PINNED_SG3B_TES_BLOCK\n"
        + tes
        + "// END PINNED_SG3B_TES_BLOCK\n\n"
        + "// BEGIN PINNED_SG3B_SUBSTRATE_AND_COPPER_SUPPORT_BLOCK\n"
        + supports
        + "// END PINNED_SG3B_SUBSTRATE_AND_COPPER_SUPPORT_BLOCK\n\n"
        + local_cold_plate_additions()
        + "\n// BEGIN SH3_NESTED_CHIMNEY_SHELLS\n"
        + shell_layers
        + "\n// Outer IR/optical filter immediately ahead of the structural Be window.\n"
        + outer_filter
        + "// END SH3_NESTED_CHIMNEY_SHELLS\n"
        + "\n"
        + bgo_and_mechanical_shell_block()
    )


def standalone_text() -> str:
    return f"""Name SH3_Chimney_Component_Standalone
Version 1

Include Materials_SH3.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 30 30 30
WorldVolume.Mother 0

// Production merge replaces this placement only; component internals stay local.
Volume SH3_ChimneyFrame
SH3_ChimneyFrame.Visibility 0
SH3_ChimneyFrame.Material Vacuum
SH3_ChimneyFrame.Shape BRIK {CHIMNEY_FRAME_HALF_CM:.6f} {CHIMNEY_FRAME_HALF_CM:.6f} {CHIMNEY_FRAME_HALF_CM:.6f}
SH3_ChimneyFrame.Position 0 0 0
SH3_ChimneyFrame.Mother WorldVolume

Include SH3_Chimney_Component.geo
"""


def setup_text() -> str:
    return """Name SH3_Chimney_Component_Standalone
Version 1
Include SH3_Chimney_Standalone.geo
Include SH3_Chimney.det
SurroundingSphere 20 0 0 0 20
"""


def layer_volume_cm3(layer: ShellLayer) -> float:
    ro = layer.outer_radius_cm
    side_length = layer.rear_x_cm - (layer.front_x_cm + layer.cap_thickness_cm)
    side = math.pi * (ro * ro - layer.inner_radius_cm**2) * side_length
    front = math.pi * (ro * ro - OPTICAL_APERTURE_RADIUS_CM**2) * layer.cap_thickness_cm
    rear = math.pi * (ro * ro - COLD_PORT_RADIUS_CM**2) * layer.cap_thickness_cm
    window = math.pi * WINDOW_RADIUS_CM**2 * (2 * layer.window_half_thickness_cm)
    return side + front + rear + window


def annular_tube_volume_cm3(x0: float, x1: float, r0: float, r1: float) -> float:
    return math.pi * (r1 * r1 - r0 * r0) * (x1 - x0)


def mass_proxy() -> dict[str, object]:
    pixel_volume = (2 * 0.15) * (2 * 0.075) * (2 * 0.075)
    ta_mass = 6 * TES_PIXELS_PER_LAYER * pixel_volume * 16.69
    shell_rows = []
    for layer in SHELL_LAYERS:
        total = layer_volume_cm3(layer)
        shell_rows.append(
            {
                "local_shell_layer": layer.key,
                "combined_shell_caps_window_volume_cm3": total,
                "nominal_mass_g_using_aluminium_density": total * 2.699,
                "note": "Al shell/caps plus a thin window; the mixed window material is not separately mass-closed",
            }
        )
    bgo_rows = [
        {
            "volume": "SH3_BGO40_SideShield",
            "volume_cm3": annular_tube_volume_cm3(
                BGO_SIDE_X0_CM,
                BGO_SIDE_X1_CM,
                BGO_INNER_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
        },
        {
            "volume": "SH3_BGO40_FrontOpticalAnnulus",
            "volume_cm3": annular_tube_volume_cm3(
                BGO_FRONT_X0_CM,
                BGO_FRONT_X1_CM,
                OPTICAL_APERTURE_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
        },
        {
            "volume": "SH3_BGO40_RearColdPortAnnulus",
            "volume_cm3": annular_tube_volume_cm3(
                BGO_REAR_X0_CM,
                BGO_REAR_X1_CM,
                COLD_PORT_RADIUS_CM,
                BGO_OUTER_RADIUS_CM,
            ),
        },
    ]
    for row in bgo_rows:
        row["nominal_mass_g_using_bgo_density_7p13"] = row["volume_cm3"] * 7.13
    aluminium_rows = [
        {
            "volume": "SH3_BGO_MechanicalAl_SideShell_3mm",
            "volume_cm3": annular_tube_volume_cm3(
                MECHANICAL_AL_SIDE_X0_CM,
                MECHANICAL_AL_SIDE_X1_CM,
                MECHANICAL_AL_INNER_RADIUS_CM,
                MECHANICAL_AL_OUTER_RADIUS_CM,
            ),
        },
        {
            "volume": "SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm",
            "volume_cm3": annular_tube_volume_cm3(
                MECHANICAL_AL_FRONT_X0_CM,
                MECHANICAL_AL_FRONT_X1_CM,
                OPTICAL_APERTURE_RADIUS_CM,
                MECHANICAL_AL_OUTER_RADIUS_CM,
            ),
        },
    ]
    for row in aluminium_rows:
        row["nominal_mass_g_using_aluminium_density_2p699"] = (
            row["volume_cm3"] * 2.699
        )
    return {
        "ta_absorbers_mass_g": ta_mass,
        "ta_absorbers_count": 6 * TES_PIXELS_PER_LAYER,
        "shell_layer_proxy_rows": shell_rows,
        "active_bgo_rows": bgo_rows,
        "active_bgo_total_volume_cm3": sum(row["volume_cm3"] for row in bgo_rows),
        "active_bgo_total_nominal_mass_kg": sum(
            row["nominal_mass_g_using_bgo_density_7p13"] for row in bgo_rows
        )
        / 1000.0,
        "mechanical_al_rows": aluminium_rows,
        "mechanical_al_total_nominal_mass_kg": sum(
            row["nominal_mass_g_using_aluminium_density_2p699"]
            for row in aluminium_rows
        )
        / 1000.0,
        "warning": "Engineering mass proxy only; exact copper supports and mixed window materials are not closed here. BGO optical coupling/readout and brackets are not included.",
    }


def svg_text() -> str:
    width, height = 1500, 900
    x_min, x_max = -11.4, 11.2
    r_max = 11.5
    plot_left, plot_right = 150, 1400
    plot_top, plot_bottom = 100, 800

    def sx(x: float) -> float:
        return plot_left + (x - x_min) / (x_max - x_min) * (plot_right - plot_left)

    def sy(r: float) -> float:
        return 0.5 * (plot_top + plot_bottom) - r / r_max * 0.5 * (plot_bottom - plot_top)

    def rect(x0: float, x1: float, r0: float, r1: float, fill: str, opacity: float = 0.9) -> str:
        return (
            f'<rect x="{sx(x0):.2f}" y="{sy(r1):.2f}" width="{sx(x1)-sx(x0):.2f}" '
            f'height="{sy(r0)-sy(r1):.2f}" fill="{fill}" opacity="{opacity}"/>'
        )

    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="750" y="42" text-anchor="middle" font-family="DejaVu Sans" font-size="28" font-weight="700">SH3 TES chimney — x′/radius section</text>',
        '<text x="750" y="72" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">40 mm active BGO; optical window and cold-finger port remain open; no rear Al end cap</text>',
        f'<line x1="{sx(x_min):.2f}" y1="{sy(0):.2f}" x2="{sx(x_max):.2f}" y2="{sy(0):.2f}" stroke="#333" stroke-width="2"/>',
    ]
    for sign in (1, -1):
        a, b = sorted(
            (
                sign * MECHANICAL_AL_INNER_RADIUS_CM,
                sign * MECHANICAL_AL_OUTER_RADIUS_CM,
            )
        )
        items.append(
            rect(
                MECHANICAL_AL_SIDE_X0_CM,
                MECHANICAL_AL_SIDE_X1_CM,
                a,
                b,
                "#697780",
                0.95,
            )
        )
        a, b = sorted(
            (sign * OPTICAL_APERTURE_RADIUS_CM, sign * MECHANICAL_AL_OUTER_RADIUS_CM)
        )
        items.append(
            rect(
                MECHANICAL_AL_FRONT_X0_CM,
                MECHANICAL_AL_FRONT_X1_CM,
                a,
                b,
                "#697780",
                0.95,
            )
        )
    for sign in (1, -1):
        a, b = sorted((sign * BGO_INNER_RADIUS_CM, sign * BGO_OUTER_RADIUS_CM))
        items.append(rect(BGO_SIDE_X0_CM, BGO_SIDE_X1_CM, a, b, "#156c3c", 0.82))
        a, b = sorted((sign * OPTICAL_APERTURE_RADIUS_CM, sign * BGO_OUTER_RADIUS_CM))
        items.append(rect(BGO_FRONT_X0_CM, BGO_FRONT_X1_CM, a, b, "#1f9d55", 0.84))
        a, b = sorted((sign * COLD_PORT_RADIUS_CM, sign * BGO_OUTER_RADIUS_CM))
        items.append(rect(BGO_REAR_X0_CM, BGO_REAR_X1_CM, a, b, "#2bb673", 0.84))
    for layer in reversed(SHELL_LAYERS):
        x0 = layer.front_x_cm + layer.cap_thickness_cm
        for sign in (1, -1):
            a, b = sorted((sign * layer.inner_radius_cm, sign * layer.outer_radius_cm))
            items.append(rect(x0, layer.rear_x_cm, a, b, layer.color, 0.82))
            a2, b2 = sorted((sign * OPTICAL_APERTURE_RADIUS_CM, sign * layer.outer_radius_cm))
            items.append(rect(layer.front_x_cm, x0, a2, b2, layer.color, 0.82))
            a3, b3 = sorted((sign * COLD_PORT_RADIUS_CM, sign * layer.outer_radius_cm))
            items.append(rect(layer.rear_x_cm, layer.rear_x_cm + layer.cap_thickness_cm, a3, b3, layer.color, 0.82))
        win_mid = layer.front_x_cm + 0.5 * layer.cap_thickness_cm
        half = max(layer.window_half_thickness_cm, 0.025)
        items.append(rect(win_mid - half, win_mid + half, -WINDOW_RADIUS_CM, WINDOW_RADIUS_CM, "#f2c94c", 0.85))
    for index, x in enumerate(TES_LAYER_X_CM):
        items.append(rect(x - 0.15, x + 0.15, -1.8, 1.8, "#c62828", 0.72))
        items.append(f'<text x="{sx(x):.2f}" y="{sy(2.05):.2f}" text-anchor="middle" font-family="DejaVu Sans" font-size="15">L{index}</text>')
    items.append(rect(3.245, 3.595, -2.8, 2.8, "#b87333", 0.74))
    items.append(rect(COLD_STUB_X0_CM, COLD_STUB_X1_CM, -COLD_STUB_RADIUS_CM, COLD_STUB_RADIUS_CM, "#8c4b19", 1.0))
    items.extend(
        (
            f'<text x="{sx(-9.7):.2f}" y="{sy(9.4):.2f}" font-family="DejaVu Sans" font-size="17" fill="#0d4f2c">BGO 40 mm front annulus</text>',
            f'<text x="{sx(-3.3):.2f}" y="{sy(9.4):.2f}" font-family="DejaVu Sans" font-size="17" fill="#0d4f2c">BGO 40 mm side shield</text>',
            f'<text x="{sx(7.0):.2f}" y="{sy(9.4):.2f}" font-family="DejaVu Sans" font-size="17" fill="#0d4f2c">BGO rear annulus</text>',
            f'<text x="{sx(-10.8):.2f}" y="{sy(11.0):.2f}" font-family="DejaVu Sans" font-size="16" fill="#404b52">3 mm mechanical Al</text>',
            f'<text x="{sx(-6.7):.2f}" y="{sy(3.25):.2f}" font-family="DejaVu Sans" font-size="18">aligned optical windows</text>',
            f'<text x="{sx(3.05):.2f}" y="{sy(3.25):.2f}" font-family="DejaVu Sans" font-size="18">local TES cold plate</text>',
            f'<text x="{sx(5.2):.2f}" y="{sy(0.65):.2f}" font-family="DejaVu Sans" font-size="18">cold-finger merge stub</text>',
            f'<text x="{sx(-10.6):.2f}" y="{sy(-10.9):.2f}" font-family="DejaVu Sans" font-size="18">optical front/open window</text>',
            f'<text x="{sx(6.2):.2f}" y="{sy(-10.9):.2f}" font-family="DejaVu Sans" font-size="18">main-DR side/open cold port</text>',
            '<text x="55" y="455" text-anchor="middle" font-family="DejaVu Sans" font-size="18" transform="rotate(-90 55 455)">radius r (cm)</text>',
            '<text x="775" y="858" text-anchor="middle" font-family="DejaVu Sans" font-size="18">local optical axis x′ (cm)</text>',
            '</svg>',
            '',
        )
    )
    return "\n".join(items)


def validate(component: str, standalone: str, detector: str) -> dict[str, object]:
    declared = re.findall(r"^Volume\s+(\S+)\s*$", component, re.MULTILINE)
    copies = re.findall(r"^TES_Pixel_L\d+\.Copy\s+(\S+)\s*$", component, re.MULTILINE)
    mothers = re.findall(r"^\S+\.Mother\s+(\S+)\s*$", component, re.MULTILINE)
    template_count = len(re.findall(r"^Volume TES_Pixel_L\d$", component, re.MULTILINE))
    layer_count = len(re.findall(r"^Volume TES_L\d$", component, re.MULTILINE))
    checks = {
        "reference_tes_templates_6": template_count == 6,
        "reference_tes_containers_6": layer_count == 6,
        "reference_tes_pixel_copies_2256": len(copies) == 2256,
        "reference_pixel_names_unique": len(copies) == len(set(copies)),
        "declared_volume_names_unique": len(declared) == len(set(declared)),
        "all_component_mothers_resolve": all(m in set(declared) | {"SH3_ChimneyFrame"} for m in mothers),
        "component_has_no_world": "Volume WorldVolume" not in component,
        "component_has_no_instrument_frame": "Volume InstrumentFrame" not in component,
        "reference_top_level_z_offset_removed": not re.search(
            r"^\S+\.Position\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+-5\.2(?:0*)?\s*$",
            component,
            re.MULTILINE,
        ),
        "component_has_no_mxc_volume": not any("MXC" in name for name in declared),
        "three_active_bgo_volumes": len(
            re.findall(r"^Volume SH3_BGO40_(?:SideShield|FrontOpticalAnnulus|RearColdPortAnnulus)$", component, re.MULTILINE)
        )
        == 3,
        "bgo_40mm_radial_and_axial_thickness": math.isclose(
            BGO_OUTER_RADIUS_CM - BGO_INNER_RADIUS_CM, 4.0
        )
        and math.isclose(BGO_FRONT_X1_CM - BGO_FRONT_X0_CM, 4.0)
        and math.isclose(BGO_REAR_X1_CM - BGO_REAR_X0_CM, 4.0),
        "bgo_front_optical_aperture_preserved": (
            f"SH3_BGO40_FrontOpticalAnnulus.Shape TUBS {OPTICAL_APERTURE_RADIUS_CM:.6f} {BGO_OUTER_RADIUS_CM:.6f}"
            in component
        ),
        "bgo_rear_cold_port_preserved": (
            f"SH3_BGO40_RearColdPortAnnulus.Shape TUBS {COLD_PORT_RADIUS_CM:.6f} {BGO_OUTER_RADIUS_CM:.6f}"
            in component
        ),
        "mechanical_al_side_and_front_only": (
            "Volume SH3_BGO_MechanicalAl_SideShell_3mm" in component
            and "Volume SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm" in component
            and "MechanicalAl_Rear" not in component
        ),
        "mechanical_al_3mm_thickness": math.isclose(
            MECHANICAL_AL_OUTER_RADIUS_CM - MECHANICAL_AL_INNER_RADIUS_CM, 0.3
        )
        and math.isclose(
            MECHANICAL_AL_FRONT_X1_CM - MECHANICAL_AL_FRONT_X0_CM, 0.3
        ),
        "component_has_no_bi_material": ".Material Bi" not in component,
        "component_has_no_plastic_material": ".Material Plastic" not in component,
        "five_nested_local_shell_layers": all(f"Volume SH3_{layer.key}_SideShell" in component for layer in SHELL_LAYERS),
        "five_aligned_local_windows": all(f"Volume SH3_{layer.key}_OpticalWindow" in component for layer in SHELL_LAYERS),
        "five_rear_cold_port_annuli": all(f"Volume SH3_{layer.key}_RearColdPortAnnulus" in component for layer in SHELL_LAYERS),
        "no_dr_temperature_stage_names_in_volumes": not any(
            any(token in name for token in ("MXC", "50mK", "Still", "4K", "60K"))
            for name in declared
        ),
        "local_tes_bottom_plate_present": "Volume SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm" in component,
        "cold_finger_merge_stub_present": "Volume SH3_TES_ColdFinger_InterfaceStub" in component,
        "standalone_defines_single_world": standalone.count("Volume WorldVolume") == 1,
        "standalone_defines_single_chimney_frame": standalone.count("Volume SH3_ChimneyFrame") == 1,
        "detector_has_six_mdcalorimeters": len(re.findall(r"^MDCalorimeter D\d$", detector, re.MULTILINE)) == 6,
        "detector_has_three_bgo_scintillators": len(
            re.findall(r"^Scintillator SH3_BGO40_\S+_SD$", detector, re.MULTILINE)
        )
        == 3,
        "bgo_native_trigger_threshold_80kev": len(
            re.findall(r"^SH3_BGO40_\S+_SD\.TriggerThreshold 80$", detector, re.MULTILINE)
        )
        == 3,
    }
    shell_gaps = []
    for inner, outer in zip(SHELL_LAYERS, SHELL_LAYERS[1:]):
        gap = outer.inner_radius_cm - inner.outer_radius_cm
        shell_gaps.append({"inner_layer": inner.key, "outer_layer": outer.key, "radial_gap_cm": gap})
    copper_corner = math.sqrt(2.0) * TES_BOTTOM_PLATE_OUTER_HALF_CM
    clearance = SHELL_LAYERS[0].inner_radius_cm - copper_corner
    checks.update(
        {
            "all_shell_radial_gaps_positive": all(row["radial_gap_cm"] > 0 for row in shell_gaps),
            "bottom_cold_plate_inside_innermost_local_shell": clearance > 0,
            "optical_aperture_accepts_20cm2_equivalent_disk": OPTICAL_APERTURE_RADIUS_CM >= math.sqrt(20.0 / math.pi),
            "cold_stub_fits_all_rear_ports": COLD_STUB_RADIUS_CM < COLD_PORT_RADIUS_CM,
            "bgo_clears_outer_chimney_shell": BGO_INNER_RADIUS_CM
            > SHELL_LAYERS[-1].outer_radius_cm
            and BGO_FRONT_X1_CM < SHELL_LAYERS[-1].front_x_cm
            and BGO_REAR_X0_CM
            > SHELL_LAYERS[-1].rear_x_cm + SHELL_LAYERS[-1].cap_thickness_cm,
            "mechanical_al_clears_bgo": MECHANICAL_AL_INNER_RADIUS_CM
            > BGO_OUTER_RADIUS_CM
            and MECHANICAL_AL_FRONT_X1_CM < BGO_FRONT_X0_CM,
            "component_fits_standalone_frame": max(
                abs(MECHANICAL_AL_FRONT_X0_CM),
                MECHANICAL_AL_SIDE_X1_CM,
                MECHANICAL_AL_OUTER_RADIUS_CM,
            )
            < CHIMNEY_FRAME_HALF_CM,
        }
    )
    status = "PASS__SH3_COMPONENT_STATIC" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "physics_status": "GEOMETRY COMPONENT ONLY — UNMERGED/UNTRANSPORTED",
        "checks": checks,
        "counts": {
            "declared_component_volumes": len(declared),
            "tes_pixel_template_volumes": template_count,
            "tes_container_volumes": layer_count,
            "tes_pixel_copies": len(copies),
            "tes_total_absorbers": 6 * TES_PIXELS_PER_LAYER,
        },
        "clearances": {
            "bottom_plate_corner_to_innermost_shell_cm": clearance,
            "shell_radial_gaps": shell_gaps,
            "cold_stub_to_rear_port_radial_clearance_cm": COLD_PORT_RADIUS_CM - COLD_STUB_RADIUS_CM,
            "outer_shell_to_bgo_radial_clearance_cm": BGO_INNER_RADIUS_CM
            - SHELL_LAYERS[-1].outer_radius_cm,
            "bgo_to_mechanical_al_radial_clearance_cm": MECHANICAL_AL_INNER_RADIUS_CM
            - BGO_OUTER_RADIUS_CM,
            "20cm2_equivalent_radius_cm": math.sqrt(20.0 / math.pi),
            "optical_aperture_radius_cm": OPTICAL_APERTURE_RADIUS_CM,
        },
    }


def main() -> int:
    references = verify_reference()
    tes, supports, detector = inherited_blocks()
    detector += bgo_detector_block()
    component = component_text(tes, supports)
    standalone = standalone_text()
    materials = REFERENCE_MATERIALS.read_text(encoding="utf-8")
    outputs = {
        COMPONENT: component,
        STANDALONE: standalone,
        SETUP: setup_text(),
        DET: detector,
        MATERIALS: materials,
        FIGURE: svg_text(),
    }
    for path, text in outputs.items():
        atomic_text(path, text)
    validation = validate(component, standalone, detector)
    if not validation["status"].startswith("PASS"):
        atomic_json(STATIC, validation)
        raise BuildError("SH3 component static validation failed")
    atomic_json(STATIC, validation)
    manifest = {
        "status": "PASS__SH3_COMPONENT_BUILT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3",
        "coordinate_contract": {
            "frame": "SH3_ChimneyFrame",
            "optical_axis": "+x'",
            "optical_front": "negative x'",
            "main_dr_merge_side": "positive x'",
            "standalone_frame_position_cm": [0.0, 0.0, 0.0],
            "production_position_rotation": "deliberately undefined until SG3B merge",
            "reference_recenter_translation_cm": [0.0, 0.0, 5.2],
        },
        "reference_sg3b": references,
        "parameters": {
            "local_shell_layers": [asdict(layer) | {"outer_radius_cm": layer.outer_radius_cm} for layer in SHELL_LAYERS],
            "optical_aperture_radius_cm": OPTICAL_APERTURE_RADIUS_CM,
            "cold_port_radius_cm": COLD_PORT_RADIUS_CM,
            "tes_layer_x_cm": list(TES_LAYER_X_CM),
            "tes_pixels_per_layer": TES_PIXELS_PER_LAYER,
            "tes_total_absorbers": 6 * TES_PIXELS_PER_LAYER,
            "tes_bottom_plate_x_cm": TES_BOTTOM_PLATE_X_CM,
            "reference_instrument_tes_center_z_cm": REFERENCE_INSTRUMENT_TES_CENTER_Z_CM,
            "cold_stub_radius_cm": COLD_STUB_RADIUS_CM,
            "cold_stub_x_extent_cm": [COLD_STUB_X0_CM, COLD_STUB_X1_CM],
            "bgo": {
                "thickness_cm": BGO_THICKNESS_CM,
                "inner_radius_cm": BGO_INNER_RADIUS_CM,
                "outer_radius_cm": BGO_OUTER_RADIUS_CM,
                "side_x_extent_cm": [BGO_SIDE_X0_CM, BGO_SIDE_X1_CM],
                "front_x_extent_cm": [BGO_FRONT_X0_CM, BGO_FRONT_X1_CM],
                "rear_x_extent_cm": [BGO_REAR_X0_CM, BGO_REAR_X1_CM],
                "front_optical_aperture_radius_cm": OPTICAL_APERTURE_RADIUS_CM,
                "rear_cold_port_radius_cm": COLD_PORT_RADIUS_CM,
                "native_trigger_threshold_kev": 80,
                "selection_basis": "Retain the project-validated 40 mm SG3 side baseline. Thinner 30/20 mm side cases increased straight-ray cavity leakage; no local evidence establishes net benefit beyond 40 mm.",
            },
            "external_mechanical_aluminium": {
                "thickness_cm": MECHANICAL_AL_THICKNESS_CM,
                "inner_radius_cm": MECHANICAL_AL_INNER_RADIUS_CM,
                "outer_radius_cm": MECHANICAL_AL_OUTER_RADIUS_CM,
                "side_x_extent_cm": [
                    MECHANICAL_AL_SIDE_X0_CM,
                    MECHANICAL_AL_SIDE_X1_CM,
                ],
                "front_x_extent_cm": [
                    MECHANICAL_AL_FRONT_X0_CM,
                    MECHANICAL_AL_FRONT_X1_CM,
                ],
                "rear_end_cap": False,
            },
            "standalone_frame_half_size_cm": CHIMNEY_FRAME_HALF_CM,
        },
        "included": [
            "five generic nested local shell layers with thermal-stage ownership intentionally unset",
            "aligned windows and structural front annuli at every local layer",
            "rear annular caps with one small coaxial cold-finger port",
            "pinned SG3B six-layer 2256-pixel Ta TES stack, rigidly recentered into the SH3 local frame",
            "pinned SG3B silicon substrates and per-layer copper support frames with unchanged relative coordinates",
            "local TES bottom copper ring, minimal hub/spokes, and merge stub",
            "40 mm active BGO side shield plus 40 mm optical-front and cold-port-rear annuli",
            "80 keV native BGO scorer definitions for the three BGO volumes",
            "3 mm external mechanical aluminium side shell and optical-front annulus",
        ],
        "excluded": [
            "all main-DR cold plates and vessels, including MXC, Still, 4 K, and 60 K structures",
            "main-DR cold finger beyond the SH3 merge stub",
            "mechanical aluminium rear end cap on the cold-finger face",
            "plastic veto, passive Bi, W collimator, and BGO optical coupling/readout hardware",
            "signal cables, SQUID/readout, thermal intercept straps, and flight structural supports",
            "transport, activation, delayed source, detector response, timing, and sensitivity claims",
        ],
        "mass_proxy": mass_proxy(),
        "outputs": {path.name: file_record(path) for path in outputs},
        "static_validation": file_record(STATIC),
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps({"status": manifest["status"], "manifest": str(MANIFEST), "static": validation["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
