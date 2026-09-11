#!/usr/bin/env python3
"""Historical and remaining seven-family retain-all accounting.

This module deliberately produces no compact-performance estimate before the
28-cell matched smoke runs.  It separates event-bearing SIM bytes from fixed
per-job artifacts, credits only hash-pinned batch0000--0005 jobs, and leaves
all confidence-bound performance conclusions null/blocked.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from manifest_discovery import AUTHORITY_REGISTRY, load_authority
from preflight_common import ROOT, rel, repo_path, sha256, strict_json, verify_file


FAMILIES = ("gamma", "alpha", "eminus", "eplus", "muminus", "muplus", "n")
GEOMETRIES = ("mass_model_511", "s3d_o8")
MODES = ("instant", "buildup")
TARGET_EVENTS_PER_CELL = {
    "gamma": 10_000_000,
    "alpha": 191_464,
    "eminus": 3_316_936,
    "eplus": 1_949_816,
    "muminus": 82_824,
    "muplus": 92_840,
    "n": 7_704_528,
}

PINNED_CREDIT_AUTHORITIES: tuple[dict[str, str], ...] = (
    {
        "batch": "batch0000", "path": "runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_ledger.json",
        "sha256": "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f",
        "status": "PASS__BATCH0000_MERGE_ELIGIBLE",
        "validation_path": "runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_validation.json",
        "validation_sha256": "2fbc8a3c08e4544f127c1acf0e45f58790e18b51cdb9cce0128bbe3a14761760",
        "validation_status": "PASS",
    },
    {
        "batch": "batch0001", "path": AUTHORITY_REGISTRY["batch0001"]["path"],
        "sha256": AUTHORITY_REGISTRY["batch0001"]["sha256"],
        "status": AUTHORITY_REGISTRY["batch0001"]["status"],
        "validation_path": AUTHORITY_REGISTRY["batch0001"]["validation_path"],
        "validation_sha256": AUTHORITY_REGISTRY["batch0001"]["validation_sha256"],
        "validation_status": AUTHORITY_REGISTRY["batch0001"]["validation_status"],
    },
    {
        "batch": "batch0002", "path": "runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_ledger.json",
        "sha256": "742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62",
        "status": "PASS__BATCH0002_MERGE_ELIGIBLE",
        "validation_path": "runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_validation.json",
        "validation_sha256": "faf37b3cfbf533c5ac12f0ab3efb83e6ffdb4c6a5abaaf7786856de4b94b3004",
        "validation_status": "PASS",
    },
    {
        "batch": "batch0003", "path": AUTHORITY_REGISTRY["batch0003_prefix76"]["path"],
        "sha256": AUTHORITY_REGISTRY["batch0003_prefix76"]["sha256"],
        "status": AUTHORITY_REGISTRY["batch0003_prefix76"]["status"],
        "validation_path": AUTHORITY_REGISTRY["batch0003_prefix76"]["validation_path"],
        "validation_sha256": AUTHORITY_REGISTRY["batch0003_prefix76"]["validation_sha256"],
        "validation_status": AUTHORITY_REGISTRY["batch0003_prefix76"]["validation_status"],
    },
    {
        "batch": "batch0004", "path": (
            "runs/particle_source_unit_repair_20260811/seven_family_1m_screening_batch0004_partial_checkpoint_20260812/"
            "batch0004_partial_through_ordinal0097_v1_ledger.json"
        ),
        "sha256": "b4de513e7902ae4755eb741e7a79d23c378b3e3dd8cee993c7ffbff1af19dba0",
        "status": "PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE",
        "validation_path": (
            "runs/particle_source_unit_repair_20260811/seven_family_1m_screening_batch0004_partial_checkpoint_20260812/"
            "batch0004_partial_through_ordinal0097_v1_validation.json"
        ),
        "validation_sha256": "3d29449dd80051c1faf60fb8156fb757a11004981f426e22eac36b7bd56fe291",
        "validation_status": "PASS",
    },
    {
        "batch": "batch0005", "path": (
            "runs/particle_source_unit_repair_20260811/reduced_breadth_continuation_batch0005_v1_ledger.json"
        ),
        "sha256": "670bc6f14de7799306301343908f524738c564ac62161caab1206a0be5cc41a0",
        "status": "PASS__BATCH0005_REDUCED_BREADTH_ADDON_MERGE_ELIGIBLE",
        "validation_path": (
            "runs/particle_source_unit_repair_20260811/reduced_breadth_continuation_batch0005_v1_validation.json"
        ),
        "validation_sha256": "d100985b3cbecd267042bb4bfb0d23fa9794befdb748f7c2ca45f9abfdfc5cee",
        "validation_status": "PASS",
    },
)


def _load_credit_authority(spec: dict[str, str]) -> dict[str, Any]:
    ledger = strict_json(verify_file(spec["path"], spec["sha256"]))
    validation = strict_json(verify_file(spec["validation_path"], spec["validation_sha256"]))
    if (
        ledger.get("status") != spec["status"]
        or ledger.get("errors") != []
        or validation.get("status") != spec["validation_status"]
        or validation.get("errors") != []
        or ledger.get("validation_report") != spec["validation_path"]
    ):
        raise ValueError(f"{spec['batch']}: ledger/validation pair is not closed")
    recorded = ledger.get("validation_report_sha256")
    if recorded is not None and recorded != spec["validation_sha256"]:
        raise ValueError(f"{spec['batch']}: recorded validation SHA drift")
    if spec["batch"] == "batch0001":
        load_authority("batch0001")
    elif spec["batch"] == "batch0003":
        load_authority("batch0003_prefix76")
    return ledger


def _campaign_calibration(campaign: dict[str, Any]) -> dict[str, dict[str, float]]:
    summary_path = repo_path(campaign["run_summary_csv"])
    if sha256(summary_path) != campaign["run_summary_csv_sha256"]:
        raise ValueError(f"run-summary hash drift: {rel(summary_path)}")
    ledger_jobs = {job["job_name"]: job for job in campaign["jobs"]}
    accumulated: dict[str, dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "sim_bytes": 0.0, "fixed_bytes": 0.0, "beam_on_elapsed_s": 0.0, "jobs": 0.0}
    )
    seen: set[str] = set()
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row["job_name"]
            if name not in ledger_jobs or row["status"] != "PASS" or name in seen:
                raise ValueError(f"unbound/non-PASS/duplicate run-summary row {name}")
            job = ledger_jobs[name]
            family = row["particle"]
            if int(row["events"]) != int(job["events"]) or family != job["family"]:
                raise ValueError(f"event/family mismatch for {name}")
            for summary_key, job_key in (("sim_path", "sim"), ("dat_path", "isotope_dat"), ("log", "log")):
                if repo_path(row[summary_key]) != repo_path(job[job_key]):
                    raise ValueError(f"artifact path mismatch for {name}:{summary_key}")
            paths = {key: repo_path(job[key]) for key in ("sim", "isotope_dat", "log", "job_source")}
            sim_bytes = paths["sim"].stat().st_size
            fixed_bytes = sum(paths[key].stat().st_size for key in ("isotope_dat", "log", "job_source"))
            if sim_bytes != int(row["sim_size_bytes"]):
                raise ValueError(f"SIM byte mismatch for {name}")
            target = accumulated[family]
            target["events"] += int(row["events"])
            target["sim_bytes"] += sim_bytes
            target["fixed_bytes"] += fixed_bytes
            # Historical runner calls this cpu_s, but the log marker is the
            # internal Cosima run timer.  It is not OS process CPU time.
            target["beam_on_elapsed_s"] += float(row["cpu_s"])
            target["jobs"] += 1
            seen.add(name)
    if seen != set(ledger_jobs) or set(accumulated) != set(FAMILIES):
        raise ValueError("calibration run-summary/job/seven-family closure failed")
    return dict(accumulated)


def _credit_and_current_disk() -> tuple[dict[tuple[str, str, str], int], list[dict[str, Any]], int, int]:
    credits: dict[tuple[str, str, str], int] = defaultdict(int)
    identities: set[tuple[str, str, str, str]] = set()
    artifacts: dict[str, int] = {}
    authorities: list[dict[str, Any]] = []
    seven_family_credit_total = 0
    for spec in PINNED_CREDIT_AUTHORITIES:
        ledger = _load_credit_authority(spec)
        batch_events = 0
        for campaign in ledger.get("campaigns", []):
            geometry, mode = campaign.get("geometry"), campaign.get("mode")
            for job in campaign.get("jobs", []):
                family = job.get("family")
                events = int(job.get("events", -1))
                sim_path = job.get("sim")
                identity = (geometry, mode, family, sim_path)
                if events <= 0 or identity in identities:
                    raise ValueError(f"{spec['batch']}: duplicate/invalid credited job identity")
                identities.add(identity)
                batch_events += events
                if family in FAMILIES:
                    credits[(geometry, mode, family)] += events
                    seven_family_credit_total += events
                for key in ("sim", "isotope_dat", "log", "job_source"):
                    path_value = job.get(key)
                    if not isinstance(path_value, str):
                        raise ValueError(f"{spec['batch']}: missing credited artifact {key}")
                    path = repo_path(path_value)
                    size = path.stat().st_size
                    if path_value in artifacts:
                        raise ValueError(f"duplicate credited artifact path across batches: {path_value}")
                    artifacts[path_value] = size
        authorities.append({**spec, "new_job_event_count_in_ledger": batch_events})
    return dict(credits), authorities, sum(artifacts.values()), seven_family_credit_total


def _positive_ratio_or_null(numerator: float | None, denominator: float | None) -> dict[str, Any]:
    if numerator is None or denominator is None or denominator <= 0.0:
        return {"value": None, "status": "BLOCKED__MISSING_OR_NONPOSITIVE_DENOMINATOR"}
    return {"value": numerator / denominator, "status": "DEFINED"}


def build_projection() -> dict[str, Any]:
    batch1 = load_authority("batch0001")
    calibration_by_cell: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
    for campaign in batch1["campaigns"]:
        calibration_by_cell[(campaign["geometry"], campaign["mode"])] = _campaign_calibration(campaign)
    credits, credit_authorities, current_retained_disk_bytes, credited_total = _credit_and_current_disk()

    records: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for mode in MODES:
            calibration = calibration_by_cell[(geometry, mode)]
            for family in FAMILIES:
                base = calibration[family]
                target_events = TARGET_EVENTS_PER_CELL[family]
                credited_events = credits.get((geometry, mode, family), 0)
                if not 0 <= credited_events <= target_events:
                    raise ValueError("credited events exceed historical cell target")
                remaining_events = target_events - credited_events
                sim_bytes_per_event = base["sim_bytes"] / base["events"]
                fixed_bytes_per_job = base["fixed_bytes"] / base["jobs"]
                events_per_calibration_job = base["events"] / base["jobs"]
                historical_job_count_model = math.ceil(target_events / events_per_calibration_job)
                remaining_job_count_model = math.ceil(remaining_events / events_per_calibration_job) if remaining_events else 0
                historical_bytes = target_events * sim_bytes_per_event + historical_job_count_model * fixed_bytes_per_job
                remaining_bytes = remaining_events * sim_bytes_per_event + remaining_job_count_model * fixed_bytes_per_job
                records.append(
                    {
                        "geometry": geometry,
                        "mode": mode,
                        "family": family,
                        "historical_target_events": target_events,
                        "credited_events_batch0000_through_batch0005": credited_events,
                        "remaining_events_after_pinned_credits": remaining_events,
                        "baseline_authority_ledger_path": AUTHORITY_REGISTRY["batch0001"]["path"],
                        "baseline_authority_ledger_sha256": AUTHORITY_REGISTRY["batch0001"]["sha256"],
                        "calibration_events": int(base["events"]),
                        "calibration_jobs": int(base["jobs"]),
                        "calibration_sim_bytes": int(base["sim_bytes"]),
                        "calibration_fixed_non_sim_bytes": int(base["fixed_bytes"]),
                        "calibration_beam_on_elapsed_s": base["beam_on_elapsed_s"],
                        "sim_bytes_per_event_point": sim_bytes_per_event,
                        "fixed_non_sim_bytes_per_job_point": fixed_bytes_per_job,
                        "calibration_events_per_job": events_per_calibration_job,
                        "historical_job_count_model": historical_job_count_model,
                        "remaining_job_count_model": remaining_job_count_model,
                        "historical_retain_all_bytes_point": historical_bytes,
                        "remaining_retain_all_bytes_point": remaining_bytes,
                        "compact_bytes_point": None,
                        "disk_upper95_bytes": None,
                        "reduction_lower95": None,
                        "performance_status": "BLOCKED__MATCHED_28_CELL_SMOKE_NOT_RUN",
                    }
                )
    records.sort(key=lambda row: (row["geometry"], row["mode"], row["family"]))
    expected_cells = {(g, m, f) for g in GEOMETRIES for m in MODES for f in FAMILIES}
    if len(records) != 28 or {(r["geometry"], r["mode"], r["family"]) for r in records} != expected_cells:
        raise ValueError("28-cell projection closure failed")
    historical_events = sum(row["historical_target_events"] for row in records)
    remaining_events = sum(row["remaining_events_after_pinned_credits"] for row in records)
    if historical_events != 93_353_632 or historical_events - remaining_events != credited_total:
        raise ValueError("historical/credit/remaining event arithmetic drift")
    historical_bytes = math.fsum(row["historical_retain_all_bytes_point"] for row in records)
    remaining_bytes = math.fsum(row["remaining_retain_all_bytes_point"] for row in records)
    impossible_speed = _positive_ratio_or_null(None, None)
    return {
        "schema_version": 2,
        "status": "PARTIAL__NO_GO_FULL_TARGET__PLANNED_28_CELLS_NOT_EXECUTED",
        "transport_events_launched": 0,
        "unit_policy": {"GB": "10^9 bytes", "GiB": "2^30 bytes", "TB": "10^12 bytes"},
        "families": list(FAMILIES),
        "geometry_count": 2,
        "mode_count": 2,
        "cell_count": 28,
        "planned_matched_subshards_per_cell": 4,
        "executed_cell_count": 0,
        "historical_total": {
            "events": historical_events,
            "retain_all_bytes_point": historical_bytes,
            "scope": "full frozen seven-family target before any batch credit",
        },
        "remaining_after_pinned_batch0000_through_batch0005": {
            "credited_events": credited_total,
            "remaining_events": remaining_events,
            "retain_all_bytes_point": remaining_bytes,
            "current_retained_plus_new_remaining_retain_all_bytes_point": (
                current_retained_disk_bytes + remaining_bytes
            ),
            "identity_rule": "each credited job is unique by geometry/mode/family/SIM path; no cumulative count is re-credited",
            "capacity_accounting_equation": (
                "current retained pinned-artifact stat bytes + modeled bytes for only the untransported target remainder"
            ),
        },
        "current_retained_disk": {
            "bytes": current_retained_disk_bytes,
            "scope": "current stat size of unique SIM/DAT/log/job-source artifacts named by the six pinned ledgers",
            "included_in_remaining_capacity_accounting": True,
        },
        "pinned_credit_authorities": credit_authorities,
        "storage_decomposition": {
            "event_variable": "SIM bytes / transported events from batch0001 calibration",
            "fixed_per_job": "DAT + log + generated job-source bytes / jobs from batch0001 calibration",
            "caveat": "DAT/log can also grow with event complexity; this is an explicit accounting model, not a causal fit",
        },
        "timing_semantics": {
            "calibration_beam_on_elapsed_s": (
                "retained run_summary cpu_s is renamed because its source is Cosima's 'Total CPU time spent in run' "
                "internal timer; it is not OS child-process CPU"
            ),
            "os_cpu": "must be measured independently as process-group user+system CPU in the future smoke",
        },
        "confidence_contract": {
            "current_disk_upper95_bytes": None,
            "current_reduction_lower95": None,
            "status": "BLOCKED__NO_MATCHED_SMOKE_DISTRIBUTIONS",
            "future_cell_estimator": (
                "four matched arm-order-rotated subshards per geometry/mode/family; separate fixed bytes/job and bytes/event"
            ),
            "paired_runtime_interval": (
                "per-cell paired log(F/C) interval using all positive wall and beam_on_elapsed observations; "
                "zero/nonfinite/impossible denominator yields null/BLOCKED"
            ),
            "disk_heavy_tail_bound": (
                "one-sided empirical-Bernstein bound per cell/artifact type using the preregistered 2-GB/job bound; "
                "Bonferroni alpha=0.05/28 before summing full-target cell upper bounds"
            ),
            "final_gate": "disk upper95 and reduction lower95 may be populated only from executed matched shards",
            "example_impossible_speed_denominator": impossible_speed,
        },
        "inference_boundary": (
            "This is historical/remaining retain-all accounting only. No compact capacity, runtime, transport-speed, "
            "or full-seven-family optimization claim exists before all 28 cells execute."
        ),
        "records": records,
    }
