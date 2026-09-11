#!/usr/bin/env python3
"""Perfect-removal central ceilings for the magnetic and 50 mK Cu boxes.

Read-only post-processing of the official S3d-O8 selected lineage, mission
timeline, and source-mix screen.  Production/activity is deliberately not
added to observed selected W2; candidate host migration remains UNKNOWN.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
M05 = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
)
LINEAGE = M05 / "outputs/04_common_response/selected_background_w2_lineage.csv"
MISSION = M05 / "outputs/06_mission"
SOURCE_MIX = M05 / "outputs/03_delayed/delayed_source_mix.csv"
OUT_SCENARIOS = HERE / "remove_magnet_copper_boxes_upper_bound.csv"
OUT_VOLUMES = HERE / "remove_magnet_copper_boxes_volume_detail.csv"

GEOMETRY = "S3d_O8"
FORMAL_GATE = 27073.008579

MAGNET = {
    "Nb_MagShield_Inner_Cylinder_2mm",
    "Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
    "MuMetal_MagShield_Outer_Cylinder_2mm",
    "MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm",
}
CAN_A = {
    "Cu_50mK_StillLike_Can_bottom_cap_2mm",
    "Cu_50mK_StillLike_Can_side_wall_below_side_port",
    "Cu_50mK_StillLike_Can_side_wall_above_side_port",
    "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
}
L0_B = {"Cu_SubstrateSupport_SolidDisk_L0_deepest"}

VOLUME_CLASS = {
    **{v: "MAGNET_Nb_inner_plus_Mu_outer_full" for v in MAGNET},
    **{v: "A_50mK_Cu_Can_full" for v in CAN_A},
    **{v: "B_L0_Cu_enclosure" for v in L0_B},
}

SCENARIOS = (
    ("baseline_no_removal", set()),
    ("magnet_full_only", MAGNET),
    ("A_50mK_Cu_Can_only", CAN_A),
    ("B_L0_Cu_enclosure_only", L0_B),
    ("C_A_plus_B_Cu_boxes", CAN_A | L0_B),
    ("magnet_plus_A_Cu_Can", MAGNET | CAN_A),
    ("magnet_plus_B_L0", MAGNET | L0_B),
    ("magnet_plus_C_all_named_boxes", MAGNET | CAN_A | L0_B),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def neff(weights: list[float]) -> float:
    return math.fsum(weights) ** 2 / math.fsum(w * w for w in weights) if weights else 0.0


def event_uid(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row["family"],
        row["local_event_id"],
        row["source_parent_ZA"],
        row["source_volume"],
        row["source_file"],
    )


def main() -> None:
    timeline = [r for r in read_csv(MISSION / "mission_timeline.csv") if r["geometry"] == GEOMETRY]
    timeline.sort(key=lambda r: int(r["time_bin_id"]))
    if len(timeline) != 81:
        raise RuntimeError(f"mission timeline drift: {len(timeline)}")
    dt = {int(r["time_bin_id"]): float(r["trajectory_quadrature_weight_s"]) for r in timeline}
    live = {int(r["time_bin_id"]): float(r["accidental_live_factor"]) for r in timeline}
    scales = {
        (int(r["time_bin_id"]), r["incident_family"], int(r["source_parent_ZA"])):
        float(r["activity_scale_to_constant_environment_day15_inventory"])
        for r in read_csv(MISSION / "family_parent_activity_by_time.csv")
        if r["geometry"] == GEOMETRY
    }

    lineage = [
        r for r in read_csv(LINEAGE)
        if r["geometry"] == GEOMETRY and r["stream"] == "delayed"
    ]
    if len(lineage) != 420:
        raise RuntimeError(f"official delayed lineage drift: {len(lineage)}")

    events: list[dict[str, object]] = []
    for row in lineage:
        family = row["family"]
        parent = int(row["source_parent_ZA"])
        cps = float(row["event_weight_cps"])
        counts = math.fsum(
            cps * scales[(time_id, family, parent)] * dt[time_id] * live[time_id]
            for time_id in range(81)
        )
        events.append(
            {
                **row,
                "static_cps": cps,
                "mission_counts": counts,
            }
        )
    uids = [event_uid(r) for r in events]
    if len(set(uids)) != len(uids):
        raise RuntimeError("official selected row UID is not unique")

    baseline_cps = math.fsum(float(r["static_cps"]) for r in events)
    baseline_delayed = math.fsum(float(r["mission_counts"]) for r in events)
    prompt_counts = math.fsum(
        float(r["prompt_final_cps_noacc"])
        * float(r["trajectory_quadrature_weight_s"])
        * float(r["accidental_live_factor"])
        for r in timeline
    )
    if not math.isclose(baseline_cps, 0.05447975222726722, abs_tol=1e-15):
        raise RuntimeError(f"static delayed cps drift: {baseline_cps}")
    if not math.isclose(baseline_delayed, 88804.86265187593, abs_tol=1e-8):
        raise RuntimeError(f"mission delayed count drift: {baseline_delayed}")
    if not math.isclose(prompt_counts, 55398.97943402516, abs_tol=1e-8):
        raise RuntimeError(f"mission prompt count drift: {prompt_counts}")

    source_mix = [r for r in read_csv(SOURCE_MIX) if r["geometry"] == GEOMETRY]
    mix_keys = [(r["family"], r["source_volume"], int(r["source_parent_ZA"])) for r in source_mix]
    if len(set(mix_keys)) != len(mix_keys):
        raise RuntimeError("source-mix family-volume-parent keys are not unique")
    mix_totals = {
        "full": sum(int(r["full_50000_blocks"]) for r in source_mix),
        "selected": sum(int(r["selected_10000_blocks"]) for r in source_mix),
        "realized": sum(int(r["realized_250000_triggers"]) for r in source_mix),
    }
    if mix_totals != {"full": 400000, "selected": 80000, "realized": 2000000}:
        raise RuntimeError(f"source-mix denominator drift: {mix_totals}")

    scenario_rows: list[dict[str, object]] = []
    for scenario, volumes in SCENARIOS:
        removed = [r for r in events if r["source_volume"] in volumes]
        residual = [r for r in events if r["source_volume"] not in volumes]
        if set(event_uid(r) for r in removed) & set(event_uid(r) for r in residual):
            raise RuntimeError(f"row-set overlap in {scenario}")
        if len(removed) + len(residual) != len(events):
            raise RuntimeError(f"row-set partition failure in {scenario}")

        rem_counts_w = [float(r["mission_counts"]) for r in removed]
        res_counts_w = [float(r["mission_counts"]) for r in residual]
        removed_counts = math.fsum(rem_counts_w)
        residual_counts = math.fsum(res_counts_w)
        removed_cps = math.fsum(float(r["static_cps"]) for r in removed)
        residual_cps = math.fsum(float(r["static_cps"]) for r in residual)
        if not math.isclose(removed_counts + residual_counts, baseline_delayed, abs_tol=1e-8):
            raise RuntimeError(f"mission partition does not close in {scenario}")
        if not math.isclose(removed_cps + residual_cps, baseline_cps, abs_tol=1e-14):
            raise RuntimeError(f"static cps partition does not close in {scenario}")

        by_volume: dict[str, float] = defaultdict(float)
        for row in removed:
            by_volume[str(row["source_volume"])] += float(row["mission_counts"])
        hottest_volume, hottest_counts = (
            max(by_volume.items(), key=lambda item: item[1]) if by_volume else ("NONE", 0.0)
        )
        largest_removed = max(removed, key=lambda r: float(r["mission_counts"]), default=None)
        largest_residual = max(residual, key=lambda r: float(r["mission_counts"]), default=None)

        mix_removed = [r for r in source_mix if r["source_volume"] in volumes]
        mix_full = sum(int(r["full_50000_blocks"]) for r in mix_removed)
        mix_selected = sum(int(r["selected_10000_blocks"]) for r in mix_removed)
        mix_realized = sum(int(r["realized_250000_triggers"]) for r in mix_removed)
        total_counts = prompt_counts + residual_counts

        scenario_rows.append(
            {
                "geometry": GEOMETRY,
                "scenario": scenario,
                "removed_volume_count": len(volumes),
                "removed_volumes": "|".join(sorted(volumes)) or "NONE",
                "official_selected_rows_removed": len(removed),
                "official_removed_static_selected_cps": removed_cps,
                "official_removed_static_cps_fraction": removed_cps / baseline_cps,
                "official_removed_mission_counts": removed_counts,
                "official_removed_mission_fraction": removed_counts / baseline_delayed,
                "official_residual_delayed_static_cps": residual_cps,
                "official_residual_D20_counts": residual_counts,
                "baseline_prompt_P20_counts_unchanged": prompt_counts,
                "optimistic_total_PplusD20_counts": total_counts,
                "formal_baseline_gate_counts": FORMAL_GATE,
                "total_minus_gate_counts": total_counts - FORMAL_GATE,
                "total_over_gate": total_counts / FORMAL_GATE,
                "central_gate_verdict": "PASS" if total_counts <= FORMAL_GATE else "FAIL",
                "removed_event_Neff": neff(rem_counts_w),
                "largest_removed_event_counts": (
                    float(largest_removed["mission_counts"]) if largest_removed else 0.0
                ),
                "largest_removed_event_fraction": (
                    float(largest_removed["mission_counts"]) / removed_counts
                    if largest_removed and removed_counts else 0.0
                ),
                "largest_removed_event": (
                    f"{largest_removed['family']}:{largest_removed['local_event_id']}:"
                    f"{largest_removed['source_volume']}" if largest_removed else "NONE"
                ),
                "hottest_removed_volume": hottest_volume,
                "hottest_removed_volume_counts": hottest_counts,
                "hottest_removed_volume_fraction": hottest_counts / removed_counts if removed_counts else 0.0,
                "residual_event_Neff": neff(res_counts_w),
                "largest_residual_event_counts": (
                    float(largest_residual["mission_counts"]) if largest_residual else 0.0
                ),
                "source_mix_family_volume_parent_rows": len(mix_removed),
                "source_mix_full_50000_blocks": mix_full,
                "source_mix_full_fraction_of_8family_denominator": mix_full / mix_totals["full"],
                "source_mix_selected_10000_blocks": mix_selected,
                "source_mix_selected_fraction_of_8family_denominator": (
                    mix_selected / mix_totals["selected"]
                ),
                "source_mix_realized_250000_triggers": mix_realized,
                "source_mix_realized_fraction_of_8family_denominator": (
                    mix_realized / mix_totals["realized"]
                ),
                "accounting": (
                    "PERFECT_DELETE_OBSERVED_SELECTED_ROWS_ONCE__PROMPT_FROZEN__"
                    "NO_PRODUCTION_BQ_ADDITION__NO_REPLACEMENT_OR_HOST_MIGRATION"
                ),
            }
        )

    volume_rows: list[dict[str, object]] = []
    for volume in sorted(VOLUME_CLASS):
        selected = [r for r in events if r["source_volume"] == volume]
        weights = [float(r["mission_counts"]) for r in selected]
        counts = math.fsum(weights)
        cps = math.fsum(float(r["static_cps"]) for r in selected)
        largest = max(selected, key=lambda r: float(r["mission_counts"]), default=None)
        mix = [r for r in source_mix if r["source_volume"] == volume]
        volume_rows.append(
            {
                "geometry": GEOMETRY,
                "scope_class": VOLUME_CLASS[volume],
                "source_volume": volume,
                "official_selected_rows": len(selected),
                "official_static_selected_cps": cps,
                "official_mission_counts": counts,
                "event_Neff": neff(weights),
                "largest_event_counts": float(largest["mission_counts"]) if largest else 0.0,
                "largest_event_fraction": (
                    float(largest["mission_counts"]) / counts if largest and counts else 0.0
                ),
                "largest_event": (
                    f"{largest['family']}:{largest['local_event_id']}:{largest['source_parent_ZA']}"
                    if largest else "NONE_OBSERVED"
                ),
                "source_mix_family_volume_parent_rows": len(mix),
                "source_mix_full_50000_blocks": sum(int(r["full_50000_blocks"]) for r in mix),
                "source_mix_selected_10000_blocks": sum(
                    int(r["selected_10000_blocks"]) for r in mix
                ),
                "source_mix_realized_250000_triggers": sum(
                    int(r["realized_250000_triggers"]) for r in mix
                ),
                "zero_selected_status": (
                    "FINITE_MC_ZERO__NOT_ZERO_TRUE_COUPLING" if not selected else "OBSERVED_SELECTED"
                ),
            }
        )

    write_csv(OUT_SCENARIOS, scenario_rows)
    write_csv(OUT_VOLUMES, volume_rows)
    print(
        f"PASS: 420 unique rows; D20={baseline_delayed:.12f}; "
        f"P20={prompt_counts:.12f}; source_mix_triggers={mix_totals['realized']}"
    )
    for row in scenario_rows:
        print(
            row["scenario"],
            f"removed={float(row['official_removed_mission_counts']):.6f}",
            f"residual={float(row['official_residual_D20_counts']):.6f}",
            f"P+D={float(row['optimistic_total_PplusD20_counts']):.6f}",
        )


if __name__ == "__main__":
    main()
