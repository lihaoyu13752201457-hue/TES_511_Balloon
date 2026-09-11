#!/usr/bin/env python3
"""Independent static validator for the S3d-O8 LG1 geometry package."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import build_lg1_geometry as build


OUTPUT = build.DATA / "lg1_geometry_validation.json"
STATUS = "PASS_S3D_O8_LG1_STATIC_GEOMETRY_VALIDATION"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duplicate_declarations(text: str, pattern: str) -> list[str]:
    values = re.findall(pattern, text, flags=re.MULTILINE)
    return sorted(name for name, count in Counter(values).items() if count > 1)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    required = (
        build.BASE_GEO,
        build.BASE_DET,
        build.BASE_INTRO,
        build.BASE_MATERIALS,
        build.ANALYSIS_INPUTS,
        build.LG1_GEO,
        build.LG1_DET,
        build.LG1_SETUP,
        build.LG1_INTRO,
        build.LG1_MATERIALS,
        build.OVERLAP_SOURCE,
        build.MANIFEST,
    )
    missing = [str(path) for path in required if not path.is_file()]
    require(not missing, f"missing validation inputs: {missing}")

    base_geo = build.BASE_GEO.read_bytes()
    base_det = build.BASE_DET.read_bytes()
    geo_patch = build.geometry_patch().encode("utf-8")
    det_patch = build.detector_patch().encode("utf-8")
    lg1_geo = build.LG1_GEO.read_bytes()
    lg1_det = build.LG1_DET.read_bytes()

    require(lg1_geo == base_geo + geo_patch, "GEO is not exact base bytes plus exact LG1 patch")
    require(lg1_det == base_det + det_patch, "DET is not exact base bytes plus exact LG1 patch")
    require(lg1_geo[: len(base_geo)] == base_geo, "stripped GEO base is not byte-identical")
    require(lg1_det[: len(base_det)] == base_det, "stripped DET base is not byte-identical")
    require(build.LG1_INTRO.read_bytes() == build.BASE_INTRO.read_bytes(), "Intro changed")
    require(build.LG1_MATERIALS.read_bytes() == build.BASE_MATERIALS.read_bytes(), "Materials changed")

    setup = build.LG1_SETUP.read_text(encoding="utf-8")
    require(setup == build.setup_text(), "unique setup text differs from builder contract")
    setup_files = sorted(build.GEOMETRY.glob("*.geo.setup"))
    require(setup_files == [build.LG1_SETUP], f"setup is not unique: {setup_files}")
    include_lines = [line.split(maxsplit=1)[1] for line in setup.splitlines() if line.startswith("Include ")]
    require(len(include_lines) == 2, f"setup Include count differs: {include_lines}")
    require(all(Path(value).is_absolute() for value in include_lines), "setup includes are not absolute")
    require(include_lines == [str(build.LG1_GEO.resolve()), str(build.LG1_DET.resolve())], "setup absolute includes differ")

    overlap = build.OVERLAP_SOURCE.read_text(encoding="utf-8")
    require(overlap == build.overlap_source_text(), "overlap source differs from builder contract")
    # The static geometry contract owns only geometry/*.source.  Later,
    # independently frozen smoke inputs live under smoke_inputs/sources and
    # must not invalidate a post-smoke rerun of this validator.
    source_files = sorted(build.GEOMETRY.glob("*.source"))
    require(source_files == [build.OVERLAP_SOURCE], f"unexpected source cards exist: {source_files}")
    geometry_line = [line for line in overlap.splitlines() if line.startswith("Geometry ")]
    require(len(geometry_line) == 1, "overlap source Geometry line is not unique")
    require(geometry_line[0].split()[-1] == str(build.LG1_SETUP.resolve()), "overlap source setup path is not absolute/current")

    geo_text = lg1_geo.decode("utf-8")
    det_text = lg1_det.decode("utf-8")
    duplicates = {
        "volumes": duplicate_declarations(geo_text, r"^Volume\s+(\S+)"),
        "shapes": duplicate_declarations(geo_text, r"^Shape\s+\S+\s+(\S+)"),
        "orientations": duplicate_declarations(geo_text, r"^Orientation\s+(\S+)"),
        "scintillators": duplicate_declarations(det_text, r"^Scintillator\s+(\S+)"),
    }
    require(not any(duplicates.values()), f"duplicate declarations: {duplicates}")

    patch_geo_text = geo_patch.decode("utf-8")
    patch_det_text = det_patch.decode("utf-8")
    patch_volumes = re.findall(r"^Volume\s+(\S+)", patch_geo_text, flags=re.MULTILINE)
    patch_scorers = re.findall(r"^Scintillator\s+(\S+)", patch_det_text, flags=re.MULTILINE)
    require(patch_volumes == [build.SIDE_NAME, build.BACK_NAME], f"new volume set differs: {patch_volumes}")
    require(patch_scorers == [f"{build.SIDE_NAME}_SD", f"{build.BACK_NAME}_SD"], f"new scorer set differs: {patch_scorers}")

    for spec in build.VOLUMES:
        name = str(spec["name"])
        half_x = 0.5 * (float(spec["x_max_cm"]) - float(spec["x_min_cm"]))
        center_x = 0.5 * (float(spec["x_max_cm"]) + float(spec["x_min_cm"]))
        expected = (
            f"{name}_Shape.Parameters 0 360 2 {-half_x:g} {float(spec['r_inner_cm']):g} "
            f"{float(spec['r_outer_cm']):g} {half_x:g} {float(spec['r_inner_cm']):g} "
            f"{float(spec['r_outer_cm']):g}"
        )
        for line in (
            f"Volume {name}",
            f"{name}.Material BGO",
            expected,
            f"{name}.Position {center_x:g} 0 -5.2",
            f"{name}.Rotation 0 90 0",
            f"{name}.Mother InstrumentFrame",
            f"Scintillator {name}_SD",
            f"{name}_SD.SensitiveVolume {name}",
            f"{name}_SD.DetectorVolume {name}",
            f"{name}_SD.TriggerThreshold 80",
        ):
            haystack = geo_text if line in geo_text else det_text
            require(haystack.count(line + "\n") == 1, f"missing or duplicated exact line: {line}")

    side_volume = math.pi * (3.60**2 - 3.10**2) * (3.10 - (-3.55))
    back_volume = math.pi * (3.60**2 - 1.85**2) * (4.00 - 3.70)
    side_mass = side_volume * 7.13 / 1000.0
    back_mass = back_volume * 7.13 / 1000.0
    total_mass = side_mass + back_mass
    require(math.isclose(side_mass, build.mass_kg(build.SIDE), rel_tol=1e-14), "side mass mismatch")
    require(math.isclose(back_mass, build.mass_kg(build.BACK), rel_tol=1e-14), "back mass mismatch")

    edge_radius = math.hypot(1.95 + 0.0707106781, 1.95 + 0.0707106781)
    cold_finger_radius = math.hypot(1.10 + 0.113137085, 1.10 + 0.113137085)
    aperture_corner = math.hypot(1.898, 1.898)
    clearances = {
        "side_inner_to_edge_rods_cm": 3.10 - edge_radius,
        "side_outer_to_nb_inner_wall_cm": 4.0 - 3.60,
        "side_back_to_l0_disk_front_cm": (3.42 - 0.175) - 3.10,
        "back_front_to_l0_disk_back_cm": 3.70 - (3.42 + 0.175),
        "back_to_nb_back_cap_cm": 4.10 - 4.00,
        "back_hole_to_cold_fingers_cm": 1.85 - cold_finger_radius,
        "side_aperture_corner_margin_cm": 3.10 - aperture_corner,
    }
    minima = {
        "side_inner_to_edge_rods_cm": 0.20,
        "side_outer_to_nb_inner_wall_cm": 0.30,
        "side_back_to_l0_disk_front_cm": 0.14,
        "back_front_to_l0_disk_back_cm": 0.10,
        "back_to_nb_back_cap_cm": 0.09,
        "back_hole_to_cold_fingers_cm": 0.10,
        "side_aperture_corner_margin_cm": 0.40,
    }
    for key, minimum in minima.items():
        require(clearances[key] >= minimum, f"clearance gate failed: {key}={clearances[key]} < {minimum}")

    manifest = json.loads(build.MANIFEST.read_text(encoding="utf-8"))
    contract = manifest.get("active_veto_contract", {})
    analysis_inputs = json.loads(build.ANALYSIS_INPUTS.read_text(encoding="utf-8"))
    retained_contract = analysis_inputs["geometries"]["S3d_O8"]
    require(
        retained_contract.get("expected_active_veto_count") == 6,
        "analysis-input authority no longer expects six S3d-O8 active volumes",
    )
    require(
        retained_contract.get("active_veto_volumes")
        == list(build.BASE_ACTIVE_VETO_VOLUMES),
        "hard-frozen base six differ from analysis-input authority",
    )
    require(
        contract.get("authority", {}).get("sha256")
        == sha256(build.ANALYSIS_INPUTS),
        "active-veto authority hash is stale",
    )
    require(contract.get("base_exact_count") == 6, "base active-veto count is not six")
    require(contract.get("lg1_exact_count") == 8, "LG1 active-veto count is not eight")
    require(contract.get("volumes") == list(build.LG1_ACTIVE_VETO_VOLUMES), "active exact list is not original six plus LG1 two")
    require(len(set(contract["volumes"])) == 8, "active exact list contains duplicates")
    require(manifest.get("transport_source_cards_created") is False, "manifest claims transport source cards")
    require(manifest.get("overlap_status") == "NOT_RUN", "overlap status must remain NOT_RUN")
    require(manifest["generated"]["setup_absolute"] == str(build.LG1_SETUP.resolve()), "manifest setup absolute path differs")
    require(manifest["generated"]["geo"]["sha256"] == sha256(build.LG1_GEO), "manifest GEO hash stale")
    require(manifest["generated"]["det"]["sha256"] == sha256(build.LG1_DET), "manifest DET hash stale")
    require(math.isclose(manifest["mass_ledger"]["total_kg"], total_mass, rel_tol=1e-14), "manifest mass stale")
    for key, value in clearances.items():
        require(math.isclose(manifest["clearance_ledger"][key], value, rel_tol=1e-14, abs_tol=1e-14), f"manifest clearance stale: {key}")

    payload = {
        "status": STATUS,
        "claim_boundary": "Static geometry validation only; Cosima and all transport remain unrun.",
        "baseline": {
            "geometry_setup": {
                "path": build.relative(
                    build.BASE_GEOMETRY / f"{build.BASE_STEM}.geo.setup"
                ),
                "sha256": sha256(
                    build.BASE_GEOMETRY / f"{build.BASE_STEM}.geo.setup"
                ),
            },
            "geo": {"path": build.relative(build.BASE_GEO), "sha256": sha256(build.BASE_GEO)},
            "det": {"path": build.relative(build.BASE_DET), "sha256": sha256(build.BASE_DET)},
        },
        "candidate": {
            "geometry_setup": {
                "path": build.relative(build.LG1_SETUP),
                "absolute_path": str(build.LG1_SETUP.resolve()),
                "sha256": sha256(build.LG1_SETUP),
            },
            "geo": {"path": build.relative(build.LG1_GEO), "sha256": sha256(build.LG1_GEO)},
            "det": {"path": build.relative(build.LG1_DET), "sha256": sha256(build.LG1_DET)},
        },
        "guard": {
            "volumes": [
                {
                    "uid": str(spec["name"]),
                    "name": str(spec["name"]),
                    "material": "BGO",
                    "shape": "PCON",
                }
                for spec in build.VOLUMES
            ],
            "detectors": [
                {
                    "uid": f"{spec['name']}_SD",
                    "name": f"{spec['name']}_SD",
                    "sensitive_volume": str(spec["name"]),
                    "detector_volume": str(spec["name"]),
                    "native_trigger_keV": build.NATIVE_TRIGGER_KEV,
                }
                for spec in build.VOLUMES
            ],
        },
        "checks": {
            "base_after_patch_strip_byte_identical": {"geo": True, "det": True},
            "copied_core_byte_identical": {"intro": True, "materials": True},
            "unique_absolute_setup": {"path": str(build.LG1_SETUP.resolve()), "includes": include_lines},
            "only_overlap_source_present": build.relative(build.OVERLAP_SOURCE),
            "new_declarations": {"volumes": patch_volumes, "scintillators": patch_scorers},
            "duplicates": duplicates,
            "mass_kg": {"side": side_mass, "back": back_mass, "total": total_mass},
            "clearances_cm": clearances,
            "active_veto_exact_list": list(build.LG1_ACTIVE_VETO_VOLUMES),
            "active_veto_base_authority": {
                "path": build.relative(build.ANALYSIS_INPUTS),
                "sha256": sha256(build.ANALYSIS_INPUTS),
            },
            "negative_x_optical_entrance_open": True,
            "cosima_run": False,
        },
        "active_veto_exact_list": list(build.LG1_ACTIVE_VETO_VOLUMES),
        "geometry": build.relative(build.LG1_SETUP),
        "manifest": build.relative(build.MANIFEST),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": STATUS, "validation": str(OUTPUT), "mass_kg": total_mass}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
