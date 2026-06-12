#!/usr/bin/env python3
"""Validate the v3p5 fullstat R2 closure invariants."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STEP05 = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1"
STEP06 = ROOT / "stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2"
STEP08 = ROOT / "stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2"
PERF = ROOT / "stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms"
COMPARE = ROOT / "outputs/reports/compare_511_narrow_1Ms_20260612"
CLOSURE = ROOT / "outputs/reports/v3p5_fullstat_performance_w2_closure_20260612"
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


def validate_decay_audits(problems: list[str]) -> None:
    for path in DECAY_AUDITS:
        data = load_json(path)
        require(data.get("status") == "PASS", f"{rel(path)} is not PASS", problems)
        require(not data.get("problems"), f"{rel(path)} problems: {data.get('problems')}", problems)
        for row in data["rows"]:
            files = int(row["files"])
            require(int(row["tt_files"]) == files, f"{rel(path)} {row['tag']} TT files != files", problems)
            require(int(row["tt_line_count"]) == files, f"{rel(path)} {row['tag']} TT lines != files", problems)


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
    validate_decay_audits(problems)
    validate_bad_values(problems)
    payload = {
        "status": "PASS_V3P5_FULLSTAT_R2_VALIDATION" if not problems else "FAIL_V3P5_FULLSTAT_R2_VALIDATION",
        "problems": problems,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
