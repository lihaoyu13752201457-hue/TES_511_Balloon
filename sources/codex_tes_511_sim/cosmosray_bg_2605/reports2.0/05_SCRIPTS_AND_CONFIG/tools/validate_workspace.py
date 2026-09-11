#!/usr/bin/env python3
"""Validate the local extended cosmosray_bg_2605 workspace."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD = Path("/home/ubuntu/cosmosray_bg_2602")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def add(results: list[dict], name: str, status: str, details: str, **extra) -> None:
    row = {"check": name, "status": status, "details": details}
    row.update(extra)
    results.append(row)


def validate_geometry(results: list[dict]) -> None:
    files = [
        "TibetTES_v5_6layers.geo.setup",
        "TibetTES_v5_6layers.geo",
        "TibetTES_v5_6layers.det",
        "Intro_TibetTES.geo",
        "Materials_TibetTES.geo",
        "bounds.json",
    ]
    mismatches = []
    for name in files:
        local = ROOT / "XZTES" / name
        old = OLD / "XZTES" / name
        if not local.exists():
            mismatches.append(f"missing local {name}")
            continue
        if not old.exists():
            mismatches.append(f"missing old {name}")
            continue
        if sha256(local) != sha256(old):
            mismatches.append(name)
    add(
        results,
        "geometry_identity",
        "PASS" if not mismatches else "FAIL",
        "XZTES core geometry matches original" if not mismatches else "; ".join(mismatches),
    )

    required_links = [
        "TibetTES_v5_6layers.geo.setup",
        "TibetTES_v5_6layers.geo",
        "TibetTES_v5_6layers.det",
        "Intro_TibetTES.geo",
        "Materials_TibetTES.geo",
        "crossections",
    ]
    missing = [x for x in required_links if not (ROOT / x).exists()]
    add(
        results,
        "root_geometry_entrypoints",
        "PASS" if not missing else "FAIL",
        "root symlinks/crossections let package sources run from workspace root"
        if not missing
        else "missing: " + ", ".join(missing),
    )


def validate_fullsphere(results: list[dict]) -> None:
    manifest = read_csv(ROOT / "expacs_fullsphere_20bin_sources" / "manifest.csv")
    particles = sorted({r["particle"] for r in manifest})
    expected = ["alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p"]
    add(
        results,
        "fullsphere_component_count",
        "PASS" if len(manifest) == 160 and particles == expected else "FAIL",
        f"rows={len(manifest)} particles={particles}",
    )

    bad_bins = []
    for p in expected:
      rows = [r for r in manifest if r["particle"] == p]
      down = [r for r in rows if r["direction_tag"] == "atm_down"]
      up = [r for r in rows if r["direction_tag"] == "atm_up_albedo_like"]
      if len(rows) != 20 or len(down) != 10 or len(up) != 10:
          bad_bins.append(f"{p}: rows={len(rows)} down={len(down)} up={len(up)}")
    add(
        results,
        "fullsphere_down_up_bins",
        "PASS" if not bad_bins else "FAIL",
        "each particle has 10 down and 10 up equal-mu bins"
        if not bad_bins
        else "; ".join(bad_bins),
    )

    closure = read_csv(ROOT / "expacs_fullsphere_20bin_sources" / "flux_closure_audit.csv")
    max_dev = max(abs(float(r["fullsphere_to_main_ratio"]) - 1.0) for r in closure)
    add(
        results,
        "fullsphere_flux_closure",
        "PASS" if max_dev < 0.01 else "FAIL",
        f"max |ratio-1| = {max_dev:.6e}",
    )

    dp_dir = ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra_dp_2602units"
    dp_files = sorted(dp_dir.glob("*.dat"))
    bad = []
    for path in dp_files[:5]:
        lines = [l for l in path.read_text().splitlines() if not l.startswith("#")]
        if not lines or not lines[0].lower().startswith("ip") or sum(l.startswith("DP ") for l in lines) < 2:
            bad.append(path.name)
    add(
        results,
        "cosima_ready_spectra_dp",
        "PASS" if len(dp_files) == 160 and not bad else "FAIL",
        f"files={len(dp_files)} bad_sample={bad}",
    )

    sample = dp_dir / "p_bin09_theta87.13_pdf.dat"
    old_sample = OLD / "megalib_sources_v2" / "fixed_p_bin10.dat"
    try:
        sample_e = next(float(l.split()[1]) for l in sample.read_text().splitlines() if l.startswith("DP "))
        old_e = next(float(l.split()[1]) for l in old_sample.read_text().splitlines() if l.startswith("DP "))
        ratio = sample_e / old_e
        ok = math.isclose(ratio, 1.0, rel_tol=1e-9, abs_tol=1e-12)
        details = f"p bin first energy ratio to old 2602 = {ratio:.6e}"
    except Exception as exc:
        ok = False
        details = f"failed to compare sample energy axis: {exc}"
    add(
        results,
        "cosima_spectra_2602_energy_axis",
        "PASS" if ok else "FAIL",
        details,
    )


def validate_science(results: list[dict]) -> None:
    source = ROOT / "run_configs" / "Science_511_onaxis_focalbeam_local.source"
    text = source.read_text()
    ok = "Beam HomogeneousBeam 0.0 0.0 127.66 0.0 0.0 -1.0 18.0" in text
    add(
        results,
        "science_local_beam_token",
        "PASS" if ok else "FAIL",
        "uses Cosima-supported near-field HomogeneousBeam at Be entrance plane"
        if ok
        else "expected HomogeneousBeam line not found",
    )

    package_candidate = (ROOT / "science_511_onaxis_source" / "Science_511_onaxis_focaldisk_candidate.source").read_text()
    add(
        results,
        "science_package_candidate_token",
        "FIXED",
        "archive candidate uses version-sensitive NearFieldDiskSource; local run_config replaces it with HomogeneousBeam",
        archive_has_nearfielddisksource="NearFieldDiskSource" in package_candidate,
    )

    ledger = read_csv(ROOT / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv")
    rates_ok = True
    for r in ledger:
        expected = float(r["flux_ph_cm2_s"]) * float(r["A_opt_cm2"]) * float(r["T_atm"])
        got = float(r["rate_to_injection_plane_s^-1"])
        rates_ok = rates_ok and math.isclose(expected, got, rel_tol=2e-12, abs_tol=1e-18)
    add(
        results,
        "science_rate_ledger",
        "PASS" if rates_ok else "FAIL",
        "R = F_511 * A_opt * T_atm verified for ledger rows",
    )


def validate_time_variable(results: list[dict]) -> None:
    validation = read_csv(ROOT / "time_variable_balloon_background_curves_verified" / "validation_report.csv")
    statuses = sorted({r["status"] for r in validation})
    severe = [r for r in validation if r["status"] not in {"PASS", "WARN"}]
    add(
        results,
        "time_variable_validation_report",
        "PASS" if not severe else "FAIL",
        f"statuses={statuses}",
    )

    ts = read_csv(ROOT / "time_variable_balloon_background_curves_verified" / "expacs_flux_timeseries.csv")
    shapes = [float(r["lightcurve_shape"]) for r in ts]
    mn, mx = min(shapes), max(shapes)
    add(
        results,
        "prompt_lightcurve_nonflatness",
        "WARN" if math.isclose(mn, 1.0) and math.isclose(mx, 1.0) else "PASS",
        f"prompt shapes min={mn:.6e} max={mx:.6e}; WARN means EXPACS fallback produced static prompt curves",
    )

    sig = read_csv(ROOT / "time_variable_balloon_background_curves_verified" / "science_signal_lightcurve.csv")
    t_atm = [float(r["T_atm_511"]) for r in sig]
    add(
        results,
        "science_signal_atmosphere_curve",
        "PASS" if min(t_atm) > 0 and max(t_atm) <= 1 else "FAIL",
        f"T_atm_511 min={min(t_atm):.6e} max={max(t_atm):.6e}",
    )

    dp_dir = ROOT / "time_variable_balloon_background_curves_verified" / "lightcurves_dp"
    dp_files = sorted(dp_dir.glob("*.lc"))
    bad = []
    for path in dp_files[:5]:
        lines = path.read_text().splitlines()
        if not lines or not lines[0].lower().startswith("ip") or sum(l.startswith("DP ") for l in lines) < 2:
            bad.append(path.name)
    add(
        results,
        "cosima_ready_lightcurves_dp",
        "PASS" if len(dp_files) == 160 and not bad else "FAIL",
        f"files={len(dp_files)} bad_sample={bad}",
    )


def validate_delay_fix(results: list[dict]) -> None:
    source = ROOT / "run_configs" / "activation_decay_day15_groundstate_fixed_full1m_local.source"
    text = source.read_text()
    add(
        results,
        "delay_source_self_contained_geometry",
        "PASS" if "Geometry TibetTES_v5_6layers.geo.setup" in text else "FAIL",
        "local full1m delayed source uses workspace geometry entrypoint",
    )
    add(
        results,
        "delay_w183_w180_source_blocks_removed",
        "PASS" if "ParticleType 74183" not in text and "ParticleType 74180" not in text else "FAIL",
        f"ParticleType 74183 count={text.count('ParticleType 74183')}, 74180 count={text.count('ParticleType 74180')}",
    )

    summary = json.loads((ROOT / "delay_fix" / "source_fix_summary.json").read_text())
    add(
        results,
        "delay_fix_summary_loaded",
        "PASS",
        "source_fix_summary.json is present",
        summary_keys=sorted(summary.keys()),
    )


def validate_paths(results: list[dict]) -> None:
    offenders = []
    nondp = []
    for path in (ROOT / "run_configs").glob("*.source"):
        text = path.read_text(errors="replace")
        if (
            "/home/ubuntu/cosmosray_bg_2602" in text
            or "/home/ubuntu/cosmosray_bg_2605" in text
        ):
            offenders.append(str(path.relative_to(ROOT)))
        if path.name.startswith("Background_atm") and "cosima_spectra/" in text:
            nondp.append(str(path.relative_to(ROOT)))
        if path.name.startswith("Background_atm") and "cosima_spectra_dp_2602units/" not in text:
            nondp.append(str(path.relative_to(ROOT)))
        if "lightcurve" in path.name.lower() and "lightcurves/" in text:
            nondp.append(str(path.relative_to(ROOT)))
    add(
        results,
        "run_configs_no_old_absolute_paths",
        "PASS" if not offenders else "FAIL",
        "run_configs are local-path clean" if not offenders else ", ".join(offenders),
    )
    add(
        results,
        "run_configs_use_cosima_ready_tables",
        "PASS" if not nondp else "FAIL",
        "background run_configs point at 2602-compatible spectra and *_dp MFunction tables"
        if not nondp
        else ", ".join(nondp),
    )

    expected_particle_types = {
        "Atm_gamma_": "1",
        "Atm_n_": "6",
        "Atm_p_": "4",
        "Atm_alpha_": "21",
        "Atm_eminus_": "3",
        "Atm_eplus_": "2",
        "Atm_muminus_": "9",
        "Atm_muplus_": "8",
    }
    bad_types = []
    for path in (ROOT / "run_configs").glob("Background_atm*.source"):
        for line in path.read_text(errors="replace").splitlines():
            if ".ParticleType " not in line:
                continue
            left, value = line.split(".ParticleType ", 1)
            for prefix, expected in expected_particle_types.items():
                if left.startswith(prefix) and value.strip() != expected:
                    bad_types.append(f"{path.name}:{left}={value.strip()} expected {expected}")
    add(
        results,
        "run_configs_megalib_particle_types",
        "PASS" if not bad_types else "FAIL",
        "background run_configs use original MEGAlib particle IDs"
        if not bad_types
        else "; ".join(bad_types[:10]),
    )


def validate_nextphase_511(results: list[dict]) -> None:
    base = ROOT / "reports" / "nextphase_511"
    gate_a = base / "gate_A_source_placement" / "be_window_crossing_summary.json"
    gate_b = base / "gate_B_detector_response" / "detector_response_summary.json"
    line_sens = base / "science_line_models" / "sensitivity_by_line_model.csv"
    inventory = base / "time_variable_day1_day20" / "inventory" / "constant_limit_validation.json"
    source_build = ROOT / "production_runs" / "time_variable_delayed" / "source_build_summary.json"
    spatial = base / "activation_spatial_model" / "activation_source_spatial_summary.json"
    timing = base / "timing_window_scan" / "timing_window_scan_summary.csv"
    activation = base / "activation_511_diagnostics" / "activation_511_diagnostic_summary.json"
    likelihood = base / "likelihood_511" / "likelihood_sensitivity_by_model.csv"
    injection = base / "long_timeline_injection" / "injection_recovery_summary.csv"
    completion = base / "final_completion_report" / "completion_summary.json"

    if gate_a.exists():
        data = json.loads(gate_a.read_text())
        ok = bool(data.get("passed")) and math.isclose(float(data["source"]["z"]), 127.66, rel_tol=0.0, abs_tol=1.0e-9)
        add(
            results,
            "nextphase_gate_A_source_placement",
            "PASS" if ok else "FAIL",
            f"passed={data.get('passed')} source_z={data.get('source', {}).get('z')} clearance={data.get('clearance_source_minus_win_top')}",
        )
    else:
        add(results, "nextphase_gate_A_source_placement", "FAIL", "missing Gate A summary")

    if gate_b.exists():
        data = json.loads(gate_b.read_text())
        fwhm = float(data.get("science_peak_measured_fwhm_robust_keV", 0.0))
        ok = bool(data.get("passed")) and 0.05 < fwhm < 0.3
        add(
            results,
            "nextphase_gate_B_detector_response",
            "PASS" if ok else "FAIL",
            f"passed={data.get('passed')} measured_fwhm_keV={fwhm:.6g}",
        )
    else:
        add(results, "nextphase_gate_B_detector_response", "FAIL", "missing Gate B summary")

    if line_sens.exists():
        rows = read_csv(line_sens)
        mono_broad = [
            r for r in rows
            if r["model_id"] == "mono"
            and r["energy_window"] == "broad_480_550"
            and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
        ]
        wide_line = [
            r for r in rows
            if r["model_id"] == "gaussian_fwhm_2p5"
            and r["energy_window"] == "line_510p3_511p8"
            and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
        ]
        ok = bool(mono_broad and wide_line) and float(wide_line[0]["flux_3sigma_ph_cm2_s"]) > float(mono_broad[0]["flux_3sigma_ph_cm2_s"])
        add(
            results,
            "nextphase_science_line_sensitivity",
            "PASS" if ok else "FAIL",
            f"rows={len(rows)} mono_broad_1Ms={mono_broad[0]['flux_3sigma_ph_cm2_s'] if mono_broad else 'missing'} wide_line_1Ms={wide_line[0]['flux_3sigma_ph_cm2_s'] if wide_line else 'missing'}",
        )
    else:
        add(results, "nextphase_science_line_sensitivity", "FAIL", "missing sensitivity_by_line_model.csv")

    if inventory.exists():
        data = json.loads(inventory.read_text())
        ok = data.get("status") == "PASS" and float(data.get("reference_total_rel_diff", 1.0)) < 1.0e-12
        add(
            results,
            "nextphase_constant_inventory_limit",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} day15_total_rel_diff={float(data.get('reference_total_rel_diff', 1.0)):.3e}",
        )
    else:
        add(results, "nextphase_constant_inventory_limit", "WARN", "constant-profile inventory validation not yet generated")

    if source_build.exists():
        data = json.loads(source_build.read_text())
        ok = data.get("status") == "PASS" and data.get("day15_source_reproduces_template_fluxes") is True
        add(
            results,
            "nextphase_time_variable_source_scaling",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} day15_repro={data.get('day15_source_reproduces_template_fluxes')}",
        )
    else:
        add(results, "nextphase_time_variable_source_scaling", "WARN", "time-variable delayed source scaling not yet generated")

    if spatial.exists():
        data = json.loads(spatial.read_text())
        ok = data.get("status") == "PASS" and abs(float(data.get("normalization_closure_fraction", 1.0))) < 1.0e-12
        add(
            results,
            "nextphase_activation_spatial_model_audit",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} closure={float(data.get('normalization_closure_fraction', 1.0)):.3e} voxel_fraction={float(data.get('voxel_activity_fraction', 0.0)):.6g}",
        )
    else:
        add(results, "nextphase_activation_spatial_model_audit", "FAIL", "missing activation spatial summary")

    if timing.exists():
        rows = read_csv(timing)
        one_us = [r for r in rows if r["energy_window"] == "broad_480_550" and math.isclose(float(r["window_us"]), 1.0)]
        hundred_us = [r for r in rows if r["energy_window"] == "broad_480_550" and math.isclose(float(r["window_us"]), 100.0)]
        ok = bool(one_us and hundred_us) and float(one_us[0]["science_survival"]) > float(hundred_us[0]["science_survival"])
        add(
            results,
            "nextphase_timing_window_scan",
            "PASS" if ok else "FAIL",
            f"rows={len(rows)} 1us_survival={one_us[0]['science_survival'] if one_us else 'missing'} 100us_survival={hundred_us[0]['science_survival'] if hundred_us else 'missing'}",
        )
    else:
        add(results, "nextphase_timing_window_scan", "FAIL", "missing timing window scan")

    if activation.exists():
        data = json.loads(activation.read_text())
        top = data.get("top_nuclides_by_broad_final", [{}])[0]
        ok = data.get("status") == "PASS" and top.get("nuclide") == "W-187"
        add(
            results,
            "nextphase_activation_511_diagnostics",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} top_broad={top.get('nuclide')} rate={top.get('broad_480_550_final_cps')}",
        )
    else:
        add(results, "nextphase_activation_511_diagnostics", "FAIL", "missing activation diagnostic summary")

    if likelihood.exists():
        rows = read_csv(likelihood)
        broad_window = [
            r for r in rows
            if r["energy_window"] == "broad_480_550"
            and r["model"] == "window_counting_same_events"
            and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
        ]
        broad_spatial = [
            r for r in rows
            if r["energy_window"] == "broad_480_550"
            and r["model"] == "energy_radius_layer_template"
            and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
        ]
        ok = bool(broad_window and broad_spatial) and float(broad_spatial[0]["flux_3sigma_ph_cm2_s"]) < float(broad_window[0]["flux_3sigma_ph_cm2_s"])
        add(
            results,
            "nextphase_spatial_spectral_likelihood",
            "PASS" if ok else "FAIL",
            f"rows={len(rows)} broad_window={broad_window[0]['flux_3sigma_ph_cm2_s'] if broad_window else 'missing'} broad_spatial={broad_spatial[0]['flux_3sigma_ph_cm2_s'] if broad_spatial else 'missing'}",
        )
    else:
        add(results, "nextphase_spatial_spectral_likelihood", "FAIL", "missing likelihood sensitivity")

    if injection.exists():
        rows = read_csv(injection)
        hits = [
            r for r in rows
            if r["energy_window"] == "broad_480_550"
            and r["model"] == "energy_radius_layer_template"
            and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
            and abs(float(r["input_flux_ph_cm2_s"]) - 1.0e-4) < 1.0e-12
        ]
        ok = bool(hits) and abs(float(hits[0]["mean_recovered_flux"]) - 1.0e-4) < 1.0e-5
        add(
            results,
            "nextphase_long_timeline_injection",
            "PASS" if ok else "FAIL",
            f"rows={len(rows)} broad_spatial_1Ms_1e-4_mean={hits[0]['mean_recovered_flux'] if hits else 'missing'} P3={hits[0]['detection_probability_3sigma'] if hits else 'missing'}",
        )
    else:
        add(results, "nextphase_long_timeline_injection", "FAIL", "missing injection recovery summary")

    if completion.exists():
        data = json.loads(completion.read_text())
        pdf = base / "final_completion_report" / "COSMOSRAY_BG_2605_nextphase_completion_report.pdf"
        md = base / "final_completion_report" / "COSMOSRAY_BG_2605_nextphase_completion_report.md"
        ok = data.get("status") == "PASS_WITH_EXPLICIT_CAVEATS" and pdf.exists() and pdf.stat().st_size > 100_000 and md.exists()
        add(
            results,
            "nextphase_completion_report",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} pdf_exists={pdf.exists()} pdf_bytes={pdf.stat().st_size if pdf.exists() else 0}",
        )
    else:
        add(results, "nextphase_completion_report", "FAIL", "missing final completion summary")


def validate_phase2_real_flight(results: list[dict]) -> None:
    base = ROOT / "reports" / "phase2_real_flight_physical_production"
    authorities = base / "CURRENT_AUTHORITIES.md"
    env = base / "environment_grid_real" / "environment_grid_summary.json"
    prompt = base / "prompt_reweight_real" / "prompt_reweight_real_summary.json"
    inventory = base / "activation_inventory_parentfed" / "inventory_parentfed_summary.json"
    delayed = base / "delayed_sources_real_profile" / "source_build_summary.json"
    mixed = base / "mixed_voxel_transport" / "radial_vs_mixed_summary.json"
    catalog = base / "event_catalog_v2_measured" / "catalog_v2_summary.json"
    timing = base / "timing_daq" / "timing_daq_model_summary.json"
    truth = base / "activation_511_truth" / "activation_511_truth_summary.json"
    likelihood = base / "likelihood_profiled" / "profile_likelihood_template_summary.json"
    injection = base / "long_timeline_injection_profiled" / "source_injection_profiled_summary.json"
    summary = base / "phase2_summary.json"
    report_md = base / "phase2_real_flight_report.md"
    report_pdf = base / "phase2_real_flight_report.pdf"
    integrated_pdf = base / "phase2_integrated_summary_report_zh.pdf"

    if authorities.exists():
        text = authorities.read_text(errors="replace")
        ok = (
            "SUPERSEDED_INVALID_FOR_SCIENCE_RESPONSE" in text
            and "Legacy-not-current science beam: z=12.766, radius=1.8" in text
            and "current_authority = Gate-A corrected Be-window beam, z=127.66, radius=18.0 geometry units" in text
            and "current_response_cps_per_ph_cm2_s = 24.858993900839696" in text
        )
        add(
            results,
            "phase2_current_authorities",
            "PASS" if ok else "FAIL",
            "authority file marks old science placement as legacy-not-current and records current Gate-A authority"
            if ok
            else "authority file missing legacy-not-current marker or current Gate-A authority",
        )
    else:
        add(results, "phase2_current_authorities", "FAIL", "missing CURRENT_AUTHORITIES.md")

    if env.exists():
        data = json.loads(env.read_text())
        ok = (
            data.get("status") == "PASS"
            and data.get("physical_environment_available") is True
            and int(data.get("n_time_bins", 0)) >= 2
            and float(data.get("scale_max", 1.0)) > float(data.get("scale_min", 1.0))
        )
        add(
            results,
            "phase2_environment_grid_real",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} backend={data.get('backend')} bins={data.get('n_time_bins')} scale=[{data.get('scale_min')}, {data.get('scale_max')}]",
        )
    else:
        add(results, "phase2_environment_grid_real", "FAIL", "missing environment summary")

    if prompt.exists():
        data = json.loads(prompt.read_text())
        ok = data.get("status") == "PASS" and "particle_only" in data.get("metadata_level", "")
        add(
            results,
            "phase2_prompt_reweight_real",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} metadata={data.get('metadata_level')} min={data.get('real_profile_final_480_550_min_cps')} max={data.get('real_profile_final_480_550_max_cps')}",
        )
    else:
        add(results, "phase2_prompt_reweight_real", "FAIL", "missing prompt reweight summary")

    if inventory.exists():
        data = json.loads(inventory.read_text())
        ok = str(data.get("status", "")).startswith("PASS") and data.get("parent_feed_available") is False
        add(
            results,
            "phase2_activation_inventory_parentfed",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} parent_feed_available={data.get('parent_feed_available')} day15_activity={data.get('day15_total_activity_Bq')}",
        )
    else:
        add(results, "phase2_activation_inventory_parentfed", "FAIL", "missing inventory summary")

    if delayed.exists():
        data = json.loads(delayed.read_text())
        ok = data.get("status") == "PASS" and data.get("spatial_profile_mode") == "fixed_day15_scaled"
        add(
            results,
            "phase2_delayed_sources_real_profile",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} spatial_mode={data.get('spatial_profile_mode')} records={len(data.get('records', []))}",
        )
    else:
        add(results, "phase2_delayed_sources_real_profile", "FAIL", "missing delayed source summary")

    if mixed.exists():
        data = json.loads(mixed.read_text())
        ok = data.get("status") == "NOT_RUN_REQUIRES_COSIMA_TRANSPORT" and data.get("radial_vs_mixed_selected_rate_available") is False
        add(
            results,
            "phase2_mixed_voxel_gate",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} selected_rate_available={data.get('radial_vs_mixed_selected_rate_available')}",
        )
    else:
        add(results, "phase2_mixed_voxel_gate", "FAIL", "missing mixed voxel gate summary")

    if catalog.exists():
        data = json.loads(catalog.read_text())
        ok = data.get("status") == "PASS_WITH_BGO_EVENT_TOTAL_PROXY" and int(data.get("events", 0)) > 0
        add(
            results,
            "phase2_event_catalog_v2_measured",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} events={data.get('events')} bgo_mode={data.get('bgo_hit_mode')}",
        )
    else:
        add(results, "phase2_event_catalog_v2_measured", "FAIL", "missing catalog v2 summary")

    if timing.exists():
        data = json.loads(timing.read_text())
        ok = data.get("status") == "PASS_TOY_DAQ_MODELS" and len(data.get("models", [])) >= 4
        add(
            results,
            "phase2_timing_daq_models",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} models={len(data.get('models', []))}",
        )
    else:
        add(results, "phase2_timing_daq_models", "FAIL", "missing timing/DAQ summary")

    if truth.exists():
        data = json.loads(truth.read_text())
        ok = data.get("status") == "PASS_WITH_DECAY_PROXY" and data.get("top_broad_nuclide") == "W-187"
        add(
            results,
            "phase2_activation_511_truth",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} top_broad={data.get('top_broad_nuclide')} rows={data.get('rows')}",
        )
    else:
        add(results, "phase2_activation_511_truth", "FAIL", "missing activation truth summary")

    if likelihood.exists():
        data = json.loads(likelihood.read_text())
        ok = data.get("status") == "PASS_PROXY_PROFILE_LIKELIHOOD" and float(data.get("degradation_factor", 0.0)) > 1.0
        add(
            results,
            "phase2_profile_likelihood_proxy",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} degradation={data.get('degradation_factor')}",
        )
    else:
        add(results, "phase2_profile_likelihood_proxy", "FAIL", "missing profiled likelihood summary")

    if injection.exists():
        data = json.loads(injection.read_text())
        ok = data.get("status") == "PASS_PROXY_PROFILED_INJECTION" and int(data.get("rows", 0)) >= 100
        add(
            results,
            "phase2_profiled_injection_proxy",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')} rows={data.get('rows')}",
        )
    else:
        add(results, "phase2_profiled_injection_proxy", "FAIL", "missing profiled injection summary")

    if summary.exists():
        data = json.loads(summary.read_text())
        ok = data.get("status") == "PASS_PRELIMINARY_PHYSICAL_PROFILE_WITH_GATED_LIMITATIONS"
        add(
            results,
            "phase2_summary_status",
            "PASS" if ok else "FAIL",
            f"status={data.get('status')}",
        )
    else:
        add(results, "phase2_summary_status", "FAIL", "missing phase2_summary.json")

    if report_md.exists():
        text = report_md.read_text(errors="replace")
        needs_env = "real flight-profile" in text.lower() or "Real-Flight" in text
        has_required = env.exists() and inventory.exists()
        needs_like = "publication-level sensitivity" in text
        has_like = likelihood.exists() and injection.exists()
        ok = (not needs_env or has_required) and (not needs_like or has_like)
        add(
            results,
            "phase2_report_wording_guards",
            "PASS" if ok else "FAIL",
            f"needs_env={needs_env} has_env_inventory={has_required} needs_like={needs_like} has_like_injection={has_like}",
        )
    else:
        add(results, "phase2_report_wording_guards", "FAIL", "missing phase2 report markdown")

    ok_pdf = report_pdf.exists() and report_pdf.stat().st_size > 100_000
    add(
        results,
        "phase2_report_pdf",
        "PASS" if ok_pdf else "FAIL",
        f"pdf_exists={report_pdf.exists()} pdf_bytes={report_pdf.stat().st_size if report_pdf.exists() else 0}",
    )

    ok_integrated = integrated_pdf.exists() and integrated_pdf.stat().st_size > 100_000
    add(
        results,
        "phase2_integrated_summary_pdf",
        "PASS" if ok_integrated else "FAIL",
        f"pdf_exists={integrated_pdf.exists()} pdf_bytes={integrated_pdf.stat().st_size if integrated_pdf.exists() else 0}",
    )


def validate_phase2_convergence_patch(results: list[dict]) -> None:
    base = ROOT / "reports" / "phase2_convergence_patch"
    summary_path = base / "phase2_convergence_patch_summary.json"
    if not summary_path.exists():
        add(results, "phase2_convergence_patch_summary", "FAIL", "missing convergence patch summary")
        return

    data = json.loads(summary_path.read_text())

    authority = data.get("authority", {})
    ok_authority = (
        authority.get("status") == "PASS"
        and authority.get("current_beam_ok") is True
        and math.isclose(float(authority.get("current_response_cps_per_flux", 0.0)), 24.858993900839696, rel_tol=0.0, abs_tol=1e-12)
        and authority.get("active_report_old_response_present") is False
    )
    add(
        results,
        "phase2_convergence_authority",
        "PASS" if ok_authority else "FAIL",
        f"status={authority.get('status')} response={authority.get('current_response_cps_per_flux')} old_response_active={authority.get('active_report_old_response_present')}",
    )

    catalog = data.get("catalog", {})
    ok_catalog = (
        catalog.get("status") == "PASS"
        and float(catalog.get("max_stream_closure_relative_error", 1.0)) < 1.0e-6
        and catalog.get("veto_monotonic_all_pass") is True
        and catalog.get("background_template_science_contamination_found") is False
    )
    add(
        results,
        "phase2_convergence_catalog_closure",
        "PASS" if ok_catalog else "FAIL",
        (
            f"status={catalog.get('status')} max_rel={catalog.get('max_stream_closure_relative_error')} "
            f"bgo_flip={catalog.get('bgo_threshold_max_flip_fraction')}"
        ),
    )

    parma = data.get("parma", {})
    policy = base / "parma_scale_audit" / "parma_scale_policy.md"
    ok_parma = (
        parma.get("status") == "PASS"
        and policy.exists()
        and float(parma.get("scale_min", 1.0)) < 1.0
        and float(parma.get("scale_max", 1.0)) > 1.0
        and parma.get("decision") in {
            "UNCAPPED_ACCEPTABLE_WITH_SMALL_SYSTEMATIC",
            "SOFT_CAP_RECOMMENDED_FOR_SYSTEMATIC_BRACKET",
            "PARTICLE_SCALE_PROXY_ONLY_DO_NOT_CLAIM_EVENT_RESOLVED_REAL_PROFILE",
        }
    )
    add(
        results,
        "phase2_convergence_parma_policy",
        "PASS" if ok_parma else "FAIL",
        f"status={parma.get('status')} scale=[{parma.get('scale_min')}, {parma.get('scale_max')}] decision={parma.get('decision')}",
    )

    parent = data.get("parent_feed", {})
    ok_parent = (
        str(parent.get("status", "")).startswith("PASS")
        and parent.get("rate_change_applied") is False
        and (base / "parent_feed" / "top511_before_after_rates.csv").exists()
    )
    add(
        results,
        "phase2_convergence_parent_feed_scope",
        "PASS" if ok_parent else "FAIL",
        f"status={parent.get('status')} rate_change={parent.get('rate_change_applied')} nuclides={len(parent.get('patched_nuclides', []))}",
    )

    mixed = data.get("mixed_voxel", {})
    decision_md = base / "mixed_voxel_bound" / "voxel_transport_decision.md"
    ok_mixed = (
        mixed.get("status") == "PASS_BOUND_COMPLETE"
        and mixed.get("new_transport_run") is False
        and decision_md.exists()
        and float(mixed.get("max_bound_fraction_of_final_background", -1.0)) >= 0.0
    )
    add(
        results,
        "phase2_convergence_mixed_voxel_bound",
        "PASS" if ok_mixed else "FAIL",
        f"status={mixed.get('status')} decision={mixed.get('decision')} max_bound={mixed.get('max_bound_fraction_of_final_background')}",
    )

    bgo = data.get("bgo", {})
    bgo_csv = base / "bgo_perhit" / "bgo_threshold_sensitivity.csv"
    ok_bgo = (
        bgo.get("status") == "PASS_PROXY_QUANTIFIED_NO_PERHIT_TABLE"
        and bgo_csv.exists()
        and float(bgo.get("max_threshold_flip_fraction", 1.0)) < 0.01
    )
    add(
        results,
        "phase2_convergence_bgo_proxy",
        "PASS" if ok_bgo else "FAIL",
        f"status={bgo.get('status')} max_flip={bgo.get('max_threshold_flip_fraction')} decision={bgo.get('decision')}",
    )

    profile = data.get("profile", {})
    coverage_csv = base / "minimal_profile_likelihood" / "injection_coverage_summary.csv"
    ok_profile = (
        str(profile.get("status", "")).startswith("PASS")
        and coverage_csv.exists()
        and profile.get("robust_1e_4_1Ms_detection_claim_allowed") is False
        and float(profile.get("max_P3_at_1e_4_1Ms_energy_radius_layer", 1.0)) < 0.5
    )
    add(
        results,
        "phase2_convergence_profile_closure",
        "PASS" if ok_profile else "FAIL",
        (
            f"status={profile.get('status')} P3_1e-4_1Ms={profile.get('max_P3_at_1e_4_1Ms_energy_radius_layer')} "
            f"robust_claim={profile.get('robust_1e_4_1Ms_detection_claim_allowed')}"
        ),
    )

    report_pdf = base / "final_report" / "COSMOSRAY_BG_2605_Phase2_convergence_patch_report.pdf"
    report_md = base / "final_report" / "COSMOSRAY_BG_2605_Phase2_convergence_patch_report.md"
    ok_report = report_pdf.exists() and report_pdf.stat().st_size > 20_000 and report_md.exists()
    add(
        results,
        "phase2_convergence_patch_report",
        "PASS" if ok_report else "FAIL",
        f"pdf_exists={report_pdf.exists()} pdf_bytes={report_pdf.stat().st_size if report_pdf.exists() else 0}",
    )


def validate_phase2_convergence_patch_update(results: list[dict]) -> None:
    base = ROOT / "reports" / "phase2_convergence_patch_update"
    summary_path = base / "phase2_convergence_patch_update_summary.json"
    if not summary_path.exists():
        add(results, "phase2_convergence_patch_update_summary", "FAIL", "missing convergence patch update summary")
        return
    data = json.loads(summary_path.read_text())

    src = data.get("source_authority", {})
    ok_src = (
        src.get("status") == "PASS_SOURCE_AUTHORITY_WORDING_LOCKED"
        and int(src.get("unqualified_old_source_or_response_hits", 1)) == 0
        and math.isclose(float(src.get("current_response_cps_per_ph_cm2_s", 0.0)), 24.858993900839696, rel_tol=0.0, abs_tol=1e-12)
        and (base / "source_authority_update" / "source_authority_note.md").exists()
    )
    add(
        results,
        "phase2_update_source_authority_wording",
        "PASS" if ok_src else "FAIL",
        f"status={src.get('status')} unqualified_hits={src.get('unqualified_old_source_or_response_hits')} response={src.get('current_response_cps_per_ph_cm2_s')}",
    )

    parma = data.get("parma_outlier", {})
    ok_parma = (
        str(parma.get("status", "")).startswith("PASS_CONTRIBUTION_WEIGHTED")
        and float(parma.get("broad_fraction_from_scale_gt10", 1.0)) < 0.01
        and float(parma.get("line_fraction_from_scale_gt10", 1.0)) < 0.01
        and float(parma.get("hard_cap_broad_relative_difference", 1.0)) < 0.01
        and float(parma.get("hard_cap_line_relative_difference", 1.0)) < 0.01
        and (base / "parma_outlier_audit" / "parma_scale_contribution.csv").exists()
    )
    add(
        results,
        "phase2_update_parma_outlier_contribution",
        "PASS" if ok_parma else "FAIL",
        (
            f"status={parma.get('status')} gt10={parma.get('broad_fraction_from_scale_gt10')}/"
            f"{parma.get('line_fraction_from_scale_gt10')} hard_shift={parma.get('hard_cap_broad_relative_difference')}/"
            f"{parma.get('hard_cap_line_relative_difference')}"
        ),
    )

    parent = data.get("parent_feed", {})
    ok_parent = (
        parent.get("status") == "PASS_PARENT_FEED_TOP_CONTRIBUTOR_DATA_NOTE"
        and parent.get("rate_change_applied") is False
        and "O-15" in parent.get("beta_plus_line_caveat_nuclides", [])
        and (base / "parent_feed_data_note" / "parent_feed_top_contributors_note.md").exists()
    )
    add(
        results,
        "phase2_update_parent_feed_data_note",
        "PASS" if ok_parent else "FAIL",
        f"status={parent.get('status')} rate_change={parent.get('rate_change_applied')} beta_caveats={parent.get('beta_plus_line_caveat_nuclides')}",
    )

    mixed = data.get("mixed_voxel", {})
    ok_mixed = (
        mixed.get("status") == "PASS_SYSTEMATIC_FREEZE_NO_DELTA_TRANSPORT"
        and mixed.get("new_transport_run") is False
        and 0.0 < float(mixed.get("max_assigned_systematic_fraction", 0.0)) < 0.02
        and (base / "mixed_voxel_delta" / "mixed_voxel_systematic_freeze.md").exists()
    )
    add(
        results,
        "phase2_update_mixed_voxel_systematic_freeze",
        "PASS" if ok_mixed else "FAIL",
        f"status={mixed.get('status')} max_systematic={mixed.get('max_assigned_systematic_fraction')} new_transport={mixed.get('new_transport_run')}",
    )

    claim = data.get("claim_control", {})
    ok_claim = (
        claim.get("status") == "PASS_CLAIM_CONTROL_PATCH"
        and (base / "claim_control" / "allowed_claims.md").exists()
        and (base / "claim_control" / "forbidden_claims.md").exists()
        and (base / "claim_control" / "final_conclusion_patch.md").exists()
    )
    add(
        results,
        "phase2_update_claim_control",
        "PASS" if ok_claim else "FAIL",
        f"status={claim.get('status')} allowed={claim.get('allowed_claims')} forbidden={claim.get('forbidden_claims')}",
    )


def validate_511_source_cases(results: list[dict]) -> None:
    base = ROOT / "reports2.0" / "09_SOURCE_CASES_ABC"
    summary_path = base / "source_case_summary.json"
    config_path = ROOT / "configs" / "astro_source_cases" / "source_cases_511_ABC.yaml"
    cosima_manifest_path = base / "cosima_source_manifest.csv"
    if not summary_path.exists():
        add(results, "source_cases_abc_summary", "FAIL", "missing reports2.0/09_SOURCE_CASES_ABC/source_case_summary.json")
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    checks = summary.get("checks", {})
    authority = summary.get("authority", {})
    config_text = config_path.read_text(encoding="utf-8", errors="ignore") if config_path.exists() else ""

    ok_authority = (
        config_path.exists()
        and "run_configs/Science_511_onaxis_focalbeam_local.source" in config_text
        and "Do not rename generic Be-window source" in config_text
        and math.isclose(float(authority.get("current_response_cps_per_flux", 0.0)), 24.858993900839696, rel_tol=0.0, abs_tol=1e-12)
    )
    add(
        results,
        "source_cases_abc_authority",
        "PASS" if ok_authority else "FAIL",
        f"status={summary.get('status')} response={authority.get('current_response_cps_per_flux')} config={config_path.exists()}",
    )

    closure = float(checks.get("A_point_source_current_response_closure_relative_error", 1.0))
    add(
        results,
        "source_cases_abc_A_response_closure",
        "PASS" if closure <= 1e-12 else "FAIL",
        f"relative_error={closure}",
    )

    b_frac = float(checks.get("B_default_diffuse_to_instrument_background_fraction", 1.0))
    b_ok = (
        checks.get("B_handling") == "aperture_integral_no_focal_spot_source"
        and b_frac < 1e-4
        and (base / "diffuse_aperture_foreground.csv").exists()
        and (base / "figures" / "B_diffuse_flux_fraction_vs_fov.png").exists()
    )
    add(
        results,
        "source_cases_abc_B_aperture_foreground",
        "PASS" if b_ok else "FAIL",
        f"handling={checks.get('B_handling')} Bfrac={b_frac}",
    )

    c_energy = float(checks.get("C_redshift_z0p10_observed_energy_keV", 0.0))
    c_status = str(checks.get("C_redshift_bandpass_status", ""))
    c_ok = 464.0 < c_energy < 465.0 and "REDSHIFTED_BELOW_480" in c_status and (base / "v404_bandpass_loss.csv").exists()
    add(
        results,
        "source_cases_abc_C_bandpass_risk",
        "PASS" if c_ok else "FAIL",
        f"Eobs={c_energy} status={c_status}",
    )

    if cosima_manifest_path.exists():
        rows = read_csv(cosima_manifest_path)
        b_written = [r for r in rows if r.get("case_prefix") == "B_GC_DIFFUSE" and str(r.get("status", "")).startswith("WRITTEN")]
        a_sources = [r for r in rows if r.get("case_prefix") == "A_GC_POINT" and r.get("status") == "WRITTEN"]
        risk_rows = [r for r in rows if r.get("status") == "WRITTEN_BANDPASS_RISK_CANDIDATE"]
        ok_manifest = not b_written and len(a_sources) >= 2 and risk_rows
        details = f"A_written={len(a_sources)} B_written={len(b_written)} risk_candidates={len(risk_rows)}"
    else:
        ok_manifest = False
        details = "missing cosima_source_manifest.csv"
    add(results, "source_cases_abc_cosima_manifest", "PASS" if ok_manifest else "FAIL", details)

    required = [
        base / "source_case_summary.md",
        base / "detectability_A_GC_POINT.csv",
        base / "source_spectrum_summary.csv",
        base / "artifact_manifest.csv",
        ROOT / "reports2.0" / "05_SCRIPTS_AND_CONFIG" / "tools" / "make_511_source_case_report.py",
        ROOT / "run_configs" / "astro_cases" / "Science511_A_GC_POINT_mono_511.source",
        base / "configs" / "source_cases_511_ABC.yaml",
        base / "spectra" / "gaussian_fwhm_1p5.dat",
        base / "run_configs" / "astro_cases" / "Science511_A_GC_POINT_mono_511.source",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    add(
        results,
        "source_cases_abc_artifacts",
        "PASS" if not missing else "FAIL",
        "all required source-case artifacts present" if not missing else "missing: " + ", ".join(missing),
    )


def validate_phase10_point_diffuse(results: list[dict]) -> None:
    try:
        from validate_phase10_point_diffuse import validate as validate_phase10  # noqa: WPS433
    except Exception as exc:
        add(results, "phase10_validator_import", "FAIL", f"failed to import Phase 10 validator: {exc}")
        return
    phase10_results: list[dict] = []
    try:
        validate_phase10(phase10_results)
    except Exception as exc:
        add(results, "phase10_validator_runtime", "FAIL", f"Phase 10 validator raised: {exc}")
        return
    results.extend(phase10_results)


def validate_phase11_metric_reconciliation(results: list[dict]) -> None:
    validators = [
        ("phase11_metric_crosswalk", "validate_phase11_metric_crosswalk"),
        ("phase11_selection_upgrade", "validate_phase11_selection_upgrade"),
        ("phase11_optics_schema", "validate_phase11_optics_schema"),
        ("phase11_claim_control", "validate_phase11_claim_control"),
    ]
    for label, module_name in validators:
        try:
            module = __import__(module_name, fromlist=["validate"])
        except Exception as exc:
            add(results, f"{label}_validator_import", "FAIL", f"failed to import {module_name}: {exc}")
            continue
        try:
            module.validate(results)
        except Exception as exc:
            add(results, f"{label}_validator_runtime", "FAIL", f"{module_name}.validate raised: {exc}")


def validate_phase12_final_closure(results: list[dict]) -> None:
    try:
        from validate_phase12_final_closure import validate as validate_phase12  # noqa: WPS433
    except Exception as exc:
        add(results, "phase12_validator_import", "FAIL", f"failed to import Phase 12 validator: {exc}")
        return
    try:
        validate_phase12(results)
    except Exception as exc:
        add(results, "phase12_validator_runtime", "FAIL", f"Phase 12 validator raised: {exc}")


def validate_firstprinciples_optics(results: list[dict]) -> None:
    try:
        from validate_firstprinciples_optics import validate as validate_firstprinciples  # noqa: WPS433
    except Exception as exc:
        add(results, "firstprinciples_optics_validator_import", "FAIL", f"failed to import first-principles optics validator: {exc}")
        return

    optics_results: list[dict] = []
    try:
        validate_firstprinciples(optics_results)
    except Exception as exc:
        add(results, "firstprinciples_optics_validator_runtime", "FAIL", f"first-principles optics validator raised: {exc}")
        return
    results.extend(optics_results)

    report = ROOT / "reports2.0" / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "first_principles_channeling_optics"
    required = [
        "README.md",
        "first_principles_optics_coupling_summary.json",
        "phase12_firstprinciples_optics_coupling.csv",
        "optics_response_firstprinciples_channeling_v1.yaml",
        "first_principles_claim_boundary.md",
        "first_principles_matrix_summary.csv",
        "optics_response_matrix_coarse.npz",
        "optics_response_matrix_coarse_summary.json",
    ]
    missing = [name for name in required if not (report / name).exists()]
    add(
        results,
        "firstprinciples_phase12_coupling_artifacts",
        "PASS" if not missing else "FAIL",
        "all first-principles coupling artifacts are present" if not missing else "missing: " + ", ".join(missing),
    )
    summary_path = report / "first_principles_optics_coupling_summary.json"
    if not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ok = (
        summary.get("status") == "PASS_FIRST_PRINCIPLES_OPTICS_COUPLED"
        and summary.get("claim_level") == "FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT"
        and summary.get("cam511_calibration_used") is False
        and summary.get("production_optics_response") is False
        and summary.get("hard_checks_pass") is True
        and float(summary.get("firstprinciples_aeff_cm2", 0.0)) > 0.0
    )
    add(
        results,
        "firstprinciples_phase12_coupling_guard",
        "PASS" if ok else "FAIL",
        (
            f"status={summary.get('status')} claim={summary.get('claim_level')} "
            f"aeff={summary.get('firstprinciples_aeff_cm2')} production={summary.get('production_optics_response')}"
        ),
    )


def validate_no_direct_scaling_alignment(results: list[dict]) -> None:
    try:
        from validate_no_direct_scaling_alignment import validate as validate_alignment  # noqa: WPS433
    except Exception as exc:
        add(results, "no_direct_scaling_alignment_validator_import", "FAIL", f"failed to import validator: {exc}")
        return
    root = ROOT / "reports2.0" / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "no_direct_scaling_optics_alignment"
    try:
        alignment_results = validate_alignment(root)
    except Exception as exc:
        add(results, "no_direct_scaling_alignment_validator_runtime", "FAIL", f"validator raised: {exc}")
        return
    for row in alignment_results:
        add(results, f"no_direct_scaling_{row['check']}", row["status"], row["details"])


def _validate_equiv_summary(results: list[dict], mode: str, expected_events: int) -> None:
    path = ROOT / "production_runs" / f"{mode}_equiv2602" / "run_summary.csv"
    if not path.exists():
        add(results, f"production_{mode}_summary", "FAIL", f"missing {path.relative_to(ROOT)}")
        return
    rows = read_csv(path)
    failures = [r for r in rows if r["status"] == "FAIL"]
    requested = sum(int(r["events"]) for r in rows)
    generated = sum(int(r["generated_particles"] or 0) for r in rows)
    sim_gb = sum(int(r["sim_size_bytes"]) for r in rows) / 1e9
    ok = len(rows) == 60 and not failures and requested == generated == expected_events
    add(
        results,
        f"production_{mode}_summary",
        "PASS" if ok else "FAIL",
        f"jobs={len(rows)} failures={len(failures)} generated={generated}/{requested} sim_gb={sim_gb:.6f}",
    )


def validate_full_production(results: list[dict]) -> None:
    expected = 25_210_216
    _validate_equiv_summary(results, "instant", expected)
    _validate_equiv_summary(results, "buildup", expected)

    fixed_dir = ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602"
    fixed_source = fixed_dir / "activation_decay_day15_groundstate_fixed.source"
    summary_path = fixed_dir / "source_fix_summary.json"
    if fixed_source.exists() and summary_path.exists():
        text = fixed_source.read_text(errors="replace")
        summary = json.loads(summary_path.read_text())
        blocks = text.count("DecayRun.Source ")
        total_flux = sum(float(m.group(1)) for m in re.finditer(r"\.Flux\s+([-+0-9.eE]+)", text))
        ok = (
            blocks == 5156
            and "ParticleType 74183" not in text
            and "ParticleType 74180" not in text
            and summary.get("source_blocks_removed") == 120
            and math.isclose(total_flux, 823.9513812643273, rel_tol=5e-9)
        )
        add(
            results,
            "production_delay_fix_full_source",
            "PASS" if ok else "FAIL",
            (
                f"blocks={blocks} removed={summary.get('source_blocks_removed')} "
                f"activity_bq={total_flux:.8e} W183/W180 residual="
                f"{text.count('ParticleType 74183')}/{text.count('ParticleType 74180')}"
            ),
        )
    else:
        add(results, "production_delay_fix_full_source", "FAIL", "missing fixed source or summary")

    full_log = fixed_dir / "cosima_full1m.log"
    full_sim = fixed_dir / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
    if full_log.exists() and full_sim.exists():
        log_text = full_log.read_text(errors="replace")
        m = re.search(r"Total number of generated particles:\s+(\d+)", log_text)
        generated = int(m.group(1)) if m else -1
        ok = generated == 1_000_000 and full_sim.stat().st_size > 0
        add(
            results,
            "production_delay_fix_full_cosima",
            "PASS" if ok else "FAIL",
            f"generated={generated}/1000000 sim_gb={full_sim.stat().st_size / 1e9:.6f}",
        )
    else:
        add(results, "production_delay_fix_full_cosima", "FAIL", "missing full delayed log or SIM")


def write_reports(results: list[dict]) -> None:
    outdir = ROOT / "reports"
    outdir.mkdir(exist_ok=True)
    (outdir / "workspace_validation.json").write_text(json.dumps(results, indent=2) + "\n")
    lines = ["# Workspace Validation", ""]
    for r in results:
        extra = {k: v for k, v in r.items() if k not in {"check", "status", "details"}}
        lines.append(f"- {r['status']}: {r['check']} - {r['details']}")
        if extra:
            lines.append(f"  extra: `{json.dumps(extra, sort_keys=True)}`")
    (outdir / "workspace_validation.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    results: list[dict] = []
    validate_geometry(results)
    validate_fullsphere(results)
    validate_science(results)
    validate_time_variable(results)
    validate_delay_fix(results)
    validate_paths(results)
    validate_nextphase_511(results)
    validate_phase2_real_flight(results)
    validate_phase2_convergence_patch(results)
    validate_phase2_convergence_patch_update(results)
    validate_511_source_cases(results)
    validate_phase10_point_diffuse(results)
    validate_phase11_metric_reconciliation(results)
    validate_phase12_final_closure(results)
    validate_firstprinciples_optics(results)
    validate_no_direct_scaling_alignment(results)
    validate_full_production(results)
    write_reports(results)
    hard_fail = any(r["status"] == "FAIL" for r in results)
    for r in results:
        print(f"{r['status']:5} {r['check']}: {r['details']}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
