from __future__ import annotations

import math
from typing import Iterable, Tuple

Vector3 = Tuple[float, float, float]


def dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(v: Vector3) -> float:
    return math.sqrt(dot(v, v))


def unit(v: Iterable[float]) -> Vector3:
    values = tuple(float(x) for x in v)
    if len(values) != 3:
        raise ValueError("expected a 3-vector")
    n = norm(values)  # type: ignore[arg-type]
    if n == 0.0:
        raise ValueError("zero-length vector")
    return (values[0] / n, values[1] / n, values[2] / n)


def add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(s: float, v: Vector3) -> Vector3:
    return (s * v[0], s * v[1], s * v[2])


def specular_reflect(direction: Vector3, normal: Vector3) -> Vector3:
    k = unit(direction)
    n = unit(normal)
    return unit(sub(k, mul(2.0 * dot(k, n), n)))


def grazing_angle_rad(direction: Vector3, normal: Vector3) -> float:
    k = unit(direction)
    n = unit(normal)
    cos_alpha = abs(dot(k, n))
    cos_alpha = min(1.0, max(0.0, cos_alpha))
    return math.asin(cos_alpha)


def rotate_small_angle(direction: Vector3, dx_rad: float, dy_rad: float) -> Vector3:
    """Apply a small-angle perturbation in the local transverse basis."""
    k = unit(direction)
    if abs(k[2]) < 0.9:
        ref = (0.0, 0.0, 1.0)
    else:
        ref = (1.0, 0.0, 0.0)
    e1 = unit(
        (
            k[1] * ref[2] - k[2] * ref[1],
            k[2] * ref[0] - k[0] * ref[2],
            k[0] * ref[1] - k[1] * ref[0],
        )
    )
    e2 = unit(
        (
            k[1] * e1[2] - k[2] * e1[1],
            k[2] * e1[0] - k[0] * e1[2],
            k[0] * e1[1] - k[1] * e1[0],
        )
    )
    return unit(add(k, add(mul(dx_rad, e1), mul(dy_rad, e2))))

