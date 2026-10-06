#!/usr/bin/env python3
"""Preflight and compact the retained M05 SG3/SH3 prompt supplements.

The default operation is a targeted, header-only preflight.  Raw SIM payloads
are streamed only when ``--execute`` is supplied, and then only through the
retained package-62 SG3 or current Step05-exact SH3 ``scan_job`` function.
This program never launches Cosima and never computes a SIM digest.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = HERE.parents[4]
DEFAULT_MANIFEST = PACKAGE / "analysis_manifest.json"
OUTPUTS = PACKAGE / "outputs"

PASS_RECEIPT = "PASS"
PASS_COMPACT = "PASS__COMPACT_JOB_CATALOG"
FORBIDDEN_LEGACY_SPECTRUM = "cosima_spectra_dp_2602units"
CORRECTED_SPECTRUM_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"

SOURCE_GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$", re.MULTILINE)
SOURCE_SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$", re.MULTILINE)
SOURCE_RUN_RE = re.compile(r"^Run\s+(\S+)\s*$", re.MULTILINE)
SIM_ID_RE = re.compile(r"^ID\s+\d+\s+\d+")


class ClosureError(RuntimeError):
    """An authority or provenance closure check failed."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - message enrichment
        raise ClosureError(f"cannot read JSON authority {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    resolved = path.resolve(strict=True) if path.is_absolute() else (ROOT / path).resolve(strict=True)
    return resolved


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def sha256_small(path: Path, *, max_bytes: int = 64 * 1024 * 1024) -> str:
    """Hash a small authority and fail closed if a SIM-like payload is passed."""
    lower = path.name.lower()
    if lower.endswith((".sim", ".sim.gz")):
        raise ClosureError(f"refusing to hash SIM payload: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ClosureError(f"small-authority hash size guard exceeded ({size} bytes): {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    observed = sha256_small(path)
    if observed != expected:
        raise ClosureError(f"{label} SHA-256 mismatch: {path}: {observed} != {expected}")
    return observed


def decode_mount_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def mount_authority(path: Path) -> dict[str, Any]:
    target = path.resolve(strict=True)
    matches: list[tuple[int, dict[str, Any]]] = []
    for raw in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if "-" not in fields or len(fields) < 10:
            continue
        separator = fields.index("-")
        mountpoint = Path(decode_mount_field(fields[4]))
        try:
            resolved_mountpoint = mountpoint.resolve(strict=True)
        except FileNotFoundError:
            continue
        if target == resolved_mountpoint or is_below(target, resolved_mountpoint):
            options = set(fields[5].split(","))
            super_options = set(fields[separator + 3].split(","))
            matches.append(
                (
                    len(str(resolved_mountpoint)),
                    {
                        "mountpoint": str(resolved_mountpoint),
                        "source": fields[separator + 2],
                        "filesystem": fields[separator + 1],
                        "mount_options": sorted(options),
                        "super_options": sorted(super_options),
                        "read_only": "ro" in options or "ro" in super_options,
                    },
                )
            )
    if not matches:
        raise ClosureError(f"cannot resolve mount authority for {target}")
    authority = max(matches, key=lambda row: row[0])[1]
    if Path(authority["mountpoint"]) != target:
        raise ClosureError(
            f"configured external root is not itself a mountpoint: {target} -> {authority['mountpoint']}"
        )
    if not authority["read_only"]:
        raise ClosureError(f"external data mount is not read-only: {target}")
    return authority


def map_external_path(path_text: str, legacy_prefix: Path, mount_root: Path) -> Path:
    """Map only an absolute legacy /mnt/data path into the configured RO mount."""
    pure = PurePosixPath(path_text)
    try:
        relative = pure.relative_to(PurePosixPath(str(legacy_prefix)))
    except ValueError as exc:
        raise ClosureError(f"external path does not use the permitted legacy prefix: {path_text}") from exc
    candidate = mount_root.joinpath(*relative.parts).resolve(strict=True)
    if not is_below(candidate, mount_root):
        raise ClosureError(f"mapped path escapes read-only mount: {path_text} -> {candidate}")
    return candidate


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise ClosureError(f"{label} mismatch: {observed!r} != {expected!r}")


def require_path_equal(observed: str, expected: str, label: str) -> None:
    observed_path = Path(observed).resolve(strict=True)
    expected_path = Path(expected).resolve(strict=True)
    if observed_path != expected_path:
        raise ClosureError(f"{label} path mismatch: {observed_path} != {expected_path}")


def one_match(pattern: re.Pattern[str], text: str, label: str, path: Path) -> str:
    values = pattern.findall(text)
    if len(values) != 1:
        raise ClosureError(f"{label} must occur exactly once in {path}; found {len(values)}")
    return values[0]


def source_card_authority(path: Path, job_id: str) -> dict[str, Any]:
    payload = path.read_bytes()
    text = payload.decode("utf-8", errors="strict")
    if FORBIDDEN_LEGACY_SPECTRUM in text:
        raise ClosureError(f"legacy factor-1000 spectrum reference in {path}")
    if CORRECTED_SPECTRUM_TOKEN not in text:
        raise ClosureError(f"corrected-keV spectrum authority token missing in {path}")
    geometry = one_match(SOURCE_GEOMETRY_RE, text, "Geometry", path)
    seed = int(one_match(SOURCE_SEED_RE, text, "Seed", path))
    run = one_match(SOURCE_RUN_RE, text, "Run", path)
    escaped = re.escape(job_id)
    events = int(
        one_match(
            re.compile(rf"^{escaped}\.Events\s+(\d+)\s*$", re.MULTILINE),
            text,
            f"{job_id}.Events",
            path,
        )
    )
    filename = one_match(
        re.compile(rf"^{escaped}\.FileName\s+(\S+)\s*$", re.MULTILINE),
        text,
        f"{job_id}.FileName",
        path,
    )
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "geometry": geometry,
        "seed": seed,
        "run": run,
        "events": events,
        "filename": filename,
        "bytes": len(payload),
    }


def sim_header_authority(path: Path, *, maximum_uncompressed_bytes: int = 1024 * 1024) -> dict[str, Any]:
    """Read only the small text header, stopping before the first event ID."""
    geometry: str | None = None
    seed: int | None = None
    consumed = 0
    lines = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
            for raw in handle:
                consumed += len(raw.encode("utf-8"))
                lines += 1
                if consumed > maximum_uncompressed_bytes:
                    raise ClosureError(f"SIM header exceeds {maximum_uncompressed_bytes} bytes: {path}")
                line = raw.strip()
                if line.startswith("Geometry "):
                    if geometry is not None:
                        raise ClosureError(f"duplicate Geometry header in {path}")
                    geometry = line.split(maxsplit=1)[1]
                elif line.startswith("Seed "):
                    if seed is not None:
                        raise ClosureError(f"duplicate Seed header in {path}")
                    seed = int(line.split()[1])
                if SIM_ID_RE.match(line):
                    break
    except ClosureError:
        raise
    except Exception as exc:
        raise ClosureError(f"cannot read gzip SIM header {path}: {exc}") from exc
    if geometry is None or seed is None:
        raise ClosureError(f"incomplete SIM header before first event: {path}")
    return {
        "geometry": geometry,
        "seed": seed,
        "uncompressed_bytes_read": consumed,
        "lines_read": lines,
        "policy": "HEADER_ONLY__NO_SIM_DIGEST",
    }


def indexed(rows: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = str(row.get(key, ""))
        if not identity or identity in output:
            raise ClosureError(f"{label} has missing or duplicate {key}: {identity!r}")
        output[identity] = row
    return output


def validate_code_authorities(model: str, cfg: dict[str, Any]) -> dict[str, Any]:
    parser_path = repo_path(cfg["parser"])
    response_path = repo_path(cfg["response_config"])
    result = {
        "parser": str(parser_path),
        "parser_sha256": require_sha(parser_path, cfg["parser_sha256"], f"{model} parser"),
        "response_config": str(response_path),
        "response_config_sha256": require_sha(
            response_path, cfg["response_config_sha256"], f"{model} response config"
        ),
    }
    if model == "sh3":
        step05_path = repo_path(cfg["step05"])
        result.update(
            {
                "step05": str(step05_path),
                "step05_sha256": require_sha(step05_path, cfg["step05_sha256"], "SH3 Step05"),
            }
        )
    return result


def response_parameters(model: str, cfg: dict[str, Any]) -> dict[str, Any]:
    response = load_json(repo_path(cfg["response_config"]))
    active = response["active_veto"]
    parameters = {
        "plastic_volumes": list(active["plastic_positron_veto_volumes"]),
        "bgo_volumes": list(active["bgo_active_scintillator_volumes"]),
        "threshold_keV": float(active.get("offline_threshold_keV", 50.0)),
    }
    if model == "sh3":
        side = response["side_entry_disk"]
        parameters["side_entry_disk"] = {
            "local_center_cm": [float(value) for value in side["local_center_cm"]],
            "radius_cm": float(side["radius_cm"]),
            "rotation_y_deg": float(side["rotation_y_deg"]),
            "reject_policy": str(side.get("reject_policy", "keep")),
        }
    return parameters


def base_overlap_audit(model_cfg: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    base_job_ids: set[str] = set()
    base_seeds: set[int] = set()
    authorities: list[dict[str, Any]] = []
    for source in model_cfg["base_lineage"]:
        path = repo_path(source["path"])
        payload = load_json(path)
        rows = payload.get(source["jobs_key"])
        if not isinstance(rows, list):
            raise ClosureError(f"base lineage jobs list missing: {path}:{source['jobs_key']}")
        missing_seed = 0
        for row in rows:
            if row.get("job_id") is not None:
                base_job_ids.add(str(row["job_id"]))
            if row.get(source["seed_key"]) is None:
                missing_seed += 1
            else:
                base_seeds.add(int(row[source["seed_key"]]))
        if missing_seed:
            raise ClosureError(f"base lineage rows lack seeds: {path}: {missing_seed}")
        authorities.append(
            {
                "path": str(path),
                "jobs_key": source["jobs_key"],
                "seed_key": source["seed_key"],
                "rows": len(rows),
            }
        )
    new_ids = {str(job["job_id"]) for job in jobs}
    new_seeds = {int(job["seed"]) for job in jobs}
    duplicate_job_ids = sorted(new_ids & base_job_ids)
    duplicate_seeds = sorted(new_seeds & base_seeds)
    status = "PASS__NO_BASE_JOB_OR_SEED_OVERLAP" if not duplicate_job_ids and not duplicate_seeds else "FAIL"
    if status != "PASS__NO_BASE_JOB_OR_SEED_OVERLAP":
        raise ClosureError(
            f"supplement overlaps {len(duplicate_job_ids)} base job IDs and {len(duplicate_seeds)} base seeds"
        )
    return {
        "status": status,
        "authorities": authorities,
        "base_unique_job_ids": len(base_job_ids),
        "base_unique_seeds": len(base_seeds),
        "duplicate_job_ids": duplicate_job_ids,
        "duplicate_seeds": duplicate_seeds,
    }


def validate_receipt(
    *,
    model: str,
    family: str,
    receipt_path: Path,
    plan: dict[str, Any],
    source_manifest_row: dict[str, Any],
    seed_registry_row: dict[str, Any],
    controller_status: str,
    model_cfg: dict[str, Any],
    response: dict[str, Any],
    legacy_prefix: Path,
    mount_root: Path,
    bundle_sources_root: Path,
) -> dict[str, Any]:
    receipt = load_json(receipt_path)
    job_id = str(receipt.get("job_id", ""))
    context = f"{model}/{family}/{job_id or receipt_path.name}"
    forbidden_task_id = str(model_cfg["forbidden_task_id"])
    for path_field in ("source_path", "setup_path", "sim_path", "log_path", "isotope_dat_path"):
        if forbidden_task_id in str(receipt.get(path_field, "")):
            raise ClosureError(f"{context} {path_field} references the forbidden task")
    require_equal(receipt_path.stem, job_id, f"{context} receipt filename")
    require_equal(receipt.get("status"), PASS_RECEIPT, f"{context} receipt status")
    require_equal(int(receipt.get("returncode", -1)), 0, f"{context} returncode")
    require_equal(receipt.get("errors"), [], f"{context} receipt errors")
    require_equal(receipt.get("watchdog_reason"), "completed", f"{context} watchdog")
    require_equal(receipt.get("candidate"), model_cfg["candidate"], f"{context} candidate")
    require_equal(receipt.get("family"), family, f"{context} family")
    require_equal(receipt.get("mode"), "instant", f"{context} mode")

    for field in ("job_id", "family", "candidate", "mode", "seed", "events", "setup_path", "source_path"):
        require_equal(receipt.get(field), plan.get(field), f"{context} receipt/job-plan {field}")
    for field in ("job_id", "family", "mode", "seed", "events", "setup_path", "source_path"):
        require_equal(receipt.get(field), source_manifest_row.get(field), f"{context} receipt/source-manifest {field}")
    require_equal(seed_registry_row.get("job_id"), job_id, f"{context} seed-registry job")
    require_equal(int(seed_registry_row.get("seed", -1)), int(receipt["seed"]), f"{context} seed-registry seed")

    source = Path(str(receipt["source_path"])).resolve(strict=True)
    if not is_below(source, bundle_sources_root):
        raise ClosureError(f"{context} source escapes configured bundle source root: {source}")
    source_info = source_card_authority(source, job_id)
    require_equal(source_info["sha256"], receipt.get("source_sha256"), f"{context} receipt source SHA")
    require_equal(
        source_info["sha256"], source_manifest_row.get("source_sha256"), f"{context} manifest source SHA"
    )
    require_equal(source_info["run"], job_id, f"{context} source Run")
    require_equal(source_info["seed"], int(receipt["seed"]), f"{context} source seed")
    require_equal(source_info["events"], int(receipt["events"]), f"{context} source events")
    require_equal(source_info["filename"], plan.get("output_prefix"), f"{context} source output prefix")

    setup = Path(str(receipt["setup_path"])).resolve(strict=True)
    require_path_equal(source_info["geometry"], str(setup), f"{context} source/setup")
    require_equal(
        sha256_small(setup), model_cfg["expected_setup_sha256"], f"{context} setup SHA"
    )
    sim_header_receipt = receipt.get("sim_header", {})
    require_path_equal(str(sim_header_receipt.get("geometry", "")), str(setup), f"{context} receipt SIM geometry")
    require_equal(int(sim_header_receipt.get("seed", -1)), int(receipt["seed"]), f"{context} receipt SIM seed")
    require_equal(
        receipt.get("sim_digest_policy"),
        "OMITTED__PATH_SIZE_AND_HEADER_ONLY",
        f"{context} SIM digest policy",
    )
    if "HEADER_ONLY" not in str(sim_header_receipt.get("policy", "")):
        raise ClosureError(f"{context} receipt SIM-header policy is not header-only")

    sim = map_external_path(str(receipt["sim_path"]), legacy_prefix, mount_root)
    log = map_external_path(str(receipt["log_path"]), legacy_prefix, mount_root)
    isotope_dat = map_external_path(str(receipt["isotope_dat_path"]), legacy_prefix, mount_root)
    require_equal(sim.stat().st_size, int(receipt["sim_bytes"]), f"{context} SIM size")
    require_equal(log.stat().st_size, int(receipt["log_bytes"]), f"{context} log size")
    require_equal(isotope_dat.stat().st_size, int(receipt["isotope_dat_bytes"]), f"{context} isotope DAT size")
    artifact_sum = int(receipt["sim_bytes"]) + int(receipt["log_bytes"]) + int(receipt["isotope_dat_bytes"])
    require_equal(artifact_sum, int(receipt["artifact_bytes"]), f"{context} artifact-byte closure")

    actual_header = sim_header_authority(sim)
    require_path_equal(actual_header["geometry"], str(setup), f"{context} actual SIM geometry")
    require_equal(actual_header["seed"], int(receipt["seed"]), f"{context} actual SIM seed")

    log_meta = receipt.get("log", {})
    require_equal(int(log_meta.get("generated_events", -1)), int(receipt["events"]), f"{context} log events")
    require_equal(log_meta.get("error_marker"), False, f"{context} log error marker")
    require_equal(log_meta.get("graphics_terminal_marker"), True, f"{context} log terminal marker")
    isotope_meta = receipt.get("isotope_dat", {})
    require_equal(isotope_meta.get("terminal_EN"), True, f"{context} isotope terminal EN")
    require_equal(int(isotope_meta.get("RP_record_count", -1)), 0, f"{context} prompt RP count")
    require_equal(isotope_meta.get("errors"), [], f"{context} isotope errors")
    tt_s = float(isotope_meta.get("TT_s", 0.0))
    if not math.isfinite(tt_s) or tt_s <= 0.0:
        raise ClosureError(f"{context} actual receipt exposure is not positive: {tt_s}")
    if not math.isclose(tt_s, float(log_meta.get("observation_time_s", -1.0)), rel_tol=0.0, abs_tol=1e-12):
        raise ClosureError(f"{context} TT/log observation-time closure differs")

    if model_cfg["setup_stratum"] != "main":
        raise ClosureError(f"{context} only the main setup stratum is accepted here")
    if forbidden_task_id in str(receipt_path):
        raise ClosureError(f"{context} forbidden task path encountered")

    return {
        "stream": "prompt",
        "family": family,
        "mode": "instant",
        "batch_id": "m05new_zero_prompt_supplement_20260823_v1",
        "job_id": job_id,
        "seed": int(receipt["seed"]),
        "events": int(receipt["events"]),
        "sim_path": str(sim),
        "sim_path_receipt": str(receipt["sim_path"]),
        "sim_bytes": int(receipt["sim_bytes"]),
        "source_path": str(source),
        "source_sha256": source_info["sha256"],
        "expected_geometry": str(setup),
        "setup_sha256": model_cfg["expected_setup_sha256"],
        "setup_stratum": "main",
        "weight_cps": 0.0,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
        "plastic_volumes": response["plastic_volumes"],
        "bgo_volumes": response["bgo_volumes"],
        "positions_path": None,
        "exposure_TT_s": tt_s,
        "receipt_path": str(receipt_path),
        "controller_status": controller_status,
        "sim_header": actual_header,
    }


def validate_model_inputs(
    model: str,
    model_cfg: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    code = validate_code_authorities(model, model_cfg)
    response = response_parameters(model, model_cfg)
    threshold = float(manifest["offline_veto_threshold_keV"])
    if not math.isclose(response["threshold_keV"], threshold, rel_tol=0.0, abs_tol=1e-12):
        raise ClosureError(f"{model} response threshold differs from integration manifest")

    legacy_prefix = Path(manifest["legacy_external_prefix"])
    mount_root = Path(manifest["readonly_external_mount"]).resolve(strict=True)
    external_original = Path(model_cfg["external_root"])
    external = map_external_path(str(external_original), legacy_prefix, mount_root)
    bundle_root = repo_path(model_cfg["bundle_root"])
    forbidden = str(manifest["forbidden_task_id"])
    if forbidden in str(external) or forbidden in str(bundle_root):
        raise ClosureError(f"forbidden task entered {model} input roots")

    expected_family_counts = {str(key): int(value) for key, value in model_cfg["families"].items()}
    jobs: list[dict[str, Any]] = []
    family_audit: dict[str, Any] = {}
    planned_ids_all: set[str] = set()
    completed_ids_all: set[str] = set()

    for family, expected_completed in expected_family_counts.items():
        bundle = bundle_root / family
        run = external / family / "run"
        controller_path = run / "controller_state.json"
        receipt_dir = run / "receipts"
        config_path = bundle / "config.json"
        generated = bundle / "generated"
        plan_path = generated / "job_plan.json"
        source_manifest_path = generated / "source_manifest.json"
        seed_registry_path = generated / "seed_registry.json"
        preflight_path = generated / "preflight.json"
        for path in (
            controller_path,
            receipt_dir,
            config_path,
            plan_path,
            source_manifest_path,
            seed_registry_path,
            preflight_path,
        ):
            if not path.exists():
                raise ClosureError(f"missing configured {model}/{family} authority: {path}")

        config = load_json(config_path)
        controller = load_json(controller_path)
        plan_payload = load_json(plan_path)
        source_payload = load_json(source_manifest_path)
        seed_payload = load_json(seed_registry_path)
        preflight = load_json(preflight_path)
        require_equal(config.get("candidate"), model_cfg["candidate"], f"{model}/{family} config candidate")
        require_equal(preflight.get("status"), config.get("preflight_pass_status"), f"{model}/{family} preflight")
        require_equal(source_payload.get("status"), config.get("source_manifest_pass_status"), f"{model}/{family} source manifest")
        require_equal(seed_payload.get("status"), config.get("seed_registry_pass_status"), f"{model}/{family} seed registry")
        require_equal(plan_payload.get("status"), "PASS", f"{model}/{family} job plan")
        require_path_equal(config["geometry_setup"], plan_payload["jobs"][0]["setup_path"], f"{model}/{family} configured setup")
        require_equal(config.get("source_policy"), "corrected_keV_background", f"{model}/{family} source policy")
        require_equal(config.get("forbidden_legacy_token"), FORBIDDEN_LEGACY_SPECTRUM, f"{model}/{family} forbidden spectrum")
        require_equal(config.get("corrected_token"), CORRECTED_SPECTRUM_TOKEN, f"{model}/{family} corrected spectrum")

        plan_by = indexed(plan_payload.get("jobs", []), "job_id", f"{model}/{family} job plan")
        source_by = indexed(source_payload.get("sources", []), "job_id", f"{model}/{family} source manifest")
        seed_by = indexed(seed_payload.get("seeds", []), "job_id", f"{model}/{family} seed registry")
        configured_jobs = int(config["expected_jobs"])
        require_equal(len(plan_by), configured_jobs, f"{model}/{family} planned jobs")
        require_equal(set(source_by), set(plan_by), f"{model}/{family} source/job-plan IDs")
        require_equal(set(seed_by), set(plan_by), f"{model}/{family} seed/job-plan IDs")

        receipt_paths = sorted(receipt_dir.glob("*.json"))
        require_equal(len(receipt_paths), expected_completed, f"{model}/{family} receipt-PASS count")
        completed_ids = [str(value) for value in controller.get("completed_jobs", [])]
        require_equal(int(controller.get("completed_count", -1)), len(completed_ids), f"{model}/{family} controller count")
        require_equal(set(completed_ids), {path.stem for path in receipt_paths}, f"{model}/{family} controller/receipt IDs")
        if len(completed_ids) == configured_jobs:
            require_equal(controller.get("status"), "COMPLETE", f"{model}/{family} controller status")
            require_equal(controller.get("error"), None, f"{model}/{family} controller error")
            controller_policy = "COMPLETE"
        else:
            if model != "sg3":
                raise ClosureError(f"{model}/{family} is incomplete but only SG3 partial receipt reuse is allowed")
            require_equal(controller.get("status"), "FAILED", f"{model}/{family} partial controller status")
            pending = [str(value) for value in controller.get("pending_jobs", [])]
            if not pending or set(pending) & set(completed_ids):
                raise ClosureError(f"{model}/{family} partial controller pending/completed closure differs")
            if not set(pending).issubset(set(plan_by)):
                raise ClosureError(f"{model}/{family} pending jobs escape job plan")
            controller_policy = "PARTIAL_RECEIPT_REUSE__ACTUAL_TT_ONLY"

        bundle_sources_root = (generated / "sources").resolve(strict=True)
        family_jobs: list[dict[str, Any]] = []
        for receipt_path in receipt_paths:
            receipt_id = receipt_path.stem
            if receipt_id not in plan_by or receipt_id not in source_by or receipt_id not in seed_by:
                raise ClosureError(f"{model}/{family} receipt is absent from generated authorities: {receipt_id}")
            family_jobs.append(
                validate_receipt(
                    model=model,
                    family=family,
                    receipt_path=receipt_path,
                    plan=plan_by[receipt_id],
                    source_manifest_row=source_by[receipt_id],
                    seed_registry_row=seed_by[receipt_id],
                    controller_status=str(controller.get("status")),
                    model_cfg={**model_cfg, "forbidden_task_id": forbidden},
                    response=response,
                    legacy_prefix=legacy_prefix,
                    mount_root=mount_root,
                    bundle_sources_root=bundle_sources_root,
                )
            )
        jobs.extend(family_jobs)
        planned_ids_all.update(plan_by)
        completed_ids_all.update(completed_ids)
        family_audit[family] = {
            "status": "PASS__RECEIPT_SUBSET_CLOSED",
            "controller_status": controller.get("status"),
            "controller_policy": controller_policy,
            "planned_jobs": configured_jobs,
            "completed_receipt_pass_jobs": len(family_jobs),
            "pending_or_unrun_jobs": configured_jobs - len(family_jobs),
            "events": sum(int(job["events"]) for job in family_jobs),
            "sim_bytes": sum(int(job["sim_bytes"]) for job in family_jobs),
            "actual_exposure_TT_s": math.fsum(float(job["exposure_TT_s"]) for job in family_jobs),
            "controller": str(controller_path),
            "job_plan": str(plan_path),
            "source_manifest": str(source_manifest_path),
            "seed_registry": str(seed_registry_path),
        }

    for scan_index, job in enumerate(jobs):
        job["scan_index"] = scan_index
    job_ids = [str(job["job_id"]) for job in jobs]
    seeds = [int(job["seed"]) for job in jobs]
    if len(job_ids) != len(set(job_ids)):
        raise ClosureError(f"{model} duplicate supplement job IDs")
    if len(seeds) != len(set(seeds)):
        raise ClosureError(f"{model} duplicate supplement seeds")
    require_equal(len(jobs), int(model_cfg["expected_receipt_pass_jobs"]), f"{model} total jobs")
    require_equal(sum(int(job["events"]) for job in jobs), int(model_cfg["expected_events"]), f"{model} events")
    if model_cfg.get("expected_sim_bytes") is not None:
        require_equal(
            sum(int(job["sim_bytes"]) for job in jobs),
            int(model_cfg["expected_sim_bytes"]),
            f"{model} SIM bytes",
        )
    overlap = base_overlap_audit(model_cfg, jobs)
    exposure = {
        family: math.fsum(float(job["exposure_TT_s"]) for job in jobs if job["family"] == family)
        for family in expected_family_counts
    }
    audit = {
        "status": "PASS__TARGETED_RECEIPT_HEADER_CLOSURE",
        "model": model,
        "candidate": model_cfg["candidate"],
        "setup_stratum": model_cfg["setup_stratum"],
        "jobs_count": len(jobs),
        "events": sum(int(job["events"]) for job in jobs),
        "sim_bytes": sum(int(job["sim_bytes"]) for job in jobs),
        "families": family_audit,
        "planned_jobs_in_selected_family_campaigns": len(planned_ids_all),
        "completed_receipt_pass_jobs": len(completed_ids_all),
        "exposure_TT_s_by_family": exposure,
        "seeds": seeds,
        "base_overlap_audit": overlap,
        "code_authorities": code,
        "response": response,
        "external_root_receipt": str(external_original),
        "external_root_mapped": str(external),
        "sim_hashes_computed": 0,
        "cosima_transport_started": False,
    }
    return jobs, audit


def selected_models(selection: str) -> list[str]:
    return ["sg3", "sh3"] if selection == "both" else [selection]


def preflight(manifest_path: Path, selection: str) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    manifest = load_json(manifest_path)
    require_equal(manifest.get("status"), "READY__PREFLIGHT_REQUIRED__NO_TRANSPORT", "manifest status")
    forbidden = str(manifest["forbidden_task_id"])
    if forbidden in str(PACKAGE):
        raise ClosureError("integration package path contains forbidden task ID")
    mount_root = Path(manifest["readonly_external_mount"])
    mount = mount_authority(mount_root)

    jobs_by_model: dict[str, list[dict[str, Any]]] = {}
    audits: dict[str, Any] = {}
    all_seeds: list[int] = []
    all_job_ids: list[str] = []
    for model in selected_models(selection):
        model_cfg = manifest["models"][model]
        jobs, audit = validate_model_inputs(model, model_cfg, manifest)
        jobs_by_model[model] = jobs
        audits[model] = audit
        all_seeds.extend(int(job["seed"]) for job in jobs)
        all_job_ids.extend(str(job["job_id"]) for job in jobs)
    if len(all_seeds) != len(set(all_seeds)):
        duplicates = sorted(seed for seed, count in Counter(all_seeds).items() if count > 1)
        raise ClosureError(f"cross-model supplement seed reuse: {duplicates}")
    if len(all_job_ids) != len(set(all_job_ids)):
        duplicates = sorted(job for job, count in Counter(all_job_ids).items() if count > 1)
        raise ClosureError(f"cross-model supplement job-ID reuse: {duplicates}")

    audit = {
        "schema_version": 1,
        "schema": "m05_supplement_preflight_v1",
        "status": "PASS__M05_SUPPLEMENT_TARGETED_PREFLIGHT",
        "selection": selection,
        "manifest": str(manifest_path),
        "mount_authority": mount,
        "models": audits,
        "cross_model_unique_seeds": len(all_seeds),
        "cross_model_unique_job_ids": len(all_job_ids),
        "authority_boundary": {
            "receipt_and_small_authority_files_read": True,
            "sim_headers_read": len(all_job_ids),
            "sim_payloads_streamed": 0,
            "sim_hashes_computed": 0,
            "cosima_transport_started": False,
            "paper_or_ebb2_outputs_modified": False,
            "forbidden_task_outputs_read": False,
        },
    }
    return audit, jobs_by_model


def load_external_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ClosureError(f"cannot import retained scanner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def scan_worker(
    model: str,
    parser_path_text: str,
    response_config_text: str,
    cache_dir_text: str,
    threshold_keV: float,
    job: dict[str, Any],
) -> dict[str, Any]:
    parser_path = Path(parser_path_text)
    module = load_external_module(f"m05_supplement_{model}_{os.getpid()}", parser_path)
    if model == "sg3":
        return module.scan_job(job, cache_dir_text, threshold_keV)
    response = load_json(Path(response_config_text))
    side = response["side_entry_disk"]
    disk = module.side_entry_disk(
        tuple(float(value) for value in side["local_center_cm"]),
        float(side["radius_cm"]),
        float(side["rotation_y_deg"]),
    )
    reject_policy = str(side.get("reject_policy", "keep"))
    return module.scan_job(job, cache_dir_text, threshold_keV, disk, reject_policy)


def expected_cache_paths(model: str, cache_dir: Path, job: dict[str, Any]) -> tuple[Path, Path]:
    stem = f"job_{int(job['scan_index']):03d}_{job['job_id']}"
    if model == "sh3":
        stem += ".step05"
    npz = cache_dir / f"{stem}.npz"
    return npz, npz.with_suffix(".json")


def guard_existing_cache(model: str, cache_dir: Path, jobs: list[dict[str, Any]]) -> None:
    expected: set[Path] = set()
    for job in jobs:
        npz, meta = expected_cache_paths(model, cache_dir, job)
        expected.update((npz, meta))
        if npz.exists() != meta.exists():
            raise ClosureError(f"partial cache pair requires manual review: {npz}, {meta}")
        if not meta.exists():
            continue
        prior = load_json(meta)
        for field in ("job_id", "seed", "events", "sim_bytes", "sim_path"):
            require_equal(prior.get(field), job.get(field), f"{model}/{job['job_id']} cached {field}")
        require_equal(prior.get("status"), PASS_COMPACT, f"{model}/{job['job_id']} cached status")
    extras = sorted(
        str(path)
        for path in cache_dir.glob("*")
        if path.is_file() and path.suffix in {".npz", ".json"} and path not in expected
    )
    if extras:
        raise ClosureError(f"unexpected cache files in {cache_dir}: {extras[:5]}")


def verify_compact_meta(model: str, job: dict[str, Any], meta: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    npz, meta_path = expected_cache_paths(model, cache_dir, job)
    require_equal(meta.get("status"), PASS_COMPACT, f"{model}/{job['job_id']} compact status")
    for field in ("job_id", "seed", "events", "sim_bytes", "sim_path", "family", "batch_id", "stream"):
        require_equal(meta.get(field), job.get(field), f"{model}/{job['job_id']} compact {field}")
    if not npz.is_file() or not meta_path.is_file():
        raise ClosureError(f"compact pair missing after scan: {npz}, {meta_path}")
    require_equal(Path(str(meta.get("catalog_path"))).resolve(strict=True), npz.resolve(strict=True), f"{model} compact path")
    require_equal(float(meta.get("weight_cps", math.nan)), 0.0, f"{model}/{job['job_id']} deferred weight")
    if int(meta.get("detector_positive_events", -1)) < 0:
        raise ClosureError(f"{model}/{job['job_id']} invalid detector-positive count")
    return {
        "job_id": job["job_id"],
        "seed": int(job["seed"]),
        "family": job["family"],
        "stream": "prompt",
        "batch_id": job["batch_id"],
        "setup_stratum": job["setup_stratum"],
        "exposure_TT_s": float(job["exposure_TT_s"]),
        "events": int(job["events"]),
        "sim_bytes": int(job["sim_bytes"]),
        "sim_path": job["sim_path"],
        "receipt_path": job["receipt_path"],
        "source_path": job["source_path"],
        "source_sha256": job["source_sha256"],
        "expected_geometry": job["expected_geometry"],
        "setup_sha256": job["setup_sha256"],
        "scan_index": int(job["scan_index"]),
        "cache_npz": str(npz.resolve()),
        "cache_json": str(meta_path.resolve()),
        "detector_positive_events": int(meta["detector_positive_events"]),
        "tes_positive_events": int(meta["tes_positive_events"]),
        "active_only_events": int(meta["active_only_events"]),
        "raw_pixel_hits": int(meta["raw_pixel_hits"]),
        "weight_cps": 0.0,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
    }


def execute_model(
    model: str,
    model_cfg: dict[str, Any],
    jobs: list[dict[str, Any]],
    preflight_audit: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    model_output = OUTPUTS / model
    cache_dir = model_output / "job_catalogs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    guard_existing_cache(model, cache_dir, jobs)
    parser_path = repo_path(model_cfg["parser"])
    response_config = repo_path(model_cfg["response_config"])
    threshold = float(preflight_audit["response"]["threshold_keV"])
    started = time.time()
    metas: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                scan_worker,
                model,
                str(parser_path),
                str(response_config),
                str(cache_dir),
                threshold,
                job,
            ): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            meta = future.result()
            metas.append(meta)
            print(
                json.dumps(
                    {
                        "model": model,
                        "job_id": job["job_id"],
                        "family": job["family"],
                        "detector_positive_events": int(meta["detector_positive_events"]),
                        "complete": len(metas),
                        "total": len(jobs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    meta_by_id = indexed(metas, "job_id", f"{model} compact metadata")
    rows = [verify_compact_meta(model, job, meta_by_id[job["job_id"]], cache_dir) for job in jobs]
    exposure = {
        family: math.fsum(float(row["exposure_TT_s"]) for row in rows if row["family"] == family)
        for family in model_cfg["families"]
    }
    jobs_payload = {
        "schema_version": 1,
        "schema": "m05_supplement_compact_jobs_v1",
        "status": "PASS__M05_SUPPLEMENT_COMPACT_JOBS",
        "model": model,
        "candidate": model_cfg["candidate"],
        "setup_stratum": model_cfg["setup_stratum"],
        "jobs_count": len(rows),
        "events": sum(int(row["events"]) for row in rows),
        "seeds": [int(row["seed"]) for row in rows],
        "exposure_TT_s_by_family": exposure,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
        "base_overlap_audit": preflight_audit["base_overlap_audit"],
        "jobs": rows,
    }
    jobs_path = model_output / "jobs.json"
    write_json(jobs_path, jobs_payload)
    scan_audit = {
        "schema_version": 1,
        "schema": "m05_supplement_scan_audit_v1",
        "status": "PASS__M05_SUPPLEMENT_STREAMING_COMPACTION",
        "model": model,
        "candidate": model_cfg["candidate"],
        "setup_stratum": model_cfg["setup_stratum"],
        "jobs_json": str(jobs_path),
        "jobs_count": len(rows),
        "events": jobs_payload["events"],
        "detector_positive_events": sum(int(row["detector_positive_events"]) for row in rows),
        "tes_positive_events": sum(int(row["tes_positive_events"]) for row in rows),
        "active_only_events": sum(int(row["active_only_events"]) for row in rows),
        "raw_pixel_hits": sum(int(row["raw_pixel_hits"]) for row in rows),
        "exposure_TT_s_by_family": exposure,
        "wall_s": time.time() - started,
        "workers": workers,
        "authority_boundary": {
            "sim_payloads_streamed": len(rows),
            "sim_payload_bytes_streamed": sum(int(row["sim_bytes"]) for row in rows),
            "sim_hashes_computed": 0,
            "cosima_transport_started": False,
            "paper_or_ebb2_outputs_modified": False,
            "model_or_setup_strata_merged": False,
            "final_physical_weights_assigned": False,
        },
    }
    write_json(model_output / "scan_audit.json", scan_audit)
    return scan_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("sg3", "sh3", "both"), default="both")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="targeted header-only validation (default)")
    mode.add_argument("--execute", action="store_true", help="stream validated SIMs into compact caches")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1 or args.workers > 8:
        raise ClosureError("--workers must be in [1, 8]")
    manifest_path = args.manifest.resolve(strict=True)
    audit, jobs_by_model = preflight(manifest_path, args.model)
    write_json(OUTPUTS / "preflight_audit.json", audit)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "selection": args.model,
                "jobs": sum(len(rows) for rows in jobs_by_model.values()),
                "audit": str(OUTPUTS / "preflight_audit.json"),
                "execute": bool(args.execute),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if not args.execute:
        return 0

    manifest = load_json(manifest_path)
    execution: dict[str, Any] = {}
    for model in selected_models(args.model):
        execution[model] = execute_model(
            model,
            manifest["models"][model],
            jobs_by_model[model],
            audit["models"][model],
            args.workers,
        )
    summary = {
        "schema_version": 1,
        "status": "PASS__M05_SUPPLEMENT_COMPACTION_SELECTED_MODELS",
        "selection": args.model,
        "models": execution,
        "sim_hashes_computed": 0,
        "cosima_transport_started": False,
    }
    write_json(OUTPUTS / "execution_summary.json", summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClosureError as exc:
        print(json.dumps({"status": "FAIL__CLOSURE", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
