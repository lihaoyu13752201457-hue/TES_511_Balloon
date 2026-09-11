from __future__ import annotations

import csv
import json
import math
import os
import random
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

from external_baseline.channel_raytrace_py.geometry import containment_diameter_cm
from external_baseline.channel_raytrace_py.vector import unit
from .bragg import bragg_angle_rad, focal_length_m_from_radius_cm


@dataclass(frozen=True)
class LaueRing:
    id: int
    radius_cm: float
    tile_radial_mm: float
    tile_tangential_mm: float
    n_tiles: int


@dataclass(frozen=True)
class LaueConfig:
    system: str
    energy_keV: float
    focal_length_m: float
    d_spacing_A: float
    mosaic_spread_arcmin: float
    rings: Tuple[LaueRing, ...]
    p_diffraction: float
    p_absorption: float
    angular_spread_arcmin: float
    warning: str

    @property
    def focal_length_mm(self) -> float:
        return self.focal_length_m * 1000.0


@dataclass(frozen=True)
class LaueEvent:
    event_id: int
    E_keV: float
    x0_mm: float
    y0_mm: float
    z0_mm: float
    ux0: float
    uy0: float
    uz0: float
    x_mm: float
    y_mm: float
    z_mm: float
    ux: float
    uy: float
    uz: float
    ring_id: int
    outcome: str
    weight: float


def load_laue_config(path: str | Path) -> LaueConfig:
    with Path(path).open() as f:
        raw = yaml.safe_load(f)
    rings = tuple(
        LaueRing(
            id=int(r["id"]),
            radius_cm=float(r["radius_cm"]),
            tile_radial_mm=float(r["tile_radial_mm"]),
            tile_tangential_mm=float(r["tile_tangential_mm"]),
            n_tiles=int(r["n_tiles"]),
        )
        for r in raw["rings"]
    )
    process = raw["process"]
    cfg = LaueConfig(
        system=str(raw["system"]),
        energy_keV=float(raw["energy_keV"]),
        focal_length_m=float(raw["focal_length_m"]),
        d_spacing_A=float(raw["crystals"]["d_spacing_A"]),
        mosaic_spread_arcmin=float(raw["crystals"]["mosaic_spread_arcmin"]),
        rings=rings,
        p_diffraction=float(process["p_diffraction"]),
        p_absorption=float(process["p_absorption"]),
        angular_spread_arcmin=float(process["angular_spread_arcmin"]),
        warning=str(process.get("warning", "")),
    )
    if cfg.p_diffraction < 0.0 or cfg.p_absorption < 0.0 or cfg.p_diffraction + cfg.p_absorption > 1.0:
        raise ValueError("invalid Laue probabilities")
    return cfg


def _sample_ring_position_mm(rng: random.Random, ring: LaueRing) -> Tuple[float, float]:
    radius_mm = ring.radius_cm * 10.0 + rng.uniform(-0.5, 0.5) * ring.tile_radial_mm
    phi = 2.0 * math.pi * rng.random()
    return radius_mm * math.cos(phi), radius_mm * math.sin(phi)


def _focus_offset_mm(rng: random.Random, sigma_arcmin: float, focal_length_mm: float) -> Tuple[float, float]:
    sigma_rad = math.radians(sigma_arcmin / 60.0)
    return rng.gauss(0.0, sigma_rad * focal_length_mm), rng.gauss(0.0, sigma_rad * focal_length_mm)


def trace_laue_event(cfg: LaueConfig, event_id: int, rng: random.Random) -> LaueEvent:
    ring = cfg.rings[event_id % len(cfg.rings)]
    x0_mm, y0_mm = _sample_ring_position_mm(rng, ring)
    u = rng.random()
    if u < cfg.p_absorption:
        outcome = "ABSORB"
        x_mm, y_mm, z_mm = x0_mm, y0_mm, 0.0
        direction = (0.0, 0.0, 1.0)
    elif u < cfg.p_absorption + cfg.p_diffraction:
        dx_mm, dy_mm = _focus_offset_mm(rng, cfg.angular_spread_arcmin, cfg.focal_length_mm)
        x_mm, y_mm, z_mm = dx_mm, dy_mm, cfg.focal_length_mm
        direction = unit((x_mm - x0_mm, y_mm - y0_mm, z_mm))
        outcome = "DIFFRACT"
    else:
        x_mm, y_mm, z_mm = x0_mm, y0_mm, cfg.focal_length_mm
        direction = (0.0, 0.0, 1.0)
        outcome = "TRANSMIT"
    return LaueEvent(
        event_id=event_id,
        E_keV=cfg.energy_keV,
        x0_mm=x0_mm,
        y0_mm=y0_mm,
        z0_mm=0.0,
        ux0=0.0,
        uy0=0.0,
        uz0=1.0,
        x_mm=x_mm,
        y_mm=y_mm,
        z_mm=z_mm,
        ux=direction[0],
        uy=direction[1],
        uz=direction[2],
        ring_id=ring.id,
        outcome=outcome,
        weight=1.0,
    )


def simulate_laue(cfg: LaueConfig, n: int, seed: int) -> List[LaueEvent]:
    rng = random.Random(seed)
    return [trace_laue_event(cfg, i, rng) for i in range(n)]


def summarize_laue(cfg: LaueConfig, events: Iterable[LaueEvent], seed: int) -> Dict[str, object]:
    rows = list(events)
    diffracted = [e for e in rows if e.outcome == "DIFFRACT"]
    points = [(e.x_mm, e.y_mm) for e in diffracted]
    theta = bragg_angle_rad(cfg.energy_keV, cfg.d_spacing_A)
    return {
        "system": cfg.system,
        "warning": cfg.warning,
        "seed": seed,
        "n_primaries": len(rows),
        "n_diffracted": len(diffracted),
        "n_absorbed": sum(1 for e in rows if e.outcome == "ABSORB"),
        "n_transmitted": sum(1 for e in rows if e.outcome == "TRANSMIT"),
        "diffraction_fraction": len(diffracted) / len(rows) if rows else 0.0,
        "spot_d90_cm": containment_diameter_cm(points, 0.9),
        "energy_keV": cfg.energy_keV,
        "bragg_angle_deg": math.degrees(theta),
        "configured_focal_length_m": cfg.focal_length_m,
        "focal_length_from_first_ring_m": focal_length_m_from_radius_cm(cfg.rings[0].radius_cm, theta),
    }


def write_laue_events_csv(path: str | Path, events: Iterable[LaueEvent]) -> None:
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(LaueEvent.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(asdict(e) for e in events)


def plot_laue_spot(path: str | Path, events: Iterable[LaueEvent]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    points = [(e.x_mm / 10.0, e.y_mm / 10.0) for e in events if e.outcome == "DIFFRACT"]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=(5.8, 5.2), dpi=140)
    ax.scatter(xs, ys, s=2.0, alpha=0.35, linewidths=0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x at focal plane [cm]")
    ax.set_ylabel("y at focal plane [cm]")
    ax.set_title("511 keV Laue toy focal spot")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def run_laue_baseline(cfg: LaueConfig, n: int, out_dir: str | Path, seed: int, config_path: Optional[str | Path] = None) -> Dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    events = simulate_laue(cfg, n, seed)
    summary = summarize_laue(cfg, events, seed)
    write_laue_events_csv(out / "laue_events.csv", events)
    plot_laue_spot(out / "focal_spot.png", events)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    if config_path is not None:
        shutil.copyfile(config_path, out / "config_used.yaml")
    return summary
