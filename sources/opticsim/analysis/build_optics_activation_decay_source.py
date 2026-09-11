#!/usr/bin/env python3
"""Build day-N optics activation decay-ion sources from true production positions.

The input is the Geant4 prompt-transport ``activation_inventory.csv`` written by
``all_particle_farfield_demo``. Each secondary ion candidate already carries its
production position in the optics coordinate system, so this script preserves the
same position for the delayed decay source instead of replacing it by a volume
center.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

SYMS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def parse_days(text: str) -> list[float]:
    days = []
    for item in text.split(","):
        item = item.strip()
        if item:
            days.append(float(item))
    return sorted(set(days))


def nuclide_name(z: int, a: int) -> str:
    if 0 < z < len(SYMS) and SYMS[z]:
        return f"{SYMS[z]}-{a}"
    return f"Z{z}-A{a}"


def load_driver_profile(path: Path | None) -> list[tuple[float, float]]:
    if path is None:
        return []
    rows = read_csv(path)
    grouped: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        if "time_s" in row and row.get("time_s", "") != "":
            time_s = safe_float(row["time_s"], 0.0)
        elif "day" in row and row.get("day", "") != "":
            time_s = safe_float(row["day"], 0.0) * 86400.0
        elif "day_mid" in row and row.get("day_mid", "") != "":
            time_s = safe_float(row["day_mid"], 0.0) * 86400.0
        else:
            continue
        scale = None
        for key in ("activation_driver", "scale_to_ref", "prompt_scale_to_ref", "scale_to_reference"):
            if key in row and row.get(key, "") != "":
                scale = safe_float(row[key], 1.0)
                break
        if scale is not None and scale >= 0.0:
            grouped[time_s].append(scale)
    profile = [(t, sum(vals) / len(vals)) for t, vals in grouped.items() if vals]
    profile.sort(key=lambda item: item[0])
    if profile and profile[0][0] > 0.0:
        profile.insert(0, (0.0, profile[0][1]))
    return profile


def activity_factor(lam: float, day: float, profile: list[tuple[float, float]]) -> float:
    end_s = day * 86400.0
    if end_s <= 0.0:
        return 0.0
    if not profile:
        return -math.expm1(-lam * end_s)

    inventory_per_rate = 0.0
    t = 0.0
    idx = 0
    scale = profile[0][1]
    while t < end_s:
        while idx + 1 < len(profile) and profile[idx + 1][0] <= t:
            idx += 1
            scale = profile[idx][1]
        next_t = end_s
        if idx + 1 < len(profile):
            next_t = min(next_t, profile[idx + 1][0])
        dt = max(0.0, next_t - t)
        if dt <= 0.0:
            t = next_t
            continue
        decay = math.exp(-lam * dt)
        inventory_per_rate = inventory_per_rate * decay + scale * (1.0 - decay) / lam
        t = next_t
    return lam * inventory_per_rate


def row_is_radioactive(row: dict[str, str]) -> bool:
    if safe_int(row.get("stable", "0"), 0) != 0:
        return False
    lifetime = safe_float(row.get("lifetime_s", "0"), 0.0)
    return lifetime > 0.0 and math.isfinite(lifetime)


def choose_index(cumulative: list[float], total: float, rng: random.Random) -> int:
    x = rng.random() * total
    lo, hi = 0, len(cumulative) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cumulative[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def build_sources(args: argparse.Namespace) -> dict[str, object]:
    inventory_rows = read_csv(args.inventory)
    outdir: Path = args.out
    outdir.mkdir(parents=True, exist_ok=True)
    profile = load_driver_profile(args.driver_profile)
    rng = random.Random(args.seed)
    days = parse_days(args.days)
    selected_day = args.day
    if selected_day not in days:
        days.append(selected_day)
        days = sorted(set(days))

    radioactive_rows = []
    skipped_stable = 0
    skipped_bad = 0
    for idx, row in enumerate(inventory_rows):
        if not row_is_radioactive(row):
            if safe_int(row.get("stable", "0"), 0) != 0:
                skipped_stable += 1
            else:
                skipped_bad += 1
            continue
        z = safe_int(row.get("Z", "0"), 0)
        a = safe_int(row.get("A", "0"), 0)
        lifetime = safe_float(row.get("lifetime_s", "0"), 0.0)
        weight = safe_float(row.get("weight", "1"), 1.0)
        if z <= 0 or a <= 0 or weight <= 0.0:
            skipped_bad += 1
            continue
        radioactive_rows.append((idx, row, z, a, lifetime, weight))

    activity_rows: list[dict[str, object]] = []
    per_row_activity: list[tuple[int, dict[str, str], float]] = []
    totals_by_day: dict[float, float] = defaultdict(float)
    for idx, row, z, a, lifetime, weight in radioactive_rows:
        lam = math.log(2.0) / lifetime
        production_rate = weight / args.source_duration_s
        volume = row.get("volume_name", "unknown")
        exc = safe_float(row.get("excitation_keV", "0"), 0.0)
        for day in days:
            factor = activity_factor(lam, day, profile)
            activity = production_rate * factor
            totals_by_day[day] += activity
            rec = {
                "day": day,
                "time_s": day * 86400.0,
                "inventory_row": idx,
                "volume_name": volume,
                "Z": z,
                "A": a,
                "ZA": z * 1000 + a,
                "nuclide": nuclide_name(z, a),
                "excitation_keV": exc,
                "lifetime_s": lifetime,
                "half_life_s": lifetime * math.log(2.0),
                "source_duration_s": args.source_duration_s,
                "production_weight_atoms": weight,
                "production_rate_atoms_s": production_rate,
                "activity_Bq": activity,
                "activity_factor": factor,
                "x_mm": row.get("x_mm", "0"),
                "y_mm": row.get("y_mm", "0"),
                "z_mm": row.get("z_mm", "0"),
                "creator_process": row.get("creator_process", ""),
                "source_particle_name": row.get("source_particle_name", ""),
                "source_pdg_encoding": row.get("source_pdg_encoding", ""),
            }
            activity_rows.append(rec)
            if abs(day - selected_day) < 1.0e-9 and activity > 0.0:
                per_row_activity.append((idx, row, activity))

    fields = [
        "day", "time_s", "inventory_row", "volume_name", "Z", "A", "ZA", "nuclide",
        "excitation_keV", "lifetime_s", "half_life_s", "source_duration_s",
        "production_weight_atoms", "production_rate_atoms_s", "activity_Bq",
        "activity_factor", "x_mm", "y_mm", "z_mm", "creator_process",
        "source_particle_name", "source_pdg_encoding",
    ]
    write_csv(outdir / "activity_by_day_position.csv", activity_rows, fields)
    total_rows = [
        {"day": day, "time_s": day * 86400.0, "total_activity_Bq": totals_by_day.get(day, 0.0)}
        for day in days
    ]
    write_csv(outdir / "total_activity_by_day.csv", total_rows, ["day", "time_s", "total_activity_Bq"])

    decay_fields = [
        "event_id", "inventory_row", "day", "time_s", "Z", "A", "excitation_keV",
        "x_mm", "y_mm", "z_mm", "weight", "activity_Bq", "source_tag",
        "source_event_id", "source_particle_name", "source_pdg_encoding",
        "volume_name", "creator_process", "nuclide", "lifetime_s",
    ]
    decay_rows: list[dict[str, object]] = []
    total_activity = sum(activity for _, _, activity in per_row_activity)
    if total_activity > 0.0 and args.n_decays > 0:
        cumulative = []
        acc = 0.0
        for _, _, activity in per_row_activity:
            acc += activity
            cumulative.append(acc)
        per_event_weight = total_activity * args.observation_s / args.n_decays
        for event_id in range(args.n_decays):
            source_idx = choose_index(cumulative, total_activity, rng)
            inventory_idx, row, activity = per_row_activity[source_idx]
            z = safe_int(row.get("Z", "0"), 0)
            a = safe_int(row.get("A", "0"), 0)
            decay_rows.append({
                "event_id": event_id,
                "inventory_row": inventory_idx,
                "day": selected_day,
                "time_s": rng.random() * args.observation_s,
                "Z": z,
                "A": a,
                "excitation_keV": safe_float(row.get("excitation_keV", "0"), 0.0),
                "x_mm": row.get("x_mm", "0"),
                "y_mm": row.get("y_mm", "0"),
                "z_mm": row.get("z_mm", "0"),
                "weight": per_event_weight,
                "activity_Bq": activity,
                "source_tag": f"optics_activation_day{selected_day:g}",
                "source_event_id": row.get("source_event_id", ""),
                "source_particle_name": row.get("source_particle_name", ""),
                "source_pdg_encoding": row.get("source_pdg_encoding", ""),
                "volume_name": row.get("volume_name", ""),
                "creator_process": row.get("creator_process", ""),
                "nuclide": nuclide_name(z, a),
                "lifetime_s": safe_float(row.get("lifetime_s", "0"), 0.0),
            })
    decay_csv = outdir / f"optics_activation_decay_day{selected_day:g}_ions.csv"
    write_csv(decay_csv, decay_rows, decay_fields)

    summary = {
        "status": "PASS" if decay_rows else "NO_RADIOACTIVE_CANDIDATES",
        "inventory": str(args.inventory),
        "source_duration_s": args.source_duration_s,
        "day": selected_day,
        "days": days,
        "observation_s": args.observation_s,
        "driver_profile": str(args.driver_profile) if args.driver_profile else None,
        "driver_profile_points": len(profile),
        "n_inventory_rows": len(inventory_rows),
        "n_radioactive_rows": len(radioactive_rows),
        "n_skipped_stable_rows": skipped_stable,
        "n_skipped_bad_rows": skipped_bad,
        "total_activity_Bq_day": total_activity,
        "n_decay_source_rows": len(decay_rows),
        "decay_ion_source_csv": str(decay_csv),
        "activity_csv": str(outdir / "activity_by_day_position.csv"),
        "total_activity_csv": str(outdir / "total_activity_by_day.csv"),
        "normalization_note": "Decay ion rows are sampled from true isotope production positions. Row weight is total_activity_Bq * observation_s / n_decays.",
        "physics_note": "This is an optics-side RPIP-equivalent position-preserving delayed source builder; it does not add parent feeding.",
    }
    (outdir / "source_build_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-duration-s", type=float, default=10.0)
    parser.add_argument("--day", type=float, default=15.0)
    parser.add_argument("--days", default="1,5,10,15,20")
    parser.add_argument("--observation-s", type=float, default=1000.0)
    parser.add_argument("--n-decays", type=int, default=1000)
    parser.add_argument("--driver-profile", type=Path)
    parser.add_argument("--seed", type=int, default=20260520)
    args = parser.parse_args()
    if args.source_duration_s <= 0.0:
        raise SystemExit("--source-duration-s must be positive")
    if args.observation_s <= 0.0:
        raise SystemExit("--observation-s must be positive")
    print(json.dumps(build_sources(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
