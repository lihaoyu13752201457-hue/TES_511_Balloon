#!/usr/bin/env python3
"""Build and analyze the geo-opt atmospheric 511-keV 4pi sidecar replay."""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708"
RUN_NAME = "Atm511SidecarS1Nominal3M_GeoOptS1BpeW5"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
GEOMETRY_SETUP = (
    ROOT
    / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
MANIFEST = ROOT / "expacs_fullsphere_20bin_sources/manifest.csv"
TRAJECTORY = (
    ROOT
    / "stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1"
    / "trajectory_profile.csv"
)
STEP06_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1"
    / "step06_geo_opt_s1_bpe_w5_fullstat_v1_summary.json"
)
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1"
    / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json"
)
STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1"
    / "step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json"
)
STEP09_BRIDGE = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)

X_REF_G_CM2 = 3.6
LAMBDA_511_G_CM2 = 11.5
ALBEDO_A = 1.7
ACTIVE_VETO_THRESHOLD_KEV = 50.0

SCENARIOS = [
    {"run": "S0", "phi_ref": 0.0, "eta": None, "r0": None, "description": "no ATM511 control"},
    {"run": "S1", "phi_ref": 0.10, "eta": 0.8, "r0": 0.20, "description": "nominal"},
    {"run": "S2", "phi_ref": 0.03, "eta": 0.5, "r0": 0.05, "description": "conservative low"},
    {"run": "S3", "phi_ref": 0.20, "eta": 1.0, "r0": 0.50, "description": "conservative high"},
    {"run": "S4", "phi_ref": 0.10, "eta": 0.8, "r0": 0.00, "description": "albedo-only comparison"},
    {"run": "S5", "phi_ref": 0.60, "eta": 0.8, "r0": 0.20, "description": "low-cutoff/high-latitude stress only"},
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    fields = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_step05_module():
    spec = importlib.util.spec_from_file_location("geo_opt_atm511_sidecar_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.STEP09_SUMMARY = STEP09_BRIDGE
    return mod


def f_R_harris(rc_gv: float) -> float:
    if rc_gv < 7.0:
        return 1.000
    if rc_gv < 9.0:
        return 0.805
    if rc_gv < 11.0:
        return 0.624
    if rc_gv < 13.0:
        return 0.532
    return 0.479


def g_depth(depth_g_cm2: float, eta: float) -> float:
    return (depth_g_cm2 / X_REF_G_CM2) ** eta


def load_manifest_bins() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    env: dict[str, Any] = {}
    seen: set[int] = set()
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("particle") != "gamma":
                continue
            bin_id = int(row["bin_id"])
            if bin_id in seen:
                continue
            seen.add(bin_id)
            rows.append(
                {
                    "bin_id": bin_id,
                    "direction_tag": row["direction_tag"],
                    "theta_min_deg": float(row["theta_min_deg"]),
                    "theta_max_deg": float(row["theta_max_deg"]),
                    "theta_mid_deg": float(row["theta_mid_deg"]),
                    "mu_high": float(row["mu_high"]),
                    "mu_low": float(row["mu_low"]),
                    "delta_omega_sr": float(row["delta_omega_sr"]),
                }
            )
            if not env:
                env = {
                    "static_manifest_lat_deg": float(row["expacs_lat_deg"]),
                    "static_manifest_lon_deg": float(row["expacs_lon_deg"]),
                    "static_manifest_altitude_km": float(row["expacs_altitude_km"]),
                    "static_manifest_Rc_GV": float(row["expacs_Rc_GV"]),
                    "static_manifest_date_or_W": row["W_or_date"],
                }
    rows.sort(key=lambda item: int(item["bin_id"]))
    if len(rows) != 20:
        raise RuntimeError(f"expected 20 gamma bins in {MANIFEST}, found {len(rows)}")
    return rows, env


def load_day15_environment() -> dict[str, Any]:
    summary = load_json(STEP06_SUMMARY)
    day15_index = int(summary.get("mission_axis", summary.get("activity", {}))["day15_index"])
    with TRAJECTORY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["time_bin_id"]) == day15_index:
                return {
                    "environment_source": "geo-opt Step06 day-15 trajectory proxy",
                    "time_bin_id": int(row["time_bin_id"]),
                    "day_mid": float(row["day_mid"]),
                    "latitude_deg": float(row["latitude_deg"]),
                    "longitude_deg": float(row["longitude_deg"]),
                    "altitude_km": float(row["altitude_km"]),
                    "Rc_GV": float(row["Rc_GV"]),
                    "depth_g_cm2": float(row["depth_g_cm2"]),
                    "T_atm_511": float(row["T_atm_511"]),
                }
    raise RuntimeError(f"day15 index {day15_index} not found in {TRAJECTORY}")


def down_kernel(mu: float, depth_g_cm2: float) -> float:
    if mu <= 0.0:
        return 1.0
    return 1.0 - math.exp(-depth_g_cm2 / (LAMBDA_511_G_CM2 * mu))


def integrate_midpoint(func: Any, lo: float, hi: float, steps: int) -> float:
    if hi <= lo:
        return 0.0
    width = (hi - lo) / steps
    total = 0.0
    for i in range(steps):
        total += func(lo + (i + 0.5) * width)
    return total * width


def model_fluxes(env: dict[str, Any], phi_ref: float, eta: float | None, r0: float | None) -> dict[str, Any]:
    if phi_ref == 0.0:
        return {
            "phi_ref_ph_cm2_s": 0.0,
            "f_R": f_R_harris(float(env["Rc_GV"])),
            "g_X": 0.0,
            "f_solar": 1.0,
            "phi_4pi_ph_cm2_s": 0.0,
            "r_down": 0.0,
            "phi_up_ph_cm2_s": 0.0,
            "phi_down_ph_cm2_s": 0.0,
        }
    assert eta is not None
    assert r0 is not None
    depth = float(env["depth_g_cm2"])
    f_r = f_R_harris(float(env["Rc_GV"]))
    g_x = g_depth(depth, float(eta))
    phi_4pi = float(phi_ref) * f_r * g_x
    r_down = min(1.0, float(r0) * (depth / X_REF_G_CM2) ** 0.5)
    phi_up = phi_4pi / (1.0 + r_down)
    phi_down = r_down * phi_4pi / (1.0 + r_down)
    return {
        "phi_ref_ph_cm2_s": float(phi_ref),
        "f_R": float(f_r),
        "g_X": float(g_x),
        "f_solar": 1.0,
        "phi_4pi_ph_cm2_s": float(phi_4pi),
        "r_down": float(r_down),
        "phi_up_ph_cm2_s": float(phi_up),
        "phi_down_ph_cm2_s": float(phi_down),
    }


def bin_fluxes(bins: list[dict[str, Any]], env: dict[str, Any], flux_model: dict[str, Any]) -> list[dict[str, Any]]:
    depth = float(env["depth_g_cm2"])
    phi_up = float(flux_model["phi_up_ph_cm2_s"])
    phi_down = float(flux_model["phi_down_ph_cm2_s"])
    norm_down = integrate_midpoint(lambda mu: down_kernel(mu, depth), 0.0, 1.0, 20000)
    rows: list[dict[str, Any]] = []

    def down_intensity(mu: float) -> float:
        if phi_down == 0.0:
            return 0.0
        return phi_down / (2.0 * math.pi * norm_down) * down_kernel(mu, depth)

    def up_intensity(mu_u: float) -> float:
        if phi_up == 0.0:
            return 0.0
        return phi_up / (2.0 * math.pi * (1.0 + ALBEDO_A / 2.0)) * (1.0 + ALBEDO_A * mu_u)

    for row in bins:
        theta1 = float(row["theta_min_deg"])
        theta2 = float(row["theta_max_deg"])
        flux = 0.0
        component = ""
        if theta1 < 90.0:
            d1 = theta1
            d2 = min(theta2, 90.0)
            mu_lo = max(0.0, math.cos(math.radians(d2)))
            mu_hi = min(1.0, math.cos(math.radians(d1)))
            flux += 2.0 * math.pi * integrate_midpoint(down_intensity, mu_lo, mu_hi, 3000)
            component = "downward_residual_atmosphere"
        if theta2 > 90.0:
            u1 = max(theta1, 90.0)
            u2 = theta2
            mu_lo = max(0.0, -math.cos(math.radians(u1)))
            mu_hi = min(1.0, -math.cos(math.radians(u2)))
            flux += 2.0 * math.pi * integrate_midpoint(up_intensity, mu_lo, mu_hi, 3000)
            component = "upward_earth_albedo" if not component else "split_at_horizon"
        out = dict(row)
        out.update(
            {
                "component": component,
                "source_name": f"Atm511_bin{int(row['bin_id']):02d}_{'down' if theta2 <= 90.0 else 'up'}",
                "flux_ph_cm2_s": float(flux),
                "flux_fraction_of_4pi": float(flux / flux_model["phi_4pi_ph_cm2_s"]) if flux_model["phi_4pi_ph_cm2_s"] else 0.0,
            }
        )
        rows.append(out)
    return rows


def build_source_text(bin_rows: list[dict[str, Any]], env: dict[str, Any], model: dict[str, Any], events: int) -> str:
    lines = [
        "# ATM511 EXPACS-like 4pi sidecar nominal source for geo_opt_s1_bpe_w5, 2026-07-08.",
        "# Separate line-integrated mono-511 component; not an EXPACS continuum keV^-1 point.",
        f"# Environment: lat={env['latitude_deg']:.6f} lon={env['longitude_deg']:.6f} alt={env['altitude_km']:.6f} km Rc={env['Rc_GV']:.6f} GV depth={env['depth_g_cm2']:.12g} g/cm2.",
        f"# Total 4pi flux={model['phi_4pi_ph_cm2_s']:.12e} ph cm^-2 s^-1; up={model['phi_up_ph_cm2_s']:.12e}; down={model['phi_down_ph_cm2_s']:.12e}.",
        "",
        f"Geometry {rel(GEOMETRY_SETUP)}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes false",
        "DetectorTimeConstant 1e-9",
        "Seed 260708",
        "",
        f"Run {RUN_NAME}",
        f"{RUN_NAME}.Events {events}",
        f"{RUN_NAME}.FileName {rel(RUN_DIR / RUN_NAME)}",
        "",
    ]
    for row in bin_rows:
        lines.append(f"{RUN_NAME}.Source {row['source_name']}")
    lines.append("")
    for row in bin_rows:
        lines.extend(
            [
                f"{row['source_name']}.ParticleType 1",
                f"{row['source_name']}.Beam FarFieldAreaSource {row['theta_min_deg']:.6f} {row['theta_max_deg']:.6f} 0.000000 360.000000",
                f"{row['source_name']}.Spectrum Mono 511",
                f"{row['source_name']}.Flux {row['flux_ph_cm2_s']:.12e}",
                "",
            ]
        )
    return "\n".join(lines)


def write_source_and_model(events: int) -> dict[str, Any]:
    bins, static_env = load_manifest_bins()
    env = load_day15_environment()
    env.update(static_env)
    nominal = next(item for item in SCENARIOS if item["run"] == "S1")
    model = model_fluxes(env, nominal["phi_ref"], nominal["eta"], nominal["r0"])
    rows = bin_fluxes(bins, env, model)
    scenario_rows: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        scenario_model = model_fluxes(env, scenario["phi_ref"], scenario["eta"], scenario["r0"])
        scenario_bins = bin_fluxes(bins, env, scenario_model)
        scenario_rows.append(
            {
                "run": scenario["run"],
                "description": scenario["description"],
                "phi_ref_ph_cm2_s": scenario_model["phi_ref_ph_cm2_s"],
                "eta": "" if scenario["eta"] is None else scenario["eta"],
                "r0": "" if scenario["r0"] is None else scenario["r0"],
                "Rc_GV": env["Rc_GV"],
                "depth_g_cm2": env["depth_g_cm2"],
                "f_R": scenario_model["f_R"],
                "g_X": scenario_model["g_X"],
                "phi_4pi_ph_cm2_s": scenario_model["phi_4pi_ph_cm2_s"],
                "phi_up_ph_cm2_s": scenario_model["phi_up_ph_cm2_s"],
                "phi_down_ph_cm2_s": scenario_model["phi_down_ph_cm2_s"],
                "r_down": scenario_model["r_down"],
                "bin_flux_sum_ph_cm2_s": sum(float(row["flux_ph_cm2_s"]) for row in scenario_bins),
            }
        )

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(build_source_text(rows, env, model, events), encoding="utf-8")
    bin_csv = OUT / "atm511_sidecar_s1_nominal_bin_fluxes.csv"
    scenario_csv = OUT / "atm511_sidecar_systematic_scenarios.csv"
    write_csv(bin_csv, rows)
    write_csv(scenario_csv, scenario_rows)
    payload = {
        "status": "SOURCE_BUILT_ATM511_EXPACS_LIKE_4PI_SIDECAR",
        "generated_at_utc": now_utc(),
        "inputs": {
            "sidecar_spec": "engineering/ATM511_EXPACS_LIKE_SIDECAR_MODEL_20260708.md",
            "expacs_manifest": rel(MANIFEST),
            "trajectory_profile": rel(TRAJECTORY),
            "step06_summary": rel(STEP06_SUMMARY),
            "geometry_setup": rel(GEOMETRY_SETUP),
            "source": rel(SOURCE),
            "log": rel(LOG),
            "sim": rel(SIM),
        },
        "environment": env,
        "model": {
            "source_model": "PAPER_IMPLEMENTABLE_SEMI_EMPIRICAL_4PI_ATM511_SIDECAR",
            "scenario": "S1 nominal",
            "phi_ref_ph_cm2_s": model["phi_ref_ph_cm2_s"],
            "X_ref_g_cm2": X_REF_G_CM2,
            "eta": nominal["eta"],
            "r0": nominal["r0"],
            "beta": 0.5,
            "Lambda_511_g_cm2": LAMBDA_511_G_CM2,
            "albedo_limb_darkening_a": ALBEDO_A,
            **model,
        },
        "bin_flux_csv": rel(bin_csv),
        "scenario_csv": rel(scenario_csv),
        "bin_flux_rows": rows,
        "scenario_rows": scenario_rows,
        "flux_closure": {
            "bin_flux_sum_ph_cm2_s": float(sum(float(row["flux_ph_cm2_s"]) for row in rows)),
            "expected_phi_4pi_ph_cm2_s": float(model["phi_4pi_ph_cm2_s"]),
            "absolute_error_ph_cm2_s": float(sum(float(row["flux_ph_cm2_s"]) for row in rows) - model["phi_4pi_ph_cm2_s"]),
        },
        "transport": {"status": "MISSING_SIM_OR_LOG", "events_requested": events},
    }
    write_json(OUT / "atm511_sidecar_source_model_summary.json", payload)
    return payload


def p2_observation_time_s() -> float:
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"cannot locate Observation time in {LOG}")


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    if upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper:
        return True
    return upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")


def parse_catalog() -> dict[str, Any]:
    cc_re = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
    kv_re = re.compile(r"(\w+)=([^\s]+)")
    id_re = re.compile(r"^ID\s+(\d+)")
    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
    cat: dict[str, Any] = {
        "local_id": [],
        "tes_total_keV": [],
        "active_total_keV": [],
        "pix_start": [],
        "pix_count": [],
        "pix_uid": [],
        "pix_layer": [],
        "pix_e": [],
        "pix_x": [],
        "pix_y": [],
        "pix_z": [],
    }
    generated = 0
    kept = 0
    cur_id: int | None = None
    active_total = 0.0
    pix: dict[str, dict[str, float]] = {}

    def flush() -> None:
        nonlocal cur_id, active_total, pix, kept
        if cur_id is None:
            return
        pix_start = len(cat["pix_e"])
        tes_total = 0.0
        for uid, rec in sorted(pix.items()):
            e = float(rec["e"])
            if e <= 0:
                continue
            tes_total += e
            cat["pix_uid"].append(uid)
            cat["pix_layer"].append(int(rec["layer"]))
            cat["pix_e"].append(e)
            cat["pix_x"].append(float(rec["wx"] / e))
            cat["pix_y"].append(float(rec["wy"] / e))
            cat["pix_z"].append(float(rec["wz"] / e))
        pix_count = len(cat["pix_e"]) - pix_start
        if pix_count > 0 or active_total > 0:
            cat["local_id"].append(int(cur_id))
            cat["tes_total_keV"].append(float(tes_total))
            cat["active_total_keV"].append(float(active_total))
            cat["pix_start"].append(int(pix_start))
            cat["pix_count"].append(int(pix_count))
            kept += 1
        cur_id = None
        active_total = 0.0
        pix = {}

    with gzip.open(SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = id_re.match(line)
            if match_id:
                cur_id = int(match_id.group(1))
                generated += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            match_hit = cc_re.match(line)
            if match_hit is None:
                continue
            vol = match_hit.group(1)
            kv = dict(kv_re.findall(match_hit.group(2)))
            try:
                edep = float(kv["edep_keV"])
                x = float(kv["x"])
                y = float(kv["y"])
                z = float(kv["z"])
            except Exception:
                continue
            match_tp = tp_re.match(vol)
            if match_tp:
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": float(match_tp.group("layer"))})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
            elif is_active_veto_volume(vol):
                active_total += edep
    flush()

    for key in ("local_id", "pix_start", "pix_count", "pix_layer"):
        cat[key] = np.asarray(cat[key], dtype=np.int64)
    for key in ("tes_total_keV", "active_total_keV", "pix_e", "pix_x", "pix_y", "pix_z"):
        cat[key] = np.asarray(cat[key], dtype=np.float64)
    cat["pix_uid"] = np.asarray(cat["pix_uid"], dtype=object)
    cat["generated_events"] = generated
    cat["kept_events_tes_or_active"] = kept
    return cat


def event_hits(cat: dict[str, Any], idx: int) -> list[Any]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    hits = []
    for j in range(start, start + count):
        hit = type("Hit", (), {})()
        hit.x = float(cat["pix_x"][j])
        hit.y = float(cat["pix_y"][j])
        hit.z = float(cat["pix_z"][j])
        hit.e = float(cat["pix_e"][j])
        hit.pixel_uid = str(cat["pix_uid"][j])
        hit.layer = int(cat["pix_layer"][j])
        hits.append(hit)
    return hits


def summarize_window(cat: dict[str, Any], step05: Any, emin: float, emax: float, phi_4pi: float) -> dict[str, Any]:
    tes = cat["tes_total_keV"]
    active_energy = cat["active_total_keV"]
    mask = (tes >= emin) & (tes < emax)
    active = mask & (active_energy < ACTIVE_VETO_THRESHOLD_KEV)
    classes: Counter[str] = Counter()
    final_indices: list[int] = []
    disk = step05.side_entry_disk()
    for idx in np.flatnonzero(active):
        keep, cls = step05.side_keep_from_hits(event_hits(cat, int(idx)), disk, "keep")
        classes[cls] += 1
        if keep:
            final_indices.append(int(idx))
    event_weight = 1.0 / float(cat["observation_time_s"])

    def rate(count: int) -> float:
        return float(count * event_weight)

    def transfer(value: float) -> float | None:
        return float(value / phi_4pi) if phi_4pi > 0 else None

    raw_count = int(np.sum(mask))
    active_count = int(np.sum(active))
    final_count = int(len(final_indices))
    raw_rate = rate(raw_count)
    active_rate = rate(active_count)
    final_rate = rate(final_count)
    return {
        "window_keV": [emin, emax],
        "raw_events": raw_count,
        "active_veto_pass_events": active_count,
        "side_compton_fov_pass_events": final_count,
        "raw_rate_cps": raw_rate,
        "active_rate_cps": active_rate,
        "final_rate_cps": final_rate,
        "raw_transfer_cps_per_ph_cm2_s_4pi": transfer(raw_rate),
        "active_transfer_cps_per_ph_cm2_s_4pi": transfer(active_rate),
        "final_transfer_cps_per_ph_cm2_s_4pi": transfer(final_rate),
        "event_rate_weight_cps": event_weight,
        "final_relative_poisson_sigma": float(1.0 / math.sqrt(final_count)) if final_count else None,
        "side_compton_class_counts": dict(sorted(classes.items())),
        "final_event_ids": [int(cat["local_id"][i]) for i in final_indices],
        "final_energies_keV": [float(cat["tes_total_keV"][i]) for i in final_indices],
        "final_active_veto_keV": [float(cat["active_total_keV"][i]) for i in final_indices],
        "final_pix_counts": [int(cat["pix_count"][i]) for i in final_indices],
    }


def sim_header() -> dict[str, Any]:
    header: dict[str, Any] = {}
    with gzip.open(SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry"):
                header["geometry"] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("Seed"):
                header["seed"] = int(line.split()[1])
            elif line == "SE":
                break
    return header


def analyze_transport(source_payload: dict[str, Any]) -> dict[str, Any]:
    step05_mod = load_step05_module()
    step05 = load_json(STEP05_SUMMARY)
    step08 = load_json(STEP08_SUMMARY)
    cat = parse_catalog()
    cat["observation_time_s"] = p2_observation_time_s()
    phi_4pi = float(source_payload["model"]["phi_4pi_ph_cm2_s"])
    w2 = summarize_window(cat, step05_mod, 510.58, 511.42, phi_4pi)
    broad = summarize_window(cat, step05_mod, 480.0, 550.0, phi_4pi)

    b_current = float(step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]["background_cps"])
    f3_current = float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    final_rate = float(w2["final_rate_cps"])
    b_new = b_current + final_rate
    f3_new = f3_current * math.sqrt(b_new / b_current)

    scenario_rows = []
    nominal_transfer = w2["final_transfer_cps_per_ph_cm2_s_4pi"]
    for row in source_payload["scenario_rows"]:
        approx = None if nominal_transfer is None else float(nominal_transfer) * float(row["phi_4pi_ph_cm2_s"])
        scenario_rows.append(
            {
                **row,
                "approx_final_cps_using_s1_nominal_4pi_transfer": approx,
                "approx_background_cps": None if approx is None else b_current + approx,
                "approx_F3_20d_ph_cm2_s": None if approx is None else f3_current * math.sqrt((b_current + approx) / b_current),
                "detector_response_note": "Only S1 nominal angular shape is transported in this replay; non-S1 rows are source-model systematic scales unless separately transported.",
            }
        )
    scenario_csv = OUT / "atm511_sidecar_detector_response_scenarios.csv"
    write_csv(scenario_csv, scenario_rows)

    payload = {
        **source_payload,
        "status": "PASS_GEO_OPT_S1_BPE_W5_ATM511_4PI_SIDECAR_REPLAY",
        "generated_at_utc": now_utc(),
        "sim_header": sim_header(),
        "normalization": {
            "source_total_4pi_flux_ph_cm2_s": phi_4pi,
            "source_upward_flux_ph_cm2_s": source_payload["model"]["phi_up_ph_cm2_s"],
            "source_downward_flux_ph_cm2_s": source_payload["model"]["phi_down_ph_cm2_s"],
            "observation_time_s": float(cat["observation_time_s"]),
            "rate_weight_per_generated_event_s-1": 1.0 / float(cat["observation_time_s"]),
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "rate_units": "cps for physical S1 nominal ATM511 sidecar flux; transfer fields are per total 4pi line flux",
            "active_veto_volume_rule": "CsI/BGO/legacy active tokens plus GeoOpt_S1_PlasticFullWrap* plastic skin.",
        },
        "catalog": {
            "generated_events": int(cat["generated_events"]),
            "kept_events_tes_or_active": int(cat["kept_events_tes_or_active"]),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0)),
            "active_veto_events": int(np.sum(cat["active_total_keV"] > 0)),
        },
        "windows": {"w2_510p58_511p42": w2, "broad_480_550": broad},
        "baseline_without_atm511_sidecar": {
            "geo_opt_step05_w2_background_cps": b_current,
            "geo_opt_step08_w2_F3_20d_ph_cm2_s": f3_current,
        },
        "sidecar_included_nominal": {
            "atm511_added_cps": final_rate,
            "background_new_cps": b_new,
            "background_fractional_increase": final_rate / b_current,
            "F3_20d_new_ph_cm2_s": f3_new,
        },
        "scenario_detector_response_csv": rel(scenario_csv),
        "scenario_rows": scenario_rows,
        "transport": {"status": "PASS_SIM_ANALYZED", "events_requested": source_payload["transport"]["events_requested"]},
        "interpretation": {
            "replacement": "Supersedes the 2026-07-07 lower-hemisphere unit-flux atm511 replay for current geo-opt conclusions.",
            "limitation": "S1 is a 4pi sidecar at the Step06 day-15 environment; scenario rows other than S1 need separate transport to capture angular-shape changes exactly.",
        },
    }
    write_json(OUT / "p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json", payload)
    return payload


def write_readme(payload: dict[str, Any]) -> None:
    model = payload["model"]
    transport = payload.get("transport", {})
    w2 = payload.get("windows", {}).get("w2_510p58_511p42")
    lines = [
        "# Geo-opt S1/BPE/W5 Atmospheric 511 4pi Sidecar Replay",
        "",
        f"Status: `{payload['status']}`",
        "",
        "Scope: EXPACS-like semi-empirical atmospheric e+e- annihilation 511-keV line sidecar for the current geo-opt S1/BPE/W5 geometry. This replaces the 2026-07-07 lower-hemisphere-only atm511 replay in downstream geo-opt conclusions.",
        "",
        "## Source Model",
        "",
        f"- Environment: lat `{payload['environment']['latitude_deg']:.6g}` deg, lon `{payload['environment']['longitude_deg']:.6g}` deg, alt `{payload['environment']['altitude_km']:.6g}` km, Rc `{payload['environment']['Rc_GV']:.6g}` GV, depth `{payload['environment']['depth_g_cm2']:.6g}` g cm^-2.",
        f"- Nominal 4pi line flux: `{model['phi_4pi_ph_cm2_s']:.12g}` ph cm^-2 s^-1.",
        f"- Up/down split: up `{model['phi_up_ph_cm2_s']:.12g}`, down `{model['phi_down_ph_cm2_s']:.12g}`, r_down `{model['r_down']:.6g}`.",
        f"- Flux closure error: `{payload['flux_closure']['absolute_error_ph_cm2_s']:.3e}` ph cm^-2 s^-1.",
        "",
    ]
    if transport.get("status") == "PASS_SIM_ANALYZED" and w2:
        sidecar = payload["sidecar_included_nominal"]
        lines.extend(
            [
                "## Transport Result",
                "",
                f"- Generated events: `{payload['catalog']['generated_events']}`",
                f"- Observation time: `{payload['normalization']['observation_time_s']:.6g} s`",
                f"- W2 raw/active/final events: `{w2['raw_events']}` / `{w2['active_veto_pass_events']}` / `{w2['side_compton_fov_pass_events']}`",
                f"- W2 final nominal atm511 rate: `{w2['final_rate_cps']:.12g}` cps",
                f"- W2 final transfer per 4pi flux: `{w2['final_transfer_cps_per_ph_cm2_s_4pi']:.12g}` cps / (ph cm^-2 s^-1)",
                f"- Sidecar-included W2 background: `{sidecar['background_new_cps']:.12g}` cps",
                f"- Sidecar-included W2 F3(20d): `{sidecar['F3_20d_new_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
                "",
            ]
        )
    else:
        lines.extend(["## Transport Result", "", "- SIM/log are not present yet; source/model products are ready for Cosima.", ""])
    lines.extend(
        [
            "## Files",
            "",
            f"- Source: `{payload['inputs']['source']}`",
            f"- SIM: `{payload['inputs']['sim']}`",
            f"- Summary: `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json`",
            f"- Bin fluxes: `{payload['bin_flux_csv']}`",
            f"- Source scenarios: `{payload['scenario_csv']}`",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=3_000_000)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()

    payload = write_source_and_model(args.events)
    if not args.source_only and SIM.exists() and LOG.exists():
        payload = analyze_transport(payload)
    write_readme(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source": rel(SOURCE),
                "sim_exists": SIM.exists(),
                "log_exists": LOG.exists(),
                "phi_4pi": payload["model"]["phi_4pi_ph_cm2_s"],
                "w2_final_events": payload.get("windows", {}).get("w2_510p58_511p42", {}).get("side_compton_fov_pass_events"),
                "w2_final_cps": payload.get("windows", {}).get("w2_510p58_511p42", {}).get("final_rate_cps"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
