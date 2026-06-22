#!/usr/bin/env python3
"""Build a smoke-test geometry/source for upstream Laue hardware background.

This is not a production background run. It derives the current detector geometry,
adds a Ge annulus with the same volume and mass scale as the f=10 m Laue ring,
sets the far-field source surface from the combined detector-plus-lens envelope,
and emits low-stat EXPACS/PARMA source cards.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STEP = ROOT / "stepwise_maintenance" / "step11_upstream_optics_background"
BASE_GEO_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SOURCE_DIR = (
    ROOT
    / "stepwise_maintenance/step02_raw_background_simulation/"
    "source_snapshots_v3p5_centerfinger_fullstat_v2"
)
OUT_DIR = STEP / "smoke_geometry"

BASE = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
NAME = "DEMO2_DR_v3p5_centerfinger_with_f10m_laue_ge_proxy"
PARTICLES = ("gamma", "n", "eminus", "eplus", "p", "alpha", "muplus", "muminus")
EXPACS_EVENTS = 100
FORCED_ACTIVATION_EVENTS = 1000
FOCAL_LENGTH_CM = 1000.0
WORLD_HALF_CM = 2500.0
DETECTOR_PROXY_BOUND_CM = 80.0 * math.sqrt(3.0)
SOURCE_MARGIN_FRACTION = 0.05
GE_DENSITY_G_CM3 = 5.323


def copy_with_name(src_name: str, dst_name: str) -> None:
    shutil.copy2(BASE_GEO_DIR / src_name, OUT_DIR / dst_name)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    copy_with_name(f"Materials_DEMO2_DR_v3p5.geo", "Materials_DEMO2_DR_v3p5.geo")
    copy_with_name(f"{BASE}.det", f"{NAME}.det")

    intro = (BASE_GEO_DIR / f"Intro_{BASE}.geo").read_text()
    intro = intro.replace("Name Massmodel_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy", f"Name Massmodel_{NAME}")
    intro = intro.replace(
        "WorldVolume.Shape BRIK 1000 1000 1000",
        f"WorldVolume.Shape BRIK {WORLD_HALF_CM:g} {WORLD_HALF_CM:g} {WORLD_HALF_CM:g}",
    )
    (OUT_DIR / f"Intro_{NAME}.geo").write_text(intro)

    base_geo = (BASE_GEO_DIR / f"{BASE}.geo").read_text()
    base_geo = base_geo.replace(f"Include Intro_{BASE}.geo", f"Include Intro_{NAME}.geo", 1)

    # f=10 m A1 ring: 25 tiles, 18 mm square, 10.218801 mm thick.
    # Replace the detailed azimuthal tiles by an equal-mass Ge annulus for the
    # prompt/activation smoke test.  The production branch should use explicit
    # tile volumes and a documented support model.
    radius_mm = 74.277929
    n_tiles = 25
    tile_size_cm = 1.8
    thickness_cm = 1.0218801
    area_cm2 = n_tiles * tile_size_cm * tile_size_cm
    ring_width_cm = area_cm2 / (2.0 * math.pi * radius_mm / 10.0)
    r_mid_cm = radius_mm / 10.0
    r_in_cm = r_mid_cm - 0.5 * ring_width_cm
    r_out_cm = r_mid_cm + 0.5 * ring_width_cm
    half_t_cm = 0.5 * thickness_cm
    ge_volume_cm3 = area_cm2 * thickness_cm
    ge_mass_kg = ge_volume_cm3 * GE_DENSITY_G_CM3 / 1000.0

    # Put the lens one focal length upstream along the Step09 side-entry optical
    # axis.  This keeps it inside the enlarged world and source sphere.
    axis = (1 / math.sqrt(2), 0.0, -1 / math.sqrt(2))
    lens_center = tuple(-FOCAL_LENGTH_CM * c for c in axis)
    tile_half_diagonal_cm = math.sqrt((0.5 * tile_size_cm) ** 2 + (0.5 * tile_size_cm) ** 2 + half_t_cm**2)
    lens_volume_bound_radius_cm = r_mid_cm + tile_half_diagonal_cm
    geometry_bound_cm = max(DETECTOR_PROXY_BOUND_CM, FOCAL_LENGTH_CM + lens_volume_bound_radius_cm)
    source_sphere_cm = math.ceil(geometry_bound_cm * (1.0 + SOURCE_MARGIN_FRACTION) / 10.0) * 10.0
    source_face_area_cm2 = math.pi * source_sphere_cm**2
    run_dir = STEP / f"smoke_run_r{int(source_sphere_cm)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    lens_block = f"""

// Step11 smoke-test upstream Laue-lens Ge mass proxy.
// Equal-mass annulus for f=10 m Ge(111) ring; production should use tile volumes.
Volume Step11_Laue_Ge_Annulus_Proxy
Step11_Laue_Ge_Annulus_Proxy.Material Germanium
Step11_Laue_Ge_Annulus_Proxy.Visibility 1
Step11_Laue_Ge_Annulus_Proxy.Shape PCON 0 360 2 {-half_t_cm:.9g} {r_in_cm:.9g} {r_out_cm:.9g} {half_t_cm:.9g} {r_in_cm:.9g} {r_out_cm:.9g}
Step11_Laue_Ge_Annulus_Proxy.Position {lens_center[0]:.9g} {lens_center[1]:.9g} {lens_center[2]:.9g}
Step11_Laue_Ge_Annulus_Proxy.Mother WorldVolume
"""
    (OUT_DIR / f"{NAME}.geo").write_text(base_geo + lens_block)

    setup = "\n".join(
        [
            f"Name {NAME}",
            "Version 1",
            f"Include {NAME}.geo",
            f"Include {NAME}.det",
            f"SurroundingSphere {source_sphere_cm:g} 0 0 0 {source_sphere_cm:g}",
            "",
        ]
    )
    (OUT_DIR / f"{NAME}.geo.setup").write_text(setup)

    source_cards = {}
    for particle in PARTICLES:
        run = f"Background_{particle}_fullsphere20"
        run_name = f"step11_{particle}_smoke{EXPACS_EVENTS}_r{int(source_sphere_cm)}"
        source = (SOURCE_DIR / f"{run}.source").read_text()
        source = source.replace(
            f"Geometry outputs/geometry/{BASE}/{BASE}.geo.setup",
            f"Geometry {OUT_DIR.relative_to(ROOT)}/{NAME}.geo.setup",
        )
        source = re.sub(rf"{run}\.Events\s+\d+", f"{run}.Events {EXPACS_EVENTS}", source)
        source = re.sub(
            rf"{run}\.FileName\s+\S+",
            f"{run}.FileName {run_dir.relative_to(ROOT)}/{run_name}",
            source,
        )
        source = re.sub(
            rf"{run}\.IsotopeProductionFile\s+\S+",
            f"{run}.IsotopeProductionFile {run_dir.relative_to(ROOT)}/{run_name}.isotopes",
            source,
        )
        source = source.replace(
            "# farfield_radius_cm=60",
            f"# farfield_radius_cm={source_sphere_cm:g}",
        )
        source = source.replace(
            "# v3p5 center-finger migrated source card",
            f"# Step11 upstream-optics {particle} EXPACS/PARMA smoke source card",
        )
        out_source = OUT_DIR / f"{run_name}.source"
        out_source.write_text(source)
        source_cards[particle] = str(out_source.relative_to(ROOT))

    forced_activation = "\n".join(
        [
            "# Step11 forced activation smoke source card",
            "# Engineering verification only: monoenergetic proton beam aimed at the Ge proxy.",
            "# It is not used for physics normalization or background rates.",
            "Version 1",
            f"Geometry {OUT_DIR.relative_to(ROOT)}/{NAME}.geo.setup",
            "PhysicsListHD qgsp-bic-hp",
            "PhysicsListEM LivermorePol",
            "DecayMode ActivationBuildup",
            "StoreSimulationInfo all",
            "StoreIsotopes true",
            "DetectorTimeConstant 1e-9",
            "DefaultRangeCut 0.1",
            "Seed 24680",
            "",
            "Run Step11_ForcedActivation",
            f"Step11_ForcedActivation.Events {FORCED_ACTIVATION_EVENTS}",
            f"Step11_ForcedActivation.FileName {run_dir.relative_to(ROOT)}/step11_forced_ge_activation_r{int(source_sphere_cm)}",
            f"Step11_ForcedActivation.IsotopeProductionFile {run_dir.relative_to(ROOT)}/step11_forced_ge_activation_r{int(source_sphere_cm)}.isotopes",
            "",
            "Step11_ForcedActivation.Source Step11_ProtonBeam",
            "Step11_ProtonBeam.ParticleType 4",
            (
                "Step11_ProtonBeam.Beam HomogeneousBeam "
                f"{lens_center[0]:.9g} {lens_center[1]:.9g} {lens_center[2] + 20.0:.9g} "
                f"0 0 -1 {r_out_cm:.9g}"
            ),
            "Step11_ProtonBeam.Spectrum Mono 100000",
            "Step11_ProtonBeam.Flux 1",
            "",
        ]
    )
    forced_source = OUT_DIR / "step11_forced_ge_activation.source"
    forced_source.write_text(forced_activation)

    metadata = {
        "status": "BUILT_STEP11_SMOKE_INPUTS",
        "geometry_setup": str((OUT_DIR / f"{NAME}.geo.setup").relative_to(ROOT)),
        "source_cards": source_cards,
        "forced_activation_source": str(forced_source.relative_to(ROOT)),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "lens_proxy": {
            "type": "equal_mass_ge_annulus",
            "radius_mid_cm": r_mid_cm,
            "r_in_cm": r_in_cm,
            "r_out_cm": r_out_cm,
            "thickness_cm": thickness_cm,
            "volume_cm3": ge_volume_cm3,
            "mass_kg": ge_mass_kg,
            "density_g_cm3": GE_DENSITY_G_CM3,
            "tile_equivalent": {
                "n_tiles": n_tiles,
                "tile_size_cm": tile_size_cm,
                "tile_thickness_cm": thickness_cm,
                "total_geometric_area_cm2": area_cm2,
                "total_volume_cm3": ge_volume_cm3,
            },
            "position_cm": lens_center,
            "volume_bound_radius_cm": lens_volume_bound_radius_cm,
            "production_caveat": "Smoke-test proxy only; production branch needs explicit tile and support volumes.",
        },
        "source_surface": {
            "radius_cm": source_sphere_cm,
            "start_area_cm2": source_face_area_cm2,
            "geometry_bound_cm": geometry_bound_cm,
            "margin_fraction": SOURCE_MARGIN_FRACTION,
            "detector_proxy_bound_cm": DETECTOR_PROXY_BOUND_CM,
            "lens_center_distance_cm": FOCAL_LENGTH_CM,
            "lens_volume_bound_radius_cm": lens_volume_bound_radius_cm,
            "world_half_cm": WORLD_HALF_CM,
            "closure_policy": "Far-field source surface radius is derived from the detector-plus-upstream-lens enclosing sphere and rounded upward to the next 10 cm.",
        },
        "expacs_events_per_particle": EXPACS_EVENTS,
        "forced_activation_events": FORCED_ACTIVATION_EVENTS,
        "particles": PARTICLES,
    }
    (OUT_DIR / "step11_smoke_input_summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
