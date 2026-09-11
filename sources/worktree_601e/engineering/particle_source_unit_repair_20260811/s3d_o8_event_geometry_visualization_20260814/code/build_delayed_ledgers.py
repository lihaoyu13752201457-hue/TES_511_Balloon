#!/usr/bin/env python3
"""Build auditable S3d-O8 delayed event, point, and production-origin ledgers.

This script is deliberately a read-only join over frozen project authorities.  It
does not launch transport, copy SIM files, or infer a production reaction where
the retained production-origin scan has no exact coordinate match.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SOURCE_WORKTREE = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
MAIN_REPOSITORY = Path("/home/ubuntu/TES_511_Balloon")
LOOP_WORKTREE = Path("/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon")

REANALYSIS = (
    SOURCE_WORKTREE
    / "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813"
)
LINEAGE = REANALYSIS / "outputs/04_common_response/selected_background_w2_lineage.csv"
INVENTORY = REANALYSIS / "outputs/02_activation/day15_inventory.csv"
DELAYED_MANIFEST = REANALYSIS / "outputs/03_delayed/delayed_input_manifest.csv"
DELAYED_SOURCE_MIX = REANALYSIS / "outputs/03_delayed/delayed_source_mix.csv"

COMPACT_CATALOG_DIR = (
    MAIN_REPOSITORY
    / "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/outputs/03_delayed/catalog/S3d_O8"
)
SAMPLED_SOURCE_ROOT = (
    MAIN_REPOSITORY
    / "runs/particle_source_unit_repair_20260811/"
    "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/"
    "state_aware_exactpos_v1/sources/S3d_O8"
)

GEOMETRY_DIR = (
    SOURCE_WORKTREE
    / "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry"
)
GEOMETRY = GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
INTRO_GEOMETRY = GEOMETRY_DIR / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"

PARTIAL_ORIGINS = (
    LOOP_WORKTREE
    / "engineering/s3d_o8_loop_engineering_20260814/agents/delayed/"
    "target_production_origin_events.csv"
)
BUILDUP_CATALOG = (
    MAIN_REPOSITORY
    / "runs/particle_source_unit_repair_20260811/"
    "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/catalog_v1/catalog.json"
)

GEOMETRY_NAME = "S3d_O8"
STREAM = "delayed"
W2_WINDOW_ID = "w2_510p58_511p42"
ORIGIN_COORD_TOLERANCE_CM = 5.1e-6
SOURCE_COORD_TOLERANCE_CM = 5.1e-6

EXPECTED_EVENT_ROWS = 420
EXPECTED_SOURCE_POINTS = 66
EXPECTED_SOURCE_KEYS = 49
EXPECTED_ISOTOPES = 15
EXPECTED_TOTAL_W2_CPS = 0.05447975222726722
EXPECTED_CATALOG_EVENTS = 9075
EXPECTED_EXACT_ORIGIN_EVENT_LINKS = 25
EXPECTED_EXACT_ORIGIN_POINTS = 22

ELEMENTS = (
    "n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
    "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn "
    "Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re "
    "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm "
    "Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()


EVENT_COLUMNS = [
    "geometry", "stream", "w2_window_id", "incident_family",
    "delayed_local_event_id", "source_file", "batch_id", "job_name", "transport_seed",
    "measured_total_keV", "measured_multiplicity", "shield_keV", "plastic_keV",
    "event_weight_cps", "w2_rate_cps", "source_point_id", "source_key_id",
    "source_parent_ZA", "source_Z", "source_A", "source_isotope",
    "source_excitation_keV", "source_state_designator", "source_volume", "exact_material",
    "source_world_x_cm", "source_world_y_cm", "source_world_z_cm",
    "source_IF_x_cm", "source_IF_y_cm", "source_IF_z_cm",
    "sim_initial_ZA", "parent_match_distance_cm", "sampled_position_match_distance_cm",
    "has_deca", "inventory_cell_material_category", "inventory_cell_sum_RP",
    "inventory_cell_sum_TT_s", "inventory_cell_production_rate_s-1",
    "inventory_cell_half_life_s", "inventory_cell_half_life_source",
    "inventory_cell_day15_activity_Bq", "inventory_cell_RPIP_support_count",
    "inventory_cell_source_disposition", "inventory_cell_holdout_reason",
    "source_mix_full_50000_blocks", "source_mix_selected_10000_blocks",
    "source_mix_realized_250000_triggers", "origin_match_status", "origin_candidate_count",
]

POINT_COLUMNS = [
    "source_point_id", "source_key_id", "incident_family", "source_parent_ZA",
    "source_Z", "source_A", "source_isotope", "source_excitation_keV",
    "source_state_designator", "source_volume", "exact_material",
    "source_world_x_cm", "source_world_y_cm", "source_world_z_cm",
    "source_IF_x_cm", "source_IF_y_cm", "source_IF_z_cm",
    "selected_event_rows", "selected_w2_rate_cps", "selected_sum_weight_sq",
    "selected_event_neff", "parent_match_distance_max_cm",
    "sampled_position_match_distance_max_cm", "inventory_cell_material_category",
    "inventory_cell_sum_RP", "inventory_cell_sum_TT_s",
    "inventory_cell_production_rate_s-1", "inventory_cell_half_life_s",
    "inventory_cell_half_life_source", "inventory_cell_day15_activity_Bq",
    "inventory_cell_RPIP_support_count", "inventory_cell_source_disposition",
    "inventory_cell_holdout_reason", "source_mix_full_50000_blocks",
    "source_mix_selected_10000_blocks", "source_mix_realized_250000_triggers",
    "origin_match_status", "origin_candidate_count", "exact_origin_linked_event_rows",
]

ORIGIN_COLUMNS = [
    "geometry", "incident_family", "delayed_source_file", "delayed_local_event_id",
    "source_point_id", "source_key_id", "source_parent_ZA", "source_isotope",
    "source_volume", "exact_material", "source_world_x_cm", "source_world_y_cm",
    "source_world_z_cm", "origin_match_status", "origin_match_distance_cm",
    "activation_job_id", "activation_batch_id", "activation_simulation_file",
    "activation_local_event_id", "production_world_x_cm", "production_world_y_cm",
    "production_world_z_cm", "track_id", "parent_track_id", "secondary_process",
    "transport_primary", "interacting_particle", "creator_process",
    "primary_particle_id", "primary_world_x_cm", "primary_world_y_cm", "primary_world_z_cm",
    "primary_dir_world_x", "primary_dir_world_y", "primary_dir_world_z",
    "primary_energy_keV", "theta_from_IF_plus_x_deg", "azimuth_about_IF_x_deg",
    "production_rate_contribution_s-1", "day15_activity_contribution_Bq",
    "inventory_key_match",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def isotope_label(za: int) -> str:
    z, a = divmod(int(za), 1000)
    element = ELEMENTS[z] if 0 <= z < len(ELEMENTS) else f"Z{z}"
    return f"{element}-{a}"


def world_to_instrument(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def linf_distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right))


def parse_exact_materials(path: Path) -> dict[str, str]:
    materials: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if len(fields) < 2 or not fields[0].endswith(".Material"):
            continue
        volume = fields[0][:-len(".Material")]
        material = fields[1]
        old = materials.setdefault(volume, material)
        if old != material:
            raise RuntimeError(f"conflicting exact material for {volume}: {old} vs {material}")
    return materials


def validate_instrument_frame(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split(maxsplit=1)
        if len(fields) == 2 and fields[0] in {
            "InstrumentFrame.Position", "InstrumentFrame.Rotation", "InstrumentFrame.Mother"
        }:
            values[fields[0]] = fields[1]
    expected = {
        "InstrumentFrame.Position": "0 0 0",
        "InstrumentFrame.Rotation": "0 45 0",
        "InstrumentFrame.Mother": "WorldVolume",
    }
    if values != expected:
        raise RuntimeError(f"InstrumentFrame authority changed: {values!r}")
    return values


def catalog_records() -> tuple[dict[tuple[str, int, str], dict[str, Any]], int, dict[str, int]]:
    lookup: dict[tuple[str, int, str], dict[str, Any]] = {}
    total = 0
    family_counts: dict[str, int] = {}
    expected_keys: tuple[str, ...] | None = None
    scalar_fields = [
        "rate_hz", "source_parent_ZA", "source_volume", "source_excitation_keV",
        "sim_initial_ZA", "parent_match_distance_cm", "production_x_cm",
        "production_y_cm", "production_z_cm", "has_deca",
    ]
    for path in sorted(COMPACT_CATALOG_DIR.glob("*.pkl")):
        with path.open("rb") as handle:
            catalog = pickle.load(handle)
        keys = tuple(catalog.keys())
        if expected_keys is None:
            expected_keys = keys
        elif keys != expected_keys:
            raise RuntimeError(f"compact catalog schema differs: {path}")
        count = len(catalog["local_id"])
        family = str(catalog["cell_metadata"]["family"])
        family_counts[family] = count
        total += count
        for index in range(count):
            key = (str(catalog["tag"][index]), int(catalog["local_id"][index]), str(catalog["source_file"][index]))
            if key in lookup:
                raise RuntimeError(f"duplicate compact event key: {key}")
            record = {name: catalog[name][index] for name in scalar_fields}
            record.update(
                {
                    "input_id": catalog["input_id"][index],
                    "batch_id": catalog["batch_id"][index],
                    "job_name": catalog["job_name"][index],
                    "seed": catalog["seed"][index],
                }
            )
            lookup[key] = record
    return lookup, total, family_counts


def sampled_position_index(families: set[str]) -> dict[str, dict[tuple[str, str, str], list[dict[str, Any]]]]:
    result: dict[str, dict[tuple[str, str, str], list[dict[str, Any]]]] = {}
    for family in sorted(families):
        path = SAMPLED_SOURCE_ROOT / family / "sampled_exact_positions_m50000.csv"
        rounded: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in read_csv(path):
            if int(row["sample_index"]) % 5:
                continue
            xyz = (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            rounded[tuple(f"{axis:.5f}" for axis in xyz)].append(
                {
                    "xyz": xyz,
                    "volume": row["volume"],
                    "ZA": int(row["ZA"]),
                    "excitation_keV": float(row["excitation_keV"]),
                }
            )
        result[family] = rounded
    return result


def find_sampled_position(
    family_index: dict[tuple[str, str, str], list[dict[str, Any]]],
    xyz: tuple[float, float, float],
) -> tuple[dict[str, Any], float]:
    candidates = family_index.get(tuple(f"{axis:.5f}" for axis in xyz), [])
    if not candidates:
        raise RuntimeError(f"no sampled-position candidate for {xyz}")
    ranked = sorted((linf_distance(xyz, row["xyz"]), row) for row in candidates)
    nearest, chosen = ranked[0]
    same = [row for distance, row in ranked if abs(distance - nearest) <= 1e-15]
    metadata = {(row["volume"], row["ZA"], row["excitation_keV"]) for row in same}
    if nearest > SOURCE_COORD_TOLERANCE_CM or len(metadata) != 1:
        raise RuntimeError(f"sampled-position match is not unique: xyz={xyz} nearest={nearest} metadata={metadata}")
    return chosen, nearest


def inventory_index() -> dict[tuple[str, str, int, float], dict[str, str]]:
    result: dict[tuple[str, str, int, float], dict[str, str]] = {}
    for row in read_csv(INVENTORY):
        if row["geometry"] != GEOMETRY_NAME:
            continue
        key = (
            row["incident_family"], row["source_volume"],
            int(row["source_parent_ZA"]), float(row["excitation_keV"]),
        )
        if key in result:
            raise RuntimeError(f"duplicate inventory key: {key}")
        result[key] = row
    return result


def source_mix_index() -> dict[tuple[str, str, int], dict[str, str]]:
    result: dict[tuple[str, str, int], dict[str, str]] = {}
    for row in read_csv(DELAYED_SOURCE_MIX):
        if row["geometry"] != GEOMETRY_NAME:
            continue
        key = (row["family"], row["source_volume"], int(row["source_parent_ZA"]))
        if key in result:
            raise RuntimeError(f"duplicate source-mix key: {key}")
        result[key] = row
    return result


def origin_index() -> tuple[dict[tuple[str, str, int], list[dict[str, str]]], set[str], int]:
    result: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    families: set[str] = set()
    rows = read_csv(PARTIAL_ORIGINS)
    for row in rows:
        key = (row["family"], row["source_volume"], int(row["source_parent_ZA"]))
        result[key].append(row)
        families.add(row["family"])
    return result, families, len(rows)


def source_key_id(family: str, volume: str, za: int, excitation: float) -> str:
    state = "g" if excitation == 0.0 else f"Ex={excitation:g}keV"
    return f"{family}|{volume}|{za}|{state}"


def inventory_fields(row: dict[str, str]) -> dict[str, Any]:
    return {
        "inventory_cell_material_category": row["material_category"],
        "inventory_cell_sum_RP": float(row["sum_RP"]),
        "inventory_cell_sum_TT_s": float(row["sum_TT_s"]),
        "inventory_cell_production_rate_s-1": float(row["production_rate_s-1"]),
        "inventory_cell_half_life_s": "" if row["half_life_s"] == "" else float(row["half_life_s"]),
        "inventory_cell_half_life_source": row["half_life_source"],
        "inventory_cell_day15_activity_Bq": "" if row["day15_activity_Bq"] == "" else float(row["day15_activity_Bq"]),
        "inventory_cell_RPIP_support_count": int(row["RPIP_support_count"]),
        "inventory_cell_source_disposition": row["source_disposition"],
        "inventory_cell_holdout_reason": row["holdout_reason"],
    }


def mix_fields(row: dict[str, str] | None) -> dict[str, Any]:
    if row is None:
        return {
            "source_mix_full_50000_blocks": 0,
            "source_mix_selected_10000_blocks": 0,
            "source_mix_realized_250000_triggers": 0,
        }
    return {
        "source_mix_full_50000_blocks": int(row["full_50000_blocks"]),
        "source_mix_selected_10000_blocks": int(row["selected_10000_blocks"]),
        "source_mix_realized_250000_triggers": int(row["realized_250000_triggers"]),
    }


def build(output_root: Path) -> dict[str, Any]:
    for path in [
        LINEAGE, INVENTORY, DELAYED_MANIFEST, DELAYED_SOURCE_MIX, GEOMETRY,
        INTRO_GEOMETRY, PARTIAL_ORIGINS, BUILDUP_CATALOG,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    if not COMPACT_CATALOG_DIR.is_dir() or not SAMPLED_SOURCE_ROOT.is_dir():
        raise FileNotFoundError("compact catalog or sampled-source authority is missing")

    frame_authority = validate_instrument_frame(INTRO_GEOMETRY)
    exact_material = parse_exact_materials(GEOMETRY)
    catalogs, catalog_event_total, catalog_family_counts = catalog_records()
    inventory = inventory_index()
    source_mix = source_mix_index()
    origins, origin_scanned_families, origin_row_total = origin_index()

    lineage = [
        row for row in read_csv(LINEAGE)
        if row["geometry"] == GEOMETRY_NAME and row["stream"] == STREAM
    ]
    event_keys = [
        (row["family"], int(row["local_event_id"]), row["source_file"])
        for row in lineage
    ]
    if len(event_keys) != len(set(event_keys)):
        raise RuntimeError("selected lineage event key is not unique")
    sampled = sampled_position_index({row["family"] for row in lineage})

    provisional: list[dict[str, Any]] = []
    point_members: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    catalog_misses = inventory_misses = material_misses = 0
    lineage_catalog_mismatches = 0
    sim_parent_matches = deca_true = excitation_zero = 0
    sampled_matches = 0
    sampled_distances: list[float] = []
    parent_distances: list[float] = []

    for lineage_row in lineage:
        family = lineage_row["family"]
        event_key = (family, int(lineage_row["local_event_id"]), lineage_row["source_file"])
        catalog = catalogs.get(event_key)
        if catalog is None:
            catalog_misses += 1
            continue
        comparisons = [
            float(lineage_row["event_weight_cps"]) == float(catalog["rate_hz"]),
            int(lineage_row["source_parent_ZA"]) == int(catalog["source_parent_ZA"]),
            lineage_row["source_volume"] == catalog["source_volume"],
            float(lineage_row["source_excitation_keV"]) == float(catalog["source_excitation_keV"]),
            int(lineage_row["sim_initial_ZA"]) == int(catalog["sim_initial_ZA"]),
            abs(float(lineage_row["parent_match_distance_cm"]) - float(catalog["parent_match_distance_cm"])) <= 1e-15,
        ]
        lineage_catalog_mismatches += int(not all(comparisons))

        za = int(catalog["source_parent_ZA"])
        z, a = divmod(za, 1000)
        excitation = float(catalog["source_excitation_keV"])
        volume = str(catalog["source_volume"])
        world = (
            float(catalog["production_x_cm"]), float(catalog["production_y_cm"]),
            float(catalog["production_z_cm"]),
        )
        instrument = world_to_instrument(*world)
        sampled_row, sampled_distance = find_sampled_position(sampled[family], world)
        sampled_distances.append(sampled_distance)
        sampled_matches += int(
            sampled_row["volume"] == volume
            and sampled_row["ZA"] == za
            and sampled_row["excitation_keV"] == excitation
        )

        inventory_key = (family, volume, za, excitation)
        inventory_row = inventory.get(inventory_key)
        if inventory_row is None:
            inventory_misses += 1
            continue
        material = exact_material.get(volume)
        if material is None:
            material_misses += 1
            continue
        mix_row = source_mix.get((family, volume, za))

        origin_candidates: list[tuple[float, dict[str, str]]] = []
        for origin in origins.get((family, volume, za), []):
            origin_xyz = (
                float(origin["production_x_cm"]), float(origin["production_y_cm"]),
                float(origin["production_z_cm"]),
            )
            distance = linf_distance(world, origin_xyz)
            if distance <= ORIGIN_COORD_TOLERANCE_CM:
                origin_candidates.append((distance, origin))
        origin_candidates.sort(key=lambda item: (item[0], item[1]["simulation_file"], int(item[1]["local_event_id"])))
        if len(origin_candidates) == 1:
            origin_status = "EXACT_COORD_UNIQUE"
        elif len(origin_candidates) > 1:
            origin_status = "AMBIGUOUS_MULTIPLE_RP"
        elif family not in origin_scanned_families:
            origin_status = "NOT_SCANNED_FAMILY"
        else:
            origin_status = "COMPONENT_FILTERED_OR_NOT_RETAINED"

        state = "g" if excitation == 0.0 else f"Ex={excitation:g}keV"
        skey = source_key_id(family, volume, za, excitation)
        parent_distance = float(catalog["parent_match_distance_cm"])
        parent_distances.append(parent_distance)
        sim_parent_matches += int(int(catalog["sim_initial_ZA"]) == za)
        deca_true += int(bool(catalog["has_deca"]))
        excitation_zero += int(excitation == 0.0)

        event = {
            "geometry": GEOMETRY_NAME,
            "stream": STREAM,
            "w2_window_id": W2_WINDOW_ID,
            "incident_family": family,
            "delayed_local_event_id": int(lineage_row["local_event_id"]),
            "source_file": lineage_row["source_file"],
            "batch_id": lineage_row["batch_id"],
            "job_name": lineage_row["job_name"],
            "transport_seed": int(lineage_row["transport_seed"]),
            "measured_total_keV": float(lineage_row["measured_total_keV"]),
            "measured_multiplicity": int(lineage_row["measured_multiplicity"]),
            "shield_keV": float(lineage_row["shield_keV"]),
            "plastic_keV": float(lineage_row["plastic_keV"]),
            "event_weight_cps": float(lineage_row["event_weight_cps"]),
            "w2_rate_cps": float(lineage_row["event_weight_cps"]),
            "source_point_id": "",
            "source_key_id": skey,
            "source_parent_ZA": za,
            "source_Z": z,
            "source_A": a,
            "source_isotope": isotope_label(za),
            "source_excitation_keV": excitation,
            "source_state_designator": state,
            "source_volume": volume,
            "exact_material": material,
            "source_world_x_cm": world[0],
            "source_world_y_cm": world[1],
            "source_world_z_cm": world[2],
            "source_IF_x_cm": instrument[0],
            "source_IF_y_cm": instrument[1],
            "source_IF_z_cm": instrument[2],
            "sim_initial_ZA": int(catalog["sim_initial_ZA"]),
            "parent_match_distance_cm": parent_distance,
            "sampled_position_match_distance_cm": sampled_distance,
            "has_deca": int(bool(catalog["has_deca"])),
            **inventory_fields(inventory_row),
            **mix_fields(mix_row),
            "origin_match_status": origin_status,
            "origin_candidate_count": len(origin_candidates),
            "_point_key": (family, volume, za, excitation, *world),
            "_origin_candidates": origin_candidates,
        }
        provisional.append(event)
        point_members[event["_point_key"]].append(event)

    sorted_point_keys = sorted(point_members)
    point_ids = {key: f"P{index:04d}" for index, key in enumerate(sorted_point_keys, start=1)}
    for event in provisional:
        event["source_point_id"] = point_ids[event["_point_key"]]

    event_rows = sorted(
        provisional,
        key=lambda row: (row["incident_family"], row["job_name"], row["delayed_local_event_id"]),
    )
    origin_links: list[dict[str, Any]] = []
    for event in event_rows:
        for distance, origin in event["_origin_candidates"]:
            origin_links.append(
                {
                    "geometry": GEOMETRY_NAME,
                    "incident_family": event["incident_family"],
                    "delayed_source_file": event["source_file"],
                    "delayed_local_event_id": event["delayed_local_event_id"],
                    "source_point_id": event["source_point_id"],
                    "source_key_id": event["source_key_id"],
                    "source_parent_ZA": event["source_parent_ZA"],
                    "source_isotope": event["source_isotope"],
                    "source_volume": event["source_volume"],
                    "exact_material": event["exact_material"],
                    "source_world_x_cm": event["source_world_x_cm"],
                    "source_world_y_cm": event["source_world_y_cm"],
                    "source_world_z_cm": event["source_world_z_cm"],
                    "origin_match_status": event["origin_match_status"],
                    "origin_match_distance_cm": distance,
                    "activation_job_id": origin["job_id"],
                    "activation_batch_id": origin["batch_id"],
                    "activation_simulation_file": origin["simulation_file"],
                    "activation_local_event_id": int(origin["local_event_id"]),
                    "production_world_x_cm": float(origin["production_x_cm"]),
                    "production_world_y_cm": float(origin["production_y_cm"]),
                    "production_world_z_cm": float(origin["production_z_cm"]),
                    "track_id": int(origin["track_id"]),
                    "parent_track_id": int(origin["parent_track_id"]),
                    "secondary_process": origin["secondary_process"],
                    "transport_primary": origin["transport_primary"],
                    "interacting_particle": origin["interacting_particle"],
                    "creator_process": origin["creator_process"],
                    "primary_particle_id": int(origin["primary_particle_id"]),
                    "primary_world_x_cm": float(origin["primary_x_cm"]),
                    "primary_world_y_cm": float(origin["primary_y_cm"]),
                    "primary_world_z_cm": float(origin["primary_z_cm"]),
                    "primary_dir_world_x": float(origin["primary_dir_x"]),
                    "primary_dir_world_y": float(origin["primary_dir_y"]),
                    "primary_dir_world_z": float(origin["primary_dir_z"]),
                    "primary_energy_keV": float(origin["primary_energy_keV"]),
                    "theta_from_IF_plus_x_deg": float(origin["theta_from_IF_plus_x_deg"]),
                    "azimuth_about_IF_x_deg": float(origin["azimuth_about_IF_x_deg"]),
                    "production_rate_contribution_s-1": float(origin["production_rate_contribution_s-1"]),
                    "day15_activity_contribution_Bq": float(origin["day15_activity_contribution_Bq"]),
                    "inventory_key_match": int(origin["inventory_key_match"]),
                }
            )

    point_rows: list[dict[str, Any]] = []
    exact_origin_points = 0
    for point_key in sorted_point_keys:
        members = point_members[point_key]
        first = members[0]
        statuses = {row["origin_match_status"] for row in members}
        candidate_counts = {row["origin_candidate_count"] for row in members}
        if len(statuses) != 1 or len(candidate_counts) != 1:
            raise RuntimeError(f"origin status differs within source point {point_key}")
        status = next(iter(statuses))
        exact_origin_points += int(status == "EXACT_COORD_UNIQUE")
        weights = [float(row["w2_rate_cps"]) for row in members]
        sum_weight = math.fsum(weights)
        sum_weight_sq = math.fsum(weight * weight for weight in weights)
        point_rows.append(
            {
                "source_point_id": point_ids[point_key],
                "source_key_id": first["source_key_id"],
                "incident_family": first["incident_family"],
                "source_parent_ZA": first["source_parent_ZA"],
                "source_Z": first["source_Z"],
                "source_A": first["source_A"],
                "source_isotope": first["source_isotope"],
                "source_excitation_keV": first["source_excitation_keV"],
                "source_state_designator": first["source_state_designator"],
                "source_volume": first["source_volume"],
                "exact_material": first["exact_material"],
                "source_world_x_cm": first["source_world_x_cm"],
                "source_world_y_cm": first["source_world_y_cm"],
                "source_world_z_cm": first["source_world_z_cm"],
                "source_IF_x_cm": first["source_IF_x_cm"],
                "source_IF_y_cm": first["source_IF_y_cm"],
                "source_IF_z_cm": first["source_IF_z_cm"],
                "selected_event_rows": len(members),
                "selected_w2_rate_cps": sum_weight,
                "selected_sum_weight_sq": sum_weight_sq,
                "selected_event_neff": sum_weight * sum_weight / sum_weight_sq,
                "parent_match_distance_max_cm": max(float(row["parent_match_distance_cm"]) for row in members),
                "sampled_position_match_distance_max_cm": max(float(row["sampled_position_match_distance_cm"]) for row in members),
                **{name: first[name] for name in POINT_COLUMNS if name.startswith("inventory_cell_")},
                **{name: first[name] for name in POINT_COLUMNS if name.startswith("source_mix_")},
                "origin_match_status": status,
                "origin_candidate_count": next(iter(candidate_counts)),
                "exact_origin_linked_event_rows": sum(row["origin_match_status"] == "EXACT_COORD_UNIQUE" for row in members),
            }
        )

    for event in event_rows:
        event.pop("_point_key")
        event.pop("_origin_candidates")

    family_counts = Counter(row["incident_family"] for row in event_rows)
    material_counts = Counter(row["exact_material"] for row in event_rows)
    status_counts = Counter(row["origin_match_status"] for row in event_rows)
    point_status_counts = Counter(row["origin_match_status"] for row in point_rows)
    unique_source_keys = {row["source_key_id"] for row in event_rows}
    unique_isotopes = {row["source_parent_ZA"] for row in event_rows}
    total_w2 = math.fsum(float(row["w2_rate_cps"]) for row in event_rows)

    checks = {
        "event_rows_420": len(event_rows) == EXPECTED_EVENT_ROWS,
        "source_points_66": len(point_rows) == EXPECTED_SOURCE_POINTS,
        "source_keys_49": len(unique_source_keys) == EXPECTED_SOURCE_KEYS,
        "isotopes_15": len(unique_isotopes) == EXPECTED_ISOTOPES,
        "catalog_event_total_9075": catalog_event_total == EXPECTED_CATALOG_EVENTS,
        "catalog_join_complete": catalog_misses == 0,
        "inventory_join_complete": inventory_misses == 0,
        "exact_material_join_complete": material_misses == 0,
        "lineage_catalog_fields_identical": lineage_catalog_mismatches == 0,
        "sampled_position_join_complete": sampled_matches == EXPECTED_EVENT_ROWS,
        "sim_initial_ZA_matches_parent": sim_parent_matches == EXPECTED_EVENT_ROWS,
        "all_selected_events_have_DECA": deca_true == EXPECTED_EVENT_ROWS,
        "all_selected_sources_ground_state": excitation_zero == EXPECTED_EVENT_ROWS,
        "total_w2_rate_matches_authority": math.isclose(total_w2, EXPECTED_TOTAL_W2_CPS, rel_tol=0.0, abs_tol=1e-15),
        "exact_origin_event_links_25": len(origin_links) == EXPECTED_EXACT_ORIGIN_EVENT_LINKS,
        "exact_origin_points_22": exact_origin_points == EXPECTED_EXACT_ORIGIN_POINTS,
        "no_ambiguous_origin_match": status_counts.get("AMBIGUOUS_MULTIPLE_RP", 0) == 0,
        "origin_status_partition": status_counts == Counter({
            "NOT_SCANNED_FAMILY": 392,
            "EXACT_COORD_UNIQUE": 25,
            "COMPONENT_FILTERED_OR_NOT_RETAINED": 3,
        }),
        "material_partition": material_counts == Counter({
            "Copper": 373, "Nb": 25, "MuMetal": 20,
            "SilverSinterProxy": 1, "CuNi": 1,
        }),
        "point_event_count_closure": sum(int(row["selected_event_rows"]) for row in point_rows) == len(event_rows),
        "point_rate_closure": math.isclose(
            math.fsum(float(row["selected_w2_rate_cps"]) for row in point_rows),
            total_w2, rel_tol=0.0, abs_tol=1e-15,
        ),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(f"delayed ledger validation failed: {failed}")

    data_dir = output_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    event_path = data_dir / "delayed_selected_event_ledger.csv"
    point_path = data_dir / "delayed_source_point_ledger.csv"
    origin_path = data_dir / "delayed_partial_production_origin_links.csv"
    validation_path = output_root / "delayed_validation.json"
    write_csv(event_path, EVENT_COLUMNS, event_rows)
    write_csv(point_path, POINT_COLUMNS, point_rows)
    write_csv(origin_path, ORIGIN_COLUMNS, origin_links)

    validation = {
        "status": "PASS",
        "scope": "S3d-O8 selected delayed W2 event/source-position ledger",
        "semantics": {
            "event_weight": "Each selected row contributes event_weight_cps to the W2 rate.",
            "compact_coordinate_fields": "PKL production_x/y/z are delayed SIM IA INIT coordinates and are exported as decay source world coordinates.",
            "inventory_fields": "inventory_cell_* values are cell totals and must not be summed across event or point rows.",
            "origin_policy": "Projectile/channel fields are emitted only for an exact unique family+volume+ZA+world-coordinate match. Missing values are not inferred.",
            "world_to_InstrumentFrame": {
                "x_IF": "(x_world - z_world) / sqrt(2)",
                "y_IF": "y_world",
                "z_IF": "(x_world + z_world) / sqrt(2)",
                "authority": frame_authority,
            },
        },
        "authorities": {
            "selected_lineage": str(LINEAGE),
            "compact_catalog_dir": str(COMPACT_CATALOG_DIR),
            "sampled_source_root": str(SAMPLED_SOURCE_ROOT),
            "delayed_input_manifest": str(DELAYED_MANIFEST),
            "delayed_source_mix": str(DELAYED_SOURCE_MIX),
            "day15_inventory": str(INVENTORY),
            "geometry": str(GEOMETRY),
            "instrument_frame_geometry": str(INTRO_GEOMETRY),
            "partial_production_origins": str(PARTIAL_ORIGINS),
            "existing_buildup_catalog_for_future_origin_completion": str(BUILDUP_CATALOG),
        },
        "outputs": {
            "event_ledger": str(event_path),
            "source_point_ledger": str(point_path),
            "partial_production_origin_links": str(origin_path),
        },
        "counts": {
            "selected_event_rows": len(event_rows),
            "source_points": len(point_rows),
            "source_keys": len(unique_source_keys),
            "isotopes": len(unique_isotopes),
            "total_w2_rate_cps": total_w2,
            "compact_catalog_events": catalog_event_total,
            "partial_origin_authority_rows": origin_row_total,
            "exact_origin_event_links": len(origin_links),
            "exact_origin_points": exact_origin_points,
            "event_family_counts": dict(sorted(family_counts.items())),
            "event_exact_material_counts": dict(sorted(material_counts.items())),
            "event_origin_status_counts": dict(sorted(status_counts.items())),
            "point_origin_status_counts": dict(sorted(point_status_counts.items())),
        },
        "coordinate_audit": {
            "parent_match_distance_min_cm": min(parent_distances),
            "parent_match_distance_max_cm": max(parent_distances),
            "sampled_position_match_distance_min_cm": min(sampled_distances),
            "sampled_position_match_distance_max_cm": max(sampled_distances),
            "origin_match_tolerance_cm": ORIGIN_COORD_TOLERANCE_CM,
            "sampled_position_match_tolerance_cm": SOURCE_COORD_TOLERANCE_CM,
        },
        "compact_catalog_family_event_counts": dict(sorted(catalog_family_counts.items())),
        "validation_checks": checks,
        "columns": {
            "event_ledger": EVENT_COLUMNS,
            "source_point_ledger": POINT_COLUMNS,
            "partial_production_origin_links": ORIGIN_COLUMNS,
        },
    }
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return validation


def main() -> None:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=default_root)
    args = parser.parse_args()
    validation = build(args.output_root.resolve())
    print(json.dumps({"status": validation["status"], "counts": validation["counts"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
