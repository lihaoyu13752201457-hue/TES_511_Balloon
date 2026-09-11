#!/usr/bin/env python3
"""Build the S2b 45-degree cryostat-following plastic/BPE shell.

This branch intentionally differs from the over-large S2 sealed outer can:
- the new shell is mounted in InstrumentFrame, so it follows the cryostat
  45-degree axis in world coordinates;
- it encloses the cryostat/outer-Al body scale, not the NF2 support cage;
- it only adds borated polyethylene and plastic scintillator structures.

The output is a geometry-review package and source-visualization package, not a
transport-performance result.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import random
import re
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
ORIGINAL_GEOOPT_DIR = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry"
ORIGINAL_GEOOPT_WRL = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c.wrl"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

GEOM_DIR = WORK / "geometry"
FIG_DIR = WORK / "figures"
GEO = GEOM_DIR / f"{STEM}.geo"
DET = GEOM_DIR / f"{STEM}.det"
SETUP = GEOM_DIR / f"{STEM}.geo.setup"
INTRO = GEOM_DIR / f"Intro_{STEM}.geo"
MATERIALS = GEOM_DIR / "Materials_DEMO2_DR_v3p5.geo"
OVERLAP_SOURCE = GEOM_DIR / "overlap_check.source"

WRL = FIG_DIR / "geoopt_s2b_cryo_shell_45deg.wrl"
DETAIL_PNG = FIG_DIR / "geoopt_s2b_cryo_shell_45deg_2d_detail.png"
DETAIL_SVG = FIG_DIR / "geoopt_s2b_cryo_shell_45deg_2d_detail.svg"
SOURCE_ORIGINAL_WRL = FIG_DIR / "source_1000_prompt_rays_original_s1_R60.wrl"
SOURCE_NEW_WRL = FIG_DIR / "source_1000_prompt_rays_s2b_cryo_shell_R60.wrl"
SOURCE_ORIGINAL_R65_WRL = FIG_DIR / "source_1000_prompt_rays_original_s1_R65_full_geometry_coverage.wrl"
SOURCE_NEW_R65_WRL = FIG_DIR / "source_1000_prompt_rays_s2b_cryo_shell_R65_full_geometry_coverage.wrl"
SOURCE_COMPARISON_PNG = FIG_DIR / "source_1000_prompt_rays_original_vs_s2b.png"
SOURCE_COVERAGE_NOTES = FIG_DIR / "source_radius_coverage_notes.txt"
README = WORK / "README.md"
MANIFEST = WORK / "geoopt_s2b_cryo_shell_45deg_manifest.json"

EXPORTER = ROOT / "old/reports/user_redesign_cylmag_20260621/export_megalib_geo_to_wrl.py"

FILES_TO_COPY = [
    f"{STEM}.geo",
    f"{STEM}.det",
    f"{STEM}.geo.setup",
    f"Intro_{STEM}.geo",
    "Materials_DEMO2_DR_v3p5.geo",
    "overlap_check.source",
]

PATCH_STATUS = "DRAFT_S2B_CRYO_SHELL_45DEG_NOT_TRANSPORT_VALIDATED"

# Local InstrumentFrame dimensions, cm.  InstrumentFrame itself is rotated
# 0 45 0 in the intro geometry, so these cylinders appear as a 45-degree shell
# in world coordinates.  NF2 support radii are deliberately not used.
BPE_RIN_CM = 27.00
BPE_ROUT_CM = 29.00
BPE_SIDE_ZMIN_CM = -24.50
BPE_SIDE_ZMAX_CM = 46.00
BPE_BOTTOM_ZMIN_CM = -26.50
BPE_BOTTOM_ZMAX_CM = -24.50
BPE_TOP_ZMIN_CM = 46.00
BPE_TOP_ZMAX_CM = 48.00
BPE_DENSITY_G_CM3 = 0.95

PLASTIC_RIN_CM = 29.00
PLASTIC_ROUT_CM = 30.00
PLASTIC_SIDE_ZMIN_CM = -26.50
PLASTIC_SIDE_ZMAX_CM = 48.00
PLASTIC_BOTTOM_ZMIN_CM = -27.50
PLASTIC_BOTTOM_ZMAX_CM = -26.50
PLASTIC_TOP_ZMIN_CM = 48.00
PLASTIC_TOP_ZMAX_CM = 49.00
PLASTIC_DENSITY_G_CM3 = 1.03

SOURCE_CENTER_CM = (5.0, 0.0, 9.0)
SOURCE_RADIUS_CM = 60.0
SOURCE_DEBUG_RADIUS_CM = 65.0
N_SOURCE_RAYS = 1000

NF2_RELIEF_ROTATION = (0.0, -45.0, 0.0)
NF2_ROD_RELIEF_HALF_CM = (2.40, 2.40, 32.00)
NF2_SUPPORT_RELIEFS = [
    {
        "label": "BaseMountAnnulus",
        "kind": "PCON",
        "planes": [(-0.80, 34.90, 49.00), (0.80, 34.90, 49.00)],
        "position": (19.7989899, 0.0, -12.7279221),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "TopMountAnnulus",
        "kind": "PCON",
        "planes": [(-0.55, 34.10, 49.80), (0.55, 34.10, 49.80)],
        "position": (-24.7487373, 0.0, 31.8198052),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod01",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (23.2447686, 21.0, 35.2655838),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod02",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (-2.47487373, 42.0, 9.54594155),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod03",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (-28.194516, 21.0, -16.1737008),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod04",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (-28.194516, -21.0, -16.1737008),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod05",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (-2.47487373, -42.0, 9.54594155),
        "rotation": NF2_RELIEF_ROTATION,
    },
    {
        "label": "Rod06",
        "kind": "BRIK",
        "half": NF2_ROD_RELIEF_HALF_CM,
        "position": (23.2447686, -21.0, 35.2655838),
        "rotation": NF2_RELIEF_ROTATION,
    },
]


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


def local_pcon_planes(
    z_min: float, z_max: float, r_inner: float, r_outer: float
) -> tuple[list[tuple[float, float, float]], float]:
    z_center = 0.5 * (z_min + z_max)
    z_half = 0.5 * (z_max - z_min)
    return [(-z_half, r_inner, r_outer), (z_half, r_inner, r_outer)], z_center


def support_relief_shape_defs(
    name: str, planes: list[tuple[float, float, float]], volume_position: tuple[float, float, float]
) -> tuple[tuple[str, ...], str]:
    """Return a PCON base shape with NF2 support clearances subtracted."""
    full = f"{name}_FullShape"
    lines = [
        f"Shape PCON {full}",
        f"{full}.Parameters {' '.join(pcon_line(0.0, 360.0, planes).split()[1:])}",
    ]
    previous = full
    for idx, relief in enumerate(NF2_SUPPORT_RELIEFS, start=1):
        label = str(relief["label"])
        cut = f"{name}_NF2_{label}_ReliefShape"
        orient = f"{name}_NF2_{label}_ReliefOrientation"
        sub = f"{name}_NF2ReliefStep{idx:02d}Shape"
        if relief["kind"] == "PCON":
            relief_planes = relief["planes"]
            lines.extend(
                [
                    f"Shape PCON {cut}",
                    f"{cut}.Parameters {' '.join(pcon_line(0.0, 360.0, relief_planes).split()[1:])}",
                ]
            )
        else:
            hx, hy, hz = relief["half"]
            lines.extend(
                [
                    f"Shape BRIK {cut}",
                    f"{cut}.Parameters {fmt(hx)} {fmt(hy)} {fmt(hz)}",
                ]
            )
        px, py, pz = relief["position"]
        rx, ry, rz = relief["rotation"]
        lines.extend(
            [
                f"Orientation {orient}",
                f"{orient}.Position {fmt(px - volume_position[0])} {fmt(py - volume_position[1])} {fmt(pz - volume_position[2])}",
                f"{orient}.Rotation {fmt(rx)} {fmt(ry)} {fmt(rz)}",
                f"Shape Subtraction {sub}",
                f"{sub}.Parameters {previous} {cut} {orient}",
            ]
        )
        previous = sub
    return tuple(lines), previous


def load_exporter():
    spec = importlib.util.spec_from_file_location("geo_review_wrl_exporter", EXPORTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXPORTER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEOM_DIR = GEOM_DIR
    module.INTRO = INTRO
    module.GEO = GEO
    module.OUT = WRL
    module.COLORS["PlasticScintillator"] = (0.10, 0.75, 0.95, 0.36)
    module.COLORS["BoratedPolyethylene5wtB"] = (0.78, 0.95, 0.18, 0.34)
    return module


def copy_geometry_inputs() -> None:
    GEOM_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES_TO_COPY:
        src = SOURCE_GEOM_DIR / filename
        dst = GEOM_DIR / filename
        if not src.exists():
            raise RuntimeError(f"missing source geometry file: {src}")
        shutil.copy2(src, dst)


def update_setup_surrounding_sphere() -> None:
    text = SETUP.read_text(encoding="utf-8")
    replacement = (
        f"SurroundingSphere {fmt(SOURCE_RADIUS_CM)} "
        f"{fmt(SOURCE_CENTER_CM[0])} {fmt(SOURCE_CENTER_CM[1])} {fmt(SOURCE_CENTER_CM[2])} "
        f"{fmt(SOURCE_RADIUS_CM)}"
    )
    lines = []
    replaced = False
    for line in text.splitlines():
        if line.strip().startswith("SurroundingSphere "):
            lines.append(replacement)
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        raise RuntimeError(f"no SurroundingSphere line found in {SETUP}")
    SETUP.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_materials() -> None:
    text = MATERIALS.read_text(encoding="utf-8")
    block = """

# BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_MATERIALS
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
# END GEOOPT_S2B_CRYO_SHELL_45DEG_MATERIALS
"""
    if "BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_MATERIALS" not in text:
        MATERIALS.write_text(text.rstrip() + block, encoding="utf-8")


def build_patch_volumes() -> list[PatchVolume]:
    specs = [
        (
            "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm",
            "BoratedPolyethylene5wtB",
            BPE_SIDE_ZMIN_CM,
            BPE_SIDE_ZMAX_CM,
            BPE_RIN_CM,
            BPE_ROUT_CM,
            BPE_DENSITY_G_CM3,
            "20 mm BPE side shell following InstrumentFrame; sized to the cryostat/outer-Al body, with NF2 support reliefs",
            False,
        ),
        (
            "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm",
            "BoratedPolyethylene5wtB",
            BPE_BOTTOM_ZMIN_CM,
            BPE_BOTTOM_ZMAX_CM,
            0.0,
            BPE_ROUT_CM,
            BPE_DENSITY_G_CM3,
            "20 mm BPE bottom cap below the cryostat body, with NF2 support reliefs",
            False,
        ),
        (
            "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm",
            "BoratedPolyethylene5wtB",
            BPE_TOP_ZMIN_CM,
            BPE_TOP_ZMAX_CM,
            0.0,
            BPE_ROUT_CM,
            BPE_DENSITY_G_CM3,
            "20 mm BPE top cap above the 300K top-service sleeves, with NF2 support reliefs",
            False,
        ),
        (
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
            "PlasticScintillator",
            PLASTIC_SIDE_ZMIN_CM,
            PLASTIC_SIDE_ZMAX_CM,
            PLASTIC_RIN_CM,
            PLASTIC_ROUT_CM,
            PLASTIC_DENSITY_G_CM3,
            "10 mm active plastic side skin outside the BPE cryostat shell, with NF2 support reliefs",
            True,
        ),
        (
            "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
            "PlasticScintillator",
            PLASTIC_BOTTOM_ZMIN_CM,
            PLASTIC_BOTTOM_ZMAX_CM,
            0.0,
            PLASTIC_ROUT_CM,
            PLASTIC_DENSITY_G_CM3,
            "10 mm active plastic bottom cap outside the BPE bottom cap, with NF2 support reliefs",
            True,
        ),
        (
            "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
            "PlasticScintillator",
            PLASTIC_TOP_ZMIN_CM,
            PLASTIC_TOP_ZMAX_CM,
            0.0,
            PLASTIC_ROUT_CM,
            PLASTIC_DENSITY_G_CM3,
            "10 mm active plastic top cap closing the cryostat-following shell, with NF2 support reliefs",
            True,
        ),
    ]
    volumes: list[PatchVolume] = []
    for name, material, zmin, zmax, rin, rout, density, role, active in specs:
        planes, z = local_pcon_planes(zmin, zmax, rin, rout)
        position = (0.0, 0.0, z)
        shape_defs, final_shape = support_relief_shape_defs(name, planes, position)
        vol = pcon_volume(0.0, 360.0, planes)
        volumes.append(
            PatchVolume(
                name=name,
                material=material,
                shape=final_shape,
                position=position,
                role=role,
                volume_cm3=vol,
                mass_kg=vol * density / 1000.0,
                active=active,
                shape_defs=shape_defs,
            )
        )
    return volumes


def append_geo_patch(volumes: list[PatchVolume]) -> None:
    text = GEO.read_text(encoding="utf-8")
    if "BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_PATCH" in text:
        return
    lines = [
        "",
        "// BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_PATCH",
        f"// Status: {PATCH_STATUS}",
        "// Mother volume is InstrumentFrame, which is rotated 0 45 0 in world coordinates.",
        "// NF2_OuterSupport volumes are deliberately not used to set the envelope.",
        "// NF2 support rods/rings are subtracted as local reliefs so the shell does not enclose support members.",
        "// Only plastic scintillator and borated polyethylene structures are added.",
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
    lines.append("// END GEOOPT_S2B_CRYO_SHELL_45DEG_PATCH")
    GEO.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def append_det_patch(volumes: list[PatchVolume]) -> None:
    text = DET.read_text(encoding="utf-8")
    if "BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_DET" in text:
        return
    lines = [
        "",
        "// BEGIN GEOOPT_S2B_CRYO_SHELL_45DEG_DET",
        "// Active detector entries for the S2b plastic scintillator shell only.",
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
    lines.append("// END GEOOPT_S2B_CRYO_SHELL_45DEG_DET")
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
                "Minimum.FileName            /tmp/DelMe_geoopt_s2b_cryo_shell_overlap",
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


def write_wrl() -> None:
    module = load_exporter()
    module.main()
    # The legacy exporter does not mesh MEGAlib Shape Subtraction solids.  Append
    # a transparent visual envelope so the review WRL still shows the S2b shell
    # size and 45-degree orientation.  The authoritative geometry remains GEO.
    WRL.write_text(
        WRL.read_text(encoding="utf-8")
        + "\n"
        + wrl_shell_visual_overlay("S2b_visual_overlay")
        + "\n",
        encoding="utf-8",
    )


def wrl_shell_visual_overlay(prefix: str) -> str:
    def cylinder_node(name: str, radius: float, height: float, z_center: float, color: str, alpha: float) -> str:
        return f"""
# {prefix}_{name}: visual envelope only; relief cutouts are in the .geo file.
Transform {{
  rotation 0 1 0 0.785398163397
  translation 0 0 0
  children [
    Transform {{
      rotation 1 0 0 1.57079632679
      translation 0 0 {fmt(z_center)}
      children [
        Shape {{
          appearance Appearance {{ material Material {{ diffuseColor {color} transparency {alpha:.3f} }} }}
          geometry Cylinder {{ radius {fmt(radius)} height {fmt(height)} }}
        }}
      ]
    }}
  ]
}}
"""

    return "\n".join(
        [
            "# BEGIN_GEOOPT_S2B_VISUAL_OVERLAY",
            cylinder_node(
                "BPE_outer",
                BPE_ROUT_CM,
                BPE_TOP_ZMAX_CM - BPE_BOTTOM_ZMIN_CM,
                0.5 * (BPE_TOP_ZMAX_CM + BPE_BOTTOM_ZMIN_CM),
                "0.75 0.95 0.2",
                0.74,
            ),
            cylinder_node(
                "Plastic_outer",
                PLASTIC_ROUT_CM,
                PLASTIC_TOP_ZMAX_CM - PLASTIC_BOTTOM_ZMIN_CM,
                0.5 * (PLASTIC_TOP_ZMAX_CM + PLASTIC_BOTTOM_ZMIN_CM),
                "0.1 0.75 0.95",
                0.80,
            ),
            "# END_GEOOPT_S2B_VISUAL_OVERLAY",
        ]
    )


def projected_segments(module, paths: list[Path], axes: tuple[str, str]) -> dict[str, list[list[tuple[float, float]]]]:
    idx = {"x": 0, "y": 1, "z": 2}
    a_idx = idx[axes[0]]
    b_idx = idx[axes[1]]
    objs = module.parse_files(paths)
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
        color = (r, g, b, min(0.94, max(0.18, 1.0 - alpha)))
        lw = 0.14
        if material in {"PlasticScintillator", "BoratedPolyethylene5wtB"}:
            lw = 0.65
        elif material in {"CsI", "Copper", "Aluminium"}:
            lw = 0.26
        ax.add_collection(LineCollection(segs, colors=[color], linewidths=lw, rasterized=True))


def set_equal_limits(ax, points: list[tuple[float, float]], pad: float = 5.0) -> None:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    span = max(xmax - xmin, ymax - ymin) + 2.0 * pad
    ax.set_xlim(cx - 0.5 * span, cx + 0.5 * span)
    ax.set_ylim(cy - 0.5 * span, cy + 0.5 * span)
    ax.set_aspect("equal", adjustable="box")


def write_detail_figure(volumes: list[PatchVolume]) -> None:
    module = load_exporter()
    paths = [INTRO, GEO]
    xz = projected_segments(module, paths, ("x", "z"))
    xy = projected_segments(module, paths, ("x", "y"))
    yz = projected_segments(module, paths, ("y", "z"))

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)
    for ax, segs, title, xlabel, ylabel, proj_axes in [
        (axes[0], xz, "World X-Z projection", "x [cm]", "z [cm]", ("x", "z")),
        (axes[1], xy, "World X-Y projection", "x [cm]", "y [cm]", ("x", "y")),
        (axes[2], yz, "World Y-Z projection", "y [cm]", "z [cm]", ("y", "z")),
    ]:
        add_segments(ax, module, segs)
        bpe_overlay = projected_shell_wire_segments(
            BPE_ROUT_CM, BPE_BOTTOM_ZMIN_CM, BPE_TOP_ZMAX_CM, axes=proj_axes
        )
        plastic_overlay = projected_shell_wire_segments(
            PLASTIC_ROUT_CM, PLASTIC_BOTTOM_ZMIN_CM, PLASTIC_TOP_ZMAX_CM, axes=proj_axes
        )
        ax.add_collection(LineCollection(bpe_overlay, colors=[(0.78, 0.95, 0.18, 0.92)], linewidths=0.8))
        ax.add_collection(LineCollection(plastic_overlay, colors=[(0.10, 0.75, 0.95, 0.95)], linewidths=0.95))
        pts = [p for mat_segs in segs.values() for seg in mat_segs for p in seg]
        pts.extend([p for seg in bpe_overlay for p in seg])
        pts.extend([p for seg in plastic_overlay for p in seg])
        set_equal_limits(ax, pts, pad=6.0)
        ax.grid(True, lw=0.25, alpha=0.35)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

    legend_items = [
        ("S2b plastic scintillator, 10 mm", "#19bfdf"),
        ("S2b BPE, 20 mm", "#c8f22e"),
        ("Al/Cu/CsI existing geometry", "#888888"),
    ]
    for label, color in legend_items:
        axes[0].plot([], [], color=color, lw=3, label=label)
    axes[0].legend(loc="upper right", fontsize=8)
    fig.suptitle(
        "GeoOpt S2b 45-degree cryostat shell: BPE/plastic follow InstrumentFrame, not NF2 supports",
        fontsize=12,
    )
    fig.savefig(DETAIL_PNG, dpi=240)
    fig.savefig(DETAIL_SVG)
    plt.close(fig)

    mass_lines = [
        f"{vol.name}: {vol.mass_kg:.3f} kg, {vol.role}" for vol in volumes
    ]
    (FIG_DIR / "geoopt_s2b_cryo_shell_45deg_mass_notes.txt").write_text(
        "\n".join(mass_lines) + "\n", encoding="utf-8"
    )


def parse_source_card(path: Path) -> list[dict[str, float]]:
    bins: list[dict[str, float]] = []
    pattern = re.compile(
        r"^(?P<name>\S+)\.Beam\s+FarFieldAreaSource\s+"
        r"(?P<t0>[-+0-9.eE]+)\s+(?P<t1>[-+0-9.eE]+)\s+"
        r"(?P<p0>[-+0-9.eE]+)\s+(?P<p1>[-+0-9.eE]+)"
    )
    fluxes: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        match = pattern.match(stripped)
        if match:
            vals = match.groupdict()
            bins.append(
                {
                    "name": vals["name"],
                    "theta0": float(vals["t0"]),
                    "theta1": float(vals["t1"]),
                    "phi0": float(vals["p0"]),
                    "phi1": float(vals["p1"]),
                    "flux": 0.0,
                }
            )
            continue
        if ".Flux" in stripped:
            name, value = stripped.split(".Flux", 1)
            try:
                fluxes[name.strip()] = float(value.strip().split()[0])
            except (IndexError, ValueError):
                pass
    for item in bins:
        item["flux"] = fluxes.get(item["name"], 0.0)
    return bins


def sample_farfield_rays(
    source_card: Path,
    n_rays: int,
    seed: int = 20260708,
    radius_cm: float = SOURCE_RADIUS_CM,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    bins = parse_source_card(source_card)
    weights = [max(0.0, item["flux"]) for item in bins]
    if not bins or sum(weights) <= 0:
        raise RuntimeError(f"could not parse weighted FarFieldAreaSource bins from {source_card}")
    rng = random.Random(seed)
    rays = []
    center = SOURCE_CENTER_CM
    for _ in range(n_rays):
        item = rng.choices(bins, weights=weights, k=1)[0]
        mu0 = math.cos(math.radians(item["theta0"]))
        mu1 = math.cos(math.radians(item["theta1"]))
        mu = rng.uniform(min(mu0, mu1), max(mu0, mu1))
        theta = math.acos(mu)
        phi = math.radians(rng.uniform(item["phi0"], item["phi1"]))
        direction_from_center = (
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta),
        )
        start = tuple(center[i] + radius_cm * direction_from_center[i] for i in range(3))
        end = center
        rays.append((start, end))
    return rays


def world_axis_points_for_instrument_shell(
    radius_cm: float = PLASTIC_ROUT_CM,
    z_min_cm: float = PLASTIC_BOTTOM_ZMIN_CM,
    z_max_cm: float = PLASTIC_TOP_ZMAX_CM,
) -> list[tuple[float, float, float]]:
    angle = math.radians(45.0)
    c, s = math.cos(angle), math.sin(angle)

    def rot_y(point: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = point
        return (c * x + s * z, y, -s * x + c * z)

    pts: list[tuple[float, float, float]] = []
    for z in (z_min_cm, z_max_cm):
        for r in (0.0, radius_cm):
            for phi in range(0, 360, 30):
                a = math.radians(phi)
                pts.append(rot_y((r * math.cos(a), r * math.sin(a), z)))
    return pts


def geometry_visible_max_radius(
    module, paths: list[Path]
) -> tuple[float, tuple[float, float, float], str]:
    objs = module.parse_files(paths)
    memo: dict[str, list[list[float]]] = {}
    best_distance = -1.0
    best_point = (0.0, 0.0, 0.0)
    best_name = ""
    for name in sorted(objs):
        obj = objs[name]
        if obj.material == "Vacuum" and not name.startswith("W_Multihole_CollimatorVac"):
            continue
        mesh = module.mesh_for(obj)
        if mesh is None:
            continue
        vertices, _faces = mesh
        matrix = module.global_matrix(name, objs, memo)
        for vertex in vertices:
            point = module.apply(matrix, vertex)
            distance = math.sqrt(
                (point[0] - SOURCE_CENTER_CM[0]) ** 2
                + (point[1] - SOURCE_CENTER_CM[1]) ** 2
                + (point[2] - SOURCE_CENTER_CM[2]) ** 2
            )
            if distance > best_distance:
                best_distance = distance
                best_point = point
                best_name = name
    return best_distance, best_point, best_name


def projected_shell_wire_segments(
    radius_cm: float,
    z_min_cm: float,
    z_max_cm: float,
    n_phi: int = 144,
    axes: tuple[str, str] = ("x", "z"),
) -> list[list[tuple[float, float]]]:
    coord_idx = {"x": 0, "y": 1, "z": 2}
    a_idx = coord_idx[axes[0]]
    b_idx = coord_idx[axes[1]]
    angle = math.radians(45.0)
    c, s = math.cos(angle), math.sin(angle)

    def rot_y(point: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = point
        return (c * x + s * z, y, -s * x + c * z)

    rings: list[list[tuple[float, float]]] = []
    for z in (z_min_cm, z_max_cm):
        ring = []
        for idx in range(n_phi + 1):
            phi = 2.0 * math.pi * idx / n_phi
            p = rot_y((radius_cm * math.cos(phi), radius_cm * math.sin(phi), z))
            ring.append((p[a_idx], p[b_idx]))
        rings.append(ring)
    segments: list[list[tuple[float, float]]] = []
    for ring in rings:
        for idx in range(len(ring) - 1):
            segments.append([ring[idx], ring[idx + 1]])
    for idx in range(0, n_phi, 12):
        phi = 2.0 * math.pi * idx / n_phi
        p0 = rot_y((radius_cm * math.cos(phi), radius_cm * math.sin(phi), z_min_cm))
        p1 = rot_y((radius_cm * math.cos(phi), radius_cm * math.sin(phi), z_max_cm))
        segments.append([(p0[a_idx], p0[b_idx]), (p1[a_idx], p1[b_idx])])
    return segments


def write_source_wrl(
    out: Path,
    title: str,
    rays: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    base_geometry_wrl: Path,
    source_radius_cm: float,
) -> None:
    ray_color = "1 0.15 0.08"
    if not base_geometry_wrl.exists():
        raise RuntimeError(f"missing base geometry WRL: {base_geometry_wrl}")
    parts = [
        base_geometry_wrl.read_text(encoding="utf-8").rstrip(),
        "",
        "# BEGIN_SOURCE_RAY_OVERLAY",
        f"# {title}",
        f"# Source sphere center cm: {SOURCE_CENTER_CM}; radius cm: {source_radius_cm}",
    ]

    # Source sphere.
    parts.append(
        f"""
Transform {{
  translation {fmt(SOURCE_CENTER_CM[0])} {fmt(SOURCE_CENTER_CM[1])} {fmt(SOURCE_CENTER_CM[2])}
  children [
    Shape {{
      appearance Appearance {{ material Material {{ diffuseColor 0.1 0.25 1 transparency 0.88 }} }}
      geometry Sphere {{ radius {fmt(source_radius_cm)} }}
    }}
  ]
}}
"""
    )

    coords: list[str] = []
    indexes: list[str] = []
    for idx, (start, end) in enumerate(rays):
        coords.append(f"{fmt(start[0])} {fmt(start[1])} {fmt(start[2])}")
        coords.append(f"{fmt(end[0])} {fmt(end[1])} {fmt(end[2])}")
        indexes.append(f"{2 * idx}, {2 * idx + 1}, -1")
    parts.append(
        f"""
Shape {{
  appearance Appearance {{ material Material {{ emissiveColor {ray_color} diffuseColor {ray_color} transparency 0.58 }} }}
  geometry IndexedLineSet {{
    coord Coordinate {{ point [ {', '.join(coords)} ] }}
    coordIndex [ {', '.join(indexes)} ]
  }}
}}
"""
    )
    parts.append("# END_SOURCE_RAY_OVERLAY")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def project_rays_xz(
    rays: list[tuple[tuple[float, float, float], tuple[float, float, float]]]
) -> list[list[tuple[float, float]]]:
    return [[(a[0], a[2]), (b[0], b[2])] for a, b in rays]


def write_source_visuals() -> None:
    source_card = ROOT / (
        "runs/geometry_optimization_20260704/"
        "step02_buildup_geo_opt_s1_bpe_w5_fullstat_v1/job_sources/"
        "Background_n_fullsphere20_rep01_part01.source"
    )
    rays = sample_farfield_rays(source_card, N_SOURCE_RAYS, radius_cm=SOURCE_RADIUS_CM)
    rays_r65 = sample_farfield_rays(
        source_card,
        N_SOURCE_RAYS,
        seed=20260708,
        radius_cm=SOURCE_DEBUG_RADIUS_CM,
    )
    write_source_wrl(
        SOURCE_ORIGINAL_WRL,
        "Original S1 R60 source with 1000 prompt neutron far-field rays over full geometry WRL",
        rays,
        ORIGINAL_GEOOPT_WRL,
        SOURCE_RADIUS_CM,
    )
    write_source_wrl(
        SOURCE_NEW_WRL,
        "S2b cryostat shell R60 source with 1000 prompt neutron far-field rays over full geometry WRL",
        rays,
        WRL,
        SOURCE_RADIUS_CM,
    )
    write_source_wrl(
        SOURCE_ORIGINAL_R65_WRL,
        "Original S1 R65 source with 1000 prompt neutron far-field rays over full geometry WRL",
        rays_r65,
        ORIGINAL_GEOOPT_WRL,
        SOURCE_DEBUG_RADIUS_CM,
    )
    write_source_wrl(
        SOURCE_NEW_R65_WRL,
        "S2b cryostat shell R65 source with 1000 prompt neutron far-field rays over full geometry WRL",
        rays_r65,
        WRL,
        SOURCE_DEBUG_RADIUS_CM,
    )

    module = load_exporter()
    orig_max, orig_point, orig_name = geometry_visible_max_radius(
        module,
        [
            ORIGINAL_GEOOPT_DIR / f"Intro_{STEM}.geo",
            ORIGINAL_GEOOPT_DIR / f"{STEM}.geo",
        ],
    )
    new_max, new_point, new_name = geometry_visible_max_radius(module, [INTRO, GEO])
    shell_pts_3d = world_axis_points_for_instrument_shell(
        PLASTIC_ROUT_CM, PLASTIC_BOTTOM_ZMIN_CM, PLASTIC_TOP_ZMAX_CM
    )
    shell_max, shell_point = max(
        (
            math.sqrt(
                (point[0] - SOURCE_CENTER_CM[0]) ** 2
                + (point[1] - SOURCE_CENTER_CM[1]) ** 2
                + (point[2] - SOURCE_CENTER_CM[2]) ** 2
            ),
            point,
        )
        for point in shell_pts_3d
    )
    SOURCE_COVERAGE_NOTES.write_text(
        "\n".join(
            [
                "Source radius coverage check",
                "============================",
                f"Source center cm: {SOURCE_CENTER_CM}",
                f"Applied production source radius: {SOURCE_RADIUS_CM:.3f} cm",
                f"Conservative debug source radius: {SOURCE_DEBUG_RADIUS_CM:.3f} cm",
                "",
                f"S2b explicit plastic shell max distance: {shell_max:.3f} cm at {tuple(round(x, 3) for x in shell_point)}",
                f"Original S1 visible-geometry max distance: {orig_max:.3f} cm at {tuple(round(x, 3) for x in orig_point)} in {orig_name}",
                f"S2b visible-geometry max distance: {new_max:.3f} cm at {tuple(round(x, 3) for x in new_point)} in {new_name}",
                "",
                "Conclusion:",
                "- With the shifted center, R60 is sufficient for the complete visible detector geometry.",
                "- The R60 clearance is about 2 cm for both original S1 and S2b visible geometry.",
                "- R65 is retained only as a conservative debug visualization; it is not the MEGAlib-manual-preferred production choice.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    ray_segments = project_rays_xz(rays)
    shell_pts = [(p[0], p[2]) for p in world_axis_points_for_instrument_shell()]
    new_shell_segments = projected_shell_wire_segments(
        PLASTIC_ROUT_CM, PLASTIC_BOTTOM_ZMIN_CM, PLASTIC_TOP_ZMAX_CM
    )
    old_shell_segments = projected_shell_wire_segments(29.4, -25.1, 9.2)
    for ax, title, include_new in [
        (axes[0], "Original S1 source sanity, shifted-center R60", False),
        (axes[1], "New S2b source sanity, shifted-center R60", True),
    ]:
        ax.add_collection(LineCollection(ray_segments, colors=[(1, 0.2, 0.1, 0.12)], linewidths=0.35))
        ax.add_patch(
            Circle((SOURCE_CENTER_CM[0], SOURCE_CENTER_CM[2]), SOURCE_RADIUS_CM, fill=False, lw=1.0, ec="blue", alpha=0.7)
        )
        if include_new:
            ax.add_collection(LineCollection(new_shell_segments, colors=[(0.10, 0.75, 0.95, 0.9)], linewidths=0.9))
        else:
            ax.add_collection(LineCollection(old_shell_segments, colors=[(0.10, 0.75, 0.95, 0.65)], linewidths=0.8))
        pts = [(x, z) for seg in ray_segments for x, z in seg]
        pts.extend([(SOURCE_CENTER_CM[0] - SOURCE_RADIUS_CM, SOURCE_CENTER_CM[2] - SOURCE_RADIUS_CM)])
        pts.extend([(SOURCE_CENTER_CM[0] + SOURCE_RADIUS_CM, SOURCE_CENTER_CM[2] + SOURCE_RADIUS_CM)])
        if include_new:
            pts.extend(shell_pts)
        set_equal_limits(ax, pts, pad=10.0)
        ax.grid(True, lw=0.25, alpha=0.35)
        ax.set_xlabel("world x [cm]")
        ax.set_ylabel("world z [cm]")
        ax.set_title(title)
    fig.suptitle("1000 prompt-particle far-field ray samples, MEGAlib-manual R60 center shifted to (5, 0, 9) cm")
    fig.savefig(SOURCE_COMPARISON_PNG, dpi=220)
    plt.close(fig)


def write_readme(volumes: list[PatchVolume]) -> None:
    total_mass = sum(v.mass_kg for v in volumes)
    plastic_mass = sum(v.mass_kg for v in volumes if v.material == "PlasticScintillator")
    bpe_mass = sum(v.mass_kg for v in volumes if v.material == "BoratedPolyethylene5wtB")
    rows = [
        "| Volume | Material | Mass kg | Role |",
        "|---|---:|---:|---|",
    ]
    for vol in volumes:
        rows.append(f"| `{vol.name}` | `{vol.material}` | {vol.mass_kg:.3f} | {vol.role} |")
    README.write_text(
        "\n".join(
            [
                "# Geometry Optimization Draft: S2b 45-degree cryostat shell",
                "",
                f"Status: `{PATCH_STATUS}`",
                "",
                "This branch replaces the over-large S2 sealed outer-can interpretation with a small shell",
                "that follows the cryostat axis.  The added volumes are children of `InstrumentFrame`,",
                "whose intro geometry has `InstrumentFrame.Rotation 0 45 0`; therefore the shell is",
                "45 degrees in world coordinates without using the NF2 support-cage envelope.",
                "",
                "Only plastic scintillator and borated polyethylene are added in this branch.  No W baffle",
                "or other passive gamma collimator is added here.",
                "",
                "## Dimensions",
                "",
                f"- BPE side shell: `r={BPE_RIN_CM:.1f}-{BPE_ROUT_CM:.1f} cm`, `z={BPE_SIDE_ZMIN_CM:.1f}..{BPE_SIDE_ZMAX_CM:.1f} cm`, thickness 20 mm.",
                f"- BPE caps: bottom `z={BPE_BOTTOM_ZMIN_CM:.1f}..{BPE_BOTTOM_ZMAX_CM:.1f}`, top `z={BPE_TOP_ZMIN_CM:.1f}..{BPE_TOP_ZMAX_CM:.1f}`, solid to `r={BPE_ROUT_CM:.1f} cm`.",
                f"- Plastic side skin: `r={PLASTIC_RIN_CM:.1f}-{PLASTIC_ROUT_CM:.1f} cm`, `z={PLASTIC_SIDE_ZMIN_CM:.1f}..{PLASTIC_SIDE_ZMAX_CM:.1f} cm`, thickness 10 mm.",
                f"- Plastic caps: bottom `z={PLASTIC_BOTTOM_ZMIN_CM:.1f}..{PLASTIC_BOTTOM_ZMAX_CM:.1f}`, top `z={PLASTIC_TOP_ZMIN_CM:.1f}..{PLASTIC_TOP_ZMAX_CM:.1f}`, solid to `r={PLASTIC_ROUT_CM:.1f} cm`.",
                "- NF2 support annuli/rods are excluded from the envelope; local reliefs are subtracted where they pass through the shell.",
                f"- Production source sphere: `SurroundingSphere {SOURCE_RADIUS_CM:.0f} {SOURCE_CENTER_CM[0]:.1f} {SOURCE_CENTER_CM[1]:.1f} {SOURCE_CENTER_CM[2]:.1f} {SOURCE_RADIUS_CM:.0f}`.",
                "",
                "## Added mass",
                "",
                f"- Plastic scintillator: `{plastic_mass:.3f} kg` before relief subtraction.",
                f"- Borated polyethylene: `{bpe_mass:.3f} kg` before relief subtraction.",
                f"- Total added mass: `{total_mass:.3f} kg` before relief subtraction.",
                "",
                "## Visual outputs",
                "",
                f"- Geometry WRL: `{rel(WRL)}`",
                f"- Geometry 2D PNG: `{rel(DETAIL_PNG)}`",
                f"- Source WRL on full geometry, original S1 R60: `{rel(SOURCE_ORIGINAL_WRL)}`",
                f"- Source WRL on full geometry, S2b R60: `{rel(SOURCE_NEW_WRL)}`",
                f"- Source WRL on full geometry, original S1 R65: `{rel(SOURCE_ORIGINAL_R65_WRL)}`",
                f"- Source WRL on full geometry, S2b R65: `{rel(SOURCE_NEW_R65_WRL)}`",
                f"- Source PNG comparison: `{rel(SOURCE_COMPARISON_PNG)}`",
                f"- Source radius coverage notes: `{rel(SOURCE_COVERAGE_NOTES)}`",
                "",
                "## Added volumes",
                "",
                *rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_manifest(volumes: list[PatchVolume]) -> None:
    total_mass = sum(v.mass_kg for v in volumes)
    shell_outer_world_extent_note = (
        "InstrumentFrame-local shell is r<=30 cm and z=-27.5..49 cm. "
        "It is not sized from NF2 support radii.  The production source sphere is shifted-center R60: "
        "SurroundingSphere 60 5.0 0.0 9.0 60."
    )
    payload = {
        "status": PATCH_STATUS,
        "created": "2026-07-08",
        "branch": WORK.name,
        "geometry": rel(GEO),
        "setup": rel(SETUP),
        "detector": rel(DET),
        "basis_geometry": rel(SOURCE_GEOM_DIR),
        "original_s1_geometry_for_visual_comparison": rel(ORIGINAL_GEOOPT_DIR),
        "coordinate_policy": {
            "mother": "InstrumentFrame",
            "instrument_frame_rotation_deg": [0.0, 45.0, 0.0],
            "excluded_envelope": "NF2_OuterSupport_* support cage and rods",
        },
        "dimensions_cm": {
            "bpe": {
                "side_r_inner": BPE_RIN_CM,
                "side_r_outer": BPE_ROUT_CM,
                "side_z_min": BPE_SIDE_ZMIN_CM,
                "side_z_max": BPE_SIDE_ZMAX_CM,
                "bottom_z_min": BPE_BOTTOM_ZMIN_CM,
                "bottom_z_max": BPE_BOTTOM_ZMAX_CM,
                "top_z_min": BPE_TOP_ZMIN_CM,
                "top_z_max": BPE_TOP_ZMAX_CM,
            },
            "plastic": {
                "side_r_inner": PLASTIC_RIN_CM,
                "side_r_outer": PLASTIC_ROUT_CM,
                "side_z_min": PLASTIC_SIDE_ZMIN_CM,
                "side_z_max": PLASTIC_SIDE_ZMAX_CM,
                "bottom_z_min": PLASTIC_BOTTOM_ZMIN_CM,
                "bottom_z_max": PLASTIC_BOTTOM_ZMAX_CM,
                "top_z_min": PLASTIC_TOP_ZMIN_CM,
                "top_z_max": PLASTIC_TOP_ZMAX_CM,
            },
        },
        "source_visuals": {
            "source_card": rel(
                ROOT
                / "runs/geometry_optimization_20260704/step02_buildup_geo_opt_s1_bpe_w5_fullstat_v1/job_sources/Background_n_fullsphere20_rep01_part01.source"
            ),
            "n_prompt_ray_samples": N_SOURCE_RAYS,
            "source_radius_cm": SOURCE_RADIUS_CM,
            "debug_source_radius_cm": SOURCE_DEBUG_RADIUS_CM,
            "source_center_cm": SOURCE_CENTER_CM,
            "original_wrl": rel(SOURCE_ORIGINAL_WRL),
            "new_wrl": rel(SOURCE_NEW_WRL),
            "original_r65_wrl": rel(SOURCE_ORIGINAL_R65_WRL),
            "new_r65_wrl": rel(SOURCE_NEW_R65_WRL),
            "comparison_png": rel(SOURCE_COMPARISON_PNG),
            "coverage_notes": rel(SOURCE_COVERAGE_NOTES),
        },
        "mass_kg": {
            "plastic": sum(v.mass_kg for v in volumes if v.material == "PlasticScintillator"),
            "bpe": sum(v.mass_kg for v in volumes if v.material == "BoratedPolyethylene5wtB"),
            "total": total_mass,
        },
        "volumes": [
            {
                "name": v.name,
                "material": v.material,
                "position_cm": v.position,
                "shape": v.shape,
                "role": v.role,
                "volume_cm3": v.volume_cm3,
                "mass_kg": v.mass_kg,
                "active": v.active,
            }
            for v in volumes
        ],
        "notes": [
            shell_outer_world_extent_note,
            "Transport performance is not claimed by this geometry-review branch.",
            "Active veto post-processing must include GeoOpt_S2B_CryoShell_Plastic* volumes.",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    copy_geometry_inputs()
    update_setup_surrounding_sphere()
    append_materials()
    volumes = build_patch_volumes()
    append_geo_patch(volumes)
    append_det_patch(volumes)
    write_overlap_source()
    write_wrl()
    write_detail_figure(volumes)
    write_source_visuals()
    write_readme(volumes)
    write_manifest(volumes)
    print(f"Wrote {rel(GEO)}")
    print(f"Wrote {rel(WRL)}")
    print(f"Wrote {rel(DETAIL_PNG)}")
    print(f"Wrote {rel(SOURCE_ORIGINAL_WRL)}")
    print(f"Wrote {rel(SOURCE_NEW_WRL)}")
    print(f"Added mass kg: {sum(v.mass_kg for v in volumes):.3f}")


if __name__ == "__main__":
    main()
