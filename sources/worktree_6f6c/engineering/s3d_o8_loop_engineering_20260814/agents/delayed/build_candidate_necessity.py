#!/usr/bin/env python3
"""Build optimistic delayed-budget removal ceilings; no transport."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
B_TARGET_CPS = 0.016581812


def read_csv(name: str) -> list[dict[str, str]]:
    with (HERE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def neff(values: list[float]) -> float:
    total = math.fsum(values)
    squares = math.fsum(value * value for value in values)
    return total * total / squares if squares > 0.0 else 0.0


def main() -> None:
    components = {
        row["component_group"]: row
        for row in read_csv("delayed_component_summary.csv")
    }
    materials = {
        row["material"]: row
        for row in read_csv("delayed_material_summary.csv")
    }
    bubbles = read_csv("delayed_position_bubbles.csv")

    scenarios: list[dict[str, Any]] = [
        {
            "aggregation": "component",
            "scenario": "MXC_only",
            "groups": ("MXC_50mK_plate",),
            "topology_status": "one named component, but perfect removal is not an engineering candidate",
        },
        {
            "aggregation": "component",
            "scenario": "Nb_inner_plus_Mu_outer_only",
            "groups": ("Nb_inner_cylinder", "MuMetal_outer_cylinder"),
            "topology_status": "two mandatory magnetic shells; perfect removal violates function",
        },
        {
            "aggregation": "component",
            "scenario": "minimum_named_common_ceiling",
            "groups": (
                "MXC_50mK_plate", "Nb_inner_cylinder",
                "MuMetal_outer_cylinder", "L0_Cu_disk",
            ),
            "topology_status": "four independent thermal/structural/magnetic components, not one topology",
        },
        {
            "aggregation": "component",
            "scenario": "minimum_common_ceiling_with_Other_bucket",
            "groups": (
                "MXC_50mK_plate", "Nb_inner_cylinder",
                "MuMetal_outer_cylinder", "Other",
            ),
            "topology_status": "Other is heterogeneous and cannot define a geometry operation",
        },
        {
            "aggregation": "material",
            "scenario": "all_Cu_only",
            "groups": ("Copper",),
            "topology_status": "material-class deletion spans many independent cold plates/can/supports",
        },
        {
            "aggregation": "material",
            "scenario": "Nb_plus_Mu_all_material_only",
            "groups": ("Nb", "Mu-metal"),
            "topology_status": "two magnetic material classes; perfect removal violates shielding function",
        },
        {
            "aggregation": "material",
            "scenario": "Copper_plus_Nb",
            "groups": ("Copper", "Nb"),
            "topology_status": "two material classes across multiple components; optimistic ceiling only",
        },
        {
            "aggregation": "material",
            "scenario": "Copper_plus_Mu",
            "groups": ("Copper", "Mu-metal"),
            "topology_status": "two material classes across multiple components; optimistic ceiling only",
        },
        {
            "aggregation": "material",
            "scenario": "Copper_plus_Ag",
            "groups": ("Copper", "Ag-proxy"),
            "topology_status": "Ag proxy is one selected event and is not a stable closing class",
        },
        {
            "aggregation": "material",
            "scenario": "all_non_Copper",
            "groups": tuple(name for name in materials if name != "Copper"),
            "topology_status": "counterfactual necessity test, not a candidate",
        },
    ]

    rate_fields = {
        "official_observed_central": "selected_rate_cps_observed_mix",
        "source_mix_screen": "selected_rate_cps_full_inventory_reweighted",
    }
    baseline_by_basis = {
        basis: math.fsum(float(row[field]) for row in components.values())
        for basis, field in rate_fields.items()
    }

    output: list[dict[str, Any]] = []
    for scenario in scenarios:
        summary = components if scenario["aggregation"] == "component" else materials
        group_field = "component_group" if scenario["aggregation"] == "component" else "material"
        groups = scenario["groups"]
        selected_bubbles = [row for row in bubbles if row[group_field] in groups]
        position_rates = [float(row["selected_rate_cps_at_position"]) for row in selected_bubbles]
        official_position_neff = neff(position_rates)
        official_largest_position_share = (
            max(position_rates, default=0.0) / math.fsum(position_rates)
            if position_rates else 0.0
        )
        total_bq = math.fsum(float(summary[group]["day15_activity_Bq"]) for group in groups)
        supported_bq = math.fsum(float(summary[group]["coupling_supported_Bq"]) for group in groups)
        for basis, rate_field in rate_fields.items():
            baseline = baseline_by_basis[basis]
            required = baseline - B_TARGET_CPS
            removed = math.fsum(float(summary[group][rate_field]) for group in groups)
            residual = baseline - removed
            margin = B_TARGET_CPS - residual
            output.append(
                {
                    "basis": basis,
                    "aggregation": scenario["aggregation"],
                    "scenario": scenario["scenario"],
                    "removed_groups": " | ".join(groups),
                    "baseline_cps": baseline,
                    "target_cps": B_TARGET_CPS,
                    "required_reduction_cps": required,
                    "optimistic_100pct_removed_rate_cps": removed,
                    "fraction_of_required_reduction_covered": removed / required,
                    "optimistic_residual_cps": residual,
                    "target_margin_cps_positive_is_pass": margin,
                    "optimistic_ceiling_passes_target": int(margin >= 0.0),
                    "coupling_supported_Bq_coverage": supported_bq / total_bq if total_bq else 0.0,
                    "official_selected_positions_in_removed_group": len(selected_bubbles),
                    "official_selected_position_Neff_of_removed_group": official_position_neff,
                    "official_largest_position_fraction_of_removed_group": official_largest_position_share,
                    "evidence_status": (
                        "CENTRAL_CEILING_ONLY__PERFECT_ELIMINATION__NO_HOST_MIGRATION"
                        if basis == "official_observed_central"
                        else "SCREEN_ONLY__SOURCE_MIX_REWEIGHT__UNSUPPORTED_KEYS_ZERO_IMPUTED"
                    ),
                    "topology_status": scenario["topology_status"],
                }
            )

    fields = list(output[0])
    with (HERE / "delayed_candidate_necessity.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)

    print(f"wrote {len(output)} rows to delayed_candidate_necessity.csv")


if __name__ == "__main__":
    main()
