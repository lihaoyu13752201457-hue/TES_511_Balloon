#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.bragg import bragg_angle_rad, focal_length_mm_from_radius, ring_radius_mm
from laue511.constants import DEFAULT_FOCAL_LENGTH_MM
from laue511.probabilities import darwin_hamilton_mosaic_probabilities
from laue511.rings import load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--focal-length-mm", type=float, default=DEFAULT_FOCAL_LENGTH_MM)
    args = parser.parse_args()

    rows = []
    for ring in load_ring_config(args.config):
        theta = bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)
        probs = darwin_hamilton_mosaic_probabilities(
            E_keV=ring.design_energy_keV,
            d_spacing_A=ring.d_spacing_A,
            thickness_mm=ring.thickness_mm,
            delta_theta_rad=0.0,
        )
        rows.append(
            {
                "ring_id": ring.ring_id,
                "energy_keV": ring.design_energy_keV,
                "thetaB_deg": math.degrees(theta),
                "radius_mm_from_8300": ring_radius_mm(args.focal_length_mm, theta),
                "radius_mm_config": ring.radius_mm,
                "focal_length_mm_from_config": focal_length_mm_from_radius(ring.radius_mm, theta),
                "p_diff": probs.p_diff,
                "p_abs": probs.p_abs,
                "p_trans": probs.p_trans,
                "prob_sum_raw": probs.prob_sum_raw,
            }
        )
    print(json.dumps({"rings": rows}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
