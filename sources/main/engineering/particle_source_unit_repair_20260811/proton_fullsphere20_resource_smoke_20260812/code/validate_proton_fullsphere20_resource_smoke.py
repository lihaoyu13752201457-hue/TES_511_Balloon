#!/usr/bin/env python3
"""Fail-closed dynamic validator for the full-spectrum proton resource smoke."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import smoke_common as common


GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$")
ID_RE = re.compile(r"^ID\s+(\d+)(?:\s|$)")


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def spectrum_points(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) == 3 and fields[0] == "DP":
            points.append((float(fields[1]), float(fields[2])))
    if len(points) < 2 or any(not math.isfinite(x) or not math.isfinite(y) for x, y in points):
        raise RuntimeError(f"invalid spectrum points: {common.rel(path)}")
    return points


def support_by_bin() -> dict[int, tuple[float, float]]:
    manifest = common.load_json(common.SOURCE_CONTRACT)
    rows = [row for row in manifest["spectra"]["files"] if row.get("family") == "p"]
    if len(rows) != 20:
        raise RuntimeError(f"source contract has {len(rows)} proton spectra")
    supports: dict[int, tuple[float, float]] = {}
    for row in rows:
        index = int(row["bin_id"])
        path = common.resolve_repo_path(row["corrected_spectrum"])
        if common.sha256(path) != row["corrected_sha256"]:
            raise RuntimeError(f"proton spectrum hash mismatch: {common.rel(path)}")
        points = spectrum_points(path)
        supports[index] = (min(x for x, _ in points), max(x for x, _ in points))
    if set(supports) != set(range(20)):
        raise RuntimeError("proton spectrum bin IDs are not exactly 0..19")
    return supports


def parse_init(line: str) -> dict[str, float | int]:
    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise ValueError(f"malformed IA INIT with {len(fields)} fields")
    values: dict[str, float | int] = {
        "particle_type": int(fields[15]),
        "dir_x": float(fields[16]),
        "dir_y": float(fields[17]),
        "dir_z": float(fields[18]),
        "energy_keV": float(fields[22]),
    }
    if not all(math.isfinite(float(value)) for value in values.values()):
        raise ValueError("non-finite IA INIT field")
    return values


def angular_bin_from_dir_z(dir_z: float) -> int:
    # The inward IA direction is opposite the FarFieldAreaSource direction.
    return max(0, min(19, int(math.floor((1.0 + dir_z) * 10.0))))


def scan_sim(
    path: Path,
    *,
    expected_events: int,
    expected_seed: int,
    expected_geometry: Path,
    supports: dict[int, tuple[float, float]],
) -> dict[str, Any]:
    problems: list[str] = []
    ids: list[int] = []
    header_geometry: str | None = None
    header_seed: int | None = None
    current: dict[str, Any] | None = None
    event_metrics: list[dict[str, Any]] = []
    init_records = 0
    bad_particle = 0
    bad_direction = 0
    bad_energy = 0
    energies: list[float] = []
    total_uncompressed_bytes = 0
    total_lines = 0
    total_cc = 0
    total_ia = 0

    def problem(message: str) -> None:
        if len(problems) < 30:
            problems.append(message)

    def finish_event() -> None:
        nonlocal current
        if current is None:
            return
        if current["init_count"] != 1:
            problem(f"ID {current['event_id']}: IA INIT count={current['init_count']}, expected 1")
        event_metrics.append(current)
        current = None

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            encoded_bytes = len(raw.encode("utf-8"))
            total_uncompressed_bytes += encoded_bytes
            total_lines += 1
            line = raw.strip()
            if header_geometry is None and (match := GEOMETRY_RE.match(line)):
                header_geometry = match.group(1)
            if header_seed is None and line.startswith("Seed "):
                try:
                    header_seed = int(line.split()[1])
                except (IndexError, ValueError):
                    problem(f"malformed SIM Seed header: {line}")
            if line == "SE":
                finish_event()
                continue
            if match := ID_RE.match(line):
                if current is not None:
                    problem(f"ID {current['event_id']}: next ID before SE")
                    finish_event()
                event_id = int(match.group(1))
                ids.append(event_id)
                current = {
                    "event_id": event_id,
                    "uncompressed_bytes": encoded_bytes,
                    "lines": 1,
                    "cc_records": 0,
                    "ia_records": 0,
                    "init_count": 0,
                    "initial_energy_keV": None,
                }
                continue
            if current is not None:
                current["uncompressed_bytes"] += encoded_bytes
                current["lines"] += 1
                if line.startswith("CC "):
                    current["cc_records"] += 1
                    total_cc += 1
                if line.startswith("IA "):
                    current["ia_records"] += 1
                    total_ia += 1
            if not line.startswith("IA INIT"):
                continue
            if current is None:
                problem("IA INIT outside an event")
                continue
            current["init_count"] += 1
            init_records += 1
            try:
                init = parse_init(line)
            except Exception as exc:
                problem(f"ID {current['event_id']}: {exc}")
                continue
            if int(init["particle_type"]) != 4:
                bad_particle += 1
            direction = (
                float(init["dir_x"]),
                float(init["dir_y"]),
                float(init["dir_z"]),
            )
            norm = math.sqrt(math.fsum(value * value for value in direction))
            if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5.0e-4):
                bad_direction += 1
            energy = float(init["energy_keV"])
            energies.append(energy)
            current["initial_energy_keV"] = energy
            angular_bin = angular_bin_from_dir_z(direction[2])
            low, high = supports[angular_bin]
            tolerance = max(0.002, 1.0e-10 * max(abs(low), abs(high)))
            if not low - tolerance <= energy <= high + tolerance:
                neighbors = [
                    supports[index]
                    for index in (angular_bin - 1, angular_bin + 1)
                    if index in supports
                ]
                if not any(lo - tolerance <= energy <= hi + tolerance for lo, hi in neighbors):
                    bad_energy += 1
        finish_event()

    if header_geometry is None:
        problem("missing SIM Geometry header")
    elif common.resolve_repo_path(header_geometry) != expected_geometry.resolve():
        problem(f"wrong SIM Geometry header: {header_geometry}")
    if header_seed != expected_seed:
        problem(f"SIM Seed={header_seed}, expected {expected_seed}")
    if ids != list(range(1, expected_events + 1)):
        problem(f"SIM IDs are not exactly 1..{expected_events}; observed {len(ids)}")
    if init_records != expected_events:
        problem(f"IA INIT records={init_records}, expected {expected_events}")
    if bad_particle:
        problem(f"wrong IA INIT particle type records={bad_particle}")
    if bad_direction:
        problem(f"non-unit IA INIT direction records={bad_direction}")
    if bad_energy:
        problem(f"IA INIT energy outside corrected bin support records={bad_energy}")

    top_events = sorted(
        event_metrics,
        key=lambda row: int(row["uncompressed_bytes"]),
        reverse=True,
    )[:10]
    compressed_bytes = path.stat().st_size
    return {
        "events": len(ids),
        "ia_init_records": init_records,
        "energy_min_keV": min(energies) if energies else None,
        "energy_max_keV": max(energies) if energies else None,
        "energy_over_100GeV": sum(value > 1.0e8 for value in energies),
        "energy_over_200GeV": sum(value > 2.0e8 for value in energies),
        "bad_energy_records": bad_energy,
        "bad_particle_records": bad_particle,
        "bad_direction_records": bad_direction,
        "geometry_header": header_geometry,
        "seed_header": header_seed,
        "compressed_bytes": compressed_bytes,
        "uncompressed_bytes": total_uncompressed_bytes,
        "compression_ratio": total_uncompressed_bytes / compressed_bytes if compressed_bytes else None,
        "lines": total_lines,
        "cc_records": total_cc,
        "ia_records": total_ia,
        "top_events_by_uncompressed_bytes": top_events,
        "problems": problems,
    }


def parse_isotope_dat(path: Path) -> dict[str, Any]:
    tt_values: list[float] = []
    rp_count = 0
    rp_sum = 0.0
    current_volume: str | None = None
    end_count = 0
    problems: list[str] = []
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT":
            value = parse_float(fields[1]) if len(fields) == 2 else None
            if value is None or value <= 0:
                problems.append(f"line {line_number}: invalid TT")
            else:
                tt_values.append(value)
        elif fields[0] == "VN":
            current_volume = line[2:].strip()
            if not current_volume:
                problems.append(f"line {line_number}: empty VN")
        elif fields[0] == "RP":
            if len(fields) != 4 or current_volume is None:
                problems.append(f"line {line_number}: malformed or unscoped RP")
                continue
            try:
                isotope_id = int(fields[1])
            except ValueError:
                isotope_id = -1
            excitation = parse_float(fields[2])
            value = parse_float(fields[3])
            if (
                isotope_id <= 0
                or excitation is None
                or excitation < 0
                or value is None
                or value < 0
            ):
                problems.append(f"line {line_number}: invalid RP")
            else:
                rp_count += 1
                rp_sum = math.fsum((rp_sum, value))
        elif fields == ["EN"]:
            end_count += 1
        else:
            problems.append(f"line {line_number}: unknown record {fields[0]!r}")
    if len(tt_values) != 1:
        problems.append(f"TT record count={len(tt_values)}, expected 1")
    if end_count != 1:
        problems.append(f"EN record count={end_count}, expected 1")
    return {
        "TT_s": tt_values[0] if len(tt_values) == 1 else None,
        "RP_record_count": rp_count,
        "sum_RP": rp_sum,
        "problems": problems,
    }


def validate_receipt_artifacts(receipt: dict[str, Any]) -> None:
    if receipt.get("status") != "PASS_TRANSPORT_EXIT" or receipt.get("returncode") != 0:
        raise RuntimeError("transport receipt is not a clean PASS")
    if receipt.get("contract_sha256") != common.sha256(common.CONTRACT):
        raise RuntimeError("receipt/contract hash binding failed")
    for artifact in receipt.get("artifacts", []):
        path = common.resolve_repo_path(artifact["path"])
        if (
            not path.is_file()
            or path.stat().st_size != int(artifact["size_bytes"])
            or common.sha256(path) != artifact["sha256"]
        ):
            raise RuntimeError(f"receipt artifact drifted: {artifact['path']}")


def validate_job(
    spec: dict[str, Any],
    contract: dict[str, Any],
    supports: dict[int, tuple[float, float]],
) -> dict[str, Any]:
    label = spec["key"]
    receipt_path = Path(spec["receipt"])
    if not receipt_path.is_file():
        raise RuntimeError(f"{label}: missing receipt")
    receipt = common.load_json(receipt_path)
    validate_receipt_artifacts(receipt)
    for key in ("job_source", "sim", "dat", "log"):
        path = Path(spec[key])
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"{label}: missing/empty {key}: {path}")
    expected_source = common.expected_job_source(spec)
    actual_source = Path(spec["job_source"]).read_text(encoding="utf-8")
    if actual_source != expected_source:
        raise RuntimeError(f"{label}: job source differs from the allowed deterministic transform")
    if receipt.get("job_source_sha256") != common.sha256(Path(spec["job_source"])):
        raise RuntimeError(f"{label}: receipt/job-source hash mismatch")
    if spec["mode"] == "instant" and "DecayMode" in actual_source:
        raise RuntimeError(f"{label}: instant source unexpectedly has DecayMode")
    if spec["mode"] == "buildup" and actual_source.count("DecayMode ActivationBuildUp") != 1:
        raise RuntimeError(f"{label}: buildup source lacks exactly one ActivationBuildUp mode")

    log = common.parse_log(Path(spec["log"]))
    if (
        log["returncode"] != 0
        or log["generated_particles"] != int(spec["events"])
        or log["cpu_s"] is None
        or log["cpu_s"] < 0
        or log["observation_time_s"] is None
        or log["observation_time_s"] <= 0
        or log["wall_s"] is None
        or log["wall_s"] <= 0
        or log["peak_process_group_rss_bytes"] is None
        or log["has_error_marker"]
        or not log["megalib_banner"]
    ):
        raise RuntimeError(f"{label}: invalid transport log summary: {log}")
    sim = scan_sim(
        Path(spec["sim"]),
        expected_events=int(spec["events"]),
        expected_seed=int(spec["seed"]),
        expected_geometry=common.resolve_repo_path(
            contract["source"]["cards"][spec["geometry"]]["geometry_setup"]
        ),
        supports=supports,
    )
    if sim["problems"]:
        raise RuntimeError(f"{label}: SIM validation problems: {sim['problems']}")
    isotope = parse_isotope_dat(Path(spec["dat"]))
    if isotope["problems"]:
        raise RuntimeError(f"{label}: DAT validation problems: {isotope['problems']}")
    if not math.isclose(
        float(isotope["TT_s"]),
        float(log["observation_time_s"]),
        rel_tol=2.0e-3,
        abs_tol=2.0e-6,
    ):
        raise RuntimeError(
            f"{label}: DAT TT {isotope['TT_s']} != log TT {log['observation_time_s']}"
        )
    directory_bytes = common.tree_size(Path(spec["directory"]))
    if directory_bytes > common.BATCH_OUTPUT_CAP_BYTES:
        raise RuntimeError(f"{label}: cell directory exceeds aggregate batch cap")
    return {
        "status": "PASS",
        "key": label,
        "geometry": spec["geometry"],
        "mode": spec["mode"],
        "events": spec["events"],
        "seed": spec["seed"],
        "source_sha256": common.sha256(Path(spec["job_source"])),
        "sim_sha256": common.sha256(Path(spec["sim"])),
        "dat_sha256": common.sha256(Path(spec["dat"])),
        "log_sha256": common.sha256(Path(spec["log"])),
        "sim_size_bytes": Path(spec["sim"]).stat().st_size,
        "dat_size_bytes": Path(spec["dat"]).stat().st_size,
        "log_size_bytes": Path(spec["log"]).stat().st_size,
        "directory_size_bytes": directory_bytes,
        "cpu_s": log["cpu_s"],
        "wall_s": log["wall_s"],
        "peak_process_group_rss_bytes": log["peak_process_group_rss_bytes"],
        "observation_time_s": log["observation_time_s"],
        "sim": sim,
        "isotope_dat": isotope,
        "rates": {
            "sim_gz_bytes_per_primary": Path(spec["sim"]).stat().st_size / int(spec["events"]),
            "sim_uncompressed_bytes_per_primary": sim["uncompressed_bytes"] / int(spec["events"]),
            "cpu_s_per_primary": log["cpu_s"] / int(spec["events"]),
            "wall_s_per_primary": log["wall_s"] / int(spec["events"]),
        },
    }


def build_summary(jobs: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    total_events = sum(int(row["events"]) for row in jobs)
    total_sim = sum(int(row["sim_size_bytes"]) for row in jobs)
    total_uncompressed = sum(int(row["sim"]["uncompressed_bytes"]) for row in jobs)
    total_cpu = math.fsum(float(row["cpu_s"]) for row in jobs)
    total_wall = math.fsum(float(row["wall_s"]) for row in jobs)
    targets = {
        "one_million_gamma_equivalent_per_geometry_mode": round(
            common.FLUX_CM2_S / 4.7996615777852 * 1_000_000
        ),
        "one_million_protons_per_geometry_mode": 1_000_000,
    }
    projections: dict[str, Any] = {}
    for target_name, events in targets.items():
        cells = []
        for row in jobs:
            cells.append(
                {
                    "key": row["key"],
                    "target_primaries": events,
                    "linear_sim_gz_bytes": row["rates"]["sim_gz_bytes_per_primary"] * events,
                    "linear_cpu_s": row["rates"]["cpu_s_per_primary"] * events,
                }
            )
        projections[target_name] = {
            "cells": cells,
            "aggregate_linear_sim_gz_bytes": math.fsum(
                item["linear_sim_gz_bytes"] for item in cells
            ),
            "aggregate_linear_cpu_s": math.fsum(item["linear_cpu_s"] for item in cells),
        }
    return {
        "schema_version": 1,
        "batch_id": common.BATCH_ID,
        "status": "PASS_RESOURCE_DIAGNOSTIC__NOT_MERGE_AUTHORITY",
        "authority_boundary": contract["authority_boundary"],
        "contract": common.rel(common.CONTRACT),
        "contract_sha256": common.sha256(common.CONTRACT),
        "sample": {
            "jobs": len(jobs),
            "events": total_events,
            "sim_gz_bytes": total_sim,
            "sim_uncompressed_bytes": total_uncompressed,
            "cpu_s": total_cpu,
            "serial_wall_s": total_wall,
            "peak_process_group_rss_bytes": max(
                int(row["peak_process_group_rss_bytes"]) for row in jobs
            ),
            "energy_min_keV": min(float(row["sim"]["energy_min_keV"]) for row in jobs),
            "energy_max_keV": max(float(row["sim"]["energy_max_keV"]) for row in jobs),
            "energy_over_100GeV": sum(int(row["sim"]["energy_over_100GeV"]) for row in jobs),
            "energy_over_200GeV": sum(int(row["sim"]["energy_over_200GeV"]) for row in jobs),
        },
        "jobs": jobs,
        "linear_planning_projections": projections,
        "projection_caveat": (
            "The direct EXPACS proton source is strongly heavy-tailed. These are linear point "
            "projections from 64 primaries per cell, not confidence bounds or capacity promises."
        ),
        "resource_limits": contract["resource_limits"],
    }


def run_validation(job_key: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not common.CONTRACT.is_file():
        raise RuntimeError("frozen contract is absent")
    contract = common.load_json(common.CONTRACT)
    if (
        contract.get("batch_id") != common.BATCH_ID
        or contract.get("status") != "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED"
        or contract.get("source", {}).get("source_contract_manifest_sha256")
        != common.SOURCE_CONTRACT_SHA256
        or contract.get("statistics", {}).get("events_per_job") != common.EVENTS_PER_JOB
        or contract.get("statistics", {}).get("job_count") != 4
        or contract.get("statistics", {}).get("total_primaries") != 256
    ):
        raise RuntimeError("frozen contract identity/statistics/source binding failed")
    common.static_gate()
    common.verify_input_snapshots(contract["frozen_inputs"])
    if common.canonical_digest(contract["frozen_inputs"]) != contract["frozen_inputs_digest"]:
        raise RuntimeError("frozen input inventory digest mismatch")
    specs = common.job_specs()
    if [common.serializable_job(row) for row in specs] != contract["statistics"]["jobs"]:
        raise RuntimeError("current fixed schedule differs from frozen contract")
    if job_key is not None:
        specs = [row for row in specs if row["key"] == job_key]
        if len(specs) != 1:
            raise RuntimeError(f"unknown job key: {job_key}")
    supports = support_by_bin()
    jobs = [validate_job(spec, contract, supports) for spec in specs]
    report = {
        "schema_version": 1,
        "validator": Path(__file__).name,
        "status": "PASS",
        "errors": [],
        "batch_id": common.BATCH_ID,
        "scope": job_key or "all_four_jobs",
        "authority_boundary": contract["authority_boundary"],
        "contract": common.rel(common.CONTRACT),
        "contract_sha256": common.sha256(common.CONTRACT),
        "checks": {
            "corrected_source_static_gate": "PASS",
            "frozen_input_hashes": "PASS",
            "deterministic_source_transform": "PASS",
            "transport_exit_and_log": "PASS",
            "sim_event_seed_geometry_particle_direction_energy": "PASS",
            "dat_tt_and_record_grammar": "PASS",
            "receipt_artifact_hashes": "PASS",
        },
        "jobs": jobs,
    }
    summary = build_summary(jobs, contract) if job_key is None else None
    return report, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate read-only")
    parser.add_argument("--job", help="validate one fixed job key")
    args = parser.parse_args()
    summary: dict[str, Any] | None = None
    try:
        report, summary = run_validation(args.job)
    except Exception as exc:
        report = {
            "schema_version": 1,
            "validator": Path(__file__).name,
            "status": "FAIL",
            "errors": [f"{type(exc).__name__}: {exc}"],
            "batch_id": common.BATCH_ID,
            "scope": args.job or "all_four_jobs",
        }
    if not args.check and args.job is None:
        if summary is not None:
            common.atomic_write_once_json(common.SUMMARY, summary)
            report["resource_summary"] = common.rel(common.SUMMARY)
            report["resource_summary_sha256"] = common.sha256(common.SUMMARY)
        common.atomic_write_once_json(common.VALIDATION_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
