from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class RingSpec:
    ring_id: int
    design_energy_keV: float
    radius_mm: float
    n_tiles: int
    material: str
    h: int
    k: int
    l: int
    d_spacing_A: float
    tile_size_mm: float
    thickness_mm: float


def load_ring_config(path: str | Path) -> List[RingSpec]:
    with Path(path).open(newline="") as handle:
        return [_ring_from_row(row) for row in csv.DictReader(handle)]


def find_ring(rings: Iterable[RingSpec], ring_id: int) -> RingSpec:
    for ring in rings:
        if ring.ring_id == ring_id:
            return ring
    raise KeyError(f"ring_id {ring_id} not found")


def _ring_from_row(row: dict[str, str]) -> RingSpec:
    return RingSpec(
        ring_id=int(row["ring_id"]),
        design_energy_keV=float(row["design_energy_keV"]),
        radius_mm=float(row["radius_mm"]),
        n_tiles=int(row["n_tiles"]),
        material=row["material"],
        h=int(row["h"]),
        k=int(row["k"]),
        l=int(row["l"]),
        d_spacing_A=float(row["d_spacing_A"]),
        tile_size_mm=float(row["tile_size_mm"]),
        thickness_mm=float(row["thickness_mm"]),
    )
