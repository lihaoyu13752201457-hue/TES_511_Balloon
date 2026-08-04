#!/usr/bin/env python3
"""Rebuild the retained S3c-C0 geometry without legacy S3/S3a/S3b files.

The vendored base recipe is used only as geometry construction code.  Output is
written to this dated mainline package and never overwrites retained S3c-C0.

No source cards, run products, Step05/06/08 outputs, or authority geometries are
modified by this builder.
"""

from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
GEOOPT = ROOT / "engineering/geometry_optimization_20260704"
S3_BUILDER = Path(__file__).resolve().parent / "_s3c_base_recipe.py"


def load_s3_builder():
    spec = importlib.util.spec_from_file_location("geoopt_s3_builder", S3_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load S3 builder: {S3_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


s3 = load_s3_builder()


@dataclass(frozen=True)
class Variant:
    key: str
    directory: str
    title: str
    status: str
    scintillator_material: str
    scintillator_density_g_cm3: float
    shell: str
    description: str


VARIANTS = [
    Variant(
        key="s3c",
        directory="40_s3c_mainline_lightweight_review_20260710/generated_geometry/s3c_c0_rebuild",
        title="S3c-C0 BGO Barrel With 2 mm W + 3 mm Al Shell",
        status="S3C_C0_REBUILD_NOT_RETAINED_AUTHORITY",
        scintillator_material="BGO",
        scintillator_density_g_cm3=7.13,
        shell="w2_al3",
        description="S3 geometry combining the BGO full-wrap scintillator and the 2 mm W + 3 mm Al outer shell.",
    ),
]


STEM = s3.STEM
W_DENSITY_G_CM3 = 19.3
AL_DENSITY_G_CM3 = s3.AL_DENSITY_G_CM3

# For the thinner W+Al shell, keep the S3 inner shell faces fixed and leave the
# removed 3 mm as empty clearance on the outside.
W_THICKNESS_CM = 0.2
AL_THIN_THICKNESS_CM = 0.3
THIN_SHELL_ROUT_CM = s3.AL_RIN_CM + W_THICKNESS_CM + AL_THIN_THICKNESS_CM


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def copy_geometry_inputs(geometry_dir: Path) -> None:
    geometry_dir.mkdir(parents=True, exist_ok=True)
    for filename in s3.FILES_TO_COPY:
        src = s3.S2B_GEOM / filename
        dst_name = "overlap_check_s2b.source" if filename == "overlap_check.source" else filename
        shutil.copy2(src, geometry_dir / dst_name)


def scintillator_prefix(variant: Variant) -> str:
    return f"{variant.scintillator_material}_{variant.key.upper()}"


def wrapper_prefix(variant: Variant) -> str:
    return f"ActiveShield_{variant.key.upper()}_{variant.scintillator_material}"


def shell_prefix(variant: Variant, material: str) -> str:
    return f"Outer_{material}_{variant.key.upper()}_{variant.scintillator_material}"


def scintillator_volumes(variant: Variant) -> list:
    prefix = scintillator_prefix(variant)
    material = variant.scintillator_material
    density = variant.scintillator_density_g_cm3
    label = "BGO" if material == "BGO" else "CsI"
    return [
        s3.S3Volume(
            name=f"{prefix}_FullWrap_SideShell_WindowCut_40mm",
            material=material,
            rin=s3.CSI_RIN_CM,
            rout=s3.CSI_ROUT_CM,
            zmin=s3.CSI_SIDE_ZMIN_CM,
            zmax=s3.CSI_SIDE_ZMAX_CM,
            density=density,
            role=f"4 cm {label} active side shell; S3 dimensions and side-window cut retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="side_window",
            nf2_relief=True,
            pump_line_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_FullWrap_BottomCap_40mm",
            material=material,
            rin=0.0,
            rout=s3.CSI_ROUT_CM,
            zmin=s3.BOTTOM_CSI_ZMIN_CM,
            zmax=s3.BOTTOM_CSI_ZMAX_CM,
            density=density,
            role=f"4 cm {label} active bottom cap; S3 dimensions retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_FullWrap_TopAnnulus_40mm",
            material=material,
            rin=s3.TOP_SERVICE_OPENING_R_CM,
            rout=s3.CSI_ROUT_CM,
            zmin=s3.TOP_CSI_ZMIN_CM,
            zmax=s3.TOP_CSI_ZMAX_CM,
            density=density,
            role=f"4 cm {label} active top annulus; top service opening retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def kapton_volumes(variant: Variant) -> list:
    prefix = wrapper_prefix(variant)
    label = variant.scintillator_material
    return [
        s3.S3Volume(
            name=f"{prefix}_Kapton_SideWrap_WindowCut_0p3mm",
            material="Kapton",
            rin=s3.KAPTON_RIN_CM,
            rout=s3.KAPTON_ROUT_CM,
            zmin=s3.KAPTON_SIDE_ZMIN_CM,
            zmax=s3.KAPTON_SIDE_ZMAX_CM,
            density=s3.KAPTON_DENSITY_G_CM3,
            role=f"thin Kapton side wrapper following the {label} shell; side-window cut retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_Kapton_BottomCap_0p3mm",
            material="Kapton",
            rin=0.0,
            rout=s3.KAPTON_ROUT_CM,
            zmin=s3.BOTTOM_KAPTON_ZMIN_CM,
            zmax=s3.BOTTOM_KAPTON_ZMAX_CM,
            density=s3.KAPTON_DENSITY_G_CM3,
            role=f"thin Kapton bottom wrapper between the {label} cap and outer shell",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_Kapton_TopAnnulus_0p3mm",
            material="Kapton",
            rin=s3.TOP_SERVICE_OPENING_R_CM,
            rout=s3.KAPTON_ROUT_CM,
            zmin=s3.TOP_KAPTON_ZMIN_CM,
            zmax=s3.TOP_KAPTON_ZMAX_CM,
            density=s3.KAPTON_DENSITY_G_CM3,
            role=f"thin Kapton top annulus wrapper preserving the {label} top service opening",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def al8_shell_volumes(variant: Variant) -> list:
    prefix = shell_prefix(variant, "Al")
    label = variant.scintillator_material
    return [
        s3.S3Volume(
            name=f"{prefix}_Mechanical_SideShell_WindowCut_8mm",
            material="Aluminium",
            rin=s3.AL_RIN_CM,
            rout=s3.AL_ROUT_CM,
            zmin=s3.AL_SIDE_ZMIN_CM,
            zmax=s3.AL_SIDE_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role=f"0.8 cm Al mechanical side shell following the {label} shell; S3 dimensions retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_Mechanical_BottomCap_8mm",
            material="Aluminium",
            rin=0.0,
            rout=s3.AL_ROUT_CM,
            zmin=s3.BOTTOM_AL_ZMIN_CM,
            zmax=s3.BOTTOM_AL_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role=f"0.8 cm Al mechanical bottom cap for the {label} shell; S3 dimensions retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{prefix}_Mechanical_TopAnnulus_8mm",
            material="Aluminium",
            rin=s3.TOP_SERVICE_OPENING_R_CM,
            rout=s3.AL_ROUT_CM,
            zmin=s3.TOP_AL_ZMIN_CM,
            zmax=s3.TOP_AL_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role=f"0.8 cm Al mechanical top annulus for the {label} shell; S3 dimensions retained",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def w2_al3_shell_volumes(variant: Variant) -> list:
    label = variant.scintillator_material
    w_prefix = shell_prefix(variant, "W")
    al_prefix = shell_prefix(variant, "Al")

    bottom_w_zmax = s3.BOTTOM_AL_ZMAX_CM
    bottom_w_zmin = bottom_w_zmax - W_THICKNESS_CM
    bottom_al_zmax = bottom_w_zmin
    bottom_al_zmin = bottom_al_zmax - AL_THIN_THICKNESS_CM

    top_w_zmin = s3.TOP_AL_ZMIN_CM
    top_w_zmax = top_w_zmin + W_THICKNESS_CM
    top_al_zmin = top_w_zmax
    top_al_zmax = top_al_zmin + AL_THIN_THICKNESS_CM

    return [
        s3.S3Volume(
            name=f"{w_prefix}_Mechanical_SideShell_WindowCut_2mm",
            material="W",
            rin=s3.AL_RIN_CM,
            rout=s3.AL_RIN_CM + W_THICKNESS_CM,
            zmin=s3.AL_SIDE_ZMIN_CM,
            zmax=s3.AL_SIDE_ZMAX_CM,
            density=W_DENSITY_G_CM3,
            role=f"2 mm W inner mechanical side shell replacing the inner part of the S3 8 mm Al shell around {label}",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{al_prefix}_Mechanical_SideShell_WindowCut_3mm",
            material="Aluminium",
            rin=s3.AL_RIN_CM + W_THICKNESS_CM,
            rout=THIN_SHELL_ROUT_CM,
            zmin=s3.AL_SIDE_ZMIN_CM,
            zmax=s3.AL_SIDE_ZMAX_CM,
            density=AL_DENSITY_G_CM3,
            role="3 mm Al outer mechanical side shell; outer 3 mm of the old S3 shell is left as empty clearance",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="side_window",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{w_prefix}_Mechanical_BottomCap_2mm",
            material="W",
            rin=0.0,
            rout=THIN_SHELL_ROUT_CM,
            zmin=bottom_w_zmin,
            zmax=bottom_w_zmax,
            density=W_DENSITY_G_CM3,
            role=f"2 mm W bottom cap adjacent to the {label}/Kapton package",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{al_prefix}_Mechanical_BottomCap_3mm",
            material="Aluminium",
            rin=0.0,
            rout=THIN_SHELL_ROUT_CM,
            zmin=bottom_al_zmin,
            zmax=bottom_al_zmax,
            density=AL_DENSITY_G_CM3,
            role="3 mm Al bottom cap outside the W cap; remaining old S3 bottom thickness is empty clearance",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{w_prefix}_Mechanical_TopAnnulus_2mm",
            material="W",
            rin=s3.TOP_SERVICE_OPENING_R_CM,
            rout=THIN_SHELL_ROUT_CM,
            zmin=top_w_zmin,
            zmax=top_w_zmax,
            density=W_DENSITY_G_CM3,
            role=f"2 mm W top annulus adjacent to the {label}/Kapton package",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name=f"{al_prefix}_Mechanical_TopAnnulus_3mm",
            material="Aluminium",
            rin=s3.TOP_SERVICE_OPENING_R_CM,
            rout=THIN_SHELL_ROUT_CM,
            zmin=top_al_zmin,
            zmax=top_al_zmax,
            density=AL_DENSITY_G_CM3,
            role="3 mm Al top annulus outside the W annulus; remaining old S3 top thickness is empty clearance",
            detector=True,
            trigger_threshold=0.001,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def variant_volumes(variant: Variant) -> list:
    volumes = []
    volumes.extend(scintillator_volumes(variant))
    volumes.extend(kapton_volumes(variant))
    if variant.shell == "al8":
        volumes.extend(al8_shell_volumes(variant))
    elif variant.shell == "w2_al3":
        volumes.extend(w2_al3_shell_volumes(variant))
    else:
        raise RuntimeError(f"unknown shell mode: {variant.shell}")
    return volumes


def append_variant_geo(work_dir: Path, geometry_dir: Path, variant: Variant, volumes: list) -> dict[str, int]:
    geo = geometry_dir / f"{STEM}.geo"
    text = geo.read_text(encoding="utf-8")
    text, remove_counts = s3.remove_volume_blocks(text, s3.REMOVED_VOLUMES)
    marker = f"BEGIN GEOOPT_{variant.key.upper()}_PATCH"
    if marker in text:
        raise RuntimeError(f"{variant.key} patch already present in {geo}")

    lines = [
        "",
        f"// {marker}",
        f"// Status: {variant.status}",
        "// Derived from S3.  S2b BPE/plastic shells, source sphere, and signal-window aperture are unchanged.",
        f"// Variant change: {variant.description}",
    ]
    if variant.shell == "w2_al3":
        lines.append(
            f"// The old S3 outer Al shell occupied {s3.AL_RIN_CM:.1f}..{s3.AL_ROUT_CM:.1f} cm radially on the side;"
            f" this branch fills only {s3.AL_RIN_CM:.1f}..{THIN_SHELL_ROUT_CM:.1f} cm and leaves the outside clearance empty."
        )

    for vol in volumes:
        shape_lines, final_shape = s3.shape_defs(vol)
        lines.extend(shape_lines)
        lines.extend(
            [
                f"// Volume {vol.name}; kind={vol.shape_kind}; role={vol.role}; volume_cm3={s3.fmt(vol.volume_cm3)}; mass_kg={s3.fmt(vol.mass_kg)}",
                f"Volume {vol.name}",
                f"{vol.name}.Material {vol.material}",
                f"{vol.name}.Visibility 1",
                f"{vol.name}.Shape {final_shape}",
                f"{vol.name}.Position 0 0 {s3.fmt(vol.zcenter)}",
                f"{vol.name}.Mother InstrumentFrame",
                "",
            ]
        )
    lines.append(f"// END GEOOPT_{variant.key.upper()}_PATCH")
    geo.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")

    (work_dir / f"{variant.key}_remove_counts.json").write_text(
        json.dumps({"removed_geo_volume_blocks": remove_counts}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return remove_counts


def append_variant_det(work_dir: Path, geometry_dir: Path, variant: Variant, volumes: list) -> dict[str, int]:
    det = geometry_dir / f"{STEM}.det"
    text = det.read_text(encoding="utf-8")
    text, remove_counts = s3.remove_detector_blocks(text, s3.REMOVED_VOLUMES)
    marker = f"BEGIN GEOOPT_{variant.key.upper()}_DET"
    if marker in text:
        raise RuntimeError(f"{variant.key} detector patch already present in {det}")

    lines = [
        "",
        f"// {marker}",
        "// Scorers for the variant replacement scintillator/wrapper/mechanical shell package.",
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
                f"{sd}.TriggerThreshold {s3.fmt(vol.trigger_threshold)}",
            ]
        )
        if vol.trigger_threshold >= 1.0:
            lines.append(f"{sd}.NoiseThresholdEqualsTriggerThreshold true")
        lines.extend(
            [
                f"{sd}.EnergyResolution Gauss {s3.fmt(vol.trigger_threshold)} {s3.fmt(vol.trigger_threshold)} 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    lines.append(f"// END GEOOPT_{variant.key.upper()}_DET")
    det.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")

    (work_dir / f"{variant.key}_det_remove_counts.json").write_text(
        json.dumps({"removed_detector_blocks": remove_counts}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return remove_counts


def write_overlap_source(geometry_dir: Path, variant: Variant) -> Path:
    setup = geometry_dir / f"{STEM}.geo.setup"
    overlap_source = geometry_dir / f"overlap_check_{variant.key}.source"
    overlap_source.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {setup}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                f"Minimum.FileName            /tmp/DelMe_geoopt_{variant.key}_overlap",
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
    return overlap_source


def write_readme_and_manifest(work_dir: Path, geometry_dir: Path, variant: Variant, volumes: list, overlap_source: Path) -> None:
    manifest_path = work_dir / f"geoopt_{variant.key}_geometry_manifest.json"
    setup = geometry_dir / f"{STEM}.geo.setup"
    geo = geometry_dir / f"{STEM}.geo"
    det = geometry_dir / f"{STEM}.det"

    mass_summary = {
        "scintillator": sum(v.mass_kg for v in volumes if v.material == variant.scintillator_material),
        "kapton": sum(v.mass_kg for v in volumes if v.material == "Kapton"),
        "aluminium": sum(v.mass_kg for v in volumes if v.material == "Aluminium"),
        "w": sum(v.mass_kg for v in volumes if v.material == "W"),
    }
    clearance = None
    if variant.shell == "w2_al3":
        clearance = {
            "side_outer_gap_cm": [THIN_SHELL_ROUT_CM, s3.AL_ROUT_CM],
            "bottom_outer_gap_z_cm": [s3.BOTTOM_AL_ZMIN_CM, s3.BOTTOM_AL_ZMAX_CM - W_THICKNESS_CM - AL_THIN_THICKNESS_CM],
            "top_outer_gap_z_cm": [s3.TOP_AL_ZMIN_CM + W_THICKNESS_CM + AL_THIN_THICKNESS_CM, s3.TOP_AL_ZMAX_CM],
            "note": "The old S3 8 mm Al shell footprint is not refilled after replacing it with 2 mm W + 3 mm Al.",
        }

    manifest = {
        "status": variant.status,
        "variant": variant.key,
        "description": variant.description,
        "base_recipe": rel(S3_BUILDER),
        "base_geometry_input": rel(s3.S2B_GEOM / f"{STEM}.geo.setup"),
        "generated_geometry": rel(setup),
        "scope": "Geometry-only S3-derived branch.  No source cards or transport/response products are changed.",
        "unchanged": [
            "S2b BPE cryostat shell",
            "S2b plastic scintillator cryostat shell",
            "S3 scintillator/Kapton radial and axial placement unless explicitly changed by material",
            "source sphere center and radius",
            "side-window signal aperture location and half-widths",
            "top service opening radius",
            "NF2 support and pump-line relief scheme",
        ],
        "detector_trigger_note": "Native detector trigger thresholds are inherited from S3: full-wrap scintillator 80 keV, wrapper/mechanical scorer volumes 0.001 keV.",
        "new_volumes": [
            {
                "name": vol.name,
                "material": vol.material,
                "shape_kind": vol.shape_kind,
                "r_inner_cm": vol.rin,
                "r_outer_cm": vol.rout,
                "z_min_cm": vol.zmin,
                "z_max_cm": vol.zmax,
                "mass_kg_pre_relief": vol.mass_kg,
                "detector_scorer": vol.detector,
                "trigger_threshold_keV": vol.trigger_threshold,
                "nf2_support_relief": vol.nf2_relief,
                "pump_line_relief": vol.pump_line_relief,
                "role": vol.role,
            }
            for vol in volumes
        ],
        "mass_summary_kg_pre_relief": mass_summary,
        "thin_shell_clearance": clearance,
        "removed_local_volumes": s3.REMOVED_VOLUMES,
        "outputs": {
            "geometry_dir": rel(geometry_dir),
            "geometry_setup": rel(setup),
            "geometry_body": rel(geo),
            "detector_map": rel(det),
            "materials": rel(geometry_dir / "Materials_DEMO2_DR_v3p5.geo"),
            "overlap_source": rel(overlap_source),
        },
        "validation_status": "Generated and statically checked by builder; cosima overlap/load is an external post-generation check and is not run by the builder.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    rows = "\n".join(
        f"| `{v.name}` | `{v.material}` | {v.rin:.2f}--{v.rout:.2f} | {v.zmin:.2f}..{v.zmax:.2f} | {v.mass_kg:.3f} | {v.role} |"
        for v in volumes
    )
    clearance_note = ""
    if clearance:
        clearance_note = (
            "\nFor the W+Al shell, the S3 shell inner faces are retained.  The replacement fills only "
            f"`{s3.AL_RIN_CM:.1f}..{THIN_SHELL_ROUT_CM:.1f} cm` on the side instead of the old "
            f"`{s3.AL_RIN_CM:.1f}..{s3.AL_ROUT_CM:.1f} cm`; the remaining outside clearance is left empty.\n"
        )

    (work_dir / "README.md").write_text(
        f"""# Geometry Optimization Draft: {variant.title}

Status: `{variant.status}`

{variant.description}

This is derived from the S3 CsI-barrel geometry recipe.  The branch is geometry
only: source cards, run directories, detector-response products, Mass_model_511
authority files, and existing S3 products are not modified.

## Boundary

- S2b BPE and plastic cryostat-following shells are unchanged.
- S3 side-window aperture, top service opening, NF2 reliefs, and pump-line
  relief treatment are retained.
- Native detector trigger thresholds are inherited from S3.
{clearance_note}
## New Replacement Volumes

| Volume | Material | r cm | z cm | Mass kg pre-relief | Role |
|---|---|---:|---:|---:|---|
{rows}

## Generated Files

- Geometry setup: `{rel(setup)}`
- Geometry body: `{rel(geo)}`
- Detector map: `{rel(det)}`
- Manifest: `{rel(manifest_path)}`
- Overlap source card: `{rel(overlap_source)}`

## Validation

The builder generated the files and ran static text checks.  The builder does
not run cosima overlap/load checks; record any separate post-generation cosima
checks in this branch README/manifest.  No transport, Step05, or Step06--08
product is generated by this geometry-only builder.
""",
        encoding="utf-8",
    )


def static_check(geometry_dir: Path, variant: Variant, volumes: list) -> list[str]:
    geo_text = (geometry_dir / f"{STEM}.geo").read_text(encoding="utf-8")
    det_text = (geometry_dir / f"{STEM}.det").read_text(encoding="utf-8")
    problems: list[str] = []

    for vol in volumes:
        if f"Volume {vol.name}\n" not in geo_text:
            problems.append(f"missing geo volume {vol.name}")
        if f"{vol.name}.Material {vol.material}" not in geo_text:
            problems.append(f"missing material line for {vol.name}")
        if vol.detector and f"{vol.name}_SD.DetectorVolume {vol.name}" not in det_text:
            problems.append(f"missing detector scorer for {vol.name}")

    if variant.scintillator_material == "BGO" and f"BGO_{variant.key.upper()}_FullWrap" not in geo_text:
        problems.append("BGO full-wrap volumes not found")
    if variant.shell == "w2_al3":
        if f"Outer_W_{variant.key.upper()}_" not in geo_text:
            problems.append("W shell volumes not found")
        if "_Mechanical_SideShell_WindowCut_8mm.Material Aluminium" in geo_text:
            problems.append("old variant-specific 8mm Al shell unexpectedly present")

    return problems


def build_variant(variant: Variant) -> dict:
    work_dir = GEOOPT / variant.directory
    geometry_dir = work_dir / "geometry"
    work_dir.mkdir(parents=True, exist_ok=True)
    copy_geometry_inputs(geometry_dir)
    volumes = variant_volumes(variant)
    append_variant_geo(work_dir, geometry_dir, variant, volumes)
    append_variant_det(work_dir, geometry_dir, variant, volumes)
    overlap_source = write_overlap_source(geometry_dir, variant)
    write_readme_and_manifest(work_dir, geometry_dir, variant, volumes, overlap_source)
    problems = static_check(geometry_dir, variant, volumes)
    if problems:
        raise RuntimeError(f"{variant.key} static check failed: {problems}")
    return {
        "variant": variant.key,
        "status": variant.status,
        "geometry": rel(geometry_dir / f"{STEM}.geo.setup"),
        "volume_count": len(volumes),
        "scintillator_material": variant.scintillator_material,
        "shell": variant.shell,
    }


def main() -> int:
    results = [build_variant(variant) for variant in VARIANTS]
    print(json.dumps({"status": "PASS_S3C_C0_REBUILD_GENERATED", "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
