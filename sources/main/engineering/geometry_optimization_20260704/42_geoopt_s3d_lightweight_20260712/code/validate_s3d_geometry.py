#!/usr/bin/env python3
"""Independent, assertion-driven validation of the generated S3d geometry."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry"
)
GEOMETRY = WORK / "geometry"
DATA = WORK / "data"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

SETUP = GEOMETRY / f"{STEM}.geo.setup"
GEO = GEOMETRY / f"{STEM}.geo"
DET = GEOMETRY / f"{STEM}.det"
LEDGER = DATA / "s3d_mass_ledger.json"
BUILDER_AUDIT = DATA / "s3c_to_s3d_static_diff_summary.json"
OVERLAP_SUMMARY = DATA / "cosima_overlap_s3d_summary.json"
OUTPUT = DATA / "s3d_independent_geometry_validation.json"

OLD = (
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3C_FullWrap_BottomCap_40mm",
    "BGO_S3C_FullWrap_TopAnnulus_40mm",
    "Outer_W_S3C_BGO_Mechanical_SideShell_WindowCut_2mm",
    "Outer_W_S3C_BGO_Mechanical_BottomCap_2mm",
    "Outer_W_S3C_BGO_Mechanical_TopAnnulus_2mm",
)
UNCHANGED = (
    "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
    "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm",
    "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
    "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
)
EXPECTED = {
    "BGO_S3D_FullWrap_SideShell_WindowCut_30mm": {
        "rin": 21.2,
        "rout": 24.2,
        "zmin": -19.4,
        "zmax": 40.9,
        "position": 10.75,
        "base_shape": "FullShellShape",
    },
    "BGO_S3D_FullWrap_BottomCap_30mm": {
        "rin": 0.0,
        "rout": 25.2,
        "zmin": -22.4,
        "zmax": -19.4,
        "position": -20.9,
        "base_shape": "BasePconShape",
    },
    "BGO_S3D_FullWrap_TopAnnulus_30mm": {
        "rin": 20.9,
        "rout": 25.2,
        "zmin": 40.9,
        "zmax": 43.9,
        "position": 42.4,
        "base_shape": "BasePconShape",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def volume_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?:^// Volume {re.escape(name)}[^\n]*\n)?^Volume {re.escape(name)}\n.*?^{re.escape(name)}\.Mother [^\n]+\n",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing volume block {name}")
    return match.group(0)


def detector_block(text: str, name: str) -> str:
    detector = re.escape(f"{name}_SD")
    match = re.search(
        rf"^Scintillator {detector}\n.*?(?=\n\s*\n|^Scintillator |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing detector block {name}")
    return match.group(0)


def declaration_duplicates(text: str, pattern: str) -> list[str]:
    names = re.findall(pattern, text, flags=re.MULTILINE)
    return sorted(name for name, count in Counter(names).items() if count > 1)


def panel_mass_kg(rin: float, rout: float, zmin: float, zmax: float) -> float:
    volume_cm3 = math.pi * (rout * rout - rin * rin) * (zmax - zmin)
    return volume_cm3 * 7.13 / 1000.0


def assert_line(text: str, exact: str) -> None:
    if text.count(exact + "\n") != 1:
        raise AssertionError(f"expected exactly one line: {exact}")


def main() -> int:
    required = (SETUP, GEO, DET, LEDGER, BUILDER_AUDIT, OVERLAP_SUMMARY)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing validation prerequisite(s): {missing}")

    setup_text = SETUP.read_text(encoding="utf-8")
    geo_text = GEO.read_text(encoding="utf-8")
    det_text = DET.read_text(encoding="utf-8")
    base_geo = (BASE / f"{STEM}.geo").read_text(encoding="utf-8")
    base_det = (BASE / f"{STEM}.det").read_text(encoding="utf-8")
    ledger = json.loads(LEDGER.read_text())
    builder_audit = json.loads(BUILDER_AUDIT.read_text())
    overlap_summary = json.loads(OVERLAP_SUMMARY.read_text())

    checks: dict[str, object] = {}

    expected_setup = (
        f"Name {STEM}\n"
        "Version 1\n"
        f"Include {STEM}.geo\n"
        f"Include {STEM}.det\n"
        "SurroundingSphere 60 5 0 9 60\n"
    )
    checks["setup_exact"] = setup_text == expected_setup
    if not checks["setup_exact"]:
        raise AssertionError("setup content or surrounding sphere changed")

    core_hashes = {}
    for name in (
        f"{STEM}.geo.setup",
        f"Intro_{STEM}.geo",
        "Materials_DEMO2_DR_v3p5.geo",
    ):
        base_path = BASE / name
        new_path = GEOMETRY / name
        core_hashes[name] = {
            "base": sha256(base_path),
            "new": sha256(new_path),
            "identical": sha256(base_path) == sha256(new_path),
        }
        if not core_hashes[name]["identical"]:
            raise AssertionError(f"unexpected core-file delta: {name}")
    checks["core_hashes"] = core_hashes

    for name in OLD:
        if name in geo_text or name in det_text:
            raise AssertionError(f"retired target identifier remains: {name}")
    checks["retired_target_identifiers_absent"] = True

    patch_match = re.search(
        r"^// BEGIN GEOOPT_S3D_O9_MINPATCH$\n(.*?)^// END GEOOPT_S3D_O9_MINPATCH$",
        geo_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    detector_patch_match = re.search(
        r"^// BEGIN GEOOPT_S3D_O9_MINPATCH_DET$\n(.*?)^// END GEOOPT_S3D_O9_MINPATCH_DET$",
        det_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if patch_match is None or detector_patch_match is None:
        raise AssertionError("missing or duplicated S3d patch markers")
    patch_volumes = set(
        re.findall(r"^Volume\s+(\S+)", patch_match.group(1), re.MULTILINE)
    )
    patch_scintillators = set(
        re.findall(
            r"^Scintillator\s+(\S+)", detector_patch_match.group(1), re.MULTILINE
        )
    )
    expected_names = set(EXPECTED)
    if patch_volumes != expected_names:
        raise AssertionError(f"unexpected patch volume set: {patch_volumes}")
    if patch_scintillators != {f"{name}_SD" for name in expected_names}:
        raise AssertionError(
            f"unexpected patch scintillator set: {patch_scintillators}"
        )
    checks["exact_patch_declaration_sets"] = {
        "volumes": sorted(patch_volumes),
        "scintillators": sorted(patch_scintillators),
    }

    physical = {}
    analytic_masses = {}
    for name, spec in EXPECTED.items():
        assert_line(geo_text, f"Volume {name}")
        assert_line(geo_text, f"{name}.Material BGO")
        assert_line(geo_text, f"{name}.Position 0 0 {spec['position']:g}")
        assert_line(geo_text, f"{name}.Mother InstrumentFrame")
        assert_line(det_text, f"Scintillator {name}_SD")
        assert_line(det_text, f"{name}_SD.SensitiveVolume {name}")
        assert_line(det_text, f"{name}_SD.DetectorVolume {name}")
        assert_line(det_text, f"{name}_SD.TriggerThreshold 80")

        half_z = (spec["zmax"] - spec["zmin"]) / 2.0
        shape_line = (
            f"{name}_{spec['base_shape']}.Parameters 0 360 2 "
            f"{-half_z:g} {spec['rin']:g} {spec['rout']:g} "
            f"{half_z:g} {spec['rin']:g} {spec['rout']:g}"
        )
        assert_line(geo_text, shape_line)
        mass = panel_mass_kg(
            spec["rin"], spec["rout"], spec["zmin"], spec["zmax"]
        )
        analytic_masses[name] = mass
        ledger_mass = ledger["s3d_components_kg"]["bgo"][name]
        if not math.isclose(mass, ledger_mass, rel_tol=1e-12, abs_tol=1e-10):
            raise AssertionError(f"mass mismatch for {name}: {mass} != {ledger_mass}")
        physical[name] = {
            **spec,
            "thickness_cm": spec["rout"] - spec["rin"]
            if "SideShell" in name
            else spec["zmax"] - spec["zmin"],
            "analytic_mass_kg": mass,
        }
    checks["new_bgo_physical_definitions"] = physical

    unchanged_blocks = {}
    for name in UNCHANGED:
        geo_equal = volume_block(base_geo, name) == volume_block(geo_text, name)
        det_equal = detector_block(base_det, name) == detector_block(det_text, name)
        unchanged_blocks[name] = {"geo_identical": geo_equal, "det_identical": det_equal}
        if not (geo_equal and det_equal):
            raise AssertionError(f"preserved Al/Kapton block changed: {name}")
    checks["unchanged_al_kapton_blocks"] = unchanged_blocks

    duplicate_sets = {
        "volumes": declaration_duplicates(geo_text, r"^Volume\s+(\S+)"),
        "shapes": declaration_duplicates(geo_text, r"^Shape\s+\S+\s+(\S+)"),
        "orientations": declaration_duplicates(geo_text, r"^Orientation\s+(\S+)"),
        "scintillators": declaration_duplicates(det_text, r"^Scintillator\s+(\S+)"),
    }
    if any(duplicate_sets.values()):
        raise AssertionError(f"duplicate declarations: {duplicate_sets}")
    checks["duplicate_declarations"] = duplicate_sets

    intro_path = GEOMETRY / f"Intro_{STEM}.geo"
    materials_path = GEOMETRY / "Materials_DEMO2_DR_v3p5.geo"
    intro_text = intro_path.read_text(encoding="utf-8")
    materials_text = materials_path.read_text(encoding="utf-8")
    include_checks = {}
    for parent, text in ((SETUP, setup_text), (GEO, geo_text), (intro_path, intro_text)):
        for include in re.findall(r"^Include\s+(\S+)", text, re.MULTILINE):
            target = parent.parent / include
            include_checks[f"{parent.name}:{include}"] = target.exists()
            if not target.exists():
                raise AssertionError(f"unresolved include {include} from {parent}")
    checks["include_refs_resolved"] = include_checks

    combined_geo = "\n".join((materials_text, intro_text, geo_text))
    declared_shapes = set(
        re.findall(r"^Shape\s+\S+\s+(\S+)", combined_geo, re.MULTILINE)
    )
    declared_orientations = set(
        re.findall(r"^Orientation\s+(\S+)", combined_geo, re.MULTILINE)
    )
    missing_shape_assignments = []
    for line in combined_geo.splitlines():
        match = re.match(r"^\S+\.Shape\s+(\S+)(?:\s+(.*))?$", line)
        if match and match.group(2) is None and match.group(1) not in declared_shapes:
            missing_shape_assignments.append(match.group(1))

    missing_boolean_refs = []
    boolean_shapes = re.findall(
        r"^Shape\s+(?:Subtraction|Union|Intersection)\s+(\S+)",
        combined_geo,
        re.MULTILINE,
    )
    for name in boolean_shapes:
        match = re.search(
            rf"^{re.escape(name)}\.Parameters\s+(\S+)\s+(\S+)\s+(\S+)",
            combined_geo,
            re.MULTILINE,
        )
        if match is None:
            missing_boolean_refs.append(f"{name}:missing_parameters")
            continue
        first, second, orientation = match.groups()
        if first not in declared_shapes:
            missing_boolean_refs.append(f"{name}:shape:{first}")
        if second not in declared_shapes:
            missing_boolean_refs.append(f"{name}:shape:{second}")
        if orientation not in declared_orientations:
            missing_boolean_refs.append(f"{name}:orientation:{orientation}")
    if missing_shape_assignments or missing_boolean_refs:
        raise AssertionError(
            "unresolved shape graph: "
            f"assignments={sorted(set(missing_shape_assignments))}, "
            f"boolean={missing_boolean_refs[:20]}"
        )
    checks["shape_orientation_refs_resolved"] = {
        "declared_shapes": len(declared_shapes),
        "declared_orientations": len(declared_orientations),
        "boolean_shapes": len(boolean_shapes),
        "missing_shape_assignments": [],
        "missing_boolean_refs": [],
    }

    all_declared_volumes = set(
        re.findall(r"^Volume\s+(\S+)", combined_geo, re.MULTILINE)
    )
    mother_refs = set(
        re.findall(r"^\S+\.Mother\s+(\S+)", combined_geo, re.MULTILINE)
    ) - {"0"}
    missing_mothers = sorted(mother_refs - all_declared_volumes)
    if missing_mothers:
        raise AssertionError(f"unresolved Mother refs: {missing_mothers}")
    checks["mother_refs_resolved"] = {
        "references": len(mother_refs),
        "missing": missing_mothers,
    }

    declared_volumes = set(re.findall(r"^Volume\s+(\S+)", geo_text, re.MULTILINE))
    sensitive = set(re.findall(r"^\S+\.SensitiveVolume\s+(\S+)", det_text, re.MULTILINE))
    detector = set(re.findall(r"^\S+\.DetectorVolume\s+(\S+)", det_text, re.MULTILINE))
    missing_refs = sorted((sensitive | detector) - declared_volumes)
    if missing_refs:
        raise AssertionError(f"unresolved detector volume refs: {missing_refs}")
    checks["detector_refs_resolved"] = {
        "sensitive": len(sensitive),
        "detector": len(detector),
        "missing": missing_refs,
    }

    total = (
        sum(analytic_masses.values())
        + ledger["s3d_components_kg"]["al3_unchanged"]
        + ledger["s3d_components_kg"]["kapton_unchanged"]
    )
    if not math.isclose(
        total, ledger["s3d_shield_package_total_kg"], rel_tol=1e-12
    ):
        raise AssertionError("independent total mass does not reproduce ledger")
    saved = ledger["baseline_s3c_c0_shield_package_mass_kg"] - total
    if not math.isclose(saved, ledger["mass_saved_kg"], rel_tol=1e-12):
        raise AssertionError("independent mass saving does not reproduce ledger")
    checks["mass_reproduction"] = {
        "total_kg": total,
        "saved_kg": saved,
        "reduction_fraction": saved
        / ledger["baseline_s3c_c0_shield_package_mass_kg"],
    }

    if builder_audit.get("status") != "PASS":
        raise AssertionError("builder static-diff audit is not PASS")
    checks["builder_audit_status"] = builder_audit["status"]

    overlap_hashes = {
        "source": sha256(GEOMETRY / "overlap_check_s3d.source")
        == overlap_summary["files"]["source"]["sha256"],
        "setup": sha256(SETUP) == overlap_summary["files"]["setup"]["sha256"],
        "geo": sha256(GEO) == overlap_summary["files"]["geo"]["sha256"],
        "det": sha256(DET) == overlap_summary["files"]["det"]["sha256"],
    }
    if overlap_summary.get("status") != "PASS" or not all(overlap_hashes.values()):
        raise AssertionError(
            f"overlap evidence is failed or stale: {overlap_summary.get('status')}, "
            f"hashes={overlap_hashes}"
        )
    checks["cosima_overlap_hash_pinned"] = {
        "status": overlap_summary["status"],
        "hashes": overlap_hashes,
        "bad_lines": overlap_summary.get("bad_lines", []),
    }

    output = {
        "status": "PASS",
        "geometry": SETUP.resolve().relative_to(ROOT).as_posix(),
        "checks": checks,
        "boundary": (
            "This validates the authorized geometry delta and analytic pre-relief "
            "mass only; it is not a transport or structural qualification."
        ),
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": output["status"],
                "output": OUTPUT.resolve().relative_to(ROOT).as_posix(),
                "mass_kg_pre_relief": total,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
