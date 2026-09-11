#!/usr/bin/env python3
"""Offline-only M-sampling audit for the retained S3d-O8 package-44 data.

This program intentionally has no subprocess import and no simulation entry point.
It only:

1. verifies frozen hashes;
2. reproduces the exact Python ``random.Random`` weighted source draw in memory;
3. checks the retained M=50,000 source cards block-by-block;
4. resamples the existing weighted tables in memory for source-layer diagnostics;
5. reconnects the retained primary-response selected lineage to weighted-table rows;
6. performs explicitly conditional importance reweighting of those same physical
   events; and
7. summarizes the already-retained 64-response-seed aggregate CSV.

It does not run Cosima, a package runner, transport, compilation, or a download.
"""

from __future__ import annotations

import bisect
import csv
import functools
import gc
import hashlib
import gzip
import importlib.util
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
ROOT = SCRIPT.parents[4]
CONFIG_PATH = PACKAGE / "config/offline_validation_config.json"
DATA = PACKAGE / "data"
SOURCE_ONLY = PACKAGE / "source_only"

PARTICLE_RE = re.compile(r"^(RP_\d+)\.ParticleType\s+(\d+)\s*$")
BEAM_RE = re.compile(
    r"^(RP_\d+)\.Beam\s+PointSource\s+"
    r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$"
)
FLUX_RE = re.compile(r"^(RP_\d+)\.Flux\s+([-+0-9.eE]+)\s*$")
TRIGGERS_RE = re.compile(r"^DecayRun\.Triggers\s+(\d+)\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$")


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def finite_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return value


def verify_hashes(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for relative, expected in sorted(config["expected_sha256"].items()):
        path = ROOT / relative
        exists = path.is_file()
        actual = sha256(path) if exists else None
        status = "PASS" if actual == expected else "FAIL"
        rows.append(
            {
                "status": status,
                "path": relative,
                "size_bytes": path.stat().st_size if exists else None,
                "expected_sha256": expected,
                "actual_sha256": actual,
            }
        )
        if status != "PASS":
            failures.append(relative)
    write_csv(
        DATA / "input_hash_audit.csv",
        rows,
        ["status", "path", "size_bytes", "expected_sha256", "actual_sha256"],
    )
    if failures:
        raise AuditError(f"protected input hash failures: {failures}")
    return rows


def family_path(config: dict[str, Any], kind: str, family: str) -> Path:
    return ROOT / config["path_templates"][kind].format(family=family)


def resolve_recorded_path(value: Any) -> Path:
    path = Path(str(value).strip())
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_population(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for csv_line, row in enumerate(csv.DictReader(handle), start=2):
            weight = float(row["sample_weight"])
            if not math.isfinite(weight) or weight <= 0.0:
                raise AuditError(f"{path}: invalid weight on CSV line {csv_line}")
            rows.append(
                {
                    "csv_line": csv_line,
                    "VN": row["VN"],
                    "ZA": int(row["ZA"]),
                    "exc_keV": float(row["exc_keV"]),
                    "x_cm": float(row["x_cm"]),
                    "y_cm": float(row["y_cm"]),
                    "z_cm": float(row["z_cm"]),
                    "weight": weight,
                }
            )
    if not rows:
        raise AuditError(f"empty weighted table: {path}")
    weights = [float(row["weight"]) for row in rows]
    total = math.fsum(weights)
    probabilities = [weight / total for weight in weights]
    cdf: list[float] = []
    acc = 0.0
    # This deliberately matches the retained builder's sequential CDF sum.
    for weight in weights:
        acc += weight
        cdf.append(acc)
    positions = {
        (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
        for row in rows
    }
    return {
        "rows": rows,
        "weights": weights,
        "probabilities": probabilities,
        "total": total,
        "cdf": cdf,
        "unique_positions": len(positions),
    }


def draw_counts(population: dict[str, Any], m: int, seed: int) -> tuple[list[int], list[int]]:
    cdf = population["cdf"]
    total = math.fsum(population["weights"])
    rng = random.Random(seed)
    counts = [0] * len(cdf)
    chosen: list[int] = []
    for _ in range(m):
        index = bisect.bisect_left(cdf, rng.random() * total)
        if index >= len(cdf):
            index = len(cdf) - 1
        counts[index] += 1
        chosen.append(index)
    return counts, chosen


def parse_source_card(path: Path) -> dict[str, Any]:
    particles: dict[str, int] = {}
    beams: dict[str, tuple[float, float, float]] = {}
    fluxes: dict[str, float] = {}
    triggers: int | None = None
    geometry: str | None = None
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            match = PARTICLE_RE.match(line)
            if match:
                particles[match.group(1)] = int(match.group(2))
                continue
            match = BEAM_RE.match(line)
            if match:
                beams[match.group(1)] = tuple(float(match.group(i)) for i in (2, 3, 4))
                continue
            match = FLUX_RE.match(line)
            if match:
                fluxes[match.group(1)] = float(match.group(2))
                continue
            match = TRIGGERS_RE.match(line)
            if match:
                triggers = int(match.group(1))
                continue
            match = GEOMETRY_RE.match(line)
            if match:
                geometry = match.group(1)
    names = sorted(particles, key=lambda name: int(name.split("_")[1]))
    if set(names) != set(beams) or set(names) != set(fluxes):
        raise AuditError(f"source card has incomplete PointSource blocks: {path}")
    return {
        "names": names,
        "particles": particles,
        "beams": beams,
        "fluxes": fluxes,
        "triggers": triggers,
        "geometry": geometry,
    }


def compare_source_replay(
    population: dict[str, Any], chosen: list[int], source: dict[str, Any]
) -> dict[str, Any]:
    if len(chosen) != len(source["names"]):
        raise AuditError(
            f"source block count={len(source['names'])} differs from replay={len(chosen)}"
        )
    mismatches = 0
    first_mismatch: dict[str, Any] | None = None
    for offset, (name, index) in enumerate(zip(source["names"], chosen)):
        row = population["rows"][index]
        expected_position = (row["x_cm"], row["y_cm"], row["z_cm"])
        actual_position = source["beams"][name]
        same = int(row["ZA"]) == source["particles"][name] and all(
            abs(a - b) <= 5.0e-10 for a, b in zip(expected_position, actual_position)
        )
        if not same:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = {
                    "block_offset": offset,
                    "name": name,
                    "table_index": index,
                    "expected_ZA": row["ZA"],
                    "actual_ZA": source["particles"][name],
                    "expected_position_cm": expected_position,
                    "actual_position_cm": actual_position,
                }
    flux_values = sorted(set(source["fluxes"].values()))
    return {
        "blocks": len(chosen),
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "uniform_flux": len(flux_values) == 1,
        "serialized_flux_per_block_Bq": flux_values[0] if len(flux_values) == 1 else None,
        "serialized_flux_sum_Bq": math.fsum(source["fluxes"].values()),
    }


def jsd_sequences(p_values: Iterable[float], q_values: Iterable[float]) -> float | None:
    p = list(p_values)
    q = list(q_values)
    p_total = math.fsum(p)
    q_total = math.fsum(q)
    if p_total <= 0.0 or q_total <= 0.0 or len(p) != len(q):
        return None
    result = 0.0
    for left, right in zip(p, q):
        left /= p_total
        right /= q_total
        middle = 0.5 * (left + right)
        if left > 0.0:
            result += 0.5 * left * math.log(left / middle)
        if right > 0.0:
            result += 0.5 * right * math.log(right / middle)
    return result


def jsd_mappings(left: dict[Any, float], right: dict[Any, float]) -> float | None:
    keys = sorted(set(left) | set(right), key=str)
    return jsd_sequences(
        (float(left.get(key, 0.0)) for key in keys),
        (float(right.get(key, 0.0)) for key in keys),
    )


def top_mass_set(values: dict[Any, float], threshold: float) -> set[Any]:
    total = math.fsum(values.values())
    if total <= 0.0:
        return set()
    selected: set[Any] = set()
    cumulative = 0.0
    for key, value in sorted(values.items(), key=lambda item: (-item[1], str(item[0]))):
        if value <= 0.0:
            continue
        selected.add(key)
        cumulative += value / total
        if cumulative >= threshold:
            break
    return selected


def jaccard(left: set[Any], right: set[Any]) -> float | None:
    union = left | right
    return len(left & right) / len(union) if union else None


def expected_inclusion(probability: float, m: int) -> float:
    if probability >= 1.0:
        return 1.0
    return -math.expm1(m * math.log1p(-probability))


def source_metrics(
    family: str,
    population: dict[str, Any],
    counts: list[int],
    m: int,
    seed: int,
    top_fraction: float,
) -> dict[str, Any]:
    rows = population["rows"]
    p = population["probabilities"]
    empirical = [count / m for count in counts]
    groups_target: dict[tuple[str, int], float] = defaultdict(float)
    groups_sample: dict[tuple[str, int], float] = defaultdict(float)
    for row, probability, count in zip(rows, p, counts):
        key = (str(row["VN"]), int(row["ZA"]))
        groups_target[key] += probability
        if count:
            groups_sample[key] += count / m
    covered_rows = [index for index, count in enumerate(counts) if count]
    covered_groups = set(groups_sample)
    row_mass_coverage = math.fsum(p[index] for index in covered_rows)
    group_mass_coverage = math.fsum(groups_target[key] for key in covered_groups)
    row_tv = 0.5 * math.fsum(abs(left - right) for left, right in zip(p, empirical))
    group_keys = sorted(groups_target, key=str)
    group_tv = 0.5 * math.fsum(
        abs(groups_target[key] - groups_sample.get(key, 0.0)) for key in group_keys
    )
    radii = [math.hypot(row["x_cm"], row["y_cm"]) for row in rows]
    z_values = [float(row["z_cm"]) for row in rows]
    target_r = math.fsum(probability * value for probability, value in zip(p, radii))
    sample_r = math.fsum(count * value for count, value in zip(counts, radii)) / m
    target_z = math.fsum(probability * value for probability, value in zip(p, z_values))
    sample_z = math.fsum(count * value for count, value in zip(counts, z_values)) / m
    target_z_var = math.fsum(
        probability * (value - target_z) ** 2 for probability, value in zip(p, z_values)
    )
    expected_unique = math.fsum(expected_inclusion(probability, m) for probability in p)
    expected_mass = math.fsum(
        probability * expected_inclusion(probability, m) for probability in p
    )
    target_top = top_mass_set(groups_target, top_fraction)
    sample_top = top_mass_set(groups_sample, top_fraction)
    return {
        "family": family,
        "m": m,
        "source_seed": seed,
        "population_rows": len(rows),
        "population_groups_vn_za": len(groups_target),
        "unique_rows_drawn": len(covered_rows),
        "unique_groups_vn_za_drawn": len(covered_groups),
        "target_row_mass_coverage": row_mass_coverage,
        "target_row_mass_unseen": 1.0 - row_mass_coverage,
        "target_group_mass_coverage": group_mass_coverage,
        "target_group_mass_unseen": 1.0 - group_mass_coverage,
        "expected_unique_rows": expected_unique,
        "expected_target_row_mass_coverage": expected_mass,
        "row_total_variation": row_tv,
        "row_jsd_nats": jsd_sequences(p, empirical),
        "group_total_variation": group_tv,
        "group_jsd_nats": jsd_mappings(groups_target, groups_sample),
        "group_top90_jaccard": jaccard(target_top, sample_top),
        "target_mean_r_cm": target_r,
        "sample_mean_r_cm": sample_r,
        "mean_r_relative_error": (sample_r - target_r) / target_r if target_r else None,
        "target_mean_z_cm": target_z,
        "sample_mean_z_cm": sample_z,
        "mean_z_error_target_sd": (
            (sample_z - target_z) / math.sqrt(target_z_var) if target_z_var > 0.0 else None
        ),
        "empirical_row_ess": 1.0 / math.fsum(value * value for value in empirical),
    }


def selected_group_contributions(
    events: list[dict[str, Any]], contributions: list[float]
) -> dict[tuple[str, str, int], float]:
    result: dict[tuple[str, str, int], float] = defaultdict(float)
    for event, contribution in zip(events, contributions):
        key = (
            str(event["incident_family"]),
            str(event["source_parent_volume"]),
            int(event["source_parent_ZA"]),
        )
        result[key] += contribution
    return dict(result)


def conditional_reweight(
    family: str,
    events: list[dict[str, Any]],
    population: dict[str, Any],
    baseline_counts: list[int],
    candidate_counts: list[int],
    m: int,
    seed: int,
    baseline_m: int,
    top_fraction: float,
) -> tuple[dict[str, Any], list[float], dict[tuple[str, str, int], float]]:
    outside_draws = sum(
        count for count, baseline in zip(candidate_counts, baseline_counts) if baseline == 0
    )
    target_outside = math.fsum(
        probability
        for probability, baseline in zip(population["probabilities"], baseline_counts)
        if baseline == 0
    )
    base_contributions = [float(event["event_weight_cps"]) for event in events]
    candidate_contributions: list[float] = []
    ratios: list[float] = []
    for event in events:
        index = int(event["weighted_table_row"]) - 2
        if index < 0 or index >= len(baseline_counts):
            raise AuditError(f"{family}: invalid weighted_table_row={event['weighted_table_row']}")
        baseline = baseline_counts[index]
        if baseline <= 0:
            raise AuditError(
                f"{family}: selected event row {index} is absent from retained source draw"
            )
        ratio = (candidate_counts[index] / m) / (baseline / baseline_m)
        ratios.append(ratio)
        candidate_contributions.append(float(event["event_weight_cps"]) * ratio)
    base_rate = math.fsum(base_contributions)
    candidate_rate = math.fsum(candidate_contributions)
    represented_fraction = 1.0 - outside_draws / m
    hajek_rate = (
        candidate_rate / represented_fraction if represented_fraction > 0.0 else None
    )
    base_groups = selected_group_contributions(events, base_contributions)
    candidate_groups = selected_group_contributions(events, candidate_contributions)
    positive = [value for value in candidate_contributions if value > 0.0]
    event_ess = (
        math.fsum(positive) ** 2 / math.fsum(value * value for value in positive)
        if positive
        else 0.0
    )
    record = {
        "family": family,
        "m": m,
        "source_seed": seed,
        "primary_selected_physical_events": len(events),
        "baseline_primary_selected_rate_cps": base_rate,
        "conditional_reweighted_rate_cps": candidate_rate,
        "conditional_rate_ratio_to_baseline": candidate_rate / base_rate if base_rate else None,
        "candidate_draw_fraction_on_retained_row_support": represented_fraction,
        "conditional_hajek_rate_cps": hajek_rate,
        "conditional_hajek_rate_ratio_to_baseline": hajek_rate / base_rate
        if hajek_rate is not None and base_rate
        else None,
        "candidate_draw_fraction_outside_retained_row_support": outside_draws / m,
        "fixed_target_row_mass_outside_retained_support": target_outside,
        "selected_events_with_positive_candidate_weight": sum(ratio > 0.0 for ratio in ratios),
        "selected_event_importance_ess": event_ess,
        "max_selected_event_importance_ratio": max(ratios) if ratios else None,
        "selected_contribution_group_jsd_nats_vs_baseline": jsd_mappings(
            base_groups, candidate_groups
        ),
        "selected_contribution_top90_jaccard_vs_baseline": jaccard(
            top_mass_set(base_groups, top_fraction),
            top_mass_set(candidate_groups, top_fraction),
        ),
        "interpretation": "conditional_on_retained_transport_and_observed_row_support",
    }
    return record, candidate_contributions, candidate_groups


def load_dynamic_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot import analysis module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def replay_response_selected_lineage(
    config: dict[str, Any], primary_lineage: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Replay the retained analysis response, never transport, for all 64 seeds."""
    response_path = ROOT / config["authorities"]["response_summary"]
    response_authority = load_json(response_path)
    implementation = ROOT / response_authority["input_authorities"][
        "response_implementation"
    ]
    module_name = "m04_wp1_readonly_response_replay"
    module = load_dynamic_module(module_name, implementation)
    closure = module.load_module(
        "m04_wp1_readonly_response_kernel", module.RETAINED_RESPONSE_CODE
    )
    selection, disk = module.load_selection()
    print("[offline-response] loading retained event catalog", flush=True)
    main_catalog, lineage = module.compact_main(closure)
    with (ROOT / config["authorities"]["response_replicas"]).open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        replica_rows = {
            int(row["replica_index"]): row for row in csv.DictReader(handle)
        }
    expected_replicas = int(
        config["offline_event_analysis"]["response_seed_replicas"]
    )
    if len(replica_rows) != expected_replicas:
        raise AuditError("retained response replica CSV does not contain 64 rows")
    records: list[dict[str, Any]] = []
    per_seed: list[dict[str, Any]] = []
    for index in range(expected_replicas):
        seed = int(module.PRIMARY_SEED + index * module.SEED_STRIDE)
        # Generate the response on the complete retained catalogue so that the
        # seeded random-number sequence is bit-for-bit identical to the frozen
        # authority.  Selection work is then restricted to delayed events:
        # prompt/science classifications cannot affect delayed W511 lineage and
        # made a 64-seed read-only replay unnecessarily expensive.
        np = module.np
        hits, totals, multiplicity = closure.measured_hits(
            main_catalog,
            seed,
            apply_response=True,
            apply_threshold=True,
        )
        delayed = main_catalog.stream == "delayed"
        broad_lo, broad_hi = module.WINDOWS["broad_480_550"]
        broad_active = (
            delayed
            & (totals >= broad_lo)
            & (totals < broad_hi)
            & (main_catalog.active_keV < module.ACTIVE_THRESHOLD_KEV)
        )
        keep = np.zeros(len(totals), dtype=bool)
        one = broad_active & (multiplicity == 1)
        keep[one] = True
        many = broad_active & (multiplicity > int(selection.MAX_ENUM_HITS))
        keep[many] = True
        complex_indices = np.flatnonzero(
            broad_active
            & (multiplicity >= 2)
            & (multiplicity <= int(selection.MAX_ENUM_HITS))
        )
        for event_index in complex_indices:
            accepted, _classification = selection.side_keep_from_hits(
                closure._event_hits(main_catalog, int(event_index), hits),
                disk,
                "keep",
            )
            keep[event_index] = bool(accepted)
        w_lo, w_hi = module.WINDOWS["w2_510p58_511p42"]
        final = (
            delayed
            & (totals >= w_lo)
            & (totals < w_hi)
            & (main_catalog.active_keV < module.ACTIVE_THRESHOLD_KEV)
            & keep
        )
        selected = [
            {
                "incident_family": str(main_catalog.tag[event_index]),
                "source_file": str(lineage.source_file[event_index]),
                "local_id": int(lineage.local_id[event_index]),
                "event_weight_cps": float(main_catalog.rate_hz[event_index]),
            }
            for event_index in np.flatnonzero(final)
        ]
        retained = replica_rows[index]
        if seed != int(retained["response_seed"]):
            raise AuditError(f"response seed mismatch at replica {index}")
        if len(selected) != int(retained["delayed_final_events"]):
            raise AuditError(f"response selected count mismatch at replica {index}")
        family_counts = Counter(str(row["incident_family"]) for row in selected)
        for family in config["families"]:
            if family_counts[family] != int(
                retained[f"delayed_{family}_final_events"]
            ):
                raise AuditError(
                    f"response family count mismatch at replica {index}/{family}"
                )
        rate = math.fsum(float(row["event_weight_cps"]) for row in selected)
        if not math.isclose(
            rate,
            float(retained["delayed_final_cps"]),
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise AuditError(f"response selected rate mismatch at replica {index}")
        for row in selected:
            records.append(
                {
                    "replica_index": index,
                    "response_seed": seed,
                    "family": str(row["incident_family"]),
                    "source_file": str(row["source_file"]),
                    "local_id": int(row["local_id"]),
                    "event_weight_cps": float(row["event_weight_cps"]),
                }
            )
        per_seed.append(
            {
                "replica_index": index,
                "response_seed": seed,
                "selected_delayed_events": len(selected),
                "selected_delayed_rate_cps": rate,
            }
        )
        if (index + 1) % 8 == 0:
            print(
                f"[offline-response] replayed {index + 1}/{expected_replicas} seeds",
                flush=True,
            )
    primary_replayed = {
        (row["family"], int(row["local_id"]))
        for row in records
        if int(row["replica_index"]) == 0
    }
    primary_frozen = {
        (str(row["incident_family"]), int(row["local_id"]))
        for row in primary_lineage["lineage"]
    }
    if primary_replayed != primary_frozen:
        raise AuditError("event-level primary response replay differs from frozen lineage")
    audit = {
        "status": "PASS_EXACT_EVENT_LEVEL_REPLAY_OF_ALL_64_RETAINED_RESPONSE_SEEDS",
        "replicas": expected_replicas,
        "selected_event_occurrences": len(records),
        "unique_family_local_ids": len(
            {(row["family"], row["local_id"]) for row in records}
        ),
        "per_seed": per_seed,
        "transport_launched": False,
    }
    del main_catalog, lineage, closure, selection, disk, module
    sys.modules.pop(module_name, None)
    gc.collect()
    return records, audit


def poisson_cdf(count: int, mean: float) -> float:
    """Stable P[X<=count] for a Poisson random variable."""
    if count < 0:
        return 0.0
    if mean <= 0.0:
        return 1.0
    log_terms = [
        -mean + index * math.log(mean) - math.lgamma(index + 1.0)
        for index in range(count + 1)
    ]
    anchor = max(log_terms)
    return math.exp(anchor) * math.fsum(
        math.exp(value - anchor) for value in log_terms
    )


@functools.lru_cache(maxsize=None)
def poisson_mean_upper_95(count: int) -> float:
    """One-sided 95% Garwood-equivalent upper mean, solved without SciPy."""
    if count < 0:
        raise AuditError("Poisson count cannot be negative")
    alpha = 0.05
    lower = 0.0
    upper = max(1.0, count + 10.0 * math.sqrt(count + 1.0) + 10.0)
    while poisson_cdf(count, upper) > alpha:
        upper *= 2.0
    for _ in range(100):
        midpoint = 0.5 * (lower + upper)
        if poisson_cdf(count, midpoint) > alpha:
            lower = midpoint
        else:
            upper = midpoint
    return upper


def position_key_5(values: Iterable[float]) -> tuple[str, str, str]:
    value_list = [float(value) for value in values]
    return tuple(f"{value:.5f}" for value in value_list)  # type: ignore[return-value]


def position_bucket(values: Iterable[float]) -> tuple[int, int, int]:
    value_list = [float(value) for value in values]
    return tuple(math.floor(value / 1.0e-4) for value in value_list)  # type: ignore[return-value]


def scan_raw_sim_row_trials(
    family: str,
    sim: Path,
    population: dict[str, Any],
    source_block_counts: list[int],
    mapping_config: dict[str, Any],
    selected_ids: set[int],
    expected_events: int,
) -> tuple[list[int], list[int], dict[int, int], dict[str, Any]]:
    """Stream one retained SIM and uniquely map every IA INIT to source support.

    IA INIT is printed at five decimals and can be displaced from the six-decimal
    PointSource coordinate by the short initial radioactive-ion track.  Mapping
    therefore uses nearest and second-nearest distances among rows actually
    present in the retained source card (K>0), with an absolute displacement cap
    and explicit separation/ratio guards.  Exact-print-only coverage is retained
    as a diagnostic rather than imposed on all raw events.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    if len(source_block_counts) != len(population["rows"]):
        raise AuditError(f"{family}: source-block count vector length mismatch")
    support_indices = [
        index for index, count in enumerate(source_block_counts) if count > 0
    ]
    if not support_indices:
        raise AuditError(f"{family}: retained source support is empty")
    support_coordinates = np.asarray(
        [
            [
                population["rows"][index]["x_cm"],
                population["rows"][index]["y_cm"],
                population["rows"][index]["z_cm"],
            ]
            for index in support_indices
        ],
        dtype=np.float64,
    )
    tree = cKDTree(support_coordinates)
    self_distances, _self_indices = tree.query(
        support_coordinates, k=2, p=np.inf, workers=1
    )
    support_min_separation = (
        float(np.min(self_distances[:, 1]))
        if len(support_indices) >= 2
        else float("inf")
    )
    observed_positions = np.empty((expected_events, 3), dtype=np.float64)
    observed_init_za = np.empty(expected_events, dtype=np.int64)
    ids_seen = 0
    init_seen = 0
    duplicate_init = 0
    sequence_mismatches = 0
    current_id: int | None = None
    current_has_init = False
    print(f"[offline-raw-scan] {family}: start {sim}", flush=True)
    with gzip.open(sim, "rb") as handle:
        for raw in handle:
            if raw.startswith(b"ID "):
                fields = raw.split()
                current_id = int(fields[1]) if len(fields) >= 2 else None
                ids_seen += 1
                current_has_init = False
                if current_id != ids_seen:
                    sequence_mismatches += 1
                continue
            if not raw.startswith(b"IA INIT"):
                continue
            if current_id is None:
                raise AuditError(f"{family}: IA INIT before first ID")
            if current_has_init:
                duplicate_init += 1
                continue
            current_has_init = True
            init_seen += 1
            parts = [field.strip() for field in raw[7:].split(b";")]
            if len(parts) < 16:
                raise AuditError(f"{family}: malformed IA INIT at ID={current_id}")
            if init_seen > expected_events:
                raise AuditError(f"{family}: more IA INIT records than expected")
            observed_positions[init_seen - 1] = [
                float(parts[4]),
                float(parts[5]),
                float(parts[6]),
            ]
            observed_init_za[init_seen - 1] = int(parts[15])
    if ids_seen != expected_events or init_seen != expected_events:
        raise AuditError(
            f"{family}: ID/IA INIT cardinality mismatch before position mapping"
        )

    distances, local_neighbors = tree.query(
        observed_positions, k=2, p=np.inf, workers=1
    )
    if len(support_indices) == 1:
        nearest_distance = np.asarray(distances[:, 0], dtype=np.float64)
        second_distance = np.full(expected_events, np.inf, dtype=np.float64)
        nearest_local = np.asarray(local_neighbors[:, 0], dtype=np.int64)
    else:
        nearest_distance = np.asarray(distances[:, 0], dtype=np.float64)
        second_distance = np.asarray(distances[:, 1], dtype=np.float64)
        nearest_local = np.asarray(local_neighbors[:, 0], dtype=np.int64)
    second_gap = second_distance - nearest_distance

    # Pure source-card (six decimal) plus SIM IA INIT (five decimal) rounding
    # contributes at most 0.5e-6 + 0.5e-5 cm per axis.  The larger adaptive cap
    # allows the observed short radioactive-ion displacement but only if the
    # next source-support point remains decisively farther away.
    serialization_tolerance_cm = float(
        mapping_config["serialization_tolerance_cm_per_axis"]
    )
    retained_selected_tolerance_cm = float(
        mapping_config["retained_selected_lineage_tolerance_cm_per_axis"]
    )
    adaptive_displacement_cap_cm = float(
        mapping_config["adaptive_displacement_cap_cm_per_axis"]
    )
    minimum_second_gap_cm = float(
        mapping_config["minimum_second_nearest_gap_cm"]
    )
    minimum_second_to_first_ratio = float(
        mapping_config["minimum_second_to_first_distance_ratio"]
    )
    within_cap = nearest_distance <= adaptive_displacement_cap_cm
    separated = second_gap >= minimum_second_gap_cm
    ratio_clear = second_distance >= (
        minimum_second_to_first_ratio * np.maximum(nearest_distance, 1.0e-30)
    )
    accepted = within_cap & separated & ratio_clear

    mapped_full_indices = np.asarray(
        [support_indices[int(value)] for value in nearest_local], dtype=np.int64
    )
    mapped_parent_za = np.asarray(
        [int(population["rows"][int(index)]["ZA"]) for index in mapped_full_indices],
        dtype=np.int64,
    )
    init_equals_parent = observed_init_za == mapped_parent_za

    # IA INIT ZA is daughter/transport evidence in the retained mission-fold
    # contract, not always the sampled source-parent ZA.  Quantify what a hard
    # same-ZA nearest-neighbour rule would do, but never let it overwrite the
    # source-card coordinate authority.
    support_by_za: dict[int, list[int]] = defaultdict(list)
    for local_index, full_index in enumerate(support_indices):
        support_by_za[int(population["rows"][full_index]["ZA"])].append(local_index)
    same_za_support_available = np.zeros(expected_events, dtype=bool)
    same_za_adaptive_accepted = np.zeros(expected_events, dtype=bool)
    same_za_agrees_coordinate_parent = np.zeros(expected_events, dtype=bool)
    same_za_nearest_distance = np.full(expected_events, np.nan, dtype=np.float64)
    for init_za in np.unique(observed_init_za):
        event_mask = observed_init_za == init_za
        event_indices = np.flatnonzero(event_mask)
        candidate_local = support_by_za.get(int(init_za), [])
        if not candidate_local:
            continue
        same_za_support_available[event_indices] = True
        candidate_coordinates = support_coordinates[candidate_local]
        za_tree = cKDTree(candidate_coordinates)
        za_distances, za_neighbors = za_tree.query(
            observed_positions[event_indices], k=2, p=np.inf, workers=1
        )
        if len(candidate_local) == 1:
            za_first = np.asarray(za_distances[:, 0], dtype=np.float64)
            za_second = np.full(len(event_indices), np.inf, dtype=np.float64)
            za_nearest = np.asarray(za_neighbors[:, 0], dtype=np.int64)
        else:
            za_first = np.asarray(za_distances[:, 0], dtype=np.float64)
            za_second = np.asarray(za_distances[:, 1], dtype=np.float64)
            za_nearest = np.asarray(za_neighbors[:, 0], dtype=np.int64)
        same_za_nearest_distance[event_indices] = za_first
        za_accept = (
            (za_first <= adaptive_displacement_cap_cm)
            & ((za_second - za_first) >= minimum_second_gap_cm)
            & (
                za_second
                >= minimum_second_to_first_ratio * np.maximum(za_first, 1.0e-30)
            )
        )
        same_za_adaptive_accepted[event_indices] = za_accept
        za_full = np.asarray(
            [
                support_indices[candidate_local[int(local)]]
                for local in za_nearest
            ],
            dtype=np.int64,
        )
        same_za_agrees_coordinate_parent[event_indices] = (
            za_full == mapped_full_indices[event_indices]
        )
    accepted_full_indices = mapped_full_indices[accepted]
    counts_array = np.bincount(
        accepted_full_indices, minlength=len(population["rows"])
    )
    trials = [int(value) for value in counts_array.tolist()]
    nearest_all_counts_array = np.bincount(
        mapped_full_indices, minlength=len(population["rows"])
    )
    nearest_all_trials = [int(value) for value in nearest_all_counts_array.tolist()]
    selected_id_to_row: dict[int, int] = {}
    selected_rejected: list[int] = []
    for local_id in sorted(selected_ids):
        if local_id < 1 or local_id > expected_events or not bool(accepted[local_id - 1]):
            selected_rejected.append(local_id)
            continue
        selected_id_to_row[local_id] = int(mapped_full_indices[local_id - 1])
    missing_selected = sorted(selected_ids.difference(selected_id_to_row))
    rejected_indices = np.flatnonzero(~accepted)
    rejected_examples = [
        {
            "local_id": int(index + 1),
            "position_cm": observed_positions[index].tolist(),
            "nearest_distance_chebyshev_cm": float(nearest_distance[index]),
            "second_nearest_distance_chebyshev_cm": float(second_distance[index]),
            "nearest_weighted_table_row": int(
                population["rows"][int(mapped_full_indices[index])]["csv_line"]
            ),
        }
        for index in rejected_indices[:20]
    ]

    def quantile(value: float) -> float:
        return float(np.quantile(nearest_distance, value))

    selected_distance_values = np.asarray(
        [nearest_distance[local_id - 1] for local_id in selected_ids],
        dtype=np.float64,
    )
    audit = {
        "family": family,
        "sim": sim.relative_to(ROOT).as_posix(),
        "expected_events": expected_events,
        "ID_records": ids_seen,
        "IA_INIT_records": init_seen,
        "mapped_IA_INIT_records": sum(trials),
        "duplicate_IA_INIT_records": duplicate_init,
        "ID_sequence_mismatches": sequence_mismatches,
        "missing_IA_INIT_records": ids_seen - init_seen,
        "position_metric": "Chebyshev_max_abs_axis_distance_cm",
        "source_support_rows_k_gt_zero": len(support_indices),
        "source_support_min_pairwise_chebyshev_separation_cm": finite_or_none(
            support_min_separation
        ),
        "source_card_coordinate_decimals": int(
            mapping_config["source_card_coordinate_decimals"]
        ),
        "sim_ia_init_coordinate_decimals": int(
            mapping_config["sim_ia_init_coordinate_decimals"]
        ),
        "serialization_tolerance_cm_per_axis": serialization_tolerance_cm,
        "retained_selected_lineage_tolerance_cm_per_axis": retained_selected_tolerance_cm,
        "adaptive_displacement_cap_cm_per_axis": adaptive_displacement_cap_cm,
        "minimum_second_nearest_gap_cm": minimum_second_gap_cm,
        "minimum_second_to_first_distance_ratio": minimum_second_to_first_ratio,
        "within_serialization_tolerance_records": int(
            np.count_nonzero(nearest_distance <= serialization_tolerance_cm)
        ),
        "within_retained_selected_tolerance_records": int(
            np.count_nonzero(nearest_distance <= retained_selected_tolerance_cm)
        ),
        "adaptive_unique_mapped_records": int(np.count_nonzero(accepted)),
        "adaptive_unique_unmapped_records": int(np.count_nonzero(~accepted)),
        "adaptive_unique_unmapped_fraction": float(np.mean(~accepted)),
        "adaptive_unmapped_selected_events": len(missing_selected),
        "adaptive_unmapped_known_zero_selected_events": int(
            np.count_nonzero(~accepted)
        )
        - len(missing_selected),
        "failed_absolute_cap_records": int(np.count_nonzero(~within_cap)),
        "failed_second_gap_records": int(np.count_nonzero(~separated)),
        "failed_distance_ratio_records": int(np.count_nonzero(~ratio_clear)),
        "rejected_first20": rejected_examples,
        "nearest_distance_median_cm": quantile(0.5),
        "nearest_distance_p99_cm": quantile(0.99),
        "nearest_distance_p99p9_cm": quantile(0.999),
        "nearest_distance_p99p99_cm": quantile(0.9999),
        "nearest_distance_p99p999_cm": quantile(0.99999),
        "nearest_distance_max_cm": float(np.max(nearest_distance)),
        "second_nearest_gap_min_cm": finite_or_none(float(np.min(second_gap))),
        "selected_ids_nearest_distance_max_cm": float(
            np.max(selected_distance_values)
        )
        if len(selected_distance_values)
        else None,
        "selected_ids_requested": len(selected_ids),
        "selected_ids_mapped": len(selected_id_to_row),
        "selected_ids_missing": len(missing_selected),
        "selected_ids_missing_first20": missing_selected[:20],
        "ia_init_za_semantics": "transport_or_daughter_ZA_not_guaranteed_source_parent_ZA",
        "init_za_equals_coordinate_mapped_source_parent_za_records": int(
            np.count_nonzero(init_equals_parent)
        ),
        "init_za_differs_from_coordinate_mapped_source_parent_za_records": int(
            np.count_nonzero(~init_equals_parent)
        ),
        "init_za_differs_from_coordinate_mapped_source_parent_za_fraction": float(
            np.mean(~init_equals_parent)
        ),
        "same_init_za_source_support_available_records": int(
            np.count_nonzero(same_za_support_available)
        ),
        "forced_same_za_adaptive_accepted_records": int(
            np.count_nonzero(same_za_adaptive_accepted)
        ),
        "forced_same_za_adaptive_agrees_coordinate_parent_records": int(
            np.count_nonzero(
                same_za_adaptive_accepted & same_za_agrees_coordinate_parent
            )
        ),
        "forced_same_za_adaptive_disagrees_coordinate_parent_records": int(
            np.count_nonzero(
                same_za_adaptive_accepted & ~same_za_agrees_coordinate_parent
            )
        ),
        "forced_same_za_nearest_distance_max_cm": finite_or_none(
            float(np.nanmax(same_za_nearest_distance))
            if np.any(same_za_support_available)
            else float("nan")
        ),
        "selected_init_za_by_local_id": {
            str(local_id): int(observed_init_za[local_id - 1])
            for local_id in sorted(selected_ids)
        },
        "mapping_strategy_sensitivity": {
            "strict_serialization_only_mapped_fraction": float(
                np.mean(nearest_distance <= serialization_tolerance_cm)
            ),
            "retained_selected_tolerance_mapped_fraction": float(
                np.mean(nearest_distance <= retained_selected_tolerance_cm)
            ),
            "adaptive_unique_mapped_fraction": float(np.mean(accepted)),
            "nearest_all_fraction": 1.0,
            "adaptive_vs_nearest_all_assignment_disagreements": int(
                np.count_nonzero(~accepted)
            ),
        },
    }
    if (
        duplicate_init
        or sequence_mismatches
        or missing_selected
    ):
        raise AuditError(f"{family}: raw SIM IA INIT mapping contract failed: {audit}")
    print(
        f"[offline-raw-scan] {family}: mapped {sum(trials)}/{expected_events} events",
        flush=True,
    )
    return trials, nearest_all_trials, selected_id_to_row, audit


def cluster_moment_record(
    *,
    family: str,
    response_seed: int,
    replica_index: int,
    resolution: str,
    target_weights: list[float],
    trials: list[int],
    selected: list[int],
    m: int,
    generated_events: int,
    te_s: float,
    source_activity_bq: float,
    target_mass_covered: float,
) -> dict[str, Any]:
    if not (len(target_weights) == len(trials) == len(selected)):
        raise AuditError(f"{family}/{resolution}: cluster vector length mismatch")
    total_weight = math.fsum(target_weights)
    if total_weight <= 0.0:
        raise AuditError(f"{family}/{resolution}: sampled cluster mass is zero")
    normalized = [value / total_weight for value in target_weights]
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=2.0e-12):
        raise AuditError(
            f"{family}/{resolution}: K/M cluster weights do not sum to one"
        )
    qhat = [success / trial if trial > 0 else 0.0 for success, trial in zip(selected, trials)]
    zero_trial_target_mass = math.fsum(
        weight for weight, trial in zip(normalized, trials) if trial == 0
    )
    mu = math.fsum(weight * value for weight, value in zip(normalized, qhat))
    naive_second = math.fsum(
        weight * value * value for weight, value in zip(normalized, qhat)
    )
    naive_variance = max(0.0, naive_second - mu * mu)
    unbiased_second = math.fsum(
        weight * (success * (success - 1) / (trial * (trial - 1)))
        for weight, success, trial in zip(normalized, selected, trials)
        if trial >= 2
    )
    within_mean_variance = math.fsum(
        weight * weight * (success * (trial - success) / (trial * trial * (trial - 1)))
        for weight, success, trial in zip(normalized, selected, trials)
        if trial >= 2
    )
    unbiased_mu_squared = mu * mu - within_mean_variance
    # The K/M weights describe the M sampled source blocks.  Apply the usual
    # finite-sample correction when using their empirical q distribution to
    # estimate Var_p(q) for a fresh M-block realization.
    finite_sample_correction = m / (m - 1.0) if m > 1 else 1.0
    debiased_variance_raw = finite_sample_correction * (
        unbiased_second - unbiased_mu_squared
    )
    debiased_variance = max(0.0, debiased_variance_raw)
    repeated_success_pairs = sum(
        success * (success - 1) // 2 for success in selected
    )
    pair_exposure = sum(trial * (trial - 1) // 2 for trial in trials)
    pair_coefficients = [
        weight / (trial * (trial - 1) / 2.0)
        for weight, trial in zip(normalized, trials)
        if trial >= 2
    ]
    pair_unexposed_mass = math.fsum(
        weight for weight, trial in zip(normalized, trials) if trial < 2
    )
    max_pair_coefficient = max(pair_coefficients) if pair_coefficients else 0.0
    poisson_pair_mean_upper = poisson_mean_upper_95(repeated_success_pairs)
    # Under the explicitly labelled rare-pair Poisson approximation, the
    # exposed contribution to E(q^2) is at most a_max times the total expected
    # repeated-pair count.  Clusters with n<2 receive the physical worst case
    # q^2=1.  This is conservative but remains finite when no repeated success
    # pair is observed.
    poisson_q2_upper = min(
        1.0,
        pair_unexposed_mass
        + max_pair_coefficient * poisson_pair_mean_upper,
    )
    conservative_variance_upper = min(0.25, poisson_q2_upper)
    event_rate = generated_events / te_s
    selected_total = sum(selected)
    current_selected_rate = selected_total / te_s
    conditional_target_rate = event_rate * mu
    if source_activity_bq <= 0.0:
        raise AuditError(f"{family}/{resolution}: source activity must be positive")
    activity_exposure = te_s * source_activity_bq
    h_mean = selected_total / activity_exposure
    h_second_factorial = math.fsum(
        weight
        * (success * (success - 1))
        / ((activity_exposure * weight) ** 2)
        for weight, success in zip(normalized, selected)
    )
    h_mean_squared_factorial = (
        selected_total * (selected_total - 1) / (activity_exposure**2)
    )
    h_variance_raw = finite_sample_correction * (
        h_second_factorial - h_mean_squared_factorial
    )
    h_variance = max(0.0, h_variance_raw)
    h_rate_sd = source_activity_bq * math.sqrt(h_variance / m)
    h_rate_cv = math.sqrt(h_variance / m) / h_mean if h_mean > 0.0 else None
    h_pair_coefficients = [
        2.0 * weight / ((activity_exposure * weight) ** 2)
        for weight in normalized
    ]
    h_max_pair_coefficient = max(h_pair_coefficients)
    h_second_poisson_upper = (
        h_max_pair_coefficient * poisson_pair_mean_upper
    )
    h_variance_poisson_upper = h_second_poisson_upper
    h_rate_sd_poisson_upper = source_activity_bq * math.sqrt(
        h_variance_poisson_upper / m
    )
    h_rate_cv_poisson_upper = (
        math.sqrt(h_variance_poisson_upper / m) / h_mean
        if h_mean > 0.0
        else None
    )
    return {
        "family": family,
        "replica_index": replica_index,
        "response_seed": response_seed,
        "resolution": resolution,
        "clusters": len(target_weights),
        "clusters_with_trials": sum(trial > 0 for trial in trials),
        "clusters_with_at_least_two_trials": sum(trial >= 2 for trial in trials),
        "clusters_with_selected": sum(success > 0 for success in selected),
        "generated_trials": sum(trials),
        "generated_trials_expected": generated_events,
        "identified_trial_fraction": sum(trials) / generated_events,
        "unassigned_known_zero_selected_trials": generated_events - sum(trials),
        "selected_events": selected_total,
        "target_mass_covered_by_retained_source": target_mass_covered,
        "target_mass_missing_from_retained_source": 1.0 - target_mass_covered,
        "conditional_support_zero_trial_mass": zero_trial_target_mass,
        "conditional_support_lt2_trial_mass": pair_unexposed_mass,
        "conditional_target_mean_selection_probability": mu,
        "conditional_target_predicted_rate_cps": conditional_target_rate,
        "current_selected_rate_cps": current_selected_rate,
        "source_activity_Bq": source_activity_bq,
        "per_block_selected_yield_mean_h": h_mean,
        "per_block_selected_yield_second_factorial": h_second_factorial,
        "per_block_selected_yield_mean_squared_factorial": h_mean_squared_factorial,
        "per_block_selected_yield_variance_debiased_raw": h_variance_raw,
        "per_block_selected_yield_variance_debiased_clipped": h_variance,
        "finite_m_selected_rate_sd_cps_h_yield": h_rate_sd,
        "finite_m_selected_rate_cv_h_yield": h_rate_cv,
        "h_yield_max_weighted_pair_coefficient": h_max_pair_coefficient,
        "h_yield_second_moment_poisson_one_sided_95_upper": h_second_poisson_upper,
        "finite_m_selected_rate_sd_cps_h_yield_poisson_pair_upper": h_rate_sd_poisson_upper,
        "finite_m_selected_rate_cv_h_yield_poisson_pair_upper": h_rate_cv_poisson_upper,
        "naive_between_cluster_q_variance": naive_variance,
        "debiased_between_cluster_q_variance_raw": debiased_variance_raw,
        "debiased_between_cluster_q_variance_clipped": debiased_variance,
        "exact_repeated_success_pairs": repeated_success_pairs,
        "exact_unordered_trial_pair_exposure": pair_exposure,
        "max_k_over_m_per_trial_pair_coefficient": max_pair_coefficient,
        "poisson_repeated_pair_mean_one_sided_95_upper": poisson_pair_mean_upper,
        "poisson_q2_one_sided_95_upper_conservative": poisson_q2_upper,
        "poisson_variance_one_sided_95_upper_no_mu2_subtraction": conservative_variance_upper,
        "naive_finite_m_source_sd_cps": event_rate
        * math.sqrt(naive_variance / m),
        "naive_finite_m_source_cv": math.sqrt(naive_variance / m) / mu
        if mu > 0.0
        else None,
        "debiased_finite_m_source_sd_cps": event_rate
        * math.sqrt(debiased_variance / m),
        "debiased_finite_m_source_cv": math.sqrt(debiased_variance / m) / mu
        if mu > 0.0
        else None,
        "poisson_upper_finite_m_source_sd_cps": event_rate
        * math.sqrt(conservative_variance_upper / m),
        "poisson_upper_finite_m_source_cv_using_point_mean": math.sqrt(
            conservative_variance_upper / m
        )
        / mu
        if mu > 0.0
        else None,
        "transport_counting_rse_observed": 1.0 / math.sqrt(selected_total)
        if selected_total > 0
        else None,
        "warning": "PRIMARY_RATE_METRIC_is_per_block_h_yield_with_Sj_Poisson_factorial_moment; q_selection_probability_is_diagnostic_because_raw_trial_share_is_not_K_over_M; naive_q_variance_contains_transport_Bernoulli_noise; Poisson_pair_upper_is_a_declared_rare_pair_approximation_and_its_CV_uses_the_point_mean",
    }


def poisson_source_bootstrap(
    *,
    family: str,
    resolution: str,
    target_weights: list[float],
    trials: list[int],
    selected: list[int],
    m: int,
    generated_events: int,
    te_s: float,
    source_activity_bq: float,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    import numpy as np

    weights = np.asarray(target_weights, dtype=np.float64)
    weights /= float(np.sum(weights))
    trial_array = np.asarray(trials, dtype=np.float64)
    selected_array = np.asarray(selected, dtype=np.float64)
    qhat = np.divide(
        selected_array,
        trial_array,
        out=np.zeros_like(selected_array),
        where=trial_array > 0,
    )
    hhat = np.divide(
        selected_array,
        te_s * source_activity_bq * weights,
        out=np.zeros_like(selected_array),
        where=weights > 0.0,
    )
    lam = float(m) * weights
    rng = np.random.default_rng(seed)
    rates: list[float] = []
    yield_rates: list[float] = []
    chunk_size = 64
    event_rate = generated_events / te_s
    for start in range(0, replicates, chunk_size):
        size = min(chunk_size, replicates - start)
        poisson_weights = rng.poisson(lam=lam, size=(size, len(lam)))
        denominators = np.sum(poisson_weights, axis=1)
        means = np.divide(
            poisson_weights @ qhat,
            denominators,
            out=np.zeros(size, dtype=np.float64),
            where=denominators > 0,
        )
        rates.extend((event_rate * means).tolist())
        yield_means = np.divide(
            poisson_weights @ hhat,
            denominators,
            out=np.zeros(size, dtype=np.float64),
            where=denominators > 0,
        )
        yield_rates.extend((source_activity_bq * yield_means).tolist())
    values = np.asarray(rates, dtype=np.float64)
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    yield_values = np.asarray(yield_rates, dtype=np.float64)
    yield_mean = float(np.mean(yield_values))
    yield_sd = float(np.std(yield_values, ddof=1))
    return {
        "family": family,
        "resolution": resolution,
        "replicates": replicates,
        "bootstrap_seed": seed,
        "m": m,
        "mean_rate_cps": mean,
        "sample_sd_cps": sd,
        "sample_cv": sd / mean if mean > 0.0 else None,
        "q02p5_rate_cps": float(np.quantile(values, 0.025)),
        "median_rate_cps": float(np.quantile(values, 0.5)),
        "q97p5_rate_cps": float(np.quantile(values, 0.975)),
        "h_yield_mean_rate_cps": yield_mean,
        "h_yield_sample_sd_cps": yield_sd,
        "h_yield_sample_cv": yield_sd / yield_mean if yield_mean > 0.0 else None,
        "h_yield_q02p5_rate_cps": float(np.quantile(yield_values, 0.025)),
        "h_yield_median_rate_cps": float(np.quantile(yield_values, 0.5)),
        "h_yield_q97p5_rate_cps": float(np.quantile(yield_values, 0.975)),
        "scope": "Poissonized_M_block_bootstrap_from_empirical_K_over_M; hhat=S/(T*A*w) is the rate-yield diagnostic; qhat=S/n is retained separately; neither resamples transport outcomes",
    }


def summarize_response_replicas(path: Path, families: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        replicas = list(csv.DictReader(handle))
    if len(replicas) != 64:
        raise AuditError(f"response replica count={len(replicas)} expected=64")
    components = [("delayed", "delayed_final_events", "delayed_final_cps")]
    components.extend(
        (family, f"delayed_{family}_final_events", f"delayed_{family}_final_cps")
        for family in families
    )
    output: list[dict[str, Any]] = []
    for component, event_field, rate_field in components:
        event_values = [int(row[event_field]) for row in replicas]
        rate_values = [float(row[rate_field]) for row in replicas]
        mean_rate = statistics.fmean(rate_values)
        sd_rate = statistics.stdev(rate_values)
        output.append(
            {
                "component": component,
                "replicas": len(replicas),
                "mean_events": statistics.fmean(event_values),
                "min_events": min(event_values),
                "max_events": max(event_values),
                "mean_rate_cps": mean_rate,
                "sample_sd_across_response_seeds_cps": sd_rate,
                "mean_se_across_response_seeds_cps": sd_rate / math.sqrt(len(replicas)),
                "mean_se_fraction": sd_rate / math.sqrt(len(replicas)) / mean_rate
                if mean_rate
                else None,
                "warning": "same_physical_transport_events_not_independent_transport_replicas",
            }
        )
    return output, {"replicas": replicas}


def aggregate_source_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    fields = [
        "target_row_mass_coverage",
        "target_group_mass_unseen",
        "row_jsd_nats",
        "group_jsd_nats",
        "group_top90_jaccard",
    ]
    keys = sorted({(row["family"], row["m"]) for row in rows})
    for family, m in keys:
        subset = [row for row in rows if row["family"] == family and row["m"] == m]
        record: dict[str, Any] = {"family": family, "m": m, "source_seeds": len(subset)}
        for field in fields:
            values = [float(row[field]) for row in subset if row[field] is not None]
            record[f"mean_{field}"] = statistics.fmean(values) if values else None
            record[f"sample_sd_{field}"] = statistics.stdev(values) if len(values) > 1 else 0.0
        output.append(record)
    return output


def output_manifest_paths() -> list[Path]:
    return [
        PACKAGE / "README.md",
        PACKAGE / "M_SAMPLING_CONCLUSION.md",
        CONFIG_PATH,
        SCRIPT,
        DATA / "input_hash_audit.csv",
        DATA / "source_population_summary.csv",
        SOURCE_ONLY / "source_only_resampling.csv",
        DATA / "conditional_selected_rate_reweight.csv",
        DATA / "response_seed_ensemble_summary.csv",
        DATA / "raw_sim_parse_summary.csv",
        DATA / "raw_sim_source_row_clusters.csv",
        DATA / "response_seed_selected_lineage.csv",
        DATA / "cluster_source_variance_by_response_seed.csv",
        DATA / "cluster_poisson_bootstrap_primary_seed.csv",
        DATA / "m_sampling_offline_summary.json",
    ]


def write_output_manifest(config: dict[str, Any], status: str) -> None:
    manifest_paths = output_manifest_paths()
    missing = [path for path in manifest_paths if not path.is_file()]
    if missing:
        raise AuditError(f"cannot write output manifest; missing artifacts={missing}")
    output_manifest = {
        "schema": "m04_wp1_offline_output_manifest_v1",
        "analysis_date": config["analysis_date"],
        "status": status,
        "artifacts": [
            {
                "path": path.relative_to(PACKAGE).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in manifest_paths
        ],
        "boundary": "manifest covers offline code/config/docs/results only; retained inputs are frozen separately in data/input_hash_audit.csv",
    }
    write_json(DATA / "output_manifest.json", output_manifest)


def main() -> int:
    config = load_json(CONFIG_PATH)
    DATA.mkdir(parents=True, exist_ok=True)
    SOURCE_ONLY.mkdir(parents=True, exist_ok=True)
    hash_rows = verify_hashes(config)

    families = list(config["families"])
    baseline_m = int(config["baseline"]["m_blocks"])
    baseline_seed = int(config["baseline"]["source_seed"])
    m_values = [int(value) for value in config["source_only_resampling"]["m_values"]]
    seeds = [int(value) for value in config["source_only_resampling"]["source_seeds"]]
    top_fraction = float(config["source_only_resampling"]["top_mass_fraction"])

    lineage_authority = load_json(ROOT / config["authorities"]["primary_selected_lineage"])
    response_authority = load_json(ROOT / config["authorities"]["response_summary"])
    if int(lineage_authority.get("response_seed") or -1) != int(
        config["baseline"]["response_seed_primary"]
    ):
        raise AuditError("primary selected-lineage response seed is stale")
    lineage_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in lineage_authority["lineage"]:
        lineage_by_family[str(event["incident_family"])].append(event)
    response_lineage_records, response_event_replay_audit = (
        replay_response_selected_lineage(config, lineage_authority)
    )
    response_lineage_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in response_lineage_records:
        response_lineage_by_family[str(record["family"])].append(record)

    source_rows: list[dict[str, Any]] = []
    resampling_rows: list[dict[str, Any]] = []
    conditional_rows: list[dict[str, Any]] = []
    total_conditional: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {
            "contributions": [],
            "groups": defaultdict(float),
            "activity_outside_numerator": 0.0,
            "target_outside_numerator": 0.0,
            "activity_total": 0.0,
            "hajek_rate": 0.0,
            "max_importance_ratio": 0.0,
        }
    )
    raw_sim_bindings: list[dict[str, Any]] = []
    raw_parse_rows: list[dict[str, Any]] = []
    raw_cluster_rows: list[dict[str, Any]] = []
    response_lineage_mapped_rows: list[dict[str, Any]] = []
    cluster_variance_rows: list[dict[str, Any]] = []
    cluster_bootstrap_rows: list[dict[str, Any]] = []
    family_audit_by_name = {
        str(row["family"]): row for row in lineage_authority["family_audits"]
    }
    for family in families:
        manifest = load_json(family_path(config, "manifest", family))
        population = read_population(family_path(config, "weighted_table", family))
        source = parse_source_card(family_path(config, "source_card", family))
        baseline_counts, baseline_chosen = draw_counts(population, baseline_m, baseline_seed)
        replay = compare_source_replay(population, baseline_chosen, source)
        if replay["mismatches"] or not replay["uniform_flux"]:
            raise AuditError(f"{family}: retained source card does not exactly replay")
        if source["triggers"] != int(config["baseline"]["triggers_per_positive_family"]):
            raise AuditError(f"{family}: source-card Triggers mismatch")
        if int(manifest.get("seed") or -1) != baseline_seed:
            raise AuditError(f"{family}: manifest source seed mismatch")
        if int(manifest.get("n_pointsource_blocks") or -1) != baseline_m:
            raise AuditError(f"{family}: manifest M mismatch")
        if resolve_recorded_path(source["geometry"]) != resolve_recorded_path(
            manifest["geometry"]
        ):
            raise AuditError(f"{family}: source-card geometry differs from manifest")
        transport = manifest.get("delayed_transport") or {}
        if (
            transport.get("status") != "PASS"
            or int(transport.get("seed") or -1) != baseline_seed
            or int(transport.get("SE") or -1) != int(
                config["baseline"]["triggers_per_positive_family"]
            )
            or int(transport.get("ID") or -1) != int(
                config["baseline"]["triggers_per_positive_family"]
            )
            or int(transport.get("TS") or -1) != 1
            or int(transport.get("TS_value") or -1)
            != int(config["baseline"]["triggers_per_positive_family"])
            or resolve_recorded_path(transport.get("header_geometry", "/"))
            != resolve_recorded_path(manifest["geometry"])
        ):
            raise AuditError(f"{family}: retained manifest transport/header contract failed")
        relative_activity_delta = abs(
            population["total"] - float(manifest["fixed_total_activity_Bq"])
        ) / float(manifest["fixed_total_activity_Bq"])
        # The retained table serializes each row to 12 significant digits.  Its
        # sum therefore closes to the unrounded manifest activity at O(1e-9)
        # relative for the smallest families, not at machine precision.
        if relative_activity_delta > 1.0e-8:
            raise AuditError(f"{family}: serialized table activity does not close")

        baseline_metrics = source_metrics(
            family,
            population,
            baseline_counts,
            baseline_m,
            baseline_seed,
            top_fraction,
        )
        manifest_group_unseen = float(
            manifest.get("sampling_audit", {}).get(
                "missed_nuclides_total_activity_fraction", float("nan")
            )
        )
        source_rows.append(
            {
                "family": family,
                "weighted_table_rows": len(population["rows"]),
                "unique_positions": population["unique_positions"],
                "target_activity_Bq": population["total"],
                "manifest_activity_Bq": manifest["fixed_total_activity_Bq"],
                "serialized_table_activity_relative_delta": relative_activity_delta,
                "target_row_effective_support": 1.0
                / math.fsum(value * value for value in population["probabilities"]),
                "target_groups_vn_za": baseline_metrics["population_groups_vn_za"],
                "baseline_m": baseline_m,
                "baseline_seed": baseline_seed,
                "source_card_triggers": source["triggers"],
                "source_card_geometry": source["geometry"],
                "source_card_blocks": replay["blocks"],
                "source_replay_mismatches": replay["mismatches"],
                "source_flux_uniform": replay["uniform_flux"],
                "source_text_flux_sum_Bq": replay["serialized_flux_sum_Bq"],
                "baseline_unique_rows": baseline_metrics["unique_rows_drawn"],
                "baseline_target_row_mass_coverage": baseline_metrics[
                    "target_row_mass_coverage"
                ],
                "baseline_target_row_mass_unseen": baseline_metrics[
                    "target_row_mass_unseen"
                ],
                "baseline_unique_groups_vn_za": baseline_metrics[
                    "unique_groups_vn_za_drawn"
                ],
                "baseline_target_group_mass_coverage": baseline_metrics[
                    "target_group_mass_coverage"
                ],
                "baseline_target_group_mass_unseen": baseline_metrics[
                    "target_group_mass_unseen"
                ],
                "manifest_missed_vn_za_activity_fraction": finite_or_none(
                    manifest_group_unseen
                ),
                "computed_minus_manifest_group_unseen": finite_or_none(
                    baseline_metrics["target_group_mass_unseen"] - manifest_group_unseen
                ),
            }
        )

        events = lineage_by_family.get(family, [])
        for event in events:
            index = int(event["weighted_table_row"]) - 2
            row = population["rows"][index]
            if (
                int(row["ZA"]) != int(event["source_parent_ZA"])
                or str(row["VN"]) != str(event["source_parent_volume"])
                or any(
                    abs(float(row[axis]) - float(value)) > 5.0e-10
                    for axis, value in zip(
                        ("x_cm", "y_cm", "z_cm"), event["source_parent_position_cm"]
                    )
                )
            ):
                raise AuditError(f"{family}: selected lineage row does not reconnect")
            if baseline_counts[index] <= 0:
                raise AuditError(f"{family}: selected lineage row absent from source draw")

        family_audit = family_audit_by_name[family]
        if (
            resolve_recorded_path(family_audit.get("sim", "/"))
            != resolve_recorded_path(transport["path"])
            or int(family_audit.get("sim_size_bytes") or -1)
            != int(transport["size_bytes"])
            or family_audit.get("sim_sha256") != transport.get("sha256")
            or not math.isclose(
                1.0 / float(family_audit["event_weight_cps"]),
                float(transport["TE_s"]),
                rel_tol=0.0,
                abs_tol=5.0e-7,
            )
        ):
            raise AuditError(f"{family}: lineage/SIM/TE binding differs from manifest")
        raw_sim_bindings.append(
            {
                "family": family,
                "sim": family_audit.get("sim"),
                "sim_size_bytes": family_audit.get("sim_size_bytes"),
                "sim_sha256_from_retained_lineage_authority": family_audit.get("sim_sha256"),
                "transport_provenance_verified_by_retained_authority": family_audit.get(
                    "transport_provenance_verified"
                ),
                "selected_events_primary_response_seed": family_audit.get("selected_events"),
                "event_weight_cps": family_audit.get("event_weight_cps"),
                "source_and_transport_seed": transport.get("seed"),
                "SE": transport.get("SE"),
                "ID": transport.get("ID"),
                "TS_records": transport.get("TS"),
                "TS_value": transport.get("TS_value"),
                "TE_s_from_manifest": transport.get("TE_s"),
                "TE_s_inferred_as_inverse_event_weight": 1.0
                / float(family_audit["event_weight_cps"]),
            }
        )

        family_response_records = response_lineage_by_family.get(family, [])
        selected_ids_any_seed = {
            int(record["local_id"]) for record in family_response_records
        }
        (
            raw_trials,
            nearest_all_raw_trials,
            selected_id_to_row,
            raw_audit,
        ) = scan_raw_sim_row_trials(
            family,
            resolve_recorded_path(transport["path"]),
            population,
            baseline_counts,
            config["raw_sim_position_mapping"],
            selected_ids_any_seed,
            int(transport["ID"]),
        )
        source_trial_tv = 0.5 * math.fsum(
            abs(trial / int(transport["ID"]) - blocks / baseline_m)
            for trial, blocks in zip(raw_trials, baseline_counts)
        )
        nearest_all_source_trial_tv = 0.5 * math.fsum(
            abs(trial / int(transport["ID"]) - blocks / baseline_m)
            for trial, blocks in zip(nearest_all_raw_trials, baseline_counts)
        )
        raw_audit.update(
            {
                "adaptive_identified_transport_trials": sum(raw_trials),
                "adaptive_unidentified_zero_outcome_trials": int(transport["ID"])
                - sum(raw_trials),
                "retained_source_unique_rows": sum(value > 0 for value in baseline_counts),
                "retained_source_rows_with_zero_transport_trials": sum(
                    blocks > 0 and trial == 0
                    for blocks, trial in zip(baseline_counts, raw_trials)
                ),
                "transport_trials_on_rows_absent_from_source": sum(
                    trial for blocks, trial in zip(baseline_counts, raw_trials) if blocks == 0
                ),
                "source_block_vs_realized_trial_share_total_variation": source_trial_tv,
                "nearest_all_sensitivity_source_block_vs_trial_share_total_variation": nearest_all_source_trial_tv,
                "selected_indicator_contract": (
                    "response replay enumerates every final delayed W511 lineage; "
                    "all other local IDs, including events absent from the TES compact "
                    "catalog, have selected indicator zero"
                ),
            }
        )
        raw_parse_rows.append(raw_audit)

        mapped_family_records: list[dict[str, Any]] = []
        for record in family_response_records:
            if resolve_recorded_path(record["source_file"]) != resolve_recorded_path(
                transport["path"]
            ):
                raise AuditError(f"{family}: response lineage source file mismatch")
            index = selected_id_to_row[int(record["local_id"])]
            row = population["rows"][index]
            mapped = {
                **record,
                "sim_initial_ZA_transport_or_daughter": int(
                    raw_audit["selected_init_za_by_local_id"][
                        str(int(record["local_id"]))
                    ]
                ),
                "weighted_table_row": int(row["csv_line"]),
                "weighted_table_index_zero_based": index,
                "source_parent_volume": row["VN"],
                "source_parent_ZA": row["ZA"],
                "source_parent_x_cm": row["x_cm"],
                "source_parent_y_cm": row["y_cm"],
                "source_parent_z_cm": row["z_cm"],
                "source_block_multiplicity": baseline_counts[index],
                "raw_transport_trials_at_row": raw_trials[index],
            }
            mapped_family_records.append(mapped)
            response_lineage_mapped_rows.append(mapped)

        selected_occurrences_by_row = Counter(
            int(record["weighted_table_index_zero_based"])
            for record in mapped_family_records
        )
        selected_ids_by_row: dict[int, set[int]] = defaultdict(set)
        for record in mapped_family_records:
            selected_ids_by_row[int(record["weighted_table_index_zero_based"])].add(
                int(record["local_id"])
            )
        primary_selected_by_row = Counter(
            int(record["weighted_table_index_zero_based"])
            for record in mapped_family_records
            if int(record["replica_index"]) == 0
        )
        for index, (blocks, trial) in enumerate(zip(baseline_counts, raw_trials)):
            if blocks <= 0:
                continue
            row = population["rows"][index]
            raw_cluster_rows.append(
                {
                    "family": family,
                    "weighted_table_row": row["csv_line"],
                    "weighted_table_index_zero_based": index,
                    "VN": row["VN"],
                    "ZA": row["ZA"],
                    "x_cm": row["x_cm"],
                    "y_cm": row["y_cm"],
                    "z_cm": row["z_cm"],
                    "target_probability": population["probabilities"][index],
                    "source_block_multiplicity": blocks,
                    "source_block_share": blocks / baseline_m,
                    "generated_transport_trials": trial,
                    "generated_transport_trial_share": trial / int(transport["ID"]),
                    "nearest_all_sensitivity_transport_trials": nearest_all_raw_trials[
                        index
                    ],
                    "primary_response_selected_events": primary_selected_by_row[index],
                    "selected_occurrences_across_64_response_seeds": selected_occurrences_by_row[
                        index
                    ],
                    "unique_local_ids_selected_in_any_response_seed": len(
                        selected_ids_by_row[index]
                    ),
                }
            )

        support_indices = [
            index for index, blocks in enumerate(baseline_counts) if blocks > 0
        ]
        # The retained M-block source card is itself an i.i.d. probability
        # sample from p.  K/M, not target-p renormalized to the observed row
        # set, is therefore the primary empirical measure for estimating
        # Var_p(q) from this one realization.
        position_weights = [
            baseline_counts[index] / baseline_m for index in support_indices
        ]
        position_trials = [raw_trials[index] for index in support_indices]
        position_nearest_all_trials = [
            nearest_all_raw_trials[index] for index in support_indices
        ]
        position_target_mass = math.fsum(
            population["probabilities"][index] for index in support_indices
        )

        group_target: dict[tuple[str, int], float] = defaultdict(float)
        group_blocks: dict[tuple[str, int], int] = defaultdict(int)
        group_supported: set[tuple[str, int]] = set()
        group_trials_map: dict[tuple[str, int], int] = defaultdict(int)
        group_nearest_all_trials_map: dict[tuple[str, int], int] = defaultdict(int)
        for index, row in enumerate(population["rows"]):
            key = (str(row["VN"]), int(row["ZA"]))
            group_target[key] += population["probabilities"][index]
            if baseline_counts[index] > 0:
                group_supported.add(key)
                group_blocks[key] += baseline_counts[index]
                group_trials_map[key] += raw_trials[index]
                group_nearest_all_trials_map[key] += nearest_all_raw_trials[index]
        group_keys = sorted(group_supported, key=str)
        group_weights = [group_blocks[key] / baseline_m for key in group_keys]
        group_trials = [group_trials_map[key] for key in group_keys]
        group_nearest_all_trials = [
            group_nearest_all_trials_map[key] for key in group_keys
        ]
        group_target_mass = math.fsum(group_target[key] for key in group_keys)

        records_by_replica: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for record in mapped_family_records:
            records_by_replica[int(record["replica_index"])].append(record)
        primary_position_selected: list[int] | None = None
        primary_group_selected: list[int] | None = None
        for seed_record in response_event_replay_audit["per_seed"]:
            replica_index = int(seed_record["replica_index"])
            response_seed = int(seed_record["response_seed"])
            selected_by_index = Counter(
                int(record["weighted_table_index_zero_based"])
                for record in records_by_replica.get(replica_index, [])
            )
            position_selected = [selected_by_index[index] for index in support_indices]
            selected_by_group: dict[tuple[str, int], int] = defaultdict(int)
            for index, count in selected_by_index.items():
                row = population["rows"][index]
                selected_by_group[(str(row["VN"]), int(row["ZA"]))] += count
            group_selected = [selected_by_group[key] for key in group_keys]
            cluster_variance_rows.append(
                cluster_moment_record(
                    family=family,
                    response_seed=response_seed,
                    replica_index=replica_index,
                    resolution="exact_position_row",
                    target_weights=position_weights,
                    trials=position_trials,
                    selected=position_selected,
                    m=baseline_m,
                    generated_events=int(transport["ID"]),
                    te_s=float(transport["TE_s"]),
                    source_activity_bq=float(population["total"]),
                    target_mass_covered=position_target_mass,
                )
            )
            cluster_variance_rows.append(
                cluster_moment_record(
                    family=family,
                    response_seed=response_seed,
                    replica_index=replica_index,
                    resolution="vn_za_group_constant_q_model",
                    target_weights=group_weights,
                    trials=group_trials,
                    selected=group_selected,
                    m=baseline_m,
                    generated_events=int(transport["ID"]),
                    te_s=float(transport["TE_s"]),
                    source_activity_bq=float(population["total"]),
                    target_mass_covered=group_target_mass,
                )
            )
            if replica_index == 0:
                primary_position_selected = position_selected
                primary_group_selected = group_selected
                cluster_variance_rows.append(
                    cluster_moment_record(
                        family=family,
                        response_seed=response_seed,
                        replica_index=replica_index,
                        resolution="exact_position_row_nearest_all_mapping_sensitivity",
                        target_weights=position_weights,
                        trials=position_nearest_all_trials,
                        selected=position_selected,
                        m=baseline_m,
                        generated_events=int(transport["ID"]),
                        te_s=float(transport["TE_s"]),
                        source_activity_bq=float(population["total"]),
                        target_mass_covered=position_target_mass,
                    )
                )
                cluster_variance_rows.append(
                    cluster_moment_record(
                        family=family,
                        response_seed=response_seed,
                        replica_index=replica_index,
                        resolution="vn_za_group_nearest_all_mapping_sensitivity",
                        target_weights=group_weights,
                        trials=group_nearest_all_trials,
                        selected=group_selected,
                        m=baseline_m,
                        generated_events=int(transport["ID"]),
                        te_s=float(transport["TE_s"]),
                        source_activity_bq=float(population["total"]),
                        target_mass_covered=group_target_mass,
                    )
                )
        if primary_position_selected is None or primary_group_selected is None:
            raise AuditError(f"{family}: primary response seed was not replayed")
        bootstrap_config = config["offline_event_analysis"]
        family_offset = families.index(family) * 10
        cluster_bootstrap_rows.append(
            poisson_source_bootstrap(
                family=family,
                resolution="exact_position_row",
                target_weights=position_weights,
                trials=position_trials,
                selected=primary_position_selected,
                m=baseline_m,
                generated_events=int(transport["ID"]),
                te_s=float(transport["TE_s"]),
                source_activity_bq=float(population["total"]),
                replicates=int(
                    bootstrap_config["poisson_source_block_bootstrap_replicates"]
                ),
                seed=int(
                    bootstrap_config["poisson_source_block_bootstrap_seed"]
                )
                + family_offset,
            )
        )
        cluster_bootstrap_rows.append(
            poisson_source_bootstrap(
                family=family,
                resolution="vn_za_group_constant_q_model",
                target_weights=group_weights,
                trials=group_trials,
                selected=primary_group_selected,
                m=baseline_m,
                generated_events=int(transport["ID"]),
                te_s=float(transport["TE_s"]),
                source_activity_bq=float(population["total"]),
                replicates=int(
                    bootstrap_config["poisson_source_block_bootstrap_replicates"]
                ),
                seed=int(
                    bootstrap_config["poisson_source_block_bootstrap_seed"]
                )
                + family_offset
                + 1,
            )
        )
        cluster_bootstrap_rows.append(
            poisson_source_bootstrap(
                family=family,
                resolution="exact_position_row_nearest_all_mapping_sensitivity",
                target_weights=position_weights,
                trials=position_nearest_all_trials,
                selected=primary_position_selected,
                m=baseline_m,
                generated_events=int(transport["ID"]),
                te_s=float(transport["TE_s"]),
                source_activity_bq=float(population["total"]),
                replicates=int(
                    bootstrap_config["poisson_source_block_bootstrap_replicates"]
                ),
                seed=int(
                    bootstrap_config["poisson_source_block_bootstrap_seed"]
                )
                + family_offset
                + 2,
            )
        )

        for m in m_values:
            for seed in seeds:
                counts, _ = draw_counts(population, m, seed)
                metrics = source_metrics(
                    family, population, counts, m, seed, top_fraction
                )
                resampling_rows.append(metrics)
                conditional, contributions, groups = conditional_reweight(
                    family,
                    events,
                    population,
                    baseline_counts,
                    counts,
                    m,
                    seed,
                    baseline_m,
                    top_fraction,
                )
                conditional_rows.append(conditional)
                accumulator = total_conditional[(m, seed)]
                accumulator["contributions"].extend(contributions)
                for key, value in groups.items():
                    accumulator["groups"][key] += value
                activity = float(population["total"])
                accumulator["activity_outside_numerator"] += activity * float(
                    conditional["candidate_draw_fraction_outside_retained_row_support"]
                )
                accumulator["target_outside_numerator"] += activity * float(
                    conditional["fixed_target_row_mass_outside_retained_support"]
                )
                accumulator["activity_total"] += activity
                accumulator["hajek_rate"] += float(
                    conditional["conditional_hajek_rate_cps"] or 0.0
                )
                accumulator["max_importance_ratio"] = max(
                    accumulator["max_importance_ratio"],
                    float(conditional["max_selected_event_importance_ratio"] or 0.0),
                )

    base_events = [event for family in families for event in lineage_by_family.get(family, [])]
    base_contributions = [float(event["event_weight_cps"]) for event in base_events]
    base_groups = selected_group_contributions(base_events, base_contributions)
    base_total_rate = math.fsum(base_contributions)
    for (m, seed), accumulator in sorted(total_conditional.items()):
        contributions = list(accumulator["contributions"])
        rate = math.fsum(contributions)
        positive = [value for value in contributions if value > 0.0]
        conditional_rows.append(
            {
                "family": "ALL_POSITIVE_FAMILIES",
                "m": m,
                "source_seed": seed,
                "primary_selected_physical_events": len(base_events),
                "baseline_primary_selected_rate_cps": base_total_rate,
                "conditional_reweighted_rate_cps": rate,
                "conditional_rate_ratio_to_baseline": rate / base_total_rate,
                "candidate_draw_fraction_on_retained_row_support": 1.0
                - accumulator["activity_outside_numerator"]
                / accumulator["activity_total"],
                "conditional_hajek_rate_cps": accumulator["hajek_rate"],
                "conditional_hajek_rate_ratio_to_baseline": accumulator[
                    "hajek_rate"
                ]
                / base_total_rate,
                "candidate_draw_fraction_outside_retained_row_support": accumulator[
                    "activity_outside_numerator"
                ]
                / accumulator["activity_total"],
                "fixed_target_row_mass_outside_retained_support": accumulator[
                    "target_outside_numerator"
                ]
                / accumulator["activity_total"],
                "selected_events_with_positive_candidate_weight": len(positive),
                "selected_event_importance_ess": math.fsum(positive) ** 2
                / math.fsum(value * value for value in positive)
                if positive
                else 0.0,
                "max_selected_event_importance_ratio": accumulator[
                    "max_importance_ratio"
                ],
                "selected_contribution_group_jsd_nats_vs_baseline": jsd_mappings(
                    base_groups, accumulator["groups"]
                ),
                "selected_contribution_top90_jaccard_vs_baseline": jaccard(
                    top_mass_set(base_groups, top_fraction),
                    top_mass_set(accumulator["groups"], top_fraction),
                ),
                "interpretation": "conditional_on_retained_transport_and_observed_row_support",
            }
        )

    response_rows, response_raw = summarize_response_replicas(
        ROOT / config["authorities"]["response_replicas"], families
    )
    source_aggregate = aggregate_source_metrics(resampling_rows)
    neutron = next(row for row in source_rows if row["family"] == "n")
    neutron_events = len(lineage_by_family["n"])
    transport_sigma = math.sqrt(math.fsum(value * value for value in base_contributions))
    neutron_position_cluster_primary = next(
        row
        for row in cluster_variance_rows
        if row["family"] == "n"
        and row["replica_index"] == 0
        and row["resolution"] == "exact_position_row"
    )
    neutron_group_cluster_primary = next(
        row
        for row in cluster_variance_rows
        if row["family"] == "n"
        and row["replica_index"] == 0
        and row["resolution"] == "vn_za_group_constant_q_model"
    )
    neutron_position_mapping_sensitivity = next(
        row
        for row in cluster_variance_rows
        if row["family"] == "n"
        and row["replica_index"] == 0
        and row["resolution"]
        == "exact_position_row_nearest_all_mapping_sensitivity"
    )
    primary_exact_rows = [
        row
        for row in cluster_variance_rows
        if row["replica_index"] == 0
        and row["resolution"] == "exact_position_row"
    ]
    primary_exact_bootstrap_rows = [
        row
        for row in cluster_bootstrap_rows
        if row["resolution"] == "exact_position_row"
    ]
    all_family_exact_primary = {
        "families": len(primary_exact_rows),
        "selected_rate_cps": base_total_rate,
        "h_yield_debiased_source_sd_cps_independent_family_rss": math.sqrt(
            math.fsum(
                float(row["finite_m_selected_rate_sd_cps_h_yield"]) ** 2
                for row in primary_exact_rows
            )
        ),
        "h_yield_debiased_source_sd_cps_perfect_positive_correlation_sum": math.fsum(
            float(row["finite_m_selected_rate_sd_cps_h_yield"])
            for row in primary_exact_rows
        ),
        "h_yield_poisson_pair_upper_source_sd_cps_independent_family_rss": math.sqrt(
            math.fsum(
                float(
                    row[
                        "finite_m_selected_rate_sd_cps_h_yield_poisson_pair_upper"
                    ]
                )
                ** 2
                for row in primary_exact_rows
            )
        ),
        "h_yield_poisson_pair_upper_source_sd_cps_perfect_positive_correlation_sum": math.fsum(
            float(
                row[
                    "finite_m_selected_rate_sd_cps_h_yield_poisson_pair_upper"
                ]
            )
            for row in primary_exact_rows
        ),
        "h_yield_naive_bootstrap_sd_cps_independent_family_rss": math.sqrt(
            math.fsum(
                float(row["h_yield_sample_sd_cps"]) ** 2
                for row in primary_exact_bootstrap_rows
            )
        ),
        "q_selection_probability_diagnostic_sd_cps_independent_family_rss": math.sqrt(
            math.fsum(
                float(row["debiased_finite_m_source_sd_cps"]) ** 2
                for row in primary_exact_rows
            )
        ),
        "family_dependence_warning": (
            "the retained families reuse source seed 260613; RSS assumes independent "
            "source realizations, while the arithmetic sum is the reported perfect-"
            "positive-correlation sensitivity bound"
        ),
    }
    for key in list(all_family_exact_primary):
        if "_sd_cps_" in key:
            all_family_exact_primary[f"{key.replace('_sd_cps_', '_cv_')}"] = (
                float(all_family_exact_primary[key]) / base_total_rate
                if base_total_rate > 0.0
                else None
            )

    def response_seed_metric_range(resolution: str, field: str) -> dict[str, float | None]:
        values = [
            float(row[field])
            for row in cluster_variance_rows
            if row["family"] == "n"
            and row["resolution"] == resolution
            and row[field] is not None
        ]
        return {
            "min": min(values) if values else None,
            "median": statistics.median(values) if values else None,
            "max": max(values) if values else None,
        }

    neutron_response_seed_ranges = {
        resolution: {
            field: response_seed_metric_range(resolution, field)
            for field in (
                "finite_m_selected_rate_cv_h_yield",
                "finite_m_selected_rate_cv_h_yield_poisson_pair_upper",
                "debiased_finite_m_source_cv",
                "poisson_upper_finite_m_source_cv_using_point_mean",
                "exact_repeated_success_pairs",
            )
        }
        for resolution in (
            "exact_position_row",
            "vn_za_group_constant_q_model",
        )
    }

    source_fields = list(source_rows[0].keys())
    resampling_fields = list(resampling_rows[0].keys())
    conditional_fields = list(conditional_rows[0].keys())
    response_fields = list(response_rows[0].keys())
    write_csv(DATA / "source_population_summary.csv", source_rows, source_fields)
    write_csv(SOURCE_ONLY / "source_only_resampling.csv", resampling_rows, resampling_fields)
    write_csv(
        DATA / "conditional_selected_rate_reweight.csv",
        conditional_rows,
        conditional_fields,
    )
    write_csv(
        DATA / "response_seed_ensemble_summary.csv", response_rows, response_fields
    )
    write_csv(
        DATA / "raw_sim_parse_summary.csv",
        raw_parse_rows,
        list(raw_parse_rows[0].keys()),
    )
    write_csv(
        DATA / "raw_sim_source_row_clusters.csv",
        raw_cluster_rows,
        list(raw_cluster_rows[0].keys()),
    )
    write_csv(
        DATA / "response_seed_selected_lineage.csv",
        response_lineage_mapped_rows,
        list(response_lineage_mapped_rows[0].keys()),
    )
    write_csv(
        DATA / "cluster_source_variance_by_response_seed.csv",
        cluster_variance_rows,
        list(cluster_variance_rows[0].keys()),
    )
    write_csv(
        DATA / "cluster_poisson_bootstrap_primary_seed.csv",
        cluster_bootstrap_rows,
        list(cluster_bootstrap_rows[0].keys()),
    )

    summary = {
        "schema": "m04_wp1_offline_m_sampling_validation_summary_v1",
        "analysis_date": config["analysis_date"],
        "status": "CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS",
        "scope": config["scope"],
        "user_override": {
            "handoff_section_7_3B_transport_matrix": "NOT_EXECUTED_USER_OVERRIDDEN_ZERO_SIMULATION",
            "handoff_section_8_4_6_detector_transport": "USER_OVERRIDDEN_WP1_NO_TRANSPORT__WP2_INDEPENDENT_ATMOSPHERIC_ANNIHILATION_511KEV_MONO_ONLY",
        },
        "input_hash_audit": {
            "status": "PASS_ALL_FROZEN_INPUT_HASHES",
            "files": len(hash_rows),
            "csv": "data/input_hash_audit.csv",
        },
        "builder_semantics": {
            "activity_distribution_key": ["VN", "ZA"],
            "exc_keV_recorded_but_not_distribution_key": True,
            "sampling": "with_replacement_using_random.Random(seed)_and_activity_weights",
            "pointsource_flux": "equal_A_div_M",
            "m_meaning": "finite_resampled_spatial_support_not_transport_count",
            "triggers_meaning": "Cosima_requested_pretrigger_records",
            "TE_meaning": "SIM_rate_normalization_authority_event_weight_equals_1_div_TE",
            "same_current_source_and_transport_seed": 260613,
        },
        "baseline_source_replay": {
            "status": "PASS_ALL_SEVEN_SOURCE_CARDS_EXACT_BLOCKWISE_REPLAY",
            "m": baseline_m,
            "source_seed": baseline_seed,
            "triggers_per_positive_family": config["baseline"][
                "triggers_per_positive_family"
            ],
        },
        "neutron_key_distinction": {
            "eligible_weighted_table_rows": neutron["weighted_table_rows"],
            "current_unique_rows": neutron["baseline_unique_rows"],
            "individual_position_target_mass_coverage": neutron[
                "baseline_target_row_mass_coverage"
            ],
            "individual_position_target_mass_unseen": neutron[
                "baseline_target_row_mass_unseen"
            ],
            "vn_za_group_target_mass_unseen": neutron[
                "baseline_target_group_mass_unseen"
            ],
            "manifest_vn_za_group_activity_unseen": neutron[
                "manifest_missed_vn_za_activity_fraction"
            ],
            "warning": "the_about_0p515_percent_group_miss_is_not_a_bound_on_the_about_34p79_percent_individual_position_mass_unseen_or_on_W511_rate",
            "sampling_interpretation": "the_M50000_rows_are_an_iid_probability_sample_from_p; unseen_target_rows_limit_row_level_attribution_but_do_not_by_themselves_block_an_aggregate_Var_p(q)_estimate_from_K_over_M",
        },
        "source_only_resampling": {
            "status": "PASS_SOURCE_LAYER_DIAGNOSTICS_ONLY",
            "m_values": m_values,
            "source_seeds": seeds,
            "rows_csv": "source_only/source_only_resampling.csv",
            "aggregate": source_aggregate,
            "boundary": "cannot_establish_post_selection_rate_convergence",
        },
        "retained_transport_and_lineage": {
            "primary_response_seed": lineage_authority["response_seed"],
            "selected_physical_events": len(base_events),
            "selected_rate_cps": base_total_rate,
            "weighted_poisson_transport_counting_sigma_cps": transport_sigma,
            "weighted_poisson_transport_counting_rse": transport_sigma
            / base_total_rate,
            "neutron_selected_physical_events": neutron_events,
            "neutron_poisson_counting_rse": 1.0 / math.sqrt(neutron_events),
            "raw_sim_bindings_imported_from_hash_frozen_lineage_authority": raw_sim_bindings,
            "raw_sim_reparsed_by_this_program": True,
            "raw_sim_parse_summary_csv": "data/raw_sim_parse_summary.csv",
            "raw_sim_parse_audit": raw_parse_rows,
            "selected_indicator_contract": (
                "all seven 1M-event SIMs retain one IA INIT per ID; the exact 64-seed "
                "response replay enumerates all final delayed W511 strong-lineage keys; "
                "the complement is selected=0"
            ),
        },
        "raw_cluster_finite_m_analysis": {
            "status": "CONDITIONAL_SINGLE_M_SAMPLE_K_OVER_M_FACTORIAL_MOMENT_ESTIMATE",
            "row_clusters_csv": "data/raw_sim_source_row_clusters.csv",
            "response_seed_lineage_csv": "data/response_seed_selected_lineage.csv",
            "variance_by_response_seed_csv": "data/cluster_source_variance_by_response_seed.csv",
            "poisson_bootstrap_primary_seed_csv": "data/cluster_poisson_bootstrap_primary_seed.csv",
            "neutron_primary_exact_position": neutron_position_cluster_primary,
            "neutron_primary_vn_za_constant_q_model": neutron_group_cluster_primary,
            "neutron_primary_nearest_all_mapping_sensitivity": neutron_position_mapping_sensitivity,
            "all_family_primary_exact_position": all_family_exact_primary,
            "neutron_ranges_across_64_response_seeds": neutron_response_seed_ranges,
            "primary_rate_variance_formula": "Sj~Poisson(T*A*(Kj/M)*hj); Var_rate_at_M=A^2*Var_p(h)/M, with per-block selected yield h as the primary rate variable",
            "primary_rate_debiased_moment": "E_p(h^2)=sum[(K/M)*Sj*(Sj-1)/(T*A*K/M)^2]; mu_h^2=S_total*(S_total-1)/(T*A)^2; multiply their difference by M/(M-1) then clip at zero",
            "q_selection_probability_diagnostic": "E_p(q^2) uses sum[(K/M)*s*(s-1)/(n*(n-1))] and removes Binomial transport noise, but raw n share is measurably not K/M, so q alone is not the selected-rate M variance",
            "poisson_pair_upper": "the exact same-row repeated-success-pair count is converted to a one-sided 95% rare-Poisson mean upper; max[2*(K/M)/(T*A*K/M)^2] gives a conservative h^2 upper before conversion to rate CV",
            "poisson_bootstrap": "Poissonized M-block multiplicities use fixed hhat=S/(T*A*K/M) for the primary rate-yield diagnostic and fixed qhat=S/n separately; transport outcomes are not resampled",
            "identification_boundary": [
                "target rows absent from the M50000 probability sample cannot receive row-specific q attribution, but their absence alone is not an aggregate source-variance blocker",
                "vn_za result assumes constant q within each group and therefore suppresses within-group spatial heterogeneity",
                "naive row variance contains finite-transport noise; sparse debiasing can be negative and is then reported both raw and clipped",
                "raw transport trial share differs materially from K/M because per-block event-generation intensity varies; h, not q alone, is therefore the rate authority",
                "the repeated-pair upper is a declared rare-pair Poisson approximation and its CV uses the point mean",
                "bootstrap conditions on fitted qhat and is not a transport confidence interval",
            ],
        },
        "conditional_existing_event_reweight": {
            "csv": "data/conditional_selected_rate_reweight.csv",
            "formula_truncated": "sum_selected_event[(1_div_TE_family)*(g_candidate_row_div_g_retained_row)]",
            "formula_hajek_within_retained_support": "truncated_rate_div_candidate_fraction_on_retained_row_support_computed_per_family_then_summed",
            "status": "CONDITIONAL_DIAGNOSTIC_NOT_UNBIASED_FOR_UNOBSERVED_RETAINED_ROW_SUPPORT",
            "limitations": [
                "rows absent from the retained M=50000 draw have no transport outcome",
                "hypothetical source-draw reweight table uses primary-response events; all 64 retained response seeds are analyzed separately in the raw-cluster output",
                "the same selected physical events are reused for every candidate draw",
                "candidate importance ESS and unseen-support fraction must be read with each rate",
            ],
        },
        "retained_response_seed_ensemble": {
            "authority_status": response_authority["status"],
            "replicas": len(response_raw["replicas"]),
            "summary_csv": "data/response_seed_ensemble_summary.csv",
            "event_level_replay": response_event_replay_audit,
            "event_level_selected_lineage_csv": "data/response_seed_selected_lineage.csv",
            "warning": "64_response_seeds_are_analysis_only_replicas_of_the_same_transport_events_not_64_independent_transport_samples",
        },
        "preexisting_frozen_selection_blocker": {
            "status": "NOT_REPAIRED_IN_WP1_OFFLINE_M_ANALYSIS",
            "predicate": "ACTIVE_SHIELD substring matching also classifies passive ActiveShield_S3C_BGO_Kapton_* volumes as active veto",
            "actual_frozen_veto_scope": "BGO plus plastic plus Kapton volumes captured by the stored name predicate",
            "impact": "all response replay and finite-M selected indicators exactly reproduce the frozen predicate; they do not validate its physical correctness",
            "rerun_performed": False,
        },
        "missing_identification": [
            "no independent source-seed transport realizations for a direct between-realization cross-check; the reported estimator instead uses the single iid M-block probability sample",
            "no row-specific q attribution for target rows outside the retained M-block sample; this is distinct from aggregate Var_p(q) estimation",
            "only 60 primary-response neutron W511 events and 78 all-family events",
            "BUILDUP yield uncertainty is not addressed by source-table resampling",
            "source seed and transport seed were not separated in the retained baseline",
            "rare-pair 95% upper remains a Poisson approximation rather than independent-source-seed empirical coverage",
        ],
        "stop_conditions": [
            "any frozen input hash mismatch",
            "source card fails exact blockwise replay",
            "selected lineage does not uniquely reconnect to its weighted-table row",
            "raw IA INIT nearest-neighbor mapping violates its displacement, second-gap, or distance-ratio guard",
            "the rare-pair factorial-moment upper is approximate and does not replace independent-source-seed or multi-M validation, even when its numerical 95% upper is below the handoff 10% subcriterion",
            "importance ESS is small or candidate mass outside retained support is material",
            "transport counting RSE remains above the requested precision",
            "attempt to interpret 64 response seeds as independent transport statistics",
            "attempt to use Var_p(q) alone as selected-rate M variance despite measured raw trial share differing from K/M",
            "attempt to promote the frozen selected rate without resolving the passive-Kapton active-veto predicate blocker",
        ],
        "claim_boundary": {
            "allowed": [
                "PASS_SOURCE_LAYER_REPLAY",
                "CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE",
                "CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS",
            ],
            "forbidden": [
                "PASS_M50000_CONDITIONAL_ON_FIXED_BUILDUP",
                "PASS_M_SAMPLING",
                "transport_backed_convergence",
            ],
        },
    }
    write_json(DATA / "m_sampling_offline_summary.json", summary)
    write_output_manifest(config, str(summary["status"]))
    print(json.dumps({
        "status": summary["status"],
        "neutron_position_mass_coverage": summary["neutron_key_distinction"]["individual_position_target_mass_coverage"],
        "neutron_vn_za_mass_unseen": summary["neutron_key_distinction"]["vn_za_group_target_mass_unseen"],
        "selected_events": len(base_events),
        "outputs": str(PACKAGE.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--manifest-only"]:
        manifest_config = load_json(CONFIG_PATH)
        manifest_summary = load_json(DATA / "m_sampling_offline_summary.json")
        write_output_manifest(manifest_config, str(manifest_summary["status"]))
        print("PASS_OUTPUT_MANIFEST_REFRESH_ONLY")
        raise SystemExit(0)
    if sys.argv[1:]:
        raise SystemExit(f"unsupported arguments: {sys.argv[1:]}")
    raise SystemExit(main())
