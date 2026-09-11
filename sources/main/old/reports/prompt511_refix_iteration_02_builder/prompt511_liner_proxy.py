#!/usr/bin/env python3
"""Cheap prompt-511 liner proxy for iteration 02 candidates.

This is a geometry screen only unless mu/rho and density are supplied. It traces
the selected prompt-eplus annihilation-to-TES records through a candidate radial
liner and classifies rays as caught by solid liner, through the signal port, or
missed/inside the proxy shell. It is not an MC result and does not include
self-annihilation add-back, neutron production, delayed activation, or signal replay.
"""
import argparse
import json
import math
from pathlib import Path

RECORDS = (
    Path(__file__).resolve().parents[1]
    / "prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json"
)


def cross_radius(a, t, radius):
    d = [t[i] - a[i] for i in range(3)]
    aa = d[0] * d[0] + d[1] * d[1]
    if aa == 0:
        return None
    bb = 2 * (a[0] * d[0] + a[1] * d[1])
    cc = a[0] * a[0] + a[1] * a[1] - radius * radius
    disc = bb * bb - 4 * aa * cc
    if disc < 0:
        return None
    root = math.sqrt(disc)
    for s in sorted(((-bb - root) / (2 * aa), (-bb + root) / (2 * aa))):
        if 0 <= s <= 1:
            return [a[i] + d[i] * s for i in range(3)]
    return None


def in_port(point, phi_min, phi_max, z_min, z_max):
    phi = math.degrees(math.atan2(point[1], point[0])) % 360
    return phi_min <= phi <= phi_max and z_min <= point[2] <= z_max


def classify_ray(a, t, rin, rout, phi_min, phi_max, z_min, z_max, samples):
    crossings = []
    for i in range(samples):
        radius = rin + (rout - rin) * i / (samples - 1)
        point = cross_radius(a, t, radius)
        if point is not None:
            crossings.append(point)
    if not crossings:
        return "miss_or_inside"
    if all(in_port(p, phi_min, phi_max, z_min, z_max) for p in crossings):
        return "through_port"
    return "caught_solid"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--material", required=True)
    ap.add_argument("--rin", type=float, required=True)
    ap.add_argument("--rout", type=float, required=True)
    ap.add_argument("--phi-min", type=float, default=171.0)
    ap.add_argument("--phi-max", type=float, default=189.0)
    ap.add_argument("--z-min", type=float, default=-7.2)
    ap.add_argument("--z-max", type=float, default=-3.2)
    ap.add_argument("--samples", type=int, default=33)
    ap.add_argument("--mu-rho", type=float, default=None)
    ap.add_argument("--density", type=float, default=None)
    args = ap.parse_args()

    records = json.loads(RECORDS.read_text())
    totals = {"caught_solid": 0.0, "through_port": 0.0, "miss_or_inside": 0.0}
    counts = {"caught_solid": 0, "through_port": 0, "miss_or_inside": 0}
    for rec in records:
        label = classify_ray(
            rec["annihilation_local_cm"],
            rec["tes_centroid_local_cm"],
            args.rin,
            args.rout,
            args.phi_min,
            args.phi_max,
            args.z_min,
            args.z_max,
            args.samples,
        )
        totals[label] += rec["rate_s-1"]
        counts[label] += 1

    total_cps = sum(rec["rate_s-1"] for rec in records)
    out = {
        "candidate": args.candidate,
        "material": args.material,
        "rin_cm": args.rin,
        "rout_cm": args.rout,
        "radial_thickness_cm": args.rout - args.rin,
        "port_phi_deg": [args.phi_min, args.phi_max],
        "port_z_cm": [args.z_min, args.z_max],
        "records": len(records),
        "baseline_prompt_eplus_cps_in_records": total_cps,
        "classification_cps": totals,
        "classification_counts": counts,
        "caught_fraction": totals["caught_solid"] / total_cps if total_cps else None,
        "proxy_scope": "geometric catch screen; not MC closure",
        "caveats": [
            "selected-tag prompt-eplus records only",
            "no self-annihilation 511 add-back transport",
            "no neutron or delayed activation estimate",
            "no signal replay",
        ],
    }
    if args.mu_rho is not None and args.density is not None:
        mu = args.mu_rho * args.density
        transmission = math.exp(-mu * (args.rout - args.rin))
        out["simple_attenuation"] = {
            "mu_rho_cm2_g": args.mu_rho,
            "density_g_cm3": args.density,
            "linear_mu_cm-1": mu,
            "radial_transmission": transmission,
            "radial_absorption": 1.0 - transmission,
            "residual_cps_from_proxy": (
                totals["caught_solid"] * transmission
                + totals["through_port"]
                + totals["miss_or_inside"]
            ),
            "note": "radial-thickness attenuation only; MC is required for prompt closure",
        }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
