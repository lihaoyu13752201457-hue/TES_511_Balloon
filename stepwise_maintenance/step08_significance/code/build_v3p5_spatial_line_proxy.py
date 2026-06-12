#!/usr/bin/env python3
"""Build the v3p5 fullstat focused-spot W2 spatial sidecar."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_v3p5_centerfinger_fullstat_v2_spatial"
DETECTOR_RESPONSE = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_focus_response.json"
)
SPATIAL_CSV = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_spatial_line_cuts.csv"
)
STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / "outputs_v3p5_centerfinger_fullstat_v2_l1"
    / "step05_v3p5_centerfinger_l1_response_summary.json"
)
STEP06_BG = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "background_time_variation.csv"
)
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step08_v3p5_centerfinger_time_dependent_summary.json"
)

SECONDS_PER_DAY = 86400.0
MISSION_DAYS = 20.0
W2_SELECTION = "w2_510p58_511p42"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def fmt(value: Any, ndigits: int = 6) -> str:
    if value in ("", None):
        return ""
    x = float(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def crossing_time(days: list[float], zvals: list[float], threshold: float) -> float | None:
    for idx, value in enumerate(zvals):
        if value < threshold:
            continue
        if idx == 0:
            return days[0]
        x0, x1 = days[idx - 1], days[idx]
        y0, y1 = zvals[idx - 1], zvals[idx]
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def extrapolated_time_days(final_day: float, final_z: float, threshold: float) -> float | None:
    if final_z <= 0.0:
        return None
    if final_z >= threshold:
        return final_day
    return final_day * (threshold / final_z) ** 2


def fold_cut(cut: dict[str, Any], bg_rows: list[dict[str, str]], tau_s: float, reference_flux: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = [row for row in bg_rows if row["selection_id"] == W2_SELECTION]
    rows.sort(key=lambda row: int(row["time_bin_id"]))
    cumulative_source = 0.0
    cumulative_background = 0.0
    elapsed = 0.0
    days: list[float] = []
    zvals: list[float] = []
    curve: list[dict[str, Any]] = []
    for row in rows:
        dt_s = f(row, "dt_s")
        prompt_scale = f(row, "prompt_scale_to_day15")
        delayed_scale = f(row, "delayed_activity_scale_to_day15")
        science_scale = f(row, "science_atm_scale_to_day15")
        occupancy_hz = f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")
        live = math.exp(-occupancy_hz * tau_s)
        source = f(cut, "signal_cps_at_reference_flux") * science_scale * live
        background = (f(cut, "prompt_cps") * prompt_scale + f(cut, "delayed_cps") * delayed_scale) * live
        cumulative_source += source * dt_s
        cumulative_background += background * dt_s
        elapsed += dt_s
        day = elapsed / SECONDS_PER_DAY
        z = cumulative_source / math.sqrt(cumulative_background) if cumulative_background > 0.0 else 0.0
        days.append(day)
        zvals.append(z)
        curve.append(
            {
                "cut_id": cut["cut_id"],
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "elapsed_stop_day": day,
                "dt_s": dt_s,
                "prompt_scale_to_day15": prompt_scale,
                "delayed_activity_scale_to_day15": delayed_scale,
                "science_atm_scale_to_day15": science_scale,
                "accidental_live_factor": live,
                "source_cps": source,
                "background_cps": background,
                "cumulative_source_counts": cumulative_source,
                "cumulative_background_counts": cumulative_background,
                "counting_Z": z,
            }
        )
    final_day = days[-1] if days else 0.0
    final_z = zvals[-1] if zvals else 0.0
    t3 = crossing_time(days, zvals, 3.0)
    t5 = crossing_time(days, zvals, 5.0)
    metrics = {
        **cut,
        "Z20d_time_dependent_at_reference_flux": final_z,
        "T3_day_time_dependent": t3 if t3 is not None else extrapolated_time_days(final_day, final_z, 3.0),
        "T5_day_time_dependent": t5 if t5 is not None else extrapolated_time_days(final_day, final_z, 5.0),
        "T3_time_dependent_status": "mission_internal_crossing" if t3 is not None else "extrapolated_beyond_20d",
        "T5_time_dependent_status": "mission_internal_crossing" if t5 is not None else "extrapolated_beyond_20d",
        "flux_3sigma_20d_time_dependent_ph_cm2_s": reference_flux * 3.0 / final_z if final_z > 0.0 else math.inf,
        "total_source_counts_time_dependent": cumulative_source,
        "total_background_counts_time_dependent": cumulative_background,
    }
    return metrics, curve


def build() -> dict[str, Any]:
    detector = load_json(DETECTOR_RESPONSE)
    step05 = load_json(STEP05)
    step08 = load_json(STEP08)
    spatial_rows = read_csv(SPATIAL_CSV)
    bg_rows = read_csv(STEP06_BG)
    reference_flux = float(step05["science_physical_normalization"]["reference_flux_ph_cm2_s"])
    tau = float(step05["normalization"]["coincidence_window_s"])
    current_w2_z = float(step08["checks"]["A_reference_w2_Z20d_time_dependent"])

    rows: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    for cut in spatial_rows:
        metrics, curve = fold_cut(cut, bg_rows, tau, reference_flux)
        rows.append(metrics)
        curves.extend(curve)
    spot = next(row for row in rows if row["cut_id"] == "spot_r90")
    best = max([row for row in rows if row["cut_id"] not in {"spot_rmax", "full_aperture_1p8"}], key=lambda row: f(row, "Z20d_time_dependent_at_reference_flux"))

    out_csv = OUT / "v3p5_spatial_line_proxy.csv"
    out_curve = OUT / "v3p5_spatial_line_time_dependent.csv"
    out_json = OUT / "v3p5_spatial_line_proxy_summary.json"
    out_md = OUT / "v3p5_spatial_line_proxy.md"
    write_csv(out_csv, rows)
    write_csv(out_curve, curves)
    payload = {
        "status": "PASS_V3P5_FULLSTAT_SPATIAL_LINE_PROXY",
        "claim_level": "V3P5_L1_SPATIAL_LINE_FULLSTAT_V2_SIDECAR",
        "scope": "Detector-coupled v3p5 fullstat W2 focused-spot spatial sidecar. This is a post-processing sidecar and does not replace the current W2 counting authority.",
        "inputs": {
            "detector_response": rel(DETECTOR_RESPONSE),
            "spatial_csv": rel(SPATIAL_CSV),
            "step05_summary": rel(STEP05),
            "step06_background_time_variation": rel(STEP06_BG),
            "step08_w2_authority": rel(STEP08),
        },
        "checks": {
            "signal_radius_r90_cm": f(spot, "radius_cm"),
            "spot_r90_signal_psf_fraction": f(spot, "signal_psf_fraction"),
            "spot_r90_prompt_cps": f(spot, "prompt_cps"),
            "spot_r90_delayed_cps": f(spot, "delayed_cps"),
            "spot_r90_background_cps": f(spot, "background_cps"),
            "spot_r90_signal_cps_at_reference_flux": f(spot, "signal_cps_at_reference_flux"),
            "spot_r90_Z20d_constant_rate": f(spot, "Z20d_at_reference_flux"),
            "spot_r90_Z20d_time_dependent": f(spot, "Z20d_time_dependent_at_reference_flux"),
            "spot_r90_T3_day_time_dependent": f(spot, "T3_day_time_dependent"),
            "spot_r90_T5_day_time_dependent": f(spot, "T5_day_time_dependent"),
            "spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s": f(spot, "flux_3sigma_20d_time_dependent_ph_cm2_s"),
            "spot_r90_gain_vs_current_w2_time_dependent": f(spot, "Z20d_time_dependent_at_reference_flux") / current_w2_z if current_w2_z > 0.0 else 0.0,
            "best_time_dependent_cut_id": best["cut_id"],
            "best_time_dependent_Z20d": f(best, "Z20d_time_dependent_at_reference_flux"),
            "detector_response_W2_Z20d_constant_rate": detector["window_checks"]["W2_511_pm_420eV"]["Z20d_both"],
            "current_w2_authority_Z20d_time_dependent": current_w2_z,
        },
        "outputs": {
            "summary_json": rel(out_json),
            "markdown": rel(out_md),
            "csv": rel(out_csv),
            "time_dependent_csv": rel(out_curve),
        },
        "limitations": [
            "Gaussian TES line-window sidecar; current v3p5 W2 authority remains the hard-window Step05/Step08 counting chain.",
            "No profile likelihood gain is claimed.",
            "Delayed source remains the RadialProfileBeam-compressed source.",
        ],
    }
    write_json(out_json, payload)
    lines = [
        "# v3p5 Fullstat Spatial Line Proxy",
        "",
        "Status: `PASS_V3P5_FULLSTAT_SPATIAL_LINE_PROXY`.",
        "",
        "This sidecar applies detector-coupled focused-spot spatial cuts to the v3p5 fullstat W2 line response and folds the day-15 rates through the Step06 time axis.",
        "",
        "## Headline",
        "",
        f"- `spot_r90` radius: `{fmt(spot['radius_cm'])}` cm; signal PSF fraction `{fmt(spot['signal_psf_fraction'])}`.",
        f"- `spot_r90` background: `{fmt(spot['background_cps'])}` cps (`prompt={fmt(spot['prompt_cps'])}`, `delayed={fmt(spot['delayed_cps'])}`).",
        f"- `spot_r90` time-dependent Z20d: `{fmt(spot['Z20d_time_dependent_at_reference_flux'])}`; T3 `{fmt(spot['T3_day_time_dependent'])}` day.",
        f"- `spot_r90` 20-day 3-sigma flux: `{fmt(spot['flux_3sigma_20d_time_dependent_ph_cm2_s'])}` ph cm^-2 s^-1.",
        f"- Gain vs current v3p5 W2 counting authority: `{fmt(payload['checks']['spot_r90_gain_vs_current_w2_time_dependent'])}`.",
        "",
        "## Cut Table",
        "",
        "| cut | radius cm | signal frac | background cps | Z20d const | Z20d time | T3 time day | F3sigma20d time |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['cut_id']} | {fmt(row['radius_cm'])} | {fmt(row['signal_psf_fraction'])} | "
            f"{fmt(row['background_cps'])} | {fmt(row['Z20d_at_reference_flux'])} | "
            f"{fmt(row['Z20d_time_dependent_at_reference_flux'])} | {fmt(row['T3_day_time_dependent'])} | "
            f"{fmt(row['flux_3sigma_20d_time_dependent_ph_cm2_s'])} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This is a sidecar, not a replacement for the current hard-window W2 authority.",
            "- No spatial/profile likelihood gain is applied.",
            "- Exact-position delayed-source sampling remains pending.",
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step08_significance/code/build_v3p5_spatial_line_proxy.py",
            "```",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "checks": payload["checks"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
