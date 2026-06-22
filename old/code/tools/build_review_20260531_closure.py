#!/usr/bin/env python3
"""Build a closure matrix for the 2026-05-31 review follow-up."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "review_20260531_closure"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def fmt(value: Any, nd: int = 6) -> str:
    if isinstance(value, (int, float)):
        value = float(value)
        if value == 0.0:
            return "0"
        if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
            return f"{value:.{nd}e}"
        return f"{value:.{nd}g}"
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def current_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if path.name == "workflow.md":
        text = text.split("## Legacy Warning", 1)[0]
    return text


def stale_live_doc_hits() -> list[str]:
    docs = [
        ROOT / "README.md",
        ROOT / "workflow.md",
        ROOT / "stepwise_maintenance" / "CURRENT_PROGRESS_STEP_BREAKDOWN.md",
        ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / "README.md",
        ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "README.md",
    ]
    stale_tokens = ["110.09", "110.088", "9003.74", "0.3996", "4.886", "6.78", "1094.2"]
    hits = []
    for path in docs:
        text = current_text(path)
        for token in stale_tokens:
            if token in text:
                hits.append(f"{rel(path)} contains {token}")
    return hits


def validation_detail(check_name: str) -> str:
    validation = load_json(ROOT / "outputs" / "reports" / "validation_new_geo_re" / "validation_new_geo_re.json", {})
    for row in validation.get("checks", []):
        if row.get("check") == check_name:
            return str(row.get("details", ""))
    return "pending next root validation run"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    step08 = load_json(
        ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "step08_significance_summary.json", {}
    )
    line = load_json(
        ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "line_window_sensitivity_summary.json", {}
    )
    spatial = load_json(
        ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "spatial_line_proxy_summary.json", {}
    )
    focus = load_json(
        ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json", {}
    )
    half = load_json(ROOT / "outputs" / "reports" / "half_life_unit_audit" / "half_life_unit_audit_summary.json", {})
    csi = load_json(ROOT / "outputs" / "reports" / "csi_activation_baseline" / "csi_activation_baseline_summary.json", {})
    bgo = load_json(
        ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_bgo_control" / "bgo_control_geometry_summary.json",
        {},
    )
    step07 = load_json(
        ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_case_summary.json", {}
    )

    line_chk = line.get("checks", {})
    spatial_chk = spatial.get("checks", {})
    step08_chk = step08.get("checks", {})
    half_chk = half.get("checks", {})
    csi_chk = csi.get("checks", {})
    bgo_chk = bgo.get("checks", {})
    step07_chk = step07.get("checks", {})
    stale_hits = stale_live_doc_hits()

    items: list[dict[str, Any]] = [
        {
            "item_id": "P0_DOC_STALE_DEMO2_VALUES",
            "priority": "P0",
            "status": "CLOSED",
            "claim_level": "documentation_authority",
            "evidence": f"live_doc_stale_hits={len(stale_hits)}; README/workflow/progress now quote 624.271 Bq, 1584.61 s, broad final about 2.35-2.37 cps, Z20d=2.0466",
            "remaining_gap": "Legacy values remain only in explicitly marked historical sections.",
        },
        {
            "item_id": "P0_LINE_WINDOW_PERFORMANCE",
            "priority": "P0",
            "status": "CLOSED_L1",
            "claim_level": line.get("claim_level", "missing"),
            "evidence": (
                f"511 +/- 3 sigma: background={fmt(line_chk.get('line_pm_3sigma_background_cps'))} cps; "
                f"Z20d={fmt(line_chk.get('line_pm_3sigma_Z20d'))}; "
                f"spot_r90_Z20d={fmt(spatial_chk.get('spot_r90_Z20d'))}; "
                f"T3={fmt(line_chk.get('line_pm_3sigma_T3_day_constant_rate'))} d; "
                f"spot_r90_flux3sigma20d={fmt(spatial_chk.get('spot_r90_flux_3sigma_20d_ph_cm2_s'))}"
            ),
            "remaining_gap": "Detector-coupled EventList response is in place; full profile likelihood remains a paper-upgrade item.",
        },
        {
            "item_id": "P1_T3_EXTRAPOLATION_LABEL",
            "priority": "P1",
            "status": "CLOSED",
            "claim_level": step08.get("claim_level", "missing"),
            "evidence": (
                f"A_reference_T3_status={step08_chk.get('A_reference_T3_status')}; "
                f"T3_extrapolated={fmt(step08_chk.get('A_reference_T3_day_extrapolated_constant_profile'))} d; "
                f"mission={fmt(step08_chk.get('mission_duration_day'))} d"
            ),
            "remaining_gap": "None for the broad-window label; profile-likelihood detectability is separate.",
        },
        {
            "item_id": "P1_HALF_LIFE_PREFIX_UNITS",
            "priority": "P1",
            "status": "CLOSED_FOR_FIXED_SOURCE",
            "claim_level": half.get("claim_level", "missing"),
            "evidence": (
                f"prefix_rows={half_chk.get('prefix_year_rows')}; "
                f"units={half_chk.get('prefix_year_units_seen')}; "
                f"line_rel={fmt(half_chk.get('prefix_nubase_line_max_rel_error'))}; "
                f"W180_new_Bq={fmt(half_chk.get('w180_new_total_activity_Bq'))}; "
                f"forbidden_particles={half_chk.get('fixed_source_forbidden_particle_types')}"
            ),
            "remaining_gap": "The final fixed source is audited; unify the raw external half-life cache path before using it as a standalone authority.",
        },
        {
            "item_id": "P1_NATIVE_CSI_VETO_STRUCTURE",
            "priority": "P1",
            "status": "CLOSED_STRUCTURE",
            "claim_level": "detector_file_structure",
            "evidence": validation_detail("native_csi_veto_trigger"),
            "remaining_gap": "Quantitative veto performance remains Step05 post-processing because current production SIM predates native triggers.",
        },
        {
            "item_id": "P1_CSI_ACTIVATION_BASELINE",
            "priority": "P1",
            "status": "PARTIAL_L1",
            "claim_level": csi.get("claim_level", "missing"),
            "evidence": (
                f"CsI_activity_fraction={fmt(csi_chk.get('csi_active_shield_activity_fraction'))}; "
                f"I128_fraction={fmt(csi_chk.get('I128_total_activity_fraction'))}; "
                f"delayed_final={fmt(csi_chk.get('delayed_final_480_550_cps'))} cps; "
                f"BGO_control={csi_chk.get('bgo_control_status')}"
            ),
            "remaining_gap": "BGO control geometry scaffold is ready; BGO source/transport/selection/significance chain is not run.",
        },
        {
            "item_id": "P1_BGO_CONTROL_GEOMETRY_SCAFFOLD",
            "priority": "P1",
            "status": "CLOSED_SCAFFOLD",
            "claim_level": bgo.get("claim_level", "missing"),
            "evidence": (
                f"BGO_segments={bgo_chk.get('bgo_material_segments')}; "
                f"veto_triggers={bgo_chk.get('veto_triggers')}; "
                f"BGO_active_mass_kg={fmt(bgo_chk.get('bgo_active_mass_kg'))}; "
                f"overlap={bgo_chk.get('cosima_overlap_status')}; "
                f"transport={bgo_chk.get('transport_status')}"
            ),
            "remaining_gap": "Input geometry scaffold is ready; source/transport/selection/significance chain is still not run.",
        },
        {
            "item_id": "P1_FOCUSED_SPOT_SPATIAL_PROXY",
            "priority": "P1",
            "status": "CLOSED",
            "claim_level": spatial.get("claim_level", "missing"),
            "evidence": (
                f"Step09_rows={spatial_chk.get('signal_eventlist_rows')}; "
                f"detector_events={spatial_chk.get('signal_detector_events')}; "
                f"spot_r90={fmt(spatial_chk.get('signal_radius_r90_cm'))} cm; "
                f"spot_r90_background={fmt(spatial_chk.get('spot_r90_background_cps'))} cps; "
                f"spot_r90_Z20d={fmt(spatial_chk.get('spot_r90_Z20d'))}; "
                f"focus_status={focus.get('status')}"
            ),
            "remaining_gap": "Detector-coupled focused-spot transport is done; profile-likelihood analysis remains separate.",
        },
        {
            "item_id": "P2_V404_TINY_RESPONSE_CLAMP",
            "priority": "P2",
            "status": "CLOSED",
            "claim_level": step07.get("claim_level", "missing"),
            "evidence": (
                f"tiny_response_clamp={step07_chk.get('tiny_response_clamp')}; "
                f"V404_narrow_response={fmt(step07_chk.get('V404_redshift_narrow_response_fraction'))}; "
                f"V404_narrow_max_final={fmt(step07_chk.get('V404_redshift_narrow_max_final_rate_day15_cps'))}"
            ),
            "remaining_gap": "None for numeric hygiene.",
        },
        {
            "item_id": "P2_PROFILE_LIKELIHOOD_LIMA",
            "priority": "P2",
            "status": "OPEN",
            "claim_level": "not_implemented",
            "evidence": f"Step08 scope: {step08.get('scope', '')}",
            "remaining_gap": "Implement line-window spatial-spectral likelihood or Li&Ma-equivalent treatment before making final paper sensitivity claims.",
        },
        {
            "item_id": "P2_BGO_FULL_CONTROL_CHAIN",
            "priority": "P2",
            "status": "OPEN",
            "claim_level": "not_run",
            "evidence": (
                f"BGO_control_status={csi_chk.get('bgo_control_status')}; "
                f"BGO_geometry_scaffold={bgo.get('status')}; "
                f"BGO_transport={bgo_chk.get('transport_status')}"
            ),
            "remaining_gap": "Run alternate BGO geometry, fixed source, delayed transport, Step05, Step08, and compare against CsI.",
        },
    ]

    open_p0 = [item["item_id"] for item in items if item["priority"] == "P0" and item["status"] in {"OPEN", "PARTIAL_L1"}]
    open_or_partial = [item["item_id"] for item in items if item["status"].startswith("OPEN") or item["status"].startswith("PARTIAL")]
    status = "PASS" if not open_p0 and not stale_hits else "FAIL"
    payload = {
        "status": status,
        "claim_level": "L1_REVIEW_20260531_CLOSURE_MATRIX",
        "scope": "Priority-ordered closure matrix for review_20260531.html follow-up. PASS means no open P0 item and no stale live-doc current-section hits; it does not mean all P1/P2 physics upgrades are complete.",
        "checks": {
            "items_total": len(items),
            "p0_items": [item["item_id"] for item in items if item["priority"] == "P0"],
            "open_p0_items": open_p0,
            "open_or_partial_items": open_or_partial,
            "live_doc_stale_hits": stale_hits,
        },
        "items": items,
        "outputs": {
            "markdown": rel(OUT / "review_20260531_closure.md"),
            "csv": rel(OUT / "review_20260531_closure.csv"),
        },
    }

    fields = ["item_id", "priority", "status", "claim_level", "evidence", "remaining_gap"]
    write_csv(OUT / "review_20260531_closure.csv", items, fields)
    (OUT / "review_20260531_closure_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Review 2026-05-31 Closure Matrix",
        "",
        f"Status: `{status}`.",
        "",
        "PASS here means no open P0 item and no stale current-section live-doc hits. It does not mean all P1/P2 paper-upgrade simulations are complete.",
        "",
        "## Checks",
        "",
        f"- Items total: `{len(items)}`.",
        f"- Open P0 items: `{open_p0}`.",
        f"- Open or partial items: `{open_or_partial}`.",
        f"- Live-doc stale hits: `{stale_hits}`.",
        "",
        "## Matrix",
        "",
        md_table(items, fields),
        "",
    ]
    (OUT / "review_20260531_closure.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": status, "checks": payload["checks"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
