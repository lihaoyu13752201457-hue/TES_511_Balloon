#!/usr/bin/env python3
"""Read-only prompt-chain audit for removing magnetic and copper enclosures.

This does not transport a changed geometry.  It joins the ten selected baseline
chains, traces the original uncollided primary/annihilation-partner rays through
the baseline CSG, and reports which tagged hosts/chords belong to each removal
scope.  A skipped CSG segment is only a host-migration candidate, never an event
deletion claim.
"""

from __future__ import annotations

import csv
import gzip
import math
import subprocess
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
LOOP = HERE.parents[2]
PROMPT0 = LOOP / "agents/prompt"
RECON = LOOP / "reconsideration_20260814/agents/prompt"
TRACER = PROMPT0 / "trace_true_geometry_rays"

S3D_SUMMARY = PROMPT0 / "prompt_leak_event_summary.csv"
S3D_POINTS = PROMPT0 / "prompt_leak_interaction_points.csv"
MASS_HOSTS = PROMPT0 / "mass_model_final_prompt_pair_hosts.csv"
PARTNERS = RECON / "annihilation_partner_paths.csv"
PARTNER_SEGMENTS = RECON / "partner_straight_ray_segments.csv"

OUT_CHAIN = HERE / "box_removal_chain_audit.csv"
OUT_PRIMARY = HERE / "box_removal_primary_ray_segments.csv"
OUT_TES = HERE / "box_removal_tes511_ray_segments.csv"
OUT_BOUNDS = HERE / "box_removal_observed_chain_bounds.csv"

GEOMETRIES = {
    "S3d_O8": Path(
        "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
        "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
        "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    ),
    "Mass_model_511": Path(
        "/home/ubuntu/TES_511_Balloon/outputs/geometry/"
        "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_"
        "20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_"
        "megalib_proxy.geo.setup"
    ),
}

WEIGHTS = {
    ("S3d_O8", "gamma"): 0.016921464065444387,
    ("Mass_model_511", "gamma"): 0.01692988541454006,
    ("Mass_model_511", "eplus"): 0.02183924366418699,
}

# 510.999-keV macroscopic total cross sections from the existing MEGAlib /
# Geant4-10.02 response tables.  Used only for an uncollided transmission scale.
MU511 = {"mag": 0.7438, "can": 0.7397019566, "l0": 0.7397019566}

SCENARIOS = {
    "remove_mag_only": {"mag"},
    "remove_50mK_can_only": {"can"},
    "remove_L0_enclosure_only": {"l0"},
    "remove_mag_plus_50mK_can": {"mag", "can"},
    "remove_mag_plus_L0_enclosure": {"mag", "l0"},
    "remove_mag_plus_both_Cu_boxes": {"mag", "can", "l0"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def box_category(volume: str) -> str:
    if volume.startswith("Nb_MagShield_") or volume.startswith("MuMetal_MagShield_"):
        return "mag"
    if volume.startswith("Cu_50mK_StillLike_Can_"):
        return "can"
    if volume.startswith("Cu_SubstrateSupport_"):
        return "l0"
    return "other"


def blocker_category(volume: str, material: str) -> str:
    box = box_category(volume)
    if box != "other":
        return box
    if volume.startswith("ColdPlate_"):
        return "coldplate"
    if volume.startswith("DR_") and material == "Copper":
        return "dr_cu"
    if material == "SilverSinterProxy":
        return "ag"
    if material == "StainlessSteel":
        return "ss"
    if material == "W":
        return "w"
    if material in {"BGO", "CsI", "PlasticScintillator"}:
        return "active"
    if material == "Vacuum":
        return "vacuum"
    if material == "Copper":
        return "other_cu"
    return "other"


def event_lines(path: str, event_id: str) -> list[str]:
    found = False
    lines: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("ID "):
                current = line.split()[1]
                if found and current != event_id:
                    break
                found = current == event_id
            if found:
                lines.append(line.rstrip())
    if not lines:
        raise RuntimeError(f"missing event {event_id}: {path}")
    return lines


def parse_init(lines: list[str]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    line = next(line for line in lines if line.startswith("IA INIT"))
    fields = line.split(";")
    point = tuple(float(fields[i]) for i in (4, 5, 6))
    direction = tuple(float(fields[i]) for i in (16, 17, 18))
    norm = math.sqrt(sum(value * value for value in direction))
    return point, tuple(value / norm for value in direction)


def load_cases() -> list[dict[str, object]]:
    point_rows = read_csv(S3D_POINTS)
    by_s3d: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in point_rows:
        by_s3d[row["event_id"]].append(row)
    cases: list[dict[str, object]] = []
    for row in read_csv(S3D_SUMMARY):
        points = by_s3d[row["event_id"]]
        init = next(item for item in points if item["point_type"] == "INIT")
        pair = next(item for item in points if item["point_type"] == "PAIR")
        cases.append({
            "geometry": "S3d_O8",
            "family": "gamma",
            "event_id": row["event_id"],
            "source_file": init["source_file"],
            "step05_pass": row["step05_pass"],
            "pair_volume": row["pair_volume"],
            "pair_material": pair["material"],
            "annihilation_volume": row["annihilation_volume"],
            "annihilation_material": next(item for item in points if item["point_type"] == "ANNI")["material"],
            "pair_point": tuple(float(pair[key]) for key in ("x_world_cm", "y_world_cm", "z_world_cm")),
            "primary_trace_kind": "uncollided_primary_gamma",
        })
    for row in read_csv(MASS_HOSTS):
        pair_point = None
        if row["primary_first_pair_x_cm"]:
            pair_point = tuple(float(row[key]) for key in (
                "primary_first_pair_x_cm", "primary_first_pair_y_cm", "primary_first_pair_z_cm"
            ))
        cases.append({
            "geometry": "Mass_model_511",
            "family": row["family"],
            "event_id": row["event_id"],
            "source_file": row["source_file"],
            "step05_pass": "True",
            "pair_volume": row["tes_lineage_pair_volume"],
            "pair_material": row["tes_lineage_pair_material"],
            "annihilation_volume": row["tes_lineage_annihilation_volume"],
            "annihilation_material": row["tes_lineage_annihilation_material"],
            "pair_point": pair_point,
            "primary_trace_kind": (
                "charged_eplus_to_BREM_gamma__no_single_straight_primary"
                if row["family"] == "eplus"
                else ("secondary_BREM_pair__primary_trace_not_pair_lineage"
                      if row["event_id"] == "88"
                      else ("primary_COMP_then_pair__straight_after_COMP_invalid"
                            if row["first_primary_key_process"] == "COMP" else "primary_gamma"))
            ),
        })
    for case in cases:
        case["event_weight_cps"] = WEIGHTS[(str(case["geometry"]), str(case["family"]))]
    return cases


def trace_primary(cases: list[dict[str, object]]) -> list[dict[str, str]]:
    all_segments: list[dict[str, str]] = []
    for geometry, setup in GEOMETRIES.items():
        feed: list[str] = []
        for case in cases:
            if case["geometry"] != geometry or case["family"] != "gamma":
                continue
            point, direction = parse_init(event_lines(str(case["source_file"]), str(case["event_id"])))
            case["init_point"] = point
            case["init_direction"] = direction
            ray_id = f"{geometry}__{case['family']}__{case['event_id']}"
            feed.append(" ".join([ray_id, *(f"{x:.12g}" for x in point),
                                  *(f"{x:.12g}" for x in direction), "120", "0.005"]))
        proc = subprocess.run(
            [str(TRACER), str(setup)], input="\n".join(feed) + "\n", text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        fields = None
        for line in proc.stdout.splitlines():
            if line.startswith("ray_id,"):
                fields = next(csv.reader([line]))
            elif line.startswith(geometry) and fields:
                row = dict(zip(fields, next(csv.reader([line]))))
                row = {"geometry": geometry, **row}
                all_segments.append(row)
    return all_segments


def trace_tes_rays(partner_cases: list[dict[str, str]]) -> list[dict[str, str]]:
    all_segments: list[dict[str, str]] = []
    for geometry, setup in GEOMETRIES.items():
        feed: list[str] = []
        for row in partner_cases:
            if row["geometry"] != geometry:
                continue
            ray_id = f"{geometry}__{row['family']}__{row['event_id']}"
            values = [row[key] for key in (
                "annihilation_x_cm", "annihilation_y_cm", "annihilation_z_cm",
                "tes_511_dx", "tes_511_dy", "tes_511_dz",
            )]
            feed.append(" ".join([ray_id, *values, "80", "0.002"]))
        proc = subprocess.run(
            [str(TRACER), str(setup)], input="\n".join(feed) + "\n", text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        fields = None
        for line in proc.stdout.splitlines():
            if line.startswith("ray_id,"):
                fields = next(csv.reader([line]))
            elif line.startswith(geometry) and fields:
                row = dict(zip(fields, next(csv.reader([line]))))
                all_segments.append({"geometry": geometry, **row})
    return all_segments


def next_host(case: dict[str, object], segments: list[dict[str, str]], removed: str) -> str:
    if case["family"] != "gamma" or case["pair_point"] is None:
        return "UNKNOWN__no_single_straight_pair_ray"
    if case["event_id"] == "88":
        return "NOT_APPLICABLE__TES_pair_is_secondary_BREM"
    point = case["init_point"]
    direction = case["init_direction"]
    pair_point = case["pair_point"]
    delta = tuple(pair_point[i] - point[i] for i in range(3))
    t_pair = sum(delta[i] * direction[i] for i in range(3))
    residual = math.sqrt(sum((delta[i] - t_pair * direction[i]) ** 2 for i in range(3)))
    if residual > 1.0e-2:
        return "UNKNOWN__primary_scattered_before_pair"
    candidates = []
    for row in segments:
        if row["ray_id"] != f"{case['geometry']}__{case['family']}__{case['event_id']}":
            continue
        if float(row["t_exit_cm"]) <= t_pair + 1.0e-3 or row["material"] == "Vacuum":
            continue
        if box_category(row["deepest_volume"]) == removed:
            continue
        candidates.append(row)
    if not candidates:
        return "NONE_before_120cm"
    row = min(candidates, key=lambda item: float(item["t_entry_cm"]))
    return f"{row['deepest_volume']}[{row['material']}]@t={float(row['t_entry_cm']):.4f}cm"


def primary_pre_pair_metrics(case: dict[str, object], segments: list[dict[str, str]]) -> dict[str, object]:
    empty: dict[str, object] = {
        "primary_pair_ray_residual_cm": "UNKNOWN",
        "primary_pair_host_ray_chord_cm": "UNKNOWN",
        "primary_pre_pair_mag_chord_cm": "UNKNOWN",
        "primary_pre_pair_can_chord_cm": "UNKNOWN",
        "primary_pre_pair_L0_chord_cm": "UNKNOWN",
        "primary_pre_pair_coldplate_chord_cm": "UNKNOWN",
        "primary_pre_pair_DR_Cu_chord_cm": "UNKNOWN",
        "primary_pre_pair_Ag_chord_cm": "UNKNOWN",
        "primary_pre_pair_SS_chord_cm": "UNKNOWN",
    }
    if case["family"] != "gamma" or case["pair_point"] is None:
        return empty
    point = case["init_point"]
    direction = case["init_direction"]
    pair_point = case["pair_point"]
    delta = tuple(pair_point[i] - point[i] for i in range(3))
    t_pair = sum(delta[i] * direction[i] for i in range(3))
    residual = math.sqrt(sum((delta[i] - t_pair * direction[i]) ** 2 for i in range(3)))
    chords: dict[str, float] = defaultdict(float)
    host_chord = 0.0
    ray_id = f"{case['geometry']}__{case['family']}__{case['event_id']}"
    for row in segments:
        if row["ray_id"] != ray_id:
            continue
        lo, hi = float(row["t_entry_cm"]), float(row["t_exit_cm"])
        overlap = max(0.0, min(hi, t_pair) - max(lo, 0.0))
        if overlap:
            chords[blocker_category(row["deepest_volume"], row["material"])] += overlap
        if lo - 1.0e-3 <= t_pair <= hi + 1.0e-3:
            host_chord = float(row["path_cm"])
    return {
        "primary_pair_ray_residual_cm": residual,
        "primary_pair_host_ray_chord_cm": host_chord,
        "primary_pre_pair_mag_chord_cm": chords["mag"],
        "primary_pre_pair_can_chord_cm": chords["can"],
        "primary_pre_pair_L0_chord_cm": chords["l0"],
        "primary_pre_pair_coldplate_chord_cm": chords["coldplate"],
        "primary_pre_pair_DR_Cu_chord_cm": chords["dr_cu"],
        "primary_pre_pair_Ag_chord_cm": chords["ag"],
        "primary_pre_pair_SS_chord_cm": chords["ss"],
    }


def tes_ray_metrics(case: dict[str, object], segments: list[dict[str, str]]) -> dict[str, object]:
    ray_id = f"{case['geometry']}__{case['family']}__{case['event_id']}"
    rows = [row for row in segments if row["ray_id"] == ray_id]
    first_tes = next((row for row in rows if row["deepest_volume"].startswith("TP_L")), None)
    if first_tes is None:
        limit = float("inf")
    else:
        limit = float(first_tes["t_entry_cm"])
    chords: dict[str, float] = defaultdict(float)
    for row in rows:
        lo, hi = float(row["t_entry_cm"]), float(row["t_exit_cm"])
        if lo >= limit:
            continue
        overlap = min(hi, limit) - lo
        if overlap > 0:
            chords[blocker_category(row["deepest_volume"], row["material"])] += overlap
    return {
        "straight_original_TES511_reaches_TES_pixel": first_tes is not None,
        "straight_original_TES511_first_pixel": first_tes["deepest_volume"] if first_tes else "NONE",
        "TES511_pre_pixel_mag_chord_cm": chords["mag"],
        "TES511_pre_pixel_can_chord_cm": chords["can"],
        "TES511_pre_pixel_L0_chord_cm": chords["l0"],
        "TES511_pre_pixel_coldplate_chord_cm": chords["coldplate"],
        "TES511_pre_pixel_DR_Cu_chord_cm": chords["dr_cu"],
        "TES511_pre_pixel_Ag_chord_cm": chords["ag"],
        "TES511_pre_pixel_SS_chord_cm": chords["ss"],
        "TES511_pre_pixel_other_Cu_chord_cm": chords["other_cu"],
    }


def build_outputs() -> None:
    cases = load_cases()
    partner_case_order = read_csv(PARTNERS)
    partners = {(row["geometry"], row["family"], row["event_id"]): row for row in partner_case_order}
    partner_rows = read_csv(PARTNER_SEGMENTS)
    partner_ray = {
        (row["geometry"], row["family"], row["event_id"]): f"r{i}"
        for i, row in enumerate(partner_case_order)
    }
    primary_segments = trace_primary(cases)
    write_csv(OUT_PRIMARY, primary_segments)
    tes_segments = trace_tes_rays(partner_case_order)
    write_csv(OUT_TES, tes_segments)

    chain_rows: list[dict[str, object]] = []
    for case in cases:
        key = (str(case["geometry"]), str(case["family"]), str(case["event_id"]))
        partner = partners[key]
        chords: dict[str, float] = defaultdict(float)
        for segment in partner_rows:
            if segment["ray_id"] != partner_ray[key]:
                continue
            chords[blocker_category(segment["deepest_volume"], segment["material"])] += float(segment["path_cm"])
        pair_cat = box_category(str(case["pair_volume"]))
        anni_cat = box_category(str(case["annihilation_volume"]))
        primary_metrics = primary_pre_pair_metrics(case, primary_segments)
        tes_metrics = tes_ray_metrics(case, tes_segments)
        tes_mag = float(tes_metrics["TES511_pre_pixel_mag_chord_cm"])
        tes_can = float(tes_metrics["TES511_pre_pixel_can_chord_cm"])
        tes_l0 = float(tes_metrics["TES511_pre_pixel_L0_chord_cm"])
        row: dict[str, object] = {
            "geometry": case["geometry"], "family": case["family"], "event_id": case["event_id"],
            "step05_pass": case["step05_pass"], "event_weight_cps": case["event_weight_cps"],
            "pair_volume": case["pair_volume"], "pair_material": case["pair_material"], "pair_box_category": pair_cat,
            "annihilation_volume": case["annihilation_volume"], "annihilation_material": case["annihilation_material"],
            "annihilation_box_category": anni_cat,
            "partner_actual_first_process": partner["partner_first_interaction_process"],
            "partner_actual_first_volume": partner["partner_first_interaction_volume"],
            "partner_actual_first_category": blocker_category(partner["partner_first_interaction_volume"], partner["partner_first_interaction_material"]),
            "partner_mag_chord_cm": chords["mag"], "partner_can_chord_cm": chords["can"],
            "partner_L0_chord_cm": chords["l0"], "partner_coldplate_chord_cm": chords["coldplate"],
            "partner_DR_Cu_chord_cm": chords["dr_cu"], "partner_Ag_chord_cm": chords["ag"],
            "partner_SS_chord_cm": chords["ss"], "partner_other_Cu_chord_cm": chords["other_cu"],
            "partner_W_chord_cm": chords["w"], "partner_active_chord_cm": chords["active"],
            "primary_trace_kind": case["primary_trace_kind"],
            **primary_metrics,
            **tes_metrics,
            "TES511_mag_removal_uncollided_multiplier_proxy": math.exp(MU511["mag"] * tes_mag),
            "TES511_can_removal_uncollided_multiplier_proxy": math.exp(MU511["can"] * tes_can),
            "TES511_L0_removal_uncollided_multiplier_proxy": math.exp(MU511["l0"] * tes_l0),
            "TES511_all_boxes_removal_uncollided_multiplier_proxy": math.exp(
                MU511["mag"] * tes_mag + MU511["can"] * tes_can + MU511["l0"] * tes_l0
            ),
            "next_host_if_pair_mag_removed": next_host(case, primary_segments, "mag") if pair_cat == "mag" else "PAIR_HOST_NOT_MAG",
            "next_host_if_pair_can_removed": next_host(case, primary_segments, "can") if pair_cat == "can" else "PAIR_HOST_NOT_CAN",
            "next_host_if_pair_L0_removed": next_host(case, primary_segments, "l0") if pair_cat == "l0" else "PAIR_HOST_NOT_L0",
        }
        for scenario, removed in SCENARIOS.items():
            row[f"baseline_chain_host_tagged_{scenario}"] = pair_cat in removed or anni_cat in removed
        chain_rows.append(row)
    write_csv(OUT_CHAIN, chain_rows)

    bound_rows: list[dict[str, object]] = []
    for geometry, selected_filter in (("S3d_O8", True), ("S3d_O8_all3", False), ("Mass_model_511", False)):
        selected = [row for row in chain_rows if (
            (row["geometry"] == "S3d_O8" and (not selected_filter or row["step05_pass"] == "True"))
            if geometry.startswith("S3d") else row["geometry"] == geometry
        )]
        total = sum(float(row["event_weight_cps"]) for row in selected)
        neff = total * total / sum(float(row["event_weight_cps"]) ** 2 for row in selected)
        for scenario in SCENARIOS:
            tagged = [row for row in selected if row[f"baseline_chain_host_tagged_{scenario}"]]
            tagged_rate = sum(float(row["event_weight_cps"]) for row in tagged)
            bound_rows.append({
                "geometry_denominator": geometry,
                "scenario": scenario,
                "selected_baseline_rows": len(selected),
                "selected_baseline_Neff": neff,
                "baseline_rate_cps": total,
                "host_tagged_rows": len(tagged),
                "host_tagged_rate_cps": tagged_rate,
                "host_tagged_fraction": tagged_rate / total if total else 0.0,
                "ideal_no_migration_residual_cps": total - tagged_rate,
                "lower_bound_on_real_suppression": "NONE__may_be_zero_or_negative",
                "interpretation": "OBSERVED_CHAIN_TAG_CEILING_ONLY__NOT_POPULATION_EFFICIENCY",
            })
    write_csv(OUT_BOUNDS, bound_rows)
    print(f"wrote {len(chain_rows)} chains, {len(primary_segments)} primary segments, {len(bound_rows)} bounds")


if __name__ == "__main__":
    build_outputs()
