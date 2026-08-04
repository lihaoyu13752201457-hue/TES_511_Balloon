#!/usr/bin/env python3
"""Build the preregistered O8 fallback by wrapping the audited O9 builder core.

The shared 42_ builder supplies target stripping, retained-file copying, shape
generation, reference checks, canonical static diffing, and overlap hash
pinning.  This wrapper binds the independent 43_ output tree and the O8 profile:
the byte-identical C0 side BGO 40 mm block, bottom 30 mm, top 10 mm, no outer
W2 shell, unchanged Al3 and Kapton.  It never writes into the 42_ package.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
GEOOPT = ROOT / "engineering/geometry_optimization_20260704"
SHARED_BUILDER = (
    GEOOPT
    / "42_geoopt_s3d_lightweight_20260712/code/build_s3d_geometry.py"
)

STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEOMETRY = WORK / "geometry"
DATA = WORK / "data"
GEO = GEOMETRY / f"{STEM}.geo"
DET = GEOMETRY / f"{STEM}.det"
SETUP = GEOMETRY / f"{STEM}.geo.setup"
OVERLAP_SOURCE = GEOMETRY / "overlap_check_s3d_o8.source"
OVERLAP_SUMMARY = DATA / "cosima_overlap_s3d_o8_summary.json"
MANIFEST = DATA / "s3d_o8_geometry_manifest.json"
MASS_LEDGER = DATA / "s3d_o8_mass_ledger.json"
DIFF_AUDIT = DATA / "s3c_to_s3d_o8_static_diff_summary.json"
DECISION_EVIDENCE = DATA / "o8_fallback_decision_evidence.json"
README = WORK / "README.md"

STATUS = "S3D_O8_FALLBACK_GEOMETRY_GENERATED_PENDING_COSIMA_OVERLAP"
VALIDATED_STATUS = "S3D_O8_FALLBACK_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"
sys.dont_write_bytecode = True
PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O8_FALLBACK_MINPATCH"
PATCH_END = "// END GEOOPT_S3D_O8_FALLBACK_MINPATCH"
DET_PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O8_FALLBACK_MINPATCH_DET"
DET_PATCH_END = "// END GEOOPT_S3D_O8_FALLBACK_MINPATCH_DET"


def load_shared_builder():
    spec = importlib.util.spec_from_file_location(
        "s3d_o8_shared_geometry_builder", SHARED_BUILDER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load shared builder: {SHARED_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared_builder()


def configure_shared_paths() -> None:
    """Redirect every shared-builder output before any mutating function runs."""
    shared.WORK = WORK
    shared.CODE_DIR = WORK / "code"
    shared.GEOMETRY_DIR = GEOMETRY
    shared.DATA_DIR = DATA
    shared.GEO = GEO
    shared.DET = DET
    shared.SETUP = SETUP
    shared.OVERLAP_SOURCE = OVERLAP_SOURCE
    shared.OVERLAP_SUMMARY = OVERLAP_SUMMARY
    shared.MANIFEST = MANIFEST
    shared.MASS_LEDGER = MASS_LEDGER
    shared.DIFF_AUDIT = DIFF_AUDIT
    shared.README = README
    shared.STATUS = STATUS
    shared.VALIDATED_STATUS = VALIDATED_STATUS
    shared.PATCH_BEGIN = PATCH_BEGIN
    shared.PATCH_END = PATCH_END
    shared.DET_PATCH_BEGIN = DET_PATCH_BEGIN
    shared.DET_PATCH_END = DET_PATCH_END
    # Side40 is not a target: O8 retains its original C0 volume/scorer byte for
    # byte.  Only bottom40, top40, and the three outer W2 blocks are replaced.
    shared.TARGET_OLD = shared.OLD_BGO[1:] + shared.OLD_W
    shared.UNCHANGED_TARGET_VOLUMES = (
        [shared.OLD_BGO[0]] + shared.UNCHANGED_KAPTON + shared.UNCHANGED_AL
    )


def new_bgo_volumes() -> list:
    # Cavity-side faces and all inherited relief logic are frozen to S3c-C0.
    return [
        shared.s3.S3Volume(
            name="BGO_S3D_O8_FullWrap_BottomCap_30mm",
            material="BGO",
            rin=0.0,
            rout=25.2,
            zmin=-22.4,
            zmax=-19.4,
            density=7.13,
            role="3 cm BGO active bottom cap; C0 cavity-side face and NF2 reliefs retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        shared.s3.S3Volume(
            name="BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
            material="BGO",
            rin=20.9,
            rout=25.2,
            zmin=40.9,
            zmax=41.9,
            density=7.13,
            role="1 cm BGO active top annulus; C0 cavity-side face, service opening, and NF2 reliefs retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def append_geo_patch(volumes: list) -> dict[str, int]:
    text = GEO.read_text(encoding="utf-8")
    if PATCH_BEGIN in text:
        raise RuntimeError("O8 patch already present before target stripping")
    stripped, counts = shared.strip_named_geo_lines(text, shared.TARGET_OLD)
    if any(count <= 0 for count in counts.values()):
        raise RuntimeError(f"failed to remove every target C0 definition: {counts}")
    lines = [
        "",
        PATCH_BEGIN,
        f"// Status: {STATUS}",
        "// Exact-copy S3c-C0 base; the original side40 block is untouched, bottom/top become 30/10 mm, and only outer W2 is removed.",
        "// Al3 and Kapton retain their original IDs, placements, shapes, materials, and detector scorers.",
    ]
    for volume in volumes:
        shape_lines, final_shape = shared.s3.shape_defs(volume)
        lines.extend(shape_lines)
        lines.extend(
            [
                (
                    f"// Volume {volume.name}; kind={volume.shape_kind}; "
                    f"role={volume.role}; volume_cm3={shared.s3.fmt(volume.volume_cm3)}; "
                    f"mass_kg_pre_relief={shared.s3.fmt(volume.mass_kg)}"
                ),
                f"Volume {volume.name}",
                f"{volume.name}.Material {volume.material}",
                f"{volume.name}.Visibility 1",
                f"{volume.name}.Shape {final_shape}",
                f"{volume.name}.Position 0 0 {shared.s3.fmt(volume.zcenter)}",
                f"{volume.name}.Mother InstrumentFrame",
                "",
            ]
        )
    lines.append(PATCH_END)
    GEO.write_text(
        stripped.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8"
    )
    return counts


def append_det_patch(volumes: list) -> dict[str, int]:
    text = DET.read_text(encoding="utf-8")
    if DET_PATCH_BEGIN in text:
        raise RuntimeError("O8 detector patch already present")
    stripped, counts = shared.s3.remove_detector_blocks(text, shared.TARGET_OLD)
    if any(count != 1 for count in counts.values()):
        raise RuntimeError(f"target C0 detector removal mismatch: {counts}")
    lines = [
        "",
        DET_PATCH_BEGIN,
        "// O8 BGO scorers retain the native C0 80 keV definition; the frozen analysis veto remains 50 keV.",
    ]
    for volume in volumes:
        sd = f"{volume.name}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {volume.name}",
                f"{sd}.DetectorVolume {volume.name}",
                f"{sd}.TriggerThreshold {shared.s3.fmt(volume.trigger_threshold)}",
                f"{sd}.NoiseThresholdEqualsTriggerThreshold true",
                f"{sd}.EnergyResolution Gauss {shared.s3.fmt(volume.trigger_threshold)} {shared.s3.fmt(volume.trigger_threshold)} 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    lines.append(DET_PATCH_END)
    DET.write_text(
        stripped.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8"
    )
    return counts


def write_overlap_source() -> None:
    OVERLAP_SOURCE.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {SETUP.resolve()}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                "Minimum.FileName            /tmp/DelMe_geoopt_s3d_o8_overlap",
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


def write_mass_and_manifest(volumes: list, audit: dict) -> tuple[dict, dict]:
    retained_side_mass = (
        math.pi * (25.2**2 - 21.2**2) * (40.9 - (-19.4)) * 7.13 / 1000.0
    )
    bgo = {shared.OLD_BGO[0]: retained_side_mass}
    bgo.update({volume.name: volume.mass_kg for volume in volumes})
    bgo_total = sum(bgo.values())
    total = (
        bgo_total
        + shared.BASELINE_COMPONENT_MASS_KG["al3_shell"]
        + shared.BASELINE_COMPONENT_MASS_KG["kapton"]
    )
    saved = shared.BASELINE_MASS_KG - total
    ledger = {
        "status": "PRE_RELIEF_GEOMETRY_LEDGER_NOT_STRUCTURAL_QUALIFICATION",
        "convention": (
            "shield-package axisymmetric analytic mass before window/NF2/pump "
            "relief subtraction, matching retained C0 bookkeeping; not whole-"
            "instrument or structural mass"
        ),
        "density_bgo_g_cm3": 7.13,
        "baseline_s3c_c0_shield_package_mass_kg": shared.BASELINE_MASS_KG,
        "o8_components_kg": {
            "bgo": bgo,
            "bgo_total": bgo_total,
            "retained_side40_exact_axisymmetric_kg": retained_side_mass,
            "retained_side40_bookkeeping_rounded_kg": shared.BASELINE_COMPONENT_MASS_KG["bgo_side40"],
            "outer_w2_shell_kg": 0.0,
            "al3_unchanged": shared.BASELINE_COMPONENT_MASS_KG["al3_shell"],
            "kapton_unchanged": shared.BASELINE_COMPONENT_MASS_KG["kapton"],
        },
        "s3d_shield_package_total_kg": total,
        "o8_shield_package_total_kg": total,
        "mass_saved_kg": saved,
        "mass_reduction_fraction": saved / shared.BASELINE_MASS_KG,
    }
    MASS_LEDGER.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    overlap = shared.overlap_validation_state()
    evidence_state = {
        "path": shared.rel(DECISION_EVIDENCE),
        "exists": DECISION_EVIDENCE.exists(),
    }
    if DECISION_EVIDENCE.exists():
        evidence_state["sha256"] = shared.sha256(DECISION_EVIDENCE)
        evidence_state["status"] = json.loads(
            DECISION_EVIDENCE.read_text(encoding="utf-8")
        ).get("status")
    manifest = {
        "status": VALIDATED_STATUS if overlap["status"] == "PASS" else STATUS,
        "variant": "s3d_o8_side40_bottom30_top10_no_outer_w2_al3",
        "base_authority": shared.rel(
            shared.BASE_GEOMETRY_DIR / f"{STEM}.geo.setup"
        ),
        "generated_geometry": shared.rel(SETUP),
        "shared_builder_authority": {
            "path": shared.rel(SHARED_BUILDER),
            "sha256": shared.sha256(SHARED_BUILDER),
            "reused_functions": [
                "copy_core_geometry",
                "shape_defs via retained _s3c_base_recipe",
                "strip_named_geo_lines",
                "static_diff_audit",
                "overlap_validation_state",
            ],
        },
        "decision_evidence": evidence_state,
        "design_decision": (
            "O8 is the preregistered, data-driven fallback after O9 exceeded the "
            "dominant W2 gate. O9 atmospheric final-W2 survivors are 17/18 side "
            "entries (C0: 5/6) and their event count is 3x C0, so O8 restores "
            "the side BGO to 40 mm while retaining bottom/top mass reductions."
        ),
        "physical_changes": [
            "BGO bottom 40 to 30 mm, cavity-side z fixed at -19.4 cm",
            "BGO top annulus 40 to 10 mm, cavity-side z fixed at 40.9 cm",
            "remove exactly three outer 2 mm W mechanical-shell volumes and scorers",
        ],
        "unchanged": [
            "BGO side40 volume ID, full geometry block, and detector scorer block",
            "Al3 and Kapton IDs, placements, shapes, materials, and scorers",
            "side window, pump-line relief, top service opening, and NF2 relief scheme",
            "TES/cryostat/BPE/plastic geometry, InstrumentFrame, materials, response, and thresholds",
            "source sphere center and radius",
        ],
        "new_bgo_volumes": [
            {
                "name": volume.name,
                "r_inner_cm": volume.rin,
                "r_outer_cm": volume.rout,
                "z_min_cm": volume.zmin,
                "z_max_cm": volume.zmax,
                "mass_kg_pre_relief": volume.mass_kg,
                "trigger_threshold_keV": volume.trigger_threshold,
            }
            for volume in volumes
        ],
        "retained_bgo_volumes": [
            {
                "name": shared.OLD_BGO[0],
                "r_inner_cm": 21.2,
                "r_outer_cm": 25.2,
                "z_min_cm": -19.4,
                "z_max_cm": 40.9,
                "mass_kg_pre_relief_independent": retained_side_mass,
                "retained_geo_and_det_blocks_byte_identical": True,
            }
        ],
        "mass_ledger": shared.rel(MASS_LEDGER),
        "static_diff_audit": shared.rel(DIFF_AUDIT),
        "static_diff_status": audit["status"],
        "overlap_source": shared.rel(OVERLAP_SOURCE),
        "overlap_validation": overlap,
        "structural_model_boundary": {
            "bgo_to_retained_kapton_clearance_cm": {
                "side": 0.17,
                "bottom": 1.17,
                "top": 3.17,
            },
            "retained_kapton_to_al_clearance_cm": {
                "side": 0.30,
                "bottom": 0.30,
                "top": 0.30,
            },
            "interpretation": (
                "Byte-identical external Kapton/Al creates deliberate asymmetric "
                "service/vacuum gaps. This is a minimal-delta transport geometry, "
                "not a support/manufacturing or structural qualification."
            ),
        },
        "threshold_boundary": {
            "native_bgo_trigger_keV": 80.0,
            "frozen_screening_active_veto_keV": 50.0,
            "note": "Future C0/O8 transport must freeze the same effective selection.",
        },
        "production_boundary": (
            "No prompt, atmospheric, focused-signal, buildup, activation, or "
            "delayed production is launched by this package."
        ),
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return ledger, overlap


def write_readme(ledger: dict, overlap: dict) -> None:
    package_status = VALIDATED_STATUS if overlap["status"] == "PASS" else STATUS
    README.write_text(
        f"""# S3d O8 fallback geometry — side40 / bottom30 / top10 / no outer W2

Status: `{package_status}`

This package is the preregistered fallback from the retained S3c-C0 geometry.
It is a strict minimal delta: retain the original 40 mm side BGO volume and
scorer blocks byte-for-byte, thin bottom BGO to 30 mm,
thin the top annulus to 10 mm, remove only the three outer W2 shell volumes and
scorers, and preserve Al3, Kapton, and every other geometry/response definition.
The `42_` package is read as shared code/evidence authority; no geometry,
manifest, simulation, or other package output is written there.

## Why O8 is the data-driven fallback

The O9 matched screening gives `e+ + n = 0.002710741516565003 cps` and
atmospheric-511 `= 0.003499800705793143 cps`, for
`0.006210542222358145 cps`.  This exceeds the preregistered `0.0052 cps`
dominant-W2 limit, so O9 fails that transport gate.

Using the retained `IA INIT` parser and `classify_entry` implementation, the
O9 atmospheric final-W2 survivors classify as `17/18 side`, `1/18 bottom`, and
`0/18 top`; C0 classifies as `5/6 side`, `1/6 bottom`, and `0/6 top`.  The O9
atmospheric survivor count is exactly `3x` C0 (normalized-rate ratio
`2.999270875`).  The failure is therefore strongly side-dominated.  O8 restores
the side BGO to 40 mm while keeping bottom/top thinning as the remaining mass
lever.  This is a design inference, not an O8 performance result; matched O8
transport is still required.  Reproducible event-level evidence:
`{shared.rel(DECISION_EVIDENCE)}`.

## Authorized geometry delta

- Side BGO: original `BGO_S3C_FullWrap_SideShell_WindowCut_40mm` geo and
  detector blocks remain byte-identical (`r=21.2..25.2 cm`, 40 mm).
- Bottom BGO: `z=-23.4..-19.4 -> -22.4..-19.4 cm` (30 mm).
- Top BGO: `z=40.9..44.9 -> 40.9..41.9 cm` (10 mm).
- Remove exactly the three S3c outer W2 side/bottom/top volumes and scorers.
- Preserve byte-identical Al3 and Kapton blocks, aperture/service/relief scheme,
  TES/cryostat/BPE/plastic geometry, materials, thresholds, response, and R60.

## Analytic mass ledger

The pre-relief BGO/Kapton/outer-shell package is
`{ledger['o8_shield_package_total_kg']:.9f} kg`, down
`{ledger['mass_saved_kg']:.9f} kg`
(`{100.0 * ledger['mass_reduction_fraction']:.6f}%`) from the retained C0
bookkeeping baseline.  This is not whole-instrument mass and not a structural
qualification.  Unrelated retained tungsten elsewhere in the instrument is
unchanged.  Keeping the external envelope fixed leaves BGO-to-Kapton gaps of
`0.17 cm` side, `1.17 cm` bottom, and `3.17 cm` top; support/manufacturing
closure remains outside this transport-only model.

## Evidence

- Geometry: `{shared.rel(SETUP)}`
- Manifest: `{shared.rel(MANIFEST)}`
- Mass ledger: `{shared.rel(MASS_LEDGER)}`
- Static diff: `{shared.rel(DIFF_AUDIT)}`
- Independent semantic validation: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_independent_geometry_validation.json`
- Overlap source: `{shared.rel(OVERLAP_SOURCE)}`
- Overlap summary: `{shared.rel(OVERLAP_SUMMARY)}` (`{overlap['status']}` for current hashes)

## Claim boundary

The builder and one-event Cosima smoke establish only geometry loadability,
overlap cleanliness at the configured check, reference integrity, and analytic
mass bookkeeping.  This package launches no prompt, atmospheric-511, focused
signal, buildup, activation, or delayed production and makes no O8 performance
claim.
""",
        encoding="utf-8",
    )


def main() -> int:
    configure_shared_paths()
    shared.new_bgo_volumes = new_bgo_volumes
    shared.append_geo_patch = append_geo_patch
    shared.append_det_patch = append_det_patch
    shared.write_overlap_source = write_overlap_source
    shared.write_mass_and_manifest = write_mass_and_manifest
    shared.write_readme = write_readme
    return shared.main()


if __name__ == "__main__":
    raise SystemExit(main())
