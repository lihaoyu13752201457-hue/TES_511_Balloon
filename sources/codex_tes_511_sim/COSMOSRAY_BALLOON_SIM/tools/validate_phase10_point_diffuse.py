#!/usr/bin/env python3
"""Validate Phase 10 compact-source/diffuse-null discrimination artifacts."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports2.0" / "10_POINT_DIFFUSE_DISCRIMINATION"
CFG = ROOT / "configs" / "astro_source_cases"
ABC = ROOT / "reports2.0" / "09_SOURCE_CASES_ABC"
SCRIPTS = ROOT / "tools"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def validate(results: list[dict[str, str]]) -> None:
    summary_path = OUT / "phase10_summary.json"
    if not summary_path.exists():
        add(results, "phase10_summary", "FAIL", "missing reports2.0/10_POINT_DIFFUSE_DISCRIMINATION/phase10_summary.json")
        return
    summary = read_json(summary_path)
    add(
        results,
        "phase10_summary",
        "PASS"
        if summary.get("status") == "PASS_PHASE10_L1_POINT_DIFFUSE_SCAFFOLD"
        and summary.get("case_id") == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"
        and summary.get("claim_status") == "NOT_FINAL_ASTROPHYSICAL_CLAIM"
        else "FAIL",
        f"status={summary.get('status')} case_id={summary.get('case_id')} claim={summary.get('claim_status')}",
    )

    v2_path = CFG / "source_cases_511_ABC_v2.yaml"
    if v2_path.exists():
        cfg = yaml.safe_load(v2_path.read_text(encoding="utf-8"))
        cases = cfg.get("cases", [])
        case_ids = [case.get("case_id") for case in cases]
        a_cases = [case for case in cases if case.get("case_id") == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"]
        ok = (
            "A_GC_POINT_SgrA_anchor" not in case_ids
            and len(a_cases) == 1
            and a_cases[0].get("legacy_case_id") == "A_GC_POINT_SgrA_anchor"
            and a_cases[0].get("association_status") == "assumption_only_not_claimed"
            and "confirmed_SgrA_511_source" in a_cases[0].get("forbidden_claims", [])
        )
        add(results, "phase10_A_naming_not_overclaim", "PASS" if ok else "FAIL", f"case_ids={case_ids}")
    else:
        add(results, "phase10_A_naming_not_overclaim", "FAIL", f"missing {rel(v2_path)}")

    manifest_path = OUT / "source_case_manifest_phase10.csv"
    manifest = read_csv(manifest_path) if manifest_path.exists() else []
    b_rows = [r for r in manifest if r.get("case_id") == "B_GC_DIFFUSE_BULGE_DISK"]
    b_source_files = sorted((ROOT / "run_configs" / "astro_cases").glob("*B_GC_DIFFUSE*.source"))
    b_ok = (
        len(b_rows) == 1
        and b_rows[0].get("run_status") == "SKIPPED_BY_DESIGN"
        and not b_rows[0].get("source_file")
        and b_rows[0].get("claim_status") == "NO_FOCAL_SPOT_SOURCE_WITHOUT_RAYTRACE"
        and not b_source_files
    )
    add(results, "phase10_B_no_total_flux_to_point_source", "PASS" if b_ok else "FAIL", f"B_rows={len(b_rows)} B_source_files={len(b_source_files)}")

    fov_path = OUT / "B_diffuse_fov_scan.csv"
    if fov_path.exists():
        fov = read_csv(fov_path)
        rates = [float(r["diffuse_cps_proxy"]) for r in fov]
        radii = [float(r["fov_radius_arcmin"]) for r in fov]
        zero_ok = radii and radii[0] == 0.0 and abs(rates[0]) < 1e-30
        mono_ok = all(b >= a - 1e-30 for a, b in zip(rates, rates[1:]))
        add(results, "phase10_B_fov_zero_and_monotonic", "PASS" if zero_ok and mono_ok else "FAIL", f"r0={radii[:1]} rate0={rates[:1]} monotonic={mono_ok}")
    else:
        add(results, "phase10_B_fov_zero_and_monotonic", "FAIL", f"missing {rel(fov_path)}")

    abc_summary_path = ABC / "source_case_summary.json"
    if abc_summary_path.exists():
        abc_summary = read_json(abc_summary_path)
        e_obs = float(abc_summary.get("checks", {}).get("C_redshift_z0p10_observed_energy_keV", 0.0))
        expected = 511.0 / 1.10
        c_status = str(abc_summary.get("checks", {}).get("C_redshift_bandpass_status", ""))
        ok = math.isclose(e_obs, expected, rel_tol=0.0, abs_tol=1e-9) and "REDSHIFTED_BELOW_480" in c_status
        add(results, "phase10_C_redshift_formula_guard", "PASS" if ok else "FAIL", f"Eobs={e_obs} expected={expected} status={c_status}")
    else:
        add(results, "phase10_C_redshift_formula_guard", "FAIL", f"missing {rel(abc_summary_path)}")

    c_rows = [r for r in manifest if r.get("case_id") == "C_V404_2015_TRANSIENT_BENCHMARK"]
    a_rows = [r for r in manifest if r.get("case_id") == "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"]
    manifest_ok = (
        len(a_rows) >= 2
        and all(r.get("run_status") == "CANDIDATE_NOT_RUN" for r in a_rows)
        and len(c_rows) == 1
        and c_rows[0].get("claim_status") == "NOT_SUPPORTED_PRODUCTION"
        and not any(r.get("run_status") == "RUN_COMPLETE" for r in manifest)
    )
    add(results, "phase10_manifest_status_guard", "PASS" if manifest_ok else "FAIL", f"A={len(a_rows)} C={len(c_rows)} run_complete={sum(r.get('run_status') == 'RUN_COMPLETE' for r in manifest)}")

    schema_path = CFG / "optics_response_511_schema.yaml"
    placeholder_path = CFG / "optics_response_511_placeholder.yaml"
    if schema_path.exists() and placeholder_path.exists():
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        placeholder = yaml.safe_load(placeholder_path.read_text(encoding="utf-8"))
        required_keys = {"metadata", "energy_grid_keV", "aeff_cm2", "bandpass", "psf", "fov", "diffuse_focal_map", "pointing_visibility", "claim_control"}
        ok = (
            required_keys.issubset(schema)
            and required_keys.issubset(placeholder)
            and placeholder.get("metadata", {}).get("status") == "PLACEHOLDER"
            and "final_point_diffuse_imaging_discrimination" in placeholder.get("claim_control", {}).get("forbidden_claims", [])
        )
        add(results, "phase10_placeholder_optics_guard", "PASS" if ok else "FAIL", f"schema_keys={sorted(schema.keys())} placeholder_status={placeholder.get('metadata', {}).get('status')}")
    else:
        missing = [rel(p) for p in [schema_path, placeholder_path] if not p.exists()]
        add(results, "phase10_placeholder_optics_guard", "FAIL", "missing: " + ", ".join(missing))

    point_path = OUT / "point_diffuse_discrimination.csv"
    point_json = OUT / "point_diffuse_discrimination.json"
    if point_path.exists() and point_json.exists():
        point_rows = read_csv(point_path)
        point_summary = read_json(point_json)
        modes = {r.get("mode") for r in point_rows}
        selections = {r.get("selection_id") for r in point_rows}
        f3_errors = []
        for row in point_rows:
            flux = float(row["A_flux_ph_cm2_s"])
            signal_cps = float(row["A_expected_cps"])
            response = signal_cps / flux if flux > 0 else 0.0
            background = float(row["total_background_cps"])
            penalty = float(row["template_confusion_penalty"])
            expected_f3 = 3.0 * math.sqrt(background) / (response * math.sqrt(1.0e6)) * penalty if response > 0 and background > 0 else float("nan")
            got_f3 = float(row["F3_ph_cm2_s"])
            if not math.isclose(got_f3, expected_f3, rel_tol=1e-10, abs_tol=1e-14):
                f3_errors.append((row.get("selection_id"), row.get("mode"), row.get("A_spectrum_model"), got_f3, expected_f3))
        ok = (
            point_summary.get("claim_status") == "NOT_FINAL_ASTROPHYSICAL_CLAIM"
            and point_summary.get("optics_status") == "PLACEHOLDER_OPTICS"
            and {"count_only_L1", "uniform_focal_conservative", "psf_like_worst_case"}.issubset(modes)
            and {"baseline", "selection_only_best_pending_measured_audit"}.issubset(selections)
            and all(r.get("claim_status") == "NOT_FINAL_ASTROPHYSICAL_CLAIM" for r in point_rows)
            and all(r.get("F3_method") == "conservative_counting_from_response_background" for r in point_rows)
            and not f3_errors
        )
        add(results, "phase10_detection_claim_guard", "PASS" if ok else "FAIL", f"rows={len(point_rows)} modes={sorted(modes)} selections={sorted(selections)} f3_formula_errors={len(f3_errors)}")
    else:
        add(results, "phase10_detection_claim_guard", "FAIL", "missing point/diffuse discrimination outputs")

    audit_path = OUT / "selection_best_measured_energy_audit.csv"
    audit_json = OUT / "selection_best_measured_energy_audit.json"
    if audit_path.exists() and audit_json.exists():
        audit = read_csv(audit_path)
        audit_summary = read_json(audit_json)
        status = audit_summary.get("status", "")
        best_broad = [
            r for r in audit
            if r.get("selection_id") == "bgo30_r18_cent_single_top1_L5_keep"
            and r.get("window") == "broad_480_550"
            and r.get("energy_basis") == "measured"
        ]
        baseline_broad = [
            r for r in audit
            if r.get("selection_id") == "baseline"
            and r.get("window") == "broad_480_550"
            and r.get("energy_basis") == "measured"
        ]
        if status == "PASS_SELECTION_BEST_MEASURED_ENERGY_AUDITED":
            ok = (
                len(best_broad) == 1
                and len(baseline_broad) == 1
                and best_broad[0].get("pass_status") == "PASS_MEASURED_ENERGY_AUDIT"
                and float(best_broad[0]["F3_ph_cm2_s"]) < float(baseline_broad[0]["F3_ph_cm2_s"])
                and audit_summary.get("claim_status") == "L1_MEASURED_ENERGY_AUDIT_NOT_FINAL_FLIGHT_SENSITIVITY"
            )
        else:
            ok = status == "FAIL_KEEP_BASELINE_PRIMARY" and "baseline remains primary" in audit_summary.get("promotion_policy", "")
        add(results, "phase10_selection_best_measured_energy_guard", "PASS" if ok else "FAIL", f"status={status} rows={len(audit)}")
    else:
        add(results, "phase10_selection_best_measured_energy_guard", "FAIL", "missing measured-energy audit outputs")

    matrix_path = OUT / "optics_requirements_matrix.csv"
    if matrix_path.exists():
        matrix = read_csv(matrix_path)
        reqs = {r.get("requirement_id") for r in matrix}
        needed = {"REQ_AEFF_E_THETA", "REQ_BANDPASS", "REQ_PSF", "REQ_FOV_OFFAXIS", "REQ_DIFFUSE_FOCAL_MAP", "REQ_POINTING", "REQ_ATMOSPHERE"}
        ok = len(matrix) >= 10 and needed.issubset(reqs) and all(r.get("production_requirement") for r in matrix)
        add(results, "phase10_optics_schema_completeness", "PASS" if ok else "FAIL", f"rows={len(matrix)} missing={sorted(needed - reqs)}")
    else:
        add(results, "phase10_optics_schema_completeness", "FAIL", f"missing {rel(matrix_path)}")

    v404_path = OUT / "v404_literature_anchor_table.csv"
    if v404_path.exists():
        rows = read_csv(v404_path)
        status_set = {r.get("assumption_status") for r in rows}
        usable = {r.get("usable_for_transport") for r in rows}
        ok = "LITERATURE_ANCHORING_REQUIRED" in status_set and "NO_PRODUCTION_TRANSPORT_YET" in usable
        add(results, "phase10_V404_anchor_status_guard", "PASS" if ok else "FAIL", f"statuses={sorted(status_set)} usable={sorted(usable)}")
    else:
        add(results, "phase10_V404_anchor_status_guard", "FAIL", f"missing {rel(v404_path)}")

    required = [
        OUT / "README.md",
        OUT / "claim_control_phase10.md",
        OUT / "phase10_summary.json",
        OUT / "point_diffuse_discrimination.csv",
        OUT / "selection_best_measured_energy_audit.csv",
        OUT / "B_diffuse_fov_scan.csv",
        OUT / "source_case_manifest_phase10.csv",
        OUT / "optics_requirements_matrix.csv",
        OUT / "figures" / "A_vs_B_expected_counts.png",
        OUT / "figures" / "A_vs_B_detection_probability.png",
        OUT / "figures" / "B_diffuse_foreground_fov_scan.png",
        OUT / "figures" / "selection_best_true_vs_measured.png",
        OUT / "figures" / "phase10_claim_boundary_map.png",
        OUT / "packaged_inputs" / "source_cases_511_ABC_v2.yaml",
        OUT / "packaged_inputs" / "optics_response_511_schema.yaml",
        OUT / "packaged_inputs" / "optics_response_511_placeholder.yaml",
        SCRIPTS / "make_511_phase10_point_diffuse_report.py",
        SCRIPTS / "validate_phase10_point_diffuse.py",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    add(results, "phase10_artifacts_exist", "PASS" if not missing else "FAIL", "all required Phase 10 artifacts present" if not missing else "missing: " + ", ".join(missing))


def write_reports(results: list[dict[str, str]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase10_validation.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    lines = ["# Phase 10 Validation", ""]
    for row in results:
        lines.append(f"- {row['status']}: {row['check']} - {row['details']}")
    (OUT / "phase10_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    write_reports(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
