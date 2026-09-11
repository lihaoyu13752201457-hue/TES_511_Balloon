#!/usr/bin/env python3
"""Build a constant-limit environment grid for next-phase 511 studies.

This is deliberately a reference-profile tool: it does not invent an EXPACS
flight model.  It records the time grid and assigns scale_to_ref = 1.0 so the
time-variable machinery can be tested against the existing static day-15 chain.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "configs" / "nextphase" / "flight_profile_template.csv"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid"
DEFAULT_PARTICLES = ["gamma", "eplus", "eminus", "p", "n", "alpha", "muplus", "muminus"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_environment_grid(profile: Path, outdir: Path, particles: list[str]) -> dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    profile_rows = read_csv(profile)
    if not profile_rows:
        raise SystemExit(f"empty flight profile: {profile}")

    env_rows: list[dict[str, object]] = []
    particle_rows: list[dict[str, object]] = []
    angle_rows: list[dict[str, object]] = []
    transmission_rows: list[dict[str, object]] = []

    for row in profile_rows:
        time_s = float(row["time_s"])
        day = float(row.get("day") or time_s / 86400.0)
        live = float(row.get("livetime_fraction") or 1.0)
        base = {
            "time_s": time_s,
            "day": day,
            "altitude_km": row.get("altitude_km", ""),
            "latitude_deg": row.get("latitude_deg", ""),
            "longitude_deg": row.get("longitude_deg", ""),
            "profile_id": row.get("profile_id", "constant_reference"),
        }
        for particle in particles:
            env_rows.append({
                **base,
                "particle": particle,
                "angle_bin": "all",
                "energy_bin": "all",
                "E_low_keV": "",
                "E_high_keV": "",
                "flux_cm2_s": "",
                "scale_to_ref": live,
                "model_note": "constant reference; no new EXPACS scaling applied",
            })
            particle_rows.append({
                **base,
                "particle": particle,
                "livetime_fraction": live,
                "scale_to_ref": live,
            })
        angle_rows.append({
            **base,
            "angle_bin": "all",
            "livetime_fraction": live,
            "scale_to_ref": live,
        })
        transmission_rows.append({
            **base,
            "atmosphere_transmission_511": 1.0,
            "model_note": "constant reference placeholder for optical/atmospheric attenuation gate",
        })

    write_csv(outdir / "env_grid.csv", env_rows, [
        "time_s", "day", "altitude_km", "latitude_deg", "longitude_deg", "profile_id",
        "particle", "angle_bin", "energy_bin", "E_low_keV", "E_high_keV",
        "flux_cm2_s", "scale_to_ref", "model_note",
    ])
    write_csv(outdir / "particle_flux_by_time.csv", particle_rows, [
        "time_s", "day", "altitude_km", "latitude_deg", "longitude_deg", "profile_id",
        "particle", "livetime_fraction", "scale_to_ref",
    ])
    write_csv(outdir / "angle_flux_by_time.csv", angle_rows, [
        "time_s", "day", "altitude_km", "latitude_deg", "longitude_deg", "profile_id",
        "angle_bin", "livetime_fraction", "scale_to_ref",
    ])
    write_csv(outdir / "atmosphere_transmission_511_by_time.csv", transmission_rows, [
        "time_s", "day", "altitude_km", "latitude_deg", "longitude_deg", "profile_id",
        "atmosphere_transmission_511", "model_note",
    ])

    summary = {
        "status": "ok",
        "mode": "constant_reference",
        "flight_profile": str(profile.relative_to(ROOT) if profile.is_relative_to(ROOT) else profile),
        "n_profile_rows": len(profile_rows),
        "particles": particles,
        "scale_to_ref_min": min(float(r["scale_to_ref"]) for r in env_rows),
        "scale_to_ref_max": max(float(r["scale_to_ref"]) for r in env_rows),
        "outputs": [
            "env_grid.csv",
            "particle_flux_by_time.csv",
            "angle_flux_by_time.csv",
            "atmosphere_transmission_511_by_time.csv",
        ],
        "caveat": "This grid only validates the constant-profile limit; it is not a real flight radiation model.",
    }
    (outdir / "environment_grid_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flight-profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--particles", default=",".join(DEFAULT_PARTICLES))
    args = parser.parse_args()

    particles = [p.strip() for p in args.particles.split(",") if p.strip()]
    summary = build_environment_grid(args.flight_profile, args.out, particles)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
