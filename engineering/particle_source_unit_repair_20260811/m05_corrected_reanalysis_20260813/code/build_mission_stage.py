#!/usr/bin/env python3
"""Fold corrected prompt, delayed, and focused signal over the retained 81-bin mission."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
CONFIG = PACKAGE / "analysis_inputs.json"
COMMON = PACKAGE / "outputs/04_common_response"
ACTIVATION = PACKAGE / "outputs/02_activation/day15_inventory.csv"
OUTPUT = PACKAGE / "outputs/06_mission"
LEGACY_MISSION_CODE = ROOT / "engineering/ea_s3d_o8_all8_family_nuclide_mission_fold_20260713/code/build_s3d_o8_all8_family_nuclide_mission_fold.py"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
DAY15 = 15.0
SECONDS_PER_DAY = 86_400.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_legacy() -> Any:
    spec = importlib.util.spec_from_file_location("m05_retained_mission_math", LEGACY_MISSION_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {LEGACY_MISSION_CODE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def aggregate_inventory(rows: list[dict[str, str]]) -> dict[tuple[str, str, int], dict[str, float]]:
    inventory: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in rows:
        if row["source_disposition"] != "transported_ground_state":
            continue
        key = (row["geometry"], row["incident_family"], int(row["source_parent_ZA"]))
        item = inventory.setdefault(
            key,
            {
                "day15_activity_Bq": 0.0,
                "production_rate_s-1": 0.0,
                "half_life_s": float(row["half_life_s"]),
            },
        )
        item["day15_activity_Bq"] += float(row["day15_activity_Bq"])
        item["production_rate_s-1"] += float(row["production_rate_s-1"])
    return inventory


def family_scale(row: dict[str, str], family: str) -> float:
    return float(row[f"scale_{family}_to_parma_reference"])


def advance_linear_inventory(number: float, production_left: float, production_right: float, lam: float, dt_s: float) -> float:
    """Exact decay convolution for production varying linearly across one interval."""
    x = lam * dt_s
    if x < 1.0e-5:
        phi1 = 1.0 - x / 2.0 + x * x / 6.0 - x**3 / 24.0 + x**4 / 120.0
        phi2 = 0.5 - x / 6.0 + x * x / 24.0 - x**3 / 120.0 + x**4 / 720.0
    else:
        phi1 = -math.expm1(-x) / x
        phi2 = (1.0 - phi1) / x
    return (
        number * math.exp(-x)
        + dt_s * (production_left * phi1 + (production_right - production_left) * phi2)
    )


def crossing_trapezoid(
    days: list[float], signal_rates: list[float], background_rates: list[float], threshold: float
) -> float | None:
    """Find S/sqrt(B)=threshold inside the piecewise-linear-rate integral."""
    source = 0.0
    background = 0.0
    threshold2 = threshold * threshold
    for index in range(1, len(days)):
        dt_s = (days[index] - days[index - 1]) * SECONDS_PER_DAY
        source_next = source + 0.5 * (signal_rates[index - 1] + signal_rates[index]) * dt_s
        background_next = background + 0.5 * (background_rates[index - 1] + background_rates[index]) * dt_s
        if source_next * source_next >= threshold2 * background_next:
            left = 0.0
            right = 1.0
            for _ in range(60):
                fraction = 0.5 * (left + right)
                source_at = source + dt_s * (
                    signal_rates[index - 1] * fraction
                    + 0.5 * (signal_rates[index] - signal_rates[index - 1]) * fraction * fraction
                )
                background_at = background + dt_s * (
                    background_rates[index - 1] * fraction
                    + 0.5 * (background_rates[index] - background_rates[index - 1]) * fraction * fraction
                )
                if source_at * source_at >= threshold2 * background_at:
                    right = fraction
                else:
                    left = fraction
            return days[index - 1] + right * (days[index] - days[index - 1])
        source = source_next
        background = background_next
    return None


def crossing_or_sqrt_extrapolation(crossing: float | None, day_last: float, z_last: float, threshold: float) -> float:
    return crossing if crossing is not None else day_last * (threshold / z_last) ** 2


def activity_curves(
    legacy: Any,
    base: list[dict[str, str]],
    scales: list[dict[str, str]],
    inventory: dict[tuple[str, str, int], dict[str, float]],
) -> dict[tuple[str, str, int], list[float]]:
    curves: dict[tuple[str, str, int], list[float]] = {}
    for key, item in inventory.items():
        _, family, _ = key
        lam = math.log(2.0) / item["half_life_s"]
        production_ref = item["production_rate_s-1"]
        number = 0.0
        curve = [0.0]
        for index in range(1, len(base)):
            dt_s = (float(base[index]["day_mid"]) - float(base[index - 1]["day_mid"])) * SECONDS_PER_DAY
            production_left = production_ref * family_scale(scales[index - 1], family)
            production_right = production_ref * family_scale(scales[index], family)
            number = advance_linear_inventory(number, production_left, production_right, lam, dt_s)
            curve.append(lam * number)
        curves[key] = curve
    return curves


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        mission = config["analysis"]["mission"]
        reference_flux = float(mission["reference_flux_ph_cm2_s"])
        coincidence_window = float(mission["coincidence_window_s"])
        elevation_deg = float(mission["source_elevation_deg"])
        slant_factor = 1.0 / math.sin(math.radians(elevation_deg))
        scales_path = ROOT / mission["family_scale_authority"]
        scales_metadata_path = ROOT / mission["family_scale_metadata"]
        atmosphere_path = ROOT / mission["atmosphere_authority"]

        common_summary = json.loads((COMMON / "summary.json").read_text(encoding="utf-8"))
        scales_metadata = json.loads(scales_metadata_path.read_text(encoding="utf-8"))
        cutflow = read_csv(COMMON / "common_cutflow.csv")
        signal = read_csv(COMMON / "signal_acceptance_effective_area.csv")
        occupancy = read_csv(COMMON / "common_fullband_occupancy.csv")
        lineage = read_csv(COMMON / "selected_background_w2_lineage.csv")
        inventory_rows = read_csv(ACTIVATION)
        scales = sorted(read_csv(scales_path), key=lambda row: int(row["time_bin_id"]))
        atmosphere = sorted(read_csv(atmosphere_path), key=lambda row: int(row["time_bin_id"]))
        if len(scales) != int(mission["time_bins"]) or len(atmosphere) != int(mission["time_bins"]):
            raise RuntimeError("mission authority does not contain 81 bins")
        for scale_row, atmosphere_row in zip(scales, atmosphere):
            if (
                int(scale_row["time_bin_id"]) != int(atmosphere_row["time_bin_id"])
                or not math.isclose(float(scale_row["day_mid"]), float(atmosphere_row["day_mid"]))
            ):
                raise RuntimeError("mission scale and atmosphere time axes differ")

        base = [
            {
                "time_bin_id": row["time_bin_id"], "day_mid": row["day_mid"],
                "dt_s": row["dt_s"], "T_atm_511": row["T_atm_511"],
                "depth_g_cm2": row["depth_g_cm2"],
            }
            for row in atmosphere
        ]
        legacy = load_legacy()
        inventory = aggregate_inventory(inventory_rows)
        curves = activity_curves(legacy, base, scales, inventory)
        day15_index = next(i for i, row in enumerate(base) if math.isclose(float(row["day_mid"]), DAY15))

        selected_counts = Counter(
            (row["geometry"], row["family"], int(row["source_parent_ZA"]))
            for row in lineage if row["stream"] == "delayed"
        )
        selected_weight: dict[tuple[str, str], float] = {}
        for row in lineage:
            if row["stream"] != "delayed":
                continue
            selected_weight[(row["geometry"], row["family"])] = float(row["event_weight_cps"])

        final_components = {
            (row["geometry"], row["stream"], row["family"]): row
            for row in cutflow
            if row["response_state"] == "measured" and row["stage"] == "side_compton_fov_pass"
            and row["window_id"] == "w2_510p58_511p42" and row["stream"] in {"prompt", "delayed"}
        }
        occupancy_map = {
            (row["geometry"], row["stream"], row["family"]): float(row["weighted_occupancy"])
            for row in occupancy if row["stream"] in {"prompt", "delayed"}
        }
        signal_map = {
            row["geometry"]: row for row in signal
            if row["response_state"] == "measured" and row["stage"] == "side_compton_fov_pass"
            and row["window_id"] == "w2_510p58_511p42"
        }

        activity_rows = []
        for (geometry, family, za), values in sorted(curves.items()):
            item = inventory[(geometry, family, za)]
            count = selected_counts[(geometry, family, za)]
            weight = selected_weight.get((geometry, family), 0.0)
            for index, activity in enumerate(values):
                scale = activity / item["day15_activity_Bq"]
                activity_rows.append(
                    {
                        "geometry": geometry, "time_bin_id": int(base[index]["time_bin_id"]),
                        "day_mid": float(base[index]["day_mid"]), "incident_family": family,
                        "source_parent_ZA": za, "half_life_s": item["half_life_s"],
                        "constant_source_environment_day15_activity_Bq": item["day15_activity_Bq"],
                        "production_rate_at_corrected_source_environment_s-1": item["production_rate_s-1"],
                        "activity_Bq": activity,
                        "activity_scale_to_constant_environment_day15_inventory": scale,
                        "selected_events_in_static_day15_transport": count,
                        "static_day15_transport_event_weight_cps": weight,
                        "selected_rate_cps": count * weight * scale,
                    }
                )

        timeline = []
        summaries: dict[str, Any] = {}
        for geometry in GEOMETRIES:
            family_activity = {
                family: [
                    math.fsum(
                        curve[index] for (g, f, _), curve in curves.items()
                        if g == geometry and f == family
                    )
                    for index in range(len(base))
                ]
                for family in FAMILIES
            }
            family_activity_reference = {
                family: math.fsum(
                    item["day15_activity_Bq"] for (g, f, _), item in inventory.items()
                    if g == geometry and f == family
                )
                for family in FAMILIES
            }
            family_delayed_rate = {family: [0.0] * len(base) for family in FAMILIES}
            family_delayed_variance = {family: [0.0] * len(base) for family in FAMILIES}
            for key, count in selected_counts.items():
                g, family, za = key
                if g != geometry:
                    continue
                weight = selected_weight[(geometry, family)]
                activity_ref = inventory[(geometry, family, za)]["day15_activity_Bq"]
                for index, activity in enumerate(curves[(geometry, family, za)]):
                    scaled_weight = weight * activity / activity_ref
                    family_delayed_rate[family][index] += count * scaled_weight
                    family_delayed_variance[family][index] += count * scaled_weight * scaled_weight

            cumulative_signal = 0.0
            cumulative_background = 0.0
            cumulative_signal_lower = 0.0
            cumulative_background_upper = 0.0
            days = []
            central_z = []
            conditional_z = []
            central_signal_rates = []
            central_background_rates = []
            conditional_signal_rates = []
            conditional_background_rates = []
            geometry_rows = []
            previous_rates: dict[str, float] | None = None
            for index, base_row in enumerate(base):
                prompt_rate = prompt_variance = prompt_upper = prompt_occ = 0.0
                delayed_rate = delayed_variance = delayed_upper = delayed_occ = 0.0
                row_family: dict[str, Any] = {}
                for family in FAMILIES:
                    prompt_family_scale = family_scale(scales[index], family)
                    prompt_component = final_components[(geometry, "prompt", family)]
                    prompt_family_rate = float(prompt_component["weighted_value"]) * prompt_family_scale
                    prompt_rate += prompt_family_rate
                    prompt_variance += (float(prompt_component["weighted_stat_sigma"]) * prompt_family_scale) ** 2
                    prompt_upper += float(prompt_component["weighted_upper95"]) * prompt_family_scale
                    prompt_occ += occupancy_map[(geometry, "prompt", family)] * prompt_family_scale

                    delayed_component = final_components[(geometry, "delayed", family)]
                    delayed_family_rate = family_delayed_rate[family][index]
                    delayed_rate += delayed_family_rate
                    delayed_variance += family_delayed_variance[family][index]
                    day15_selected = float(delayed_component["weighted_value"])
                    if family_activity_reference[family] > 0.0:
                        activity_scale = family_activity[family][index] / family_activity_reference[family]
                    else:
                        activity_scale = 0.0
                    if day15_selected > 0.0:
                        delayed_scale = delayed_family_rate / day15_selected
                    else:
                        delayed_scale = activity_scale
                    delayed_upper += float(delayed_component["weighted_upper95"]) * delayed_scale
                    delayed_occ += occupancy_map[(geometry, "delayed", family)] * activity_scale
                    row_family[f"prompt_{family}_cps"] = prompt_family_rate
                    row_family[f"delayed_{family}_cps"] = delayed_family_rate

                transmission_vertical = float(base_row["T_atm_511"])
                transmission_slant = transmission_vertical ** slant_factor
                signal_row = signal_map[geometry]
                signal_rate = reference_flux * float(signal_row["selected_effective_area_cm2"]) * transmission_slant
                signal_lower = reference_flux * float(signal_row["selected_effective_area_lower95_cm2"]) * transmission_slant
                occupancy_rate = prompt_occ + delayed_occ
                live = math.exp(-occupancy_rate * coincidence_window)
                background = prompt_rate + delayed_rate
                background_upper = prompt_upper + delayed_upper
                day_mid = float(base_row["day_mid"])
                interval_s = 0.0 if index == 0 else (
                    day_mid - float(base[index - 1]["day_mid"])
                ) * SECONDS_PER_DAY
                current_rates = {
                    "signal": signal_rate * live,
                    "background": background * live,
                    "signal_lower": signal_lower * live,
                    "background_upper": background_upper * live,
                }
                central_signal_rates.append(current_rates["signal"])
                central_background_rates.append(current_rates["background"])
                conditional_signal_rates.append(current_rates["signal_lower"])
                conditional_background_rates.append(current_rates["background_upper"])
                if previous_rates is not None:
                    cumulative_signal += 0.5 * (previous_rates["signal"] + current_rates["signal"]) * interval_s
                    cumulative_background += 0.5 * (previous_rates["background"] + current_rates["background"]) * interval_s
                    cumulative_signal_lower += 0.5 * (previous_rates["signal_lower"] + current_rates["signal_lower"]) * interval_s
                    cumulative_background_upper += 0.5 * (
                        previous_rates["background_upper"] + current_rates["background_upper"]
                    ) * interval_s
                previous_rates = current_rates
                z = cumulative_signal / math.sqrt(cumulative_background) if cumulative_background > 0.0 else 0.0
                z_conditional = (
                    cumulative_signal_lower / math.sqrt(cumulative_background_upper)
                    if cumulative_background_upper > 0.0 else 0.0
                )
                days.append(day_mid)
                central_z.append(z)
                conditional_z.append(z_conditional)
                geometry_rows.append(
                    {
                        "geometry": geometry, "time_bin_id": int(base_row["time_bin_id"]),
                        "day_mid": day_mid, "elapsed_day": day_mid,
                        "trajectory_quadrature_weight_s": float(base_row["dt_s"]),
                        "integration_interval_from_previous_s": interval_s,
                        "altitude_km": float(scales[index]["altitude_km"]),
                        "prompt_occupancy_cps": prompt_occ, "delayed_occupancy_cps": delayed_occ,
                        "accidental_live_factor": live, "T_atm_511_vertical": transmission_vertical,
                        "T_atm_511_slant45": transmission_slant,
                        "prompt_final_cps_noacc": prompt_rate, "delayed_final_cps_noacc": delayed_rate,
                        "background_final_cps_noacc": background,
                        "background_mc_counting_sigma_cps": math.sqrt(prompt_variance + delayed_variance),
                        "signal_final_cps_noacc_at_reference_flux": signal_rate,
                        "prompt_componentwise_upper95_proxy_cps_noacc": prompt_upper,
                        "delayed_conditional_mixture_upper95_proxy_cps_noacc": delayed_upper,
                        "background_componentwise_upper95_proxy_cps_noacc": background_upper,
                        "signal_lower95_cps_noacc_at_reference_flux": signal_lower,
                        "cumulative_source_counts": cumulative_signal,
                        "cumulative_background_counts": cumulative_background,
                        "cumulative_source_lower95_counts": cumulative_signal_lower,
                        "cumulative_background_upper95_proxy_counts": cumulative_background_upper,
                        "counting_Z": z, "counting_Z_conditional_endpoint_proxy": z_conditional,
                        **row_family,
                    }
                )
            timeline.extend(geometry_rows)
            day15_row = geometry_rows[day15_index]
            static_prompt_day15 = math.fsum(
                float(final_components[(geometry, "prompt", family)]["weighted_value"])
                for family in FAMILIES
            )
            static_delayed_day15 = math.fsum(
                float(final_components[(geometry, "delayed", family)]["weighted_value"])
                for family in FAMILIES
            )
            static_activity_day15 = math.fsum(family_activity_reference.values())
            forward_activity_day15 = math.fsum(
                family_activity[family][day15_index] for family in FAMILIES
            )
            z20 = central_z[-1]
            z20_conditional = conditional_z[-1]
            t3_crossing = crossing_trapezoid(days, central_signal_rates, central_background_rates, 3.0)
            t5_crossing = crossing_trapezoid(days, central_signal_rates, central_background_rates, 5.0)
            t3_conditional_crossing = crossing_trapezoid(
                days, conditional_signal_rates, conditional_background_rates, 3.0
            )
            t5_conditional_crossing = crossing_trapezoid(
                days, conditional_signal_rates, conditional_background_rates, 5.0
            )
            summaries[geometry] = {
                "constant_environment_day15_reference": {
                    "transported_activity_Bq": static_activity_day15,
                    "prompt_final_cps": static_prompt_day15,
                    "delayed_final_cps": static_delayed_day15,
                    "background_final_cps": static_prompt_day15 + static_delayed_day15,
                },
                "trajectory_day15_node": day15_row,
                "trajectory_day15_to_constant_environment_ratio": {
                    "transported_activity": forward_activity_day15 / static_activity_day15,
                    "prompt_final": day15_row["prompt_final_cps_noacc"] / static_prompt_day15,
                    "delayed_final": day15_row["delayed_final_cps_noacc"] / static_delayed_day15,
                    "background_final": day15_row["background_final_cps_noacc"] / (
                        static_prompt_day15 + static_delayed_day15
                    ),
                },
                "source_counts_20d": cumulative_signal,
                "background_counts_20d": cumulative_background,
                "source_lower95_counts_20d": cumulative_signal_lower,
                "background_upper95_proxy_counts_20d": cumulative_background_upper,
                "Z20d": z20,
                "Z20d_conditional_endpoint_proxy": z20_conditional,
                "T3_day": crossing_or_sqrt_extrapolation(t3_crossing, days[-1], z20, 3.0),
                "T5_day": crossing_or_sqrt_extrapolation(t5_crossing, days[-1], z20, 5.0),
                "T3_day_conditional_endpoint_proxy": crossing_or_sqrt_extrapolation(
                    t3_conditional_crossing, days[-1], z20_conditional, 3.0
                ),
                "T5_day_conditional_endpoint_proxy": crossing_or_sqrt_extrapolation(
                    t5_conditional_crossing, days[-1], z20_conditional, 5.0
                ),
                "T3_status": "CROSSED_WITHIN_20D" if t3_crossing is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY",
                "T5_status": "CROSSED_WITHIN_20D" if t5_crossing is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY",
                "T3_conditional_endpoint_proxy_status": "CROSSED_WITHIN_20D" if t3_conditional_crossing is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY",
                "T5_conditional_endpoint_proxy_status": "CROSSED_WITHIN_20D" if t5_conditional_crossing is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY",
                "flux_3sigma_20d_ph_cm2_s": reference_flux * 3.0 / z20,
                "flux_3sigma_20d_conditional_endpoint_proxy_ph_cm2_s": reference_flux * 3.0 / z20_conditional,
                "accidental_loss_min": min(1.0 - row["accidental_live_factor"] for row in geometry_rows),
                "accidental_loss_max": max(1.0 - row["accidental_live_factor"] for row in geometry_rows),
            }

        comparison = []
        for geometry in GEOMETRIES:
            item = summaries[geometry]
            comparison.append(
                {
                    "geometry": geometry,
                    "trajectory_day15_background_cps": item["trajectory_day15_node"]["background_final_cps_noacc"],
                    "trajectory_day15_signal_cps_at_reference_flux": item["trajectory_day15_node"]["signal_final_cps_noacc_at_reference_flux"],
                    "constant_environment_day15_background_reference_cps": item["constant_environment_day15_reference"]["background_final_cps"],
                    "source_counts_20d": item["source_counts_20d"],
                    "background_counts_20d": item["background_counts_20d"],
                    "Z20d": item["Z20d"],
                    "Z20d_conditional_endpoint_proxy": item["Z20d_conditional_endpoint_proxy"],
                    "T3_day": item["T3_day"], "T5_day": item["T5_day"],
                    "T3_status": item["T3_status"], "T5_status": item["T5_status"],
                    "T3_day_conditional_endpoint_proxy": item["T3_day_conditional_endpoint_proxy"],
                    "T5_day_conditional_endpoint_proxy": item["T5_day_conditional_endpoint_proxy"],
                    "T3_conditional_endpoint_proxy_status": item["T3_conditional_endpoint_proxy_status"],
                    "T5_conditional_endpoint_proxy_status": item["T5_conditional_endpoint_proxy_status"],
                    "flux_3sigma_20d_ph_cm2_s": item["flux_3sigma_20d_ph_cm2_s"],
                    "flux_3sigma_20d_conditional_endpoint_proxy_ph_cm2_s": item["flux_3sigma_20d_conditional_endpoint_proxy_ph_cm2_s"],
                }
            )

        summary = {
            "schema_version": 1,
            "status": "PASS__M05_CORRECTED_81BIN_FORWARD_ANALYTIC_SCENARIO__PROMOTION_DEFERRED",
            "input_common_response_status": common_summary["status"],
            "mission_contract": mission,
            "family_scale_metadata": scales_metadata,
            "source_elevation_slant_factor": slant_factor,
            "geometries": summaries,
            "background_contract": "prompt unit_only_total_gamma plus delayed; no additive atmospheric mono-511",
            "activity_contract": (
                "scenario assumption of zero inventory at mission day 0; exact piecewise-linear-source decay convolution of stage-02 production_rate_s-1 times the "
                "energy-integrated PARMA family ratio to its 34N,100E,38km reference; no day-15 reanchoring"
            ),
            "time_integration": "trapezoidal rate integration on the 81 trajectory nodes from day 0 through day 20; threshold crossings solve S(t)^2=threshold^2 B(t) inside each interval",
            "uncertainty_contract": {
                "central": "weighted transport-MC central rates; instantaneous MC sigma is sqrt(sum(w_i^2))",
                "conditional_endpoint_proxy": (
                    "componentwise prompt Garwood upper plus delayed parent-mixture-scaled upper, "
                    "with focused-signal Clopper-Pearson lower; not joint 95% coverage"
                ),
                "not_propagated": [
                    "cumulative transport-MC variance across time-correlated reuse of the same events",
                    "full-band occupancy MC uncertainty in the accidental-live factor",
                    "source-position mixture, activation-yield, optics, atmosphere, and trajectory systematics",
                ],
            },
            "known_exclusions": [
                "PARMA driver gives W=114.6 while the corrected source contract records W=118.3; only driver-internal relative ratios are used",
                "family scalar transport holds the within-family energy spectrum, angular distribution, detector response, and activation yield fixed across trajectory bins; no corrected multipoint transport validates that approximation",
                "zero inventory at mission day 0 excludes pre-flight and ground activation",
                "non-day15 delayed occupancy uses a family-total-activity proxy because active-only parent lineage is unavailable",
                "10k exact-position source-mixture uncertainty (parent-ZA TV up to 6.19%)",
                "0.0998092689784 Bq S3d excited-state holdout and unresolved NUBASE rows",
                "optics effective-area systematic and source visibility/duty-cycle history",
                "full-envelope BPE/plastic optical transmission outside the post-Be EventList scope",
                "the 81-bin altitude/position profile is synthetic rather than flight telemetry",
                "T3/T5 values beyond 20 d are labeled sqrt-time extrapolations, not trajectory crossings",
            ],
            "authority_boundary": (
                "CORRECTED_FORWARD_ANALYTIC_FAMILY_SCALAR_SCENARIO_COMPLETE__"
                "NOT_CORRECTED_MULTIPOINT_TRANSPORT_OR_FINAL_GEOMETRY_PROMOTION_AUTHORITY"
            ),
        }
        write_csv(work / "family_parent_activity_by_time.csv", activity_rows)
        write_csv(work / "mission_timeline.csv", timeline)
        write_csv(work / "mission_comparison.csv", comparison)
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = [
            "# Corrected-keV 81-bin forward analytic mission scenario", "", f"Status: `{summary['status']}`", "",
            "Stage-02 production rates are advanced under the scenario assumption of zero inventory at mission day 0 using an exact piecewise-linear-source decay convolution. Pre-flight/ground activation is not included, and no day-15 activity is forced to match the constant-environment inventory.", "",
            "| Geometry | Z20 central | Z20 conditional proxy | T3 d | T5 d | F3(20d) | F3 proxy |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in comparison:
            t3 = f"{row['T3_day']:.6g}" if row["T3_status"] == "CROSSED_WITHIN_20D" else f">20 (sqrt-time extrap. {row['T3_day']:.4g})"
            t5 = f"{row['T5_day']:.6g}" if row["T5_status"] == "CROSSED_WITHIN_20D" else f">20 (sqrt-time extrap. {row['T5_day']:.4g})"
            report.append(
                f"| {row['geometry']} | {row['Z20d']:.6g} | {row['Z20d_conditional_endpoint_proxy']:.6g} | "
                f"{t3} | {t5} | {row['flux_3sigma_20d_ph_cm2_s']:.6g} | "
                f"{row['flux_3sigma_20d_conditional_endpoint_proxy_ph_cm2_s']:.6g} |"
            )
        report.extend(["", "## Day-15 node versus constant-environment reference", "", "| Geometry | Static reference B (cps) | Trajectory-node B (cps) | Ratio |", "|---|---:|---:|---:|"])
        for row in comparison:
            ratio = row["trajectory_day15_background_cps"] / row["constant_environment_day15_background_reference_cps"]
            report.append(
                f"| {row['geometry']} | {row['constant_environment_day15_background_reference_cps']:.6g} | "
                f"{row['trajectory_day15_background_cps']:.6g} | {ratio:.6g} |"
            )
        report.extend([
            "",
            "The corrected broadband gamma already includes the annihilation bump; no atmospheric mono-511 background is added. The conditional endpoint is a componentwise mixture proxy, not a joint 95% interval.",
            "",
            "The PARMA executable returns W=114.6 for the retained date while the corrected source contract records W=118.3. Only ratios to the driver's 34N,100E,38 km reference are used; the within-family energy spectrum, angular distribution, detector response, and activation yield remain fixed scenario assumptions.",
            "",
        ])
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        manifest = {
            "schema_version": 1, "status": summary["status"], "analysis_code": relative(HERE),
            "reused_stable_math_helpers": relative(LEGACY_MISSION_CODE),
            "inputs": [
                relative(COMMON / "summary.json"), relative(COMMON / "common_cutflow.csv"),
                relative(COMMON / "signal_acceptance_effective_area.csv"),
                relative(COMMON / "common_fullband_occupancy.csv"),
                relative(COMMON / "selected_background_w2_lineage.csv"), relative(ACTIVATION), relative(scales_path),
                relative(scales_metadata_path), relative(atmosphere_path),
            ],
            "files": [{"path": str(path.relative_to(work)), "bytes": path.stat().st_size} for path in sorted(work.iterdir()) if path.is_file()],
            "hash_policy": "small published tables and retained mission authorities; no SIM reopening or large-artifact hashing",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(work, output)
        print(f"{summary['status']}: {output}")
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


if __name__ == "__main__":
    run()
