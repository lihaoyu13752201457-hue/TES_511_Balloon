#!/usr/bin/env python3
"""Read-only delayed-lineage and exact-geometry audit for thermal-Cu rethink.

The script streams only the seven official S3d-O8 delayed SIM files referenced
by the 420-row selected lineage.  It does not run particle transport.  It
reconstructs which annihilation photon supplied each type-2 (TES) HTsim hit,
finds the anti-TES sibling through IA parentage, and traces that sibling as an
unscattered ray through the retained baseline geometry.

All rates retain the exact geometry x family x parent-ZA mission join.  The
straight-ray result is a geometric opportunity/ceiling, never a realized veto
efficiency claim.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SOURCE_WT = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
M05 = (
    SOURCE_WT
    / "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813"
)
LINEAGE = M05 / "outputs/04_common_response/selected_background_w2_lineage.csv"
MISSION = M05 / "outputs/06_mission"
GEOMETRY = (
    SOURCE_WT
    / "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
QUERY = (
    REPO
    / "engineering/s3d_o8_loop_engineering_20260814/code/"
    "query_megalib_geometry"
)
TRACER = (
    REPO
    / "engineering/s3d_o8_loop_engineering_20260814/agents/prompt/"
    "trace_true_geometry_rays"
)

EXPECTED_ROWS = 420
EXPECTED_STATIC_CPS = 0.05447975222726722
EXPECTED_MISSION_COUNTS = 88804.86265187593
SECONDS_20D = 20.0 * 86400.0

ACTIVE_BGO = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}
ACTIVE_PLASTIC = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}
ACTIVE = ACTIVE_BGO | ACTIVE_PLASTIC
TOP_BGO = "BGO_S3D_O8_FullWrap_TopAnnulus_10mm"
SIDE_BGO = "BGO_S3C_FullWrap_SideShell_WindowCut_40mm"
BOTTOM_BGO = "BGO_S3D_O8_FullWrap_BottomCap_30mm"

CENTRAL_THERMAL_CU = {
    "ColdPlate_MXC_50mK_SD_anchor",
    "ColdPlate_CP_100mK_intercept",
    "ColdPlate_Still_0p7K",
    "ColdPlate_4K",
    "ColdPlate_60K",
    "Cu_50mK_StillLike_Can_bottom_cap_2mm",
    "Cu_SubstrateSupport_SolidDisk_L0_deepest",
}

CC_RE = re.compile(
    r"^CC HIT (\S+) edep_keV=([0-9.eE+\-]+).*? sec=(\S+) tid=(\d+) "
    r"pid=(\d+).*? cproc=(\S+)"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write an empty CSV: {path}")
    if fields is None:
        fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def neff(values: Iterable[float]) -> float:
    weights = list(values)
    total = math.fsum(weights)
    squares = math.fsum(value * value for value in weights)
    return total * total / squares if squares > 0.0 else 0.0


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def component_group(volume: str) -> str:
    if volume == "ColdPlate_MXC_50mK_SD_anchor":
        return "MXC_50mK_plate"
    if volume == "Nb_MagShield_Inner_Cylinder_2mm":
        return "Nb_inner_cylinder"
    if volume == "MuMetal_MagShield_Outer_Cylinder_2mm":
        return "MuMetal_outer_cylinder"
    if volume == "Cu_50mK_StillLike_Can_bottom_cap_2mm":
        return "can_50mK_bottom"
    if volume == "Cu_SubstrateSupport_SolidDisk_L0_deepest":
        return "L0_Cu_disk"
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L5_"):
        return "L5_Cu_support"
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L2_"):
        return "L2_Cu_support"
    if "Ag" in volume or "Sinter" in volume:
        return "Ag_sinter_proxy"
    if volume.startswith("ColdPlate_"):
        return "other_cold_plate"
    return "Other"


def material_group(volume: str) -> str:
    if volume.startswith("Nb_"):
        return "Nb"
    if volume.startswith("MuMetal_"):
        return "Mu-metal"
    if "CuNi" in volume:
        return "CuNi"
    if "Ag" in volume or "Sinter" in volume:
        return "Ag-proxy"
    if volume.startswith(("Cu_", "ColdPlate_", "DR_MixingChamber_Cu", "DR_Still_Pot_Cu", "DR_4K_Condenser_Cu")):
        return "Copper"
    return "Other"


def parse_ia(line: str) -> dict[str, Any]:
    fields = line.split(";")
    head = fields[0].split()
    if len(fields) != 23:
        raise ValueError(f"IA field-count drift: {line}")
    return {
        "process": head[1],
        "id": int(head[2]),
        "parent": int(fields[1]),
        "detector_type": int(fields[2]),
        "time_s": float(fields[3]),
        "xyz": tuple(float(fields[i]) for i in (4, 5, 6)),
        "in_type": int(fields[7]),
        "in_direction": tuple(float(fields[i]) for i in (8, 9, 10)),
        "in_energy_keV": float(fields[14]),
        "out_type": int(fields[15]),
        "direction": tuple(float(fields[i]) for i in (16, 17, 18)),
        "energy_keV": float(fields[22]),
    }


def parse_htsim(line: str) -> dict[str, Any]:
    fields = [field.strip() for field in line[len("HTsim "):].split(";")]
    if len(fields) < 7:
        raise ValueError(f"malformed HTsim: {line}")
    return {
        "detector_type": int(fields[0]),
        "xyz": tuple(float(fields[i]) for i in (1, 2, 3)),
        "energy_keV": float(fields[4]),
        "time_s": float(fields[5]),
        "origins": tuple(int(value) for value in fields[6:]),
    }


def stream_selected_events(lineage: list[dict[str, str]]) -> dict[tuple[str, int], dict[str, Any]]:
    by_file: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in lineage:
        event_id = int(row["local_event_id"])
        if event_id in by_file[row["source_file"]]:
            raise RuntimeError("duplicate selected event ID within one SIM")
        by_file[row["source_file"]][event_id] = row

    events: dict[tuple[str, int], dict[str, Any]] = {}
    for path_text, wanted in sorted(by_file.items()):
        active: dict[str, Any] | None = None
        found: set[int] = set()
        with gzip.open(path_text, "rt", encoding="utf-8", errors="replace") as stream:
            for raw in stream:
                line = raw.rstrip("\n")
                if line.startswith("ID "):
                    event_id = int(line.split()[1])
                    if event_id in wanted:
                        if event_id in found:
                            raise RuntimeError(f"duplicate raw event {event_id}: {path_text}")
                        row = wanted[event_id]
                        active = {
                            "lineage": row,
                            "interactions": [],
                            "htsim": [],
                            "cc_active_keV": defaultdict(float),
                            "cc_tes_keV": 0.0,
                        }
                        found.add(event_id)
                    else:
                        active = None
                    continue
                if active is None:
                    continue
                if line.startswith("IA "):
                    active["interactions"].append(parse_ia(line))
                elif line.startswith("HTsim "):
                    active["htsim"].append(parse_htsim(line))
                elif match := CC_RE.match(line):
                    volume, energy, _sec, _tid, _pid, _cproc = match.groups()
                    edep = float(energy)
                    if volume.startswith("TP_L"):
                        active["cc_tes_keV"] += edep
                    elif volume in ACTIVE:
                        active["cc_active_keV"][volume] += edep
                elif line in {"SE", "EN"}:
                    row = active["lineage"]
                    key = (row["family"], int(row["local_event_id"]))
                    events[key] = active
                    active = None
        missing = set(wanted) - found
        if missing:
            raise RuntimeError(f"selected raw events absent in {path_text}: {sorted(missing)[:10]}")
    if len(events) != EXPECTED_ROWS:
        raise RuntimeError(f"raw selected closure drift: {len(events)}")
    return events


def nearest_ancestor_process(
    start: int,
    process: str,
    by_id: dict[int, dict[str, Any]],
    parent_of: dict[int, int],
) -> int | None:
    seen: set[int] = set()
    current = start
    while current and current not in seen:
        seen.add(current)
        ia = by_id.get(current)
        if ia is not None and ia["process"] == process:
            return current
        current = parent_of.get(current, 0)
    return None


def descends_from(ia_id: int, ancestor: int, parent_of: dict[int, int]) -> bool:
    seen: set[int] = set()
    current = ia_id
    while current and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        current = parent_of.get(current, 0)
    return False


def mission_exposure_factors(
    lineage: list[dict[str, str]],
) -> tuple[dict[tuple[str, int], float], float, float]:
    timeline = [
        row for row in read_csv(MISSION / "mission_timeline.csv")
        if row["geometry"] == "S3d_O8"
    ]
    timeline.sort(key=lambda row: int(row["time_bin_id"]))
    if len(timeline) != 81:
        raise RuntimeError("mission timeline row drift")
    dt = {int(row["time_bin_id"]): float(row["trajectory_quadrature_weight_s"]) for row in timeline}
    live = {int(row["time_bin_id"]): float(row["accidental_live_factor"]) for row in timeline}
    if not math.isclose(math.fsum(dt.values()), SECONDS_20D, abs_tol=1.0e-9):
        raise RuntimeError("mission quadrature does not close")
    activity = [
        row for row in read_csv(MISSION / "family_parent_activity_by_time.csv")
        if row["geometry"] == "S3d_O8"
    ]
    scales = {
        (int(row["time_bin_id"]), row["incident_family"], int(row["source_parent_ZA"])):
        float(row["activity_scale_to_constant_environment_day15_inventory"])
        for row in activity
    }
    parent_keys = {(row["family"], int(row["source_parent_ZA"])) for row in lineage}
    factors: dict[tuple[str, int], float] = {}
    for family, parent in parent_keys:
        factors[(family, parent)] = math.fsum(
            dt[index] * live[index] * scales[(index, family, parent)]
            for index in range(81)
        )
    effective_live = math.fsum(dt[index] * live[index] for index in range(81))
    prompt_counts = math.fsum(
        float(row["prompt_final_cps_noacc"])
        * float(row["trajectory_quadrature_weight_s"])
        * float(row["accidental_live_factor"])
        for row in timeline
    )
    return factors, effective_live, prompt_counts


def reconstruct_events(
    raw_events: dict[tuple[str, int], dict[str, Any]],
    mission_factors: dict[tuple[str, int], float],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for (family, event_id), raw in sorted(raw_events.items()):
        row = raw["lineage"]
        interactions = raw["interactions"]
        by_id = {int(ia["id"]): ia for ia in interactions}
        parent_of = {int(ia["id"]): int(ia["parent"]) for ia in interactions}
        if len(by_id) != len(interactions):
            raise RuntimeError(f"duplicate IA ID: {family}/{event_id}")
        init = next((ia for ia in interactions if ia["process"] == "INIT"), None)
        tes_ht = [ht for ht in raw["htsim"] if ht["detector_type"] == 2]
        tes_raw_keV = math.fsum(ht["energy_keV"] for ht in tes_ht)
        energy_by_anni: dict[int, float] = defaultdict(float)
        ambiguous_ht_keV = 0.0
        no_anni_ht_keV = 0.0
        for ht in tes_ht:
            ancestors = {
                ancestor
                for origin in ht["origins"]
                if (ancestor := nearest_ancestor_process(origin, "ANNI", by_id, parent_of)) is not None
            }
            if len(ancestors) == 1:
                energy_by_anni[next(iter(ancestors))] += ht["energy_keV"]
            elif not ancestors:
                no_anni_ht_keV += ht["energy_keV"]
            else:
                ambiguous_ht_keV += ht["energy_keV"]

        tes_anni_ids = sorted(energy_by_anni)
        trace_status = "UNKNOWN__NO_TES_ANNI_ANCESTOR"
        tes_anni = None
        sibling = None
        if len(tes_anni_ids) > 1:
            trace_status = "UNKNOWN__MULTIPLE_TES_ANNI_ANCESTORS"
        elif len(tes_anni_ids) == 1:
            tes_anni = by_id[tes_anni_ids[0]]
            siblings = [
                ia for ia in interactions
                if ia["process"] == "ANNI"
                and ia["id"] != tes_anni["id"]
                and ia["parent"] == tes_anni["parent"]
                and abs(float(ia["time_s"]) - float(tes_anni["time_s"])) < 1.0e-18
            ]
            if len(siblings) == 1:
                sibling = siblings[0]
                trace_status = "FACT__UNIQUE_TES_ANNI_AND_ANTIPODAL_SIBLING"
            else:
                trace_status = f"UNKNOWN__TES_ANNI_SIBLING_MULTIPLICITY_{len(siblings)}"

        weight = float(row["event_weight_cps"])
        parent = int(row["source_parent_ZA"])
        source_xyz = init["xyz"] if init is not None else (math.nan, math.nan, math.nan)
        source_if = world_to_if(*source_xyz) if init is not None else (math.nan, math.nan, math.nan)
        result: dict[str, Any] = {
            "family": family,
            "local_event_id": event_id,
            "source_parent_ZA": parent,
            "source_volume": row["source_volume"],
            "source_material_group": material_group(row["source_volume"]),
            "source_component_group": component_group(row["source_volume"]),
            "event_weight_cps": weight,
            "mission_counts_20d_baseline_live": weight * mission_factors[(family, parent)],
            "measured_total_keV": float(row["measured_total_keV"]),
            "raw_type2_tes_keV": tes_raw_keV,
            "cc_tes_keV": float(raw["cc_tes_keV"]),
            "cc_active_total_keV": math.fsum(raw["cc_active_keV"].values()),
            "cc_active_by_volume": "|".join(
                f"{volume}:{energy:.9g}" for volume, energy in sorted(raw["cc_active_keV"].items())
            ),
            "tes_htsim_rows": len(tes_ht),
            "tes_anni_ancestor_count": len(tes_anni_ids),
            "tes_anni_attributed_keV": math.fsum(energy_by_anni.values()),
            "tes_anni_unattributed_keV": no_anni_ht_keV,
            "tes_anni_ambiguous_keV": ambiguous_ht_keV,
            "trace_status": trace_status,
            "traceable_sibling": int(sibling is not None),
            "source_world_x_cm": source_xyz[0],
            "source_world_y_cm": source_xyz[1],
            "source_world_z_cm": source_xyz[2],
            "source_IF_x_cm": source_if[0],
            "source_IF_y_cm": source_if[1],
            "source_IF_z_cm": source_if[2],
            "tes_anni_ia_id": int(tes_anni["id"]) if tes_anni else "",
            "sibling_anni_ia_id": int(sibling["id"]) if sibling else "",
            "annihilation_world_x_cm": tes_anni["xyz"][0] if tes_anni else "",
            "annihilation_world_y_cm": tes_anni["xyz"][1] if tes_anni else "",
            "annihilation_world_z_cm": tes_anni["xyz"][2] if tes_anni else "",
            "tes_511_world_dx": tes_anni["direction"][0] if tes_anni else "",
            "tes_511_world_dy": tes_anni["direction"][1] if tes_anni else "",
            "tes_511_world_dz": tes_anni["direction"][2] if tes_anni else "",
            "sibling_world_dx": sibling["direction"][0] if sibling else "",
            "sibling_world_dy": sibling["direction"][1] if sibling else "",
            "sibling_world_dz": sibling["direction"][2] if sibling else "",
            "tes_511_IF_dx": "",
            "tes_511_IF_dy": "",
            "tes_511_IF_dz": "",
            "sibling_IF_dx": "",
            "sibling_IF_dy": "",
            "sibling_IF_dz": "",
            "anti_parallel_dot": "",
            "actual_sibling_branch_n_ia": 0,
            "actual_sibling_first_interaction_process": "UNKNOWN__POINT_MEMBERSHIP_NOT_RUN",
            "actual_sibling_first_interaction_volume": "UNKNOWN__POINT_MEMBERSHIP_NOT_RUN",
            "actual_sibling_first_interaction_material": "UNKNOWN__POINT_MEMBERSHIP_NOT_RUN",
            "actual_sibling_first_energy_change_process": "UNKNOWN__POINT_MEMBERSHIP_NOT_RUN",
            "actual_sibling_first_energy_change_volume": "UNKNOWN__POINT_MEMBERSHIP_NOT_RUN",
            # Selected events may have sub-threshold (<50 keV) event-level
            # active energy.  CC track IDs are not IA IDs, so this scan does
            # not attribute those deposits specifically to the sibling branch.
            "event_level_active_hit_any_branch": int(
                math.fsum(raw["cc_active_keV"].values()) > 0.0
            ),
            "event_level_active_hit_volumes_branch_UNKNOWN": (
                "EVENT_LEVEL_ACTIVE_HIT__BRANCH_ATTRIBUTION_UNKNOWN"
                if math.fsum(raw["cc_active_keV"].values()) > 0.0 else "NONE"
            ),
            "_actual_sibling_branch": [],
        }
        if tes_anni and sibling:
            tes_if = world_to_if(*tes_anni["direction"])
            sibling_if = world_to_if(*sibling["direction"])
            result.update({
                "tes_511_IF_dx": tes_if[0],
                "tes_511_IF_dy": tes_if[1],
                "tes_511_IF_dz": tes_if[2],
                "sibling_IF_dx": sibling_if[0],
                "sibling_IF_dy": sibling_if[1],
                "sibling_IF_dz": sibling_if[2],
                "anti_parallel_dot": math.fsum(
                    a * b for a, b in zip(tes_anni["direction"], sibling["direction"])
                ),
            })
            branch = sorted(
                [
                    ia for ia in interactions
                    if ia["id"] != sibling["id"]
                    and descends_from(int(ia["id"]), int(sibling["id"]), parent_of)
                ],
                key=lambda ia: (float(ia["time_s"]), int(ia["id"])),
            )
            result["actual_sibling_branch_n_ia"] = len(branch)
            result["_actual_sibling_branch"] = branch
            escape_gammas = [
                ia for ia in branch
                if ia["process"] == "ESCP" and int(ia["in_type"]) == 1
            ]
            escape_energies = [float(ia["in_energy_keV"]) for ia in escape_gammas]
            result["actual_sibling_escape_gamma_count"] = len(escape_gammas)
            result["actual_sibling_escape_gamma_energy_sum_keV"] = math.fsum(escape_energies)
            result["actual_sibling_escape_gamma_energy_max_keV"] = max(escape_energies, default=0.0)
            result["actual_sibling_escape_gamma_above50keV"] = int(
                any(energy >= 50.0 for energy in escape_energies)
            )
        output.append(result)
    return output


def classify_actual_branches(events: list[dict[str, Any]]) -> None:
    inputs: list[str] = []
    lookup: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for event_index, event in enumerate(events):
        for branch_index, ia in enumerate(event["_actual_sibling_branch"]):
            qid = f"q{event_index}_{branch_index}"
            x, y, z = ia["xyz"]
            inputs.append(f"{qid} {x} {y} {z}")
            lookup[qid] = (event, ia)
    proc = subprocess.run(
        [str(QUERY), str(GEOMETRY)],
        input="\n".join(inputs) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    classified: dict[int, list[tuple[dict[str, Any], str, str]]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        if not line.startswith("q"):
            continue
        qid, _x, _y, _z, volume, material, _sequence = line.split(",", 6)
        if qid not in lookup:  # query_id CSV header
            continue
        event, ia = lookup[qid]
        classified[id(event)].append((ia, volume, material))
    if sum(len(values) for values in classified.values()) != len(inputs):
        raise RuntimeError("actual branch point-classification closure failed")
    for event in events:
        points = sorted(
            classified.get(id(event), []),
            key=lambda item: (float(item[0]["time_s"]), int(item[0]["id"])),
        )
        first = next((item for item in points if item[0]["process"] != "ESCP"), None)
        first_energy = next(
            (item for item in points if item[0]["process"] not in {"ESCP", "RAYL"}),
            None,
        )
        touched = sorted({volume for _ia, volume, _material in points if volume in ACTIVE})
        def at_or_outside_current_bgo(volume: str) -> bool:
            return (
                volume in ACTIVE
                or volume.startswith("ActiveShield_S3C_BGO_Kapton_")
                or volume.startswith("Outer_Al_S3C_BGO_Mechanical_")
                or "CryoShell_BPE5" in volume
            )

        outer_gamma_points = [
            (ia, volume) for ia, volume, _material in points
            if int(ia["in_type"]) == 1
            and max(float(ia["in_energy_keV"]), float(ia["energy_keV"])) >= 50.0
            and (ia["process"] == "ESCP" or at_or_outside_current_bgo(volume))
        ]
        event["actual_sibling_first_interaction_process"] = first[0]["process"] if first else "NONE"
        event["actual_sibling_first_interaction_volume"] = first[1] if first else "NONE"
        event["actual_sibling_first_interaction_material"] = first[2] if first else "NONE"
        event["actual_sibling_first_energy_change_process"] = first_energy[0]["process"] if first_energy else "NONE"
        event["actual_sibling_first_energy_change_volume"] = first_energy[1] if first_energy else "NONE"
        event["actual_sibling_IA_point_in_active"] = int(bool(touched))
        event["actual_sibling_IA_point_active_volumes"] = "|".join(touched) if touched else "NONE"
        event["actual_sibling_gamma_ge50_reaches_current_BGO_or_outer_region"] = int(
            bool(outer_gamma_points)
        )
        event["actual_sibling_gamma_ge50_outer_region_point_count"] = len(outer_gamma_points)
        event["actual_sibling_gamma_ge50_outer_region_volumes"] = (
            "|".join(sorted({volume for _ia, volume in outer_gamma_points}))
            if outer_gamma_points else "NONE"
        )
        event["actual_sibling_gamma_outer_region_max_energy_proxy_keV"] = max(
            (
                max(float(ia["in_energy_keV"]), float(ia["energy_keV"]))
                for ia, _volume in outer_gamma_points
            ),
            default=0.0,
        )


def trace_sibling_rays(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ray_events = [event for event in events if event["traceable_sibling"]]
    by_ray: dict[str, dict[str, Any]] = {}
    feed: list[str] = []
    for index, event in enumerate(ray_events):
        ray_id = f"r{index:04d}"
        by_ray[ray_id] = event
        feed.append(" ".join([
            ray_id,
            str(event["annihilation_world_x_cm"]),
            str(event["annihilation_world_y_cm"]),
            str(event["annihilation_world_z_cm"]),
            str(event["sibling_world_dx"]),
            str(event["sibling_world_dy"]),
            str(event["sibling_world_dz"]),
            "60", "0.01",
        ]))
    proc = subprocess.run(
        [str(TRACER), str(GEOMETRY)],
        input="\n".join(feed) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    header: list[str] | None = None
    segments: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        if line.startswith("ray_id,"):
            header = next(csv.reader([line]))
        elif line.startswith("r") and header is not None:
            values = next(csv.reader([line]))
            segment: dict[str, Any] = dict(zip(header, values))
            event = by_ray[segment["ray_id"]]
            segment.update({
                "family": event["family"],
                "local_event_id": event["local_event_id"],
                "event_weight_cps": event["event_weight_cps"],
                "mission_counts_20d_baseline_live": event["mission_counts_20d_baseline_live"],
            })
            segments.append(segment)
            grouped[segment["ray_id"]].append(segment)
    if set(grouped) != set(by_ray):
        raise RuntimeError(f"ray-trace closure failed: {len(grouped)}/{len(by_ray)}")

    intersections: list[dict[str, Any]] = []
    for ray_id, event in by_ray.items():
        ray_segments = sorted(grouped[ray_id], key=lambda item: int(item["segment_index"]))
        first_active = next((segment for segment in ray_segments if segment["deepest_volume"] in ACTIVE), None)
        first_active_t = float(first_active["t_entry_cm"]) if first_active else math.inf
        chords: dict[str, float] = defaultdict(float)
        pre_active_material_chords: dict[str, float] = defaultdict(float)
        pre_active_cu_volumes: dict[str, float] = defaultdict(float)
        bpe_chord = 0.0
        central_segments: list[dict[str, Any]] = []
        for segment in ray_segments:
            volume = segment["deepest_volume"]
            material = segment["material"]
            length = float(segment["path_cm"])
            chords[volume] += length
            if "BPE" in volume or material == "BoratedPolyethylene5wtB":
                bpe_chord += length
            if float(segment["t_entry_cm"]) < first_active_t:
                pre_length = min(length, first_active_t - float(segment["t_entry_cm"]))
                pre_active_material_chords[material] += pre_length
                if material == "Copper":
                    pre_active_cu_volumes[volume] += pre_length
            if volume in CENTRAL_THERMAL_CU:
                central_segments.append(segment)
        reaches_top = chords[TOP_BGO] > 0.0
        for segment in central_segments:
                volume = segment["deepest_volume"]
                length = float(segment["path_cm"])
                x = 0.5 * (float(segment["entry_x_cm"]) + float(segment["exit_x_cm"]))
                y = 0.5 * (float(segment["entry_y_cm"]) + float(segment["exit_y_cm"]))
                z = 0.5 * (float(segment["entry_z_cm"]) + float(segment["exit_z_cm"]))
                ifx, ify, ifz = world_to_if(x, y, z)
                intersections.append({
                    "family": event["family"],
                    "local_event_id": event["local_event_id"],
                    "source_component_group": event["source_component_group"],
                    "source_volume": event["source_volume"],
                    "event_weight_cps": event["event_weight_cps"],
                    "mission_counts_20d_baseline_live": event["mission_counts_20d_baseline_live"],
                    "sibling_reaches_top_BGO_unscattered": int(reaches_top),
                    "intersected_volume": volume,
                    "chord_cm": length,
                    "mid_world_x_cm": x,
                    "mid_world_y_cm": y,
                    "mid_world_z_cm": z,
                    "mid_IF_x_cm": ifx,
                    "mid_IF_y_cm": ify,
                    "mid_IF_z_cm": ifz,
                    "mid_IF_radius_cm": math.hypot(ifx, ify),
                })
        event.update({
            "ray_first_active_volume": first_active["deepest_volume"] if first_active else "NONE",
            "ray_distance_to_first_active_cm": first_active_t if first_active else "inf",
            "ray_reaches_any_active_unscattered": int(first_active is not None),
            "ray_reaches_any_BGO_unscattered": int(any(chords[volume] > 0.0 for volume in ACTIVE_BGO)),
            "ray_reaches_top_BGO_unscattered": int(chords[TOP_BGO] > 0.0),
            "ray_reaches_side_BGO_unscattered": int(chords[SIDE_BGO] > 0.0),
            "ray_reaches_bottom_BGO_unscattered": int(chords[BOTTOM_BGO] > 0.0),
            "ray_hits_top_plastic_gap_unscattered": int(
                first_active is not None
                and first_active["deepest_volume"] == "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm"
            ),
            "ray_reaches_existing_BGO_or_top_gap_unscattered": int(
                any(chords[volume] > 0.0 for volume in ACTIVE_BGO)
                or (
                    first_active is not None
                    and first_active["deepest_volume"] == "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm"
                )
            ),
            "ray_top_BGO_chord_cm": chords[TOP_BGO],
            "ray_side_BGO_chord_cm": chords[SIDE_BGO],
            "ray_bottom_BGO_chord_cm": chords[BOTTOM_BGO],
            "ray_BPE_chord_cm": bpe_chord,
            "ray_pre_active_Cu_chord_cm": pre_active_material_chords["Copper"],
            "ray_pre_active_Nb_chord_cm": pre_active_material_chords["Nb"],
            "ray_pre_active_MuMetal_chord_cm": pre_active_material_chords["MuMetal"],
            "ray_pre_active_Al_chord_cm": pre_active_material_chords["Aluminium"],
            "ray_pre_active_W_chord_cm": pre_active_material_chords["W"],
            "ray_pre_active_central_thermal_Cu_chord_cm": math.fsum(
                chord for volume, chord in pre_active_cu_volumes.items() if volume in CENTRAL_THERMAL_CU
            ),
            "ray_pre_active_Cu_volumes": "|".join(
                f"{volume}:{chord:.9g}" for volume, chord in sorted(pre_active_cu_volumes.items())
            ) or "NONE",
            "ray_top_BGO_after_central_thermal_Cu": int(
                chords[TOP_BGO] > 0.0
                and any(chords[volume] > 0.0 for volume in CENTRAL_THERMAL_CU)
            ),
        })
    return segments, intersections


def aggregate_fraction(
    label: str,
    events: list[dict[str, Any]],
    predicate,
    denominator_predicate=lambda _event: True,
    note: str = "",
) -> dict[str, Any]:
    denominator = [event for event in events if denominator_predicate(event)]
    numerator = [event for event in denominator if predicate(event)]
    denom_cps = math.fsum(event["event_weight_cps"] for event in denominator)
    num_cps = math.fsum(event["event_weight_cps"] for event in numerator)
    denom_counts = math.fsum(event["mission_counts_20d_baseline_live"] for event in denominator)
    num_counts = math.fsum(event["mission_counts_20d_baseline_live"] for event in numerator)
    weights = [event["mission_counts_20d_baseline_live"] for event in numerator]
    return {
        "metric": label,
        "denominator_rows": len(denominator),
        "numerator_rows": len(numerator),
        "row_fraction": len(numerator) / len(denominator) if denominator else math.nan,
        "denominator_static_cps": denom_cps,
        "numerator_static_cps": num_cps,
        "static_cps_fraction": num_cps / denom_cps if denom_cps > 0.0 else math.nan,
        "denominator_mission_counts_20d": denom_counts,
        "numerator_mission_counts_20d": num_counts,
        "mission_count_fraction": num_counts / denom_counts if denom_counts > 0.0 else math.nan,
        "numerator_mission_Neff": neff(weights),
        "dominant_event_fraction_of_numerator_mission_counts": (
            max(weights, default=0.0) / num_counts if num_counts > 0.0 else math.nan
        ),
        "interpretation": note,
    }


def weighted_quantile(points: list[tuple[float, float]], quantile: float) -> float:
    if not points:
        return math.nan
    ordered = sorted(points)
    total = math.fsum(weight for _value, weight in ordered)
    threshold = quantile * total
    running = 0.0
    for value, weight in ordered:
        running += weight
        if running >= threshold:
            return value
    return ordered[-1][0]


def build_intersection_summary(intersections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in intersections:
        grouped[(row["intersected_volume"], row["sibling_reaches_top_BGO_unscattered"])].append(row)
    output = []
    for (volume, reaches_top), rows in sorted(grouped.items()):
        # One event can only contribute one convex-body segment for these plates,
        # but keep the exact event denominator explicit regardless.
        weights = [float(row["mission_counts_20d_baseline_live"]) for row in rows]
        total = math.fsum(weights)
        cx = math.fsum(float(row["mid_IF_x_cm"]) * weight for row, weight in zip(rows, weights)) / total
        cy = math.fsum(float(row["mid_IF_y_cm"]) * weight for row, weight in zip(rows, weights)) / total
        radii = [
            (math.hypot(float(row["mid_IF_x_cm"]) - cx, float(row["mid_IF_y_cm"]) - cy), weight)
            for row, weight in zip(rows, weights)
        ]
        output.append({
            "intersected_volume": volume,
            "sibling_reaches_top_BGO_unscattered": reaches_top,
            "intersection_rows": len(rows),
            "unique_events": len({(row["family"], row["local_event_id"]) for row in rows}),
            "static_cps": math.fsum(float(row["event_weight_cps"]) for row in rows),
            "mission_counts_20d": total,
            "mission_Neff": neff(weights),
            "dominant_event_fraction": max(weights) / total if total > 0.0 else math.nan,
            "weighted_centroid_IF_x_cm": cx,
            "weighted_centroid_IF_y_cm": cy,
            "weighted_radius50_about_centroid_cm": weighted_quantile(radii, 0.50),
            "weighted_radius90_about_centroid_cm": weighted_quantile(radii, 0.90),
            "max_radius_about_centroid_cm": max((value for value, _weight in radii), default=math.nan),
            "scope_warning": "selected-W2 anti-TES sibling intersections only; not an unbiased decay aperture map",
        })
    return output


def main() -> None:
    lineage = [
        row for row in read_csv(LINEAGE)
        if row["geometry"] == "S3d_O8" and row["stream"] == "delayed"
    ]
    if len(lineage) != EXPECTED_ROWS:
        raise RuntimeError(f"selected lineage row drift: {len(lineage)}")
    if len({(row["family"], int(row["local_event_id"])) for row in lineage}) != EXPECTED_ROWS:
        raise RuntimeError("lineage family x local-event key is not unique")
    static_cps = math.fsum(float(row["event_weight_cps"]) for row in lineage)
    if not math.isclose(static_cps, EXPECTED_STATIC_CPS, abs_tol=1.0e-14):
        raise RuntimeError(f"selected static-rate drift: {static_cps}")

    mission_factors, effective_live, prompt_counts = mission_exposure_factors(lineage)
    raw_events = stream_selected_events(lineage)
    events = reconstruct_events(raw_events, mission_factors)
    # Classify the already-realized sibling IA branch independently of the
    # straight-ray opportunity.  Six retained rows have sub-threshold
    # event-level active energy; CC track IDs still cannot be identified with
    # IA IDs, so those energy deposits retain branch attribution UNKNOWN.
    classify_actual_branches(events)
    segments, intersections = trace_sibling_rays(events)

    mission_counts = math.fsum(event["mission_counts_20d_baseline_live"] for event in events)
    if not math.isclose(mission_counts, EXPECTED_MISSION_COUNTS, abs_tol=1.0e-8):
        raise RuntimeError(f"mission-count closure drift: {mission_counts}")
    traceable = [event for event in events if event["traceable_sibling"]]
    if any(float(event["anti_parallel_dot"]) > -0.999 for event in traceable):
        raise RuntimeError("unique ANNI sibling is not antipodal")

    segment_fields = [
        "family", "local_event_id", "event_weight_cps", "mission_counts_20d_baseline_live",
        "ray_id", "segment_index", "t_entry_cm", "t_exit_cm", "path_cm",
        "entry_x_cm", "entry_y_cm", "entry_z_cm", "exit_x_cm", "exit_y_cm", "exit_z_cm",
        "deepest_volume", "material", "is_active", "volume_sequence",
    ]
    write_csv(HERE / "delayed_sibling_ray_segments.csv", segments, segment_fields)
    write_csv(HERE / "delayed_chimney_slice_intersections.csv", intersections)
    intersection_summary = build_intersection_summary(intersections)
    write_csv(HERE / "delayed_chimney_slice_summary.csv", intersection_summary)

    event_fields = [field for field in events[0] if not field.startswith("_")]
    write_csv(HERE / "delayed_annihilation_sibling_events.csv", events, event_fields)

    metrics = [
        aggregate_fraction(
            "traceable_unique_ANNI_sibling / all420", events,
            lambda event: bool(event["traceable_sibling"]),
            note="Raw IA+type-2 HTsim lineage closure; missing fraction remains UNKNOWN for chimney claims.",
        ),
        aggregate_fraction(
            "sibling_IF_dz_positive / traceable", events,
            lambda event: float(event["sibling_IF_dz"]) > 0.0,
            lambda event: bool(event["traceable_sibling"]),
            "InstrumentFrame direction, not survivor-only extrapolation.",
        ),
        aggregate_fraction(
            "unscattered_sibling_to_any_BGO / traceable", events,
            lambda event: bool(event["ray_reaches_any_BGO_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Exact baseline geometry straight ray; opportunity ceiling, not realized veto.",
        ),
        aggregate_fraction(
            "unscattered_sibling_to_top_BGO / traceable", events,
            lambda event: bool(event["ray_reaches_top_BGO_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Tests the proposed +IF-z/top-channel chimney directly.",
        ),
        aggregate_fraction(
            "unscattered_sibling_to_side_BGO / traceable", events,
            lambda event: bool(event["ray_reaches_side_BGO_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Exact baseline geometry straight ray.",
        ),
        aggregate_fraction(
            "unscattered_sibling_to_bottom_BGO / traceable", events,
            lambda event: bool(event["ray_reaches_bottom_BGO_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Exact baseline geometry straight ray.",
        ),
        aggregate_fraction(
            "unscattered_sibling_to_top_plastic_gap / traceable", events,
            lambda event: bool(event["ray_hits_top_plastic_gap_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Exact current top-annulus hole; could only become BGO opportunity by extending the same existing top channel inward.",
        ),
        aggregate_fraction(
            "existing_BGO_or_top_gap_if_same_channel_filled / traceable", events,
            lambda event: bool(event["ray_reaches_existing_BGO_or_top_gap_unscattered"]),
            lambda event: bool(event["traceable_sibling"]),
            "Geometric ceiling after hypothetical top-hole infill; still not 511 survival or threshold efficiency.",
        ),
        aggregate_fraction(
            "top_BGO_after_central_thermal_Cu / traceable", events,
            lambda event: bool(event["ray_top_BGO_after_central_thermal_Cu"]),
            lambda event: bool(event["traceable_sibling"]),
            "Upper ceiling for a Cu-preserving aperture that only clears named central thermal-Cu volumes.",
        ),
        aggregate_fraction(
            "event_level_subthreshold_active_hit_any_branch / traceable", events,
            lambda event: bool(event["event_level_active_hit_any_branch"]),
            lambda event: bool(event["traceable_sibling"]),
            "Six rows have event-level active energy below the 50-keV veto threshold; sibling-branch attribution is UNKNOWN.",
        ),
    ]

    for component in sorted({event["source_component_group"] for event in events}):
        metrics.append(aggregate_fraction(
            f"source_component={component}: top_BGO / traceable_component",
            events,
            lambda event: bool(event["ray_reaches_top_BGO_unscattered"]),
            lambda event, component=component: (
                bool(event["traceable_sibling"])
                and event["source_component_group"] == component
            ),
            "Component-specific selected-lineage directional denominator.",
        ))
    write_csv(HERE / "delayed_sibling_denominator_summary.csv", metrics)

    status_counts: dict[str, int] = defaultdict(int)
    status_cps: dict[str, float] = defaultdict(float)
    status_mission: dict[str, float] = defaultdict(float)
    for event in events:
        status_counts[event["trace_status"]] += 1
        status_cps[event["trace_status"]] += event["event_weight_cps"]
        status_mission[event["trace_status"]] += event["mission_counts_20d_baseline_live"]

    audit = {
        "status": "PASS__READ_ONLY_420_LINEAGE_AND_TRUE_GEOMETRY_TRACE",
        "scope": "official S3d-O8 delayed selected W2 lineage only",
        "selected_rows": len(events),
        "selected_static_cps": static_cps,
        "selected_mission_counts_20d_baseline_live": mission_counts,
        "selected_mission_Neff": neff(event["mission_counts_20d_baseline_live"] for event in events),
        "dominant_event_fraction_of_mission_counts": max(
            event["mission_counts_20d_baseline_live"] for event in events
        ) / mission_counts,
        "trace_status_rows": dict(sorted(status_counts.items())),
        "trace_status_static_cps": dict(sorted(status_cps.items())),
        "trace_status_mission_counts": dict(sorted(status_mission.items())),
        "mission_effective_live_exposure_s": effective_live,
        "baseline_prompt_counts_20d": prompt_counts,
        "geometry": str(GEOMETRY),
        "geometry_trace": {
            "type": "unscattered exact-volume ray membership",
            "tmax_cm": 60.0,
            "coarse_step_cm": 0.01,
            "boundary_refinement_cm": 1.0e-9,
            "warning": "geometric reach/chord is not interaction survival or BGO threshold efficiency",
        },
        "normalization_boundary": "S3d_O8 x exact delayed family x source_parent_ZA; event weight folded with retained 81-node activity and baseline live factor",
        "files": [
            "delayed_annihilation_sibling_events.csv",
            "delayed_sibling_ray_segments.csv",
            "delayed_chimney_slice_intersections.csv",
            "delayed_chimney_slice_summary.csv",
            "delayed_sibling_denominator_summary.csv",
        ],
    }
    (HERE / "audit_summary.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
