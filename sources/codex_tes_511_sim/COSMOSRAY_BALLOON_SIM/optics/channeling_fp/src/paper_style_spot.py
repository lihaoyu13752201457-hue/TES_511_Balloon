"""Render focal-plane samples in a paper-style spoke plot similar to CAM511 Fig. 3."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Render paper-style focal spot from bent_channel samples")
    ap.add_argument(
        "--samples",
        default="optics/channeling_fp/out/bent_supplemented/bent_channel_samples.csv",
        help="CSV produced by bent_channel.py",
    )
    ap.add_argument(
        "--outdir",
        default="optics/channeling_fp/out/paper_style_spot",
        help="Output directory",
    )
    ap.add_argument("--max-points", type=int, default=1600, help="Maximum samples to render")
    ap.add_argument("--seed", type=int, default=511, help="Random seed for downsampling")
    return ap.parse_args()


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = {h: [] for h in reader.fieldnames or []}
        for row in reader:
            for h, v in row.items():
                cols[h].append(float(v))
    return {k: np.asarray(v, dtype=float) for k, v in cols.items()}


def weighted_centroid(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    wsum = float(np.sum(w))
    if wsum <= 0.0:
        return float(np.mean(x)), float(np.mean(y))
    return float(np.sum(x * w) / wsum), float(np.sum(y * w) / wsum)


def downsample(data: dict[str, np.ndarray], nmax: int, seed: int) -> dict[str, np.ndarray]:
    n = len(next(iter(data.values())))
    if n <= nmax:
        return data
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=nmax, replace=False)
    idx.sort()
    return {k: v[idx] for k, v in data.items()}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    data = downsample(load_csv(Path(args.samples)), int(args.max_points), int(args.seed))

    x = data["x_fp_mm"]
    y = data["y_fp_mm"]
    w = data.get("effective_area_term_mm2", np.ones_like(x))
    cx, cy = weighted_centroid(x, y, w)

    dx = x - cx
    dy = y - cy
    r = np.sqrt(dx * dx + dy * dy)
    keep = r > 1.0e-6
    x = x[keep]
    y = y[keep]
    w = w[keep]
    dx = dx[keep]
    dy = dy[keep]
    r = r[keep]

    unit_x = dx / r
    unit_y = dy / r
    inner = np.clip(0.25 * r, 0.6, 3.5)
    outer = np.clip(0.10 * r, 0.4, 2.0)

    x0 = x - inner * unit_x
    y0 = y - inner * unit_y
    x1 = x + outer * unit_x
    y1 = y + outer * unit_y

    segments = np.stack([np.column_stack([x0, y0]), np.column_stack([x1, y1])], axis=1)
    alpha = np.clip((w / np.max(w)) ** 0.35, 0.12, 0.6)
    colors = np.column_stack(
        [
            np.full_like(alpha, 0.96),
            np.full_like(alpha, 0.67),
            np.full_like(alpha, 0.31),
            alpha,
        ]
    )

    lim = max(20.0, float(np.quantile(np.sqrt((x - cx) ** 2 + (y - cy) ** 2), 0.995)) * 1.15)

    fig, ax = plt.subplots(figsize=(5.4, 5.2), constrained_layout=True)
    lc = LineCollection(segments, colors=colors, linewidths=0.8)
    ax.add_collection(lc)
    ax.scatter([cx], [cy], s=24, color="#e07a1f", alpha=0.85, zorder=3)
    ax.set_xlim(cx - lim, cx + lim)
    ax.set_ylim(cy - lim, cy + lim)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title("Paper-style focal spot")
    fig.savefig(outdir / "paper_style_spot.png", dpi=240)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 5.2), constrained_layout=True)
    ax.scatter(x, y, s=3.0, c="#f0a35a", alpha=0.32, linewidths=0)
    ax.scatter([cx], [cy], s=24, color="#e07a1f", alpha=0.85, zorder=3)
    ax.set_xlim(cx - lim, cx + lim)
    ax.set_ylim(cy - lim, cy + lim)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title("Raw focal spot scatter")
    fig.savefig(outdir / "paper_style_spot_scatter.png", dpi=240)
    plt.close(fig)

    summary = {
        "centroid_x_mm": cx,
        "centroid_y_mm": cy,
        "rendered_points": int(len(x)),
        "plot_limit_mm": lim,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("[OK] wrote", outdir / "paper_style_spot.png")
    print("[OK] wrote", outdir / "paper_style_spot_scatter.png")
    print("[OK] wrote", outdir / "summary.json")


if __name__ == "__main__":
    main()
