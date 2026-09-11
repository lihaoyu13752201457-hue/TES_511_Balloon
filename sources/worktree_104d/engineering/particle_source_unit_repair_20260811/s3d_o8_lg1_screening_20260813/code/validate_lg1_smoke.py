#!/usr/bin/env python3
"""Validate frozen LG1 smoke inputs, and optionally completed SIM outputs.

Preflight is static and never invokes Cosima.  Output validation is structural:
it checks the EventList successor contract, A/B geometry and seed headers,
complete gzip/trailer/ID records, IA INIT multiplicity, and exact LG1 guard
``CC HIT`` UIDs.  It intentionally makes no physical-rate statement.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import build_lg1_smoke_inputs as build


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_plan(path: Path = build.PLAN) -> dict[str, Any]:
    require(path.is_file(), f"missing frozen smoke plan: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data.get("schema_version") == 1, "unsupported smoke plan schema")
    require(data.get("status") == "READY_FOR_EXPLICIT_LAUNCH_NO_TRANSPORT_RUN", "plan status is not launch-ready")
    require(data.get("confirmation_token") == build.CONFIRMATION, "confirmation token changed")
    return data


def parse_eventlist(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        fields = raw.split()
        require(len(fields) == 15, f"{path}:{number}: expected 15 EventList tokens, got {len(fields)}")
        try:
            row = {
                "id": int(fields[0]),
                "successor": int(fields[1]),
                "particle": int(fields[2]),
                "excitation": int(fields[3]),
                "time": float(fields[4]),
                "position": tuple(float(fields[index]) for index in (5, 6, 7)),
                "direction": tuple(float(fields[index]) for index in (8, 9, 10)),
                "polarization": tuple(float(fields[index]) for index in (11, 12, 13)),
                "energy": float(fields[14]),
            }
        except ValueError as exc:
            raise ValidationError(f"{path}:{number}: non-numeric EventList token") from exc
        require(row["successor"] in (0, 1), f"{path}:{number}: successor flag is not Boolean")
        require(row["particle"] == 1 and row["excitation"] == 0, f"{path}:{number}: not a ground-state gamma")
        norm = math.sqrt(math.fsum(value * value for value in row["direction"]))
        require(math.isclose(norm, 1.0, abs_tol=5e-4, rel_tol=0.0), f"{path}:{number}: direction norm {norm}")
        require(all(math.isfinite(value) for value in (*row["position"], *row["direction"], row["time"], row["energy"])), f"{path}:{number}: non-finite value")
        rows.append(row)
    return rows


def validate_tape(key: str, spec: dict[str, Any]) -> dict[str, Any]:
    path = Path(spec["path"])
    require(path.is_file(), f"missing tape {key}: {path}")
    require(sha256_file(path) == spec["sha256"], f"tape hash mismatch: {key}")
    rows = parse_eventlist(path)
    require(len(rows) == spec["rows"], f"{key}: row count mismatch")
    successors = sum(row["successor"] for row in rows)
    require(successors == spec["successor_rows"], f"{key}: successor count mismatch")

    kind = spec["kind"]
    if kind == "focused_first1000":
        require([row["id"] for row in rows] == list(range(1000)), "focused first1000 IDs are not exactly 0..999")
        require(all(row["successor"] == 0 and math.isclose(row["energy"], 511.0) for row in rows), "focused tape root/energy contract changed")
        authority = Path(spec["authority_path"])
        require(sha256_file(authority) == spec["authority_sha256"], "focused authority hash changed")
        prefix = "\n".join(line for line in authority.read_text(encoding="utf-8").splitlines() if line.strip()).splitlines()[:1000]
        digest = hashlib.sha256(("\n".join(prefix) + "\n").encode("utf-8")).hexdigest()
        require(digest == spec["first1000_sha256"] == spec["sha256"], "focused tape is not the exact authority prefix")
    elif kind == "serialized_directional_gamma":
        require([row["id"] for row in rows] == list(range(1, 513)), f"{key}: IDs are not 1..512")
        require(all(row["successor"] == 0 for row in rows), f"{key}: directional roots contain a successor")
        root = spec["serialized_root"]
        require(sha256_file(Path(root["sim_path"])) == root["sim_sha256"], f"{key}: serialized SIM authority changed")
        expected = root["init"]
        for row in rows:
            require(all(math.isclose(row["position"][i], expected["position_cm"][i], abs_tol=5e-9, rel_tol=0.0) for i in range(3)), f"{key}: root position changed")
            require(all(math.isclose(row["direction"][i], expected["direction"][i], abs_tol=5e-9, rel_tol=0.0) for i in range(3)), f"{key}: root direction changed")
            require(math.isclose(row["energy"], expected["energy_keV"], abs_tol=5e-7, rel_tol=0.0), f"{key}: root energy changed")
    elif kind == "back_to_back511_successor":
        require(len(spec["positions"]) >= 4 and len(spec["directions"]) >= 2, "successor cassette lacks position/direction breadth")
        require(len(rows) % 2 == 0, "successor cassette has an odd row count")
        require([row["id"] for row in rows] == list(range(1, len(rows) + 1)), "successor particle IDs are not consecutive")
        for offset in range(0, len(rows), 2):
            first, second = rows[offset : offset + 2]
            require(first["successor"] == 0 and second["successor"] == 1, f"successor pair {offset // 2}: flags are not 0,1")
            require(first["position"] == second["position"] and first["time"] == second["time"], f"successor pair {offset // 2}: not coincident")
            require(math.isclose(first["energy"], 511.0, abs_tol=1e-9) and math.isclose(second["energy"], 511.0, abs_tol=1e-9), f"successor pair {offset // 2}: not 511 keV")
            dot = math.fsum(first["direction"][i] * second["direction"][i] for i in range(3))
            require(math.isclose(dot, -1.0, abs_tol=2e-8, rel_tol=0.0), f"successor pair {offset // 2}: directions are not antiparallel ({dot})")
        require(len(rows) // 2 == spec["root_events"], "successor root-event count mismatch")
    else:
        raise ValidationError(f"unknown tape kind: {kind}")
    return {"rows": len(rows), "root_events": spec["root_events"], "successor_rows": successors}


def parse_source(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            continue
        key, value = fields
        if key == "Geometry":
            result["geometry"] = value
        elif key == "Seed":
            result["seed"] = int(value)
        elif key.endswith(".NEvents"):
            result["n_events"] = int(value)
        elif key.endswith(".FileName"):
            result["output_prefix"] = value
        elif key.endswith(".EventList"):
            result["eventlist"] = value
    return result


def validate_preflight(plan: dict[str, Any], *, require_clean_output: bool = True, rescan_registry: bool = True) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    validation_entry = plan["geometry_validation"]
    validation_path = Path(validation_entry["path"])
    require(sha256_file(validation_path) == validation_entry["sha256"], "canonical geometry validation changed after freezing")
    geometry_validation = json.loads(validation_path.read_text(encoding="utf-8"))
    require(geometry_validation.get("status") == validation_entry["status"] == "PASS_S3D_O8_LG1_STATIC_GEOMETRY_VALIDATION", "LG1 static geometry gate is not PASS")
    guard_uids = tuple(item["uid"] for item in geometry_validation["guard"]["volumes"])
    require(guard_uids == build.GUARD_VOLUMES, "guard UID contract changed")

    for geometry_key, geometry in plan["geometries"].items():
        setup = Path(geometry["setup"])
        require(setup.is_absolute() and setup.is_file(), f"{geometry_key}: setup is missing or non-absolute")
        require(sha256_file(setup) == geometry["setup_sha256"], f"{geometry_key}: setup hash mismatch")
    baseline_det = build.ROOT / geometry_validation["baseline"]["det"]["path"]
    candidate_det = build.ROOT / geometry_validation["candidate"]["det"]["path"]
    baseline_text = baseline_det.read_text(encoding="utf-8")
    candidate_text = candidate_det.read_text(encoding="utf-8")
    for uid in guard_uids:
        require(uid not in baseline_text, f"baseline unexpectedly declares LG1 guard {uid}")
        require(f".SensitiveVolume {uid}" in candidate_text and f".DetectorVolume {uid}" in candidate_text, f"candidate guard scorer mapping missing: {uid}")

    require(Path(plan["cosima"]["path"]).is_file(), "Cosima executable is absent")
    require(sha256_file(Path(plan["cosima"]["path"])) == plan["cosima"]["sha256"], "Cosima binary hash changed")
    limits = plan["limits"]
    require(limits["minimum_free_bytes"] == 20 * 1024**3, "free-space floor is not 20 GiB")
    require(limits["aggregate_output_max_bytes"] == 5_000_000_000, "aggregate cap is not <5 GB")
    require(limits["single_sim_max_bytes"] == 1024**3, "per-SIM cap is not 1 GiB")
    require(limits["per_job_timeout_seconds"] == 900, "per-job timeout is not 15 minutes")

    for entry in plan["input_files"]:
        path = Path(entry["path"])
        require(path.is_file(), f"missing frozen input: {path}")
        require(path.stat().st_size == entry["size_bytes"] and sha256_file(path) == entry["sha256"], f"frozen input changed: {path}")
    tape_results = {key: validate_tape(key, spec) for key, spec in plan["tapes"].items()}

    jobs = plan["jobs"]
    require(len(jobs) == 16 and plan["totals"]["paired_cells"] == 8, "expected 8 paired cells / 16 jobs")
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        by_cell.setdefault(job["cell_id"], []).append(job)
        source_path = Path(job["source"])
        require(sha256_file(source_path) == job["source_sha256"], f"source hash mismatch: {job['job_id']}")
        parsed = parse_source(source_path)
        geometry = plan["geometries"][job["geometry_key"]]
        require(parsed.get("geometry") == geometry["setup"], f"{job['job_id']}: source geometry mismatch")
        require(parsed.get("seed") == job["seed"], f"{job['job_id']}: source seed mismatch")
        require(parsed.get("n_events") == job["n_events"], f"{job['job_id']}: source NEvents mismatch")
        require(parsed.get("eventlist") == job["eventlist"], f"{job['job_id']}: source tape mismatch")
        require(parsed.get("output_prefix") == job["output_prefix_partial"], f"{job['job_id']}: source output prefix mismatch")
        require("cosima_spectra_dp_2602units" not in source_path.read_text(encoding="utf-8"), f"{job['job_id']}: legacy spectrum reference")
        if require_clean_output:
            require(not Path(job["partial_attempt_dir"]).exists(), f"write-once partial attempt already exists: {job['job_id']}")
            require(not Path(job["final_attempt_dir"]).exists(), f"write-once final attempt already exists: {job['job_id']}")

    observed_cell_seeds: set[int] = set()
    for cell, pair in by_cell.items():
        require(len(pair) == 2 and {job["geometry_key"] for job in pair} == {"A_baseline", "B_lg1"}, f"{cell}: not an A/B pair")
        require(len({job["seed"] for job in pair}) == 1, f"{cell}: A/B seeds differ")
        require(len({job["eventlist"] for job in pair}) == 1, f"{cell}: A/B tapes differ")
        seed = pair[0]["seed"]
        require(seed not in observed_cell_seeds, f"seed reused across paired cells: {seed}")
        observed_cell_seeds.add(seed)
    require(observed_cell_seeds == set(plan["seed_registry"]["planned_by_cell"].values()), "planned seed registry does not match jobs")

    if rescan_registry:
        # These report/diagnostic JSON files were created only after the
        # write-once plan was frozen.  They summarize this same batch (and the
        # diagnostic repeats its planned seeds), so exclude them from the
        # *external* registry rescan while still validating every source/SIM
        # seed below against the frozen plan.
        post_freeze_self_outputs = {
            build.PACKAGE / "data/lg1_smoke_diagnostic.json",
            build.PACKAGE / "data/optimization_summary.json",
            build.PACKAGE / "data/report_artifact.json",
        }
        current = build.scan_seed_registry(extra_excluded_files=post_freeze_self_outputs)
        frozen = plan["seed_registry"]
        for key in ("scan_roots", "excluded_prefixes", "file_counts", "record_count", "unique_seed_count", "records_sha256"):
            require(current[key] == frozen[key], f"external seed registry changed after freeze: {key}")
        expected_excluded_files = set(frozen["excluded_files"]) | {
            str(path.absolute()) for path in post_freeze_self_outputs
        }
        require(set(current["excluded_files"]) == expected_excluded_files, "external registry self-output exclusions differ")
        used = set(current["used_seeds"])
        collision = sorted(observed_cell_seeds & used)
        require(not collision, f"planned seeds collide with external registry: {collision}")
        checks["seed_registry_sha256"] = current["records_sha256"]

    checks.update(
        {
            "status": "PASS_STATIC_PREFLIGHT_NO_COSIMA_RUN",
            "geometry_status": geometry_validation["status"],
            "jobs": len(jobs),
            "paired_cells": len(by_cell),
            "fresh_seeds": sorted(observed_cell_seeds),
            "tapes": tape_results,
            "run_root_exists": Path(plan["run_root"]).exists(),
            "claim_boundary": plan["claim_boundary"],
        }
    )
    return checks


def find_final_sim(job: dict[str, Any]) -> Path:
    directory = Path(job["final_attempt_dir"])
    matches = sorted(path for path in directory.glob(f"{job['job_id']}*.sim.gz") if path.is_file())
    require(len(matches) == 1, f"{job['job_id']}: expected exactly one final SIM.gz, found {len(matches)}")
    return matches[0]


def validate_sim_file(job: dict[str, Any], sim: Path, plan: dict[str, Any]) -> dict[str, Any]:
    require(sim.is_file() and sim.suffix == ".gz", f"{job['job_id']}: missing gzip SIM")
    require(sim.stat().st_size < plan["limits"]["single_sim_max_bytes"], f"{job['job_id']}: SIM reached 1 GiB cap")
    header_geometry = None
    header_seed = None
    ids: list[int] = []
    current_id = None
    current_init = 0
    init_counts: list[int] = []
    guard_hits: Counter[str] = Counter()
    en_count = te_count = ts_count = 0
    ts_value = None
    with gzip.open(sim, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if header_geometry is None and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            if line.startswith("ID "):
                fields = line.split()
                require(len(fields) == 3, f"{job['job_id']}: malformed ID line")
                first, second = int(fields[1]), int(fields[2])
                require(first == second, f"{job['job_id']}: split ID pair {first},{second}")
                require(current_id is None, f"{job['job_id']}: new ID before previous SE")
                current_id = first
                current_init = 0
                ids.append(first)
            elif line.startswith("IA INIT"):
                require(current_id is not None, f"{job['job_id']}: IA INIT outside event")
                current_init += 1
            elif line.startswith("CC HIT "):
                fields = line.split()
                require(len(fields) >= 4 and "edep_keV=" in line, f"{job['job_id']}: malformed CC HIT")
                volume = fields[2]
                if volume in build.GUARD_VOLUMES:
                    guard_hits[volume] += 1
            elif line == "SE" and current_id is not None:
                init_counts.append(current_init)
                current_id = None
            elif line == "EN":
                # SIM v101 uses SE between events, but EN terminates the final
                # event directly.  Treat both records as event boundaries.
                if current_id is not None:
                    init_counts.append(current_init)
                    current_id = None
                en_count += 1
            elif line.startswith("TE "):
                te_count += 1
            elif line.startswith("TS "):
                ts_count += 1
                ts_value = int(line.split()[1])
    require(current_id is None, f"{job['job_id']}: unterminated final event")
    expected_ids = list(range(1, job["n_events"] + 1))
    require(ids == expected_ids, f"{job['job_id']}: ID sequence/count mismatch ({len(ids)} vs {job['n_events']})")
    require(init_counts == [job["expected_init_per_event"]] * job["n_events"], f"{job['job_id']}: IA INIT multiplicity mismatch")
    require(header_geometry == plan["geometries"][job["geometry_key"]]["setup"], f"{job['job_id']}: SIM geometry header mismatch")
    require(header_seed == job["seed"], f"{job['job_id']}: SIM seed header mismatch")
    require(en_count == te_count == ts_count == 1 and ts_value == job["n_events"], f"{job['job_id']}: EOF/trailer contract mismatch")
    if job["geometry_key"] == "A_baseline":
        require(not guard_hits, f"{job['job_id']}: baseline emitted LG1 guard CC HIT")
    if job["require_guard_cc_hit"]:
        require(sum(guard_hits.values()) > 0, f"{job['job_id']}: successor diagnostic produced no LG1 guard CC HIT")
    return {
        "sim": str(sim),
        "sha256": sha256_file(sim),
        "size_bytes": sim.stat().st_size,
        "events": len(ids),
        "seed": header_seed,
        "geometry": header_geometry,
        "guard_cc_hit_by_uid": dict(guard_hits),
        "guard_cc_hit_total": sum(guard_hits.values()),
        "gzip_eof_and_trailer_pass": True,
    }


def validate_outputs(plan: dict[str, Any]) -> dict[str, Any]:
    static = validate_preflight(plan, require_clean_output=False, rescan_registry=True)
    results = []
    aggregate = 0
    for job in plan["jobs"]:
        sim = find_final_sim(job)
        result = validate_sim_file(job, sim, plan)
        aggregate += result["size_bytes"]
        results.append({"job_id": job["job_id"], **result})
    require(aggregate < plan["limits"]["aggregate_output_max_bytes"], "aggregate SIM output reached 5 GB cap")
    return {
        "status": "PASS_DYNAMIC_RECORD_SMOKE_NO_RATE_CONCLUSION",
        "static_preflight": static["status"],
        "aggregate_sim_bytes": aggregate,
        "jobs": results,
        "claim_boundary": plan["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="validate frozen inputs only (default)")
    mode.add_argument("--outputs", action="store_true", help="validate completed write-once SIM outputs")
    parser.add_argument("--plan", type=Path, default=build.PLAN)
    args = parser.parse_args()
    plan = load_plan(args.plan)
    result = validate_outputs(plan) if args.outputs else validate_preflight(plan)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
