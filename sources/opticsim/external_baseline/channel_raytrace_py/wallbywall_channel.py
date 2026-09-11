from __future__ import annotations

import csv
import json
import math
import random
import shutil
from bisect import bisect_left
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .geometry import ChannelConfig, Ring, containment_diameter_cm
from .reflectivity_table import ReflectivityParams, ReflectivityTable
from .vector import unit


@dataclass(frozen=True)
class WallByWallOptions:
    seed: int = 20260521
    si_mu_cm_inv: float = 0.20193273411049242
    include_si_path_absorption: bool = True
    support_open_fraction: float = 1.0
    stack_id: str = "WSi_30_150"
    max_bounces: int = 10000
    source_tag: str = "channel_wallbywall_rebuild"


@dataclass(frozen=True)
class WallByWallEvent:
    event_id: int
    E_keV: float
    x_mm: float
    y_mm: float
    z_mm: float
    ux: float
    uy: float
    uz: float
    weight: float
    source_tag: str
    ring_id: int
    tile_id: int
    n_bounce: int
    outcome: str
    mean_grazing_angle_rad: float
    path_length_mm: float


@dataclass(frozen=True)
class WallHit:
    event_id: int
    track_id: int
    optics_kind: str
    stage: str
    ring_id: int
    tile_id: int
    surface_id: str
    E_keV: float
    x_mm: float
    y_mm: float
    z_mm: float
    ux_in: float
    uy_in: float
    uz_in: float
    ux_out: float
    uy_out: float
    uz_out: float
    grazing_angle_rad: float
    p_reflect: float
    p_absorb: float
    p_transmit: float
    n_bounce: int
    weight: float


@dataclass
class _TraceState:
    s_mm: float
    q_mm: float
    alpha_rad: float
    path_length_mm: float = 0.0
    n_bounce: int = 0
    sum_theta_rad: float = 0.0


def simulate_wallbywall_channel(
    cfg: ChannelConfig,
    n: int,
    table: ReflectivityTable,
    options: WallByWallOptions,
) -> Tuple[List[WallByWallEvent], List[WallHit]]:
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = random.Random(options.seed)
    events: List[WallByWallEvent] = []
    history: List[WallHit] = []
    ring_weights = _ring_collecting_area_weights(cfg.rings)
    lookup = _FastReflectivityLookup(table, cfg.energy_keV, options.stack_id)
    for event_id in range(n):
        ring, tile_id, radial_offset_mm, tangent_offset_mm, channel_q_mm, open_ok = _sample_entrance(
            cfg, ring_weights, rng, options
        )
        if not open_ok:
            event, row = _blocked_event(cfg, event_id, ring, tile_id, radial_offset_mm, tangent_offset_mm, options)
            events.append(event)
            history.append(row)
            continue
        event, rows = _trace_one_event(
            cfg,
            event_id,
            ring,
            tile_id,
            radial_offset_mm,
            tangent_offset_mm,
            channel_q_mm,
            lookup,
            rng,
            options,
        )
        events.append(event)
        history.extend(rows)
    return events, history


def summarize_wallbywall(
    cfg: ChannelConfig,
    events: Iterable[WallByWallEvent],
    history: Iterable[WallHit],
    options: WallByWallOptions,
    table_path: str,
) -> Dict[str, object]:
    rows = list(events)
    hit_rows = list(history)
    survived = [row for row in rows if row.outcome == "EXIT"]
    points = [(row.x_mm, row.y_mm) for row in survived]
    n = len(rows)
    n_exit = len(survived)
    n_absorb = sum(1 for row in rows if row.outcome == "ABSORB")
    n_leak = sum(1 for row in rows if row.outcome == "LEAK")
    n_entry_blocked = sum(1 for row in rows if row.outcome == "ENTRY_BLOCKED")
    theta_values = [row.grazing_angle_rad for row in hit_rows if row.stage == "BOUNCE"]
    bounce_counts = [row.n_bounce for row in rows]
    return {
        "system": "channel_wallbywall_rebuild",
        "model": "bilayer_spacer_wall_by_wall_raytrace_v1",
        "schema_version": "channel_optics_summary_v2",
        "model_class": "public_geometry_wallbywall_reconstruction",
        "is_calibrated_handoff": False,
        "is_public_wallbywall_geometry": True,
        "is_first_principles_80pct_closure": False,
        "calibration_target": None,
        "warning": (
            "Wall-by-wall reconstruction using the public 30 nm W / 150 nm Si bilayer geometry. "
            "It does not use calibrated n_bounce or theta values, but it is still a reconstruction "
            "because the original 511-CAM IDL source and exact assembly tolerances are not public."
        ),
        "seed": options.seed,
        "n_primaries": n,
        "n_survived": n_exit,
        "n_absorbed": n_absorb,
        "n_leaked": n_leak,
        "n_entry_blocked": n_entry_blocked,
        "n_wall_bounces": sum(1 for row in hit_rows if row.stage == "BOUNCE"),
        "transmissivity": n_exit / n if n else 0.0,
        "aperture_area_cm2": cfg.aperture_area_cm2,
        "effective_area_cm2": cfg.aperture_area_cm2 * n_exit / n if n else 0.0,
        "spot_d90_cm": containment_diameter_cm(points, 0.9),
        "mean_bounces_per_primary": sum(bounce_counts) / n if n else 0.0,
        "mean_bounces_per_survivor": sum(row.n_bounce for row in survived) / len(survived) if survived else 0.0,
        "max_bounces": max(bounce_counts) if bounce_counts else 0,
        "mean_grazing_angle_rad": sum(theta_values) / len(theta_values) if theta_values else 0.0,
        "min_grazing_angle_rad": min(theta_values) if theta_values else 0.0,
        "max_grazing_angle_rad": max(theta_values) if theta_values else 0.0,
        "spacer_nm": cfg.multilayer.low_Z_thickness_nm,
        "reflector_nm": cfg.multilayer.high_Z_thickness_nm,
        "open_fraction_from_geometry": cfg.multilayer.low_Z_thickness_nm
        / (cfg.multilayer.low_Z_thickness_nm + cfg.multilayer.high_Z_thickness_nm),
        "support_open_fraction": options.support_open_fraction,
        "include_si_path_absorption": options.include_si_path_absorption,
        "si_mu_cm_inv": options.si_mu_cm_inv,
        "reflectivity_table": table_path,
    }


def summarize_wallbywall_by_ring(events: Iterable[WallByWallEvent]) -> List[Dict[str, object]]:
    rows = list(events)
    out: List[Dict[str, object]] = []
    for ring_id in sorted({row.ring_id for row in rows}):
        ring_rows = [row for row in rows if row.ring_id == ring_id]
        n = len(ring_rows)
        survived = [row for row in ring_rows if row.outcome == "EXIT"]
        out.append(
            {
                "ring_id": ring_id,
                "n_primaries": n,
                "n_survived": len(survived),
                "n_absorbed": sum(1 for row in ring_rows if row.outcome == "ABSORB"),
                "n_leaked": sum(1 for row in ring_rows if row.outcome == "LEAK"),
                "n_entry_blocked": sum(1 for row in ring_rows if row.outcome == "ENTRY_BLOCKED"),
                "transmissivity": len(survived) / n if n else 0.0,
                "mean_bounces": sum(row.n_bounce for row in ring_rows) / n if n else 0.0,
                "mean_survivor_bounces": sum(row.n_bounce for row in survived) / len(survived) if survived else 0.0,
                "mean_grazing_angle_rad": (
                    sum(row.mean_grazing_angle_rad for row in ring_rows if row.n_bounce > 0)
                    / max(1, sum(1 for row in ring_rows if row.n_bounce > 0))
                ),
            }
        )
    return out


def write_wallbywall_outputs(
    out_dir: str | Path,
    cfg: ChannelConfig,
    events: Iterable[WallByWallEvent],
    history: Iterable[WallHit],
    summary: Dict[str, object],
    config_path: str | Path | None = None,
) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    event_rows = list(events)
    history_rows = list(history)
    _write_phase_space(out / "phase_space.csv", event_rows)
    _write_history(out / "optics_history.csv", history_rows)
    _write_events(out / "wallbywall_events.csv", event_rows)
    per_ring = summarize_wallbywall_by_ring(event_rows)
    _write_dict_csv(out / "per_ring_summary.csv", per_ring)
    (out / "per_ring_summary.json").write_text(json.dumps(per_ring, indent=2, sort_keys=True) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if config_path is not None:
        shutil.copyfile(config_path, out / "config_used.yaml")


def _ring_collecting_area_weights(rings: Iterable[Ring]) -> List[Tuple[Ring, float]]:
    values = [(ring, ring.width_cm * (ring.thickness_mm / 10.0) * max(1, _default_n_tiles(ring))) for ring in rings]
    total = sum(weight for _, weight in values)
    if total <= 0.0:
        raise ValueError("ring collecting area must be positive")
    return values


class _FastReflectivityLookup:
    def __init__(self, table: ReflectivityTable, energy_keV: float, stack_id: str):
        candidates = [row for row in table.rows if row.stack_id == stack_id]
        if not candidates:
            raise KeyError(f"no rows for stack_id={stack_id!r}")
        if len(candidates) == 1 and _is_declared_toy_or_constant(candidates[0].source):
            self._constant = candidates[0]
            self._rows: List[ReflectivityParams] = []
            self._theta: List[float] = []
            return
        self._constant = None
        nearest_energy = min({row.E_keV for row in candidates}, key=lambda value: abs(value - energy_keV))
        self._rows = sorted((row for row in candidates if row.E_keV == nearest_energy), key=lambda row: row.theta_rad)
        if not self._rows:
            raise ValueError("reflectivity table has no rows at nearest energy")
        self._theta = [row.theta_rad for row in self._rows]

    def lookup(self, theta_rad: float) -> ReflectivityParams:
        if self._constant is not None:
            return self._constant
        tol = 1.0e-12
        if theta_rad < self._theta[0] - tol or theta_rad > self._theta[-1] + tol:
            raise ValueError(
                f"theta_rad={theta_rad} is outside table range [{self._theta[0]}, {self._theta[-1]}]"
            )
        if theta_rad <= self._theta[0] + tol:
            return self._rows[0]
        if theta_rad >= self._theta[-1] - tol:
            return self._rows[-1]
        idx = bisect_left(self._theta, theta_rad)
        lower = self._rows[idx - 1]
        upper = self._rows[idx]
        return _interpolate_reflectivity(lower, upper, theta_rad)


def _is_declared_toy_or_constant(source: str) -> bool:
    normalized = source.lower()
    return "toy" in normalized or "constant" in normalized


def _interpolate_reflectivity(
    lower: ReflectivityParams,
    upper: ReflectivityParams,
    theta_rad: float,
) -> ReflectivityParams:
    if upper.theta_rad == lower.theta_rad:
        return lower
    f = (theta_rad - lower.theta_rad) / (upper.theta_rad - lower.theta_rad)

    def lerp(a: float, b: float) -> float:
        return a + f * (b - a)

    r = lerp(lower.R, upper.R)
    a = lerp(lower.A, upper.A)
    t = lerp(lower.T, upper.T)
    total = r + a + t
    if total > 0.0:
        r, a, t = r / total, a / total, t / total
    return ReflectivityParams(
        stack_id=lower.stack_id,
        E_keV=lower.E_keV,
        theta_rad=theta_rad,
        R=r,
        A=a,
        T=t,
        open_fraction=lerp(lower.open_fraction, upper.open_fraction),
        sigma_slope_rad=lerp(lower.sigma_slope_rad, upper.sigma_slope_rad),
        sigma_rough_nm=lerp(lower.sigma_rough_nm, upper.sigma_rough_nm),
        source=f"{lower.source}:theta_interpolated",
    )


def _default_n_tiles(ring: Ring) -> int:
    circumference_cm = 2.0 * math.pi * ring.radius_cm
    return max(1, int(round(circumference_cm / ring.width_cm)))


def _sample_weighted_ring(ring_weights: List[Tuple[Ring, float]], rng: random.Random) -> Ring:
    total = sum(weight for _, weight in ring_weights)
    threshold = rng.random() * total
    running = 0.0
    for ring, weight in ring_weights:
        running += weight
        if running >= threshold:
            return ring
    return ring_weights[-1][0]


def _sample_entrance(
    cfg: ChannelConfig,
    ring_weights: List[Tuple[Ring, float]],
    rng: random.Random,
    options: WallByWallOptions,
) -> Tuple[Ring, int, float, float, float, bool]:
    ring = _sample_weighted_ring(ring_weights, rng)
    n_tiles = _default_n_tiles(ring)
    tile_id = rng.randrange(n_tiles)
    radial_offset_mm = (rng.random() - 0.5) * ring.thickness_mm
    tangent_offset_mm = (rng.random() - 0.5) * ring.width_cm * 10.0
    period_nm = cfg.multilayer.low_Z_thickness_nm + cfg.multilayer.high_Z_thickness_nm
    cell_nm = rng.random() * period_nm
    open_ok = cell_nm < cfg.multilayer.low_Z_thickness_nm and rng.random() < options.support_open_fraction
    q_mm = (cell_nm / cfg.multilayer.low_Z_thickness_nm - 0.5) * cfg.multilayer.low_Z_thickness_nm * 1.0e-6 if open_ok else 0.0
    return ring, tile_id, radial_offset_mm, tangent_offset_mm, q_mm, open_ok


def _blocked_event(
    cfg: ChannelConfig,
    event_id: int,
    ring: Ring,
    tile_id: int,
    radial_offset_mm: float,
    tangent_offset_mm: float,
    options: WallByWallOptions,
) -> Tuple[WallByWallEvent, WallHit]:
    pos, direction = _global_position_direction(cfg, ring, tile_id, radial_offset_mm, tangent_offset_mm, 0.0, 0.0, 0.0)
    event = WallByWallEvent(
        event_id=event_id,
        E_keV=cfg.energy_keV,
        x_mm=pos[0],
        y_mm=pos[1],
        z_mm=pos[2],
        ux=direction[0],
        uy=direction[1],
        uz=direction[2],
        weight=1.0,
        source_tag=options.source_tag,
        ring_id=ring.id,
        tile_id=tile_id,
        n_bounce=0,
        outcome="ENTRY_BLOCKED",
        mean_grazing_angle_rad=0.0,
        path_length_mm=0.0,
    )
    hit = WallHit(
        event_id=event_id,
        track_id=1,
        optics_kind="CHANNEL",
        stage="LEAK",
        ring_id=ring.id,
        tile_id=tile_id,
        surface_id="entry_closed_fraction",
        E_keV=cfg.energy_keV,
        x_mm=pos[0],
        y_mm=pos[1],
        z_mm=pos[2],
        ux_in=0.0,
        uy_in=0.0,
        uz_in=1.0,
        ux_out=0.0,
        uy_out=0.0,
        uz_out=1.0,
        grazing_angle_rad=0.0,
        p_reflect=0.0,
        p_absorb=0.0,
        p_transmit=1.0,
        n_bounce=0,
        weight=1.0,
    )
    return event, hit


def _trace_one_event(
    cfg: ChannelConfig,
    event_id: int,
    ring: Ring,
    tile_id: int,
    radial_offset_mm: float,
    tangent_offset_mm: float,
    q0_mm: float,
    lookup: "_FastReflectivityLookup",
    rng: random.Random,
    options: WallByWallOptions,
) -> Tuple[WallByWallEvent, List[WallHit]]:
    state = _TraceState(s_mm=0.0, q_mm=q0_mm, alpha_rad=0.0)
    rows: List[WallHit] = []
    length_mm = ring.length_cm * 10.0
    half_gap_mm = 0.5 * cfg.multilayer.low_Z_thickness_nm * 1.0e-6
    curvature = math.radians(ring.bending_angle_deg) / length_mm
    outcome = "EXIT"
    last_stage = "EXIT"
    while state.s_mm < length_mm and state.n_bounce < options.max_bounces:
        hit = _next_wall_hit(state, half_gap_mm, curvature, length_mm)
        if hit is None:
            break
        ds_mm, wall_sign = hit
        theta_hit = state.alpha_rad + curvature * ds_mm
        state.path_length_mm += ds_mm / max(1.0e-12, math.cos(theta_hit))
        state.s_mm += ds_mm
        state.q_mm = wall_sign * half_gap_mm

        pos, direction_in = _global_position_direction(
            cfg, ring, tile_id, radial_offset_mm, tangent_offset_mm, state.s_mm, state.q_mm, theta_hit
        )

        if options.include_si_path_absorption:
            path_survival = math.exp(-options.si_mu_cm_inv * (ds_mm / 10.0))
            if rng.random() > path_survival:
                rows.append(
                    _history_row(
                        event_id,
                        ring,
                        tile_id,
                        "ABSORB",
                        "si_spacer_path",
                        pos,
                        direction_in,
                        direction_in,
                        abs(theta_hit),
                        0.0,
                        1.0 - path_survival,
                        path_survival,
                        state.n_bounce + 1,
                        cfg.energy_keV,
                    )
                )
                outcome = "ABSORB"
                last_stage = "ABSORB"
                break

        params = lookup.lookup(abs(theta_hit))
        u = rng.random()
        if u < params.A:
            rows.append(
                _history_row(
                    event_id,
                    ring,
                    tile_id,
                    "ABSORB",
                    f"wall_{'outer' if wall_sign > 0 else 'inner'}",
                    pos,
                    direction_in,
                    direction_in,
                    abs(theta_hit),
                    params.R,
                    params.A,
                    params.T,
                    state.n_bounce + 1,
                    cfg.energy_keV,
                )
            )
            outcome = "ABSORB"
            last_stage = "ABSORB"
            break
        if u >= params.A + params.R:
            rows.append(
                _history_row(
                    event_id,
                    ring,
                    tile_id,
                    "LEAK",
                    f"wall_{'outer' if wall_sign > 0 else 'inner'}",
                    pos,
                    direction_in,
                    direction_in,
                    abs(theta_hit),
                    params.R,
                    params.A,
                    params.T,
                    state.n_bounce + 1,
                    cfg.energy_keV,
                )
            )
            outcome = "LEAK"
            last_stage = "LEAK"
            break

        reflected_alpha = -theta_hit
        _, direction_out = _global_position_direction(
            cfg, ring, tile_id, radial_offset_mm, tangent_offset_mm, state.s_mm, state.q_mm, reflected_alpha
        )
        state.n_bounce += 1
        state.sum_theta_rad += abs(theta_hit)
        rows.append(
            _history_row(
                event_id,
                ring,
                tile_id,
                "BOUNCE",
                f"wall_{'outer' if wall_sign > 0 else 'inner'}",
                pos,
                direction_in,
                direction_out,
                abs(theta_hit),
                params.R,
                params.A,
                params.T,
                state.n_bounce,
                cfg.energy_keV,
            )
        )
        state.alpha_rad = reflected_alpha
        state.q_mm = wall_sign * (half_gap_mm - 1.0e-12)

    if state.n_bounce >= options.max_bounces and outcome == "EXIT":
        outcome = "LEAK"
        last_stage = "LEAK"

    if outcome == "EXIT":
        remaining = length_mm - state.s_mm
        final_q_mm = state.q_mm + state.alpha_rad * remaining + 0.5 * curvature * remaining * remaining
        final_alpha_rad = state.alpha_rad + curvature * remaining
        state.path_length_mm += remaining / max(1.0e-12, math.cos(final_alpha_rad))
        if options.include_si_path_absorption:
            path_survival = math.exp(-options.si_mu_cm_inv * (remaining / 10.0))
            if rng.random() > path_survival:
                state.s_mm = length_mm
                state.q_mm = final_q_mm
                state.alpha_rad = final_alpha_rad
                pos, direction_abs = _global_position_direction(
                    cfg, ring, tile_id, radial_offset_mm, tangent_offset_mm, state.s_mm, state.q_mm, state.alpha_rad
                )
                rows.append(
                    _history_row(
                        event_id,
                        ring,
                        tile_id,
                        "ABSORB",
                        "si_spacer_exit_path",
                        pos,
                        direction_abs,
                        direction_abs,
                        abs(state.alpha_rad),
                        0.0,
                        1.0 - path_survival,
                        path_survival,
                        state.n_bounce,
                        cfg.energy_keV,
                    )
                )
                outcome = "ABSORB"
                last_stage = "ABSORB"
            else:
                state.q_mm = final_q_mm
                state.alpha_rad = final_alpha_rad
                state.s_mm = length_mm
        else:
            state.q_mm = final_q_mm
            state.alpha_rad = final_alpha_rad
            state.s_mm = length_mm

    pos, direction = _global_position_direction(
        cfg, ring, tile_id, radial_offset_mm, tangent_offset_mm, state.s_mm, state.q_mm, state.alpha_rad
    )
    if outcome == "EXIT" and direction[2] > 0.0:
        t_mm = (cfg.focal_length_mm - pos[2]) / direction[2]
        x_mm = pos[0] + direction[0] * t_mm
        y_mm = pos[1] + direction[1] * t_mm
        z_mm = cfg.focal_length_mm
    else:
        x_mm, y_mm, z_mm = pos
    if outcome == "EXIT":
        rows.append(
            _history_row(
                event_id,
                ring,
                tile_id,
                "EXIT",
                "channel_exit",
                pos,
                direction,
                direction,
                abs(state.alpha_rad),
                1.0,
                0.0,
                0.0,
                state.n_bounce,
                cfg.energy_keV,
            )
        )
    event = WallByWallEvent(
        event_id=event_id,
        E_keV=cfg.energy_keV,
        x_mm=x_mm,
        y_mm=y_mm,
        z_mm=z_mm,
        ux=direction[0],
        uy=direction[1],
        uz=direction[2],
        weight=1.0,
        source_tag=options.source_tag,
        ring_id=ring.id,
        tile_id=tile_id,
        n_bounce=state.n_bounce,
        outcome=outcome if last_stage != "EXIT" else "EXIT",
        mean_grazing_angle_rad=state.sum_theta_rad / state.n_bounce if state.n_bounce else 0.0,
        path_length_mm=state.path_length_mm,
    )
    return event, rows


def _next_wall_hit(
    state: _TraceState,
    half_gap_mm: float,
    curvature_rad_per_mm: float,
    length_mm: float,
) -> Optional[Tuple[float, int]]:
    candidates: List[Tuple[float, int]] = []
    for wall_sign in (-1, 1):
        c = state.q_mm - wall_sign * half_gap_mm
        a = 0.5 * curvature_rad_per_mm
        b = state.alpha_rad
        roots = _positive_roots(a, b, c)
        for root in roots:
            if root > 1.0e-10 and state.s_mm + root <= length_mm + 1.0e-9:
                candidates.append((root, wall_sign))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])


def _positive_roots(a: float, b: float, c: float) -> List[float]:
    if abs(a) < 1.0e-18:
        if abs(b) < 1.0e-18:
            return []
        return [-c / b] if -c / b > 0.0 else []
    disc = b * b - 4.0 * a * c
    if disc < -1.0e-18:
        return []
    disc = max(0.0, disc)
    sq = math.sqrt(disc)
    roots = [(-b - sq) / (2.0 * a), (-b + sq) / (2.0 * a)]
    return [root for root in roots if root > 0.0 and math.isfinite(root)]


def _global_position_direction(
    cfg: ChannelConfig,
    ring: Ring,
    tile_id: int,
    radial_offset_mm: float,
    tangent_offset_mm: float,
    s_mm: float,
    q_mm: float,
    alpha_rad: float,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    length_mm = ring.length_cm * 10.0
    bend = math.radians(ring.bending_angle_deg)
    curvature = bend / length_mm
    theta = curvature * s_mm
    if abs(curvature) < 1.0e-18:
        center_r_mm = ring.radius_cm * 10.0 + radial_offset_mm
        z_mm = s_mm
    else:
        center_r_mm = ring.radius_cm * 10.0 + radial_offset_mm + (math.cos(theta) - 1.0) / curvature
        z_mm = math.sin(theta) / curvature
    phi = 2.0 * math.pi * tile_id / max(1, _default_n_tiles(ring))
    local_tangent = (-math.sin(theta), math.cos(theta))
    local_normal = (math.cos(theta), math.sin(theta))
    r_mm = center_r_mm + q_mm * local_normal[0]
    z_mm = z_mm + q_mm * local_normal[1]
    x_mm = r_mm * math.cos(phi) - tangent_offset_mm * math.sin(phi)
    y_mm = r_mm * math.sin(phi) + tangent_offset_mm * math.cos(phi)

    k_r = math.cos(alpha_rad) * local_tangent[0] + math.sin(alpha_rad) * local_normal[0]
    k_z = math.cos(alpha_rad) * local_tangent[1] + math.sin(alpha_rad) * local_normal[1]
    direction = unit((k_r * math.cos(phi), k_r * math.sin(phi), k_z))
    return (x_mm, y_mm, z_mm), direction


def _history_row(
    event_id: int,
    ring: Ring,
    tile_id: int,
    stage: str,
    surface_id: str,
    pos: Tuple[float, float, float],
    direction_in: Tuple[float, float, float],
    direction_out: Tuple[float, float, float],
    theta_rad: float,
    p_reflect: float,
    p_absorb: float,
    p_transmit: float,
    bounce_index: int,
    energy_keV: float,
) -> WallHit:
    return WallHit(
        event_id=event_id,
        track_id=1,
        optics_kind="CHANNEL",
        stage=stage,
        ring_id=ring.id,
        tile_id=tile_id,
        surface_id=surface_id,
        E_keV=energy_keV,
        x_mm=pos[0],
        y_mm=pos[1],
        z_mm=pos[2],
        ux_in=direction_in[0],
        uy_in=direction_in[1],
        uz_in=direction_in[2],
        ux_out=direction_out[0],
        uy_out=direction_out[1],
        uz_out=direction_out[2],
        grazing_angle_rad=theta_rad,
        p_reflect=p_reflect,
        p_absorb=p_absorb,
        p_transmit=p_transmit,
        n_bounce=bounce_index,
        weight=1.0,
    )


def _write_phase_space(path: Path, events: Iterable[WallByWallEvent]) -> None:
    fields = [
        "event_id",
        "E_keV",
        "x_mm",
        "y_mm",
        "z_mm",
        "ux",
        "uy",
        "uz",
        "weight",
        "source_tag",
        "particle_name",
        "pdg_encoding",
        "track_id",
        "parent_id",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for event in events:
            if event.outcome != "EXIT":
                continue
            row = {
                "event_id": event.event_id,
                "E_keV": event.E_keV,
                "x_mm": event.x_mm,
                "y_mm": event.y_mm,
                "z_mm": event.z_mm,
                "ux": event.ux,
                "uy": event.uy,
                "uz": event.uz,
                "weight": event.weight,
                "source_tag": event.source_tag,
                "particle_name": "gamma",
                "pdg_encoding": 22,
                "track_id": 1,
                "parent_id": 0,
            }
            writer.writerow(row)


def _write_history(path: Path, history: Iterable[WallHit]) -> None:
    fields = list(WallHit.__dataclass_fields__.keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in history)


def _write_events(path: Path, events: Iterable[WallByWallEvent]) -> None:
    fields = list(WallByWallEvent.__dataclass_fields__.keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in events)


def _write_dict_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
