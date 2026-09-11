#!/usr/bin/env python3
"""Finalize the effective SF3-only Plan-1 chain from small authorities.

This adapter never opens, stats, or hashes a SIM payload.  Canonical receipt
metadata is the sole transport-artifact authority.  ``--check-prerequisites``
is strictly read-only; ``--build`` publishes one write-once stage-07 directory
only after every effective receipt and stage 00--06 contract passes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
DEFAULT_PACKAGE_ROOT = HERE.parent.parent
DEFAULT_CONFIG = DEFAULT_PACKAGE_ROOT / "analysis_inputs.json"
PROFILE_ID = "SF3_PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN"
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
EXPECTED_INSTANT = 1_280_693
EXPECTED_BUILDUP = 1_015_492
EXPECTED_BACKGROUND_JOBS = 21
EXPECTED_DELAYED_EVENTS = 83_334
EXPECTED_SIGNAL_EVENTS = 37_194
EXPECTED_INPUT_AEFF = 20.08476
START_GATE_BYTES = 30_000_000_000
DYNAMIC_RESERVE_BYTES = 8 * 1024**3
SE3_B20 = 144_203.8420859011
SE3_B20_PROXY = 1_249_284.0948305726
SE3_PROMPT_CPS = 0.03384292813088877
SE3_DELAYED_CPS = 0.054479752227267225
UNAVAILABLE = "UNAVAILABLE_BY_USER_SCOPE"
MAX_SMALL_BYTES = 64 * 1024**2
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_STAGE_STATUS = {
    "stage00": "PASS",
    "stage01": "PASS__SF3_PLAN1_PROMPT_COMPLETE",
    "stage02": "PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY",
    "stage03": "PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
    "stage04": "PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE",
    "stage05": "PASS__SF3_PLAN1_DAY15_BACKGROUND_COMPARISON_AND_SF3_ONLY_FULL_ENVELOPE_SIGNAL",
    "stage06": "PASS__SF3_FULL_ENVELOPE_81NODE_ABSOLUTE_F3__SE3_RATIO_UNAVAILABLE_BY_USER_SCOPE",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def reject_nonfinite(token: str) -> None:
    raise ValueError(f"non-finite JSON token: {token}")


def sha256_small(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_SMALL_BYTES:
        raise RuntimeError(f"small-authority limit exceeded ({size} bytes): {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def small_record(path: Path) -> dict[str, Any]:
    return {
        "path": norm(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_small(path),
    }


def load_small_json(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid small JSON size ({size}): {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, parse_constant=reject_nonfinite)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_small_csv(path: Path) -> list[dict[str, str]]:
    size = path.stat().st_size
    if size <= 0 or size > MAX_SMALL_BYTES:
        raise RuntimeError(f"invalid small CSV size ({size}): {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(a: Any, b: Any, *, rel: float = 2e-10, absolute: float = 1e-12) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=absolute)
    except (TypeError, ValueError):
        return False


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def json(self, label: str, path: Path, *, bind: bool = True) -> dict[str, Any] | None:
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_json(path)
            if bind:
                self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def csv(self, label: str, path: Path, *, bind: bool = True) -> list[dict[str, str]] | None:
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            value = load_small_csv(path)
            if bind:
                self.authorities[label] = small_record(path)
            return value
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None


def cast_plan(rows: list[dict[str, str]], check: Checker) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        try:
            item: dict[str, Any] = dict(row)
            for key in ("ordinal", "shard", "events", "se3_histories", "target_histories", "seed"):
                item[key] = int(row[key])
            for key in ("paired_seed_exception", "production_canary"):
                item[key] = row[key].strip().lower() == "true"
            output.append(item)
        except Exception as exc:
            check.errors.append(f"job plan row {index} invalid: {exc}")
    return output


def validate_plan(plan: list[dict[str, Any]], check: Checker) -> None:
    check.expect(len(plan) == 31, f"job plan rows {len(plan)} != 31")
    ids = [str(row.get("job_id")) for row in plan]
    check.expect(len(ids) == len(set(ids)), "job plan contains duplicate job IDs")
    background = [row for row in plan if row.get("stage") == "background"]
    instant = [row for row in background if row.get("mode") == "instant"]
    buildup = [row for row in background if row.get("mode") == "buildup"]
    check.expect(len(background) == EXPECTED_BACKGROUND_JOBS, "background job count is not 21")
    check.expect(sum(row["events"] for row in instant) == EXPECTED_INSTANT, "instant history total differs")
    check.expect(sum(row["events"] for row in buildup) == EXPECTED_BUILDUP, "buildup history total differs")
    for mode in ("instant", "buildup"):
        for family in FAMILIES:
            cell = [row for row in background if row.get("mode") == mode and row.get("family") == family]
            check.expect(bool(cell), f"missing background cell {mode}/{family}")
            if not cell:
                continue
            targets = {int(row["target_histories"]) for row in cell}
            check.expect(len(targets) == 1, f"target drift in {mode}/{family}")
            target = next(iter(targets))
            check.expect(target == math.ceil(int(cell[0]["se3_histories"]) / 3), f"ceil(1/3) mismatch {mode}/{family}")
            check.expect(sum(int(row["events"]) for row in cell) == target, f"shard closure mismatch {mode}/{family}")
            if target <= 100_000:
                check.expect(len(cell) == 1, f"target <=100k was split: {mode}/{family}")
            else:
                check.expect(all(int(row["events"]) >= 100_000 for row in cell), f"sub-100k shard: {mode}/{family}")
    delayed = [row for row in plan if row.get("stage") == "delayed"]
    check.expect(len(delayed) == 8, "delayed plan does not contain eight registered cells")
    check.expect({row.get("family") for row in delayed} == set(FAMILIES), "delayed family closure differs")
    check.expect(all(row.get("geometry") == "SF3" and row.get("events") == EXPECTED_DELAYED_EVENTS for row in delayed), "delayed plan geometry/event contract differs")
    signal = [row for row in plan if row.get("stage") == "signal"]
    check.expect(len(signal) == 2, "paired signal plan does not contain two registered rows")
    check.expect({row.get("geometry") for row in signal} == {"SF3", "SE3"}, "paired signal geometry registration differs")
    check.expect(all(row.get("events") == EXPECTED_SIGNAL_EVENTS for row in signal), "signal trials differ from 37194")
    check.expect(len({row.get("seed") for row in signal}) == 1, "paired signal seed differs")
    canaries = [row for row in background if row.get("production_canary")]
    check.expect(len(canaries) == 1 and canaries[0].get("job_id") == "sf3_instant_gamma_shard0001", "gamma production canary registration differs")


def validate_seed_registry(rows: list[dict[str, str]], plan: list[dict[str, Any]], check: Checker) -> None:
    by_id = {row["job_id"]: row for row in rows}
    check.expect(set(by_id) == {row["job_id"] for row in plan}, "seed registry/job plan key closure differs")
    for job in plan:
        row = by_id.get(job["job_id"])
        if row is None:
            continue
        check.expect(int(row["seed"]) == int(job["seed"]), f"seed registry mismatch: {job['job_id']}")
        check.expect(row.get("collision_with_prior", "").lower() == "false", f"registered seed collision: {job['job_id']}")


def stage_paths(config: dict[str, Any]) -> dict[str, tuple[Path, Path | None]]:
    outputs = config["outputs"]
    return {
        "stage00": (Path(outputs["stage_00"]) / "input_audit.json", None),
        "stage01": (Path(outputs["stage_01"]) / "summary.json", Path(outputs["stage_01"]) / "manifest.json"),
        "stage02": (Path(outputs["stage_02"]) / "day15_summary.json", Path(outputs["stage_02"]) / "manifest.json"),
        "stage03": (Path(outputs["stage_03"]) / "summary.json", Path(outputs["stage_03"]) / "manifest.json"),
        "stage04": (Path(outputs["stage_04"]) / "summary.json", Path(outputs["stage_04"]) / "manifest.json"),
        "stage05": (Path(outputs["stage_05"]) / "summary.json", Path(outputs["stage_05"]) / "manifest.json"),
        "stage06": (Path(outputs["stage_06"]) / "summary.json", None),
    }


def validate_receipt(job: dict[str, Any], payload: dict[str, Any], path: Path, check: Checker) -> dict[str, Any] | None:
    job_id = str(job["job_id"])
    check.expect(payload.get("status") == "PASS" and payload.get("errors") in ([], None), f"non-PASS canonical receipt: {job_id}")
    for key in ("job_id", "stage", "geometry", "mode", "family", "events", "seed", "source_path", "setup_path"):
        check.expect(payload.get(key) == job.get(key), f"receipt {job_id} {key} differs from plan")
    log = payload.get("log") or {}
    header = payload.get("sim_header") or {}
    check.expect(log.get("generated_events") == job["events"], f"generated-event mismatch: {job_id}")
    check.expect(log.get("graphics_terminal_marker") is True, f"terminal marker missing: {job_id}")
    check.expect(norm(str(header.get("geometry", ""))) == norm(job["setup_path"]), f"header geometry mismatch: {job_id}")
    check.expect(header.get("seed") == job["seed"], f"header seed mismatch: {job_id}")
    check.expect(payload.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", f"SIM digest policy mismatch: {job_id}")
    check.expect(SHA256_RE.fullmatch(str(payload.get("source_sha256", ""))) is not None, f"source digest metadata invalid: {job_id}")
    for key in ("source_path", "setup_path", "sim_path", "log_path", "attempt_dir"):
        check.expect(Path(str(payload.get(key, ""))).is_absolute(), f"receipt path is not absolute ({key}): {job_id}")
    if job["stage"] == "background":
        isotope = payload.get("isotope_dat") or {}
        check.expect(isinstance(isotope.get("TT_s"), (int, float)) and isotope["TT_s"] > 0, f"background TT is not positive: {job_id}")
    sim_bytes = int(payload.get("sim_bytes", -1))
    log_bytes = int(payload.get("log_bytes", -1))
    dat_bytes = int(payload.get("isotope_dat_bytes", 0) or 0)
    artifact_bytes = int(payload.get("artifact_bytes", -1))
    check.expect(min(sim_bytes, log_bytes, dat_bytes, artifact_bytes) >= 0, f"negative receipt bytes: {job_id}")
    check.expect(artifact_bytes == sim_bytes + log_bytes + dat_bytes, f"artifact-byte closure mismatch: {job_id}")
    return {
        "job_id": job_id,
        "receipt_path": norm(path),
        "receipt_sha256": sha256_small(path),
        "stage": job["stage"],
        "geometry": job["geometry"],
        "mode": job["mode"],
        "family": job["family"],
        "events": int(job["events"]),
        "seed": int(job["seed"]),
        "attempt": int(payload.get("attempt", 0)),
        "source_path": norm(payload["source_path"]),
        "source_sha256": payload["source_sha256"],
        "setup_path": norm(payload["setup_path"]),
        "header_geometry": norm(header.get("geometry", "")),
        "header_seed": header.get("seed"),
        "sim_path": norm(payload["sim_path"]),
        "sim_bytes": sim_bytes,
        "log_path": norm(payload["log_path"]),
        "log_bytes": log_bytes,
        "isotope_dat_bytes": dat_bytes,
        "artifact_bytes": artifact_bytes,
        "peak_process_group_rss_bytes": int(payload.get("peak_process_group_rss_bytes", 0)),
        "wall_s": float(payload.get("wall_s", 0.0)),
        "beam_on_cpu_s": float(log.get("beam_on_cpu_s", 0.0) or 0.0),
        "TT_s": (payload.get("isotope_dat") or {}).get("TT_s"),
        "RP_record_count": (payload.get("isotope_dat") or {}).get("RP_record_count"),
    }


def get_nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    check = Checker()
    config = check.json("analysis_inputs", config_path.resolve())
    if config is None:
        return {
            "schema_version": 1, "profile_id": PROFILE_ID,
            "status": "NOT_READY__SF3_FINAL_CHAIN_INPUTS_INCOMPLETE", "ready": False,
            "checked_at": utc_now(), "missing": sorted(set(check.missing)),
            "errors": check.errors, "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__RECEIPT_METADATA_ONLY",
        }
    package_root = Path(config.get("package_root", config_path.parent)).resolve()
    run_root = Path(config.get("run_root", ""))
    output_root = package_root / "outputs/07_final_audit"
    check.expect(config.get("profile_id") == PROFILE_ID, "profile_id differs")
    check.expect(package_root == config_path.resolve().parent, "config package_root differs from config parent")
    check.expect(run_root.is_absolute(), "run_root is not absolute")
    exclusions = get_nested(config, "transport", "execution_exclusions") or {}
    check.expect(isinstance(exclusions, dict), "transport.execution_exclusions is not an object")
    check.expect(set(exclusions) == {"signal_full_envelope_se3"}, "configured execution gate is not exact SF3-only scope")
    check.expect("NO_SE3_RERUN" in str(exclusions.get("signal_full_envelope_se3", "")), "SE3 exclusion reason differs")
    check.expect(int(get_nested(config, "transport", "start_free_gate_bytes") or -1) == START_GATE_BYTES, "30 GB start gate differs")
    check.expect(int(get_nested(config, "transport", "dynamic_reserve_bytes") or -1) == DYNAMIC_RESERVE_BYTES, "8 GiB dynamic reserve differs")

    plan_path = Path(get_nested(config, "transport", "job_plan") or "")
    seed_path = Path(get_nested(config, "transport", "seed_registry") or "")
    plan_rows = check.csv("job_plan", plan_path)
    seed_rows = check.csv("seed_registry", seed_path)
    plan = cast_plan(plan_rows or [], check)
    if plan_rows is not None:
        validate_plan(plan, check)
    if seed_rows is not None and plan_rows is not None:
        validate_seed_registry(seed_rows, plan, check)
    plan_by_id = {row["job_id"]: row for row in plan}

    stage_payloads: dict[str, dict[str, Any] | None] = {}
    stage_bindings: dict[str, Any] = {}
    try:
        configured_stages = stage_paths(config)
    except Exception as exc:
        check.errors.append(f"stage output config invalid: {exc}")
        configured_stages = {}
    for stage, paths in configured_stages.items():
        summary_path, manifest_path = paths
        summary = check.json(f"{stage}_summary", summary_path)
        stage_payloads[stage] = summary
        binding: dict[str, Any] = {
            "expected_status": EXPECTED_STAGE_STATUS[stage],
            "summary_path": norm(summary_path),
            "observed_status": summary.get("status") if summary else None,
        }
        if summary is not None:
            check.expect(summary.get("status") == EXPECTED_STAGE_STATUS[stage], f"{stage} status differs")
        if manifest_path is not None:
            manifest = check.json(f"{stage}_manifest", manifest_path)
            binding["manifest_path"] = norm(manifest_path)
            binding["manifest_status"] = manifest.get("status") if manifest else None
            if manifest is not None:
                check.expect(manifest.get("status") == EXPECTED_STAGE_STATUS[stage], f"{stage} manifest status differs")
        stage_bindings[stage] = binding

    audits = {
        "source_validation": package_root / "audit/sf3_plan1_source_validation.json",
        "background_receipt_validation": package_root / "audit/sf3_plan1_background_receipt_validation.json",
        "all_receipt_validation": package_root / "audit/sf3_plan1_all_receipt_validation.json",
        "transport_receipts": package_root / "audit/sf3_plan1_transport_receipts.json",
        "activation_validation": package_root / "audit/sf3_activation_validation.json",
        "signal_static": package_root / "audit/full_envelope_signal_static_audit.json",
        "signal_navigation": package_root / "audit/full_envelope_signal_navigation_audit.json",
        "signal_transport_gate": package_root / "audit/full_envelope_signal_transport_gate.json",
        "user_scope": package_root / "audit/user_scope_override_no_se3_rerun_20260815.json",
        "frozen_se3_signal_scope": package_root / "audit/frozen_se3_signal_scope_audit.json",
        "interrupt_recovery": package_root / "audit/controller_interruption_recovery_20260815.json",
        "disk_recovery": package_root / "audit/dynamic_disk_recovery_20260815.json",
    }
    audit_payloads = {name: check.json(name, path) for name, path in audits.items()}
    source = audit_payloads["source_validation"]
    if source:
        check.expect(source.get("status") == "PASS", "source validation is not PASS")
        check.expect(get_nested(source, "sources", "count") == 21, "source count differs")
        check.expect(get_nested(source, "sources", "all_sf3_geometry") is True, "background sources are not all SF3")
        check.expect(get_nested(source, "sources", "legacy_reference_count") == 0, "legacy spectrum reference present")
    bg_validation = audit_payloads["background_receipt_validation"]
    if bg_validation:
        check.expect(bg_validation.get("status") == "PASS", "background receipt validation is not PASS")
        check.expect(bg_validation.get("validated_jobs_in_scope") == 21, "background validated receipt count differs")
        check.expect(bg_validation.get("validated_events_in_scope") == EXPECTED_INSTANT + EXPECTED_BUILDUP, "background validated event total differs")
    all_validation = audit_payloads["all_receipt_validation"]
    if all_validation:
        check.expect(all_validation.get("status") == "PASS" and all_validation.get("scope") == "all", "all-receipt audit is not PASS/all")
        check.expect(all_validation.get("dynamic_reserve_pass") is True, "all-receipt dynamic reserve gate failed")
    user_scope = audit_payloads["user_scope"]
    if user_scope:
        check.expect(str(user_scope.get("status", "")).startswith("PASS__SF3_ONLY"), "user SF3-only scope audit differs")
        check.expect(set((user_scope.get("excluded_transport_jobs") or {})) == {"signal_full_envelope_se3"}, "user scope exclusion differs")
        check.expect(user_scope.get("se3_background_transport") == "NOT_PLANNED_AND_NOT_RUN", "user scope permits SE3 background transport")
    frozen_scope = audit_payloads["frozen_se3_signal_scope"]
    if frozen_scope:
        check.expect(frozen_scope.get("full_envelope_geometry_ratio_eligible") is False, "frozen SE3 signal was incorrectly made ratio eligible")
        check.expect(frozen_scope.get("fresh_se3_full_envelope_receipt_found") is False, "unexpected fresh SE3 signal authority")
    static = audit_payloads["signal_static"]
    if static:
        check.expect(str(static.get("status", "")).startswith("PASS__"), "signal static audit is not PASS")
        check.expect(get_nested(static, "frozen_bank", "data_rows") == EXPECTED_SIGNAL_EVENTS, "signal frozen-bank rows differ")
        check.expect(get_nested(static, "pair", "no_resampling_or_bootstrap") is True, "signal bank was resampled")
    navigation = audit_payloads["signal_navigation"]
    if navigation:
        check.expect(get_nested(navigation, "driver_validation", "status") == "PASS", "native signal navigation audit is not PASS")
        check.expect(get_nested(navigation, "geometries", "SF3", "status") == "PASS", "SF3 navigation geometry status is not PASS")
        check.expect(get_nested(navigation, "geometries", "SF3", "parsed_rows") == EXPECTED_SIGNAL_EVENTS, "SF3 navigation row count differs")
    transport_gate = audit_payloads["signal_transport_gate"]
    if transport_gate:
        check.expect(transport_gate.get("status") == "PASS", "signal transport gate is not PASS")
        check.expect("signal_full_envelope_sf3" in (transport_gate.get("permitted_signal_jobs") or []), "signal gate omits SF3")
        check.expect(transport_gate.get("paired_bank_rows") == EXPECTED_SIGNAL_EVENTS, "signal gate row count differs")
        check.expect(transport_gate.get("transport_launched") is False, "navigation gate claims transport launch")
    interrupt = audit_payloads["interrupt_recovery"]
    recovered_jobs: set[str] = set()
    if interrupt:
        check.expect(str(interrupt.get("status", "")).startswith("PASS__"), "interrupt recovery audit is not PASS")
        check.expect(interrupt.get("statistics_policy") == "FAILED_PARTIALS_EXCLUDED", "interrupted partials are not excluded")
        recovered_jobs = {str(item).split("/", 1)[0] for item in interrupt.get("failed_attempts", [])}
        check.expect(interrupt.get("jobs") == len(recovered_jobs), "interrupt recovery job count differs")
    disk_recovery = audit_payloads["disk_recovery"]
    if disk_recovery:
        check.expect(str(disk_recovery.get("status", "")).startswith("PASS__"), "disk recovery audit is not PASS")
        check.expect(disk_recovery.get("project_authority_files_removed") == 0, "disk recovery removed project authority")

    stage00 = stage_payloads.get("stage00")
    if stage00:
        check.expect(get_nested(stage00, "plan", "background_jobs") == 21, "stage00 background jobs differ")
        check.expect(get_nested(stage00, "plan", "instant_histories") == EXPECTED_INSTANT, "stage00 instant total differs")
        check.expect(get_nested(stage00, "plan", "buildup_histories") == EXPECTED_BUILDUP, "stage00 buildup total differs")
        check.expect(get_nested(stage00, "r0", "start_gate_pass") is True, "stage00 30 GB gate did not pass")
        check.expect(int(get_nested(stage00, "r0", "free_bytes") or 0) >= START_GATE_BYTES, "stage00 free bytes below 30 GB")
    stage01 = stage_payloads.get("stage01")
    if stage01:
        check.expect(stage01.get("selected_jobs") == 11 and stage01.get("selected_histories") == EXPECTED_INSTANT, "stage01 prompt closure differs")
    activation = audit_payloads["activation_validation"]
    run_delayed: set[str] | None = None
    zero_delayed: set[str] = set()
    if activation:
        check.expect(activation.get("status") == "PASS", "activation launch gate is not PASS")
        cards = activation.get("source_cards") or []
        check.expect(len(cards) == 8, "activation gate does not register eight delayed cells")
        run_delayed = set()
        families_seen: set[str] = set()
        for card in cards:
            family = str(card.get("family"))
            job_id = str(card.get("job_id"))
            families_seen.add(family)
            job = plan_by_id.get(job_id)
            check.expect(job is not None and job.get("stage") == "delayed" and job.get("family") == family, f"activation card/job binding differs: {job_id}")
            if job:
                check.expect(card.get("seed") == job.get("seed") and card.get("events") == EXPECTED_DELAYED_EVENTS, f"activation seed/events differ: {job_id}")
            disposition = card.get("execution_disposition")
            if disposition == "RUN_83334":
                run_delayed.add(job_id)
                check.expect(float(card.get("transported_ground_activity_Bq", 0)) > 0 and card.get("actual_transport_events") == EXPECTED_DELAYED_EVENTS, f"RUN delayed cell differs: {job_id}")
            elif disposition == "SKIP_ZERO_A15":
                zero_delayed.add(job_id)
                check.expect(float(card.get("transported_ground_activity_Bq", -1)) == 0 and card.get("actual_transport_events") == 0, f"zero-A15 closure differs: {job_id}")
            else:
                check.errors.append(f"unknown delayed disposition: {job_id}/{disposition}")
        check.expect(families_seen == set(FAMILIES), "activation delayed-family closure differs")
        check.expect(len(run_delayed) + len(zero_delayed) == 8, "effective delayed count closure differs")
        check.expect(activation.get("transport_delayed_jobs") == len(run_delayed), "activation RUN count differs")
        check.expect(activation.get("skipped_zero_A15_jobs") == len(zero_delayed), "activation zero count differs")
        check.expect(activation.get("delayed_events_total") == EXPECTED_DELAYED_EVENTS * len(run_delayed), "activation trigger total differs")
    stage02 = stage_payloads.get("stage02")
    if stage02:
        check.expect(stage02.get("selected_buildup_jobs") == 10 and stage02.get("selected_buildup_histories") == EXPECTED_BUILDUP, "stage02 buildup closure differs")
        check.expect(stage02.get("registered_delayed_source_cells") == 8, "stage02 delayed registration differs")
        if run_delayed is not None:
            check.expect(stage02.get("delayed_transport_jobs_planned") == len(run_delayed), "stage02 RUN delayed count differs")
            check.expect(stage02.get("delayed_zero_source_jobs_skipped") == len(zero_delayed), "stage02 skipped delayed count differs")
    stage03 = stage_payloads.get("stage03")
    if stage03 and run_delayed is not None:
        check.expect(stage03.get("registered_source_cells") == 8, "stage03 registered delayed count differs")
        check.expect(stage03.get("transport_jobs") == len(run_delayed), "stage03 RUN delayed count differs")
        check.expect(stage03.get("skipped_zero_A15_jobs") == len(zero_delayed), "stage03 zero delayed count differs")
        check.expect(stage03.get("transport_triggers_per_family") == EXPECTED_DELAYED_EVENTS, "stage03 triggers/cell differ")
        check.expect(stage03.get("transport_triggers") == EXPECTED_DELAYED_EVENTS * len(run_delayed), "stage03 trigger total differs")

    expected_ids: set[str] = {row["job_id"] for row in plan if row.get("stage") == "background"}
    expected_ids.add("signal_full_envelope_sf3")
    if run_delayed is not None:
        expected_ids.update(run_delayed)
    excluded_ids = {"signal_full_envelope_se3"} | zero_delayed
    receipt_rows: list[dict[str, Any]] = []
    for job_id in sorted(expected_ids, key=lambda key: int(plan_by_id[key]["ordinal"])):
        receipt_path = run_root / "receipts" / f"{job_id}.json"
        receipt = check.json(f"receipt_{job_id}", receipt_path, bind=False)
        if receipt is not None:
            row = validate_receipt(plan_by_id[job_id], receipt, receipt_path, check)
            if row:
                receipt_rows.append(row)
    for job_id in excluded_ids:
        path = run_root / "receipts" / f"{job_id}.json"
        check.expect(not path.exists(), f"excluded transport has canonical receipt: {job_id}")
    receipt_ids = {row["job_id"] for row in receipt_rows}
    if run_delayed is not None:
        check.expect(all((row["attempt"] >= 2) for row in receipt_rows if row["job_id"] in recovered_jobs), "recovered interrupted job lacks retry receipt")
    check.expect(len({row["sim_path"] for row in receipt_rows}) == len(receipt_rows), "effective receipts reuse a SIM path")

    aggregate = audit_payloads["transport_receipts"]
    if aggregate:
        selected_ids = {row.get("job_id") for row in aggregate.get("selected_receipts", [])}
        check.expect(selected_ids == receipt_ids, "aggregate/canonical receipt set differs")
        check.expect(aggregate.get("background_planned_jobs") == 21, "aggregate background plan count differs")
        projection = aggregate.get("projection") or {}
        check.expect(projection.get("pass") is True, "aggregate dynamic reserve projection failed")
        if run_delayed is not None and expected_ids.issubset(receipt_ids):
            check.expect(aggregate.get("effective_planned_jobs") == len(expected_ids), "aggregate effective job count differs")
            check.expect(aggregate.get("validated_jobs") == len(expected_ids), "aggregate validated job count differs")
            check.expect(str(aggregate.get("status", "")).startswith("PASS__"), "aggregate is not final PASS")

    stage04 = stage_payloads.get("stage04")
    stage05 = stage_payloads.get("stage05")
    stage06 = stage_payloads.get("stage06")
    physics: dict[str, Any] = {}
    if stage04:
        background = get_nested(stage04, "final_measured_w2", "SF3_background") or {}
        signal = get_nested(stage04, "final_measured_w2", "SF3_signal") or {}
        if run_delayed is not None:
            run_families = {str(plan_by_id[job_id]["family"]) for job_id in run_delayed}
            zero_families = {str(plan_by_id[job_id]["family"]) for job_id in zero_delayed}
            dispositions = stage04.get("delayed_dispositions") or {}
            check.expect(set(dispositions.get("RUN_83334") or []) == run_families, "stage04 delayed RUN disposition closure differs")
            check.expect(set(dispositions.get("SKIP_ZERO_A15") or []) == zero_families, "stage04 delayed zero-A15 disposition closure differs")
            check.expect(dispositions.get("zero_A15_central_rate_policy") == "EXACT_ZERO__NO_CATALOG_OR_SIM_OPEN", "stage04 zero-A15 central policy differs")
            check.expect(len(dispositions.get("finite_upper_provenance") or []) == len(zero_families), "stage04 zero-A15 finite-upper provenance count differs")
            check.expect(get_nested(stage04, "catalogs", "delayed_registered_cells") == 8, "stage04 delayed registered-cell closure differs")
            check.expect(get_nested(stage04, "catalogs", "delayed_transport_opened") == len(run_families), "stage04 delayed transport-open count differs")
            check.expect(get_nested(stage04, "catalogs", "delayed_structural_zero_rate") == len(zero_families), "stage04 delayed structural-zero count differs")
        check.expect(get_nested(stage04, "signal", "eventlist_rows") == EXPECTED_SIGNAL_EVENTS, "stage04 signal trials differ")
        check.expect(get_nested(stage04, "signal", "semantic_sim_scans") == 1 and get_nested(stage04, "signal", "sim_hashes_recomputed") == 0, "stage04 signal one-pass/no-hash contract differs")
        check.expect(signal.get("trials") == EXPECTED_SIGNAL_EVENTS, "stage04 W2 signal trials differ")
        check.expect(close(signal.get("input_optics_aeff_cm2"), EXPECTED_INPUT_AEFF), "stage04 input Aeff differs")
        physics["day15_common_response"] = {
            "prompt_w2_cps": background.get("prompt_rate_cps"),
            "delayed_w2_cps": background.get("delayed_rate_cps"),
            "background_w2_cps": background.get("total_background_rate_cps"),
        }
        physics["full_envelope_signal"] = {
            "trials": signal.get("trials"), "selected_events": signal.get("selected_events"),
            "Aeff_cm2": signal.get("selected_effective_area_cm2"),
            "Aeff_lower95_cm2": signal.get("selected_effective_area_lower95_cm2"),
            "Aeff_upper95_cm2": signal.get("selected_effective_area_upper95_cm2"),
        }
        check.expect(get_nested(stage04, "final_measured_w2", "SE3_signal") == "UNAVAILABLE_BY_USER_SCOPE__NO_FRESH_SE3_TRANSPORT", "stage04 SE3 signal scope differs")
    if stage05:
        w2 = stage05.get("w2") or {}
        check.expect(get_nested(stage05, "signal_authority", "SE3") == UNAVAILABLE, "stage05 SE3 signal authority differs")
        check.expect(get_nested(stage05, "signal_authority", "historical_post_be_used_as_denominator") is False, "stage05 used old post-Be denominator")
        if run_delayed is not None:
            zero_families = {str(plan_by_id[job_id]["family"]) for job_id in zero_delayed}
            zero_policy = stage05.get("zero_count_policy") or {}
            check.expect(set(zero_policy.get("SF3_zero_A15_families") or []) == zero_families, "stage05 zero-A15 family closure differs")
            check.expect(set((zero_policy.get("SF3_zero_A15_provenance") or {}).keys()) == zero_families, "stage05 zero-A15 provenance closure differs")
        physics["day15_frozen_se3_comparison"] = {
            "SE3_prompt_w2_cps": w2.get("SE3_prompt_rate_cps"),
            "SE3_delayed_w2_cps": w2.get("SE3_delayed_rate_cps"),
            "SE3_background_w2_cps": w2.get("SE3_background_rate_cps"),
            "SF3_over_SE3_prompt": w2.get("SF3_over_SE3_prompt_rate_central"),
            "SF3_over_SE3_delayed": w2.get("SF3_over_SE3_delayed_rate_central"),
            "SF3_over_SE3_background": w2.get("SF3_over_SE3_background_rate_central"),
        }
    if stage06:
        sf3 = get_nested(stage06, "geometries", "SF3") or {}
        se3 = get_nested(stage06, "geometries", "SE3") or {}
        ratios = stage06.get("fair_full_envelope_ratios") or {}
        ratio_contract = stage06.get("ratio_contract") or {}
        check.expect(close(se3.get("background_counts_20d"), SE3_B20), "frozen SE3 B20 anchor differs")
        check.expect(close(se3.get("background_upper95_proxy_counts_20d"), SE3_B20_PROXY), "frozen SE3 B20 proxy anchor differs")
        check.expect(close(get_nested(se3, "constant_environment_day15_reference", "prompt_final_cps"), SE3_PROMPT_CPS), "frozen SE3 prompt anchor differs")
        check.expect(close(get_nested(se3, "constant_environment_day15_reference", "delayed_final_cps"), SE3_DELAYED_CPS), "frozen SE3 delayed anchor differs")
        for key in ("F3_SF3_over_SE3_full_envelope", "F3_componentwise_proxy_SF3_over_SE3_full_envelope", "S20_SF3_over_SE3_full_envelope"):
            check.expect(ratios.get(key) == UNAVAILABLE, f"fair ratio {key} is not unavailable by user scope")
        check.expect(ratios.get("status") == UNAVAILABLE and ratio_contract.get("status") == UNAVAILABLE, "mission fair-ratio status differs")
        check.expect(stage06.get("old_post_be_ratio_eligible") is False, "old post-Be result was made ratio eligible")
        if run_delayed is not None:
            zero_families = {str(plan_by_id[job_id]["family"]) for job_id in zero_delayed}
            proxy = sf3.get("zero_A15_proxy_contract") or {}
            uncertainty_zero = get_nested(stage06, "uncertainty_contract", "zero_A15") or {}
            check.expect(set(proxy.get("families") or []) == zero_families, "stage06 zero-A15 proxy family closure differs")
            check.expect(proxy.get("central_rate") == "EXACT_ZERO", "stage06 zero-A15 central rate differs")
            check.expect(proxy.get("inventory_sentinel_created") is False, "stage06 created a zero-A15 inventory sentinel")
            check.expect(set((proxy.get("provenance") or {}).keys()) == zero_families, "stage06 zero-A15 proxy provenance closure differs")
            check.expect(set(uncertainty_zero.get("registered_families") or []) == zero_families, "stage06 uncertainty zero-A15 family closure differs")
            check.expect(uncertainty_zero.get("central") == "EXACT_ZERO__NO_INVENTORY_SENTINEL", "stage06 uncertainty zero-A15 central contract differs")
        physics["mission20"] = {
            "SF3_S20_counts": sf3.get("source_counts_20d"),
            "SF3_S20_lower95_counts": sf3.get("source_lower95_counts_20d"),
            "SF3_B20_counts": sf3.get("background_counts_20d"),
            "SF3_B20_upper95_proxy_counts": sf3.get("background_upper95_proxy_counts_20d"),
            "SF3_Z20": sf3.get("Z20d"),
            "SF3_Z20_componentwise_proxy": sf3.get("Z20d_componentwise_proxy"),
            "SF3_F3_ph_cm2_s": sf3.get("F3_20d_ph_cm2_s"),
            "SF3_F3_componentwise_proxy_ph_cm2_s": sf3.get("F3_20d_componentwise_proxy_ph_cm2_s"),
            "SE3_frozen_B20_counts": se3.get("background_counts_20d"),
            "SE3_frozen_B20_upper95_proxy_counts": se3.get("background_upper95_proxy_counts_20d"),
            "SF3_over_frozen_SE3_B20": ratios.get("B20_SF3_over_SE3_frozen_background"),
            "SF3_over_SE3_full_envelope_F3": UNAVAILABLE,
            "SF3_over_SE3_full_envelope_F3_proxy": UNAVAILABLE,
        }
        physics["old_post_be_continuity_only"] = stage06.get("old_post_be_continuity")

    resource_totals = {
        "effective_job_count": len(expected_ids) if run_delayed is not None else None,
        "validated_receipt_count": len(receipt_rows),
        "background_jobs": EXPECTED_BACKGROUND_JOBS,
        "instant_histories": EXPECTED_INSTANT,
        "buildup_histories": EXPECTED_BUILDUP,
        "delayed_RUN_cells": len(run_delayed) if run_delayed is not None else None,
        "delayed_zero_A15_skips": len(zero_delayed) if run_delayed is not None else None,
        "delayed_triggers": EXPECTED_DELAYED_EVENTS * len(run_delayed) if run_delayed is not None else None,
        "SF3_signal_trials": EXPECTED_SIGNAL_EVENTS,
        "sim_bytes_from_receipts": sum(row["sim_bytes"] for row in receipt_rows),
        "log_bytes_from_receipts": sum(row["log_bytes"] for row in receipt_rows),
        "artifact_bytes_from_receipts": sum(row["artifact_bytes"] for row in receipt_rows),
        "wall_s_sum": math.fsum(row["wall_s"] for row in receipt_rows),
        "beam_on_cpu_s_sum": math.fsum(row["beam_on_cpu_s"] for row in receipt_rows),
        "peak_process_group_rss_bytes_max": max((row["peak_process_group_rss_bytes"] for row in receipt_rows), default=0),
        "disk_free_bytes_at_check": shutil.disk_usage(package_root).free,
        "dynamic_reserve_bytes": DYNAMIC_RESERVE_BYTES,
        "dynamic_reserve_pass_at_check": shutil.disk_usage(package_root).free >= DYNAMIC_RESERVE_BYTES,
        "cache_bytes_removed": (disk_recovery or {}).get("cache_bytes_removed"),
        "interrupted_partial_sim_bytes_reclaimed": (interrupt or {}).get("partial_sim_bytes_reclaimed"),
    }
    check.expect(resource_totals["dynamic_reserve_pass_at_check"] is True, "current disk free is below the 8 GiB reserve")
    if run_delayed is not None and expected_ids.issubset(receipt_ids):
        check.expect(len(receipt_rows) == len(expected_ids), "effective canonical receipt count differs")
        check.expect(sum(row["events"] for row in receipt_rows if row["mode"] == "instant") == EXPECTED_INSTANT, "receipt instant total differs")
        check.expect(sum(row["events"] for row in receipt_rows if row["mode"] == "buildup") == EXPECTED_BUILDUP, "receipt buildup total differs")
        check.expect(sum(row["events"] for row in receipt_rows if row["stage"] == "delayed") == EXPECTED_DELAYED_EVENTS * len(run_delayed), "receipt delayed total differs")
        check.expect(sum(row["events"] for row in receipt_rows if row["stage"] == "signal") == EXPECTED_SIGNAL_EVENTS, "receipt SF3 signal total differs")
        check.expect(all(row["geometry"] == "SF3" for row in receipt_rows), "effective receipt set is not strictly SF3-only")

    already_built = output_root.exists()
    if already_built:
        check.errors.append(f"write-once stage07 output already exists: {output_root}")
    ready = not check.errors and not check.missing
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": "READY__SF3_EFFECTIVE_CHAIN_FINAL_AUDIT" if ready else ("FAIL__SF3_FINAL_CHAIN_CONTRACT" if check.errors else "NOT_READY__SF3_FINAL_CHAIN_INPUTS_INCOMPLETE"),
        "ready": ready,
        "checked_at": utc_now(),
        "package_root": norm(package_root),
        "run_root": norm(run_root),
        "output_root": norm(output_root),
        "scope": "EFFECTIVE_SF3_ONLY__SE3_FROZEN_SMALL_TABLES_ONLY",
        "execution_scope": {
            "registered_plan_jobs": len(plan),
            "effective_job_ids": sorted(expected_ids),
            "effective_job_count": len(expected_ids) if run_delayed is not None else None,
            "configured_exclusions": exclusions,
            "dynamic_zero_A15_exclusions": sorted(zero_delayed),
            "fresh_se3_transport_receipts_allowed": False,
        },
        "stage_bindings": stage_bindings,
        "job_receipts": receipt_rows,
        "resource_totals": resource_totals,
        "physics_results": physics,
        "input_authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "errors": check.errors,
        "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__CANONICAL_RECEIPT_FIELDS_ONLY",
        "authority_boundary": "PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN__NO_AUTOMATIC_GEOMETRY_PROMOTION",
    }


RECEIPT_FIELDS = (
    "job_id", "receipt_path", "receipt_sha256", "stage", "geometry", "mode", "family",
    "events", "seed", "attempt", "source_path", "source_sha256", "setup_path",
    "header_geometry", "header_seed", "sim_path", "sim_bytes", "log_path", "log_bytes",
    "isotope_dat_bytes", "artifact_bytes", "peak_process_group_rss_bytes", "wall_s",
    "beam_on_cpu_s", "TT_s", "RP_record_count",
)


def receipt_csv_text(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=RECEIPT_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in RECEIPT_FIELDS})
    return stream.getvalue()


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def report_text(audit: dict[str, Any]) -> str:
    physics = audit["physics_results"]
    day15 = physics["day15_common_response"]
    signal = physics["full_envelope_signal"]
    mission = physics["mission20"]
    lines = [
        "# SF3 Plan-1 final chain audit",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This is the effective SF3-only approximately one-third atmospheric cosmic-ray screen. No fresh SE3 transport receipt or SIM is used. SE3 enters only through frozen corrected-M05 small-table background anchors.",
        "",
        "## Chain closure",
        "",
        "| Stage | Status | Summary |",
        "|---|---|---|",
    ]
    for stage in sorted(audit["stage_bindings"]):
        row = audit["stage_bindings"][stage]
        lines.append(f"| {stage} | {row['observed_status']} | `{row['summary_path']}` |")
    lines.extend([
        "",
        "## Central results",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| SF3 day-15 prompt W2 rate (cps) | {fmt(day15['prompt_w2_cps'])} |",
        f"| SF3 day-15 delayed W2 rate (cps) | {fmt(day15['delayed_w2_cps'])} |",
        f"| SF3 day-15 total W2 background (cps) | {fmt(day15['background_w2_cps'])} |",
        f"| SF3 full-envelope selected rays | {fmt(signal['selected_events'])} / {EXPECTED_SIGNAL_EVENTS} |",
        f"| SF3 full-envelope W2 Aeff (cm²) | {fmt(signal['Aeff_cm2'])} |",
        f"| SF3 S20 (counts/20 d at reference flux) | {fmt(mission['SF3_S20_counts'])} |",
        f"| SF3 B20 (counts/20 d) | {fmt(mission['SF3_B20_counts'])} |",
        f"| SF3 F3 central (ph cm⁻² s⁻¹) | {fmt(mission['SF3_F3_ph_cm2_s'])} |",
        f"| SF3 F3 componentwise proxy (ph cm⁻² s⁻¹) | {fmt(mission['SF3_F3_componentwise_proxy_ph_cm2_s'])} |",
        f"| SF3/SE3 frozen-background B20 ratio | {fmt(mission['SF3_over_frozen_SE3_B20'])} |",
        f"| Fair SF3/SE3 full-envelope F3 ratio | {UNAVAILABLE} |",
        f"| Fair SF3/SE3 full-envelope F3 proxy ratio | {UNAVAILABLE} |",
        "",
        "The historical SE3 post-Be 37,194→27,855 result is retained separately for continuity only. It is excluded from every full-envelope signal, S20, Z20, and F3 geometry ratio.",
        "",
        "## Effective transport receipts",
        "",
        "| Job | Stage/mode/family | Events | Seed | Attempt | SIM bytes (receipt) | Receipt |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    for row in audit["job_receipts"]:
        label = f"{row['stage']}/{row['mode']}/{row['family']}"
        lines.append(f"| {row['job_id']} | {label} | {row['events']} | {row['seed']} | {row['attempt']} | {row['sim_bytes']} | `{row['receipt_path']}` |")
    resources = audit["resource_totals"]
    lines.extend([
        "",
        "## Resource receipt totals",
        "",
        f"- Effective jobs: {resources['effective_job_count']} (21 background + {resources['delayed_RUN_cells']} delayed RUN + 1 SF3 signal).",
        f"- Dynamic zero-A15 skips: {resources['delayed_zero_A15_skips']}.",
        f"- SIM bytes from receipt metadata: {resources['sim_bytes_from_receipts']:,}; artifact bytes: {resources['artifact_bytes_from_receipts']:,}.",
        f"- Maximum audited process-group RSS: {resources['peak_process_group_rss_bytes_max']:,} bytes.",
        f"- Disk free before stage07 publication: {resources['disk_free_bytes_at_check']:,} bytes; 8 GiB reserve pass: {resources['dynamic_reserve_pass_at_check']}.",
        "",
        f"Machine-readable audit: `{audit['final_paths']['final_audit']}`",
        f"Receipt table: `{audit['final_paths']['job_receipts']}`",
        "",
        "No SIM payload was opened, statted, or hashed by this finalizer.",
        "",
    ])
    return "\n".join(lines)


def build(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    checked = check_prerequisites(config_path)
    if not checked.get("ready"):
        raise RuntimeError(json_text(checked))
    output = Path(checked["output_root"])
    if output.exists():
        raise FileExistsError(f"write-once stage07 output exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".07_final_audit.work-", dir=output.parent))
    try:
        final_paths = {
            "final_audit": norm(output / "final_audit.json"),
            "job_receipts": norm(output / "job_receipts.csv"),
            "final_report": norm(output / "FINAL_REPORT.md"),
        }
        audit = dict(checked)
        audit.update({
            "status": "PASS__SF3_PLAN1_EFFECTIVE_SF3_ONLY_CHAIN_COMPLETE",
            "ready": True,
            "finalized_at": utc_now(),
            "final_paths": final_paths,
            "write_contract": "ATOMIC_DIRECTORY_RENAME__WRITE_ONCE",
        })
        (work / "job_receipts.csv").write_text(receipt_csv_text(audit["job_receipts"]), encoding="utf-8")
        (work / "FINAL_REPORT.md").write_text(report_text(audit), encoding="utf-8")
        (work / "final_audit.json").write_text(json_text(audit), encoding="utf-8")
        for path in work.iterdir():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        os.replace(work, output)
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            "schema_version": 1,
            "status": audit["status"],
            "output_root": norm(output),
            "final_paths": final_paths,
            "effective_job_count": audit["resource_totals"]["effective_job_count"],
            "SF3_F3_ph_cm2_s": get_nested(audit, "physics_results", "mission20", "SF3_F3_ph_cm2_s"),
            "SF3_F3_componentwise_proxy_ph_cm2_s": get_nested(audit, "physics_results", "mission20", "SF3_F3_componentwise_proxy_ph_cm2_s"),
            "fair_SE3_full_envelope_F3_ratio": UNAVAILABLE,
        }
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    """Exercise small-fixture parsing and receipt binding without a SIM file."""
    with tempfile.TemporaryDirectory(prefix="sf3_finalizer_selftest_") as temp:
        root = Path(temp)
        fixture = root / "receipt.json"
        job = {
            "job_id": "synthetic", "stage": "background", "geometry": "SF3",
            "mode": "instant", "family": "gamma", "events": 7, "seed": 11,
            "source_path": "/synthetic/source.source", "setup_path": "/synthetic/SF3.geo.setup",
        }
        payload = {
            **job, "status": "PASS", "errors": [], "attempt": 1,
            "source_sha256": "0" * 64, "sim_path": "/synthetic/not-opened.sim.gz",
            "log_path": "/synthetic/run.log", "attempt_dir": "/synthetic/attempt01",
            "sim_bytes": 100, "log_bytes": 20, "isotope_dat_bytes": 3,
            "artifact_bytes": 123, "peak_process_group_rss_bytes": 50,
            "wall_s": 1.5, "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
            "sim_header": {"geometry": job["setup_path"], "seed": 11},
            "log": {"generated_events": 7, "graphics_terminal_marker": True, "beam_on_cpu_s": 1.0},
            "isotope_dat": {"TT_s": 2.0, "RP_record_count": 0},
        }
        fixture.write_text(json_text(payload), encoding="utf-8")
        checker = Checker()
        observed = load_small_json(fixture)
        row = validate_receipt(job, observed, fixture, checker)
        if checker.errors or row is None or row["artifact_bytes"] != 123:
            raise AssertionError(f"synthetic receipt fixture failed: {checker.errors}")
        if Path(row["sim_path"]).exists():
            raise AssertionError("synthetic SIM unexpectedly exists")
        if UNAVAILABLE != "UNAVAILABLE_BY_USER_SCOPE":
            raise AssertionError("ratio-unavailable token drift")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FINALIZER_SYNTHETIC_SMALL_FIXTURE_SELF_TEST",
        "checks": [
            "small_JSON_fixture", "receipt_source_header_seed_event_binding",
            "artifact_byte_closure", "SIM_path_not_opened_or_created",
            "UNAVAILABLE_BY_USER_SCOPE_ratio_contract",
        ],
        "files_written_outside_tmp": False,
        "sim_opened_statted_or_hashed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-prerequisites", action="store_true", help="read-only small-authority readiness check")
    actions.add_argument("--build", action="store_true", help="atomically publish write-once outputs/07_final_audit")
    actions.add_argument("--self-test", action="store_true", help="run synthetic small-fixture checks in /tmp")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites:
            result = check_prerequisites(args.config.resolve())
        else:
            result = build(args.config.resolve())
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready", False):
            return 2 if not result.get("errors") else 1
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "status": "FAIL__SF3_FINALIZER",
            "error": str(exc),
            "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__CANONICAL_RECEIPT_FIELDS_ONLY",
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
