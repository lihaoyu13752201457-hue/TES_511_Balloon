#!/usr/bin/env python3
"""Real-position delayed-source smoke test.

Goal
----
Prove that the delayed activation source can be emitted from the *exact* stored
RPIP production positions ("CC IP RP <VN> x y z ZA exc t"), one Cosima
``PointSource`` per sampled decay, instead of compressing positions into the
``RadialProfileBeam`` (z-bin + radial-profile) grid that the production Step03
source uses. The grid is coarse in the radial direction for thin-wall PCON
shells; direct point sampling has zero radial smearing.

Why this is feasible (and not a workflow blocker)
-------------------------------------------------
The "full sampling is astronomical" worry is a misconception. We do not emit one
source per production point (N ~ 7e5). We emit ``M`` decays (our choice, e.g.
the trigger budget), drawn *with replacement* and weighted by activity, from the
already-parsed exact point cloud. The exact points are already on disk at
``stepwise_maintenance/step03_delay_source/outputs/rpip_production_points_sample.csv``
(a 50k reservoir sample of true RPIP positions), so this builder does not even
need to re-read the multi-GB buildup SIM files.

Activity weighting / flux normalization
---------------------------------------
The RPIP sample is (approximately) uniform over *production* points, not over
*activity*. We reweight each point by

    w_point = Activity_Bq(VN, ZA) / n_sample_points(VN, ZA)

so that the per-species sampling probability is proportional to its day-15
activity. Because we importance-sample positions ~ activity, every emitted
``PointSource`` then carries an equal flux ``Flux = A_total / M``; the sum over
the M blocks reproduces the total inventory activity in expectation.

This is a *smoke test*: it uses the raw day-15 inventory activities (not the
ground-state-fixed activities) and a small M / trigger budget. It demonstrates
the method and that Cosima runs it; it is not a production rebuild.

Subcommands
-----------
    build   : write the PointSource .source (+ manifest + fidelity comparison)
    verify  : parse the cosima .sim output and confirm emitted positions
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "outputs"

RPIP_SAMPLE = (
    ROOT
    / "stepwise_maintenance"
    / "step03_delay_source"
    / "outputs"
    / "rpip_production_points_sample.csv"
)
INVENTORY = (
    ROOT
    / "stepwise_maintenance"
    / "step03_delay_source"
    / "source_snapshots"
    / "activation_inventory_day15.csv"
)
GEOMETRY = (
    ROOT
    / "outputs"
    / "geometry"
    / "XZTES_ADR_v4c_mkflange_cm"
    / "TibetTES_ADR_v4c_mkflange_cm.geo.setup"
)

SOURCE_OUT = OUT / "realpos_delayed_smoke.source"
MANIFEST_OUT = OUT / "realpos_smoke_manifest.json"
FIDELITY_OUT = OUT / "fidelity_vs_grid.csv"
VERIFY_OUT = OUT / "verify_summary.json"

OUTFILE_PREFIX = str((OUT / "realpos_delayed_smoke").resolve())
SIM_OUT = OUT / "realpos_delayed_smoke.inc1.id1.sim.gz"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_inventory_activity() -> dict[tuple[str, int], float]:
    """Sum day-15 activity per (VN, ZA) over excitation rows."""
    activity: dict[tuple[str, int], float] = defaultdict(float)
    with INVENTORY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                a = float(row["Activity_Bq"])
                za = int(row["ZA"])
            except (KeyError, ValueError):
                continue
            if a <= 0.0:
                continue
            activity[(row["VN"], za)] += a
    return dict(activity)


def load_rpip_points() -> list[dict]:
    points: list[dict] = []
    with RPIP_SAMPLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                points.append(
                    {
                        "x_cm": float(row["x_cm"]),
                        "y_cm": float(row["y_cm"]),
                        "z_cm": float(row["z_cm"]),
                        "VN": row["VN"],
                        "ZA": int(row["ZA"]),
                        "nuclide": row.get("nuclide", ""),
                    }
                )
            except (KeyError, ValueError):
                continue
    return points


# --------------------------------------------------------------------------- #
# Activity-weighted sampling of exact positions
# --------------------------------------------------------------------------- #
def assign_activity_weights(
    points: list[dict], activity: dict[tuple[str, int], float]
) -> list[float]:
    counts: dict[tuple[str, int], int] = defaultdict(int)
    for p in points:
        counts[(p["VN"], p["ZA"])] += 1
    weights = []
    for p in points:
        key = (p["VN"], p["ZA"])
        n = counts[key]
        weights.append(activity.get(key, 0.0) / n if n else 0.0)
    return weights


def weighted_sample_indices(weights: list[float], m: int, seed: int) -> list[int]:
    total = sum(weights)
    if total <= 0.0:
        raise SystemExit("No positive-activity RPIP points to sample from.")
    cdf = []
    run = 0.0
    for w in weights:
        run += w
        cdf.append(run)
    rng = random.Random(seed)
    out = []
    for _ in range(m):
        x = rng.random() * total
        lo, hi = 0, len(cdf) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cdf[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        out.append(lo)
    return out


# --------------------------------------------------------------------------- #
# Cosima .source writer (exact-position PointSource per decay)
# --------------------------------------------------------------------------- #
def write_source(sampled: list[dict], flux_per_block: float, triggers: int) -> None:
    geo = GEOMETRY.resolve()
    lines = [
        "Version 1",
        f"Geometry {geo}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {OUTFILE_PREFIX}",
        f"DecayRun.Triggers {int(triggers)}",
        "",
    ]
    for i, _p in enumerate(sampled):
        lines.append(f"DecayRun.Source RP_{i:06d}")
    lines.append("\n# ===== exact-position PointSource decay blocks =====")
    for i, p in enumerate(sampled):
        name = f"RP_{i:06d}"
        lines.append(f"{name}.ParticleType {int(p['ZA'])}")
        # Near-field isotropic point at the exact RPIP production position (cm).
        lines.append(
            f"{name}.Beam PointSource {p['x_cm']:.6f} {p['y_cm']:.6f} {p['z_cm']:.6f}"
        )
        lines.append(f"{name}.Flux {flux_per_block:.8e}")
        lines.append("")
    SOURCE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Fidelity comparison vs the (r,z)-grid RadialProfileBeam representation
# --------------------------------------------------------------------------- #
def fidelity_vs_grid(points: list[dict], z_bins: int, r_bins: int) -> list[dict]:
    """For each volume, quantify radial smearing the grid would introduce.

    The production CsI source used --z-bins 10 --r-bins 20. The grid replaces
    every exact in-wall radius by a bin whose width is r_max(volume)/r_bins,
    and regenerates azimuth uniformly. We report, per volume, the true radial
    extent (the "wall") and the grid bin width: if bin_width is a large fraction
    of the wall extent, the grid cannot resolve the in-wall production gradient.
    """
    by_vol: dict[str, list[dict]] = defaultdict(list)
    for p in points:
        by_vol[p["VN"]].append(p)
    rows = []
    for vn, pts in by_vol.items():
        rs = [math.hypot(p["x_cm"], p["y_cm"]) for p in pts]
        zs = [p["z_cm"] for p in pts]
        r_min, r_max = min(rs), max(rs)
        wall = r_max - r_min
        # grid radial bin edges run 0 .. ~r_max (percentile in builder); use r_max.
        r_bin_width = (r_max / r_bins) if r_max > 0 else 0.0
        bins_across_wall = (wall / r_bin_width) if r_bin_width > 0 else 0.0
        rows.append(
            {
                "VN": vn,
                "n_points": len(pts),
                "r_min_cm": round(r_min, 4),
                "r_max_cm": round(r_max, 4),
                "wall_radial_extent_cm": round(wall, 4),
                "z_extent_cm": round(max(zs) - min(zs), 4),
                "grid_r_bin_width_cm": round(r_bin_width, 4),
                "grid_bins_across_wall": round(bins_across_wall, 3),
            }
        )
    rows.sort(key=lambda d: d["n_points"], reverse=True)
    return rows


def cmd_build(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    activity = load_inventory_activity()
    points = load_rpip_points()
    total_activity = sum(activity.values())
    weights = assign_activity_weights(points, activity)
    idx = weighted_sample_indices(weights, args.n_decays, args.seed)
    sampled = [points[i] for i in idx]
    flux_per_block = total_activity / args.n_decays
    write_source(sampled, flux_per_block, args.triggers)

    fidelity = fidelity_vs_grid(points, z_bins=10, r_bins=20)
    with FIDELITY_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fidelity[0].keys()))
        writer.writeheader()
        writer.writerows(fidelity)

    species_drawn = sorted({(p["VN"], p["ZA"]) for p in sampled})
    manifest = {
        "method": "exact_RPIP_PointSource_per_decay_activity_weighted_with_replacement",
        "geometry": str(GEOMETRY.resolve()),
        "rpip_sample_points_available": len(points),
        "positive_activity_species": len(activity),
        "total_inventory_activity_Bq_day15": total_activity,
        "n_decays_emitted": args.n_decays,
        "flux_per_pointsource_Bq": flux_per_block,
        "sum_flux_check_Bq": flux_per_block * args.n_decays,
        "triggers_requested": args.triggers,
        "distinct_species_in_draw": len(species_drawn),
        "source_file": str(SOURCE_OUT),
        "beam_keyword": "PointSource (near-field isotropic, cm)",
        "note": (
            "Raw day-15 inventory activities used (not ground-state-fixed); "
            "smoke-scale M and triggers. Production rebuild would use the "
            "fixed activities and M=trigger budget."
        ),
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"\n[OK] wrote {SOURCE_OUT}")
    print(f"[OK] wrote {FIDELITY_OUT}")
    worst = max(fidelity, key=lambda d: d["grid_bins_across_wall"])
    print(
        "[fidelity] highest-stat volume "
        f"{fidelity[0]['VN']}: wall={fidelity[0]['wall_radial_extent_cm']} cm, "
        f"grid bin={fidelity[0]['grid_r_bin_width_cm']} cm "
        f"=> only {fidelity[0]['grid_bins_across_wall']} bins across the wall"
    )
    return 0


# --------------------------------------------------------------------------- #
# Verify the cosima sim output
# --------------------------------------------------------------------------- #
def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def cmd_verify(args: argparse.Namespace) -> int:
    sim = SIM_OUT if SIM_OUT.exists() else None
    if sim is None:
        # cosima may write uncompressed
        alt = OUT / "realpos_delayed_smoke.inc1.id1.sim"
        sim = alt if alt.exists() else None
    if sim is None:
        raise SystemExit(f"No sim output found in {OUT}")

    sampled_points: set[tuple[float, float, float]] = set()
    # rebuild the exact draw to confirm emitted IA INIT positions are a subset
    activity = load_inventory_activity()
    points = load_rpip_points()
    weights = assign_activity_weights(points, activity)
    idx = weighted_sample_indices(weights, args.n_decays, args.seed)
    for i in idx:
        p = points[i]
        sampled_points.add((round(p["x_cm"], 3), round(p["y_cm"], 3), round(p["z_cm"], 3)))

    n_events = 0
    n_ia_init = 0
    matched_positions = 0
    checked_positions = 0
    with open_text(sim) as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("SE"):
                n_events += 1
            elif line.startswith("IA INIT"):
                n_ia_init += 1
                # MEGAlib IA line is ';'-delimited:
                # "IA INIT <id>; <orig>;<detid>;<t>; <x>; <y>; <z>;<...>"
                # fields[4],[5],[6] are the emission x/y/z in cm.
                parts = line.split(";")
                if len(parts) >= 7:
                    try:
                        x, y, z = float(parts[4]), float(parts[5]), float(parts[6])
                    except ValueError:
                        continue
                    checked_positions += 1
                    if (round(x, 3), round(y, 3), round(z, 3)) in sampled_points:
                        matched_positions += 1

    summary = {
        "sim_file": str(sim),
        "events_SE": n_events,
        "ia_init_lines": n_ia_init,
        "init_positions_checked": checked_positions,
        "init_positions_matching_exact_input": matched_positions,
        "match_fraction": (matched_positions / checked_positions) if checked_positions else None,
        "feasible": n_events > 0,
        "interpretation": (
            "events_SE>0 proves cosima parsed and ran thousands of exact-position "
            "PointSource decay blocks. A high match_fraction confirms decays are "
            "emitted from the exact RPIP coordinates (zero radial smearing), unlike "
            "the RadialProfileBeam grid."
        ),
    }
    VERIFY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="write the exact-position PointSource .source")
    b.add_argument("--n-decays", type=int, default=2000, help="M decays to emit")
    b.add_argument("--triggers", type=int, default=2000, help="cosima trigger budget")
    b.add_argument("--seed", type=int, default=260609)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="parse cosima sim and confirm exact positions")
    v.add_argument("--n-decays", type=int, default=2000)
    v.add_argument("--seed", type=int, default=260609)
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
