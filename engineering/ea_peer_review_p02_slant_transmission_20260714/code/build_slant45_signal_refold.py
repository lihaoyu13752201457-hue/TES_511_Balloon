#!/usr/bin/env python3
"""Re-fold the retained S3d-O8 signal for a fixed 45 deg source elevation.

This is a derived correction package.  It does not modify the retained
all-eight-family transport, background rates, activation inventory, or live
factor.  Only the celestial signal transmission is changed from the legacy
vertical column to the plane-parallel slant column appropriate to a fixed
45-degree elevation axis.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "engineering/ea_peer_review_p02_slant_transmission_20260714"
DATA = PACKAGE / "data"
OUTPUTS = PACKAGE / "outputs"

RETAINED_ROOT = ROOT / "engineering/ea_s3d_o8_all8_family_nuclide_mission_fold_20260713"
RETAINED_SUMMARY = RETAINED_ROOT / "data/s3d_o8_all8_family_nuclide_mission_summary.json"
RETAINED_TIMELINE = RETAINED_ROOT / "outputs/w2_all8_family_nuclide_mission_timeline.csv"
STEP06_ROOT = ROOT / (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/fullchain/step06"
)
VERTICAL_ATMOSPHERE = STEP06_ROOT / "atmosphere_transmission_511_by_time.csv"
STEP06_SUMMARY = STEP06_ROOT / "step06_s3d_o8_fullchain_summary.json"

OUTPUT_TIMELINE = OUTPUTS / "w2_all8_family_nuclide_mission_timeline_slant45.csv"
OUTPUT_SUMMARY = DATA / "slant45_signal_refold_summary.json"
OUTPUT_VALIDATION = DATA / "slant45_signal_refold_validation.json"

SOURCE_ELEVATION_DEG = 45.0
SOURCE_ZENITH_DEG = 90.0 - SOURCE_ELEVATION_DEG
SLANT_FACTOR = 1.0 / math.cos(math.radians(SOURCE_ZENITH_DEG))
REFERENCE_FLUX = 1.0e-4
IBIS_UPPER_LIMIT_2SIGMA = 1.6e-4
LAUE_EFFECTIVE_AREA_CM2 = 20.1
DAY15 = 15.0

ADDED_FIELDS = [
    "source_elevation_deg",
    "source_zenith_deg",
    "slant_column_factor",
    "vertical_depth_g_cm2",
    "slant_path_depth_g_cm2",
    "T_atm_511_vertical_legacy",
    "T_atm_511_slant45",
    "science_atm_scale_slant45_to_day15",
]


class RefoldError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float, *, atol: float = 1.0e-12, rtol: float = 2.0e-10) -> bool:
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def crossing(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def time_or_extrapolate(days: list[float], values: list[float], threshold: float) -> float:
    value = crossing(days, values, threshold)
    return value if value is not None else days[-1] * (threshold / values[-1]) ** 2


def main() -> None:
    for path in (RETAINED_SUMMARY, RETAINED_TIMELINE, VERTICAL_ATMOSPHERE, STEP06_SUMMARY):
        if not path.is_file():
            raise RefoldError(f"Missing input authority: {path}")

    retained_document = read_json(RETAINED_SUMMARY)
    retained = retained_document["mission"]
    step06 = read_json(STEP06_SUMMARY)
    mu_eff = float(step06["atmosphere_model"]["mu_eff_cm2_g"])
    depth_ref = float(step06["atmosphere_model"]["depth_ref_g_cm2"])
    retained_rows = read_csv(RETAINED_TIMELINE)
    atmosphere_rows = read_csv(VERTICAL_ATMOSPHERE)
    atmosphere_by_id = {int(row["time_bin_id"]): row for row in atmosphere_rows}
    if len(retained_rows) != 81 or len(atmosphere_by_id) != 81:
        raise RefoldError(
            f"Expected 81 retained/atmosphere bins, got {len(retained_rows)}/{len(atmosphere_by_id)}"
        )

    original_fields = list(retained_rows[0])
    output_rows: list[dict[str, Any]] = []
    cumulative_signal = 0.0
    cumulative_background = 0.0
    cumulative_signal_lower = 0.0
    cumulative_background_upper = 0.0
    days: list[float] = []
    central_z: list[float] = []
    conditional_z: list[float] = []
    problems: list[str] = []

    for retained_row in retained_rows:
        row = dict(retained_row)
        time_bin_id = int(row["time_bin_id"])
        atmosphere = atmosphere_by_id[time_bin_id]
        if not close(float(row["day_mid"]), float(atmosphere["day_mid"]), atol=1.0e-10):
            problems.append(f"time-bin {time_bin_id}: day_mid mismatch")

        depth_vertical = float(atmosphere["depth_g_cm2"])
        transmission_vertical = float(atmosphere["T_atm_511"])
        expected_vertical = math.exp(-mu_eff * depth_vertical)
        if not close(transmission_vertical, expected_vertical, atol=3.0e-12):
            problems.append(f"time-bin {time_bin_id}: retained vertical transmission is inconsistent")

        path_depth = depth_vertical * SLANT_FACTOR
        transmission_slant = math.exp(-mu_eff * path_depth)
        ratio = transmission_slant / transmission_vertical
        signal_rate = float(row["signal_final_cps_noacc"]) * ratio
        signal_lower = float(row["signal_final_lower95_cps_noacc"]) * ratio
        live = float(row["accidental_live_factor"])
        dt_s = float(row["dt_s"])
        background_rate = float(row["background_final_cps_noacc"])
        background_upper = float(
            row["background_final_componentwise_transport_counting_endpoint_cps_noacc"]
        )

        cumulative_signal += signal_rate * live * dt_s
        cumulative_background += background_rate * live * dt_s
        cumulative_signal_lower += signal_lower * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        z = cumulative_signal / math.sqrt(cumulative_background)
        z_conditional = cumulative_signal_lower / math.sqrt(cumulative_background_upper)

        row.update(
            {
                "signal_final_cps_noacc": repr(signal_rate),
                "signal_final_lower95_cps_noacc": repr(signal_lower),
                "cumulative_source_counts": repr(cumulative_signal),
                "cumulative_background_counts": repr(cumulative_background),
                "cumulative_source_transport_counting_lower_endpoint_counts": repr(
                    cumulative_signal_lower
                ),
                "cumulative_background_componentwise_transport_counting_upper_endpoint_counts": repr(
                    cumulative_background_upper
                ),
                "counting_Z": repr(z),
                "counting_Z_componentwise_transport_counting_endpoint_conditional": repr(
                    z_conditional
                ),
                "source_elevation_deg": repr(SOURCE_ELEVATION_DEG),
                "source_zenith_deg": repr(SOURCE_ZENITH_DEG),
                "slant_column_factor": repr(SLANT_FACTOR),
                "vertical_depth_g_cm2": repr(depth_vertical),
                "slant_path_depth_g_cm2": repr(path_depth),
                "T_atm_511_vertical_legacy": repr(transmission_vertical),
                "T_atm_511_slant45": repr(transmission_slant),
                "science_atm_scale_slant45_to_day15": "",  # filled after day-15 anchor is known
            }
        )
        output_rows.append(row)
        days.append(float(row["elapsed_stop_day"]))
        central_z.append(z)
        conditional_z.append(z_conditional)

    day15_index = next(
        index for index, row in enumerate(output_rows) if close(float(row["day_mid"]), DAY15)
    )
    day15_row = output_rows[day15_index]
    transmission_ref_vertical = float(day15_row["T_atm_511_vertical_legacy"])
    transmission_ref_slant = float(day15_row["T_atm_511_slant45"])
    for row in output_rows:
        row["science_atm_scale_slant45_to_day15"] = repr(
            float(row["T_atm_511_slant45"]) / transmission_ref_slant
        )

    if not close(depth_ref, float(day15_row["vertical_depth_g_cm2"])):
        problems.append("day-15 vertical depth differs from the Step06 atmosphere authority")
    if not close(transmission_ref_slant, transmission_ref_vertical ** SLANT_FACTOR):
        problems.append("day-15 slant transmission does not equal T_vertical**sec(zenith)")

    retained_signal = float(retained["day15_selected_rates_cps"]["signal"])
    retained_signal_lower = float(
        retained["day15_selected_rates_cps"]["signal_transport_counting_lower_endpoint_cps"]
    )
    selected_instrument_area = retained_signal / (REFERENCE_FLUX * transmission_ref_vertical)
    detector_selection_efficiency = selected_instrument_area / LAUE_EFFECTIVE_AREA_CM2
    day15_signal = float(day15_row["signal_final_cps_noacc"])
    day15_signal_lower = float(day15_row["signal_final_lower95_cps_noacc"])

    retained_background_counts = float(retained["background_counts_20d"])
    retained_background_upper_counts = float(
        retained["background_componentwise_transport_counting_upper_endpoint_counts_20d"]
    )
    if not close(cumulative_background, retained_background_counts, atol=2.0e-8):
        problems.append("central background counts changed during signal-only refold")
    if not close(cumulative_background_upper, retained_background_upper_counts, atol=2.0e-8):
        problems.append("conditional background counts changed during signal-only refold")
    if not close(
        day15_signal,
        REFERENCE_FLUX * selected_instrument_area * transmission_ref_slant,
        atol=2.0e-15,
    ):
        problems.append("day-15 signal normalization does not close")
    if not close(
        day15_signal_lower,
        retained_signal_lower * transmission_ref_slant / transmission_ref_vertical,
        atol=2.0e-15,
    ):
        problems.append("day-15 signal lower endpoint does not close")

    output_fields = original_fields + ADDED_FIELDS
    write_csv(OUTPUT_TIMELINE, output_rows, output_fields)

    z20 = central_z[-1]
    z20_conditional = conditional_z[-1]
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary = {
        "status": "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD" if not problems else "FAIL_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD",
        "generated_at_utc": generated_at,
        "scope": (
            "Derived signal-only atmospheric correction. Retained all-eight-family prompt, delayed, "
            "atmospheric-line background, occupancy, live factors, and transport statistics are unchanged."
        ),
        "input_authorities": {
            "retained_mission_summary": str(RETAINED_SUMMARY.relative_to(ROOT)),
            "retained_mission_summary_sha256": sha256(RETAINED_SUMMARY),
            "retained_mission_timeline": str(RETAINED_TIMELINE.relative_to(ROOT)),
            "retained_mission_timeline_sha256": sha256(RETAINED_TIMELINE),
            "vertical_atmosphere_timeline": str(VERTICAL_ATMOSPHERE.relative_to(ROOT)),
            "vertical_atmosphere_timeline_sha256": sha256(VERTICAL_ATMOSPHERE),
            "step06_summary": str(STEP06_SUMMARY.relative_to(ROOT)),
            "step06_summary_sha256": sha256(STEP06_SUMMARY),
        },
        "fixed_source_geometry": {
            "source_elevation_deg": SOURCE_ELEVATION_DEG,
            "source_zenith_deg": SOURCE_ZENITH_DEG,
            "plane_parallel_slant_column_factor": SLANT_FACTOR,
            "qualification": "fixed continuously observed reference axis, not a Galactic-centre visibility forecast",
        },
        "atmosphere_model": {
            "formula": "T=exp[-mu_eff*X_vertical/cos(zenith)]",
            "day15_vertical_depth_g_cm2": depth_ref,
            "mu_eff_cm2_g": mu_eff,
            "day15_vertical_transmission_legacy": transmission_ref_vertical,
            "day15_slant_path_depth_g_cm2": depth_ref * SLANT_FACTOR,
            "day15_slant45_transmission": transmission_ref_slant,
            "slant_to_vertical_transmission_ratio": transmission_ref_slant / transmission_ref_vertical,
            "attenuation_note": (
                "mu_eff is inherited from the retained vertical T/depth closure and is consistent with "
                "the NIST XCOM dry-air mass attenuation coefficient near 511 keV."
            ),
        },
        "point_source_reference": {
            "reference_surface": "top of atmosphere",
            "F0_ph_cm2_s": REFERENCE_FLUX,
            "IBIS_2sigma_upper_limit_ph_cm2_s": IBIS_UPPER_LIMIT_2SIGMA,
            "IBIS_exposure_s": 1.0e7,
            "IBIS_reference": "De Cesare 2011, A&A 531 A56, doi:10.1051/0004-6361/201116516",
            "F0_payload_plane_ph_cm2_s_at_day15_slant45": REFERENCE_FLUX * transmission_ref_slant,
            "IBIS_limit_payload_plane_ph_cm2_s_at_day15_slant45": (
                IBIS_UPPER_LIMIT_2SIGMA * transmission_ref_slant
            ),
        },
        "detector_signal_normalization": {
            "Laue_on_axis_effective_area_cm2": LAUE_EFFECTIVE_AREA_CM2,
            "detector_selection_efficiency_after_focal_plane": detector_selection_efficiency,
            "instrument_only_selected_effective_area_cm2": selected_instrument_area,
            "day15_atmosphere_folded_selected_conversion_cm2": day15_signal / REFERENCE_FLUX,
            "day15_focal_plane_rate_cps_at_F0": (
                REFERENCE_FLUX * LAUE_EFFECTIVE_AREA_CM2 * transmission_ref_slant
            ),
        },
        "day15_selected_rates_cps": {
            "background_unchanged": float(retained["day15_selected_rates_cps"]["background"]),
            "signal": day15_signal,
            "signal_transport_counting_lower_endpoint": day15_signal_lower,
        },
        "mission": {
            "reference_flux_ph_cm2_s": REFERENCE_FLUX,
            "source_counts_20d": cumulative_signal,
            "background_counts_20d": cumulative_background,
            "source_transport_counting_lower_endpoint_counts_20d": cumulative_signal_lower,
            "background_componentwise_transport_counting_upper_endpoint_counts_20d": cumulative_background_upper,
            "Z20d": z20,
            "Z20d_componentwise_transport_counting_endpoint_conditional": z20_conditional,
            "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20,
            "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s": (
                REFERENCE_FLUX * 3.0 / z20_conditional
            ),
            "T3_day": time_or_extrapolate(days, central_z, 3.0),
            "T5_day": time_or_extrapolate(days, central_z, 5.0),
            "T3_day_componentwise_transport_counting_endpoint_conditional": time_or_extrapolate(
                days, conditional_z, 3.0
            ),
            "T5_day_componentwise_transport_counting_endpoint_conditional": time_or_extrapolate(
                days, conditional_z, 5.0
            ),
            "model": {
                **retained["model"],
                "signal_transmission": (
                    "fixed 45 degree elevation; T=exp[-mu_eff*X_vertical/cos(45 deg)] "
                    "in every trajectory bin"
                ),
            },
        },
        "comparison_to_legacy_vertical_signal": {
            "day15_signal_ratio": day15_signal / retained_signal,
            "Z20d_ratio": z20 / float(retained["Z20d"]),
            "central_flux_threshold_ratio": (
                (REFERENCE_FLUX * 3.0 / z20) / float(retained["flux_3sigma_20d_ph_cm2_s"])
            ),
        },
        "outputs": {
            "timeline": str(OUTPUT_TIMELINE.relative_to(ROOT)),
            "timeline_sha256": sha256(OUTPUT_TIMELINE),
        },
        "problems": problems,
    }
    write_json(OUTPUT_SUMMARY, summary)

    validation = {
        "status": "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD_VALIDATION" if not problems else "FAIL_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD_VALIDATION",
        "generated_at_utc": generated_at,
        "summary": str(OUTPUT_SUMMARY.relative_to(ROOT)),
        "summary_sha256": sha256(OUTPUT_SUMMARY),
        "timeline": str(OUTPUT_TIMELINE.relative_to(ROOT)),
        "timeline_sha256": sha256(OUTPUT_TIMELINE),
        "bins": len(output_rows),
        "day15_index": day15_index,
        "checks": {
            "background_counts_unchanged": close(cumulative_background, retained_background_counts, atol=2.0e-8),
            "background_upper_counts_unchanged": close(cumulative_background_upper, retained_background_upper_counts, atol=2.0e-8),
            "day15_signal_normalization_closes": close(
                day15_signal,
                REFERENCE_FLUX * selected_instrument_area * transmission_ref_slant,
                atol=2.0e-15,
            ),
            "slant_transmission_below_vertical": transmission_ref_slant < transmission_ref_vertical,
            "all_81_bins_joined": len(output_rows) == len(atmosphere_by_id) == 81,
        },
        "problems": problems,
    }
    write_json(OUTPUT_VALIDATION, validation)
    if problems:
        raise RefoldError("; ".join(problems))

    print(json.dumps({
        "status": validation["status"],
        "T45": transmission_ref_slant,
        "day15_signal_cps": day15_signal,
        "Z20d": z20,
        "F3_20d": REFERENCE_FLUX * 3.0 / z20,
        "Z20d_conditional": z20_conditional,
        "F3_20d_conditional": REFERENCE_FLUX * 3.0 / z20_conditional,
    }, indent=2))


if __name__ == "__main__":
    main()
