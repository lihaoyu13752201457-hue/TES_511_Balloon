from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


@dataclass(frozen=True)
class Ring:
    id: int
    radius_cm: float
    bending_angle_deg: float
    length_cm: float
    width_cm: float
    thickness_mm: float


@dataclass(frozen=True)
class Multilayer:
    high_Z_material: str
    low_Z_material: str
    high_Z_thickness_nm: float
    low_Z_thickness_nm: float
    total_stack_thickness_um: float
    open_fraction: float
    roughness_nm: float


@dataclass(frozen=True)
class ChannelConfig:
    system: str
    energy_keV: float
    focal_length_m: float
    lens_outer_diameter_cm: float
    rings: Tuple[Ring, ...]
    multilayer: Multilayer
    raytrace: Dict[str, Any]
    expected: Dict[str, Any]

    @property
    def focal_length_mm(self) -> float:
        return self.focal_length_m * 1000.0

    @property
    def aperture_radius_cm(self) -> float:
        return self.lens_outer_diameter_cm / 2.0

    @property
    def aperture_radius_mm(self) -> float:
        return self.aperture_radius_cm * 10.0

    @property
    def aperture_area_cm2(self) -> float:
        return math.pi * self.aperture_radius_cm * self.aperture_radius_cm

    @property
    def total_transmissivity(self) -> float:
        return float(self.raytrace["total_transmissivity"])

    @property
    def spot_d90_mm(self) -> float:
        return float(self.raytrace["spot_d90_cm"]) * 10.0

    @property
    def spot_sigma_mm(self) -> float:
        return self.spot_d90_mm / math.sqrt(-2.0 * math.log(0.1)) / 2.0

    def nearest_ring(self, r_cm: float) -> Ring:
        return min(self.rings, key=lambda ring: abs(ring.radius_cm - r_cm))


def load_channel_config(path: str | Path) -> ChannelConfig:
    with Path(path).open() as f:
        raw = yaml.safe_load(f)
    rings = tuple(
        Ring(
            id=int(r["id"]),
            radius_cm=float(r["radius_cm"]),
            bending_angle_deg=float(r["bending_angle_deg"]),
            length_cm=float(r["length_cm"]),
            width_cm=float(r["width_cm"]),
            thickness_mm=float(r["thickness_mm"]),
        )
        for r in raw["rings"]
    )
    multilayer_raw = raw["multilayer"]
    multilayer = Multilayer(
        high_Z_material=str(multilayer_raw["high_Z_material"]),
        low_Z_material=str(multilayer_raw["low_Z_material"]),
        high_Z_thickness_nm=float(multilayer_raw["high_Z_thickness_nm"]),
        low_Z_thickness_nm=float(multilayer_raw["low_Z_thickness_nm"]),
        total_stack_thickness_um=float(multilayer_raw["total_stack_thickness_um"]),
        open_fraction=float(multilayer_raw["open_fraction"]),
        roughness_nm=float(multilayer_raw["roughness_nm"]),
    )
    cfg = ChannelConfig(
        system=str(raw["system"]),
        energy_keV=float(raw["energy_keV"]),
        focal_length_m=float(raw["focal_length_m"]),
        lens_outer_diameter_cm=float(raw["lens_outer_diameter_cm"]),
        rings=rings,
        multilayer=multilayer,
        raytrace=dict(raw["raytrace"]),
        expected=dict(raw["expected"]),
    )
    validate_channel_config(cfg)
    return cfg


def validate_channel_config(cfg: ChannelConfig) -> None:
    if cfg.energy_keV <= 0.0:
        raise ValueError("energy_keV must be positive")
    if cfg.focal_length_m <= 0.0 or cfg.lens_outer_diameter_cm <= 0.0:
        raise ValueError("focal length and lens diameter must be positive")
    if not cfg.rings:
        raise ValueError("at least one ring is required")
    if not (0.0 <= cfg.total_transmissivity <= 1.0):
        raise ValueError("total_transmissivity must be within [0, 1]")
    if not (0.0 <= float(cfg.raytrace["loss_absorb_fraction"]) <= 1.0):
        raise ValueError("loss_absorb_fraction must be within [0, 1]")
    if cfg.spot_d90_mm < 0.0:
        raise ValueError("spot_d90 must be non-negative")


def sample_uniform_disk_mm(rng: Any, radius_mm: float) -> Tuple[float, float]:
    r = radius_mm * math.sqrt(rng.random())
    phi = 2.0 * math.pi * rng.random()
    return r * math.cos(phi), r * math.sin(phi)


def containment_diameter_cm(points_mm: Iterable[Tuple[float, float]], fraction: float = 0.9) -> float:
    radii = sorted(math.hypot(x, y) for x, y in points_mm)
    if not radii:
        return 0.0
    idx = max(0, min(len(radii) - 1, math.ceil(fraction * len(radii)) - 1))
    return 2.0 * radii[idx] / 10.0

