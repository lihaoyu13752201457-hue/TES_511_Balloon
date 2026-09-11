from __future__ import annotations

from .constants import GE_DENSITY_G_CM3


def ge_mu_cm_inv(E_keV: float, density_g_cm3: float = GE_DENSITY_G_CM3) -> float:
    """Linear attenuation coefficient for Ge near 480-550 keV.

    The normalization matches the local opticsim xraydb-backed validation fit
    used by the current Geant4 Laue process.
    """

    mu_at_511 = 0.4321058247470657 * density_g_cm3 / GE_DENSITY_G_CM3
    return mu_at_511 * (511.0 / E_keV) ** 0.55


def ge_mass_attenuation_cm2_g(E_keV: float) -> float:
    return ge_mu_cm_inv(E_keV) / GE_DENSITY_G_CM3
