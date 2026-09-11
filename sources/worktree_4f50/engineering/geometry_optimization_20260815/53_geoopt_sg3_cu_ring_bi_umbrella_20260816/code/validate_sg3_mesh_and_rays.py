#!/usr/bin/env python3
"""Static inherited-mesh clearance and frozen 37,194-ray audit for SG3.

No transport SIM is opened.  The test uses the hash-pinned SE3 native mesh
product and the independent focused 511-keV EventList.  Native geometry and
Geant4 overlap audits remain separate hard gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEO = PACKAGE / "geometry/DEMO2_DR_v3p5_SG3.geo"
INTRO = PACKAGE / "geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
AUDIT = PACKAGE / "audit/sg3_mesh_ray_static_prefilter.json"
MESH = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/"
    "data/se3_geometry_mesh_products.npz"
)
EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/"
    "signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)

EXPECTED = {
    "mesh": (1_467_990, "9ef8c6053146d6e055a5915d38de9a1a3eadc3c12ebaaa0bf7dbdf9c91985cb1"),
    "eventlist": (5_819_305, "a709a6dcbf5eaebda60be7ec419f4c214979d4cb215254134568eccebe27e57e"),
    "geo": (697_331, "f0bb7f993b6804522fb0ad239b629405949ac70d4a6b0476ecd942d73bb887c5"),
    "intro": (500, "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52"),
}

OLD_DISK = "Cu_SubstrateSupport_SolidDisk_L0_deepest"
RING = "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm"
BI = "SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm"

RING_LO = np.asarray((3.245, -2.8, -8.0), dtype=np.float64)
RING_HI = np.asarray((3.595, 2.8, -2.4), dtype=np.float64)
RING_CUT_LO = np.asarray((3.2449, -0.8, -6.0), dtype=np.float64)
RING_CUT_HI = np.asarray((3.5951, 0.8, -4.4), dtype=np.float64)
OLD_DISK_LO = np.asarray((3.245, -2.2, -7.4), dtype=np.float64)
OLD_DISK_HI = np.asarray((3.595, 2.2, -3.0), dtype=np.float64)
BI_LO = np.asarray((-3.8, -2.25, -2.39), dtype=np.float64)
BI_HI = np.asarray((4.0, 2.25, -1.9104), dtype=np.float64)
EPS = 1.0e-7

RAY_DIRECTIONS = np.asarray(
    ((0.913, 0.271, 0.305), (0.217, 0.941, 0.259), (0.333, 0.181, 0.925)),
    dtype=np.float64,
)
RAY_DIRECTIONS /= np.linalg.norm(RAY_DIRECTIONS, axis=1)[:, None]


class ValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path, key: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"missing {key}: {path}")
    result = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
    expected_bytes, expected_sha = EXPECTED[key]
    if result["bytes"] != expected_bytes or result["sha256"] != expected_sha:
        raise ValidationError(f"{key} hash/size drift: {result}")
    return result


def candidate_membership(points: np.ndarray) -> dict[str, np.ndarray]:
    inside_ring_outer = np.all((points > RING_LO + EPS) & (points < RING_HI - EPS), axis=1)
    inside_ring_cut = np.all(
        (points > RING_CUT_LO + EPS) & (points < RING_CUT_HI - EPS), axis=1
    )
    inside_bi = np.all((points > BI_LO + EPS) & (points < BI_HI - EPS), axis=1)
    return {"ring": inside_ring_outer & ~inside_ring_cut, "bi": inside_bi}


def ray_parity(point: np.ndarray, triangles: np.ndarray, direction: np.ndarray) -> int:
    vertex0 = triangles[:, 0]
    edge1 = triangles[:, 1] - vertex0
    edge2 = triangles[:, 2] - vertex0
    repeated = np.broadcast_to(direction, edge2.shape)
    h = np.cross(repeated, edge2)
    determinant = np.einsum("ij,ij->i", edge1, h)
    valid = np.abs(determinant) > 1.0e-11
    inverse = np.zeros_like(determinant)
    inverse[valid] = 1.0 / determinant[valid]
    displacement = point - vertex0
    u = inverse * np.einsum("ij,ij->i", displacement, h)
    q = np.cross(displacement, edge1)
    v = inverse * np.einsum("j,ij->i", direction, q)
    distance = inverse * np.einsum("ij,ij->i", edge2, q)
    hits = np.sort(
        distance[
            valid
            & (u > 1.0e-10)
            & (v > 1.0e-10)
            & (u + v < 1.0 - 1.0e-10)
            & (distance > 1.0e-10)
        ]
    )
    if len(hits) == 0:
        return 0
    unique = [float(hits[0])]
    for value in hits[1:]:
        if abs(float(value) - unique[-1]) > 1.0e-8:
            unique.append(float(value))
    return len(unique) % 2


def load_mesh() -> dict[str, np.ndarray]:
    keys = (
        "vertices_instrument_cm",
        "triangles",
        "triangle_solid_ids",
        "solid_names",
        "materials",
        "is_nonvacuum",
        "instrument_bounds_per_solid_cm",
        "instrument_from_world_rotation",
    )
    with np.load(MESH, allow_pickle=False) as archive:
        data = {key: np.asarray(archive[key]) for key in keys}
    if data["vertices_instrument_cm"].shape != (75_527, 3):
        raise ValidationError("mesh vertex closure failed")
    if data["triangles"].shape != (138_018, 3):
        raise ValidationError("mesh triangle closure failed")
    if data["solid_names"].shape != (3_334,):
        raise ValidationError("mesh solid closure failed")
    return data


def internal_probes() -> tuple[np.ndarray, dict[str, int]]:
    bi_axes = [
        np.linspace(BI_LO[i] + 0.02, BI_HI[i] - 0.02, count)
        for i, count in enumerate((9, 7, 5))
    ]
    bi = np.asarray(
        [[x, y, z] for x in bi_axes[0] for y in bi_axes[1] for z in bi_axes[2]],
        dtype=np.float64,
    )
    ring: list[list[float]] = []
    for x in np.linspace(RING_LO[0] + 0.02, RING_HI[0] - 0.02, 3):
        for y in np.linspace(RING_LO[1] + 0.02, RING_HI[1] - 0.02, 15):
            for z in np.linspace(RING_LO[2] + 0.02, RING_HI[2] - 0.02, 15):
                point = np.asarray([[x, y, z]])
                if candidate_membership(point)["ring"][0]:
                    ring.append([x, y, z])
    result = np.vstack((bi, np.asarray(ring, dtype=np.float64)))
    masks = candidate_membership(result)
    if not np.all(masks["bi"] | masks["ring"]):
        raise ValidationError("internal probe generation failed")
    return result, {"bi": len(bi), "ring": len(ring)}


def mesh_clearance(mesh: dict[str, np.ndarray]) -> dict[str, Any]:
    vertices = mesh["vertices_instrument_cm"]
    triangle_indices = mesh["triangles"]
    triangle_solid_ids = mesh["triangle_solid_ids"]
    solid_names = mesh["solid_names"]
    is_nonvacuum = mesh["is_nonvacuum"]
    bounds = mesh["instrument_bounds_per_solid_cm"]

    old_matches = np.flatnonzero(solid_names == OLD_DISK)
    if len(old_matches) != 1:
        raise ValidationError("old L0 disk is not unique in inherited mesh")
    old_id = int(old_matches[0])
    keep_triangles = is_nonvacuum[triangle_solid_ids] & (triangle_solid_ids != old_id)
    tri = vertices[triangle_indices[keep_triangles]]
    surface_samples = np.concatenate(
        (
            tri[:, 0], tri[:, 1], tri[:, 2],
            0.5 * (tri[:, 0] + tri[:, 1]),
            0.5 * (tri[:, 1] + tri[:, 2]),
            0.5 * (tri[:, 2] + tri[:, 0]),
            np.mean(tri, axis=1),
        ),
        axis=0,
    )
    surface_masks = candidate_membership(surface_samples)
    surface_counts = {key: int(np.count_nonzero(value)) for key, value in surface_masks.items()}
    if any(surface_counts.values()):
        raise ValidationError(f"inherited surface samples enter SG3 candidate: {surface_counts}")

    probes, probe_counts = internal_probes()
    candidate_ids: list[int] = []
    union_lo = np.minimum(RING_LO, BI_LO)
    union_hi = np.maximum(RING_HI, BI_HI)
    for index, name in enumerate(solid_names):
        if not is_nonvacuum[index] or index == old_id:
            continue
        lo, hi = bounds[index]
        if np.all(hi > union_lo) and np.all(lo < union_hi):
            candidate_ids.append(index)

    inside_pairs: list[dict[str, Any]] = []
    point_solid_pairs = 0
    for point_id, point in enumerate(probes):
        for solid_id in candidate_ids:
            lo, hi = bounds[solid_id]
            if not np.all((point > lo + EPS) & (point < hi - EPS)):
                continue
            point_solid_pairs += 1
            triangles = vertices[triangle_indices[triangle_solid_ids == solid_id]]
            votes = [ray_parity(point, triangles, direction) for direction in RAY_DIRECTIONS]
            if sum(votes) >= 2:
                inside_pairs.append(
                    {
                        "probe": point_id,
                        "point_cm": point.tolist(),
                        "solid": str(solid_names[solid_id]),
                        "votes": votes,
                    }
                )
                if len(inside_pairs) >= 25:
                    break
        if len(inside_pairs) >= 25:
            break
    if inside_pairs:
        raise ValidationError(f"SG3 internal probes enter inherited solids: {inside_pairs}")

    return {
        "inherited_old_disk_excluded_solid_id": old_id,
        "surface_sampling": {
            "samples": int(len(surface_samples)),
            "inside_candidate": surface_counts,
        },
        "internal_probe_sampling": {
            "counts": probe_counts,
            "total": int(len(probes)),
            "aabb_candidate_solids": [str(solid_names[index]) for index in candidate_ids],
            "point_solid_pairs_tested": point_solid_pairs,
            "inside_pairs": 0,
        },
    }


def ray_box_chord(points: np.ndarray, directions: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        t0 = (lo - points) / directions
        t1 = (hi - points) / directions
    parallel = np.abs(directions) < 1.0e-15
    outside_parallel = parallel & ((points < lo) | (points > hi))
    near = np.where(parallel, -np.inf, np.minimum(t0, t1))
    far = np.where(parallel, np.inf, np.maximum(t0, t1))
    enter = np.max(near, axis=1)
    leave = np.min(far, axis=1)
    leave = np.where(np.any(outside_parallel, axis=1), -np.inf, leave)
    return np.maximum(0.0, leave - np.maximum(enter, 0.0))


def focused_rays(mesh: dict[str, np.ndarray]) -> dict[str, Any]:
    eventlist = np.loadtxt(EVENTLIST, dtype=np.float64)
    if eventlist.shape != (37_194, 15):
        raise ValidationError(f"frozen EventList shape drift: {eventlist.shape}")
    rotation = mesh["instrument_from_world_rotation"]
    points = eventlist[:, 5:8] @ rotation.T
    directions = eventlist[:, 8:11] @ rotation.T
    norms = np.linalg.norm(directions, axis=1)
    if not np.allclose(norms, 1.0, atol=1.0e-8, rtol=0.0):
        raise ValidationError("ray direction normalization drift")

    bi_chord = ray_box_chord(points, directions, BI_LO, BI_HI)
    if np.count_nonzero(bi_chord > 1.0e-10):
        raise ValidationError("a focused ray intersects the Bi umbrella")
    outer_chord = ray_box_chord(points, directions, RING_LO, RING_HI)
    cut_chord = ray_box_chord(points, directions, RING_CUT_LO, RING_CUT_HI)
    ring_chord = np.maximum(0.0, outer_chord - cut_chord)
    old_chord = ray_box_chord(points, directions, OLD_DISK_LO, OLD_DISK_HI)
    delta = ring_chord - old_chord
    if np.any(delta > 1.0e-8):
        raise ValidationError("analytical Cu ring adds focused-ray Cu chord")

    def z_at_x(x: float) -> np.ndarray:
        distance = (x - points[:, 0]) / directions[:, 0]
        return points[:, 2] + distance * directions[:, 2]

    maximum_ray_z = np.maximum(z_at_x(BI_LO[0]), z_at_x(BI_HI[0]))
    vertical_clearance = BI_LO[2] - maximum_ray_z
    return {
        "rows": int(len(eventlist)),
        "bi_umbrella": {
            "zero_chord_rays": int(np.count_nonzero(bi_chord <= 1.0e-10)),
            "nonzero_chord_rays": int(np.count_nonzero(bi_chord > 1.0e-10)),
            "minimum_vertical_clearance_cm": float(np.min(vertical_clearance)),
            "minimum_clearance_ray_id": int(np.argmin(vertical_clearance)),
        },
        "l0_cu_replacement": {
            "old_disk_nonzero_chord_rays": int(np.count_nonzero(old_chord > 1.0e-10)),
            "new_ring_nonzero_chord_rays": int(np.count_nonzero(ring_chord > 1.0e-10)),
            "rays_with_reduced_Cu_chord": int(np.count_nonzero(delta < -1.0e-8)),
            "rays_with_added_Cu_chord": int(np.count_nonzero(delta > 1.0e-8)),
            "minimum_sg3_minus_sf3_Cu_chord_cm": float(np.min(delta)),
        },
    }


def publish(payload: dict[str, Any], check: bool) -> str:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if check:
        if not AUDIT.is_file() or AUDIT.read_bytes() != data:
            raise ValidationError("existing audit differs from reproducible result")
        return "CHECKED_IDENTICAL"
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    if AUDIT.exists():
        if AUDIT.read_bytes() == data:
            return "EXISTING_IDENTICAL"
        raise ValidationError("write-once audit exists with different bytes")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=AUDIT.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, AUDIT)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return "CREATED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        inputs = {
            "mesh": record(MESH, "mesh"),
            "eventlist": record(EVENTLIST, "eventlist"),
            "geo": record(GEO, "geo"),
            "intro": record(INTRO, "intro"),
        }
        text = GEO.read_text(encoding="utf-8")
        for exact in (
            f"{RING}.Shape {RING}_Shape",
            f"{RING}.Position 3.42 0 -5.2",
            f"{BI}.Shape BRIK 3.9 2.25 0.2398",
            f"{BI}.Position 0.1 0 -2.1502",
        ):
            if text.count(exact) != 1:
                raise ValidationError(f"geometry contract line drift: {exact}")
        mesh = load_mesh()
        payload = {
            "status": "PASS__SG3_STATIC_MESH_AND_37194_RAY_PREFILTER",
            "authority": "STATIC_PREFILTER_ONLY__NOT_NATIVE_GEOMETRY_AUTHORITY",
            "model_identity": "SG3",
            "parent_identity": "SF3",
            "transport_SIM_files_opened": 0,
            "inputs": inputs,
            "mesh_clearance": mesh_clearance(mesh),
            "focused_37194_ray_envelope": focused_rays(mesh),
            "hard_gates_remaining": [
                "Geant4 CheckForOverlaps 10000 0.0001",
                "native SF3/SG3 frozen-bank geometry navigator",
            ],
        }
        publication = publish(payload, args.check)
        print(json.dumps({"status": payload["status"], "publication": publication}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL__SG3_STATIC_PREFILTER", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
