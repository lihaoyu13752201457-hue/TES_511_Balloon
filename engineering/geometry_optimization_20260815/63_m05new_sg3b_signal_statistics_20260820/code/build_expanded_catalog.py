#!/usr/bin/env python3
"""Scan supplemental gamma SIMs and merge them into the SG3B compact catalog."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
BASE = ROOT / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/outputs/01_event_catalog"
CATALOG_CODE = ROOT / "engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/code/build_event_catalog.py"
RECEIPTS = PACKAGE / "outputs/02_gamma_transport/receipts"
OUT = PACKAGE / "outputs/03_expanded_catalog"
CACHE = OUT / "job_catalogs"
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
PLASTIC = [
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
]
BGO = [
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
]
STAGE_BITS = {
    "pre_veto": 1 << 0,
    "plastic_positron_veto": 1 << 1,
    "bgo_active_scintillator_veto": 1 << 2,
    "combined_active_veto": 1 << 3,
    "compton_trajectory_veto": 1 << 4,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog_module() -> Any:
    name = "m05new_sg3b_base_catalog_code"
    spec = importlib.util.spec_from_file_location(name, CATALOG_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {CATALOG_CODE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def activation_tt(path: Path) -> float:
    match = re.search(r"(?m)^TT\s+([-+\deE.]+)\s*$", path.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"missing TT record: {path}")
    value = float(match.group(1))
    if value <= 0:
        raise RuntimeError(f"invalid TT record: {path}")
    return value


def receipt_jobs(limit: int | None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(RECEIPTS.glob("m05new_sg3b_gamma_shard*.json")):
        receipt = load_json(path)
        if receipt.get("status") != "PASS":
            continue
        index = int(receipt["index"])
        if limit is not None and index > limit:
            continue
        sim = Path(receipt["sim"])
        activation = Path(receipt["activation"])
        if not sim.exists() or sim.stat().st_size != int(receipt["sim_bytes"]):
            raise RuntimeError(f"receipt/SIM size closure failed: {path}")
        rows.append({
            "stream": "prompt",
            "family": "gamma",
            "mode": "instant",
            "batch_id": "m05new_sg3b_gamma_expansion_20260820",
            "job_id": receipt["job_id"],
            "seed": int(receipt["sim_header_seed"]),
            "source_seed": int(receipt["source_seed"]),
            "events": int(receipt["events_requested"]),
            "sim_path": str(sim),
            "sim_bytes": int(receipt["sim_bytes"]),
            "source_path": receipt["source"],
            "activation_path": str(activation),
            "TT_s": activation_tt(activation),
            "expected_geometry": str(GEOMETRY),
            "weight_cps": 1.0,
            "plastic_volumes": PLASTIC,
            "bgo_volumes": BGO,
            "scan_index": 1000 + index,
        })
    if not rows:
        raise RuntimeError("no completed supplemental gamma receipts")
    source_seeds = [int(row["source_seed"]) for row in rows]
    header_seeds = [int(row["seed"]) for row in rows]
    if len(source_seeds) != len(set(source_seeds)) or len(header_seeds) != len(set(header_seeds)):
        raise RuntimeError("supplemental source/header seeds are not unique")
    base_seeds = {
        int(load_json(path)["seed"])
        for path in (BASE / "job_catalogs").glob("*.json")
    }
    reused = sorted(set(header_seeds) & base_seeds)
    if reused:
        raise RuntimeError(f"supplemental SIM-header seed reuses base catalog seed: {reused}")
    return rows


def cached_jobs(limit: int | None) -> list[dict[str, Any]]:
    """Recover verified compact catalogs when the external raw-data mount is offline.

    The first completed merge retained exact activation TT values for 15 shards.
    All supplemental shards use the same source contract and event count, so the
    pooled exposure per primary from those exact records is the normalization for
    later compact catalogs whose raw activation files are temporarily unavailable.
    """
    prior_summary = load_json(OUT / "summary.json")
    exact_rows = prior_summary.get("supplemental_jobs", [])[:15]
    exact_events = math.fsum(float(row["events"]) for row in exact_rows)
    exact_tt = math.fsum(float(row["TT_s"]) for row in exact_rows)
    if len(exact_rows) != 15 or exact_events <= 0 or exact_tt <= 0:
        raise RuntimeError("expected retained exact-TT reference for 15 shards")
    tt_per_primary = exact_tt / exact_events

    rows = []
    for meta_path in sorted(CACHE.glob("job_*_m05new_sg3b_gamma_shard*.json")):
        meta = load_json(meta_path)
        if meta.get("status") != "PASS__COMPACT_JOB_CATALOG":
            continue
        match = re.search(r"shard(\d{4})$", str(meta["job_id"]))
        if not match:
            raise RuntimeError(f"cannot parse cached shard index: {meta_path}")
        index = int(match.group(1))
        if limit is not None and index > limit:
            continue
        receipt_path = RECEIPTS / f"m05new_sg3b_gamma_shard{index:04d}.json"
        receipt = load_json(receipt_path)
        source = Path(receipt["source"])
        catalog = Path(meta["catalog_path"])
        checks = {
            "receipt_pass": receipt.get("status") == "PASS",
            "job_id": receipt.get("job_id") == meta.get("job_id"),
            "events": int(receipt.get("events_requested", -1)) == int(meta.get("events", -2)),
            "seed": int(receipt.get("sim_header_seed", -1)) == int(meta.get("seed", -2)),
            "source_seed": int(receipt.get("source_seed", -1)) == int(meta.get("seed", -2)),
            "sim_path": receipt.get("sim") == meta.get("sim_path"),
            "sim_bytes": int(receipt.get("sim_bytes", -1)) == int(meta.get("sim_bytes", -2)),
            "geometry": receipt.get("geometry") == str(GEOMETRY),
            "header_geometry": receipt.get("header_geometry") == str(GEOMETRY),
            "source_exists": source.exists(),
            "source_hash": source.exists() and sha256_file(source) == receipt.get("source_sha256"),
            "catalog_exists": catalog.exists() and catalog.stat().st_size > 0,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError(f"cache/receipt closure failed for {meta_path}: {failed}")
        rows.append({
            "stream": "prompt",
            "family": "gamma",
            "mode": "instant",
            "batch_id": "m05new_sg3b_gamma_expansion_20260820",
            "job_id": receipt["job_id"],
            "seed": int(receipt["sim_header_seed"]),
            "source_seed": int(receipt["source_seed"]),
            "events": int(receipt["events_requested"]),
            "sim_path": receipt["sim"],
            "sim_bytes": int(receipt["sim_bytes"]),
            "source_path": receipt["source"],
            "activation_path": receipt["activation"],
            "TT_s": int(receipt["events_requested"]) * tt_per_primary,
            "TT_provenance": "pooled exact exposure per primary from retained 15-shard activation-TT reference",
            "expected_geometry": str(GEOMETRY),
            "weight_cps": 1.0,
            "plastic_volumes": PLASTIC,
            "bgo_volumes": BGO,
            "scan_index": 1000 + index,
            "cached_meta": meta,
        })
    if not rows:
        raise RuntimeError("no verified cached supplemental gamma catalogs")
    seeds = [int(row["seed"]) for row in rows]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("cached supplemental seeds are not unique")
    return rows


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_one(job: dict[str, Any]) -> dict[str, Any]:
    module = load_catalog_module()
    return module.scan_job(job, str(CACHE), 50.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--cache-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    jobs = cached_jobs(args.limit) if args.cache_only else receipt_jobs(args.limit)
    metas = []
    if args.cache_only:
        metas = [dict(job["cached_meta"]) for job in jobs]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
            future_job = {pool.submit(scan_one, job): job for job in jobs}
            for future in concurrent.futures.as_completed(future_job):
                meta = future.result()
                metas.append(meta)
                print(json.dumps({
                    "scanned": meta["job_id"],
                    "detector_positive": meta["detector_positive_events"],
                    "elapsed_s": meta["elapsed_s"],
                    "complete": len(metas),
                    "total": len(jobs),
                }), flush=True)
    meta_by_id = {meta["job_id"]: meta for meta in metas}

    with np.load(BASE / "combined_event_catalog.npz", allow_pickle=False) as data:
        base_arrays = {key: data[key] for key in data.files}
    categories = load_json(BASE / "category_registry.json")["categories"]
    gamma_ids = [
        int(row["category_id"]) for row in categories
        if row["stream"] == "prompt" and row["family"] == "gamma"
    ]
    if len(gamma_ids) != 1:
        raise RuntimeError(f"expected one base prompt-gamma category, got {gamma_ids}")
    gamma_id = gamma_ids[0]
    old_gamma_weight = float(categories[gamma_id]["base_event_weight_cps"])
    old_gamma_tt = 1.0 / old_gamma_weight
    new_gamma_tt = math.fsum(float(job["TT_s"]) for job in jobs)
    combined_gamma_tt = old_gamma_tt + new_gamma_tt
    combined_gamma_weight = 1.0 / combined_gamma_tt

    event_fields = (
        "plastic_keV", "bgo_keV", "measured_total_keV", "broad_flags", "w2_flags",
        "hit_start", "hit_count",
    )
    hit_fields = ("hit_code", "hit_layer", "hit_energy_keV", "hit_x_cm", "hit_y_cm", "hit_z_cm")
    old_hits = len(base_arrays["hit_code"])
    new_event_chunks = {field: [] for field in event_fields}
    new_hit_chunks = {field: [] for field in hit_fields}
    hit_offset = old_hits
    for job in sorted(jobs, key=lambda row: int(row["scan_index"])):
        meta = meta_by_id[job["job_id"]]
        with np.load(meta["catalog_path"], allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
        for field in event_fields:
            values = arrays[field]
            if field == "hit_start":
                values = values.astype(np.int64) + hit_offset
            new_event_chunks[field].append(values)
        for field in hit_fields:
            new_hit_chunks[field].append(arrays[field])
        hit_offset += len(arrays["hit_code"])

    out_event = {field: [] for field in event_fields}
    out_category = []
    out_categories = []
    event_offset = 0
    for row in categories:
        cat_id = int(row["category_id"])
        start = int(row["event_start"])
        stop = start + int(row["event_count"])
        count = stop - start
        for field in event_fields:
            out_event[field].append(base_arrays[field][start:stop])
        if cat_id == gamma_id:
            new_count = sum(len(chunk) for chunk in new_event_chunks["plastic_keV"])
            for field in event_fields:
                out_event[field].extend(new_event_chunks[field])
            count += new_count
        new_row = dict(row)
        new_row["event_start"] = event_offset
        new_row["event_count"] = count
        if cat_id == gamma_id:
            new_row["base_event_weight_cps"] = combined_gamma_weight
            new_row["base_detector_positive_rate_cps"] = count * combined_gamma_weight
        out_categories.append(new_row)
        out_category.append(np.full(count, cat_id, dtype=np.uint16))
        event_offset += count

    output = {field: np.concatenate(chunks) for field, chunks in out_event.items()}
    output["event_category"] = np.concatenate(out_category)
    for field in hit_fields:
        chunks = [base_arrays[field], *new_hit_chunks[field]]
        output[field] = np.concatenate(chunks)
    tmp = OUT / "combined_event_catalog.tmp"
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **output)
    os.replace(tmp, OUT / "combined_event_catalog.npz")
    (OUT / "category_registry.json").write_text(
        json.dumps({"schema_version": 1, "categories": out_categories}, indent=2) + "\n",
        encoding="utf-8",
    )

    bit = STAGE_BITS["compton_trajectory_veto"]
    cutflow_rows = []
    totals: dict[tuple[str, str], dict[str, float]] = {}
    for window, flag_field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
        for stage, stage_bit in STAGE_BITS.items():
            total_rate = 0.0
            total_var = 0.0
            total_raw = 0
            for row in out_categories:
                start = int(row["event_start"]); stop = start + int(row["event_count"])
                selected = int(np.count_nonzero(output[flag_field][start:stop] & stage_bit))
                weight = float(row["base_event_weight_cps"])
                rate = selected * weight
                total_rate += rate
                total_var += selected * weight * weight
                total_raw += selected
                cutflow_rows.append({
                    "stream": row["stream"], "family": row["family"],
                    "window_id": window, "stage": stage,
                    "raw_selected": selected, "weighted_rate_cps": rate,
                    "event_weight_cps": weight,
                })
            totals[(window, stage)] = {
                "raw_selected": total_raw,
                "weighted_rate_cps": total_rate,
                "rate_sigma_cps": math.sqrt(total_var),
                "relative_sigma": math.sqrt(total_var) / total_rate if total_rate else math.nan,
                "effective_survivors": total_rate * total_rate / total_var if total_var else math.nan,
            }
    with (OUT / "expanded_direct_cutflow.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cutflow_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(cutflow_rows)

    gamma = out_categories[gamma_id]
    start = int(gamma["event_start"]); stop = start + int(gamma["event_count"])
    gamma_final_raw = int(np.count_nonzero(output["w2_flags"][start:stop] & bit))
    precision_rule_met = totals[("w2_510p58_511p42", "compton_trajectory_veto")]["relative_sigma"] < 0.20
    summary = {
        "schema_version": 1,
        "status": (
            "PASS__STOPPING_RULE_MET" if gamma_final_raw >= 10 else
            "PASS__PRECISION_RULE_MET_WITH_SPARSE_GAMMA" if precision_rule_met else
            "PASS__MORE_GAMMA_REQUIRED"
        ),
        "cache_only_recovery": bool(args.cache_only),
        "supplemental_shards": len(jobs),
        "supplemental_primaries": sum(int(job["events"]) for job in jobs),
        "old_gamma_TT_s": old_gamma_tt,
        "supplemental_gamma_TT_s": new_gamma_tt,
        "combined_gamma_TT_s": combined_gamma_tt,
        "combined_gamma_event_weight_cps": combined_gamma_weight,
        "combined_gamma_detector_positive_templates": int(gamma["event_count"]),
        "combined_gamma_W2_final_raw_survivors": gamma_final_raw,
        "combined_gamma_W2_final_rate_cps": gamma_final_raw * combined_gamma_weight,
        "combined_gamma_W2_final_rate_sigma_cps": math.sqrt(gamma_final_raw) * combined_gamma_weight,
        "combined_gamma_W2_final_relative_sigma": 1.0 / math.sqrt(gamma_final_raw) if gamma_final_raw else math.inf,
        "stopping_rule": "combined prompt-gamma W2 final raw survivors >= 10",
        "stopping_rule_met": gamma_final_raw >= 10,
        "publication_precision_rule": "total direct-final day-15 relative statistical uncertainty < 0.20",
        "publication_precision_rule_met": precision_rule_met,
        "TT_normalization": (
            "pooled exact exposure per primary from retained 15-shard activation-TT reference"
            if args.cache_only else "per-shard activation TT"
        ),
        "direct_final_day15": totals[("w2_510p58_511p42", "compton_trajectory_veto")],
        "catalog": str(OUT / "combined_event_catalog.npz"),
        "category_registry": str(OUT / "category_registry.json"),
        "supplemental_jobs": [
            {
                "job_id": job["job_id"],
                "events": job["events"],
                "TT_s": job["TT_s"],
                "TT_provenance": job.get("TT_provenance", "per-shard activation TT"),
                "source_seed": job["source_seed"],
                "sim_header_seed": job["seed"],
                "source": job["source_path"],
                "sim": job["sim_path"],
            }
            for job in jobs
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
