from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .detector_response import load_detector_config, run_detector_only
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from external_baseline.detector_response_py.detector_response import load_detector_config, run_detector_only


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a calibrated detector-only TES/BGO response on optics phase space.")
    parser.add_argument("--config", default="config/detector_tes_bgo.yaml")
    parser.add_argument("--source", default="runs/channel_4ring_calibrated_v2/phase_space.csv")
    parser.add_argument("--out", default="runs/detector_only_4ring_calibrated_v2")
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    cfg = load_detector_config(args.config)
    summary = run_detector_only(cfg, args.source, args.out, seed=args.seed, config_path=args.config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
