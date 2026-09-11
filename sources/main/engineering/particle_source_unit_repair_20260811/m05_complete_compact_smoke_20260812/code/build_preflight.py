#!/usr/bin/env python3
"""Build the write-once, transport-blocked M05 compact-smoke preflight.

This program performs no Cosima invocation.  All retained inputs are selected
through fixed, hash-bound ledgers; all generated source cards use only a frozen
EventList tape.  The final status remains WAIT until an independent reviewer
authorizes transport outside this builder.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from manifest_discovery import (
    AUTHORITY_REGISTRY,
    load_authority,
    registered_authorities,
    resolve_job,
)
from preflight_common import (
    PACKAGE,
    ROOT,
    RUN_PACKAGE,
    assert_canonical_json,
    canonical_json_bytes,
    fsync_directory,
    quarantine_directory_no_replace,
    rename_no_replace,
    reject_lexical_symlinks,
    rel,
    sha256,
    sha256_bytes,
    strict_json,
    strict_json_bytes,
    write_once,
)
from seven_family_projection import build_projection
from tape_contract import (
    CELL_COUNTS,
    SOURCE_CONTRACT,
    SOURCE_CONTRACT_SHA256,
    build_cell_tapes,
    validate_cell_manifest,
    validate_sidecar,
)
from representation_schema import validate_mapping
from geometry_classification import build_geometry_classification
from run_preflight_unit_tests import tested_file_manifest


BENCHMARK_CLASS = "NON_MERGEABLE_BENCHMARK"
CONTRACT_PATH = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/"
    "GPT56_SOL_ULTRA_SMOKE_FOLLOWUP.md"
)
CONTRACT_SHA256 = "5288aa348a1fa5f669e8ad0f6c8e2c0e51e7bbac2f7b911183379754167b14be"
FEEDBACK01_PATH = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/"
    "INDEPENDENT_EVALUATOR_FEEDBACK_01.md"
)
FEEDBACK01_SHA256 = "57f52999ced570af079344ea538935ce0505502003c05229597b85faadf78748"
FEEDBACK_PATH = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/"
    "INDEPENDENT_EVALUATOR_FEEDBACK_02.md"
)
FEEDBACK_SHA256 = "caa97d522214b9ef811a9b6d71a5307dffd9f551e5687f1c736bcfe081a2a1d7"
EXTERNAL_SOURCES = PACKAGE / "external_sources.json"
EXECUTION_STATUS = PACKAGE / "EXECUTION_STATUS.json"
SHADOW_MANIFEST = RUN_PACKAGE / "preflight/shadow_build/build_manifest.json"
PRELOAD_OBSERVER_MANIFEST = RUN_PACKAGE / "preflight/preload_observer/build_manifest.json"
DURABLE_CONSUMER_COMMIT = (
    PACKAGE / "evidence/standalone_consumer_fixture_v1_20260812/commit.json"
)
DURABLE_CONSUMER_COMMIT_SHA256 = "ddb998339d6e4fe4581e72e7af6db68d1032d6af65ae16560f3e22f402992158"
PRELOAD_VALIDATOR = PACKAGE / "code/preload_observer_validation.py"
PRELOAD_SCHEMA = PACKAGE / "schema/preload_generated_observation_v1.schema.json"
UNIT_TEST_LOG = RUN_PACKAGE / "preflight/preflight_unit_tests.log"
UNIT_TEST_EVIDENCE = RUN_PACKAGE / "preflight/preflight_unit_tests.json"
BENCHMARK_CONTRACT = PACKAGE / "benchmark_contract.json"
GENERATED_NAME = "transport_preflight_v1"
FINAL_ROOT = RUN_PACKAGE / "preflight" / GENERATED_NAME
RECORD_SCHEMA = PACKAGE / "schema/m05cc_v2.record_schema.json"
RECORD_VALIDATOR = PACKAGE / "code/record_validation.py"
N1_COMMIT_SCHEMA = PACKAGE / "schema/m05cc_n1_v1.commit_schema.json"
N1_COMMIT_VALIDATOR = PACKAGE / "code/n1_validation.py"
ACTIVE_WHITELIST = PACKAGE / "schema/active_volume_whitelist_v1.json"

GEOMETRIES = ("mass_model_511", "s3d_o8")
CELLS = tuple(CELL_COUNTS)
ARMS = ("F", "C", "U", "N1")
ARM_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "F": {
        "binary_role": "installed_production_cosima",
        "native_event_output": "rich_gzip",
        "argv_option": "-z",
        "purpose": "matched analog rich-reference serialization",
        "generated_observation_contract": (
            "CANDIDATE__COMPILE_ONLY_MCRUN_POST_GPS_OBSERVER__SENTINEL_NOT_EXECUTED_OR_REVIEWED"
        ),
    },
    "U": {
        "binary_role": "installed_production_cosima",
        "native_event_output": "rich_uncompressed",
        "argv_option": "-u",
        "purpose": "separate gzip cost from rich construction/serialization",
        "generated_observation_contract": (
            "CANDIDATE__COMPILE_ONLY_MCRUN_POST_GPS_OBSERVER__SENTINEL_NOT_EXECUTED_OR_REVIEWED"
        ),
    },
    "C": {
        "binary_role": "isolated_shadow_m05cosima",
        "native_event_output": "disabled_compact_sidecars_plus_selected_truth",
        "argv_option": None,
        "purpose": "M05-complete compact candidate with exact root/RP hooks",
        "generated_observation_contract": (
            "PLANNED__POST_GPS_NORMALIZED_BINARY64_HOOK_PLUS_RICH_SIM_IA_INIT_STATE_AND_NATIVE_EVENT_TIME"
        ),
    },
    "N1": {
        "binary_role": "isolated_shadow_m05cosima",
        "native_event_output": "disabled_root_and_footer_provenance_only",
        "argv_option": None,
        "purpose": "rich objects constructed but native rich file disabled",
        "generated_observation_contract": (
            "PLANNED__POST_GPS_NORMALIZED_BINARY64_HOOK_PLUS_RICH_SIM_IA_INIT_STATE_AND_NATIVE_EVENT_TIME"
        ),
    },
}
ARM_ORDER = ("F", "C", "U", "N1")
ARM_ORDER_DESIGN = (
    ("F", "C", "U", "N1"),
    ("C", "F", "N1", "U"),
    ("U", "N1", "F", "C"),
    ("N1", "U", "C", "F"),
)


def arm_order_for(geometry_index: int, cell_index: int, shard_index: int) -> tuple[str, ...]:
    """Return one row of a four-treatment Williams-balanced design.

    Across the four shards every arm occupies every order slot once and every
    ordered arm pair is split 2:2.  Geometry/cell phasing changes which shard
    receives a row without changing those closures.
    """

    return ARM_ORDER_DESIGN[(geometry_index + cell_index + shard_index) % len(ARM_ORDER_DESIGN)]


def planned_job_readiness(arm: str) -> dict[str, Any]:
    """Return the fail-closed readiness of a plan-only arm in this artifact revision."""

    if arm not in ARMS:
        raise ValueError(f"unknown benchmark arm: {arm}")
    if arm in {"F", "U"}:
        status = "BLOCKED__P12_PRELOAD_OBSERVER_SENTINEL_NOT_EXECUTED_OR_REVIEWED"
    else:
        status = "BLOCKED__MATCHED_MATRIX_DEPENDS_ON_UNCLOSED_F_U_P12"
    return {
        "runnable_after_independent_authorization": False,
        "technical_readiness_status": status,
        "required_before_launch": (
            "Run the separately authorized installed plain-versus-preload sentinel, publish its atomic hash-bound "
            "PASS receipt, close P12 in a new artifact revision, rerun all non-transport gates, and obtain a "
            "separate write-once independent full-smoke authorization token."
        ),
    }

# These are fixed complete/partial authorities, not directory-discovery hints.
# They are used only to reject reuse of any already registered seed.
SEED_AUTHORITIES: dict[str, dict[str, str]] = {
    "batch0000": {
        "path": "runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_ledger.json",
        "sha256": "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f",
        "status": "PASS__BATCH0000_MERGE_ELIGIBLE",
    },
    "batch0001": {
        "path": AUTHORITY_REGISTRY["batch0001"]["path"],
        "sha256": AUTHORITY_REGISTRY["batch0001"]["sha256"],
        "status": AUTHORITY_REGISTRY["batch0001"]["status"],
    },
    "batch0002": {
        "path": "runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_ledger.json",
        "sha256": "742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62",
        "status": "PASS__BATCH0002_MERGE_ELIGIBLE",
    },
    "batch0003_prefix76": {
        "path": AUTHORITY_REGISTRY["batch0003_prefix76"]["path"],
        "sha256": AUTHORITY_REGISTRY["batch0003_prefix76"]["sha256"],
        "status": AUTHORITY_REGISTRY["batch0003_prefix76"]["status"],
    },
    "batch0004_partial_ordinal0097": {
        "path": (
            "runs/particle_source_unit_repair_20260811/"
            "seven_family_1m_screening_batch0004_partial_checkpoint_20260812/"
            "batch0004_partial_through_ordinal0097_v1_ledger.json"
        ),
        "sha256": "b4de513e7902ae4755eb741e7a79d23c378b3e3dd8cee993c7ffbff1af19dba0",
        "status": "PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE",
    },
    "batch0005": {
        "path": "runs/particle_source_unit_repair_20260811/reduced_breadth_continuation_batch0005_v1_ledger.json",
        "sha256": "670bc6f14de7799306301343908f524738c564ac62161caab1206a0be5cc41a0",
        "status": "PASS__BATCH0005_REDUCED_BREADTH_ADDON_MERGE_ELIGIBLE",
    },
}

CASSSETTE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "mass_gamma_w2_single_pixel_pair_ancestry",
        "authority_id": "batch0003_prefix76",
        "geometry": "mass_model_511",
        "mode": "instant",
        "family": "gamma",
        "ordinal": 22,
        "event_id": 5426,
        "required_markers": ("tes", "wide", "w2", "pair", "annihilation"),
    },
    {
        "case_id": "mass_gamma_wide_window_multipixel",
        "authority_id": "batch0003_prefix76",
        "geometry": "mass_model_511",
        "mode": "instant",
        "family": "gamma",
        "ordinal": 27,
        "event_id": 11043,
        "required_markers": ("tes", "wide", "pair", "annihilation"),
    },
    {
        "case_id": "o8_gamma_w2_pair_annihilation",
        "authority_id": "batch0003_prefix76",
        "geometry": "s3d_o8",
        "mode": "instant",
        "family": "gamma",
        "ordinal": 32,
        "event_id": 3883,
        "required_markers": ("tes", "wide", "w2", "pair", "annihilation"),
    },
    {
        "case_id": "o8_gamma_bgo_plastic_veto",
        "authority_id": "batch0001",
        "geometry": "s3d_o8",
        "mode": "instant",
        "family": "gamma",
        "job_name": "Background_gamma_fullsphere20_rep01_part01",
        "event_id": 2653,
        "required_markers": ("tes", "o8_bgo", "o8_plastic", "pair", "annihilation"),
    },
    {
        "case_id": "mass_gamma_csi_veto",
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "mode": "instant",
        "family": "gamma",
        "job_name": "Background_gamma_fullsphere20_rep01_part01",
        "event_id": 23343,
        "required_markers": ("tes", "mass_csi", "pair", "annihilation"),
    },
    {
        "case_id": "o8_prompt_eplus_heavy_driver",
        "authority_id": "batch0001",
        "geometry": "s3d_o8",
        "mode": "instant",
        "family": "eplus",
        "job_name": "Background_eplus_fullsphere20_rep01_part01",
        "event_id": 16,
        "required_markers": ("tes", "o8_bgo", "o8_plastic", "annihilation"),
    },
    {
        "case_id": "o8_prompt_neutron_heavy_driver",
        "authority_id": "batch0001",
        "geometry": "s3d_o8",
        "mode": "instant",
        "family": "n",
        "job_name": "Background_n_fullsphere20_rep01_part01",
        "event_id": 384,
        "required_markers": ("tes", "o8_bgo", "o8_plastic", "pair", "annihilation"),
    },
    {
        "case_id": "mass_prompt_alpha_heavy_driver",
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "mode": "instant",
        "family": "alpha",
        "job_name": "Background_alpha_fullsphere20_rep01_part01",
        "event_id": 77,
        "required_markers": ("tes", "mass_csi", "pair", "annihilation"),
    },
    {
        "case_id": "o8_buildup_eplus_rp",
        "authority_id": "batch0001",
        "geometry": "s3d_o8",
        "mode": "buildup",
        "family": "eplus",
        "job_name": "Background_eplus_fullsphere20_rep01_part01",
        "event_id": 515,
        "required_markers": ("tes", "o8_bgo", "o8_plastic", "native_rp"),
    },
    {
        "case_id": "o8_buildup_neutron_rp",
        "authority_id": "batch0001",
        "geometry": "s3d_o8",
        "mode": "buildup",
        "family": "n",
        "job_name": "Background_n_fullsphere20_rep01_part01",
        "event_id": 157,
        "required_markers": ("tes", "o8_bgo", "o8_plastic", "native_rp"),
    },
    {
        "case_id": "mass_buildup_alpha_rp",
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "mode": "buildup",
        "family": "alpha",
        "job_name": "Background_alpha_fullsphere20_rep01_part01",
        "event_id": 20,
        "required_markers": ("tes", "mass_csi", "native_rp"),
    },
)

ZERO_RP_SPEC = {
    "case_id": "o8_buildup_muminus_zero_rp_positive_tt",
    "authority_id": "batch0001",
    "geometry": "s3d_o8",
    "mode": "buildup",
    "family": "muminus",
    "job_name": "Background_muminus_fullsphere20_rep01_part01",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _verify_file_anywhere(path_value: str | Path, expected: str) -> Path:
    lexical = Path(path_value)
    lexical = lexical if lexical.is_absolute() else ROOT / lexical
    reject_lexical_symlinks(lexical)
    state = os.lstat(lexical)
    if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise FileNotFoundError(f"missing, linked, or non-regular frozen file: {lexical}")
    path = lexical.resolve(strict=True)
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"hash drift for {path}: {actual} != {expected}")
    return path


def _all_int_seeds(value: Any, key: str | None = None) -> Iterable[int]:
    if key == "seed" and isinstance(value, int) and not isinstance(value, bool):
        yield value
    elif key == "seeds" and isinstance(value, list):
        for item in value:
            if isinstance(item, int) and not isinstance(item, bool):
                yield item
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _all_int_seeds(child, child_key)
    elif isinstance(value, list) and key != "seeds":
        for child in value:
            yield from _all_int_seeds(child)


def load_registered_seeds() -> tuple[set[int], list[dict[str, Any]]]:
    registered: set[int] = set()
    authorities: list[dict[str, Any]] = []
    for authority_id, spec in sorted(SEED_AUTHORITIES.items()):
        path = _verify_file_anywhere(spec["path"], spec["sha256"])
        ledger = strict_json(path)
        if ledger.get("status") != spec["status"]:
            raise ValueError(f"{authority_id}: seed authority status drift")
        seeds = set(_all_int_seeds(ledger))
        if not seeds:
            raise ValueError(f"{authority_id}: no registered seeds found")
        registered.update(seeds)
        authorities.append(
            {
                "authority_id": authority_id,
                "path": spec["path"],
                "sha256": spec["sha256"],
                "status": spec["status"],
                "unique_seed_count": len(seeds),
            }
        )
    return registered, authorities


def deterministic_seeds(registered: set[int]) -> list[dict[str, Any]]:
    """Produce one seed per cell/shard, paired across geometry and output arm."""
    records: list[dict[str, Any]] = []
    selected: set[int] = set()
    for cell_index, (family, mode) in enumerate(CELLS):
        for shard_index in range(len(CELL_COUNTS[(family, mode)])):
            label = f"m05-complete-compact-smoke-v1|{cell_index}|{family}|{mode}|{shard_index}"
            nonce = 0
            while True:
                digest = hashlib.sha256(f"{label}|{nonce}".encode("utf-8")).digest()
                seed = 100_000_000 + int.from_bytes(digest[:8], "big") % 900_000_000
                if seed not in registered and seed not in selected:
                    break
                nonce += 1
            selected.add(seed)
            records.append(
                {
                    "cell": f"{family}_{mode}",
                    "family": family,
                    "mode": mode,
                    "shard_index": shard_index,
                    "seed": seed,
                    "derivation_label": label,
                    "collision_nonce": nonce,
                    "paired_scope": "same cell/shard seed for F/C/U/N1 and both geometries",
                }
            )
    expected = sum(len(counts) for counts in CELL_COUNTS.values())
    if expected != 56 or len(records) != expected or len(selected) != expected or selected & registered:
        raise ValueError("new seed uniqueness/registry closure failed")
    return records


def load_geometry_bundles() -> dict[str, Any]:
    ledger = load_authority("batch0001")
    bundles = ledger.get("geometry_bundles")
    if not isinstance(bundles, dict) or set(bundles) != set(GEOMETRIES):
        raise ValueError("canonical geometry bundle set drift")
    output: dict[str, Any] = {}
    for geometry in GEOMETRIES:
        bundle = bundles[geometry]
        if bundle.get("file_count") != len(bundle.get("files", [])) or bundle.get("file_count") != 6:
            raise ValueError(f"{geometry}: geometry file-count drift")
        records = []
        for item in bundle["files"]:
            path = _verify_file_anywhere(item["path"], item["sha256"])
            records.append(
                {
                    "path": item["path"],
                    "absolute_path": str(path),
                    "sha256": item["sha256"],
                    "size_bytes": path.stat().st_size,
                }
            )
        digest_input = "".join(
            f"{item['path']}\0{item['sha256']}\n" for item in sorted(bundle["files"], key=lambda row: row["path"])
        )
        digest = sha256_bytes(digest_input.encode("utf-8"))
        if digest != bundle["bundle_sha256"]:
            raise ValueError(f"{geometry}: bundle digest closure failed")
        setup_path = _verify_file_anywhere(
            bundle["setup"],
            next(item["sha256"] for item in bundle["files"] if item["path"] == bundle["setup"]),
        )
        output[geometry] = {
            "bundle_sha256": digest,
            "digest_contract": bundle["digest_contract"],
            "file_count": 6,
            "files": records,
            "setup_path": bundle["setup"],
            "setup_absolute_path": str(setup_path),
            "setup_sha256": sha256(setup_path),
        }
    return output


def load_shadow_build() -> dict[str, Any]:
    if not SHADOW_MANIFEST.is_file():
        raise FileNotFoundError(f"WAIT: required shadow manifest is absent: {SHADOW_MANIFEST}")
    manifest = assert_canonical_json(SHADOW_MANIFEST)
    if manifest.get("status") != "PASS__SHADOW_BUILD_ONLY__EXECUTABLE_NOT_RUN":
        raise ValueError("shadow build status is not the required unexecuted PASS")
    if manifest.get("transport_events_launched") != 0:
        raise ValueError("shadow build manifest reports transport")
    if manifest.get("no_needed_libCosima") is not True or "libCosima" in manifest.get("readelf_dynamic", ""):
        raise ValueError("shadow binary dependency isolation failed")
    if manifest.get("scorer_rng_source_scan", {}).get("status") != "PASS":
        raise ValueError("shadow scorer source RNG scan failed")
    if manifest.get("scorer_rng_undefined_symbol_scan") != "PASS__ONLY_ALLOWLISTED_HEADER_INITIALIZER":
        raise ValueError("shadow scorer symbol RNG scan failed")
    binary = _verify_file_anywhere(manifest["binary_path"], manifest["binary_sha256"])
    if binary.stat().st_size != manifest["binary_size_bytes"]:
        raise ValueError("shadow binary size drift")
    return {
        "manifest_path": rel(SHADOW_MANIFEST),
        "manifest_sha256": sha256(SHADOW_MANIFEST),
        "manifest_size_bytes": SHADOW_MANIFEST.stat().st_size,
        "status": manifest["status"],
        "transport_events_launched": 0,
        "binary_path": str(binary),
        "binary_sha256": manifest["binary_sha256"],
        "binary_size_bytes": manifest["binary_size_bytes"],
        "no_needed_libCosima": True,
        "scorer_rng_source_scan": "PASS",
        "scorer_rng_undefined_symbol_scan": "PASS",
    }


def load_preload_observer_build() -> dict[str, Any]:
    """Load the dormant build-only witness without treating it as P12 closure."""

    reject_lexical_symlinks(PRELOAD_OBSERVER_MANIFEST)
    if not PRELOAD_OBSERVER_MANIFEST.is_file() or os.lstat(PRELOAD_OBSERVER_MANIFEST).st_nlink != 1:
        raise FileNotFoundError(f"WAIT: required preload-observer manifest is absent/non-regular: {PRELOAD_OBSERVER_MANIFEST}")
    manifest = assert_canonical_json(PRELOAD_OBSERVER_MANIFEST)
    if (
        manifest.get("status") != "PASS__PRELOAD_OBSERVER_BUILD_ONLY__NOT_EXECUTED"
        or manifest.get("artifact_is_transport_authority") is not False
        or manifest.get("transport_events_launched") != 0
        or manifest.get("runtime_state") != "DORMANT__NO_COSIMA_OR_EVENTLIST_EXECUTION"
        or manifest.get("compiler_dependency_mode") != "-MD__INCLUDING_SYSTEM_HEADERS"
        or manifest.get("needed_libCosima_absent") is not True
    ):
        raise ValueError("preload observer is not the required dormant/full-dependency build-only candidate")
    source = manifest.get("source", {})
    observer_source = PACKAGE / "code/preload_observer/M05GPSPreloadObserver.cc"
    if (
        source.get("path") != rel(observer_source)
        or source.get("sha256") != sha256(observer_source)
        or source.get("size_bytes") != observer_source.stat().st_size
    ):
        raise ValueError("preload observer source drift after compile-only build")
    build_root = PRELOAD_OBSERVER_MANIFEST.parent.resolve(strict=True)
    binary_lexical = Path(manifest.get("binary", {}).get("path", ""))
    dependency_lexical = Path(manifest.get("compiler_dependency_file", {}).get("path", ""))
    for lexical, binding, label in (
        (binary_lexical, manifest.get("binary", {}), "binary"),
        (dependency_lexical, manifest.get("compiler_dependency_file", {}), "dependency file"),
    ):
        reject_lexical_symlinks(lexical)
        state = os.lstat(lexical)
        path = lexical.resolve(strict=True)
        try:
            path.relative_to(build_root)
        except ValueError as exc:
            raise ValueError(f"preload observer {label} escapes its build root") from exc
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 1
            or sha256(path) != binding.get("sha256")
            or path.stat().st_size != binding.get("size_bytes")
        ):
            raise ValueError(f"preload observer {label} binding drift")
    closure = manifest.get("compiler_dependency_closure")
    if not isinstance(closure, list) or len(closure) < 100:
        raise ValueError("preload observer full compiler dependency closure is absent")
    seen_dependencies: set[str] = set()
    for binding in closure:
        if not isinstance(binding, dict) or set(binding) != {
            "is_symlink", "lexical_path", "resolved_path", "sha256", "size_bytes",
        }:
            raise ValueError("preload observer compiler dependency record schema drift")
        lexical = Path(binding["lexical_path"])
        if str(lexical) in seen_dependencies:
            raise ValueError("duplicate preload compiler dependency")
        seen_dependencies.add(str(lexical))
        state = os.lstat(lexical)
        is_symlink = stat.S_ISLNK(state.st_mode)
        resolved = lexical.resolve(strict=True)
        if (
            is_symlink != binding["is_symlink"]
            or str(resolved) != binding["resolved_path"]
            or not resolved.is_file()
            or sha256(resolved) != binding["sha256"]
            or resolved.stat().st_size != binding["size_bytes"]
        ):
            raise ValueError(f"preload observer compiler dependency drift: {lexical}")
    if manifest.get("actual_compile_mcrun_header", {}).get("is_symlink") is not True:
        raise ValueError("preload observer did not bind the lexical installed MCRun header")
    binary = binary_lexical.resolve(strict=True)
    validator = _verify_file_anywhere(PRELOAD_VALIDATOR, sha256(PRELOAD_VALIDATOR))
    schema = _verify_file_anywhere(PRELOAD_SCHEMA, sha256(PRELOAD_SCHEMA))
    validator_python = Path(sys.executable).resolve(strict=True)
    return {
        "manifest_path": rel(PRELOAD_OBSERVER_MANIFEST),
        "manifest_sha256": sha256(PRELOAD_OBSERVER_MANIFEST),
        "manifest_size_bytes": PRELOAD_OBSERVER_MANIFEST.stat().st_size,
        "status": manifest["status"],
        "artifact_is_transport_authority": False,
        "transport_events_launched": 0,
        "binary_path": str(binary),
        "binary_sha256": manifest["binary"]["sha256"],
        "binary_size_bytes": manifest["binary"]["size_bytes"],
        "compiler_dependency_file_sha256": manifest["compiler_dependency_file"]["sha256"],
        "compiler_dependency_count": len(closure),
        "needed_libCosima_absent": True,
        "validator_path": str(validator),
        "validator_sha256": sha256(validator),
        "validator_size_bytes": validator.stat().st_size,
        "validator_python_path": str(validator_python),
        "validator_python_sha256": sha256(validator_python),
        "schema_path": str(schema),
        "schema_sha256": sha256(schema),
        "schema_size_bytes": schema.stat().st_size,
        "sentinel_status": "NOT_EXECUTED__P12_REMAINS_BLOCKED",
    }


def load_durable_consumer_fixture() -> dict[str, Any]:
    """Verify and bind the durable real MFileEventsSim/Revan zero-transport commit."""

    if sha256(DURABLE_CONSUMER_COMMIT) != DURABLE_CONSUMER_COMMIT_SHA256:
        raise ValueError("durable standalone-consumer commit hash drift")
    commit = assert_canonical_json(DURABLE_CONSUMER_COMMIT)
    if (
        commit.get("schema_version") != "m05-standalone-consumer-durable-fixture-v1"
        or commit.get("status") != "PASS__DURABLE_REAL_MFILEEVENTSSIM_AND_REVAN_ZERO_TRANSPORT_FIXTURE"
        or commit.get("scope", {}).get("transport_events_launched") != 0
        or commit.get("scope", {}).get("cosima_invoked") is not False
        or commit.get("scope", {}).get("eventlist_transport_invoked") is not False
        or commit.get("observations", {}).get("mfileeventssim_roundtrip", {}).get("status")
        != "PASS__REAL_MFILEEVENTSSIM_ROUNDTRIP__REAL_REVAN_INPUT_AND_ANALYZE"
        or commit.get("observations", {}).get("revan", {}).get("status")
        != "PASS__REAL_REVAN_CONSUMER_RECONSTRUCTION"
    ):
        raise ValueError("durable standalone-consumer status/scope drift")
    files = commit.get("files")
    if not isinstance(files, dict) or len(files) != 17:
        raise ValueError("durable standalone-consumer file manifest is incomplete")
    for label, binding in files.items():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "size_bytes"}:
            raise ValueError(f"durable consumer file binding schema drift: {label}")
        path = _verify_file_anywhere(binding["path"], binding["sha256"])
        if path.stat().st_size != binding["size_bytes"]:
            raise ValueError(f"durable consumer file size drift: {label}")
    observations = commit["observations"]
    if (
        observations["mfileeventssim_roundtrip"].get("event_count") != 5
        or observations["mfileeventssim_roundtrip"].get("ia_count") != 5
        or observations["mfileeventssim_roundtrip"].get("unique_init_count") != 5
        or observations["revan"].get("counts", {}).get("standalone_event_count") != 5
    ):
        raise ValueError("durable consumer event/IA/Revan count closure drift")
    return {
        "commit_path": rel(DURABLE_CONSUMER_COMMIT),
        "commit_sha256": DURABLE_CONSUMER_COMMIT_SHA256,
        "commit_size_bytes": DURABLE_CONSUMER_COMMIT.stat().st_size,
        "status": commit["status"],
        "transport_events_launched": 0,
        "bound_file_count": len(files),
        "mfileeventssim_roundtrip": observations["mfileeventssim_roundtrip"],
        "revan": observations["revan"],
    }


def load_execution_status() -> dict[str, Any]:
    value = assert_canonical_json(EXECUTION_STATUS)
    if (
        value.get("benchmark_class") != BENCHMARK_CLASS
        or value.get("transport_authorized") is not False
        or value.get("transport_events_launched") != 0
        or value.get("merge_eligible") is not False
        or "TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW" not in value.get("status", "")
        or value.get("evaluator_feedback_path") != rel(FEEDBACK_PATH)
        or value.get("evaluator_feedback_sha256") != FEEDBACK_SHA256
        or value.get("contract_path") != rel(CONTRACT_PATH)
        or value.get("contract_sha256") != CONTRACT_SHA256
    ):
        raise ValueError("terminal execution status is not fail-closed or feedback02-bound")
    return {
        "path": rel(EXECUTION_STATUS),
        "sha256": sha256(EXECUTION_STATUS),
        "size_bytes": EXECUTION_STATUS.stat().st_size,
        "status": value["status"],
        "phase": value["phase"],
        "transport_authorized": False,
        "transport_events_launched": 0,
    }


def load_production_binary() -> dict[str, Any]:
    sources = assert_canonical_json(EXTERNAL_SOURCES)
    matches = [row for row in sources["installed_execution_authorities"] if row["authority_id"] == "production_cosima"]
    if len(matches) != 1:
        raise ValueError("production Cosima identity is not unique")
    row = matches[0]
    path = _verify_file_anywhere(row["absolute_path"], row["sha256"])
    if path.stat().st_size != row["size_bytes"]:
        raise ValueError("production Cosima size drift")
    return {
        "external_sources_path": rel(EXTERNAL_SOURCES),
        "external_sources_sha256": sha256(EXTERNAL_SOURCES),
        "binary_path": str(path),
        "binary_sha256": row["sha256"],
        "binary_size_bytes": row["size_bytes"],
        "version_probe": row["version_probe"],
    }


def load_unit_test_evidence() -> dict[str, Any]:
    if not UNIT_TEST_EVIDENCE.is_file() or not UNIT_TEST_LOG.is_file():
        raise FileNotFoundError("WAIT: fixed preflight unit-test log/evidence is absent")
    evidence = assert_canonical_json(UNIT_TEST_EVIDENCE)
    if (
        evidence.get("status") != "PASS__PREFLIGHT_UNIT_TESTS__NO_TRANSPORT"
        or evidence.get("exit_code") != 0
        or evidence.get("transport_events_launched") != 0
    ):
        raise ValueError("preflight unit-test evidence is not a zero-exit/no-transport PASS")
    if evidence.get("log_path") != rel(UNIT_TEST_LOG) or evidence.get("log_sha256") != sha256(UNIT_TEST_LOG):
        raise ValueError("preflight unit-test log binding failed")
    test_path = PACKAGE / "tests/test_preflight.py"
    if evidence.get("test_path") != rel(test_path) or evidence.get("test_sha256") != sha256(test_path):
        raise ValueError("preflight unit-test source drift after execution")
    if evidence.get("tested_file_manifest") != tested_file_manifest():
        raise ValueError("tested implementation/schema source drift after unit-test execution")
    consumers = evidence.get("real_consumer_authorities")
    if not isinstance(consumers, dict) or set(consumers) != {
        "M05_MFILE_CONSUMER", "M05_TEST_GEOMETRY", "M05_REVAN_EXECUTABLE", "FROZEN_REVAN_CONFIG",
    }:
        raise ValueError("required real MFileEventsSim/Revan consumer evidence is absent")
    for name, binding in consumers.items():
        path = Path(binding.get("absolute_path", ""))
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256(path) != binding.get("sha256")
            or path.stat().st_size != binding.get("size_bytes")
        ):
            raise ValueError(f"real consumer authority drift after unit tests: {name}")
    if b"skipped" in UNIT_TEST_LOG.read_bytes().lower():
        raise ValueError("formal unit-test log contains a skipped real-consumer gate")
    return {
        "evidence_path": rel(UNIT_TEST_EVIDENCE),
        "evidence_sha256": sha256(UNIT_TEST_EVIDENCE),
        "evidence_size_bytes": UNIT_TEST_EVIDENCE.stat().st_size,
        "log_path": rel(UNIT_TEST_LOG),
        "log_sha256": sha256(UNIT_TEST_LOG),
        "log_size_bytes": UNIT_TEST_LOG.stat().st_size,
        "command_argv": evidence["command_argv"],
        "exit_code": 0,
        "status": evidence["status"],
        "real_consumer_authorities": consumers,
    }


def _map_stage_path(value: str, stage: Path, final_root: Path) -> str:
    path = ROOT / value
    relative = path.resolve().relative_to(stage.resolve())
    return rel(final_root / relative)


def _remap_tape_manifest(cells: list[dict[str, Any]], stage: Path, final_root: Path) -> None:
    for cell in cells:
        cell["cell_manifest_path"] = _map_stage_path(cell["cell_manifest_path"], stage, final_root)
        for shard in cell["shards"]:
            shard["tape_path"] = _map_stage_path(shard["tape_path"], stage, final_root)
            shard["root_sidecar_path"] = _map_stage_path(shard["root_sidecar_path"], stage, final_root)


def build_tape_manifest(stage: Path, final_root: Path, authorities: list[dict[str, Any]]) -> dict[str, Any]:
    tape_root = stage / "tapes"
    cells: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    for family, mode in CELLS:
        cell = build_cell_tapes(family, mode, tape_root)
        committed_cell_dir = ROOT / Path(cell["cell_manifest_path"]).parent
        cell_check = validate_cell_manifest(committed_cell_dir)
        if cell_check["event_count"] != cell["events"] or cell_check["shard_count"] != 4:
            raise ValueError("atomic tape cell-manifest validation failed")
        cells.append(cell)
        for shard in cell["shards"]:
            tape = ROOT / shard["tape_path"]
            sidecar = ROOT / shard["root_sidecar_path"]
            checked = validate_sidecar(tape, sidecar)
            if checked["event_count"] != shard["event_count"]:
                raise ValueError("tape validation count mismatch")
            validation_rows.append({"cell": cell["cell"], "shard_index": shard["shard_index"], **checked})
    _remap_tape_manifest(cells, stage, final_root)
    total_events = sum(cell["events"] for cell in cells)
    if total_events != 27_200 or len(validation_rows) != 56:
        raise ValueError("full seven-family representation-smoke tape-count closure failed")
    return {
        "schema_version": 1,
        "status": "PASS__FROZEN_TAPES_AND_ROOT_SIDECARS_VALIDATED__TRANSPORT_NOT_RUN",
        "benchmark_class": BENCHMARK_CLASS,
        "transport_authorized": False,
        "transport_events_launched": 0,
        "primary_state_scope": (
            "The same 56 tapes are reused by both geometries and F/C/U/N1. This proves matched initial states only; "
            "post-transport event identity is never assumed across geometries."
        ),
        "root_driver_contract": (
            "Every row freezes row/global index, EventList ID, stable root ID, atmospheric driver, family/mode, "
            "source-card, all 20 corrected spectra/fluxes, corrected source-contract provenance, exact raw/binary64 "
            "tuple and expected normalized comparison hash. stable_root_id is only ordered benchmark identity."
        ),
        "rng_contract": "The EventList reader and compact scorer must consume no scorer RNG; transport seeds are separate below.",
        "source_contract_path": rel(SOURCE_CONTRACT),
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "retained_cassette_authorities_not_tape_donors": authorities,
        "geometry_mode_family_cell_count": 28,
        "unique_family_mode_tape_cell_count": 14,
        "shard_count": 56,
        "unique_primary_state_count": total_events,
        "cells": cells,
        "sidecar_validations": validation_rows,
    }


def _cell_record(tape_manifest: dict[str, Any], family: str, mode: str) -> dict[str, Any]:
    matches = [row for row in tape_manifest["cells"] if (row["family"], row["mode"]) == (family, mode)]
    if len(matches) != 1:
        raise ValueError("tape cell resolution failed")
    return matches[0]


def _source_card_text(
    *,
    geometry: dict[str, Any],
    family: str,
    mode: str,
    shard_index: int,
    events: int,
    seed: int,
    arm: str,
    tape_absolute: Path,
    output_prefix: Path,
) -> str:
    run_name = f"M05_{family}_{mode}_s{shard_index}_{arm}"
    lines = [
        "# NON_MERGEABLE_BENCHMARK: isolated matched M05 compact smoke",
        "# Frozen EventList is the only source input; no spectrum/beam/flux source is permitted.",
        f"# canonical_geometry_bundle_sha256={geometry['bundle_sha256']}",
        f"# corrected_source_contract_sha256={SOURCE_CONTRACT_SHA256}",
        f"Geometry {geometry['setup_absolute_path']}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreOneHitPerEvent false",
        "StoreIsotopes true",
    ]
    if mode == "buildup":
        lines.append("DecayMode ActivationBuildUp")
    isotope_base = (
        output_prefix.with_name(output_prefix.name + ".m05cc.partial") / "native"
        if arm in {"C", "N1"}
        else Path(str(output_prefix) + ".dat")
    )
    lines.extend(
        [
            "DetectorTimeConstant 1e-9",
            "StoreTextScientific true 17",
            "PreTriggerMode Everything",
            "",
            f"Run {run_name}",
            f"{run_name}.Events {events}",
        ]
    )
    if arm in {"F", "U"}:
        lines.append(f"{run_name}.FileName {output_prefix}")
    lines.extend(
        [
            f"{run_name}.IsotopeProductionFile {isotope_base}",
            f"{run_name}.Source FrozenPrimary",
            f"FrozenPrimary.EventList {tape_absolute}",
            "",
        ]
    )
    return "\n".join(lines)


def validate_source_card(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    forbidden = ("cosima_spectra_dp_2602units", "Spectrum File", ".Spectrum", ".Flux", ".Beam", ".ParticleType")
    found = [token for token in forbidden if token in text]
    if found:
        raise ValueError(f"{path}: forbidden non-EventList source tokens: {found}")
    event_lists = [line for line in lines if ".EventList " in line]
    if event_lists != [f"FrozenPrimary.EventList {expected['tape_absolute_path']}"]:
        raise ValueError(f"{path}: EventList-only source closure failed")
    if any(line.startswith("Seed ") for line in lines):
        raise ValueError(f"{path}: global Seed is not an installed MCParameterFile keyword; use CLI -s")
    if lines.count(f"Geometry {expected['geometry_setup_absolute_path']}") != 1:
        raise ValueError(f"{path}: geometry mismatch")
    if lines.count("PhysicsListHD qgsp-bic-hp") != 1 or lines.count("PhysicsListEM LivermorePol") != 1:
        raise ValueError(f"{path}: physics-list mismatch")
    if (
        lines.count("StoreSimulationInfo all") != 1
        or lines.count("StoreOneHitPerEvent false") != 1
        or lines.count("StoreIsotopes true") != 1
        or lines.count("DetectorTimeConstant 1e-9") != 1
        or lines.count("StoreTextScientific true 17") != 1
        or lines.count("PreTriggerMode Everything") != 1
    ):
        raise ValueError(f"{path}: matched rich-construction contract missing")
    has_decay = "DecayMode ActivationBuildUp" in lines
    if has_decay != (expected["mode"] == "buildup"):
        raise ValueError(f"{path}: prompt/BUILDUP mode mismatch")
    file_names = [line for line in lines if ".FileName " in line]
    if bool(file_names) != (expected["arm"] in {"F", "U"}) or len(file_names) > 1:
        raise ValueError(f"{path}: native rich-output arm mismatch")
    isotope_lines = [line for line in lines if ".IsotopeProductionFile " in line]
    if len(isotope_lines) != 1 or isotope_lines[0].split(maxsplit=1)[1] != expected["isotope_base_absolute_path"]:
        raise ValueError(f"{path}: native isotope/TT output is not unique")
    return {"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size, "status": "PASS"}


def transport_argv(binary_path: str, arm: str, seed: int, source_card: Path) -> list[str]:
    """Return installed-MCMain-compatible argv; the parameter file is the final bare argument.

    MCMain's ``-f`` is an incarnation ID, not a source-card flag.  Its ``-s``
    is the executable seed authority; ``Seed`` is not an MCParameterFile
    keyword even though retained generated cards keep it as provenance text.
    """
    if arm not in ARMS or not 0 < seed < 1_000_000_000:
        raise ValueError("invalid arm or nine-digit transport seed")
    argv = [binary_path]
    option = ARM_DESCRIPTIONS[arm]["argv_option"]
    if option is not None:
        argv.append(option)
    argv.extend(["-s", str(seed), str(source_card.resolve())])
    return argv


def build_cards_and_jobs(
    stage: Path,
    final_root: Path,
    tape_manifest: dict[str, Any],
    seed_records: list[dict[str, Any]],
    geometries: dict[str, Any],
    production: dict[str, Any],
    shadow: dict[str, Any],
    preload_observer: dict[str, Any],
    geometry_classification_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seed_map = {(row["family"], row["mode"], row["shard_index"]): row["seed"] for row in seed_records}
    jobs: list[dict[str, Any]] = []
    card_validations: list[dict[str, Any]] = []
    blocked_n0: list[dict[str, Any]] = []
    for geometry_index, geometry_name in enumerate(GEOMETRIES):
        geometry = geometries[geometry_name]
        for cell_index, (family, mode) in enumerate(CELLS):
            cell = _cell_record(tape_manifest, family, mode)
            for shard in cell["shards"]:
                shard_index = shard["shard_index"]
                seed = seed_map[(family, mode, shard_index)]
                arm_order = arm_order_for(geometry_index, cell_index, shard_index)
                base_id = f"{geometry_name}__{family}_{mode}__s{shard_index:04d}"
                blocked_n0.append(
                    {
                        "slot_id": f"{base_id}__N0",
                        "geometry": geometry_name,
                        "family": family,
                        "mode": mode,
                        "shard_index": shard_index,
                        "events": shard["event_count"],
                        "seed": seed,
                        "runnable": False,
                        "source_card_path": None,
                        "command_argv": None,
                        "status": "BLOCKED__NO_SAFE_EXTENSION_POINT_TO_DISABLE_RICH_RECORD_CONSTRUCTION",
                        "inference_boundary": (
                            "N0 absence forbids any claim separating transport stepping from rich-object construction."
                        ),
                    }
                )
                tape_path = ROOT / shard["tape_path"]
                sidecar_path = ROOT / shard["root_sidecar_path"]
                # During staging the final paths do not yet exist; their content hashes are already frozen.
                if not (stage / tape_path.relative_to(final_root)).is_file():
                    raise ValueError("staged tape mapping failed")
                for order_slot, arm in enumerate(arm_order):
                    job_id = f"{base_id}__{arm}"
                    card_final = final_root / "cards" / geometry_name / f"{job_id}.source"
                    card_stage = stage / card_final.relative_to(final_root)
                    output_final = final_root / "planned_outputs" / geometry_name / family / mode / job_id
                    output_stage_dir = stage / output_final.parent.relative_to(final_root)
                    card_stage.parent.mkdir(parents=True, exist_ok=True)
                    output_stage_dir.mkdir(parents=True, exist_ok=True)
                    text = _source_card_text(
                        geometry=geometry,
                        family=family,
                        mode=mode,
                        shard_index=shard_index,
                        events=shard["event_count"],
                        seed=seed,
                        arm=arm,
                        tape_absolute=tape_path.resolve(),
                        output_prefix=output_final.resolve(),
                    )
                    write_once(card_stage, text.encode("utf-8"))
                    expected = {
                        "tape_absolute_path": str(tape_path.resolve()),
                        "seed": seed,
                        "geometry_setup_absolute_path": geometry["setup_absolute_path"],
                        "mode": mode,
                        "arm": arm,
                        "isotope_base_absolute_path": (
                            str(output_final.resolve()) + ".m05cc.partial/native"
                            if arm in {"C", "N1"}
                            else str(output_final.resolve()) + ".dat"
                        ),
                    }
                    checked = validate_source_card(card_stage, expected)
                    checked["path"] = rel(card_final)
                    card_validations.append(checked)
                    binary = production if arm in {"F", "U"} else shadow
                    argv = transport_argv(binary["binary_path"], arm, seed, card_final)
                    environment: dict[str, str] = {}
                    if arm in {"F", "U"}:
                        observer_directory = Path(str(output_final.resolve()) + ".gpsobs")
                        environment = {
                            "LD_PRELOAD": preload_observer["binary_path"],
                            "TES511_PRELOAD_ARM": arm,
                            "TES511_PRELOAD_TAPE_ROOT_SIDECAR": str(sidecar_path.resolve()),
                            "TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256": shard["root_sidecar_sha256"],
                            "TES511_PRELOAD_OUTPUT_PREFIX": str(output_final.resolve()),
                            "TES511_PRELOAD_ALLOWED_ROOT": str(output_final.parent.resolve()),
                            "TES511_PRELOAD_EXPECTED_LIBCOSIMA": (
                                "/home/ubuntu/MEGAlib_Install/megalib-main/lib/libCosima.so"
                            ),
                            "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256": (
                                "0656a54e0351a72347ad70437a96097b4d37688d10ac9059038e0b697ce6a495"
                            ),
                        }
                        generated_observer_binding = {
                            "implementation": "installed_MCRun_GeneratePrimaries_RTLD_NEXT_preload_observer",
                            "build_manifest_path": preload_observer["manifest_path"],
                            "build_manifest_sha256": preload_observer["manifest_sha256"],
                            "binary_path": preload_observer["binary_path"],
                            "binary_sha256": preload_observer["binary_sha256"],
                            "schema_path": preload_observer["schema_path"],
                            "schema_sha256": preload_observer["schema_sha256"],
                            "validator_path": preload_observer["validator_path"],
                            "validator_sha256": preload_observer["validator_sha256"],
                            "validator_python_path": preload_observer["validator_python_path"],
                            "validator_python_sha256": preload_observer["validator_python_sha256"],
                            "planned_observer_directory": str(observer_directory),
                            "validation_argv": [
                                preload_observer["validator_python_path"], preload_observer["validator_path"],
                                "--observer-directory", str(observer_directory),
                                "--tape", str(tape_path.resolve()),
                                "--tape-root-sidecar", str(sidecar_path.resolve()),
                                "--arm", arm,
                            ],
                            "completion_scope": "observer transaction only; outer atomic job receipt remains mandatory",
                            "runtime_validation_status": "NOT_EXECUTED__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW",
                        }
                    else:
                        environment = {
                            "TES511_SMOKE_ARM": arm,
                            "TES511_GEOMETRY": geometry_name,
                            "TES511_MODE": mode,
                            "TES511_FAMILY": family,
                            "TES511_JOB_ID": job_id,
                            "TES511_SHARD_INDEX": str(shard_index),
                            "TES511_SEED": str(seed),
                            "TES511_TAPE_ROOT_SIDECAR": str(sidecar_path.resolve()),
                            "TES511_TAPE_ROOT_SIDECAR_SHA256": shard["root_sidecar_sha256"],
                            "TES511_OUTPUT_PREFIX": str(output_final.resolve()),
                            "TES511_ALLOWED_RUN_DIRECTORY": str(output_final.parent.resolve()),
                            "TES511_GEOMETRY_BUNDLE_SHA256": geometry["bundle_sha256"],
                            "TES511_RUNTIME_SOURCE_CARD_SHA256": checked["sha256"],
                            "TES511_CORRECTED_SOURCE_CARD_SHA256": cell["source_card_sha256"],
                            "TES511_SOURCE_CONTRACT_SHA256": SOURCE_CONTRACT_SHA256,
                            "TES511_RECORD_SCHEMA_SHA256": sha256(RECORD_SCHEMA),
                            "TES511_N1_COMMIT_SCHEMA_SHA256": sha256(N1_COMMIT_SCHEMA),
                            "TES511_VETO_WHITELIST_SHA256": sha256(ACTIVE_WHITELIST),
                            "TES511_GEOMETRY_CLASSIFICATION_SHA256": geometry_classification_sha256,
                        }
                        m05cc_directory = str(output_final.resolve()) + ".m05cc"
                        classification_path = str(final_root.resolve() / "geometry_classification_manifest.json")
                        if arm == "C":
                            planned_commit = m05cc_directory + "/record_bundle.json"
                            generated_observer_binding = {
                                "implementation": "isolated_shadow_post_GPS_compact_scorer_hook",
                                "planned_observations_path": m05cc_directory + "/generated_observations.tsv",
                                "planned_commit_path": planned_commit,
                                "commit_contract": "m05cc-v2-record-bundle__C_ONLY",
                                "record_schema_path": rel(RECORD_SCHEMA),
                                "record_schema_sha256": sha256(RECORD_SCHEMA),
                                "validator_path": rel(RECORD_VALIDATOR),
                                "validator_sha256": sha256(RECORD_VALIDATOR),
                                "validation_argv": [
                                    sys.executable, str(RECORD_VALIDATOR), planned_commit,
                                    "--schema", str(RECORD_SCHEMA),
                                    "--whitelist", str(ACTIVE_WHITELIST),
                                    "--geometry-classification", classification_path,
                                ],
                                "runtime_validation_status": "NOT_EXECUTED__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW",
                            }
                        else:
                            planned_commit = m05cc_directory + "/commit.json"
                            generated_observer_binding = {
                                "implementation": "isolated_shadow_post_GPS_N1_root_observer_hook",
                                "planned_observations_path": m05cc_directory + "/generated_observations.tsv",
                                "planned_commit_path": planned_commit,
                                "commit_contract": "m05cc-n1-v1-commit__N1_ONLY__NOT_MATERIALIZER_INPUT",
                                "record_schema_path": rel(N1_COMMIT_SCHEMA),
                                "record_schema_sha256": sha256(N1_COMMIT_SCHEMA),
                                "validator_path": rel(N1_COMMIT_VALIDATOR),
                                "validator_sha256": sha256(N1_COMMIT_VALIDATOR),
                                "validation_argv": [
                                    sys.executable, str(N1_COMMIT_VALIDATOR), planned_commit,
                                    "--eventlist", str(tape_path.resolve()),
                                    "--runtime-source-card", str(card_final.resolve()),
                                    "--geometry-classification", classification_path,
                                    "--schema", str(N1_COMMIT_SCHEMA),
                                    "--whitelist", str(ACTIVE_WHITELIST),
                                    "--expected-output-prefix", str(output_final.resolve()),
                                    "--expected-job-id", job_id,
                                    "--expected-geometry", geometry_name,
                                    "--expected-mode", mode,
                                    "--expected-family", family,
                                    "--expected-shard-index", str(shard_index),
                                    "--expected-seed", str(seed),
                                    "--expected-event-count", str(shard["event_count"]),
                                    "--expected-eventlist-sha256", shard["tape_sha256"],
                                    "--expected-tape-root-sidecar-sha256", shard["root_sidecar_sha256"],
                                    "--expected-runtime-source-card-sha256", checked["sha256"],
                                    "--expected-geometry-bundle-sha256", geometry["bundle_sha256"],
                                    "--expected-geometry-classification-sha256", geometry_classification_sha256,
                                    "--expected-corrected-source-card-sha256", cell["source_card_sha256"],
                                ],
                                "runtime_validation_status": "NOT_EXECUTED__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW",
                            }
                    jobs.append(
                        {
                            "job_id": job_id,
                            "benchmark_class": BENCHMARK_CLASS,
                            "geometry": geometry_name,
                            "geometry_bundle_sha256": geometry["bundle_sha256"],
                            "family": family,
                            "mode": mode,
                            "shard_index": shard_index,
                            "events": shard["event_count"],
                            "arm": arm,
                            "arm_order": list(arm_order),
                            "order_slot": order_slot,
                            "seed": seed,
                            "tape_path": shard["tape_path"],
                            "tape_sha256": shard["tape_sha256"],
                            "root_sidecar_path": shard["root_sidecar_path"],
                            "root_sidecar_sha256": shard["root_sidecar_sha256"],
                            "source_card_path": rel(card_final),
                            "source_card_sha256": checked["sha256"],
                            "source_card_size_bytes": checked["size_bytes"],
                            "output_prefix": rel(output_final),
                            "binary_path": binary["binary_path"],
                            "binary_sha256": binary["binary_sha256"],
                            "command_argv": argv,
                            "environment": environment,
                            "generated_observer_binding": generated_observer_binding,
                            "native_isotope_base": expected["isotope_base_absolute_path"],
                            **planned_job_readiness(arm),
                            "launched": False,
                            "resource_limits": {
                                "wall_timeout_s": {
                                    "gamma": 1800, "n": 3600, "eplus": 2400, "eminus": 2400,
                                    "alpha": 2400, "muminus": 2400, "muplus": 2400,
                                }[family],
                                "terminate_grace_s": 30,
                                "peak_process_group_rss_bytes": (
                                    12 * 1024**3
                                    if geometry_name == "s3d_o8" and family in {
                                        "n", "eplus", "eminus", "alpha", "muminus", "muplus"
                                    }
                                    else 8 * 1024**3
                                ),
                                "per_job_new_bytes": 2_000_000_000,
                                "global_smoke_new_bytes": 10_000_000_000,
                                "minimum_live_disk_reserve_bytes": 20 * 1024**3,
                                "fail_action": "terminate process group; retain partial output; mark NO_GO; do not continue cell",
                            },
                        }
                    )
    if len(jobs) != 448 or len(card_validations) != 448 or len(blocked_n0) != 112:
        raise ValueError("planned/blocked arm-count closure failed")
    if sum(job["events"] for job in jobs) != 217_600:
        raise ValueError("planned transport invocation-event closure failed")
    rich_jobs = [job for job in jobs if job["arm"] in {"F", "U"}]
    compact_jobs = [job for job in jobs if job["arm"] in {"C", "N1"}]
    c_jobs = [job for job in jobs if job["arm"] == "C"]
    n1_jobs = [job for job in jobs if job["arm"] == "N1"]
    required_preload_environment = {
        "LD_PRELOAD", "TES511_PRELOAD_ARM", "TES511_PRELOAD_TAPE_ROOT_SIDECAR",
        "TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256", "TES511_PRELOAD_OUTPUT_PREFIX",
        "TES511_PRELOAD_ALLOWED_ROOT", "TES511_PRELOAD_EXPECTED_LIBCOSIMA",
        "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256",
    }
    if (
        len(rich_jobs) != 224
        or len(compact_jobs) != 224
        or len(c_jobs) != 112
        or len(n1_jobs) != 112
        or any(set(job["environment"]) != required_preload_environment for job in rich_jobs)
        or any(job["environment"]["LD_PRELOAD"] != preload_observer["binary_path"] for job in rich_jobs)
        or any(job["generated_observer_binding"]["binary_sha256"] != preload_observer["binary_sha256"] for job in rich_jobs)
        or any("LD_PRELOAD" in job["environment"] for job in compact_jobs)
        or any(
            job["generated_observer_binding"]["planned_commit_path"].endswith("/record_bundle.json") is False
            or job["generated_observer_binding"]["record_schema_sha256"] != sha256(RECORD_SCHEMA)
            or job["generated_observer_binding"]["validator_sha256"] != sha256(RECORD_VALIDATOR)
            for job in c_jobs
        )
        or any(
            job["generated_observer_binding"]["planned_commit_path"].endswith("/commit.json") is False
            or job["generated_observer_binding"]["record_schema_sha256"] != sha256(N1_COMMIT_SCHEMA)
            or job["generated_observer_binding"]["validator_sha256"] != sha256(N1_COMMIT_VALIDATOR)
            for job in n1_jobs
        )
        or any(
            job["environment"].get("TES511_N1_COMMIT_SCHEMA_SHA256") != sha256(N1_COMMIT_SCHEMA)
            for job in compact_jobs
        )
    ):
        raise ValueError("F/U preload observer or C/N1 shadow generated-observer binding closure failed")
    return jobs, blocked_n0, card_validations


def _event_evidence(sim: Path, event_id: int) -> dict[str, Any]:
    found = False
    active = False
    digest = hashlib.sha256()
    line_count = 0
    records: Counter[str] = Counter()
    marker_counts: Counter[str] = Counter()
    tes_energies: list[float] = []
    markers = {
        "tes": b"TP_L",
        "mass_csi": b"CsI_",
        "o8_bgo": b"BGO_S3",
        "o8_plastic": b"GeoOpt_S2B_CryoShell_Plastic",
        "pair": b"conv",
        "annihilation": b"annihil",
        "native_rp": b"CC IP RP ",
    }
    with gzip.open(sim, "rb") as handle:
        for raw in handle:
            stripped = raw.strip()
            if stripped.startswith(b"ID "):
                if active:
                    raise ValueError(f"event {event_id}: next ID before SE")
                active = int(stripped.split()[1]) == event_id
                if active:
                    if found:
                        raise ValueError(f"event {event_id}: duplicate ID")
                    found = True
            if not active:
                continue
            digest.update(raw)
            line_count += 1
            key = stripped.split(maxsplit=1)[0].decode("ascii") if stripped else "EMPTY"
            records[key] += 1
            for name, needle in markers.items():
                if needle in stripped:
                    marker_counts[name] += 1
            if stripped.startswith(b"HTsim 2;"):
                fields = [field.strip() for field in stripped.decode("ascii").split(";")]
                if len(fields) < 5:
                    raise ValueError("malformed HTsim type-2 cassette row")
                tes_energies.append(float(fields[4]))
            if stripped == b"SE":
                active = False
                break
    if not found or active or line_count == 0:
        raise ValueError(f"event {event_id}: not found or unterminated")
    if records["ID"] != 1 or records["IA"] < 1 or records["SE"] != 1:
        raise ValueError(f"event {event_id}: structural record closure failed")
    tes_sum = sum(tes_energies)
    if tes_energies:
        marker_counts["wide"] = int(480.0 <= tes_sum <= 550.0)
        marker_counts["w2"] = int(510.58 <= tes_sum <= 511.42)
    return {
        "decompressed_event_block_sha256": digest.hexdigest(),
        "line_count": line_count,
        "record_counts": dict(sorted(records.items())),
        "marker_counts": dict(sorted(marker_counts.items())),
        "htsim_type2_multiplicity": len(tes_energies),
        "htsim_type2_sum_keV": tes_sum,
    }


def build_cassette_manifest() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for spec in CASSSETTE_SPECS:
        selector = {key: spec[key] for key in ("job_name", "ordinal") if key in spec}
        ref = resolve_job(
            spec["authority_id"],
            geometry=spec["geometry"],
            mode=spec["mode"],
            family=spec["family"],
            **selector,
        )
        artifacts = ref.bind_artifacts()
        evidence = _event_evidence(ROOT / artifacts["sim"]["path"], spec["event_id"])
        missing = [name for name in spec["required_markers"] if evidence["marker_counts"].get(name, 0) < 1]
        if missing:
            raise ValueError(f"cassette {spec['case_id']} lacks required markers: {missing}")
        cases.append(
            {
                "case_id": spec["case_id"],
                "authority_id": spec["authority_id"],
                "authority_ledger_path": AUTHORITY_REGISTRY[spec["authority_id"]]["path"],
                "authority_ledger_sha256": AUTHORITY_REGISTRY[spec["authority_id"]]["sha256"],
                "geometry": spec["geometry"],
                "mode": spec["mode"],
                "family": spec["family"],
                "selector": selector,
                "event_id": spec["event_id"],
                "required_markers": list(spec["required_markers"]),
                "job_name": ref.job["job_name"],
                "job_seed": ref.job["seed"],
                "job_events": ref.job["events"],
                "artifacts": artifacts,
                "event_evidence": evidence,
            }
        )
    zero = ZERO_RP_SPEC
    zero_ref = resolve_job(
        zero["authority_id"],
        geometry=zero["geometry"],
        mode=zero["mode"],
        family=zero["family"],
        job_name=zero["job_name"],
    )
    zero_artifacts = zero_ref.bind_artifacts()
    tt = float(zero_ref.job["TT_s_from_isotope_dat"])
    rp_count = int(zero_ref.job["isotope_store"]["RP_record_count"])
    if not tt > 0.0 or rp_count != 0:
        raise ValueError("zero-RP positive-TT cassette closure failed")
    return {
        "schema_version": 1,
        "status": "PASS__LEDGER_ONLY_REPRESENTATION_CASSETTE_FROZEN__NOT_A_RATE_SAMPLE",
        "benchmark_class": BENCHMARK_CLASS,
        "transport_events_launched": 0,
        "discovery_contract": (
            "Every selector resolves through the two fixed manifest_discovery ledger authorities. "
            "No live controller state, recursive receipt discovery, or unpaired batch0003 ordinal 77 is eligible."
        ),
        "purpose": (
            "Structural regression only: TES/W2/wide-window, multiplicity, pair/annihilation ancestry, typed veto, "
            "heavy e+/n/alpha and BUILDUP RP/zero-RP TT representation. Never use these hand-selected events for rates."
        ),
        "event_case_count": len(cases),
        "cases": cases,
        "zero_rp_positive_tt_case": {
            "case_id": zero["case_id"],
            "authority_id": zero["authority_id"],
            "authority_ledger_path": AUTHORITY_REGISTRY[zero["authority_id"]]["path"],
            "authority_ledger_sha256": AUTHORITY_REGISTRY[zero["authority_id"]]["sha256"],
            "geometry": zero["geometry"],
            "mode": zero["mode"],
            "family": zero["family"],
            "job_name": zero_ref.job["job_name"],
            "TT_s_from_isotope_dat": tt,
            "RP_record_count": rp_count,
            "artifacts": zero_artifacts,
        },
    }


def _write_canonical(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_once(path, canonical_json_bytes(value))
    assert_canonical_json(path)
    return {"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def publish_wait_contract_then_preflight(
    stage: Path,
    output_root: Path,
    contract_path: Path,
    contract_bytes: bytes,
    *,
    inject_failure_after_contract: bool = False,
) -> None:
    """Publish a fail-closed WAIT contract, then commit the preflight directory.

    A contract without its preflight is explicitly WAIT/non-authorizing.  The
    reverse ordering is forbidden because a committed-looking preflight must
    never point at an absent contract.  Any failed stage is retained under a
    ``.failed`` name for audit.
    """

    if output_root.exists() or contract_path.exists() or not stage.is_dir():
        raise FileExistsError("preflight publication targets/stage are not write-once")
    contract = strict_json_bytes(contract_bytes, source="candidate benchmark contract bytes")
    if (
        canonical_json_bytes(contract) != contract_bytes
        or not str(contract.get("status", "")).startswith("WAIT__")
        or contract.get("transport_authorized") is not False
        or contract.get("transport_events_launched") != 0
    ):
        raise ValueError("only a canonical, fail-closed WAIT contract may precede preflight publication")
    published = False
    try:
        write_once(contract_path, contract_bytes)
        if contract_path.read_bytes() != contract_bytes or sha256(contract_path) != sha256_bytes(contract_bytes):
            raise ValueError("published WAIT contract verification failed")
        if inject_failure_after_contract:
            raise RuntimeError("injected publication failure after WAIT contract")
        rename_no_replace(stage, output_root)
        published = True
        fsync_directory(output_root.parent)
    except BaseException as original:
        try:
            if published:
                quarantine_directory_no_replace(output_root)
            elif stage.exists():
                # Includes a no-replace collision: quarantine only our stage,
                # never the concurrently created final target.
                quarantine_directory_no_replace(stage)
        except BaseException as cleanup:
            raise original from cleanup
        raise


def build_benchmark_contract(
    *,
    generated_utc: str,
    geometries: dict[str, Any],
    production: dict[str, Any],
    shadow: dict[str, Any],
    preload_observer: dict[str, Any],
    durable_consumer: dict[str, Any],
    execution_status: dict[str, Any],
    unit_tests: dict[str, Any],
    representation_mapping: dict[str, Any],
    seed_authorities: list[dict[str, Any]],
    seed_records: list[dict[str, Any]],
    tape_binding: dict[str, Any],
    jobs_binding: dict[str, Any],
    cassette_binding: dict[str, Any],
    projection_binding: dict[str, Any],
    geometry_classification_binding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "WAIT__PREFLIGHT_PARTIAL__P12_SENTINEL_AND_N0_BLOCKED__PENDING_INDEPENDENT_REREVIEW",
        "created_utc": generated_utc,
        "benchmark_class": BENCHMARK_CLASS,
        "merge_eligible": False,
        "transport_authorized": False,
        "transport_events_launched": 0,
        "authorization_boundary": (
            "This write-once contract cannot authorize launch. A second independent evaluator must review the actual "
            "source/build/preflight hashes and issue separate explicit authority before any Cosima event."
        ),
        "governance": {
            "continuation_contract_path": rel(CONTRACT_PATH),
            "continuation_contract_sha256": CONTRACT_SHA256,
            "cumulative_evaluator_feedback": [
                {"path": rel(FEEDBACK01_PATH), "sha256": FEEDBACK01_SHA256},
                {"path": rel(FEEDBACK_PATH), "sha256": FEEDBACK_SHA256},
            ],
        },
        "physics_contract": {
            "geometry_bundles": geometries,
            "physics_list_hd": "qgsp-bic-hp",
            "physics_list_em": "LivermorePol",
            "production_cuts_changed": False,
            "energy_support_changed": False,
            "physics_processes_changed": False,
            "materials_changed": False,
            "source_contract_path": rel(SOURCE_CONTRACT),
            "source_contract_sha256": SOURCE_CONTRACT_SHA256,
            "source_form": "frozen EventList only; no spectrum/beam/flux or mono-511 source",
            "buildup_contract": "DecayMode ActivationBuildUp; native isotope DAT plus exact post-AddIsotope RP sidecar",
        },
        "execution_identities": {
            "production_F_U": production,
            "isolated_shadow_C_N1": shadow,
            "installed_F_U_preload_observer_build_only": preload_observer,
            "durable_real_MFileEventsSim_Revan_zero_transport_fixture": durable_consumer,
            "terminal_execution_status": execution_status,
            "preflight_unit_tests": unit_tests,
            "m05cc_representation_mapping": representation_mapping,
            "geometry_classification_manifest": geometry_classification_binding,
        },
        "arms": {
            **ARM_DESCRIPTIONS,
            "N0": {
                "runnable": False,
                "status": "BLOCKED__NO_SAFE_EXTENSION_POINT_TO_DISABLE_RICH_RECORD_CONSTRUCTION",
                "blocked_slot_count": 112,
                "consequence": (
                    "No pure Geant4 stepping/transport-vs-record-construction causal decomposition or physics-algorithm "
                    "speedup GO may be claimed. Matched F/C end-to-end output-path wall ratios remain reportable."
                ),
            },
        },
        "minimum_stress_cells": [
            {"family": family, "mode": mode, "events_per_geometry": sum(CELL_COUNTS[(family, mode)]), "shards": list(CELL_COUNTS[(family, mode)])}
            for family, mode in CELLS
        ],
        "pairing_contract": {
            "unique_tape_primary_count": 27_200,
            "geometry_mode_family_cell_count": 28,
            "unique_family_mode_tape_cell_count": 14,
            "cell_shard_seed_count": 56,
            "same_seed_across": "both geometries and F/C/U/N1 within each cell/shard",
            "same_tape_across": "both geometries and F/C/U/N1 within each cell/shard",
            "cross_geometry_limit": "matched initial state only; never assume post-transport identity",
            "scorer_rng": "forbidden and source/symbol scans PASS in shadow manifest",
            "stable_control_predicate": (
                "row_index0<3 in every family/mode/subshard plus first 64 root bits modulo 100==0; therefore at least "
                "three outcome-independent controls in every geometry/mode/family/subshard after exact tape reuse; "
                "post-run validation must still establish at least one TES-zero control; no RNG"
            ),
            "runtime_generated_observation_boundary": {
                "C_N1": (
                    "post-run require exact raw EventList hash, exact normalized post-GPS generated binary64 hash, "
                    "field-tolerant serialized IA INIT state, and exact stateful MCSource/MCRun binary64 "
                    "recurrence/native event time"
                ),
                "F_U": (
                    "COMPILE-ONLY CANDIDATE: installed MCRun interposition observes the actual stateful simulated time, "
                    "GPS getters, and the new vertex/primary bitwise closure after calling the installed implementation "
                    "exactly once; it is not P12 evidence until the separately authorized paired sentinel passes"
                ),
                "P12_status": "BLOCKED__PRELOAD_OBSERVER_SENTINEL_NOT_EXECUTED_OR_REVIEWED",
            },
            "preload_observer_sentinel_plan": {
                "status": "PLAN_ONLY__NOT_AUTHORIZED__NOT_EXECUTED",
                "events": 672,
                "matched_pairs": 112,
                "invocations": 224,
                "coverage": "28 cells x 4 shards x first 3 preregistered controls x installed plain/preload",
                "required_equality": (
                    "canonical rich SIM except Date plus raw native DAT/TT equality; exact tape/generated witness, "
                    "resource/observer-overhead, transaction, and real MFileEventsSim gates; C-arm P13 RP "
                    "reconciliation is a separate later production-bundle gate, not an F/U sentinel claim"
                ),
                "authorization": "separate write-once independent sentinel token required before the first event",
            },
            "seed_derivation": "100000000 + uint64_be(SHA256(label|nonce)[0:8]) modulo 900000000; increment nonce on collision",
            "seed_authorities": seed_authorities,
            "seeds": seed_records,
        },
        "planned_execution": {
            "planned_job_count": 448,
            "runnable_job_count": 0,
            "direct_F_U_P12_blocked_job_count": 224,
            "F_U_preload_observer_bound_job_count": 224,
            "C_N1_ready_but_matched_matrix_blocked_job_count": 224,
            "blocked_N0_slot_count": 112,
            "planned_transport_invocation_events": 217_600,
            "arm_order_rotation": (
                "four-row Williams-balanced F/C/U/N1 design phased by geometry+cell+shard; "
                "each arm occupies every slot once and every ordered arm pair is 2:2 per cell"
            ),
            "scheduler": {
                "max_concurrent_transport_processes": 6,
                "threads_per_process": 1,
                "serialize_o8_neutron_eplus_alpha": True,
                "reason": "single-thread multi-process; O8 n/e+/alpha heavy cells are serialized",
            },
            "global_resource_watchdog": {
                "maximum_new_smoke_bytes": 10_000_000_000,
                "maximum_live_bytes_per_job": 9_500_000_000,
                "minimum_live_disk_reserve_bytes": 20 * 1024**3,
                "check_points": "before every launch, once per second while live, after process exit and validation",
                "process_group_required": True,
                "kill_policy": "TERM process group, wait 30 s, then KILL; retain all partial evidence and stop cell",
                "high_RSS_policy": "all transport is serial; O8 n/e+/alpha can never overlap another transport",
            },
            "measurement_contract": {
                "wall": "CLOCK_MONOTONIC around child process",
                "cpu": "sum child process-group user+system CPU; record unavailable descendants explicitly",
                "rss": "poll complete process group at <=1 s cadence and retain raw samples/peak",
                "BeamOn": "parse and bind exact log markers separately from process wall",
                "bytes": "logical/uncompressed and on-disk bytes by record/output type, before validation",
                "serialization_compression": (
                    "record direct phase timers when available; otherwise store null with an explicit reason. The paired "
                    "same-binary F/U contrast can estimate compression-path wall cost but is not a direct phase timer."
                ),
                "validation_time": "separate monotonic interval; never include in BeamOn",
                "required_raw_metric_fields": [
                    "job_id",
                    "arm",
                    "geometry",
                    "family",
                    "mode",
                    "shard_index",
                    "seed",
                    "events",
                    "beam_on_elapsed_s",
                    "process_wall_s",
                    "cpu_user_s",
                    "cpu_system_s",
                    "peak_process_group_rss_bytes",
                    "logical_bytes",
                    "on_disk_bytes",
                    "artifact_bytes_by_type",
                    "record_type_counts",
                    "serialization_elapsed_s",
                    "compression_elapsed_s",
                    "phase_timer_unavailable_reason",
                    "validation_wall_s",
                    "exit_code",
                    "timeout_or_resource_gate",
                ],
            },
            "job_manifest": jobs_binding,
        },
        "artifact_bindings": {
            "tape_provenance_manifest": tape_binding,
            "representation_cassette_manifest": cassette_binding,
            "seven_family_projection": projection_binding,
            "geometry_classification_manifest": geometry_classification_binding,
            "durable_real_consumer_commit": durable_consumer,
            "terminal_execution_status": execution_status,
        },
        "equivalence_gates": {
            "event_float": "abs <= 1e-6 keV or rel <= 1e-9 for serialized floating values",
            "exact_fields": "root/event/order/UID/volume/material/process/ZA/state/track/parent/primary integers and strings",
            "required": [
                "all F/U/C/N1 raw tape <-> actual post-GPS generated binary64 state <-> unique IA INIT state/event "
                "time, using the bound preload observer for F/U and the bound shadow hook for C/N1; serialized IA "
                "uses its separately declared tolerance/format and never substitutes for the binary64 hook",
                "TES pixel energy/centroid/time/multiplicity/order, wide 480--550 keV and W2 510.58--511.42 keV",
                "Mass CsI and O8 BGO/plastic typed deposits; Kapton excluded from veto",
                "candidate plus pre-registered control full ancestry and Compton/FoV/Revan input truth",
                "source time, full-band/coincidence/occupancy templates and response fixtures",
                "BUILDUP TT including zero-RP and RP one-to-one ZA/state/material/logical+physical volume/exact position/root lineage",
                "NUBASE/delayed exact-position/common-response/mission-fold fixture equality",
            ],
            "missing_expected_arm_policy": "never PASS; explicit PARTIAL/WAIT/NO_GO",
            "P12_cross_arm_status": "BLOCKED__PRELOAD_OBSERVER_SENTINEL_NOT_EXECUTED_OR_REVIEWED",
        },
        "performance_gates": {
            "disk": "full-seven-family projected 95% upper bound < 80000000000 bytes",
            "wall": "paired wall-speedup 95% lower bound >= 1.5x",
            "rss": "compact peak process-group RSS <= 1.2x full arm",
            "N0_missing_rule": (
                "forbid pure stepping/transport causal speedup claims; do not forbid the pre-registered matched F/C "
                "end-to-end simulation-output-path wall ratio or its lower-95% gate"
            ),
        },
        "projection_preflight_decision": (
            "PARTIAL__NO_GO_FULL_TARGET until all planned 28 geometry/mode/family cells have >=3 matched executed "
            "subshards. The current object is a plan, not a measured capacity/performance verdict."
        ),
        "tape_manifest": tape_binding,
    }


def build(output_root: Path = FINAL_ROOT, generated_utc: str | None = None) -> dict[str, Any]:
    if output_root.resolve() != FINAL_ROOT.resolve():
        raise ValueError("real preflight output root is fixed; test pure helper functions instead")
    if output_root.exists() or BENCHMARK_CONTRACT.exists():
        raise FileExistsError("write-once preflight or benchmark contract already exists")
    generated_utc = generated_utc or _utc_now()
    if (
        sha256(CONTRACT_PATH) != CONTRACT_SHA256
        or sha256(FEEDBACK01_PATH) != FEEDBACK01_SHA256
        or sha256(FEEDBACK_PATH) != FEEDBACK_SHA256
    ):
        raise ValueError("governing contract/evaluator feedback hash drift")
    if sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise ValueError("corrected-keV source contract hash drift")

    # All hard gates are checked before the first generated artifact is staged.
    production = load_production_binary()
    shadow = load_shadow_build()
    preload_observer = load_preload_observer_build()
    durable_consumer = load_durable_consumer_fixture()
    execution_status = load_execution_status()
    unit_tests = load_unit_test_evidence()
    representation_mapping = validate_mapping()
    geometries = load_geometry_bundles()
    donor_authorities = registered_authorities()
    registered_seeds, seed_authorities = load_registered_seeds()
    seed_records = deterministic_seeds(registered_seeds)
    projection = build_projection()
    if projection["status"] != "PARTIAL__NO_GO_FULL_TARGET__PLANNED_28_CELLS_NOT_EXECUTED":
        raise ValueError("seven-family projection is not explicitly PARTIAL/no-transport")
    cassette = build_cassette_manifest()
    geometry_classification = build_geometry_classification()
    geometry_classification_sha256 = sha256_bytes(canonical_json_bytes(geometry_classification))

    preflight_parent = output_root.parent
    preflight_parent.mkdir(parents=True, exist_ok=True)
    stage = preflight_parent / f".{GENERATED_NAME}.stage.{os.getpid()}"
    if stage.exists():
        raise FileExistsError(stage)
    stage.mkdir(parents=False, exist_ok=False)
    try:
        tape_manifest = build_tape_manifest(stage, output_root, donor_authorities)
        jobs, blocked_n0, card_validations = build_cards_and_jobs(
            stage, output_root, tape_manifest, seed_records, geometries, production, shadow,
            preload_observer, geometry_classification_sha256,
        )
        tape_binding = _write_canonical(stage / "tape_provenance_manifest.json", tape_manifest)
        tape_binding["path"] = rel(output_root / "tape_provenance_manifest.json")
        cassette_binding = _write_canonical(stage / "representation_cassette_manifest.json", cassette)
        cassette_binding["path"] = rel(output_root / "representation_cassette_manifest.json")
        projection_binding = _write_canonical(stage / "seven_family_projection.json", projection)
        projection_binding["path"] = rel(output_root / "seven_family_projection.json")
        geometry_classification_binding = _write_canonical(
            stage / "geometry_classification_manifest.json", geometry_classification
        )
        geometry_classification_binding["path"] = rel(output_root / "geometry_classification_manifest.json")
        job_manifest = {
            "schema_version": 1,
            "status": "WAIT__PARTIAL__448_PLAN_ONLY_CARDS__224_F_U_P12_SENTINEL_BLOCKED__112_N0_SLOTS_BLOCKED",
            "benchmark_class": BENCHMARK_CLASS,
            "transport_authorized": False,
            "transport_events_launched": 0,
            "planned_job_count": len(jobs),
            "runnable_job_count": sum(job["runnable_after_independent_authorization"] for job in jobs),
            "direct_F_U_P12_blocked_job_count": sum(job["arm"] in {"F", "U"} for job in jobs),
            "F_U_preload_observer_bound_job_count": sum(
                job["arm"] in {"F", "U"} and "LD_PRELOAD" in job["environment"] for job in jobs
            ),
            "C_N1_ready_but_matched_matrix_blocked_job_count": sum(job["arm"] in {"C", "N1"} for job in jobs),
            "blocked_N0_slot_count": len(blocked_n0),
            "planned_transport_invocation_events": sum(job["events"] for job in jobs),
            "jobs": jobs,
            "blocked_N0_slots": blocked_n0,
        }
        jobs_binding = _write_canonical(stage / "planned_job_manifest.json", job_manifest)
        jobs_binding["path"] = rel(output_root / "planned_job_manifest.json")
        contract = build_benchmark_contract(
            generated_utc=generated_utc,
            geometries=geometries,
            production=production,
            shadow=shadow,
            preload_observer=preload_observer,
            durable_consumer=durable_consumer,
            execution_status=execution_status,
            unit_tests=unit_tests,
            representation_mapping=representation_mapping,
            seed_authorities=seed_authorities,
            seed_records=seed_records,
            tape_binding=tape_binding,
            jobs_binding=jobs_binding,
            cassette_binding=cassette_binding,
            projection_binding=projection_binding,
            geometry_classification_binding=geometry_classification_binding,
        )
        contract_bytes = canonical_json_bytes(contract)
        contract_sha = sha256_bytes(contract_bytes)
        validation = {
            "schema_version": 1,
            "status": "WAIT__PREFLIGHT_PARTIAL__P12_SENTINEL_AND_N0_BLOCKED__PENDING_INDEPENDENT_REREVIEW",
            "validated_utc": generated_utc,
            "benchmark_class": BENCHMARK_CLASS,
            "merge_eligible": False,
            "transport_authorized": False,
            "transport_events_launched": 0,
            "benchmark_contract_path": rel(BENCHMARK_CONTRACT),
            "benchmark_contract_sha256": contract_sha,
            "checks": {
                "governing_contract_and_feedback_hashes": "PASS",
                "installed_production_binary_identity": "PASS",
                "isolated_shadow_build_unexecuted_and_hash_bound": "PASS",
                "shadow_no_needed_libCosima": "PASS",
                "shadow_scorer_rng_source_and_symbol_scans": "PASS",
                "preload_observer_full_dependency_compile_and_rng_gates": "PASS__BUILD_ONLY_NOT_RUNTIME_VALIDATED",
                "durable_real_MFileEventsSim_and_Revan_zero_transport_fixture": "PASS",
                "preflight_unit_test_command_exit_and_log_hash": "PASS",
                "logical_to_physical_mapping_and_scorer_headers": "PASS",
                "two_canonical_geometry_bundles_recomputed": "PASS",
                "rp_geometry_volume_logical_material_classification_from_actual_bundles": "PASS",
                "corrected_keV_source_contract": "PASS",
                "manifest_only_donor_and_cassette_discovery": "PASS",
                "batch0003_exact_paired_prefix_1_through_76": "PASS",
                "batch0003_unpaired_mass_ordinal77_excluded": "PASS",
                "twenty_eight_geometry_mode_family_cells_four_matched_subshards_planned": "PASS__PLAN_ONLY_NOT_RUN",
                "fourteen_unique_family_mode_tapes_fifty_six_atomic_shards": "PASS",
                "eventlist_only_source_cards": "PASS",
                "deterministic_seed_registry_collision_check": "PASS",
                "planned_F_C_U_N1_job_count_448": "PASS__PLAN_ONLY",
                "runnable_job_count": "BLOCKED__ZERO_UNTIL_P12_CLOSED_AND_NEW_ARTIFACT_AUTHORIZED",
                "blocked_N0_slot_count_112": "PASS",
                "heavy_O8_n_eplus_alpha_prompt_or_buildup_present": "PASS__PLAN_ONLY_NOT_RUN",
                "representation_cassette_TES_W2_veto_pair_RP_zeroRP": "PASS",
                "full_28_cell_seven_family_retain_all_projection": "PASS__ACCOUNTING_ONLY_NO_OPTIMIZATION_VERDICT",
                "F_U_high_precision_post_GPS_generated_observer": (
                    "CANDIDATE__COMPILE_ONLY__BLOCKED_UNTIL_PAIRED_SENTINEL_AND_INDEPENDENT_REREVIEW"
                ),
                "full_target_capacity_and_performance_verdict": "PARTIAL__NO_GO__ALL_CONFIDENCE_BOUNDS_NULL",
                "transport_launch": "BLOCKED",
            },
            "counts": {
                "unique_primary_states": 27_200,
                "geometry_mode_family_cells": 28,
                "unique_family_mode_tape_cells": 14,
                "unique_tape_shards": 56,
                "geometry_cell_shards": 112,
                "geometries": 2,
                "planned_arms": 4,
                "planned_jobs": len(jobs),
                "runnable_arms": 0,
                "runnable_jobs": sum(job["runnable_after_independent_authorization"] for job in jobs),
                "direct_F_U_P12_blocked_jobs": sum(job["arm"] in {"F", "U"} for job in jobs),
                "F_U_preload_observer_bound_jobs": sum(
                    job["arm"] in {"F", "U"} and "LD_PRELOAD" in job["environment"] for job in jobs
                ),
                "C_N1_ready_but_matched_matrix_blocked_jobs": sum(job["arm"] in {"C", "N1"} for job in jobs),
                "blocked_N0_slots": len(blocked_n0),
                "source_cards": len(card_validations),
                "cassette_event_cases": cassette["event_case_count"],
                "planned_transport_invocation_events": sum(job["events"] for job in jobs),
                "actual_transport_events": 0,
            },
            "artifact_bindings": {
                "tape_provenance_manifest": tape_binding,
                "planned_job_manifest": jobs_binding,
                "representation_cassette_manifest": cassette_binding,
                "seven_family_projection": projection_binding,
                "geometry_classification_manifest": geometry_classification_binding,
                "shadow_build_manifest": {
                    "path": shadow["manifest_path"],
                    "sha256": shadow["manifest_sha256"],
                    "size_bytes": shadow["manifest_size_bytes"],
                },
                "preload_observer_build_manifest": preload_observer,
                "durable_real_consumer_commit": durable_consumer,
                "terminal_execution_status": execution_status,
                "preflight_unit_tests": unit_tests,
                "m05cc_representation_mapping": representation_mapping,
            },
            "card_validations": card_validations,
            "decision": (
                "Leave for a fresh independent review. The zero-transport preflight contract passes and all 28 cells "
                "are planned with four matched subshards, but none has run. N0 remains intentionally unavailable, so "
                "no pure stepping/transport causal speedup may be claimed; matched F/C end-to-end output-path wall "
                "ratios remain a valid empirical gate after execution."
            ),
        }
        _write_canonical(stage / "preflight_validation.json", validation)
        # Final internal verification occurs while all data are still staged.
        for path in (
            stage / "tape_provenance_manifest.json",
            stage / "planned_job_manifest.json",
            stage / "representation_cassette_manifest.json",
            stage / "seven_family_projection.json",
            stage / "geometry_classification_manifest.json",
            stage / "preflight_validation.json",
        ):
            assert_canonical_json(path)
        publish_wait_contract_then_preflight(stage, output_root, BENCHMARK_CONTRACT, contract_bytes)
    except BaseException:
        if stage.exists():
            # Preserve every failed staging artifact for independent audit; never delete project data.
            quarantine_directory_no_replace(stage)
        raise
    return {
        "status": validation["status"],
        "benchmark_contract_path": rel(BENCHMARK_CONTRACT),
        "benchmark_contract_sha256": sha256(BENCHMARK_CONTRACT),
        "preflight_root": rel(output_root),
        "preflight_validation_path": rel(output_root / "preflight_validation.json"),
        "transport_events_launched": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-utc", help="Optional frozen UTC timestamp, e.g. 2026-08-12T06:00:00Z")
    args = parser.parse_args()
    result = build(generated_utc=args.generated_utc)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
