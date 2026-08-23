#!/usr/bin/env python3
"""Build the corrected-keV M05 prompt catalog and screening tables.

This is a path/config adapter around the retained M05 compact-catalog parser,
the corrected keyed TES response, and the retained Step05 Compton/FoV code.
Published ledgers and receipts select the SIM files; large SIM hashes are not
recomputed here.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import pickle
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
DEFAULT_CONFIG = PACKAGE / "analysis_inputs.json"
DEFAULT_OUTPUT = PACKAGE / "outputs/01_prompt"
OLD_CATALOG_PARSER = ROOT / "old/code/tools/make_complete_day15_report_ADR.py"
CORRECTED_CORE = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "composite_partial_postprocess_20260812/code/analyze_composite_partial.py"
)
STEP05 = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_corrected_prompt_matplotlib")

GEOMETRY_ORDER = ("Mass_model_511", "S3d_O8")
FAMILY_ORDER = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
CORE_GEOMETRY = {"Mass_model_511": "mass_model_511", "S3d_O8": "s3d_o8"}
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
SPECTRUM_LO_KEV = 480.0
SPECTRUM_HI_KEV = 550.0
SPECTRUM_BIN_KEV = 0.5

_OLD: Any | None = None


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def old_parser() -> Any:
    global _OLD
    if _OLD is None:
        old_tools = str(OLD_CATALOG_PARSER.parent)
        if old_tools not in sys.path:
            sys.path.insert(0, old_tools)
        _OLD = load_module("m05_retained_compact_catalog_parser", OLD_CATALOG_PARSER)
    return _OLD


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def select_instant_jobs(config: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for input_index, entry in enumerate(config["transport_inputs"]):
        ledger_path = check_inputs.repo_path(entry["path"])
        ledger = check_inputs.load_json(ledger_path)
        for row in check_inputs.selected_jobs(ledger, entry, config):
            if row["mode"] != "instant":
                continue
            geometry = row["geometry"]
            active = list(config["geometries"][geometry]["active_veto_volumes"])
            row.update(
                {
                    "input_index": input_index,
                    "ledger_path": entry["path"],
                    "sim_path": str(check_inputs.repo_path(row["sim_path"]).resolve()),
                    "shield_volumes": [name for name in active if "Plastic" not in name],
                    "plastic_volumes": [name for name in active if "Plastic" in name],
                }
            )
            jobs.append(row)
    jobs.sort(
        key=lambda row: (
            GEOMETRY_ORDER.index(row["geometry"]),
            FAMILY_ORDER.index(row["family"]),
            row["input_index"],
            row["ordinal"] is None,
            row["ordinal"] or 0,
            row["job_id"],
        )
    )
    for index, row in enumerate(jobs):
        row["scan_index"] = index
    return jobs


def smoke_subset(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: dict[tuple[str, str], dict[str, Any]] = {}
    for job in jobs:
        chosen.setdefault((job["geometry"], job["family"]), job)
    return [chosen[(geometry, family)] for geometry in GEOMETRY_ORDER for family in FAMILY_ORDER]


def scan_job(job: dict[str, Any], cache_dir: str) -> dict[str, Any]:
    """Reuse retained catalog primitives while adding exact plastic bookkeeping."""
    parser = old_parser()
    catalog = parser.empty_catalog()
    extras: dict[str, list[Any]] = {
        "input_id": [],
        "batch_id": [],
        "job_name": [],
        "seed": [],
        "plastic_total_keV": [],
        "has_pair_ia": [],
        "has_annihilation_ia": [],
    }
    shield = set(job["shield_volumes"])
    plastic = set(job["plastic_volumes"])
    current_id: int | None = None
    active_total = 0.0
    plastic_total = 0.0
    pixels: dict[str, dict[str, float | int]] = {}
    has_pair = False
    has_annihilation = False
    generated = 0
    active_only = 0

    def flush() -> None:
        nonlocal current_id, active_total, plastic_total, pixels
        nonlocal has_pair, has_annihilation, active_only
        if current_id is None:
            return
        if pixels:
            before = len(catalog["stream"])
            parser.append_event(
                catalog,
                "prompt",
                job["family"],
                job["sim_path"],
                current_id,
                0.0,
                active_total,
                pixels,
            )
            if len(catalog["stream"]) == before + 1:
                extras["input_id"].append(job["input_id"])
                extras["batch_id"].append(job["batch_id"])
                extras["job_name"].append(job["job_id"])
                extras["seed"].append(job["seed"])
                extras["plastic_total_keV"].append(plastic_total)
                extras["has_pair_ia"].append(has_pair)
                extras["has_annihilation_ia"].append(has_annihilation)
        elif active_total > 0.0 or plastic_total > 0.0:
            active_only += 1
        current_id = None
        active_total = 0.0
        plastic_total = 0.0
        pixels = {}
        has_pair = False
        has_annihilation = False

    with parser.open_text(job["sim_path"]) as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                current_id = int(match.group(1))
                generated += 1
                continue
            if line.startswith("IA PAIR"):
                has_pair = True
                continue
            if line.startswith("IA ANNI"):
                has_annihilation = True
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
                    {
                        "e": 0.0,
                        "wx": 0.0,
                        "wy": 0.0,
                        "wz": 0.0,
                        "layer": int(pixel_match.group("layer")),
                    },
                )
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in shield:
                active_total += edep
            elif volume in plastic:
                plastic_total += edep
    flush()
    if generated != job["events"]:
        raise RuntimeError(f"event count differs for {job['job_id']}: {generated} != {job['events']}")

    catalog.update(extras)
    catalog["n_generated_events_seen"] = generated
    catalog["active_only_events"] = active_only
    cache_path = Path(cache_dir) / f"job_{job['scan_index']:04d}.pkl"
    with cache_path.open("wb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return {
        "scan_index": job["scan_index"],
        "path": str(cache_path),
        "geometry": job["geometry"],
        "family": job["family"],
        "generated_events": generated,
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": active_only,
        "pixel_hits": len(catalog["pix_e"]),
    }


def merge_cell(
    jobs: list[dict[str, Any]], results: dict[int, dict[str, Any]], target: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    parser = old_parser()
    merged = parser.empty_catalog()
    extra_names = (
        "input_id",
        "batch_id",
        "job_name",
        "seed",
        "plastic_total_keV",
        "has_pair_ia",
        "has_annihilation_ia",
    )
    extras = {name: [] for name in extra_names}
    active_only = 0
    for job in jobs:
        with Path(results[job["scan_index"]]["path"]).open("rb") as handle:
            catalog = pickle.load(handle)
        parser.merge_one_catalog_into(merged, catalog)
        for name in extra_names:
            extras[name].extend(catalog[name])
        active_only += int(catalog["active_only_events"])
    merged.update(extras)
    tt_s = math.fsum(float(job["TT_s"]) for job in jobs)
    weight = 1.0 / tt_s
    merged["rate_hz"] = [weight] * len(merged["stream"])
    merged["generated_events"] = sum(int(job["events"]) for job in jobs)
    merged["active_only_events"] = active_only
    merged["active_only_rate_hz"] = active_only * weight
    merged["cell_metadata"] = {
        "geometry": jobs[0]["geometry"],
        "family": jobs[0]["family"],
        "mode": "instant",
        "jobs": len(jobs),
        "generated_events": merged["generated_events"],
        "TT_s": tt_s,
        "event_weight_cps": weight,
        "normalization": "selected events / sum(TT) within geometry x instant x family",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        pickle.dump(merged, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return merged, merged["cell_metadata"]


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def topology_keep(hits: list[Any], step05: Any, disk: dict[str, Any]) -> tuple[bool, str]:
    if len(hits) == 1:
        return True, "single"
    if len(hits) > int(step05.MAX_ENUM_HITS):
        return True, "reject_kept"
    return step05.side_keep_from_hits(hits, disk, "keep")


def evaluate_event(
    catalog: dict[str, Any],
    event_index: int,
    core: Any,
    step05: Any,
    disk: dict[str, Any],
) -> dict[str, Any]:
    """Apply the shared keyed response, exact veto, and Step05 to one event."""
    meta = catalog["cell_metadata"]
    geometry = meta["geometry"]
    family = meta["family"]
    mode = str(meta.get("mode", "instant"))
    core_geometry = CORE_GEOMETRY[geometry]
    start = int(catalog["pix_start"][event_index])
    stop = start + int(catalog["pix_count"][event_index])
    raw_hits: list[Any] = []
    measured_hits: list[Any] = []
    for hit_index in range(start, stop):
        energy = float(catalog["pix_e"][hit_index])
        uid = str(catalog["pix_uid"][hit_index])
        common = {
            "x": float(catalog["pix_x"][hit_index]),
            "y": float(catalog["pix_y"][hit_index]),
            "z": float(catalog["pix_z"][hit_index]),
            "pixel_uid": uid,
            "layer": int(catalog["pix_layer"][hit_index]),
        }
        raw_hits.append(SimpleNamespace(e=energy, **common))
        measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
            core_geometry,
            mode,
            family,
            catalog["batch_id"][event_index],
            int(catalog["seed"][event_index]),
            catalog["job_name"][event_index],
            int(catalog["local_id"][event_index]),
            uid,
        )
        if measured >= core.PIXEL_THRESHOLD_KEV:
            measured_hits.append(SimpleNamespace(e=measured, **common))

    shield_keV = float(catalog["bgo_total_keV"][event_index])
    plastic_keV = float(catalog["plastic_total_keV"][event_index])
    active_pass = {
        threshold: shield_keV < threshold
        and (geometry != "S3d_O8" or plastic_keV < core.O8_PLASTIC_THRESHOLD_KEV)
        for threshold in (50.0, 70.0, 80.0)
    }
    measured_total = math.fsum(hit.e for hit in measured_hits)
    topology_pass = False
    topology_class = "not_evaluated"
    if active_pass[50.0] and in_window(measured_total, WINDOWS["broad_480_550"]):
        topology_pass, topology_class = topology_keep(measured_hits, step05, disk)
    return {
        "raw_hits": raw_hits,
        "measured_hits": measured_hits,
        "raw_total_keV": math.fsum(hit.e for hit in raw_hits),
        "measured_total_keV": measured_total,
        "shield_keV": shield_keV,
        "plastic_keV": plastic_keV,
        "active_pass": active_pass,
        "topology_pass": topology_pass,
        "topology_class": topology_class,
    }


def evaluate_cell(
    catalog: dict[str, Any], core: Any, step05: Any, disk: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], tuple[int, float, float]], dict[str, Any]]:
    meta = catalog["cell_metadata"]
    geometry = meta["geometry"]
    family = meta["family"]
    mode = str(meta.get("mode", "instant"))
    normalization_time_s = float(meta["TT_s"])
    weight = (
        float(meta["event_weight_cps"])
        if "event_weight_cps" in meta
        else 1.0 / normalization_time_s
    )
    counts: Counter[tuple[str, str, str]] = Counter()
    spectrum_counts: Counter[tuple[str, str, int]] = Counter()
    topology_classes: Counter[str] = Counter()
    n_bins = int(round((SPECTRUM_HI_KEV - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV))

    for event_index in range(len(catalog["stream"])):
        event = evaluate_event(catalog, event_index, core, step05, disk)
        responses = {"raw": event["raw_hits"], "measured": event["measured_hits"]}
        active_pass = event["active_pass"]
        topology_pass = bool(event["topology_pass"])
        topology_class = str(event["topology_class"])
        if topology_class != "not_evaluated":
            topology_classes[topology_class] += 1

        for response, hits in responses.items():
            total = math.fsum(hit.e for hit in hits)
            stage_flags = {
                "pre_veto": True,
                "active_veto50": active_pass[50.0],
                "active_veto70": active_pass[70.0],
                "active_veto80": active_pass[80.0],
            }
            if response == "measured":
                stage_flags["side_compton_fov_pass"] = active_pass[50.0] and topology_pass
            for stage, passes in stage_flags.items():
                if not passes:
                    continue
                for window_id, bounds in WINDOWS.items():
                    if in_window(total, bounds):
                        counts[(response, stage, window_id)] += 1
                if SPECTRUM_LO_KEV <= total < SPECTRUM_HI_KEV:
                    bin_index = int((total - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV)
                    if 0 <= bin_index < n_bins:
                        spectrum_counts[(response, stage, bin_index)] += 1

    cutflow: list[dict[str, Any]] = []
    for response in ("raw", "measured"):
        stages = ["pre_veto", "active_veto50", "active_veto70", "active_veto80"]
        if response == "measured":
            stages.append("side_compton_fov_pass")
        for stage in stages:
            for window_id, bounds in WINDOWS.items():
                count = int(counts[(response, stage, window_id)])
                low, high = core.gamma.garwood_interval(count)
                cutflow.append(
                    {
                        "geometry": geometry,
                        "family": family,
                        "mode": mode,
                        "response_state": response,
                        "stage": stage,
                        "window_id": window_id,
                        "energy_lo_keV": bounds[0],
                        "energy_hi_keV": bounds[1],
                        "generated_events": int(meta["generated_events"]),
                        "TT_s": normalization_time_s,
                        "selected_events": count,
                        "event_weight_cps": weight,
                        "rate_cps": count * weight,
                        "rate_stat_sigma_cps": math.sqrt(count) * weight,
                        "rate_lower95_cps": low * weight,
                        "rate_upper95_cps": high * weight,
                        "authority_status": meta.get("authority_status", "PROMPT_SCREENING_ONLY"),
                    }
                )
    spectrum = {
        key: (int(value), value * weight, value * weight * weight)
        for key, value in spectrum_counts.items()
    }
    occupancy = {
        "geometry": geometry,
        "family": family,
        "generated_events": int(meta["generated_events"]),
        "TT_s": normalization_time_s,
        "detector_occupancy_events": len(catalog["stream"]) + int(catalog["active_only_events"]),
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": int(catalog["active_only_events"]),
        "pixel_hits": len(catalog["pix_e"]),
        "fullband_rate_cps": (len(catalog["stream"]) + int(catalog["active_only_events"])) * weight,
        "tes_rate_cps": len(catalog["stream"]) * weight,
        "active_only_rate_cps": int(catalog["active_only_events"]) * weight,
        "rate_stat_sigma_cps": math.sqrt(len(catalog["stream"]) + int(catalog["active_only_events"])) * weight,
        "topology_class_counts_json": json.dumps(dict(sorted(topology_classes.items())), separators=(",", ":")),
    }
    return cutflow, spectrum, occupancy


def aggregate_spectrum(
    pieces: list[tuple[str, dict[tuple[str, str, int], tuple[int, float, float]]]]
) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str, int], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for geometry, piece in pieces:
        for (response, stage, bin_index), (events, rate, variance) in piece.items():
            row = totals[(geometry, response, stage, bin_index)]
            row[0] += events
            row[1] += rate
            row[2] += variance
    rows: list[dict[str, Any]] = []
    n_bins = int(round((SPECTRUM_HI_KEV - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV))
    for geometry in GEOMETRY_ORDER:
        for response, stages in (
            ("raw", ("pre_veto", "active_veto50")),
            ("measured", ("pre_veto", "active_veto50", "side_compton_fov_pass")),
        ):
            for stage in stages:
                for bin_index in range(n_bins):
                    events, rate, variance = totals[(geometry, response, stage, bin_index)]
                    lo = SPECTRUM_LO_KEV + bin_index * SPECTRUM_BIN_KEV
                    rows.append(
                        {
                            "geometry": geometry,
                            "response_state": response,
                            "stage": stage,
                            "energy_lo_keV": lo,
                            "energy_hi_keV": lo + SPECTRUM_BIN_KEV,
                            "energy_center_keV": lo + 0.5 * SPECTRUM_BIN_KEV,
                            "events_per_bin": int(events),
                            "rate_cps_per_keV": rate / SPECTRUM_BIN_KEV,
                            "rate_stat_sigma_cps_per_keV": math.sqrt(variance) / SPECTRUM_BIN_KEV,
                        }
                    )
    return rows


def geometry_summary(cutflow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0}
    )
    for row in cutflow:
        key = (row["geometry"], row["response_state"], row["stage"], row["window_id"])
        totals[key]["events"] += int(row["selected_events"])
        totals[key]["rate"] += float(row["rate_cps"])
        totals[key]["variance"] += float(row["rate_stat_sigma_cps"]) ** 2
    rows = []
    for key in sorted(
        totals,
        key=lambda value: (GEOMETRY_ORDER.index(value[0]), value[1], value[2], value[3]),
    ):
        value = totals[key]
        rows.append(
            {
                "geometry": key[0],
                "response_state": key[1],
                "stage": key[2],
                "window_id": key[3],
                "descriptive_selected_events_across_families": int(value["events"]),
                "rate_cps_sum_of_family_rates": value["rate"],
                "rate_stat_sigma_cps_quadrature": math.sqrt(value["variance"]),
            }
        )
    return rows


def build_report(summary_rows: list[dict[str, Any]], histories: int, jobs: int) -> str:
    wanted = {
        (row["geometry"], row["stage"], row["window_id"]): row
        for row in summary_rows
        if row["response_state"] == "measured"
    }
    lines = [
        "# Corrected-keV prompt screening",
        "",
        f"Selected {jobs:,} instant jobs and {histories:,} primary histories across two geometries and eight families.",
        "Rates are formed within each geometry×family cell as count/sum(TT), then family rates are added; family TT is never pooled.",
        "",
        "| Geometry | 480–550 measured | after 50-keV veto | after Step05 | W2 measured | after veto | after Step05 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for geometry in GEOMETRY_ORDER:
        def cell(stage: str, window: str) -> str:
            row = wanted[(geometry, stage, window)]
            return f"{int(row['descriptive_selected_events_across_families'])} ({row['rate_cps_sum_of_family_rates']:.6g} cps)"

        lines.append(
            f"| {geometry} | {cell('pre_veto', 'broad_480_550')} | "
            f"{cell('active_veto50', 'broad_480_550')} | {cell('side_compton_fov_pass', 'broad_480_550')} | "
            f"{cell('pre_veto', 'w2_510p58_511p42')} | {cell('active_veto50', 'w2_510p58_511p42')} | "
            f"{cell('side_compton_fov_pass', 'w2_510p58_511p42')} |"
        )
    lines.extend(
        [
            "",
            "This is prompt-only heterogeneous screening. The compact catalogs retain TES hit position and exact active/plastic energy for the shared prompt+delayed+signal response stage.",
            "It is not delayed-background, mission-sensitivity, or geometry-promotion authority.",
            "",
        ]
    )
    return "\n".join(lines)


def run(config_path: Path, output: Path, workers: int, smoke: bool) -> dict[str, Any]:
    config = check_inputs.load_json(config_path)
    jobs = select_instant_jobs(config)
    full_jobs = len(jobs)
    full_histories = sum(int(job["events"]) for job in jobs)
    expected = config["expected_selection_summary"]["by_mode"]["instant"]
    if {"jobs": full_jobs, "histories": full_histories} != expected:
        raise RuntimeError("instant selector differs from input audit")
    if smoke:
        jobs = smoke_subset(jobs)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    cache_dir = work / "job_cache"
    cache_dir.mkdir()
    started = time.monotonic()
    results: dict[int, dict[str, Any]] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scan_job, job, str(cache_dir)): job for job in jobs}
            for completed, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results[result["scan_index"]] = result
                if completed % 10 == 0 or completed == len(jobs):
                    scanned = sum(item["generated_events"] for item in results.values())
                    print(
                        f"scanned {completed}/{len(jobs)} jobs, {scanned:,} events, "
                        f"{time.monotonic() - started:.1f}s",
                        flush=True,
                    )

        core_wrapper = load_module("m05_corrected_partial_core", CORRECTED_CORE)
        core = core_wrapper.core
        step05 = load_module("m05_retained_step05", STEP05)
        step05.ROOT = ROOT
        step05.STEP09_SUMMARY = (
            ROOT
            / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
            / "step09_optics_bridge_summary.json"
        )
        disk = step05.side_entry_disk()

        jobs_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for job in jobs:
            jobs_by_cell[(job["geometry"], job["family"])].append(job)

        cutflow: list[dict[str, Any]] = []
        occupancy: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []
        spectrum_pieces = []
        for geometry in GEOMETRY_ORDER:
            for family in FAMILY_ORDER:
                cell_jobs = jobs_by_cell[(geometry, family)]
                target = work / "catalog" / geometry / f"{family}.pkl"
                catalog, meta = merge_cell(cell_jobs, results, target)
                cell_cutflow, cell_spectrum, cell_occupancy = evaluate_cell(
                    catalog, core, step05, disk
                )
                cutflow.extend(cell_cutflow)
                spectrum_pieces.append((geometry, cell_spectrum))
                occupancy.append(cell_occupancy)
                coverage.append(
                    {
                        "geometry": geometry,
                        "family": family,
                        "completeness_status": "OBSERVED_HETEROGENEOUS_SCREENING",
                        "jobs": meta["jobs"],
                        "generated_events": meta["generated_events"],
                        "TT_s": meta["TT_s"],
                        "tes_positive_events": len(catalog["stream"]),
                        "active_only_events": catalog["active_only_events"],
                        "pixel_hits": len(catalog["pix_e"]),
                        "event_weight_cps": meta["event_weight_cps"],
                        "catalog_path": relative(output / "catalog" / geometry / f"{family}.pkl"),
                    }
                )

        spectrum = aggregate_spectrum(spectrum_pieces)
        summary_rows = geometry_summary(cutflow)
        input_manifest = [
            {
                "input_id": job["input_id"],
                "ledger_path": job["ledger_path"],
                "geometry": job["geometry"],
                "family": job["family"],
                "mode": job["mode"],
                "job_id": job["job_id"],
                "seed": job["seed"],
                "events": job["events"],
                "TT_s": job["TT_s"],
                "sim_path": relative(Path(job["sim_path"])),
                "declared_sim_sha256": job["sim_sha256"],
                "sim_hash_recomputed": False,
            }
            for job in jobs
        ]
        write_csv(work / "prompt_input_manifest.csv", input_manifest)
        write_csv(work / "prompt_cell_coverage.csv", coverage)
        write_csv(work / "prompt_cutflow.csv", cutflow)
        write_csv(work / "prompt_spectrum_480_550.csv", spectrum)
        write_csv(work / "prompt_fullband_occupancy.csv", occupancy)
        write_csv(work / "prompt_geometry_summary.csv", summary_rows)

        selected_histories = sum(int(job["events"]) for job in jobs)
        status = "PASS__M05_CORRECTED_PROMPT_SMOKE" if smoke else "PASS__M05_CORRECTED_PROMPT_SCREENING"
        summary = {
            "schema_version": 1,
            "status": status,
            "scope": "corrected-keV instant prompt; two geometries; eight families",
            "selected_jobs": len(jobs),
            "selected_histories": selected_histories,
            "response": {
                "fwhm_keV": core.FWHM_KEV,
                "pixel_threshold_keV": core.PIXEL_THRESHOLD_KEV,
                "rng": "retained corrected keyed Box-Muller response",
            },
            "active_veto": "Mass exact 24 CsI; S3d-O8 exact 3 BGO plus 3 plastic",
            "compton_fov": "retained Step05 side_keep_from_hits with reject_policy=keep",
            "normalization": "count/sum(TT) per geometry x family; geometry totals sum family rates",
            "large_sim_hash_policy": "use terminal ledger/receipt declarations; do not recompute",
            "gamma_model": "unit_only_total_gamma; no additive mono-511",
            "authority_boundary": "PROMPT_ONLY_HETEROGENEOUS_SCREENING__NOT_DELAYED_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY",
            "geometry_summary": summary_rows,
            "elapsed_s": time.monotonic() - started,
        }
        write_json(work / "summary.json", summary)
        (work / "REPORT.md").write_text(
            build_report(summary_rows, selected_histories, len(jobs)), encoding="utf-8"
        )
        shutil.rmtree(cache_dir)
        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "status": status,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_code": relative(HERE),
            "reused_code": [relative(OLD_CATALOG_PARSER), relative(CORRECTED_CORE), relative(STEP05)],
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in files
            ],
            "hash_note": "No large SIM or derived-output hashes were recomputed in this stage.",
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(f"{status}: {len(jobs)} jobs, {selected_histories} histories, {output}")
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    run(args.config.resolve(), output.resolve(), args.workers, args.smoke)


if __name__ == "__main__":
    main()
