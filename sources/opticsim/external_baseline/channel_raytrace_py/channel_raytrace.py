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

from .geometry import ChannelConfig, containment_diameter_cm, sample_uniform_disk_mm
from .reflectivity_table import ReflectivityTable
from .vector import Vector3, unit


@dataclass(frozen=True)
class ChannelEvent:
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
    weight: float
    source_tag: str
    ring_id: int
    n_bounce: int
    survived: int
    outcome: str


def _estimated_bounce_count(r_cm: float, ring_length_cm: float, bending_angle_deg: float) -> int:
    if r_cm <= 0.0:
        return 0
    bend_rad = math.radians(bending_angle_deg)
    path_factor = max(1.0, ring_length_cm / 2.0)
    return max(1, int(round(path_factor * (1.0 + bend_rad * 180.0 / math.pi))))


def trace_effective_channel_event(cfg: ChannelConfig, event_id: int, rng: random.Random) -> ChannelEvent:
    x0_mm, y0_mm = sample_uniform_disk_mm(rng, cfg.aperture_radius_mm)
    r_cm = math.hypot(x0_mm, y0_mm) / 10.0
    ring = cfg.nearest_ring(r_cm)

    survived = rng.random() < cfg.total_transmissivity
    loss_absorb_fraction = float(cfg.raytrace["loss_absorb_fraction"])

    if survived:
        spot_x_mm = rng.gauss(0.0, cfg.spot_sigma_mm)
        spot_y_mm = rng.gauss(0.0, cfg.spot_sigma_mm)
        outcome = "EXIT"
        n_bounce = _estimated_bounce_count(r_cm, ring.length_cm, ring.bending_angle_deg)
    else:
        spot_x_mm = float("nan")
        spot_y_mm = float("nan")
        outcome = "ABSORB" if rng.random() < loss_absorb_fraction else "LEAK"
        n_bounce = max(0, _estimated_bounce_count(r_cm, ring.length_cm, ring.bending_angle_deg) - 1)

    if survived:
        direction = unit((spot_x_mm - x0_mm, spot_y_mm - y0_mm, cfg.focal_length_mm))
        x_mm = spot_x_mm
        y_mm = spot_y_mm
        z_mm = cfg.focal_length_mm
    else:
        direction = (0.0, 0.0, 1.0)
        x_mm = x0_mm
        y_mm = y0_mm
        z_mm = 0.0

    return ChannelEvent(
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
        weight=1.0,
        source_tag=cfg.system,
        ring_id=ring.id,
        n_bounce=n_bounce,
        survived=1 if survived else 0,
        outcome=outcome,
    )


def _theta_for_policy(
    ring_bending_angle_deg: float,
    n_bounce: int,
    policy: str,
    fixed_theta_rad: Optional[float],
    ring_id: Optional[int] = None,
    ring_theta_rad: Optional[Dict[int, float]] = None,
) -> float:
    if policy == "ring_calibrated":
        if ring_id is None or ring_theta_rad is None or ring_id not in ring_theta_rad:
            raise ValueError("ring_calibrated theta policy requires a theta map containing every ring id")
        theta = ring_theta_rad[ring_id]
        if theta <= 0.0:
            raise ValueError("ring-calibrated theta values must be positive")
        return theta
    if policy == "fixed":
        if fixed_theta_rad is None or fixed_theta_rad <= 0.0:
            raise ValueError("fixed_theta_rad must be positive for fixed theta policy")
        return fixed_theta_rad
    if policy == "ring_bending":
        return math.radians(ring_bending_angle_deg)
    if policy == "ring_bending_per_bounce":
        return math.radians(ring_bending_angle_deg) / max(1, n_bounce)
    raise ValueError(f"unknown theta policy: {policy}")


def trace_reflectivity_table_channel_event(
    cfg: ChannelConfig,
    event_id: int,
    rng: random.Random,
    table: ReflectivityTable,
    theta_policy: str = "fixed",
    fixed_theta_rad: Optional[float] = None,
    stack_id: str = "WSi_30_150",
    ring_theta_rad: Optional[Dict[int, float]] = None,
) -> ChannelEvent:
    x0_mm, y0_mm = sample_uniform_disk_mm(rng, cfg.aperture_radius_mm)
    r_cm = math.hypot(x0_mm, y0_mm) / 10.0
    ring = cfg.nearest_ring(r_cm)
    n_bounce = _estimated_bounce_count(r_cm, ring.length_cm, ring.bending_angle_deg)
    theta_rad = _theta_for_policy(
        ring.bending_angle_deg,
        n_bounce,
        theta_policy,
        fixed_theta_rad,
        ring_id=ring.id,
        ring_theta_rad=ring_theta_rad,
    )
    params = table.lookup(cfg.energy_keV, theta_rad, stack_id)

    outcome = "EXIT"
    for _ in range(n_bounce):
        u = rng.random()
        if u < params.A:
            outcome = "ABSORB"
            break
        if u >= params.A + params.R:
            outcome = "LEAK"
            break

    if outcome == "EXIT":
        spot_x_mm = rng.gauss(0.0, cfg.spot_sigma_mm)
        spot_y_mm = rng.gauss(0.0, cfg.spot_sigma_mm)
        direction = unit((spot_x_mm - x0_mm, spot_y_mm - y0_mm, cfg.focal_length_mm))
        x_mm = spot_x_mm
        y_mm = spot_y_mm
        z_mm = cfg.focal_length_mm
    else:
        direction = (0.0, 0.0, 1.0)
        x_mm = x0_mm
        y_mm = y0_mm
        z_mm = 0.0

    return ChannelEvent(
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
        weight=1.0,
        source_tag=cfg.system,
        ring_id=ring.id,
        n_bounce=n_bounce,
        survived=1 if outcome == "EXIT" else 0,
        outcome=outcome,
    )


def simulate_channel(cfg: ChannelConfig, n: int, seed: Optional[int] = None) -> List[ChannelEvent]:
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = random.Random(int(seed if seed is not None else cfg.raytrace["seed_default"]))
    return [trace_effective_channel_event(cfg, i, rng) for i in range(n)]


def simulate_channel_with_reflectivity(
    cfg: ChannelConfig,
    n: int,
    table: ReflectivityTable,
    seed: Optional[int] = None,
    theta_policy: str = "fixed",
    fixed_theta_rad: Optional[float] = None,
    stack_id: str = "WSi_30_150",
    ring_theta_rad: Optional[Dict[int, float]] = None,
) -> List[ChannelEvent]:
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = random.Random(int(seed if seed is not None else cfg.raytrace["seed_default"]))
    return [
        trace_reflectivity_table_channel_event(
            cfg,
            i,
            rng,
            table,
            theta_policy=theta_policy,
            fixed_theta_rad=fixed_theta_rad,
            stack_id=stack_id,
            ring_theta_rad=ring_theta_rad,
        )
        for i in range(n)
    ]


def summarize_events(cfg: ChannelConfig, events: Iterable[ChannelEvent], seed: int, model: Optional[str] = None) -> Dict[str, object]:
    rows = list(events)
    survived = [e for e in rows if e.survived]
    focal_points = [(e.x_mm, e.y_mm) for e in survived]
    n = len(rows)
    n_survived = len(survived)
    transmissivity = n_survived / n if n else 0.0
    spot_d90_cm = containment_diameter_cm(focal_points, 0.9)
    spot_rms_cm = 0.0
    if focal_points:
        spot_rms_cm = math.sqrt(sum(x * x + y * y for x, y in focal_points) / len(focal_points)) / 10.0
    return {
        "system": cfg.system,
        "model": model or cfg.raytrace["model"],
        "schema_version": "channel_optics_summary_v2",
        "model_class": "calibrated_detector_handoff",
        "is_calibrated_handoff": True,
        "is_public_wallbywall_geometry": False,
        "is_first_principles_80pct_closure": False,
        "calibration_target": "511-CAM headline transmissivity scale; detector handoff only",
        "warning": cfg.raytrace.get("warning", ""),
        "seed": seed,
        "n_primaries": n,
        "n_survived": n_survived,
        "n_absorbed": sum(1 for e in rows if e.outcome == "ABSORB"),
        "n_leaked": sum(1 for e in rows if e.outcome == "LEAK"),
        "transmissivity": transmissivity,
        "target_transmissivity": cfg.total_transmissivity,
        "aperture_area_cm2": cfg.aperture_area_cm2,
        "effective_area_cm2": cfg.aperture_area_cm2 * transmissivity,
        "target_effective_area_cm2": cfg.expected.get("effective_area_cm2"),
        "spot_d90_cm": spot_d90_cm,
        "spot_rms_cm": spot_rms_cm,
        "target_spot_d90_cm": cfg.raytrace["spot_d90_cm"],
        "energy_keV": cfg.energy_keV,
        "focal_length_m": cfg.focal_length_m,
        "open_fraction_policy": cfg.raytrace["open_fraction_policy"],
    }


def summarize_events_by_ring(cfg: ChannelConfig, events: Iterable[ChannelEvent]) -> List[Dict[str, object]]:
    rows = list(events)
    total_n = len(rows)
    summaries: List[Dict[str, object]] = []
    for ring in cfg.rings:
        ring_rows = [e for e in rows if e.ring_id == ring.id]
        n = len(ring_rows)
        n_survived = sum(1 for e in ring_rows if e.survived)
        n_absorbed = sum(1 for e in ring_rows if e.outcome == "ABSORB")
        n_leaked = sum(1 for e in ring_rows if e.outcome == "LEAK")
        mean_bounce = sum(e.n_bounce for e in ring_rows) / n if n else 0.0
        transmissivity = n_survived / n if n else 0.0
        aperture_fraction = n / total_n if total_n else 0.0
        summaries.append(
            {
                "ring_id": ring.id,
                "radius_cm": ring.radius_cm,
                "bending_angle_deg": ring.bending_angle_deg,
                "length_cm": ring.length_cm,
                "n_primaries": n,
                "aperture_fraction_sampled": aperture_fraction,
                "n_survived": n_survived,
                "n_absorbed": n_absorbed,
                "n_leaked": n_leaked,
                "transmissivity": transmissivity,
                "mean_bounce": mean_bounce,
                "effective_area_contribution_cm2": cfg.aperture_area_cm2 * n_survived / total_n if total_n else 0.0,
            }
        )
    return summaries


def write_events_csv(path: str | Path, events: Iterable[ChannelEvent]) -> None:
    rows = [asdict(e) for e in events]
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ChannelEvent.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_per_ring_summary_csv(path: str | Path, summaries: Iterable[Dict[str, object]]) -> None:
    rows = list(summaries)
    if not rows:
        raise ValueError("no ring summaries to write")
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_phase_space_csv(path: str | Path, events: Iterable[ChannelEvent]) -> None:
    fields = ["event_id", "E_keV", "x_mm", "y_mm", "z_mm", "ux", "uy", "uz", "weight", "source_tag"]
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in events:
            if e.survived:
                writer.writerow({field: getattr(e, field) for field in fields})


def write_optics_history_csv(path: str | Path, events: Iterable[ChannelEvent], cfg: ChannelConfig) -> None:
    fields = [
        "event_id",
        "track_id",
        "optics_kind",
        "stage",
        "ring_id",
        "tile_id",
        "surface_id",
        "E_keV",
        "x_mm",
        "y_mm",
        "z_mm",
        "ux_in",
        "uy_in",
        "uz_in",
        "ux_out",
        "uy_out",
        "uz_out",
        "grazing_angle_rad",
        "p_reflect",
        "p_absorb",
        "p_transmit",
        "n_bounce",
        "weight",
    ]
    p_survive = cfg.total_transmissivity
    p_absorb = (1.0 - p_survive) * float(cfg.raytrace["loss_absorb_fraction"])
    p_leak = 1.0 - p_survive - p_absorb
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in events:
            writer.writerow(
                {
                    "event_id": e.event_id,
                    "track_id": 1,
                    "optics_kind": "CHANNEL",
                    "stage": e.outcome,
                    "ring_id": e.ring_id,
                    "tile_id": -1,
                    "surface_id": "effective_axisymmetric_channel",
                    "E_keV": e.E_keV,
                    "x_mm": e.x_mm,
                    "y_mm": e.y_mm,
                    "z_mm": e.z_mm,
                    "ux_in": e.ux0,
                    "uy_in": e.uy0,
                    "uz_in": e.uz0,
                    "ux_out": e.ux,
                    "uy_out": e.uy,
                    "uz_out": e.uz,
                    "grazing_angle_rad": "",
                    "p_reflect": p_survive,
                    "p_absorb": p_absorb,
                    "p_transmit": p_leak,
                    "n_bounce": e.n_bounce,
                    "weight": e.weight,
                }
            )


def plot_focal_spot(path: str | Path, events: Iterable[ChannelEvent], summary: Dict[str, object]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    survived = [e for e in events if e.survived]
    xs = [e.x_mm / 10.0 for e in survived]
    ys = [e.y_mm / 10.0 for e in survived]
    fig, ax = plt.subplots(figsize=(5.8, 5.2), dpi=140)
    ax.scatter(xs, ys, s=2.0, alpha=0.35, linewidths=0)
    radius = float(summary["spot_d90_cm"]) / 2.0
    ax.add_patch(plt.Circle((0.0, 0.0), radius, fill=False, color="tab:red", linewidth=1.4, label="90% diameter"))
    ax.set_aspect("equal", adjustable="box")
    lim = max(2.4, radius * 1.35)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("x at focal plane [cm]")
    ax.set_ylabel("y at focal plane [cm]")
    ax.set_title("511 keV channel optics focal spot")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def run_channel_baseline(
    cfg: ChannelConfig,
    n: int,
    out_dir: str | Path,
    seed: Optional[int] = None,
    config_path: Optional[str | Path] = None,
    reflectivity_table_path: Optional[str | Path] = None,
    theta_policy: str = "fixed",
    fixed_theta_rad: Optional[float] = None,
    stack_id: str = "WSi_30_150",
    ring_theta_rad: Optional[Dict[int, float]] = None,
) -> Dict[str, object]:
    actual_seed = int(seed if seed is not None else cfg.raytrace["seed_default"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reflectivity_table_path is None:
        events = simulate_channel(cfg, n, actual_seed)
        model = cfg.raytrace["model"]
    else:
        table = ReflectivityTable.from_csv(reflectivity_table_path)
        events = simulate_channel_with_reflectivity(
            cfg,
            n,
            table,
            actual_seed,
            theta_policy=theta_policy,
            fixed_theta_rad=fixed_theta_rad,
            stack_id=stack_id,
            ring_theta_rad=ring_theta_rad,
        )
        model = f"reflectivity_table:{Path(reflectivity_table_path).name}:{theta_policy}"
    summary = summarize_events(cfg, events, actual_seed, model=model)
    per_ring_summary = summarize_events_by_ring(cfg, events)
    if reflectivity_table_path is not None:
        summary["reflectivity_table"] = str(reflectivity_table_path)
        summary["theta_policy"] = theta_policy
        summary["fixed_theta_rad"] = fixed_theta_rad
        summary["stack_id"] = stack_id
        if ring_theta_rad is not None:
            summary["ring_theta_rad"] = {str(k): v for k, v in sorted(ring_theta_rad.items())}
        summary["warning"] = (
            "Reflectivity-table mode; validate that the selected grazing-angle policy "
            "matches the physical channel geometry before treating results as a 511-CAM reproduction."
        )
    write_events_csv(out / "all_events.csv", events)
    write_per_ring_summary_csv(out / "per_ring_summary.csv", per_ring_summary)
    write_phase_space_csv(out / "phase_space.csv", events)
    write_optics_history_csv(out / "optics_history.csv", events, cfg)
    plot_focal_spot(out / "focal_spot.png", events, summary)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    with (out / "per_ring_summary.json").open("w") as f:
        json.dump(per_ring_summary, f, indent=2, sort_keys=True)
        f.write("\n")
    if config_path is not None:
        shutil.copyfile(config_path, out / "config_used.yaml")
    return summary
