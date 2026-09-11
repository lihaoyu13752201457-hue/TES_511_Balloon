#!/usr/bin/env python3
"""Apply the current A/B detector response to a monoenergetic PARMA line run.

The large SIM files are streamed, never hashed or loaded wholesale.  Existing
reviewed response functions are imported from the current model-specific
catalog builders.  Per-event primary angular-bin identity is recovered from
the printed IA INIT direction for later trajectory reweighting.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]

MODEL_A_ROOT = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_parma511_sidecar_3m_v1")
MODEL_B95_ROOT = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_eqstats_v1/parma511")
MODEL_B60_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/"
    "sh3_optv3_60cm_full_adaptive_2p5h_v1"
)

A_CONFIG = ROOT / "engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817/analysis_inputs.json"
A_BUILDER = ROOT / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/code/build_event_catalog.py"
B_CONFIG = ROOT / "DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json"
B_BUILDER = ROOT / "DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py"

STAGES = {
    "pre_veto": 1 << 0,
    "plastic_positron_veto": 1 << 1,
    "bgo_active_scintillator_veto": 1 << 2,
    "combined_active_veto": 1 << 3,
    "compton_trajectory_veto": 1 << 4,
}
WINDOW_FIELDS = {
    "broad_480_550": "broad_flags",
    "w2_510p58_511p42": "w2_flags",
}
EVENT_FIELDS = (
    "event_id", "plastic_keV", "bgo_keV", "measured_total_keV",
    "broad_flags", "w2_flags", "hit_start", "hit_count",
)
HIT_FIELDS = (
    "hit_code", "hit_layer", "hit_energy_keV", "hit_x_cm", "hit_y_cm", "hit_z_cm",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_bin80_from_dir_z(dir_z: float) -> int:
    # FarFieldAreaSource theta is the source-side sky direction; IA INIT points inward.
    return max(0, min(79, int(math.floor((1.0 + dir_z) * 40.0))))


def validate_and_prepare(
    model: str, line_roots: list[Path]
) -> tuple[list[dict[str, Any]], float, Any]:
    bundles: list[Path] = []
    for line_root in line_roots:
        if (line_root / "run/receipts").is_dir():
            discovered = [line_root]
        else:
            discovered = sorted(
                path
                for path in (line_root / "rounds").glob("round*/parma511")
                if (path / "run/receipts").is_dir()
            )
        if not discovered:
            raise RuntimeError(f"no line bundles found: {line_root}")
        bundles.extend(discovered)
    resolved_bundles = [bundle.resolve() for bundle in bundles]
    if len(set(resolved_bundles)) != len(resolved_bundles):
        raise RuntimeError("duplicate mono-line bundle supplied through multiple roots")
    receipt_rows: list[tuple[str, dict[str, Any]]] = []
    for bundle in bundles:
        controller = load_json(bundle / "run/controller_state.json")
        rows = [load_json(path) for path in sorted((bundle / "run/receipts").glob("*.json"))]
        if controller.get("status") != "COMPLETE" or controller.get("error") is not None:
            raise RuntimeError(f"line controller is not complete: {bundle}")
        if int(controller.get("completed_count", -1)) != len(rows) or not rows:
            raise RuntimeError(f"line controller/receipt count mismatch: {bundle}")
        receipt_rows.extend((bundle.parent.name if bundle.parent.name.startswith("round") else bundle.name, row)
                            for row in rows)
    receipts = [row for _, row in receipt_rows]
    if any(row.get("status") != "PASS" for row in receipts):
        raise RuntimeError("non-PASS line receipt")
    if sum(int(row["events"]) for row in receipts) <= 0:
        raise RuntimeError("empty line transport")

    if model == "a":
        cfg = load_json(A_CONFIG)
        builder = load_module("m05_line_a_builder", A_BUILDER)
        expected = Path(cfg["geometry_setup"]).resolve()
        plastic = list(cfg["active_veto"]["plastic_positron_veto_volumes"])
        bgo = list(cfg["active_veto"]["bgo_active_scintillator_volumes"])
    else:
        cfg = load_json(B_CONFIG)
        builder = load_module("m05_line_b_builder", B_BUILDER)
        expected = Path(receipts[0]["setup_path"]).resolve()
        plastic = list(cfg["active_veto"]["plastic_positron_veto_volumes"])
        bgo = list(cfg["active_veto"]["bgo_active_scintillator_volumes"])

    exposure_s = math.fsum(float(row["log"]["observation_time_s"]) for row in receipts)
    if exposure_s <= 0.0:
        raise RuntimeError("non-positive line exposure")
    weight = 1.0 / exposure_s
    jobs: list[dict[str, Any]] = []
    seen_seeds: set[int] = set()
    for index, (batch_id, row) in enumerate(receipt_rows):
        source = Path(row["source_path"])
        text = source.read_text(encoding="utf-8")
        if text.count(".Spectrum Mono 510.99895") != 80 or text.count(".Source ") != 80:
            raise RuntimeError(f"line source definition differs: {source}")
        setup = Path(row["setup_path"]).resolve()
        header_setup = Path(row["sim_header"]["geometry"]).resolve()
        if setup != expected or header_setup != expected:
            raise RuntimeError(f"line geometry mismatch: {row['job_id']}")
        seed = int(row["seed"])
        if seed in seen_seeds or int(row["sim_header"]["seed"]) != seed:
            raise RuntimeError(f"line seed mismatch/reuse: {row['job_id']}")
        seen_seeds.add(seed)
        sim = Path(row["sim_path"])
        if not sim.is_file() or sim.stat().st_size != int(row["sim_bytes"]):
            raise RuntimeError(f"line SIM missing/size mismatch: {sim}")
        jobs.append({
            "stream": "prompt",
            "family": "atm511",
            "mode": "atm511",
            "batch_id": batch_id,
            "job_id": row["job_id"],
            "scan_index": index,
            "seed": seed,
            "events": int(row["events"]),
            "sim_path": str(sim),
            "sim_bytes": int(row["sim_bytes"]),
            "source_path": str(source),
            "expected_geometry": str(expected),
            "weight_cps": weight,
            "plastic_volumes": plastic,
            "bgo_volumes": bgo,
            "positions_path": None,
        })
    return jobs, exposure_s, builder


def extract_primary_bins(sim_path: Path, wanted: set[int]) -> dict[int, int]:
    found: dict[int, int] = {}
    current: int | None = None
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                fields = line.split()
                current = int(fields[1]) if len(fields) >= 2 else None
                continue
            if current not in wanted or not line.startswith("IA INIT"):
                continue
            fields = [value.strip() for value in line.split(";")]
            if len(fields) <= 18:
                raise RuntimeError(f"malformed IA INIT in {sim_path}")
            if current in found:
                raise RuntimeError(f"multiple IA INIT records for event {current} in {sim_path}")
            found[current] = source_bin80_from_dir_z(float(fields[18]))
    if set(found) != wanted:
        missing = sorted(wanted - set(found))[:10]
        raise RuntimeError(f"primary-bin recovery incomplete for {sim_path}: {missing}")
    return found


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(model: str, line_roots: list[Path], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "job_catalogs"
    cache.mkdir(parents=True, exist_ok=True)
    jobs, exposure_s, builder = validate_and_prepare(model, line_roots)
    threshold = 50.0
    if model == "a":
        scan = lambda job: builder.scan_job(job, str(cache), threshold)
    else:
        cfg = load_json(B_CONFIG)
        sde = cfg["side_entry_disk"]
        disk = builder.side_entry_disk(
            tuple(float(x) for x in sde["local_center_cm"]),
            float(sde["radius_cm"]), float(sde["rotation_y_deg"]),
        )
        reject = str(sde.get("reject_policy", "keep"))
        scan = lambda job: builder.scan_job(job, str(cache), threshold, disk, reject)

    metas: list[dict[str, Any]] = []
    for ordinal, job in enumerate(jobs, 1):
        meta = scan(job)
        metas.append(meta)
        print(json.dumps({
            "model": model, "job": job["job_id"], "complete": ordinal,
            "total": len(jobs), "detector_positive": meta["detector_positive_events"],
        }), flush=True)

    all_events: dict[str, list[np.ndarray]] = {field: [] for field in EVENT_FIELDS}
    all_hits: dict[str, list[np.ndarray]] = {field: [] for field in HIT_FIELDS}
    all_bins: list[np.ndarray] = []
    all_jobs: list[np.ndarray] = []
    hit_offset = 0
    cut_counts = {(window, stage): 0 for window in WINDOW_FIELDS for stage in STAGES}
    bin_final_counts = np.zeros(80, dtype=np.int64)
    detector_positive = 0
    for job, meta in zip(jobs, metas):
        with np.load(meta["catalog_path"], allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files}
        ids = arrays["event_id"].astype(np.int64)
        recovered = extract_primary_bins(Path(job["sim_path"]), set(int(value) for value in ids))
        bins = np.asarray([recovered[int(value)] for value in ids], dtype=np.uint8)
        starts = arrays["hit_start"].astype(np.int64) + hit_offset
        hit_offset += len(arrays["hit_code"])
        for field in EVENT_FIELDS:
            all_events[field].append(starts if field == "hit_start" else arrays[field])
        for field in HIT_FIELDS:
            all_hits[field].append(arrays[field])
        all_bins.append(bins)
        all_jobs.append(np.full(len(ids), int(job["scan_index"]), dtype=np.uint16))
        detector_positive += len(ids)
        for window, field in WINDOW_FIELDS.items():
            flags = arrays[field]
            for stage, bit in STAGES.items():
                mask = (flags & bit) != 0
                cut_counts[(window, stage)] += int(np.count_nonzero(mask))
                if window == "w2_510p58_511p42" and stage == "compton_trajectory_veto":
                    bin_final_counts += np.bincount(bins[mask], minlength=80)

    merged = {
        field: np.concatenate(chunks) if chunks else np.empty(0)
        for field, chunks in {**all_events, **all_hits}.items()
    }
    merged["source_bin80"] = np.concatenate(all_bins) if all_bins else np.empty(0, dtype=np.uint8)
    merged["event_job_index"] = np.concatenate(all_jobs) if all_jobs else np.empty(0, dtype=np.uint16)
    merged["base_event_weight_cps"] = np.full(detector_positive, 1.0 / exposure_s, dtype=np.float64)
    catalog_path = output / "mono_line_event_catalog.npz"
    tmp = catalog_path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **merged)
    os.replace(tmp, catalog_path)

    weight = 1.0 / exposure_s
    cutflow = []
    for window in WINDOW_FIELDS:
        for stage in STAGES:
            count = cut_counts[(window, stage)]
            cutflow.append({
                "model": model,
                "window_id": window,
                "stage": stage,
                "selected_events": count,
                "event_weight_cps": weight,
                "weighted_rate_cps": count * weight,
                "weighted_mc_sigma_cps": math.sqrt(count) * weight,
                "effective_selected_events": count,
            })
    write_csv(output / "mono_line_cutflow.csv", cutflow)
    write_csv(output / "mono_line_final_by_source_bin80.csv", [
        {"source_bin80": index, "selected_events": int(value),
         "weighted_rate_cps": float(value) * weight}
        for index, value in enumerate(bin_final_counts)
    ])
    final_count = cut_counts[("w2_510p58_511p42", "compton_trajectory_veto")]
    summary = {
        "status": "COMPLETE__MONO_LINE_COMMON_RESPONSE",
        "model": model,
        "line_roots": [str(path) for path in line_roots],
        "geometry_setup": jobs[0]["expected_geometry"],
        "incident_photons": sum(int(job["events"]) for job in jobs),
        "jobs": len(jobs),
        "physical_exposure_s": exposure_s,
        "event_weight_cps": weight,
        "detector_positive_events": detector_positive,
        "detector_positive_rate_cps": detector_positive * weight,
        "w2_final_selected_events": final_count,
        "w2_final_rate_cps": final_count * weight,
        "w2_final_mc_sigma_cps": math.sqrt(final_count) * weight,
        "w2_final_relative_mc_sigma": (1.0 / math.sqrt(final_count)) if final_count else None,
        "w2_final_effective_sample_size": final_count,
        "catalog": str(catalog_path),
        "normalization": "each selected event carries 1/sum(Cosima observation time over all independent shards)",
        "sim_hashes_computed": 0,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("a", "b95", "b60"), required=True)
    parser.add_argument("--line-root", type=Path)
    parser.add_argument(
        "--extra-line-root", type=Path, action="append", default=[],
        help="additional completed mono-line bundle/root to merge with --line-root",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    defaults = {"a": MODEL_A_ROOT, "b95": MODEL_B95_ROOT, "b60": MODEL_B60_ROOT}
    line_root = (args.line_root or defaults[args.model]).resolve()
    line_roots = [line_root, *(path.resolve() for path in args.extra_line_root)]
    output = (args.output or (PACKAGE / "outputs" / f"01_line_response_{args.model}")).resolve()
    model_logic = "a" if args.model == "a" else "b"
    run(model_logic, line_roots, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
