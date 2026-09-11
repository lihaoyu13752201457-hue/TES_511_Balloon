#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase-2 physical-production summary pipeline.

This script is a local, auditable implementation of the Phase-2 plan.  It
integrates the official EXPACS/PARMA C++ package when available, builds a
reference balloon flight profile, propagates prompt and activation rates through
that profile, creates measured-energy catalog summaries, runs timing/profiled
statistics, and writes a report.  It never labels unavailable full transport as
done: mixed voxel Cosima transport and complete parent-fed branch ratios are
reported as explicit gates when the required physics inputs are absent.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import pickle
import re
import shutil
import subprocess
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

import make_complete_day15_report as complete
from make_day15_report import setup_fonts


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "reports" / "phase2_real_flight_physical_production"
FIG = OUT / "figures"
TABLE = OUT / "tables"
CONFIG = ROOT / "configs" / "phase2"
PARMA_CPP = ROOT / "external" / "expacs_parma" / "parma_cpp"
PARMA_EXE = ROOT / "external" / "expacs_parma" / "phase2_parma_grid_driver"
SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
CATALOG = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
INVENTORY = ROOT / "reports" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
FIXED_SOURCE = ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602_cmfix" / "activation_decay_day15_groundstate_fixed.source"
NEXT = ROOT / "reports" / "nextphase_511"
LIKELIHOOD = NEXT / "likelihood_511" / "likelihood_sensitivity_by_model.csv"
TIMING = NEXT / "timing_window_scan" / "timing_window_scan_summary.csv"
ACTIVATION_DIAG = NEXT / "activation_511_diagnostics" / "activation_511_diagnostic_summary.json"
LINE_SENS = NEXT / "science_line_models" / "sensitivity_by_line_model.csv"

PARTICLES = ["gamma", "n", "p", "alpha", "eminus", "eplus", "muminus", "muplus"]
PARMA_PARTICLE = {"gamma": "gamma", "n": "n", "p": "p", "alpha": "alpha", "eminus": "eminus", "eplus": "eplus", "muminus": "muminus", "muplus": "muplus"}
WINDOWS = {"broad_480_550": (480.0, 550.0), "line_510p3_511p8": (510.3, 511.8)}
MU_AIR_511_CM2_G = 0.088
EARTH_RADIUS_KM = 6371.0
PARMA_SOLAR_DATE = (2025, 8, 31)
PARMA_SOLAR_LABEL = "EXPACS_PARMA_reference_date_2025-08-31"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        try:
            return str(path.relative_to(WORKSPACE))
        except ValueError:
            return str(path)


def fmt(x: Any, digits: int = 6) -> str:
    try:
        v = float(x)
    except Exception:
        return str(x)
    if not math.isfinite(v):
        return "nan"
    if v != 0 and (abs(v) < 1e-3 or abs(v) > 1e4):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}g}"


def ensure_dirs() -> None:
    for path in [OUT, FIG, TABLE, CONFIG]:
        path.mkdir(parents=True, exist_ok=True)


def write_default_profile(path: Path) -> None:
    if path.exists():
        rows = read_csv(path)
        if rows and all(r.get("comment") == "reference_balloon_profile_not_measured_telemetry" for r in rows):
            changed = False
            for row in rows:
                if row.get("solar_state") != PARMA_SOLAR_LABEL:
                    row["solar_state"] = PARMA_SOLAR_LABEL
                    changed = True
            if changed:
                write_csv(path, rows)
        return
    rows = []
    # A reference 20-day balloon profile, not measured flight telemetry.
    for i in range(0, 20 * 4 + 1):
        t = i * 21600.0
        day = t / 86400.0
        altitude = 38.0 + 5.0 * math.sin(2.0 * math.pi * day / 4.0)
        latitude = 34.0 + 5.0 * math.sin(2.0 * math.pi * day / 20.0)
        longitude = 100.0 + 12.0 * day / 20.0
        source_zenith = 52.0 + 48.0 * max(0.0, math.sin(2.0 * math.pi * day / 1.0 - 0.8))
        rows.append({
            "time_s": f"{t:.0f}",
            "day": f"{day:.6f}",
            "altitude_km": f"{altitude:.6f}",
            "latitude_deg": f"{latitude:.6f}",
            "longitude_deg": f"{longitude:.6f}",
            "pressure_hPa": "",
            "vertical_depth_g_cm2": "",
            "source_zenith_deg": f"{source_zenith:.6f}",
            "source_azimuth_deg": "180.0",
            "pointing_ra_deg": "266.4",
            "pointing_dec_deg": "-29.0",
            "solar_state": PARMA_SOLAR_LABEL,
            "comment": "reference_balloon_profile_not_measured_telemetry",
        })
    write_csv(path, rows)


def write_authorities() -> None:
    p = OUT / "CURRENT_AUTHORITIES.md"
    text = f"""# Current Authorities For Phase 2

- Corrected science source: `run_configs/Science_511_onaxis_focalbeam_local.source`.
- Corrected science SIM: `science_511_onaxis_source/Science_511_onaxis_focalbeam_cmfix.inc1.id1.sim.gz`.
- Corrected day-15 summary: `reports/day15_complete_report/complete_day15_summary.json`.
- WP3 line-model table: `reports/nextphase_511/science_line_models/sensitivity_by_line_model.csv`.
- WP4 constant-limit validation: `reports/nextphase_511/time_variable_day1_day20/inventory/constant_limit_validation.json`.
- WP5 spatial audit: `reports/nextphase_511/activation_spatial_model/activation_source_spatial_summary.json`.
- WP7 activation diagnostics: `reports/nextphase_511/activation_511_diagnostics/activation_511_diagnostic_summary.json`.
- WP8 likelihood authority: `reports/nextphase_511/likelihood_511/likelihood_sensitivity_by_model.csv`.
- WP9 injection authority: `reports/nextphase_511/long_timeline_injection/injection_recovery_summary.csv`.
- Final next-phase completion report: `reports/nextphase_511/final_completion_report/COSMOSRAY_BG_2605_nextphase_completion_report.pdf`.

Legacy science source explicitly not current:

```text
Current science beam: z=12.766 cm, radius=1.8 cm
status = CURRENT_CM_GEOMETRY
reason = XZTES geometry is globally scaled by 0.1 so TES active thickness is 0.3 cm
current_authority = Be-window HomogeneousBeam in cm-scaled geometry
current_response_cps_per_ph_cm2_s = recomputed_from_cmfix_science_run
```
"""
    p.write_text(text, encoding="utf-8")


def compile_parma_driver() -> dict[str, Any]:
    driver_src = ROOT / "tools" / "phase2_parma_grid_driver.cpp"
    subroutines = PARMA_CPP / "subroutines.cpp"
    if not PARMA_CPP.exists() or not subroutines.exists():
        return {"status": "MISSING", "physical_environment_available": False, "reason": "PARMA C++ package not present"}
    cmd = ["g++", str(driver_src), str(subroutines), "-O2", "-std=c++11", "-o", str(PARMA_EXE)]
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "physical_environment_available": proc.returncode == 0,
        "command": " ".join(cmd),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "exe": rel(PARMA_EXE),
        "source": rel(driver_src),
        "parma_cpp": rel(PARMA_CPP),
    }


def run_parma_condition(year: int, month: int, day: int, lat: float, lon: float, altitude_km: float, g: float) -> tuple[dict[str, float], list[dict[str, Any]]]:
    cmd = [str(PARMA_EXE), str(year), str(month), str(day), str(lat), str(lon), str(altitude_km), str(g)]
    proc = subprocess.run(cmd, cwd=str(PARMA_CPP), text=True, capture_output=True, check=True)
    lines = [line for line in proc.stdout.splitlines() if line.startswith("META,") or line.startswith("particle,") or re.match(r"^(n|p|alpha|muplus|muminus|eminus|eplus|gamma),", line)]
    meta_line = next(line for line in lines if line.startswith("META,"))
    meta_vals = meta_line.split(",")
    meta = {"W_index": float(meta_vals[1]), "Rc_GV": float(meta_vals[2]), "depth_g_cm2": float(meta_vals[3])}
    rows = []
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("particle,"))
    reader = csv.DictReader(lines[header_idx:])
    for row in reader:
        rows.append({
            "particle": row["particle"],
            "angle_bin": int(row["angle_bin"]),
            "mu_mid": float(row["mu_mid"]),
            "theta_mid_deg": float(row["theta_mid_deg"]),
            "energy_bin": int(row["energy_bin"]),
            "energy_MeV": float(row["energy_MeV"]),
            "angular_integrated_flux_cm2_s_MeV": float(row["angular_integrated_flux_cm2_s_MeV"]),
            "differential_flux_cm2_s_sr_MeV": max(float(row["differential_flux_cm2_s_sr_MeV"]), 0.0),
        })
    return meta, rows


def build_environment_grid(profile_path: Path) -> dict[str, Any]:
    outdir = OUT / "environment_grid_real"
    outdir.mkdir(parents=True, exist_ok=True)
    compile_info = compile_parma_driver()
    profile = read_csv(profile_path)
    if not compile_info.get("physical_environment_available"):
        summary = {**compile_info, "status": "FAIL", "physical_environment_available": False}
        (outdir / "environment_grid_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return summary

    ref_year, ref_month, ref_day = PARMA_SOLAR_DATE
    ref_meta, ref_rows = run_parma_condition(ref_year, ref_month, ref_day, 34.0, 100.0, 38.0, 10.0)
    ref = {(r["particle"], r["angle_bin"], r["energy_bin"]): r for r in ref_rows}
    grid_rows = []
    prompt_scale_rows = []
    science_rows = []
    eps = 1.0e-300
    for ibin, prof in enumerate(profile):
        time_s = float(prof["time_s"])
        day_mid = float(prof["day"])
        alt = float(prof["altitude_km"])
        lat = float(prof["latitude_deg"])
        lon = float(prof["longitude_deg"])
        zen = float(prof["source_zenith_deg"])
        meta, rows = run_parma_condition(ref_year, ref_month, ref_day, lat, lon, alt, 10.0)
        for r in rows:
            rr = ref[(r["particle"], r["angle_bin"], r["energy_bin"])]
            scale = r["differential_flux_cm2_s_sr_MeV"] / max(rr["differential_flux_cm2_s_sr_MeV"], eps)
            grid_rows.append({
                "time_bin_id": ibin,
                "time_mid_s": time_s,
                "day_mid": day_mid,
                "particle": r["particle"],
                "angle_bin": r["angle_bin"],
                "theta_mid_deg": r["theta_mid_deg"],
                "mu_mid": r["mu_mid"],
                "energy_bin": r["energy_bin"],
                "energy_MeV": r["energy_MeV"],
                "flux_cm2_s_sr_MeV": r["differential_flux_cm2_s_sr_MeV"],
                "reference_flux_cm2_s_sr_MeV": rr["differential_flux_cm2_s_sr_MeV"],
                "scale_to_reference": scale,
                "altitude_km": alt,
                "latitude_deg": lat,
                "longitude_deg": lon,
                "Rc_GV": meta["Rc_GV"],
                "depth_g_cm2": meta["depth_g_cm2"],
            })
        # Component average scales, weighted by the reference differential flux.
        by_pa: dict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
        by_particle: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for r in grid_rows[-len(rows):]:
            weight = float(r["reference_flux_cm2_s_sr_MeV"])
            val = float(r["scale_to_reference"])
            by_pa[(str(r["particle"]), int(r["angle_bin"]))].append((weight, val))
            by_particle[str(r["particle"])].append((weight, val))
        for (particle, angle_bin), vals in by_pa.items():
            den = sum(w for w, _ in vals)
            scale = sum(w * v for w, v in vals) / den if den > 0 else 1.0
            prompt_scale_rows.append({
                "time_bin_id": ibin,
                "day_mid": day_mid,
                "particle": particle,
                "angle_bin": angle_bin,
                "scale_to_reference": scale,
                "altitude_km": alt,
                "latitude_deg": lat,
                "longitude_deg": lon,
            })
        # Science atmosphere and Earth-occultation proxy.
        dip = math.degrees(math.acos(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + alt)))
        horizon_zenith = 90.0 + dip
        visible = zen <= horizon_zenith
        if visible:
            cosz = max(math.cos(math.radians(min(zen, 89.0))), 0.05)
            path_depth = meta["depth_g_cm2"] / cosz
            trans = math.exp(-MU_AIR_511_CM2_G * path_depth)
        else:
            path_depth = float("inf")
            trans = 0.0
        science_rows.append({
            "time_bin_id": ibin,
            "time_mid_s": time_s,
            "day_mid": day_mid,
            "altitude_km": alt,
            "source_zenith_deg": zen,
            "horizon_zenith_deg": horizon_zenith,
            "earth_visible": int(visible),
            "vertical_depth_g_cm2": meta["depth_g_cm2"],
            "path_depth_g_cm2": path_depth if math.isfinite(path_depth) else "",
            "T_atm_511": trans,
            "earth_occultation_factor": 1.0 if visible else 0.0,
        })

    write_csv(outdir / "environment_grid_real.csv", grid_rows)
    write_csv(outdir / "prompt_scale_by_particle_angle_energy.csv", prompt_scale_rows)
    write_csv(outdir / "science_atmospheric_transmission.csv", science_rows)

    # Particle average plot.
    particle_curve = []
    for ibin, prof in enumerate(profile):
        for particle in sorted({r["particle"] for r in prompt_scale_rows}):
            vals = [float(r["scale_to_reference"]) for r in prompt_scale_rows if int(r["time_bin_id"]) == ibin and r["particle"] == particle]
            particle_curve.append({"time_bin_id": ibin, "day_mid": prof["day"], "particle": particle, "scale": float(np.mean(vals))})
    write_csv(outdir / "particle_scale_by_time.csv", particle_curve)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for particle in PARTICLES:
        sub = [r for r in particle_curve if r["particle"] == particle]
        if not sub:
            continue
        ax.plot([float(r["day_mid"]) for r in sub], [float(r["scale"]) for r in sub], label=particle, lw=1.2)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("PARMA scale to 38 km reference")
    ax.set_title("Phase-2 reference flight prompt scale by particle")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncols=4)
    fig.tight_layout()
    fig.savefig(FIG / "phase2_particle_scale_by_day.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot([float(r["day_mid"]) for r in science_rows], [float(r["T_atm_511"]) for r in science_rows], color="#4C78A8")
    ax.set_xlabel("Flight day")
    ax.set_ylabel("511 keV atmospheric transmission")
    ax.set_title("Science 511 atmospheric transmission and Earth occultation")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "phase2_science_transmission.png", dpi=220)
    plt.close(fig)

    scales = [float(r["scale_to_reference"]) for r in grid_rows if math.isfinite(float(r["scale_to_reference"]))]
    summary = {
        "status": "PASS",
        "backend": "official_EXPACS_PARMA_CPP_driver",
        "physical_environment_available": True,
        "parma_compile": compile_info,
        "reference_condition": {"year": ref_year, "month": ref_month, "day": ref_day, "lat": 34.0, "lon": 100.0, "altitude_km": 38.0, "g": 10.0, **ref_meta},
        "profile": rel(profile_path),
        "n_time_bins": len(profile),
        "n_grid_rows": len(grid_rows),
        "scale_min": min(scales),
        "scale_max": max(scales),
        "science_T_atm_min": min(float(r["T_atm_511"]) for r in science_rows),
        "science_T_atm_max": max(float(r["T_atm_511"]) for r in science_rows),
        "caveat": "Reference flight profile is a physically motivated 33-43 km balloon profile, not measured telemetry; PARMA g=10 ideal-atmosphere mode is used for the environment scale. For altitude >=25 km, atmospheric depth is supplied by an exponential standard-atmosphere approximation because the public PARMA C++ altitude helper falls back outside this range.",
    }
    (outdir / "environment_grid_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def event_indices_for_window(cat: dict[str, Any], lo: float, hi: float) -> np.ndarray:
    return np.flatnonzero((cat["tes_total_keV"] >= lo) & (cat["tes_total_keV"] < hi))


def prompt_component_rates() -> dict[str, Any]:
    cat = pickle.load(open(CATALOG, "rb"))
    streams = cat["stream"].astype(str)
    tags = cat["tag"].astype(str)
    out: dict[str, Any] = {}
    reject_policy = "keep"
    for wname, (lo, hi) in WINDOWS.items():
        rows = []
        for idx in event_indices_for_window(cat, lo, hi):
            idx = int(idx)
            if streams[idx] != "prompt":
                continue
            particle = tags[idx]
            rate = float(cat["rate_hz"][idx])
            stage = "raw"
            rows.append((particle, stage, rate))
            if float(cat["bgo_total_keV"][idx]) < complete.BGO_THR_KEV:
                rows.append((particle, "bgo", rate))
                keep, _cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
                if keep:
                    rows.append((particle, "final", rate))
        agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for particle, stage, rate in rows:
            agg[particle][stage] += rate
        out[wname] = {p: dict(v) for p, v in agg.items()}
    return out


def build_prompt_metadata_and_reweight() -> dict[str, Any]:
    outdir = OUT / "prompt_reweight_real"
    outdir.mkdir(parents=True, exist_ok=True)
    env_scales = read_csv(OUT / "environment_grid_real" / "prompt_scale_by_particle_angle_energy.csv")
    prompt_rates = prompt_component_rates()

    # Average over source angles because the existing event catalog does not retain
    # the individual source component or primary energy for each prompt event.
    scale_by_time_particle: dict[tuple[int, str], list[float]] = defaultdict(list)
    for r in env_scales:
        scale_by_time_particle[(int(r["time_bin_id"]), r["particle"])].append(float(r["scale_to_reference"]))
    particle_scale_rows = []
    for (time_bin, particle), vals in sorted(scale_by_time_particle.items()):
        particle_scale_rows.append({"time_bin_id": time_bin, "particle": particle, "scale": float(np.mean(vals))})
    write_csv(outdir / "prompt_event_metadata.csv", [
        {"particle": p, "metadata_level": "particle_only", "primary_energy_assignment": "not_available_in_current_catalog", "angle_assignment": "averaged_over_20_source_components"}
        for p in sorted({p for w in prompt_rates.values() for p in w})
    ])

    profile = read_csv(CONFIG / "flight_profile_real.csv")
    rate_rows = []
    for ibin, prof in enumerate(profile):
        for window, pdata in prompt_rates.items():
            totals = {"raw": 0.0, "bgo": 0.0, "final": 0.0}
            for particle, stages in pdata.items():
                scale = np.mean([r["scale"] for r in particle_scale_rows if r["time_bin_id"] == ibin and r["particle"] == PARMA_PARTICLE.get(particle, particle)])
                for stage in totals:
                    totals[stage] += float(stages.get(stage, 0.0)) * float(scale)
                rate_rows.append({
                    "time_bin_id": ibin,
                    "day_mid": prof["day"],
                    "window": window,
                    "particle": particle,
                    "scale": float(scale),
                    "raw_cps": float(stages.get("raw", 0.0)) * float(scale),
                    "bgo_cps": float(stages.get("bgo", 0.0)) * float(scale),
                    "final_cps": float(stages.get("final", 0.0)) * float(scale),
                })
            rate_rows.append({
                "time_bin_id": ibin,
                "day_mid": prof["day"],
                "window": window,
                "particle": "TOTAL",
                "scale": "",
                "raw_cps": totals["raw"],
                "bgo_cps": totals["bgo"],
                "final_cps": totals["final"],
            })
    write_csv(outdir / "prompt_rate_by_time_particle.csv", rate_rows)
    final_rows = [r for r in rate_rows if r["particle"] == "TOTAL"]
    write_csv(outdir / "prompt_final_rate_by_time_window.csv", final_rows)

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for window in WINDOWS:
        sub = [r for r in final_rows if r["window"] == window]
        ax.plot([float(r["day_mid"]) for r in sub], [float(r["final_cps"]) for r in sub], marker=".", label=window)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("Prompt final rate (cps)")
    ax.set_title("Real-profile prompt final rate from PARMA particle scales")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "phase2_prompt_rate_day_curve.png", dpi=220)
    plt.close(fig)

    ref = load_json(SUMMARY)["expectation_rates_by_stream_cps"]["prompt"]
    summary = {
        "status": "PASS",
        "metadata_level": "particle_only_with_angle_energy_scale_averaged",
        "primary_energy_assignment": "not_available_in_current_catalog",
        "reference_prompt_final_480_550_cps": ref["final"],
        "real_profile_final_480_550_min_cps": min(float(r["final_cps"]) for r in final_rows if r["window"] == "broad_480_550"),
        "real_profile_final_480_550_max_cps": max(float(r["final_cps"]) for r in final_rows if r["window"] == "broad_480_550"),
        "caveat": "Current prompt event catalog has particle identity but not source angle/primary-energy identity; PARMA angle/energy scales are therefore averaged per particle for rate reweighting.",
    }
    (outdir / "prompt_reweight_real_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def integrate_parentfed_inventory() -> dict[str, Any]:
    outdir = OUT / "activation_inventory_parentfed"
    outdir.mkdir(parents=True, exist_ok=True)
    inv = read_csv(INVENTORY)
    prompt = read_csv(OUT / "prompt_reweight_real" / "prompt_final_rate_by_time_window.csv")
    profile = read_csv(CONFIG / "flight_profile_real.csv")
    # Activation driver: neutron/proton/alpha-sensitive proxy normalized to day-15-ish average.
    broad = [r for r in prompt if r["window"] == "broad_480_550" and r["particle"] == "TOTAL"]
    vals = np.asarray([float(r["final_cps"]) for r in broad])
    driver = vals / np.mean(vals) if np.mean(vals) > 0 else np.ones_like(vals)
    t_ref = 15.0 * 86400.0
    inventories_by_day: dict[float, list[dict[str, Any]]] = {}
    current: dict[tuple[str, str, str], float] = {}
    p_ref: dict[tuple[str, str, str], float] = {}
    lam: dict[tuple[str, str, str], float] = {}
    meta: dict[tuple[str, str, str], dict[str, str]] = {}
    for r in inv:
        key = (r["VN"], r["ZA"], r["exc_keV"])
        hl = float(r["hl_s"])
        l = math.log(2.0) / hl if hl > 0 else 0.0
        a_ref = float(r["Activity_Bq_after_fix"])
        prod = a_ref / max(1.0 - math.exp(-l * t_ref), 1.0e-30) if l > 0 else 0.0
        current[key] = 0.0
        p_ref[key] = prod
        lam[key] = l
        meta[key] = r
    prev_t = 0.0
    target_days = {1.0, 5.0, 10.0, 15.0, 20.0}
    all_rows = []
    for i, prof in enumerate(profile):
        t = float(prof["time_s"])
        dt = max(t - prev_t, 0.0)
        scale = float(driver[i])
        for key in current:
            l = lam[key]
            p = p_ref[key] * scale
            if l > 0:
                current[key] = current[key] * math.exp(-l * dt) + p / l * (1.0 - math.exp(-l * dt))
            else:
                current[key] = current[key] + p * dt
        prev_t = t
        day = round(float(prof["day"]), 6)
        nearest = min(target_days, key=lambda x: abs(x - day))
        if abs(nearest - day) < 0.001 or day in target_days:
            rows = []
            for key, n_atoms in current.items():
                m = meta[key]
                a = lam[key] * n_atoms
                row = {
                    "day": nearest,
                    "VN": m["VN"],
                    "ZA": m["ZA"],
                    "nuclide": m["nuclide"],
                    "exc_keV": m["exc_keV"],
                    "hl_s": m["hl_s"],
                    "Activity_Bq_parentfed": a,
                    "Activity_Bq_no_parent": a,
                    "parent_feed_fraction": 0.0,
                    "direct_production_fraction": 1.0,
                    "decay_chain_data_status": "branch_ratios_not_available_locally",
                }
                rows.append(row)
                all_rows.append(row)
            inventories_by_day[nearest] = rows
    for day, rows in inventories_by_day.items():
        write_csv(outdir / f"inventory_parentfed_day{int(day):02d}.csv", rows)
    write_csv(outdir / "activity_by_time_nuclide_volume_parentfed.csv", all_rows)

    top = sorted(inventories_by_day.get(15.0, []), key=lambda r: float(r["Activity_Bq_parentfed"]), reverse=True)[:12]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for nuclide in sorted({r["nuclide"] for r in top}):
        series = []
        for day in sorted(inventories_by_day):
            total = sum(float(r["Activity_Bq_parentfed"]) for r in inventories_by_day[day] if r["nuclide"] == nuclide)
            series.append((day, total))
        ax.plot([d for d, _ in series], [v for _, v in series], marker="o", label=nuclide)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("Activity (Bq)")
    ax.set_title("Top activation activities under Phase-2 profile driver")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(FIG / "phase2_top_nuclide_activity_vs_day.png", dpi=220)
    plt.close(fig)

    summary = {
        "status": "PASS_WITH_LIMITED_PARENT_FEED",
        "parent_feed_available": False,
        "reason": "Local NUBASE half-life data are available, but audited branch-ratio parent-feed tables are not available in the workspace.",
        "mode": "real_profile_independent_production_with_parentfed_schema",
        "days_written": sorted(inventories_by_day),
        "day15_total_activity_Bq": sum(float(r["Activity_Bq_parentfed"]) for r in inventories_by_day.get(15.0, [])),
        "caveat": "The schema carries parent-feed fields, but parent_feed_fraction is zero until audited branch-ratio data are added.",
    }
    (outdir / "inventory_parentfed_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def build_real_profile_delayed_sources() -> dict[str, Any]:
    outdir = OUT / "delayed_sources_real_profile"
    prod = ROOT / "production_runs" / "phase2_real_profile_delayed_level1"
    outdir.mkdir(parents=True, exist_ok=True)
    prod.mkdir(parents=True, exist_ok=True)
    template = FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore").splitlines()
    day15 = read_csv(OUT / "activation_inventory_parentfed" / "inventory_parentfed_day15.csv")
    ref_by_za = defaultdict(float)
    for r in day15:
        ref_by_za[r["ZA"]] += float(r["Activity_Bq_parentfed"])
    records = []
    for day in (1, 5, 10, 15, 20):
        inv_path = OUT / "activation_inventory_parentfed" / f"inventory_parentfed_day{day:02d}.csv"
        rows = read_csv(inv_path)
        by_za = defaultdict(float)
        for r in rows:
            by_za[r["ZA"]] += float(r["Activity_Bq_parentfed"])
        ratios = {za: by_za[za] / ref_by_za[za] if ref_by_za[za] > 0 else 1.0 for za in set(ref_by_za) | set(by_za)}
        out_lines = []
        cur_za = None
        scaled = 0
        for line in template:
            m_pt = re.search(r"\.ParticleType\s+(\d+)", line)
            if m_pt:
                cur_za = m_pt.group(1)
            m_flux = re.search(r"(\.Flux\s+)([-+0-9.eE]+)", line)
            if m_flux and cur_za:
                val = float(m_flux.group(2)) * ratios.get(cur_za, 1.0)
                line = re.sub(r"(\.Flux\s+)([-+0-9.eE]+)", rf"\g<1>{val:.12e}", line)
                scaled += 1
            out_lines.append(line)
        day_dir = prod / f"day{day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)
        src = day_dir / f"activation_decay_day{day:02d}_real_profile_level1.source"
        src.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        records.append({"day": day, "source": rel(src), "flux_lines_scaled": scaled, "spatial_profile_mode": "fixed_day15_scaled", "total_activity_Bq": sum(by_za.values())})
    write_csv(outdir / "delayed_source_level1_manifest.csv", records)
    summary = {
        "status": "PASS",
        "spatial_profile_mode": "fixed_day15_scaled",
        "source_dir": rel(prod),
        "records": records,
        "caveat": "Level-1 delayed sources use fixed day-15 spatial profiles scaled by the real-profile activity schema; no new RPIP spatial distributions are generated.",
    }
    (outdir / "source_build_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def write_mixed_voxel_gate() -> dict[str, Any]:
    outdir = OUT / "mixed_voxel_transport"
    outdir.mkdir(parents=True, exist_ok=True)
    spatial = load_json(NEXT / "activation_spatial_model" / "activation_source_spatial_summary.json", {})
    summary = {
        "status": "NOT_RUN_REQUIRES_COSIMA_TRANSPORT",
        "normalization_audit_status": spatial.get("status"),
        "voxel_activity_fraction": spatial.get("voxel_activity_fraction"),
        "radial_vs_mixed_selected_rate_available": False,
        "reason": "Current phase generated Level-1 real-profile sources but did not run a new mixed radial/voxel delayed Cosima transport. Reporting this as a gate prevents false publication-level claims.",
    }
    (outdir / "radial_vs_mixed_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "README.md").write_text("# Mixed Voxel Transport Gate\n\n" + summary["reason"] + "\n", encoding="utf-8")
    return summary


def build_event_catalog_v2_summary() -> dict[str, Any]:
    outdir = OUT / "event_catalog_v2_measured"
    outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(26052026)
    cat = pickle.load(open(CATALOG, "rb"))
    n = len(cat["stream"])
    pix_meas = np.asarray(cat["pix_e"], dtype=float) + rng.normal(0.0, 0.14 / 2.3548200450309493, size=len(cat["pix_e"]))
    pix_meas = np.maximum(pix_meas, 0.0)
    tes_meas = np.zeros(n, dtype=float)
    for i in range(n):
        s = int(cat["pix_start"][i])
        c = int(cat["pix_count"][i])
        if c:
            tes_meas[i] = float(np.sum(pix_meas[s:s + c]))
    bgo_meas = np.maximum(np.asarray(cat["bgo_total_keV"], dtype=float) + rng.normal(0.0, 1.0 / 2.3548200450309493, size=n), 0.0)
    streams = cat["stream"].astype(str)
    summary_rows = []
    for window, (lo, hi) in WINDOWS.items():
        for etype, tes, bgo in (("true", np.asarray(cat["tes_total_keV"], dtype=float), np.asarray(cat["bgo_total_keV"], dtype=float)), ("measured", tes_meas, bgo_meas)):
            mask = (tes >= lo) & (tes < hi)
            raw = float(np.sum(cat["rate_hz"][mask]))
            bmask = mask & (bgo < complete.BGO_THR_KEV)
            bgo_rate = float(np.sum(cat["rate_hz"][bmask]))
            final = 0.0
            for idx in np.flatnonzero(bmask):
                keep, _cls = complete.classify_final(complete.event_hits(cat, int(idx)), "keep")
                if keep:
                    final += float(cat["rate_hz"][idx])
            summary_rows.append({"window": window, "energy_type": etype, "raw_cps": raw, "bgo_cps": bgo_rate, "final_cps": final})
    write_csv(outdir / "true_vs_measured_rates.csv", summary_rows)
    # Save compact arrays needed by later audit, not full duplicated hit tables.
    with (outdir / "event_catalog_v2_measured_compact.pkl").open("wb") as fh:
        pickle.dump({"tes_total_measured_keV": tes_meas, "bgo_total_measured_keV": bgo_meas, "pix_e_measured_keV": pix_meas}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    summary = {
        "status": "PASS_WITH_BGO_EVENT_TOTAL_PROXY",
        "events": n,
        "pixel_hits": len(cat["pix_e"]),
        "tes_fwhm_keV": 0.14,
        "bgo_fwhm_keV": 1.0,
        "bgo_hit_mode": "event_total_proxy",
        "rates_csv": rel(outdir / "true_vs_measured_rates.csv"),
        "catalog_compact": rel(outdir / "event_catalog_v2_measured_compact.pkl"),
        "caveat": "TES is smeared per pixel; BGO remains event-total proxy because the current catalog did not retain per-BGO-hit records.",
    }
    (outdir / "catalog_v2_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_timing_daq_models() -> dict[str, Any]:
    outdir = OUT / "timing_daq"
    outdir.mkdir(parents=True, exist_ok=True)
    wp6 = read_csv(TIMING)
    broad = {float(r["window_us"]): r for r in wp6 if r["energy_window"] == "broad_480_550"}
    models = [
        ("rolling_1us", 1.0, 1.0),
        ("fixed_gate_10us", 10.0, 1.03),
        ("bgo_prepost_30us", 30.0, 1.05),
        ("deadtime_pileup_100us", 100.0, 0.92),
    ]
    rows = []
    for name, nearest, factor in models:
        src = broad[nearest]
        rows.append({
            "model": name,
            "equivalent_window_us": nearest,
            "background_final_cps": float(src["background_final_cps"]) * factor,
            "science_survival": float(src["science_survival"]) * min(factor, 1.0),
            "flux_3sigma_1Ms": float(src["broad_flux3_1Ms_if_applicable"]) / max(min(factor, 1.0), 1e-9),
            "model_status": "toy_hardware_proxy",
        })
    write_csv(outdir / "timing_daq_model_summary.csv", rows)
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    ax.bar([r["model"] for r in rows], [float(r["science_survival"]) for r in rows], color="#4C78A8")
    ax.set_ylabel("Science survival")
    ax.set_title("Phase-2 timing/DAQ model scan")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "phase2_science_survival_by_timing_model.png", dpi=220)
    plt.close(fig)
    summary = {"status": "PASS_TOY_DAQ_MODELS", "models": rows, "caveat": "DAQ models are timing proxies built from WP6 bootstrap rows; hardware impulse response/deadtime must replace these before publication-level claims."}
    (outdir / "timing_daq_model_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def build_activation_truth_table() -> dict[str, Any]:
    outdir = OUT / "activation_511_truth"
    outdir.mkdir(parents=True, exist_ok=True)
    diag = load_json(ACTIVATION_DIAG)
    inv = read_csv(INVENTORY)
    activity_by_nuclide = defaultdict(float)
    hl_by_nuclide = {}
    za_by_nuclide = {}
    for r in inv:
        activity_by_nuclide[r["nuclide"]] += float(r["Activity_Bq_after_fix"])
        hl_by_nuclide[r["nuclide"]] = float(r["hl_s"])
        za_by_nuclide[r["nuclide"]] = r["ZA"]
    beta_plus = {"O-15": 0.999, "C-11": 0.997, "Ga-68": 0.891}
    rows = []
    for r in diag["top_nuclides_by_broad_final"]:
        n = r["nuclide"]
        rows.append({
            "nuclide": n,
            "ZA": za_by_nuclide.get(n, r.get("ZA", "")),
            "half_life_s": hl_by_nuclide.get(n, ""),
            "decay_mode_proxy": "beta_plus_or_EC" if n in beta_plus or n.startswith("Ge-") else "gamma_or_beta_continuum",
            "beta_plus_branch_proxy": beta_plus.get(n, 0.0),
            "parent_feed_fraction": 0.0,
            "direct_production_fraction": 1.0,
            "source_activity_Bq": activity_by_nuclide.get(n, 0.0),
            "broad_480_550_final_cps": r["broad_480_550_final_cps"],
            "line_510p3_511p8_final_cps": r["line_510p3_511p8_final_cps"],
            "near_506_516_final_cps": r["near_506_516_final_cps"],
            "volume_proxy_list": r["volumes"],
            "truth_status": "transport_truth_from_SIM_plus_decay_proxy",
        })
    write_csv(outdir / "activation_511_truth_table.csv", rows)
    summary = {"status": "PASS_WITH_DECAY_PROXY", "rows": len(rows), "top_broad_nuclide": rows[0]["nuclide"], "caveat": "Nuclide rates are true SIM transport diagnostics; decay modes/branch ratios are local proxies unless audited ENSDF/Geant4 decay tables are added."}
    (outdir / "activation_511_truth_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_profile_likelihood_and_injection() -> tuple[dict[str, Any], dict[str, Any]]:
    ldir = OUT / "likelihood_profiled"
    idir = OUT / "long_timeline_injection_profiled"
    ldir.mkdir(parents=True, exist_ok=True)
    idir.mkdir(parents=True, exist_ok=True)
    base = read_csv(LIKELIHOOD)
    rows = []
    nuisance = {
        "alpha_prompt_total": 0.10,
        "alpha_delayed_total": 0.10,
        "alpha_W187": 0.20,
        "alpha_timing_survival": 0.08,
        "TES_FWHM": 0.05,
        "science_atmospheric_transmission": 0.10,
    }
    degradation = math.sqrt(1.0 + sum(v * v for v in nuisance.values()) * 6.0)
    for r in base:
        out = dict(r)
        out["nuisance_model"] = "diagonal_gaussian_proxy"
        out["profile_degradation_factor"] = degradation
        out["profiled_flux_3sigma_ph_cm2_s"] = float(r["flux_3sigma_ph_cm2_s"]) * degradation
        out["profiled_flux_5sigma_ph_cm2_s"] = float(r["flux_5sigma_ph_cm2_s"]) * degradation
        rows.append(out)
    write_csv(ldir / "asimov_profiled_sensitivity.csv", rows)
    (ldir / "profile_likelihood_template_summary.json").write_text(json.dumps({
        "status": "PASS_PROXY_PROFILE_LIKELIHOOD",
        "nuisance_priors_fractional": nuisance,
        "degradation_factor": degradation,
        "caveat": "This is a profile-likelihood proxy using diagonal nuisance degradation on current templates, not a full Poisson optimizer with separate background templates.",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    one = [r for r in rows if abs(float(r["exposure_s"]) - 1e6) < 1]
    ax.bar(np.arange(len(one)) - 0.18, [float(r["flux_3sigma_ph_cm2_s"]) for r in one], width=0.36, label="Fisher")
    ax.bar(np.arange(len(one)) + 0.18, [float(r["profiled_flux_3sigma_ph_cm2_s"]) for r in one], width=0.36, label="profiled proxy")
    ax.set_xticks(np.arange(len(one)), [f"{r['energy_window']}\n{r['model']}" for r in one], rotation=40, ha="right", fontsize=7)
    ax.set_ylabel("3 sigma / 1 Ms flux")
    ax.set_title("Profiled nuisance proxy vs Fisher baseline")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "phase2_profiled_vs_fisher_threshold.png", dpi=220)
    plt.close(fig)

    rng = np.random.default_rng(26052027)
    fluxes = [0.0, 3e-5, 5e-5, 7e-5, 1e-4, 1.5e-4, 2e-4, 5e-4]
    exposures = [1e5, 1e6, 1e7]
    inj_rows = []
    for r in one:
        sigma_1ms = float(r["profiled_flux_3sigma_ph_cm2_s"]) / 3.0
        for exp in exposures:
            sigma = sigma_1ms * math.sqrt(1e6 / exp)
            for f in fluxes:
                draws = rng.normal(loc=f, scale=sigma, size=20000)
                z = draws / sigma
                inj_rows.append({
                    "energy_window": r["energy_window"],
                    "model": r["model"],
                    "exposure_s": exp,
                    "input_flux_ph_cm2_s": f,
                    "sigma_flux": sigma,
                    "mean_recovered_flux": float(np.mean(draws)),
                    "std_recovered_flux": float(np.std(draws, ddof=1)),
                    "P3": float(np.mean(z >= 3.0)),
                    "P5": float(np.mean(z >= 5.0)),
                    "n_realizations": 20000,
                })
    write_csv(idir / "source_injection_profiled_summary.csv", inj_rows)
    write_csv(idir / "real_flight_detection_probability.csv", inj_rows)
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    for rkey in [("broad_480_550", "energy_radius_layer_template"), ("line_510p3_511p8", "energy_radius_layer_template")]:
        sub = sorted([r for r in inj_rows if r["energy_window"] == rkey[0] and r["model"] == rkey[1] and abs(float(r["exposure_s"]) - 1e6) < 1], key=lambda x: float(x["input_flux_ph_cm2_s"]))
        ax.plot([float(r["input_flux_ph_cm2_s"]) for r in sub], [float(r["P3"]) for r in sub], marker="o", label="/".join(rkey))
    ax.set_xlabel("Injected flux")
    ax.set_ylabel("P(>=3 sigma), 1 Ms")
    ax.set_title("Profiled source-injection proxy")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "phase2_P3_vs_flux_profiled.png", dpi=220)
    plt.close(fig)
    inj_summary = {
        "status": "PASS_PROXY_PROFILED_INJECTION",
        "rows": len(inj_rows),
        "caveat": "Injection uses Gaussian profiled-flux proxy from degraded Fisher thresholds; full profiled Poisson source injection remains a future gate.",
    }
    (idir / "source_injection_profiled_summary.json").write_text(json.dumps(inj_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    like_summary = load_json(ldir / "profile_likelihood_template_summary.json")
    return like_summary, inj_summary


def build_image8_style_tables() -> None:
    summary = load_json(SUMMARY)
    rows = []
    for stream, vals in summary["expectation_rates_by_stream_cps"].items():
        rows.append({"component": stream, "window": "broad_480_550", "raw_cps": vals["raw"], "bgo_cps": vals["bgo"], "final_cps": vals["final"]})
    act = load_json(ACTIVATION_DIAG)
    rows.append({"component": "activation_delayed_only", "window": "line_510p3_511p8", "raw_cps": act["totals"]["line_510p3_511p8"]["raw_cps"], "bgo_cps": act["totals"]["line_510p3_511p8"]["bgo_cps"], "final_cps": act["totals"]["line_510p3_511p8"]["final_cps"]})
    write_csv(TABLE / "image8_style_component_rates.csv", rows)
    for window in ["broad_480_550", "line_510p3_511p8"]:
        sub = [r for r in rows if r["window"] == window]
        if not sub:
            continue
        fig, ax = plt.subplots(figsize=(6.2, 4.5))
        ax.bar([r["component"] for r in sub], [float(r["final_cps"]) for r in sub], color=["#4C78A8", "#F58518", "#54A24B"][:len(sub)])
        ax.set_ylabel("Final rate (cps)")
        ax.set_title(f"IMAGE8-style final component rates: {window}")
        ax.tick_params(axis="x", rotation=25)
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(FIG / f"phase2_image8_{window}.png", dpi=220)
        plt.close(fig)


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(f, "")) for f in fields) + " |")
    return "\n".join(lines)


def add_text_page(pdf: PdfPages, title: str, body: str, font_prop: Any) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes([0.06, 0.05, 0.88, 0.90])
    ax.axis("off")
    ax.text(0.0, 1.02, title, fontsize=15, weight="bold", va="top", fontproperties=font_prop)
    wrapped = []
    for para in body.splitlines():
        if para.startswith("|") or para.startswith("- ") or para.startswith("#") or not para.strip():
            wrapped.append(para)
        else:
            wrapped.extend(textwrap.wrap(para, width=90) or [""])
    ax.text(0.0, 0.98, "\n".join(wrapped), fontsize=8.8, va="top", linespacing=1.25, fontproperties=font_prop)
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf: PdfPages, title: str, path: Path, caption: str, font_prop: Any) -> None:
    if not path.exists():
        add_text_page(pdf, title, f"Missing figure: {rel(path)}\n{caption}", font_prop)
        return
    img = mpimg.imread(path)
    fig = plt.figure(figsize=(8.27, 11.69))
    ax_t = fig.add_axes([0.06, 0.91, 0.88, 0.05]); ax_t.axis("off")
    ax_t.text(0.0, 0.8, title, fontsize=15, weight="bold", fontproperties=font_prop)
    ax = fig.add_axes([0.06, 0.18, 0.88, 0.70]); ax.imshow(img); ax.axis("off")
    ax_c = fig.add_axes([0.06, 0.05, 0.88, 0.10]); ax_c.axis("off")
    ax_c.text(0.0, 1.0, caption, fontsize=9, va="top", fontproperties=font_prop)
    pdf.savefig(fig)
    plt.close(fig)


def make_report(pieces: dict[str, Any]) -> dict[str, Any]:
    build_image8_style_tables()
    profile_rows = read_csv(OUT / "likelihood_profiled" / "asimov_profiled_sensitivity.csv")
    inj_rows = read_csv(OUT / "long_timeline_injection_profiled" / "source_injection_profiled_summary.csv")
    key_like = [
        {
            "window": r["energy_window"],
            "model": r["model"],
            "Fisher_3s_1Ms": fmt(r["flux_3sigma_ph_cm2_s"]),
            "Profiled_3s_1Ms": fmt(r["profiled_flux_3sigma_ph_cm2_s"]),
        }
        for r in profile_rows if abs(float(r["exposure_s"]) - 1e6) < 1 and r["model"] in {"window_counting_same_events", "energy_radius_layer_template"}
    ]
    key_inj = [
        {
            "window": r["energy_window"],
            "model": r["model"],
            "flux": r["input_flux_ph_cm2_s"],
            "P3": fmt(r["P3"], 4),
            "P5": fmt(r["P5"], 4),
        }
        for r in inj_rows
        if abs(float(r["exposure_s"]) - 1e6) < 1 and abs(float(r["input_flux_ph_cm2_s"]) - 1e-4) < 1e-12 and r["model"] == "energy_radius_layer_template"
    ]
    phase2_summary = {
        "status": "PASS_PRELIMINARY_PHYSICAL_PROFILE_WITH_GATED_LIMITATIONS",
        "project_definition": {
            "geometry": "Inherited XZTES/TibetTES_v5_6layers geometry.",
            "sources": "20-bin up/down atmospheric cosmic rays, corrected delayed activation, Doppler-broadened 511 source with optics/atmosphere/occultation factors.",
            "veto": "BGO and Compton/FoV veto on event/timing candidates.",
            "time_variability": "PARMA-driven 33-43 km profile plus activation ODE schema.",
        },
        "pieces": pieces,
        "key_profiled_likelihood_rows_1Ms": key_like,
        "key_profiled_injection_rows_1Ms_flux1e-4": key_inj,
        "publication_guard": [
            "Do not call the reference profile measured flight telemetry.",
            "Do not call parent-fed complete until branch ratios are audited.",
            "Do not call mixed voxel transport complete until Cosima transport is run.",
            "Do not call profiled likelihood publication-level until full Poisson nuisance fit replaces proxy degradation.",
        ],
    }
    (OUT / "phase2_summary.json").write_text(json.dumps(phase2_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md = f"""# COSMOSRAY_BG_2605 Phase 2 Real-Flight Physical Production Report

状态：`{phase2_summary['status']}`

## 项目定义

本项目几何继承旧 XZTES/TibetTES 六层 TES/BGO 质量模型。源模型由三部分组成：上行+下行 20-bin 大气宇宙线 prompt/buildup；由 buildup RPIP 记录构造并经 W183/W180 ground-state 修正的 delayed activation；以及带 intrinsic line width 的 511 keV science source。Science source 在 Cosima 中只代表聚焦光学后的 Be-window 入射光子；物理通量通过 optics effective area、大气衰减和地球遮挡因子归一化。

## Phase 2 已实现内容

- 官方 EXPACS/PARMA C++ 包已下载到 `external/expacs_parma/`，并用本地 driver 计算 33-43 km reference balloon profile 的 particle/angle/energy scale。
- 生成 `configs/phase2/flight_profile_real.csv`：这是物理参考剖面，不是实测 flight telemetry。
- 生成 real-profile prompt reweight。当前 catalog 只保留 particle，不保留 source angle/primary energy，因此 angle/energy scale 按 particle 加权平均。
- 生成 activation parent-fed schema 和 real-profile Level-1 delayed source。由于本地没有审计过的 parent branch-ratio 表，parent_feed_fraction 当前为 0。
- 生成 measured-energy catalog v2 compact proxy。TES 为 per-pixel smear；BGO 仍为 event-total proxy。
- 生成 timing/DAQ toy hardware models、activation 511 truth table、profile-likelihood proxy 和 profiled source injection。

## 核心数值

Profiled likelihood proxy, 1 Ms:

{md_table(key_like, ['window','model','Fisher_3s_1Ms','Profiled_3s_1Ms'])}

Profiled source injection proxy, 1 Ms, F=1e-4:

{md_table(key_inj, ['window','model','flux','P3','P5'])}

## 关键限制

- `environment_grid_real` 是 PARMA 驱动的 reference balloon profile；没有用户实测轨迹时不能写成真实实测飞行。
- `activation_inventory_parentfed` 已有 parent-fed schema，但缺少审计 branch-ratio 数据，当前 parent feed 未真正改变活度。
- `mixed_voxel_transport` 是 gate，不是完成的 Cosima transport。
- `likelihood_profiled` 是 nuisance degradation proxy，不是完整 Poisson profile optimizer。

## 主要产物

- `CURRENT_AUTHORITIES.md`
- `environment_grid_real/environment_grid_summary.json`
- `prompt_reweight_real/prompt_reweight_real_summary.json`
- `activation_inventory_parentfed/inventory_parentfed_summary.json`
- `delayed_sources_real_profile/source_build_summary.json`
- `mixed_voxel_transport/radial_vs_mixed_summary.json`
- `event_catalog_v2_measured/catalog_v2_summary.json`
- `timing_daq/timing_daq_model_summary.json`
- `activation_511_truth/activation_511_truth_table.csv`
- `likelihood_profiled/asimov_profiled_sensitivity.csv`
- `long_timeline_injection_profiled/source_injection_profiled_summary.csv`
"""
    (OUT / "phase2_real_flight_report.md").write_text(md, encoding="utf-8")
    font = setup_fonts()
    pdf_path = OUT / "phase2_real_flight_report.pdf"
    with PdfPages(pdf_path) as pdf:
        add_text_page(pdf, "Phase 2 Summary", md, font)
        for title, path, cap in [
            ("PARMA Particle Scale", FIG / "phase2_particle_scale_by_day.png", "Official EXPACS/PARMA C++ driver scales for the reference 33-43 km balloon profile."),
            ("Science Transmission", FIG / "phase2_science_transmission.png", "511 keV atmospheric transmission plus Earth-occultation visibility proxy."),
            ("Prompt Rate Curve", FIG / "phase2_prompt_rate_day_curve.png", "Prompt final rates after PARMA particle-scale reweighting."),
            ("Activation Activity", FIG / "phase2_top_nuclide_activity_vs_day.png", "Top activation activities under the Phase-2 production-scale driver."),
            ("Timing/DAQ", FIG / "phase2_science_survival_by_timing_model.png", "Toy hardware timing/DAQ model scan based on WP6 timing rows."),
            ("Profiled Likelihood", FIG / "phase2_profiled_vs_fisher_threshold.png", "Nuisance-degraded profiled proxy compared with Fisher baseline."),
            ("Profiled Injection", FIG / "phase2_P3_vs_flux_profiled.png", "Profiled source-injection probability curves."),
            ("IMAGE8 Broad", FIG / "phase2_image8_broad_480_550.png", "IMAGE8-style broad-window component final rates."),
            ("IMAGE8 Line", FIG / "phase2_image8_line_510p3_511p8.png", "IMAGE8-style line-window component final rates."),
        ]:
            add_image_page(pdf, title, path, cap, font)
    return phase2_summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=Path, default=CONFIG / "flight_profile_real.csv")
    args = ap.parse_args()
    ensure_dirs()
    write_default_profile(args.profile)
    write_authorities()
    pieces = {}
    pieces["environment"] = build_environment_grid(args.profile)
    pieces["prompt"] = build_prompt_metadata_and_reweight()
    pieces["activation_inventory"] = integrate_parentfed_inventory()
    pieces["delayed_sources"] = build_real_profile_delayed_sources()
    pieces["mixed_voxel"] = write_mixed_voxel_gate()
    pieces["event_catalog_v2"] = build_event_catalog_v2_summary()
    pieces["timing_daq"] = run_timing_daq_models()
    pieces["activation_truth"] = build_activation_truth_table()
    like, inj = run_profile_likelihood_and_injection()
    pieces["profile_likelihood"] = like
    pieces["profiled_injection"] = inj
    summary = make_report(pieces)
    print(OUT / "phase2_real_flight_report.pdf")
    print(json.dumps({"status": summary["status"], "out": rel(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
