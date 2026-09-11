#!/usr/bin/env python3
"""Build the frozen, paired S3d-O8/LG1 first-pass smoke inputs.

This builder performs no transport.  It is deliberately write-once: the
generated ``smoke_inputs`` directory and ``data/smoke_plan.json`` must both be
absent.  Seeds are selected only after scanning JSON, source cards, and SIM
headers in both the active worktree and the retained repository authority.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
VALIDATION = PACKAGE / "data/lg1_geometry_validation.json"
PLAN = PACKAGE / "data/smoke_plan.json"
SMOKE_INPUTS = PACKAGE / "smoke_inputs"
RETAINED_ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260814_v1"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
FOCUSED_AUTHORITY = ROOT / (
    "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/"
    "eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
CONFIRMATION = "S3D_O8_LG1_SMOKE_V1"
GUARD_VOLUMES = (
    "BGO_S3D_O8_LG1_OpticalAxis_OpenWell_Side_5mm",
    "BGO_S3D_O8_LG1_OpticalAxis_BackAnnulus_3mm",
)

ROOT_CASES = (
    {
        "key": "gamma_root_4148keV_event3883",
        "event_id": 3883,
        "sim": Path(
            "/home/ubuntu/TES_511_Balloon/runs/particle_source_unit_repair_20260811/"
            "s3d_o8/instant_gamma_batch0003_v1/shards/shard0032/attempt01/"
            "Background_gamma_fullsphere20_batch0003_shard0032.inc1.id1.sim.gz"
        ),
        "sha256": "ca49d54d77c10a6b70b0fd284b36e58dbbfe9e6271818c47608c2eb1e79b41ee",
    },
    {
        "key": "gamma_root_5769keV_event19932",
        "event_id": 19932,
        "sim": Path(
            "/home/ubuntu/TES_511_Balloon/runs/particle_source_unit_repair_20260811/"
            "m05_16h_90gb_campaign_batch0006_v1/stage10_seven_family/S3d_O8/"
            "instant/gamma/shard0014/attempt01/"
            "s10_gamma_instant_S3d_O8_shard0014.inc1.id1.sim.gz"
        ),
        "sha256": "075e1f5e0d571e02422f67022d0f55c0f714c0278c61e42116fb51e6332c0aa2",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(records: Iterable[tuple[str, int, str]]) -> str:
    digest = hashlib.sha256()
    for path, seed, kind in sorted(records):
        digest.update(f"{kind}\t{seed}\t{path}\n".encode("utf-8"))
    return digest.hexdigest()


def _integer_values(value: Any) -> Iterable[int]:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        yield value
    elif isinstance(value, float) and value.is_integer():
        yield int(value)
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,10}", value.strip()):
        yield int(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _integer_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _integer_values(item)


def _json_seeds(value: Any) -> Iterable[int]:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower():
                yield from _integer_values(item)
            else:
                yield from _json_seeds(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_seeds(item)


def _is_excluded(path: Path, excluded_prefixes: tuple[Path, ...], excluded_files: set[Path]) -> bool:
    absolute = path.absolute()
    if absolute in excluded_files:
        return True
    return any(absolute == prefix or prefix in absolute.parents for prefix in excluded_prefixes)


def scan_seed_registry(*, extra_excluded_files: Iterable[Path] = ()) -> dict[str, Any]:
    """Scan all repository JSON/source/SIM headers, excluding this harness' outputs."""

    roots = tuple(dict.fromkeys(path.absolute() for path in (ROOT, RETAINED_ROOT) if path.is_dir()))
    excluded_prefixes = (SMOKE_INPUTS.absolute(), RUN_ROOT.absolute())
    excluded_files = {PLAN.absolute(), *(path.absolute() for path in extra_excluded_files)}
    records: set[tuple[str, int, str]] = set()
    counts = {"json": 0, "source": 0, "sim_header": 0}
    parse_errors: list[str] = []
    source_re = re.compile(r"(?:^|\s)(?:Seed|-s)\s+([0-9]{1,10})(?:\s|$)")
    header_re = re.compile(r"^Seed\s+([0-9]{1,10})\s*$")

    for scan_root in roots:
        for directory, names, files in os.walk(scan_root, followlinks=False):
            # Environment/tool distributions are not repository simulation
            # provenance.  In particular, ``.tools`` contains vendor JSON that
            # is intentionally not strict JSON.  All project trees, including
            # engineering, runs, outputs, old, inputs, and source cards, remain
            # in scope.
            names[:] = [
                name
                for name in names
                if name not in {".git", "__pycache__", ".tools", ".codex", ".agents", ".claude"}
            ]
            base = Path(directory)
            if _is_excluded(base, excluded_prefixes, excluded_files):
                names[:] = []
                continue
            for filename in files:
                path = base / filename
                if _is_excluded(path, excluded_prefixes, excluded_files):
                    continue
                kind = None
                if filename.endswith(".json"):
                    kind = "json"
                elif filename.endswith(".source"):
                    kind = "source"
                elif filename.endswith(".sim") or filename.endswith(".sim.gz"):
                    kind = "sim_header"
                if kind is None:
                    continue
                counts[kind] += 1
                label = str(path.absolute())
                try:
                    if kind == "json":
                        value = json.loads(path.read_text(encoding="utf-8"))
                        for seed in _json_seeds(value):
                            if 0 < seed <= 2_147_483_647:
                                records.add((label, seed, kind))
                    elif kind == "source":
                        for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
                            for match in source_re.finditer(line):
                                records.add((label, int(match.group(1)), kind))
                    else:
                        opener = gzip.open if filename.endswith(".gz") else open
                        with opener(path, "rt", encoding="utf-8", errors="strict") as handle:
                            for index, line in enumerate(handle):
                                text = line.strip()
                                if match := header_re.match(text):
                                    records.add((label, int(match.group(1)), kind))
                                if text == "SE" or index >= 511:
                                    break
                except (OSError, UnicodeError, json.JSONDecodeError, EOFError) as exc:
                    parse_errors.append(f"{label}: {type(exc).__name__}: {exc}")

    if parse_errors:
        preview = "\n".join(parse_errors[:20])
        raise RuntimeError(f"seed registry scan was not complete ({len(parse_errors)} errors):\n{preview}")
    used = sorted({seed for _, seed, _ in records})
    return {
        "scan_roots": [str(path) for path in roots],
        "excluded_prefixes": [str(path) for path in excluded_prefixes],
        "excluded_files": [str(path) for path in sorted(excluded_files)],
        "file_counts": counts,
        "record_count": len(records),
        "unique_seed_count": len(used),
        "records_sha256": canonical_digest(records),
        "used_seeds": used,
    }


def require_geometry_gate() -> dict[str, Any]:
    data = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if data.get("status") != "PASS_S3D_O8_LG1_STATIC_GEOMETRY_VALIDATION":
        raise RuntimeError(f"LG1 geometry validation is not PASS: {data.get('status')!r}")
    if data.get("checks", {}).get("cosima_run") is not False:
        raise RuntimeError("geometry gate must remain a static-only validation")
    volumes = tuple(item["uid"] for item in data.get("guard", {}).get("volumes", []))
    if volumes != GUARD_VOLUMES:
        raise RuntimeError(f"unexpected guard UID contract: {volumes!r}")
    for geometry_key in ("baseline", "candidate"):
        for artifact in ("geometry_setup", "geo", "det"):
            entry = data[geometry_key][artifact]
            path = ROOT / entry["path"]
            if not path.is_file() or sha256_file(path) != entry["sha256"]:
                raise RuntimeError(f"geometry authority mismatch: {path}")
    return data


def parse_interactions(case: dict[str, Any]) -> dict[str, Any]:
    path = case["sim"]
    if not path.is_file() or sha256_file(path) != case["sha256"]:
        raise RuntimeError(f"serialized-root authority mismatch: {path}")
    selected: list[dict[str, Any]] = []
    active = False
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                active = int(line.split()[1]) == case["event_id"]
            elif active and line.startswith("IA "):
                interaction = line.split()[1]
                fields = [field.strip() for field in line.split(interaction, 1)[1].split(";")]
                if len(fields) < 23:
                    raise RuntimeError(f"malformed {interaction} record in {path}")
                selected.append(
                    {
                        "interaction": interaction,
                        "position_cm": [float(fields[index]) for index in (4, 5, 6)],
                        "particle_type": int(fields[15]),
                        "direction": [float(fields[index]) for index in (16, 17, 18)],
                        "energy_keV": float(fields[22]),
                        "serialized_line": line,
                    }
                )
            elif active and line == "SE":
                break
    init = [row for row in selected if row["interaction"] == "INIT"]
    pair = [row for row in selected if row["interaction"] == "PAIR"]
    anni = [row for row in selected if row["interaction"] == "ANNI"]
    if len(init) != 1 or init[0]["particle_type"] != 1 or len(pair) < 2 or len(anni) != 2:
        raise RuntimeError(f"serialized-root event contract changed: {path} ID {case['event_id']}")
    if not math.isclose(init[0]["energy_keV"], 4148.290 if case["event_id"] == 3883 else 5768.820):
        raise RuntimeError("serialized-root energy changed")
    return {
        "key": case["key"],
        "event_id": case["event_id"],
        "sim_path": str(path),
        "sim_sha256": case["sha256"],
        "init": init[0],
        "pair_position_cm": pair[0]["position_cm"],
        "annihilation_position_cm": anni[0]["position_cm"],
        "annihilation_serialized_lines": [row["serialized_line"] for row in anni],
    }


def event_row(
    particle_id: int,
    successor: int,
    time_s: float,
    position: Iterable[float],
    direction: Iterable[float],
    energy_keV: float,
) -> str:
    x, y, z = position
    dx, dy, dz = direction
    return (
        f"{particle_id} {successor} 1 0 {time_s:.12e} "
        f"{x:.8f} {y:.8f} {z:.8f} {dx:.8f} {dy:.8f} {dz:.8f} "
        f"0 0 0 {energy_keV:.6f}"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def source_text(job: dict[str, Any], geometry: Path, tape: Path, output_prefix: Path) -> str:
    run_name = re.sub(r"[^A-Za-z0-9_]", "_", job["job_id"])
    source_name = f"{run_name}_PhaseSpace"
    return f"""# Frozen LG1 first-pass paired smoke input; no rate interpretation.
Version 1
Geometry {geometry}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {job['seed']}

Run {run_name}
{run_name}.FileName {output_prefix}
{run_name}.NEvents {job['n_events']}
{run_name}.Source {source_name}
{source_name}.EventList {tape}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if PLAN.exists() or SMOKE_INPUTS.exists():
        raise RuntimeError("write-once smoke inputs already exist; refusing to overwrite")
    geometry_validation = require_geometry_gate()
    registry = scan_seed_registry()
    used = set(registry.pop("used_seeds"))
    seed_cells = [
        "focused_first1000",
        "gamma_root_4148keV_rep01",
        "gamma_root_4148keV_rep02",
        "gamma_root_4148keV_rep03",
        "gamma_root_5769keV_rep01",
        "gamma_root_5769keV_rep02",
        "gamma_root_5769keV_rep03",
        "back_to_back511_successor",
    ]
    planned: dict[str, int] = {}
    candidate = 2_120_000_003
    for cell in seed_cells:
        while candidate in used or candidate > 2_147_483_647:
            candidate += 7919
        if candidate > 2_147_483_647:
            raise RuntimeError("no signed-32-bit fresh seed remains in reserved range")
        planned[cell] = candidate
        used.add(candidate)
        candidate += 7919

    roots = [parse_interactions(case) for case in ROOT_CASES]
    focused_lines = [line for line in FOCUSED_AUTHORITY.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(focused_lines) < 1000:
        raise RuntimeError("focused authority has fewer than 1000 rows")
    focused_lines = focused_lines[:1000]
    for index, line in enumerate(focused_lines):
        fields = line.split()
        if len(fields) != 15 or int(fields[0]) != index or int(fields[1]) != 0:
            raise RuntimeError(f"focused first1000 row {index} is not the frozen root-only sequence")

    with tempfile.TemporaryDirectory(prefix=".lg1_smoke_build_", dir=PACKAGE) as temp_name:
        stage = Path(temp_name)
        stage_inputs = stage / "smoke_inputs"
        eventlists = stage_inputs / "eventlists"
        eventlists.mkdir(parents=True)
        tape_specs: dict[str, dict[str, Any]] = {}

        focused_path = eventlists / "focused_first1000.eventlist.dat"
        write_text(focused_path, "\n".join(focused_lines) + "\n")
        tape_specs["focused_first1000"] = {
            "kind": "focused_first1000",
            "relative_path": "eventlists/focused_first1000.eventlist.dat",
            "rows": 1000,
            "root_events": 1000,
            "successor_rows": 0,
            "expected_init_per_event": 1,
            "authority_path": str(FOCUSED_AUTHORITY),
            "authority_sha256": sha256_file(FOCUSED_AUTHORITY),
            "first1000_sha256": sha256_file(focused_path),
        }

        for root in roots:
            key = root["key"]
            path = eventlists / f"{key}_512.eventlist.dat"
            init = root["init"]
            lines = [
                event_row(index + 1, 0, index * 1e-9, init["position_cm"], init["direction"], init["energy_keV"])
                for index in range(512)
            ]
            write_text(path, "\n".join(lines) + "\n")
            tape_specs[key] = {
                "kind": "serialized_directional_gamma",
                "relative_path": f"eventlists/{path.name}",
                "rows": 512,
                "root_events": 512,
                "successor_rows": 0,
                "expected_init_per_event": 1,
                "serialized_root": root,
            }

        b2b_path = eventlists / "back_to_back511_successor_4pos_6dir.eventlist.dat"
        positions = []
        for root in roots:
            positions.extend(
                [
                    {"label": f"{root['key']}_PAIR", "position_cm": root["pair_position_cm"], "provenance": root["sim_path"]},
                    {"label": f"{root['key']}_ANNI", "position_cm": root["annihilation_position_cm"], "provenance": root["sim_path"]},
                ]
            )
        q = math.sqrt(0.5)
        directions = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (q, q, 0.0), (q, 0.0, q), (0.0, q, q)]
        b2b_lines: list[str] = []
        particle_id = 1
        event_index = 0
        for position in positions:
            for direction in directions:
                time_s = event_index * 1e-9
                b2b_lines.append(event_row(particle_id, 0, time_s, position["position_cm"], direction, 511.0))
                b2b_lines.append(event_row(particle_id + 1, 1, time_s, position["position_cm"], (-direction[0], -direction[1], -direction[2]), 511.0))
                particle_id += 2
                event_index += 1
        write_text(b2b_path, "\n".join(b2b_lines) + "\n")
        tape_specs["back_to_back511_successor"] = {
            "kind": "back_to_back511_successor",
            "relative_path": f"eventlists/{b2b_path.name}",
            "rows": len(b2b_lines),
            "root_events": event_index,
            "successor_rows": event_index,
            "expected_init_per_event": 2,
            "positions": positions,
            "directions": [list(vector) for vector in directions],
            "diagnostic_only": True,
        }

        geometry_paths = {
            "A_baseline": (ROOT / geometry_validation["baseline"]["geometry_setup"]["path"]).absolute(),
            "B_lg1": (ROOT / geometry_validation["candidate"]["geometry_setup"]["path"]).absolute(),
        }
        cell_defs = [("focused_first1000", "focused_first1000", planned["focused_first1000"])]
        for root in roots:
            stem = "gamma_root_4148keV" if root["event_id"] == 3883 else "gamma_root_5769keV"
            for replica in range(1, 4):
                cell = f"{stem}_rep{replica:02d}"
                cell_defs.append((cell, root["key"], planned[cell]))
        cell_defs.append(("back_to_back511_successor", "back_to_back511_successor", planned["back_to_back511_successor"]))

        jobs: list[dict[str, Any]] = []
        for cell_id, tape_key, seed in cell_defs:
            spec = tape_specs[tape_key]
            final_tape = SMOKE_INPUTS / spec["relative_path"]
            for geometry_key in ("A_baseline", "B_lg1"):
                suffix = "A" if geometry_key == "A_baseline" else "B"
                job_id = f"{cell_id}__{suffix}"
                source_relative = Path("sources") / suffix / f"{job_id}.source"
                source_stage = stage_inputs / source_relative
                partial_dir = RUN_ROOT / job_id / ".attempt01.partial"
                output_prefix = partial_dir / job_id
                job = {
                    "job_id": job_id,
                    "cell_id": cell_id,
                    "geometry_key": geometry_key,
                    "seed": seed,
                    "n_events": spec["root_events"],
                    "expected_init_per_event": spec["expected_init_per_event"],
                    "eventlist": str(final_tape),
                    "source": str(SMOKE_INPUTS / source_relative),
                    "partial_attempt_dir": str(partial_dir),
                    "final_attempt_dir": str(RUN_ROOT / job_id / "attempt01"),
                    "output_prefix_partial": str(output_prefix),
                    "require_guard_cc_hit": geometry_key == "B_lg1" and tape_key == "back_to_back511_successor",
                }
                write_text(source_stage, source_text(job, geometry_paths[geometry_key], final_tape, output_prefix))
                job["source_sha256"] = sha256_file(source_stage)
                jobs.append(job)

        input_files: list[dict[str, Any]] = []
        for path in sorted(stage_inputs.rglob("*")):
            if path.is_file():
                relative = path.relative_to(stage_inputs)
                input_files.append(
                    {
                        "path": str(SMOKE_INPUTS / relative),
                        "sha256": sha256_file(path),
                        "size_bytes": path.stat().st_size,
                    }
                )
        for key, spec in tape_specs.items():
            stage_path = stage_inputs / spec["relative_path"]
            spec["path"] = str(SMOKE_INPUTS / spec["relative_path"])
            spec["sha256"] = sha256_file(stage_path)

        plan = {
            "schema_version": 1,
            "status": "READY_FOR_EXPLICIT_LAUNCH_NO_TRANSPORT_RUN",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "confirmation_token": CONFIRMATION,
            "claim_boundary": "First-pass geometry/load and event-record smoke only; no physical rate, activation, delayed, response, sensitivity, or geometry-promotion conclusion.",
            "geometry_validation": {
                "path": str(VALIDATION),
                "sha256": sha256_file(VALIDATION),
                "status": geometry_validation["status"],
            },
            "geometries": {
                "A_baseline": {
                    "setup": str(geometry_paths["A_baseline"]),
                    "setup_sha256": geometry_validation["baseline"]["geometry_setup"]["sha256"],
                    "guard_volumes": [],
                },
                "B_lg1": {
                    "setup": str(geometry_paths["B_lg1"]),
                    "setup_sha256": geometry_validation["candidate"]["geometry_setup"]["sha256"],
                    "guard_volumes": list(GUARD_VOLUMES),
                },
            },
            "cosima": {"path": str(COSIMA), "sha256": sha256_file(COSIMA)},
            "run_root": str(RUN_ROOT),
            "limits": {
                "minimum_free_bytes": 20 * 1024**3,
                "aggregate_output_max_bytes": 5_000_000_000,
                "single_sim_max_bytes": 1024**3,
                "per_job_timeout_seconds": 15 * 60,
                "execution": "serial",
                "worst_case_wall_seconds": len(jobs) * 15 * 60,
            },
            "seed_registry": {
                **registry,
                "selection_start": 2_120_000_003,
                "selection_stride": 7919,
                "planned_by_cell": planned,
                "pairing_rule": "A/B in one cell share a seed; different cells have distinct seeds",
            },
            "tapes": tape_specs,
            "jobs": jobs,
            "input_files": input_files,
            "totals": {
                "jobs": len(jobs),
                "paired_cells": len(cell_defs),
                "transport_events_if_launched": sum(job["n_events"] for job in jobs),
                "directional_gamma_jobs": 12,
                "focused_jobs": 2,
                "successor_guard_jobs": 2,
            },
            "dynamic_pass_contract": {
                "all_jobs": "zero exit, gzip readable through EOF, one EN/TE/TS trailer, exact geometry and seed headers, sequential paired ID fields, exact NEvents and IA INIT multiplicity",
                "baseline_guard": "zero CC HIT rows under the two LG1 guard UIDs",
                "candidate_guard": "record exact per-UID CC HIT counts; the successor diagnostic requires at least one LG1 guard CC HIT",
                "interpretation": "diagnostic record integrity only, never a background or signal rate estimate",
            },
        }
        stage_plan = stage / "smoke_plan.json"
        write_text(stage_plan, json.dumps(plan, indent=2, sort_keys=True) + "\n")
        os.replace(stage_inputs, SMOKE_INPUTS)
        os.replace(stage_plan, PLAN)

    print(json.dumps({"status": plan["status"], "plan": str(PLAN), "jobs": len(jobs), "seeds": planned}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
