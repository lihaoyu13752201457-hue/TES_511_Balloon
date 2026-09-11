"""Multilayer reflectivity utilities."""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Sequence

from .materials import OpticalConstants, material_density, optical_constants_from_xraydb


HC_KEV_NM = 1.239841984


@dataclass(frozen=True)
class Layer:
    material: str
    thickness_nm: float
    optical_constants: OpticalConstants


def wavelength_nm(energy_keV: float) -> float:
    return HC_KEV_NM / energy_keV


def kz_in_medium(k0_nm_inv: float, n_complex: complex, grazing_angle_rad: float) -> complex:
    sin_a = math.sin(grazing_angle_rad)
    return k0_nm_inv * cmath.sqrt(n_complex * n_complex - (math.cos(grazing_angle_rad) ** 2))


def fresnel_r(kz_j: complex, kz_k: complex) -> complex:
    return (kz_j - kz_k) / (kz_j + kz_k)


def parratt_reflectivity(
    energy_keV: float,
    grazing_angle_rad: float,
    layers: Sequence[Layer],
    substrate: OpticalConstants,
) -> float:
    """Return specular reflectivity using a simple Parratt recursion."""
    lam_nm = wavelength_nm(energy_keV)
    k0 = 2.0 * math.pi / lam_nm

    ambient = OpticalConstants(delta=0.0, beta=0.0)
    media = [ambient] + [layer.optical_constants for layer in layers] + [substrate]
    kz = [kz_in_medium(k0, m.refractive_index, grazing_angle_rad) for m in media]

    r_total = 0.0j
    for i in range(len(layers), 0, -1):
        r_jk = fresnel_r(kz[i], kz[i + 1])
        phase = cmath.exp(2.0j * kz[i] * layers[i - 1].thickness_nm)
        r_total = (r_jk + r_total * phase) / (1.0 + r_jk * r_total * phase)

    r_ambient = fresnel_r(kz[0], kz[1])
    return abs((r_ambient + r_total) / (1.0 + r_ambient * r_total)) ** 2


def bilayer_stack_from_config(cfg: dict, energy_keV: float) -> tuple[list[Layer], OpticalConstants]:
    ml = cfg["multilayer"]
    mat_a = ml["material_a"]
    mat_b = ml["material_b"]
    t_a = float(ml["layer_a_thickness_nm"])
    t_b = float(ml["layer_b_thickness_nm"])
    n_periods = int(ml.get("periods", 1))
    substrate_name = ml.get("substrate", mat_b)

    oc_a = optical_constants_from_xraydb(mat_a, material_density(mat_a), energy_keV)
    oc_b = optical_constants_from_xraydb(mat_b, material_density(mat_b), energy_keV)
    oc_sub = optical_constants_from_xraydb(substrate_name, material_density(substrate_name), energy_keV)

    layers: list[Layer] = []
    for _ in range(n_periods):
        layers.append(Layer(material=mat_a, thickness_nm=t_a, optical_constants=oc_a))
        layers.append(Layer(material=mat_b, thickness_nm=t_b, optical_constants=oc_b))
    return layers, oc_sub
