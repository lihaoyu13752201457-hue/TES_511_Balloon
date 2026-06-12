#!/usr/bin/env python3
"""Build detector-coupled response for the focused Step09 EventList run.

This consumes the full, non-smoke Cosima output from the Step09 focused
EventList source and the existing day-15 prompt/delayed event catalog.  It does
not rerun transport.  The output is the single downstream authority for:

* true focused science response normalized by Step04 A_eff(511);
* W1/W2 non-X-ray background after raw/scintillator/Compton/both selections;
* detector-coupled spatial cuts based on focused science TES centroids.
"""

from __future__ import annotations

import csv
import argparse
import gzip
import json
import math
import os
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step09_optics_bridge"
OUT = STEP_DIR / "outputs"
FIG_DIR = OUT / "figures"
FOCUS_RESPONSE_JSON = OUT / "detector_coupled_focus_response.json"
FOCUS_RESPONSE_MD = OUT / "detector_coupled_focus_response.md"
WINDOW_CSV = OUT / "detector_coupled_focus_windows.csv"
BACKGROUND_CSV = OUT / "non_xray_background_w1_w2_veto_table.csv"
SPATIAL_CSV = OUT / "detector_coupled_spatial_line_cuts.csv"
SPECTRUM_CSV = OUT / "non_xray_background_spectrum_480_550.csv"

OPTICS_AUTHORITY = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority.json"
STEP09_SUMMARY = OUT / "step09_optics_bridge_summary.json"
STEP06_SUMMARY = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "step06_mission_time_variation_summary.json"
DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
BACKGROUND_CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
FOCUSED_SIM = ROOT / "runs" / "step09_optics_bridge" / "Opticsim_laue_new_geo_re.inc1.id1.sim.gz"
SPATIAL_FRAME: dict[str, Any] = {"axis_policy": "legacy_z_entry"}

REFERENCE_FLUX = 1.0e-4
LINE_CENTER_KEV = 511.0
TES_SIGMA_KEV = 0.14
MISSION_DAYS = 20.0
SECONDS_PER_DAY = 86400.0
SPECTRUM_EMIN = 480.0
SPECTRUM_EMAX = 550.0
SPECTRUM_BINW = 0.01

sys.path.insert(0, str(ROOT / "code" / "tools"))
import make_complete_day15_report_ADR as complete  # noqa: E402


def configure_profile(profile: str) -> None:
    global OUT, FIG_DIR, FOCUS_RESPONSE_JSON, FOCUS_RESPONSE_MD, WINDOW_CSV, BACKGROUND_CSV, SPATIAL_CSV, SPECTRUM_CSV
    global OPTICS_AUTHORITY, STEP09_SUMMARY, STEP06_SUMMARY, DAY15_SUMMARY, BACKGROUND_CATALOG, FOCUSED_SIM

    if profile in {"legacy", "new_geo_re"}:
        return
    if profile not in {"v3p5_fullstat_v2", "f10m_a1_v3p5_fullstat_v2"}:
        raise ValueError(f"unknown profile: {profile}")

    OUT = STEP_DIR / "outputs_f10m_a1_v3p5"
    FIG_DIR = OUT / "figures"
    FOCUS_RESPONSE_JSON = OUT / "detector_coupled_focus_response.json"
    FOCUS_RESPONSE_MD = OUT / "detector_coupled_focus_response.md"
    WINDOW_CSV = OUT / "detector_coupled_focus_windows.csv"
    BACKGROUND_CSV = OUT / "non_xray_background_w1_w2_veto_table.csv"
    SPATIAL_CSV = OUT / "detector_coupled_spatial_line_cuts.csv"
    SPECTRUM_CSV = OUT / "non_xray_background_spectrum_480_550.csv"

    OPTICS_AUTHORITY = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority_f10m_a1.json"
    STEP09_SUMMARY = OUT / "step09_optics_bridge_summary.json"
    STEP06_SUMMARY = (
        ROOT
        / "stepwise_maintenance"
        / "step06_mission_time_variation"
        / "outputs_v3p5_centerfinger_fullstat_v2"
        / "step06_v3p5_centerfinger_fullstat_v2_summary.json"
    )
    DAY15_SUMMARY = (
        ROOT
        / "stepwise_maintenance"
        / "step05_veto_time_axis"
        / "outputs_v3p5_centerfinger_fullstat_v2_l1"
        / "step05_v3p5_centerfinger_l1_response_summary.json"
    )
    BACKGROUND_CATALOG = (
        ROOT
        / "stepwise_maintenance"
        / "step05_veto_time_axis"
        / "outputs_v3p5_centerfinger_fullstat_v2_l1"
        / "work"
        / "event_catalog.pkl"
    )
    FOCUSED_SIM = ROOT / "runs" / "step09_optics_bridge" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def fmt(value: Any, nd: int = 6) -> str:
    try:
        x = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def gaussian_window_probability(energy_kev: float, lo_kev: float, hi_kev: float, sigma_kev: float = TES_SIGMA_KEV) -> float:
    inv = 1.0 / (math.sqrt(2.0) * sigma_kev)
    return 0.5 * (math.erf((hi_kev - energy_kev) * inv) - math.erf((lo_kev - energy_kev) * inv))


def rotate_y(values: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = values
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    return c * x + s * z, y, -s * x + c * z


def configure_spatial_frame(step09: dict[str, Any]) -> None:
    global SPATIAL_FRAME

    bridge = step09.get("bridge", {})
    policy = str(bridge.get("axis_policy", "legacy_z_entry"))
    if policy == "v3p5_side_entry_tilt45":
        SPATIAL_FRAME = {
            "axis_policy": policy,
            "axis_y_cm": float(bridge.get("axis_y_cm", 0.0)),
            "axis_z_cm": float(bridge.get("axis_z_cm", -5.2)),
            "be_radius_cm": float(bridge.get("be_radius_cm", 1.898)),
            "instrument_rotation_y_deg": float(bridge.get("instrument_rotation_y_deg", 45.0)),
        }
    else:
        SPATIAL_FRAME = {"axis_policy": "legacy_z_entry"}


def line_windows(optics: dict[str, Any]) -> list[dict[str, Any]]:
    w1 = optics["natural_passband_fwhm"]
    rows = [
        {
            "window_id": "W1_design_passband",
            "label": "W1 design natural passband FWHM",
            "lo_keV": float(w1["lo_keV"]),
            "hi_keV": float(w1["hi_keV"]),
            "basis": "Step04 optics_aeff_authority natural_passband_fwhm",
        },
        {
            "window_id": "line_pm_1sigma",
            "label": "511 +/- 1 sigma_TES",
            "lo_keV": LINE_CENTER_KEV - TES_SIGMA_KEV,
            "hi_keV": LINE_CENTER_KEV + TES_SIGMA_KEV,
            "basis": "TES Gaussian energy response",
        },
        {
            "window_id": "line_pm_2sigma",
            "label": "511 +/- 2 sigma_TES",
            "lo_keV": LINE_CENTER_KEV - 2.0 * TES_SIGMA_KEV,
            "hi_keV": LINE_CENTER_KEV + 2.0 * TES_SIGMA_KEV,
            "basis": "TES Gaussian energy response",
        },
        {
            "window_id": "W2_511_pm_420eV",
            "label": "W2 511 +/- 420 eV",
            "lo_keV": LINE_CENTER_KEV - 0.420,
            "hi_keV": LINE_CENTER_KEV + 0.420,
            "basis": "requested narrow line window, equal to +/-3 sigma_TES",
        },
    ]
    return rows


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_focused_sim(path: Path, rate_hz_per_event: float) -> dict[str, Any]:
    cat = complete.empty_catalog()
    cur_id = None
    bgo_total = 0.0
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, bgo_total, pix
        if cur_id is not None:
            complete.append_event(cat, "science_focus", "step09_eventlist", str(path), int(cur_id), rate_hz_per_event, bgo_total, pix)
        cur_id = None
        bgo_total = 0.0
        pix = {}

    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            m_id = complete.ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                cat["n_generated_events_seen"] += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = complete.parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = complete.TP_RE.match(vol)
            if m_tp:
                layer = int(m_tp.group("layer"))
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": layer})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
            elif complete.is_active_veto_volume(vol):
                bgo_total += edep
    flush()
    return complete.catalog_to_arrays(cat)


def classify_tes(cat: dict[str, Any], idx: int, reject_policy: str) -> tuple[bool, str]:
    pix_count = int(cat["pix_count"][idx])
    if pix_count <= 0:
        return False, "no_tes"
    if pix_count == 1:
        return True, "single"
    if pix_count > 6 and reject_policy == "keep":
        return True, "reject_kept"
    return complete.classify_final(complete.event_hits(cat, idx), reject_policy)


def event_centroid_radius_cm(cat: dict[str, Any], idx: int) -> float | None:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    if count <= 0:
        return None
    sum_e = 0.0
    wx = 0.0
    wy = 0.0
    wz = 0.0
    for j in range(start, start + count):
        e = float(cat["pix_e"][j])
        if e <= 0.0:
            continue
        sum_e += e
        wx += e * float(cat["pix_x"][j])
        wy += e * float(cat["pix_y"][j])
        wz += e * float(cat["pix_z"][j])
    if sum_e <= 0.0:
        return None
    cx = wx / sum_e
    cy = wy / sum_e
    cz = wz / sum_e
    if SPATIAL_FRAME.get("axis_policy") == "v3p5_side_entry_tilt45":
        _lx, ly, lz = rotate_y((cx, cy, cz), -float(SPATIAL_FRAME["instrument_rotation_y_deg"]))
        return math.hypot(ly - float(SPATIAL_FRAME["axis_y_cm"]), lz - float(SPATIAL_FRAME["axis_z_cm"]))
    return math.hypot(cx, cy)


def weighted_percentile(values: list[float], weights: list[float], frac: float) -> float:
    if not values:
        return 0.0
    order = np.argsort(np.asarray(values, dtype=float))
    v = np.asarray(values, dtype=float)[order]
    w = np.asarray(weights, dtype=float)[order]
    total = float(np.sum(w))
    if total <= 0.0:
        return float(v[min(len(v) - 1, max(0, int(round(frac * (len(v) - 1)))) )])
    c = np.cumsum(w)
    idx = int(np.searchsorted(c, frac * total, side="left"))
    idx = min(len(v) - 1, max(0, idx))
    return float(v[idx])


def z_for_rates(signal_cps: float, background_cps: float, mission_days: float = MISSION_DAYS) -> float:
    t = mission_days * SECONDS_PER_DAY
    if background_cps <= 0.0:
        return 0.0
    return signal_cps * t / math.sqrt(background_cps * t)


def t3_days(z20: float) -> float:
    if z20 <= 0.0:
        return math.inf
    return MISSION_DAYS * (3.0 / z20) ** 2


def flux3_20d(response_cps_per_flux: float, background_cps: float) -> float:
    t = MISSION_DAYS * SECONDS_PER_DAY
    if response_cps_per_flux <= 0.0 or background_cps <= 0.0:
        return math.inf
    return 3.0 * math.sqrt(background_cps * t) / (response_cps_per_flux * t)


def stage_flags(cat: dict[str, Any], idx: int, reject_policy: str) -> dict[str, bool]:
    has_tes = int(cat["pix_count"][idx]) > 0 and float(cat["tes_total_keV"][idx]) > 0.0
    bgo_pass = float(cat["bgo_total_keV"][idx]) < complete.BGO_THR_KEV
    compton_pass = False
    if has_tes:
        compton_pass, _cls = classify_tes(cat, idx, reject_policy)
    return {
        "raw": has_tes,
        "scintillator": has_tes and bgo_pass,
        "compton_fov": has_tes and compton_pass,
        "both": has_tes and bgo_pass and compton_pass,
    }


def classified_events(
    cat: dict[str, Any],
    reject_policy: str,
    include_streams: set[str] | None,
    skip_streams: set[str] | None,
    emin_keV: float,
    emax_keV: float,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for idx in range(len(cat["stream"])):
        stream = str(cat["stream"][idx])
        if include_streams is not None and stream not in include_streams:
            continue
        if skip_streams is not None and stream in skip_streams:
            continue
        energy = float(cat["tes_total_keV"][idx])
        if not (emin_keV <= energy <= emax_keV):
            continue
        flags = stage_flags(cat, idx, reject_policy)
        if not any(flags.values()):
            continue
        events.append(
            {
                "stream": stream,
                "energy_keV": energy,
                "rate_hz": float(cat["rate_hz"][idx]),
                "radius_cm": event_centroid_radius_cm(cat, idx),
                "raw": flags["raw"],
                "scintillator": flags["scintillator"],
                "compton_fov": flags["compton_fov"],
                "both": flags["both"],
            }
        )
    return events


def summarize_windows_for_events(
    events: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    source_label: str,
) -> list[dict[str, Any]]:
    acc: dict[tuple[str, str, str], dict[str, float]] = {}
    for event in events:
        energy = float(event["energy_keV"])
        rate = float(event["rate_hz"])
        stream = str(event["stream"])
        for window in windows:
            prob = gaussian_window_probability(energy, float(window["lo_keV"]), float(window["hi_keV"]))
            if prob <= 0.0:
                continue
            for stage in ("raw", "scintillator", "compton_fov", "both"):
                if not bool(event[stage]):
                    continue
                key = (str(window["window_id"]), stage, stream)
                rec = acc.setdefault(
                    key,
                    {
                        "window_id": str(window["window_id"]),
                        "stage": stage,
                        "source": source_label,
                        "stream": stream,
                        "lo_keV": float(window["lo_keV"]),
                        "hi_keV": float(window["hi_keV"]),
                        "rate_cps": 0.0,
                        "effective_catalog_events": 0.0,
                    },
                )
                rec["rate_cps"] += rate * prob
                rec["effective_catalog_events"] += prob
    rows = list(acc.values())
    rows.sort(key=lambda r: (str(r["window_id"]), str(r["stage"]), str(r["stream"])))
    return rows


def summarize_windows_for_catalog(
    cat: dict[str, Any],
    windows: list[dict[str, Any]],
    reject_policy: str,
    include_streams: set[str] | None,
    skip_streams: set[str] | None,
    source_label: str,
) -> list[dict[str, Any]]:
    acc: dict[tuple[str, str, str], dict[str, float]] = {}
    n = len(cat["stream"])
    for idx in range(n):
        stream = str(cat["stream"][idx])
        if include_streams is not None and stream not in include_streams:
            continue
        if skip_streams is not None and stream in skip_streams:
            continue
        energy = float(cat["tes_total_keV"][idx])
        if energy <= 0.0:
            continue
        flags = stage_flags(cat, idx, reject_policy)
        if not any(flags.values()):
            continue
        rate = float(cat["rate_hz"][idx])
        for window in windows:
            prob = gaussian_window_probability(energy, float(window["lo_keV"]), float(window["hi_keV"]))
            if prob <= 0.0:
                continue
            for stage, passed in flags.items():
                if not passed:
                    continue
                key = (str(window["window_id"]), stage, stream)
                rec = acc.setdefault(
                    key,
                    {
                        "window_id": str(window["window_id"]),
                        "stage": stage,
                        "source": source_label,
                        "stream": stream,
                        "lo_keV": float(window["lo_keV"]),
                        "hi_keV": float(window["hi_keV"]),
                        "rate_cps": 0.0,
                        "effective_catalog_events": 0.0,
                    },
                )
                rec["rate_cps"] += rate * prob
                rec["effective_catalog_events"] += prob
    rows = list(acc.values())
    rows.sort(key=lambda r: (str(r["window_id"]), str(r["stage"]), str(r["stream"])))
    return rows


def combined_window_rows(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    acc: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["window_id"]), str(row["stage"]))
        rec = acc.setdefault(
            key,
            {
                "window_id": row["window_id"],
                "stage": row["stage"],
                "source": source,
                "lo_keV": row["lo_keV"],
                "hi_keV": row["hi_keV"],
                "rate_cps": 0.0,
                "prompt_cps": 0.0,
                "delayed_cps": 0.0,
                "science_focus_cps": 0.0,
                "effective_catalog_events": 0.0,
            },
        )
        rate = float(row["rate_cps"])
        stream = str(row["stream"])
        rec["rate_cps"] += rate
        rec["effective_catalog_events"] += float(row.get("effective_catalog_events", 0.0))
        if stream == "prompt":
            rec["prompt_cps"] += rate
        elif stream == "delayed":
            rec["delayed_cps"] += rate
        elif stream == "science_focus":
            rec["science_focus_cps"] += rate
    out = list(acc.values())
    out.sort(key=lambda r: (str(r["window_id"]), str(r["stage"])))
    return out


def rows_by_window_stage(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["window_id"]), str(row["stage"])): row for row in rows}


def selected_spatial_events(cat: dict[str, Any], window: dict[str, Any], reject_policy: str) -> list[dict[str, float]]:
    events: list[dict[str, float]] = []
    for idx in range(len(cat["stream"])):
        if float(cat["tes_total_keV"][idx]) <= 0.0:
            continue
        flags = stage_flags(cat, idx, reject_policy)
        if not flags["both"]:
            continue
        prob = gaussian_window_probability(float(cat["tes_total_keV"][idx]), float(window["lo_keV"]), float(window["hi_keV"]))
        if prob <= 0.0:
            continue
        radius = event_centroid_radius_cm(cat, idx)
        if radius is None:
            continue
        events.append(
            {
                "radius_cm": radius,
                "rate_weight_cps": float(cat["rate_hz"][idx]) * prob,
                "window_prob": prob,
                "rate_hz": float(cat["rate_hz"][idx]),
            }
        )
    return events


def background_spatial_events(cat: dict[str, Any], window: dict[str, Any], reject_policy: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for idx in range(len(cat["stream"])):
        stream = str(cat["stream"][idx])
        if stream == "science":
            continue
        if float(cat["tes_total_keV"][idx]) <= 0.0:
            continue
        flags = stage_flags(cat, idx, reject_policy)
        if not flags["both"]:
            continue
        prob = gaussian_window_probability(float(cat["tes_total_keV"][idx]), float(window["lo_keV"]), float(window["hi_keV"]))
        if prob <= 0.0:
            continue
        radius = event_centroid_radius_cm(cat, idx)
        if radius is None:
            continue
        events.append(
            {
                "stream": stream,
                "radius_cm": radius,
                "rate_weight_cps": float(cat["rate_hz"][idx]) * prob,
                "window_prob": prob,
            }
        )
    return events


def build_spatial_rows(
    focus_cat: dict[str, Any],
    background_cat: dict[str, Any],
    w2: dict[str, Any],
    reject_policy: str,
    reference_flux: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signal_events = selected_spatial_events(focus_cat, w2, reject_policy)
    background_events = background_spatial_events(background_cat, w2, reject_policy)
    radii = [float(e["radius_cm"]) for e in signal_events]
    weights = [float(e["rate_weight_cps"]) for e in signal_events]
    signal_total = sum(weights)
    q50 = weighted_percentile(radii, weights, 0.50)
    q68 = weighted_percentile(radii, weights, 0.68)
    q90 = weighted_percentile(radii, weights, 0.90)
    q95 = weighted_percentile(radii, weights, 0.95)
    q99 = weighted_percentile(radii, weights, 0.99)
    rmax = max(radii) if radii else 0.0
    cut_specs = [
        ("spot_r50", q50),
        ("spot_r68", q68),
        ("spot_r90", q90),
        ("spot_r95", q95),
        ("spot_r99", q99),
        ("spot_rmax", rmax),
        ("full_aperture_1p8", 1.8),
    ]
    rows: list[dict[str, Any]] = []
    for cut_id, radius in cut_specs:
        sig = sum(float(e["rate_weight_cps"]) for e in signal_events if float(e["radius_cm"]) <= radius)
        bg_prompt = sum(float(e["rate_weight_cps"]) for e in background_events if str(e["stream"]) == "prompt" and float(e["radius_cm"]) <= radius)
        bg_delayed = sum(float(e["rate_weight_cps"]) for e in background_events if str(e["stream"]) == "delayed" and float(e["radius_cm"]) <= radius)
        bg = bg_prompt + bg_delayed
        response = sig / reference_flux if reference_flux > 0.0 else 0.0
        z20 = z_for_rates(sig, bg)
        rows.append(
            {
                "cut_id": cut_id,
                "radius_cm": radius,
                "signal_cps_at_reference_flux": sig,
                "signal_response_cps_per_ph_cm2_s": response,
                "signal_psf_fraction": sig / signal_total if signal_total > 0.0 else 0.0,
                "prompt_cps": bg_prompt,
                "delayed_cps": bg_delayed,
                "background_cps": bg,
                "Z20d_at_reference_flux": z20,
                "T3_day_constant_rate": t3_days(z20),
                "T3_status": "mission_internal_crossing" if t3_days(z20) <= MISSION_DAYS else "extrapolated_beyond_20d",
                "flux_3sigma_20d_ph_cm2_s": flux3_20d(response, bg),
            }
        )
    robust_rows = [row for row in rows if row["cut_id"] not in {"spot_rmax", "full_aperture_1p8"}]
    best = max(robust_rows, key=lambda row: float(row["Z20d_at_reference_flux"])) if robust_rows else {}
    checks = {
        "signal_detector_events": len(signal_events),
        "background_detector_events": len(background_events),
        "signal_radius_r50_cm": q50,
        "signal_radius_r68_cm": q68,
        "signal_radius_r90_cm": q90,
        "signal_radius_r95_cm": q95,
        "signal_radius_r99_cm": q99,
        "signal_radius_max_cm": rmax,
        "best_cut_id": best.get("cut_id", ""),
        "best_cut_radius_cm": best.get("radius_cm", 0.0),
        "best_cut_signal_psf_fraction": best.get("signal_psf_fraction", 0.0),
        "best_cut_background_cps": best.get("background_cps", 0.0),
        "best_cut_Z20d": best.get("Z20d_at_reference_flux", 0.0),
        "spot_r90_signal_psf_fraction": next((r["signal_psf_fraction"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_background_cps": next((r["background_cps"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_Z20d": next((r["Z20d_at_reference_flux"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_flux_3sigma_20d_ph_cm2_s": next((r["flux_3sigma_20d_ph_cm2_s"] for r in rows if r["cut_id"] == "spot_r90"), math.inf),
    }
    return rows, checks


def build_spatial_rows_from_events(
    focus_events: list[dict[str, Any]],
    background_events: list[dict[str, Any]],
    w2: dict[str, Any],
    reference_flux: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signal_events = []
    for event in focus_events:
        if not bool(event["both"]) or event.get("radius_cm") is None:
            continue
        prob = gaussian_window_probability(float(event["energy_keV"]), float(w2["lo_keV"]), float(w2["hi_keV"]))
        if prob <= 0.0:
            continue
        signal_events.append(
            {
                "radius_cm": float(event["radius_cm"]),
                "rate_weight_cps": float(event["rate_hz"]) * prob,
            }
        )
    bg_events = []
    for event in background_events:
        if not bool(event["both"]) or event.get("radius_cm") is None:
            continue
        prob = gaussian_window_probability(float(event["energy_keV"]), float(w2["lo_keV"]), float(w2["hi_keV"]))
        if prob <= 0.0:
            continue
        bg_events.append(
            {
                "stream": str(event["stream"]),
                "radius_cm": float(event["radius_cm"]),
                "rate_weight_cps": float(event["rate_hz"]) * prob,
            }
        )
    radii = [float(e["radius_cm"]) for e in signal_events]
    weights = [float(e["rate_weight_cps"]) for e in signal_events]
    signal_total = sum(weights)
    q50 = weighted_percentile(radii, weights, 0.50)
    q68 = weighted_percentile(radii, weights, 0.68)
    q90 = weighted_percentile(radii, weights, 0.90)
    q95 = weighted_percentile(radii, weights, 0.95)
    q99 = weighted_percentile(radii, weights, 0.99)
    rmax = max(radii) if radii else 0.0
    cut_specs = [
        ("spot_r50", q50),
        ("spot_r68", q68),
        ("spot_r90", q90),
        ("spot_r95", q95),
        ("spot_r99", q99),
        ("spot_rmax", rmax),
        ("full_aperture_1p8", 1.8),
    ]
    rows: list[dict[str, Any]] = []
    for cut_id, radius in cut_specs:
        sig = sum(float(e["rate_weight_cps"]) for e in signal_events if float(e["radius_cm"]) <= radius)
        bg_prompt = sum(float(e["rate_weight_cps"]) for e in bg_events if str(e["stream"]) == "prompt" and float(e["radius_cm"]) <= radius)
        bg_delayed = sum(float(e["rate_weight_cps"]) for e in bg_events if str(e["stream"]) == "delayed" and float(e["radius_cm"]) <= radius)
        bg = bg_prompt + bg_delayed
        response = sig / reference_flux if reference_flux > 0.0 else 0.0
        z20 = z_for_rates(sig, bg)
        rows.append(
            {
                "cut_id": cut_id,
                "radius_cm": radius,
                "signal_cps_at_reference_flux": sig,
                "signal_response_cps_per_ph_cm2_s": response,
                "signal_psf_fraction": sig / signal_total if signal_total > 0.0 else 0.0,
                "prompt_cps": bg_prompt,
                "delayed_cps": bg_delayed,
                "background_cps": bg,
                "Z20d_at_reference_flux": z20,
                "T3_day_constant_rate": t3_days(z20),
                "T3_status": "mission_internal_crossing" if t3_days(z20) <= MISSION_DAYS else "extrapolated_beyond_20d",
                "flux_3sigma_20d_ph_cm2_s": flux3_20d(response, bg),
            }
        )
    robust_rows = [row for row in rows if row["cut_id"] not in ("spot_rmax", "full_aperture_1p8")]
    best = max(robust_rows, key=lambda row: float(row["Z20d_at_reference_flux"])) if robust_rows else {}
    checks = {
        "signal_detector_events": len(signal_events),
        "background_detector_events": len(bg_events),
        "signal_radius_r50_cm": q50,
        "signal_radius_r68_cm": q68,
        "signal_radius_r90_cm": q90,
        "signal_radius_r95_cm": q95,
        "signal_radius_r99_cm": q99,
        "signal_radius_max_cm": rmax,
        "best_cut_id": best.get("cut_id", ""),
        "best_cut_radius_cm": best.get("radius_cm", 0.0),
        "best_cut_signal_psf_fraction": best.get("signal_psf_fraction", 0.0),
        "best_cut_background_cps": best.get("background_cps", 0.0),
        "best_cut_Z20d": best.get("Z20d_at_reference_flux", 0.0),
        "spot_r90_signal_psf_fraction": next((r["signal_psf_fraction"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_background_cps": next((r["background_cps"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_Z20d": next((r["Z20d_at_reference_flux"] for r in rows if r["cut_id"] == "spot_r90"), 0.0),
        "spot_r90_flux_3sigma_20d_ph_cm2_s": next((r["flux_3sigma_20d_ph_cm2_s"] for r in rows if r["cut_id"] == "spot_r90"), math.inf),
    }
    return rows, checks


def build_spectrum_rows_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n_bins = int((SPECTRUM_EMAX - SPECTRUM_EMIN) / SPECTRUM_BINW)
    edges = [SPECTRUM_EMIN + i * SPECTRUM_BINW for i in range(n_bins + 1)]
    rates = {
        "raw": np.zeros(n_bins),
        "scintillator": np.zeros(n_bins),
        "compton_fov": np.zeros(n_bins),
        "both": np.zeros(n_bins),
    }
    by_stream = {
        "raw_prompt": np.zeros(n_bins),
        "raw_delayed": np.zeros(n_bins),
        "both_prompt": np.zeros(n_bins),
        "both_delayed": np.zeros(n_bins),
    }
    for event in events:
        stream = str(event["stream"])
        energy = float(event["energy_keV"])
        if not (SPECTRUM_EMIN <= energy < SPECTRUM_EMAX):
            continue
        k = int((energy - SPECTRUM_EMIN) / SPECTRUM_BINW)
        if not (0 <= k < n_bins):
            continue
        rate_density = float(event["rate_hz"]) / SPECTRUM_BINW
        for stage in ("raw", "scintillator", "compton_fov", "both"):
            if bool(event[stage]):
                rates[stage][k] += rate_density
        if bool(event["raw"]):
            by_stream[f"raw_{stream}"][k] += rate_density
        if bool(event["both"]):
            by_stream[f"both_{stream}"][k] += rate_density
    rows: list[dict[str, Any]] = []
    for k in range(n_bins):
        row = {
            "energy_lo_keV": edges[k],
            "energy_hi_keV": edges[k + 1],
            "energy_center_keV": 0.5 * (edges[k] + edges[k + 1]),
            "raw_cps_per_keV": rates["raw"][k],
            "scintillator_cps_per_keV": rates["scintillator"][k],
            "compton_fov_cps_per_keV": rates["compton_fov"][k],
            "both_cps_per_keV": rates["both"][k],
            "raw_prompt_cps_per_keV": by_stream["raw_prompt"][k],
            "raw_delayed_cps_per_keV": by_stream["raw_delayed"][k],
            "both_prompt_cps_per_keV": by_stream["both_prompt"][k],
            "both_delayed_cps_per_keV": by_stream["both_delayed"][k],
        }
        rows.append(row)
    return rows


def plot_background_spectrum(
    rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    w1_checks: dict[str, Any],
) -> None:
    x = np.asarray([float(r["energy_center_keV"]) for r in rows])
    fig, ax = plt.subplots(figsize=(9.0, 5.1))
    styles = [
        ("raw_cps_per_keV", "raw", "background_raw_cps", "#4C78A8"),
        ("scintillator_cps_per_keV", "+CsI scintillator", "background_scintillator_cps", "#F58518"),
        ("compton_fov_cps_per_keV", "+Compton/FoV", "background_compton_fov_cps", "#54A24B"),
        ("both_cps_per_keV", "after both", "background_both_cps", "#B279A2"),
    ]
    for key, label, rate_key, color in styles:
        y = np.asarray([float(r[key]) for r in rows])
        rate = float(w1_checks.get(rate_key, 0.0))
        ax.step(x, y, where="mid", lw=1.4, color=color, label=f"{label} ({fmt(rate, 3)} cps)")
    w1_window = None
    for window in windows:
        if str(window["window_id"]) == "W1_design_passband":
            w1_window = window
            ax.axvspan(float(window["lo_keV"]), float(window["hi_keV"]), color="#F58518", alpha=0.06, label="W1")
        if str(window["window_id"]) == "W2_511_pm_420eV":
            ax.axvspan(float(window["lo_keV"]), float(window["hi_keV"]), color="#D62728", alpha=0.16, label="W2")
    if w1_window is not None:
        ax.set_xlim(float(w1_window["lo_keV"]), float(w1_window["hi_keV"]))
    ax.set_yscale("log")
    ax.set_xlabel("TES event energy (keV)")
    ax.set_ylabel("background rate (cps/keV)")
    ax.set_title("Day-15 non-X-ray background spectrum, veto chain over W1 (W2 marked)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, ncols=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "non_xray_background_spectrum_w1_w2.png", dpi=220)
    plt.close(fig)


def plot_spatial_rows(rows: list[dict[str, Any]]) -> None:
    fig, ax1 = plt.subplots(figsize=(8.2, 4.8))
    labels = [str(r["cut_id"]) for r in rows]
    x = np.arange(len(rows))
    z = [float(r["Z20d_at_reference_flux"]) for r in rows]
    bg = [float(r["background_cps"]) for r in rows]
    ax1.bar(x, z, color="#4C78A8", alpha=0.78, label="Z20d")
    ax1.set_xticks(x, labels, rotation=24, ha="right")
    ax1.set_ylabel("Z20d at 1e-4 ph cm-2 s-1")
    ax1.grid(True, axis="y", alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(x, bg, marker="o", color="#F58518", label="background cps")
    ax2.set_yscale("log")
    ax2.set_ylabel("W2 final background (cps)")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "detector_coupled_spatial_line_cuts.png", dpi=220)
    plt.close(fig)


def build_background_veto_table(background_combined: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = rows_by_window_stage(background_combined)
    out: list[dict[str, Any]] = []
    for window_id in ("W1_design_passband", "W2_511_pm_420eV"):
        raw = float(by_key[(window_id, "raw")]["rate_cps"])
        for stage in ("raw", "scintillator", "compton_fov", "both"):
            row = dict(by_key[(window_id, stage)])
            row["rejection_factor_vs_raw"] = raw / float(row["rate_cps"]) if float(row["rate_cps"]) > 0.0 else math.inf
            out.append(row)
    return out


def write_markdown(payload: dict[str, Any]) -> None:
    checks = payload["checks"]
    w = payload["window_checks"]
    s = payload["spatial_checks"]
    lines = [
        "# Step09 Detector-Coupled Focus Response",
        "",
        "Status: `PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST`.",
        "",
        "This report parses the full non-smoke Step09 focused EventList Cosima output and normalizes it with the Step04 B-FULL A_eff(511) authority. The science source is the focused EventList, not a homogeneous Be-window beam.",
        "",
        "## Optics Authority",
        "",
        f"- design: `{payload['optics']['design_name']}`",
        f"- focal length: `{fmt(payload['optics']['focal_length_mm'])}` mm",
        f"- A_eff(511): `{fmt(payload['optics']['aeff_511_cm2'])}` cm2",
        f"- target residual: `{fmt(checks['aeff_design_rel_residual'])}` against the 16 cm2 design target",
        f"- W1: `{fmt(payload['windows']['W1_design_passband']['lo_keV'])}-{fmt(payload['windows']['W1_design_passband']['hi_keV'])}` keV",
        f"- W2: `{fmt(payload['windows']['W2_511_pm_420eV']['lo_keV'])}-{fmt(payload['windows']['W2_511_pm_420eV']['hi_keV'])}` keV",
        "",
        "## Detector Response",
        "",
        f"- focused source triggers parsed: `{checks['focused_generated_events_seen']}`",
        f"- focused TES events kept: `{checks['focused_kept_events']}`",
        f"- W1 after both: signal `{fmt(w['W1_design_passband']['signal_both_cps_at_reference_flux'])}` cps at 1e-4, background `{fmt(w['W1_design_passband']['background_both_cps'])}` cps, Z20d `{fmt(w['W1_design_passband']['Z20d_both'])}`",
        f"- W2 after both: signal `{fmt(w['W2_511_pm_420eV']['signal_both_cps_at_reference_flux'])}` cps at 1e-4, background `{fmt(w['W2_511_pm_420eV']['background_both_cps'])}` cps, Z20d `{fmt(w['W2_511_pm_420eV']['Z20d_both'])}`",
        "",
        "## Spatial Cut",
        "",
        f"- detector-coupled focused W2 r90: `{fmt(s['signal_radius_r90_cm'])}` cm",
        f"- headline cut: `spot_r90`, signal fraction `{fmt(s['spot_r90_signal_psf_fraction'])}`, background `{fmt(s['spot_r90_background_cps'])}` cps, Z20d `{fmt(s['spot_r90_Z20d'])}`",
        f"- best robust cut: `{s['best_cut_id']}` at `{fmt(s['best_cut_radius_cm'])}` cm, Z20d `{fmt(s['best_cut_Z20d'])}`",
        "",
        "## Outputs",
        "",
        f"- JSON: `{rel(FOCUS_RESPONSE_JSON)}`",
        f"- windows: `{rel(WINDOW_CSV)}`",
        f"- W1/W2 veto table: `{rel(BACKGROUND_CSV)}`",
        f"- spatial cuts: `{rel(SPATIAL_CSV)}`",
        f"- spectrum: `{rel(SPECTRUM_CSV)}`",
        f"- figures: `{rel(FIG_DIR)}`",
    ]
    FOCUS_RESPONSE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    ensure_dirs()
    optics = load_json(OPTICS_AUTHORITY, {})
    step09 = load_json(STEP09_SUMMARY, {})
    step06 = load_json(STEP06_SUMMARY, {})
    day15 = load_json(DAY15_SUMMARY, {})
    configure_spatial_frame(step09)
    if not FOCUSED_SIM.exists():
        raise FileNotFoundError(FOCUSED_SIM)
    windows = line_windows(optics)
    wmap = {str(w["window_id"]): w for w in windows}
    reject_policy = str(day15.get("normalization", {}).get("reject_policy", "keep"))
    reference_flux = float(
        day15.get("science_physical_normalization", {}).get(
            "reference_flux_ph_cm2_s",
            day15.get("normalization", {}).get("science_flux_ph_cm2_s", REFERENCE_FLUX),
        )
    )
    t_atm = float(step06.get("normalization", {}).get("T_ref", step06.get("atmosphere", {}).get("T_ref", 0.7390423888027)))
    aeff = float(optics["aeff_511_cm2"])
    eventlist_rows = int(step09.get("bridge", {}).get("rows_written", 0))
    focused_rate = reference_flux * aeff * t_atm
    rate_per_event = focused_rate / max(eventlist_rows, 1)

    focus_cat = parse_focused_sim(FOCUSED_SIM, rate_per_event)
    with BACKGROUND_CATALOG.open("rb") as handle:
        background_cat = pickle.load(handle)

    class_emin = min(SPECTRUM_EMIN, min(float(w["lo_keV"]) for w in windows)) - 5.0 * TES_SIGMA_KEV
    class_emax = max(SPECTRUM_EMAX, max(float(w["hi_keV"]) for w in windows)) + 5.0 * TES_SIGMA_KEV
    focus_events = classified_events(
        focus_cat,
        reject_policy,
        include_streams={"science_focus"},
        skip_streams=None,
        emin_keV=class_emin,
        emax_keV=class_emax,
    )
    background_events = classified_events(
        background_cat,
        reject_policy,
        include_streams=None,
        skip_streams={"science"},
        emin_keV=class_emin,
        emax_keV=class_emax,
    )
    signal_stream_rows = summarize_windows_for_events(focus_events, windows, "focused_eventlist_science")
    background_stream_rows = summarize_windows_for_events(background_events, windows, "non_xray_background")
    signal_combined = combined_window_rows(signal_stream_rows, "focused_eventlist_science")
    background_combined = combined_window_rows(background_stream_rows, "non_xray_background")
    all_rows = signal_combined + background_combined
    write_csv(WINDOW_CSV, all_rows)
    background_veto_rows = build_background_veto_table(background_combined)
    write_csv(BACKGROUND_CSV, background_veto_rows)

    signal_lookup = rows_by_window_stage(signal_combined)
    background_lookup = rows_by_window_stage(background_combined)
    window_checks: dict[str, dict[str, Any]] = {}
    for window in windows:
        wid = str(window["window_id"])
        sig_both = float(signal_lookup.get((wid, "both"), {}).get("rate_cps", 0.0))
        sig_scint = float(signal_lookup.get((wid, "scintillator"), {}).get("rate_cps", 0.0))
        sig_compton = float(signal_lookup.get((wid, "compton_fov"), {}).get("rate_cps", 0.0))
        bg_both = float(background_lookup.get((wid, "both"), {}).get("rate_cps", 0.0))
        sig_raw = float(signal_lookup.get((wid, "raw"), {}).get("rate_cps", 0.0))
        bg_raw = float(background_lookup.get((wid, "raw"), {}).get("rate_cps", 0.0))
        z20 = z_for_rates(sig_both, bg_both)
        window_checks[wid] = {
            "lo_keV": float(window["lo_keV"]),
            "hi_keV": float(window["hi_keV"]),
            "signal_raw_cps_at_reference_flux": sig_raw,
            "signal_scintillator_cps_at_reference_flux": sig_scint,
            "signal_compton_fov_cps_at_reference_flux": sig_compton,
            "signal_both_cps_at_reference_flux": sig_both,
            "signal_both_response_cps_per_ph_cm2_s": sig_both / reference_flux if reference_flux > 0.0 else 0.0,
            "signal_scintillator_response_cps_per_ph_cm2_s": sig_scint / reference_flux if reference_flux > 0.0 else 0.0,
            "signal_compton_fov_response_cps_per_ph_cm2_s": sig_compton / reference_flux if reference_flux > 0.0 else 0.0,
            "background_raw_cps": bg_raw,
            "background_scintillator_cps": float(background_lookup.get((wid, "scintillator"), {}).get("rate_cps", 0.0)),
            "background_compton_fov_cps": float(background_lookup.get((wid, "compton_fov"), {}).get("rate_cps", 0.0)),
            "background_both_cps": bg_both,
            "Z20d_both": z20,
            "T3_day_constant_rate": t3_days(z20),
            "T3_status": "mission_internal_crossing" if t3_days(z20) <= MISSION_DAYS else "extrapolated_beyond_20d",
            "flux_3sigma_20d_ph_cm2_s": flux3_20d(sig_both / reference_flux if reference_flux > 0.0 else 0.0, bg_both),
        }

    spatial_rows, spatial_checks = build_spatial_rows_from_events(focus_events, background_events, wmap["W2_511_pm_420eV"], reference_flux)
    write_csv(SPATIAL_CSV, spatial_rows)
    spectrum_rows = build_spectrum_rows_from_events(background_events)
    write_csv(SPECTRUM_CSV, spectrum_rows)
    plot_background_spectrum(spectrum_rows, windows, window_checks["W1_design_passband"])
    plot_spatial_rows(spatial_rows)

    target = float(optics.get("design_target", {}).get("aeff_511_design_cm2", 16.0))
    tol = float(optics.get("design_target", {}).get("aeff_tolerance_fraction", 0.15))
    residual = abs(aeff - target) / target if target > 0.0 else 0.0
    payload = {
        "status": "PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST",
        "claim_level": "L1_DETECTOR_COUPLED_FOCUSED_EVENTLIST",
        "scope": "Full non-smoke Step09 focused EventList science transport parsed through the current TES/CsI/Compton-FoV selection. Optics hardware mass activation is still not included.",
        "inputs": {
            "focused_sim": rel(FOCUSED_SIM),
            "background_catalog": rel(BACKGROUND_CATALOG),
            "optics_authority": rel(OPTICS_AUTHORITY),
            "step09_summary": rel(STEP09_SUMMARY),
            "day15_summary": rel(DAY15_SUMMARY),
            "step06_summary": rel(STEP06_SUMMARY),
            "reject_policy": reject_policy,
            "spatial_frame": SPATIAL_FRAME,
        },
        "normalization": {
            "reference_flux_ph_cm2_s": reference_flux,
            "A_eff_511_cm2": aeff,
            "T_atm_ref": t_atm,
            "focused_plane_rate_cps_at_reference_flux": focused_rate,
            "eventlist_rows": eventlist_rows,
            "rate_per_event_cps": rate_per_event,
            "tes_sigma_keV": TES_SIGMA_KEV,
            "mission_days": MISSION_DAYS,
        },
        "optics": {
            "design_name": optics.get("design_name"),
            "focal_length_mm": optics.get("focal_length_mm"),
            "aeff_511_cm2": aeff,
            "natural_passband_fwhm": optics.get("natural_passband_fwhm"),
            "focal_stats": optics.get("focal_stats"),
        },
        "windows": {str(w["window_id"]): w for w in windows},
        "window_checks": window_checks,
        "spatial_checks": spatial_checks,
        "checks": {
            "focused_generated_events_seen": int(focus_cat.get("n_generated_events_seen", 0)),
            "focused_kept_events": int(focus_cat.get("n_kept_events", 0)),
            "focused_classified_events_480_550": len(focus_events),
            "background_classified_events_480_550": len(background_events),
            "focused_rate_matches_aeff_times_tatm": focused_rate,
            "aeff_design_target_cm2": target,
            "aeff_design_tolerance_fraction": tol,
            "aeff_design_rel_residual": residual,
            "aeff_design_within_tolerance": residual <= tol + 1.0e-12,
            "W1_background_rejection_both_vs_raw": window_checks["W1_design_passband"]["background_raw_cps"] / window_checks["W1_design_passband"]["background_both_cps"],
            "W2_background_rejection_both_vs_raw": window_checks["W2_511_pm_420eV"]["background_raw_cps"] / window_checks["W2_511_pm_420eV"]["background_both_cps"],
        },
        "outputs": {
            "json": rel(FOCUS_RESPONSE_JSON),
            "markdown": rel(FOCUS_RESPONSE_MD),
            "windows_csv": rel(WINDOW_CSV),
            "background_veto_csv": rel(BACKGROUND_CSV),
            "spatial_csv": rel(SPATIAL_CSV),
            "spectrum_csv": rel(SPECTRUM_CSV),
            "background_spectrum_figure": rel(FIG_DIR / "non_xray_background_spectrum_w1_w2.png"),
            "spatial_figure": rel(FIG_DIR / "detector_coupled_spatial_line_cuts.png"),
        },
    }
    write_json(FOCUS_RESPONSE_JSON, payload)
    write_markdown(payload)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--profile",
        default="legacy",
        choices=["legacy", "new_geo_re", "v3p5_fullstat_v2", "f10m_a1_v3p5_fullstat_v2"],
        help="Input/output profile. Default preserves the legacy new_geo_re paths.",
    )
    args = ap.parse_args()
    configure_profile(args.profile)
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "claim_level": payload["claim_level"],
                "W1": payload["window_checks"]["W1_design_passband"],
                "W2": payload["window_checks"]["W2_511_pm_420eV"],
                "spatial": payload["spatial_checks"],
                "out": rel(FOCUS_RESPONSE_JSON),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
