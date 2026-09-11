#!/usr/bin/env python3
"""Stream existing S3d-O8 BUILDUP SIMs to recover target production origins.

No transport is launched and no raw artifact is copied.  Three incident-family
cells (n, p, alpha) are scanned independently.  Every IA INIT contributes to
the incident energy/direction denominator; only requested isotope/component RP
records are retained as small output rows.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
SOURCE_MAIN = Path("/home/ubuntu/TES_511_Balloon")
CATALOG = (
    SOURCE_MAIN
    / "runs/particle_source_unit_repair_20260811/"
    "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/"
    "catalog_v1/catalog.json"
)
INVENTORY = (
    Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
    / "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv"
)
BUBBLES = HERE / "delayed_position_bubbles.csv"

FAMILIES = ("n", "p", "alpha")
SPECIFIED_ZA = {29061, 29062, 29064, 39085, 41089, 41090, 27054}
EXPECTED_SUM_TT = {"n": 44.5656746, "p": 20.0382191, "alpha": 33.6719935}

CC_RP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<volume>\S+)\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+"
    r"(?P<z>[-+0-9.eE]+)\s+(?P<za>\d+)\s+"
    r"(?P<exc>[-+0-9.eE]+)\s+(?P<t>[-+0-9.eE]+)"
    r"(?:\s+tid=(?P<tid>\d+)\s+pid=(?P<pid>\d+)\s+"
    r"sproc=(?P<sproc>\S+)\s+prim=(?P<prim>\S+)\s+"
    r"par=(?P<par>\S+)\s+cproc=(?P<cproc>\S+))?"
)

ELEMENTS = (
    "n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
    "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn "
    "Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re "
    "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm "
    "Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()


def isotope_label(za: int) -> str:
    z, a = divmod(int(za), 1000)
    return f"{ELEMENTS[z] if z < len(ELEMENTS) else f'Z{z}'}-{a}"


def component_group(volume: str) -> str:
    if volume == "ColdPlate_MXC_50mK_SD_anchor":
        return "MXC_50mK_plate"
    if volume == "Nb_MagShield_Inner_Cylinder_2mm":
        return "Nb_inner_cylinder"
    if volume == "Cu_50mK_StillLike_Can_bottom_cap_2mm":
        return "can_50mK_bottom"
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L5_"):
        return "L5_Cu_support"
    if volume == "Cu_SubstrateSupport_SolidDisk_L0_deepest":
        return "L0_Cu_disk"
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L2_"):
        return "L2_Cu_support"
    if volume == "MuMetal_MagShield_Outer_Cylinder_2mm":
        return "MuMetal_outer_cylinder"
    if "Ag" in volume or "Sinter" in volume:
        return "Ag_sinter_proxy"
    return "Other"


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def direction_angles(dx: float, dy: float, dz: float) -> tuple[float, float]:
    ifx, ify, ifz = world_to_if(dx, dy, dz)
    norm = math.sqrt(ifx * ifx + ify * ify + ifz * ifz)
    if norm <= 0.0:
        raise RuntimeError("zero IA INIT direction")
    ifx, ify, ifz = ifx / norm, ify / norm, ifz / norm
    theta = math.degrees(math.acos(max(-1.0, min(1.0, ifx))))
    azimuth = math.degrees(math.atan2(ifz, ify)) % 360.0
    return theta, azimuth


def energy_bin(energy: float) -> tuple[float, float]:
    if energy <= 0.0:
        return 0.0, 0.0
    power = math.floor(math.log10(energy))
    lo = 10.0**power
    return lo, 10.0 * lo


def angle_bin(angle: float, width: float, upper: float) -> tuple[float, float]:
    index = min(int(angle // width), int(upper // width) - 1)
    return index * width, (index + 1) * width


def parse_init(line: str) -> dict[str, float | int]:
    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise RuntimeError(f"malformed IA INIT: {line.rstrip()}")
    dx, dy, dz = float(fields[16]), float(fields[17]), float(fields[18])
    theta, azimuth = direction_angles(dx, dy, dz)
    energy = float(fields[22])
    elo, ehi = energy_bin(energy)
    tlo, thi = angle_bin(theta, 30.0, 180.0)
    alo, ahi = angle_bin(azimuth, 45.0, 360.0)
    return {
        "primary_particle_id": int(fields[15]),
        "primary_x_cm": float(fields[4]),
        "primary_y_cm": float(fields[5]),
        "primary_z_cm": float(fields[6]),
        "primary_dir_x": dx,
        "primary_dir_y": dy,
        "primary_dir_z": dz,
        "primary_energy_keV": energy,
        "theta_from_IF_plus_x_deg": theta,
        "azimuth_about_IF_x_deg": azimuth,
        "energy_lo_keV": elo,
        "energy_hi_keV": ehi,
        "theta_lo_deg": tlo,
        "theta_hi_deg": thi,
        "azimuth_lo_deg": alo,
        "azimuth_hi_deg": ahi,
    }


def target_record(
    family: str,
    volume: str,
    za: int,
    selected_keys: set[tuple[str, str, int]],
) -> bool:
    component = component_group(volume)
    if component == "Other":
        return False
    return za in SPECIFIED_ZA or (family, volume, za) in selected_keys


def scan_family(args: tuple[str, list[dict[str, Any]], set[tuple[str, str, int]]]) -> dict[str, Any]:
    family, entries, selected_keys = args
    incident_bins: dict[tuple[float, ...], int] = defaultdict(int)
    target_rows: list[dict[str, Any]] = []
    events_seen = 0
    init_seen = 0
    rp_seen = 0
    expected_events = 0

    for entry in entries:
        sim = SOURCE_MAIN / entry["sim_reference"]["path"]
        expected_events += int(entry["events"])
        current_id: int | None = None
        current_init: dict[str, Any] | None = None
        current_targets: list[dict[str, Any]] = []

        def flush() -> None:
            nonlocal events_seen
            if current_id is None:
                return
            events_seen += 1
            if current_init is None:
                raise RuntimeError(f"{sim}: ID {current_id} lacks IA INIT")
            denominator_key = (
                current_init["energy_lo_keV"], current_init["energy_hi_keV"],
                current_init["theta_lo_deg"], current_init["theta_hi_deg"],
                current_init["azimuth_lo_deg"], current_init["azimuth_hi_deg"],
            )
            incident_bins[denominator_key] += 1
            for rp in current_targets:
                row = {
                    "family": family,
                    "job_id": entry["job_id"],
                    "batch_id": entry["batch_id"],
                    "simulation_file": str(sim),
                    "local_event_id": current_id,
                    "source_volume": rp["source_volume"],
                    "component_group": component_group(rp["source_volume"]),
                    "source_parent_ZA": rp["source_parent_ZA"],
                    "isotope": isotope_label(rp["source_parent_ZA"]),
                    "excitation_keV": rp["excitation_keV"],
                    "production_x_cm": rp["production_x_cm"],
                    "production_y_cm": rp["production_y_cm"],
                    "production_z_cm": rp["production_z_cm"],
                    "track_id": rp["track_id"],
                    "parent_track_id": rp["parent_track_id"],
                    "secondary_process": rp["secondary_process"],
                    "transport_primary": rp["transport_primary"],
                    "interacting_particle": rp["interacting_particle"],
                    "creator_process": rp["creator_process"],
                    "selected_W2_source_key": int((family, rp["source_volume"], rp["source_parent_ZA"]) in selected_keys),
                }
                row.update(current_init)
                target_rows.append(row)

        with gzip.open(sim, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                if raw.startswith("ID "):
                    flush()
                    parts = raw.split()
                    current_id = int(parts[1])
                    current_init = None
                    current_targets = []
                    continue
                if raw.startswith("IA INIT"):
                    current_init = parse_init(raw)
                    init_seen += 1
                    continue
                if not raw.startswith("CC IP RP "):
                    continue
                match = CC_RP_RE.match(raw)
                if match is None:
                    raise RuntimeError(f"unparsed CC IP RP: {raw.rstrip()}")
                volume = match.group("volume")
                za = int(match.group("za"))
                if not target_record(family, volume, za, selected_keys):
                    continue
                rp_seen += 1
                current_targets.append(
                    {
                        "source_volume": volume,
                        "source_parent_ZA": za,
                        "excitation_keV": float(match.group("exc")),
                        "production_x_cm": float(match.group("x")),
                        "production_y_cm": float(match.group("y")),
                        "production_z_cm": float(match.group("z")),
                        "track_id": int(match.group("tid")) if match.group("tid") else -1,
                        "parent_track_id": int(match.group("pid")) if match.group("pid") else -1,
                        "secondary_process": match.group("sproc") or "UNKNOWN",
                        "transport_primary": match.group("prim") or "UNKNOWN",
                        "interacting_particle": match.group("par") or "UNKNOWN",
                        "creator_process": match.group("cproc") or "UNKNOWN",
                    }
                )
        flush()
    if events_seen != expected_events or init_seen != expected_events:
        raise RuntimeError(
            f"{family}: event/init closure {events_seen}/{init_seen}, expected {expected_events}"
        )
    return {
        "family": family,
        "events_seen": events_seen,
        "init_seen": init_seen,
        "target_rp_seen": rp_seen,
        "incident_bins": incident_bins,
        "target_rows": target_rows,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def main() -> None:
    if not BUBBLES.is_file():
        raise RuntimeError("run analyze_delayed.py before scanning production origins")
    selected_keys = {
        (row["family"], row["source_volume"], int(row["source_parent_ZA"]))
        for row in read_csv(BUBBLES)
        if row["family"] in FAMILIES and row["component_group"] != "Other"
    }
    inventory_rows = [
        row for row in read_csv(INVENTORY)
        if row["geometry"] == "S3d_O8"
        and row["incident_family"] in FAMILIES
        and row["source_disposition"] == "transported_ground_state"
        and abs(float(row["excitation_keV"])) < 1.0e-9
    ]
    inventory: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in inventory_rows:
        key = (row["incident_family"], row["source_volume"], int(row["source_parent_ZA"]))
        inventory[key] = {
            "sum_RP": float(row["sum_RP"]),
            "production_rate_s-1": float(row["production_rate_s-1"]),
            "day15_activity_Bq": float(row["day15_activity_Bq"]),
        }

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    cells = {
        (row["geometry"], row["family"]): row
        for row in catalog["cells"]
    }
    entries_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_paths: set[str] = set()
    for entry in catalog["dat_entries"]:
        if entry["geometry"] != "S3d_O8" or entry["family"] not in FAMILIES:
            continue
        path = entry["sim_reference"]["path"]
        if path in seen_paths:
            raise RuntimeError(f"duplicate SIM reference in catalog: {path}")
        seen_paths.add(path)
        entries_by_family[entry["family"]].append(entry)

    for family in FAMILIES:
        declared_tt = float(cells[("S3d_O8", family)]["sum_TT_s"])
        if not math.isclose(declared_tt, EXPECTED_SUM_TT[family], rel_tol=0.0, abs_tol=1e-7):
            raise RuntimeError(f"{family} TT denominator drift: {declared_tt}")

    results = {}
    tasks = [
        (family, sorted(entries_by_family[family], key=lambda row: row["sim_reference"]["path"]), selected_keys)
        for family in FAMILIES
    ]
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(scan_family, task): task[0] for task in tasks}
        for future in as_completed(futures):
            family = futures[future]
            results[family] = future.result()
            print(
                f"{family}: {results[family]['events_seen']} primaries, "
                f"{results[family]['target_rp_seen']} retained target RP"
            )

    target_rows = [row for family in FAMILIES for row in results[family]["target_rows"]]
    for row in target_rows:
        key = (row["family"], row["source_volume"], row["source_parent_ZA"])
        inv = inventory.get(key)
        if inv is None:
            row["inventory_key_match"] = 0
            row["production_rate_contribution_s-1"] = math.nan
            row["day15_activity_contribution_Bq"] = math.nan
        else:
            row["inventory_key_match"] = 1
            row["production_rate_contribution_s-1"] = 1.0 / EXPECTED_SUM_TT[row["family"]]
            row["day15_activity_contribution_Bq"] = inv["day15_activity_Bq"] / inv["sum_RP"]
    target_rows.sort(key=lambda row: (row["family"], row["source_parent_ZA"], row["source_volume"], row["simulation_file"], row["local_event_id"]))
    write_csv(HERE / "target_production_origin_events.csv", target_rows, list(target_rows[0]))

    incident_rows = []
    incident_lookup: dict[tuple[Any, ...], int] = {}
    for family in FAMILIES:
        total = results[family]["events_seen"]
        for bins, count in sorted(results[family]["incident_bins"].items()):
            key = (family, *bins)
            incident_lookup[key] = count
            incident_rows.append(
                {
                    "family": family,
                    "energy_lo_keV": bins[0],
                    "energy_hi_keV": bins[1],
                    "theta_lo_deg": bins[2],
                    "theta_hi_deg": bins[3],
                    "azimuth_lo_deg": bins[4],
                    "azimuth_hi_deg": bins[5],
                    "incident_primary_count": count,
                    "fraction_of_family_primaries": count / total,
                    "family_primary_count": total,
                    "family_sum_TT_s": EXPECTED_SUM_TT[family],
                }
            )
    write_csv(HERE / "incident_primary_energy_direction_denominators.csv", incident_rows, list(incident_rows[0]))

    reaction_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    bin_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in target_rows:
        reaction_groups[(
            row["family"], row["component_group"], row["source_volume"],
            row["source_parent_ZA"], row["creator_process"], row["interacting_particle"],
        )].append(row)
        bin_groups[(
            row["family"], row["component_group"], row["source_volume"],
            row["source_parent_ZA"], row["energy_lo_keV"], row["energy_hi_keV"],
            row["theta_lo_deg"], row["theta_hi_deg"],
            row["azimuth_lo_deg"], row["azimuth_hi_deg"],
        )].append(row)

    summary_rows = []
    for key, rows in sorted(reaction_groups.items()):
        energies = [row["primary_energy_keV"] for row in rows]
        thetas = [row["theta_from_IF_plus_x_deg"] for row in rows]
        matched = [row for row in rows if row["inventory_key_match"]]
        summary_rows.append(
            {
                "family": key[0],
                "component_group": key[1],
                "source_volume": key[2],
                "source_parent_ZA": key[3],
                "isotope": isotope_label(key[3]),
                "creator_process": key[4],
                "interacting_particle": key[5],
                "RP_records": len(rows),
                "unique_primary_events": len({(row["simulation_file"], row["local_event_id"]) for row in rows}),
                "production_rate_s-1": len(rows) / EXPECTED_SUM_TT[key[0]],
                "day15_activity_Bq_support": sum(row["day15_activity_contribution_Bq"] for row in matched),
                "selected_W2_source_key": max(row["selected_W2_source_key"] for row in rows),
                "primary_energy_min_keV": min(energies),
                "primary_energy_q25_keV": quantile(energies, 0.25),
                "primary_energy_median_keV": statistics.median(energies),
                "primary_energy_q75_keV": quantile(energies, 0.75),
                "primary_energy_max_keV": max(energies),
                "theta_min_deg": min(thetas),
                "theta_median_deg": statistics.median(thetas),
                "theta_max_deg": max(thetas),
            }
        )
    summary_rows.sort(key=lambda row: -row["day15_activity_Bq_support"])
    write_csv(HERE / "target_production_reaction_summary.csv", summary_rows, list(summary_rows[0]))

    bin_rows = []
    for key, rows in sorted(bin_groups.items()):
        denominator_key = (key[0], key[4], key[5], key[6], key[7], key[8], key[9])
        denominator = incident_lookup[denominator_key]
        matched = [row for row in rows if row["inventory_key_match"]]
        bin_rows.append(
            {
                "family": key[0],
                "component_group": key[1],
                "source_volume": key[2],
                "source_parent_ZA": key[3],
                "isotope": isotope_label(key[3]),
                "energy_lo_keV": key[4],
                "energy_hi_keV": key[5],
                "theta_lo_deg": key[6],
                "theta_hi_deg": key[7],
                "azimuth_lo_deg": key[8],
                "azimuth_hi_deg": key[9],
                "target_RP_records": len(rows),
                "incident_primary_count_denominator": denominator,
                "target_products_per_incident_primary": len(rows) / denominator,
                "production_rate_contribution_s-1": len(rows) / EXPECTED_SUM_TT[key[0]],
                "day15_activity_Bq_support": sum(row["day15_activity_contribution_Bq"] for row in matched),
            }
        )
    write_csv(HERE / "target_production_energy_direction_rates.csv", bin_rows, list(bin_rows[0]))

    observed_counts: dict[tuple[str, str, int], int] = defaultdict(int)
    for row in target_rows:
        observed_counts[(row["family"], row["source_volume"], row["source_parent_ZA"])] += 1
    expected_counts = {
        key: int(value["sum_RP"])
        for key, value in inventory.items()
        if target_record(key[0], key[1], key[2], selected_keys)
    }
    mismatches = {
        str(key): {"expected": expected_counts.get(key, 0), "observed": observed_counts.get(key, 0)}
        for key in sorted(set(expected_counts) | set(observed_counts))
        if expected_counts.get(key, 0) != observed_counts.get(key, 0)
    }
    audit = {
        "status": "PASS__TARGET_BUILDUP_PRIMARY_ORIGIN_CLOSED" if not mismatches else "PARTIAL__TARGET_VOLUME_MAPPING_MISMATCH",
        "scope": "existing corrected S3d-O8 BUILDUP n/p/alpha only; no transport launched",
        "family_primary_counts": {family: results[family]["events_seen"] for family in FAMILIES},
        "family_sum_TT_s": EXPECTED_SUM_TT,
        "target_RP_records": len(target_rows),
        "target_inventory_key_mismatches": mismatches,
        "reaction_semantics": (
            "creator_process is the Geant4 cproc attached to CC IP RP; interacting_particle is par. "
            "This identifies the simulated production mechanism but is not an evaluated nuclear cross section."
        ),
        "denominator_semantics": (
            "Each energy/theta/azimuth bin denominator is all IA INIT primaries in the same S3d_O8 BUILDUP family. "
            "No family pooling is used."
        ),
        "files": [
            "target_production_origin_events.csv",
            "incident_primary_energy_direction_denominators.csv",
            "target_production_reaction_summary.csv",
            "target_production_energy_direction_rates.csv",
        ],
    }
    (HERE / "origin_scan_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
