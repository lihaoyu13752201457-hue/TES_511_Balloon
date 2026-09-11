from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Mapping, Sequence, Tuple


def branch_fractions(counts: Mapping[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total == 0:
        return {"ABSORB": 0.0, "DIFFRACT": 0.0, "TRANSMIT": 0.0}
    return {key: counts.get(key, 0) / total for key in ("ABSORB", "DIFFRACT", "TRANSMIT")}


def binomial_z(observed: int, n: int, p: float) -> float:
    variance = n * p * (1.0 - p)
    if variance <= 0.0:
        return 0.0
    return (observed - n * p) / math.sqrt(variance)


def containment_diameter_mm(points: Sequence[Tuple[float, float]], fraction: float = 0.9) -> float:
    if not points:
        return 0.0
    radii = sorted(math.hypot(x, y) for x, y in points)
    idx = min(len(radii) - 1, max(0, math.ceil(fraction * len(radii)) - 1))
    return 2.0 * radii[idx]


def weighted_containment_diameter_mm(
    points: Sequence[Tuple[float, float]],
    weights: Sequence[float],
    fraction: float = 0.9,
) -> float:
    if not points:
        return 0.0
    weighted_radii = sorted((math.hypot(x, y), weight) for (x, y), weight in zip(points, weights))
    total_weight = sum(weight for _, weight in weighted_radii)
    if total_weight <= 0.0:
        return 0.0
    target = fraction * total_weight
    cumulative = 0.0
    for radius, weight in weighted_radii:
        cumulative += weight
        if cumulative >= target:
            return 2.0 * radius
    return 2.0 * weighted_radii[-1][0]


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
