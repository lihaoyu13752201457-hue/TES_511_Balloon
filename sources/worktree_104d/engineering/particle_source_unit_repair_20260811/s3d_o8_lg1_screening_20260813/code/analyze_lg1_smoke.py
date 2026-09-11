#!/usr/bin/env python3
"""Build the paired S3d-O8 LG1 smoke *diagnostic* after transport completes.

This program deliberately reports conditional event-record observables only.
It does not attach a sky normalization, calculate a background rate, apply the
TES detector response, calculate mission sensitivity, or promote a geometry.

The completed write-once SIM files are first passed through
``validate_lg1_smoke.validate_outputs``.  The analyzer then makes a second,
read-only pass over the validated records to accumulate exact-volume energy.
The two deliverables are published atomically and are never overwritten.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import validate_lg1_smoke as validate


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
DEFAULT_PLAN = PACKAGE / "data/smoke_plan.json"
OUTPUT_JSON = PACKAGE / "data/lg1_smoke_diagnostic.json"
OUTPUT_REPORT = PACKAGE / "LG1_SMOKE_DIAGNOSTIC.md"

THRESHOLDS_KEV = (1.0, 5.0, 10.0, 20.0, 50.0, 80.0)
RAW_W2_KEV = (510.58, 511.42)
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$", re.IGNORECASE)
KV_RE = re.compile(r"(\w+)=([^\s]+)")

STATUS = "PASS_LG1_SMOKE_PHYSICS_DIAGNOSTIC_NO_RATE_OR_PROMOTION_AUTHORITY"


def require(condition: bool, message: str) -> None:
    validate.require(condition, message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fraction(numerator: int, denominator: int) -> dict[str, int | float | None]:
    require(0 <= numerator <= denominator, f"invalid conditional count {numerator}/{denominator}")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": numerator / denominator if denominator else None,
    }


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    require(0.0 <= q <= 1.0, f"invalid quantile {q}")
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def energy_stats(values: Iterable[float]) -> dict[str, int | float | None]:
    materialized = [float(value) for value in values]
    require(all(math.isfinite(value) and value >= 0.0 for value in materialized), "invalid energy")
    positive = [value for value in materialized if value > 0.0]
    total = math.fsum(materialized)
    return {
        "event_count": len(materialized),
        "positive_event_count": len(positive),
        "sum_keV": total,
        "mean_all_events_keV": total / len(materialized) if materialized else None,
        "mean_positive_keV": math.fsum(positive) / len(positive) if positive else None,
        "median_positive_keV": statistics.median(positive) if positive else None,
        "p95_positive_keV": quantile(positive, 0.95),
        "max_keV": max(materialized) if materialized else None,
    }


def parse_edep(line: str) -> tuple[str, float]:
    fields = line.split()
    require(len(fields) >= 4 and fields[:2] == ["CC", "HIT"], f"malformed CC HIT: {line}")
    values = dict(KV_RE.findall(" ".join(fields[3:])))
    require("edep_keV" in values, f"CC HIT lacks edep_keV: {line}")
    try:
        energy = float(values["edep_keV"])
    except ValueError as exc:
        raise validate.ValidationError(f"non-numeric CC HIT energy: {line}") from exc
    require(math.isfinite(energy) and energy >= 0.0, f"invalid CC HIT energy: {line}")
    return fields[2], energy


def empty_event(
    local_id: int, original_active: tuple[str, ...], lg1_volumes: tuple[str, ...]
) -> dict[str, Any]:
    return {
        "local_id": local_id,
        "init_records": 0,
        "pair_records": 0,
        "anni_records": 0,
        "tes_cc_hit_records": 0,
        "tes_raw_keV": 0.0,
        "original_active_by_volume_keV": {volume: 0.0 for volume in original_active},
        "lg1_by_volume_keV": {volume: 0.0 for volume in lg1_volumes},
    }


def finalize_event(event: dict[str, Any]) -> None:
    event["original_active_total_keV"] = math.fsum(
        event["original_active_by_volume_keV"].values()
    )
    event["lg1_total_keV"] = math.fsum(event["lg1_by_volume_keV"].values())
    event["all_exact_active_total_keV"] = (
        event["original_active_total_keV"] + event["lg1_total_keV"]
    )
    event["has_pair"] = event["pair_records"] > 0
    event["has_anni"] = event["anni_records"] > 0
    event["tes_hit"] = event["tes_raw_keV"] > 0.0
    event["raw_w2"] = RAW_W2_KEV[0] <= event["tes_raw_keV"] < RAW_W2_KEV[1]


def parse_validated_sim(
    sim: Path,
    job: dict[str, Any],
    original_active: tuple[str, ...],
    lg1_volumes: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Extract event observables after the canonical validator has passed."""
    original_set = set(original_active)
    lg1_set = set(lg1_volumes)
    current: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []

    with gzip.open(sim, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                fields = line.split()
                require(len(fields) == 3 and fields[1] == fields[2], f"{job['job_id']}: invalid ID")
                require(current is None, f"{job['job_id']}: ID before previous SE")
                current = empty_event(int(fields[1]), original_active, lg1_volumes)
                continue
            # SIM v101 uses SE between events, while EN terminates the final
            # event directly.  Both records therefore close an active event.
            if line in {"SE", "EN"} and current is not None:
                finalize_event(current)
                events.append(current)
                current = None
                continue
            if current is None:
                continue
            if line.startswith("IA INIT"):
                current["init_records"] += 1
            elif line.startswith("IA PAIR"):
                current["pair_records"] += 1
            elif line.startswith("IA ANNI"):
                current["anni_records"] += 1
            elif line.startswith("CC HIT "):
                volume, energy = parse_edep(line)
                if TP_RE.fullmatch(volume):
                    current["tes_cc_hit_records"] += 1
                    current["tes_raw_keV"] += energy
                elif volume in original_set:
                    current["original_active_by_volume_keV"][volume] += energy
                elif volume in lg1_set:
                    current["lg1_by_volume_keV"][volume] += energy

    require(current is None, f"{job['job_id']}: unterminated final event")
    expected_ids = list(range(1, int(job["n_events"]) + 1))
    require(
        [event["local_id"] for event in events] == expected_ids,
        f"{job['job_id']}: analyzer ID sequence differs from validated sequence",
    )
    require(
        all(event["init_records"] == int(job["expected_init_per_event"]) for event in events),
        f"{job['job_id']}: analyzer INIT multiplicity mismatch",
    )
    return events


def event_ids(
    events: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> set[int]:
    return {int(event["local_id"]) for event in events if predicate(event)}


def threshold_record(events: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    all_ids = event_ids(events, lambda _event: True)
    pair_ids = event_ids(events, lambda event: bool(event["has_pair"]))
    anni_ids = event_ids(events, lambda event: bool(event["has_anni"]))
    tes_ids = event_ids(events, lambda event: bool(event["tes_hit"]))
    w2_ids = event_ids(events, lambda event: bool(event["raw_w2"]))
    original_cross = event_ids(
        events, lambda event: float(event["original_active_total_keV"]) >= threshold
    )
    lg1_cross = event_ids(events, lambda event: float(event["lg1_total_keV"]) >= threshold)
    combined_cross = event_ids(
        events, lambda event: float(event["all_exact_active_total_keV"]) >= threshold
    )
    original_pass = all_ids - original_cross
    w2_original_pass = w2_ids & original_pass

    conditions = {
        "diagnostic_generated": all_ids,
        "ia_pair_event": pair_ids,
        "ia_anni_event": anni_ids,
        "tes_hit_event": tes_ids,
        "raw_w2_event": w2_ids,
        "original_six_below_threshold": original_pass,
        "raw_w2_and_original_six_below_threshold": w2_original_pass,
    }
    conditional = {
        name: fraction(len(ids & lg1_cross), len(ids)) for name, ids in conditions.items()
    }
    return {
        "threshold_keV": threshold,
        "crossing_rule": "summed exact-volume energy_keV >= threshold_keV",
        "original_six_active": {
            "at_or_above_event_count": len(original_cross),
            "below_event_count": len(all_ids - original_cross),
        },
        "lg1_two_body": {
            "at_or_above_event_count": len(lg1_cross),
            "below_event_count": len(all_ids - lg1_cross),
        },
        "all_eight_exact_active": {
            "at_or_above_event_count": len(combined_cross),
            "below_event_count": len(all_ids - combined_cross),
        },
        "coincidence_event_counts": {
            "tes_hit_and_lg1": len(tes_ids & lg1_cross),
            "raw_w2_and_lg1": len(w2_ids & lg1_cross),
            "ia_pair_and_lg1": len(pair_ids & lg1_cross),
            "ia_anni_and_lg1": len(anni_ids & lg1_cross),
            "raw_w2_original_six_pass_and_lg1": len(w2_original_pass & lg1_cross),
        },
        "raw_w2_survival_counts": {
            "before_exact_active": len(w2_ids),
            "after_original_six": len(w2_ids - original_cross),
            "after_original_six_plus_lg1": len(w2_ids - combined_cross),
        },
        "lg1_conditional_interception": conditional,
    }


def summarize_job(
    job: dict[str, Any],
    validation_row: dict[str, Any],
    events: list[dict[str, Any]],
    original_active: tuple[str, ...],
    lg1_volumes: tuple[str, ...],
) -> dict[str, Any]:
    threshold_rows = [threshold_record(events, threshold) for threshold in THRESHOLDS_KEV]
    original_values = [float(event["original_active_total_keV"]) for event in events]
    lg1_values = [float(event["lg1_total_keV"]) for event in events]
    tes_values = [float(event["tes_raw_keV"]) for event in events]
    return {
        "job_id": job["job_id"],
        "cell_id": job["cell_id"],
        "geometry_key": job["geometry_key"],
        "seed": job["seed"],
        "generated": len(events),
        "validated_sim": {
            "path": validation_row["sim"],
            "sha256": validation_row["sha256"],
            "size_bytes": validation_row["size_bytes"],
            "geometry_header": validation_row["geometry"],
            "seed_header": validation_row["seed"],
            "gzip_eof_and_trailer_pass": validation_row["gzip_eof_and_trailer_pass"],
        },
        "ia": {
            "init_record_count": sum(int(event["init_records"]) for event in events),
            "pair_event_count": sum(bool(event["has_pair"]) for event in events),
            "pair_record_count": sum(int(event["pair_records"]) for event in events),
            "anni_event_count": sum(bool(event["has_anni"]) for event in events),
            "anni_record_count": sum(int(event["anni_records"]) for event in events),
        },
        "tes_raw": {
            "definition": "sum of unbroadened CC HIT edep_keV over exact TP_Ln_pixel volumes",
            "energy": energy_stats(tes_values),
            "cc_hit_record_count": sum(int(event["tes_cc_hit_records"]) for event in events),
            "tes_hit_event_count": sum(bool(event["tes_hit"]) for event in events),
            "raw_w2_half_open_keV": list(RAW_W2_KEV),
            "raw_w2_event_count": sum(bool(event["raw_w2"]) for event in events),
        },
        "original_six_active_exact": {
            "volumes": list(original_active),
            "summed_energy": energy_stats(original_values),
            "per_volume": {
                volume: energy_stats(
                    float(event["original_active_by_volume_keV"][volume]) for event in events
                )
                for volume in original_active
            },
        },
        "lg1_two_body_exact": {
            "volumes": list(lg1_volumes),
            "summed_energy": energy_stats(lg1_values),
            "per_volume": {
                volume: energy_stats(float(event["lg1_by_volume_keV"][volume]) for event in events)
                for volume in lg1_volumes
            },
        },
        "threshold_diagnostics": threshold_rows,
    }


def cell_kind(cell_id: str) -> str:
    if cell_id == "focused_first1000":
        return "focused_signal_prefix"
    if cell_id.startswith("gamma_root_"):
        return "serialized_directional_gamma"
    if cell_id == "back_to_back511_successor":
        return "forced_back_to_back511_diagnostic"
    raise validate.ValidationError(f"unknown diagnostic cell: {cell_id}")


def matched_contingency(
    a_events: list[dict[str, Any]],
    b_events: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, int]:
    a_ids = event_ids(a_events, predicate)
    b_ids = event_ids(b_events, predicate)
    all_ids = {int(event["local_id"]) for event in a_events}
    return {
        "both": len(a_ids & b_ids),
        "A_only": len(a_ids - b_ids),
        "B_only": len(b_ids - a_ids),
        "neither": len(all_ids - a_ids - b_ids),
    }


def threshold_lookup(summary: dict[str, Any], threshold: float) -> dict[str, Any]:
    matches = [
        row for row in summary["threshold_diagnostics"] if row["threshold_keV"] == threshold
    ]
    require(len(matches) == 1, f"missing threshold row {threshold}")
    return matches[0]


def cell_observable_view(summary: dict[str, Any]) -> dict[str, Any]:
    """Expose every requested per-cell observable without SIM metadata duplication."""
    return {
        "job_id": summary["job_id"],
        "generated": summary["generated"],
        "ia": summary["ia"],
        "tes_raw": summary["tes_raw"],
        "original_six_active_exact": summary["original_six_active_exact"],
        "lg1_two_body_exact": summary["lg1_two_body_exact"],
        "threshold_diagnostics": summary["threshold_diagnostics"],
    }


def build_cell(
    cell_id: str,
    pair: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
    events_by_job: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    by_geometry = {job["geometry_key"]: job for job in pair}
    require(set(by_geometry) == {"A_baseline", "B_lg1"}, f"{cell_id}: invalid A/B pair")
    a_job = by_geometry["A_baseline"]
    b_job = by_geometry["B_lg1"]
    a_summary = summaries[a_job["job_id"]]
    b_summary = summaries[b_job["job_id"]]
    a_events = events_by_job[a_job["job_id"]]
    b_events = events_by_job[b_job["job_id"]]
    a_ids = [int(event["local_id"]) for event in a_events]
    b_ids = [int(event["local_id"]) for event in b_events]
    require(a_ids == b_ids, f"{cell_id}: paired analyzer IDs differ")
    require(a_job["seed"] == b_job["seed"], f"{cell_id}: paired seeds differ")

    deltas = {
        "generated_B_minus_A": b_summary["generated"] - a_summary["generated"],
        "ia_pair_events_B_minus_A": (
            b_summary["ia"]["pair_event_count"] - a_summary["ia"]["pair_event_count"]
        ),
        "ia_anni_events_B_minus_A": (
            b_summary["ia"]["anni_event_count"] - a_summary["ia"]["anni_event_count"]
        ),
        "tes_hit_events_B_minus_A": (
            b_summary["tes_raw"]["tes_hit_event_count"]
            - a_summary["tes_raw"]["tes_hit_event_count"]
        ),
        "raw_w2_events_B_minus_A": (
            b_summary["tes_raw"]["raw_w2_event_count"]
            - a_summary["tes_raw"]["raw_w2_event_count"]
        ),
        "tes_raw_sum_keV_B_minus_A": (
            b_summary["tes_raw"]["energy"]["sum_keV"]
            - a_summary["tes_raw"]["energy"]["sum_keV"]
        ),
        "original_six_energy_sum_keV_B_minus_A": (
            b_summary["original_six_active_exact"]["summed_energy"]["sum_keV"]
            - a_summary["original_six_active_exact"]["summed_energy"]["sum_keV"]
        ),
        "lg1_energy_sum_keV_B_minus_A": (
            b_summary["lg1_two_body_exact"]["summed_energy"]["sum_keV"]
            - a_summary["lg1_two_body_exact"]["summed_energy"]["sum_keV"]
        ),
    }
    thresholds: list[dict[str, Any]] = []
    for threshold in THRESHOLDS_KEV:
        a_row = threshold_lookup(a_summary, threshold)
        b_row = threshold_lookup(b_summary, threshold)
        b_guard_ids = event_ids(
            b_events, lambda event, t=threshold: float(event["lg1_total_keV"]) >= t
        )
        a_tes_ids = event_ids(a_events, lambda event: bool(event["tes_hit"]))
        a_w2_ids = event_ids(a_events, lambda event: bool(event["raw_w2"]))
        a_old_pass_ids = event_ids(
            a_events, lambda event, t=threshold: float(event["original_active_total_keV"]) < t
        )
        a_w2_old_pass_ids = a_w2_ids & a_old_pass_ids
        thresholds.append(
            {
                "threshold_keV": threshold,
                "A_guard_coincidence_with_tes_hit": a_row["coincidence_event_counts"][
                    "tes_hit_and_lg1"
                ],
                "B_guard_coincidence_with_tes_hit": b_row["coincidence_event_counts"][
                    "tes_hit_and_lg1"
                ],
                "guard_tes_coincidence_B_minus_A": (
                    b_row["coincidence_event_counts"]["tes_hit_and_lg1"]
                    - a_row["coincidence_event_counts"]["tes_hit_and_lg1"]
                ),
                "A_guard_coincidence_with_raw_w2": a_row["coincidence_event_counts"][
                    "raw_w2_and_lg1"
                ],
                "B_guard_coincidence_with_raw_w2": b_row["coincidence_event_counts"][
                    "raw_w2_and_lg1"
                ],
                "guard_raw_w2_coincidence_B_minus_A": (
                    b_row["coincidence_event_counts"]["raw_w2_and_lg1"]
                    - a_row["coincidence_event_counts"]["raw_w2_and_lg1"]
                ),
                "B_raw_w2_survival_after_original_six_plus_lg1": b_row[
                    "raw_w2_survival_counts"
                ]["after_original_six_plus_lg1"],
                "matched_A_tes_hit_intercepted_by_B_lg1": fraction(
                    len(a_tes_ids & b_guard_ids), len(a_tes_ids)
                ),
                "matched_A_raw_w2_intercepted_by_B_lg1": fraction(
                    len(a_w2_ids & b_guard_ids), len(a_w2_ids)
                ),
                "matched_A_raw_w2_original_pass_intercepted_by_B_lg1": fraction(
                    len(a_w2_old_pass_ids & b_guard_ids), len(a_w2_old_pass_ids)
                ),
            }
        )

    result = {
        "cell_id": cell_id,
        "kind": cell_kind(cell_id),
        "paired_seed": a_job["seed"],
        "A_job_id": a_job["job_id"],
        "B_job_id": b_job["job_id"],
        "A_observables": cell_observable_view(a_summary),
        "B_observables": cell_observable_view(b_summary),
        "A_B_differences": deltas,
        "matched_event_contingency": {
            "tes_hit": matched_contingency(a_events, b_events, lambda event: bool(event["tes_hit"])),
            "raw_w2": matched_contingency(a_events, b_events, lambda event: bool(event["raw_w2"])),
            "ia_pair": matched_contingency(a_events, b_events, lambda event: bool(event["has_pair"])),
            "ia_anni": matched_contingency(a_events, b_events, lambda event: bool(event["has_anni"])),
        },
        "threshold_A_B_comparison": thresholds,
        "conditional_interception_contract": (
            "Every fraction is conditional on this finite prerecorded diagnostic tape and the "
            "named event subset. It is not an isotropic-sky, atmospheric, or mission probability."
        ),
        "A_conditional_interception": {
            str(int(row["threshold_keV"])): row["lg1_conditional_interception"]
            for row in a_summary["threshold_diagnostics"]
        },
        "B_conditional_interception": {
            str(int(row["threshold_keV"])): row["lg1_conditional_interception"]
            for row in b_summary["threshold_diagnostics"]
        },
    }
    if cell_id == "focused_first1000":
        result["focused_observables"] = {
            "A_tes_hit_event_count": a_summary["tes_raw"]["tes_hit_event_count"],
            "B_tes_hit_event_count": b_summary["tes_raw"]["tes_hit_event_count"],
            "tes_hit_B_minus_A": deltas["tes_hit_events_B_minus_A"],
            "A_raw_w2_event_count": a_summary["tes_raw"]["raw_w2_event_count"],
            "B_raw_w2_event_count": b_summary["tes_raw"]["raw_w2_event_count"],
            "raw_w2_B_minus_A": deltas["raw_w2_events_B_minus_A"],
            "threshold_guard_coincidence_and_survival": thresholds,
        }
    return result


def ratio_text(value: dict[str, Any]) -> str:
    if value["denominator"] == 0:
        return "0/0 (undefined)"
    return f"{value['numerator']}/{value['denominator']} ({value['fraction']:.6g})"


def build_report(payload: dict[str, Any], json_sha256: str) -> str:
    jobs = {row["job_id"]: row for row in payload["jobs"]}
    lines = [
        "# S3d-O8 LG1 paired smoke diagnostic",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a finite-tape physical diagnostic with no sky normalization. Counts and "
        "fractions below are conditional on the prerecorded focused, directional, or forced "
        "back-to-back-511 inputs. They are not background rates, mission sensitivities, or a "
        "geometry-promotion result.",
        "",
        f"Diagnostic JSON SHA256: `{json_sha256}`",
        "",
        "## Exact-volume contract",
        "",
        "Original active volumes:",
        "",
    ]
    lines.extend(f"- `{volume}`" for volume in payload["contracts"]["original_six_active_volumes"])
    lines.extend(["", "LG1 volumes:", ""])
    lines.extend(f"- `{volume}`" for volume in payload["contracts"]["lg1_two_body_volumes"])
    lines.extend(
        [
            "",
            "## Per-job raw diagnostics",
            "",
            "| job | geometry | generated | PAIR events/records | ANNI events/records | TES-hit | raw W2 | old6 ≥50 keV | LG1 ≥1 keV | LG1 ≥50 keV |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for job in payload["jobs"]:
        t1 = threshold_lookup(job, 1.0)
        t50 = threshold_lookup(job, 50.0)
        lines.append(
            f"| {job['job_id']} | {job['geometry_key']} | {job['generated']} | "
            f"{job['ia']['pair_event_count']}/{job['ia']['pair_record_count']} | "
            f"{job['ia']['anni_event_count']}/{job['ia']['anni_record_count']} | "
            f"{job['tes_raw']['tes_hit_event_count']} | {job['tes_raw']['raw_w2_event_count']} | "
            f"{t50['original_six_active']['at_or_above_event_count']} | "
            f"{t1['lg1_two_body']['at_or_above_event_count']} | "
            f"{t50['lg1_two_body']['at_or_above_event_count']} |"
        )

    lines.extend(
        [
            "",
            "## A/B event-count differences",
            "",
            "| cell | kind | ΔPAIR events | ΔANNI events | ΔTES-hit | Δraw W2 |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for cell in payload["cells"]:
        delta = cell["A_B_differences"]
        lines.append(
            f"| {cell['cell_id']} | {cell['kind']} | {delta['ia_pair_events_B_minus_A']} | "
            f"{delta['ia_anni_events_B_minus_A']} | {delta['tes_hit_events_B_minus_A']} | "
            f"{delta['raw_w2_events_B_minus_A']} |"
        )

    focused = next(cell for cell in payload["cells"] if cell["cell_id"] == "focused_first1000")
    focused_obs = focused["focused_observables"]
    lines.extend(
        [
            "",
            "## Focused first-1000 diagnostic",
            "",
            f"TES-hit A/B: {focused_obs['A_tes_hit_event_count']}/{focused_obs['B_tes_hit_event_count']} "
            f"(B−A {focused_obs['tes_hit_B_minus_A']:+d}). Raw-W2 A/B: "
            f"{focused_obs['A_raw_w2_event_count']}/{focused_obs['B_raw_w2_event_count']} "
            f"(B−A {focused_obs['raw_w2_B_minus_A']:+d}).",
            "",
            "| threshold (keV) | A guard∩TES | B guard∩TES | Δ | A guard∩raw-W2 | B guard∩raw-W2 | Δ | B raw-W2 after old6+LG1 | matched A raw-W2 intercepted in B |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in focused_obs["threshold_guard_coincidence_and_survival"]:
        lines.append(
            f"| {row['threshold_keV']:g} | {row['A_guard_coincidence_with_tes_hit']} | "
            f"{row['B_guard_coincidence_with_tes_hit']} | {row['guard_tes_coincidence_B_minus_A']:+d} | "
            f"{row['A_guard_coincidence_with_raw_w2']} | {row['B_guard_coincidence_with_raw_w2']} | "
            f"{row['guard_raw_w2_coincidence_B_minus_A']:+d} | "
            f"{row['B_raw_w2_survival_after_original_six_plus_lg1']} | "
            f"{ratio_text(row['matched_A_raw_w2_intercepted_by_B_lg1'])} |"
        )

    lines.extend(
        [
            "",
            "## Directional and forced-511 conditional LG1 interception (candidate B)",
            "",
            "The denominator is always shown. Undefined zero-denominator conditions are not "
            "silently converted to zero probability.",
            "",
            "| cell | threshold (keV) | given generated | given IA PAIR | given IA ANNI | given old6 pass | given raw-W2 & old6 pass |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for cell in payload["cells"]:
        if cell["kind"] == "focused_signal_prefix":
            continue
        for threshold in THRESHOLDS_KEV:
            conditional = cell["B_conditional_interception"][str(int(threshold))]
            lines.append(
                f"| {cell['cell_id']} | {threshold:g} | "
                f"{ratio_text(conditional['diagnostic_generated'])} | "
                f"{ratio_text(conditional['ia_pair_event'])} | "
                f"{ratio_text(conditional['ia_anni_event'])} | "
                f"{ratio_text(conditional['original_six_below_threshold'])} | "
                f"{ratio_text(conditional['raw_w2_and_original_six_below_threshold'])} |"
            )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            payload["claim_boundary"],
            "",
            "The raw W2 count uses unbroadened TES CC HIT energy only. No pixel threshold, "
            "energy response, topology, active-veto timing, accidental coincidence, activation, "
            "or delayed-background model is applied here.",
            "",
        ]
    )
    # Guard against accidentally introducing forbidden normalization language in a future edit.
    report = "\n".join(lines)
    require("cps" not in report.lower(), "report unexpectedly contains a rate unit")
    require("F3" not in report, "report unexpectedly contains a mission sensitivity symbol")
    require(set(jobs) == {row["job_id"] for row in payload["jobs"]}, "job report map mismatch")
    return report


def write_temp(target: Path, payload: bytes) -> Path:
    temp = target.with_name(f".{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    descriptor = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def atomic_publish_pair(outputs: list[tuple[Path, bytes]]) -> None:
    """Publish same-filesystem hard links without ever replacing a target."""
    require(len(outputs) == 2, "expected exactly two diagnostic outputs")
    for target, _payload in outputs:
        require(target.parent.is_dir(), f"missing output parent: {target.parent}")
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing diagnostic: {target}")

    temporaries: list[tuple[Path, Path]] = []
    published: list[tuple[Path, Path]] = []
    lock = PACKAGE / ".lg1_smoke_diagnostic.publish.lock"
    lock_descriptor: int | None = None
    try:
        temporaries = [(target, write_temp(target, payload)) for target, payload in outputs]
        lock_descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        for target, _temp in temporaries:
            if target.exists():
                raise FileExistsError(f"refusing concurrent overwrite: {target}")
        for target, temp in temporaries:
            os.link(temp, target)
            published.append((target, temp))
        for directory in {target.parent for target, _temp in published}:
            directory_descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except BaseException:
        for target, temp in reversed(published):
            try:
                if target.exists() and temp.exists() and os.path.samefile(target, temp):
                    target.unlink()
            except OSError:
                pass
        raise
    finally:
        for _target, temp in temporaries:
            temp.unlink(missing_ok=True)
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            lock.unlink(missing_ok=True)


def run(plan_path: Path) -> dict[str, Any]:
    plan_path = plan_path.resolve()
    require(plan_path == DEFAULT_PLAN.resolve(), f"analysis is frozen to {DEFAULT_PLAN}")
    if OUTPUT_JSON.exists() or OUTPUT_REPORT.exists():
        existing = [str(path) for path in (OUTPUT_JSON, OUTPUT_REPORT) if path.exists()]
        raise FileExistsError(f"refusing to overwrite diagnostic outputs: {existing}")

    initial_plan_sha256 = validate.sha256_file(plan_path)
    plan = validate.load_plan(plan_path)
    dynamic = validate.validate_outputs(plan)
    require(
        dynamic["status"] == "PASS_DYNAMIC_RECORD_SMOKE_NO_RATE_CONCLUSION",
        "canonical dynamic validation did not pass",
    )
    validation_by_job = {row["job_id"]: row for row in dynamic["jobs"]}
    require(len(validation_by_job) == len(plan["jobs"]) == 16, "expected 16 validated SIM jobs")

    geometry_validation_path = Path(plan["geometry_validation"]["path"])
    geometry_validation = json.loads(geometry_validation_path.read_text(encoding="utf-8"))
    active_exact = tuple(str(volume) for volume in geometry_validation["active_veto_exact_list"])
    lg1_volumes = tuple(str(volume) for volume in plan["geometries"]["B_lg1"]["guard_volumes"])
    require(len(active_exact) == 8 and len(set(active_exact)) == 8, "active exact list is not 8 unique volumes")
    require(len(lg1_volumes) == 2 and active_exact[-2:] == lg1_volumes, "LG1 exact list mismatch")
    original_active = active_exact[:-2]
    require(len(original_active) == 6, "original active exact list is not six volumes")

    events_by_job: dict[str, list[dict[str, Any]]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for job in plan["jobs"]:
        validation_row = validation_by_job[job["job_id"]]
        sim = Path(validation_row["sim"])
        require(validate.sha256_file(sim) == validation_row["sha256"], f"SIM changed after validation: {sim}")
        events = parse_validated_sim(sim, job, original_active, lg1_volumes)
        events_by_job[job["job_id"]] = events
        summaries[job["job_id"]] = summarize_job(
            job, validation_row, events, original_active, lg1_volumes
        )

    by_cell: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in plan["jobs"]:
        by_cell[job["cell_id"]].append(job)
    require(len(by_cell) == 8, "expected eight paired diagnostic cells")
    cells = [
        build_cell(cell_id, by_cell[cell_id], summaries, events_by_job)
        for cell_id in sorted(by_cell)
    ]
    baseline_lg1_zero = all(
        summaries[job["job_id"]]["lg1_two_body_exact"]["summed_energy"]["sum_keV"] == 0.0
        for job in plan["jobs"]
        if job["geometry_key"] == "A_baseline"
    )
    require(baseline_lg1_zero, "baseline unexpectedly has exact LG1 energy")
    require(
        validate.sha256_file(plan_path) == initial_plan_sha256,
        "smoke plan changed during diagnostic analysis",
    )

    payload = {
        "schema_version": 1,
        "status": STATUS,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "S3d-O8 LG1 paired finite-tape physical smoke diagnostic",
        "claim_boundary": plan["claim_boundary"],
        "interpretation": (
            "Generated counts, exact-volume energy deposits, and conditional interception "
            "fractions apply only to the finite prerecorded smoke tapes. No sky normalization, "
            "physical background rate, detector-response sensitivity, or geometry promotion is inferred."
        ),
        "contracts": {
            "thresholds_keV": list(THRESHOLDS_KEV),
            "threshold_crossing_rule": "summed exact-volume energy_keV >= threshold_keV",
            "raw_w2_half_open_keV": list(RAW_W2_KEV),
            "tes_raw_definition": "unbroadened sum of exact TP_Ln_pixel CC HIT edep_keV",
            "original_six_active_volumes": list(original_active),
            "lg1_two_body_volumes": list(lg1_volumes),
            "normalization": "none",
        },
        "inputs": {
            "smoke_plan": {"path": str(plan_path), "sha256": initial_plan_sha256},
            "geometry_validation": {
                "path": str(geometry_validation_path),
                "sha256": validate.sha256_file(geometry_validation_path),
                "status": geometry_validation["status"],
            },
            "analyzer": {"path": str(HERE), "sha256": validate.sha256_file(HERE)},
            "canonical_dynamic_validation": dynamic,
        },
        "checks": {
            "validated_sim_jobs": len(validation_by_job),
            "paired_cells": len(cells),
            "all_generated_match_plan": all(
                summaries[job["job_id"]]["generated"] == job["n_events"] for job in plan["jobs"]
            ),
            "all_sim_hashes_rechecked_after_validation": True,
            "all_A_B_event_id_sequences_match": True,
            "baseline_exact_lg1_energy_zero": baseline_lg1_zero,
            "plan_hash_stable_during_analysis": True,
            "output_refuses_overwrite": True,
            "output_atomic_publish": "same-filesystem no-replace hard-link publication",
        },
        "jobs": [summaries[job["job_id"]] for job in plan["jobs"]],
        "cells": cells,
    }

    json_payload = (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    json_sha256 = sha256_bytes(json_payload)
    report_payload = build_report(payload, json_sha256).encode("utf-8")
    atomic_publish_pair([(OUTPUT_JSON, json_payload), (OUTPUT_REPORT, report_payload)])
    return {
        "status": STATUS,
        "json": {
            "path": str(OUTPUT_JSON),
            "sha256": validate.sha256_file(OUTPUT_JSON),
            "size_bytes": OUTPUT_JSON.stat().st_size,
        },
        "report": {
            "path": str(OUTPUT_REPORT),
            "sha256": validate.sha256_file(OUTPUT_REPORT),
            "size_bytes": OUTPUT_REPORT.stat().st_size,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()
    result = run(args.plan)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
