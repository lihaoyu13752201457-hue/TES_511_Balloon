#!/usr/bin/env python3
"""Build/check the fresh SF3 Plan-1 plan, seeds, and source cards.

The script is intentionally transport-incapable: it neither imports nor
executes Cosima, and it only reads compact JSON/CSV authorities plus the
frozen 37,194-row EventList.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from sf3_plan1_common import (
    ACTIVE_VETO_VOLUMES,
    BASE_SOURCE_ROOT,
    CORRECTED_TOKEN,
    CPU_BUDGET,
    DYNAMIC_RESERVE_BYTES,
    EVENTLIST,
    EVENTLIST_AUTHORITY,
    EVENTLIST_FROZEN_SHA256,
    FAMILIES,
    FORBIDDEN_TOKEN,
    GEOMETRY_AUTHORITIES,
    HANDOFF,
    MAX_ATTEMPTS,
    MAX_WORKERS,
    MEM_AVAILABLE_FLOOR_BYTES,
    M05_ROOT,
    MIN_WORKERS,
    MODES,
    PACKAGE_ROOT,
    PASSIVE_W_DIAGNOSTIC_VOLUMES,
    PRIMARY_ROOT,
    PROFILE_ID,
    PSI_MEMORY_FULL_AVG10_MAX,
    PSI_MEMORY_SOME_AVG10_MAX,
    RUN_ROOT,
    S3D_SETUP,
    S3D_STATS_ROOT,
    SE3_PLAN1_ROOT,
    SE3_SEED_REGISTRY,
    SE3_SETUP,
    SF3_DET,
    SF3_GEO,
    SF3_GEOMETRY_ROOT,
    SF3_SETUP,
    SHARDS,
    SIGNAL_EVENTS,
    SIGNAL_INJECTION_XPRIME_CM,
    SOURCE_CONTRACT,
    SOURCE_CWD,
    SOURCE_WORKTREE,
    START_FREE_GATE_BYTES,
    SWAP_FREE_FLOOR_BYTES,
    SWAP_PAGES_PER_SECOND_MAX,
    active_prefix,
    background_run_name,
    base_source,
    build_job_plan,
    derive_seed_plan,
    plan_identities,
    render_csv,
    render_json,
    sha256,
    text_sha256,
    utc_now,
    validate_shards,
    write_once_text,
)


MAX_SMALL_AUTHORITY_BYTES = 20_000_000
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


def read_small_json(path: Path) -> Any:
    size = path.stat().st_size
    if size > MAX_SMALL_AUTHORITY_BYTES:
        raise RuntimeError(f"refusing oversized JSON authority: {path} ({size} bytes)")
    return json.loads(path.read_text(encoding="utf-8"))


def collect_occupied_seeds() -> tuple[set[int], dict[str, Any]]:
    """Freeze M05, S3d, and every row of the retained 47 seed registry."""
    m05_config_path = M05_ROOT / "analysis_inputs.json"
    m05_config = read_small_json(m05_config_path)
    queue: list[Path] = []
    for item in m05_config["transport_inputs"]:
        path = resolve_authority_json(str(item["path"]))
        if path is None:
            raise FileNotFoundError(f"missing M05 seed authority: {item['path']}")
        queue.append(path)

    seen: set[Path] = set()
    m05_seeds: set[int] = set()
    authority_rows: list[dict[str, Any]] = []
    while queue:
        path = queue.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        payload = read_small_json(path)
        found = extract_seed_values(payload)
        m05_seeds.update(found)
        authority_rows.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "seed_values": len(found),
        })
        for reference in referenced_small_json(payload):
            resolved = resolve_authority_json(reference)
            if resolved is not None and resolved.resolve() not in seen:
                queue.append(resolved)

    s3d_stats = S3D_STATS_ROOT / "data/s3d_o8_particle_family_statistics.csv"
    s3d_seeds: set[int] = set()
    s3d_rows = 0
    with s3d_stats.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            s3d_rows += 1
            s3d_seeds.add(int(row["delayed_source_sampling_seed"]))
            s3d_seeds.add(int(row["delayed_transport_seed"]))
    if s3d_rows != len(FAMILIES):
        raise RuntimeError(f"S3d statistics must contain 8 family rows, got {s3d_rows}")

    se3_registry_seeds: set[int] = set()
    se3_registry_rows = 0
    with SE3_SEED_REGISTRY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            se3_registry_rows += 1
            se3_registry_seeds.add(int(row["seed"]))
    # Retained 47 has 31 rows because its two signal jobs intentionally share
    # one seed; all rows and the complete 30-seed set must be occupied here.
    if se3_registry_rows != 31 or len(se3_registry_seeds) != 30:
        raise RuntimeError(
            "retained 47 full registry contract changed: "
            f"rows={se3_registry_rows}, unique={len(se3_registry_seeds)}"
        )

    occupied = m05_seeds | s3d_seeds | se3_registry_seeds
    audit = {
        "status": "PASS__M05_S3D_AND_SE3_PLAN1_FULL_REGISTRY_OCCUPIED",
        "policy": "SMALL_JSON_AND_CSV_AUTHORITIES_ONLY__NO_SIM_DISCOVERY_OPEN_OR_HASH",
        "m05": {
            "analysis_inputs": str(m05_config_path),
            "analysis_inputs_sha256": sha256(m05_config_path),
            "authority_files": sorted(authority_rows, key=lambda row: row["path"]),
            "authority_file_count": len(authority_rows),
            "occupied_seed_count": len(m05_seeds),
        },
        "s3d": {
            "statistics_csv": str(s3d_stats),
            "statistics_sha256": sha256(s3d_stats),
            "rows": s3d_rows,
            "occupied_seed_count": len(s3d_seeds),
        },
        "se3_plan1_47": {
            "full_registry_csv": str(SE3_SEED_REGISTRY),
            "full_registry_sha256": sha256(SE3_SEED_REGISTRY),
            "rows": se3_registry_rows,
            "unique_occupied_seed_count": len(se3_registry_seeds),
            "shared_pair_seed_rows_preserved": se3_registry_rows - len(se3_registry_seeds),
        },
        "occupied_union_count": len(occupied),
    }
    return occupied, audit


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
    if len(scoped) != 23:
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
            patched.append(f"Geometry {SF3_SETUP}")
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
    validate_background_source(
        result, job_id=job_id, run_name=run_name, mode=mode, seed=seed, events=events
    )
    return result


def validate_background_source(
    text: str, *, job_id: str, run_name: str, mode: str, seed: int, events: int
) -> None:
    lines = text.splitlines()
    exact = lambda value: sum(line.strip() == value for line in lines)
    required = {
        f"Geometry {SF3_SETUP}": 1,
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
        raise RuntimeError("forbidden additive mono-511 marker found")


def signal_source_text(seed: int) -> str:
    job_id = "signal_full_envelope_sf3"
    source_name = f"{job_id}_EventList"
    text = f"""# SF3 Plan-1 fresh full-envelope focused-signal replay.
# Direct reuse of the frozen 37,194-ray SE3 full-envelope bank; no resampling.

Version 1
Geometry {SF3_SETUP}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {job_id}
{job_id}.FileName {active_prefix(job_id)}
{job_id}.Triggers {SIGNAL_EVENTS}
{job_id}.Source {source_name}

{source_name}.EventList {EVENTLIST}
"""
    exact = lambda value: sum(line.strip() == value for line in text.splitlines())
    required = (
        f"Geometry {SF3_SETUP}",
        f"Seed {seed}",
        f"Run {job_id}",
        f"{job_id}.FileName {active_prefix(job_id)}",
        f"{job_id}.Triggers {SIGNAL_EVENTS}",
        f"{source_name}.EventList {EVENTLIST}",
    )
    if any(exact(value) != 1 for value in required):
        raise RuntimeError("SF3 signal source contract failed")
    # The retained bank filename contains ``se3`` as provenance; only fresh
    # Run/Source registrations are forbidden.
    if any(
        line.strip().startswith("Run signal_full_envelope_se3")
        or line.strip().startswith("Run signal_full_envelope_s3d")
        for line in text.splitlines()
    ):
        raise RuntimeError("fresh SE3/S3d signal registration leaked into SF3 card")
    return text


def validate_eventlist() -> dict[str, Any]:
    rows = 0
    first_id: int | None = None
    last_id: int | None = None
    with EVENTLIST.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip() or raw.lstrip().startswith("#"):
                raise RuntimeError("frozen bank unexpectedly contains blank/comment row")
            fields = raw.split()
            if len(fields) != 15:
                raise RuntimeError(f"frozen bank field count changed at row {rows}: {len(fields)}")
            ray_id = int(fields[0])
            if ray_id != rows:
                raise RuntimeError(f"frozen bank ID/order changed at row {rows}: {ray_id}")
            if float(fields[14]) != 511.0:
                raise RuntimeError(f"frozen bank energy changed at ray {ray_id}")
            first_id = ray_id if first_id is None else first_id
            last_id = ray_id
            rows += 1
    digest = sha256(EVENTLIST)
    if rows != SIGNAL_EVENTS or first_id != 0 or last_id != SIGNAL_EVENTS - 1:
        raise RuntimeError(f"frozen bank row/ID closure failed: {rows}, {first_id}, {last_id}")
    if digest != EVENTLIST_FROZEN_SHA256:
        raise RuntimeError(f"frozen bank hash changed: {digest}")
    authority = read_small_json(EVENTLIST_AUTHORITY)
    if authority.get("status") != "PASS__FULL_ENVELOPE_SIGNAL_STATIC_PREPARATION":
        raise RuntimeError("47 signal static authority is not PASS")
    if authority["frozen_bank"]["output_sha256"] != digest:
        raise RuntimeError("47 signal authority does not bind current frozen bank")
    return {
        "path": str(EVENTLIST),
        "bytes": EVENTLIST.stat().st_size,
        "sha256": digest,
        "rows": rows,
        "first_id": first_id,
        "last_id": last_id,
        "energy_keV": 511.0,
        "source_authority": str(EVENTLIST_AUTHORITY),
        "source_authority_sha256": sha256(EVENTLIST_AUTHORITY),
    }


def validate_geometry_authorities(bound_at: str) -> dict[str, Any]:
    payloads = {name: read_small_json(path) for name, path in GEOMETRY_AUTHORITIES.items()}
    static = payloads["strict_additive"]
    mesh = payloads["mesh_prefilter"]
    overlap = payloads["geant4_overlap"]
    native = payloads["native_navigation"]
    expected_status = {
        "strict_additive": "PASS__SF3_STRICT_ADDITIVE_GEOMETRY_DELTA",
        "mesh_prefilter": "PASS__SF3_MESH_CLEARANCE_STATIC_PREFILTER",
        "geant4_overlap": "PASS",
        "native_navigation": "PASS__SF3_NATIVE_FROZEN_BANK_AND_W_WITNESS_AUDIT",
    }
    for name, status in expected_status.items():
        if payloads[name].get("status") != status:
            raise RuntimeError(f"SF3 geometry authority {name} is not PASS: {payloads[name].get('status')}")

    current = {
        "setup": sha256(SF3_SETUP),
        "geo": sha256(SF3_GEO),
        "det": sha256(SF3_DET),
        "static_validation": sha256(GEOMETRY_AUTHORITIES["strict_additive"]),
    }
    bindings = {
        "static_setup": static["generated"]["setup"]["sha256"] == current["setup"],
        "static_geo": static["generated"]["geo"]["sha256"] == current["geo"],
        "static_det": static["generated"]["det"]["sha256"] == current["det"],
        "mesh_geo": mesh["inputs"]["sf3_geo"]["sha256"] == current["geo"],
        "overlap_setup": overlap["files"]["setup"]["sha256"] == current["setup"],
        "overlap_geo": overlap["files"]["geo"]["sha256"] == current["geo"],
        "overlap_det": overlap["files"]["det"]["sha256"] == current["det"],
        "overlap_static": (
            overlap["files"]["static_validation"]["sha256"] == current["static_validation"]
        ),
        "native_setup": native["inputs"]["sf3_setup"]["sha256"] == current["setup"],
        "native_static": (
            native["inputs"]["sf3_static_validation"]["sha256"] == current["static_validation"]
        ),
    }
    if not all(bindings.values()):
        raise RuntimeError(f"SF3 geometry authority hash binding failed: {bindings}")
    static_checks = static.get("checks", {})
    if not static_checks or not all(static_checks.values()):
        raise RuntimeError("SF3 strict-additive check set is not all true")
    if overlap.get("transport_launched") is not False or native.get("transport_launched") is not False:
        raise RuntimeError("geometry-only authorities unexpectedly claim transport")
    if overlap["check_for_overlaps"] != {"samples": 10_000, "tolerance_cm": 0.0001}:
        raise RuntimeError("Geant4 overlap sampling contract changed")
    if native.get("rows") != SIGNAL_EVENTS:
        raise RuntimeError("native authority does not cover the frozen 37,194-ray bank")
    if native["added_W_focused_chord"]["zero_rays"] != SIGNAL_EVENTS:
        raise RuntimeError("native authority reports a focused ray crossing added W")
    if native["full_path_material_comparison"]["equal_rays"] != SIGNAL_EVENTS:
        raise RuntimeError("native authority reports inherited material drift")
    if native["W_presence_witnesses"]["volume_passes"] != 3:
        raise RuntimeError("native authority lacks all three W witnesses")

    return {
        "schema_version": 1,
        "status": "PASS__SF3_FOUR_GEOMETRY_AUTHORITIES_CURRENT_AND_HASH_BOUND",
        "bound_at_utc": bound_at,
        "candidate": "SF3",
        "setup": {"path": str(SF3_SETUP), "sha256": current["setup"]},
        "geo": {"path": str(SF3_GEO), "sha256": current["geo"]},
        "det": {"path": str(SF3_DET), "sha256": current["det"]},
        "authorities": {
            name: {
                "path": str(GEOMETRY_AUTHORITIES[name]),
                "bytes": GEOMETRY_AUTHORITIES[name].stat().st_size,
                "sha256": sha256(GEOMETRY_AUTHORITIES[name]),
                "status": payloads[name]["status"],
            }
            for name in GEOMETRY_AUTHORITIES
        },
        "hash_bindings": bindings,
        "geometry_evidence": {
            "geant4_overlap_samples": overlap["check_for_overlaps"]["samples"],
            "geant4_overlap_tolerance_cm": overlap["check_for_overlaps"]["tolerance_cm"],
            "native_rows": native["rows"],
            "native_zero_added_W_chord_rays": native["added_W_focused_chord"]["zero_rays"],
            "native_equal_inherited_material_rays": native["full_path_material_comparison"]["equal_rays"],
            "native_W_witnesses": native["W_presence_witnesses"]["volume_passes"],
        },
        "transport_launched": False,
    }


def build_analysis_inputs() -> dict[str, Any]:
    outputs = {
        f"stage_{index:02d}": str(PACKAGE_ROOT / f"outputs/{index:02d}_{name}")
        for index, name in (
            (0, "input_audit"),
            (1, "prompt"),
            (2, "activation"),
            (3, "delayed"),
            (4, "common_response"),
            (5, "se3_vs_sf3_matched_comparison"),
            (6, "mission"),
            (7, "final_audit"),
        )
    }
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "authority_boundary": "SF3_PLAN1_CONFIG_ONLY__TRANSPORT_NOT_LAUNCHED",
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(RUN_ROOT),
        "handoff": str(HANDOFF),
        "source": {
            "contract_path": str(SOURCE_CONTRACT),
            "cwd_required": str(SOURCE_CWD),
            "energy_unit": "keV_total",
            "gamma_profile": "unit_only_total_gamma",
            "additive_mono511": False,
            "forbidden_legacy_token": FORBIDDEN_TOKEN,
            "base_source_root": str(BASE_SOURCE_ROOT),
        },
        "geometry": {
            "candidate": "SF3",
            "sf3_setup": str(SF3_SETUP),
            "frozen_se3_setup": str(SE3_SETUP),
            "s3d_setup_provenance_only": str(S3D_SETUP),
            "active_veto_volumes": list(ACTIVE_VETO_VOLUMES),
            "shield_veto_volumes": list(ACTIVE_VETO_VOLUMES[:3]),
            "plastic_veto_volumes": list(ACTIVE_VETO_VOLUMES[3:]),
            "apply_plastic_veto": True,
            "passive_W_diagnostic_volumes": list(PASSIVE_W_DIAGNOSTIC_VOLUMES),
            "passive_W_active_veto": False,
        },
        "transport": {
            "job_plan": str(PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"),
            "seed_registry": str(PACKAGE_ROOT / "data/sf3_plan1_seed_registry.csv"),
            "receipts": str(PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"),
            "cpu_budget": CPU_BUDGET,
            "min_workers_when_stable": MIN_WORKERS,
            "max_workers": MAX_WORKERS,
            "start_free_gate_bytes": START_FREE_GATE_BYTES,
            "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            "mem_available_floor_bytes": MEM_AVAILABLE_FLOOR_BYTES,
            "swap_free_floor_bytes": SWAP_FREE_FLOOR_BYTES,
            "psi_memory_some_avg10_max": PSI_MEMORY_SOME_AVG10_MAX,
            "psi_memory_full_avg10_max": PSI_MEMORY_FULL_AVG10_MAX,
            "swap_pages_per_second_max": SWAP_PAGES_PER_SECOND_MAX,
            "max_attempts": MAX_ATTEMPTS,
            "canary_job_id": "sf3_instant_gamma_shard0001",
            "canary_must_complete_before_parallel_production": True,
        },
        "activation_delayed": {
            "own_buildup_inventory_required": True,
            "actual_production_position_required": True,
            "registered_families": list(FAMILIES),
            "registered_triggers_per_family": 83_334,
            "zero_A15_policy": "SKIP_ZERO_A15_ONLY_AFTER_FRESH_SF3_TRANSPORTED_GROUND_A15_EQUALS_ZERO",
            "W_lineage_diagnostic_required": True,
        },
        "signal": {
            "job_id": "signal_full_envelope_sf3",
            "fresh_geometry": "SF3",
            "eventlist": str(EVENTLIST),
            "eventlist_rows": SIGNAL_EVENTS,
            "eventlist_frozen_sha256": EVENTLIST_FROZEN_SHA256,
            "fresh_seed": True,
            "no_resampling_or_bootstrap": True,
            "input_optics_aeff_cm2": 20.08476,
            "injection_plane_xprime_cm": SIGNAL_INJECTION_XPRIME_CM,
            "scope": "FULL_ENVELOPE_SF3_ONLY",
            "fresh_se3_or_s3d_signal_registered": False,
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
            "atmosphere": str(
                S3D_SETUP.parents[1] / "fullchain/step06/atmosphere_transmission_511_by_time.csv"
            ),
        },
        "frozen_se3": {
            # Compatibility key retained for 47 stage04 consumers.
            "m05_outputs": str(SE3_PLAN1_ROOT / "outputs"),
            "plan1_outputs": str(SE3_PLAN1_ROOT / "outputs"),
            "final_audit": str(SE3_PLAN1_ROOT / "outputs/07_final_audit/final_audit.json"),
            "prompt_W2_cps": 0.0,
            "delayed_W2_cps": 0.06011336205846697,
            "signal_selected": 21_657,
            "signal_trials": 37_194,
            "aeff_cm2": 11.69478,
            "S20": 1279.2886580217926,
            "B20": 98257.66904712601,
            "F3_central": 7.350822463201115e-05,
            "F3_proxy": 4.4813103398753603e-04,
            "fresh_transport_forbidden": True,
        },
        "decision": {
            "fullstat_trigger_metric": "central_F3_SF3_over_F3_SE3",
            "fullstat_trigger_max": 0.75,
            "sf3_F3_equivalent_max": 5.513116847400837e-05,
            "proxy_is_not_an_additional_trigger": True,
        },
        "audits": {
            "geometry_authority_bindings": str(PACKAGE_ROOT / "audit/sf3_geometry_authority_bindings.json"),
            "full_envelope_signal_static": str(PACKAGE_ROOT / "audit/full_envelope_signal_static_audit.json"),
            "full_envelope_signal_transport_gate": str(PACKAGE_ROOT / "audit/full_envelope_signal_transport_gate.json"),
            "user_scope_override_no_se3_rerun": str(
                PACKAGE_ROOT / "audit/user_scope_override_no_se3_rerun_20260816.json"
            ),
            "seed_occupancy": str(PACKAGE_ROOT / "audit/sf3_seed_occupancy_audit.json"),
        },
        "outputs": outputs,
    }


def existing_field(path: Path, key: str, default: Any) -> Any:
    if not path.is_file():
        return default
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get(key, default)


def compare_or_write(artifacts: dict[Path, str], *, build: bool) -> None:
    for path in sorted(artifacts, key=str):
        expected = artifacts[path]
        if build:
            write_once_text(path, expected)
        else:
            if not path.is_file():
                raise FileNotFoundError(f"missing built artifact: {path}")
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                raise RuntimeError(f"built artifact differs from current contract: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true", help="create write-once config/source artifacts")
    action.add_argument("--check", action="store_true", help="read-only exact validation of built artifacts")
    args = parser.parse_args()

    validate_shards()
    required = [
        HANDOFF,
        SF3_SETUP,
        SF3_GEO,
        SF3_DET,
        SE3_SETUP,
        S3D_SETUP,
        SOURCE_CONTRACT,
        M05_ROOT / "README.md",
        EVENTLIST,
        EVENTLIST_AUTHORITY,
        SE3_SEED_REGISTRY,
        SE3_PLAN1_ROOT / "outputs/07_final_audit/final_audit.json",
    ]
    required.extend(GEOMETRY_AUTHORITIES.values())
    required.extend(base_source(family) for family in FAMILIES)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing authoritative inputs: {missing}")

    disk = shutil.disk_usage(PACKAGE_ROOT)
    if disk.free < START_FREE_GATE_BYTES:
        raise RuntimeError(f"30 GB start-space gate failed: {disk.free} < {START_FREE_GATE_BYTES}")

    now = utc_now()
    geometry_binding_path = PACKAGE_ROOT / "audit/sf3_geometry_authority_bindings.json"
    geometry_bound_at = existing_field(geometry_binding_path, "bound_at_utc", now)
    geometry_binding = validate_geometry_authorities(geometry_bound_at)
    geometry_binding_text = render_json(geometry_binding)

    if len(ACTIVE_VETO_VOLUMES) != 6:
        raise RuntimeError("active veto list must remain exactly six volumes")
    if set(ACTIVE_VETO_VOLUMES) & set(PASSIVE_W_DIAGNOSTIC_VOLUMES):
        raise RuntimeError("passive W leaked into active-veto roles")
    det_text = SF3_DET.read_text(encoding="utf-8")
    if any(volume in det_text for volume in PASSIVE_W_DIAGNOSTIC_VOLUMES):
        raise RuntimeError("passive W leaked into the detector map")

    occupied, seed_occupancy = collect_occupied_seeds()
    seed_by_identity = derive_seed_plan(occupied)
    collisions = sorted(set(seed_by_identity.values()) & occupied)
    if collisions or len(seed_by_identity) != len(set(seed_by_identity.values())):
        raise RuntimeError(f"fresh seed collision: {collisions}")
    if set(seed_by_identity) != set(plan_identities()):
        raise RuntimeError("fresh seed identity set does not equal the 30-job plan")

    plan = build_job_plan(seed_by_identity)
    background_rows = [row for row in plan if row["stage"] == "background"]
    delayed_rows = [row for row in plan if row["stage"] == "delayed"]
    signal_rows = [row for row in plan if row["stage"] == "signal"]
    canaries = [row for row in plan if row["production_canary"]]
    if len(background_rows) != 21 or len(delayed_rows) != 8 or len(signal_rows) != 1:
        raise RuntimeError("job plan must be 21 background + 8 delayed + 1 signal")
    if len(canaries) != 1 or canaries[0]["job_id"] != "sf3_instant_gamma_shard0001":
        raise RuntimeError("exactly one gamma shard0001 production canary is required")
    if int(canaries[0]["events"]) != 267_312:
        raise RuntimeError("production canary must contain 267312 histories")
    if any("signal_full_envelope_se3" == row["job_id"] for row in plan):
        raise RuntimeError("fresh SE3 signal job is forbidden")
    if any("signal_full_envelope_s3d" in row["job_id"] for row in plan):
        raise RuntimeError("fresh S3d signal job is forbidden")
    if sum(int(row["events"]) for row in plan if row["mode"] == "instant") != 1_280_693:
        raise RuntimeError("instant history total differs from handoff")
    if sum(int(row["events"]) for row in plan if row["mode"] == "buildup") != 1_015_492:
        raise RuntimeError("buildup history total differs from handoff")
    if sum(int(row["events"]) for row in delayed_rows) != 666_672:
        raise RuntimeError("registered delayed trigger total differs from handoff")

    eventlist_info = validate_eventlist()
    source_texts: dict[Path, str] = {}
    source_manifest: list[dict[str, Any]] = []
    for row in background_rows:
        base = base_source(str(row["family"]))
        card = patch_background_source(
            base.read_text(encoding="utf-8"),
            job_id=str(row["job_id"]),
            run_name=background_run_name(str(row["mode"]), str(row["family"]), int(row["shard"])),
            mode=str(row["mode"]),
            seed=int(row["seed"]),
            events=int(row["events"]),
        )
        path = Path(str(row["source_path"]))
        source_texts[path] = card
        source_manifest.append({
            "card_kind": "background",
            "job_id": row["job_id"],
            "geometry": "SF3",
            "mode": row["mode"],
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "base_source": str(base),
            "base_source_sha256": sha256(base),
            "eventlist": "",
            "eventlist_sha256": "",
            "source": str(path),
            "source_sha256": text_sha256(card),
            "setup": str(SF3_SETUP),
            "corrected_references": card.count(CORRECTED_TOKEN),
            "legacy_references": card.count(FORBIDDEN_TOKEN),
        })

    signal_row = signal_rows[0]
    signal_path = Path(str(signal_row["source_path"]))
    signal_card = signal_source_text(int(signal_row["seed"]))
    source_texts[signal_path] = signal_card
    source_manifest.append({
        "card_kind": "signal",
        "job_id": signal_row["job_id"],
        "geometry": "SF3",
        "mode": "signal",
        "family": "focused_gamma",
        "events": signal_row["events"],
        "seed": signal_row["seed"],
        "base_source": "",
        "base_source_sha256": "",
        "eventlist": str(EVENTLIST),
        "eventlist_sha256": eventlist_info["sha256"],
        "source": str(signal_path),
        "source_sha256": text_sha256(signal_card),
        "setup": str(SF3_SETUP),
        "corrected_references": 0,
        "legacy_references": 0,
    })

    plan_text = render_csv(plan)
    seed_rows = [
        {
            "job_id": row["job_id"],
            "seed_identity": row["seed_identity"],
            "seed": row["seed"],
            "paired_seed_exception": False,
            "collision_with_prior": False,
            "namespace": PROFILE_ID,
        }
        for row in plan
    ]
    seed_registry_text = render_csv(seed_rows)
    source_manifest_text = render_csv(source_manifest)
    analysis_inputs_text = render_json(build_analysis_inputs())

    seed_occupancy_path = PACKAGE_ROOT / "audit/sf3_seed_occupancy_audit.json"
    seed_occupancy_created = existing_field(seed_occupancy_path, "created_at_utc", now)
    seed_occupancy = {
        **seed_occupancy,
        "created_at_utc": seed_occupancy_created,
        "fresh_namespace": PROFILE_ID,
        "fresh_registered_rows": len(seed_rows),
        "fresh_unique_seeds": len(set(seed_by_identity.values())),
        "fresh_collisions_with_occupied": collisions,
    }
    seed_occupancy_text = render_json(seed_occupancy)

    signal_static_path = PACKAGE_ROOT / "audit/full_envelope_signal_static_audit.json"
    signal_static_created = existing_field(signal_static_path, "created_at_utc", now)
    signal_static = {
        "schema_version": 1,
        "status": "PASS__SF3_FULL_ENVELOPE_SIGNAL_STATIC_PREPARATION",
        "created_at_utc": signal_static_created,
        "scope": "FULL_ENVELOPE_SF3_ONLY",
        "authority_boundary": "STATIC_SOURCE_PREPARATION_ONLY__NO_TRANSPORT_LAUNCHED",
        "frozen_bank": eventlist_info,
        "no_resampling_or_bootstrap": True,
        "ray_id_order_time_energy_direction_weight_preserved": True,
        "fresh_jobs": [{
            "job_id": signal_row["job_id"],
            "geometry": "SF3",
            "events": signal_row["events"],
            "seed": signal_row["seed"],
            "seed_identity": signal_row["seed_identity"],
            "fresh_unique_seed": True,
            "paired_seed_exception": False,
            "setup_path": str(SF3_SETUP),
            "source_path": str(signal_path),
            "source_sha256": text_sha256(signal_card),
            "eventlist_path": str(EVENTLIST),
            "eventlist_sha256": eventlist_info["sha256"],
        }],
        "fresh_job_count": 1,
        "fresh_se3_jobs": 0,
        "fresh_s3d_jobs": 0,
        "transport_launched": False,
    }
    signal_static_text = render_json(signal_static)

    signal_gate_path = PACKAGE_ROOT / "audit/full_envelope_signal_transport_gate.json"
    signal_gate_created = existing_field(signal_gate_path, "created_at_utc", now)
    native_authority = geometry_binding["authorities"]["native_navigation"]
    signal_gate = {
        "schema_version": 1,
        "status": "PASS__READY_FOR_FRESH_SF3_SIGNAL_ONLY",
        "created_at_utc": signal_gate_created,
        "scope": "FULL_ENVELOPE_SF3_ONLY",
        "permitted_fresh_geometries": ["SF3"],
        "forbidden_fresh_geometries": ["SE3", "S3d_O8"],
        "permitted_job_ids": ["signal_full_envelope_sf3"],
        "frozen_bank_sha256": eventlist_info["sha256"],
        "native_geometry_authority": native_authority,
        "native_authority_bound": (
            native_authority["sha256"] == sha256(GEOMETRY_AUTHORITIES["native_navigation"])
        ),
        "zero_added_W_chord_rays": geometry_binding["geometry_evidence"][
            "native_zero_added_W_chord_rays"
        ],
        "transport_launched": False,
    }
    signal_gate_text = render_json(signal_gate)

    scope_path = PACKAGE_ROOT / "audit/user_scope_override_no_se3_rerun_20260816.json"
    scope_created = existing_field(scope_path, "created_at_utc", now)
    scope_override = {
        "schema_version": 1,
        "status": "PASS__USER_SCOPE_NO_FRESH_SE3_OR_S3D_RERUN",
        "created_at_utc": scope_created,
        "user_instruction": "Do not rerun SE3 or S3d; compare fresh SF3 to frozen SE3 authorities.",
        "fresh_transport_permitted_geometries": ["SF3"],
        "fresh_transport_forbidden_geometries": ["SE3", "S3d_O8"],
        "fresh_signal_jobs": ["signal_full_envelope_sf3"],
        "frozen_se3_plan1_outputs": str(SE3_PLAN1_ROOT / "outputs"),
        "frozen_se3_final_audit": str(SE3_PLAN1_ROOT / "outputs/07_final_audit/final_audit.json"),
        "large_historical_SIM_discovery_open_or_hash": False,
        "transport_launched": False,
    }
    scope_override_text = render_json(scope_override)

    input_audit_path = PACKAGE_ROOT / "outputs/00_input_audit/input_audit.json"
    input_created = existing_field(input_audit_path, "created_at_utc", now)
    free_at_build = existing_field(input_audit_path, "free_bytes_at_build", disk.free)
    input_audit = {
        "schema_version": 1,
        "status": "PASS__SF3_PLAN1_FRESH_ADAPTER_AND_SOURCES_FROZEN",
        "created_at_utc": input_created,
        "profile_id": PROFILE_ID,
        "authority_boundary": "CONFIG_AND_SOURCE_BUILD_ONLY__NO_TRANSPORT_LAUNCHED",
        "package_root": str(PACKAGE_ROOT),
        "run_root_literal": str(RUN_ROOT),
        "source_cwd_required": str(SOURCE_CWD),
        "free_bytes_at_build": free_at_build,
        "resource_gates": {
            "start_free_gate_bytes": START_FREE_GATE_BYTES,
            "start_gate_pass_at_build": free_at_build >= START_FREE_GATE_BYTES,
            "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
            "mem_available_floor_bytes": MEM_AVAILABLE_FLOOR_BYTES,
            "swap_free_floor_bytes": SWAP_FREE_FLOOR_BYTES,
            "cpu_budget": CPU_BUDGET,
            "worker_range": [MIN_WORKERS, MAX_WORKERS],
        },
        "plan": {
            "jobs": len(plan),
            "background_jobs": len(background_rows),
            "delayed_registered_jobs": len(delayed_rows),
            "signal_jobs": len(signal_rows),
            "instant_histories": 1_280_693,
            "buildup_histories": 1_015_492,
            "delayed_registered_triggers": 666_672,
            "signal_trials": SIGNAL_EVENTS,
            "production_canary": {"job_id": canaries[0]["job_id"], "events": canaries[0]["events"]},
            "fresh_se3_or_s3d_jobs": 0,
            "plan_sha256": text_sha256(plan_text),
            "seed_registry_sha256": text_sha256(seed_registry_text),
        },
        "seeds": {
            "occupied_authority": str(seed_occupancy_path),
            "occupied_authority_sha256": text_sha256(seed_occupancy_text),
            "fresh_rows": len(seed_rows),
            "fresh_unique": len(set(seed_by_identity.values())),
            "collisions": collisions,
        },
        "sources": {
            "generated_background_cards": len(background_rows),
            "generated_signal_cards": 1,
            "generated_delayed_cards": 0,
            "delayed_cards_pending_fresh_SF3_inventory": len(delayed_rows),
            "all_generated_cards_use_SF3": all(row["geometry"] == "SF3" for row in source_manifest),
            "corrected_references": sum(int(row["corrected_references"]) for row in source_manifest),
            "legacy_references": sum(int(row["legacy_references"]) for row in source_manifest),
            "manifest_sha256": text_sha256(source_manifest_text),
        },
        "geometry": {
            "authority_bindings": str(geometry_binding_path),
            "authority_bindings_sha256": text_sha256(geometry_binding_text),
            "active_veto_volume_count": len(ACTIVE_VETO_VOLUMES),
            "passive_W_diagnostic_volume_count": len(PASSIVE_W_DIAGNOSTIC_VOLUMES),
            "passive_W_in_active_veto": False,
        },
        "signal_scope_authorities": {
            "static": {"path": str(signal_static_path), "sha256": text_sha256(signal_static_text)},
            "transport_gate": {"path": str(signal_gate_path), "sha256": text_sha256(signal_gate_text)},
            "user_scope": {"path": str(scope_path), "sha256": text_sha256(scope_override_text)},
        },
        "transport_launched": False,
    }
    input_audit_text = render_json(input_audit)

    artifacts: dict[Path, str] = {
        PACKAGE_ROOT / "analysis_inputs.json": analysis_inputs_text,
        PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv": plan_text,
        PACKAGE_ROOT / "data/job_plan.csv": plan_text,
        PACKAGE_ROOT / "data/sf3_plan1_seed_registry.csv": seed_registry_text,
        PACKAGE_ROOT / "data/seed_registry.csv": seed_registry_text,
        PACKAGE_ROOT / "data/sf3_source_manifest.csv": source_manifest_text,
        geometry_binding_path: geometry_binding_text,
        seed_occupancy_path: seed_occupancy_text,
        signal_static_path: signal_static_text,
        signal_gate_path: signal_gate_text,
        scope_path: scope_override_text,
        input_audit_path: input_audit_text,
        PACKAGE_ROOT / "audit/sf3_plan1_source_validation.json": input_audit_text,
        **source_texts,
    }
    compare_or_write(artifacts, build=args.build)

    result = {
        "status": (
            "PASS__SF3_PLAN1_FRESH_ADAPTER_AND_SOURCES_FROZEN"
            if args.build
            else "PASS__SF3_PLAN1_BUILT_ARTIFACTS_CURRENT"
        ),
        "action": "build" if args.build else "check",
        "package_root": str(PACKAGE_ROOT),
        "run_root": str(RUN_ROOT),
        "jobs": len(plan),
        "background_jobs": len(background_rows),
        "delayed_registered_jobs": len(delayed_rows),
        "signal_jobs": len(signal_rows),
        "generated_source_cards": len(source_texts),
        "occupied_prior_seeds": len(occupied),
        "fresh_unique_seeds": len(set(seed_by_identity.values())),
        "fresh_seed_collisions": collisions,
        "geometry_authorities": geometry_binding["status"],
        "transport_launched": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
