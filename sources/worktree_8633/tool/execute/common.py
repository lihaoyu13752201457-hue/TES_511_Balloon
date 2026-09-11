#!/usr/bin/env python3
"""Small shared helpers for the SG3B background execution package."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PACKAGE_ROOT / "config.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve() if path else CONFIG_PATH
    config = load_json(config_path)
    if config.get("schema_version") != 1:
        raise RuntimeError("config identity is not schema-1")
    for key in ("profile_id", "candidate", "generated_root", "run_root"):
        if not config.get(key):
            raise RuntimeError(f"config lacks required identity field: {key}")
    return config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, path)


def write_once_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"write-once conflict: {path}")
        return
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(text, encoding="utf-8")
    try:
        os.link(partial, path)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"concurrent write-once conflict: {path}")
    finally:
        partial.unlink(missing_ok=True)


def write_once_json(path: Path, value: Any) -> None:
    write_once_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _resolved_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_plan_payload(config: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = payload.get("jobs")
    if (
        payload.get("schema_version") != 1
        or payload.get("status") != "PASS"
        or payload.get("profile_id") != config["profile_id"]
        or payload.get("candidate") != config["candidate"]
        or not isinstance(jobs, list)
    ):
        raise RuntimeError("generated job plan identity/status is not compatible with config")
    if len(jobs) != int(config["expected_jobs"]):
        raise RuntimeError("generated job plan count drift")
    job_ids = [str(job.get("job_id", "")) for job in jobs]
    seeds = [job.get("seed") for job in jobs]
    ordinals = [job.get("ordinal") for job in jobs]
    if not all(job_ids) or len(set(job_ids)) != len(job_ids):
        raise RuntimeError("job plan IDs are empty or non-unique")
    if not all(isinstance(seed, int) and seed > 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise RuntimeError("job plan seeds are invalid or non-unique")
    if len(set(ordinals)) != len(ordinals):
        raise RuntimeError("job plan ordinals are non-unique")
    generated_sources = Path(config["generated_root"]) / "sources"
    run_root = Path(config["run_root"])
    allowed_stages = set(config.get("allowed_stages", ["background"]))
    for job in jobs:
        job_id = str(job["job_id"])
        expected_prefix = run_root / "jobs" / job_id / "active" / job_id
        if job.get("candidate") != config["candidate"] or job.get("stage") not in allowed_stages:
            raise RuntimeError(f"job candidate/stage drift: {job_id}")
        if job.get("setup_path") != config["geometry_setup"]:
            raise RuntimeError(f"job setup drift: {job_id}")
        if not isinstance(job.get("events"), int) or int(job["events"]) <= 0:
            raise RuntimeError(f"job event count is invalid: {job_id}")
        if not _resolved_under(Path(job["source_path"]), generated_sources):
            raise RuntimeError(f"job source escapes generated source root: {job_id}")
        if Path(job["output_prefix"]).resolve() != expected_prefix.resolve():
            raise RuntimeError(f"job output prefix/run root drift: {job_id}")
    totals = payload.get("totals", {})
    instant = sum(int(job["events"]) for job in jobs if job.get("mode") == "instant")
    buildup = sum(int(job["events"]) for job in jobs if job.get("mode") == "buildup")
    expected_totals = {
        "jobs": len(jobs),
        "instant_histories": instant,
        "buildup_histories": buildup,
    }
    if totals != expected_totals:
        raise RuntimeError("job plan stored totals drift from job rows")
    if "expected_instant_histories" in config and instant != int(config["expected_instant_histories"]):
        raise RuntimeError("job plan INSTANT total drift")
    if "expected_buildup_histories" in config and buildup != int(config["expected_buildup_histories"]):
        raise RuntimeError("job plan BUILDUP total drift")
    if sum(bool(job.get("production_canary")) for job in jobs) != 1:
        raise RuntimeError("job plan must contain exactly one production canary")
    if next(job["job_id"] for job in jobs if job.get("production_canary")) != config["canary_job_id"]:
        raise RuntimeError("job plan canary identity drift")
    return jobs


def load_plan(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    payload = load_json(Path(cfg["generated_root"]) / "job_plan.json")
    return validate_plan_payload(cfg, payload)


def validate_generated_bundle(config: dict[str, Any], jobs: list[dict[str, Any]]) -> None:
    generated = Path(config["generated_root"])
    registry = load_json(generated / "seed_registry.json")
    manifest = load_json(generated / "source_manifest.json")
    preflight = load_json(generated / "preflight.json")
    expected_identity = (config["profile_id"], config["candidate"])
    if registry.get("profile_id") != expected_identity[0] or registry.get("status") != config.get("seed_registry_pass_status", "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS"):
        raise RuntimeError("seed registry identity/status drift")
    if manifest.get("profile_id") != expected_identity[0] or manifest.get("status") != config.get("source_manifest_pass_status", "PASS__SG3B_CORRECTED_BACKGROUND_SOURCES"):
        raise RuntimeError("source manifest identity/status drift")
    if preflight.get("profile_id") != expected_identity[0] or preflight.get("candidate") != expected_identity[1]:
        raise RuntimeError("preflight identity drift")
    if preflight.get("status") != config.get("preflight_pass_status", "PASS__SG3B_BACKGROUND_TRANSPORT_PREFLIGHT"):
        raise RuntimeError("preflight status is not PASS")
    expected_totals = {
        "jobs": len(jobs),
        "instant_histories": sum(int(job["events"]) for job in jobs if job["mode"] == "instant"),
        "buildup_histories": sum(int(job["events"]) for job in jobs if job["mode"] == "buildup"),
    }
    if preflight.get("job_plan") != expected_totals:
        raise RuntimeError("preflight job totals drift")
    registry_rows = registry.get("seeds")
    manifest_rows = manifest.get("sources")
    if not isinstance(registry_rows, list) or not isinstance(manifest_rows, list):
        raise RuntimeError("generated registry/manifest rows are invalid")
    seed_by_job = {str(row.get("job_id")): row.get("seed") for row in registry_rows}
    source_by_job = {str(row.get("job_id")): row for row in manifest_rows}
    if set(seed_by_job) != {job["job_id"] for job in jobs} or set(source_by_job) != set(seed_by_job):
        raise RuntimeError("job plan, seed registry and source manifest identities differ")
    for job in jobs:
        job_id = job["job_id"]
        row = source_by_job[job_id]
        source = Path(job["source_path"])
        if seed_by_job[job_id] != job["seed"]:
            raise RuntimeError(f"seed registry drift: {job_id}")
        for key in ("mode", "family", "events", "seed", "source_path", "setup_path"):
            if row.get(key) != job.get(key):
                raise RuntimeError(f"source manifest {key} drift: {job_id}")
        if not source.is_file() or sha256(source) != row.get("source_sha256"):
            raise RuntimeError(f"source card content drift: {job_id}")
        text = source.read_text(encoding="utf-8", errors="replace")
        if config.get("source_policy", "corrected_keV_background") == "corrected_keV_background":
            if text.count(config["corrected_token"]) != 20:
                raise RuntimeError(f"corrected-keV source token drift: {job_id}")
            if config["forbidden_legacy_token"] in text or "mono511" in text.lower() or "mono_511" in text.lower():
                raise RuntimeError(f"forbidden source content: {job_id}")


def canonical_receipt_path(config: dict[str, Any], job_id: str) -> Path:
    return Path(config["run_root"]) / "receipts" / f"{job_id}.json"


def load_bound_receipt(
    config: dict[str, Any],
    job: dict[str, Any],
    *,
    require_artifacts: bool = True,
) -> dict[str, Any] | None:
    path = canonical_receipt_path(config, job["job_id"])
    if not path.is_file():
        return None
    payload = load_json(path)
    expected = {
        "status": "PASS",
        "profile_id": config["profile_id"],
        "candidate": config["candidate"],
        "job_id": job["job_id"],
        "mode": job["mode"],
        "family": job["family"],
        "events": job["events"],
        "seed": job["seed"],
        "source_path": job["source_path"],
        "setup_path": job["setup_path"],
    }
    mismatches = [key for key, value in expected.items() if payload.get(key) != value]
    if payload.get("errors") or mismatches:
        raise RuntimeError(f"canonical receipt identity mismatch ({mismatches}): {path}")
    sim_header = payload.get("sim_header", {})
    if sim_header.get("geometry") != job["setup_path"] or sim_header.get("seed") != job["seed"]:
        raise RuntimeError(f"canonical receipt SIM-header evidence mismatch: {path}")
    source = Path(job["source_path"])
    if not source.is_file() or payload.get("source_sha256") != sha256(source):
        raise RuntimeError(f"canonical receipt source evidence mismatch: {path}")
    if require_artifacts:
        attempt_dir = Path(str(payload.get("attempt_dir", "")))
        expected_attempt_root = Path(config["run_root"]) / "jobs" / job["job_id"] / "attempts"
        if not _resolved_under(attempt_dir, expected_attempt_root):
            raise RuntimeError(f"canonical receipt attempt path escapes job root: {path}")
        expected_paths = {
            "sim_path": attempt_dir / f"{job['job_id']}.inc1.id1.sim.gz",
            "log_path": attempt_dir / f"{job['job_id']}.log",
        }
        if job.get("requires_isotope_dat", True):
            expected_paths["isotope_dat_path"] = attempt_dir / f"{job['job_id']}.dat.inc1.dat"
        for key, expected_path in expected_paths.items():
            artifact = Path(str(payload.get(key, "")))
            if artifact.resolve() != expected_path.resolve() or not artifact.is_file() or artifact.stat().st_size <= 0:
                raise RuntimeError(f"canonical receipt artifact is missing/misbound ({key}): {path}")
    return payload


def meminfo() -> dict[str, int]:
    result = {"MemAvailable": 0, "SwapFree": 0}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key = line.split(":", 1)[0]
        if key in result:
            result[key] = int(line.split()[1]) * 1024
    return result


def load_megalib_environment(path: Path) -> dict[str, str]:
    command = f"source {shlex.quote(str(path))} >/dev/null && env -0"
    completed = subprocess.run(
        ["bash", "-c", command],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    environment = dict(os.environ)
    for item in completed.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        environment[key.decode()] = value.decode()
    return environment
