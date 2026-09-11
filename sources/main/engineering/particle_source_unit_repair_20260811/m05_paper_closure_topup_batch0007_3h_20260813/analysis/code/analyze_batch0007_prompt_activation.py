#!/usr/bin/env python3
"""Read-only M05 prompt/activation analysis for corrected-keV batch0007.

``--check`` performs only static and terminal-authority checks.  It never opens
SIM/DAT artifacts and is therefore safe while transport is active.  ``--run``
requires the immutable batch0007 PASS terminal trio, reads only its selected
receipts/artifacts, and publishes a write-once analysis package through
``.partial`` members followed by atomic ``os.replace``.

This is a supplemental-screening reader.  It does not merge historical rates,
run delayed transport, establish mission sensitivity, or promote a geometry.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


sys.dont_write_bytecode = True

ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1"
PACKAGE_ROOT = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_20260813"
)
AUTHORITY = RUN_ROOT / "authority.json"
FINAL_VALIDATION = RUN_ROOT / "final_validation.json"
FINAL_LEDGER = RUN_ROOT / "final_ledger.json"
FINAL_UMBRELLA = RUN_ROOT / "final_umbrella.json"
OUTPUT = RUN_ROOT / "analysis_prompt_activation"

PASS_STATUS = "PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("eminus", "muminus")
MODES = ("buildup", "instant")
EXPECTED_JOBS = 24
EXPECTED_EVENTS = 1_008_000
EXPECTED_CELLS = {
    (geometry, mode, family)
    for geometry in GEOMETRIES
    for mode, family in (("buildup", "eminus"), ("buildup", "muminus"), ("instant", "eminus"))
}

TES_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
M05_RESPONSE_SEED = 26071301
M05_RESPONSE_FWHM_KEV = 0.420
M05_RESPONSE_SIGMA_KEV = M05_RESPONSE_FWHM_KEV / 2.354820045
MEASURED_PIXEL_THRESHOLD_KEV = 0.3
BROAD = (480.0, 550.0)
W2 = (510.58, 511.42)
VETO_THRESHOLDS_KEV = (50.0, 70.0, 80.0)
ZERO_COUNT_95_UPPER_MEAN = 2.995732273553991

MASS_ACTIVE = frozenset(
    {
        "CsI_Side_Segment_00",
        "CsI_Side_Segment_01",
        "CsI_Side_Segment_02",
        "CsI_Side_Segment_03_below_side_port",
        "CsI_Side_Segment_03_above_side_port",
        "CsI_Side_Segment_03_rectcut_window_band",
        "CsI_Side_Segment_04_below_side_port",
        "CsI_Side_Segment_04_above_side_port",
        "CsI_Side_Segment_04_rectcut_window_band",
        "CsI_Side_Segment_05",
        "CsI_Side_Segment_06",
        "CsI_Side_Segment_07",
        *(f"CsI_Bottom_Quadrant_{index:02d}" for index in range(4)),
        *(f"CsI_TopAnnulus_Segment_{index:02d}" for index in range(8)),
    }
)
O8_ACTIVE = frozenset(
    {
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    }
)
REQUIRED_HIT_KV = frozenset(
    {"edep_keV", "x", "y", "z", "t", "sec", "tid", "pid", "sproc", "prim", "par", "cproc", "primid"}
)
REQUIRED_RP_ANCESTRY = frozenset({"tid", "pid", "sproc", "prim", "par", "cproc"})


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if path.name.endswith(".partial"):
        raise RuntimeError(f"refusing partial input: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_payload(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def csv_payload(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def parse_kv(tokens: list[str]) -> dict[str, str]:
    return {key: value for token in tokens if "=" in token for key, value in [token.split("=", 1)]}


def active_blocks(geometry: str) -> frozenset[str]:
    if geometry == "Mass_model_511":
        return MASS_ACTIVE
    if geometry == "S3d_O8":
        return O8_ACTIVE
    raise RuntimeError(f"unknown geometry: {geometry}")


def assert_close(actual: float, expected: float, label: str, tolerance: float = 1e-8) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise RuntimeError(f"{label}: {actual!r} != {expected!r}")


def output_collision_check() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"write-once output already exists: {OUTPUT}")
    partial_dir = OUTPUT.with_name(OUTPUT.name + ".partial")
    if partial_dir.exists():
        raise RuntimeError(f"stale write-once partial directory exists: {partial_dir}")


def terminal_files_present() -> bool:
    return all(path.is_file() for path in (FINAL_VALIDATION, FINAL_LEDGER, FINAL_UMBRELLA))


def selected_receipts() -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    """Resolve only immutable terminal-selected receipts; no artifact is opened."""
    if not terminal_files_present():
        raise RuntimeError("batch0007 terminal authority trio is not yet complete")
    authority = load_json(AUTHORITY)
    validation = load_json(FINAL_VALIDATION)
    ledger = load_json(FINAL_LEDGER)
    umbrella = load_json(FINAL_UMBRELLA)
    for label, value in (("validation", validation), ("ledger", ledger), ("umbrella", umbrella)):
        if value.get("status") != PASS_STATUS:
            raise RuntimeError(f"{label} is not terminal PASS: {value.get('status')}")
    if ledger.get("validation") != rel(FINAL_VALIDATION):
        raise RuntimeError("ledger/validation binding mismatch")
    if umbrella.get("authority") != rel(AUTHORITY):
        raise RuntimeError("umbrella/authority binding mismatch")
    if umbrella.get("final_validation") != rel(FINAL_VALIDATION) or umbrella.get("final_ledger") != rel(FINAL_LEDGER):
        raise RuntimeError("umbrella terminal-path binding mismatch")

    plan = authority.get("plan")
    if not isinstance(plan, list) or len(plan) != EXPECTED_JOBS:
        raise RuntimeError("authority plan is missing or has unexpected length")
    expected_by_id = {str(job["job_id"]): job for job in plan}
    if len(expected_by_id) != EXPECTED_JOBS:
        raise RuntimeError("authority plan has duplicate job IDs")
    if sum(int(job["events"]) for job in plan) != EXPECTED_EVENTS:
        raise RuntimeError("authority plan event total drift")
    observed_cells = {(str(job["geometry"]), str(job["mode"]), str(job["family"])) for job in plan}
    if observed_cells != EXPECTED_CELLS:
        raise RuntimeError(f"authority cell drift: {sorted(observed_cells)}")

    selected = ledger.get("selected_receipts")
    validation_selected = validation.get("selected_receipts")
    if not isinstance(selected, list) or not isinstance(validation_selected, list):
        raise RuntimeError("terminal selected receipt lists are missing")
    ledger_map = {str(row["job_id"]): row for row in selected}
    validation_map = {str(row["job_id"]): row for row in validation_selected}
    if set(ledger_map) != set(expected_by_id) or ledger_map != validation_map:
        raise RuntimeError("terminal selected receipts do not exactly match the frozen plan")
    if int(validation.get("validated_jobs", -1)) != EXPECTED_JOBS:
        raise RuntimeError("terminal validated job count drift")
    if int(validation.get("validated_events", -1)) != EXPECTED_EVENTS:
        raise RuntimeError("terminal validated event count drift")

    receipts: list[dict[str, Any]] = []
    receipt_root = (RUN_ROOT / "job_receipts").resolve()
    for job_id, expected_job in expected_by_id.items():
        row = ledger_map[job_id]
        receipt_path = (ROOT / str(row["path"])).resolve()
        if receipt_path.name.endswith(".partial") or receipt_root not in receipt_path.parents:
            raise RuntimeError(f"noncanonical selected receipt path: {receipt_path}")
        receipt = load_json(receipt_path)
        if receipt.get("status") != "PASS" or int(receipt.get("returncode", -1)) != 0 or receipt.get("errors"):
            raise RuntimeError(f"selected receipt is not PASS: {job_id}")
        if receipt.get("job") != expected_job:
            raise RuntimeError(f"selected receipt/frozen job drift: {job_id}")
        if int(row["events"]) != int(expected_job["events"]):
            raise RuntimeError(f"selected receipt event declaration drift: {job_id}")
        if int(row["selected_attempt"]) != int(receipt["selected_attempt"]):
            raise RuntimeError(f"selected attempt drift: {job_id}")
        if row.get("declared_artifacts") != receipt.get("artifacts"):
            raise RuntimeError(f"selected artifact declaration drift: {job_id}")
        receipt["_path"] = receipt_path
        receipts.append(receipt)

    receipts.sort(
        key=lambda receipt: (
            GEOMETRIES.index(str(receipt["job"]["geometry"])),
            MODES.index(str(receipt["job"]["mode"])),
            FAMILIES.index(str(receipt["job"]["family"])),
            int(receipt["job"]["shard_ordinal"]),
        )
    )
    hashes = {
        "authority": sha256_file(AUTHORITY),
        "final_validation": sha256_file(FINAL_VALIDATION),
        "final_ledger": sha256_file(FINAL_LEDGER),
        "final_umbrella": sha256_file(FINAL_UMBRELLA),
    }
    terminal = {
        "status": PASS_STATUS,
        "validated_jobs": EXPECTED_JOBS,
        "validated_events": EXPECTED_EVENTS,
        "old_artifact_hashes_recomputed_at_terminal": bool(validation.get("old_artifact_hashes_recomputed", False)),
    }
    return receipts, hashes, terminal


def parse_dat(path: Path) -> dict[str, Any]:
    tt_values: list[float] = []
    current_volume: str | None = None
    rp_count = 0
    rp_sum = 0.0
    end_count = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT" and len(fields) == 2:
            tt_values.append(float(fields[1]))
        elif fields[0] == "VN":
            current_volume = line[2:].strip()
        elif fields[0] == "RP" and len(fields) == 4 and current_volume:
            isotope, excitation, quantity = int(fields[1]), float(fields[2]), float(fields[3])
            if isotope <= 0 or excitation < 0 or quantity < 0:
                raise RuntimeError(f"invalid DAT RP at {rel(path)}:{line_number}")
            rp_count += 1
            rp_sum = math.fsum((rp_sum, quantity))
        elif fields == ["EN"]:
            end_count += 1
        else:
            raise RuntimeError(f"unrecognized DAT record at {rel(path)}:{line_number}: {line}")
    if len(tt_values) != 1 or tt_values[0] <= 0 or not math.isfinite(tt_values[0]) or end_count != 1:
        raise RuntimeError(f"DAT framing failure: {rel(path)}")
    return {"TT_s": tt_values[0], "RP_record_count": rp_count, "RP_sum": rp_sum}


def artifact_path(receipt: dict[str, Any], kind: str) -> Path:
    path = (ROOT / str(receipt["attempt_dir"]) / str(receipt["artifacts"][kind]["name"])).resolve()
    attempt = (ROOT / str(receipt["attempt_dir"])).resolve()
    if path.name.endswith(".partial") or attempt not in path.parents or not path.is_file():
        raise RuntimeError(f"missing/noncanonical {kind} artifact for {receipt['job']['job_id']}: {path}")
    return path


def scan(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_events: dict[str, list[dict[str, Any]]] = {geometry: [] for geometry in GEOMETRIES}
    prompt_meta = {geometry: Counter() for geometry in GEOMETRIES}
    active_observed = {geometry: set() for geometry in GEOMETRIES}
    o8_nonwhitelist_suspects: Counter[str] = Counter()

    rp_tuples: dict[tuple[str, str, str, int, float], dict[str, Any]] = {}
    rp_structures: dict[tuple[str, str, str], dict[str, Any]] = {}
    buildup_family: dict[tuple[str, str], dict[str, Any]] = {}
    sim_rp_by_job: Counter[str] = Counter()

    cell_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    total_events = 0
    total_prompt_hits = 0
    total_tes_steps = 0
    typed_hit_missing = 0
    rp_ancestry_missing = 0
    rp_position_invalid = 0
    gzip_eof_files = 0

    for receipt in receipts:
        job = receipt["job"]
        geometry, mode, family = str(job["geometry"]), str(job["mode"]), str(job["family"])
        sim_path = artifact_path(receipt, "sim")
        dat_path = artifact_path(receipt, "dat")
        dat = parse_dat(dat_path)
        assert_close(dat["TT_s"], float(receipt["isotope_dat"]["TT_s"]), f"DAT/receipt TT {job['job_id']}")
        if dat["RP_record_count"] != int(receipt["isotope_dat"]["RP_record_count"]):
            raise RuntimeError(f"DAT/receipt RP row mismatch: {job['job_id']}")
        assert_close(dat["RP_sum"], float(receipt["isotope_dat"]["RP_sum"]), f"DAT/receipt RP sum {job['job_id']}")

        cell_key = (geometry, mode, family)
        cell = cell_rows.setdefault(
            cell_key,
            {
                "geometry": geometry,
                "mode": mode,
                "family": family,
                "jobs": 0,
                "events": 0,
                "TT_s": 0.0,
                "RP_record_count": 0,
                "RP_sum": 0.0,
                "artifact_bytes": 0,
                "wall_sum_s": 0.0,
                "max_process_group_RSS_bytes": 0,
                "zero_RP_jobs": 0,
            },
        )
        cell["jobs"] += 1
        cell["events"] += int(job["events"])
        cell["TT_s"] = math.fsum((float(cell["TT_s"]), dat["TT_s"]))
        cell["RP_record_count"] += dat["RP_record_count"]
        cell["RP_sum"] = math.fsum((float(cell["RP_sum"]), dat["RP_sum"]))
        cell["artifact_bytes"] += sum(int(value["bytes"]) for value in receipt["artifacts"].values())
        cell["wall_sum_s"] = math.fsum((float(cell["wall_sum_s"]), float(receipt["wall_s"])))
        cell["max_process_group_RSS_bytes"] = max(
            int(cell["max_process_group_RSS_bytes"]), int(receipt["peak_process_group_rss_bytes"])
        )
        cell["zero_RP_jobs"] += int(dat["RP_sum"] == 0.0)

        current_id: int | None = None
        pixels: defaultdict[str, float] = defaultdict(float)
        active: Counter[str] = Counter()
        file_events = 0
        se_count = 0
        en_count = 0
        next_id = 1
        header_geometry: str | None = None
        header_seed: int | None = None

        def flush_event() -> None:
            nonlocal current_id, pixels, active, file_events
            if current_id is None:
                return
            if mode == "instant":
                prompt_meta[geometry]["events"] += 1
                if pixels:
                    rows = [(name, float(pixels[name])) for name in sorted(pixels)]
                    prompt_events[geometry].append(
                        {"job_id": job["job_id"], "event_id": current_id, "pixels": rows, "active_total_keV": math.fsum(active.values())}
                    )
                    prompt_meta[geometry]["tes_positive_events"] += 1
                    prompt_meta[geometry]["pixel_readouts"] += len(rows)
                    prompt_meta[geometry]["max_raw_pixel_multiplicity"] = max(
                        int(prompt_meta[geometry]["max_raw_pixel_multiplicity"]), len(rows)
                    )
            file_events += 1
            current_id = None
            pixels = defaultdict(float)
            active = Counter()

        with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
            for raw in handle:
                line = raw.strip()
                if header_geometry is None and line.startswith("Geometry "):
                    header_geometry = line.split(maxsplit=1)[1]
                if header_seed is None and line.startswith("Seed "):
                    header_seed = int(line.split()[1])
                if line == "SE":
                    flush_event()
                    se_count += 1
                    continue
                if line == "EN":
                    en_count += 1
                    continue
                if line.startswith("ID "):
                    fields = line.split()
                    if len(fields) != 3 or int(fields[1]) != int(fields[2]) or int(fields[1]) != next_id:
                        raise RuntimeError(f"SIM event identity failure in {job['job_id']}: {line}")
                    current_id = int(fields[1])
                    next_id += 1
                    continue
                if mode == "instant" and line.startswith("CC HIT "):
                    total_prompt_hits += 1
                    fields = line.split()
                    if len(fields) < 4:
                        raise RuntimeError(f"malformed CC HIT in {job['job_id']}")
                    volume = fields[2]
                    kv = parse_kv(fields[3:])
                    missing = not REQUIRED_HIT_KV.issubset(kv)
                    typed_hit_missing += int(missing)
                    if missing:
                        continue
                    edep = float(kv["edep_keV"])
                    numeric = (edep, *(float(kv[key]) for key in ("x", "y", "z", "t")))
                    if edep < 0 or not all(math.isfinite(value) for value in numeric):
                        raise RuntimeError(f"invalid typed CC HIT in {job['job_id']}")
                    if TES_RE.fullmatch(volume):
                        pixels[volume] += edep
                        total_tes_steps += 1
                    elif volume in active_blocks(geometry):
                        active[volume] += edep
                        active_observed[geometry].add(volume)
                    elif geometry == "S3d_O8" and ("BGO" in volume or "Plastic" in volume or "ActiveShield" in volume):
                        o8_nonwhitelist_suspects[volume] += 1
                    continue
                if mode == "buildup" and line.startswith("CC IP RP "):
                    fields = line.split()
                    if len(fields) < 11:
                        raise RuntimeError(f"malformed CC IP RP in {job['job_id']}")
                    volume = fields[3]
                    x, y, z = (float(fields[index]) for index in (4, 5, 6))
                    isotope, excitation, production_time_s = int(fields[7]), float(fields[8]), float(fields[9])
                    kv = parse_kv(fields[10:])
                    rp_ancestry_missing += int(not REQUIRED_RP_ANCESTRY.issubset(kv))
                    invalid_position = not all(math.isfinite(value) for value in (x, y, z, production_time_s))
                    rp_position_invalid += int(invalid_position)
                    if invalid_position or isotope <= 0 or excitation < 0:
                        raise RuntimeError(f"invalid CC IP RP in {job['job_id']}")
                    sim_rp_by_job[str(job["job_id"])] += 1
                    tuple_key = (geometry, family, volume, isotope, excitation)
                    row = rp_tuples.setdefault(
                        tuple_key,
                        {
                            "geometry": geometry,
                            "family": family,
                            "physical_volume": volume,
                            "isotope_id": isotope,
                            "excitation_keV": excitation,
                            "production_instances": 0,
                            "x_min_cm": x,
                            "x_max_cm": x,
                            "y_min_cm": y,
                            "y_max_cm": y,
                            "z_min_cm": z,
                            "z_max_cm": z,
                            "production_time_min_s": production_time_s,
                            "production_time_max_s": production_time_s,
                        },
                    )
                    row["production_instances"] += 1
                    for axis, value in (("x", x), ("y", y), ("z", z)):
                        row[f"{axis}_min_cm"] = min(float(row[f"{axis}_min_cm"]), value)
                        row[f"{axis}_max_cm"] = max(float(row[f"{axis}_max_cm"]), value)
                    row["production_time_min_s"] = min(float(row["production_time_min_s"]), production_time_s)
                    row["production_time_max_s"] = max(float(row["production_time_max_s"]), production_time_s)

                    structure_key = (geometry, family, volume)
                    structure = rp_structures.setdefault(
                        structure_key,
                        {
                            "geometry": geometry,
                            "family": family,
                            "physical_volume": volume,
                            "production_instances": 0,
                            "isotope_states": set(),
                            "x_min_cm": x,
                            "x_max_cm": x,
                            "y_min_cm": y,
                            "y_max_cm": y,
                            "z_min_cm": z,
                            "z_max_cm": z,
                        },
                    )
                    structure["production_instances"] += 1
                    structure["isotope_states"].add((isotope, excitation))
                    for axis, value in (("x", x), ("y", y), ("z", z)):
                        structure[f"{axis}_min_cm"] = min(float(structure[f"{axis}_min_cm"]), value)
                        structure[f"{axis}_max_cm"] = max(float(structure[f"{axis}_max_cm"]), value)
        flush_event()
        gzip_eof_files += 1
        expected_geometry = str(receipt["sim"]["geometry_header"])
        observed_geometry = str((ROOT / header_geometry).resolve()) if header_geometry and not Path(header_geometry).is_absolute() else str(Path(header_geometry).resolve()) if header_geometry else None
        if observed_geometry != str(Path(expected_geometry).resolve()) or header_seed != int(job["seed"]):
            raise RuntimeError(f"SIM Geometry/Seed mismatch: {job['job_id']}")
        if file_events != int(job["events"]) or se_count != int(job["events"]) or en_count != 1:
            raise RuntimeError(f"SIM framing mismatch: {job['job_id']}")
        total_events += file_events

        if mode == "buildup":
            assert_close(float(sim_rp_by_job[str(job["job_id"])]), dat["RP_sum"], f"SIM/DAT RP {job['job_id']}")
            key = (geometry, family)
            family_row = buildup_family.setdefault(
                key,
                {
                    "geometry": geometry,
                    "family": family,
                    "jobs": 0,
                    "events": 0,
                    "TT_s": 0.0,
                    "DAT_RP_record_count": 0,
                    "DAT_RP_sum": 0.0,
                    "SIM_RP_instances": 0,
                    "zero_RP_jobs": 0,
                },
            )
            family_row["jobs"] += 1
            family_row["events"] += int(job["events"])
            family_row["TT_s"] = math.fsum((float(family_row["TT_s"]), dat["TT_s"]))
            family_row["DAT_RP_record_count"] += dat["RP_record_count"]
            family_row["DAT_RP_sum"] = math.fsum((float(family_row["DAT_RP_sum"]), dat["RP_sum"]))
            family_row["SIM_RP_instances"] += sim_rp_by_job[str(job["job_id"])]
            family_row["zero_RP_jobs"] += int(dat["RP_sum"] == 0.0)

    if set(cell_rows) != EXPECTED_CELLS or any(int(row["jobs"]) != 4 for row in cell_rows.values()):
        raise RuntimeError(f"cell/job coverage mismatch: {cell_rows}")
    if total_events != EXPECTED_EVENTS or gzip_eof_files != EXPECTED_JOBS:
        raise RuntimeError(f"analysis event/EOF mismatch: {total_events}/{gzip_eof_files}")
    if typed_hit_missing or rp_ancestry_missing or rp_position_invalid:
        raise RuntimeError(
            f"typed rich-SIM field failure: hit={typed_hit_missing}, ancestry={rp_ancestry_missing}, position={rp_position_invalid}"
        )

    prompt_rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        rng = np.random.default_rng(M05_RESPONSE_SEED)
        counts = Counter()
        max_measured_multiplicity = 0
        for event in prompt_events[geometry]:
            raw_total = math.fsum(energy for _name, energy in event["pixels"])
            measured = [float(rng.normal(energy, M05_RESPONSE_SIGMA_KEV)) for _name, energy in event["pixels"]]
            accepted = [value for value in measured if value >= MEASURED_PIXEL_THRESHOLD_KEV]
            measured_total = math.fsum(accepted)
            measured_multiplicity = len(accepted)
            max_measured_multiplicity = max(max_measured_multiplicity, measured_multiplicity)
            counts["raw_broad"] += int(BROAD[0] <= raw_total < BROAD[1])
            counts["measured_broad"] += int(BROAD[0] <= measured_total < BROAD[1])
            counts["raw_W2"] += int(W2[0] <= raw_total < W2[1])
            measured_w2 = W2[0] <= measured_total < W2[1]
            counts["measured_W2"] += int(measured_w2)
            counts["measured_W2_single_pixel_proxy"] += int(measured_w2 and measured_multiplicity == 1)
            if measured_w2:
                for threshold in VETO_THRESHOLDS_KEV:
                    passed = float(event["active_total_keV"]) < threshold
                    counts[f"W2_pass_{int(threshold)}"] += int(passed)
                    counts[f"W2_single_pixel_proxy_pass_{int(threshold)}"] += int(passed and measured_multiplicity == 1)
        tt = float(cell_rows[(geometry, "instant", "eminus")]["TT_s"])
        row: dict[str, Any] = {
            "geometry": geometry,
            "family": "eminus",
            "events": int(cell_rows[(geometry, "instant", "eminus")]["events"]),
            "TT_s": tt,
            "tes_positive_events": int(prompt_meta[geometry]["tes_positive_events"]),
            "pixel_readouts": int(prompt_meta[geometry]["pixel_readouts"]),
            "max_raw_pixel_multiplicity": int(prompt_meta[geometry]["max_raw_pixel_multiplicity"]),
            "max_measured_pixel_multiplicity": max_measured_multiplicity,
        }
        names = (
            "raw_broad",
            "measured_broad",
            "raw_W2",
            "measured_W2",
            "measured_W2_single_pixel_proxy",
            "W2_pass_50",
            "W2_pass_70",
            "W2_pass_80",
            "W2_single_pixel_proxy_pass_50",
            "W2_single_pixel_proxy_pass_70",
            "W2_single_pixel_proxy_pass_80",
        )
        for name in names:
            count = int(counts[name])
            row[f"{name}_count"] = count
            row[f"{name}_rate_cps"] = count / tt
            row[f"{name}_poisson_RSE"] = None if count == 0 else 1.0 / math.sqrt(count)
            row[f"{name}_zero_count_95_upper_rate_cps"] = ZERO_COUNT_95_UPPER_MEAN / tt if count == 0 else None
        prompt_rows.append(row)

    buildup_rows: list[dict[str, Any]] = []
    for key in sorted(buildup_family, key=lambda item: (GEOMETRIES.index(item[0]), FAMILIES.index(item[1]))):
        row = buildup_family[key]
        tuples = [value for tuple_key, value in rp_tuples.items() if tuple_key[0] == key[0] and tuple_key[1] == key[1]]
        row["physical_volume_count"] = len({value["physical_volume"] for value in tuples})
        row["physical_volume_isotope_state_tuple_count"] = len(tuples)
        row["production_rate_per_TT_s"] = float(row["SIM_RP_instances"]) / float(row["TT_s"])
        row["zero_RP_cell"] = int(row["SIM_RP_instances"]) == 0
        row["zero_RP_TT_retained"] = True
        buildup_rows.append(row)

    tuple_rows: list[dict[str, Any]] = []
    for key in sorted(rp_tuples, key=lambda item: (GEOMETRIES.index(item[0]), FAMILIES.index(item[1]), item[2], item[3], item[4])):
        row = dict(rp_tuples[key])
        row["production_rate_per_TT_s"] = float(row["production_instances"]) / float(
            buildup_family[(row["geometry"], row["family"])]["TT_s"]
        )
        tuple_rows.append(row)

    structure_rows: list[dict[str, Any]] = []
    for key in sorted(rp_structures, key=lambda item: (GEOMETRIES.index(item[0]), FAMILIES.index(item[1]), item[2])):
        source = rp_structures[key]
        row = {name: value for name, value in source.items() if name != "isotope_states"}
        row["isotope_state_count"] = len(source["isotope_states"])
        row["production_rate_per_TT_s"] = float(row["production_instances"]) / float(
            buildup_family[(row["geometry"], row["family"])]["TT_s"]
        )
        structure_rows.append(row)

    buildup_geometry: dict[str, Any] = {}
    for geometry in GEOMETRIES:
        rows = [row for row in tuple_rows if row["geometry"] == geometry]
        buildup_geometry[geometry] = {
            "SIM_RP_instances": sum(int(row["production_instances"]) for row in rows),
            "unique_physical_volumes": len({str(row["physical_volume"]) for row in rows}),
            "unique_physical_volume_isotope_state_tuples": len(rows),
            "families": {
                family: {
                    "TT_s": float(buildup_family[(geometry, family)]["TT_s"]),
                    "SIM_RP_instances": int(buildup_family[(geometry, family)]["SIM_RP_instances"]),
                    "zero_RP_jobs": int(buildup_family[(geometry, family)]["zero_RP_jobs"]),
                }
                for family in FAMILIES
            },
        }

    return {
        "cell_rows": [cell_rows[key] for key in sorted(cell_rows)],
        "prompt_rows": prompt_rows,
        "buildup_rows": buildup_rows,
        "tuple_rows": tuple_rows,
        "structure_rows": structure_rows,
        "buildup_geometry": buildup_geometry,
        "active_observed": {geometry: sorted(active_observed[geometry]) for geometry in GEOMETRIES},
        "o8_nonwhitelist_suspects": dict(sorted(o8_nonwhitelist_suspects.items())),
        "raw_scan": {
            "receipts": len(receipts),
            "events": total_events,
            "gzip_EOF_files": gzip_eof_files,
            "prompt_events": sum(int(row["events"]) for row in prompt_rows),
            "prompt_CC_HIT": total_prompt_hits,
            "prompt_CC_HIT_typed_missing": typed_hit_missing,
            "prompt_TES_steps": total_tes_steps,
            "buildup_SIM_RP_instances": sum(int(row["SIM_RP_instances"]) for row in buildup_rows),
            "buildup_RP_ancestry_missing": rp_ancestry_missing,
            "buildup_RP_position_invalid": rp_position_invalid,
        },
    }


def report_markdown(summary: dict[str, Any]) -> str:
    prompt = {row["geometry"]: row for row in summary["prompt"]}
    buildup = summary["buildup"]
    lines = [
        "# Batch0007 supplemental M05 prompt/activation analysis",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This read-only analysis uses only terminal-PASS batch0007 receipts. It is supplemental corrected-keV screening, not a complete prompt+delayed response, mission sensitivity, final background ranking, or geometry promotion.",
        "",
        "## Prompt e− observable",
        "",
        "TES `CC HIT` deposits were summed by event and `TP_L<layer>_<pixel>`, smeared independently with the M05 0.420 keV FWHM response using seed 26071301, and measured pixels below 0.3 keV were discarded. W2 is `[510.58, 511.42)` keV. Active-veto flags use exact block names and offline 50/70/80 keV thresholds; native detector thresholds were unchanged.",
        "",
        "| Geometry | Events | TT (s) | TES-positive | Measured W2 | W2 after 50/70/80 | Single-pixel proxy W2 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for geometry in GEOMETRIES:
        row = prompt[geometry]
        lines.append(
            f"| {geometry} | {row['events']:,} | {row['TT_s']:.9g} | {row['tes_positive_events']:,} | "
            f"{row['measured_W2_count']} | {row['W2_pass_50_count']}/{row['W2_pass_70_count']}/{row['W2_pass_80_count']} | "
            f"{row['measured_W2_single_pixel_proxy_count']} |"
        )
    lines.extend(
        [
            "",
            "The single-pixel number is an explicit topology proxy only. It is not the paper's final Compton/FoV selection.",
            "",
            "## BUILDUP position/isotope-state coverage",
            "",
            "The denominator is the full geometry × family BUILDUP TT, including jobs with zero RP. Spatial source placement uses rich-SIM `CC IP RP` physical volume, x/y/z and production time; DAT is used for TT and aggregate cross-checking, not as the spatial authority.",
            "",
            "| Geometry | RP instances | Physical volumes | Volume–isotope-state tuples |",
            "|---|---:|---:|---:|",
        ]
    )
    for geometry in GEOMETRIES:
        row = buildup[geometry]
        lines.append(
            f"| {geometry} | {row['SIM_RP_instances']:,} | {row['unique_physical_volumes']:,} | "
            f"{row['unique_physical_volume_isotope_state_tuples']:,} |"
        )
    lines.extend(
        [
            "",
            "## Exact-whitelist caveat and authority boundary",
            "",
            "S3d-O8 active veto uses exactly three BGO and three plastic blocks. BGO/plastic/mechanical names outside that six-block set are recorded as suspects but never counted as active energy. This avoids the historical broad-substring-reader caveat.",
            "",
            "No historical factor-1000 rates are combined here. No delayed transport, detector-response closure beyond the prompt diagnostic, complete atmospheric model, mission sensitivity, final structure ranking, or geometry decision is claimed.",
            "",
        ]
    )
    return "\n".join(lines)


def build_payloads(scan_result: dict[str, Any], authority_hashes: dict[str, str], terminal: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    created_at = datetime.now(timezone.utc).isoformat()
    prompt_by_geometry = {row["geometry"]: row for row in scan_result["prompt_rows"]}
    summary = {
        "schema_version": 1,
        "created_at": created_at,
        "status": "PASS__BATCH0007_READ_ONLY_PROMPT_ACTIVATION_SCREENING",
        "authority": {
            "terminal": terminal,
            "hashes": authority_hashes,
            "selected_receipts": len(scan_result["cell_rows"]) * 4,
            "artifact_hashes_recomputed_by_analysis": False,
            "partial_inputs_opened": False,
        },
        "raw_scan": scan_result["raw_scan"],
        "prompt_method": {
            "family": "eminus",
            "TES_pixel_regex": TES_RE.pattern,
            "response_seed": M05_RESPONSE_SEED,
            "response_FWHM_keV": M05_RESPONSE_FWHM_KEV,
            "response_sigma_keV": M05_RESPONSE_SIGMA_KEV,
            "measured_pixel_discard_below_keV": MEASURED_PIXEL_THRESHOLD_KEV,
            "W2_keV_half_open": list(W2),
            "offline_active_veto_thresholds_keV": list(VETO_THRESHOLDS_KEV),
            "Mass_exact_active_whitelist": sorted(MASS_ACTIVE),
            "S3d_O8_exact_active_whitelist": sorted(O8_ACTIVE),
            "native_detector_thresholds_changed": False,
            "rate_estimator": "count / sum(TT) within geometry × instant × eminus",
            "topology_proxy": "exactly one measured TES pixel after the 0.3 keV cut; not formal Compton/FoV selection",
        },
        "prompt": scan_result["prompt_rows"],
        "active_observed": scan_result["active_observed"],
        "O8_nonwhitelist_BGO_plastic_mechanical_suspects": scan_result["o8_nonwhitelist_suspects"],
        "O8_exact_whitelist_caveat": (
            "Only the six named BGO/plastic detector blocks contribute to active-veto energy. "
            "Substring matches can admit mechanical volumes and are forbidden."
        ),
        "buildup_method": {
            "families": ["eminus", "muminus"],
            "position_authority": "rich SIM CC IP RP physical volume + x/y/z + production time",
            "DAT_role": "TT and logical aggregate cross-check only; not sufficient for spatial placement",
            "rate_estimator": "production instances / full family TT within geometry × buildup × family",
            "zero_RP_TT_retained": True,
        },
        "buildup": scan_result["buildup_geometry"],
        "paper_executability": {
            "TES_pixel_sum_and_measured_threshold": True,
            "W2_and_offline_active_veto_flags": True,
            "topology_proxy": True,
            "formal_Compton_FoV_selection_executed": False,
            "position_resolved_activation_source_inputs": True,
            "zero_RP_safe_family_statistics": True,
            "final_physics_closure": False,
        },
        "authority_boundary": {
            "included": "batch0007 terminal-PASS supplemental corrected-keV eminus prompt and eminus/muminus BUILDUP only",
            "excluded": [
                "in-progress or .partial inputs",
                "historical factor-1000 rates/rankings",
                "other particle families",
                "delayed transport and detector-response closure",
                "mission sensitivity",
                "final structure/background ranking",
                "geometry promotion",
            ],
        },
        "headline_counts": {
            geometry: {
                "prompt_events": int(prompt_by_geometry[geometry]["events"]),
                "measured_W2": int(prompt_by_geometry[geometry]["measured_W2_count"]),
                "W2_pass_50_70_80": [
                    int(prompt_by_geometry[geometry][f"W2_pass_{threshold}_count"]) for threshold in (50, 70, 80)
                ],
            }
            for geometry in GEOMETRIES
        },
    }

    prompt_fields = [
        "geometry",
        "family",
        "events",
        "TT_s",
        "tes_positive_events",
        "pixel_readouts",
        "max_raw_pixel_multiplicity",
        "max_measured_pixel_multiplicity",
    ]
    for name in (
        "raw_broad",
        "measured_broad",
        "raw_W2",
        "measured_W2",
        "measured_W2_single_pixel_proxy",
        "W2_pass_50",
        "W2_pass_70",
        "W2_pass_80",
        "W2_single_pixel_proxy_pass_50",
        "W2_single_pixel_proxy_pass_70",
        "W2_single_pixel_proxy_pass_80",
    ):
        prompt_fields.extend(
            [f"{name}_count", f"{name}_rate_cps", f"{name}_poisson_RSE", f"{name}_zero_count_95_upper_rate_cps"]
        )

    payloads = {
        "summary.json": json_payload(summary),
        "cell_coverage.csv": csv_payload(
            scan_result["cell_rows"],
            [
                "geometry",
                "mode",
                "family",
                "jobs",
                "events",
                "TT_s",
                "RP_record_count",
                "RP_sum",
                "artifact_bytes",
                "wall_sum_s",
                "max_process_group_RSS_bytes",
                "zero_RP_jobs",
            ],
        ),
        "prompt_observables.csv": csv_payload(scan_result["prompt_rows"], prompt_fields),
        "buildup_family_coverage.csv": csv_payload(
            scan_result["buildup_rows"],
            [
                "geometry",
                "family",
                "jobs",
                "events",
                "TT_s",
                "DAT_RP_record_count",
                "DAT_RP_sum",
                "SIM_RP_instances",
                "zero_RP_jobs",
                "zero_RP_cell",
                "zero_RP_TT_retained",
                "physical_volume_count",
                "physical_volume_isotope_state_tuple_count",
                "production_rate_per_TT_s",
            ],
        ),
        "buildup_volume_isotope_state.csv": csv_payload(
            scan_result["tuple_rows"],
            [
                "geometry",
                "family",
                "physical_volume",
                "isotope_id",
                "excitation_keV",
                "production_instances",
                "production_rate_per_TT_s",
                "x_min_cm",
                "x_max_cm",
                "y_min_cm",
                "y_max_cm",
                "z_min_cm",
                "z_max_cm",
                "production_time_min_s",
                "production_time_max_s",
            ],
        ),
        "buildup_structure_contributions.csv": csv_payload(
            scan_result["structure_rows"],
            [
                "geometry",
                "family",
                "physical_volume",
                "production_instances",
                "production_rate_per_TT_s",
                "isotope_state_count",
                "x_min_cm",
                "x_max_cm",
                "y_min_cm",
                "y_max_cm",
                "z_min_cm",
                "z_max_cm",
            ],
        ),
        "REPORT.md": report_markdown(summary).encode("utf-8"),
    }
    return payloads, summary


def publish_write_once(payloads: dict[str, bytes], authority_hashes: dict[str, str]) -> dict[str, Any]:
    output_collision_check()
    OUTPUT.mkdir(parents=False, exist_ok=False)
    staged: list[tuple[Path, Path, bytes]] = []
    for name, payload in payloads.items():
        target = OUTPUT / name
        partial = OUTPUT / f"{name}.partial"
        with partial.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if partial.stat().st_size != len(payload) or sha256_file(partial) != sha256_bytes(payload):
            raise RuntimeError(f"staged payload verification failed: {partial}")
        staged.append((partial, target, payload))
    for partial, target, _payload in staged:
        if target.exists():
            raise RuntimeError(f"write-once target appeared during publish: {target}")
        os.replace(partial, target)

    members = [
        {"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)}
        for name, payload in sorted(payloads.items())
    ]
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__WRITE_ONCE_ATOMIC_PUBLICATION",
        "canonical_directory": rel(OUTPUT),
        "analysis_code": {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "authority_hashes": authority_hashes,
        "publication_policy": "members staged as .partial and atomically replaced; MANIFEST published last",
        "members": members,
    }
    encoded = json_payload(manifest)
    partial = OUTPUT / "MANIFEST.json.partial"
    target = OUTPUT / "MANIFEST.json"
    with partial.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256_file(partial) != sha256_bytes(encoded):
        raise RuntimeError("manifest staged verification failed")
    os.replace(partial, target)
    directory_fd = os.open(OUTPUT, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {**manifest, "manifest_sha256": sha256_file(target), "manifest_bytes": target.stat().st_size}


def check() -> tuple[dict[str, Any], int]:
    output_collision_check()
    static = {
        "expected_jobs": EXPECTED_JOBS,
        "expected_events": EXPECTED_EVENTS,
        "expected_cells": len(EXPECTED_CELLS),
        "response_seed": M05_RESPONSE_SEED,
        "Mass_exact_active_blocks": len(MASS_ACTIVE),
        "S3d_O8_exact_active_blocks": len(O8_ACTIVE),
        "partial_inputs_opened": False,
        "SIM_or_DAT_opened": False,
        "writes": False,
    }
    if not terminal_files_present():
        return {
            "status": "PASS__READER_STATIC_CHECK__AWAITING_BATCH0007_TERMINAL_AUTHORITY",
            "terminal_ready": False,
            "static": static,
        }, 0
    try:
        receipts, hashes, terminal = selected_receipts()
    except RuntimeError as error:
        return {
            "status": "BLOCKED__BATCH0007_TERMINAL_AUTHORITY_NOT_ANALYSIS_ELIGIBLE",
            "terminal_ready": False,
            "error": str(error),
            "static": static,
        }, 2
    return {
        "status": "PASS__READER_CHECK__TERMINAL_AUTHORITY_READY",
        "terminal_ready": True,
        "selected_receipts": len(receipts),
        "authority_hashes": hashes,
        "terminal": terminal,
        "static": static,
    }, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="static/terminal JSON checks only; never open SIM or DAT")
    mode.add_argument("--run", action="store_true", help="require terminal PASS, scan selected rich SIM/DAT, publish write-once")
    args = parser.parse_args()

    if args.check:
        result, returncode = check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return returncode

    output_collision_check()
    receipts, authority_hashes, terminal = selected_receipts()
    scan_result = scan(receipts)
    payloads, summary = build_payloads(scan_result, authority_hashes, terminal)
    manifest = publish_write_once(payloads, authority_hashes)
    print(
        json.dumps(
            {
                "status": "PASS__BATCH0007_ANALYSIS_PUBLISHED",
                "analysis_status": summary["status"],
                "output": rel(OUTPUT),
                "raw_scan": summary["raw_scan"],
                "headline_counts": summary["headline_counts"],
                "manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
