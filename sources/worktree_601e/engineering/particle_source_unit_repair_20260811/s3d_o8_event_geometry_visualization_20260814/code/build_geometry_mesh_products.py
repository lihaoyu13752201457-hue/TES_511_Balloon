#!/usr/bin/env python3
"""Build auditable, plot-ready mesh products from the native S3d-O8 WRL.

The input WRL is produced by Geant4's VRML2FILE driver after Geomega has
resolved the complete volume hierarchy and Boolean CSG.  This script does not
reconstruct geometry from textual primitives.  It joins each WRL physical
solid to the exact Volume/Copy declaration in the S3d-O8 Geomega authority,
preserves the original polygon topology, provides triangulated faces for
plotting, and enforces the geometry-presence gates used by the engineering
review.

Coordinate conventions
----------------------
* ``vertices_world_mm``: native Geant4/WRL world coordinates, millimetres.
* ``vertices_instrument_cm``: InstrumentFrame-local coordinates, centimetres.
  The current authority places InstrumentFrame at world (0, 0, 0) cm with a
  +45 degree rotation about world Y.  The transform is read from Intro rather
  than silently hard-coded.

No event or transport data are read or produced.
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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SCHEMA_VERSION = "s3d_o8_geometry_mesh_products_v1"
EXPECTED_SOLID_COUNT = 3096
EXPECTED_GEOMETRY_VOLUME_COUNT = 234
EXPECTED_GEOMETRY_COPY_COUNT = 2880
EXPECTED_GEOMETRY_OBJECT_COUNT = 3114

SCRIPT_DIR = Path(__file__).resolve().parent
PRODUCT_DIR = SCRIPT_DIR.parent
DEFAULT_SOURCE_CARD = SCRIPT_DIR / "s3d_o8_geometry_only.source"
DEFAULT_WRL = PRODUCT_DIR / "geometry" / "s3d_o8_native_geant4_full.wrl"
DEFAULT_MANIFEST = PRODUCT_DIR / "data" / "geometry_volume_manifest.csv"
DEFAULT_MESH_NPZ = PRODUCT_DIR / "data" / "geometry_mesh_products.npz"
DEFAULT_AUDIT = PRODUCT_DIR / "audit" / "geometry_validation.json"


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

WINDOW_CSG_BAND_NAMES = (
    "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
    "Still_Shield_Al_side_window_side_wall_rectcut_window_band",
    "Shield_4K_Al_side_window_side_wall_rectcut_window_band",
    "Shield_60K_Al_side_window_side_wall_rectcut_window_band",
    "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_rectcut_window_band",
)

WINDOW_FOIL_NAMES = (
    "Win_50mK_Al_foil_side",
    "Win_Still_Al_foil_side",
    "Win_4K_Al_foil_side",
    "Win_60K_Al_foil_side",
    "Win_Be_Vacuum_150um_side",
    "Win_Outer_Al_Filter_side",
    "Win_MagShield_Al_foil_side",
)

ACTIVE_VETO_NAMES = BGO_NAMES + PLASTIC_NAMES

EXPECTED_PLACED_CSG_NAMES = (
    WINDOW_CSG_BAND_NAMES
    + BPE_NAMES
    + PLASTIC_NAMES
    + (BGO_NAMES[0],)
    + KAPTON_NAMES
    + OUTER_AL_NAMES
    + BGO_NAMES[1:]
)

REQUIRED_GROUPS: dict[str, tuple[str, ...]] = {
    "active_veto": ACTIVE_VETO_NAMES,
    "bpe": BPE_NAMES,
    "plastic": PLASTIC_NAMES,
    "bgo": BGO_NAMES,
    "kapton": KAPTON_NAMES,
    "outer_al": OUTER_AL_NAMES,
    "window_csg_bands": WINDOW_CSG_BAND_NAMES,
    "window_foils": WINDOW_FOIL_NAMES,
}

EXPECTED_GROUP_MATERIALS = {
    "bpe": "BoratedPolyethylene5wtB",
    "plastic": "PlasticScintillator",
    "bgo": "BGO",
    "kapton": "Kapton",
    "outer_al": "Aluminium",
}


class GeometryProductError(RuntimeError):
    """Raised when an input cannot be parsed without ambiguity."""


@dataclass
class GeoObject:
    name: str
    record_kind: str
    source: str = ""
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedGeoObject:
    name: str
    record_kind: str
    source: str
    material: str
    mother: str
    shape_token: str
    shape_kind: str
    is_placed: bool
    is_csg: bool


@dataclass
class SolidMesh:
    tag: str
    line_start: int
    line_end: int = 0
    description: str = ""
    diffuse_rgb: tuple[float, float, float] | None = None
    transparency: float | None = None
    vertices_world_mm: list[tuple[float, float, float]] = field(default_factory=list)
    polygons: list[list[int]] = field(default_factory=list)
    point_block_count: int = 0
    index_block_count: int = 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def resolve_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base if base is not None else Path.cwd()) / path
    return path.resolve()


def find_geometry_setup(source_card: Path) -> Path:
    geometry_lines: list[str] = []
    for raw in source_card.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0] == "Geometry":
            geometry_lines.append(parts[1].strip())
    if len(geometry_lines) != 1:
        raise GeometryProductError(
            f"Expected exactly one Geometry line in {source_card}, found {len(geometry_lines)}"
        )
    return resolve_path(geometry_lines[0], source_card.parent)


def include_paths(path: Path) -> list[Path]:
    includes: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        match = re.fullmatch(r"Include\s+(\S+)", line)
        if match:
            includes.append(resolve_path(match.group(1), path.parent))
    return includes


def resolve_authority_paths(
    source_card: Path,
    setup_override: Path | None,
    main_override: Path | None,
    intro_override: Path | None,
) -> tuple[Path, Path, Path]:
    setup = setup_override if setup_override is not None else find_geometry_setup(source_card)
    setup = setup.resolve()
    setup_includes = include_paths(setup)

    if main_override is not None:
        main_geo = main_override.resolve()
    else:
        geo_candidates = [p for p in setup_includes if p.name.endswith(".geo")]
        if len(geo_candidates) != 1:
            raise GeometryProductError(
                f"Expected one main .geo Include in {setup}, found {geo_candidates}"
            )
        main_geo = geo_candidates[0]

    if intro_override is not None:
        intro_geo = intro_override.resolve()
    else:
        intro_candidates = [p for p in include_paths(main_geo) if p.name.startswith("Intro_")]
        if len(intro_candidates) != 1:
            raise GeometryProductError(
                f"Expected one Intro_ Include in {main_geo}, found {intro_candidates}"
            )
        intro_geo = intro_candidates[0]

    for path in (setup, main_geo, intro_geo):
        if not path.is_file():
            raise GeometryProductError(f"Required authority file is missing: {path}")
    return setup, main_geo, intro_geo


def parse_geomega(
    intro_geo: Path, main_geo: Path
) -> tuple[dict[str, GeoObject], dict[str, str]]:
    objects: dict[str, GeoObject] = {}
    shape_kinds: dict[str, str] = {}
    auxiliary_names: set[str] = set()

    for path in (intro_geo, main_geo):
        for line_number, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw.strip()
            if not line or line.startswith(("#", "//")):
                continue

            volume_match = re.fullmatch(r"Volume\s+(\S+)", line)
            if volume_match:
                name = volume_match.group(1)
                if name in objects:
                    raise GeometryProductError(
                        f"Duplicate geometry object {name} at {path}:{line_number}"
                    )
                objects[name] = GeoObject(name=name, record_kind="volume")
                continue

            copy_match = re.fullmatch(r"(\S+)\.Copy\s+(\S+)", line)
            if copy_match:
                source, name = copy_match.groups()
                if name in objects:
                    raise GeometryProductError(
                        f"Duplicate geometry object {name} at {path}:{line_number}"
                    )
                objects[name] = GeoObject(name=name, record_kind="copy", source=source)
                continue

            shape_match = re.fullmatch(r"Shape\s+(\S+)\s+(\S+)", line)
            if shape_match:
                kind, name = shape_match.groups()
                if name in shape_kinds and shape_kinds[name] != kind:
                    raise GeometryProductError(
                        f"Conflicting Shape definition for {name} at {path}:{line_number}"
                    )
                shape_kinds[name] = kind
                auxiliary_names.add(name)
                continue

            orientation_match = re.fullmatch(r"Orientation\s+(\S+)", line)
            if orientation_match:
                auxiliary_names.add(orientation_match.group(1))
                continue

            property_match = re.fullmatch(
                r"(\S+)\.(Material|Visibility|Shape|Position|Rotation|Mother)\s+(.+)",
                line,
            )
            if property_match:
                name, key, value = property_match.groups()
                if name not in objects:
                    if name in auxiliary_names:
                        continue
                    raise GeometryProductError(
                        f"Property precedes Volume/Copy declaration for {name} at "
                        f"{path}:{line_number}"
                    )
                objects[name].properties[key] = value.strip()

    for obj in objects.values():
        if obj.record_kind == "copy" and obj.source not in objects:
            raise GeometryProductError(
                f"Copy {obj.name} refers to missing source object {obj.source}"
            )
    return objects, shape_kinds


def resolve_geomega_objects(
    objects: dict[str, GeoObject], shape_kinds: dict[str, str]
) -> dict[str, ResolvedGeoObject]:
    @lru_cache(maxsize=None)
    def inherited_property(name: str, key: str, trail: tuple[str, ...] = ()) -> str:
        if name in trail:
            raise GeometryProductError(f"Copy inheritance cycle: {' -> '.join(trail + (name,))}")
        obj = objects[name]
        if key in obj.properties:
            return obj.properties[key]
        if obj.source:
            return inherited_property(obj.source, key, trail + (name,))
        return ""

    resolved: dict[str, ResolvedGeoObject] = {}
    for name, obj in objects.items():
        material = inherited_property(name, "Material").split(maxsplit=1)[0]
        shape_value = inherited_property(name, "Shape")
        shape_token = shape_value.split(maxsplit=1)[0] if shape_value else ""
        shape_kind = shape_kinds.get(shape_token, shape_token)
        mother_value = obj.properties.get("Mother", "")
        mother = mother_value.split(maxsplit=1)[0] if mother_value else ""
        is_placed = bool(mother and mother != "0")
        is_csg = shape_kind.lower() in {"subtraction", "union", "intersection"}
        resolved[name] = ResolvedGeoObject(
            name=name,
            record_kind=obj.record_kind,
            source=obj.source,
            material=material,
            mother=mother,
            shape_token=shape_token,
            shape_kind=shape_kind,
            is_placed=is_placed,
            is_csg=is_csg,
        )
    return resolved


def parse_float_triplet(value: str, label: str) -> np.ndarray:
    parts = value.split()
    if len(parts) < 3:
        raise GeometryProductError(f"Expected three values for {label}, got: {value}")
    try:
        result = np.asarray([float(parts[0]), float(parts[1]), float(parts[2])], dtype=np.float64)
    except ValueError as exc:
        raise GeometryProductError(f"Non-numeric values for {label}: {value}") from exc
    if not np.isfinite(result).all():
        raise GeometryProductError(f"Non-finite values for {label}: {value}")
    return result


def rotation_xyz_matrix(rotation_deg: np.ndarray) -> np.ndarray:
    rx, ry, rz = np.deg2rad(rotation_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = np.asarray(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=np.float64)
    rot_y = np.asarray(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=np.float64)
    rot_z = np.asarray(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=np.float64)
    return rot_z @ rot_y @ rot_x


def finalize_solid(solid: SolidMesh, line_end: int) -> SolidMesh:
    solid.line_end = line_end
    if solid.point_block_count != 1 or solid.index_block_count != 1:
        raise GeometryProductError(
            f"Solid {solid.tag} has {solid.point_block_count} point blocks and "
            f"{solid.index_block_count} coordIndex blocks"
        )
    if solid.description != solid.tag:
        raise GeometryProductError(
            f"Solid tag/Anchor description mismatch: {solid.tag!r} vs {solid.description!r}"
        )
    if solid.diffuse_rgb is None or solid.transparency is None:
        raise GeometryProductError(f"Solid {solid.tag} is missing material display attributes")
    if not solid.vertices_world_mm or not solid.polygons:
        raise GeometryProductError(f"Solid {solid.tag} has empty mesh data")
    vertex_count = len(solid.vertices_world_mm)
    for polygon_index, polygon in enumerate(solid.polygons):
        if len(polygon) < 3:
            raise GeometryProductError(
                f"Solid {solid.tag} polygon {polygon_index} has fewer than three vertices"
            )
        if min(polygon) < 0 or max(polygon) >= vertex_count:
            raise GeometryProductError(
                f"Solid {solid.tag} polygon {polygon_index} has out-of-range indices"
            )
    return solid


def parse_wrl(path: Path) -> list[SolidMesh]:
    solid_pattern = re.compile(r"^#---------- SOLID:\s+(.+?)\s*$")
    description_pattern = re.compile(r'^description\s+"(.*)"$')
    current: SolidMesh | None = None
    solids: list[SolidMesh] = []
    mode = ""
    current_polygon: list[int] = []
    saw_vrml_header = False
    last_line_number = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            last_line_number = line_number
            line = raw.strip()
            if line_number == 1:
                saw_vrml_header = line == "#VRML V2.0 utf8"

            solid_match = solid_pattern.match(line)
            if solid_match:
                if current is not None:
                    if current_polygon:
                        raise GeometryProductError(
                            f"Unterminated polygon before solid {solid_match.group(1)}"
                        )
                    solids.append(finalize_solid(current, line_number - 1))
                current = SolidMesh(tag=solid_match.group(1), line_start=line_number)
                mode = ""
                continue

            if current is None:
                continue

            description_match = description_pattern.match(line)
            if description_match:
                current.description = description_match.group(1)
                continue

            if line.startswith("diffuseColor "):
                values = line.split()[1:]
                if len(values) != 3:
                    raise GeometryProductError(f"Malformed diffuseColor at {path}:{line_number}")
                current.diffuse_rgb = tuple(float(value) for value in values)
                continue

            if line.startswith("transparency "):
                values = line.split()[1:]
                if len(values) != 1:
                    raise GeometryProductError(f"Malformed transparency at {path}:{line_number}")
                current.transparency = float(values[0])
                continue

            if line == "point [":
                if mode:
                    raise GeometryProductError(f"Nested WRL array at {path}:{line_number}")
                current.point_block_count += 1
                mode = "points"
                continue

            if line == "coordIndex [":
                if mode:
                    raise GeometryProductError(f"Nested WRL array at {path}:{line_number}")
                current.index_block_count += 1
                mode = "indices"
                continue

            if mode == "points":
                if line == "]":
                    mode = ""
                    continue
                tokens = line.rstrip(",").split()
                if len(tokens) != 3:
                    raise GeometryProductError(f"Malformed point at {path}:{line_number}: {line}")
                point = tuple(float(token) for token in tokens)
                if not all(math.isfinite(value) for value in point):
                    raise GeometryProductError(f"Non-finite point at {path}:{line_number}")
                current.vertices_world_mm.append(point)
                continue

            if mode == "indices":
                if line == "]":
                    if current_polygon:
                        raise GeometryProductError(
                            f"coordIndex block ends without -1 at {path}:{line_number}"
                        )
                    mode = ""
                    continue
                for value_text in re.findall(r"-?\d+", line):
                    value = int(value_text)
                    if value == -1:
                        if not current_polygon:
                            raise GeometryProductError(
                                f"Empty polygon at {path}:{line_number}"
                            )
                        current.polygons.append(current_polygon)
                        current_polygon = []
                    else:
                        current_polygon.append(value)

    if not saw_vrml_header:
        raise GeometryProductError(f"Not a VRML V2.0 file: {path}")
    if mode or current_polygon:
        raise GeometryProductError(f"Unterminated WRL block at end of {path}")
    if current is not None:
        solids.append(finalize_solid(current, last_line_number))
    if not solids:
        raise GeometryProductError(f"No top-level SOLID records found in {path}")
    return solids


def normalize_wrl_tag(tag: str, geometry_objects: dict[str, ResolvedGeoObject]) -> tuple[str, int]:
    if tag in geometry_objects:
        return tag, -1
    match = re.fullmatch(r"(.+)\.(\d+)", tag)
    if match and match.group(1) in geometry_objects:
        return match.group(1), int(match.group(2))
    raise GeometryProductError(f"WRL solid tag does not map to a Geomega Volume/Copy: {tag}")


def category_for(name: str) -> str:
    for category, names in REQUIRED_GROUPS.items():
        # Active-veto membership overlaps the concrete BGO/Plastic component
        # classes and is carried separately by ``is_active_veto``.
        if category == "active_veto":
            continue
        if name in names:
            return category
    return "other"


def bounds_dict(bounds: np.ndarray, unit: str) -> dict[str, Any]:
    return {
        "unit": unit,
        "min": [float(value) for value in bounds[0]],
        "max": [float(value) for value in bounds[1]],
        "span": [float(value) for value in bounds[1] - bounds[0]],
        "max_abs": float(np.max(np.abs(bounds))),
    }


def atomic_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
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
            mode="w+b",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            np.savez_compressed(handle, **arrays)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def build_products(args: argparse.Namespace) -> dict[str, Any]:
    source_card = resolve_path(args.source_card)
    wrl_path = resolve_path(args.wrl)
    manifest_path = resolve_path(args.manifest)
    mesh_path = resolve_path(args.mesh_npz)
    audit_path = resolve_path(args.audit)
    setup_override = resolve_path(args.setup) if args.setup else None
    main_override = resolve_path(args.main_geo) if args.main_geo else None
    intro_override = resolve_path(args.intro_geo) if args.intro_geo else None

    for path in (source_card, wrl_path):
        if not path.is_file():
            raise GeometryProductError(f"Required input is missing: {path}")

    setup_path, main_geo, intro_geo = resolve_authority_paths(
        source_card, setup_override, main_override, intro_override
    )
    geo_objects, shape_kinds = parse_geomega(intro_geo, main_geo)
    resolved_geo = resolve_geomega_objects(geo_objects, shape_kinds)
    solids = parse_wrl(wrl_path)

    instrument = geo_objects.get("InstrumentFrame")
    if instrument is None:
        raise GeometryProductError("InstrumentFrame is absent from Intro geometry")
    instrument_position_cm = parse_float_triplet(
        instrument.properties.get("Position", ""), "InstrumentFrame.Position"
    )
    instrument_rotation_deg = parse_float_triplet(
        instrument.properties.get("Rotation", ""), "InstrumentFrame.Rotation"
    )
    world_from_instrument = rotation_xyz_matrix(instrument_rotation_deg)
    instrument_from_world = world_from_instrument.T

    normalized_names: list[str] = []
    copy_numbers: list[int] = []
    for solid in solids:
        name, copy_number = normalize_wrl_tag(solid.tag, resolved_geo)
        normalized_names.append(name)
        copy_numbers.append(copy_number)

    vertex_chunks: list[np.ndarray] = []
    instrument_vertex_chunks: list[np.ndarray] = []
    polygon_vertex_indices: list[int] = []
    polygon_index_offsets = [0]
    triangle_chunks: list[tuple[int, int, int]] = []
    triangle_solid_ids: list[int] = []
    solid_vertex_offsets = [0]
    solid_polygon_offsets = [0]
    solid_triangle_offsets = [0]
    world_bounds_per_solid: list[np.ndarray] = []
    instrument_bounds_per_solid: list[np.ndarray] = []
    manifest_rows: list[dict[str, Any]] = []

    for solid_index, (solid, geometry_name, copy_number) in enumerate(
        zip(solids, normalized_names, copy_numbers, strict=True)
    ):
        geo = resolved_geo[geometry_name]
        world_vertices = np.asarray(solid.vertices_world_mm, dtype=np.float64)
        world_cm = world_vertices / 10.0
        instrument_vertices = (world_cm - instrument_position_cm) @ world_from_instrument
        vertex_start = solid_vertex_offsets[-1]
        polygon_start = solid_polygon_offsets[-1]
        triangle_start = solid_triangle_offsets[-1]

        vertex_chunks.append(world_vertices)
        instrument_vertex_chunks.append(instrument_vertices)
        solid_vertex_offsets.append(vertex_start + len(world_vertices))

        for polygon in solid.polygons:
            global_polygon = [vertex_start + index for index in polygon]
            polygon_vertex_indices.extend(global_polygon)
            polygon_index_offsets.append(len(polygon_vertex_indices))
            for index in range(1, len(global_polygon) - 1):
                triangle_chunks.append(
                    (global_polygon[0], global_polygon[index], global_polygon[index + 1])
                )
                triangle_solid_ids.append(solid_index)
        solid_polygon_offsets.append(polygon_start + len(solid.polygons))
        solid_triangle_offsets.append(triangle_start + len(triangle_chunks) - triangle_start)

        world_bounds = np.vstack((world_vertices.min(axis=0), world_vertices.max(axis=0)))
        instrument_bounds = np.vstack(
            (instrument_vertices.min(axis=0), instrument_vertices.max(axis=0))
        )
        world_bounds_per_solid.append(world_bounds)
        instrument_bounds_per_solid.append(instrument_bounds)
        category = category_for(geometry_name)

        manifest_rows.append(
            {
                "solid_index": solid_index,
                "wrl_solid_tag": solid.tag,
                "wrl_copy_number": copy_number,
                "geometry_name": geometry_name,
                "geo_record_kind": geo.record_kind,
                "copy_source": geo.source,
                "material": geo.material,
                "mother": geo.mother,
                "shape_token": geo.shape_token,
                "shape_kind": geo.shape_kind,
                "is_placed_csg": str(geo.is_placed and geo.is_csg).lower(),
                "is_active_veto": str(geometry_name in ACTIVE_VETO_NAMES).lower(),
                "required_group": category,
                "vertex_count": len(world_vertices),
                "polygon_count": len(solid.polygons),
                "triangle_count": solid_triangle_offsets[-1] - triangle_start,
                "wrl_line_start": solid.line_start,
                "wrl_line_end": solid.line_end,
                "diffuse_r": solid.diffuse_rgb[0],
                "diffuse_g": solid.diffuse_rgb[1],
                "diffuse_b": solid.diffuse_rgb[2],
                "transparency": solid.transparency,
                "world_length_unit": "mm",
                "world_x_min_mm": world_bounds[0, 0],
                "world_y_min_mm": world_bounds[0, 1],
                "world_z_min_mm": world_bounds[0, 2],
                "world_x_max_mm": world_bounds[1, 0],
                "world_y_max_mm": world_bounds[1, 1],
                "world_z_max_mm": world_bounds[1, 2],
                "instrument_length_unit": "cm",
                "instrument_x_min_cm": instrument_bounds[0, 0],
                "instrument_y_min_cm": instrument_bounds[0, 1],
                "instrument_z_min_cm": instrument_bounds[0, 2],
                "instrument_x_max_cm": instrument_bounds[1, 0],
                "instrument_y_max_cm": instrument_bounds[1, 1],
                "instrument_z_max_cm": instrument_bounds[1, 2],
            }
        )

    vertices_world_mm = np.concatenate(vertex_chunks, axis=0)
    vertices_instrument_cm = np.concatenate(instrument_vertex_chunks, axis=0)
    triangles = np.asarray(triangle_chunks, dtype=np.int32).reshape((-1, 3))
    world_solid_bounds = np.asarray(world_bounds_per_solid, dtype=np.float64)
    instrument_solid_bounds = np.asarray(instrument_bounds_per_solid, dtype=np.float64)
    world_global_bounds = np.vstack(
        (vertices_world_mm.min(axis=0), vertices_world_mm.max(axis=0))
    )
    instrument_global_bounds = np.vstack(
        (vertices_instrument_cm.min(axis=0), vertices_instrument_cm.max(axis=0))
    )

    material_names = [resolved_geo[name].material for name in normalized_names]
    shape_kinds_for_solids = [resolved_geo[name].shape_kind for name in normalized_names]
    categories = [category_for(name) for name in normalized_names]
    display_rgba = np.asarray(
        [
            (
                solid.diffuse_rgb[0],
                solid.diffuse_rgb[1],
                solid.diffuse_rgb[2],
                1.0 - solid.transparency,
            )
            for solid in solids
        ],
        dtype=np.float32,
    )

    mesh_arrays: dict[str, np.ndarray] = {
        "schema_version": np.asarray(SCHEMA_VERSION),
        "world_length_unit": np.asarray("mm"),
        "instrument_length_unit": np.asarray("cm"),
        "vertices_world_mm": vertices_world_mm,
        "vertices_instrument_cm": vertices_instrument_cm,
        "triangles": triangles,
        "triangle_solid_ids": np.asarray(triangle_solid_ids, dtype=np.int32),
        "polygon_vertex_indices": np.asarray(polygon_vertex_indices, dtype=np.int32),
        "polygon_index_offsets": np.asarray(polygon_index_offsets, dtype=np.int64),
        "solid_vertex_offsets": np.asarray(solid_vertex_offsets, dtype=np.int64),
        "solid_polygon_offsets": np.asarray(solid_polygon_offsets, dtype=np.int64),
        "solid_triangle_offsets": np.asarray(solid_triangle_offsets, dtype=np.int64),
        "solid_names": np.asarray(normalized_names),
        "wrl_solid_tags": np.asarray([solid.tag for solid in solids]),
        "materials": np.asarray(material_names),
        "shape_kinds": np.asarray(shape_kinds_for_solids),
        "required_groups": np.asarray(categories),
        "is_placed_csg": np.asarray(
            [resolved_geo[name].is_placed and resolved_geo[name].is_csg for name in normalized_names],
            dtype=np.bool_,
        ),
        "is_active_veto": np.asarray(
            [name in ACTIVE_VETO_NAMES for name in normalized_names], dtype=np.bool_
        ),
        "display_rgba": display_rgba,
        "world_bounds_per_solid_mm": world_solid_bounds,
        "instrument_bounds_per_solid_cm": instrument_solid_bounds,
        "instrument_position_world_cm": instrument_position_cm,
        "instrument_rotation_xyz_deg": instrument_rotation_deg,
        "world_from_instrument_rotation": world_from_instrument,
        "instrument_from_world_rotation": instrument_from_world,
    }

    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        passed: bool,
        expected: Any,
        actual: Any,
        severity: str = "critical",
        details: Any | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "id": check_id,
            "status": "PASS" if passed else "FAIL",
            "severity": severity,
            "expected": expected,
            "actual": actual,
        }
        if details is not None:
            record["details"] = details
        checks.append(record)

    unique_tags = set(solid.tag for solid in solids)
    unique_names = set(normalized_names)
    geometry_volume_count = sum(obj.record_kind == "volume" for obj in geo_objects.values())
    geometry_copy_count = sum(obj.record_kind == "copy" for obj in geo_objects.values())
    expected_drawable = {
        name
        for name, geo in resolved_geo.items()
        if geo.is_placed and geo.material != "Vacuum" and bool(geo.shape_token)
    }
    actual_csg_names = {
        name
        for name in normalized_names
        if resolved_geo[name].is_placed and resolved_geo[name].is_csg
    }

    add_check("solid_count", len(solids) == EXPECTED_SOLID_COUNT, EXPECTED_SOLID_COUNT, len(solids))
    add_check("unique_wrl_tags", len(unique_tags) == len(solids), len(solids), len(unique_tags))
    add_check(
        "unique_geometry_names",
        len(unique_names) == len(solids),
        len(solids),
        len(unique_names),
    )
    add_check(
        "geometry_volume_count",
        geometry_volume_count == EXPECTED_GEOMETRY_VOLUME_COUNT,
        EXPECTED_GEOMETRY_VOLUME_COUNT,
        geometry_volume_count,
    )
    add_check(
        "geometry_copy_count",
        geometry_copy_count == EXPECTED_GEOMETRY_COPY_COUNT,
        EXPECTED_GEOMETRY_COPY_COUNT,
        geometry_copy_count,
    )
    add_check(
        "geometry_object_count",
        len(geo_objects) == EXPECTED_GEOMETRY_OBJECT_COUNT,
        EXPECTED_GEOMETRY_OBJECT_COUNT,
        len(geo_objects),
    )
    add_check(
        "exact_drawable_set_match",
        unique_names == expected_drawable,
        len(expected_drawable),
        len(unique_names),
        details={
            "missing_from_wrl": sorted(expected_drawable - unique_names),
            "unexpected_in_wrl": sorted(unique_names - expected_drawable),
        },
    )
    add_check(
        "placed_csg_exact_set",
        actual_csg_names == set(EXPECTED_PLACED_CSG_NAMES),
        sorted(EXPECTED_PLACED_CSG_NAMES),
        sorted(actual_csg_names),
        details={
            "expected_count": 20,
            "actual_count": len(actual_csg_names),
            "missing": sorted(set(EXPECTED_PLACED_CSG_NAMES) - actual_csg_names),
            "unexpected": sorted(actual_csg_names - set(EXPECTED_PLACED_CSG_NAMES)),
        },
    )

    group_results: dict[str, Any] = {}
    for group_name, required_names in REQUIRED_GROUPS.items():
        expected_names = set(required_names)
        found_names = expected_names & unique_names
        group_results[group_name] = {
            "expected_count": len(expected_names),
            "found_count": len(found_names),
            "expected_names": sorted(expected_names),
            "found_names": sorted(found_names),
            "missing_names": sorted(expected_names - unique_names),
        }
        add_check(
            f"required_group_{group_name}",
            found_names == expected_names,
            len(expected_names),
            len(found_names),
            details=group_results[group_name],
        )

    for group_name, expected_material in EXPECTED_GROUP_MATERIALS.items():
        observed = sorted({resolved_geo[name].material for name in REQUIRED_GROUPS[group_name]})
        add_check(
            f"material_{group_name}",
            observed == [expected_material],
            [expected_material],
            observed,
        )

    add_check(
        "instrument_position",
        bool(np.allclose(instrument_position_cm, (0.0, 0.0, 0.0), atol=1.0e-12)),
        [0.0, 0.0, 0.0],
        instrument_position_cm.tolist(),
    )
    add_check(
        "instrument_rotation",
        bool(np.allclose(instrument_rotation_deg, (0.0, 45.0, 0.0), atol=1.0e-12)),
        [0.0, 45.0, 0.0],
        instrument_rotation_deg.tolist(),
    )
    reconstructed_world_cm = vertices_instrument_cm @ world_from_instrument.T + instrument_position_cm
    transform_roundtrip_error_cm = float(np.max(np.abs(reconstructed_world_cm - vertices_world_mm / 10.0)))
    add_check(
        "coordinate_transform_roundtrip",
        transform_roundtrip_error_cm <= 1.0e-10,
        "<= 1e-10 cm",
        transform_roundtrip_error_cm,
    )
    finite_mesh = bool(
        np.isfinite(vertices_world_mm).all()
        and np.isfinite(vertices_instrument_cm).all()
        and np.isfinite(display_rgba).all()
    )
    add_check("finite_mesh_values", finite_mesh, True, finite_mesh)
    world_max_abs = float(np.max(np.abs(world_global_bounds)))
    instrument_max_abs = float(np.max(np.abs(instrument_global_bounds)))
    add_check(
        "world_mm_scale_envelope",
        500.0 <= world_max_abs <= 700.0,
        {"unit": "mm", "min_max_abs": 500.0, "max_max_abs": 700.0},
        world_max_abs,
    )
    add_check(
        "instrument_cm_scale_envelope",
        60.0 <= instrument_max_abs <= 75.0,
        {"unit": "cm", "min_max_abs": 60.0, "max_max_abs": 75.0},
        instrument_max_abs,
    )

    manifest_fields = list(manifest_rows[0].keys())
    atomic_csv(manifest_path, manifest_fields, manifest_rows)
    atomic_npz(mesh_path, mesh_arrays)

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    audit: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Geometry-only post-processing of the native S3d-O8 Geant4 WRL; "
            "no event overlay or transport data are included."
        ),
        "inputs": {
            "source_card": file_record(source_card),
            "geometry_setup": file_record(setup_path),
            "intro_geo": file_record(intro_geo),
            "main_geo": file_record(main_geo),
            "native_wrl": file_record(wrl_path),
            "builder": file_record(Path(__file__).resolve()),
        },
        "outputs": {
            "volume_manifest_csv": file_record(manifest_path),
            "mesh_npz": file_record(mesh_path),
        },
        "coordinate_systems": {
            "geomega_authority": {
                "length_unit": "cm",
                "description": "Input .geo dimensions and placements.",
            },
            "wrl_world": {
                "length_unit": "mm",
                "description": (
                    "Geant4 world coordinates written directly by the VRML2FILE driver "
                    "after Geomega hierarchy and CSG resolution."
                ),
                "bounds": bounds_dict(world_global_bounds, "mm"),
            },
            "instrument_frame": {
                "length_unit": "cm",
                "position_world_cm": instrument_position_cm.tolist(),
                "rotation_xyz_deg": instrument_rotation_deg.tolist(),
                "rotation_convention": "world = Rz * Ry * Rx * instrument + position",
                "world_from_instrument_rotation": world_from_instrument.tolist(),
                "instrument_from_world_rotation": instrument_from_world.tolist(),
                "current_closed_form": {
                    "x_instrument_cm": "(X_world_mm - Z_world_mm) / (10*sqrt(2))",
                    "y_instrument_cm": "Y_world_mm / 10",
                    "z_instrument_cm": "(X_world_mm + Z_world_mm) / (10*sqrt(2))",
                },
                "bounds": bounds_dict(instrument_global_bounds, "cm"),
                "roundtrip_max_abs_error_cm": transform_roundtrip_error_cm,
            },
        },
        "counts": {
            "geometry_volume_definitions_including_intro": geometry_volume_count,
            "geometry_copy_declarations": geometry_copy_count,
            "geometry_named_objects": len(geo_objects),
            "expected_drawable_nonvacuum_placements": len(expected_drawable),
            "wrl_top_level_solids": len(solids),
            "unique_wrl_tags": len(unique_tags),
            "unique_joined_geometry_names": len(unique_names),
            "placed_csg_solids": len(actual_csg_names),
            "vertices": int(len(vertices_world_mm)),
            "polygons": int(len(polygon_index_offsets) - 1),
            "triangles": int(len(triangles)),
            "materials": len(set(material_names)),
        },
        "required_groups": group_results,
        "placed_csg_names": sorted(actual_csg_names),
        "checks": checks,
        "limitations": [
            "The WRL is a Geant4 polyhedral visualization mesh, not analytic STEP/B-rep CAD.",
            "Curved surfaces are faceted at the export setting of 100 line segments per circle.",
            "The NPZ preserves original WRL polygons and also supplies fan-triangulated faces.",
            "Material tokens come from exact Geomega Volume/Copy inheritance, not WRL colours.",
        ],
    }
    atomic_json(audit_path, audit)

    if status != "PASS":
        failed = [check["id"] for check in checks if check["status"] == "FAIL"]
        raise GeometryProductError(
            f"Geometry validation failed ({', '.join(failed)}); see {audit_path}"
        )
    return audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-card", default=str(DEFAULT_SOURCE_CARD))
    parser.add_argument("--wrl", default=str(DEFAULT_WRL))
    parser.add_argument("--setup", help="Override geometry .geo.setup path")
    parser.add_argument("--main-geo", help="Override main S3d-O8 .geo path")
    parser.add_argument("--intro-geo", help="Override Intro .geo path")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--mesh-npz", default=str(DEFAULT_MESH_NPZ))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        audit = build_products(args)
    except (GeometryProductError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    counts = audit["counts"]
    print(
        "PASS: "
        f"{counts['wrl_top_level_solids']} solids, "
        f"{counts['vertices']} vertices, "
        f"{counts['polygons']} polygons, "
        f"{counts['triangles']} triangles, "
        f"{counts['placed_csg_solids']} placed CSG solids"
    )
    print(f"manifest: {resolve_path(args.manifest)}")
    print(f"mesh: {resolve_path(args.mesh_npz)}")
    print(f"audit: {resolve_path(args.audit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
