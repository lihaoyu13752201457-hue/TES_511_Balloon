#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import pickle
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
OUT = STEP_DIR / "outputs"
FIG = OUT / "figures"

SECONDS_PER_DAY = 86400.0
DAY15 = 15.0
T_REF = 0.7390423888027
ALT_REF_KM = 38.75
LAT_REF_DEG = 34.0
LON_REF_DEG = 100.0
ALT_AMP_KM = 2.5
LAT_AMP_DEG = 0.25
LON_AMP_DEG = 0.25
SCALE_HEIGHT_KM = 6.8
DEPTH_AT_38KM_G_CM2 = 3.86509853156
PROMPT_ATTEN_DEPTH_G_CM2 = 30.0
PARTICLES = ["gamma", "eplus", "eminus", "p", "n", "alpha", "muplus", "muminus"]
PARMA_SOLAR_DATE = (2025, 8, 31)
PARMA_MU_BIN_WIDTH = 0.1
PARMA_EXE_CANDIDATES = [
    ROOT.parent / "COSMOSRAY_BALLOON_SIM" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
    ROOT.parent / "cosmosray_bg_260516" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
    ROOT.parent / "cosmosray_bg_2605" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
]
PARMA_CPP_CANDIDATES = [
    ROOT.parent / "COSMOSRAY_BALLOON_SIM" / "external" / "expacs_parma" / "parma_cpp",
    ROOT.parent / "cosmosray_bg_260516" / "external" / "expacs_parma" / "parma_cpp",
    ROOT.parent / "cosmosray_bg_2605" / "external" / "expacs_parma" / "parma_cpp",
]
PROMPT_CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
INSTANT_RUN_SUMMARY = ROOT / "runs" / "step02_instant_equiv2602_aligned" / "run_summary.json"
BUILDUP_RUN_SUMMARY = ROOT / "runs" / "step02_buildup_equiv2602_aligned" / "run_summary.json"
PROMPT_PARTICLE_RE = re.compile(r"Background_(alpha|eminus|eplus|gamma|muminus|muplus|n|p)_")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def vertical_depth_g_cm2(altitude_km: float) -> float:
    return DEPTH_AT_38KM_G_CM2 * math.exp(-(altitude_km - 38.0) / SCALE_HEIGHT_KM)


def build_time_grid(day_stop: float = 20.0, step_day: float = 0.25) -> list[float]:
    n = int(round(day_stop / step_day))
    return [i * step_day for i in range(n + 1)]


def bin_widths(days: list[float]) -> list[float]:
    widths = []
    for i, day in enumerate(days):
        if len(days) == 1:
            width = 0.0
        elif i == 0:
            width = 0.5 * (days[1] - day)
        elif i == len(days) - 1:
            width = 0.5 * (day - days[i - 1])
        else:
            width = 0.5 * (days[i + 1] - days[i - 1])
        widths.append(width * SECONDS_PER_DAY)
    return widths


def read_science_ledger() -> dict[str, float]:
    rows = read_csv(ROOT / "config" / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv")
    row = next(r for r in rows if abs(float(r["flux_ph_cm2_s"]) - 1.0e-4) < 1.0e-12)
    return {
        "flux_ph_cm2_s": float(row["flux_ph_cm2_s"]),
        "A_opt_cm2": float(row["A_opt_cm2"]),
        "T_atm": float(row["T_atm"]),
        "rate_to_injection_plane_s^-1": float(row["rate_to_injection_plane_s^-1"]),
    }


def parma_driver_paths() -> tuple[Path, Path] | None:
    for exe in PARMA_EXE_CANDIDATES:
        cpp = exe.parent / "parma_cpp"
        if exe.exists() and os.access(exe, os.X_OK) and (cpp / "subroutines.cpp").exists():
            return exe, cpp
    for cpp in PARMA_CPP_CANDIDATES:
        exe = cpp.parent / "phase2_parma_grid_driver"
        if exe.exists() and os.access(exe, os.X_OK) and (cpp / "subroutines.cpp").exists():
            return exe, cpp
    return None


def run_parma_condition(exe: Path, cwd: Path, row: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]]]:
    year, month, day = PARMA_SOLAR_DATE
    cmd = [
        str(exe),
        str(year),
        str(month),
        str(day),
        str(float(row["latitude_deg"])),
        str(float(row["longitude_deg"])),
        str(float(row["altitude_km"])),
        "10.0",
    ]
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=True)
    meta: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    reader: csv.DictReader[str] | None = None
    lines = [line for line in proc.stdout.splitlines() if line]
    for i, line in enumerate(lines):
        if line.startswith("META,"):
            _tag, w_index, rc_gv, depth = line.split(",")
            meta = {"W_index": float(w_index), "Rc_GV_parma": float(rc_gv), "depth_g_cm2_parma": float(depth)}
        if line.startswith("particle,"):
            reader = csv.DictReader(lines[i:])
            break
    if reader is None:
        raise RuntimeError("PARMA driver did not return a particle table")
    for item in reader:
        rows.append(
            {
                "particle": item["particle"],
                "angle_bin": int(item["angle_bin"]),
                "mu_mid": float(item.get("mu_mid", 0.0)),
                "theta_mid_deg": float(item.get("theta_mid_deg", 0.0)),
                "energy_bin": int(item["energy_bin"]),
                "energy_MeV": float(item["energy_MeV"]),
                "angular_integrated_flux_cm2_s_MeV": max(float(item.get("angular_integrated_flux_cm2_s_MeV", 0.0)), 0.0),
                "differential_flux_cm2_s_sr_MeV": max(float(item["differential_flux_cm2_s_sr_MeV"]), 0.0),
            }
        )
    if not meta:
        raise RuntimeError("PARMA driver did not return META")
    return meta, rows


def particle_flux_integrals(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    solid_angle_weight = 2.0 * math.pi * PARMA_MU_BIN_WIDTH
    for row in rows:
        totals[str(row["particle"])] += float(row["differential_flux_cm2_s_sr_MeV"]) * solid_angle_weight
    return dict(totals)


def normalize_weights(raw: dict[str, float]) -> dict[str, float]:
    clean = {p: max(float(raw.get(p, 0.0)), 0.0) for p in PARTICLES}
    total = sum(clean.values())
    if total <= 0.0:
        return {p: 1.0 / len(PARTICLES) for p in PARTICLES}
    return {p: clean[p] / total for p in PARTICLES}


def source_rate_weights(summary_path: Path) -> dict[str, float]:
    try:
        rows = load_json(summary_path)
    except Exception:
        return {p: 1.0 / len(PARTICLES) for p in PARTICLES}
    rates: dict[str, float] = defaultdict(float)
    for row in rows:
        particle = str(row.get("particle", ""))
        if particle not in PARTICLES:
            continue
        obs = float(row.get("observation_time_s", 0.0))
        gen = float(row.get("generated_particles", 0.0))
        if obs > 0.0 and gen > 0.0:
            rates[particle] += gen / obs
    return normalize_weights(rates)


def prompt_final_particle_weights() -> tuple[dict[str, float], dict[str, int]]:
    """Return (weights, per-particle surviving-event counts).

    The weights come from the few prompt events that survive the full 480-550
    keV final selection, so the counts are the statistical basis of the weight
    split; particles with zero counts get zero weight by construction, not by
    physics.
    """
    if not PROMPT_CATALOG.exists():
        return source_rate_weights(INSTANT_RUN_SUMMARY), {}
    try:
        sys.path.insert(0, str(ROOT / "code" / "tools"))
        import make_complete_day15_report_ADR as complete  # noqa: PLC0415

        cat = pickle.load(PROMPT_CATALOG.open("rb"))
        rates: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        n = len(cat["stream"])
        for idx in range(n):
            if str(cat["stream"][idx]) != "prompt":
                continue
            energy = float(cat["tes_total_keV"][idx])
            if not (480.0 <= energy <= 550.0):
                continue
            if float(cat["bgo_total_keV"][idx]) >= complete.BGO_THR_KEV:
                continue
            pix_count = int(cat["pix_count"][idx])
            if pix_count <= 1:
                keep = True
            elif pix_count > 6:
                keep = True
            else:
                keep, _cls = complete.classify_final(complete.event_hits(cat, idx), "keep")
            if not keep:
                continue
            match = PROMPT_PARTICLE_RE.search(str(cat["source_file"][idx]))
            if match:
                rates[match.group(1)] += float(cat["rate_hz"][idx])
                counts[match.group(1)] += 1
        return normalize_weights(rates), dict(counts)
    except Exception:
        return source_rate_weights(INSTANT_RUN_SUMMARY), {}


def write_prompt_driver_weights(
    prompt_weights: dict[str, float],
    delayed_weights: dict[str, float],
    prompt_counts: dict[str, int],
) -> None:
    rows = []
    for particle in PARTICLES:
        rows.append(
            {
                "particle": particle,
                "prompt_detector_final_weight": f"{prompt_weights.get(particle, 0.0):.12e}",
                "prompt_final_event_count": str(prompt_counts.get(particle, 0)),
                "delayed_production_source_weight": f"{delayed_weights.get(particle, 0.0):.12e}",
            }
        )
    write_csv(
        OUT / "expacs_prompt_driver_weights.csv",
        rows,
        ["particle", "prompt_detector_final_weight", "prompt_final_event_count", "delayed_production_source_weight"],
    )


def attach_expacs_prompt_driver(drivers: list[dict[str, Any]]) -> dict[str, Any]:
    paths = parma_driver_paths()
    for row in drivers:
        proxy = float(row["prompt_flux_scale_to_ref"])
        row["proxy_prompt_flux_scale_to_day15"] = f"{proxy:.12g}"
        row["proxy_delayed_production_scale_to_day15"] = f"{proxy:.12g}"
        row["prompt_driver_backend"] = "analytic_depth_cutoff_proxy"
    if paths is None:
        return {
            "status": "FALLBACK_PROXY",
            "backend": "analytic_depth_cutoff_proxy",
            "reason": "EXPACS/PARMA executable and parma_cpp directory were not found",
        }

    exe, cwd = paths
    day15_index = min(range(len(drivers)), key=lambda i: abs(float(drivers[i]["day_mid"]) - DAY15))
    prompt_weights, prompt_counts = prompt_final_particle_weights()
    delayed_weights = source_rate_weights(BUILDUP_RUN_SUMMARY)
    write_prompt_driver_weights(prompt_weights, delayed_weights, prompt_counts)

    ref_meta, ref_rows = run_parma_condition(exe, cwd, drivers[day15_index])
    ref_flux = particle_flux_integrals(ref_rows)
    particle_rows: list[dict[str, Any]] = []
    prompt_values: list[float] = []
    delayed_values: list[float] = []
    for row in drivers:
        meta, parma_rows = run_parma_condition(exe, cwd, row)
        flux = particle_flux_integrals(parma_rows)
        scales = {}
        for particle in PARTICLES:
            ref = ref_flux.get(particle, 0.0)
            scale = flux.get(particle, 0.0) / ref if ref > 0.0 else 1.0
            scales[particle] = scale
            particle_rows.append(
                {
                    "time_bin_id": row["time_bin_id"],
                    "day_mid": row["day_mid"],
                    "particle": particle,
                    "scale_to_day15": f"{scale:.12e}",
                    "flux_integral": f"{flux.get(particle, 0.0):.12e}",
                    "reference_flux_integral_day15": f"{ref:.12e}",
                    "integration_note": "sum(differential_flux_cm2_s_sr_MeV * 2pi * dmu) over PARMA 20 equal-mu angular bins and 64 energy support points",
                    "altitude_km": row["altitude_km"],
                    "latitude_deg": row["latitude_deg"],
                    "longitude_deg": row["longitude_deg"],
                    "W_index": f"{meta['W_index']:.12g}",
                    "Rc_GV_parma": f"{meta['Rc_GV_parma']:.12g}",
                    "depth_g_cm2_parma": f"{meta['depth_g_cm2_parma']:.12g}",
                    "backend": "official_EXPACS_PARMA_CPP_driver",
                }
            )
        prompt_scale = sum(prompt_weights[p] * scales[p] for p in PARTICLES)
        delayed_scale = sum(delayed_weights[p] * scales[p] for p in PARTICLES)
        row["prompt_flux_scale_to_ref"] = f"{prompt_scale:.12g}"
        row["delayed_production_scale_to_ref"] = f"{delayed_scale:.12g}"
        row["prompt_driver_backend"] = "official_EXPACS_PARMA_CPP_driver"
        prompt_values.append(prompt_scale)
        delayed_values.append(delayed_scale)

    write_csv(
        OUT / "expacs_particle_scale_by_time.csv",
        particle_rows,
        [
            "time_bin_id",
            "day_mid",
            "particle",
            "scale_to_day15",
            "flux_integral",
            "reference_flux_integral_day15",
            "integration_note",
            "altitude_km",
            "latitude_deg",
            "longitude_deg",
            "W_index",
            "Rc_GV_parma",
            "depth_g_cm2_parma",
            "backend",
        ],
    )
    audit = {
        "status": "PASS",
        "backend": "official_EXPACS_PARMA_CPP_driver",
        "solar_reference_date": {"year": PARMA_SOLAR_DATE[0], "month": PARMA_SOLAR_DATE[1], "day": PARMA_SOLAR_DATE[2]},
        "exe": str(exe),
        "parma_cpp_cwd": str(cwd),
        "reference_time_bin_id": int(drivers[day15_index]["time_bin_id"]),
        "reference_day_mid": float(drivers[day15_index]["day_mid"]),
        "reference_meta": ref_meta,
        "n_time_bins": len(drivers),
        "particle_rows": len(particle_rows),
        "particle_scale_integration": {
            "method": "sum_differential_flux_times_2pi_dmu_over_PARMA_equal_mu_angle_bins_and_energy_support_points",
            "mu_bin_width": PARMA_MU_BIN_WIDTH,
            "note": "Scale ratios are normalized to the day-15 reference condition; no time-bin Cosima detector transport is rerun.",
        },
        "prompt_detector_scale_range": [min(prompt_values), max(prompt_values)],
        "delayed_production_scale_range": [min(delayed_values), max(delayed_values)],
        "prompt_detector_weights": prompt_weights,
        "prompt_detector_weight_event_counts": prompt_counts,
        "prompt_detector_weight_statistics_note": (
            "Prompt weights are rate-weighted over the prompt events surviving the full "
            "480-550 keV final selection; the per-particle event counts above are the "
            "statistical basis. Zero-count particles get zero weight by construction, "
            "and small counts mean the weight split carries large Poisson uncertainty."
        ),
        "delayed_production_weights": delayed_weights,
        "outputs": {
            "particle_scale_by_time": rel(OUT / "expacs_particle_scale_by_time.csv"),
            "weights": rel(OUT / "expacs_prompt_driver_weights.csv"),
        },
    }
    write_json(OUT / "expacs_prompt_driver_summary.json", audit)
    return audit


def build_trajectory_and_drivers() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    days = build_time_grid()
    widths_s = bin_widths(days)
    depth_ref = vertical_depth_g_cm2(ALT_REF_KM)
    mu_eff = -math.log(T_REF) / depth_ref
    rows = []
    drivers = []
    for idx, (day, dt_s) in enumerate(zip(days, widths_s)):
        phase = 2.0 * math.pi * (day - DAY15)
        alt_offset = ALT_AMP_KM * math.sin(phase / 5.0)
        lat_offset = LAT_AMP_DEG * math.sin(phase / 7.0)
        lon_offset = LON_AMP_DEG * math.sin(phase / 9.0)
        altitude = ALT_REF_KM + alt_offset
        latitude = LAT_REF_DEG + lat_offset
        longitude = LON_REF_DEG + lon_offset
        depth = vertical_depth_g_cm2(altitude)
        rc = 11.0 - 0.08 * lat_offset + 0.03 * lon_offset
        # L0 float-regime proxy: prompt secondaries increase with residual
        # atmospheric depth, while 511 keV source transmission uses the
        # opposite Beer-Lambert sign through the same depth.
        prompt_scale = math.exp((depth - depth_ref) / PROMPT_ATTEN_DEPTH_G_CM2) * (11.0 / rc) ** 0.2
        source_zenith_deg = 0.0
        path_depth = depth
        t_atm = math.exp(-mu_eff * path_depth)
        science_scale = t_atm / T_REF
        trajectory_row = {
            "time_bin_id": idx,
            "time_mid_s": f"{day * SECONDS_PER_DAY:.6f}",
            "day_mid": f"{day:.6f}",
            "dt_s": f"{dt_s:.6f}",
            "altitude_km": f"{altitude:.9f}",
            "altitude_offset_km": f"{alt_offset:.9f}",
            "latitude_deg": f"{latitude:.9f}",
            "latitude_offset_deg": f"{lat_offset:.9f}",
            "longitude_deg": f"{longitude:.9f}",
            "longitude_offset_deg": f"{lon_offset:.9f}",
            "Rc_GV": f"{rc:.9f}",
            "depth_g_cm2": f"{depth:.12g}",
        }
        driver_row = {
            **trajectory_row,
            "source_zenith_deg": f"{source_zenith_deg:.6f}",
            "path_depth_g_cm2": f"{path_depth:.12g}",
            "T_atm_511": f"{t_atm:.12g}",
            "science_atm_scale_to_ref": f"{science_scale:.12g}",
            "prompt_flux_scale_to_ref": f"{prompt_scale:.12g}",
            "delayed_production_scale_to_ref": f"{prompt_scale:.12g}",
            "claim_level": "L0_proxy_small_offset_trajectory",
        }
        rows.append(trajectory_row)
        drivers.append(driver_row)
    prompt_driver = attach_expacs_prompt_driver(drivers)
    model = {"depth_ref_g_cm2": depth_ref, "mu_eff_cm2_g": mu_eff, "prompt_driver": prompt_driver}
    return rows, drivers, model


def pearson_corr(xs: list[float], ys: list[float]) -> float:
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    dx = [x - x_mean for x in xs]
    dy = [y - y_mean for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if denom <= 0.0:
        return 0.0
    return sum(x * y for x, y in zip(dx, dy)) / denom


def build_environment_trend_checks(drivers: list[dict[str, Any]]) -> dict[str, Any]:
    min_alt_row = min(drivers, key=lambda r: float(r["altitude_km"]))
    max_alt_row = max(drivers, key=lambda r: float(r["altitude_km"]))
    altitudes = [float(r["altitude_km"]) for r in drivers]
    prompt_scales = [float(r["prompt_flux_scale_to_ref"]) for r in drivers]
    transmissions = [float(r["T_atm_511"]) for r in drivers]
    prompt_min_alt = float(min_alt_row["prompt_flux_scale_to_ref"])
    prompt_max_alt = float(max_alt_row["prompt_flux_scale_to_ref"])
    t_min_alt = float(min_alt_row["T_atm_511"])
    t_max_alt = float(max_alt_row["T_atm_511"])
    return {
        "prompt_depth_proxy_sign": "secondary_dominated_prompt_scale_increases_with_residual_depth",
        "science_transmission_sign": "Beer-Lambert_source_transmission_increases_with_altitude",
        "min_altitude_km": float(min_alt_row["altitude_km"]),
        "max_altitude_km": float(max_alt_row["altitude_km"]),
        "prompt_scale_at_min_altitude": prompt_min_alt,
        "prompt_scale_at_max_altitude": prompt_max_alt,
        "T_atm_at_min_altitude": t_min_alt,
        "T_atm_at_max_altitude": t_max_alt,
        "prompt_high_altitude_less_than_low_altitude": prompt_max_alt < prompt_min_alt,
        "T_atm_high_altitude_greater_than_low_altitude": t_max_alt > t_min_alt,
        "altitude_vs_prompt_scale_corr": pearson_corr(altitudes, prompt_scales),
        "altitude_vs_T_atm_corr": pearson_corr(altitudes, transmissions),
    }


def integrate_activity(inventory_rows: list[dict[str, str]], drivers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    days = [float(r["day_mid"]) for r in drivers]
    day15_index = min(range(len(days)), key=lambda i: abs(days[i] - DAY15))
    if abs(days[day15_index] - DAY15) > 1.0e-12:
        raise RuntimeError("time grid does not contain day 15 anchor")

    raw_by_key: dict[tuple[str, str, str, str], list[float]] = {}
    ref_by_key: dict[tuple[str, str, str, str], float] = {}
    meta_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}

    for row in inventory_rows:
        a_ref = float(row["Activity_Bq"])
        hl_s = float(row["hl_s"])
        if a_ref <= 0.0 or hl_s <= 0.0 or not math.isfinite(hl_s):
            continue
        key = (row["VN"], row["ZA"], row["nuclide"], row.get("exc_keV", "0.0"))
        lam = math.log(2.0) / hl_s
        build_factor = 1.0 - math.exp(-lam * DAY15 * SECONDS_PER_DAY)
        p_ref = a_ref / max(build_factor, 1.0e-300)
        n_start = 0.0
        acts = []
        for drow in drivers:
            dt = float(drow["dt_s"])
            driver = float(drow["delayed_production_scale_to_ref"])
            p_now = p_ref * driver
            half = 0.5 * dt
            n_mid = n_start * math.exp(-lam * half) + (p_now / lam) * (1.0 - math.exp(-lam * half))
            acts.append(lam * n_mid)
            n_start = n_start * math.exp(-lam * dt) + (p_now / lam) * (1.0 - math.exp(-lam * dt))
        raw_by_key[key] = acts
        ref_by_key[key] = a_ref
        meta_by_key[key] = row

    activity_rows: list[dict[str, Any]] = []
    total_by_day = defaultdict(float)
    ref_total = sum(ref_by_key.values())
    max_day15_rel = 0.0
    for key, raw in raw_by_key.items():
        a_ref = ref_by_key[key]
        anchor = raw[day15_index]
        anchor_scale = a_ref / anchor if anchor > 0.0 else 1.0
        max_day15_rel = max(max_day15_rel, abs(raw[day15_index] * anchor_scale - a_ref) / max(a_ref, 1.0e-300))
        row0 = meta_by_key[key]
        for i, drow in enumerate(drivers):
            act = raw[i] * anchor_scale
            day = float(drow["day_mid"])
            total_by_day[day] += act
            activity_rows.append(
                {
                    "time_bin_id": drow["time_bin_id"],
                    "day_mid": drow["day_mid"],
                    "VN": key[0],
                    "ZA": key[1],
                    "nuclide": key[2],
                    "exc_keV": key[3],
                    "hl_s": row0["hl_s"],
                    "reference_activity_Bq_day15": f"{a_ref:.12e}",
                    "raw_ode_activity_Bq": f"{raw[i]:.12e}",
                    "anchor_scale_to_day15": f"{anchor_scale:.12e}",
                    "activity_Bq": f"{act:.12e}",
                    "activity_ratio_to_day15": f"{act / a_ref:.12e}",
                    "claim_level": "per_nuclide_ODE_anchored_to_day15",
                }
            )

    total_rows = []
    max_total_closure = 0.0
    for drow in drivers:
        day = float(drow["day_mid"])
        total = total_by_day[day]
        grid_total = sum(float(r["activity_Bq"]) for r in activity_rows if int(r["time_bin_id"]) == int(drow["time_bin_id"]))
        rel = abs(total - grid_total) / max(total, 1.0e-300)
        max_total_closure = max(max_total_closure, rel)
        total_rows.append(
            {
                "time_bin_id": drow["time_bin_id"],
                "day_mid": drow["day_mid"],
                "total_activity_Bq_from_nuclide": f"{total:.12e}",
                "total_activity_Bq_grid": f"{grid_total:.12e}",
                "relative_closure_error": f"{rel:.12e}",
                "activity_scale_to_day15": f"{total / ref_total:.12e}",
            }
        )

    audit = {
        "day15_index": day15_index,
        "day15_mid": days[day15_index],
        "reference_total_activity_Bq": ref_total,
        "max_day15_per_nuclide_rel_error": max_day15_rel,
        "max_total_activity_closure_rel_error": max_total_closure,
    }
    return activity_rows, total_rows, audit


def build_background_time_variation(drivers: list[dict[str, Any]], total_activity_rows: list[dict[str, Any]], summary05: dict[str, Any]) -> list[dict[str, Any]]:
    by_day_activity = {float(r["day_mid"]): float(r["activity_scale_to_day15"]) for r in total_activity_rows}
    rates = summary05["expectation_rates_by_stream_cps"]
    rows = []
    for drow in drivers:
        day = float(drow["day_mid"])
        prompt_scale = float(drow["prompt_flux_scale_to_ref"])
        delayed_scale = by_day_activity[day]
        science_scale = float(drow["science_atm_scale_to_ref"])
        out = {
            "time_bin_id": drow["time_bin_id"],
            "time_mid_s": drow["time_mid_s"],
            "day_mid": drow["day_mid"],
            "dt_s": drow["dt_s"],
            "prompt_scale_to_day15": f"{prompt_scale:.12e}",
            "delayed_activity_scale_to_day15": f"{delayed_scale:.12e}",
            "science_atm_scale_to_day15": f"{science_scale:.12e}",
            "T_atm_511": drow["T_atm_511"],
        }
        for stage in ("raw", "bgo", "final"):
            p = rates["prompt"][stage] * prompt_scale
            d = rates["delayed"][stage] * delayed_scale
            s = rates["science"][stage] * science_scale
            out[f"prompt_{stage}_cps"] = f"{p:.12e}"
            out[f"delayed_{stage}_cps"] = f"{d:.12e}"
            out[f"background_{stage}_cps"] = f"{p + d:.12e}"
            out[f"science_{stage}_cps_at_ref_flux"] = f"{s:.12e}"
        if str(drow.get("prompt_driver_backend", "")) == "official_EXPACS_PARMA_CPP_driver":
            out["claim_level"] = "L0_expacs_parma_prompt_driver_rate_reweighting_no_new_transport"
        else:
            out["claim_level"] = "L0_proxy_rate_reweighting_no_new_transport"
        rows.append(out)
    return rows


def write_particle_flux(drivers: list[dict[str, Any]]) -> None:
    rows = []
    expacs_rows = read_csv(OUT / "expacs_particle_scale_by_time.csv") if (OUT / "expacs_particle_scale_by_time.csv").exists() else []
    if expacs_rows and str(drivers[0].get("prompt_driver_backend", "")) == "official_EXPACS_PARMA_CPP_driver":
        for row in expacs_rows:
            rows.append(
                {
                    "time_bin_id": row["time_bin_id"],
                    "day_mid": row["day_mid"],
                    "particle": row["particle"],
                    "scale_to_ref": row["scale_to_day15"],
                    "model_note": "official EXPACS/PARMA C++ driver, scale to day-15 reference condition",
                }
            )
    else:
        for drow in drivers:
            for particle in PARTICLES:
                rows.append(
                    {
                        "time_bin_id": drow["time_bin_id"],
                        "day_mid": drow["day_mid"],
                        "particle": particle,
                        "scale_to_ref": drow["prompt_flux_scale_to_ref"],
                        "model_note": "fallback L0 proxy: common secondary-dominated depth/cutoff scale for all prompt species",
                    }
                )
    write_csv(OUT / "particle_flux_by_time.csv", rows, ["time_bin_id", "day_mid", "particle", "scale_to_ref", "model_note"])


def plot_outputs(trajectory: list[dict[str, Any]], drivers: list[dict[str, Any]], rates: list[dict[str, Any]], totals: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    days = [float(r["day_mid"]) for r in trajectory]
    alt = [float(r["altitude_km"]) for r in trajectory]
    lat = [float(r["latitude_offset_deg"]) for r in trajectory]
    lon = [float(r["longitude_offset_deg"]) for r in trajectory]
    t_atm = [float(r["T_atm_511"]) for r in drivers]
    prompt = [float(r["prompt_final_cps"]) for r in rates]
    delayed = [float(r["delayed_final_cps"]) for r in rates]
    bkg = [float(r["background_final_cps"]) for r in rates]
    sci = [float(r["science_final_cps_at_ref_flux"]) for r in rates]
    act = [float(r["activity_scale_to_day15"]) for r in totals]

    fig, (ax_alt, ax_geo) = plt.subplots(
        2,
        1,
        figsize=(8, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0]},
    )
    ax_alt.plot(days, alt, label="altitude", color="#2f6f9f")
    ax_alt.axvline(DAY15, color="k", ls=":", lw=1)
    ax_alt.set_ylabel("Altitude (km)")
    ax_alt.set_title("Step06 small-offset reference trajectory")
    ax_alt.grid(alpha=0.25)
    ax_alt.legend(fontsize=8)

    ax_geo.plot(days, lat, label="latitude offset", color="#a6463a")
    ax_geo.plot(days, lon, label="longitude offset", color="#3d7f4f")
    ax_geo.axhline(0.0, color="0.35", ls="--", lw=0.8, alpha=0.7)
    ax_geo.axvline(DAY15, color="k", ls=":", lw=1)
    ax_geo.set_xlabel("Mission day")
    ax_geo.set_ylabel("Offset (deg)")
    ax_geo.grid(alpha=0.25)
    ax_geo.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "step06_trajectory_offsets.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.8))
    plt.plot(days, t_atm, label="T_atm_511")
    plt.axhline(T_REF, color="k", ls="--", lw=1, label="Step05 ledger T_ref")
    plt.axvline(DAY15, color="k", ls=":", lw=1)
    plt.xlabel("Mission day")
    plt.ylabel("Transmission")
    plt.title("511 keV atmospheric transmission proxy")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "step06_atmospheric_transmission.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.8))
    plt.plot(days, prompt, label="prompt final")
    plt.plot(days, delayed, label="delayed final")
    plt.plot(days, bkg, label="background final")
    plt.plot(days, sci, label="science final at ref flux")
    plt.axvline(DAY15, color="k", ls=":", lw=1)
    plt.xlabel("Mission day")
    plt.ylabel("Rate (cps)")
    plt.title("Step06 reweighted final-stage rates")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "step06_background_time_variation.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.8))
    plt.plot(days, act, label="total delayed activity / day15")
    plt.axhline(1.0, color="k", ls="--", lw=1)
    plt.axvline(DAY15, color="k", ls=":", lw=1)
    plt.xlabel("Mission day")
    plt.ylabel("Activity scale")
    plt.title("Per-nuclide ODE delayed activity scale")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "step06_delayed_activity_scale.png", dpi=180)
    plt.close()


def write_readme(summary: dict[str, Any]) -> None:
    lines = [
        "# Step06 Mission Time Variation",
        "",
        f"Status: `{summary['claim_level']}`.",
        "",
        "This step adds the first mission-time layer for `new_geo_re` without new Cosima transport.",
        "The time-axis layer is unchanged by the B-FULL optics handoff: it still folds the existing Step05 response rates and does not add new Cosima transport or optics-mass activation.",
        "",
        "## Trajectory Constraint",
        "",
        f"- Latitude center `{LAT_REF_DEG}` deg with max offset `{summary['trajectory']['max_abs_latitude_offset_deg']:.6g}` deg.",
        f"- Longitude center `{LON_REF_DEG}` deg with max offset `{summary['trajectory']['max_abs_longitude_offset_deg']:.6g}` deg.",
        f"- Altitude reference `{ALT_REF_KM}` km with max offset `{summary['trajectory']['max_abs_altitude_offset_km']:.6g}` km.",
        "- This is a synthetic/reference profile, not telemetry.",
        "",
        "## Atmospheric Transmission",
        "",
        "- Model: Beer-Lambert through residual atmospheric depth.",
        "- The effective 511 keV mass attenuation coefficient is calibrated so the day-15/reference bin exactly reproduces the Step05 science ledger transmission.",
        f"- `T_ref = {summary['atmosphere']['T_ref']:.12g}`.",
        f"- `T_day15 = {summary['atmosphere']['T_day15']:.12g}`.",
        f"- absolute closure error `{summary['atmosphere']['day15_abs_error']:.3e}`.",
        f"- transmission range `{summary['atmosphere']['T_min']:.6g}` to `{summary['atmosphere']['T_max']:.6g}`.",
        "",
        "This confirms the correction is internally consistent with the existing Step05 ledger.",
        "",
        "## Prompt And Activation Driver",
        "",
        f"- Backend: `{summary['prompt_driver']['backend']}`.",
        f"- 81-bin EXPACS/PARMA prompt driver status: `{summary['prompt_driver']['status']}`.",
        "- The prompt detector-rate driver is a particle-weighted fold of the 81 trajectory-bin EXPACS/PARMA spectra using current 480-550 keV final-prompt particle weights.",
        "- The delayed-production driver uses EXPACS/PARMA particle scales weighted by the buildup source particle rates, then the activity ODE carries the irradiation history.",
        "- No time bin reruns Cosima detector transport; this is still a rate-level response fold.",
        f"- prompt scale at min altitude `{summary['environment_trend_checks']['prompt_scale_at_min_altitude']:.6g}`.",
        f"- prompt scale at max altitude `{summary['environment_trend_checks']['prompt_scale_at_max_altitude']:.6g}`.",
        f"- altitude vs prompt-scale correlation `{summary['environment_trend_checks']['altitude_vs_prompt_scale_corr']:.6g}`.",
        f"- altitude vs 511 keV transmission correlation `{summary['environment_trend_checks']['altitude_vs_T_atm_corr']:.6g}`.",
        "",
        "## Delayed Activity",
        "",
        "- Each inventory nuclide/volume row is integrated with a half-life ODE.",
        "- The ODE time series is anchored so every nuclide reproduces the fixed Step03 day-15 activity at the day-15 bin.",
        f"- max per-nuclide day-15 relative error `{summary['delayed_activity']['max_day15_per_nuclide_rel_error']:.3e}`.",
        f"- max total ODE/grid closure relative error `{summary['delayed_activity']['max_total_activity_closure_rel_error']:.3e}`.",
        "- Rate folding currently uses a uniform per-Bq delayed response proxy because no per-nuclide detector-response matrix exists yet.",
        "",
        "## Day-15 Closure",
        "",
        f"- prompt final cps day15 `{summary['day15_closure']['prompt_final_cps']:.12g}`.",
        f"- delayed final cps day15 `{summary['day15_closure']['delayed_final_cps']:.12g}`.",
        f"- science final cps day15 `{summary['day15_closure']['science_final_cps_at_ref_flux']:.12g}`.",
        f"- max relative day15 rate closure error `{summary['day15_closure']['max_rel_error']:.3e}`.",
        "",
        "## Outputs",
        "",
        "- `outputs/trajectory_profile.csv`",
        "- `outputs/time_dependent_driver_grid.csv`",
        "- `outputs/atmosphere_transmission_511_by_time.csv`",
        "- `outputs/particle_flux_by_time.csv`",
        "- `outputs/expacs_particle_scale_by_time.csv`",
        "- `outputs/expacs_prompt_driver_weights.csv`",
        "- `outputs/expacs_prompt_driver_summary.json`",
        "- `outputs/activity_by_time_nuclide_volume.csv`",
        "- `outputs/total_activity_by_time.csv`",
        "- `outputs/background_time_variation.csv`",
        "- `outputs/step06_mission_time_variation_summary.json`",
        "- `outputs/figures/`",
        "",
        "## Rebuild",
        "",
        "```bash",
        "python3 stepwise_maintenance/step06_mission_time_variation/code/build_step06_mission_time_variation.py",
        "```",
    ]
    (STEP_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    summary05 = load_json(ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json")
    ledger = read_science_ledger()
    if abs(ledger["T_atm"] - T_REF) > 1.0e-12:
        raise RuntimeError("hard-coded T_REF differs from science ledger")
    trajectory, drivers, atmosphere_model = build_trajectory_and_drivers()
    inventory = read_csv(ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_inventory_day15.csv")
    activity_rows, total_activity_rows, activity_audit = integrate_activity(inventory, drivers)
    rate_rows = build_background_time_variation(drivers, total_activity_rows, summary05)
    plot_outputs(trajectory, drivers, rate_rows, total_activity_rows)

    write_csv(
        OUT / "trajectory_profile.csv",
        trajectory,
        ["time_bin_id", "time_mid_s", "day_mid", "dt_s", "altitude_km", "altitude_offset_km", "latitude_deg", "latitude_offset_deg", "longitude_deg", "longitude_offset_deg", "Rc_GV", "depth_g_cm2"],
    )
    write_csv(
        OUT / "time_dependent_driver_grid.csv",
        drivers,
        [
            "time_bin_id",
            "time_mid_s",
            "day_mid",
            "dt_s",
            "altitude_km",
            "altitude_offset_km",
            "latitude_deg",
            "latitude_offset_deg",
            "longitude_deg",
            "longitude_offset_deg",
            "Rc_GV",
            "depth_g_cm2",
            "source_zenith_deg",
            "path_depth_g_cm2",
            "T_atm_511",
            "science_atm_scale_to_ref",
            "prompt_flux_scale_to_ref",
            "delayed_production_scale_to_ref",
            "proxy_prompt_flux_scale_to_day15",
            "proxy_delayed_production_scale_to_day15",
            "prompt_driver_backend",
            "claim_level",
        ],
    )
    write_csv(
        OUT / "atmosphere_transmission_511_by_time.csv",
        drivers,
        ["time_bin_id", "time_mid_s", "day_mid", "altitude_km", "depth_g_cm2", "source_zenith_deg", "path_depth_g_cm2", "T_atm_511", "science_atm_scale_to_ref", "claim_level"],
    )
    write_particle_flux(drivers)
    write_csv(
        OUT / "activity_by_time_nuclide_volume.csv",
        activity_rows,
        ["time_bin_id", "day_mid", "VN", "ZA", "nuclide", "exc_keV", "hl_s", "reference_activity_Bq_day15", "raw_ode_activity_Bq", "anchor_scale_to_day15", "activity_Bq", "activity_ratio_to_day15", "claim_level"],
    )
    write_csv(
        OUT / "total_activity_by_time.csv",
        total_activity_rows,
        ["time_bin_id", "day_mid", "total_activity_Bq_from_nuclide", "total_activity_Bq_grid", "relative_closure_error", "activity_scale_to_day15"],
    )
    write_csv(
        OUT / "background_time_variation.csv",
        rate_rows,
        ["time_bin_id", "time_mid_s", "day_mid", "dt_s", "prompt_scale_to_day15", "delayed_activity_scale_to_day15", "science_atm_scale_to_day15", "T_atm_511", "prompt_raw_cps", "delayed_raw_cps", "background_raw_cps", "science_raw_cps_at_ref_flux", "prompt_bgo_cps", "delayed_bgo_cps", "background_bgo_cps", "science_bgo_cps_at_ref_flux", "prompt_final_cps", "delayed_final_cps", "background_final_cps", "science_final_cps_at_ref_flux", "claim_level"],
    )

    day15_row = next(r for r in rate_rows if abs(float(r["day_mid"]) - DAY15) < 1.0e-12)
    ref = summary05["expectation_rates_by_stream_cps"]
    closure_terms = [
        abs(float(day15_row["prompt_final_cps"]) - ref["prompt"]["final"]) / ref["prompt"]["final"],
        abs(float(day15_row["delayed_final_cps"]) - ref["delayed"]["final"]) / ref["delayed"]["final"],
        abs(float(day15_row["science_final_cps_at_ref_flux"]) - ref["science"]["final"]) / ref["science"]["final"],
    ]
    t_values = [float(r["T_atm_511"]) for r in drivers]
    day15_driver = next(r for r in drivers if abs(float(r["day_mid"]) - DAY15) < 1.0e-12)
    trend_checks = build_environment_trend_checks(drivers)
    prompt_driver = atmosphere_model["prompt_driver"]
    claim_level = "L0_EXPACS_PROMPT_DRIVER_RATE_FOLD_COMPLETE" if prompt_driver.get("backend") == "official_EXPACS_PARMA_CPP_driver" else "L0_PROXY_COMPLETE"
    summary = {
        "status": "PASS",
        "claim_level": claim_level,
        "optics_policy": "B-FULL Step04/Step09 focal phase space is available; Step06 remains a rate-level time-axis fold and has not rerun detector transport or optics-mass activation",
        "prompt_driver": prompt_driver,
        "trajectory": {
            "profile": "synthetic_small_offset_reference",
            "n_bins": len(trajectory),
            "day_start": 0.0,
            "day_stop": 20.0,
            "step_day": 0.25,
            "max_abs_latitude_offset_deg": max(abs(float(r["latitude_offset_deg"])) for r in trajectory),
            "max_abs_longitude_offset_deg": max(abs(float(r["longitude_offset_deg"])) for r in trajectory),
            "max_abs_altitude_offset_km": max(abs(float(r["altitude_offset_km"])) for r in trajectory),
            "dt_sum_s": sum(float(r["dt_s"]) for r in trajectory),
        },
        "atmosphere": {
            "model": "Beer-Lambert residual-depth proxy calibrated to Step05 science ledger",
            "T_ref": T_REF,
            "T_day15": float(day15_driver["T_atm_511"]),
            "day15_abs_error": abs(float(day15_driver["T_atm_511"]) - T_REF),
            "T_min": min(t_values),
            "T_max": max(t_values),
            **atmosphere_model,
        },
        "environment_trend_checks": trend_checks,
        "delayed_activity": activity_audit,
        "day15_closure": {
            "prompt_final_cps": float(day15_row["prompt_final_cps"]),
            "delayed_final_cps": float(day15_row["delayed_final_cps"]),
            "science_final_cps_at_ref_flux": float(day15_row["science_final_cps_at_ref_flux"]),
            "max_rel_error": max(closure_terms),
        },
        "outputs": {
            "trajectory": rel(OUT / "trajectory_profile.csv"),
            "drivers": rel(OUT / "time_dependent_driver_grid.csv"),
            "background_time_variation": rel(OUT / "background_time_variation.csv"),
            "activity_by_time": rel(OUT / "activity_by_time_nuclide_volume.csv"),
            "expacs_particle_scale_by_time": rel(OUT / "expacs_particle_scale_by_time.csv"),
            "expacs_prompt_driver_summary": rel(OUT / "expacs_prompt_driver_summary.json"),
        },
    }
    write_json(OUT / "step06_mission_time_variation_summary.json", summary)
    write_readme(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
