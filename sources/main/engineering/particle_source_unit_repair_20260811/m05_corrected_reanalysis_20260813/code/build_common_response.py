#!/usr/bin/env python3
"""Replay prompt, delayed, and focused signal through one response contract."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import pickle
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import check_inputs
import run_prompt_analysis as prompt


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
CONFIG = PACKAGE / "analysis_inputs.json"
OUTPUT = PACKAGE / "outputs/04_common_response"
PROMPT_CATALOG = PACKAGE / "outputs/01_prompt/catalog"
DELAYED_CATALOG = PACKAGE / "outputs/03_delayed/catalog"
STEP09 = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json"
EVENTLIST = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
OPTICS = ROOT / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
SIGNAL_TRIALS = 37_194

SIGNAL_INPUTS = {
    "Mass_model_511": {
        "sim": ROOT / "runs/Mass_model_511_nearfield_migration_20260701/step09_focus_candidate_Mass_model_511_Mass_model_511_smoke/Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.inc1.id1.sim.gz",
        "source": ROOT / "runs/Mass_model_511_nearfield_migration_20260701/step09_focus_candidate_Mass_model_511_Mass_model_511_smoke/Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.source",
        "authority": ROOT / "engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/signal_transport_manifest.json",
        "run_name": "Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke",
    },
    "S3d_O8": {
        "sim": ROOT / "runs/geometry_optimization_20260704/s3d_o8_f10m_a1_signal_replay_37194_20260712/Opticsim_laue_f10m_a1_s3d_o8_signal37194.inc1.id1.sim.gz",
        "source": ROOT / "runs/geometry_optimization_20260704/s3d_o8_f10m_a1_signal_replay_37194_20260712/Opticsim_laue_f10m_a1_s3d_o8_signal37194.source",
        "authority": ROOT / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_signal_replay_summary.json",
        "run_name": "Opticsim_laue_f10m_a1_s3d_o8_signal37194",
    },
}

_RUNTIME: tuple[Any, Any, dict[str, Any]] | None = None


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def signal_header(path: Path) -> tuple[str, int]:
    geometry = ""
    seed = -1
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line in handle:
            if line.startswith("Geometry "):
                geometry = line.split(maxsplit=1)[1].strip()
            elif line.startswith("Seed "):
                seed = int(line.split()[1])
            elif line == "SE\n":
                break
    return geometry, seed


def source_seed(path: Path) -> int:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Seed "):
            return int(line.split()[1])
    raise RuntimeError(f"source seed absent: {path}")


def build_signal_jobs(config: dict[str, Any], eventlist_sha256: str) -> list[dict[str, Any]]:
    rows = []
    for index, geometry in enumerate(prompt.GEOMETRY_ORDER):
        item = SIGNAL_INPUTS[geometry]
        header_geometry, header_seed = signal_header(item["sim"])
        expected_geometry = (ROOT / config["geometries"][geometry]["setup"]).resolve()
        if Path(header_geometry).resolve() != expected_geometry:
            raise RuntimeError(f"signal geometry differs: {geometry}")
        active = list(config["geometries"][geometry]["active_veto_volumes"])
        rows.append(
            {
                "scan_index": index,
                "geometry": geometry,
                "family": "focused_511",
                "mode": "signal",
                "input_id": "focused_signal_eventlist",
                "batch_id": f"eventlist_sha256:{eventlist_sha256}",
                "job_id": item["run_name"],
                "events": SIGNAL_TRIALS,
                "sim_path": str(item["sim"].resolve()),
                "seed": header_seed,
                "source_declared_seed": source_seed(item["source"]),
                "expected_geometry": str(expected_geometry),
                "shield_volumes": [name for name in active if "Plastic" not in name],
                "plastic_volumes": [name for name in active if "Plastic" in name],
                "source": relative(item["source"]),
                "authority": relative(item["authority"]),
            }
        )
    return rows


def publish_signal_catalog(
    job: dict[str, Any], scan: dict[str, Any], target: Path, aeff_cm2: float,
    eventlist_sha256: str, sim_sha256: str,
) -> dict[str, Any]:
    with Path(scan["path"]).open("rb") as handle:
        catalog = pickle.load(handle)
    weight = aeff_cm2 / SIGNAL_TRIALS
    catalog["stream"] = ["signal"] * len(catalog["stream"])
    catalog["tag"] = ["focused_511"] * len(catalog["tag"])
    catalog["rate_hz"] = [weight] * len(catalog["rate_hz"])
    catalog["eventlist_id"] = [int(local_id) - 1 for local_id in catalog["local_id"]]
    catalog["cell_metadata"] = {
        "geometry": job["geometry"],
        "family": "focused_511",
        "mode": "signal",
        "jobs": 1,
        "generated_events": SIGNAL_TRIALS,
        "TT_s": 0.0,
        "event_weight_cps": weight,
        "event_weight_unit": "cm2",
        "effective_area_input_cm2": aeff_cm2,
        "eventlist_sha256": eventlist_sha256,
        "sim_sha256": sim_sha256,
        "transport_header_seed": job["seed"],
        "source_declared_seed": job["source_declared_seed"],
        "authority_status": "FOCUSED_SIGNAL_BE_WINDOW_INJECTION_RAW_CATALOG",
        "scope": "post-Be-window detector acceptance; not full-envelope BPE/plastic transmission",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return {
        "geometry": job["geometry"],
        "generated_events": SIGNAL_TRIALS,
        "TES_positive_events": len(catalog["stream"]),
        "active_only_events": int(catalog["active_only_events"]),
        "pixel_hits": len(catalog["pix_e"]),
        "transport_header_seed": job["seed"],
        "source_declared_seed": job["source_declared_seed"],
        "catalog": f"catalog/signal/{job['geometry']}.pkl",
    }


def response_runtime() -> tuple[Any, Any, dict[str, Any]]:
    global _RUNTIME
    if _RUNTIME is None:
        core = prompt.load_module("m05_common_response_core", prompt.CORRECTED_CORE).core
        step05 = prompt.load_module("m05_common_response_step05", prompt.STEP05)
        step05.ROOT = ROOT
        step05.STEP09_SUMMARY = STEP09
        _RUNTIME = core, step05, step05.side_entry_disk()
    return _RUNTIME


def centroid_radius(hits: list[Any], bridge: dict[str, Any]) -> float | None:
    total = math.fsum(float(hit.e) for hit in hits)
    if total <= 0.0:
        return None
    x = math.fsum(float(hit.e) * float(hit.x) for hit in hits) / total
    y = math.fsum(float(hit.e) * float(hit.y) for hit in hits) / total
    z = math.fsum(float(hit.e) * float(hit.z) for hit in hits) / total
    angle = math.radians(-float(bridge["instrument_rotation_y_deg"]))
    local_z = -math.sin(angle) * x + math.cos(angle) * z
    return math.hypot(y - float(bridge["axis_y_cm"]), local_z - float(bridge["axis_z_cm"]))


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))]


def evaluate_catalog(task: dict[str, Any]) -> dict[str, Any]:
    with Path(task["path"]).open("rb") as handle:
        catalog = pickle.load(handle)
    core, step05, disk = response_runtime()
    cutflow, spectrum, occupancy = prompt.evaluate_cell(catalog, core, step05, disk)
    multiplicity: Counter[tuple[str, str, str, str]] = Counter()
    selected: list[dict[str, Any]] = []
    psf: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
    signal_pass_ids: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    bridge = task["bridge"]

    for event_index in range(len(catalog["stream"])):
        event = prompt.evaluate_event(catalog, event_index, core, step05, disk)
        for response_state, hits in (("raw", event["raw_hits"]), ("measured", event["measured_hits"])):
            total = math.fsum(hit.e for hit in hits)
            stages = {
                "pre_veto": True,
                "active_veto50": event["active_pass"][50.0],
            }
            if response_state == "measured":
                stages["side_compton_fov_pass"] = event["active_pass"][50.0] and event["topology_pass"]
            for stage, passed in stages.items():
                if not passed:
                    continue
                for window_id, bounds in prompt.WINDOWS.items():
                    if not prompt.in_window(total, bounds):
                        continue
                    count = len(hits)
                    bucket = "n1" if count == 1 else ("n2" if count == 2 else "n3plus")
                    multiplicity[(response_state, stage, window_id, bucket)] += 1
                    if task["stream"] == "signal" and response_state == "measured":
                        radius = centroid_radius(hits, bridge)
                        if radius is not None:
                            psf[(stage, window_id)].append(radius)
                        signal_pass_ids[(stage, window_id)].append(
                            int(catalog["local_id"][event_index])
                        )

        measured = event["measured_total_keV"]
        final = (
            prompt.in_window(measured, prompt.WINDOWS["w2_510p58_511p42"])
            and event["active_pass"][50.0]
            and event["topology_pass"]
        )
        if final and task["stream"] in {"prompt", "delayed"}:
            row = {
                "geometry": task["geometry"],
                "stream": task["stream"],
                "family": task["family"],
                "local_event_id": int(catalog["local_id"][event_index]),
                "batch_id": catalog["batch_id"][event_index],
                "job_name": catalog["job_name"][event_index],
                "transport_seed": int(catalog["seed"][event_index]),
                "measured_total_keV": measured,
                "measured_multiplicity": len(event["measured_hits"]),
                "shield_keV": event["shield_keV"],
                "plastic_keV": event["plastic_keV"],
                "event_weight_cps": float(catalog["cell_metadata"]["event_weight_cps"]),
                "source_parent_ZA": "",
                "source_volume": "",
                "source_excitation_keV": "",
                "sim_initial_ZA": "",
                "parent_match_distance_cm": "",
                "source_file": catalog["source_file"][event_index],
            }
            if task["stream"] == "delayed":
                row.update(
                    {
                        "source_parent_ZA": int(catalog["source_parent_ZA"][event_index]),
                        "source_volume": catalog["source_volume"][event_index],
                        "source_excitation_keV": float(catalog["source_excitation_keV"][event_index]),
                        "sim_initial_ZA": int(catalog["sim_initial_ZA"][event_index]),
                        "parent_match_distance_cm": float(catalog["parent_match_distance_cm"][event_index]),
                    }
                )
            selected.append(row)

    event_weight = float(catalog["cell_metadata"]["event_weight_cps"])
    multiplicity_rows = []
    for key, value in sorted(multiplicity.items()):
        if task["stream"] == "signal":
            trials = int(catalog["cell_metadata"]["generated_events"])
            probability = value / trials
            sigma = float(catalog["cell_metadata"]["effective_area_input_cm2"]) * math.sqrt(
                probability * (1.0 - probability) / trials
            )
            statistical_model = "binomial_marginal__categories_are_multinomial"
        else:
            sigma = math.sqrt(value) * event_weight
            statistical_model = "poisson_mc"
        multiplicity_rows.append(
            {
                "response_state": key[0], "stage": key[1], "window_id": key[2],
                "multiplicity": key[3], "events": value,
                "event_weight": event_weight, "weighted_value": value * event_weight,
                "weighted_stat_sigma": sigma,
                "weighted_unit": "cm2" if task["stream"] == "signal" else "cps",
                "statistical_model": statistical_model,
            }
        )

    return {
        "geometry": task["geometry"],
        "stream": task["stream"],
        "family": task["family"],
        "meta": catalog["cell_metadata"],
        "cutflow": cutflow,
        "spectrum": spectrum,
        "occupancy": occupancy,
        "multiplicity": multiplicity_rows,
        "selected": selected,
        "psf": [
            {
                "stage": key[0], "window_id": key[1], "events": len(values),
                "r50_cm": quantile(values, 0.5), "r90_cm": quantile(values, 0.9),
                "r95_cm": quantile(values, 0.95), "r99_cm": quantile(values, 0.99),
            }
            for key, values in sorted(psf.items())
        ],
        "signal_pass_ids": {
            f"{key[0]}|{key[1]}": sorted(values)
            for key, values in sorted(signal_pass_ids.items())
        },
    }


def clopper_pearson(count: int, trials: int) -> tuple[float, float]:
    from scipy.stats import beta

    lower = 0.0 if count == 0 else float(beta.ppf(0.025, count, trials - count + 1))
    upper = 1.0 if count == trials else float(beta.ppf(0.975, count + 1, trials - count))
    return lower, upper


def common_cutflow(results: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        stream = result["stream"]
        meta = result["meta"]
        for source in result["cutflow"]:
            count = int(source["selected_events"])
            if stream == "signal":
                trials = int(meta["generated_events"])
                weight = aeff_cm2 / trials
                probability = count / trials
                lower, upper = clopper_pearson(count, trials)
                weighted = count * weight
                sigma = aeff_cm2 * math.sqrt(probability * (1.0 - probability) / trials)
                lower_weighted, upper_weighted = aeff_cm2 * lower, aeff_cm2 * upper
                unit = "cm2"
                exposure = trials / aeff_cm2
                exposure_unit = "cm-2"
            else:
                weight = float(source["event_weight_cps"])
                weighted = float(source["rate_cps"])
                sigma = float(source["rate_stat_sigma_cps"])
                lower_weighted = float(source["rate_lower95_cps"])
                upper_weighted = float(source["rate_upper95_cps"])
                unit = "cps"
                exposure = float(source["TT_s"])
                exposure_unit = "s"
            rows.append(
                {
                    "geometry": result["geometry"], "stream": stream, "family": result["family"],
                    "response_state": source["response_state"], "stage": source["stage"],
                    "window_id": source["window_id"], "energy_lo_keV": source["energy_lo_keV"],
                    "energy_hi_keV": source["energy_hi_keV"], "generated_events": source["generated_events"],
                    "normalization_exposure": exposure, "normalization_exposure_unit": exposure_unit,
                    "selected_events": count, "event_weight": weight, "weighted_value": weighted,
                    "weighted_stat_sigma": sigma, "weighted_lower95": lower_weighted,
                    "weighted_upper95": upper_weighted, "weighted_unit": unit,
                    "authority_status": meta.get("authority_status", "PROMPT_CORRECTED_COMMON_RESPONSE"),
                }
            )
    return rows


def common_spectrum(results: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    totals: defaultdict[tuple[str, str, str, str, int], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0]
    )
    for result in results:
        for (response, stage, bin_index), (events, weighted, variance) in result["spectrum"].items():
            key = (result["geometry"], result["stream"], response, stage, bin_index)
            target = totals[key]
            target[0] += events
            target[1] += weighted
            target[2] += variance
    rows = []
    n_bins = int(round((prompt.SPECTRUM_HI_KEV - prompt.SPECTRUM_LO_KEV) / prompt.SPECTRUM_BIN_KEV))
    for geometry in prompt.GEOMETRY_ORDER:
        for stream in ("prompt", "delayed", "signal"):
            for response, stages in (
                ("raw", ("pre_veto", "active_veto50")),
                ("measured", ("pre_veto", "active_veto50", "side_compton_fov_pass")),
            ):
                for stage in stages:
                    for bin_index in range(n_bins):
                        events, weighted, variance = totals[(geometry, stream, response, stage, bin_index)]
                        if stream == "signal":
                            weighted = events * aeff_cm2 / SIGNAL_TRIALS
                            probability = events / SIGNAL_TRIALS
                            sigma = aeff_cm2 * math.sqrt(probability * (1.0 - probability) / SIGNAL_TRIALS)
                            unit = "cm2/keV"
                        else:
                            sigma = math.sqrt(variance)
                            unit = "cps/keV"
                        lo = prompt.SPECTRUM_LO_KEV + bin_index * prompt.SPECTRUM_BIN_KEV
                        rows.append(
                            {
                                "geometry": geometry, "stream": stream, "response_state": response,
                                "stage": stage, "energy_lo_keV": lo,
                                "energy_hi_keV": lo + prompt.SPECTRUM_BIN_KEV,
                                "energy_center_keV": lo + 0.5 * prompt.SPECTRUM_BIN_KEV,
                                "events_per_bin": int(events),
                                "weighted_density": weighted / prompt.SPECTRUM_BIN_KEV,
                                "weighted_stat_sigma_density": sigma / prompt.SPECTRUM_BIN_KEV,
                                "weighted_density_unit": unit,
                            }
                        )
    return rows


def background_summary(cutflow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: defaultdict[tuple[str, str, str, str, str], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0]
    )
    for row in cutflow:
        if row["stream"] not in {"prompt", "delayed"}:
            continue
        key = (row["geometry"], row["stream"], row["response_state"], row["stage"], row["window_id"])
        target = totals[key]
        target[0] += int(row["selected_events"])
        target[1] += float(row["weighted_value"])
        target[2] += float(row["weighted_stat_sigma"]) ** 2
    rows = []
    for geometry in prompt.GEOMETRY_ORDER:
        for response in ("raw", "measured"):
            stages = ("pre_veto", "active_veto50") + (("side_compton_fov_pass",) if response == "measured" else ())
            for stage in stages:
                for window_id in prompt.WINDOWS:
                    p = totals[(geometry, "prompt", response, stage, window_id)]
                    d = totals[(geometry, "delayed", response, stage, window_id)]
                    rows.append(
                        {
                            "geometry": geometry, "response_state": response, "stage": stage,
                            "window_id": window_id, "prompt_events": int(p[0]), "prompt_rate_cps": p[1],
                            "prompt_stat_sigma_cps": math.sqrt(p[2]), "delayed_events": int(d[0]),
                            "delayed_rate_cps": d[1], "delayed_stat_sigma_cps": math.sqrt(d[2]),
                            "total_background_rate_cps": p[1] + d[1],
                            "total_background_stat_sigma_cps": math.sqrt(p[2] + d[2]),
                        }
                    )
    return rows


def signal_acceptance(cutflow: list[dict[str, Any]], aeff_cm2: float) -> list[dict[str, Any]]:
    rows = []
    for row in cutflow:
        if row["stream"] != "signal":
            continue
        count = int(row["selected_events"])
        lower, upper = clopper_pearson(count, SIGNAL_TRIALS)
        rows.append(
            {
                "geometry": row["geometry"], "response_state": row["response_state"],
                "stage": row["stage"], "window_id": row["window_id"], "trials": SIGNAL_TRIALS,
                "selected_events": count, "acceptance": count / SIGNAL_TRIALS,
                "acceptance_lower95": lower, "acceptance_upper95": upper,
                "input_optics_aeff_cm2": aeff_cm2,
                "selected_effective_area_cm2": float(row["weighted_value"]),
                "selected_effective_area_lower95_cm2": aeff_cm2 * lower,
                "selected_effective_area_upper95_cm2": aeff_cm2 * upper,
            }
        )
    return rows


def paired_signal_comparison(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_geometry = {
        result["geometry"]: result["signal_pass_ids"]
        for result in results if result["stream"] == "signal"
    }
    rows = []
    for response_key in sorted(set(by_geometry["Mass_model_511"]) | set(by_geometry["S3d_O8"])):
        mass = set(by_geometry["Mass_model_511"].get(response_key, []))
        o8 = set(by_geometry["S3d_O8"].get(response_key, []))
        both = len(mass & o8)
        mass_only = len(mass - o8)
        o8_only = len(o8 - mass)
        neither = SIGNAL_TRIALS - both - mass_only - o8_only
        mass_acceptance = len(mass) / SIGNAL_TRIALS
        o8_acceptance = len(o8) / SIGNAL_TRIALS
        stage, window_id = response_key.split("|", 1)
        rows.append(
            {
                "response_state": "measured", "stage": stage, "window_id": window_id,
                "pairing_scope": "same_EventList_local_id_only__not_matched_transport_or_response_RNG",
                "paired_trials": SIGNAL_TRIALS, "both_pass": both,
                "Mass_model_511_only": mass_only, "S3d_O8_only": o8_only, "neither_pass": neither,
                "Mass_model_511_acceptance": mass_acceptance, "S3d_O8_acceptance": o8_acceptance,
                "S3d_O8_minus_Mass_acceptance": o8_acceptance - mass_acceptance,
                "S3d_O8_over_Mass_acceptance": o8_acceptance / mass_acceptance if mass_acceptance else "",
            }
        )
    return rows


def run(output: Path, workers: int) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    cache = work / "signal_scan_cache"
    cache.mkdir()
    started = time.monotonic()
    try:
        config = load_json(CONFIG)
        actual_namespace = response_runtime()[0].RESPONSE_NAMESPACE
        if actual_namespace != config["analysis"]["response"]["rng_namespace"]:
            raise RuntimeError(
                f"response namespace differs: actual={actual_namespace}, "
                f"configured={config['analysis']['response']['rng_namespace']}"
            )
        optics = load_json(OPTICS)
        bridge = load_json(STEP09)["bridge"]
        aeff_cm2 = float(optics["aeff_511_cm2"])
        eventlist_sha = sha256(EVENTLIST)
        eventlist_rows = sum(1 for line in EVENTLIST.open("r", encoding="utf-8") if line.strip() and not line.startswith("#"))
        if eventlist_rows != SIGNAL_TRIALS:
            raise RuntimeError(f"EventList rows={eventlist_rows}")
        jobs = build_signal_jobs(config, eventlist_sha)
        signal_hashes = {job["geometry"]: sha256(Path(job["sim_path"])) for job in jobs}

        scans: dict[int, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(prompt.scan_job, job, str(cache)): job for job in jobs}
            for future in as_completed(futures):
                row = future.result()
                scans[row["scan_index"]] = row
                print(f"signal raw scan {len(scans)}/2 complete", flush=True)

        signal_catalogs = []
        for job in jobs:
            target = work / "catalog/signal" / f"{job['geometry']}.pkl"
            signal_catalogs.append(
                publish_signal_catalog(
                    job, scans[job["scan_index"]], target, aeff_cm2,
                    eventlist_sha, signal_hashes[job["geometry"]],
                )
            )

        tasks = []
        for geometry in prompt.GEOMETRY_ORDER:
            for family in prompt.FAMILY_ORDER:
                tasks.append(
                    {"path": str(PROMPT_CATALOG / geometry / f"{family}.pkl"), "geometry": geometry,
                     "stream": "prompt", "family": family, "bridge": bridge}
                )
                tasks.append(
                    {"path": str(DELAYED_CATALOG / geometry / f"{family}.pkl"), "geometry": geometry,
                     "stream": "delayed", "family": family, "bridge": bridge}
                )
            tasks.append(
                {"path": str(work / "catalog/signal" / f"{geometry}.pkl"), "geometry": geometry,
                 "stream": "signal", "family": "focused_511", "bridge": bridge}
            )

        results = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(evaluate_catalog, task): task for task in tasks}
            for future in as_completed(futures):
                results.append(future.result())
                if len(results) % 8 == 0 or len(results) == len(tasks):
                    print(f"common response {len(results)}/{len(tasks)} catalogs complete", flush=True)

        full_cutflow = common_cutflow(results, aeff_cm2)
        veto_threshold_scan = [
            row for row in full_cutflow
            if row["stage"] in {"active_veto50", "active_veto70", "active_veto80"}
        ]
        cutflow = [
            row for row in full_cutflow
            if row["stage"] not in {"active_veto70", "active_veto80"}
        ]
        spectrum = common_spectrum(results, aeff_cm2)
        background = background_summary(cutflow)
        signal = signal_acceptance(cutflow, aeff_cm2)
        paired_signal = paired_signal_comparison(results)
        multiplicity = []
        selected = []
        psf = []
        occupancy = []
        for result in results:
            for row in result["multiplicity"]:
                multiplicity.append(
                    {"geometry": result["geometry"], "stream": result["stream"],
                     "family": result["family"], **row}
                )
            selected.extend(result["selected"])
            for row in result["psf"]:
                psf.append({"geometry": result["geometry"], **row})
            occ = result["occupancy"]
            unit = "cm2" if result["stream"] == "signal" else "cps"
            event_weight = float(result["meta"]["event_weight_cps"])
            if result["stream"] == "signal":
                trials = int(result["meta"]["generated_events"])
                scale = float(result["meta"]["effective_area_input_cm2"])

                def occupancy_sigma(events: int) -> float:
                    probability = events / trials
                    return scale * math.sqrt(probability * (1.0 - probability) / trials)

                statistical_model = "binomial"
            else:
                def occupancy_sigma(events: int) -> float:
                    return math.sqrt(events) * event_weight

                statistical_model = "poisson_mc"
            occupancy_sigma_value = occupancy_sigma(int(occ["detector_occupancy_events"]))
            occupancy.append(
                {
                    "geometry": result["geometry"], "stream": result["stream"], "family": result["family"],
                    "generated_events": occ["generated_events"],
                    "detector_occupancy_events": occ["detector_occupancy_events"],
                    "tes_positive_events": occ["tes_positive_events"], "active_only_events": occ["active_only_events"],
                    "pixel_hits": occ["pixel_hits"], "weighted_occupancy": occ["fullband_rate_cps"],
                    "weighted_tes": occ["tes_rate_cps"], "weighted_active_only": occ["active_only_rate_cps"],
                    "weighted_stat_sigma": occupancy_sigma_value,
                    "weighted_occupancy_stat_sigma": occupancy_sigma_value,
                    "weighted_tes_stat_sigma": occupancy_sigma(int(occ["tes_positive_events"])),
                    "weighted_active_only_stat_sigma": occupancy_sigma(int(occ["active_only_events"])),
                    "weighted_unit": unit, "statistical_model": statistical_model,
                }
            )

        write_csv(work / "common_cutflow.csv", sorted(cutflow, key=lambda r: (r["geometry"], r["stream"], r["family"], r["response_state"], r["stage"], r["window_id"])))
        write_csv(work / "veto_threshold_scan.csv", sorted(veto_threshold_scan, key=lambda r: (r["geometry"], r["stream"], r["family"], r["response_state"], r["stage"], r["window_id"])))
        write_csv(work / "common_spectrum_480_550.csv", spectrum)
        write_csv(work / "background_prompt_delayed_cutflow.csv", background)
        write_csv(work / "signal_acceptance_effective_area.csv", signal)
        write_csv(work / "signal_paired_comparison.csv", paired_signal)
        write_csv(work / "signal_psf.csv", sorted(psf, key=lambda r: (r["geometry"], r["stage"], r["window_id"])))
        write_csv(work / "common_multiplicity.csv", sorted(multiplicity, key=lambda r: (r["geometry"], r["stream"], r["family"], r["response_state"], r["stage"], r["window_id"], r["multiplicity"])))
        write_csv(work / "common_fullband_occupancy.csv", sorted(occupancy, key=lambda r: (r["geometry"], r["stream"], r["family"])))
        if selected:
            write_csv(work / "selected_background_w2_lineage.csv", sorted(selected, key=lambda r: (r["geometry"], r["stream"], r["family"], r["job_name"], r["local_event_id"])))
        else:
            (work / "selected_background_w2_lineage.csv").write_text("geometry,stream,family,local_event_id\n", encoding="utf-8")

        def background_cell(geometry: str, window: str) -> dict[str, Any]:
            return next(
                row for row in background
                if row["geometry"] == geometry and row["response_state"] == "measured"
                and row["stage"] == "side_compton_fov_pass" and row["window_id"] == window
            )

        def signal_cell(geometry: str, window: str) -> dict[str, Any]:
            return next(
                row for row in signal
                if row["geometry"] == geometry and row["response_state"] == "measured"
                and row["stage"] == "side_compton_fov_pass" and row["window_id"] == window
            )

        summary = {
            "schema_version": 1,
            "status": "PASS__M05_CORRECTED_COMMON_RESPONSE_PROMPT_DELAYED_SIGNAL_COMPLETE",
            "response_workers": workers,
            "catalogs": {"prompt": 16, "delayed": 16, "signal": 2},
            "response": {
                "implementation": relative(prompt.CORRECTED_CORE),
                "namespace": actual_namespace,
                "key": config["analysis"]["response"]["rng_key"],
                "seed_policy": config["analysis"]["response"]["seed_policy"],
                "FWHM_keV": config["analysis"]["response"]["fwhm_keV"],
                "measured_pixel_threshold_keV": config["analysis"]["response"]["measured_pixel_threshold_keV"],
                "active_veto": "Mass exact 24 CsI; S3d exact 3 BGO at threshold plus exact 3 plastic fixed below 50 keV",
                "compton_fov": relative(prompt.STEP05),
            },
            "signal": {
                "eventlist": relative(EVENTLIST), "eventlist_sha256": eventlist_sha,
                "eventlist_rows": eventlist_rows, "input_optics_aeff_cm2": aeff_cm2,
                "catalogs": signal_catalogs,
                "sim_sha256": signal_hashes,
                "scope": "post-Be-window detector acceptance; no full-envelope plastic/BPE transmission claim",
                "normalization": f"selected effective area = {aeff_cm2} cm2 * selected/{SIGNAL_TRIALS}; no second {SIGNAL_TRIALS}/150000 factor",
                "eventlist_pairing_scope": "same EventList local ID only; transport seeds and response keys are geometry-specific",
            },
            "output_domains": {
                "common_response": "nominal 50-keV active veto plus Step05",
                "veto_threshold_scan": "50/70/80-keV scan retained only in veto_threshold_scan.csv",
            },
            "statistical_notes": {
                "background": "independent weighted MC components use sqrt(sum(w_i^2))",
                "signal": "fixed-N acceptance uses binomial marginal uncertainty; multiplicity buckets have multinomial covariance",
            },
            "final_measured": {
                geometry: {
                    "broad_480_550": background_cell(geometry, "broad_480_550"),
                    "w2_510p58_511p42": background_cell(geometry, "w2_510p58_511p42"),
                    "signal_broad_480_550": signal_cell(geometry, "broad_480_550"),
                    "signal_w2_510p58_511p42": signal_cell(geometry, "w2_510p58_511p42"),
                }
                for geometry in prompt.GEOMETRY_ORDER
            },
            "elapsed_s": time.monotonic() - started,
            "known_exclusions": [
                "0.0998092689784 Bq S3d excited-state holdout and unresolved NUBASE rows",
                "10k exact-position source subsampling uncertainty is separate from transport counting sigma",
                "atmospheric transmission, source flux, timeline, significance, and sensitivity are deferred to stage06",
            ],
            "authority_boundary": "COMMON_RESPONSE_COMPLETE__NOT_YET_MATCHED_GEOMETRY_PROMOTION_MISSION_OR_SENSITIVITY_AUTHORITY",
        }
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        report = [
            "# Corrected-keV common response", "", f"Status: `{summary['status']}`", "",
            "| Geometry | prompt W2 cps | delayed W2 cps | total W2 cps | signal W2 acceptance | selected Aeff (cm2) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for geometry in prompt.GEOMETRY_ORDER:
            background_row = background_cell(geometry, "w2_510p58_511p42")
            signal_row = signal_cell(geometry, "w2_510p58_511p42")
            report.append(
                f"| {geometry} | {background_row['prompt_rate_cps']:.8g} | {background_row['delayed_rate_cps']:.8g} | "
                f"{background_row['total_background_rate_cps']:.8g} | {signal_row['acceptance']:.8g} | "
                f"{signal_row['selected_effective_area_cm2']:.8g} |"
            )
        report.extend(
            ["", "Signal is normalized at the Be-window injection plane. Mission folding and any geometry-promotion claim remain deferred.", ""]
        )
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        shutil.rmtree(cache)
        manifest = {
            "schema_version": 1, "status": summary["status"], "analysis_code": relative(HERE),
            "reused_code": [relative(prompt.HERE), relative(prompt.CORRECTED_CORE), relative(prompt.STEP05)],
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in sorted(work.rglob("*")) if path.is_file()
            ],
            "input_stage_summaries": [
                {"path": relative(path), "sha256": sha256(path)}
                for path in (PROMPT_CATALOG.parent / "summary.json", DELAYED_CATALOG.parent / "summary.json")
            ],
            "hash_policy": "signal SIMs, shared EventList, and small stage01/stage03 summaries only",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(work, output)
        print(f"{summary['status']}: {output}")
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
