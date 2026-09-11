from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .reflectivity_table import ReflectivityTable
from .vector import Vector3, dot, grazing_angle_rad, specular_reflect, unit


@dataclass(frozen=True)
class WallBounce:
    bounce_id: int
    wall: str
    position_mm: Vector3
    normal: Vector3
    grazing_angle_rad: float
    outcome: str
    direction_in: Vector3
    direction_out: Vector3


@dataclass(frozen=True)
class TwoWallResult:
    outcome: str
    position_mm: Vector3
    direction: Vector3
    bounces: Tuple[WallBounce, ...]


def trace_two_wall_channel(
    *,
    position_mm: Vector3,
    direction: Vector3,
    half_gap_mm: float,
    length_mm: float,
    E_keV: float,
    table: ReflectivityTable,
    seed: int = 1,
    max_bounces: int = 100,
) -> TwoWallResult:
    if half_gap_mm <= 0.0 or length_mm <= 0.0:
        raise ValueError("half_gap_mm and length_mm must be positive")
    rng = random.Random(seed)
    pos = tuple(float(x) for x in position_mm)
    k = unit(direction)
    bounces: List[WallBounce] = []

    for bounce_id in range(max_bounces):
        if k[2] <= 0.0:
            return TwoWallResult("BACKWARD", pos, k, tuple(bounces))
        t_exit = (length_mm - pos[2]) / k[2]
        candidates = []
        if k[1] > 0.0:
            candidates.append(((half_gap_mm - pos[1]) / k[1], "TOP", (0.0, -1.0, 0.0)))
        elif k[1] < 0.0:
            candidates.append(((-half_gap_mm - pos[1]) / k[1], "BOTTOM", (0.0, 1.0, 0.0)))
        positive = [(t, wall, n) for t, wall, n in candidates if t > 1.0e-12]
        if not positive or t_exit <= min(t for t, _, _ in positive):
            exit_pos = (pos[0] + t_exit * k[0], pos[1] + t_exit * k[1], length_mm)
            return TwoWallResult("EXIT", exit_pos, k, tuple(bounces))

        t_hit, wall, normal = min(positive, key=lambda item: item[0])
        hit_pos = (pos[0] + t_hit * k[0], pos[1] + t_hit * k[1], pos[2] + t_hit * k[2])
        theta = grazing_angle_rad(k, normal)
        params = table.lookup(E_keV, theta)
        u = rng.random()
        if u < params.A:
            bounces.append(WallBounce(bounce_id, wall, hit_pos, normal, theta, "ABSORB", k, k))
            return TwoWallResult("ABSORB", hit_pos, k, tuple(bounces))
        if u < params.A + params.R:
            reflected = specular_reflect(k, normal)
            bounces.append(WallBounce(bounce_id, wall, hit_pos, normal, theta, "BOUNCE", k, reflected))
            pos = (
                hit_pos[0] + 1.0e-9 * reflected[0],
                hit_pos[1] + 1.0e-9 * reflected[1],
                hit_pos[2] + 1.0e-9 * reflected[2],
            )
            k = reflected
            continue
        bounces.append(WallBounce(bounce_id, wall, hit_pos, normal, theta, "LEAK", k, k))
        return TwoWallResult("LEAK", hit_pos, k, tuple(bounces))

    return TwoWallResult("MAX_BOUNCE", pos, k, tuple(bounces))

