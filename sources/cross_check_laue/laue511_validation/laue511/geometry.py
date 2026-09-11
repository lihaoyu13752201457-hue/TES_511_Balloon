from __future__ import annotations

import math
from typing import Iterable, Tuple

Vec3 = Tuple[float, float, float]


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(v: Vec3) -> float:
    return math.sqrt(dot(v, v))


def unit(v: Iterable[float]) -> Vec3:
    x, y, z = (float(c) for c in v)
    n = math.sqrt(x * x + y * y + z * z)
    if n == 0.0:
        raise ValueError("zero-length vector")
    return (x / n, y / n, z / n)


def slab_path_length_cm(thickness_mm: float, incoming_dir: Vec3, slab_normal: Vec3) -> float:
    cos_inc = abs(dot(unit(incoming_dir), unit(slab_normal)))
    if cos_inc <= 0.0:
        return math.inf
    return (thickness_mm / 10.0) / cos_inc


def reflect_across_plane(incoming_dir: Vec3, plane_normal: Vec3) -> Vec3:
    k = unit(incoming_dir)
    n = unit(plane_normal)
    scale = 2.0 * dot(k, n)
    return unit((k[0] - scale * n[0], k[1] - scale * n[1], k[2] - scale * n[2]))


def ideal_plane_normal(incoming_dir: Vec3, outgoing_dir: Vec3) -> Vec3:
    kin = unit(incoming_dir)
    kout = unit(outgoing_dir)
    return unit((kin[0] - kout[0], kin[1] - kout[1], kin[2] - kout[2]))


def direction_to_point(start_mm: Vec3, target_mm: Vec3) -> Vec3:
    return unit(
        (
            target_mm[0] - start_mm[0],
            target_mm[1] - start_mm[1],
            target_mm[2] - start_mm[2],
        )
    )


def plane_hit_at_z(start_mm: Vec3, direction: Vec3, z_mm: float) -> Vec3:
    d = unit(direction)
    t = (z_mm - start_mm[2]) / d[2]
    return (start_mm[0] + t * d[0], start_mm[1] + t * d[1], z_mm)
