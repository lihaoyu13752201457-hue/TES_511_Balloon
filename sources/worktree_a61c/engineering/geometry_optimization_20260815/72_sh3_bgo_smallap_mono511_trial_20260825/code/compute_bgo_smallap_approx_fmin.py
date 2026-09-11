#!/usr/bin/env python3
"""Approximate small-aperture SH3 Fmin by replacing only the PARMA mono-511 template.

This deliberately freezes the flux-closed SH3 non-line background, coincidence
timeline, atmospheric transmission, and signal-survival kernel.  It reports the
requested primary approximation with the frozen SH3 signal kernel and, separately,
a conservative engineering scenario that multiplies that kernel by the purely
geometric direct-through fraction 29598/37194.  Neither scenario is a full new-
geometry broadband/signal/activation closure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import uuid

import numpy as np


SECONDS_PER_DAY = 86400.0
ANCHORS = np.asarray([0, 20, 40, 60, 80], dtype=float)
GEOMETRIC_CLEAR_RAYS = 29598
GEOMETRIC_TOTAL_RAYS = 37194
GEOMETRIC_DIRECT_THROUGH_FRACTION = GEOMETRIC_CLEAR_RAYS / GEOMETRIC_TOTAL_RAYS

SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_PACKAGE67 = Path(
    "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823"
)
DEFAULT_LINE_RESPONSE = PACKAGE_ROOT / "outputs/01_mono_line_response"
DEFAULT_OUTPUT = PACKAGE_ROOT / "outputs/02_approx_fmin"


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def asimov_required_signal(background: float, target_z: float) -> float:
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)

    def significance(signal: float) -> float:
        return math.sqrt(
            2.0 * ((signal + background) * math.log1p(signal / background) - signal)
        )

    while significance(high) < target_z:
        high *= 2.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if significance(middle) < target_z:
            low = middle
        else:
            high = middle
    return high


def fmin_values(background: float, kernel: float) -> dict[str, float]:
    if kernel <= 0.0:
        raise ValueError("signal kernel must be positive")
    return {
        "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(background) / kernel,
        "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(background) / kernel,
        "Fmin_3sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 3.0) / kernel,
        "Fmin_5sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 5.0) / kernel,
    }


def fmin_with_uncertainty(
    background: float,
    background_sigma: float,
    kernel: float,
    signal_relative_sigma: float,
) -> dict[str, dict[str, float]]:
    values = fmin_values(background, kernel)
    background_relative_sigma = background_sigma / background
    result: dict[str, dict[str, float]] = {}
    for z in (3.0, 5.0):
        gaussian_key = f"Fmin_{int(z)}sigma_gaussian_ph_cm2_s"
        gaussian_value = values[gaussian_key]
        gaussian_relative = math.hypot(
            0.5 * background_relative_sigma,
            signal_relative_sigma,
        )
        result[gaussian_key] = {
            "value": gaussian_value,
            "standard_error": gaussian_value * gaussian_relative,
            "relative_standard_error": gaussian_relative,
        }

        asimov_key = f"Fmin_{int(z)}sigma_poisson_asimov_ph_cm2_s"
        asimov_value = values[asimov_key]
        required_signal = asimov_required_signal(background, z)
        logarithm = math.log1p(required_signal / background)
        derivative = (required_signal / background - logarithm) / logarithm
        asimov_sigma = math.hypot(
            derivative * background_sigma / kernel,
            asimov_value * signal_relative_sigma,
        )
        result[asimov_key] = {
            "value": asimov_value,
            "standard_error": asimov_sigma,
            "relative_standard_error": asimov_sigma / asimov_value,
        }
    return result


def selected_by_bin(path: Path) -> np.ndarray:
    rows = read_csv(path)
    if len(rows) != 80 or [int(row["source_bin80"]) for row in rows] != list(range(80)):
        raise RuntimeError(f"source-bin table is not exactly bins 0..79: {path}")
    return np.asarray([int(row["selected_events"]) for row in rows], dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fold the new small-aperture mono-511 response into the flux-closed "
            "SH3 model-B mission authority."
        )
    )
    parser.add_argument("--package67", type=Path, default=DEFAULT_PACKAGE67)
    parser.add_argument("--line-response", type=Path, default=DEFAULT_LINE_RESPONSE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    p67 = args.package67.resolve()
    new_line_dir = args.line_response.resolve()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.staging-{os.getpid()}-{uuid.uuid4().hex}"
    staging.mkdir(mode=0o755)

    source_dir = p67 / "outputs/00_source_closure"
    old_line_dir = p67 / "outputs/01_line_response_b60"
    old_timeline_dir = p67 / "outputs/03_fluxclosed_timeline_b"

    paths = {
        "mono511_target": source_dir / "mono511_target_81x80.csv",
        "old_line_bins": old_line_dir / "mono_line_final_by_source_bin80.csv",
        "old_line_summary": old_line_dir / "summary.json",
        "old_timeline": old_timeline_dir / "mission_timeline_81nodes.csv",
        "old_timeline_summary": old_timeline_dir / "summary.json",
        "new_line_bins": new_line_dir / "mono_line_final_by_source_bin80.csv",
        "new_line_summary": new_line_dir / "summary.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    old_line_summary = read_json(paths["old_line_summary"])
    new_line_summary = read_json(paths["new_line_summary"])
    old_timeline_summary = read_json(paths["old_timeline_summary"])
    old_n = selected_by_bin(paths["old_line_bins"])
    new_n = selected_by_bin(paths["new_line_bins"])
    old_weight = 1.0 / float(old_line_summary["physical_exposure_s"])
    new_weight = 1.0 / float(new_line_summary["physical_exposure_s"])

    if int(old_n.sum()) != int(old_line_summary["w2_final_selected_events"]):
        raise RuntimeError("old SH3 bin counts do not close to final selection")
    if int(new_n.sum()) != int(new_line_summary["w2_final_selected_events"]):
        raise RuntimeError("small-aperture bin counts do not close to final selection")
    if not math.isclose(
        float(old_n.sum()) * old_weight,
        float(old_line_summary["w2_final_rate_cps"]),
        rel_tol=2e-14,
    ):
        raise RuntimeError("old SH3 day-15 line rate does not close")
    if not math.isclose(
        float(new_n.sum()) * new_weight,
        float(new_line_summary["w2_final_rate_cps"]),
        rel_tol=2e-14,
    ):
        raise RuntimeError("small-aperture day-15 line rate does not close")

    # The old and new samples may contain different incident-photon totals.  Each
    # is normalized by its own summed physical exposure, so matching N_incident is
    # neither required nor used in the fold.
    old_incident = int(old_line_summary["incident_photons"])
    new_incident = int(new_line_summary["incident_photons"])

    target_rows = read_csv(paths["mono511_target"])
    if len(target_rows) != 81 * 80:
        raise RuntimeError("mono511 target table is not 81x80")
    importance = np.zeros((81, 80), dtype=float)
    days = np.full(81, np.nan, dtype=float)
    seen = set()
    for row in target_rows:
        node = int(row["time_bin_id"])
        source_bin = int(row["source_bin80"])
        key = (node, source_bin)
        if key in seen:
            raise RuntimeError(f"duplicate mono511 target row: {key}")
        seen.add(key)
        importance[node, source_bin] = float(row["importance_ratio"])
        day = float(row["day_mid"])
        if math.isnan(days[node]):
            days[node] = day
        elif days[node] != day:
            raise RuntimeError(f"inconsistent day at node {node}")
    expected_keys = {(node, source_bin) for node in range(81) for source_bin in range(80)}
    if seen != expected_keys:
        raise RuntimeError("mono511 target node/bin coverage is incomplete")

    timeline_rows = read_csv(paths["old_timeline"])
    if len(timeline_rows) != 81 or [int(row["time_bin_id"]) for row in timeline_rows] != list(range(81)):
        raise RuntimeError("old SH3 mission timeline is not exactly nodes 0..80")
    timeline_days = np.asarray([float(row["day_mid"]) for row in timeline_rows])
    if not np.array_equal(days, timeline_days):
        raise RuntimeError("source and mission day axes differ")
    timeline_ratio = np.asarray(
        [float(row["interpolated_background_timeline_ratio"]) for row in timeline_rows]
    )
    direct_other = np.asarray([float(row["direct_other_cps"]) for row in timeline_rows])
    direct_gamma = np.asarray(
        [float(row["direct_gamma_continuum_cps"]) for row in timeline_rows]
    )
    signal_kernel = np.asarray(
        [float(row["conditional_signal_kernel_cm2"]) for row in timeline_rows]
    )
    geometric_signal_kernel = signal_kernel * GEOMETRIC_DIRECT_THROUGH_FRACTION

    direct_old_line = importance @ (old_n * old_weight)
    direct_new_line = importance @ (new_n * new_weight)
    # Flux conservation: direct_gamma is the package67 coarse-bin-de-lined
    # continuum.  Add exactly one monoenergetic replacement line, never the line
    # on top of the original line-containing broadband total.
    direct_new_total = direct_other + direct_gamma + direct_new_line
    mature_new_total = direct_new_total * timeline_ratio

    trapz = getattr(np, "trapezoid", None) or np.trapz
    bin_coefficients = np.asarray(
        [
            float(trapz(importance[:, source_bin] * timeline_ratio, days)) * SECONDS_PER_DAY
            for source_bin in range(80)
        ]
    )
    old_line_counts = float(np.sum(old_n * old_weight * bin_coefficients))
    new_line_counts = float(np.sum(new_n * new_weight * bin_coefficients))
    old_line_variance = float(np.sum(old_n * (old_weight * bin_coefficients) ** 2))
    new_line_variance = float(np.sum(new_n * (new_weight * bin_coefficients) ** 2))

    old_line_authority = old_timeline_summary["mission_transport_components"]["atm511"]
    if not math.isclose(
        old_line_counts,
        float(old_line_authority["integrated_background_counts"]),
        rel_tol=3e-12,
    ):
        raise RuntimeError("independent old-line mission count reproduction failed")
    if not math.isclose(
        old_line_variance,
        float(old_line_authority["sum_W_i2_counts2"]),
        rel_tol=3e-12,
    ):
        raise RuntimeError("independent old-line mission variance reproduction failed")

    old_components = old_timeline_summary["mission_transport_components"]
    frozen_other_counts = float(old_components["other"]["integrated_background_counts"])
    frozen_gamma_counts = float(
        old_components["gamma_continuum"]["integrated_background_counts"]
    )
    frozen_other_variance = float(old_components["other"]["sum_W_i2_counts2"])
    frozen_gamma_variance = float(old_components["gamma_continuum"]["sum_W_i2_counts2"])
    new_background = frozen_other_counts + frozen_gamma_counts + new_line_counts
    new_transport_variance = frozen_other_variance + frozen_gamma_variance + new_line_variance
    new_transport_sigma = math.sqrt(new_transport_variance)

    anchor_errors = np.asarray(
        [
            float(
                old_timeline_summary["anchors"][str(int(node))][
                    "timeline_to_direct_ratio_standard_error"
                ]
            )
            for node in ANCHORS
        ]
    )
    node_axis = np.arange(81, dtype=float)
    ratio_coefficients = []
    for index in range(len(ANCHORS)):
        basis = np.zeros(len(ANCHORS), dtype=float)
        basis[index] = 1.0
        interpolated = np.interp(node_axis, ANCHORS, basis)
        ratio_coefficients.append(
            float(trapz(direct_new_total * interpolated, days)) * SECONDS_PER_DAY
        )
    new_timeline_sigma = float(
        np.sqrt(np.sum((np.asarray(ratio_coefficients) * anchor_errors) ** 2))
    )
    new_background_sigma = math.hypot(new_transport_sigma, new_timeline_sigma)
    new_background_relative_sigma = new_background_sigma / new_background

    old_final = old_timeline_summary["mission_final_20day"]
    old_background = float(old_final["cumulative_background_counts"])
    signal_counts_per_unit_flux = float(old_final["cumulative_signal_counts_per_unit_flux"])
    independently_integrated_signal_kernel = float(trapz(signal_kernel, days)) * SECONDS_PER_DAY
    if not math.isclose(
        independently_integrated_signal_kernel,
        signal_counts_per_unit_flux,
        rel_tol=3e-12,
    ):
        raise RuntimeError("frozen SH3 signal kernel integration failed")
    old_fmins_recomputed = fmin_values(old_background, signal_counts_per_unit_flux)
    for key, value in old_fmins_recomputed.items():
        if not math.isclose(value, float(old_final[key]), rel_tol=3e-12):
            raise RuntimeError(f"old SH3 Fmin reproduction failed: {key}")

    geometric_signal_counts_per_unit_flux = (
        signal_counts_per_unit_flux * GEOMETRIC_DIRECT_THROUGH_FRACTION
    )
    signal_relative_sigma = float(
        old_timeline_summary["statistical_uncertainty"]["signal_combined_relative_sigma"]
    )
    frozen_signal_fmin = fmin_with_uncertainty(
        new_background,
        new_background_sigma,
        signal_counts_per_unit_flux,
        signal_relative_sigma,
    )
    geometric_signal_fmin = fmin_with_uncertainty(
        new_background,
        new_background_sigma,
        geometric_signal_counts_per_unit_flux,
        signal_relative_sigma,
    )

    old_day15 = old_timeline_summary["day15_W2_final_component_rates"]
    new_day15_total = (
        float(old_day15["other"]["rate_cps"])
        + float(old_day15["gamma_continuum"]["rate_cps"])
        + float(new_line_summary["w2_final_rate_cps"])
    )

    cumulative_background = 0.0
    cumulative_frozen_kernel = 0.0
    cumulative_geometric_kernel = 0.0
    cumulative_new_line = 0.0
    output_timeline = []
    for node in range(81):
        if node > 0:
            dt = (days[node] - days[node - 1]) * SECONDS_PER_DAY
            cumulative_background += 0.5 * (
                mature_new_total[node - 1] + mature_new_total[node]
            ) * dt
            cumulative_frozen_kernel += 0.5 * (
                signal_kernel[node - 1] + signal_kernel[node]
            ) * dt
            cumulative_geometric_kernel += 0.5 * (
                geometric_signal_kernel[node - 1] + geometric_signal_kernel[node]
            ) * dt
            new_line_rate_previous = direct_new_line[node - 1] * timeline_ratio[node - 1]
            new_line_rate_current = direct_new_line[node] * timeline_ratio[node]
            cumulative_new_line += 0.5 * (
                new_line_rate_previous + new_line_rate_current
            ) * dt
        row = {
            "time_bin_id": node,
            "day_mid": float(days[node]),
            "direct_other_cps_frozen_sh3": float(direct_other[node]),
            "direct_gamma_continuum_cps_fluxclosed_frozen_sh3": float(direct_gamma[node]),
            "direct_atm511_cps_bgo_smallap": float(direct_new_line[node]),
            "direct_total_cps_approx": float(direct_new_total[node]),
            "interpolated_background_timeline_ratio_frozen_sh3": float(timeline_ratio[node]),
            "mature_background_cps_approx": float(mature_new_total[node]),
            "cumulative_atm511_counts_bgo_smallap": cumulative_new_line,
            "cumulative_background_counts_approx": cumulative_background,
            "cumulative_signal_counts_per_unit_flux_frozen_sh3": cumulative_frozen_kernel,
            "cumulative_signal_counts_per_unit_flux_geometric_direct_through": (
                cumulative_geometric_kernel
            ),
        }
        if cumulative_frozen_kernel > 0.0:
            for key, value in fmin_values(
                cumulative_background,
                cumulative_frozen_kernel,
            ).items():
                row[f"frozen_sh3_signal__{key}"] = value
            for key, value in fmin_values(
                cumulative_background,
                cumulative_geometric_kernel,
            ).items():
                row[f"geometric_signal__{key}"] = value
        else:
            for key in fmin_values(1.0, 1.0):
                row[f"frozen_sh3_signal__{key}"] = ""
                row[f"geometric_signal__{key}"] = ""
        output_timeline.append(row)

    if not math.isclose(cumulative_background, new_background, rel_tol=3e-12):
        raise RuntimeError("new total background component/trapezoid closure failed")
    if not math.isclose(cumulative_new_line, new_line_counts, rel_tol=3e-12):
        raise RuntimeError("new line component/trapezoid closure failed")
    if not math.isclose(
        cumulative_frozen_kernel,
        signal_counts_per_unit_flux,
        rel_tol=3e-12,
    ):
        raise RuntimeError("new timeline frozen signal-kernel closure failed")
    if not math.isclose(
        cumulative_geometric_kernel,
        geometric_signal_counts_per_unit_flux,
        rel_tol=3e-12,
    ):
        raise RuntimeError("new timeline geometric signal-kernel closure failed")

    frozen_g3 = frozen_signal_fmin["Fmin_3sigma_gaussian_ph_cm2_s"]
    geometric_g3 = geometric_signal_fmin["Fmin_3sigma_gaussian_ph_cm2_s"]
    frozen_a3 = frozen_signal_fmin["Fmin_3sigma_poisson_asimov_ph_cm2_s"]
    geometric_a3 = geometric_signal_fmin["Fmin_3sigma_poisson_asimov_ph_cm2_s"]

    summary = {
        "status": "PASS__APPROX_BGO_SMALLAP_FMIN_UNDER_FROZEN_SH3_NONLINE_ASSUMPTION",
        "schema_version": 1,
        "result_scope": (
            "conditional engineering approximation; not a full small-aperture "
            "broadband/signal/activation closure"
        ),
        "assumptions": {
            "other_background": "frozen from SH3 model-B 81-node authority",
            "gamma_continuum": (
                "flux-conserving coarse-bin-de-lined continuum frozen from SH3 "
                "model-B 81-node authority"
            ),
            "atm511": (
                "replaced by the small-aperture 510.99895-keV response and folded "
                "with the same 81x80 PARMA target"
            ),
            "new_geometry_activation_near_511": (
                "assumed absent for this requested approximation; no new activation "
                "component is added"
            ),
            "timeline_coincidence_ratio": "frozen SH3 five-anchor interpolation",
            "primary_signal_response": (
                "frozen SH3 effective area, atmospheric transmission, and "
                "accidental-survival kernel"
            ),
            "geometric_signal_response": (
                "frozen SH3 signal kernel multiplied by 29598/37194; purely "
                "geometric direct-through estimate, not a transported signal response"
            ),
        },
        "flux_conservation": {
            "formula": (
                "frozen other + frozen (broadband gamma minus coarse-bin line) + "
                "new monoenergetic line"
            ),
            "line_double_counted": False,
        },
        "parma": {
            "line_energy_keV": 510.99895,
            "day15_full_space_flux_ph_cm2_s": 0.16651547160226118,
            "angular_components_equal_mu": 80,
        },
        "line_statistics": {
            "incident_statistics_match_required": False,
            "normalization": "each response uses its own 1/physical_exposure_s",
            "old_open_sh3_incident_photons": old_incident,
            "new_bgo_smallap_incident_photons": new_incident,
            "new_over_old_incident_ratio": new_incident / old_incident,
            "old_open_sh3_physical_exposure_s": float(
                old_line_summary["physical_exposure_s"]
            ),
            "new_bgo_smallap_physical_exposure_s": float(
                new_line_summary["physical_exposure_s"]
            ),
            "old_open_sh3_selected_events": int(old_n.sum()),
            "new_bgo_smallap_selected_events": int(new_n.sum()),
            "old_open_sh3_day15_line_rate_cps": float(
                old_line_summary["w2_final_rate_cps"]
            ),
            "new_bgo_smallap_day15_line_rate_cps": float(
                new_line_summary["w2_final_rate_cps"]
            ),
        },
        "day15_reference": {
            "old_sh3_total_rate_cps": float(old_day15["total"]["rate_cps"]),
            "approx_bgo_smallap_total_rate_cps": new_day15_total,
            "ratio": new_day15_total / float(old_day15["total"]["rate_cps"]),
        },
        "mission_20day": {
            "old_sh3_atm511_counts": old_line_counts,
            "approx_bgo_smallap_atm511_counts": new_line_counts,
            "atm511_ratio": new_line_counts / old_line_counts,
            "frozen_other_counts": frozen_other_counts,
            "frozen_gamma_continuum_counts": frozen_gamma_counts,
            "old_sh3_total_background_counts": old_background,
            "approx_bgo_smallap_total_background_counts": new_background,
            "total_background_ratio": new_background / old_background,
            "old_sh3_Fmin": {
                key: float(old_final[key]) for key in fmin_values(1.0, 1.0)
            },
            "primary_frozen_sh3_signal": {
                "signal_counts_per_unit_flux": signal_counts_per_unit_flux,
                "Fmin": frozen_signal_fmin,
                "gaussian_3sigma_threshold_ratio_new_over_old": (
                    frozen_g3["value"]
                    / float(old_final["Fmin_3sigma_gaussian_ph_cm2_s"])
                ),
            },
            "conservative_geometric_direct_through_signal": {
                "geometric_clear_rays": GEOMETRIC_CLEAR_RAYS,
                "geometric_total_rays": GEOMETRIC_TOTAL_RAYS,
                "geometric_direct_through_fraction": GEOMETRIC_DIRECT_THROUGH_FRACTION,
                "signal_counts_per_unit_flux": geometric_signal_counts_per_unit_flux,
                "Fmin": geometric_signal_fmin,
                "gaussian_3sigma_threshold_ratio_new_over_old": (
                    geometric_g3["value"]
                    / float(old_final["Fmin_3sigma_gaussian_ph_cm2_s"])
                ),
                "caveat": (
                    "pure geometry scaling only; it does not replace a transported "
                    "signal response"
                ),
            },
        },
        "uncertainty": {
            "new_atm511_transport_sigma_counts": math.sqrt(new_line_variance),
            "new_total_transport_sigma_counts": new_transport_sigma,
            "new_timeline_replay_sigma_counts": new_timeline_sigma,
            "new_background_combined_sigma_counts": new_background_sigma,
            "new_background_combined_relative_sigma": new_background_relative_sigma,
            "frozen_signal_combined_relative_sigma": signal_relative_sigma,
            "geometric_fraction_treated_as_exact_for_reported_statistical_error": True,
            "note": (
                "MC/statistical uncertainty only; approximation/systematic error "
                "from freezing non-line/signal responses and from geometric signal "
                "scaling is not quantified"
            ),
        },
        "validation": {
            "old_line_mission_counts_reproduced": True,
            "old_line_mission_variance_reproduced": True,
            "old_sh3_Fmin_reproduced": True,
            "new_line_81node_count_and_variance_folded_from_bin80": True,
            "component_sum_matches_trapezoid_total": True,
            "frozen_signal_kernel_reproduced": True,
            "geometric_signal_kernel_ratio_reproduced": True,
            "incident_statistics_equality_not_required": True,
        },
        "inputs": {
            name: {"path": str(path), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "outputs": [
            "approx_fmin_summary.json",
            "mission_timeline_81nodes_approx.csv",
            "README.md",
        ],
    }

    write_json(staging / "approx_fmin_summary.json", summary)
    write_csv(staging / "mission_timeline_81nodes_approx.csv", output_timeline)
    readme = f"""# SH3 active-BGO small-aperture conditional Fmin approximation

This is a **conditional approximation**, not a full new-geometry background,
signal, or activation closure.  It uses the flux-conserving combination
`frozen other + frozen de-lined broadband gamma + new PARMA mono-511 line`.

## 20-day results

Primary, frozen SH3 signal kernel:

- Gaussian 3 sigma: `{frozen_g3['value']:.12g} +/- {frozen_g3['standard_error']:.12g} ph cm^-2 s^-1`
- Poisson Asimov 3 sigma: `{frozen_a3['value']:.12g} +/- {frozen_a3['standard_error']:.12g} ph cm^-2 s^-1`

Conservative geometric signal scenario (kernel x `{GEOMETRIC_DIRECT_THROUGH_FRACTION:.12g}`):

- Gaussian 3 sigma: `{geometric_g3['value']:.12g} +/- {geometric_g3['standard_error']:.12g} ph cm^-2 s^-1`
- Poisson Asimov 3 sigma: `{geometric_a3['value']:.12g} +/- {geometric_a3['standard_error']:.12g} ph cm^-2 s^-1`

The geometric scenario is only a ray-clearance scaling (`{GEOMETRIC_CLEAR_RAYS}/{GEOMETRIC_TOTAL_RAYS}`),
not a transported signal response.  Reported errors are statistical only and do
not quantify the approximation error from frozen non-line/signal responses.
"""
    (staging / "README.md").write_text(readme, encoding="utf-8")
    os.rename(staging, output)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "output": str(output),
                "primary_frozen_sh3_signal": {
                    "gaussian_3sigma": frozen_g3,
                    "asimov_3sigma": frozen_a3,
                },
                "conservative_geometric_signal": {
                    "direct_through_fraction": GEOMETRIC_DIRECT_THROUGH_FRACTION,
                    "gaussian_3sigma": geometric_g3,
                    "asimov_3sigma": geometric_a3,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
