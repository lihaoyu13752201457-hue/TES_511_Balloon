#!/usr/bin/env python3
"""Reproduce the SF3 static mesh and frozen-ray clearance prefilter.

This program deliberately does not open transport SIM files.  It reads only
the hash-pinned SE3 native mesh product, the frozen 37,194-ray signal
EventList, and the current additive SF3 geometry text.  Its result is a
static prefilter: native geometry navigation and Geant4 overlap checking stay
mandatory hard gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]

MESH = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/"
    "data/se3_geometry_mesh_products.npz"
)
EVENTLIST = (
    REPO
    / "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/"
    "config/signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)
SF3_GEO = PACKAGE / "geometry/DEMO2_DR_v3p5_SF3.geo"
SF3_INTRO = (
    PACKAGE
    / "geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
)
AUDIT = PACKAGE / "audit/sf3_mesh_clearance_prefilter.json"

EXPECTED_INPUTS = {
    "mesh": {
        "bytes": 1_467_990,
        "sha256": "9ef8c6053146d6e055a5915d38de9a1a3eadc3c12ebaaa0bf7dbdf9c91985cb1",
    },
    "eventlist": {
        "bytes": 5_819_305,
        "sha256": "a709a6dcbf5eaebda60be7ec419f4c214979d4cb215254134568eccebe27e57e",
    },
    "sf3_geo": {
        "bytes": 697_978,
        "sha256": "7d2a5ee19d118d8ecb2c095203d7a8c6046e3c0e0020a67ba63d77ba399d8b16",
    },
    "sf3_intro": {
        "bytes": 500,
        "sha256": "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    },
}

# All dimensions are centimetres in the unrotated InstrumentFrame.  The
# volume-local PCON z coordinate becomes instrument x-prime after Rotation
# 0 90 0.  InstrumentFrame itself supplies the one world Rotation 0 45 0.
SIDE_X0 = -4.3575
SIDE_X1 = 4.305
SIDE_RIN = 4.205
SIDE_ROUT = 4.495
FRONT_X0 = -4.6475
FRONT_X1 = -4.3575
REAR_X0 = 4.305
REAR_X1 = 4.595
REAR_RIN = 1.85
CAP_ROUT = 4.495
WINDOW_HALF = 1.9
CENTER_Z = -5.2
BOUNDARY_EPS_CM = 1.0e-7

RAY_DIRECTIONS = np.asarray(
    ((0.913, 0.271, 0.305), (0.217, 0.941, 0.259), (0.333, 0.181, 0.925)),
    dtype=np.float64,
)
RAY_DIRECTIONS /= np.linalg.norm(RAY_DIRECTIONS, axis=1)[:, None]

POSITIVE_CONTROLS = (
    ("SE3_Al_Shield_Inner_Cylinder_2mm", (0.0, 4.1, -5.2)),
    ("SE3_Al_Shield_Inner_Back_ColdFingerCap_2mm", (4.2, 2.5, -5.2)),
    ("Cu_50mK_StillLike_Can_side_wall_below_side_port", (0.0, 15.2, -8.0)),
)


class ValidationError(RuntimeError):
    """Fail-closed prefilter error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def validate_input(path: Path, key: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"missing {key}: {path}")
    record = file_record(path)
    expected = EXPECTED_INPUTS[key]
    if record["bytes"] != expected["bytes"] or record["sha256"] != expected["sha256"]:
        raise ValidationError(
            f"{key} drift: bytes={record['bytes']} sha256={record['sha256']}"
        )
    return record


def validate_sf3_contract(geo_text: str, intro_text: str) -> None:
    exact_lines = (
        "SF3_W_NearField_SideSleeve_2p9mm.Shape PCON 0 360 2 -4.3575 4.205 4.495 4.305 4.205 4.495",
        "SF3_W_NearField_SideSleeve_2p9mm.Position 0 0 -5.2",
        "SF3_W_NearField_SideSleeve_2p9mm.Rotation 0 90 0",
        "SF3_W_NearField_SideSleeve_2p9mm.Mother InstrumentFrame",
        "SF3_W_NearField_FrontWindowPlate_2p9mm_FullDiskShape.Parameters 0 360 2 -4.6475 0 4.495 -4.3575 0 4.495",
        "SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutShape.Parameters 1.9 1.9 0.1451",
        "SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutOrientation.Position 0 0 -4.5025",
        "SF3_W_NearField_FrontWindowPlate_2p9mm.Position 0 0 -5.2",
        "SF3_W_NearField_FrontWindowPlate_2p9mm.Rotation 0 90 0",
        "SF3_W_NearField_FrontWindowPlate_2p9mm.Mother InstrumentFrame",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm.Shape PCON 0 360 2 4.305 1.85 4.495 4.595 1.85 4.495",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm.Position 0 0 -5.2",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm.Rotation 0 90 0",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm.Mother InstrumentFrame",
    )
    for line in exact_lines:
        if geo_text.count(line) != 1:
            raise ValidationError(f"SF3 geometry contract line is not exact-once: {line}")
    volume_lines = [
        line
        for line in geo_text.splitlines()
        if line.startswith("Volume SF3_W_NearField_")
    ]
    if len(volume_lines) != 3:
        raise ValidationError(f"expected exactly three SF3 W physical volumes, got {volume_lines}")
    for volume in (
        "SF3_W_NearField_SideSleeve_2p9mm",
        "SF3_W_NearField_FrontWindowPlate_2p9mm",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
    ):
        if geo_text.count(f"{volume}.Material W") != 1:
            raise ValidationError(f"passive W material contract drift: {volume}")
    if intro_text.count("InstrumentFrame.Rotation 0 45 0") != 1:
        raise ValidationError("InstrumentFrame Rotation 0 45 0 is not exact-once")


def candidate_membership(points: np.ndarray) -> dict[str, np.ndarray]:
    """Return eroded-open-interior membership masks for the three W pieces."""
    x = points[:, 0]
    y = points[:, 1]
    z_from_center = points[:, 2] - CENTER_Z
    radius = np.hypot(y, z_from_center)
    eps = BOUNDARY_EPS_CM
    side = (
        (x > SIDE_X0 + eps)
        & (x < SIDE_X1 - eps)
        & (radius > SIDE_RIN + eps)
        & (radius < SIDE_ROUT - eps)
    )
    rear = (
        (x > REAR_X0 + eps)
        & (x < REAR_X1 - eps)
        & (radius > REAR_RIN + eps)
        & (radius < CAP_ROUT - eps)
    )
    outside_square_cut = (np.abs(y) > WINDOW_HALF + eps) | (
        np.abs(z_from_center) > WINDOW_HALF + eps
    )
    front = (
        (x > FRONT_X0 + eps)
        & (x < FRONT_X1 - eps)
        & (radius < CAP_ROUT - eps)
        & outside_square_cut
    )
    return {"side": side, "front": front, "rear": rear}


def build_candidate_internal_probes() -> tuple[np.ndarray, dict[str, int]]:
    side: list[list[float]] = []
    for x in (-4.2, -3.0, 0.0, 3.0, 4.2):
        for radius in (4.22, 4.35, 4.48):
            for angle in np.linspace(0.031, 2.0 * math.pi + 0.031, 64, endpoint=False):
                side.append(
                    [x, radius * math.cos(angle), CENTER_Z + radius * math.sin(angle)]
                )

    rear: list[list[float]] = []
    for x in (4.32, 4.45, 4.58):
        for radius in (1.9, 2.5, 3.5, 4.48):
            for angle in np.linspace(0.019, 2.0 * math.pi + 0.019, 64, endpoint=False):
                rear.append(
                    [x, radius * math.cos(angle), CENTER_Z + radius * math.sin(angle)]
                )

    front: list[list[float]] = []
    for x in (-4.62, -4.50, -4.38):
        for y in np.linspace(-4.4, 4.4, 25):
            for z_from_center in np.linspace(-4.4, 4.4, 25):
                if (
                    y * y + z_from_center * z_from_center < 4.48**2
                    and not (abs(y) < 1.91 and abs(z_from_center) < 1.91)
                ):
                    front.append([x, y, CENTER_Z + z_from_center])

    probes = np.asarray(side + front + rear, dtype=np.float64)
    masks = candidate_membership(probes)
    if not np.all(masks["side"] | masks["front"] | masks["rear"]):
        raise ValidationError("an internal probe is not strictly inside the SF3 W contract")
    if np.any(
        masks["side"].astype(np.int8)
        + masks["front"].astype(np.int8)
        + masks["rear"].astype(np.int8)
        != 1
    ):
        raise ValidationError("candidate internal probe pieces are not disjoint")
    counts = {"side": len(side), "front": len(front), "rear": len(rear)}
    return probes, counts


def ray_parity(point: np.ndarray, triangles: np.ndarray, direction: np.ndarray) -> int:
    """Odd/even Moller-Trumbore point-in-closed-mesh test for one ray."""
    vertex0 = triangles[:, 0]
    edge1 = triangles[:, 1] - vertex0
    edge2 = triangles[:, 2] - vertex0
    repeated_direction = np.broadcast_to(direction, edge2.shape)
    h = np.cross(repeated_direction, edge2)
    determinant = np.einsum("ij,ij->i", edge1, h)
    valid = np.abs(determinant) > 1.0e-11
    inverse = np.zeros_like(determinant)
    inverse[valid] = 1.0 / determinant[valid]
    displacement = point - vertex0
    u = inverse * np.einsum("ij,ij->i", displacement, h)
    q = np.cross(displacement, edge1)
    v = inverse * np.einsum("j,ij->i", direction, q)
    distance = inverse * np.einsum("ij,ij->i", edge2, q)
    intersections = np.sort(
        distance[
            valid
            & (u > 1.0e-10)
            & (v > 1.0e-10)
            & (u + v < 1.0 - 1.0e-10)
            & (distance > 1.0e-9)
        ]
    )
    if len(intersections) == 0:
        return 0
    unique = np.concatenate(
        (np.asarray((True,), dtype=bool), np.diff(intersections) > 1.0e-8)
    )
    return int(int(np.count_nonzero(unique)) % 2)


def mesh_prefilter(mesh_data: dict[str, np.ndarray]) -> dict[str, Any]:
    vertices = mesh_data["vertices_instrument_cm"]
    triangle_indices = mesh_data["triangles"]
    triangle_solid_ids = mesh_data["triangle_solid_ids"]
    solid_names = mesh_data["solid_names"]
    solid_bounds = mesh_data["instrument_bounds_per_solid_cm"]
    nonvacuum = mesh_data["is_nonvacuum"]

    triangles = vertices[triangle_indices]
    surface_samples = np.concatenate(
        (
            triangles.reshape(-1, 3),
            (triangles[:, 0] + triangles[:, 1]) / 2.0,
            (triangles[:, 1] + triangles[:, 2]) / 2.0,
            (triangles[:, 2] + triangles[:, 0]) / 2.0,
            triangles.mean(axis=1),
        ),
        axis=0,
    )
    surface_sample_solid_ids = np.concatenate(
        (
            np.repeat(triangle_solid_ids, 3),
            triangle_solid_ids,
            triangle_solid_ids,
            triangle_solid_ids,
            triangle_solid_ids,
        )
    )
    surface_masks = candidate_membership(surface_samples)
    surface_results: dict[str, Any] = {}
    any_surface = np.zeros(len(surface_samples), dtype=bool)
    for piece, mask in surface_masks.items():
        any_surface |= mask
        hit_ids = np.unique(surface_sample_solid_ids[mask])
        surface_results[piece] = {
            "samples_inside_candidate_piece": int(np.count_nonzero(mask)),
            "existing_solid_names": [str(solid_names[index]) for index in hit_ids],
        }
    any_hit_ids = np.unique(surface_sample_solid_ids[any_surface])
    surface_results["any"] = {
        "samples_inside_candidate": int(np.count_nonzero(any_surface)),
        "existing_solid_names": [str(solid_names[index]) for index in any_hit_ids],
    }

    probes, probe_piece_counts = build_candidate_internal_probes()
    aabb_contains_probe = np.any(
        np.all(
            (probes[None, :, :] >= solid_bounds[:, 0, None, :])
            & (probes[None, :, :] <= solid_bounds[:, 1, None, :]),
            axis=2,
        ),
        axis=1,
    ) & nonvacuum
    candidate_solid_ids = np.flatnonzero(aabb_contains_probe)
    inside_probe_ids: set[int] = set()
    inside_solid_pairs: list[dict[str, Any]] = []
    aabb_point_solid_pairs = 0
    for solid_id in candidate_solid_ids:
        probe_ids = np.flatnonzero(
            np.all(
                (probes >= solid_bounds[solid_id, 0])
                & (probes <= solid_bounds[solid_id, 1]),
                axis=1,
            )
        )
        aabb_point_solid_pairs += len(probe_ids)
        solid_triangles = vertices[triangle_indices[triangle_solid_ids == solid_id]]
        local_inside: list[int] = []
        for probe_id in probe_ids:
            votes = sum(
                ray_parity(probes[probe_id], solid_triangles, direction)
                for direction in RAY_DIRECTIONS
            )
            if votes >= 2:
                local_inside.append(int(probe_id))
                inside_probe_ids.add(int(probe_id))
        if local_inside:
            inside_solid_pairs.append(
                {
                    "solid_id": int(solid_id),
                    "solid_name": str(solid_names[solid_id]),
                    "inside_probe_count": len(local_inside),
                    "probe_ids": local_inside,
                }
            )

    positive_results: list[dict[str, Any]] = []
    for solid_name, point_values in POSITIVE_CONTROLS:
        matches = np.flatnonzero(solid_names == solid_name)
        if len(matches) != 1:
            raise ValidationError(f"positive-control solid is not unique: {solid_name}")
        solid_id = int(matches[0])
        solid_triangles = vertices[triangle_indices[triangle_solid_ids == solid_id]]
        point = np.asarray(point_values, dtype=np.float64)
        votes = [
            ray_parity(point, solid_triangles, direction)
            for direction in RAY_DIRECTIONS
        ]
        if votes != [1, 1, 1]:
            raise ValidationError(
                f"mesh point-in-solid positive control failed: {solid_name}: {votes}"
            )
        positive_results.append(
            {
                "solid_id": solid_id,
                "solid_name": solid_name,
                "instrument_point_cm": list(point_values),
                "inside_votes": votes,
                "pass": True,
            }
        )

    if surface_results["any"]["samples_inside_candidate"] != 0:
        raise ValidationError("existing mesh surface samples enter the SF3 W interior")
    if inside_probe_ids:
        raise ValidationError("SF3 W internal probes enter an existing mesh solid")

    return {
        "mesh_counts": {
            "solids": int(len(solid_names)),
            "vertices": int(len(vertices)),
            "triangles": int(len(triangle_indices)),
        },
        "existing_surface_sampling": {
            "algorithm": "per triangle: 3 vertices + 3 edge midpoints + centroid",
            "boundary_policy": "candidate W open interior eroded by 1e-7 cm",
            "samples_per_triangle": 7,
            "total_samples": int(len(surface_samples)),
            "results": surface_results,
        },
        "candidate_internal_probe_sampling": {
            "algorithm": (
                "deterministic side/rear polar probes plus front Cartesian grid; "
                "AABB broad phase then 3-direction odd/even Moller-Trumbore ray parity"
            ),
            "probe_piece_counts": probe_piece_counts,
            "total_probes": int(len(probes)),
            "aabb_candidate_solid_count": int(len(candidate_solid_ids)),
            "aabb_candidate_solid_names": [
                str(solid_names[index]) for index in candidate_solid_ids
            ],
            "aabb_point_solid_pairs_tested": int(aabb_point_solid_pairs),
            "ray_directions": RAY_DIRECTIONS.tolist(),
            "majority_vote_threshold": 2,
            "probes_inside_any_existing_solid": len(inside_probe_ids),
            "inside_solid_pairs": inside_solid_pairs,
        },
        "point_in_solid_positive_controls": positive_results,
    }


def focused_ray_clearance(
    eventlist: np.ndarray, instrument_from_world: np.ndarray
) -> dict[str, Any]:
    if eventlist.shape != (37_194, 15):
        raise ValidationError(f"frozen EventList shape drift: {eventlist.shape}")
    positions_world = eventlist[:, 5:8]
    directions_world = eventlist[:, 8:11]
    positions = positions_world @ instrument_from_world.T
    directions = directions_world @ instrument_from_world.T
    if np.any(directions[:, 0] <= 0.0):
        raise ValidationError("a focused ray does not propagate along +x-prime")

    def transverse_at(xprime: float) -> tuple[np.ndarray, np.ndarray]:
        distance = (xprime - positions[:, 0]) / directions[:, 0]
        return (
            positions[:, 1] + distance * directions[:, 1],
            positions[:, 2] + distance * directions[:, 2],
        )

    front_clearance_endpoints = []
    for xprime in (FRONT_X0, FRONT_X1):
        y, z = transverse_at(xprime)
        front_clearance_endpoints.append(
            WINDOW_HALF - np.maximum(np.abs(y), np.abs(z - CENTER_Z))
        )
    front_clearance_endpoints_array = np.asarray(front_clearance_endpoints)
    front_clearance_per_ray = np.min(front_clearance_endpoints_array, axis=0)

    side_radius_endpoints = []
    for xprime in (SIDE_X0, SIDE_X1):
        y, z = transverse_at(xprime)
        side_radius_endpoints.append(np.hypot(y, z - CENTER_Z))
    side_radius_endpoints_array = np.asarray(side_radius_endpoints)
    side_radius_per_ray = np.max(side_radius_endpoints_array, axis=0)

    rear_radius_endpoints = []
    for xprime in (REAR_X0, REAR_X1):
        y, z = transverse_at(xprime)
        rear_radius_endpoints.append(np.hypot(y, z - CENTER_Z))
    rear_radius_endpoints_array = np.asarray(rear_radius_endpoints)
    rear_radius_per_ray = np.max(rear_radius_endpoints_array, axis=0)

    front_hits = front_clearance_per_ray <= 0.0
    side_hits = side_radius_per_ray >= SIDE_RIN
    rear_hits = rear_radius_per_ray >= REAR_RIN
    any_hits = front_hits | side_hits | rear_hits
    if np.any(any_hits):
        raise ValidationError("a frozen focused ray has non-zero analytical new-W chord")

    world_from_instrument = instrument_from_world.T
    sky_facing_axis_world = world_from_instrument @ np.asarray((-1.0, 0.0, 0.0))
    return {
        "rows": int(len(eventlist)),
        "coordinate_transform": "instrument = instrument_from_world_rotation @ world",
        "injection_xprime_cm": {
            "min": float(np.min(positions[:, 0])),
            "max": float(np.max(positions[:, 0])),
        },
        "direction_xprime": {
            "min": float(np.min(directions[:, 0])),
            "max": float(np.max(directions[:, 0])),
        },
        "world_plus_Z_semantics": "sky/up",
        "sky_facing_minus_xprime_axis_world": sky_facing_axis_world.tolist(),
        "focused_photon_propagation": "+xprime (45 degrees downward in world)",
        "front_square_window": {
            "xprime_interval_cm": [FRONT_X0, FRONT_X1],
            "half_width_cm": WINDOW_HALF,
            "minimum_edge_clearance_cm": float(np.min(front_clearance_per_ray)),
            "minimum_edge_clearance_ray_id": int(np.argmin(front_clearance_per_ray)),
            "endpoint_minima_cm": [
                float(np.min(values)) for values in front_clearance_endpoints_array
            ],
            "rays_intersecting_new_W": int(np.count_nonzero(front_hits)),
        },
        "side_sleeve": {
            "xprime_interval_cm": [SIDE_X0, SIDE_X1],
            "inner_radius_cm": SIDE_RIN,
            "maximum_ray_radius_cm": float(np.max(side_radius_per_ray)),
            "minimum_inner_radial_clearance_cm": float(
                SIDE_RIN - np.max(side_radius_per_ray)
            ),
            "maximum_radius_ray_id": int(np.argmax(side_radius_per_ray)),
            "endpoint_maxima_cm": [
                float(np.max(values)) for values in side_radius_endpoints_array
            ],
            "rays_intersecting_new_W": int(np.count_nonzero(side_hits)),
        },
        "rear_service_aperture": {
            "xprime_interval_cm": [REAR_X0, REAR_X1],
            "aperture_radius_cm": REAR_RIN,
            "maximum_ray_radius_cm": float(np.max(rear_radius_per_ray)),
            "minimum_aperture_clearance_cm": float(
                REAR_RIN - np.max(rear_radius_per_ray)
            ),
            "maximum_radius_ray_id": int(np.argmax(rear_radius_per_ray)),
            "endpoint_maxima_cm": [
                float(np.max(values)) for values in rear_radius_endpoints_array
            ],
            "rays_intersecting_new_W": int(np.count_nonzero(rear_hits)),
        },
        "analytical_new_W_chord": {
            "zero_chord_rays": int(len(eventlist) - np.count_nonzero(any_hits)),
            "nonzero_chord_rays": int(np.count_nonzero(any_hits)),
            "reasoning": (
                "transverse ray coordinates are linear in x-prime; absolute square "
                "coordinates and radial norm are convex, so slab endpoint maxima close "
                "the full thickness intervals"
            ),
        },
    }


def load_mesh() -> dict[str, np.ndarray]:
    required = (
        "schema_version",
        "vertices_instrument_cm",
        "triangles",
        "triangle_solid_ids",
        "solid_names",
        "materials",
        "is_nonvacuum",
        "instrument_bounds_per_solid_cm",
        "instrument_rotation_xyz_deg",
        "world_from_instrument_rotation",
        "instrument_from_world_rotation",
    )
    with np.load(MESH, allow_pickle=False) as archive:
        missing = sorted(set(required) - set(archive.files))
        if missing:
            raise ValidationError(f"mesh archive keys missing: {missing}")
        data = {key: np.asarray(archive[key]) for key in required}
    if str(data["schema_version"].item()) != "se3_geometry_mesh_products_v1":
        raise ValidationError("SE3 mesh schema drift")
    if data["vertices_instrument_cm"].shape != (75_527, 3):
        raise ValidationError("SE3 mesh vertex count drift")
    if data["triangles"].shape != (138_018, 3):
        raise ValidationError("SE3 mesh triangle count drift")
    if data["solid_names"].shape != (3_334,):
        raise ValidationError("SE3 mesh solid count drift")
    if not np.allclose(data["instrument_rotation_xyz_deg"], (0.0, 45.0, 0.0)):
        raise ValidationError("mesh InstrumentFrame rotation drift")
    if not np.allclose(
        data["world_from_instrument_rotation"].T,
        data["instrument_from_world_rotation"],
        atol=1.0e-14,
        rtol=0.0,
    ):
        raise ValidationError("mesh coordinate transforms are not inverse rotations")
    return data


def build_report() -> dict[str, Any]:
    inputs = {
        "mesh": validate_input(MESH, "mesh"),
        "eventlist": validate_input(EVENTLIST, "eventlist"),
        "sf3_geo": validate_input(SF3_GEO, "sf3_geo"),
        "sf3_intro": validate_input(SF3_INTRO, "sf3_intro"),
        "validator_script": file_record(SCRIPT),
    }
    geo_text = SF3_GEO.read_text(encoding="utf-8")
    intro_text = SF3_INTRO.read_text(encoding="utf-8")
    validate_sf3_contract(geo_text, intro_text)
    mesh_data = load_mesh()
    eventlist = np.loadtxt(EVENTLIST, dtype=np.float64)
    report = {
        "status": "PASS__SF3_MESH_CLEARANCE_STATIC_PREFILTER",
        "authority": "STATIC_PREFILTER_ONLY__NOT_NATIVE_GEOMETRY_AUTHORITY",
        "model_identity": "SF3",
        "parent_identity": "SE3",
        "transport_SIM_files_opened": 0,
        "inputs": inputs,
        "candidate_geometry_contract": {
            "strict_additive_passive_W_pieces": 3,
            "position_in_InstrumentFrame_cm": [0.0, 0.0, CENTER_Z],
            "volume_rotation_deg": [0.0, 90.0, 0.0],
            "InstrumentFrame_rotation_deg": [0.0, 45.0, 0.0],
            "boundary_erosion_for_static_membership_cm": BOUNDARY_EPS_CM,
            "side": {
                "xprime_interval_cm": [SIDE_X0, SIDE_X1],
                "inner_radius_cm": SIDE_RIN,
                "outer_radius_cm": SIDE_ROUT,
            },
            "front": {
                "xprime_interval_cm": [FRONT_X0, FRONT_X1],
                "outer_radius_cm": CAP_ROUT,
                "square_window_half_width_cm": WINDOW_HALF,
            },
            "rear": {
                "xprime_interval_cm": [REAR_X0, REAR_X1],
                "inner_radius_cm": REAR_RIN,
                "outer_radius_cm": CAP_ROUT,
            },
        },
        "mesh_clearance_prefilter": mesh_prefilter(mesh_data),
        "focused_37194_ray_envelope": focused_ray_clearance(
            eventlist, mesh_data["instrument_from_world_rotation"]
        ),
        "hard_gates_remaining": [
            {
                "gate": "Geant4 CheckForOverlaps",
                "required_sampling": 10_000,
                "required_tolerance_cm": 0.0001,
                "status": "REQUIRED_NOT_SATISFIED_BY_THIS_STATIC_PREFILTER",
            },
            {
                "gate": "native paired geometry navigator on the identical 37194-ray bank",
                "required_result": (
                    "zero added-W chord for every ray and unchanged inherited material chords"
                ),
                "status": "REQUIRED_NOT_SATISFIED_BY_THIS_STATIC_PREFILTER",
            },
        ],
    }
    return report


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def write_once(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == data:
            return "EXISTING_IDENTICAL"
        raise ValidationError(f"write-once audit exists with different bytes: {path}")
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
    except FileExistsError as exc:
        raise ValidationError(f"write-once audit raced with another writer: {path}") from exc
    return "CREATED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="publish the write-once audit")
    mode.add_argument("--check", action="store_true", help="recompute and compare existing audit")
    args = parser.parse_args()
    try:
        report = build_report()
        data = report_bytes(report)
        if args.write:
            publication = write_once(AUDIT, data)
        else:
            if not AUDIT.is_file():
                raise ValidationError(f"missing write-once audit: {AUDIT}")
            if AUDIT.read_bytes() != data:
                raise ValidationError("existing audit differs from reproducible calculation")
            publication = "CHECKED_IDENTICAL"
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "audit": str(AUDIT),
                    "publication": publication,
                    "surface_samples": report["mesh_clearance_prefilter"]
                    ["existing_surface_sampling"]["total_samples"],
                    "internal_probes": report["mesh_clearance_prefilter"]
                    ["candidate_internal_probe_sampling"]["total_probes"],
                    "focused_rays": report["focused_37194_ray_envelope"]["rows"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL__SF3_MESH_CLEARANCE_STATIC_PREFILTER",
                    "error": str(exc),
                    "transport_SIM_files_opened": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
