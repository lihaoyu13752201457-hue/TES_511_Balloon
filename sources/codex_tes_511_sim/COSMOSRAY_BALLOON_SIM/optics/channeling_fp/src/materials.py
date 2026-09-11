"""Material optical-constant helpers for hard X / soft gamma multilayers."""

from __future__ import annotations

from dataclasses import dataclass
import cmath
import math


@dataclass(frozen=True)
class OpticalConstants:
    delta: float
    beta: float

    @property
    def refractive_index(self) -> complex:
        return complex(1.0 - self.delta, self.beta)


DEFAULT_DENSITIES_G_CM3 = {
    "W": 19.25,
    "Si": 2.329,
}


def material_density(material: str) -> float:
    if material not in DEFAULT_DENSITIES_G_CM3:
        raise KeyError(f"No default density configured for material {material!r}")
    return DEFAULT_DENSITIES_G_CM3[material]


def optical_constants_from_xraydb(material: str, density_g_cm3: float, energy_keV: float) -> OpticalConstants:
    try:
        import xraydb
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "xraydb is required for the first-principles channeling model. "
            "Install it before running this project."
        ) from exc

    delta, beta, _atten_len = xraydb.xray_delta_beta(material, density_g_cm3, energy_keV * 1000.0)
    return OpticalConstants(delta=float(delta), beta=float(beta))


def fresnel_surface_reflectivity(optical_constants: OpticalConstants, grazing_angle_rad: float) -> float:
    n = optical_constants.refractive_index
    kz0 = math.sin(grazing_angle_rad)
    kz1 = cmath.sqrt(n * n - (math.cos(grazing_angle_rad) ** 2))
    r = (kz0 - kz1) / (kz0 + kz1)
    return abs(r) ** 2


def roughness_factor_nevot_croce(roughness_nm: float, energy_keV: float, grazing_angle_rad: float) -> float:
    if roughness_nm <= 0.0:
        return 1.0
    wavelength_nm = 1.239841984 / energy_keV
    q = 4.0 * math.pi * math.sin(grazing_angle_rad) / wavelength_nm
    return math.exp(-((q * roughness_nm) ** 2))
