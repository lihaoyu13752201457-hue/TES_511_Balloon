#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.geometry import load_channel_config
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable
from external_baseline.channel_raytrace_py.wallbywall_channel import (
    WallByWallOptions,
    simulate_wallbywall_channel,
    summarize_wallbywall,
    write_wallbywall_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a public-geometry wall-by-wall reconstruction of the 511-CAM channel optics."
    )
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--reflectivity-table", default="data/reflectivity/WSi_511keV_parratt_grid_dense.csv")
    parser.add_argument("--stack-id", default="WSi_30_150")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--out", default="runs/channel_wallbywall_rebuild")
    parser.add_argument("--si-mu-cm-inv", type=float, default=0.20193273411049242)
    parser.add_argument("--no-si-path-absorption", action="store_true")
    parser.add_argument(
        "--support-open-fraction",
        type=float,
        default=1.0,
        help="Extra macro support/open-area factor. Keep 1.0 for the 511-CAM formula; use 0.6 for the Shirazi 2020 support-hardware pressure test.",
    )
    args = parser.parse_args()

    cfg = load_channel_config(args.config)
    table = ReflectivityTable.from_csv(args.reflectivity_table)
    options = WallByWallOptions(
        seed=args.seed,
        si_mu_cm_inv=args.si_mu_cm_inv,
        include_si_path_absorption=not args.no_si_path_absorption,
        support_open_fraction=args.support_open_fraction,
        stack_id=args.stack_id,
    )
    events, history = simulate_wallbywall_channel(cfg, args.n, table, options)
    summary = summarize_wallbywall(cfg, events, history, options, args.reflectivity_table)
    write_wallbywall_outputs(args.out, cfg, events, history, summary, config_path=args.config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
