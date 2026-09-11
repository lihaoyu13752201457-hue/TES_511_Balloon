#!/usr/bin/env python3
"""Build isolated, shrink-only S3d-O8 low-grammage screening geometries.

This script performs no transport.  It copies the retained S3d-O8 authority
and applies exact, fail-closed text substitutions.  The retained geometry is
never modified.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
OUT = PACKAGE / "geometry"
DATA = PACKAGE / "data"
BASE = ROOT / (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry"
)
BASE_GEO = BASE / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
BASE_DET = BASE / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
BASE_INTRO = BASE / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
BASE_MATERIALS = BASE / "Materials_DEMO2_DR_v3p5.geo"

CU_DENSITY_G_CM3 = 8.96
NB_DENSITY_G_CM3 = 8.57


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact occurrence, found {count}")
    return text.replace(old, new, 1)


def build_variant(key: str, *, thin_nb: bool, thin_mxc: bool = False) -> dict:
    text = BASE_GEO.read_text(encoding="utf-8")
    edits: list[dict[str, str]] = []

    def edit(old: str, new: str, label: str) -> None:
        nonlocal text
        text = replace_once(text, old, new, label)
        edits.append({"label": label, "old": old, "new": new})

    # Simple copper-only low-grammage core.  All centers and interfaces stay
    # fixed except the can bottom, whose inner face remains at z=-9.7 cm.
    edit(
        "ColdPlate_MXC_50mK_SD_anchor.Shape PCON 0 360 2 -0.3 0 15 0.3 0 15",
        (
            "ColdPlate_MXC_50mK_SD_anchor.Shape PCON 0 360 2 -0.15 0 12 0.15 0 12"
            if thin_mxc
            else "ColdPlate_MXC_50mK_SD_anchor.Shape PCON 0 360 2 -0.3 0 12 0.3 0 12"
        ),
        "MXC cold-plate radius 15 -> 12 cm"
        + (" and thickness 6 -> 3 mm" if thin_mxc else ""),
    )
    if thin_mxc:
        edit(
            "ColdPlate_MXC_50mK_SD_anchor.Position 0 0 0",
            "ColdPlate_MXC_50mK_SD_anchor.Position 0 0 -0.15",
            "keep MXC cold-plate lower interface at z=-0.3 cm",
        )
    edit(
        "Cu_50mK_StillLike_Can_bottom_cap_2mm.Shape PCON 0 360 2 -0.1 0 15.3 0.1 0 15.3",
        "Cu_50mK_StillLike_Can_bottom_cap_2mm.Shape PCON 0 360 2 -0.05 0 15.3 0.05 0 15.3",
        "50 mK can bottom thickness 2 -> 1 mm",
    )
    edit(
        "Cu_50mK_StillLike_Can_bottom_cap_2mm.Position 0 0 -9.8",
        "Cu_50mK_StillLike_Can_bottom_cap_2mm.Position 0 0 -9.75",
        "keep can-bottom inner interface at z=-9.7 cm",
    )
    edit(
        "DR_MixingChamber_Cu.Shape PCON 0 360 2 -0.9 0 2.2 0.9 0 2.2",
        "DR_MixingChamber_Cu.Shape PCON 0 360 2 -0.3 0 1.8 0.3 0 1.8",
        "mixing-chamber Cu puck r 2.2 -> 1.8 cm and t 18 -> 6 mm",
    )
    edit(
        "Cu_SubstrateSupport_SolidDisk_L0_deepest.Shape BRIK 0.175 2.2 2.2",
        "Cu_SubstrateSupport_SolidDisk_L0_deepest.Shape BRIK 0.075 2.2 2.2",
        "L0 Cu support thickness 3.5 -> 1.5 mm",
    )
    for layer in range(1, 6):
        for face, a, b in (
            ("ZP", "1.73", "0.175"),
            ("ZM", "1.73", "0.175"),
            ("YP", "0.175", "1.73"),
            ("YM", "0.175", "1.73"),
        ):
            uid = f"Cu_SubstrateSupport_OpenRing_L{layer}_{face}_panel"
            edit(
                f"{uid}.Shape BRIK 0.15 {a} {b}",
                f"{uid}.Shape BRIK 0.075 {a} {b}",
                f"{uid} thickness 3 -> 1.5 mm",
            )

    if thin_nb:
        edit(
            "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2",
            "Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.05 4.1 4 4.05",
            "Nb inner cylinder thickness 2 -> 0.5 mm at fixed inner radius",
        )
        edit(
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2",
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.05 4.15 1.85 4.05",
            "Nb back cap thickness 2 -> 0.5 mm",
        )

    name = f"DEMO2_DR_v3p5_S3d_O8_{key}_screening_20260814"
    geo = OUT / f"{name}.geo"
    det = OUT / f"{name}.det"
    setup = OUT / f"{name}.geo.setup"
    geo.write_text(text, encoding="utf-8")
    shutil.copyfile(BASE_DET, det)
    setup.write_text(
        f"Name {name}\nVersion 1\nInclude {geo.resolve()}\n"
        f"Include {det.resolve()}\nSurroundingSphere 60 5 0 9 60\n",
        encoding="utf-8",
    )
    return {
        "key": key,
        "thin_nb": thin_nb,
        "thin_mxc": thin_mxc,
        "name": name,
        "geo": {"path": str(geo.relative_to(ROOT)), "sha256": sha256(geo)},
        "det": {"path": str(det.relative_to(ROOT)), "sha256": sha256(det)},
        "setup": {"path": str(setup.relative_to(ROOT)), "sha256": sha256(setup)},
        "edits": edits,
    }


def masses() -> dict:
    pi = math.pi
    current = {
        "mxc_plate": pi * 15**2 * 0.6 * CU_DENSITY_G_CM3 / 1000,
        "can_bottom": pi * 15.3**2 * 0.2 * CU_DENSITY_G_CM3 / 1000,
        "dr_mixing_cu": pi * 2.2**2 * 1.8 * CU_DENSITY_G_CM3 / 1000,
        "l0_support": (0.35 * 4.4 * 4.4) * CU_DENSITY_G_CM3 / 1000,
        "open_rings_20": 20 * (0.3 * 3.46 * 0.35) * CU_DENSITY_G_CM3 / 1000,
        "nb_cylinder": pi * (4.2**2 - 4.0**2) * 7.95 * NB_DENSITY_G_CM3 / 1000,
        "nb_back_cap": pi * (4.2**2 - 1.85**2) * 0.2 * NB_DENSITY_G_CM3 / 1000,
    }
    cu = {
        "mxc_plate": pi * 12**2 * 0.6 * CU_DENSITY_G_CM3 / 1000,
        "can_bottom": pi * 15.3**2 * 0.1 * CU_DENSITY_G_CM3 / 1000,
        "dr_mixing_cu": pi * 1.8**2 * 0.6 * CU_DENSITY_G_CM3 / 1000,
        "l0_support": (0.15 * 4.4 * 4.4) * CU_DENSITY_G_CM3 / 1000,
        "open_rings_20": 20 * (0.15 * 3.46 * 0.35) * CU_DENSITY_G_CM3 / 1000,
        "nb_cylinder": current["nb_cylinder"],
        "nb_back_cap": current["nb_back_cap"],
    }
    cu_nb = dict(cu)
    cu_nb["nb_cylinder"] = pi * (4.05**2 - 4.0**2) * 7.95 * NB_DENSITY_G_CM3 / 1000
    cu_nb["nb_back_cap"] = pi * (4.05**2 - 1.85**2) * 0.05 * NB_DENSITY_G_CM3 / 1000
    lc2 = dict(cu_nb)
    lc2["mxc_plate"] *= 0.5
    return {
        "density_g_cm3": {"Copper": CU_DENSITY_G_CM3, "Nb": NB_DENSITY_G_CM3},
        "current_kg": current,
        "LC1_Cu_kg": cu,
        "LC1_CuNb_kg": cu_nb,
        "LC2_CuNb_MXC3mm_kg": lc2,
        "current_subset_total_kg": sum(current.values()),
        "LC1_Cu_subset_total_kg": sum(cu.values()),
        "LC1_CuNb_subset_total_kg": sum(cu_nb.values()),
        "LC2_CuNb_MXC3mm_subset_total_kg": sum(lc2.values()),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    for src in (BASE_INTRO, BASE_MATERIALS):
        shutil.copyfile(src, OUT / src.name)
    variants = [
        build_variant("LC1_Cu", thin_nb=False),
        build_variant("LC1_CuNb", thin_nb=True),
        build_variant("LC2_CuNb_MXC3mm", thin_nb=True, thin_mxc=True),
    ]
    manifest = {
        "schema_version": 1,
        "status": "BUILT_STATIC_ONLY__NO_TRANSPORT_OR_PROMOTION_AUTHORITY",
        "baseline": {
            "geo": {"path": str(BASE_GEO.relative_to(ROOT)), "sha256": sha256(BASE_GEO)},
            "det": {"path": str(BASE_DET.relative_to(ROOT)), "sha256": sha256(BASE_DET)},
        },
        "variants": variants,
        "mass_model": masses(),
        "engineering_boundaries": [
            "All edits are shrink-only in the transport model.",
            "The 12 cm MXC radius leaves 2.35 cm beyond the modeled 9.65 cm MuMetal envelope, but real service routing is absent and requires CAD review.",
            "The Nb option requires magnetic FEM and field testing; geometry transport cannot establish magnetic adequacy.",
            "The LC2 MXC plate keeps its lower modeled interface fixed and requires thermal/structural verification; the static geometry is not a mechanical design.",
            "Thermal conductance, stiffness, launch vibration, fastener pads, cabling, and assembly tolerance are not represented.",
        ],
    }
    path = DATA / "lc1_geometry_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
