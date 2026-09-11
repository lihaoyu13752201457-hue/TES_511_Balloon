#!/usr/bin/env python3
"""M05 delayed-response reader for epsilon formal partial recovery0002.

The six p/n/alpha SIMs are eligible only after the independent append-only
``revalidation0001`` authority declares all six cells compatible.  Some valid
artifacts intentionally remain in preserved ``.attempt01.partial`` directories
after an over-strict first validator rejected tiny non-DECA fractions.  This
reader never moves or rewrites them: the revalidation row's explicit
``valid_artifact_path`` is the sole SIM binding.

The detector-response implementation is reused from the already reviewed
phase02 adapter: event/pixel TES summation, 0.420 keV FWHM Gaussian response,
measured-pixel <0.3 keV discard, W2=[510.58,511.42) keV, exact active-block
50/70/80 keV offline veto flags, and retained Step05 topology.  Output is
write-once partial delayed screening, never full delayed or paper closure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import analyze_batch0007_prompt_activation as shared
import analyze_phase02_delayed_response as mature


sys.dont_write_bytecode = True

ROOT = Path("/home/ubuntu/TES_511_Balloon")
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1"
RECOVERY_ROOT = (
    RUN_ROOT
    / "delayed_phase02/state_aware_exactpos_v1/spectrum_epsilon_formal_partial_recovery0002"
)
PLAN = RECOVERY_ROOT / "formal_partial_jobs.json"
REVALIDATION = RECOVERY_ROOT / "revalidation0001/formal_partial_revalidation.json"
OUTPUT = RUN_ROOT / "analysis_delayed_response_recovery0002_revalidation0001"

PASS_REVALIDATION = "PASS__REVALIDATION0001_SIX_CELL_DELAYED_PARTIAL_SCREENING_COMPATIBLE"
PASS_SOURCE = "PASS__GROUND_STATE_EXACT_POSITION_SOURCE_READY__NONZERO_STATES_FAIL_CLOSED"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("p", "n", "alpha")
TRIGGERS = 250_000
EPSILON_KEV = 1.0e-6
EXPECTED_JOB_IDS = {
    f"epsilon_formal_partial_{family}_{geometry}"
    for geometry in GEOMETRIES
    for family in FAMILIES
}


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if path.name.startswith(".") or path.name.endswith(".partial"):
        raise RuntimeError(f"refusing staging JSON authority: {path}")
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
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def csv_payload(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def output_collision_check() -> None:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError(f"write-once output collision: {OUTPUT}")


def plan_by_id() -> dict[str, dict[str, Any]]:
    plan = load_json(PLAN)
    if plan.get("status") != "READY__EPSILON_FORMAL_PARTIAL_SCREENING_NOT_LAUNCHED":
        raise RuntimeError(f"unexpected recovery plan status: {plan.get('status')}")
    if int(plan.get("triggers_per_job", -1)) != TRIGGERS:
        raise RuntimeError("recovery plan trigger count drift")
    if float(plan.get("epsilon_keV", -1.0)) != EPSILON_KEV:
        raise RuntimeError("recovery plan epsilon drift")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("recovery plan lacks jobs")
    by_id = {str(job["job_id"]): job for job in jobs}
    if set(by_id) != EXPECTED_JOB_IDS or len(by_id) != 6:
        raise RuntimeError(f"recovery plan cell drift: {sorted(by_id)}")
    for job in by_id.values():
        if int(job.get("triggers", -1)) != TRIGGERS:
            raise RuntimeError(f"job trigger drift: {job['job_id']}")
        if int(job.get("selected_position_blocks", -1)) != 10_000:
            raise RuntimeError(f"position-block drift: {job['job_id']}")
        if float(job.get("epsilon_keV", -1.0)) != EPSILON_KEV:
            raise RuntimeError(f"job epsilon drift: {job['job_id']}")
        closure = job.get("sum_flux_closure", {})
        if closure.get("status") != "PASS" or abs(float(closure.get("relative_difference", 1.0))) > 1e-12:
            raise RuntimeError(f"flux closure drift: {job['job_id']}")
    return by_id


def eligible_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve authority-bound SIM rows without opening any SIM."""
    by_id = plan_by_id()
    if not REVALIDATION.is_file():
        raise RuntimeError(f"independent revalidation authority absent: {REVALIDATION}")
    authority = load_json(REVALIDATION)
    if authority.get("status") != PASS_REVALIDATION:
        raise RuntimeError(f"independent revalidation not PASS: {authority.get('status')}")
    rows = authority.get("jobs")
    if not isinstance(rows, list) or len(rows) != 6:
        raise RuntimeError("revalidation authority must bind exactly six jobs")
    rows_by_id = {str(row["job_id"]): row for row in rows}
    if set(rows_by_id) != EXPECTED_JOB_IDS or len(rows_by_id) != 6:
        raise RuntimeError(f"revalidation cell drift: {sorted(rows_by_id)}")

    selected: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            job_id = f"epsilon_formal_partial_{family}_{geometry}"
            job, row = by_id[job_id], rows_by_id[job_id]
            if row.get("status") != "PASS":
                raise RuntimeError(f"revalidation row not PASS: {job_id}")
            if str(row.get("geometry")) != geometry or str(row.get("family")) != family:
                raise RuntimeError(f"revalidation identity drift: {job_id}")
            if int(row.get("seed", -1)) != int(job["seed"]):
                raise RuntimeError(f"revalidation seed drift: {job_id}")
            if row.get("sum_flux_closure_pass") is not True:
                raise RuntimeError(f"revalidation flux closure not PASS: {job_id}")
            if row.get("source_sha256_matches_plan") is not True:
                raise RuntimeError(f"revalidation source binding not PASS: {job_id}")
            if row.get("old_receipt_preserved") is not True or row.get("attempt_directory_stable") is not True:
                raise RuntimeError(f"preservation/stability binding not PASS: {job_id}")

            sim_path = (ROOT / str(row["valid_artifact_path"])).resolve()
            allowed = {
                (ROOT / str(job["published_sim"])).resolve(),
                (ROOT / str(job["expected_sim"])).resolve(),
            }
            if sim_path not in allowed or not sim_path.is_file():
                raise RuntimeError(f"valid artifact path not plan-bound/present: {job_id}: {sim_path}")
            source = (ROOT / str(row["source"])).resolve()
            if source != (ROOT / str(job["source"])).resolve() or not source.is_file():
                raise RuntimeError(f"revalidation source path drift: {job_id}")
            if sha256_file(source) != str(job["source_sha256"]):
                raise RuntimeError(f"source SHA drift: {job_id}")

            sim_check = row.get("sim_revalidation", {})
            if sim_check.get("status") != "PASS":
                raise RuntimeError(f"SIM revalidation not PASS: {job_id}")
            if int(sim_check.get("SE", -1)) != TRIGGERS or int(sim_check.get("ID", -1)) != TRIGGERS:
                raise RuntimeError(f"SIM event framing declaration drift: {job_id}")
            if int(sim_check.get("EN", -1)) != 1 or sim_check.get("gzip_eof_reached") is not True:
                raise RuntimeError(f"SIM EOF declaration drift: {job_id}")
            if sim_check.get("ID_both_columns_sequential_1_to_N") is not True or sim_check.get(
                "ID_exactly_two_integer_columns"
            ) is not True:
                raise RuntimeError(f"SIM ID declaration drift: {job_id}")
            if int(sim_check.get("IA_INIT_2MeV_artifact_count", -1)) != 0:
                raise RuntimeError(f"2 MeV fallback artifact declared: {job_id}")
            if int(sim_check.get("IA_INIT_lines", -1)) != TRIGGERS:
                raise RuntimeError(f"IA INIT coverage drift: {job_id}")
            if float(sim_check.get("IA_INIT_energy_min_keV", math.nan)) != 0.0 or float(
                sim_check.get("IA_INIT_energy_max_keV", math.nan)
            ) != 0.0:
                raise RuntimeError(f"IA INIT epsilon handling drift: {job_id}")
            spectral = sim_check.get("spectral_lines", [])
            if spectral != ["SpectralType Mono 1e-06"]:
                raise RuntimeError(f"spectral binding drift: {job_id}: {spectral}")

            selected.append({"job": job, "authority_row": row, "sim_path": sim_path})
    return selected, authority


def weight_for(selected: dict[str, Any]) -> dict[str, Any]:
    job = selected["job"]
    closure = job["sum_flux_closure"]
    activity = float(closure["original_50000_sum_flux_Bq"])
    if not math.isfinite(activity) or activity <= 0.0:
        raise RuntimeError(f"non-positive activity: {job['job_id']}")

    prepared = (ROOT / str(job["prepared_source"])).resolve()
    source_manifest = prepared.parent / "source_manifest.json"
    manifest = load_json(source_manifest)
    if manifest.get("status") != PASS_SOURCE:
        raise RuntimeError(f"prepared source manifest not PASS: {job['job_id']}")
    if str(manifest.get("geometry")) != str(job["geometry"]) or str(manifest.get("family")) != str(job["family"]):
        raise RuntimeError(f"prepared source cell drift: {job['job_id']}")
    manifest_activity = float(manifest.get("included_ground_activity_Bq", math.nan))
    if not math.isclose(activity, manifest_activity, rel_tol=1e-12, abs_tol=1e-9):
        raise RuntimeError(f"prepared/recovery activity drift: {job['job_id']}")
    return {
        "source_manifest": rel(source_manifest),
        "source_manifest_sha256": sha256_file(source_manifest),
        "included_ground_activity_Bq": activity,
        "event_weight_cps": activity / TRIGGERS,
        "equivalent_time_s": TRIGGERS / activity,
        "known_holdout_activity_Bq": float(manifest.get("known_holdout_activity_Bq", 0.0)),
        "known_holdout_activity_fraction": float(manifest.get("known_holdout_activity_fraction", 0.0)),
        "unknown_activity_state_count": int(manifest.get("unknown_activity_state_count", 0)),
    }


def run_scan(selected: list[dict[str, Any]]) -> dict[str, Any]:
    step05, disk = mature.load_step05()
    indexed = {
        (str(item["job"]["geometry"]), str(item["job"]["family"])): item
        for item in selected
    }
    rows: list[dict[str, Any]] = []
    topology_rows: list[dict[str, Any]] = []
    active_seen = {geometry: set() for geometry in GEOMETRIES}
    for geometry in GEOMETRIES:
        rng = np.random.default_rng(shared.M05_RESPONSE_SEED)
        for family in FAMILIES:
            selected_item = indexed[(geometry, family)]
            job = selected_item["job"]
            authority_row = selected_item["authority_row"]
            weight = weight_for(selected_item)
            pseudo_receipt = {
                "job": {
                    "job_id": job["job_id"],
                    "geometry": geometry,
                    "family": family,
                    "triggers": TRIGGERS,
                    "seed": int(job["seed"]),
                },
                "published_sim": rel(selected_item["sim_path"]),
                "minimal_sim_check": {"geometry": str(job["expected_geometry"])},
            }
            row, topology_classes, observed = mature.analyze_job(
                pseudo_receipt, weight, rng, step05, disk
            )
            sim_validation = authority_row["sim_revalidation"]
            row.update(
                {
                    "artifact_state": authority_row.get("artifact_state"),
                    "valid_artifact_path": rel(selected_item["sim_path"]),
                    "events_with_IA_DECA": int(sim_validation["events_with_IA_DECA"]),
                    "events_without_IA_DECA": TRIGGERS - int(sim_validation["events_with_IA_DECA"]),
                    "IA_DECA_coverage_fraction": int(sim_validation["events_with_IA_DECA"]) / TRIGGERS,
                }
            )
            rows.append(row)
            active_seen[geometry].update(observed)
            for classification, count in sorted(topology_classes.items()):
                topology_rows.append(
                    {
                        "geometry": geometry,
                        "family": family,
                        "classification": classification,
                        "measured_W2_events": int(count),
                        "rate_cps": int(count) * float(weight["event_weight_cps"]),
                    }
                )

    metrics = (
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
    )
    geometry_summary: dict[str, Any] = {}
    for geometry in GEOMETRIES:
        subset = [row for row in rows if row["geometry"] == geometry]
        geometry_summary[geometry] = {
            "jobs": len(subset),
            "events": sum(int(row["events"]) for row in subset),
            "events_with_IA_DECA": sum(int(row["events_with_IA_DECA"]) for row in subset),
            "events_without_IA_DECA": sum(int(row["events_without_IA_DECA"]) for row in subset),
            "included_ground_activity_Bq": math.fsum(float(row["included_ground_activity_Bq"]) for row in subset),
            "known_holdout_activity_Bq": math.fsum(float(row["known_holdout_activity_Bq"]) for row in subset),
            "counts": {name: sum(int(row[f"{name}_count"]) for row in subset) for name in metrics},
            "rates_cps": {
                name: math.fsum(float(row[f"{name}_rate_cps"]) for row in subset)
                for name in metrics
            },
            "active_blocks_observed": sorted(active_seen[geometry]),
        }
    return {
        "rows": rows,
        "topology_rows": topology_rows,
        "geometry": geometry_summary,
        "raw_scan": {
            "jobs": len(rows),
            "events": sum(int(row["events"]) for row in rows),
            "events_with_IA_DECA": sum(int(row["events_with_IA_DECA"]) for row in rows),
            "events_without_IA_DECA": sum(int(row["events_without_IA_DECA"]) for row in rows),
            "CC_HIT": sum(int(row["CC_HIT"]) for row in rows),
            "TES_steps": sum(int(row["TES_steps"]) for row in rows),
            "TES_positive_events": sum(int(row["TES_positive_events"]) for row in rows),
        },
        "step05": {
            "implementation": rel(mature.STEP05_IMPLEMENTATION),
            "implementation_sha256": sha256_file(mature.STEP05_IMPLEMENTATION),
            "side_entry_bridge": rel(mature.STEP09_SUMMARY),
            "side_entry_bridge_sha256": sha256_file(mature.STEP09_SUMMARY),
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
        "# Recovery0002 delayed-response partial screening",
        "",
        f"Status: `{summary['status']}`",
        "",
        "The independently revalidated p/n/alpha epsilon delayed SIMs were actually parsed through the M05 detector-response and retained Step05 topology chain. This is a three-family positional-subsample screen, not complete delayed or paper closure.",
        "",
        "| Geometry | Events | DECA coverage | Measured W2 | Active pass 50/70/80 | Topology pass 50/70/80 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for geometry in GEOMETRIES:
        row = summary["geometry"][geometry]
        count = row["counts"]
        deca = row["events_with_IA_DECA"] / row["events"]
        lines.append(
            f"| {geometry} | {row['events']:,} | {deca:.6%} | {count['measured_W2']} | "
            f"{count['W2_active_pass_50']}/{count['W2_active_pass_70']}/{count['W2_active_pass_80']} | "
            f"{count['W2_active_topology_pass_50']}/{count['W2_active_topology_pass_70']}/{count['W2_active_topology_pass_80']} |"
        )
    lines.extend(
        [
            "",
            "TES deposits are summed by event and exact physical pixel, independently smeared with 0.420 keV FWHM, and measured hits below 0.3 keV are discarded. W2 is `[510.58,511.42)` keV. The 50/70/80 keV active flags use exact whitelists; native detector thresholds are unchanged.",
            "",
            "Rates use `selected events × full cell ground-state activity / 250,000`. All triggers remain in the denominator, including the small no-DECA fraction. The 10,000-position stride subsample (with flux ×5 closure) adds positional-subsampling uncertainty not represented by event-count Poisson RSE.",
            "",
            "Only p/n/alpha ground-state activity is included. gamma/e-/mu-/e+/mu+, explicit non-ground-state holdouts, unknown states, full delayed response, mission sensitivity, final paper-rate closure, structure ranking, and geometry promotion remain outside this authority.",
            "",
        ]
    )
    return "\n".join(lines)


def build_payloads(scan: dict[str, Any], authority: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    summary = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__RECOVERY0002_THREE_FAMILY_DELAYED_RESPONSE_PARTIAL_SCREENING",
        "revalidation_authority": {
            "path": rel(REVALIDATION),
            "sha256": sha256_file(REVALIDATION),
            "status": authority["status"],
            "jobs": len(authority["jobs"]),
        },
        "method": {
            "mature_adapter": rel(Path(mature.__file__)),
            "mature_adapter_sha256": sha256_file(Path(mature.__file__)),
            "response_seed_scope": "reset once per geometry; family order p,n,alpha; event ID then pixel UID",
            "response_seed": shared.M05_RESPONSE_SEED,
            "response_FWHM_keV": shared.M05_RESPONSE_FWHM_KEV,
            "response_sigma_keV": shared.M05_RESPONSE_SIGMA_KEV,
            "measured_pixel_discard_below_keV": shared.MEASURED_PIXEL_THRESHOLD_KEV,
            "W2_keV_half_open": list(shared.W2),
            "offline_active_veto_thresholds_keV": list(shared.VETO_THRESHOLDS_KEV),
            "Mass_exact_active_whitelist": sorted(shared.MASS_ACTIVE),
            "S3d_O8_exact_active_whitelist": sorted(shared.O8_ACTIVE),
            "native_detector_thresholds_changed": False,
            "topology": scan["step05"],
            "rate_estimator": "selected events × original 50,000-position included ground-state activity / 250,000 triggers within family",
            "no_DECA_denominator_policy": "retain all source triggers in denominator; no-DECA events contribute zero selected response",
        },
        "raw_scan": scan["raw_scan"],
        "geometry": scan["geometry"],
        "authority_boundary": {
            "included": "paired p,n,alpha corrected epsilon delayed transport; 10,000 exact-position stride subset per cell with flux x5 closure",
            "excluded": [
                "gamma, eminus, muminus, eplus, and muplus delayed transport",
                "all explicit non-zero-excitation and unknown-state holdouts",
                "positional-subsampling uncertainty beyond event-count Poisson RSE",
                "complete delayed response and final M05 paper-rate closure",
                "mission sensitivity, structure ranking, and geometry promotion",
            ],
            "historical_2MeV_fallback_SIM_opened": False,
            "historical_factor_1000_rates_used": False,
            "artifacts_moved_or_modified": False,
            "preserved_partial_artifacts_read": sum(
                str(row["valid_artifact_path"]).find(".attempt01.partial") >= 0 for row in authority["jobs"]
            ),
        },
    }
    fields = [
        "job_id", "geometry", "family", "events", "events_with_IA_DECA",
        "events_without_IA_DECA", "IA_DECA_coverage_fraction", "artifact_state",
        "valid_artifact_path", "included_ground_activity_Bq", "known_holdout_activity_Bq",
        "known_holdout_activity_fraction", "unknown_activity_state_count", "event_weight_cps",
        "equivalent_time_s", "CC_HIT", "TES_steps", "TES_positive_events",
        "raw_pixel_readouts", "measured_pixel_readouts", "source_manifest", "source_manifest_sha256",
    ]
    for name in (
        "raw_broad", "measured_broad", "raw_W2", "measured_W2",
        "W2_active_pass_50", "W2_active_pass_70", "W2_active_pass_80",
        "W2_active_topology_pass_50", "W2_active_topology_pass_70", "W2_active_topology_pass_80",
    ):
        fields.extend(
            [f"{name}_count", f"{name}_rate_cps", f"{name}_poisson_RSE", f"{name}_zero_count_95_upper_rate_cps"]
        )
    payloads = {
        "summary.json": json_payload(summary),
        "delayed_observables.csv": csv_payload(scan["rows"], fields),
        "topology_classes.csv": csv_payload(
            scan["topology_rows"],
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
        partial, target = OUTPUT / f"{name}.partial", OUTPUT / name
        with partial.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if partial.stat().st_size != len(payload) or sha256_file(partial) != sha256_bytes(payload):
            raise RuntimeError(f"staged payload mismatch: {partial}")
        staged.append((partial, target, payload))
    for partial, target, _payload in staged:
        os.replace(partial, target)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__WRITE_ONCE_ATOMIC_PUBLICATION",
        "canonical_directory": rel(OUTPUT),
        "analysis_code": {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "revalidation_authority": {"path": rel(REVALIDATION), "sha256": sha256_file(REVALIDATION)},
        "members": [
            {"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)}
            for name, payload in sorted(payloads.items())
        ],
    }
    encoded = json_payload(manifest)
    partial, target = OUTPUT / "MANIFEST.json.partial", OUTPUT / "MANIFEST.json"
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
    plan_by_id()
    base = {
        "expected_jobs": 6,
        "expected_events": 1_500_000,
        "expected_families": list(FAMILIES),
        "expected_revalidation": rel(REVALIDATION),
        "SIM_opened": False,
        "writes": False,
    }
    if not REVALIDATION.is_file():
        return {
            "status": "PASS__RECOVERY0002_DELAYED_READER_READY__AWAITING_REVALIDATION0001",
            "terminal_ready": False,
            **base,
        }, 0
    try:
        rows, authority = eligible_rows()
    except RuntimeError as error:
        return {
            "status": "BLOCKED__RECOVERY0002_REVALIDATION_NOT_ANALYSIS_ELIGIBLE",
            "terminal_ready": False,
            "error": str(error),
            **base,
        }, 2
    return {
        "status": "PASS__RECOVERY0002_DELAYED_READER_TERMINAL_GATE_READY",
        "terminal_ready": True,
        "selected_rows": len(rows),
        "revalidation_status": authority["status"],
        "revalidation_sha256": sha256_file(REVALIDATION),
        **base,
    }, 0


def self_test() -> dict[str, Any]:
    assert len(EXPECTED_JOB_IDS) == 6
    assert shared.W2 == (510.58, 511.42)
    assert shared.MEASURED_PIXEL_THRESHOLD_KEV == 0.3
    assert len(shared.O8_ACTIVE) == 6
    assert "BGO_S3D_O8_FullWrap_BottomCap_30mm_mechanical" not in shared.O8_ACTIVE
    assert mature.topology([], object(), {}) == (True, "single")
    return {
        "status": "PASS__RECOVERY0002_DELAYED_RESPONSE_STATIC_SELF_TEST",
        "tests": 6,
        "SIM_opened": False,
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
    selected, authority = eligible_rows()
    scan = run_scan(selected)
    if scan["raw_scan"]["jobs"] != 6 or scan["raw_scan"]["events"] != 1_500_000:
        raise RuntimeError(f"delayed-response scan coverage drift: {scan['raw_scan']}")
    payloads, summary = build_payloads(scan, authority)
    manifest = publish_write_once(payloads)
    print(
        json.dumps(
            {
                "status": "PASS__RECOVERY0002_DELAYED_RESPONSE_ANALYSIS_PUBLISHED",
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
