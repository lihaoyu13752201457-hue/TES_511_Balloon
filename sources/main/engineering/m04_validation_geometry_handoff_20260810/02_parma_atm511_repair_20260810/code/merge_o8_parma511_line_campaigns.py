#!/usr/bin/env python3
"""Merge validated O8 PARMA-511 campaign aggregates without reading raw SIM.

Only ``o8-parma511-line-campaign-aggregate-v1`` receipts and their hash-closed
compact CSV/JSON/response artifacts are accepted.  Detector response is rerun
by importing the frozen line-only harness and calling its own
``response_analysis`` implementation.  This module has no Cosima or transport
entry point and never resolves a raw-SIM path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
ROOT = SCRIPT.parents[4]
HARNESS_PATH = SCRIPT.with_name("o8_parma511_line_transport_harness.py")

INPUT_SCHEMA = "o8-parma511-line-campaign-aggregate-v1"
OUTPUT_SCHEMA = "o8-parma511-line-supercampaign-aggregate-v1"
SELFTEST_SCHEMA = "o8-parma511-line-supercampaign-self-test-v1"
RESPONSE_REPLICAS = 64
SUPER_EVENT_ID_STRIDE = 1_000_000_000_000_000

SMOKE_RECEIPT = (
    PACKAGE
    / "transport/campaigns/o8_parma511_line_smoke_1k/aggregate"
    / "wave_0000_0000_a7ad454c9438/campaign_aggregate_receipt.json"
)
class MergeError(RuntimeError):
    """A compact-input, provenance, identity, or response gate failed."""


def load_harness() -> Any:
    if not HARNESS_PATH.is_file():
        raise MergeError(f"line-only harness is missing: {HARNESS_PATH}")
    spec = importlib.util.spec_from_file_location(
        "o8_parma511_line_transport_harness_for_supermerge", HARNESS_PATH
    )
    if spec is None or spec.loader is None:
        raise MergeError(f"cannot import line-only harness: {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H = load_harness()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MergeError(message)


def close(left: float, right: float, *, atol: float = 1.0e-15) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=atol)


def root_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def is_raw_like(path: Path) -> bool:
    lowered = [part.lower() for part in path.parts]
    name = path.name.lower()
    return (
        "raw" in lowered
        or "logs" in lowered
        or "source_cards" in lowered
        or name.endswith(".sim")
        or name.endswith(".sim.gz")
        or name.endswith(".log")
        or name.endswith(".log.gz")
        or name.endswith(".source")
    )


def compact_path(value: str, *, allowed_root: Path, role: str) -> Path:
    path = root_path(value).resolve()
    require(not is_raw_like(path), f"{role} attempts a forbidden raw/log/source read: {path}")
    require(path.is_relative_to(allowed_root.resolve()), f"{role} escapes compact root: {path}")
    require(path.is_file(), f"{role} is missing: {path}")
    require(path.suffix.lower() in {".json", ".csv"}, f"{role} is not compact JSON/CSV: {path}")
    return path


def hash_record(path: Path) -> dict[str, Any]:
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def verify_record(path: Path, record: dict[str, Any], role: str) -> None:
    require(sha256(path) == record.get("sha256"), f"{role} SHA-256 mismatch: {path}")
    if "bytes" in record:
        require(path.stat().st_size == int(record["bytes"]), f"{role} byte-count mismatch: {path}")


def read_csv_rows(path: Path, expected_fields: list[str], role: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_fields, f"{role} header changed: {reader.fieldnames}")
        return list(reader)


def expected_response_parameters() -> dict[str, Any]:
    return {
        "fwhm_keV": H.FWHM_KEV,
        "sigma_keV": H.SIGMA_KEV,
        "tes_threshold_keV": H.TES_THRESHOLD_KEV,
        "active_threshold_keV": H.ACTIVE_THRESHOLD_KEV,
        "primary_seed": H.PRIMARY_ATM_RESPONSE_SEED,
        "seed_stride": H.RESPONSE_SEED_STRIDE,
        "replicas": RESPONSE_REPLICAS,
        "step05_sha256": H.EXPECTED_SHA256[H.STEP05_IMPLEMENTATION],
        "step09_summary_sha256": H.EXPECTED_SHA256[H.STEP09_SUMMARY],
        "active_veto_predicate_blocker": H.ACTIVE_VETO_NAMING_BLOCKER,
        "active_shield_named_passive_kapton_wrappers_in_o8": list(
            H.KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS
        ),
    }


def validate_response_parameters(response: dict[str, Any], role: str) -> dict[str, Any]:
    require(response.get("schema") == H.RESPONSE_SCHEMA, f"{role} response schema changed")
    require(response.get("scope") == "atmospheric annihilation mono line only", f"{role} scope changed")
    require(response.get("proposal") == "parma80", f"{role} proposal is not parma80")
    actual = response.get("detector_response", {})
    expected = expected_response_parameters()
    for key, value in expected.items():
        if isinstance(value, float):
            require(close(actual.get(key), value), f"{role} detector-response {key} changed")
        else:
            require(actual.get(key) == value, f"{role} detector-response {key} changed")
    require(
        actual.get("step05_implementation") == rel(H.STEP05_IMPLEMENTATION),
        f"{role} Step05 path changed",
    )
    require(
        actual.get("step09_summary") == rel(H.STEP09_SUMMARY),
        f"{role} Step09 path changed",
    )
    topology = str(actual.get("topology_contract", ""))
    require("broad 480<=E<550" in topology, f"{role} broad topology contract changed")
    require("active<50" in topology, f"{role} active threshold contract changed")
    require("side_keep_from_hits" in topology, f"{role} frozen topology implementation absent")
    return actual


def validate_response_artifacts(
    response_path: Path, response: dict[str, Any]
) -> tuple[dict[str, Path], list[int]]:
    expected_names = {
        "response_seed_replicas.csv",
        "primary_event_response.csv",
        "angular_response_coefficients_20bins.csv",
        "angular_response_coefficients_40bins.csv",
        "angular_response_coefficients_80bins.csv",
    }
    found: dict[str, Path] = {}
    for value, record in response.get("artifacts", {}).items():
        path = compact_path(value, allowed_root=response_path.parent, role="response artifact")
        require(path.name not in found, f"duplicate response artifact name: {path.name}")
        verify_record(path, record, "response artifact")
        found[path.name] = path
    require(set(found) == expected_names, f"response artifact set changed: {sorted(found)}")
    seed_fields = [
        "replica_index",
        "response_seed",
        "w2_raw_events",
        "w2_active_veto_pass_events",
        "w2_frozen_step05_pass_events",
        "rate_20bin_cps",
        "mc_sigma_20bin_cps",
        "ess_20bin",
        "rate_40bin_cps",
        "mc_sigma_40bin_cps",
        "ess_40bin",
        "rate_80bin_cps",
        "mc_sigma_80bin_cps",
        "ess_80bin",
        "relative_20_minus_80",
        "relative_40_minus_80",
    ]
    rows = read_csv_rows(found["response_seed_replicas.csv"], seed_fields, "response seeds")
    require(len(rows) == RESPONSE_REPLICAS, f"response seed count is {len(rows)}, not 64")
    expected_seeds = [
        H.PRIMARY_ATM_RESPONSE_SEED + index * H.RESPONSE_SEED_STRIDE
        for index in range(RESPONSE_REPLICAS)
    ]
    require([int(row["replica_index"]) for row in rows] == list(range(RESPONSE_REPLICAS)), "response replica indices changed")
    seeds = [int(row["response_seed"]) for row in rows]
    require(seeds == expected_seeds, "64 detector-response seeds changed")
    recomputed_gate = H.detector_rate_gate(
        response["primary_420eV"]["paired_reweight"]
    )
    require(
        recomputed_gate == response.get("primary_detector_rate_gate"),
        "stored detector-rate gate does not reproduce with the current harness",
    )
    return found, seeds


def artifact_paths(
    *, provenance_path: Path, provenance: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Path]:
    expected_names = {
        "tes_events.csv",
        "tes_pixel_hits.csv",
        "event_lineage.csv",
        "angular_counts.json",
    }
    receipt_artifacts = receipt["merged_compact"].get("artifacts", {})
    provenance_artifacts = provenance.get("artifacts", {})
    require(receipt_artifacts == provenance_artifacts, "receipt/provenance compact artifact maps differ")
    found: dict[str, Path] = {}
    for value, record in provenance_artifacts.items():
        path = compact_path(value, allowed_root=provenance_path.parent, role="merged compact artifact")
        require(path.name not in found, f"duplicate merged artifact name: {path.name}")
        verify_record(path, record, "merged compact artifact")
        found[path.name] = path
    require(set(found) == expected_names, f"merged compact artifact set changed: {sorted(found)}")
    return found


def validate_campaign_receipt(receipt_path: Path) -> dict[str, Any]:
    receipt_path = receipt_path.resolve()
    require(receipt_path.is_file(), f"aggregate receipt missing: {receipt_path}")
    require(receipt_path.suffix.lower() == ".json", f"aggregate receipt is not JSON: {receipt_path}")
    require(receipt_path.is_relative_to(PACKAGE.resolve()), "aggregate receipt is outside the isolated WP2 package")
    require(not is_raw_like(receipt_path), "aggregate receipt path is raw-like")
    receipt_hash = sha256(receipt_path)
    receipt = read_json(receipt_path)
    require(receipt.get("schema") == INPUT_SCHEMA, f"unsupported input schema: {receipt_path}")
    require(not receipt.get("allow_partial", False), "partial campaign aggregate is not accepted")
    require(not receipt.get("incomplete_batch_indices", []), "campaign aggregate has incomplete batches")
    require(receipt["merged_compact"].get("raw_sim_files_read") is False, "input aggregate reports raw read")

    aggregate_root = receipt_path.parent.resolve()
    provenance_path = compact_path(
        receipt["merged_compact"]["provenance"],
        allowed_root=aggregate_root,
        role="merged provenance",
    )
    require(
        sha256(provenance_path) == receipt["merged_compact"]["provenance_sha256"],
        "merged provenance hash mismatch",
    )
    provenance = read_json(provenance_path)
    require(provenance.get("schema") == H.PARSE_SCHEMA, "merged provenance schema changed")
    require(provenance.get("status") == "PASS_STREAM_PARSE_COMPLETE", "merged provenance is not PASS")
    require(provenance.get("proposal") == "parma80_physical_flux", "input proposal is not physical parma80")
    require(close(provenance.get("expected_energy_keV"), H.PARMA_LINE_ENERGY_KEV), "input is not exactly the 510.99895-keV line")
    require("atmospheric annihilation mono line only" in str(provenance.get("scope", "")), "input scope is not atmospheric mono-line only")
    require(provenance.get("raw_sim_files_read_during_merge") is False, "input provenance reports raw read")
    require(provenance.get("parser", {}).get("sha256") == sha256(HARNESS_PATH), "input was produced by a different harness revision")
    require(provenance.get("geometry_authority") == str(H.O8_SETUP), "input SIM geometry authority changed")
    require(all(bool(value) for value in provenance.get("checks", {}).values()), "input compact provenance contains failed checks")

    paths = artifact_paths(
        provenance_path=provenance_path, provenance=provenance, receipt=receipt
    )
    events = read_csv_rows(paths["tes_events.csv"], list(H.EVENT_FIELDS), "TES event catalog")
    pixels = read_csv_rows(paths["tes_pixel_hits.csv"], list(H.PIXEL_FIELDS), "TES pixel catalog")
    lineage_fields = ["global_event_id", "batch_index", "run_name", "local_event_id"]
    lineage = read_csv_rows(paths["event_lineage.csv"], lineage_fields, "event lineage")
    angular = read_json(paths["angular_counts.json"])
    require(angular.get("schema") == H.PARSE_SCHEMA, "angular-count schema changed")

    counts = {key: int(value) for key, value in provenance["counts"].items()}
    footer = provenance["sim_footer"]
    ts = int(footer["TS"])
    te_s = float(footer["TE_s"])
    require(ts > 0 and te_s > 0.0, "input TS/TE is non-positive")
    require(len(events) == counts["tes_events"], "TES event count does not close")
    require(len(pixels) == counts["tes_pixel_hits"], "TES pixel count does not close")
    require(len(lineage) == len(events), "event lineage count does not close")
    require(int(receipt["merged_compact"]["events"]) == len(events), "receipt TES count differs")
    require(int(receipt["merged_compact"]["pixel_hits"]) == len(pixels), "receipt pixel count differs")
    require(int(receipt["merged_compact"]["TS"]) == ts, "receipt TS differs")
    require(close(receipt["merged_compact"]["TE_s"], te_s), "receipt TE differs")

    angular_counts: dict[int, list[int]] = {}
    for bins in (20, 40, 80):
        values = [int(value) for value in angular["counts"][str(bins)]]
        require(len(values) == bins, f"input {bins}-bin angular length changed")
        require(sum(values) == ts, f"input {bins}-bin angular counts do not close")
        angular_counts[bins] = values
    require(int(angular.get("init_records")) == ts, "angular INIT total differs from TS")

    event_ids: set[int] = set()
    for row in events:
        event_id = int(row["event_id"])
        require(event_id not in event_ids, f"duplicate input event ID: {event_id}")
        event_ids.add(event_id)
        require(close(row["init_energy_keV"], H.PARMA_LINE_ENERGY_KEV, atol=0.001), "TES event is not from the mono line")
        direction = float(row["dir_z"])
        for bins in (20, 40, 80):
            require(int(row[f"bin{bins}"]) == H.angular_bin_from_init_dir_z(direction, bins), f"TES event {event_id} has wrong bin{bins}")
    pixel_event_ids = {int(row["event_id"]) for row in pixels}
    require(pixel_event_ids.issubset(event_ids), "pixel catalog references an unknown event")

    included = [int(value) for value in receipt.get("included_batch_indices", [])]
    batch_receipts = receipt.get("batch_receipts", [])
    require(len(included) == len(set(included)), "duplicate included batch index")
    require(sorted(included) == sorted(int(row["batch_index"]) for row in batch_receipts), "included batch list differs from batch receipts")
    batch_by_index: dict[int, dict[str, Any]] = {}
    batch_counts: Counter[str] = Counter()
    batch_ts = 0
    batch_te = 0.0
    batch_angular = {bins: [0] * bins for bins in (20, 40, 80)}
    local_transport_seeds: set[int] = set()
    local_run_names: set[str] = set()
    for batch in batch_receipts:
        index = int(batch["batch_index"])
        require(index not in batch_by_index, f"duplicate batch receipt {index}")
        batch_by_index[index] = batch
        require(all(bool(value) for value in batch.get("checks", {}).values()), f"batch {index} contains a failed closure check")
        for key in ("o8_setup_hash_matches", "o8_geo_hash_matches", "o8_det_hash_matches", "energy_matches"):
            require(batch["checks"].get(key) is True, f"batch {index} lacks {key}")
        seed = int(batch["transport_seed"])
        run_name = str(batch["run_name"])
        require(seed not in local_transport_seeds, f"duplicate transport seed within campaign: {seed}")
        require(run_name not in local_run_names, f"duplicate run name within campaign: {run_name}")
        local_transport_seeds.add(seed)
        local_run_names.add(run_name)
        require(int(batch["sim_header"]["seed"]) == seed, f"batch {index} header seed differs")
        require(batch["sim_header"]["geometry"] == str(H.O8_SETUP), f"batch {index} geometry differs")
        require(batch["sim_header"]["spectral_type_first"] == "SpectralType Mono 510.999", f"batch {index} header is not the line")
        batch_ts += int(batch["sim_footer"]["TS"])
        batch_te += float(batch["sim_footer"]["TE_s"])
        batch_counts.update({key: int(value) for key, value in batch["counts"].items()})
        for bins in (20, 40, 80):
            values = [int(value) for value in batch["angular_counts"][str(bins)]]
            batch_angular[bins] = [left + right for left, right in zip(batch_angular[bins], values)]
    require(batch_ts == ts, "batch TS does not close to merged TS")
    require(close(batch_te, te_s, atol=1.0e-12), "batch TE does not close to merged TE")
    require(dict(batch_counts) == counts, "batch counts do not close to merged counts")
    require(batch_angular == angular_counts, "batch angular counts do not close")
    require([int(value) for value in provenance["transport_seed"]] == [int(row["transport_seed"]) for row in batch_receipts], "provenance transport-seed list differs")

    lineage_by_event: dict[int, dict[str, str]] = {}
    for row in lineage:
        event_id = int(row["global_event_id"])
        index = int(row["batch_index"])
        local_id = int(row["local_event_id"])
        require(event_id not in lineage_by_event, f"duplicate lineage event ID: {event_id}")
        require(index in batch_by_index, f"lineage references unknown batch {index}")
        require(row["run_name"] == batch_by_index[index]["run_name"], "lineage run name differs from batch")
        require(event_id == index * 10_000_000_000 + local_id, "input campaign event-ID convention changed")
        lineage_by_event[event_id] = row
    require(set(lineage_by_event) == event_ids, "lineage/event ID sets differ")

    response_path = compact_path(
        receipt["response"]["summary"], allowed_root=aggregate_root, role="campaign response summary"
    )
    require(sha256(response_path) == receipt["response"]["summary_sha256"], "campaign response-summary hash mismatch")
    require(int(receipt["response"]["replicas"]) == RESPONSE_REPLICAS, "campaign response replicas are not 64")
    response = read_json(response_path)
    detector_response = validate_response_parameters(response, "input campaign")
    response_paths, response_seeds = validate_response_artifacts(response_path, response)
    input_parse_path = compact_path(
        response["input_parse"]["path"], allowed_root=provenance_path.parent, role="response input provenance"
    )
    require(input_parse_path == provenance_path, "response points to another compact provenance")
    require(response["input_parse"]["sha256"] == sha256(provenance_path), "response input-provenance hash mismatch")
    require(response["transport_footer"] == footer, "response transport footer differs")

    campaign_manifest = str(receipt["campaign_manifest"]["path"])
    campaign_id = Path(campaign_manifest).parent.name
    require(bool(campaign_id), "campaign identity is empty")
    return {
        "receipt_path": receipt_path,
        "receipt_sha256": receipt_hash,
        "receipt": receipt,
        "campaign_manifest": campaign_manifest,
        "campaign_id": campaign_id,
        "aggregate_fingerprint_sha256": str(receipt["aggregate_fingerprint_sha256"]),
        "provenance_path": provenance_path,
        "provenance": provenance,
        "paths": paths,
        "events": events,
        "pixels": pixels,
        "lineage_by_event": lineage_by_event,
        "angular_counts": angular_counts,
        "counts": counts,
        "TS": ts,
        "TE_s": te_s,
        "batch_receipts": batch_receipts,
        "transport_seeds": [int(row["transport_seed"]) for row in batch_receipts],
        "run_names": [str(row["run_name"]) for row in batch_receipts],
        "response_path": response_path,
        "response": response,
        "response_paths": response_paths,
        "response_seeds": response_seeds,
        "detector_response": detector_response,
    }


def validate_input_set(receipt_paths: list[Path]) -> list[dict[str, Any]]:
    require(bool(receipt_paths), "at least one campaign aggregate receipt is required")
    resolved = [path.resolve() for path in receipt_paths]
    require(len(resolved) == len(set(resolved)), "duplicate input receipt path")
    inputs = [validate_campaign_receipt(path) for path in resolved]
    inputs.sort(key=lambda row: (row["campaign_manifest"], row["receipt_sha256"]))
    campaign_ids = [row["campaign_manifest"] for row in inputs]
    require(len(campaign_ids) == len(set(campaign_ids)), "duplicate campaign identity")
    receipt_hashes = [row["receipt_sha256"] for row in inputs]
    require(len(receipt_hashes) == len(set(receipt_hashes)), "duplicate campaign receipt content")
    seeds = [seed for row in inputs for seed in row["transport_seeds"]]
    require(len(seeds) == len(set(seeds)), "duplicate transport seed across campaigns")
    run_names = [name for row in inputs for name in row["run_names"]]
    require(len(run_names) == len(set(run_names)), "duplicate batch run name across campaigns")
    fingerprints = [row["aggregate_fingerprint_sha256"] for row in inputs]
    require(len(fingerprints) == len(set(fingerprints)), "duplicate aggregate fingerprint")
    batch_keys = [
        (row["campaign_manifest"], int(batch["batch_index"]))
        for row in inputs
        for batch in row["batch_receipts"]
    ]
    require(len(batch_keys) == len(set(batch_keys)), "duplicate campaign/batch identity")
    start_areas = {float(row["provenance"]["sim_header"]["start_area_cm2"]) for row in inputs}
    require(len(start_areas) == 1 and next(iter(start_areas)) > 0.0, "campaign start areas differ")
    detector_fingerprints = {canonical_sha256(row["detector_response"]) for row in inputs}
    require(len(detector_fingerprints) == 1, "campaign detector-response parameters differ")
    response_seed_sets = {tuple(row["response_seeds"]) for row in inputs}
    require(len(response_seed_sets) == 1, "campaign 64-seed response ensembles differ")
    return inputs


def merge_receipts(
    receipt_paths: list[Path],
    output_dir: Path,
    *,
    allow_temporary_output: bool = False,
) -> dict[str, Any]:
    authority = H.authority_report()
    inputs = validate_input_set(receipt_paths)
    output_dir = output_dir.resolve()
    allowed_output = output_dir.is_relative_to(PACKAGE.resolve())
    if allow_temporary_output:
        allowed_output = allowed_output or output_dir.is_relative_to(
            Path(tempfile.gettempdir()).resolve()
        )
    require(
        allowed_output,
        "supercampaign output must stay inside the isolated WP2 package"
        + (" or the system temporary directory" if allow_temporary_output else ""),
    )
    require(not output_dir.exists(), f"refusing to overwrite supercampaign output: {output_dir}")
    output_dir.mkdir(parents=True)
    merged_dir = output_dir / "merged_compact"
    response_dir = output_dir / "response"
    merged_dir.mkdir()
    response_dir.mkdir()

    event_path = merged_dir / "tes_events.csv"
    pixel_path = merged_dir / "tes_pixel_hits.csv"
    lineage_path = merged_dir / "event_lineage.csv"
    angular_path = merged_dir / "angular_counts.json"
    provenance_path = merged_dir / "provenance.json"

    total_counts: Counter[str] = Counter()
    total_ts = 0
    total_te_s = 0.0
    merged_angular = {bins: [0] * bins for bins in (20, 40, 80)}
    output_event_ids: set[int] = set()
    event_count = 0
    pixel_count = 0
    lineage_fields = [
        "super_event_id",
        "campaign_ordinal",
        "campaign_id",
        "campaign_receipt_sha256",
        "input_global_event_id",
        "batch_index",
        "run_name",
        "local_event_id",
    ]
    with event_path.open("x", encoding="utf-8", newline="") as event_handle, pixel_path.open(
        "x", encoding="utf-8", newline=""
    ) as pixel_handle, lineage_path.open("x", encoding="utf-8", newline="") as lineage_handle:
        event_writer = csv.DictWriter(event_handle, fieldnames=list(H.EVENT_FIELDS))
        pixel_writer = csv.DictWriter(pixel_handle, fieldnames=list(H.PIXEL_FIELDS))
        lineage_writer = csv.DictWriter(lineage_handle, fieldnames=lineage_fields)
        event_writer.writeheader()
        pixel_writer.writeheader()
        lineage_writer.writeheader()
        for ordinal, item in enumerate(inputs):
            id_map: dict[int, int] = {}
            for row in item["events"]:
                input_id = int(row["event_id"])
                require(0 <= input_id < SUPER_EVENT_ID_STRIDE, "input event ID exceeds supercampaign namespace")
                output_id = ordinal * SUPER_EVENT_ID_STRIDE + input_id
                require(output_id not in output_event_ids, "supercampaign event-ID collision")
                output_event_ids.add(output_id)
                id_map[input_id] = output_id
                output_row = dict(row)
                output_row["event_id"] = output_id
                event_writer.writerow(output_row)
                source_lineage = item["lineage_by_event"][input_id]
                lineage_writer.writerow(
                    {
                        "super_event_id": output_id,
                        "campaign_ordinal": ordinal,
                        "campaign_id": item["campaign_id"],
                        "campaign_receipt_sha256": item["receipt_sha256"],
                        "input_global_event_id": input_id,
                        "batch_index": source_lineage["batch_index"],
                        "run_name": source_lineage["run_name"],
                        "local_event_id": source_lineage["local_event_id"],
                    }
                )
                event_count += 1
            for row in item["pixels"]:
                input_id = int(row["event_id"])
                require(input_id in id_map, "pixel references an unmapped supercampaign event")
                output_row = dict(row)
                output_row["event_id"] = id_map[input_id]
                pixel_writer.writerow(output_row)
                pixel_count += 1
            total_counts.update(item["counts"])
            total_ts += item["TS"]
            total_te_s += item["TE_s"]
            for bins in (20, 40, 80):
                merged_angular[bins] = [
                    left + right
                    for left, right in zip(merged_angular[bins], item["angular_counts"][bins])
                ]

    require(event_count == total_counts["tes_events"], "supercampaign TES count does not close")
    require(pixel_count == total_counts["tes_pixel_hits"], "supercampaign pixel count does not close")
    for bins in (20, 40, 80):
        require(sum(merged_angular[bins]) == total_ts, f"supercampaign {bins}-bin counts do not close")
    atomic_write_json(
        angular_path,
        {
            "schema": H.PARSE_SCHEMA,
            "mapping": "mu_source=-IA_INIT.dir_z; same-event 20/40/80 merged counts",
            "init_records": total_ts,
            "counts": {str(bins): values for bins, values in merged_angular.items()},
        },
    )
    compact_artifacts = {
        rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in (event_path, pixel_path, angular_path, lineage_path)
    }
    fingerprint_payload = {
        "schema": OUTPUT_SCHEMA,
        "inputs": [
            {
                "campaign_manifest": item["campaign_manifest"],
                "receipt_sha256": item["receipt_sha256"],
                "aggregate_fingerprint_sha256": item["aggregate_fingerprint_sha256"],
            }
            for item in inputs
        ],
        "response_replicas": RESPONSE_REPLICAS,
        "response_harness_sha256": sha256(HARNESS_PATH),
    }
    super_fingerprint = canonical_sha256(fingerprint_payload)
    start_area = float(inputs[0]["provenance"]["sim_header"]["start_area_cm2"])
    merged_provenance = {
        "schema": H.PARSE_SCHEMA,
        "status": "PASS_STREAM_PARSE_COMPLETE",
        "parsed_at_utc": utc_now(),
        "parser": {"path": rel(SCRIPT), "sha256": sha256(SCRIPT)},
        "frozen_response_harness": {
            "path": rel(HARNESS_PATH),
            "sha256": sha256(HARNESS_PATH),
            "imported_response_function": "response_analysis",
        },
        "scope": "supercampaign compact merge; atmospheric annihilation mono line only",
        "proposal": "parma80_physical_flux",
        "source_card": {
            "input_campaign_receipts": [rel(item["receipt_path"]) for item in inputs],
            "note": "No source card or raw SIM was opened by this compact-only merger.",
        },
        "raw_sim": "NOT_RESOLVED_OR_READ",
        "raw_sim_files_read_during_merge": False,
        "cosima_launched": False,
        "transport_invocations": 0,
        "sim_header": {
            "start_area_cm2": start_area,
            "campaign_headers": [item["provenance"]["sim_header"] for item in inputs],
        },
        "geometry_authority": str(H.O8_SETUP),
        "geometry_hashes": {
            "setup": H.EXPECTED_SHA256[H.O8_SETUP],
            "geo": H.EXPECTED_SHA256[H.O8_GEO],
            "det": H.EXPECTED_SHA256[H.O8_DET],
        },
        "transport_seed": [seed for item in inputs for seed in item["transport_seeds"]],
        "expected_energy_keV": H.PARMA_LINE_ENERGY_KEV,
        "energy_tolerance_keV": 0.001,
        "sim_footer": {"TE_s": total_te_s, "TS": total_ts},
        "counts": dict(total_counts),
        "checks": {
            "input_campaign_receipts_all_hash_closed": True,
            "input_campaigns_unique": True,
            "input_batches_unique": True,
            "transport_seeds_unique": True,
            "o8_three_hashes_current_and_consistent": True,
            "step05_hash_current_and_consistent": True,
            "response_parameters_and_64_seeds_consistent": True,
            "merged_event_count_closed": True,
            "merged_pixel_count_closed": True,
            "merged_angular_counts_closed": True,
            "merge_used_compact_only": True,
            "raw_paths_not_resolved_or_read": True,
            "cosima_not_launched": True,
        },
        "artifacts": compact_artifacts,
        "input_receipts": [
            {
                "campaign_id": item["campaign_id"],
                "campaign_manifest": item["campaign_manifest"],
                "receipt": rel(item["receipt_path"]),
                "receipt_sha256": item["receipt_sha256"],
                "aggregate_fingerprint_sha256": item["aggregate_fingerprint_sha256"],
                "merged_provenance": rel(item["provenance_path"]),
                "merged_provenance_sha256": sha256(item["provenance_path"]),
                "response_summary": rel(item["response_path"]),
                "response_summary_sha256": sha256(item["response_path"]),
                "batch_indices": [int(row["batch_index"]) for row in item["batch_receipts"]],
                "transport_seeds": item["transport_seeds"],
                "TS": item["TS"],
                "TE_s": item["TE_s"],
            }
            for item in inputs
        ],
        "supercampaign_fingerprint_sha256": super_fingerprint,
    }
    atomic_write_json(provenance_path, merged_provenance)

    response = H.response_analysis(
        parsed_dir=merged_dir,
        output_dir=response_dir,
        proposal="parma80",
        replicas=RESPONSE_REPLICAS,
    )
    output_detector = validate_response_parameters(response, "supercampaign")
    require(output_detector == inputs[0]["detector_response"], "rerun response metadata differs from input campaigns")
    output_response_path = response_dir / "response_64seed_summary.json"
    _, output_response_seeds = validate_response_artifacts(output_response_path, response)
    require(output_response_seeds == inputs[0]["response_seeds"], "rerun 64-seed ensemble differs")
    require(response["input_parse"]["sha256"] == sha256(provenance_path), "supercampaign response did not bind merged provenance")

    primary_gate = response["primary_detector_rate_gate"]
    status = (
        "PASS_SUPERCAMPAIGN_COMPACT_AGGREGATE_AND_LINE_RATE_GATE"
        if primary_gate["passes_detector_rate_gate"]
        else "SUPERCAMPAIGN_COMPACT_AGGREGATE_COMPLETE_DIAGNOSTIC_ONLY"
    )
    receipt_path = output_dir / "supercampaign_aggregate_receipt.json"
    receipt = {
        "schema": OUTPUT_SCHEMA,
        "status": status,
        "created_at_utc": utc_now(),
        "scope": {
            "particle": "gamma",
            "module": "atmospheric annihilation mono line only",
            "energy_keV": H.PARMA_LINE_ENERGY_KEV,
            "proposal": "parma80 physical-flux angular grid",
            "continuum_included": False,
            "other_particles_included": False,
            "raw_sim_files_read": False,
            "cosima_launched": False,
            "transport_invocations": 0,
        },
        "supercampaign_fingerprint_sha256": super_fingerprint,
        "merger": {"path": rel(SCRIPT), "sha256": sha256(SCRIPT)},
        "frozen_response_harness": {"path": rel(HARNESS_PATH), "sha256": sha256(HARNESS_PATH)},
        "authority": {
            "o8_setup_sha256": H.EXPECTED_SHA256[H.O8_SETUP],
            "o8_geo_sha256": H.EXPECTED_SHA256[H.O8_GEO],
            "o8_det_sha256": H.EXPECTED_SHA256[H.O8_DET],
            "step05_sha256": H.EXPECTED_SHA256[H.STEP05_IMPLEMENTATION],
            "step09_summary_sha256": H.EXPECTED_SHA256[H.STEP09_SUMMARY],
            "authority_preflight_status": authority["status"],
        },
        "input_campaigns": merged_provenance["input_receipts"],
        "included_campaign_ids": [item["campaign_id"] for item in inputs],
        "included_campaign_count": len(inputs),
        "included_batch_count": sum(len(item["batch_receipts"]) for item in inputs),
        "transport_seeds": merged_provenance["transport_seed"],
        "merged_compact": {
            "provenance": rel(provenance_path),
            "provenance_sha256": sha256(provenance_path),
            "events": event_count,
            "pixel_hits": pixel_count,
            "TS": total_ts,
            "TE_s": total_te_s,
            "artifacts": compact_artifacts,
            "raw_sim_files_read": False,
        },
        "response": {
            "summary": rel(output_response_path),
            "summary_sha256": sha256(output_response_path),
            "replicas": RESPONSE_REPLICAS,
            "response_seeds": output_response_seeds,
            "primary_gate": primary_gate,
        },
        "selection_blocker": {
            "preserved": True,
            "active_veto_predicate_blocker": H.ACTIVE_VETO_NAMING_BLOCKER,
            "passive_kapton_wrappers": list(H.KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS),
        },
        "checks": merged_provenance["checks"],
        "raw_deleted": False,
        "cosima_launched": False,
        "claim_boundary": (
            "This receipt merges only hash-closed compact atmospheric-511 line campaigns. "
            "It neither reads raw SIM nor runs transport. Publication-grade use still "
            "requires the recorded detector-rate gate to pass and retains the passive-Kapton naming blocker."
        ),
    }
    atomic_write_json(receipt_path, receipt)
    return receipt


def artifact_hashes_by_name(response: dict[str, Any]) -> dict[str, str]:
    return {Path(path).name: record["sha256"] for path, record in response["artifacts"].items()}


def scientific_response_view(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "unsmeared": response["unsmeared"],
        "primary_420eV": response["primary_420eV"],
        "primary_detector_rate_gate": response["primary_detector_rate_gate"],
        "angular_response_summaries": response["angular_response_coefficients"]["summaries"],
        "ensemble": response["ensemble"],
    }


def expected_rejection(callable_value: Any, phrase: str) -> dict[str, Any]:
    try:
        callable_value()
    except MergeError as exc:
        message = str(exc)
        require(phrase in message, f"rejection raised the wrong error: {message}")
        return {"passed": True, "expected_phrase": phrase, "error": message}
    raise MergeError(f"expected rejection did not occur: {phrase}")


def identity_self_test(
    *, smoke_receipt: Path, output_dir: Path, selftest_receipt: Path
) -> dict[str, Any]:
    require(not output_dir.exists(), f"self-test output already exists: {output_dir}")
    require(not selftest_receipt.exists(), f"self-test receipt already exists: {selftest_receipt}")
    super_receipt = merge_receipts(
        [smoke_receipt], output_dir, allow_temporary_output=True
    )
    source = validate_campaign_receipt(smoke_receipt)
    super_path = output_dir / "supercampaign_aggregate_receipt.json"
    super_value = read_json(super_path)
    super_provenance_path = root_path(super_value["merged_compact"]["provenance"])
    super_provenance = read_json(super_provenance_path)
    super_response_path = root_path(super_value["response"]["summary"])
    super_response = read_json(super_response_path)

    input_artifact_hashes = {
        name: sha256(path) for name, path in source["paths"].items()
    }
    output_artifact_hashes = {
        Path(path).name: record["sha256"]
        for path, record in super_value["merged_compact"]["artifacts"].items()
    }
    checks = {
        "single_input_schema_is_supercampaign_v1": super_value["schema"] == OUTPUT_SCHEMA,
        "TS_identity": int(super_value["merged_compact"]["TS"]) == source["TS"],
        "TE_identity": close(super_value["merged_compact"]["TE_s"], source["TE_s"]),
        "count_identity": super_provenance["counts"] == source["provenance"]["counts"],
        "angular_numeric_identity": read_json(root_path(next(path for path in super_value["merged_compact"]["artifacts"] if Path(path).name == "angular_counts.json")))["counts"] == read_json(source["paths"]["angular_counts.json"])["counts"],
        "tes_events_hash_identity": output_artifact_hashes["tes_events.csv"] == input_artifact_hashes["tes_events.csv"],
        "tes_pixel_hits_hash_identity": output_artifact_hashes["tes_pixel_hits.csv"] == input_artifact_hashes["tes_pixel_hits.csv"],
        "angular_counts_hash_identity": output_artifact_hashes["angular_counts.json"] == input_artifact_hashes["angular_counts.json"],
        "scientific_response_identity": scientific_response_view(super_response) == scientific_response_view(source["response"]),
        "response_artifact_hash_identity": artifact_hashes_by_name(super_response) == artifact_hashes_by_name(source["response"]),
        "super_receipt_hash_is_well_formed": len(sha256(super_path)) == 64,
        "merged_provenance_hash_closes": sha256(super_provenance_path) == super_value["merged_compact"]["provenance_sha256"],
        "response_summary_hash_closes": sha256(super_response_path) == super_value["response"]["summary_sha256"],
        "kapton_blocker_preserved": super_value["selection_blocker"]["active_veto_predicate_blocker"] == H.ACTIVE_VETO_NAMING_BLOCKER,
        "cosima_not_launched": super_value["cosima_launched"] is False and super_value["scope"]["transport_invocations"] == 0,
        "raw_not_read": super_value["scope"]["raw_sim_files_read"] is False,
    }
    require(all(checks.values()), f"single-input identity checks failed: {checks}")

    duplicate_input_path = expected_rejection(
        lambda: validate_input_set([smoke_receipt, smoke_receipt]),
        "duplicate input receipt path",
    )
    # Receipt paths are deliberately bound to their aggregate directory, so the
    # temporary negative fixtures live beside the smoke receipt and are removed
    # immediately after the checks.  They never point at, open, or copy raw SIM.
    fixture_token = f"{os.getpid()}_{next(tempfile._get_candidate_names())}"
    campaign_clone_path = smoke_receipt.parent / f".supermerge_campaign_fixture_{fixture_token}.json"
    clone_path = smoke_receipt.parent / f".supermerge_seed_fixture_{fixture_token}.json"
    corrupted_path = smoke_receipt.parent / f".supermerge_hash_fixture_{fixture_token}.json"
    require(
        not campaign_clone_path.exists()
        and not clone_path.exists()
        and not corrupted_path.exists(),
        "self-test fixture path exists",
    )
    try:
        atomic_write_json(campaign_clone_path, read_json(smoke_receipt))
        duplicate_campaign = expected_rejection(
            lambda: validate_input_set([smoke_receipt, campaign_clone_path]),
            "duplicate campaign identity",
        )
        clone = read_json(smoke_receipt)
        clone["campaign_manifest"]["path"] = (
            "engineering/m04_validation_geometry_handoff_20260810/"
            "02_parma_atm511_repair_20260810/transport/campaigns/"
            "synthetic_distinct_campaign_for_seed_rejection/campaign_manifest.json"
        )
        atomic_write_json(clone_path, clone)
        duplicate_seed = expected_rejection(
            lambda: validate_input_set([smoke_receipt, clone_path]),
            "duplicate transport seed across campaigns",
        )
        corrupted = read_json(smoke_receipt)
        first_artifact = next(iter(corrupted["merged_compact"]["artifacts"]))
        corrupted["merged_compact"]["artifacts"][first_artifact]["sha256"] = "0" * 64
        atomic_write_json(corrupted_path, corrupted)
        corrupted_hash = expected_rejection(
            lambda: validate_campaign_receipt(corrupted_path),
            "receipt/provenance compact artifact maps differ",
        )
    finally:
        for fixture in (campaign_clone_path, clone_path, corrupted_path):
            if fixture.exists():
                fixture.unlink()

    report = {
        "schema": SELFTEST_SCHEMA,
        "status": "PASS_REAL_1K_SINGLE_INPUT_IDENTITY_AND_REJECTION_TESTS",
        "created_at_utc": utc_now(),
        "scope": "compact-only; no raw SIM read; no Cosima or transport invocation",
        "script": hash_record(SCRIPT),
        "frozen_response_harness": hash_record(HARNESS_PATH),
        "input_smoke_receipt": hash_record(smoke_receipt),
        "output_supercampaign_receipt": hash_record(super_path),
        "output_merged_provenance": hash_record(super_provenance_path),
        "output_response_summary": hash_record(super_response_path),
        "identity_checks": checks,
        "rejection_checks": {
            "duplicate_input_receipt_path": duplicate_input_path,
            "duplicate_campaign": duplicate_campaign,
            "duplicate_transport_seed": duplicate_seed,
            "corrupted_compact_hash": corrupted_hash,
        },
        "identity_values": {
            "TS": source["TS"],
            "TE_s": source["TE_s"],
            "events": source["counts"]["tes_events"],
            "pixel_hits": source["counts"]["tes_pixel_hits"],
            "response_primary_gate": super_receipt["response"]["primary_gate"],
        },
        "cosima_launched": False,
        "transport_invocations": 0,
        "raw_sim_files_read": False,
    }
    atomic_write_json(selftest_receipt, report)
    return report


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="merge one or more complete campaign aggregate receipts")
    merge.add_argument("--receipt", action="append", type=Path, required=True)
    merge.add_argument("--output-dir", type=Path, required=True)
    test = sub.add_parser("self-test", help="run the real 1k single-input identity test")
    test.add_argument("--smoke-receipt", type=Path, default=SMOKE_RECEIPT)
    test.add_argument(
        "--output-dir",
        type=Path,
        help="persistent supercampaign output; omit with --self-test-receipt for an auto-cleaned /tmp test",
    )
    test.add_argument(
        "--self-test-receipt",
        type=Path,
        help="persistent self-test receipt; omit with --output-dir for an auto-cleaned /tmp test",
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "merge":
            result = merge_receipts(args.receipt, args.output_dir)
            output = {
                "status": result["status"],
                "schema": result["schema"],
                "receipt": rel(args.output_dir.resolve() / "supercampaign_aggregate_receipt.json"),
                "campaigns": result["included_campaign_count"],
                "batches": result["included_batch_count"],
                "TS": result["merged_compact"]["TS"],
                "TE_s": result["merged_compact"]["TE_s"],
                "primary_gate": result["response"]["primary_gate"],
                "cosima_launched": False,
                "raw_sim_files_read": False,
            }
        else:
            persistent = args.output_dir is not None or args.self_test_receipt is not None
            require(
                (args.output_dir is None) == (args.self_test_receipt is None),
                "persistent self-test requires both --output-dir and --self-test-receipt",
            )
            if persistent:
                result = identity_self_test(
                    smoke_receipt=args.smoke_receipt.resolve(),
                    output_dir=args.output_dir.resolve(),
                    selftest_receipt=args.self_test_receipt.resolve(),
                )
                receipt_label = rel(args.self_test_receipt.resolve())
                cleanup = False
            else:
                with tempfile.TemporaryDirectory(
                    prefix="o8_parma511_supercampaign_selftest_",
                    dir=tempfile.gettempdir(),
                ) as tmp_name:
                    tmp = Path(tmp_name)
                    result = identity_self_test(
                        smoke_receipt=args.smoke_receipt.resolve(),
                        output_dir=tmp / "supercampaign",
                        selftest_receipt=tmp / "self_test_receipt.json",
                    )
                    receipt_label = "TEMPORARY_SELF_TEST_RECEIPT_VALIDATED_THEN_AUTO_CLEANED"
                    cleanup = True
            output = {
                "status": result["status"],
                "self_test_receipt": receipt_label,
                "supercampaign_receipt_sha256": result["output_supercampaign_receipt"]["sha256"],
                "temporary_outputs_auto_cleaned": cleanup,
                "identity_checks": result["identity_checks"],
                "rejection_checks": result["rejection_checks"],
                "cosima_launched": False,
                "raw_sim_files_read": False,
            }
    except (MergeError, H.HarnessError, KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
