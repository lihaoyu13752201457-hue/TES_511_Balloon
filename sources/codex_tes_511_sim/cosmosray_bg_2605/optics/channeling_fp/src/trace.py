"""Entry point for the physics-first channeling tracer."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.geometry import Ring
    from src.multilayer import bilayer_stack_from_config, parratt_reflectivity
else:
    from .geometry import Ring
    from .multilayer import bilayer_stack_from_config, parratt_reflectivity


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Physics-first CAM511 channeling tracer")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/run01", help="Output directory")
    ap.add_argument("--n-rays", type=int, default=None, help="Override number of rays")
    ap.add_argument("--seed", type=int, default=None, help="Override RNG seed")
    ap.add_argument("--offaxis-x-arcmin", type=float, default=0.0, help="Off-axis source angle in x")
    ap.add_argument("--offaxis-y-arcmin", type=float, default=0.0, help="Off-axis source angle in y")
    return ap.parse_args()


def arcmin_to_rad(v: float) -> float:
    return math.radians(v / 60.0)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ring_slope_tan(radius_mm: float, focus_length_mm: float) -> float:
    """Cone slope chosen so the ring center reflects the on-axis beam to focus."""
    return math.tan(0.5 * math.atan(radius_mm / focus_length_mm))


def sample_rings(cfg: dict, rng: np.random.Generator, n: int) -> tuple[np.ndarray, list[Ring], np.ndarray]:
    rings = [Ring(**r) for r in cfg["rings"]]
    weights = np.array([r.geometric_weight for r in rings], dtype=float)
    weights /= weights.sum()
    idx = rng.choice(len(rings), size=n, p=weights)
    return idx, rings, weights


def make_summary(
    cfg: dict,
    args: argparse.Namespace,
    x_fp: np.ndarray,
    y_fp: np.ndarray,
    reflectivity: np.ndarray,
    effective_area_terms_mm2: np.ndarray,
) -> dict:
    f_mm = float(cfg["focus_length_m"]) * 1000.0
    x0 = f_mm * math.tan(arcmin_to_rad(float(args.offaxis_x_arcmin)))
    y0 = f_mm * math.tan(arcmin_to_rad(float(args.offaxis_y_arcmin)))
    r = np.sqrt((x_fp - x0) ** 2 + (y_fp - y0) ** 2)
    q = lambda p: float(np.quantile(r, p))
    return {
        "focus_length_m": float(cfg["focus_length_m"]),
        "energy_keV": float(cfg["energy_keV"]),
        "offaxis_x_arcmin": float(args.offaxis_x_arcmin),
        "offaxis_y_arcmin": float(args.offaxis_y_arcmin),
        "measured_r50_mm": q(0.50),
        "measured_r68_mm": q(0.68),
        "measured_r90_mm": q(0.90),
        "measured_r95_mm": q(0.95),
        "measured_hpd_diameter_mm": 2.0 * q(0.50),
        "measured_hpd_arcmin": math.degrees((2.0 * q(0.50)) / f_mm) * 60.0,
        "mean_reflectivity": float(np.mean(reflectivity)),
        "median_reflectivity": float(np.median(reflectivity)),
        "estimated_effective_area_cm2": float(np.sum(effective_area_terms_mm2) / 100.0),
        "estimated_effective_area_note": "Single-bounce conical-ring estimate using projected surface area times Parratt reflectivity.",
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
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    sc = axes[0].scatter(rows["x_surface_mm"], rows["z_surface_mm"], c=rows["ring_id"], s=2.0, alpha=0.35, cmap="tab10")
    axes[0].set_title("Sampled conical reflection surface")
    axes[0].set_xlabel("x [mm]")
    axes[0].set_ylabel("z [mm]")

    im = axes[1].scatter(rows["x_fp_mm"], rows["y_fp_mm"], c=rows["reflectivity"], s=2.0, alpha=0.35, cmap="viridis")
    axes[1].set_title("Focal-plane intersection map")
    axes[1].set_xlabel("x [mm]")
    axes[1].set_ylabel("y [mm]")
    axes[1].set_aspect("equal")

    fig.colorbar(im, ax=axes[1], label="Reflectivity")
    fig.savefig(outdir / "focal_map.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
    ax.hist(rows["grazing_angle_mrad"], bins=60, color="#2563eb", alpha=0.8)
    ax.set_xlabel("Grazing angle [mrad]")
    ax.set_ylabel("Count")
    ax.set_title("Surface grazing-angle distribution")
    fig.savefig(outdir / "grazing_angle_hist.png", dpi=180)
    plt.close(fig)


def run_trace(cfg: dict, args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict]:
    energy_keV = float(cfg["energy_keV"])
    f_mm = float(cfg["focus_length_m"]) * 1000.0
    z_fp = float(cfg.get("focal_plane_z_mm", f_mm))
    trace_cfg = cfg["trace"]
    n_rays = int(args.n_rays if args.n_rays is not None else trace_cfg["n_rays"])
    seed = int(args.seed if args.seed is not None else trace_cfg["seed"])
    rng = np.random.default_rng(seed)

    layers, substrate = bilayer_stack_from_config(cfg, energy_keV)
    ring_idx, rings, ring_probs = sample_rings(cfg, rng, n_rays)

    phi = rng.uniform(0.0, 2.0 * math.pi, size=n_rays)
    z_local = np.array(
        [
            rng.uniform(-0.5 * rings[i].segment_length_mm, 0.5 * rings[i].segment_length_mm)
            for i in ring_idx
        ],
        dtype=float,
    )

    radii_center = np.array([rings[i].radius_mm for i in ring_idx], dtype=float)
    slopes = np.array([ring_slope_tan(rings[i].radius_mm, f_mm) for i in ring_idx], dtype=float)
    radii_surface = radii_center + slopes * z_local

    x_surface = radii_surface * np.cos(phi)
    y_surface = radii_surface * np.sin(phi)
    z_surface = z_local

    theta_x = arcmin_to_rad(float(args.offaxis_x_arcmin))
    theta_y = arcmin_to_rad(float(args.offaxis_y_arcmin))
    k_in = np.array([math.tan(theta_x), math.tan(theta_y), 1.0], dtype=float)
    k_in /= np.linalg.norm(k_in)

    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    normals = np.stack([-cos_phi, -sin_phi, -slopes], axis=1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]

    k_in_dot_n = np.clip(normals @ k_in, -1.0, 1.0)
    k_out = k_in[None, :] - 2.0 * k_in_dot_n[:, None] * normals
    k_out /= np.linalg.norm(k_out, axis=1)[:, None]

    t_fp = (z_fp - z_surface) / k_out[:, 2]
    x_fp = x_surface + t_fp * k_out[:, 0]
    y_fp = y_surface + t_fp * k_out[:, 1]

    grazing_angle_rad = np.arcsin(np.abs(k_in_dot_n))
    reflectivity = np.array(
        [parratt_reflectivity(energy_keV, float(alpha), layers, substrate) for alpha in grazing_angle_rad],
        dtype=float,
    )

    area_surface_ring = np.array(
        [
            2.0
            * math.pi
            * rings[i].radius_mm
            * rings[i].segment_length_mm
            * math.sqrt(1.0 + slopes[j] ** 2)
            for j, i in enumerate(ring_idx)
        ],
        dtype=float,
    )
    per_ray_surface_area = area_surface_ring / (n_rays * ring_probs[ring_idx])
    projected_area_term = per_ray_surface_area * np.abs(k_in_dot_n)
    effective_area_terms_mm2 = projected_area_term * reflectivity

    rows = {
        "sample_id": np.arange(n_rays, dtype=np.int64),
        "ring_id": np.array([rings[i].id for i in ring_idx], dtype=np.int64),
        "x_surface_mm": x_surface,
        "y_surface_mm": y_surface,
        "z_surface_mm": z_surface,
        "x_fp_mm": x_fp,
        "y_fp_mm": y_fp,
        "z_fp_mm": np.full(n_rays, z_fp, dtype=float),
        "dir_in_x": np.full(n_rays, k_in[0], dtype=float),
        "dir_in_y": np.full(n_rays, k_in[1], dtype=float),
        "dir_in_z": np.full(n_rays, k_in[2], dtype=float),
        "dir_out_x": k_out[:, 0],
        "dir_out_y": k_out[:, 1],
        "dir_out_z": k_out[:, 2],
        "grazing_angle_mrad": grazing_angle_rad * 1.0e3,
        "reflectivity": reflectivity,
        "projected_area_mm2": projected_area_term,
        "effective_area_term_mm2": effective_area_terms_mm2,
    }
    summary = make_summary(cfg, args, x_fp, y_fp, reflectivity, effective_area_terms_mm2)
    return rows, summary


def main() -> None:
    args = parse_args()
    cfg = load_config(Path(args.config))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows, summary = run_trace(cfg, args)
    write_csv(outdir / "focal_plane_samples.csv", rows)
    (outdir / "summary.json").write_text(
        json.dumps({"config": cfg, "summary": summary}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    make_plots(outdir, rows, summary)

    print("[OK] wrote", outdir / "focal_plane_samples.csv")
    print("[OK] wrote", outdir / "summary.json")
    print("[OK] wrote", outdir / "focal_map.png")
    print("[OK] wrote", outdir / "grazing_angle_hist.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
