from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import xraydb
from scipy import integrate, special


HC_KEV_A = 12.398419843320026
CLASSICAL_ELECTRON_RADIUS_CM = 2.8179403262e-13


@dataclass(frozen=True)
class CrystalModel:
    material: str
    lattice: str
    lattice_constant_A: float


@dataclass(frozen=True)
class DarwinMosaicResult:
    energy_keV: float
    theta_B_rad: float
    delta_theta_rad: float
    material: str
    h: int
    k: int
    l: int
    d_spacing_A: float
    mosaic_fwhm_arcsec: float
    thickness_mm: float
    crystallite_thickness_um: float
    extinction_length_um: float
    q_cm_inv: float
    w_rad_inv: float
    coherent_sigma_cm_inv: float
    absorption_mu_cm_inv: float
    absorption_transmission: float
    diffraction_efficiency_no_abs: float
    p_diff: float
    p_abs: float
    p_trans: float
    source: str


CRYSTALS: Dict[str, CrystalModel] = {
    "Ge": CrystalModel("Ge", "diamond", 5.6579),
    "Si": CrystalModel("Si", "diamond", 5.4310),
    "Cu": CrystalModel("Cu", "fcc", 3.6149),
    "Au": CrystalModel("Au", "fcc", 4.0782),
}


def bragg_angle_rad(energy_keV: float, d_spacing_A: float) -> float:
    arg = HC_KEV_A / energy_keV / (2.0 * d_spacing_A)
    if not 0.0 < arg < 1.0:
        raise ValueError(f"invalid Bragg argument {arg:g}")
    return math.asin(arg)


def d_spacing_A(material: str, h: int, k: int, l: int) -> float:
    crystal = _crystal(material)
    return crystal.lattice_constant_A / math.sqrt(h * h + k * k + l * l)


def mosaic_weight_rad_inv(delta_theta_rad: float, mosaic_fwhm_arcsec: float) -> float:
    omega = math.radians(mosaic_fwhm_arcsec / 3600.0)
    if omega <= 0.0:
        raise ValueError("mosaic_fwhm_arcsec must be positive")
    return 2.0 * math.sqrt(math.log(2.0) / math.pi) / omega * math.exp(
        -math.log(2.0) * (delta_theta_rad / (0.5 * omega)) ** 2
    )


def structure_factor_abs(material: str, h: int, k: int, l: int, energy_keV: float) -> float:
    crystal = _crystal(material)
    d_A = d_spacing_A(material, h, k, l)
    q_A_inv = 1.0 / (2.0 * d_A)
    f0 = float(xraydb.f0(material, q_A_inv)[0])
    f1 = float(xraydb.f1_chantler(material, energy_keV * 1000.0))
    f2 = float(xraydb.f2_chantler(material, energy_keV * 1000.0))
    atom_f = complex(f0 + f1, f2)
    lattice_sum = _lattice_sum(crystal.lattice, h, k, l)
    return abs(lattice_sum * atom_f)


def extinction_length_cm(
    energy_keV: float,
    material: str,
    h: int,
    k: int,
    l: int,
    polarization_factor: float = 1.0,
) -> float:
    if polarization_factor <= 0.0:
        raise ValueError("polarization_factor must be positive")
    crystal = _crystal(material)
    d_A = d_spacing_A(material, h, k, l)
    theta_B = bragg_angle_rad(energy_keV, d_A)
    wavelength_cm = HC_KEV_A / energy_keV * 1.0e-8
    unit_cell_volume_cm3 = (crystal.lattice_constant_A * 1.0e-8) ** 3
    structure_factor = structure_factor_abs(material, h, k, l, energy_keV)
    if structure_factor <= 0.0:
        raise ValueError(f"{material}({h}{k}{l}) has zero structure factor in {crystal.lattice}")
    return (
        math.pi
        * unit_cell_volume_cm3
        * math.cos(theta_B)
        / (CLASSICAL_ELECTRON_RADIUS_CM * wavelength_cm * polarization_factor * structure_factor)
    )


def darwin_q_cm_inv(
    energy_keV: float,
    material: str,
    h: int,
    k: int,
    l: int,
    crystallite_thickness_um: float,
) -> float:
    d_cm = d_spacing_A(material, h, k, l) * 1.0e-8
    theta_B = bragg_angle_rad(energy_keV, d_spacing_A(material, h, k, l))
    lambda0_cm = extinction_length_cm(energy_keV, material, h, k, l)
    t0_cm = crystallite_thickness_um * 1.0e-4
    a_param = math.pi * t0_cm / (lambda0_cm * math.cos(theta_B))
    f_a = _darwin_f(a_param)
    return math.pi * math.pi * d_cm / (lambda0_cm * lambda0_cm * math.cos(theta_B)) * f_a


def darwin_mosaic_probabilities(
    *,
    energy_keV: float,
    material: str,
    h: int,
    k: int,
    l: int,
    mosaic_fwhm_arcsec: float,
    thickness_mm: float,
    crystallite_thickness_um: float,
    delta_theta_rad: float = 0.0,
) -> DarwinMosaicResult:
    d_A = d_spacing_A(material, h, k, l)
    theta_B = bragg_angle_rad(energy_keV, d_A)
    thickness_cm = thickness_mm / 10.0
    q_cm_inv = darwin_q_cm_inv(energy_keV, material, h, k, l, crystallite_thickness_um)
    w_rad_inv = mosaic_weight_rad_inv(delta_theta_rad, mosaic_fwhm_arcsec)
    sigma = w_rad_inv * q_cm_inv
    mu = float(xraydb.material_mu(material, energy_keV * 1000.0))
    absorption_transmission = math.exp(-mu * thickness_cm / math.cos(theta_B))
    diffraction_efficiency = 0.5 * (1.0 - math.exp(-2.0 * sigma * thickness_cm))
    p_diff = diffraction_efficiency * absorption_transmission
    p_abs = 1.0 - absorption_transmission
    p_trans = max(0.0, absorption_transmission - p_diff)
    total = p_diff + p_abs + p_trans
    if total > 0.0:
        p_diff /= total
        p_abs /= total
        p_trans /= total
    lambda0_cm = extinction_length_cm(energy_keV, material, h, k, l)
    return DarwinMosaicResult(
        energy_keV=energy_keV,
        theta_B_rad=theta_B,
        delta_theta_rad=delta_theta_rad,
        material=material,
        h=h,
        k=k,
        l=l,
        d_spacing_A=d_A,
        mosaic_fwhm_arcsec=mosaic_fwhm_arcsec,
        thickness_mm=thickness_mm,
        crystallite_thickness_um=crystallite_thickness_um,
        extinction_length_um=lambda0_cm * 1.0e4,
        q_cm_inv=q_cm_inv,
        w_rad_inv=w_rad_inv,
        coherent_sigma_cm_inv=sigma,
        absorption_mu_cm_inv=mu,
        absorption_transmission=absorption_transmission,
        diffraction_efficiency_no_abs=diffraction_efficiency,
        p_diff=p_diff,
        p_abs=p_abs,
        p_trans=p_trans,
        source=(
            "barriere2009_zachariasen_darwin_mosaic"
            f";xraydb={getattr(xraydb, '__version__', 'unknown')}"
            f";crystallite_um={crystallite_thickness_um:g}"
        ),
    )


def optimal_mosaic_thickness_mm(
    *,
    energy_keV: float,
    material: str,
    h: int,
    k: int,
    l: int,
    mosaic_fwhm_arcsec: float,
    crystallite_thickness_um: float,
) -> float:
    q_cm_inv = darwin_q_cm_inv(energy_keV, material, h, k, l, crystallite_thickness_um)
    w0 = mosaic_weight_rad_inv(0.0, mosaic_fwhm_arcsec)
    mu = float(xraydb.material_mu(material, energy_keV * 1000.0))
    denominator = 2.0 * w0 * q_cm_inv
    if denominator <= 0.0:
        raise ValueError("invalid Darwin denominator")
    return 10.0 * math.log(denominator / mu + 1.0) / denominator


def _crystal(material: str) -> CrystalModel:
    try:
        return CRYSTALS[material]
    except KeyError as exc:
        raise ValueError(f"unsupported crystal material: {material}") from exc


def _lattice_sum(lattice: str, h: int, k: int, l: int) -> complex:
    if lattice == "fcc":
        if h % 2 == k % 2 == l % 2:
            return 4.0 + 0.0j
        return 0.0 + 0.0j
    if lattice == "diamond":
        if h % 2 != k % 2 or h % 2 != l % 2:
            return 0.0 + 0.0j
        fcc_sum = 4.0
        phase = complex(
            math.cos(0.5 * math.pi * (h + k + l)),
            math.sin(0.5 * math.pi * (h + k + l)),
        )
        return fcc_sum * (1.0 + phase)
    raise ValueError(f"unsupported lattice: {lattice}")


def _darwin_f(a_param: float) -> float:
    if abs(a_param) < 1.0e-10:
        return 1.0
    upper = 2.0 * a_param
    integral = integrate.quad(lambda x: special.j0(x), 0.0, upper, epsabs=1.0e-10, epsrel=1.0e-10)[0]
    return integral / upper
