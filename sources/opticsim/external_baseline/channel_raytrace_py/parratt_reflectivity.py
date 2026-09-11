from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
import xraydb
from xraydb.xray import PLANCK_HC


@dataclass(frozen=True)
class MultilayerSpec:
    stack_id: str = "WSi_30_150"
    high_Z_material: str = "W"
    low_Z_material: str = "Si"
    high_Z_density_g_cm3: float = 19.3
    low_Z_density_g_cm3: float = 2.33
    high_Z_thickness_nm: float = 30.0
    low_Z_thickness_nm: float = 150.0
    n_periods: int = 30
    substrate_material: str = "Si"
    substrate_density_g_cm3: float = 2.33
    roughness_nm: float = 5.0
    polarization: str = "s"

    @property
    def high_Z_thickness_A(self) -> float:
        return self.high_Z_thickness_nm * 10.0

    @property
    def low_Z_thickness_A(self) -> float:
        return self.low_Z_thickness_nm * 10.0

    @property
    def total_stack_thickness_cm(self) -> float:
        return (self.high_Z_thickness_nm + self.low_Z_thickness_nm) * self.n_periods * 1.0e-7

    @property
    def open_fraction(self) -> float:
        period = self.high_Z_thickness_nm + self.low_Z_thickness_nm
        return self.low_Z_thickness_nm / period


@dataclass(frozen=True)
class ReflectivityGridRow:
    stack_id: str
    E_keV: float
    theta_rad: float
    R: float
    A: float
    T: float
    open_fraction: float
    sigma_slope_rad: float
    sigma_rough_nm: float
    source: str


def geometric_theta_grid(theta_min_rad: float, theta_max_rad: float, n: int) -> np.ndarray:
    if theta_min_rad <= 0.0 or theta_max_rad <= 0.0:
        raise ValueError("theta limits must be positive")
    if theta_max_rad <= theta_min_rad:
        raise ValueError("theta_max_rad must exceed theta_min_rad")
    if n < 2:
        raise ValueError("n must be at least 2")
    return np.geomspace(theta_min_rad, theta_max_rad, n)


def _effective_mu_cm_inv(spec: MultilayerSpec, E_eV: float) -> float:
    mu_high = float(xraydb.material_mu(spec.high_Z_material, E_eV, density=spec.high_Z_density_g_cm3))
    mu_low = float(xraydb.material_mu(spec.low_Z_material, E_eV, density=spec.low_Z_density_g_cm3))
    period = spec.high_Z_thickness_nm + spec.low_Z_thickness_nm
    return (
        mu_high * spec.high_Z_thickness_nm / period
        + mu_low * spec.low_Z_thickness_nm / period
    )


def _nonreflected_transmission(spec: MultilayerSpec, E_eV: float, theta_rad: float) -> float:
    sin_theta = max(math.sin(theta_rad), 1.0e-12)
    path_cm = spec.total_stack_thickness_cm / sin_theta
    tau = _effective_mu_cm_inv(spec, E_eV) * path_cm
    if tau > 700.0:
        return 0.0
    return math.exp(-tau)


def compute_reflectivity_rows(
    spec: MultilayerSpec,
    *,
    E_keV: float,
    theta_rad: Sequence[float],
    sigma_slope_rad: float = 0.0,
) -> List[ReflectivityGridRow]:
    if E_keV <= 0.0:
        raise ValueError("E_keV must be positive")
    E_eV = E_keV * 1000.0
    theta_values = np.asarray(theta_rad, dtype=float)
    if np.any(theta_values <= 0.0):
        raise ValueError("all theta values must be positive")

    R_values = xraydb.multilayer_reflectivity(
        [spec.high_Z_material, spec.low_Z_material],
        [spec.high_Z_thickness_A, spec.low_Z_thickness_A],
        spec.substrate_material,
        theta_values,
        E_eV,
        n_periods=spec.n_periods,
        density=[spec.high_Z_density_g_cm3, spec.low_Z_density_g_cm3],
        substrate_density=spec.substrate_density_g_cm3,
        substrate_rough=spec.roughness_nm * 10.0,
        surface_rough=spec.roughness_nm * 10.0,
        polarization=spec.polarization,
        output="intensity",
    )

    rows: List[ReflectivityGridRow] = []
    for theta, raw_R in zip(theta_values, R_values):
        R = min(1.0, max(0.0, float(raw_R)))
        T_nonreflected = _nonreflected_transmission(spec, E_eV, float(theta))
        T = (1.0 - R) * T_nonreflected
        A = 1.0 - R - T
        rows.append(
            ReflectivityGridRow(
                stack_id=spec.stack_id,
                E_keV=E_keV,
                theta_rad=float(theta),
                R=R,
                A=max(0.0, A),
                T=max(0.0, T),
                open_fraction=spec.open_fraction,
                sigma_slope_rad=sigma_slope_rad,
                sigma_rough_nm=spec.roughness_nm,
                source="xraydb_multilayer_reflectivity_chantler_plus_stack_attenuation",
            )
        )
    return rows


def manual_parratt_reflectivity_s(
    spec: MultilayerSpec,
    *,
    E_keV: float,
    theta_rad: Sequence[float],
) -> np.ndarray:
    """Independent s-polarization Parratt recursion for W/Si cross-checks.

    This intentionally does not call `xraydb.multilayer_reflectivity`; it only
    uses xraydb material optical constants. Thicknesses are handled in Angstroms
    to match the xraydb optical-constant convention.
    """
    if E_keV <= 0.0:
        raise ValueError("E_keV must be positive")
    theta = np.asarray(theta_rad, dtype=float)
    if np.any(theta <= 0.0):
        raise ValueError("all theta values must be positive")
    E_eV = E_keV * 1000.0
    k0 = 2.0 * np.pi * E_eV / PLANCK_HC
    k_air_z = k0 * np.sin(theta)
    cos_theta_sq = np.cos(theta) ** 2

    period_materials = [spec.high_Z_material, spec.low_Z_material]
    period_densities = [spec.high_Z_density_g_cm3, spec.low_Z_density_g_cm3]
    period_thickness_A = [spec.high_Z_thickness_A, spec.low_Z_thickness_A]
    layers = period_materials * spec.n_periods
    densities = period_densities * spec.n_periods
    thickness_A = period_thickness_A * spec.n_periods

    kz = []
    for material, density in zip(layers, densities):
        delta, beta, _ = xraydb.xray_delta_beta(material, density, E_eV)
        n_complex = 1.0 - delta + 1j * beta
        kz.append(k0 * np.sqrt(n_complex * n_complex - cos_theta_sq))

    delta_sub, beta_sub, _ = xraydb.xray_delta_beta(
        spec.substrate_material,
        spec.substrate_density_g_cm3,
        E_eV,
    )
    n_sub = 1.0 - delta_sub + 1j * beta_sub
    kz_sub = k0 * np.sqrt(n_sub * n_sub - cos_theta_sq)

    rough_A = spec.roughness_nm * 10.0
    amp = (kz[-1] - kz_sub) / (kz[-1] + kz_sub)
    if rough_A > 0.0:
        amp = amp * np.exp(-2.0 * rough_A * rough_A * kz[-1] * kz_sub)
    for i in reversed(range(len(layers) - 1)):
        fresnel = (kz[i] - kz[i + 1]) / (kz[i] + kz[i + 1])
        phase = np.exp(2j * thickness_A[i + 1] * kz[i + 1])
        amp = (fresnel + amp * phase) / (1.0 + fresnel * amp * phase)

    fresnel_surface = (k_air_z - kz[0]) / (k_air_z + kz[0])
    phase_surface = np.exp(2j * thickness_A[0] * kz[0])
    amp = (fresnel_surface + amp * phase_surface) / (1.0 + fresnel_surface * amp * phase_surface)
    if rough_A > 0.0:
        amp = amp * np.exp(-2.0 * rough_A * rough_A * k_air_z * kz[0])
    return np.clip((amp * np.conjugate(amp)).real, 0.0, 1.0)


def compute_manual_parratt_rows(
    spec: MultilayerSpec,
    *,
    E_keV: float,
    theta_rad: Sequence[float],
    sigma_slope_rad: float = 0.0,
) -> List[ReflectivityGridRow]:
    E_eV = E_keV * 1000.0
    theta_values = np.asarray(theta_rad, dtype=float)
    R_values = manual_parratt_reflectivity_s(spec, E_keV=E_keV, theta_rad=theta_values)
    rows: List[ReflectivityGridRow] = []
    for theta, raw_R in zip(theta_values, R_values):
        R = min(1.0, max(0.0, float(raw_R)))
        T_nonreflected = _nonreflected_transmission(spec, E_eV, float(theta))
        T = (1.0 - R) * T_nonreflected
        A = 1.0 - R - T
        rows.append(
            ReflectivityGridRow(
                stack_id=spec.stack_id,
                E_keV=E_keV,
                theta_rad=float(theta),
                R=R,
                A=max(0.0, A),
                T=max(0.0, T),
                open_fraction=spec.open_fraction,
                sigma_slope_rad=sigma_slope_rad,
                sigma_rough_nm=spec.roughness_nm,
                source="manual_parratt_recursion_chantler_plus_stack_attenuation",
            )
        )
    return rows


def write_reflectivity_csv(path: str | Path, rows: Iterable[ReflectivityGridRow]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("no rows to write")
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ReflectivityGridRow.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def summarize_rows(rows: Sequence[ReflectivityGridRow]) -> dict[str, float]:
    if not rows:
        raise ValueError("no rows to summarize")
    best = max(rows, key=lambda r: r.R)
    last_high = max((r.theta_rad for r in rows if r.R >= 0.5), default=0.0)
    return {
        "n_rows": float(len(rows)),
        "max_R": best.R,
        "theta_at_max_R_rad": best.theta_rad,
        "theta_R_ge_0p5_max_rad": last_high,
        "R_at_min_theta": rows[0].R,
        "R_at_max_theta": rows[-1].R,
        "open_fraction": rows[0].open_fraction,
    }
