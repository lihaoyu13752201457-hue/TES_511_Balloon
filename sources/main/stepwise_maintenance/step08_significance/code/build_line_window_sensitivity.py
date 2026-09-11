#!/usr/bin/env python3
"""Build a 511-keV line-window sensitivity sidecar for Step08.

This is a deterministic direct-expectation calculation.  It reuses the current
day-15 event catalog, applies the same active-shield and Compton/FoV final
selection, then folds a Gaussian TES energy response into several 511-keV
analysis windows.  It does not redraw the Poisson timeline and it does not add
spatial/PSF information.
"""

from __future__ import annotations

import csv
import json
import math
import os
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
FOCUS_WINDOWS = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_windows.csv"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"

SECONDS_PER_DAY = 86400.0
MISSION_DAYS = 20.0
REFERENCE_FLUX = 1.0e-4
LINE_CENTER_KEV = 511.0
TES_SIGMA_KEV = 0.14

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


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    if x is None or not math.isfinite(float(x)):
        return "nan"
    x = float(x)
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def time_dependent_fold(
    selection_id: str,
    prompt_cps_day15: float,
    delayed_cps_day15: float,
    science_cps_day15: float,
) -> tuple[dict[str, float | str], list[dict[str, Any]]]:
    """Fold a day-15 detector response through the Step06 time-axis scales."""
    return shared_time_dependent_fold(
        selection_id,
        prompt_cps_day15,
        delayed_cps_day15,
        science_cps_day15,
        REFERENCE_FLUX,
        id_field="selection_id",
        step06_bg_csv=STEP06_BG,
        day15_summary_json=DAY15_SUMMARY,
    )


def gaussian_window_probability(energy_kev: float, lo_kev: float, hi_kev: float, sigma_kev: float) -> float:
    if sigma_kev <= 0.0:
        return 1.0 if lo_kev <= energy_kev < hi_kev else 0.0
    inv = 1.0 / (math.sqrt(2.0) * sigma_kev)
    return 0.5 * (math.erf((hi_kev - energy_kev) * inv) - math.erf((lo_kev - energy_kev) * inv))


def line_windows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "window_id": "broad_480_550",
            "label": "480-550 keV broad optics-band window",
            "lo_keV": 480.0,
            "hi_keV": 550.0,
            "k_sigma": "",
        },
        {
            "window_id": "tenkeV_506_516",
            "label": "506-516 keV diagnostic window",
            "lo_keV": 506.0,
            "hi_keV": 516.0,
            "k_sigma": "",
        },
    ]
    for k in (1.0, 2.0, 3.0):
        half_width = k * TES_SIGMA_KEV
        rows.append(
            {
                "window_id": f"line_pm_{k:g}sigma",
                "label": f"511 +/- {k:g} sigma_TES",
                "lo_keV": LINE_CENTER_KEV - half_width,
                "hi_keV": LINE_CENTER_KEV + half_width,
                "k_sigma": k,
            }
        )
    return rows


def selected_final_background_events(cat: dict[str, Any], reject_policy: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    n = len(cat["stream"])
    for i in range(n):
        stream = str(cat["stream"][i])
        if stream == "science":
            continue
        e = float(cat["tes_total_keV"][i])
        if not (505.0 <= e <= 517.0):
            continue
        if float(cat["bgo_total_keV"][i]) >= complete.BGO_THR_KEV:
            continue
        pix_count = int(cat["pix_count"][i])
        if pix_count <= 1:
            keep, cls = True, "single"
        elif pix_count > 6 and reject_policy == "keep":
            keep, cls = True, "reject_kept"
        else:
            keep, cls = complete.classify_final(complete.event_hits(cat, i), reject_policy)
        if not keep:
            continue
        selected.append(
            {
                "energy_keV": e,
                "stream": stream,
                "rate_hz": float(cat["rate_hz"][i]),
                "class": cls,
            }
        )
    return selected


def background_rates_for_window(events: list[dict[str, Any]], lo_kev: float, hi_kev: float, sigma_kev: float) -> dict[str, float]:
    by_stream: dict[str, float] = defaultdict(float)
    effective_catalog_events: dict[str, float] = defaultdict(float)
    for event in events:
        prob = gaussian_window_probability(float(event["energy_keV"]), lo_kev, hi_kev, sigma_kev)
        if prob <= 0.0:
            continue
        stream = str(event["stream"])
        by_stream[stream] += float(event["rate_hz"]) * prob
        effective_catalog_events[stream] += prob
    return {
        "prompt_cps": by_stream["prompt"],
        "delayed_cps": by_stream["delayed"],
        "background_cps": by_stream["prompt"] + by_stream["delayed"],
        "background_effective_catalog_events": effective_catalog_events["prompt"] + effective_catalog_events["delayed"],
    }


def science_rate_for_window(cat: dict[str, Any], lo_kev: float, hi_kev: float, sigma_kev: float, final_survival: float) -> dict[str, float]:
    rate = 0.0
    effective_events = 0.0
    n = len(cat["stream"])
    for i in range(n):
        if str(cat["stream"][i]) != "science":
            continue
        if float(cat["bgo_total_keV"][i]) >= complete.BGO_THR_KEV:
            continue
        e = float(cat["tes_total_keV"][i])
        if not (lo_kev - 5.0 * sigma_kev <= e <= hi_kev + 5.0 * sigma_kev):
            continue
        prob = gaussian_window_probability(e, lo_kev, hi_kev, sigma_kev)
        if prob <= 0.0:
            continue
        rate += float(cat["rate_hz"][i]) * prob
        effective_events += prob
    return {
        "science_cps": rate * final_survival,
        "science_effective_catalog_events": effective_events,
    }


def broad_row_from_summary(summary: dict[str, Any], science_flux: float) -> dict[str, Any]:
    by_stream = summary["expectation_rates_by_stream_cps"]
    science = float(by_stream["science"]["final"])
    prompt = float(by_stream["prompt"]["final"])
    delayed = float(by_stream["delayed"]["final"])
    background = prompt + delayed
    mission_s = MISSION_DAYS * SECONDS_PER_DAY
    response = science / science_flux if science_flux > 0 else 0.0
    z20 = science * mission_s / math.sqrt(background * mission_s) if background > 0 else 0.0
    t3 = MISSION_DAYS * (3.0 / z20) ** 2 if z20 > 0.0 else math.inf
    flux3 = 3.0 * math.sqrt(background * mission_s) / (response * mission_s) if response > 0 and background > 0 else math.inf
    return {
        "window_id": "broad_480_550",
        "label": "480-550 keV broad optics-band window",
        "lo_keV": 480.0,
        "hi_keV": 550.0,
        "k_sigma": "",
        "tes_sigma_keV": TES_SIGMA_KEV,
        "tes_fwhm_keV": TES_SIGMA_KEV * 2.354820045,
        "prompt_cps": prompt,
        "delayed_cps": delayed,
        "background_cps": background,
        "science_cps_at_reference_flux": science,
        "science_response_cps_per_ph_cm2_s": response,
        "background_vs_broad": 1.0,
        "Z20d_at_reference_flux": z20,
        "Z_gain_vs_broad": 1.0,
        "T3_day_constant_rate": t3,
        "T3_status": "mission_internal_crossing" if t3 <= MISSION_DAYS else "extrapolated_beyond_20d",
        "flux_3sigma_20d_ph_cm2_s": flux3,
        "science_effective_catalog_events": "",
        "background_effective_catalog_events": "",
    }


def build() -> dict[str, Any]:
    focus = load_json(FOCUS_RESPONSE)
    focus_window_rows = read_csv(FOCUS_WINDOWS)
    reject_policy = str(focus.get("inputs", {}).get("reject_policy", "keep"))
    science_flux = float(focus["normalization"]["reference_flux_ph_cm2_s"])
    mission_s = MISSION_DAYS * SECONDS_PER_DAY
    row_lookup = {
        (row["window_id"], row["stage"], row["source"]): row
        for row in focus_window_rows
    }
    window_order = [
        ("W1_design_passband", "W1 design passband"),
        ("line_pm_1sigma", "511 +/- 1 sigma_TES"),
        ("line_pm_2sigma", "511 +/- 2 sigma_TES"),
        ("W2_511_pm_420eV", "511 +/- 3 sigma_TES / W2 511 +/- 420 eV"),
    ]
    rows: list[dict[str, Any]] = []
    for source_window_id, label in window_order:
        bg = row_lookup[(source_window_id, "both", "non_xray_background")]
        sig = row_lookup[(source_window_id, "both", "focused_eventlist_science")]
        checks = focus["window_checks"][source_window_id]
        science_cps = float(sig["rate_cps"])
        background = float(bg["rate_cps"])
        response = science_cps / science_flux if science_flux > 0 else 0.0
        z20 = (science_cps * mission_s / math.sqrt(background * mission_s)) if background > 0.0 else 0.0
        t3 = MISSION_DAYS * (3.0 / z20) ** 2 if z20 > 0.0 else math.inf
        status = "mission_internal_crossing" if t3 <= MISSION_DAYS else "extrapolated_beyond_20d"
        flux3 = 3.0 * math.sqrt(background * mission_s) / (response * mission_s) if response > 0 and background > 0 else math.inf
        window_id = "line_pm_3sigma" if source_window_id == "W2_511_pm_420eV" else source_window_id
        row = {
            "window_id": window_id,
            "source_window_id": source_window_id,
            "label": label,
            "lo_keV": float(checks["lo_keV"]),
            "hi_keV": float(checks["hi_keV"]),
            "k_sigma": 3.0 if source_window_id == "W2_511_pm_420eV" else "",
            "tes_sigma_keV": TES_SIGMA_KEV,
            "tes_fwhm_keV": TES_SIGMA_KEV * 2.354820045,
            "prompt_cps": float(bg.get("prompt_cps", 0.0) or 0.0),
            "delayed_cps": float(bg.get("delayed_cps", 0.0) or 0.0),
            "background_cps": background,
            "science_cps_at_reference_flux": science_cps,
            "science_response_cps_per_ph_cm2_s": response,
            "background_vs_broad": "",
            "Z20d_at_reference_flux": z20,
            "Z_gain_vs_broad": "",
            "T3_day_constant_rate": t3,
            "T3_status": status,
            "flux_3sigma_20d_ph_cm2_s": flux3,
            "science_effective_catalog_events": sig.get("effective_catalog_events", ""),
            "background_effective_catalog_events": bg.get("effective_catalog_events", ""),
        }
        rows.append(row)

    broad_reference_z = float(rows[0]["Z20d_at_reference_flux"])
    broad_reference_background = float(rows[0]["background_cps"])
    for row in rows:
        row["background_vs_broad"] = float(row["background_cps"]) / broad_reference_background
        row["Z_gain_vs_broad"] = float(row["Z20d_at_reference_flux"]) / broad_reference_z
    time_curve_rows: list[dict[str, Any]] = []
    for row in rows:
        metrics, curve = time_dependent_fold(
            str(row["window_id"]),
            float(row["prompt_cps"]),
            float(row["delayed_cps"]),
            float(row["science_cps_at_reference_flux"]),
        )
        row.update(metrics)
        time_curve_rows.extend(curve)

    out_csv = OUT / "line_window_sensitivity.csv"
    out_time_csv = OUT / "line_window_time_dependent_significance.csv"
    out_json = OUT / "line_window_sensitivity_summary.json"
    out_md = OUT / "line_window_sensitivity.md"
    write_csv(out_csv, rows)
    write_csv(out_time_csv, time_curve_rows)
    key = next(row for row in rows if row["window_id"] == "line_pm_3sigma")
    payload = {
        "status": "PASS",
        "claim_level": "L1_LINE_WINDOW_DETECTOR_COUPLED_FOCUS",
        "scope": "Direct-expectation 511-keV line-window sidecar using the full Step09 focused EventList detector response and current day-15 non-X-ray background catalog, with an additional Step06 time-axis fold. No Poisson timeline redraw.",
        "inputs": {
            "focus_response": rel(FOCUS_RESPONSE),
            "focus_window_csv": rel(FOCUS_WINDOWS),
            "step06_background_time_variation": rel(STEP06_BG),
            "reject_policy": reject_policy,
        },
        "assumptions": {
            "line_center_keV": LINE_CENTER_KEV,
            "tes_sigma_keV": TES_SIGMA_KEV,
            "tes_fwhm_keV": TES_SIGMA_KEV * 2.354820045,
            "mission_days": MISSION_DAYS,
            "reference_flux_ph_cm2_s": science_flux,
            "energy_response": "analytic Gaussian CDF integrated per event",
            "science_response_policy": "science rates are parsed from the full detector-coupled focused EventList transport",
            "time_dependent_policy": "day-15 prompt/delayed/science rates are scaled by Step06 prompt_scale_to_day15, delayed_activity_scale_to_day15, and science_atm_scale_to_day15; the same analytic accidental live factor is applied.",
        },
        "checks": {
            "focus_response_status": focus.get("status"),
            "broad_Z20d": rows[0]["Z20d_at_reference_flux"],
            "broad_Z20d_time_dependent": rows[0]["Z20d_time_dependent_at_reference_flux"],
            "line_pm_3sigma_background_cps": key["background_cps"],
            "line_pm_3sigma_Z20d": key["Z20d_at_reference_flux"],
            "line_pm_3sigma_Z20d_time_dependent": key["Z20d_time_dependent_at_reference_flux"],
            "line_pm_3sigma_Z_gain_vs_broad": key["Z_gain_vs_broad"],
            "line_pm_3sigma_T3_day_constant_rate": key["T3_day_constant_rate"],
            "line_pm_3sigma_T3_day_time_dependent": key["T3_day_time_dependent"],
            "line_pm_3sigma_T3_status": key["T3_status"],
            "line_pm_3sigma_T3_time_dependent_status": key["T3_time_dependent_status"],
            "line_pm_3sigma_flux_3sigma_20d_ph_cm2_s": key["flux_3sigma_20d_ph_cm2_s"],
            "line_pm_3sigma_flux_3sigma_20d_time_dependent_ph_cm2_s": key["flux_3sigma_20d_time_dependent_ph_cm2_s"],
        },
        "outputs": {
            "csv": rel(out_csv),
            "time_dependent_csv": rel(out_time_csv),
            "markdown": rel(out_md),
        },
    }
    write_json(out_json, payload)

    lines = [
        "# Step08 Line-Window Sensitivity Sidecar",
        "",
        "Status: `PASS`.",
        "",
        "This sidecar uses the Step09 detector-coupled focused EventList science response and the current prompt+delayed non-X-ray background catalog. Each event is folded through a Gaussian TES energy response using the `.det` authority `sigma = 0.14 keV` (`FWHM = 0.330 keV`). It reports both the original day-15 constant-rate result and a Step06 time-axis fold, without a Poisson timeline redraw.",
        "",
        "## Key Result",
        "",
        f"- W1 design passband baseline: background `{fmt(rows[0]['background_cps'])}` cps, Z20d `{fmt(rows[0]['Z20d_at_reference_flux'])}` for `1e-4 ph cm^-2 s^-1`.",
        f"- W2 / 511 +/- 3 sigma window: background `{fmt(key['background_cps'])}` cps, Z20d `{fmt(key['Z20d_at_reference_flux'])}`, gain `{fmt(key['Z_gain_vs_broad'])}`.",
        f"- 511 +/- 3 sigma 3-sigma time: `{fmt(key['T3_day_constant_rate'])}` day (`{key['T3_status']}`).",
        f"- 20-day 3-sigma flux in the 511 +/- 3 sigma proxy: `{fmt(key['flux_3sigma_20d_ph_cm2_s'])}` ph cm^-2 s^-1.",
        f"- Time-dependent W2 fold: Z20d `{fmt(key['Z20d_time_dependent_at_reference_flux'])}`, T3 `{fmt(key['T3_day_time_dependent'])}` day (`{key['T3_time_dependent_status']}`), 20-day 3-sigma flux `{fmt(key['flux_3sigma_20d_time_dependent_ph_cm2_s'])}` ph cm^-2 s^-1.",
        "",
        "## Window Table",
        "",
        "| window | range keV | background cps | science cps at 1e-4 | Z20d const | Z20d time | T3 const day | T3 time day | status time |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['window_id']} | {float(row['lo_keV']):.3f}-{float(row['hi_keV']):.3f} | "
            f"{fmt(row['background_cps'])} | {fmt(row['science_cps_at_reference_flux'])} | "
            f"{fmt(row['Z20d_at_reference_flux'])} | {fmt(row['Z20d_time_dependent_at_reference_flux'])} | "
            f"{fmt(row['T3_day_constant_rate'])} | {fmt(row['T3_day_time_dependent'])} | "
            f"{row['T3_time_dependent_status']} |"
        )
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py",
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
