#!/usr/bin/env python3
"""Terminal-gated, write-once M05 response adapter for phase02 delayed SIMs.

The active phase02 transport writes below ``.attempt01.partial`` directories.
This reader never opens those paths.  ``--check`` and ``--self-test`` do not
open any SIM.  ``--run`` is admitted only after the canonical 12-job subset
summary has been atomically published with PASS status and every selected SIM
is bound to a final ``attempt01`` directory.

The resulting rates cover the six paired phase02 families only and retain the
source package's explicit excited-state holdout.  They are partial delayed
response screening, not complete delayed, mission-sensitivity, paper-rate, or
geometry-promotion authority.
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
from types import SimpleNamespace
from typing import Any

import numpy as np

import analyze_batch0007_prompt_activation as shared


sys.dont_write_bytecode = True

ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1"
PHASE_ROOT = RUN_ROOT / "delayed_phase02/state_aware_exactpos_v1"
TRANSPORT_PLAN = PHASE_ROOT / "transport_jobs.json"
PREPARED_MANIFEST = PHASE_ROOT / "manifest.json"
EXPECTED_FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "muminus")
GEOMETRIES = ("Mass_model_511", "S3d_O8")
TRIGGERS_PER_JOB = 1_000_000
EXPECTED_JOB_COUNT = len(EXPECTED_FAMILIES) * len(GEOMETRIES)
EXPECTED_EVENT_COUNT = EXPECTED_JOB_COUNT * TRIGGERS_PER_JOB
EXPECTED_TERMINAL_SUMMARY_NAME = "transport_summary.partial_59ff7d29ca6e.json"
EXPECTED_TERMINAL_SUMMARY = PHASE_ROOT / EXPECTED_TERMINAL_SUMMARY_NAME
OUTPUT = RUN_ROOT / "analysis_delayed_response"

STEP05_IMPLEMENTATION = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
PASS_SUMMARY_STATUS = "PASS__SELECTED_DELAYED_TRANSPORT_SUBSET_COMPLETED"
PASS_SOURCE_STATUS = "PASS__GROUND_STATE_EXACT_POSITION_SOURCE_READY__NONZERO_STATES_FAIL_CLOSED"

RESPONSE_SEED = shared.M05_RESPONSE_SEED
RESPONSE_SIGMA_KEV = shared.M05_RESPONSE_SIGMA_KEV
MEASURED_PIXEL_THRESHOLD_KEV = shared.MEASURED_PIXEL_THRESHOLD_KEV
BROAD = shared.BROAD
W2 = shared.W2
VETO_THRESHOLDS_KEV = shared.VETO_THRESHOLDS_KEV
ZERO_COUNT_95_UPPER_MEAN = shared.ZERO_COUNT_95_UPPER_MEAN
TES_RE = shared.TES_RE
REQUIRED_HIT_KV = shared.REQUIRED_HIT_KV


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if path.name.startswith(".") or path.name.endswith(".partial"):
        raise RuntimeError(f"refusing staging JSON input: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
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


def output_collision_check() -> None:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError(f"write-once output collision: {OUTPUT}")


def expected_job_ids() -> list[str]:
    return [f"delayed02_{family}_{geometry}" for family in EXPECTED_FAMILIES for geometry in GEOMETRIES]


def expected_summary_digest() -> str:
    canonical = json.dumps(expected_job_ids(), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def path_is_staging(path: Path) -> bool:
    return any(part.startswith(".") or part.endswith(".partial") for part in path.parts)


def validate_plan() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    plan = load_json(TRANSPORT_PLAN)
    prepared = load_json(PREPARED_MANIFEST)
    if plan.get("status") != "READY_NOT_LAUNCHED" or prepared.get("status") != "PASS__STATE_AWARE_EXACT_POSITION_DELAYED_SOURCES_READY__TRANSPORT_NOT_LAUNCHED":
        raise RuntimeError("phase02 prepared plan/manifest status drift")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("phase02 transport plan lacks jobs")
    by_id = {str(job["job_id"]): job for job in jobs}
    if len(by_id) != len(jobs):
        raise RuntimeError("phase02 transport plan contains duplicate job IDs")
    missing = sorted(set(expected_job_ids()) - set(by_id))
    if missing:
        raise RuntimeError(f"phase02 plan lacks expected 12-job subset: {missing}")
    for job_id in expected_job_ids():
        job = by_id[job_id]
        if int(job.get("triggers", -1)) != TRIGGERS_PER_JOB:
            raise RuntimeError(f"unexpected trigger count: {job_id}")
        if str(job.get("geometry")) not in GEOMETRIES or str(job.get("family")) not in EXPECTED_FAMILIES:
            raise RuntimeError(f"unexpected job cell: {job_id}")
        published = (ROOT / str(job["published_sim"])).resolve()
        if path_is_staging(published) or published.parent.name != "attempt01":
            raise RuntimeError(f"published SIM path is not final attempt01: {published}")
    if EXPECTED_TERMINAL_SUMMARY.name != f"transport_summary.partial_{expected_summary_digest()}.json":
        raise RuntimeError("expected phase02 terminal-summary digest drift")
    return plan, by_id


def validate_terminal_summary() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read terminal declarations only; never open a SIM or staging directory."""
    _plan, by_id = validate_plan()
    if not EXPECTED_TERMINAL_SUMMARY.is_file():
        raise RuntimeError(f"phase02 12-job terminal summary is absent: {EXPECTED_TERMINAL_SUMMARY}")
    summary = load_json(EXPECTED_TERMINAL_SUMMARY)
    if summary.get("status") != PASS_SUMMARY_STATUS:
        raise RuntimeError(f"phase02 12-job terminal summary is not PASS: {summary.get('status')}")
    selection = summary.get("selection")
    if not isinstance(selection, dict):
        raise RuntimeError("phase02 terminal summary lacks selection")
    ids = [str(value) for value in selection.get("selected_job_ids", [])]
    if ids != expected_job_ids() or int(selection.get("selected_job_count", -1)) != EXPECTED_JOB_COUNT:
        raise RuntimeError(f"phase02 terminal selected-job drift: {ids}")
    if selection.get("all_prepared_jobs_selected") is not False:
        raise RuntimeError("expected the explicitly bounded 12-job subset, not a different coverage scope")
    if int(summary.get("completed", -1)) != EXPECTED_JOB_COUNT or summary.get("completed_job_ids") != ids:
        raise RuntimeError("phase02 terminal completion declaration drift")
    if summary.get("paper_closure_claimed") is not False:
        raise RuntimeError("phase02 terminal authority boundary drift")
    if summary.get("summary_path") != rel(EXPECTED_TERMINAL_SUMMARY):
        raise RuntimeError("phase02 terminal summary self-binding mismatch")

    rows = summary.get("jobs")
    if not isinstance(rows, list) or len(rows) != EXPECTED_JOB_COUNT:
        raise RuntimeError("phase02 terminal receipt list drift")
    receipts_by_id = {str(row["job"]["job_id"]): row for row in rows}
    if set(receipts_by_id) != set(ids):
        raise RuntimeError("phase02 terminal receipt identities drift")

    receipts: list[dict[str, Any]] = []
    for job_id in ids:
        receipt = receipts_by_id[job_id]
        job = receipt.get("job")
        if job != by_id[job_id]:
            raise RuntimeError(f"terminal receipt/frozen plan mismatch: {job_id}")
        check = receipt.get("minimal_sim_check", {})
        if receipt.get("status") != "PASS" or int(receipt.get("returncode", -1)) != 0 or check.get("status") != "PASS":
            raise RuntimeError(f"terminal receipt not PASS: {job_id}")
        if int(check.get("SE", -1)) != TRIGGERS_PER_JOB or int(check.get("ID", -1)) != TRIGGERS_PER_JOB or int(check.get("EN", -1)) != 1:
            raise RuntimeError(f"terminal SIM framing declaration drift: {job_id}")
        if int(check.get("seed", -1)) != int(job["seed"]):
            raise RuntimeError(f"terminal SIM seed declaration drift: {job_id}")
        sim = (ROOT / str(receipt["published_sim"])).resolve()
        expected_sim = (ROOT / str(job["published_sim"])).resolve()
        final_dir = (ROOT / str(job["attempt_final_dir"])).resolve()
        staging_dir = (ROOT / str(job["attempt_partial_dir"])).resolve()
        if sim != expected_sim or sim.parent != final_dir or final_dir.name != "attempt01" or path_is_staging(sim):
            raise RuntimeError(f"terminal SIM is not bound to final attempt01: {job_id}")
        if staging_dir.exists():
            raise RuntimeError(f"selected staging attempt still exists; refusing analysis: {staging_dir}")
        if not sim.is_file():
            raise RuntimeError(f"terminal published SIM missing: {sim}")
        final_receipt = final_dir / "receipt.json"
        if not final_receipt.is_file() or load_json(final_receipt) != receipt:
            raise RuntimeError(f"terminal embedded/final receipt mismatch: {job_id}")
        receipts.append(receipt)
    return receipts, summary


def source_weight(job: dict[str, Any]) -> dict[str, Any]:
    source = (ROOT / str(job["source"])).resolve()
    if path_is_staging(source) or not source.is_file():
        raise RuntimeError(f"noncanonical phase02 source: {source}")
    manifest_path = source.parent / "source_manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != PASS_SOURCE_STATUS:
        raise RuntimeError(f"phase02 source manifest not PASS: {manifest_path}")
    if str(manifest.get("geometry")) != str(job["geometry"]) or str(manifest.get("family")) != str(job["family"]):
        raise RuntimeError(f"source manifest cell mismatch: {job['job_id']}")
    if (ROOT / str(manifest.get("source"))).resolve() != source:
        raise RuntimeError(f"source manifest path mismatch: {job['job_id']}")
    if int(manifest.get("triggers_requested", -1)) != int(job["triggers"]):
        raise RuntimeError(f"source/transport trigger mismatch: {job['job_id']}")
    if int(manifest.get("transport_seed", -1)) != int(job["seed"]):
        raise RuntimeError(f"source/transport seed mismatch: {job['job_id']}")
    activity = float(manifest.get("included_ground_activity_Bq", 0.0))
    if not math.isfinite(activity) or activity <= 0.0:
        raise RuntimeError(f"non-positive source activity: {job['job_id']}")
    return {
        "source_manifest": rel(manifest_path),
        "source_manifest_sha256": sha256_file(manifest_path),
        "included_ground_activity_Bq": activity,
        "event_weight_cps": activity / int(job["triggers"]),
        "equivalent_time_s": int(job["triggers"]) / activity,
        "known_holdout_activity_Bq": float(manifest.get("known_holdout_activity_Bq", 0.0)),
        "known_holdout_activity_fraction": float(manifest.get("known_holdout_activity_fraction", 0.0)),
        "unknown_activity_state_count": int(manifest.get("unknown_activity_state_count", 0)),
    }


def load_step05() -> tuple[Any, dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("batch0007_delayed_step05", STEP05_IMPLEMENTATION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Step05 selection: {STEP05_IMPLEMENTATION}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.STEP09_SUMMARY = STEP09_SUMMARY
    disk = module.side_entry_disk()
    return module, disk


def topology(hits: list[Any], step05: Any, disk: dict[str, Any]) -> tuple[bool, str]:
    if len(hits) <= 1:
        return True, "single"
    if len(hits) > int(step05.MAX_ENUM_HITS):
        return True, "reject_kept"
    keep, classification = step05.side_keep_from_hits(hits, disk, "keep")
    return bool(keep), str(classification)


def analyze_job(
    receipt: dict[str, Any],
    weight: dict[str, Any],
    rng: np.random.Generator,
    step05: Any,
    disk: dict[str, Any],
) -> tuple[dict[str, Any], Counter[str], set[str]]:
    job = receipt["job"]
    geometry, family = str(job["geometry"]), str(job["family"])
    sim_path = (ROOT / str(receipt["published_sim"])).resolve()
    exact_active = shared.active_blocks(geometry)
    counters: Counter[str] = Counter()
    topology_classes: Counter[str] = Counter()
    active_observed: set[str] = set()
    current_id: int | None = None
    next_id = 1
    pixels: dict[str, dict[str, float]] = {}
    active_keV = 0.0
    header_geometry: str | None = None
    header_seed: int | None = None
    en_count = 0

    def flush() -> None:
        nonlocal current_id, pixels, active_keV
        if current_id is None:
            return
        counters["events"] += 1
        if pixels:
            counters["TES_positive_events"] += 1
            counters["raw_pixel_readouts"] += len(pixels)
            raw_total = math.fsum(float(record["energy_keV"]) for record in pixels.values())
            counters["raw_broad"] += int(BROAD[0] <= raw_total < BROAD[1])
            counters["raw_W2"] += int(W2[0] <= raw_total < W2[1])
            measured_hits: list[Any] = []
            for uid, record in sorted(pixels.items()):
                raw_energy = float(record["energy_keV"])
                measured_energy = float(rng.normal(raw_energy, RESPONSE_SIGMA_KEV))
                if measured_energy < MEASURED_PIXEL_THRESHOLD_KEV:
                    continue
                match = TES_RE.fullmatch(uid)
                if match is None:
                    raise RuntimeError(f"internal TES UID mismatch: {uid}")
                measured_hits.append(
                    SimpleNamespace(
                        x=float(record["wx"] / raw_energy),
                        y=float(record["wy"] / raw_energy),
                        z=float(record["wz"] / raw_energy),
                        e=measured_energy,
                        pixel_uid=uid,
                        layer=int(match.group("layer")),
                    )
                )
            counters["measured_pixel_readouts"] += len(measured_hits)
            measured_total = math.fsum(hit.e for hit in measured_hits)
            counters["measured_broad"] += int(BROAD[0] <= measured_total < BROAD[1])
            measured_w2 = W2[0] <= measured_total < W2[1]
            counters["measured_W2"] += int(measured_w2)
            if measured_w2:
                keep, classification = topology(measured_hits, step05, disk)
                topology_classes[classification] += 1
                for threshold in VETO_THRESHOLDS_KEV:
                    threshold_name = int(threshold)
                    active_pass = active_keV < threshold
                    counters[f"W2_active_pass_{threshold_name}"] += int(active_pass)
                    counters[f"W2_active_topology_pass_{threshold_name}"] += int(active_pass and keep)
        current_id = None
        pixels = {}
        active_keV = 0.0

    with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if header_geometry is None and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1]
            if header_seed is None and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            if line == "SE":
                flush()
                continue
            if line == "EN":
                en_count += 1
                continue
            if line.startswith("ID "):
                fields = line.split()
                if len(fields) not in (2, 3):
                    raise RuntimeError(f"malformed phase02 ID: {job['job_id']}: {line}")
                first = int(fields[1])
                second = first if len(fields) == 2 else int(fields[2])
                if first != second or first != next_id:
                    raise RuntimeError(f"phase02 ID sequence mismatch: {job['job_id']}: {line}")
                current_id = first
                next_id += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            counters["CC_HIT"] += 1
            fields = line.split()
            if len(fields) < 4:
                raise RuntimeError(f"malformed CC HIT: {job['job_id']}")
            volume = fields[2]
            kv = shared.parse_kv(fields[3:])
            if not REQUIRED_HIT_KV.issubset(kv):
                counters["CC_HIT_typed_missing"] += 1
                continue
            edep = float(kv["edep_keV"])
            x, y, z = (float(kv[key]) for key in ("x", "y", "z"))
            if edep < 0.0 or not all(math.isfinite(value) for value in (edep, x, y, z)):
                raise RuntimeError(f"invalid CC HIT numeric values: {job['job_id']}")
            match = TES_RE.fullmatch(volume)
            if match and edep > 0.0:
                counters["TES_steps"] += 1
                record = pixels.setdefault(volume, {"energy_keV": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0})
                record["energy_keV"] += edep
                record["wx"] += edep * x
                record["wy"] += edep * y
                record["wz"] += edep * z
            elif volume in exact_active and edep > 0.0:
                active_keV += edep
                active_observed.add(volume)
    flush()

    if counters["events"] != int(job["triggers"]) or en_count != 1:
        raise RuntimeError(f"phase02 scan framing mismatch: {job['job_id']}: events={counters['events']} EN={en_count}")
    if counters["CC_HIT_typed_missing"]:
        raise RuntimeError(f"phase02 typed CC HIT fields missing: {job['job_id']}: {counters['CC_HIT_typed_missing']}")
    expected_geometry = Path(str(receipt["minimal_sim_check"]["geometry"])).resolve()
    observed_geometry = Path(str(header_geometry or "/__missing_geometry__")).resolve()
    if observed_geometry != expected_geometry or header_seed != int(job["seed"]):
        raise RuntimeError(f"phase02 SIM geometry/seed drift: {job['job_id']}")

    row: dict[str, Any] = {
        "job_id": job["job_id"],
        "geometry": geometry,
        "family": family,
        "events": int(counters["events"]),
        "included_ground_activity_Bq": weight["included_ground_activity_Bq"],
        "known_holdout_activity_Bq": weight["known_holdout_activity_Bq"],
        "known_holdout_activity_fraction": weight["known_holdout_activity_fraction"],
        "unknown_activity_state_count": weight["unknown_activity_state_count"],
        "event_weight_cps": weight["event_weight_cps"],
        "equivalent_time_s": weight["equivalent_time_s"],
        "CC_HIT": int(counters["CC_HIT"]),
        "TES_steps": int(counters["TES_steps"]),
        "TES_positive_events": int(counters["TES_positive_events"]),
        "raw_pixel_readouts": int(counters["raw_pixel_readouts"]),
        "measured_pixel_readouts": int(counters["measured_pixel_readouts"]),
        "source_manifest": weight["source_manifest"],
        "source_manifest_sha256": weight["source_manifest_sha256"],
    }
    for name in (
        "raw_broad",
        "measured_broad",
        "raw_W2",
        "measured_W2",
        "W2_active_pass_50",
        "W2_active_pass_70",
        "W2_active_pass_80",
        "W2_active_topology_pass_50",
        "W2_active_topology_pass_70",
        "W2_active_topology_pass_80",
    ):
        count = int(counters[name])
        row[f"{name}_count"] = count
        row[f"{name}_rate_cps"] = count * float(weight["event_weight_cps"])
        row[f"{name}_poisson_RSE"] = None if count == 0 else 1.0 / math.sqrt(count)
        row[f"{name}_zero_count_95_upper_rate_cps"] = (
            ZERO_COUNT_95_UPPER_MEAN * float(weight["event_weight_cps"]) if count == 0 else None
        )
    return row, topology_classes, active_observed


def scan(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    step05, disk = load_step05()
    receipts_by_id = {str(receipt["job"]["job_id"]): receipt for receipt in receipts}
    rows: list[dict[str, Any]] = []
    topology_rows: list[dict[str, Any]] = []
    active_seen = {geometry: set() for geometry in GEOMETRIES}
    for geometry in GEOMETRIES:
        rng = np.random.default_rng(RESPONSE_SEED)
        for family in EXPECTED_FAMILIES:
            job_id = f"delayed02_{family}_{geometry}"
            receipt = receipts_by_id[job_id]
            weight = source_weight(receipt["job"])
            row, classes, observed = analyze_job(receipt, weight, rng, step05, disk)
            rows.append(row)
            active_seen[geometry].update(observed)
            for classification, count in sorted(classes.items()):
                topology_rows.append(
                    {
                        "geometry": geometry,
                        "family": family,
                        "classification": classification,
                        "measured_W2_events": int(count),
                        "rate_cps": int(count) * float(weight["event_weight_cps"]),
                    }
                )

    geometry_summary: dict[str, Any] = {}
    for geometry in GEOMETRIES:
        subset = [row for row in rows if row["geometry"] == geometry]
        counts: dict[str, int] = {}
        rates: dict[str, float] = {}
        for name in (
            "raw_broad",
            "measured_broad",
            "raw_W2",
            "measured_W2",
            "W2_active_pass_50",
            "W2_active_pass_70",
            "W2_active_pass_80",
            "W2_active_topology_pass_50",
            "W2_active_topology_pass_70",
            "W2_active_topology_pass_80",
        ):
            counts[name] = sum(int(row[f"{name}_count"]) for row in subset)
            rates[name] = math.fsum(float(row[f"{name}_rate_cps"]) for row in subset)
        geometry_summary[geometry] = {
            "jobs": len(subset),
            "events": sum(int(row["events"]) for row in subset),
            "included_ground_activity_Bq": math.fsum(float(row["included_ground_activity_Bq"]) for row in subset),
            "known_holdout_activity_Bq": math.fsum(float(row["known_holdout_activity_Bq"]) for row in subset),
            "counts": counts,
            "rates_cps": rates,
            "active_blocks_observed": sorted(active_seen[geometry]),
        }
    return {
        "rows": rows,
        "topology_rows": topology_rows,
        "geometry": geometry_summary,
        "raw_scan": {
            "jobs": len(rows),
            "events": sum(int(row["events"]) for row in rows),
            "CC_HIT": sum(int(row["CC_HIT"]) for row in rows),
            "TES_steps": sum(int(row["TES_steps"]) for row in rows),
            "TES_positive_events": sum(int(row["TES_positive_events"]) for row in rows),
        },
        "step05": {
            "implementation": rel(STEP05_IMPLEMENTATION),
            "implementation_sha256": sha256_file(STEP05_IMPLEMENTATION),
            "side_entry_bridge": rel(STEP09_SUMMARY),
            "side_entry_bridge_sha256": sha256_file(STEP09_SUMMARY),
            "reject_policy": "keep",
            "MAX_ENUM_HITS": int(step05.MAX_ENUM_HITS),
            "N_CONE_SAMPLES": int(step05.N_CONE_SAMPLES),
            "disk": {
                "center_cm": [float(value) for value in disk["center_cm"]],
                "normal": [float(value) for value in disk["normal"]],
                "radius_cm": float(disk["radius_cm"]),
            },
        },
    }


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase02 delayed detector-response screening",
        "",
        f"Status: `{summary['status']}`",
        "",
        "The 12 terminal-PASS delayed SIMs were read with the M05 pixel-response and baseline Step05 side-entry topology chain. This is a six-family, ground-state-transport subset with explicit excited-state holdouts; it is not full delayed or paper closure.",
        "",
        "## Method",
        "",
        "TES deposits are aggregated by event and physical pixel, independently smeared with 0.420 keV FWHM using response seed 26071301, and measured pixels below 0.3 keV are discarded. W2 is `[510.58,511.42)` keV. Active veto uses exact blocks at 50/70/80 keV; native detector thresholds are unchanged. Baseline topology uses the retained Step05 side-entry disk with `reject_policy=keep`.",
        "",
        "| Geometry | Events | Measured W2 | Active pass 50/70/80 | Baseline topology pass 50/70/80 |",
        "|---|---:|---:|---:|---:|",
    ]
    for geometry in GEOMETRIES:
        row = summary["geometry"][geometry]
        count = row["counts"]
        lines.append(
            f"| {geometry} | {row['events']:,} | {count['measured_W2']} | "
            f"{count['W2_active_pass_50']}/{count['W2_active_pass_70']}/{count['W2_active_pass_80']} | "
            f"{count['W2_active_topology_pass_50']}/{count['W2_active_topology_pass_70']}/{count['W2_active_topology_pass_80']} |"
        )
    lines.extend(
        [
            "",
            "Rates are summed as `selected events × included_ground_activity_Bq / 1,000,000` separately by family. The reported sum excludes omitted e+/μ+ jobs and every non-zero-excitation holdout, so it must not be described as the complete delayed background.",
            "",
            "S3d-O8 uses exactly three BGO and three plastic volumes. Broad substring predicates are not used because they can admit mechanical BGO/active-shield names.",
            "",
        ]
    )
    return "\n".join(lines)


def build_payloads(scan_result: dict[str, Any], terminal_summary: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    summary = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__PHASE02_SIX_FAMILY_DELAYED_RESPONSE_PARTIAL_SCREENING",
        "terminal_authority": {
            "path": rel(EXPECTED_TERMINAL_SUMMARY),
            "sha256": sha256_file(EXPECTED_TERMINAL_SUMMARY),
            "status": terminal_summary["status"],
            "completed_jobs": terminal_summary["completed"],
            "coverage_status": terminal_summary["coverage_status"],
        },
        "method": {
            "response_seed_scope": "reset once per geometry; jobs ordered p,n,alpha,gamma,eminus,muminus; event ID then pixel UID",
            "response_seed": RESPONSE_SEED,
            "response_FWHM_keV": shared.M05_RESPONSE_FWHM_KEV,
            "response_sigma_keV": RESPONSE_SIGMA_KEV,
            "measured_pixel_discard_below_keV": MEASURED_PIXEL_THRESHOLD_KEV,
            "W2_keV_half_open": list(W2),
            "offline_active_veto_thresholds_keV": list(VETO_THRESHOLDS_KEV),
            "Mass_exact_active_whitelist": sorted(shared.MASS_ACTIVE),
            "S3d_O8_exact_active_whitelist": sorted(shared.O8_ACTIVE),
            "native_detector_thresholds_changed": False,
            "topology": scan_result["step05"],
            "rate_estimator": "selected events × included_ground_activity_Bq / 1,000,000 within family, summed across six included families",
        },
        "raw_scan": scan_result["raw_scan"],
        "geometry": scan_result["geometry"],
        "authority_boundary": {
            "included": "paired p,n,alpha,gamma,eminus,muminus phase02 ground-state exact-position delayed transport",
            "excluded": [
                "eplus and muplus prepared jobs",
                "every non-zero-excitation state held out by the installed PointSource syntax",
                "unknown activity states",
                "prompt background",
                "complete delayed response",
                "mission sensitivity and final M05 rate closure",
                "final structure ranking and geometry promotion",
            ],
            "historical_factor_1000_rates_used": False,
            "partial_or_staging_SIM_opened": False,
        },
    }
    fields = [
        "job_id",
        "geometry",
        "family",
        "events",
        "included_ground_activity_Bq",
        "known_holdout_activity_Bq",
        "known_holdout_activity_fraction",
        "unknown_activity_state_count",
        "event_weight_cps",
        "equivalent_time_s",
        "CC_HIT",
        "TES_steps",
        "TES_positive_events",
        "raw_pixel_readouts",
        "measured_pixel_readouts",
        "source_manifest",
        "source_manifest_sha256",
    ]
    for name in (
        "raw_broad",
        "measured_broad",
        "raw_W2",
        "measured_W2",
        "W2_active_pass_50",
        "W2_active_pass_70",
        "W2_active_pass_80",
        "W2_active_topology_pass_50",
        "W2_active_topology_pass_70",
        "W2_active_topology_pass_80",
    ):
        fields.extend([f"{name}_count", f"{name}_rate_cps", f"{name}_poisson_RSE", f"{name}_zero_count_95_upper_rate_cps"])
    payloads = {
        "summary.json": json_payload(summary),
        "delayed_observables.csv": csv_payload(scan_result["rows"], fields),
        "topology_classes.csv": csv_payload(
            scan_result["topology_rows"],
            ["geometry", "family", "classification", "measured_W2_events", "rate_cps"],
        ),
        "REPORT.md": report_markdown(summary).encode("utf-8"),
    }
    return payloads, summary


def publish_write_once(payloads: dict[str, bytes]) -> dict[str, Any]:
    output_collision_check()
    OUTPUT.mkdir(parents=False, exist_ok=False)
    staged: list[tuple[Path, Path, bytes]] = []
    for name, payload in payloads.items():
        partial = OUTPUT / f"{name}.partial"
        target = OUTPUT / name
        with partial.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if partial.stat().st_size != len(payload) or sha256_file(partial) != sha256_bytes(payload):
            raise RuntimeError(f"staged analysis payload mismatch: {partial}")
        staged.append((partial, target, payload))
    for partial, target, _payload in staged:
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
        "terminal_summary": {"path": rel(EXPECTED_TERMINAL_SUMMARY), "sha256": sha256_file(EXPECTED_TERMINAL_SUMMARY)},
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
        raise RuntimeError("staged manifest mismatch")
    os.replace(partial, target)
    directory_fd = os.open(OUTPUT, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {**manifest, "manifest_sha256": sha256_file(target), "manifest_bytes": target.stat().st_size}


def check() -> tuple[dict[str, Any], int]:
    output_collision_check()
    _plan, by_id = validate_plan()
    selected_staging_paths_present = sum(
        (ROOT / str(by_id[job_id]["attempt_partial_dir"])).exists() for job_id in expected_job_ids()
    )
    base = {
        "expected_terminal_summary": rel(EXPECTED_TERMINAL_SUMMARY),
        "expected_jobs": EXPECTED_JOB_COUNT,
        "expected_events": EXPECTED_EVENT_COUNT,
        "expected_families": list(EXPECTED_FAMILIES),
        "selected_staging_paths_present": selected_staging_paths_present,
        "staging_paths_opened": False,
        "SIM_opened": False,
        "writes": False,
        "response_seed": RESPONSE_SEED,
        "Mass_exact_active_blocks": len(shared.MASS_ACTIVE),
        "S3d_O8_exact_active_blocks": len(shared.O8_ACTIVE),
    }
    if not EXPECTED_TERMINAL_SUMMARY.is_file():
        return {
            "status": "PASS__DELAYED_RESPONSE_READER_READY__AWAITING_PHASE02_12JOB_TERMINAL_SUMMARY",
            "terminal_ready": False,
            **base,
        }, 0
    try:
        receipts, terminal = validate_terminal_summary()
    except RuntimeError as error:
        return {
            "status": "BLOCKED__PHASE02_TERMINAL_SUMMARY_NOT_ANALYSIS_ELIGIBLE",
            "terminal_ready": False,
            "error": str(error),
            **base,
        }, 2
    return {
        "status": "PASS__DELAYED_RESPONSE_READER_TERMINAL_GATE_READY",
        "terminal_ready": True,
        "selected_receipts": len(receipts),
        "terminal_status": terminal["status"],
        "terminal_summary_sha256": sha256_file(EXPECTED_TERMINAL_SUMMARY),
        **base,
    }, 0


def self_test() -> dict[str, Any]:
    assert expected_summary_digest() == "59ff7d29ca6e"
    assert len(expected_job_ids()) == 12 and len(set(expected_job_ids())) == 12
    assert "BGO_S3D_O8_FullWrap_BottomCap_30mm" in shared.O8_ACTIVE
    assert "BGO_S3D_O8_FullWrap_BottomCap_30mm_mechanical" not in shared.O8_ACTIVE
    assert "CsI_Side_Segment_00" in shared.MASS_ACTIVE
    rng1 = np.random.default_rng(RESPONSE_SEED)
    rng2 = np.random.default_rng(RESPONSE_SEED)
    assert float(rng1.normal(511.0, RESPONSE_SIGMA_KEV)) == float(rng2.normal(511.0, RESPONSE_SIGMA_KEV))
    assert topology([SimpleNamespace(e=511.0)], SimpleNamespace(MAX_ENUM_HITS=6), {}) == (True, "single")
    assert path_is_staging(Path("x/.attempt01.partial/y.sim.gz"))
    assert not path_is_staging(Path("x/attempt01/y.sim.gz"))
    return {
        "status": "PASS__PHASE02_DELAYED_RESPONSE_STATIC_SELF_TEST",
        "tests": 9,
        "expected_jobs": EXPECTED_JOB_COUNT,
        "expected_events": EXPECTED_EVENT_COUNT,
        "expected_terminal_summary": rel(EXPECTED_TERMINAL_SUMMARY),
        "SIM_opened": False,
        "staging_paths_opened": False,
        "transport_launched": False,
        "writes": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--self-test", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check:
        payload, returncode = check()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return returncode

    output_collision_check()
    receipts, terminal = validate_terminal_summary()
    scan_result = scan(receipts)
    if scan_result["raw_scan"]["jobs"] != EXPECTED_JOB_COUNT or scan_result["raw_scan"]["events"] != EXPECTED_EVENT_COUNT:
        raise RuntimeError(f"phase02 response scan coverage drift: {scan_result['raw_scan']}")
    payloads, summary = build_payloads(scan_result, terminal)
    manifest = publish_write_once(payloads)
    print(
        json.dumps(
            {
                "status": "PASS__PHASE02_DELAYED_RESPONSE_ANALYSIS_PUBLISHED",
                "analysis_status": summary["status"],
                "output": rel(OUTPUT),
                "raw_scan": summary["raw_scan"],
                "geometry": summary["geometry"],
                "manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
