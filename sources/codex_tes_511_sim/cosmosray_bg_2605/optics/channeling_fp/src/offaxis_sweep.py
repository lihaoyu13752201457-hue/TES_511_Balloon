"""Sweep source off-axis angle for the bent-channel CAM511 model."""

from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser(description="Off-axis sweep for channeling_fp bent-channel model")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/offaxis_sweep", help="Output directory")
    ap.add_argument("--n-rays", type=int, default=1200, help="Rays per point")
    ap.add_argument("--seed", type=int, default=511, help="Base seed")
    ap.add_argument("--npts", type=int, default=8, help="Number of off-axis radii including zero")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fov_radius_arcmin = float(cfg["field_of_view_radius_arcmin_reference"])
    radii = np.linspace(0.0, fov_radius_arcmin, int(args.npts))
    records = []

    for i, r_arcmin in enumerate(radii):
        class RunArgs:
            n_rays = int(args.n_rays)
            seed = int(args.seed + i)
            offaxis_x_arcmin = float(r_arcmin)
            offaxis_y_arcmin = 0.0

        rows, summary = run(cfg, RunArgs)
        w = rows["effective_area_term_mm2"]
        wsum = float(np.sum(w))
        cx = float(np.sum(rows["x_fp_mm"] * w) / wsum)
        cy = float(np.sum(rows["y_fp_mm"] * w) / wsum)
        records.append(
            {
                "offaxis_arcmin": float(r_arcmin),
                "centroid_x_mm": cx,
                "centroid_y_mm": cy,
                "weighted_hpd_mm": float(summary["weighted_hpd_diameter_mm"]),
                "estimated_effective_area_cm2": float(summary["estimated_effective_area_cm2"]),
            }
        )

    with (outdir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({"records": records}, f, indent=2, ensure_ascii=False)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    axes[0].plot([r["offaxis_arcmin"] for r in records], [r["centroid_x_mm"] for r in records], marker="o", color="#2563eb")
    axes[0].set_xlabel("Off-axis source radius [arcmin]")
    axes[0].set_ylabel("Weighted centroid x [mm]")
    axes[0].set_title("Centroid shift vs off-axis angle")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot([r["offaxis_arcmin"] for r in records], [r["weighted_hpd_mm"] for r in records], marker="o", color="#7c3aed", label="HPD")
    axes[1].plot([r["offaxis_arcmin"] for r in records], [r["estimated_effective_area_cm2"] for r in records], marker="s", color="#dc2626", label="Aeff")
    axes[1].set_xlabel("Off-axis source radius [arcmin]")
    axes[1].set_title("Spot and effective area vs off-axis angle")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.savefig(outdir / "offaxis_sweep.png", dpi=180)
    plt.close(fig)

    print("[OK] wrote", outdir / "summary.json")
    print("[OK] wrote", outdir / "offaxis_sweep.png")
    print(json.dumps({"records": records}, indent=2))


if __name__ == "__main__":
    main()
