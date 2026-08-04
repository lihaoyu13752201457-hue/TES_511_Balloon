#!/usr/bin/env python3
"""Prepare/audit matched S3c-C0 and S3d f10m-A1 signal replays."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _s3d_replay_common import (
    AuditError,
    DATA,
    ROOT,
    S3C_GEOMETRY_SETUP,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    canonicalize_source,
    cosima_environment,
    existing_run_artifacts,
    geometry_header_matches,
    rel,
    run_cosima,
    safe_write_json,
    safe_write_text,
    selection_contract,
    sha256,
    sim_header,
    source_run_name,
    source_scalar,
)


REFERENCE_RUN_NAME = "Opticsim_laue_f10m_a1_geo_opt_s1_bpe_w5_fullstat_v1_signal"
REFERENCE_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step09_focus_geo_opt_s1_bpe_w5_fullstat_v1"
)
REFERENCE_SOURCE = REFERENCE_RUN_DIR / f"{REFERENCE_RUN_NAME}.source"
REFERENCE_TRANSPORT_MANIFEST = (
    ROOT
    / "engineering/geometry_optimization_20260704/03_step05_detector_response_20260706"
    / "signal_transport_manifest.json"
)
BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
EVENTLIST = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists"
    / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)

TRIGGERS = 37_194
SEED = 260616
CONFIRMATION = "MATCHED_S3C_C0_AND_S3D_O9_SIGNAL37194"
MANIFEST = DATA / "s3d_signal_replay_manifest.json"


BRANCHES: dict[str, dict[str, Any]] = {
    "s3c_c0": {
        "label": "S3c-C0",
        "run_name": "Opticsim_laue_f10m_a1_s3c_c0_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3c_c0_f10m_a1_signal_replay_37194_matched_20260712"
        ),
        "geometry": S3C_GEOMETRY_SETUP,
    },
    "s3d_o9": {
        "label": "S3d-O9",
        "run_name": "Opticsim_laue_f10m_a1_s3d_o9_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3d_o9_f10m_a1_signal_replay_37194_20260712"
        ),
        "geometry": S3D_GEOMETRY_SETUP,
    },
}
for _branch in BRANCHES.values():
    _branch["source"] = _branch["run_dir"] / f"{_branch['run_name']}.source"
    _branch["prefix"] = _branch["run_dir"] / _branch["run_name"]
    _branch["log"] = _branch["run_dir"] / f"cosima_{_branch['run_name']}.log"
    _branch["sim"] = _branch["run_dir"] / f"{_branch['run_name']}.inc1.id1.sim.gz"


def eventlist_audit() -> dict[str, Any]:
    if not EVENTLIST.is_file():
        raise AuditError(f"retained EventList is missing: {rel(EVENTLIST)}")
    count = 0
    first_id: int | None = None
    last_id: int | None = None
    sequential = True
    min_energy = float("inf")
    max_energy = float("-inf")
    column_counts: set[int] = set()
    with EVENTLIST.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            column_counts.add(len(fields))
            if len(fields) < 2:
                raise AuditError(f"malformed EventList row {count + 1}")
            event_id = int(fields[0])
            energy = float(fields[-1])
            if first_id is None:
                first_id = event_id
            if event_id != count:
                sequential = False
            last_id = event_id
            min_energy = min(min_energy, energy)
            max_energy = max(max_energy, energy)
            count += 1
    checks = {
        "rows": count,
        "first_id": first_id,
        "last_id": last_id,
        "zero_based_sequential_ids": sequential,
        "column_counts": sorted(column_counts),
        "energy_min_keV": min_energy,
        "energy_max_keV": max_energy,
        "sha256": sha256(EVENTLIST),
    }
    passed = (
        count == TRIGGERS
        and first_id == 0
        and last_id == TRIGGERS - 1
        and sequential
        and min_energy == 511.0
        and max_energy == 511.0
    )
    if not passed:
        raise AuditError(f"EventList authority audit failed: {checks}")
    return {"status": "PASS", **checks}


def build_source(branch: dict[str, Any]) -> str:
    text = REFERENCE_SOURCE.read_text(encoding="utf-8")
    if source_run_name(text) != REFERENCE_RUN_NAME:
        raise AuditError("reference focused-signal run label changed")
    lines = text.splitlines()
    if lines:
        lines[0] = f"# Matched f10m A1 focused EventList replay through {branch['label']}."
    if len(lines) > 1 and lines[1].startswith("# Replays"):
        lines[1] = "# C0 and S3d use identical EventList, trigger count, seed, physics, and later selection."
    text = "\n".join(lines) + "\n"
    text, n_geometry = re.subn(
        r"^Geometry\s+.*$",
        f"Geometry {rel(branch['geometry'])}",
        text,
        count=1,
        flags=re.M,
    )
    text = text.replace(REFERENCE_RUN_NAME, branch["run_name"])
    text, n_prefix = re.subn(
        rf"^{re.escape(branch['run_name'])}\.FileName\s+.*$",
        f"{branch['run_name']}.FileName {rel(branch['prefix'])}",
        text,
        count=1,
        flags=re.M,
    )
    if n_geometry != 1 or n_prefix != 1:
        raise AuditError(
            f"unexpected signal source patch counts for {branch['label']}: "
            f"geometry={n_geometry}, prefix={n_prefix}"
        )
    return text


def source_audit(text: str, branch: dict[str, Any], reference: str) -> dict[str, Any]:
    canonical = canonicalize_source(
        text,
        run_name=branch["run_name"],
        geometry=rel(branch["geometry"]),
        output_prefix=rel(branch["prefix"]),
    )
    ref_canonical = canonicalize_source(
        reference,
        run_name=REFERENCE_RUN_NAME,
        geometry=source_scalar(reference, "Geometry"),
        output_prefix=source_scalar(reference, f"{REFERENCE_RUN_NAME}.FileName"),
    )
    eventlist_directive = source_scalar(
        text, f"{branch['run_name']}_EventList.EventList"
    )
    checks = {
        "canonical_transport_directives_identical_to_reference": canonical == ref_canonical,
        "geometry": source_scalar(text, "Geometry"),
        "run_name": source_run_name(text),
        "seed": int(source_scalar(text, "Seed")),
        "triggers": int(source_scalar(text, f"{branch['run_name']}.Triggers")),
        "eventlist": eventlist_directive,
        "eventlist_matches_retained_authority": eventlist_directive == rel(EVENTLIST),
        "physics_em": source_scalar(text, "PhysicsListEM"),
        "physics_hd": source_scalar(text, "PhysicsListHD"),
        "discretize_hits": source_scalar(text, "DiscretizeHits"),
        "detector_time_constant": source_scalar(text, "DetectorTimeConstant"),
    }
    passed = (
        checks["canonical_transport_directives_identical_to_reference"]
        and checks["geometry"] == rel(branch["geometry"])
        and checks["run_name"] == branch["run_name"]
        and checks["seed"] == SEED
        and checks["triggers"] == TRIGGERS
        and checks["eventlist_matches_retained_authority"]
        and checks["physics_em"] == "LivermorePol"
        and checks["physics_hd"] == "qgsp-bic-hp"
        and checks["discretize_hits"] == "true"
        and checks["detector_time_constant"] == "1e-9"
    )
    if not passed:
        raise AuditError(f"signal source audit failed for {branch['label']}: {checks}")
    return {"status": "PASS", "checks": checks}


def prepare() -> dict[str, Any]:
    if not REFERENCE_SOURCE.is_file() or not REFERENCE_TRANSPORT_MANIFEST.is_file():
        raise AuditError("retained geometry-local focused-signal source authority is missing")
    geometry = audit_geometry_authority()
    env, env_evidence = cosima_environment()
    del env
    eventlist = eventlist_audit()
    reference = REFERENCE_SOURCE.read_text(encoding="utf-8")
    records: dict[str, Any] = {}
    canonical_by_branch: dict[str, str] = {}
    for key, branch in BRANCHES.items():
        text = build_source(branch)
        audit = source_audit(text, branch, reference)
        write_state = safe_write_text(branch["source"], text)
        artifacts = existing_run_artifacts(branch["run_dir"], {branch["source"]})
        header = sim_header(branch["sim"])
        if header.get("exists"):
            if not geometry_header_matches(header.get("geometry"), branch["geometry"]):
                raise AuditError(f"existing {branch['label']} signal SIM points at wrong geometry")
            if header.get("seed") != SEED:
                raise AuditError(f"existing {branch['label']} signal SIM has wrong seed")
        canonical_by_branch[key] = canonicalize_source(
            text,
            run_name=branch["run_name"],
            geometry=rel(branch["geometry"]),
            output_prefix=rel(branch["prefix"]),
        )
        records[key] = {
            "label": branch["label"],
            "run_name": branch["run_name"],
            "run_dir": rel(branch["run_dir"]),
            "geometry": rel(branch["geometry"]),
            "source": rel(branch["source"]),
            "source_sha256": sha256(branch["source"]),
            "source_write_state": "PRESENT_IDENTICAL",
            "log": rel(branch["log"]),
            "sim": rel(branch["sim"]),
            "source_audit": audit,
            "non_source_artifacts_in_run_dir": artifacts,
            "no_overwrite_ready": not artifacts,
            "sim_header": header,
        }
    matched = canonical_by_branch["s3c_c0"] == canonical_by_branch["s3d_o9"]
    if not matched:
        raise AuditError("C0 and S3d signal source contracts differ beyond geometry/run/output")
    all_ready = all(record["no_overwrite_ready"] for record in records.values())
    payload = {
        "status": (
            "PASS_DRY_RUN_READY_MATCHED_C0_S3D_NO_PRODUCTION_LAUNCHED"
            if all_ready
            else "AUDIT_EXISTING_OUTPUTS_PRESENT_NO_OVERWRITE"
        ),
        "claim_boundary": (
            "This prepares a fresh matched S3c-C0/S3d detector-transport comparison. "
            "No retained S3c-C0 37194-row signal transport existed; no acceptance result is claimed here."
        ),
        "reference_authority": {
            "source": rel(REFERENCE_SOURCE),
            "source_sha256": sha256(REFERENCE_SOURCE),
            "transport_manifest": rel(REFERENCE_TRANSPORT_MANIFEST),
            "bridge_summary": rel(BRIDGE_SUMMARY),
            "eventlist": rel(EVENTLIST),
            "eventlist_audit": eventlist,
        },
        "matched_contract": {
            "triggers": TRIGGERS,
            "seed": SEED,
            "physics_em": "LivermorePol",
            "physics_hd": "qgsp-bic-hp",
            "store_simulation_info": "all",
            "discretize_hits": True,
            "detector_time_constant_s": 1e-9,
            "canonical_sources_identical_except_geometry_run_output": matched,
            "selection": selection_contract(),
        },
        "geometry_authority": geometry,
        "megalib_environment": env_evidence,
        "branches": records,
        "execution": {
            "default_branch_order": ["s3c_c0", "s3d_o9"],
            "production_launched": False,
            "guarded_execute_command": (
                f"python3 {rel(Path(__file__))} --execute --confirm {CONFIRMATION}"
            ),
            "direct_cosima_commands": [
                f"/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima -s {SEED} {record['source']}"
                for record in records.values()
            ],
        },
        "result_contract": {
            "summary": rel(DATA / "s3d_signal_replay_summary.json"),
            "required_header_fields_per_branch": ["geometry", "seed", "SE", "ID"],
            "required_selection_fields_per_branch": (
                "W2 raw/active-veto/final counts and unit-EventList acceptance"
            ),
            "promotion_metric": "1 - (S3d final W2 acceptance / S3c-C0 final W2 acceptance)",
            "promotion_limit": 0.02,
            "status": "PENDING_MATCHED_TRANSPORT_NOT_ZERO",
        },
        "resource_estimate_from_retained_replays": {
            "cpu_seconds_per_branch": "28-31",
            "wall_time_sequential_both": "about 1 minute on one comparable CPU core",
            "compressed_sim_mb_per_branch": "23-24",
            "log_mb_per_branch": "about 8",
            "minimum_free_disk_guidance_mb": 100,
        },
    }
    manifest_state = safe_write_json(MANIFEST, payload)
    return {**payload, "manifest_write_state": manifest_state}


def audit_completed_branch(key: str) -> dict[str, Any]:
    branch = BRANCHES[key]
    header = sim_header(branch["sim"], count_events=True)
    checks = {
        "geometry_matches": geometry_header_matches(header.get("geometry"), branch["geometry"]),
        "seed_matches": header.get("seed") == SEED,
        "SE_matches": header.get("SE") == TRIGGERS,
        "ID_matches": header.get("ID") == TRIGGERS,
    }
    if not all(checks.values()):
        raise AuditError(f"completed {branch['label']} header/count audit failed: {header}, {checks}")
    return {"status": "PASS", "header": header, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="launch both matched full transports")
    parser.add_argument("--confirm", default="", help="must match the guarded comparison token")
    parser.add_argument("--audit-existing", action="store_true", help="scan both existing SIMs")
    args = parser.parse_args()
    try:
        if args.audit_existing:
            audit_geometry_authority()
            eventlist_audit()
            audits = {key: audit_completed_branch(key) for key in BRANCHES}
            print(json.dumps({"manifest": rel(MANIFEST), "branches": audits}, indent=2))
            return 0
        payload = prepare()
        if args.execute:
            if args.confirm != CONFIRMATION:
                raise AuditError(f"--confirm must exactly equal {CONFIRMATION}")
            completed: dict[str, Any] = {}
            for key in ("s3c_c0", "s3d_o9"):
                branch = BRANCHES[key]
                rc = run_cosima(
                    source=branch["source"],
                    log=branch["log"],
                    run_dir=branch["run_dir"],
                    allowed_preexisting={branch["source"]},
                    seed=SEED,
                )
                if rc != 0:
                    raise AuditError(
                        f"Cosima failed for {branch['label']} with return code {rc}; "
                        f"log retained at {rel(branch['log'])}"
                    )
                completed[key] = audit_completed_branch(key)
            print(json.dumps({"status": "PASS_MATCHED_TRANSPORT_HEADERS", "branches": completed}, indent=2))
            return 0
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "manifest": rel(MANIFEST),
                    "sources": {key: record["source"] for key, record in payload["branches"].items()},
                    "production_launched": False,
                },
                indent=2,
            )
        )
        return 0
    except AuditError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
