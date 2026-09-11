"""Sweep channel gap for the bent-channel CAM511 model."""

from __future__ import annotations

import argparse
import json
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
    ap = argparse.ArgumentParser(description="Gap sweep for channeling_fp bent-channel model")
    ap.add_argument(
        "--config",
        default="optics/channeling_fp/configs/cam511_channeling_fp_baseline.json",
        help="Baseline JSON config",
    )
    ap.add_argument("--outdir", default="optics/channeling_fp/out/gap_sweep", help="Output directory")
    ap.add_argument("--n-rays", type=int, default=1200, help="Rays per sweep point")
    ap.add_argument("--seed", type=int, default=511, help="Base seed")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg0 = json.loads(Path(args.config).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    gap_values = np.array([50, 75, 100, 150, 200, 300, 500, 1000, 2000, 5000], dtype=float)
    records = []

    class SweepArgs:
        n_rays = int(args.n_rays)
        seed = int(args.seed)
        offaxis_x_arcmin = 0.0
        offaxis_y_arcmin = 0.0

    for i, gap_nm in enumerate(gap_values):
        cfg = json.loads(json.dumps(cfg0))
        cfg["multilayer"]["channel_gap_nm"] = float(gap_nm)
        sweep_rows, summary = run(cfg, SweepArgs)
        records.append(
            {
                "gap_nm": float(gap_nm),
                "Aeff_cm2": float(summary["estimated_effective_area_cm2"]),
                "HPD_mm": float(summary["weighted_hpd_diameter_mm"]),
                "median_alpha_mrad": float(summary["median_last_alpha_mrad"]),
                "mean_bounces": float(summary["mean_bounce_count"]),
            }
        )

    csv_path = outdir / "gap_sweep.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("gap_nm,Aeff_cm2,HPD_mm,median_alpha_mrad,mean_bounces\n")
        for rec in records:
            f.write(
                f"{rec['gap_nm']:.8g},{rec['Aeff_cm2']:.8g},{rec['HPD_mm']:.8g},"
                f"{rec['median_alpha_mrad']:.8g},{rec['mean_bounces']:.8g}\n"
            )

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.5), constrained_layout=True)
    axes[0].plot(gap_values, [r["Aeff_cm2"] for r in records], marker="o", color="#2563eb")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Channel gap [nm]")
    axes[0].set_ylabel("Estimated Aeff [cm²]")
    axes[0].set_title("Effective area vs channel gap")
    axes[0].grid(True, which="both", alpha=0.25)

    axes[1].plot(gap_values, [r["HPD_mm"] for r in records], marker="o", color="#7c3aed")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Channel gap [nm]")
    axes[1].set_ylabel("Weighted HPD [mm]")
    axes[1].set_title("Spot size vs channel gap")
    axes[1].grid(True, which="both", alpha=0.25)

    axes[2].plot(gap_values, [r["mean_bounces"] for r in records], marker="o", color="#dc2626", label="mean bounces")
    axes[2].plot(gap_values, [r["median_alpha_mrad"] for r in records], marker="s", color="#059669", label="median alpha [mrad]")
    axes[2].set_xscale("log")
    axes[2].set_xlabel("Channel gap [nm]")
    axes[2].set_title("Transport diagnostics")
    axes[2].grid(True, which="both", alpha=0.25)
    axes[2].legend(fontsize=8)

    fig.savefig(outdir / "gap_sweep.png", dpi=180)
    plt.close(fig)

    (outdir / "summary.json").write_text(json.dumps({"records": records}, indent=2), encoding="utf-8")
    print("[OK] wrote", csv_path)
    print("[OK] wrote", outdir / "gap_sweep.png")
    print("[OK] wrote", outdir / "summary.json")


if __name__ == "__main__":
    main()
