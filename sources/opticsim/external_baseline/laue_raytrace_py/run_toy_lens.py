from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .laue_raytrace import load_laue_config, run_laue_baseline
except ImportError:  # Support direct script execution from the repository root.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from external_baseline.laue_raytrace_py.laue_raytrace import load_laue_config, run_laue_baseline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 511 keV Laue toy focusing baseline.")
    parser.add_argument("--config", default="config/laue_toy_baseline.yaml")
    parser.add_argument("--n", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out", default="runs/laue_toy")
    args = parser.parse_args()
    cfg = load_laue_config(args.config)
    summary = run_laue_baseline(cfg, args.n, args.out, args.seed, args.config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
