#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "validation_new_geo_re"
VALIDATION_MD = ROOT / "VALIDATION.md"


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
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add(checks: list[dict[str, Any]], check: str, status: str, details: str, **extra: Any) -> None:
    row = {"check": check, "status": status, "details": details}
    row.update(extra)
    checks.append(row)


def all_z_values(obj: Any) -> list[float]:
    vals = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (int, float)) and ("z" in key.lower()):
                vals.append(float(value))
            vals.extend(all_z_values(value))
    elif isinstance(obj, list):
        for item in obj:
            vals.extend(all_z_values(item))
    return vals


def parse_homogeneous_beams(path: Path) -> list[dict[str, Any]]:
    rows = []
    pat = re.compile(
        r"^(?P<name>\S+)\.Beam\s+HomogeneousBeam\s+"
        r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+(?P<z>[-+0-9.eE]+)\s+"
        r"(?P<dx>[-+0-9.eE]+)\s+(?P<dy>[-+0-9.eE]+)\s+(?P<dz>[-+0-9.eE]+)\s+"
        r"(?P<r>[-+0-9.eE]+)"
    )
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        m = pat.match(line.strip())
        if m:
            rows.append(
                {
                    "path": path,
                    "lineno": lineno,
                    "name": m.group("name"),
                    "z": float(m.group("z")),
                    "r": float(m.group("r")),
                    "line": line.strip(),
                }
            )
    return rows


def check_source_unit_guard(checks: list[dict[str, Any]], bounds: dict[str, Any]) -> None:
    windows = bounds.get("WINDOWS", [])
    be = next((w for w in windows if w.get("name") == "Win_Be_Cryostat"), None)
    z_vals = all_z_values(bounds)
    z_min, z_max = min(z_vals), max(z_vals)
    be_r = float(be["r_max"]) if be else float("nan")
    source_cards = sorted((ROOT / "config" / "run_configs").glob("Science_511*.source"))
    source_cards += sorted((ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "run_configs").glob("Science511_*.source"))
    problems = []
    checked = 0
    for card in source_cards:
        for beam in parse_homogeneous_beams(card):
            checked += 1
            if not (z_min <= beam["z"] <= z_max):
                problems.append(f"{rel(card)}:{beam['lineno']} z={beam['z']} outside [{z_min},{z_max}]")
            if not (beam["r"] <= be_r + 1.0e-9):
                problems.append(f"{rel(card)}:{beam['lineno']} r={beam['r']} > Be r={be_r}")
            if beam["z"] > 50.0 or beam["r"] > 5.0:
                problems.append(f"{rel(card)}:{beam['lineno']} resembles stale 10x source card: z={beam['z']} r={beam['r']}")
    add(
        checks,
        "source_card_unit_guard",
        "PASS" if checked and not problems else "FAIL",
        f"checked {checked} science HomogeneousBeam cards; Be r={be_r}; z_range=[{z_min:.6g},{z_max:.6g}]"
        if not problems
        else "; ".join(problems),
    )


def check_geometry(checks: list[dict[str, Any]], bounds: dict[str, Any]) -> None:
    meta = bounds.get("META", {})
    be = next((w for w in bounds.get("WINDOWS", []) if w.get("name") == "Win_Be_Cryostat"), {})
    stage_windows = bounds.get("STAGE_WINDOWS", [])
    stage_names = {w.get("name") for w in stage_windows}
    active = bounds.get("ACTIVE_SHIELD", {})
    passive_names = {p.get("name") for p in bounds.get("PASSIVE_PROXIES", [])}
    ok = (
        bounds.get("UNITS") == "cm"
        and str(bounds.get("VERSION", "")).startswith("ADR_v6_demo2")
        and meta.get("length_unit") == "cm"
        and math.isclose(float(meta.get("tes_pixel_thickness_cm", -1)), 0.3, rel_tol=0, abs_tol=1.0e-12)
        and math.isclose(float(be.get("r_max", -1)), 1.898, rel_tol=0, abs_tol=1.0e-12)
        and math.isclose(float(be.get("thick", -1)), 0.015, rel_tol=0, abs_tol=1.0e-12)
        and math.isclose(float(meta.get("science_beam_z_cm", -1)), 16.051, rel_tol=0, abs_tol=1.0e-12)
        and math.isclose(float(meta.get("science_beam_radius_cm", -1)), 1.8, rel_tol=0, abs_tol=1.0e-12)
        and active.get("name") == "CsI_Active_Shield"
        and active.get("mat") == "CsI"
        and set(active.get("threshold_scan_keV", [])) == {30, 50, 70, 80, 100}
        and {
            "Win_50mK_Al_Shield",
            "Win_1K_Al_Shield",
            "Win_4K_Al_Shield",
            "Win_60K_Al_Shield",
        }.issubset(stage_names)
        and {"Passive_Cu_Inner_Liner", "Passive_W_Outer_Liner", "Passive_Bottom_W_Shield"}.issubset(passive_names)
    )
    add(
        checks,
        "geometry_authority",
        "PASS" if ok else "FAIL",
        "DEMO2 cm authority, TES 0.3 cm, Be 1.898/0.015 cm, CsI active shield, staged Al windows, Cu/W passive shield",
    )


def check_native_csi_veto_trigger(checks: list[dict[str, Any]]) -> None:
    det = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "TibetTES_ADR_v4c_mkflange_cm.det"
    text = det.read_text(encoding="utf-8", errors="ignore") if det.exists() else ""
    segments = sorted(
        set(
            re.findall(
                r"^(CsI_Active_Shield_(?:Side|Bottom|Top)\d{2}_SD)\.SensitiveVolume\s+CsI_Active_Shield_",
                text,
                flags=re.MULTILINE,
            )
        )
    )
    threshold_ok = []
    noise_ok = []
    for seg in segments:
        threshold_ok.append(bool(re.search(rf"^{re.escape(seg)}\.TriggerThreshold\s+50(?:\.0)?\s*$", text, flags=re.MULTILINE)))
        noise_ok.append(
            bool(re.search(rf"^{re.escape(seg)}\.NoiseThresholdEqualsTriggerThreshold\s+true\s*$", text, flags=re.MULTILINE))
        )
    native_residue = (
        "# ===== Native MEGAlib TES-trigger" in text
        or "TES_MainTrigger" in text
        or bool(re.search(r"^(Trigger\s|Veto_)", text, flags=re.MULTILINE))
    )
    ok = (
        det.exists()
        and len(segments) == 20
        and all(threshold_ok)
        and all(noise_ok)
        and not native_residue
    )
    add(
        checks,
        "csi_det_no_native_trigger_block",
        "PASS" if ok else "FAIL",
        f"det={rel(det)}; native_trigger_residue={native_residue}; CsI_segments={len(segments)}; "
        f"threshold50={sum(threshold_ok)}/{len(segments)}; noise_equals_threshold={sum(noise_ok)}/{len(segments)}; "
        "native trigger/veto block intentionally absent so activation buildup stores full events",
    )


def parse_observation_time(path: Path) -> float | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if vals:
                return float(vals[0])
    return None


def parse_total_generated_particles(path: Path) -> int | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Total number of generated particles:" in line:
            vals = re.findall(r"\d+", line)
            if vals:
                return int(vals[-1])
    return None


def parse_run_triggers(path: Path) -> int | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^\S+\.Triggers\s+(\d+)\s*$", line.strip())
        if m:
            return int(m.group(1))
    return None


def sum_source_flux_bq(path: Path) -> float | None:
    if not path.exists():
        return None
    total = 0.0
    seen = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^\S+\.Flux\s+([-+0-9.eE]+)\s*$", line.strip())
        if m:
            total += float(m.group(1))
            seen = True
    return total if seen else None


def check_production_paths(checks: list[dict[str, Any]]) -> None:
    fixed_source = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "activation_decay_day15_groundstate_fixed.source"
    delayed_log = ROOT / "runs" / "step02_delayed_transport_equiv2602_aligned" / "cosima_delayed_transport_1m.log"
    required = [
        ROOT / "runs" / "step02_instant_equiv2602_aligned" / "run_summary.json",
        ROOT / "runs" / "step02_buildup_equiv2602_aligned" / "run_summary.json",
        ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_inventory_day15.csv",
        fixed_source,
        delayed_log,
    ]
    missing = [rel(p) for p in required if not p.exists()]
    obs = parse_observation_time(delayed_log)
    generated = parse_total_generated_particles(delayed_log)
    triggers = parse_run_triggers(fixed_source)
    flux_bq = sum_source_flux_bq(fixed_source)
    expected_obs = (float(triggers) / flux_bq) if triggers is not None and flux_bq and flux_bq > 0.0 else None
    obs_rel_delta = abs(obs - expected_obs) / expected_obs if obs is not None and expected_obs else None
    ok = (
        not missing
        and obs is not None
        and obs > 0.0
        and triggers == 1000000
        and generated == 1000000
        and expected_obs is not None
        and obs_rel_delta is not None
        and obs_rel_delta <= 0.05
    )
    add(
        checks,
        "production_paths_aligned",
        "PASS" if ok else "FAIL",
        f"missing={missing}; delayed_obs_s={obs}; generated={generated}; expected_obs_s={expected_obs}; obs_rel_delta={obs_rel_delta}; triggers={triggers}; fixed_activity_Bq={flux_bq}",
    )


def check_fixed_source(checks: list[dict[str, Any]]) -> None:
    source = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "activation_decay_day15_groundstate_fixed.source"
    text = source.read_text(encoding="utf-8", errors="ignore") if source.exists() else ""
    has_bad = ("ParticleType 74183" in text) or ("ParticleType 74180" in text)
    add(checks, "fixed_source_groundstate_removed", "PASS" if source.exists() and not has_bad else "FAIL", "W-183/W-180 ParticleType 74183/74180 absent")


def check_half_life_unit_audit(checks: list[dict[str, Any]]) -> None:
    summary = load_json(ROOT / "outputs" / "reports" / "half_life_unit_audit" / "half_life_unit_audit_summary.json", {})
    csv_path = ROOT / "outputs" / "reports" / "half_life_unit_audit" / "prefix_year_unit_rows.csv"
    md_path = ROOT / "outputs" / "reports" / "half_life_unit_audit" / "half_life_unit_audit.md"
    nubase_path = ROOT / "inputs" / "nubase" / "nubase_2020.txt"
    if not summary:
        add(checks, "half_life_prefix_unit_audit", "FAIL", "half_life_unit_audit_summary.json is missing")
        return
    chk = summary.get("checks", {})
    units_seen = set(chk.get("prefix_year_units_seen", []))
    self_tests = set(chk.get("unit_self_test_units", []))
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_HALF_LIFE_PREFIX_UNIT_AUDIT"
        and csv_path.exists()
        and md_path.exists()
        and nubase_path.exists()
        and int(chk.get("prefix_year_rows", 0)) > 0
        and {"Ey", "ky"}.issubset(units_seen)
        and {"ky", "My", "Gy", "Ty", "Py", "Ey"}.issubset(self_tests)
        and float(chk.get("unit_self_test_max_rel_error", 999)) <= 1.0e-15
        and float(chk.get("prefix_unit_max_rel_error", 999)) <= 1.0e-12
        and float(chk.get("prefix_nubase_line_max_rel_error", 999)) <= 1.0e-12
        and int(chk.get("prefix_nubase_line_mismatches", 999)) == 0
        and int(chk.get("w180_rows", 0)) > 0
        and 0.0 < float(chk.get("w180_new_total_activity_Bq", 999)) < 1.0e-15
        and bool(chk.get("w180_removed_negligible", False))
        and not chk.get("fixed_source_forbidden_particle_types", [])
    )
    details = (
        f"claim={summary.get('claim_level')}; prefix_rows={chk.get('prefix_year_rows')}; "
        f"units={sorted(units_seen)}; self_tests={sorted(self_tests)}; "
        f"prefix_rel={chk.get('prefix_unit_max_rel_error')}; "
        f"line_rel={chk.get('prefix_nubase_line_max_rel_error')}; "
        f"line_mismatches={chk.get('prefix_nubase_line_mismatches')}; "
        f"W180_new_Bq={chk.get('w180_new_total_activity_Bq')}; "
        f"forbidden_ZA={chk.get('fixed_source_forbidden_particle_types')}; "
        f"nubase={nubase_path.exists()}; csv={csv_path.exists()}; md={md_path.exists()}"
    )
    add(checks, "half_life_prefix_unit_audit", "PASS" if ok else "FAIL", details)


def check_csi_activation_baseline(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "outputs" / "reports" / "csi_activation_baseline"
    summary = load_json(out / "csi_activation_baseline_summary.json", {})
    md_path = out / "csi_activation_baseline.md"
    csi_csv = out / "top_csi_activity_by_nuclide.csv"
    total_csv = out / "top_total_activity_by_nuclide.csv"
    if not summary:
        add(checks, "csi_activation_baseline", "FAIL", "csi_activation_baseline_summary.json is missing")
        return
    chk = summary.get("checks", {})
    total_rel = float(chk.get("total_activity_rel_error", 999))
    active_fraction = float(chk.get("csi_active_shield_activity_fraction", 0.0))
    i128_fraction = float(chk.get("I128_total_activity_fraction", 0.0))
    bgo_status = str(chk.get("bgo_control_status", ""))
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_CSI_ACTIVATION_BASELINE_NO_BGO_CONTROL"
        and md_path.exists()
        and csi_csv.exists()
        and total_csv.exists()
        and int(chk.get("rows", 0)) > 0
        and total_rel <= 1.0e-10
        and active_fraction > 0.5
        and i128_fraction > 0.5
        and bgo_status == "NOT_RUN"
    )
    details = (
        f"claim={summary.get('claim_level')}; activity_rel={total_rel}; "
        f"CsI_activity_fraction={active_fraction}; I128_fraction={i128_fraction}; "
        f"delayed_final_cps={chk.get('delayed_final_480_550_cps')}; BGO_control={bgo_status}; "
        f"md={md_path.exists()}; csv={csi_csv.exists() and total_csv.exists()}"
    )
    add(checks, "csi_activation_baseline", "PASS" if ok else "FAIL", details)


def check_bgo_control_geometry(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_bgo_control"
    summary = load_json(out / "bgo_control_geometry_summary.json", {})
    md_path = out / "bgo_control_geometry.md"
    geo_path = out / "TibetTES_ADR_v4c_mkflange_bgo_control.geo"
    det_path = out / "TibetTES_ADR_v4c_mkflange_bgo_control.det"
    setup_path = out / "TibetTES_ADR_v4c_mkflange_bgo_control.geo.setup"
    if not summary:
        add(checks, "bgo_control_geometry", "FAIL", "bgo_control_geometry_summary.json is missing")
        return
    chk = summary.get("checks", {})
    stale = chk.get("stale_csi_active_names", [])
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_BGO_CONTROL_GEOMETRY_SCAFFOLD_NO_TRANSPORT"
        and md_path.exists()
        and geo_path.exists()
        and det_path.exists()
        and setup_path.exists()
        and int(chk.get("bgo_material_segments", 0)) == 20
        and int(chk.get("detector_segments", 0)) == 20
        and int(chk.get("veto_triggers", 0)) == 20
        and int(chk.get("threshold50_segments", 0)) == 20
        and int(chk.get("noise_equals_threshold_segments", 0)) == 20
        and chk.get("bounds_active_name") == "BGO_Active_Shield"
        and chk.get("bounds_active_material") == "BGO"
        and not stale
        and float(chk.get("bgo_active_mass_kg", 0.0)) > float(chk.get("csi_active_mass_kg", 999.0))
        and chk.get("transport_status") == "NOT_RUN"
        and chk.get("cosima_overlap_status") == "PASS"
    )
    details = (
        f"claim={summary.get('claim_level')}; BGO_segments={chk.get('bgo_material_segments')}; "
        f"veto_triggers={chk.get('veto_triggers')}; threshold50={chk.get('threshold50_segments')}; "
        f"noise_equals={chk.get('noise_equals_threshold_segments')}; "
        f"BGO_active_mass_kg={chk.get('bgo_active_mass_kg')}; "
        f"mass_ratio={chk.get('active_mass_ratio_bgo_over_csi')}; "
        f"transport={chk.get('transport_status')}; overlap={chk.get('cosima_overlap_status')}; "
        f"stale={stale}; md={md_path.exists()}"
    )
    add(checks, "bgo_control_geometry", "PASS" if ok else "FAIL", details)


def check_review_20260531_closure(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "outputs" / "reports" / "review_20260531_closure"
    summary = load_json(out / "review_20260531_closure_summary.json", {})
    md_path = out / "review_20260531_closure.md"
    csv_path = out / "review_20260531_closure.csv"
    if not summary:
        add(checks, "review_20260531_closure", "FAIL", "review_20260531_closure_summary.json is missing")
        return
    chk = summary.get("checks", {})
    open_p0 = chk.get("open_p0_items", [])
    stale_hits = chk.get("live_doc_stale_hits", [])
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_REVIEW_20260531_CLOSURE_MATRIX"
        and md_path.exists()
        and csv_path.exists()
        and int(chk.get("items_total", 0)) >= 8
        and not open_p0
        and not stale_hits
    )
    details = (
        f"claim={summary.get('claim_level')}; items={chk.get('items_total')}; "
        f"open_p0={open_p0}; open_or_partial={chk.get('open_or_partial_items')}; "
        f"stale_hits={stale_hits}; md={md_path.exists()}; csv={csv_path.exists()}"
    )
    add(checks, "review_20260531_closure", "PASS" if ok else "FAIL", details)


def rel_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-300)


def check_timeline(checks: list[dict[str, Any]]) -> None:
    summary = load_json(ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json", {})
    timeline = summary.get("timeline_rates_cps", {})
    expect = summary.get("expectation_rates_cps", {})
    diffs = {stage: rel_diff(float(timeline.get(stage, 0.0)), float(expect.get(stage, 0.0))) for stage in ("raw", "bgo", "final")}
    ok = bool(timeline) and all(v <= 0.05 for v in diffs.values())
    add(checks, "timeline_expectation_closure", "PASS" if ok else "FAIL", f"relative differences={diffs}; tolerance=0.05")


def check_compton_geometry(checks: list[dict[str, Any]]) -> None:
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        import compton_fov_geometry

        compton_fov_geometry.main()
        add(checks, "compton_fov_backprojection", "PASS", "synthetic Be-window-center two-hit event is kept")
    except Exception as exc:
        add(checks, "compton_fov_backprojection", "FAIL", repr(exc))


def check_step06(checks: list[dict[str, Any]]) -> None:
    summary = load_json(ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "step06_mission_time_variation_summary.json", {})
    if not summary:
        add(checks, "step06_mission_time_variation", "FAIL", "Step06 summary is missing")
        return
    traj = summary.get("trajectory", {})
    atm = summary.get("atmosphere", {})
    trend = summary.get("environment_trend_checks", {})
    delayed = summary.get("delayed_activity", {})
    closure = summary.get("day15_closure", {})
    ok = (
        summary.get("status") == "PASS"
        and float(traj.get("max_abs_latitude_offset_deg", 999)) <= 0.25 + 1.0e-12
        and float(traj.get("max_abs_longitude_offset_deg", 999)) <= 0.25 + 1.0e-12
        and float(traj.get("max_abs_altitude_offset_km", 999)) <= 2.5 + 1.0e-12
        and float(atm.get("day15_abs_error", 999)) <= 1.0e-10
        and float(delayed.get("max_total_activity_closure_rel_error", 999)) <= 1.0e-10
        and float(closure.get("max_rel_error", 999)) <= 1.0e-10
        and bool(trend.get("prompt_high_altitude_less_than_low_altitude", False))
        and bool(trend.get("T_atm_high_altitude_greater_than_low_altitude", False))
        and float(trend.get("altitude_vs_prompt_scale_corr", 1.0)) < 0.0
        and float(trend.get("altitude_vs_T_atm_corr", -1.0)) > 0.0
    )
    details = (
        f"offsets lat/lon/alt={traj.get('max_abs_latitude_offset_deg')}/"
        f"{traj.get('max_abs_longitude_offset_deg')}/{traj.get('max_abs_altitude_offset_km')}; "
        f"T_day15_error={atm.get('day15_abs_error')}; "
        f"activity_closure={delayed.get('max_total_activity_closure_rel_error')}; "
        f"per_nuclide_rel_error={delayed.get('max_day15_per_nuclide_rel_error')}; "
        f"rate_closure={closure.get('max_rel_error')}; "
        f"alt_prompt_corr={trend.get('altitude_vs_prompt_scale_corr')}; "
        f"alt_T_corr={trend.get('altitude_vs_T_atm_corr')}"
    )
    add(checks, "step06_mission_time_variation", "PASS" if ok else "FAIL", details)


def check_step07(checks: list[dict[str, Any]], bounds: dict[str, Any]) -> None:
    out = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs"
    summary = load_json(out / "source_case_summary.json", {})
    if not summary:
        add(checks, "step07_source_cases", "FAIL", "Step07 source_case_summary.json is missing")
        return
    required = [
        out / "configs" / "source_cases_511_ABC.yaml",
        out / "configs" / "literature_flux_anchors.yaml",
        out / "configs" / "optics_response_current_scaffold.yaml",
        out / "source_spectrum_summary.csv",
        out / "diffuse_aperture_foreground.csv",
        out / "source_case_rates.csv",
        out / "point_vs_diffuse_discrimination.csv",
        out / "cosima_source_manifest.csv",
        ROOT / "stepwise_maintenance" / "step07_source_cases" / "README.md",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    checks_payload = summary.get("checks", {})
    rel_errors = [
        float(checks_payload.get("A_onaxis_mono_final_rel_error", 999)),
        float(checks_payload.get("A_onaxis_mono_plane_rel_error", 999)),
    ]
    v404_narrow_response = float(checks_payload.get("V404_redshift_narrow_response_fraction", 999))
    v404_narrow_max_final = float(checks_payload.get("V404_redshift_narrow_max_final_rate_day15_cps", 999))
    manifest = read_csv(out / "cosima_source_manifest.csv")
    b_skipped = any(row.get("case_prefix") == "B_GC_DIFFUSE" and row.get("status") == "SKIPPED_BY_DESIGN" for row in manifest)
    written_sources = [row for row in manifest if row.get("source_file")]
    windows = bounds.get("WINDOWS", [])
    be = next((w for w in windows if w.get("name") == "Win_Be_Cryostat"), None)
    be_r = float(be["r_max"]) if be else float("nan")
    source_card_problems = []
    eventlist_sources = []
    for row in written_sources:
        card = ROOT / row["source_file"]
        text = card.read_text(encoding="utf-8", errors="ignore") if card.exists() else ""
        if ".EventList " in text and row.get("eventlist_file"):
            eventlist_sources.append(row)
        elif row.get("status") == "FOCUSED_EVENTLIST_SOURCE_READY":
            source_card_problems.append(f"{row['source_file']} is not an EventList source")
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING"
        and not missing
        and all(v <= 1.0e-12 for v in rel_errors)
        and b_skipped
        and len(eventlist_sources) >= 1
        and not source_card_problems
        and "b-full" in str(summary.get("optics_policy", "")).lower()
        and "eventlist" in str(summary.get("optics_policy", "")).lower()
        and 10.0 <= float(summary.get("authority", {}).get("A_opt_cm2", 0.0)) <= 20.0
        and v404_narrow_response == 0.0
        and v404_narrow_max_final == 0.0
    )
    details = (
        f"claim={summary.get('claim_level')}; A closure rel={rel_errors}; "
        f"B default={checks_payload.get('B_default_diffuse_day15_final_cps')} cps; "
        f"B/source policy={checks_payload.get('B_cosima_source_card_policy')}; "
        f"V404_redshift_narrow_response={v404_narrow_response}; "
        f"eventlist_sources={len(eventlist_sources)}; written_sources={len(written_sources)}; missing={missing}"
    )
    if source_card_problems:
        details += "; source_card_problems=" + "; ".join(source_card_problems)
    add(checks, "step07_source_cases", "PASS" if ok else "FAIL", details)


def check_step08(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
    summary = load_json(out / "step08_significance_summary.json", {})
    if not summary:
        add(checks, "step08_significance", "FAIL", "Step08 step08_significance_summary.json is missing")
        return
    required = [
        out / "rate_independent_veto_efficiencies.csv",
        out / "accidental_veto_by_time.csv",
        out / "accidental_representative_anchor.csv",
        out / "cumulative_significance_by_case.csv",
        out / "t3_t5_summary.csv",
        out / "which_number_is_headline.md",
        ROOT / "stepwise_maintenance" / "step08_significance" / "README.md",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    chk = summary.get("checks", {})
    day15_loss = float(chk.get("day15_scale_accidental_loss", 999))
    a_ref_z = float(chk.get("A_reference_final_Z_20d", 0))
    a_ref_t3 = float(chk.get("A_reference_T3_day_counting_or_extrapolated", 0))
    a_ref_t3_status = str(chk.get("A_reference_T3_status", ""))
    mission_days = float(chk.get("mission_duration_day", 0.0))
    bootstrap_rows = int(chk.get("bootstrap_anchor_rows", 0))
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL"
        and not missing
        and 5.0e-4 <= day15_loss <= 1.2e-3
        and a_ref_z > 0.0
        and a_ref_t3 > 0.0
        and mission_days >= 20.0
        and a_ref_t3_status in {"mission_internal_crossing", "extrapolated_beyond_20d"}
        and (a_ref_t3_status != "extrapolated_beyond_20d" or a_ref_t3 > mission_days)
        and float(chk.get("template_proxy_gain", 999)) == 1.0
        and bootstrap_rows == 3
    )
    details = (
        f"claim={summary.get('claim_level')}; day15_acc_loss={day15_loss}; "
        f"A_ref_Z20d={a_ref_z}; A_ref_T3_day={a_ref_t3}; "
        f"T3_status={a_ref_t3_status}; template_gain={chk.get('template_proxy_gain')}; "
        f"bootstrap_rows={bootstrap_rows}; missing={missing}"
    )
    add(checks, "step08_significance", "PASS" if ok else "FAIL", details)


def check_line_window_sensitivity(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
    summary = load_json(out / "line_window_sensitivity_summary.json", {})
    csv_path = out / "line_window_sensitivity.csv"
    md_path = out / "line_window_sensitivity.md"
    if not summary:
        add(checks, "line_window_sensitivity", "FAIL", "line_window_sensitivity_summary.json is missing")
        return
    chk = summary.get("checks", {})
    z_broad = float(chk.get("broad_Z20d_time_dependent", chk.get("broad_Z20d", 0.0)))
    z_line = float(chk.get("line_pm_3sigma_Z20d_time_dependent", chk.get("line_pm_3sigma_Z20d", 0.0)))
    gain = float(chk.get("line_pm_3sigma_Z_gain_vs_broad", 0.0))
    b_line = float(chk.get("line_pm_3sigma_background_cps", 999.0))
    t3 = float(chk.get("line_pm_3sigma_T3_day_time_dependent", chk.get("line_pm_3sigma_T3_day_constant_rate", 999.0)))
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_LINE_WINDOW_DETECTOR_COUPLED_FOCUS"
        and csv_path.exists()
        and md_path.exists()
        and z_broad > 0.5
        and z_line > z_broad
        and gain > 1.5
        and 0.0 < b_line < 1.0
        and 0.0 < t3 < 400.0
    )
    details = (
        f"claim={summary.get('claim_level')}; broad_Z20d={z_broad}; "
        f"line_pm_3sigma_background_cps={b_line}; line_pm_3sigma_Z20d_time={z_line}; "
        f"gain={gain}; T3_day={t3}; csv={csv_path.exists()}; md={md_path.exists()}"
    )
    add(checks, "line_window_sensitivity", "PASS" if ok else "FAIL", details)


def check_spatial_line_proxy(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
    summary = load_json(out / "spatial_line_proxy_summary.json", {})
    csv_path = out / "spatial_line_proxy.csv"
    md_path = out / "spatial_line_proxy.md"
    if not summary:
        add(checks, "spatial_line_proxy", "FAIL", "spatial_line_proxy_summary.json is missing")
        return
    chk = summary.get("checks", {})
    line_b = float(chk.get("line_no_spatial_background_cps", 0.0))
    line_z = float(chk.get("line_no_spatial_Z20d_time_dependent", chk.get("line_no_spatial_Z20d", 0.0)))
    # Gate on the headline (best, Z-maximizing) robust spatial cut, NOT spot_rmax.
    # spot_rmax is driven by the few Compton-scattered diffracted gammas in the
    # tracked tail and is not a meaningful significance cut.
    best_cut = str(chk.get("best_cut_id", ""))
    best_b = float(chk.get("best_cut_background_cps", 999.0))
    best_signal = float(chk.get("best_cut_signal_psf_fraction", 0.0))
    best_z = float(chk.get("best_time_dependent_Z20d", chk.get("best_cut_Z20d", 0.0)))
    gain = best_z / line_z if line_z > 0.0 else float(chk.get("best_cut_Z_gain_vs_line", 0.0))
    rmax = float(chk.get("signal_radius_max_cm", 999.0))
    ok = (
        summary.get("status") == "PASS"
        and summary.get("claim_level") == "L1_SPATIAL_LINE_DETECTOR_COUPLED_CLOSED"
        and csv_path.exists()
        and md_path.exists()
        and int(chk.get("signal_eventlist_rows", 0)) > 0
        and 0.0 < rmax < 1.898
        and 0.5 <= best_signal <= 1.0
        and 0.0 < best_b < line_b
        and best_z > max(line_z, 3.0)
        and gain > 1.5
    )
    details = (
        f"claim={summary.get('claim_level')}; rows={chk.get('signal_eventlist_rows')}; "
        f"best_cut={best_cut}; rmax={rmax}; line_background={line_b}; best_background={best_b}; "
        f"best_signal_fraction={best_signal}; line_Z20d={line_z}; best_Z20d={best_z}; "
        f"gain={gain}; csv={csv_path.exists()}; md={md_path.exists()}"
    )
    add(checks, "spatial_line_proxy", "PASS" if ok else "FAIL", details)


def check_detector_coupled_focus_response(checks: list[dict[str, Any]]) -> None:
    out = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs"
    summary = load_json(out / "detector_coupled_focus_response.json", {})
    md_path = out / "detector_coupled_focus_response.md"
    if not summary:
        add(checks, "detector_coupled_focus_response", "FAIL", "detector_coupled_focus_response.json is missing")
        return
    chk = summary.get("checks", {})
    w = summary.get("window_checks", {})
    spatial = summary.get("spatial_checks", {})
    w2 = w.get("W2_511_pm_420eV", {})
    ok = (
        summary.get("status") == "PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST"
        and summary.get("claim_level") == "L1_DETECTOR_COUPLED_FOCUSED_EVENTLIST"
        and md_path.exists()
        and bool(chk.get("aeff_design_within_tolerance"))
        and int(chk.get("focused_generated_events_seen", 0)) >= 10000
        and float(w2.get("signal_both_response_cps_per_ph_cm2_s", 0.0)) > 0.0
        and 0.0 < float(w2.get("background_both_cps", 0.0)) < 1.0
        and 0.0 < float(spatial.get("signal_radius_r90_cm", 999.0)) < 1.898
        and float(spatial.get("spot_r90_Z20d", 0.0)) > 3.0
    )
    details = (
        f"status={summary.get('status')}; Aeff_resid={chk.get('aeff_design_rel_residual')}; "
        f"generated={chk.get('focused_generated_events_seen')}; "
        f"W2_signal_response={w2.get('signal_both_response_cps_per_ph_cm2_s')}; "
        f"W2_background={w2.get('background_both_cps')}; "
        f"spot_r90={spatial.get('signal_radius_r90_cm')}; "
        f"spot_r90_Z20d={spatial.get('spot_r90_Z20d')}; md={md_path.exists()}"
    )
    add(checks, "detector_coupled_focus_response", "PASS" if ok else "FAIL", details)


def check_step09(checks: list[dict[str, Any]], bounds: dict[str, Any]) -> None:
    out = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs"
    summary = load_json(out / "step09_optics_bridge_summary.json", {})
    if not summary:
        add(checks, "step09_optics_bridge", "FAIL", "Step09 step09_optics_bridge_summary.json is missing")
        return
    bridge = summary.get("bridge", {})
    smoke = summary.get("smoke_transport", {})
    be_r = float(next((w for w in bounds.get("WINDOWS", []) if w.get("name") == "Win_Be_Cryostat"), {}).get("r_max", float("nan")))
    source_paths = [
        ROOT / bridge.get("source", ""),
        ROOT / bridge.get("smoke_source", ""),
    ]
    stale_hits = []
    for path in source_paths:
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        if "127.66" in text or " 18.0" in text:
            stale_hits.append(rel(path))
    eventlist = ROOT / bridge.get("eventlist", "")
    first_z = None
    if eventlist.exists():
        first = eventlist.read_text(encoding="utf-8", errors="ignore").splitlines()[0].split()
        if len(first) >= 8:
            first_z = float(first[7])
    ok = (
        summary.get("status") == "PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED"
        and summary.get("claim_level") == "L1_OPTICS_EVENTLIST_BRIDGE"
        and int(bridge.get("rows_written", 0)) > 0
        and float(bridge.get("max_radius_cm", 999)) <= be_r + 1.0e-9
        and abs(float(bridge.get("z_plane_cm", 999)) - 16.051) <= 1.0e-9
        and first_z is not None
        and abs(first_z - 16.051) <= 1.0e-9
        and float(bridge.get("direction_uz_max", 1)) < 0.0
        and bool(smoke.get("sim_exists")) is True
        and int(smoke.get("stored_events", 0)) == 1000
        and not stale_hits
    )
    details = (
        f"status={summary.get('status')}; rows={bridge.get('rows_written')}; "
        f"max_radius_cm={bridge.get('max_radius_cm')} <= Be {be_r}; "
        f"z_plane={bridge.get('z_plane_cm')}; first_eventlist_z={first_z}; "
        f"uz_max={bridge.get('direction_uz_max')}; smoke_events={smoke.get('stored_events')}; "
        f"stale_hits={stale_hits}"
    )
    add(checks, "step09_optics_bridge", "PASS" if ok else "FAIL", details)


def check_stale_paths(checks: list[dict[str, Any]]) -> None:
    files = [
        ROOT / "README.md",
        ROOT / "MEMORY.md",
        ROOT / "workflow.md",
        ROOT / "stepwise_maintenance" / "CURRENT_PROGRESS_STEP_BREAKDOWN.md",
        ROOT / "code" / "tools" / "make_complete_day15_report_ADR.py",
        ROOT / "code" / "tools" / "make_day15_report_ADR.py",
        ROOT / "code" / "tools" / "make_new_geo_closure_report.py",
    ]
    patterns = [
        "instant_equiv2602_ADR_cmfix",
        "buildup_equiv2602_ADR_cmfix",
        "delay_fix_from_buildup",
        "decay_from_buildup",
        "cosima_full1m",
        "1094.2",
    ]
    hits = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        for pat in patterns:
            if pat in text:
                hits.append(f"{rel(path)} contains {pat}")
    add(checks, "no_live_stale_paths", "PASS" if not hits else "FAIL", "no stale background path tokens in live files" if not hits else "; ".join(hits))


def check_optics_policy(checks: list[dict[str, Any]]) -> None:
    readme = ROOT / "stepwise_maintenance" / "step04_opticsim" / "README.md"
    audit = load_json(ROOT / "stepwise_maintenance" / "step04_opticsim" / "outputs" / "step04_opticsim_audit.json", {})
    text = readme.read_text(encoding="utf-8", errors="ignore") if readme.exists() else ""
    bfull = audit.get("bfull_nominal_xopmap", {})
    focal_stats = bfull.get("focal_crossing_stats", {})
    checks_block = audit.get("checks", {})
    ok = (
        audit.get("status") == "PASS_BFULL_XOPMAP_EVENTLIST_READY"
        and "B-FULL" in text
        and "channel optics is not used" in text.lower()
        and checks_block.get("standard_geant4_em_enabled") is True
        and checks_block.get("process_base_is_g4vdiscreteprocess") is True
        and checks_block.get("external_xop_map_used") is True
        and checks_block.get("spot_inside_be_window") is True
    )
    details = (
        f"status={audit.get('status')}; model=B-FULL XOP-map; "
        f"focused_signal_within_be={focal_stats.get('within_be_rows')}; "
        f"diffracted_focal={focal_stats.get('diffracted_focal_rows')}; r99={focal_stats.get('r99_cm')}; "
        f"Be={focal_stats.get('be_radius_cm')}; channel_optics_used={audit.get('scope', {}).get('channel_optics_used')}"
    )
    add(checks, "optics_bfull_policy", "PASS" if ok else "FAIL", details)


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(f, "")) for f in fields) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    bounds = load_json(ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json", {})
    check_source_unit_guard(checks, bounds)
    check_geometry(checks, bounds)
    check_native_csi_veto_trigger(checks)
    check_production_paths(checks)
    check_fixed_source(checks)
    check_half_life_unit_audit(checks)
    check_csi_activation_baseline(checks)
    check_bgo_control_geometry(checks)
    check_review_20260531_closure(checks)
    check_timeline(checks)
    check_compton_geometry(checks)
    check_step06(checks)
    check_step07(checks, bounds)
    check_step08(checks)
    check_line_window_sensitivity(checks)
    check_spatial_line_proxy(checks)
    check_detector_coupled_focus_response(checks)
    check_step09(checks, bounds)
    check_stale_paths(checks)
    check_optics_policy(checks)

    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    payload = {"status": status, "checks": checks}
    (OUT / "validation_new_geo_re.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(OUT / "validation_new_geo_re.csv", checks, ["check", "status", "details"])
    md = "# NEW_GEO_RE Validation\n\n" + f"Status: **{status}**\n\n" + md_table(checks, ["check", "status", "details"]) + "\n"
    (OUT / "VALIDATION.md").write_text(md, encoding="utf-8")
    VALIDATION_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
