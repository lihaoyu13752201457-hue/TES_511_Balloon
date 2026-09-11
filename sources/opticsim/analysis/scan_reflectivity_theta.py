from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.channel_raytrace import _estimated_bounce_count  # noqa: E402
from external_baseline.channel_raytrace_py.geometry import load_channel_config, sample_uniform_disk_mm  # noqa: E402
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable  # noqa: E402


def sampled_bounce_counts(cfg, n: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    counts: list[int] = []
    for _ in range(n):
        x_mm, y_mm = sample_uniform_disk_mm(rng, cfg.aperture_radius_mm)
        r_cm = math.hypot(x_mm, y_mm) / 10.0
        ring = cfg.nearest_ring(r_cm)
        counts.append(_estimated_bounce_count(r_cm, ring.length_cm, ring.bending_angle_deg))
    return counts


def expected_transmissivity(table: ReflectivityTable, cfg, theta_rad: float, bounce_counts: list[int], stack_id: str) -> float:
    params = table.lookup(cfg.energy_keV, theta_rad, stack_id)
    return sum(params.R ** n for n in bounce_counts) / len(bounce_counts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan fixed grazing angle against a channel reflectivity table.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--reflectivity-table", default="data/reflectivity/WSi_511keV_parratt_grid.csv")
    parser.add_argument("--stack-id", default="WSi_30_150")
    parser.add_argument("--theta-min-rad", type=float, default=1.0e-8)
    parser.add_argument("--theta-max-rad", type=float, default=5.0e-3)
    parser.add_argument("--n-theta", type=int, default=220)
    parser.add_argument("--n-samples", type=int, default=50000)
    parser.add_argument("--target", type=float, default=0.80)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out", default="runs/reflectivity_theta_scan")
    args = parser.parse_args()

    cfg = load_channel_config(args.config)
    table = ReflectivityTable.from_csv(args.reflectivity_table)
    bounce_counts = sampled_bounce_counts(cfg, args.n_samples, args.seed)
    theta_values = [
        math.exp(math.log(args.theta_min_rad) + i * (math.log(args.theta_max_rad) - math.log(args.theta_min_rad)) / (args.n_theta - 1))
        for i in range(args.n_theta)
    ]
    rows = []
    for theta in theta_values:
        tr = expected_transmissivity(table, cfg, theta, bounce_counts, args.stack_id)
        rows.append({"theta_rad": theta, "transmissivity": tr})
    best = min(rows, key=lambda row: abs(row["transmissivity"] - args.target))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "theta_scan.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["theta_rad", "transmissivity"])
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "config": args.config,
        "reflectivity_table": args.reflectivity_table,
        "target_transmissivity": args.target,
        "best_theta_rad": best["theta_rad"],
        "best_transmissivity": best["transmissivity"],
        "n_samples": args.n_samples,
        "seed": args.seed,
        "mean_bounce_count": sum(bounce_counts) / len(bounce_counts),
        "min_bounce_count": min(bounce_counts),
        "max_bounce_count": max(bounce_counts),
    }
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")

    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 4.2), dpi=140)
    ax.semilogx([r["theta_rad"] for r in rows], [r["transmissivity"] for r in rows], color="tab:blue")
    ax.axhline(args.target, color="tab:red", linestyle="--", linewidth=1.0)
    ax.axvline(best["theta_rad"], color="tab:green", linestyle=":", linewidth=1.0)
    ax.set_xlabel("fixed grazing angle [rad]")
    ax.set_ylabel("expected multi-bounce transmissivity")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out / "theta_scan.png")
    plt.close(fig)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

