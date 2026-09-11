#!/usr/bin/env python3
"""Build the write-once batch0006 rich-SIM M05 smoke-closure review.

This program is deliberately read-only with respect to the campaign.  Its only
write target is ANALYSIS_OUT.  It consumes only recovery0001-selected stage00
receipts and their immutable artifacts; later production stages are out of
scope.  All report members are prepared in memory, written as ``.partial``
files, verified, and atomically renamed.  Existing output is a hard failure.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
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
os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_smoke_closure_reviewer01_matplotlib")

ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
PACKAGE_ROOT = ROOT / "engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812"
ANALYSIS_OUT = RUN_ROOT / "analysis_m05_smoke_closure_reviewer01"

SOURCE_CONTRACT = ROOT / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
GLOBAL_CONTRACT = RUN_ROOT / "global_contract.json"
RECOVERY_AUTHORITY = RUN_ROOT / "recovery0001_authority.json"
SMOKE_DECISION = RUN_ROOT / "smoke_decision.recovery0001.json"
VALIDATION = RUN_ROOT / "checkpoint_authority/smoke_validation.recovery0001.json"
LEDGER = RUN_ROOT / "checkpoint_authority/smoke_ledger.recovery0001.json"
BINDING = RUN_ROOT / "checkpoint_authority/stage00_mergeable_smoke.recovery0001.binding.json"

EXPECTED_AUTHORITY_HASHES = {
    "source_contract_manifest": "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326",
    "global_contract": "4586fb62a16c0145401a997f70a878bfaebd94529fe04c45da51a1abcf102275",
    "recovery0001_authority": "50a3e6a81e57f2d16f43732fd4c30b07742a60658ae5f188ced7798c5827e654",
    "smoke_decision_recovery0001": "cd6a25b2ea58ec7217bc545640a6ca3dbb7f3ec160cdf1abc32ce43c1b36be21",
    "smoke_validation_recovery0001": "1d387ecc885af6f0aa3d52ab4c98d60e1b71a30849919aa1d7e87fa718be05a1",
    "smoke_ledger_recovery0001": "a98053b01edde18ba87ae803c065af27764d682f8ed0548d5218184132d300d9",
    "stage00_binding_recovery0001": "3430564a1602ad1c81e4c01ab5913b648e48467935c3a7013f9b1bf31a8af676",
}
AUTHORITY_PATHS = {
    "source_contract_manifest": SOURCE_CONTRACT,
    "global_contract": GLOBAL_CONTRACT,
    "recovery0001_authority": RECOVERY_AUTHORITY,
    "smoke_decision_recovery0001": SMOKE_DECISION,
    "smoke_validation_recovery0001": VALIDATION,
    "smoke_ledger_recovery0001": LEDGER,
    "stage00_binding_recovery0001": BINDING,
}

GEOMETRIES = ("Mass_model_511", "S3d_O8")
MODES = ("buildup", "instant")
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "neutron", "proton")
PARTICLE_TYPE = {"alpha": 21, "eminus": 3, "eplus": 2, "gamma": 1, "muminus": 9, "muplus": 8, "neutron": 6, "proton": 4}

TES_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$")
SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)\s*$")
GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")

MASS_ACTIVE = frozenset(
    {
        "CsI_Side_Segment_00", "CsI_Side_Segment_01", "CsI_Side_Segment_02",
        "CsI_Side_Segment_03_below_side_port", "CsI_Side_Segment_03_above_side_port",
        "CsI_Side_Segment_03_rectcut_window_band", "CsI_Side_Segment_04_below_side_port",
        "CsI_Side_Segment_04_above_side_port", "CsI_Side_Segment_04_rectcut_window_band",
        "CsI_Side_Segment_05", "CsI_Side_Segment_06", "CsI_Side_Segment_07",
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
VETO_THRESHOLDS_KEV = (50.0, 70.0, 80.0)
M05_RESPONSE_SEED = 26071301
M05_RESPONSE_FWHM_KEV = 0.420
M05_RESPONSE_SIGMA_KEV = M05_RESPONSE_FWHM_KEV / 2.354820045
MEASURED_PIXEL_THRESHOLD_KEV = 0.3
W2 = (510.58, 511.42)
BROAD = (480.0, 550.0)

REQUIRED_HIT_KV = frozenset(
    {"edep_keV", "x", "y", "z", "t", "sec", "tid", "pid", "sproc", "prim", "par", "cproc", "primid"}
)
REQUIRED_RP_ANCESTRY = frozenset({"tid", "pid", "sproc", "prim", "par", "cproc"})


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_close(actual: float, expected: float, label: str, atol: float = 1e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=atol):
        raise RuntimeError(f"{label}: {actual!r} != {expected!r}")


def active_blocks(geometry: str) -> frozenset[str]:
    if geometry == "Mass_model_511":
        return MASS_ACTIVE
    if geometry == "S3d_O8":
        return O8_ACTIVE
    raise RuntimeError(f"unknown geometry {geometry}")


def parse_kv(tokens: list[str]) -> dict[str, str]:
    return {key: value for token in tokens if "=" in token for key, value in [token.split("=", 1)]}


def spectrum_support(path: Path) -> tuple[float, float]:
    energies = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "DP":
            energies.append(float(fields[1]))
    if len(energies) < 2 or any(not math.isfinite(value) for value in energies):
        raise RuntimeError(f"invalid corrected spectrum {rel(path)}")
    return min(energies), max(energies)


def source_contract(source_path: Path) -> tuple[dict[int, tuple[float, float]], str, int]:
    text = source_path.read_text(encoding="utf-8", errors="strict")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError(f"legacy spectrum reference in {rel(source_path)}")
    refs = [match.group(1) for line in text.splitlines() if (match := SPECTRUM_RE.search(line))]
    if len(refs) != 20 or any("spectra/correct_keV_total/" not in ref for ref in refs):
        raise RuntimeError(f"corrected 20-bin source contract failed in {rel(source_path)}")
    source_components = sum(1 for line in text.splitlines() if re.search(r"\.Source\s+Atm_", line))
    if source_components != 20:
        raise RuntimeError(f"unexpected source-component count in {rel(source_path)}")
    lowered = text.lower()
    if any(token in lowered for token in ("mono511", "mono_511", "mono-511", "511_line")):
        raise RuntimeError(f"standalone mono-511 marker in {rel(source_path)}")
    geometries = [match.group(1) for line in text.splitlines() if (match := GEOMETRY_RE.match(line.strip()))]
    if len(geometries) != 1:
        raise RuntimeError(f"source Geometry count != 1 in {rel(source_path)}")
    supports = {index: spectrum_support((ROOT / ref).resolve()) for index, ref in enumerate(refs)}
    return supports, geometries[0], source_components


def parse_dat(path: Path) -> dict[str, Any]:
    tt_values: list[float] = []
    current_volume: str | None = None
    rp_records = 0
    rp_sum = 0.0
    tuples: Counter[tuple[str, int, float]] = Counter()
    end_count = 0
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT" and len(fields) == 2:
            tt_values.append(float(fields[1]))
        elif fields[0] == "VN":
            current_volume = line[2:].strip()
        elif fields[0] == "RP" and len(fields) == 4 and current_volume:
            isotope = int(fields[1])
            excitation = float(fields[2])
            quantity = float(fields[3])
            if isotope <= 0 or excitation < 0 or quantity < 0:
                raise RuntimeError(f"invalid RP at {rel(path)}:{number}")
            rp_records += 1
            rp_sum = math.fsum((rp_sum, quantity))
            tuples[(current_volume, isotope, excitation)] += quantity
        elif fields == ["EN"]:
            end_count += 1
        else:
            raise RuntimeError(f"unrecognized DAT record at {rel(path)}:{number}: {line}")
    if len(tt_values) != 1 or not math.isfinite(tt_values[0]) or tt_values[0] <= 0 or end_count != 1:
        raise RuntimeError(f"DAT framing failure in {rel(path)}")
    return {"TT_s": tt_values[0], "RP_record_count": rp_records, "RP_sum": rp_sum, "tuples": tuples}


def audit_authority() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    observed = {name: sha256_file(path) for name, path in AUTHORITY_PATHS.items()}
    if observed != EXPECTED_AUTHORITY_HASHES:
        raise RuntimeError(f"authority hash drift: {observed}")
    global_contract = load_json(GLOBAL_CONTRACT)
    recovery = load_json(RECOVERY_AUTHORITY)
    decision = load_json(SMOKE_DECISION)
    validation = load_json(VALIDATION)
    ledger = load_json(LEDGER)
    binding = load_json(BINDING)
    if global_contract["selected_arm"] != "F_RICH_BASELINE" or global_contract["compact_transport_authorized"] is not False:
        raise RuntimeError("global F-rich/compact boundary failed")
    if global_contract["source_contract"]["sha256"] != observed["source_contract_manifest"]:
        raise RuntimeError("source-contract chain failed")
    if recovery["global_contract_sha256"] != observed["global_contract"]:
        raise RuntimeError("recovery/global chain failed")
    if decision["selected_arm"] != "F_RICH_BASELINE" or not decision["production_may_continue"]:
        raise RuntimeError("smoke decision is not F-rich continuation PASS")
    if not all(str(payload.get("status", "")).startswith("PASS") for payload in (validation, ledger, binding)):
        raise RuntimeError("recovery0001 smoke authority is not PASS")
    if binding["ledger_sha256"] != observed["smoke_ledger_recovery0001"]:
        raise RuntimeError("binding/ledger chain failed")
    if binding["validation_sha256"] != observed["smoke_validation_recovery0001"]:
        raise RuntimeError("binding/validation chain failed")
    if binding["recovery_authority_sha256"] != observed["recovery0001_authority"]:
        raise RuntimeError("binding/recovery chain failed")
    return global_contract, validation, ledger, observed


def receipt_key(receipt: dict[str, Any]) -> tuple[int, int, int, int]:
    job = receipt["job"]
    return (GEOMETRIES.index(job["geometry"]), MODES.index(job["mode"]), FAMILIES.index(job["family"]), int(job["shard_ordinal"]))


def audit_receipts(ledger: dict[str, Any], validation: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    receipt_hash_failures = 0
    for selected in ledger["selected_receipts"]:
        receipt_path = ROOT / selected["path"]
        observed_receipt_hash = sha256_file(receipt_path)
        if observed_receipt_hash != selected["sha256"]:
            receipt_hash_failures += 1
        receipt = load_json(receipt_path)
        receipt["_receipt_path"] = str(receipt_path)
        receipt["_receipt_sha256"] = observed_receipt_hash
        if receipt["status"] != "PASS" or receipt["returncode"] != 0 or receipt["errors"]:
            raise RuntimeError(f"non-PASS receipt {rel(receipt_path)}")
        if receipt["global_contract_sha256"] != EXPECTED_AUTHORITY_HASHES["global_contract"]:
            raise RuntimeError(f"receipt/global mismatch {rel(receipt_path)}")
        if receipt.get("recovery_authority_sha256") != EXPECTED_AUTHORITY_HASHES["recovery0001_authority"]:
            raise RuntimeError(f"receipt/recovery mismatch {rel(receipt_path)}")
        attempt_dir = ROOT / receipt["attempt_dir"]
        for kind in ("source", "sim", "dat", "log"):
            declared = receipt["artifacts"][kind]
            artifact = attempt_dir / declared["name"]
            observed_size = artifact.stat().st_size
            observed_hash = sha256_file(artifact)
            if observed_size != declared["bytes"] or observed_hash != declared["sha256"]:
                raise RuntimeError(f"artifact mismatch {rel(artifact)}")
            artifact_rows.append(
                {
                    "job_id": receipt["job"]["job_id"], "geometry": receipt["job"]["geometry"],
                    "mode": receipt["job"]["mode"], "family": receipt["job"]["family"],
                    "shard_ordinal": receipt["job"]["shard_ordinal"], "kind": kind, "path": rel(artifact),
                    "bytes": observed_size, "sha256": observed_hash, "receipt_match": True,
                }
            )
        receipts.append(receipt)
    if receipt_hash_failures or len(receipts) != 100:
        raise RuntimeError(f"receipt audit failed: count={len(receipts)} hash failures={receipt_hash_failures}")
    receipts.sort(key=receipt_key)

    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for receipt in receipts:
        job = receipt["job"]
        key = (job["geometry"], job["mode"], job["family"])
        row = grouped.setdefault(
            key,
            {
                "geometry": key[0], "mode": key[1], "family": key[2], "jobs": 0, "events": 0,
                "TT_s": 0.0, "RP_record_count": 0, "RP_sum": 0.0, "artifact_bytes": 0,
                "RSS_max_bytes": 0, "wall_sum_s": 0.0, "beam_on_cpu_sum_s": 0.0, "zero_RP_jobs": 0,
            },
        )
        row["jobs"] += 1
        row["events"] += int(job["events"])
        row["TT_s"] = math.fsum((row["TT_s"], float(receipt["isotope_dat"]["TT_s"])))
        row["RP_record_count"] += int(receipt["isotope_dat"]["RP_record_count"])
        row["RP_sum"] = math.fsum((row["RP_sum"], float(receipt["isotope_dat"]["RP_sum"])))
        row["artifact_bytes"] += sum(int(value["bytes"]) for value in receipt["artifacts"].values())
        row["RSS_max_bytes"] = max(row["RSS_max_bytes"], int(receipt["peak_process_group_rss_bytes"]))
        row["wall_sum_s"] = math.fsum((row["wall_sum_s"], float(receipt["wall_s"])))
        row["beam_on_cpu_sum_s"] = math.fsum((row["beam_on_cpu_sum_s"], float(receipt["log"]["beam_on_cpu_s"])))
        row["zero_RP_jobs"] += int(float(receipt["isotope_dat"]["RP_sum"]) == 0.0)
    cell_rows = [grouped[key] for key in sorted(grouped, key=lambda key: (GEOMETRIES.index(key[0]), MODES.index(key[1]), FAMILIES.index(key[2])))]
    if len(cell_rows) != 32:
        raise RuntimeError(f"cell coverage={len(cell_rows)}, expected 32")
    validation_by_key = {(row["geometry"], row["mode"], row["family"]): row for row in validation["cells"]}
    for row in cell_rows:
        expected = validation_by_key[(row["geometry"], row["mode"], row["family"])]
        for field, validation_field in (("jobs", "jobs"), ("events", "events"), ("RP_record_count", "RP_count")):
            if row[field] != expected[validation_field]:
                raise RuntimeError(f"cell {field} mismatch: {row}")
        assert_close(row["TT_s"], float(expected["TT_s"]), f"cell TT {row['geometry']}/{row['mode']}/{row['family']}", 2e-9)

    totals = {
        "receipts": len(receipts), "cells": len(cell_rows),
        "events": sum(row["events"] for row in cell_rows),
        "TT_s": math.fsum(row["TT_s"] for row in cell_rows),
        "RP_record_count": sum(row["RP_record_count"] for row in cell_rows),
        "RP_sum": math.fsum(row["RP_sum"] for row in cell_rows),
        "artifact_bytes": sum(row["artifact_bytes"] for row in cell_rows),
        "RSS_max_bytes": max(row["RSS_max_bytes"] for row in cell_rows),
        "wall_sum_s": math.fsum(row["wall_sum_s"] for row in cell_rows),
        "beam_on_cpu_sum_s": math.fsum(row["beam_on_cpu_sum_s"] for row in cell_rows),
        "zero_RP_jobs": sum(row["zero_RP_jobs"] for row in cell_rows),
    }
    expected_totals = {
        "events": 55424, "RP_record_count": 1003, "RP_sum": 1330.0,
        "artifact_bytes": 653390814, "RSS_max_bytes": 2096963584, "zero_RP_jobs": 71,
    }
    for field, expected in expected_totals.items():
        if totals[field] != expected:
            raise RuntimeError(f"total {field}={totals[field]} != {expected}")
    assert_close(totals["TT_s"], 42.8715377, "total TT", 2e-9)
    assert_close(totals["wall_sum_s"], 2057.743302298157, "total wall", 2e-9)
    assert_close(totals["beam_on_cpu_sum_s"], 811.592011, "total beam CPU", 2e-9)
    return receipts, cell_rows, artifact_rows, totals


def scan_rich_sim(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_events: dict[str, dict[str, list[dict[str, Any]]]] = {
        geometry: {family: [] for family in FAMILIES} for geometry in GEOMETRIES
    }
    prompt_meta: dict[str, dict[str, dict[str, Any]]] = {
        geometry: {family: defaultdict(int) for family in FAMILIES} for geometry in GEOMETRIES
    }
    active_observed = {geometry: set() for geometry in GEOMETRIES}
    prompt_cc_hit_count = 0
    prompt_cc_typed_missing = 0
    prompt_tes_steps = 0
    sim_total_events = 0
    sim_total_init = 0
    sim_bad_id_pair = 0
    sim_bad_particle = 0
    sim_bad_direction = 0
    sim_bad_energy_support = 0
    sample_hit_line: str | None = None
    sample_reader_receipt: dict[str, Any] | None = None

    rp_tuple: dict[tuple[str, str, str, int, float], dict[str, Any]] = {}
    rp_structure: dict[tuple[str, str, str], dict[str, Any]] = {}
    buildup_family: dict[tuple[str, str], dict[str, Any]] = {}
    sim_rp_by_job: Counter[str] = Counter()
    sim_rp_by_geometry: Counter[str] = Counter()
    sim_rp_ancestry_missing = 0
    sim_rp_position_invalid = 0

    support_cache: dict[str, tuple[dict[int, tuple[float, float]], str, int]] = {}
    job_kept_exact: Counter[str] = Counter()

    for receipt in receipts:
        job = receipt["job"]
        geometry, mode, family = job["geometry"], job["mode"], job["family"]
        attempt_dir = ROOT / receipt["attempt_dir"]
        source_path = attempt_dir / receipt["artifacts"]["source"]["name"]
        sim_path = attempt_dir / receipt["artifacts"]["sim"]["name"]
        dat_path = attempt_dir / receipt["artifacts"]["dat"]["name"]
        log_path = attempt_dir / receipt["artifacts"]["log"]["name"]

        source_key = receipt["source"]["base_source_sha256"]
        if source_key not in support_cache:
            support_cache[source_key] = source_contract(source_path)
        supports, source_geometry, _source_components = support_cache[source_key]
        expected_geometry = str(Path(receipt["sim"]["geometry_header"]).resolve())
        resolved_source_geometry = str((ROOT / source_geometry).resolve()) if not Path(source_geometry).is_absolute() else str(Path(source_geometry).resolve())
        if resolved_source_geometry != expected_geometry:
            raise RuntimeError(f"source geometry mismatch for {job['job_id']}")

        dat = parse_dat(dat_path)
        assert_close(dat["TT_s"], float(receipt["isotope_dat"]["TT_s"]), f"DAT receipt TT {job['job_id']}", 2e-9)
        if dat["RP_record_count"] != receipt["isotope_dat"]["RP_record_count"]:
            raise RuntimeError(f"DAT RP-record mismatch {job['job_id']}")
        assert_close(dat["RP_sum"], float(receipt["isotope_dat"]["RP_sum"]), f"DAT RP sum {job['job_id']}", 1e-9)
        log_text = log_path.read_text(encoding="utf-8", errors="strict")
        generated = [int(match.group(1)) for match in GENERATED_RE.finditer(log_text)]
        observations = [float(match.group(1)) for match in OBSERVATION_RE.finditer(log_text)]
        if not generated or generated[-1] != job["events"] or not observations:
            raise RuntimeError(f"log generated/TT missing {job['job_id']}")
        assert_close(observations[-1], dat["TT_s"], f"log/DAT TT {job['job_id']}", 2e-6)

        current_id: int | None = None
        current_init = 0
        pixels: dict[str, dict[str, float]] = {}
        active: Counter[str] = Counter()
        file_events = 0
        file_init = 0
        se_count = 0
        en_count = 0
        next_id = 1
        header_geometry: str | None = None
        header_seed: int | None = None

        def flush_event() -> None:
            nonlocal current_id, current_init, pixels, active, file_events
            if current_id is None:
                return
            if current_init != 1:
                raise RuntimeError(f"{job['job_id']} event {current_id}: IA INIT count={current_init}")
            if mode == "instant":
                pixel_rows = [(uid, record["energy_keV"]) for uid, record in sorted(pixels.items())]
                active_total = math.fsum(active.values())
                prompt_events[geometry][family].append(
                    {"job_id": job["job_id"], "event_id": current_id, "pixels": pixel_rows, "active_total_keV": active_total}
                )
                if pixel_rows:
                    prompt_meta[geometry][family]["tes_positive_events"] += 1
                    prompt_meta[geometry][family]["pixel_readouts"] += len(pixel_rows)
                    prompt_meta[geometry][family]["max_pixel_multiplicity"] = max(
                        prompt_meta[geometry][family]["max_pixel_multiplicity"], len(pixel_rows)
                    )
                if pixel_rows or active_total > 0:
                    job_kept_exact[job["job_id"]] += 1
            file_events += 1
            current_id = None
            current_init = 0
            pixels = {}
            active = Counter()

        with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
            for raw in handle:
                line = raw.strip()
                if header_geometry is None and (match := GEOMETRY_RE.match(line)):
                    header_geometry = match.group(1)
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
                    if len(fields) != 3:
                        raise RuntimeError(f"non-two-column ID in {job['job_id']}: {line}")
                    first, second = int(fields[1]), int(fields[2])
                    if first != second:
                        sim_bad_id_pair += 1
                    if first != next_id:
                        raise RuntimeError(f"ID sequence in {job['job_id']}: {first} != {next_id}")
                    next_id += 1
                    current_id = first
                    continue
                if line.startswith("IA INIT"):
                    if current_id is None:
                        raise RuntimeError(f"IA INIT outside event in {job['job_id']}")
                    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
                    if len(fields) < 23:
                        raise RuntimeError(f"malformed IA INIT in {job['job_id']}")
                    particle = int(fields[15])
                    direction = tuple(float(fields[index]) for index in (16, 17, 18))
                    energy = float(fields[22])
                    current_init += 1
                    file_init += 1
                    sim_bad_particle += int(particle != PARTICLE_TYPE[family])
                    norm = math.sqrt(math.fsum(value * value for value in direction))
                    sim_bad_direction += int(not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5e-4))
                    angular = max(0, min(19, int(math.floor((1.0 + direction[2]) * 10.0))))
                    low, high = supports[angular]
                    tolerance = max(0.002, 1e-10 * max(abs(low), abs(high)))
                    neighbors = [supports[index] for index in (angular - 1, angular + 1) if index in supports]
                    supported = low - tolerance <= energy <= high + tolerance or any(
                        neighbor_low - tolerance <= energy <= neighbor_high + tolerance
                        for neighbor_low, neighbor_high in neighbors
                    )
                    sim_bad_energy_support += int(not supported)
                    continue
                if mode == "instant" and line.startswith("CC HIT "):
                    prompt_cc_hit_count += 1
                    fields = line.split()
                    if len(fields) < 4:
                        raise RuntimeError(f"malformed CC HIT in {job['job_id']}")
                    volume = fields[2]
                    kv = parse_kv(fields[3:])
                    prompt_cc_typed_missing += int(not REQUIRED_HIT_KV.issubset(kv))
                    if not REQUIRED_HIT_KV.issubset(kv):
                        continue
                    edep = float(kv["edep_keV"])
                    x, y, z, time_s = (float(kv[key]) for key in ("x", "y", "z", "t"))
                    if edep < 0 or not all(math.isfinite(value) for value in (edep, x, y, z, time_s)):
                        raise RuntimeError(f"invalid CC HIT numeric fields in {job['job_id']}")
                    if sample_hit_line is None:
                        sample_hit_line = line
                    match = TES_RE.fullmatch(volume)
                    if match:
                        prompt_tes_steps += 1
                        record = pixels.setdefault(
                            volume,
                            {"energy_keV": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "t_min": time_s, "t_max": time_s},
                        )
                        record["energy_keV"] += edep
                        record["wx"] += edep * x
                        record["wy"] += edep * y
                        record["wz"] += edep * z
                        record["t_min"] = min(record["t_min"], time_s)
                        record["t_max"] = max(record["t_max"], time_s)
                    elif volume in active_blocks(geometry):
                        active[volume] += edep
                        active_observed[geometry].add(volume)
                    continue
                if mode == "buildup" and line.startswith("CC IP RP "):
                    fields = line.split()
                    if len(fields) < 11:
                        raise RuntimeError(f"malformed CC IP RP in {job['job_id']}")
                    volume = fields[3]
                    x, y, z = (float(fields[index]) for index in (4, 5, 6))
                    isotope = int(fields[7])
                    excitation = float(fields[8])
                    production_time_s = float(fields[9])
                    kv = parse_kv(fields[10:])
                    sim_rp_ancestry_missing += int(not REQUIRED_RP_ANCESTRY.issubset(kv))
                    invalid_position = not all(math.isfinite(value) for value in (x, y, z, production_time_s))
                    sim_rp_position_invalid += int(invalid_position)
                    if invalid_position or isotope <= 0 or excitation < 0:
                        raise RuntimeError(f"invalid CC IP RP numeric fields in {job['job_id']}")
                    sim_rp_by_job[job["job_id"]] += 1
                    sim_rp_by_geometry[geometry] += 1
                    tuple_key = (geometry, family, volume, isotope, excitation)
                    tuple_row = rp_tuple.setdefault(
                        tuple_key,
                        {
                            "geometry": geometry, "family": family, "physical_volume": volume,
                            "isotope_id": isotope, "excitation_keV": excitation, "production_instances": 0,
                            "x_min_cm": x, "x_max_cm": x, "y_min_cm": y, "y_max_cm": y,
                            "z_min_cm": z, "z_max_cm": z, "production_time_min_s": production_time_s,
                            "production_time_max_s": production_time_s,
                        },
                    )
                    tuple_row["production_instances"] += 1
                    for axis, value in (("x", x), ("y", y), ("z", z)):
                        tuple_row[f"{axis}_min_cm"] = min(tuple_row[f"{axis}_min_cm"], value)
                        tuple_row[f"{axis}_max_cm"] = max(tuple_row[f"{axis}_max_cm"], value)
                    tuple_row["production_time_min_s"] = min(tuple_row["production_time_min_s"], production_time_s)
                    tuple_row["production_time_max_s"] = max(tuple_row["production_time_max_s"], production_time_s)
                    structure_key = (geometry, family, volume)
                    structure_row = rp_structure.setdefault(
                        structure_key,
                        {
                            "geometry": geometry, "family": family, "physical_volume": volume,
                            "production_instances": 0, "isotope_states": set(),
                            "x_min_cm": x, "x_max_cm": x, "y_min_cm": y, "y_max_cm": y,
                            "z_min_cm": z, "z_max_cm": z,
                        },
                    )
                    structure_row["production_instances"] += 1
                    structure_row["isotope_states"].add((isotope, excitation))
                    for axis, value in (("x", x), ("y", y), ("z", z)):
                        structure_row[f"{axis}_min_cm"] = min(structure_row[f"{axis}_min_cm"], value)
                        structure_row[f"{axis}_max_cm"] = max(structure_row[f"{axis}_max_cm"], value)
                    continue
        flush_event()
        observed_geometry = str((ROOT / header_geometry).resolve()) if header_geometry and not Path(header_geometry).is_absolute() else str(Path(header_geometry).resolve()) if header_geometry else None
        if observed_geometry != expected_geometry or header_seed != job["seed"]:
            raise RuntimeError(f"SIM Geometry/Seed mismatch {job['job_id']}")
        if file_events != job["events"] or file_init != job["events"] or se_count != job["events"] or en_count != 1:
            raise RuntimeError(f"SIM framing mismatch {job['job_id']}")
        sim_total_events += file_events
        sim_total_init += file_init
        if mode == "buildup":
            assert_close(float(sim_rp_by_job[job["job_id"]]), dat["RP_sum"], f"SIM/DAT RP instances {job['job_id']}", 1e-9)
            key = (geometry, family)
            row = buildup_family.setdefault(
                key,
                {
                    "geometry": geometry, "family": family, "jobs": 0, "events": 0, "TT_s": 0.0,
                    "DAT_RP_record_count": 0, "DAT_RP_sum": 0.0, "SIM_RP_instances": 0,
                    "zero_RP_jobs": 0,
                },
            )
            row["jobs"] += 1
            row["events"] += job["events"]
            row["TT_s"] = math.fsum((row["TT_s"], dat["TT_s"]))
            row["DAT_RP_record_count"] += dat["RP_record_count"]
            row["DAT_RP_sum"] = math.fsum((row["DAT_RP_sum"], dat["RP_sum"]))
            row["SIM_RP_instances"] += sim_rp_by_job[job["job_id"]]
            row["zero_RP_jobs"] += int(dat["RP_sum"] == 0.0)
        if sample_reader_receipt is None and geometry == "Mass_model_511" and mode == "instant" and family == "alpha":
            sample_reader_receipt = receipt

    if any((sim_bad_id_pair, sim_bad_particle, sim_bad_direction, sim_bad_energy_support)):
        raise RuntimeError(
            f"SIM identity/init failures: ID={sim_bad_id_pair} particle={sim_bad_particle} "
            f"direction={sim_bad_direction} support={sim_bad_energy_support}"
        )
    if sim_total_events != 55424 or sim_total_init != 55424:
        raise RuntimeError(f"SIM total events/init={sim_total_events}/{sim_total_init}")
    if prompt_cc_hit_count != 7454488 or prompt_cc_typed_missing != 0 or prompt_tes_steps != 6906:
        raise RuntimeError(
            f"prompt typed scan mismatch: hits={prompt_cc_hit_count} missing={prompt_cc_typed_missing} TES={prompt_tes_steps}"
        )
    if sim_rp_by_geometry != Counter({"Mass_model_511": 352, "S3d_O8": 978}):
        raise RuntimeError(f"SIM RP totals mismatch {sim_rp_by_geometry}")
    if sim_rp_ancestry_missing or sim_rp_position_invalid:
        raise RuntimeError(f"RP field failures ancestry={sim_rp_ancestry_missing} position={sim_rp_position_invalid}")
    for geometry in GEOMETRIES:
        if active_observed[geometry] != set(active_blocks(geometry)):
            raise RuntimeError(f"active block coverage {geometry}: {active_observed[geometry]}")

    prompt_rows: list[dict[str, Any]] = []
    prompt_geometry: dict[str, Any] = {}
    cell_tt = {
        (receipt["job"]["geometry"], receipt["job"]["family"]): 0.0 for receipt in receipts if receipt["job"]["mode"] == "instant"
    }
    for receipt in receipts:
        job = receipt["job"]
        if job["mode"] == "instant":
            key = (job["geometry"], job["family"])
            cell_tt[key] = math.fsum((cell_tt[key], float(receipt["isotope_dat"]["TT_s"])))

    for geometry in GEOMETRIES:
        rng = np.random.default_rng(M05_RESPONSE_SEED)
        geometry_totals = Counter()
        geometry_rate_sums = defaultdict(float)
        w2_active_energies: list[float] = []
        for family in FAMILIES:
            counts = Counter()
            for event in prompt_events[geometry][family]:
                raw_total = math.fsum(energy for _uid, energy in event["pixels"])
                measured_pixels = [float(rng.normal(energy, M05_RESPONSE_SIGMA_KEV)) for _uid, energy in event["pixels"]]
                measured_total = math.fsum(value for value in measured_pixels if value >= MEASURED_PIXEL_THRESHOLD_KEV)
                raw_broad = BROAD[0] <= raw_total < BROAD[1]
                measured_broad = BROAD[0] <= measured_total < BROAD[1]
                raw_w2 = W2[0] <= raw_total < W2[1]
                measured_w2 = W2[0] <= measured_total < W2[1]
                counts["raw_broad"] += int(raw_broad)
                counts["measured_broad"] += int(measured_broad)
                counts["raw_W2"] += int(raw_w2)
                counts["measured_W2"] += int(measured_w2)
                if measured_w2:
                    w2_active_energies.append(float(event["active_total_keV"]))
                    for threshold in VETO_THRESHOLDS_KEV:
                        counts[f"W2_pass_{int(threshold)}"] += int(event["active_total_keV"] < threshold)
            tt = cell_tt[(geometry, family)]
            meta = prompt_meta[geometry][family]
            row: dict[str, Any] = {
                "geometry": geometry, "family": family, "events": len(prompt_events[geometry][family]),
                "TT_s": tt, "tes_positive_events": int(meta["tes_positive_events"]),
                "pixel_readouts": int(meta["pixel_readouts"]),
                "max_pixel_multiplicity": int(meta["max_pixel_multiplicity"]),
            }
            for name in ("raw_broad", "measured_broad", "raw_W2", "measured_W2", "W2_pass_50", "W2_pass_70", "W2_pass_80"):
                row[f"{name}_count"] = int(counts[name])
                row[f"{name}_rate_cps"] = float(counts[name] / tt)
                geometry_totals[name] += counts[name]
                geometry_rate_sums[name] += counts[name] / tt
            prompt_rows.append(row)
        prompt_geometry[geometry] = {
            "events": sum(len(prompt_events[geometry][family]) for family in FAMILIES),
            "tes_positive_events": sum(int(prompt_meta[geometry][family]["tes_positive_events"]) for family in FAMILIES),
            "pixel_readouts": sum(int(prompt_meta[geometry][family]["pixel_readouts"]) for family in FAMILIES),
            "counts": dict(geometry_totals),
            "sum_of_family_rates_cps": dict(geometry_rate_sums),
            "measured_W2_active_energy_keV": w2_active_energies,
            "rate_definition": "sum by family of count_family / sum_TT_family; never pooled across family",
        }
    if prompt_geometry["Mass_model_511"]["events"] != 13856 or prompt_geometry["S3d_O8"]["events"] != 13856:
        raise RuntimeError(f"prompt geometry event coverage mismatch {prompt_geometry}")
    if prompt_geometry["Mass_model_511"]["counts"]["measured_W2"] != 0:
        raise RuntimeError("unexpected Mass measured W2 count")
    if prompt_geometry["Mass_model_511"]["counts"]["measured_broad"] != 1:
        raise RuntimeError("unexpected Mass broad count")
    if prompt_geometry["S3d_O8"]["counts"]["measured_W2"] != 1 or prompt_geometry["S3d_O8"]["counts"]["measured_broad"] != 9:
        raise RuntimeError("unexpected O8 W2/broad count")
    if any(prompt_geometry["S3d_O8"]["counts"][f"W2_pass_{threshold}"] for threshold in (50, 70, 80)):
        raise RuntimeError("unexpected O8 post-veto W2 survivor")

    family_rows: list[dict[str, Any]] = []
    for key in sorted(buildup_family, key=lambda value: (GEOMETRIES.index(value[0]), FAMILIES.index(value[1]))):
        row = buildup_family[key]
        tuples_for_family = [value for tuple_key, value in rp_tuple.items() if tuple_key[0] == key[0] and tuple_key[1] == key[1]]
        row["physical_volume_count"] = len({value["physical_volume"] for value in tuples_for_family})
        row["physical_volume_isotope_state_tuple_count"] = len(tuples_for_family)
        row["production_rate_per_TT_s"] = row["SIM_RP_instances"] / row["TT_s"]
        row["zero_RP_cell"] = row["SIM_RP_instances"] == 0
        family_rows.append(row)

    tuple_rows = []
    for key in sorted(rp_tuple, key=lambda value: (GEOMETRIES.index(value[0]), FAMILIES.index(value[1]), value[2], value[3], value[4])):
        row = dict(rp_tuple[key])
        denominator = buildup_family[(row["geometry"], row["family"])]["TT_s"]
        row["production_rate_per_TT_s"] = row["production_instances"] / denominator
        tuple_rows.append(row)

    structure_rows = []
    for key in sorted(rp_structure, key=lambda value: (GEOMETRIES.index(value[0]), FAMILIES.index(value[1]), value[2])):
        value = rp_structure[key]
        denominator = buildup_family[(value["geometry"], value["family"])]["TT_s"]
        row = {field: field_value for field, field_value in value.items() if field != "isotope_states"}
        row["isotope_state_count"] = len(value["isotope_states"])
        row["production_rate_per_TT_s"] = value["production_instances"] / denominator
        structure_rows.append(row)

    buildup_geometry = {}
    for geometry in GEOMETRIES:
        geometry_tuples = {(row["physical_volume"], row["isotope_id"], row["excitation_keV"]) for row in tuple_rows if row["geometry"] == geometry}
        geometry_volumes = {row["physical_volume"] for row in tuple_rows if row["geometry"] == geometry}
        buildup_geometry[geometry] = {
            "SIM_RP_instances": int(sim_rp_by_geometry[geometry]),
            "unique_physical_volume_isotope_state_tuples": len(geometry_tuples),
            "unique_physical_volumes": len(geometry_volumes),
            "position_fields_valid_instances": int(sim_rp_by_geometry[geometry]),
            "ancestry_fields_valid_instances": int(sim_rp_by_geometry[geometry]),
        }
    expected_coverage = {
        "Mass_model_511": (352, 267, 83),
        "S3d_O8": (978, 383, 67),
    }
    for geometry, expected in expected_coverage.items():
        observed = buildup_geometry[geometry]
        if (observed["SIM_RP_instances"], observed["unique_physical_volume_isotope_state_tuples"], observed["unique_physical_volumes"]) != expected:
            raise RuntimeError(f"buildup physical coverage mismatch {geometry}: {observed}")

    reader_compatibility = test_existing_reader(sample_reader_receipt, sample_hit_line, job_kept_exact)
    return {
        "prompt_rows": prompt_rows,
        "prompt_geometry": prompt_geometry,
        "buildup_family_rows": family_rows,
        "buildup_tuple_rows": tuple_rows,
        "buildup_structure_rows": structure_rows,
        "buildup_geometry": buildup_geometry,
        "reader_compatibility": reader_compatibility,
        "raw_scan": {
            "receipts": len(receipts), "events": sim_total_events, "IA_INIT": sim_total_init,
            "gzip_EOF_files": len(receipts), "prompt_jobs": 50, "prompt_events": 27712,
            "prompt_CC_HIT": prompt_cc_hit_count, "prompt_CC_HIT_typed_missing": prompt_cc_typed_missing,
            "prompt_TES_steps": prompt_tes_steps, "buildup_jobs": 50, "buildup_events": 27712,
            "buildup_SIM_RP_instances": int(sum(sim_rp_by_geometry.values())),
            "buildup_RP_ancestry_missing": sim_rp_ancestry_missing,
            "buildup_RP_position_invalid": sim_rp_position_invalid,
            "bad_ID_pair": sim_bad_id_pair, "bad_particle": sim_bad_particle,
            "bad_direction": sim_bad_direction, "bad_corrected_energy_support": sim_bad_energy_support,
        },
        "active_block_coverage": {
            geometry: {"expected": sorted(active_blocks(geometry)), "observed": sorted(active_observed[geometry])}
            for geometry in GEOMETRIES
        },
    }


def test_existing_reader(
    receipt: dict[str, Any] | None, sample_hit_line: str | None, job_kept_exact: Counter[str]
) -> dict[str, Any]:
    if receipt is None or sample_hit_line is None:
        raise RuntimeError("reader sample was not captured")
    reader_path = ROOT / "old/code/tools/make_complete_day15_report_ADR.py"
    reader_dir = reader_path.parent
    sys.path.insert(0, str(reader_dir))
    try:
        spec = importlib.util.spec_from_file_location("m05_existing_reader_smoke_test", reader_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load established M05 reader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        parsed_hit = module.parse_cc_hit(sample_hit_line)
        if parsed_hit is None or len(parsed_hit) != 5:
            raise RuntimeError("established reader did not parse observed CC HIT")
        module.event_rate_for_mode = lambda _path, _mode, _science_flux: ("prompt", "smoke", 1.0)
        geometry = receipt["job"]["geometry"]
        module.is_active_veto_volume = lambda volume: volume in active_blocks(geometry)
        sim_path = ROOT / receipt["attempt_dir"] / receipt["artifacts"]["sim"]["name"]
        catalog = module.parse_sim_catalog((sim_path, "prompt", 1.0))
        expected_generated = receipt["job"]["events"]
        expected_kept = job_kept_exact[receipt["job"]["job_id"]]
        if catalog["n_generated_events_seen"] != expected_generated or catalog["n_kept_events"] != expected_kept:
            raise RuntimeError("established reader representative-file count mismatch")
        return {
            "status": "PASS_WITH_EXACT_O8_WHITELIST_REQUIRED",
            "reader_path": rel(reader_path), "reader_sha256": sha256_file(reader_path),
            "observed_CC_HIT_parse": True, "representative_SIM": rel(sim_path),
            "representative_generated_events": int(catalog["n_generated_events_seen"]),
            "representative_kept_events": int(catalog["n_kept_events"]),
            "caveat": (
                "The historical broad O8 active-volume predicate can include mechanical names containing BGO/ActiveShield. "
                "Use the six exact O8 BGO/plastic names recorded in this report. Raw data are not invalid."
            ),
        }
    finally:
        if sys.path and sys.path[0] == str(reader_dir):
            sys.path.pop(0)


def csv_payload(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def json_payload(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def build_report_markdown(summary: dict[str, Any]) -> str:
    prompt = summary["prompt"]
    buildup = summary["buildup"]
    return f"""# Batch0006 rich-SIM M05 smoke closure — reviewer01

VERDICT=ANALYSIS_READY_CONTINUE

## Technical summary

The recovery0001 F-rich smoke is transport-valid and analysis-ready. The independent read-only scan closed **100/100 receipts, 55,424/55,424 events, 400 artifacts, 32/32 cells, 42.8715377 s of TT, 1,003 DAT RP records and 1,330 production instances**. The main campaign may continue. This is a corrected-keV smoke and analysis-pipeline compatibility result, not a complete M05 physics result.

The raw records are sufficient to execute the paper's offline active veto, Compton/topology veto and family-separated statistics. They also preserve position-resolved activation production for a secondary delayed-source chain. Execution feasibility does not establish final veto gain, background ranking, delayed response, sensitivity or geometry promotion.

## Actual rich-SIM evidence supports the intended analysis

The prompt scan read 50 recovery-selected SIM files and {summary['raw_scan']['prompt_events']:,} events, including {summary['raw_scan']['prompt_CC_HIT']:,} typed `CC HIT` records. All required deposit fields were present. TES deposits can be grouped by `TP_L<layer>_<pixel>`, with energy-weighted position and per-step time retained. The scan found {summary['raw_scan']['prompt_TES_steps']:,} TES steps.

The diagnostic response used FWHM 0.420 keV (`sigma={M05_RESPONSE_SIGMA_KEV:.12f} keV`), seed {M05_RESPONSE_SEED}, independent per-pixel Gaussian smearing, rejection of measured pixels below 0.3 keV, and event summation. W2 is the half-open interval `[510.58, 511.42) keV`. Active-veto flags were constructed offline at 50/70/80 keV without changing native detector thresholds.

| Geometry | Prompt events | TES-positive events | Pixel sums | Measured 480–550 | Measured W2 before veto | W2 after 50/70/80 keV veto |
|---|---:|---:|---:|---:|---:|---:|
| Mass_model_511 | {prompt['Mass_model_511']['events']:,} | {prompt['Mass_model_511']['tes_positive_events']} | {prompt['Mass_model_511']['pixel_readouts']} | {prompt['Mass_model_511']['counts']['measured_broad']} | {prompt['Mass_model_511']['counts']['measured_W2']} | {prompt['Mass_model_511']['counts']['W2_pass_50']}/{prompt['Mass_model_511']['counts']['W2_pass_70']}/{prompt['Mass_model_511']['counts']['W2_pass_80']} |
| S3d_O8 | {prompt['S3d_O8']['events']:,} | {prompt['S3d_O8']['tes_positive_events']} | {prompt['S3d_O8']['pixel_readouts']} | {prompt['S3d_O8']['counts']['measured_broad']} | {prompt['S3d_O8']['counts']['measured_W2']} | {prompt['S3d_O8']['counts']['W2_pass_50']}/{prompt['S3d_O8']['counts']['W2_pass_70']}/{prompt['S3d_O8']['counts']['W2_pass_80']} |

These counts are deliberately reported as a small-sample diagnostic. Rates in `prompt_observables.csv` are `count_family / sum(TT_family)` and geometry totals are sums of family rates; TT is never pooled across families.

## Active and Compton veto are executable, but their final benefit is not yet measured

Mass uses the exact 24-name CsI set. S3d-O8 uses exactly three BGO and three plastic volumes listed in `review_summary.json`. The historical broad substring predicate can incorrectly admit O8 mechanical aluminium/Kapton names; this report therefore uses an exact six-block whitelist. That reader caveat is repairable in analysis and does not invalidate the raw data.

The TES records contain pixel identity, energy, x/y/z, per-step time and multiplicity, so the paper's Compton ordering and geometry/FoV tests can be executed. This smoke does not have enough survivors or exposure to claim a Compton-veto gain or a final structure/background ranking.

## Position-resolved activation is present and normalized

The BUILDUP scan read 50 SIM files and {summary['raw_scan']['buildup_events']:,} events. Each `CC IP RP` instance contains physical volume, x/y/z, isotope ID, excitation/state, production time and ancestry. Mass contains {buildup['Mass_model_511']['SIM_RP_instances']} instances in {buildup['Mass_model_511']['unique_physical_volumes']} physical volumes and {buildup['Mass_model_511']['unique_physical_volume_isotope_state_tuples']} unique volume–isotope-state tuples; S3d-O8 contains {buildup['S3d_O8']['SIM_RP_instances']}, {buildup['S3d_O8']['unique_physical_volumes']} and {buildup['S3d_O8']['unique_physical_volume_isotope_state_tuples']}, respectively.

This supports the proposed innovation of constructing secondary activation/delayed sources at the actual production positions. The rich SIM is the position authority; DAT is a logical-volume/isotope-state aggregate and must not be used alone for spatial source placement. `buildup_volume_isotope_state.csv` preserves spatial bounds and production-time coverage; `buildup_structure_contributions.csv` supports preliminary structure-level production screening.

Zero-RP exposure is retained: Mass e− has TT 0.212525 s, Mass μ+ 4.07182 s, and O8 μ+ 3.9965 s with zero production. The estimator is `sum(RP instances) / sum(TT)` within geometry × BUILDUP × family × volume × isotope-state; zero-RP TT remains in the denominator.

## Authority and robustness checks close

All selected receipt and source/SIM/DAT/log artifact hashes match. Gzip streams reached EOF; both ID columns are equal and exactly `1..N`; IA INIT particle, unit direction and corrected-keV angular-bin support pass; source and SIM Geometry/Seed agree; DAT TT agrees with logs; and the global/recovery/validation/ledger/binding chain matches `authority_hashes.json`.

The established typed reader was run on an actual selected SIM and reproduced its generated/kept counts after substituting the exact active-volume set. Historical reader code and historical factor-1000 rates are structural references only, not physics authority.

## Authority boundary and limitations

- Only recovery0001-selected `stage00_mergeable_smoke` receipts are authority here. Superseded parser-failed final/smoke publications are excluded.
- F-rich is the only formal arm; compact transport remains unauthorized.
- The corrected broadband gamma component already contains the annihilation bump. No extra mono-511 is present or permitted in this batch.
- The package supports corrected-keV transport integrity, active-veto/Compton/statistical executability, position-aware activation methods and partial screening.
- It does **not** establish a complete atmospheric-line component, full delayed decay transport/response, final structure ranking, mission sensitivity, geometry promotion or a complete M05 rate closure.

## Recommended next steps

1. Let the frozen campaign continue without changing seeds, sources, geometry, physics, cuts or native thresholds.
2. Apply the exact O8 active-block whitelist in formal post-processing and retain 50 keV as the paper threshold with 70/80 keV offline diagnostics.
3. Build position-preserving delayed sources from rich-SIM `CC IP RP`, retaining isotope state, ancestry/provenance and per-family TT normalization.
4. Complete delayed transport, detector response, active veto, Compton/FoV selection and uncertainty intervals before publishing physical rates or rankings.
5. Close the independent atmospheric-line/continuum flux model separately; do not append mono-511 to this broadband-total batch.

## Files

- `review_summary.json`: machine-readable verdict, method and boundaries.
- `cell_coverage.csv`: exact 32-cell job/event/TT/RP/resource table.
- `prompt_observables.csv`: family-level prompt counts and rates.
- `buildup_family_coverage.csv`: family TT/RP/zero-RP coverage.
- `buildup_volume_isotope_state.csv`: position-aware physical production tuples.
- `buildup_structure_contributions.csv`: structure-level activation production screening.
- `artifact_audit.csv`: 400 artifact hashes and sizes.
- `authority_hashes.json`: recovery0001 authority chain.
- `MANIFEST.json`: write-once publication member hashes.
"""


def build_payloads(
    authority_hashes: dict[str, str], cell_rows: list[dict[str, Any]], artifact_rows: list[dict[str, Any]],
    totals: dict[str, Any], scan: dict[str, Any], created_at: str,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    summary = {
        "schema_version": 1,
        "created_at": created_at,
        "verdict": "ANALYSIS_READY_CONTINUE",
        "status": "PASS__CORRECTED_KEV_SMOKE__ANALYSIS_PIPELINE_COMPATIBLE__PARTIAL_SCREENING_ONLY",
        "authority_boundary": {
            "included": "recovery0001-selected stage00_mergeable_smoke F-rich receipts and their artifacts only",
            "excluded": [
                "superseded parser-failed final/smoke publications", "compact arm", "later/in-progress campaign stages",
                "historical factor-1000 rates and geometry rankings",
            ],
            "campaign_action": "none; read-only review; parent session controls continuation",
        },
        "authority_hashes": authority_hashes,
        "transport_integrity": totals,
        "raw_scan": scan["raw_scan"],
        "prompt_method": {
            "TES_pixel_regex": TES_RE.pattern, "per_event_pixel_operation": "sum raw CC HIT edep by pixel UID",
            "position_operation": "edep-weighted x/y/z; per-step t retained", "response_seed": M05_RESPONSE_SEED,
            "response_rng_scope": "independent numpy default_rng per geometry; fixed family/shard/event/pixel order",
            "response_FWHM_keV": M05_RESPONSE_FWHM_KEV, "response_sigma_keV": M05_RESPONSE_SIGMA_KEV,
            "measured_pixel_discard_below_keV": MEASURED_PIXEL_THRESHOLD_KEV,
            "W2_keV_half_open": list(W2), "broad_keV_half_open": list(BROAD),
            "offline_active_veto_thresholds_keV": list(VETO_THRESHOLDS_KEV),
            "native_detector_thresholds_changed": False,
            "rate_estimator": "count_family / sum(TT_family), then sum family rates; no family pooling",
        },
        "prompt": scan["prompt_geometry"],
        "active_block_coverage": scan["active_block_coverage"],
        "buildup_method": {
            "position_authority": "rich SIM CC IP RP physical volume + x/y/z + production time",
            "DAT_role": "logical-volume/isotope-state/TT aggregate; not sufficient alone for spatial source placement",
            "rate_estimator": "sum(RP instances) / sum(TT) within geometry/mode/family/volume/isotope-state",
            "zero_RP_TT_retained": True,
            "RP_definition_note": "authority RP_record_count=1003 DAT RP rows; RP_sum=1330 production instances",
            "known_mapping_note": "three physical TP pixel names map to DAT logical TES layers; one 4e-6 keV excitation is rounded to 0.00 in DAT display",
        },
        "buildup": scan["buildup_geometry"],
        "reader_compatibility": scan["reader_compatibility"],
        "paper_executability": {
            "offline_active_veto": True, "Compton_topology_veto": True,
            "family_separated_prompt_statistics": True, "zero_RP_safe_activation_statistics": True,
            "structure_level_prompt_screening": True, "position_resolved_activation_source_construction": True,
            "final_physics_conclusions_ready": False,
        },
        "claim_boundary": {
            "supported": [
                "corrected-keV smoke transport integrity", "rich-SIM reader compatibility",
                "TES pixel aggregation and measured-hit threshold", "W2 and 50/70/80 keV offline veto flags",
                "Compton/topology input-field availability", "family-separated small-sample prompt screening",
                "BUILDUP TT/RP/zero-RP and position/isotope-state coverage", "structure-level activation production screening",
            ],
            "not_supported": [
                "complete atmospheric-line/four-component background", "complete delayed response",
                "final structure ranking", "mission sensitivity", "geometry promotion", "complete M05 rate closure",
            ],
        },
    }

    payloads: dict[str, bytes] = {}
    payloads["review_summary.json"] = json_payload(summary)
    payloads["authority_hashes.json"] = json_payload(
        {
            "schema_version": 1, "created_at": created_at, "hash_algorithm": "SHA-256",
            "authority": [
                {"name": name, "path": rel(AUTHORITY_PATHS[name]), "sha256": authority_hashes[name]}
                for name in AUTHORITY_PATHS
            ],
            "boundary": summary["authority_boundary"],
        }
    )
    payloads["cell_coverage.csv"] = csv_payload(
        cell_rows,
        ["geometry", "mode", "family", "jobs", "events", "TT_s", "RP_record_count", "RP_sum",
         "artifact_bytes", "RSS_max_bytes", "wall_sum_s", "beam_on_cpu_sum_s", "zero_RP_jobs"],
    )
    prompt_fields = [
        "geometry", "family", "events", "TT_s", "tes_positive_events", "pixel_readouts", "max_pixel_multiplicity",
        "raw_broad_count", "raw_broad_rate_cps", "measured_broad_count", "measured_broad_rate_cps",
        "raw_W2_count", "raw_W2_rate_cps", "measured_W2_count", "measured_W2_rate_cps",
        "W2_pass_50_count", "W2_pass_50_rate_cps", "W2_pass_70_count", "W2_pass_70_rate_cps",
        "W2_pass_80_count", "W2_pass_80_rate_cps",
    ]
    payloads["prompt_observables.csv"] = csv_payload(scan["prompt_rows"], prompt_fields)
    payloads["buildup_family_coverage.csv"] = csv_payload(
        scan["buildup_family_rows"],
        ["geometry", "family", "jobs", "events", "TT_s", "DAT_RP_record_count", "DAT_RP_sum",
         "SIM_RP_instances", "zero_RP_jobs", "zero_RP_cell", "physical_volume_count",
         "physical_volume_isotope_state_tuple_count", "production_rate_per_TT_s"],
    )
    payloads["buildup_volume_isotope_state.csv"] = csv_payload(
        scan["buildup_tuple_rows"],
        ["geometry", "family", "physical_volume", "isotope_id", "excitation_keV", "production_instances",
         "production_rate_per_TT_s", "x_min_cm", "x_max_cm", "y_min_cm", "y_max_cm", "z_min_cm", "z_max_cm",
         "production_time_min_s", "production_time_max_s"],
    )
    payloads["buildup_structure_contributions.csv"] = csv_payload(
        scan["buildup_structure_rows"],
        ["geometry", "family", "physical_volume", "production_instances", "production_rate_per_TT_s",
         "isotope_state_count", "x_min_cm", "x_max_cm", "y_min_cm", "y_max_cm", "z_min_cm", "z_max_cm"],
    )
    payloads["artifact_audit.csv"] = csv_payload(
        artifact_rows,
        ["job_id", "geometry", "mode", "family", "shard_ordinal", "kind", "path", "bytes", "sha256", "receipt_match"],
    )
    payloads["REPORT.md"] = build_report_markdown(summary).encode("utf-8")
    return payloads, summary


def publish_write_once(payloads: dict[str, bytes], authority_hashes: dict[str, str], created_at: str) -> dict[str, Any]:
    if ANALYSIS_OUT.exists():
        raise RuntimeError(f"write-once output already exists: {ANALYSIS_OUT}")
    ANALYSIS_OUT.mkdir(parents=False, exist_ok=False)
    staged: list[tuple[Path, Path, bytes]] = []
    for name, payload in payloads.items():
        target = ANALYSIS_OUT / name
        partial = ANALYSIS_OUT / f"{name}.partial"
        if target.exists() or partial.exists():
            raise RuntimeError(f"write-once collision: {target}")
        with partial.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if sha256_file(partial) != sha256_bytes(payload) or partial.stat().st_size != len(payload):
            raise RuntimeError(f"staged verification failed: {partial}")
        staged.append((partial, target, payload))
    for partial, target, _payload in staged:
        if target.exists():
            raise RuntimeError(f"target appeared during publish: {target}")
        partial.rename(target)

    members = [
        {"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)}
        for name, payload in sorted(payloads.items())
    ]
    manifest = {
        "schema_version": 1, "created_at": created_at, "status": "PASS__WRITE_ONCE_ATOMIC_PUBLICATION",
        "verdict": "ANALYSIS_READY_CONTINUE", "canonical_directory": rel(ANALYSIS_OUT),
        "publication_policy": "all members staged as .partial, verified, then atomically renamed; MANIFEST published last",
        "analysis_code": {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "authority_hashes": authority_hashes, "members": members,
    }
    manifest_payload = json_payload(manifest)
    manifest_partial = ANALYSIS_OUT / "MANIFEST.json.partial"
    manifest_target = ANALYSIS_OUT / "MANIFEST.json"
    with manifest_partial.open("xb") as handle:
        handle.write(manifest_payload)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256_file(manifest_partial) != sha256_bytes(manifest_payload):
        raise RuntimeError("manifest staged verification failed")
    manifest_partial.rename(manifest_target)
    directory_fd = os.open(ANALYSIS_OUT, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {**manifest, "manifest_sha256": sha256_file(manifest_target), "manifest_bytes": manifest_target.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="run the full analysis and all assertions without writing")
    args = parser.parse_args()
    if ANALYSIS_OUT.exists():
        raise RuntimeError(f"canonical write-once output already exists: {ANALYSIS_OUT}")
    _global, validation, ledger, authority_hashes = audit_authority()
    receipts, cell_rows, artifact_rows, totals = audit_receipts(ledger, validation)
    scan = scan_rich_sim(receipts)
    created_at = datetime.now(timezone.utc).isoformat()
    payloads, summary = build_payloads(authority_hashes, cell_rows, artifact_rows, totals, scan, created_at)
    check_result = {
        "verdict": summary["verdict"], "receipts": totals["receipts"], "events": totals["events"],
        "cells": totals["cells"], "prompt_CC_HIT": scan["raw_scan"]["prompt_CC_HIT"],
        "buildup_SIM_RP_instances": scan["raw_scan"]["buildup_SIM_RP_instances"],
        "payloads": {name: {"bytes": len(payload), "sha256": sha256_bytes(payload)} for name, payload in payloads.items()},
    }
    if args.check_only:
        print(json.dumps({"status": "PASS__CHECK_ONLY__NO_WRITES", **check_result}, indent=2, sort_keys=True))
        return 0
    manifest = publish_write_once(payloads, authority_hashes, created_at)
    print(json.dumps({"status": "PASS__PUBLISHED", **check_result, "manifest": manifest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
