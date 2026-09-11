#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.constants import DEFAULT_FOCAL_LENGTH_MM
from laue511.geometry import direction_to_point, plane_hit_at_z
from laue511.metrics import branch_fractions, containment_diameter_mm
from laue511.probabilities import darwin_hamilton_mosaic_probabilities
from laue511.rings import find_ring, load_ring_config
from laue511.sampling import sample_branch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ring-id", type=int, default=2)
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--n-photons", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--focal-length-mm", type=float, default=DEFAULT_FOCAL_LENGTH_MM)
    args = parser.parse_args()

    ring = find_ring(load_ring_config(args.config), args.ring_id)
    probs = darwin_hamilton_mosaic_probabilities(
        E_keV=ring.design_energy_keV,
        d_spacing_A=ring.d_spacing_A,
        thickness_mm=ring.thickness_mm,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    counts: Counter[str] = Counter()
    focal_points: list[tuple[float, float]] = []

    history_fields = [
        "event_id",
        "photon_id",
        "mode",
        "branch",
        "ring_id",
        "tile_id",
        "E_actual_keV",
        "E_design_keV",
        "x_mm",
        "y_mm",
        "z_mm",
        "dx_in",
        "dy_in",
        "dz_in",
        "dx_out",
        "dy_out",
        "dz_out",
        "p_diff_raw",
        "p_trans_raw",
        "p_abs_raw",
        "prob_sum_raw",
        "prob_residual",
        "renormalized_flag",
    ]
    phase_fields = [
        "event_id",
        "photon_id",
        "parent_id",
        "E_keV",
        "x_mm",
        "y_mm",
        "z_mm",
        "dx",
        "dy",
        "dz",
        "time_s",
        "weight",
        "ring_id",
        "tile_id",
        "branch",
        "source_tag",
        "offaxis_x_rad",
        "offaxis_y_rad",
    ]

    with (out_dir / "optics_history.csv").open("w", newline="") as h, (out_dir / "phase_space.csv").open("w", newline="") as p, (out_dir / "transmitted_space.csv").open("w", newline="") as t:
        history = csv.DictWriter(h, fieldnames=history_fields)
        phase = csv.DictWriter(p, fieldnames=phase_fields)
        transmitted = csv.DictWriter(t, fieldnames=phase_fields)
        history.writeheader()
        phase.writeheader()
        transmitted.writeheader()
        for event_id in range(args.n_photons):
            tile_id = event_id % ring.n_tiles
            phi = 2.0 * math.pi * tile_id / ring.n_tiles
            pos = (ring.radius_mm * math.cos(phi), ring.radius_mm * math.sin(phi), -0.5 * ring.thickness_mm)
            in_dir = (0.0, 0.0, 1.0)
            focus = (0.0, 0.0, args.focal_length_mm)
            diffracted_dir = direction_to_point(pos, focus)
            branch = sample_branch(probs.p_abs, probs.p_diff, probs.p_trans, rng)
            counts[branch] += 1
            emitted_dir = diffracted_dir if branch == "DIFFRACT" else in_dir
            history.writerow(
                {
                    "event_id": event_id,
                    "photon_id": event_id,
                    "mode": "reference_single_ring",
                    "branch": branch,
                    "ring_id": ring.ring_id,
                    "tile_id": tile_id,
                    "E_actual_keV": ring.design_energy_keV,
                    "E_design_keV": ring.design_energy_keV,
                    "x_mm": pos[0],
                    "y_mm": pos[1],
                    "z_mm": pos[2],
                    "dx_in": in_dir[0],
                    "dy_in": in_dir[1],
                    "dz_in": in_dir[2],
                    "dx_out": emitted_dir[0],
                    "dy_out": emitted_dir[1],
                    "dz_out": emitted_dir[2],
                    "p_diff_raw": probs.p_diff_raw,
                    "p_trans_raw": probs.p_trans_raw,
                    "p_abs_raw": probs.p_abs_raw,
                    "prob_sum_raw": probs.prob_sum_raw,
                    "prob_residual": probs.prob_residual,
                    "renormalized_flag": probs.renormalized_flag,
                }
            )
            if branch in {"DIFFRACT", "TRANSMIT"}:
                hit = plane_hit_at_z(pos, emitted_dir, args.focal_length_mm)
                row = {
                    "event_id": event_id,
                    "photon_id": event_id,
                    "parent_id": 0,
                    "E_keV": ring.design_energy_keV,
                    "x_mm": hit[0],
                    "y_mm": hit[1],
                    "z_mm": hit[2],
                    "dx": emitted_dir[0],
                    "dy": emitted_dir[1],
                    "dz": emitted_dir[2],
                    "time_s": 0.0,
                    "weight": 1.0,
                    "ring_id": ring.ring_id,
                    "tile_id": tile_id,
                    "branch": branch,
                    "source_tag": "laue511_reference_single_ring",
                    "offaxis_x_rad": 0.0,
                    "offaxis_y_rad": 0.0,
                }
                if branch == "DIFFRACT":
                    phase.writerow(row)
                    focal_points.append((hit[0], hit[1]))
                else:
                    transmitted.writerow(row)

    metrics = {
        "ring_id": ring.ring_id,
        "n_photons": args.n_photons,
        "seed": args.seed,
        "counts": dict(counts),
        "fractions": branch_fractions(counts),
        "expected_probabilities": {
            "p_diff": probs.p_diff,
            "p_abs": probs.p_abs,
            "p_trans": probs.p_trans,
        },
        "focal_d90_mm": containment_diameter_mm(focal_points, 0.9),
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "run_config.json").write_text(json.dumps(vars(args), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps({"kernel": "laue511.reference", "ring_config": args.config}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(
        f"# Single-ring benchmark\n\nRing {ring.ring_id}, N={args.n_photons}, diffraction fraction={metrics['fractions']['DIFFRACT']:.6f}.\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
