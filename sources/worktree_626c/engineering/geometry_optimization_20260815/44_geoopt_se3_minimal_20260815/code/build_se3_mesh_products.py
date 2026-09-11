#!/usr/bin/env python3
"""Parse the native SE3 Geant4 WRL into auditable mesh products.

The WRL is the geometry-only VRML2FILE export.  Native vertices are Geant4
world millimetres.  Instrument-frame vertices are stored in centimetres after
reading ``InstrumentFrame.Position`` and ``InstrumentFrame.Rotation`` from the
SE3 Intro geometry.  No transport or event data are read.

Vacuum hole daughters are intentionally visible in the native WRL.  Every
accepted row in ``se3_hole_pattern.csv`` must therefore map to exactly one WRL
solid, and its native bounding box must close to the ledger centre, its
candidate-owned equivalent-area radius, and the through-plate axial span.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


SCHEMA_VERSION = "se3_geometry_mesh_products_v1"
ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_DIR = ROOT / "geometry"
DATA_DIR = ROOT / "data"
AUDIT_DIR = ROOT / "audit"

DEFAULT_SOURCE = Path(__file__).resolve().parent / "se3_geometry_only.source"
DEFAULT_SETUP = GEOMETRY_DIR / "DEMO2_DR_v3p5_SE3.geo.setup"
DEFAULT_MAIN = GEOMETRY_DIR / "DEMO2_DR_v3p5_SE3.geo"
DEFAULT_WRL = GEOMETRY_DIR / "se3_native_geant4_full.wrl"
DEFAULT_HOLES = DATA_DIR / "se3_hole_pattern.csv"
DEFAULT_MANIFEST = DATA_DIR / "se3_geometry_volume_manifest.csv"
DEFAULT_MESH = DATA_DIR / "se3_geometry_mesh_products.npz"
DEFAULT_AUDIT = AUDIT_DIR / "se3_mesh_validation.json"

EXPECTED_NONVACUUM_SOLIDS = 3094
EXPECTED_EQUIVALENT_HOLES = 240
EXPECTED_HOLES_PER_PLATE = 48
SOURCE_HOLE_RADIUS_CM = 0.2
EXPECTED_BASE_COPIES = 2880
EXPECTED_VOLUME_DEFINITIONS = 237
EXPECTED_NONVACUUM_MATERIAL_COUNTS = {
    "Ta": 2256,
    "W": 625,
    "StainlessSteel": 78,
    "Copper": 60,
    "Aluminium": 32,
    "G10": 11,
    "Silicon": 6,
    "CuNi": 6,
    "NbTiCableProxy": 5,
    "PlasticScintillator": 3,
    "BGO": 3,
    "Kapton": 3,
    "BoratedPolyethylene5wtB": 3,
    "Be": 1,
    "SilverSinterProxy": 1,
    "CharcoalProxy": 1,
}


@dataclass(frozen=True)
class PlateSpec:
    name: str
    radius_cm: float
    center_z_cm: float
    material: str
    short_label: str


PLATES = (
    PlateSpec("ColdPlate_MXC_50mK_SD_anchor", 15.0, 0.0, "Copper", "50 mK"),
    PlateSpec("ColdPlate_CP_100mK_intercept", 15.0, 5.0, "Copper", "100 mK"),
    PlateSpec("ColdPlate_Still_0p7K", 15.0, 11.0, "Copper", "0.7 K"),
    PlateSpec("ColdPlate_4K", 17.5, 20.0, "Copper", "4 K"),
    PlateSpec("ColdPlate_60K", 17.5, 29.0, "Aluminium", "60 K"),
)
PLATE_BY_NAME = {plate.name: plate for plate in PLATES}
SOURCE_ACCEPTED_HOLE_COUNTS = {
    "ColdPlate_MXC_50mK_SD_anchor": 1623,
    "ColdPlate_CP_100mK_intercept": 1744,
    "ColdPlate_Still_0p7K": 1567,
    "ColdPlate_4K": 1920,
    "ColdPlate_60K": 1998,
}

PLATE_ALIASES: dict[str, str] = {}
for _plate in PLATES:
    for _alias in (
        _plate.name,
        _plate.short_label,
        _plate.short_label.replace(" ", ""),
        _plate.name.removeprefix("ColdPlate_"),
    ):
        PLATE_ALIASES[_alias.lower()] = _plate.name

NEW_AL_SHIELDS = {
    "SE3_Al_Shield_Inner_Cylinder_2mm",
    "SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm",
}
FORBIDDEN_OLD_SHIELDS = {
    "MuMetal_MagShield_Outer_Cylinder_2mm",
    "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm",
    "Nb_MagShield_Inner_Cylinder_2mm",
    "Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
}

BPE_NAMES = (
    "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm",
    "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm",
    "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm",
)
PLASTIC_NAMES = (
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
)
BGO_NAMES = (
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
)
KAPTON_NAMES = (
    "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
)
OUTER_AL_NAMES = (
    "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm",
    "Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm",
    "Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm",
)
WINDOW_CSG_NAMES = (
    "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
    "Still_Shield_Al_side_window_side_wall_rectcut_window_band",
    "Shield_4K_Al_side_window_side_wall_rectcut_window_band",
    "Shield_60K_Al_side_window_side_wall_rectcut_window_band",
    "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_rectcut_window_band",
)
WINDOW_FOILS = (
    "Win_50mK_Al_foil_side",
    "Win_Still_Al_foil_side",
    "Win_4K_Al_foil_side",
    "Win_60K_Al_foil_side",
    "Win_Be_Vacuum_150um_side",
    "Win_Outer_Al_Filter_side",
    "Win_MagShield_Al_foil_side",
)
EXPECTED_PLACED_CSG = set(
    WINDOW_CSG_NAMES
    + BPE_NAMES
    + PLASTIC_NAMES
    + (BGO_NAMES[0],)
    + KAPTON_NAMES
    + OUTER_AL_NAMES
    + BGO_NAMES[1:]
)


class MeshProductError(RuntimeError):
    """An input cannot be reconciled without ambiguity."""


@dataclass
class GeoObject:
    name: str
    kind: str
    source: str = ""
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedGeo:
    name: str
    kind: str
    source: str
    material: str
    mother: str
    shape_token: str
    shape_kind: str
    placed: bool
    csg: bool


@dataclass
class RawSolid:
    tag: str
    description: str
    vertices_mm: list[tuple[float, float, float]]
    faces: list[list[int]]
    line_start: int
    line_end: int


@dataclass(frozen=True)
class HoleRecord:
    row_number: int
    plate: str
    accepted: bool
    decision: str
    geometry_name: str
    x_cm: float
    y_cm: float
    radius_cm: float
    keepout_reason: str


def resolve_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise MeshProductError("Refusing to write an empty volume manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w+b", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            np.savez_compressed(handle, **arrays)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def include_paths(path: Path) -> list[Path]:
    result: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        match = re.fullmatch(r"Include\s+(\S+)", line)
        if match:
            result.append(resolve_path(match.group(1), path.parent))
    return result


def find_intro(main_geo: Path) -> Path:
    candidates = [path for path in include_paths(main_geo) if path.name.startswith("Intro_")]
    if len(candidates) != 1:
        raise MeshProductError(f"Expected one Intro_ Include in {main_geo}, found {candidates}")
    return candidates[0]


def parse_geomega(intro_geo: Path, main_geo: Path) -> tuple[dict[str, GeoObject], dict[str, str]]:
    objects: dict[str, GeoObject] = {}
    shape_kinds: dict[str, str] = {}
    auxiliary: set[str] = set()
    for path in (intro_geo, main_geo):
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith(("#", "//")):
                continue
            match = re.fullmatch(r"Volume\s+(\S+)", line)
            if match:
                name = match.group(1)
                if name in objects:
                    raise MeshProductError(f"Duplicate Volume/Copy {name} at {path}:{line_number}")
                objects[name] = GeoObject(name, "volume")
                continue
            match = re.fullmatch(r"(\S+)\.Copy\s+(\S+)", line)
            if match:
                source, name = match.groups()
                if name in objects:
                    raise MeshProductError(f"Duplicate Volume/Copy {name} at {path}:{line_number}")
                objects[name] = GeoObject(name, "copy", source)
                continue
            match = re.fullmatch(r"Shape\s+(\S+)\s+(\S+)", line)
            if match:
                kind, name = match.groups()
                shape_kinds[name] = kind
                auxiliary.add(name)
                continue
            match = re.fullmatch(r"Orientation\s+(\S+)", line)
            if match:
                auxiliary.add(match.group(1))
                continue
            match = re.fullmatch(
                r"(\S+)\.(Material|Visibility|Shape|Position|Rotation|Mother)\s+(.+)", line
            )
            if match:
                name, key, value = match.groups()
                if name in auxiliary:
                    continue
                if name not in objects:
                    raise MeshProductError(
                        f"Property precedes Volume/Copy {name} at {path}:{line_number}"
                    )
                objects[name].properties[key] = value.strip()
    for obj in objects.values():
        if obj.source and obj.source not in objects:
            raise MeshProductError(f"Copy {obj.name} has missing source {obj.source}")
    return objects, shape_kinds


def resolve_geomega(
    objects: dict[str, GeoObject], shape_kinds: dict[str, str]
) -> dict[str, ResolvedGeo]:
    @lru_cache(maxsize=None)
    def inherit(name: str, key: str, trail: tuple[str, ...] = ()) -> str:
        if name in trail:
            raise MeshProductError(f"Copy inheritance cycle: {' -> '.join(trail + (name,))}")
        obj = objects[name]
        if key in obj.properties:
            return obj.properties[key]
        if obj.source:
            return inherit(obj.source, key, trail + (name,))
        return ""

    result: dict[str, ResolvedGeo] = {}
    for name, obj in objects.items():
        material = inherit(name, "Material").split(maxsplit=1)[0]
        shape_value = inherit(name, "Shape")
        shape_token = shape_value.split(maxsplit=1)[0] if shape_value else ""
        shape_kind = shape_kinds.get(shape_token, shape_token)
        mother_value = obj.properties.get("Mother", "")
        mother = mother_value.split(maxsplit=1)[0] if mother_value else ""
        placed = bool(mother and mother != "0")
        result[name] = ResolvedGeo(
            name=name,
            kind=obj.kind,
            source=obj.source,
            material=material,
            mother=mother,
            shape_token=shape_token,
            shape_kind=shape_kind,
            placed=placed,
            csg=shape_kind.lower() in {"subtraction", "union", "intersection"},
        )
    return result


def parse_triplet(value: str, label: str) -> np.ndarray:
    parts = value.split()
    if len(parts) < 3:
        raise MeshProductError(f"Expected three numeric values for {label}: {value!r}")
    try:
        array = np.asarray([float(parts[0]), float(parts[1]), float(parts[2])], dtype=float)
    except ValueError as exc:
        raise MeshProductError(f"Non-numeric {label}: {value!r}") from exc
    if not np.isfinite(array).all():
        raise MeshProductError(f"Non-finite {label}: {value!r}")
    return array


def rotation_xyz_matrix(rotation_deg: np.ndarray) -> np.ndarray:
    rx, ry, rz = np.deg2rad(rotation_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = np.asarray(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=float)
    rot_y = np.asarray(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=float)
    rot_z = np.asarray(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=float)
    return rot_z @ rot_y @ rot_x


def _column(fieldnames: list[str], candidates: Iterable[str], label: str) -> str:
    lower = {name.lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise MeshProductError(f"Hole ledger lacks {label}; columns={fieldnames}")


def _accepted(value: str) -> bool:
    token = value.strip().lower().replace("-", "_")
    if token in {"1", "true", "yes", "y", "accepted", "accept", "keep", "hole", "pass"}:
        return True
    if token in {
        "0", "false", "no", "n", "skipped", "skip", "reject", "keepout",
        "skipped_keep_out", "skipped_equivalent_48_selection", "fail",
    }:
        return False
    raise MeshProductError(f"Unrecognised hole acceptance token: {value!r}")


def _plate_name(value: str) -> str:
    key = value.strip().lower()
    if key in PLATE_ALIASES:
        return PLATE_ALIASES[key]
    for alias, name in PLATE_ALIASES.items():
        if alias and alias in key:
            return name
    raise MeshProductError(f"Unrecognised cold-plate identifier in hole ledger: {value!r}")


def _coordinate_cm(row: dict[str, str], column: str) -> float:
    value = float(row[column])
    lower = column.lower()
    if lower.endswith("_mm") or "_mm_" in lower:
        value /= 10.0
    elif not (lower.endswith("_cm") or "_cm_" in lower):
        raise MeshProductError(f"Coordinate column must declare cm or mm: {column}")
    if not math.isfinite(value):
        raise MeshProductError(f"Non-finite coordinate in {column}: {row[column]!r}")
    return value


def read_hole_ledger(path: Path) -> tuple[list[HoleRecord], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows:
        raise MeshProductError(f"Hole ledger is empty: {path}")
    plate_col = _column(
        fieldnames, ("plate_volume", "plate_name", "parent_volume", "mother", "plate"), "plate column"
    )
    accepted_col = _column(
        fieldnames, ("accepted", "is_accepted", "decision", "status", "hole_status"),
        "accepted/status column",
    )
    name_col = _column(
        fieldnames,
        (
            "hole_volume_name", "hole_copy_name", "copy_volume", "placement_name",
            "geometry_name", "wrl_name", "hole_name", "copy_name",
        ),
        "accepted-hole geometry placement name",
    )
    x_col = _column(
        fieldnames,
        ("x_prime_cm", "x_instrument_cm", "x_local_cm", "local_x_cm", "hole_x_cm", "center_x_cm", "x_cm",
         "x_prime_mm", "x_local_mm", "local_x_mm", "hole_x_mm", "center_x_mm", "x_mm"),
        "local x coordinate with units",
    )
    y_col = _column(
        fieldnames,
        ("y_prime_cm", "y_instrument_cm", "y_local_cm", "local_y_cm", "hole_y_cm", "center_y_cm", "y_cm",
         "y_prime_mm", "y_local_mm", "local_y_mm", "hole_y_mm", "center_y_mm", "y_mm"),
        "local y coordinate with units",
    )
    radius_col = _column(
        fieldnames,
        ("hole_radius_cm", "radius_cm", "equivalent_radius_cm", "hole_radius_mm", "radius_mm"),
        "hole radius with units",
    )
    reason_cols = [
        name for name in fieldnames
        if name.lower() in {
            "keepout_reason", "skip_reason", "reason", "keepout_categories",
            "keepout_features", "keepout_kinds",
        }
    ]
    records: list[HoleRecord] = []
    for row_number, row in enumerate(rows, 2):
        accepted = _accepted(row[accepted_col])
        geometry_name = row[name_col].strip()
        if geometry_name.endswith(".0"):
            geometry_name = geometry_name[:-2]
        if accepted and not geometry_name:
            raise MeshProductError(f"Accepted hole row {row_number} has no geometry placement name")
        radius_cm = _coordinate_cm(row, radius_col)
        if radius_cm <= 0.0:
            raise MeshProductError(
                f"Hole ledger row {row_number} has non-positive radius: {radius_cm} cm"
            )
        records.append(
            HoleRecord(
                row_number=row_number,
                plate=_plate_name(row[plate_col]),
                accepted=accepted,
                decision=row[accepted_col].strip(),
                geometry_name=geometry_name,
                x_cm=_coordinate_cm(row, x_col),
                y_cm=_coordinate_cm(row, y_col),
                radius_cm=radius_cm,
                keepout_reason="; ".join(
                    value for value in (row.get(column, "").strip() for column in reason_cols) if value
                ),
            )
        )
    accepted_names = [record.geometry_name for record in records if record.accepted]
    if len(accepted_names) != len(set(accepted_names)):
        duplicates = sorted(name for name, count in Counter(accepted_names).items() if count > 1)
        raise MeshProductError(f"Duplicate accepted-hole geometry names: {duplicates[:20]}")
    columns = {
        "plate": plate_col,
        "accepted": accepted_col,
        "geometry_name": name_col,
        "x": x_col,
        "y": y_col,
        "radius": radius_col,
        "keepout_reason": ",".join(reason_cols),
    }
    return records, columns


def _finalize_raw(solid: RawSolid) -> RawSolid:
    if solid.description and solid.description != solid.tag:
        raise MeshProductError(
            f"WRL Anchor description differs from SOLID tag: {solid.tag!r} vs {solid.description!r}"
        )
    if not solid.vertices_mm or not solid.faces:
        raise MeshProductError(f"WRL solid has empty mesh: {solid.tag}")
    count = len(solid.vertices_mm)
    for face in solid.faces:
        if len(face) < 3 or min(face) < 0 or max(face) >= count:
            raise MeshProductError(f"Invalid face indices in WRL solid {solid.tag}")
    return solid


def iter_wrl_solids(path: Path) -> Iterator[RawSolid]:
    solid_re = re.compile(r"^#---------- SOLID:\s+(.+?)\s*$")
    description_re = re.compile(r'^description\s+"(.*)"$')
    current: RawSolid | None = None
    mode = ""
    polygon: list[int] = []
    saw_header = False
    last_line = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            last_line = line_number
            line = raw.strip()
            if line_number == 1:
                saw_header = line == "#VRML V2.0 utf8"
            match = solid_re.match(line)
            if match:
                if current is not None:
                    if mode or polygon:
                        raise MeshProductError(f"Unterminated WRL array before line {line_number}")
                    current.line_end = line_number - 1
                    yield _finalize_raw(current)
                current = RawSolid(match.group(1), "", [], [], line_number, 0)
                continue
            if current is None:
                continue
            match = description_re.match(line)
            if match:
                current.description = match.group(1)
                continue
            if line == "point [":
                if mode:
                    raise MeshProductError(f"Nested WRL point block at {path}:{line_number}")
                mode = "points"
                continue
            if line == "coordIndex [":
                if mode:
                    raise MeshProductError(f"Nested WRL index block at {path}:{line_number}")
                mode = "indices"
                continue
            if mode == "points":
                if line == "]":
                    mode = ""
                    continue
                tokens = line.rstrip(",").split()
                if len(tokens) != 3:
                    raise MeshProductError(f"Malformed WRL point at {path}:{line_number}: {line}")
                point = tuple(float(token) for token in tokens)
                if not all(math.isfinite(value) for value in point):
                    raise MeshProductError(f"Non-finite WRL point at {path}:{line_number}")
                current.vertices_mm.append(point)
                continue
            if mode == "indices":
                if line == "]":
                    if polygon:
                        raise MeshProductError(f"WRL polygon lacks -1 at {path}:{line_number}")
                    mode = ""
                    continue
                for token in re.findall(r"-?\d+", line):
                    value = int(token)
                    if value == -1:
                        if not polygon:
                            raise MeshProductError(f"Empty WRL polygon at {path}:{line_number}")
                        current.faces.append(polygon)
                        polygon = []
                    else:
                        polygon.append(value)
    if not saw_header:
        raise MeshProductError(f"Not a VRML 2.0 UTF-8 file: {path}")
    if mode or polygon:
        raise MeshProductError(f"Unterminated WRL array at end of {path}")
    if current is not None:
        current.line_end = last_line
        yield _finalize_raw(current)


def normalize_tag(tag: str, geometry: dict[str, ResolvedGeo]) -> tuple[str, int]:
    if tag in geometry:
        return tag, -1
    match = re.fullmatch(r"(.+)\.(\d+)", tag)
    if match and match.group(1) in geometry:
        return match.group(1), int(match.group(2))
    raise MeshProductError(f"WRL SOLID tag does not map to SE3 geometry: {tag}")


def _close(actual: float, expected: float, tolerance: float = 2.0e-3) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)


def build_products(args: argparse.Namespace) -> dict[str, Any]:
    source = resolve_path(args.source)
    setup = resolve_path(args.setup)
    main_geo = resolve_path(args.main_geo)
    intro_geo = resolve_path(args.intro_geo) if args.intro_geo else find_intro(main_geo)
    wrl = resolve_path(args.wrl)
    holes_path = resolve_path(args.holes)
    manifest_path = resolve_path(args.manifest)
    mesh_path = resolve_path(args.mesh)
    audit_path = resolve_path(args.audit)
    for path in (source, setup, main_geo, intro_geo, wrl, holes_path):
        if not path.is_file():
            raise MeshProductError(f"Required input is missing: {path}")

    hole_records, hole_columns = read_hole_ledger(holes_path)
    accepted_holes = [record for record in hole_records if record.accepted]
    accepted_by_name = {record.geometry_name: record for record in accepted_holes}
    expected_hole_names = set(accepted_by_name)

    geo_objects, shape_kinds = parse_geomega(intro_geo, main_geo)
    geometry = resolve_geomega(geo_objects, shape_kinds)
    instrument = geo_objects.get("InstrumentFrame")
    if instrument is None:
        raise MeshProductError("InstrumentFrame is absent from Intro geometry")
    position_cm = parse_triplet(instrument.properties.get("Position", ""), "InstrumentFrame.Position")
    rotation_deg = parse_triplet(instrument.properties.get("Rotation", ""), "InstrumentFrame.Rotation")
    world_from_if = rotation_xyz_matrix(rotation_deg)
    if_from_world = world_from_if.T

    vertices_world_chunks: list[np.ndarray] = []
    vertices_if_chunks: list[np.ndarray] = []
    triangle_chunks: list[np.ndarray] = []
    triangle_solid_chunks: list[np.ndarray] = []
    solid_vertex_offsets = [0]
    solid_triangle_offsets = [0]
    solid_names: list[str] = []
    wrl_tags: list[str] = []
    materials: list[str] = []
    mothers: list[str] = []
    hole_flags: list[bool] = []
    world_bounds: list[np.ndarray] = []
    if_bounds: list[np.ndarray] = []
    manifest: list[dict[str, Any]] = []

    for solid_index, solid in enumerate(iter_wrl_solids(wrl)):
        name, copy_number = normalize_tag(solid.tag, geometry)
        geo = geometry[name]
        vertices_world = np.asarray(solid.vertices_mm, dtype=np.float64)
        vertices_if = (vertices_world / 10.0 - position_cm) @ world_from_if
        vertex_start = solid_vertex_offsets[-1]
        local_triangles: list[tuple[int, int, int]] = []
        for face in solid.faces:
            for index in range(1, len(face) - 1):
                local_triangles.append((face[0], face[index], face[index + 1]))
        triangles = np.asarray(local_triangles, dtype=np.int32).reshape((-1, 3)) + vertex_start
        bounds_world = np.vstack((vertices_world.min(axis=0), vertices_world.max(axis=0)))
        bounds_if = np.vstack((vertices_if.min(axis=0), vertices_if.max(axis=0)))
        is_hole = name in expected_hole_names

        vertices_world_chunks.append(vertices_world)
        vertices_if_chunks.append(vertices_if)
        triangle_chunks.append(triangles)
        triangle_solid_chunks.append(np.full(len(triangles), solid_index, dtype=np.int32))
        solid_vertex_offsets.append(vertex_start + len(vertices_world))
        solid_triangle_offsets.append(solid_triangle_offsets[-1] + len(triangles))
        solid_names.append(name)
        wrl_tags.append(solid.tag)
        materials.append(geo.material)
        mothers.append(geo.mother)
        hole_flags.append(is_hole)
        world_bounds.append(bounds_world)
        if_bounds.append(bounds_if)
        manifest.append(
            {
                "solid_index": solid_index,
                "wrl_solid_tag": solid.tag,
                "wrl_copy_number": copy_number,
                "geometry_name": name,
                "geo_record_kind": geo.kind,
                "copy_source": geo.source,
                "material": geo.material,
                "mother": geo.mother,
                "shape_token": geo.shape_token,
                "shape_kind": geo.shape_kind,
                "is_nonvacuum": str(geo.material != "Vacuum").lower(),
                "is_plate_hole": str(is_hole).lower(),
                "vertex_count": len(vertices_world),
                "polygon_count": len(solid.faces),
                "triangle_count": len(triangles),
                "wrl_line_start": solid.line_start,
                "wrl_line_end": solid.line_end,
                "world_length_unit": "mm",
                "world_x_min_mm": bounds_world[0, 0],
                "world_y_min_mm": bounds_world[0, 1],
                "world_z_min_mm": bounds_world[0, 2],
                "world_x_max_mm": bounds_world[1, 0],
                "world_y_max_mm": bounds_world[1, 1],
                "world_z_max_mm": bounds_world[1, 2],
                "instrument_length_unit": "cm",
                "instrument_x_min_cm": bounds_if[0, 0],
                "instrument_y_min_cm": bounds_if[0, 1],
                "instrument_z_min_cm": bounds_if[0, 2],
                "instrument_x_max_cm": bounds_if[1, 0],
                "instrument_y_max_cm": bounds_if[1, 1],
                "instrument_z_max_cm": bounds_if[1, 2],
            }
        )

    if not manifest:
        raise MeshProductError(f"No SOLID blocks found in {wrl}")
    vertices_world = np.concatenate(vertices_world_chunks)
    vertices_if = np.concatenate(vertices_if_chunks)
    triangles = np.concatenate(triangle_chunks)
    triangle_solid_ids = np.concatenate(triangle_solid_chunks)
    world_bounds_array = np.asarray(world_bounds)
    if_bounds_array = np.asarray(if_bounds)
    hole_flags_array = np.asarray(hole_flags, dtype=np.bool_)
    nonvac_flags = np.asarray([material != "Vacuum" for material in materials], dtype=np.bool_)

    arrays = {
        "schema_version": np.asarray(SCHEMA_VERSION),
        "world_length_unit": np.asarray("mm"),
        "instrument_length_unit": np.asarray("cm"),
        "vertices_world_mm": vertices_world,
        "vertices_instrument_cm": vertices_if,
        "triangles": triangles,
        "triangle_solid_ids": triangle_solid_ids,
        "solid_vertex_offsets": np.asarray(solid_vertex_offsets, dtype=np.int64),
        "solid_triangle_offsets": np.asarray(solid_triangle_offsets, dtype=np.int64),
        "solid_names": np.asarray(solid_names),
        "wrl_solid_tags": np.asarray(wrl_tags),
        "materials": np.asarray(materials),
        "mothers": np.asarray(mothers),
        "is_nonvacuum": nonvac_flags,
        "is_plate_hole": hole_flags_array,
        "world_bounds_per_solid_mm": world_bounds_array,
        "instrument_bounds_per_solid_cm": if_bounds_array,
        "instrument_position_world_cm": position_cm,
        "instrument_rotation_xyz_deg": rotation_deg,
        "world_from_instrument_rotation": world_from_if,
        "instrument_from_world_rotation": if_from_world,
    }

    checks: list[dict[str, Any]] = []

    def check(identifier: str, passed: bool, expected: Any, actual: Any, details: Any = None) -> None:
        record: dict[str, Any] = {
            "id": identifier,
            "status": "PASS" if passed else "FAIL",
            "expected": expected,
            "actual": actual,
        }
        if details is not None:
            record["details"] = details
        checks.append(record)

    actual_names = set(solid_names)
    actual_nonvac_names = {name for name, material in zip(solid_names, materials) if material != "Vacuum"}
    actual_hole_names = {name for name, flag in zip(solid_names, hole_flags) if flag}
    unexpected_vacuum = {
        name for name, material, flag in zip(solid_names, materials, hole_flags)
        if material == "Vacuum" and not flag
    }
    expected_nonvac_names = {
        name for name, geo in geometry.items()
        if geo.placed and geo.material != "Vacuum" and bool(geo.shape_token)
    }
    nonvac_material_counts = Counter(
        material for material, nonvacuum in zip(materials, nonvac_flags) if nonvacuum
    )
    volume_count = sum(obj.kind == "volume" for obj in geo_objects.values())
    copy_count = sum(obj.kind == "copy" for obj in geo_objects.values())
    placed_csg = {name for name, geo in geometry.items() if geo.placed and geo.csg}

    check("unique_wrl_tags", len(wrl_tags) == len(set(wrl_tags)), len(wrl_tags), len(set(wrl_tags)))
    check("unique_geometry_names", len(solid_names) == len(actual_names), len(solid_names), len(actual_names))
    check("nonvacuum_solid_count", int(nonvac_flags.sum()) == EXPECTED_NONVACUUM_SOLIDS,
          EXPECTED_NONVACUUM_SOLIDS, int(nonvac_flags.sum()))
    check("nonvacuum_exact_set", actual_nonvac_names == expected_nonvac_names,
          len(expected_nonvac_names), len(actual_nonvac_names), {
              "missing": sorted(expected_nonvac_names - actual_nonvac_names),
              "unexpected": sorted(actual_nonvac_names - expected_nonvac_names),
          })
    check("hole_wrl_exact_set", actual_hole_names == expected_hole_names,
          len(expected_hole_names), len(actual_hole_names), {
              "missing": sorted(expected_hole_names - actual_hole_names)[:100],
              "unexpected": sorted(actual_hole_names - expected_hole_names)[:100],
          })
    check("no_unexpected_visible_vacuum", not unexpected_vacuum, [], sorted(unexpected_vacuum)[:100])
    check("total_solid_count", len(solid_names) == EXPECTED_NONVACUUM_SOLIDS + len(expected_hole_names),
          EXPECTED_NONVACUUM_SOLIDS + len(expected_hole_names), len(solid_names))
    accepted_by_plate = Counter(record.plate for record in accepted_holes)
    check("equivalent_hole_total", len(expected_hole_names) == EXPECTED_EQUIVALENT_HOLES,
          EXPECTED_EQUIVALENT_HOLES, len(expected_hole_names))
    check(
        "equivalent_holes_48_per_plate",
        accepted_by_plate == Counter({plate.name: EXPECTED_HOLES_PER_PLATE for plate in PLATES}),
        {plate.name: EXPECTED_HOLES_PER_PLATE for plate in PLATES},
        dict(accepted_by_plate),
    )
    equivalent_area_measurements: dict[str, Any] = {}
    equivalent_area_ok = True
    for plate in PLATES:
        plate_records = [record for record in accepted_holes if record.plate == plate.name]
        radii = np.asarray([record.radius_cm for record in plate_records], dtype=float)
        uniform = bool(
            len(radii) == EXPECTED_HOLES_PER_PLATE
            and np.allclose(radii, radii[0], rtol=0.0, atol=1.0e-10)
        )
        actual_area = float(np.pi * np.square(radii).sum())
        expected_area = (
            SOURCE_ACCEPTED_HOLE_COUNTS[plate.name] * math.pi * SOURCE_HOLE_RADIUS_CM**2
        )
        area_closes = math.isclose(actual_area, expected_area, rel_tol=2.0e-10, abs_tol=2.0e-10)
        equivalent_area_ok &= uniform and area_closes
        equivalent_area_measurements[plate.name] = {
            "hole_count": len(radii),
            "diameter_mm": float(20.0 * radii[0]) if uniform else None,
            "actual_removed_area_cm2": actual_area,
            "source_removed_area_cm2": expected_area,
            "area_residual_cm2": actual_area - expected_area,
            "uniform_radius_within_plate": uniform,
        }
    check(
        "equivalent_hole_area_preserved_per_plate",
        equivalent_area_ok,
        "48 equal-radius holes per plate with the source 4 mm-hole total area",
        equivalent_area_measurements,
    )
    check("se3_total_solid_count_3334", len(solid_names) == 3334, 3334, len(solid_names))
    check("all_wrl_names_expected", actual_names == expected_nonvac_names | expected_hole_names,
          len(expected_nonvac_names | expected_hole_names), len(actual_names))
    check("nonvacuum_material_counts", dict(nonvac_material_counts) == EXPECTED_NONVACUUM_MATERIAL_COUNTS,
          EXPECTED_NONVACUUM_MATERIAL_COUNTS, dict(nonvac_material_counts))
    check("old_nb_mumetal_absent", not (actual_names & FORBIDDEN_OLD_SHIELDS), [],
          sorted(actual_names & FORBIDDEN_OLD_SHIELDS))
    check("se3_al_shields_present", NEW_AL_SHIELDS <= actual_names, sorted(NEW_AL_SHIELDS),
          sorted(NEW_AL_SHIELDS & actual_names))
    check("se3_al_shields_material", all(geometry[name].material == "Aluminium" for name in NEW_AL_SHIELDS),
          "Aluminium", {name: geometry.get(name).material if name in geometry else None for name in NEW_AL_SHIELDS})
    check("required_outer_groups_present",
          set(BPE_NAMES + PLASTIC_NAMES + BGO_NAMES + KAPTON_NAMES + OUTER_AL_NAMES + WINDOW_FOILS) <= actual_names,
          "all required BPE/plastic/BGO/Kapton/outer-Al/window volumes",
          sorted(set(BPE_NAMES + PLASTIC_NAMES + BGO_NAMES + KAPTON_NAMES + OUTER_AL_NAMES + WINDOW_FOILS) - actual_names))
    check("placed_csg_exact_set", placed_csg == EXPECTED_PLACED_CSG,
          sorted(EXPECTED_PLACED_CSG), sorted(placed_csg), {
              "missing": sorted(EXPECTED_PLACED_CSG - placed_csg),
              "unexpected": sorted(placed_csg - EXPECTED_PLACED_CSG),
          })
    check("geometry_volume_count", volume_count == EXPECTED_VOLUME_DEFINITIONS,
          EXPECTED_VOLUME_DEFINITIONS, volume_count)
    check("geometry_copy_count", copy_count == EXPECTED_BASE_COPIES + len(expected_hole_names),
          EXPECTED_BASE_COPIES + len(expected_hole_names), copy_count)
    check("geometry_object_count", len(geo_objects) == EXPECTED_VOLUME_DEFINITIONS + EXPECTED_BASE_COPIES + len(expected_hole_names),
          EXPECTED_VOLUME_DEFINITIONS + EXPECTED_BASE_COPIES + len(expected_hole_names), len(geo_objects))

    check("instrument_position", bool(np.allclose(position_cm, (0, 0, 0), atol=1e-12)),
          [0, 0, 0], position_cm.tolist())
    check("instrument_rotation", bool(np.allclose(rotation_deg, (0, 45, 0), atol=1e-12)),
          [0, 45, 0], rotation_deg.tolist())
    check("rotation_right_handed", _close(float(np.linalg.det(world_from_if)), 1.0, 1e-12),
          1.0, float(np.linalg.det(world_from_if)))
    outward = world_from_if @ np.asarray((-1.0, 0.0, 0.0))
    incoming = world_from_if @ np.asarray((1.0, 0.0, 0.0))
    expected_outward = np.asarray((-1 / math.sqrt(2), 0, 1 / math.sqrt(2)))
    expected_incoming = -expected_outward
    check("sky_facing_minus_x_prime", bool(np.allclose(outward, expected_outward, atol=1e-12)),
          expected_outward.tolist(), outward.tolist())
    check("incoming_plus_x_prime", bool(np.allclose(incoming, expected_incoming, atol=1e-12)),
          expected_incoming.tolist(), incoming.tolist())
    reconstructed = vertices_if @ world_from_if.T + position_cm
    roundtrip_error = float(np.max(np.abs(reconstructed - vertices_world / 10.0)))
    check("coordinate_roundtrip", roundtrip_error <= 1e-10, "<=1e-10 cm", roundtrip_error)
    world_max_abs = float(np.max(np.abs(vertices_world)))
    check("native_world_mm_envelope", 500.0 <= world_max_abs <= 700.0,
          "500..700 mm", world_max_abs)
    with wrl.open(encoding="utf-8") as camera_handle:
        camera_text_head = camera_handle.read(3000)
    check(
        "native_geant4_camera_unmodified",
        "#---------- CAMERA" in camera_text_head
        and "#---------- CAMERA / SE3 FLIGHT ORIENTATION" not in camera_text_head
        and bool(re.search(r"position\s+0\s+0\s+[0-9.eE+-]+", camera_text_head)),
        "unaltered Geant4 10.02 VRML2FILE +Z camera metadata",
        "the audited figures independently project world -Y with world +Z screen-up",
    )

    manifest_by_name = {row["geometry_name"]: row for row in manifest}
    plate_measurements: dict[str, Any] = {}
    plate_ok = True
    for plate in PLATES:
        row = manifest_by_name.get(plate.name)
        if row is None:
            plate_ok = False
            plate_measurements[plate.name] = {"missing": True}
            continue
        spans = np.asarray((
            float(row["instrument_x_max_cm"]) - float(row["instrument_x_min_cm"]),
            float(row["instrument_y_max_cm"]) - float(row["instrument_y_min_cm"]),
            float(row["instrument_z_max_cm"]) - float(row["instrument_z_min_cm"]),
        ))
        centre_z = 0.5 * (float(row["instrument_z_min_cm"]) + float(row["instrument_z_max_cm"]))
        okay = (
            _close(spans[0], 2 * plate.radius_cm)
            and _close(spans[1], 2 * plate.radius_cm)
            and _close(spans[2], 0.4)
            and _close(centre_z, plate.center_z_cm)
            and row["material"] == plate.material
            and int(row["vertex_count"]) == 202
        )
        plate_ok &= okay
        plate_measurements[plate.name] = {
            "span_cm": spans.tolist(), "center_z_cm": centre_z,
            "material": row["material"], "vertex_count": int(row["vertex_count"]),
            "status": "PASS" if okay else "FAIL",
        }
    check("cold_plate_native_dimensions", plate_ok,
          "R=15/17.5 cm, thickness=0.4 cm, locked z centres, parent mesh 100 segments",
          plate_measurements)

    hole_measurements: dict[str, Any] = {}
    hole_geometry_ok = True
    hole_facet_ok = True
    for name, record in accepted_by_name.items():
        row = manifest_by_name.get(name)
        geo = geometry.get(name)
        if row is None or geo is None:
            hole_geometry_ok = False
            hole_measurements[name] = {"missing": True}
            continue
        centre = np.asarray((
            0.5 * (float(row["instrument_x_min_cm"]) + float(row["instrument_x_max_cm"])),
            0.5 * (float(row["instrument_y_min_cm"]) + float(row["instrument_y_max_cm"])),
            0.5 * (float(row["instrument_z_min_cm"]) + float(row["instrument_z_max_cm"])),
        ))
        span = np.asarray((
            float(row["instrument_x_max_cm"]) - float(row["instrument_x_min_cm"]),
            float(row["instrument_y_max_cm"]) - float(row["instrument_y_min_cm"]),
            float(row["instrument_z_max_cm"]) - float(row["instrument_z_min_cm"]),
        ))
        expected_centre = np.asarray((record.x_cm, record.y_cm, PLATE_BY_NAME[record.plate].center_z_cm))
        okay = (
            geo.material == "Vacuum"
            and geo.mother == record.plate
            and bool(np.allclose(centre, expected_centre, atol=2e-3, rtol=0))
            and _close(span[0], 2.0 * record.radius_cm)
            and _close(span[1], 2.0 * record.radius_cm)
            and 0.399 <= span[2] <= 0.405
        )
        facets_ok = int(row["vertex_count"]) == 50
        hole_geometry_ok &= okay
        hole_facet_ok &= facets_ok
        if not okay or not facets_ok:
            hole_measurements[name] = {
                "ledger_row": record.row_number,
                "plate": record.plate,
                "centre_cm": centre.tolist(),
                "expected_centre_cm": expected_centre.tolist(),
                "span_cm": span.tolist(),
                "expected_radius_cm": record.radius_cm,
                "material": geo.material,
                "mother": geo.mother,
                "vertex_count": int(row["vertex_count"]),
            }
    check("hole_bbox_ledger_closure", hole_geometry_ok,
          f"{len(expected_hole_names)} exact Vacuum hole centres, ledger radii, through span",
          {"failed_examples": dict(list(hole_measurements.items())[:50]), "checked": len(expected_hole_names)})
    check("hole_mesh_24_segments", hole_facet_ok, "50 vertices per two-plane PCON (24 segments)",
          {"failed_examples": dict(list(hole_measurements.items())[:50])})

    window = manifest_by_name.get("Win_MagShield_Al_foil_side")
    if window:
        window_center_y = 0.5 * (float(window["instrument_y_min_cm"]) + float(window["instrument_y_max_cm"]))
        window_center_z = 0.5 * (float(window["instrument_z_min_cm"]) + float(window["instrument_z_max_cm"]))
        window_y_span = float(window["instrument_y_max_cm"]) - float(window["instrument_y_min_cm"])
        window_z_span = float(window["instrument_z_max_cm"]) - float(window["instrument_z_min_cm"])
        window_actual = {
            "center_y_cm": window_center_y, "center_z_cm": window_center_z,
            "span_y_cm": window_y_span, "span_z_cm": window_z_span,
        }
        window_ok = all((
            _close(window_center_y, 0.0), _close(window_center_z, -5.2),
            _close(window_y_span, 3.796), _close(window_z_span, 3.796),
        ))
    else:
        window_actual = {"missing": True}
        window_ok = False
    check("focused_window_known_dimension_mm_scale", window_ok,
          {"center_yz_cm": [0, -5.2], "span_yz_cm": [3.796, 3.796]}, window_actual)

    atomic_csv(manifest_path, manifest)
    atomic_npz(mesh_path, arrays)
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    audit = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_identity": "SE3",
        "physics_status": "GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN",
        "inputs": {
            "source_card": file_record(source), "geometry_setup": file_record(setup),
            "intro_geo": file_record(intro_geo), "main_geo": file_record(main_geo),
            "native_wrl": file_record(wrl), "hole_pattern": file_record(holes_path),
            "builder": file_record(Path(__file__).resolve()),
        },
        "outputs": {"manifest": file_record(manifest_path), "mesh_npz": file_record(mesh_path)},
        "hole_ledger_columns": hole_columns,
        "counts": {
            "wrl_solids": len(solid_names), "nonvacuum_solids": int(nonvac_flags.sum()),
            "visible_vacuum_holes": int(hole_flags_array.sum()),
            "accepted_hole_ledger_rows": len(accepted_holes),
            "skipped_hole_ledger_rows": len(hole_records) - len(accepted_holes),
            "vertices": int(len(vertices_world)), "triangles": int(len(triangles)),
            "geometry_volume_definitions": volume_count, "geometry_copy_declarations": copy_count,
            "materials_nonvacuum": dict(nonvac_material_counts),
        },
        "coordinate_systems": {
            "native_wrl": {"frame": "world", "length_unit": "mm"},
            "instrument": {
                "length_unit": "cm", "position_world_cm": position_cm.tolist(),
                "rotation_xyz_deg": rotation_deg.tolist(),
                "world_from_instrument_rotation": world_from_if.tolist(),
                "closed_form_world_to_instrument": {
                    "x_prime_cm": "(X_world_mm-Z_world_mm)/(10*sqrt(2))",
                    "y_prime_cm": "Y_world_mm/10",
                    "z_prime_cm": "(X_world_mm+Z_world_mm)/(10*sqrt(2))",
                },
                "sky_facing_minus_x_prime_world": outward.tolist(),
                "incoming_plus_x_prime_world": incoming.tolist(),
                "world_plus_z_is_sky_up": True,
            },
        },
        "checks": checks,
        "limitations": [
            "The WRL is a Geant4 visualization tessellation, not analytic CAD.",
            "Non-hole curved solids use 100 segments per circle; visible hole daughters use 24.",
            "Vacuum daughter meshes expose navigator holes but do not Boolean-subtract the parent display surface.",
            "Geant4 10.02 VRML2FILE hard-codes its native camera on world +Z; the raw WRL is preserved, while figures explicitly project from world -Y with world +Z screen-up.",
        ],
    }
    atomic_json(audit_path, audit)
    if status != "PASS":
        failed = [item["id"] for item in checks if item["status"] == "FAIL"]
        raise MeshProductError(f"SE3 mesh validation failed: {failed}; see {audit_path}")
    return audit


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source", default=str(DEFAULT_SOURCE))
    result.add_argument("--setup", default=str(DEFAULT_SETUP))
    result.add_argument("--main-geo", default=str(DEFAULT_MAIN))
    result.add_argument("--intro-geo")
    result.add_argument("--wrl", default=str(DEFAULT_WRL))
    result.add_argument("--holes", default=str(DEFAULT_HOLES))
    result.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    result.add_argument("--mesh", default=str(DEFAULT_MESH))
    result.add_argument("--audit", default=str(DEFAULT_AUDIT))
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        audit = build_products(args)
    except (MeshProductError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    counts = audit["counts"]
    print(
        f"PASS: {counts['nonvacuum_solids']} non-vacuum solids + "
        f"{counts['visible_vacuum_holes']} visible Vacuum holes; native WRL units=mm"
    )
    print(f"manifest: {resolve_path(args.manifest)}")
    print(f"mesh: {resolve_path(args.mesh)}")
    print(f"audit: {resolve_path(args.audit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
