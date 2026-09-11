#!/usr/bin/env python3
"""Independent arithmetic and implementation validation for the final M05 result."""

from __future__ import annotations

import ast
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np


PACKAGE = Path(__file__).resolve().parents[1]
CONFIG = PACKAGE / "modified/analysis_inputs_optv3_B.json"
CATALOG = PACKAGE / "outputs/04_event_catalog_step05_m05_fixed_20260820"
TIMELINE = PACKAGE / "outputs/05_mature_timeline_m05_fixed_20260820"
OUT = PACKAGE / "outputs/06_final_statistics_validation_20260820.json"
ORIGINAL_STEP05 = Path("/home/ubuntu/TES_511_Balloon/old/code/tools/build_v3p5_centerfinger_step05_l1_response.py")
PORTED_STEP05 = PACKAGE / "modified/step05_side_compton.py"
SECONDS_PER_DAY = 86_400.0


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def function_body_dumps(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class RemoveImports(ast.NodeTransformer):
        def visit_Import(self, node):
            return None

        def visit_ImportFrom(self, node):
            return None

    output = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        cleaned = RemoveImports().visit(ast.Module(body=node.body, type_ignores=[]))
        ast.fix_missing_locations(cleaned)
        output[node.name] = ast.dump(cleaned, include_attributes=False)
    return output


def read_eventlist(path: Path) -> tuple[np.ndarray, np.ndarray]:
    positions = []
    directions = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 13:
                continue
            positions.append([float(fields[5]), float(fields[6]), float(fields[7])])
            directions.append([float(fields[8]), float(fields[9]), float(fields[10])])
    return np.asarray(positions), np.asarray(directions)


def main() -> int:
    cfg = load(CONFIG)
    summary = load(TIMELINE / "summary.json")
    catalog_summary = load(CATALOG / "summary.json")
    categories = load(CATALOG / "category_registry.json")["categories"]
    mission = rows(TIMELINE / "mission_timeline_81nodes.csv")
    scales = sorted(
        rows(Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon") / cfg["mission"]["family_scales"]),
        key=lambda row: int(row["time_bin_id"]),
    )
    timeline_code = load_module("validate_optv3_timeline", PACKAGE / "modified/run_mature_timeline_sh3_optv3_B.py")
    activation = load(Path(cfg["campaigns"]["activation_manifest"]))
    curves, day15 = timeline_code.build_inventory_curves(categories, scales, activation, [])
    with np.load(CATALOG / "combined_event_catalog.npz", allow_pickle=False) as handle:
        w2_flags = handle["w2_flags"]
    counts = np.asarray([int(row["event_count"]) for row in categories], dtype=np.int64)
    selected = np.asarray([
        int(np.count_nonzero(
            w2_flags[int(row["event_start"]):int(row["event_start"]) + int(row["event_count"])]
            & timeline_code.STAGE_BITS["compton_trajectory_veto"]
        ))
        for row in categories
    ], dtype=np.int64)

    integrated_weights = np.zeros(len(categories), dtype=np.float64)
    previous_day = None
    previous_weights = None
    direct_differences = []
    for node, mission_row in enumerate(mission):
        rates = timeline_code.category_rates_at_node(categories, scales[node], curves, day15, node)
        per_event = np.divide(rates, counts, out=np.zeros_like(rates), where=counts > 0)
        direct = float(np.sum(selected * per_event))
        direct_differences.append(direct - float(mission_row["direct_w2_final_no_coincidence_cps"]))
        corrected = per_event * float(mission_row["interpolated_background_timeline_ratio"])
        day = float(mission_row["day_mid"])
        if previous_day is not None:
            dt = (day - previous_day) * SECONDS_PER_DAY
            integrated_weights += 0.5 * (previous_weights + corrected) * dt
        previous_day = day
        previous_weights = corrected

    background = float(np.sum(selected * integrated_weights))
    variance = float(np.sum(selected * integrated_weights**2))
    transport_sigma = math.sqrt(variance)
    mission_days = np.asarray([float(row["day_mid"]) for row in mission])
    kernel = np.asarray([float(row["conditional_signal_kernel_cm2"]) for row in mission])
    trapz = getattr(np, "trapezoid", None) or np.trapz
    signal_per_flux = float(trapz(kernel, mission_days) * SECONDS_PER_DAY)
    fmin_gaussian = 3.0 * math.sqrt(background) / signal_per_flux
    fmin_asimov = float(summary["fmin_ph_cm2_s"]["fmin_3sigma_asimov_ph_cm2_s"])
    asimov_signal = fmin_asimov * signal_per_flux
    asimov_z = math.sqrt(2.0 * ((asimov_signal + background) * math.log1p(asimov_signal / background) - asimov_signal))

    uncertainty = summary["statistical_uncertainty"]
    propagated_relative = math.sqrt(
        (0.5 * float(uncertainty["background_combined_relative_sigma"])) ** 2
        + float(uncertainty["signal_combined_relative_sigma"]) ** 2
    )
    propagated_sigma = fmin_gaussian * propagated_relative

    old_ast = function_body_dumps(ORIGINAL_STEP05)
    new_ast = function_body_dumps(PORTED_STEP05)
    step05_functions = (
        "unit", "representative_points_box", "orthonormal_basis_batch", "compton_cos_theta",
        "segments_intersect_disk_2d", "sample_cone_side_disk", "sequence_metrics",
        "classify_side_compton", "side_keep_from_hits",
    )
    step05_equal = {name: old_ast[name] == new_ast[name] for name in step05_functions}

    original_eventlist = Path(
        "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/"
        "outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
    )
    transformed_eventlist = Path(cfg["signal"]["eventlist"])
    old_pos, old_dir = read_eventlist(original_eventlist)
    new_pos, new_dir = read_eventlist(transformed_eventlist)
    expected_translation = np.asarray(cfg["signal"]["beam_transform_world"]["T"], dtype=float)
    translation_residual = new_pos - old_pos - expected_translation

    checks = {
        "catalog_status_pass": str(catalog_summary["status"]).startswith("PASS__"),
        "timeline_status_pass": str(summary["status"]).startswith("PASS__"),
        "mission_nodes_81": len(mission) == 81,
        "direct_rate_closure": max(abs(value) for value in direct_differences) < 1e-14,
        "background_count_closure": math.isclose(background, float(summary["integrated_background_counts_20d"]), rel_tol=2e-12, abs_tol=1e-6),
        "transport_sigma_closure": math.isclose(transport_sigma, float(uncertainty["background_transport_MC_sigma_counts"]), rel_tol=2e-12),
        "signal_kernel_closure": math.isclose(signal_per_flux, float(summary["signal_counts_per_flux_cm2_s"]), rel_tol=2e-12),
        "gaussian_fmin_closure": math.isclose(fmin_gaussian, float(summary["fmin_ph_cm2_s"]["fmin_3sigma_gauss_ph_cm2_s"]), rel_tol=2e-12),
        "asimov_z_closure": math.isclose(asimov_z, 3.0, rel_tol=0.0, abs_tol=1e-12),
        "uncertainty_closure": math.isclose(propagated_sigma, float(summary["fmin_3sigma_gaussian_standard_error_ph_cm2_s"]), rel_tol=2e-12),
        "step05_pure_logic_equivalent": all(step05_equal.values()),
        "signal_eventlist_row_closure": len(old_pos) == len(new_pos) == int(cfg["signal"]["eventlist_rows"]),
        "signal_translation_closure": float(np.max(np.abs(translation_residual))) < 5e-7,
        "signal_directions_unchanged": float(np.max(np.abs(new_dir - old_dir))) == 0.0,
    }
    result = {
        "schema_version": 1,
        "status": "PASS__FINAL_M05_STATISTICS_INDEPENDENT_VALIDATION" if all(checks.values()) else "FAIL__FINAL_M05_STATISTICS_INDEPENDENT_VALIDATION",
        "checks": checks,
        "recomputed": {
            "integrated_background_counts_20d": background,
            "background_transport_MC_sigma_counts": transport_sigma,
            "weighted_effective_transport_survivors": background**2 / variance,
            "signal_counts_per_unit_flux": signal_per_flux,
            "fmin_3sigma_gaussian_ph_cm2_s": fmin_gaussian,
            "fmin_3sigma_asimov_test_z": asimov_z,
            "fmin_relative_standard_error": propagated_relative,
            "fmin_standard_error_ph_cm2_s": propagated_sigma,
        },
        "step05_function_body_equivalence": step05_equal,
        "signal_transform": {
            "rows": len(new_pos),
            "expected_translation_world_cm": expected_translation.tolist(),
            "max_abs_translation_residual_cm": float(np.max(np.abs(translation_residual))),
            "max_abs_direction_change": float(np.max(np.abs(new_dir - old_dir))),
            "direction_norm_min": float(np.min(np.linalg.norm(new_dir, axis=1))),
            "direction_norm_max": float(np.max(np.linalg.norm(new_dir, axis=1))),
        },
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
