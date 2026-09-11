#!/usr/bin/env python3
"""Reverse-budget and low-Neff audit for the cold-core Cu->Al hypothesis.

Post-processing only: this script reads the retained S3d-O8 M05 lineage and
mission fold.  It does not launch transport or copy simulation caches.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
WT = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
M05 = WT / (
    "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813"
)
MISSION = M05 / "outputs/06_mission"
LINEAGE = M05 / "outputs/04_common_response/selected_background_w2_lineage.csv"
INVENTORY = M05 / "outputs/02_activation/day15_inventory.csv"
SOURCE_MIX = M05 / "outputs/03_delayed/delayed_source_mix.csv"
GEO = WT / (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
)

GEOMETRY = "S3d_O8"
CANDIDATE_SETUP = (
    "engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/"
    "agents/geometry/candidate_proxy/"
    "S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup"
)
EXPECTED_LINEAGE_ROWS = 420
EXPECTED_DELAYED_COUNTS = 88804.86265187593
EXPECTED_TOTAL_COUNTS = 144203.8420859011
CANDIDATE_SIGNAL_TRIALS = 37194
BASELINE_SIGNAL_SELECTED = 27855
CANDIDATE_SIGNAL_SELECTED = 27993
CANDIDATE_SIGNAL_S20 = 1653.53937791
CANDIDATE_SIGNAL_GATE = 27341.9247429
GARWOOD_ZERO_UPPER95 = -math.log(0.05)
# Conservative, explicitly named beta+/EC-capable screening subset.  This is
# not an exhaustive decay-branch parser; candidate decay transport must use the
# full positive ground-state inventory rather than only this list.
POSITRON_SCREEN_ZA = {
    6010, 6011, 7013, 8015, 9017, 9018, 10019,
    11021, 11022, 12022, 12023, 13024, 13025, 14027,
}

ELEMENTS = (
    "n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
    "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn "
    "Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W "
    "Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf "
    "Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def f(value: str | None) -> float:
    return float(value) if value not in (None, "") else 0.0


def neff(values: Iterable[float]) -> float:
    vals = list(values)
    total = math.fsum(vals)
    squares = math.fsum(x * x for x in vals)
    return total * total / squares if squares else 0.0


def isotope_label(za: int) -> str:
    z, a = divmod(za, 1000)
    return f"{ELEMENTS[z] if z < len(ELEMENTS) else f'Z{z}'}-{a}"


def geometry_materials() -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(r"([^\s.]+)\.Material\s+(\S+)")
    for line in GEO.read_text(encoding="utf-8").splitlines():
        match = pattern.fullmatch(line.strip())
        if match:
            result[match.group(1)] = match.group(2)
    return result


def main() -> None:
    materials = geometry_materials()
    candidate_copper_volumes = {
        volume for volume, material in materials.items()
        if material == "Copper" and (
            volume.startswith("Cu_SubstrateSupport_")
            or volume.startswith("Cu_ColdFinger_")
            or volume.startswith("Cu_MXC_Clamp_")
            or volume.startswith("Cu_50mK_StillLike_Can_")
            or volume in {
                "ColdPlate_MXC_50mK_SD_anchor", "ColdPlate_CP_100mK_intercept",
                "ColdPlate_Still_0p7K", "ColdPlate_4K", "DR_MixingChamber_Cu",
                "DR_Still_Pot_Cu", "DR_4K_Condenser_Cu",
            }
        )
    }
    if len(candidate_copper_volumes) != 48:
        raise RuntimeError(f"candidate passive-Copper scope drift: {len(candidate_copper_volumes)}")
    timeline = [
        row for row in read_csv(MISSION / "mission_timeline.csv")
        if row["geometry"] == GEOMETRY
    ]
    timeline.sort(key=lambda row: int(row["time_bin_id"]))
    if len(timeline) != 81:
        raise RuntimeError(f"timeline drift: {len(timeline)}")
    dt = [f(row["trajectory_quadrature_weight_s"]) for row in timeline]
    live = [f(row["accidental_live_factor"]) for row in timeline]

    activity_rows = [
        row for row in read_csv(MISSION / "family_parent_activity_by_time.csv")
        if row["geometry"] == GEOMETRY
    ]
    scales = {
        (int(row["time_bin_id"]), row["incident_family"], int(row["source_parent_ZA"])):
        f(row["activity_scale_to_constant_environment_day15_inventory"])
        for row in activity_rows
    }

    lineage = [
        row for row in read_csv(LINEAGE)
        if row["geometry"] == GEOMETRY and row["stream"] == "delayed"
    ]
    if len(lineage) != EXPECTED_LINEAGE_ROWS:
        raise RuntimeError(f"lineage drift: {len(lineage)}")

    events: list[dict[str, Any]] = []
    for row in lineage:
        family = row["family"]
        parent = int(row["source_parent_ZA"])
        weight = f(row["event_weight_cps"])
        counts = math.fsum(
            weight * scales[(time_id, family, parent)] * dt[time_id] * live[time_id]
            for time_id in range(81)
        )
        events.append(
            {
                "family": family,
                "parent": parent,
                "volume": row["source_volume"],
                "material": materials.get(row["source_volume"], "UNKNOWN"),
                "event_id": int(row["local_event_id"]),
                "static_weight_cps": weight,
                "mission_counts": counts,
            }
        )

    delayed_counts = math.fsum(event["mission_counts"] for event in events)
    prompt_counts = math.fsum(
        f(row["prompt_final_cps_noacc"]) * l * q
        for row, l, q in zip(timeline, live, dt)
    )
    total_counts = delayed_counts + prompt_counts
    if not math.isclose(delayed_counts, EXPECTED_DELAYED_COUNTS, abs_tol=1e-8):
        raise RuntimeError(f"delayed count drift: {delayed_counts}")
    if not math.isclose(total_counts, EXPECTED_TOTAL_COUNTS, abs_tol=1e-8):
        raise RuntimeError(f"total count drift: {total_counts}")

    summary = json.loads((MISSION / "summary.json").read_text(encoding="utf-8"))
    source_counts = f(str(summary["geometries"][GEOMETRY]["source_counts_20d"]))
    count_gate = (source_counts / 10.0) ** 2

    def selected(predicate: Any) -> list[dict[str, Any]]:
        return [event for event in events if predicate(event)]

    exact_copper = selected(lambda event: event["material"] == "Copper")
    copper_like = selected(lambda event: event["material"] in {"Copper", "CuNi"})
    nbmu = selected(lambda event: event["material"] in {"Nb", "MuMetal"})
    fixed_other = selected(
        lambda event: event["material"] not in {"Copper", "Nb", "MuMetal"}
    )
    copper_counts = math.fsum(event["mission_counts"] for event in exact_copper)
    copper_like_counts = math.fsum(event["mission_counts"] for event in copper_like)
    nbmu_counts = math.fsum(event["mission_counts"] for event in nbmu)
    fixed_other_counts = math.fsum(event["mission_counts"] for event in fixed_other)
    selected_copper_volumes = {event["volume"] for event in exact_copper}
    if not selected_copper_volumes <= candidate_copper_volumes:
        raise RuntimeError(
            "selected Copper source volume lies outside the 48-volume candidate scope: "
            f"{sorted(selected_copper_volumes - candidate_copper_volumes)}"
        )
    if not math.isclose(
        prompt_counts + copper_counts + nbmu_counts + fixed_other_counts,
        total_counts, abs_tol=1e-8,
    ):
        raise RuntimeError("reverse-budget material partition does not close")

    # Time-correlated weight concentration is diagnostic only; the mission
    # authority explicitly does not provide a cumulative joint MC interval.
    stat_groups = [
        ("baseline_delayed", events),
        ("exact_geometry_material_Copper", exact_copper),
        ("audit_Copper_like_including_one_CuNi_row", copper_like),
        ("residual_after_exact_Copper_removal", selected(lambda e: e["material"] != "Copper")),
        ("all_Nb_plus_MuMetal", nbmu),
        ("fixed_other_including_CuNi_and_Ag", fixed_other),
    ]
    stat_rows: list[dict[str, Any]] = []
    for name, group in stat_groups:
        counts = [event["mission_counts"] for event in group]
        total = math.fsum(counts)
        concentration_scale = math.sqrt(math.fsum(value * value for value in counts))
        stat_rows.append(
            {
                "geometry": GEOMETRY,
                "scope": name,
                "selected_event_rows": len(group),
                "mission_counts_20d_baseline_live": total,
                "event_Neff_mission_integrated": neff(counts),
                "sqrt_sum_event_count_weight_squared_diagnostic": concentration_scale,
                "relative_weight_concentration_scale": concentration_scale / total if total else math.nan,
                "largest_single_event_counts": max(counts, default=0.0),
                "count_gate": count_gate,
                "scope_minus_count_gate": total - count_gate,
                "scope_minus_gate_over_weight_scale": (
                    (total - count_gate) / concentration_scale if concentration_scale else math.nan
                ),
                "uncertainty_status": (
                    "WEIGHT_CONCENTRATION_ONLY__NOT_A_FORMAL_CUMULATIVE_MC_INTERVAL"
                ),
            }
        )
    write_csv(HERE / "statistical_reconsideration.csv", stat_rows)

    # The exact candidate replaces geometry-material Copper.  CuNi is retained,
    # so it belongs to the fixed-other term.  The boundary credits no reduction
    # of new Al activity or other host migration: these enter as Delta_unknown.
    boundary_rows: list[dict[str, Any]] = []
    for signal_retention in (1.0, 0.95):
        candidate_gate = count_gate * signal_retention * signal_retention
        required_reduction = total_counts - candidate_gate
        for prompt_step in range(21):
            s_prompt = prompt_step / 20.0
            for nbmu_step in range(21):
                s_nbmu = nbmu_step / 20.0
                min_s_cu = (
                    required_reduction
                    - prompt_counts * s_prompt
                    - nbmu_counts * s_nbmu
                ) / copper_counts
                residual_if_full_cu = (
                    prompt_counts * (1.0 - s_prompt)
                    + nbmu_counts * (1.0 - s_nbmu)
                    + fixed_other_counts
                )
                boundary_rows.append(
                    {
                        "geometry": GEOMETRY,
                        "signal_count_retention": signal_retention,
                        "prompt_suppression": s_prompt,
                        "NbMu_effective_selected_term_suppression": s_nbmu,
                        "minimum_incumbent_Cu_selected_term_suppression_zero_new_hosts": min_s_cu,
                        "zero_unknown_term_feasible_with_0_to_1_Cu_suppression": int(min_s_cu <= 1.0),
                        "residual_counts_if_incumbent_Cu_term_suppression_is_1": residual_if_full_cu,
                        "headroom_for_Al_activation_and_host_migration_counts_at_full_Cu_suppression": (
                            candidate_gate - residual_if_full_cu
                        ),
                        "candidate_mission_count_gate": candidate_gate,
                        "baseline_signal_mission_count_gate": count_gate,
                        "model_equation": (
                            "P*(1-sP)+Cu*(1-sCu)+NbMu*(1-sNM)+Other+Delta_unknown"
                            "<=Bmax_baseline*signal_retention^2"
                        ),
                        "boundary_status": (
                            "CENTRAL_BASELINE_LIVE_LOWER_BOUND__AL_AND_MIGRATION_NOT_CREDITED"
                        ),
                    }
                )
    write_csv(HERE / "joint_feasible_boundary.csv", boundary_rows)

    anchors = [
        (1.000, 0.000), (1.000, 0.100), (1.000, 0.200), (1.000, 0.250),
        (0.995, 0.200), (0.995, 0.250), (0.990, 0.200), (0.990, 0.250),
        (0.980, 0.250), (0.950, 0.250),
    ]
    anchor_rows: list[dict[str, Any]] = []
    for signal_retention in (1.0, 0.95):
        candidate_gate = count_gate * signal_retention * signal_retention
        required_reduction = total_counts - candidate_gate
        for s_cu, s_nbmu in anchors:
            min_s_prompt = (
                required_reduction - copper_counts * s_cu - nbmu_counts * s_nbmu
            ) / prompt_counts
            residual_at_full_prompt = (
                copper_counts * (1.0 - s_cu)
                + nbmu_counts * (1.0 - s_nbmu)
                + fixed_other_counts
            )
            anchor_rows.append(
                {
                    "signal_count_retention": signal_retention,
                    "incumbent_Cu_selected_term_suppression": s_cu,
                    "NbMu_effective_selected_term_suppression": s_nbmu,
                    "minimum_prompt_suppression_zero_unknown": min_s_prompt,
                    "headroom_for_Al_and_migration_counts_if_prompt_suppression_is_1": (
                        candidate_gate - residual_at_full_prompt
                    ),
                    "feasible_zero_unknown": int(min_s_prompt <= 1.0),
                    "prompt_counts_baseline": prompt_counts,
                    "exact_Copper_counts_baseline": copper_counts,
                    "NbMu_counts_baseline": nbmu_counts,
                    "fixed_other_counts": fixed_other_counts,
                    "candidate_mission_count_gate": candidate_gate,
                }
            )
    write_csv(HERE / "joint_feasible_anchor_points.csv", anchor_rows)

    tc_prompt = 0.80
    tc_cu = 0.95
    tc_nbmu = 0.75
    candidate_signal_retention = CANDIDATE_SIGNAL_SELECTED / BASELINE_SIGNAL_SELECTED
    if not math.isclose(
        candidate_signal_retention, 1.00495422725, rel_tol=0.0, abs_tol=5e-12
    ):
        raise RuntimeError("candidate focused-signal retention drift")
    if not math.isclose(
        (CANDIDATE_SIGNAL_S20 / 10.0) ** 2,
        CANDIDATE_SIGNAL_GATE,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise RuntimeError("candidate focused-signal gate drift")
    effective_live_exposure = math.fsum(q * l for q, l in zip(dt, live))
    tc_rows: list[dict[str, Any]] = []
    for (
        budget_scope, cu_term, other_term, signal_retention, candidate_gate,
        signal_evidence, signal_trials, baseline_selected, candidate_selected,
        candidate_s20,
    ) in (
        (
            "official_Copper_like_bucket__signal95_sensitivity",
            copper_like_counts,
            total_counts - prompt_counts - copper_like_counts - nbmu_counts,
            0.95,
            count_gate * 0.95 * 0.95,
            "ASSUMED_95_PERCENT_SIGNAL_RETENTION_SENSITIVITY",
            "", "", "", "",
        ),
        (
            "exact_48_volume_geometry_Copper_scope__signal95_sensitivity",
            copper_counts,
            fixed_other_counts,
            0.95,
            count_gate * 0.95 * 0.95,
            "ASSUMED_95_PERCENT_SIGNAL_RETENTION_SENSITIVITY",
            "", "", "", "",
        ),
        (
            "candidate_own_focused_signal__exact_48_volume_scope",
            copper_counts,
            fixed_other_counts,
            candidate_signal_retention,
            CANDIDATE_SIGNAL_GATE,
            "MEASURED_FOCUSED_511_SIGNAL_ONLY__BACKGROUND_SUPPRESSIONS_UNMEASURED",
            CANDIDATE_SIGNAL_TRIALS,
            BASELINE_SIGNAL_SELECTED,
            CANDIDATE_SIGNAL_SELECTED,
            CANDIDATE_SIGNAL_S20,
        ),
    ):
        residual = (
            prompt_counts * (1.0 - tc_prompt)
            + cu_term * (1.0 - tc_cu)
            + nbmu_counts * (1.0 - tc_nbmu)
            + other_term
        )
        required_cu = (
            total_counts - candidate_gate - prompt_counts * tc_prompt - nbmu_counts * tc_nbmu
        ) / cu_term
        max_new_material = candidate_gate - (
            prompt_counts * (1.0 - tc_prompt)
            + nbmu_counts * (1.0 - tc_nbmu)
            + other_term
        )
        incumbent_cu_or_replacement_allowance = cu_term * (1.0 - tc_cu)
        tc_rows.append(
            {
                "budget_scope": budget_scope,
                "signal_count_retention": signal_retention,
                "signal_evidence": signal_evidence,
                "focused_signal_trials": signal_trials,
                "baseline_signal_selected": baseline_selected,
                "candidate_signal_selected": candidate_selected,
                "candidate_signal_S20": candidate_s20,
                "prompt_suppression_assumed": tc_prompt,
                "Cu_net_selected_term_suppression_assumed": tc_cu,
                "NbMu_effective_selected_term_suppression_assumed": tc_nbmu,
                "candidate_count_gate": candidate_gate,
                "predicted_residual_counts": residual,
                "central_margin_counts": candidate_gate - residual,
                "minimum_Cu_net_suppression_at_other_assumptions": required_cu,
                "maximum_new_Al_plus_remaining_Cu_counts_if_Cu_atoms_removed": max_new_material,
                "maximum_new_material_counts_as_fraction_of_Cu_baseline": max_new_material / cu_term,
                "net95_replacement_plus_remaining_Cu_allowance_counts": incumbent_cu_or_replacement_allowance,
                "net95_replacement_plus_remaining_Cu_allowance_rate_equivalent_cps": (
                    incumbent_cu_or_replacement_allowance / effective_live_exposure
                ),
                "implied_rate_equivalent_cps_per_Bq_if_candidate_Al_activity_is_100_Bq": (
                    incumbent_cu_or_replacement_allowance / effective_live_exposure / 100.0
                ),
                "evidence_status": (
                    "SIGNAL_MEASURED__BACKGROUND_SUPPRESSIONS_ARITHMETIC_ONLY"
                    if signal_trials else
                    "ARITHMETIC_POINT_ONLY__ALL_SUPPRESSIONS_UNMEASURED"
                ),
            }
        )
    write_csv(HERE / "TC_AF1_budget_audit.csv", tc_rows)

    by_volume: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": 0, "static_cps": 0.0, "mission_counts": 0.0}
    )
    for event in exact_copper:
        item = by_volume[event["volume"]]
        item["rows"] += 1
        item["static_cps"] += event["static_weight_cps"]
        item["mission_counts"] += event["mission_counts"]
    volume_rows = [
        {
            "source_volume": volume,
            "geometry_material": "Copper",
            "selected_event_rows": values["rows"],
            "static_day15_selected_rate_cps": values["static_cps"],
            "mission_counts_20d_baseline_live": values["mission_counts"],
            "candidate_scope": "same-geometry non-readout structural/cold Copper replacement",
        }
        for volume, values in sorted(
            by_volume.items(), key=lambda item: -item[1]["mission_counts"]
        )
    ]
    write_csv(HERE / "cold_core_Copper_selected_scope.csv", volume_rows)

    candidate_inventory: dict[str, dict[str, float]] = {
        volume: {"production": 0.0, "activity": 0.0, "sum_RP": 0.0}
        for volume in candidate_copper_volumes
    }
    for row in read_csv(INVENTORY):
        if (
            row["geometry"] == GEOMETRY
            and row["source_volume"] in candidate_copper_volumes
            and row["source_disposition"] == "transported_ground_state"
        ):
            item = candidate_inventory[row["source_volume"]]
            item["production"] += f(row["production_rate_s-1"])
            item["activity"] += f(row["day15_activity_Bq"])
            item["sum_RP"] += f(row["sum_RP"])
    write_csv(
        HERE / "cold_core_Copper_inventory_scope.csv",
        [
            {
                "source_volume": volume,
                "geometry_material": "Copper",
                "production_rate_s-1": values["production"],
                "day15_activity_Bq": values["activity"],
                "sum_RP": values["sum_RP"],
                "candidate_scope": "48 passive cold-core Copper volumes",
            }
            for volume, values in sorted(
                candidate_inventory.items(), key=lambda item: -item[1]["activity"]
            )
        ],
    )

    # Current elemental-Al inventory is a risk screen, not a transferable
    # coupling measurement: all retained Al volumes are at different positions.
    mix = {
        (row["family"], row["source_volume"], int(row["source_parent_ZA"])):
        int(row["realized_250000_triggers"])
        for row in read_csv(SOURCE_MIX)
        if row["geometry"] == GEOMETRY
    }
    al_family: dict[str, dict[str, float]] = defaultdict(
        lambda: {"production": 0.0, "activity": 0.0, "triggers": 0.0}
    )
    al_parent: dict[tuple[str, int], dict[str, float]] = defaultdict(
        lambda: {"production": 0.0, "activity": 0.0, "triggers": 0.0}
    )
    al_inventory_keys: dict[tuple[str, str, int], dict[str, float]] = defaultdict(
        lambda: {"production": 0.0, "activity": 0.0}
    )
    al_holdout_activity = 0.0
    for row in read_csv(INVENTORY):
        if row["geometry"] != GEOMETRY or materials.get(row["source_volume"]) != "Aluminium":
            continue
        if row["source_disposition"] != "transported_ground_state":
            al_holdout_activity += f(row["day15_activity_Bq"])
            continue
        family = row["incident_family"]
        parent = int(row["source_parent_ZA"])
        key = (family, row["source_volume"], parent)
        al_inventory_keys[key]["production"] += f(row["production_rate_s-1"])
        al_inventory_keys[key]["activity"] += f(row["day15_activity_Bq"])
    for (family, volume, parent), key_values in al_inventory_keys.items():
        production = key_values["production"]
        activity = key_values["activity"]
        triggers = mix.get((family, volume, parent), 0)
        al_family[family]["production"] += production
        al_family[family]["activity"] += activity
        al_family[family]["triggers"] += triggers
        al_parent[(family, parent)]["production"] += production
        al_parent[(family, parent)]["activity"] += activity
        al_parent[(family, parent)]["triggers"] += triggers

    al_selected_rows = sum(
        1 for event in events if event["material"] == "Aluminium"
    )
    al_family_rows: list[dict[str, Any]] = []
    for family, values in sorted(al_family.items()):
        upper = (
            GARWOOD_ZERO_UPPER95 * values["activity"] / values["triggers"]
            if values["triggers"] > 0 and al_selected_rows == 0 else math.nan
        )
        al_family_rows.append(
            {
                "family": family,
                "current_elemental_Al_production_rate_s-1": values["production"],
                "current_elemental_Al_day15_activity_Bq": values["activity"],
                "current_elemental_Al_realized_decay_triggers": int(values["triggers"]),
                "current_elemental_Al_selected_W2_rows_all_families": al_selected_rows,
                "family_zero_event_95_upper_selected_rate_cps_diagnostic": upper,
                "transfer_status": "NOT_TRANSFERABLE_TO_NEAR_TES_REPLACEMENT_POSITIONS",
            }
        )
    write_csv(HERE / "current_elemental_Al_family_screen.csv", al_family_rows)

    al_parent_rows = [
        {
            "family": family,
            "parent_ZA": parent,
            "isotope": isotope_label(parent),
            "current_elemental_Al_production_rate_s-1": values["production"],
            "current_elemental_Al_day15_activity_Bq": values["activity"],
            "realized_decay_triggers": int(values["triggers"]),
            "candidate_near_TES_coupling": "UNKNOWN__REQUIRES_EXACT_POSITION_DECAY",
        }
        for (family, parent), values in sorted(
            al_parent.items(), key=lambda item: -item[1]["activity"]
        )
        if values["activity"] > 0.0
    ]
    write_csv(HERE / "current_elemental_Al_parent_inventory.csv", al_parent_rows)
    positron_rows: list[dict[str, Any]] = []
    for parent in sorted(POSITRON_SCREEN_ZA):
        matching = [
            (family, values) for (family, za), values in al_parent.items()
            if za == parent
        ]
        production = math.fsum(values["production"] for _, values in matching)
        activity = math.fsum(values["activity"] for _, values in matching)
        triggers = int(math.fsum(values["triggers"] for _, values in matching))
        if activity <= 0.0:
            continue
        positron_rows.append(
            {
                "parent_ZA": parent,
                "isotope": isotope_label(parent),
                "current_elemental_Al_production_rate_s-1": production,
                "current_elemental_Al_day15_activity_Bq": activity,
                "realized_decay_triggers": triggers,
                "classification": "NAMED_BETA_PLUS_OR_EC_CAPABLE_SCREEN_SUBSET",
                "candidate_requirement": "FULL_DECAY_BRANCH_AND_EXACT_POSITION_TRANSPORT",
            }
        )
    write_csv(HERE / "current_elemental_Al_positron_parent_screen.csv", positron_rows)

    write_csv(
        HERE / "suppression_variable_definitions.csv",
        [
            {
                "symbol": "s_prompt",
                "strict_definition": "1 - candidate prompt selected mission counts / baseline prompt selected mission counts",
                "applicability_boundary": "same geometry-specific prompt family normalization and mission live fold",
            },
            {
                "symbol": "s_Cu_old",
                "strict_definition": "1 - candidate counts from incumbent 48-scope Cu parent inventory / baseline exact-Copper counts",
                "applicability_boundary": "new Al/BPE/BGO parents and host migration are not credited here; they enter Delta_new",
            },
            {
                "symbol": "s_NbMu_eff",
                "strict_definition": "1 - (candidate activity/base activity)*(candidate W2_per_Bq/base W2_per_Bq)",
                "applicability_boundary": "equals pure coupling suppression only if candidate/base activity ratio is exactly one; report both factors",
            },
            {
                "symbol": "Delta_new",
                "strict_definition": "candidate mission counts from replacement Al, added BPE/BGO, and all source-host migration terms",
                "applicability_boundary": "nonnegative in the reverse-budget screen; must come from candidate-own exact-position decay",
            },
            {
                "symbol": "r_signal",
                "strict_definition": "candidate S20 / baseline S20",
                "applicability_boundary": "screen gate is baseline_B20max*r_signal^2; promotion uses candidate-own (S20/10)^2",
            },
        ],
    )

    write_csv(
        HERE / "Al_material_option_comparison.csv",
        [
            {
                "option": "existing_elemental_Aluminium",
                "role": "PREFERRED_FOCUSED_TRANSPORT_CANDIDATE",
                "material_card_status": "EXISTS__ELEMENTAL_AL__rho_2p7_g_cm3",
                "candidate_volume_scope": "48 explicit non-readout cold-core passive Copper volumes",
                "same_shape_candidate_mass_kg": 6.11221016,
                "baseline_scope_Copper_mass_kg": 20.26989993,
                "released_mass_kg": 14.15768977,
                "activation_status": "UNKNOWN_AT_CANDIDATE_NEAR_TES_POSITIONS",
                "required_test": "focused n|p|alpha BUILDUP plus all-parent exact-position decay",
                "decision": "KEEP_FOR_FALSIFICATION_ONLY",
            },
            {
                "option": "Al_6061",
                "role": "COMPOSITION_EXPLICIT_COMPARATOR_ONLY",
                "material_card_status": "NO_VALIDATED_EXACT_ALLOY_CARD_IN_CANDIDATE_PACKAGE",
                "candidate_volume_scope": "same 48-volume geometry only if exact Mg|Si|Cu|Cr|Fe alloy card is supplied",
                "same_shape_candidate_mass_kg": "UNKNOWN_UNTIL_CARD",
                "baseline_scope_Copper_mass_kg": 20.26989993,
                "released_mass_kg": "UNKNOWN_UNTIL_CARD",
                "activation_status": "UNKNOWN__IMPURITY_PARENTS_NOT_ALLOWED_TO_BE_ZERO_IMPUTED",
                "required_test": "same matched BUILDUP and exact-position decay as elemental Al",
                "decision": "KILL_AS_NAMED_CANDIDATE_UNLESS_EXACT_ALLOY_CARD_EXISTS",
            },
        ],
    )

    test_rows = [
        {
            "test_id": "B0",
            "stage": "BUILDUP reuse",
            "geometry_variant": "official S3d_O8 baseline",
            "families": "n|p|alpha",
            "sampling": "retained corrected spectra; exact geometry×family TT denominators",
            "observable": "Cu/Al/Nb/Mu parent production and source positions",
            "minimum_gate": "reference only; no new transport",
            "direct_falsifier": "normalization or family-parent key fails closure",
        },
        {
            "test_id": "B1",
            "stage": "focused BUILDUP",
            "geometry_variant": "all scoped Copper volumes -> elemental Aluminium; no shield reallocation",
            "families": "n|p|alpha",
            "sampling": "matched source histories; stratify n in log-E and p/alpha 1-1000 MeV; retain equal-mu/azimuth denominators",
            "observable": "new Al parents; residual Cu trace; Nb/Mu production",
            "minimum_gate": "s_Cu_prod>=0.99 and no unsupported parent/state collapse",
            "direct_falsifier": "new Al inventory cannot leave >=1000-count mission allowance at any feasible prompt/NbMu point",
        },
        {
            "test_id": "B2",
            "stage": "focused BUILDUP",
            "geometry_variant": "all scoped Copper volumes -> exact 6061 alloy card; no shield reallocation",
            "families": "n|p|alpha",
            "sampling": "same histories and strata as B1",
            "observable": "Al/Mg/Si/Cu/Cr/Fe alloy-parent inventory versus B1",
            "minimum_gate": "one-sided new-parent mission allowance no worse than B1, or reject 6061 physics option",
            "direct_falsifier": "alloy impurities add a parent contribution whose lower bound consumes the feasible headroom",
        },
        {
            "test_id": "B3",
            "stage": "focused BUILDUP candidate",
            "geometry_variant": (
                "single AF1-48 unified proxy: elemental Al 48-volume replacement; extra 12 "
                "above-4K/manifold/remote-flex Copper volumes retained; Nb/Mu sleeve+cap "
                "2->0.5 mm; 5 mm inner BPE; existing top-BGO channel extended inward"
            ),
            "families": "n|p|alpha",
            "sampling": "matched to B1/B2; denominator-complete direction bins; no source-family pooling",
            "observable": "new Al/BPE/BGO parents and Nb/Mu production; prompt handled by paired gamma test",
            "minimum_gate": "joint lower-confidence suppression point reaches candidate-own signal gate; no >10% single-event path",
            "direct_falsifier": "new Al/BPE/BGO products or Nb/Mu response consume the 1543-count central margin",
        },
        {
            "test_id": "D1",
            "stage": "exact-position decay",
            "geometry_variant": "B1 and B2 inventories at their own source positions",
            "families": "n|p|alpha production strata kept separate",
            "sampling": "all positive new Al/alloy ground-state parents; adaptive triggers per family×parent×volume",
            "observable": "new-material 20-day W2 counts and W2/Bq; single-event weights explicit",
            "minimum_gate": "aggregate one-sided upper leaves >=1000 counts headroom; every >10% path Neff>=30",
            "direct_falsifier": "Al/alloy activation plus migration exceeds available headroom",
        },
        {
            "test_id": "D2",
            "stage": "exact-position decay",
            "geometry_variant": "B3 Nb and Mu inventories in the AF1-48 unified proxy",
            "families": "n|p|alpha production strata kept separate",
            "sampling": "Y-85|Nb-89|Nb-90|Co-54 plus every positive candidate parent; adaptive exact positions",
            "observable": "separate production Bq and candidate W2/Bq coupling",
            "minimum_gate": "joint (s_Cu,s_NbMu,s_prompt) lower-confidence point lies inside feasible region",
            "direct_falsifier": "Nb/Mu coupling rises after Cu removal or remains below required suppression",
        },
        {
            "test_id": "D3",
            "stage": "focused combined decay confirmation",
            "geometry_variant": "single AF1-48 unified proxy only",
            "families": "n|p|alpha only for this screen",
            "sampling": "candidate-own exact source positions; continue until >10% paths have Neff>=30",
            "observable": "central and one-sided delayed count budget without full eight-family chain",
            "minimum_gate": "central plus pre-registered one-sided conditional bound <= candidate-own (S20/10)^2",
            "direct_falsifier": "gate fails, any single weighted event controls >10%, or new activation/pair host appears",
        },
    ]
    write_csv(HERE / "focused_BUILDUP_exact_decay_test_matrix.csv", test_rows)

    audit = {
        "geometry": GEOMETRY,
        "status": "PASS__POSTPROCESSING_ONLY__NO_TRANSPORT",
        "official_delayed_rows": len(events),
        "candidate_setup": CANDIDATE_SETUP,
        "baseline_effective_live_exposure_s": effective_live_exposure,
        "candidate_focused_signal": {
            "trials": CANDIDATE_SIGNAL_TRIALS,
            "baseline_selected": BASELINE_SIGNAL_SELECTED,
            "candidate_selected": CANDIDATE_SIGNAL_SELECTED,
            "retention": candidate_signal_retention,
            "candidate_S20": CANDIDATE_SIGNAL_S20,
            "candidate_count_gate": CANDIDATE_SIGNAL_GATE,
            "boundary": "SIGNAL_MEASURED__BACKGROUND_SUPPRESSIONS_UNMEASURED",
        },
        "mission_counts": {
            "prompt": prompt_counts,
            "exact_geometry_material_Copper": copper_counts,
            "Nb_plus_MuMetal": nbmu_counts,
            "fixed_other_including_CuNi_and_Ag": fixed_other_counts,
            "total": total_counts,
            "gate": count_gate,
        },
        "candidate_equation": (
            "P*(1-s_prompt)+Cu*(1-s_Cu_old)+"
            "NbMu*(1-s_NbMu_eff)+Other+Delta_new <= Bmax"
        ),
        "current_elemental_Al": {
            "production_rate_s-1": math.fsum(v["production"] for v in al_family.values()),
            "day15_activity_Bq": math.fsum(v["activity"] for v in al_family.values()),
            "realized_decay_triggers": int(math.fsum(v["triggers"] for v in al_family.values())),
            "selected_W2_rows": al_selected_rows,
            "sum_familywise_zero_event_upper95_cps_diagnostic": math.fsum(
                GARWOOD_ZERO_UPPER95 * v["activity"] / v["triggers"]
                for v in al_family.values() if v["triggers"] > 0
            ),
            "named_positron_parent_screen_activity_Bq": math.fsum(
                row["current_elemental_Al_day15_activity_Bq"] for row in positron_rows
            ),
            "excited_or_unresolved_holdout_Bq": al_holdout_activity,
            "transfer_status": "UNKNOWN_NEAR_TES",
        },
        "candidate_passive_Copper_scope": {
            "volume_count": len(candidate_copper_volumes),
            "selected_source_volume_count": len(selected_copper_volumes),
            "all_selected_Copper_source_volumes_inside_scope": True,
            "production_rate_s-1": math.fsum(v["production"] for v in candidate_inventory.values()),
            "day15_activity_Bq": math.fsum(v["activity"] for v in candidate_inventory.values()),
            "sum_RP": math.fsum(v["sum_RP"] for v in candidate_inventory.values()),
        },
    }
    (HERE / "audit_summary.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit["mission_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
