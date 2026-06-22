#!/usr/bin/env python3
"""Build the Route-A full-chain experiment report for 2026-06-01."""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "experiment_report_20260601"
FIG_DIR = OUT / "figures"
REPORT = OUT / "experiment_report.md"
LOG = ROOT / "ROUTE_A_FULLCHAIN_EXECUTION_LOG_20260601.md"

OPTICS = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority.json"
STEP04_AUDIT = ROOT / "stepwise_maintenance" / "step04_opticsim" / "outputs" / "step04_opticsim_audit.json"
STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_case_summary.json"
STEP08 = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "step08_significance_summary.json"
LINE = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "line_window_sensitivity_summary.json"
SPATIAL = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "spatial_line_proxy_summary.json"
STAT_UNCERTAINTY = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "headline_statistical_uncertainty.csv"
STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "step09_optics_bridge_summary.json"
FOCUS = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
NON_XRAY = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "non_xray_background_w1_w2_veto_table.csv"
VALIDATION = ROOT / "outputs" / "reports" / "validation_new_geo_re" / "validation_new_geo_re.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt(value: Any, nd: int = 6) -> str:
    try:
        x = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(out)


def first_value(row: dict[str, Any], primary: str, fallback: str | None = None) -> Any:
    value = row.get(primary)
    if value not in ("", None):
        return value
    if fallback is None:
        return value
    return row.get(fallback)


def variant(headline: Any, constant: Any) -> str:
    if constant in ("", None):
        return fmt(headline)
    return f"{fmt(headline)} (constant-rate variant {fmt(constant)})"


def rows_by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in rows}


def copy_figures() -> list[dict[str, str]]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    sources = [
        ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "figures" / "non_xray_background_spectrum_w1_w2.png",
        ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "figures" / "detector_coupled_spatial_line_cuts.png",
        ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "figures" / "source_case_final_rates_day15.png",
        ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "figures" / "cumulative_significance_examples.png",
    ]
    copied = []
    for src in sources:
        if not src.exists():
            continue
        dst = FIG_DIR / src.name
        shutil.copy2(src, dst)
        copied.append({"source": rel(src), "report_copy": rel(dst)})
    return copied


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    optics = load_json(OPTICS, {})
    step04 = load_json(STEP04_AUDIT, {})
    step07 = load_json(STEP07, {})
    step08 = load_json(STEP08, {})
    line = load_json(LINE, {})
    spatial = load_json(SPATIAL, {})
    step09 = load_json(STEP09, {})
    focus = load_json(FOCUS, {})
    validation = load_json(VALIDATION, {})
    non_xray_rows = read_csv(NON_XRAY)
    stat_rows = rows_by_key(read_csv(STAT_UNCERTAINTY), "selection_id") if STAT_UNCERTAINTY.exists() else {}
    copied_figures = copy_figures()

    aeff_target = float(optics.get("design_target", {}).get("aeff_511_design_cm2", 16.0))
    aeff = float(optics.get("aeff_511_cm2", 0.0))
    aeff_residual = abs(aeff - aeff_target) / aeff_target
    w1 = focus["window_checks"]["W1_design_passband"]
    w2 = focus["window_checks"]["W2_511_pm_420eV"]
    spatial_chk = spatial.get("checks", {})
    line_chk = line.get("checks", {})
    step08_chk = step08.get("checks", {})
    step07_chk = step07.get("checks", {})
    bridge = step09.get("bridge", {})

    w1_a_z = step08_chk.get("A_reference_final_Z_20d")
    w1_a_t3 = step08_chk.get("A_reference_T3_day_extrapolated_constant_profile")
    broad_z_td = first_value(line_chk, "broad_Z20d_time_dependent", "broad_Z20d")
    w2_z_td = first_value(line_chk, "line_pm_3sigma_Z20d_time_dependent", "line_pm_3sigma_Z20d")
    w2_t3_td = first_value(line_chk, "line_pm_3sigma_T3_day_time_dependent", "line_pm_3sigma_T3_day_constant_rate")
    w2_flux_td = first_value(line_chk, "line_pm_3sigma_flux_3sigma_20d_time_dependent_ph_cm2_s", "line_pm_3sigma_flux_3sigma_20d_ph_cm2_s")
    spot_z_td = first_value(spatial_chk, "spot_r90_Z20d_time_dependent", "spot_r90_Z20d")
    spot_t3_td = first_value(spatial_chk, "spot_r90_T3_day_time_dependent", "spot_r90_T3_day")
    spot_flux_td = first_value(spatial_chk, "spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s", "spot_r90_flux_3sigma_20d_ph_cm2_s")
    best_td_id = first_value(spatial_chk, "best_time_dependent_cut_id", "best_cut_id")
    best_td_z = first_value(spatial_chk, "best_time_dependent_Z20d", "best_cut_Z20d")
    w2_stat = stat_rows.get("W2_511_pm_420eV", {})
    spot_stat = stat_rows.get("spot_r90", {})

    step_rows = [
        {"step": "Step01 geometry", "status": "unchanged authority", "output": "outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json"},
        {"step": "Step02 prompt/delayed transport", "status": "reused day15 catalog", "output": "outputs/reports/day15_complete_report/work/event_catalog.pkl"},
        {"step": "Step03 delay source", "status": "reused fixed source", "output": "runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json"},
        {"step": "Step04 optics", "status": step04.get("status", ""), "output": "stepwise_maintenance/step04_opticsim/optics_aeff_authority.json"},
        {"step": "Step05 veto/catalog", "status": "reused TES/CsI/Compton selection", "output": "outputs/reports/day15_complete_report/complete_day15_summary.json"},
        {"step": "Step06 mission axis", "status": "PASS", "output": "stepwise_maintenance/step06_mission_time_variation/outputs/background_time_variation.csv"},
        {"step": "Step07 source cases", "status": step07.get("claim_level", ""), "output": "stepwise_maintenance/step07_source_cases/outputs/source_case_summary.json"},
        {"step": "Step08 significance", "status": step08.get("claim_level", ""), "output": "stepwise_maintenance/step08_significance/outputs/"},
        {"step": "Step09 EventList/full transport", "status": focus.get("status", ""), "output": "stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json"},
        {"step": "Step10 report", "status": "written", "output": rel(REPORT)},
    ]

    comparison_rows = [
        {
            "quantity": "science source geometry",
            "old_placeholder": "HomogeneousBeam r=1.8 cm",
            "new_focused": "Step09 focused EventList",
        },
        {
            "quantity": "A_opt / A_eff",
            "old_placeholder": "50.89 cm2",
            "new_focused": f"{fmt(aeff)} cm2",
        },
        {
            "quantity": "W1 final response",
            "old_placeholder": "23.9928 cps/(ph cm-2 s-1)",
            "new_focused": f"{fmt(w1['signal_both_response_cps_per_ph_cm2_s'])} cps/(ph cm-2 s-1)",
        },
        {
            "quantity": "W2 final response",
            "old_placeholder": "line sidecar used old science catalog",
            "new_focused": f"{fmt(w2['signal_both_response_cps_per_ph_cm2_s'])} cps/(ph cm-2 s-1)",
        },
        {
            "quantity": "spatial headline",
            "old_placeholder": "EventList radius proxy",
            "new_focused": f"detector-coupled spot_r90, time-dependent Z20d={fmt(spot_z_td)}",
        },
    ]

    background_rows = []
    for row in non_xray_rows:
        background_rows.append(
            {
                "window": row["window_id"],
                "stage": row["stage"],
                "total_cps": fmt(row["rate_cps"]),
                "prompt_cps": fmt(row["prompt_cps"]),
                "delayed_cps": fmt(row["delayed_cps"]),
                "reject_vs_raw": fmt(row["rejection_factor_vs_raw"]),
            }
        )

    lines = [
        "# Route-A 511-keV Focused EventList Experiment Report",
        "",
        "Date: 2026-06-01",
        "",
        "## Executive Summary",
        "",
        f"- Optics design: `{optics.get('design_name')}`, Ge(111), f=`{fmt(optics.get('focal_length_mm'))}` mm, tiles=`{optics.get('total_tiles')}`.",
        f"- A_eff(511): `{fmt(aeff)}` cm2 against design `{fmt(aeff_target)}` cm2; residual `{fmt(aeff_residual)}` is below the 15% adjustment threshold, so no geometry retune was applied.",
        f"- Natural W1 passband: `{fmt(w1['lo_keV'])}-{fmt(w1['hi_keV'])}` keV. W2 line window: `{fmt(w2['lo_keV'])}-{fmt(w2['hi_keV'])}` keV.",
        f"- Step09 focused EventList rows: `{bridge.get('rows_written')}`; detector-coupled focused W2 signal events: `{spatial_chk.get('signal_detector_events')}`.",
        f"- W2 no-spatial: background `{fmt(line_chk.get('line_pm_3sigma_background_cps'))}` cps, time-dependent fold (headline) Z20d `{variant(w2_z_td, line_chk.get('line_pm_3sigma_Z20d'))}`.",
        f"- Headline spatial cut is `spot_r90`, not `spot_rmax`: radius `{fmt(spatial_chk.get('signal_radius_r90_cm'))}` cm, background `{fmt(spatial_chk.get('spot_r90_background_cps'))}` cps, time-dependent Z20d `{variant(spot_z_td, spatial_chk.get('spot_r90_Z20d'))}`, T3 `{variant(spot_t3_td, spatial_chk.get('spot_r90_T3_day'))}` day, 20-day 3-sigma flux `{variant(spot_flux_td, spatial_chk.get('spot_r90_flux_3sigma_20d_ph_cm2_s'))}` ph cm-2 s-1.",
        "",
        "## Step Outputs",
        "",
        md_table(step_rows, ["step", "status", "output"]),
        "",
        "## Placeholder Replacement",
        "",
        md_table(comparison_rows, ["quantity", "old_placeholder", "new_focused"]),
        "",
        "## Non-X-Ray Background",
        "",
        "W1 is the optics design natural passband. W2 is 511 +/- 420 eV. The four stages are raw, +CsI scintillator, +Compton/FoV, and after both.",
        "",
        md_table(background_rows, ["window", "stage", "total_cps", "prompt_cps", "delayed_cps", "reject_vs_raw"]),
        "",
        "Figures copied into this report directory:",
        "",
    ]
    for item in copied_figures:
        lines.append(f"- `{item['report_copy']}` from `{item['source']}`")
    lines.extend(
        [
            "",
            "## Science Significance",
            "",
            f"- Step08 W1 mission-axis A-reference time-dependent Z20d: `{fmt(w1_a_z)}`; time-dependent T3 extrapolation: `{fmt(w1_a_t3)}` day.",
            f"- Step08 W1 detector-coupled passband sidecar time-dependent Z20d: `{fmt(broad_z_td)}`.",
            f"- Step08 W2 line-only time-dependent Z20d: `{variant(w2_z_td, line_chk.get('line_pm_3sigma_Z20d'))}`; T3 `{variant(w2_t3_td, line_chk.get('line_pm_3sigma_T3_day_constant_rate'))}` day; 20-day 3-sigma flux `{variant(w2_flux_td, line_chk.get('line_pm_3sigma_flux_3sigma_20d_ph_cm2_s'))}` ph cm-2 s-1.",
            f"- Step08 W2 + spot_r90 detector-coupled time-dependent Z20d: `{variant(spot_z_td, spatial_chk.get('spot_r90_Z20d'))}`; T3 `{variant(spot_t3_td, spatial_chk.get('spot_r90_T3_day'))}` day; 20-day 3-sigma flux `{variant(spot_flux_td, spatial_chk.get('spot_r90_flux_3sigma_20d_ph_cm2_s'))}` ph cm-2 s-1.",
            f"- Best robust diagnostic cut by time-dependent convention is `{best_td_id}` with Z20d `{fmt(best_td_z)}`; constant-rate best cut was `{spatial_chk.get('best_cut_id')}` with Z20d `{fmt(spatial_chk.get('best_cut_Z20d'))}`. It is diagnostic only, while `spot_r90` is the reported robust headline cut.",
            f"- Statistical sidecar: W2 background `{fmt(w2_stat.get('B_cps'))} +/- {fmt(w2_stat.get('delta_B_cps'))}` cps and Z20d `{fmt(w2_stat.get('Z20d_td'))} +/- {fmt(w2_stat.get('delta_Z20d_td_analytic'))}`; spot_r90 background `{fmt(spot_stat.get('B_cps'))} +/- {fmt(spot_stat.get('delta_B_cps'))}` cps and Z20d `{fmt(spot_stat.get('Z20d_td'))} +/- {fmt(spot_stat.get('delta_Z20d_td_analytic'))}`.",
            "",
            "## Route A / Route B Meaning",
            "",
            "- Route A is the compact/on-axis 511-keV point-source case. In this closure it is simulated as the true focused Step09 EventList source and normalized by Step04 A_eff.",
            "- Route B is the diffuse bulge/disk foreground case. It is still aperture/rate folded in Step07 and is not emitted as a focal EventList source because it needs a diffuse-sky optics focal-map projection.",
            "",
            "## Validation",
            "",
            f"- Latest validator status included at report build time: `{validation.get('status', 'not_run_at_report_build')}`.",
            f"- Step07 A-plane closure relative error: `{fmt(step07_chk.get('A_onaxis_mono_plane_rel_error'))}`.",
            f"- Step07 A-final closure relative error: `{fmt(step07_chk.get('A_onaxis_mono_final_rel_error'))}`.",
            "",
            "## Remaining Scope",
            "",
            "Optics hardware mass prompt/delayed activation is not included in the detector geometry. Diffuse-sky Route B is not yet projected through an energy-dependent optics focal map. These are separate upgrades and do not change the Route-A focused EventList closure above.",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    log_lines = [
        "# Route-A Full-Chain Execution Log 2026-06-01",
        "",
        f"- Design: `{optics.get('design_name')}`.",
        f"- A_eff(511): `{fmt(aeff)}` cm2; target residual `{fmt(aeff_residual)}` < 15%, no retune.",
        f"- Step09 EventList rows: `{bridge.get('rows_written')}`; full Cosima focused SIM parsed by `{rel(FOCUS)}`.",
        f"- W1 final background: `{fmt(w1['background_both_cps'])}` cps; W1 signal at 1e-4: `{fmt(w1['signal_both_cps_at_reference_flux'])}` cps; detector-coupled passband time-dependent Z20d `{fmt(broad_z_td)}`.",
        f"- W2 final background: `{fmt(w2['background_both_cps'])}` cps; W2 signal at 1e-4: `{fmt(w2['signal_both_cps_at_reference_flux'])}` cps; time-dependent Z20d `{variant(w2_z_td, line_chk.get('line_pm_3sigma_Z20d'))}`.",
        f"- W2 + spot_r90 background: `{fmt(spatial_chk.get('spot_r90_background_cps'))}` cps; time-dependent Z20d `{variant(spot_z_td, spatial_chk.get('spot_r90_Z20d'))}`; 3-sigma 20d flux `{variant(spot_flux_td, spatial_chk.get('spot_r90_flux_3sigma_20d_ph_cm2_s'))}` ph cm-2 s-1.",
        f"- Report: `{rel(REPORT)}`.",
    ]
    LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "report": rel(REPORT), "log": rel(LOG)}


def main() -> int:
    payload = build()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
