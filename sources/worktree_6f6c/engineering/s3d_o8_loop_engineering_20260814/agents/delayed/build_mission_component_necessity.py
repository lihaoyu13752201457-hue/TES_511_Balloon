#!/usr/bin/env python3
"""Fold official S3d-O8 delayed lineage into the retained 20-day mission.

This is post-processing only.  It joins exact family x parent-ZA event lineage
to the mission activity curves, then applies the retained node quadrature and
baseline accidental-live factor.  It launches no transport.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Callable

from analyze_delayed import component_group, material_label, neff


HERE = Path(__file__).resolve().parent
SOURCE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
)
LINEAGE = SOURCE / "outputs/04_common_response/selected_background_w2_lineage.csv"
MISSION = SOURCE / "outputs/06_mission"
GEOMETRY = "S3d_O8"
B_TARGET_CPS = 0.016581812
EXPECTED_ROWS = 420
EXPECTED_STATIC_CPS = 0.05447975222726722
SECONDS_20D = 20.0 * 86400.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    lineage = [
        row for row in read_csv(LINEAGE)
        if row["geometry"] == GEOMETRY and row["stream"] == "delayed"
    ]
    if len(lineage) != EXPECTED_ROWS:
        raise RuntimeError(f"selected delayed row drift: {len(lineage)}")
    if len({(row["family"], int(row["local_event_id"])) for row in lineage}) != len(lineage):
        raise RuntimeError("family/local-event key is not unique")

    events: list[dict[str, Any]] = []
    for row in lineage:
        volume = row["source_volume"]
        events.append(
            {
                "family": row["family"],
                "parent_ZA": int(row["source_parent_ZA"]),
                "volume": volume,
                "component": component_group(volume),
                "material": material_label(volume),
                "weight_cps": float(row["event_weight_cps"]),
            }
        )
    static_total = math.fsum(event["weight_cps"] for event in events)
    if not math.isclose(static_total, EXPECTED_STATIC_CPS, rel_tol=0.0, abs_tol=1e-14):
        raise RuntimeError(f"static delayed rate drift: {static_total}")

    timeline = [
        row for row in read_csv(MISSION / "mission_timeline.csv")
        if row["geometry"] == GEOMETRY
    ]
    if len(timeline) != 81:
        raise RuntimeError(f"mission timeline row drift: {len(timeline)}")
    timeline.sort(key=lambda row: int(row["time_bin_id"]))
    if not math.isclose(
        math.fsum(float(row["trajectory_quadrature_weight_s"]) for row in timeline),
        SECONDS_20D, rel_tol=0.0, abs_tol=1e-9,
    ):
        raise RuntimeError("mission quadrature does not close to 20 days")

    activity_rows = [
        row for row in read_csv(MISSION / "family_parent_activity_by_time.csv")
        if row["geometry"] == GEOMETRY
    ]
    activity_keys = [
        (int(row["time_bin_id"]), row["incident_family"], int(row["source_parent_ZA"]))
        for row in activity_rows
    ]
    if len(activity_keys) != len(set(activity_keys)):
        raise RuntimeError("mission activity composite key is not unique")
    scales = {
        key: float(row["activity_scale_to_constant_environment_day15_inventory"])
        for key, row in zip(activity_keys, activity_rows)
    }
    selected_parent_keys = {(event["family"], event["parent_ZA"]) for event in events}
    missing = {
        (time_id, family, za)
        for time_id in range(81)
        for family, za in selected_parent_keys
        if (time_id, family, za) not in scales
    }
    if missing:
        raise RuntimeError(f"mission activity join misses {len(missing)} cells")

    node_dt = [float(row["trajectory_quadrature_weight_s"]) for row in timeline]
    node_live = [float(row["accidental_live_factor"]) for row in timeline]
    effective_live_exposure = math.fsum(dt * live for dt, live in zip(node_dt, node_live))
    min_live = min(node_live)
    max_live = max(node_live)

    def rates_for(predicate: Callable[[dict[str, Any]], bool]) -> list[float]:
        chosen = [event for event in events if predicate(event)]
        return [
            math.fsum(
                event["weight_cps"]
                * scales[(time_id, event["family"], event["parent_ZA"])]
                for event in chosen
            )
            for time_id in range(81)
        ]

    baseline_rates = rates_for(lambda _: True)
    rate_residuals = [
        abs(rate - float(row["delayed_final_cps_noacc"]))
        for rate, row in zip(baseline_rates, timeline)
    ]
    if max(rate_residuals) > 1e-13:
        raise RuntimeError(f"mission delayed-rate reconstruction drift: {max(rate_residuals)}")

    baseline_counts = math.fsum(
        rate * live * dt
        for rate, live, dt in zip(baseline_rates, node_live, node_dt)
    )
    baseline_noacc_counts = math.fsum(rate * dt for rate, dt in zip(baseline_rates, node_dt))
    prompt_counts = math.fsum(
        float(row["prompt_final_cps_noacc"]) * live * dt
        for row, live, dt in zip(timeline, node_live, node_dt)
    )
    mission_background = float(timeline[-1]["cumulative_background_counts"])
    if not math.isclose(
        baseline_counts + prompt_counts, mission_background,
        rel_tol=0.0, abs_tol=1e-8,
    ):
        raise RuntimeError("prompt + reconstructed delayed counts do not close mission background")

    summary = json.loads((MISSION / "summary.json").read_text(encoding="utf-8"))
    geometry_summary = summary["geometries"][GEOMETRY]
    source_counts_20d = float(geometry_summary["source_counts_20d"])
    mission_count_ceiling_z10 = (source_counts_20d / 10.0) ** 2
    if not math.isclose(
        mission_background, float(geometry_summary["background_counts_20d"]),
        rel_tol=0.0, abs_tol=1e-9,
    ):
        raise RuntimeError("timeline/summary background-count mismatch")

    scenarios: list[tuple[str, str, Callable[[dict[str, Any]], bool], str]] = [
        ("baseline_delayed", "baseline", lambda _: True, "all 420 official selected delayed rows"),
        ("MXC", "component", lambda event: event["component"] == "MXC_50mK_plate", "MXC 50 mK plate"),
        ("Nb_inner", "component", lambda event: event["component"] == "Nb_inner_cylinder", "inner Nb cylinder"),
        ("Mu_outer", "component", lambda event: event["component"] == "MuMetal_outer_cylinder", "outer Mu-metal cylinder"),
        ("L0", "component", lambda event: event["component"] == "L0_Cu_disk", "L0 Cu disk"),
        ("all_Copper", "material", lambda event: event["material"] == "Copper", "all selected Copper volumes"),
        (
            "MXC_plus_Nb_inner", "combination",
            lambda event: event["component"] in {"MXC_50mK_plate", "Nb_inner_cylinder"},
            "counterfactual joint removal; not the G-Nb-S1 one-part candidate",
        ),
        (
            "MXC_plus_Nb_plus_Mu_plus_L0", "combination",
            lambda event: event["component"] in {
                "MXC_50mK_plate", "Nb_inner_cylinder",
                "MuMetal_outer_cylinder", "L0_Cu_disk",
            },
            "minimum all-named four-component day-15 central ceiling",
        ),
    ]

    target_counts_baseline_live = B_TARGET_CPS * effective_live_exposure
    bubbles = read_csv(HERE / "delayed_position_bubbles.csv")
    output: list[dict[str, Any]] = []
    for name, scope_type, predicate, definition in scenarios:
        chosen = [event for event in events if predicate(event)]
        rates = rates_for(predicate)
        static_rate = math.fsum(event["weight_cps"] for event in chosen)
        counts = math.fsum(
            rate * live * dt for rate, live, dt in zip(rates, node_live, node_dt)
        )
        noacc_counts = math.fsum(rate * dt for rate, dt in zip(rates, node_dt))
        equivalent_rate = counts / effective_live_exposure
        calendar_noacc_rate = noacc_counts / SECONDS_20D
        day15_rate = rates[60]

        is_baseline = name == "baseline_delayed"
        if is_baseline:
            residual_counts = math.nan
            residual_noacc_counts = math.nan
            residual_equivalent = math.nan
            residual_calendar_noacc_rate = math.nan
            residual_static = math.nan
            static_pass = "NA"
            mission_pass = "NA"
            mission_count_floor_pass = "NA"
            mission_count_live1_pass = "NA"
            feedback_can_rescue = "NA"
        else:
            residual_rates = [base - removed for base, removed in zip(baseline_rates, rates)]
            residual_counts = baseline_counts - counts
            residual_noacc_counts = baseline_noacc_counts - noacc_counts
            residual_equivalent = residual_counts / effective_live_exposure
            residual_calendar_noacc_rate = residual_noacc_counts / SECONDS_20D
            residual_static = static_total - static_rate
            static_pass = int(residual_static <= B_TARGET_CPS)
            mission_pass = int(residual_equivalent <= B_TARGET_CPS)
            # If the candidate only reduces occupancy, L_candidate >= L_baseline.
            # Consequently baseline-live residual counts are an optimistic lower
            # bound, and live=1 residual counts are an upper bound.  Recovered
            # live time cannot rescue a lower-bound count-gate failure.
            mission_count_floor_pass = int(residual_counts <= mission_count_ceiling_z10)
            mission_count_live1_pass = int(residual_noacc_counts <= mission_count_ceiling_z10)
            feedback_can_rescue = 0

        position_rates = [
            float(row["selected_rate_cps_at_position"])
            for row in bubbles
            if predicate(
                {
                    "component": row["component_group"],
                    "material": row["material"],
                }
            )
        ]
        output.append(
            {
                "geometry": GEOMETRY,
                "scope": name,
                "scope_type": scope_type,
                "scope_definition": definition,
                "official_selected_rows": len(chosen),
                "official_selected_positions": len(position_rates),
                "official_selected_position_Neff": neff(position_rates),
                "static_day15_rate_cps": static_rate,
                "mission_day15_node_rate_cps": day15_rate,
                "mission_counts_20d_baseline_live": counts,
                "mission_counts_20d_no_accidental_loss": noacc_counts,
                "mission_rate_equivalent_cps_baseline_live": equivalent_rate,
                "mission_calendar_average_cps_noacc": calendar_noacc_rate,
                "mission_to_static_day15_rate_ratio": (
                    equivalent_rate / static_rate if static_rate > 0.0 else math.nan
                ),
                "fraction_of_baseline_delayed_counts": counts / baseline_counts,
                "residual_static_day15_rate_after_100pct_removal_cps": residual_static,
                "residual_mission_counts_20d_baseline_live": residual_counts,
                "residual_mission_counts_20d_live_equals_1": residual_noacc_counts,
                "residual_mission_rate_equivalent_cps_baseline_live": residual_equivalent,
                "residual_mission_calendar_average_cps_live_equals_1": residual_calendar_noacc_rate,
                "rate_gate_target_cps": B_TARGET_CPS,
                "target_counts_at_baseline_live_exposure": target_counts_baseline_live,
                "static_day15_100pct_removal_passes_gate": static_pass,
                "mission_100pct_removal_passes_rate_equivalent_gate": mission_pass,
                "mission_source_counts_20d": source_counts_20d,
                "mission_background_count_ceiling_for_Z10": mission_count_ceiling_z10,
                "mission_count_ceiling_rate_equivalent_cps_at_baseline_live": (
                    mission_count_ceiling_z10 / effective_live_exposure
                ),
                "residual_count_floor_over_Z10_ceiling": (
                    residual_counts / mission_count_ceiling_z10 if not is_baseline else math.nan
                ),
                "mission_count_gate_passes_at_optimistic_baseline_live_floor": mission_count_floor_pass,
                "mission_count_gate_passes_even_at_live_equals_1": mission_count_live1_pass,
                "occupancy_live_feedback_can_rescue_count_gate_failure": feedback_can_rescue,
                "candidate_residual_count_lower_bound_if_occupancy_only_decreases": residual_counts,
                "candidate_residual_count_upper_bound_if_occupancy_only_decreases": residual_noacc_counts,
                "residual_total_counts_if_baseline_prompt_retained": (
                    residual_counts + prompt_counts if not is_baseline else math.nan
                ),
                "count_gate_passes_if_baseline_prompt_retained": (
                    int(residual_counts + prompt_counts <= mission_count_ceiling_z10)
                    if not is_baseline else "NA"
                ),
                "residual_gate_assumption": (
                    "100pct selected delayed scope removed; all prompt removed; unchanged signal; no host migration"
                    if not is_baseline else "official retained baseline delayed"
                ),
                "baseline_prompt_counts_20d": prompt_counts,
                "baseline_delayed_counts_20d": baseline_counts,
                "baseline_total_background_counts_20d": mission_background,
                "baseline_live_factor_min": min_live,
                "baseline_live_factor_max": max_live,
                "baseline_effective_live_exposure_s": effective_live_exposure,
                "activity_join_boundary": "S3d_O8 x exact family x parent_ZA; volume inherits parent time scale",
            }
        )

    write_csv(HERE / "mission_component_necessity.csv", output)
    print(
        f"PASS: {len(events)} events x 81 nodes; delayed counts={baseline_counts:.12g}; "
        f"prompt+delayed={baseline_counts + prompt_counts:.12g}"
    )


if __name__ == "__main__":
    main()
