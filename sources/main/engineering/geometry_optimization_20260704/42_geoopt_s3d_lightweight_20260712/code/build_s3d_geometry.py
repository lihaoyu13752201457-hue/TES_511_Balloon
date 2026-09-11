#!/usr/bin/env python3
"""Build the S3d lightweight geometry as a strict delta from retained S3c-C0.

The only physical changes are:

* BGO side, bottom, and top thicknesses: 40 mm -> 30 mm, with the cavity-side
  faces held fixed;
* removal of the three 2 mm W mechanical-shell volumes and their detector
  scorers.

All other S3c geometry text is copied from the retained 29_ package.  In
particular, the Al3 and Kapton volumes keep their original names, positions,
shapes, and detector blocks so that the non-target delta can be audited byte
for byte.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
CODE_DIR = WORK / "code"
GEOMETRY_DIR = WORK / "geometry"
DATA_DIR = WORK / "data"

GEOOPT = ROOT / "engineering/geometry_optimization_20260704"
BASE_WORK = GEOOPT / "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
BASE_GEOMETRY_DIR = BASE_WORK / "geometry"
RECIPE = (
    GEOOPT
    / "40_s3c_mainline_lightweight_review_20260710/code/_s3c_base_recipe.py"
)

STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
CORE_FILES = [
    f"{STEM}.geo.setup",
    f"{STEM}.geo",
    f"{STEM}.det",
    f"Intro_{STEM}.geo",
    "Materials_DEMO2_DR_v3p5.geo",
]

GEO = GEOMETRY_DIR / f"{STEM}.geo"
DET = GEOMETRY_DIR / f"{STEM}.det"
SETUP = GEOMETRY_DIR / f"{STEM}.geo.setup"
OVERLAP_SOURCE = GEOMETRY_DIR / "overlap_check_s3d.source"
OVERLAP_SUMMARY = DATA_DIR / "cosima_overlap_s3d_summary.json"
MANIFEST = DATA_DIR / "s3d_geometry_manifest.json"
MASS_LEDGER = DATA_DIR / "s3d_mass_ledger.json"
DIFF_AUDIT = DATA_DIR / "s3c_to_s3d_static_diff_summary.json"
README = WORK / "README.md"

STATUS = "S3D_O9_GEOMETRY_GENERATED_PENDING_COSIMA_OVERLAP"
VALIDATED_STATUS = "S3D_O9_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"
BASELINE_MASS_KG = 391.1988472997
BASELINE_COMPONENT_MASS_KG = {
    "bgo_side40": 250.688659,
    "bgo_bottom40": 56.8984552,
    "bgo_top40": 17.7610556,
    "w2_shell": 53.87667474,
    "al3_shell": 11.393391653,
    "kapton": 0.5806111067,
}

OLD_BGO = [
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3C_FullWrap_BottomCap_40mm",
    "BGO_S3C_FullWrap_TopAnnulus_40mm",
]
OLD_W = [
    "Outer_W_S3C_BGO_Mechanical_SideShell_WindowCut_2mm",
    "Outer_W_S3C_BGO_Mechanical_BottomCap_2mm",
    "Outer_W_S3C_BGO_Mechanical_TopAnnulus_2mm",
]
TARGET_OLD = OLD_BGO + OLD_W

UNCHANGED_KAPTON = [
    "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
]
UNCHANGED_AL = [
    "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm",
    "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
    "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
]
UNCHANGED_TARGET_VOLUMES = UNCHANGED_KAPTON + UNCHANGED_AL

PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O9_MINPATCH"
PATCH_END = "// END GEOOPT_S3D_O9_MINPATCH"
DET_PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O9_MINPATCH_DET"
DET_PATCH_END = "// END GEOOPT_S3D_O9_MINPATCH_DET"


def load_recipe():
    spec = importlib.util.spec_from_file_location("s3d_s3c_recipe", RECIPE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load retained recipe: {RECIPE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


s3 = load_recipe()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def overlap_validation_state() -> dict:
    """Accept overlap evidence only when it is PASS and hash-pinned to this build."""
    state = {
        "status": "PENDING",
        "summary": rel(OVERLAP_SUMMARY),
        "hash_match": False,
    }
    if not OVERLAP_SUMMARY.exists():
        return state
    try:
        summary = json.loads(OVERLAP_SUMMARY.read_text(encoding="utf-8"))
        hashes = summary["files"]
        matches = {
            "source": hashes["source"]["sha256"] == sha256(OVERLAP_SOURCE),
            "setup": hashes["setup"]["sha256"] == sha256(SETUP),
            "geo": hashes["geo"]["sha256"] == sha256(GEO),
            "det": hashes["det"]["sha256"] == sha256(DET),
        }
        state.update(
            {
                "status": "PASS"
                if summary.get("status") == "PASS" and all(matches.values())
                else "STALE_OR_FAILED",
                "reported_status": summary.get("status"),
                "hash_match": all(matches.values()),
                "hashes": matches,
            }
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        state.update({"status": "INVALID_SUMMARY", "error": str(exc)})
    return state


def copy_core_geometry() -> None:
    GEOMETRY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in CORE_FILES:
        source = BASE_GEOMETRY_DIR / name
        if not source.exists():
            raise RuntimeError(f"missing retained S3c core geometry file: {source}")
        shutil.copy2(source, GEOMETRY_DIR / name)


def new_bgo_volumes() -> list:
    # O9: uniform 30 mm BGO.  The cavity-side faces are identical to S3c-C0.
    return [
        s3.S3Volume(
            name="BGO_S3D_FullWrap_SideShell_WindowCut_30mm",
            material="BGO",
            rin=21.2,
            rout=24.2,
            zmin=-19.4,
            zmax=40.9,
            density=7.13,
            role="3 cm BGO active side shell; S3c inner face, side window, pump-line relief, and NF2 reliefs retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="side_window",
            nf2_relief=True,
            pump_line_relief=True,
        ),
        s3.S3Volume(
            name="BGO_S3D_FullWrap_BottomCap_30mm",
            material="BGO",
            rin=0.0,
            rout=25.2,
            zmin=-22.4,
            zmax=-19.4,
            density=7.13,
            role="3 cm BGO active bottom cap; S3c cavity-side face and NF2 reliefs retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
        s3.S3Volume(
            name="BGO_S3D_FullWrap_TopAnnulus_30mm",
            material="BGO",
            rin=20.9,
            rout=25.2,
            zmin=40.9,
            zmax=43.9,
            density=7.13,
            role="3 cm BGO active top annulus; S3c cavity-side face, service opening, and NF2 reliefs retained",
            detector=True,
            trigger_threshold=80.0,
            shape_kind="pcon",
            nf2_relief=True,
        ),
    ]


def target_line(line: str, names: list[str]) -> bool:
    stripped = line.strip()
    for name in names:
        if stripped.startswith(f"// Volume {name}"):
            return True
        if stripped.startswith(name + ".") or stripped.startswith(name + "_"):
            return True
        fields = stripped.split()
        if len(fields) >= 2 and fields[0] == "Volume" and fields[1] == name:
            return True
        if len(fields) >= 2 and fields[0] == "Orientation" and fields[1].startswith(name + "_"):
            return True
        if len(fields) >= 3 and fields[0] == "Shape" and fields[2].startswith(name + "_"):
            return True
    return False


def strip_named_geo_lines(text: str, names: list[str]) -> tuple[str, dict[str, int]]:
    counts = {name: 0 for name in names}
    kept: list[str] = []
    for line in text.splitlines():
        matched = False
        for name in names:
            if target_line(line, [name]):
                counts[name] += 1
                matched = True
                break
        if not matched:
            kept.append(line)
    return "\n".join(kept).rstrip() + "\n", counts


def append_geo_patch(volumes: list) -> dict[str, int]:
    base_text = GEO.read_text(encoding="utf-8")
    if PATCH_BEGIN in base_text:
        raise RuntimeError("S3d patch already present before target stripping")
    stripped, counts = strip_named_geo_lines(base_text, TARGET_OLD)
    if any(count <= 0 for count in counts.values()):
        raise RuntimeError(f"failed to remove every target S3c geometry definition: {counts}")

    lines = [
        "",
        PATCH_BEGIN,
        f"// Status: {STATUS}",
        "// Exact-copy S3c-C0 base; only BGO40->BGO30 and removal of the three W2 shell volumes are authorized.",
        "// Al3 and Kapton keep their original S3C volume IDs, placements, shapes, materials, and detector scorers.",
    ]
    for volume in volumes:
        shape_lines, final_shape = s3.shape_defs(volume)
        lines.extend(shape_lines)
        lines.extend(
            [
                (
                    f"// Volume {volume.name}; kind={volume.shape_kind}; role={volume.role}; "
                    f"volume_cm3={s3.fmt(volume.volume_cm3)}; mass_kg_pre_relief={s3.fmt(volume.mass_kg)}"
                ),
                f"Volume {volume.name}",
                f"{volume.name}.Material {volume.material}",
                f"{volume.name}.Visibility 1",
                f"{volume.name}.Shape {final_shape}",
                f"{volume.name}.Position 0 0 {s3.fmt(volume.zcenter)}",
                f"{volume.name}.Mother InstrumentFrame",
                "",
            ]
        )
    lines.append(PATCH_END)
    GEO.write_text(stripped.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return counts


def append_det_patch(volumes: list) -> dict[str, int]:
    text = DET.read_text(encoding="utf-8")
    if DET_PATCH_BEGIN in text:
        raise RuntimeError("S3d detector patch already present")
    stripped, counts = s3.remove_detector_blocks(text, TARGET_OLD)
    if any(count != 1 for count in counts.values()):
        raise RuntimeError(f"target S3c detector removal count mismatch: {counts}")

    lines = [
        "",
        DET_PATCH_BEGIN,
        "// S3d BGO scorers retain the S3c native 80 keV definition; analysis-level 50 keV veto is a separate frozen selection.",
    ]
    for volume in volumes:
        sd = f"{volume.name}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {volume.name}",
                f"{sd}.DetectorVolume {volume.name}",
                f"{sd}.TriggerThreshold {s3.fmt(volume.trigger_threshold)}",
                f"{sd}.NoiseThresholdEqualsTriggerThreshold true",
                f"{sd}.EnergyResolution Gauss {s3.fmt(volume.trigger_threshold)} {s3.fmt(volume.trigger_threshold)} 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    lines.append(DET_PATCH_END)
    DET.write_text(stripped.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
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
                "Minimum.FileName            /tmp/DelMe_geoopt_s3d_o9_overlap",
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


def block(text: str, name: str) -> str:
    pattern = re.compile(
        rf"(?:^// Volume {re.escape(name)}[^\n]*\n)?^Volume {re.escape(name)}\n.*?^{re.escape(name)}\.Mother [^\n]+\n",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"unable to extract volume block: {name}")
    return match.group(0)


def det_block(text: str, volume_name: str) -> str:
    sd = re.escape(f"{volume_name}_SD")
    pattern = re.compile(rf"^Scintillator {sd}\n.*?(?=\n\s*\n|^Scintillator |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"unable to extract detector block: {volume_name}")
    return match.group(0)


def remove_patch(text: str, begin: str, end: str) -> str:
    pattern = re.compile(rf"\n?^{re.escape(begin)}$.*?^{re.escape(end)}$\n?", re.MULTILINE | re.DOTALL)
    cleaned, count = pattern.subn("\n", text)
    if count != 1:
        raise RuntimeError(f"patch marker removal count mismatch for {begin}: {count}")
    return cleaned


def canonical_nonempty(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()) + "\n"


def declarations(text: str, pattern: str) -> list[str]:
    return re.findall(pattern, text, flags=re.MULTILINE)


def duplicate_names(text: str, kind: str) -> list[str]:
    patterns = {
        "volume": r"^Volume\s+(\S+)",
        "shape": r"^Shape\s+\S+\s+(\S+)",
        "orientation": r"^Orientation\s+(\S+)",
        "scintillator": r"^Scintillator\s+(\S+)",
    }
    names = declarations(text, patterns[kind])
    return sorted(name for name, count in Counter(names).items() if count > 1)


def static_diff_audit(volumes: list, geo_remove_counts: dict, det_remove_counts: dict) -> dict:
    base_geo = (BASE_GEOMETRY_DIR / f"{STEM}.geo").read_text(encoding="utf-8")
    base_det = (BASE_GEOMETRY_DIR / f"{STEM}.det").read_text(encoding="utf-8")
    new_geo = GEO.read_text(encoding="utf-8")
    new_det = DET.read_text(encoding="utf-8")

    base_geo_canon = canonical_nonempty(strip_named_geo_lines(base_geo, TARGET_OLD)[0])
    new_geo_without_patch = remove_patch(new_geo, PATCH_BEGIN, PATCH_END)
    new_geo_canon = canonical_nonempty(strip_named_geo_lines(new_geo_without_patch, TARGET_OLD)[0])

    base_det_canon = canonical_nonempty(s3.remove_detector_blocks(base_det, TARGET_OLD)[0])
    new_det_canon = canonical_nonempty(remove_patch(new_det, DET_PATCH_BEGIN, DET_PATCH_END))

    unchanged_blocks = {}
    for name in UNCHANGED_TARGET_VOLUMES:
        unchanged_blocks[name] = {
            "geo_identical": block(base_geo, name) == block(new_geo, name),
            "det_identical": det_block(base_det, name) == det_block(new_det, name),
        }

    volumes_declared = set(declarations(new_geo, r"^Volume\s+(\S+)"))
    sensitive_refs = set(declarations(new_det, r"^\S+\.SensitiveVolume\s+(\S+)"))
    detector_refs = set(declarations(new_det, r"^\S+\.DetectorVolume\s+(\S+)"))

    core_hashes = {}
    for name in [f"{STEM}.geo.setup", f"Intro_{STEM}.geo", "Materials_DEMO2_DR_v3p5.geo"]:
        base = BASE_GEOMETRY_DIR / name
        new = GEOMETRY_DIR / name
        core_hashes[name] = {
            "base_sha256": sha256(base),
            "new_sha256": sha256(new),
            "identical": sha256(base) == sha256(new),
        }

    new_names = [volume.name for volume in volumes]
    audit = {
        "status": "PASS" if (
            base_geo_canon == new_geo_canon
            and base_det_canon == new_det_canon
            and all(row["geo_identical"] and row["det_identical"] for row in unchanged_blocks.values())
            and all(row["identical"] for row in core_hashes.values())
            and not any(duplicate_names(new_geo, kind) for kind in ("volume", "shape", "orientation"))
            and not duplicate_names(new_det, "scintillator")
            and sensitive_refs.issubset(volumes_declared)
            and detector_refs.issubset(volumes_declared)
            and all(f"Volume {name}\n" not in new_geo for name in TARGET_OLD)
            and all(f"Scintillator {name}_SD\n" not in new_det for name in TARGET_OLD)
            and all(f"Volume {name}\n" in new_geo for name in new_names)
        ) else "FAIL",
        "base_geometry": rel(BASE_GEOMETRY_DIR / f"{STEM}.geo.setup"),
        "generated_geometry": rel(SETUP),
        "authorized_delta": {
            "remove_geo_and_det": TARGET_OLD,
            "add_geo_and_det": new_names,
            "retain_byte_identical": UNCHANGED_TARGET_VOLUMES,
        },
        "removal_line_counts": geo_remove_counts,
        "removal_detector_block_counts": det_remove_counts,
        "canonical_non_target": {
            "geo_base_sha256": sha256_text(base_geo_canon),
            "geo_new_sha256": sha256_text(new_geo_canon),
            "geo_identical": base_geo_canon == new_geo_canon,
            "det_base_sha256": sha256_text(base_det_canon),
            "det_new_sha256": sha256_text(new_det_canon),
            "det_identical": base_det_canon == new_det_canon,
        },
        "unchanged_target_blocks": unchanged_blocks,
        "unchanged_core_files": core_hashes,
        "duplicates": {
            "volumes": duplicate_names(new_geo, "volume"),
            "shapes": duplicate_names(new_geo, "shape"),
            "orientations": duplicate_names(new_geo, "orientation"),
            "scintillators": duplicate_names(new_det, "scintillator"),
        },
        "detector_reference_resolution": {
            "sensitive_volume_refs": len(sensitive_refs),
            "detector_volume_refs": len(detector_refs),
            "missing_sensitive_volumes": sorted(sensitive_refs - volumes_declared),
            "missing_detector_volumes": sorted(detector_refs - volumes_declared),
        },
        "declaration_counts": {
            "base_volumes": len(declarations(base_geo, r"^Volume\s+(\S+)")),
            "new_volumes": len(declarations(new_geo, r"^Volume\s+(\S+)")),
            "base_scintillators": len(declarations(base_det, r"^Scintillator\s+(\S+)")),
            "new_scintillators": len(declarations(new_det, r"^Scintillator\s+(\S+)")),
        },
    }
    DIFF_AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if audit["status"] != "PASS":
        raise RuntimeError(f"S3c-to-S3d static diff audit failed; inspect {DIFF_AUDIT}")
    return audit


def write_mass_and_manifest(volumes: list, audit: dict) -> tuple[dict, dict]:
    bgo = {volume.name: volume.mass_kg for volume in volumes}
    bgo_total = sum(bgo.values())
    total = bgo_total + BASELINE_COMPONENT_MASS_KG["al3_shell"] + BASELINE_COMPONENT_MASS_KG["kapton"]
    saved = BASELINE_MASS_KG - total
    ledger = {
        "status": "PRE_RELIEF_GEOMETRY_LEDGER_NOT_STRUCTURAL_QUALIFICATION",
        "convention": "shield-package axisymmetric analytic mass before window/NF2/pump relief subtraction, matching retained S3c bookkeeping; not whole-instrument or structural mass",
        "density_bgo_g_cm3": 7.13,
        "baseline_s3c_c0_shield_package_mass_kg": BASELINE_MASS_KG,
        "s3d_components_kg": {
            "bgo": bgo,
            "bgo_total": bgo_total,
            "outer_w2_shell_kg": 0.0,
            "al3_unchanged": BASELINE_COMPONENT_MASS_KG["al3_shell"],
            "kapton_unchanged": BASELINE_COMPONENT_MASS_KG["kapton"],
        },
        "s3d_shield_package_total_kg": total,
        "mass_saved_kg": saved,
        "mass_reduction_fraction": saved / BASELINE_MASS_KG,
    }
    MASS_LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    overlap = overlap_validation_state()
    manifest = {
        "status": VALIDATED_STATUS if overlap["status"] == "PASS" else STATUS,
        "variant": "s3d_o9_uniform_bgo30_no_w_al3",
        "base_authority": rel(BASE_GEOMETRY_DIR / f"{STEM}.geo.setup"),
        "generated_geometry": rel(SETUP),
        "design_decision": (
            "O9 is the Pareto-knee candidate: it retains continuous 30 mm active BGO while removing the high-Z passive W shell. "
            "O10 saves only 8.88 kg more but thins the top active shield to 10 mm and is retained only as a later stress test."
        ),
        "physical_changes": [
            "BGO side 40 to 30 mm, inner radius fixed at 21.2 cm",
            "BGO bottom 40 to 30 mm, cavity-side z fixed at -19.4 cm",
            "BGO top annulus 40 to 30 mm, cavity-side z fixed at 40.9 cm",
            "remove three 2 mm W mechanical-shell volumes and detector scorers",
        ],
        "unchanged": [
            "Al3 and Kapton volume IDs, placements, shapes, materials, and scorers",
            "top service opening, side window, pump-line relief, and NF2 relief scheme",
            "TES/cryostat/BPE/plastic geometry, InstrumentFrame, materials, response, and thresholds",
            "source sphere center and radius",
        ],
        "threshold_boundary": {
            "native_bgo_trigger_keV": 80.0,
            "screening_active_veto_keV": 50.0,
            "note": "C0 and S3d comparisons must freeze the same effective selection. Gehrels' below-50-keV recommendation is not claimed as implemented hardware performance.",
        },
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
        "mass_ledger": rel(MASS_LEDGER),
        "static_diff_audit": rel(DIFF_AUDIT),
        "static_diff_status": audit["status"],
        "overlap_source": rel(OVERLAP_SOURCE),
        "overlap_validation": overlap,
        "structural_model_boundary": {
            "bgo_to_retained_kapton_clearance_cm": 1.17,
            "retained_kapton_to_al_clearance_cm": 0.30,
            "interpretation": "The unchanged outer envelope creates a deliberate service/vacuum gap after BGO thinning. This is a minimal-delta transport model, not a manufacturing or structural qualification.",
        },
        "promotion_guardrails": {
            "dominant_w2_subset_cps_max": 0.0052,
            "focused_signal_acceptance_loss_fraction_max": 0.02,
            "neutron_only_delayed_activity_bq_max": 57.8243,
            "full_closure_f3_central_ratio_max": 1.05,
            "full_closure_f3_95pct_upper_ratio_max": 1.10,
            "fallback_if_failed": "O8 side40/bottom30/top10/noW/Al3",
        },
        "literature_design_check": {
            "reference": "N. Gehrels, NIM A 239 (1985) 324-349, doi:10.1016/0168-9002(85)90732-6",
            "nasa_report": "https://ntrs.nasa.gov/citations/19850010602",
            "alignment": [
                "remove high-Z passive material close to the detector",
                "retain low-Z Al structural shell",
                "retain continuous active anticoincidence coverage",
                "preserve aperture geometry and segmented detector topology",
            ],
            "open_boundary": "native 80 keV versus analysis-level 50 keV active-veto threshold requires a matched-threshold systematic study",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ledger, overlap


def write_readme(ledger: dict, overlap: dict) -> None:
    package_status = VALIDATED_STATUS if overlap["status"] == "PASS" else STATUS
    README.write_text(
        f"""# S3d lightweight geometry — O9 Pareto-knee candidate

Status: `{package_status}`

This package is a strict, auditable delta from the retained S3c-C0 geometry.
The selected profile uses uniform 30 mm active BGO, removes the three 2 mm W
mechanical-shell volumes, and retains the original Al3 and Kapton package.

## Decision

The 41_ audit arithmetic is internally consistent, but it does not prove that
the lightest O10 point preserves performance: e+/n/residual were frozen and the
method calibration differs from the historical LW1 screen by a factor of 7.98.
O9 is used here because it is the Pareto knee: `{ledger['mass_saved_kg']:.3f} kg`
(`{100.0 * ledger['mass_reduction_fraction']:.2f}%`) pre-relief mass saving with
the screening proxy at +6.57% F3.  O10 saves only 8.88 kg more while thinning
the top active shield from 30 to 10 mm; it is kept as a later stress test.

## Authorized geometry delta

- BGO side: `r=21.2..25.2 -> 21.2..24.2 cm`; `z=-19.4..40.9 cm` unchanged.
- BGO bottom: `z=-23.4..-19.4 -> -22.4..-19.4 cm`; radius unchanged.
- BGO top annulus: `z=40.9..44.9 -> 40.9..43.9 cm`; radii unchanged.
- Remove the three S3c W2 side/bottom/top placements and detector scorers.
- Preserve Al3, Kapton, aperture, service opening, reliefs, TES/cryostat,
  BPE/plastic, materials, thresholds, and response definitions.

The reported mass is pre-relief analytic bookkeeping for the BGO/Kapton/outer
shell package only; it is neither whole-instrument mass nor a structural mass
qualification.  `outer_w2_shell_kg = 0` does not imply that unrelated retained
tungsten parts elsewhere in the instrument were removed.  Source:
`{rel(MASS_LEDGER)}`.

Keeping the external Kapton/Al envelope byte-identical leaves a deliberate
`1.17 cm` BGO-to-Kapton and `0.30 cm` Kapton-to-Al service/vacuum clearance on
the side, bottom, and top.  This is the frozen minimal-delta transport model;
it requires a separate support/manufacturing design before hardware use.

## Gehrels 1985 design check

The design follows the classic recommendations to minimize passive material
near the detector, prefer low-Z structural material, retain active shielding,
and avoid trading aperture/background control for passive high-Z mass.  The
paper also recommends a shield threshold well below 50 keV.  This geometry
retains the S3c native 80 keV BGO detector definition while the analysis uses a
matched 50 keV post-processing veto; that mismatch is an explicit systematic
boundary, not a claimed hardware achievement.

Reference: N. Gehrels, *Instrumental background in balloon-borne gamma-ray
spectrometers and techniques for its reduction*, NIM A 239 (1985) 324-349,
doi:10.1016/0168-9002(85)90732-6.

## Generated evidence

- Geometry: `{rel(SETUP)}`
- Manifest: `{rel(MANIFEST)}`
- Mass ledger: `{rel(MASS_LEDGER)}`
- S3c-to-S3d static diff audit: `{rel(DIFF_AUDIT)}`
- Cosima overlap source: `{rel(OVERLAP_SOURCE)}`
- Cosima overlap summary: `{rel(OVERLAP_SUMMARY)}` (`{overlap['status']}` for the current geometry hashes)

## Required promotion gates

1. Static diff PASS, Cosima overlap/load PASS, and every source/SIM header must
   resolve to this geometry.
2. Matched e+/n/atm511 dominant W2 subset <= 0.0052 cps.
3. f10m A1 final W2 signal acceptance loss <= 2% versus S3c-C0.
4. Clean neutron-only delayed activity <= 57.8243 Bq with NUBASE, TT division,
   exact-position sampling, and provenance gates all PASS.
5. After all prompt families and delayed response are closed, central F3 <=
   1.05 times C0 and its 95% upper ratio <= 1.10; otherwise fall back to O8.

## Non-claims

- No transport or performance result is created by this geometry builder.
- The pre-relief mass is not a structural qualification.
- The 41_ screening proxy is not a validated F3 or promotion decision.
- Optics-hardware background remains outside this detector geometry branch.
""",
        encoding="utf-8",
    )


def main() -> int:
    copy_core_geometry()
    volumes = new_bgo_volumes()
    geo_remove_counts = append_geo_patch(volumes)
    det_remove_counts = append_det_patch(volumes)
    write_overlap_source()
    audit = static_diff_audit(volumes, geo_remove_counts, det_remove_counts)
    ledger, overlap = write_mass_and_manifest(volumes, audit)
    write_readme(ledger, overlap)
    print(
        json.dumps(
            {
                "status": VALIDATED_STATUS if overlap["status"] == "PASS" else STATUS,
                "geometry": rel(SETUP),
                "static_diff": audit["status"],
                "mass_kg_pre_relief": ledger["s3d_shield_package_total_kg"],
                "mass_saved_kg": ledger["mass_saved_kg"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
