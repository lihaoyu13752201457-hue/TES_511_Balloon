from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.channel_raytrace import run_channel_baseline  # noqa: E402
from external_baseline.channel_raytrace_py.geometry import load_channel_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the explicit 4-ring channel diagnostic.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--reflectivity-table", default="data/reflectivity/WSi_511keV_parratt_grid.csv")
    parser.add_argument("--fixed-theta-rad", type=float, default=1.496e-4)
    parser.add_argument("--theta-policy", choices=["fixed", "ring_bending", "ring_bending_per_bounce"], default="fixed")
    parser.add_argument("--n", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out", default="runs/channel_4ring_parratt")
    args = parser.parse_args()

    cfg = load_channel_config(args.config)
    summary = run_channel_baseline(
        cfg,
        args.n,
        args.out,
        args.seed,
        args.config,
        reflectivity_table_path=args.reflectivity_table,
        theta_policy=args.theta_policy,
        fixed_theta_rad=args.fixed_theta_rad,
    )
    per_ring_path = Path(args.out) / "per_ring_summary.json"
    with per_ring_path.open() as f:
        per_ring = json.load(f)
    print(json.dumps({"summary": summary, "per_ring": per_ring}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

