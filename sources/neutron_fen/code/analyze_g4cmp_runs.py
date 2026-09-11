#!/usr/bin/env python3
"""Aggregate one or more SH3 G4CMP run directories into detector observables.

Each run directory must contain summary.json, event_map.csv, and hits.csv.  The
script writes analysis.json, events.csv, and channels.csv into each run.  An
optional cross-run JSON summary can also be requested.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / (2.0 * math.sqrt(2.0 * math.log(2.0)))
ROI_LOW_KEV = 510.58
ROI_HIGH_KEV = 511.42
TT_S = 1911.8824
PROMPT_MAX_NS = 1_000.0
INTERMEDIATE_MAX_NS = 10_000.0

EVENT_MAP_REQUIRED = {
    "sim_event_id", "group_key", "event_order", "sample_id", "job_id",
    "event_id", "layer", "candidate", "strict_recoil_event",
    "direct_tes_keV", "bgo_total_keV", "deposit_count", "input_energy_keV",
    "reference_time_ns", "primary_packet_count", "packet_energy_meV",
}

HITS_REQUIRED = {
    "sim_event_id", "group_key", "event_order", "job_id", "event_id",
    "layer", "candidate", "track_id", "particle", "start_energy_eV",
    "start_time_ns", "end_time_ns", "arrival_from_group_ns",
    "energy_deposited_eV", "track_weight", "weighted_energy_eV",
    "end_local_x_mm", "end_local_y_mm", "end_local_z_mm", "surface_class",
    "pixel_id",
}

EVENT_CSV_FIELDS = [
    "run_id", "group", "event_index", "source_event_order",
    "original_event_key", "sample_id", "job_id", "event_id", "candidate",
    "strict_recoil_event", "layers", "merged_layer_group_count",
    "deposit_count", "primary_packet_count", "terminal_branch_count",
    "si_input_keV", "sensor_keV", "bath_keV", "bulk_keV",
    "recorded_total_keV", "energy_closure_fraction", "sensor_eta",
    "bath_fraction", "bulk_fraction", "sensor_terminal_hit_count",
    "sensor_channel_hit_multiplicity", "sensor_channel_effective_multiplicity_ipr",
    "dominant_sensor_channel", "dominant_sensor_channel_keV",
    "sensor_arrival_q10_ns", "sensor_arrival_q50_ns", "sensor_arrival_q90_ns",
    "sensor_arrival_q99_ns", "sensor_prompt_lt_1us_keV",
    "sensor_intermediate_1_to_10us_keV", "sensor_late_ge_10us_keV",
    "sensor_prompt_fraction", "sensor_intermediate_fraction",
    "sensor_late_fraction", "direct_tes_keV", "reconstructed_mean_keV",
    "eta_mc_terminal_effective_count", "eta_mc_conservative_effective_count",
    "eta_mc_standard_error", "reconstructed_mean_mc_standard_error_keV",
    "gaussian_fwhm_keV", "gaussian_sigma_keV", "roi_low_keV",
    "roi_high_keV_exclusive", "gaussian_roi_probability",
    "expected_roi_count", "expected_roi_rate_per_s",
]

CHANNEL_CSV_FIELDS = [
    "run_id", "group", "event_index", "source_event_order",
    "original_event_key", "sample_id", "job_id", "event_id", "candidate",
    "layer", "pixel_id", "channel_id", "sensor_energy_keV",
    "fraction_of_event_sensor_energy", "fraction_of_si_input_energy",
    "terminal_hit_count", "arrival_q10_ns", "arrival_q50_ns", "arrival_q90_ns",
    "arrival_q99_ns", "prompt_lt_1us_keV", "intermediate_1_to_10us_keV",
    "late_ge_10us_keV",
]


def die(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def f(value: str) -> float:
    return float(value)


def i(value: str) -> int:
    return int(value)


def close(a: float, b: float, *, abs_tol: float = 1e-6) -> bool:
    return math.isclose(a, b, rel_tol=2e-10, abs_tol=abs_tol)


def only_consistent_float(values: Iterable[float], label: str) -> float:
    values = list(values)
    if not values:
        die(f"no values for {label}")
    if any(not close(values[0], value) for value in values[1:]):
        die(f"inconsistent values for merged layer groups: {label}={values}")
    return values[0]


def only_consistent_text(values: Iterable[str], label: str) -> str:
    values = list(values)
    if not values:
        die(f"no values for {label}")
    if any(values[0] != value for value in values[1:]):
        die(f"inconsistent values for merged layer groups: {label}={values}")
    return values[0]


def read_csv(path: Path, required: set[str]) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        missing = sorted(required - set(fields))
        if missing:
            die(f"{path} is missing required fields: {missing}")
        return fields, list(reader)


def weighted_quantile_ns(
    time_weight_pairs: Iterable[tuple[float, float]], probability: float
) -> float | None:
    pairs = sorted(
        (float(time), float(weight))
        for time, weight in time_weight_pairs if float(weight) > 0.0
    )
    if not pairs:
        return None
    total = math.fsum(weight for _, weight in pairs)
    target = probability * total
    cumulative = 0.0
    for time, weight in pairs:
        cumulative += weight
        if cumulative >= target:
            return time
    return pairs[-1][0]


def timing_summary(sensor_hits: list[dict[str, Any]]) -> dict[str, float | None]:
    pairs = [
        (float(hit["arrival_from_group_ns"]), float(hit["weighted_energy_eV"]))
        for hit in sensor_hits
    ]
    prompt_eV = math.fsum(weight for time, weight in pairs if time < PROMPT_MAX_NS)
    intermediate_eV = math.fsum(
        weight for time, weight in pairs
        if PROMPT_MAX_NS <= time < INTERMEDIATE_MAX_NS
    )
    late_eV = math.fsum(weight for time, weight in pairs if time >= INTERMEDIATE_MAX_NS)
    return {
        "q10_ns": weighted_quantile_ns(pairs, 0.10),
        "q50_ns": weighted_quantile_ns(pairs, 0.50),
        "q90_ns": weighted_quantile_ns(pairs, 0.90),
        "q99_ns": weighted_quantile_ns(pairs, 0.99),
        "prompt_eV": prompt_eV,
        "intermediate_eV": intermediate_eV,
        "late_eV": late_eV,
    }


def gaussian_interval_probability(mean_keV: float) -> float:
    """Stable Gaussian integral over the half-open ROI (endpoint is measure zero)."""
    lo = (ROI_LOW_KEV - mean_keV) / SIGMA_KEV
    hi = (ROI_HIGH_KEV - mean_keV) / SIGMA_KEV
    sqrt2 = math.sqrt(2.0)
    if lo >= 0.0:
        value = 0.5 * (math.erfc(lo / sqrt2) - math.erfc(hi / sqrt2))
    elif hi <= 0.0:
        value = 0.5 * (math.erfc(-hi / sqrt2) - math.erfc(-lo / sqrt2))
    else:
        value = 0.5 * (math.erf(hi / sqrt2) - math.erf(lo / sqrt2))
    return min(1.0, max(0.0, value))


def base_original_key(group_key: str) -> str:
    return re.sub(r"\|L\d+$", "", group_key)


def infer_group(summary: dict[str, Any], run_dir: Path) -> str:
    input_csv = summary.get("paths", {}).get("input_csv", "")
    stem = Path(input_csv).stem if input_csv else run_dir.name
    return re.sub(r"^\d+_", "", stem)


def packet_mc_uncertainty(
    terminal_hits: list[dict[str, Any]], primary_packet_count: int,
    input_eV: float,
) -> dict[str, float | None]:
    """Weighted Bernoulli packet estimate with an ancestry-agnostic cap.

    A terminal branch is coded 1 for sensor and 0 otherwise and weighted by its
    recorded energy.  Since hits.csv has no primary-parent ancestry, its Kish
    effective branch count is capped at the number of independently launched
    primary packets.  This avoids claiming extra independence from phonon
    down-conversion branches.  Primary packets are assumed independent; model,
    geometry, surface-parameter, and finite-event uncertainties are excluded.
    """
    weights = [float(hit["weighted_energy_eV"]) for hit in terminal_hits]
    total = math.fsum(weights)
    sumsq = math.fsum(weight * weight for weight in weights)
    if total <= 0.0 or sumsq <= 0.0 or primary_packet_count <= 0:
        return {
            "terminal_effective_count": None,
            "conservative_effective_count": None,
            "eta_standard_error": None,
        }
    n_terminal = total * total / sumsq
    n_conservative = min(float(primary_packet_count), n_terminal)
    sensor = math.fsum(
        float(hit["weighted_energy_eV"])
        for hit in terminal_hits if hit["surface_class"] == "sensor"
    )
    p_sensor_recorded = sensor / total
    closure = total / input_eV
    standard_error = closure * math.sqrt(
        max(0.0, p_sensor_recorded * (1.0 - p_sensor_recorded)) / n_conservative
    )
    return {
        "terminal_effective_count": n_terminal,
        "conservative_effective_count": n_conservative,
        "eta_standard_error": standard_error,
    }


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    return value


def write_table(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def load_and_validate_run(root: Path, run_dir: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    run_dir = run_dir.resolve(strict=True)
    try:
        run_dir.relative_to(root)
    except ValueError:
        die(f"run directory is outside the writable workspace: {run_dir}")
    paths = {
        name: run_dir / name
        for name in ("summary.json", "event_map.csv", "hits.csv")
    }
    for path in paths.values():
        if not path.is_file():
            die(f"required run input is missing: {path}")

    with paths["summary.json"].open(encoding="utf-8") as handle:
        summary = json.load(handle)
    if summary.get("status") != "COMPLETE":
        die(f"run summary status is not COMPLETE: {run_dir}")
    event_fields, maps = read_csv(paths["event_map.csv"], EVENT_MAP_REQUIRED)
    hit_fields, hits = read_csv(paths["hits.csv"], HITS_REQUIRED)

    sim_map: dict[int, dict[str, str]] = {}
    buckets: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: {"maps": [], "hits": []}
    )
    for row in maps:
        sim_id = i(row["sim_event_id"])
        if sim_id in sim_map:
            die(f"duplicate sim_event_id {sim_id} in {run_dir}/event_map.csv")
        sim_map[sim_id] = row
        key = base_original_key(row["group_key"])
        buckets[key]["maps"].append(row)

    weighted_total_eV = 0.0
    class_energy_eV: dict[str, list[float]] = defaultdict(list)
    for source_row, row in enumerate(hits, start=2):
        sim_id = i(row["sim_event_id"])
        if sim_id not in sim_map:
            die(f"HIT row {source_row} has unknown sim_event_id={sim_id}")
        mapped = sim_map[sim_id]
        for field in ("group_key", "event_order", "job_id", "event_id", "layer", "candidate"):
            if row[field] != mapped[field]:
                die(f"HIT/event_map {field} mismatch at hits.csv row {source_row}")
        surface = row["surface_class"]
        if surface not in {"sensor", "bath", "bulk"}:
            die(f"unsupported surface_class={surface!r} at hits.csv row {source_row}")
        weighted = f(row["weighted_energy_eV"])
        calculated_weighted = f(row["energy_deposited_eV"]) * f(row["track_weight"])
        if not close(weighted, calculated_weighted, abs_tol=1e-7):
            die(f"weighted energy mismatch at hits.csv row {source_row}")
        arrival = f(row["arrival_from_group_ns"])
        if arrival < -1e-9:
            die(f"negative group-relative arrival at hits.csv row {source_row}")
        if not close(
            arrival,
            f(row["end_time_ns"]) - f(mapped["reference_time_ns"]),
            abs_tol=1e-7,
        ):
            die(f"arrival/reference time mismatch at hits.csv row {source_row}")
        enriched: dict[str, Any] = dict(row)
        enriched["weighted_energy_eV"] = weighted
        enriched["arrival_from_group_ns"] = arrival
        enriched["source_row"] = source_row
        key = base_original_key(row["group_key"])
        buckets[key]["hits"].append(enriched)
        weighted_total_eV += weighted
        class_energy_eV[surface].append(weighted)

    counts = summary.get("counts", {})
    if len(maps) != int(counts.get("groups", -1)):
        die("event_map row count does not match summary counts.groups")
    if sum(i(row["deposit_count"]) for row in maps) != int(counts.get("deposits", -1)):
        die("event_map deposit sum does not match summary counts.deposits")
    if sum(i(row["primary_packet_count"]) for row in maps) != int(
        counts.get("primary_packets", -1)
    ):
        die("event_map packet sum does not match summary counts.primary_packets")
    if len(hits) != int(counts.get("recorded_terminal_hits", -1)):
        die("hits.csv row count does not match summary terminal-hit count")

    map_input_eV = 1000.0 * math.fsum(f(row["input_energy_keV"]) for row in maps)
    energy_summary = summary.get("energy_eV", {})
    comparisons = {
        "input_weighted": map_input_eV,
        "sensor": math.fsum(class_energy_eV["sensor"]),
        "bath": math.fsum(class_energy_eV["bath"]),
        "bulk": math.fsum(class_energy_eV["bulk"]),
        "recorded_total": weighted_total_eV,
    }
    for name, actual in comparisons.items():
        if not close(actual, float(energy_summary.get(name, math.nan)), abs_tol=1e-5):
            die(f"raw {name} energy does not match summary.json in {run_dir}")

    return {
        "run_dir": run_dir,
        "summary": summary,
        "event_map_fields": event_fields,
        "hit_fields": hit_fields,
        "maps": maps,
        "hits": hits,
        "buckets": buckets,
        "input_paths": paths,
        "raw_energy_eV": comparisons,
    }


def aggregate_run(root: Path, loaded: dict[str, Any]) -> dict[str, Any]:
    run_dir: Path = loaded["run_dir"]
    summary = loaded["summary"]
    group = infer_group(summary, run_dir)
    run_id = run_dir.relative_to(root.resolve(strict=True)).as_posix()
    buckets = loaded["buckets"]
    ordered_keys = sorted(
        buckets,
        key=lambda key: (
            min(i(row["event_order"]) for row in buckets[key]["maps"]), key
        ),
    )

    event_rows: list[dict[str, Any]] = []
    channel_rows: list[dict[str, Any]] = []
    multi_layer_event_count = 0

    for event_index, key in enumerate(ordered_keys, start=1):
        maps = sorted(
            buckets[key]["maps"], key=lambda row: (i(row["layer"]), i(row["sim_event_id"]))
        )
        # Process chunks may split a large physical event.  Rebase every
        # terminal hit to the earliest reference among all merged segments so
        # timing quantiles remain physical-event-relative rather than
        # transport-chunk-relative.
        event_reference_ns = min(
            f(row["reference_time_ns"]) for row in buckets[key]["maps"]
        )
        rebased_hits = []
        for source_hit in buckets[key]["hits"]:
            hit = dict(source_hit)
            hit["arrival_from_group_ns"] = f(hit["end_time_ns"]) - event_reference_ns
            if hit["arrival_from_group_ns"] < -1e-7:
                die(f"negative event-relative arrival in event {key}")
            rebased_hits.append(hit)
        terminal_hits = sorted(
            rebased_hits,
            key=lambda row: (
                f(row["arrival_from_group_ns"]), i(row["layer"]),
                i(row["pixel_id"]), i(row["track_id"]), i(str(row["source_row"])),
            ),
        )
        layers = sorted({i(row["layer"]) for row in maps})
        if len(layers) > 1:
            multi_layer_event_count += 1
        event_order = i(only_consistent_text((row["event_order"] for row in maps), "event_order"))
        sample_id = only_consistent_text((row["sample_id"] for row in maps), "sample_id")
        job_id = only_consistent_text((row["job_id"] for row in maps), "job_id")
        event_id = i(only_consistent_text((row["event_id"] for row in maps), "event_id"))
        candidate = only_consistent_text((row["candidate"] for row in maps), "candidate")
        strict = i(only_consistent_text(
            (row["strict_recoil_event"] for row in maps), "strict_recoil_event"
        ))
        direct_tes_keV = only_consistent_float(
            (f(row["direct_tes_keV"]) for row in maps), "direct_tes_keV"
        )
        bgo_total_keV = only_consistent_float(
            (f(row["bgo_total_keV"]) for row in maps), "bgo_total_keV"
        )
        input_keV = math.fsum(f(row["input_energy_keV"]) for row in maps)
        input_eV = 1000.0 * input_keV
        primary_packets = sum(i(row["primary_packet_count"]) for row in maps)

        energy_eV = {
            surface: math.fsum(
                float(hit["weighted_energy_eV"])
                for hit in terminal_hits if hit["surface_class"] == surface
            )
            for surface in ("sensor", "bath", "bulk")
        }
        recorded_eV = math.fsum(energy_eV.values())
        sensor_hits = [hit for hit in terminal_hits if hit["surface_class"] == "sensor"]
        timing = timing_summary(sensor_hits)

        channels: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for hit in sensor_hits:
            pixel_id = i(hit["pixel_id"])
            if pixel_id < 0:
                die(f"sensor terminal has negative pixel_id in event {key}")
            channels[(i(hit["layer"]), pixel_id)].append(hit)
        channel_energies_eV = {
            channel: math.fsum(float(hit["weighted_energy_eV"]) for hit in hits)
            for channel, hits in channels.items()
        }
        sensor_eV = energy_eV["sensor"]
        multiplicity = len(channel_energies_eV)
        effective_multiplicity = (
            sensor_eV * sensor_eV
            / math.fsum(value * value for value in channel_energies_eV.values())
            if sensor_eV > 0.0 else 0.0
        )
        dominant = (
            max(channel_energies_eV, key=lambda channel: channel_energies_eV[channel])
            if channel_energies_eV else None
        )

        closure = recorded_eV / input_eV
        eta = sensor_eV / input_eV
        reconstructed_keV = direct_tes_keV + sensor_eV / 1000.0
        roi_probability = gaussian_interval_probability(reconstructed_keV)
        uncertainty = packet_mc_uncertainty(
            terminal_hits, primary_packets, input_eV
        )
        eta_se = uncertainty["eta_standard_error"]
        sensor_fraction_denominator = sensor_eV if sensor_eV > 0 else 1.0

        event_row = {
            "run_id": run_id,
            "group": group,
            "event_index": event_index,
            "source_event_order": event_order,
            "original_event_key": key,
            "sample_id": sample_id,
            "job_id": job_id,
            "event_id": event_id,
            "candidate": candidate,
            "strict_recoil_event": strict,
            "layers": layers,
            "merged_layer_group_count": len(maps),
            "deposit_count": sum(i(row["deposit_count"]) for row in maps),
            "primary_packet_count": primary_packets,
            "terminal_branch_count": len(terminal_hits),
            "si_input_keV": input_keV,
            "sensor_keV": sensor_eV / 1000.0,
            "bath_keV": energy_eV["bath"] / 1000.0,
            "bulk_keV": energy_eV["bulk"] / 1000.0,
            "recorded_total_keV": recorded_eV / 1000.0,
            "energy_closure_fraction": closure,
            "sensor_eta": eta,
            "bath_fraction": energy_eV["bath"] / input_eV,
            "bulk_fraction": energy_eV["bulk"] / input_eV,
            "sensor_terminal_hit_count": len(sensor_hits),
            "sensor_channel_hit_multiplicity": multiplicity,
            "sensor_channel_effective_multiplicity_ipr": effective_multiplicity,
            "dominant_sensor_channel": (
                f"L{dominant[0]}:P{dominant[1]}" if dominant else None
            ),
            "dominant_sensor_channel_keV": (
                channel_energies_eV[dominant] / 1000.0 if dominant else 0.0
            ),
            "sensor_arrival_q10_ns": timing["q10_ns"],
            "sensor_arrival_q50_ns": timing["q50_ns"],
            "sensor_arrival_q90_ns": timing["q90_ns"],
            "sensor_arrival_q99_ns": timing["q99_ns"],
            "sensor_prompt_lt_1us_keV": float(timing["prompt_eV"]) / 1000.0,
            "sensor_intermediate_1_to_10us_keV":
                float(timing["intermediate_eV"]) / 1000.0,
            "sensor_late_ge_10us_keV": float(timing["late_eV"]) / 1000.0,
            "sensor_prompt_fraction": float(timing["prompt_eV"]) / sensor_fraction_denominator,
            "sensor_intermediate_fraction":
                float(timing["intermediate_eV"]) / sensor_fraction_denominator,
            "sensor_late_fraction": float(timing["late_eV"]) / sensor_fraction_denominator,
            "direct_tes_keV": direct_tes_keV,
            "reconstructed_mean_keV": reconstructed_keV,
            "eta_mc_terminal_effective_count": uncertainty["terminal_effective_count"],
            "eta_mc_conservative_effective_count":
                uncertainty["conservative_effective_count"],
            "eta_mc_standard_error": eta_se,
            "reconstructed_mean_mc_standard_error_keV": (
                input_keV * float(eta_se) if eta_se is not None else None
            ),
            "gaussian_fwhm_keV": FWHM_KEV,
            "gaussian_sigma_keV": SIGMA_KEV,
            "roi_low_keV": ROI_LOW_KEV,
            "roi_high_keV_exclusive": ROI_HIGH_KEV,
            "gaussian_roi_probability": roi_probability,
            "expected_roi_count": roi_probability,
            "expected_roi_rate_per_s": roi_probability / TT_S,
        }
        event_rows.append(event_row)

        for layer_pixel in sorted(channels):
            layer, pixel_id = layer_pixel
            channel_hits = channels[layer_pixel]
            channel_eV = channel_energies_eV[layer_pixel]
            channel_timing = timing_summary(channel_hits)
            channel_rows.append({
                "run_id": run_id,
                "group": group,
                "event_index": event_index,
                "source_event_order": event_order,
                "original_event_key": key,
                "sample_id": sample_id,
                "job_id": job_id,
                "event_id": event_id,
                "candidate": candidate,
                "layer": layer,
                "pixel_id": pixel_id,
                "channel_id": f"L{layer}:P{pixel_id}",
                "sensor_energy_keV": channel_eV / 1000.0,
                "fraction_of_event_sensor_energy": channel_eV / sensor_eV,
                "fraction_of_si_input_energy": channel_eV / input_eV,
                "terminal_hit_count": len(channel_hits),
                "arrival_q10_ns": channel_timing["q10_ns"],
                "arrival_q50_ns": channel_timing["q50_ns"],
                "arrival_q90_ns": channel_timing["q90_ns"],
                "arrival_q99_ns": channel_timing["q99_ns"],
                "prompt_lt_1us_keV": float(channel_timing["prompt_eV"]) / 1000.0,
                "intermediate_1_to_10us_keV":
                    float(channel_timing["intermediate_eV"]) / 1000.0,
                "late_ge_10us_keV": float(channel_timing["late_eV"]) / 1000.0,
            })

    # Event aggregation must reproduce the raw run totals after layer merging.
    if not close(
        1000.0 * math.fsum(row["si_input_keV"] for row in event_rows),
        loaded["raw_energy_eV"]["input_weighted"], abs_tol=1e-5,
    ):
        die("event-level input energy does not close to raw run total")
    for surface in ("sensor", "bath", "bulk"):
        if not close(
            1000.0 * math.fsum(row[f"{surface}_keV"] for row in event_rows),
            loaded["raw_energy_eV"][surface], abs_tol=1e-5,
        ):
            die(f"event-level {surface} energy does not close to raw run total")

    events_path = run_dir / "events.csv"
    channels_path = run_dir / "channels.csv"
    write_table(events_path, EVENT_CSV_FIELDS, event_rows)
    write_table(channels_path, CHANNEL_CSV_FIELDS, channel_rows)

    expected_count = math.fsum(row["expected_roi_count"] for row in event_rows)
    total_sensor_keV = math.fsum(row["sensor_keV"] for row in event_rows)
    total_input_keV = math.fsum(row["si_input_keV"] for row in event_rows)
    total_recorded_keV = math.fsum(row["recorded_total_keV"] for row in event_rows)
    analysis = {
        "schema_version": 1,
        "status": "PASS__G4CMP_RUN_ANALYZED",
        "run_id": run_id,
        "group": group,
        "input_files": {
            name: {
                "path": path.relative_to(root.resolve(strict=True)).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in loaded["input_paths"].items()
        },
        "engine": summary.get("engine", {}),
        "configuration": summary.get("configuration", {}),
        "definitions": {
            "original_event_merge": (
                "event_map group_key with terminal |L{layer} removed; all layer groups "
                "having that original key are summed, while direct_tes_keV is added once"
            ),
            "sensor_eta": "sensor weighted terminal energy / Si input energy",
            "hit_multiplicity": "number of L{layer}:P{pixel} channels with positive sensor energy",
            "effective_multiplicity": (
                "energy inverse-participation ratio: (sum channel E)^2/sum(channel E^2)"
            ),
            "arrival_quantiles": (
                "inverse-CDF quantiles of arrival_from_group_ns weighted by sensor "
                "weighted_energy_eV"
            ),
            "time_bands": (
                "prompt <1 us; intermediate 1 us <= t <10 us; late >=10 us"
            ),
            "reconstructed_mean": "direct_tes_keV + sensor_keV",
            "roi_probability": (
                "Gaussian integral over [510.58,511.42) keV centered on reconstructed_mean"
            ),
            "packet_mc_eta_standard_error": (
                "Weighted Bernoulli sensor-vs-nonsensor plug-in SE. Terminal branches are "
                "energy-weighted; Kish branch n_eff is capped by independently launched "
                "primary_packet_count because hits.csv lacks branch ancestry. Primary "
                "packets are assumed independent. This is conservative against treating "
                "down-conversion branches as independent, but excludes surface/model/"
                "geometry systematics and has zero plug-in SE at eta boundaries."
            ),
        },
        "response": {
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": SIGMA_KEV,
            "roi_keV_half_open": [ROI_LOW_KEV, ROI_HIGH_KEV],
            "equivalent_time_s": TT_S,
        },
        "counts": {
            "event_map_layer_groups": len(loaded["maps"]),
            "original_events_after_layer_merge": len(event_rows),
            "multi_layer_original_events": multi_layer_event_count,
            "terminal_branches": len(loaded["hits"]),
            "event_channel_rows": len(channel_rows),
            "strict_recoil_events": sum(row["strict_recoil_event"] for row in event_rows),
            "candidate_counts": dict(sorted(Counter(
                row["candidate"] for row in event_rows if row["candidate"]
            ).items())),
        },
        "energy_keV": {
            "si_input": total_input_keV,
            "sensor": total_sensor_keV,
            "bath": math.fsum(row["bath_keV"] for row in event_rows),
            "bulk": math.fsum(row["bulk_keV"] for row in event_rows),
            "recorded_total": total_recorded_keV,
            "global_sensor_eta": total_sensor_keV / total_input_keV,
            "global_closure_fraction": total_recorded_keV / total_input_keV,
        },
        "roi_expectation": {
            "sum_expected_counts": expected_count,
            "rate_per_s": expected_count / TT_S,
            "equivalent_time_s": TT_S,
        },
        "output_files": {
            "events.csv": {
                "rows": len(event_rows), "sha256": sha256(events_path),
            },
            "channels.csv": {
                "rows": len(channel_rows), "sha256": sha256(channels_path),
            },
        },
        "self_checks": {
            "input_summary_status_complete": True,
            "raw_csv_counts_match_summary": True,
            "raw_csv_energies_match_summary": True,
            "weighted_terminal_energy_formula_matches": True,
            "arrival_reference_times_match": True,
            "multi_layer_groups_merged_by_original_key": True,
            "direct_tes_added_once_after_layer_merge": True,
            "event_energy_sums_match_run_totals": True,
            "channel_energy_sums_match_event_sensor_energy": all(
                close(
                    math.fsum(
                        channel["sensor_energy_keV"] for channel in channel_rows
                        if channel["event_index"] == event["event_index"]
                    ),
                    event["sensor_keV"],
                )
                for event in event_rows
            ),
            "all_required_checks_pass": True,
        },
        "events": event_rows,
        "channels": channel_rows,
    }
    if not analysis["self_checks"]["channel_energy_sums_match_event_sensor_energy"]:
        die("channel energies do not sum to event sensor energies")
    analysis_path = run_dir / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return analysis


def write_cross_run_summary(
    root: Path, output_path: Path, analyses: list[dict[str, Any]]
) -> None:
    root = root.resolve(strict=True)
    output_path = output_path if output_path.is_absolute() else root / output_path
    output_path = output_path.resolve()
    try:
        output_path.relative_to(root)
    except ValueError:
        die(f"cross-run output is outside workspace: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"run_count": 0, "event_records": 0, "sum_expected_counts": 0.0}
    )
    identity_counts: Counter[tuple[str, str]] = Counter()
    run_entries = []
    for analysis in analyses:
        group = analysis["group"]
        grouped[group]["run_count"] = int(grouped[group]["run_count"]) + 1
        grouped[group]["event_records"] = (
            int(grouped[group]["event_records"])
            + int(analysis["counts"]["original_events_after_layer_merge"])
        )
        grouped[group]["sum_expected_counts"] = (
            float(grouped[group]["sum_expected_counts"])
            + float(analysis["roi_expectation"]["sum_expected_counts"])
        )
        for event in analysis["events"]:
            identity_counts[(group, event["original_event_key"])] += 1
        analysis_path = root / analysis["run_id"] / "analysis.json"
        run_entries.append({
            "run_id": analysis["run_id"],
            "group": group,
            "event_records": analysis["counts"]["original_events_after_layer_merge"],
            "sum_expected_counts": analysis["roi_expectation"]["sum_expected_counts"],
            "rate_per_s": analysis["roi_expectation"]["rate_per_s"],
            "analysis_sha256": sha256(analysis_path),
        })
    duplicate_identities = sorted(
        {f"{group}|{key}": count for (group, key), count in identity_counts.items() if count > 1}.items()
    )
    group_rows = {
        group: {
            **values,
            "rate_per_s": float(values["sum_expected_counts"]) / TT_S,
        }
        for group, values in sorted(grouped.items())
    }
    total_expected = math.fsum(
        float(analysis["roi_expectation"]["sum_expected_counts"])
        for analysis in analyses
    )
    cross = {
        "schema_version": 1,
        "status": "PASS__G4CMP_CROSS_RUN_SUMMARY",
        "aggregation_semantics": (
            "Run-local event expectations are summed as distinct MC evaluations. "
            "Overlapping (group, original_event_key) records are reported, not silently "
            "deduplicated or averaged."
        ),
        "equivalent_time_s": TT_S,
        "run_count": len(analyses),
        "runs": run_entries,
        "groups": group_rows,
        "overlapping_group_original_keys": dict(duplicate_identities),
        "total": {
            "event_records": sum(
                int(analysis["counts"]["original_events_after_layer_merge"])
                for analysis in analyses
            ),
            "sum_expected_counts": total_expected,
            "rate_per_s": total_expected / TT_S,
        },
    }
    output_path.write_text(
        json.dumps(cross, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument(
        "--workspace", type=Path,
        default=Path(__file__).resolve().parents[1],
        help="writable workspace root",
    )
    parser.add_argument(
        "--cross-run-summary", "--combined-output", dest="cross_run_summary",
        type=Path, default=None,
        help="optional cross-run summary JSON path (relative paths are under workspace)",
    )
    args = parser.parse_args()
    root = args.workspace.resolve(strict=True)
    analyses = []
    for raw_dir in args.run_dirs:
        run_dir = raw_dir if raw_dir.is_absolute() else root / raw_dir
        loaded = load_and_validate_run(root, run_dir)
        analysis = aggregate_run(root, loaded)
        analyses.append(analysis)
        print(
            f"PASS {analysis['run_id']}: "
            f"{analysis['counts']['original_events_after_layer_merge']} events, "
            f"ROI expected={analysis['roi_expectation']['sum_expected_counts']:.12g}, "
            f"rate={analysis['roi_expectation']['rate_per_s']:.12g}/s"
        )
    if args.cross_run_summary is not None:
        write_cross_run_summary(root, args.cross_run_summary, analyses)
        print(f"PASS cross-run summary: {args.cross_run_summary}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
