#!/usr/bin/env python3
"""Build the isolated S3d-O8 LG1 local-guard screening geometry.

The retained 43_ S3d-O8 geometry is copied byte-for-byte.  This builder then
appends exactly two BGO volumes to the GEO body and exactly two Scintillator
blocks to the DET body.  It does not create transport cards or run Cosima.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"

BASE_PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
BASE_GEOMETRY = BASE_PACKAGE / "geometry"
ANALYSIS_INPUTS = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_corrected_reanalysis_20260813"
    / "analysis_inputs.json"
)
BASE_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
LG1_STEM = "DEMO2_DR_v3p5_S3d_O8_LG1_screening_20260813"

BASE_GEO = BASE_GEOMETRY / f"{BASE_STEM}.geo"
BASE_DET = BASE_GEOMETRY / f"{BASE_STEM}.det"
BASE_INTRO = BASE_GEOMETRY / f"Intro_{BASE_STEM}.geo"
BASE_MATERIALS = BASE_GEOMETRY / "Materials_DEMO2_DR_v3p5.geo"

LG1_GEO = GEOMETRY / f"{LG1_STEM}.geo"
LG1_DET = GEOMETRY / f"{LG1_STEM}.det"
LG1_SETUP = GEOMETRY / f"{LG1_STEM}.geo.setup"
LG1_INTRO = GEOMETRY / BASE_INTRO.name
LG1_MATERIALS = GEOMETRY / BASE_MATERIALS.name
OVERLAP_SOURCE = GEOMETRY / "overlap_check_lg1.source"
MANIFEST = DATA / "lg1_geometry_manifest.json"

STATUS = "S3D_O8_LG1_GEOMETRY_BUILT_PENDING_COSIMA_OVERLAP"
GEO_PATCH_BEGIN = "// BEGIN S3D_O8_LG1_LOCAL_GUARD_PATCH"
GEO_PATCH_END = "// END S3D_O8_LG1_LOCAL_GUARD_PATCH"
DET_PATCH_BEGIN = "// BEGIN S3D_O8_LG1_LOCAL_GUARD_DET_PATCH"
DET_PATCH_END = "// END S3D_O8_LG1_LOCAL_GUARD_DET_PATCH"

BGO_DENSITY_G_CM3 = 7.13
NATIVE_TRIGGER_KEV = 80.0
ANALYSIS_VETO_KEV = 50.0
GUARD_CENTER_Y_CM = 0.0
GUARD_CENTER_Z_CM = -5.2
GUARD_ROTATION = (0.0, 90.0, 0.0)

SIDE_NAME = "BGO_S3D_O8_LG1_OpticalAxis_OpenWell_Side_5mm"
BACK_NAME = "BGO_S3D_O8_LG1_OpticalAxis_BackAnnulus_3mm"

SIDE = {
    "name": SIDE_NAME,
    "x_min_cm": -3.55,
    "x_max_cm": 3.10,
    "r_inner_cm": 3.10,
    "r_outer_cm": 3.60,
}
BACK = {
    "name": BACK_NAME,
    "x_min_cm": 3.70,
    "x_max_cm": 4.00,
    "r_inner_cm": 1.85,
    "r_outer_cm": 3.60,
}
VOLUMES = (SIDE, BACK)

BASE_ACTIVE_VETO_VOLUMES = (
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
)
LG1_ACTIVE_VETO_VOLUMES = BASE_ACTIVE_VETO_VOLUMES + (SIDE_NAME, BACK_NAME)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def fmt(value: float) -> str:
    return f"{value:.12g}"


def volume_cm3(spec: dict[str, float | str]) -> float:
    return (
        math.pi
        * (float(spec["r_outer_cm"]) ** 2 - float(spec["r_inner_cm"]) ** 2)
        * (float(spec["x_max_cm"]) - float(spec["x_min_cm"]))
    )


def mass_kg(spec: dict[str, float | str]) -> float:
    return volume_cm3(spec) * BGO_DENSITY_G_CM3 / 1000.0


def geometry_block(spec: dict[str, float | str]) -> list[str]:
    name = str(spec["name"])
    x_min = float(spec["x_min_cm"])
    x_max = float(spec["x_max_cm"])
    half_x = 0.5 * (x_max - x_min)
    center_x = 0.5 * (x_max + x_min)
    rin = float(spec["r_inner_cm"])
    rout = float(spec["r_outer_cm"])
    shape = f"{name}_Shape"
    return [
        f"Shape PCON {shape}",
        (
            f"{shape}.Parameters 0 360 2 {-half_x:g} {rin:g} {rout:g} "
            f"{half_x:g} {rin:g} {rout:g}"
        ),
        (
            f"// Volume {name}; role=LG1 open optical-axis local BGO guard; "
            f"volume_cm3={fmt(volume_cm3(spec))}; mass_kg={fmt(mass_kg(spec))}"
        ),
        f"Volume {name}",
        f"{name}.Material BGO",
        f"{name}.Visibility 1",
        f"{name}.Shape {shape}",
        f"{name}.Position {center_x:g} {GUARD_CENTER_Y_CM:g} {GUARD_CENTER_Z_CM:g}",
        f"{name}.Rotation {GUARD_ROTATION[0]:g} {GUARD_ROTATION[1]:g} {GUARD_ROTATION[2]:g}",
        f"{name}.Mother InstrumentFrame",
        "",
    ]


def geometry_patch() -> str:
    lines = [
        GEO_PATCH_BEGIN,
        "// Screening-only local guard: negative-X optical entrance remains open.",
        "// The two volumes are inside the retained Nb cylinder and outside the TES/support envelope.",
    ]
    for spec in VOLUMES:
        lines.extend(geometry_block(spec))
    lines.append(GEO_PATCH_END)
    return "\n".join(lines) + "\n"


def detector_block(name: str) -> list[str]:
    scorer = f"{name}_SD"
    return [
        f"Scintillator {scorer}",
        f"{scorer}.SensitiveVolume {name}",
        f"{scorer}.DetectorVolume {name}",
        f"{scorer}.TriggerThreshold {NATIVE_TRIGGER_KEV:g}",
        f"{scorer}.NoiseThresholdEqualsTriggerThreshold true",
        f"{scorer}.EnergyResolution Gauss {NATIVE_TRIGGER_KEV:g} {NATIVE_TRIGGER_KEV:g} 1",
        f"{scorer}.EnergyResolution Gauss 3000 3000 1",
        "",
    ]


def detector_patch() -> str:
    lines = [
        DET_PATCH_BEGIN,
        (
            "// Native scorer threshold follows retained BGO=80 keV; the matched "
            "post-processing veto remains 50 keV."
        ),
    ]
    for spec in VOLUMES:
        lines.extend(detector_block(str(spec["name"])))
    lines.append(DET_PATCH_END)
    return "\n".join(lines) + "\n"


def setup_text() -> str:
    return "\n".join(
        [
            f"Name {LG1_STEM}",
            "Version 1",
            f"Include {LG1_GEO.resolve()}",
            f"Include {LG1_DET.resolve()}",
            "SurroundingSphere 60 5 0 9 60",
            "",
        ]
    )


def overlap_source_text() -> str:
    return "\n".join(
        [
            "Version                     1",
            f"Geometry                    {LG1_SETUP.resolve()}",
            "CheckForOverlaps            10000 0.0001",
            "PhysicsListEM               LivermorePol",
            "Run Minimum",
            "Minimum.FileName            /tmp/DelMe_s3d_o8_lg1_overlap",
            "Minimum.NEvents             1",
            "Minimum.Source MinimumS",
            "MinimumS.ParticleType       1",
            "MinimumS.Beam               PointSource 0 0 0",
            "MinimumS.Spectrum           Mono 511",
            "MinimumS.Flux               1.0",
            "",
        ]
    )


def clearance_ledger() -> dict[str, float]:
    edge_rod_extent = 1.95 + 0.0707106781
    edge_rod_radius = math.hypot(edge_rod_extent, edge_rod_extent)
    cold_finger_extent = 1.10 + 0.113137085
    cold_finger_radius = math.hypot(cold_finger_extent, cold_finger_extent)
    aperture_corner = math.hypot(1.898, 1.898)
    return {
        "side_inner_to_edge_rods_cm": float(SIDE["r_inner_cm"]) - edge_rod_radius,
        "side_outer_to_nb_inner_wall_cm": 4.0 - float(SIDE["r_outer_cm"]),
        "side_back_to_l0_disk_front_cm": (3.42 - 0.175) - float(SIDE["x_max_cm"]),
        "back_front_to_l0_disk_back_cm": float(BACK["x_min_cm"]) - (3.42 + 0.175),
        "back_to_nb_back_cap_cm": 4.10 - float(BACK["x_max_cm"]),
        "back_hole_to_cold_fingers_cm": float(BACK["r_inner_cm"]) - cold_finger_radius,
        "side_aperture_corner_margin_cm": float(SIDE["r_inner_cm"]) - aperture_corner,
    }


def main() -> int:
    required = (BASE_GEO, BASE_DET, BASE_INTRO, BASE_MATERIALS, ANALYSIS_INPUTS)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing retained O8 geometry authority: {missing}")

    analysis_inputs = json.loads(ANALYSIS_INPUTS.read_text(encoding="utf-8"))
    retained_active = tuple(
        analysis_inputs["geometries"]["S3d_O8"]["active_veto_volumes"]
    )
    retained_count = int(
        analysis_inputs["geometries"]["S3d_O8"]["expected_active_veto_count"]
    )
    if retained_count != 6 or retained_active != BASE_ACTIVE_VETO_VOLUMES:
        raise RuntimeError(
            "retained S3d-O8 active-veto authority differs from the frozen six: "
            f"count={retained_count} volumes={retained_active}"
        )

    GEOMETRY.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    shutil.copy2(BASE_INTRO, LG1_INTRO)
    shutil.copy2(BASE_MATERIALS, LG1_MATERIALS)
    LG1_GEO.write_bytes(BASE_GEO.read_bytes() + geometry_patch().encode("utf-8"))
    LG1_DET.write_bytes(BASE_DET.read_bytes() + detector_patch().encode("utf-8"))
    LG1_SETUP.write_text(setup_text(), encoding="utf-8")
    OVERLAP_SOURCE.write_text(overlap_source_text(), encoding="utf-8")

    component_rows = []
    for spec in VOLUMES:
        component_rows.append(
            {
                **spec,
                "material": "BGO",
                "density_g_cm3": BGO_DENSITY_G_CM3,
                "volume_cm3": volume_cm3(spec),
                "mass_kg": mass_kg(spec),
                "position_cm": [
                    0.5 * (float(spec["x_min_cm"]) + float(spec["x_max_cm"])),
                    GUARD_CENTER_Y_CM,
                    GUARD_CENTER_Z_CM,
                ],
                "rotation_deg": list(GUARD_ROTATION),
                "native_trigger_keV": NATIVE_TRIGGER_KEV,
            }
        )

    manifest = {
        "status": STATUS,
        "variant": "s3d_o8_lg1_open_optical_axis_local_bgo_guard",
        "claim_boundary": (
            "Geometry build and static bookkeeping only. No Cosima overlap, transport, "
            "activation, response, sensitivity, thermal, magnetic, or structural claim."
        ),
        "base_authority": {
            "package": relative(BASE_PACKAGE),
            "geo": {"path": relative(BASE_GEO), "sha256": sha256(BASE_GEO)},
            "det": {"path": relative(BASE_DET), "sha256": sha256(BASE_DET)},
            "intro": {"path": relative(BASE_INTRO), "sha256": sha256(BASE_INTRO)},
            "materials": {
                "path": relative(BASE_MATERIALS),
                "sha256": sha256(BASE_MATERIALS),
            },
        },
        "generated": {
            "setup_absolute": str(LG1_SETUP.resolve()),
            "setup_relative": relative(LG1_SETUP),
            "geo": {"path": relative(LG1_GEO), "sha256": sha256(LG1_GEO)},
            "det": {"path": relative(LG1_DET), "sha256": sha256(LG1_DET)},
            "intro": {"path": relative(LG1_INTRO), "sha256": sha256(LG1_INTRO)},
            "materials": {
                "path": relative(LG1_MATERIALS),
                "sha256": sha256(LG1_MATERIALS),
            },
            "overlap_source": {
                "path": relative(OVERLAP_SOURCE),
                "sha256": sha256(OVERLAP_SOURCE),
            },
        },
        "patch_contract": {
            "geo_marker": [GEO_PATCH_BEGIN, GEO_PATCH_END],
            "det_marker": [DET_PATCH_BEGIN, DET_PATCH_END],
            "only_new_volumes": [SIDE_NAME, BACK_NAME],
            "only_new_scorers": [f"{SIDE_NAME}_SD", f"{BACK_NAME}_SD"],
            "negative_x_optical_entrance_open": True,
        },
        "components": component_rows,
        "mass_ledger": {
            "side_kg": mass_kg(SIDE),
            "back_kg": mass_kg(BACK),
            "total_kg": sum(mass_kg(spec) for spec in VOLUMES),
            "scope": "analytic full-PCON BGO only; excludes wrappers, supports, readout, and reliefs",
        },
        "clearance_ledger": clearance_ledger(),
        "active_veto_contract": {
            "authority": {
                "path": relative(ANALYSIS_INPUTS),
                "sha256": sha256(ANALYSIS_INPUTS),
            },
            "base_exact_count": len(BASE_ACTIVE_VETO_VOLUMES),
            "lg1_exact_count": len(LG1_ACTIVE_VETO_VOLUMES),
            "analysis_veto_threshold_keV": ANALYSIS_VETO_KEV,
            "volumes": list(LG1_ACTIVE_VETO_VOLUMES),
        },
        "overlap_status": "NOT_RUN",
        "transport_source_cards_created": False,
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": STATUS, "manifest": str(MANIFEST), "mass_kg": manifest["mass_ledger"]["total_kg"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
