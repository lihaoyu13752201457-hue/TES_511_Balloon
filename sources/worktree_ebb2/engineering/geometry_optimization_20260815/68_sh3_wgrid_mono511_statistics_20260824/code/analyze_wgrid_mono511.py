#!/usr/bin/env python3
"""Analyze the matched-statistics SH3+W-grid PARMA 510.99895 keV run.

The detector response itself is delegated to the frozen package-67
``analyze_mono_line.py`` model-B implementation.  This wrapper adds an exact
open-frame SH3 comparator, independent-MC error propagation, angular
aggregation, and a transparent incremental-statistics decision.  Every output
is assembled in a unique sibling staging directory and promoted with one
atomic directory rename.

No file below /mnt/data is opened by this wrapper.  The open-frame comparator
is the compact, locally frozen package-67 response.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PACKAGE67 = Path(
    "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823"
)
ANALYZER = PACKAGE67 / "code/analyze_mono_line.py"
OPEN_SH3 = PACKAGE67 / "outputs/01_line_response_b60"
OPEN_FILES = {
    "summary.json": "d6487790c9818f0dde9fef1323e164ae3dc500559381fdfdca6ffd21558de1e2",
    "mono_line_cutflow.csv": "e264f97841eb80ed636293c38da02bbccb69c1a1b3e0b49ab055dc29d3e33986",
    "mono_line_final_by_source_bin80.csv": "b970ee2483eedbb0415497b3e6d59cfed0b3de4eb732ee922fb554dbd9ac5456",
    "MERGE_RECEIPT.json": "feb59daa2ef1bfecaf134da5cb1deef0fe6b09280fe5f3165f5a2b69dc332726",
}

REPO = Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
B_CONFIG = REPO / "DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json"
B_BUILDER = REPO / "DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py"
PARMA_BINS = (
    REPO
    / "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/line/parma511_day15_80bins.csv"
)
METHOD_FILES = {
    ANALYZER: "086bb418c43dce04b94d92ef08324511e34a85541d891abe1f6081c5f5571d8b",
    B_CONFIG: "e2780f3ff5fa85f45403661ac939eaa94331daa6dfa79fe62a062229bce84d53",
    B_BUILDER: "f6d968e8804ed3b64e127786da9c376502d2c7bb85405a7949a8c1c4bb80b401",
    PARMA_BINS: "2f4ae904bf89179fe1709e3a8123ff864f4450e8bcf443389898ea43cd6a5a32",
}

EXPECTED_INCIDENT_PHOTONS = 15_709_417
EXPECTED_EXPOSURE_S = 8343.628079999999
EXPECTED_WEIGHT_CPS = 0.00011985193855860365
EXPECTED_PARMA_FLUX = 0.16651547160226118
PARMA_FRAGMENT_SHA256 = "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6"
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
LINE_TRANSPORT_CONTRACT_SHA256 = "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f"
MAX_EXPOSURE_RELATIVE_DIFFERENCE = 0.002
OPEN_FINAL_RELATIVE_MC_SIGMA = 1.0 / math.sqrt(186.0)
WINDOWS = ("broad_480_550", "w2_510p58_511p42")
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
FINAL_KEY = ("w2_510p58_511p42", "compton_trajectory_veto")
PRE_VETO_KEY = ("w2_510p58_511p42", "pre_veto")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def under_mnt_data(path: Path) -> bool:
    resolved = path.resolve()
    forbidden = Path("/mnt/data")
    return resolved == forbidden or forbidden in resolved.parents


def verify_frozen_authorities() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path, expected in {**METHOD_FILES, **{OPEN_SH3 / k: v for k, v in OPEN_FILES.items()}}.items():
        require(path.is_file(), f"frozen authority is missing: {path}")
        observed = sha256(path)
        require(observed == expected, f"frozen authority hash differs: {path}")
        records.append({"path": str(path), "bytes": path.stat().st_size, "sha256": observed})
    return {"status": "PASS__FROZEN_AUTHORITIES_MATCH", "files": records}


def freeze_inputs(stage: Path) -> dict[str, Any]:
    comparator_dir = stage / "frozen_open_sh3_comparator"
    method_dir = stage / "frozen_method_authority"
    parma_dir = stage / "frozen_parma_authority"
    comparator_dir.mkdir()
    method_dir.mkdir()
    parma_dir.mkdir()

    copies: list[dict[str, Any]] = []
    for name, expected in OPEN_FILES.items():
        source = OPEN_SH3 / name
        target = comparator_dir / name
        shutil.copy2(source, target)
        observed = sha256(target)
        require(observed == expected, f"comparator copy hash differs: {name}")
        copies.append({"role": "open_sh3_comparator", "file": str(target.relative_to(stage)), "sha256": observed})
    for source in (ANALYZER, B_CONFIG, B_BUILDER):
        target = method_dir / source.name
        shutil.copy2(source, target)
        observed = sha256(target)
        require(observed == METHOD_FILES[source], f"method copy hash differs: {source}")
        copies.append({"role": "model_b_method", "file": str(target.relative_to(stage)), "sha256": observed})
    target = parma_dir / PARMA_BINS.name
    shutil.copy2(PARMA_BINS, target)
    observed = sha256(target)
    require(observed == METHOD_FILES[PARMA_BINS], "PARMA-bin table copy hash differs")
    copies.append({"role": "parma_day15_80bin", "file": str(target.relative_to(stage)), "sha256": observed})
    return {"status": "PASS__INPUTS_FROZEN", "copies": copies}


def load_cutflow(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows = read_csv(path)
    expected = {(window, stage) for window in WINDOWS for stage in STAGES}
    require(len(rows) == 10, f"cutflow must have exactly 10 rows: {path}")
    parsed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["window_id"], row["stage"])
        require(key not in parsed, f"duplicate cutflow key: {key}")
        parsed[key] = {
            "model": row["model"],
            "window_id": key[0],
            "stage": key[1],
            "selected_events": int(row["selected_events"]),
            "event_weight_cps": float(row["event_weight_cps"]),
            "weighted_rate_cps": float(row["weighted_rate_cps"]),
            "weighted_mc_sigma_cps": float(row["weighted_mc_sigma_cps"]),
            "effective_selected_events": float(row["effective_selected_events"]),
        }
    require(set(parsed) == expected, f"cutflow keys differ: {path}")
    return parsed


def load_bin80(path: Path) -> dict[int, dict[str, Any]]:
    rows = read_csv(path)
    require(len(rows) == 80, f"source-bin table must have 80 rows: {path}")
    parsed: dict[int, dict[str, Any]] = {}
    for row in rows:
        index = int(row["source_bin80"])
        require(index not in parsed, f"duplicate source bin {index}: {path}")
        parsed[index] = {
            "selected_events": int(row["selected_events"]),
            "weighted_rate_cps": float(row["weighted_rate_cps"]),
        }
    require(set(parsed) == set(range(80)), f"source-bin IDs are not 0..79: {path}")
    return parsed


def load_parma_bins(path: Path) -> dict[int, dict[str, Any]]:
    rows = read_csv(path)
    require(len(rows) == 80, "PARMA angular authority must have 80 rows")
    parsed: dict[int, dict[str, Any]] = {}
    for row in rows:
        index = int(row["theta_bin_id"])
        parsed[index] = {
            "source_id": row["source_id"],
            "direction_label": row["direction_label"],
            "parma_mu_low": float(row["parma_mu_low"]),
            "parma_mu_high": float(row["parma_mu_high"]),
            "line_fraction": float(row["line_fraction"]),
            "line_flux_ph_cm2_s": float(row["line_flux_ph_cm-2_s-1"]),
        }
    require(set(parsed) == set(range(80)), "PARMA angular-bin IDs are not 0..79")
    require(all(parsed[i]["direction_label"] == "down" for i in range(40)), "PARMA down-bin contract differs")
    require(all(parsed[i]["direction_label"] == "up" for i in range(40, 80)), "PARMA up-bin contract differs")
    flux = math.fsum(row["line_flux_ph_cm2_s"] for row in parsed.values())
    require(math.isclose(flux, EXPECTED_PARMA_FLUX, rel_tol=1e-13, abs_tol=1e-15), "PARMA day-15 flux differs")
    return parsed


def validate_response(response: Path, role: str) -> dict[str, Any]:
    summary = load_json(response / "summary.json")
    cutflow = load_cutflow(response / "mono_line_cutflow.csv")
    bins = load_bin80(response / "mono_line_final_by_source_bin80.csv")
    require(summary.get("status") == "COMPLETE__MONO_LINE_COMMON_RESPONSE", "response status is not complete")
    require(summary.get("model") == "b", "response did not use model-B logic")
    require(int(summary["incident_photons"]) == EXPECTED_INCIDENT_PHOTONS, "new run is not matched to open SH3 incident statistics")
    exposure = float(summary["physical_exposure_s"])
    weight = float(summary["event_weight_cps"])
    require(exposure > 0.0, f"{role} response has non-positive exposure")
    require(math.isclose(weight, 1.0 / exposure, rel_tol=1e-13, abs_tol=1e-16), f"{role} response weight is not 1/sum(T)")
    if role == "open_sh3":
        require(math.isclose(exposure, EXPECTED_EXPOSURE_S, rel_tol=1e-12, abs_tol=1e-7), "open SH3 exposure authority differs")
        require(math.isclose(weight, EXPECTED_WEIGHT_CPS, rel_tol=1e-12, abs_tol=1e-16), "open SH3 weight authority differs")
    else:
        relative_difference = abs(exposure / EXPECTED_EXPOSURE_S - 1.0)
        require(relative_difference <= MAX_EXPOSURE_RELATIVE_DIFFERENCE, "new exposure differs from the matched PARMA realization sanity band")

    for key, row in cutflow.items():
        count = row["selected_events"]
        require(math.isclose(row["event_weight_cps"], weight, rel_tol=1e-13), f"cutflow weight differs: {key}")
        require(math.isclose(row["weighted_rate_cps"], count * weight, rel_tol=1e-12, abs_tol=1e-16), f"cutflow rate mismatch: {key}")
        require(math.isclose(row["weighted_mc_sigma_cps"], math.sqrt(count) * weight, rel_tol=1e-12, abs_tol=1e-16), f"cutflow sigma mismatch: {key}")
        require(math.isclose(row["effective_selected_events"], float(count), rel_tol=0.0, abs_tol=1e-9), f"cutflow ESS mismatch: {key}")

    final_count = cutflow[FINAL_KEY]["selected_events"]
    require(sum(row["selected_events"] for row in bins.values()) == final_count, "80-bin sum does not equal final selection")
    for index, row in bins.items():
        require(math.isclose(row["weighted_rate_cps"], row["selected_events"] * weight, rel_tol=1e-12, abs_tol=1e-16), f"bin-rate mismatch: {index}")
    require(int(summary["w2_final_selected_events"]) == final_count, "summary/cutflow final-count mismatch")
    require(math.isclose(float(summary["w2_final_rate_cps"]), final_count * weight, rel_tol=1e-12, abs_tol=1e-16), "summary final-rate mismatch")
    require(math.isclose(float(summary["w2_final_mc_sigma_cps"]), math.sqrt(final_count) * weight, rel_tol=1e-12, abs_tol=1e-16), "summary final-sigma mismatch")
    require(int(summary["w2_final_effective_sample_size"]) == final_count, "summary final-ESS mismatch")
    return {"summary": summary, "cutflow": cutflow, "bins": bins}


def compare_values(new: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    new_rate = float(new["weighted_rate_cps"])
    old_rate = float(old["weighted_rate_cps"])
    new_sigma = float(new["weighted_mc_sigma_cps"])
    old_sigma = float(old["weighted_mc_sigma_cps"])
    delta = new_rate - old_rate
    delta_sigma = math.hypot(new_sigma, old_sigma)
    result: dict[str, Any] = {
        "new_selected_events": int(new["selected_events"]),
        "old_selected_events": int(old["selected_events"]),
        "new_effective_sample_size": float(new["effective_selected_events"]),
        "old_effective_sample_size": float(old["effective_selected_events"]),
        "new_rate_cps": new_rate,
        "old_rate_cps": old_rate,
        "new_mc_sigma_cps": new_sigma,
        "old_mc_sigma_cps": old_sigma,
        "new_minus_old_cps": delta,
        "independent_difference_sigma_cps": delta_sigma,
        "difference_z": delta / delta_sigma if delta_sigma > 0.0 else None,
    }
    if new_rate > 0.0 and old_rate > 0.0:
        ratio = new_rate / old_rate
        rel_ratio_sigma = math.hypot(new_sigma / new_rate, old_sigma / old_rate)
        result.update({
            "new_over_old_ratio": ratio,
            "independent_ratio_sigma": ratio * rel_ratio_sigma,
            "independent_ratio_relative_sigma": rel_ratio_sigma,
            "fractional_change": ratio - 1.0,
            "percent_change": 100.0 * (ratio - 1.0),
            "suppression_fraction": 1.0 - ratio,
        })
    else:
        result.update({
            "new_over_old_ratio": None,
            "independent_ratio_sigma": None,
            "independent_ratio_relative_sigma": None,
            "fractional_change": None,
            "percent_change": None,
            "suppression_fraction": None,
        })
    return result


def compare_cutflow(new_rows: dict[tuple[str, str], dict[str, Any]], old_rows: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        for stage in STAGES:
            key = (window, stage)
            rows.append({"window_id": window, "stage": stage, **compare_values(new_rows[key], old_rows[key])})
    require(len(rows) == 10, "internal cutflow comparison length error")
    return rows


def bin_as_cutrow(row: dict[str, Any], weight: float) -> dict[str, Any]:
    count = int(row["selected_events"])
    return {
        "selected_events": count,
        "effective_selected_events": float(count),
        "weighted_rate_cps": float(row["weighted_rate_cps"]),
        "weighted_mc_sigma_cps": math.sqrt(count) * weight,
    }


def compare_bins(
    new_bins: dict[int, dict[str, Any]],
    old_bins: dict[int, dict[str, Any]],
    parma_bins: dict[int, dict[str, Any]],
    new_weight: float,
    old_weight: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(80):
        meta = parma_bins[index]
        comparison = compare_values(
            bin_as_cutrow(new_bins[index], new_weight),
            bin_as_cutrow(old_bins[index], old_weight),
        )
        rows.append({
            "source_bin80": index,
            "source_id": meta["source_id"],
            "direction_label": meta["direction_label"],
            "parma_mu_low": meta["parma_mu_low"],
            "parma_mu_high": meta["parma_mu_high"],
            "line_fraction": meta["line_fraction"],
            "line_flux_ph_cm2_s": meta["line_flux_ph_cm2_s"],
            **comparison,
        })
    return rows


def aggregate_direction(
    label: str,
    indices: Iterable[int],
    new_bins: dict[int, dict[str, Any]],
    old_bins: dict[int, dict[str, Any]],
    parma_bins: dict[int, dict[str, Any]],
    new_weight: float,
    old_weight: float,
) -> dict[str, Any]:
    ids = list(indices)
    new_count = sum(new_bins[index]["selected_events"] for index in ids)
    old_count = sum(old_bins[index]["selected_events"] for index in ids)
    new_row = bin_as_cutrow({"selected_events": new_count, "weighted_rate_cps": new_count * new_weight}, new_weight)
    old_row = bin_as_cutrow({"selected_events": old_count, "weighted_rate_cps": old_count * old_weight}, old_weight)
    return {
        "direction_label": label,
        "source_bin80_first": ids[0],
        "source_bin80_last": ids[-1],
        "parma_line_flux_ph_cm2_s": math.fsum(parma_bins[index]["line_flux_ph_cm2_s"] for index in ids),
        **compare_values(new_row, old_row),
    }


def required_ess(relative_target: float) -> int:
    return int(math.ceil((1.0 / (relative_target * relative_target)) - 1e-12))


def projected_additional_incident(current_incident: int, current_ess: float, target_ess: int) -> int | None:
    if current_ess <= 0.0:
        return None
    required_total_incident = math.ceil(current_incident * target_ess / current_ess)
    return max(0, required_total_incident - current_incident)


def statistics_decision(
    final_comparison: dict[str, Any],
    current_incident: int,
    line_target: float,
    ratio_target: float,
) -> dict[str, Any]:
    new_ess = float(final_comparison["new_effective_sample_size"])
    old_ess = float(final_comparison["old_effective_sample_size"])
    line_required = required_ess(line_target)
    line_pass = new_ess >= line_required
    line_additional = projected_additional_incident(current_incident, new_ess, line_required)

    ratio_floor = 1.0 / math.sqrt(old_ess) if old_ess > 0.0 else math.inf
    denominator = ratio_target * ratio_target - (1.0 / old_ess if old_ess > 0.0 else math.inf)
    if denominator <= 0.0:
        ratio_required: int | None = None
        ratio_pass = False
        ratio_additional = None
        ratio_status = "IMPOSSIBLE_WITH_NEW_GRID_TOPUP_ONLY"
    else:
        ratio_required = int(math.ceil((1.0 / denominator) - 1e-12))
        ratio_pass = new_ess >= ratio_required
        ratio_additional = projected_additional_incident(current_incident, new_ess, ratio_required)
        ratio_status = "PASS" if ratio_pass else "TOPUP_REQUIRED"

    projected_candidates = [value for value in (line_additional, ratio_additional) if value is not None]
    projected_max = max(projected_candidates) if projected_candidates else None
    overall_pass = line_pass and ratio_pass
    return {
        "status": "PASS__INCREMENTAL_STATISTICS_ASSESSED",
        "decision": "NO_TOPUP" if overall_pass else "TOPUP_RECOMMENDED_FOR_REQUESTED_PRECISION",
        "action_policy": "do not auto-run; preserve the matched-statistics result and, if authorized, add a separate resumable top-up campaign",
        "common_weight_ess_contract": "all day-15 selected events carry one common weight, so Kish ESS equals selected-event count",
        "line_rate_precision": {
            "target_relative_mc_sigma": line_target,
            "observed_effective_sample_size": new_ess,
            "observed_relative_mc_sigma": (1.0 / math.sqrt(new_ess)) if new_ess > 0.0 else None,
            "required_effective_sample_size": line_required,
            "decision": "PASS" if line_pass else "TOPUP_REQUIRED",
            "projected_additional_incident_photons_point_estimate": line_additional,
        },
        "new_over_open_ratio_precision": {
            "target_relative_mc_sigma": ratio_target,
            "observed_new_effective_sample_size": new_ess,
            "fixed_open_sh3_effective_sample_size": old_ess,
            "fixed_open_sh3_relative_precision_floor": ratio_floor,
            "observed_relative_mc_sigma": final_comparison["independent_ratio_relative_sigma"],
            "required_new_effective_sample_size": ratio_required,
            "decision": ratio_status,
            "projected_additional_incident_photons_point_estimate": ratio_additional,
        },
        "projected_additional_incident_photons_to_meet_both_point_estimate": projected_max,
        "projection_caveat": "projection assumes unchanged selection efficiency and is a planning estimate, not a replacement for the completed-run uncertainty",
    }


def comparator_seed_set() -> set[int]:
    receipt = load_json(OPEN_SH3 / "MERGE_RECEIPT.json")
    seeds = [*receipt["inputs"]["old_response_seeds"], *receipt["inputs"]["topup"]["seeds"]]
    require(len(seeds) == 70 and len(set(seeds)) == 70, "open SH3 seed authority differs")
    return {int(seed) for seed in seeds}


def rewrite_stage_paths(response: Path, stage: Path, output: Path) -> None:
    old = str(stage.resolve())
    new = str(output.resolve())
    for path in response.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")


def run_package67_analysis(
    roots: list[Path], response: Path, expected_geometry_setup: Path | None
) -> dict[str, Any]:
    require(bool(roots), "at least one --line-root is required")
    for root in roots:
        require(not under_mnt_data(root), f"/mnt/data input is forbidden for this closure: {root}")
    analyzer = load_module("wgrid_frozen_package67_analyzer", ANALYZER)
    jobs, exposure_s, _ = analyzer.validate_and_prepare("b", roots)
    new_seeds = {int(job["seed"]) for job in jobs}
    require(len(new_seeds) == len(jobs), "new campaign seed reuse")
    overlap = sorted(new_seeds & comparator_seed_set())
    require(not overlap, f"new/open SH3 seeds overlap: {overlap[:10]}")
    require(sum(int(job["events"]) for job in jobs) == EXPECTED_INCIDENT_PHOTONS, "new incident count does not match open SH3")
    require(abs(exposure_s / EXPECTED_EXPOSURE_S - 1.0) <= MAX_EXPOSURE_RELATIVE_DIFFERENCE, "new exposure differs from the matched PARMA realization sanity band")
    if expected_geometry_setup is not None:
        expected = expected_geometry_setup.resolve()
        observed = {Path(job["expected_geometry"]).resolve() for job in jobs}
        require(observed == {expected}, f"new geometry setup differs: observed={sorted(map(str, observed))}, expected={expected}")
    analyzer.run("b", roots, response)
    return {
        "status": "PASS__INDEPENDENT_MODEL_B_ANALYSIS",
        "new_job_count": len(jobs),
        "new_seed_count": len(new_seeds),
        "open_sh3_seed_count": 70,
        "seed_overlap_count": 0,
        "independent_error_propagation_authorized": True,
    }


def copy_static_response(source: Path, response: Path) -> dict[str, Any]:
    require(not under_mnt_data(source), f"/mnt/data input is forbidden for this closure: {source}")
    response.mkdir(parents=True)
    for name in ("summary.json", "mono_line_cutflow.csv", "mono_line_final_by_source_bin80.csv"):
        path = source / name
        require(path.is_file(), f"static response input is missing: {path}")
        shutil.copy2(path, response / name)
    return {
        "status": "STATIC_RESPONSE_INPUT__SEED_INDEPENDENCE_NOT_RECHECKED",
        "source": str(source.resolve()),
        "independent_error_propagation_authorized": False,
    }


def small_artifact_manifest(stage: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in stage.rglob("*") if item.is_file()):
        if path.name == "ARTIFACT_MANIFEST.json":
            continue
        size = path.stat().st_size
        row: dict[str, Any] = {"path": str(path.relative_to(stage)), "bytes": size}
        if path.suffix != ".npz" and size <= 64 * 1024 * 1024:
            row["sha256"] = sha256(path)
        else:
            row["sha256"] = None
            row["hash_policy"] = "not hashed: large/binary analysis cache"
        rows.append(row)
    return {"status": "PASS__SMALL_ARTIFACT_MANIFEST", "files": rows}


def build_outputs(
    stage: Path,
    output: Path,
    line_roots: list[Path] | None,
    response_input: Path | None,
    expected_geometry_setup: Path | None,
    line_target: float,
    ratio_target: float,
) -> dict[str, Any]:
    authority = verify_frozen_authorities()
    frozen = freeze_inputs(stage)
    response = stage / "response"
    if line_roots is not None:
        run_audit = run_package67_analysis(line_roots, response, expected_geometry_setup)
        rewrite_stage_paths(response, stage, output)
    else:
        require(response_input is not None, "internal input-mode error")
        run_audit = copy_static_response(response_input, response)

    new = validate_response(response, "wgrid")
    old = validate_response(stage / "frozen_open_sh3_comparator", "open_sh3")
    require(int(old["summary"]["incident_photons"]) == EXPECTED_INCIDENT_PHOTONS, "frozen comparator incident count differs")
    require(int(old["summary"]["w2_final_selected_events"]) == 186, "frozen comparator final count differs")
    parma = load_parma_bins(stage / "frozen_parma_authority" / PARMA_BINS.name)

    cutflow_rows = compare_cutflow(new["cutflow"], old["cutflow"])
    write_csv(stage / "comparison_cutflow_10rows.csv", cutflow_rows)
    bin_rows = compare_bins(
        new["bins"], old["bins"], parma,
        float(new["summary"]["event_weight_cps"]),
        float(old["summary"]["event_weight_cps"]),
    )
    write_csv(stage / "comparison_final_by_source_bin80.csv", bin_rows)
    direction_rows = [
        aggregate_direction(
            "down", range(0, 40), new["bins"], old["bins"], parma,
            float(new["summary"]["event_weight_cps"]), float(old["summary"]["event_weight_cps"]),
        ),
        aggregate_direction(
            "up", range(40, 80), new["bins"], old["bins"], parma,
            float(new["summary"]["event_weight_cps"]), float(old["summary"]["event_weight_cps"]),
        ),
    ]
    write_csv(stage / "comparison_up_down.csv", direction_rows)

    by_key = {(row["window_id"], row["stage"]): row for row in cutflow_rows}
    final = by_key[FINAL_KEY]
    decision = statistics_decision(final, EXPECTED_INCIDENT_PHOTONS, line_target, ratio_target)
    write_json(stage / "incremental_statistics_decision.json", decision)

    comparison = {
        "status": "PASS__MATCHED_SH3_WGRID_MONO511_COMPARISON",
        "created_at": utc_now(),
        "physics_scope": "PARMA dedicated atmospheric monoenergetic line only",
        "line_energy_keV": 510.99895,
        "parma_day15_full_space_flux_ph_cm2_s": EXPECTED_PARMA_FLUX,
        "angular_distribution": "80 equal-mu components from the same day-15 PARMA atmospheric state",
        "response_contract": "package-67 model-B response and selection, unchanged",
        "matched_statistics": {
            "incident_photons_each": EXPECTED_INCIDENT_PHOTONS,
            "source_normalization": "same PARMA flux and 60-cm source surface",
            "open_sh3_physical_exposure_s": float(old["summary"]["physical_exposure_s"]),
            "wgrid_physical_exposure_s": float(new["summary"]["physical_exposure_s"]),
            "open_sh3_event_weight_cps": float(old["summary"]["event_weight_cps"]),
            "wgrid_event_weight_cps": float(new["summary"]["event_weight_cps"]),
            "time_note": "independent source realizations use their own 1/sum(T); exact equality of stochastic Cosima observation times is neither assumed nor imposed",
        },
        "uncertainty_contract": "new and open-frame transports use disjoint seeds; rate-difference variances add; ratio uncertainty uses first-order independent propagation",
        "key_comparisons": {
            "w2_pre_veto": by_key[PRE_VETO_KEY],
            "w2_final": final,
        },
        "direction_aggregates": {row["direction_label"]: row for row in direction_rows},
        "incremental_statistics": decision,
        "files": {
            "cutflow_10rows": "comparison_cutflow_10rows.csv",
            "source_bin80": "comparison_final_by_source_bin80.csv",
            "up_down": "comparison_up_down.csv",
            "statistics_decision": "incremental_statistics_decision.json",
            "report_input": "report_input.json",
        },
    }
    write_json(stage / "comparison_summary.json", comparison)
    report_input = {
        "schema_version": 1,
        "metadata": {
            "data_status": "actual",
            "line_energy_keV": 510.99895,
            "parma_day15_full_space_flux_ph_cm2_s": EXPECTED_PARMA_FLUX,
            "angular_components_equal_mu": 80,
            "common_parma_source": True,
            "common_response_selection_time": True,
            "independent_mc_samples": True,
            "window_id": "w2_510p58_511p42",
            "source_fragment_sha256": PARMA_FRAGMENT_SHA256,
            "source_contract_sha256": SOURCE_CONTRACT_SHA256,
            "line_transport_contract_sha256": LINE_TRANSPORT_CONTRACT_SHA256,
            "response_selection_contract": "package-67 model-B response and selection, unchanged",
        },
        "open_frame": {
            "label": "SH3 开放框",
            "geometry_id": old["summary"]["geometry_setup"],
            "incident_photons": int(old["summary"]["incident_photons"]),
            "physical_exposure_s": float(old["summary"]["physical_exposure_s"]),
            "selected_events": int(old["summary"]["w2_final_selected_events"]),
            "effective_selected_events": int(old["summary"]["w2_final_effective_sample_size"]),
            "rate_cps": float(old["summary"]["w2_final_rate_cps"]),
            "sigma_cps": float(old["summary"]["w2_final_mc_sigma_cps"]),
        },
        "w_grid": {
            "label": "SH3 + W-grid",
            "geometry_id": new["summary"]["geometry_setup"],
            "incident_photons": int(new["summary"]["incident_photons"]),
            "physical_exposure_s": float(new["summary"]["physical_exposure_s"]),
            "selected_events": int(new["summary"]["w2_final_selected_events"]),
            "effective_selected_events": int(new["summary"]["w2_final_effective_sample_size"]),
            "rate_cps": float(new["summary"]["w2_final_rate_cps"]),
            "sigma_cps": float(new["summary"]["w2_final_mc_sigma_cps"]),
        },
    }
    write_json(stage / "report_input.json", report_input)
    provenance = {
        "status": "PASS__ANALYSIS_PROVENANCE_CLOSED",
        "created_at": utc_now(),
        "authority_validation": authority,
        "frozen_inputs": frozen,
        "analysis_run": run_audit,
        "output_destination": str(output.resolve()),
        "sim_hashes_computed": 0,
    }
    write_json(stage / "PROVENANCE.json", provenance)
    write_json(stage / "PROMOTION_RECEIPT.json", {
        "status": "READY__SIBLING_ATOMIC_DIRECTORY_RENAME",
        "prepared_at": utc_now(),
        "staging_basename": stage.name,
        "destination": str(output.resolve()),
        "non_overwrite": True,
    })
    write_json(stage / "ARTIFACT_MANIFEST.json", small_artifact_manifest(stage))
    return comparison


def execute(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    require(not under_mnt_data(output), f"/mnt/data output is forbidden for this closure: {output}")
    require(not output.exists(), f"non-overwrite destination already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{uuid.uuid4().hex}"
    stage = output.parent / f".{output.name}.staging-{token}"
    stage.mkdir(exist_ok=False)
    try:
        comparison = build_outputs(
            stage=stage,
            output=output,
            line_roots=[path.resolve() for path in args.line_root] if args.line_root else None,
            response_input=args.response_input.resolve() if args.response_input else None,
            expected_geometry_setup=args.expected_geometry_setup.resolve() if args.expected_geometry_setup else None,
            line_target=float(args.target_line_relative_mc_sigma),
            ratio_target=float(args.target_ratio_relative_mc_sigma),
        )
        require(not output.exists(), f"destination appeared during analysis: {output}")
        os.rename(stage, output)
        return {"status": "PASS__ATOMICALLY_PROMOTED", "output": str(output), "comparison": comparison}
    except Exception as exc:
        failure = stage.parent / f".{output.name}.failed-{token}"
        if stage.exists():
            try:
                write_json(stage / "FAILURE_RECEIPT.json", {
                    "status": "FAIL__ANALYSIS_NOT_PROMOTED",
                    "failed_at": utc_now(),
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                })
                os.rename(stage, failure)
            except Exception:
                pass
        raise RuntimeError(f"analysis failed; unpromoted staging preserved at {failure}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--line-root", type=Path, action="append", help="completed local mono511 transport root; may be repeated")
    source.add_argument("--response-input", type=Path, help="static package-67-format response (comparison/self-test only)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-geometry-setup", type=Path, help="exact W-grid 60-cm setup path; checked before scanning")
    parser.add_argument("--target-line-relative-mc-sigma", type=float, default=OPEN_FINAL_RELATIVE_MC_SIGMA)
    parser.add_argument("--target-ratio-relative-mc-sigma", type=float, default=0.10)
    args = parser.parse_args()
    require(0.0 < args.target_line_relative_mc_sigma < 1.0, "line precision target must be in (0,1)")
    require(0.0 < args.target_ratio_relative_mc_sigma < 1.0, "ratio precision target must be in (0,1)")
    result = execute(args)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
