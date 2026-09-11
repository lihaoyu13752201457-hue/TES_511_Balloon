#!/usr/bin/env python3
"""Build the SE3 minimal geometry from the pinned, finished S3d-O8 authority.

This builder deliberately does not import or invoke the historical S3/S3d
builders: those rebuild from an older S3c base.  It hash-pins and copies the
five finished S3d-O8 core files, then applies exact-once literal replacements
for the SE3 whitelist only.

The default product is SE3-P20: retain 20 mm BPE, cut only the registered
focused aperture in the BPE side shell, and leave the 10 mm plastic
scintillator uncut.  ``--bpe-mode P0`` is available only as a future matched
falsifier and must be directed to an explicit alternate output root.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]

AUTHORITY_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712"
)
AUTHORITY_GEOMETRY = AUTHORITY_ROOT / "geometry"
AUTHORITY_BUILDER = AUTHORITY_ROOT / "code/build_s3d_o8_geometry.py"

OLD_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SE3_STEM = "DEMO2_DR_v3p5_SE3"

SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "setup": {
        "name": f"{OLD_STEM}.geo.setup",
        "size": 219,
        "sha256": "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    },
    "geo": {
        "name": f"{OLD_STEM}.geo",
        "size": 650588,
        "sha256": "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    },
    "det": {
        "name": f"{OLD_STEM}.det",
        "size": 57508,
        "sha256": "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    },
    "intro": {
        "name": f"Intro_{OLD_STEM}.geo",
        "size": 500,
        "sha256": "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    },
    "materials": {
        "name": "Materials_DEMO2_DR_v3p5.geo",
        "size": 1897,
        "sha256": "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf",
    },
}

DEST_NAMES = {
    "setup": f"{SE3_STEM}.geo.setup",
    "geo": f"{SE3_STEM}.geo",
    "det": f"{SE3_STEM}.det",
    # These two retained support files remain byte-identical and keep their
    # authority basenames; only setup/main/det are the SE3 entry files.
    "intro": f"Intro_{OLD_STEM}.geo",
    "materials": "Materials_DEMO2_DR_v3p5.geo",
}

AUTHORITY_BUILDER_SHA256 = (
    "5b154fad2beff70824b658ec2073b7096a8dd04c2156884512d0dfdabcbef112"
)

PLATE_SPECS = (
    {
        "key": "MXC_50mK",
        "volume": "ColdPlate_MXC_50mK_SD_anchor",
        "material": "Copper",
        "density": 8.954,
        "radius": 15.0,
        "z": 0.0,
    },
    {
        "key": "CP_100mK",
        "volume": "ColdPlate_CP_100mK_intercept",
        "material": "Copper",
        "density": 8.954,
        "radius": 15.0,
        "z": 5.0,
    },
    {
        "key": "Still_0p7K",
        "volume": "ColdPlate_Still_0p7K",
        "material": "Copper",
        "density": 8.954,
        "radius": 15.0,
        "z": 11.0,
    },
    {
        "key": "4K",
        "volume": "ColdPlate_4K",
        "material": "Copper",
        "density": 8.954,
        "radius": 17.5,
        "z": 20.0,
    },
    {
        "key": "60K",
        "volume": "ColdPlate_60K",
        "material": "Aluminium",
        "density": 2.7,
        "radius": 17.5,
        "z": 29.0,
    },
)

# The first SE3 implementation used every accepted 4 mm hole on the locked
# 6 mm lattice.  On 2026-08-15 the user explicitly replaced that high-copy
# representation with 48 equivalent-area holes per plate.  The source counts
# remain pinned here so the new, larger diameters preserve the excavated area
# (and therefore plate mass) of that reviewed design exactly.
SOURCE_HOLE_RADIUS_CM = 0.2
HOLE_PITCH_CM = 0.6
EQUIVALENT_HOLES_PER_PLATE = 48
SOURCE_ACCEPTED_HOLE_COUNTS = {
    "MXC_50mK": 1623,
    "CP_100mK": 1744,
    "Still_0p7K": 1567,
    "4K": 1920,
    "60K": 1998,
}
EDGE_SOLID_CM = 0.2
# Large equivalent holes are kept at least 2 mm clear of every projected
# functional interface as a conservative manufacturing/navigation margin.
KEEPOUT_SOLID_CM = 0.2
PLATE_OLD_THICKNESS_CM = 0.6
PLATE_NEW_THICKNESS_CM = 0.4


@dataclass(frozen=True)
class Keepout:
    plate_key: str
    feature: str
    category: str
    kind: str
    params: tuple[float, ...]


def disk(plate: str, feature: str, category: str, x: float, y: float, r: float) -> Keepout:
    return Keepout(plate, feature, category, "disk", (x, y, r))


def annulus(
    plate: str,
    feature: str,
    category: str,
    x: float,
    y: float,
    rin: float,
    rout: float,
) -> Keepout:
    return Keepout(plate, feature, category, "annulus", (x, y, rin, rout))


def sector(
    plate: str,
    feature: str,
    category: str,
    x: float,
    y: float,
    start_deg: float,
    delta_deg: float,
    rin: float,
    rout: float,
) -> Keepout:
    return Keepout(
        plate,
        feature,
        category,
        "annular_sector",
        (x, y, start_deg, delta_deg, rin, rout),
    )


def rectangle(
    plate: str,
    feature: str,
    category: str,
    x: float,
    y: float,
    hx: float,
    hy: float,
) -> Keepout:
    return Keepout(plate, feature, category, "rectangle", (x, y, hx, hy))


ROD_50_100 = (
    (6.16701521, 2.24460997, 0.845796179, "01"),
    (-6.16701521, -2.24460997, 0.845796179, "02"),
    (-1.13961835, -6.46309682, 0.845796179, "03"),
    (5.02739686, -4.21848685, 0.845796179, "04"),
)
ROD_100_STILL = (
    (6.19112313, 2.25338454, 0.818329356, "01"),
    (-6.19112313, -2.25338454, 0.818329356, "02"),
    (-1.14407331, -6.48836217, 0.818329356, "03"),
    (5.04704982, -4.23497764, 0.818329356, "04"),
)
ROD_STILL_4K = tuple(
    (x, y, 1.163232, f"{index:02d}")
    for index, (x, y) in enumerate(
        (
            (4.29855997, 4.29855997),
            (-4.29855997, 4.29855997),
            (-4.29855997, -4.29855997),
            (4.29855997, -4.29855997),
        ),
        start=1,
    )
)
ROD_4K_60K = tuple(
    (x, y, 1.32995485, f"{index:02d}")
    for index, (x, y) in enumerate(
        (
            (6.13008476, 6.13008476),
            (-6.13008476, 6.13008476),
            (-6.13008476, -6.13008476),
            (6.13008476, -6.13008476),
        ),
        start=1,
    )
)
ROD_60_300 = tuple(
    (x, y, 1.15492496, f"{index:02d}")
    for index, (x, y) in enumerate(
        (
            (7.3046183, 7.3046183),
            (-7.3046183, 7.3046183),
            (-7.3046183, -7.3046183),
            (7.3046183, -7.3046183),
        ),
        start=1,
    )
)


def add_rods(
    result: list[Keepout],
    plates: Iterable[str],
    family: str,
    rods: Iterable[tuple[float, float, float, str]],
) -> None:
    for plate in plates:
        for x, y, radius, suffix in rods:
            result.append(
                disk(
                    plate,
                    f"XS400_Group1_SupportRod_{family}_{suffix}",
                    "XS400_ROD_PROJECTION",
                    x,
                    y,
                    radius,
                )
            )


def build_keepouts() -> tuple[Keepout, ...]:
    result: list[Keepout] = []

    # 50 mK cold-finger and clamp footprints.
    for y, ym in ((1.1, "YP"), (-1.1, "YM")):
        result.extend(
            (
                rectangle(
                    "MXC_50mK",
                    f"Cu_ColdFinger_OffAxis_{ym}_ZP_from_Disk_to_Stem",
                    "COLD_FINGER_PROJECTION",
                    4.7425,
                    y,
                    1.1375,
                    0.113137085,
                ),
                rectangle(
                    "MXC_50mK",
                    f"Cu_ColdFinger_OffAxis_{ym}_ZM_from_Disk_to_Stem",
                    "COLD_FINGER_PROJECTION",
                    5.1425,
                    y,
                    1.5375,
                    0.113137085,
                ),
                disk(
                    "MXC_50mK",
                    f"Cu_ColdFinger_Stem_{ym}_ZP_to_MXC",
                    "COLD_FINGER_PROJECTION",
                    6.05,
                    y,
                    0.16,
                ),
                disk(
                    "MXC_50mK",
                    f"Cu_ColdFinger_Stem_{ym}_ZM_to_MXC",
                    "COLD_FINGER_PROJECTION",
                    6.85,
                    y,
                    0.16,
                ),
                disk(
                    "MXC_50mK",
                    f"Cu_MXC_Clamp_Pad_{ym}_ZP_for_OffAxisStem",
                    "CLAMP_PAD_PROJECTION",
                    6.05,
                    y,
                    0.35,
                ),
                disk(
                    "MXC_50mK",
                    f"Cu_MXC_Clamp_Pad_{ym}_ZM_for_OffAxisStem",
                    "CLAMP_PAD_PROJECTION",
                    6.85,
                    y,
                    0.35,
                ),
            )
        )

    add_rods(result, ("MXC_50mK", "CP_100mK"), "50mK_to_100mK", ROD_50_100)
    add_rods(result, ("CP_100mK", "Still_0p7K"), "100mK_to_Still", ROD_100_STILL)
    add_rods(result, ("Still_0p7K", "4K"), "Still_to_4K_single_edge", ROD_STILL_4K)
    add_rods(result, ("4K", "60K"), "4K_to_60K", ROD_4K_60K)
    add_rods(result, ("60K",), "60K_to_300K", ROD_60_300)

    # Deterministic, explicitly evidenced thermal-interface projections.  These
    # are projected even where thinning increases the small axial gap.
    result.extend(
        (
            disk("MXC_50mK", "DR_MixingChamber_Cu", "THERMAL_INTERFACE", 0, 0, 2.2),
            annulus("MXC_50mK", "DR_MXC_Sinter_HEX_AgProxy", "THERMAL_INTERFACE", 0, 0, 2.5, 3.5),
            sector("MXC_50mK", "DR_Continuous_HEX_CuNi_MXC_to_CP", "THERMAL_INTERFACE", 0, 0, 0, 108, 5.2, 5.5),
            sector("MXC_50mK", "DR_Capillary_CuNi_MXC_CP", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 6.2, 6.32),
            sector("MXC_50mK", "NbTi_Bundle_MXC_CP", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 6.6, 6.9),
            sector("MXC_50mK", "G10_Support_Ring_MXC_CP", "THERMAL_INTERFACE", 0, 0, 210, 90, 7.45, 7.75),
            sector("MXC_50mK", "NbTi_Bundle_bay_to_MXC", "THERMAL_INTERFACE", 0, 0, 59.4, 61.2, 6.6, 6.9),

            sector("CP_100mK", "DR_Continuous_HEX_CuNi_MXC_to_CP", "THERMAL_INTERFACE", 0, 0, 0, 108, 5.2, 5.5),
            sector("CP_100mK", "DR_Continuous_HEX_CuNi_CP_to_Still", "THERMAL_INTERFACE", 0, 0, 0, 108, 5.2, 5.5),
            sector("CP_100mK", "DR_Capillary_CuNi_MXC_CP", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 6.2, 6.32),
            sector("CP_100mK", "DR_Capillary_CuNi_CP_Still", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 6.2, 6.32),
            sector("CP_100mK", "NbTi_Bundle_MXC_CP", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 6.6, 6.9),
            sector("CP_100mK", "NbTi_Bundle_CP_Still", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 6.6, 6.9),
            sector("CP_100mK", "G10_Support_Ring_MXC_CP", "THERMAL_INTERFACE", 0, 0, 210, 90, 7.45, 7.75),
            sector("CP_100mK", "G10_Support_Ring_CP_Still", "THERMAL_INTERFACE", 0, 0, 210, 90, 8.05, 8.35),

            disk("Still_0p7K", "DR_Still_Pot_Cu", "THERMAL_INTERFACE", 0, 0, 2.6),
            annulus("Still_0p7K", "DR_Still_Heater_SS_ring", "THERMAL_INTERFACE", 0, 0, 2.7, 2.9),
            sector("Still_0p7K", "DR_Continuous_HEX_CuNi_CP_to_Still", "THERMAL_INTERFACE", 0, 0, 0, 108, 5.2, 5.5),
            sector("Still_0p7K", "DR_Capillary_CuNi_CP_Still", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 6.2, 6.32),
            sector("Still_0p7K", "NbTi_Bundle_CP_Still", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 6.6, 6.9),
            sector("Still_0p7K", "G10_Support_Ring_CP_Still", "THERMAL_INTERFACE", 0, 0, 210, 90, 8.05, 8.35),
            sector("Still_0p7K", "DR_Capillary_CuNi_Still_4K", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 9.2, 9.32),
            sector("Still_0p7K", "NbTi_Bundle_Still_4K", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 9.2, 9.5),
            sector("Still_0p7K", "G10_Support_Ring_Still_4K", "THERMAL_INTERFACE", 0, 0, 210, 90, 9.35, 9.65),

            disk("4K", "DR_4K_Condenser_Cu", "THERMAL_INTERFACE", 0, 0, 1.8),
            sector("4K", "DR_Capillary_CuNi_Still_4K", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 9.2, 9.32),
            sector("4K", "NbTi_Bundle_Still_4K", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 9.2, 9.5),
            sector("4K", "G10_Support_Ring_Still_4K", "THERMAL_INTERFACE", 0, 0, 210, 90, 9.35, 9.65),
            sector("4K", "DR_Capillary_CuNi_4K_60K", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 10.7, 10.82),
            sector("4K", "NbTi_Bundle_4K_60K", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 10.7, 11.0),
            sector("4K", "G10_Support_Ring_4K_60K", "THERMAL_INTERFACE", 0, 0, 210, 90, 10.85, 11.15),
            sector("4K", "XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K", "THERMAL_INTERFACE", 0, 0, 230, 260, 3.2, 7.1822672),
            annulus("4K", "XS400_Group3_Cu_Coarse_LowerFlange_4K60K", "THERMAL_INTERFACE", -6.8, 0, 0.55, 2.95987352),

            disk("60K", "DR_60K_Charcoal_Trap", "THERMAL_INTERFACE", 0, 0, 1.9),
            sector("60K", "DR_Capillary_CuNi_4K_60K", "THERMAL_INTERFACE", 0, 0, 38.4, 43.2, 10.7, 10.82),
            sector("60K", "NbTi_Bundle_4K_60K", "THERMAL_INTERFACE", 0, 0, 99.4, 61.2, 10.7, 11.0),
            sector("60K", "G10_Support_Ring_4K_60K", "THERMAL_INTERFACE", 0, 0, 210, 90, 10.85, 11.15),
            sector("60K", "G10_Support_Ring_60K_Top", "THERMAL_INTERFACE", 0, 0, 210, 90, 12.45, 12.7),
            rectangle("60K", "PreCool_FlexLink_Cu_remote_interface", "THERMAL_INTERFACE", -10.7, 0, 0.15, 0.5),
            sector("60K", "XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K", "THERMAL_INTERFACE", 0, 0, 230, 260, 3.2, 6.3224351),
            annulus("60K", "XS400_Group3_Cu_Coarse_TopFlange_4K60K", "THERMAL_INTERFACE", -6.8, 0, 0.65, 2.90825269),
        )
    )
    return tuple(result)


KEEPOUTS = build_keepouts()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def atomic_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exact old block once, found {count}")
    result = text.replace(old, new, 1)
    # Insertions deliberately retain their anchor as a prefix of ``new``.
    # For true replacements/deletions the old literal must disappear.
    if old and old not in new and old in result:
        raise RuntimeError(f"{label}: old block remains after replacement")
    if new and result.count(new) != 1:
        raise RuntimeError(f"{label}: new block is not exact-once after replacement")
    return result


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def angle_in_sector(theta_deg: float, start_deg: float, delta_deg: float) -> bool:
    if delta_deg >= 360.0:
        return True
    return ((theta_deg - start_deg) % 360.0) <= delta_deg + 1.0e-12


def distance_to_annular_sector(
    x: float,
    y: float,
    cx: float,
    cy: float,
    start_deg: float,
    delta_deg: float,
    rin: float,
    rout: float,
) -> float:
    px, py = x - cx, y - cy
    radius = math.hypot(px, py)
    theta = math.degrees(math.atan2(py, px)) % 360.0
    if angle_in_sector(theta, start_deg, delta_deg):
        if rin <= radius <= rout:
            return 0.0
        return min(abs(radius - rin), abs(radius - rout))
    distances: list[float] = []
    for angle_deg in (start_deg, start_deg + delta_deg):
        angle = math.radians(angle_deg)
        ux, uy = math.cos(angle), math.sin(angle)
        distances.append(
            point_segment_distance(px, py, rin * ux, rin * uy, rout * ux, rout * uy)
        )
    return min(distances)


def distance_to_keepout(x: float, y: float, keepout: Keepout) -> float:
    """Return the non-negative point-to-projected-feature distance in cm."""
    if keepout.kind == "disk":
        cx, cy, radius = keepout.params
        distance = max(0.0, math.hypot(x - cx, y - cy) - radius)
    elif keepout.kind == "annulus":
        cx, cy, rin, rout = keepout.params
        radial = math.hypot(x - cx, y - cy)
        distance = 0.0 if rin <= radial <= rout else min(abs(radial - rin), abs(radial - rout))
    elif keepout.kind == "rectangle":
        cx, cy, hx, hy = keepout.params
        dx = max(abs(x - cx) - hx, 0.0)
        dy = max(abs(y - cy) - hy, 0.0)
        distance = math.hypot(dx, dy)
    elif keepout.kind == "annular_sector":
        cx, cy, start, delta, rin, rout = keepout.params
        distance = distance_to_annular_sector(x, y, cx, cy, start, delta, rin, rout)
    else:
        raise RuntimeError(f"unsupported keepout kind: {keepout.kind}")
    return distance


def intersects_keepout(
    x: float,
    y: float,
    keepout: Keepout,
    hole_radius_cm: float,
    solid_margin_cm: float = 0.0,
) -> bool:
    return (
        distance_to_keepout(x, y, keepout)
        <= hole_radius_cm + solid_margin_cm + 1.0e-12
    )


def reference_hole_counts() -> dict[str, int]:
    """Recompute and pin the reviewed, high-copy 4 mm-hole source areas."""
    counts: dict[str, int] = {}
    for plate in PLATE_SPECS:
        key = str(plate["key"])
        radius = float(plate["radius"])
        relevant = [item for item in KEEPOUTS if item.plate_key == key]
        limit = int(math.ceil((radius - 0.4) / HOLE_PITCH_CM))
        accepted = 0
        candidate_count = 0
        for i in range(-limit, limit + 1):
            for j in range(-limit, limit + 1):
                x, y = HOLE_PITCH_CM * i, HOLE_PITCH_CM * j
                if math.hypot(x, y) > radius - 0.4 + 1.0e-12:
                    continue
                candidate_count += 1
                if not any(
                    intersects_keepout(x, y, item, SOURCE_HOLE_RADIUS_CM)
                    for item in relevant
                ):
                    accepted += 1
        expected_candidates = 1869 if math.isclose(radius, 15.0) else 2561
        if candidate_count != expected_candidates:
            raise RuntimeError(
                f"{key}: source 4 mm lattice candidate count {candidate_count} "
                f"!= {expected_candidates}"
            )
        expected_accepted = SOURCE_ACCEPTED_HOLE_COUNTS[key]
        if accepted != expected_accepted:
            raise RuntimeError(
                f"{key}: source 4 mm accepted count drifted: {accepted} != {expected_accepted}"
            )
        counts[key] = accepted
    return counts


def equivalent_radius_cm(source_hole_count: int) -> float:
    return SOURCE_HOLE_RADIUS_CM * math.sqrt(
        source_hole_count / EQUIVALENT_HOLES_PER_PLATE
    )


def select_maximin_centres(
    eligible: list[dict[str, Any]], hole_radius_cm: float
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Choose 48 deterministic, well-separated centres from the locked grid.

    Multiple deterministic seeds avoid a fragile single-seed traversal.  The
    lexicographic objective maximizes the minimum centre spacing first, then
    edge/keep-out robustness and aggregate nearest-neighbour spacing.
    """
    target = EQUIVALENT_HOLES_PER_PLATE
    if len(eligible) < target:
        raise RuntimeError(f"only {len(eligible)} eligible centres for {target} holes")

    def identity(row: dict[str, Any]) -> tuple[int, int]:
        return int(row["grid_i"]), int(row["grid_j"])

    def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
        return math.hypot(
            float(a["x_instrument_cm"]) - float(b["x_instrument_cm"]),
            float(a["y_instrument_cm"]) - float(b["y_instrument_cm"]),
        )

    robust = sorted(
        eligible,
        key=lambda row: (
            min(float(row["edge_solid_cm"]), float(row["keepout_clearance_cm"])),
            float(row["edge_solid_cm"]) + float(row["keepout_clearance_cm"]),
            -abs(int(row["grid_i"])) - abs(int(row["grid_j"])),
            -int(row["grid_i"]),
            -int(row["grid_j"]),
        ),
        reverse=True,
    )
    polar = sorted(
        eligible,
        key=lambda row: (
            math.atan2(float(row["y_instrument_cm"]), float(row["x_instrument_cm"])),
            math.hypot(float(row["x_instrument_cm"]), float(row["y_instrument_cm"])),
            int(row["grid_i"]),
            int(row["grid_j"]),
        ),
    )
    polar_step = max(1, len(polar) // 24)
    seed_candidates = robust[:32] + polar[::polar_step][:24]
    seeds: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for row in seed_candidates:
        if identity(row) not in seen:
            seen.add(identity(row))
            seeds.append(row)

    best_score: tuple[float, ...] | None = None
    best_selected: list[dict[str, Any]] | None = None
    for seed in seeds:
        selected = [seed]
        remaining = [row for row in eligible if identity(row) != identity(seed)]
        nearest = {identity(row): distance(row, seed) for row in remaining}
        while len(selected) < target:
            chosen = max(
                remaining,
                key=lambda row: (
                    nearest[identity(row)],
                    min(
                        float(row["edge_solid_cm"]),
                        float(row["keepout_clearance_cm"]),
                    ),
                    float(row["edge_solid_cm"])
                    + float(row["keepout_clearance_cm"]),
                    -abs(int(row["grid_i"])) - abs(int(row["grid_j"])),
                    -int(row["grid_i"]),
                    -int(row["grid_j"]),
                ),
            )
            selected.append(chosen)
            remaining.remove(chosen)
            for row in remaining:
                nearest[identity(row)] = min(
                    nearest[identity(row)], distance(row, chosen)
                )

        pair_distances = [
            distance(a, b)
            for index, a in enumerate(selected)
            for b in selected[index + 1 :]
        ]
        nearest_neighbours = [
            min(distance(row, other) for other in selected if other is not row)
            for row in selected
        ]
        score = (
            min(pair_distances),
            min(float(row["edge_solid_cm"]) for row in selected),
            min(float(row["keepout_clearance_cm"]) for row in selected),
            sum(nearest_neighbours),
            -sum(
                float(row["x_instrument_cm"]) ** 2
                + float(row["y_instrument_cm"]) ** 2
                for row in selected
            ),
        )
        if best_score is None or score > best_score:
            best_score, best_selected = score, selected

    if best_score is None or best_selected is None:
        raise RuntimeError("maximin equivalent-hole selection produced no solution")
    minimum_web = best_score[0] - 2.0 * hole_radius_cm
    if minimum_web < EDGE_SOLID_CM - 1.0e-12:
        raise RuntimeError(
            f"equivalent-hole minimum web {minimum_web:.12g} cm is below 0.2 cm"
        )
    metrics = {
        "minimum_center_spacing_cm": best_score[0],
        "minimum_solid_web_cm": minimum_web,
        "minimum_solid_edge_cm": best_score[1],
        "minimum_keepout_clearance_cm": best_score[2],
    }
    return best_selected, metrics


def build_hole_rows() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows: list[dict[str, Any]] = []
    accepted_by_plate: dict[str, list[dict[str, Any]]] = {}
    source_counts = reference_hole_counts()
    for plate in PLATE_SPECS:
        key = str(plate["key"])
        radius = float(plate["radius"])
        source_count = source_counts[key]
        hole_radius = equivalent_radius_cm(source_count)
        relevant = [item for item in KEEPOUTS if item.plate_key == key]
        limit_index = int(
            math.ceil((radius - EDGE_SOLID_CM - hole_radius) / HOLE_PITCH_CM)
        )
        candidates: list[dict[str, Any]] = []
        for i in range(-limit_index, limit_index + 1):
            for j in range(-limit_index, limit_index + 1):
                x = HOLE_PITCH_CM * i
                y = HOLE_PITCH_CM * j
                edge_solid = radius - math.hypot(x, y) - hole_radius
                if edge_solid < EDGE_SOLID_CM - 1.0e-12:
                    continue
                clearances = [distance_to_keepout(x, y, item) - hole_radius for item in relevant]
                keepout_clearance = min(clearances, default=999.0)
                hits = [
                    item
                    for item in relevant
                    if intersects_keepout(
                        x, y, item, hole_radius, solid_margin_cm=KEEPOUT_SOLID_CM
                    )
                ]
                row = {
                    "plate_key": key,
                    "plate_volume": plate["volume"],
                    "plate_material": plate["material"],
                    "plate_radius_cm": radius,
                    "plate_center_z_cm": plate["z"],
                    "grid_i": i,
                    "grid_j": j,
                    "x_instrument_cm": f"{x:.10g}",
                    "y_instrument_cm": f"{y:.10g}",
                    "hole_radius_cm": f"{hole_radius:.15g}",
                    "hole_diameter_mm": f"{20.0 * hole_radius:.12g}",
                    "pitch_cm": HOLE_PITCH_CM,
                    "equivalent_source_hole_count": source_count,
                    "equivalent_source_hole_radius_cm": SOURCE_HOLE_RADIUS_CM,
                    "equivalent_target_hole_count": EQUIVALENT_HOLES_PER_PLATE,
                    "equivalent_source_area_cm2": f"{source_count * math.pi * SOURCE_HOLE_RADIUS_CM**2:.15g}",
                    "edge_solid_cm": f"{edge_solid:.15g}",
                    "keepout_clearance_cm": f"{keepout_clearance:.15g}",
                    "nearest_hole_web_cm": "",
                    "selection_rank": "",
                    "selection_method": "deterministic_multistart_maximin_on_6mm_locked_grid",
                    "status": (
                        "SKIPPED_KEEP_OUT"
                        if hits
                        else "SKIPPED_EQUIVALENT_48_SELECTION"
                    ),
                    "copy_name": "",
                    "keepout_categories": ";".join(sorted({item.category for item in hits})),
                    "keepout_features": ";".join(item.feature for item in hits),
                    "keepout_kinds": ";".join(item.kind for item in hits),
                }
                candidates.append(row)
        eligible = [
            row
            for row in candidates
            if row["status"] == "SKIPPED_EQUIVALENT_48_SELECTION"
        ]
        selected, metrics = select_maximin_centres(eligible, hole_radius)
        selected_ids = {
            (int(row["grid_i"]), int(row["grid_j"])): rank
            for rank, row in enumerate(selected, start=1)
        }
        selected_rows = [
            row
            for row in candidates
            if (int(row["grid_i"]), int(row["grid_j"])) in selected_ids
        ]
        selected_rows.sort(key=lambda row: (int(row["grid_i"]), int(row["grid_j"])))
        for accepted_index, row in enumerate(selected_rows, start=1):
            row["status"] = "ACCEPTED"
            row["copy_name"] = f"SE3_HOLE_{key}_{accepted_index:05d}"
            row["selection_rank"] = selected_ids[
                (int(row["grid_i"]), int(row["grid_j"]))
            ]
            nearest_distance = min(
                math.hypot(
                    float(row["x_instrument_cm"]) - float(other["x_instrument_cm"]),
                    float(row["y_instrument_cm"]) - float(other["y_instrument_cm"]),
                )
                for other in selected_rows
                if other is not row
            )
            row["nearest_hole_web_cm"] = f"{nearest_distance - 2.0 * hole_radius:.15g}"

        accepted = [row for row in candidates if row["status"] == "ACCEPTED"]
        if len(accepted) != EQUIVALENT_HOLES_PER_PLATE:
            raise RuntimeError(f"{key}: selected {len(accepted)} holes instead of 48")
        for metric, expected in (
            ("minimum_solid_web_cm", EDGE_SOLID_CM),
            ("minimum_solid_edge_cm", EDGE_SOLID_CM),
            ("minimum_keepout_clearance_cm", KEEPOUT_SOLID_CM),
        ):
            if metrics[metric] < expected - 1.0e-12:
                raise RuntimeError(f"{key}: {metric}={metrics[metric]} below {expected}")
        accepted_by_plate[key] = accepted
        rows.extend(candidates)
    copy_names = [row["copy_name"] for row in rows if row["copy_name"]]
    if len(copy_names) != len(set(copy_names)):
        raise RuntimeError("hole copy names are not globally unique")
    return rows, accepted_by_plate


def hole_geo_block(plate: dict[str, Any], accepted: list[dict[str, Any]]) -> str:
    key = str(plate["key"])
    template = f"SE3_HoleTemplate_{key}"
    if not accepted:
        raise RuntimeError(f"{key}: no accepted equivalent holes")
    radius_text = str(accepted[0]["hole_radius_cm"])
    if any(str(row["hole_radius_cm"]) != radius_text for row in accepted):
        raise RuntimeError(f"{key}: accepted equivalent-hole radii are not uniform")
    lines = [
        "",
        f"// BEGIN SE3_HOLE_PATTERN_{key}",
        "// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.",
        "// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.",
        f"Volume {template}",
        f"{template}.Material Vacuum",
        f"{template}.Visibility 1",
        f"{template}.Shape PCON 0 360 2 -0.2 0 {radius_text} 0.2 0 {radius_text}",
        "",
    ]
    for row in accepted:
        name = row["copy_name"]
        lines.extend(
            (
                f"{template}.Copy {name}",
                f"{name}.Position {row['x_instrument_cm']} {row['y_instrument_cm']} 0",
                f"{name}.Mother {plate['volume']}",
                f"{name}.Visibility 1",
                "",
            )
        )
    lines.append(f"// END SE3_HOLE_PATTERN_{key}")
    return "\n".join(lines)


def build_equivalent_48_summary(
    hole_rows: list[dict[str, Any]],
    accepted_by_plate: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for plate in PLATE_SPECS:
        key = str(plate["key"])
        accepted = accepted_by_plate[key]
        plate_rows = [row for row in hole_rows if row["plate_key"] == key]
        radius = float(accepted[0]["hole_radius_cm"])
        source_count = int(accepted[0]["equivalent_source_hole_count"])
        source_area = source_count * math.pi * SOURCE_HOLE_RADIUS_CM**2
        target_area = len(accepted) * math.pi * radius**2
        centres = [
            (float(row["x_instrument_cm"]), float(row["y_instrument_cm"]))
            for row in accepted
        ]
        minimum_spacing = min(
            math.hypot(ax - bx, ay - by)
            for index, (ax, ay) in enumerate(centres)
            for bx, by in centres[index + 1 :]
        )
        summary.append(
            {
                "plate_key": key,
                "plate_volume": plate["volume"],
                "plate_material": plate["material"],
                "plate_radius_cm": plate["radius"],
                "source_hole_count": source_count,
                "source_hole_diameter_mm": 20.0 * SOURCE_HOLE_RADIUS_CM,
                "source_total_hole_area_cm2": source_area,
                "equivalent_hole_count": len(accepted),
                "equivalent_hole_radius_cm": radius,
                "equivalent_hole_diameter_mm": 20.0 * radius,
                "equivalent_total_hole_area_cm2": target_area,
                "area_residual_cm2": target_area - source_area,
                "area_relative_residual": (target_area - source_area) / source_area,
                "candidate_grid_points_inside_edge": len(plate_rows),
                "eligible_grid_points_after_keepout_margin": sum(
                    row["status"] != "SKIPPED_KEEP_OUT" for row in plate_rows
                ),
                "minimum_center_spacing_cm": minimum_spacing,
                "minimum_solid_web_cm": minimum_spacing - 2.0 * radius,
                "minimum_solid_edge_cm": min(
                    float(row["edge_solid_cm"]) for row in accepted
                ),
                "minimum_keepout_clearance_cm": min(
                    float(row["keepout_clearance_cm"]) for row in accepted
                ),
                "centre_selection_lattice_cm": HOLE_PITCH_CM,
                "required_solid_web_edge_cm": EDGE_SOLID_CM,
                "required_keepout_clearance_cm": KEEPOUT_SOLID_CM,
                "selection_method": "deterministic multistart maximin on the locked 6 mm centre grid",
            }
        )
    return summary


def patch_setup(text: str) -> str:
    expected = "\n".join(
        (
            f"Name {OLD_STEM}",
            "Version 1",
            f"Include {OLD_STEM}.geo",
            f"Include {OLD_STEM}.det",
            "SurroundingSphere 60 5 0 9 60",
            "",
        )
    )
    replacement = "\n".join(
        (
            f"Name {SE3_STEM}",
            "Version 1",
            f"Include {SE3_STEM}.geo",
            f"Include {SE3_STEM}.det",
            "SurroundingSphere 60 5 0 9 60",
            "",
        )
    )
    return replace_once(text, expected, replacement, "setup entry rewrite")


def patch_shields_geo(text: str) -> str:
    old_nb_cylinder = """// User cylindrical redesign: Nb_MagShield_Inner_Cylinder_2mm; material=Nb
Volume Nb_MagShield_Inner_Cylinder_2mm
Nb_MagShield_Inner_Cylinder_2mm.Material Nb
Nb_MagShield_Inner_Cylinder_2mm.Visibility 1
Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2
Nb_MagShield_Inner_Cylinder_2mm.Position 0 0 -5.2
Nb_MagShield_Inner_Cylinder_2mm.Rotation 0 90 0
Nb_MagShield_Inner_Cylinder_2mm.Mother InstrumentFrame
"""
    new_al_cylinder = """// SE3 whitelist replacement: inner 2 mm cylinder keeps shape/pose and becomes Aluminium.
Volume SE3_Al_Shield_Inner_Cylinder_2mm
SE3_Al_Shield_Inner_Cylinder_2mm.Material Aluminium
SE3_Al_Shield_Inner_Cylinder_2mm.Visibility 1
SE3_Al_Shield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2
SE3_Al_Shield_Inner_Cylinder_2mm.Position 0 0 -5.2
SE3_Al_Shield_Inner_Cylinder_2mm.Rotation 0 90 0
SE3_Al_Shield_Inner_Cylinder_2mm.Mother InstrumentFrame
"""
    old_mu_cylinder = """// User cylindrical redesign: MuMetal_MagShield_Outer_Cylinder_2mm; material=MuMetal
Volume MuMetal_MagShield_Outer_Cylinder_2mm
MuMetal_MagShield_Outer_Cylinder_2mm.Material MuMetal
MuMetal_MagShield_Outer_Cylinder_2mm.Visibility 1
MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.45 4.3 4.25 4.45
MuMetal_MagShield_Outer_Cylinder_2mm.Position 0 0 -5.2
MuMetal_MagShield_Outer_Cylinder_2mm.Rotation 0 90 0
MuMetal_MagShield_Outer_Cylinder_2mm.Mother InstrumentFrame
"""
    old_nb_cap = """// Fix5: Nb_MagShield_Inner_Back_ColdFingerCap_2mm; material=Nb
Volume Nb_MagShield_Inner_Back_ColdFingerCap_2mm
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Material Nb
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Visibility 1
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Position 0 0 -5.2
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Rotation 0 90 0
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""
    new_al_cap = """// SE3 whitelist replacement: inner 2 mm back annulus keeps shape/pose and becomes Aluminium.
Volume SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Material Aluminium
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Visibility 1
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Position 0 0 -5.2
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Rotation 0 90 0
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""
    old_mu_cap = """// Fix5: MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm; material=MuMetal
Volume MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Material MuMetal
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Visibility 1
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.45 4.5 1.85 4.45
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Position 0 0 -5.2
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Rotation 0 90 0
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""
    text = replace_once(text, old_nb_cylinder, new_al_cylinder, "Nb inner cylinder -> SE3 Al")
    text = replace_once(text, old_mu_cylinder, "", "remove MuMetal outer cylinder")
    text = replace_once(text, old_nb_cap, new_al_cap, "Nb inner back cap -> SE3 Al")
    text = replace_once(text, old_mu_cap, "", "remove MuMetal outer back cap")
    return text


def patch_shields_det(text: str) -> str:
    mappings = (
        (
            "Nb_MagShield_Inner_Cylinder_2mm",
            "SE3_Al_Shield_Inner_Cylinder_2mm",
            "rename inner-cylinder scorer",
        ),
        (
            "Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
            "SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm",
            "rename inner-cap scorer",
        ),
    )
    for old_name, new_name, label in mappings:
        old = "\n".join(
            (
                f"Scintillator {old_name}_SD",
                f"{old_name}_SD.SensitiveVolume {old_name}",
                f"{old_name}_SD.DetectorVolume {old_name}",
                f"{old_name}_SD.TriggerThreshold 0.001",
                f"{old_name}_SD.EnergyResolution Gauss 0.001 0.001 1",
                f"{old_name}_SD.EnergyResolution Gauss 3000 3000 1",
                "",
            )
        )
        new = old.replace(old_name, new_name)
        text = replace_once(text, old, new, label)
    for old_name, label in (
        ("MuMetal_MagShield_Outer_Cylinder_2mm", "remove outer-cylinder scorer"),
        ("MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm", "remove outer-cap scorer"),
    ):
        old = "\n".join(
            (
                f"Scintillator {old_name}_SD",
                f"{old_name}_SD.SensitiveVolume {old_name}",
                f"{old_name}_SD.DetectorVolume {old_name}",
                f"{old_name}_SD.TriggerThreshold 0.001",
                f"{old_name}_SD.EnergyResolution Gauss 0.001 0.001 1",
                f"{old_name}_SD.EnergyResolution Gauss 3000 3000 1",
                "",
            )
        )
        text = replace_once(text, old, "", label)
    return text


def patch_plates_geo(
    text: str, accepted_by_plate: dict[str, list[dict[str, Any]]]
) -> str:
    for plate in PLATE_SPECS:
        radius = f"{plate['radius']:g}"
        old_shape = (
            f"{plate['volume']}.Shape PCON 0 360 2 -0.3 0 {radius} 0.3 0 {radius}"
        )
        new_shape = (
            f"{plate['volume']}.Shape PCON 0 360 2 -0.2 0 {radius} 0.2 0 {radius}"
        )
        text = replace_once(text, old_shape, new_shape, f"thin {plate['volume']} to 4 mm")
        anchor = f"{plate['volume']}.Mother InstrumentFrame\n"
        insertion = anchor + hole_geo_block(plate, accepted_by_plate[str(plate["key"])]) + "\n"
        text = replace_once(text, anchor, insertion, f"insert holes for {plate['volume']}")
    return text


def patch_bpe_p20(text: str) -> str:
    anchor = """Shape Subtraction GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape
GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape.Parameters GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep07Shape GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2_Rod06_ReliefShape GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2_Rod06_ReliefOrientation
"""
    addition = anchor + """// SE3-P20 registered focused aperture: BPE only; plastic remains uncut.
Shape BRIK SE3_BPE_FocusedPortCutShape
SE3_BPE_FocusedPortCutShape.Parameters 14.5001 1.898 1.898
Orientation SE3_BPE_FocusedPortCutOrientation
SE3_BPE_FocusedPortCutOrientation.Position -14.5 0 -15.95
Shape Subtraction SE3_BPE_FocusedPortFinalShape
SE3_BPE_FocusedPortFinalShape.Parameters GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape SE3_BPE_FocusedPortCutShape SE3_BPE_FocusedPortCutOrientation
"""
    text = replace_once(text, anchor, addition, "insert registered BPE side port")
    old_shape = (
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape "
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape"
    )
    new_shape = (
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape "
        "SE3_BPE_FocusedPortFinalShape"
    )
    return replace_once(text, old_shape, new_shape, "bind BPE side volume to port shape")


def remove_volume_placement(text: str, name: str, label: str) -> str:
    # P0 is intentionally parameterized but not generated for the main package.
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line == f"Volume {name}\n"), None)
    if start is None:
        raise RuntimeError(f"{label}: missing exact Volume line")
    end = start
    while end < len(lines) and not lines[end].startswith(f"{name}.Mother "):
        end += 1
    if end >= len(lines):
        raise RuntimeError(f"{label}: missing Mother line")
    del lines[start : end + 1]
    return "".join(lines)


def patch_bpe_p0(text: str) -> str:
    for name in (
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm",
        "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm",
        "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm",
    ):
        text = remove_volume_placement(text, name, f"P0 remove {name}")
    return text


def exact_port_volume_cm3() -> float:
    half = 1.898
    rin, rout = 27.0, 29.0

    def primitive(radius: float, y: float) -> float:
        return 0.5 * (
            y * math.sqrt(radius * radius - y * y)
            + radius * radius * math.asin(y / radius)
        )

    shell_cross_section = 2.0 * (
        primitive(rout, half) - primitive(rin, half)
    )
    return shell_cross_section * (2.0 * half)


def build_mass_rows(
    hole_rows: list[dict[str, Any]], accepted_by_plate: dict[str, list[dict[str, Any]]], bpe_mode: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    touched_delta = 0.0
    for plate in PLATE_SPECS:
        accepted = accepted_by_plate[str(plate["key"])]
        candidates = [row for row in hole_rows if row["plate_key"] == plate["key"]]
        hole_radius = float(accepted[0]["hole_radius_cm"])
        source_count = int(accepted[0]["equivalent_source_hole_count"])
        full_before = math.pi * float(plate["radius"]) ** 2 * PLATE_OLD_THICKNESS_CM
        full_after = math.pi * float(plate["radius"]) ** 2 * PLATE_NEW_THICKNESS_CM
        void = len(accepted) * math.pi * hole_radius**2 * PLATE_NEW_THICKNESS_CM
        source_void = (
            source_count * math.pi * SOURCE_HOLE_RADIUS_CM**2 * PLATE_NEW_THICKNESS_CM
        )
        if not math.isclose(void, source_void, rel_tol=0.0, abs_tol=1.0e-11):
            raise RuntimeError(
                f"{plate['key']}: equivalent 48-hole void {void:.15g} != "
                f"source void {source_void:.15g} cm3"
            )
        net_after = full_after - void
        density = float(plate["density"])
        before_mass = full_before * density / 1000.0
        after_mass = net_after * density / 1000.0
        delta = after_mass - before_mass
        touched_delta += delta
        rows.append(
            {
                "scope": "cold_plate",
                "component": plate["volume"],
                "material_before": plate["material"],
                "material_after": plate["material"],
                "density_g_cm3": density,
                "radius_cm": plate["radius"],
                "hole_radius_cm": hole_radius,
                "hole_diameter_mm": 20.0 * hole_radius,
                "equivalent_source_hole_count": source_count,
                "thickness_before_cm": PLATE_OLD_THICKNESS_CM,
                "thickness_after_cm": PLATE_NEW_THICKNESS_CM,
                "candidate_hole_count": len(candidates),
                "accepted_hole_count": len(accepted),
                "skipped_hole_count": len(candidates) - len(accepted),
                "void_cm3": void,
                "volume_before_cm3": full_before,
                "volume_after_cm3": net_after,
                "mass_before_kg": before_mass,
                "mass_after_kg": after_mass,
                "delta_mass_kg": delta,
                "open_fraction": void / full_after,
                "method": "exact analytic PCON disk minus explicit Vacuum daughter count",
            }
        )

    component_specs = (
        (
            "SE3_Al_Shield_Inner_Cylinder_2mm",
            "Nb",
            "Aluminium",
            math.pi * (4.2**2 - 4.0**2) * (4.10 - (-3.85)),
            8.57,
            2.7,
        ),
        (
            "SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm",
            "Nb",
            "Aluminium",
            math.pi * (4.2**2 - 1.85**2) * (4.30 - 4.10),
            8.57,
            2.7,
        ),
        (
            "MuMetal_MagShield_Outer_Cylinder_2mm_REMOVED",
            "MuMetal",
            "REMOVED",
            math.pi * (4.45**2 - 4.25**2) * (4.30 - (-4.35)),
            8.7,
            0.0,
        ),
        (
            "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm_REMOVED",
            "MuMetal",
            "REMOVED",
            math.pi * (4.45**2 - 1.85**2) * (4.50 - 4.30),
            8.7,
            0.0,
        ),
    )
    for name, material_before, material_after, volume, density_before, density_after in component_specs:
        before_mass = volume * density_before / 1000.0
        after_mass = volume * density_after / 1000.0
        delta = after_mass - before_mass
        touched_delta += delta
        rows.append(
            {
                "scope": "nearfield_shield",
                "component": name,
                "material_before": material_before,
                "material_after": material_after,
                "density_g_cm3": density_after,
                "radius_cm": "",
                "hole_radius_cm": "",
                "hole_diameter_mm": "",
                "equivalent_source_hole_count": "",
                "thickness_before_cm": "",
                "thickness_after_cm": "",
                "candidate_hole_count": "",
                "accepted_hole_count": "",
                "skipped_hole_count": "",
                "void_cm3": "",
                "volume_before_cm3": volume,
                "volume_after_cm3": volume if density_after else 0.0,
                "mass_before_kg": before_mass,
                "mass_after_kg": after_mass,
                "delta_mass_kg": delta,
                "open_fraction": "",
                "method": "exact analytic PCON annulus using unchanged authority dimensions",
            }
        )

    if bpe_mode == "P20-port":
        port_volume = exact_port_volume_cm3()
        port_mass = port_volume * 0.95 / 1000.0
        touched_delta -= port_mass
        rows.append(
            {
                "scope": "bpe_port",
                "component": "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_focused_port",
                "material_before": "BoratedPolyethylene5wtB",
                "material_after": "Vacuum aperture",
                "density_g_cm3": 0.95,
                "radius_cm": "",
                "hole_radius_cm": "",
                "hole_diameter_mm": "",
                "equivalent_source_hole_count": "",
                "thickness_before_cm": 2.0,
                "thickness_after_cm": 0.0,
                "candidate_hole_count": "",
                "accepted_hole_count": "",
                "skipped_hole_count": "",
                "void_cm3": port_volume,
                "volume_before_cm3": port_volume,
                "volume_after_cm3": 0.0,
                "mass_before_kg": port_mass,
                "mass_after_kg": 0.0,
                "delta_mass_kg": -port_mass,
                "open_fraction": 1.0,
                "method": "exact square-aperture integral through r=27..29 cm negative-x side shell",
            }
        )

    exact_mass_before = sum(float(row["mass_before_kg"]) for row in rows)
    exact_mass_after = sum(float(row["mass_after_kg"]) for row in rows)
    exact_delta = exact_mass_after - exact_mass_before
    if not math.isclose(exact_delta, touched_delta, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError(
            f"mass ledger closure failed: rows={exact_delta:.15g}, accumulator={touched_delta:.15g}"
        )

    rows.append(
        {
            "scope": "touched_components_total",
            "component": "SE3_WHITELIST_EXACT_DELTA",
            "material_before": "mixed",
            "material_after": "mixed",
            "density_g_cm3": "",
            "radius_cm": "",
            "hole_radius_cm": "",
            "hole_diameter_mm": "",
            "equivalent_source_hole_count": sum(SOURCE_ACCEPTED_HOLE_COUNTS.values()),
            "thickness_before_cm": "",
            "thickness_after_cm": "",
            "candidate_hole_count": "",
            "accepted_hole_count": sum(len(items) for items in accepted_by_plate.values()),
            "skipped_hole_count": sum(1 for row in hole_rows if row["status"] != "ACCEPTED"),
            "void_cm3": "",
            "volume_before_cm3": "",
            "volume_after_cm3": "",
            "mass_before_kg": exact_mass_before,
            "mass_after_kg": exact_mass_after,
            "delta_mass_kg": exact_delta,
            "open_fraction": "",
            "method": "exact sum of every whitelist-touched component row; whole-instrument native snapshot is recorded separately by validation",
        }
    )
    return rows


def canonical_checks(
    authority_texts: dict[str, str], output_texts: dict[str, str], hole_rows: list[dict[str, Any]], bpe_mode: str
) -> dict[str, Any]:
    geo = output_texts["geo"]
    det = output_texts["det"]
    intro = output_texts["intro"]
    materials = output_texts["materials"]
    setup = output_texts["setup"]
    accepted_count = sum(row["status"] == "ACCEPTED" for row in hole_rows)
    accepted_by_plate = {
        key: sum(
            row["status"] == "ACCEPTED" and row["plate_key"] == key
            for row in hole_rows
        )
        for key in SOURCE_ACCEPTED_HOLE_COUNTS
    }

    checks: dict[str, bool] = {
        "intro_byte_identical": intro == authority_texts["intro"],
        "materials_byte_identical": materials == authority_texts["materials"],
        "setup_only_se3_main_and_det": (
            f"Include {SE3_STEM}.geo\n" in setup
            and f"Include {SE3_STEM}.det\n" in setup
            and OLD_STEM not in setup
        ),
        "instrument_rotation_frozen": intro.count("InstrumentFrame.Rotation 0 45 0") == 1,
        "old_nb_placements_absent": not any(
            token in geo
            for token in (
                "Volume Nb_MagShield_Inner_Cylinder_2mm",
                "Volume Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
            )
        ),
        "old_mu_placements_absent": not any(
            token in geo
            for token in (
                "Volume MuMetal_MagShield_Outer_Cylinder_2mm",
                "Volume MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm",
            )
        ),
        "new_al_placements_exactly_two": geo.count("Volume SE3_Al_Shield_") == 2,
        "old_nb_mu_scorers_absent": (
            "Nb_MagShield_Inner_" not in det and "MuMetal_MagShield_Outer_" not in det
        ),
        "new_al_scorers_exactly_two": det.count("Scintillator SE3_Al_Shield_") == 2,
        "hole_copy_count_matches_ledger": geo.count(".Copy SE3_HOLE_") == accepted_count,
        "exactly_48_equivalent_holes_per_plate": (
            accepted_count == EQUIVALENT_HOLES_PER_PLATE * len(PLATE_SPECS)
            and all(
                count == EQUIVALENT_HOLES_PER_PLATE
                for count in accepted_by_plate.values()
            )
        ),
        "equivalent_area_preserved_per_plate": all(
            math.isclose(
                sum(
                    math.pi * float(row["hole_radius_cm"]) ** 2
                    for row in hole_rows
                    if row["status"] == "ACCEPTED" and row["plate_key"] == key
                ),
                source_count * math.pi * SOURCE_HOLE_RADIUS_CM**2,
                rel_tol=0.0,
                abs_tol=1.0e-11,
            )
            for key, source_count in SOURCE_ACCEPTED_HOLE_COUNTS.items()
        ),
        "five_hole_templates": geo.count("Volume SE3_HoleTemplate_") == 5,
        "plastic_side_shape_frozen": (
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm.Shape "
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_NF2ReliefStep08Shape"
        ) in geo,
        "plastic_no_se3_port_token": "SE3_BPE_FocusedPort" not in "\n".join(
            line for line in geo.splitlines() if "Plastic" in line
        ),
        "win_magshield_frozen": authority_texts["geo"][
            authority_texts["geo"].index("// Fix5 magnetic/window panel: Win_MagShield_Al_foil_side") :
            authority_texts["geo"].index("// Volume ColdPlate_MXC_50mK_SD_anchor")
        ] in geo,
        "p20_port_present_iff_selected": (
            ("SE3_BPE_FocusedPortFinalShape" in geo) == (bpe_mode == "P20-port")
        ),
        "forbidden_performance_claim_absent": "PHYSICS PROMOTED" not in geo + det + setup,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "counts": {
            "accepted_holes": accepted_count,
            "accepted_holes_by_plate": accepted_by_plate,
            "skipped_keepout_points": sum(
                row["status"] == "SKIPPED_KEEP_OUT" for row in hole_rows
            ),
            "skipped_equivalent_selection_points": sum(
                row["status"] == "SKIPPED_EQUIVALENT_48_SELECTION"
                for row in hole_rows
            ),
            "se3_geo_lines": len(geo.splitlines()),
            "se3_det_lines": len(det.splitlines()),
        },
    }


def verify_authority() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for key, spec in SOURCE_SPECS.items():
        path = AUTHORITY_GEOMETRY / str(spec["name"])
        if not path.is_file():
            raise RuntimeError(f"missing pinned authority file: {path}")
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        if actual_size != spec["size"] or actual_hash != spec["sha256"]:
            raise RuntimeError(
                f"authority drift for {path}: size/hash {actual_size}/{actual_hash}"
            )
        records[key] = {
            "path": str(path),
            "size_bytes": actual_size,
            "sha256": actual_hash,
            "destination_name": DEST_NAMES[key],
        }
    builder_hash = sha256(AUTHORITY_BUILDER)
    if builder_hash != AUTHORITY_BUILDER_SHA256:
        raise RuntimeError(f"S3d-O8 builder authority drift: {builder_hash}")
    records["s3d_o8_builder"] = {
        "path": str(AUTHORITY_BUILDER),
        "sha256": builder_hash,
        "usage": "provenance only; not invoked because it rebuilds from older S3c",
    }
    return records


def build(output_root: Path, bpe_mode: str) -> dict[str, Any]:
    if bpe_mode == "P0" and output_root.resolve() == WORK.resolve():
        raise RuntimeError("P0 must use --output-root and may not overwrite the main SE3-P20 package")
    authority_records = verify_authority()
    geometry = output_root / "geometry"
    data = output_root / "data"
    figures = output_root / "figures"
    audit_dir = output_root / "audit"
    code = output_root / "code"
    for directory in (geometry, data, figures, audit_dir, code):
        directory.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for key, spec in SOURCE_SPECS.items():
        source = AUTHORITY_GEOMETRY / str(spec["name"])
        destination = geometry / DEST_NAMES[key]
        shutil.copy2(source, destination)
        paths[key] = destination

    authority_texts = {
        key: (AUTHORITY_GEOMETRY / str(spec["name"])).read_text(encoding="utf-8")
        for key, spec in SOURCE_SPECS.items()
    }
    hole_rows, accepted_by_plate = build_hole_rows()

    setup_text = patch_setup(authority_texts["setup"])
    geo_text = patch_shields_geo(authority_texts["geo"])
    geo_text = patch_plates_geo(geo_text, accepted_by_plate)
    geo_text = patch_bpe_p20(geo_text) if bpe_mode == "P20-port" else patch_bpe_p0(geo_text)
    det_text = patch_shields_det(authority_texts["det"])

    atomic_text(paths["setup"], setup_text)
    atomic_text(paths["geo"], geo_text)
    atomic_text(paths["det"], det_text)

    output_texts = {
        "setup": setup_text,
        "geo": geo_text,
        "det": det_text,
        "intro": paths["intro"].read_text(encoding="utf-8"),
        "materials": paths["materials"].read_text(encoding="utf-8"),
    }
    static_audit = canonical_checks(authority_texts, output_texts, hole_rows, bpe_mode)
    if static_audit["status"] != "PASS":
        failed = [name for name, passed in static_audit["checks"].items() if not passed]
        raise RuntimeError(f"static build audit failed: {failed}")

    hole_fields = [
        "plate_key", "plate_volume", "plate_material", "plate_radius_cm",
        "plate_center_z_cm", "grid_i", "grid_j", "x_instrument_cm",
        "y_instrument_cm", "hole_radius_cm", "hole_diameter_mm", "pitch_cm",
        "equivalent_source_hole_count", "equivalent_source_hole_radius_cm",
        "equivalent_target_hole_count", "equivalent_source_area_cm2",
        "edge_solid_cm", "keepout_clearance_cm", "nearest_hole_web_cm",
        "selection_rank", "selection_method", "status", "copy_name",
        "keepout_categories", "keepout_features", "keepout_kinds",
    ]
    atomic_csv(data / "se3_hole_pattern.csv", hole_fields, hole_rows)

    equivalent_summary = build_equivalent_48_summary(hole_rows, accepted_by_plate)
    atomic_csv(
        data / "se3_equivalent_48_summary.csv",
        list(equivalent_summary[0].keys()),
        equivalent_summary,
    )

    mass_rows = build_mass_rows(hole_rows, accepted_by_plate, bpe_mode)
    mass_fields = list(mass_rows[0].keys())
    atomic_csv(data / "se3_mass_ledger.csv", mass_fields, mass_rows)

    generated_files = {
        key: {
            "path": str(path.resolve()),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for key, path in paths.items()
    }
    source_manifest = {
        "status": "PASS",
        "model_identity": "SE3",
        "bpe_mode": bpe_mode,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "authority": authority_records,
        "generated_core": generated_files,
        "method": "pinned finished S3d-O8 five-core copy plus exact-once SE3 whitelist patch",
        "hole_design": {
            "revision": "user-authorized equivalent-area 48 holes per cold plate",
            "source_hole_diameter_mm": 4.0,
            "source_accepted_counts": SOURCE_ACCEPTED_HOLE_COUNTS,
            "equivalent_holes_per_plate": EQUIVALENT_HOLES_PER_PLATE,
            "total_physical_hole_placements": EQUIVALENT_HOLES_PER_PLATE * len(PLATE_SPECS),
            "area_and_mass_preserved_from_reviewed_high_copy_design": True,
        },
        "explicitly_not_invoked": str(AUTHORITY_BUILDER),
        "transport_launched": False,
        "physics_status": "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN",
    }
    atomic_json(data / "se3_source_manifest.json", source_manifest)

    static_audit.update(
        {
            "model_identity": "SE3",
            "bpe_mode": bpe_mode,
            "authority_hashes": {
                key: record["sha256"] for key, record in authority_records.items()
            },
            "generated_hashes": {
                key: record["sha256"] for key, record in generated_files.items()
            },
            "whitelist": [
                "remove exactly two MuMetal placements/scorers",
                "rename exactly two Nb placements/scorers and change material to Aluminium",
                "thin exactly five cold plates from 6 mm to 4 mm and add 48 equivalent-area hole daughters per plate",
                "cut the registered focused port in BPE side shell only for P20-port",
                "update setup entry filename/name for SE3",
            ],
        }
    )
    atomic_json(audit_dir / "se3_static_diff.json", static_audit)

    accepted_summary = {
        key: len(value) for key, value in accepted_by_plate.items()
    }
    readme = f"""# SE3 minimal geometry ({bpe_mode})

Status: `GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN`

This package is a hash-pinned, complete copy of the finished S3d-O8 authority
followed by an exact-once SE3 whitelist patch.  It is not rebuilt from S3c and
does not overwrite S3d-O8, fix5, or any other authority product.

- Geometry entry: `{paths['setup'].resolve()}`
- Hole ledger: `{(data / 'se3_hole_pattern.csv').resolve()}`
- Equivalent-area design summary: `{(data / 'se3_equivalent_48_summary.csv').resolve()}`
- Exact touched-component mass ledger: `{(data / 'se3_mass_ledger.csv').resolve()}`
- Static whitelist audit: `{(audit_dir / 'se3_static_diff.json').resolve()}`
- Accepted equivalent-area holes by plate: `{json.dumps(accepted_summary, sort_keys=True)}`

The reviewed high-copy Ø4 mm pattern is represented by exactly 48 larger
through-holes on each plate.  Each plate-specific diameter preserves its
reviewed excavated area and mass; centres are selected deterministically on
the locked 6 mm grid with at least 2 mm web, edge, and projected-interface
clearance.  This reduces physical hole placements from 8,852 to 240.

The 20 mm BPE is retained with a focused port only in its side shell.  The
10 mm plastic scintillator remains continuous and uncut.  The
`InstrumentFrame.Rotation 0 45 0` convention is frozen: world +Z is sky/up,
the sky-facing optical axis is -x-prime, and incoming focused photons travel
along +x-prime.

No prompt, delayed, activation, signal, or full-eight-family transport is
launched by this builder.  Geometry validation and native WRL products are
separate, mandatory gates.
"""
    atomic_text(output_root / "README.md", readme)
    return {
        "output_root": str(output_root.resolve()),
        "setup": str(paths["setup"].resolve()),
        "accepted_holes": accepted_summary,
        "accepted_hole_total": sum(accepted_summary.values()),
        "skipped_hole_total": sum(row["status"] != "ACCEPTED" for row in hole_rows),
        "skipped_keepout_total": sum(
            row["status"] == "SKIPPED_KEEP_OUT" for row in hole_rows
        ),
        "static_audit": static_audit["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bpe-mode", choices=("P20-port", "P0"), default="P20-port"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=WORK,
        help="Package root; P0 requires an explicit alternate root",
    )
    args = parser.parse_args()
    result = build(args.output_root.resolve(), args.bpe_mode)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
