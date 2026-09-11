from __future__ import annotations

import math

from .constants import HC_KEV_A


def wavelength_A(E_keV: float) -> float:
    return HC_KEV_A / E_keV


def bragg_angle_rad(E_keV: float, d_spacing_A: float, order: int = 1) -> float:
    arg = order * wavelength_A(E_keV) / (2.0 * d_spacing_A)
    if abs(arg) > 1.0:
        raise ValueError("No Bragg solution")
    return math.asin(arg)


def ring_radius_mm(focal_length_mm: float, thetaB_rad: float) -> float:
    return focal_length_mm * math.tan(2.0 * thetaB_rad)


def focal_length_mm_from_radius(radius_mm: float, thetaB_rad: float) -> float:
    return radius_mm / math.tan(2.0 * thetaB_rad)
