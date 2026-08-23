#!/usr/bin/env python3
"""Build the non-overwriting SH3 pure-DR base from pinned SG3B authority.

The output retains the dilution-refrigerator plates, thermal hardware, service
pipes, and mechanical support cage.  It removes the TES/detector bay, windows,
collimator, BGO, outer plastic/BPE shield packages, readout, and harness proxy.
The former side-window stack is replaced by five aluminium shells carrying one
coaxial 1.50 cm-diameter cold-finger interface.  No chimney is assembled here.
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
REFERENCE_INTRO = REFERENCE_PACKAGE / "geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
REFERENCE_MATERIALS = REFERENCE_PACKAGE / "geometry/Materials_DEMO2_DR_v3p5.geo"
PINNED = {
    "geo": "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9",
    "intro": "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    "materials": "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
}

GEO = GEOMETRY / "SH3_PureDR_Base.geo"
SETUP = GEOMETRY / "SH3_PureDR_Base.geo.setup"
MATERIALS = GEOMETRY / "Materials_SH3_DR_Base.geo"
MANIFEST = DATA / "dr_base_manifest.json"
STATIC = AUDIT / "dr_base_static_validation.json"
FIGURE = FIGURES / "sh3_pure_dr_base_xz_section.svg"

PORT_DIAMETER_CM = 1.50
PORT_RADIUS_CM = 0.5 * PORT_DIAMETER_CM
PORT_CENTER_Z_CM = -5.2
INSTRUMENT_FRAME_ROTATION_DEG = (0.0, 45.0, 0.0)


@dataclass(frozen=True)
class Shell:
    key: str
    label: str
    material: str
    inner_radius_cm: float
    outer_radius_cm: float
    side_z_min_cm: float
    side_z_max_cm: float
    bottom_z_min_cm: float
    bottom_z_max_cm: float
    color: str


SHELLS = (
    Shell("MXC50mK", "50 mK aluminium can", "Aluminium", 15.1, 15.3, -9.7, -0.3, -9.9, -9.7, "#2457d6"),
    Shell("Still", "Still aluminium shield", "Aluminium", 15.5, 15.8, -10.4, 10.7, -10.7, -10.4, "#367ee8"),
    Shell("4K", "4 K aluminium shield", "Aluminium", 17.7, 18.0, -11.4, 19.7, -11.7, -11.4, "#49a6e9"),
    Shell("60K", "60 K aluminium shield", "Aluminium", 18.2, 18.5, -12.4, 28.65, -12.7, -12.4, "#79c8e8"),
    Shell("VacuumJacket", "300 K aluminium vacuum jacket", "Aluminium", 20.1, 20.6, -13.6, 37.5, -14.1, -13.6, "#9aa5b1"),
)


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
    paths = {
        "geo": REFERENCE_GEO,
        "intro": REFERENCE_INTRO,
        "materials": REFERENCE_MATERIALS,
    }
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
    begin = text.index(start)
    end = text.index(stop)
    if end <= begin:
        raise BuildError(f"reference extraction markers are reversed: {start!r}, {stop!r}")
    return text[begin:end].rstrip() + "\n"


def retained_blocks(reference: str) -> dict[str, str]:
    return {
        "cold_plates_and_internal_supports": extract_between(
            reference,
            "// Volume ColdPlate_MXC_50mK_SD_anchor; material=Copper",
            "// Volume Still_Shield_Al_side_window_bottom_cap; material=Aluminium",
        ),
        "dr_core": extract_between(
            reference,
            "// Volume DR_MixingChamber_Cu; material=Copper",
            "// Volume SQUID_uMUX_Box_Al_relocated_offbeam_minimal; material=Aluminium",
        ),
        "g10_support_rings": extract_between(
            reference,
            "// Volume G10_Support_Ring_MXC_CP; material=G10",
            "// Volume Passive_W_Bottom_Plate_detector_bay; material=W",
        ),
        "top_services_and_outer_support_cage": extract_between(
            reference,
            "// BEGIN XS400_TOP_300K_FEEDTHROUGH_PIPE_PROXY",
            "// BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_PATCH",
        ),
    }


def intro_text() -> str:
    return """// SH3 pure dilution-refrigerator base; chimney intentionally not assembled.
// Parent-frame 45 degree tilt is retained from pinned SG3B.
Include Materials_SH3_DR_Base.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0

Volume InstrumentFrame
InstrumentFrame.Visibility 0
InstrumentFrame.Material Vacuum
InstrumentFrame.Shape BRIK 80 80 80
InstrumentFrame.Position 0 0 0
InstrumentFrame.Rotation 0 45 0
InstrumentFrame.Mother WorldVolume

"""


def shell_text(shell: Shell) -> str:
    prefix = f"SH3_DRBase_{shell.key}"
    cutter_half_height = 0.5 * (shell.outer_radius_cm - shell.inner_radius_cm) + 0.20
    cutter_center_x = -0.5 * (shell.inner_radius_cm + shell.outer_radius_cm)
    return f"""// {shell.label}; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON {prefix}_FullSideShellShape
{prefix}_FullSideShellShape.Parameters 0 360 2 {shell.side_z_min_cm:.6f} {shell.inner_radius_cm:.6f} {shell.outer_radius_cm:.6f} {shell.side_z_max_cm:.6f} {shell.inner_radius_cm:.6f} {shell.outer_radius_cm:.6f}
Shape TUBS {prefix}_ColdFingerPortCutShape
{prefix}_ColdFingerPortCutShape.Parameters 0 {PORT_RADIUS_CM:.6f} {cutter_half_height:.6f} 0 360
Orientation {prefix}_ColdFingerPortCutOrientation
{prefix}_ColdFingerPortCutOrientation.Position {cutter_center_x:.6f} 0 {PORT_CENTER_Z_CM:.6f}
{prefix}_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction {prefix}_PortedSideShellShape
{prefix}_PortedSideShellShape.Parameters {prefix}_FullSideShellShape {prefix}_ColdFingerPortCutShape {prefix}_ColdFingerPortCutOrientation

Volume {prefix}_PortedSideShell
{prefix}_PortedSideShell.Material {shell.material}
{prefix}_PortedSideShell.Visibility 1
{prefix}_PortedSideShell.Shape {prefix}_PortedSideShellShape
{prefix}_PortedSideShell.Position 0 0 0
{prefix}_PortedSideShell.Mother InstrumentFrame

Volume {prefix}_BottomCap
{prefix}_BottomCap.Material {shell.material}
{prefix}_BottomCap.Visibility 1
{prefix}_BottomCap.Shape PCON 0 360 2 {shell.bottom_z_min_cm:.6f} 0 {shell.outer_radius_cm:.6f} {shell.bottom_z_max_cm:.6f} 0 {shell.outer_radius_cm:.6f}
{prefix}_BottomCap.Position 0 0 0
{prefix}_BottomCap.Mother InstrumentFrame

"""


def geometry_text(blocks: dict[str, str]) -> str:
    retained = "\n".join(
        (
            "// BEGIN PINNED_SG3B_COLD_PLATES_AND_INTERNAL_SUPPORTS",
            blocks["cold_plates_and_internal_supports"],
            "// END PINNED_SG3B_COLD_PLATES_AND_INTERNAL_SUPPORTS\n",
            "// BEGIN SH3_DRBASE_PORTED_THERMAL_SHELLS",
            "".join(shell_text(shell) for shell in SHELLS),
            "// END SH3_DRBASE_PORTED_THERMAL_SHELLS\n",
            "// BEGIN PINNED_SG3B_DR_CORE",
            blocks["dr_core"],
            "// END PINNED_SG3B_DR_CORE\n",
            "// BEGIN PINNED_SG3B_G10_SUPPORT_RINGS",
            blocks["g10_support_rings"],
            "// END PINNED_SG3B_G10_SUPPORT_RINGS\n",
            "// BEGIN PINNED_SG3B_TOP_SERVICES_AND_OUTER_SUPPORT_CAGE",
            blocks["top_services_and_outer_support_cage"],
            "// END PINNED_SG3B_TOP_SERVICES_AND_OUTER_SUPPORT_CAGE\n",
        )
    )
    return intro_text() + retained


def setup_text() -> str:
    return """Name SH3_PureDR_Base
Version 1
Include SH3_PureDR_Base.geo
SurroundingSphere 60 5 0 9 60
"""


def svg_text() -> str:
    """Return a dimensioned section drawing; this does not alter the geometry."""
    width, height = 2000, 1250
    x_min, x_max = -23.5, 23.5
    z_min, z_max = -16.0, 47.0
    left, right, top, bottom = 105.0, 825.0, 135.0, 1100.0

    def sx(x: float) -> float:
        return left + (x - x_min) / (x_max - x_min) * (right - left)

    def sz(z: float) -> float:
        return bottom - (z - z_min) / (z_max - z_min) * (bottom - top)

    def rect(
        x0: float,
        x1: float,
        z0: float,
        z1: float,
        fill: str,
        opacity: float = 0.82,
        *,
        stroke: str = "none",
        stroke_width: float = 0.0,
        dash: str = "",
    ) -> str:
        return (
            f'<rect x="{sx(x0):.2f}" y="{sz(z1):.2f}" width="{sx(x1)-sx(x0):.2f}" '
            f'height="{sz(z0)-sz(z1):.2f}" fill="{fill}" opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"'
            + (f' stroke-dasharray="{dash}"' if dash else "")
            + "/>"
        )

    def line(x1: float, z1: float, x2: float, z2: float, **attrs: object) -> str:
        attr_text = " ".join(f'{key.replace("_", "-")}="{value}"' for key, value in attrs.items())
        return (
            f'<line x1="{sx(x1):.2f}" y1="{sz(z1):.2f}" x2="{sx(x2):.2f}" '
            f'y2="{sz(z2):.2f}" {attr_text}/>'
        )

    def text_at(x: float, z: float, value: str, **attrs: object) -> str:
        attr_text = " ".join(f'{key.replace("_", "-")}="{value_}"' for key, value_ in attrs.items())
        return f'<text x="{sx(x):.2f}" y="{sz(z):.2f}" {attr_text}>{value}</text>'

    def plate(radius: float, z: float, half_z: float, material: str) -> list[str]:
        color = "#d99032" if material == "Cu" else "#8ecae6"
        result = [rect(-radius, radius, z - half_z, z + half_z, color, 0.88, stroke="#5b6470", stroke_width=0.7)]
        # Representative markers only: the geometry retains 48 vacuum holes on
        # every DR cold plate, but most do not intersect the y'=0 section.
        for x in (-12.0, -7.8, 0.0, 7.8, 12.0):
            result.append(
                f'<circle cx="{sx(x):.2f}" cy="{sz(z):.2f}" r="2.2" fill="#ffffff" stroke="#5b6470" stroke-width="0.6"/>'
            )
        return result

    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#333"/></marker><pattern id="removed" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" stroke="#c43b3b" stroke-width="2" opacity="0.26"/></pattern></defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="1000" y="42" text-anchor="middle" font-family="DejaVu Sans" font-size="29" font-weight="700">SH3 pure-DR base — detailed verification section</text>',
        '<text x="1000" y="76" text-anchor="middle" font-family="DejaVu Sans" font-size="18" fill="#444">Local x′–z′ geometry; equal spatial scale in the main panel; no chimney or cold finger assembled</text>',
        '<rect x="88" y="116" width="754" height="1002" fill="#fafcff" stroke="#aeb7c2" stroke-width="1.4"/>',
        '<text x="112" y="157" font-family="DejaVu Sans" font-size="20" font-weight="700">A. Exact y′=0 section of retained DR base</text>',
    ]

    # Removed SG3B detector bay is shown as a ghost only.  Its six former TES
    # layer centres were x'=-3,-1.8,-0.6,+0.6,+1.8,+3 cm at z'=-5.2 cm.
    items.append(rect(-3.25, 3.25, -7.15, -3.25, "url(#removed)", 1.0, stroke="#c43b3b", stroke_width=1.5, dash="7 5"))
    for x in (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0):
        items.append(rect(x - 0.15, x + 0.15, -7.0, -3.4, "#ef767a", 0.24, stroke="#c43b3b", stroke_width=0.5))

    # Five nested aluminium shells.  In this axial plane, an x'-axis circular
    # penetration is a 1.50-cm-high rectangular gap through each negative wall.
    gap_low = PORT_CENTER_Z_CM - PORT_RADIUS_CM
    gap_high = PORT_CENTER_Z_CM + PORT_RADIUS_CM
    for shell in reversed(SHELLS):
        items.append(rect(-shell.outer_radius_cm, -shell.inner_radius_cm, shell.side_z_min_cm, min(gap_low, shell.side_z_max_cm), shell.color))
        items.append(rect(-shell.outer_radius_cm, -shell.inner_radius_cm, max(gap_high, shell.side_z_min_cm), shell.side_z_max_cm, shell.color))
        items.append(rect(shell.inner_radius_cm, shell.outer_radius_cm, shell.side_z_min_cm, shell.side_z_max_cm, shell.color))
        items.append(rect(-shell.outer_radius_cm, shell.outer_radius_cm, shell.bottom_z_min_cm, shell.bottom_z_max_cm, shell.color, 0.68))

    # Main cold plates and upper lid.
    for args in (
        (15.0, 0.0, 0.2, "Cu"),
        (15.0, 5.0, 0.2, "Cu"),
        (15.0, 11.0, 0.2, "Cu"),
        (17.5, 20.0, 0.2, "Cu"),
        (17.5, 29.0, 0.2, "Al"),
        (20.0, 38.0, 0.3, "Al"),
    ):
        items.extend(plate(*args))

    # DR process components intersecting y'=0.
    items.extend(
        (
            rect(-2.2, 2.2, 0.31, 2.11, "#d99032", 0.95, stroke="#754b18", stroke_width=0.8),
            rect(-3.5, -2.5, 0.4, 2.2, "#c9cdd3", 0.95, stroke="#666", stroke_width=0.7),
            rect(2.5, 3.5, 0.4, 2.2, "#c9cdd3", 0.95, stroke="#666", stroke_width=0.7),
            rect(5.2, 5.5, 0.4, 4.6, "#b87333", 0.9),
            rect(5.2, 5.5, 5.4, 9.6, "#b87333", 0.9),
            rect(-2.6, 2.6, 9.0, 10.6, "#d99032", 0.95, stroke="#754b18", stroke_width=0.8),
            rect(-2.9, -2.7, 9.2, 9.5, "#69727d", 0.95),
            rect(2.7, 2.9, 9.2, 9.5, "#69727d", 0.95),
            rect(-1.8, 1.8, 18.4, 19.6, "#d99032", 0.95, stroke="#754b18", stroke_width=0.8),
            rect(-1.9, 1.9, 26.3, 28.5, "#444b53", 0.92, stroke="#222", stroke_width=0.8),
            rect(21.2, 21.6, 12.0, 37.4, "#69727d", 0.9),
            rect(-10.85, -10.55, 24.0, 28.5, "#d99032", 0.95),
        )
    )

    # Representative projected supports: they are deliberately dashed because
    # their centres are off the exact y'=0 cut plane.
    for x, z0, z1, radius in (
        (6.17, 0.32, 4.68, 0.85),
        (-6.17, 0.32, 4.68, 0.85),
        (6.19, 5.32, 10.68, 0.82),
        (-6.19, 5.32, 10.68, 0.82),
        (4.30, 11.32, 19.68, 1.16),
        (-4.30, 11.32, 19.68, 1.16),
        (6.13, 20.32, 28.68, 1.33),
        (-6.13, 20.32, 28.68, 1.33),
        (7.30, 29.32, 37.68, 1.15),
        (-7.30, 29.32, 37.68, 1.15),
    ):
        items.append(rect(x - radius, x + radius, z0, z1, "none", 1.0, stroke="#5f7f3f", stroke_width=1.2, dash="5 4"))

    # Exact axes and the coaxial port centreline.
    items.extend(
        (
            line(x_min, 0, x_max, 0, stroke="#333", stroke_width="1.0"),
            line(0, z_min, 0, z_max, stroke="#333", stroke_width="1.0"),
            line(-21.2, PORT_CENTER_Z_CM, -14.35, PORT_CENTER_Z_CM, stroke="#d62728", stroke_width="2.4", stroke_dasharray="8 5"),
            line(-21.2, gap_low, -14.35, gap_low, stroke="#d62728", stroke_width="1.0", stroke_dasharray="4 4"),
            line(-21.2, gap_high, -14.35, gap_high, stroke="#d62728", stroke_width="1.0", stroke_dasharray="4 4"),
            text_at(-13.8, -3.85, "Ø1.50 port band", font_family="DejaVu Sans", font_size="15", fill="#b71c1c"),
            text_at(-3.05, -7.7, "removed SG3B TES bay (ghost only)", font_family="DejaVu Sans", font_size="14", fill="#a42727"),
            '<text x="465" y="1145" text-anchor="middle" font-family="DejaVu Sans" font-size="17">local radial x′ (cm)</text>',
            '<text x="48" y="615" text-anchor="middle" font-family="DejaVu Sans" font-size="17" transform="rotate(-90 48 615)">DR axis z′ (cm)</text>',
        )
    )

    # Main-panel dimension arrows.
    items.extend(
        (
            f'<line x1="{sx(-20.6):.2f}" y1="{sz(-15.25):.2f}" x2="{sx(20.6):.2f}" y2="{sz(-15.25):.2f}" stroke="#333" stroke-width="1.2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            f'<text x="{sx(0):.2f}" y="{sz(-15.55):.2f}" text-anchor="middle" font-family="DejaVu Sans" font-size="14">vacuum jacket OD 41.20 cm</text>',
            f'<line x1="{sx(22.55):.2f}" y1="{sz(-14.1):.2f}" x2="{sx(22.55):.2f}" y2="{sz(38.3):.2f}" stroke="#333" stroke-width="1.2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            f'<text x="{sx(23.0):.2f}" y="{sz(12.1):.2f}" text-anchor="middle" font-family="DejaVu Sans" font-size="14" transform="rotate(-90 {sx(23.0):.2f} {sz(12.1):.2f})">shell + lid span 52.40 cm</text>',
        )
    )

    # Right-side port detail.  This makes explicit why the axial view uses
    # rectangular wall gaps while the transverse face shows a circle.
    items.extend(
        (
            '<rect x="890" y="116" width="1060" height="365" fill="#fafcff" stroke="#aeb7c2" stroke-width="1.4"/>',
            '<text x="916" y="153" font-family="DejaVu Sans" font-size="20" font-weight="700">B. Port stack detail at z′ = −5.20 cm</text>',
            '<text x="916" y="182" font-family="DejaVu Sans" font-size="15" fill="#444">Axial x′–z′ cut: one coaxial bore through the five negative-x′ walls</text>',
            '<line x1="930" y1="300" x2="1470" y2="300" stroke="#d62728" stroke-width="2" stroke-dasharray="8 5" marker-end="url(#arrow)"/>',
            '<text x="934" y="286" font-family="DejaVu Sans" font-size="14" fill="#b71c1c">cold-finger axis (+x′)</text>',
        )
    )
    inset_scale = 40.0
    inset_x0 = 940.0
    inset_center_y = 300.0
    inset_min_x = -21.0
    for shell in reversed(SHELLS):
        wall_x = inset_x0 + (shell.inner_radius_cm * -1.0 - inset_min_x) * inset_scale
        wall_w = (shell.outer_radius_cm - shell.inner_radius_cm) * inset_scale
        items.append(
            f'<rect x="{wall_x-wall_w:.2f}" y="210" width="{wall_w:.2f}" height="180" fill="{shell.color}" opacity="0.88"/>'
        )
        items.append(
            f'<rect x="{wall_x-wall_w-0.5:.2f}" y="270" width="{wall_w+1.0:.2f}" height="60" fill="#ffffff" stroke="#d62728" stroke-width="1.2"/>'
        )
    items.extend(
        (
            '<line x1="930" y1="270" x2="930" y2="330" stroke="#333" stroke-width="1.1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            '<text x="910" y="304" text-anchor="middle" font-family="DejaVu Sans" font-size="14" transform="rotate(-90 910 304)">1.50 cm</text>',
            '<text x="940" y="416" font-family="DejaVu Sans" font-size="14">300 K</text>',
            '<text x="1023" y="416" font-family="DejaVu Sans" font-size="14">60 K</text>',
            '<text x="1059" y="443" font-family="DejaVu Sans" font-size="14">4 K</text>',
            '<text x="1145" y="416" font-family="DejaVu Sans" font-size="14">Still</text>',
            '<text x="1168" y="443" font-family="DejaVu Sans" font-size="14">50 mK</text>',
            '<line x1="1510" y1="218" x2="1510" y2="386" stroke="#aeb7c2" stroke-width="1"/>',
            '<text x="1540" y="215" font-family="DejaVu Sans" font-size="16" font-weight="700">Transverse y′–z′ port face</text>',
            '<rect x="1660" y="240" width="151.84" height="151.84" fill="none" stroke="#c43b3b" stroke-width="1.6" stroke-dasharray="8 5"/>',
            '<circle cx="1735.92" cy="315.92" r="30" fill="#ffffff" stroke="#d62728" stroke-width="2.5"/>',
            '<line x1="1705.92" y1="410" x2="1765.92" y2="410" stroke="#333" stroke-width="1.1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            '<text x="1735.92" y="437" text-anchor="middle" font-family="DejaVu Sans" font-size="14">new Ø1.50 cm</text>',
            '<text x="1735.92" y="231" text-anchor="middle" font-family="DejaVu Sans" font-size="14" fill="#a42727">old 3.796 × 3.796 cm window (removed)</text>',
        )
    )

    # Retained-dimension table and legend.
    items.extend(
        (
            '<rect x="890" y="505" width="650" height="585" fill="#fafcff" stroke="#aeb7c2" stroke-width="1.4"/>',
            '<text x="916" y="542" font-family="DejaVu Sans" font-size="20" font-weight="700">C. Retained shells and plates (cm, local)</text>',
            '<text x="916" y="579" font-family="DejaVu Sans" font-size="14" font-weight="700">Stage</text>',
            '<text x="1095" y="579" font-family="DejaVu Sans" font-size="14" font-weight="700">Rin–Rout</text>',
            '<text x="1240" y="579" font-family="DejaVu Sans" font-size="14" font-weight="700">side z′ span</text>',
            '<text x="1405" y="579" font-family="DejaVu Sans" font-size="14" font-weight="700">bottom</text>',
        )
    )
    for index, shell in enumerate(SHELLS):
        y = 612 + index * 39
        items.extend(
            (
                f'<rect x="916" y="{y-14}" width="16" height="16" fill="{shell.color}"/>',
                f'<text x="941" y="{y}" font-family="DejaVu Sans" font-size="14">{shell.key}</text>',
                f'<text x="1095" y="{y}" font-family="DejaVu Sans" font-size="14">{shell.inner_radius_cm:.1f}–{shell.outer_radius_cm:.1f}</text>',
                f'<text x="1240" y="{y}" font-family="DejaVu Sans" font-size="14">{shell.side_z_min_cm:.2f} to {shell.side_z_max_cm:.2f}</text>',
                f'<text x="1405" y="{y}" font-family="DejaVu Sans" font-size="14">{shell.bottom_z_min_cm:.1f} to {shell.bottom_z_max_cm:.1f}</text>',
            )
        )
    items.extend(
        (
            '<line x1="916" y1="820" x2="1514" y2="820" stroke="#aeb7c2" stroke-width="1"/>',
            '<text x="916" y="853" font-family="DejaVu Sans" font-size="15" font-weight="700">Cold plates / lid</text>',
            '<text x="916" y="883" font-family="DejaVu Sans" font-size="14">MXC Cu: R15.0, z′=0.0, t=0.4</text>',
            '<text x="916" y="911" font-family="DejaVu Sans" font-size="14">100 mK Cu: R15.0, z′=5.0, t=0.4</text>',
            '<text x="916" y="939" font-family="DejaVu Sans" font-size="14">Still Cu: R15.0, z′=11.0, t=0.4</text>',
            '<text x="916" y="967" font-family="DejaVu Sans" font-size="14">4 K Cu: R17.5, z′=20.0, t=0.4</text>',
            '<text x="916" y="995" font-family="DejaVu Sans" font-size="14">60 K Al: R17.5, z′=29.0, t=0.4</text>',
            '<text x="916" y="1023" font-family="DejaVu Sans" font-size="14">300 K Al lid: R20.0, z′=38.0, t=0.6</text>',
            '<text x="916" y="1061" font-family="DejaVu Sans" font-size="13" fill="#555">Small white marks represent the retained 48-hole plate pattern; not every hole intersects this plane.</text>',
        )
    )

    # Coordinate/orientation audit and explicit removal ledger.
    items.extend(
        (
            '<rect x="1570" y="505" width="380" height="585" fill="#fafcff" stroke="#aeb7c2" stroke-width="1.4"/>',
            '<text x="1596" y="542" font-family="DejaVu Sans" font-size="20" font-weight="700">D. Coordinate &amp; scope audit</text>',
            '<line x1="1730" y1="675" x2="1730" y2="580" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>',
            '<text x="1744" y="588" font-family="DejaVu Sans" font-size="14">world vertical</text>',
            '<line x1="1730" y1="675" x2="1797" y2="608" stroke="#2457d6" stroke-width="3" marker-end="url(#arrow)"/>',
            '<text x="1802" y="608" font-family="DejaVu Sans" font-size="14" fill="#2457d6">local z′</text>',
            '<line x1="1730" y1="675" x2="1663" y2="608" stroke="#d62728" stroke-width="3" marker-end="url(#arrow)"/>',
            '<text x="1600" y="606" font-family="DejaVu Sans" font-size="14" fill="#b71c1c">local −x′ / port</text>',
            '<path d="M1730 635 A40 40 0 0 1 1758 647" fill="none" stroke="#333" stroke-width="1.2"/>',
            '<text x="1753" y="632" font-family="DejaVu Sans" font-size="13">45°</text>',
            '<text x="1596" y="720" font-family="DejaVu Sans" font-size="14" font-weight="700">Current base authority</text>',
            '<text x="1596" y="750" font-family="DejaVu Sans" font-size="14">• InstrumentFrame.Rotation = 0 45 0</text>',
            '<text x="1596" y="778" font-family="DejaVu Sans" font-size="14">• Port axis = local x′, not world vertical</text>',
            '<text x="1596" y="806" font-family="DejaVu Sans" font-size="14">• Chimney alignment deferred to assembly</text>',
            '<text x="1596" y="850" font-family="DejaVu Sans" font-size="14" font-weight="700">Intentionally absent from this base</text>',
            '<text x="1596" y="880" font-family="DejaVu Sans" font-size="14">• TES arrays and near-TES Cu/Al/Bi</text>',
            '<text x="1596" y="908" font-family="DejaVu Sans" font-size="14">• all old windows and filters</text>',
            '<text x="1596" y="936" font-family="DejaVu Sans" font-size="14">• W collimator and W bottom plate</text>',
            '<text x="1596" y="964" font-family="DejaVu Sans" font-size="14">• BGO, Kapton, outer Al shield</text>',
            '<text x="1596" y="992" font-family="DejaVu Sans" font-size="14">• plastic scintillator and BPE</text>',
            '<text x="1596" y="1020" font-family="DejaVu Sans" font-size="14">• SQUID/readout/cable bundles</text>',
            '<text x="1596" y="1060" font-family="DejaVu Sans" font-size="13" fill="#a42727">Red hatching in panel A is reference-only, not geometry.</text>',
            '<text x="1000" y="1212" text-anchor="middle" font-family="DejaVu Sans" font-size="15" fill="#444">Drawing generated from build_sh3_dr_base.py constants; geometry content unchanged by this figure revision.</text>',
            '</svg>',
            '',
        )
    )
    return "\n".join(items)


def validate(geometry: str, setup: str) -> dict[str, object]:
    declared = re.findall(r"^Volume\s+(\S+)\s*$", geometry, re.MULTILINE)
    copies = re.findall(r"^\S+\.Copy\s+(\S+)\s*$", geometry, re.MULTILINE)
    mothers = re.findall(r"^\S+\.Mother\s+(\S+)\s*$", geometry, re.MULTILINE)
    available = set(declared) | set(copies) | {"0"}
    volume_materials = re.findall(r"^(\S+)\.Material\s+(\S+)\s*$", geometry, re.MULTILINE)
    material_by_volume = {name: material for name, material in volume_materials}
    shell_names = [f"SH3_DRBase_{shell.key}_PortedSideShell" for shell in SHELLS]
    removed_name_patterns = (
        r"TES",
        r"BGO",
        r"Plastic",
        r"Collimator",
        r"^Win_",
        r"Passive_W",
        r"Bi_MXC",
        r"SQUID",
        r"Bundle_",
        r"CryoShell_BPE",
    )
    prohibited_names = [
        name for name in declared if any(re.search(pattern, name) for pattern in removed_name_patterns)
    ]
    prohibited_materials = {
        "BGO", "PlasticScintillator", "BoratedPolyethylene5wtB", "W", "Bi", "Ta", "Silicon"
    }
    checks = {
        "world_and_instrument_frame_present": {"WorldVolume", "InstrumentFrame"}.issubset(declared),
        "instrument_frame_retains_45deg_tilt": "InstrumentFrame.Rotation 0 45 0" in geometry,
        "declared_volume_names_unique": len(declared) == len(set(declared)),
        "copy_names_unique": len(copies) == len(set(copies)),
        "all_mothers_resolve": all(mother in available for mother in mothers),
        "five_ported_dr_shells_present": all(name in declared for name in shell_names),
        "ten_shell_and_bottom_cap_volumes": sum(name.startswith("SH3_DRBase_") for name in declared) == 10,
        "port_radius_is_0p75cm_in_all_cutters": all(
            f"SH3_DRBase_{shell.key}_ColdFingerPortCutShape.Parameters 0 0.750000" in geometry
            for shell in SHELLS
        ),
        "port_center_retains_former_window_z": all(
            f"SH3_DRBase_{shell.key}_ColdFingerPortCutOrientation.Position" in geometry
            and f" 0 {PORT_CENTER_Z_CM:.6f}" in geometry
            for shell in SHELLS
        ),
        "main_dr_cold_plates_retained": all(
            name in declared
            for name in (
                "ColdPlate_MXC_50mK_SD_anchor",
                "ColdPlate_CP_100mK_intercept",
                "ColdPlate_Still_0p7K",
                "ColdPlate_4K",
                "ColdPlate_60K",
                "Plate_300K_Top_Service_Lid",
            )
        ),
        "dr_core_retained": all(
            name in declared
            for name in (
                "DR_MixingChamber_Cu",
                "DR_Still_Pot_Cu",
                "DR_4K_Condenser_Cu",
                "DR_60K_Charcoal_Trap",
            )
        ),
        "no_removed_family_volume_names": not prohibited_names,
        "no_removed_family_material_assignments": not any(
            material in prohibited_materials for material in material_by_volume.values()
        ),
        "no_detector_declaration": not re.search(r"^(?:MDCalorimeter|Scintillator)\s+", geometry, re.MULTILINE),
        "chimney_not_assembled": "SH3_Chimney" not in geometry,
        "setup_includes_only_pure_dr_geometry": setup.count("Include SH3_PureDR_Base.geo") == 1,
    }
    shell_clearances = [
        {
            "inner_shell": inner.key,
            "outer_shell": outer.key,
            "radial_gap_cm": outer.inner_radius_cm - inner.outer_radius_cm,
        }
        for inner, outer in zip(SHELLS, SHELLS[1:])
    ]
    checks["all_shell_radial_gaps_positive"] = all(
        row["radial_gap_cm"] > 0 for row in shell_clearances
    )
    status = "PASS__SH3_PURE_DR_BASE_STATIC" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "physics_status": "PURE DR GEOMETRY ONLY — CHIMNEY UNASSEMBLED/UNTRANSPORTED",
        "checks": checks,
        "counts": {
            "declared_volumes": len(declared),
            "copy_placements": len(copies),
            "ported_shells": len(shell_names),
            "prohibited_volume_names": prohibited_names,
        },
        "interface": {
            "diameter_cm": PORT_DIAMETER_CM,
            "radius_cm": PORT_RADIUS_CM,
            "center_local_cm": [None, 0.0, PORT_CENTER_Z_CM],
            "axis": "local x' at former SG3B side-window stack",
            "shell_radial_gaps": shell_clearances,
        },
    }


def main() -> int:
    references = verify_reference()
    reference = REFERENCE_GEO.read_text(encoding="utf-8")
    blocks = retained_blocks(reference)
    geometry = geometry_text(blocks)
    setup = setup_text()
    materials = REFERENCE_MATERIALS.read_text(encoding="utf-8")
    outputs = {GEO: geometry, SETUP: setup, MATERIALS: materials, FIGURE: svg_text()}
    for path, text in outputs.items():
        atomic_text(path, text)

    validation = validate(geometry, setup)
    atomic_json(STATIC, validation)
    if not validation["status"].startswith("PASS"):
        raise BuildError("SH3 pure-DR base static validation failed")

    block_records = {
        name: {"bytes": len(text.encode("utf-8")), "sha256": sha256_bytes(text.encode("utf-8"))}
        for name, text in blocks.items()
    }
    manifest = {
        "status": "PASS__SH3_PURE_DR_BASE_BUILT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_PureDR_Base",
        "reference_sg3b": references,
        "retained_reference_blocks": block_records,
        "coordinate_contract": {
            "frame": "InstrumentFrame",
            "frame_rotation_deg": list(INSTRUMENT_FRAME_ROTATION_DEG),
            "dr_axis": "local +z'",
            "cold_finger_port_axis": "local x' through the former side-window stack",
            "cold_finger_port_center_z_cm": PORT_CENTER_Z_CM,
            "future_chimney_world_vertical_placement": "deliberately deferred to assembly geometry",
        },
        "interface": {
            "diameter_cm": PORT_DIAMETER_CM,
            "radius_cm": PORT_RADIUS_CM,
            "matching_sh3_chimney_parameter": "COLD_PORT_RADIUS_CM=0.75",
        },
        "retained": [
            "MXC/100mK/Still/4K/60K cold plates and their validated hole patterns",
            "five DR aluminium shells and bottom caps, rebuilt with a common small port",
            "DR process hardware, capillaries, thermal structures, top services, and support cage",
            "45 degree InstrumentFrame tilt from pinned SG3B",
        ],
        "removed": [
            "all TES pixels, TES containers, silicon substrates, local copper support/cold-finger assembly, and detector map",
            "near-TES Al/Bi shielding, readout/SQUID, and SG3B cable-bundle proxy",
            "all old window foils/filters and 3.796 cm square side-window cuts",
            "passive W bottom plate and W multihole collimator",
            "BGO, Kapton active-shield wrap, BGO mechanical enclosure, outer plastic scintillator, and outer BPE",
            "SH3 chimney placement and connecting cold finger",
        ],
        "shells": [asdict(shell) for shell in SHELLS],
        "outputs": {path.name: file_record(path) for path in outputs},
        "static_validation": file_record(STATIC),
    }
    atomic_json(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "manifest": str(MANIFEST),
                "static": validation["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
