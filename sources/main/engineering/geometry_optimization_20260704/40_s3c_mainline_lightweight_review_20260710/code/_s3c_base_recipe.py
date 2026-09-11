#!/usr/bin/env python3
"""Build S3 from S2b by replacing local CsI veto pieces with a full shell.

S3 keeps the S2b BPE/plastic cryostat shell unchanged.  Only the local CsI
veto package and its local Kapton/Al wrapper are replaced by a cryostat-local
side shell plus end closures, with the existing side-window cutout preserved.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
S2B = ROOT / "engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708"
S2B_GEOM = S2B / "geometry"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

GEOM_DIR = WORK / "geometry"
FIG_DIR = WORK / "figures"
GEO = GEOM_DIR / f"{STEM}.geo"
DET = GEOM_DIR / f"{STEM}.det"
SETUP = GEOM_DIR / f"{STEM}.geo.setup"
INTRO = GEOM_DIR / f"Intro_{STEM}.geo"
MATERIALS = GEOM_DIR / "Materials_DEMO2_DR_v3p5.geo"
OVERLAP_SOURCE = GEOM_DIR / "overlap_check_s3.source"
README = WORK / "README.md"
MANIFEST = WORK / "geoopt_s3_csi_barrel_manifest.json"
FIG_PNG = FIG_DIR / "geoopt_s3_csi_barrel_2d_detail.png"
FIG_SVG = FIG_DIR / "geoopt_s3_csi_barrel_2d_detail.svg"

PATCH_STATUS = "DRAFT_S3_CSI_BARREL_NOT_TRANSPORT_VALIDATED"

# Keep S2b source normalization choice.
SOURCE_CENTER_CM = (5.0, 0.0, 9.0)
SOURCE_RADIUS_CM = 60.0

# BPE/plastic S2b reference dimensions, for documentation and plotting only.
BPE_RIN_CM = 27.0
BPE_ROUT_CM = 29.0
BPE_ZMIN_CM = -26.5
BPE_ZMAX_CM = 48.0
PLASTIC_RIN_CM = 29.0
PLASTIC_ROUT_CM = 30.0
PLASTIC_ZMIN_CM = -27.5
PLASTIC_ZMAX_CM = 49.0

# Existing local CsI side thickness is 4 cm: r=21.2..25.2.
# S3 is kept inside the S2b BPE side-shell span so BPE/plastic remain unchanged.
S3_ZMIN_CM = -24.5
S3_ZMAX_CM = 46.0
CSI_THICKNESS_CM = 4.0
CSI_RIN_CM = 21.2
CSI_ROUT_CM = 25.2
CSI_DENSITY_G_CM3 = 4.51
TOP_SERVICE_OPENING_R_CM = 20.9

# Existing wrapper thicknesses are retained.
KAPTON_RIN_CM = 25.37
KAPTON_ROUT_CM = 25.40
KAPTON_DENSITY_G_CM3 = 1.42
AL_RIN_CM = 25.50
AL_ROUT_CM = 26.30
AL_DENSITY_G_CM3 = 2.70

# Axial wrapper packing mirrors the existing radial gaps around local CsI:
# CsI -> 0.17 cm gap -> Kapton -> 0.10 cm gap -> Al.
CSI_TO_KAPTON_GAP_CM = KAPTON_RIN_CM - CSI_ROUT_CM
KAPTON_TO_AL_GAP_CM = AL_RIN_CM - KAPTON_ROUT_CM
AL_THICKNESS_CM = AL_ROUT_CM - AL_RIN_CM
KAPTON_THICKNESS_CM = KAPTON_ROUT_CM - KAPTON_RIN_CM

BOTTOM_AL_ZMIN_CM = S3_ZMIN_CM
BOTTOM_AL_ZMAX_CM = BOTTOM_AL_ZMIN_CM + AL_THICKNESS_CM
BOTTOM_KAPTON_ZMIN_CM = BOTTOM_AL_ZMAX_CM + KAPTON_TO_AL_GAP_CM
BOTTOM_KAPTON_ZMAX_CM = BOTTOM_KAPTON_ZMIN_CM + KAPTON_THICKNESS_CM
BOTTOM_CSI_ZMIN_CM = BOTTOM_KAPTON_ZMAX_CM + CSI_TO_KAPTON_GAP_CM
BOTTOM_CSI_ZMAX_CM = BOTTOM_CSI_ZMIN_CM + CSI_THICKNESS_CM

TOP_AL_ZMAX_CM = S3_ZMAX_CM
TOP_AL_ZMIN_CM = TOP_AL_ZMAX_CM - AL_THICKNESS_CM
TOP_KAPTON_ZMAX_CM = TOP_AL_ZMIN_CM - KAPTON_TO_AL_GAP_CM
TOP_KAPTON_ZMIN_CM = TOP_KAPTON_ZMAX_CM - KAPTON_THICKNESS_CM
TOP_CSI_ZMAX_CM = TOP_KAPTON_ZMIN_CM - CSI_TO_KAPTON_GAP_CM
TOP_CSI_ZMIN_CM = TOP_CSI_ZMAX_CM - CSI_THICKNESS_CM

CSI_SIDE_ZMIN_CM = BOTTOM_CSI_ZMAX_CM
CSI_SIDE_ZMAX_CM = TOP_CSI_ZMIN_CM
KAPTON_SIDE_ZMIN_CM = BOTTOM_KAPTON_ZMAX_CM
KAPTON_SIDE_ZMAX_CM = TOP_KAPTON_ZMIN_CM
AL_SIDE_ZMIN_CM = BOTTOM_AL_ZMAX_CM
AL_SIDE_ZMAX_CM = TOP_AL_ZMIN_CM

# Preserve the existing side-window aperture: y/z half-widths 1.898 cm, centered
# at instrument-local x=-r_out/2 and z=-5.2 cm.
WINDOW_HALF_Y_CM = 1.898
WINDOW_HALF_Z_CM = 1.898
WINDOW_CENTER_Z_CM = -5.2

NF2_RELIEF_HALF_CM = (2.4, 2.4, 32.0)
NF2_ROD_CENTERS_CM = [
    (23.2447686, 21.0, 35.2655838),
    (-2.47487373, 42.0, 9.54594155),
    (-28.194516, 21.0, -16.1737008),
    (-28.194516, -21.0, -16.1737008),
    (-2.47487373, -42.0, 9.54594155),
    (23.2447686, -21.0, 35.2655838),
]

PUMP_LINE_RELIEF_CENTER_CM = (21.4, 0.0, 24.7)
PUMP_LINE_RELIEF_HALF_CM = (0.75, 0.75, 13.25)

FILES_TO_COPY = [
    f"{STEM}.geo",
    f"{STEM}.det",
    f"{STEM}.geo.setup",
    f"Intro_{STEM}.geo",
    "Materials_DEMO2_DR_v3p5.geo",
    "overlap_check.source",
]

OLD_CSI_VOLUMES = [
    "CsI_Side_Segment_00",
    "CsI_Side_Segment_01",
    "CsI_Side_Segment_02",
    "CsI_Side_Segment_03_below_side_port",
    "CsI_Side_Segment_03_above_side_port",
    "CsI_Side_Segment_04_below_side_port",
    "CsI_Side_Segment_04_above_side_port",
    "CsI_Side_Segment_05",
    "CsI_Side_Segment_06",
    "CsI_Side_Segment_07",
    "CsI_Bottom_Quadrant_00",
    "CsI_Bottom_Quadrant_01",
    "CsI_Bottom_Quadrant_02",
    "CsI_Bottom_Quadrant_03",
    "CsI_TopAnnulus_Segment_00",
    "CsI_TopAnnulus_Segment_01",
    "CsI_TopAnnulus_Segment_02",
    "CsI_TopAnnulus_Segment_03",
    "CsI_TopAnnulus_Segment_04",
    "CsI_TopAnnulus_Segment_05",
    "CsI_TopAnnulus_Segment_06",
    "CsI_TopAnnulus_Segment_07",
    "CsI_Side_Segment_03_rectcut_window_band",
    "CsI_Side_Segment_04_rectcut_window_band",
]

OLD_WRAPPER_VOLUMES = [
    "ActiveShield_Flex_Kapton_detector_bay_below_side_port",
    "ActiveShield_Flex_Kapton_detector_bay_above_side_port",
    "ActiveShield_Flex_Kapton_detector_bay_rectcut_window_band",
    "Outer_Al_Mechanical_Shell_detector_bay_bottom_cap",
    "Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port",
    "Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port",
    "Outer_Al_Mechanical_Shell_detector_bay_side_wall_rectcut_window_band",
    "Outer_Al_Mechanical_Shell_detector_bay_top_annulus",
]

REMOVED_VOLUMES = OLD_CSI_VOLUMES + OLD_WRAPPER_VOLUMES


@dataclass(frozen=True)
class S3Volume:
    name: str
    material: str
    rin: float
    rout: float
    zmin: float
    zmax: float
    density: float
    role: str
    detector: bool
    trigger_threshold: float
    shape_kind: str
    nf2_relief: bool = False
    pump_line_relief: bool = False

    @property
    def zcenter(self) -> float:
        return 0.5 * (self.zmin + self.zmax)

    @property
    def half_height(self) -> float:
        return 0.5 * (self.zmax - self.zmin)

    @property
    def volume_cm3(self) -> float:
        return math.pi * (self.rout * self.rout - self.rin * self.rin) * (self.zmax - self.zmin)

    @property
    def mass_kg(self) -> float:
        return self.volume_cm3 * self.density / 1000.0


def fmt(value: float) -> str:
    if abs(value) < 5.0e-10:
        value = 0.0
    return f"{value:.9g}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def s3_volumes() -> list[S3Volume]:
    return [
        S3Volume(
            name="CsI_S3_FullWrap_SideShell_WindowCut_40mm",
            material="CsI",
            rin=CSI_RIN_CM,
            rout=CSI_ROUT_CM,
            zmin=CSI_SIDE_ZMIN_CM,
            zmax=CSI_SIDE_ZMAX_CM,
            density=CSI_DENSITY_G_CM3,
            role="4 cm CsI active side shell replacing the local side segments; side-window cut retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="side_window",
            nf2_relief=True,
            pump_line_relief=True,
        ),
        S3Volume(
            name="CsI_S3_FullWrap_BottomCap_40mm",
            material="CsI",
            rin=0.0,
            rout=CSI_ROUT_CM,
            zmin=BOTTOM_CSI_ZMIN_CM,
            zmax=BOTTOM_CSI_ZMAX_CM,
            density=CSI_DENSITY_G_CM3,
            role="4 cm CsI active bottom cap closing the S3 inner veto shell inside the unchanged BPE envelope",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        S3Volume(
            name="CsI_S3_FullWrap_TopAnnulus_40mm",
            material="CsI",
            rin=TOP_SERVICE_OPENING_R_CM,
            rout=CSI_ROUT_CM,
            zmin=TOP_CSI_ZMIN_CM,
            zmax=TOP_CSI_ZMAX_CM,
            density=CSI_DENSITY_G_CM3,
            role="4 cm CsI active top annulus closing the S3 veto shell while preserving the top service opening",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        S3Volume(
            name="ActiveShield_S3_CsI_Kapton_SideWrap_WindowCut_0p3mm",
            material="Kapton",
            rin=KAPTON_RIN_CM,
            rout=KAPTON_ROUT_CM,
            zmin=KAPTON_SIDE_ZMIN_CM,
            zmax=KAPTON_SIDE_ZMAX_CM,
            density=KAPTON_DENSITY_G_CM3,
            role="thin Kapton side wrapper following the new CsI shell; side-window cut retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        S3Volume(
            name="ActiveShield_S3_CsI_Kapton_BottomCap_0p3mm",
            material="Kapton",
            rin=0.0,
            rout=KAPTON_ROUT_CM,
            zmin=BOTTOM_KAPTON_ZMIN_CM,
            zmax=BOTTOM_KAPTON_ZMAX_CM,
            density=KAPTON_DENSITY_G_CM3,
            role="thin Kapton bottom wrapper between the S3 CsI bottom cap and outer Al shell",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        S3Volume(
            name="ActiveShield_S3_CsI_Kapton_TopAnnulus_0p3mm",
            material="Kapton",
            rin=TOP_SERVICE_OPENING_R_CM,
            rout=KAPTON_ROUT_CM,
            zmin=TOP_KAPTON_ZMIN_CM,
            zmax=TOP_KAPTON_ZMAX_CM,
            density=KAPTON_DENSITY_G_CM3,
            role="thin Kapton top annulus wrapper preserving the top service opening",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        S3Volume(
            name="Outer_Al_S3_CsI_Mechanical_SideShell_WindowCut_8mm",
            material="Aluminium",
            rin=AL_RIN_CM,
            rout=AL_ROUT_CM,
            zmin=AL_SIDE_ZMIN_CM,
            zmax=AL_SIDE_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role="0.8 cm Al mechanical side shell following the new CsI shell; side-window cut retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        S3Volume(
            name="Outer_Al_S3_CsI_Mechanical_BottomCap_8mm",
            material="Aluminium",
            rin=0.0,
            rout=AL_ROUT_CM,
            zmin=BOTTOM_AL_ZMIN_CM,
            zmax=BOTTOM_AL_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role="0.8 cm Al mechanical bottom cap for the S3 CsI shell",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        S3Volume(
            name="Outer_Al_S3_CsI_Mechanical_TopAnnulus_8mm",
            material="Aluminium",
            rin=TOP_SERVICE_OPENING_R_CM,
            rout=AL_ROUT_CM,
            zmin=TOP_AL_ZMIN_CM,
            zmax=TOP_AL_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role="0.8 cm Al mechanical top annulus preserving the top service opening",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def copy_geometry_inputs() -> None:
    GEOM_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES_TO_COPY:
        src = S2B_GEOM / filename
        dst = GEOM_DIR / filename
        if not src.exists():
            raise RuntimeError(f"missing S2b geometry input: {src}")
        shutil.copy2(src, dst)


def remove_volume_blocks(text: str, names: list[str]) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name in names:
        escaped = re.escape(name)
        # Remove the concrete volume placement block.  Shape helpers can remain
        # unused; removing them is not necessary and risks touching unrelated
        # side-window helper shapes with similar names.
        pattern = re.compile(
            rf"(?:^// Volume {escaped}[^\n]*\n)?^Volume {escaped}\n.*?^{escaped}\.Mother [^\n]+\n+",
            re.MULTILINE | re.DOTALL,
        )
        text, n = pattern.subn("", text)
        counts[name] = n
    return text, counts


def remove_detector_blocks(text: str, volume_names: list[str]) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name in volume_names:
        sd = re.escape(f"{name}_SD")
        pattern = re.compile(rf"^Scintillator {sd}\n.*?(?=\n\s*\n|^Scintillator |\Z)", re.MULTILINE | re.DOTALL)
        text, n = pattern.subn("", text)
        counts[name] = n
    return text, counts


def window_cut_shape_defs(vol: S3Volume) -> tuple[list[str], str]:
    full = f"{vol.name}_FullShellShape"
    cut = f"{vol.name}_RectWindowCutShape"
    orient = f"{vol.name}_RectWindowCutOrientation"
    sub = f"{vol.name}_RectWindowSubtractionShape"
    half_x = vol.rout / 2.0 + 1.0e-4
    center_x = -vol.rout / 2.0
    rel_z = WINDOW_CENTER_Z_CM - vol.zcenter
    lines = [
        f"Shape PCON {full}",
        (
            f"{full}.Parameters 0 360 2 "
            f"{fmt(-vol.half_height)} {fmt(vol.rin)} {fmt(vol.rout)} "
            f"{fmt(vol.half_height)} {fmt(vol.rin)} {fmt(vol.rout)}"
        ),
        f"Shape BRIK {cut}",
        f"{cut}.Parameters {fmt(half_x)} {fmt(WINDOW_HALF_Y_CM)} {fmt(WINDOW_HALF_Z_CM)}",
        f"Orientation {orient}",
        f"{orient}.Position {fmt(center_x)} 0 {fmt(rel_z)}",
        f"Shape Subtraction {sub}",
        f"{sub}.Parameters {full} {cut} {orient}",
    ]
    return lines, sub


def relief_shape_defs(vol: S3Volume, base_shape: str) -> tuple[list[str], str]:
    lines: list[str] = []
    current = base_shape

    if vol.pump_line_relief:
        cut = f"{vol.name}_PumpLineReliefShape"
        orient = f"{vol.name}_PumpLineReliefOrientation"
        sub = f"{vol.name}_PumpLineReliefSubtractionShape"
        rel_z = PUMP_LINE_RELIEF_CENTER_CM[2] - vol.zcenter
        lines.extend(
            [
                f"Shape BRIK {cut}",
                (
                    f"{cut}.Parameters {fmt(PUMP_LINE_RELIEF_HALF_CM[0])} "
                    f"{fmt(PUMP_LINE_RELIEF_HALF_CM[1])} {fmt(PUMP_LINE_RELIEF_HALF_CM[2])}"
                ),
                f"Orientation {orient}",
                f"{orient}.Position {fmt(PUMP_LINE_RELIEF_CENTER_CM[0])} {fmt(PUMP_LINE_RELIEF_CENTER_CM[1])} {fmt(rel_z)}",
                f"Shape Subtraction {sub}",
                f"{sub}.Parameters {current} {cut} {orient}",
            ]
        )
        current = sub

    if vol.nf2_relief:
        for idx, (x, y, z) in enumerate(NF2_ROD_CENTERS_CM, start=1):
            cut = f"{vol.name}_NF2_Rod{idx:02d}_ReliefShape"
            orient = f"{vol.name}_NF2_Rod{idx:02d}_ReliefOrientation"
            sub = f"{vol.name}_NF2_ReliefStep{idx:02d}Shape"
            rel_z = z - vol.zcenter
            lines.extend(
                [
                    f"Shape BRIK {cut}",
                    (
                        f"{cut}.Parameters {fmt(NF2_RELIEF_HALF_CM[0])} "
                        f"{fmt(NF2_RELIEF_HALF_CM[1])} {fmt(NF2_RELIEF_HALF_CM[2])}"
                    ),
                    f"Orientation {orient}",
                    f"{orient}.Position {fmt(x)} {fmt(y)} {fmt(rel_z)}",
                    f"{orient}.Rotation 0 -45 0",
                    f"Shape Subtraction {sub}",
                    f"{sub}.Parameters {current} {cut} {orient}",
                ]
            )
            current = sub

    return lines, current


def shape_defs(vol: S3Volume) -> tuple[list[str], str]:
    if vol.shape_kind == "side_window":
        lines, shape = window_cut_shape_defs(vol)
    elif vol.shape_kind == "pcon":
        shape = f"{vol.name}_BasePconShape"
        lines = [
            f"Shape PCON {shape}",
            (
                f"{shape}.Parameters 0 360 2 "
                f"{fmt(-vol.half_height)} {fmt(vol.rin)} {fmt(vol.rout)} "
                f"{fmt(vol.half_height)} {fmt(vol.rin)} {fmt(vol.rout)}"
            ),
        ]
    else:
        raise RuntimeError(f"unknown S3 shape kind for {vol.name}: {vol.shape_kind}")
    relief_lines, final_shape = relief_shape_defs(vol, shape)
    lines.extend(relief_lines)
    return lines, final_shape


def append_s3_geo(volumes: list[S3Volume]) -> None:
    text = GEO.read_text(encoding="utf-8")
    text, remove_counts = remove_volume_blocks(text, REMOVED_VOLUMES)
    if "BEGIN GEOOPT_S3_CSI_BARREL_PATCH" in text:
        raise RuntimeError("S3 patch already present")

    lines = [
        "",
        "// BEGIN GEOOPT_S3_CSI_BARREL_PATCH",
        f"// Status: {PATCH_STATUS}",
        "// Based on S2b.  BPE/plastic S2b volumes are unchanged.",
        "// Local CsI pieces and their local Kapton/Al wrapper volumes were removed from this S3 copy.",
        "// Replacement CsI package is an InstrumentFrame-local side shell plus end closures.",
        "// The replacement wrapper package follows the same topology; the negative-x side-window cut is retained on side shells.",
    ]
    for vol in volumes:
        shape_lines, final_shape = shape_defs(vol)
        lines.extend(shape_lines)
        lines.extend(
            [
                f"// Volume {vol.name}; kind={vol.shape_kind}; role={vol.role}; volume_cm3={fmt(vol.volume_cm3)}; mass_kg={fmt(vol.mass_kg)}",
                f"Volume {vol.name}",
                f"{vol.name}.Material {vol.material}",
                f"{vol.name}.Visibility 1",
                f"{vol.name}.Shape {final_shape}",
                f"{vol.name}.Position 0 0 {fmt(vol.zcenter)}",
                f"{vol.name}.Mother InstrumentFrame",
                "",
            ]
        )
    lines.append("// END GEOOPT_S3_CSI_BARREL_PATCH")
    GEO.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")

    return_counts = {
        "removed_geo_volume_blocks": remove_counts,
    }
    (WORK / "s3_remove_counts.json").write_text(json.dumps(return_counts, indent=2, sort_keys=True), encoding="utf-8")


def append_s3_det(volumes: list[S3Volume]) -> None:
    text = DET.read_text(encoding="utf-8")
    text, remove_counts = remove_detector_blocks(text, REMOVED_VOLUMES)
    if "BEGIN GEOOPT_S3_CSI_BARREL_DET" in text:
        raise RuntimeError("S3 detector patch already present")
    lines = [
        "",
        "// BEGIN GEOOPT_S3_CSI_BARREL_DET",
        "// Scorers for replacement CsI full-wrap package and local wrapper volumes.",
    ]
    for vol in volumes:
        if not vol.detector:
            continue
        sd = f"{vol.name}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {vol.name}",
                f"{sd}.DetectorVolume {vol.name}",
                f"{sd}.TriggerThreshold {fmt(vol.trigger_threshold)}",
            ]
        )
        if vol.trigger_threshold >= 1.0:
            lines.append(f"{sd}.NoiseThresholdEqualsTriggerThreshold true")
        lines.extend(
            [
                f"{sd}.EnergyResolution Gauss {fmt(vol.trigger_threshold)} {fmt(vol.trigger_threshold)} 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    lines.append("// END GEOOPT_S3_CSI_BARREL_DET")
    DET.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    (WORK / "s3_det_remove_counts.json").write_text(
        json.dumps({"removed_detector_blocks": remove_counts}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_overlap_source() -> None:
    OVERLAP_SOURCE.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {SETUP}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                "Minimum.FileName            /tmp/DelMe_geoopt_s3_csi_barrel_overlap",
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


def write_fig(volumes: list[S3Volume]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 5.4))
    ax.add_patch(Rectangle((BPE_RIN_CM, BPE_ZMIN_CM), BPE_ROUT_CM - BPE_RIN_CM, BPE_ZMAX_CM - BPE_ZMIN_CM,
                           facecolor="#c8f22e", alpha=0.22, edgecolor="#6f8c00", label="S2b BPE side"))
    ax.add_patch(Rectangle((PLASTIC_RIN_CM, PLASTIC_ZMIN_CM), PLASTIC_ROUT_CM - PLASTIC_RIN_CM,
                           PLASTIC_ZMAX_CM - PLASTIC_ZMIN_CM,
                           facecolor="#28b8d5", alpha=0.22, edgecolor="#00728a", label="S2b plastic side"))
    colors = {
        "CsI": ("#d8b11e", "#7b6400"),
        "Kapton": ("#a05a2c", "#663000"),
        "Aluminium": ("#9fa7b3", "#4a5568"),
    }
    for vol in volumes:
        face, edge = colors.get(vol.material, ("#cccccc", "#555555"))
        ax.add_patch(
            Rectangle(
                (vol.rin, vol.zmin),
                vol.rout - vol.rin,
                vol.zmax - vol.zmin,
                facecolor=face,
                alpha=0.34,
                edgecolor=edge,
                linewidth=1.0,
                label=vol.name.replace("_", " "),
            )
        )
    ax.add_patch(Rectangle((0, WINDOW_CENTER_Z_CM - WINDOW_HALF_Z_CM), CSI_ROUT_CM, 2 * WINDOW_HALF_Z_CM,
                           facecolor="white", edgecolor="#333333", hatch="//", alpha=0.7,
                           label="side-window cut zone"))
    ax.set_xlim(0, 31.5)
    ax.set_ylim(-30, 51)
    ax.set_xlabel("Instrument-frame radius r (cm)")
    ax.set_ylabel("Instrument-frame z (cm)")
    ax.set_title("S3 CsI full-wrap shell inside unchanged S2b BPE/plastic")
    ax.grid(True, linewidth=0.3, alpha=0.45)
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG_PNG, dpi=180)
    fig.savefig(FIG_SVG)
    plt.close(fig)


def write_readme_and_manifest(volumes: list[S3Volume]) -> None:
    old_csi_mass = (
        math.pi * (25.2**2 - 21.2**2) * 16.4
        + math.pi * (25.2**2 - 20.8**2) * 3.0
        + math.pi * 18.0**2 * 6.0
    ) * CSI_DENSITY_G_CM3 / 1000.0
    manifest = {
        "status": PATCH_STATUS,
        "base_geometry": rel(S2B_GEOM / f"{STEM}.geo.setup"),
        "generated_geometry": rel(SETUP),
        "scope": "S2b-derived geometry draft; only local CsI veto package and local CsI wrapper volumes are replaced.",
        "unchanged": [
            "S2b BPE cryostat shell",
            "S2b plastic scintillator cryostat shell",
            "source sphere center and radius",
            "side-window signal aperture location and half-widths",
        ],
        "removed_local_volumes": REMOVED_VOLUMES,
        "new_volumes": [
            {
                "name": vol.name,
                "material": vol.material,
                "shape_kind": vol.shape_kind,
                "r_inner_cm": vol.rin,
                "r_outer_cm": vol.rout,
                "z_min_cm": vol.zmin,
                "z_max_cm": vol.zmax,
                "mass_kg": vol.mass_kg,
                "detector_scorer": vol.detector,
                "trigger_threshold_keV": vol.trigger_threshold,
                "nf2_support_relief": vol.nf2_relief,
                "pump_line_relief": vol.pump_line_relief,
                "role": vol.role,
            }
            for vol in volumes
        ],
        "mass_summary_kg": {
            "approx_old_local_csi_reference": old_csi_mass,
            "new_csi_full_wrap": sum(v.mass_kg for v in volumes if v.material == "CsI"),
            "new_kapton_wrapper": sum(v.mass_kg for v in volumes if v.material == "Kapton"),
            "new_al_wrapper": sum(v.mass_kg for v in volumes if v.material == "Aluminium"),
        },
        "s3_envelope_cm": {
            "z_min": S3_ZMIN_CM,
            "z_max": S3_ZMAX_CM,
            "top_service_opening_r_inner": TOP_SERVICE_OPENING_R_CM,
            "note": "S3 package is kept inside the unchanged S2b BPE side-shell z span; top closure is annular to preserve service clearance.",
        },
        "reliefs": {
            "nf2_support_rods": "S2b-style BRIK reliefs are subtracted from every S3 replacement volume.",
            "dr_still_pump_line": "A local slot is subtracted from the CsI side shell for DR_Still_PumpLine_SS_to_300K_top.",
            "mass_entries": "Analytic masses are pre-relief values, matching the convention used by S2b documentation.",
        },
        "side_window_cut": {
            "center_local_z_cm": WINDOW_CENTER_Z_CM,
            "half_y_cm": WINDOW_HALF_Y_CM,
            "half_z_cm": WINDOW_HALF_Z_CM,
            "cut_style": "rectangular negative-x through-window subtraction from each S3 side shell",
        },
        "validation_status": "geometry generated; overlap/cosima transport not yet run by this builder",
        "outputs": {
            "geometry_dir": rel(GEOM_DIR),
            "figure_png": rel(FIG_PNG),
            "figure_svg": rel(FIG_SVG),
            "overlap_source": rel(OVERLAP_SOURCE),
            "geo_remove_counts": rel(WORK / "s3_remove_counts.json"),
            "det_remove_counts": rel(WORK / "s3_det_remove_counts.json"),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    rows = "\n".join(
        f"| `{v.name}` | `{v.material}` | {v.rin:.2f}--{v.rout:.2f} | {v.zmin:.2f}..{v.zmax:.2f} | {v.mass_kg:.3f} | {v.role} |"
        for v in volumes
    )
    README.write_text(
        f"""# Geometry Optimization Draft: S3 CsI Barrel

Status: `{PATCH_STATUS}`

S3 is derived from S2b.  The S2b BPE and plastic cryostat-following shells are
left unchanged.  The local CsI side segments, top annulus, bottom quadrants,
and local CsI Kapton/Al wrapper volumes are removed from this S3 copy and
replaced by a CsI full-wrap package: side shell, bottom cap, and top annulus,
with matching Kapton/Al wrapper pieces.

## Design Interpretation

- Base: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/`.
- New CsI side-shell remains at the existing CsI radial thickness:
  `r={CSI_RIN_CM:.1f}..{CSI_ROUT_CM:.1f} cm` (`{CSI_THICKNESS_CM:.1f} cm`).
- The S3 replacement package is kept inside the unchanged S2b BPE side-shell
  span: `z={S3_ZMIN_CM:.1f}..{S3_ZMAX_CM:.1f} cm`.
- The bottom CsI cap is solid.  The top CsI closure is an annulus with
  inner radius `{TOP_SERVICE_OPENING_R_CM:.1f} cm` to preserve top-service
  clearance inside the unchanged S2b BPE/plastic envelope.
- S2b-style NF2 support-rod reliefs are subtracted from all new S3 volumes.
  A local pump-line relief is also subtracted from the CsI side shell for
  `DR_Still_PumpLine_SS_to_300K_top`.
- Side-window aperture is retained at local `z={WINDOW_CENTER_Z_CM:.1f} cm`,
  with half-widths `y,z={WINDOW_HALF_Y_CM:.3f} cm`.
- No BPE/plastic/source-card/fix5/Mass_model authority file is changed.

## New Volumes

| Volume | Material | r cm | z cm | Mass kg | Role |
|---|---|---:|---:|---:|---|
{rows}

Approximate old local CsI mass reference: `{old_csi_mass:.3f} kg`.
New CsI full-wrap mass: `{sum(v.mass_kg for v in volumes if v.material == "CsI"):.3f} kg`.
Masses above are analytic pre-relief values.

## Generated Files

- Geometry setup: `{rel(SETUP)}`
- Geometry body: `{rel(GEO)}`
- Detector map: `{rel(DET)}`
- Manifest: `{rel(MANIFEST)}`
- 2D detail: `{rel(FIG_PNG)}` / `{rel(FIG_SVG)}`
- Overlap source card: `{rel(OVERLAP_SOURCE)}`
- Removed geometry volume counts: `{rel(WORK / "s3_remove_counts.json")}`
- Removed detector block counts: `{rel(WORK / "s3_det_remove_counts.json")}`

## Boundary

This is a geometry draft only.  It is not a transport result, not a promotion,
and not a background-rate claim.  The next required gates are cosima overlap
load/check, focused signal throughput, atmospheric-511 sidecar replay, prompt
e+/n equal-stat replay, and delayed activation review.
""",
        encoding="utf-8",
    )


def main() -> int:
    volumes = s3_volumes()
    copy_geometry_inputs()
    append_s3_geo(volumes)
    append_s3_det(volumes)
    write_overlap_source()
    write_fig(volumes)
    write_readme_and_manifest(volumes)
    print(
        json.dumps(
            {
                "status": PATCH_STATUS,
                "geometry": rel(SETUP),
                "new_csi_mass_kg": sum(v.mass_kg for v in volumes if v.material == "CsI"),
                "new_volume_count": len(volumes),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
