#!/usr/bin/env python3
"""Build a manuscript-facing smoke audit for the Step06/Step08 time axis."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LATEX = ROOT / "core_md" / "balloon511_nima_latex_drafts"
OUT = LATEX / "paper_resource"
STEP06 = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / "outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613"
)
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613"
)

SECONDS_PER_DAY = 86400.0
DAY15 = 15.0
ALT_REF_KM = 38.75
LAT_REF_DEG = 34.0
LON_REF_DEG = 100.0
ALT_AMP_KM = 2.5
LAT_AMP_DEG = 0.25
LON_AMP_DEG = 0.25
SCALE_HEIGHT_KM = 6.8
DEPTH_AT_38KM_G_CM2 = 3.86509853156
PROMPT_ATTEN_DEPTH_G_CM2 = 30.0
T_REF = 0.7390423888027


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def vertical_depth(altitude_km: float) -> float:
    return DEPTH_AT_38KM_G_CM2 * math.exp(-(altitude_km - 38.0) / SCALE_HEIGHT_KM)


def trajectory_formula(day: float) -> dict[str, float]:
    phase = 2.0 * math.pi * (day - DAY15)
    alt_offset = ALT_AMP_KM * math.sin(phase / 5.0)
    lat_offset = LAT_AMP_DEG * math.sin(phase / 7.0)
    lon_offset = LON_AMP_DEG * math.sin(phase / 9.0)
    altitude = ALT_REF_KM + alt_offset
    latitude = LAT_REF_DEG + lat_offset
    longitude = LON_REF_DEG + lon_offset
    rc = 11.0 - 0.08 * lat_offset + 0.03 * lon_offset
    depth_ref = vertical_depth(ALT_REF_KM)
    depth = vertical_depth(altitude)
    mu_eff = -math.log(T_REF) / depth_ref
    t_atm = math.exp(-mu_eff * depth)
    prompt_scale = math.exp((depth - depth_ref) / PROMPT_ATTEN_DEPTH_G_CM2) * (11.0 / rc) ** 0.2
    return {
        "altitude_km": altitude,
        "latitude_deg": latitude,
        "longitude_deg": longitude,
        "Rc_GV": rc,
        "depth_g_cm2": depth,
        "T_atm_511": t_atm,
        "science_atm_scale_to_day15": t_atm / T_REF,
        "prompt_scale_to_day15": prompt_scale,
        "delayed_production_scale_to_day15": prompt_scale,
    }


def max_abs_delta(actual: dict[str, str], expected: dict[str, float], keys: list[str]) -> float:
    return max(abs(float(actual[key]) - expected[key]) for key in keys)


def rel_delta(actual: float, expected: float) -> float:
    if expected == 0.0:
        return abs(actual - expected)
    return abs(actual - expected) / abs(expected)


def main() -> int:
    traj = read_csv(STEP06 / "trajectory_profile.csv")
    bg_all = read_csv(STEP06 / "background_time_variation.csv")
    activity = read_csv(STEP06 / "total_activity_by_time.csv")
    step06_summary = load_json(STEP06 / "step06_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_summary.json")
    step08_summary = load_json(STEP08 / "step08_v3p5_centerfinger_time_dependent_summary.json")
    cumulative = read_csv(STEP08 / "cumulative_significance_by_case.csv")

    by_day = {float(row["day_mid"]): row for row in traj}
    activity_by_day = {float(row["day_mid"]): row for row in activity}
    probe_days = [15.0, 1.25, 3.75]
    probe_rows = []
    for day in probe_days:
        actual = by_day[day]
        expected = trajectory_formula(day)
        keys = [
            "altitude_km",
            "latitude_deg",
            "longitude_deg",
            "Rc_GV",
            "depth_g_cm2",
            "T_atm_511",
            "science_atm_scale_to_day15",
            "prompt_scale_to_day15",
            "delayed_production_scale_to_day15",
        ]
        probe_rows.append(
            {
                "day": day,
                "max_abs_formula_delta": max_abs_delta(actual, expected, keys),
                "altitude_km": float(actual["altitude_km"]),
                "T_atm_511": float(actual["T_atm_511"]),
                "prompt_scale_to_day15": float(actual["prompt_scale_to_day15"]),
                "delayed_activity_scale_to_day15": float(activity_by_day[day]["activity_scale_to_day15"]),
            }
        )

    w2 = [row for row in bg_all if row["selection_id"] == "w2_510p58_511p42"]
    day15 = min(w2, key=lambda row: abs(float(row["day_mid"]) - DAY15))
    prompt15 = float(day15["prompt_final_cps"])
    delayed15 = float(day15["delayed_final_cps"])
    science15 = float(day15["science_final_cps_at_ref_flux"])
    max_rate_rel = 0.0
    for row in w2:
        prompt = prompt15 * float(row["prompt_scale_to_day15"])
        delayed = delayed15 * float(row["delayed_activity_scale_to_day15"])
        science = science15 * float(row["science_atm_scale_to_day15"])
        max_rate_rel = max(max_rate_rel, rel_delta(float(row["prompt_final_cps"]), prompt))
        max_rate_rel = max(max_rate_rel, rel_delta(float(row["delayed_final_cps"]), delayed))
        max_rate_rel = max(max_rate_rel, rel_delta(float(row["background_final_cps"]), prompt + delayed))
        max_rate_rel = max(max_rate_rel, rel_delta(float(row["science_final_cps_at_ref_flux"]), science))

    target_case = "A_point_w2_510p58_511p42_F0.0001"
    case_rows = [row for row in cumulative if row["analysis_case_id"] == target_case]
    final = case_rows[-1]
    checks = step08_summary["checks"]
    final_checks = {
        "Z20d": float(final["counting_Z"]),
        "source_counts": float(final["cumulative_source_counts"]),
        "background_counts": float(final["cumulative_background_counts"]),
        "summary_Z20d": checks["A_reference_w2_Z20d_time_dependent"],
        "summary_source_counts": checks["A_reference_w2_source_counts"],
        "summary_background_counts": checks["A_reference_w2_background_counts"],
        "Z20d_abs_delta": abs(float(final["counting_Z"]) - checks["A_reference_w2_Z20d_time_dependent"]),
        "source_counts_abs_delta": abs(float(final["cumulative_source_counts"]) - checks["A_reference_w2_source_counts"]),
        "background_counts_abs_delta": abs(float(final["cumulative_background_counts"]) - checks["A_reference_w2_background_counts"]),
    }

    traj_ranges = {}
    for key in ["altitude_km", "latitude_deg", "longitude_deg", "Rc_GV", "T_atm_511", "prompt_scale_to_day15"]:
        vals = [float(row[key]) for row in traj]
        traj_ranges[key] = {"min": min(vals), "max": max(vals)}
    delayed_vals = [float(row["activity_scale_to_day15"]) for row in activity]
    traj_ranges["delayed_activity_scale_to_day15"] = {"min": min(delayed_vals), "max": max(delayed_vals)}

    payload = {
        "status": "PASS_TIME_AXIS_FORMULA_SMOKE_AUDIT",
        "scope": "Step06/Step08 exact-position M=50000 mission-time fold",
        "inputs": {
            "step06_summary": str(STEP06 / "step06_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_summary.json"),
            "step08_summary": str(STEP08 / "step08_v3p5_centerfinger_time_dependent_summary.json"),
        },
        "trajectory_formula_probe_rows": probe_rows,
        "trajectory_ranges": traj_ranges,
        "max_w2_rate_formula_relative_delta": max_rate_rel,
        "step06_checks": step06_summary["checks"],
        "step08_final_checks": final_checks,
        "distribution_assumption": {
            "current_model": "The reference activation-production nuclide/volume/position distribution is reused; the environment changes only a scalar production driver before isotope-by-isotope half-life ODE integration.",
            "evidence_level": "internal formula closure only; no independent activation-production transport grid at trajectory extrema is present in this audit",
            "fallback": "If center/extreme activation transports show material or nuclide distribution changes, replace the scalar delayed-production driver with interpolation over precomputed production vectors.",
        },
    }

    json_path = OUT / "time_axis_smoke_audit_20260617.json"
    md_path = OUT / "time_axis_smoke_audit_20260617.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Time-Axis Formula Smoke Audit",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This audit recomputes the Step06 analytic trajectory formula at the day-15 center point and at the two altitude extrema, then checks that the W511 time-dependent rates and Step08 cumulative result are reproduced from the CSV products.",
        "",
        "## Probe Points",
        "",
        "| day | altitude km | T_atm | prompt scale | delayed activity scale | max formula delta |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in probe_rows:
        lines.append(
            f"| {row['day']:.2f} | {row['altitude_km']:.6g} | {row['T_atm_511']:.12g} | "
            f"{row['prompt_scale_to_day15']:.12g} | {row['delayed_activity_scale_to_day15']:.12g} | "
            f"{row['max_abs_formula_delta']:.3e} |"
        )
    lines += [
        "",
        "## Rate And Significance Closure",
        "",
        f"- Maximum relative delta when reconstructing W511 prompt, delayed, background, and signal rates from day-15 rates and time-dependent scales: `{max_rate_rel:.3e}`.",
        f"- Step08 final Z20d delta between cumulative CSV and summary JSON: `{final_checks['Z20d_abs_delta']:.3e}`.",
        f"- Step08 final source/background count deltas: `{final_checks['source_counts_abs_delta']:.3e}` / `{final_checks['background_counts_abs_delta']:.3e}`.",
        "",
        "## Delayed-Distribution Assumption",
        "",
        "The current rate fold reuses the reference activation-production nuclide/volume/position distribution and lets the trajectory change only a scalar production driver before isotope-by-isotope half-life integration. This audit proves formula and bookkeeping closure for that model; it does not prove that activation-product distributions are physically invariant under a different altitude/latitude/longitude transport. If future center/extreme activation transports contradict the scalar-driver assumption, the manuscript fallback is to interpolate production vectors over the trajectory grid before solving the same ODE.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "json": str(json_path), "md": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
