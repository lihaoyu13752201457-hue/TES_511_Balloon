"""Bent-channel multilayer tracer for CAM511-style channeling optics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Callable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.geometry import Ring
    from src.materials import (
        fresnel_surface_reflectivity,
        material_density,
        optical_constants_from_xraydb,
        roughness_factor_nevot_croce,
    )
else:
    from .geometry import Ring
    from .materials import (
        fresnel_surface_reflectivity,
        material_density,
        optical_constants_from_xraydb,
        roughness_factor_nevot_croce,
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bent-channel CAM511 tracer")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/bent_channel", help="Output directory")
    ap.add_argument("--n-rays", type=int, default=None, help="Override number of rays")
    ap.add_argument("--seed", type=int, default=None, help="Override RNG seed")
    ap.add_argument("--offaxis-x-arcmin", type=float, default=0.0, help="Off-axis source angle in x")
    ap.add_argument("--offaxis-y-arcmin", type=float, default=0.0, help="Off-axis source angle in y")
    return ap.parse_args()


def arcmin_to_rad(v: float) -> float:
    return math.radians(v / 60.0)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    cdf = np.cumsum(w)
    if cdf[-1] <= 0.0:
        return float(np.quantile(values, q))
    target = q * cdf[-1]
    idx = int(np.searchsorted(cdf, target, side="left"))
    idx = min(idx, len(v) - 1)
    return float(v[idx])


def interp_lookup(alpha_mrad: float, points: list[list[float]]) -> float:
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    if alpha_mrad <= xs[0]:
        return float(ys[0])
    if alpha_mrad >= xs[-1]:
        return float(ys[-1])
    return float(np.interp(alpha_mrad, xs, ys))


def load_reflectivity_table(path: Path) -> dict[str, Any]:
    rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "energy_keV": float(row["energy_keV"]),
                    "alpha_mrad": float(row["alpha_mrad"]),
                    "R_multilayer": float(row["R_multilayer"]),
                }
            )
    if not rows:
        raise ValueError(f"empty reflectivity table: {path}")
    energy_arr = np.array([row["energy_keV"] for row in rows], dtype=float)
    alpha_arr = np.array([row["alpha_mrad"] for row in rows], dtype=float)
    refl_arr = np.array([row["R_multilayer"] for row in rows], dtype=float)
    energies = np.unique(energy_arr)
    alpha_grids: list[np.ndarray] = []
    refl_grids: list[np.ndarray] = []
    for energy in energies:
        sub = energy_arr == energy
        order = np.argsort(alpha_arr[sub])
        alpha_grid = alpha_arr[sub][order]
        refl_grid = refl_arr[sub][order]
        if np.any(~np.isfinite(alpha_grid)) or np.any(~np.isfinite(refl_grid)):
            raise ValueError(f"non-finite values in reflectivity table: {path}")
        if np.any(np.diff(alpha_grid) <= 0.0):
            raise ValueError(f"alpha grid must be strictly increasing for energy={energy:g} keV")
        alpha_grids.append(alpha_grid)
        refl_grids.append(np.clip(refl_grid, 0.0, 1.0))

    common_alpha_grid = alpha_grids[0]
    if not all(grid.shape == common_alpha_grid.shape and np.allclose(grid, common_alpha_grid) for grid in alpha_grids):
        common_alpha_grid = None
    return {
        "energies": energies,
        "alpha_grids": alpha_grids,
        "refl_grids": refl_grids,
        "common_alpha_grid": common_alpha_grid,
    }


def interpolate_reflectivity(table: dict[str, Any], energy_keV: float, alpha_rad: float) -> float:
    alpha_mrad = max(float(alpha_rad) * 1.0e3, 0.0)
    energies = table["energies"]
    if len(energies) == 1:
        alphas = table["alpha_grids"][0]
        refl = table["refl_grids"][0]
        value = np.interp(alpha_mrad, alphas, refl, left=refl[0], right=refl[-1])
        return float(np.clip(value, 0.0, 1.0))

    energy_keV = float(np.clip(energy_keV, energies[0], energies[-1]))
    hi_idx = int(np.searchsorted(energies, energy_keV, side="left"))
    if hi_idx == 0:
        e0 = e1 = energies[0]
    elif hi_idx >= len(energies):
        e0 = e1 = energies[-1]
    else:
        e0 = energies[hi_idx - 1]
        e1 = energies[hi_idx]

    def interp_at_index(index: int) -> float:
        alphas = table["alpha_grids"][index]
        refl = table["refl_grids"][index]
        return float(np.interp(alpha_mrad, alphas, refl, left=refl[0], right=refl[-1]))

    i0 = int(np.searchsorted(energies, e0))
    i1 = int(np.searchsorted(energies, e1))
    r0 = interp_at_index(i0)
    r1 = interp_at_index(i1)
    if e1 == e0:
        return float(np.clip(r0, 0.0, 1.0))
    frac = (energy_keV - e0) / (e1 - e0)
    return float(np.clip(r0 + frac * (r1 - r0), 0.0, 1.0))


def make_reflectivity_table_func(table: dict[str, Any], energy_keV: float) -> Callable[[float, float], float]:
    """Freeze the table at the run energy and return a fast per-bounce lookup."""
    energies = table["energies"]
    common_alpha_grid = table.get("common_alpha_grid")
    if common_alpha_grid is None:
        return lambda e, a: interpolate_reflectivity(table, e, a)

    if len(energies) == 1 or energy_keV <= float(energies[0]):
        refl_grid = np.array(table["refl_grids"][0], dtype=float, copy=True)
    elif energy_keV >= float(energies[-1]):
        refl_grid = np.array(table["refl_grids"][-1], dtype=float, copy=True)
    else:
        hi_idx = int(np.searchsorted(energies, energy_keV, side="left"))
        lo_idx = hi_idx - 1
        e0 = float(energies[lo_idx])
        e1 = float(energies[hi_idx])
        frac = (float(energy_keV) - e0) / (e1 - e0)
        refl_grid = (1.0 - frac) * table["refl_grids"][lo_idx] + frac * table["refl_grids"][hi_idx]
        refl_grid = np.clip(refl_grid, 0.0, 1.0)

    alpha_grid = np.asarray(common_alpha_grid, dtype=float)
    if len(alpha_grid) < 2 or alpha_grid[0] <= 0.0:
        return lambda _e, a: float(np.interp(max(float(a) * 1.0e3, 0.0), alpha_grid, refl_grid, left=refl_grid[0], right=refl_grid[-1]))

    log_alpha = np.log(alpha_grid)
    log_steps = np.diff(log_alpha)
    if not np.allclose(log_steps, log_steps[0], rtol=1.0e-5, atol=1.0e-12):
        return lambda _e, a: float(np.interp(max(float(a) * 1.0e3, 0.0), alpha_grid, refl_grid, left=refl_grid[0], right=refl_grid[-1]))

    alpha_min = float(alpha_grid[0])
    alpha_max = float(alpha_grid[-1])
    log_min = float(log_alpha[0])
    inv_log_step = 1.0 / float(log_steps[0])
    n = len(alpha_grid)

    def lookup(_energy_keV: float, alpha_rad: float) -> float:
        alpha_mrad = float(alpha_rad) * 1.0e3
        if alpha_mrad <= alpha_min:
            return float(refl_grid[0])
        if alpha_mrad >= alpha_max:
            return float(refl_grid[-1])
        idx = int((math.log(alpha_mrad) - log_min) * inv_log_step)
        if idx < 0:
            return float(refl_grid[0])
        if idx >= n - 1:
            return float(refl_grid[-1])
        x0 = float(alpha_grid[idx])
        x1 = float(alpha_grid[idx + 1])
        y0 = float(refl_grid[idx])
        y1 = float(refl_grid[idx + 1])
        value = y0 + ((alpha_mrad - x0) / (x1 - x0)) * (y1 - y0)
        if value <= 0.0:
            return 0.0
        if value >= 1.0:
            return 1.0
        return float(value)

    return lookup


def sample_rings(cfg: dict, rng: np.random.Generator, n: int) -> tuple[np.ndarray, list[Ring], np.ndarray]:
    rings = [Ring(**r) for r in cfg["rings"]]
    aperture_area = np.array([2.0 * math.pi * r.radius_mm * r.segment_thickness_mm for r in rings], dtype=float)
    probs = aperture_area / aperture_area.sum()
    idx = rng.choice(len(rings), size=n, p=probs)
    return idx, rings, probs


def sample_segment_geometry(ring: Ring, rng: np.random.Generator) -> tuple[float, float, int]:
    n_segments = max(1, int(round((2.0 * math.pi * ring.radius_mm) / ring.segment_width_mm)))
    seg_idx = int(rng.integers(0, n_segments))
    phi_center = 2.0 * math.pi * (seg_idx + 0.5) / n_segments
    tangential_offset_mm = rng.uniform(-0.5 * ring.segment_width_mm, 0.5 * ring.segment_width_mm)
    return phi_center, tangential_offset_mm, n_segments


def next_wall_intersection(u: float, p: float, kappa: float, gap_mm: float) -> tuple[float | None, float | None]:
    half_gap = 0.5 * gap_mm
    roots: list[tuple[float, float]] = []
    a = 0.5 * kappa
    for target in (-half_gap, half_gap):
        c = u - target
        if abs(a) < 1.0e-18:
            if abs(p) < 1.0e-18:
                continue
            ds = -c / p
            if ds > 1.0e-18:
                roots.append((ds, target))
            continue
        disc = p * p - 4.0 * a * c
        if disc < 0.0:
            continue
        root = math.sqrt(disc)
        for ds in ((-p - root) / (2.0 * a), (-p + root) / (2.0 * a)):
            if ds > 1.0e-18:
                roots.append((ds, target))
    if not roots:
        return None, None
    ds, target = min(roots, key=lambda item: item[0])
    return ds, target


def centerline_state(r0_mm: float, bend_angle_rad: float, length_mm: float, s_mm: float) -> tuple[float, float, float]:
    if abs(bend_angle_rad) < 1.0e-18:
        return r0_mm, s_mm, 0.0
    radius_curv_mm = length_mm / bend_angle_rad
    theta = bend_angle_rad * (s_mm / length_mm)
    x_c = r0_mm - radius_curv_mm * (1.0 - math.cos(theta))
    z_c = radius_curv_mm * math.sin(theta)
    return x_c, z_c, theta


def trace_one_ray(
    channel_radius_mm: float,
    bend_angle_rad: float,
    phi: float,
    tangential_offset_mm: float,
    p0: float,
    u0_mm: float,
    gap_mm: float,
    length_mm: float,
    z_fp_mm: float,
    energy_keV: float,
    wall_optics,
    reflectivity_func: Callable[[float, float], float],
    roughness_nm: float,
    radial_exit_sigma_mrad: float,
    tangential_exit_sigma_mrad: float,
    rng: np.random.Generator,
    max_bounces: int,
) -> dict[str, float]:
    kappa = bend_angle_rad / length_mm
    s = 0.0
    u = u0_mm
    p = p0
    weight = 1.0
    bounces = 0
    last_alpha = abs(p0)
    alpha_sum = 0.0
    alpha_max = 0.0

    while s < length_mm and bounces < max_bounces and weight > 0.0:
        ds_hit, target = next_wall_intersection(u, p, kappa, gap_mm)
        ds_exit = length_mm - s
        if ds_hit is None or ds_hit >= ds_exit:
            u = u + p * ds_exit + 0.5 * kappa * ds_exit * ds_exit
            p = p + kappa * ds_exit
            s = length_mm
            break

        u = float(target)
        p_hit = p + kappa * ds_hit
        alpha = abs(p_hit)
        refl = reflectivity_func(energy_keV, alpha)
        weight *= refl
        bounces += 1
        s += ds_hit
        p = -p_hit
        last_alpha = alpha
        alpha_sum += alpha
        alpha_max = max(alpha_max, alpha)

    x_c, z_c, theta_c = centerline_state(channel_radius_mm, bend_angle_rad, length_mm, s)
    x_local = x_c + u * math.cos(theta_c)
    z_local = z_c + u * math.sin(theta_c)

    d_x_local = -math.sin(theta_c) + p * math.cos(theta_c)
    d_z_local = math.cos(theta_c) + p * math.sin(theta_c)
    norm = math.hypot(d_x_local, d_z_local)
    d_x_local /= norm
    d_z_local /= norm

    delta_radial = rng.normal(0.0, radial_exit_sigma_mrad * 1.0e-3) if radial_exit_sigma_mrad > 0.0 else 0.0
    delta_tangential = rng.normal(0.0, tangential_exit_sigma_mrad * 1.0e-3) if tangential_exit_sigma_mrad > 0.0 else 0.0

    x_global = x_local * math.cos(phi)
    y_global = x_local * math.sin(phi)
    x_global += -tangential_offset_mm * math.sin(phi)
    y_global += tangential_offset_mm * math.cos(phi)
    d_x = (d_x_local + delta_radial) * math.cos(phi) - delta_tangential * math.sin(phi)
    d_y = (d_x_local + delta_radial) * math.sin(phi) + delta_tangential * math.cos(phi)
    d_z = d_z_local
    d_norm = math.sqrt(d_x * d_x + d_y * d_y + d_z * d_z)
    d_x /= d_norm
    d_y /= d_norm
    d_z /= d_norm

    t_fp = (z_fp_mm - z_local) / d_z
    x_fp = x_global + t_fp * d_x
    y_fp = y_global + t_fp * d_y
    fp_radial_mm = x_fp * math.cos(phi) + y_fp * math.sin(phi)
    fp_tangential_mm = -x_fp * math.sin(phi) + y_fp * math.cos(phi)

    return {
        "channel_radius_mm": channel_radius_mm,
        "tangential_offset_mm": tangential_offset_mm,
        "x_exit_mm": x_global,
        "y_exit_mm": y_global,
        "z_exit_mm": z_local,
        "x_fp_mm": x_fp,
        "y_fp_mm": y_fp,
        "fp_radial_mm": fp_radial_mm,
        "fp_tangential_mm": fp_tangential_mm,
        "dir_out_x": d_x,
        "dir_out_y": d_y,
        "dir_out_z": d_z,
        "final_u_nm": u * 1.0e6,
        "final_p_mrad": p * 1.0e3,
        "last_alpha_mrad": last_alpha * 1.0e3,
        "mean_alpha_mrad": (alpha_sum / bounces) * 1.0e3 if bounces > 0 else abs(p0) * 1.0e3,
        "max_alpha_mrad": alpha_max * 1.0e3,
        "radial_exit_perturb_mrad": delta_radial * 1.0e3,
        "tangential_exit_perturb_mrad": delta_tangential * 1.0e3,
        "bounce_count": float(bounces),
        "reflectivity_product": weight,
    }


def write_csv(path: Path, rows: dict[str, np.ndarray]) -> None:
    headers = list(rows.keys())
    n = len(next(iter(rows.values())))
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(n):
            row = []
            for h in headers:
                v = rows[h][i]
                if isinstance(v, (np.floating, float)):
                    row.append(f"{float(v):.8g}")
                elif isinstance(v, (np.integer, int)):
                    row.append(int(v))
                else:
                    row.append(str(v))
            writer.writerow(row)


def make_plots(outdir: Path, rows: dict[str, np.ndarray], summary: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), constrained_layout=True)
    sc = axes[0].scatter(rows["x_fp_mm"], rows["y_fp_mm"], c=rows["bounce_count"], s=2.0, alpha=0.35, cmap="plasma")
    axes[0].set_xlabel("x [mm]")
    axes[0].set_ylabel("y [mm]")
    axes[0].set_title("Focal-plane map colored by bounce count")
    axes[0].set_aspect("equal")
    fig.colorbar(sc, ax=axes[0], label="Bounce count")

    axes[1].hist(rows["last_alpha_mrad"], bins=80, weights=rows["effective_area_term_mm2"], color="#2563eb", alpha=0.8)
    axes[1].set_xlabel("Last grazing angle [mrad]")
    axes[1].set_ylabel("Weighted area contribution [mm²]")
    axes[1].set_title("Weighted grazing-angle distribution")
    fig.savefig(outdir / "bent_channel_overview.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.8, 4.8), constrained_layout=True)
    ax.hist(rows["bounce_count"], bins=np.arange(rows["bounce_count"].max() + 2) - 0.5, weights=rows["effective_area_term_mm2"], color="#7c3aed", alpha=0.8)
    ax.set_xlabel("Bounce count")
    ax.set_ylabel("Weighted area contribution [mm²]")
    ax.set_title("Bounce-count contribution")
    fig.savefig(outdir / "bounce_hist.png", dpi=180)
    plt.close(fig)


def make_summary(cfg: dict, args: argparse.Namespace, rows: dict[str, np.ndarray]) -> dict:
    f_mm = float(cfg["focus_length_m"]) * 1000.0
    x0 = f_mm * math.tan(arcmin_to_rad(float(args.offaxis_x_arcmin)))
    y0 = f_mm * math.tan(arcmin_to_rad(float(args.offaxis_y_arcmin)))
    r = np.sqrt((rows["x_fp_mm"] - x0) ** 2 + (rows["y_fp_mm"] - y0) ** 2)
    w = rows["effective_area_term_mm2"]
    wsum = float(np.sum(w))
    radial_center = float(np.sum(rows["fp_radial_mm"] * w) / wsum) if wsum > 0.0 else float(np.mean(rows["fp_radial_mm"]))
    tangential_center = float(np.sum(rows["fp_tangential_mm"] * w) / wsum) if wsum > 0.0 else float(np.mean(rows["fp_tangential_mm"]))
    radial_abs = np.abs(rows["fp_radial_mm"] - radial_center)
    tangential_abs = np.abs(rows["fp_tangential_mm"] - tangential_center)
    transport_cfg = cfg.get("transport", {})

    return {
        "focus_length_m": float(cfg["focus_length_m"]),
        "energy_keV": float(cfg["energy_keV"]),
        "offaxis_x_arcmin": float(args.offaxis_x_arcmin),
        "offaxis_y_arcmin": float(args.offaxis_y_arcmin),
        "weighted_r50_mm": weighted_quantile(r, w, 0.50),
        "weighted_r68_mm": weighted_quantile(r, w, 0.68),
        "weighted_r90_mm": weighted_quantile(r, w, 0.90),
        "weighted_r95_mm": weighted_quantile(r, w, 0.95),
        "weighted_hpd_diameter_mm": 2.0 * weighted_quantile(r, w, 0.50),
        "weighted_hpd_arcmin": math.degrees((2.0 * weighted_quantile(r, w, 0.50)) / f_mm) * 60.0,
        "estimated_effective_area_cm2": float(np.sum(w) / 100.0),
        "mean_bounce_count": float(np.average(rows["bounce_count"], weights=np.maximum(w, 1.0e-30))),
        "max_bounce_count": int(np.max(rows["bounce_count"])),
        "median_last_alpha_mrad": float(np.median(rows["last_alpha_mrad"])),
        "weighted_radial_fullwidth95_mm": 2.0 * weighted_quantile(radial_abs, w, 0.95),
        "weighted_tangential_fullwidth95_mm": 2.0 * weighted_quantile(tangential_abs, w, 0.95),
        "open_fraction": float(cfg["multilayer"]["channel_gap_nm"] / cfg["multilayer"]["period_nm"]),
        "periods": int(cfg["multilayer"]["periods"]),
        "roughness_nm": float(cfg["multilayer"].get("roughness_nm", 0.0)),
        "weight_model": transport_cfg.get("weight_model", "surface_product"),
        "radial_exit_sigma_mrad": float(transport_cfg.get("radial_exit_sigma_mrad", 0.0)),
        "tangential_exit_sigma_mrad": float(transport_cfg.get("tangential_exit_sigma_mrad", 0.0)),
        "cam511_calibration_used": bool(transport_cfg.get("cam511_calibration_used", transport_cfg.get("weight_model") == "effective_lookup")),
        "use_effective_lookup": bool(transport_cfg.get("use_effective_lookup", transport_cfg.get("weight_model") == "effective_lookup")),
        "reflectivity_table": transport_cfg.get("reflectivity_table", ""),
        "n_rays": int(len(rows["x_fp_mm"])),
        "model_note": "Bent-channel paraxial billiard with configurable transport weighting and optional radial/tangential exit-angle spread.",
    }


def run(cfg: dict, args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict]:
    energy_keV = float(cfg["energy_keV"])
    z_fp_mm = float(cfg.get("focal_plane_z_mm", float(cfg["focus_length_m"]) * 1000.0))
    trace_cfg = cfg["trace"]
    n_rays = int(args.n_rays if args.n_rays is not None else trace_cfg["n_rays"])
    seed = int(args.seed if args.seed is not None else trace_cfg["seed"])
    max_bounces = int(trace_cfg["max_bounces"])
    rng = np.random.default_rng(seed)

    wall_material = cfg["multilayer"].get("material_a", "W")
    wall_optics = optical_constants_from_xraydb(wall_material, material_density(wall_material), energy_keV)
    roughness_nm = float(cfg["multilayer"].get("roughness_nm", 0.0))
    transport_cfg = cfg.get("transport", {})
    weight_model = transport_cfg.get("weight_model", "surface_product")
    radial_exit_sigma_mrad = float(transport_cfg.get("radial_exit_sigma_mrad", 0.0))
    tangential_exit_sigma_mrad = float(transport_cfg.get("tangential_exit_sigma_mrad", 0.0))
    effective_lookup = transport_cfg.get("effective_reflectivity_lookup", [])
    reflectivity_table_path = transport_cfg.get("reflectivity_table", "")
    reflectivity_table: dict[str, Any] | None = None
    if weight_model == "multilayer_table":
        if not reflectivity_table_path:
            raise ValueError("weight_model=multilayer_table requires transport.reflectivity_table")
        reflectivity_table = load_reflectivity_table(Path(reflectivity_table_path))
        reflectivity_func = make_reflectivity_table_func(reflectivity_table, energy_keV)
    elif weight_model in {"surface_product", "effective_lookup"}:
        reflectivity_func = lambda e, a: fresnel_surface_reflectivity(wall_optics, a) * roughness_factor_nevot_croce(roughness_nm, e, a)
    else:
        raise ValueError(f"unsupported weight_model={weight_model!r}")
    ring_idx, rings, ring_probs = sample_rings(cfg, rng, n_rays)

    gap_mm = float(cfg["multilayer"]["channel_gap_nm"]) * 1.0e-6
    open_fraction = float(cfg["multilayer"]["channel_gap_nm"] / cfg["multilayer"]["period_nm"])

    theta_x = arcmin_to_rad(float(args.offaxis_x_arcmin))
    theta_y = arcmin_to_rad(float(args.offaxis_y_arcmin))

    rows_list: list[dict[str, float]] = []
    for j in range(n_rays):
        ring = rings[ring_idx[j]]
        phi_center, tangential_offset_mm, n_segments = sample_segment_geometry(ring, rng)
        bend_angle_rad = math.radians(float(getattr(ring, "bending_angle_deg", cfg["rings"][ring_idx[j]].get("bending_angle_deg", 0.0))))
        theta_r = theta_x * math.cos(phi_center) + theta_y * math.sin(phi_center)
        u0_mm = rng.uniform(-0.5 * gap_mm, 0.5 * gap_mm)
        channel_offset_mm = rng.uniform(-0.5 * ring.segment_thickness_mm, 0.5 * ring.segment_thickness_mm)
        channel_radius_mm = ring.radius_mm + channel_offset_mm
        ray = trace_one_ray(
            channel_radius_mm=float(channel_radius_mm),
            bend_angle_rad=bend_angle_rad,
            phi=float(phi_center),
            tangential_offset_mm=float(tangential_offset_mm),
            p0=float(theta_r),
            u0_mm=float(u0_mm),
            gap_mm=gap_mm,
            length_mm=float(ring.segment_length_mm),
            z_fp_mm=z_fp_mm,
            energy_keV=energy_keV,
            wall_optics=wall_optics,
            reflectivity_func=reflectivity_func,
            roughness_nm=roughness_nm,
            radial_exit_sigma_mrad=radial_exit_sigma_mrad,
            tangential_exit_sigma_mrad=tangential_exit_sigma_mrad,
            rng=rng,
            max_bounces=max_bounces,
        )
        area_ring_mm2 = 2.0 * math.pi * ring.radius_mm * ring.segment_thickness_mm
        geom_area_per_ray_mm2 = area_ring_mm2 / (n_rays * ring_probs[ring_idx[j]])
        if weight_model == "effective_lookup" and effective_lookup:
            transport_weight = interp_lookup(ray["mean_alpha_mrad"], effective_lookup)
        else:
            transport_weight = ray["reflectivity_product"]
        ray["initial_u_nm"] = u0_mm * 1.0e6
        ray["channel_offset_mm"] = channel_offset_mm
        ray["ring_id"] = ring.id
        ray["phi_rad"] = float(phi_center)
        ray["segment_count"] = n_segments
        ray["entrance_area_mm2"] = geom_area_per_ray_mm2
        ray["transport_weight"] = transport_weight
        ray["effective_area_term_mm2"] = geom_area_per_ray_mm2 * open_fraction * transport_weight
        rows_list.append(ray)

    keys = list(rows_list[0].keys())
    rows = {k: np.array([row[k] for row in rows_list]) for k in keys}
    summary = make_summary(cfg, args, rows)
    return rows, summary


def main() -> None:
    args = parse_args()
    cfg = load_config(Path(args.config))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows, summary = run(cfg, args)
    write_csv(outdir / "bent_channel_samples.csv", rows)
    (outdir / "summary.json").write_text(
        json.dumps({"config": cfg, "summary": summary}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    make_plots(outdir, rows, summary)

    print("[OK] wrote", outdir / "bent_channel_samples.csv")
    print("[OK] wrote", outdir / "summary.json")
    print("[OK] wrote", outdir / "bent_channel_overview.png")
    print("[OK] wrote", outdir / "bounce_hist.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
