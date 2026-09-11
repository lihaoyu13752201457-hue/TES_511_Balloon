#!/usr/bin/env python3
"""Extract compact IA/CC routes for accepted SG3B final-W2 events.

The response implementation is imported from package 58 so keyed energy noise,
active-veto thresholds, and Step05 topology decisions remain byte-for-byte the
same algorithm.  Only jobs proven by package 58 to contain a combined-veto
broad-window topology candidate are opened.  No SIM is hashed and no transport
is started.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
OUTPUT = PACKAGE / "outputs/01_selected_routes"
COMMON = ROOT / "engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817"
COMMON_CODE = COMMON / "code/analyze_sg3b_common_time.py"
COMMON_JOB_SCAN = COMMON / "outputs/01_common_time_response/input_job_semantic_scan.csv"
COMMON_CUTFLOW = COMMON / "outputs/01_common_time_response/sg3b_measured_cutflow.csv"

IA_RE = re.compile(r"^IA\s+(?P<proc>\S+)\s+(?P<body>.*)$")
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>[^\s]+)")
SQRT_HALF = math.sqrt(0.5)
CENTER_Z = -5.2


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def world_to_instrument(point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return SQRT_HALF * (x - z), y, SQRT_HALF * (x + z)


def projected(point: tuple[float, float, float]) -> dict[str, Any]:
    xp, yp, zp = world_to_instrument(point)
    zc = zp - CENTER_Z
    return {
        "world_cm": list(point),
        "xprime_cm": xp,
        "yprime_cm": yp,
        "zprime_cm": zp,
        "z_centered_cm": zc,
        "radius_cm": math.hypot(yp, zc),
        "sg3b_key_region": key_region(xp, yp, zp),
    }


def key_region(xp: float, yp: float, zp: float) -> str:
    radius = math.hypot(yp, zp - CENTER_Z)
    in_bi_x = -3.8 <= xp <= 3.24 or 3.60 <= xp <= 4.0
    if in_bi_x and 3.5154 <= radius <= 3.995 and zp >= CENTER_Z:
        return "SG3B_PASSIVE_BI_UPPER_HALF_CYLINDER"
    if 3.245 <= xp <= 3.595 and (
        -8.0 <= zp <= -6.0 or -4.4 <= zp <= -2.4
    ):
        return "SG3B_L0_CU_HEATSINK_RING"
    if -3.85 <= xp <= 4.10 and 4.0 <= radius <= 4.2:
        return "RETAINED_2MM_AL_NEARFIELD_CYLINDER"
    if -3.0 <= xp <= 3.5 and -7.6 <= zp <= -2.8:
        return "TES_NEARFIELD_ENVELOPE"
    return "OTHER"


def parse_number(value: str, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_ia(line: str) -> dict[str, Any] | None:
    match = IA_RE.match(line)
    if not match:
        return None
    fields = [part.strip() for part in match.group("body").split(";")]
    if len(fields) < 23:
        return None
    try:
        point = (float(fields[4]), float(fields[5]), float(fields[6]))
        result = {
            "process": match.group("proc").upper(),
            "ia_id": int(fields[0]),
            "parent_id": int(fields[1]),
            "detector_type": int(fields[2]),
            "time_s": float(fields[3]),
            "incoming_particle_code": int(fields[7]),
            "incoming_energy_keV": parse_number(fields[14]),
            "secondary_particle_code": int(fields[15]),
            "secondary_energy_keV": parse_number(fields[22]),
        }
    except (TypeError, ValueError):
        return None
    result.update(projected(point))
    return result


def parse_cc_detail(line: str) -> dict[str, Any] | None:
    if not line.startswith("CC HIT "):
        return None
    parts = line.split(maxsplit=3)
    if len(parts) < 4:
        return None
    values = {item.group("key"): item.group("value") for item in FIELD_RE.finditer(line)}
    try:
        point = (float(values["x"]), float(values["y"]), float(values["z"]))
        edep = float(values["edep_keV"])
    except (KeyError, ValueError):
        return None
    result = {
        "volume": parts[2],
        "edep_keV": edep,
        "time_s": parse_number(values.get("t", "")),
        "secondary": values.get("sec", ""),
        "track_id": values.get("tid", ""),
        "parent_track_id": values.get("pid", ""),
        "secondary_process": values.get("sproc", ""),
        "primary": values.get("prim", ""),
        "parent": values.get("par", ""),
        "creator_process": values.get("cproc", ""),
        "primary_id": values.get("primid", ""),
    }
    result.update(projected(point))
    return result


def grouped_hit_rows(groups: dict[tuple[str, ...], dict[str, float]]) -> list[dict[str, Any]]:
    rows = []
    for key, value in groups.items():
        volume, secondary, track_id, parent_track_id, sproc, primary, parent, cproc = key
        energy = value["e"]
        point = (
            value["wx"] / energy,
            value["wy"] / energy,
            value["wz"] / energy,
        )
        row = {
            "volume": volume,
            "secondary": secondary,
            "track_id": track_id,
            "parent_track_id": parent_track_id,
            "secondary_process": sproc,
            "primary": primary,
            "parent": parent,
            "creator_process": cproc,
            "edep_keV": energy,
            "first_time_s": value["first_time_s"],
        }
        row.update(projected(point))
        rows.append(row)
    return sorted(rows, key=lambda row: (row["first_time_s"], row["volume"], row["track_id"]))


def candidate_jobs(common: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = json.loads((COMMON / "analysis_inputs.json").read_text(encoding="utf-8"))
    jobs, receipt_audit = common.prepare_jobs(config)
    semantic = {
        (row["stream"], row["family"], row["batch_id"], row["job_id"]): row
        for row in read_csv(COMMON_JOB_SCAN)
    }
    chosen = []
    rejected = []
    for job in jobs:
        key = (job["stream"], job["family"], job["batch_id"], job["job_id"])
        row = semantic[key]
        has_candidate = row["topology_classes_json"] != "{}"
        if has_candidate:
            chosen.append(job)
        else:
            rejected.append(job["job_id"])
    return chosen, {
        "receipt_audit": receipt_audit,
        "possible_jobs_opened": len(chosen),
        "jobs_excluded_by_existing_broad_topology_empty_sieve": len(rejected),
        "excluded_job_ids": rejected,
        "sieve_authority": str(COMMON_JOB_SCAN),
    }


def scan_one(job: dict[str, Any], threshold_keV: float) -> dict[str, Any]:
    common = load_module(f"sg3b_common_worker_{job['scan_index']}", COMMON_CODE)
    parser, core, step05, disk = common.runtime()
    locator = common.position_locator(Path(job["positions_path"])) if job["stream"] == "delayed" else None
    plastic_volumes = set(job["plastic_volumes"])
    bgo_volumes = set(job["bgo_volumes"])
    current_id: int | None = None
    current_init_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    pixels: dict[str, dict[str, float | int]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0
    ia_lines: list[str] = []
    hit_groups: dict[tuple[str, ...], dict[str, float]] = {}
    selected: list[dict[str, Any]] = []
    generated = 0
    header_geometry = ""
    header_seed: int | None = None
    max_match = 0.0

    def flush() -> None:
        nonlocal current_id, current_init_za, production_xyz, init_count, pixels
        nonlocal plastic_keV, bgo_keV, ia_lines, hit_groups, max_match
        if current_id is None:
            return
        source: dict[str, Any] | None = None
        if job["stream"] == "delayed":
            if init_count != 1 or production_xyz is None or locator is None:
                raise RuntimeError(f"{job['job_id']}:{current_id} delayed INIT closure failed")
            metadata, distance = common.locate_source(locator, production_xyz)
            max_match = max(max_match, distance)
            source = {
                "source_volume": metadata[0],
                "source_parent_ZA": int(metadata[1]),
                "source_excitation_keV": float(metadata[2]),
                "transport_init_ZA": current_init_za,
                "transport_init_ZA_matches_source_parent": int(metadata[1]) == current_init_za,
                "position_match_distance_cm": distance,
                **projected(production_xyz),
            }
        if pixels:
            raw_hits: list[Any] = []
            measured_hits: list[Any] = []
            for uid, record in pixels.items():
                energy = float(record["e"])
                if energy <= 0.0:
                    continue
                common_hit = {
                    "x": float(record["wx"]) / energy,
                    "y": float(record["wy"]) / energy,
                    "z": float(record["wz"]) / energy,
                    "pixel_uid": uid,
                    "layer": int(record["layer"]),
                }
                raw_hits.append(SimpleNamespace(e=energy, **common_hit))
                measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
                    "sg3b", job["mode"], job["family"], job["batch_id"],
                    int(job["seed"]), job["job_id"], int(current_id), uid,
                )
                if measured >= core.PIXEL_THRESHOLD_KEV:
                    measured_hits.append(SimpleNamespace(e=measured, **common_hit))
            measured_total = math.fsum(hit.e for hit in measured_hits)
            raw_total = math.fsum(hit.e for hit in raw_hits)
            combined_pass = plastic_keV < threshold_keV and bgo_keV < threshold_keV
            topology_pass = False
            topology_class = "not_evaluated"
            if combined_pass and common.in_window(measured_total, common.WINDOWS["broad_480_550"]):
                topology_pass, topology_class = common.topology_keep(measured_hits, step05, disk)
            if (
                combined_pass
                and topology_pass
                and common.in_window(measured_total, common.WINDOWS["w2_510p58_511p42"])
            ):
                interactions = [value for line in ia_lines if (value := parse_ia(line)) is not None]
                hits = grouped_hit_rows(hit_groups)
                tes_hits = [row for row in hits if parser.TP_RE.match(str(row["volume"]))]
                tes_edep = math.fsum(float(row["edep_keV"]) for row in tes_hits)
                tes_point = tuple(
                    math.fsum(float(row["edep_keV"]) * float(row["world_cm"][axis]) for row in tes_hits) / tes_edep
                    for axis in range(3)
                )
                selected.append({
                    "stream": job["stream"],
                    "family": job["family"],
                    "batch_id": job["batch_id"],
                    "job_id": job["job_id"],
                    "source_file": job["sim_path"],
                    "local_event_id": current_id,
                    "transport_seed": int(job["seed"]),
                    "event_weight_cps_day15_or_reference": float(job["weight_cps"]),
                    "raw_total_keV": raw_total,
                    "measured_total_keV": measured_total,
                    "plastic_keV": plastic_keV,
                    "bgo_keV": bgo_keV,
                    "topology_class": topology_class,
                    "source": source,
                    "interactions": interactions,
                    "hit_groups": hits,
                    "tes": {
                        "raw_edep_keV": tes_edep,
                        "pixels": sorted({row["volume"] for row in tes_hits}),
                        **projected(tes_point),
                    },
                })
        current_id = None
        current_init_za = None
        production_xyz = None
        init_count = 0
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0
        ia_lines = []
        hit_groups = {}

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
                    raise RuntimeError(f"{job['job_id']}: ID before SE")
                current_id = int(match.group(1))
                generated += 1
                continue
            if line.startswith("IA "):
                ia_lines.append(line)
                if line.startswith("IA INIT") and job["stream"] == "delayed":
                    fields = [value.strip() for value in line.split(";")]
                    init_count += 1
                    current_init_za = int(fields[15])
                    production_xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parser.parse_cc_hit(line)
            detail = parse_cc_detail(line)
            if hit is None or detail is None:
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
            key = tuple(str(detail[field]) for field in (
                "volume", "secondary", "track_id", "parent_track_id",
                "secondary_process", "primary", "parent", "creator_process",
            ))
            group = hit_groups.setdefault(
                key, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "first_time_s": math.inf}
            )
            group["e"] += edep
            group["wx"] += edep * x
            group["wy"] += edep * y
            group["wz"] += edep * z
            group["first_time_s"] = min(group["first_time_s"], float(detail["time_s"]))
    flush()
    if generated != int(job["events"]):
        raise RuntimeError(f"{job['job_id']}: generated {generated} != {job['events']}")
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve():
        raise RuntimeError(f"{job['job_id']}: geometry mismatch")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: seed mismatch")
    return {
        "scan_index": int(job["scan_index"]),
        "job_id": job["job_id"],
        "stream": job["stream"],
        "family": job["family"],
        "events_scanned": generated,
        "sim_bytes": int(job["sim_bytes"]),
        "selected_events": selected,
        "max_position_match_distance_cm": max_match,
    }


def expected_counts() -> dict[tuple[str, str], int]:
    rows = read_csv(COMMON_CUTFLOW)
    return {
        (row["stream"], row["family"]): int(row["selected_events"])
        for row in rows
        if row["stage"] == "compton_trajectory_veto"
        and row["window_id"] == "w2_510p58_511p42"
    }


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--workers", type=int, default=6)
    args.add_argument("--output", type=Path, default=OUTPUT)
    ns = args.parse_args()
    ns.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    common = load_module("sg3b_common_parent", COMMON_CODE)
    jobs, sieve = candidate_jobs(common)
    threshold = float(config["response"]["active_threshold_keV"])
    results: dict[int, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=min(ns.workers, len(jobs))) as pool:
        futures = {pool.submit(scan_one, job, threshold): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            result = future.result()
            results[int(job["scan_index"])] = result
            print(json.dumps({
                "job_id": result["job_id"],
                "events_scanned": result["events_scanned"],
                "selected": len(result["selected_events"]),
            }), flush=True)
    scans = [results[index] for index in sorted(results)]
    events = [event for scan in scans for event in scan["selected_events"]]
    events.sort(key=lambda row: (row["stream"], row["family"], row["job_id"], row["local_event_id"]))
    found = Counter((row["stream"], row["family"]) for row in events)
    expected = expected_counts()
    mismatches = {
        f"{stream}|{family}": {"expected": count, "found": found[(stream, family)]}
        for (stream, family), count in expected.items()
        if count != found[(stream, family)]
    }
    if mismatches:
        raise RuntimeError(f"final-W2 count mismatch: {mismatches}")
    payload = {
        "status": "PASS__SG3B_ACCEPTED_FINAL_W2_COMPACT_ROUTES",
        "authority_boundary": "DIAGNOSTIC_EVENT_LINEAGE__RATE_AUTHORITY_REMAINS_PACKAGE58",
        "candidate": "SG3B",
        "selection": {
            "measured_window_keV": config["response"]["window_keV"],
            "active_threshold_keV": threshold,
            "stage": config["response"]["stage"],
            "response_code": str(COMMON_CODE),
        },
        "sim_access": {
            "accepted_possible_jobs_opened": len(scans),
            "events_scanned": sum(row["events_scanned"] for row in scans),
            "bytes_opened_without_hashing": sum(row["sim_bytes"] for row in scans),
            "large_SIM_hashes_computed": 0,
            "transport_started": False,
            "superseded_delayed_v1_transport_opened": False,
            "parma_mono511_opened_or_added": False,
            "scans": [{key: row[key] for key in row if key != "selected_events"} for row in scans],
        },
        "sieve": sieve,
        "count_validation": {
            "status": "PASS",
            "expected_by_stream_family": {f"{a}|{b}": value for (a, b), value in sorted(expected.items())},
            "found_by_stream_family": {f"{a}|{b}": value for (a, b), value in sorted(found.items())},
            "total_selected_events": len(events),
        },
        "coordinate_contract": {
            "frame": "InstrumentFrame",
            "world_to_instrument": "x'=(x-z)/sqrt(2), y'=y, z'=(x+z)/sqrt(2)",
            "axial_radius": "sqrt(y'^2 + (z'+5.2 cm)^2)",
        },
        "source_parent_note": (
            "source_parent_ZA comes from the audited exact-position mixture. "
            "transport_init_ZA is retained separately and may be daughter-shifted by one Z."
        ),
        "events": events,
    }
    output = ns.output / "sg3b_selected_w2_routes.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "events": len(events), "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
