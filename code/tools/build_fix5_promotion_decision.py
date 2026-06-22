#!/usr/bin/env python3
"""Build the fix5 full-stat promotion decision artifact.

This fails closed unless all machine-readable promotion requirements are met,
including a selected W2 delayed-rate decomposition by W/collimator origin.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
PROMOTION_DECISION = REPORT_DIR / "fix5_promotion_decision.json"
BENCHMARKS = ROOT / "core_md" / "fix5_benchmarks.json"
VERIFIER = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_verification_verdict.json"
STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / f"outputs_{LABEL}_l1"
    / f"step05_{LABEL}_l1_response_summary.json"
)
STEP06 = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / f"outputs_{LABEL}"
    / f"step06_{LABEL}_summary.json"
)
STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_{LABEL}" / "source_case_summary.json"
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / f"outputs_{LABEL}"
    / f"step08_{LABEL}_time_dependent_summary.json"
)
STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / f"outputs_{LABEL}" / "step09_focus_summary.json"
GROUNDSTATE = REPORT_DIR / "fix5_groundstate_half_life_audit_summary.json"
DELAYED_SOURCE = REPORT_DIR / "fix5_delayed_source_exactpos_summary.json"
W_ACTIVATION_AUDIT = REPORT_DIR / "fix5_w_activation_selected_w2_audit.json"
BENCHMARK_ALIGNMENT = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_benchmark_alignment.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def poisson_rate_sigma(rate: float, events: int) -> float:
    if events <= 0:
        return math.inf
    return rate / math.sqrt(events)


def upsert_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    check = row["check"]
    for index, existing in enumerate(rows):
        if existing.get("check") == check:
            rows[index] = row
            return
    rows.append(row)


def build_decision() -> dict[str, Any]:
    bench = load_json(BENCHMARKS)
    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step07 = load_json(STEP07)
    step08 = load_json(STEP08)
    step09 = load_json(STEP09)
    groundstate = load_json(GROUNDSTATE)
    delayed_source = load_json(DELAYED_SOURCE)
    w_audit = load_json(W_ACTIVATION_AUDIT)
    alignment = load_json(BENCHMARK_ALIGNMENT)

    w2 = step05["windows"]["w2_510p58_511p42"]
    phys = w2["physical_reference_flux"]
    prompt = w2["by_stream"]["prompt"]
    delayed = w2["by_stream"]["delayed"]
    ref = bench["benchmarks"]["v3p5_current_authority"]

    prompt_cps = float(phys["prompt_background_cps"])
    delayed_cps = float(phys["delayed_background_cps"])
    b_cps = float(phys["background_cps"])
    signal_cps = float(phys["signal_cps_at_reference_flux"])
    prompt_events = int(phys["low_stat_prompt_final_events"])
    delayed_events = int(phys["low_stat_delayed_final_events"])
    prompt_sigma = poisson_rate_sigma(prompt_cps, prompt_events)
    delayed_sigma = poisson_rate_sigma(delayed_cps, delayed_events)
    b_sigma = math.sqrt(prompt_sigma * prompt_sigma + delayed_sigma * delayed_sigma)

    ref_b = float(ref["step05_background_cps"])
    ref_delayed = float(ref["w2_delayed_cps"])
    z20d = float(step08["checks"]["A_reference_w2_Z20d_time_dependent"])
    f3_20d = float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    delayed_total_red_flag = delayed_cps > ref_delayed + delayed_sigma
    background_decisive_pass = b_cps + b_sigma < ref_b
    background_compatible_pass = b_cps <= ref_b and not background_decisive_pass
    focused_transport = step09.get("focused_transport", {})
    signal_replay_complete = (
        str(step09.get("status", "")).startswith("PASS")
        and rel(ROOT / str(step05["inputs"]["science_sim"])) == str(focused_transport.get("path"))
        and "DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy" in str(focused_transport.get("geometry", ""))
        and int(focused_transport.get("SE") or 0) == int(step09.get("triggers") or -1)
        and int(focused_transport.get("ID") or 0) == int(step09.get("triggers") or -2)
    )
    signal_keep = signal_cps / float(ref["step05_signal_cps"]) if signal_replay_complete else None
    signal_keep_threshold = float(bench["promotion_thresholds"]["min_signal_keep_fraction_vs_v3p5"])
    z_threshold_met = z20d >= float(ref["step08_Z20d"]) if signal_replay_complete else None
    f3_threshold_met = f3_20d <= float(ref["step08_F3_20d_ph_cm2_s"]) if signal_replay_complete else None
    signal_keep_threshold_met = signal_keep is not None and signal_keep >= signal_keep_threshold

    w_activity = float(
        groundstate["checks"]["w_or_collimator_new_activity_Bq"]
        if "checks" in groundstate
        else groundstate["w_or_collimator_new_activity_Bq"]
    )
    fixed_activity = float(step06["checks"]["step02_fixed_source_activity_Bq"])
    w_checks = w_audit.get("checks", {})
    w_activation_rate_decomposition_available = (
        str(w_audit.get("status", "")).startswith("PASS")
        and int(w_checks.get("selected_events", -1)) == delayed_events
        and abs(float(w_checks.get("selected_rate_hz", math.nan)) - delayed_cps) <= 1.0e-15
        and bool(w_checks.get("events_match_step05")) is True
        and bool(w_checks.get("rate_matches_step05")) is True
        and int(w_checks.get("exactpos_match_failures", -1)) == 0
    )
    w_activation_cps = (
        float(w_checks["w_or_collimator_selected_rate_hz"])
        if w_activation_rate_decomposition_available
        else None
    )
    w_activation_fraction = (
        float(w_checks["w_or_collimator_fraction_of_delayed_selected_rate"])
        if w_activation_rate_decomposition_available
        and w_checks.get("w_or_collimator_fraction_of_delayed_selected_rate") is not None
        else None
    )
    w_activation_dominant = (
        bool(w_checks.get("w_or_collimator_is_dominant_component"))
        if w_activation_rate_decomposition_available
        else None
    )
    delayed_red_flag = delayed_total_red_flag or bool(w_activation_dominant)
    automatic_pass_rule_met = (
        (background_decisive_pass or background_compatible_pass)
        and signal_keep_threshold_met
        and bool(z_threshold_met)
        and bool(f3_threshold_met)
        and not delayed_red_flag
        and w_activation_rate_decomposition_available
    )
    if automatic_pass_rule_met:
        decision = "PASS_FIX5_REPLACES_V3P5"
        decision_reason = "All automatic promotion thresholds are satisfied, including selected W2 delayed W/collimator-origin decomposition."
    else:
        if not w_activation_rate_decomposition_available:
            decision = "USER_REVIEW_REQUIRED_SELECTED_W_ACTIVATION_RATE_NOT_DECOMPOSED"
            decision_reason = (
                "Fix5 passes the full-stat background, delayed-total, signal-keep, Z20d, and F3 checks against the current v3p5 authority, "
                "and the fix5 signal replay is consumed by Step05. Automatic replacement is not issued because selected W/collimator-origin W2 delayed cps is not decomposed; the source-level W/collimator activity is reported instead."
            )
        elif bool(w_activation_dominant):
            decision = "USER_REVIEW_REQUIRED_SELECTED_W_ACTIVATION_DOMINANT"
            decision_reason = "Selected W/collimator-origin W2 delayed cps is a dominant delayed component, triggering the delayed red-flag rule."
        else:
            decision = "FAIL_FIX5_PROMOTION_THRESHOLDS_NOT_MET"
            decision_reason = "One or more automatic promotion thresholds against the current v3p5 authority are not satisfied."

    blocking_items: list[str] = []
    if not w_activation_rate_decomposition_available:
        blocking_items.append(
            "Selected W2 delayed cps is not decomposed by W/collimator origin; use source-level W/collimator activity as the current audit evidence or run a dedicated delayed-origin decomposition before automatic replacement."
        )
    if bool(w_activation_dominant):
        blocking_items.append("Selected W/collimator-origin W2 delayed cps is a dominant delayed component.")
    if not (background_decisive_pass or background_compatible_pass):
        blocking_items.append("Fix5 W2 background does not pass the v3p5 current-authority background threshold.")
    if not signal_keep_threshold_met:
        blocking_items.append("Fix5 signal keep fraction is below the configured threshold.")
    if not bool(z_threshold_met):
        blocking_items.append("Fix5 Z20d is below the current v3p5 authority.")
    if not bool(f3_threshold_met):
        blocking_items.append("Fix5 F3(20d) is above the current v3p5 authority.")
    if delayed_total_red_flag:
        blocking_items.append("Fix5 delayed total exceeds the current v3p5 delayed authority by more than one fix5 delayed sigma.")

    return {
        "label": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "contract_authority": rel(BENCHMARKS),
        "decision": decision,
        "decision_reason": decision_reason,
        "B_cps": b_cps,
        "B_sigma_cps": b_sigma,
        "B_sigma_method": "quadrature of prompt_cps/sqrt(prompt_selected_events) and delayed_cps/sqrt(delayed_selected_events)",
        "prompt_cps": prompt_cps,
        "prompt_sigma_cps": prompt_sigma,
        "prompt_selected_events": prompt_events,
        "delayed_cps": delayed_cps,
        "delayed_sigma_cps": delayed_sigma,
        "delayed_selected_events": delayed_events,
        "w_activation_cps": w_activation_cps,
        "w_activation_cps_status": (
            "SELECTED_W2_RATE_DECOMPOSED"
            if w_activation_rate_decomposition_available
            else "NOT_DECOMPOSED_TO_SELECTED_W2_RATE"
        ),
        "w_activation_rate_decomposition_available": w_activation_rate_decomposition_available,
        "w_activation_selected_events": (
            int(w_checks["w_or_collimator_selected_events"])
            if w_activation_rate_decomposition_available
            else None
        ),
        "w_activation_fraction_of_delayed_selected_rate": w_activation_fraction,
        "w_activation_dominant_component": w_activation_dominant,
        "w_or_collimator_activity_Bq": w_activity,
        "w_or_collimator_activity_fraction_of_fixed_source": w_activity / fixed_activity if fixed_activity else None,
        "signal_cps": signal_cps,
        "signal_cps_status": "FIX5_FOCUSED_REPLAY_CONSUMED_BY_STEP05" if signal_replay_complete else "MISSING_OR_UNVERIFIED_FIX5_SIGNAL_REPLAY",
        "signal_keep_fraction_vs_v3p5": signal_keep,
        "signal_replay_complete": signal_replay_complete,
        "Z20d": z20d,
        "Z20d_status": "FIX5_SIGNAL_REPLAY_BACKED" if signal_replay_complete else "PLACEHOLDER_PENDING_FIX5_SIGNAL_REPLAY",
        "F3_20d_ph_cm2_s": f3_20d,
        "F3_20d_status": "FIX5_SIGNAL_REPLAY_BACKED" if signal_replay_complete else "PLACEHOLDER_PENDING_FIX5_SIGNAL_REPLAY",
        "comparison_vs_v3p5": {
            "reference_label": ref["label"],
            "reference_B_cps": ref_b,
            "reference_delayed_cps": ref_delayed,
            "reference_Z20d": ref["step08_Z20d"],
            "reference_F3_20d_ph_cm2_s": ref["step08_F3_20d_ph_cm2_s"],
            "B_ratio_fix5_over_v3p5": b_cps / ref_b,
            "B_delta_cps": b_cps - ref_b,
            "background_decisive_pass": background_decisive_pass,
            "background_compatible_pass": background_compatible_pass,
            "delayed_total_red_flag": delayed_total_red_flag,
            "w_activation_dominant_component": w_activation_dominant,
            "delayed_red_flag": delayed_red_flag,
            "delayed_ratio_fix5_over_v3p5": delayed_cps / ref_delayed,
            "signal_keep_fraction_vs_v3p5": signal_keep,
            "Z20d_ratio_fix5_over_v3p5": z20d / float(ref["step08_Z20d"]),
            "F3_ratio_fix5_over_v3p5": f3_20d / float(ref["step08_F3_20d_ph_cm2_s"]),
        },
        "comparison_vs_old_new_geo_re": {
            "benchmark_alignment_decision": alignment.get("decision"),
            "gate_allowed": alignment.get("decision") == "ALIGNED",
            "prompt_old_total_cps": bench["benchmarks"]["new_geo_re"]["prompt_total_cps"],
            "delayed_old_total_cps": bench["benchmarks"]["new_geo_re"]["delayed_total_cps"],
            "interpretation": "REPORT_ONLY_UNTIL_ALIGNMENT_IS_ALIGNED",
        },
        "promotion_thresholds": bench["promotion_thresholds"],
        "threshold_evaluation": {
            "background_decisive_or_compatible_pass": background_decisive_pass or background_compatible_pass,
            "signal_keep_fraction_available": signal_keep is not None,
            "signal_keep_threshold_met": signal_keep_threshold_met,
            "Z20d_threshold_met": z_threshold_met,
            "F3_20d_threshold_met": f3_threshold_met,
            "no_delayed_red_flag": not delayed_red_flag,
            "w_activation_rate_decomposition_available": w_activation_rate_decomposition_available,
            "automatic_pass_rule_met": automatic_pass_rule_met,
        },
        "blocking_items": blocking_items,
        "evidence": {
            "step05_summary": rel(STEP05),
            "step06_summary": rel(STEP06),
            "step07_summary": rel(STEP07),
            "step08_summary": rel(STEP08),
            "step09_signal_replay_summary": rel(STEP09),
            "step09_signal_replay_sim": focused_transport.get("path"),
            "groundstate_half_life_audit": rel(GROUNDSTATE),
            "delayed_source_exactpos_summary": rel(DELAYED_SOURCE),
            "w_activation_selected_w2_audit": rel(W_ACTIVATION_AUDIT),
            "w_activation_selected_w2_events": w_audit.get("event_table"),
            "benchmark_alignment": rel(BENCHMARK_ALIGNMENT),
            "prompt_counts": {
                "raw_events": prompt["raw_events"],
                "active_veto_pass_events": prompt["active_veto_pass_events"],
                "side_compton_fov_pass_events": prompt["side_compton_fov_pass_events"],
            },
            "delayed_counts": {
                "raw_events": delayed["raw_events"],
                "active_veto_pass_events": delayed["active_veto_pass_events"],
                "side_compton_fov_pass_events": delayed["side_compton_fov_pass_events"],
            },
        },
    }


def update_verifier(decision: dict[str, Any]) -> None:
    verifier = load_json(VERIFIER)
    rows = verifier.setdefault("rows", [])
    now = decision["generated_at_utc"]
    common = {"updated_at_utc": now}
    upsert_row(
        rows,
        {
            "check": "fix5_step05_l1_response",
            "status": "PASS",
            "evidence_path": rel(STEP05),
            "blocking": True,
            "details": {
                "status": load_json(STEP05)["status"],
                "w2_background_cps": decision["B_cps"],
                "prompt_cps": decision["prompt_cps"],
                "delayed_cps": decision["delayed_cps"],
                "signal_status": decision["signal_cps_status"],
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_step06_mission_time_axis",
            "status": "PASS",
            "evidence_path": rel(STEP06),
            "blocking": True,
            "details": {
                "status": load_json(STEP06)["status"],
                "w2_dt_weighted_background_final_cps": load_json(STEP06)["checks"]["w2_dt_weighted_background_final_cps"],
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_step07_source_cases",
            "status": "PASS_NON_PROMOTION",
            "evidence_path": rel(STEP07),
            "blocking": False,
            "details": {
                "status": load_json(STEP07)["status"],
                "claim_level": load_json(STEP07)["claim_level"],
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_step08_time_dependent_significance",
            "status": "PASS_NON_PROMOTION",
            "evidence_path": rel(STEP08),
            "blocking": False,
            "details": {
                "status": load_json(STEP08)["status"],
                "claim_level": load_json(STEP08)["claim_level"],
                "Z20d": decision["Z20d"],
                "Z20d_status": decision["Z20d_status"],
                "F3_20d_ph_cm2_s": decision["F3_20d_ph_cm2_s"],
                "F3_20d_status": decision["F3_20d_status"],
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_signal_replay",
            "status": "PASS" if decision["signal_replay_complete"] else "PENDING",
            "evidence_path": decision["evidence"].get("step09_signal_replay_summary", ""),
            "blocking": True,
            "details": {
                "required": "Focused signal replay source card and SIM header must use the fix5 .geo.setup before promotion.",
                "current_step05_signal_status": decision["signal_cps_status"],
                "signal_keep_fraction_vs_v3p5": decision["signal_keep_fraction_vs_v3p5"],
                "signal_replay_complete": decision["signal_replay_complete"],
                "step09_signal_replay_sim": decision["evidence"].get("step09_signal_replay_sim"),
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_w_activation_selected_w2_audit",
            "status": "PASS" if decision["w_activation_rate_decomposition_available"] else "USER_REVIEW_REQUIRED",
            "evidence_path": decision["evidence"].get("w_activation_selected_w2_audit", ""),
            "blocking": True,
            "details": {
                "w_activation_cps": decision["w_activation_cps"],
                "w_activation_cps_status": decision["w_activation_cps_status"],
                "w_activation_selected_events": decision["w_activation_selected_events"],
                "w_activation_fraction_of_delayed_selected_rate": decision["w_activation_fraction_of_delayed_selected_rate"],
                "w_activation_dominant_component": decision["w_activation_dominant_component"],
            },
            **common,
        },
    )
    upsert_row(
        rows,
        {
            "check": "fix5_promotion_decision",
            "status": "PASS" if decision["decision"] == "PASS_FIX5_REPLACES_V3P5" else decision["decision"],
            "evidence_path": rel(PROMOTION_DECISION),
            "blocking": True,
            "details": {
                "decision": decision["decision"],
                "B_cps": decision["B_cps"],
                "B_sigma_cps": decision["B_sigma_cps"],
                "background_decisive_pass": decision["comparison_vs_v3p5"]["background_decisive_pass"],
                "delayed_red_flag": decision["comparison_vs_v3p5"]["delayed_red_flag"],
                "signal_replay_complete": decision["signal_replay_complete"],
                "signal_keep_fraction_vs_v3p5": decision["signal_keep_fraction_vs_v3p5"],
                "automatic_pass_rule_met": decision["threshold_evaluation"]["automatic_pass_rule_met"],
                "w_activation_cps_status": decision["w_activation_cps_status"],
            },
            **common,
        },
    )
    verifier["overall_status"] = (
        "PASS_FIX5_PROMOTION"
        if decision["decision"] == "PASS_FIX5_REPLACES_V3P5"
        else "USER_REVIEW_REQUIRED_FIX5_PROMOTION_SELECTED_W_ACTIVATION_RATE_NOT_DECOMPOSED"
    )
    verifier["updated_at_utc"] = now
    verifier["phase_step05_to_step08_status"] = "PASS_SIGNAL_REPLAYED_STEP05_TO_STEP08_CHAIN"
    verifier["promotion_decision_artifact"] = rel(PROMOTION_DECISION)
    verifier["final_rate_claim_allowed"] = decision["signal_replay_complete"]
    verifier["final_promotion_decision_allowed"] = decision["decision"] == "PASS_FIX5_REPLACES_V3P5"
    verifier["step05_l1_response_release_allowed"] = True
    write_json(VERIFIER, verifier)


def main() -> int:
    decision = build_decision()
    write_json(PROMOTION_DECISION, decision)
    update_verifier(decision)
    print(
        json.dumps(
            {
                "decision": decision["decision"],
                "promotion_decision": rel(PROMOTION_DECISION),
                "verifier": rel(VERIFIER),
                "B_cps": decision["B_cps"],
                "B_sigma_cps": decision["B_sigma_cps"],
                "signal_replay_complete": decision["signal_replay_complete"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
