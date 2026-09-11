#!/usr/bin/env python3
"""Validate the Phase 12 final compact-source closure package."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "reports2.0"
OUT = R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
VALIDATION = OUT / "validation"

FORBIDDEN_PHRASES = [
    "confirmed Galactic-center point source",
    "confirmed source identity",
    "final production optics detectability",
    "final V404 detectability",
    "B diffuse focal-spot source",
    "selection best replaces baseline",
    "unqualified astrophysical discovery",
]

ALLOWING_GUARDS = [
    "forbidden, not claimed",
    "does not claim",
    "not claim",
    "not claimed",
    "no discovery",
    "not final",
    "not reached",
    "without final metric reproduction",
    "production optics are not available",
    "before a production",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def finite_positive(value: Any) -> bool:
    try:
        got = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(got) and got > 0


def line_allowed(line: str) -> bool:
    low = line.lower()
    return any(guard in low for guard in ALLOWING_GUARDS)


def validate_required_files(results: list[dict[str, str]]) -> None:
    required = [
        "README.md",
        "FINAL_DECISION.md",
        "final_claim_control.md",
        "inputs_manifest_final.csv",
        "authority_manifest_final.csv",
        "metric_closure_final.csv",
        "metric_closure_final.json",
        "phase9_phase10_phase12_reconciliation.md",
        "selection_upgrade_decision_final.md",
        "selection_upgrade_decision_final.json",
        "optics_model_status_final.md",
        "optics_model_status_final.json",
        "optics_requirements_final.csv",
        "requirements_closure_final.csv",
        "AB_template_likelihood_final.csv",
        "AB_template_likelihood_final.json",
        "AB_injection_recovery_final.csv",
        "source_case_status_final.csv",
        "phase12_summary.json",
        "artifact_manifest.csv",
        "final_tables_for_paper/table_numerical_lineage_final.csv",
        "final_tables_for_paper/table_metric_closure_final.csv",
        "final_tables_for_paper/table_AB_detectability_final.csv",
        "final_tables_for_paper/table_optics_requirements_final.csv",
        "final_tables_for_paper/table_claim_boundary_final.csv",
        "configs_final/source_cases_511_AB_final.yaml",
        "configs_final/optics_response_511_final_or_parametric.yaml",
        "configs_final/likelihood_bins_final.yaml",
        "configs_final/claim_policy_final.yaml",
        "manuscript_patch/NIMA_final_results_insert_zh.md",
        "manuscript_patch/NIMA_claim_control_insert_zh.md",
        "manuscript_patch/PPT_final_update_notes.md",
    ]
    missing = [item for item in required if not (OUT / item).exists()]
    add(
        results,
        "phase12_required_files",
        "PASS" if not missing else "FAIL",
        "all terminal Phase 12 files are present" if not missing else "missing: " + ", ".join(missing[:12]),
    )


def validate_manifests(results: list[dict[str, str]]) -> None:
    inputs_path = OUT / "inputs_manifest_final.csv"
    authority_path = OUT / "authority_manifest_final.csv"
    if not inputs_path.exists() or not authority_path.exists():
        add(results, "phase12_manifests_present", "FAIL", "missing inputs or authority manifest")
        return

    inputs = read_csv(inputs_path)
    input_ids = {row["item_id"] for row in inputs}
    required_inputs = {
        "phase12_guide",
        "science_detector_source",
        "phase11_crosswalk",
        "phase10_selection_audit",
        "phase9_detectability",
        "event_catalog",
        "measured_catalog",
        "final_numerical_lineage",
    }
    missing_inputs = sorted(required_inputs - input_ids)
    input_exists_ok = all(as_bool(row.get("exists")) for row in inputs if row["item_id"] in required_inputs)
    add(
        results,
        "phase12_inputs_manifest_complete",
        "PASS" if not missing_inputs and input_exists_ok else "FAIL",
        f"rows={len(inputs)} missing={missing_inputs} required_exists={input_exists_ok}",
    )

    authority = read_csv(authority_path)
    by_id = {row["item_id"]: row for row in authority}
    required_authority = {"science_detector_source", "background_ledger", "measured_catalog", "source_cases_AB", "optics_model", "selection_best"}
    missing_authority = sorted(required_authority - set(by_id))
    science_ok = by_id.get("science_detector_source", {}).get("path") == "particle_sources/run_configs/Science_511_onaxis_focalbeam_local.source"
    source_cases_ok = by_id.get("source_cases_AB", {}).get("forbidden_use") == "replacement detector source"
    selection_ok = by_id.get("selection_best", {}).get("status") == "AUDITED_NOT_MAIN_UNLESS_GATE_PASS"
    add(
        results,
        "phase12_authority_manifest_complete",
        "PASS" if not missing_authority and science_ok and source_cases_ok and selection_ok else "FAIL",
        f"rows={len(authority)} missing={missing_authority} science_ok={science_ok} source_cases_ok={source_cases_ok} selection_ok={selection_ok}",
    )


def validate_detector_and_source_cases(results: list[dict[str, str]]) -> None:
    science = ROOT / "particle_sources" / "run_configs" / "Science_511_onaxis_focalbeam_local.source"
    source_cfg = OUT / "configs_final" / "source_cases_511_AB_final.yaml"
    b_focal_sources = sorted((ROOT / "particle_sources" / "run_configs" / "astro_cases").glob("*B_GC_DIFFUSE*.source"))
    cfg_text = source_cfg.read_text(encoding="utf-8", errors="ignore") if source_cfg.exists() else ""
    ok = (
        science.exists()
        and source_cfg.exists()
        and "detector_response_authority: particle_sources/run_configs/Science_511_onaxis_focalbeam_local.source" in cfg_text
        and (
            "forbidden_use: replacement detector source" in cfg_text
            or "detector_response_forbidden_use: replacement detector source" in cfg_text
        )
        and "forbidden_use: focal-spot source" in cfg_text
        and not b_focal_sources
    )
    add(
        results,
        "phase12_detector_source_not_replaced",
        "PASS" if ok else "FAIL",
        f"science_exists={science.exists()} source_cfg={source_cfg.exists()} B_diffuse_sources={len(b_focal_sources)}",
    )

    status_path = OUT / "source_case_status_final.csv"
    if not status_path.exists():
        add(results, "phase12_source_case_status_final", "FAIL", "missing source_case_status_final.csv")
        return
    rows = read_csv(status_path)
    by_case = {row["case_id"]: row for row in rows}
    required = {"A_GC_COMPACT_CENTER", "B_GC_DIFFUSE_BULGE_DISK", "C_V404_2015_TRANSIENT_BENCHMARK"}
    b_ok = "focal-spot source" in by_case.get("B_GC_DIFFUSE_BULGE_DISK", {}).get("forbidden_claim", "")
    c_ok = by_case.get("C_V404_2015_TRANSIENT_BENCHMARK", {}).get("status") == "CLOSED_AS_BANDPASS_RISK_OR_OPTIONAL"
    add(
        results,
        "phase12_source_case_status_final",
        "PASS" if required.issubset(by_case) and b_ok and c_ok else "FAIL",
        f"cases={sorted(by_case)} B_guard={b_ok} C_closed={c_ok}",
    )
    if c_ok:
        add(results, "phase12_C_V404_closed_as_benchmark_only", "WARN", "C/V404 remains closed as bandpass-risk benchmark, not final detectability")


def validate_metric_closure(results: list[dict[str, str]]) -> dict[str, Any] | None:
    path = OUT / "metric_closure_final.csv"
    js_path = OUT / "metric_closure_final.json"
    if not path.exists() or not js_path.exists():
        add(results, "phase12_metric_closure_final", "FAIL", "missing metric_closure_final csv/json")
        return None
    rows = read_csv(path)
    data = read_json(js_path)
    summary = data.get("summary", {})
    by_id = {row["metric_id"]: row for row in rows}
    required = {
        "phase9_baseline_ERL",
        "phase10_baseline_count_only",
        "phase12_baseline_measured_E",
        "phase12_baseline_measured_ER",
        "phase12_baseline_measured_ERL",
        "phase12_selection_best_measured_E",
        "phase12_selection_best_measured_ER",
        "phase12_selection_best_measured_ERL",
    }
    missing = sorted(required - set(by_id))
    primary = [row["metric_id"] for row in rows if as_bool(row.get("primary_metric_candidate"))]
    positive = all(finite_positive(by_id[mid].get("F3_1Ms")) and finite_positive(by_id[mid].get("F5_1Ms")) for mid in required if mid in by_id)
    decision = summary.get("final_decision_code")
    no_a_without_optics = decision != "A" or summary.get("production_optics_ready") is True
    claim_ok = (
        (decision == "C" and summary.get("final_claim_level") == "PARAMETRIC_OPTICS_REQUIREMENT")
        or (decision in {"A", "B"} and summary.get("final_claim_level") == "MEASURED_TEMPLATE_ANALYSIS")
    )
    add(
        results,
        "phase12_metric_closure_final",
        "PASS" if not missing and len(primary) == 1 and positive and decision in {"A", "B", "C"} and no_a_without_optics and claim_ok else "FAIL",
        f"rows={len(rows)} missing={missing} primary={primary} decision={decision} positive={positive} no_a_without_optics={no_a_without_optics}",
    )
    return summary


def validate_selection_and_optics(results: list[dict[str, str]], metric_summary: dict[str, Any] | None) -> None:
    sel_path = OUT / "selection_upgrade_decision_final.json"
    sel_md = OUT / "selection_upgrade_decision_final.md"
    if not sel_path.exists() or not sel_md.exists():
        add(results, "phase12_selection_upgrade_guard", "FAIL", "missing selection decision md/json")
    else:
        data = read_json(sel_path)
        reproduced = data.get("performance_reproduced_under_final_metric") is True
        upgraded = data.get("upgraded_to_main_analysis") is True
        stable = bool(metric_summary and metric_summary.get("selection_performance_reproduced_under_final_metric") is True)
        logic_ok = (upgraded == reproduced == stable) and (upgraded or data.get("main_result_selection_id") == "baseline")
        text = sel_md.read_text(encoding="utf-8", errors="ignore")
        wording_ok = "Forbidden, not claimed: selection best replaces baseline" in text
        add(
            results,
            "phase12_selection_upgrade_guard",
            "PASS" if logic_ok and wording_ok else "FAIL",
            f"reproduced={reproduced} upgraded={upgraded} metric_stable={stable} wording_ok={wording_ok}",
        )
        if not upgraded:
            add(results, "phase12_selection_not_upgraded", "WARN", "selection candidate remains secondary because final reproduction gate did not pass")

    optics_path = OUT / "optics_model_status_final.json"
    optics_md = OUT / "optics_model_status_final.md"
    if not optics_path.exists() or not optics_md.exists():
        add(results, "phase12_optics_status_guard", "FAIL", "missing final optics status md/json")
        return
    optics = read_json(optics_path)
    parametric = optics.get("status") == "PARAMETRIC_REQUIREMENTS_NOT_PRODUCTION"
    no_production_claim = (
        optics.get("real_or_production_optics_available") is False
        and optics.get("final_claim_level") == "PARAMETRIC_OPTICS_REQUIREMENT"
        and "Forbidden, not claimed" in optics.get("forbidden_final_claim", "")
    )
    decision_ok = not (metric_summary and metric_summary.get("final_decision_code") == "A" and parametric)
    add(
        results,
        "phase12_optics_status_guard",
        "PASS" if parametric and no_production_claim and decision_ok else "FAIL",
        f"status={optics.get('status')} no_production_claim={no_production_claim} decision_ok={decision_ok}",
    )
    if parametric:
        add(results, "phase12_real_optics_not_available", "WARN", "final optics model is parametric requirements, not production response")


def validate_ab_and_requirements(results: list[dict[str, str]], metric_summary: dict[str, Any] | None) -> None:
    ab_path = OUT / "AB_template_likelihood_final.csv"
    ab_json = OUT / "AB_template_likelihood_final.json"
    inj_path = OUT / "AB_injection_recovery_final.csv"
    req_path = OUT / "requirements_closure_final.csv"
    if not ab_path.exists() or not ab_json.exists() or not inj_path.exists():
        add(results, "phase12_AB_template_likelihood_final", "FAIL", "missing AB likelihood csv/json or injection csv")
    else:
        rows = read_csv(ab_path)
        js = read_json(ab_json)
        ids = {row["metric_id"] for row in rows}
        required_ids = {
            "A_flux_1.0e-4_baseline",
            "A_flux_1p0e-4_selection_candidate",
            "requirements_scan_Aeff_50cm2",
            "requirements_scan_Aeff_100cm2",
            "requirements_scan_exposure_2p5Ms",
        }
        numeric_ok = all(finite_positive(row.get("F3_required")) and float(row.get("TS_Asimov", "nan")) >= 0.0 for row in rows)
        claim_levels = {row.get("claim_level") for row in rows}
        expected_claim = {metric_summary.get("final_claim_level")} if metric_summary else claim_levels
        h_ok = js.get("H0") == "I_instr + B_diffuse" and js.get("H1") == "I_instr + B_diffuse + A_compact"
        b_ok = all(row.get("B_model_id") == "B_GC_DIFFUSE_BULGE_DISK" for row in rows)
        optics_ok = all(row.get("optics_id") == "PARAMETRIC_511_OPTICS_REQUIREMENTS_V1" for row in rows)
        add(
            results,
            "phase12_AB_template_likelihood_final",
            "PASS" if rows and required_ids.issubset(ids) and numeric_ok and claim_levels == expected_claim and h_ok and b_ok and optics_ok else "FAIL",
            f"rows={len(rows)} missing={sorted(required_ids - ids)} numeric_ok={numeric_ok} claim_levels={sorted(claim_levels)} h_ok={h_ok} b_ok={b_ok}",
        )

        inj = read_csv(inj_path)
        inj_ok = len(inj) == len(rows) and all(row.get("recovery_model") == "ASIMOV_REQUIREMENT_PROXY_NO_RANDOM_MC" for row in inj)
        add(
            results,
            "phase12_AB_injection_recovery_final",
            "PASS" if inj_ok else "FAIL",
            f"rows={len(inj)} expected={len(rows)}",
        )

    if not req_path.exists() or not (OUT / "optics_requirements_final.csv").exists():
        add(results, "phase12_requirements_closure_final", "FAIL", "missing requirements closure or optics requirements table")
        return
    req = read_csv(req_path)
    req_ids = {row["metric_id"] for row in req}
    needed = {"phase9_baseline_ERL", "phase10_baseline_count_only", "phase12_baseline_measured_ERL", "phase12_selection_best_measured_ERL"}
    req_ok = needed.issubset(req_ids) and all(finite_positive(row.get("required_response_gain")) for row in req)
    add(
        results,
        "phase12_requirements_closure_final",
        "PASS" if req_ok else "FAIL",
        f"rows={len(req)} missing={sorted(needed - req_ids)}",
    )


def validate_tables_figures_configs(results: list[dict[str, str]]) -> None:
    figures = [
        "metric_closure_phase9_phase10_phase12.png",
        "selection_decision_matrix.png",
        "optics_bandpass_or_requirement.png",
        "AB_template_overlap.png",
        "TS_vs_A_flux.png",
        "exposure_requirement_vs_flux.png",
    ]
    missing_figures = []
    for name in figures:
        path = OUT / "final_figures" / name
        if not path.exists() or path.stat().st_size <= 1000:
            missing_figures.append(name)
    add(
        results,
        "phase12_final_figures_present",
        "PASS" if not missing_figures else "FAIL",
        "all final figures are nonempty" if not missing_figures else "missing_or_tiny: " + ", ".join(missing_figures),
    )

    manifest = OUT / "artifact_manifest.csv"
    reports_manifest = R2 / "MANIFEST.tsv"
    manifest_ok = manifest.exists() and "12_FINAL_COMPACT_SOURCE_ANALYSIS/FINAL_DECISION.md" in reports_manifest.read_text(encoding="utf-8", errors="ignore")
    add(
        results,
        "phase12_artifact_manifest_registered",
        "PASS" if manifest_ok else "FAIL",
        f"artifact_manifest={manifest.exists()} reports_manifest={reports_manifest.exists()}",
    )


def validate_claim_control(results: list[dict[str, str]]) -> None:
    files = []
    for path in OUT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".json", ".yaml"}:
            continue
        rel_parts = path.relative_to(OUT).parts
        if rel_parts and rel_parts[0] == "validation":
            continue
        files.append(path)
    bad: list[str] = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for phrase in FORBIDDEN_PHRASES:
                if phrase.lower() in line.lower() and not line_allowed(line):
                    bad.append(f"{path.relative_to(OUT)}:{lineno}:{phrase}")
    final_decision = OUT / "FINAL_DECISION.md"
    readme = OUT / "README.md"
    final_ok = final_decision.exists() and "Final claim level:" in final_decision.read_text(encoding="utf-8", errors="ignore")
    no_phase13 = readme.exists() and "No `13_...` directory is required" in readme.read_text(encoding="utf-8", errors="ignore")
    add(
        results,
        "phase12_final_claim_control_guard",
        "PASS" if not bad and final_ok and no_phase13 else "FAIL",
        f"dangerous_hits={bad[:5]} final_ok={final_ok} no_phase13={no_phase13}",
    )


def write_validation_reports(results: list[dict[str, str]]) -> None:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    write_json(VALIDATION / "validate_final_workspace_summary.json", {"results": results})
    write_json(VALIDATION / "validate_final_metric_closure.json", {"results": [row for row in results if "metric" in row["check"] or "selection" in row["check"]]})
    write_json(VALIDATION / "validate_final_optics_status.json", {"results": [row for row in results if "optics" in row["check"] or "source" in row["check"] or "detector" in row["check"]]})
    write_json(VALIDATION / "validate_final_AB_likelihood.json", {"results": [row for row in results if "AB" in row["check"] or "requirements" in row["check"]]})
    write_json(VALIDATION / "validate_final_claim_control.json", {"results": [row for row in results if "claim" in row["check"] or "decision" in row["check"]]})


def validate(results: list[dict[str, str]]) -> None:
    validate_required_files(results)
    validate_manifests(results)
    validate_detector_and_source_cases(results)
    metric_summary = validate_metric_closure(results)
    validate_selection_and_optics(results, metric_summary)
    validate_ab_and_requirements(results, metric_summary)
    validate_tables_figures_configs(results)
    validate_claim_control(results)
    write_validation_reports(results)


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
