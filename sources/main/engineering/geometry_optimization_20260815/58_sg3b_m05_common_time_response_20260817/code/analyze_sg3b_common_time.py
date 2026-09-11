#!/usr/bin/env python3
"""SG3B corrected-M05 response, common Poisson time axis, and flux reach.

Large SIM payloads are streamed once and are not hashed.  The accepted prompt
receipts and canonical delayed-v2 receipts are the only transport selectors.
The repaired broadband gamma component is kept closed: the standalone PARMA
mono-511 sidecar is never added to the background.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
DEFAULT_OUTPUT = PACKAGE / "outputs/01_common_time_response"
PROMPT_ADAPTER = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_corrected_reanalysis_20260813/code/run_prompt_analysis.py"
)
CORRECTED_CORE = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "composite_partial_postprocess_20260812/code/analyze_composite_partial.py"
)
STEP05 = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
SECONDS_PER_DAY = 86_400.0
DAY15 = 15.0
_RUNTIME: tuple[Any, Any, Any, dict[str, Any]] | None = None


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def runtime() -> tuple[Any, Any, Any, dict[str, Any]]:
    global _RUNTIME
    if _RUNTIME is None:
        adapter_dir = str(PROMPT_ADAPTER.parent)
        if adapter_dir not in sys.path:
            sys.path.insert(0, adapter_dir)
        adapter = load_module("sg3b_m05_prompt_adapter", PROMPT_ADAPTER)
        composite = load_module("sg3b_m05_corrected_core", CORRECTED_CORE)
        step05 = load_module("sg3b_m05_step05", STEP05)
        step05.ROOT = ROOT
        step05.STEP09_SUMMARY = STEP09_SUMMARY
        _RUNTIME = adapter.old_parser(), composite.core, step05, step05.side_entry_disk()
    return _RUNTIME


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def topology_keep(hits: list[Any], step05: Any, disk: dict[str, Any]) -> tuple[bool, str]:
    if len(hits) == 1:
        return True, "single"
    if not hits:
        return False, "zero"
    if len(hits) > int(step05.MAX_ENUM_HITS):
        return True, "reject_kept"
    return step05.side_keep_from_hits(hits, disk, "keep")


def receipt_rows(directory: Path) -> list[dict[str, Any]]:
    rows = [load_json(path) for path in sorted(directory.glob("*.json"))]
    if not rows:
        raise RuntimeError(f"no receipts in {directory}")
    for row in rows:
        if row.get("status") != "PASS":
            raise RuntimeError(f"non-PASS receipt selected: {row.get('job_id')}")
    return rows


def validate_small_source(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"source card missing: {path}")
    text = path.read_text(encoding="utf-8")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError(f"legacy factor-1000 spectrum reference: {path}")


def position_locator(path: Path) -> dict[str, Any]:
    """Build the retained M05 exact-position source-parent mapping."""
    from scipy.spatial import cKDTree

    unique: dict[tuple[float, float, float], tuple[str, int, float]] = {}
    selected_rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["sample_index"]) % 5:
                continue
            selected_rows += 1
            position = (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            value = (row["volume"], int(row["ZA"]), float(row["excitation_keV"]))
            old = unique.setdefault(position, value)
            if old != value:
                raise RuntimeError(f"ambiguous exact source position in {path}: {position}")
    coordinates = np.asarray(list(unique), dtype=np.float64)
    if selected_rows != 10_000 or not len(coordinates):
        raise RuntimeError(f"stride-5 source support is not 10,000 rows: {path}")
    return {"tree": cKDTree(coordinates), "metadata": list(unique.values()), "cache": {}}


def locate_source(
    locator: dict[str, Any], position: tuple[float, float, float]
) -> tuple[tuple[str, int, float], float]:
    """Map five-decimal SIM coordinates to the six-decimal source authority."""
    observed_key = tuple(f"{axis:.5f}" for axis in position)
    cached = locator["cache"].get(observed_key)
    if cached is not None:
        return cached
    count = len(locator["metadata"])
    k = min(8, count)
    second = math.inf
    chosen: tuple[str, int, float] | None = None
    nearest = math.inf
    while True:
        distances, neighbors = locator["tree"].query(
            np.asarray(position, dtype=np.float64), k=k, p=np.inf, workers=1
        )
        distance_values = np.atleast_1d(distances)
        neighbor_values = np.atleast_1d(neighbors)
        nearest = float(distance_values[0])
        chosen = locator["metadata"][int(neighbor_values[0])]
        for distance, neighbor in zip(distance_values[1:], neighbor_values[1:]):
            if locator["metadata"][int(neighbor)] != chosen:
                second = float(distance)
                break
        if math.isfinite(second) or k == count:
            break
        k = min(2 * k, count)
    if not (
        chosen is not None
        and nearest <= 1.0e-3
        and second - nearest >= 1.102e-5
        and second >= 2.0 * max(nearest, 1.0e-30)
    ):
        raise RuntimeError(
            f"source-position lineage is not uniquely resolved: nearest={nearest:.9g}, second={second:.9g} cm"
        )
    result = (chosen, nearest)
    locator["cache"][observed_key] = result
    return result


def prepare_jobs(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_geometry = str(Path(config["geometry_setup"]).resolve())
    plastic = list(config["active_veto"]["plastic_positron_veto_volumes"])
    bgo = list(config["active_veto"]["bgo_active_scintillator_volumes"])
    jobs: list[dict[str, Any]] = []
    prompt_receipts: list[tuple[str, dict[str, Any]]] = []
    prompt_controller = []
    for campaign_text in config["prompt_campaigns"]:
        campaign = Path(campaign_text)
        controller = load_json(campaign / "controller_state.json")
        receipts = receipt_rows(campaign / "receipts")
        prompt_controller.append(
            {
                "campaign": str(campaign),
                "status": controller.get("status"),
                "completed_count": controller.get("completed_count"),
                "receipt_count": len(receipts),
            }
        )
        for receipt in receipts:
            prompt_receipts.append((campaign.name, receipt))
    if len(prompt_receipts) != 41:
        raise RuntimeError(f"prompt/BUILDUP accepted receipt count differs: {len(prompt_receipts)}")
    if sum(int(row["events"]) for _, row in prompt_receipts) != 6_887_107:
        raise RuntimeError("prompt/BUILDUP accepted primary total differs")
    instant = [(batch, row) for batch, row in prompt_receipts if row["mode"] == "instant"]
    if len(instant) != 22 or sum(int(row["events"]) for _, row in instant) != 3_842_079:
        raise RuntimeError("prompt instant selection differs")
    tt_by_family = {
        family: math.fsum(
            float(row["isotope_dat"]["TT_s"])
            for _, row in instant
            if row["family"] == family
        )
        for family in FAMILIES
    }
    for batch, receipt in instant:
        source = Path(receipt["source_path"])
        validate_small_source(source)
        jobs.append(
            {
                "stream": "prompt",
                "family": receipt["family"],
                "mode": "instant",
                "batch_id": batch,
                "job_id": receipt["job_id"],
                "seed": int(receipt["seed"]),
                "events": int(receipt["events"]),
                "sim_path": receipt["sim_path"],
                "source_path": str(source),
                "expected_geometry": expected_geometry,
                "weight_cps": 1.0 / tt_by_family[receipt["family"]],
                "plastic_volumes": plastic,
                "bgo_volumes": bgo,
            }
        )

    delayed_root = Path(config["delayed_campaign"])
    delayed_controller = load_json(delayed_root / "run/controller_state.json")
    delayed_receipts = receipt_rows(delayed_root / "run/receipts")
    if delayed_controller.get("status") != "COMPLETE" or len(delayed_receipts) != 33:
        raise RuntimeError("canonical delayed-v2 controller/receipt closure differs")
    if sum(int(row["events"]) for row in delayed_receipts) != 8_000_000:
        raise RuntimeError("canonical delayed-v2 trigger total differs")
    activation = load_json(Path(config["activation_manifest"]))
    if activation.get("status") != "PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY":
        raise RuntimeError("activation manifest is not canonical PASS")
    activity_by_family = {
        row["family"]: float(row["transported_ground_activity_Bq"])
        for row in activation["activation_cells"]
    }
    positions_by_family = {
        row["family"]: row["positions_path"] for row in activation["source_cells"]
    }
    delayed_events_by_family = Counter()
    for row in delayed_receipts:
        delayed_events_by_family[row["family"]] += int(row["events"])
    if set(delayed_events_by_family) != set(FAMILIES) or any(
        delayed_events_by_family[family] != 1_000_000 for family in FAMILIES
    ):
        raise RuntimeError(f"delayed per-family trigger closure differs: {delayed_events_by_family}")
    for receipt in delayed_receipts:
        source = Path(receipt["source_path"])
        validate_small_source(source)
        family = receipt["family"]
        jobs.append(
            {
                "stream": "delayed",
                "family": family,
                "mode": "delayed",
                "batch_id": delayed_root.name,
                "job_id": receipt["job_id"],
                "seed": int(receipt["seed"]),
                "events": int(receipt["events"]),
                "sim_path": receipt["sim_path"],
                "source_path": str(source),
                "expected_geometry": expected_geometry,
                "weight_cps": activity_by_family[family] / 1_000_000.0,
                "positions_path": positions_by_family[family],
                "plastic_volumes": plastic,
                "bgo_volumes": bgo,
            }
        )
    seeds = [int(job["seed"]) for job in jobs]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("registered seed reuse within analyzed transport jobs")
    for index, job in enumerate(jobs):
        sim = Path(job["sim_path"])
        if not sim.is_file() or sim.stat().st_size <= 0:
            raise RuntimeError(f"SIM missing: {sim}")
        job["scan_index"] = index
        job["sim_bytes"] = sim.stat().st_size
    audit = {
        "prompt_controller": prompt_controller,
        "prompt_accepted_receipts": len(prompt_receipts),
        "prompt_buildup_accepted_primaries": sum(int(row["events"]) for _, row in prompt_receipts),
        "prompt_instant_jobs_analyzed": len(instant),
        "prompt_instant_events_analyzed": sum(int(row["events"]) for _, row in instant),
        "prompt_sum_TT_s_by_family": tt_by_family,
        "delayed_controller_status": delayed_controller.get("status"),
        "delayed_jobs_analyzed": len(delayed_receipts),
        "delayed_triggers_analyzed": sum(int(row["events"]) for row in delayed_receipts),
        "delayed_day15_activity_Bq_by_family": activity_by_family,
        "superseded_delayed_v1_included": False,
        "parma_mono511_added_to_broadband": False,
        "large_SIM_hashes_computed": 0,
    }
    return jobs, audit


def scan_job(job: dict[str, Any], threshold_keV: float, cache_dir: str) -> dict[str, Any]:
    parser, core, step05, disk = runtime()
    locator = position_locator(Path(job["positions_path"])) if job["stream"] == "delayed" else None
    plastic_volumes = set(job["plastic_volumes"])
    bgo_volumes = set(job["bgo_volumes"])
    selected: Counter[str] = Counter()
    selected_by_za: Counter[str] = Counter()
    topology_classes: Counter[str] = Counter()
    occupancy_by_za: Counter[int] = Counter()
    current_id: int | None = None
    current_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    pixels: dict[str, dict[str, float | int]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0
    generated = 0
    occupancy_events = 0
    tes_positive_events = 0
    active_only_events = 0
    pixel_hits = 0
    header_geometry = ""
    header_seed: int | None = None
    init_source_za_mismatch_events = 0
    max_position_match_distance_cm = 0.0

    def flush() -> None:
        nonlocal current_id, current_za, production_xyz, init_count, pixels, plastic_keV, bgo_keV
        nonlocal occupancy_events, tes_positive_events, active_only_events, pixel_hits
        nonlocal init_source_za_mismatch_events, max_position_match_distance_cm
        if current_id is None:
            return
        if job["stream"] == "delayed" and (
            init_count != 1 or current_za is None or production_xyz is None or locator is None
        ):
            raise RuntimeError(f"{job['job_id']} event {current_id}: delayed IA INIT closure failed")
        source_za: int | None = None
        if job["stream"] == "delayed":
            source_metadata, match_distance = locate_source(locator, production_xyz)
            source_za = int(source_metadata[1])
            max_position_match_distance_cm = max(max_position_match_distance_cm, match_distance)
            init_source_za_mismatch_events += int(source_za != current_za)
        detector_positive = bool(pixels) or plastic_keV > 0.0 or bgo_keV > 0.0
        if detector_positive:
            occupancy_events += 1
            if source_za is not None:
                occupancy_by_za[source_za] += 1
        if not pixels:
            if plastic_keV > 0.0 or bgo_keV > 0.0:
                active_only_events += 1
        else:
            tes_positive_events += 1
            raw_hits: list[Any] = []
            measured_hits: list[Any] = []
            for uid, record in pixels.items():
                energy = float(record["e"])
                if energy <= 0.0:
                    continue
                common = {
                    "x": float(record["wx"]) / energy,
                    "y": float(record["wy"]) / energy,
                    "z": float(record["wz"]) / energy,
                    "pixel_uid": uid,
                    "layer": int(record["layer"]),
                }
                raw_hits.append(SimpleNamespace(e=energy, **common))
                measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
                    "sg3b",
                    job["mode"],
                    job["family"],
                    job["batch_id"],
                    int(job["seed"]),
                    job["job_id"],
                    int(current_id),
                    uid,
                )
                if measured >= core.PIXEL_THRESHOLD_KEV:
                    measured_hits.append(SimpleNamespace(e=measured, **common))
            pixel_hits += len(raw_hits)
            measured_total = math.fsum(hit.e for hit in measured_hits)
            plastic_pass = plastic_keV < threshold_keV
            bgo_pass = bgo_keV < threshold_keV
            combined_pass = plastic_pass and bgo_pass
            topology_pass = False
            topology_class = "not_evaluated"
            if combined_pass and in_window(measured_total, WINDOWS["broad_480_550"]):
                topology_pass, topology_class = topology_keep(measured_hits, step05, disk)
                topology_classes[topology_class] += 1
            flags = {
                "pre_veto": True,
                "plastic_positron_veto": plastic_pass,
                "bgo_active_scintillator_veto": bgo_pass,
                "combined_active_veto": combined_pass,
                "compton_trajectory_veto": combined_pass and topology_pass,
            }
            for stage, passes in flags.items():
                if not passes:
                    continue
                for window_id, bounds in WINDOWS.items():
                    if in_window(measured_total, bounds):
                        key = f"{stage}|{window_id}"
                        selected[key] += 1
                        if source_za is not None:
                            selected_by_za[f"{stage}|{window_id}|{source_za}"] += 1
        current_id = None
        current_za = None
        production_xyz = None
        init_count = 0
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0

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
        raise RuntimeError(f"{job['job_id']}: {generated} events != {job['events']}")
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve():
        raise RuntimeError(f"{job['job_id']}: geometry header mismatch")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: seed header mismatch")
    result = {
        "lineage_policy": "exact_position_stride5_kdtree_v1",
        "scan_index": job["scan_index"],
        "stream": job["stream"],
        "family": job["family"],
        "batch_id": job["batch_id"],
        "job_id": job["job_id"],
        "events": generated,
        "sim_bytes": job["sim_bytes"],
        "weight_cps": job["weight_cps"],
        "selected": dict(selected),
        "selected_by_za": dict(selected_by_za),
        "occupancy_events": occupancy_events,
        "occupancy_by_za": {str(key): value for key, value in occupancy_by_za.items()},
        "tes_positive_events": tes_positive_events,
        "active_only_events": active_only_events,
        "pixel_hits": pixel_hits,
        "init_source_za_mismatch_events": init_source_za_mismatch_events,
        "max_position_match_distance_cm": max_position_match_distance_cm,
        "topology_classes": dict(topology_classes),
    }
    cache_path = Path(cache_dir) / f"job_{job['scan_index']:03d}.json"
    cache_path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    return result


def aggregate_results(
    jobs: list[dict[str, Any]], results: dict[int, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    aggregate: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0}
    )
    occupancy: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0, "tes": 0.0, "active": 0.0}
    )
    delayed_za_rate: dict[tuple[str, str, str, int], float] = defaultdict(float)
    delayed_za_occ: dict[tuple[str, int], float] = defaultdict(float)
    job_rows = []
    for job in jobs:
        row = results[job["scan_index"]]
        weight = float(row["weight_cps"])
        for key, count_value in row["selected"].items():
            stage, window_id = key.split("|")
            count = int(count_value)
            cell = aggregate[(row["stream"], row["family"], stage, window_id)]
            cell["events"] += count
            cell["rate"] += count * weight
            cell["variance"] += count * weight * weight
        for key, count_value in row["selected_by_za"].items():
            stage, window_id, za_text = key.split("|")
            delayed_za_rate[(row["family"], stage, window_id, int(za_text))] += int(count_value) * weight
        occ = occupancy[(row["stream"], row["family"])]
        occ["events"] += int(row["occupancy_events"])
        occ["rate"] += int(row["occupancy_events"]) * weight
        occ["variance"] += int(row["occupancy_events"]) * weight * weight
        occ["tes"] += int(row["tes_positive_events"])
        occ["active"] += int(row["active_only_events"])
        if row["stream"] == "delayed":
            for za_text, count in row["occupancy_by_za"].items():
                delayed_za_occ[(row["family"], int(za_text))] += int(count) * weight
        job_rows.append(
            {
                "stream": row["stream"],
                "family": row["family"],
                "batch_id": row["batch_id"],
                "job_id": row["job_id"],
                "events": row["events"],
                "sim_bytes": row["sim_bytes"],
                "event_weight_cps": weight,
                "detector_occupancy_events": row["occupancy_events"],
                "tes_positive_events": row["tes_positive_events"],
                "active_only_events": row["active_only_events"],
                "pixel_hits": row["pixel_hits"],
                "init_source_za_mismatch_events": row["init_source_za_mismatch_events"],
                "max_position_match_distance_cm": row["max_position_match_distance_cm"],
                "topology_classes_json": json.dumps(row["topology_classes"], sort_keys=True, separators=(",", ":")),
            }
        )
    cutflow = []
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            for stage in STAGES:
                for window_id, bounds in WINDOWS.items():
                    value = aggregate[(stream, family, stage, window_id)]
                    cutflow.append(
                        {
                            "geometry": "SG3B",
                            "stream": stream,
                            "family": family,
                            "response_state": "measured",
                            "stage": stage,
                            "window_id": window_id,
                            "energy_lo_keV": bounds[0],
                            "energy_hi_keV": bounds[1],
                            "selected_events": int(value["events"]),
                            "weighted_rate_cps": value["rate"],
                            "weighted_mc_sigma_cps": math.sqrt(value["variance"]),
                        }
                    )
    occupancy_rows = []
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            value = occupancy[(stream, family)]
            occupancy_rows.append(
                {
                    "geometry": "SG3B",
                    "stream": stream,
                    "family": family,
                    "detector_occupancy_events": int(value["events"]),
                    "tes_positive_events": int(value["tes"]),
                    "active_only_events": int(value["active"]),
                    "weighted_occupancy_cps": value["rate"],
                    "weighted_mc_sigma_cps": math.sqrt(value["variance"]),
                }
            )
    extras = {
        "aggregate": aggregate,
        "occupancy": occupancy,
        "delayed_za_rate": delayed_za_rate,
        "delayed_za_occ": delayed_za_occ,
        "job_rows": job_rows,
    }
    return cutflow, occupancy_rows, extras


def advance_linear_inventory(number: float, p_left: float, p_right: float, lam: float, dt_s: float) -> float:
    x = lam * dt_s
    if x < 1.0e-5:
        phi1 = 1.0 - x / 2.0 + x * x / 6.0 - x**3 / 24.0 + x**4 / 120.0
        phi2 = 0.5 - x / 6.0 + x * x / 24.0 - x**3 / 120.0 + x**4 / 720.0
    else:
        phi1 = -math.expm1(-x) / x
        phi2 = (1.0 - phi1) / x
    return number * math.exp(-x) + dt_s * (p_left * phi1 + (p_right - p_left) * phi2)


def inventory_authority(manifest: dict[str, Any]) -> dict[tuple[str, int], dict[str, float]]:
    inventory: dict[tuple[str, int], dict[str, float]] = {}
    for cell in manifest["source_cells"]:
        family = cell["family"]
        for state in cell["included_states"]:
            activity = float(state["day15_activity_Bq"])
            if activity <= 0.0:
                continue
            half_life = float(state["half_life_s"])
            key = (family, int(state["ZA"]))
            target = inventory.setdefault(
                key,
                {"day15_activity_Bq": 0.0, "production_rate_s-1": 0.0, "half_life_s": half_life},
            )
            if not math.isclose(target["half_life_s"], half_life, rel_tol=1e-12):
                raise RuntimeError(f"half-life disagreement for {key}")
            target["day15_activity_Bq"] += activity
            target["production_rate_s-1"] += float(state["production_rate_s-1"])
    return inventory


def activity_curves(
    inventory: dict[tuple[str, int], dict[str, float]],
    scales: list[dict[str, str]],
) -> dict[tuple[str, int], list[float]]:
    curves = {}
    for key, item in inventory.items():
        family, _ = key
        lam = math.log(2.0) / item["half_life_s"]
        number = 0.0
        curve = [0.0]
        for index in range(1, len(scales)):
            dt_s = (float(scales[index]["day_mid"]) - float(scales[index - 1]["day_mid"])) * SECONDS_PER_DAY
            p_left = item["production_rate_s-1"] * float(scales[index - 1][f"scale_{family}_to_parma_reference"])
            p_right = item["production_rate_s-1"] * float(scales[index][f"scale_{family}_to_parma_reference"])
            number = advance_linear_inventory(number, p_left, p_right, lam, dt_s)
            curve.append(lam * number)
        curves[key] = curve
    return curves


def signal_proxy_by_stage(config: dict[str, Any]) -> dict[str, float]:
    rows = read_csv(Path(config["conditional_signal_proxy"]["authority"]))
    selected = {
        row["stage"]: float(row["weighted_value"])
        for row in rows
        if row["geometry"] == "SE3"
        and row["stream"] == "signal"
        and row["response_state"] == "measured"
        and row["window_id"] == "w2_510p58_511p42"
    }
    required = {"pre_veto", "active_veto50", "side_compton_fov_pass"}
    if not required <= set(selected):
        raise RuntimeError("SE3 full-envelope conditional signal proxy is incomplete")
    if not math.isclose(selected["pre_veto"], selected["active_veto50"], rel_tol=0.0, abs_tol=1e-15):
        raise RuntimeError("signal proxy has active-veto loss; separate veto proxy cannot be inferred")
    static = load_json(Path(config["conditional_signal_proxy"]["static_no_intersection_audit"]))
    if int(static["focused_signal"]["rays"]) != 37_194 or int(static["focused_signal"]["intersections"]) != 0:
        raise RuntimeError("SG3B static focused-ray no-intersection audit differs")
    return {
        "pre_veto": selected["pre_veto"],
        "plastic_positron_veto": selected["active_veto50"],
        "bgo_active_scintillator_veto": selected["active_veto50"],
        "combined_active_veto": selected["active_veto50"],
        "compton_trajectory_veto": selected["side_compton_fov_pass"],
    }


def asimov_required_signal(background: float, target_z: float) -> float:
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)

    def z(signal: float) -> float:
        return math.sqrt(2.0 * ((signal + background) * math.log1p(signal / background) - signal))

    while z(high) < target_z:
        high *= 2.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        if z(mid) < target_z:
            low = mid
        else:
            high = mid
    return high


def build_mission(
    config: dict[str, Any], extras: dict[str, Any], activation: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    mission = config["mission"]
    scales = sorted(read_csv(ROOT / mission["family_scales"]), key=lambda row: int(row["time_bin_id"]))
    atmosphere = sorted(read_csv(ROOT / mission["atmospheric_transmission"]), key=lambda row: int(row["time_bin_id"]))
    if len(scales) != 81 or len(atmosphere) != 81:
        raise RuntimeError("mission time authority is not 81 nodes")
    for left, right in zip(scales, atmosphere):
        if int(left["time_bin_id"]) != int(right["time_bin_id"]) or not math.isclose(
            float(left["day_mid"]), float(right["day_mid"]), abs_tol=1e-12
        ):
            raise RuntimeError("family-scale and atmosphere time axes differ")
    inventory = inventory_authority(activation)
    curves = activity_curves(inventory, scales)
    delayed_za_rate = extras["delayed_za_rate"]
    delayed_za_occ = extras["delayed_za_occ"]
    observed_za = {(family, za) for family, _, _, za in delayed_za_rate} | set(delayed_za_occ)
    missing = observed_za - set(inventory)
    if missing:
        raise RuntimeError(f"delayed transport ZA absent from activation inventory: {sorted(missing)}")
    aggregate = extras["aggregate"]
    occupancy = extras["occupancy"]
    signal_aeff = signal_proxy_by_stage(config)
    tau = float(mission["coincidence_window_s"])
    slant = 1.0 / math.sin(math.radians(float(mission["source_elevation_deg"])))
    timeline: list[dict[str, Any]] = []
    cumulative = {stage: {"B": 0.0, "K": 0.0} for stage in STAGES}
    previous: dict[str, dict[str, float]] | None = None
    for index, (scale_row, atm_row) in enumerate(zip(scales, atmosphere)):
        prompt_occ = math.fsum(
            occupancy[("prompt", family)]["rate"] * float(scale_row[f"scale_{family}_to_parma_reference"])
            for family in FAMILIES
        )
        delayed_occ = 0.0
        for key, day15_rate in delayed_za_occ.items():
            ref = inventory[key]["day15_activity_Bq"]
            delayed_occ += day15_rate * curves[key][index] / ref
        live = math.exp(-(prompt_occ + delayed_occ) * tau)
        transmission = float(atm_row["T_atm_511"]) ** slant
        rates: dict[str, dict[str, float]] = {}
        for stage in STAGES:
            prompt_rate = math.fsum(
                aggregate[("prompt", family, stage, "w2_510p58_511p42")]["rate"]
                * float(scale_row[f"scale_{family}_to_parma_reference"])
                for family in FAMILIES
            )
            delayed_rate = 0.0
            for (family, key_stage, window_id, za), day15_rate in delayed_za_rate.items():
                if key_stage != stage or window_id != "w2_510p58_511p42":
                    continue
                key = (family, za)
                delayed_rate += day15_rate * curves[key][index] / inventory[key]["day15_activity_Bq"]
            rates[stage] = {
                "prompt": prompt_rate,
                "delayed": delayed_rate,
                "background_live": (prompt_rate + delayed_rate) * live,
                "signal_kernel_live_cm2": signal_aeff[stage] * transmission * live,
            }
        day = float(scale_row["day_mid"])
        dt_s = 0.0 if index == 0 else (day - float(scales[index - 1]["day_mid"])) * SECONDS_PER_DAY
        if previous is not None:
            for stage in STAGES:
                cumulative[stage]["B"] += 0.5 * (
                    previous[stage]["background_live"] + rates[stage]["background_live"]
                ) * dt_s
                cumulative[stage]["K"] += 0.5 * (
                    previous[stage]["signal_kernel_live_cm2"] + rates[stage]["signal_kernel_live_cm2"]
                ) * dt_s
        for stage in STAGES:
            background_counts = cumulative[stage]["B"]
            kernel = cumulative[stage]["K"]
            row = {
                "geometry": "SG3B",
                "time_bin_id": int(scale_row["time_bin_id"]),
                "day_mid": day,
                "stage": stage,
                "prompt_occupancy_cps": prompt_occ,
                "delayed_occupancy_cps": delayed_occ,
                "total_occupancy_cps": prompt_occ + delayed_occ,
                "poisson_accidental_live_factor": live,
                "T_atm_511_vertical": float(atm_row["T_atm_511"]),
                "T_atm_511_slant45": transmission,
                "prompt_W2_cps_noacc": rates[stage]["prompt"],
                "delayed_W2_cps_noacc": rates[stage]["delayed"],
                "background_W2_cps_live": rates[stage]["background_live"],
                "conditional_signal_proxy_Aeff_cm2": signal_aeff[stage],
                "conditional_signal_kernel_live_cm2": rates[stage]["signal_kernel_live_cm2"],
                "cumulative_background_counts": background_counts,
                "cumulative_signal_counts_per_unit_flux": kernel,
                "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(background_counts) / kernel if kernel > 0 else "",
                "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(background_counts) / kernel if kernel > 0 else "",
                "Fmin_3sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background_counts, 3.0) / kernel if kernel > 0 else "",
                "Fmin_5sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background_counts, 5.0) / kernel if kernel > 0 else "",
            }
            timeline.append(row)
        previous = rates
    day15_index = next(i for i, row in enumerate(scales) if math.isclose(float(row["day_mid"]), DAY15))
    final_rows = [row for row in timeline if row["time_bin_id"] == 80]
    final_by_stage = {row["stage"]: row for row in final_rows}
    day15_rows = [row for row in timeline if row["time_bin_id"] == day15_index]
    day15_final = next(row for row in day15_rows if row["stage"] == "compton_trajectory_veto")
    local_time_rows = []
    local_b = float(day15_final["background_W2_cps_live"])
    local_k = float(day15_final["conditional_signal_kernel_live_cm2"])
    for flux in (1e-4, 7.5e-5, 5e-5, 3e-5, 1e-5):
        for sigma in (3.0, 5.0):
            dt_gaussian = sigma * sigma * local_b / ((flux * local_k) ** 2)
            local_time_rows.append(
                {
                    "reference_node_day": DAY15,
                    "stage": "compton_trajectory_veto",
                    "flux_ph_cm2_s": flux,
                    "target_sigma": sigma,
                    "minimum_integration_s_gaussian_local_stationary": dt_gaussian,
                    "minimum_integration_hours_gaussian_local_stationary": dt_gaussian / 3600.0,
                    "minimum_integration_days_gaussian_local_stationary": dt_gaussian / SECONDS_PER_DAY,
                    "day15_background_cps_live": local_b,
                    "day15_signal_kernel_live_cm2": local_k,
                }
            )
    summary = {
        "conditional_signal_proxy_Aeff_cm2_by_stage": signal_aeff,
        "mission_endpoint_by_stage": final_by_stage,
        "day15_final_stage": day15_final,
        "authority_boundary": "CONDITIONAL_FLUX_REACH_ONLY__FRESH_SG3B_FULL_ENVELOPE_SIGNAL_TRANSPORT_REQUIRED",
    }
    return timeline, local_time_rows, summary, day15_rows


def poisson_common_axis_validation(day15_rows: list[dict[str, Any]], seed: int = 20260817) -> dict[str, Any]:
    final = next(row for row in day15_rows if row["stage"] == "compton_trajectory_veto")
    components = {
        "prompt": float(final["prompt_occupancy_cps"]),
        "delayed": float(final["delayed_occupancy_cps"]),
    }
    total = math.fsum(components.values())
    if total <= 0.0:
        raise RuntimeError("zero day15 occupancy cannot validate common time axis")
    duration = 1_000_000.0 / total
    rng = np.random.default_rng(seed)
    streams = []
    realized = {}
    for name, rate in components.items():
        count = int(rng.poisson(rate * duration))
        realized[name] = count
        streams.append(np.sort(rng.uniform(0.0, duration, count)))
    merged = np.sort(np.concatenate(streams))
    tau = 1e-6
    gaps = np.diff(merged)
    observed_live = (1.0 + float(np.count_nonzero(gaps > tau))) / len(merged)
    analytic_live = math.exp(-total * tau)
    groups = 1 + int(np.count_nonzero(gaps > tau))
    return {
        "status": "PASS__SUPERPOSED_POISSON_COMMON_AXIS_VALIDATION",
        "seed": seed,
        "reference_node_day": DAY15,
        "duration_s": duration,
        "component_rates_cps": components,
        "realized_component_events": realized,
        "realized_total_events": len(merged),
        "coincidence_window_s": tau,
        "merged_adjacent_time_groups": groups,
        "analytic_one_window_live_factor": analytic_live,
        "observed_one_window_live_fraction": observed_live,
        "absolute_difference": abs(observed_live - analytic_live),
        "model": "independent Poisson streams sampled on one axis, merged and sorted; adjacent gaps <= tau form a coincidence group",
    }


def build_report(summary: dict[str, Any], audit: dict[str, Any]) -> str:
    endpoint = summary["mission"]["mission_endpoint_by_stage"]
    final = endpoint["compton_trajectory_veto"]
    day15 = summary["mission"]["day15_final_stage"]
    lines = [
        "# SG3B M05 common-time response", "",
        f"Status: `{summary['status']}`", "",
        "## 归一化与选择", "",
        f"- prompt 使用 22 个 INSTANT receipt、{audit['prompt_instant_events_analyzed']:,} primaries；每族事件权重为 `1/sum(TT_family)`。",
        f"- delayed 使用 canonical v2 的 33 个 receipt、{audit['delayed_triggers_analyzed']:,} triggers；每族事件权重为 `A15_family/1,000,000`。",
        "- 先分别施加 10 mm plastic 正电子/带电粒子 veto 与三块 BGO 主动闪烁体 veto，再取二者交集，最后执行 retained Step05 Compton/FoV。两类主动层均用严格 `<50 keV` 离线阈值。",
        "- prompt 与 delayed 的全带探测器 occupancy 按独立泊松流叠加到同一个 1 microsecond 时间轴；弱源 live factor 为 `exp[-tau(R_prompt+R_delayed)]`。",
        "- repaired broadband gamma 已含湮没隆起；PARMA mono-511 sidecar 未加入任何本底和。", "",
        "## 20-day 条件通量阈值", "",
        "| stage | B20 counts | proxy Aeff (cm2) | F3 Gaussian | F3 Poisson-Asimov | F5 Poisson-Asimov |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for stage in STAGES:
        row = endpoint[stage]
        lines.append(
            f"| {stage} | {float(row['cumulative_background_counts']):.7g} | "
            f"{float(row['conditional_signal_proxy_Aeff_cm2']):.7g} | "
            f"{float(row['Fmin_3sigma_gaussian_ph_cm2_s']):.7g} | "
            f"{float(row['Fmin_3sigma_poisson_asimov_ph_cm2_s']):.7g} | "
            f"{float(row['Fmin_5sigma_poisson_asimov_ph_cm2_s']):.7g} |"
        )
    lines.extend(
        [
            "", "## 时间解析形式", "",
            "对任意累计时刻 `T`，本包输出 `K(T)=integral[Aeff(t) T_atm(t) L(t) dt]` 与 `B(T)=integral[B_rate(t)L(t)dt]`。M05 高计数近似为 `F_q(T)=q sqrt(B(T))/K(T)`；同时给出由 `Z_A=sqrt(2[(S+B)ln(1+S/B)-S])` 反解的 Poisson-Asimov 阈值。局部平稳近似的时间分辨式为 `Delta t_min=q^2 B_rate/(F^2 K_rate^2)`。",
            f"第 15 天 final stage 的 live 后本底率为 `{float(day15['background_W2_cps_live']):.7g} cps`，条件信号 kernel 为 `{float(day15['conditional_signal_kernel_live_cm2']):.7g} cm2`。",
            f"20 天 final stage 条件结果：Gaussian F3=`{float(final['Fmin_3sigma_gaussian_ph_cm2_s']):.7g}`，Poisson-Asimov F3=`{float(final['Fmin_3sigma_poisson_asimov_ph_cm2_s']):.7g}` ph cm^-2 s^-1。", "",
            "## Authority boundary", "",
            "这些通量阈值不是 SG3B 最终灵敏度 authority。分母使用 SE3 的 37,194-ray full-envelope W2 selected Aeff 作为条件代理；SG3B 静态审计只证明新增 Bi 不与 primary rays 相交，不能替代 SG3B 自身的 full-envelope 信号输运及共同响应。prompt/delayed 本底、veto cutflow、归一化和 common-time occupancy 则来自 SG3B 自身 accepted transports。", "",
        ]
    )
    return "\n".join(lines)


def run(output: Path, workers: int) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    started = time.monotonic()
    try:
        config = load_json(CONFIG)
        jobs, audit = prepare_jobs(config)
        threshold = float(config["active_veto"]["offline_threshold_keV"])
        results: dict[int, dict[str, Any]] = {}
        cache = Path("/tmp/sg3b_m05_common_time_semantic_cache_exactpos_v2")
        cache.mkdir(parents=True, exist_ok=True)
        for job in jobs:
            cache_path = cache / f"job_{job['scan_index']:03d}.json"
            if not cache_path.is_file():
                continue
            cached = load_json(cache_path)
            if not (
                cached.get("lineage_policy") == "exact_position_stride5_kdtree_v1"
                and cached.get("job_id") == job["job_id"]
                and cached.get("batch_id") == job["batch_id"]
                and int(cached.get("events", -1)) == int(job["events"])
            ):
                raise RuntimeError(f"semantic cache identity mismatch: {cache_path}")
            results[job["scan_index"]] = cached
        if results:
            print(
                f"reused {len(results)}/{len(jobs)} exact-position semantic cache rows; "
                f"{sum(row['events'] for row in results.values()):,} events",
                flush=True,
            )
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(scan_job, job, threshold, str(cache)): job
                for job in jobs
                if job["scan_index"] not in results
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results[result["scan_index"]] = result
                print(
                    f"scanned {len(results)}/{len(jobs)} jobs; "
                    f"{sum(row['events'] for row in results.values()):,} events; "
                    f"{time.monotonic()-started:.1f}s",
                    flush=True,
                )
        cutflow, occupancy_rows, extras = aggregate_results(jobs, results)
        activation = load_json(Path(config["activation_manifest"]))
        timeline, local_time, mission_summary, day15_rows = build_mission(config, extras, activation)
        poisson_validation = poisson_common_axis_validation(day15_rows)
        write_csv(work / "input_job_semantic_scan.csv", extras["job_rows"])
        write_csv(work / "sg3b_measured_cutflow.csv", cutflow)
        write_csv(work / "sg3b_fullband_occupancy.csv", occupancy_rows)
        write_csv(work / "mission_time_resolved_flux_threshold.csv", timeline)
        write_csv(work / "day15_local_time_resolution.csv", local_time)
        (work / "input_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (work / "poisson_common_axis_validation.json").write_text(
            json.dumps(poisson_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        summary = {
            "schema_version": 1,
            "status": "PASS__SG3B_OWN_BACKGROUND_COMMON_TIME_RESPONSE__CONDITIONAL_SIGNAL_PROXY_FLUX_REACH",
            "candidate": "SG3B",
            "transport_semantic_scan": {
                "jobs": len(jobs),
                "prompt_instant_jobs": sum(job["stream"] == "prompt" for job in jobs),
                "delayed_jobs": sum(job["stream"] == "delayed" for job in jobs),
                "events": sum(int(job["events"]) for job in jobs),
                "compressed_SIM_GiB": sum(int(job["sim_bytes"]) for job in jobs) / 2**30,
                "large_SIM_hashes_computed": 0,
                "workers": workers,
                "elapsed_s": time.monotonic() - started,
            },
            "normalization": {
                "prompt": "selected/sum(TT) within SG3B x INSTANT x family",
                "delayed_day15": "selected * transported_ground_activity_Bq / 1,000,000 within family",
                "mission_delayed": "isotope-resolved exact decay convolution driven by 81-node family production scales",
            },
            "response": {
                "pixel_FWHM_keV": 0.42,
                "post_noise_pixel_threshold_keV": 0.3,
                "plastic_positron_veto_threshold_keV": threshold,
                "bgo_active_scintillator_veto_threshold_keV": threshold,
                "threshold_comparison": "strict less-than passes; equality vetoes",
                "compton_fov": relative(STEP05),
            },
            "common_time_axis": poisson_validation,
            "mission": mission_summary,
            "explicit_exclusions": {
                "superseded_sg3b_m05_delayed_1m_v1_receipts": True,
                "parma_mono511_added_to_repaired_broadband": False,
                "fresh_SG3B_37194_ray_signal_transport_available": False,
            },
            "authority_boundary": mission_summary["authority_boundary"],
        }
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (work / "REPORT.md").write_text(build_report(summary, audit), encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "status": summary["status"],
            "analysis_code": relative(HERE),
            "config": relative(CONFIG),
            "reused_code": [relative(PROMPT_ADAPTER), relative(CORRECTED_CORE), relative(STEP05)],
            "large_SIM_hash_policy": "no large-payload hashes; streamed once to gzip EOF for semantic detector analysis",
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in sorted(work.rglob("*"))
                if path.is_file()
            ],
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(work, output)
        shutil.rmtree(cache, ignore_errors=True)
        print(f"{summary['status']}: {output}", flush=True)
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    run(output.resolve(), args.workers)


if __name__ == "__main__":
    main()
