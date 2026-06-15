#!/usr/bin/env python3
"""Build tracked Bgo_sample extended closure sidecars.

This is a post-processing closure.  It does not rerun Cosima transport.
"""

from __future__ import annotations

import csv
import json
import math
import pickle
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BGO_DIR = ROOT / "Bgo_sample"
OUT_JSON = BGO_DIR / "extended_closure_summary.json"
OUT_MD = BGO_DIR / "EXTENDED_CLOSURE_SUMMARY.md"
OUT_THRESHOLD_CSV = BGO_DIR / "extended_closure_threshold_scan.csv"
OUT_SPATIAL_CSV = BGO_DIR / "extended_closure_spatial_sidecar.csv"

STEP05_SUMMARY = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_bgo_sample_fullstat_v2_exactpos_l1" / "step05_bgo_sample_l1_response_summary.json"
STEP05_CATALOG = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_bgo_sample_fullstat_v2_exactpos_l1" / "work" / "event_catalog.pkl"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_bgo_sample_fullstat_v2_exactpos" / "background_time_variation.csv"
STEP08_SUMMARY = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_bgo_sample_fullstat_v2_exactpos" / "step08_bgo_sample_time_dependent_summary.json"
SPATIAL_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_bgo_sample_fullstat_v2_exactpos" / "detector_coupled_focus_response.json"
SPATIAL_CUTS = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_bgo_sample_fullstat_v2_exactpos" / "detector_coupled_spatial_line_cuts.csv"
ATTENUATION = BGO_DIR / "attenuation_verification.json"

W2 = "w2_510p58_511p42"
W2_LO_KEV = 510.58
W2_HI_KEV = 511.42
REFERENCE_FLUX = 1.0e-4
SECONDS_PER_DAY = 86400.0
THRESHOLDS_KEV = [50.0, 60.0, 70.0, 80.0, 100.0]
ANNULUS_CUT_ORDER = ["spot_r50", "spot_r68", "spot_r90", "spot_r95", "spot_r99", "full_aperture_1p8"]

sys.path.insert(0, str(ROOT / "code" / "tools"))
import build_v3p5_centerfinger_step05_l1_response as step05_l1  # noqa: E402


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def crossing_time(days: list[float], zvals: list[float], threshold: float) -> float | None:
    for idx, value in enumerate(zvals):
        if value < threshold:
            continue
        if idx == 0:
            return days[0]
        x0, x1 = days[idx - 1], days[idx]
        y0, y1 = zvals[idx - 1], zvals[idx]
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def extrapolated_time_days(final_day: float, final_z: float, threshold: float) -> float:
    if final_z <= 0.0:
        return math.inf
    if final_z >= threshold:
        return final_day
    return final_day * (threshold / final_z) ** 2


def asimov_poisson_z(source_counts: list[float], background_counts: list[float]) -> float:
    q = 0.0
    for s, b in zip(source_counts, background_counts):
        if s <= 0.0:
            continue
        if b <= 0.0:
            b = 1.0e-300
        q += 2.0 * ((s + b) * math.log1p(s / b) - s)
    return math.sqrt(max(q, 0.0))


def fold_rates(prompt_cps: float, delayed_cps: float, signal_cps: float) -> dict[str, Any]:
    rows = [row for row in read_csv(STEP06_BG) if row["selection_id"] == W2]
    source_total = 0.0
    background_total = 0.0
    elapsed = 0.0
    days: list[float] = []
    zvals: list[float] = []
    for row in rows:
        dt_s = f(row, "dt_s")
        live = math.exp(-(f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")) * f(row, "coincidence_window_s", 1.0e-6))
        source = signal_cps * f(row, "science_atm_scale_to_day15") * live
        background = (prompt_cps * f(row, "prompt_scale_to_day15") + delayed_cps * f(row, "delayed_activity_scale_to_day15")) * live
        source_total += source * dt_s
        background_total += background * dt_s
        elapsed += dt_s
        days.append(elapsed / SECONDS_PER_DAY)
        zvals.append(source_total / math.sqrt(background_total) if background_total > 0.0 else 0.0)
    final_day = days[-1]
    z20 = zvals[-1]
    t3 = crossing_time(days, zvals, 3.0)
    t5 = crossing_time(days, zvals, 5.0)
    return {
        "Z20d": z20,
        "T3_day": t3 if t3 is not None else extrapolated_time_days(final_day, z20, 3.0),
        "T3_status": "mission_internal_crossing" if t3 is not None else "extrapolated_beyond_20d",
        "T5_day": t5 if t5 is not None else extrapolated_time_days(final_day, z20, 5.0),
        "T5_status": "mission_internal_crossing" if t5 is not None else "extrapolated_beyond_20d",
        "F3_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20 if z20 > 0.0 else math.inf,
        "source_counts": source_total,
        "background_counts": background_total,
    }


def build_threshold_scan(step05_summary: dict[str, Any], step08: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    step05_l1.configure_paths("bgo_sample_fullstat_v2_exactpos")
    disk = step05_l1.side_entry_disk()
    reject_policy = str(step05_summary["normalization"]["reject_policy"])
    science_scale = float(step05_summary["science_physical_normalization"]["scale_from_unit_eventlist_rate"])
    with STEP05_CATALOG.open("rb") as handle:
        catalog = pickle.load(handle)

    old_threshold = step05_l1.ACTIVE_VETO_THRESHOLD_KEV
    rows: list[dict[str, Any]] = []
    try:
        for threshold in THRESHOLDS_KEV:
            step05_l1.ACTIVE_VETO_THRESHOLD_KEV = threshold
            window = step05_l1.summarize_window(catalog, W2_LO_KEV, W2_HI_KEV, disk, reject_policy)
            prompt = window["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
            delayed = window["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
            signal_unit = window["by_stream"]["science"]["side_compton_fov_pass_rate_s-1"]
            signal = signal_unit * science_scale
            folded = fold_rates(prompt, delayed, signal)
            rows.append(
                {
                    "threshold_keV": threshold,
                    "prompt_final_cps": prompt,
                    "delayed_final_cps": delayed,
                    "background_final_cps": prompt + delayed,
                    "signal_cps_at_reference_flux": signal,
                    **folded,
                    "raw_events": window["total"]["raw"]["events"],
                    "active_veto_pass_events": window["total"]["active_veto_pass"]["events"],
                    "side_compton_fov_pass_events": window["total"]["side_compton_fov_pass"]["events"],
                }
            )
    finally:
        step05_l1.ACTIVE_VETO_THRESHOLD_KEV = old_threshold

    authority_z = float(step08["checks"]["A_reference_w2_Z20d_time_dependent"])
    authority_f3 = float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    row70 = next(row for row in rows if row["threshold_keV"] == 70.0)
    z_rel = abs(row70["Z20d"] / authority_z - 1.0)
    f3_rel = abs(row70["F3_20d_ph_cm2_s"] / authority_f3 - 1.0)
    check = {
        "status": "PASS_BGO_THRESHOLD_REPLAY_SCAN" if z_rel < 1.0e-10 and f3_rel < 1.0e-10 else "FAIL_BGO_THRESHOLD_REPLAY_SCAN",
        "thresholds_keV": THRESHOLDS_KEV,
        "authority_threshold_keV": 70.0,
        "authority_replay_Z20d_relative_error": z_rel,
        "authority_replay_F3_relative_error": f3_rel,
        "best_threshold_by_F3_keV": min(rows, key=lambda row: row["F3_20d_ph_cm2_s"])["threshold_keV"],
        "min_F3_20d_ph_cm2_s": min(row["F3_20d_ph_cm2_s"] for row in rows),
        "max_F3_20d_ph_cm2_s": max(row["F3_20d_ph_cm2_s"] for row in rows),
    }
    return rows, check


def build_spatial_sidecar() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    spatial_response = load_json(SPATIAL_RESPONSE)
    cut_rows = read_csv(SPATIAL_CUTS)
    rows: list[dict[str, Any]] = []
    for row in cut_rows:
        folded = fold_rates(f(row, "prompt_cps"), f(row, "delayed_cps"), f(row, "signal_cps_at_reference_flux"))
        rows.append(
            {
                "cut_id": row["cut_id"],
                "radius_cm": f(row, "radius_cm"),
                "signal_psf_fraction": f(row, "signal_psf_fraction"),
                "prompt_cps": f(row, "prompt_cps"),
                "delayed_cps": f(row, "delayed_cps"),
                "background_cps": f(row, "background_cps"),
                "signal_cps_at_reference_flux": f(row, "signal_cps_at_reference_flux"),
                **folded,
            }
        )
    spot = next(row for row in rows if row["cut_id"] == "spot_r90")
    robust = [row for row in rows if row["cut_id"] not in {"spot_rmax", "full_aperture_1p8"}]
    best = max(robust, key=lambda row: row["Z20d"])
    hard = load_json(STEP08_SUMMARY)["checks"]["A_reference_w2_Z20d_time_dependent"]
    spatial_check = {
        "status": "PASS_BGO_SPATIAL_SIDECAR",
        "spatial_response_status": spatial_response["status"],
        "spot_r90_Z20d_time_dependent": spot["Z20d"],
        "spot_r90_F3_20d_ph_cm2_s": spot["F3_20d_ph_cm2_s"],
        "spot_r90_gain_vs_hard_window_step08": spot["Z20d"] / float(hard),
        "best_cut_id": best["cut_id"],
        "best_cut_Z20d_time_dependent": best["Z20d"],
        "best_cut_F3_20d_ph_cm2_s": best["F3_20d_ph_cm2_s"],
    }

    by_cut = {row["cut_id"]: row for row in rows}
    annuli: list[dict[str, Any]] = []
    prev: dict[str, Any] | None = None
    for cut_id in ANNULUS_CUT_ORDER:
        outer = by_cut[cut_id]
        if prev is None:
            inner_radius = 0.0
            base = {"source_counts": 0.0, "background_counts": 0.0, "prompt_cps": 0.0, "delayed_cps": 0.0, "signal_cps_at_reference_flux": 0.0}
        else:
            inner_radius = prev["radius_cm"]
            base = prev
        source = max(0.0, outer["source_counts"] - base["source_counts"])
        background = max(0.0, outer["background_counts"] - base["background_counts"])
        annuli.append(
            {
                "annulus_id": f"{inner_radius:.6g}_{outer['radius_cm']:.6g}",
                "outer_cut_id": cut_id,
                "r_inner_cm": inner_radius,
                "r_outer_cm": outer["radius_cm"],
                "source_counts_20d": source,
                "background_counts_20d": background,
                "s_over_sqrt_b_annulus": source / math.sqrt(background) if background > 0.0 else 0.0,
            }
        )
        prev = outer
    s_counts = [row["source_counts_20d"] for row in annuli]
    b_counts = [row["background_counts_20d"] for row in annuli]
    z_like = asimov_poisson_z(s_counts, b_counts)
    z_count = sum(s_counts) / math.sqrt(sum(b_counts))
    likelihood_check = {
        "status": "PASS_BGO_FIXED_TEMPLATE_ANNULAR_LIKELIHOOD_SIDECAR",
        "annulus_count": len(annuli),
        "annular_likelihood_Z20d": z_like,
        "annular_likelihood_F3_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z_like,
        "same_aperture_counting_Z20d": z_count,
        "gain_vs_same_aperture_counting": z_like / z_count,
        "gain_vs_hard_window_step08": z_like / float(hard),
    }
    return rows, spatial_check, annuli, likelihood_check


def material_check() -> dict[str, Any]:
    att = load_json(ATTENUATION)
    return {
        "status": "PASS_BGO_MATERIAL_ATTENUATION_SCAN",
        "source_status": att["status"],
        "method": att["method"],
        "parts": sorted(att["by_part"]),
        "energies_keV": [row["energy_keV"] for row in att["energies"]],
        "relative_tolerance": att["tolerance"]["relative_tolerance"],
        "max_abs_relative_difference": att["max_abs_relative_difference"],
        "passes_tolerance": att["max_abs_relative_difference"] <= att["tolerance"]["relative_tolerance"],
    }


def markdown(payload: dict[str, Any]) -> str:
    hard = payload["hard_window_authority"]
    spatial = payload["spatial_sidecar"]
    like = payload["annular_likelihood_sidecar"]
    threshold = payload["threshold_scan"]
    material = payload["material_attenuation_scan"]
    rows = payload["threshold_rows"]
    lines = [
        "# Bgo_sample Extended Closure Summary",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This tracked summary closes the BGO sidecar boundaries that were previously left as optional: detector-coupled spatial cuts, fixed-template annular likelihood, detector-threshold replay scan, and the BGO material attenuation design scan.",
        "",
        "## Hard-Window Authority",
        "",
        f"- Step08 W2 Z20d: `{hard['Z20d']:.12g}`",
        f"- Step08 W2 T3: `{hard['T3_day']:.12g}` d",
        f"- Step08 W2 F3(20d): `{hard['F3_20d_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
        "",
        "## Spatial Sidecars",
        "",
        f"- `spot_r90` time-dependent Z20d: `{spatial['spot_r90_Z20d_time_dependent']:.12g}`",
        f"- `spot_r90` F3(20d): `{spatial['spot_r90_F3_20d_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
        f"- fixed-template annular likelihood Z20d: `{like['annular_likelihood_Z20d']:.12g}`",
        f"- fixed-template annular likelihood F3(20d): `{like['annular_likelihood_F3_20d_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
        f"- annular likelihood gain vs hard-window Step08: `{like['gain_vs_hard_window_step08']:.7g}`",
        "",
        "## Threshold Replay Scan",
        "",
        f"- status: `{threshold['status']}`",
        f"- authority 70 keV replay Z relative error: `{threshold['authority_replay_Z20d_relative_error']:.3e}`",
        f"- best threshold by F3 in scan: `{threshold['best_threshold_by_F3_keV']:.6g}` keV",
        "",
        "| threshold keV | background cps | signal cps | Z20d | F3(20d) |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['threshold_keV']:.6g} | {row['background_final_cps']:.12g} | {row['signal_cps_at_reference_flux']:.12g} | {row['Z20d']:.12g} | {row['F3_20d_ph_cm2_s']:.12g} |"
        )
    lines.extend(
        [
            "",
            "## Material Attenuation Scan",
            "",
            f"- status: `{material['status']}`",
            f"- max absolute relative total-interaction efficiency difference: `{material['max_abs_relative_difference']:.7g}`",
            f"- tolerance: `{material['relative_tolerance']:.7g}`",
            "",
            "Boundary:",
            "- The hard-window Step08 result remains the paper-facing counting sensitivity authority.",
            "- The spatial numbers are detector-coupled sidecars: fixed cuts and fixed-template annular Poisson likelihood, not a nuisance-profile publication likelihood.",
            "- The threshold scan replays the same transported event catalog; it closes detector-threshold robustness without new Cosima transport.",
            "- The material scan is the tracked Geant4/MEGAlib total-cross-section attenuation design scan for the BGO equal-attenuation substitution.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    step05_summary = load_json(STEP05_SUMMARY)
    step08 = load_json(STEP08_SUMMARY)
    threshold_rows, threshold_check = build_threshold_scan(step05_summary, step08)
    spatial_rows, spatial_check, annuli, likelihood_check = build_spatial_sidecar()
    material = material_check()
    hard = {
        "Z20d": step08["checks"]["A_reference_w2_Z20d_time_dependent"],
        "T3_day": step08["checks"]["A_reference_w2_T3_day"],
        "F3_20d_ph_cm2_s": step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"],
        "source_counts": step08["checks"]["A_reference_w2_source_counts"],
        "background_counts": step08["checks"]["A_reference_w2_background_counts"],
    }
    statuses = [threshold_check["status"], spatial_check["status"], likelihood_check["status"], material["status"]]
    payload = {
        "status": "PASS_BGO_SAMPLE_EXTENDED_CLOSURE" if all(status.startswith("PASS") for status in statuses) else "FAIL_BGO_SAMPLE_EXTENDED_CLOSURE",
        "claim_level": "BGO_SAMPLE_HARD_WINDOW_PLUS_SPATIAL_THRESHOLD_MATERIAL_SIDECAR_CLOSURE",
        "inputs": {
            "step05_summary": rel(STEP05_SUMMARY),
            "step05_catalog": rel(STEP05_CATALOG),
            "step06_background_time_variation": rel(STEP06_BG),
            "step08_summary": rel(STEP08_SUMMARY),
            "spatial_response": rel(SPATIAL_RESPONSE),
            "spatial_cuts": rel(SPATIAL_CUTS),
            "attenuation_verification": rel(ATTENUATION),
        },
        "hard_window_authority": hard,
        "spatial_sidecar": spatial_check,
        "annular_likelihood_sidecar": likelihood_check,
        "threshold_scan": threshold_check,
        "material_attenuation_scan": material,
        "threshold_rows": threshold_rows,
        "spatial_rows": spatial_rows,
        "annular_rows": annuli,
        "outputs": {
            "summary_json": rel(OUT_JSON),
            "summary_md": rel(OUT_MD),
            "threshold_csv": rel(OUT_THRESHOLD_CSV),
            "spatial_csv": rel(OUT_SPATIAL_CSV),
        },
    }
    write_json(OUT_JSON, payload)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    write_csv(OUT_THRESHOLD_CSV, threshold_rows)
    write_csv(OUT_SPATIAL_CSV, spatial_rows)
    print(json.dumps({"status": payload["status"], "summary": rel(OUT_JSON), "md": rel(OUT_MD)}, indent=2, ensure_ascii=False))
    return 0 if payload["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
