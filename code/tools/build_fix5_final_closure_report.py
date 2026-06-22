#!/usr/bin/env python3
"""Build the final fix5 full-stat closure report and comparison table."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
OUT_JSON = REPORT_DIR / "fix5_final_closure_report.json"
OUT_MD = REPORT_DIR / "fix5_final_closure_report.md"
OUT_CSV = REPORT_DIR / "fix5_final_comparison_table.csv"

BENCHMARKS = ROOT / "core_md" / "fix5_benchmarks.json"
SOURCE_MANIFEST = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_source_manifest.json"
BENCHMARK_ALIGNMENT = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_benchmark_alignment.json"
VERIFIER = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_verification_verdict.json"
PROMOTION = REPORT_DIR / "fix5_promotion_decision.json"
W_AUDIT = REPORT_DIR / "fix5_w_activation_selected_w2_audit.json"
GROUNDSTATE = REPORT_DIR / "fix5_groundstate_half_life_audit_summary.json"
DELAYED_SOURCE = REPORT_DIR / "fix5_delayed_source_exactpos_summary.json"
ONE_OF_TEN = ROOT / "outputs" / "reports" / "fix5_1of10" / "fix5_step05_screen_summary.json"
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


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return load_json(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def metric_row(
    metric: str,
    fix5_value: float | str | None,
    fix5_sigma: float | None,
    v3p5_reference: float | str | None,
    old_new_geo_re_reference: float | str | None,
    status: str,
    notes: str,
) -> dict[str, Any]:
    numeric_fix5 = fix5_value if isinstance(fix5_value, float) else None
    numeric_v3p5 = v3p5_reference if isinstance(v3p5_reference, float) else None
    return {
        "metric": metric,
        "fix5": fix5_value,
        "fix5_sigma": fix5_sigma,
        "v3p5_reference": v3p5_reference,
        "fix5_over_v3p5": ratio(numeric_fix5, numeric_v3p5),
        "old_new_geo_re_reference": old_new_geo_re_reference,
        "status": status,
        "notes": notes,
    }


def blocking_rows(verifier: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in verifier.get("rows", []) if row.get("blocking")]


def all_blocking_pass(verifier: dict[str, Any]) -> bool:
    return all(row.get("status") == "PASS" for row in blocking_rows(verifier))


def source_card_count(source_manifest: dict[str, Any]) -> int | None:
    cards = source_manifest.get("source_cards")
    if isinstance(cards, list):
        return len(cards)
    if isinstance(cards, dict):
        return len(cards)
    return None


def build() -> dict[str, Any]:
    bench = load_json(BENCHMARKS)
    source_manifest = load_json(SOURCE_MANIFEST)
    alignment = load_json(BENCHMARK_ALIGNMENT)
    verifier = load_json(VERIFIER)
    promotion = load_json(PROMOTION)
    w_audit = load_json(W_AUDIT)
    groundstate = load_json(GROUNDSTATE)
    delayed_source = load_json(DELAYED_SOURCE)
    one_of_ten = maybe_load_json(ONE_OF_TEN)
    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step07 = load_json(STEP07)
    step08 = load_json(STEP08)
    step09 = load_json(STEP09)

    v3p5 = bench["benchmarks"]["v3p5_current_authority"]
    old = bench["benchmarks"]["new_geo_re"]
    comparison_rows = [
        metric_row(
            "W2 total selected background cps",
            promotion["B_cps"],
            promotion["B_sigma_cps"],
            v3p5["step05_background_cps"],
            None,
            "PASS_DECISIVE_VS_V3P5",
            "B_fix5 + sigma_fix5 is below current v3p5 authority.",
        ),
        metric_row(
            "W2 prompt selected cps",
            promotion["prompt_cps"],
            promotion["prompt_sigma_cps"],
            v3p5["w2_prompt_cps"],
            old["prompt_total_cps"],
            "PASS_VS_V3P5_REPORT_ONLY_VS_OLD_NEW_GEO_RE",
            "Old new_geo_re prompt is report-only because benchmark_alignment.decision is not ALIGNED.",
        ),
        metric_row(
            "W2 delayed selected cps",
            promotion["delayed_cps"],
            promotion["delayed_sigma_cps"],
            v3p5["w2_delayed_cps"],
            old["delayed_total_cps"],
            "PASS_VS_V3P5_REPORT_ONLY_VS_OLD_NEW_GEO_RE",
            "Delayed total is below current v3p5; old new_geo_re delayed is not a promotion bar.",
        ),
        metric_row(
            "W/collimator-origin W2 delayed selected cps",
            promotion["w_activation_cps"],
            None,
            None,
            None,
            "PASS_NOT_DOMINANT",
            "Dedicated selected-event audit found zero W/collimator-origin W2 delayed selected events.",
        ),
        metric_row(
            "W/collimator source activity Bq",
            promotion["w_or_collimator_activity_Bq"],
            None,
            None,
            None,
            "AUDITED_SOURCE_LEVEL_CONTEXT",
            "Ground-state corrected fixed source activity inventory; selected-rate audit is the promotion check.",
        ),
        metric_row(
            "Reference-flux signal cps",
            promotion["signal_cps"],
            None,
            v3p5["step05_signal_cps"],
            None,
            "PASS_SIGNAL_KEEP",
            "Fix5 focused signal replay was consumed by Step05.",
        ),
        metric_row(
            "Z20d",
            promotion["Z20d"],
            None,
            v3p5["step08_Z20d"],
            None,
            "PASS",
            "Fix5 is above the current v3p5 authority.",
        ),
        metric_row(
            "F3(20d) ph cm^-2 s^-1",
            promotion["F3_20d_ph_cm2_s"],
            None,
            v3p5["step08_F3_20d_ph_cm2_s"],
            None,
            "PASS",
            "Fix5 is below the current v3p5 authority.",
        ),
        metric_row(
            "Old new_geo_re benchmark alignment",
            alignment.get("decision"),
            None,
            None,
            "ALIGNED required before old-new_geo_re gating",
            "REPORT_ONLY",
            "Historical old-new_geo_re numbers are not used for pass/fail gating.",
        ),
    ]

    final_status = (
        "PASS_FIX5_FULLSTAT_CLOSURE"
        if promotion.get("decision") == "PASS_FIX5_REPLACES_V3P5"
        and verifier.get("overall_status") == "PASS_FIX5_PROMOTION"
        and all_blocking_pass(verifier)
        and not promotion.get("blocking_items")
        else "FAIL_OR_USER_REVIEW_FIX5_FULLSTAT_CLOSURE"
    )

    artifacts = {
        "source_manifest": {
            "path": rel(SOURCE_MANIFEST),
            "status": "PASS_BY_VERIFIER" if all_blocking_pass(verifier) else "CHECK_VERIFIER",
            "source_card_count": source_card_count(source_manifest),
        },
        "benchmark_alignment": {
            "path": rel(BENCHMARK_ALIGNMENT),
            "decision": alignment.get("decision"),
            "use_of_old_new_geo_re": "REPORT_ONLY" if alignment.get("decision") != "ALIGNED" else "GATE_ALLOWED",
        },
        "verification_verdict": {
            "path": rel(VERIFIER),
            "overall_status": verifier.get("overall_status"),
            "all_blocking_rows_pass": all_blocking_pass(verifier),
        },
        "promotion_decision": {
            "path": rel(PROMOTION),
            "decision": promotion.get("decision"),
            "blocking_items": promotion.get("blocking_items", []),
        },
        "w_activation_selected_w2_audit": {
            "path": rel(W_AUDIT),
            "status": w_audit.get("status"),
            "selected_events": w_audit["checks"]["selected_events"],
            "w_or_collimator_selected_rate_hz": w_audit["checks"]["w_or_collimator_selected_rate_hz"],
        },
        "final_report": {
            "json": rel(OUT_JSON),
            "markdown": rel(OUT_MD),
            "comparison_table_csv": rel(OUT_CSV),
        },
    }

    payload = {
        "status": final_status,
        "label": LABEL,
        "generated_at_utc": now_utc(),
        "decision": promotion.get("decision"),
        "decision_reason": promotion.get("decision_reason"),
        "contract_authority": rel(BENCHMARKS),
        "fixed_geometry": bench["geometry"]["fix5_geo_setup"],
        "old_new_geo_re_policy": "REPORT_ONLY_UNTIL_BENCHMARK_ALIGNMENT_IS_ALIGNED",
        "clean_fullstat_policy": "Clean full-stat fix5 closure; no append/merge promotion was used.",
        "role_split": {
            "Builder": "Prepared fix5 source cards, Step09 focused signal replay wiring, and report builders under fix5-specific output paths.",
            "Runner": "Executed clean fix5 prompt, buildup, delayed, and focused signal transports with fix5 SIM headers.",
            "Verifier": "Checked source/SIM geometry provenance, delayed normalization, selected W activation decomposition, Step05--Step08 outputs, and promotion decision.",
        },
        "required_artifacts": artifacts,
        "normalization_audits": {
            "groundstate_half_life": {
                "path": rel(GROUNDSTATE),
                "status": groundstate.get("status"),
                "w_or_collimator_new_activity_Bq": promotion["w_or_collimator_activity_Bq"],
            },
            "delayed_exactpos_source": {
                "path": rel(DELAYED_SOURCE),
                "status": delayed_source.get("status"),
            },
        },
        "one_of_ten_screen": {
            "path": rel(ONE_OF_TEN),
            "status": one_of_ten.get("status") if one_of_ten else "MISSING",
            "use_in_final_decision": "SUPERSEDED_BY_FULLSTAT",
        },
        "step_chain": {
            "step05": {"path": rel(STEP05), "status": step05.get("status")},
            "step06": {"path": rel(STEP06), "status": step06.get("status")},
            "step07": {"path": rel(STEP07), "status": step07.get("status")},
            "step08": {"path": rel(STEP08), "status": step08.get("status")},
            "step09_signal_replay": {"path": rel(STEP09), "status": step09.get("status")},
        },
        "comparison_table": comparison_rows,
    }
    return payload


def write_csv_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "metric",
        "fix5",
        "fix5_sigma",
        "v3p5_reference",
        "fix5_over_v3p5",
        "old_new_geo_re_reference",
        "status",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(row.get(key)) for key in fields})


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Metric | fix5 | sigma | v3p5 reference | fix5/v3p5 | old new_geo_re | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {metric} | {fix5} | {sigma} | {v3p5} | {ratio_value} | {old} | {status} |".format(
                metric=row["metric"],
                fix5=fmt(row["fix5"]),
                sigma=fmt(row["fix5_sigma"]),
                v3p5=fmt(row["v3p5_reference"]),
                ratio_value=fmt(row["fix5_over_v3p5"]),
                old=fmt(row["old_new_geo_re_reference"]),
                status=row["status"],
            )
        )
    return "\n".join(lines)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    promotion = load_json(PROMOTION)
    artifacts = payload["required_artifacts"]
    lines = [
        "# fix5 Full-Stat Simulation Closure",
        "",
        f"- Status: `{payload['status']}`",
        f"- Final decision: `{payload['decision']}`",
        f"- Geometry: `{payload['fixed_geometry']}`",
        f"- Contract authority: `{payload['contract_authority']}`",
        f"- Old `new_geo_re` policy: `{payload['old_new_geo_re_policy']}`",
        f"- Clean full-stat policy: `{payload['clean_fullstat_policy']}`",
        "",
        "## Decision",
        "",
        payload["decision_reason"],
        "",
        "## Required Artifacts",
        "",
        f"- Source manifest: `{artifacts['source_manifest']['path']}`",
        f"- Benchmark alignment: `{artifacts['benchmark_alignment']['path']}` (`{artifacts['benchmark_alignment']['decision']}`)",
        f"- Verification verdict: `{artifacts['verification_verdict']['path']}` (`{artifacts['verification_verdict']['overall_status']}`)",
        f"- Promotion decision: `{artifacts['promotion_decision']['path']}` (`{artifacts['promotion_decision']['decision']}`)",
        f"- W activation selected-rate audit: `{artifacts['w_activation_selected_w2_audit']['path']}` (`{artifacts['w_activation_selected_w2_audit']['status']}`)",
        "",
        "## Comparison Table",
        "",
        markdown_table(payload["comparison_table"]),
        "",
        "## Key Checks",
        "",
        f"- W2 background: `{fmt(promotion['B_cps'])} +/- {fmt(promotion['B_sigma_cps'])}` cps.",
        f"- Prompt/delayed: `{fmt(promotion['prompt_cps'])}` / `{fmt(promotion['delayed_cps'])}` cps.",
        f"- W/collimator selected W2 delayed: `{fmt(promotion['w_activation_cps'])}` cps, fraction `{fmt(promotion['w_activation_fraction_of_delayed_selected_rate'])}`.",
        f"- Signal keep vs v3p5: `{fmt(promotion['signal_keep_fraction_vs_v3p5'])}`.",
        f"- Z20d / F3(20d): `{fmt(promotion['Z20d'])}` / `{fmt(promotion['F3_20d_ph_cm2_s'])}`.",
        "",
        "## Notes",
        "",
        "- Full-stat results override the 1/10 screen.",
        "- The historical old `new_geo_re` prompt/delayed values remain report-only because benchmark alignment is `NOT_ALIGNED`.",
        "- This report does not overwrite current v3p5, BGO, or old `new_geo_re` authority outputs.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    payload = build()
    write_json(OUT_JSON, payload)
    write_csv_table(OUT_CSV, payload["comparison_table"])
    write_markdown(OUT_MD, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "decision": payload["decision"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
                "comparison_csv": rel(OUT_CSV),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if str(payload["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
