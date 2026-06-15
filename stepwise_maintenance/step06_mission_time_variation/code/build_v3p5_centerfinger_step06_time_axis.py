#!/usr/bin/env python3
"""Build the v3p5 center-finger 1/10 Step06 mission time axis.

This is a low-statistics branch product.  It folds the v3p5 Step05 direct
response rates over the same synthetic 20-day mission profile used by the
mainline Step06, and it anchors delayed activity to the v3p5 day-15
ground-state correction ledger.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_v3p5_centerfinger_1of10"
FIG = OUT / "figures"
STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
STEP02 = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / "outputs_v3p5_centerfinger_1of10" / "step02_v3p5_centerfinger_1of10_summary.json"
GROUNDSTATE = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_1of10" / "groundstate_activity_corrections.csv"

SECONDS_PER_DAY = 86400.0
DAY15 = 15.0
MISSION_DAYS = 20.0
STEP_DAY = 0.25
ALT_REF_KM = 38.75
LAT_REF_DEG = 34.0
LON_REF_DEG = 100.0
ALT_AMP_KM = 2.5
LAT_AMP_DEG = 0.25
LON_AMP_DEG = 0.25
SCALE_HEIGHT_KM = 6.8
DEPTH_AT_38KM_G_CM2 = 3.86509853156
PROMPT_ATTEN_DEPTH_G_CM2 = 30.0

STAGE_MAP = {
    "raw": "raw_rate_s-1",
    "active": "active_veto_pass_rate_s-1",
    "final": "side_compton_fov_pass_rate_s-1",
}


def is_bgo_sample_label(label: str) -> bool:
    return label == "bgo_sample_fullstat_v2_exactpos"


def output_prefix(label: str) -> str:
    return "bgo_sample" if is_bgo_sample_label(label) else "v3p5_centerfinger"


def step06_summary_filename(label: str) -> str:
    if is_bgo_sample_label(label):
        return "step06_bgo_sample_fullstat_v2_exactpos_summary.json"
    return f"step06_{output_prefix(label)}_{label}_summary.json"


def configure_paths(label: str) -> None:
    global OUT, FIG, STEP05, STEP02, GROUNDSTATE

    if is_bgo_sample_label(label):
        OUT = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / f"outputs_{label}"
        STEP05 = (
            ROOT
            / "stepwise_maintenance"
            / "step05_veto_time_axis"
            / "outputs_bgo_sample_fullstat_v2_exactpos_l1"
            / "step05_bgo_sample_l1_response_summary.json"
        )
        STEP02 = ROOT / "Bgo_sample" / "step02_fullstat_v2_exactpos_summary.json"
        GROUNDSTATE = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_delay_fix" / "groundstate_activity_corrections.csv"
        FIG = OUT / "figures"
        return

    OUT = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / f"outputs_v3p5_centerfinger_{label}"
    FIG = OUT / "figures"
    if label == "1of10":
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    else:
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    STEP02 = (
        ROOT
        / "stepwise_maintenance"
        / "step02_raw_background_simulation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step02_v3p5_centerfinger_{label}_summary.json"
    )
    GROUNDSTATE = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "groundstate_activity_corrections.csv"


def fixed_source_activity_bq(step02: dict[str, Any]) -> float:
    if "fixed_decay_source" in step02:
        return float(step02["fixed_decay_source"]["total_activity_Bq"])
    return float(step02["fixed_total_activity_Bq"])


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, ndigits: int = 6) -> str:
    if x == 0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def vertical_depth_g_cm2(altitude_km: float) -> float:
    return DEPTH_AT_38KM_G_CM2 * math.exp(-(altitude_km - 38.0) / SCALE_HEIGHT_KM)


def bin_centers() -> list[float]:
    n = int(round(MISSION_DAYS / STEP_DAY))
    return [i * STEP_DAY for i in range(n + 1)]


def bin_widths(days: list[float]) -> list[float]:
    widths: list[float] = []
    for i, day in enumerate(days):
        if i == 0:
            width = 0.5 * (days[1] - day)
        elif i == len(days) - 1:
            width = 0.5 * (day - days[i - 1])
        else:
            width = 0.5 * (days[i + 1] - days[i - 1])
        widths.append(width * SECONDS_PER_DAY)
    return widths


def build_trajectory(t_ref: float) -> tuple[list[dict[str, Any]], dict[str, float]]:
    days = bin_centers()
    widths = bin_widths(days)
    depth_ref = vertical_depth_g_cm2(ALT_REF_KM)
    mu_eff = -math.log(t_ref) / depth_ref
    rows: list[dict[str, Any]] = []
    for idx, (day, dt_s) in enumerate(zip(days, widths)):
        phase = 2.0 * math.pi * (day - DAY15)
        alt_offset = ALT_AMP_KM * math.sin(phase / 5.0)
        lat_offset = LAT_AMP_DEG * math.sin(phase / 7.0)
        lon_offset = LON_AMP_DEG * math.sin(phase / 9.0)
        altitude = ALT_REF_KM + alt_offset
        latitude = LAT_REF_DEG + lat_offset
        longitude = LON_REF_DEG + lon_offset
        depth = vertical_depth_g_cm2(altitude)
        rc = 11.0 - 0.08 * lat_offset + 0.03 * lon_offset
        prompt_scale = math.exp((depth - depth_ref) / PROMPT_ATTEN_DEPTH_G_CM2) * (11.0 / rc) ** 0.2
        t_atm = math.exp(-mu_eff * depth)
        rows.append(
            {
                "time_bin_id": idx,
                "time_mid_s": day * SECONDS_PER_DAY,
                "day_mid": day,
                "dt_s": dt_s,
                "altitude_km": altitude,
                "altitude_offset_km": alt_offset,
                "latitude_deg": latitude,
                "latitude_offset_deg": lat_offset,
                "longitude_deg": longitude,
                "longitude_offset_deg": lon_offset,
                "Rc_GV": rc,
                "depth_g_cm2": depth,
                "T_atm_511": t_atm,
                "science_atm_scale_to_day15": t_atm / t_ref,
                "prompt_scale_to_day15": prompt_scale,
                "delayed_production_scale_to_day15": prompt_scale,
            }
        )
    return rows, {"depth_ref_g_cm2": depth_ref, "mu_eff_cm2_g": mu_eff}


def integrate_activity(trajectory: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    correction_rows = read_csv(GROUNDSTATE)
    days = [float(row["day_mid"]) for row in trajectory]
    day15_index = min(range(len(days)), key=lambda i: abs(days[i] - DAY15))
    per_key: list[dict[str, Any]] = []
    totals: dict[int, float] = defaultdict(float)
    reference_total = 0.0
    skipped = 0
    for row in correction_rows:
        activity_ref = float(row["new_groundstate_activity_Bq"])
        hl_s = float(row["nubase_half_life_s"])
        if activity_ref <= 0.0 or hl_s <= 0.0 or not math.isfinite(hl_s):
            skipped += 1
            continue
        reference_total += activity_ref
        lam = math.log(2.0) / hl_s
        build_factor = 1.0 - math.exp(-lam * DAY15 * SECONDS_PER_DAY)
        production_ref = activity_ref / max(build_factor, 1.0e-300)
        inventory_n = 0.0
        raw_activities: list[float] = []
        for trow in trajectory:
            dt_s = float(trow["dt_s"])
            driver = float(trow["delayed_production_scale_to_day15"])
            production = production_ref * driver
            half = 0.5 * dt_s
            mid_n = inventory_n * math.exp(-lam * half) + (production / lam) * (1.0 - math.exp(-lam * half))
            raw_activities.append(lam * mid_n)
            inventory_n = inventory_n * math.exp(-lam * dt_s) + (production / lam) * (1.0 - math.exp(-lam * dt_s))
        anchor = raw_activities[day15_index]
        anchor_scale = activity_ref / anchor if anchor > 0 else 1.0
        for trow, raw_activity in zip(trajectory, raw_activities):
            activity = raw_activity * anchor_scale
            idx = int(trow["time_bin_id"])
            totals[idx] += activity
            per_key.append(
                {
                    "time_bin_id": idx,
                    "day_mid": trow["day_mid"],
                    "VN": row["VN"],
                    "ZA": row["ZA"],
                    "nuclide": row["nuclide"],
                    "hl_s": hl_s,
                    "reference_activity_Bq_day15": activity_ref,
                    "activity_Bq": activity,
                    "activity_ratio_to_day15": activity / activity_ref if activity_ref > 0 else "",
                }
            )
    total_rows: list[dict[str, Any]] = []
    for trow in trajectory:
        idx = int(trow["time_bin_id"])
        total = totals[idx]
        total_rows.append(
            {
                "time_bin_id": idx,
                "day_mid": trow["day_mid"],
                "total_activity_Bq": total,
                "activity_scale_to_day15": total / reference_total if reference_total > 0 else 1.0,
            }
        )
    audit = {
        "groundstate_corrections": rel(GROUNDSTATE),
        "rows_used": len(correction_rows) - skipped,
        "rows_skipped": skipped,
        "reference_total_activity_Bq": reference_total,
        "day15_index": day15_index,
        "day15_mid": days[day15_index],
        "activity_scale_min": min(float(row["activity_scale_to_day15"]) for row in total_rows),
        "activity_scale_max": max(float(row["activity_scale_to_day15"]) for row in total_rows),
    }
    return per_key, total_rows, audit


def stage_rates(step05: dict[str, Any], selection: str) -> dict[str, dict[str, float]]:
    window = step05["windows"][selection]
    out: dict[str, dict[str, float]] = {}
    for stream in ("prompt", "delayed", "science"):
        row = window["by_stream"][stream]
        out[stream] = {stage: float(row[column]) for stage, column in STAGE_MAP.items()}
    phys = window["physical_reference_flux"]
    out["science_physical"] = {
        "raw": out["science"]["raw"] * phys["rate_to_v3p5_injection_plane_s-1"],
        "active": out["science"]["active"] * phys["rate_to_v3p5_injection_plane_s-1"],
        "final": phys["signal_cps_at_reference_flux"],
    }
    return out


def build_background_time_variation(
    step05: dict[str, Any],
    trajectory: list[dict[str, Any]],
    totals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    activity_scale = {int(row["time_bin_id"]): float(row["activity_scale_to_day15"]) for row in totals}
    draw = step05["timeline_draw_summary"]
    prompt_event_rate = float(draw["prompt"]["rate_hz"])
    delayed_event_rate = float(draw["delayed"]["rate_hz"])
    label = str(step05.get("statistics_label", "1of10")).upper()
    rows: list[dict[str, Any]] = []
    for selection in step05["windows"]:
        rates = stage_rates(step05, selection)
        for trow in trajectory:
            idx = int(trow["time_bin_id"])
            prompt_scale = float(trow["prompt_scale_to_day15"])
            delayed_scale = activity_scale[idx]
            science_scale = float(trow["science_atm_scale_to_day15"])
            out: dict[str, Any] = {
                "selection_id": selection,
                "time_bin_id": idx,
                "time_mid_s": trow["time_mid_s"],
                "day_mid": trow["day_mid"],
                "dt_s": trow["dt_s"],
                "prompt_scale_to_day15": prompt_scale,
                "delayed_activity_scale_to_day15": delayed_scale,
                "science_atm_scale_to_day15": science_scale,
                "T_atm_511": trow["T_atm_511"],
                "prompt_event_rate_hz": prompt_event_rate * prompt_scale,
                "delayed_event_rate_hz": delayed_event_rate * delayed_scale,
            }
            for stage in ("raw", "active", "final"):
                prompt = rates["prompt"][stage] * prompt_scale
                delayed = rates["delayed"][stage] * delayed_scale
                science = rates["science_physical"][stage] * science_scale
                out[f"prompt_{stage}_cps"] = prompt
                out[f"delayed_{stage}_cps"] = delayed
                out[f"background_{stage}_cps"] = prompt + delayed
                out[f"science_{stage}_cps_at_ref_flux"] = science
            out["claim_level"] = f"V3P5_L1_RATE_FOLD_{label}_NO_NEW_TRANSPORT"
            rows.append(out)
    return rows


def plot_outputs(trajectory: list[dict[str, Any]], background: list[dict[str, Any]], totals: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    days = [float(row["day_mid"]) for row in trajectory]
    plt.figure(figsize=(8, 4.5))
    plt.plot(days, [float(row["altitude_km"]) for row in trajectory], label="altitude")
    plt.xlabel("Mission day")
    plt.ylabel("Altitude (km)")
    plt.title("v3p5 Step06 reference trajectory")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIG / "v3p5_step06_trajectory.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.plot(days, [float(row["T_atm_511"]) for row in trajectory], label="T_atm")
    plt.xlabel("Mission day")
    plt.ylabel("511 keV transmission")
    plt.title("v3p5 Step06 atmospheric transmission")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIG / "v3p5_step06_t_atm.png", dpi=180)
    plt.close()

    w2 = [row for row in background if row["selection_id"] == "w2_510p58_511p42"]
    plt.figure(figsize=(8, 4.5))
    plt.plot([float(row["day_mid"]) for row in w2], [float(row["background_final_cps"]) for row in w2], label="W2 background")
    plt.plot([float(row["day_mid"]) for row in w2], [float(row["science_final_cps_at_ref_flux"]) for row in w2], label="W2 science @ ref flux")
    plt.xlabel("Mission day")
    plt.ylabel("Rate (cps)")
    plt.title("v3p5 Step06 W2 time-dependent rates")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIG / "v3p5_step06_w2_rates.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.plot([float(row["day_mid"]) for row in totals], [float(row["activity_scale_to_day15"]) for row in totals])
    plt.xlabel("Mission day")
    plt.ylabel("Total delayed activity / day15")
    plt.title("v3p5 Step06 delayed activity scale")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIG / "v3p5_step06_activity_scale.png", dpi=180)
    plt.close()


def markdown(summary: dict[str, Any]) -> str:
    c = summary["checks"]
    title = "# Step06 Bgo_sample Mission Time Variation" if is_bgo_sample_label(summary["statistics_label"]) else "# Step06 v3p5 Center-Finger Mission Time Variation"
    intro = (
        f"This is the Bgo_sample `{summary['statistics_label']}` mission-axis fold. It does not run new Cosima transport; it reweights the BGO Step05 direct response rates over a synthetic 20-day trajectory."
        if is_bgo_sample_label(summary["statistics_label"])
        else f"This is the v3p5 `{summary['statistics_label']}` mission-axis fold. It does not run new Cosima transport; it reweights the v3p5 Step05 direct response rates over a synthetic 20-day trajectory."
    )
    return "\n".join(
        [
            title,
            "",
            f"Status: `{summary['status']}`.",
            "",
            f"Claim level: {summary['claim_level']}.",
            "",
            intro,
            "The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.",
            "",
            "Key checks:",
            f"- T_atm day-15 closure: `{c['T_day15']:.12g}` vs reference `{c['T_ref']:.12g}`.",
            f"- W2 day-15 background/signal: `{c['w2_day15_background_final_cps']:.6g}` / `{c['w2_day15_science_final_cps_at_ref_flux']:.6g}` cps.",
            f"- W2 mission-mean background/signal: `{c['w2_dt_weighted_background_final_cps']:.6g}` / `{c['w2_dt_weighted_science_final_cps_at_ref_flux']:.6g}` cps.",
            f"- delayed activity scale range: `{c['activity_scale_min']:.6g}` to `{c['activity_scale_max']:.6g}`.",
            "",
            "Outputs:",
            f"- summary JSON: `{summary['outputs']['summary_json']}`",
            f"- background time variation: `{summary['outputs']['background_time_variation']}`",
            f"- total activity by time: `{summary['outputs']['total_activity_by_time']}`",
            f"- figures: `{summary['outputs']['figures']}`",
            "",
            "Limitations:",
            *[f"- {item}" for item in summary.get("pending", [])],
            "- this is a rate-level fold, not per-bin detector transport.",
            "",
        ]
    )


def build_summary(
    step05: dict[str, Any],
    step02: dict[str, Any],
    trajectory: list[dict[str, Any]],
    totals: list[dict[str, Any]],
    background: list[dict[str, Any]],
    activity_audit: dict[str, Any],
    atmosphere_model: dict[str, float],
) -> dict[str, Any]:
    label = step05.get("statistics_label", "1of10")
    prefix = output_prefix(label)
    t_ref = float(step05["science_physical_normalization"]["atmospheric_transmission"]["T_atm"])
    day15 = min(trajectory, key=lambda row: abs(float(row["day_mid"]) - DAY15))
    w2_rows = [row for row in background if row["selection_id"] == "w2_510p58_511p42"]
    w2_day15 = min(w2_rows, key=lambda row: abs(float(row["day_mid"]) - DAY15))
    total_dt = sum(float(row["dt_s"]) for row in w2_rows)
    mean_b = sum(float(row["background_final_cps"]) * float(row["dt_s"]) for row in w2_rows) / total_dt
    mean_s = sum(float(row["science_final_cps_at_ref_flux"]) * float(row["dt_s"]) for row in w2_rows) / total_dt
    if is_bgo_sample_label(label):
        status = "PASS_BGO_SAMPLE_STEP06_TIME_AXIS_FULLSTAT_V2_EXACTPOS"
        claim_level = "BGO_SAMPLE_L1_MISSION_RATE_FOLD_FULLSTAT_V2_EXACTPOS_NO_NEW_TRANSPORT"
        pending = [
            "Downstream Step07, Step08, and the BGO-vs-CsI hard-window comparison are closed for this label.",
            "Optional: run BGO spatial/profile-likelihood sidecars before claiming spatial-analysis gains.",
            "Optional: add BGO material-uncertainty or detector-threshold sensitivity scans before claiming robustness against those choices.",
        ]
    else:
        status = f"PASS_V3P5_STEP06_TIME_AXIS_{label.upper()}"
        claim_level = f"V3P5_L1_MISSION_RATE_FOLD_{label.upper()}_NO_NEW_TRANSPORT"
        pending = [
            "Replace delayed-source RadialProfileBeam compression with exact-position sampling.",
            "Promote this branch fold only after full Step06-Step08 review.",
        ]
    summary = {
        "status": status,
        "statistics_label": label,
        "claim_level": claim_level,
        "inputs": {
            "step05_summary": rel(STEP05),
            "step02_summary": rel(STEP02),
            "groundstate_activity_corrections": rel(GROUNDSTATE),
        },
        "normalization": {
            "reference_flux_ph_cm2_s": step05["science_physical_normalization"]["reference_flux_ph_cm2_s"],
            "T_ref": t_ref,
            "reference_injection_rate_s-1": step05["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"],
            "coincidence_window_s": step05["normalization"]["coincidence_window_s"],
        },
        "trajectory": {
            "mission_days": MISSION_DAYS,
            "step_day": STEP_DAY,
            "bins": len(trajectory),
            "altitude_ref_km": ALT_REF_KM,
            "altitude_range_km": [min(float(r["altitude_km"]) for r in trajectory), max(float(r["altitude_km"]) for r in trajectory)],
        },
        "activity": activity_audit,
        "atmosphere_model": atmosphere_model,
        "checks": {
            "T_ref": t_ref,
            "T_day15": float(day15["T_atm_511"]),
            "T_day15_abs_error": abs(float(day15["T_atm_511"]) - t_ref),
            "activity_scale_min": activity_audit["activity_scale_min"],
            "activity_scale_max": activity_audit["activity_scale_max"],
            "w2_day15_background_final_cps": float(w2_day15["background_final_cps"]),
            "w2_day15_science_final_cps_at_ref_flux": float(w2_day15["science_final_cps_at_ref_flux"]),
            "w2_dt_weighted_background_final_cps": mean_b,
            "w2_dt_weighted_science_final_cps_at_ref_flux": mean_s,
            "step02_fixed_source_activity_Bq": fixed_source_activity_bq(step02),
        },
        "outputs": {
            "summary_json": rel(OUT / step06_summary_filename(label)),
            "readme": rel(OUT / "README.md"),
            "trajectory_profile": rel(OUT / "trajectory_profile.csv"),
            "atmosphere_transmission": rel(OUT / "atmosphere_transmission_511_by_time.csv"),
            "activity_by_time_nuclide_volume": rel(OUT / "activity_by_time_nuclide_volume.csv"),
            "total_activity_by_time": rel(OUT / "total_activity_by_time.csv"),
            "background_time_variation": rel(OUT / "background_time_variation.csv"),
            "figures": rel(FIG),
        },
        "pending": pending,
    }
    return summary


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="1of10", help="Run/output label, e.g. 1of10 or fullstat_v2")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    step05 = load_json(STEP05)
    step02 = load_json(STEP02)
    t_ref = float(step05["science_physical_normalization"]["atmospheric_transmission"]["T_atm"])
    trajectory, atmosphere_model = build_trajectory(t_ref)
    activity_rows, total_rows, activity_audit = integrate_activity(trajectory)
    background_rows = build_background_time_variation(step05, trajectory, total_rows)
    write_csv(OUT / "trajectory_profile.csv", trajectory)
    write_csv(
        OUT / "atmosphere_transmission_511_by_time.csv",
        [
            {
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "altitude_km": row["altitude_km"],
                "depth_g_cm2": row["depth_g_cm2"],
                "T_atm_511": row["T_atm_511"],
                "science_atm_scale_to_day15": row["science_atm_scale_to_day15"],
            }
            for row in trajectory
        ],
    )
    write_csv(OUT / "activity_by_time_nuclide_volume.csv", activity_rows)
    write_csv(OUT / "total_activity_by_time.csv", total_rows)
    write_csv(OUT / "background_time_variation.csv", background_rows)
    plot_outputs(trajectory, background_rows, total_rows)
    summary = build_summary(step05, step02, trajectory, total_rows, background_rows, activity_audit, atmosphere_model)
    write_json(OUT / step06_summary_filename(args.label), summary)
    (OUT / "README.md").write_text(markdown(summary), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary": summary["outputs"]["summary_json"], "readme": summary["outputs"]["readme"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
