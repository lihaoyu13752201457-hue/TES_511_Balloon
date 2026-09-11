from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.channel_raytrace import (  # noqa: E402
    _estimated_bounce_count,
    run_channel_baseline,
)
from external_baseline.channel_raytrace_py.geometry import load_channel_config  # noqa: E402
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable  # noqa: E402


def theta_for_required_R(table: ReflectivityTable, energy_keV: float, stack_id: str, required_R: float) -> float:
    rows = sorted((r for r in table.rows if r.stack_id == stack_id), key=lambda r: r.theta_rad)
    if not rows:
        raise ValueError(f"no table rows for stack {stack_id}")
    best_row = min(rows, key=lambda row: abs(row.R - required_R))
    for lower, upper in zip(rows[:-1], rows[1:]):
        if (lower.R - required_R) * (upper.R - required_R) <= 0.0:
            lo = lower.theta_rad
            hi = upper.theta_rad
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                mid_R = table.lookup(energy_keV, mid, stack_id).R
                if abs(mid_R - required_R) < 1.0e-8:
                    return mid
                if (table.lookup(energy_keV, lo, stack_id).R - required_R) * (mid_R - required_R) <= 0.0:
                    hi = mid
                else:
                    lo = mid
            return 0.5 * (lo + hi)
    return best_row.theta_rad


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate one effective grazing angle per 511-CAM ring.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--reflectivity-table", default="data/reflectivity/WSi_511keV_parratt_grid.csv")
    parser.add_argument("--target", type=float, default=0.80)
    parser.add_argument("--stack-id", default="WSi_30_150")
    parser.add_argument("--n", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out", default="runs/channel_4ring_calibrated")
    args = parser.parse_args()

    cfg = load_channel_config(args.config)
    table = ReflectivityTable.from_csv(args.reflectivity_table)
    ring_theta: dict[int, float] = {}
    calibration = []
    for ring in cfg.rings:
        n_bounce = _estimated_bounce_count(ring.radius_cm, ring.length_cm, ring.bending_angle_deg)
        required_R = args.target ** (1.0 / max(1, n_bounce))
        theta_rad = theta_for_required_R(table, cfg.energy_keV, args.stack_id, required_R)
        params = table.lookup(cfg.energy_keV, theta_rad, args.stack_id)
        ring_theta[ring.id] = theta_rad
        calibration.append(
            {
                "ring_id": ring.id,
                "radius_cm": ring.radius_cm,
                "n_bounce": n_bounce,
                "required_single_bounce_R": required_R,
                "theta_rad": theta_rad,
                "table_R": params.R,
                "expected_transmissivity": params.R ** n_bounce,
            }
        )

    summary = run_channel_baseline(
        cfg,
        args.n,
        args.out,
        args.seed,
        args.config,
        reflectivity_table_path=args.reflectivity_table,
        theta_policy="ring_calibrated",
        ring_theta_rad=ring_theta,
        stack_id=args.stack_id,
    )
    with (Path(args.out) / "ring_theta_calibration.json").open("w") as f:
        json.dump(calibration, f, indent=2, sort_keys=True)
        f.write("\n")
    with (Path(args.out) / "per_ring_summary.json").open() as f:
        per_ring = json.load(f)
    print(json.dumps({"summary": summary, "calibration": calibration, "per_ring": per_ring}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
