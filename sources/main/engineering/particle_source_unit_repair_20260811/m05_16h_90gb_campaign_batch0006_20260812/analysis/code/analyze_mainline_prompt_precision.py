#!/usr/bin/env python3
"""Read-only sparse prompt scan for batch0006 statistical-planning evidence.

The transport artifacts and authorities are never modified.  The only output is
published write-once through a sibling ``.partial`` file followed by os.replace.
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
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1"
FINAL_VALIDATION = RUN_ROOT / "recovery0008_current_attempt_disk_admission/final_validation.json"
DEFAULT_OUTPUT = RUN_ROOT / "analysis_m05_smoke_closure_reviewer01/mainline_prompt_precision_v1.json"

GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "neutron", "proton")
TES_RE = re.compile(r"TP_L\d+_\d+")
M05_SEED = 26071301
SIGMA_KEV = 0.420 / 2.354820045
PIXEL_THRESHOLD_KEV = 0.3
BROAD = (480.0, 550.0)
W2 = (510.58, 511.42)
VETO_THRESHOLDS = (50.0, 70.0, 80.0)
ACTIVE_BLOCKS = {
    "Mass_model_511": frozenset(),  # Mass is handled by the CsI_ prefix below.
    "S3d_O8": frozenset(
        {
            "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
            "BGO_S3D_O8_FullWrap_BottomCap_30mm",
            "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
            "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
            "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
            "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
        }
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_kv(tokens: list[str]) -> dict[str, str]:
    return {key: value for token in tokens if "=" in token for key, value in [token.split("=", 1)]}


def is_active(geometry: str, volume: str) -> bool:
    if geometry == "Mass_model_511":
        return volume.startswith("CsI_")
    return volume in ACTIVE_BLOCKS[geometry]


def receipt_sort_key(receipt: dict[str, Any]) -> tuple[int, int, str, int]:
    job = receipt["job"]
    return (
        GEOMETRIES.index(job["geometry"]),
        FAMILIES.index(job["family"]),
        str(job["stage"]),
        int(job["shard_ordinal"]),
    )


def percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    return float(np.quantile(np.asarray(values, dtype=float), q, method="linear"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--response-replicas", type=int, default=64)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"write-once output already exists: {output}")
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"partial output already exists: {partial}")

    final = json.loads(FINAL_VALIDATION.read_text(encoding="utf-8"))
    if final["status"] != "PASS__REPLANNED_MAINLINE_EVENT_TARGET_COMPLETE":
        raise RuntimeError(f"unexpected final authority status: {final['status']}")

    receipts: list[dict[str, Any]] = []
    for selected in final["selected_receipts"]:
        receipt = json.loads((ROOT / selected["path"]).read_text(encoding="utf-8"))
        if receipt["status"] != "PASS" or receipt["job"]["mode"] != "instant":
            continue
        receipt["_path"] = selected["path"]
        receipts.append(receipt)
    receipts.sort(key=receipt_sort_key)

    sparse: dict[str, dict[str, list[dict[str, Any]]]] = {
        geometry: {family: [] for family in FAMILIES} for geometry in GEOMETRIES
    }
    cells: dict[tuple[str, str], dict[str, Any]] = {}
    active_seen = {geometry: set() for geometry in GEOMETRIES}
    total_hits = 0
    total_tes_steps = 0
    total_events = 0
    started = time.monotonic()

    for file_index, receipt in enumerate(receipts, start=1):
        job = receipt["job"]
        geometry, family = job["geometry"], job["family"]
        sim_path = ROOT / receipt["attempt_dir"] / receipt["artifacts"]["sim"]["name"]
        key = (geometry, family)
        cell = cells.setdefault(
            key,
            {
                "geometry": geometry,
                "family": family,
                "jobs": 0,
                "events": 0,
                "TT_s": 0.0,
                "tes_positive_events": 0,
                "pixel_readouts": 0,
                "TES_steps": 0,
                "CC_HIT": 0,
                "raw_broad_count": 0,
                "raw_W2_count": 0,
                "raw_W2_pass_50_count": 0,
                "raw_W2_pass_70_count": 0,
                "raw_W2_pass_80_count": 0,
            },
        )
        cell["jobs"] += 1
        cell["events"] += int(job["events"])
        cell["TT_s"] = math.fsum((cell["TT_s"], float(receipt["isotope_dat"]["TT_s"])))

        current_id: int | None = None
        pixels: defaultdict[str, float] = defaultdict(float)
        active_total = 0.0
        file_events = 0

        def flush() -> None:
            nonlocal current_id, pixels, active_total, file_events, total_events
            if current_id is None:
                return
            file_events += 1
            total_events += 1
            if pixels:
                energies = tuple(pixels[name] for name in sorted(pixels))
                raw_total = math.fsum(energies)
                record = {
                    "job_id": job["job_id"],
                    "event_id": current_id,
                    "pixel_energies_keV": energies,
                    "active_total_keV": active_total,
                }
                sparse[geometry][family].append(record)
                cell["tes_positive_events"] += 1
                cell["pixel_readouts"] += len(energies)
                cell["raw_broad_count"] += int(BROAD[0] <= raw_total < BROAD[1])
                if W2[0] <= raw_total < W2[1]:
                    cell["raw_W2_count"] += 1
                    for threshold in VETO_THRESHOLDS:
                        cell[f"raw_W2_pass_{int(threshold)}_count"] += int(active_total < threshold)
            current_id = None
            pixels = defaultdict(float)
            active_total = 0.0

        with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
            for raw in handle:
                line = raw.strip()
                if line == "SE":
                    flush()
                    continue
                if line.startswith("ID "):
                    fields = line.split()
                    current_id = int(fields[1])
                    continue
                if not line.startswith("CC HIT "):
                    continue
                fields = line.split()
                volume = fields[2]
                kv = parse_kv(fields[3:])
                if "edep_keV" not in kv:
                    raise RuntimeError(f"missing edep_keV: {job['job_id']}")
                edep = float(kv["edep_keV"])
                cell["CC_HIT"] += 1
                total_hits += 1
                if TES_RE.fullmatch(volume):
                    pixels[volume] += edep
                    cell["TES_steps"] += 1
                    total_tes_steps += 1
                elif is_active(geometry, volume):
                    active_total += edep
                    active_seen[geometry].add(volume)
        flush()
        if file_events != int(job["events"]):
            raise RuntimeError(f"event framing mismatch {job['job_id']}: {file_events} != {job['events']}")
        if file_index % 10 == 0 or file_index == len(receipts):
            elapsed = time.monotonic() - started
            print(
                f"scanned {file_index}/{len(receipts)} files, {total_events} events, "
                f"{total_hits} hits, {elapsed:.1f}s",
                file=sys.stderr,
                flush=True,
            )

    response_rows: list[dict[str, Any]] = []
    seeds = [M05_SEED + index for index in range(args.response_replicas)]
    response_fields = (
        "measured_broad_count",
        "measured_W2_count",
        "measured_W2_pass_50_count",
        "measured_W2_pass_70_count",
        "measured_W2_pass_80_count",
    )
    distributions: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    for seed in seeds:
        for geometry in GEOMETRIES:
            rng = np.random.default_rng(seed)
            counts_by_family = {family: Counter() for family in FAMILIES}
            for family in FAMILIES:
                for event in sparse[geometry][family]:
                    measured = math.fsum(
                        value
                        for value in (
                            float(rng.normal(energy, SIGMA_KEV))
                            for energy in event["pixel_energies_keV"]
                        )
                        if value >= PIXEL_THRESHOLD_KEV
                    )
                    counts = counts_by_family[family]
                    counts["measured_broad_count"] += int(BROAD[0] <= measured < BROAD[1])
                    if W2[0] <= measured < W2[1]:
                        counts["measured_W2_count"] += 1
                        for threshold in VETO_THRESHOLDS:
                            counts[f"measured_W2_pass_{int(threshold)}_count"] += int(
                                event["active_total_keV"] < threshold
                            )
            for family in FAMILIES:
                for field in response_fields:
                    distributions[(geometry, family, field)].append(int(counts_by_family[family][field]))

    for geometry in GEOMETRIES:
        for family in FAMILIES:
            base = dict(cells[(geometry, family)])
            tt = float(base["TT_s"])
            for count_field in (
                "raw_broad_count",
                "raw_W2_count",
                "raw_W2_pass_50_count",
                "raw_W2_pass_70_count",
                "raw_W2_pass_80_count",
            ):
                count = int(base[count_field])
                prefix = count_field.removesuffix("_count")
                base[prefix + "_rate_cps"] = count / tt
                base[prefix + "_poisson_rse"] = None if count == 0 else 1.0 / math.sqrt(count)
                base[prefix + "_zero_count_95_upper_rate_cps"] = 2.995732273553991 / tt if count == 0 else None
            for field in response_fields:
                values = distributions[(geometry, family, field)]
                prefix = field.removesuffix("_count")
                base[prefix + "_m05_seed_count"] = values[0]
                base[prefix + "_replica_mean_count"] = statistics.fmean(values)
                base[prefix + "_replica_sd_count"] = statistics.stdev(values) if len(values) > 1 else 0.0
                base[prefix + "_replica_min_count"] = min(values)
                base[prefix + "_replica_p05_count"] = percentile(values, 0.05)
                base[prefix + "_replica_p95_count"] = percentile(values, 0.95)
                base[prefix + "_replica_max_count"] = max(values)
                base[prefix + "_m05_seed_rate_cps"] = values[0] / tt
                base[prefix + "_m05_seed_poisson_rse"] = None if values[0] == 0 else 1.0 / math.sqrt(values[0])
                base[prefix + "_m05_seed_zero_count_95_upper_rate_cps"] = (
                    2.995732273553991 / tt if values[0] == 0 else None
                )
            response_rows.append(base)

    expected_active = {
        "Mass_model_511": None,
        "S3d_O8": sorted(ACTIVE_BLOCKS["S3d_O8"]),
    }
    observed_active = {geometry: sorted(values) for geometry, values in active_seen.items()}
    if observed_active["S3d_O8"] != expected_active["S3d_O8"]:
        raise RuntimeError(f"O8 exact active-block coverage mismatch: {observed_active['S3d_O8']}")

    payload = {
        "schema_version": 1,
        "status": "PASS__READ_ONLY_MAINLINE_PROMPT_PRECISION_SCAN",
        "authority": {
            "path": str(FINAL_VALIDATION.relative_to(ROOT)),
            "sha256": sha256_file(FINAL_VALIDATION),
            "status": final["status"],
            "selected_receipts": len(final["selected_receipts"]),
            "validated_events_all_modes": final["validated_events"],
        },
        "method": {
            "scope": "instant mode only; all canonical recovery0008 PASS receipts",
            "TES_pixel_rule": r"^TP_L\d+_\d+$, sum deposits within event and pixel",
            "response_sigma_keV": SIGMA_KEV,
            "response_seed_first": M05_SEED,
            "response_seed_count": len(seeds),
            "measured_pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "broad_window_keV": list(BROAD),
            "W2_half_open_keV": list(W2),
            "veto_thresholds_keV": list(VETO_THRESHOLDS),
            "Mass_active_rule": "volume.startswith('CsI_')",
            "S3d_O8_exact_active_whitelist": sorted(ACTIVE_BLOCKS["S3d_O8"]),
            "event_order": "geometry, family, stage string, shard ordinal, SIM event ID, pixel name",
            "statistics_note": "Poisson RSE is 1/sqrt(observed candidate count); zero-count 95% upper mean is 2.995732.",
        },
        "scan": {
            "prompt_receipts": len(receipts),
            "prompt_events": total_events,
            "CC_HIT": total_hits,
            "TES_steps": total_tes_steps,
            "TES_positive_events": sum(len(sparse[g][f]) for g in GEOMETRIES for f in FAMILIES),
            "active_observed": observed_active,
            "elapsed_s": time.monotonic() - started,
        },
        "cells": response_rows,
        "authority_boundary": (
            "Supports corrected-keV prompt analysis-pipeline compatibility and statistical planning only; "
            "does not include Compton-topology selection, delayed-decay transport, mission sensitivity, "
            "or geometry promotion."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with partial.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, output)
    print(json.dumps({"output": str(output), "bytes": len(encoded), "sha256": sha256_file(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
