from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.parratt_reflectivity import (  # noqa: E402
    MultilayerSpec,
    compute_reflectivity_rows,
    geometric_theta_grid,
    summarize_rows,
    write_reflectivity_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a 511 keV W/Si multilayer reflectivity table using xraydb.")
    parser.add_argument("--energy-kev", type=float, default=511.0)
    parser.add_argument("--theta-min-rad", type=float, default=1.0e-8)
    parser.add_argument("--theta-max-rad", type=float, default=5.0e-3)
    parser.add_argument("--n-theta", type=int, default=240)
    parser.add_argument("--out", default="data/reflectivity/WSi_511keV_parratt_grid.csv")
    args = parser.parse_args()

    spec = MultilayerSpec()
    theta = geometric_theta_grid(args.theta_min_rad, args.theta_max_rad, args.n_theta)
    rows = compute_reflectivity_rows(spec, E_keV=args.energy_kev, theta_rad=theta)
    write_reflectivity_csv(args.out, rows)
    print(json.dumps(summarize_rows(rows), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
