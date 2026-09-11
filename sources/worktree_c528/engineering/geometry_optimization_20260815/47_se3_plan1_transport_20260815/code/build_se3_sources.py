#!/usr/bin/env python3
"""Freeze Plan-1 jobs, seeds, and corrected-keV SE3 background cards."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any

from se3_plan1_common import (
    BASE_SOURCE_ROOT,
    CORRECTED_TOKEN,
    EVENTLIST,
    FAMILIES,
    FORBIDDEN_TOKEN,
    HANDOFF,
    HANDOFF_WORKTREE,
    M05_ROOT,
    MODES,
    PACKAGE_ROOT,
    PRIMARY_ROOT,
    PROFILE_ID,
    RUN_ROOT,
    S3D_SETUP,
    S3D_STATS_ROOT,
    SE3_SETUP,
    SHARDS,
    SOURCE_CONTRACT,
    SOURCE_WORKTREE,
    START_FREE_GATE_BYTES,
    DYNAMIC_RESERVE_BYTES,
    active_prefix,
    background_job_id,
    background_run_name,
    base_source,
    build_job_plan,
    derive_seed_plan,
    job_source_path,
    json_sha256,
    sha256,
    utc_now,
    validate_shards,
    write_csv_once,
    write_once_json,
    write_once_text,
)


SEED_META_WORDS = {
    "base", "stride", "count", "sha256", "digest", "hash", "policy",
    "rule", "formula", "status", "collision", "namespace", "ordinal",
}


def extract_seed_values(value: Any, *, context: bool = False) -> set[int]:
    result: set[int] = set()
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).lower().replace("-", "_")
            words = set(key.split("_"))
            is_seed_key = bool({"seed", "seeds"} & words)
            is_meta = bool(words & SEED_META_WORDS)
            result.update(extract_seed_values(child, context=(context or is_seed_key) and not is_meta))
    elif isinstance(value, list):
        for child in value:
            result.update(extract_seed_values(child, context=context))
    elif context and isinstance(value, int) and not isinstance(value, bool) and value > 0:
        result.add(value)
    return result


def referenced_small_json(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            result.update(referenced_small_json(child))
    elif isinstance(value, list):
        for child in value:
            result.update(referenced_small_json(child))
    elif isinstance(value, str) and value.endswith(".json"):
        result.add(value)
    return result


def resolve_authority_json(path_text: str) -> Path | None:
    path = Path(path_text)
    candidates = [path] if path.is_absolute() else [PRIMARY_ROOT / path, SOURCE_WORKTREE / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def collect_occupied_seeds() -> tuple[set[int], dict[str, Any]]:
    """Read JSON ledgers/receipts only; never touch SIM payloads."""
    config = json.loads((M05_ROOT / "analysis_inputs.json").read_text(encoding="utf-8"))
    queue: list[Path] = []
    for item in config["transport_inputs"]:
        path = resolve_authority_json(str(item["path"]))
        if path is None:
            raise FileNotFoundError(f"missing seed authority ledger: {item['path']}")
        queue.append(path)
    seen: set[Path] = set()
    occupied: set[int] = set()
    sizes: list[int] = []
    while queue:
        path = queue.pop()
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        size = path.stat().st_size
        if size > 20_000_000:
            raise RuntimeError(f"refusing oversized JSON seed authority: {path} ({size})")
        payload = json.loads(path.read_text(encoding="utf-8"))
        sizes.append(size)
        occupied.update(extract_seed_values(payload))
        for ref in referenced_small_json(payload):
            resolved = resolve_authority_json(ref)
            if resolved is not None and resolved.resolve() not in seen:
                queue.append(resolved)

    # Freeze previously used exact-position and delayed seeds from the compact
    # S3d statistics table as additional collision evidence.
    stats_csv = S3D_STATS_ROOT / "data/s3d_o8_particle_family_statistics.csv"
    with stats_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            occupied.add(int(row["delayed_source_sampling_seed"]))
            occupied.add(int(row["delayed_transport_seed"]))
    return occupied, {
        "status": "PASS",
        "policy": "SMALL_JSON_LEDGER_AND_RECEIPT_ONLY__NO_SIM_OPEN_OR_HASH",
        "authority_json_files": len(seen),
        "authority_json_bytes": sum(sizes),
        "largest_authority_json_bytes": max(sizes, default=0),
        "occupied_seed_count": len(occupied),
        "m05_input_config": str(M05_ROOT / "analysis_inputs.json"),
        "s3d_statistics_csv": str(stats_csv),
    }


def _unique_index(lines: list[str], predicate, label: str) -> int:
    indices = [index for index, line in enumerate(lines) if predicate(line)]
    if len(indices) != 1:
        raise RuntimeError(f"base source requires exactly one {label}, got {len(indices)}")
    return indices[0]


def patch_background_source(
    base_text: str,
    *,
    job_id: str,
    run_name: str,
    mode: str,
    seed: int,
    events: int,
) -> str:
    if mode not in MODES:
        raise ValueError(mode)
    lines = base_text.splitlines()
    geometry_i = _unique_index(lines, lambda x: x.strip().startswith("Geometry "), "Geometry")
    seed_i = _unique_index(lines, lambda x: x.strip().startswith("Seed "), "Seed")
    run_i = _unique_index(lines, lambda x: x.strip().startswith("Run "), "Run")
    decay_i = _unique_index(lines, lambda x: x.strip().startswith("DecayMode "), "DecayMode")
    _unique_index(lines, lambda x: x.strip() == "StoreSimulationInfo all", "StoreSimulationInfo all")
    _unique_index(lines, lambda x: x.strip() == "StoreIsotopes true", "StoreIsotopes true")
    old_run = lines[run_i].strip().split(maxsplit=1)[1]
    scoped = [index for index, line in enumerate(lines) if line.startswith(f"{old_run}.")]
    if len(scoped) != 23:  # Events, FileName, IsotopeProductionFile, 20 Source rows
        raise RuntimeError(f"unexpected run-scoped key count for {old_run}: {len(scoped)}")
    events_i = _unique_index(lines, lambda x: x.startswith(f"{old_run}.Events "), "Events")
    filename_i = _unique_index(lines, lambda x: x.startswith(f"{old_run}.FileName "), "FileName")
    isotope_i = _unique_index(
        lines, lambda x: x.startswith(f"{old_run}.IsotopeProductionFile "), "IsotopeProductionFile"
    )
    output_prefix = active_prefix(job_id)
    patched: list[str] = []
    for index, raw in enumerate(lines):
        if index == geometry_i:
            patched.append(f"Geometry {SE3_SETUP}")
        elif index == seed_i:
            patched.append(f"Seed {seed}")
        elif index == run_i:
            patched.append(f"Run {run_name}")
        elif index == decay_i and mode == "instant":
            continue
        elif index == events_i:
            patched.append(f"{run_name}.Events {events}")
        elif index == filename_i:
            patched.append(f"{run_name}.FileName {output_prefix}")
        elif index == isotope_i:
            patched.append(f"{run_name}.IsotopeProductionFile {output_prefix}.dat")
        elif raw.startswith(f"{old_run}."):
            patched.append(run_name + raw[len(old_run):])
        else:
            patched.append(raw)
    result = "\n".join(patched) + "\n"
    validate_patched_source(result, job_id=job_id, run_name=run_name, mode=mode, seed=seed, events=events)
    return result


def validate_patched_source(
    text: str, *, job_id: str, run_name: str, mode: str, seed: int, events: int
) -> None:
    lines = text.splitlines()
    exact = lambda value: sum(line.strip() == value for line in lines)
    required = {
        f"Geometry {SE3_SETUP}": 1,
        f"Seed {seed}": 1,
        f"Run {run_name}": 1,
        f"{run_name}.Events {events}": 1,
        f"{run_name}.FileName {active_prefix(job_id)}": 1,
        f"{run_name}.IsotopeProductionFile {active_prefix(job_id)}.dat": 1,
        "StoreSimulationInfo all": 1,
        "StoreIsotopes true": 1,
        "PhysicsListHD qgsp-bic-hp": 1,
        "PhysicsListEM LivermorePol": 1,
    }
    bad = {key: exact(key) for key, expected in required.items() if exact(key) != expected}
    if bad:
        raise RuntimeError(f"patched source control mismatch: {bad}")
    expected_decay = 1 if mode == "buildup" else 0
    if exact("DecayMode ActivationBuildUp") != expected_decay:
        raise RuntimeError("DecayMode contract failed")
    if text.count(".Spectrum File ") != 20 or text.count(CORRECTED_TOKEN) != 20:
        raise RuntimeError("corrected-keV 20-spectrum contract failed")
    if FORBIDDEN_TOKEN in text:
        raise RuntimeError("legacy factor-1000 spectrum token found")
    if text.count(f"{run_name}.Source ") != 20:
        raise RuntimeError("run-scoped 20-source contract failed")
    if text.count("Beam FarFieldAreaSource") != 20:
        raise RuntimeError("20 equal-mu FarFieldAreaSource contract failed")
    if "mono511" in text.lower() or "mono_511" in text.lower():
        raise RuntimeError("forbidden additive mono-511 source marker found")


def build_analysis_inputs() -> dict[str, Any]:
    active_veto = [
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    ]
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "authority_boundary": "PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN__NO_AUTOMATIC_PROMOTION",
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(RUN_ROOT),
        "handoff": str(HANDOFF),
        "source": {
            "contract_path": str(SOURCE_CONTRACT),
            "energy_unit": "keV_total",
            "gamma_profile": "unit_only_total_gamma",
            "additive_mono511": False,
            "forbidden_legacy_token": FORBIDDEN_TOKEN,
            "base_source_root": str(BASE_SOURCE_ROOT),
        },
        "geometry": {
            "candidate": "SE3",
            "se3_setup": str(SE3_SETUP),
            "s3d_control_setup": str(S3D_SETUP),
            "active_veto_volumes": active_veto,
            "shield_veto_volumes": active_veto[:3],
            "plastic_veto_volumes": active_veto[3:],
            "apply_plastic_veto": True,
        },
        "transport": {
            "job_plan": str(PACKAGE_ROOT / "data/se3_plan1_job_plan.csv"),
            "seed_registry": str(PACKAGE_ROOT / "data/se3_plan1_seed_registry.csv"),
            "receipts": str(PACKAGE_ROOT / "audit/se3_plan1_transport_receipts.json"),
            "cpu_budget": 6,
            "max_cpu_budget": 8,
            "start_free_gate_bytes": START_FREE_GATE_BYTES,
            "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            "max_attempts": 2,
        },
        "signal": {
            "eventlist": str(EVENTLIST),
            "eventlist_rows": 37_194,
            "eventlist_frozen_sha256": "ee538d20d818baab94a5c3ebe01392a3ae9f278a231aa5b8938cdf23870f62b5",
            "input_optics_aeff_cm2": 20.08476,
            "injection_plane_xprime_cm": -30.0001,
            "scope": "FULL_ENVELOPE_PAIRED_S3D_O8_VS_SE3",
        },
        "analysis": {
            "response_fwhm_keV": 0.42,
            "measured_pixel_threshold_keV": 0.3,
            "active_veto_threshold_keV": 50.0,
            "w2_keV": [510.58, 511.42],
            "step05_policy": "retained_side_compton_fov_reject",
            "mission_days": 20.0,
            "mission_nodes": 81,
            "reference_flux_ph_cm2_s": 1.0e-4,
            "family_scales": str(M05_ROOT / "data/parma_energy_integrated_family_scales_81bins.csv"),
            "atmosphere": str(S3D_SETUP.parents[1] / "fullchain/step06/atmosphere_transmission_511_by_time.csv"),
        },
        "frozen_s3d": {
            "statistics_root": str(S3D_STATS_ROOT),
            "m05_outputs": str(M05_ROOT / "outputs"),
            "background_mission20_counts": 144_203.8420859011,
            "background_upper95_proxy": 1_249_284.0948305726,
            "old_post_be_signal_scope": "CONTINUITY_ONLY__NOT_GEOMETRY_RATIO",
        },
        "outputs": {f"stage_{i:02d}": str(PACKAGE_ROOT / f"outputs/{i:02d}_{name}") for i, name in (
            (0, "input_audit"), (1, "prompt"), (2, "activation"), (3, "delayed"),
            (4, "common_response"), (5, "matched_comparison"), (6, "mission")
        )},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-read-only-check", action="store_true", help="validate existing write-once files")
    args = parser.parse_args()
    validate_shards()
    required = [HANDOFF, SE3_SETUP, S3D_SETUP, SOURCE_CONTRACT, EVENTLIST]
    required.extend(base_source(family) for family in FAMILIES)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing authoritative inputs: {missing}")
    disk = shutil.disk_usage(PACKAGE_ROOT)
    if not args.force_read_only_check and disk.free < START_FREE_GATE_BYTES:
        raise RuntimeError(f"R0 start-space gate failed: free={disk.free} < {START_FREE_GATE_BYTES}")

    occupied, seed_audit = collect_occupied_seeds()
    seed_by_identity = derive_seed_plan(occupied)
    collisions = sorted(set(seed_by_identity.values()) & occupied)
    if collisions or len(seed_by_identity) != len(set(seed_by_identity.values())):
        raise RuntimeError(f"seed collision: {collisions}")
    plan = build_job_plan(seed_by_identity)

    plan_fields = list(plan[0])
    write_csv_once(PACKAGE_ROOT / "data/se3_plan1_job_plan.csv", plan, plan_fields)
    # Compatibility alias promised by the scaffold section of the handoff.
    write_csv_once(PACKAGE_ROOT / "data/job_plan.csv", plan, plan_fields)
    seed_rows = [{
        "job_id": row["job_id"],
        "seed_identity": row["seed_identity"],
        "seed": row["seed"],
        "paired_seed_exception": row["paired_seed_exception"],
        "collision_with_prior": False,
        "namespace": PROFILE_ID,
    } for row in plan]
    write_csv_once(PACKAGE_ROOT / "data/se3_plan1_seed_registry.csv", seed_rows)
    write_csv_once(PACKAGE_ROOT / "data/seed_registry.csv", seed_rows)

    source_rows: list[dict[str, Any]] = []
    for row in plan:
        if row["stage"] != "background":
            continue
        base = base_source(str(row["family"]))
        text = patch_background_source(
            base.read_text(encoding="utf-8"),
            job_id=str(row["job_id"]),
            run_name=background_run_name(str(row["mode"]), str(row["family"]), int(row["shard"])),
            mode=str(row["mode"]),
            seed=int(row["seed"]),
            events=int(row["events"]),
        )
        path = job_source_path(str(row["job_id"]))
        write_once_text(path, text)
        source_rows.append({
            "job_id": row["job_id"],
            "mode": row["mode"],
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "base_source": str(base),
            "base_source_sha256": sha256(base),
            "source": str(path),
            "source_sha256": sha256(path),
            "setup": str(SE3_SETUP),
            "corrected_references": text.count(CORRECTED_TOKEN),
            "legacy_references": text.count(FORBIDDEN_TOKEN),
        })
    write_csv_once(PACKAGE_ROOT / "data/se3_background_source_manifest.csv", source_rows)

    inputs = build_analysis_inputs()
    write_once_json(PACKAGE_ROOT / "analysis_inputs.json", inputs)
    audit_path = PACKAGE_ROOT / "outputs/00_input_audit/input_audit.json"
    frozen_audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else None
    source_audit = {
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "created_at": frozen_audit["created_at"] if frozen_audit else utc_now(),
        "policy": "SMALL_AUTHORITY_DIGESTS_ONCE__NO_LARGE_SIM_OPEN_OR_HASH",
        "r0": {
            "filesystem": str(PACKAGE_ROOT),
            "free_bytes": frozen_audit["r0"]["free_bytes"] if frozen_audit else disk.free,
            "start_gate_bytes": START_FREE_GATE_BYTES,
            "start_gate_pass": disk.free >= START_FREE_GATE_BYTES,
            "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        },
        "plan": {
            "jobs": len(plan),
            "background_jobs": sum(row["stage"] == "background" for row in plan),
            "delayed_jobs": sum(row["stage"] == "delayed" for row in plan),
            "signal_jobs": sum(row["stage"] == "signal" for row in plan),
            "instant_histories": sum(int(row["events"]) for row in plan if row["mode"] == "instant"),
            "buildup_histories": sum(int(row["events"]) for row in plan if row["mode"] == "buildup"),
            "delayed_triggers": sum(int(row["events"]) for row in plan if row["mode"] == "delayed"),
            "signal_trials": sum(int(row["events"]) for row in plan if row["mode"] == "signal"),
            "plan_sha256": sha256(PACKAGE_ROOT / "data/se3_plan1_job_plan.csv"),
            "seed_registry_sha256": sha256(PACKAGE_ROOT / "data/se3_plan1_seed_registry.csv"),
        },
        "seed_audit": {**seed_audit, "new_unique_seed_count": len(seed_by_identity), "collisions": collisions},
        "sources": {
            "count": len(source_rows),
            "all_se3_geometry": all(row["setup"] == str(SE3_SETUP) for row in source_rows),
            "corrected_reference_count": sum(int(row["corrected_references"]) for row in source_rows),
            "legacy_reference_count": sum(int(row["legacy_references"]) for row in source_rows),
        },
        "small_authorities": {
            "handoff": {"path": str(HANDOFF), "sha256": sha256(HANDOFF)},
            "m05_readme": {"path": str(M05_ROOT / "README.md"), "sha256": sha256(M05_ROOT / "README.md")},
            "source_contract": {"path": str(SOURCE_CONTRACT), "sha256": sha256(SOURCE_CONTRACT)},
            "se3_setup": {"path": str(SE3_SETUP), "sha256": sha256(SE3_SETUP)},
            "s3d_setup": {"path": str(S3D_SETUP), "sha256": sha256(S3D_SETUP)},
        },
    }
    write_once_json(audit_path, source_audit)
    write_once_json(PACKAGE_ROOT / "audit/se3_plan1_source_validation.json", source_audit)
    print(json.dumps({
        "status": "PASS__SE3_PLAN1_FRESH_ADAPTER_AND_SOURCES_FROZEN",
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(RUN_ROOT),
        "jobs": len(plan),
        "background_sources": len(source_rows),
        "free_bytes": shutil.disk_usage(PACKAGE_ROOT).free,
        "start_gate_bytes": START_FREE_GATE_BYTES,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
