#!/usr/bin/env python3
"""Build the 15-cell corrected delayed compact catalog and screening tables.

The reader joins the independently revalidated p/n/alpha recovery with the
remaining-nine terminal transport summary.  It reuses the prompt compact
catalog, keyed TES response, exact active-veto lists, and retained Step05 code.
Each SIM is decompressed once; geometry/seed/epsilon/DECA and detector hits are
collected in that same pass.  Large SIM hashes are not recomputed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import pickle
import shutil
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import check_inputs
import run_prompt_analysis as prompt


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
CONFIG = PACKAGE / "analysis_inputs.json"
OUTPUT = PACKAGE / "outputs/03_delayed"
PHASE_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/state_aware_exactpos_v1"
)
RECOVERY_ROOT = PHASE_ROOT / "spectrum_epsilon_formal_partial_recovery0002"
RECOVERY_PLAN = RECOVERY_ROOT / "formal_partial_jobs.json"
RECOVERY_AUTHORITY = RECOVERY_ROOT / "revalidation0001/formal_partial_revalidation.json"
REMAINING_ROOT = PHASE_ROOT / "m05_corrected_delayed_remaining9_v1"
REMAINING_SUMMARY = REMAINING_ROOT / "transport_summary.json"
ACTIVATION_SOURCE_INDEX = PACKAGE / "outputs/02_activation/delayed_source_index.csv"

GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = prompt.FAMILY_ORDER
TRIGGERS = 250_000
PASS_RECOVERY = "PASS__REVALIDATION0001_SIX_CELL_DELAYED_PARTIAL_SCREENING_COMPATIBLE"
PASS_REMAINING = "PASS__M05_CORRECTED_DELAYED_REMAINING9_TRANSPORT_PROCESS_COMPLETE__SEMANTIC_SCAN_DEFERRED"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def read_source_index() -> dict[tuple[str, str], dict[str, str]]:
    with ACTIVATION_SOURCE_INDEX.open("r", encoding="utf-8", newline="") as handle:
        return {
            (row["geometry"], row["incident_family"]): row
            for row in csv.DictReader(handle)
        }


def selected_jobs(config: dict[str, Any]) -> list[dict[str, Any]]:
    source_index = read_source_index()
    recovery_plan = load_json(RECOVERY_PLAN)
    recovery_by_id = {row["job_id"]: row for row in recovery_plan["jobs"]}
    recovery = load_json(RECOVERY_AUTHORITY)
    if recovery.get("status") != PASS_RECOVERY:
        raise RuntimeError(f"recovery0002 is not eligible: {recovery.get('status')}")
    remaining = load_json(REMAINING_SUMMARY)
    if remaining.get("status") != PASS_REMAINING:
        raise RuntimeError(f"remaining-nine transport is not process-complete: {remaining.get('status')}")

    rows: list[dict[str, Any]] = []
    for authority in recovery["jobs"]:
        plan = recovery_by_id[authority["job_id"]]
        rows.append(
            {
                "authority_group": "recovery0002_revalidation0001",
                "authority_path": relative(RECOVERY_AUTHORITY),
                "geometry": plan["geometry"],
                "family": plan["family"],
                "job_id": plan["job_id"],
                "seed": int(plan["seed"]),
                "events": TRIGGERS,
                "sim_path": str((ROOT / authority["valid_artifact_path"]).resolve()),
                "expected_geometry": str(Path(plan["expected_geometry"]).resolve()),
                "prepared_source": plan["prepared_source"],
                "source": plan["source"],
                "activity_Bq": float(plan["sum_flux_closure"]["original_50000_sum_flux_Bq"]),
            }
        )
    for receipt in remaining["jobs"]:
        if receipt.get("status") != "PASS":
            raise RuntimeError(f"remaining-nine receipt is not PASS: {receipt.get('job', {}).get('job_id')}")
        plan = receipt["job"]
        rows.append(
            {
                "authority_group": "remaining9_process_complete",
                "authority_path": relative(REMAINING_SUMMARY),
                "geometry": plan["geometry"],
                "family": plan["family"],
                "job_id": plan["job_id"],
                "seed": int(plan["seed"]),
                "events": TRIGGERS,
                "sim_path": str((ROOT / receipt["sim_path"]).resolve()),
                "expected_geometry": str(Path(plan["expected_geometry"]).resolve()),
                "prepared_source": plan["prepared_source"],
                "source": plan["source"],
                "activity_Bq": float(plan["sum_flux_closure"]["original_50000_sum_flux_Bq"]),
            }
        )

    expected = {(geometry, family) for geometry in GEOMETRIES for family in FAMILIES}
    expected.remove(("Mass_model_511", "muplus"))
    observed = {(row["geometry"], row["family"]) for row in rows}
    if observed != expected or len(rows) != 15:
        raise RuntimeError(f"delayed cell closure differs: missing={sorted(expected-observed)} extra={sorted(observed-expected)}")
    for index, row in enumerate(sorted(rows, key=lambda value: (GEOMETRIES.index(value["geometry"]), FAMILIES.index(value["family"])))):
        cell = source_index[(row["geometry"], row["family"])]
        source_manifest = load_json(ROOT / cell["source_manifest_path"])
        if not math.isclose(
            row["activity_Bq"], float(source_manifest["included_ground_activity_Bq"]), rel_tol=1.0e-12
        ):
            raise RuntimeError(f"activity/source-manifest mismatch: {row['geometry']}/{row['family']}")
        active = list(config["geometries"][row["geometry"]]["active_veto_volumes"])
        row.update(
            {
                "scan_index": index,
                "input_id": row["authority_group"],
                "batch_id": row["authority_group"],
                "mode": "delayed",
                "shield_volumes": [name for name in active if "Plastic" not in name],
                "plastic_volumes": [name for name in active if "Plastic" in name],
                "sampled_positions_path": cell["sampled_positions_path"],
                "source_manifest_path": cell["source_manifest_path"],
                "known_holdout_activity_Bq": float(cell["known_holdout_activity_Bq"]),
                "unknown_activity_state_count": int(cell["unknown_activity_state_count"]),
                "event_weight_cps": row["activity_Bq"] / TRIGGERS,
                "equivalent_time_s": TRIGGERS / row["activity_Bq"],
            }
        )
    return sorted(rows, key=lambda value: value["scan_index"])


def position_locator(path: Path) -> dict[str, Any]:
    """Build the retained M04 coordinate-authority mapping for one source cell."""
    import numpy as np
    from scipy.spatial import cKDTree

    unique: dict[tuple[float, float, float], tuple[str, int, float]] = {}
    full_mix: Counter[tuple[str, int]] = Counter()
    selected_mix: Counter[tuple[str, int]] = Counter()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            position = (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            value = (row["volume"], int(row["ZA"]), float(row["excitation_keV"]))
            full_mix[(value[0], value[1])] += 1
            if int(row["sample_index"]) % 5:
                continue
            selected_mix[(value[0], value[1])] += 1
            old = unique.setdefault(position, value)
            if old != value:
                raise RuntimeError(f"ambiguous source position in {path}: {position}")
    coordinates = np.asarray(list(unique), dtype=np.float64)
    return {
        "tree": cKDTree(coordinates),
        "metadata": list(unique.values()),
        "cache": {},
        "full_mix": full_mix,
        "selected_mix": selected_mix,
    }


def locate_source(locator: dict[str, Any], position: tuple[float, float, float]) -> tuple[tuple[str, int, float], float]:
    """Map a five-decimal IA INIT position to its six-decimal source support."""
    import numpy as np

    observed_key = tuple(f"{axis:.5f}" for axis in position)
    cached = locator["cache"].get(observed_key)
    if cached is not None:
        return cached
    count = len(locator["metadata"])
    k = min(8, count)
    nearest = second = math.inf
    local = -1
    chosen: tuple[str, int, float] | None = None
    while True:
        distances, neighbors = locator["tree"].query(
            np.asarray(position, dtype=np.float64), k=k, p=np.inf, workers=1
        )
        distance_values = np.atleast_1d(distances)
        neighbor_values = np.atleast_1d(neighbors)
        local = int(neighbor_values[0])
        nearest = float(distance_values[0])
        chosen = locator["metadata"][local]
        for distance, neighbor in zip(distance_values[1:], neighbor_values[1:]):
            if locator["metadata"][int(neighbor)] != chosen:
                second = float(distance)
                break
        if math.isfinite(second) or k == count:
            break
        k = min(2 * k, count)
    accepted = (
        nearest <= 1.0e-3
        and second - nearest >= 1.102e-5
        and second >= 2.0 * max(nearest, 1.0e-30)
    )
    if not accepted:
        raise RuntimeError(
            f"source-position lineage is not uniquely resolved: nearest={nearest:.9g} cm, "
            f"second={second:.9g} cm"
        )
    result = (chosen, nearest)
    locator["cache"][observed_key] = result
    return result


def scan_job(job: dict[str, Any], cache_dir: str) -> dict[str, Any]:
    parser = prompt.old_parser()
    locator = position_locator(ROOT / job["sampled_positions_path"])
    catalog = parser.empty_catalog()
    extras: dict[str, list[Any]] = {
        "input_id": [], "batch_id": [], "job_name": [], "seed": [],
        "plastic_total_keV": [], "has_pair_ia": [], "has_annihilation_ia": [],
        "sim_initial_ZA": [], "source_parent_ZA": [], "source_volume": [], "source_excitation_keV": [],
        "parent_match_distance_cm": [],
        "production_x_cm": [], "production_y_cm": [], "production_z_cm": [],
        "has_deca": [],
    }
    shield = set(job["shield_volumes"])
    plastic = set(job["plastic_volumes"])
    current_id: int | None = None
    pixels: dict[str, dict[str, float | int]] = {}
    active_total = plastic_total = 0.0
    sim_initial_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    has_deca = has_pair = has_annihilation = False
    generated = active_only = total_init = deca_events = 0
    exact_print_matches = 0
    nearest_distance_max_cm = 0.0
    realized_mix: Counter[tuple[str, int]] = Counter()
    header_geometry = ""
    header_seed: int | None = None
    spectral: list[str] = []

    def flush() -> None:
        nonlocal current_id, pixels, active_total, plastic_total, sim_initial_za, production_xyz
        nonlocal init_count, has_deca, has_pair, has_annihilation, active_only, deca_events
        nonlocal exact_print_matches, nearest_distance_max_cm
        if current_id is None:
            return
        if init_count != 1 or sim_initial_za is None or production_xyz is None:
            raise RuntimeError(f"{job['job_id']} event {current_id}: IA INIT count={init_count}")
        source, nearest_distance = locate_source(locator, production_xyz)
        nearest_distance_max_cm = max(nearest_distance_max_cm, nearest_distance)
        exact_print_matches += int(nearest_distance <= 5.51e-6)
        realized_mix[(source[0], source[1])] += 1
        if has_deca:
            deca_events += 1
        if pixels:
            before = len(catalog["stream"])
            parser.append_event(
                catalog, "delayed", job["family"], job["sim_path"], current_id,
                job["event_weight_cps"], active_total, pixels,
            )
            if len(catalog["stream"]) == before + 1:
                extras["input_id"].append(job["input_id"])
                extras["batch_id"].append(job["batch_id"])
                extras["job_name"].append(job["job_id"])
                extras["seed"].append(job["seed"])
                extras["plastic_total_keV"].append(plastic_total)
                extras["has_pair_ia"].append(has_pair)
                extras["has_annihilation_ia"].append(has_annihilation)
                extras["sim_initial_ZA"].append(sim_initial_za)
                extras["source_parent_ZA"].append(source[1])
                extras["source_volume"].append(source[0])
                extras["source_excitation_keV"].append(source[2])
                extras["parent_match_distance_cm"].append(nearest_distance)
                extras["production_x_cm"].append(production_xyz[0])
                extras["production_y_cm"].append(production_xyz[1])
                extras["production_z_cm"].append(production_xyz[2])
                extras["has_deca"].append(has_deca)
        elif active_total > 0.0 or plastic_total > 0.0:
            active_only += 1
        current_id = None
        pixels = {}
        active_total = plastic_total = 0.0
        sim_initial_za = None
        production_xyz = None
        init_count = 0
        has_deca = has_pair = has_annihilation = False

    with gzip.open(job["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            elif line.startswith("SpectralType "):
                spectral.append(line)
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise RuntimeError(f"{job['job_id']}: ID before prior event boundary")
                current_id = int(match.group(1))
                generated += 1
                if current_id != generated:
                    raise RuntimeError(
                        f"{job['job_id']}: non-contiguous local ID {current_id} at event {generated}"
                    )
                continue
            if line.startswith("IA INIT"):
                fields = [value.strip() for value in line.split(";")]
                if len(fields) < 16:
                    raise RuntimeError(f"malformed IA INIT: {job['job_id']}")
                init_count += 1
                total_init += 1
                production_xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
                sim_initial_za = int(fields[15])
                continue
            if line.startswith("IA DECA"):
                has_deca = True
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
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(pixel_match.group("layer"))},
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

    if generated != TRIGGERS or total_init != TRIGGERS:
        raise RuntimeError(
            f"{job['job_id']}: events={generated}, init={total_init}"
        )
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve() or header_seed != job["seed"]:
        raise RuntimeError(f"{job['job_id']}: geometry/seed header mismatch")
    if spectral != ["SpectralType Mono 1e-06"]:
        raise RuntimeError(f"{job['job_id']}: epsilon spectral header mismatch: {spectral}")

    catalog.update(extras)
    catalog["n_generated_events_seen"] = generated
    catalog["generated_events"] = generated
    catalog["active_only_events"] = active_only
    catalog["active_only_rate_hz"] = active_only * job["event_weight_cps"]
    catalog["cell_metadata"] = {
        "geometry": job["geometry"], "family": job["family"], "mode": "delayed",
        "jobs": 1, "generated_events": generated, "TT_s": job["equivalent_time_s"],
        "event_weight_cps": job["event_weight_cps"], "included_ground_activity_Bq": job["activity_Bq"],
        "known_holdout_activity_Bq": job["known_holdout_activity_Bq"],
        "unknown_activity_state_count": job["unknown_activity_state_count"],
        "authority_status": "DELAYED_GROUND_STATE_POSITIONAL_SUBSAMPLE_SCREENING",
        "normalization": "included ground-state day15 activity / 250000 triggers",
    }
    cache = Path(cache_dir) / f"job_{job['scan_index']:02d}.pkl"
    with cache.open("wb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return {
        "scan_index": job["scan_index"], "path": str(cache), "geometry": job["geometry"],
        "family": job["family"], "events": generated, "deca_events": deca_events,
        "tes_positive_events": len(catalog["stream"]), "active_only_events": active_only,
        "pixel_hits": len(catalog["pix_e"]), "sim_bytes": Path(job["sim_path"]).stat().st_size,
        "exact_print_matches": exact_print_matches,
        "nearest_distance_max_cm": nearest_distance_max_cm,
        "full_mix": [[volume, za, count] for (volume, za), count in sorted(locator["full_mix"].items())],
        "selected_mix": [[volume, za, count] for (volume, za), count in sorted(locator["selected_mix"].items())],
        "realized_mix": [[volume, za, count] for (volume, za), count in sorted(realized_mix.items())],
    }


def distribution_tv(left: Counter[Any], right: Counter[Any]) -> float:
    left_total = math.fsum(left.values())
    right_total = math.fsum(right.values())
    keys = set(left) | set(right)
    return 0.5 * math.fsum(
        abs(left.get(key, 0) / left_total - right.get(key, 0) / right_total)
        for key in keys
    )


def aggregate_mix(rows: list[list[Any]], field: str) -> Counter[Any]:
    index = {"volume": 0, "ZA": 1, "joint": None}[field]
    result: Counter[Any] = Counter()
    for volume, za, count in rows:
        key = (str(volume), int(za)) if index is None else (str(volume) if index == 0 else int(za))
        result[key] += int(count)
    return result


def empty_zero_catalog() -> dict[str, Any]:
    catalog = prompt.old_parser().empty_catalog()
    for name in (
        "input_id", "batch_id", "job_name", "seed", "plastic_total_keV",
        "has_pair_ia", "has_annihilation_ia", "sim_initial_ZA", "source_parent_ZA",
        "source_volume", "source_excitation_keV", "parent_match_distance_cm",
        "production_x_cm", "production_y_cm", "production_z_cm", "has_deca",
    ):
        catalog[name] = []
    catalog.update(
        {
            "generated_events": 0,
            "active_only_events": 0,
            "active_only_rate_hz": 0.0,
            "cell_metadata": {
                "geometry": "Mass_model_511",
                "family": "muplus",
                "mode": "delayed",
                "jobs": 0,
                "generated_events": 0,
                "TT_s": 0.0,
                "event_weight_cps": 0.0,
                "included_ground_activity_Bq": 0.0,
                "authority_status": "NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
            },
        }
    )
    return catalog


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    names = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(output: Path, workers: int) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    config = load_json(CONFIG)
    jobs = selected_jobs(config)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    cache = work / "job_cache"
    cache.mkdir()
    started = time.monotonic()
    results: dict[int, dict[str, Any]] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scan_job, job, str(cache)): job for job in jobs}
            for completed, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                results[row["scan_index"]] = row
                print(
                    f"scanned {completed}/15 delayed cells, "
                    f"{sum(item['events'] for item in results.values()):,} events, "
                    f"{time.monotonic()-started:.1f}s",
                    flush=True,
                )

        coverage: list[dict[str, Any]] = []
        input_rows: list[dict[str, Any]] = []
        mix_rows: list[dict[str, Any]] = []
        mix_tv: list[dict[str, Any]] = []
        catalog_dir = work / "catalog"
        for job in jobs:
            result = results[job["scan_index"]]
            with Path(result["path"]).open("rb") as handle:
                catalog = pickle.load(handle)
            target = catalog_dir / job["geometry"] / f"{job['family']}.pkl"
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
            input_rows.append(
                {
                    "geometry": job["geometry"], "family": job["family"],
                    "source_status": "TRANSPORT_AND_RAW_SEMANTIC_SCAN_COMPLETE",
                    "cohort": job["authority_group"], "job_id": job["job_id"], "seed": job["seed"],
                    "triggers": TRIGGERS, "included_ground_activity_Bq": job["activity_Bq"],
                    "event_weight_cps": job["event_weight_cps"], "equivalent_time_s": job["equivalent_time_s"],
                    "subsample_rule": "sample_index modulo 5 equals 0; retained block flux multiplied by 5",
                    "source_path": job["prepared_source"], "source_manifest_path": job["source_manifest_path"],
                    "sampled_positions_path": job["sampled_positions_path"],
                    "sim_path": relative(Path(job["sim_path"])), "authority_path": job["authority_path"],
                    "known_holdout_activity_Bq": job["known_holdout_activity_Bq"],
                    "unknown_activity_state_count": job["unknown_activity_state_count"],
                }
            )
            coverage.append(
                {
                    "geometry": job["geometry"], "family": job["family"], "source_status": "TRANSPORT_AND_SEMANTIC_SCAN_COMPLETE",
                    "triggers": TRIGGERS, "included_ground_activity_Bq": job["activity_Bq"],
                    "event_weight_cps": job["event_weight_cps"], "equivalent_time_s": job["equivalent_time_s"],
                    "TES_positive_events": result["tes_positive_events"], "active_only_events": result["active_only_events"],
                    "pixel_hits": result["pixel_hits"], "events_with_IA_DECA": result["deca_events"],
                    "events_without_IA_DECA": TRIGGERS-result["deca_events"],
                    "lineage_matched_events": TRIGGERS, "lineage_ambiguous_events": 0, "lineage_unmatched_events": 0,
                    "exact_print_lineage_matches": result["exact_print_matches"],
                    "parent_match_distance_max_cm": result["nearest_distance_max_cm"],
                    "header_geometry_seed_epsilon_match": True,
                    "sim_path": relative(Path(job["sim_path"])), "authority_path": job["authority_path"],
                }
            )
            full = {(str(volume), int(za)): int(count) for volume, za, count in result["full_mix"]}
            selected = {(str(volume), int(za)): int(count) for volume, za, count in result["selected_mix"]}
            realized = {(str(volume), int(za)): int(count) for volume, za, count in result["realized_mix"]}
            for volume, parent_za in sorted(set(full) | set(selected) | set(realized)):
                mix_rows.append(
                    {
                        "geometry": job["geometry"], "family": job["family"], "source_volume": volume,
                        "source_parent_ZA": parent_za,
                        "full_50000_blocks": full.get((volume, parent_za), 0),
                        "full_50000_fraction": full.get((volume, parent_za), 0) / 50_000,
                        "selected_10000_blocks": selected.get((volume, parent_za), 0),
                        "selected_10000_fraction": selected.get((volume, parent_za), 0) / 10_000,
                        "realized_250000_triggers": realized.get((volume, parent_za), 0),
                        "realized_250000_fraction": realized.get((volume, parent_za), 0) / TRIGGERS,
                    }
                )
            full_rows = result["full_mix"]
            selected_rows = result["selected_mix"]
            realized_rows = result["realized_mix"]
            mix_tv.append(
                {
                    "geometry": job["geometry"], "family": job["family"],
                    "full_to_selected_volume_tv": distribution_tv(aggregate_mix(full_rows, "volume"), aggregate_mix(selected_rows, "volume")),
                    "full_to_selected_parent_ZA_tv": distribution_tv(aggregate_mix(full_rows, "ZA"), aggregate_mix(selected_rows, "ZA")),
                    "full_to_selected_joint_tv": distribution_tv(aggregate_mix(full_rows, "joint"), aggregate_mix(selected_rows, "joint")),
                    "selected_to_realized_joint_tv": distribution_tv(aggregate_mix(selected_rows, "joint"), aggregate_mix(realized_rows, "joint")),
                    "full_to_realized_joint_tv": distribution_tv(aggregate_mix(full_rows, "joint"), aggregate_mix(realized_rows, "joint")),
                }
            )

        zero_catalog = empty_zero_catalog()
        zero_target = catalog_dir / "Mass_model_511/muplus.pkl"
        zero_target.parent.mkdir(parents=True, exist_ok=True)
        with zero_target.open("wb") as handle:
            pickle.dump(zero_catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
        input_rows.append(
            {
                "geometry": "Mass_model_511", "family": "muplus",
                "source_status": "NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY", "cohort": "none",
                "job_id": "", "seed": "", "triggers": 0, "included_ground_activity_Bq": 0.0,
                "event_weight_cps": 0.0, "equivalent_time_s": 0.0, "subsample_rule": "not applicable",
                "source_path": "", "source_manifest_path": "", "sampled_positions_path": "", "sim_path": "",
                "authority_path": relative(ACTIVATION_SOURCE_INDEX), "known_holdout_activity_Bq": 0.0,
                "unknown_activity_state_count": 0,
            }
        )
        coverage.append(
            {
                "geometry": "Mass_model_511", "family": "muplus", "source_status": "NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
                "triggers": 0, "included_ground_activity_Bq": 0.0, "event_weight_cps": 0.0,
                "equivalent_time_s": 0.0, "TES_positive_events": 0, "active_only_events": 0,
                "pixel_hits": 0, "events_with_IA_DECA": 0, "events_without_IA_DECA": 0,
                "lineage_matched_events": 0, "lineage_ambiguous_events": 0, "lineage_unmatched_events": 0,
                "exact_print_lineage_matches": 0, "parent_match_distance_max_cm": 0.0,
                "header_geometry_seed_epsilon_match": True,
                "sim_path": "", "authority_path": relative(ACTIVATION_SOURCE_INDEX),
            }
        )
        input_rows.sort(key=lambda row: (GEOMETRIES.index(row["geometry"]), FAMILIES.index(row["family"])))
        coverage.sort(key=lambda row: (GEOMETRIES.index(row["geometry"]), FAMILIES.index(row["family"])))
        write_csv(work / "delayed_input_manifest.csv", input_rows)
        write_csv(work / "delayed_cell_coverage.csv", coverage)
        write_csv(work / "delayed_source_mix.csv", mix_rows)
        summary = {
            "schema_version": 1,
            "status": "PASS__M05_CORRECTED_DELAYED_RAW_CATALOG_15_SOURCE_CELL_COMPLETE",
            "transport_jobs": 15,
            "transport_triggers": 15 * TRIGGERS,
            "zero_source_cells": ["Mass_model_511/muplus"],
            "semantic_scan": {
                "workers": workers, "events": sum(row["events"] for row in results.values()),
                "events_with_IA_DECA": sum(row["deca_events"] for row in results.values()),
                "TES_positive_events": sum(row["tes_positive_events"] for row in results.values()),
                "pixel_hits": sum(row["pixel_hits"] for row in results.values()),
                "elapsed_s": time.monotonic()-started,
            },
            "normalization": "selected events * included ground-state day15 activity / 250000 triggers within each cell",
            "source_mix_total_variation": mix_tv,
            "catalog_scope": "raw TES and exact active-volume deposits plus activation-parent lineage; response is deferred to stage04",
            "known_exclusions": [
                "five unresolved NUBASE state rows", "0.0998092689784 Bq known S3d-O8 excited-state holdout",
                "positional stride-5 source-mix uncertainty is reported separately from transport counting statistics",
            ],
            "large_sim_hash_policy": "no large SIM hash recomputation; one semantic+detector scan to gzip EOF",
            "authority_boundary": "DELAYED_RAW_GROUND_STATE_CATALOG__NOT_YET_COMMON_RESPONSE_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        report = [
            "# Corrected-keV delayed screening", "", f"Status: `{summary['status']}`", "",
            f"Fifteen positive ground-state cells contribute {15*TRIGGERS:,} delayed triggers; Mass_model_511/muplus is retained as a zero-source cell.",
            "Rates use the full day-15 cell activity divided by 250,000 triggers. The six recovery0002 and nine new cells share the same 10,000-position stride-5, flux-x5 source contract.",
            "", "This stage publishes raw compact detector records, parent lineage, and source-mix QA only. Pixel response, exact active veto, and Step05 are intentionally deferred to the shared stage04 replay.",
            "", "Explicit excited/unresolved state holdouts and positional-subsampling uncertainty remain outside the transport counting interval; mission sensitivity and geometry promotion are not claimed.", "",
        ]
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        shutil.rmtree(cache)
        manifest = {
            "schema_version": 1, "status": summary["status"], "analysis_code": relative(HERE),
            "reused_code": [relative(prompt.HERE)],
            "method_reference": "engineering/m04_validation_geometry_handoff_20260810/01_m_sampling_validation_20260810/code/run_offline_m_sampling_validation.py",
            "files": [{"path": str(path.relative_to(work)), "bytes": path.stat().st_size} for path in sorted(work.rglob("*")) if path.is_file()],
            "hash_note": "Large SIM hashes were not recomputed.",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        os.rename(work, output)
        print(f"{summary['status']}: {15*TRIGGERS} triggers, {output}")
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    run(output.resolve(), args.workers)


if __name__ == "__main__":
    main()
