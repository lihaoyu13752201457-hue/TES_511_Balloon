from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .channel_raytrace import run_channel_baseline
    from .geometry import load_channel_config
except ImportError:  # Support direct script execution from the repository root.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from external_baseline.channel_raytrace_py.channel_raytrace import run_channel_baseline
    from external_baseline.channel_raytrace_py.geometry import load_channel_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the calibrated 511-CAM channel-optics Python baseline.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--n", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default="runs/channel_baseline")
    parser.add_argument("--reflectivity-table", default=None)
    parser.add_argument("--theta-policy", choices=["fixed", "ring_bending", "ring_bending_per_bounce"], default="fixed")
    parser.add_argument("--fixed-theta-rad", type=float, default=None)
    parser.add_argument("--stack-id", default="WSi_30_150")
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
        stack_id=args.stack_id,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
