"""Geometry helpers for the CAM511 channeling-ring baseline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ring:
    id: int
    radius_mm: float
    bending_angle_deg: float
    segment_length_mm: float
    segment_width_mm: float
    segment_thickness_mm: float

    @property
    def geometric_weight(self) -> float:
        return self.radius_mm * self.segment_length_mm
