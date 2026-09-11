#!/usr/bin/env python3
"""Fail-closed, non-transport validation of the SE3 geometry package.

This validator is intentionally separate from ``build_se3_geometry.py``.  It
reconstructs the pinned S3d-O8 authority by reversing only the SE3 whitelist,
recomputes the hole and mass ledgers, and resolves the local geometry symbol
graph.  It does not launch Cosima, Geomega, or particle transport.

The detailed keep-out dimensions are the implementation contract recorded in
the package builder.  They are loaded as data only; this file independently
enumerates the lattice and independently evaluates every intersection.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import hashlib
import json
import math
import os
import re
import runpy
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


sys.dont_write_bytecode = True

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_DIR = PACKAGE_ROOT / "geometry"
DATA_DIR = PACKAGE_ROOT / "data"
AUDIT_DIR = PACKAGE_ROOT / "audit"
BUILDER = PACKAGE_ROOT / "code/build_se3_geometry.py"

AUTHORITY_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712"
)
AUTHORITY_GEOMETRY = AUTHORITY_ROOT / "geometry"
AUTHORITY_BUILDER = AUTHORITY_ROOT / "code/build_s3d_o8_geometry.py"

OLD_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SE3_STEM = "DEMO2_DR_v3p5_SE3"

AUTHORITY_SPECS: dict[str, tuple[Path, int, str]] = {
    "setup": (
        AUTHORITY_GEOMETRY / f"{OLD_STEM}.geo.setup",
        219,
        "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    ),
    "geo": (
        AUTHORITY_GEOMETRY / f"{OLD_STEM}.geo",
        650588,
        "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    ),
    "det": (
        AUTHORITY_GEOMETRY / f"{OLD_STEM}.det",
        57508,
        "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    ),
    "intro": (
        AUTHORITY_GEOMETRY / f"Intro_{OLD_STEM}.geo",
        500,
        "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    ),
    "materials": (
        AUTHORITY_GEOMETRY / "Materials_DEMO2_DR_v3p5.geo",
        1897,
        "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf",
    ),
    "s3d_o8_builder": (
        AUTHORITY_BUILDER,
        -1,
        "5b154fad2beff70824b658ec2073b7096a8dd04c2156884512d0dfdabcbef112",
    ),
}

SE3_FILES = {
    "setup": GEOMETRY_DIR / f"{SE3_STEM}.geo.setup",
    "geo": GEOMETRY_DIR / f"{SE3_STEM}.geo",
    "det": GEOMETRY_DIR / f"{SE3_STEM}.det",
    "intro": GEOMETRY_DIR / f"Intro_{OLD_STEM}.geo",
    "materials": GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}

PLATES = (
    ("MXC_50mK", "ColdPlate_MXC_50mK_SD_anchor", "Copper", 8.954, 15.0, 0.0),
    ("CP_100mK", "ColdPlate_CP_100mK_intercept", "Copper", 8.954, 15.0, 5.0),
    ("Still_0p7K", "ColdPlate_Still_0p7K", "Copper", 8.954, 15.0, 11.0),
    ("4K", "ColdPlate_4K", "Copper", 8.954, 17.5, 20.0),
    ("60K", "ColdPlate_60K", "Aluminium", 2.7, 17.5, 29.0),
)

# The revised fabrication-friendly representation uses 48 equal-radius holes
# per plate.  The radius is plate-dependent and chosen so that each plate
# removes exactly the same area as its previous accepted set of 4 mm holes.
REFERENCE_D4_HOLE_RADIUS_CM = 0.2
EQUIVALENT_D4_HOLE_COUNTS = {
    "MXC_50mK": 1623,
    "CP_100mK": 1744,
    "Still_0p7K": 1567,
    "4K": 1920,
    "60K": 1998,
}
PHYSICAL_HOLES_PER_PLATE = 48
MINIMUM_SOLID_WEB_EDGE_CM = 0.2
OLD_THICKNESS_CM = 0.6
NEW_THICKNESS_CM = 0.4
NUMERIC_ABS_TOL = 2.0e-11

REQUIRED_HOLE_FIELDS = {
    "plate_key",
    "plate_volume",
    "plate_material",
    "plate_radius_cm",
    "plate_center_z_cm",
    "x_instrument_cm",
    "y_instrument_cm",
    "hole_radius_cm",
    "status",
    "copy_name",
    "keepout_categories",
    "keepout_features",
    "keepout_kinds",
}

MASS_FIELDS = [
    "scope",
    "component",
    "material_before",
    "material_after",
    "density_g_cm3",
    "radius_cm",
    "thickness_before_cm",
    "thickness_after_cm",
    "candidate_hole_count",
    "accepted_hole_count",
    "skipped_hole_count",
    "void_cm3",
    "volume_before_cm3",
    "volume_after_cm3",
    "mass_before_kg",
    "mass_after_kg",
    "delta_mass_kg",
    "open_fraction",
    "method",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def close(actual: float, expected: float, tolerance: float = NUMERIC_ABS_TOL) -> bool:
    return math.isclose(actual, expected, rel_tol=2.0e-12, abs_tol=tolerance)


def as_float(value: str, field: str) -> float:
    if value == "":
        raise ValueError(f"empty numeric field: {field}")
    return float(value)


def scorer_block(name: str) -> str:
    return "\n".join(
        (
            f"Scintillator {name}_SD",
            f"{name}_SD.SensitiveVolume {name}",
            f"{name}_SD.DetectorVolume {name}",
            f"{name}_SD.TriggerThreshold 0.001",
            f"{name}_SD.EnergyResolution Gauss 0.001 0.001 1",
            f"{name}_SD.EnergyResolution Gauss 3000 3000 1",
            "",
        )
    )


OLD_NB_CYLINDER = """// User cylindrical redesign: Nb_MagShield_Inner_Cylinder_2mm; material=Nb
Volume Nb_MagShield_Inner_Cylinder_2mm
Nb_MagShield_Inner_Cylinder_2mm.Material Nb
Nb_MagShield_Inner_Cylinder_2mm.Visibility 1
Nb_MagShield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2
Nb_MagShield_Inner_Cylinder_2mm.Position 0 0 -5.2
Nb_MagShield_Inner_Cylinder_2mm.Rotation 0 90 0
Nb_MagShield_Inner_Cylinder_2mm.Mother InstrumentFrame
"""

OLD_MU_CYLINDER = """// User cylindrical redesign: MuMetal_MagShield_Outer_Cylinder_2mm; material=MuMetal
Volume MuMetal_MagShield_Outer_Cylinder_2mm
MuMetal_MagShield_Outer_Cylinder_2mm.Material MuMetal
MuMetal_MagShield_Outer_Cylinder_2mm.Visibility 1
MuMetal_MagShield_Outer_Cylinder_2mm.Shape PCON 0 360 2 -4.35 4.25 4.45 4.3 4.25 4.45
MuMetal_MagShield_Outer_Cylinder_2mm.Position 0 0 -5.2
MuMetal_MagShield_Outer_Cylinder_2mm.Rotation 0 90 0
MuMetal_MagShield_Outer_Cylinder_2mm.Mother InstrumentFrame
"""

SE3_AL_CYLINDER = """// SE3 whitelist replacement: inner 2 mm cylinder keeps shape/pose and becomes Aluminium.
Volume SE3_Al_Shield_Inner_Cylinder_2mm
SE3_Al_Shield_Inner_Cylinder_2mm.Material Aluminium
SE3_Al_Shield_Inner_Cylinder_2mm.Visibility 1
SE3_Al_Shield_Inner_Cylinder_2mm.Shape PCON 0 360 2 -3.85 4 4.2 4.1 4 4.2
SE3_Al_Shield_Inner_Cylinder_2mm.Position 0 0 -5.2
SE3_Al_Shield_Inner_Cylinder_2mm.Rotation 0 90 0
SE3_Al_Shield_Inner_Cylinder_2mm.Mother InstrumentFrame
"""

OLD_NB_CAP = """// Fix5: Nb_MagShield_Inner_Back_ColdFingerCap_2mm; material=Nb
Volume Nb_MagShield_Inner_Back_ColdFingerCap_2mm
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Material Nb
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Visibility 1
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Position 0 0 -5.2
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Rotation 0 90 0
Nb_MagShield_Inner_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""

OLD_MU_CAP = """// Fix5: MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm; material=MuMetal
Volume MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Material MuMetal
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Visibility 1
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.3 1.85 4.45 4.5 1.85 4.45
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Position 0 0 -5.2
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Rotation 0 90 0
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""

SE3_AL_CAP = """// SE3 whitelist replacement: inner 2 mm back annulus keeps shape/pose and becomes Aluminium.
Volume SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Material Aluminium
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Visibility 1
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Shape PCON 0 360 2 4.1 1.85 4.2 4.3 1.85 4.2
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Position 0 0 -5.2
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Rotation 0 90 0
SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm.Mother InstrumentFrame
"""

BPE_PORT_ADDITION = """// SE3-P20 registered focused aperture: BPE only; plastic remains uncut.
Shape BRIK SE3_BPE_FocusedPortCutShape
SE3_BPE_FocusedPortCutShape.Parameters 14.5001 1.898 1.898
Orientation SE3_BPE_FocusedPortCutOrientation
SE3_BPE_FocusedPortCutOrientation.Position -14.5 0 -15.95
Shape Subtraction SE3_BPE_FocusedPortFinalShape
SE3_BPE_FocusedPortFinalShape.Parameters GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape SE3_BPE_FocusedPortCutShape SE3_BPE_FocusedPortCutOrientation
"""


class Recorder:
    def __init__(self) -> None:
        self.checks: dict[str, bool] = {}
        self.failures: list[str] = []

    def record(self, name: str, result: bool, detail: str = "") -> bool:
        value = bool(result)
        self.checks[name] = value
        if not value:
            self.failures.append(f"{name}: {detail or 'check returned false'}")
        return value

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
    operations: dict[str, int],
) -> str:
    count = text.count(old)
    operations[label] = count
    if count != 1:
        raise ValueError(f"{label}: expected exact block once, found {count}")
    return text.replace(old, new, 1)


def reconstruct_authority_geo(se3: str) -> tuple[str, dict[str, int]]:
    operations: dict[str, int] = {}
    text = replace_once(
        se3,
        SE3_AL_CYLINDER + "\n",
        OLD_NB_CYLINDER + "\n" + OLD_MU_CYLINDER,
        "restore Nb/Mu cylinder pair",
        operations,
    )
    text = replace_once(
        text,
        SE3_AL_CAP + "\n",
        OLD_NB_CAP + "\n" + OLD_MU_CAP,
        "restore Nb/Mu back-cap pair",
        operations,
    )

    for key, volume, _material, _density, radius, _z in PLATES:
        pattern = re.compile(
            rf"\n// BEGIN SE3_HOLE_PATTERN_{re.escape(key)}\n.*?"
            rf"// END SE3_HOLE_PATTERN_{re.escape(key)}\n",
            re.DOTALL,
        )
        text, count = pattern.subn("", text)
        operations[f"remove hole block {key}"] = count
        if count != 1:
            raise ValueError(f"{key}: expected one complete hole block, found {count}")
        new_shape = f"{volume}.Shape PCON 0 360 2 -0.2 0 {radius:g} 0.2 0 {radius:g}"
        old_shape = f"{volume}.Shape PCON 0 360 2 -0.3 0 {radius:g} 0.3 0 {radius:g}"
        text = replace_once(
            text,
            new_shape,
            old_shape,
            f"restore 6 mm thickness {key}",
            operations,
        )

    text = replace_once(
        text,
        BPE_PORT_ADDITION,
        "",
        "remove focused BPE port definitions",
        operations,
    )
    text = replace_once(
        text,
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape SE3_BPE_FocusedPortFinalShape",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape "
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_NF2ReliefStep08Shape",
        "restore BPE side-shell shape binding",
        operations,
    )
    return text, operations


def reconstruct_authority_det(se3: str) -> tuple[str, dict[str, int]]:
    operations: dict[str, int] = {}
    text = replace_once(
        se3,
        scorer_block("SE3_Al_Shield_Inner_Cylinder_2mm") + "\n",
        scorer_block("Nb_MagShield_Inner_Cylinder_2mm")
        + "\n"
        + scorer_block("MuMetal_MagShield_Outer_Cylinder_2mm"),
        "restore Nb/Mu cylinder scorers",
        operations,
    )
    text = replace_once(
        text,
        scorer_block("SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm"),
        scorer_block("Nb_MagShield_Inner_Back_ColdFingerCap_2mm")
        + scorer_block("MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm"),
        "restore Nb/Mu cap scorers",
        operations,
    )
    return text, operations


def reconstruct_authority_setup(se3: str) -> tuple[str, dict[str, int]]:
    operations: dict[str, int] = {}
    text = replace_once(
        se3,
        f"Name {SE3_STEM}\n",
        f"Name {OLD_STEM}\n",
        "restore setup name",
        operations,
    )
    text = replace_once(
        text,
        f"Include {SE3_STEM}.geo\n",
        f"Include {OLD_STEM}.geo\n",
        "restore setup geo include",
        operations,
    )
    text = replace_once(
        text,
        f"Include {SE3_STEM}.det\n",
        f"Include {OLD_STEM}.det\n",
        "restore setup det include",
        operations,
    )
    return text, operations


def residual_diff(expected: str, actual: str, from_name: str, to_name: str) -> dict[str, Any]:
    lines = list(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=from_name,
            tofile=to_name,
            lineterm="",
            n=3,
        )
    )
    changed = sum(
        1
        for line in lines
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    )
    return {
        "equal": expected == actual,
        "residual_changed_lines": changed,
        "residual_diff_head": lines[:80],
        "authority_sha256": sha256_text(expected),
        "reconstructed_sha256": sha256_text(actual),
    }


def point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def angle_in_sector(theta_deg: float, start_deg: float, delta_deg: float) -> bool:
    if delta_deg >= 360.0:
        return True
    return ((theta_deg - start_deg) % 360.0) <= delta_deg + 1.0e-12


def sector_distance(x: float, y: float, params: Iterable[float]) -> float:
    cx, cy, start_deg, delta_deg, rin, rout = tuple(params)
    px, py = x - cx, y - cy
    radial = math.hypot(px, py)
    theta = math.degrees(math.atan2(py, px)) % 360.0
    if angle_in_sector(theta, start_deg, delta_deg):
        if rin <= radial <= rout:
            return 0.0
        return min(abs(radial - rin), abs(radial - rout))
    distances = []
    for angle_deg in (start_deg, start_deg + delta_deg):
        angle = math.radians(angle_deg)
        ux, uy = math.cos(angle), math.sin(angle)
        distances.append(
            point_segment_distance(px, py, rin * ux, rin * uy, rout * ux, rout * uy)
        )
    return min(distances)


def intersects_keepout(
    x: float,
    y: float,
    hole_radius_cm: float,
    keepout: Any,
    solid_margin_cm: float = 0.0,
) -> bool:
    params = tuple(float(item) for item in keepout.params)
    if keepout.kind == "disk":
        cx, cy, radius = params
        distance = math.hypot(x - cx, y - cy) - radius
    elif keepout.kind == "annulus":
        cx, cy, rin, rout = params
        radial = math.hypot(x - cx, y - cy)
        distance = 0.0 if rin <= radial <= rout else min(abs(radial - rin), abs(radial - rout))
    elif keepout.kind == "rectangle":
        cx, cy, hx, hy = params
        dx = max(abs(x - cx) - hx, 0.0)
        dy = max(abs(y - cy) - hy, 0.0)
        distance = math.hypot(dx, dy)
    elif keepout.kind == "annular_sector":
        distance = sector_distance(x, y, params)
    else:
        raise ValueError(f"unsupported keep-out kind: {keepout.kind}")
    return distance <= hole_radius_cm + solid_margin_cm + 1.0e-12


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def validate_holes(
    recorder: Recorder,
    geo: str,
    det: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    ledger_path = DATA_DIR / "se3_hole_pattern.csv"
    fields, rows = read_csv(ledger_path)
    missing_fields = sorted(REQUIRED_HOLE_FIELDS - set(fields))
    recorder.record(
        "hole_ledger_required_fields_present",
        not missing_fields,
        f"missing fields: {missing_fields}; actual={fields}",
    )

    builder_hash_before = sha256(BUILDER)
    builder_data = runpy.run_path(str(BUILDER))
    builder_hash_after = sha256(BUILDER)
    recorder.require(builder_hash_before == builder_hash_after, "builder changed while loading keep-outs")
    keepouts = tuple(builder_data["KEEPOUTS"])

    accepted_names: set[str] = set()
    plate_reports: dict[str, Any] = {}
    all_ledger_valid = True
    plate_mean_radii: dict[str, float] = {}

    for key, volume, material, _density, radius, center_z in PLATES:
        relevant = [item for item in keepouts if item.plate_key == key]
        plate_rows = [row for row in rows if row.get("plate_key") == key]
        accepted_rows = [row for row in plate_rows if row.get("status") == "ACCEPTED"]
        nonaccepted_rows = [row for row in plate_rows if row.get("status") != "ACCEPTED"]
        physical_holes: list[tuple[str, float, float, float]] = []
        keepout_mismatches: list[dict[str, Any]] = []
        row_mismatches: list[dict[str, Any]] = []

        for row in accepted_rows:
            try:
                x, y = float(row["x_instrument_cm"]), float(row["y_instrument_cm"])
                hole_radius = float(row["hole_radius_cm"])
                name = row["copy_name"]
                identity = name or f"{key}@({x},{y})"

                invariant = (
                    row["plate_volume"] == volume
                    and row["plate_material"] == material
                    and close(float(row["plate_radius_cm"]), radius)
                    and close(float(row["plate_center_z_cm"]), center_z)
                    and hole_radius > 0.0
                    and radius - math.hypot(x, y) - hole_radius
                    >= MINIMUM_SOLID_WEB_EDGE_CM - 1.0e-10
                )
                if not invariant:
                    raise ValueError(f"plate/edge invariant failed for {identity}")

                hits = [
                    item
                    for item in relevant
                    if intersects_keepout(
                        x,
                        y,
                        hole_radius,
                        item,
                        solid_margin_cm=MINIMUM_SOLID_WEB_EDGE_CM,
                    )
                ]
                if hits or any(
                    row[field]
                    for field in ("keepout_categories", "keepout_features", "keepout_kinds")
                ):
                    keepout_mismatches.append(
                        {
                            "copy_name": name,
                            "center_cm": [x, y],
                            "radius_cm": hole_radius,
                            "ledger_features": row["keepout_features"],
                            "intersected_features": [item.feature for item in hits],
                        }
                    )
                if not name or name in accepted_names:
                    raise ValueError(f"missing/duplicate accepted copy name: {name!r}")
                accepted_names.add(name)
                physical_holes.append((name, x, y, hole_radius))
            except Exception as exc:
                all_ledger_valid = False
                if len(row_mismatches) < 30:
                    row_mismatches.append({"row": row, "error": str(exc)})

        # Candidate rows are diagnostic only: no historical candidate count is
        # a gate.  If present, a keep-out skip must reproduce the 2 mm margin;
        # an unselected maximin candidate must be clear and nameless.
        for row in nonaccepted_rows:
            try:
                if row.get("copy_name"):
                    raise ValueError("non-accepted diagnostic row names a physical daughter")
                x, y = float(row["x_instrument_cm"]), float(row["y_instrument_cm"])
                hole_radius = float(row["hole_radius_cm"])
                hits = [
                    item
                    for item in relevant
                    if intersects_keepout(
                        x,
                        y,
                        hole_radius,
                        item,
                        solid_margin_cm=MINIMUM_SOLID_WEB_EDGE_CM,
                    )
                ]
                expected_categories = ";".join(sorted({item.category for item in hits}))
                expected_features = ";".join(item.feature for item in hits)
                expected_kinds = ";".join(item.kind for item in hits)
                if row.get("status") == "SKIPPED_KEEP_OUT":
                    if not hits or (
                        row["keepout_categories"],
                        row["keepout_features"],
                        row["keepout_kinds"],
                    ) != (expected_categories, expected_features, expected_kinds):
                        raise ValueError(
                            "keep-out skip does not match independent 2 mm-margin intersection"
                        )
                elif row.get("status") == "SKIPPED_EQUIVALENT_48_SELECTION":
                    if hits or any(
                        row[field]
                        for field in (
                            "keepout_categories",
                            "keepout_features",
                            "keepout_kinds",
                        )
                    ):
                        raise ValueError("unselected maximin candidate is not keep-out clear")
                else:
                    raise ValueError(f"unknown diagnostic status {row.get('status')!r}")
            except Exception as exc:
                all_ledger_valid = False
                if len(row_mismatches) < 30:
                    row_mismatches.append({"row": row, "error": str(exc)})

        pair_clearances: list[tuple[float, str, str, float]] = []
        for index, (name_a, x_a, y_a, r_a) in enumerate(physical_holes):
            for name_b, x_b, y_b, r_b in physical_holes[index + 1 :]:
                center_distance = math.hypot(x_a - x_b, y_a - y_b)
                pair_clearances.append(
                    (center_distance - r_a - r_b, name_a, name_b, center_distance)
                )
        minimum_pair = min(pair_clearances, default=(math.inf, "", "", math.inf))
        min_web = minimum_pair[0]
        min_edge = min(
            (
                radius - math.hypot(x, y) - hole_radius
                for _name, x, y, hole_radius in physical_holes
            ),
            default=-math.inf,
        )
        removed_area = sum(math.pi * hole_radius**2 for _name, _x, _y, hole_radius in physical_holes)
        reference_count = EQUIVALENT_D4_HOLE_COUNTS[key]
        target_area = reference_count * math.pi * REFERENCE_D4_HOLE_RADIUS_CM**2
        area_equivalent = math.isclose(
            removed_area, target_area, rel_tol=5.0e-9, abs_tol=5.0e-7
        )
        radius_values = [item[3] for item in physical_holes]
        uniform_radius = bool(radius_values) and max(radius_values) - min(radius_values) <= 1.0e-10
        if radius_values:
            plate_mean_radii[key] = sum(radius_values) / len(radius_values)
        expected_names = {
            f"SE3_HOLE_{key}_{index:05d}"
            for index in range(1, PHYSICAL_HOLES_PER_PLATE + 1)
        }
        actual_names = {item[0] for item in physical_holes}
        plate_ok = (
            len(physical_holes) == PHYSICAL_HOLES_PER_PLATE
            and actual_names == expected_names
            and uniform_radius
            and area_equivalent
            and not keepout_mismatches
            and not row_mismatches
            and min_edge >= MINIMUM_SOLID_WEB_EDGE_CM - 1.0e-10
            and min_web >= MINIMUM_SOLID_WEB_EDGE_CM - 1.0e-10
        )
        all_ledger_valid = all_ledger_valid and plate_ok
        plate_reports[key] = {
            "ledger_row_count": len(plate_rows),
            "accepted_physical_hole_count": len(physical_holes),
            "required_physical_hole_count": PHYSICAL_HOLES_PER_PLATE,
            "nonaccepted_diagnostic_row_count": len(nonaccepted_rows),
            "hole_radius_cm": plate_mean_radii.get(key),
            "uniform_radius_within_plate": uniform_radius,
            "equivalent_d4mm_hole_count": reference_count,
            "removed_area_cm2": removed_area,
            "target_equivalent_area_cm2": target_area,
            "equivalent_area_match": area_equivalent,
            "minimum_center_distance_cm": minimum_pair[3],
            "minimum_solid_web_cm": min_web,
            "minimum_solid_edge_cm": min_edge,
            "minimum_web_pair": [minimum_pair[1], minimum_pair[2]],
            "keepout_definition_count": len(relevant),
            "keepout_mismatch_count": len(keepout_mismatches),
            "keepout_mismatch_head": keepout_mismatches[:20],
            "row_mismatch_count": len(row_mismatches),
            "row_mismatch_head": row_mismatches[:20],
            "status": "PASS" if plate_ok else "FAIL",
        }

    unknown_plate_rows = [row for row in rows if row.get("plate_key") not in {p[0] for p in PLATES}]
    all_ledger_valid = all_ledger_valid and not unknown_plate_rows
    distinct_plate_radii = {round(value, 10) for value in plate_mean_radii.values()}
    varying_plate_radii = len(distinct_plate_radii) > 1
    all_ledger_valid = all_ledger_valid and varying_plate_radii
    recorder.record(
        "equivalent_48hole_area_web_edge_keepout_ledger_recomputed",
        all_ledger_valid,
    )

    copy_re = re.compile(r"^(SE3_HoleTemplate_(\S+))\.Copy (SE3_HOLE_\S+)$", re.MULTILINE)
    position_re = re.compile(r"^(SE3_HOLE_\S+)\.Position ([^ ]+) ([^ ]+) ([^ ]+)$", re.MULTILINE)
    mother_re = re.compile(r"^(SE3_HOLE_\S+)\.Mother (\S+)$", re.MULTILINE)
    visibility_re = re.compile(r"^(SE3_HOLE_\S+)\.Visibility (\S+)$", re.MULTILINE)
    copy_matches = list(copy_re.finditer(geo))
    position_matches = list(position_re.finditer(geo))
    mother_matches = list(mother_re.finditer(geo))
    visibility_matches = list(visibility_re.finditer(geo))
    geo_copies = {match.group(3): (match.group(1), match.group(2)) for match in copy_matches}
    positions = {
        match.group(1): tuple(float(match.group(i)) for i in (2, 3, 4))
        for match in position_matches
    }
    mothers = {match.group(1): match.group(2) for match in mother_matches}
    visibility = {match.group(1): match.group(2) for match in visibility_matches}
    geometry_mismatches: list[str] = []
    accepted_rows = [row for row in rows if row.get("status") == "ACCEPTED"]
    row_by_name = {row["copy_name"]: row for row in accepted_rows}

    if set(geo_copies) != set(row_by_name):
        geometry_mismatches.append(
            f"copy-name set differs: geo={len(geo_copies)} ledger={len(row_by_name)}"
        )
    for label, matches in (
        ("copy", copy_matches),
        ("position", position_matches),
        ("mother", mother_matches),
        ("visibility", visibility_matches),
    ):
        if len(matches) != len(row_by_name):
            geometry_mismatches.append(
                f"hole {label} assignment count {len(matches)} != {len(row_by_name)}"
            )
    plate_by_key = {item[0]: item for item in PLATES}
    for name in sorted(set(geo_copies) & set(row_by_name)):
        row = row_by_name[name]
        key = row["plate_key"]
        volume = plate_by_key[key][1]
        expected_template = f"SE3_HoleTemplate_{key}"
        expected_position = (float(row["x_instrument_cm"]), float(row["y_instrument_cm"]), 0.0)
        if geo_copies[name][0] != expected_template:
            geometry_mismatches.append(f"{name}: wrong template {geo_copies[name][0]}")
        actual_position = positions.get(name)
        if actual_position is None or not all(
            close(actual, expected, tolerance=1.0e-9)
            for actual, expected in zip(actual_position, expected_position)
        ):
            geometry_mismatches.append(f"{name}: wrong/missing position {positions.get(name)}")
        if mothers.get(name) != volume:
            geometry_mismatches.append(f"{name}: wrong/missing mother {mothers.get(name)}")
        if visibility.get(name) != "1":
            geometry_mismatches.append(f"{name}: visibility is {visibility.get(name)}")

    for key, _volume, _material, _density, _radius, _z in PLATES:
        template = f"SE3_HoleTemplate_{key}"
        template_pattern = re.compile(
            rf"^Volume {re.escape(template)}\n"
            rf"{re.escape(template)}\.Material Vacuum\n"
            rf"{re.escape(template)}\.Visibility 1\n"
            rf"{re.escape(template)}\.Shape PCON 0 360 2 -0\.2 0 ([^ ]+) 0\.2 0 ([^\n]+)\n",
            re.MULTILINE,
        )
        matches = list(template_pattern.finditer(geo))
        expected_radius = plate_mean_radii.get(key)
        if len(matches) != 1 or expected_radius is None:
            geometry_mismatches.append(f"{key}: exact Vacuum template block count != 1")
        else:
            first_radius, second_radius = (float(value) for value in matches[0].groups())
            if not (
                close(first_radius, expected_radius, tolerance=1.0e-9)
                and close(second_radius, expected_radius, tolerance=1.0e-9)
            ):
                geometry_mismatches.append(
                    f"{key}: template radii {(first_radius, second_radius)} != ledger {expected_radius}"
                )

    if "SE3_HOLE_" in det or "SE3_HoleTemplate_" in det:
        geometry_mismatches.append("hole/template unexpectedly has DET scorer references")
    geometry_ok = not geometry_mismatches and len(accepted_names) == len(accepted_rows)
    recorder.record("hole_ledger_matches_geo_daughters", geometry_ok, "; ".join(geometry_mismatches[:5]))

    return (
        {
            "status": "PASS" if all_ledger_valid and geometry_ok else "FAIL",
            "definition_source": {
                "path": str(BUILDER),
                "sha256": builder_hash_after,
                "role": "keep-out dimensions only; enumeration/intersection is independent",
            },
            "ledger_row_total": len(rows),
            "accepted_total": len(accepted_rows),
            "required_accepted_total": PHYSICAL_HOLES_PER_PLATE * len(PLATES),
            "nonaccepted_diagnostic_row_total": len(rows) - len(accepted_rows),
            "plate_dependent_radii": varying_plate_radii,
            "geometry_copy_total": len(geo_copies),
            "unknown_plate_row_count": len(unknown_plate_rows),
            "geometry_mismatch_count": len(geometry_mismatches),
            "geometry_mismatch_head": geometry_mismatches[:30],
            "plates": plate_reports,
        },
        rows,
    )


def exact_port_volume_cm3() -> float:
    half = 1.898
    rin, rout = 27.0, 29.0

    def primitive(radius: float, y: float) -> float:
        return 0.5 * (
            y * math.sqrt(radius * radius - y * y)
            + radius * radius * math.asin(y / radius)
        )

    shell_cross_section = 2.0 * (primitive(rout, half) - primitive(rin, half))
    return shell_cross_section * (2.0 * half)


def numeric_fields_match(row: dict[str, str], expected: dict[str, float | int | str]) -> list[str]:
    mismatches: list[str] = []
    for field, value in expected.items():
        actual = row.get(field, "")
        if isinstance(value, str):
            if actual != value:
                mismatches.append(f"{field}: {actual!r} != {value!r}")
        elif isinstance(value, int):
            try:
                if int(actual) != value:
                    mismatches.append(f"{field}: {actual!r} != {value}")
            except ValueError:
                mismatches.append(f"{field}: non-integer {actual!r}")
        else:
            try:
                if not close(float(actual), value):
                    mismatches.append(f"{field}: {actual!r} != {value:.17g}")
            except ValueError:
                mismatches.append(f"{field}: non-float {actual!r}")
    return mismatches


def validate_mass(
    recorder: Recorder,
    hole_rows: list[dict[str, str]],
) -> dict[str, Any]:
    path = DATA_DIR / "se3_mass_ledger.csv"
    fields, rows = read_csv(path)
    missing_mass_fields = sorted(set(MASS_FIELDS) - set(fields))
    recorder.record(
        "mass_ledger_required_fields_present",
        not missing_mass_fields,
        f"missing fields: {missing_mass_fields}; actual={fields}",
    )
    by_component = {row["component"]: row for row in rows}
    duplicate_components = len(by_component) != len(rows)
    mismatches: dict[str, list[str]] = {}
    component_deltas: list[float] = []
    component_before_masses: list[float] = []
    component_after_masses: list[float] = []
    five_plate_before = 0.0
    five_plate_after = 0.0

    for key, volume_name, material, density, radius, _z in PLATES:
        plate_rows = [row for row in hole_rows if row["plate_key"] == key]
        accepted = [row for row in plate_rows if row["status"] == "ACCEPTED"]
        full_before = math.pi * radius**2 * OLD_THICKNESS_CM
        full_after = math.pi * radius**2 * NEW_THICKNESS_CM
        removed_area = sum(
            math.pi * float(row["hole_radius_cm"]) ** 2 for row in accepted
        )
        void = removed_area * NEW_THICKNESS_CM
        net_after = full_after - void
        before_mass = full_before * density / 1000.0
        after_mass = net_after * density / 1000.0
        delta = after_mass - before_mass
        five_plate_before += before_mass
        five_plate_after += after_mass
        component_deltas.append(delta)
        component_before_masses.append(before_mass)
        component_after_masses.append(after_mass)
        expected: dict[str, float | int | str] = {
            "scope": "cold_plate",
            "material_before": material,
            "material_after": material,
            "density_g_cm3": density,
            "radius_cm": radius,
            "thickness_before_cm": OLD_THICKNESS_CM,
            "thickness_after_cm": NEW_THICKNESS_CM,
            "accepted_hole_count": len(accepted),
            "void_cm3": void,
            "volume_before_cm3": full_before,
            "volume_after_cm3": net_after,
            "mass_before_kg": before_mass,
            "mass_after_kg": after_mass,
            "delta_mass_kg": delta,
            "open_fraction": void / full_after,
        }
        row = by_component.get(volume_name)
        if row is not None and "hole_radius_cm" in fields:
            expected["hole_radius_cm"] = float(accepted[0]["hole_radius_cm"])
        if row is not None and "hole_diameter_mm" in fields:
            expected["hole_diameter_mm"] = 20.0 * float(accepted[0]["hole_radius_cm"])
        if row is not None and "equivalent_source_hole_count" in fields:
            expected["equivalent_source_hole_count"] = EQUIVALENT_D4_HOLE_COUNTS[key]
        mismatches[volume_name] = ["missing row"] if row is None else numeric_fields_match(row, expected)

    shield_specs = (
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
    for name, before_material, after_material, volume, before_density, after_density in shield_specs:
        before_mass = volume * before_density / 1000.0
        after_mass = volume * after_density / 1000.0
        delta = after_mass - before_mass
        component_deltas.append(delta)
        component_before_masses.append(before_mass)
        component_after_masses.append(after_mass)
        expected = {
            "scope": "nearfield_shield",
            "material_before": before_material,
            "material_after": after_material,
            "density_g_cm3": after_density,
            "volume_before_cm3": volume,
            "volume_after_cm3": volume if after_density else 0.0,
            "mass_before_kg": before_mass,
            "mass_after_kg": after_mass,
            "delta_mass_kg": delta,
        }
        row = by_component.get(name)
        mismatches[name] = ["missing row"] if row is None else numeric_fields_match(row, expected)

    port_name = "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_focused_port"
    port_volume = exact_port_volume_cm3()
    port_mass = port_volume * 0.95 / 1000.0
    port_expected: dict[str, float | int | str] = {
        "scope": "bpe_port",
        "material_before": "BoratedPolyethylene5wtB",
        "material_after": "Vacuum aperture",
        "density_g_cm3": 0.95,
        "thickness_before_cm": 2.0,
        "thickness_after_cm": 0.0,
        "void_cm3": port_volume,
        "volume_before_cm3": port_volume,
        "volume_after_cm3": 0.0,
        "mass_before_kg": port_mass,
        "mass_after_kg": 0.0,
        "delta_mass_kg": -port_mass,
        "open_fraction": 1.0,
    }
    row = by_component.get(port_name)
    mismatches[port_name] = ["missing row"] if row is None else numeric_fields_match(row, port_expected)
    component_deltas.append(-port_mass)
    component_before_masses.append(port_mass)
    component_after_masses.append(0.0)

    total_name = "SE3_WHITELIST_EXACT_DELTA"
    total_expected: dict[str, float | int | str] = {
        "scope": "touched_components_total",
        "accepted_hole_count": sum(row["status"] == "ACCEPTED" for row in hole_rows),
        "mass_before_kg": sum(component_before_masses),
        "mass_after_kg": sum(component_after_masses),
        "delta_mass_kg": sum(component_deltas),
    }
    row = by_component.get(total_name)
    mismatches[total_name] = ["missing row"] if row is None else numeric_fields_match(row, total_expected)

    expected_components = {
        item[1] for item in PLATES
    } | {item[0] for item in shield_specs} | {port_name, total_name}
    extra_components = sorted(set(by_component) - expected_components)
    failed = {name: problems for name, problems in mismatches.items() if problems}
    ok = not duplicate_components and not failed and not extra_components and len(rows) == 11
    recorder.record("mass_ledger_independent_exact_recalculation", ok, repr(failed)[:1000])
    return {
        "status": "PASS" if ok else "FAIL",
        "row_count": len(rows),
        "duplicate_component": duplicate_components,
        "extra_components": extra_components,
        "mismatches": failed,
        "five_plate_mass_before_kg": five_plate_before,
        "five_plate_mass_after_kg": five_plate_after,
        "five_plate_delta_kg": five_plate_after - five_plate_before,
        "touched_component_delta_kg": sum(component_deltas),
        "touched_component_mass_before_kg": sum(component_before_masses),
        "touched_component_mass_after_kg": sum(component_after_masses),
        "bpe_port_void_cm3": port_volume,
        "method": "independent analytic recalculation from explicit SE3 solids and accepted-hole count",
        "whole_instrument_native_mass": "not evaluated by this static tool",
    }


def parse_geometry_symbols(geo: str, intro: str, det: str) -> dict[str, Any]:
    geometry_text = intro + "\n" + geo
    volume_declarations = re.findall(r"^Volume\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    copy_pairs = re.findall(r"^(\S+)\.Copy\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    copies = [destination for _source, destination in copy_pairs]
    volume_instances = set(volume_declarations) | set(copies)
    duplicate_volumes = sorted(
        name for name, count in Counter(volume_declarations + copies).items() if count != 1
    )

    mothers = re.findall(r"^(\S+)\.Mother\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    unresolved_copy_sources = sorted({source for source, _dest in copy_pairs if source not in volume_instances})
    unresolved_mother_lhs = sorted({lhs for lhs, _mother in mothers if lhs not in volume_instances})
    unresolved_mothers = sorted(
        {mother for _lhs, mother in mothers if mother != "0" and mother not in volume_instances}
    )

    shape_declarations = re.findall(r"^Shape\s+(\S+)\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    shape_types = {name: kind for kind, name in shape_declarations}
    duplicate_shapes = sorted(
        name for name, count in Counter(name for _kind, name in shape_declarations).items() if count != 1
    )
    orientation_declarations = re.findall(r"^Orientation\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    orientations = set(orientation_declarations)
    duplicate_orientations = sorted(
        name for name, count in Counter(orientation_declarations).items() if count != 1
    )

    primitive_shapes = {
        "BRIK", "TUBS", "SPHE", "TRD1", "TRD2", "CONE", "CONS", "PCON", "PGON",
        "TRAP", "GTRA", "ELTU", "PARA", "HYPE", "ARB8",
    }
    unresolved_volume_shapes: list[str] = []
    for line in geometry_text.splitlines():
        match = re.match(r"^(\S+)\.Shape\s+(\S+)(?:\s+.*)?$", line)
        if not match or match.group(1) not in volume_instances:
            continue
        reference = match.group(2)
        if reference not in primitive_shapes and reference not in shape_types:
            unresolved_volume_shapes.append(f"{match.group(1)} -> {reference}")

    unresolved_boolean_refs: list[str] = []
    for line in geometry_text.splitlines():
        match = re.match(r"^(\S+)\.Parameters\s+(.+)$", line)
        if not match:
            continue
        shape_name, tail = match.groups()
        kind = shape_types.get(shape_name)
        if kind not in {"Subtraction", "Union", "Intersection"}:
            continue
        tokens = tail.split()
        if len(tokens) != 3:
            unresolved_boolean_refs.append(f"{shape_name}: expected 3 refs, got {tokens}")
            continue
        first, second, orientation = tokens
        if first not in shape_types:
            unresolved_boolean_refs.append(f"{shape_name}: missing first shape {first}")
        if second not in shape_types:
            unresolved_boolean_refs.append(f"{shape_name}: missing second shape {second}")
        if orientation not in orientations:
            unresolved_boolean_refs.append(f"{shape_name}: missing orientation {orientation}")

    detector_declarations = re.findall(
        r"^(?:Scintillator|MDCalorimeter)\s+(\S+)\s*$", det, re.MULTILINE
    )
    duplicate_detectors = sorted(
        name for name, count in Counter(detector_declarations).items() if count != 1
    )
    unresolved_detector_volumes: list[str] = []
    for kind, target in re.findall(
        r"^\S+\.(SensitiveVolume|DetectorVolume)\s+(\S+)\s*$", det, re.MULTILINE
    ):
        if target not in volume_instances:
            unresolved_detector_volumes.append(f"{kind} -> {target}")

    material_by_decl = dict(
        re.findall(r"^(\S+)\.Material\s+(\S+)\s*$", geometry_text, re.MULTILINE)
    )
    copy_source = {destination: source for source, destination in copy_pairs}
    mother_map = dict(mothers)

    def material_of(name: str) -> str | None:
        seen: set[str] = set()
        while name in copy_source:
            if name in seen:
                return None
            seen.add(name)
            name = copy_source[name]
        return material_by_decl.get(name)

    unresolved_material_instances: list[str] = []
    placed_histogram: Counter[str] = Counter()
    se3_visible_vacuum_holes = 0
    for instance in mother_map:
        material = material_of(instance)
        if material is None:
            unresolved_material_instances.append(instance)
        else:
            placed_histogram[material] += 1
            if instance.startswith("SE3_HOLE_") and material == "Vacuum":
                se3_visible_vacuum_holes += 1

    errors = {
        "duplicate_volumes_or_copies": duplicate_volumes,
        "unresolved_copy_sources": unresolved_copy_sources,
        "unresolved_mother_lhs": unresolved_mother_lhs,
        "unresolved_mothers": unresolved_mothers,
        "duplicate_shapes": duplicate_shapes,
        "duplicate_orientations": duplicate_orientations,
        "unresolved_volume_shapes": unresolved_volume_shapes,
        "unresolved_boolean_refs": unresolved_boolean_refs,
        "duplicate_detectors": duplicate_detectors,
        "unresolved_detector_volumes": unresolved_detector_volumes,
        "unresolved_material_instances": unresolved_material_instances,
    }
    ok = not any(errors.values())
    nonvacuum_count = sum(
        count for material, count in placed_histogram.items() if material != "Vacuum"
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "volume_declaration_count": len(volume_declarations),
        "copy_count": len(copies),
        "placed_instance_count": len(mother_map),
        "shape_count": len(shape_declarations),
        "orientation_count": len(orientation_declarations),
        "detector_count": len(detector_declarations),
        "nonvacuum_placed_solid_count": nonvacuum_count,
        "se3_visible_vacuum_hole_count": se3_visible_vacuum_holes,
        "contract_visible_solid_count": nonvacuum_count + se3_visible_vacuum_holes,
        "placed_material_histogram": dict(sorted(placed_histogram.items())),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=AUDIT_DIR / "se3_geometry_validation.json",
        help="validation JSON destination",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    recorder = Recorder()
    started = dt.datetime.now(dt.timezone.utc)
    report: dict[str, Any] = {
        "model_identity": "SE3",
        "validation_scope": "static geometry, whitelist, ledgers, and local symbol graph",
        "transport_launched": False,
        "started_at_utc": started.isoformat(),
    }

    try:
        required = list(SE3_FILES.values()) + [
            DATA_DIR / "se3_source_manifest.json",
            DATA_DIR / "se3_hole_pattern.csv",
            DATA_DIR / "se3_mass_ledger.csv",
            BUILDER,
        ] + [spec[0] for spec in AUTHORITY_SPECS.values()]
        missing = [str(path) for path in required if not path.is_file()]
        recorder.require(not missing, f"missing prerequisites: {missing}")

        authority_records: dict[str, Any] = {}
        authority_ok = True
        for key, (path, expected_size, expected_hash) in AUTHORITY_SPECS.items():
            actual_size = path.stat().st_size
            actual_hash = sha256(path)
            item_ok = actual_hash == expected_hash and (
                expected_size < 0 or actual_size == expected_size
            )
            authority_ok = authority_ok and item_ok
            authority_records[key] = {
                "path": str(path),
                "size_bytes": actual_size,
                "expected_size_bytes": None if expected_size < 0 else expected_size,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "status": "PASS" if item_ok else "FAIL",
            }
        recorder.record("pinned_s3d_o8_authority_hashes", authority_ok)
        report["authority"] = authority_records

        manifest_path = DATA_DIR / "se3_source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_authority_ok = all(
            manifest.get("authority", {}).get(key, {}).get("sha256") == expected_hash
            for key, (_path, _size, expected_hash) in AUTHORITY_SPECS.items()
        )
        manifest_core: dict[str, Any] = {}
        generated_ok = True
        for key, path in SE3_FILES.items():
            actual_hash = sha256(path)
            actual_size = path.stat().st_size
            record = manifest.get("generated_core", {}).get(key, {})
            item_ok = (
                record.get("sha256") == actual_hash
                and record.get("size_bytes") == actual_size
                and Path(record.get("path", "")).resolve() == path.resolve()
            )
            generated_ok = generated_ok and item_ok
            manifest_core[key] = {
                "path": str(path.resolve()),
                "sha256": actual_hash,
                "size_bytes": actual_size,
                "manifest_match": item_ok,
            }
        manifest_metadata_ok = (
            manifest.get("model_identity") == "SE3"
            and manifest.get("bpe_mode") == "P20-port"
            and manifest.get("transport_launched") is False
            and manifest.get("status") == "PASS"
        )
        recorder.record("source_manifest_authority_hashes", manifest_authority_ok)
        recorder.record("source_manifest_generated_core_hashes", generated_ok)
        recorder.record("source_manifest_se3_p20_nontransport_identity", manifest_metadata_ok)
        report["source_manifest"] = {
            "path": str(manifest_path.resolve()),
            "sha256": sha256(manifest_path),
            "generated_core": manifest_core,
            "metadata_match": manifest_metadata_ok,
        }

        authority_text = {
            key: AUTHORITY_SPECS[key][0].read_text(encoding="utf-8")
            for key in ("setup", "geo", "det", "intro", "materials")
        }
        se3_text = {key: path.read_text(encoding="utf-8") for key, path in SE3_FILES.items()}

        normalized: dict[str, Any] = {}
        geo_rebuilt, geo_ops = reconstruct_authority_geo(se3_text["geo"])
        normalized["geo"] = residual_diff(
            authority_text["geo"], geo_rebuilt, "S3d-O8.geo", "SE3.geo normalized"
        )
        normalized["geo"]["normalization_exact_counts"] = geo_ops
        det_rebuilt, det_ops = reconstruct_authority_det(se3_text["det"])
        normalized["det"] = residual_diff(
            authority_text["det"], det_rebuilt, "S3d-O8.det", "SE3.det normalized"
        )
        normalized["det"]["normalization_exact_counts"] = det_ops
        setup_rebuilt, setup_ops = reconstruct_authority_setup(se3_text["setup"])
        normalized["setup"] = residual_diff(
            authority_text["setup"], setup_rebuilt, "S3d-O8.geo.setup", "SE3 setup normalized"
        )
        normalized["setup"]["normalization_exact_counts"] = setup_ops
        normalized["intro"] = residual_diff(
            authority_text["intro"], se3_text["intro"], "S3d-O8 intro", "SE3 intro"
        )
        normalized["materials"] = residual_diff(
            authority_text["materials"],
            se3_text["materials"],
            "S3d-O8 materials",
            "SE3 materials",
        )
        diff_ok = all(item["equal"] for item in normalized.values())
        recorder.record("whitelist_normalized_diff_zero", diff_ok)
        report["whitelist_normalized_diff"] = normalized

        frozen_orientation_ok = (
            se3_text["intro"].count("InstrumentFrame.Rotation 0 45 0") == 1
            and "MASS511" not in "\n".join(se3_text.values())
        )
        plastic_ok = (
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm.Shape "
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_NF2ReliefStep08Shape"
            in se3_text["geo"]
            and "SE3_BPE_FocusedPort" not in "\n".join(
                line for line in se3_text["geo"].splitlines() if "Plastic" in line
            )
        )
        bpe_ok = (
            se3_text["geo"].count(BPE_PORT_ADDITION) == 1
            and se3_text["geo"].count(
                "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm.Shape SE3_BPE_FocusedPortFinalShape"
            )
            == 1
        )
        recorder.record("instrument_45deg_sky_orientation_frozen", frozen_orientation_ok)
        recorder.record("plastic_scintillator_uncut", plastic_ok)
        recorder.record("bpe_p20_focused_port_exact", bpe_ok)

        hole_report, hole_rows = validate_holes(recorder, se3_text["geo"], se3_text["det"])
        report["hole_ledger"] = hole_report
        report["mass_ledger"] = validate_mass(recorder, hole_rows)

        symbols = parse_geometry_symbols(
            se3_text["geo"], se3_text["intro"], se3_text["det"]
        )
        authority_symbols = parse_geometry_symbols(
            authority_text["geo"], authority_text["intro"], authority_text["det"]
        )
        recorder.record("duplicate_and_reference_resolution", symbols["status"] == "PASS")
        recorder.record(
            "nonvacuum_solid_count_3094",
            symbols["nonvacuum_placed_solid_count"] == 3094,
            str(symbols["nonvacuum_placed_solid_count"]),
        )
        recorder.record(
            "physical_hole_count_240",
            hole_report["accepted_total"] == 240,
            str(hole_report["accepted_total"]),
        )
        recorder.record(
            "contract_visible_solid_count_3334",
            symbols["contract_visible_solid_count"] == 3334,
            str(symbols["contract_visible_solid_count"]),
        )
        expected_hist = Counter(authority_symbols["placed_material_histogram"])
        expected_hist["Nb"] -= 2
        expected_hist["MuMetal"] -= 2
        expected_hist["Aluminium"] += 2
        expected_hist["Vacuum"] += hole_report["accepted_total"]
        expected_hist = Counter({key: value for key, value in expected_hist.items() if value})
        actual_hist = Counter(symbols["placed_material_histogram"])
        material_delta_ok = actual_hist == expected_hist
        recorder.record("placement_material_histogram_exact_se3_delta", material_delta_ok)
        symbols["authority_nonvacuum_placed_solid_count"] = authority_symbols[
            "nonvacuum_placed_solid_count"
        ]
        symbols["expected_se3_material_histogram"] = dict(sorted(expected_hist.items()))
        symbols["material_histogram_exact_delta"] = material_delta_ok
        report["duplicate_and_reference_resolution"] = symbols

    except Exception as exc:
        recorder.failures.append(f"validator exception: {type(exc).__name__}: {exc}")
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}

    status = "PASS" if recorder.checks and all(recorder.checks.values()) and not recorder.failures else "FAIL"
    report.update(
        {
            "status": status,
            "physics_status": (
                "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN"
                if status == "PASS"
                else "GEOMETRY VALIDATION FAILED — PHYSICS UNKNOWN"
            ),
            "checks": recorder.checks,
            "failures": recorder.failures,
            "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "limitations": [
                "No Cosima/Geomega construction or overlap check is performed by this script.",
                "Whole-instrument native mass and navigator/ray chords require their separate gates.",
                "No prompt, delayed, activation, signal, or full-family transport was launched.",
            ],
        }
    )
    atomic_json(output, report)
    print(json.dumps({"status": status, "output": str(output)}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
