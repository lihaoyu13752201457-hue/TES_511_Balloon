"""Generate CAM511-style overview plots from bent-channel samples."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="CAM511-style overview plots")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_supplemented.json",
        help="Config JSON",
    )
    ap.add_argument(
        "--samples",
        default="optics/channeling_fp/out/bent_supplemented/bent_channel_samples.csv",
        help="CSV produced by bent_channel.py",
    )
    ap.add_argument(
        "--outdir",
        default="optics/channeling_fp/out/cam511_style",
        help="Output directory",
    )
    ap.add_argument("--plot-rays", type=int, default=250, help="Number of sample rays to draw in side view")
    return ap.parse_args()


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = {h: [] for h in reader.fieldnames or []}
        for row in reader:
            for h, v in row.items():
                cols[h].append(float(v))
    return {k: np.asarray(v, dtype=float) for k, v in cols.items()}


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    data = load_csv(Path(args.samples))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    f_mm = float(cfg["focal_plane_z_mm"])
    ring_ids = data["ring_id"].astype(int)
    unique_rings = sorted(set(ring_ids.tolist()))
    cmap = plt.get_cmap("tab10")
    colors = {rid: cmap(i % 10) for i, rid in enumerate(unique_rings)}

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.8), constrained_layout=True)

    ax = axes[0]
    for ring in cfg["rings"]:
        rid = int(ring["id"])
        color = colors[rid]
        r0 = float(ring["radius_mm"])
        thickness = float(ring["segment_thickness_mm"])
        length = float(ring["segment_length_mm"])
        bend = math.radians(float(ring["bending_angle_deg"]))
        s = np.linspace(0.0, length, 200)
        if abs(bend) < 1.0e-18:
            theta = np.zeros_like(s)
            x_c = np.full_like(s, r0)
            z_c = s
        else:
            rc = length / bend
            theta = bend * (s / length)
            x_c = r0 - rc * (1.0 - np.cos(theta))
            z_c = rc * np.sin(theta)
        ax.plot(z_c, x_c, color=color, linewidth=2.0, label=f"ring {rid}")
        ax.fill_between(z_c, x_c - 0.5 * thickness, x_c + 0.5 * thickness, color=color, alpha=0.18)

    take = np.linspace(0, len(data["x_fp_mm"]) - 1, min(int(args.plot_rays), len(data["x_fp_mm"])), dtype=int)
    for idx in take:
        rid = int(ring_ids[idx])
        color = colors[rid]
        z0 = float(data["z_exit_mm"][idx])
        r0 = math.hypot(float(data["x_exit_mm"][idx]), float(data["y_exit_mm"][idx]))
        z1 = f_mm
        r1 = math.hypot(float(data["x_fp_mm"][idx]), float(data["y_fp_mm"][idx]))
        ax.plot([z0, z1], [r0, r1], color=color, alpha=0.18, linewidth=0.8)

    ax.axvline(f_mm, color="#475569", linestyle="--", linewidth=1.3)
    ax.set_xlabel("Focal length coordinate z [mm]")
    ax.set_ylabel("Radius of rings / ray radius [mm]")
    ax.set_title("CAM511-style side view: ring radius vs focal length")
    ax.legend(fontsize=8, loc="upper right")

    ax = axes[1]
    for rid in unique_rings:
        mask = ring_ids == rid
        ax.scatter(
            data["x_fp_mm"][mask],
            data["y_fp_mm"][mask],
            s=3.0,
            alpha=0.30,
            color=colors[rid],
            label=f"ring {rid}",
        )
    ax.set_xlabel("x on focal plane [mm]")
    ax.set_ylabel("y on focal plane [mm]")
    ax.set_title("Focal spot from sampled rays")
    ax.set_aspect("equal")
    ax.legend(fontsize=8, loc="upper right")

    fig.savefig(outdir / "cam511_style_overview.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 6.0), constrained_layout=True)
    radial = data["fp_radial_mm"]
    tangential = data["fp_tangential_mm"]
    for rid in unique_rings:
        mask = ring_ids == rid
        ax.scatter(
            tangential[mask],
            radial[mask],
            s=3.0,
            alpha=0.30,
            color=colors[rid],
            label=f"ring {rid}",
        )
    ax.set_xlabel("Tangential coordinate on focal plane [mm]")
    ax.set_ylabel("Radial coordinate on focal plane [mm]")
    ax.set_title("Focal spot in radial/tangential coordinates")
    ax.axhline(0.0, color="#94a3b8", linewidth=0.8)
    ax.axvline(0.0, color="#94a3b8", linewidth=0.8)
    fig.savefig(outdir / "cam511_style_spot_rt.png", dpi=220)
    plt.close(fig)

    print("[OK] wrote", outdir / "cam511_style_overview.png")
    print("[OK] wrote", outdir / "cam511_style_spot_rt.png")


if __name__ == "__main__":
    main()
