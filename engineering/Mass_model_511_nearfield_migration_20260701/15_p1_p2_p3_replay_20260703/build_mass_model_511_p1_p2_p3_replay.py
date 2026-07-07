#!/usr/bin/env python3
"""Build Mass_model_511-specific P1/P2/P3 replay products."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
MASS_STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
    / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
)
MASS_STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1"
    / "step08_Mass_model_511_fullstat_v1_time_dependent_summary.json"
)
MASS_CATALOG = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/work/event_catalog.pkl"
)
P2_DIR = ROOT / "runs/Mass_model_511_nearfield_migration_20260701/p2_atm511_unit_Mass_model_511_fullstat_v1"
P2_SOURCE = P2_DIR / "Atm511LowerUnit3M_MassModel511.source"
P2_LOG = P2_DIR / "cosima_Atm511LowerUnit3M_MassModel511.log"
P2_SIM = P2_DIR / "Atm511LowerUnit3M_MassModel511.inc1.id1.sim.gz"

W2_CENTER_KEV = 511.0
W2_HALF_KEV = 0.42
W2_WIDTH_KEV = 2.0 * W2_HALF_KEV
DET_SIGMA_KEV = 0.14
REFERENCE_FLUX = 1.0e-4


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
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
    spec = importlib.util.spec_from_file_location("mass_model_511_p123_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.TOOLS = ROOT / "old/code/tools"
    return mod


def side_entry_disk() -> dict[str, Any]:
    center = np.asarray([-12.94005409571382, 0.0, 5.586143571373725], dtype=float)
    normal = np.asarray([0.7071067811865476, 0.0, -0.7071067811865475], dtype=float)
    normal = normal / np.linalg.norm(normal)
    ref = np.asarray([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(normal, ref))) > 0.9:
        ref = np.asarray([0.0, 1.0, 0.0], dtype=float)
    u = np.cross(normal, ref)
    u = u / np.linalg.norm(u)
    v = np.cross(normal, u)
    v = v / np.linalg.norm(v)
    return {"center_cm": center, "normal": normal, "basis_u": u, "basis_v": v, "radius_cm": 1.898}


def gaussian_acceptance(half_width_keV: float, sigma_keV: float) -> float:
    if sigma_keV <= 0:
        return 1.0
    return math.erf(half_width_keV / (math.sqrt(2.0) * sigma_keV))


def fwhm_to_sigma(fwhm_keV: float) -> float:
    return fwhm_keV / 2.3548200450309493


def build_mass_spectra(step05: Any) -> tuple[list[dict[str, Any]], dict[str, float]]:
    with MASS_CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    disk = side_entry_disk()
    spectra: dict[tuple[str, str, float], dict[str, Any]] = {}
    stream = np.asarray(cat["stream"], dtype=object)
    energy = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    rate = np.asarray(cat["rate_hz"], dtype=float)

    for stream_name in ("prompt", "delayed"):
        mask = (stream == stream_name) & (energy >= 480.0) & (energy < 550.0) & (bgo < 50.0)
        for idx in np.flatnonzero(mask):
            keep, _cls = step05.side_keep_from_hits(step05.event_hits(cat, int(idx)), disk, "keep")
            if not keep:
                continue
            bin_lo = float(math.floor(float(energy[idx])))
            key = ("final_selected", stream_name, bin_lo)
            row = spectra.setdefault(
                key,
                {
                    "stage": "final_selected",
                    "stream": stream_name,
                    "energy_lo_keV": bin_lo,
                    "energy_hi_keV": bin_lo + 1.0,
                    "energy_center_keV": bin_lo + 0.5,
                    "events": 0,
                    "rate_cps": 0.0,
                    "sigma_cps": 0.0,
                },
            )
            row["events"] += 1
            row["rate_cps"] += float(rate[idx])

    rows = []
    for stream_name in ("prompt", "delayed"):
        for bin_lo in range(480, 550):
            row = spectra.get(
                ("final_selected", stream_name, float(bin_lo)),
                {
                    "stage": "final_selected",
                    "stream": stream_name,
                    "energy_lo_keV": float(bin_lo),
                    "energy_hi_keV": float(bin_lo + 1),
                    "energy_center_keV": float(bin_lo) + 0.5,
                    "events": 0,
                    "rate_cps": 0.0,
                    "sigma_cps": 0.0,
                },
            )
            events = int(row["events"])
            row["sigma_cps"] = float(row["rate_cps"] / math.sqrt(events)) if events > 0 else 0.0
            rows.append(row)

    side_rate = 0.0
    side_width = 0.0
    for row in rows:
        lo = float(row["energy_lo_keV"])
        hi = float(row["energy_hi_keV"])
        if (500.0 <= lo and hi <= 510.0) or (512.0 <= lo and hi <= 522.0):
            side_rate += float(row["rate_cps"])
            side_width += hi - lo
    cont = {
        "sideband_rate_cps": side_rate,
        "sideband_width_keV": side_width,
        "continuum_density_cps_per_keV": side_rate / side_width if side_width > 0 else 0.0,
    }
    return rows, cont


def build_p1_outputs(step05: Any) -> dict[str, Any]:
    mass_step05 = load_json(MASS_STEP05_SUMMARY)
    mass_step08 = load_json(MASS_STEP08_SUMMARY)
    spectra_rows, cont = build_mass_spectra(step05)
    spectra_csv = OUT / "p1_mass_model_511_spectra_480_550_by_stream_stage.csv"
    write_csv(spectra_csv, spectra_rows)

    w2 = mass_step05["windows"]["w2_510p58_511p42"]
    b_current = float(w2["physical_reference_flux"]["background_cps"])
    signal_current = float(w2["physical_reference_flux"]["signal_cps_at_reference_flux"])
    f3_current = float(mass_step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    z_current = float(mass_step08["checks"]["A_reference_w2_Z20d_time_dependent"])
    acc_current = gaussian_acceptance(W2_HALF_KEV, DET_SIGMA_KEV)
    line_total_cps = (b_current - cont["continuum_density_cps_per_keV"] * W2_WIDTH_KEV) / acc_current

    source_fwhms = [0.0, 1.3, 2.43, 5.36]
    bkg_fwhms = [0.0, 2.43]
    fixed_rows: list[dict[str, Any]] = []
    opt_rows: list[dict[str, Any]] = []
    for bkg_fwhm in bkg_fwhms:
        bkg_sigma = math.sqrt(DET_SIGMA_KEV**2 + fwhm_to_sigma(bkg_fwhm) ** 2)
        b_fixed = line_total_cps * gaussian_acceptance(W2_HALF_KEV, bkg_sigma) + cont["continuum_density_cps_per_keV"] * W2_WIDTH_KEV
        for src_fwhm in source_fwhms:
            src_sigma = math.sqrt(DET_SIGMA_KEV**2 + fwhm_to_sigma(src_fwhm) ** 2)
            src_acc = gaussian_acceptance(W2_HALF_KEV, src_sigma)
            scale = src_acc / acc_current
            fixed_rows.append(
                {
                    "source_fwhm_keV": src_fwhm,
                    "background_fwhm_keV": bkg_fwhm,
                    "window_half_keV": W2_HALF_KEV,
                    "source_acceptance": src_acc,
                    "background_cps": b_fixed,
                    "signal_cps_at_1e-4": signal_current * scale,
                    "Z20d_est": z_current * scale / math.sqrt(b_fixed / b_current),
                    "F3_20d_est_ph_cm2_s": f3_current * math.sqrt(b_fixed / b_current) / scale,
                    "mode": "fixed_mass_model_511_w2",
                }
            )

        half_grid = np.concatenate([np.linspace(0.10, 1.00, 91), np.linspace(1.02, 4.00, 150), np.linspace(4.05, 10.0, 120)])
        for src_fwhm in source_fwhms:
            src_sigma = math.sqrt(DET_SIGMA_KEV**2 + fwhm_to_sigma(src_fwhm) ** 2)
            best: dict[str, Any] | None = None
            for half in half_grid:
                src_acc = gaussian_acceptance(float(half), src_sigma)
                if src_acc <= 0:
                    continue
                b_scan = line_total_cps * gaussian_acceptance(float(half), bkg_sigma) + cont["continuum_density_cps_per_keV"] * (2.0 * float(half))
                scale = src_acc / acc_current
                row = {
                    "source_fwhm_keV": src_fwhm,
                    "background_fwhm_keV": bkg_fwhm,
                    "opt_window_half_keV": float(half),
                    "source_acceptance": src_acc,
                    "background_cps": b_scan,
                    "Z20d_est": z_current * scale / math.sqrt(b_scan / b_current),
                    "F3_20d_est_ph_cm2_s": f3_current * math.sqrt(b_scan / b_current) / scale,
                    "mode": "mass_model_511_optimized_window_scan",
                }
                if best is None or row["F3_20d_est_ph_cm2_s"] < best["F3_20d_est_ph_cm2_s"]:
                    best = row
            assert best is not None
            opt_rows.append(best)

    fixed_csv = OUT / "p1_mass_model_511_fixed_w2_linewidth_scan.csv"
    opt_csv = OUT / "p1_mass_model_511_optimized_window_linewidth_scan.csv"
    write_csv(fixed_csv, fixed_rows)
    write_csv(opt_csv, opt_rows)
    payload = {
        "status": "PASS_MASS_MODEL_511_P1_LINEWIDTH_REPLAY",
        "generated_at_utc": now_utc(),
        "inputs": {
            "step05_summary": rel(MASS_STEP05_SUMMARY),
            "step08_summary": rel(MASS_STEP08_SUMMARY),
            "event_catalog": rel(MASS_CATALOG),
            "spectra_csv": rel(spectra_csv),
        },
        "assumptions": {
            "detector_sigma_keV": DET_SIGMA_KEV,
            "current_window_keV": [W2_CENTER_KEV - W2_HALF_KEV, W2_CENTER_KEV + W2_HALF_KEV],
            "line_widths_checked_fwhm_keV": source_fwhms,
            "background_line_widths_checked_fwhm_keV": bkg_fwhms,
            "continuum_sidebands_keV": [[500.0, 510.0], [512.0, 522.0]],
            "model": "Mass_model_511 final-selected sideband continuum plus analytic Gaussian line-width/window convolution.",
        },
        "current_authority": {
            "B_cps": b_current,
            "signal_cps_at_1e-4": signal_current,
            "Z20d": z_current,
            "F3_20d_ph_cm2_s": f3_current,
            "current_unresolved_acceptance": acc_current,
        },
        "continuum_density": cont,
        "calibrated_total_line_rate_cps": line_total_cps,
        "fixed_w2_csv": rel(fixed_csv),
        "optimized_window_csv": rel(opt_csv),
        "fixed_w2_rows": fixed_rows,
        "optimized_window_rows": opt_rows,
    }
    write_json(OUT / "p1_mass_model_511_linewidth_sensitivity_summary.json", payload)
    return payload


def p2_observation_time_s() -> float:
    for line in P2_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"cannot locate Observation time in {P2_LOG}")


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def parse_p2_catalog() -> dict[str, Any]:
    cc_re = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
    kv_re = re.compile(r"(\w+)=([^\s]+)")
    id_re = re.compile(r"^ID\s+(\d+)")
    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
    cat: dict[str, Any] = {
        "local_id": [],
        "tes_total_keV": [],
        "bgo_total_keV": [],
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
    bgo_total = 0.0
    pix: dict[str, dict[str, float]] = {}

    def flush() -> None:
        nonlocal cur_id, bgo_total, pix, kept
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
        if pix_count > 0 or bgo_total > 0:
            cat["local_id"].append(int(cur_id))
            cat["tes_total_keV"].append(float(tes_total))
            cat["bgo_total_keV"].append(float(bgo_total))
            cat["pix_start"].append(int(pix_start))
            cat["pix_count"].append(int(pix_count))
            kept += 1
        cur_id = None
        bgo_total = 0.0
        pix = {}

    with gzip.open(P2_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
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
                bgo_total += edep
    flush()

    for key in ("local_id", "pix_start", "pix_count", "pix_layer"):
        cat[key] = np.asarray(cat[key], dtype=np.int64)
    for key in ("tes_total_keV", "bgo_total_keV", "pix_e", "pix_x", "pix_y", "pix_z"):
        cat[key] = np.asarray(cat[key], dtype=np.float64)
    cat["pix_uid"] = np.asarray(cat["pix_uid"], dtype=object)
    cat["generated_events"] = generated
    cat["kept_events_tes_or_active"] = kept
    return cat


def p2_event_hits(cat: dict[str, Any], idx: int) -> list[Any]:
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


def summarize_p2_window(cat: dict[str, Any], step05: Any, emin: float, emax: float) -> dict[str, Any]:
    tes = cat["tes_total_keV"]
    bgo = cat["bgo_total_keV"]
    mask = (tes >= emin) & (tes < emax)
    active = mask & (bgo < 50.0)
    classes: Counter[str] = Counter()
    final_indices = []
    disk = side_entry_disk()
    for idx in np.flatnonzero(active):
        keep, cls = step05.side_keep_from_hits(p2_event_hits(cat, int(idx)), disk, "keep")
        classes[cls] += 1
        if keep:
            final_indices.append(int(idx))
    event_weight = 1.0 / float(cat["observation_time_s"])
    return {
        "window_keV": [emin, emax],
        "raw_events": int(np.sum(mask)),
        "active_veto_pass_events": int(np.sum(active)),
        "side_compton_fov_pass_events": int(len(final_indices)),
        "raw_rate_per_unit_flux_cps_per_ph_cm2_s": float(np.sum(mask) * event_weight),
        "active_rate_per_unit_flux_cps_per_ph_cm2_s": float(np.sum(active) * event_weight),
        "final_rate_per_unit_flux_cps_per_ph_cm2_s": float(len(final_indices) * event_weight),
        "final_relative_poisson_sigma": float(1.0 / math.sqrt(len(final_indices))) if final_indices else None,
        "side_compton_class_counts": dict(sorted(classes.items())),
        "final_event_ids": [int(cat["local_id"][i]) for i in final_indices],
        "final_energies_keV": [float(cat["tes_total_keV"][i]) for i in final_indices],
        "final_bgo_keV": [float(cat["bgo_total_keV"][i]) for i in final_indices],
        "final_pix_counts": [int(cat["pix_count"][i]) for i in final_indices],
    }


def sim_header() -> dict[str, Any]:
    header: dict[str, Any] = {}
    with gzip.open(P2_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry"):
                header["geometry"] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("Seed"):
                header["seed"] = int(line.split()[1])
            elif line == "SE":
                break
    return header


def build_p2_outputs(step05: Any) -> dict[str, Any]:
    mass_step05 = load_json(MASS_STEP05_SUMMARY)
    mass_step08 = load_json(MASS_STEP08_SUMMARY)
    cat = parse_p2_catalog()
    cat["observation_time_s"] = p2_observation_time_s()
    w2 = summarize_p2_window(cat, step05, 510.58, 511.42)
    broad = summarize_p2_window(cat, step05, 480.0, 550.0)

    b_current = float(mass_step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]["background_cps"])
    f3_current = float(mass_step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    transfer = float(w2["final_rate_per_unit_flux_cps_per_ph_cm2_s"])
    scenarios = [
        ("Harris_Rc_11_13_total_disk_no_alt_scale", 4.38e-2 * 0.532, "Harris 2003 Table 2 normalized to <7 GV; no payload-altitude rescaling"),
        ("lower_hemisphere_brightness_3e-3_sr", 3e-3 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("lower_hemisphere_brightness_6e-3_sr", 6e-3 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("lower_hemisphere_brightness_1e-2_sr", 1e-2 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("MEGAlib_SMM_500km_to_34km_stress", 22.7e-3 * (500.0 / 34.0) ** 2, "MEGAlib BackgroundGenerator-style altitude scaling; stress test only"),
    ]
    scenario_rows = []
    for name, flux, note in scenarios:
        r_atm = transfer * flux
        b_new = b_current + r_atm
        f3_new = f3_current * math.sqrt(b_new / b_current)
        scenario_rows.append(
            {
                "scenario": name,
                "atm511_flux_ph_cm2_s": flux,
                "atm511_added_cps": r_atm,
                "background_new_cps": b_new,
                "background_fractional_increase": r_atm / b_current,
                "F3_20d_new_ph_cm2_s": f3_new,
                "note": note,
            }
        )

    scenario_csv = OUT / "p2_mass_model_511_atm511_flux_scenarios.csv"
    write_csv(scenario_csv, scenario_rows)
    header = sim_header()
    payload = {
        "status": "PASS_MASS_MODEL_511_P2_ATM511_TRANSFER_REPLAY",
        "generated_at_utc": now_utc(),
        "inputs": {
            "p2_source": rel(P2_SOURCE),
            "p2_log": rel(P2_LOG),
            "p2_sim": rel(P2_SIM),
            "step05_summary": rel(MASS_STEP05_SUMMARY),
            "step08_summary": rel(MASS_STEP08_SUMMARY),
            "step05_veto_algorithm": rel(STEP05_SCRIPT),
        },
        "sim_header": header,
        "normalization": {
            "source_total_lower_hemisphere_flux_ph_cm2_s": 1.0,
            "observation_time_s": float(cat["observation_time_s"]),
            "rate_weight_per_generated_event_s-1": 1.0 / float(cat["observation_time_s"]),
        },
        "catalog": {
            "generated_events": int(cat["generated_events"]),
            "kept_events_tes_or_active": int(cat["kept_events_tes_or_active"]),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0)),
            "active_veto_events": int(np.sum(cat["bgo_total_keV"] > 0)),
        },
        "windows": {
            "w2_510p58_511p42": w2,
            "broad_480_550": broad,
        },
        "scenario_csv": rel(scenario_csv),
        "scenario_rows": scenario_rows,
        "interpretation": {
            "limitation": "Detector-response transfer for an idealized lower-hemisphere mono-line field; dominant uncertainty remains atmospheric-line normalization and angular model.",
            "use_in_paper": "Mass_model_511-specific P2 correction table if the Mass_model_511 branch is adopted as paper authority.",
        },
    }
    write_json(OUT / "p2_mass_model_511_atm511_transfer_summary.json", payload)
    return payload


def write_readme(p1: dict[str, Any], p2: dict[str, Any]) -> None:
    harris = next(row for row in p2["scenario_rows"] if row["scenario"] == "Harris_Rc_11_13_total_disk_no_alt_scale")
    opt_243 = [
        row
        for row in p1["optimized_window_rows"]
        if abs(row["background_fwhm_keV"] - 2.43) < 1.0e-9 and row["source_fwhm_keV"] in (1.3, 2.43, 5.36)
    ]
    opt_lines = "\n".join(
        f"- source FWHM {row['source_fwhm_keV']:.2g} keV, bkg FWHM 2.43 keV: opt half-window {row['opt_window_half_keV']:.2f} keV, F3={row['F3_20d_est_ph_cm2_s']:.3e} ph cm^-2 s^-1"
        for row in opt_243
    )
    text = f"""# Mass_model_511 P1/P2/P3 Replay - 2026-07-03

Status: `PASS_MASS_MODEL_511_P1_P2_P3_REPLAY_NOT_PAPER_APPLIED`

This replay is specific to the current Mass_model_511 geometry branch. It does
not modify manuscript `.tex` files and does not replace the fix5 paper authority
unless the replacement review is accepted separately.

## P1 Line Width

Current Mass_model_511 W2 authority used here:
`B={p1['current_authority']['B_cps']:.8g} cps`,
`S(F0=1e-4)={p1['current_authority']['signal_cps_at_1e-4']:.8g} cps`,
`Z20d={p1['current_authority']['Z20d']:.6g}`,
`F3={p1['current_authority']['F3_20d_ph_cm2_s']:.8g} ph cm^-2 s^-1`.

Mass_model_511 final-selected sideband continuum density:
`{p1['continuum_density']['continuum_density_cps_per_keV']:.6g} cps/keV`.

Representative optimized-window estimates:
{opt_lines}

## P2 Atmospheric 511-keV Line

Transport source: `{rel(P2_SOURCE)}`

Simulation output: `{rel(P2_SIM)}`

W2 final unit transfer:
`{p2['windows']['w2_510p58_511p42']['final_rate_per_unit_flux_cps_per_ph_cm2_s']:.6g} cps / (ph cm^-2 s^-1)`,
from `{p2['windows']['w2_510p58_511p42']['side_compton_fov_pass_events']}` final events.

Harris Rc~11-13 GV scenario:
`F_atm={harris['atm511_flux_ph_cm2_s']:.6g} ph cm^-2 s^-1`,
added background `{harris['atm511_added_cps']:.6g} cps`,
new `F3={harris['F3_20d_new_ph_cm2_s']:.6g} ph cm^-2 s^-1`.

## P3 Geometry

No new transport is required. The Mass_model_511 Step06--Step08 current-geometry
products keep the same framing boundary: use the reference calculation as a
northern/near-zenith transient or compact-source sensitivity case; Galactic
center observations at 34 deg N remain a separate low-elevation/airmass case.

## Files

- `p1_mass_model_511_linewidth_sensitivity_summary.json`
- `p1_mass_model_511_fixed_w2_linewidth_scan.csv`
- `p1_mass_model_511_optimized_window_linewidth_scan.csv`
- `p1_mass_model_511_spectra_480_550_by_stream_stage.csv`
- `p2_mass_model_511_atm511_transfer_summary.json`
- `p2_mass_model_511_atm511_flux_scenarios.csv`
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [path for path in [MASS_STEP05_SUMMARY, MASS_STEP08_SUMMARY, MASS_CATALOG, P2_SOURCE, P2_LOG, P2_SIM] if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + ", ".join(rel(path) for path in missing))
    step05 = load_step05_module()
    p1 = build_p1_outputs(step05)
    p2 = build_p2_outputs(step05)
    write_readme(p1, p2)
    print(
        json.dumps(
            {
                "out": rel(OUT),
                "p1_fixed_rows": len(p1["fixed_w2_rows"]),
                "p1_opt_rows": len(p1["optimized_window_rows"]),
                "p2_final_events": p2["windows"]["w2_510p58_511p42"]["side_compton_fov_pass_events"],
                "p2_transfer": p2["windows"]["w2_510p58_511p42"]["final_rate_per_unit_flux_cps_per_ph_cm2_s"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
