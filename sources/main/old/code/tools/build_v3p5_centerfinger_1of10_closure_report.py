#!/usr/bin/env python3
"""Build the v3p5 center-finger 1/10 transport closure report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "v3p5_centerfinger_1of10_closure"
SUMMARY_JSON = OUT / "v3p5_centerfinger_1of10_closure_summary.json"
SUMMARY_MD = OUT / "v3p5_centerfinger_1of10_closure_report.md"

GEOM_VALIDATION = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_validation.json"
STEP00 = ROOT / "stepwise_maintenance" / "step00_geometry" / "outputs" / "v3p5_centerfinger" / "step00_v3p5_centerfinger_closure.json"
STEP02 = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / "outputs_v3p5_centerfinger_1of10" / "step02_v3p5_centerfinger_1of10_summary.json"
STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
STEP06 = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_v3p5_centerfinger_1of10" / "step06_v3p5_centerfinger_1of10_summary.json"
STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs_v3p5_centerfinger_1of10" / "source_case_summary.json"
STEP08 = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_v3p5_centerfinger_1of10" / "step08_v3p5_centerfinger_l1_significance_summary.json"
STEP08_TIME = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_v3p5_centerfinger_1of10" / "step08_v3p5_centerfinger_time_dependent_summary.json"
STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5" / "step09_optics_bridge_summary.json"
SOURCE_MANIFEST = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45" / "source_migration_manifest.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, problems: list[str]) -> None:
    if not condition:
        problems.append(message)


def build_payload() -> dict[str, Any]:
    geom = load_json(GEOM_VALIDATION)
    step00 = load_json(STEP00)
    step02 = load_json(STEP02)
    step05 = load_json(STEP05) if STEP05.exists() else None
    step06 = load_json(STEP06) if STEP06.exists() else None
    step07 = load_json(STEP07) if STEP07.exists() else None
    step08 = load_json(STEP08) if STEP08.exists() else None
    step08_time = load_json(STEP08_TIME) if STEP08_TIME.exists() else None
    step09 = load_json(STEP09)
    source = load_json(SOURCE_MANIFEST)

    problems: list[str] = []
    w_thick = geom["checks"]["w_side_collimator_thickness_cm"]
    w_range = geom["checks"]["w_side_collimator_x_range_cm"]
    frame = step00["geometry_extents"]["instrument_frame"]
    det = step00["detector_core"]
    step02_delayed = step02["delayed_transport"]
    step09_bridge = step09["bridge"]
    step09_full = step09["full_transport"]

    require(step00["status"] == "STEP00_PASS", "Step00 is not PASS", problems)
    require(step00["proxy_status"] == "PROXY_PASS", "Step00 proxy is not PASS", problems)
    require(step02["status"] == "PASS_1OF10_TRANSPORT_CLOSURE", "Step02 1/10 is not PASS", problems)
    valid_step05 = {
        "PASS_V3P5_STEP05_L1_RAW_ACTIVE_VETO",
        "PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1",
    }
    require(step05 is not None and step05["status"] in valid_step05, "Step05 v3p5 L1 response is not PASS", problems)
    require(step06 is not None and step06["status"] == "PASS_V3P5_STEP06_TIME_AXIS_1OF10", "Step06 v3p5 time axis is not PASS", problems)
    require(step07 is not None and step07["status"] == "PASS_V3P5_STEP07_SOURCE_CASES_1OF10", "Step07 v3p5 source cases are not PASS", problems)
    require(
        step08 is not None and step08["status"] == "PASS_V3P5_STEP08_L1_DIRECT_EXPECTATION_1OF10",
        "Step08 v3p5 L1 direct significance sidecar is not PASS",
        problems,
    )
    require(
        step08_time is not None and step08_time["status"] == "PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10",
        "Step08 v3p5 time-dependent significance is not PASS",
        problems,
    )
    require(step09["status"] == "PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED", "Step09 full transport is not PASS", problems)
    require(abs(float(w_thick) - 2.0) < 1.0e-9, "W side collimator is not 2 cm", problems)
    require(abs(float(source["farfield_radius_cm"]) - 60.0) < 1.0e-9, "far-field radius is not 60 cm", problems)
    require(abs(float(frame["side_window_look_elevation_deg"]) - 45.0) < 1.0e-6, "side-window elevation is not 45 deg", problems)
    require(int(det["total_pixel_copies"]) == 2256, "detector pixel copy count is not 2256", problems)
    require(int(step02_delayed["SE"]) == 100000, "Step02 delayed transport SE is not 100000", problems)
    require(int(step09_full.get("stored_events", 0)) == int(step09_bridge["rows_written"]), "Step09 full stored events do not match EventList rows", problems)
    require(int(step09_full.get("id_events", 0)) == int(step09_bridge["rows_written"]), "Step09 full ID events do not match EventList rows", problems)

    return {
        "status": "PASS_V3P5_1OF10_TRANSPORT_CLOSURE" if not problems else "FAIL_V3P5_1OF10_TRANSPORT_CLOSURE",
        "claim_level": "low-stat v3p5 closure through Step00/02/05/06/07/08/09; not paper-facing statistics",
        "problems": problems,
        "geometry": {
            "bounds": "geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json",
            "setup": step00["simulation_geometry_setup"],
            "step00_status": step00["status"],
            "proxy_status": step00["proxy_status"],
            "cosima_overlap": step00["cosima_overlap"]["status"],
            "source_total_mass_kg": step00["source_total_mass_kg"],
            "active_csi_mass_kg": step00["active_csi_mass_kg"],
            "detector_total_pixel_copies": det["total_pixel_copies"],
            "side_window_look_elevation_deg": frame["side_window_look_elevation_deg"],
            "farfield_radius_cm": source["farfield_radius_cm"],
            "w_side_collimator_thickness_cm": w_thick,
            "w_side_collimator_x_range_cm": w_range,
        },
        "step02_background_1of10": {
            "summary": rel(STEP02),
            "status": step02["status"],
            "instant_generated": step02["instant_transport"]["events_generated"],
            "instant_jobs": step02["instant_transport"]["jobs"],
            "instant_passes": step02["instant_transport"]["passes"],
            "buildup_generated": step02["buildup_transport"]["events_generated"],
            "buildup_jobs": step02["buildup_transport"]["jobs"],
            "buildup_passes": step02["buildup_transport"]["passes"],
            "fixed_source_blocks": step02["fixed_decay_source"]["source_blocks"],
            "fixed_source_activity_Bq": step02["fixed_decay_source"]["total_activity_Bq"],
            "delayed_transport_sim": step02_delayed["path"],
            "delayed_transport_SE": step02_delayed["SE"],
            "delayed_transport_ID": step02_delayed["ID"],
            "delayed_transport_TE_s": step02_delayed["TE_s"],
        },
        "step09_focused_signal": {
            "summary": rel(STEP09),
            "status": step09["status"],
            "profile": step09["profile"],
            "eventlist_rows": step09_bridge["rows_written"],
            "eventlist_r90_cm": step09_bridge["r90_cm"],
            "eventlist_r95_cm": step09_bridge["r95_cm"],
            "eventlist_max_radius_cm": step09_bridge["max_radius_cm"],
            "be_radius_cm": step09_bridge["be_radius_cm"],
            "full_source": step09_bridge["source"],
            "full_sim": step09_full["sim"],
            "full_stored_events": step09_full.get("stored_events"),
            "full_id_events": step09_full.get("id_events"),
            "full_observation_time_s": step09_full.get("observation_time_from_sim_s"),
        },
        "step05_l1_detector_response": None
        if step05 is None
        else {
            "summary": rel(STEP05),
            "status": step05["status"],
            "claim_level": step05["claim_level"],
            "science_physical_normalization": step05.get("science_physical_normalization"),
            "broad_480_550": step05["windows"]["broad_480_550"],
            "w2_510p58_511p42": step05["windows"]["w2_510p58_511p42"],
            "timeline": step05.get("timeline"),
            "timeline_draw_summary": step05.get("timeline_draw_summary"),
        },
        "step06_time_axis": None
        if step06 is None
        else {
            "summary": rel(STEP06),
            "status": step06["status"],
            "claim_level": step06["claim_level"],
            "checks": step06["checks"],
        },
        "step07_source_cases": None
        if step07 is None
        else {
            "summary": rel(STEP07),
            "status": step07["status"],
            "claim_level": step07["claim_level"],
            "checks": step07["checks"],
        },
        "step08_l1_direct_significance": None
        if step08 is None
        else {
            "summary": rel(STEP08),
            "status": step08["status"],
            "claim_level": step08["claim_level"],
            "headline_window": step08["headline_window"],
            "headline": step08["headline"],
            "warnings": step08.get("warnings", []),
        },
        "step08_time_dependent_significance": None
        if step08_time is None
        else {
            "summary": rel(STEP08_TIME),
            "status": step08_time["status"],
            "claim_level": step08_time["claim_level"],
            "checks": step08_time["checks"],
        },
        "not_yet_v3p5": [
            "Higher-statistics production beyond this 1/10 checkpoint",
            "Exact-position delayed-source sampling replacing axisymmetric RadialProfileBeam compression",
            "Selection-consistent spatial/profile likelihood and spatial cuts for v3p5",
            "Diffuse/off-axis EventList treatment beyond the current aperture-flux proxy",
        ],
    }


def markdown(payload: dict[str, Any]) -> str:
    g = payload["geometry"]
    b = payload["step02_background_1of10"]
    d = payload.get("step05_l1_detector_response")
    step06 = payload.get("step06_time_axis")
    step07 = payload.get("step07_source_cases")
    e = payload.get("step08_l1_direct_significance")
    et = payload.get("step08_time_dependent_significance")
    s = payload["step09_focused_signal"]
    lines = [
        "# v3p5 Center-Finger 1/10 Transport Closure",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Claim level: {payload['claim_level']}.",
        "",
        "This report joins the current v3p5 geometry, atmospheric background transport, delayed transport, focused optics EventList transport, Step05 L1 selection, Step06 mission-axis fold, Step07 source-case ledger, and Step08 time-dependent significance into one low-statistics closure record. It intentionally does not claim paper-facing statistics.",
        "",
        "## Geometry",
        "",
        f"- setup: `{g['setup']}`",
        f"- Step00/proxy/overlap: `{g['step00_status']}` / `{g['proxy_status']}` / `{g['cosima_overlap']}`",
        f"- source mass: `{g['source_total_mass_kg']:.6g} kg`; active CsI mass: `{g['active_csi_mass_kg']:.6g} kg`",
        f"- detector core: `{g['detector_total_pixel_copies']}` TES pixel copies",
        f"- side-window elevation: `{g['side_window_look_elevation_deg']:.6g} deg`",
        f"- far-field/setup sphere: `{g['farfield_radius_cm']:.6g} cm`",
        f"- W side collimator: `{g['w_side_collimator_thickness_cm']:.6g} cm`, x range `{g['w_side_collimator_x_range_cm']}`",
        "",
        "## Step02 Background",
        "",
        f"- status: `{b['status']}`",
        f"- instant: `{b['instant_passes']}/{b['instant_jobs']}` jobs passed, `{b['instant_generated']}` generated particles",
        f"- buildup: `{b['buildup_passes']}/{b['buildup_jobs']}` jobs passed, `{b['buildup_generated']}` generated particles",
        f"- fixed delayed source: `{b['fixed_source_blocks']}` blocks, `{b['fixed_source_activity_Bq']:.8g} Bq`",
        f"- delayed transport: `SE={b['delayed_transport_SE']}`, `ID={b['delayed_transport_ID']}`, `TE={b['delayed_transport_TE_s']:.9g} s`",
        f"- summary: `{b['summary']}`",
        "",
        "## Step05 L1 Detector Response",
        "",
    ]
    if d is None:
        lines.append("- status: missing")
    else:
        broad = d["broad_480_550"]["by_stream"]
        w2 = d["w2_510p58_511p42"]["by_stream"]
        timeline = d.get("timeline") or {}
        tl_w2 = (timeline.get("windows") or {}).get("w2_510p58_511p42", {})
        lines.extend(
            [
                f"- status: `{d['status']}`",
                f"- claim level: {d['claim_level']}",
                f"- broad 480-550 side-Compton/FoV direct rates: prompt `{broad['prompt']['side_compton_fov_pass_rate_s-1']:.6g} s^-1`, delayed `{broad['delayed']['side_compton_fov_pass_rate_s-1']:.6g} s^-1`, focused signal `{broad['science']['side_compton_fov_pass_rate_s-1']:.6g}` per unit EventList injection rate",
                f"- W2 510.58-511.42 side-Compton/FoV direct rates: prompt `{w2['prompt']['side_compton_fov_pass_rate_s-1']:.6g} s^-1`, delayed `{w2['delayed']['side_compton_fov_pass_rate_s-1']:.6g} s^-1`, focused signal `{w2['science']['side_compton_fov_pass_rate_s-1']:.6g}` per unit EventList injection rate",
                f"- physical normalization: A_eff `{d['science_physical_normalization']['aeff_511_cm2']:.6g} cm2`, T_atm `{d['science_physical_normalization']['atmospheric_transmission']['T_atm']:.6g}`, reference injection rate `{d['science_physical_normalization']['rate_to_v3p5_injection_plane_s-1']:.6g} s^-1` at `1e-4 ph cm^-2 s^-1`",
                f"- W2 common-time-axis side-Compton/FoV rate: `{(tl_w2.get('rates_s-1') or {}).get('side_compton_fov_pass', 0.0):.6g} s^-1` under unit EventList injection-rate normalization",
                f"- summary: `{d['summary']}`",
            ]
        )
    lines.extend(
        [
        "",
        "## Step06 Mission Time Axis",
        "",
        ]
    )
    if step06 is None:
        lines.append("- status: missing")
    else:
        c = step06["checks"]
        lines.extend(
            [
                f"- status: `{step06['status']}`",
                f"- claim level: {step06['claim_level']}",
                f"- W2 day-15 background/signal: `{c['w2_day15_background_final_cps']:.6g}` / `{c['w2_day15_science_final_cps_at_ref_flux']:.6g}` cps",
                f"- W2 mission-mean background/signal: `{c['w2_dt_weighted_background_final_cps']:.6g}` / `{c['w2_dt_weighted_science_final_cps_at_ref_flux']:.6g}` cps",
                f"- delayed activity scale range: `{c['activity_scale_min']:.6g}` to `{c['activity_scale_max']:.6g}`",
                f"- summary: `{step06['summary']}`",
            ]
        )
    lines.extend(
        [
        "",
        "## Step07 Source Cases",
        "",
        ]
    )
    if step07 is None:
        lines.append("- status: missing")
    else:
        c = step07["checks"]
        lines.extend(
            [
                f"- status: `{step07['status']}`",
                f"- claim level: {step07['claim_level']}",
                f"- source-case rows: `{c['source_case_rows']}`",
                f"- W2 response/background: `{c['w2_response_cps_per_ph_cm2_s']:.6g}` cps/(ph cm^-2 s^-1) / `{c['w2_background_final_cps']:.6g}` cps",
                f"- A reference W2 final rate: `{c['A_reference_w2_final_rate_day15_cps']:.6g}` cps",
                f"- summary: `{step07['summary']}`",
            ]
        )
    lines.extend(
        [
        "",
        "## Step08 Time-Dependent Significance",
        "",
        ]
    )
    if et is None:
        lines.append("- status: missing")
    else:
        c = et["checks"]
        lines.extend(
            [
                f"- status: `{et['status']}`",
                f"- claim level: {et['claim_level']}",
                f"- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d={c['A_reference_w2_Z20d_time_dependent']:.6g}`",
                f"- T3/T5: `{c['A_reference_w2_T3_day']:.6g}` / `{c['A_reference_w2_T5_day']:.6g}` day",
                f"- 20-day 3-sigma flux: `{c['A_reference_w2_flux_3sigma_20d_ph_cm2_s']:.6g} ph cm^-2 s^-1`",
                f"- accidental loss range: `{c['accidental_loss_min']:.6g}` to `{c['accidental_loss_max']:.6g}`",
                f"- low-stat selected W2 background events: `{c['w2_low_stat_background_events']}`",
                f"- summary: `{et['summary']}`",
            ]
        )
    lines.extend(
        [
        "",
        "## Step08 L1 Direct Significance",
        "",
        ]
    )
    if e is None:
        lines.append("- status: missing")
    else:
        h = e["headline"]
        lines.extend(
            [
                f"- status: `{e['status']}`",
                f"- claim level: {e['claim_level']}",
                f"- headline window: `{e['headline_window']}`",
                f"- background/signal: `{h['background_cps']:.6g}` / `{h['signal_cps_at_reference_flux']:.6g}` cps at `1e-4 ph cm^-2 s^-1`",
                f"- direct 20-day Z: `{h['Z20d_direct_s_over_sqrt_b']:.6g}`; constant-rate T3: `{h['T3_day_constant_rate_direct']:.6g} day`; 20-day 3-sigma flux: `{h['flux_3sigma_20d_ph_cm2_s']:.6g} ph cm^-2 s^-1`",
                f"- low-stat selected background events: `{h['low_stat_final_background_events']}`",
                f"- summary: `{e['summary']}`",
            ]
        )
        for warning in e.get("warnings", []):
            lines.append(f"- warning: {warning}")
    lines.extend(
        [
        "",
        "## Step09 Focused Signal",
        "",
        f"- status: `{s['status']}`",
        f"- profile: `{s['profile']}`",
        f"- EventList rows/full transported events: `{s['eventlist_rows']}` / `{s['full_stored_events']}`",
        f"- EventList radii: `r90={s['eventlist_r90_cm']:.6g} cm`, `r95={s['eventlist_r95_cm']:.6g} cm`, `rmax={s['eventlist_max_radius_cm']:.6g} cm`",
        f"- Be radius: `{s['be_radius_cm']:.6g} cm`",
        f"- full SIM: `{s['full_sim']}`",
        f"- summary: `{s['summary']}`",
        "",
        "## Remaining v3p5 Work",
        "",
        ]
    )
    for item in payload["not_yet_v3p5"]:
        lines.append(f"- {item}")
    if payload["problems"]:
        lines.extend(["", "## Problems", ""])
        for item in payload["problems"]:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2, ensure_ascii=False))
    return 0 if payload["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
