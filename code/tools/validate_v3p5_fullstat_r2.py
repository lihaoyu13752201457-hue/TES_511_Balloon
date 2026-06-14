#!/usr/bin/env python3
"""Validate the v3p5 fullstat R2 closure invariants."""

from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STEP05 = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1"
STEP06 = ROOT / "stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2"
STEP08 = ROOT / "stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2"
PERF = ROOT / "stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms"
COMPARE = ROOT / "outputs/reports/compare_511_narrow_1Ms_20260612"
CLOSURE = ROOT / "outputs/reports/v3p5_fullstat_performance_w2_closure_20260612"
SPATIAL = ROOT / "stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial"
BOUNDARY = ROOT / "outputs/reports/v3p5_boundary_closure_20260613"
DETECTOR_RESPONSE = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_response.json"
OPTICS_AEFF = ROOT / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
OPTICS_OUTPUT = ROOT / "stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_f10m_a1_r2_3seed"
I128_ANCHOR = ROOT / "stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.json"
PLACEHOLDER_READMES = [
    ROOT / "runs/step02_delayed_transport_mainline_div8_review_20260612/README.md",
    ROOT / "outputs/reports/validation_new_geo_re/README.md",
]
DECAY_AUDITS = [
    ROOT / "runs/step02_decay_source_v3p5_centerfinger_1of10/normalization_audit_day15.json",
    ROOT / "runs/step02_delay_fix_v3p5_centerfinger_1of10/normalization_audit_groundstate_fix.json",
    ROOT / "runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/normalization_audit_day15.json",
    ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/normalization_audit_groundstate_fix.json",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, problems: list[str]) -> None:
    if not condition:
        problems.append(message)


def close(value: float, expected: float, atol: float, message: str, problems: list[str]) -> None:
    require(abs(value - expected) <= atol, f"{message}: got {value}, expected {expected}", problems)


def validate_prompt_audit(problems: list[str]) -> None:
    audit = load_json(STEP05 / "prompt_normalization_audit.json")
    require(audit.get("status") == "PASS", "prompt audit is not PASS", problems)
    require(not audit.get("problems"), f"prompt audit problems: {audit.get('problems')}", problems)
    for row in audit["rows"]:
        tag = row["tag"]
        close(float(row["rate_times_tt_sum"]), 1.0, 1.0e-12, f"prompt rate*TT for {tag}", problems)
        require(int(row["tt_line_count"]) == int(row["files"]), f"prompt {tag} TT lines != files", problems)


def validate_headlines(problems: list[str]) -> None:
    step05 = load_json(STEP05 / "step05_v3p5_centerfinger_l1_response_summary.json")
    step06 = load_json(STEP06 / "step06_v3p5_centerfinger_fullstat_v2_summary.json")
    step08 = load_json(STEP08 / "step08_v3p5_centerfinger_time_dependent_summary.json")
    perf = load_json(PERF / "performance_curve_comparison_1Ms_summary.json")
    closure = load_json(CLOSURE / "v3p5_fullstat_performance_w2_closure_summary.json")
    w2 = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    checks06 = step06["checks"]
    checks08 = step08["checks"]
    v3p5 = perf["one_Ms"]["v3p5_W2"]

    require(step05["status"] == "PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2", "bad Step05 status", problems)
    require(step06["status"] == "PASS_V3P5_STEP06_TIME_AXIS_FULLSTAT_V2", "bad Step06 status", problems)
    require(step08["status"] == "PASS_V3P5_STEP08_TIME_DEPENDENT_FULLSTAT_V2", "bad Step08 status", problems)
    require(closure["status"] == "PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE", "bad closure status", problems)
    require(
        closure.get("authority_role") in {"CONSERVATIVE_CURRENT_RATE_AUTHORITY", "CONSERVATIVE_RADIALPROFILE_BASELINE_CROSSCHECK"},
        f"bad closure authority_role: {closure.get('authority_role')}",
        problems,
    )
    require(not closure.get("problems"), f"closure problems: {closure.get('problems')}", problems)

    close(float(w2["background_cps"]), 0.07295764410312272, 1.0e-15, "Step05 W2 background", problems)
    close(float(w2["signal_cps_at_reference_flux"]), 0.0011811656293957314, 1.0e-15, "Step05 W2 signal", problems)
    close(float(checks06["w2_dt_weighted_background_final_cps"]), 0.07304283195081326, 1.0e-15, "Step06 W2 mission background", problems)
    close(float(checks08["A_reference_w2_Z20d_time_dependent"]), 5.702213417976891, 1.0e-15, "Step08 Z20d", problems)
    close(float(checks08["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]), 5.261114904156606e-05, 1.0e-18, "Step08 flux20", problems)
    close(float(v3p5["flux_3sigma_ph_cm2_s"]), 6.823006741638457e-05, 1.0e-18, "1Ms v3p5 W2 flux", problems)


def validate_labels(problems: list[str]) -> None:
    paths = [
        STEP06 / "README.md",
        STEP06 / "step06_v3p5_centerfinger_fullstat_v2_summary.json",
        STEP08 / "step08_v3p5_centerfinger_time_dependent_summary.json",
        STEP08 / "t3_t5_summary.csv",
        CLOSURE / "v3p5_fullstat_performance_w2_closure_summary.json",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        require("1OF10" not in text, f"stale 1OF10 label in {rel(path)}", problems)


def validate_compare(problems: list[str]) -> None:
    text = (COMPARE / "compare_511_narrow_1Ms.md").read_text(encoding="utf-8")
    require("current requested TES_511_Balloon reduced prompt" not in text, "compare report still has stale current-requested wording", problems)
    require("TES_511_Balloon_delayed_only_aspiration" in text, "compare report missing delayed-only row", problems)
    require("TES_511_Balloon_v3p5_fullstat_W2_current" in text, "compare report missing current v3p5 row", problems)
    rows = list(csv.DictReader((COMPARE / "compare_511_narrow_1Ms_data.csv").open("r", encoding="utf-8", newline="")))
    by_case = {row["case"]: row for row in rows}
    close(float(by_case["TES_511_Balloon_delayed_only_aspiration"]["flux_3sigma_1Ms_ph_cm2_s"]), 2.9917526839687664e-05, 1.0e-18, "compare delayed-only flux", problems)
    close(float(by_case["TES_511_Balloon_v3p5_fullstat_W2_current"]["flux_3sigma_1Ms_ph_cm2_s"]), 6.823006741638457e-05, 1.0e-18, "compare current v3p5 flux", problems)


def validate_spatial_sidecar(problems: list[str]) -> None:
    spatial = load_json(SPATIAL / "v3p5_spatial_line_proxy_summary.json")
    detector = load_json(DETECTOR_RESPONSE)
    checks = spatial["checks"]
    frame = detector["inputs"]["spatial_frame"]
    require(spatial.get("status") == "PASS_V3P5_FULLSTAT_SPATIAL_LINE_PROXY", "bad v3p5 spatial sidecar status", problems)
    require(frame.get("axis_policy") == "v3p5_side_entry_tilt45", "detector response spatial frame is not v3p5 side-entry", problems)
    close(float(checks["signal_radius_r90_cm"]), 1.0516422148529696, 1.0e-15, "spatial spot_r90 radius", problems)
    close(float(checks["spot_r90_background_cps"]), 0.023251049574647638, 1.0e-15, "spatial spot_r90 background", problems)
    close(float(checks["spot_r90_Z20d_time_dependent"]), 8.175664736254516, 1.0e-15, "spatial spot_r90 Z20d time", problems)
    close(float(checks["spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s"]), 3.669426397460591e-05, 1.0e-18, "spatial spot_r90 flux20", problems)
    require(float(checks["signal_radius_r90_cm"]) < float(detector["inputs"]["spatial_frame"].get("be_radius_cm", 1.898)) if "be_radius_cm" in detector["inputs"]["spatial_frame"] else True, "spatial radius exceeds Be radius", problems)


def validate_boundary_closure_sidecars(problems: list[str]) -> None:
    path = BOUNDARY / "v3p5_boundary_closure_summary.json"
    if not path.exists():
        script = ROOT / "code/tools/build_v3p5_boundary_closure_report.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            problems.append(
                "failed to rebuild missing boundary closure sidecar "
                f"{rel(path)}: {result.stderr.strip() or result.stdout.strip()}"
            )
    require(path.exists(), f"missing boundary closure summary: {rel(path)}", problems)
    if not path.exists():
        return
    data = load_json(path)
    atmosphere = data["atmosphere_45deg_los"]
    likelihood = data["spatial_annular_likelihood"]
    exact = data["exact_position_delayed_source"]
    require(data.get("status") == "PASS_V3P5_BOUNDARY_CLOSURE_SIDECARS", "bad boundary closure status", problems)
    require(atmosphere.get("status") == "PASS_V3P5_45DEG_LOS_ATMOSPHERE_SIDECAR", "bad 45deg LOS sidecar status", problems)
    require(likelihood.get("status") == "PASS_V3P5_SPATIAL_ANNULAR_LIKELIHOOD_SIDECAR", "bad spatial likelihood sidecar status", problems)
    require(exact.get("status") == "SOURCE_AUDITS_PASS_TRANSPORT_NOT_RERUN", "exact-position boundary incorrectly marked", problems)
    require(
        exact.get("feasibility_status") == "EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_NOT_PRODUCTION_RERUN",
        "exact-position feasibility status should record smoke validation without production rerun",
        problems,
    )
    close(float(atmosphere["w2_hard_window"]["T_ref_slant"]), 0.6520342542373311, 1.0e-15, "45deg T_ref slant", problems)
    close(float(atmosphere["w2_hard_window"]["Z20d"]), 5.02544147909131, 1.0e-15, "45deg W2 Z20d", problems)
    close(float(atmosphere["spot_r90"]["Z20d"]), 7.205329171859502, 1.0e-15, "45deg spot_r90 Z20d", problems)
    close(float(likelihood["annular_likelihood_Z20d"]), 8.458041391463423, 1.0e-15, "annular likelihood Z20d", problems)
    close(float(likelihood["flux_3sigma_20d_ph_cm2_s"]), 3.5469204525622874e-05, 1.0e-18, "annular likelihood flux20", problems)
    require(float(likelihood["gain_vs_spot_r90_time_dependent"]) > 1.0, "annular likelihood does not exceed spot_r90 sidecar", problems)
    require("NOT_CLOSED" in exact.get("claim_level", ""), "exact-position transport boundary should remain not paper-closed", problems)
    smoke_readme = ROOT / exact.get("feasibility_evidence", {}).get("repo_smoke_readme", "")
    require(smoke_readme.exists(), f"missing exact-position smoke-test README: {rel(smoke_readme)}", problems)
    if smoke_readme.exists():
        smoke_text = smoke_readme.read_text(encoding="utf-8")
        require("PointSource" in smoke_text and "smoke test" in smoke_text.lower(), "exact-position smoke README lacks PointSource evidence wording", problems)


def validate_optics_per_seed(problems: list[str]) -> None:
    authority = load_json(OPTICS_AEFF)
    focal = authority["focal_stats"]
    be_radius_cm = float(focal["be_radius_cm"])
    summed_diffracted = 0
    summed_within = 0
    summed_outside = 0
    require((OPTICS_OUTPUT / "focal_crossings.csv").exists(), "missing combined f10m focal crossings", problems)
    require((OPTICS_OUTPUT / "seed_runs_summary.json").exists(), "missing f10m seed_runs_summary.json", problems)
    require((OPTICS_OUTPUT / "README.md").exists(), "missing f10m output README", problems)
    for seed in focal["per_seed"]:
        repo_path = ROOT / seed.get("repo_focal_crossings", "")
        require(seed.get("repo_focal_crossings"), f"seed {seed.get('seed')} missing repo_focal_crossings", problems)
        require(repo_path.exists(), f"seed {seed.get('seed')} repo focal crossings missing: {rel(repo_path)}", problems)
        if not repo_path.exists():
            continue
        diffracted = 0
        within = 0
        outside = 0
        with repo_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["source_tag"] != "laue_bfull_diffracted":
                    continue
                diffracted += 1
                r_cm = math.hypot(float(row["x_mm"]) / 10.0, float(row["y_mm"]) / 10.0)
                if r_cm <= be_radius_cm:
                    within += 1
                else:
                    outside += 1
        require(diffracted == int(seed["diffracted_rows"]), f"seed {seed['seed']} diffracted rows mismatch: got {diffracted}", problems)
        require(within == int(seed["within_be_rows"]), f"seed {seed['seed']} within-Be rows mismatch: got {within}", problems)
        require(outside == int(seed["outside_be_rows"]), f"seed {seed['seed']} outside-Be rows mismatch: got {outside}", problems)
        summed_diffracted += diffracted
        summed_within += within
        summed_outside += outside
    require(summed_diffracted == int(focal["diffracted_focal_rows"]), f"optics diffracted sum mismatch: got {summed_diffracted}", problems)
    require(summed_within == int(focal["within_be_rows"]), f"optics within-Be sum mismatch: got {summed_within}", problems)
    require(summed_outside == int(focal["outside_be_rows"]), f"optics outside-Be sum mismatch: got {summed_outside}", problems)


def validate_i128_anchor(problems: list[str]) -> None:
    anchor = load_json(I128_ANCHOR)
    checks = anchor["checks"]
    require(anchor.get("status") == "PASS_I128_R2_CURRENT_CHAIN_ANCHOR", "bad I-128 R2 anchor status", problems)
    close(float(checks["mainline_div8_i128_activity_bq"]), 66.62942376598845, 1.0e-12, "mainline div8 I-128 activity", problems)
    close(float(checks["v3p5_i128_activity_bq"]), 66.00180110381153, 1.0e-12, "v3p5 I-128 activity", problems)
    close(float(checks["v3p5_active_csi_mass_kg"]), 62.83369781500205, 1.0e-12, "v3p5 active CsI mass", problems)
    close(float(checks["v3p5_i128_specific_activity_bq_per_kg"]), 1.0504204495195741, 1.0e-15, "v3p5 I-128 Bq/kg", problems)
    retired = anchor.get("retired_anchor", {})
    require(retired.get("reason"), "I-128 anchor missing retired-anchor reason", problems)


def validate_decay_audits(problems: list[str]) -> None:
    for path in DECAY_AUDITS:
        data = load_json(path)
        require(data.get("status") == "PASS", f"{rel(path)} is not PASS", problems)
        require(not data.get("problems"), f"{rel(path)} problems: {data.get('problems')}", problems)
        for row in data["rows"]:
            files = int(row["files"])
            require(int(row["tt_files"]) == files, f"{rel(path)} {row['tag']} TT files != files", problems)
            require(int(row["tt_line_count"]) == files, f"{rel(path)} {row['tag']} TT lines != files", problems)


def validate_placeholder_readmes(problems: list[str]) -> None:
    for path in PLACEHOLDER_READMES:
        require(path.exists(), f"missing placeholder README: {rel(path)}", problems)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            require("placeholder" in text.lower() or "legacy" in text.lower(), f"placeholder README lacks boundary wording: {rel(path)}", problems)
            require("v3p5" in text or "R2" in text, f"placeholder README lacks current-authority pointer: {rel(path)}", problems)


def validate_current_docs(problems: list[str]) -> None:
    memory = (ROOT / "core_md/Project_Memory.md").read_text(encoding="utf-8")
    readme = (ROOT / "core_md/README.md").read_text(encoding="utf-8")
    workflow = (ROOT / "core_md/workflow.md").read_text(encoding="utf-8")
    require("stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md" in memory, "Project_Memory Fast Authority Map missing R2 I-128 anchor", problems)
    require("stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md" in readme, "README missing R2 I-128 anchor", problems)
    require("sec(45 deg)=1.414" in readme, "README missing 45 deg T_atm slant-column caveat", problems)
    require("sec(45 deg)=1.414" in workflow, "workflow missing 45 deg T_atm slant-column caveat", problems)
    workflow_head = "\n".join(workflow.splitlines()[:35])
    require("runs/step02_decay_source_equiv2602_aligned" not in workflow_head, "workflow head still points at equiv2602 aligned as current", problems)
    require("outputs/geometry/XZTES_ADR_v4c_mkflange_cm" not in workflow_head, "workflow head still points at XZTES as current", problems)


def validate_bad_values(problems: list[str]) -> None:
    pattern = re.compile(r"0\.486136|2\.20208|1\.36235e-4|1\.76837e-4|89\.3%")
    allowed = {
        ROOT / "core_md/Project_Memory.md",
        ROOT / "outputs/reports/claude_review_r2_execution_20260612/claude_review_r2_execution_report.md",
    }
    roots = [ROOT / "core_md", ROOT / "stepwise_maintenance", ROOT / "outputs/reports"]
    hits: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".md", ".json", ".csv"}:
                continue
            if path.name.startswith("focal_crossings") and OPTICS_OUTPUT in path.parents:
                continue
            if path in allowed:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                hits.append(rel(path))
    require(not hits, f"stale R2-bad values outside Project_Memory misquote block: {hits}", problems)


def main() -> int:
    problems: list[str] = []
    validate_prompt_audit(problems)
    validate_headlines(problems)
    validate_labels(problems)
    validate_compare(problems)
    validate_spatial_sidecar(problems)
    validate_boundary_closure_sidecars(problems)
    validate_optics_per_seed(problems)
    validate_i128_anchor(problems)
    validate_decay_audits(problems)
    validate_placeholder_readmes(problems)
    validate_current_docs(problems)
    validate_bad_values(problems)
    payload = {
        "status": "PASS_V3P5_FULLSTAT_R2_VALIDATION" if not problems else "FAIL_V3P5_FULLSTAT_R2_VALIDATION",
        "problems": problems,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
