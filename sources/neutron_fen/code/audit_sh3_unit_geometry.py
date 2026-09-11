#!/usr/bin/env python3
"""Deterministically audit the SH3 Si/Ta unit geometry snapshot.

This script intentionally reads only the four compact files in
``input_snapshot/geometry`` and writes one JSON artifact.  It does not follow
Include directives, inspect SIM files, or import geometry from another worktree.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_DIR = ROOT / "input_snapshot" / "geometry"
OUTPUT = ROOT / "outputs" / "sh3_unit_geometry.json"
PIXEL_MAP_OUTPUT = ROOT / "outputs" / "tes_pixel_map.csv"

REL_GEO = "input_snapshot/geometry/SH3_Assembly_OptV3.geo"
REL_DET = "input_snapshot/geometry/SH3_Assembly_OptV3.det"
REL_SI_DET = "input_snapshot/geometry/SH3_Assembly_OptV3_SiSubstrateSD.det"
REL_SETUP = "input_snapshot/geometry/SH3_Assembly_OptV3_SiSubstrateSD_60cm.geo.setup"

SOURCE_PATHS = {
    REL_GEO: ROOT / REL_GEO,
    REL_DET: ROOT / REL_DET,
    REL_SI_DET: ROOT / REL_SI_DET,
    REL_SETUP: ROOT / REL_SETUP,
}

EXPECTED_SHA256 = {
    REL_GEO: "a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934",
    REL_DET: "12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9",
    REL_SI_DET: "799dbdf1eb82950aa92f763a0f49ebde0b5cc6a6cfc6fa411571eff6fed36754",
    REL_SETUP: "a1dcb621c141667cf07d9ff16d7535de32a904563e91d492d73e485713e62f77",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(a: float, b: float, atol: float = 1.0e-12) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=atol)


def vector_close(a: list[float], b: list[float], atol: float = 1.0e-12) -> bool:
    return len(a) == len(b) and all(close(x, y, atol) for x, y in zip(a, b))


def clean(value: float, digits: int = 12) -> float:
    rounded = round(value, digits)
    return 0.0 if rounded == -0.0 else rounded


class Source:
    def __init__(self, relpath: str, path: Path) -> None:
        self.relpath = relpath
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()

    def unique_regex(self, pattern: str) -> tuple[int, re.Match[str]]:
        regex = re.compile(pattern)
        hits: list[tuple[int, re.Match[str]]] = []
        for number, line in enumerate(self.lines, start=1):
            match = regex.fullmatch(line.strip())
            if match:
                hits.append((number, match))
        if len(hits) != 1:
            raise AssertionError(
                f"Expected exactly one match for {pattern!r} in {self.relpath}; got {len(hits)}"
            )
        return hits[0]

    def property_tokens(self, name: str, prop: str) -> tuple[int, list[str]]:
        line, match = self.unique_regex(
            rf"{re.escape(name)}\.{re.escape(prop)}\s+(.+)"
        )
        return line, match.group(1).split()

    def vector(self, name: str, prop: str) -> tuple[int, list[float]]:
        line, tokens = self.property_tokens(name, prop)
        return line, [float(value) for value in tokens]

    def brik_half_lengths(self, name: str) -> tuple[int, list[float]]:
        line, tokens = self.property_tokens(name, "Shape")
        if len(tokens) != 4 or tokens[0] != "BRIK":
            raise AssertionError(f"{name} is not an inline BRIK: {tokens}")
        return line, [float(value) for value in tokens[1:]]


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, detail: Any = None) -> None:
    record: dict[str, Any] = {"name": name, "passed": bool(condition)}
    if detail is not None:
        record["detail"] = detail
    checks.append(record)
    if not condition:
        raise AssertionError(f"Self-check failed: {name}: {detail}")


def ref(file: str, lines: int | list[int]) -> dict[str, Any]:
    if isinstance(lines, int):
        lines = [lines]
    return {"file": file, "lines": lines}


def main() -> None:
    sources = {relpath: Source(relpath, path) for relpath, path in SOURCE_PATHS.items()}
    geo = sources[REL_GEO]
    det = sources[REL_DET]
    si_det = sources[REL_SI_DET]
    setup = sources[REL_SETUP]

    source_manifest: dict[str, Any] = {}
    for relpath, path in SOURCE_PATHS.items():
        actual_hash = sha256(path)
        check(
            f"pinned SHA-256: {relpath}",
            actual_hash == EXPECTED_SHA256[relpath],
            {"expected": EXPECTED_SHA256[relpath], "actual": actual_hash},
        )
        source_manifest[relpath] = {
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
            "line_count": len(sources[relpath].lines),
        }

    frame_position_line, frame_position = geo.vector("InstrumentFrame", "Position")
    frame_rotation_line, frame_rotation = geo.vector("InstrumentFrame", "Rotation")
    check("InstrumentFrame has zero translation", vector_close(frame_position, [0.0, 0.0, 0.0]))
    check("InstrumentFrame has pinned +45 degree y rotation", vector_close(frame_rotation, [0.0, 45.0, 0.0]))

    # For Rotation 0 45 0, use the ordinary right-handed active R_y(+45 deg)
    # convention.  The raw MEGAlib card is retained alongside this explicit
    # interpretation so downstream code never silently changes the sign.
    angle = math.radians(frame_rotation[1])
    cosine = math.cos(angle)
    sine = math.sin(angle)
    rotation_matrix = [
        [cosine, 0.0, sine],
        [0.0, 1.0, 0.0],
        [-sine, 0.0, cosine],
    ]

    def to_global(local: list[float]) -> list[float]:
        return [
            clean(sum(rotation_matrix[row][column] * local[column] for column in range(3)) + frame_position[row])
            for row in range(3)
        ]

    # Parse all Ta-copy placements and their immediately declared mothers.
    copy_definitions: dict[str, tuple[int, int]] = {}
    copy_positions: dict[str, tuple[int, list[float]]] = {}
    copy_mothers: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(geo.lines, start=1):
        stripped = line.strip()
        match = re.fullmatch(r"TES_Pixel_L([0-5])\.Copy\s+(TP_L\1_[0-9]{5})", stripped)
        if match:
            copy_definitions[match.group(2)] = (number, int(match.group(1)))
            continue
        match = re.fullmatch(r"(TP_L[0-5]_[0-9]{5})\.Position\s+(.+)", stripped)
        if match:
            copy_positions[match.group(1)] = (
                number,
                [float(value) for value in match.group(2).split()],
            )
            continue
        match = re.fullmatch(r"(TP_L[0-5]_[0-9]{5})\.Mother\s+(TES_L[0-5])", stripped)
        if match:
            copy_mothers[match.group(1)] = (number, match.group(2))

    check("all Ta copies have positions", set(copy_definitions) == set(copy_positions))
    check("all Ta copies have mothers", set(copy_definitions) == set(copy_mothers))

    grids: dict[int, list[list[float]]] = defaultdict(list)
    copy_line_ranges: dict[int, list[int]] = {}
    for layer in range(6):
        names = sorted(name for name, (_, value) in copy_definitions.items() if value == layer)
        check(f"L{layer} has 376 Ta copies", len(names) == 376, len(names))
        check(
            f"L{layer} Ta copy indices are contiguous 00000..00375",
            names == [f"TP_L{layer}_{index:05d}" for index in range(376)],
        )
        for name in names:
            position_line, position = copy_positions[name]
            mother_line, mother = copy_mothers[name]
            check(f"{name} local x is zero", close(position[0], 0.0))
            check(f"{name} mother is TES_L{layer}", mother == f"TES_L{layer}")
            grids[layer].append(position)
        copy_line_ranges[layer] = [
            copy_definitions[names[0]][0],
            copy_mothers[names[-1]][0],
        ]

    reference_grid = grids[0]
    for layer in range(1, 6):
        check(f"L{layer} Ta layout equals L0", grids[layer] == reference_grid)

    ta_pixel_shape_lines: list[int] = []
    ta_envelope_shape_lines: list[int] = []
    ta_envelope_position_lines: list[int] = []
    si_shape_lines: list[int] = []
    si_position_lines: list[int] = []
    layer_records: list[dict[str, Any]] = []
    ta_centres: list[float] = []
    si_centres: list[float] = []

    for layer in range(6):
        pixel_name = f"TES_Pixel_L{layer}"
        envelope_name = f"TES_L{layer}"
        substrate_name = f"Si_Substrate_Stack_side_entry_L{layer}"

        pixel_shape_line, pixel_half = geo.brik_half_lengths(pixel_name)
        envelope_shape_line, envelope_half = geo.brik_half_lengths(envelope_name)
        envelope_position_line, envelope_position = geo.vector(envelope_name, "Position")
        substrate_shape_line, substrate_half = geo.brik_half_lengths(substrate_name)
        substrate_position_line, substrate_position = geo.vector(substrate_name, "Position")
        pixel_material_line, pixel_material = geo.property_tokens(pixel_name, "Material")
        substrate_material_line, substrate_material = geo.property_tokens(substrate_name, "Material")

        check(f"L{layer} Ta material", pixel_material == ["Ta"])
        check(f"L{layer} Ta half dimensions", vector_close(pixel_half, [0.15, 0.075, 0.075]))
        check(f"L{layer} envelope half dimensions", vector_close(envelope_half, [0.15, 1.8, 1.8]))
        check(f"L{layer} Si material", substrate_material == ["Silicon"])
        check(f"L{layer} Si half dimensions", vector_close(substrate_half, [0.015, 1.8, 1.8]))
        check(
            f"L{layer} Ta and Si share y,z centre",
            vector_close(envelope_position[1:], substrate_position[1:]),
        )

        ta_centres.append(envelope_position[0])
        si_centres.append(substrate_position[0])
        axial_offset = substrate_position[0] - envelope_position[0]
        axial_gap = axial_offset - pixel_half[0] - substrate_half[0]
        check(f"L{layer} Ta-to-Si centre offset is 0.18 cm", close(axial_offset, 0.18), axial_offset)
        check(f"L{layer} Ta-to-Si face gap is 0.015 cm", close(axial_gap, 0.015), axial_gap)

        ta_pixel_shape_lines.append(pixel_shape_line)
        ta_envelope_shape_lines.append(envelope_shape_line)
        ta_envelope_position_lines.append(envelope_position_line)
        si_shape_lines.append(substrate_shape_line)
        si_position_lines.append(substrate_position_line)
        layer_records.append(
            {
                "layer": layer,
                "ta_pixel_material": pixel_material[0],
                "ta_pixel_center_local_cm": envelope_position,
                "ta_pixel_center_global_cm": to_global(envelope_position),
                "si_center_local_cm": substrate_position,
                "si_center_global_cm": to_global(substrate_position),
                "si_minus_ta_center_xprime_cm": clean(axial_offset),
                "ta_downstream_face_xprime_cm": clean(envelope_position[0] + pixel_half[0]),
                "si_upstream_face_xprime_cm": clean(substrate_position[0] - substrate_half[0]),
                "vacuum_face_gap_cm": clean(axial_gap),
                "vacuum_face_gap_mm": clean(axial_gap * 10.0),
                "contact_in_proxy": False,
                "ta_copy_source": ref(REL_GEO, copy_line_ranges[layer]),
                "ta_center_source": ref(REL_GEO, envelope_position_line),
                "si_source": ref(REL_GEO, [substrate_shape_line, substrate_position_line]),
            }
        )

    layer_pitches = [ta_centres[index + 1] - ta_centres[index] for index in range(5)]
    check("all Ta layer centre pitches are 1.2 cm", all(close(value, 1.2) for value in layer_pitches), layer_pitches)
    check(
        "all Si layer centre pitches are 1.2 cm",
        all(close(si_centres[index + 1] - si_centres[index], 1.2) for index in range(5)),
    )

    # Detector-map pitch is independent corroboration of the explicit copy grid.
    pitch_lines: list[int] = []
    detector_pitches: list[list[float]] = []
    for detector_index in range(1, 7):
        pitch_line, pitch = det.vector(f"D{detector_index}", "StructuralPitch")
        pitch_lines.append(pitch_line)
        detector_pitches.append(pitch)
    check(
        "all six detector-map pitches are identical",
        all(vector_close(value, [0.155, 0.155, 0.1]) for value in detector_pitches),
        detector_pitches,
    )

    yz_centres = [(position[1], position[2]) for position in reference_grid]
    unique_y = sorted(set(y for y, _ in yz_centres))
    unique_z = sorted(set(z for _, z in yz_centres))
    y_step = min(b - a for a, b in zip(unique_y, unique_y[1:]))
    z_step = min(b - a for a, b in zip(unique_z, unique_z[1:]))
    check("explicit y grid step is 0.155 cm", close(y_step, 0.155), y_step)
    check("explicit z grid step is 0.155 cm", close(z_step, 0.155), z_step)

    row_counts = Counter(y for y, _ in yz_centres)
    disk_sites = {
        (clean(i * 0.155, 3), clean(j * 0.155, 3))
        for i in range(-11, 12)
        for j in range(-11, 12)
        if i * i + j * j <= 11 * 11
    }
    explicit_sites = {(clean(y, 3), clean(z, 3)) for y, z in yz_centres}
    missing_disk_sites = sorted(disk_sites - explicit_sites)
    extra_disk_sites = sorted(explicit_sites - disk_sites)
    check("layout is an r=11 pitch lattice disk minus one site", len(disk_sites) == 377)
    check("only (+1.705, 0) is missing from that disk", missing_disk_sites == [(1.705, 0.0)], missing_disk_sites)
    check("no sites lie outside that disk", not extra_disk_sites, extra_disk_sites)

    pixel_half = [0.15, 0.075, 0.075]
    substrate_half = [0.015, 1.8, 1.8]
    pixel_full_cm = [2.0 * value for value in pixel_half]
    substrate_full_cm = [2.0 * value for value in substrate_half]
    projected_pixel_area_cm2 = pixel_full_cm[1] * pixel_full_cm[2]
    projected_ta_area_cm2 = len(reference_grid) * projected_pixel_area_cm2
    substrate_face_area_cm2 = substrate_full_cm[1] * substrate_full_cm[2]
    coverage_fraction = projected_ta_area_cm2 / substrate_face_area_cm2
    inplane_edge_gap = y_step - pixel_full_cm[1]
    footprint_extrema = {
        "y": [
            min(y for y, _ in yz_centres) - pixel_half[1],
            max(y for y, _ in yz_centres) + pixel_half[1],
        ],
        "z": [
            min(z for _, z in yz_centres) - pixel_half[2],
            max(z for _, z in yz_centres) + pixel_half[2],
        ],
    }
    substrate_side_margins = {
        "y_minus": footprint_extrema["y"][0] - (-substrate_half[1]),
        "y_plus": substrate_half[1] - footprint_extrema["y"][1],
        "z_minus": footprint_extrema["z"][0] - (-substrate_half[2]),
        "z_plus": substrate_half[2] - footprint_extrema["z"][1],
    }
    substrate_axis_margin = min(substrate_side_margins.values())
    check("Ta rectangles do not overlap", inplane_edge_gap > 0.0, inplane_edge_gap)
    check("all Ta rectangles fit inside Si projection", substrate_axis_margin >= 0.0, substrate_axis_margin)
    check("proxy Ta projected coverage is 235/360", close(coverage_fraction, 235.0 / 360.0), coverage_fraction)

    # Compact direct input for the Geant4CMP application.  Numeric pixel_id N
    # maps exactly to the source copy TP_L0_NNNNN.  Coordinates are L0-local
    # in-plane centres; all other layers were asserted identical above.
    pixel_csv_lines = ["pixel_id,y_mm,z_mm"]
    for pixel_id, (_, y_cm, z_cm) in enumerate(reference_grid):
        pixel_csv_lines.append(
            f"{pixel_id},{format(y_cm * 10.0, '.12g')},{format(z_cm * 10.0, '.12g')}"
        )
    pixel_csv_text = "\n".join(pixel_csv_lines) + "\n"
    PIXEL_MAP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PIXEL_MAP_OUTPUT.write_text(pixel_csv_text, encoding="utf-8")
    check("pixel-map CSV has header plus 376 rows", len(pixel_csv_lines) == 377)
    check(
        "pixel-map CSV round-trips exactly",
        PIXEL_MAP_OUTPUT.read_text(encoding="utf-8") == pixel_csv_text,
    )
    pixel_map_sha256 = sha256(PIXEL_MAP_OUTPUT)

    # Five four-panel open supports follow substrates L0..L4 in +x'.
    open_supports: list[dict[str, Any]] = []
    support_shape_lines: list[int] = []
    support_position_lines: list[int] = []
    for support_index in range(1, 6):
        upstream_layer = support_index - 1
        component_records: list[dict[str, Any]] = []
        x_centres: list[float] = []
        inplane_clearances: list[float] = []
        for suffix in ("ZP", "ZM", "YP", "YM"):
            name = f"Cu_SubstrateSupport_OpenRing_L{support_index}_{suffix}_panel"
            shape_line, half = geo.brik_half_lengths(name)
            position_line, position = geo.vector(name, "Position")
            material_line, material = geo.property_tokens(name, "Material")
            check(f"{name} is Copper", material == ["Copper"])
            x_centres.append(position[0])
            if suffix.startswith("Z"):
                clearance = abs(position[2] - layer_records[upstream_layer]["si_center_local_cm"][2]) - half[2] - substrate_half[2]
            else:
                clearance = abs(position[1] - layer_records[upstream_layer]["si_center_local_cm"][1]) - half[1] - substrate_half[1]
            inplane_clearances.append(clearance)
            support_shape_lines.append(shape_line)
            support_position_lines.append(position_line)
            component_records.append(
                {
                    "name": name,
                    "full_dimensions_cm": [clean(2.0 * value) for value in half],
                    "position_local_cm": position,
                    "source": ref(REL_GEO, [shape_line, position_line, material_line]),
                }
            )
        check(f"open support L{support_index} components share x centre", all(close(value, x_centres[0]) for value in x_centres))
        check(f"open support L{support_index} has 0.05 cm in-plane Si clearance", all(close(value, 0.05) for value in inplane_clearances), inplane_clearances)
        substrate_downstream_face = si_centres[upstream_layer] + substrate_half[0]
        support_upstream_face = x_centres[0] - 0.15
        axial_clearance = support_upstream_face - substrate_downstream_face
        check(f"open support L{support_index} has 0.005 cm axial clearance", close(axial_clearance, 0.005), axial_clearance)
        open_supports.append(
            {
                "name_index": support_index,
                "coordinate_adjacent_substrate_layer": upstream_layer,
                "components": component_records,
                "axial_clearance_from_si_cm": clean(axial_clearance),
                "axial_clearance_from_si_mm": clean(axial_clearance * 10.0),
                "minimum_inplane_clearance_from_si_cm": clean(min(inplane_clearances)),
                "minimum_inplane_clearance_from_si_mm": clean(min(inplane_clearances) * 10.0),
                "minimum_euclidean_clearance_from_si_mm": clean(
                    10.0 * math.hypot(axial_clearance, min(inplane_clearances))
                ),
                "contact_with_si": False,
            }
        )

    # Coordinate-nearest final heat-sink ring (despite its inherited L0 name).
    outer_line, outer_half = geo.vector(
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_OuterShape", "Parameters"
    )
    cut_line, cut_half = geo.vector(
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutShape", "Parameters"
    )
    heat_position_line, heat_position = geo.vector(
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm", "Position"
    )
    heat_material_line, heat_material = geo.property_tokens(
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm", "Material"
    )
    check("heat-sink ring material is Copper", heat_material == ["Copper"])
    check("heat-sink outer half dimensions", vector_close(outer_half, [0.175, 2.8, 2.8]))
    check("heat-sink cut half dimensions", vector_close(cut_half, [0.1751, 0.8, 0.8]))
    heat_axial_clearance = (heat_position[0] - outer_half[0]) - (si_centres[5] + substrate_half[0])
    check("heat-sink ring is 0.05 cm downstream of L5 Si", close(heat_axial_clearance, 0.05), heat_axial_clearance)
    heat_projected_overlap_cm2 = substrate_face_area_cm2 - (2.0 * cut_half[1]) * (2.0 * cut_half[2])

    # Four longitudinal corner rods.  Their x intervals overlap the stack, but
    # both transverse intervals are outside each substrate edge.
    edge_rods: list[dict[str, Any]] = []
    rod_downstream_faces: list[float] = []
    for rod_index in range(1, 5):
        name = f"Cu_SubstrateSupport_EdgeRod_{rod_index}"
        shape_line, half = geo.brik_half_lengths(name)
        position_line, position = geo.vector(name, "Position")
        material_line, material = geo.property_tokens(name, "Material")
        check(f"{name} is Copper", material == ["Copper"])
        y_clearance = abs(position[1]) - half[1] - substrate_half[1]
        z_clearance = abs(position[2] - si_centres[0] * 0.0 - (-2.8)) - half[2] - substrate_half[2]
        # The explicit '-2.8' above is the common substrate local-z centre; the
        # zero-valued term makes clear no x coordinate enters this calculation.
        check(f"{name} y clearance is positive", y_clearance > 0.0, y_clearance)
        check(f"{name} z clearance is positive", z_clearance > 0.0, z_clearance)
        rod_downstream_faces.append(position[0] + half[0])
        edge_rods.append(
            {
                "name": name,
                "full_dimensions_cm": [clean(2.0 * value) for value in half],
                "position_local_cm": position,
                "y_clearance_from_si_edge_mm": clean(y_clearance * 10.0),
                "z_clearance_from_si_edge_mm": clean(z_clearance * 10.0),
                "corner_euclidean_clearance_from_si_mm": clean(10.0 * math.hypot(y_clearance, z_clearance)),
                "contact_with_si": False,
                "source": ref(REL_GEO, [shape_line, position_line, material_line]),
            }
        )
    rod_to_heatsink_gap = (heat_position[0] - outer_half[0]) - max(rod_downstream_faces)
    check("edge rods stop 0.01 cm before heat-sink ring", close(rod_to_heatsink_gap, 0.01), rod_to_heatsink_gap)

    # The local copper completion is geometrically continuous from ring to stub,
    # but the source explicitly says the main-DR cold finger is absent.
    hub_shape_line, hub_tokens = geo.property_tokens("SH3_TES_BottomColdPlate_CentralHub", "Shape")
    hub_position_line, hub_position = geo.vector("SH3_TES_BottomColdPlate_CentralHub", "Position")
    stub_shape_line, stub_tokens = geo.property_tokens("SH3_TES_ColdFinger_InterfaceStub", "Shape")
    stub_position_line, stub_position = geo.vector("SH3_TES_ColdFinger_InterfaceStub", "Position")
    stub_rotation_line, stub_rotation = geo.vector("SH3_TES_ColdFinger_InterfaceStub", "Rotation")
    check("central hub is a TUBS", hub_tokens[0] == "TUBS")
    check("cold-finger stub is a TUBS", stub_tokens[0] == "TUBS")
    check("cold-finger stub is rotated onto local x axis", vector_close(stub_rotation, [0.0, 90.0, 0.0]))
    stub_half_length = float(stub_tokens[3])
    stub_upstream_face = stub_position[0] - stub_half_length
    heat_downstream_face = heat_position[0] + outer_half[0]
    check("cold-finger stub touches copper completion face", close(stub_upstream_face, heat_downstream_face), {"stub": stub_upstream_face, "plate": heat_downstream_face})

    # Verify all six diagnostic Si SD declarations and retain their exact role.
    si_sd_refs: list[dict[str, Any]] = []
    for layer in range(6):
        detector_name = f"Si_Substrate_Stack_side_entry_L{layer}_SD"
        sensitive_line, sensitive = si_det.property_tokens(detector_name, "SensitiveVolume")
        detector_line, detector_volume = si_det.property_tokens(detector_name, "DetectorVolume")
        threshold_line, threshold = si_det.property_tokens(detector_name, "TriggerThreshold")
        expected_volume = f"Si_Substrate_Stack_side_entry_L{layer}"
        check(f"L{layer} Si SD maps to substrate proxy", sensitive == [expected_volume] and detector_volume == [expected_volume])
        check(f"L{layer} Si SD threshold is 0.001 keV", threshold == ["0.001"])
        si_sd_refs.append(ref(REL_SI_DET, [sensitive_line, detector_line, threshold_line]))

    # Portability audit: preserve Include text but never follow it.
    setup_includes: list[dict[str, Any]] = []
    for number, line in enumerate(setup.lines, start=1):
        match = re.fullmatch(r"Include\s+(.+)", line.strip())
        if match:
            target = match.group(1)
            setup_includes.append(
                {
                    "line": number,
                    "target_as_written": target,
                    "absolute": Path(target).is_absolute(),
                    "followed_by_this_audit": False,
                }
            )
    check("setup contains three absolute Includes", len(setup_includes) == 3 and all(item["absolute"] for item in setup_includes), setup_includes)
    material_include_line, material_match = geo.unique_regex(r"Include\s+(.+)")
    material_include = material_match.group(1)
    material_present_in_snapshot = (GEOMETRY_DIR / material_include).exists()
    check("material include is absent from compact snapshot", not material_present_in_snapshot, material_include)

    absence_patterns = {
        "SiO2": r"\bSiO2\b",
        "SiNx": r"\bSiNx\b",
        "SiliconDioxide": r"\bSiliconDioxide\b",
        "SiliconNitride": r"\bSiliconNitride\b",
        "transition-edge sensor phrase": r"\btransition[- ]edge\b",
        "wiring": r"\bwiring\b",
        "wire": r"\bwire\b",
        "bond": r"\bbond\b",
        "Kapitza": r"\bKapitza\b",
        "epoxy": r"\bepoxy\b",
        "indium": r"\bindium\b",
    }
    absence_counts: dict[str, int] = {}
    searched_relpaths = [REL_GEO, REL_DET, REL_SI_DET]
    for label, pattern in absence_patterns.items():
        regex = re.compile(pattern, re.IGNORECASE)
        count = sum(len(regex.findall(sources[relpath].text)) for relpath in searched_relpaths)
        absence_counts[label] = count
        check(f"no explicit {label} token in audited geo/det files", count == 0, count)

    result: dict[str, Any] = {
        "schema_version": 1,
        "scope": {
            "purpose": "SH3 single-layer Geant4CMP geometry authority audit",
            "read_scope": list(SOURCE_PATHS),
            "include_directives_followed": False,
            "sim_files_read": False,
            "interpretation_boundary": (
                "Raw transport geometry is authoritative only for the listed proxy solids and placements. "
                "It is not authority for real TES films, dielectric stacks, wiring, contacts, or thermal boundary conditions."
            ),
        },
        "sources": source_manifest,
        "generator": {
            "path": "code/audit_sh3_unit_geometry.py",
            "sha256": sha256(Path(__file__).resolve()),
        },
        "derived_artifacts": {
            "outputs/tes_pixel_map.csv": {
                "sha256": pixel_map_sha256,
                "columns": ["pixel_id", "y_mm", "z_mm"],
                "data_rows": len(reference_grid),
                "coordinate_frame": "TES_L0 local; x'=0 for every Ta pixel centre",
                "pixel_id_mapping": "integer N maps to source copy TP_L0_{N:05d}",
                "all_six_layers_identical": True,
                "source": ref(REL_GEO, copy_line_ranges[0]),
            }
        },
        "units_and_shape_convention": {
            "source_length_unit": "cm",
            "derived_length_unit_also_reported": "mm",
            "BRIK_parameters": "half-lengths along local x, y, z",
            "supporting_internal_comment": ref(REL_GEO, [14083, 14084]),
        },
        "instrument_frame": {
            "position_global_cm": frame_position,
            "rotation_card_deg_xyz": frame_rotation,
            "rotation_interpretation": "right-handed active R_y(+45 deg), local to global",
            "local_to_global_rotation_matrix": [
                [clean(value) for value in row] for row in rotation_matrix
            ],
            "local_to_global_equations": {
                "X": "cos(45deg)*x' + sin(45deg)*z'",
                "Y": "y'",
                "Z": "-sin(45deg)*x' + cos(45deg)*z'",
            },
            "global_to_local_equations": {
                "x_prime": "cos(45deg)*X - sin(45deg)*Z",
                "y_prime": "Y",
                "z_prime": "sin(45deg)*X + cos(45deg)*Z",
            },
            "local_axis_contract": "x' is optical axis; signal travels from negative x' to positive x'",
            "source": ref(REL_GEO, [frame_position_line, frame_rotation_line, 2466]),
        },
        "six_layer_proxy": {
            "layer_count": 6,
            "layer_pitch_xprime_cm": clean(layer_pitches[0]),
            "layer_pitch_xprime_mm": clean(layer_pitches[0] * 10.0),
            "layers": layer_records,
            "ta_pixel": {
                "material": "Ta",
                "full_dimensions_cm_xyz": pixel_full_cm,
                "full_dimensions_mm_xyz": [clean(value * 10.0) for value in pixel_full_cm],
                "shape_source": ref(REL_GEO, ta_pixel_shape_lines),
                "note": "This is the transport Ta absorber/pixel proxy, not an explicit TES film geometry.",
            },
            "silicon_substrate": {
                "material": "Silicon",
                "full_dimensions_cm_xyz": substrate_full_cm,
                "full_dimensions_mm_xyz": [clean(value * 10.0) for value in substrate_full_cm],
                "shape_source": ref(REL_GEO, si_shape_lines),
                "diagnostic_sd_sources": si_sd_refs,
                "diagnostic_sd_role": "energy-deposition scorer only; not a TES or Si-to-TES coupling model",
                "role_comment_source": ref(REL_SI_DET, [1, 2, 3]),
            },
            "ta_to_si_relation": {
                "si_is_downstream_in_positive_xprime": True,
                "center_offset_cm": 0.18,
                "center_offset_mm": 1.8,
                "face_gap_cm": 0.015,
                "face_gap_mm": 0.15,
                "medium_in_geo_gap": "Vacuum (both are separate daughters of InstrumentFrame)",
                "contact_in_proxy": False,
                "consequence": "Literal proxy geometry provides no direct Ta-Si phonon interface.",
            },
        },
        "ta_pixel_array": {
            "copies_per_layer": len(reference_grid),
            "copies_all_six_layers": len(reference_grid) * 6,
            "all_six_layouts_identical": True,
            "explicit_center_pitch_cm_yz": [clean(y_step), clean(z_step)],
            "explicit_center_pitch_mm_yz": [clean(y_step * 10.0), clean(z_step * 10.0)],
            "detector_map_structural_pitch_cm": detector_pitches[0],
            "detector_map_pitch_sources": ref(REL_DET, pitch_lines),
            "nominal_interpixel_edge_gap_cm_yz": [clean(inplane_edge_gap), clean(inplane_edge_gap)],
            "nominal_interpixel_edge_gap_mm_yz": [clean(inplane_edge_gap * 10.0), clean(inplane_edge_gap * 10.0)],
            "layout_description": "integer 0.155-cm square lattice inside radius 11 pitches, with the (+1.705, 0) cm site omitted",
            "full_disk_site_count": len(disk_sites),
            "missing_site_cm_yz": [list(value) for value in missing_disk_sites],
            "row_counts_by_y_cm": [
                {"y_cm": clean(y, 3), "count": row_counts[y]} for y in sorted(row_counts)
            ],
            "center_coordinate_extrema_cm_yz": {
                "y": [clean(min(y for y, _ in yz_centres)), clean(max(y for y, _ in yz_centres))],
                "z": [clean(min(z for _, z in yz_centres)), clean(max(z for _, z in yz_centres))],
            },
            "projected_footprint_axis_extrema_cm": {
                axis: [clean(value) for value in extrema]
                for axis, extrema in footprint_extrema.items()
            },
            "substrate_side_margins_cm": {
                side: clean(value) for side, value in substrate_side_margins.items()
            },
            "minimum_axis_margin_to_si_edge_cm": clean(substrate_axis_margin),
            "minimum_axis_margin_to_si_edge_mm": clean(substrate_axis_margin * 10.0),
            "one_pixel_projected_area_cm2": clean(projected_pixel_area_cm2),
            "all_ta_projected_area_per_layer_cm2": clean(projected_ta_area_cm2),
            "si_face_area_cm2": clean(substrate_face_area_cm2),
            "ta_absorber_projected_coverage_fraction_of_si": clean(coverage_fraction),
            "ta_absorber_projected_coverage_percent_of_si": clean(coverage_fraction * 100.0),
            "true_tes_collection_interface_coverage_fraction": None,
            "coverage_warning": "65.2778% is Ta absorber footprint coverage only; real TES/collector coverage is absent and unknown.",
            "placement_source_ranges": [
                ref(REL_GEO, copy_line_ranges[layer]) for layer in range(6)
            ],
        },
        "copper_support_and_heat_sink": {
            "five_four_panel_open_supports": open_supports,
            "open_support_summary": {
                "coordinate_mapping": "support indices L1..L5 lie immediately after Si layers L0..L4 in +x'",
                "panel_full_dimensions_cm": {
                    "ZP_or_ZM": [0.3, 3.46, 0.35],
                    "YP_or_YM": [0.3, 0.35, 3.46],
                },
                "si_contact": False,
                "reason": "Each panel is separated both axially (0.05 mm) and in-plane (0.5 mm).",
                "source": ref(REL_GEO, sorted(support_shape_lines + support_position_lines)),
            },
            "coordinate_nearest_final_heat_sink": {
                "name_as_written": "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm",
                "coordinate_adjacent_substrate_layer": 5,
                "material": "Copper",
                "outer_full_dimensions_cm_xyz": [clean(2.0 * value) for value in outer_half],
                "through_cut_full_dimensions_cm_xyz": [clean(2.0 * value) for value in cut_half],
                "position_local_cm": heat_position,
                "axial_clearance_from_L5_Si_cm": clean(heat_axial_clearance),
                "axial_clearance_from_L5_Si_mm": clean(heat_axial_clearance * 10.0),
                "projected_overlap_with_L5_Si_cm2": clean(heat_projected_overlap_cm2),
                "projected_overlap_fraction_of_L5_Si": clean(heat_projected_overlap_cm2 / substrate_face_area_cm2),
                "contact_with_si": False,
                "reason": "Projection overlaps, but a 0.5-mm axial vacuum gap remains.",
                "source": ref(REL_GEO, [14083, 14084, outer_line, cut_line, heat_material_line, heat_position_line]),
            },
            "four_edge_rods": edge_rods,
            "edge_rod_to_final_heat_sink_axial_gap_cm": clean(rod_to_heatsink_gap),
            "edge_rod_to_final_heat_sink_axial_gap_mm": clean(rod_to_heatsink_gap * 10.0),
            "local_copper_completion": {
                "heat_sink_to_interface_stub_surface_contact": True,
                "central_hub_position_local_cm": hub_position,
                "cold_finger_stub_position_local_cm": stub_position,
                "cold_finger_stub_rotation_deg_xyz": stub_rotation,
                "cold_finger_stub_full_length_cm": clean(2.0 * stub_half_length),
                "main_DR_cold_finger_present": False,
                "bath_boundary_condition_defined": False,
                "source": ref(
                    REL_GEO,
                    [14139, hub_shape_line, hub_position_line, stub_shape_line, stub_position_line, stub_rotation_line, 14183],
                ),
            },
            "thermal_authority": "none: these are transport solids; no Si-Cu contact conductance, bath temperature, or surface boundary is assigned",
        },
        "unknown_real_device_geometry": [
            {
                "item": "TES transition-edge film",
                "unknown": ["material stack", "thickness", "footprint", "location on absorber", "channel topology"],
            },
            {
                "item": "SiO2 and SiNx layers represented by the monolithic Silicon proxy",
                "unknown": ["existence/order in this device", "thickness", "lateral extent", "patterning", "interfaces"],
            },
            {
                "item": "Ta absorber to TES and Ta absorber to substrate coupling",
                "unknown": ["mechanical attachment", "phonon collector/fins", "contact area", "interface transmission"],
            },
            {
                "item": "wiring and bonds",
                "unknown": ["materials", "trace dimensions", "routing", "bond pads/wires", "thermal anchoring"],
            },
            {
                "item": "Si to copper support/contact geometry",
                "unknown": ["clamps/pads", "adhesive or indium", "true contact area", "contact pressure", "Kapitza conductance"],
            },
            {
                "item": "Si crystal and surface specification needed by Geant4CMP",
                "unknown": ["crystal orientation", "doping", "surface finish", "coatings", "specularity/absorption"],
            },
        ],
        "absence_audit": {
            "searched_files": searched_relpaths,
            "case_insensitive_exact_token_counts": absence_counts,
            "no_child_volumes_inside_Ta_pixel_copies": True,
            "meaning": "Absence from these files means not represented, not that the real hardware lacks the feature.",
        },
        "snapshot_portability": {
            "setup_absolute_includes": setup_includes,
            "setup_safe_to_execute_as_workspace_only": False,
            "setup_reason": "All setup Includes are absolute paths outside this isolated snapshot.",
            "geo_material_include": {
                "line": material_include_line,
                "target_as_written": material_include,
                "present_in_compact_snapshot": material_present_in_snapshot,
            },
            "full_MEGAlib_geometry_instantiable_from_compact_snapshot_alone": False,
            "recommended_use": "Parse/copy only the audited primitive dimensions into an isolated Geant4CMP unit model; do not run the raw setup.",
        },
        "modeling_decisions": {
            "literal_proxy_contact_model_is_valid": False,
            "minimum_single_layer_solids_with_direct_authority": [
                "36 x 36 x 0.3 mm Silicon slab",
                "376 Ta absorber pixels, each 3.0 x 1.5 x 1.5 mm",
            ],
            "must_be_parameter_envelopes": [
                "replace/bridge the proxy 0.15-mm Ta-Si vacuum gap with hypothesized real interfaces",
                "TES/collector footprint and coupling",
                "Si surface scattering and absorption",
                "Si-to-Cu support contact and bath coupling",
            ],
            "do_not_use_as_real_TES_coverage": "the 65.2778% Ta footprint fraction",
        },
        "self_checks": {
            "passed": True,
            "count": len(checks),
            "checks": checks,
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} checks")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
