#!/usr/bin/env python3
"""Estimate the focused-aperture gamma background as a separate rate ledger.

This is intentionally a Level-1 addendum: it uses the existing optics
acceptance, local atmospheric-gamma directional spectra, and measured
post-optics detector efficiency.  It does not rewrite or reweight the direct
full-sphere prompt-background stream, which avoids double counting.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import fmean


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT = R2 / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background"

WINDOWS = {
    "line_510p3_511p8": (510.3, 511.8),
    "broad_480_550": (480.0, 550.0),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def interp_linear(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo = 0
    hi = len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    dx = xs[hi] - xs[lo]
    if dx <= 0:
        return ys[lo]
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / dx


def integrate_window_fraction(path: Path, emin: float, emax: float) -> float:
    energies: list[float] = []
    pdf: list[float] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            energies.append(float(parts[0]))
            pdf.append(float(parts[1]))

    if len(energies) < 2:
        raise ValueError(f"not enough spectrum samples in {path}")
    if emax <= energies[0] or emin >= energies[-1]:
        return 0.0

    lo = max(emin, energies[0])
    hi = min(emax, energies[-1])
    grid = [lo]
    grid.extend(e for e in energies if lo < e < hi)
    grid.append(hi)

    area = 0.0
    last_x = grid[0]
    last_y = interp_linear(energies, pdf, last_x)
    for x in grid[1:]:
        y = interp_linear(energies, pdf, x)
        area += 0.5 * (last_y + y) * (x - last_x)
        last_x = x
        last_y = y
    return max(area, 0.0)


def load_gamma_direction_bins() -> list[dict[str, object]]:
    manifest = read_csv(ROOT / "expacs_fullsphere_20bin_sources" / "manifest.csv")
    rows: list[dict[str, object]] = []
    for row in manifest:
        if row.get("particle") != "gamma":
            continue
        spectrum_path = ROOT / row["cosima_spectrum_path"]
        fractions = {
            name: integrate_window_fraction(spectrum_path, emin, emax)
            for name, (emin, emax) in WINDOWS.items()
        }
        rows.append(
            {
                "bin_id": int(row["bin_id"]),
                "theta_mid_deg": float(row["theta_mid_deg"]),
                "theta_min_deg": float(row["theta_min_deg"]),
                "theta_max_deg": float(row["theta_max_deg"]),
                "integral_per_sr_cm2_s": float(row["integral_per_sr_cm2_s"]),
                "spectrum_path": row["cosima_spectrum_path"],
                "fractions": fractions,
            }
        )
    rows.sort(key=lambda item: item["theta_mid_deg"])
    return rows


def nearest_direction_bin(theta_deg: float, rows: list[dict[str, object]]) -> dict[str, object]:
    return min(rows, key=lambda item: abs(float(item["theta_mid_deg"]) - theta_deg))


def load_optics_config() -> dict[str, float]:
    summary_path = ROOT / "docs" / "summary.json"
    with summary_path.open(encoding="utf-8") as f:
        data = json.load(f)
    optics = data.get("optics") or data.get("metrics") or data.get("config")
    config = data.get("config", {})
    metrics = data.get("metrics", {})
    return {
        "effective_area_cm2": float(optics["effective_area_cm2_at_511"]),
        "field_of_view_radius_arcmin": float(optics["field_of_view_radius_arcmin"]),
        "target_spot_diameter_mm": float(optics.get("target_spot_diameter_mm", config.get("target_spot_diameter_mm"))),
        "r95_diameter_mm": float(
            optics.get("r95_diameter_mm", optics.get("measured_r95_diameter_mm", metrics.get("measured_r95_diameter_mm")))
        ),
    }


def detector_efficiency_from_science_ledger() -> dict[str, float]:
    authority = R2 / "02_PHASE2_CORE_MATERIALS" / "authorities" / "complete_day15_summary.json"
    with authority.open(encoding="utf-8") as f:
        summary = json.load(f)
    normalization = summary.get("normalization", summary)
    sensitivity = summary.get("science_sensitivity", summary)
    reference_flux = float(normalization.get("science_flux_ph_cm2_s", 1.0e-4))
    injection_rate = float(normalization["science_injection_rate_s^-1"])
    final_rate = float(
        sensitivity.get(
            "science_reference_final_cps",
            float(sensitivity["science_final_response_cps_per_ph_cm-2_s-1"]) * reference_flux,
        )
    )
    return {
        "science_injection_rate_s^-1": injection_rate,
        "science_reference_flux_ph_cm2_s": reference_flux,
        "science_final_rate_cps_at_reference_flux": final_rate,
        "post_optics_transport_efficiency": final_rate / injection_rate if injection_rate > 0 else 0.0,
    }


def load_gamma_scales() -> dict[str, float]:
    rows = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "environment_grid" / "particle_scale_by_time.csv")
    scales: dict[str, float] = {}
    for row in rows:
        if row["particle"] == "gamma":
            scales[row["time_bin_id"]] = float(row.get("scale_factor", row.get("scale", 1.0)))
    return scales


def load_old_background_rates() -> dict[str, dict[str, float]]:
    path = R2 / "02_PHASE2_CORE_MATERIALS" / "likelihood_profiled" / "asimov_profiled_sensitivity.csv"
    rows = read_csv(path)
    selected: dict[str, dict[str, float]] = {}
    for row in rows:
        if float(row.get("exposure_s", 0.0)) != 1000000.0:
            continue
        model = row.get("model", row.get("mode", ""))
        if model != "window_counting_same_events":
            continue
        window = row.get("energy_window", "")
        if window in WINDOWS:
            selected[window] = {
                "old_background_cps": float(row["background_cps"]),
                "old_threshold_flux_ph_cm2_s": float(row.get("profiled_flux_3sigma_ph_cm2_s", row["flux_3sigma_ph_cm2_s"])),
            }
    return selected


def make_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    optics = load_optics_config()
    efficiency = detector_efficiency_from_science_ledger()
    gamma_bins = load_gamma_direction_bins()
    gamma_scales = load_gamma_scales()
    old_background = load_old_background_rates()
    transmission = read_csv(
        R2 / "02_PHASE2_CORE_MATERIALS" / "environment_grid" / "science_atmospheric_transmission.csv"
    )

    fov_radius_rad = optics["field_of_view_radius_arcmin"] * math.pi / (180.0 * 60.0)
    omega_opt_sr = math.pi * fov_radius_rad * fov_radius_rad
    eps = efficiency["post_optics_transport_efficiency"]

    timeseries: list[dict[str, object]] = []
    for row in transmission:
        time_bin = row["time_bin_id"]
        source_zenith = float(row["source_zenith_deg"])
        horizon = float(row["horizon_zenith_deg"])
        visibility = float(row.get("earth_occultation_factor", "1"))
        if source_zenith > horizon:
            visibility = 0.0
        scale = gamma_scales.get(time_bin, 1.0)
        gamma_bin = nearest_direction_bin(source_zenith, gamma_bins)
        intensity = float(gamma_bin["integral_per_sr_cm2_s"])
        for window, (emin, emax) in WINDOWS.items():
            frac = float(gamma_bin["fractions"][window])  # type: ignore[index]
            plane_rate = intensity * frac * scale * visibility * omega_opt_sr * optics["effective_area_cm2"]
            final_rate = plane_rate * eps
            timeseries.append(
                {
                    "time_bin_id": time_bin,
                    "day_mid": float(row["day_mid"]),
                    "source_zenith_deg": source_zenith,
                    "nearest_theta_bin_id": int(gamma_bin["bin_id"]),
                    "nearest_theta_mid_deg": float(gamma_bin["theta_mid_deg"]),
                    "window": window,
                    "emin_keV": emin,
                    "emax_keV": emax,
                    "spectrum_fraction": frac,
                    "gamma_scale_factor": scale,
                    "visibility_factor": visibility,
                    "directional_intensity_total_per_sr_cm2_s": intensity,
                    "solid_angle_sr": omega_opt_sr,
                    "effective_area_cm2": optics["effective_area_cm2"],
                    "post_optics_plane_rate_s^-1": plane_rate,
                    "detector_efficiency": eps,
                    "final_focused_gamma_cps": final_rate,
                }
            )

    summary_rows: list[dict[str, object]] = []
    sensitivity_rows: list[dict[str, object]] = []
    for window in WINDOWS:
        subset = [r for r in timeseries if r["window"] == window]
        avg_plane = fmean(float(r["post_optics_plane_rate_s^-1"]) for r in subset)
        avg_final = fmean(float(r["final_focused_gamma_cps"]) for r in subset)
        max_final = max(float(r["final_focused_gamma_cps"]) for r in subset)
        min_final = min(float(r["final_focused_gamma_cps"]) for r in subset)
        representative = max(subset, key=lambda r: float(r["final_focused_gamma_cps"]))
        summary_rows.append(
            {
                "window": window,
                "emin_keV": WINDOWS[window][0],
                "emax_keV": WINDOWS[window][1],
                "mean_post_optics_plane_rate_s^-1": avg_plane,
                "mean_final_focused_gamma_cps": avg_final,
                "min_final_focused_gamma_cps": min_final,
                "max_final_focused_gamma_cps": max_final,
                "representative_theta_mid_deg": representative["nearest_theta_mid_deg"],
                "representative_spectrum_fraction": representative["spectrum_fraction"],
                "detector_efficiency": eps,
                "solid_angle_sr": omega_opt_sr,
                "effective_area_cm2": optics["effective_area_cm2"],
                "accounting_policy": "separate optics-aperture addendum; direct prompt gamma stream is unchanged",
            }
        )
        old = old_background.get(window)
        if old:
            new_background = old["old_background_cps"] + avg_final
            threshold_scale = math.sqrt(new_background / old["old_background_cps"])
            sensitivity_rows.append(
                {
                    "window": window,
                    "old_background_cps": old["old_background_cps"],
                    "focused_gamma_addendum_cps": avg_final,
                    "new_background_cps": new_background,
                    "focused_fraction_of_background": avg_final / old["old_background_cps"],
                    "old_threshold_flux_ph_cm2_s": old["old_threshold_flux_ph_cm2_s"],
                    "threshold_scale_sqrt_Bnew_over_Bold": threshold_scale,
                    "new_threshold_flux_ph_cm2_s": old["old_threshold_flux_ph_cm2_s"] * threshold_scale,
                }
            )

    summary_json: dict[str, object] = {
        "status": "computed",
        "method": "Level-1 optics-aperture rate addendum",
        "no_double_count_policy": (
            "The direct full-sphere prompt gamma background remains unchanged. "
            "The values here are only the subset accepted by the focusing optics aperture "
            "and are added as a separately labelled component."
        ),
        "optics": optics,
        "detector_efficiency": efficiency,
        "solid_angle_sr": omega_opt_sr,
        "time_bins": len({r["time_bin_id"] for r in timeseries}),
        "summary_by_window": summary_rows,
        "sensitivity_addendum": sensitivity_rows,
    }
    return timeseries, summary_rows, sensitivity_rows, summary_json


def main() -> None:
    timeseries, summary_rows, sensitivity_rows, summary_json = make_rows()
    write_csv(
        OUT / "focused_gamma_background_timeseries.csv",
        timeseries,
        [
            "time_bin_id",
            "day_mid",
            "source_zenith_deg",
            "nearest_theta_bin_id",
            "nearest_theta_mid_deg",
            "window",
            "emin_keV",
            "emax_keV",
            "spectrum_fraction",
            "gamma_scale_factor",
            "visibility_factor",
            "directional_intensity_total_per_sr_cm2_s",
            "solid_angle_sr",
            "effective_area_cm2",
            "post_optics_plane_rate_s^-1",
            "detector_efficiency",
            "final_focused_gamma_cps",
        ],
    )
    write_csv(
        OUT / "focused_gamma_background_summary.csv",
        summary_rows,
        [
            "window",
            "emin_keV",
            "emax_keV",
            "mean_post_optics_plane_rate_s^-1",
            "mean_final_focused_gamma_cps",
            "min_final_focused_gamma_cps",
            "max_final_focused_gamma_cps",
            "representative_theta_mid_deg",
            "representative_spectrum_fraction",
            "detector_efficiency",
            "solid_angle_sr",
            "effective_area_cm2",
            "accounting_policy",
        ],
    )
    write_csv(
        OUT / "focused_gamma_sensitivity_addendum.csv",
        sensitivity_rows,
        [
            "window",
            "old_background_cps",
            "focused_gamma_addendum_cps",
            "new_background_cps",
            "focused_fraction_of_background",
            "old_threshold_flux_ph_cm2_s",
            "threshold_scale_sqrt_Bnew_over_Bold",
            "new_threshold_flux_ph_cm2_s",
        ],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "focused_gamma_background_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
