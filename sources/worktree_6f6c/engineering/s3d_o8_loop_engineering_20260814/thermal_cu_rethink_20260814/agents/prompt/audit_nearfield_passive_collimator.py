#!/usr/bin/env python3
"""Read-only denominator audit for a passive, signal-axis near-field cage.

No transport is performed.  Raw SIMs are streamed and only counters are kept.
The topology under test is deliberately geometric:

* focused-beam front aperture along InstrumentFrame +x;
* side/back passive cage outside the existing TES/support envelope;
* no claim that crossing passive material is absorption or suppression.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
RAW_ROOT = Path("/home/ubuntu/TES_511_Balloon")
MANIFEST = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/"
    "outputs/01_prompt/prompt_input_manifest.csv"
)
EVENTLIST = Path(
    "/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/"
    "outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
DELAYED = HERE.parent / "delayed/delayed_annihilation_sibling_events.csv"
PROMPT_PATHS = (
    HERE.parents[2]
    / "reconsideration_20260814/agents/prompt/annihilation_partner_paths.csv"
)

ENERGY_EDGES_KEV = (0.0, 1022.0, 2000.0, 4000.0, 5000.0, 6000.0,
                    8000.0, 12000.0, 20000.0, 50000.0, math.inf)
SQRT_HALF = math.sqrt(0.5)

# Legacy L0--L4 analysis box used for the original denominator pass.  It omits
# L5 and therefore must not be used to classify event 8081 or a full six-layer
# TES acceptance.  See BOX_REMOVAL_PROMPT_REVIEW.md for the full-CSG erratum.
TES_BOX = ((-3.15, 1.95), (-1.8, 1.8), (-7.0, -3.4))
# A support-clear cage cannot intrude through the existing +/-2.2 cm supports.
CAGE_BOX = ((-4.35125, 3.60), (-4.0, 4.0), (-9.2, -1.2))
SIGNAL_X_RANGE = (-4.35125, 2.30)
APERTURES_CM = (1.20, 1.30, 1.40, 1.45, 1.50, 1.60, 1.70, 1.80, 1.85)


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    return SQRT_HALF * (x - z), y, SQRT_HALF * (x + z)


def energy_bin(energy_kev: float) -> int:
    for i in range(len(ENERGY_EDGES_KEV) - 1):
        if ENERGY_EDGES_KEV[i] <= energy_kev < ENERGY_EDGES_KEV[i + 1]:
            return i
    raise AssertionError(energy_kev)


def ray_box_entry(
    point: tuple[float, float, float],
    direction: tuple[float, float, float],
    box: tuple[tuple[float, float], ...],
) -> tuple[str, float, float] | None:
    """Return forward entry face and [entry,exit] t for an axis-aligned box."""
    names = (("front_-x", "back_+x"), ("side_y-", "side_y+"),
             ("side_z-", "side_z+"))
    t_enter = -math.inf
    t_exit = math.inf
    face = ""
    inside = True
    for i, ((lo, hi), p, d) in enumerate(zip(box, point, direction)):
        inside = inside and lo <= p <= hi
        if abs(d) < 1.0e-14:
            if not lo <= p <= hi:
                return None
            continue
        a = (lo - p) / d
        b = (hi - p) / d
        near_face = names[i][0] if a <= b else names[i][1]
        if a > b:
            a, b = b, a
        if a > t_enter:
            t_enter = a
            face = near_face
        t_exit = min(t_exit, b)
        if t_enter > t_exit:
            return None
    if t_exit < 0.0:
        return None
    return ("origin_inside" if inside else face, max(0.0, t_enter), t_exit)


def parse_init(line: str) -> tuple[float, float, float, float, float, float, float]:
    fields = [field.strip() for field in line[len("IA INIT") :].split(";")]
    return (
        float(fields[4]), float(fields[5]), float(fields[6]),
        float(fields[16]), float(fields[17]), float(fields[18]),
        float(fields[22]),
    )


def parse_prompt_shard(task: tuple[str, int]) -> dict:
    path, declared = task
    counts: Counter[tuple[int, str, str]] = Counter()
    parsed = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("IA INIT"):
                continue
            x, y, z, dx, dy, dz, energy = parse_init(line)
            p_if = world_to_if(x, y, z)
            d_if = world_to_if(dx, dy, dz)
            norm = math.sqrt(sum(v * v for v in d_if))
            d_if = tuple(v / norm for v in d_if)
            ebin = energy_bin(energy)
            tes = ray_box_entry(p_if, d_if, TES_BOX)
            cage = ray_box_entry(p_if, d_if, CAGE_BOX)
            counts[(ebin, "all", "all")] += 1
            if tes is not None:
                counts[(ebin, "tes_box", tes[0])] += 1
            if cage is not None:
                counts[(ebin, "cage_box", cage[0])] += 1
            parsed += 1
    if parsed != declared:
        raise RuntimeError(f"{path}: parsed {parsed}, declared {declared}")
    return {"path": path, "parsed": parsed, "counts": list((*key, n) for key, n in counts.items())}


def prompt_denominator() -> tuple[list[dict], int, int]:
    tasks: list[tuple[str, int]] = []
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if (row["geometry"], row["family"], row["mode"]) != ("S3d_O8", "gamma", "instant"):
                continue
            path = str((RAW_ROOT / row["sim_path"]).resolve())
            tasks.append((path, int(row["events"])))
    total: Counter[tuple[int, str, str]] = Counter()
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(parse_prompt_shard, task) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            result = future.result()
            for ebin, surface, face, n in result["counts"]:
                total[(ebin, surface, face)] += n
            if done == 1 or done % 20 == 0 or done == len(tasks):
                print(f"prompt shards {done}/{len(tasks)}", flush=True)
    rows = []
    for ebin in range(len(ENERGY_EDGES_KEV) - 1):
        n_all = total[(ebin, "all", "all")]
        for surface in ("tes_box", "cage_box"):
            for face in ("front_-x", "back_+x", "side_y-", "side_y+",
                         "side_z-", "side_z+", "origin_inside", "miss"):
                n = total[(ebin, surface, face)]
                rows.append({
                    "energy_bin": ebin,
                    "energy_lo_keV": ENERGY_EDGES_KEV[ebin],
                    "energy_hi_keV": ENERGY_EDGES_KEV[ebin + 1],
                    "surface": surface,
                    "entry_class": face,
                    "incident_histories": n_all,
                    "intersecting_histories": n,
                    "fraction_of_incident": n / n_all if n_all else math.nan,
                })
    return rows, len(tasks), sum(total[(i, "all", "all")] for i in range(len(ENERGY_EDGES_KEV) - 1))


def signal_acceptance() -> tuple[list[dict], dict]:
    rays = []
    theta = []
    for line in EVENTLIST.open(encoding="utf-8"):
        fields = line.split()
        x, y, z = map(float, fields[5:8])
        dx, dy, dz = map(float, fields[8:11])
        p_if = world_to_if(x, y, z)
        d_if = world_to_if(dx, dy, dz)
        norm = math.sqrt(sum(v * v for v in d_if))
        d_if = tuple(v / norm for v in d_if)
        points = []
        for x_plane in SIGNAL_X_RANGE:
            t = (x_plane - p_if[0]) / d_if[0]
            points.append((p_if[1] + t * d_if[1], p_if[2] + t * d_if[2] + 5.2))
        max_square = max(abs(v) for point in points for v in point)
        max_circle = max(math.hypot(*point) for point in points)
        rays.append((max_square, max_circle))
        theta.append(math.degrees(math.acos(max(-1.0, min(1.0, d_if[0])))))
    rows = []
    for aperture in APERTURES_CM:
        for shape, index in (("square_halfwidth", 0), ("circle_radius", 1)):
            accepted = sum(ray[index] <= aperture for ray in rays)
            rows.append({
                "shape": shape,
                "aperture_cm": aperture,
                "signal_rays": len(rays),
                "geometrically_accepted": accepted,
                "geometric_acceptance": accepted / len(rays),
                "claim_boundary": "straight INIT ray only; not transported Aeff",
            })
    summary = {
        "rows": len(rays),
        "theta_min_deg": min(theta),
        "theta_max_deg": max(theta),
        "max_required_square_halfwidth_cm": max(ray[0] for ray in rays),
        "max_required_circle_radius_cm": max(ray[1] for ray in rays),
    }
    return rows, summary


def delayed_faces() -> tuple[list[dict], dict]:
    counters: dict[str, list[float]] = {}
    total_weight = 0.0
    with DELAYED.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            weight = float(row["mission_counts_20d_baseline_live"])
            total_weight += weight
            if not row["tes_511_IF_dx"]:
                key = "untraceable"
            else:
                p_if = world_to_if(
                    float(row["annihilation_world_x_cm"]),
                    float(row["annihilation_world_y_cm"]),
                    float(row["annihilation_world_z_cm"]),
                )
                d_if = tuple(float(row[name]) for name in (
                    "tes_511_IF_dx", "tes_511_IF_dy", "tes_511_IF_dz"
                ))
                hit = ray_box_entry(p_if, d_if, TES_BOX)
                key = hit[0] if hit else "straight_ray_misses_TES_box"
            values = counters.setdefault(key, [0.0, 0.0, 0.0])
            values[0] += 1
            values[1] += weight
            values[2] += weight * weight
    rows = []
    for key, (n, weight, sumw2) in sorted(counters.items(), key=lambda item: -item[1][1]):
        rows.append({
            "entry_class": key,
            "selected_rows": int(n),
            "mission_counts": weight,
            "mission_fraction": weight / total_weight,
            "mission_neff": weight * weight / sumw2 if sumw2 else 0.0,
            "interpretation": (
                "geometric front-aperture bypass" if key == "front_-x" else
                "ancestry photon is not direct-to-box; scattered path UNKNOWN" if key == "straight_ray_misses_TES_box" else
                "candidate passive-cage geometric opportunity only"
            ),
        })
    return rows, {"total_rows": int(sum(v[0] for v in counters.values())), "total_mission_counts": total_weight}


def prompt_leak_faces() -> list[dict]:
    rows = []
    with PROMPT_PATHS.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["geometry"] != "S3d_O8":
                continue
            p_if = world_to_if(float(row["annihilation_x_cm"]), float(row["annihilation_y_cm"]), float(row["annihilation_z_cm"]))
            d_if = world_to_if(float(row["tes_511_dx"]), float(row["tes_511_dy"]), float(row["tes_511_dz"]))
            hit = ray_box_entry(p_if, d_if, TES_BOX)
            rows.append({
                "event_id": row["event_id"],
                "init_energy_keV": row["init_energy_keV"],
                "pair_material": row["pair_material"],
                "annihilation_material": row["annihilation_material"],
                "straight_tes_511_entry_class": hit[0] if hit else "straight_ray_misses_TES_box",
                "status": "MECHANISM_TAG_ONLY__THREE_EVENTS_NOT_DIRECTION_DENOMINATOR",
            })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    signal_rows, signal_summary = signal_acceptance()
    delayed_rows, delayed_summary = delayed_faces()
    leak_rows = prompt_leak_faces()
    prompt_rows, shards, prompt_histories = prompt_denominator()
    write_csv(HERE / "passive_collimator_signal_acceptance.csv", signal_rows)
    write_csv(HERE / "passive_collimator_delayed_faces.csv", delayed_rows)
    write_csv(HERE / "passive_collimator_prompt_leaks.csv", leak_rows)
    write_csv(HERE / "passive_collimator_prompt_denominator.csv", prompt_rows)
    summary = {
        "status": "READ_ONLY_GEOMETRIC_AUDIT__NOT_TRANSPORT",
        "candidate": "near-field passive side/back cage with focused +IF-x aperture",
        "signal": signal_summary,
        "delayed": delayed_summary,
        "prompt_shards": shards,
        "prompt_histories": prompt_histories,
        "tes_box_IF_cm": TES_BOX,
        "cage_box_IF_cm": CAGE_BOX,
        "signal_x_range_IF_cm": SIGNAL_X_RANGE,
    }
    (HERE / "passive_collimator_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
