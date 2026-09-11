#!/usr/bin/env python3
"""Independent semantic and provenance validation for the generated O8 geometry."""

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
    / "engineering/geometry_optimization_20260704"
    / "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry"
)
GEOMETRY = WORK / "geometry"
DATA = WORK / "data"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"

SETUP = GEOMETRY / f"{STEM}.geo.setup"
GEO = GEOMETRY / f"{STEM}.geo"
DET = GEOMETRY / f"{STEM}.det"
LEDGER = DATA / "s3d_o8_mass_ledger.json"
MANIFEST = DATA / "s3d_o8_geometry_manifest.json"
BUILDER_AUDIT = DATA / "s3c_to_s3d_o8_static_diff_summary.json"
OVERLAP_SOURCE = GEOMETRY / "overlap_check_s3d_o8.source"
OVERLAP_SUMMARY = DATA / "cosima_overlap_s3d_o8_summary.json"
DECISION = DATA / "o8_fallback_decision_evidence.json"
OUTPUT = DATA / "s3d_o8_independent_geometry_validation.json"

PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O8_FALLBACK_MINPATCH"
PATCH_END = "// END GEOOPT_S3D_O8_FALLBACK_MINPATCH"
DET_PATCH_BEGIN = "// BEGIN GEOOPT_S3D_O8_FALLBACK_MINPATCH_DET"
DET_PATCH_END = "// END GEOOPT_S3D_O8_FALLBACK_MINPATCH_DET"

OLD = (
    "BGO_S3C_FullWrap_BottomCap_40mm",
    "BGO_S3C_FullWrap_TopAnnulus_40mm",
    "Outer_W_S3C_BGO_Mechanical_SideShell_WindowCut_2mm",
    "Outer_W_S3C_BGO_Mechanical_BottomCap_2mm",
    "Outer_W_S3C_BGO_Mechanical_TopAnnulus_2mm",
)
RETAINED_SIDE = "BGO_S3C_FullWrap_SideShell_WindowCut_40mm"
UNCHANGED = (
    RETAINED_SIDE,
    "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
    "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm",
    "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
    "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
)
EXPECTED = {
    "BGO_S3D_O8_FullWrap_BottomCap_30mm": {
        "rin": 0.0,
        "rout": 25.2,
        "zmin": -22.4,
        "zmax": -19.4,
        "position": -20.9,
        "shape_suffix": "BasePconShape",
    },
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm": {
        "rin": 20.9,
        "rout": 25.2,
        "zmin": 40.9,
        "zmax": 41.9,
        "position": 41.4,
        "shape_suffix": "BasePconShape",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()) + "\n"


def declaration_duplicates(text: str, pattern: str) -> list[str]:
    names = re.findall(pattern, text, flags=re.MULTILINE)
    return sorted(name for name, count in Counter(names).items() if count > 1)


def volume_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?:^// Volume {re.escape(name)}[^\n]*\n)?^Volume {re.escape(name)}\n.*?^{re.escape(name)}\.Mother [^\n]+\n",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing volume block: {name}")
    return match.group(0)


def detector_block(text: str, name: str) -> str:
    sd = re.escape(f"{name}_SD")
    match = re.search(
        rf"^Scintillator {sd}\n.*?(?=\n\s*\n|^Scintillator |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing detector block: {name}")
    return match.group(0)


def is_target_geo_line(line: str, name: str) -> bool:
    stripped = line.strip()
    fields = stripped.split()
    return bool(
        stripped.startswith(f"// Volume {name}")
        or stripped.startswith(name + ".")
        or stripped.startswith(name + "_")
        or (len(fields) >= 2 and fields[0] == "Volume" and fields[1] == name)
        or (
            len(fields) >= 2
            and fields[0] == "Orientation"
            and fields[1].startswith(name + "_")
        )
        or (
            len(fields) >= 3
            and fields[0] == "Shape"
            and fields[2].startswith(name + "_")
        )
    )


def strip_target_geo(text: str) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if not any(is_target_geo_line(line, name) for name in OLD)
    ) + "\n"


def strip_detector_blocks(text: str) -> str:
    result = text
    for name in OLD:
        sd = re.escape(f"{name}_SD")
        result, count = re.subn(
            rf"^Scintillator {sd}\n.*?(?=\n\s*\n|^Scintillator |\Z)\n?",
            "",
            result,
            flags=re.MULTILINE | re.DOTALL,
        )
        if count != 1:
            raise AssertionError(f"base detector target count changed for {name}: {count}")
    return result


def remove_patch(text: str, begin: str, end: str) -> str:
    result, count = re.subn(
        rf"\n?^{re.escape(begin)}$.*?^{re.escape(end)}$\n?",
        "\n",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if count != 1:
        raise AssertionError(f"patch marker count mismatch: {begin} -> {count}")
    return result


def panel_mass_kg(spec: dict) -> float:
    volume = (
        math.pi
        * (spec["rout"] ** 2 - spec["rin"] ** 2)
        * (spec["zmax"] - spec["zmin"])
    )
    return volume * 7.13 / 1000.0


def assert_single_line(text: str, line: str) -> None:
    if text.count(line + "\n") != 1:
        raise AssertionError(f"expected exactly one line: {line}")


def main() -> int:
    required = (
        SETUP,
        GEO,
        DET,
        LEDGER,
        MANIFEST,
        BUILDER_AUDIT,
        OVERLAP_SOURCE,
        OVERLAP_SUMMARY,
        DECISION,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing O8 validation prerequisite(s): {missing}")

    setup = SETUP.read_text(encoding="utf-8")
    geo = GEO.read_text(encoding="utf-8")
    det = DET.read_text(encoding="utf-8")
    base_geo = (BASE / f"{STEM}.geo").read_text(encoding="utf-8")
    base_det = (BASE / f"{STEM}.det").read_text(encoding="utf-8")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    builder_audit = json.loads(BUILDER_AUDIT.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP_SUMMARY.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    checks: dict[str, object] = {}

    expected_setup = (
        f"Name {STEM}\nVersion 1\nInclude {STEM}.geo\nInclude {STEM}.det\n"
        "SurroundingSphere 60 5 0 9 60\n"
    )
    if setup != expected_setup:
        raise AssertionError("setup or R60 surrounding sphere changed")
    checks["setup_exact"] = True

    core_hashes = {}
    for name in (
        f"{STEM}.geo.setup",
        f"Intro_{STEM}.geo",
        "Materials_DEMO2_DR_v3p5.geo",
    ):
        base_path = BASE / name
        new_path = GEOMETRY / name
        same = sha256(base_path) == sha256(new_path)
        core_hashes[name] = {
            "base_sha256": sha256(base_path),
            "new_sha256": sha256(new_path),
            "identical": same,
        }
        if not same:
            raise AssertionError(f"unexpected core-file delta: {name}")
    checks["unchanged_core_files"] = core_hashes

    for name in OLD:
        if name in geo or name in det:
            raise AssertionError(f"retired target identifier remains: {name}")
    if "S3D_O9" in geo or "S3D_O9" in det:
        raise AssertionError("O9 identifier leaked into O8 geometry")
    if geo.count(f"Volume {RETAINED_SIDE}\n") != 1:
        raise AssertionError("retained C0 side40 volume is missing or duplicated")
    if det.count(f"Scintillator {RETAINED_SIDE}_SD\n") != 1:
        raise AssertionError("retained C0 side40 scorer is missing or duplicated")
    checks["retired_c0_targets_and_o9_identifiers_absent"] = True

    patch = re.search(
        rf"^{re.escape(PATCH_BEGIN)}$\n(.*?)^{re.escape(PATCH_END)}$",
        geo,
        flags=re.MULTILINE | re.DOTALL,
    )
    det_patch = re.search(
        rf"^{re.escape(DET_PATCH_BEGIN)}$\n(.*?)^{re.escape(DET_PATCH_END)}$",
        det,
        flags=re.MULTILINE | re.DOTALL,
    )
    if patch is None or det_patch is None:
        raise AssertionError("O8 patch markers are missing or duplicated")
    patch_volumes = set(re.findall(r"^Volume\s+(\S+)", patch.group(1), re.MULTILINE))
    patch_sds = set(
        re.findall(r"^Scintillator\s+(\S+)", det_patch.group(1), re.MULTILINE)
    )
    if patch_volumes != set(EXPECTED):
        raise AssertionError(f"unexpected O8 patch volumes: {patch_volumes}")
    if patch_sds != {f"{name}_SD" for name in EXPECTED}:
        raise AssertionError(f"unexpected O8 scintillators: {patch_sds}")
    checks["exact_patch_declaration_sets"] = {
        "volumes": sorted(patch_volumes),
        "scintillators": sorted(patch_sds),
    }

    masses = {}
    physical = {}
    for name, spec in EXPECTED.items():
        half_z = (spec["zmax"] - spec["zmin"]) / 2.0
        expected_shape = (
            f"{name}_{spec['shape_suffix']}.Parameters 0 360 2 "
            f"{-half_z:g} {spec['rin']:g} {spec['rout']:g} "
            f"{half_z:g} {spec['rin']:g} {spec['rout']:g}"
        )
        for line in (
            f"Volume {name}",
            f"{name}.Material BGO",
            expected_shape,
            f"{name}.Position 0 0 {spec['position']:g}",
            f"{name}.Mother InstrumentFrame",
            f"Scintillator {name}_SD",
            f"{name}_SD.SensitiveVolume {name}",
            f"{name}_SD.DetectorVolume {name}",
            f"{name}_SD.TriggerThreshold 80",
        ):
            assert_single_line(geo if line in geo else det, line)
        mass = panel_mass_kg(spec)
        masses[name] = mass
        ledger_mass = ledger["o8_components_kg"]["bgo"][name]
        if not math.isclose(mass, ledger_mass, rel_tol=1e-12, abs_tol=1e-10):
            raise AssertionError(f"independent mass mismatch for {name}")
        physical[name] = {**spec, "analytic_mass_kg": mass}
    checks["o8_bgo_physical_definitions"] = physical

    retained_side_spec = {
        "rin": 21.2,
        "rout": 25.2,
        "zmin": -19.4,
        "zmax": 40.9,
    }
    retained_side_mass = panel_mass_kg(retained_side_spec)
    masses[RETAINED_SIDE] = retained_side_mass
    ledger_side_mass = ledger["o8_components_kg"]["bgo"][RETAINED_SIDE]
    if not math.isclose(
        retained_side_mass, ledger_side_mass, rel_tol=1e-12, abs_tol=1e-10
    ):
        raise AssertionError("retained side40 mass does not reproduce ledger")
    checks["retained_side40_physical_definition"] = {
        **retained_side_spec,
        "analytic_mass_kg": retained_side_mass,
        "geo_and_det_blocks_checked_below": True,
    }

    unchanged = {}
    for name in UNCHANGED:
        geo_same = volume_block(base_geo, name) == volume_block(geo, name)
        det_same = detector_block(base_det, name) == detector_block(det, name)
        unchanged[name] = {"geo_identical": geo_same, "det_identical": det_same}
        if not (geo_same and det_same):
            raise AssertionError(f"preserved side40/Al/Kapton block changed: {name}")
    checks["unchanged_side40_al3_kapton_blocks"] = unchanged

    base_geo_non_target = canonical(strip_target_geo(base_geo))
    new_geo_non_target = canonical(
        strip_target_geo(remove_patch(geo, PATCH_BEGIN, PATCH_END))
    )
    base_det_non_target = canonical(strip_detector_blocks(base_det))
    new_det_non_target = canonical(
        remove_patch(det, DET_PATCH_BEGIN, DET_PATCH_END)
    )
    if base_geo_non_target != new_geo_non_target:
        raise AssertionError("independent GEO non-target canonical diff failed")
    if base_det_non_target != new_det_non_target:
        raise AssertionError("independent DET non-target canonical diff failed")
    checks["independent_non_target_canonical_identity"] = {
        "geo": True,
        "det": True,
        "geo_sha256": hashlib.sha256(base_geo_non_target.encode()).hexdigest(),
        "det_sha256": hashlib.sha256(base_det_non_target.encode()).hexdigest(),
    }

    duplicates = {
        "volumes": declaration_duplicates(geo, r"^Volume\s+(\S+)"),
        "shapes": declaration_duplicates(geo, r"^Shape\s+\S+\s+(\S+)"),
        "orientations": declaration_duplicates(geo, r"^Orientation\s+(\S+)"),
        "scintillators": declaration_duplicates(det, r"^Scintillator\s+(\S+)"),
    }
    if any(duplicates.values()):
        raise AssertionError(f"duplicate declarations: {duplicates}")
    checks["duplicate_declarations"] = duplicates

    intro = (GEOMETRY / f"Intro_{STEM}.geo").read_text(encoding="utf-8")
    materials = (GEOMETRY / "Materials_DEMO2_DR_v3p5.geo").read_text(encoding="utf-8")
    combined = "\n".join((materials, intro, geo))
    declared_volumes = set(re.findall(r"^Volume\s+(\S+)", combined, re.MULTILINE))
    declared_shapes = set(
        re.findall(r"^Shape\s+\S+\s+(\S+)", combined, re.MULTILINE)
    )
    declared_orientations = set(
        re.findall(r"^Orientation\s+(\S+)", combined, re.MULTILINE)
    )
    missing_mothers = sorted(
        set(re.findall(r"^\S+\.Mother\s+(\S+)", combined, re.MULTILINE))
        - {"0"}
        - declared_volumes
    )
    missing_shape_assignments = []
    for match in re.finditer(r"^\S+\.Shape\s+(\S+)(?:\s+(.*))?$", combined, re.MULTILINE):
        if match.group(2) is None and match.group(1) not in declared_shapes:
            missing_shape_assignments.append(match.group(1))
    missing_boolean = []
    for name in re.findall(
        r"^Shape\s+(?:Subtraction|Union|Intersection)\s+(\S+)",
        combined,
        re.MULTILINE,
    ):
        match = re.search(
            rf"^{re.escape(name)}\.Parameters\s+(\S+)\s+(\S+)\s+(\S+)",
            combined,
            re.MULTILINE,
        )
        if match is None:
            missing_boolean.append(f"{name}:parameters")
            continue
        first, second, orientation = match.groups()
        if first not in declared_shapes:
            missing_boolean.append(f"{name}:shape:{first}")
        if second not in declared_shapes:
            missing_boolean.append(f"{name}:shape:{second}")
        if orientation not in declared_orientations:
            missing_boolean.append(f"{name}:orientation:{orientation}")
    detector_refs = set(
        re.findall(r"^\S+\.(?:SensitiveVolume|DetectorVolume)\s+(\S+)", det, re.MULTILINE)
    )
    missing_detector_refs = sorted(detector_refs - declared_volumes)
    if missing_mothers or missing_shape_assignments or missing_boolean or missing_detector_refs:
        raise AssertionError(
            "unresolved semantic references: "
            f"mothers={missing_mothers}, shapes={missing_shape_assignments[:10]}, "
            f"boolean={missing_boolean[:10]}, detector={missing_detector_refs}"
        )
    checks["semantic_references_resolved"] = {
        "declared_volumes": len(declared_volumes),
        "declared_shapes": len(declared_shapes),
        "declared_orientations": len(declared_orientations),
        "detector_refs": len(detector_refs),
    }

    total = (
        sum(masses.values())
        + ledger["o8_components_kg"]["al3_unchanged"]
        + ledger["o8_components_kg"]["kapton_unchanged"]
    )
    baseline = ledger["baseline_s3c_c0_shield_package_mass_kg"]
    saved = baseline - total
    reduction = saved / baseline
    if not math.isclose(total, 309.77676671553456, rel_tol=0.0, abs_tol=1e-9):
        raise AssertionError(f"unexpected independently calculated O8 mass: {total}")
    if not math.isclose(total, ledger["o8_shield_package_total_kg"], rel_tol=1e-12):
        raise AssertionError("independent total does not reproduce the O8 ledger")
    if not math.isclose(saved, ledger["mass_saved_kg"], rel_tol=1e-12):
        raise AssertionError("independent saving does not reproduce the O8 ledger")
    checks["independent_mass_reproduction"] = {
        "total_kg": total,
        "saved_kg": saved,
        "reduction_fraction": reduction,
    }

    if builder_audit.get("status") != "PASS":
        raise AssertionError("shared-core static diff audit is not PASS")
    if decision.get("status") != "PASS_REPRODUCED_O9_GATE_FAILURE_AND_ENTRY_DIRECTIONS":
        raise AssertionError("fallback decision evidence is not PASS")
    if decision["o9_transport_gate"]["pass"] is not False:
        raise AssertionError("O9 decision evidence no longer records a failed gate")
    if manifest.get("static_diff_status") != "PASS":
        raise AssertionError("manifest static-diff state is not PASS")
    checks["decision_and_static_diff_authorities"] = {
        "builder_audit": builder_audit["status"],
        "decision": decision["status"],
        "o9_gate_pass": False,
    }

    overlap_hashes = {
        "source": sha256(OVERLAP_SOURCE) == overlap["files"]["source"]["sha256"],
        "setup": sha256(SETUP) == overlap["files"]["setup"]["sha256"],
        "geo": sha256(GEO) == overlap["files"]["geo"]["sha256"],
        "det": sha256(DET) == overlap["files"]["det"]["sha256"],
    }
    if overlap.get("status") != "PASS" or not all(overlap_hashes.values()):
        raise AssertionError(
            f"overlap evidence failed/stale: {overlap.get('status')}, {overlap_hashes}"
        )
    if overlap.get("generated_particles") != 1:
        raise AssertionError("overlap smoke was not exactly one generated particle")
    checks["cosima_overlap_hash_pinned"] = {
        "status": overlap["status"],
        "hashes": overlap_hashes,
        "generated_particles": overlap["generated_particles"],
        "bad_lines": overlap.get("bad_lines", []),
    }

    result = {
        "status": "PASS",
        "geometry": SETUP.resolve().relative_to(ROOT).as_posix(),
        "checks": checks,
        "boundary": (
            "Validates only the authorized O8 geometry delta, hash-pinned one-event "
            "Cosima overlap/load smoke, and analytic pre-relief mass. No O8 "
            "production transport or performance claim is included."
        ),
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": OUTPUT.resolve().relative_to(ROOT).as_posix(),
                "mass_kg_pre_relief": total,
                "mass_saved_kg": saved,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
