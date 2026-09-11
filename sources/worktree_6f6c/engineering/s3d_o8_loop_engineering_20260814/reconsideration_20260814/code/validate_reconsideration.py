#!/usr/bin/env python3
"""Cross-check the AF1-48 reconsideration's decision-critical numbers."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str) -> dict:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def assert_close(actual: float, expected: float, *, tolerance: float = 1e-8) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise AssertionError(f"{actual!r} != {expected!r}")


def main() -> None:
    signal = load_json("focused_signal/candidate_signal_result.json")
    prompt = load_json(
        "focused_prompt_repeat64/three_cell_mechanism_result_repeat64.json"
    )
    prompt_plan = load_json(
        "focused_prompt_repeat64/three_cell_transport_plan_repeat64.json"
    )
    delayed = load_json("agents/delayed/audit_summary.json")

    assert signal["trials"] == 37194
    assert signal["baseline_selected_events"] == 27855
    assert signal["candidate_selected_events"] == 27993
    assert_close(
        signal["signal_retention_ratio"],
        signal["candidate_selected_events"] / signal["baseline_selected_events"],
    )
    candidate_s20 = signal["candidate_S20_counts"]
    candidate_gate = (candidate_s20 / 10.0) ** 2
    assert_close(signal["candidate_B20_max_counts"], candidate_gate)

    denominator_states = prompt["denominator_states"]
    assert denominator_states == {
        "cell_19932": 94,
        "cell_3883": 71,
        "cell_8081": 92,
    }
    assert sum(denominator_states.values()) == 257
    assert prompt_plan["uniform_repeats_per_state"] == 64
    assert prompt_plan["transport_events_per_geometry"] == 16448
    assert prompt["event_summary"]["rows"] == 32896

    mechanism = prompt["mechanism_comparison"]
    assert mechanism["baseline_active_veto_clean_pair"] == 160
    assert mechanism["candidate_active_veto_clean_pair"] == 104
    assert_close(mechanism["central_ratio"], 104 / 160)
    assert_close(mechanism["one_sided_exact_conditional_ratio_upper95"], 0.805087125734676)
    final = prompt["focused_final_comparison"]
    assert final["baseline_selected"] == 1
    assert final["candidate_selected"] == 0
    assert_close(final["one_sided_exact_conditional_ratio_upper95"], 19.0)

    mission = delayed["mission_counts"]
    p_counts = mission["prompt"]
    cu_counts = mission["exact_geometry_material_Copper"]
    nbmu_counts = mission["Nb_plus_MuMetal"]
    other_counts = mission["fixed_other_including_CuNi_and_Ag"]
    s_prompt = 0.80
    s_cu = 0.95
    s_nbmu = 0.75
    delta_new = 0.0
    residual = (
        p_counts * (1.0 - s_prompt)
        + cu_counts * (1.0 - s_cu)
        + nbmu_counts * (1.0 - s_nbmu)
        + other_counts
        + delta_new
    )
    margin = candidate_gate - residual
    conditional_f3 = 3.0e-5 * math.sqrt(residual / candidate_gate)
    s_prompt_min = 1.0 - (
        candidate_gate
        - cu_counts * (1.0 - s_cu)
        - nbmu_counts * (1.0 - s_nbmu)
        - other_counts
        - delta_new
    ) / p_counts
    s_cu_min = 1.0 - (
        candidate_gate
        - p_counts * (1.0 - s_prompt)
        - nbmu_counts * (1.0 - s_nbmu)
        - other_counts
        - delta_new
    ) / cu_counts

    assert_close(residual, 22890.854439849874)
    assert_close(margin, 4451.070303013526)
    assert_close(conditional_f3, 2.74497071059e-5)
    assert_close(s_prompt_min, 0.719654290594)
    assert_close(s_cu_min, 0.8748797171525777)

    with (ROOT / "agents/delayed/TC_AF1_budget_audit.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        budget_rows = list(csv.DictReader(handle))
    candidate_budget = next(
        row
        for row in budget_rows
        if row["budget_scope"]
        == "candidate_own_focused_signal__exact_48_volume_scope"
    )
    assert_close(float(candidate_budget["candidate_signal_S20"]), candidate_s20)
    assert_close(float(candidate_budget["candidate_count_gate"]), candidate_gate)
    assert_close(float(candidate_budget["predicted_residual_counts"]), residual)
    assert candidate_budget["evidence_status"] == (
        "SIGNAL_MEASURED__BACKGROUND_SUPPRESSIONS_ARITHMETIC_ONLY"
    )

    with (ROOT / "agents/geometry/MASS_CLOSURE.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        mass_rows = list(csv.DictReader(handle))
    mass_total = next(row for row in mass_rows if row["component"] == "CHANGED_SCOPE_TOTAL")
    mass_delta_kg = float(mass_total["candidate_minus_source_kg_fixed_seed_mc"])
    if abs(mass_delta_kg) >= 0.005:
        raise AssertionError("Nominal changed-scope mass mismatch exceeds 5 g")

    overlap_text = (ROOT / "data/candidate_overlap_check.txt").read_text(
        encoding="utf-8"
    )
    if "overlap_ok=1" not in overlap_text:
        raise AssertionError("Candidate geometry overlap check did not pass")

    required_files = [
        "agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup",
        "figures/af1_48_decision_evidence.png",
        "reports/S3D_O8_SCHEME_RECONSIDERATION.md",
    ]
    missing = [relative for relative in required_files if not (ROOT / relative).is_file()]
    if missing:
        raise AssertionError(f"Missing required artifacts: {missing}")

    result = {
        "schema_version": 1,
        "status": "PASS",
        "scope": "AF1-48 reconsideration decision-critical arithmetic and artifact integrity",
        "candidate_signal": {
            "trials": signal["trials"],
            "baseline_selected": signal["baseline_selected_events"],
            "candidate_selected": signal["candidate_selected_events"],
            "retention": signal["signal_retention_ratio"],
            "S20": candidate_s20,
            "count_gate": candidate_gate,
        },
        "prompt_P1_repeat64": {
            "primary_states": 257,
            "events_per_geometry": 16448,
            "active_veto_clean_pair_baseline": 160,
            "active_veto_clean_pair_candidate": 104,
            "central_ratio": mechanism["central_ratio"],
            "one_sided_upper95": mechanism[
                "one_sided_exact_conditional_ratio_upper95"
            ],
            "required_survival": final["pre_registered_central_requirement"],
            "status": "MECHANISM_DIRECTION_SUPPORTED__PROMPT_GATE_NOT_PROVEN",
        },
        "conditional_budget_not_a_measurement": {
            "assumptions": {
                "prompt_suppression": s_prompt,
                "Cu_net_suppression": s_cu,
                "NbMu_effective_suppression": s_nbmu,
                "new_material_counts": delta_new,
            },
            "residual_counts": residual,
            "margin_counts": margin,
            "conditional_F3_photon_cm-2_s-1": conditional_f3,
            "minimum_prompt_suppression_at_anchor": s_prompt_min,
            "minimum_Cu_net_suppression_at_anchor": s_cu_min,
        },
        "geometry": {
            "overlap_ok": True,
            "nominal_mass_delta_kg": mass_delta_kg,
            "mass_precision_warning": "ROOT Boolean capacity is Monte Carlo; physical precision is gram-scale, not the nominal sub-mg delta.",
        },
        "promotion_status": "ENGINEERING_CONDITIONAL_OPTIMUM__CANDIDATE_BACKGROUND_TRANSFER_NOT_CLOSED",
    }
    output = ROOT / "data/reconsideration_validation.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
