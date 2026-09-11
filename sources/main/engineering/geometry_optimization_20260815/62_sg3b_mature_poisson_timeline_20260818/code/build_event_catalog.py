#!/usr/bin/env python3
"""Build a compact SG3B event/deposit catalog for mature time-axis replay."""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
OUT = PACKAGE / "outputs/01_event_catalog"
CACHE = OUT / "job_catalogs"
PIXEL_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
STAGE_BITS = {
    "pre_veto": 1 << 0,
    "plastic_positron_veto": 1 << 1,
    "bgo_active_scintillator_veto": 1 << 2,
    "combined_active_veto": 1 << 3,
    "compton_trajectory_veto": 1 << 4,
}
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
_COMMON: Any | None = None


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def common_module() -> Any:
    global _COMMON
    if _COMMON is None:
        config = load_json(CONFIG)
        _COMMON = load_module("sg3b_mature_catalog_common", resolve(config["package58_code"]))
    return _COMMON


def flags_for_event(
    measured_hits: list[Any], measured_total: float, plastic_keV: float, bgo_keV: float,
    threshold_keV: float, common: Any, step05: Any, disk: dict[str, Any],
) -> tuple[int, int]:
    plastic_pass = plastic_keV < threshold_keV
    bgo_pass = bgo_keV < threshold_keV
    combined = plastic_pass and bgo_pass
    topology_pass = False
    if combined and common.in_window(measured_total, WINDOWS["broad_480_550"]):
        topology_pass, _ = common.topology_keep(measured_hits, step05, disk)
    bits = 0
    if common.in_window(measured_total, WINDOWS["broad_480_550"]):
        bits |= STAGE_BITS["pre_veto"]
        if plastic_pass:
            bits |= STAGE_BITS["plastic_positron_veto"]
        if bgo_pass:
            bits |= STAGE_BITS["bgo_active_scintillator_veto"]
        if combined:
            bits |= STAGE_BITS["combined_active_veto"]
        if combined and topology_pass:
            bits |= STAGE_BITS["compton_trajectory_veto"]
    w2 = 0
    if common.in_window(measured_total, WINDOWS["w2_510p58_511p42"]):
        w2 |= STAGE_BITS["pre_veto"]
        if plastic_pass:
            w2 |= STAGE_BITS["plastic_positron_veto"]
        if bgo_pass:
            w2 |= STAGE_BITS["bgo_active_scintillator_veto"]
        if combined:
            w2 |= STAGE_BITS["combined_active_veto"]
        if combined and topology_pass:
            w2 |= STAGE_BITS["compton_trajectory_veto"]
    return bits, w2


def scan_job(job: dict[str, Any], cache_dir_text: str, threshold_keV: float) -> dict[str, Any]:
    common = common_module()
    parser, core, step05, disk = common.runtime()
    cache_dir = Path(cache_dir_text)
    cache_path = cache_dir / f"job_{int(job['scan_index']):03d}_{job['job_id']}.npz"
    meta_path = cache_path.with_suffix(".json")
    if cache_path.is_file() and meta_path.is_file():
        meta = load_json(meta_path)
        if (
            meta.get("status") == "PASS__COMPACT_JOB_CATALOG"
            and int(meta.get("events", -1)) == int(job["events"])
            and int(meta.get("sim_bytes", -1)) == int(job["sim_bytes"])
        ):
            return meta

    plastic_volumes = set(job["plastic_volumes"])
    bgo_volumes = set(job["bgo_volumes"])
    locator = common.position_locator(Path(job["positions_path"])) if job["stream"] == "delayed" else None

    event_id: list[int] = []
    source_za: list[int] = []
    plastic_values: list[float] = []
    bgo_values: list[float] = []
    measured_totals: list[float] = []
    broad_flags: list[int] = []
    w2_flags: list[int] = []
    hit_start: list[int] = []
    hit_count: list[int] = []
    hit_code: list[int] = []
    hit_layer: list[int] = []
    hit_energy: list[float] = []
    hit_x: list[float] = []
    hit_y: list[float] = []
    hit_z: list[float] = []

    current_id: int | None = None
    current_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    pixels: dict[str, dict[str, float | int]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0
    generated = 0
    header_geometry = ""
    header_seed: int | None = None
    max_position_distance = 0.0
    za_mismatch = 0

    def flush() -> None:
        nonlocal current_id, current_za, production_xyz, init_count, pixels, plastic_keV, bgo_keV
        nonlocal max_position_distance, za_mismatch
        if current_id is None:
            return
        resolved_za = -1
        if job["stream"] == "delayed":
            if init_count != 1 or current_za is None or production_xyz is None or locator is None:
                raise RuntimeError(f"{job['job_id']} event {current_id}: delayed INIT closure failed")
            source_meta, distance = common.locate_source(locator, production_xyz)
            resolved_za = int(source_meta[1])
            max_position_distance = max(max_position_distance, float(distance))
            # IA INIT's ZA is retained only as a diagnostic.  The mature M05
            # chain assigns activation lineage from the exact production
            # position; the two labels are not required to be identical.
            za_mismatch += int(resolved_za != current_za)

        detector_positive = bool(pixels) or plastic_keV > 0.0 or bgo_keV > 0.0
        if not detector_positive:
            current_id = None
            current_za = None
            production_xyz = None
            init_count = 0
            pixels = {}
            plastic_keV = 0.0
            bgo_keV = 0.0
            return

        raw_rows: list[tuple[str, int, int, float, float, float, float]] = []
        measured_hits: list[Any] = []
        for uid, record in sorted(pixels.items()):
            energy = float(record["e"])
            if energy <= 0.0:
                continue
            match = PIXEL_RE.match(uid)
            if not match:
                raise RuntimeError(f"unrecognized TES pixel UID: {uid}")
            layer = int(match.group("layer"))
            pixel = int(match.group("pixel"))
            x = float(record["wx"]) / energy
            y = float(record["wy"]) / energy
            z = float(record["wz"]) / energy
            raw_rows.append((uid, layer, layer * 100_000 + pixel, energy, x, y, z))
            measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
                "sg3b", job["mode"], job["family"], job["batch_id"], int(job["seed"]),
                job["job_id"], int(current_id), uid,
            )
            if measured >= core.PIXEL_THRESHOLD_KEV:
                measured_hits.append(SimpleNamespace(e=measured, x=x, y=y, z=z, pixel_uid=uid, layer=layer))
        measured_total = math.fsum(hit.e for hit in measured_hits)
        broad, w2 = flags_for_event(
            measured_hits, measured_total, plastic_keV, bgo_keV, threshold_keV, common, step05, disk
        )
        event_id.append(int(current_id))
        source_za.append(resolved_za)
        plastic_values.append(plastic_keV)
        bgo_values.append(bgo_keV)
        measured_totals.append(measured_total)
        broad_flags.append(broad)
        w2_flags.append(w2)
        hit_start.append(len(hit_energy))
        hit_count.append(len(raw_rows))
        for _, layer, code, energy, x, y, z in raw_rows:
            hit_code.append(code)
            hit_layer.append(layer)
            hit_energy.append(energy)
            hit_x.append(x)
            hit_y.append(y)
            hit_z.append(z)

        current_id = None
        current_za = None
        production_xyz = None
        init_count = 0
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0

    started = time.time()
    with gzip.open(job["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry"):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed"):
                header_seed = int(line.split()[1])
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise RuntimeError(f"{job['job_id']}: ID before event boundary")
                current_id = int(match.group(1))
                generated += 1
                continue
            if line.startswith("IA INIT") and job["stream"] == "delayed":
                fields = [value.strip() for value in line.split(";")]
                if len(fields) < 16:
                    raise RuntimeError(f"{job['job_id']}: malformed IA INIT")
                init_count += 1
                current_za = int(fields[15])
                production_xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parser.parse_cc_hit(line)
            if hit is None:
                continue
            volume, edep, x, y, z = hit
            pixel_match = parser.TP_RE.match(volume)
            if pixel_match:
                record = pixels.setdefault(
                    volume,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(pixel_match.group("layer"))},
                )
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in plastic_volumes:
                plastic_keV += edep
            elif volume in bgo_volumes:
                bgo_keV += edep
    flush()

    if generated != int(job["events"]):
        raise RuntimeError(f"{job['job_id']}: generated {generated} != receipt {job['events']}")
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve():
        raise RuntimeError(f"{job['job_id']}: geometry mismatch")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: seed mismatch")
    arrays = {
        "event_id": np.asarray(event_id, dtype=np.int32),
        "source_za": np.asarray(source_za, dtype=np.int32),
        "plastic_keV": np.asarray(plastic_values, dtype=np.float32),
        "bgo_keV": np.asarray(bgo_values, dtype=np.float32),
        "measured_total_keV": np.asarray(measured_totals, dtype=np.float32),
        "broad_flags": np.asarray(broad_flags, dtype=np.uint8),
        "w2_flags": np.asarray(w2_flags, dtype=np.uint8),
        "hit_start": np.asarray(hit_start, dtype=np.int32),
        "hit_count": np.asarray(hit_count, dtype=np.uint16),
        "hit_code": np.asarray(hit_code, dtype=np.int32),
        "hit_layer": np.asarray(hit_layer, dtype=np.uint8),
        "hit_energy_keV": np.asarray(hit_energy, dtype=np.float32),
        "hit_x_cm": np.asarray(hit_x, dtype=np.float32),
        "hit_y_cm": np.asarray(hit_y, dtype=np.float32),
        "hit_z_cm": np.asarray(hit_z, dtype=np.float32),
    }
    tmp = cache_path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(tmp, cache_path)
    meta = {
        "status": "PASS__COMPACT_JOB_CATALOG",
        "scan_index": int(job["scan_index"]),
        "stream": job["stream"],
        "family": job["family"],
        "batch_id": job["batch_id"],
        "job_id": job["job_id"],
        "seed": int(job["seed"]),
        "events": generated,
        "sim_path": job["sim_path"],
        "sim_bytes": int(job["sim_bytes"]),
        "weight_cps": float(job["weight_cps"]),
        "detector_positive_events": len(event_id),
        "tes_positive_events": int(np.count_nonzero(arrays["hit_count"])),
        "active_only_events": int(np.count_nonzero(arrays["hit_count"] == 0)),
        "raw_pixel_hits": len(hit_energy),
        "max_position_match_distance_cm": max_position_distance,
        "source_ZA_mismatch_events": za_mismatch,
        "elapsed_s": time.time() - started,
        "catalog_path": str(cache_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def merge_catalogs(jobs: list[dict[str, Any]], metas: list[dict[str, Any]], package58: Path) -> dict[str, Any]:
    expected_rows = read_csv(package58 / "outputs/01_common_time_response/input_job_semantic_scan.csv")
    def identity(row: dict[str, Any]) -> tuple[str, str, str, str]:
        # Job names are reused across accepted, seed-distinct prompt batches.
        # The receipt authority is therefore the four-field identity, never the
        # human-readable job_id alone.
        return (str(row["stream"]), str(row["family"]), str(row["batch_id"]), str(row["job_id"]))

    expected = {identity(row): row for row in expected_rows}
    meta_by_job = {identity(row): row for row in metas}
    job_identities = {identity(job) for job in jobs}
    if len(expected) != len(expected_rows) or len(meta_by_job) != len(metas):
        raise RuntimeError("composite receipt identity is not unique")
    if set(meta_by_job) != job_identities or set(expected) != job_identities:
        raise RuntimeError("job catalog metadata closure differs")
    for job in jobs:
        key = identity(job)
        meta = meta_by_job[key]
        row = expected[key]
        for key_meta, key_expected in (
            ("detector_positive_events", "detector_occupancy_events"),
            ("tes_positive_events", "tes_positive_events"),
            ("active_only_events", "active_only_events"),
            ("source_ZA_mismatch_events", "init_source_za_mismatch_events"),
        ):
            if int(meta[key_meta]) != int(row[key_expected]):
                raise RuntimeError(f"{job['job_id']}: {key_meta} closure differs")
        if not math.isclose(
            float(meta["max_position_match_distance_cm"]),
            float(row["max_position_match_distance_cm"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise RuntimeError(f"{job['job_id']}: exact-position match-distance closure differs")

    event_fields = (
        "plastic_keV", "bgo_keV", "measured_total_keV", "broad_flags", "w2_flags",
        "hit_start", "hit_count",
    )
    category_chunks: dict[tuple[str, str, int], dict[str, list[np.ndarray]]] = defaultdict(
        lambda: {field: [] for field in event_fields}
    )
    category_weights: dict[tuple[str, str, int], float] = {}
    hit_fields = ("hit_code", "hit_layer", "hit_energy_keV", "hit_x_cm", "hit_y_cm", "hit_z_cm")
    global_hits: dict[str, list[np.ndarray]] = {field: [] for field in hit_fields}
    hit_offset = 0
    for job in sorted(jobs, key=lambda row: int(row["scan_index"])):
        meta = meta_by_job[identity(job)]
        with np.load(meta["catalog_path"], allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
        for field in hit_fields:
            global_hits[field].append(arrays[field])
        starts = arrays["hit_start"].astype(np.int64) + hit_offset
        hit_offset += len(arrays["hit_code"])
        zas = arrays["source_za"]
        keys = [(-1, np.arange(len(zas), dtype=np.int64))] if job["stream"] == "prompt" else [
            (int(za), np.flatnonzero(zas == za)) for za in np.unique(zas)
        ]
        for za, indices in keys:
            key = (job["stream"], job["family"], za)
            old = category_weights.setdefault(key, float(job["weight_cps"]))
            if not math.isclose(old, float(job["weight_cps"]), rel_tol=0.0, abs_tol=1e-18):
                raise RuntimeError(f"category weight differs across jobs: {key}")
            target = category_chunks[key]
            for field in event_fields:
                source = starts if field == "hit_start" else arrays[field]
                target[field].append(source[indices])

    combined: dict[str, list[np.ndarray]] = {field: [] for field in event_fields}
    event_category: list[np.ndarray] = []
    category_rows: list[dict[str, Any]] = []
    event_offset = 0
    for category_id, key in enumerate(sorted(category_chunks)):
        stream, family, za = key
        chunks = category_chunks[key]
        count = sum(len(chunk) for chunk in chunks["plastic_keV"])
        category_rows.append({
            "category_id": category_id,
            "stream": stream,
            "family": family,
            "source_parent_ZA": za,
            "event_start": event_offset,
            "event_count": count,
            "base_event_weight_cps": category_weights[key],
            "base_detector_positive_rate_cps": count * category_weights[key],
        })
        for field in event_fields:
            combined[field].append(np.concatenate(chunks[field]) if chunks[field] else np.empty(0))
        event_category.append(np.full(count, category_id, dtype=np.uint16))
        event_offset += count

    output_arrays: dict[str, np.ndarray] = {
        field: np.concatenate(chunks) if chunks else np.empty(0)
        for field, chunks in combined.items()
    }
    output_arrays["event_category"] = np.concatenate(event_category)
    for field, chunks in global_hits.items():
        output_arrays[field] = np.concatenate(chunks) if chunks else np.empty(0)
    catalog_path = OUT / "combined_event_catalog.npz"
    tmp = catalog_path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **output_arrays)
    os.replace(tmp, catalog_path)
    (OUT / "category_registry.json").write_text(
        json.dumps({"schema_version": 1, "categories": category_rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    cutflow = read_csv(package58 / "outputs/01_common_time_response/sg3b_measured_cutflow.csv")
    expected_rates = {
        (row["stream"], row["family"], row["stage"], row["window_id"]): float(row["weighted_rate_cps"])
        for row in cutflow
    }
    observed_rates: dict[tuple[str, str, str, str], float] = defaultdict(float)
    for row in category_rows:
        start = int(row["event_start"])
        stop = start + int(row["event_count"])
        weight = float(row["base_event_weight_cps"])
        for window_id, flag_field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
            flags = output_arrays[flag_field][start:stop]
            for stage, bit in STAGE_BITS.items():
                observed_rates[(row["stream"], row["family"], stage, window_id)] += int(np.count_nonzero(flags & bit)) * weight
    differences = []
    for key, expected_rate in sorted(expected_rates.items()):
        observed = observed_rates[key]
        differences.append({
            "stream": key[0], "family": key[1], "stage": key[2], "window_id": key[3],
            "package58_rate_cps": expected_rate, "catalog_rate_cps": observed,
            "difference_cps": observed - expected_rate,
        })
        if not math.isclose(observed, expected_rate, rel_tol=0.0, abs_tol=2e-10):
            raise RuntimeError(f"direct cutflow closure differs for {key}: {observed} vs {expected_rate}")
    with (OUT / "direct_cutflow_closure.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(differences[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(differences)
    return {
        "combined_catalog_path": str(catalog_path),
        "category_registry": str(OUT / "category_registry.json"),
        "event_templates": int(len(output_arrays["event_category"])),
        "raw_pixel_hits": int(len(output_arrays["hit_code"])),
        "categories": len(category_rows),
        "direct_cutflow_max_abs_difference_cps": max(abs(row["difference_cps"]) for row in differences),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG)
    common = common_module()
    common_config = load_json(resolve(config["package58_config"]))
    jobs, audit = common.prepare_jobs(common_config)
    threshold = float(common_config["active_veto"]["offline_threshold_keV"])
    metas: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(scan_job, job, str(CACHE), threshold): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            meta = future.result()
            metas.append(meta)
            print(json.dumps({
                "job_id": job["job_id"], "stream": job["stream"],
                "catalog_events": meta["detector_positive_events"],
                "elapsed_s": meta["elapsed_s"], "complete": len(metas), "total": len(jobs),
            }), flush=True)
    package58 = resolve(config["package58"])
    merged = merge_catalogs(jobs, metas, package58)
    summary = {
        "status": "PASS__SG3B_COMPACT_EVENT_CATALOG__PACKAGE58_DIRECT_CLOSURE",
        "authority_boundary": {
            "accepted_jobs": len(jobs),
            "prompt_instant_events": audit["prompt_instant_events_analyzed"],
            "delayed_triggers": audit["delayed_triggers_analyzed"],
            "SIM_payloads_streamed": len(jobs),
            "SIM_payload_bytes_streamed": sum(int(job["sim_bytes"]) for job in jobs),
            "SIM_hashes_computed": 0,
            "Cosima_transport_started": False,
            "parma_mono511_included": False,
        },
        "normalization": {
            "prompt_rule": "selected/sum(TT_family) over all accepted instant receipts",
            "prompt_sum_TT_s_by_family": audit["prompt_sum_TT_s_by_family"],
            "prompt_instant_events_by_family": {
                family: sum(int(job["events"]) for job in jobs if job["stream"] == "prompt" and job["family"] == family)
                for family in sorted({job["family"] for job in jobs})
            },
            "delayed_rule": "selected * transported_ground_activity_Bq / 1,000,000 within family at day 15",
            "delayed_day15_activity_Bq_by_family": audit["delayed_day15_activity_Bq_by_family"],
            "delayed_triggers_by_family": {
                family: sum(int(job["events"]) for job in jobs if job["stream"] == "delayed" and job["family"] == family)
                for family in sorted({job["family"] for job in jobs})
            },
        },
        "merged": merged,
        "jobs": sorted(metas, key=lambda row: int(row["scan_index"])),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "merged": merged}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
