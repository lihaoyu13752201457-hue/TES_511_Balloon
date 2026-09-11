#!/usr/bin/env python3
"""Build the machine-readable SH3 Si phonon/TES evaluation from run products."""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path("/home/ubuntu/neutron_fen")
TT_S = 1911.8824


def read_json(path: Path):
    return json.loads(path.read_text())


def read_rows(path: Path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def f(row, key):
    return float(row[key])


def candidate_table(path: Path):
    return {
        row["candidate"]: {
            "eta": f(row, "sensor_eta"),
            "eta_mc_standard_error": f(row, "eta_mc_standard_error"),
            "reconstructed_mean_keV": f(row, "reconstructed_mean_keV"),
            "roi_probability": f(row, "gaussian_roi_probability"),
            "sensor_channel_hit_multiplicity": int(row["sensor_channel_hit_multiplicity"]),
            "sensor_channel_effective_multiplicity_ipr": f(row, "sensor_channel_effective_multiplicity_ipr"),
            "arrival_q10_ns": f(row, "sensor_arrival_q10_ns"),
            "arrival_q50_ns": f(row, "sensor_arrival_q50_ns"),
            "arrival_q90_ns": f(row, "sensor_arrival_q90_ns"),
            "arrival_q99_ns": f(row, "sensor_arrival_q99_ns"),
            "prompt_fraction_lt_1us": f(row, "sensor_prompt_fraction"),
            "intermediate_fraction_1_to_10us": f(row, "sensor_intermediate_fraction"),
            "late_fraction_ge_10us": f(row, "sensor_late_fraction"),
        }
        for row in read_rows(path)
    }


def main():
    event_data = read_json(ROOT / "outputs/unvetoed_events.json")
    direct = read_json(ROOT / "outputs/candidate_direct_tes_channels.json")
    geometry = read_json(ROOT / "outputs/sh3_unit_geometry.json")
    scenario_root = ROOT / "runs/staircase/04_all86"
    scenario_rows = {}
    for analysis_path in sorted(scenario_root.glob("*/analysis.json")):
        data = read_json(analysis_path)
        scenario_rows[analysis_path.parent.name] = {
            "configuration": data["configuration"],
            "global_sensor_eta": data["energy_keV"]["global_sensor_eta"],
            "energy_closure_fraction": data["energy_keV"]["global_closure_fraction"],
            "expected_roi_count": data["roi_expectation"]["sum_expected_counts"],
            "expected_roi_rate_per_s": data["roi_expectation"]["rate_per_s"],
            "analysis_path": str(analysis_path),
            "analysis_sha256": sha(analysis_path),
        }

    nominal_candidates = candidate_table(
        ROOT / "runs/staircase/02_exact_ABC/nominal_envelope_point/events.csv"
    )
    optimistic_candidates = candidate_table(
        ROOT / "runs/staircase/02_exact_ABC/optimistic/events.csv"
    )
    tuned_high_candidates = candidate_table(
        ROOT / "runs/staircase/02_exact_ABC/tuned_high_bath0p06/events.csv"
    )

    replicate_rows = []
    for path in sorted((ROOT / "runs/staircase/02c_candidate_C_replicates").glob("rep*/events.csv")):
        replicate_rows.append(read_rows(path)[0])
    replica_fields = {
        "eta": "sensor_eta",
        "reconstructed_mean_keV": "reconstructed_mean_keV",
        "roi_probability": "gaussian_roi_probability",
        "arrival_q10_ns": "sensor_arrival_q10_ns",
        "arrival_q50_ns": "sensor_arrival_q50_ns",
        "arrival_q90_ns": "sensor_arrival_q90_ns",
        "arrival_q99_ns": "sensor_arrival_q99_ns",
        "prompt_fraction_lt_1us": "sensor_prompt_fraction",
        "intermediate_fraction_1_to_10us": "sensor_intermediate_fraction",
        "late_fraction_ge_10us": "sensor_late_fraction",
        "sensor_channel_effective_multiplicity_ipr": "sensor_channel_effective_multiplicity_ipr",
    }
    c_replicates = {
        "configuration": {
            "replicates": len(replicate_rows),
            "packets_per_event_layer_group": 8192,
            "packet_energy_meV": 62.0,
            "sensor_area_scale": 0.12,
            "sensor_absorption_probability_per_encounter": 0.3,
            "bath_absorption_probability_per_encounter": 0.1,
            "specular_probability": 0.0,
        },
        "statistics": {},
    }
    for output_name, source_name in replica_fields.items():
        values = [f(row, source_name) for row in replicate_rows]
        c_replicates["statistics"][output_name] = {
            "mean": statistics.mean(values),
            "sample_standard_deviation": statistics.stdev(values),
            "standard_error_of_mean": statistics.stdev(values) / math.sqrt(len(values)),
            "min": min(values),
            "max": max(values),
        }
    c_replicates["statistics"]["conditional_rate_per_s"] = {
        key: value / TT_S
        for key, value in c_replicates["statistics"]["roi_probability"].items()
    }

    point = {}
    for name in ("point_baseline_p1024_e2p7", "point_baseline_p128_e30", "point_baseline_p64_e62"):
        rows = read_rows(ROOT / "runs" / name / "events.csv")
        by_position = {}
        for label in ("center_front", "center_middle", "center_back", "edge_front", "edge_middle", "edge_back"):
            values = [f(row, "sensor_eta") for row in rows if label in row["original_event_key"]]
            by_position[label] = {"mean_eta_over_five_energies": statistics.mean(values),
                                  "min": min(values), "max": max(values)}
        point[name] = {
            "configuration": read_json(ROOT / "runs" / name / "summary.json")["configuration"],
            "position_results": by_position,
            "mean_eta_all_30_points": statistics.mean(f(row, "sensor_eta") for row in rows),
        }

    algebraic_upper_count = 3.0
    evaluation = {
        "schema_version": 1,
        "generated_at_local": "2026-09-03T18:10:00+08:00",
        "status": "COMPLETE_CONDITIONAL__DEVICE_INTERFACES_AND_TES_ELECTROTHERMAL_MODEL_UNSPECIFIED",
        "scope": {
            "histories": 10_000_000,
            "equivalent_time_s": TT_S,
            "unvetoed_si_events": 86,
            "strict_si_elastic_recoil_events": 51,
            "si_hit_records": 327,
            "total_unvetoed_si_energy_keV": sum(float(e["si_total_keV"]) for e in event_data["events"]),
            "bgo_cut_keV": 50.0,
            "roi_keV_half_open": [510.58, 511.42],
            "gaussian_response_fwhm_keV": 0.420,
        },
        "model_boundary": {
            "computed": "G4CMP anisotropic Si acoustic-phonon transport, isotope scattering, anharmonic downconversion, boundary reflection/absorption, weighted surface collection, per-pixel timing and energy.",
            "not_computed": "Full G4CMPEnergyPartition recoil-to-charge/phonon production, electric-field charge drift, physical Si/SiO2/SiNx/Ta/AlMn interface transmission, quasiparticle diffusion, and TES electrothermal pulse reconstruction.",
            "interpretation": "The simulation is an athermal interface-response kernel and parameter envelope, not a calibrated prediction of absolute TES efficiency.",
            "miller_orientation": "[100] normal was used as an explicit reference assumption; actual wafer orientation is absent from SH3 geometry.",
        },
        "geometry": {
            "si_slab_mm": [36.0, 36.0, 0.3],
            "pixels_per_layer": 376,
            "ta_projected_area_fraction": 846.0 / 1296.0,
            "mass_proxy_has_physical_si_ta_contact": False,
            "mass_proxy_has_physical_si_cu_contact": False,
            "audit_path": str(ROOT / "outputs/sh3_unit_geometry.json"),
        },
        "point_energy_depth_edge_validation": point,
        "all_86_scenario_envelope": scenario_rows,
        "candidate_results": {
            "required_eta_for_511keV": {
                "A": event_data["candidates"]["A"]["eta_for_511keV"],
                "B": event_data["candidates"]["B"]["eta_for_511keV"],
                "C": event_data["candidates"]["C"]["eta_for_511keV"],
            },
            "nominal_envelope_point": nominal_candidates,
            "optimistic_endpoint": optimistic_candidates,
            "tuned_high_bath0p06": tuned_high_candidates,
            "candidate_C_tuned_replicates": c_replicates,
            "direct_tes_channels": direct,
            "interpretation": {
                "A": "Individually reachable only toward a near-ideal large-area sensor/weak-bath endpoint; not established by the uncalibrated device model.",
                "B": "Individually reachable toward the same high-collection family; not established by the uncalibrated device model.",
                "C": "A moderate-area parameter point can reproduce the required ~13.6% collection, but the narrow-ROI probability remains numerically and systematically sensitive.",
                "simultaneous": "No sampled common parameter point placed A, B and C together in the ROI. The high-collection endpoint that approaches A/B drives C far above the ROI; the C-like endpoint drives A/B far below it."
            }
        },
        "rate_statement": {
            "identified_algebraically_feasible_events": 3,
            "calibrated_point_estimate_available": False,
            "robust_lower_bound_per_s": 0.0,
            "conservative_central_algebraic_upper_per_s": algebraic_upper_count / TT_S,
            "conservative_one_sided_95pct_poisson_upper_per_s_if_all_three_count": 0.0040555091296058405,
            "conditional_tuned_C_replicate_average_probability": c_replicates["statistics"]["roi_probability"]["mean"],
            "conditional_tuned_C_rate_per_s": c_replicates["statistics"]["conditional_rate_per_s"]["mean"],
            "conditional_tuned_C_rate_mc_sem_per_s": c_replicates["statistics"]["conditional_rate_per_s"]["standard_error_of_mean"],
            "recommended_SH3_correction": "Do not apply a single central correction until coupon/device data constrain interface transmission, bath loss, crystal orientation and TES transfer function. Carry [0, 1.569e-3]/s as the three-candidate central envelope; use 4.056e-3/s as the associated conservative one-sided 95% transport-sample upper bound."
        },
        "fenics_decision": {
            "used": False,
            "reason": "The missing information is physical boundary conditions and TES/film material data, not PDE solver capacity. A FEniCS slow-thermal solve would add false precision and cannot replace G4CMP athermal transport."
        },
        "self_checks": {
            "all_86_present": len(event_data["events"]) == 86,
            "all_scenario_analyses_have_86_events": all(read_json(Path(v["analysis_path"]))["counts"]["original_events_after_layer_merge"] == 86 for v in scenario_rows.values()),
            "all_scenario_energy_closure_abs_1e-9": all(abs(v["energy_closure_fraction"] - 1) < 1e-9 for v in scenario_rows.values()),
            "candidate_direct_tes_matches_compact_catalog": all(direct["self_checks"].values()),
            "five_C_replicates": len(replicate_rows) == 5,
            "install_manifest_present": (ROOT / "INSTALL_MANIFEST.json").is_file(),
        },
        "key_artifacts_sha256": {
            "INSTALL_MANIFEST.json": sha(ROOT / "INSTALL_MANIFEST.json"),
            "outputs/unvetoed_events.json": sha(ROOT / "outputs/unvetoed_events.json"),
            "outputs/g4cmp_input_manifest.json": sha(ROOT / "outputs/g4cmp_input_manifest.json"),
            "outputs/sh3_unit_geometry.json": sha(ROOT / "outputs/sh3_unit_geometry.json"),
            "outputs/candidate_direct_tes_channels.json": sha(ROOT / "outputs/candidate_direct_tes_channels.json"),
            "config/staircase_scenarios.json": sha(ROOT / "config/staircase_scenarios.json"),
        },
    }
    if not all(evaluation["self_checks"].values()):
        raise SystemExit(f"final self-check failed: {evaluation['self_checks']}")
    out = ROOT / "FINAL_EVALUATION.json"
    out.write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n")
    print(f"PASS {out} sha256={sha(out)}")


if __name__ == "__main__":
    main()
