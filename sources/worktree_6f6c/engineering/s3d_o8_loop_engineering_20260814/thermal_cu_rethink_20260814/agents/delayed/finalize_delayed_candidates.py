#!/usr/bin/env python3
"""Build small, read-only-derived screens for BG-J4 and isotope-engineered Cu.

This script reads only the already-produced 420-row delayed lineage and compact
activation tables.  It does not open raw SIM files and does not launch transport.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FLOW = ROOT / "agents/delayed/delayed_production_to_w2_flow.csv"
ORIGINS = ROOT / "agents/delayed/target_production_origin_events.csv"
LINEAGE = HERE / "delayed_annihilation_sibling_events.csv"

P20 = 55398.97943402516
D20 = 88804.86265187593
GATE = 27341.9247429
L_BGO_CM = 4.0
MU_PROMPT_CM = 0.276
MU_511_CM = 0.985
F63_NATURAL = 0.6915
F65_NATURAL = 0.3085


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_bg_j4(lineage: list[dict[str, str]]) -> None:
    trace = [row for row in lineage if row["traceable_sibling"] == "1"]
    trace_counts = math.fsum(float(row["mission_counts_20d_baseline_live"]) for row in trace)
    straight_existing = math.fsum(
        float(row["mission_counts_20d_baseline_live"])
        for row in trace
        if row["ray_reaches_any_BGO_unscattered"] == "1"
    )
    straight_top_filled = math.fsum(
        float(row["mission_counts_20d_baseline_live"])
        for row in trace
        if row["ray_reaches_existing_BGO_or_top_gap_unscattered"] == "1"
    )
    actual_outer = math.fsum(
        float(row["mission_counts_20d_baseline_live"])
        for row in trace
        if row["actual_sibling_gamma_ge50_reaches_current_BGO_or_outer_region"] == "1"
    )

    ep = math.exp(-MU_PROMPT_CM * L_BGO_CM)
    ed = math.exp(-MU_511_CM * L_BGO_CM)
    prompt_residual = P20 * ep
    q_required = (prompt_residual + D20 - GATE) / (D20 * (1.0 - ed))

    def scenario(name: str, q: float, definition: str, status: str) -> dict[str, object]:
        delayed = D20 * ((1.0 - q) + q * ed)
        total = prompt_residual + delayed
        return {
            "scenario": name,
            "conditional_delayed_coupling_q_full_D20": q,
            "q_definition": definition,
            "added_BGO_chord_cm": L_BGO_CM,
            "prompt_attenuation_factor": ep,
            "delayed_511_attenuation_factor_if_eligible": ed,
            "prompt_residual_counts": prompt_residual,
            "delayed_residual_counts": delayed,
            "total_residual_counts": total,
            "exact_gate_counts": GATE,
            "margin_to_gate_counts": GATE - total,
            "status": status,
        }

    rows = [
        scenario(
            "required_conditional_coupling",
            q_required,
            "Algebraic q required for P*exp(-0.276*4)+D*((1-q)+q*exp(-0.985*4))=gate.",
            "REQUIRED__NOT_OBSERVED",
        ),
        scenario(
            "naive_all_delayed_q_equals_1",
            1.0,
            "Assumes every selected delayed sibling reaches the added BGO with >=50 keV; deliberately invalid best case.",
            "ARITHMETIC_PASS__PHYSICS_PREMISE_FALSE",
        ),
        scenario(
            "baseline_unscattered_ray_to_existing_BGO",
            straight_existing / D20,
            "Static unscattered CSG opportunity divided by all D20; not arrival or threshold coupling.",
            "FAIL__GEOMETRY_OPPORTUNITY_ONLY",
        ),
        scenario(
            "baseline_unscattered_ray_existing_BGO_or_top_gap",
            straight_top_filled / D20,
            "Static CSG opportunity after hypothetical same-channel top-gap fill; 2 untraceable rows remain UNKNOWN.",
            "ARITHMETIC_PASS__GEOMETRY_OPPORTUNITY_ONLY",
        ),
        scenario(
            "BG_J4_proxy_added_BGO_chord_ge4cm",
            88652.91172268303 / D20,
            "Candidate CSG: 413/418 traceable rays have >=4 cm added BGO; the other five relief rows are treated unattenuated.",
            "ARITHMETIC_PASS__CANDIDATE_GEOMETRY_OPPORTUNITY_ONLY",
        ),
        scenario(
            "actual_sibling_gamma_ge50_to_current_BGO_or_outer_region",
            actual_outer / D20,
            "Realized baseline sibling branch has a >=50-keV gamma IA point in current BGO/outer region or ESCP.",
            "FAIL__BASELINE_MECHANISM_PROXY_LOW_NEFF",
        ),
    ]

    # Deliberately favorable composite bounds.  Credits are made disjoint even
    # though that is not demonstrated, so failure is conservative for KILL.
    cold_credit = 9078.065543558381
    l0_can_credit = 15995.770216661536
    dr_ag_cuni_credit = 1947.1442425420672
    nbmu_r10_credit = 23188.31928
    composite_before_bpe = max(
        0.0,
        D20 - cold_credit - l0_can_credit - dr_ag_cuni_credit
        - nbmu_r10_credit - actual_outer,
    )
    for bpe in (0.16, 0.30):
        delayed = composite_before_bpe * (1.0 - bpe)
        total = prompt_residual + delayed
        rows.append(
            {
                "scenario": f"overcredited_allowed_composite_BPE_{int(100*bpe)}pct",
                "conditional_delayed_coupling_q_full_D20": "NA",
                "q_definition": (
                    "Perfect, non-overlapping credit for actual outer-eligible branch + legal cold-plate proxy + "
                    "perfect L0/can and DR/Ag/CuNi removal + 84% Nb/Mu coupling reduction, then global BPE."
                ),
                "added_BGO_chord_cm": L_BGO_CM,
                "prompt_attenuation_factor": ep,
                "delayed_511_attenuation_factor_if_eligible": 0.0,
                "prompt_residual_counts": prompt_residual,
                "delayed_residual_counts": delayed,
                "total_residual_counts": total,
                "exact_gate_counts": GATE,
                "margin_to_gate_counts": GATE - total,
                "status": "FAIL__DELIBERATELY_OVER_CREDITED_BOUND",
            }
        )

    required_bpe = 1.0 - (GATE - prompt_residual) / composite_before_bpe
    rows.append(
        {
            "scenario": "overcredited_composite_required_BPE",
            "conditional_delayed_coupling_q_full_D20": "NA",
            "q_definition": f"Required global BPE suppression after every other over-credit: {required_bpe:.12g}.",
            "added_BGO_chord_cm": L_BGO_CM,
            "prompt_attenuation_factor": ep,
            "delayed_511_attenuation_factor_if_eligible": 0.0,
            "prompt_residual_counts": prompt_residual,
            "delayed_residual_counts": GATE - prompt_residual,
            "total_residual_counts": GATE,
            "exact_gate_counts": GATE,
            "margin_to_gate_counts": 0.0,
            "status": "REQUIRES_UNSUPPORTED_GLOBAL_BPE_SUPPRESSION",
        }
    )

    # Isotope-Cu credits overlap several component credits above.  Treating
    # them as disjoint is deliberately more favorable than a valid budget.
    for name, isotope_credit in (
        ("known_channel_100pct_65Cu_net", 3289.203537320158),
        ("perfect_remove_all_strict_63Cu_capture_credit", 13197.886718900863),
    ):
        pre_bpe = max(0.0, composite_before_bpe - isotope_credit)
        delayed = pre_bpe * 0.70
        total = prompt_residual + delayed
        rows.append(
            {
                "scenario": f"overcredited_composite_plus_{name}_plus_BPE30pct",
                "conditional_delayed_coupling_q_full_D20": "NA",
                "q_definition": "Isotope credit is falsely forced disjoint from component credits; this is an impossible-best sensitivity.",
                "added_BGO_chord_cm": L_BGO_CM,
                "prompt_attenuation_factor": ep,
                "delayed_511_attenuation_factor_if_eligible": 0.0,
                "prompt_residual_counts": prompt_residual,
                "delayed_residual_counts": delayed,
                "total_residual_counts": total,
                "exact_gate_counts": GATE,
                "margin_to_gate_counts": GATE - total,
                "status": "FAIL__EVEN_WITH_NONPHYSICAL_DISJOINT_CREDITS",
            }
        )
    write_csv(
        HERE / "bg_j4_conditional_attenuation_proxy.csv",
        rows,
        list(rows[0]),
    )


def build_isotope_screen(
    flow: list[dict[str, str]],
    origins: list[dict[str, str]],
    lineage: list[dict[str, str]],
) -> None:
    mission_by_key: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in lineage:
        mission_by_key[(row["family"], row["source_volume"], row["source_parent_ZA"])] += float(
            row["mission_counts_20d_baseline_live"]
        )

    origin_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in origins:
        origin_by_key[(row["family"], row["source_volume"], row["source_parent_ZA"])].append(row)

    selected_flow: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in flow:
        key = (row["family"], row["source_volume"], row["source_parent_ZA"])
        if (
            row["material"] == "Copper"
            and row["family"] in {"n", "p", "alpha"}
            and row["source_parent_ZA"] in {"29061", "29062", "29064"}
            and origin_by_key.get(key)
        ):
            selected_flow[key] = row

    rows: list[dict[str, object]] = []
    for key in sorted(selected_flow):
        family, volume, parent = key
        frow = selected_flow[key]
        orows = origin_by_key[key]
        inventory_bq = float(frow["day15_activity_Bq"])
        support_bq = math.fsum(float(row["day15_activity_contribution_Bq"]) for row in orows)
        unique63 = math.fsum(
            float(row["day15_activity_contribution_Bq"])
            for row in orows
            if parent == "29064"
            and row["interacting_particle"] == "neutron"
            and row["creator_process"] == "nCapture"
        )
        # Conventional 65Cu channel assignment proxy.  The stored record does
        # not contain the target isotope, so even neutronInelastic cannot be
        # promoted to target-resolved FACT at high energy.  This partition is
        # used only to show the scale of a favorable pure-65Cu hypothesis.
        unique65 = math.fsum(
            float(row["day15_activity_contribution_Bq"])
            for row in orows
            if parent == "29064"
            and (
                (
                    row["interacting_particle"] == "neutron"
                    and row["creator_process"] == "neutronInelastic"
                )
                or (
                    row["interacting_particle"] == "gamma"
                    and row["creator_process"] == "photonNuclear"
                )
            )
        )
        closure = math.isclose(support_bq, inventory_bq, rel_tol=0.0, abs_tol=1.0e-8)
        mission = mission_by_key.get(key, 0.0)
        if closure and inventory_bq > 0.0:
            unresolved = max(0.0, inventory_bq - unique63 - unique65)
            remove63_credit = mission * unique63 / inventory_bq
            pure65_bq_proxy = unresolved + unique65 / F65_NATURAL
            pure63_bq_proxy = unresolved + unique63 / F63_NATURAL
            pure65_mission_proxy = mission * pure65_bq_proxy / inventory_bq
            pure63_mission_proxy = mission * pure63_bq_proxy / inventory_bq
            status = "CHANNEL_BALANCE_PROXY__TARGET_ISOTOPE_NOT_SERIALIZED"
        else:
            unresolved = inventory_bq
            remove63_credit = 0.0
            pure65_bq_proxy = "UNKNOWN"
            pure63_bq_proxy = "UNKNOWN"
            pure65_mission_proxy = "UNKNOWN"
            pure63_mission_proxy = "UNKNOWN"
            status = "UNKNOWN__ORIGIN_SUPPORT_DOES_NOT_CLOSE_INVENTORY_KEY"
        rows.append(
            {
                "family": family,
                "source_volume": volume,
                "component_group": frow["component_group"],
                "parent_ZA": parent,
                "isotope": frow["isotope"],
                "inventory_day15_Bq": inventory_bq,
                "origin_supported_day15_Bq": support_bq,
                "strict_unique_63Cu_nCapture_to_Cu64_Bq": unique63,
                "assigned_65Cu_Cu64_nonCapture_Bq_proxy": unique65,
                "target_isotope_unresolved_Bq": unresolved,
                "baseline_selected_mission_counts": mission,
                "perfect_remove_known_63Cu_channel_count_credit": remove63_credit,
                "pure65_known_channel_Bq_proxy": pure65_bq_proxy,
                "pure65_known_channel_mission_counts_proxy": pure65_mission_proxy,
                "pure63_known_channel_Bq_proxy": pure63_bq_proxy,
                "pure63_known_channel_mission_counts_proxy": pure63_mission_proxy,
                "status": status,
            }
        )
    write_csv(HERE / "copper_isotope_engineering_screen.csv", rows, list(rows[0]))

    closed = [row for row in rows if row["status"].startswith("CHANNEL_BALANCE")]
    baseline_counts = math.fsum(float(row["baseline_selected_mission_counts"]) for row in closed)
    remove63_credit = math.fsum(
        float(row["perfect_remove_known_63Cu_channel_count_credit"]) for row in closed
    )
    pure65_counts = math.fsum(float(row["pure65_known_channel_mission_counts_proxy"]) for row in closed)
    pure63_counts = math.fsum(float(row["pure63_known_channel_mission_counts_proxy"]) for row in closed)
    summary = [
        {
            "scenario": "strict_known_63Cu_channel_perfect_removal_only",
            "covered_family_volume_parent_keys": len(closed),
            "baseline_counts_in_covered_keys": baseline_counts,
            "candidate_counts_proxy": baseline_counts - remove63_credit,
            "count_reduction_proxy": remove63_credit,
            "fraction_of_full_D20": remove63_credit / D20,
            "verdict": "INSUFFICIENT_EVEN_BEFORE_65Cu_MIGRATION",
        },
        {
            "scenario": "100pct_65Cu_known_channel_balance",
            "covered_family_volume_parent_keys": len(closed),
            "baseline_counts_in_covered_keys": baseline_counts,
            "candidate_counts_proxy": pure65_counts,
            "count_reduction_proxy": baseline_counts - pure65_counts,
            "fraction_of_full_D20": (baseline_counts - pure65_counts) / D20,
            "verdict": "KILL__TARGET_ISOTOPE_UNKNOWN_AND_KNOWN_NET_CREDIT_TOO_SMALL",
        },
        {
            "scenario": "100pct_63Cu_known_channel_balance",
            "covered_family_volume_parent_keys": len(closed),
            "baseline_counts_in_covered_keys": baseline_counts,
            "candidate_counts_proxy": pure63_counts,
            "count_reduction_proxy": baseline_counts - pure63_counts,
            "fraction_of_full_D20": (baseline_counts - pure63_counts) / D20,
            "verdict": "KILL__KNOWN_CHANNEL_PROXY_INCREASES_BACKGROUND",
        },
    ]
    write_csv(HERE / "copper_isotope_engineering_summary.csv", summary, list(summary[0]))


def main() -> None:
    lineage = read_csv(LINEAGE)
    flow = read_csv(FLOW)
    origins = read_csv(ORIGINS)
    build_bg_j4(lineage)
    build_isotope_screen(flow, origins, lineage)


if __name__ == "__main__":
    main()
