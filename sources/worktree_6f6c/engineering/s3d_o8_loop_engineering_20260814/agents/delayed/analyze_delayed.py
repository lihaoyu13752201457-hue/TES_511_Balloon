#!/usr/bin/env python3
"""Independent S3d-O8 delayed-background denominator audit.

This script is deliberately post-processing only.  It reads the retained
corrected-keV inventory, source-mix table, selected W2 lineage, and compact
delayed catalogs without copying or modifying the source worktree.
"""

from __future__ import annotations

import csv
import json
import math
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
SOURCE_WT = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
SOURCE_MAIN = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = SOURCE_WT / "engineering/particle_source_unit_repair_20260811"
M05 = PACKAGE / "m05_corrected_reanalysis_20260813"
INVENTORY = M05 / "outputs/02_activation/day15_inventory.csv"
SOURCE_MIX = M05 / "outputs/03_delayed/delayed_source_mix.csv"
LINEAGE = M05 / "outputs/04_common_response/selected_background_w2_lineage.csv"
PKL_ROOT = (
    SOURCE_MAIN
    / "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/outputs/03_delayed/catalog/S3d_O8"
)
FROZEN_COORDS = (
    PACKAGE
    / "s3d_o8_low_grammage_core_20260814/data/"
    "frozen_delayed_source_coordinates.csv"
)

GEOMETRY = "S3d_O8"
N_TRIGGERS_PER_FAMILY = 250_000
EXPECTED_SELECTED_ROWS = 420
EXPECTED_SELECTED_RATE_CPS = 0.05447975222726722
AXIS_IF_Z_CM = -5.2
TARGET_PARENT_ZA = {27054, 29061, 29062, 29064, 39085, 41089, 41090, 47106}

# Component-local coordinates follow the geometry conventions already frozen in
# s3d_o8_low_grammage_core_20260814.  These are not interchangeable: the cold
# plates and can bottom use their local z axes, while the nested magnetic
# shields and horizontal support panels use the instrument x axis about z=-5.2.
LOCAL_Z_CENTERS_CM = {
    "ColdPlate_MXC_50mK_SD_anchor": 0.0,
    "ColdPlate_CP_100mK_intercept": 5.0,
    "ColdPlate_Still_0p7K": 11.0,
    "Cu_50mK_StillLike_Can_bottom_cap_2mm": -9.8,
}

ELEMENTS = (
    "n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
    "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn "
    "Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re "
    "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm "
    "Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def f(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def i(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(value)


def isotope_label(za: int) -> str:
    z, a = divmod(int(za), 1000)
    symbol = ELEMENTS[z] if 0 <= z < len(ELEMENTS) else f"Z{z}"
    return f"{symbol}-{a}"


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


def material_label(volume: str, inventory_category: str = "") -> str:
    if volume.startswith("Nb_"):
        return "Nb"
    if volume.startswith("MuMetal_"):
        return "Mu-metal"
    if "Ag" in volume or "Sinter" in volume:
        return "Ag-proxy"
    if (
        volume.startswith("Cu_")
        or volume.startswith("ColdPlate_")
        or volume.startswith("DR_MixingChamber_Cu")
        or volume.startswith("DR_Continuous_HEX_Cu")
    ):
        return "Copper"
    if volume.startswith("BGO_"):
        return "BGO"
    if inventory_category:
        return inventory_category
    return "Other"


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def component_coordinates(
    volume: str, ifx: float, ify: float, ifz: float
) -> tuple[float, float, str]:
    """Return (component radius, component axial, explicit axis convention)."""
    if volume in LOCAL_Z_CENTERS_CM:
        return (
            math.hypot(ifx, ify),
            ifz - LOCAL_Z_CENTERS_CM[volume],
            "local_z",
        )
    if (
        volume == "Nb_MagShield_Inner_Cylinder_2mm"
        or volume == "MuMetal_MagShield_Outer_Cylinder_2mm"
        or volume.startswith("Cu_SubstrateSupport_OpenRing_L")
        or volume == "Cu_SubstrateSupport_SolidDisk_L0_deepest"
    ):
        axial = ifx - 3.42 if volume == "Cu_SubstrateSupport_SolidDisk_L0_deepest" else ifx
        return math.hypot(ify, ifz - AXIS_IF_Z_CM), axial, "local_x_about_z=-5.2"
    # No geometry-local origin is asserted for remaining volumes.  IF-z and
    # radius about the IF z axis are still useful plotting coordinates, but the
    # label makes their weaker status explicit.
    return math.hypot(ifx, ify), ifz, "default_instrument_z__local_origin_UNKNOWN"


def neff(weights: Iterable[float]) -> float:
    values = list(weights)
    total = math.fsum(values)
    squares = math.fsum(value * value for value in values)
    return total * total / squares if squares > 0.0 else 0.0


def aggregate_inventory() -> tuple[dict[tuple[str, str, int], dict[str, Any]], dict[str, float], float]:
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    family_activity: dict[str, float] = defaultdict(float)
    holdout = 0.0
    for row in read_csv(INVENTORY):
        if row["geometry"] != GEOMETRY:
            continue
        activity = f(row["day15_activity_Bq"])
        if row["source_disposition"] != "transported_ground_state":
            holdout += activity
            continue
        if abs(f(row["excitation_keV"])) > 1.0e-9:
            raise RuntimeError("transported source unexpectedly contains a non-ground state")
        key = (row["incident_family"], row["source_volume"], i(row["source_parent_ZA"]))
        item = by_key.setdefault(
            key,
            {
                "family": key[0],
                "source_volume": key[1],
                "source_parent_ZA": key[2],
                "material": material_label(key[1], row["material_category"]),
                "component_group": component_group(key[1]),
                "production_rate_s-1": 0.0,
                "day15_activity_Bq": 0.0,
                "sum_RP": 0.0,
                "RPIP_support_count": 0,
                "sum_TT_s_values": set(),
            },
        )
        item["production_rate_s-1"] += f(row["production_rate_s-1"])
        item["day15_activity_Bq"] += activity
        item["sum_RP"] += f(row["sum_RP"])
        item["RPIP_support_count"] += i(row["RPIP_support_count"])
        item["sum_TT_s_values"].add(f(row["sum_TT_s"]))
        family_activity[key[0]] += activity
    for item in by_key.values():
        values = item.pop("sum_TT_s_values")
        if len(values) != 1:
            raise RuntimeError(f"TT denominator drift within inventory key: {item}")
        item["sum_TT_s"] = next(iter(values))
        if abs(item["sum_RP"] - item["RPIP_support_count"]) > 1.0e-9:
            raise RuntimeError(f"RP/RPIP closure failed: {item}")
    return by_key, dict(family_activity), holdout


def aggregate_source_mix() -> dict[tuple[str, str, int], dict[str, Any]]:
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in read_csv(SOURCE_MIX):
        if row["geometry"] != GEOMETRY:
            continue
        key = (row["family"], row["source_volume"], i(row["source_parent_ZA"]))
        if key in by_key:
            raise RuntimeError(f"duplicate source-mix key: {key}")
        by_key[key] = {
            "full_50000_blocks": i(row["full_50000_blocks"]),
            "full_50000_fraction": f(row["full_50000_fraction"]),
            "selected_10000_blocks": i(row["selected_10000_blocks"]),
            "selected_10000_fraction": f(row["selected_10000_fraction"]),
            "realized_250000_triggers": i(row["realized_250000_triggers"]),
            "realized_250000_fraction": f(row["realized_250000_fraction"]),
        }
    return by_key


def load_selected_events() -> tuple[list[dict[str, Any]], int, int]:
    rows = [
        row for row in read_csv(LINEAGE)
        if row["geometry"] == "S3d_O8" and row["stream"] == "delayed"
    ]
    frozen = {
        (row["family"], i(row["local_event_id"])): row
        for row in read_csv(FROZEN_COORDS)
    }
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)

    events: list[dict[str, Any]] = []
    coordinate_matches = 0
    frozen_component_coordinate_matches = 0
    for family, family_rows in sorted(by_family.items()):
        with (PKL_ROOT / f"{family}.pkl").open("rb") as handle:
            payload = pickle.load(handle)
        local_ids = payload["local_id"]
        if len(local_ids) != len(set(local_ids)):
            raise RuntimeError(f"duplicate compact local IDs in {family}")
        index = {int(event_id): idx for idx, event_id in enumerate(local_ids)}
        for row in family_rows:
            event_id = i(row["local_event_id"])
            idx = index.get(event_id)
            if idx is None:
                raise RuntimeError(f"selected event is absent from compact catalog: {family}/{event_id}")
            if i(row["source_parent_ZA"]) != int(payload["source_parent_ZA"][idx]):
                raise RuntimeError(f"parent mismatch for {family}/{event_id}")
            if row["source_volume"] != payload["source_volume"][idx]:
                raise RuntimeError(f"volume mismatch for {family}/{event_id}")
            x = float(payload["production_x_cm"][idx])
            y = float(payload["production_y_cm"][idx])
            z = float(payload["production_z_cm"][idx])
            ifx, ify, ifz = world_to_if(x, y, z)
            component_r, component_axial, axis_definition = component_coordinates(
                row["source_volume"], ifx, ify, ifz
            )
            frozen_row = frozen.get((family, event_id))
            if frozen_row is not None:
                if not math.isclose(
                    component_r, f(frozen_row["component_r_cm"]),
                    rel_tol=0.0, abs_tol=1.0e-12,
                ) or not math.isclose(
                    component_axial, f(frozen_row["component_axial_cm"]),
                    rel_tol=0.0, abs_tol=1.0e-12,
                ):
                    raise RuntimeError(
                        f"component-coordinate drift for {family}/{event_id}"
                    )
                frozen_component_coordinate_matches += 1
            events.append(
                {
                    "family": family,
                    "local_event_id": event_id,
                    "source_file": row["source_file"],
                    "source_parent_ZA": i(row["source_parent_ZA"]),
                    "source_volume": row["source_volume"],
                    "material": material_label(row["source_volume"]),
                    "component_group": component_group(row["source_volume"]),
                    "event_weight_cps": f(row["event_weight_cps"]),
                    "world_x_cm": x,
                    "world_y_cm": y,
                    "world_z_cm": z,
                    "instrument_x_cm": ifx,
                    "instrument_y_cm": ify,
                    "instrument_z_cm": ifz,
                    "generic_axis_x_cm": ifx,
                    "generic_radius_about_IF_x_axis_at_z_minus5p2_cm": math.hypot(
                        ify, ifz - AXIS_IF_Z_CM
                    ),
                    "component_r_cm": component_r,
                    "component_axial_cm": component_axial,
                    "component_axis_definition": axis_definition,
                    "passes_frozen_selection": int(frozen_row is not None),
                    "sim_initial_ZA": int(payload["sim_initial_ZA"][idx]),
                }
            )
            coordinate_matches += 1
    return events, coordinate_matches, frozen_component_coordinate_matches


def build_key_flow(
    inventory: dict[tuple[str, str, int], dict[str, Any]],
    family_activity: dict[str, float],
    source_mix: dict[tuple[str, str, int], dict[str, Any]],
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], dict[str, Any]]]:
    selected: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        selected[(event["family"], event["source_volume"], event["source_parent_ZA"])].append(event)
    keys = sorted(set(inventory) | set(source_mix) | set(selected))
    rows: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for key in keys:
        inv = inventory.get(key, {})
        mix = source_mix.get(key, {})
        selected_events = selected.get(key, [])
        weights = [event["event_weight_cps"] for event in selected_events]
        activity = f(inv.get("day15_activity_Bq"))
        family_total = family_activity.get(key[0], 0.0)
        inventory_fraction = activity / family_total if family_total > 0.0 else 0.0
        triggers = i(mix.get("realized_250000_triggers"))
        selected_count = len(selected_events)
        coupling = selected_count / triggers if triggers > 0 else math.nan
        if triggers <= 0:
            coupling_status = "UNKNOWN__NO_REALIZED_TRIGGER_DENOMINATOR"
        elif selected_count == 0:
            coupling_status = "ZERO_OBSERVATION__FINITE_UPPER_LIMIT_ONLY"
        elif selected_count == 1:
            coupling_status = "SINGLE_SELECTED_EVENT__LOW_NEFF"
        elif selected_count < 10:
            coupling_status = "LOW_SELECTED_COUNT_LT10"
        else:
            coupling_status = "FINITE_SAMPLE_SCREENING_ESTIMATE"
        observed_rate = math.fsum(weights)
        reweighted_rate = activity * coupling if math.isfinite(coupling) else math.nan
        positions = defaultdict(list)
        for event in selected_events:
            pos = (
                round(event["world_x_cm"], 5), round(event["world_y_cm"], 5),
                round(event["world_z_cm"], 5),
            )
            positions[pos].append(event["event_weight_cps"])
        max_position_rate = max((math.fsum(values) for values in positions.values()), default=0.0)
        position_rates = [math.fsum(values) for values in positions.values()]
        row = {
            "family": key[0],
            "material": inv.get("material", material_label(key[1])),
            "component_group": inv.get("component_group", component_group(key[1])),
            "source_parent_ZA": key[2],
            "isotope": isotope_label(key[2]),
            "source_volume": key[1],
            "production_rate_s-1": f(inv.get("production_rate_s-1")),
            "day15_activity_Bq": activity,
            "sum_RP": f(inv.get("sum_RP")),
            "RPIP_support_count": i(inv.get("RPIP_support_count")),
            "sum_TT_s": f(inv.get("sum_TT_s")),
            "inventory_fraction_within_family": inventory_fraction,
            "full_50000_blocks": i(mix.get("full_50000_blocks")),
            "full_50000_fraction": f(mix.get("full_50000_fraction")),
            "selected_10000_blocks": i(mix.get("selected_10000_blocks")),
            "selected_10000_fraction": f(mix.get("selected_10000_fraction")),
            "realized_250000_triggers": triggers,
            "realized_250000_fraction": f(mix.get("realized_250000_fraction")),
            "realized_to_inventory_mix_ratio": (
                f(mix.get("realized_250000_fraction")) / inventory_fraction
                if inventory_fraction > 0.0 else math.nan
            ),
            "realized_to_full50000_mix_ratio": (
                f(mix.get("realized_250000_fraction")) / f(mix.get("full_50000_fraction"))
                if f(mix.get("full_50000_fraction")) > 0.0 else math.nan
            ),
            "selected_event_rows": selected_count,
            "selected_unique_source_positions": len(positions),
            "selected_source_position_Neff": neff(position_rates),
            "selected_rate_cps_observed_mix": observed_rate,
            "selected_rate_fraction_of_full_delayed": observed_rate / EXPECTED_SELECTED_RATE_CPS,
            "selected_event_Neff": neff(weights),
            "dominant_event_fraction_of_key_rate": max(weights, default=0.0) / observed_rate if observed_rate > 0 else 0.0,
            "dominant_position_fraction_of_key_rate": max_position_rate / observed_rate if observed_rate > 0 else 0.0,
            "single_selected_event_flag": int(selected_count == 1),
            "W2_per_decay_realized_trigger_denominator": coupling,
            "W2_per_decay_support_status": coupling_status,
            "W2_per_decay_binomial_sigma_proxy": (
                math.sqrt(coupling * (1.0 - coupling) / triggers)
                if triggers > 0 and math.isfinite(coupling) else math.nan
            ),
            "W2_per_decay_zero_selected_95pct_upper": (
                1.0 - 0.05 ** (1.0 / triggers)
                if triggers > 0 and selected_count == 0 else math.nan
            ),
            "selected_rate_per_full_inventory_Bq_naive": observed_rate / activity if activity > 0.0 else math.nan,
            "selected_rate_cps_full_inventory_reweighted": reweighted_rate,
            "source_mix_reweight_factor": reweighted_rate / observed_rate if observed_rate > 0.0 else math.nan,
        }
        rows.append(row)
        by_key[key] = row
    return rows, by_key


def grouped_summary(
    group_name: str,
    groups: dict[str, list[tuple[str, str, int]]],
    inventory: dict[tuple[str, str, int], dict[str, Any]],
    key_flow: dict[tuple[str, str, int], dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events_by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_key[(event["family"], event["source_volume"], event["source_parent_ZA"])].append(event)
    output = []
    for label, keys in sorted(groups.items()):
        ev = [event for key in keys for event in events_by_key.get(key, [])]
        weights = [event["event_weight_cps"] for event in ev]
        observed = math.fsum(weights)
        total_bq = math.fsum(f(inventory.get(key, {}).get("day15_activity_Bq")) for key in keys)
        production = math.fsum(f(inventory.get(key, {}).get("production_rate_s-1")) for key in keys)
        sum_rp = math.fsum(f(inventory.get(key, {}).get("sum_RP")) for key in keys)
        supported_keys = [key for key in keys if i(key_flow.get(key, {}).get("realized_250000_triggers")) > 0]
        supported_bq = math.fsum(f(inventory.get(key, {}).get("day15_activity_Bq")) for key in supported_keys)
        reweighted = math.fsum(
            f(key_flow[key].get("selected_rate_cps_full_inventory_reweighted"))
            for key in supported_keys
            if math.isfinite(f(key_flow[key].get("selected_rate_cps_full_inventory_reweighted"), math.nan))
        )
        positions: dict[tuple[Any, ...], list[float]] = defaultdict(list)
        for event in ev:
            positions[(
                event["family"], event["source_volume"], event["source_parent_ZA"],
                round(event["world_x_cm"], 5), round(event["world_y_cm"], 5),
                round(event["world_z_cm"], 5),
            )].append(event["event_weight_cps"])
        max_position = max((math.fsum(value) for value in positions.values()), default=0.0)
        position_rates = [math.fsum(value) for value in positions.values()]
        max_event = max(weights, default=0.0)
        value_neff = neff(weights)
        if not ev:
            verdict = "ZERO_SELECTED__COUPLING_UPPER_LIMIT_NEEDED"
        elif value_neff < 10.0 or max_event / observed >= 0.5:
            verdict = "UNRESOLVED_LOW_NEFF_OR_SINGLE_EVENT_CONTROL"
        else:
            verdict = "SCREENING_ONLY__NOT_PROMOTION_PRECISION"
        output.append(
            {
                group_name: label,
                "production_rate_s-1": production,
                "day15_activity_Bq": total_bq,
                "sum_RP": sum_rp,
                "selected_event_rows": len(ev),
                "selected_unique_source_positions": len(positions),
                "selected_source_position_Neff": neff(position_rates),
                "selected_rate_cps_observed_mix": observed,
                "selected_rate_fraction_of_full_delayed": observed / EXPECTED_SELECTED_RATE_CPS,
                "selected_event_Neff": value_neff,
                "dominant_event_fraction_of_group_rate": max_event / observed if observed > 0.0 else 0.0,
                "dominant_position_fraction_of_group_rate": max_position / observed if observed > 0.0 else 0.0,
                "coupling_supported_Bq": supported_bq,
                "coupling_Bq_coverage_fraction": supported_bq / total_bq if total_bq > 0.0 else 0.0,
                "selected_rate_cps_full_inventory_reweighted": reweighted,
                "W2_per_Bq_on_supported_inventory": reweighted / supported_bq if supported_bq > 0.0 else math.nan,
                "W2_per_Bq_zero_imputed_over_all_inventory": reweighted / total_bq if total_bq > 0.0 else math.nan,
                "support_verdict": verdict,
            }
        )
    return output


def main() -> None:
    inventory, family_activity, holdout = aggregate_inventory()
    source_mix = aggregate_source_mix()
    events, coordinate_matches, frozen_component_coordinate_matches = load_selected_events()
    if len(events) != EXPECTED_SELECTED_ROWS:
        raise RuntimeError(f"selected row count drift: {len(events)}")
    selected_rate = math.fsum(event["event_weight_cps"] for event in events)
    if not math.isclose(selected_rate, EXPECTED_SELECTED_RATE_CPS, rel_tol=0.0, abs_tol=1.0e-14):
        raise RuntimeError(f"selected rate drift: {selected_rate}")
    trigger_by_family: dict[str, int] = defaultdict(int)
    for key, mix in source_mix.items():
        trigger_by_family[key[0]] += mix["realized_250000_triggers"]
    bad_trigger_cells = {
        family: count for family, count in trigger_by_family.items()
        if count != N_TRIGGERS_PER_FAMILY
    }
    if bad_trigger_cells:
        raise RuntimeError(f"source-mix trigger closure failed: {bad_trigger_cells}")

    key_rows, key_flow = build_key_flow(inventory, family_activity, source_mix, events)
    flow_fields = list(key_rows[0])
    write_csv(HERE / "delayed_key_flow.csv", key_rows, flow_fields)

    component_keys: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    component_family_keys: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    material_keys: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    isotope_family_keys: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for key in sorted(inventory):
        component_keys[component_group(key[1])].append(key)
        component_family_keys[f"{component_group(key[1])} | {key[0]}"].append(key)
        material_keys[inventory[key]["material"]].append(key)
        isotope_family_keys[f"{key[0]} -> {isotope_label(key[2])}"].append(key)
    component_rows = grouped_summary(
        "component_group", component_keys, inventory, key_flow, events
    )
    write_csv(HERE / "delayed_component_summary.csv", component_rows, list(component_rows[0]))
    component_family_rows = grouped_summary(
        "component_family", component_family_keys, inventory, key_flow, events
    )
    write_csv(
        HERE / "delayed_component_family_summary.csv",
        component_family_rows,
        list(component_family_rows[0]),
    )
    material_rows = grouped_summary(
        "material", material_keys, inventory, key_flow, events
    )
    write_csv(
        HERE / "delayed_material_summary.csv",
        material_rows,
        list(material_rows[0]),
    )
    isotope_rows = grouped_summary(
        "family_to_isotope", isotope_family_keys, inventory, key_flow, events
    )
    write_csv(HERE / "delayed_family_isotope_summary.csv", isotope_rows, list(isotope_rows[0]))

    component_rates = {
        row["component_group"]: row["selected_rate_cps_observed_mix"]
        for row in component_rows
    }
    position_events: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        position_events[(
            event["family"], event["source_volume"], event["source_parent_ZA"],
            round(event["world_x_cm"], 5), round(event["world_y_cm"], 5),
            round(event["world_z_cm"], 5),
        )].append(event)
    bubble_rows = []
    for key, grouped_events in sorted(position_events.items()):
        first = grouped_events[0]
        flow = key_flow[(first["family"], first["source_volume"], first["source_parent_ZA"])]
        weights = [event["event_weight_cps"] for event in grouped_events]
        rate = math.fsum(weights)
        component_rate = component_rates[first["component_group"]]
        bubble_rows.append(
            {
                "family": first["family"],
                "material": first["material"],
                "component_group": first["component_group"],
                "source_parent_ZA": first["source_parent_ZA"],
                "isotope": isotope_label(first["source_parent_ZA"]),
                "source_volume": first["source_volume"],
                "world_x_cm": first["world_x_cm"],
                "world_y_cm": first["world_y_cm"],
                "world_z_cm": first["world_z_cm"],
                "instrument_x_cm": first["instrument_x_cm"],
                "instrument_y_cm": first["instrument_y_cm"],
                "instrument_z_cm": first["instrument_z_cm"],
                "generic_axis_x_cm": first["generic_axis_x_cm"],
                "generic_radius_about_IF_x_axis_at_z_minus5p2_cm": first[
                    "generic_radius_about_IF_x_axis_at_z_minus5p2_cm"
                ],
                "component_r_cm": first["component_r_cm"],
                "component_axial_cm": first["component_axial_cm"],
                "component_axis_definition": first["component_axis_definition"],
                "selected_event_rows_at_position": len(grouped_events),
                "selected_event_Neff_at_position": neff(weights),
                "selected_rate_cps_at_position": rate,
                "rate_fraction_of_full_delayed": rate / selected_rate,
                "rate_fraction_of_component": rate / component_rate if component_rate > 0 else 0.0,
                "dominant_event_fraction_at_position": max(weights) / rate,
                "single_selected_event_position_flag": int(len(grouped_events) == 1),
                "single_event_high_weight_flag": int(
                    len(grouped_events) == 1
                    and (rate / selected_rate >= 0.01 or rate / component_rate >= 0.10)
                ),
                "passes_frozen_selection_rows": sum(event["passes_frozen_selection"] for event in grouped_events),
                "event_ids": "|".join(str(event["local_event_id"]) for event in grouped_events),
                "key_day15_activity_Bq": flow["day15_activity_Bq"],
                "key_realized_triggers": flow["realized_250000_triggers"],
                "key_W2_per_decay": flow["W2_per_decay_realized_trigger_denominator"],
                "key_realized_to_inventory_mix_ratio": flow["realized_to_inventory_mix_ratio"],
            }
        )
    bubble_rows.sort(key=lambda row: -row["selected_rate_cps_at_position"])
    write_csv(HERE / "delayed_position_bubbles.csv", bubble_rows, list(bubble_rows[0]))

    # A compact Sankey-friendly table: one row is one complete production-to-W2 path.
    sankey_rows = [row for row in key_rows if row["day15_activity_Bq"] > 0.0 or row["selected_event_rows"] > 0]
    write_csv(HERE / "delayed_production_to_w2_flow.csv", sankey_rows, flow_fields)
    compact_sankey_rows = [
        row for row in key_rows
        if row["selected_event_rows"] > 0
        or (
            row["component_group"] != "Other"
            and row["source_parent_ZA"] in TARGET_PARENT_ZA
            and row["day15_activity_Bq"] > 0.0
        )
    ]
    write_csv(
        HERE / "delayed_production_to_w2_flow_compact.csv",
        compact_sankey_rows,
        flow_fields,
    )

    total_inventory = math.fsum(item["day15_activity_Bq"] for item in inventory.values())
    audit = {
        "status": "PASS__INDEPENDENT_DELAYED_DENOMINATOR_AUDIT",
        "scope": "S3d-O8 official full Step05-selected day-15 delayed W2 lineage",
        "normalization": {
            "production": "sum(RP)/sum(TT) separately within S3d_O8 x BUILDUP x family; zero-RP DAT TT already retained by authority",
            "coupling": "selected rows for one family/volume/ZA divided by that key's realized decay triggers",
            "source_mix_reweight": "full inventory Bq multiplied by selected/realized-trigger coupling",
        },
        "selected_rows": len(events),
        "selected_rate_cps": selected_rate,
        "selected_Neff": neff(event["event_weight_cps"] for event in events),
        "selected_unique_source_positions": len(position_events),
        "selected_source_position_Neff": neff(
            math.fsum(event["event_weight_cps"] for event in grouped_events)
            for grouped_events in position_events.values()
        ),
        "coordinate_matches_to_compact_catalog": coordinate_matches,
        "component_coordinate_matches_to_frozen_rows": frozen_component_coordinate_matches,
        "transported_ground_activity_Bq": total_inventory,
        "known_excited_state_holdout_Bq": holdout,
        "family_activity_Bq": family_activity,
        "realized_triggers_by_family": dict(sorted(trigger_by_family.items())),
        "source_mix_warning": (
            "Observed weighted W2 contributions follow the realized 250k-trigger source mix. "
            "Use selected/realized-trigger coupling and full inventory Bq for source-mix-corrected screening; "
            "do not call observed_rate/full_Bq a decay coupling when mix ratios differ."
        ),
        "axis_definition": {
            "frame": "InstrumentFrame = World Ry(+45 deg)",
            "component_coordinates": (
                "Use component_r_cm/component_axial_cm together with "
                "component_axis_definition. Cold plates and can bottom use local_z; "
                "Nb/Mu/open-ring/L0 structures use local_x_about_z=-5.2."
            ),
            "generic_cross_component_coordinates": (
                "generic_radius_about_IF_x_axis_at_z_minus5p2_cm is only a common "
                "cross-component view; it is not MXC/cold-plate local radius."
            ),
        },
        "files": [
            "delayed_key_flow.csv",
            "delayed_component_summary.csv",
            "delayed_component_family_summary.csv",
            "delayed_material_summary.csv",
            "delayed_family_isotope_summary.csv",
            "delayed_position_bubbles.csv",
            "delayed_production_to_w2_flow.csv",
            "delayed_production_to_w2_flow_compact.csv",
        ],
    }
    (HERE / "audit_summary.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
