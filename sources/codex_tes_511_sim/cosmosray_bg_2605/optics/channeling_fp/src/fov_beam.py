"""Sample a uniform source cone over the quoted CAM511 FOV and propagate through bent_channel."""

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
    from src.bent_channel import run
else:
    from .bent_channel import run


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="FOV-beam footprint simulation for channeling_fp")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/fov_beam", help="Output directory")
    ap.add_argument("--n-rays", type=int, default=4000, help="Total rays")
    ap.add_argument("--seed", type=int, default=511, help="Random seed")
    return ap.parse_args()


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


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(int(args.seed))
    fov_radius_arcmin = float(cfg["field_of_view_radius_arcmin_reference"])

    rows_all = []
    remaining = int(args.n_rays)
    chunk = min(500, remaining)
    while remaining > 0:
        n_chunk = min(chunk, remaining)
        rho = fov_radius_arcmin * np.sqrt(rng.uniform(0.0, 1.0, size=n_chunk))
        psi = rng.uniform(0.0, 2.0 * math.pi, size=n_chunk)
        for r_arcmin, ang in zip(rho, psi):
            class RunArgs:
                n_rays = 1
                seed = int(rng.integers(0, 2**31 - 1))
                offaxis_x_arcmin = float(r_arcmin * math.cos(ang))
                offaxis_y_arcmin = float(r_arcmin * math.sin(ang))

            rows, _summary = run(cfg, RunArgs)
            row = {k: rows[k][0] for k in rows}
            row["source_r_arcmin"] = float(r_arcmin)
            row["source_phi_rad"] = float(ang)
            rows_all.append(row)
        remaining -= n_chunk

    keys = list(rows_all[0].keys())
    arrs = {k: np.array([row[k] for row in rows_all]) for k in keys}
    weights = arrs["effective_area_term_mm2"]
    r_fp = np.sqrt(arrs["x_fp_mm"] ** 2 + arrs["y_fp_mm"] ** 2)

    summary = {
        "fov_radius_arcmin": fov_radius_arcmin,
        "mean_effective_area_cm2_over_fov": float(np.mean(weights) / 100.0),
        "integrated_weight_sum_cm2_samples": float(np.sum(weights) / 100.0),
        "beam_r50_mm": weighted_quantile(r_fp, weights, 0.50),
        "beam_r90_mm": weighted_quantile(r_fp, weights, 0.90),
        "beam_r95_mm": weighted_quantile(r_fp, weights, 0.95),
        "beam_d95_mm": 2.0 * weighted_quantile(r_fp, weights, 0.95),
        "beam_max_radius_mm": float(np.max(r_fp)),
    }

    with (outdir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary}, f, indent=2, ensure_ascii=False)

    with (outdir / "fov_beam_samples.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for i in range(len(rows_all)):
            writer.writerow([arrs[k][i] for k in keys])

    fig, ax = plt.subplots(figsize=(6.2, 6.0), constrained_layout=True)
    sc = ax.scatter(arrs["x_fp_mm"], arrs["y_fp_mm"], c=arrs["source_r_arcmin"], s=3.0, alpha=0.35, cmap="viridis")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title("Focal-plane footprint for uniform source cone in FOV")
    ax.set_aspect("equal")
    fig.colorbar(sc, ax=ax, label="source off-axis radius [arcmin]")
    fig.savefig(outdir / "fov_beam_map.png", dpi=180)
    plt.close(fig)

    print("[OK] wrote", outdir / "summary.json")
    print("[OK] wrote", outdir / "fov_beam_samples.csv")
    print("[OK] wrote", outdir / "fov_beam_map.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
