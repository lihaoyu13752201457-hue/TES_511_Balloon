from __future__ import annotations

import math

HC_KEV_A = 12.398419843320026


def wavelength_A(E_keV: float) -> float:
    if E_keV <= 0.0:
        raise ValueError("E_keV must be positive")
    return HC_KEV_A / E_keV


def bragg_angle_rad(E_keV: float, d_spacing_A: float, order: int = 1) -> float:
    if d_spacing_A <= 0.0:
        raise ValueError("d_spacing_A must be positive")
    if order <= 0:
        raise ValueError("order must be positive")
    arg = order * wavelength_A(E_keV) / (2.0 * d_spacing_A)
    if arg > 1.0:
        raise ValueError("Bragg condition cannot be satisfied for this E/d/order")
    return math.asin(arg)


def focal_length_m_from_radius_cm(radius_cm: float, theta_B_rad: float) -> float:
    if radius_cm <= 0.0:
        raise ValueError("radius_cm must be positive")
    denom = math.tan(2.0 * theta_B_rad)
    if denom <= 0.0:
        raise ValueError("theta_B_rad must be positive")
    return (radius_cm / 100.0) / denom


def ring_radius_cm_from_focal_length_m(focal_length_m: float, theta_B_rad: float) -> float:
    if focal_length_m <= 0.0:
        raise ValueError("focal_length_m must be positive")
    return 100.0 * focal_length_m * math.tan(2.0 * theta_B_rad)

