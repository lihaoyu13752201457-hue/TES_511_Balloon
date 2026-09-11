from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .bragg import bragg_angle_rad
from .constants import DEFAULT_CRYSTALLITE_THICKNESS_UM, DEFAULT_MOSAIC_FWHM_ARCSEC
from .materials import ge_mu_cm_inv


@dataclass(frozen=True)
class ProbabilityResult:
    thetaB_rad: float
    delta_theta_rad: float
    path_length_cm: float
    mu_cm_inv: float
    attenuation: float
    q_cm_inv: float
    w_rad_inv: float
    sigma_cm_inv: float
    p_diff_raw: float
    p_abs_raw: float
    p_trans_raw: float
    prob_sum_raw: float
    prob_residual: float
    p_diff: float
    p_abs: float
    p_trans: float
    renormalized_flag: bool

    def as_dict(self) -> dict[str, float | bool]:
        return asdict(self)


def mosaic_weight_rad_inv(delta_theta_rad: float, mosaic_fwhm_arcsec: float) -> float:
    omega = math.radians(mosaic_fwhm_arcsec / 3600.0)
    return (
        2.0
        * math.sqrt(math.log(2.0) / math.pi)
        / omega
        * math.exp(-math.log(2.0) * (delta_theta_rad / (0.5 * omega)) ** 2)
    )


def ge111_extinction_length_cm(E_keV: float) -> float:
    return 539.7909510452002e-4 * (E_keV / 511.0)


def darwin_f_approx(a_param: float) -> float:
    if abs(a_param) < 1.0e-10:
        return 1.0
    return 1.0 - 0.5 * a_param * a_param + (a_param**4) / 12.0


def darwin_q_ge111_cm_inv(
    E_keV: float,
    d_spacing_A: float,
    crystallite_thickness_um: float = DEFAULT_CRYSTALLITE_THICKNESS_UM,
) -> float:
    thetaB = bragg_angle_rad(E_keV, d_spacing_A)
    d_cm = d_spacing_A * 1.0e-8
    lambda0_cm = ge111_extinction_length_cm(E_keV)
    t0_cm = crystallite_thickness_um * 1.0e-4
    a_param = math.pi * t0_cm / (lambda0_cm * math.cos(thetaB))
    return math.pi * math.pi * d_cm / (lambda0_cm * lambda0_cm * math.cos(thetaB)) * darwin_f_approx(a_param)


def darwin_hamilton_mosaic_probabilities(
    *,
    E_keV: float,
    d_spacing_A: float,
    thickness_mm: float,
    delta_theta_rad: float = 0.0,
    mosaic_fwhm_arcsec: float = DEFAULT_MOSAIC_FWHM_ARCSEC,
    crystallite_thickness_um: float = DEFAULT_CRYSTALLITE_THICKNESS_UM,
    path_length_cm: float | None = None,
    normalize: bool = False,
    strict: bool = False,
    residual_threshold: float = 1.0e-9,
) -> ProbabilityResult:
    thetaB = bragg_angle_rad(E_keV, d_spacing_A)
    if path_length_cm is None:
        path_length_cm = (thickness_mm / 10.0) / math.cos(thetaB)
    q_cm_inv = darwin_q_ge111_cm_inv(E_keV, d_spacing_A, crystallite_thickness_um)
    w_rad_inv = mosaic_weight_rad_inv(delta_theta_rad, mosaic_fwhm_arcsec)
    sigma_cm_inv = q_cm_inv * w_rad_inv
    mu_cm_inv = ge_mu_cm_inv(E_keV)
    attenuation = math.exp(-mu_cm_inv * path_length_cm)
    diffraction_efficiency = 0.5 * (1.0 - math.exp(-2.0 * sigma_cm_inv * (thickness_mm / 10.0)))
    p_diff_raw = diffraction_efficiency * attenuation
    p_abs_raw = 1.0 - attenuation
    p_trans_raw = max(0.0, attenuation - p_diff_raw)
    prob_sum_raw = p_diff_raw + p_abs_raw + p_trans_raw
    prob_residual = 1.0 - prob_sum_raw
    if strict and abs(prob_residual) > residual_threshold:
        raise ValueError(f"probability residual {prob_residual:g} exceeds threshold")
    if normalize and prob_sum_raw > 0.0:
        p_diff = p_diff_raw / prob_sum_raw
        p_abs = p_abs_raw / prob_sum_raw
        p_trans = p_trans_raw / prob_sum_raw
        renormalized = True
    else:
        p_diff = p_diff_raw
        p_abs = p_abs_raw
        p_trans = p_trans_raw
        renormalized = False
    return ProbabilityResult(
        thetaB_rad=thetaB,
        delta_theta_rad=delta_theta_rad,
        path_length_cm=path_length_cm,
        mu_cm_inv=mu_cm_inv,
        attenuation=attenuation,
        q_cm_inv=q_cm_inv,
        w_rad_inv=w_rad_inv,
        sigma_cm_inv=sigma_cm_inv,
        p_diff_raw=p_diff_raw,
        p_abs_raw=p_abs_raw,
        p_trans_raw=p_trans_raw,
        prob_sum_raw=prob_sum_raw,
        prob_residual=prob_residual,
        p_diff=p_diff,
        p_abs=p_abs,
        p_trans=p_trans,
        renormalized_flag=renormalized,
    )
