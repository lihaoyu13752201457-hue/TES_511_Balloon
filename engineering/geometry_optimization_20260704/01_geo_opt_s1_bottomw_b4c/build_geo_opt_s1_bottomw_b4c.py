#!/usr/bin/env python3
"""Build a first-pass geometry-optimization draft from Mass_model_511.

This generator is intentionally scoped:
- copy the Mass_model_511 proxy geometry into this workpackage directory;
- append analytic geometry-patch volumes only to the copied files;
- produce a WRL visualization and 2D detail projections from the generated .geo;
- do not run transport and do not modify any Mass_model_511 authority output.

The patch is a geometry draft for review, not a background-rate authority.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Rectangle


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SOURCE_GEOM_DIR = ROOT / (
    "outputs/geometry/"
    "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_"
    "20260701_megalib_proxy"
)
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

GEOM_DIR = WORK / "geometry"
FIG_DIR = WORK / "figures"
GEO = GEOM_DIR / f"{STEM}.geo"
DET = GEOM_DIR / f"{STEM}.det"
SETUP = GEOM_DIR / f"{STEM}.geo.setup"
INTRO = GEOM_DIR / f"Intro_{STEM}.geo"
MATERIALS = GEOM_DIR / "Materials_DEMO2_DR_v3p5.geo"
OVERLAP_SOURCE = GEOM_DIR / "overlap_check.source"

WRL = FIG_DIR / "geo_opt_s1_bottomw_b4c.wrl"
DETAIL_PNG = FIG_DIR / "geo_opt_s1_bottomw_b4c_2d_detail.png"
DETAIL_SVG = FIG_DIR / "geo_opt_s1_bottomw_b4c_2d_detail.svg"
README = WORK / "README.md"
MANIFEST = WORK / "geo_opt_s1_bottomw_b4c_manifest.json"

EXPORTER = ROOT / "old/reports/user_redesign_cylmag_20260621/export_megalib_geo_to_wrl.py"
R3_METRICS = ROOT / "engineering/background_anatomy_20260704/r3_metrics.json"

FILES_TO_COPY = [
    f"{STEM}.geo",
    f"{STEM}.det",
    f"{STEM}.geo.setup",
    f"Intro_{STEM}.geo",
    "Materials_DEMO2_DR_v3p5.geo",
    "overlap_check.source",
]

PATCH_STATUS = "DRAFT_ANALYTIC_PATCH_NOT_TRANSPORT_VALIDATED"

# User-reviewed patch dimensions.  The layer order is:
# outside -> inside: plastic scintillator skin, borated PE, W bottom baffle,
# then the unmodified Mass_model_511 detector.
PLASTIC_THICKNESS_CM = 0.50
PLASTIC_RIN_CM = 27.40
PLASTIC_ROUT_CM = 27.90
PLASTIC_SIDE_ZMIN_CM = -23.10
PLASTIC_SIDE_ZMAX_CM = 7.20
PLASTIC_BOTTOM_ZMIN_CM = -23.60
PLASTIC_BOTTOM_ZMAX_CM = -23.10
PLASTIC_TOP_ZMIN_CM = 7.20
PLASTIC_TOP_ZMAX_CM = 7.70

BPE_THICKNESS_CM = 1.00
BPE_RIN_CM = 26.40
BPE_ROUT_CM = 27.40
BPE_SIDE_ZMIN_CM = -22.10
BPE_SIDE_ZMAX_CM = 6.20
BPE_BOTTOM_ZMIN_CM = -23.10
BPE_BOTTOM_ZMAX_CM = -22.10
BPE_TOP_ZMIN_CM = 6.20
BPE_TOP_ZMAX_CM = 7.20
BPE_DENSITY_G_CM3 = 0.95

TOP_SERVICE_OPENING_RIN_CM = 20.90

BOTTOM_ROD_RELIEF_X_CM = -19.50
BOTTOM_ROD_RELIEF_Y_CM = 19.80
BOTTOM_ROD_RELIEF_HALF_X_CM = 4.00
BOTTOM_ROD_RELIEF_HALF_Y_CM = 4.00
BOTTOM_ROD_RELIEF_HALF_Z_CM = 0.30
SIDE_ROD_RELIEF_Z_LOCAL_CM = -14.90
SIDE_ROD_RELIEF_HALF_X_CM = 4.00
SIDE_ROD_RELIEF_HALF_Y_CM = 4.00
SIDE_ROD_RELIEF_HALF_Z_CM = 0.75

SIGNAL_WINDOW_X_SIDE = "negative-x"
SIGNAL_WINDOW_Z_CM = -5.20
SIGNAL_WINDOW_CUT_HALF_Y_CM = 2.40
SIGNAL_WINDOW_CUT_HALF_Z_CM = 2.40

W_BAFFLE_ROUT_CM = 6.00
W_BAFFLE_THICKNESS_CM = 0.50
W_BAFFLE_ZMIN_CM = -22.05
W_BAFFLE_ZMAX_CM = -21.55
PLASTIC_DENSITY_G_CM3 = 1.03
W_DENSITY_G_CM3 = 19.3


@dataclass(frozen=True)
class PatchVolume:
    name: str
    material: str
    shape: str
    position: tuple[float, float, float]
    role: str
    volume_cm3: float
    mass_kg: float
    active: bool = False
    shape_defs: tuple[str, ...] = ()


def fmt(value: float) -> str:
    if abs(value) < 5.0e-10:
        value = 0.0
    return f"{value:.9g}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def pcon_line(phi0: float, dphi: float, planes: list[tuple[float, float, float]]) -> str:
    values: list[float] = [phi0, dphi, float(len(planes))]
    for z, rin, rout in planes:
        values.extend([z, rin, rout])
    return "PCON " + " ".join(fmt(value) for value in values)


def pcon_volume(phi0: float, dphi: float, planes: list[tuple[float, float, float]]) -> float:
    frac = abs(dphi) / 360.0
    volume = 0.0
    for idx in range(len(planes) - 1):
        z0, rin0, rout0 = planes[idx]
        z1, rin1, rout1 = planes[idx + 1]
        height = abs(z1 - z0)
        outer = math.pi * height * (rout0 * rout0 + rout0 * rout1 + rout1 * rout1) / 3.0
        inner = math.pi * height * (rin0 * rin0 + rin0 * rin1 + rin1 * rin1) / 3.0
        volume += (outer - inner) * frac
    return volume


def global_pcon_planes(
    z_min: float, z_max: float, r_inner: float, r_outer: float
) -> tuple[list[tuple[float, float, float]], float]:
    z_center = 0.5 * (z_min + z_max)
    z_half = 0.5 * (z_max - z_min)
    return [(-z_half, r_inner, r_outer), (z_half, r_inner, r_outer)], z_center


def solid_cap_volume(z_min: float, z_max: float, r_outer: float) -> float:
    return math.pi * r_outer * r_outer * abs(z_max - z_min)


def bpe_side_window_shape_defs(name: str) -> tuple[str, ...]:
    planes, z_center = global_pcon_planes(BPE_SIDE_ZMIN_CM, BPE_SIDE_ZMAX_CM, BPE_RIN_CM, BPE_ROUT_CM)
    full = f"{name}_FullShellShape"
    cut = f"{name}_SignalWindowCutShape"
    orient = f"{name}_SignalWindowCutOrientation"
    sub = f"{name}_SubtractionShape"
    half_x = 0.5 * BPE_ROUT_CM + 0.001
    return (
        f"Shape PCON {full}",
        f"{full}.Parameters {' '.join(pcon_line(0.0, 360.0, planes).split()[1:])}",
        f"Shape BRIK {cut}",
        f"{cut}.Parameters {fmt(half_x)} {fmt(SIGNAL_WINDOW_CUT_HALF_Y_CM)} {fmt(SIGNAL_WINDOW_CUT_HALF_Z_CM)}",
        f"Orientation {orient}",
        f"{orient}.Position {fmt(-0.5 * BPE_ROUT_CM)} 0 {fmt(SIGNAL_WINDOW_Z_CM - z_center)}",
        f"Shape Subtraction {sub}",
        f"{sub}.Parameters {full} {cut} {orient}",
    )


def plastic_bottom_rod_relief_shape_defs(name: str) -> tuple[str, ...]:
    planes, _ = global_pcon_planes(PLASTIC_BOTTOM_ZMIN_CM, PLASTIC_BOTTOM_ZMAX_CM, 0.0, PLASTIC_ROUT_CM)
    full = f"{name}_FullDiskShape"
    cut_a = f"{name}_NF2Rod03ReliefShape"
    cut_b = f"{name}_NF2Rod04ReliefShape"
    orient_a = f"{name}_NF2Rod03ReliefOrientation"
    orient_b = f"{name}_NF2Rod04ReliefOrientation"
    sub_a = f"{name}_ReliefStep01Shape"
    sub_b = f"{name}_ReliefStep02Shape"
    return (
        f"Shape PCON {full}",
        f"{full}.Parameters {' '.join(pcon_line(0.0, 360.0, planes).split()[1:])}",
        f"Shape BRIK {cut_a}",
        f"{cut_a}.Parameters {fmt(BOTTOM_ROD_RELIEF_HALF_X_CM)} {fmt(BOTTOM_ROD_RELIEF_HALF_Y_CM)} {fmt(BOTTOM_ROD_RELIEF_HALF_Z_CM)}",
        f"Orientation {orient_a}",
        f"{orient_a}.Position {fmt(BOTTOM_ROD_RELIEF_X_CM)} {fmt(BOTTOM_ROD_RELIEF_Y_CM)} 0",
        f"Shape BRIK {cut_b}",
        f"{cut_b}.Parameters {fmt(BOTTOM_ROD_RELIEF_HALF_X_CM)} {fmt(BOTTOM_ROD_RELIEF_HALF_Y_CM)} {fmt(BOTTOM_ROD_RELIEF_HALF_Z_CM)}",
        f"Orientation {orient_b}",
        f"{orient_b}.Position {fmt(BOTTOM_ROD_RELIEF_X_CM)} {fmt(-BOTTOM_ROD_RELIEF_Y_CM)} 0",
        f"Shape Subtraction {sub_a}",
        f"{sub_a}.Parameters {full} {cut_a} {orient_a}",
        f"Shape Subtraction {sub_b}",
        f"{sub_b}.Parameters {sub_a} {cut_b} {orient_b}",
    )


def plastic_side_rod_relief_shape_defs(name: str) -> tuple[str, ...]:
    planes, _ = global_pcon_planes(
        PLASTIC_SIDE_ZMIN_CM, PLASTIC_SIDE_ZMAX_CM, PLASTIC_RIN_CM, PLASTIC_ROUT_CM
    )
    full = f"{name}_FullShellShape"
    cut_a = f"{name}_NF2Rod03ReliefShape"
    cut_b = f"{name}_NF2Rod04ReliefShape"
    orient_a = f"{name}_NF2Rod03ReliefOrientation"
    orient_b = f"{name}_NF2Rod04ReliefOrientation"
    sub_a = f"{name}_ReliefStep01Shape"
    sub_b = f"{name}_ReliefStep02Shape"
    return (
        f"Shape PCON {full}",
        f"{full}.Parameters {' '.join(pcon_line(0.0, 360.0, planes).split()[1:])}",
        f"Shape BRIK {cut_a}",
        f"{cut_a}.Parameters {fmt(SIDE_ROD_RELIEF_HALF_X_CM)} {fmt(SIDE_ROD_RELIEF_HALF_Y_CM)} {fmt(SIDE_ROD_RELIEF_HALF_Z_CM)}",
        f"Orientation {orient_a}",
        f"{orient_a}.Position {fmt(BOTTOM_ROD_RELIEF_X_CM)} {fmt(BOTTOM_ROD_RELIEF_Y_CM)} {fmt(SIDE_ROD_RELIEF_Z_LOCAL_CM)}",
        f"Shape BRIK {cut_b}",
        f"{cut_b}.Parameters {fmt(SIDE_ROD_RELIEF_HALF_X_CM)} {fmt(SIDE_ROD_RELIEF_HALF_Y_CM)} {fmt(SIDE_ROD_RELIEF_HALF_Z_CM)}",
        f"Orientation {orient_b}",
        f"{orient_b}.Position {fmt(BOTTOM_ROD_RELIEF_X_CM)} {fmt(-BOTTOM_ROD_RELIEF_Y_CM)} {fmt(SIDE_ROD_RELIEF_Z_LOCAL_CM)}",
        f"Shape Subtraction {sub_a}",
        f"{sub_a}.Parameters {full} {cut_a} {orient_a}",
        f"Shape Subtraction {sub_b}",
        f"{sub_b}.Parameters {sub_a} {cut_b} {orient_b}",
    )


def wrapped_phi_segments(phi0: float, dphi: float) -> list[tuple[float, float]]:
    start = phi0 % 360.0
    end = start + dphi
    if end <= 360.0:
        return [(start, end)]
    return [(start, 360.0), (0.0, end - 360.0)]


def subtract_phi_exclusion(
    segments: list[tuple[float, float]], cut_min: float, cut_max: float
) -> list[tuple[float, float]]:
    kept: list[tuple[float, float]] = []
    for start, end in segments:
        if end <= cut_min or start >= cut_max:
            kept.append((start, end))
            continue
        if start < cut_min:
            kept.append((start, cut_min))
        if end > cut_max:
            kept.append((cut_max, end))
    return [(start, end) for start, end in kept if end - start > 1.0e-6]


def load_r3_geometry() -> dict[str, float]:
    metrics = json.loads(R3_METRICS.read_text(encoding="utf-8"))
    skin = metrics["l7_skin_geometry"]
    return {
        "phi_start_deg": float(skin["phi_start_deg"]),
        "phi_span_deg": float(skin["phi_span_deg"]),
        "r_inner_cm": float(skin["r_inner_cm"]),
        "r_outer_cm": float(skin["r_outer_cm"]),
        "z_min_cm": float(skin["z_min_cm"]),
        "z_max_cm": float(skin["z_max_cm"]),
        "s1_area_cm2": float(skin["s1_area_cm2"]),
        "s1_mass_kg": float(skin["s1_mass_kg"]),
        "s1_live_loss_fraction": float(skin["s1_live_loss_fraction"]),
        "s1_skin_rate_hz": float(skin["s1_skin_rate_hz"]),
    }


def copy_geometry_inputs() -> None:
    GEOM_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES_TO_COPY:
        src = SOURCE_GEOM_DIR / filename
        dst = GEOM_DIR / filename
        if not src.exists():
            raise RuntimeError(f"missing source geometry file: {src}")
        shutil.copy2(src, dst)


def append_materials() -> None:
    text = MATERIALS.read_text(encoding="utf-8")
    block = """

# BEGIN GEO_OPT_S1_BOTTOMW_B4C_MATERIALS
# Local draft materials for engineering/geometry_optimization_20260704 only.
Material PlasticScintillator
PlasticScintillator.Density 1.03
PlasticScintillator.Component C 8
PlasticScintillator.Component H 8

Material BoratedPolyethylene5wtB
BoratedPolyethylene5wtB.Density 0.95
# Approximate 5 wt% natural boron in polyethylene: C:H:B ~= 1000:2000:68.
BoratedPolyethylene5wtB.Component C 1000
BoratedPolyethylene5wtB.Component H 2000
BoratedPolyethylene5wtB.Component B 68
# END GEO_OPT_S1_BOTTOMW_B4C_MATERIALS
"""
    if "BEGIN GEO_OPT_S1_BOTTOMW_B4C_MATERIALS" not in text:
        MATERIALS.write_text(text.rstrip() + block, encoding="utf-8")


def build_patch_volumes(skin: dict[str, float]) -> list[PatchVolume]:
    del skin  # R3 metrics remain provenance only; this user revision no longer instantiates R3 sectors.

    volumes: list[PatchVolume] = []

    plastic_side_planes, plastic_side_z = global_pcon_planes(
        PLASTIC_SIDE_ZMIN_CM, PLASTIC_SIDE_ZMAX_CM, PLASTIC_RIN_CM, PLASTIC_ROUT_CM
    )
    plastic_bottom_planes, plastic_bottom_z = global_pcon_planes(
        PLASTIC_BOTTOM_ZMIN_CM, PLASTIC_BOTTOM_ZMAX_CM, 0.0, PLASTIC_ROUT_CM
    )
    plastic_top_planes, plastic_top_z = global_pcon_planes(
        PLASTIC_TOP_ZMIN_CM, PLASTIC_TOP_ZMAX_CM, TOP_SERVICE_OPENING_RIN_CM, PLASTIC_ROUT_CM
    )
    bpe_side_planes, bpe_side_z = global_pcon_planes(
        BPE_SIDE_ZMIN_CM, BPE_SIDE_ZMAX_CM, BPE_RIN_CM, BPE_ROUT_CM
    )
    bpe_bottom_planes, bpe_bottom_z = global_pcon_planes(
        BPE_BOTTOM_ZMIN_CM, BPE_BOTTOM_ZMAX_CM, 0.0, BPE_ROUT_CM
    )
    bpe_top_planes, bpe_top_z = global_pcon_planes(
        BPE_TOP_ZMIN_CM, BPE_TOP_ZMAX_CM, TOP_SERVICE_OPENING_RIN_CM, BPE_ROUT_CM
    )
    w_planes, w_z = global_pcon_planes(W_BAFFLE_ZMIN_CM, W_BAFFLE_ZMAX_CM, 0.0, W_BAFFLE_ROUT_CM)

    plastic_roles = {
        "side": (
            "Full-azimuth active plastic scintillator outer side skin; covers the side-window azimuth as a charged-particle "
            "sentinel instead of using the earlier low-statistics segmented S1 sector proxy"
        ),
        "bottom": "Active plastic scintillator bottom skin closing the outer charged-particle veto envelope",
        "top": "Active plastic scintillator top annulus skin; preserves the existing central service/support opening",
    }
    for name, planes, z, role, shape, shape_defs in [
        (
            "GeoOpt_S1_PlasticFullWrap_SideShell_5mm",
            plastic_side_planes,
            plastic_side_z,
            plastic_roles["side"] + "; includes two local NF2 outer-support rod relief cutouts near the lower edge",
            "GeoOpt_S1_PlasticFullWrap_SideShell_5mm_ReliefStep02Shape",
            plastic_side_rod_relief_shape_defs("GeoOpt_S1_PlasticFullWrap_SideShell_5mm"),
        ),
        (
            "GeoOpt_S1_PlasticFullWrap_BottomCap_5mm",
            plastic_bottom_planes,
            plastic_bottom_z,
            plastic_roles["bottom"] + "; includes two local NF2 outer-support rod relief cutouts",
            "GeoOpt_S1_PlasticFullWrap_BottomCap_5mm_ReliefStep02Shape",
            plastic_bottom_rod_relief_shape_defs("GeoOpt_S1_PlasticFullWrap_BottomCap_5mm"),
        ),
        (
            "GeoOpt_S1_PlasticFullWrap_TopCap_5mm",
            plastic_top_planes,
            plastic_top_z,
            plastic_roles["top"],
            pcon_line(0.0, 360.0, plastic_top_planes),
            (),
        ),
    ]:
        vol = pcon_volume(0.0, 360.0, planes)
        volumes.append(
            PatchVolume(
                name=name,
                material="PlasticScintillator",
                shape=shape,
                position=(0.0, 0.0, z),
                role=role,
                volume_cm3=vol,
                mass_kg=vol * PLASTIC_DENSITY_G_CM3 / 1000.0,
                active=True,
                shape_defs=shape_defs,
            )
        )

    bpe_side_name = "GeoOpt_BPE5_FullWrap_SideShell_SignalWindowCut_10mm"
    bpe_side_vol = pcon_volume(0.0, 360.0, bpe_side_planes)
    volumes.append(
        PatchVolume(
            name=bpe_side_name,
            material="BoratedPolyethylene5wtB",
            shape=f"{bpe_side_name}_SubtractionShape",
            position=(0.0, 0.0, bpe_side_z),
            role=(
                "1 cm borated polyethylene inner side shell with a rectangular negative-x signal-window cutout; "
                "kept inside the plastic scintillator skin so the BPE does not become the first passive charged-particle stop"
            ),
            volume_cm3=bpe_side_vol,
            mass_kg=bpe_side_vol * BPE_DENSITY_G_CM3 / 1000.0,
            shape_defs=bpe_side_window_shape_defs(bpe_side_name),
        )
    )

    for name, planes, z, role in [
        (
            "GeoOpt_BPE5_FullWrap_BottomCap_10mm",
            bpe_bottom_planes,
            bpe_bottom_z,
            "1 cm borated polyethylene bottom cap inside the plastic skin and outside the W bottom baffle",
        ),
        (
            "GeoOpt_BPE5_FullWrap_TopCap_10mm",
            bpe_top_planes,
            bpe_top_z,
            "1 cm borated polyethylene top annulus inside the plastic skin; preserves the existing central service/support opening",
        ),
    ]:
        vol = pcon_volume(0.0, 360.0, planes)
        volumes.append(
            PatchVolume(
                name=name,
                material="BoratedPolyethylene5wtB",
                shape=pcon_line(0.0, 360.0, planes),
                position=(0.0, 0.0, z),
                role=role,
                volume_cm3=vol,
                mass_kg=vol * BPE_DENSITY_G_CM3 / 1000.0,
            )
        )

    w_vol = pcon_volume(0.0, 360.0, w_planes)
    volumes.append(
        PatchVolume(
            name="GeoOpt_W_BottomBaffle_5mm_R60",
            material="W",
            shape=pcon_line(0.0, 360.0, w_planes),
            position=(0.0, 0.0, w_z),
            role=(
                "5 mm local tungsten bottom gamma baffle retained in the S1 geometry; "
                "placed inward of the borated-polyethylene bottom layer and just outside the original Mass_model_511 bottom shell. "
                "It is not treated as the primary ATM511 sidecar mitigation path."
            ),
            volume_cm3=w_vol,
            mass_kg=w_vol * W_DENSITY_G_CM3 / 1000.0,
        )
    )
    return volumes


def append_geo_patch(volumes: list[PatchVolume]) -> None:
    text = GEO.read_text(encoding="utf-8")
    if "BEGIN GEO_OPT_S1_BOTTOMW_B4C_PATCH" in text:
        return
    lines = [
        "",
        "// BEGIN GEO_OPT_S1_BOTTOMW_B4C_PATCH",
        f"// Status: {PATCH_STATUS}",
        "// Source basis: Mass_model_511 geometry copied into this workpackage directory.",
        "// Added components are analytic draft geometry only; no transport validation is implied.",
    ]
    for vol in volumes:
        if vol.shape_defs:
            lines.extend(vol.shape_defs)
        lines.extend(
            [
                f"// Volume {vol.name}; role={vol.role}; volume_cm3={fmt(vol.volume_cm3)}; mass_kg={fmt(vol.mass_kg)}",
                f"Volume {vol.name}",
                f"{vol.name}.Material {vol.material}",
                f"{vol.name}.Visibility 1",
                f"{vol.name}.Shape {vol.shape}",
                f"{vol.name}.Position {' '.join(fmt(value) for value in vol.position)}",
                f"{vol.name}.Mother InstrumentFrame",
                "",
            ]
        )
    lines.append("// END GEO_OPT_S1_BOTTOMW_B4C_PATCH")
    GEO.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def append_det_patch(volumes: list[PatchVolume]) -> None:
    text = DET.read_text(encoding="utf-8")
    if "BEGIN GEO_OPT_S1_BOTTOMW_B4C_DET" in text:
        return
    lines = [
        "",
        "// BEGIN GEO_OPT_S1_BOTTOMW_B4C_DET",
        "// Plastic skin draft detector entries.  Timing/threshold authority remains Step05 overlay validation.",
    ]
    for vol in volumes:
        if not vol.active:
            continue
        sd = f"{vol.name}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {vol.name}",
                f"{sd}.DetectorVolume {vol.name}",
                f"{sd}.TriggerThreshold 0.001",
                f"{sd}.EnergyResolution Gauss 0.001 0.001 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    lines.append("// END GEO_OPT_S1_BOTTOMW_B4C_DET")
    DET.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def write_overlap_source() -> None:
    OVERLAP_SOURCE.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {SETUP}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                "Minimum.FileName            /tmp/DelMe_geo_opt_s1_bottomw_b4c_overlap",
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
    spec = importlib.util.spec_from_file_location("geo_opt_wrl_exporter", EXPORTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXPORTER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEOM_DIR = GEOM_DIR
    module.INTRO = INTRO
    module.GEO = GEO
    module.OUT = WRL
    module.COLORS["PlasticScintillator"] = (0.10, 0.75, 0.95, 0.40)
    module.COLORS["BoratedPolyethylene5wtB"] = (0.80, 0.95, 0.18, 0.35)
    return module


def write_wrl() -> None:
    module = load_exporter()
    module.main()


def projected_segments(module, axes: tuple[str, str]) -> dict[str, list[list[tuple[float, float]]]]:
    idx = {"x": 0, "y": 1, "z": 2}
    a_idx = idx[axes[0]]
    b_idx = idx[axes[1]]
    objs = module.parse_files([INTRO, GEO])
    memo: dict[str, list[list[float]]] = {}
    segments: dict[str, list[list[tuple[float, float]]]] = {}
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
            coords = module.apply(matrix, vertex)
            projected.append((coords[a_idx], coords[b_idx]))
        bucket = segments.setdefault(obj.material, [])
        for face in faces:
            for j, a in enumerate(face):
                b = face[(j + 1) % len(face)]
                bucket.append([projected[a], projected[b]])
    return segments


def add_segments(ax, module, segments: dict[str, list[list[tuple[float, float]]]]) -> None:
    priority = {
        "Aluminium": 2,
        "Kapton": 3,
        "CsI": 4,
        "Copper": 5,
        "BoratedPolyethylene5wtB": 7,
        "PlasticScintillator": 8,
        "W": 9,
        "Ta": 10,
    }
    for material, segs in sorted(segments.items(), key=lambda item: priority.get(item[0], 1)):
        if not segs:
            continue
        r, g, b, alpha = module.COLORS.get(material, (0.60, 0.60, 0.60, 0.60))
        color = (r, g, b, min(0.92, max(0.18, 1.0 - alpha)))
        lw = 0.15
        if material in {"PlasticScintillator", "BoratedPolyethylene5wtB", "W"}:
            lw = 0.55
        elif material in {"CsI", "Copper"}:
            lw = 0.28
        ax.add_collection(LineCollection(segs, colors=[color], linewidths=lw, rasterized=True))


def set_limits(ax, segments: dict[str, list[list[tuple[float, float]]]], pad_frac: float = 0.06) -> None:
    pts = [p for segs in segments.values() for seg in segs for p in seg]
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    span = max(xmax - xmin, ymax - ymin)
    pad = max(1.0, pad_frac * span)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)


def write_detail_figure(skin: dict[str, float]) -> None:
    module = load_exporter()
    xz = projected_segments(module, ("x", "z"))
    xy = projected_segments(module, ("x", "y"))
    del skin

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 7.6), gridspec_kw={"width_ratios": [1.05, 1.0]})
    ax_xz, ax_xy = axes

    add_segments(ax_xz, module, xz)
    add_segments(ax_xy, module, xy)

    ax_xz.set_title("X-Z detail projection: detector bay and optimization patch")
    ax_xz.set_xlabel("x [cm]")
    ax_xz.set_ylabel("z [cm]")
    ax_xz.set_xlim(-45, 45)
    ax_xz.set_ylim(-34, 32)
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.grid(alpha=0.20)
    ax_xz.axhline(-5.2, color="black", ls="--", lw=0.7, alpha=0.55)
    ax_xz.add_patch(
        Rectangle(
            (-BPE_ROUT_CM, SIGNAL_WINDOW_Z_CM - SIGNAL_WINDOW_CUT_HALF_Z_CM),
            BPE_ROUT_CM,
            2.0 * SIGNAL_WINDOW_CUT_HALF_Z_CM,
            fill=False,
            edgecolor="#6f8f00",
            linewidth=1.2,
            linestyle="--",
        )
    )
    ax_xz.add_patch(
        Rectangle(
            (-W_BAFFLE_ROUT_CM, W_BAFFLE_ZMIN_CM),
            2.0 * W_BAFFLE_ROUT_CM,
            W_BAFFLE_THICKNESS_CM,
            fill=False,
            edgecolor="black",
            linewidth=1.4,
        )
    )
    ax_xz.text(-43, 28.5, "cyan: full-wrap active plastic scintillator skin", fontsize=8, color="#007f99")
    ax_xz.text(-43, 25.5, "yellow/green: 1 cm borated PE inside plastic", fontsize=8, color="#6f8f00")
    ax_xz.text(-43, 22.5, "dashed box: BPE signal-window cutout only", fontsize=8, color="#6f8f00")
    ax_xz.text(-43, 19.5, "black: 5 mm W bottom baffle inside BPE", fontsize=8, color="#333333")
    ax_xz.text(-43, 16.5, "plastic bottom has local NF2 rod relief cutouts", fontsize=8, color="#007f99")

    add_segments(ax_xy, module, xy)
    ax_xy.set_title("X-Y projection: full outer skin and inner BPE envelope")
    ax_xy.set_xlabel("x [cm]")
    ax_xy.set_ylabel("y [cm]")
    ax_xy.set_xlim(-45, 45)
    ax_xy.set_ylim(-45, 45)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.20)
    ax_xy.add_patch(Circle((0, 0), PLASTIC_RIN_CM, fill=False, edgecolor="#0099bb", lw=0.9, ls=":"))
    ax_xy.add_patch(Circle((0, 0), PLASTIC_ROUT_CM, fill=False, edgecolor="#0099bb", lw=1.3))
    ax_xy.add_patch(Circle((0, 0), BPE_RIN_CM, fill=False, edgecolor="#6f8f00", lw=0.9, ls=":"))
    ax_xy.add_patch(Circle((0, 0), BPE_ROUT_CM, fill=False, edgecolor="#6f8f00", lw=1.2))
    ax_xy.add_patch(Circle((0, 0), W_BAFFLE_ROUT_CM, fill=False, edgecolor="black", lw=1.3))
    ax_xy.add_patch(
        Rectangle(
            (-BPE_ROUT_CM, -SIGNAL_WINDOW_CUT_HALF_Y_CM),
            BPE_ROUT_CM,
            2.0 * SIGNAL_WINDOW_CUT_HALF_Y_CM,
            fill=False,
            edgecolor="#6f8f00",
            linewidth=1.1,
            linestyle="--",
        )
    )
    ax_xy.add_patch(Circle((0, 0), TOP_SERVICE_OPENING_RIN_CM, fill=False, edgecolor="#444444", lw=0.8, ls="--"))
    ax_xy.text(-43, 41, f"plastic r={PLASTIC_RIN_CM:.1f}-{PLASTIC_ROUT_CM:.1f} cm, no phi segmentation", fontsize=8)
    ax_xy.text(-43, 37.5, f"BPE r={BPE_RIN_CM:.1f}-{BPE_ROUT_CM:.1f} cm, window cut on {SIGNAL_WINDOW_X_SIDE}", fontsize=8)
    ax_xy.text(-43, 34, f"top service opening r<{TOP_SERVICE_OPENING_RIN_CM:.1f} cm; W bottom baffle r={W_BAFFLE_ROUT_CM:.1f} cm", fontsize=8)

    fig.suptitle("GeoOpt full plastic skin + borated PE + 5 mm bottom-W draft from Mass_model_511 geometry", fontsize=13)
    fig.tight_layout()
    fig.savefig(DETAIL_PNG, dpi=220)
    fig.savefig(DETAIL_SVG)
    plt.close(fig)


def write_readme(volumes: list[PatchVolume], skin: dict[str, float]) -> None:
    rows = "\n".join(
        f"| `{vol.name}` | {vol.material} | {vol.mass_kg:.3f} | {vol.role} |"
        for vol in volumes
    )
    README.write_text(
        "\n".join(
            [
                "# Geometry Optimization Draft: Full Plastic Skin + BPE + 5 mm Bottom W",
                "",
                f"Status: `{PATCH_STATUS}`",
                "",
                "This directory contains a derived geometry draft built from the Mass_model_511 proxy geometry.",
                "The source geometry is read-only; generated files live only under this workpackage directory.",
                "",
                "User-reviewed revision implemented here:",
                "- active plastic scintillator is full-wrap rather than segmented by the low-statistics e+ sample;",
                "- borated polyethylene is a full inner envelope with only the signal-window region cut out;",
                "- the bottom W baffle is 5 mm thick and placed inward of the borated polyethylene.",
                "",
                "## Source",
                "",
                f"- Source geometry directory: `{rel(SOURCE_GEOM_DIR)}`",
                f"- Historical R3 e+ skin metrics retained for provenance only: `{rel(R3_METRICS)}`",
                "",
                "## Patch Contents",
                "",
                "| Volume | Material | Mass kg | Role |",
                "| --- | ---: | ---: | --- |",
                rows,
                "",
                "## Geometry Choices",
                "",
                f"- Plastic skin: `r={PLASTIC_RIN_CM:.3g}-{PLASTIC_ROUT_CM:.3g} cm`, side `z={PLASTIC_SIDE_ZMIN_CM:.3g}..{PLASTIC_SIDE_ZMAX_CM:.3g} cm`, bottom cap, and annular top cap; no phi segmentation.",
                f"- Borated PE: `r={BPE_RIN_CM:.3g}-{BPE_ROUT_CM:.3g} cm`, side `z={BPE_SIDE_ZMIN_CM:.3g}..{BPE_SIDE_ZMAX_CM:.3g} cm`, bottom cap, and annular top cap.",
                f"- Top service/support opening: `r< {TOP_SERVICE_OPENING_RIN_CM:.3g} cm` is left open in the top caps to avoid existing cryostat/support hardware.",
                f"- BPE signal-window cutout: `{SIGNAL_WINDOW_X_SIDE}`, centered at `z={SIGNAL_WINDOW_Z_CM:.3g} cm`, half-widths `y={SIGNAL_WINDOW_CUT_HALF_Y_CM:.3g} cm`, `z={SIGNAL_WINDOW_CUT_HALF_Z_CM:.3g} cm`; no extra window material is added.",
                f"- Plastic bottom NF2 rod relief cutouts: centers at `(x,y)=({BOTTOM_ROD_RELIEF_X_CM:.2f}, +/-{BOTTOM_ROD_RELIEF_Y_CM:.2f}) cm`, half-widths `{BOTTOM_ROD_RELIEF_HALF_X_CM:.2f} x {BOTTOM_ROD_RELIEF_HALF_Y_CM:.2f} x {BOTTOM_ROD_RELIEF_HALF_Z_CM:.2f} cm`.",
                f"- Plastic side NF2 rod relief cutouts: local centers at `(x,y,z)=({BOTTOM_ROD_RELIEF_X_CM:.2f}, +/-{BOTTOM_ROD_RELIEF_Y_CM:.2f}, {SIDE_ROD_RELIEF_Z_LOCAL_CM:.2f}) cm`, half-widths `{SIDE_ROD_RELIEF_HALF_X_CM:.2f} x {SIDE_ROD_RELIEF_HALF_Y_CM:.2f} x {SIDE_ROD_RELIEF_HALF_Z_CM:.2f} cm`.",
                f"- W baffle: `r=0..{W_BAFFLE_ROUT_CM:.2f} cm`, `z={W_BAFFLE_ZMIN_CM:.2f}..{W_BAFFLE_ZMAX_CM:.2f} cm`, thickness `{W_BAFFLE_THICKNESS_CM:.2f} cm`.",
                f"- Historical R3 reported S1 mass was `{skin['s1_mass_kg']:.6g} kg`; the generated full-wrap mass is listed in the manifest and is not the R3 segmented proxy mass.",
                "",
                "## Generated Files",
                "",
                f"- Geometry setup: `{rel(SETUP)}`",
                f"- Geometry body: `{rel(GEO)}`",
                f"- Detector map copy with plastic-skin detector entries: `{rel(DET)}`",
                f"- Local materials copy with PlasticScintillator and BoratedPolyethylene5wtB: `{rel(MATERIALS)}`",
                f"- WRL visualization: `{rel(WRL)}`",
                f"- 2D detail PNG: `{rel(DETAIL_PNG)}`",
                f"- 2D detail SVG: `{rel(DETAIL_SVG)}`",
                f"- Manifest: `{rel(MANIFEST)}`",
                "",
                "## Boundary",
                "",
                "This is not a transport result, not a replacement geometry authority, and not a paper-facing number source.",
                "Overlap and transport validation are intentionally separate follow-up gates.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_manifest(volumes: list[PatchVolume], skin: dict[str, float]) -> None:
    MANIFEST.write_text(
        json.dumps(
            {
                "status": PATCH_STATUS,
                "source_geometry_dir": rel(SOURCE_GEOM_DIR),
                "geometry_setup": rel(SETUP),
                "geometry_file": rel(GEO),
                "det_file": rel(DET),
                "materials_file": rel(MATERIALS),
                "wrl": rel(WRL),
                "detail_png": rel(DETAIL_PNG),
                "detail_svg": rel(DETAIL_SVG),
                "source_r3_metrics": rel(R3_METRICS),
                "historical_skin_geometry_from_r3_not_instantiated_as_segments": skin,
                "current_revision": {
                    "layer_order_outside_to_inside": [
                        "active PlasticScintillator full-wrap skin",
                        "BoratedPolyethylene5wtB full envelope with signal-window cutout",
                        "5 mm W bottom baffle",
                        "unmodified Mass_model_511 detector",
                    ],
                    "plastic_cm": {
                        "r_inner": PLASTIC_RIN_CM,
                        "r_outer": PLASTIC_ROUT_CM,
                        "side_z_min": PLASTIC_SIDE_ZMIN_CM,
                        "side_z_max": PLASTIC_SIDE_ZMAX_CM,
                        "bottom_z_min": PLASTIC_BOTTOM_ZMIN_CM,
                        "bottom_z_max": PLASTIC_BOTTOM_ZMAX_CM,
                        "top_z_min": PLASTIC_TOP_ZMIN_CM,
                        "top_z_max": PLASTIC_TOP_ZMAX_CM,
                        "top_service_opening_r_inner": TOP_SERVICE_OPENING_RIN_CM,
                        "bottom_nf2_rod_relief_centers": [
                            [BOTTOM_ROD_RELIEF_X_CM, BOTTOM_ROD_RELIEF_Y_CM],
                            [BOTTOM_ROD_RELIEF_X_CM, -BOTTOM_ROD_RELIEF_Y_CM],
                        ],
                        "bottom_nf2_rod_relief_half_widths": [
                            BOTTOM_ROD_RELIEF_HALF_X_CM,
                            BOTTOM_ROD_RELIEF_HALF_Y_CM,
                            BOTTOM_ROD_RELIEF_HALF_Z_CM,
                        ],
                        "side_nf2_rod_relief_centers_local": [
                            [BOTTOM_ROD_RELIEF_X_CM, BOTTOM_ROD_RELIEF_Y_CM, SIDE_ROD_RELIEF_Z_LOCAL_CM],
                            [BOTTOM_ROD_RELIEF_X_CM, -BOTTOM_ROD_RELIEF_Y_CM, SIDE_ROD_RELIEF_Z_LOCAL_CM],
                        ],
                        "side_nf2_rod_relief_half_widths": [
                            SIDE_ROD_RELIEF_HALF_X_CM,
                            SIDE_ROD_RELIEF_HALF_Y_CM,
                            SIDE_ROD_RELIEF_HALF_Z_CM,
                        ],
                    },
                    "borated_polyethylene_cm": {
                        "r_inner": BPE_RIN_CM,
                        "r_outer": BPE_ROUT_CM,
                        "side_z_min": BPE_SIDE_ZMIN_CM,
                        "side_z_max": BPE_SIDE_ZMAX_CM,
                        "bottom_z_min": BPE_BOTTOM_ZMIN_CM,
                        "bottom_z_max": BPE_BOTTOM_ZMAX_CM,
                        "top_z_min": BPE_TOP_ZMIN_CM,
                        "top_z_max": BPE_TOP_ZMAX_CM,
                        "top_service_opening_r_inner": TOP_SERVICE_OPENING_RIN_CM,
                        "signal_window_cut_side": SIGNAL_WINDOW_X_SIDE,
                        "signal_window_z_center": SIGNAL_WINDOW_Z_CM,
                        "signal_window_half_y": SIGNAL_WINDOW_CUT_HALF_Y_CM,
                        "signal_window_half_z": SIGNAL_WINDOW_CUT_HALF_Z_CM,
                    },
                    "w_bottom_baffle_cm": {
                        "r_inner": 0.0,
                        "r_outer": W_BAFFLE_ROUT_CM,
                        "z_min": W_BAFFLE_ZMIN_CM,
                        "z_max": W_BAFFLE_ZMAX_CM,
                        "thickness": W_BAFFLE_THICKNESS_CM,
                    },
                },
                "patch_volumes": [
                    {
                        "name": vol.name,
                        "material": vol.material,
                        "shape": vol.shape,
                        "shape_defs": list(vol.shape_defs),
                        "position_cm": list(vol.position),
                        "role": vol.role,
                        "volume_cm3": vol.volume_cm3,
                        "mass_kg": vol.mass_kg,
                        "active_detector_entry": vol.active,
                    }
                    for vol in volumes
                ],
                "total_added_mass_kg": sum(vol.mass_kg for vol in volumes),
                "boundaries": [
                    "Mass_model_511 source geometry is copied, not modified.",
                    "No transport or background-rate validation is implied.",
                    "The full-wrap plastic skin, borated-PE envelope, and 5 mm W baffle are draft geometric proxies pending overlap and transport validation.",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    copy_geometry_inputs()
    append_materials()
    skin = load_r3_geometry()
    volumes = build_patch_volumes(skin)
    append_geo_patch(volumes)
    append_det_patch(volumes)
    write_overlap_source()
    write_wrl()
    write_detail_figure(skin)
    write_readme(volumes, skin)
    write_manifest(volumes, skin)
    print(json.dumps({"status": PATCH_STATUS, "manifest": rel(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
