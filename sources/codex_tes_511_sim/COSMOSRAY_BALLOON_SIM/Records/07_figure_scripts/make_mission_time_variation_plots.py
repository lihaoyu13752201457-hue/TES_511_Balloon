#!/usr/bin/env python3
"""Build mission-level time-variation figures for the Records tree."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
ROOT = RECORDS.parent
OUT = RECORDS / "03_mission_time_variation"
MPLCONFIG = HERE / ".mplconfig"
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG))
MPLCONFIG.mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SOURCE_TIME = ROOT / "reports_260516" / "source_time_update"
ENV_GRID = ROOT / "reports2.0" / "02_PHASE2_CORE_MATERIALS" / "environment_grid"
PROMPT_REWEIGHT = ROOT / "reports2.0" / "02_PHASE2_CORE_MATERIALS" / "prompt_reweight"
ENV_SUMMARY = ENV_GRID / "environment_grid_summary.json"
INVENTORY_DAY15 = ROOT / "reports" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
DELAYED_NUCLIDE_TEMPLATE = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "delayed_511_by_nuclide_volume.csv"
DELAYED_NUCLIDE_SPECTRUM = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "delayed_511_energy_spectrum_by_top_nuclides.png"

PARTICLE_ORDER = ["gamma", "n", "p", "alpha", "eminus", "eplus", "muminus", "muplus"]
PARTICLE_LABEL = {
    "gamma": "gamma",
    "n": "neutron",
    "p": "proton",
    "alpha": "alpha",
    "eminus": "e-",
    "eplus": "e+",
    "muminus": "mu-",
    "muplus": "mu+",
}
COLORS = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2"]
REFERENCE_ACTIVITY_DAY = 15.0
SECONDS_PER_DAY = 86400.0


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row: dict[str, str], key: str) -> float:
    val = row.get(key, "")
    return float(val) if val != "" else float("nan")


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def half_life_label(seconds: float) -> str:
    if seconds < 3600.0:
        return f"{seconds / 60.0:.1f} min"
    if seconds < SECONDS_PER_DAY:
        return f"{seconds / 3600.0:.1f} h"
    if seconds < 365.25 * SECONDS_PER_DAY:
        return f"{seconds / SECONDS_PER_DAY:.1f} d"
    return f"{seconds / (365.25 * SECONDS_PER_DAY):.1f} yr"


def parma_cpp_dir() -> Path:
    candidates = [
        ROOT.parent / "cosmosray_bg_260516" / "external" / "expacs_parma" / "parma_cpp",
        ROOT.parent / "cosmosray_bg_2605" / "external" / "expacs_parma" / "parma_cpp",
        ROOT / "external" / "expacs_parma" / "parma_cpp",
    ]
    for candidate in candidates:
        if (candidate / "subroutines.cpp").exists():
            return candidate
    raise FileNotFoundError("EXPACS/PARMA parma_cpp/subroutines.cpp was not found")


def parma_driver() -> tuple[Path, Path]:
    cpp_dir = parma_cpp_dir()
    candidates = [
        cpp_dir.parent / "phase2_parma_grid_driver",
        Path("/tmp/cosmosray_phase2_parma_grid_driver"),
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate, cpp_dir

    driver_src = ROOT / "tools" / "phase2_parma_grid_driver.cpp"
    if not driver_src.exists():
        raise FileNotFoundError(driver_src)
    out = Path("/tmp/cosmosray_phase2_parma_grid_driver")
    subprocess.run(
        [
            "g++",
            str(driver_src),
            str(cpp_dir / "subroutines.cpp"),
            "-O2",
            "-std=c++11",
            "-o",
            str(out),
        ],
        check=True,
        cwd=str(ROOT),
    )
    return out, cpp_dir


def run_expacs_spectrum(profile_row: dict[str, str], date: tuple[int, int, int]) -> list[dict[str, object]]:
    exe, cwd = parma_driver()
    year, month, day = date
    cmd = [
        str(exe),
        str(year),
        str(month),
        str(day),
        str(as_float(profile_row, "latitude_deg")),
        str(as_float(profile_row, "longitude_deg")),
        str(as_float(profile_row, "altitude_km")),
        "10.0",
    ]
    proc = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, cwd=str(cwd))
    by_key: dict[tuple[str, int], float] = defaultdict(float)
    meta = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        if line.startswith("META,"):
            _, solar, rc, depth = line.split(",")
            meta = {"solar_modulation_W": float(solar), "Rc_GV_driver": float(rc), "depth_g_cm2_driver": float(depth)}
            continue
        if line.startswith("particle,"):
            continue
        particle, angle_bin, mu_mid, theta_mid, energy_bin, energy, _, diff = line.split(",")
        energy_bin_i = int(energy_bin)
        # The driver samples 20 equal-width mu bins from -0.95 to 0.95.
        # Integrate the differential angular flux over full azimuth and dmu=0.1.
        by_key[(particle, energy_bin_i)] += float(diff) * 2.0 * math.pi * 0.1
    rows = []
    for (particle, energy_bin), flux in sorted(by_key.items()):
        rows.append(
            {
                "time_bin_id": int(profile_row["time_bin_id"]),
                "day_mid": as_float(profile_row, "day_mid"),
                "altitude_km": as_float(profile_row, "altitude_km"),
                "latitude_deg": as_float(profile_row, "latitude_deg"),
                "longitude_deg": as_float(profile_row, "longitude_deg"),
                "particle": particle,
                "energy_bin": energy_bin,
                "energy_MeV": energy_for_bin(energy_bin),
                "fullsphere_flux_cm2_s_MeV": flux,
                **meta,
            }
        )
    return rows


def energy_for_bin(energy_bin: int) -> float:
    e_min, e_max, n_energy = 1.0e-2, 1.0e4, 64
    frac = energy_bin / (n_energy - 1)
    return math.exp(math.log(e_min) + frac * (math.log(e_max) - math.log(e_min)))


def nearest_rows_by_day(profile: list[dict[str, str]], days: list[float]) -> list[dict[str, str]]:
    selected = []
    for target in days:
        selected.append(min(profile, key=lambda row: abs(as_float(row, "day_mid") - target)))
    seen = set()
    unique = []
    for row in selected:
        key = row["time_bin_id"]
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def plot_expacs_particle_scale(particle_scale: list[dict[str, str]], prompt_rates: list[dict[str, str]]) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.6), sharex=True, constrained_layout=True)
    ax = axes[0]
    for particle in PARTICLE_ORDER:
        rows = [r for r in particle_scale if r["particle"] == particle]
        if not rows:
            continue
        ax.plot([as_float(r, "day_mid") for r in rows], [as_float(r, "scale") for r in rows], lw=1.4, label=PARTICLE_LABEL[particle])
    ax.axhline(1.0, color="#64748b", lw=0.9, ls="--")
    ax.set_ylabel("EXPACS/PARMA scale to day-0 reference")
    ax.set_title("Instant atmospheric cosmic-ray driver from EXPACS/PARMA")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=4, fontsize=8)

    ax = axes[1]
    for window, label, color in [
        ("broad_480_550", "480-550 keV prompt final", "#2563eb"),
        ("line_510p3_511p8", "510.3-511.8 keV prompt final", "#dc2626"),
    ]:
        rows = [r for r in prompt_rates if r["window"] == window]
        by_day: dict[float, float] = defaultdict(float)
        for r in rows:
            by_day[as_float(r, "day_mid")] += as_float(r, "final_cps")
        xs = sorted(by_day)
        ax.plot(xs, [by_day[x] for x in xs], label=label, lw=1.5, color=color)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("prompt final rate (cps)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    path = OUT / "01_expacs_particle_scale_by_time.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def plot_expacs_spectra(spectra: list[dict[str, object]]) -> str:
    days = sorted({float(r["day_mid"]) for r in spectra})
    fig, axes = plt.subplots(2, 4, figsize=(15.5, 7.8), sharex=True, constrained_layout=True)
    axes = list(axes.flat)
    for ax, particle in zip(axes, PARTICLE_ORDER):
        for idx, day in enumerate(days):
            rows = [r for r in spectra if r["particle"] == particle and abs(float(r["day_mid"]) - day) < 1.0e-9]
            rows.sort(key=lambda r: int(r["energy_bin"]))
            xs = [float(r["energy_MeV"]) for r in rows]
            ys = [float(r["fullsphere_flux_cm2_s_MeV"]) for r in rows]
            ax.loglog(xs, ys, lw=1.2, color=COLORS[idx % len(COLORS)], label=f"day {day:g}")
        ax.set_title(PARTICLE_LABEL[particle])
        ax.grid(True, which="both", alpha=0.18)
        ax.set_xlabel("Energy (MeV)")
        ax.set_ylabel("dPhi/dE (cm-2 s-1 MeV-1)")
    axes[0].legend(fontsize=8)
    fig.suptitle("EXPACS/PARMA full-sphere instant spectra at representative flight times", fontsize=14)
    path = OUT / "02_expacs_instant_spectra_selected_times.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def plot_activation(background: list[dict[str, str]], driver: list[dict[str, str]]) -> str:
    broad = [r for r in background if r["window"] == "broad_480_550"]
    line = [r for r in background if r["window"] == "line_510p3_511p8"]
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 9.2), sharex=True, constrained_layout=True)
    axes[0].plot([as_float(r, "day_mid") for r in driver], [as_float(r, "activation_driver") for r in driver], color="#7c3aed", lw=1.5)
    axes[0].set_ylabel("activation driver")
    axes[0].set_title("Activation source history and delayed-decay background yield")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot([as_float(r, "day_mid") for r in driver], [as_float(r, "total_delayed_activity_Bq") for r in driver], color="#059669", lw=1.5)
    axes[1].set_ylabel("total delayed activity (Bq)")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot([as_float(r, "day_mid") for r in broad], [as_float(r, "delayed_final_cps_level1") for r in broad], label="480-550 keV delayed final", color="#2563eb", lw=1.5)
    axes[2].plot([as_float(r, "day_mid") for r in line], [as_float(r, "delayed_final_cps_level1") for r in line], label="510.3-511.8 keV delayed final", color="#dc2626", lw=1.5)
    axes[2].set_xlabel("Flight day")
    axes[2].set_ylabel("delayed final rate (cps)")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=8)
    path = OUT / "03_activation_decay_background_yield.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def load_inventory_by_za() -> dict[str, dict[str, object]]:
    rows = read_csv(INVENTORY_DAY15)
    if not rows:
        raise RuntimeError(f"empty inventory: {INVENTORY_DAY15}")
    if "Activity_Bq_after_fix" in rows[0]:
        activity_key = "Activity_Bq_after_fix"
    elif "Activity_Bq" in rows[0]:
        activity_key = "Activity_Bq"
    else:
        raise KeyError("inventory has no Activity_Bq_after_fix or Activity_Bq column")

    by_za: dict[str, dict[str, object]] = {}
    for row in rows:
        za = row.get("ZA", "").strip()
        nuclide = row.get("nuclide", "").strip() or za
        hl_s = safe_float(row.get("hl_s", "0"))
        activity = safe_float(row.get(activity_key, "0"))
        if not za or hl_s <= 0.0 or activity <= 0.0 or not math.isfinite(hl_s):
            continue
        rec = by_za.setdefault(
            za,
            {
                "ZA": za,
                "nuclide": nuclide,
                "hl_s": hl_s,
                "day15_reference_activity_Bq": 0.0,
                "RP_yield": 0.0,
                "Points": 0.0,
                "volumes": set(),
            },
        )
        rec["day15_reference_activity_Bq"] = float(rec["day15_reference_activity_Bq"]) + activity
        rec["RP_yield"] = float(rec["RP_yield"]) + safe_float(row.get("RP_yield", "0"))
        rec["Points"] = float(rec["Points"]) + safe_float(row.get("Points", "0"))
        rec["volumes"].add(row.get("VN", ""))
        # Same ZA entries in the current inventory have the same half-life and
        # excitation state. Keep the first value and let validation catch drift.
    return by_za


def integrate_half_life_inventory(driver: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, object]], dict[str, float]]:
    inventory = load_inventory_by_za()
    driver_rows = sorted(driver, key=lambda row: as_float(row, "day_mid"))
    current_atoms = {za: 0.0 for za in inventory}
    production_ref: dict[str, float] = {}
    decay_const: dict[str, float] = {}
    reference_time_s = REFERENCE_ACTIVITY_DAY * SECONDS_PER_DAY
    for za, rec in inventory.items():
        hl_s = float(rec["hl_s"])
        lam = math.log(2.0) / hl_s
        decay_const[za] = lam
        denom = -math.expm1(-lam * reference_time_s)
        production_ref[za] = float(rec["day15_reference_activity_Bq"]) / max(denom, 1.0e-300)

    rows: list[dict[str, object]] = []
    total_rows: list[dict[str, object]] = []
    for drow in driver_rows:
        dt_s = max(as_float(drow, "dt_s"), 0.0)
        driver_scale = as_float(drow, "activation_driver")
        total_activity = 0.0
        for za, rec in sorted(inventory.items(), key=lambda item: item[1]["nuclide"]):
            lam = decay_const[za]
            if dt_s > 0.0:
                decay = math.exp(-lam * dt_s)
                production = production_ref[za] * driver_scale
                current_atoms[za] = current_atoms[za] * decay + production / lam * (1.0 - decay)
            activity = lam * current_atoms[za]
            total_activity += activity
            rows.append(
                {
                    "time_bin_id": int(float(drow["time_bin_id"])),
                    "day_mid": as_float(drow, "day_mid"),
                    "ZA": za,
                    "nuclide": rec["nuclide"],
                    "hl_s": rec["hl_s"],
                    "half_life_days": float(rec["hl_s"]) / SECONDS_PER_DAY,
                    "day15_reference_activity_Bq": rec["day15_reference_activity_Bq"],
                    "reference_production_atoms_s": production_ref[za],
                    "activation_driver": driver_scale,
                    "activity_Bq_ode": activity,
                    "RP_yield": rec["RP_yield"],
                    "Points": rec["Points"],
                    "source_volumes": ";".join(sorted(v for v in rec["volumes"] if v)),
                }
            )
        total_rows.append(
            {
                "time_bin_id": int(float(drow["time_bin_id"])),
                "day_mid": as_float(drow, "day_mid"),
                "activation_driver": driver_scale,
                "total_activity_Bq_ode": total_activity,
                "source_time_total_delayed_activity_Bq": as_float(drow, "total_delayed_activity_Bq"),
            }
        )

    day15_rows = [r for r in rows if abs(float(r["day_mid"]) - REFERENCE_ACTIVITY_DAY) < 1.0e-9]
    if not day15_rows:
        nearest_day = min({float(r["day_mid"]) for r in rows}, key=lambda x: abs(x - REFERENCE_ACTIVITY_DAY))
        day15_rows = [r for r in rows if abs(float(r["day_mid"]) - nearest_day) < 1.0e-9]
    day15_by_za = {str(r["ZA"]): float(r["activity_Bq_ode"]) for r in day15_rows}
    for row in rows:
        ref = day15_by_za.get(str(row["ZA"]), 0.0)
        row["activity_ratio_to_ode_day15"] = float(row["activity_Bq_ode"]) / ref if ref > 0.0 else 0.0

    write_csv(
        OUT / "activation_half_life_ode_by_za.csv",
        rows,
        [
            "time_bin_id",
            "day_mid",
            "ZA",
            "nuclide",
            "hl_s",
            "half_life_days",
            "day15_reference_activity_Bq",
            "reference_production_atoms_s",
            "activation_driver",
            "activity_Bq_ode",
            "activity_ratio_to_ode_day15",
            "RP_yield",
            "Points",
            "source_volumes",
        ],
    )
    write_csv(
        OUT / "activation_half_life_ode_total.csv",
        total_rows,
        ["time_bin_id", "day_mid", "activation_driver", "total_activity_Bq_ode", "source_time_total_delayed_activity_Bq"],
    )
    return rows, total_rows, inventory, day15_by_za


def plot_half_life_activity(activity_rows: list[dict[str, object]], total_rows: list[dict[str, object]], inventory: dict[str, dict[str, object]]) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.2), sharex=True, constrained_layout=True)
    days = [float(r["day_mid"]) for r in total_rows]
    axes[0].plot(days, [float(r["total_activity_Bq_ode"]) for r in total_rows], color="#059669", lw=1.7, label="per-nuclide ODE sum")
    axes[0].plot(days, [float(r["source_time_total_delayed_activity_Bq"]) for r in total_rows], color="#334155", lw=1.0, ls="--", label="existing source_time total")
    axes[0].set_ylabel("Total activity (Bq)")
    axes[0].set_title("Activation inventory propagated with nuclide half-lives")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    peak_by_za: dict[str, float] = defaultdict(float)
    by_za_day: dict[str, dict[float, float]] = defaultdict(dict)
    for row in activity_rows:
        za = str(row["ZA"])
        day = float(row["day_mid"])
        activity = float(row["activity_Bq_ode"])
        by_za_day[za][day] = activity
        peak_by_za[za] = max(peak_by_za[za], activity)
    top_zas = [za for za, _ in sorted(peak_by_za.items(), key=lambda item: item[1], reverse=True)[:9]]
    for za in top_zas:
        rec = inventory[za]
        label = f"{rec['nuclide']} ({half_life_label(float(rec['hl_s']))})"
        axes[1].plot(days, [by_za_day[za].get(day, 0.0) for day in days], lw=1.45, label=label)
    axes[1].set_xlabel("Flight day")
    axes[1].set_ylabel("Activity by nuclide (Bq)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=7, ncol=3)
    path = OUT / "07_activation_half_life_top_nuclides.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def load_delayed_template_by_za() -> dict[str, dict[str, object]]:
    rows = read_csv(DELAYED_NUCLIDE_TEMPLATE)
    by_za: dict[str, dict[str, object]] = {}
    for row in rows:
        za = row.get("ZA", "").strip()
        if not za:
            continue
        rec = by_za.setdefault(
            za,
            {
                "ZA": za,
                "nuclide": row.get("nuclide", za),
                "template_activity_Bq": 0.0,
                "broad_480_550_final_cps_day15_template": 0.0,
                "line_510p3_511p8_final_cps_day15_template": 0.0,
                "near_506_516_final_cps_day15_template": 0.0,
            },
        )
        rec["template_activity_Bq"] = max(float(rec["template_activity_Bq"]), safe_float(row.get("activity_Bq_total_by_ZA", "0")))
        for window in ("broad_480_550", "line_510p3_511p8", "near_506_516"):
            key = f"{window}_final_cps_day15_template"
            rec[key] = float(rec[key]) + safe_float(row.get(f"{window}_final_cps", "0"))
    return by_za


def scale_delayed_template_rates(activity_rows: list[dict[str, object]], day15_by_za: dict[str, float]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    template = load_delayed_template_by_za()
    out_rows: list[dict[str, object]] = []
    for row in activity_rows:
        za = str(row["ZA"])
        if za not in template:
            continue
        ref = day15_by_za.get(za, 0.0)
        if ref <= 0.0:
            continue
        ratio = float(row["activity_Bq_ode"]) / ref
        trec = template[za]
        out_rows.append(
            {
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "ZA": za,
                "nuclide": trec["nuclide"],
                "activity_Bq_ode": row["activity_Bq_ode"],
                "activity_ratio_to_ode_day15": ratio,
                "template_activity_Bq": trec["template_activity_Bq"],
                "broad_480_550_final_cps_template_scaled": float(trec["broad_480_550_final_cps_day15_template"]) * ratio,
                "line_510p3_511p8_final_cps_template_scaled": float(trec["line_510p3_511p8_final_cps_day15_template"]) * ratio,
                "near_506_516_final_cps_template_scaled": float(trec["near_506_516_final_cps_day15_template"]) * ratio,
                "broad_480_550_final_cps_day15_template": trec["broad_480_550_final_cps_day15_template"],
                "line_510p3_511p8_final_cps_day15_template": trec["line_510p3_511p8_final_cps_day15_template"],
            }
        )
    write_csv(
        OUT / "activation_half_life_delayed_rate_templates.csv",
        out_rows,
        [
            "time_bin_id",
            "day_mid",
            "ZA",
            "nuclide",
            "activity_Bq_ode",
            "activity_ratio_to_ode_day15",
            "template_activity_Bq",
            "broad_480_550_final_cps_template_scaled",
            "line_510p3_511p8_final_cps_template_scaled",
            "near_506_516_final_cps_template_scaled",
            "broad_480_550_final_cps_day15_template",
            "line_510p3_511p8_final_cps_day15_template",
        ],
    )
    return out_rows, template


def plot_delayed_template_rates(rate_rows: list[dict[str, object]], inventory: dict[str, dict[str, object]]) -> str:
    days = sorted({float(r["day_mid"]) for r in rate_rows})
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.4), sharex=True, constrained_layout=True)
    for ax, key, title in [
        (axes[0], "broad_480_550_final_cps_template_scaled", "480-550 keV delayed final-rate templates"),
        (axes[1], "line_510p3_511p8_final_cps_template_scaled", "510.3-511.8 keV delayed final-rate templates"),
    ]:
        by_za_day: dict[str, dict[float, float]] = defaultdict(dict)
        peak_by_za: dict[str, float] = defaultdict(float)
        total_by_day: dict[float, float] = defaultdict(float)
        names: dict[str, str] = {}
        for row in rate_rows:
            za = str(row["ZA"])
            day = float(row["day_mid"])
            value = float(row[key])
            by_za_day[za][day] = value
            total_by_day[day] += value
            peak_by_za[za] = max(peak_by_za[za], value)
            names[za] = str(row["nuclide"])
        top_zas = [za for za, _ in sorted(peak_by_za.items(), key=lambda item: item[1], reverse=True)[:7]]
        series = []
        labels = []
        for za in top_zas:
            series.append([by_za_day[za].get(day, 0.0) for day in days])
            hl = half_life_label(float(inventory[za]["hl_s"])) if za in inventory else ""
            labels.append(f"{names[za]} {hl}")
        other = []
        for idx, day in enumerate(days):
            top_sum = sum(values[idx] for values in series)
            other.append(max(total_by_day[day] - top_sum, 0.0))
        if any(v > 0.0 for v in other):
            series.append(other)
            labels.append("other")
        ax.stackplot(days, *series, labels=labels, alpha=0.88)
        ax.plot(days, [total_by_day[day] for day in days], color="#0f172a", lw=1.1, label="total")
        ax.set_ylabel("Final delayed rate (cps)")
        ax.set_title(title)
        ax.grid(True, alpha=0.22)
        ax.legend(fontsize=7, ncol=4, loc="upper left")
    axes[1].set_xlabel("Flight day")
    path = OUT / "08_delayed_nuclide_rate_templates_half_life_scaled.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def copy_day15_delayed_spectrum() -> str:
    if not DELAYED_NUCLIDE_SPECTRUM.exists():
        raise FileNotFoundError(DELAYED_NUCLIDE_SPECTRUM)
    path = OUT / "09_day15_delayed_511_energy_spectrum_by_top_nuclides.png"
    shutil.copyfile(DELAYED_NUCLIDE_SPECTRUM, path)
    return path.name


def plot_transmission(atm: list[dict[str, str]]) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), constrained_layout=True)
    ax = axes[0]
    ax.plot([as_float(r, "day_mid") for r in atm], [as_float(r, "T_atm_511") for r in atm], color="#2563eb", lw=1.5)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("T_atm(511 keV)")
    ax.set_title("511 keV atmospheric transmission over flight profile")
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    sc = ax.scatter(
        [as_float(r, "altitude_km") for r in atm],
        [as_float(r, "T_atm_511") for r in atm],
        c=[as_float(r, "source_zenith_deg") for r in atm],
        s=34,
        cmap="viridis",
        edgecolors="black",
        linewidths=0.2,
    )
    ax.set_xlabel("Altitude (km)")
    ax.set_ylabel("T_atm(511 keV)")
    ax.set_title("Transmission depends on altitude and zenith path")
    ax.grid(True, alpha=0.25)
    fig.colorbar(sc, ax=ax, label="source zenith (deg)")
    path = OUT / "04_511_atmospheric_transmission_vs_altitude.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def plot_altitude(profile: list[dict[str, str]]) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True, constrained_layout=True)
    axes[0].plot([as_float(r, "day_mid") for r in profile], [as_float(r, "altitude_km") for r in profile], color="#2563eb", lw=1.5)
    axes[0].set_ylabel("Altitude (km)")
    axes[0].set_title("Balloon altitude and atmospheric depth profile")
    axes[0].grid(True, alpha=0.25)
    axes[1].plot([as_float(r, "day_mid") for r in profile], [as_float(r, "depth_g_cm2") for r in profile], color="#dc2626", lw=1.5)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Flight day")
    axes[1].set_ylabel("Vertical depth (g cm-2)")
    axes[1].grid(True, alpha=0.25)
    path = OUT / "05_balloon_altitude_depth_vs_time.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def plot_lat_lon(profile: list[dict[str, str]]) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), constrained_layout=True)
    ax = axes[0]
    sc = ax.scatter(
        [as_float(r, "longitude_deg") for r in profile],
        [as_float(r, "latitude_deg") for r in profile],
        c=[as_float(r, "day_mid") for r in profile],
        s=34,
        cmap="plasma",
        edgecolors="black",
        linewidths=0.2,
    )
    ax.plot([as_float(r, "longitude_deg") for r in profile], [as_float(r, "latitude_deg") for r in profile], color="#475569", lw=0.7, alpha=0.55)
    ax.set_xlabel("Longitude (deg)")
    ax.set_ylabel("Latitude (deg)")
    ax.set_title("Balloon latitude-longitude track")
    ax.grid(True, alpha=0.25)
    fig.colorbar(sc, ax=ax, label="Flight day")

    ax = axes[1]
    ax.plot([as_float(r, "day_mid") for r in profile], [as_float(r, "Rc_GV") for r in profile], color="#059669", lw=1.5)
    ax.set_xlabel("Flight day")
    ax.set_ylabel("Geomagnetic cutoff Rc (GV)")
    ax.set_title("Position-dependent cutoff proxy")
    ax.grid(True, alpha=0.25)
    path = OUT / "06_balloon_lat_lon_cutoff_track.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path.name


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    profile = read_csv(SOURCE_TIME / "trajectory_profile.csv")
    driver = read_csv(SOURCE_TIME / "time_dependent_driver_grid.csv")
    background = read_csv(SOURCE_TIME / "background_time_variation.csv")
    particle_scale = read_csv(ENV_GRID / "particle_scale_by_time.csv")
    atm = read_csv(ENV_GRID / "science_atmospheric_transmission.csv")
    prompt_rates = read_csv(PROMPT_REWEIGHT / "prompt_rate_by_time_particle.csv")

    env_summary = load_json(ENV_SUMMARY)
    ref = env_summary["reference_condition"]
    date = (int(ref["year"]), int(ref["month"]), int(ref["day"]))
    selected_profile = nearest_rows_by_day(profile, [0.0, 3.0, 10.0, 20.0])
    spectra_rows: list[dict[str, object]] = []
    for row in selected_profile:
        spectra_rows.extend(run_expacs_spectrum(row, date))
    write_csv(
        OUT / "expacs_selected_time_spectra.csv",
        spectra_rows,
        [
            "time_bin_id",
            "day_mid",
            "altitude_km",
            "latitude_deg",
            "longitude_deg",
            "particle",
            "energy_bin",
            "energy_MeV",
            "fullsphere_flux_cm2_s_MeV",
            "solar_modulation_W",
            "Rc_GV_driver",
            "depth_g_cm2_driver",
        ],
    )

    activity_rows, activity_total_rows, activity_inventory, day15_by_za = integrate_half_life_inventory(driver)
    template_rate_rows, delayed_template = scale_delayed_template_rates(activity_rows, day15_by_za)

    outputs = [
        plot_expacs_particle_scale(particle_scale, prompt_rates),
        plot_expacs_spectra(spectra_rows),
        plot_activation(background, driver),
        plot_half_life_activity(activity_rows, activity_total_rows, activity_inventory),
        plot_delayed_template_rates(template_rate_rows, activity_inventory),
        copy_day15_delayed_spectrum(),
        plot_transmission(atm),
        plot_altitude(profile),
        plot_lat_lon(profile),
    ]
    ode_total_by_day = {float(r["day_mid"]): float(r["total_activity_Bq_ode"]) for r in activity_total_rows}
    source_total_by_day = {float(r["day_mid"]): float(r["source_time_total_delayed_activity_Bq"]) for r in activity_total_rows}
    max_activity_abs_delta = max(abs(ode_total_by_day[d] - source_total_by_day[d]) for d in ode_total_by_day)
    max_activity_rel_delta = max(
        abs(ode_total_by_day[d] - source_total_by_day[d]) / source_total_by_day[d]
        for d in ode_total_by_day
        if source_total_by_day[d] > 0.0
    )
    template_totals_broad = defaultdict(float)
    template_totals_line = defaultdict(float)
    for row in template_rate_rows:
        template_totals_broad[float(row["day_mid"])] += float(row["broad_480_550_final_cps_template_scaled"])
        template_totals_line[float(row["day_mid"])] += float(row["line_510p3_511p8_final_cps_template_scaled"])
    summary = {
        "status": "PASS",
        "source": {
            "trajectory_profile": str(SOURCE_TIME / "trajectory_profile.csv"),
            "driver_grid": str(SOURCE_TIME / "time_dependent_driver_grid.csv"),
            "background_time_variation": str(SOURCE_TIME / "background_time_variation.csv"),
            "particle_scale_by_time": str(ENV_GRID / "particle_scale_by_time.csv"),
            "science_atmospheric_transmission": str(ENV_GRID / "science_atmospheric_transmission.csv"),
            "prompt_rate_by_time_particle": str(PROMPT_REWEIGHT / "prompt_rate_by_time_particle.csv"),
            "day15_activation_inventory": str(INVENTORY_DAY15),
            "delayed_nuclide_response_template": str(DELAYED_NUCLIDE_TEMPLATE),
            "day15_delayed_nuclide_spectrum": str(DELAYED_NUCLIDE_SPECTRUM),
            "expacs_parma_driver": str(parma_driver()[0]),
            "expacs_reference_date": f"{date[0]:04d}-{date[1]:02d}-{date[2]:02d}",
        },
        "outputs": outputs
        + [
            "expacs_selected_time_spectra.csv",
            "activation_half_life_ode_by_za.csv",
            "activation_half_life_ode_total.csv",
            "activation_half_life_delayed_rate_templates.csv",
        ],
        "profile": {
            "n_time_bins": len(profile),
            "day_min": min(as_float(r, "day_mid") for r in profile),
            "day_max": max(as_float(r, "day_mid") for r in profile),
            "altitude_km_min": min(as_float(r, "altitude_km") for r in profile),
            "altitude_km_max": max(as_float(r, "altitude_km") for r in profile),
            "latitude_deg_min": min(as_float(r, "latitude_deg") for r in profile),
            "latitude_deg_max": max(as_float(r, "latitude_deg") for r in profile),
            "longitude_deg_min": min(as_float(r, "longitude_deg") for r in profile),
            "longitude_deg_max": max(as_float(r, "longitude_deg") for r in profile),
            "T_atm_511_min": min(as_float(r, "T_atm_511") for r in atm),
            "T_atm_511_max": max(as_float(r, "T_atm_511") for r in atm),
            "total_delayed_activity_Bq_max": max(as_float(r, "total_delayed_activity_Bq") for r in driver),
        },
        "activation_half_life_ode": {
            "mode": "direct_production_per_ZA_ODE_from_day15_inventory_and_activation_driver",
            "reference_day": REFERENCE_ACTIVITY_DAY,
            "n_inventory_za": len(activity_inventory),
            "n_template_za": len(delayed_template),
            "n_matched_inventory_template_za": len({str(r["ZA"]) for r in template_rate_rows}),
            "n_time_rate_rows": len(template_rate_rows),
            "max_total_activity_abs_delta_vs_existing_source_time_Bq": max_activity_abs_delta,
            "max_total_activity_rel_delta_vs_existing_source_time": max_activity_rel_delta,
            "template_broad_final_cps_max": max(template_totals_broad.values()) if template_totals_broad else 0.0,
            "template_line_final_cps_max": max(template_totals_line.values()) if template_totals_line else 0.0,
            "caveat": "Per-nuclide half-life ODE is active for direct production; delayed-rate plots reuse day-15 DELAY response templates with fixed spatial transport. Parent-fed branch-ratio chains and new per-bin DELAY transport are not included.",
        },
    }
    (OUT / "mission_time_variation_plot_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
