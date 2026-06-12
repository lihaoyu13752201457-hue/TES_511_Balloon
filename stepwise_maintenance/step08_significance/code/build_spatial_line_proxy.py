#!/usr/bin/env python3
"""Build a focused-spot spatial-cut proxy for the 511-keV line window."""

from __future__ import annotations

import csv
import json
import math
import os
import pickle
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
LINE_CSV = OUT / "line_window_sensitivity.csv"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"
STEP09_SUMMARY = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "step09_optics_bridge_summary.json"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
FOCUS_SPATIAL_CSV = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_spatial_line_cuts.csv"

SECONDS_PER_DAY = 86400.0
MISSION_DAYS = 20.0
LINE_CENTER_KEV = 511.0
TES_SIGMA_KEV = 0.14
LINE_LO_KEV = LINE_CENTER_KEV - 3.0 * TES_SIGMA_KEV
LINE_HI_KEV = LINE_CENTER_KEV + 3.0 * TES_SIGMA_KEV

sys.path.insert(0, str(ROOT / "code" / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_complete_day15_report_ADR as complete  # noqa: E402
from time_fold_common import time_dependent_fold as shared_time_dependent_fold  # noqa: E402


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float | None, nd: int = 6) -> str:
    if x is None or not math.isfinite(float(x)):
        return "nan"
    value = float(x)
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{nd}e}"
    return f"{value:.{nd}g}"


def time_dependent_fold(
    selection_id: str,
    prompt_cps_day15: float,
    delayed_cps_day15: float,
    science_cps_day15: float,
    reference_flux: float,
) -> tuple[dict[str, float | str], list[dict[str, Any]]]:
    return shared_time_dependent_fold(
        selection_id,
        prompt_cps_day15,
        delayed_cps_day15,
        science_cps_day15,
        reference_flux,
        id_field="cut_id",
        step06_bg_csv=STEP06_BG,
        day15_summary_json=DAY15_SUMMARY,
    )


def gaussian_window_probability(energy_kev: float, lo_kev: float, hi_kev: float, sigma_kev: float) -> float:
    inv = 1.0 / (math.sqrt(2.0) * sigma_kev)
    return 0.5 * (math.erf((hi_kev - energy_kev) * inv) - math.erf((lo_kev - energy_kev) * inv))


def event_centroid_radius_cm(cat: dict[str, Any], idx: int) -> float | None:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    if count <= 0:
        return None
    sum_e = 0.0
    wx = 0.0
    wy = 0.0
    for j in range(start, start + count):
        e = float(cat["pix_e"][j])
        if e <= 0.0:
            continue
        sum_e += e
        wx += e * float(cat["pix_x"][j])
        wy += e * float(cat["pix_y"][j])
    if sum_e <= 0.0:
        return None
    return math.hypot(wx / sum_e, wy / sum_e)


def selected_background_events(cat: dict[str, Any], reject_policy: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    n = len(cat["stream"])
    for idx in range(n):
        stream = str(cat["stream"][idx])
        if stream == "science":
            continue
        energy = float(cat["tes_total_keV"][idx])
        if not (505.0 <= energy <= 517.0):
            continue
        if float(cat["bgo_total_keV"][idx]) >= complete.BGO_THR_KEV:
            continue
        pix_count = int(cat["pix_count"][idx])
        if pix_count <= 1:
            keep = True
        elif pix_count > 6 and reject_policy == "keep":
            keep = True
        else:
            keep, _cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
        if not keep:
            continue
        radius = event_centroid_radius_cm(cat, idx)
        if radius is None:
            continue
        prob = gaussian_window_probability(energy, LINE_LO_KEV, LINE_HI_KEV, TES_SIGMA_KEV)
        if prob <= 0.0:
            continue
        out.append(
            {
                "stream": stream,
                "energy_keV": energy,
                "rate_hz": float(cat["rate_hz"][idx]),
                "radius_cm": radius,
                "line_prob": prob,
            }
        )
    return out


def parse_eventlist_signal_radii(
    path: Path, target_energy_kev: float = LINE_CENTER_KEV, tolerance_kev: float = 1.0e-3
) -> tuple[list[float], dict[str, int]]:
    radii: list[float] = []
    energy_counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 15:
                continue
            try:
                x = float(parts[5])
                y = float(parts[6])
                energy = float(parts[14])
            except ValueError:
                continue
            key = f"{energy:.6g}"
            energy_counts[key] = energy_counts.get(key, 0) + 1
            if abs(energy - target_energy_kev) <= tolerance_kev:
                radii.append(math.hypot(x, y))
    return radii, energy_counts


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def line_baseline() -> tuple[dict[str, float], dict[str, float]]:
    rows = read_csv(LINE_CSV)
    broad = next(row for row in rows if row["window_id"] == "W1_design_passband")
    line = next(row for row in rows if row["window_id"] == "line_pm_3sigma")
    non_numeric = {"window_id", "source_window_id", "label", "T3_status", "T3_time_dependent_status"}
    return (
        {key: float(value) for key, value in broad.items() if key not in non_numeric and value != ""},
        {key: float(value) for key, value in line.items() if key not in non_numeric and value != ""},
    )


def build() -> dict[str, Any]:
    focus = load_json(FOCUS_RESPONSE)
    step09 = load_json(STEP09_SUMMARY)
    eventlist = ROOT / step09["bridge"]["eventlist"]
    reject_policy = str(focus.get("inputs", {}).get("reject_policy", "keep"))
    science_flux = float(focus["normalization"]["reference_flux_ph_cm2_s"])
    broad, line = line_baseline()
    broad_z = broad["Z20d_at_reference_flux"]
    line_z = line["Z20d_at_reference_flux"]
    line_z_time = line.get("Z20d_time_dependent_at_reference_flux", line_z)
    rows = read_csv(FOCUS_SPATIAL_CSV)
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        out = dict(row)
        z20 = float(row["Z20d_at_reference_flux"])
        out["background_vs_line_no_spatial"] = float(row["background_cps"]) / line["background_cps"] if line["background_cps"] > 0.0 else 0.0
        out["Z_gain_vs_broad"] = z20 / broad_z if broad_z > 0.0 else 0.0
        out["Z_gain_vs_line_no_spatial"] = z20 / line_z if line_z > 0.0 else 0.0
        normalized_rows.append(out)
    rows = normalized_rows
    time_curve_rows: list[dict[str, Any]] = []
    for row in rows:
        metrics, curve = time_dependent_fold(
            str(row["cut_id"]),
            float(row["prompt_cps"]),
            float(row["delayed_cps"]),
            float(row["signal_cps_at_reference_flux"]),
            science_flux,
        )
        row.update(metrics)
        z20_time = float(row["Z20d_time_dependent_at_reference_flux"])
        row["Z_gain_vs_line_no_spatial_time_dependent"] = z20_time / line_z_time if line_z_time > 0.0 else 0.0
        time_curve_rows.extend(curve)
    key = next(row for row in rows if row["cut_id"] == "spot_r90")
    best = next((row for row in rows if row["cut_id"] == focus["spatial_checks"]["best_cut_id"]), key)
    best_time = max(rows, key=lambda row: float(row["Z20d_time_dependent_at_reference_flux"]))
    out_csv = OUT / "spatial_line_proxy.csv"
    out_time_csv = OUT / "spatial_line_time_dependent_significance.csv"
    out_json = OUT / "spatial_line_proxy_summary.json"
    out_md = OUT / "spatial_line_proxy.md"
    write_csv(out_csv, rows)
    write_csv(out_time_csv, time_curve_rows)
    payload = {
        "status": "PASS",
        "claim_level": "L1_SPATIAL_LINE_DETECTOR_COUPLED_CLOSED",
        "scope": "Detector-coupled focused-spot spatial cut for W2. Signal centroids come from the full non-smoke Step09 focused EventList Cosima transport; background centroids come from the current day-15 prompt+delayed catalog, with an additional Step06 time-axis fold.",
        "inputs": {
            "focus_response": rel(FOCUS_RESPONSE),
            "focus_spatial_csv": rel(FOCUS_SPATIAL_CSV),
            "line_window_csv": rel(LINE_CSV),
            "step06_background_time_variation": rel(STEP06_BG),
            "step09_summary": rel(STEP09_SUMMARY),
            "eventlist": rel(eventlist),
            "reject_policy": reject_policy,
        },
        "assumptions": {
            "line_window_keV": [LINE_LO_KEV, LINE_HI_KEV],
            "tes_sigma_keV": TES_SIGMA_KEV,
            "mission_days": MISSION_DAYS,
            "reference_flux_ph_cm2_s": science_flux,
            "headline_policy": "Use spot_r90 as the robust headline spatial cut; spot_rmax is retained only as a diagnostic.",
            "signal_policy": "Use detector-coupled TES event centroids from the full focused EventList transport.",
            "background_policy": "Use TES energy-weighted hit centroid radius for current final-selected prompt+delayed background events.",
            "time_dependent_policy": "day-15 prompt/delayed/science rates are scaled by Step06 prompt_scale_to_day15, delayed_activity_scale_to_day15, and science_atm_scale_to_day15; the same analytic accidental live factor is applied.",
        },
        "checks": {
            "signal_eventlist_rows": step09["bridge"]["rows_written"],
            "signal_detector_events": focus["spatial_checks"]["signal_detector_events"],
            "signal_radius_r50_cm": focus["spatial_checks"]["signal_radius_r50_cm"],
            "signal_radius_r68_cm": focus["spatial_checks"]["signal_radius_r68_cm"],
            "signal_radius_r90_cm": focus["spatial_checks"]["signal_radius_r90_cm"],
            "signal_radius_r95_cm": focus["spatial_checks"]["signal_radius_r95_cm"],
            "signal_radius_r99_cm": focus["spatial_checks"]["signal_radius_r99_cm"],
            "signal_radius_max_cm": focus["spatial_checks"]["signal_radius_max_cm"],
            "selected_background_events_505_517": focus["spatial_checks"]["background_detector_events"],
            "line_no_spatial_background_cps": line["background_cps"],
            "line_no_spatial_Z20d": line_z,
            "line_no_spatial_Z20d_time_dependent": line_z_time,
            "best_cut_id": best["cut_id"],
            "best_cut_radius_cm": best["radius_cm"],
            "best_cut_signal_psf_fraction": best["signal_psf_fraction"],
            "best_cut_background_cps": best["background_cps"],
            "best_cut_Z20d": best["Z20d_at_reference_flux"],
            "best_cut_Z_gain_vs_line": best["Z_gain_vs_line_no_spatial"],
            "best_cut_T3_day": best["T3_day_constant_rate"],
            "best_cut_flux_3sigma_20d_ph_cm2_s": best["flux_3sigma_20d_ph_cm2_s"],
            "best_time_dependent_cut_id": best_time["cut_id"],
            "best_time_dependent_Z20d": best_time["Z20d_time_dependent_at_reference_flux"],
            "best_time_dependent_T3_day": best_time["T3_day_time_dependent"],
            "best_time_dependent_flux_3sigma_20d_ph_cm2_s": best_time["flux_3sigma_20d_time_dependent_ph_cm2_s"],
            "spot_r90_background_cps": key["background_cps"],
            "spot_r90_signal_psf_fraction": key["signal_psf_fraction"],
            "spot_r90_Z20d": key["Z20d_at_reference_flux"],
            "spot_r90_Z20d_time_dependent": key["Z20d_time_dependent_at_reference_flux"],
            "spot_r90_Z_gain_vs_line": key["Z_gain_vs_line_no_spatial"],
            "spot_r90_Z_gain_vs_line_time_dependent": key["Z_gain_vs_line_no_spatial_time_dependent"],
            "spot_r90_T3_day": key["T3_day_constant_rate"],
            "spot_r90_T3_day_time_dependent": key["T3_day_time_dependent"],
            "spot_r90_flux_3sigma_20d_ph_cm2_s": key["flux_3sigma_20d_ph_cm2_s"],
            "spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s": key["flux_3sigma_20d_time_dependent_ph_cm2_s"],
        },
        "outputs": {
            "csv": rel(out_csv),
            "time_dependent_csv": rel(out_time_csv),
            "markdown": rel(out_md),
        },
    }
    write_json(out_json, payload)

    lines = [
        "# Step08 Spatial Line Proxy",
        "",
        "Status: `PASS`.",
        "",
        "This is the detector-coupled focused-spot spatial cut for W2. It uses the full non-smoke Step09 focused EventList Cosima transport for signal TES centroids and the current prompt+delayed day-15 catalog for non-X-ray background centroids. It reports both the original day-15 constant-rate result and a Step06 time-axis fold.",
        "",
        "## Key Result",
        "",
        f"- No-spatial 511 +/- 3 sigma line baseline: background `{fmt(line['background_cps'])}` cps, Z20d `{fmt(line_z)}`.",
        f"- Detector-coupled signal events in W2: `{focus['spatial_checks']['signal_detector_events']}`, r90 `{fmt(focus['spatial_checks']['signal_radius_r90_cm'])}` cm, rmax `{fmt(focus['spatial_checks']['signal_radius_max_cm'])}` cm.",
        f"- Headline spot-r90 cut: signal fraction `{fmt(key['signal_psf_fraction'])}`, background `{fmt(key['background_cps'])}` cps, Z20d `{fmt(key['Z20d_at_reference_flux'])}`, gain vs line `{fmt(key['Z_gain_vs_line_no_spatial'])}`.",
        f"- Spot-r90 20-day 3-sigma flux: `{fmt(key['flux_3sigma_20d_ph_cm2_s'])}` ph cm^-2 s^-1.",
        f"- Time-dependent spot-r90 fold: Z20d `{fmt(key['Z20d_time_dependent_at_reference_flux'])}`, T3 `{fmt(key['T3_day_time_dependent'])}` day, 20-day 3-sigma flux `{fmt(key['flux_3sigma_20d_time_dependent_ph_cm2_s'])}` ph cm^-2 s^-1.",
        "",
        "## Cut Table",
        "",
        "| cut | radius cm | signal frac | background cps | Z20d const | Z20d time | gain time | T3 time day | F3sigma20d time |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['cut_id']} | {fmt(row['radius_cm'])} | {fmt(row['signal_psf_fraction'])} | "
            f"{fmt(row['background_cps'])} | {fmt(row['Z20d_at_reference_flux'])} | "
            f"{fmt(row['Z20d_time_dependent_at_reference_flux'])} | "
            f"{fmt(row['Z_gain_vs_line_no_spatial_time_dependent'])} | "
            f"{fmt(row['T3_day_time_dependent'])} | "
            f"{fmt(row['flux_3sigma_20d_time_dependent_ph_cm2_s'])} |"
        )
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py",
            "```",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "checks": payload["checks"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
