#!/usr/bin/env python3
"""Validate the v3p5 exact-position delayed-source closure products."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, problems: list[str]) -> None:
    if not condition:
        problems.append(message)


def close(a: float, b: float, tol: float, message: str, problems: list[str]) -> None:
    require(math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol, f"{message}: got {a}, expected {b}", problems)


def paths(label: str) -> dict[str, Path]:
    return {
        "source_dir": ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}",
        "source": ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "activation_decay_day15_groundstate_fixed.source",
        "manifest": ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "exactpos_delayed_source_manifest.json",
        "table_summary": ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "exactpos_weighted_rpip_summary.json",
        "step02": ROOT
        / "stepwise_maintenance"
        / "step02_raw_background_simulation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step02_v3p5_centerfinger_{label}_summary.json",
        "step05": ROOT
        / "stepwise_maintenance"
        / "step05_veto_time_axis"
        / f"outputs_v3p5_centerfinger_{label}_l1"
        / "step05_v3p5_centerfinger_l1_response_summary.json",
        "step06": ROOT
        / "stepwise_maintenance"
        / "step06_mission_time_variation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step06_v3p5_centerfinger_{label}_summary.json",
        "step07": ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_v3p5_centerfinger_{label}" / "source_case_summary.json",
        "step08": ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / f"outputs_v3p5_centerfinger_{label}"
        / "step08_v3p5_centerfinger_time_dependent_summary.json",
        "performance": ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / "outputs"
        / f"performance_curve_comparison_1Ms_{label}"
        / "performance_curve_comparison_1Ms_summary.json",
        "w2_breakdown": ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / f"outputs_v3p5_centerfinger_{label}"
        / "w2_background_source_breakdown"
        / "w2_background_source_breakdown_summary.json",
        "boundary": ROOT / "outputs" / "reports" / f"v3p5_boundary_closure_{label}_20260613" / "v3p5_boundary_closure_summary.json",
        "closure": ROOT
        / "outputs"
        / "reports"
        / f"v3p5_fullstat_performance_w2_closure_{label}_20260613"
        / "v3p5_fullstat_performance_w2_closure_summary.json",
        "convergence": ROOT
        / "outputs"
        / "reports"
        / "v3p5_exactpos_convergence_20260614"
        / "v3p5_exactpos_convergence_summary.json",
    }


def validate(label: str) -> list[str]:
    problems: list[str] = []
    p = paths(label)
    for name, path in p.items():
        require(path.exists(), f"missing {name}: {rel(path)}", problems)
    if problems:
        return problems

    manifest = load_json(p["manifest"])
    table = load_json(p["table_summary"])
    step02 = load_json(p["step02"])
    step05 = load_json(p["step05"])
    step06 = load_json(p["step06"])
    step07 = load_json(p["step07"])
    step08 = load_json(p["step08"])
    performance = load_json(p["performance"])
    w2_breakdown = load_json(p["w2_breakdown"])
    boundary = load_json(p["boundary"])
    closure = load_json(p["closure"])
    convergence = load_json(p["convergence"])

    manifest_status = str(manifest.get("status", ""))
    require(
        manifest_status.startswith("PASS") and "EXACTPOS" in manifest_status,
        f"bad exactpos manifest status: {manifest.get('status')}",
        problems,
    )
    require(table.get("status") == "PASS_EXACTPOS_WEIGHTED_RPIP_TABLE", f"bad exactpos table status: {table.get('status')}", problems)
    require(int(table.get("eligible_rows_written", 0)) > 0, "exactpos weighted RPIP table has no eligible rows", problems)
    require(int(manifest.get("n_pointsource_blocks", 0)) > 0, "exactpos source has no PointSource blocks", problems)
    close(
        float(manifest.get("sum_flux_check_Bq", 0.0)),
        float(manifest.get("fixed_total_activity_Bq", 0.0)),
        1.0e-9,
        "exactpos source activity conservation",
        problems,
    )
    sampling_audit = manifest.get("sampling_audit", {})
    require(sampling_audit.get("status") in {"PASS", "WARN"}, f"bad or missing sampling audit status: {sampling_audit.get('status')}", problems)
    require(
        float(sampling_audit.get("sum_flux_abs_delta_Bq", 0.0)) <= max(1.0e-9, 1.0e-12 * float(manifest.get("fixed_total_activity_Bq", 0.0))),
        f"sampling audit flux conservation failed: {sampling_audit.get('sum_flux_abs_delta_Bq')}",
        problems,
    )
    if manifest.get("source_mode") == "sampled_equal_flux_pointsource_blocks":
        require(
            "support-size/seed convergence" in str(sampling_audit.get("interpretation", "")),
            "sampled exactpos manifest does not record support-size convergence caveat",
            problems,
        )

    source_text = p["source"].read_text(encoding="utf-8", errors="ignore")
    point_sources = source_text.count(".Beam PointSource")
    radial_sources = source_text.count(".Beam RadialProfileBeam")
    require(point_sources == int(manifest["n_pointsource_blocks"]), f"PointSource block count {point_sources} != manifest {manifest['n_pointsource_blocks']}", problems)
    require(radial_sources == 0, f"exactpos source still contains {radial_sources} RadialProfileBeam blocks", problems)

    evaluation = convergence.get("evaluation", {})
    require(convergence.get("status") == "PASS_EXACTPOS_TRANSPORT_CONVERGENCE", f"bad convergence status: {convergence.get('status')}", problems)
    require(
        evaluation.get("authority_recommendation") == "PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY",
        f"bad convergence authority recommendation: {evaluation.get('authority_recommendation')}",
        problems,
    )
    require(int(evaluation.get("transport_backed_cases") or 0) >= 4, f"too few convergence cases: {evaluation.get('transport_backed_cases')}", problems)

    delayed = step02.get("delayed_transport", {})
    require(step02.get("statistics_label") == label, f"Step02 label mismatch: {step02.get('statistics_label')}", problems)
    require(step02.get("status") == "PASS_FULLSTAT_V2_EXACTPOS_TRANSPORT_CLOSURE", f"bad Step02 status: {step02.get('status')}", problems)
    require(delayed.get("status") == "PASS", f"bad Step02 delayed status: {delayed.get('status')}", problems)
    require(int(delayed.get("SE") or 0) == int(delayed.get("ID") or -1), "Step02 delayed SE/ID mismatch", problems)
    require(float(delayed.get("TE_s") or 0.0) > 0.0, "Step02 delayed TE_s is not positive", problems)
    require("Cosima SIM TE" in str(delayed.get("TE_source", "")), "Step02 delayed transport does not document TE source", problems)

    require(step05.get("statistics_label") == label, f"Step05 label mismatch: {step05.get('statistics_label')}", problems)
    require(step05.get("status") == f"PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_{label.upper()}", f"bad Step05 status: {step05.get('status')}", problems)
    require(step06.get("statistics_label") == label, f"Step06 label mismatch: {step06.get('statistics_label')}", problems)
    require(step06.get("status") == f"PASS_V3P5_STEP06_TIME_AXIS_{label.upper()}", f"bad Step06 status: {step06.get('status')}", problems)
    require(step07.get("status") == f"PASS_V3P5_STEP07_SOURCE_CASES_{label.upper()}", f"bad Step07 status: {step07.get('status')}", problems)
    require(step08.get("status") == f"PASS_V3P5_STEP08_TIME_DEPENDENT_{label.upper()}", f"bad Step08 status: {step08.get('status')}", problems)
    require(performance.get("status") == "PASS_PERFORMANCE_CURVE_COMPARISON_1MS", f"bad performance status: {performance.get('status')}", problems)
    require(performance.get("inputs", {}).get("v3p5_label") == label, f"performance label mismatch: {performance.get('inputs', {}).get('v3p5_label')}", problems)
    require(w2_breakdown.get("status") == "PASS_V3P5_W2_BACKGROUND_SOURCE_BREAKDOWN", f"bad W2 breakdown status: {w2_breakdown.get('status')}", problems)
    require(w2_breakdown.get("statistics_label") == label, f"W2 breakdown label mismatch: {w2_breakdown.get('statistics_label')}", problems)

    exact = boundary.get("exact_position_delayed_source", {})
    require(boundary.get("statistics_label") == label, f"boundary label mismatch: {boundary.get('statistics_label')}", problems)
    require(
        boundary.get("authority_role") == "CURRENT_EXACT_POSITION_RATE_AUTHORITY",
        f"boundary authority_role mismatch: {boundary.get('authority_role')}",
        problems,
    )
    require(boundary.get("status") == "PASS_V3P5_BOUNDARY_CLOSURE_SIDECARS", f"bad boundary status: {boundary.get('status')}", problems)
    require(str(exact.get("status", "")).startswith("PASS_EXACT_RPIP"), f"boundary exactpos is not closed: {exact.get('status')}", problems)
    require(exact.get("source_mode") == manifest.get("source_mode"), "boundary source_mode mismatch", problems)
    require(int(exact.get("n_pointsource_blocks") or 0) == int(manifest.get("n_pointsource_blocks") or -1), "boundary PointSource count mismatch", problems)

    require(closure.get("statistics_label") == label, f"closure label mismatch: {closure.get('statistics_label')}", problems)
    require(
        closure.get("authority_role") == "CURRENT_EXACT_POSITION_RATE_AUTHORITY",
        f"closure authority_role mismatch: {closure.get('authority_role')}",
        problems,
    )
    require(closure.get("status") == "PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE", f"bad closure status: {closure.get('status')}", problems)
    require(not closure.get("problems"), f"closure problems: {closure.get('problems')}", problems)
    require(str(closure.get("boundary_closure", {}).get("exact_position_status", "")).startswith("PASS_EXACT_RPIP"), "closure did not package closed exactpos status", problems)
    require(
        closure.get("exactpos_convergence", {}).get("status") == "PASS_EXACTPOS_TRANSPORT_CONVERGENCE",
        f"closure did not package convergence PASS: {closure.get('exactpos_convergence')}",
        problems,
    )

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="fullstat_v2_exactpos", help="Exact-position label to validate")
    args = ap.parse_args()

    problems = validate(args.label)
    payload = {
        "status": "PASS_V3P5_EXACTPOS_CLOSURE_VALIDATION" if not problems else "FAIL_V3P5_EXACTPOS_CLOSURE_VALIDATION",
        "statistics_label": args.label,
        "problems": problems,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
