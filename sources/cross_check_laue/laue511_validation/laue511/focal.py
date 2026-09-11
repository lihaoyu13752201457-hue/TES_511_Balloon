from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .bragg import bragg_angle_rad, focal_length_mm_from_radius, ring_radius_mm
from .probabilities import darwin_hamilton_mosaic_probabilities
from .rings import RingSpec

RAD_TO_ARCSEC = 180.0 / math.pi * 3600.0


@dataclass(frozen=True)
class FocalAuditRow:
    ring_id: int
    energy_keV: float
    radius_mm_config: float
    thickness_mm: float
    thetaB_rad: float
    center_plane_focal_mm_from_config: float
    entry_face_bragg_focal_mm: float
    focal_mm_evaluated: float
    expected_radius_mm_at_focal: float
    center_plane_radius_delta_mm: float
    delta_theta_center_rad: float
    delta_theta_center_arcsec: float
    delta_theta_entry_rad: float
    delta_theta_entry_arcsec: float
    p_diff_at_bragg: float
    p_diff_at_entry_delta: float
    p_diff_abs_delta: float
    p_diff_rel_delta: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def audit_ring_focal_convention(ring: RingSpec, focal_mm: float) -> FocalAuditRow:
    thetaB = bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)
    center_focal = focal_length_mm_from_radius(ring.radius_mm, thetaB)
    entry_face_bragg_focal = center_focal - 0.5 * ring.thickness_mm
    expected_radius = ring_radius_mm(focal_mm, thetaB)
    delta_center = _theta_local_for_radius(ring.radius_mm, focal_mm) - thetaB
    delta_entry = _theta_local_for_radius(ring.radius_mm, focal_mm + 0.5 * ring.thickness_mm) - thetaB
    at_bragg = darwin_hamilton_mosaic_probabilities(
        E_keV=ring.design_energy_keV,
        d_spacing_A=ring.d_spacing_A,
        thickness_mm=ring.thickness_mm,
        delta_theta_rad=0.0,
    )
    at_entry = darwin_hamilton_mosaic_probabilities(
        E_keV=ring.design_energy_keV,
        d_spacing_A=ring.d_spacing_A,
        thickness_mm=ring.thickness_mm,
        delta_theta_rad=delta_entry,
    )
    p_delta = at_entry.p_diff - at_bragg.p_diff
    return FocalAuditRow(
        ring_id=ring.ring_id,
        energy_keV=ring.design_energy_keV,
        radius_mm_config=ring.radius_mm,
        thickness_mm=ring.thickness_mm,
        thetaB_rad=thetaB,
        center_plane_focal_mm_from_config=center_focal,
        entry_face_bragg_focal_mm=entry_face_bragg_focal,
        focal_mm_evaluated=focal_mm,
        expected_radius_mm_at_focal=expected_radius,
        center_plane_radius_delta_mm=ring.radius_mm - expected_radius,
        delta_theta_center_rad=delta_center,
        delta_theta_center_arcsec=delta_center * RAD_TO_ARCSEC,
        delta_theta_entry_rad=delta_entry,
        delta_theta_entry_arcsec=delta_entry * RAD_TO_ARCSEC,
        p_diff_at_bragg=at_bragg.p_diff,
        p_diff_at_entry_delta=at_entry.p_diff,
        p_diff_abs_delta=p_delta,
        p_diff_rel_delta=p_delta / at_bragg.p_diff if at_bragg.p_diff else 0.0,
    )


def audit_focal_convention(rings: list[RingSpec], focal_mm: float) -> dict[str, object]:
    rows = [audit_ring_focal_convention(ring, focal_mm) for ring in rings]
    return {
        "focal_mm_evaluated": focal_mm,
        "n_rings": len(rows),
        "center_plane_focal_mm_mean": _mean(row.center_plane_focal_mm_from_config for row in rows),
        "center_plane_focal_mm_min": min(row.center_plane_focal_mm_from_config for row in rows),
        "center_plane_focal_mm_max": max(row.center_plane_focal_mm_from_config for row in rows),
        "entry_face_bragg_focal_mm_min": min(row.entry_face_bragg_focal_mm for row in rows),
        "entry_face_bragg_focal_mm_max": max(row.entry_face_bragg_focal_mm for row in rows),
        "max_abs_center_plane_radius_delta_mm": max(abs(row.center_plane_radius_delta_mm) for row in rows),
        "max_abs_delta_theta_center_arcsec": max(abs(row.delta_theta_center_arcsec) for row in rows),
        "max_abs_delta_theta_entry_arcsec": max(abs(row.delta_theta_entry_arcsec) for row in rows),
        "max_abs_p_diff_delta": max(abs(row.p_diff_abs_delta) for row in rows),
        "max_abs_p_diff_rel_delta": max(abs(row.p_diff_rel_delta) for row in rows),
        "rows": [row.as_dict() for row in rows],
    }


def _theta_local_for_radius(radius_mm: float, dz_mm: float) -> float:
    return 0.5 * math.atan2(radius_mm, dz_mm)


def _mean(values: object) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
